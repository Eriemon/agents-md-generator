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
import ast
import fnmatch
import io
import os
import re
import tokenize
from pathlib import Path
from typing import Any

# 导入 脚本治理 所需的依赖模块。
from source_governance_config import load_global_rule_overrides, load_skill_source_governance, read_json


# 保留 COMMENT CHECK EXTENSIONS 中间值，支撑 模块入口 的当前计算步骤。
COMMENT_CHECK_EXTENSIONS = {".py", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"}  # COMMENT CHECK EXTENSIONS 用于本步治理判断

# 编号分片文件名会掩盖代码职责，runtime Python 脚本必须使用功能名。
NUMBERED_PYTHON_MODULE_RE = re.compile(r"^(?:\d+|_?part\d+|.*_part\d+)$")


# 定义 relative_path 的脚本治理处理入口。
def relative_path(path: Path, root: Path) -> str:

    # 返回 relative_path 已整理完成的调用载荷。
    return path.relative_to(root).as_posix()


# 定义 effective_source_governance 的脚本治理处理入口。
def effective_source_governance(project: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:

    # 收集 overrides 条目，保持 effective_source_governance 的处理顺序稳定。
    overrides = load_global_rule_overrides(project, profile)  # overrides 用于本步治理判断

    # 保留 raw 中间值，支撑 effective_source_governance 的当前计算步骤。
    raw = read_json(overrides["path"]) if overrides["path"].is_file() else {}  # raw 用于本步治理判断

    # 检查 effective_source_governance 的当前条件是否需要进入专门分支。
    if isinstance(raw, dict) and isinstance(raw.get("source_governance"), dict):

        # 返回 effective_source_governance 已整理完成的调用载荷。
        return {
            "config_path": overrides["path"],
            "config_source": "project-local",
            "config": overrides["data"].get("source_governance", {}),
            "errors": [item for item in overrides["errors"] if item.startswith("source_governance")],
        }

    # 保留 skill 中间值，支撑 effective_source_governance 的当前计算步骤。
    skill = load_skill_source_governance()  # skill 用于本步治理判断

    # 返回 effective_source_governance 已整理完成的调用载荷。
    return {
        "config_path": skill["path"],
        "config_source": "skill-local",
        "config": skill["data"],
        "errors": list(skill["errors"]),
    }


# 定义 iter_candidate_files 的脚本治理处理入口。
def iter_candidate_files(root: Path, config: dict[str, Any]) -> list[Path]:

    # 收集 excluded roots 条目，保持 iter_candidate_files 的处理顺序稳定。
    excluded_roots = {str(item).strip("/\\") for item in config.get("excluded_roots", [])}  # excluded roots 用于本步治理判断

    # 收集 files 条目，保持 iter_candidate_files 的处理顺序稳定。
    list_files: list[Path] = []  # files 用于本步治理判断

    # 逐项推进 iter_candidate_files 的候选项检查。
    for current_root, dir_names, file_names in os.walk(root):

        # 定位 current path 的文件边界，供 iter_candidate_files 后续读写校验使用。
        path_current_path = Path(current_root)  # current path 用于本步治理判断

        # 保护 iter_candidate_files 中允许失败的外部访问。
        try:

            # 收集 relative parts 条目，保持 iter_candidate_files 的处理顺序稳定。
            tuple_relative_parts = path_current_path.relative_to(root).parts  # relative parts 用于本步治理判断
        except ValueError:

            # 收集 relative parts 条目，保持 iter_candidate_files 的处理顺序稳定。
            tuple_relative_parts = ()  # relative parts 用于本步治理判断

        # 保留 中间载荷 中间值，支撑 iter_candidate_files 的当前计算步骤。
        dir_names[:] = [name for name in dir_names if not tuple_relative_parts[:1] or name not in excluded_roots]  # 中间载荷 用于本步治理判断

        # 检查 iter_candidate_files 的当前条件是否需要进入专门分支。
        if tuple_relative_parts and tuple_relative_parts[0] in excluded_roots:

            # 分隔 iter_candidate_files 的控制流边界。
            continue

        # 逐项推进 iter_candidate_files 的候选项检查。
        for file_name in file_names:

            # 保留 path 中间值，支撑 iter_candidate_files 的当前计算步骤。
            path = path_current_path / file_name  # path 用于本步治理判断

            # 调用 append 完成 iter_candidate_files 的当前动作。
            list_files.append(path)

    # 返回 iter_candidate_files 已整理完成的调用载荷。
    return sorted(list_files)


# 定义 byte_count 的脚本治理处理入口。
def byte_count(path: Path) -> int:

    # 返回 byte_count 已整理完成的调用载荷。
    return len(path.read_bytes())


# 定义 line_byte_lengths 的脚本治理处理入口。
def line_byte_lengths(path: Path) -> list[int]:

    # 返回 line_byte_lengths 已整理完成的调用载荷。
    return [len(line) for line in path.read_bytes().splitlines()]


# 定义 decomposition_plan_path 的脚本治理处理入口。
def decomposition_plan_path(project_root: Path, relative_file: str) -> Path:

    # 收集 overrides 条目，保持 decomposition_plan_path 的处理顺序稳定。
    overrides = load_global_rule_overrides(project_root)["data"]  # overrides 用于本步治理判断

    # 收集 source limits 条目，保持 decomposition_plan_path 的处理顺序稳定。
    source_limits = overrides.get("source_file_limits", {}) if isinstance(overrides.get("source_file_limits", {}), dict) else {}  # source limits 用于本步治理判断

    # 保留 plan root 中间值，支撑 decomposition_plan_path 的当前计算步骤。
    plan_root = str(source_limits.get("decomposition_plan_root", "docs/development/decomposition-plans")).strip().strip("/\\")  # plan root 用于本步治理判断

    # 保留 sanitized 中间值，支撑 decomposition_plan_path 的当前计算步骤。
    sanitized = relative_file.replace("\\", "/").replace(":", "")  # sanitized 用于本步治理判断

    # 返回 decomposition_plan_path 已整理完成的调用载荷。
    return project_root / plan_root / f"{sanitized}.md"


# 定义 has_valid_decomposition_plan 的脚本治理处理入口。
def has_valid_decomposition_plan(project_root: Path, relative_file: str) -> bool:

    # 定位 plan path 的文件边界，供 has_valid_decomposition_plan 后续读写校验使用。
    path_plan_path = decomposition_plan_path(project_root, relative_file)  # plan path 用于本步治理判断

    # 检查 has_valid_decomposition_plan 的当前条件是否需要进入专门分支。
    if not path_plan_path.is_file():

        # 返回 has_valid_decomposition_plan 已整理完成的调用载荷。
        return False

    # 保留 text 中间值，支撑 has_valid_decomposition_plan 的当前计算步骤。
    text = path_plan_path.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

    # 收集 overrides 条目，保持 has_valid_decomposition_plan 的处理顺序稳定。
    overrides = load_global_rule_overrides(project_root)["data"]  # overrides 用于本步治理判断

    # 收集 source limits 条目，保持 has_valid_decomposition_plan 的处理顺序稳定。
    source_limits = overrides.get("source_file_limits", {}) if isinstance(overrides.get("source_file_limits", {}), dict) else {}  # source limits 用于本步治理判断

    # 收集 required sections 条目，保持 has_valid_decomposition_plan 的处理顺序稳定。
    required_sections = source_limits.get("required_plan_sections", [])  # required sections 用于本步治理判断

    # 返回 has_valid_decomposition_plan 已整理完成的调用载荷。
    return all(f"## {section}" in text for section in required_sections)


# 定义 oversized_source_files 的脚本治理处理入口。
def oversized_source_files(
    root: Path,
    config: dict[str, Any],
    *,
    prefix: str = "",
    project_root: Path | None = None,
    source_relative_prefix: str = "",
) -> list[dict[str, Any]]:

    # 收集 max bytes 条目，保持 oversized_source_files 的处理顺序稳定。
    int_max_bytes = int(config.get("max_bytes", 0))  # max bytes 用于本步治理判断

    # 收集 extensions 条目，保持 oversized_source_files 的处理顺序稳定。
    extensions = {str(item).lower() for item in config.get("hard_fail_extensions", [])}  # extensions 用于本步治理判断

    # 收集 violations 条目，保持 oversized_source_files 的处理顺序稳定。
    list_violations: list[dict[str, Any]] = []  # violations 用于本步治理判断

    # 逐项推进 oversized_source_files 的候选项检查。
    for path in iter_candidate_files(root, config):

        # 检查 oversized_source_files 的当前条件是否需要进入专门分支。
        if path.suffix.lower() not in extensions:

            # 分隔 oversized_source_files 的控制流边界。
            continue

        # 保留 count 中间值，支撑 oversized_source_files 的当前计算步骤。
        int_count = byte_count(path)  # count 用于本步治理判断

        # 检查 oversized_source_files 的当前条件是否需要进入专门分支。
        if int_count <= int_max_bytes:

            # 分隔 oversized_source_files 的控制流边界。
            continue

        # 定位 rel path 的文件边界，供 oversized_source_files 后续读写校验使用。
        str_rel_path = relative_path(path, root)  # rel path 用于本步治理判断

        # 定位 plan rel path 的文件边界，供 oversized_source_files 后续读写校验使用。
        plan_rel_path = f"{source_relative_prefix.rstrip('/')}/{str_rel_path}" if source_relative_prefix else str_rel_path  # plan rel path 用于本步治理判断

        # 检查 oversized_source_files 的当前条件是否需要进入专门分支。
        if project_root is not None and has_valid_decomposition_plan(project_root, plan_rel_path):

            # 分隔 oversized_source_files 的控制流边界。
            continue

        # 检查 oversized_source_files 的当前条件是否需要进入专门分支。
        if prefix:

            # 定位 rel path 的文件边界，供 oversized_source_files 后续读写校验使用。
            str_rel_path = f"{prefix}/{str_rel_path}"  # rel path 用于本步治理判断

        # 调用 append 完成 oversized_source_files 的当前动作。
        list_violations.append({"path": str_rel_path, "byte_count": int_count, "max_bytes": int_max_bytes})

    # 返回 oversized_source_files 已整理完成的调用载荷。
    return list_violations


# 定义 minified_marker_count 的脚本治理处理入口。
def minified_marker_count(line: str) -> int:

    # 返回 minified_marker_count 已整理完成的调用载荷。
    return sum(line.count(marker) for marker in ("{", "}", ";", ",", "(", ")"))


# 定义 readability_violations 的脚本治理处理入口。
def readability_violations(root: Path, config: dict[str, Any], *, prefix: str = "") -> list[dict[str, str]]:

    # 保留 gate 中间值，支撑 readability_violations 的当前计算步骤。
    gate = config.get("readability_gate", {})  # gate 用于本步治理判断

    # 检查 readability_violations 的当前条件是否需要进入专门分支。
    if not isinstance(gate, dict) or gate.get("enabled") is not True:

        # 返回 readability_violations 已整理完成的调用载荷。
        return []

    # 收集 extensions 条目，保持 readability_violations 的处理顺序稳定。
    extensions = {str(item).lower() for item in config.get("hard_fail_extensions", [])}  # extensions 用于本步治理判断

    # 收集 max line bytes 条目，保持 readability_violations 的处理顺序稳定。
    int_max_line_bytes = int(gate.get("max_physical_line_bytes", 0))  # max line bytes 用于本步治理判断

    # 收集 single line min bytes 条目，保持 readability_violations 的处理顺序稳定。
    int_single_line_min_bytes = int(gate.get("single_line_min_bytes", 0))  # single line min bytes 用于本步治理判断

    # 收集 minified line min bytes 条目，保持 readability_violations 的处理顺序稳定。
    int_minified_line_min_bytes = int(gate.get("minified_line_min_bytes", 1000))  # minified line min bytes 用于本步治理判断

    # 收集 violations 条目，保持 readability_violations 的处理顺序稳定。
    list_violations: list[dict[str, str]] = []  # violations 用于本步治理判断

    # 逐项推进 readability_violations 的候选项检查。
    for path in iter_candidate_files(root, config):

        # 检查 readability_violations 的当前条件是否需要进入专门分支。
        if path.suffix.lower() not in extensions:

            # 分隔 readability_violations 的控制流边界。
            continue

        # 定位 rel path 的文件边界，供 readability_violations 后续读写校验使用。
        str_rel_path = relative_path(path, root)  # rel path 用于本步治理判断

        # 检查 readability_violations 的当前条件是否需要进入专门分支。
        if prefix:

            # 定位 rel path 的文件边界，供 readability_violations 后续读写校验使用。
            str_rel_path = f"{prefix}/{str_rel_path}"  # rel path 用于本步治理判断

        # 保留 raw 中间值，支撑 readability_violations 的当前计算步骤。
        raw = path.read_bytes()  # raw 用于本步治理判断

        # 保留 text 中间值，支撑 readability_violations 的当前计算步骤。
        text = raw.decode("utf-8", errors="ignore")  # text 用于本步治理判断

        # 收集 raw lines 条目，保持 readability_violations 的处理顺序稳定。
        raw_lines = raw.splitlines()  # raw lines 用于本步治理判断

        # 收集 byte lengths 条目，保持 readability_violations 的处理顺序稳定。
        byte_lengths = [len(line) for line in raw_lines]  # byte lengths 用于本步治理判断

        # 收集 non empty lines 条目，保持 readability_violations 的处理顺序稳定。
        non_empty_lines = [line for line in text.splitlines() if line.strip()]  # non empty lines 用于本步治理判断

        # 收集 total bytes 条目，保持 readability_violations 的处理顺序稳定。
        total_bytes = len(raw)  # total bytes 用于本步治理判断

        # 逐项推进 readability_violations 的候选项检查。
        for line_no, length in enumerate(byte_lengths, start=1):

            # 检查 readability_violations 的当前条件是否需要进入专门分支。
            if int_max_line_bytes > 0 and length > int_max_line_bytes:

                # 调用 append 完成 readability_violations 的当前动作。
                list_violations.append({
                    "path": str_rel_path,
                    "message": f"physical line {line_no} is {length} bytes (limit {int_max_line_bytes})",
                })

                # 分隔 readability_violations 的控制流边界。
                break

        # 检查 readability_violations 的当前条件是否需要进入专门分支。
        if len(non_empty_lines) == 1 and total_bytes >= int_single_line_min_bytes:

            # 调用 append 完成 readability_violations 的当前动作。
            list_violations.append({
                "path": str_rel_path,
                "message": f"one-line compressed source is not allowed ({total_bytes} bytes)",
            })

        # 逐项推进 readability_violations 的候选项检查。
        for line_no, line in enumerate(text.splitlines(), start=1):

            # 收集 line bytes 条目，保持 readability_violations 的处理顺序稳定。
            line_bytes = len(raw_lines[line_no - 1]) if line_no <= len(raw_lines) else len(line.encode("utf-8"))  # line bytes 用于本步治理判断

            # 检查 readability_violations 的当前条件是否需要进入专门分支。
            if line_bytes < int_minified_line_min_bytes:

                # 分隔 readability_violations 的控制流边界。
                continue

            # 保留 marker count 中间值，支撑 readability_violations 的当前计算步骤。
            int_marker_count = minified_marker_count(line)  # marker count 用于本步治理判断

            # 检查 readability_violations 的当前条件是否需要进入专门分支。
            if int_marker_count >= 80 or int_marker_count / max(line_bytes, 1) >= 0.08:

                # 调用 append 完成 readability_violations 的当前动作。
                list_violations.append({
                    "path": str_rel_path,
                    "message": f"minified or obfuscated dense line {line_no} is not allowed",
                })

                # 分隔 readability_violations 的控制流边界。
                break

    # 返回 readability_violations 已整理完成的调用载荷。
    return list_violations


# 定义 path_matches_test_only 的脚本治理处理入口。
def path_matches_test_only(rel_path: str, config: dict[str, Any]) -> str:

    # 收集 patterns 条目，保持 path_matches_test_only 的处理顺序稳定。
    patterns = config.get("test_only_patterns", {}) if isinstance(config.get("test_only_patterns", {}), dict) else {}  # patterns 用于本步治理判断

    # 逐项推进 path_matches_test_only 的候选项检查。
    for pattern in patterns.get("path_globs", []):

        # 保留 normalized 中间值，支撑 path_matches_test_only 的当前计算步骤。
        normalized = str(pattern).replace("\\", "/")  # normalized 用于本步治理判断

        # 检查 path_matches_test_only 的当前条件是否需要进入专门分支。
        if fnmatch.fnmatch(rel_path, normalized):

            # 返回 path_matches_test_only 已整理完成的调用载荷。
            return normalized

    # 返回 path_matches_test_only 已整理完成的调用载荷。
    return ""


# 定义 is_python_runtime_script 的脚本治理处理入口。
def is_python_runtime_script(rel_path: str) -> bool:

    # 使用统一分隔符识别 skill runtime 和 release runtime 下的 Python 脚本。
    parts = rel_path.replace("\\", "/").split("/")  # 路径片段用于定位 scripts/python 边界

    # 逐段查找 scripts/python，避免把普通源码目录误判为运行时脚本。
    for index in range(max(len(parts) - 1, 0)):

        # scripts/python 成对出现时才进入运行时脚本命名约束。
        if parts[index] == "scripts" and parts[index + 1] == "python":

            # 只有 Python 文件参与本次功能化命名约束。
            return rel_path.endswith(".py")

    # 未命中 runtime Python 目录时不参与该门禁。
    return False


# 定义 numbered_python_module_reason 的脚本治理处理入口。
def numbered_python_module_reason(module_name: str) -> str:

    # 去掉扩展名后检查纯数字、part 数字，以及下划线连接的 part 数字尾缀。
    stem = Path(module_name).stem  # 模块名主体用于识别顺序编号分片

    # 编号式模块名缺少功能语义，后续维护者无法从文件名判断职责。
    if NUMBERED_PYTHON_MODULE_RE.fullmatch(stem):

        # 返回调用方可以直接展示的命名错误说明。
        return "Python runtime module name uses a numbered shard suffix; use a functional name"

    # 功能化模块名不产生命名违规。
    return ""


# 定义 functional_naming_violations 的脚本治理处理入口。
def functional_naming_violations(root: Path, config: dict[str, Any], *, prefix: str = "") -> list[dict[str, str]]:

    # 收集 violations 条目，保持报告顺序稳定。
    list_violations: list[dict[str, str]] = []

    # 逐项检查候选文件，只约束 scripts/python runtime 下的 Python 模块名。
    for path in iter_candidate_files(root, config):

        # 计算相对路径，让 source 和 release 报告都使用可读路径。
        str_rel_path = relative_path(path, root)

        # 非 runtime Python 脚本不进入功能化文件名门禁。
        if not is_python_runtime_script(str_rel_path):

            # 继续检查下一个候选文件。
            continue

        # 分析模块 basename 是否仍在使用顺序编号分片名。
        str_reason = numbered_python_module_reason(path.name)

        # 功能名通过时不写入报告。
        if not str_reason:

            # 继续检查下一个候选文件。
            continue

        # 组合 release 前缀，保持发布包报告能指向 dist 内实际文件。
        str_full_path = f"{prefix}/{str_rel_path}" if prefix else str_rel_path

        # 记录违反功能化命名要求的 runtime Python 模块。
        list_violations.append({"path": str_full_path, "message": str_reason})

    # 返回所有功能化命名违规。
    return list_violations


# 定义 test_code_boundary_violations 的脚本治理处理入口。
def test_code_boundary_violations(root: Path, config: dict[str, Any], *, prefix: str = "") -> list[dict[str, str]]:

    # 收集 violations 条目，保持 test_code_boundary_violations 的处理顺序稳定。
    list_violations: list[dict[str, str]] = []  # violations 用于本步治理判断

    # 逐项推进 test_code_boundary_violations 的候选项检查。
    for path in iter_candidate_files(root, config):

        # 定位 rel path 的文件边界，供 test_code_boundary_violations 后续读写校验使用。
        str_rel_path = relative_path(path, root)  # rel path 用于本步治理判断

        # 保留 matched 中间值，支撑 test_code_boundary_violations 的当前计算步骤。
        str_matched = path_matches_test_only(str_rel_path, config)  # matched 用于本步治理判断

        # 检查 test_code_boundary_violations 的当前条件是否需要进入专门分支。
        if not str_matched:

            # 分隔 test_code_boundary_violations 的控制流边界。
            continue

        # 定位 full path 的文件边界，供 test_code_boundary_violations 后续读写校验使用。
        full_path = f"{prefix}/{str_rel_path}" if prefix else str_rel_path  # full path 用于本步治理判断

        # 调用 append 完成 test_code_boundary_violations 的当前动作。
        list_violations.append({"path": full_path, "pattern": str_matched})

    # 返回 test_code_boundary_violations 已整理完成的调用载荷。
    return list_violations


# 定义 python_assignment_comment_lines 的脚本治理处理入口。
def python_assignment_comment_lines(text: str) -> set[int]:

    # 保护 python_assignment_comment_lines 中允许失败的外部访问。
    try:

        # 保留 tree 中间值，支撑 python_assignment_comment_lines 的当前计算步骤。
        tree = ast.parse(text or "\n")  # tree 用于本步治理判断
    except SyntaxError:

        # 返回 python_assignment_comment_lines 已整理完成的调用载荷。
        return set()

    # 收集 assignment lines 条目，保持 python_assignment_comment_lines 的处理顺序稳定。
    set_assignment_lines: set[int] = set()  # assignment lines 用于本步治理判断

    # 逐项推进 python_assignment_comment_lines 的候选项检查。
    for node in ast.walk(tree):

        # 检查 python_assignment_comment_lines 的当前条件是否需要进入专门分支。
        if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):

            # 分隔 python_assignment_comment_lines 的控制流边界。
            continue

        # 保留 start 中间值，支撑 python_assignment_comment_lines 的当前计算步骤。
        start = getattr(node, "lineno", 0) or 0  # start 用于本步治理判断

        # 保留 end 中间值，支撑 python_assignment_comment_lines 的当前计算步骤。
        end = getattr(node, "end_lineno", start) or start  # end 用于本步治理判断

        # 调用 update 完成 python_assignment_comment_lines 的当前动作。
        set_assignment_lines.update(range(start, end + 1))

    # 返回 python_assignment_comment_lines 已整理完成的调用载荷。
    return set_assignment_lines


# 定义 extract_python_comment_violations 的脚本治理处理入口。
def extract_python_comment_violations(path: Path, config: dict[str, Any]) -> list[str]:

    # 保留 text 中间值，支撑 extract_python_comment_violations 的当前计算步骤。
    text = path.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

    # 保留 gate 中间值，支撑 extract_python_comment_violations 的当前计算步骤。
    gate = config.get("comment_policy_gate", {})  # gate 用于本步治理判断

    # 保留 python gate 中间值，支撑 extract_python_comment_violations 的当前计算步骤。
    python_gate = gate.get("python", {}) if isinstance(gate.get("python", {}), dict) else {}  # python gate 用于本步治理判断

    # 收集 ai markers 条目，保持 extract_python_comment_violations 的处理顺序稳定。
    ai_markers = [str(item).lower() for item in gate.get("forbid_ai_comment_markers", [])]  # ai markers 用于本步治理判断

    # 收集 violations 条目，保持 extract_python_comment_violations 的处理顺序稳定。
    list_violations: list[str] = []  # violations 用于本步治理判断

    # 检查 extract_python_comment_violations 的当前条件是否需要进入专门分支。
    if python_gate.get("require_public_api_docstring", False):

        # 保护 extract_python_comment_violations 中允许失败的外部访问。
        try:

            # 保留 tree 中间值，支撑 extract_python_comment_violations 的当前计算步骤。
            tree = ast.parse(text or "\n")  # tree 用于本步治理判断
        except SyntaxError as exc:

            # 保留 line no 中间值，支撑 extract_python_comment_violations 的当前计算步骤。
            line_no = getattr(exc, "lineno", 0) or 0  # line no 用于本步治理判断

            # 调用 append 完成 extract_python_comment_violations 的当前动作。
            list_violations.append(f"python syntax error prevents comment policy parsing (line {line_no})")

            # 保留 tree 中间值，支撑 extract_python_comment_violations 的当前计算步骤。
            tree = None  # tree 用于本步治理判断

        # 检查 extract_python_comment_violations 的当前条件是否需要进入专门分支。
        if tree is not None:

            # 逐项推进 extract_python_comment_violations 的候选项检查。
            for node in ast.walk(tree):

                # 检查 extract_python_comment_violations 的当前条件是否需要进入专门分支。
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):

                    # 检查 extract_python_comment_violations 的当前条件是否需要进入专门分支。
                    if ast.get_docstring(node, clean=False) is None:

                        # 调用 append 完成 extract_python_comment_violations 的当前动作。
                        list_violations.append(f"public API `{node.name}` is missing a docstring (line {node.lineno})")

    # 检查 extract_python_comment_violations 的当前条件是否需要进入专门分支。
    if python_gate.get("forbid_trailing_comment", False) or ai_markers:

        # 保护 extract_python_comment_violations 中允许失败的外部访问。
        try:

            # 保留 allow assignment trailing 中间值，支撑 extract_python_comment_violations 的当前计算步骤。
            bool_allow_assignment_trailing = bool(python_gate.get("allow_assignment_trailing_comment", False))  # allow assignment trailing 用于本步治理判断

            # 收集 assignment comment lines 条目，保持 extract_python_comment_violations 的处理顺序稳定。
            assignment_comment_lines = python_assignment_comment_lines(text) if bool_allow_assignment_trailing else set()  # assignment comment lines 用于本步治理判断

            # 收集 lines 条目，保持 extract_python_comment_violations 的处理顺序稳定。
            lines = text.splitlines()  # lines 用于本步治理判断

            # 逐项推进 extract_python_comment_violations 的候选项检查。
            for token in tokenize.generate_tokens(io.StringIO(text).readline):

                # 检查 extract_python_comment_violations 的当前条件是否需要进入专门分支。
                if token.type != tokenize.COMMENT:

                    # 分隔 extract_python_comment_violations 的控制流边界。
                    continue

                # 保留 line text 中间值，支撑 extract_python_comment_violations 的当前计算步骤。
                line_text = lines[token.start[0] - 1] if lines else ""  # line text 用于本步治理判断

                # 保留 code before comment 中间值，支撑 extract_python_comment_violations 的当前计算步骤。
                code_before_comment = line_text[: token.start[1]].strip()  # code before comment 用于本步治理判断

                # 检查 extract_python_comment_violations 的当前条件是否需要进入专门分支。
                if (
                    python_gate.get("forbid_trailing_comment", False)
                    and code_before_comment
                    and token.start[0] not in assignment_comment_lines
                ):

                    # 调用 append 完成 extract_python_comment_violations 的当前动作。
                    list_violations.append(f"trailing Python comment is not allowed (line {token.start[0]})")

                # 检查 extract_python_comment_violations 的当前条件是否需要进入专门分支。
                if ai_markers and any(marker in token.string.lower() for marker in ai_markers):

                    # 调用 append 完成 extract_python_comment_violations 的当前动作。
                    list_violations.append(f"AI-generated comment marker is not allowed (line {token.start[0]})")
        except tokenize.TokenError as exc:

            # 保留 line no 中间值，支撑 extract_python_comment_violations 的当前计算步骤。
            line_no = exc.args[1][0] if len(exc.args) > 1 and isinstance(exc.args[1], tuple) and exc.args[1] else 0  # line no 用于本步治理判断

            # 调用 append 完成 extract_python_comment_violations 的当前动作。
            list_violations.append(f"python tokenize error prevents comment policy parsing (line {line_no})")

    # 返回 extract_python_comment_violations 已整理完成的调用载荷。
    return list_violations


# 定义 extract_c_cpp_comment_violations 的脚本治理处理入口。
def extract_c_cpp_comment_violations(path: Path, config: dict[str, Any]) -> list[str]:

    # 保留 text 中间值，支撑 extract_c_cpp_comment_violations 的当前计算步骤。
    text = path.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

    # 保留 gate 中间值，支撑 extract_c_cpp_comment_violations 的当前计算步骤。
    gate = config.get("comment_policy_gate", {})  # gate 用于本步治理判断

    # 保留 c cpp gate 中间值，支撑 extract_c_cpp_comment_violations 的当前计算步骤。
    c_cpp_gate = gate.get("c_cpp", {}) if isinstance(gate.get("c_cpp", {}), dict) else {}  # c cpp gate 用于本步治理判断

    # 收集 ai markers 条目，保持 extract_c_cpp_comment_violations 的处理顺序稳定。
    ai_markers = [str(item).lower() for item in gate.get("forbid_ai_comment_markers", [])]  # ai markers 用于本步治理判断

    # 收集 violations 条目，保持 extract_c_cpp_comment_violations 的处理顺序稳定。
    list_violations: list[str] = []  # violations 用于本步治理判断

    # 检查 extract_c_cpp_comment_violations 的当前条件是否需要进入专门分支。
    if not c_cpp_gate.get("forbid_trailing_comment", False) and not ai_markers:

        # 返回 extract_c_cpp_comment_violations 已整理完成的调用载荷。
        return list_violations

    # 逐项推进 extract_c_cpp_comment_violations 的候选项检查。
    for line_no, line in enumerate(text.splitlines(), start=1):

        # 保留 stripped 中间值，支撑 extract_c_cpp_comment_violations 的当前计算步骤。
        stripped = line.strip()  # stripped 用于本步治理判断

        # 检查 extract_c_cpp_comment_violations 的当前条件是否需要进入专门分支。
        if not stripped:

            # 分隔 extract_c_cpp_comment_violations 的控制流边界。
            continue

        # 保留 comment index 中间值，支撑 extract_c_cpp_comment_violations 的当前计算步骤。
        comment_index = line.find("//")  # comment index 用于本步治理判断

        # 保留 block index 中间值，支撑 extract_c_cpp_comment_violations 的当前计算步骤。
        block_index = line.find("/*")  # block index 用于本步治理判断

        # 收集 indexes 条目，保持 extract_c_cpp_comment_violations 的处理顺序稳定。
        indexes = [index for index in [comment_index, block_index] if index >= 0]  # indexes 用于本步治理判断

        # 检查 extract_c_cpp_comment_violations 的当前条件是否需要进入专门分支。
        if not indexes:

            # 分隔 extract_c_cpp_comment_violations 的控制流边界。
            continue

        # 保留 index 中间值，支撑 extract_c_cpp_comment_violations 的当前计算步骤。
        index = min(indexes)  # index 用于本步治理判断

        # 检查 extract_c_cpp_comment_violations 的当前条件是否需要进入专门分支。
        if c_cpp_gate.get("forbid_trailing_comment", False) and line[:index].strip() and not stripped.startswith("#define"):

            # 调用 append 完成 extract_c_cpp_comment_violations 的当前动作。
            list_violations.append(f"trailing C/C++ comment is not allowed (line {line_no})")

        # 检查 extract_c_cpp_comment_violations 的当前条件是否需要进入专门分支。
        if ai_markers and any(marker in line[index:].lower() for marker in ai_markers):

            # 调用 append 完成 extract_c_cpp_comment_violations 的当前动作。
            list_violations.append(f"AI-generated comment marker is not allowed (line {line_no})")

    # 返回 extract_c_cpp_comment_violations 已整理完成的调用载荷。
    return list_violations


# 定义 comment_policy_violations 的脚本治理处理入口。
def comment_policy_violations(root: Path, config: dict[str, Any], *, prefix: str = "") -> list[dict[str, str]]:

    # 保留 gate 中间值，支撑 comment_policy_violations 的当前计算步骤。
    gate = config.get("comment_policy_gate", {})  # gate 用于本步治理判断

    # 检查 comment_policy_violations 的当前条件是否需要进入专门分支。
    if not isinstance(gate, dict) or gate.get("enabled") is not True:

        # 返回 comment_policy_violations 已整理完成的调用载荷。
        return []

    # 收集 violations 条目，保持 comment_policy_violations 的处理顺序稳定。
    list_violations: list[dict[str, str]] = []  # violations 用于本步治理判断

    # 逐项推进 comment_policy_violations 的候选项检查。
    for path in iter_candidate_files(root, config):

        # 检查 comment_policy_violations 的当前条件是否需要进入专门分支。
        if path.suffix.lower() not in COMMENT_CHECK_EXTENSIONS:

            # 分隔 comment_policy_violations 的控制流边界。
            continue

        # 收集 messages 条目，保持 comment_policy_violations 的处理顺序稳定。
        list_messages: list[str] = []  # messages 用于本步治理判断

        # 检查 comment_policy_violations 的当前条件是否需要进入专门分支。
        if path.suffix.lower() == ".py":

            # 调用 extend 完成 comment_policy_violations 的当前动作。
            list_messages.extend(extract_python_comment_violations(path, config))
        else:

            # 调用 extend 完成 comment_policy_violations 的当前动作。
            list_messages.extend(extract_c_cpp_comment_violations(path, config))

        # 定位 rel path 的文件边界，供 comment_policy_violations 后续读写校验使用。
        str_rel_path = relative_path(path, root)  # rel path 用于本步治理判断

        # 检查 comment_policy_violations 的当前条件是否需要进入专门分支。
        if prefix:

            # 定位 rel path 的文件边界，供 comment_policy_violations 后续读写校验使用。
            str_rel_path = f"{prefix}/{str_rel_path}"  # rel path 用于本步治理判断

        # 逐项推进 comment_policy_violations 的候选项检查。
        for message in list_messages:

            # 调用 append 完成 comment_policy_violations 的当前动作。
            list_violations.append({"path": str_rel_path, "message": message})

    # 返回 comment_policy_violations 已整理完成的调用载荷。
    return list_violations


# 定义 source_governance_report 的脚本治理处理入口。
def source_governance_report(project: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:

    # 保留 effective 中间值，支撑 source_governance_report 的当前计算步骤。
    dict_effective = effective_source_governance(project, profile)  # effective 用于本步治理判断

    # 保留 config 中间值，支撑 source_governance_report 的当前计算步骤。
    config = dict_effective["config"]  # config 用于本步治理判断

    # 保留 oversized 中间值，支撑 source_governance_report 的当前计算步骤。
    list_oversized = oversized_source_files(project, config, project_root=project)  # oversized 用于本步治理判断

    # 保留 boundary 中间值，支撑 source_governance_report 的当前计算步骤。
    list_boundary = test_code_boundary_violations(project, config)  # boundary 用于本步治理判断

    # 收集 comments 条目，保持 source_governance_report 的处理顺序稳定。
    list_comments = comment_policy_violations(project, config)  # comments 用于本步治理判断

    # 保留 readability 中间值，支撑 source_governance_report 的当前计算步骤。
    list_readability = readability_violations(project, config)  # readability 用于本步治理判断

    # 收集 naming 条目，确保 runtime Python 模块使用职责名而非编号分片名。
    list_naming = functional_naming_violations(project, config)

    # 收集 errors 条目，保持 source_governance_report 的处理顺序稳定。
    list_errors = list(dict_effective["errors"])  # errors 用于本步治理判断

    # 返回 source_governance_report 已整理完成的调用载荷。
    return {
        "project": str(project),
        "config_path": str(dict_effective["config_path"]),
        "config_source": dict_effective["config_source"],
        "config_errors": list(dict_effective["errors"]),
        "oversized_source_files": list_oversized,
        "test_code_boundary_violations": list_boundary,
        "comment_policy_violations": list_comments,
        "readability_violations": list_readability,
        "functional_naming_violations": list_naming,
        "errors": list_errors,
        "ok": not (list_errors or list_oversized or list_boundary or list_comments or list_readability or list_naming),
    }


# 定义 release_source_governance_report 的脚本治理处理入口。
def release_source_governance_report(
    project: Path,
    release_dir: Path,
    profile: dict[str, Any] | None = None,
    *,
    source_relative_prefix: str = "",
) -> dict[str, Any]:

    # 保留 effective 中间值，支撑 release_source_governance_report 的当前计算步骤。
    dict_effective = effective_source_governance(project, profile)  # effective 用于本步治理判断

    # 保留 config 中间值，支撑 release_source_governance_report 的当前计算步骤。
    dict_config = dict(dict_effective["config"])  # config 用于本步治理判断

    # 保留 中间载荷 中间值，支撑 release_source_governance_report 的当前计算步骤。
    dict_config["excluded_roots"] = []  # 中间载荷 用于本步治理判断

    # 保留 prefix 中间值，支撑 release_source_governance_report 的当前计算步骤。
    prefix = release_dir.relative_to(project).as_posix() if release_dir.is_relative_to(project) else release_dir.name  # prefix 用于本步治理判断

    # 保留 oversized 中间值，支撑 release_source_governance_report 的当前计算步骤。
    list_oversized = oversized_source_files(  # oversized 用于本步治理判断
        release_dir,  # oversized 用于本步治理判断
        dict_config,  # oversized 用于本步治理判断
        prefix=prefix,  # oversized 用于本步治理判断
        project_root=project,  # oversized 用于本步治理判断
        source_relative_prefix=source_relative_prefix,  # oversized 用于本步治理判断
    )

    # 保留 boundary 中间值，支撑 release_source_governance_report 的当前计算步骤。
    list_boundary = test_code_boundary_violations(release_dir, dict_config, prefix=prefix)  # boundary 用于本步治理判断

    # 收集 comments 条目，保持 release_source_governance_report 的处理顺序稳定。
    list_comments = comment_policy_violations(release_dir, dict_config, prefix=prefix)  # comments 用于本步治理判断

    # 保留 readability 中间值，支撑 release_source_governance_report 的当前计算步骤。
    list_readability = readability_violations(release_dir, dict_config, prefix=prefix)  # readability 用于本步治理判断

    # 收集 naming 条目，发布包中的 runtime Python 模块也必须保留功能化命名。
    list_naming = functional_naming_violations(release_dir, dict_config, prefix=prefix)

    # 返回 release_source_governance_report 已整理完成的调用载荷。
    return {
        "project": str(project),
        "release_dir": str(release_dir),
        "config_path": str(dict_effective["config_path"]),
        "config_source": dict_effective["config_source"],
        "config_errors": list(dict_effective["errors"]),
        "oversized_source_files": list_oversized,
        "test_code_boundary_violations": list_boundary,
        "comment_policy_violations": list_comments,
        "readability_violations": list_readability,
        "functional_naming_violations": list_naming,
        "errors": list(dict_effective["errors"]),
        "ok": not (dict_effective["errors"] or list_oversized or list_boundary or list_comments or list_readability or list_naming),
    }


# 定义 format_source_governance_errors 的脚本治理处理入口。
def format_source_governance_errors(report: dict[str, Any], *, prefix: str = "source governance") -> list[str]:

    # 收集 errors 条目，保持 format_source_governance_errors 的处理顺序稳定。
    errors = [f"{prefix}: {item}" for item in report.get("errors", [])]  # errors 用于本步治理判断

    # 逐项推进 format_source_governance_errors 的候选项检查。
    for item in report.get("oversized_source_files", []):

        # 调用 append 完成 format_source_governance_errors 的当前动作。
        errors.append(
            f"{prefix}: oversized file `{item['path']}` has {item['byte_count']} bytes (limit {item['max_bytes']} bytes)"
        )

    # 逐项推进 format_source_governance_errors 的候选项检查。
    for item in report.get("test_code_boundary_violations", []):

        # 调用 append 完成 format_source_governance_errors 的当前动作。
        errors.append(f"{prefix}: test-only design code outside tests `{item['path']}` matched `{item['pattern']}`")

    # 逐项推进 format_source_governance_errors 的候选项检查。
    for item in report.get("comment_policy_violations", []):

        # 调用 append 完成 format_source_governance_errors 的当前动作。
        errors.append(f"{prefix}: `{item['path']}` {item['message']}")

    # 逐项推进 format_source_governance_errors 的候选项检查。
    for item in report.get("readability_violations", []):

        # 调用 append 完成 format_source_governance_errors 的当前动作。
        errors.append(f"{prefix}: `{item['path']}` {item['message']}")

    # 逐项推进 format_source_governance_errors 的功能命名检查结果。
    for item in report.get("functional_naming_violations", []):

        # 调用 append 完成功能命名错误的人类可读输出。
        errors.append(f"{prefix}: `{item['path']}` {item['message']}")

    # 返回 format_source_governance_errors 已整理完成的调用载荷。
    return errors


