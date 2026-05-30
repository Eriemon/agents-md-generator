from __future__ import annotations

from typing import Any
from workspace_settings_policy import SETTINGS_FOLDER, remote_workspace_settings_reason, workspace_settings_path_classes


def normalize_rel(raw: str) -> str:
    return str(raw).replace("\\", "/").strip().strip("/")


def remote_workspace_root(remote_plan: dict[str, Any]) -> str:
    workspace = normalize_rel(str(remote_plan.get("workspace_root", "")).strip())
    return "" if workspace in {"", "not configured"} else workspace


def join_remote_workspace_path(workspace: str, relative: str) -> str:
    relative_norm = normalize_rel(relative)
    if not workspace:
        return relative_norm
    if not relative_norm:
        return workspace
    return f"{workspace.rstrip('/')}/{relative_norm}"


def allowed_remote_path(path: str, remote_plan: dict[str, Any]) -> bool:
    workspace = remote_workspace_root(remote_plan)
    if not workspace:
        return False
    normalized = join_remote_workspace_path(workspace, path)
    allowed = [normalize_rel(item) for item in remote_plan.get("planned_structure", []) if str(item).strip()]
    parents: set[str] = set()
    for item in allowed:
        parts = item.split("/")
        for index in range(1, len(parts)):
            parents.add("/".join(parts[:index]))
    if normalized in parents:
        return True
    for item in allowed:
        if normalized == item or normalized.startswith(item.rstrip("/") + "/"):
            return True
        if "<" in item and ">" in item:
            prefix = item.split("<", 1)[0].rstrip("/")
            if prefix and normalized.startswith(prefix + "/"):
                return True
    return False


def remote_path_classes(path: str, remote_plan: dict[str, Any]) -> list[str]:
    normalized = normalize_rel(path)
    if not normalized:
        return []
    classes = ["remote", *workspace_settings_path_classes(normalized)]
    runtime = remote_plan.get("runtime_artifacts", {}) if isinstance(remote_plan.get("runtime_artifacts"), dict) else {}
    conda = remote_plan.get("conda_environment", {}) if isinstance(remote_plan.get("conda_environment"), dict) else {}
    conda_template = normalize_rel(str(conda.get("path_template", "")).strip())
    active_template = normalize_rel(str(runtime.get("active_path_template", "")).strip())
    backup_template = normalize_rel(str(runtime.get("backup_path_template", "")).strip())
    conda_root = conda_template.split("<", 1)[0].rstrip("/") if conda_template else ""
    active_root = active_template.split("<", 1)[0].rstrip("/") if active_template else ""
    backup_root = backup_template.split("<", 1)[0].rstrip("/") if backup_template else ""
    if not path or normalized == remote_workspace_root(remote_plan):
        classes.append("workspace-root")
    if conda_root:
        if normalized == conda_root:
            classes.append("conda-environment-root")
        elif normalized.startswith(conda_root + "/"):
            classes.append("conda-environment")
    if active_root:
        if normalized == active_root:
            classes.append("active-run-root")
        elif normalized.startswith(active_root + "/"):
            classes.append("active-run")
    if backup_root:
        if normalized == backup_root:
            classes.append("backup-run-root")
        elif normalized.startswith(backup_root + "/"):
            classes.append("backup-run")
    return classes


def remote_runtime_reasons(action: str, path: str, target: str | None, remote_plan: dict[str, Any], artifact_state: str) -> list[str]:
    runtime = remote_plan.get("runtime_artifacts", {}) if isinstance(remote_plan.get("runtime_artifacts"), dict) else {}
    active_template = normalize_rel(str(runtime.get("active_path_template", "")).strip())
    backup_template = normalize_rel(str(runtime.get("backup_path_template", "")).strip())
    normalized_path = normalize_rel(path)
    normalized = normalize_rel(target if target else path)
    if not normalized:
        return []
    reasons: list[str] = []
    settings_reason = remote_workspace_settings_reason(normalized_path)
    if settings_reason:
        reasons.append(settings_reason)
    active_root = active_template.split("<run-id>", 1)[0].rstrip("/") if active_template else ""
    backup_root = backup_template.split("<run-id>", 1)[0].rstrip("/") if backup_template else ""
    if active_root and not normalized.startswith(active_root + "/") and normalized.split("/", 1)[0] not in {
        backup_root.split("/", 1)[0] if backup_root else "",
        ".conda",
        SETTINGS_FOLDER,
    }:
        reasons.append(f"remote runtime artifacts must stay under `{active_template}`; received `{normalized}`")
    if artifact_state == "verified" and backup_root and not normalized.startswith(backup_root + "/"):
        reasons.append(f"verified remote runtime artifacts must be archived under `{backup_template}`; received `{normalized}`")
    if artifact_state not in {"", "verified"} and backup_root and normalized.startswith(backup_root + "/"):
        reasons.append(f"unverified remote runtime artifacts must stay in `{active_template}` before archive; received `{normalized}`")
    protected_classes = set(str(item) for item in remote_plan.get("protected_path_classes", []) if str(item).strip())
    if action in {"delete", "move", "rename"}:
        destructive_classes = set(remote_path_classes(normalized_path, remote_plan))
        if destructive_classes & protected_classes:
            reasons.append(
                f"remote {action} is blocked for protected path classes {sorted(destructive_classes & protected_classes)} at `{normalized_path}`"
            )
    return reasons
