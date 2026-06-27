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
from typing import Any
from workspace_settings_policy import SETTINGS_FOLDER, remote_workspace_settings_reason, workspace_settings_path_classes


# 定义 normalize_rel 的脚本治理处理入口。
def normalize_rel(raw: str) -> str:

    # 返回 normalize_rel 已整理完成的调用载荷。
    return str(raw).replace("\\", "/").strip().strip("/")


# 定义 remote_workspace_root 的脚本治理处理入口。
def remote_workspace_root(remote_plan: dict[str, Any]) -> str:

    # 保留 workspace 中间值，支撑 remote_workspace_root 的当前计算步骤。
    str_workspace = normalize_rel(str(remote_plan.get("workspace_root", "")).strip())  # workspace 用于本步治理判断

    # 返回 remote_workspace_root 已整理完成的调用载荷。
    return "" if str_workspace in {"", "not configured"} else str_workspace


# 定义 join_remote_workspace_path 的脚本治理处理入口。
def join_remote_workspace_path(workspace: str, relative: str) -> str:

    # 保留 relative norm 中间值，支撑 join_remote_workspace_path 的当前计算步骤。
    str_relative_norm = normalize_rel(relative)  # relative norm 用于本步治理判断

    # 检查 join_remote_workspace_path 的当前条件是否需要进入专门分支。
    if not workspace:

        # 返回 join_remote_workspace_path 已整理完成的调用载荷。
        return str_relative_norm

    # 检查 join_remote_workspace_path 的当前条件是否需要进入专门分支。
    if not str_relative_norm:

        # 返回 join_remote_workspace_path 已整理完成的调用载荷。
        return workspace

    # 返回 join_remote_workspace_path 已整理完成的调用载荷。
    return f"{workspace.rstrip('/')}/{str_relative_norm}"


# 定义 allowed_remote_path 的脚本治理处理入口。
def allowed_remote_path(path: str, remote_plan: dict[str, Any]) -> bool:

    # 保留 workspace 中间值，支撑 allowed_remote_path 的当前计算步骤。
    str_workspace = remote_workspace_root(remote_plan)  # workspace 用于本步治理判断

    # 检查 allowed_remote_path 的当前条件是否需要进入专门分支。
    if not str_workspace:

        # 返回 allowed_remote_path 已整理完成的调用载荷。
        return False

    # 保留 normalized 中间值，支撑 allowed_remote_path 的当前计算步骤。
    str_normalized = join_remote_workspace_path(str_workspace, path)  # normalized 用于本步治理判断

    # 保留 allowed 中间值，支撑 allowed_remote_path 的当前计算步骤。
    allowed = [normalize_rel(item) for item in remote_plan.get("planned_structure", []) if str(item).strip()]  # allowed 用于本步治理判断

    # 收集 parents 条目，保持 allowed_remote_path 的处理顺序稳定。
    set_parents: set[str] = set()  # parents 用于本步治理判断

    # 逐项推进 allowed_remote_path 的候选项检查。
    for item in allowed:

        # 收集 parts 条目，保持 allowed_remote_path 的处理顺序稳定。
        parts = item.split("/")  # parts 用于本步治理判断

        # 逐项推进 allowed_remote_path 的候选项检查。
        for index in range(1, len(parts)):

            # 调用 add 完成 allowed_remote_path 的当前动作。
            set_parents.add("/".join(parts[:index]))

    # 检查 allowed_remote_path 的当前条件是否需要进入专门分支。
    if str_normalized in set_parents:

        # 返回 allowed_remote_path 已整理完成的调用载荷。
        return True

    # 逐项推进 allowed_remote_path 的候选项检查。
    for item in allowed:

        # 检查 allowed_remote_path 的当前条件是否需要进入专门分支。
        if str_normalized == item or str_normalized.startswith(item.rstrip("/") + "/"):

            # 返回 allowed_remote_path 已整理完成的调用载荷。
            return True

        # 检查 allowed_remote_path 的当前条件是否需要进入专门分支。
        if "<" in item and ">" in item:

            # 保留 prefix 中间值，支撑 allowed_remote_path 的当前计算步骤。
            prefix = item.split("<", 1)[0].rstrip("/")  # prefix 用于本步治理判断

            # 检查 allowed_remote_path 的当前条件是否需要进入专门分支。
            if prefix and str_normalized.startswith(prefix + "/"):

                # 返回 allowed_remote_path 已整理完成的调用载荷。
                return True

    # 返回 allowed_remote_path 已整理完成的调用载荷。
    return False


# 定义 remote_path_classes 的脚本治理处理入口。
def remote_path_classes(path: str, remote_plan: dict[str, Any]) -> list[str]:

    # 保留 normalized 中间值，支撑 remote_path_classes 的当前计算步骤。
    str_normalized = normalize_rel(path)  # normalized 用于本步治理判断

    # 检查 remote_path_classes 的当前条件是否需要进入专门分支。
    if not str_normalized:

        # 返回 remote_path_classes 已整理完成的调用载荷。
        return []

    # 收集 classes 条目，保持 remote_path_classes 的处理顺序稳定。
    list_classes = ["remote", *workspace_settings_path_classes(str_normalized)]  # classes 用于本步治理判断

    # 保留 runtime 中间值，支撑 remote_path_classes 的当前计算步骤。
    runtime = remote_plan.get("runtime_artifacts", {}) if isinstance(remote_plan.get("runtime_artifacts"), dict) else {}  # runtime 用于本步治理判断

    # 保留 conda 中间值，支撑 remote_path_classes 的当前计算步骤。
    conda = remote_plan.get("conda_environment", {}) if isinstance(remote_plan.get("conda_environment"), dict) else {}  # conda 用于本步治理判断

    # 保留 conda template 中间值，支撑 remote_path_classes 的当前计算步骤。
    str_conda_template = normalize_rel(str(conda.get("path_template", "")).strip())  # conda template 用于本步治理判断

    # 保留 active template 中间值，支撑 remote_path_classes 的当前计算步骤。
    str_active_template = normalize_rel(str(runtime.get("active_path_template", "")).strip())  # active template 用于本步治理判断

    # 保留 backup template 中间值，支撑 remote_path_classes 的当前计算步骤。
    str_backup_template = normalize_rel(str(runtime.get("backup_path_template", "")).strip())  # backup template 用于本步治理判断

    # 保留 conda root 中间值，支撑 remote_path_classes 的当前计算步骤。
    conda_root = str_conda_template.split("<", 1)[0].rstrip("/") if str_conda_template else ""  # conda root 用于本步治理判断

    # 保留 active root 中间值，支撑 remote_path_classes 的当前计算步骤。
    active_root = str_active_template.split("<", 1)[0].rstrip("/") if str_active_template else ""  # active root 用于本步治理判断

    # 保留 backup root 中间值，支撑 remote_path_classes 的当前计算步骤。
    backup_root = str_backup_template.split("<", 1)[0].rstrip("/") if str_backup_template else ""  # backup root 用于本步治理判断

    # 检查 remote_path_classes 的当前条件是否需要进入专门分支。
    if not path or str_normalized == remote_workspace_root(remote_plan):

        # 调用 append 完成 remote_path_classes 的当前动作。
        list_classes.append("workspace-root")

    # 检查 remote_path_classes 的当前条件是否需要进入专门分支。
    if conda_root:

        # 检查 remote_path_classes 的当前条件是否需要进入专门分支。
        if str_normalized == conda_root:

            # 调用 append 完成 remote_path_classes 的当前动作。
            list_classes.append("conda-environment-root")

        # 检查 remote_path_classes 的当前条件是否需要进入专门分支。
        elif str_normalized.startswith(conda_root + "/"):

            # 调用 append 完成 remote_path_classes 的当前动作。
            list_classes.append("conda-environment")

    # 检查 remote_path_classes 的当前条件是否需要进入专门分支。
    if active_root:

        # 检查 remote_path_classes 的当前条件是否需要进入专门分支。
        if str_normalized == active_root:

            # 调用 append 完成 remote_path_classes 的当前动作。
            list_classes.append("active-run-root")

        # 检查 remote_path_classes 的当前条件是否需要进入专门分支。
        elif str_normalized.startswith(active_root + "/"):

            # 调用 append 完成 remote_path_classes 的当前动作。
            list_classes.append("active-run")

    # 检查 remote_path_classes 的当前条件是否需要进入专门分支。
    if backup_root:

        # 检查 remote_path_classes 的当前条件是否需要进入专门分支。
        if str_normalized == backup_root:

            # 调用 append 完成 remote_path_classes 的当前动作。
            list_classes.append("backup-run-root")

        # 检查 remote_path_classes 的当前条件是否需要进入专门分支。
        elif str_normalized.startswith(backup_root + "/"):

            # 调用 append 完成 remote_path_classes 的当前动作。
            list_classes.append("backup-run")

    # 返回 remote_path_classes 已整理完成的调用载荷。
    return list_classes


# 定义 remote_runtime_reasons 的脚本治理处理入口。
def remote_runtime_reasons(action: str, path: str, target: str | None, remote_plan: dict[str, Any], artifact_state: str) -> list[str]:

    # 保留 runtime 中间值，支撑 remote_runtime_reasons 的当前计算步骤。
    """说明 remote_runtime_reasons 在 AGENTS 治理流程中的状态处理职责。
    
    数组契约:
        shape/维度: 本函数处理 AGENTS 状态、JSON 记录或文件路径，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict、list、str、Path 等 Python 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义以 AGENTS 治理配置和状态文件 schema 为准。
    """

    # 明确该赋值在脚本治理流程中的业务用途。
    runtime = remote_plan.get("runtime_artifacts", {}) if isinstance(remote_plan.get("runtime_artifacts"), dict) else {}  # runtime 用于本步治理判断

    # 保留 active template 中间值，支撑 remote_runtime_reasons 的当前计算步骤。
    str_active_template = normalize_rel(str(runtime.get("active_path_template", "")).strip())  # active template 用于本步治理判断

    # 保留 backup template 中间值，支撑 remote_runtime_reasons 的当前计算步骤。
    str_backup_template = normalize_rel(str(runtime.get("backup_path_template", "")).strip())  # backup template 用于本步治理判断

    # 定位 normalized path 的文件边界，供 remote_runtime_reasons 后续读写校验使用。
    str_normalized_path = normalize_rel(path)  # normalized path 用于本步治理判断

    # 保留 normalized 中间值，支撑 remote_runtime_reasons 的当前计算步骤。
    str_normalized = normalize_rel(target if target else path)  # normalized 用于本步治理判断

    # 检查 remote_runtime_reasons 的当前条件是否需要进入专门分支。
    if not str_normalized:

        # 返回 remote_runtime_reasons 已整理完成的调用载荷。
        return []

    # 收集 reasons 条目，保持 remote_runtime_reasons 的处理顺序稳定。
    list_reasons: list[str] = []  # reasons 用于本步治理判断

    # 保留 settings reason 中间值，支撑 remote_runtime_reasons 的当前计算步骤。
    settings_reason = remote_workspace_settings_reason(str_normalized_path)  # settings reason 用于本步治理判断

    # 检查 remote_runtime_reasons 的当前条件是否需要进入专门分支。
    if settings_reason:

        # 调用 append 完成 remote_runtime_reasons 的当前动作。
        list_reasons.append(settings_reason)

    # 保留 active root 中间值，支撑 remote_runtime_reasons 的当前计算步骤。
    active_root = str_active_template.split("<run-id>", 1)[0].rstrip("/") if str_active_template else ""  # active root 用于本步治理判断

    # 保留 backup root 中间值，支撑 remote_runtime_reasons 的当前计算步骤。
    backup_root = str_backup_template.split("<run-id>", 1)[0].rstrip("/") if str_backup_template else ""  # backup root 用于本步治理判断

    # 检查 remote_runtime_reasons 的当前条件是否需要进入专门分支。
    if active_root and not str_normalized.startswith(active_root + "/") and str_normalized.split("/", 1)[0] not in {
        backup_root.split("/", 1)[0] if backup_root else "",
        ".conda",
        SETTINGS_FOLDER,
    }:

        # 调用 append 完成 remote_runtime_reasons 的当前动作。
        list_reasons.append(f"remote runtime artifacts must stay under `{str_active_template}`; received `{str_normalized}`")

    # 检查 remote_runtime_reasons 的当前条件是否需要进入专门分支。
    if artifact_state == "verified" and backup_root and not str_normalized.startswith(backup_root + "/"):

        # 调用 append 完成 remote_runtime_reasons 的当前动作。
        list_reasons.append(f"verified remote runtime artifacts must be archived under `{str_backup_template}`; received `{str_normalized}`")

    # 检查 remote_runtime_reasons 的当前条件是否需要进入专门分支。
    if artifact_state not in {"", "verified"} and backup_root and str_normalized.startswith(backup_root + "/"):

        # 调用 append 完成 remote_runtime_reasons 的当前动作。
        list_reasons.append(f"unverified remote runtime artifacts must stay in `{str_active_template}` before archive; received `{str_normalized}`")

    # 收集 protected classes 条目，保持 remote_runtime_reasons 的处理顺序稳定。
    set_protected_classes = set(str(item) for item in remote_plan.get("protected_path_classes", []) if str(item).strip())  # protected classes 用于本步治理判断

    # 检查 remote_runtime_reasons 的当前条件是否需要进入专门分支。
    if action in {"delete", "move", "rename"}:

        # 收集 destructive classes 条目，保持 remote_runtime_reasons 的处理顺序稳定。
        set_destructive_classes = set(remote_path_classes(str_normalized_path, remote_plan))  # destructive classes 用于本步治理判断

        # 检查 remote_runtime_reasons 的当前条件是否需要进入专门分支。
        if set_destructive_classes & set_protected_classes:

            # 调用 append 完成 remote_runtime_reasons 的当前动作。
            list_reasons.append(
                f"remote {action} is blocked for protected path classes {sorted(set_destructive_classes & set_protected_classes)} at `{str_normalized_path}`"
            )

    # 返回 remote_runtime_reasons 已整理完成的调用载荷。
    return list_reasons


