from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agents_common import SKIP_DIRS, read_json
from agents_decisions import decision_request
from manage_dirs_remote import (
    allowed_remote_path,
    remote_path_classes,
    remote_runtime_reasons,
    remote_workspace_settings_reason,
)
from manage_dirs_state import (
    CHANGE_REVIEWS,
    CRITICAL_PREFIXES,
    CURRENT_STRUCTURE,
    DIR_MANAGER_MD,
    GOVERNANCE_PREFIXES,
    HISTORY_DIR_MANAGER,
    PLANNED_STRUCTURE,
    TAKEOVER_PRESERVE_ROOT_FILES,
    allowed_path,
    archive_dir_manager,
    control_profile,
    display_rel,
    init_dir_manager,
    invalid_path_reason,
    load_planned,
    nested_workspace_artifact_reason,
    normalize_rel,
    planned_structure,
    scan_structure,
    stamp,
    unapproved_root_files,
)
from workspace_settings_policy import (
    workspace_settings_location_reason,
    workspace_settings_path_classes,
)


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


def review_change(project: Path, input_path: str, *, dry_run: bool = False) -> dict[str, Any]:
    init_dir_manager(project)
    raw = read_json(Path(input_path).resolve())
    changes = raw.get("changes", []) if isinstance(raw, dict) else []
    if not isinstance(changes, list):
        changes = []
    planned = load_planned(project)
    remote_plan = planned.get("remote_deployment", {}) if isinstance(planned.get("remote_deployment"), dict) else {}
    reasons: list[str] = []
    risks: list[str] = []
    path_classes: set[str] = set()
    matched_rules: list[str] = []
    for change in changes:
        if not isinstance(change, dict):
            reasons.append("each change must be a JSON object")
            continue
        action = str(change.get("action", "")).strip().lower()
        environment = str(change.get("environment", "local")).strip().lower() or "local"
        path = str(change.get("path", "")).strip()
        target = str(change.get("target", "")).strip() if change.get("target") is not None else None
        artifact_state = str(change.get("artifact_state", "")).strip().lower()
        if action not in {"create", "move", "delete", "rename"}:
            reasons.append(f"unsupported action `{action}`")
            continue
        for value in [path, target] if target else [path]:
            invalid = invalid_path_reason(value)
            if invalid:
                reasons.append(invalid)
        if path:
            path_classes.update(workspace_settings_path_classes(path))
        if target:
            path_classes.update(workspace_settings_path_classes(target))
        if environment == "remote":
            path_classes.update(remote_path_classes(path, remote_plan))
            if target:
                path_classes.update(remote_path_classes(target, remote_plan))
            for candidate in [path, target] if target else [path]:
                reason = remote_workspace_settings_reason(candidate) if candidate else None
                if reason and reason not in reasons:
                    reasons.append(reason)
                    matched_rules.append("remote-workspace-settings")
            if path and action in {"create", "move", "rename", "delete"} and not allowed_remote_path(path, remote_plan):
                reasons.append(f"remote path `{normalize_rel(path)}` is not listed in planned_structure.json remote_deployment planning")
                matched_rules.append("remote-path-must-be-planned")
            if action in {"move", "rename"} and target and not allowed_remote_path(target, remote_plan):
                reasons.append(f"remote target path `{normalize_rel(target)}` is not listed in planned_structure.json remote_deployment planning")
                matched_rules.append("remote-target-must-be-planned")
            runtime_reasons = remote_runtime_reasons(action, path, target, remote_plan, artifact_state)
            if runtime_reasons:
                reasons.extend(runtime_reasons)
                matched_rules.append("remote-runtime-governance")
        else:
            for candidate in [path, target] if target else [path]:
                reason = workspace_settings_location_reason(candidate) if candidate else None
                if reason and reason not in reasons:
                    reasons.append(reason)
                    matched_rules.append("workspace-settings-location")
            if action == "create" and path and not allowed_path(path, planned):
                reasons.append(f"new path `{normalize_rel(path)}` is not listed in planned_structure.json")
                matched_rules.append("local-path-must-be-planned")
            critical = critical_move_reason(action, path, target)
            if critical:
                reasons.append(critical)
                matched_rules.append("local-critical-boundary")
            if action in {"move", "rename"} and target and not allowed_path(target, planned):
                reasons.append(f"target path `{normalize_rel(target)}` is not listed in planned_structure.json")
                matched_rules.append("local-target-must-be-planned")
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
        "path_classes": sorted(path_classes),
        "matched_rules": sorted(dict.fromkeys(matched_rules)),
        "force_confirmation_required": not approved,
        "force_override_archive_required": str(HISTORY_DIR_MANAGER / "YYYYMMDD-HHMMSS") if not approved else "",
        "user_message": "" if approved else "目录结构审查未通过，默认拒绝执行。若用户仍强制要求修改，必须明确确认强制执行该目录结构修改，并接受可能产生的严重危害。",
        "dry_run": dry_run,
        "decision_request": {} if approved else decision_request(
            "force_confirmation",
            question="目录结构审查未通过。是否明确强制执行该目录结构修改并接受严重风险？",
            options=[
                {"label": "不强制执行", "value": "deny", "description": "默认选项；停止目录变更并修改计划。", "recommended": True},
                {"label": "强制执行", "value": "force", "description": "先归档 dir manager 状态，再由用户承担风险继续。", "recommended": False},
            ],
            default="deny",
            risk="high",
            next_action="archive dir manager state before any force-confirmed blocked directory mutation",
            context={"reasons": reasons, "risks": risks},
        ),
    }
    if dry_run:
        result["review_file"] = ""
    else:
        review_path = project / CHANGE_REVIEWS / f"review-{stamp()}.json"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
        result["review_file"] = str(review_path)
    return result


def obvious_structure_fix_candidate(project: Path, profile: dict, planned: dict) -> dict[str, str]:
    contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract"), dict) else {}
    primary_root = normalize_rel(str(contract.get("primary_project_root", "")).strip())
    if not primary_root:
        return {}
    target = project / primary_root
    if target.exists():
        return {}
    allowed_roots = {
        normalize_rel(item).split("/", 1)[0]
        for item in planned.get("allowed_top_level_roots", [])
        if normalize_rel(item)
    }
    candidates = []
    for child in sorted(project.iterdir()):
        if child.name in SKIP_DIRS or child.name in {".agents", ".settings", "docs", "dist", "tests", "ref"}:
            continue
        if not child.is_dir():
            continue
        if child.name in allowed_roots:
            continue
        candidates.append(child)
    if len(candidates) != 1 or not candidates[0].is_dir():
        return {}
    candidate = candidates[0]
    kind = str(profile.get("kind", "")).strip().lower()
    if kind == "skill" and not (candidate / "SKILL.md").is_file():
        return {}
    return {
        "source": display_rel(candidate, project),
        "target": primary_root,
    }


def takeover_candidates(project: Path, planned: dict) -> list[Path]:
    primary_root = normalize_rel(str(planned.get("primary_project_root", "")).strip())
    if not primary_root:
        return []
    top_primary = primary_root.split("/", 1)[0]
    preserve_roots = {".agents", ".settings", "docs", "dist", "tests", "ref", top_primary}
    candidates: list[Path] = []
    for child in sorted(project.iterdir()):
        if child.name in SKIP_DIRS:
            continue
        if child.name in preserve_roots:
            continue
        if child.is_file() and child.name in TAKEOVER_PRESERVE_ROOT_FILES:
            continue
        candidates.append(child)
    return candidates


def takeover_fix(project: Path) -> dict[str, Any]:
    profile = control_profile(project)
    planned = load_planned(project) or planned_structure(project)
    primary_root = normalize_rel(str(planned.get("primary_project_root", "")).strip())
    if not primary_root:
        return {
            "project": str(project),
            "moved": [],
            "errors": ["takeover fix requires a configured primary_project_root"],
            "archive_dir": "",
        }

    archive_dir = ""
    if any((project / rel).exists() for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]):
        archive = archive_dir_manager(project, reason="takeover directory restructuring")
        archive_dir = str(archive.get("archive_dir", ""))

    target_root = project / primary_root
    target_root.mkdir(parents=True, exist_ok=True)
    moved: list[dict[str, str]] = []
    errors: list[str] = []
    project_name = str(profile.get("name", "")).strip()
    for source in takeover_candidates(project, planned):
        if source.is_dir() and project_name and source.name == project_name:
            for child in sorted(source.iterdir()):
                target = target_root / child.name
                if target.exists():
                    errors.append(f"takeover target already exists: {display_rel(target, project)}")
                    continue
                child.rename(target)
                moved.append(
                    {
                        "action": "move",
                        "source": display_rel(child, project),
                        "target": display_rel(target, project),
                    }
                )
            if not any(source.iterdir()):
                source.rmdir()
            continue
        target = target_root / source.name
        if target.exists():
            errors.append(f"takeover target already exists: {display_rel(target, project)}")
            continue
        source.rename(target)
        moved.append(
            {
                "action": "move",
                "source": display_rel(source, project),
                "target": display_rel(target, project),
            }
        )

    init_result = init_dir_manager(project)
    errors.extend(str(item) for item in init_result.get("errors", []))
    return {
        "project": str(project),
        "primary_project_root": primary_root,
        "archive_dir": archive_dir,
        "moved": moved,
        "errors": errors,
    }


def structure_gate(project: Path) -> dict[str, Any]:
    profile = control_profile(project)
    if not profile:
        return {
            "project": str(project),
            "approved": True,
            "decision": "approved",
            "reasons": [],
            "default_confirmation": "yes",
            "recommended_option": "yes",
            "auto_fix_plan": [],
            "requires_user_confirmation": False,
            "user_message": "",
            "decision_request": {},
        }
    planned = load_planned(project) or planned_structure(project)
    current = scan_structure(project)
    reasons: list[str] = []
    primary_root = normalize_rel(str(planned.get("primary_project_root", "")).strip())
    if planned.get("enforce_primary_project_root") and primary_root:
        if primary_root not in current.get("directories", []) and not any(path.startswith(primary_root + "/") for path in current.get("directories", [])):
            reasons.append(f"required primary project root is missing: {primary_root}/")
    for directory in current.get("directories", []):
        normalized = normalize_rel(directory)
        if not normalized:
            continue
        nested_reason = nested_workspace_artifact_reason(normalized, planned)
        if nested_reason:
            reasons.append(nested_reason)
            continue
        if not allowed_path(normalized, planned):
            reasons.append(f"directory violates planned structure: {normalized}")
    for file_path in unapproved_root_files(current, planned):
        reasons.append(f"root-level file violates planned structure: {file_path}")
    auto_fix_plan: list[dict[str, str]] = []
    candidate = obvious_structure_fix_candidate(project, profile, planned)
    if candidate:
        auto_fix_plan.append({"action": "move", **candidate})
    approved = not reasons
    return {
        "project": str(project),
        "approved": approved,
        "decision": "approved" if approved else "blocked",
        "reasons": reasons,
        "default_confirmation": "yes",
        "recommended_option": "yes",
        "auto_fix_plan": auto_fix_plan,
        "requires_user_confirmation": not approved,
        "user_message": "" if approved else "目录结构不符合治理契约，默认应先按规范整理/迁移。若继续，请明确确认是否执行结构修复，默认推荐“是”。",
        "decision_request": {} if approved else decision_request(
            "structure_normalization",
            question="目录结构不符合治理契约。是否按推荐方案执行结构修复？",
            options=[
                {"label": "是，执行修复", "value": "yes", "description": "默认选项；按 auto_fix_plan 或人工整理方案恢复治理结构。", "recommended": True},
                {"label": "否，暂停", "value": "no", "description": "保留当前结构，暂停会修改工作区结构的操作。", "recommended": False},
            ],
            default="yes",
            risk="high",
            next_action="run structure fix or manually normalize the work folder, then rerun structure-gate",
            context={"reasons": reasons, "auto_fix_plan": auto_fix_plan},
        ),
    }


def apply_structure_fix(project: Path) -> dict[str, Any]:
    profile = control_profile(project)
    planned = load_planned(project)
    candidate = obvious_structure_fix_candidate(project, profile, planned)
    moved: list[dict[str, str]] = []
    errors: list[str] = []
    if candidate:
        source = project / candidate["source"]
        target = project / candidate["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            errors.append(f"structure fix target already exists: {display_rel(target, project)}")
        else:
            source.rename(target)
            moved.append(candidate)
    return {
        "project": str(project),
        "moved": moved,
        "errors": errors,
    }
