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
from pathlib import Path
import re
from typing import Any


# 保留 SETTINGS FOLDER 中间值，支撑 模块入口 的当前计算步骤。
SETTINGS_FOLDER = ".settings"  # SETTINGS FOLDER 用于本步治理判断

# 保留 LOCAL SETTINGS SUFFIX 中间值，支撑 模块入口 的当前计算步骤。
LOCAL_SETTINGS_SUFFIX = ".local.json"  # LOCAL SETTINGS SUFFIX 用于本步治理判断

# 保留 REMOTE SETTINGS SUFFIX 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_SETTINGS_SUFFIX = ".remote.json"  # REMOTE SETTINGS SUFFIX 用于本步治理判断

# 保留 LOCAL DEFAULT SETTINGS 中间值，支撑 模块入口 的当前计算步骤。
LOCAL_DEFAULT_SETTINGS = f"{SETTINGS_FOLDER}/project.local.json"  # LOCAL DEFAULT SETTINGS 用于本步治理判断

# 保留 REMOTE DEFAULT SETTINGS 中间值，支撑 模块入口 的当前计算步骤。
REMOTE_DEFAULT_SETTINGS = f"{SETTINGS_FOLDER}/project.remote.json"  # REMOTE DEFAULT SETTINGS 用于本步治理判断

# 保留 WORKSPACE SETTINGS LOCAL RE 中间值，支撑 模块入口 的当前计算步骤。
WORKSPACE_SETTINGS_LOCAL_RE = re.compile(r"^\.settings/[^/]+\.local\.json$", flags=re.IGNORECASE)  # WORKSPACE SETTINGS LOCAL RE 用于本步治理判断

# 保留 WORKSPACE SETTINGS REMOTE RE 中间值，支撑 模块入口 的当前计算步骤。
WORKSPACE_SETTINGS_REMOTE_RE = re.compile(r"^\.settings/[^/]+\.remote\.json$", flags=re.IGNORECASE)  # WORKSPACE SETTINGS REMOTE RE 用于本步治理判断

# 保留 WORKSPACE SETTINGS JSON RE 中间值，支撑 模块入口 的当前计算步骤。
WORKSPACE_SETTINGS_JSON_RE = re.compile(r"^\.settings/[^/]+\.json$", flags=re.IGNORECASE)  # WORKSPACE SETTINGS JSON RE 用于本步治理判断

# 保留 ROOT SETTINGS FILE RE 中间值，支撑 模块入口 的当前计算步骤。
ROOT_SETTINGS_FILE_RE = re.compile(r"^[^/]+\.(?:local|remote)\.json$", flags=re.IGNORECASE)  # ROOT SETTINGS FILE RE 用于本步治理判断


# 定义 normalize_rel 的脚本治理处理入口。
def normalize_rel(raw: str) -> str:

    # 返回 normalize_rel 已整理完成的调用载荷。
    return re.sub(r"/+", "/", str(raw).replace("\\", "/").strip().strip("/"))


# 定义 workspace_settings_contract 的脚本治理处理入口。
def workspace_settings_contract() -> dict[str, Any]:

    # 返回 workspace_settings_contract 已整理完成的调用载荷。
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


# 定义 is_workspace_settings_local 的脚本治理处理入口。
def is_workspace_settings_local(path: str) -> bool:

    # 返回 is_workspace_settings_local 已整理完成的调用载荷。
    return WORKSPACE_SETTINGS_LOCAL_RE.fullmatch(normalize_rel(path)) is not None


# 定义 is_workspace_settings_remote 的脚本治理处理入口。
def is_workspace_settings_remote(path: str) -> bool:

    # 返回 is_workspace_settings_remote 已整理完成的调用载荷。
    return WORKSPACE_SETTINGS_REMOTE_RE.fullmatch(normalize_rel(path)) is not None


# 定义 workspace_settings_path_classes 的脚本治理处理入口。
def workspace_settings_path_classes(path: str) -> list[str]:

    # 保留 normalized 中间值，支撑 workspace_settings_path_classes 的当前计算步骤。
    str_normalized = normalize_rel(path)  # normalized 用于本步治理判断

    # 检查 workspace_settings_path_classes 的当前条件是否需要进入专门分支。
    if not str_normalized.startswith(f"{SETTINGS_FOLDER}/"):

        # 返回 workspace_settings_path_classes 已整理完成的调用载荷。
        return []

    # 收集 classes 条目，保持 workspace_settings_path_classes 的处理顺序稳定。
    list_classes = ["workspace-settings"]  # classes 用于本步治理判断

    # 检查 workspace_settings_path_classes 的当前条件是否需要进入专门分支。
    if is_workspace_settings_local(str_normalized):

        # 调用 append 完成 workspace_settings_path_classes 的当前动作。
        list_classes.append("workspace-settings-local")

    # 检查 workspace_settings_path_classes 的当前条件是否需要进入专门分支。
    elif is_workspace_settings_remote(str_normalized):

        # 调用 append 完成 workspace_settings_path_classes 的当前动作。
        list_classes.append("workspace-settings-remote")

    # 检查 workspace_settings_path_classes 的当前条件是否需要进入专门分支。
    elif str_normalized.endswith(".json"):

        # 调用 append 完成 workspace_settings_path_classes 的当前动作。
        list_classes.append("workspace-settings-json")

    # 返回 workspace_settings_path_classes 已整理完成的调用载荷。
    return list_classes


# 定义 workspace_settings_location_reason 的脚本治理处理入口。
def workspace_settings_location_reason(path: str) -> str | None:

    # 保留 normalized 中间值，支撑 workspace_settings_location_reason 的当前计算步骤。
    str_normalized = normalize_rel(path)  # normalized 用于本步治理判断

    # 检查 workspace_settings_location_reason 的当前条件是否需要进入专门分支。
    if not str_normalized:

        # 返回 workspace_settings_location_reason 已整理完成的调用载荷。
        return None

    # 检查 workspace_settings_location_reason 的当前条件是否需要进入专门分支。
    if ROOT_SETTINGS_FILE_RE.fullmatch(str_normalized):

        # 返回 workspace_settings_location_reason 已整理完成的调用载荷。
        return (
            f"workspace config `{str_normalized}` must move under `{SETTINGS_FOLDER}/` as "
            f"`{SETTINGS_FOLDER}/<name>{LOCAL_SETTINGS_SUFFIX}` or `{SETTINGS_FOLDER}/<name>{REMOTE_SETTINGS_SUFFIX}`"
        )

    # 检查 workspace_settings_location_reason 的当前条件是否需要进入专门分支。
    if str_normalized.startswith(f"{SETTINGS_FOLDER}/"):

        # 检查 workspace_settings_location_reason 的当前条件是否需要进入专门分支。
        if str_normalized.count("/") != 1:

            # 返回 workspace_settings_location_reason 已整理完成的调用载荷。
            return f"workspace config `{str_normalized}` must live directly under `{SETTINGS_FOLDER}/`"

        # 检查 workspace_settings_location_reason 的当前条件是否需要进入专门分支。
        if str_normalized.endswith(".json") and not WORKSPACE_SETTINGS_JSON_RE.fullmatch(str_normalized):

            # 返回 workspace_settings_location_reason 已整理完成的调用载荷。
            return f"workspace config `{str_normalized}` must use a single filename directly under `{SETTINGS_FOLDER}/`"

        # 检查 workspace_settings_location_reason 的当前条件是否需要进入专门分支。
        if str_normalized.endswith(".json") and not (
            WORKSPACE_SETTINGS_LOCAL_RE.fullmatch(str_normalized) or WORKSPACE_SETTINGS_REMOTE_RE.fullmatch(str_normalized)
        ):

            # 返回 workspace_settings_location_reason 已整理完成的调用载荷。
            return (
                f"workspace settings json `{str_normalized}` must use `{LOCAL_SETTINGS_SUFFIX}` or "
                f"`{REMOTE_SETTINGS_SUFFIX}` suffix"
            )

    # 返回 workspace_settings_location_reason 已整理完成的调用载荷。
    return None


# 定义 remote_workspace_settings_reason 的脚本治理处理入口。
def remote_workspace_settings_reason(path: str) -> str | None:

    # 保留 normalized 中间值，支撑 remote_workspace_settings_reason 的当前计算步骤。
    str_normalized = normalize_rel(path)  # normalized 用于本步治理判断

    # 保留 location 中间值，支撑 remote_workspace_settings_reason 的当前计算步骤。
    location = workspace_settings_location_reason(str_normalized)  # location 用于本步治理判断

    # 检查 remote_workspace_settings_reason 的当前条件是否需要进入专门分支。
    if location:

        # 返回 remote_workspace_settings_reason 已整理完成的调用载荷。
        return location

    # 检查 remote_workspace_settings_reason 的当前条件是否需要进入专门分支。
    if is_workspace_settings_local(str_normalized):

        # 返回 remote_workspace_settings_reason 已整理完成的调用载荷。
        return f"local-only workspace settings must never be copied to remote workspaces: `{str_normalized}`"

    # 检查 remote_workspace_settings_reason 的当前条件是否需要进入专门分支。
    if str_normalized.startswith(f"{SETTINGS_FOLDER}/") and str_normalized.endswith(".json") and not is_workspace_settings_remote(str_normalized):

        # 返回 remote_workspace_settings_reason 已整理完成的调用载荷。
        return f"remote workspace settings json must use `{REMOTE_SETTINGS_SUFFIX}` under `{SETTINGS_FOLDER}/`: `{str_normalized}`"

    # 返回 remote_workspace_settings_reason 已整理完成的调用载荷。
    return None


# 定义 discover_workspace_settings 的脚本治理处理入口。
def discover_workspace_settings(root: Path) -> list[str]:

    # 保留 settings dir 中间值，支撑 discover_workspace_settings 的当前计算步骤。
    settings_dir = root / SETTINGS_FOLDER  # settings dir 用于本步治理判断

    # 检查 discover_workspace_settings 的当前条件是否需要进入专门分支。
    if not settings_dir.is_dir():

        # 返回 discover_workspace_settings 已整理完成的调用载荷。
        return []

    # 保留 discovered 中间值，支撑 discover_workspace_settings 的当前计算步骤。
    list_discovered: list[str] = []  # discovered 用于本步治理判断

    # 逐项推进 discover_workspace_settings 的候选项检查。
    for path in sorted(settings_dir.glob("*.json")):

        # 检查 discover_workspace_settings 的当前条件是否需要进入专门分支。
        if path.is_file():

            # 调用 append 完成 discover_workspace_settings 的当前动作。
            list_discovered.append(path.relative_to(root).as_posix())

    # 返回 discover_workspace_settings 已整理完成的调用载荷。
    return list_discovered


