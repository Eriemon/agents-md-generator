from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, resolve_project


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SKILL_DIR = SCRIPT_DIR.parent
GATE_SCRIPT_NAMES = {
    "check_source_governance.py",
    "check_freshness.py",
    "collect_design_profile.py",
    "design_questions.py",
    "design_review_gate.py",
    "design_interview_state.py",
    "design_profile_builder.py",
    "source_governance.py",
    "source_governance_config.py",
    "render_agents.py",
    "manage_dirs.py",
    "manage_docs.py",
    "manage_docs_release.py",
    "manage_docs_sync_verify.py",
    "review_governance.py",
    "run_confidence_gate.py",
    "verify_agents.py",
}
CLI_SCRIPT_NAMES = GATE_SCRIPT_NAMES | {"install_skill.py"}
RUNTIME_ROUTING_SCRIPT_NAMES = {
    "agents_common.py",
    "agents_project_facts.py",
    "design_takeover.py",
    "manage_dirs.py",
    "manage_docs_scaffold_session.py",
    "manage_docs_shared.py",
    "manage_docs_sync_verify.py",
    "render_agents.py",
    "verify_agents.py",
}


def run_git(project: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)


def changed_files(project: Path, base: str, head: str) -> list[str]:
    result = run_git(project, ["diff", "--name-only", base, head])
    if result.returncode != 0:
        raise SystemExit(json.dumps({"ok": False, "errors": [result.stderr.strip() or result.stdout.strip() or "git diff failed"]}, indent=2))
    return sorted(line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip())


def finding(code: str, message: str, paths: list[str], severity: str = "error") -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "paths": sorted(paths),
    }


def review_dispatch_policy(mode: str, changes: list[str]) -> str:
    if not changes:
        return "none"
    if mode == "release":
        return "required_for_release"
    return "optional"


def changed_under(changes: set[str], prefix: str) -> list[str]:
    return sorted(path for path in changes if path.startswith(prefix))


def script_name(path: str) -> str:
    return Path(path).name


def build_findings(changes: list[str], skill_dir_rel: str) -> list[dict[str, Any]]:
    changed = set(changes)
    script_prefix = f"{skill_dir_rel.rstrip('/')}/scripts/"
    reference_prefix = f"{skill_dir_rel.rstrip('/')}/references/"
    evals_json = f"{skill_dir_rel.rstrip('/')}/evals/evals.json"
    version_file = f"{skill_dir_rel.rstrip('/')}/VERSION"
    script_changes = [path for path in changed_under(changed, script_prefix) if path.endswith(".py")]
    gate_changes = [path for path in script_changes if script_name(path) in GATE_SCRIPT_NAMES]
    cli_changes = [path for path in script_changes if script_name(path) in CLI_SCRIPT_NAMES]
    runtime_routing_changes = [path for path in script_changes if script_name(path) in RUNTIME_ROUTING_SCRIPT_NAMES]
    test_changes = [path for path in changed if path.startswith("tests/") and path.endswith(".py")]
    findings: list[dict[str, Any]] = []

    if script_changes and not test_changes:
        findings.append(
            finding(
                "script-change-without-tests",
                "Script changes require tests/*.py coverage in the same review span.",
                script_changes,
            )
        )
    if cli_changes and f"{reference_prefix}script-guide.md" not in changed:
        findings.append(
            finding(
                "cli-change-without-script-guide",
                "CLI or gate script changes require script-guide.md documentation in the same review span.",
                cli_changes,
            )
        )
    if gate_changes and f"{reference_prefix}review-checklist.md" not in changed:
        findings.append(
            finding(
                "gate-change-without-review-checklist",
                "Gate behavior changes require review-checklist.md coverage in the same review span.",
                gate_changes,
            )
        )
    if gate_changes and evals_json not in changed and f"{reference_prefix}evaluation-scenarios.md" not in changed:
        findings.append(
            finding(
                "gate-change-without-evals",
                "Gate behavior changes require eval or evaluation-scenarios coverage in the same review span.",
                gate_changes,
            )
        )
    if runtime_routing_changes and evals_json not in changed and "tests/run_skill_evals.py" not in changed:
        findings.append(
            finding(
                "runtime-routing-change-without-eval-harness",
                "Governance runtime routing changes require eval coverage in evals/evals.json or tests/run_skill_evals.py.",
                runtime_routing_changes,
            )
        )
    if version_file in changed:
        required_docs = {
            "docs/development/DEVELOPMENT.md",
            "docs/git_manager/CHANGELOG.md",
            "docs/git_manager/GIT_MANAGER.md",
        }
        missing = sorted(required_docs - changed)
        if missing:
            findings.append(
                finding(
                    "version-change-without-release-docs",
                    "VERSION changes require DEVELOPMENT, CHANGELOG, and GIT_MANAGER current-version updates.",
                    [version_file, *missing],
                )
            )
    return findings


def review_request(project: Path, base: str, head: str, changes: list[str], findings: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    dispatch = review_dispatch_policy(mode, changes)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "base": base,
        "head": head,
        "mode": mode,
        "changed_files": changes,
        "deterministic_findings": findings,
        "review_dispatch_policy": dispatch,
        "required_manual_review": dispatch == "required_for_release",
        "review_focus": [
            "Confirm the deterministic findings are resolved or intentionally accepted.",
            "Review design consistency for gate semantics, user confirmation wording, and release/install safety.",
            "Review code quality for small focused helpers, stable JSON output, and backwards-compatible fields.",
        ],
    }


def review_governance(project: Path, base: str, head: str, skill_dir: Path, mode: str, write_request: bool = False) -> dict[str, Any]:
    changes = changed_files(project, base, head)
    skill_dir_rel = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else skill_dir.as_posix()
    findings = build_findings(changes, skill_dir_rel)
    dispatch = review_dispatch_policy(mode, changes)
    request = review_request(project, base, head, changes, findings, mode)
    request_path = ""
    if write_request:
        target = project / ".agents" / "review-request.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")
        request_path = target.relative_to(project).as_posix()
    return {
        "project": str(project),
        "base": base,
        "head": head,
        "mode": mode,
        "changed_files": changes,
        "findings": findings,
        "review_dispatch_policy": dispatch,
        "required_manual_review": dispatch == "required_for_release",
        "ok": not any(item["severity"] == "error" for item in findings),
        "review_request": request,
        "review_request_path": request_path,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Review governance-sensitive code and design changes.")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--skill-dir", default=str(DEFAULT_SKILL_DIR))
    parser.add_argument("--mode", choices=["all", "code", "design", "release"], default="all")
    parser.add_argument("--write-request", action="store_true")
    args = parser.parse_args()

    project = resolve_project(args.project)
    skill_dir = Path(args.skill_dir)
    if not skill_dir.is_absolute():
        skill_dir = project / skill_dir
    result = review_governance(project, args.base, args.head, skill_dir.resolve(), args.mode, write_request=args.write_request)
    emit_json(result)
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
