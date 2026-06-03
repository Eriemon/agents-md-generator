from __future__ import annotations

from datetime import datetime
from fnmatch import fnmatch
import json
from pathlib import Path
import re
from typing import Any

from agents_common import SKIP_DIRS, read_json, script_command
from workspace_settings_policy import (
    SETTINGS_FOLDER,
    REMOTE_DEFAULT_SETTINGS,
    workspace_settings_contract,
    workspace_settings_location_reason,
)


DIR_MANAGER_DIR = Path("docs") / "dir_manager"
CURRENT_STRUCTURE = DIR_MANAGER_DIR / "current_structure.json"
PLANNED_STRUCTURE = DIR_MANAGER_DIR / "planned_structure.json"
DIR_MANAGER_MD = DIR_MANAGER_DIR / "DIR_MANAGER.md"
CHANGE_REVIEWS = DIR_MANAGER_DIR / "change_reviews"
HISTORY_DIR_MANAGER = DIR_MANAGER_DIR / "history_dir_manager"
CRITICAL_PREFIXES = {
    ".agents",
    ".settings",
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
TAKEOVER_PRESERVE_ROOT_FILES = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
}
ALLOWED_ROOT_FILES = sorted(TAKEOVER_PRESERVE_ROOT_FILES)
EPHEMERAL_ROOT_INPUT_FILE_RE = re.compile(
    r"^(?:answers|first-answers|recovery|session|stage|handoff|change|allowed-change|blocked-change|blocked-remote-change|blocked-remote-source-change)(?:-[a-z0-9._-]+)?\.json$",
    flags=re.IGNORECASE,
)
ALLOWED_ROOT_FILE_PATTERNS = (
    "answers.json",
    "*-answers.json",
    "change.json",
    "*-change.json",
    "session.json",
    "recovery.json",
    "handoff.json",
    "stage.json",
    "changelog.json",
    "experience-payload.json",
)
ROOT_OPTIONAL_WORK_DIRS = ("tests", "reports", "runs", "smoke")
ROOT_OPTIONAL_WORK_DIR_PREFIXES = ("smoke-",)
REMOTE_PROTECTED_PATH_CLASSES = [
    "workspace-root",
    "conda-environment-root",
    "conda-environment",
    "active-run-root",
    "active-run",
    "backup-run-root",
    "backup-run",
]
STRUCTURE_SKIP_FILE_PATTERNS = (
    ".agents/active-session.json",
    ".agents/session-*.json",
    ".agents/release-*.json",
)


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
            if any(fnmatch(rel, pattern) for pattern in STRUCTURE_SKIP_FILE_PATTERNS):
                continue
            files.append(rel)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": str(project),
        "directories": directories,
        "files": files,
        "skip_dirs": sorted(SKIP_DIRS),
    }


def dir_manager_doc(project: Path) -> str:
    review_command = script_command(project, "manage_dirs.py", "review", "<project>", "--input", "change.json")
    archive_command = script_command(project, "manage_dirs.py", "archive", "<project>", "--reason", "force-confirmed directory override")
    return "\n".join([
        "# Directory Manager",
        "",
        "This file is the strict gate for creating, moving, renaming, or deleting local project folders and remote deployment workspace folders.",
        "",
        "## Required Review",
        "- Read this file before changing folder structure.",
        f"- Run `{review_command}` before directory changes.",
        "- Do not move, rename, or delete governance folders without explicit user force-confirmation.",
        "- If review blocks a change, refuse default execution and explain the risk to the user.",
        "- If the user explicitly force-confirms a blocked change, archive old dir manager content under `history_dir_manager/YYYYMMDD-HHMMSS/` before changing structure.",
        "",
        "## Blocked By Default",
        "- Paths outside the project, absolute paths, parent traversal, wildcards, or shell-unsafe path characters.",
        "- New top-level folders not listed in `planned_structure.json`.",
        f"- Workspace engineering config files such as `project.local.json`, `project.remote.json`, or `server_list.local.json` outside `{SETTINGS_FOLDER}/`.",
        f"- Any remote attempt to copy `{SETTINGS_FOLDER}/*.local.json` such as `{SETTINGS_FOLDER}/server_list.local.json` into the remote workspace.",
        "- Remote deployment folders not listed in `planned_structure.json` remote_deployment planning.",
        "- Moving or deleting `.agents/`, `docs/dir_manager/`, `docs/handoff/`, or `docs/git_manager/`.",
        "- Moving source, tests, docs, dist, scripts, assets, references, or agents folders to unplanned locations.",
        "- Mixing generated output, release packages, or temporary references into source folders.",
        "",
        "## User Force Override",
        "- Explain why the request is unreasonable or risky.",
        "- State severe hazards such as broken tests, invalid release packages, stale AGENTS.md scopes, broken history links, or failed skill installation.",
        "- Ask the user to explicitly confirm forced directory structure modification.",
        f"- Run `{archive_command}` before applying a force-confirmed folder change.",
        "- Record confirmation and risk in the next handoff.",
        "",
    ])


def control_profile(project: Path) -> dict[str, Any]:
    data = read_json(project / ".agents" / "agents-control.json")
    return data if isinstance(data, dict) else {}


def display_rel(path: Path, project: Path) -> str:
    try:
        return path.relative_to(project).as_posix()
    except Exception:
        return path.resolve().as_posix()


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


def remote_environment_policy(project: Path) -> dict[str, Any]:
    profile = control_profile(project)
    contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract"), dict) else {}
    policy = contract.get("remote_environment_policy", {})
    return policy if isinstance(policy, dict) else {}


def remote_runtime_archive_policy(project: Path) -> dict[str, Any]:
    profile = control_profile(project)
    contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract"), dict) else {}
    policy = contract.get("remote_runtime_archive_policy", {})
    return policy if isinstance(policy, dict) else {}


def remote_deployment_plan(project: Path) -> dict[str, Any]:
    workspace = remote_structure(project)
    environment_policy = remote_environment_policy(project)
    runtime_policy = remote_runtime_archive_policy(project)
    planned = [] if workspace == "not configured" else [workspace]
    if workspace != "not configured":
        planned.append(f"{workspace.rstrip('/')}/{SETTINGS_FOLDER}/")
        conda_template = normalize_rel(str(environment_policy.get("path_template", "")).strip())
        active_template = normalize_rel(str(runtime_policy.get("active_path_template", "")).strip())
        backup_template = normalize_rel(str(runtime_policy.get("backup_path_template", "")).strip())
        for template in [conda_template, active_template, backup_template]:
            if template:
                planned.append(f"{workspace.rstrip('/')}/{template}")
        if backup_template:
            parts = backup_template.split("/")
            while len(parts) > 1:
                parts.pop()
                planned.append(f"{workspace.rstrip('/')}/{'/'.join(parts)}")
    planned = sorted(dict.fromkeys(planned))
    return {
        "workspace_root": workspace,
        "planned_structure": planned,
        "protected_paths": planned,
        "workspace_settings": workspace_settings_contract(),
        "conda_environment": {
            "status": environment_policy.get("status", "disabled"),
            "scope": environment_policy.get("scope", "remote-only"),
            "manager": environment_policy.get("manager", "conda-prefix"),
            "path_template": str(environment_policy.get("path_template", "")).strip(),
            "required_when_remote_configured": bool(environment_policy.get("required_when_remote_configured", True)),
        },
        "runtime_artifacts": {
            "status": runtime_policy.get("status", "disabled"),
            "active_path_template": str(runtime_policy.get("active_path_template", "")).strip(),
            "backup_path_template": str(runtime_policy.get("backup_path_template", "")).strip(),
            "run_id_required": bool(runtime_policy.get("run_id_required", True)),
            "archive_after_verification": bool(runtime_policy.get("archive_after_verification", False)),
            "archive_trigger": str(runtime_policy.get("archive_trigger", "")).strip(),
        },
        "protected_path_classes": list(REMOTE_PROTECTED_PATH_CLASSES),
        "require_review_for_all_mutations": True,
        "review_required_for": ["create", "move", "delete", "rename"],
        "block_on_failed_review": True,
        "force_override_requires_user_confirmation": True,
    }


def profile_layout_policy(project: Path) -> tuple[str, list[str], bool]:
    profile = control_profile(project)
    contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract"), dict) else {}
    primary = normalize_rel(str(contract.get("primary_project_root", "")).strip())
    if not primary:
        kind = str(profile.get("kind", "")).strip().lower()
        name = str(profile.get("name", "")).strip()
        skill_layout = profile.get("skill_layout", {}) if isinstance(profile.get("skill_layout"), dict) else {}
        if kind == "skill":
            primary = normalize_rel(str(skill_layout.get("path", "")).strip()) or (f"skills/{name}" if name else "")
        elif kind == "engineering" and name:
            primary = f"engineering/{name}"
    allowed = [
        normalize_rel(item)
        for item in contract.get("allowed_new_paths", [])
        if str(item).strip()
    ]
    if not allowed and primary:
        allowed = [primary, "tests", "smoke", "reports", "runs", "dist", "docs", ".agents", "ref"]
    enforce = bool(contract.get("enforce_primary_project_root", False) or primary)
    return primary, allowed, enforce


def planned_structure(project: Path) -> dict[str, Any]:
    primary_root, configured_paths, enforce_primary = profile_layout_policy(project)
    if configured_paths:
        current_dirs = set(configured_paths)
    else:
        current_dirs = {
            path.name + "/"
            for path in project.iterdir()
            if path.is_dir() and path.name not in SKIP_DIRS
        }
    current_dirs.update({
        f"{SETTINGS_FOLDER}/",
        "docs/",
        "docs/dir_manager/",
        "docs/dir_manager/history_dir_manager/",
        "docs/handoff/",
        "docs/experience/",
        "docs/development/",
        "docs/install_configuration/",
        "docs/git_manager/",
    })
    current_dirs = {item if item.endswith("/") else item + "/" for item in current_dirs}
    return {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "allowed_new_paths": sorted(current_dirs),
        "allowed_root_files": list(ALLOWED_ROOT_FILES),
        "root_optional_work_dirs": list(ROOT_OPTIONAL_WORK_DIRS),
        "root_optional_work_dir_prefixes": list(ROOT_OPTIONAL_WORK_DIR_PREFIXES),
        "workspace_settings": workspace_settings_contract(),
        "primary_project_root": f"{primary_root}/" if primary_root else "",
        "allowed_top_level_roots": sorted({
            normalize_rel(item).split("/", 1)[0] + "/"
            for item in current_dirs
            if normalize_rel(item)
        }),
        "enforce_primary_project_root": enforce_primary,
        "protected_paths": sorted(GOVERNANCE_PREFIXES),
        "review_required_for": ["create", "move", "delete", "rename"],
        "remote_deployment": remote_deployment_plan(project),
        "block_on_failed_review": True,
        "force_override_requires_user_confirmation": True,
        "force_override_archive": "docs/dir_manager/history_dir_manager/YYYYMMDD-HHMMSS",
    }


def load_planned(project: Path) -> dict[str, Any]:
    planned = read_json(project / PLANNED_STRUCTURE)
    return planned if isinstance(planned, dict) else {}


def allowed_parent_paths(planned: dict[str, Any]) -> set[str]:
    parents: set[str] = set()
    for item in planned.get("allowed_new_paths", []):
        normalized = normalize_rel(item)
        if not normalized:
            continue
        parts = normalized.split("/")
        for index in range(1, len(parts)):
            parents.add("/".join(parts[:index]))
    return parents


def configured_root_optional_work_dirs(planned: dict[str, Any]) -> set[str]:
    configured = planned.get("root_optional_work_dirs", [])
    values = {normalize_rel(item) for item in configured if normalize_rel(item)}
    return values or set(ROOT_OPTIONAL_WORK_DIRS)


def configured_root_optional_work_dir_prefixes(planned: dict[str, Any]) -> tuple[str, ...]:
    configured = planned.get("root_optional_work_dir_prefixes", [])
    values = tuple(normalize_rel(item) for item in configured if normalize_rel(item))
    return values or ROOT_OPTIONAL_WORK_DIR_PREFIXES


def root_optional_work_dir_match(path: str, planned: dict[str, Any]) -> bool:
    normalized = normalize_rel(path)
    if not normalized:
        return False
    top_level = normalized.split("/", 1)[0]
    if top_level in configured_root_optional_work_dirs(planned):
        return True
    return any(top_level.startswith(prefix) for prefix in configured_root_optional_work_dir_prefixes(planned))


def nested_workspace_artifact_reason(path: str, planned: dict[str, Any]) -> str | None:
    normalized = normalize_rel(path)
    primary_root = normalize_rel(str(planned.get("primary_project_root", "")).strip())
    if not normalized or not primary_root:
        return None
    prefix = primary_root.rstrip("/") + "/"
    if normalized == primary_root or not normalized.startswith(prefix):
        return None
    relative = normalized[len(prefix) :]
    components = [part for part in relative.split("/") if part]
    if not components:
        return None
    allowed_dirs = configured_root_optional_work_dirs(planned)
    prefixes = configured_root_optional_work_dir_prefixes(planned)
    for component in components:
        if component in allowed_dirs or any(component.startswith(prefix) for prefix in prefixes):
            return (
                f"workspace artifact directory must stay at the work-folder root, not under the primary project root: {normalized}"
            )
    return None


def allowed_path(path: str, planned: dict[str, Any]) -> bool:
    normalized = normalize_rel(path)
    if root_optional_work_dir_match(normalized, planned):
        return True
    allowed = [normalize_rel(item) for item in planned.get("allowed_new_paths", []) if str(item).strip()]
    parents = allowed_parent_paths(planned)
    if normalized in parents:
        return True
    return any(normalized == item or normalized.startswith(item.rstrip("/") + "/") for item in allowed)


def allowed_root_files(planned: dict[str, Any]) -> list[str]:
    configured = planned.get("allowed_root_files", [])
    if isinstance(configured, list):
        values = [str(item).strip() for item in configured if str(item).strip()]
        if values:
            return values
    return list(ALLOWED_ROOT_FILES)


def is_allowed_root_file(name: str, planned: dict[str, Any]) -> bool:
    normalized = str(name).strip()
    if normalized in set(allowed_root_files(planned)):
        return True
    return any(fnmatch(normalized, pattern) for pattern in ALLOWED_ROOT_FILE_PATTERNS)


def unapproved_root_files(current: dict[str, Any], planned: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for file_path in current.get("files", []):
        normalized = normalize_rel(file_path)
        if not normalized or "/" in normalized:
            continue
        if EPHEMERAL_ROOT_INPUT_FILE_RE.fullmatch(normalized):
            continue
        if not is_allowed_root_file(normalized, planned):
            explicit_reason = workspace_settings_location_reason(normalized)
            violations.append(explicit_reason or normalized)
    return violations


def workspace_settings_structure_violations(current: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for file_path in current.get("files", []):
        normalized = normalize_rel(file_path)
        if not normalized:
            continue
        reason = workspace_settings_location_reason(normalized)
        if reason:
            violations.append(reason)
    return sorted(dict.fromkeys(violations))


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
    for key in ["allowed_new_paths", "review_required_for", "allowed_root_files"]:
        if planned and not isinstance(planned.get(key), list):
            errors.append(f"{PLANNED_STRUCTURE.as_posix()}: `{key}` must be a list")
    if planned and not isinstance(planned.get("workspace_settings"), dict):
        errors.append(f"{PLANNED_STRUCTURE.as_posix()}: `workspace_settings` must be configured")
    if planned and not isinstance(planned.get("allowed_top_level_roots"), list):
        errors.append(f"{PLANNED_STRUCTURE.as_posix()}: `allowed_top_level_roots` must be a list")
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
        if not isinstance(remote.get("conda_environment"), dict):
            errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.conda_environment must be configured")
        if not isinstance(remote.get("runtime_artifacts"), dict):
            errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.runtime_artifacts must be configured")
        if not isinstance(remote.get("review_required_for"), list):
            errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.review_required_for must be a list")
        if not isinstance(remote.get("protected_path_classes"), list):
            errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.protected_path_classes must be a list")
        if remote.get("require_review_for_all_mutations") is not True:
            errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.require_review_for_all_mutations must be true")
        conda = remote.get("conda_environment", {}) if isinstance(remote.get("conda_environment"), dict) else {}
        runtime = remote.get("runtime_artifacts", {}) if isinstance(remote.get("runtime_artifacts"), dict) else {}
        if isinstance(conda, dict) and "path_template" not in conda:
            errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.conda_environment.path_template must be configured")
        if isinstance(runtime, dict):
            for key in ["active_path_template", "backup_path_template", "run_id_required", "archive_after_verification", "archive_trigger"]:
                if key not in runtime:
                    errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.runtime_artifacts.{key} must be configured")
    if current and planned:
        settings_policy = planned.get("workspace_settings", {}) if isinstance(planned.get("workspace_settings"), dict) else {}
        if settings_policy:
            if str(settings_policy.get("folder", "")).strip() != SETTINGS_FOLDER:
                errors.append(f"{PLANNED_STRUCTURE.as_posix()}: workspace_settings.folder must be `{SETTINGS_FOLDER}`")
            if str(settings_policy.get("local_default_file", "")).strip() != f"{SETTINGS_FOLDER}/project.local.json":
                errors.append(f"{PLANNED_STRUCTURE.as_posix()}: workspace_settings.local_default_file must be `{SETTINGS_FOLDER}/project.local.json`")
            if str(settings_policy.get("remote_default_file", "")).strip() != REMOTE_DEFAULT_SETTINGS:
                errors.append(f"{PLANNED_STRUCTURE.as_posix()}: workspace_settings.remote_default_file must be `{REMOTE_DEFAULT_SETTINGS}`")
            if bool(settings_policy.get("local_files_remote_blocked")) is not True:
                errors.append(f"{PLANNED_STRUCTURE.as_posix()}: workspace_settings.local_files_remote_blocked must be true")
        primary_root = normalize_rel(str(planned.get("primary_project_root", "")).strip())
        if planned.get("enforce_primary_project_root") and primary_root:
            if primary_root not in current.get("directories", []) and not any(path.startswith(primary_root + "/") for path in current.get("directories", [])):
                errors.append(f"{PLANNED_STRUCTURE.as_posix()}: required primary project root is missing: {primary_root}/")
        for directory in current.get("directories", []):
            normalized = normalize_rel(directory)
            if not normalized:
                continue
            nested_reason = nested_workspace_artifact_reason(normalized, planned)
            if nested_reason:
                errors.append(f"{CURRENT_STRUCTURE.as_posix()}: {nested_reason}")
                continue
            if not allowed_path(normalized, planned):
                errors.append(f"{CURRENT_STRUCTURE.as_posix()}: directory violates planned structure: {normalized}")
        errors.extend(f"{CURRENT_STRUCTURE.as_posix()}: {item}" for item in workspace_settings_structure_violations(current))
        for file_path in unapproved_root_files(current, planned):
            errors.append(f"{CURRENT_STRUCTURE.as_posix()}: root-level file violates planned structure: {file_path}")
    return {"project": str(project), "checked": checked, "errors": errors}


def init_dir_manager(project: Path) -> dict[str, Any]:
    target = project / DIR_MANAGER_DIR
    target.mkdir(parents=True, exist_ok=True)
    (project / CHANGE_REVIEWS).mkdir(parents=True, exist_ok=True)
    (project / HISTORY_DIR_MANAGER).mkdir(parents=True, exist_ok=True)
    if not (project / DIR_MANAGER_MD).exists():
        (project / DIR_MANAGER_MD).write_text(dir_manager_doc(project), encoding="utf-8")
    desired_planned = planned_structure(project)
    if not (project / PLANNED_STRUCTURE).exists():
        (project / PLANNED_STRUCTURE).write_text(
            json.dumps(desired_planned, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    else:
        planned = load_planned(project)
        primary_root, configured_paths, enforce_primary = profile_layout_policy(project)
        rewritten = dict(planned)
        changed = False
        remote_plan = desired_planned.get("remote_deployment", {})
        if rewritten.get("remote_deployment") != remote_plan:
            rewritten["remote_deployment"] = remote_plan
            changed = True
        if configured_paths:
            current_compare = dict(planned)
            desired_compare = dict(desired_planned)
            current_compare.pop("generated_at", None)
            desired_compare.pop("generated_at", None)
            if current_compare != desired_compare:
                rewritten = desired_planned
                changed = True
        else:
            current_allowed = [
                normalize_rel(item)
                for item in rewritten.get("allowed_new_paths", [])
                if str(item).strip()
            ]
            derived_top = sorted({item.split("/", 1)[0] + "/" for item in current_allowed if item})
            if rewritten.get("allowed_top_level_roots") != derived_top:
                rewritten["allowed_top_level_roots"] = derived_top
                changed = True
            if rewritten.get("primary_project_root", "") != primary_root:
                rewritten["primary_project_root"] = primary_root
                changed = True
            if rewritten.get("enforce_primary_project_root", False) != enforce_primary:
                rewritten["enforce_primary_project_root"] = enforce_primary
                changed = True
            if rewritten.get("allowed_root_files") != desired_planned.get("allowed_root_files"):
                rewritten["allowed_root_files"] = desired_planned.get("allowed_root_files", [])
                changed = True
        if changed:
            rewritten["generated_at"] = desired_planned["generated_at"]
            (project / PLANNED_STRUCTURE).write_text(json.dumps(rewritten, indent=2, sort_keys=True), encoding="utf-8")
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
