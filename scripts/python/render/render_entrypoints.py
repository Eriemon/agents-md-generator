"""实现根级与作用域 AGENTS.md 的渲染入口。"""

# CLI 参数和标准输出依赖用于稳定暴露渲染入口。
import argparse
import json
import os
import sys

# 路径类型用于渲染项目根和可选模板目录。
from pathlib import Path
from typing import Any

# 共享忽略目录保证 scoped 扫描与项目发现一致。
from agents_common import SKIP_DIRS
from agent_platform import (
    global_instruction_file_label,
    load_agent_config,
    load_catalog,
    resolve_agent_profile,
    write_agent_config,
)

# Codebase-memory 写入门禁和 worker 画像负责渲染前的受管能力检查。
from codebase_memory_mcp import enforce_codebase_memory_write_gate

# 语言路由校验器仍由独立模块负责，渲染器只投影压缩后的稳定合同。
from reviewer_worker_profile import REVIEWER_WORKER_SHA256, ensure_reviewer_worker_profile
from tester_worker_profile import ensure_tester_worker_profile
from gardener_worker_profile import ensure_gardener_worker_profile
# 从 render_platform_state 导入拆分后的公共合同函数。
from render_platform_state import (
    _skill_root_from_entrypoint,
    selected_agent_profile,
    _platform_selection_paths,
    _snapshot_platform_path,
    _restore_platform_path,
)

from render_platform_state import (
    _read_selection_state,
    _resolve_migration_state_paths,
    _validate_existing_platform_states,
    _validate_unselected_platform_roots,
    _validate_platform_request,
)

from render_platform_state import (
    _collect_platform_shim_paths,
    _build_platform_selection,
    _write_platform_files,
    _apply_platform_shims,
)

from render_platform_state import (
    _retire_platform_migration,
    _platform_conflict_warnings,
    _filter_platform_shim_paths,
    _merge_platform_warnings,
    ensure_platform_artifacts,
)

# 从 render_write_plan 导入拆分后的公共合同函数。
from render_write_plan import (
    enforce_structure_confirmation,
    apply_confirmed_structure_fix,
    enforce_branch_gate,
    prepare_controlled_write,
    _ensure_worker_profiles_for_write,
)

# 根正文之外的合同引用区保存完整高风险合同，避免受管提示词预算被长句撑大。
def contract_reference_notes(dict_values: dict[str, str] | None = None) -> str:
    """生成根 AGENTS.md 的完整 workspace 与 TESTER 合同引用区。

    参数：dict_values 为当前 profile 渲染出的动态合同映射，可选。
    返回：位于受管区块之外、每次渲染都会替换的完整合同正文。
    """

    # workspace 长合同保留精确授权、路由、图谱和单次确认边界。
    str_workspace_contract = (
        "- **Workspace boundary:** current work folder; verified remote-server work folder. "
        "Changes inside either work folder require no additional confirmation; remote changes remain allowed only "
        "when the configured task route matches that folder. Official codebase-memory start, index refresh, rebuild, "
        "or recovery for the project bound to either work folder, including its configured runtime cache and root "
        "persistence artifact, also requires no additional confirmation. External reads beyond those boundaries must "
        "be necessary and side-effect free. Every other external write is prohibited by default; only after the user "
        "proactively and explicitly requests the exact action. Disclose exact normalized target, action, scope, risks, "
        "alternatives, and recovery limits; obtain exactly one explicit user confirmation. Any target or scope change "
        "invalidates that confirmation. installed skill always requires exactly one explicit user confirmation. "
        "Routine test-hash confirmation is prohibited. The agent may confirm when an authoritative current tests "
        "result agrees with the authoritative current tests tree or receipt. A report-only hash mismatch is "
        "corrected to the authoritative value. Conflicting or insufficient provenance stops for user review "
        "without an autonomous rerun."
    )

    # profile 相关合同必须使用本次渲染结果，避免根文件继续投影旧的静态文案。
    dict_contract_values = dict_values or {}  # 当前动态合同映射

    # 编码行为合同跟随治理 JSON 的注释、命名和路由门禁。
    str_coding_behavior = dict_contract_values.get(  # 编码行为与语言路由合同
        "CODING_BEHAVIOR_BASELINE",  # 编码行为合同字段
        "- 编码行为配置来源：`.agents/global-rule-overrides.json`; `Kind` 列表只从该 JSON 读取；"
        "代码不得内置业务枚举。\n"
        "- 注释质量：只允许非显然意图、不变量、生成边界或公共 API 行为注释；"
        "风险边界需明确；严禁未经明确要求的批量 AI 注释。",
    )  # 当前编码行为合同正文

    # 编码行为配置路径是 verifier 的稳定锚点，必须在引用区保留一次。
    str_reference_coding_behavior = "\n".join(  # 保留完整编码行为引用
        line  # 保留编码行为正文行
        for line in str_coding_behavior.splitlines()  # 遍历编码行为引用行
    )

    # 脚本输出合同跟随治理 JSON 的机器可读与人类可读边界。
    str_script_output_policy = dict_contract_values.get(  # 脚本输出合同
        "SCRIPT_OUTPUT_POLICY",  # 脚本输出合同字段
        "- Script Output Policy: source `.agents/global-rule-overrides.json`; read the `Kind` catalog from that JSON "
        "instead of embedding business enums; use `> INFO: [{kind}]`, `> WARNING: [{kind}]`, and `> ERR: [{kind}]`; "
        "Python process INFO is enabled by default, `--quiet` disables it, WARNING and ERR remain visible, and "
        "machine-readable output has no prefix.",
    )  # 当前脚本输出合同正文

    # 脚本输出来源行是 verifier 的第二个稳定配置锚点，必须保留。
    str_reference_script_output_policy = "\n".join(  # 保留完整脚本输出引用
        line  # 保留脚本输出正文行
        for line in str_script_output_policy.splitlines()  # 遍历脚本输出引用行
    )

    # 自定义引用标记让下一次渲染能够安全移除旧引用而不触碰人工笔记。
    return "\n".join(
        [
            "<!-- AGENTS-CONTRACT-REFERENCE:START -->",
            "## Contract reference notes",
            str_workspace_contract,
            str_reference_coding_behavior,  # 当前治理 JSON 的编码行为和路由合同。
            str_reference_script_output_policy,  # 当前治理 JSON 的脚本输出合同。
            "<!-- AGENTS-CONTRACT-REFERENCE:END -->",
        ]
    )

# 根正文按稳定顺序连接项目事实、命令和局部约束。
def generated_root_body(
    project: Path,
    dict_values: dict[str, str],
    manual: str = "",
    agent_profile: Any | None = None,
) -> str:
    """
    生成默认模板和自定义模板共享的根正文。

    参数:
        project: 用于生成 scoped 索引和项目摘要的仓库根目录。
        dict_values: 已发现并渲染的项目事实、命令和门禁文本。
        manual: 受管块之外需要保留的人工维护文本。
        agent_profile: 可选平台配置，用于渲染平台相关摘要。
    返回:
        以单个换行结尾的根 AGENTS.md 正文。
    """

    # 修改前阅读段在组装前合并纯文档指针，保留工具和样例规则。
    str_read_before_changing = compact_read_before_changing(  # 修改前阅读入口
        dict_values["READ_BEFORE_CHANGING"]  # 原始修改前阅读规则
    )  # 压缩后的修改前阅读规则

    # 先构造受管阅读段，列表组装只引用已命名的段落结果。
    str_read_section = compact_section(  # 修改前阅读受管段结果
        "read-before-changing",  # 修改前阅读段落标识
        "Read before changing",  # 修改前阅读段落标题
        str_read_before_changing,  # 已压缩的修改前阅读内容
    )  # 修改前阅读受管段

    # 固定段落顺序保证重新生成时 diff 稳定。
    list_parts = [
        "<!-- FOR AI AGENTS - Human readability is a side effect, not a goal -->",  # 生成文件用途声明。
        "<!-- Managed by agent: keep sections and order; edit content outside AGENTS-GENERATED blocks -->",  # 受管边界编辑提示。
        f"<!-- Last updated: {dict_values['TIMESTAMP']} | Last verified: {dict_values['VERIFIED_TIMESTAMP']} -->",  # 更新时间与复核时间。
        (
            f"<!-- AGENTS-METADATA: agents_version={dict_values['AGENTS_VERSION']}; "
            f"generator_version={dict_values['GENERATOR_VERSION']}; "
            f"default_language={dict_values['DEFAULT_LANGUAGE']} -->"
        ),
        "# AGENTS.md",  # 根规则标题。
        (
            "**Precedence:** the closest `AGENTS.md` to the files being changed wins. "
            "Explicit user prompts override this file."
        ),
        compact_section("project", "Project", project_section(dict_values, agent_profile)),  # 项目身份受管段。
        commands_section(dict_values),  # 已发现命令受管段。
        compact_section("task-specific-gates", "Task-specific gates", dict_values["TASK_SPECIFIC_GATES"]),  # 项目专用门禁段。
        compact_section("local-conventions", "Local conventions", local_conventions_section(dict_values)),  # 本地执行约定段。
        str_read_section,  # 列表引用已预先压缩的阅读段
        compact_section("scoped-instructions", "Scoped instructions", scoped_instructions(project)),  # 下级规则索引段。
        (
            "## When Instructions Conflict\n"
            "- Conflicts: explicit user prompt > closest `AGENTS.md` > parent > repository docs."
        ),
        contract_reference_notes(dict_values),  # 当前 profile 的完整高风险合同引用区
    ]  # 根文件候选段落。

    # 人工文本只在实际存在时附加，避免空段落改变末尾格式。
    if manual:

        # 受管正文之后保留人工维护区域。
        list_parts.append(manual)

    # 空段落在连接前过滤，正文统一保留一个末尾换行。
    return "\n".join(str_part for str_part in list_parts if str(str_part).strip()).rstrip() + "\n"

# 项目摘要只保留影响代理执行的身份和控制字段。
def project_section(dict_values: dict[str, str], agent_profile: Any | None = None) -> str:
    """
    渲染项目身份和控制摘要。

    参数:
        dict_values: 包含项目概览和强控制摘要的事实映射。
        agent_profile: 可选平台配置，用于生成全局指令文件标签。
    返回:
        按输入顺序去重后的项目摘要文本。
    """

    # 输出行按项目概览在前、控制配置在后的顺序累积。
    list_lines: list[str] = []  # 待渲染项目摘要。

    # 项目概览排除会与生成元数据重复的根文件状态。
    for str_line in dict_values["PROJECT_OVERVIEW"].splitlines():

        # 去除缩进后再判断空行和重复字段。
        str_stripped = str_line.strip()  # 当前项目概览行。

        # 根摘要只保留身份、基线和版本的决策信息，详细画像仍在 profile 中。
        if str_stripped.startswith("Primary language:"):

            # 根摘要不重复固定的主语言字段。
            continue

        # 全局基线状态需要统一为当前工作文件夹的读取提示。
        elif (
            str_stripped.startswith("Global ")
            and str_stripped.endswith(": managed; read current work folder root AGENTS.md.")
        ):

            # 统一后的状态行避免把完整全局文件正文复制到项目摘要。
            str_stripped = (
                f"{global_instruction_file_label(agent_profile or selected_agent_profile())}: managed; "
                "read current work folder root AGENTS.md."
            )  # 紧凑全局基线行

        # 仅保留非空且非根 AGENTS 状态的事实。
        if str_stripped and "Root AGENTS.md:" not in str_stripped:

            # 项目身份事实保持原出现顺序。
            list_lines.append(str_stripped)

    # 强控制摘要只公开允许进入根规则的稳定字段。
    tuple_allowed_prefixes = (
        "- Strong control:",  # 强控制完成状态。
        "- Name:",  # 项目标识名称。
        "- Version:",  # 项目声明版本。
        "- Default conversation language:",  # 默认对话语言。
        "- Local governance detail source:",  # 本地治理配置来源。
    )  # 可公开控制字段前缀。

    # 控制配置逐行筛选，避免把完整 profile 复制进 AGENTS.md。
    for str_line in dict_values["CONTROL_PROFILE"].splitlines():

        # 空白规范化后执行精确策略判断。
        str_stripped = str_line.strip()  # 当前控制配置行。

        # 未配置占位和空行不进入项目摘要。
        if not str_stripped or str_stripped == "- Strong control: not configured.":

            # 跳过没有执行价值的占位文本。
            continue

        # 只有白名单字段能够进入生成段落。
        if str_stripped.startswith(tuple_allowed_prefixes):

            # 用短用途说明代替会与完整文档重复的解释段。
            if str_stripped.startswith("- Purpose/reason:"):

                # 用短用途说明代替重复的设计解释。
                str_stripped = "- Purpose: govern AGENTS.md rules and reduce drift."  # 精简用途说明

            # 根摘要只保留本地治理配置路径，避免复制解释性长文。
            elif str_stripped.startswith("- Local governance detail source:"):

                # 配置路径由合同引用区统一声明，项目摘要只保留导航语义。
                str_stripped = "- Rules: see `AGENTS-CONTRACT-REFERENCE`."  # 精简治理导航摘要

            # 控制摘要保持 profile 原始措辞。
            list_lines.append(str_stripped)

    # 顺序去重器消除概览与 profile 的重复身份行。
    return render_unique_lines(list_lines)

# Commands 段仅在发现真实命令时出现。
def commands_section(dict_values: dict[str, str]) -> str:
    """渲染非空命令表。

    参数：dict_values 为项目事实映射。
    返回：命令表 Markdown；没有真实命令时返回空文本。
    """

    # 行限制器应用仓库命令表的展示上限。
    str_rows = limit_command_rows(dict_values["COMMAND_ROWS"]).strip()  # 可展示命令行。

    # 空命令表不生成标题或表头。
    if not str_rows:

        # 调用方会过滤空段落。
        return ""

    # 受管标记包围命令表，支持后续精确替换。
    return "\n".join(
        [
            f"{GENERATED_START} commands -->",
            "## Commands",
            "| Task | Command | ~Time | Source |",
            "|------|---------|-------|--------|",
            str_rows,
            "<!-- AGENTS-GENERATED:END commands -->",
        ]
    )

# 压缩常规本地约定，保留 verifier 所需的固定短语。
def _compact_basic_convention_line(str_line: str) -> str:
    """将常规本地约定映射为短规则或吸收标记。

    参数:
        str_line: 已去除空白合同块中的一行。
    返回:
        压缩后的规则行；被上层合同吸收的行返回 None。
    """

    # 会话语言规则只替换旧短语，不改变其他技术字面量。
    if str_line.startswith("- Natural-language replies"):

        # 会话语言已由项目元数据承载，根级 local-conventions 不重复输出。
        return None

    # 其他常规规则使用前缀到固定输出的映射，避免重复分支。
    if str_line.startswith("- 配置来源："):

        # 编码行为配置行已经声明脚本输出共用同一来源，删除重复入口。
        return None

    # 固定前缀映射承载不依赖跨行状态的本地约定压缩规则。
    tuple_fixed_lines = (  # 常规本地约定映射
        ("- Natural-language replies", None),  # 会话语言已由项目元数据承载。
        ("- Finish feasible requested work", None),  # 吸收完成解释行。
        (
            "- Run narrow then final checks",  # 完成检查前缀。
            None,  # 检查合同已由 task-specific fast-convergence 规则承载。
        ),
        (
            "- 注释质量：",  # 注释合同前缀。
            "- 注释质量：只允许非显然意图、不变量、风险、生成边界或公共 API 行为注释；"
            "严禁把代码压缩到一行；炫技代码。",
        ),
        (
            "- 格式：",  # 输出格式合同前缀。
            None,  # 输出模板由 Script Output Policy 行统一承载。
        ),
        (
            "- 编码行为配置来源：",  # 编码行为配置前缀。
            "- 编码行为配置来源：`.agents/global-rule-overrides.json`。",  # 编码配置来源短文本。
        ),
        ("- 配置来源：", None),  # 配置来源已由上方脚本输出分支处理。
        ("- 生成代码须", None),  # 生成合同前缀。
        ("- 文件命名：", "- 文件命名：功能语义英文名≤30字符；Agent复核。"),  # 命名规则映射。
        ("- 文件命名语义：", None),  # 语义复核已并入文件命名规则。
    )

    # 按原始合同顺序匹配一条常规压缩规则。
    for str_prefix, str_replacement in tuple_fixed_lines:

        # 只有前缀命中时才替换或吸收当前行。
        if str_line.startswith(str_prefix):

            # None 表示当前语义已由上层合同完整承载。
            return str_replacement

    # 未命中的常规行保持原文，交给后续路由判断。
    return str_line

# 压缩双语言技能路由合同，保留两技能共同门禁和最终所有权。
def _compact_skill_route_line(str_line: str) -> str | None:
    """将双技能路由行转换为固定短合同。

    参数:
        str_line: 已去除空白合同块中的一行。
        返回:
        压缩后的路由规则行、原始行或已合并的 None。
    """

    # 三类路由的 compact_text 从 packaged structured config 读取。
    list_route_config_paths: list[Path] = [
        Path.cwd() / ".agents" / "global-rule-overrides.json",  # 当前项目的治理覆盖配置。
        Path(__file__).resolve().parents[3] / "config" / "language-routes.json",  # Skill 内置路由配置。
    ]  # 项目覆盖优先于 packaged 默认。

    # 只解析第一个存在的 structured route 配置，不使用渲染代码内的固定短文案。
    try:

        # 优先读取当前项目覆盖，缺失时使用 Skill 内置配置。
        path_route_config: Path = next(  # 受管语言路由配置文件。
            path_item  # 当前候选配置路径。
            for path_item in list_route_config_paths  # 按优先级遍历配置候选。
            if path_item.is_file()  # 仅接受存在的普通文件。
        )

        # JSON 路由对象是压缩文案的唯一事实来源。
        obj_route_config: object = json.loads(path_route_config.read_text(encoding="utf-8"))  # 已读取的路由配置对象。

    # 配置缺失或损坏时保留原始行，避免生成未经批准的替代文本。
    except (OSError, UnicodeError, json.JSONDecodeError):

        # 无法证明配置完整时不压缩当前文案。
        return str_line

    # packaged 路由直接位于 routes 根，项目覆盖使用嵌套 structured 节点。
    dict_route_records: dict[str, object] = (  # 优先使用 packaged 路由记录。
        obj_route_config.get("routes", {})  # 读取 packaged routes 根节点。
        if isinstance(obj_route_config, dict) and isinstance(obj_route_config.get("routes", {}), dict)  # 仅接受对象路由映射。
        else {}  # 非对象路由退回空映射。
    )

    # 项目 override 可能把结构化路由放在 coding_behavior 下。
    if not dict_route_records and isinstance(obj_route_config, dict):

        # 读取项目编码行为覆盖映射。
        obj_coding_behavior: object = obj_route_config.get("coding_behavior", {})  # 项目编码行为配置。

        # 读取嵌套的语言技能路由节点。
        obj_language_routes: object = (  # 项目语言技能路由节点。
            obj_coding_behavior.get("language_skill_routing", {})  # 从项目编码行为读取语言路由。
            if isinstance(obj_coding_behavior, dict)  # 仅对象配置允许读取嵌套字段。
            else {}  # 非对象配置退回空节点。
        )

        # 读取结构化路由记录，禁止回退到旧字符串字段。
        dict_route_records = (  # 项目结构化路由记录。
            obj_language_routes.get("structured", {})  # 从语言路由节点读取 structured 记录。
            if isinstance(obj_language_routes, dict) and isinstance(obj_language_routes.get("structured", {}), dict)  # 仅对象节点允许读取结构化字段。
            else {}  # 非对象节点退回空记录。
        )

    # 路由前缀到结构化记录键的映射由合同固定。
    dict_prefix_keys: dict[str, str] = {
        "- 语言技能共同门禁：": "shared",  # shared 双技能共同门禁。
        "- 语言技能路由（Python）：": "python",  # Python 最终 owner 路由。
        "- 语言技能路由（脚本）：": "script",  # 脚本最终 owner 路由。
    }

    # 逐类判断路由前缀，并保持未安装双技能时的原始文本。
    for str_prefix, str_route_key in dict_prefix_keys.items():

        # 非当前路由行继续尝试下一个合同前缀。
        if not str_line.startswith(str_prefix):

            # 当前行没有命中该路由前缀。
            continue

        # 路由正文必须同时出现两个语言技能名称才能被压缩。
        str_route_body: str = str_line.split("：", 1)[1].strip()  # 当前路由正文。

        # 分别记录 Python 和脚本技能是否存在。
        bool_python_skill: bool = "readable-python-generator" in str_route_body  # Python 技能存在状态。

        # 读取脚本技能标记是否存在。
        bool_script_skill: bool = "readable-script-generator" in str_route_body  # 脚本技能存在状态。

        # 只有双技能齐全时才允许替换为固定合同。
        bool_both_skills: bool = bool_python_skill and bool_script_skill  # 双技能可用状态。

        # 双技能齐全时使用配置 compact_text，否则保留原始配置行。
        dict_route_record: dict[str, object] = (  # 当前 owner 的路由记录。
            dict_route_records.get(str_route_key, {})  # 读取当前 owner 的结构化记录。
            if isinstance(dict_route_records.get(str_route_key, {}), dict)  # 仅对象记录允许按 owner 查询。
            else {}  # 非对象记录不参与压缩。
        )

        # 读取当前 owner 在双技能安装态下的 compact 文案。
        str_compact_text: str = (  # 当前 owner 的精简路由正文。
            str(dict_route_record.get("compact_text", "")).strip()  # 读取并清理 compact 文案。
            if isinstance(dict_route_record, dict)  # 当前记录提供 compact_text。
            else ""  # 非对象记录不能生成压缩文案。
        )

        # 只有两个 owner 都存在且文案非空时才替换原行。
        return f"{str_prefix}{str_compact_text}" if bool_both_skills and str_compact_text else str_line

    # 未命中的其他行保持原文。
    return str_line

# 统一派发常规与技能路由两类合同压缩。
def _compact_local_convention_line(str_line: str) -> str | None:
    """压缩一条本地约定，保留机器校验所需的固定短语。

    参数:
        str_line: 已去除空白合同块中的一行。
    返回:
        压缩后的规则行；被上层合同吸收的行返回 None。
    """

    # 常规前缀集合用于把普通合同和路由合同分流到各自 helper。
    tuple_basic_prefixes = (
        "- Natural-language replies",  # 会话语言前缀。
        "- Finish feasible requested work",  # 完成解释前缀。
        "- Run narrow then final checks",  # 最终检查合同前缀。
        "- 注释质量：",  # 注释质量前缀。
        "- 格式：",  # 输出格式前缀。
        "- 编码行为配置来源：",  # 编码配置来源前缀。
        "- 配置来源：",  # 配置来源前缀。
        "- 生成代码须",  # 代码生成合同入口。
        "- 文件命名：",  # 文件命名前缀。
        "- 文件命名语义：",  # 命名语义前缀。
    )

    # 常规合同由固定前缀 helper 处理，返回 None 表示已被吸收。
    if str_line.startswith(tuple_basic_prefixes):

        # 普通约定压缩不会再进入语言技能路由分支。
        return _compact_basic_convention_line(str_line)

    # 其他合同交给双技能路由 helper 处理并保留未命中的原文。
    return _compact_skill_route_line(str_line)

# 本地约定段落只负责组合合同和稳定去重。
def local_conventions_section(dict_values: dict[str, str]) -> str:
    """合并本仓库的执行约定。

    参数：dict_values 为项目事实映射。
    返回：按合同顺序连接的本地约定。
    """

    # 会话语言锁属于本地执行约定，必须与导航指针位于同一受管段。
    str_conversation_contract = dict_values.get("CONVERSATION_COMPLETION_CONTRACT", "")  # 会话完成合同正文

    # 详细规则由合同引用区和 JSON 配置承载，本段保留导航指针和会话锁。
    return "\n".join(
        part
        for part in [
            "- Local conventions: see `AGENTS-CONTRACT-REFERENCE`.",
            str_conversation_contract,
        ]
        if str(part).strip()
    )

# 仅文档指针合并为单一入口，避免根索引重复占用预算。
def compact_read_before_changing(str_rules: str) -> str:
    """合并仅由文档指针组成的修改前阅读规则。

    参数:
        str_rules: 当前项目探测得到的修改前阅读规则。
    返回:
        文档指针的紧凑入口；包含工具或样例事实时保留原始规则。
    """

    # 过滤空行和低信息量目录候选，只压缩真实文档指针。
    list_lines = [
        str_line.strip()  # 规则行去除两端空白
        for str_line in str_rules.splitlines()  # 遍历修改前阅读规则
        if str_line.strip() and "Directory coverage candidate:" not in str_line  # 排除目录候选
    ]  # 当前项目的修改前阅读规则

    # 判断当前规则是否全部是文档指针。
    bool_pointer_only = bool(list_lines) and all(  # 纯文档指针状态
        str_line.startswith("- Use `docs/") and "as a pointer" in str_line  # 单条文档指针判断
        for str_line in list_lines  # 当前规则行集合
    )  # 所有规则均为文档指针

    # 混入其他事实时继续保留逐条规则，维护具体阅读顺序。
    if not bool_pointer_only:

        # 非文档事实不能被合并，否则会丢失工具或样例入口。
        return str_rules

    # 文档路径从反引号中提取，避免硬编码当前项目的发现结果。
    list_paths = [str_line.split("`", 2)[1] for str_line in list_lines]  # 文档指针路径

    # 路径列表用短逗号格式保持根规则可读。
    str_paths = ", ".join(f"`{str_path}`" for str_path in list_paths)  # 合并后的路径文本

    # 一个入口保留所有文档路径和禁止复制正文的约束。
    return f"- Use {str_paths} as pointers; do not copy long documentation into AGENTS.md."

# scoped 索引只包含已有且具有真实局部覆盖的文件。
def scoped_instructions(project: Path) -> str:
    """发现需要从根文件索引的 scoped AGENTS.md。

    参数：project 为仓库根。
    返回：按相对文件位置排序的 scoped 指令索引。
    """

    # 索引行按文件系统相对位置稳定排序。
    list_lines: list[str] = []  # 有效 scoped 指令条目。

    # 递归扫描已有 AGENTS.md，再应用根文件和忽略目录过滤。
    for path_agents in sorted(project.rglob("AGENTS.md")):

        # 根 AGENTS.md 不能索引自身。
        if path_agents == project / "AGENTS.md":

            # 当前候选由根正文直接表示。
            continue

        # 缓存、构建和依赖目录中的文件不属于项目作用域。
        if any(str_part in SKIP_DIRS for str_part in path_agents.relative_to(project).parts):

            # 忽略目录遵循共享扫描策略。
            continue

        # 只有真实人工覆盖才值得在根文件中公开。
        if not scoped_agents_has_local_overrides(path_agents):

            # 纯脚手架文件不会增加代理路由价值。
            continue

        # POSIX 相对表示保证跨平台生成文本稳定。
        str_relative = path_agents.relative_to(project).as_posix()  # scoped 文件相对位置。

        # 根索引明确说明下级文件覆盖范围。
        list_lines.append(f"- `./{str_relative}` - local override rules for this subtree.")

    # 没有局部覆盖时返回空段落。
    return "\n".join(list_lines)

# 脚手架固定文本不应被误判为人工局部规则。
def scoped_agents_has_local_overrides(agents_path: Path) -> bool:
    """判断 scoped AGENTS.md 是否包含真实人工差异。

    参数：agents_path 为待检查 scoped 文件。
    返回：存在受管块异常或非脚手架人工文本时为 True。
    """

    # 文件读取失败按无可用人工覆盖处理。
    try:

        # 宽容解码允许检查包含遗留字符的规则文件。
        str_text = agents_path.read_text(encoding="utf-8", errors="ignore")  # scoped 文件文本。

    # 读取异常不能阻断整个根规则生成流程。
    except OSError:

        # 不可读文件不进入根索引。
        return False

    # 受管起止标记不平衡本身需要人工关注。
    if str_text.count(GENERATED_START) != str_text.count(GENERATED_END):

        # 异常生成边界视为真实差异。
        return True

    # 固定脚手架行允许在没有人工规则时保持沉默。
    set_fixed_lines = {
        "## Human Notes",  # 人工说明标题。
        "## When Stuck",  # 默认受阻处理标题。
        "- Read parent AGENTS.md.",  # 默认父级规则读取提示。
        "- Inspect nearest similar implementation and tests.",  # 默认相邻实现检查提示。
        "- Ask before inventing local conventions.",  # 默认不确定性升级提示。
        "## House Rules",  # 默认人工规则标题。
        "<!-- Human-maintained local rules go here. -->",  # 默认人工规则占位。
    }  # 可忽略脚手架整行。

    # 作用域标题、范围和优先级通过前缀匹配忽略。
    tuple_fixed_prefixes = (
        "# AGENTS.md - ",  # scoped 文件标题前缀。
        "**Scope:** this file applies to ",  # 作用域声明前缀。
        "**Precedence:** this file overrides parent AGENTS.md files for files inside this scope.",  # scoped 优先级声明。
    )  # 可忽略脚手架前缀。

    # 受管块之外逐行寻找非脚手架文本。
    for str_line in manual_content(str_text).splitlines():

        # 空白规范化后与固定集合比较。
        str_stripped = str_line.strip()  # 当前人工区域行。

        # 空行、固定行和固定前缀均不构成局部覆盖。
        if not str_stripped or str_stripped in set_fixed_lines or str_stripped.startswith(tuple_fixed_prefixes):

            # 继续寻找真正的人工规则。
            continue

        # 首个非脚手架行即可证明局部差异。
        return True

    # 所有人工区域行均为脚手架默认文本。
    return False

# 顺序去重器保留首次出现并丢弃空白行。
def render_unique_lines(lines: list[str]) -> str:
    """按出现顺序连接唯一非空行。

    参数：lines 为原始文本行。
    返回：换行连接的稳定唯一行。
    """

    # 集合提供常数时间的已见判断。
    set_seen: set[str] = set()  # 已输出规范化行。

    # 列表保持首次出现的原始顺序。
    list_rendered: list[str] = []  # 最终唯一行。

    # 每个候选先规范化空白再参与去重。
    for str_line in lines:

        # 边缘空白不属于行身份。
        str_stripped = str_line.strip()  # 当前规范化行。

        # 空行或重复行不进入输出。
        if not str_stripped or str_stripped in set_seen:

            # 跳过不会增加信息的候选。
            continue

        # 集合和顺序列表必须同步更新。
        set_seen.add(str_stripped)

        # 首次出现的行进入最终文本。
        list_rendered.append(str_stripped)

    # 唯一行以单换行连接。
    return "\n".join(list_rendered)

# scoped 文件只在目录具有明确局部配置时自动创建。
def scope_requires_local_agents(scope_dir: Path) -> bool:
    """判断作用域目录是否需要新的局部规则文件。

    参数：scope_dir 为候选作用域目录。
    返回：存在任一本地配置标记时为 True。
    """

    # 标记覆盖常见语言、构建和预提交配置。
    tuple_local_markers = (
        "AGENTS.local.md",  # 显式局部代理规则。
        "package.json",  # Node.js 局部包配置。
        "pyproject.toml",  # Python 局部项目配置。
        "go.mod",  # Go 局部模块配置。
        "Cargo.toml",  # Rust crate 边界标记。
        "pom.xml",  # Maven 模块边界标记。
        "Makefile",  # 目录级构建入口标记。
        ".pre-commit-config.yaml",  # 目录级提交前检查标记。
    )  # 可触发 scoped 文件的局部标记。

    # 任一标记存在即说明目录具有独立执行上下文。
    return any((scope_dir / str_marker).exists() for str_marker in tuple_local_markers)

# 根渲染器保留人工文本，并允许自定义模板包裹统一正文。
def render_root(
    project: Path,
    template_dir: Path | None = None,
    profile: dict | None = None,
    agent_profile: Any | None = None,
) -> str:
    """渲染根 AGENTS.md。

    参数：project 为仓库根。
    参数：template_dir 为可选自定义模板目录。
    参数：profile 为可选强控制配置。
    参数：agent_profile 为本次显式解析的平台画像。
    返回：完整根规则文本。
    """

    # 已有根文件提供受管块之外的人工文本。
    path_agents = project / "AGENTS.md"  # 根规则文件。

    # 首次生成时没有可保留文本。
    str_existing = (
        path_agents.read_text(encoding="utf-8", errors="ignore")  # 已有根规则文本。
        if path_agents.exists()  # 仅已有文件可读取。
        else ""  # 首次生成使用空文本。
    )  # 人工区域提取来源文本。

    # 项目事实由共享发现器统一生成。
    dict_values = template_values(project, profile, template_dir, agent_profile)  # 根模板替换事实。

    # 人工区域去除边缘空白后进入统一正文。
    str_manual = manual_content(str_existing).strip()  # 待保留人工文本。

    # 默认和自定义模板路径共享完全相同的生成正文。
    str_generated_body = generated_root_body(project, dict_values, str_manual, agent_profile)  # 统一根正文。

    # 默认路径直接返回统一正文。
    if template_dir is None:

        # 无外层模板时不执行额外占位替换。
        return str_generated_body

    # 自定义模板缺少 GENERATED_BODY 占位时在末尾安全追加。
    str_template = load_template(template_dir, "root-agents.md")  # 自定义根模板。

    # 外部模板必须有承载统一正文的位置。
    if "{{GENERATED_BODY}}" not in str_template:

        # 追加占位符保持旧模板兼容。
        str_template = str_template.rstrip() + "\n{{GENERATED_BODY}}\n"  # 兼容旧模板的正文插槽。

    # 复制事实映射避免修改发现器返回对象。
    dict_template_values = dict(dict_values)  # 自定义模板替换事实。

    # 统一正文去除末尾换行后写入模板占位符。
    dict_template_values["GENERATED_BODY"] = str_generated_body.rstrip()  # 模板正文替换值。

    # 自定义模板渲染后统一一个末尾换行。
    return replace_placeholders(str_template, dict_template_values).rstrip() + "\n"

# scoped 渲染器用稳定默认合同填充局部模板。
def render_scoped(
    scope: dict[str, str],
    template_dir: Path | None = None,
) -> str:
    """渲染单个作用域 AGENTS.md。

    参数：scope 提供作用域位置和用途。
    参数：template_dir 为可选自定义模板目录。
    返回：完整 scoped 规则文本。
    """

    # 作用域位置同时用于标题名称和范围说明。
    str_scope_path = scope["path"]  # 当前作用域相对位置。

    # 缺少自定义目录时使用安装包默认模板。
    str_template = load_template(  # scoped 模板文本。
        template_dir or default_template_dir(),  # 自定义或内置模板目录。
        "scoped-agents.md",  # 固定局部模板文件名。
    )  # 局部规则占位模板。

    # 默认局部合同要求调用方先检查目录后再扩展。
    dict_values = {
        "TIMESTAMP": current_timestamp(),  # 生成时间。
        "VERIFIED_TIMESTAMP": "never",  # 新文件尚未人工复核。
        "SCOPE_NAME": str_scope_path,  # 作用域显示名称。
        "SCOPE_PATH": str_scope_path,  # 作用域匹配位置。
        "SCOPE_OVERVIEW": f"{scope['purpose']}.",  # 作用域用途摘要。
        "LOCAL_COMMANDS": "Use root AGENTS.md commands unless this directory has its own package/config file.",  # 命令继承规则。
        "TESTING_RULES": "Run the narrowest relevant tests for files changed in this scope.",  # 局部测试规则。
        "LOCAL_STRUCTURE": "Document local key files here after inspecting this directory.",  # 局部结构说明。
        "CODE_STYLE": "Follow nearby files in this scope before introducing new patterns.",  # 局部代码风格。
        "GIT_WORKFLOW": "Follow root git workflow unless this scope documents a stricter local rule.",  # 局部 Git 继承规则。
        "LOCAL_BOUNDARIES": "- Ask before changing local public APIs, generated files, or ownership boundaries.",  # 局部变更边界。
        "SCOPE_PURPOSE": scope["purpose"],  # 原始作用域用途。
    }

    # 占位替换完成后统一一个末尾换行。
    return replace_placeholders(str_template, dict_values).rstrip() + "\n"

# CLI 参数解析器集中公开渲染和治理确认开关。
def build_render_parser() -> argparse.ArgumentParser:
    """构造渲染命令行解析器。

    参数：无。
    返回：声明项目、写入、模板、profile 和三个确认开关的解析器。
    """

    # 解析器描述保持公开命令帮助文本稳定。
    parser = argparse.ArgumentParser(  # AGENTS 渲染 CLI 参数合同。
        description="Render AGENTS.md from discovered project facts."  # CLI 帮助摘要。
    )  # 渲染命令解析器。

    # 项目位置缺省为当前工作目录。
    parser.add_argument("project", nargs="?", default=".")

    # 默认只打印根草稿，显式 --write 才允许落盘。
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write AGENTS.md files. Default prints root draft only.",
    )

    # 自定义目录必须同时提供根模板和 scoped 模板。
    parser.add_argument(
        "--template-dir",
        default=None,
        help="Directory containing root-agents.md and scoped-agents.md.",
    )

    # profile 参数允许调用方指定强控制配置文件。
    parser.add_argument(
        "--profile",
        default=None,
        help="Path to .agents/agents-control.json for strong-control rendering.",
    )

    # 平台选择从 agent-platforms.json 读取，不在 CLI 内嵌目录名称。
    parser.add_argument(
        "--agent-platform",
        choices=tuple(load_catalog()["platforms"]),
        default=None,
        help="Select the native agent platform for workspace state and shims.",
    )

    # 平台迁移必须同时给出旧平台和显式确认，禁止静默退休旧状态。
    parser.add_argument(
        "--migrate-platform-from",
        choices=tuple(load_catalog()["platforms"]),
        default=None,
        help="Retire a managed-only prior platform selection after explicit confirmation.",
    )

    # 单独的确认开关控制来源平台状态的退休动作。
    parser.add_argument(
        "--confirm-platform-migration",
        action="store_true",
        help="Confirm retiring the prior platform selection during a platform migration.",
    )

    # 文档布局确认只覆盖 docs 脚手架创建决策。
    parser.add_argument(
        "--confirm-docs-layout",
        action="store_true",
        help=(
            "User confirmed that docs governance may be added under "
            "the existing docs/ layout."
        ),
    )

    # 结构修复确认允许执行治理器建议的可逆移动。
    parser.add_argument(
        "--confirm-structure-fix",
        action="store_true",
        help=(
            "User explicitly confirmed applying recommended structure "
            "normalization before writing."
        ),
    )

    # 分支治理确认仅解除 Git 索引跟踪，不能覆盖 worktree 阻断或删除本地产物。
    parser.add_argument(
        "--confirm-branch-governance",
        action="store_true",
        help=(
            "User explicitly confirmed continuing after a blocked "
            "branch governance check."
        ),
    )

    # 确认开关只解除 Git 索引跟踪，不删除根级本地产物。
    parser.add_argument(
        "--confirm-codebase-memory-untrack",
        action="store_true",
        help="User confirmed removing .codebase-memory from the Git index while keeping local files.",
    )

    # 冗余 scoped 迁移默认只报告，和 --write 组合时才删除纯生成脚手架。
    parser.add_argument(
        "--migrate-redundant-scopes",
        action="store_true",
        help="Report generated-only scoped AGENTS.md files; combine with --write to remove them.",
    )

    # 已有 tester_worker 配置刷新时保留显式调用方意图字段。
    parser.add_argument(
        "--confirm-tester-worker-update",
        action="store_true",
        help="Confirm refreshing an existing tester_worker profile after its backup is shown.",
    )

    # gardener 配置刷新同样要求在展示备份后取得显式确认。
    parser.add_argument(
        "--confirm-gardener-worker-update",
        action="store_true",
        help="Confirm refreshing an existing gardener_worker profile after its backup is shown.",
    )

    # 三个 profile 与 gardener 工具的新写入流程共用 bundle 收据。
    parser.add_argument(
        "--confirm-profile-bundle-sha256",
        default="",
        help="Confirm the exact tester/reviewer/gardener profile bundle SHA-256.",
    )

    # 调用方负责执行 parse_args，便于测试解析器合同。
    return parser

# scoped 迁移只选择可证明没有人工内容的生成脚手架。
def migrate_redundant_scopes(project: Path, bool_write: bool) -> dict[str, object]:
    """报告或删除冗余的 scoped AGENTS.md 脚手架。

    参数：project 为项目根；bool_write 控制是否实际删除。
    返回：候选、删除结果和保留文件组成的机器可读报告。
    """

    # 候选集合只记录可证明没有人工局部规则的文件。
    list_candidates: list[str] = []  # 可安全迁移的纯脚手架

    # 保留集合解释哪些 scoped 文件因真实差异而不能删除。
    list_preserved: list[str] = []  # 含人工内容或未知来源的 scoped 文件

    # 删除集合只在显式写入模式下产生记录。
    list_removed: list[str] = []  # 写入模式实际删除的文件

    # 根文件不属于 scoped 迁移范围。
    for path_agents in sorted(project.rglob("AGENTS.md")):

        # 仓库根规则永远不参与 scoped 脚手架迁移。
        if path_agents == project / "AGENTS.md":

            # 继续扫描真正的子目录规则文件。
            continue

        # 忽略治理扫描已排除的目录。
        if any(str_part in SKIP_DIRS for str_part in path_agents.relative_to(project).parts):

            # 跳过缓存、发布包和其他非源码目录。
            continue

        # 文件正文用于区分生成脚手架与人工维护规则。
        str_text = path_agents.read_text(encoding="utf-8", errors="ignore")  # 当前 scoped 正文。

        # 报告统一使用项目相对 POSIX 路径。
        str_relative = path_agents.relative_to(project).as_posix()  # 可移植报告路径。

        # 管理声明或受管区块提供生成来源证据。
        bool_generated = "Managed by agent" in str_text or "AGENTS-GENERATED:START" in str_text  # 生成来源证据。

        # 来源不明或含真实局部覆盖时必须保留。
        if not bool_generated or scoped_agents_has_local_overrides(path_agents):

            # 保留原因由候选集合的互斥关系表达。
            list_preserved.append(str_relative)

            # 已确认保留的文件不再进入迁移候选。
            continue

        # 纯生成脚手架进入 dry-run 和写入模式共享的候选清单。
        list_candidates.append(str_relative)

        # 只有调用方明确请求写入时才删除候选文件。
        if bool_write:

            # 删除范围限定为当前已经验证的单个 scoped 文件。
            path_agents.unlink()

            # 删除成功后记录相对路径作为审计证据。
            list_removed.append(str_relative)

    # dry-run 和写入模式共享稳定字段，便于自动化审查。
    return {
        "mode": "write" if bool_write else "dry-run",
        "candidates": list_candidates,
        "removed": list_removed,
        "preserved": list_preserved,
        "errors": [],
    }

# 待写入集合只新增具有真实局部配置的缺失 scoped 文件。
def collect_pending_writes(
    project: Path,
    str_root_text: str,
    template_dir: Path | None,
) -> list[tuple[Path, str]]:
    """收集根文件和必要 scoped 文件的写入候选。

    参数：project 为仓库根。
    参数：str_root_text 为最终根规则文本。
    参数：template_dir 为可选 scoped 模板目录。
    返回：按发现顺序排列的文件与文本二元组。
    """

    # 根 AGENTS.md 始终是第一个写入候选。
    list_pending: list[tuple[Path, str]] = [
        (project / "AGENTS.md", str_root_text)  # 根规则写入候选。
    ]  # 待写入文件集合。

    # 项目作用域发现器提供候选目录与用途。
    for dict_scope in detect_scopes(project)["scopes"]:

        # 作用域相对位置锚定项目根。
        path_scope = project / dict_scope["path"]  # 当前作用域目录。

        # 不存在目录不能创建 scoped 文件。
        if not path_scope.exists():

            # 跳过已经消失或仅声明的作用域。
            continue

        # scoped 规则文件位于作用域根。
        path_agents = path_scope / "AGENTS.md"  # 当前 scoped 规则位置。

        # 已有文件由人工或其他流程管理，不在此覆盖。
        if path_agents.exists() or not scope_requires_local_agents(path_scope):

            # 只为缺失且具有局部配置的目录创建文件。
            continue

        # 局部模板使用作用域用途和可选模板目录渲染。
        str_scoped_text = render_scoped(dict_scope, template_dir)  # 新 scoped 规则文本。

        # 新文件追加到根文件之后。
        list_pending.append((path_agents, str_scoped_text))

    # 调用方统一执行大小校验和落盘。
    return list_pending

# 大小门禁在任何文件写入前检查完整候选集合。
def validate_pending_sizes(
    project: Path,
    list_pending: list[tuple[Path, str]],
) -> None:
    """验证根规则文件大小合同。

    参数：project 为相对位置基准。
    参数：list_pending 为全部待写入文件。
    返回：通过时无返回；超限时输出 JSON 并退出。
    异常：任一候选超出大小上限时抛出 SystemExit(1)。
    """

    # 校验器接收项目相对位置和待写文本。
    list_relative_text = [
        (path_file.relative_to(project).as_posix(), str_text)  # 相对位置与待写文本。
        for path_file, str_text in list_pending  # 每个写入候选转换一次。
    ]  # 大小检查输入。

    # 所有大小错误一次返回，避免部分写入。
    list_errors = root_size_errors(list_relative_text)  # 文件大小诊断。

    # 空错误集合允许继续落盘。
    if not list_errors:

        # 候选集合满足根文件上限。
        return

    # 机器载荷公开限制值和每个超限诊断。
    emit_json({"errors": list_errors, "max_bytes": ROOT_AGENTS_MAX_BYTES})

    # 大小失败不允许写入任一候选。
    raise SystemExit(1)

# CLI 入口编排只读草稿或受治理写入。
def main() -> None:
    """解析命令行并渲染或写入 AGENTS.md。

    参数：无；从当前进程读取命令行。
    返回：无；只读模式写标准输出，写入模式更新规则文件。
    异常：配置或治理门禁失败时抛出 SystemExit(1)。
    """

    # 参数解析器公开稳定 CLI 合同。
    parser = build_render_parser()  # 公开 CLI 参数定义。

    # 当前进程参数转换为命名空间。
    args = parser.parse_args()  # 用户命令行选择。

    # 项目解析器规范化相对位置并验证根目录。
    path_project = resolve_project(args.project)  # 当前目标仓库。

    # scoped 迁移是独立命令路径，不同时重渲染根文件。
    if args.migrate_redundant_scopes:

        # 输出迁移报告供调用方审查候选或删除结果。
        emit_json(migrate_redundant_scopes(path_project, args.write))

        # 独立迁移完成后停止进入普通渲染流程。
        return

    # 解析平台后才能决定是否需要 Codex worker 生命周期。
    profile_agent = selected_agent_profile(args.agent_platform)  # 当前 agent 平台配置

    # 写入路径由独立 helper 完成 worker 生命周期校验。
    _ensure_worker_profiles_for_write(args, profile_agent, path_project)

    # 自定义模板目录转换为绝对位置。
    path_template_dir = (
        Path(args.template_dir).resolve()  # 显式模板绝对位置。
        if args.template_dir  # 仅显式模板位置需要解析。
        else None  # 未指定时使用内置模板。
    )  # 可选模板目录。

    # profile 加载器解析显式文件或项目默认控制配置。
    profile = load_profile(path_project, args.profile)  # 当前强控制配置。

    # 初始根文本支持默认只读草稿路径。
    str_root_text = render_root(path_project, path_template_dir, profile, profile_agent)  # 当前根规则草稿。

    # 未请求写入时只打印草稿并停止。
    if not args.write:

        # 草稿保持现有 CLI 纯文本输出合同。
        sys.stdout.write(str_root_text)

        # 只读模式没有文件副作用。
        return

    # 强控制项目写入前执行全部治理与脚手架。
    if profile:

        # 门禁通过后配置和 docs 可能改变渲染事实。
        prepare_controlled_write(path_project, profile, args)

        # 重新发现事实，确保根规则反映脚手架后的状态。
        str_root_text = render_root(path_project, path_template_dir, profile, profile_agent)  # 治理后的根规则文本。

    # 根文件和必要 scoped 文件形成原子校验候选。
    list_pending = collect_pending_writes(path_project, str_root_text, path_template_dir)  # 待写入文件。

    # 所有文本在落盘前共同通过大小门禁。
    validate_pending_sizes(path_project, list_pending)

    # shim 冲突在任何 AGENTS.md 写入前阻断，保证根文件与兼容入口事务一致。
    ensure_platform_artifacts(
        path_project,
        args.agent_platform,
        bool_commit=False,
        str_migrate_from=args.migrate_platform_from,
        bool_confirm_migration=args.confirm_platform_migration,
    )

    # 根、作用域、默认覆盖配置和平台 shim 共享同一回滚快照。
    path_global_overrides = path_project / ".agents" / "global-rule-overrides.json"  # 全局规则覆盖文件

    # 记录候选写入文件和默认覆盖文件的原始节点状态。
    dict_write_snapshots = {  # 根写入事务的回滚快照
        path_file: _snapshot_platform_path(path_file)  # 当前候选文件的原始节点
        for path_file in [path_file for path_file, _ in list_pending] + [path_global_overrides]  # 待回滚文件路径
    }

    # 进入根文件与平台 shim 的统一提交事务。
    try:

        # 非强控制项目仍需要默认全局规则覆盖文件。
        if profile is None:

            # 在非强控制路径补齐根级全局规则覆盖文件。
            ensure_global_rule_overrides_file(path_project, profile)

        # 门禁全部通过后按候选顺序写入。
        for path_file, str_text in list_pending:

            # 按候选清单顺序写入每个受管文本文件。
            path_file.write_text(str_text, encoding="utf-8")

        # 根与作用域写入完成后，再同步平台状态目录和兼容入口。
        ensure_platform_artifacts(
            path_project,
            args.agent_platform,
            str_migrate_from=args.migrate_platform_from,
            bool_confirm_migration=args.confirm_platform_migration,
        )

    # 写入或 shim 同步失败时恢复所有候选节点。
    except Exception:

        # 按事务开始时的快照逐项恢复文件状态。
        for path_file, object_snapshot in dict_write_snapshots.items():

            # 当前文件恢复到写入事务开始前的内容或节点类型。
            _restore_platform_path(path_file, object_snapshot)

        # 将原始异常继续交给 CLI 顶层处理，并保留原始类型和回溯。
        raise

# 直接执行分片时由此函数控制唯一的 CLI 入口。
def _run_direct_entrypoint() -> None:
    """在直接执行分片时启动 CLI，聚合加载阶段保持安静。

    参数：无；模块状态由当前执行上下文提供。
    返回：无；符合直接执行条件时调用公开 CLI。
    """

    # 聚合加载时的哨兵阻止分片提前执行命令入口。
    if __name__ != "__main__" or globals().get("_RENDER_SHARD_LOADING", False):

        # 导入或聚合加载路径不产生命令副作用。
        return

    # 直接运行分片时进入 CLI。
    main()

# 公开入口通过小型函数隔离导入期的条件判断。
_run_direct_entrypoint()
