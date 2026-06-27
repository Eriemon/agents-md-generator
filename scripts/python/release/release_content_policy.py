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
from typing import Any

# 保留 POLICY VERSION 中间值，支撑 模块入口 的当前计算步骤。
POLICY_VERSION = "2026-05-26-v2"  # POLICY VERSION 用于本步治理判断

# 保留 TOP LEVEL FILE MODE 中间值，支撑 模块入口 的当前计算步骤。
TOP_LEVEL_FILE_MODE = "allow-nonforbidden-files"  # TOP LEVEL FILE MODE 用于本步治理判断

# 保留 ALLOWED TOP LEVEL FILES 中间值，支撑 模块入口 的当前计算步骤。
ALLOWED_TOP_LEVEL_FILES = {  # ALLOWED TOP LEVEL FILES 用于本步治理判断
    "README.md",  # ALLOWED TOP LEVEL FILES 用于本步治理判断
    "SKILL.md",  # ALLOWED TOP LEVEL FILES 用于本步治理判断
    "VERSION",  # ALLOWED TOP LEVEL FILES 用于本步治理判断
}

# 保留 IGNORED TOP LEVEL FILES 中间值，支撑 模块入口 的当前计算步骤。
IGNORED_TOP_LEVEL_FILES = {  # IGNORED TOP LEVEL FILES 用于本步治理判断
    "RELEASE_RECEIPT.json",  # IGNORED TOP LEVEL FILES 用于本步治理判断
}

# 保留 ALLOWED TOP LEVEL DIRS 中间值，支撑 模块入口 的当前计算步骤。
ALLOWED_TOP_LEVEL_DIRS = {  # ALLOWED TOP LEVEL DIRS 用于本步治理判断
    "agents",  # ALLOWED TOP LEVEL DIRS 用于本步治理判断
    "assets",  # ALLOWED TOP LEVEL DIRS 用于本步治理判断
    "config",  # ALLOWED TOP LEVEL DIRS 用于本步治理判断
    "evals",  # ALLOWED TOP LEVEL DIRS 用于本步治理判断
    "integration",  # ALLOWED TOP LEVEL DIRS 用于本步治理判断
    "references",  # ALLOWED TOP LEVEL DIRS 用于本步治理判断
    "runtime",  # ALLOWED TOP LEVEL DIRS 用于本步治理判断
    "scripts",  # ALLOWED TOP LEVEL DIRS 用于本步治理判断
}

# 保留 FORBIDDEN EXACT NAMES 中间值，支撑 模块入口 的当前计算步骤。
FORBIDDEN_EXACT_NAMES = {  # FORBIDDEN EXACT NAMES 用于本步治理判断
    "tests",  # FORBIDDEN EXACT NAMES 用于本步治理判断
    "test",  # FORBIDDEN EXACT NAMES 用于本步治理判断
    "reports",  # FORBIDDEN EXACT NAMES 用于本步治理判断
    "runs",  # FORBIDDEN EXACT NAMES 用于本步治理判断
    "_smoke_runs",  # FORBIDDEN EXACT NAMES 用于本步治理判断
    "__pycache__",  # FORBIDDEN EXACT NAMES 用于本步治理判断
    ".pytest_cache",  # FORBIDDEN EXACT NAMES 用于本步治理判断
    ".mypy_cache",  # FORBIDDEN EXACT NAMES 用于本步治理判断
    ".ruff_cache",  # FORBIDDEN EXACT NAMES 用于本步治理判断
}

# 保留 FORBIDDEN PREFIXES 中间值，支撑 模块入口 的当前计算步骤。
FORBIDDEN_PREFIXES = ("smoke",)  # FORBIDDEN PREFIXES 用于本步治理判断

# 保留 FORBIDDEN SUFFIXES 中间值，支撑 模块入口 的当前计算步骤。
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}  # FORBIDDEN SUFFIXES 用于本步治理判断


# 定义 is_forbidden_component 的脚本治理处理入口。
def is_forbidden_component(name: str) -> bool:

    # 保留 lowered 中间值，支撑 is_forbidden_component 的当前计算步骤。
    lowered = name.strip().lower()  # lowered 用于本步治理判断

    # 检查 is_forbidden_component 的当前条件是否需要进入专门分支。
    if not lowered:

        # 返回 is_forbidden_component 已整理完成的调用载荷。
        return False

    # 检查 is_forbidden_component 的当前条件是否需要进入专门分支。
    if lowered in FORBIDDEN_EXACT_NAMES:

        # 返回 is_forbidden_component 已整理完成的调用载荷。
        return True

    # 返回 is_forbidden_component 已整理完成的调用载荷。
    return any(lowered.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)


# 定义 is_forbidden_relative_path 的脚本治理处理入口。
def is_forbidden_relative_path(relative_path: str) -> bool:

    # 保留 normalized 中间值，支撑 is_forbidden_relative_path 的当前计算步骤。
    normalized = relative_path.replace("\\", "/").strip().strip("/")  # normalized 用于本步治理判断

    # 检查 is_forbidden_relative_path 的当前条件是否需要进入专门分支。
    if not normalized:

        # 返回 is_forbidden_relative_path 已整理完成的调用载荷。
        return False

    # 收集 parts 条目，保持 is_forbidden_relative_path 的处理顺序稳定。
    parts = [part for part in normalized.split("/") if part]  # parts 用于本步治理判断

    # 检查 is_forbidden_relative_path 的当前条件是否需要进入专门分支。
    if any(is_forbidden_component(part) for part in parts):

        # 返回 is_forbidden_relative_path 已整理完成的调用载荷。
        return True

    # 保留 suffix 中间值，支撑 is_forbidden_relative_path 的当前计算步骤。
    suffix = Path(parts[-1]).suffix.lower() if parts else ""  # suffix 用于本步治理判断

    # 返回 is_forbidden_relative_path 已整理完成的调用载荷。
    return suffix in FORBIDDEN_SUFFIXES


# 定义 analyze_release_content_root 的脚本治理处理入口。
def analyze_release_content_root(root: Path, *, allow_source_only_repo_local: bool = False) -> dict[str, Any]:

    # 收集 included files 条目，保持 analyze_release_content_root 的处理顺序稳定。
    list_included_files: list[str] = []  # included files 用于本步治理判断

    # 收集 forbidden paths 条目，保持 analyze_release_content_root 的处理顺序稳定。
    list_forbidden_paths: list[str] = []  # forbidden paths 用于本步治理判断

    # 收集 unexpected top level entries 条目，保持 analyze_release_content_root 的处理顺序稳定。
    set_unexpected_top_level_entries: set[str] = set()  # unexpected top level entries 用于本步治理判断

    # 收集 source only prefixes 条目，保持 analyze_release_content_root 的处理顺序稳定。
    set_source_only_prefixes: set[str] = set()  # source only prefixes 用于本步治理判断

    # 逐项推进 analyze_release_content_root 的候选项检查。
    for path in sorted(root.rglob("*")):

        # 保留 relative 中间值，支撑 analyze_release_content_root 的当前计算步骤。
        relative = path.relative_to(root).as_posix()  # relative 用于本步治理判断

        # 收集 parts 条目，保持 analyze_release_content_root 的处理顺序稳定。
        parts = Path(relative).parts  # parts 用于本步治理判断

        # 检查 analyze_release_content_root 的当前条件是否需要进入专门分支。
        if not parts:

            # 分隔 analyze_release_content_root 的控制流边界。
            continue

        # 保留 top level 中间值，支撑 analyze_release_content_root 的当前计算步骤。
        top_level = parts[0]  # top level 用于本步治理判断

        # 检查 analyze_release_content_root 的当前条件是否需要进入专门分支。
        if top_level in set_source_only_prefixes:

            # 分隔 analyze_release_content_root 的控制流边界。
            continue

        # 检查 analyze_release_content_root 的当前条件是否需要进入专门分支。
        if is_forbidden_relative_path(relative):

            # 调用 append 完成 analyze_release_content_root 的当前动作。
            list_forbidden_paths.append(relative)

            # 分隔 analyze_release_content_root 的控制流边界。
            continue

        # 检查 analyze_release_content_root 的当前条件是否需要进入专门分支。
        if len(parts) == 1 and top_level in IGNORED_TOP_LEVEL_FILES:

            # 分隔 analyze_release_content_root 的控制流边界。
            continue

        # 检查 analyze_release_content_root 的当前条件是否需要进入专门分支。
        if len(parts) == 1 and path.is_dir() and top_level not in ALLOWED_TOP_LEVEL_DIRS:

            # 调用 add 完成 analyze_release_content_root 的当前动作。
            set_unexpected_top_level_entries.add(top_level)

            # 分隔 analyze_release_content_root 的控制流边界。
            continue

        # 检查 analyze_release_content_root 的当前条件是否需要进入专门分支。
        if len(parts) > 1 and top_level not in ALLOWED_TOP_LEVEL_DIRS:

            # 调用 add 完成 analyze_release_content_root 的当前动作。
            set_unexpected_top_level_entries.add(top_level)

            # 分隔 analyze_release_content_root 的控制流边界。
            continue

        # 检查 analyze_release_content_root 的当前条件是否需要进入专门分支。
        if path.is_file():

            # 调用 append 完成 analyze_release_content_root 的当前动作。
            list_included_files.append(relative)

    # 收集 included top level entries 条目，保持 analyze_release_content_root 的处理顺序稳定。
    included_top_level_entries = sorted({Path(relative).parts[0] for relative in list_included_files})  # included top level entries 用于本步治理判断

    # 返回 analyze_release_content_root 已整理完成的调用载荷。
    return {
        "policy_version": POLICY_VERSION,
        "top_level_file_mode": TOP_LEVEL_FILE_MODE,
        "allowed_top_level_files": sorted(ALLOWED_TOP_LEVEL_FILES),
        "allowed_top_level_dirs": sorted(ALLOWED_TOP_LEVEL_DIRS),
        "forbidden_exact_names": sorted(FORBIDDEN_EXACT_NAMES),
        "forbidden_prefixes": sorted(FORBIDDEN_PREFIXES),
        "forbidden_suffixes": sorted(FORBIDDEN_SUFFIXES),
        "source_only_prefixes": sorted(set_source_only_prefixes),
        "included_files": sorted(list_included_files),
        "included_file_count": len(list_included_files),
        "included_top_level_entries": included_top_level_entries,
        "unexpected_top_level_entries": sorted(set_unexpected_top_level_entries),
        "forbidden_paths": sorted(list_forbidden_paths),
    }


# 定义 release_content_policy_receipt 的脚本治理处理入口。
def release_content_policy_receipt(analysis: dict[str, Any], *, forbidden_source_paths: list[str] | None = None) -> dict[str, Any]:

    # 返回 release_content_policy_receipt 已整理完成的调用载荷。
    return {
        "policy_version": analysis["policy_version"],
        "top_level_file_mode": analysis["top_level_file_mode"],
        "allowed_top_level_files": list(analysis["allowed_top_level_files"]),
        "allowed_top_level_dirs": list(analysis["allowed_top_level_dirs"]),
        "forbidden_exact_names": list(analysis["forbidden_exact_names"]),
        "forbidden_prefixes": list(analysis["forbidden_prefixes"]),
        "forbidden_suffixes": list(analysis["forbidden_suffixes"]),
        "included_file_count": analysis["included_file_count"],
        "included_top_level_entries": list(analysis["included_top_level_entries"]),
        "unexpected_top_level_entries": list(analysis["unexpected_top_level_entries"]),
        "forbidden_source_paths": sorted(forbidden_source_paths or []),
        "forbidden_release_paths": list(analysis["forbidden_paths"]),
    }


# 定义 validate_recorded_release_content_policy 的脚本治理处理入口。
def validate_recorded_release_content_policy(
    recorded: Any,
    release_analysis: dict[str, Any],
    *,
    forbidden_source_paths: list[str] | None = None,
    require_source_paths: bool = True,
) -> list[str]:

    # 检查 validate_recorded_release_content_policy 的当前条件是否需要进入专门分支。
    if not isinstance(recorded, dict):

        # 返回 validate_recorded_release_content_policy 已整理完成的调用载荷。
        return ["release content policy block is missing"]

    # 保留 expected 中间值，支撑 validate_recorded_release_content_policy 的当前计算步骤。
    dict_expected = release_content_policy_receipt(  # expected 用于本步治理判断
        release_analysis,  # expected 用于本步治理判断
        forbidden_source_paths=forbidden_source_paths if require_source_paths else None,  # expected 用于本步治理判断
    )

    # 收集 errors 条目，保持 validate_recorded_release_content_policy 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 逐项推进 validate_recorded_release_content_policy 的候选项检查。
    for key in (
        "policy_version",
        "top_level_file_mode",
        "allowed_top_level_files",
        "allowed_top_level_dirs",
        "forbidden_exact_names",
        "forbidden_prefixes",
        "forbidden_suffixes",
        "included_file_count",
        "included_top_level_entries",
        "unexpected_top_level_entries",
        "forbidden_release_paths",
    ):

        # 检查 validate_recorded_release_content_policy 的当前条件是否需要进入专门分支。
        if recorded.get(key) != dict_expected[key]:

            # 调用 append 完成 validate_recorded_release_content_policy 的当前动作。
            list_errors.append(f"release content policy field mismatch: {key}")

    # 检查 validate_recorded_release_content_policy 的当前条件是否需要进入专门分支。
    if require_source_paths and recorded.get("forbidden_source_paths") != dict_expected["forbidden_source_paths"]:

        # 调用 append 完成 validate_recorded_release_content_policy 的当前动作。
        list_errors.append("release content policy field mismatch: forbidden_source_paths")

    # 检查 validate_recorded_release_content_policy 的当前条件是否需要进入专门分支。
    elif not require_source_paths and not isinstance(recorded.get("forbidden_source_paths"), list):

        # 调用 append 完成 validate_recorded_release_content_policy 的当前动作。
        list_errors.append("release content policy forbidden_source_paths must be a list")

    # 返回 validate_recorded_release_content_policy 已整理完成的调用载荷。
    return list_errors


