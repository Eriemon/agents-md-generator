from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SCRIPT_DIR.parents[2]
TESTS_DIR = REPO_ROOT / "tests"
sys.path.insert(0, str(SCRIPT_DIR))

from agents_common import emit_json, resolve_project


PYTHON_CACHE_SUFFIXES = (".pyc", ".pyo")


def command_entry(name: str, argv: list[str], cwd: Path, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "name": name,
        "argv": argv,
        "cwd": str(cwd),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    try:
        entry["json"] = json.loads(result.stdout)
    except json.JSONDecodeError:
        entry["json"] = None
    return entry


def run_command(name: str, argv: list[str], cwd: Path) -> dict[str, Any]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", AGENTS_MD_INSTALLED_SKILL_DIR=str(SKILL_DIR))
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False, env=env)
    return command_entry(name, argv, cwd, result)


def cleanup_transient_artifacts(skill_dir: Path) -> None:
    for path in skill_dir.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


def parsed_errors(entry: dict[str, Any]) -> list[str]:
    parsed = entry.get("json")
    if not isinstance(parsed, dict):
        return []
    return [str(item) for item in (parsed.get("errors") or [])]


def is_cache_only_audit_failure(entry: dict[str, Any]) -> bool:
    if entry.get("name") != "audit_skill":
        return False
    errors = parsed_errors(entry)
    if not errors:
        return False
    return all("__pycache__" in item or any(suffix in item for suffix in PYTHON_CACHE_SUFFIXES) for item in errors)


def current_version(skill_dir: Path) -> str:
    version_path = skill_dir / "VERSION"
    return version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else "unknown"


def confidence_gate(
    project: Path,
    skill_dir: Path,
    *,
    evals_path: Path,
    external_skill_dir: Path | None = None,
    review_base: str | None = None,
) -> dict[str, Any]:
    version = current_version(skill_dir)
    if not review_base:
        return {
            "ok": False,
            "project": str(project),
            "skill_dir": str(skill_dir),
            "version": version,
            "commands": [],
            "errors": ["review_base is required for automated review governance; pass --review-base <sha>"],
        }
    skill_dir_arg = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else str(skill_dir)
    cleanup_transient_artifacts(skill_dir)
    if external_skill_dir is not None:
        cleanup_transient_artifacts(external_skill_dir)

    def run_audit() -> dict[str, Any]:
        return run_command("audit_skill", [sys.executable, str(SCRIPT_DIR / "audit_skill.py"), str(skill_dir)], project)

    audit_entry = run_audit()
    if is_cache_only_audit_failure(audit_entry):
        cleanup_transient_artifacts(skill_dir)
        audit_entry = run_audit()

    commands = [
        audit_entry,
        run_command("quick_validate", [sys.executable, str(SCRIPT_DIR / "quick_validate.py"), str(skill_dir)], project),
        run_command("manage_docs_verify", [sys.executable, str(SCRIPT_DIR / "manage_docs.py"), "verify", str(project)], project),
        run_command(
            "verify_agents",
            [sys.executable, str(SCRIPT_DIR / "verify_agents.py"), str(project), "--installed-skill-dir", str(skill_dir)],
            project,
        ),
        run_command("source_governance", [sys.executable, str(SCRIPT_DIR / "check_source_governance.py"), str(project)], project),
        run_command("evaluate_skill", [sys.executable, str(SCRIPT_DIR / "evaluate_skill.py"), str(skill_dir), str(project)], project),
        run_command("run_skill_evals", [sys.executable, str(TESTS_DIR / "run_skill_evals.py"), str(evals_path)], project),
        run_command(
            "work_folder_gate",
            [sys.executable, str(SCRIPT_DIR / "manage_docs.py"), "work-folder-gate", str(project), "--skill-dir", skill_dir_arg, "--mode", "release"],
            project,
        ),
        run_command("check_freshness", [sys.executable, str(SCRIPT_DIR / "check_freshness.py"), str(project)], project),
        run_command(
            "review_governance",
            [
                sys.executable,
                str(SCRIPT_DIR / "review_governance.py"),
                str(project),
                "--base",
                review_base,
                "--head",
                "HEAD",
                "--skill-dir",
                skill_dir_arg,
                "--mode",
                "all",
            ],
            project,
        ),
        run_command("branch_gate", [sys.executable, str(SCRIPT_DIR / "manage_docs.py"), "branch-gate", str(project)], project),
        run_command(
            "release_gate_pre",
            [sys.executable, str(SCRIPT_DIR / "manage_docs.py"), "release-gate", str(project), "--version", version, "--skill-dir", skill_dir_arg, "--phase", "pre"],
            project,
        ),
        run_command(
            "release_gate_post",
            [sys.executable, str(SCRIPT_DIR / "manage_docs.py"), "release-gate", str(project), "--version", version, "--skill-dir", skill_dir_arg, "--phase", "post"],
            project,
        ),
    ]
    release_dir = project / "dist" / f"{skill_dir.name}-{version}"
    if release_dir.is_dir():
        commands.append(
            run_command("install_skip", [sys.executable, str(SCRIPT_DIR / "install_skill.py"), str(release_dir), "--target", "skip"], project)
        )
    if external_skill_dir is not None:
        commands.append(
            run_command(
                "external_skill_eval",
                [
                    sys.executable,
                    str(TESTS_DIR / "run_skill_evals.py"),
                    str(evals_path),
                    "--external-skill-dir",
                    str(external_skill_dir),
                ],
                project,
            )
        )
    errors: list[str] = []
    for entry in commands:
        name = entry["name"]
        if entry["returncode"] != 0:
            errors.append(f"{name}: command exited with {entry['returncode']}")
        parsed = entry.get("json")
        if isinstance(parsed, dict):
            if name in {"branch_gate"} and parsed.get("approved") is False:
                errors.extend(f"{name}: {item}" for item in parsed.get("reasons", []))
            if name in {"release_gate_pre", "release_gate_post"} and parsed.get("errors"):
                errors.extend(f"{name}: {item}" for item in parsed.get("errors", []))
            if name in {"audit_skill", "manage_docs_verify", "verify_agents", "source_governance", "evaluate_skill"} and parsed.get("errors"):
                errors.extend(f"{name}: {item}" for item in parsed.get("errors", []))
            if name == "source_governance":
                for item in parsed.get("oversized_source_files", []):
                    errors.append(f"{name}: oversized file {item.get('path', '')}")
                for item in parsed.get("test_code_boundary_violations", []):
                    errors.append(f"{name}: test-only design code outside tests {item.get('path', '')}")
                for item in parsed.get("comment_policy_violations", []):
                    errors.append(f"{name}: comment policy violation {item.get('path', '')}: {item.get('message', '')}")
            if name == "work_folder_gate" and parsed.get("ok") is False:
                errors.extend(f"{name}: {item}" for item in parsed.get("errors", []))
            if name == "check_freshness" and parsed.get("stale") is True:
                errors.append("check_freshness: AGENTS.md freshness check is stale")
            if name == "review_governance" and parsed.get("ok") is False:
                for item in parsed.get("findings", []):
                    if isinstance(item, dict):
                        errors.append(f"review_governance: {item.get('code', 'finding')}: {item.get('message', '')}")
            if name == "run_skill_evals" and parsed.get("summary", {}).get("ok") is not True:
                errors.append(f"{name}: skill-effectiveness cases are not all green")
            if name == "install_skip" and parsed.get("errors"):
                errors.extend(f"{name}: {item}" for item in parsed.get("errors", []))
            if name == "external_skill_eval" and parsed.get("summary", {}).get("ok") is not True:
                errors.append("external_skill_eval: external skill evaluation case is not green")
    return {
        "ok": not errors,
        "project": str(project),
        "skill_dir": str(skill_dir),
        "version": version,
        "commands": commands,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the repository-local confidence gate for agents-md-generator.")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--skill-dir", default=str(SKILL_DIR))
    parser.add_argument("--evals-path", default=str(SKILL_DIR / "evals" / "evals.json"))
    parser.add_argument("--external-skill-dir", default=None)
    parser.add_argument("--review-base", default=None)
    args = parser.parse_args()

    project = resolve_project(args.project)
    skill_dir = resolve_project(args.skill_dir)
    evals_path = Path(args.evals_path).expanduser().resolve()
    external_skill_dir = Path(args.external_skill_dir).expanduser().resolve() if args.external_skill_dir else None
    emit_json(confidence_gate(project, skill_dir, evals_path=evals_path, external_skill_dir=external_skill_dir, review_base=args.review_base))


if __name__ == "__main__":
    main()
