from __future__ import annotations

import argparse
import compileall
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, resolve_project


PLACEHOLDER_RE = re.compile(r"{{[A-Z0-9_]+}}")
LOCAL_REFERENCE_RE = re.compile(r"G:[/\\]html|ref[/\\](agent-rules|html)", flags=re.IGNORECASE)
TOOL_SKILL_DIR = Path(__file__).resolve().parents[1]
ERROR_CATEGORY_NAMES = (
    "tooling_error",
    "self_repo_governance_error",
    "target_repo_governance_error",
    "target_repo_behavior_error",
)


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


def run_command(name: str, argv: list[str], cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    command_env = dict(env) if env is not None else dict(os.environ)
    command_env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False, env=command_env)
    return command_entry(name, argv, cwd, result)


def quick_validate_script() -> Path:
    candidates = [
        TOOL_SKILL_DIR.parent / ".system" / "skill-creator" / "scripts" / "quick_validate.py",
        Path.home() / ".codex" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("quick_validate helper not found in installed skill-creator locations")


def existing_python_roots(skill_dir: Path) -> list[str]:
    roots: list[str] = []
    for name in ("runtime", "integration", "smoke", "scripts", "tests"):
        if (skill_dir / name).exists():
            roots.append(name)
    return roots


def settings_arg(skill_dir: Path) -> list[str]:
    settings_path = skill_dir / "config" / "defaults.json"
    if settings_path.is_file():
        return ["--settings", str(settings_path)]
    return []


def discover_validate_script(skill_dir: Path) -> Path | None:
    scripts_dir = skill_dir / "scripts"
    if not scripts_dir.is_dir():
        return None
    candidates = sorted(path for path in scripts_dir.glob("validate*.py") if path.name not in {"quick_validate.py"})
    if len(candidates) == 1:
        return candidates[0]
    preferred = scripts_dir / f"validate_{skill_dir.name.replace('-', '_')}.py"
    if preferred in candidates:
        return preferred
    return None


def cleanup_python_caches(skill_dir: Path) -> None:
    for path in skill_dir.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)


def cleanup_transient_artifacts(skill_dir: Path) -> None:
    cleanup_python_caches(skill_dir)
    smoke_root = skill_dir / "_smoke_runs"
    if smoke_root.is_dir():
        shutil.rmtree(smoke_root, ignore_errors=True)


def render_entry(project: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    argv = [sys.executable, str(TOOL_SKILL_DIR / "scripts" / "render_agents.py"), str(project)]
    command_env = dict(env) if env is not None else dict(os.environ)
    command_env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        argv,
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
        env=command_env,
    )
    entry = command_entry("render_agents", argv, project, result)
    output = result.stdout
    entry["json"] = {
        "unresolved_placeholders": sorted(set(PLACEHOLDER_RE.findall(output))),
        "local_reference_leaks": sorted(set(match.group(0) for match in LOCAL_REFERENCE_RE.finditer(output))),
    }
    return entry


def collect_errors(commands: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for entry in commands:
        name = entry["name"]
        if entry["returncode"] != 0:
            errors.append(f"{name}: command exited with {entry['returncode']}")
        parsed = entry.get("json")
        if isinstance(parsed, dict):
            for item in parsed.get("errors", []) or []:
                errors.append(f"{name}: {item}")
            if name == "verify_agents":
                for checked in parsed.get("checked_files", []) or []:
                    if str(checked).startswith("ref/"):
                        errors.append(f"verify_agents: checked skipped reference file {checked}")
            if name == "render_agents":
                for item in parsed.get("unresolved_placeholders", []) or []:
                    errors.append(f"render_agents: unresolved placeholder {item}")
                for item in parsed.get("local_reference_leaks", []) or []:
                    errors.append(f"render_agents: local reference leak {item}")
    return errors


def error_category_for(command_name: str, *, self_skill: bool) -> str:
    if command_name in {"manage_docs_verify", "verify_agents"}:
        return "self_repo_governance_error" if self_skill else "target_repo_governance_error"
    if command_name in {"smoke", "validate_script"}:
        return "target_repo_behavior_error"
    if command_name in {"audit_skill", "compileall", "quick_validate"}:
        return "tooling_error" if self_skill else "target_repo_behavior_error"
    return "tooling_error"


def classified_errors(commands: list[dict[str, Any]], *, self_skill: bool) -> list[dict[str, str]]:
    classified: list[dict[str, str]] = []
    for entry in commands:
        name = entry["name"]
        category = error_category_for(name, self_skill=self_skill)
        if entry["returncode"] != 0:
            classified.append(
                {
                    "category": category,
                    "command": name,
                    "message": f"command exited with {entry['returncode']}",
                }
            )
        parsed = entry.get("json")
        if isinstance(parsed, dict):
            for item in parsed.get("errors", []) or []:
                item_category = category
                classified.append(
                    {
                        "category": item_category,
                        "command": name,
                        "message": str(item),
                    }
                )
            if name == "verify_agents":
                for checked in parsed.get("checked_files", []) or []:
                    if str(checked).startswith("ref/"):
                        classified.append(
                            {
                                "category": "tooling_error",
                                "command": name,
                                "message": f"checked skipped reference file {checked}",
                            }
                        )
            if name == "render_agents":
                for item in parsed.get("unresolved_placeholders", []) or []:
                    classified.append(
                        {
                            "category": "tooling_error",
                            "command": name,
                            "message": f"unresolved placeholder {item}",
                        }
                    )
                for item in parsed.get("local_reference_leaks", []) or []:
                    classified.append(
                        {
                            "category": "tooling_error",
                            "command": name,
                            "message": f"local reference leak {item}",
                        }
                    )
    return classified


def category_counts(classified: list[dict[str, str]]) -> dict[str, int]:
    counts = {name: 0 for name in ERROR_CATEGORY_NAMES}
    for item in classified:
        category = item.get("category", "")
        if category in counts:
            counts[category] += 1
    return counts


def repo_root_for(skill_dir: Path) -> Path:
    for candidate in [skill_dir.parent.parent, skill_dir.parent, skill_dir]:
        if (candidate / "tests").is_dir():
            return candidate
    return skill_dir.parent.parent if skill_dir.parent != skill_dir else skill_dir


def compileall_entry(skill_dir: Path, repo_root: Path, env: dict[str, str]) -> dict[str, Any]:
    roots = existing_python_roots(skill_dir)
    messages: list[str] = []
    ok = True
    for name in roots:
        target = skill_dir / name
        if not compileall.compile_dir(str(target), quiet=1, force=False):
            ok = False
            messages.append(f"compileall failed for {name}")
    payload = {"roots": roots, "errors": [] if ok else messages}
    result = subprocess.CompletedProcess(
        args=[sys.executable, "-m", "compileall", *roots],
        returncode=0 if ok else 1,
        stdout=json.dumps(payload),
        stderr="",
    )
    return command_entry("compileall", [sys.executable, "-m", "compileall", *roots], repo_root, result)


def evaluate(skill_dir: Path, project: Path) -> dict[str, Any]:
    repo_root = repo_root_for(skill_dir)
    self_skill = skill_dir.name == "agents-md-generator"
    base_env = dict(
        os.environ,
        AGENTS_MD_EVALUATE_RUNNING="1",
    )
    if self_skill:
        base_env["AGENTS_MD_INSTALLED_SKILL_DIR"] = str(TOOL_SKILL_DIR)
    else:
        base_env.pop("AGENTS_MD_INSTALLED_SKILL_DIR", None)

    commands: list[dict[str, Any]] = []
    warnings: list[str] = []
    cleanup_transient_artifacts(skill_dir)

    commands.append(
        run_command(
            "audit_skill",
            [sys.executable, str(TOOL_SKILL_DIR / "scripts" / "audit_skill.py"), str(skill_dir)],
            repo_root,
            base_env,
        )
    )

    python_roots = existing_python_roots(skill_dir)
    if python_roots:
        commands.append(compileall_entry(skill_dir, repo_root, base_env))
        cleanup_transient_artifacts(skill_dir)

    try:
        validator = quick_validate_script()
    except FileNotFoundError as exc:
        warnings.append(str(exc))
    else:
        commands.append(run_command("quick_validate", [sys.executable, str(validator), str(skill_dir)], repo_root, base_env))

    smoke_script = skill_dir / "smoke" / "run_smoke.py"
    if smoke_script.is_file():
        commands.append(run_command("smoke", [sys.executable, str(smoke_script)], repo_root, base_env))

    validate_script = discover_validate_script(skill_dir)
    if validate_script is not None:
        commands.append(
            run_command(
                "validate_script",
                [sys.executable, str(validate_script), *settings_arg(skill_dir)],
                repo_root,
                base_env,
            )
        )

    manage_docs_script = TOOL_SKILL_DIR / "scripts" / "manage_docs.py"
    if manage_docs_script.is_file() and (project / ".agents" / "agents-control.json").is_file():
        commands.append(
            run_command("manage_docs_verify", [sys.executable, str(manage_docs_script), "verify", str(project)], repo_root, base_env)
        )

    verify_agents_script = TOOL_SKILL_DIR / "scripts" / "verify_agents.py"
    if verify_agents_script.is_file() and (project / "AGENTS.md").is_file():
        verify_argv = [sys.executable, str(verify_agents_script), str(project)]
        if self_skill:
            verify_argv.extend(["--installed-skill-dir", str(skill_dir)])
        commands.append(run_command("verify_agents", verify_argv, repo_root, base_env))

    if self_skill:
        commands.append(render_entry(project, base_env))

    cleanup_transient_artifacts(skill_dir)
    errors = collect_errors(commands)
    structured_errors = classified_errors(commands, self_skill=self_skill)
    return {
        "ok": not errors,
        "skill_dir": str(skill_dir),
        "project": str(project),
        "commands": commands,
        "errors": errors,
        "classified_errors": structured_errors,
        "category_counts": category_counts(structured_errors),
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the fact-level validation chain for a target skill.")
    parser.add_argument("skill_dir", nargs="?", default=".")
    parser.add_argument("project", nargs="?", default=None)
    args = parser.parse_args()
    skill_dir = resolve_project(args.skill_dir)
    project = resolve_project(args.project) if args.project else repo_root_for(skill_dir)
    emit_json(evaluate(skill_dir, project))


if __name__ == "__main__":
    main()
