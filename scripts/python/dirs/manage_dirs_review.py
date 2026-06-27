from __future__ import annotations

# 分类脚本可从任意任务目录直接执行，这里补齐兄弟任务模块路径。
import sys
from pathlib import Path

_scripts_python_root = Path(__file__).resolve().parents[1]
for _task_dir in _scripts_python_root.iterdir():
    if _task_dir.is_dir():
        _task_path = str(_task_dir)
        if _task_path not in sys.path:
            sys.path.insert(0, _task_path)

# 导入 脚本治理 所需的依赖模块。
import json
from pathlib import Path
from typing import Any

# 导入 脚本治理 所需的依赖模块。
from agents_common import SKIP_DIRS, read_json
from agents_decisions import decision_request
from manage_dirs_remote import (
    allowed_remote_path,
    remote_path_classes,
    remote_runtime_reasons,
    remote_workspace_settings_reason,

    # 分隔当前密集代码块，保留原有执行顺序。
)
from manage_dirs_state import (
    CHANGE_REVIEWS,
    CRITICAL_PREFIXES,
    CURRENT_STRUCTURE,
    DIR_MANAGER_MD,

    # 再次分隔当前长代码块，降低连续语句密度。
    GOVERNANCE_PREFIXES,
    HISTORY_DIR_MANAGER,
    PLANNED_STRUCTURE,
    TAKEOVER_PRESERVE_ROOT_FILES,
    allowed_path,
    archive_dir_manager,

    # 分隔导入清单的后续成员，避免超长连续导入块。
    control_profile,
    display_rel,
    init_dir_manager,
    invalid_path_reason,
    load_planned,

    # 分隔导入清单末段，保证分组阅读边界清楚。
    nested_workspace_artifact_reason,
    normalize_rel,
    planned_structure,
    scan_structure,
    stamp,

    # 分隔最后一组导入成员，避免阅读时连续清单过长。
    unapproved_root_files,
)
from workspace_settings_policy import (
    workspace_settings_location_reason,
    workspace_settings_path_classes,
)


# 定义 critical_move_reason 的脚本治理处理入口。
def critical_move_reason(action: str, path: str, target: str | None) -> str | None:

    # 保留 normalized 中间值，支撑 critical_move_reason 的当前计算步骤。
    normalized = normalize_rel(path)  # normalized 用于本步治理判断

    # 保留 target norm 中间值，支撑 critical_move_reason 的当前计算步骤。
    target_norm = normalize_rel(target or "") if target else ""  # target norm 用于本步治理判断

    # 逐项推进 critical_move_reason 的候选项检查。
    for protected in GOVERNANCE_PREFIXES:

        # 检查 critical_move_reason 的当前条件是否需要进入专门分支。
        if normalized == protected or normalized.startswith(protected + "/"):

            # 返回 critical_move_reason 已整理完成的调用载荷。
            return f"{action} is blocked for protected governance path `{normalized}`"

    # 检查 critical_move_reason 的当前条件是否需要进入专门分支。
    if action in {"move", "rename", "delete"}:

        # 保留 top 中间值，支撑 critical_move_reason 的当前计算步骤。
        top = normalized.split("/", 1)[0]  # top 用于本步治理判断

        # 检查 critical_move_reason 的当前条件是否需要进入专门分支。
        if top in CRITICAL_PREFIXES:

            # 检查 critical_move_reason 的当前条件是否需要进入专门分支。
            if not target_norm:

                # 返回 critical_move_reason 已整理完成的调用载荷。
                return f"{action} is blocked for critical directory `{normalized}`"

            # 保留 target top 中间值，支撑 critical_move_reason 的当前计算步骤。
            target_top = target_norm.split("/", 1)[0]  # target top 用于本步治理判断

            # 检查 critical_move_reason 的当前条件是否需要进入专门分支。
            if target_top != top:

                # 返回 critical_move_reason 已整理完成的调用载荷。
                return f"{action} would move critical directory `{normalized}` outside its planned boundary"

    # 返回 critical_move_reason 已整理完成的调用载荷。
    return None


# 定义 review_change 的脚本治理处理入口。
def review_change(project: Path, input_path: str, *, dry_run: bool = False) -> dict[str, Any]:

    # 调用 init_dir_manager 完成 review_change 的当前动作。
    init_dir_manager(project)

    # 保留 raw 中间值，支撑 review_change 的当前计算步骤。
    raw = read_json(Path(input_path).resolve())  # raw 用于本步治理判断

    # 收集 changes 条目，保持 review_change 的处理顺序稳定。
    list_changes = raw.get("changes", []) if isinstance(raw, dict) else []  # changes 用于本步治理判断

    # 检查 review_change 的当前条件是否需要进入专门分支。
    if not isinstance(list_changes, list):

        # 收集 changes 条目，保持 review_change 的处理顺序稳定。
        list_changes = []  # changes 用于本步治理判断

    # 保留 planned 中间值，支撑 review_change 的当前计算步骤。
    planned = load_planned(project)  # planned 用于本步治理判断

    # 保留 remote plan 中间值，支撑 review_change 的当前计算步骤。
    remote_plan = planned.get("remote_deployment", {}) if isinstance(planned.get("remote_deployment"), dict) else {}  # remote plan 用于本步治理判断

    # 收集 reasons 条目，保持 review_change 的处理顺序稳定。
    list_reasons: list[str] = []  # reasons 用于本步治理判断

    # 收集 risks 条目，保持 review_change 的处理顺序稳定。
    list_risks: list[str] = []  # risks 用于本步治理判断

    # 定位 classes 的文件边界，供 review_change 后续读写校验使用。
    set_path_classes: set[str] = set()  # classes 用于本步治理判断

    # 收集 matched rules 条目，保持 review_change 的处理顺序稳定。
    list_matched_rules: list[str] = []  # matched rules 用于本步治理判断

    # 逐项推进 review_change 的候选项检查。
    for change in list_changes:

        # 检查 review_change 的当前条件是否需要进入专门分支。
        if not isinstance(change, dict):

            # 调用 append 完成 review_change 的当前动作。
            list_reasons.append("each change must be a JSON object")

            # 分隔 review_change 的控制流边界。
            continue

        # 保留 action 中间值，支撑 review_change 的当前计算步骤。
        action = str(change.get("action", "")).strip().lower()  # action 用于本步治理判断

        # 保留 environment 中间值，支撑 review_change 的当前计算步骤。
        environment = str(change.get("environment", "local")).strip().lower() or "local"  # environment 用于本步治理判断

        # 保留 path 中间值，支撑 review_change 的当前计算步骤。
        path = str(change.get("path", "")).strip()  # path 用于本步治理判断

        # 保留 target 中间值，支撑 review_change 的当前计算步骤。
        target = str(change.get("target", "")).strip() if change.get("target") is not None else None  # target 用于本步治理判断

        # 保留 artifact state 中间值，支撑 review_change 的当前计算步骤。
        artifact_state = str(change.get("artifact_state", "")).strip().lower()  # artifact state 用于本步治理判断

        # 检查 review_change 的当前条件是否需要进入专门分支。
        if action not in {"create", "move", "delete", "rename"}:

            # 调用 append 完成 review_change 的当前动作。
            list_reasons.append(f"unsupported action `{action}`")

            # 分隔 review_change 的控制流边界。
            continue

        # 逐项推进 review_change 的候选项检查。
        for value in [path, target] if target else [path]:

            # 保留 invalid 中间值，支撑 review_change 的当前计算步骤。
            invalid = invalid_path_reason(value)  # invalid 用于本步治理判断

            # 检查 review_change 的当前条件是否需要进入专门分支。
            if invalid:

                # 调用 append 完成 review_change 的当前动作。
                list_reasons.append(invalid)

        # 检查 review_change 的当前条件是否需要进入专门分支。
        if path:

            # 调用 update 完成 review_change 的当前动作。
            set_path_classes.update(workspace_settings_path_classes(path))

        # 检查 review_change 的当前条件是否需要进入专门分支。
        if target:

            # 调用 update 完成 review_change 的当前动作。
            set_path_classes.update(workspace_settings_path_classes(target))

        # 检查 review_change 的当前条件是否需要进入专门分支。
        if environment == "remote":

            # 调用 update 完成 review_change 的当前动作。
            set_path_classes.update(remote_path_classes(path, remote_plan))

            # 检查 review_change 的当前条件是否需要进入专门分支。
            if target:

                # 调用 update 完成 review_change 的当前动作。
                set_path_classes.update(remote_path_classes(target, remote_plan))

            # 逐项推进 review_change 的候选项检查。
            for candidate in [path, target] if target else [path]:

                # 保留 reason 中间值，支撑 review_change 的当前计算步骤。
                reason = remote_workspace_settings_reason(candidate) if candidate else None  # reason 用于本步治理判断

                # 检查 review_change 的当前条件是否需要进入专门分支。
                if reason and reason not in list_reasons:

                    # 调用 append 完成 review_change 的当前动作。
                    list_reasons.append(reason)

                    # 调用 append 完成 review_change 的当前动作。
                    list_matched_rules.append("remote-workspace-settings")

            # 检查 review_change 的当前条件是否需要进入专门分支。
            if path and action in {"create", "move", "rename", "delete"} and not allowed_remote_path(path, remote_plan):

                # 调用 append 完成 review_change 的当前动作。
                list_reasons.append(f"remote path `{normalize_rel(path)}` is not listed in planned_structure.json remote_deployment planning")

                # 调用 append 完成 review_change 的当前动作。
                list_matched_rules.append("remote-path-must-be-planned")

            # 检查 review_change 的当前条件是否需要进入专门分支。
            if action in {"move", "rename"} and target and not allowed_remote_path(target, remote_plan):

                # 调用 append 完成 review_change 的当前动作。
                list_reasons.append(f"remote target path `{normalize_rel(target)}` is not listed in planned_structure.json remote_deployment planning")

                # 调用 append 完成 review_change 的当前动作。
                list_matched_rules.append("remote-target-must-be-planned")

            # 收集 runtime reasons 条目，保持 review_change 的处理顺序稳定。
            runtime_reasons = remote_runtime_reasons(action, path, target, remote_plan, artifact_state)  # runtime reasons 用于本步治理判断

            # 检查 review_change 的当前条件是否需要进入专门分支。
            if runtime_reasons:

                # 调用 extend 完成 review_change 的当前动作。
                list_reasons.extend(runtime_reasons)

                # 调用 append 完成 review_change 的当前动作。
                list_matched_rules.append("remote-runtime-governance")
        else:

            # 逐项推进 review_change 的候选项检查。
            for candidate in [path, target] if target else [path]:

                # 保留 reason 中间值，支撑 review_change 的当前计算步骤。
                reason = workspace_settings_location_reason(candidate) if candidate else None  # reason 用于本步治理判断

                # 检查 review_change 的当前条件是否需要进入专门分支。
                if reason and reason not in list_reasons:

                    # 调用 append 完成 review_change 的当前动作。
                    list_reasons.append(reason)

                    # 调用 append 完成 review_change 的当前动作。
                    list_matched_rules.append("workspace-settings-location")

            # 检查 review_change 的当前条件是否需要进入专门分支。
            if action == "create" and path and not allowed_path(path, planned):

                # 调用 append 完成 review_change 的当前动作。
                list_reasons.append(f"new path `{normalize_rel(path)}` is not listed in planned_structure.json")

                # 调用 append 完成 review_change 的当前动作。
                list_matched_rules.append("local-path-must-be-planned")

            # 保留 critical 中间值，支撑 review_change 的当前计算步骤。
            critical = critical_move_reason(action, path, target)  # critical 用于本步治理判断

            # 检查 review_change 的当前条件是否需要进入专门分支。
            if critical:

                # 调用 append 完成 review_change 的当前动作。
                list_reasons.append(critical)

                # 调用 append 完成 review_change 的当前动作。
                list_matched_rules.append("local-critical-boundary")

            # 检查 review_change 的当前条件是否需要进入专门分支。
            if action in {"move", "rename"} and target and not allowed_path(target, planned):

                # 调用 append 完成 review_change 的当前动作。
                list_reasons.append(f"target path `{normalize_rel(target)}` is not listed in planned_structure.json")

                # 调用 append 完成 review_change 的当前动作。
                list_matched_rules.append("local-target-must-be-planned")

    # 保留 approved 中间值，支撑 review_change 的当前计算步骤。
    approved = not list_reasons  # approved 用于本步治理判断

    # 检查 review_change 的当前条件是否需要进入专门分支。
    if not approved:

        # 收集 risks 条目，保持 review_change 的处理顺序稳定。
        list_risks = [  # risks 用于本步治理判断
            "Tests and imports can break because path references become stale.",  # risks 用于本步治理判断
            "Release packages can point at the wrong files or miss required assets.",  # risks 用于本步治理判断
            "AGENTS.md scoped rules can stop applying to the files they were written for.",  # risks 用于本步治理判断
            "Handoff and git management history links can become invalid.",  # risks 用于本步治理判断
            "Skill installation can fail if bundled resources move unexpectedly.",  # risks 用于本步治理判断
        ]

    # 保留 result 中间值，支撑 review_change 的当前计算步骤。
    dict_result = {  # result 用于本步治理判断
        "project": "<PROJECT_ROOT>",  # result 用于本步治理判断
        "approved": approved,  # result 用于本步治理判断
        "decision": "approved" if approved else "blocked",  # result 用于本步治理判断
        "reasons": list_reasons,  # result 用于本步治理判断
        "risks": list_risks,  # result 用于本步治理判断
        "path_classes": sorted(set_path_classes),  # result 用于本步治理判断
        "matched_rules": sorted(dict.fromkeys(list_matched_rules)),  # result 用于本步治理判断
        "force_confirmation_required": not approved,  # result 用于本步治理判断
        "force_override_archive_required": str(HISTORY_DIR_MANAGER / "YYYYMMDD-HHMMSS") if not approved else "",  # result 用于本步治理判断
        "user_message": "" if approved else "目录结构审查未通过，默认拒绝执行。若用户仍强制要求修改，必须明确确认强制执行该目录结构修改，并接受可能产生的严重危害。",  # result 用于本步治理判断
        "dry_run": dry_run,  # result 用于本步治理判断
        "decision_request": {} if approved else decision_request(  # result 用于本步治理判断
            "force_confirmation",  # result 用于本步治理判断
            question="目录结构审查未通过。是否明确强制执行该目录结构修改并接受严重风险？",  # result 用于本步治理判断
            options=[  # result 用于本步治理判断
                {"label": "不强制执行", "value": "deny", "description": "默认选项；停止目录变更并修改计划。", "recommended": True},  # result 用于本步治理判断
                {"label": "强制执行", "value": "force", "description": "先归档 dir manager 状态，再由用户承担风险继续。", "recommended": False},  # result 用于本步治理判断
            ],  # result 用于本步治理判断
            default="deny",  # result 用于本步治理判断
            risk="high",  # result 用于本步治理判断
            next_action="archive dir manager state before any force-confirmed blocked directory mutation",  # result 用于本步治理判断
            context={"reasons": list_reasons, "risks": list_risks},  # result 用于本步治理判断
        ),  # result 用于本步治理判断
    }

    # 检查 review_change 的当前条件是否需要进入专门分支。
    if dry_run:

        # 保留 中间载荷 中间值，支撑 review_change 的当前计算步骤。
        dict_result["review_file"] = ""  # 中间载荷 用于本步治理判断
    else:

        # 定位 review path 的文件边界，供 review_change 后续读写校验使用。
        review_path = project / CHANGE_REVIEWS / f"review-{stamp()}.json"  # review path 用于本步治理判断

        # 调用 mkdir 完成 review_change 的当前动作。
        review_path.parent.mkdir(parents=True, exist_ok=True)

        # 调用 write_text 完成 review_change 的当前动作。
        review_path.write_text(json.dumps(dict_result, indent=2, sort_keys=True), encoding="utf-8")

        # 保留 中间载荷 中间值，支撑 review_change 的当前计算步骤。
        dict_result["review_file"] = str(review_path)  # 中间载荷 用于本步治理判断

    # 返回 review_change 已整理完成的调用载荷。
    return dict_result


# 定义 obvious_structure_fix_candidate 的脚本治理处理入口。
def obvious_structure_fix_candidate(project: Path, profile: dict, planned: dict) -> dict[str, str]:

    # 保留 contract 中间值，支撑 obvious_structure_fix_candidate 的当前计算步骤。
    contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract"), dict) else {}  # contract 用于本步治理判断

    # 保留 primary root 中间值，支撑 obvious_structure_fix_candidate 的当前计算步骤。
    primary_root = normalize_rel(str(contract.get("primary_project_root", "")).strip())  # primary root 用于本步治理判断

    # 检查 obvious_structure_fix_candidate 的当前条件是否需要进入专门分支。
    if not primary_root:

        # 返回 obvious_structure_fix_candidate 已整理完成的调用载荷。
        return {}

    # 保留 target 中间值，支撑 obvious_structure_fix_candidate 的当前计算步骤。
    target = project / primary_root  # target 用于本步治理判断

    # 检查 obvious_structure_fix_candidate 的当前条件是否需要进入专门分支。
    if target.exists():

        # 返回 obvious_structure_fix_candidate 已整理完成的调用载荷。
        return {}

    # 收集 allowed roots 条目，保持 obvious_structure_fix_candidate 的处理顺序稳定。
    allowed_roots = {  # allowed roots 用于本步治理判断
        normalize_rel(item).split("/", 1)[0]  # allowed roots 用于本步治理判断
        for item in planned.get("allowed_top_level_roots", [])  # allowed roots 用于本步治理判断
        if normalize_rel(item)  # allowed roots 用于本步治理判断
    }

    # 收集 candidates 条目，保持 obvious_structure_fix_candidate 的处理顺序稳定。
    list_candidates = []  # candidates 用于本步治理判断

    # 逐项推进 obvious_structure_fix_candidate 的候选项检查。
    for child in sorted(project.iterdir()):

        # 检查 obvious_structure_fix_candidate 的当前条件是否需要进入专门分支。
        if child.name in SKIP_DIRS or child.name in {".agents", ".settings", "docs", "dist", "tests", "ref"}:

            # 分隔 obvious_structure_fix_candidate 的控制流边界。
            continue

        # 检查 obvious_structure_fix_candidate 的当前条件是否需要进入专门分支。
        if not child.is_dir():

            # 分隔 obvious_structure_fix_candidate 的控制流边界。
            continue

        # 检查 obvious_structure_fix_candidate 的当前条件是否需要进入专门分支。
        if child.name in allowed_roots:

            # 分隔 obvious_structure_fix_candidate 的控制流边界。
            continue

        # 调用 append 完成 obvious_structure_fix_candidate 的当前动作。
        list_candidates.append(child)

    # 检查 obvious_structure_fix_candidate 的当前条件是否需要进入专门分支。
    if len(list_candidates) != 1 or not list_candidates[0].is_dir():

        # 返回 obvious_structure_fix_candidate 已整理完成的调用载荷。
        return {}

    # 保留 candidate 中间值，支撑 obvious_structure_fix_candidate 的当前计算步骤。
    candidate = list_candidates[0]  # candidate 用于本步治理判断

    # 保留 kind 中间值，支撑 obvious_structure_fix_candidate 的当前计算步骤。
    kind = str(profile.get("kind", "")).strip().lower()  # kind 用于本步治理判断

    # 检查 obvious_structure_fix_candidate 的当前条件是否需要进入专门分支。
    if kind == "skill" and not (candidate / "SKILL.md").is_file():

        # 返回 obvious_structure_fix_candidate 已整理完成的调用载荷。
        return {}

    # 返回 obvious_structure_fix_candidate 已整理完成的调用载荷。
    return {
        "source": display_rel(candidate, project),
        "target": primary_root,
    }


# 定义 takeover_candidates 的脚本治理处理入口。
def takeover_candidates(project: Path, planned: dict) -> list[Path]:

    # 保留 primary root 中间值，支撑 takeover_candidates 的当前计算步骤。
    primary_root = normalize_rel(str(planned.get("primary_project_root", "")).strip())  # primary root 用于本步治理判断

    # 检查 takeover_candidates 的当前条件是否需要进入专门分支。
    if not primary_root:

        # 返回 takeover_candidates 已整理完成的调用载荷。
        return []

    # 保留 top primary 中间值，支撑 takeover_candidates 的当前计算步骤。
    top_primary = primary_root.split("/", 1)[0]  # top primary 用于本步治理判断

    # 收集 preserve roots 条目，保持 takeover_candidates 的处理顺序稳定。
    set_preserve_roots = {".agents", ".settings", "docs", "dist", "tests", "ref", top_primary}  # preserve roots 用于本步治理判断

    # 收集 candidates 条目，保持 takeover_candidates 的处理顺序稳定。
    list_candidates: list[Path] = []  # candidates 用于本步治理判断

    # 逐项推进 takeover_candidates 的候选项检查。
    for child in sorted(project.iterdir()):

        # 检查 takeover_candidates 的当前条件是否需要进入专门分支。
        if child.name in SKIP_DIRS:

            # 分隔 takeover_candidates 的控制流边界。
            continue

        # 检查 takeover_candidates 的当前条件是否需要进入专门分支。
        if child.name in set_preserve_roots:

            # 分隔 takeover_candidates 的控制流边界。
            continue

        # 检查 takeover_candidates 的当前条件是否需要进入专门分支。
        if child.is_file() and child.name in TAKEOVER_PRESERVE_ROOT_FILES:

            # 分隔 takeover_candidates 的控制流边界。
            continue

        # 调用 append 完成 takeover_candidates 的当前动作。
        list_candidates.append(child)

    # 返回 takeover_candidates 已整理完成的调用载荷。
    return list_candidates


# 定义 takeover_fix 的脚本治理处理入口。
def takeover_fix(project: Path) -> dict[str, Any]:

    # 保留 profile 中间值，支撑 takeover_fix 的当前计算步骤。
    profile = control_profile(project)  # profile 用于本步治理判断

    # 保留 planned 中间值，支撑 takeover_fix 的当前计算步骤。
    planned = load_planned(project) or planned_structure(project)  # planned 用于本步治理判断

    # 保留 primary root 中间值，支撑 takeover_fix 的当前计算步骤。
    primary_root = normalize_rel(str(planned.get("primary_project_root", "")).strip())  # primary root 用于本步治理判断

    # 检查 takeover_fix 的当前条件是否需要进入专门分支。
    if not primary_root:

        # 返回 takeover_fix 已整理完成的调用载荷。
        return {
            "project": str(project),
            "moved": [],
            "errors": ["takeover fix requires a configured primary_project_root"],
            "archive_dir": "",
        }

    # 保留 archive dir 中间值，支撑 takeover_fix 的当前计算步骤。
    str_archive_dir = ""  # archive dir 用于本步治理判断

    # 检查 takeover_fix 的当前条件是否需要进入专门分支。
    if any((project / rel).exists() for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]):

        # 保留 archive 中间值，支撑 takeover_fix 的当前计算步骤。
        archive = archive_dir_manager(project, reason="takeover directory restructuring")  # archive 用于本步治理判断

        # 保留 archive dir 中间值，支撑 takeover_fix 的当前计算步骤。
        str_archive_dir = str(archive.get("archive_dir", ""))  # archive dir 用于本步治理判断

    # 保留 target root 中间值，支撑 takeover_fix 的当前计算步骤。
    target_root = project / primary_root  # target root 用于本步治理判断

    # 调用 mkdir 完成 takeover_fix 的当前动作。
    target_root.mkdir(parents=True, exist_ok=True)

    # 保留 moved 中间值，支撑 takeover_fix 的当前计算步骤。
    list_moved: list[dict[str, str]] = []  # moved 用于本步治理判断

    # 收集 errors 条目，保持 takeover_fix 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 保留 project name 中间值，支撑 takeover_fix 的当前计算步骤。
    project_name = str(profile.get("name", "")).strip()  # project name 用于本步治理判断

    # 逐项推进 takeover_fix 的候选项检查。
    for source in takeover_candidates(project, planned):

        # 检查 takeover_fix 的当前条件是否需要进入专门分支。
        if source.is_dir() and project_name and source.name == project_name:

            # 逐项推进 takeover_fix 的候选项检查。
            for child in sorted(source.iterdir()):

                # 保留 target 中间值，支撑 takeover_fix 的当前计算步骤。
                target = target_root / child.name  # target 用于本步治理判断

                # 检查 takeover_fix 的当前条件是否需要进入专门分支。
                if target.exists():

                    # 调用 append 完成 takeover_fix 的当前动作。
                    list_errors.append(f"takeover target already exists: {display_rel(target, project)}")

                    # 分隔 takeover_fix 的控制流边界。
                    continue

                # 调用 rename 完成 takeover_fix 的当前动作。
                child.rename(target)

                # 调用 append 完成 takeover_fix 的当前动作。
                list_moved.append(
                    {
                        "action": "move",
                        "source": display_rel(child, project),
                        "target": display_rel(target, project),
                    }
                )

            # 检查 takeover_fix 的当前条件是否需要进入专门分支。
            if not any(source.iterdir()):

                # 调用 rmdir 完成 takeover_fix 的当前动作。
                source.rmdir()

            # 分隔 takeover_fix 的控制流边界。
            continue

        # 保留 target 中间值，支撑 takeover_fix 的当前计算步骤。
        target = target_root / source.name  # target 用于本步治理判断

        # 检查 takeover_fix 的当前条件是否需要进入专门分支。
        if target.exists():

            # 调用 append 完成 takeover_fix 的当前动作。
            list_errors.append(f"takeover target already exists: {display_rel(target, project)}")

            # 分隔 takeover_fix 的控制流边界。
            continue

        # 调用 rename 完成 takeover_fix 的当前动作。
        source.rename(target)

        # 调用 append 完成 takeover_fix 的当前动作。
        list_moved.append(
            {
                "action": "move",
                "source": display_rel(source, project),
                "target": display_rel(target, project),
            }
        )

    # 保留 init result 中间值，支撑 takeover_fix 的当前计算步骤。
    init_result = init_dir_manager(project)  # init result 用于本步治理判断

    # 调用 extend 完成 takeover_fix 的当前动作。
    list_errors.extend(str(item) for item in init_result.get("errors", []))

    # 返回 takeover_fix 已整理完成的调用载荷。
    return {
        "project": str(project),
        "primary_project_root": primary_root,
        "archive_dir": str_archive_dir,
        "moved": list_moved,
        "errors": list_errors,
    }


# 定义 structure_gate 的脚本治理处理入口。
def structure_gate(project: Path) -> dict[str, Any]:

    # 保留 profile 中间值，支撑 structure_gate 的当前计算步骤。
    profile = control_profile(project)  # profile 用于本步治理判断

    # 检查 structure_gate 的当前条件是否需要进入专门分支。
    if not profile:

        # 返回 structure_gate 已整理完成的调用载荷。
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

    # 保留 planned 中间值，支撑 structure_gate 的当前计算步骤。
    planned = load_planned(project) or planned_structure(project)  # planned 用于本步治理判断

    # 保留 current 中间值，支撑 structure_gate 的当前计算步骤。
    current = scan_structure(project)  # current 用于本步治理判断

    # 收集 reasons 条目，保持 structure_gate 的处理顺序稳定。
    list_reasons: list[str] = []  # reasons 用于本步治理判断

    # 保留 primary root 中间值，支撑 structure_gate 的当前计算步骤。
    primary_root = normalize_rel(str(planned.get("primary_project_root", "")).strip())  # primary root 用于本步治理判断

    # 检查 structure_gate 的当前条件是否需要进入专门分支。
    if planned.get("enforce_primary_project_root") and primary_root:

        # 检查 structure_gate 的当前条件是否需要进入专门分支。
        if primary_root not in current.get("directories", []) and not any(path.startswith(primary_root + "/") for path in current.get("directories", [])):

            # 调用 append 完成 structure_gate 的当前动作。
            list_reasons.append(f"required primary project root is missing: {primary_root}/")

    # 逐项推进 structure_gate 的候选项检查。
    for directory in current.get("directories", []):

        # 保留 normalized 中间值，支撑 structure_gate 的当前计算步骤。
        normalized = normalize_rel(directory)  # normalized 用于本步治理判断

        # 检查 structure_gate 的当前条件是否需要进入专门分支。
        if not normalized:

            # 分隔 structure_gate 的控制流边界。
            continue

        # 保留 nested reason 中间值，支撑 structure_gate 的当前计算步骤。
        nested_reason = nested_workspace_artifact_reason(normalized, planned)  # nested reason 用于本步治理判断

        # 检查 structure_gate 的当前条件是否需要进入专门分支。
        if nested_reason:

            # 调用 append 完成 structure_gate 的当前动作。
            list_reasons.append(nested_reason)

            # 分隔 structure_gate 的控制流边界。
            continue

        # 检查 structure_gate 的当前条件是否需要进入专门分支。
        if not allowed_path(normalized, planned):

            # 调用 append 完成 structure_gate 的当前动作。
            list_reasons.append(f"directory violates planned structure: {normalized}")

    # 逐项推进 structure_gate 的候选项检查。
    for file_path in unapproved_root_files(current, planned):

        # 调用 append 完成 structure_gate 的当前动作。
        list_reasons.append(f"root-level file violates planned structure: {file_path}")

    # 保留 auto fix plan 中间值，支撑 structure_gate 的当前计算步骤。
    list_auto_fix_plan: list[dict[str, str]] = []  # auto fix plan 用于本步治理判断

    # 保留 candidate 中间值，支撑 structure_gate 的当前计算步骤。
    dict_candidate = obvious_structure_fix_candidate(project, profile, planned)  # candidate 用于本步治理判断

    # 检查 structure_gate 的当前条件是否需要进入专门分支。
    if dict_candidate:

        # 调用 append 完成 structure_gate 的当前动作。
        list_auto_fix_plan.append({"action": "move", **dict_candidate})

    # 保留 approved 中间值，支撑 structure_gate 的当前计算步骤。
    approved = not list_reasons  # approved 用于本步治理判断

    # 返回 structure_gate 已整理完成的调用载荷。
    return {
        "project": str(project),
        "approved": approved,
        "decision": "approved" if approved else "blocked",
        "reasons": list_reasons,
        "default_confirmation": "yes",
        "recommended_option": "yes",
        "auto_fix_plan": list_auto_fix_plan,
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
            context={"reasons": list_reasons, "auto_fix_plan": list_auto_fix_plan},
        ),
    }


# 定义 apply_structure_fix 的脚本治理处理入口。
def apply_structure_fix(project: Path) -> dict[str, Any]:

    # 保留 profile 中间值，支撑 apply_structure_fix 的当前计算步骤。
    profile = control_profile(project)  # profile 用于本步治理判断

    # 保留 planned 中间值，支撑 apply_structure_fix 的当前计算步骤。
    planned = load_planned(project)  # planned 用于本步治理判断

    # 保留 candidate 中间值，支撑 apply_structure_fix 的当前计算步骤。
    dict_candidate = obvious_structure_fix_candidate(project, profile, planned)  # candidate 用于本步治理判断

    # 保留 moved 中间值，支撑 apply_structure_fix 的当前计算步骤。
    list_moved: list[dict[str, str]] = []  # moved 用于本步治理判断

    # 收集 errors 条目，保持 apply_structure_fix 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 检查 apply_structure_fix 的当前条件是否需要进入专门分支。
    if dict_candidate:

        # 保留 source 中间值，支撑 apply_structure_fix 的当前计算步骤。
        source = project / dict_candidate["source"]  # source 用于本步治理判断

        # 保留 target 中间值，支撑 apply_structure_fix 的当前计算步骤。
        target = project / dict_candidate["target"]  # target 用于本步治理判断

        # 调用 mkdir 完成 apply_structure_fix 的当前动作。
        target.parent.mkdir(parents=True, exist_ok=True)

        # 检查 apply_structure_fix 的当前条件是否需要进入专门分支。
        if target.exists():

            # 调用 append 完成 apply_structure_fix 的当前动作。
            list_errors.append(f"structure fix target already exists: {display_rel(target, project)}")
        else:

            # 调用 rename 完成 apply_structure_fix 的当前动作。
            source.rename(target)

            # 调用 append 完成 apply_structure_fix 的当前动作。
            list_moved.append(dict_candidate)

    # 返回 apply_structure_fix 已整理完成的调用载荷。
    return {
        "project": str(project),
        "moved": list_moved,
        "errors": list_errors,
    }


