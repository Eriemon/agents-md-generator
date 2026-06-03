from __future__ import annotations

from pathlib import Path
import re
from typing import Any


SETTINGS_FOLDER = ".settings"
LOCAL_SETTINGS_SUFFIX = ".local.json"
REMOTE_SETTINGS_SUFFIX = ".remote.json"
LOCAL_DEFAULT_SETTINGS = f"{SETTINGS_FOLDER}/project.local.json"
REMOTE_DEFAULT_SETTINGS = f"{SETTINGS_FOLDER}/project.remote.json"
WORKSPACE_SETTINGS_LOCAL_RE = re.compile(r"^\.settings/[^/]+\.local\.json$", flags=re.IGNORECASE)
WORKSPACE_SETTINGS_REMOTE_RE = re.compile(r"^\.settings/[^/]+\.remote\.json$", flags=re.IGNORECASE)
WORKSPACE_SETTINGS_JSON_RE = re.compile(r"^\.settings/[^/]+\.json$", flags=re.IGNORECASE)
ROOT_SETTINGS_FILE_RE = re.compile(r"^[^/]+\.(?:local|remote)\.json$", flags=re.IGNORECASE)


def normalize_rel(raw: str) -> str:
    return re.sub(r"/+", "/", str(raw).replace("\\", "/").strip().strip("/"))


def workspace_settings_contract() -> dict[str, Any]:
    return {
        "folder": SETTINGS_FOLDER,
        "local_default_file": LOCAL_DEFAULT_SETTINGS,
        "remote_default_file": REMOTE_DEFAULT_SETTINGS,
        "local_file_pattern": f"{SETTINGS_FOLDER}/<name>{LOCAL_SETTINGS_SUFFIX}",
        "remote_file_pattern": f"{SETTINGS_FOLDER}/<name>{REMOTE_SETTINGS_SUFFIX}",
        "local_suffix": LOCAL_SETTINGS_SUFFIX,
        "remote_suffix": REMOTE_SETTINGS_SUFFIX,
        "local_files_remote_blocked": True,
    }


def is_workspace_settings_local(path: str) -> bool:
    return WORKSPACE_SETTINGS_LOCAL_RE.fullmatch(normalize_rel(path)) is not None


def is_workspace_settings_remote(path: str) -> bool:
    return WORKSPACE_SETTINGS_REMOTE_RE.fullmatch(normalize_rel(path)) is not None


def workspace_settings_path_classes(path: str) -> list[str]:
    normalized = normalize_rel(path)
    if not normalized.startswith(f"{SETTINGS_FOLDER}/"):
        return []
    classes = ["workspace-settings"]
    if is_workspace_settings_local(normalized):
        classes.append("workspace-settings-local")
    elif is_workspace_settings_remote(normalized):
        classes.append("workspace-settings-remote")
    elif normalized.endswith(".json"):
        classes.append("workspace-settings-json")
    return classes


def workspace_settings_location_reason(path: str) -> str | None:
    normalized = normalize_rel(path)
    if not normalized:
        return None
    if ROOT_SETTINGS_FILE_RE.fullmatch(normalized):
        return (
            f"workspace config `{normalized}` must move under `{SETTINGS_FOLDER}/` as "
            f"`{SETTINGS_FOLDER}/<name>{LOCAL_SETTINGS_SUFFIX}` or `{SETTINGS_FOLDER}/<name>{REMOTE_SETTINGS_SUFFIX}`"
        )
    if normalized.startswith(f"{SETTINGS_FOLDER}/"):
        if normalized.count("/") != 1:
            return f"workspace config `{normalized}` must live directly under `{SETTINGS_FOLDER}/`"
        if normalized.endswith(".json") and not WORKSPACE_SETTINGS_JSON_RE.fullmatch(normalized):
            return f"workspace config `{normalized}` must use a single filename directly under `{SETTINGS_FOLDER}/`"
        if normalized.endswith(".json") and not (
            WORKSPACE_SETTINGS_LOCAL_RE.fullmatch(normalized) or WORKSPACE_SETTINGS_REMOTE_RE.fullmatch(normalized)
        ):
            return (
                f"workspace settings json `{normalized}` must use `{LOCAL_SETTINGS_SUFFIX}` or "
                f"`{REMOTE_SETTINGS_SUFFIX}` suffix"
            )
    return None


def remote_workspace_settings_reason(path: str) -> str | None:
    normalized = normalize_rel(path)
    location = workspace_settings_location_reason(normalized)
    if location:
        return location
    if is_workspace_settings_local(normalized):
        return f"local-only workspace settings must never be copied to remote workspaces: `{normalized}`"
    if normalized.startswith(f"{SETTINGS_FOLDER}/") and normalized.endswith(".json") and not is_workspace_settings_remote(normalized):
        return f"remote workspace settings json must use `{REMOTE_SETTINGS_SUFFIX}` under `{SETTINGS_FOLDER}/`: `{normalized}`"
    return None


def discover_workspace_settings(root: Path) -> list[str]:
    settings_dir = root / SETTINGS_FOLDER
    if not settings_dir.is_dir():
        return []
    discovered: list[str] = []
    for path in sorted(settings_dir.glob("*.json")):
        if path.is_file():
            discovered.append(path.relative_to(root).as_posix())
    return discovered
