from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import SKIP_DIRS, emit_json, read_json, resolve_project


DIR_MANAGER_DIR = Path("docs") / "dir_manager"
CURRENT_STRUCTURE = DIR_MANAGER_DIR / "current_structure.json"
PLANNED_STRUCTURE = DIR_MANAGER_DIR / "planned_structure.json"
DIR_MANAGER_MD = DIR_MANAGER_DIR / "DIR_MANAGER.md"
CHANGE_REVIEWS = DIR_MANAGER_DIR / "change_reviews"
HISTORY_DIR_MANAGER = DIR_MANAGER_DIR / "history_dir_manager"
CRITICAL_PREFIXES = {
    ".agents",
    "agents",
    "assets",
    "dist",
    "docs",
    "docs/dir_manager",
    "docs/handoff",
    "docs/git_manager",
    "references",
    "scripts",
    "src",
    "tests",
}
GOVERNANCE_PREFIXES = {
    ".agents",
    "docs/dir_manager",
    "docs/handoff",
    "docs/git_manager",
}


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def normalize_rel(raw: str) -> str:
    value = str(raw).replace("\\", "/").strip().strip("/")
    return re.sub(r"/+", "/", value)


def invalid_path_reason(raw: str) -> str | None:
    value = str(raw).strip()
    normalized = value.replace("\\", "/")
    if not value:
        return "empty path is not allowed"
    if re.match(r"^[A-Za-z]:[/\\]", value) or normalized.startswith("/"):
        return f"path must stay inside the project and cannot be absolute: {value}"
    if ".." in normalized.split("/"):
        return f"path must not contain parent traversal: {value}"
    if any(char in value for char in "*?<>|"):
        return f"path must not contain wildcard or unsafe shell characters: {value}"
    return None


def is_skipped(path: Path, root: Path) -> bool:
    parts = path.relative_to(root).parts
    return bool(set(parts) & SKIP_DIRS)


def scan_structure(project: Path) -> dict[str, Any]:
    directories: list[str] = []
    files: list[str] = []
    for path in sorted(project.rglob("*")):
        if is_skipped(path, project):
            continue
        rel = path.relative_to(project).as_posix()
        if path.is_dir():
            directories.append(rel)
        elif path.is_file():
            files.append(rel)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project),
        "directories": directories,
        "files": files,
        "skip_dirs": sorted(SKIP_DIRS),
    }


def dir_manager_doc() -> str:
    return "\n".join([
        "# Directory Manager",
        "",
        "This file is the strict gate for creating, moving, renaming, or deleting local project folders and remote deployment workspace folders.",
        "",
        "## Required Review",
        "- Read this file before changing folder structure.",
        "- Run `python scripts/manage_dirs.py review <project> --input change.json` before directory changes.",
        "- Do not move, rename, or delete governance folders without explicit user force-confirmation.",
        "- If review blocks a change, refuse default execution and explain the risk to the user.",
        "- If the user explicitly force-confirms a blocked change, archive old dir manager content under `history_dir_manager/YYYYMMDD-HHMMSS/` before changing structure.",
        "",
        "## Blocked By Default",
        "- Paths outside the project, absolute paths, parent traversal, wildcards, or shell-unsafe path characters.",
        "- New top-level folders not listed in `planned_structure.json`.",
        "- Remote deployment folders not listed in `planned_structure.json` remote_deployment planning.",
        "- Moving or deleting `.agents/`, `docs/dir_manager/`, `docs/handoff/`, or `docs/git_manager/`.",
        "- Moving source, tests, docs, dist, scripts, assets, references, or agents folders to unplanned locations.",
        "- Mixing generated output, release packages, or temporary references into source folders.",
        "",
        "## User Force Override",
        "- Explain why the request is unreasonable or risky.",
        "- State severe hazards such as broken tests, invalid release packages, stale AGENTS.md scopes, broken history links, or failed skill installation.",
        "- Ask the user to explicitly confirm forced directory structure modification.",
        "- Run `python scripts/manage_dirs.py archive <project> --reason \"force-confirmed directory override\"` before applying a force-confirmed folder change.",
        "- Record confirmation and risk in the next handoff.",
        "",
    ])


def control_profile(project: Path) -> dict[str, Any]:
    data = read_json(project / ".agents" / "agents-control.json")
    return data if isinstance(data, dict) else {}


def remote_structure(project: Path) -> str:
    profile = control_profile(project)
    contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract"), dict) else {}
    raw = str(contract.get("remote", "")).strip()
    if not raw:
        return "not configured"
    if raw.lower() in {"none", "not configured"}:
        return "not configured"
    if "no remote workspace is configured" in raw.lower():
        return "not configured"
    return raw


def remote_deployment_plan(project: Path) -> dict[str, Any]:
    workspace = remote_structure(project)
    planned = [] if workspace == "not configured" else [workspace]
    return {
        "workspace_root": workspace,
        "planned_structure": planned,
        "protected_paths": planned,
        "review_required_for": ["create", "move", "delete", "rename"],
        "block_on_failed_review": True,
        "force_override_requires_user_confirmation": True,
    }


def planned_structure(project: Path) -> dict[str, Any]:
    current_dirs = {
        path.name + "/"
        for path in project.iterdir()
        if path.is_dir() and path.name not in SKIP_DIRS
    }
    current_dirs.update({
        "docs/",
        "docs/dir_manager/",
        "docs/dir_manager/history_dir_manager/",
        "docs/handoff/",
        "docs/experience/",
        "docs/development/",
        "docs/install_configuration/",
        "docs/git_manager/",
    })
    return {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "allowed_new_paths": sorted(current_dirs),
        "protected_paths": sorted(GOVERNANCE_PREFIXES),
        "review_required_for": ["create", "move", "delete", "rename"],
        "remote_deployment": remote_deployment_plan(project),
        "block_on_failed_review": True,
        "force_override_requires_user_confirmation": True,
        "force_override_archive": "docs/dir_manager/history_dir_manager/YYYYMMDD-HHMMSS",
    }


def init_dir_manager(project: Path) -> dict[str, Any]:
    target = project / DIR_MANAGER_DIR
    target.mkdir(parents=True, exist_ok=True)
    (project / CHANGE_REVIEWS).mkdir(parents=True, exist_ok=True)
    (project / HISTORY_DIR_MANAGER).mkdir(parents=True, exist_ok=True)
    if not (project / DIR_MANAGER_MD).exists():
        (project / DIR_MANAGER_MD).write_text(dir_manager_doc(), encoding="utf-8")
    if not (project / PLANNED_STRUCTURE).exists():
        (project / PLANNED_STRUCTURE).write_text(
            json.dumps(planned_structure(project), indent=2, sort_keys=True),
            encoding="utf-8",
        )
    else:
        planned = load_planned(project)
        remote_plan = remote_deployment_plan(project)
        if planned.get("remote_deployment") != remote_plan:
            planned["remote_deployment"] = remote_plan
            (project / PLANNED_STRUCTURE).write_text(json.dumps(planned, indent=2, sort_keys=True), encoding="utf-8")
    structure = scan_structure(project)
    (project / CURRENT_STRUCTURE).write_text(json.dumps(structure, indent=2, sort_keys=True), encoding="utf-8")
    verify = verify_dir_manager(project)
    return {"project": str(project), "written": [str(DIR_MANAGER_MD), str(CURRENT_STRUCTURE), str(PLANNED_STRUCTURE)], "errors": verify["errors"]}


def archive_dir_manager(project: Path, reason: str = "", review_file: str | None = None) -> dict[str, Any]:
    if not all((project / rel).exists() for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]):
        init_dir_manager(project)
    (project / HISTORY_DIR_MANAGER).mkdir(parents=True, exist_ok=True)
    archive_root = project / HISTORY_DIR_MANAGER / stamp()
    archive_root.mkdir(parents=True, exist_ok=False)
    archived: list[str] = []
    for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]:
        source = project / rel
        if source.is_file():
            target = archive_root / rel.name
            target.write_bytes(source.read_bytes())
            archived.append(str(target.relative_to(project).as_posix()))
    if (project / CHANGE_REVIEWS).is_dir():
        reviews_target = archive_root / CHANGE_REVIEWS.name
        reviews_target.mkdir(parents=True, exist_ok=True)
        for review in sorted((project / CHANGE_REVIEWS).glob("*.json")):
            target = reviews_target / review.name
            target.write_bytes(review.read_bytes())
            archived.append(str(target.relative_to(project).as_posix()))
    manifest = {
        "archived_at": datetime.now().isoformat(timespec="seconds"),
        "reason": reason or "force-confirmed directory override",
        "review_file": review_file or "",
        "archived_files": archived,
        "required_before": "applying any user force-confirmed blocked directory structure change",
    }
    manifest_path = archive_root / "archive_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    archived.append(str(manifest_path.relative_to(project).as_posix()))
    return {"project": str(project), "archive_dir": str(archive_root), "archived": archived}


def load_planned(project: Path) -> dict[str, Any]:
    planned = read_json(project / PLANNED_STRUCTURE)
    return planned if isinstance(planned, dict) else {}


def allowed_path(path: str, planned: dict[str, Any]) -> bool:
    normalized = normalize_rel(path)
    allowed = [normalize_rel(item) for item in planned.get("allowed_new_paths", []) if str(item).strip()]
    return any(normalized == item or normalized.startswith(item.rstrip("/") + "/") for item in allowed)


def critical_move_reason(action: str, path: str, target: str | None) -> str | None:
    normalized = normalize_rel(path)
    target_norm = normalize_rel(target or "") if target else ""
    for protected in GOVERNANCE_PREFIXES:
        if normalized == protected or normalized.startswith(protected + "/"):
            return f"{action} is blocked for protected governance path `{normalized}`"
    if action in {"move", "rename", "delete"}:
        top = normalized.split("/", 1)[0]
        if top in CRITICAL_PREFIXES:
            if not target_norm:
                return f"{action} is blocked for critical directory `{normalized}`"
            target_top = target_norm.split("/", 1)[0]
            if target_top != top:
                return f"{action} would move critical directory `{normalized}` outside its planned boundary"
    return None


def review_change(project: Path, input_path: str) -> dict[str, Any]:
    init_dir_manager(project)
    raw = read_json(Path(input_path).resolve())
    changes = raw.get("changes", []) if isinstance(raw, dict) else []
    if not isinstance(changes, list):
        changes = []
    planned = load_planned(project)
    reasons: list[str] = []
    risks: list[str] = []
    for change in changes:
        if not isinstance(change, dict):
            reasons.append("each change must be a JSON object")
            continue
        action = str(change.get("action", "")).strip().lower()
        path = str(change.get("path", "")).strip()
        target = str(change.get("target", "")).strip() if change.get("target") is not None else None
        if action not in {"create", "move", "delete", "rename"}:
            reasons.append(f"unsupported action `{action}`")
            continue
        for value in [path, target] if target else [path]:
            invalid = invalid_path_reason(value)
            if invalid:
                reasons.append(invalid)
        if action == "create" and path and not allowed_path(path, planned):
            reasons.append(f"new path `{normalize_rel(path)}` is not listed in planned_structure.json")
        critical = critical_move_reason(action, path, target)
        if critical:
            reasons.append(critical)
        if action in {"move", "rename"} and target and not allowed_path(target, planned):
            reasons.append(f"target path `{normalize_rel(target)}` is not listed in planned_structure.json")
    approved = not reasons
    if not approved:
        risks = [
            "Tests and imports can break because path references become stale.",
            "Release packages can point at the wrong files or miss required assets.",
            "AGENTS.md scoped rules can stop applying to the files they were written for.",
            "Handoff, experience, and git management history links can become invalid.",
            "Skill installation can fail if bundled resources move unexpectedly.",
        ]
    result = {
        "project": str(project),
        "approved": approved,
        "decision": "approved" if approved else "blocked",
        "reasons": reasons,
        "risks": risks,
        "force_confirmation_required": not approved,
        "force_override_archive_required": str(HISTORY_DIR_MANAGER / "YYYYMMDD-HHMMSS") if not approved else "",
        "user_message": "" if approved else "目录结构审查未通过，默认拒绝执行。若用户仍强制要求修改，必须明确确认强制执行该目录结构修改，并接受可能产生的严重危害。",
    }
    review_path = project / CHANGE_REVIEWS / f"review-{stamp()}.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    result["review_file"] = str(review_path)
    return result


def verify_json(path: Path, errors: list[str]) -> dict[str, Any]:
    data = read_json(path)
    if not isinstance(data, dict) or not data:
        errors.append(f"{path.as_posix()}: missing or invalid JSON object")
        return {}
    return data


def verify_dir_manager(project: Path) -> dict[str, Any]:
    errors: list[str] = []
    checked = [
        str(DIR_MANAGER_DIR.as_posix()),
        str(CHANGE_REVIEWS.as_posix()),
        str(HISTORY_DIR_MANAGER.as_posix()),
        str(DIR_MANAGER_MD.as_posix()),
        str(CURRENT_STRUCTURE.as_posix()),
        str(PLANNED_STRUCTURE.as_posix()),
    ]
    for rel in [DIR_MANAGER_DIR, CHANGE_REVIEWS, HISTORY_DIR_MANAGER]:
        if not (project / rel).is_dir():
            errors.append(f"missing dir manager directory: {rel.as_posix()}")
    for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]:
        if not (project / rel).is_file():
            errors.append(f"missing dir manager file: {rel.as_posix()}")
    current = verify_json(project / CURRENT_STRUCTURE, errors) if (project / CURRENT_STRUCTURE).exists() else {}
    planned = verify_json(project / PLANNED_STRUCTURE, errors) if (project / PLANNED_STRUCTURE).exists() else {}
    for key in ["directories", "files"]:
        if current and not isinstance(current.get(key), list):
            errors.append(f"{CURRENT_STRUCTURE.as_posix()}: `{key}` must be a list")
    for key in ["allowed_new_paths", "review_required_for"]:
        if planned and not isinstance(planned.get(key), list):
            errors.append(f"{PLANNED_STRUCTURE.as_posix()}: `{key}` must be a list")
    if planned and not planned.get("block_on_failed_review", False):
        errors.append(f"{PLANNED_STRUCTURE.as_posix()}: block_on_failed_review must be true")
    if planned and not planned.get("force_override_archive"):
        errors.append(f"{PLANNED_STRUCTURE.as_posix()}: force_override_archive must be configured")
    remote = planned.get("remote_deployment") if planned else None
    if planned and not isinstance(remote, dict):
        errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment must be configured")
    if isinstance(remote, dict):
        if not remote.get("workspace_root"):
            errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.workspace_root must be configured or `not configured`")
        if not isinstance(remote.get("planned_structure"), list):
            errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.planned_structure must be a list")
        if not isinstance(remote.get("review_required_for"), list):
            errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.review_required_for must be a list")
    return {"project": str(project), "checked": checked, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="Review and verify strict project directory management gates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("project", nargs="?", default=".")
    scan_parser.add_argument("--write", action="store_true")

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("project", nargs="?", default=".")

    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("project", nargs="?", default=".")
    review_parser.add_argument("--input", required=True)

    archive_parser = subparsers.add_parser("archive")
    archive_parser.add_argument("project", nargs="?", default=".")
    archive_parser.add_argument("--reason", default="force-confirmed directory override")
    archive_parser.add_argument("--review-file", default="")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("project", nargs="?", default=".")

    args = parser.parse_args()
    project = resolve_project(args.project)
    if args.command == "scan":
        structure = scan_structure(project)
        if args.write:
            (project / DIR_MANAGER_DIR).mkdir(parents=True, exist_ok=True)
            (project / CURRENT_STRUCTURE).write_text(json.dumps(structure, indent=2, sort_keys=True), encoding="utf-8")
        emit_json(structure)
    elif args.command == "init":
        emit_json(init_dir_manager(project))
    elif args.command == "review":
        result = review_change(project, args.input)
        emit_json(result)
        if not result["approved"]:
            raise SystemExit(1)
    elif args.command == "archive":
        emit_json(archive_dir_manager(project, reason=args.reason, review_file=args.review_file))
    elif args.command == "verify":
        result = verify_dir_manager(project)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
