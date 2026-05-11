from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, resolve_project


PLACEHOLDER_RE = re.compile(r"{{[A-Z0-9_]+}}")
LOCAL_REFERENCE_RE = re.compile(r"G:[/\\]html|ref[/\\](agent-rules|html)", flags=re.IGNORECASE)


def quick_validate_path() -> Path:
    return Path.home() / ".codex" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py"


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
    result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False, env=env)
    return command_entry(name, argv, cwd, result)


def render_entry(skill_dir: Path, project: Path) -> dict[str, Any]:
    argv = [sys.executable, str(skill_dir / "scripts" / "render_agents.py"), str(project)]
    result = subprocess.run(argv, cwd=project, text=True, capture_output=True, check=False)
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
            if name == "audit_skill":
                for item in parsed.get("warnings", []) or []:
                    errors.append(f"{name} warning: {item}")
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


def evaluate(skill_dir: Path, project: Path) -> dict[str, Any]:
    repo_root = skill_dir.parent
    quick_validate = quick_validate_path()
    test_env = dict(os.environ, AGENTS_MD_EVALUATE_RUNNING="1")
    commands = [
        run_command("unit_tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], repo_root, test_env),
        run_command("quick_validate", [sys.executable, str(quick_validate), str(skill_dir)], repo_root),
        run_command("audit_skill", [sys.executable, str(skill_dir / "scripts" / "audit_skill.py"), str(skill_dir)], repo_root),
        run_command("verify_agents", [sys.executable, str(skill_dir / "scripts" / "verify_agents.py"), str(project)], repo_root),
        render_entry(skill_dir, project),
    ]
    errors = collect_errors(commands)
    return {
        "ok": not errors,
        "skill_dir": str(skill_dir),
        "project": str(project),
        "commands": commands,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full fact-level validation chain for agents-md-generator.")
    parser.add_argument("skill_dir", nargs="?", default=".")
    parser.add_argument("project", nargs="?", default=None)
    args = parser.parse_args()
    skill_dir = resolve_project(args.skill_dir)
    project = resolve_project(args.project) if args.project else skill_dir.parent.resolve()
    emit_json(evaluate(skill_dir, project))


if __name__ == "__main__":
    main()
