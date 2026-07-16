"""根据控制档案、仓库事实和模板渲染根级与 scoped AGENTS.md。"""

# 延迟解析类型注解，避免运行时循环依赖。
from __future__ import annotations

# 标准库负责 CLI、数据模型、JSON、路径与文本匹配。
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

# 渲染脚本会被 CLI 多次调用，关闭 pycache 能减少治理工作区的临时文件噪音。
sys.dont_write_bytecode = True  # 禁止写入 pycache

# 共享任务模块提供仓库探测、治理与渲染入口。
from agents_common import (
    RELEASE_CORE_WORKTREE_RULE,
    SKIP_DIRS,
    current_timestamp,
    detect_scopes,
    ensure_global_rule_overrides_file,
    emit_json,
    extract_commands,

    # 分隔当前密集代码块，保留原有执行顺序。
    extract_context,
    global_codex_agents_sync_command,
    inspect_project,
    load_global_rule_overrides,
    project_profile,
    preferred_skill_version,

    # 再次分隔当前长代码块，降低连续语句密度。
    read_skill_version,
    resolve_project,
    root_agents_sync_command,
    script_command,
)
from manage_dirs import apply_structure_fix, structure_gate
from manage_docs import branch_gate, preflight_docs, scaffold as scaffold_docs

# 受管段起始前缀必须与增量替换器使用的标记一致。
GENERATED_START = "<!-- AGENTS-GENERATED:START"  # 受管段起始标记前缀

# 受管段结束前缀用于识别生成内容边界。
GENERATED_END = "<!-- AGENTS-GENERATED:END"  # 受管段结束标记前缀

# 根 AGENTS.md 的公开上下文预算以 KiB 展示。
ROOT_AGENTS_MAX_KB = 20  # 根规则文件允许的最大 KiB 数

# 写入门禁按 UTF-8 实际字节数执行同一预算。
ROOT_AGENTS_MAX_BYTES = ROOT_AGENTS_MAX_KB * 1024  # 根规则文件最大字节数

# 单条规则保存章节、优先级、适用条件和来源，供渲染器稳定筛选。
@dataclass(frozen=True)
class Rule:
    """描述可写入根 AGENTS.md 的一条候选规则。"""

    # 稳定标识符用于去重和追踪规则来源。
    id: str  # 规则稳定标识符

    # 章节名称决定规则在根文件中的聚合位置。
    section: str  # 规则归属章节

    # 正文是最终写入 AGENTS.md 的自然语言规则。
    text: str  # 写入 AGENTS.md 的规则正文

    # 较小优先级数值在同章节中先输出。
    priority: int = 50  # 同章节规则排序优先级

    # 条件为假时渲染器跳过当前候选规则。
    condition: bool = True  # 当前项目是否启用该规则

    # 来源记录规则对应的事实或治理配置位置。
    source: str | None = None  # 规则事实或策略来源

# 自举仓库验证命令必须显式指向当前源码 skill。
def source_mode_installed_skill_arg(project: Path, profile: dict | None) -> str:
    """为源码模式自举验证拼接本地 installed-skill 参数。

    参数:
        project: 当前治理项目根目录。
        profile: 项目类型与名称等已探测事实。

    返回:
        自举仓库使用的 installed-skill 参数；普通项目返回空字符串。
    """

    # 非字典 profile 表示项目事实不可用，不能推断 skill 名称。
    if not isinstance(profile, dict):

        # 缺少可信项目身份时不得猜测源码 skill 位置。
        return ""

    # 只有当前开发 skill 自检时需要覆盖已安装 skill 路径。
    if profile.get("kind") == "skill" and str(profile.get("name", "")).strip() == "agents-md-generator":

        # 自举验证使用仓库内 skill 目录作为安装源。
        path_skill_dir = project / "skills" / "agents-md-generator"  # 源码内 skill 目录

        # 目录存在时才拼接参数，避免普通项目渲染出无效命令。
        if path_skill_dir.is_dir():

            # 返回仓库相对路径，保证生成命令可以跨机器复用。
            return f" --installed-skill-dir {path_skill_dir.relative_to(project).as_posix()}"

    # 非自举项目不追加 installed-skill 参数。
    return ""

# 项目命令入口统一处理布局解析和源码自举参数。
def project_command(project: Path, profile: dict | None, script_name: str, *args: str) -> str:
    """生成 AGENTS.md 命令表中的项目脚本命令。

    参数:
        project: 当前治理项目根目录。
        profile: 项目布局与身份事实。
        script_name: 需要解析的治理脚本文件名。
        args: 追加到脚本命令后的参数序列。

    返回:
        按项目布局解析并补齐自举参数的命令文本。
    """

    # 先按项目布局解析脚本命令，保留既有参数顺序。
    str_command = script_command(project, script_name, *args, profile=profile)  # 项目脚本命令

    # verify_agents 在自举仓库中需要额外指定源码 skill 目录。
    if script_name == "verify_agents.py":

        # 自举验证必须比较当前源码，不能误用用户目录旧安装。
        str_command += source_mode_installed_skill_arg(project, profile)  # 附加源码 skill 验证参数

    # 返回可直接写入 Markdown 命令表的命令文本。
    return str_command

# 本地规则配置只以仓库相对路径进入生成文本。
def local_rule_config_path(project: Path, profile: dict | None) -> str:
    """返回本地治理规则配置相对路径。

    参数:
        project: 当前治理项目根目录。
        profile: 项目布局与身份事实。

    返回:
        相对于项目根的规则覆盖文件路径。
    """

    # AGENTS.md 只写项目内相对路径，避免泄露本机绝对路径。
    return load_global_rule_overrides(project, profile)["path"].relative_to(project).as_posix()

# 命令事实按探测顺序转换成 Markdown 表格正文。
def command_rows(commands: list[dict[str, str]]) -> str:
    """把命令事实渲染为 AGENTS.md 命令表行。

    参数:
        commands: 按发现顺序排列的任务命令事实。

    返回:
        Markdown 表格正文；没有命令时返回空字符串。
    """

    # 没有发现命令时保留人工验证占位，提醒代理不要伪造项目命令。
    if not commands:

        # 空字符串让上层省略没有事实支撑的命令段。
        return ""

    # 命令行顺序跟随发现结果，保持生成内容稳定。
    return "\n".join(
        f"| {item['task']} | `{item['command']}` | {item.get('time', '~30s')} | {item.get('source', 'unknown')} |"
        for item in commands
    )

# 兼容压缩入口仅删除空行，不再静默丢弃规则正文。
def limit_lines(text: str, max_lines: int) -> str:
    """保留段落的非空正文行，兼容旧调用点。

    参数:
        text: 待压缩的 Markdown 正文。
        max_lines: 旧接口保留的行预算参数，当前不截断规则。

    返回:
        删除空行但保留全部非空规则的正文。
    """

    # 空行不参与 AGENTS.md 预算，避免手写空白影响压缩判断。
    list_lines = [line for line in text.splitlines() if line.strip()]  # 非空文本行

    # 返回清理后的内容，不再在最终文本阶段丢弃规则。
    return "\n".join(list_lines)

# 命令表预算保留前若干真实命令并记录省略数量。
def limit_command_rows(rows: str, max_rows: int = 5) -> str:
    """限制命令表行数，避免根 AGENTS.md 被命令清单撑大。

    参数:
        rows: 命令表的 Markdown 正文。
        max_rows: 根文件中直接展示的最大命令数。

    返回:
        截断后的命令表正文，必要时附加省略计数行。
    """

    # 只统计非空表格行，保持 Markdown 表紧凑。
    list_lines = [line for line in rows.splitlines() if line.strip()]  # 命令表行

    # 命令数在预算内时不添加额外说明。
    if len(list_lines) <= max_rows:

        # 预算内的命令保持发现顺序完整输出。
        return "\n".join(list_lines)

    # 超出预算时保留前几项并写入生成式省略行。
    return "\n".join(
        list_lines[:max_rows]
        + [f"| More | {len(list_lines) - max_rows} additional commands omitted | inspect scripts/configs | generated |"]
    )

# 受管段渲染器确保生成标记成对并省略空正文。
def compact_section(marker: str, heading: str, body: str, max_body_lines: int | None = None) -> str:
    """渲染一个带 AGENTS-GENERATED 标记的受管段落。

    参数:
        marker: 受管段稳定标识符。
        heading: Markdown 二级标题文本。
        body: 段落正文。
        max_body_lines: 可选兼容行预算；存在时走非空行压缩入口。

    返回:
        带成对生成标记的段落；正文为空时返回空字符串。
    """

    # 调用方可选择对正文行数做预算限制。
    str_section_body = (
        limit_lines(body, max_body_lines)  # 兼容入口压缩非空正文行
        if max_body_lines  # 调用方要求使用旧行预算入口
        else "\n".join(line for line in body.splitlines() if line.strip())  # 默认仅删除正文空行
    )  # 受管段正文

    # 空段落不进入根文件，避免低价值占位标题消耗上下文。
    if not str_section_body.strip():

        # 空字符串让调用方可以直接过滤。
        return ""

    # START/END 标记必须成对出现，供后续增量更新精确替换。
    return "\n".join([
        f"{GENERATED_START} {marker} -->",
        f"## {heading}",
        str_section_body,
        f"<!-- AGENTS-GENERATED:END {marker} -->",
    ])

# 根文件预算检查只对 AGENTS.md 本身执行 UTF-8 字节计数。
def root_size_errors(paths_to_text: list[tuple[str, str]]) -> list[str]:
    """检查根 AGENTS.md 渲染结果是否超过 20KB 上限。

    参数:
        paths_to_text: 输出标签与待写入文本组成的序列。

    返回:
        根文件超出 UTF-8 字节预算时的错误消息列表。
    """

    # 错误列表会被写入渲染结果，调用方据此阻止写入。
    list_errors: list[str] = []  # 根文件大小错误

    # 只检查根 AGENTS.md，scoped 文件由各自上下文控制。
    for label, text in paths_to_text:

        # scoped 文件不共享根文件的固定上下文预算。
        if label != "AGENTS.md":

            # 继续寻找可能存在的根文件输出项。
            continue

        # UTF-8 字节数是实际文件大小预算依据。
        int_size = len(text.encode("utf-8"))  # 根 AGENTS.md UTF-8 字节预算

        # 超过上限时返回具体字节数，便于用户压缩手写内容。
        if int_size > ROOT_AGENTS_MAX_BYTES:

            # 错误包含实际字节数，便于调用方定位压缩幅度。
            list_errors.append(
                f"{label}: exceeds {ROOT_AGENTS_MAX_KB}KB limit ({int_size} bytes); "
                f"compress hand-written content before writing"
            )

    # 返回所有根文件预算错误。
    return list_errors

# 顶层目录用途通过声明式映射生成，避免多层分支压低可读性。
def file_map(facts: dict) -> str:
    """把项目顶层目录事实压缩为 AGENTS.md 中的目录速览。

    参数:
        facts: inspect_project 返回的项目目录事实。

    返回:
        Markdown 代码块形式的顶层目录用途速览。
    """

    # 目录事实来自 inspect_project，可能为空或旧格式。
    list_dirs = facts.get("directories", [])  # 顶层目录列表

    # 只有根文件时给出明确提示，避免生成空代码块。
    if not list_dirs:

        # 明确提示代理直接检查根文件，不虚构目录结构。
        return "```\n(root files only) -> inspect root files directly\n```\n"

    # 目录速览最多展示前 12 项，控制根 AGENTS.md 体积。
    list_lines = ["```"]  # 目录速览 Markdown 行

    # 常见目录用途只用于速览文案，不改变真实目录所有权。
    dict_directory_purposes = {  # 顶层目录名称到速览用途
        "src": "source code",  # 常见源码根目录
        "app": "source code",  # 应用源码根目录
        "lib": "source code",  # 可复用库源码目录
        "tests": "tests and fixtures",  # 复数测试目录
        "test": "tests and fixtures",  # 单数测试目录
        "__tests__": "tests and fixtures",  # JavaScript 测试目录
        "docs": "documentation",  # 小写文档目录
        "Documentation": "documentation",  # 大写文档目录
        "scripts": "automation scripts",  # 自动化脚本目录
        "tools": "automation scripts",  # 项目工具目录
    }

    # 根据常见目录名补充轻量用途说明。
    for directory in list_dirs[:12]:

        # 未知目录保持中性描述，避免基于名称猜测所有权。
        str_purpose = dict_directory_purposes.get(directory, "project directory")  # 当前目录速览用途

        # GitHub 配置的嵌套名称统一归入托管自动化。
        if directory.startswith(".github"):

            # 覆盖默认用途以突出工作流和仓库设置边界。
            str_purpose = "GitHub automation"  # GitHub 配置目录速览用途

        # 每个目录一行，保持 AGENTS.md 可扫描。
        list_lines.append(f"{directory}/ -> {str_purpose}")

    # 关闭 Markdown 代码块。
    list_lines.append("```")

    # 末尾换行让后续段落拼接稳定。
    return "\n".join(list_lines) + "\n"

# scoped 入口索引把探测结果转成根文件中的短指针列表。
def scope_index(scopes: list[dict[str, str]]) -> str:
    """渲染 scoped AGENTS.md 文件索引。

    参数:
        scopes: scoped 文件路径及用途事实列表。

    返回:
        根 AGENTS.md 可直接嵌入的 Markdown 列表。
    """

    # 没有局部规则时明确要求保持根文件简洁。
    if not scopes:

        # 固定提示避免生成空的 scoped 指令章节。
        return "- None detected. Keep root AGENTS.md concise.\n"

    # 每个 scoped 文件只暴露路径与用途，不复制其完整规则。
    return "".join(f"- `./{item['agents_file']}` - {item['purpose']}\n" for item in scopes)

# 默认模板目录从当前渲染模块位置稳定推导。
def default_template_dir() -> Path:
    """返回 agents-md-generator 内置模板目录。

    参数:
        无。

    返回:
        skill 包内 assets/templates 的绝对路径。
    """

    # 固定父级层数对应已治理的 skill 目录布局。
    return Path(__file__).resolve().parents[3] / "assets" / "templates"

# 模板读取入口统一执行存在性检查和 UTF-8 解码。
def load_template(template_dir: Path, name: str) -> str:
    """读取指定名称的 AGENTS 模板。

    参数:
        template_dir: 已解析的模板目录。
        name: 模板文件名。

    返回:
        UTF-8 模板文本。

    异常:
        SystemExit: 模板文件不存在时终止当前渲染命令。
    """

    # 调用方只能在给定模板目录内按名称选择文件。
    path_template = template_dir / name  # 待读取的模板文件路径

    # 缺失模板属于不可恢复的打包或配置错误。
    if not path_template.exists():

        # CLI 错误携带完整路径，便于定位发布包缺失文件。
        raise SystemExit(f"> ERR: [Python] Template does not exist: {path_template}")

    # 模板包合同规定所有文本资源均使用 UTF-8。
    return path_template.read_text(encoding="utf-8")

# 占位符替换器注入已知值并清除模板中未提供的可选字段。
def replace_placeholders(template: str, values: dict[str, str]) -> str:
    """替换 AGENTS 模板中的大写占位符。

    参数:
        template: 包含 ``{{KEY}}`` 标记的模板文本。
        values: 占位符名称到渲染文本的映射。

    返回:
        已注入给定值且不含未解析大写占位符的文本。
    """

    # 替换过程在副本上执行，保留调用方原始模板。
    str_rendered_text = template  # 当前模板渲染结果

    # 已知占位符按输入映射顺序替换，保证输出可重复。
    for str_key, str_raw_value in values.items():

        # 双花括号拼接避免 format 解释正文中的其他大括号。
        str_rendered_text = str_rendered_text.replace(  # 注入当前已知模板字段
            "{{" + str_key + "}}",  # 当前待替换占位符标记
            str_raw_value,  # 当前占位符对应渲染正文
        )

    # 剩余大写标记代表调用方未提供的可选模板字段。
    list_unresolved_keys = sorted(set(re.findall(r"{{([A-Z0-9_]+)}}", str_rendered_text)))  # 未解析占位符名称

    # 未解析的可选字段必须清空，不能泄漏到最终 AGENTS.md。
    for str_key in list_unresolved_keys:

        # 每轮只删除当前稳定排序后的占位符名称。
        str_rendered_text = str_rendered_text.replace(  # 清除当前未提供模板字段
            "{{" + str_key + "}}",  # 当前未解析占位符标记
            "",  # 未提供字段使用空文本清除
        )

    # 返回最终可写入的完整模板文本。
    return str_rendered_text

# 项目概览同时呈现技术栈以及全局、根级规则的治理健康状态。
def project_overview(facts: dict, target_version: str = "") -> str:
    """渲染项目身份与 AGENTS 治理状态概览。

    参数:
        facts: inspect_project 返回的项目与规则事实。
        target_version: 本次渲染准备写入的目标版本。

    返回:
        根 AGENTS.md 项目章节的多行正文。
    """

    # 首行始终记录可复核的语言、框架和项目类型事实。
    list_lines = [
        (  # 项目语言、框架与类型事实
            f"Primary language: {facts['primary_language']}. "
            f"Framework: {facts['framework']}. "
            f"Project type: {facts['project_type']}."
        ),
    ]  # 项目概览正文行

    # 健康的全局基线说明根规则仍是当前工作目录的第一入口。
    if facts.get("global_codex_agents_baseline_ok"):

        # 状态描述只写入口职责，不复制全局基线正文。
        list_lines.append(
            "Global .codex/AGENTS.md: present with a managed baseline that requires "
            "reading the current work folder root `AGENTS.md` first."
        )

    # 需要修复时把探测原因写入概览，禁止误报全局治理完成。
    elif facts.get("global_codex_agents_repair_required"):

        # 多个修复原因按探测顺序连接，保留诊断上下文。
        str_repair_reasons = ", ".join(facts.get("global_codex_agents_repair_reasons", []))  # 全局基线修复原因

        # 修复提示明确要求先同步全局入口再做完成声明。
        list_lines.append(
            (
                f"Global .codex/AGENTS.md: trigger-required for entry-point baseline repair "  # AGENTS 长文本片段
                f"({str_repair_reasons}); sync it before treating user-level AGENTS governance as "
                f"complete."
            )
        )

    # 根 AGENTS.md 已存在时进一步区分健康状态与重建要求。
    if facts.get("root_agents_md_exists"):

        # 新旧探测字段兼容读取同一组重建原因。
        list_trigger_reasons = facts.get(  # 根规则重建原因
            "root_agents_md_trigger_reasons",  # 优先读取当前触发原因字段
            facts.get("root_agents_md_rebuild_reasons", []),  # 兼容旧重建原因字段
        )

        # 仅版本漂移可由本次目标版本渲染直接闭合。
        set_version_only_reasons = {  # 可由目标版本覆盖的重建原因
            "agents_version_mismatch",  # 根规则声明版本漂移
            "generator_version_mismatch",  # 生成器版本漂移
        }

        # 非纯版本原因仍需重新设计或接管，不能被目标版本掩盖。
        if facts.get("root_agents_md_rebuild_required") and not (
            target_version and set(list_trigger_reasons).issubset(set_version_only_reasons)
        ):

            # 概览保留所有触发原因，供调用方决定后续治理路线。
            list_lines.append((
                f"Root AGENTS.md: present but trigger-required for agents-md-generator "
                f"regeneration/restructure "
                f"({', '.join(list_trigger_reasons)})."
            ))

        # 健康文件或可由目标版本覆盖的漂移均可声明当前渲染对齐。
        else:

            # 健康状态只说明版本对齐，不扩大为完整发布证明。
            list_lines.append("Root AGENTS.md: present and version-aligned with the current local agents-md-generator.")

    # 保持概览事实的既定顺序，便于生成结果稳定比较。
    return "\n".join(list_lines)

# 无探测上下文时提供一个保守的既有代码复用提示行。
def golden_sample_rows() -> str:
    """返回默认 golden sample 提示表格行。

    参数:
        无。

    返回:
        引导代理检查邻近实现和测试的 Markdown 表格行。
    """

    # 默认提示不声称仓库内存在尚未探测的具体样例文件。
    return "| Existing code | Inspect nearest similar file | Follow local imports, naming, tests |"

# 已探测 golden sample 只以路径指针形式进入根规则。
def golden_sample_rows_from_context(context: dict) -> str:
    """把 golden sample 路径渲染为复用提示表格行。

    参数:
        context: extract_context 返回的仓库上下文事实。

    返回:
        样例路径表格正文；没有候选时返回空字符串。
    """

    # 探测顺序代表仓库工具给出的稳定候选顺序。
    list_samples = context.get("golden_samples", [])  # golden sample 相对路径

    # 没有真实候选时不生成虚构样例表。
    if not list_samples:

        # 空字符串让上层回退到默认复用提示。
        return ""

    # 每个候选仅提供路径和复用边界，避免复制源文件内容。
    return "\n".join(f"| Existing pattern | `{path}` | Follow local structure and tests |" for path in list_samples)

# 已有工具路径帮助代理优先复用仓库自动化。
def utility_rows(context: dict) -> str:
    """把仓库工具路径渲染为复用提示表格行。

    参数:
        context: extract_context 返回的仓库上下文事实。

    返回:
        工具路径表格正文；没有工具时返回空字符串。
    """

    # 工具候选由上下文探测器去重并保持稳定顺序。
    list_utilities = context.get("utilities", [])  # 可复用工具相对路径

    # 没有真实工具时省略该表，避免创建无证据入口。
    if not list_utilities:

        # 空字符串允许模板跳过整段工具说明。
        return ""

    # 路径指针要求先检查再新增自动化，落实复用优先策略。
    return "\n".join(
        f"| Existing utility | Inspect before creating new automation | `{path}` |"
        for path in list_utilities
    )

# CI 事实渲染保留工作流与实际命令的对应关系。
def ci_rules(context: dict) -> str:
    """把已探测 CI 命令渲染为规则列表。

    参数:
        context: extract_context 返回的仓库上下文事实。

    返回:
        CI 工作流与命令的 Markdown 列表。
    """

    # CI 规则来自可见工作流 run 字段，不进行命令猜测。
    list_rules = context.get("ci_rules", [])  # CI 工作流命令事实

    # 没有发现可验证命令时省略该段。
    if not list_rules:

        # 空输出避免将“未发现”误写为不存在 CI。
        return ""

    # 每行同时保留工作流来源和原始命令文本。
    return "\n".join(f"- `{item['workflow']}` runs `{item['command']}`." for item in list_rules)

# ADR 与架构文档只作为变更前阅读指针进入根规则。
def key_decisions(context: dict) -> str:
    """渲染架构决策和关键文档阅读指针。

    参数:
        context: extract_context 返回的仓库上下文事实。

    返回:
        变更前必须阅读的文档规则列表。
    """

    # 已探测 ADR 直接约束架构或策略变更，优先进入阅读清单。
    list_adrs = context.get("adrs", [])  # 已探测架构决策记录路径

    # 架构文件补充组件所有权和边界信息。
    list_architecture_files = context.get("architecture_files", [])  # 架构文档相对路径

    # 普通文档只在没有更具体决策资料时充当入口。
    list_documentation = context.get("documentation", [])  # 通用文档相对路径

    # 根规则限制 ADR 数量，完整内容仍留在原文档中。
    list_lines = [f"- Review `{path}` before changing architecture or policy." for path in list_adrs[:8]]  # 决策阅读规则

    # 架构文件补充到同一列表，保持 ADR 优先顺序。
    list_lines.extend(
        f"- Respect ownership or architecture guidance in `{path}`."
        for path in list_architecture_files[:4]
    )

    # 没有专门决策资料时才回退到通用文档指针。
    if not list_lines and list_documentation:

        # 指针规则明确禁止把长文档复制到根 AGENTS.md。
        list_lines = [
            f"- Use `{path}` as a pointer; do not copy long documentation into AGENTS.md."  # 通用文档指针规则
            for path in list_documentation[:4]  # 最多保留四个通用文档入口
        ]  # 通用文档回退规则

    # 返回按决策强度排序的规则正文。
    return "\n".join(list_lines)

# 代码库状态段列出会影响实现选择的配置和只读参考工程。
def codebase_state(context: dict) -> str:
    """渲染质量、平台、IDE、依赖和参考工程事实。

    参数:
        context: extract_context 返回的仓库上下文事实。

    返回:
        代码库配置状态的 Markdown 列表。
    """

    # 各类路径保持探测器排序，输出便于稳定比较。
    list_quality_configs = context.get("quality_configs", [])  # 质量配置路径

    # 平台文件描述开发环境或构建平台约束。
    list_platform_files = context.get("platform_files", [])  # 平台配置路径

    # IDE 配置可承载格式、任务和调试约定。
    list_ide_settings = context.get("ide_settings", [])  # IDE 配置路径

    # 依赖自动化配置影响升级和锁定流程。
    list_dependency_configs = context.get("dependency_configs", [])  # 依赖自动化路径

    # 参考工程默认只读，避免生成器暗示可直接修改。
    list_reference_projects = context.get("reference_projects", [])  # 参考工程路径

    # 质量配置优先展示，帮助代理先找到现有门禁。
    list_lines = [f"- Quality config detected: `{path}`." for path in list_quality_configs]  # 代码库状态规则

    # 平台事实追加到现有质量配置之后。
    list_lines.extend(f"- Platform/dev-environment file detected: `{path}`." for path in list_platform_files)

    # IDE 约定可能影响格式化和本地任务入口。
    list_lines.extend(f"- Editor/IDE convention detected: `{path}`." for path in list_ide_settings)

    # 依赖自动化事实提醒代理沿用既有升级机制。
    list_lines.extend(f"- Dependency automation config detected: `{path}`." for path in list_dependency_configs)

    # 参考工程规则显式保持只读边界。
    list_lines.extend(
        f"- Reference project available: `{path}`. Treat as read-only context unless the user asks otherwise."
        for path in list_reference_projects
    )

    # 没有任何已探测配置时省略整个状态段。
    if not list_lines:

        # 空输出不等同于断言仓库没有配置。
        return ""

    # 保持类别顺序连接为根规则正文。
    return "\n".join(list_lines)

# 旧 evolution 模板入口保留空输出兼容，不再复制经验文本。
def evolution_template_guidance(project: Path, template_dir: Path | None = None) -> str:
    """兼容旧调用点并禁用 evolution 模板内容复制。

    参数:
        project: 旧接口传入的项目根目录。
        template_dir: 旧接口传入的可选模板目录。

    返回:
        始终为空，表示不生成 evolution 模板规则。
    """

    # 显式消费兼容参数，避免调用方误以为仍会读取模板。
    del project, template_dir

    # 长期经验已迁移到 memory，根规则不再承载 evolution 文本。
    return ""

# Git hook 事实用于阻止通过 no-verify 绕过仓库检查。
def hook_policy(context: dict) -> str:
    """渲染已探测 hook 配置及禁止绕过规则。

    参数:
        context: extract_context 返回的仓库上下文事实。

    返回:
        hook 配置与执行边界的 Markdown 列表。
    """

    # 已探测 hook 框架配置存在时才启用禁止绕过规则。
    list_hooks = context.get("hook_configs", [])  # 已探测提交钩子配置路径

    # 未探测到 hook 时不推断仓库采用某个框架。
    if not list_hooks:

        # 空输出让模板省略 hook 章节。
        return ""

    # 每个配置路径成为可复核的 hook 事实指针。
    list_lines = [f"- Hook framework/config detected: `{path}`." for path in list_hooks]  # hook 治理规则

    # 禁止绕过规则与具体框架无关，但仅在 hook 存在时适用。
    list_lines.append("- Never bypass hooks with `--no-verify`; fix the underlying failure.")

    # 配置指针之后追加执行边界。
    return "\n".join(list_lines)

# GitHub 配置路径作为仓库托管策略的只读入口。
def github_settings(context: dict) -> str:
    """渲染 GitHub 设置和规则集路径。

    参数:
        context: extract_context 返回的仓库上下文事实。

    返回:
        GitHub 配置指针列表。
    """

    # 设置候选由上下文探测器提供，不在渲染阶段猜测。
    list_settings = context.get("github_settings", [])  # GitHub 设置路径

    # 没有设置事实时省略该段。
    if not list_settings:

        # 空输出避免生成无来源规则。
        return ""

    # 每个设置文件单独形成一条可复核指针。
    return "\n".join(f"- GitHub setting/ruleset detected: `{path}`." for path in list_settings)

# 目录覆盖候选提醒调用方评估是否需要 scoped AGENTS.md。
def directory_coverage(context: dict) -> str:
    """渲染可能需要 scoped AGENTS.md 的目录候选。

    参数:
        context: extract_context 返回的仓库上下文事实。

    返回:
        scoped 规则覆盖候选列表。
    """

    # 候选只表示需要评估，不代表自动创建 scoped 文件。
    list_candidates = context.get("directory_coverage_candidates", [])  # scoped 覆盖候选目录

    # 没有候选时不生成空章节。
    if not list_candidates:

        # 空输出让上层保持根规则简洁。
        return ""

    # 提示语保留“可能需要”边界，避免未经确认冻结目录规则。
    return "\n".join(
        f"- Directory coverage candidate: `{path}/` may need scoped AGENTS.md if it has local rules."
        for path in list_candidates
    )

# 默认决策表只覆盖依赖、模式和未验证命令三类高频边界。
def heuristic_rows() -> str:
    """返回默认工程决策启发表格行。

    参数:
        无。

    返回:
        根 AGENTS.md 可嵌入的三条决策表格正文。
    """

    # 固定顺序从需审批动作到证据不足动作排列。
    return "\n".join([
        "| Adding dependency | Ask first |",
        "| Unsure about pattern | Read nearby files and golden samples |",
        "| Command not verified | Mark it unverified or omit it |",
    ])

# 普通文本项统一转换成 Markdown 无序列表。
def bullet_lines(items: list[str]) -> str:
    """把文本项连接为 Markdown 无序列表。

    参数:
        items: 已按期望顺序排列的正文项。

    返回:
        每项带短横线前缀的多行文本。
    """

    # 保持调用方顺序，不在通用格式化入口重排事实。
    return "\n".join(f"- {item}" for item in items)

# 控制档案加载器统一处理默认路径、JSON 语法和根对象类型。
def load_profile(project: Path, raw: str | None) -> dict | None:
    """读取 agents-control JSON 控制档案。

    参数:
        project: 当前治理项目根目录。
        raw: 用户显式传入的控制档案路径。

    返回:
        控制档案字典；默认文件不存在时返回 ``None``。

    异常:
        SystemExit: JSON 无法解析或根值不是对象。
    """

    # 显式路径优先，否则读取仓库标准控制档案位置。
    path_profile = Path(raw).resolve() if raw else project / ".agents" / "agents-control.json"  # 控制档案路径

    # 缺少默认档案表示强控制尚未配置，由调用方生成提示。
    if not path_profile.exists():

        # 不创建隐式默认内容，保留设计访谈门禁。
        return None

    # JSON 语法错误需要转换成稳定 CLI 错误。
    try:

        # 控制档案统一按 UTF-8 读取并解析一次。
        dict_profile = json.loads(path_profile.read_text(encoding="utf-8"))  # 已解析控制档案

    # 解析失败时保留原始异常细节和文件路径。
    except json.JSONDecodeError as exc:

        # 固定错误前缀满足 CLI 输出合同。
        raise SystemExit(f"> ERR: [Python] Could not parse profile JSON: {path_profile}: {exc}")

    # 后续渲染只接受键值对象，数组或标量均属配置错误。
    if not isinstance(dict_profile, dict):

        # 类型错误明确指出期望的 JSON 根结构。
        raise SystemExit(f"> ERR: [Python] Profile must be a JSON object: {path_profile}")

    # 返回已验证根类型的控制档案。
    return dict_profile

# skill 目录推断优先使用控制档案，再回退到唯一 VERSION 候选。
def inferred_project_skill_dir(project: Path, profile: dict | None = None) -> Path | None:
    """推断当前项目拥有的 skill 源目录。

    参数:
        project: 当前治理项目根目录。
        profile: 可选控制档案事实。

    返回:
        含 VERSION 文件的 skill 目录；无法唯一确定时返回 ``None``。
    """

    # 非字典 profile 不参与路径推断。
    dict_effective_profile = profile if isinstance(profile, dict) else None  # 可用于推断的控制档案

    # 控制档案中的显式布局和 skill 身份优先于目录扫描。
    if dict_effective_profile:

        # 仅字典形式的 skill_layout 能提供可信路径字段。
        dict_layout = (  # skill 布局配置
            dict_effective_profile.get("skill_layout")  # 使用显式 skill 布局对象
            if isinstance(dict_effective_profile.get("skill_layout"), dict)  # 拒绝非对象布局值
            else {}  # 无有效布局时使用空配置
        )

        # 显式布局路径支持非默认但已治理的 skill 位置。
        str_raw_path = str(dict_layout.get("path") or "").strip()  # 控制档案中的 skill 相对路径

        # 空路径不参与文件系统解析。
        if str_raw_path:

            # 候选路径相对于项目根解析并规范化。
            path_candidate = (project / str_raw_path).resolve()  # 显式布局候选目录

            # VERSION 文件证明候选目录具备 skill 发布身份。
            if (path_candidate / "VERSION").is_file():

                # 显式有效路径是最高优先级结果。
                return path_candidate

        # 默认 skill 布局可由已确认的项目名称推导。
        str_skill_name = str(dict_effective_profile.get("name") or "").strip()  # 控制档案中的 skill 名称

        # 只有 skill 项目才允许按 skills/<name> 推断。
        if dict_effective_profile.get("kind") == "skill" and str_skill_name:

            # 标准布局候选保持在项目根 skills 目录下。
            path_candidate = (project / "skills" / str_skill_name).resolve()  # 标准布局候选目录

            # 缺少 VERSION 的同名目录不能充当发布 skill 根。
            if (path_candidate / "VERSION").is_file():

                # 返回已验证的标准布局目录。
                return path_candidate

    # 无可信 profile 路径时只扫描标准 skills 根目录。
    path_skills_root = project / "skills"  # 标准 skill 集合目录

    # 不存在标准根目录时无法继续推断。
    if path_skills_root.is_dir():

        # 仅含 VERSION 的直接子目录可成为 skill 根候选。
        list_candidates = [
            path.resolve()  # 规范化每个具备版本身份的目录
            for path in path_skills_root.iterdir()  # 仅扫描 skills 直接子目录
            if (path / "VERSION").is_file()  # VERSION 文件证明候选可发布
        ]  # 标准布局中的 skill 候选目录

        # 唯一候选才可安全推断，多个候选必须由 profile 消歧。
        if len(list_candidates) == 1:

            # 返回唯一具备版本身份的 skill 目录。
            return list_candidates[0]

    # 证据不足时不猜测项目拥有哪个 skill。
    return None

# 项目版本读取只接受已确认的 skill 目录。
def resolved_project_version(project: Path, profile: dict | None = None) -> str:
    """读取当前项目 skill 的版本。

    参数:
        project: 当前治理项目根目录。
        profile: 可选控制档案事实。

    返回:
        VERSION 文件内容；无法定位 skill 时返回空字符串。
    """

    # 目录推断集中处理 profile 与唯一候选回退规则。
    path_skill_dir = inferred_project_skill_dir(project, profile)  # 已推断 skill 源目录

    # 仅在目录可确认时读取版本，避免误读其他 skill。
    return read_skill_version(path_skill_dir) if path_skill_dir else ""

# 生成器版本在自举仓库中跟随项目目标版本，其他项目读取已安装首选版本。
def resolved_generator_version(project: Path, profile: dict | None = None, project_version: str = "") -> str:
    """解析本次 AGENTS 渲染使用的生成器版本。

    参数:
        project: 当前治理项目根目录，保留供统一调用接口使用。
        profile: 可选控制档案事实。
        project_version: 当前项目 skill 版本。

    返回:
        自举目标版本或已安装生成器首选版本。
    """

    # 当前函数接口保留 project 以与其他版本解析入口一致。
    del project

    # agents-md-generator 自举发布时必须把目标项目版本写入元数据。
    if (
        isinstance(profile, dict)
        and profile.get("kind") == "skill"
        and str(profile.get("name", "")).strip() == "agents-md-generator"
        and project_version
    ):

        # 自举版本避免使用尚未更新的用户目录安装副本。
        return project_version

    # 普通项目使用版本策略选择的本地生成器版本。
    str_generator_version, _path_version_source = preferred_skill_version()  # 首选生成器版本及来源

    # 未找到安装版本时保留 unknown，禁止伪造版本号。
    return str_generator_version or "unknown"

# 控制档案摘要把已确认设计事实压缩为根规则短列表。
def control_profile(profile: dict | None, project: Path, project_version: str = "") -> str:
    """渲染强控制档案摘要。

    参数:
        profile: 已确认控制档案；缺失时生成配置提示。
        project: 当前治理项目根目录。
        project_version: 当前项目 skill 版本。

    返回:
        根 AGENTS.md 的 Control Profile 章节正文。
    """

    # 未配置强控制时只给出正式设计写入入口和禁止声明边界。
    if not profile:

        # 设计写入命令单独构造，避免在长提示行中隐藏参数边界。
        str_design_command = project_command(  # 强控制设计写入命令
            project,  # 当前治理项目根
            profile,  # 当前缺失的控制档案值
            "collect_design_profile.py",  # 设计访谈入口脚本
            "<project>",  # 文档中的项目参数占位符
            "--answers",  # 批量答案文件参数
            "answers.json",  # 示例答案文件名
            "--write",  # 正式写入设计结果
        )

        # 提示命令沿用当前项目脚本布局解析结果。
        return "\n".join([
            "- Strong control: not configured.",
            (
                f"- Run "
                f"`{str_design_command}` "
                f"before claiming strict control."
            ),
            "- Until configured, ask the mandatory design questions before writing controlled AGENTS.md output.",
        ])

    # 基础身份字段始终先输出，便于快速核对配置对象。
    list_lines = [
        "- Strong control: complete.",  # 强控制设计已完成标记
        f"- Development type: {profile.get('kind', 'unknown')}.",  # 开发类型摘要
        f"- Name: {profile.get('name', 'unknown')}.",  # 项目名称摘要
        f"- Version: {project_version or 'unknown'}.",  # 项目版本摘要
        f"- Default conversation language: {profile.get('default_conversation_language', '中文')}.",  # 默认语言摘要
        (
            f"- Local governance detail source: `{local_rule_config_path(project, profile)}` "
            f"for long-task, maintainability, and tool-layout rules."
        ),
        f"- Purpose/reason: {profile.get('purpose', 'unknown')} / {profile.get('reason', 'unknown')}.",  # 目的与原因摘要
    ]  # 控制档案摘要行

    # 可选设计字段只在用户实际确认内容后写入。
    dict_optional_lines = {  # profile 字段到摘要标签
        "development_requirements": "Development requirements",  # 开发要求摘要
        "validation_method": "Validation method",  # 验证方法摘要
        "resource_plan": "Resource boundaries",  # 资源边界摘要
        "expected_outcome": "Expected outcome",  # 预期结果摘要
        "audience_or_environment": "Audience/environment",  # 使用环境摘要
        "validation_granularity": "Validation granularity",  # 验证粒度摘要
        "forward_testing_policy": "Forward testing",  # 前向测试摘要
    }

    # 按稳定声明顺序追加非空设计字段。
    for str_field, str_label in dict_optional_lines.items():

        # 控制档案值保持原文，不在渲染阶段重新解释。
        profile_value = profile.get(str_field)  # 当前可选设计字段值

        # 缺失字段不生成 unknown 噪音行。
        if profile_value:

            # 标签与原始值形成一条简短可复核摘要。
            list_lines.append(f"- {str_label}: {profile_value}.")

    # 额外要求的 none 哨兵表示用户明确没有补充内容。
    str_extra_requirements = str(profile.get("extra_requirements", "")).strip()  # 用户额外要求

    # 仅真实补充内容进入根规则。
    if str_extra_requirements and str_extra_requirements.casefold() != "none":

        # 额外要求保持用户原文，避免语义漂移。
        list_lines.append(f"- Additional user requirements: {str_extra_requirements}.")

    # 临时参考材料要求开发后人工删除并禁止泄漏本地路径。
    if profile.get("reference_materials_temporary"):

        # 该边界属于数据治理要求，必须在摘要中显式呈现。
        list_lines.append((
            "- Temporary reference materials were used; remove them manually after "
            "development and do not copy local reference paths into AGENTS.md."
        ))

    # 返回按身份、设计字段和风险边界排列的摘要。
    return "\n".join(list_lines)

# 目录合同摘要只保留根级阻塞规则，详细路径仍由 dir manager 文档承载。
def directory_contract(profile: dict | None, project: Path) -> str:
    """渲染已确认目录合同及目录变更门禁。

    参数:
        profile: 控制档案中的目录治理事实。
        project: 当前治理项目根目录。

    返回:
        根 AGENTS.md 的目录合同规则列表。
    """

    # 缺少控制档案时不得冻结本地、远程或功能目录结构。
    if not profile:

        # 单行提示保留必须先确认目录合同的写入边界。
        return (
            "- Directory contract: not confirmed. Do not freeze structure until the user "
            "confirms local, remote, and feature-addition layout."
        )

    # 主目录合同保存本地、远程、设置和项目根事实。
    dict_contract = profile.get("directory_contract", {})  # 已确认目录合同

    # 目录管理器合同提供治理文档位置和审查入口。
    dict_dir_manager_contract = profile.get("dir_manager_contract", {})  # 目录管理器合同

    # 测试布局策略约束唯一根目录和 Python 功能分组深度。
    dict_tests_layout = dict_contract.get("tests_layout", {})  # tests 目录治理合同

    # workspace_settings_policy 必须为对象才能读取路径字段。
    dict_settings_policy = (  # 工作区设置文件策略
        dict_contract.get("workspace_settings_policy", {})  # 使用已确认设置策略
        if isinstance(dict_contract.get("workspace_settings_policy", {}), dict)  # 拒绝非对象策略值
        else {}  # 缺少有效策略时采用安全默认路径
    )

    # 主项目根保持控制档案原始相对路径表示。
    str_primary_root = str(dict_contract.get("primary_project_root", "")).strip()  # 规范主项目根

    # 有主根时说明其权威性，缺失时明确标记未配置。
    str_primary_root_line = (  # 主项目根摘要规则
        f"- Primary project root: `{str_primary_root}` is the canonical main project location."  # 已确认主项目根
        if str_primary_root  # 仅非空路径可声明主根
        else "- Primary project root: not configured."  # 缺少主根时明确未配置
    )

    # 根规则按确认状态、结构、设置安全和变更门禁顺序输出。
    list_lines = [
        f"- Confirmed: {dict_contract.get('confirmed', False)}.",  # 目录合同确认状态
        f"- Local structure: {dict_contract.get('local', 'not specified')}.",  # 本地目录结构摘要
        f"- Remote structure: {dict_contract.get('remote', 'not specified')}.",  # 远程目录结构摘要
        str_primary_root_line,  # 主项目根摘要
        (
            f"- Workspace settings: keep work-folder project config under "
            f"`{dict_settings_policy.get('folder', '.settings')}/`; local-only files use "
            f"`{dict_settings_policy.get('local_default_file', '.settings/project.local.json')}` "
            f"or `{dict_settings_policy.get('folder', '.settings')}/<name>.local.json`, and "
            f"remote workspaces use "
            f"`{dict_settings_policy.get('remote_default_file', '.settings/project.remote.json')}` "
            f"or `{dict_settings_policy.get('folder', '.settings')}/<name>.remote.json`."
        ),
        (
            f"- Security rule: never copy "
            f"`{dict_settings_policy.get('folder', '.settings')}/*.local.json` such as "
            f"`{dict_settings_policy.get('folder', '.settings')}/server_list.local.json` "
            f"to a "
            f"remote server; keep local private config local and use `.remote.json` files "
            f"for remote project settings instead."
        ),
        (
            "- Root-level work artifacts: keep `tests/`, `smoke/` and `smoke-*`, "
            "`reports/`, `runs/` at work-folder root; do not place them under the primary "
            "project root."
        ),
        (
            "- Remote deployment, conda, runtime, backup, and archive path details live in "
            "`docs/dir_manager/planned_structure.json`; root AGENTS.md is only the entry "
            "rule index."
        ),
        (
            "- Remote deployment boundary: do not sync local skill-development content to "
            "remote servers; deploy only explicit runtime/deployment artifacts unless the "
            "user explicitly overrides."
        ),
        (
            "- New feature structure: keep new work inside the confirmed local structure "
            "and primary project root; read the local JSON governance config before "
            "assuming detailed maintainability or script layout rules."
        ),
        "- Do not add new top-level directories or move ownership boundaries without updating this contract.",  # 顶层目录变更边界
        (
            f"- Dir manager gate: review directory create/move/delete/rename plans with "
            f"`{dict_dir_manager_contract.get('folder', 'docs/dir_manager')}/DIR_MANAGER.md` "
            f"before "
            f"changing folder structure."
        ),
        (
            f"- Required command before folder changes: "
            f"`{project_command(project, profile, 'manage_dirs.py', 'review', '<project>', '--input', 'change.json')}`."
        ),
        (
            "- If directory review blocks the change, refuse default execution, explain "
            "the risk, and ask for explicit user force-confirmation before proceeding."
        ),
    ]  # 目录合同根级规则

    # 已配置测试布局时在根级规则中公开不可省略的结构约束。
    if isinstance(dict_tests_layout, dict) and dict_tests_layout.get("required_root") == "tests":

        # tests 布局规则放在通用根产物规则之后，保持目录约束相邻。
        list_lines.insert(
            7,
            (
                "- Tests layout: keep exactly one root `tests/`; place Python tests under "
                "`tests/<feature>/*.py`, allow only `tests/__init__.py` at the root, and "
                "forbid nested `tests/` directories."
            ),
        )

    # skill 项目的 eval 资产必须随主项目根进入发布包。
    if str_primary_root and str(profile.get("kind", "")).strip().lower() == "skill":

        # 在设置规则之前插入发布资产所有权，便于快速扫描。
        list_lines.insert(
            4,
            (
                f"- Skill-local release content: keep eval assets under "
                f"`{str_primary_root.rstrip('/')}/evals/`; they stay in the skill package."
            ),
        )

    # 返回完整目录治理摘要，不复制 planned_structure 详细内容。
    return "\n".join(list_lines)
