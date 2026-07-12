"""校验 AGENTS.md、全局 baseline、治理配置和工作区规则完整性。"""

# 导入 AGENTS 校验所需的未来注解支持。
from __future__ import annotations

# 导入路径、CLI 与只读文件操作需要的标准库模块。
import sys
from pathlib import Path

# 导入 AGENTS 校验主体逻辑所需的标准库模块。
import argparse
from functools import lru_cache
import json
import re
from typing import Any

# 关闭字节码落盘，避免治理命令给工作树引入额外缓存文件。
sys.dont_write_bytecode = True  # 禁止写入 __pycache__ 缓存文件

# 仅在路径式 CLI 启动找不到跨任务共享模块时，补齐 common/docs 两个最小搜索路径。
def bootstrap_shared_task_imports() -> None:
    """补齐 verify 脚本运行时所需的最小跨任务模块搜索路径。

    参数:
        无。

    返回:
        无业务返回值；需要时只补齐 `common/` 与 `docs/` 两个目录。
    """

    # 先锚定 verify 兄弟任务目录的共同父目录，后续再从这里拼出 common 与 docs 的固定落点。
    path_scripts_python_root = Path(__file__).resolve().parents[1]  # verify 兄弟任务目录的共同父目录

    # verify_agents 只依赖 common 与 docs 这两个兄弟目录，不再恢复历史上的全目录注入。
    for str_task_dir_name in ("common", "docs"):

        # 拼出当前兄弟任务目录的绝对路径，后续只在缺失时再注入 sys.path。
        str_task_dir_path = str(path_scripts_python_root / str_task_dir_name)  # 当前兄弟任务目录的绝对路径

        # 仅在搜索路径缺失时补齐一次，避免重复插入扰动现有导入顺序。
        if str_task_dir_path not in sys.path:

            # 只补齐 verify_agents 真实依赖的兄弟目录，保证仓库根目录路径式启动仍可导入共享模块。
            sys.path.insert(0, str_task_dir_path)

# 构建 verify_agents 运行时要复用的共享依赖映射。
def build_shared_task_dependencies() -> dict[str, Any]:
    """按需加载 verify_agents 运行所需的跨任务共享模块。

    参数:
        无。

    返回:
        一个包含 skip 目录、profile 读取、docs 校验和 root sync 命令等共享依赖的映射。
    """

    # 先尝试直接导入；只有路径式 CLI 启动失败时才做最小路径自举。
    try:

        # 导入 AGENTS 校验依赖。
        from agents_common import (
            SKIP_DIRS as set_shared_skip_dirs,
            decomposition_plan_path as fn_decomposition_plan_path,
            emit_json as fn_emit_json,
            evolution_owner_status as fn_evolution_owner_status,
        )

        # 导入基础 AGENTS 状态判定工具，供主校验流程读取全局同步与覆盖配置。
        from agents_common import (
            global_codex_agents_status as fn_global_codex_agents_status,
            inspect_project as fn_inspect_project,
            load_global_rule_overrides as fn_load_global_rule_overrides,
        )

        # 导入项目解析与版本辅助工具，供主校验流程读取 profile、版本和同步命令。
        from agents_common import (
            global_codex_agents_sync_command as fn_global_codex_agents_sync_command,
            parse_agents_metadata as fn_parse_agents_metadata,
            project_profile as fn_project_profile,
            read_installed_skill_version as fn_read_installed_skill_version,
            resolve_project as fn_resolve_project,
            root_agents_sync_command as fn_root_agents_sync_command,
        )

        # 导入文档治理校验入口，供主校验流程复用 handoff/docs 验证结果。
        from manage_docs import verify_docs as fn_verify_docs

    # 仓库根目录路径式启动时，跨任务共享模块还没进 sys.path，需要先做一次最小路径自举。
    except ModuleNotFoundError:

        # 只补齐 verify_agents 的真实运行时依赖目录，避免恢复历史上的全目录副作用。
        bootstrap_shared_task_imports()

        # 最小路径自举完成后，重新导入 verify_agents 运行所需的跨任务共享模块。
        from agents_common import (
            SKIP_DIRS as set_shared_skip_dirs,
            decomposition_plan_path as fn_decomposition_plan_path,
            emit_json as fn_emit_json,
            evolution_owner_status as fn_evolution_owner_status,
        )

        # 导入基础 AGENTS 状态判定工具，供主校验流程读取全局同步与覆盖配置。
        from agents_common import (
            global_codex_agents_status as fn_global_codex_agents_status,
            inspect_project as fn_inspect_project,
            load_global_rule_overrides as fn_load_global_rule_overrides,
        )

        # 导入项目解析与版本辅助工具，供主校验流程读取 profile、版本和同步命令。
        from agents_common import (
            global_codex_agents_sync_command as fn_global_codex_agents_sync_command,
            parse_agents_metadata as fn_parse_agents_metadata,
            project_profile as fn_project_profile,
            read_installed_skill_version as fn_read_installed_skill_version,
            resolve_project as fn_resolve_project,
            root_agents_sync_command as fn_root_agents_sync_command,
        )

        # 导入文档治理校验入口，供主校验流程复用 handoff/docs 验证结果。
        from manage_docs import verify_docs as fn_verify_docs

    # 统一返回本模块后续 helper 需要复用的共享依赖映射。
    return {
        "skip_dirs": set_shared_skip_dirs,
        "decomposition_plan_path": fn_decomposition_plan_path,
        "emit_json": fn_emit_json,
        "evolution_owner_status": fn_evolution_owner_status,
        "global_codex_agents_status": fn_global_codex_agents_status,
        "global_codex_agents_sync_command": fn_global_codex_agents_sync_command,
        "inspect_project": fn_inspect_project,
        "load_global_rule_overrides": fn_load_global_rule_overrides,
        "parse_agents_metadata": fn_parse_agents_metadata,
        "project_profile": fn_project_profile,
        "read_installed_skill_version": fn_read_installed_skill_version,
        "resolve_project": fn_resolve_project,
        "root_agents_sync_command": fn_root_agents_sync_command,
        "verify_docs": fn_verify_docs,
    }

# 使用单例缓存包装共享依赖工厂，避免仓库级扫描重复执行导入探测。
shared_task_dependencies = lru_cache(maxsize=1)(build_shared_task_dependencies)  # 共享依赖缓存访问入口

# 导入语言技能路由契约校验，阻止 Python/脚本双技能门禁被弱化。
from language_skill_routing_contract import validate_language_skill_route_lines

# 导入源码治理报告格式化工具，用于把 profile 结果折叠成 AGENTS 诊断。
from source_governance import format_source_governance_errors, source_governance_report

# 导入 AGENTS verifier 共享的语言锁、路径和命令正则。
from verify_agents_policy import (
    COMMAND_RE,
    LANGUAGE_LOCK_RE,
    PATH_RE,
    PLAN_LANGUAGE_LOCK_RE,
)

# 导入 AGENTS verifier 共享的体积阈值与治理短语集合。
from verify_agents_policy import (
    CODING_BEHAVIOR_LANGUAGE_ROUTING_REQUIRED_SNIPPETS,
    PROJECT_LOCAL_GOVERNANCE_RUNTIME_RE,
    ROOT_AGENTS_MAX_BYTES,
    ROOT_AGENTS_MAX_KB,
    SCRIPT_OUTPUT_POLICY_REQUIRED_SNIPPETS,
)

# 定义严格双技能语言路由开始生效的版本阈值，旧版本根文件在匹配安装态时继续走兼容验收。
STRICT_LANGUAGE_SKILL_ROUTING_MIN_VERSION = (1, 4, 1)  # 从该版本开始强制双技能路由全文案

# 判断当前安装态是否仍应使用历史单技能路由兼容规则。
def uses_legacy_language_skill_routing_rules(installed_version: str | None) -> bool:
    """根据安装态版本判断是否启用历史语言路由兼容验收。

    参数:
        installed_version: 当前安装态 `agents-md-generator` 版本字符串。

    返回:
        旧版本安装态返回 True；当前严格版本或无法解析的版本返回 False。
    """

    # 缺少安装态版本时无法安全判断兼容窗口，回退到当前严格规则。
    if not installed_version:

        # 没有安装态版本证据时直接保持严格门禁，避免静默放宽历史兼容范围。
        return False

    # 解析 `vX.Y.Z` 或 `X.Y.Z` 版本号，无法解析时同样保持当前严格规则。
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(installed_version).strip())  # 安装态版本号匹配结果

    # 无法解析的版本字符串不进入历史兼容分支，避免静默放宽真实门禁。
    if not match:

        # 解析失败时同样保持严格门禁，防止脏版本字符串误触发历史兼容。
        return False

    # 把版本三元组转成整数元组，后续与严格阈值做字典序比较。
    tuple_installed_version = tuple(int(part) for part in match.groups())  # 安装态版本三元组

    # 只允许严格阈值之前的已知历史版本走兼容路由验收。
    return tuple_installed_version < STRICT_LANGUAGE_SKILL_ROUTING_MIN_VERSION

# 校验生成区块起止标记数量是否配平。
def validate_markers(text: str, file: str, errors: list[str]) -> None:
    """校验 AGENTS 生成标记是否成对出现。

    参数:
        text: 当前待检查的 AGENTS 文本。
        file: 当前错误信息应写回的文件标识。
        errors: 累积错误列表，函数会把诊断直接追加进去。

    返回:
        无业务返回值；发现问题时直接向 `errors` 追加诊断。
    """

    # 统计生成区块起点数量，后续需要和终点数量做配平校验。
    int_start_markers = len(re.findall(r"AGENTS-GENERATED:START", text))  # 生成区块起点数量

    # 统计生成区块终点数量，确保受管片段没有半截残留。
    int_end_markers = len(re.findall(r"AGENTS-GENERATED:END", text))  # 生成区块终点数量

    # 起止数量不相等时，说明受管片段已经发生结构漂移。
    if int_start_markers != int_end_markers:

        # 记录起止数量不平衡的具体诊断，方便直接定位损坏的 AGENTS 文件。
        errors.append(
            f"{file}: generated marker mismatch ({int_start_markers} starts, {int_end_markers} ends)"
        )

# 提取二级标题对应的段落正文。
def section_body(text: str, heading: str) -> str | None:
    """返回指定二级标题的正文内容。

    参数:
        text: 当前待扫描的 AGENTS 文本。
        heading: 目标二级标题，格式应与原文保持一致。

    返回:
        命中的段落正文；未命中标题时返回 `None`。
    """

    # 先定位目标标题在全文中的位置，后续才能切出对应正文。
    obj_match = re.search(rf"^{re.escape(heading)}\s*$", text, flags=re.MULTILINE)  # 目标标题匹配对象

    # 标题不存在时直接返回空结果，让上游继续尝试其他兼容标题。
    if not obj_match:

        # 返回空结果，表示当前标题没有出现在文本中。
        return None

    # 记录正文起点，后续需要从标题末尾继续向下切片。
    int_start = obj_match.end()  # 正文起始偏移量

    # 查找下一个二级标题，借此决定当前段落应该在何处截断。
    match_next_heading = re.search(r"^##\s+", text[int_start:], flags=re.MULTILINE)  # 下一个二级标题匹配对象

    # 没有后续标题时，当前段落一直延伸到文本末尾。
    int_end = int_start + match_next_heading.start() if match_next_heading else len(text)  # 正文结束偏移量

    # 返回标题对应的正文切片，供上游继续做短语校验。
    return text[int_start:int_end]

# 依次尝试多个候选标题，返回第一段命中的正文。
def first_section_body(text: str, headings: tuple[str, ...]) -> str | None:
    """返回第一个命中标题的段落正文。

    参数:
        text: 当前待扫描的 AGENTS 文本。
        headings: 允许按顺序回退尝试的多个标题。

    返回:
        第一段命中的正文；所有标题都未命中时返回 `None`。
    """

    # 依次尝试兼容标题，优先返回最先命中的正文。
    for heading in headings:

        # 提取当前候选标题的正文，命中后即可结束回退流程。
        str_section_body = section_body(text, heading)  # 当前候选标题的正文

        # 只要当前标题命中，就直接把对应正文返回给调用方。
        if str_section_body is not None:

            # 返回首个命中的段落正文，避免后续标题覆盖更精确的结果。
            return str_section_body

    # 所有候选标题都未命中时，返回空结果供上游自行兜底。
    return None

# 读取对象子块；只有映射值才能继续作为治理配置使用。
def mapping_value_or_empty(dict_container: dict[str, Any], str_key: str) -> dict[str, Any]:
    """读取治理配置子块，并在值不是映射时回退为空映射。

    参数:
        dict_container: 父级配置映射。
        str_key: 需要提取的子键名称。

    返回:
        当子键值是映射时返回原对象；否则返回空映射。
    """

    # 先提取调用方请求的子键值，后续统一判断它能否继续按映射处理。
    obj_value = dict_container.get(str_key)  # 候选配置子块

    # 只有字典值才具备继续向下读取字段的结构。
    if isinstance(obj_value, dict):

        # 保留原始映射对象，避免丢失调用方需要的字段层级。
        return obj_value

    # 非映射值统一退回空对象，防止类型错误继续向后级联。
    return {}

# 读取列表子块；只有列表值才能继续作为批量配置使用。
def list_value_or_empty(dict_container: dict[str, Any], str_key: str) -> list[Any]:
    """读取治理配置列表子块，并在值不是列表时回退为空列表。

    参数:
        dict_container: 父级配置映射。
        str_key: 需要提取的列表子键名称。

    返回:
        当子键值是列表时返回原对象；否则返回空列表。
    """

    # 先提取调用方请求的子键值，后续统一判断它能否继续按列表处理。
    obj_value = dict_container.get(str_key)  # 候选配置列表子块

    # 只有列表值才具备继续批量遍历的结构。
    if isinstance(obj_value, list):

        # 保留原始列表对象，避免丢失调用方需要的元素顺序。
        return obj_value

    # 非列表值统一退回空列表，防止类型错误继续向后级联。
    return []

# 把列表值规整成去空白后的字符串列表，统一服务于路由和路径样例校验。
def normalized_nonempty_strings(obj_items: Any) -> list[str]:
    """把任意候选列表规整成去空白后的字符串列表。

    参数:
        obj_items: 调用方提供的候选列表值。

    返回:
        输入是列表时返回去空白后的字符串列表；否则返回空列表。
    """

    # 非列表值不具备批量规整前提，统一回退为空列表。
    if not isinstance(obj_items, list):

        # 非列表值在这里直接跳过，避免调用方重复写类型守卫。
        return []

    # 仅保留去空白后仍有内容的字符串项，避免空白文本污染后续匹配。
    return [str(item).strip() for item in obj_items if str(item).strip()]

# 批量登记布尔条件失败项，减少重复的 if/append 模板。
def append_failed_checks(errors: list[str], list_checks: list[tuple[bool, str]]) -> None:
    """把失败的布尔检查统一追加到错误列表。

    参数:
        errors: 共享错误列表。
        list_checks: 由布尔条件和错误消息组成的检查清单。

    返回:
        无业务返回值；失败消息直接追加到 `errors`。
    """

    # 逐项评估布尔条件，只把失败项对应的诊断写入共享错误列表。
    for bool_condition, str_error_message in list_checks:

        # 条件失败时追加对应诊断，保持调用方提供的错误文本不变。
        if not bool_condition:

            # 把失败消息直接交给调用方的错误列表，避免重复包装文案。
            errors.append(str_error_message)

# 批量核对正文必备短语，减少逐句手写模板式缺失检查。
def append_missing_text_requirements(
    str_body: str,
    list_requirements: list[tuple[str, str]],
    errors: list[str],
) -> None:
    """检查正文是否保留全部必备短语。

    参数:
        str_body: 需要检查的段落正文。
        list_requirements: 必备短语与缺失诊断组成的清单。
        errors: 共享错误列表。

    返回:
        无业务返回值；缺失短语对应的诊断直接追加到 `errors`。
    """

    # 逐条核对正文必备短语，避免渲染文本悄悄丢掉关键执行约束。
    for str_required_text, str_error_message in list_requirements:

        # 只要正文缺失任一短语，就把对应诊断直接写回共享错误列表。
        if str_required_text not in str_body:

            # 使用调用方提供的原始错误文案，保持既有测试断言稳定。
            errors.append(str_error_message)
