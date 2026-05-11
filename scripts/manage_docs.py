from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, read_json, resolve_project
from manage_dirs import init_dir_manager, verify_dir_manager


DOC_DIRS = [
    "docs/handoff",
    "docs/handoff/history_handoff",
    "docs/experience",
    "docs/experience/history_experience",
    "docs/development",
    "docs/install_configuration",
    "docs/git_manager",
    "docs/dir_manager",
    "docs/dir_manager/change_reviews",
    "docs/dir_manager/history_dir_manager",
]
STATE_PATH = ".agents/docs-governance-state.json"
HANDOFF_SECTIONS = [
    "Original Plan And Steps",
    "Current Step",
    "Problems",
    "Resolved Problems",
    "Remaining Problems",
    "Next Work",
    "Verification Evidence",
]


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def docs_root(project: Path) -> Path:
    return project / "docs"


def state_file(project: Path) -> Path:
    return project / STATE_PATH


def load_state(project: Path) -> dict[str, Any]:
    state = read_json(state_file(project))
    return state if isinstance(state, dict) else {}


def save_state(project: Path, state: dict[str, Any]) -> None:
    agents_dir = project / ".agents"
    agents_dir.mkdir(exist_ok=True)
    state_file(project).write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def list_lines(values: Any) -> str:
    if values is None or values == "":
        return "- Not recorded."
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        values = [str(values)]
    lines = [str(item).strip() for item in values if str(item).strip()]
    if not lines:
        return "- Not recorded."
    return "\n".join(f"- {line}" for line in lines)


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")
    return cleaned or "stage"


def default_handoff() -> str:
    return "\n".join([
        "# Handoff",
        "",
        "> Latest task handoff. Archive this file before writing the next handoff.",
        "",
        "## Original Plan And Steps",
        "- Not recorded yet.",
        "",
        "## Current Step",
        "- Not recorded yet.",
        "",
        "## Problems",
        "- Not recorded yet.",
        "",
        "## Resolved Problems",
        "- Not recorded yet.",
        "",
        "## Remaining Problems",
        "- Not recorded yet.",
        "",
        "## Next Work",
        "- Not recorded yet.",
        "",
        "## Verification Evidence",
        "- Not recorded yet.",
        "",
    ])


def install_configuration_doc() -> str:
    return "\n".join([
        "# Install Configuration",
        "",
        "## Skill Install Path",
        "- Install the skill folder into the target agent skill directory before use.",
        "",
        "## Codex Adapter",
        "- Keep `SKILL.md`, `agents/openai.yaml`, `references/`, `scripts/`, and `assets/` together.",
        "",
        "## Claude Adapter",
        "- Use `CLAUDE.md` compatibility shims only when requested; preserve existing non-managed files.",
        "",
        "## OpenClaw Adapter",
        "- Treat OpenClaw as an external adapter target and record project-specific setup here when confirmed.",
        "",
        "## Compatibility Shims",
        "- Create shims with the bundled compatibility script after AGENTS.md generation when requested.",
        "",
    ])


def git_manager_doc() -> str:
    return "\n".join([
        "# Git Manager",
        "",
        "## Workspace Management",
        "- Keep current development work in the working folder unless the user requests a separate worktree.",
        "",
        "## Branch Configuration",
        "- Master/main holds the editable source branch.",
        "- Release branches or release folders are recorded before packaging.",
        "",
        "## Release Configuration",
        "- Place installable releases under `dist/`.",
        "- Name installable release folders as `<name>-vx.x.x` and create a matching zip when required.",
        "",
        "## Current Version",
        "- Record the active version and release notes here during release preparation.",
        "",
    ])


def scaffold(project: Path) -> dict[str, Any]:
    created: list[str] = []
    for rel_path in DOC_DIRS:
        path = project / rel_path
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(rel_path)
    files = {
        "docs/handoff/HANDOFF.md": default_handoff(),
        "docs/install_configuration/INSTALL_CONFIGURATION.md": install_configuration_doc(),
        "docs/git_manager/GIT_MANAGER.md": git_manager_doc(),
    }
    for rel_path, content in files.items():
        path = project / rel_path
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(rel_path)
    state = load_state(project)
    state.setdefault("handoff_count", 0)
    state.setdefault("last_experience_at", 0)
    state["dir_manager_last_scan"] = datetime.now().isoformat(timespec="seconds")
    save_state(project, state)
    dir_result = init_dir_manager(project)
    created.extend(path for path in dir_result.get("written", []) if path not in created)
    return {"project": str(project), "created": created, "state": state}


def read_input(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    data = read_json(Path(path).resolve())
    if not isinstance(data, dict):
        raise SystemExit(f"Input must be a JSON object: {path}")
    return data


def rotate_handoff(project: Path) -> str | None:
    current = project / "docs" / "handoff" / "HANDOFF.md"
    if not current.exists():
        return None
    history = project / "docs" / "handoff" / "history_handoff"
    history.mkdir(parents=True, exist_ok=True)
    target = history / f"HANDOFF-{stamp()}.md"
    while target.exists():
        target = history / f"HANDOFF-{stamp()}-{len(list(history.glob('HANDOFF-*.md')))}.md"
    shutil.move(str(current), str(target))
    return str(target)


def handoff_markdown(data: dict[str, Any], count: int) -> str:
    return "\n".join([
        "# Handoff",
        "",
        f"- Handoff count: {count}",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Original Plan And Steps",
        list_lines(data.get("original_plan") or data.get("plan")),
        "",
        "## Current Step",
        list_lines(data.get("current_step")),
        "",
        "## Problems",
        list_lines(data.get("problems")),
        "",
        "## Resolved Problems",
        list_lines(data.get("resolved") or data.get("resolved_problems")),
        "",
        "## Remaining Problems",
        list_lines(data.get("remaining") or data.get("remaining_problems")),
        "",
        "## Next Work",
        list_lines(data.get("next") or data.get("next_work")),
        "",
        "## Verification Evidence",
        list_lines(data.get("verification") or data.get("verification_evidence")),
        "",
    ])


def write_handoff(project: Path, input_path: str | None) -> dict[str, Any]:
    scaffold(project)
    archived = rotate_handoff(project)
    state = load_state(project)
    count = int(state.get("handoff_count", 0)) + 1
    data = read_input(input_path)
    target = project / "docs" / "handoff" / "HANDOFF.md"
    target.write_text(handoff_markdown(data, count), encoding="utf-8")
    state["handoff_count"] = count
    save_state(project, state)
    result = {"project": str(project), "written": str(target), "archived": archived, "handoff_count": count}
    if count % 5 == 0:
        result["experience"] = write_experience(project, force=True)
    return result


def archive_experience_files(project: Path) -> list[str]:
    experience = project / "docs" / "experience"
    history_root = experience / "history_experience"
    candidates = [
        path for path in sorted(experience.glob("*.md"))
        if path.is_file()
    ]
    if not candidates:
        return []
    target_dir = history_root / stamp()
    target_dir.mkdir(parents=True, exist_ok=True)
    archived: list[str] = []
    for path in candidates:
        target = target_dir / path.name
        shutil.move(str(path), str(target))
        archived.append(str(target))
    return archived


def write_experience(project: Path, force: bool = False) -> dict[str, Any]:
    scaffold(project)
    state = load_state(project)
    count = int(state.get("handoff_count", 0))
    last = int(state.get("last_experience_at", 0))
    if not force and count - last < 5:
        return {"project": str(project), "skipped": True, "handoff_count": count, "last_experience_at": last}
    archived = archive_experience_files(project)
    latest = project / "docs" / "handoff" / "HANDOFF.md"
    latest_text = latest.read_text(encoding="utf-8", errors="ignore") if latest.exists() else "No latest handoff found."
    target = project / "docs" / "experience" / "docs-governance-lessons.md"
    target.write_text(
        "\n".join([
            "# Docs Governance Lessons",
            "",
            f"- Handoff count: {count}",
            f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "## Summary",
            "- Review the latest five handoffs and preserve reusable process lessons here.",
            "",
            "## Latest Handoff Snapshot",
            latest_text.strip(),
            "",
        ]),
        encoding="utf-8",
    )
    state["last_experience_at"] = count
    save_state(project, state)
    return {"project": str(project), "written": str(target), "archived": archived, "handoff_count": count}


def write_development(project: Path, stage: str, input_path: str | None) -> dict[str, Any]:
    scaffold(project)
    data = read_input(input_path)
    target = project / "docs" / "development" / f"{stamp()}-{slug(stage)}.md"
    target.write_text(
        "\n".join([
            f"# Development Stage: {stage}",
            "",
            f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
            f"- Version: {data.get('version', 'not recorded')}",
            "",
            "## Goal",
            list_lines(data.get("goal")),
            "",
            "## Completed Scope",
            list_lines(data.get("completed_scope")),
            "",
            "## Verification",
            list_lines(data.get("verification")),
            "",
            "## Artifacts",
            list_lines(data.get("artifacts")),
            "",
            "## Remaining Risks",
            list_lines(data.get("remaining_risks")),
            "",
        ]),
        encoding="utf-8",
    )
    return {"project": str(project), "written": str(target)}


def verify_docs(project: Path) -> dict[str, Any]:
    errors: list[str] = []
    checked: list[str] = []
    for rel_path in DOC_DIRS:
        checked.append(rel_path)
        if not (project / rel_path).is_dir():
            errors.append(f"missing docs governance directory: {rel_path}")
    required_files = [
        "docs/handoff/HANDOFF.md",
        "docs/install_configuration/INSTALL_CONFIGURATION.md",
        "docs/git_manager/GIT_MANAGER.md",
    ]
    for rel_path in required_files:
        checked.append(rel_path)
        if not (project / rel_path).is_file():
            errors.append(f"missing docs governance file: {rel_path}")
    handoff = project / "docs" / "handoff" / "HANDOFF.md"
    if handoff.exists():
        text = handoff.read_text(encoding="utf-8", errors="ignore")
        for section in HANDOFF_SECTIONS:
            if f"## {section}" not in text:
                errors.append(f"docs/handoff/HANDOFF.md: missing section ## {section}")
    dir_result = verify_dir_manager(project)
    checked.extend(dir_result["checked"])
    errors.extend(dir_result["errors"])
    return {"project": str(project), "checked": checked, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage AGENTS.md docs governance artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold_parser = subparsers.add_parser("scaffold")
    scaffold_parser.add_argument("project", nargs="?", default=".")

    handoff_parser = subparsers.add_parser("handoff")
    handoff_parser.add_argument("project", nargs="?", default=".")
    handoff_parser.add_argument("--input", default=None)

    experience_parser = subparsers.add_parser("experience")
    experience_parser.add_argument("project", nargs="?", default=".")
    experience_parser.add_argument("--force", action="store_true")

    development_parser = subparsers.add_parser("development")
    development_parser.add_argument("project", nargs="?", default=".")
    development_parser.add_argument("--stage", required=True)
    development_parser.add_argument("--input", default=None)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("project", nargs="?", default=".")

    args = parser.parse_args()
    project = resolve_project(args.project)
    if args.command == "scaffold":
        emit_json(scaffold(project))
    elif args.command == "handoff":
        emit_json(write_handoff(project, args.input))
    elif args.command == "experience":
        emit_json(write_experience(project, force=args.force))
    elif args.command == "development":
        emit_json(write_development(project, args.stage, args.input))
    elif args.command == "verify":
        result = verify_docs(project)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
