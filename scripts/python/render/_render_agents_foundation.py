"""根据控制档案、仓库事实和模板渲染根级与 scoped AGENTS.md。"""

# 导入 AGENTS 渲染 所需的依赖模块。
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

# 导入 AGENTS 渲染 所需的依赖模块。
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

# 渲染脚本会被 CLI 多次调用，关闭 pycache 能减少治理工作区的临时文件噪音。
sys.dont_write_bytecode = True  # 禁止写入 pycache

# 导入 AGENTS 渲染 所需的依赖模块。
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

# 整理 模块入口 需要的 GENERATED START 渲染片段。
GENERATED_START = "<!-- AGENTS-GENERATED:START"  # AGENTS 受管段落渲染输入值

# 整理 模块入口 需要的 GENERATED END 渲染片段。
GENERATED_END = "<!-- AGENTS-GENERATED:END"  # AGENTS 受管段落渲染输入值

# 整理 模块入口 需要的 ROOT AGENTS MAX KB 渲染片段。
ROOT_AGENTS_MAX_KB = 20  # AGENTS 受管段落渲染输入值

# 整理 模块入口 需要的 ROOT AGENTS MAX BYTES 渲染片段。
ROOT_AGENTS_MAX_BYTES = ROOT_AGENTS_MAX_KB * 1024  # AGENTS 受管段落渲染输入值


@dataclass(frozen=True)
class Rule:
    """根 AGENTS.md 的可筛选规则。"""

    id: str
    section: str
    text: str
    priority: int = 50
    condition: bool = True
    source: str | None = None

# 定义 source_mode_installed_skill_arg 的AGENTS 渲染处理入口。
def source_mode_installed_skill_arg(project: Path, profile: dict | None) -> str:
    """为源码模式自举验证拼接本地 installed-skill 参数。

    # 补充AGENTS 渲染代码段的职责说明。
    当前 agents-md-generator 开发仓库验证自身时，必须显式指向源码内 skill，
    避免误用用户目录里已安装的旧版本。
    """

    # 非字典 profile 表示项目事实不可用，不能推断 skill 名称。
    if not isinstance(profile, dict):

        # 返回 source_mode_installed_skill_arg 的 AGENTS 渲染载荷。
        return ""

    # 只有当前开发 skill 自检时需要覆盖已安装 skill 路径。
    if profile.get("kind") == "skill" and str(profile.get("name", "")).strip() == "agents-md-generator":

        # 自举验证使用仓库内 skill 目录作为安装源。
        path_skill_dir = project / "skills" / "agents-md-generator"  # 源码内 skill 目录

        # 目录存在时才拼接参数，避免普通项目渲染出无效命令。
        if path_skill_dir.is_dir():

            # 返回 source_mode_installed_skill_arg 的 AGENTS 渲染载荷。
            return f" --installed-skill-dir {path_skill_dir.relative_to(project).as_posix()}"

    # 非自举项目不追加 installed-skill 参数。
    return ""


# 定义 project_command 的AGENTS 渲染处理入口。
def project_command(project: Path, profile: dict | None, script_name: str, *args: str) -> str:
    """生成 AGENTS.md 命令表中的项目脚本命令。"""

    # 先按项目布局解析脚本命令，保留既有参数顺序。
    str_command = script_command(project, script_name, *args, profile=profile)  # 项目脚本命令

    # verify_agents 在自举仓库中需要额外指定源码 skill 目录。
    if script_name == "verify_agents.py":

        # 整理 project_command 需要的 command 渲染片段。
        str_command += source_mode_installed_skill_arg(project, profile)  # AGENTS 受管段落渲染输入值

    # 返回可直接写入 Markdown 命令表的命令文本。
    return str_command


# 定义 local_rule_config_path 的AGENTS 渲染处理入口。
def local_rule_config_path(project: Path, profile: dict | None) -> str:
    """返回本地治理规则配置相对路径。"""

    # AGENTS.md 只写项目内相对路径，避免泄露本机绝对路径。
    return load_global_rule_overrides(project, profile)["path"].relative_to(project).as_posix()

# 定义 command_rows 的AGENTS 渲染处理入口。
def command_rows(commands: list[dict[str, str]]) -> str:
    """把命令事实渲染为 AGENTS.md 命令表行。"""

    # 没有发现命令时保留人工验证占位，提醒代理不要伪造项目命令。
    if not commands:

        # 返回 command_rows 的 AGENTS 渲染载荷。
        return ""

    # 命令行顺序跟随发现结果，保持生成内容稳定。
    return "\n".join(
        f"| {item['task']} | `{item['command']}` | {item.get('time', '~30s')} | {item.get('source', 'unknown')} |"
        for item in commands
    )


# 定义 limit_lines 的AGENTS 渲染处理入口。
def limit_lines(text: str, max_lines: int) -> str:
    """保留段落的非空正文行，兼容旧调用点。"""

    # 空行不参与 AGENTS.md 预算，避免手写空白影响压缩判断。
    list_lines = [line for line in text.splitlines() if line.strip()]  # 非空文本行

    # 返回清理后的内容，不再在最终文本阶段丢弃规则。
    return "\n".join(list_lines)


# 定义 limit_command_rows 的AGENTS 渲染处理入口。
def limit_command_rows(rows: str, max_rows: int = 5) -> str:
    """限制命令表行数，避免根 AGENTS.md 被命令清单撑大。"""

    # 只统计非空表格行，保持 Markdown 表紧凑。
    list_lines = [line for line in rows.splitlines() if line.strip()]  # 命令表行

    # 命令数在预算内时不添加额外说明。
    if len(list_lines) <= max_rows:

        # 返回 limit_command_rows 的 AGENTS 渲染载荷。
        return "\n".join(list_lines)

    # 超出预算时保留前几项并写入生成式省略行。
    return "\n".join(
        list_lines[:max_rows]
        + [f"| More | {len(list_lines) - max_rows} additional commands omitted | inspect scripts/configs | generated |"]
    )

# 定义 compact_section 的AGENTS 渲染处理入口。
def compact_section(marker: str, heading: str, body: str, max_body_lines: int | None = None) -> str:
    """渲染一个带 AGENTS-GENERATED 标记的受管段落。"""

    # 调用方可选择对正文行数做预算限制。
    str_section_body = (  # AGENTS 受管段落渲染输入值
        limit_lines(body, max_body_lines)  # AGENTS 受管段落渲染输入值
        if max_body_lines  # AGENTS 受管段落渲染输入值
        else "\n".join(line for line in body.splitlines() if line.strip())  # AGENTS 受管段落渲染输入值
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


# 定义 root_size_errors 的AGENTS 渲染处理入口。
def root_size_errors(paths_to_text: list[tuple[str, str]]) -> list[str]:
    """检查根 AGENTS.md 渲染结果是否超过 20KB 上限。"""

    # 错误列表会被写入渲染结果，调用方据此阻止写入。
    list_errors: list[str] = []  # 根文件大小错误

    # 只检查根 AGENTS.md，scoped 文件由各自上下文控制。
    for label, text in paths_to_text:

        # 校验 root_size_errors 的渲染分支条件。
        if label != "AGENTS.md":

            # 分隔 root_size_errors 的控制流边界。
            continue

        # UTF-8 字节数是实际文件大小预算依据。
        int_size = len(text.encode("utf-8"))  # 根 AGENTS.md UTF-8 字节预算

        # 超过上限时返回具体字节数，便于用户压缩手写内容。
        if int_size > ROOT_AGENTS_MAX_BYTES:

            # 追加 root_size_errors 的 AGENTS 渲染行。
            list_errors.append(
                f"{label}: exceeds {ROOT_AGENTS_MAX_KB}KB limit ({int_size} bytes); compress hand-written content before writing"
            )

    # 返回所有根文件预算错误。
    return list_errors


# 定义 file_map 的AGENTS 渲染处理入口。
def file_map(facts: dict) -> str:
    """把项目顶层目录事实压缩为 AGENTS.md 中的目录速览。"""

    # 目录事实来自 inspect_project，可能为空或旧格式。
    list_dirs = facts.get("directories", [])  # 顶层目录列表

    # 只有根文件时给出明确提示，避免生成空代码块。
    if not list_dirs:

        # 返回 file_map 的 AGENTS 渲染载荷。
        return "```\n(root files only) -> inspect root files directly\n```\n"

    # 目录速览最多展示前 12 项，控制根 AGENTS.md 体积。
    list_lines = ["```"]  # 目录速览 Markdown 行

    # 根据常见目录名补充轻量用途说明。
    for directory in list_dirs[:12]:

        # 整理 file_map 需要的 purpose 渲染片段。
        str_purpose = "project directory"  # 目录默认用途

        # 校验 file_map 的渲染分支条件。
        if directory in {"src", "app", "lib"}:

            # 整理 file_map 需要的 purpose 渲染片段。
            str_purpose = "source code"  # AGENTS 受管段落渲染输入值

        # 校验 file_map 的渲染分支条件。
        elif directory in {"tests", "test", "__tests__"}:

            # 整理 file_map 需要的 purpose 渲染片段。
            str_purpose = "tests and fixtures"  # AGENTS 受管段落渲染输入值

        # 校验 file_map 的渲染分支条件。
        elif directory in {"docs", "Documentation"}:

            # 整理 file_map 需要的 purpose 渲染片段。
            str_purpose = "documentation"  # AGENTS 受管段落渲染输入值

        # 校验 file_map 的渲染分支条件。
        elif directory in {"scripts", "tools"}:

            # 整理 file_map 需要的 purpose 渲染片段。
            str_purpose = "automation scripts"  # AGENTS 受管段落渲染输入值

        # 校验 file_map 的渲染分支条件。
        elif directory.startswith(".github"):

            # 整理 file_map 需要的 purpose 渲染片段。
            str_purpose = "GitHub automation"  # AGENTS 受管段落渲染输入值

        # 每个目录一行，保持 AGENTS.md 可扫描。
        list_lines.append(f"{directory}/ -> {str_purpose}")

    # 关闭 Markdown 代码块。
    list_lines.append("```")

    # 末尾换行让后续段落拼接稳定。
    return "\n".join(list_lines) + "\n"

# 定义 scope_index 的AGENTS 渲染处理入口。
def scope_index(scopes: list[dict[str, str]]) -> str:

    # 校验 scope_index 的渲染分支条件。
    if not scopes:

        # 返回 scope_index 的 AGENTS 渲染载荷。
        return "- None detected. Keep root AGENTS.md concise.\n"

    # 返回 scope_index 的 AGENTS 渲染载荷。
    return "".join(f"- `./{item['agents_file']}` - {item['purpose']}\n" for item in scopes)

# 定义 default_template_dir 的AGENTS 渲染处理入口。
def default_template_dir() -> Path:

    # 返回 default_template_dir 的 AGENTS 渲染载荷。
    return Path(__file__).resolve().parents[3] / "assets" / "templates"

# 定义 load_template 的AGENTS 渲染处理入口。
def load_template(template_dir: Path, name: str) -> str:

    # 整理 load_template 需要的 path 渲染片段。
    path = template_dir / name  # AGENTS 受管段落渲染输入值

    # 校验 load_template 的渲染分支条件。
    if not path.exists():

        # 抛出 load_template 已确认的阻断原因。
        raise SystemExit(f"Template does not exist: {path}")

    # 返回 load_template 的 AGENTS 渲染载荷。
    return path.read_text(encoding="utf-8")

# 定义 replace_placeholders 的AGENTS 渲染处理入口。
def replace_placeholders(template: str, values: dict[str, str]) -> str:

    # 整理 replace_placeholders 需要的 text 渲染片段。
    text = template  # AGENTS 受管段落渲染输入值

    # 逐项检查 replace_placeholders 渲染候选。
    for key, raw_value in values.items():

        # 整理 replace_placeholders 需要的 text 渲染片段。
        text = text.replace("{{" + key + "}}", raw_value)  # AGENTS 受管段落渲染输入值

    # 整理 replace_placeholders 需要的 unresolved 渲染片段。
    unresolved = sorted(set(re.findall(r"{{([A-Z0-9_]+)}}", text)))  # AGENTS 受管段落渲染输入值

    # 逐项检查 replace_placeholders 渲染候选。
    for key in unresolved:

        # 整理 replace_placeholders 需要的 text 渲染片段。
        text = text.replace("{{" + key + "}}", "")  # AGENTS 受管段落渲染输入值

    # 返回 replace_placeholders 的 AGENTS 渲染载荷。
    return text

# 定义 project_overview 的AGENTS 渲染处理入口。
def project_overview(facts: dict, target_version: str = "") -> str:

    # 汇总 lines，作为 AGENTS 受管段落拼装顺序。
    list_lines = [  # AGENTS 受管段落渲染输入值
        f"Primary language: {facts['primary_language']}. Framework: {facts['framework']}. Project type: {facts['project_type']}.",  # AGENTS 受管段落渲染输入值
    ]

    # 校验 project_overview 的渲染分支条件。
    if facts.get("global_codex_agents_baseline_ok"):

        # 追加 project_overview 的 AGENTS 渲染行。
        list_lines.append("Global .codex/AGENTS.md: present with a managed baseline that requires reading the current work folder root `AGENTS.md` first.")

    # 校验 project_overview 的渲染分支条件。
    elif facts.get("global_codex_agents_repair_required"):

        # 汇总 reasons，作为 AGENTS 受管段落拼装顺序。
        reasons = ", ".join(facts.get("global_codex_agents_repair_reasons", []))  # AGENTS 受管段落渲染输入值

        # 追加 project_overview 的 AGENTS 渲染行。
        list_lines.append(
            (
                f"Global .codex/AGENTS.md: trigger-required for entry-point baseline repair "  # AGENTS 长文本片段
                f"({reasons}); sync it before treating user-level AGENTS governance as "  # AGENTS 长文本片段
                f"complete."  # AGENTS 长文本片段
            )
        )

    # 校验 project_overview 的渲染分支条件。
    if facts.get("root_agents_md_exists"):

        # 汇总 trigger reasons，作为 AGENTS 受管段落拼装顺序。
        trigger_reasons = facts.get("root_agents_md_trigger_reasons", facts.get("root_agents_md_rebuild_reasons", []))  # AGENTS 受管段落渲染输入值

        # 汇总 version only reasons，作为 AGENTS 受管段落拼装顺序。
        set_version_only_reasons = {"agents_version_mismatch", "generator_version_mismatch"}  # AGENTS 受管段落渲染输入值

        # 校验 project_overview 的渲染分支条件。
        if facts.get("root_agents_md_rebuild_required") and not (
            target_version and set(trigger_reasons).issubset(set_version_only_reasons)
        ):

            # 追加 project_overview 的 AGENTS 渲染行。
            list_lines.append((
                f"Root AGENTS.md: present but trigger-required for agents-md-generator "  # AGENTS 长文本片段
                f"regeneration/restructure "  # AGENTS 长文本片段
                f"({', '.join(facts.get('root_agents_md_trigger_reasons', facts.get('root_agents_md_rebuild_reasons', [])))})."  # AGENTS 长文本片段
            ))
        else:

            # 追加 project_overview 的 AGENTS 渲染行。
            list_lines.append("Root AGENTS.md: present and version-aligned with the current local agents-md-generator.")
    # 返回 project_overview 的 AGENTS 渲染载荷。
    return "\n".join(list_lines)

# 定义 golden_sample_rows 的AGENTS 渲染处理入口。
def golden_sample_rows() -> str:

    # 返回 golden_sample_rows 的 AGENTS 渲染载荷。
    return "| Existing code | Inspect nearest similar file | Follow local imports, naming, tests |"

# 定义 golden_sample_rows_from_context 的AGENTS 渲染处理入口。
def golden_sample_rows_from_context(context: dict) -> str:

    # 汇总 samples，作为 AGENTS 受管段落拼装顺序。
    samples = context.get("golden_samples", [])  # AGENTS 受管段落渲染输入值

    # 校验 golden_sample_rows_from_context 的渲染分支条件。
    if not samples:

        # 返回 golden_sample_rows_from_context 的 AGENTS 渲染载荷。
        return ""

    # 返回 golden_sample_rows_from_context 的 AGENTS 渲染载荷。
    return "\n".join(f"| Existing pattern | `{path}` | Follow local structure and tests |" for path in samples)

# 定义 utility_rows 的AGENTS 渲染处理入口。
def utility_rows(context: dict) -> str:

    # 汇总 utilities，作为 AGENTS 受管段落拼装顺序。
    utilities = context.get("utilities", [])  # AGENTS 受管段落渲染输入值

    # 校验 utility_rows 的渲染分支条件。
    if not utilities:

        # 返回 utility_rows 的 AGENTS 渲染载荷。
        return ""

    # 返回 utility_rows 的 AGENTS 渲染载荷。
    return "\n".join(f"| Existing utility | Inspect before creating new automation | `{path}` |" for path in utilities)

# 定义 ci_rules 的AGENTS 渲染处理入口。
def ci_rules(context: dict) -> str:

    # 汇总 rules，作为 AGENTS 受管段落拼装顺序。
    rules = context.get("ci_rules", [])  # AGENTS 受管段落渲染输入值

    # 校验 ci_rules 的渲染分支条件。
    if not rules:

        # 返回 ci_rules 的 AGENTS 渲染载荷。
        return ""

    # 返回 ci_rules 的 AGENTS 渲染载荷。
    return "\n".join(f"- `{item['workflow']}` runs `{item['command']}`." for item in rules)

# 定义 key_decisions 的AGENTS 渲染处理入口。
def key_decisions(context: dict) -> str:

    # 汇总 adrs，作为 AGENTS 受管段落拼装顺序。
    adrs = context.get("adrs", [])  # AGENTS 受管段落渲染输入值

    # 整理 key_decisions 需要的 architecture 渲染片段。
    architecture = context.get("architecture_files", [])  # AGENTS 受管段落渲染输入值

    # 汇总 docs，作为 AGENTS 受管段落拼装顺序。
    docs = context.get("documentation", [])  # AGENTS 受管段落渲染输入值

    # 汇总 lines，作为 AGENTS 受管段落拼装顺序。
    lines = [f"- Review `{path}` before changing architecture or policy." for path in adrs[:8]]  # AGENTS 受管段落渲染输入值

    # 调用 extend 处理 key_decisions。
    lines.extend(f"- Respect ownership or architecture guidance in `{path}`." for path in architecture[:4])

    # 校验 key_decisions 的渲染分支条件。
    if not lines and docs:

        # 汇总 lines，作为 AGENTS 受管段落拼装顺序。
        lines = [f"- Use `{path}` as a pointer; do not copy long documentation into AGENTS.md." for path in docs[:4]]  # AGENTS 受管段落渲染输入值

    # 返回 key_decisions 的 AGENTS 渲染载荷。
    return "\n".join(lines)

# 定义 codebase_state 的AGENTS 渲染处理入口。
def codebase_state(context: dict) -> str:

    # 汇总 configs，作为 AGENTS 受管段落拼装顺序。
    configs = context.get("quality_configs", [])  # AGENTS 受管段落渲染输入值

    # 整理 codebase_state 需要的 platform 渲染片段。
    platform = context.get("platform_files", [])  # AGENTS 受管段落渲染输入值

    # 整理 codebase_state 需要的 ide 渲染片段。
    ide = context.get("ide_settings", [])  # AGENTS 受管段落渲染输入值

    # 整理 codebase_state 需要的 dependency 渲染片段。
    dependency = context.get("dependency_configs", [])  # AGENTS 受管段落渲染输入值

    # 汇总 reference projects，作为 AGENTS 受管段落拼装顺序。
    reference_projects = context.get("reference_projects", [])  # AGENTS 受管段落渲染输入值

    # 汇总 lines，作为 AGENTS 受管段落拼装顺序。
    lines = [f"- Quality config detected: `{path}`." for path in configs]  # AGENTS 受管段落渲染输入值

    # 调用 extend 处理 codebase_state。
    lines.extend(f"- Platform/dev-environment file detected: `{path}`." for path in platform)

    # 调用 extend 处理 codebase_state。
    lines.extend(f"- Editor/IDE convention detected: `{path}`." for path in ide)

    # 调用 extend 处理 codebase_state。
    lines.extend(f"- Dependency automation config detected: `{path}`." for path in dependency)

    # 调用 extend 处理 codebase_state。
    lines.extend(f"- Reference project available: `{path}`. Treat as read-only context unless the user asks otherwise." for path in reference_projects)

    # 校验 codebase_state 的渲染分支条件。
    if not lines:

        # 返回 codebase_state 的 AGENTS 渲染载荷。
        return ""

    # 返回 codebase_state 的 AGENTS 渲染载荷。
    return "\n".join(lines)

# 定义 evolution_template_guidance 的AGENTS 渲染处理入口。
def evolution_template_guidance(project: Path, template_dir: Path | None = None) -> str:
    del project, template_dir

    # 返回 evolution_template_guidance 的 AGENTS 渲染载荷。
    return ""
def hook_policy(context: dict) -> str:

    # 汇总 hooks，作为 AGENTS 受管段落拼装顺序。
    hooks = context.get("hook_configs", [])  # AGENTS 受管段落渲染输入值

    # 校验 hook_policy 的渲染分支条件。
    if not hooks:

        # 返回 hook_policy 的 AGENTS 渲染载荷。
        return ""

    # 汇总 lines，作为 AGENTS 受管段落拼装顺序。
    lines = [f"- Hook framework/config detected: `{path}`." for path in hooks]  # AGENTS 受管段落渲染输入值

    # 追加 hook_policy 的 AGENTS 渲染行。
    lines.append("- Never bypass hooks with `--no-verify`; fix the underlying failure.")

    # 返回 hook_policy 的 AGENTS 渲染载荷。
    return "\n".join(lines)
def github_settings(context: dict) -> str:

    # 汇总 settings，作为 AGENTS 受管段落拼装顺序。
    settings = context.get("github_settings", [])  # AGENTS 受管段落渲染输入值

    # 校验 github_settings 的渲染分支条件。
    if not settings:

        # 返回 github_settings 的 AGENTS 渲染载荷。
        return ""

    # 返回 github_settings 的 AGENTS 渲染载荷。
    return "\n".join(f"- GitHub setting/ruleset detected: `{path}`." for path in settings)
def directory_coverage(context: dict) -> str:

    # 汇总 candidates，作为 AGENTS 受管段落拼装顺序。
    candidates = context.get("directory_coverage_candidates", [])  # AGENTS 受管段落渲染输入值

    # 校验 directory_coverage 的渲染分支条件。
    if not candidates:

        # 返回 directory_coverage 的 AGENTS 渲染载荷。
        return ""

    # 返回 directory_coverage 的 AGENTS 渲染载荷。
    return "\n".join(
        f"- Directory coverage candidate: `{path}/` may need scoped AGENTS.md if it has local rules."
        for path in candidates
    )
def heuristic_rows() -> str:

    # 返回 heuristic_rows 的 AGENTS 渲染载荷。
    return "\n".join([
        "| Adding dependency | Ask first |",
        "| Unsure about pattern | Read nearby files and golden samples |",
        "| Command not verified | Mark it unverified or omit it |",
    ])

# 定义 bullet_lines 的AGENTS 渲染处理入口。
def bullet_lines(items: list[str]) -> str:

    # 返回 bullet_lines 的 AGENTS 渲染载荷。
    return "\n".join(f"- {item}" for item in items)

# 定义 load_profile 的AGENTS 渲染处理入口。
def load_profile(project: Path, raw: str | None) -> dict | None:

    # 整理 load_profile 需要的 path 渲染片段。
    path = Path(raw).resolve() if raw else project / ".agents" / "agents-control.json"  # AGENTS 受管段落渲染输入值

    # 校验 load_profile 的渲染分支条件。
    if not path.exists():

        # 返回 load_profile 的 AGENTS 渲染载荷。
        return None

    # 保护 load_profile 中允许失败的外部访问。
    try:

        # 整理 load_profile 需要的 data 渲染片段。
        dict_data = json.loads(path.read_text(encoding="utf-8"))  # AGENTS 受管段落渲染输入值
    except json.JSONDecodeError as exc:

        # 抛出 load_profile 已确认的阻断原因。
        raise SystemExit(f"Could not parse profile JSON: {path}: {exc}")

    # 校验 load_profile 的渲染分支条件。
    if not isinstance(dict_data, dict):

        # 抛出 load_profile 已确认的阻断原因。
        raise SystemExit(f"Profile must be a JSON object: {path}")

    # 返回 load_profile 的 AGENTS 渲染载荷。
    return dict_data

# 定义 inferred_project_skill_dir 的AGENTS 渲染处理入口。
def inferred_project_skill_dir(project: Path, profile: dict | None = None) -> Path | None:

    # 整理 inferred_project_skill_dir 需要的 effective profile 渲染片段。
    effective_profile = profile if isinstance(profile, dict) else None  # AGENTS 受管段落渲染输入值

    # 校验 inferred_project_skill_dir 的渲染分支条件。
    if effective_profile:

        # 整理 inferred_project_skill_dir 需要的 layout 渲染片段。
        layout = effective_profile.get("skill_layout") if isinstance(effective_profile.get("skill_layout"), dict) else {}  # AGENTS 受管段落渲染输入值

        # 定位 raw path 的文件边界，供 inferred_project_skill_dir 后续读写校验使用。
        raw_path = str(layout.get("path") or "").strip()  # AGENTS 受管段落渲染输入值

        # 校验 inferred_project_skill_dir 的渲染分支条件。
        if raw_path:

            # 整理 inferred_project_skill_dir 需要的 candidate 渲染片段。
            candidate = (project / raw_path).resolve()  # AGENTS 受管段落渲染输入值

            # 校验 inferred_project_skill_dir 的渲染分支条件。
            if (candidate / "VERSION").is_file():

                # 返回 inferred_project_skill_dir 的 AGENTS 渲染载荷。
                return candidate

        # 整理 inferred_project_skill_dir 需要的 name 渲染片段。
        name = str(effective_profile.get("name") or "").strip()  # AGENTS 受管段落渲染输入值

        # 校验 inferred_project_skill_dir 的渲染分支条件。
        if effective_profile.get("kind") == "skill" and name:

            # 整理 inferred_project_skill_dir 需要的 candidate 渲染片段。
            candidate = (project / "skills" / name).resolve()  # AGENTS 受管段落渲染输入值

            # 校验 inferred_project_skill_dir 的渲染分支条件。
            if (candidate / "VERSION").is_file():

                # 返回 inferred_project_skill_dir 的 AGENTS 渲染载荷。
                return candidate

    # 整理 inferred_project_skill_dir 需要的 skills root 渲染片段。
    skills_root = project / "skills"  # AGENTS 受管段落渲染输入值

    # 校验 inferred_project_skill_dir 的渲染分支条件。
    if skills_root.is_dir():

        # 汇总 candidates，作为 AGENTS 受管段落拼装顺序。
        candidates = [path.resolve() for path in skills_root.iterdir() if (path / "VERSION").is_file()]  # AGENTS 受管段落渲染输入值

        # 校验 inferred_project_skill_dir 的渲染分支条件。
        if len(candidates) == 1:

            # 返回 inferred_project_skill_dir 的 AGENTS 渲染载荷。
            return candidates[0]

    # 返回 inferred_project_skill_dir 的 AGENTS 渲染载荷。
    return None

# 定义 resolved_project_version 的AGENTS 渲染处理入口。
def resolved_project_version(project: Path, profile: dict | None = None) -> str:

    # 整理 resolved_project_version 需要的 skill dir 渲染片段。
    skill_dir = inferred_project_skill_dir(project, profile)  # AGENTS 受管段落渲染输入值

    # 返回 resolved_project_version 的 AGENTS 渲染载荷。
    return read_skill_version(skill_dir) if skill_dir else ""

# 定义 resolved_generator_version 的AGENTS 渲染处理入口。
def resolved_generator_version(project: Path, profile: dict | None = None, project_version: str = "") -> str:

    # 校验 resolved_generator_version 的渲染分支条件。
    if (
        isinstance(profile, dict)
        and profile.get("kind") == "skill"
        and str(profile.get("name", "")).strip() == "agents-md-generator"
        and project_version
    ):

        # 返回 resolved_generator_version 的 AGENTS 渲染载荷。
        return project_version

    # 整理 resolved_generator_version 需要的 generator version、  渲染片段。
    generator_version, _ = preferred_skill_version()  # AGENTS 受管段落渲染输入值

    # 返回 resolved_generator_version 的 AGENTS 渲染载荷。
    return generator_version or "unknown"

# 定义 control_profile 的AGENTS 渲染处理入口。
def control_profile(profile: dict | None, project: Path, project_version: str = "") -> str:

    # 校验 control_profile 的渲染分支条件。
    if not profile:

        # 返回 control_profile 的 AGENTS 渲染载荷。
        return "\n".join([
            "- Strong control: not configured.",
            (
                f"- Run "  # AGENTS 长文本片段
                f"`{project_command(project, profile, 'collect_design_profile.py', '<project>', '--answers', 'answers.json', '--write')}` "  # AGENTS 长文本片段
                f"before claiming strict control."  # AGENTS 长文本片段
            ),
            "- Until configured, ask the mandatory design questions before writing controlled AGENTS.md output.",
        ])

    # 汇总 lines，作为 AGENTS 受管段落拼装顺序。
    list_lines = [  # AGENTS 受管段落渲染输入值
        "- Strong control: complete.",  # AGENTS 受管段落渲染输入值
        f"- Development type: {profile.get('kind', 'unknown')}.",  # AGENTS 受管段落渲染输入值
        f"- Name: {profile.get('name', 'unknown')}.",  # AGENTS 受管段落渲染输入值
        f"- Version: {project_version or 'unknown'}.",  # AGENTS 受管段落渲染输入值
        f"- Default conversation language: {profile.get('default_conversation_language', '中文')}.",  # AGENTS 受管段落渲染输入值
        f"- Local governance detail source: `{local_rule_config_path(project, profile)}` for long-task, maintainability, and tool-layout rules.",  # AGENTS 受管段落渲染输入值
        f"- Purpose/reason: {profile.get('purpose', 'unknown')} / {profile.get('reason', 'unknown')}.",  # AGENTS 受管段落渲染输入值
    ]

    # 校验 control_profile 的渲染分支条件。
    if profile.get("development_requirements"):

        # 追加 control_profile 的 AGENTS 渲染行。
        list_lines.append(f"- Development requirements: {profile['development_requirements']}.")

    # 汇总 extra requirements，作为 AGENTS 受管段落拼装顺序。
    extra_requirements = str(profile.get("extra_requirements", "")).strip()  # AGENTS 受管段落渲染输入值

    # 校验 control_profile 的渲染分支条件。
    if extra_requirements and extra_requirements.casefold() != "none":

        # 追加 control_profile 的 AGENTS 渲染行。
        list_lines.append(f"- Additional user requirements: {extra_requirements}.")

    # 校验 control_profile 的渲染分支条件。
    if profile.get("validation_method"):

        # 追加 control_profile 的 AGENTS 渲染行。
        list_lines.append(f"- Validation method: {profile['validation_method']}.")

    # 校验 control_profile 的渲染分支条件。
    if profile.get("resource_plan"):

        # 追加 control_profile 的 AGENTS 渲染行。
        list_lines.append(f"- Resource boundaries: {profile['resource_plan']}.")

    # 校验 control_profile 的渲染分支条件。
    if profile.get("expected_outcome"):

        # 追加 control_profile 的 AGENTS 渲染行。
        list_lines.append(f"- Expected outcome: {profile['expected_outcome']}.")

    # 整理 control_profile 需要的 audience 渲染片段。
    audience = profile.get("audience_or_environment")  # AGENTS 受管段落渲染输入值

    # 校验 control_profile 的渲染分支条件。
    if audience:

        # 追加 control_profile 的 AGENTS 渲染行。
        list_lines.append(f"- Audience/environment: {audience}.")

    # 校验 control_profile 的渲染分支条件。
    if profile.get("validation_granularity"):

        # 追加 control_profile 的 AGENTS 渲染行。
        list_lines.append(f"- Validation granularity: {profile['validation_granularity']}.")

    # 校验 control_profile 的渲染分支条件。
    if profile.get("forward_testing_policy"):

        # 追加 control_profile 的 AGENTS 渲染行。
        list_lines.append(f"- Forward testing: {profile['forward_testing_policy']}.")

    # 校验 control_profile 的渲染分支条件。
    if profile.get("reference_materials_temporary"):

        # 追加 control_profile 的 AGENTS 渲染行。
        list_lines.append((
            "- Temporary reference materials were used; remove them manually after "  # AGENTS 长文本片段
            "development and do not copy local reference paths into AGENTS.md."  # AGENTS 长文本片段
        ))

    # 返回 control_profile 的 AGENTS 渲染载荷。
    return "\n".join(list_lines)

# 定义 directory_contract 的AGENTS 渲染处理入口。
def directory_contract(profile: dict | None, project: Path) -> str:

    # 校验 directory_contract 的渲染分支条件。
    if not profile:

        # 返回 directory_contract 的 AGENTS 渲染载荷。
        return "- Directory contract: not confirmed. Do not freeze structure until the user confirms local, remote, and feature-addition layout."

    # 整理 directory_contract 需要的 contract 渲染片段。
    contract = profile.get("directory_contract", {})  # AGENTS 受管段落渲染输入值

    # 整理 directory_contract 需要的 dir contract 渲染片段。
    dir_contract = profile.get("dir_manager_contract", {})  # AGENTS 受管段落渲染输入值

    # 整理 directory_contract 需要的 settings policy 渲染片段。
    settings_policy = contract.get("workspace_settings_policy", {}) if isinstance(contract.get("workspace_settings_policy", {}), dict) else {}  # AGENTS 受管段落渲染输入值

    # 整理 directory_contract 需要的 primary root 渲染片段。
    primary_root = str(contract.get("primary_project_root", "")).strip()  # AGENTS 受管段落渲染输入值

    # 汇总 lines，作为 AGENTS 受管段落拼装顺序。
    list_lines = [  # AGENTS 受管段落渲染输入值
        f"- Confirmed: {contract.get('confirmed', False)}.",  # AGENTS 受管段落渲染输入值
        f"- Local structure: {contract.get('local', 'not specified')}.",  # AGENTS 受管段落渲染输入值
        f"- Remote structure: {contract.get('remote', 'not specified')}.",  # AGENTS 受管段落渲染输入值
        f"- Primary project root: `{primary_root}` is the canonical main project location." if primary_root else "- Primary project root: not configured.",
        (
            f"- Workspace settings: keep work-folder project config under "  # AGENTS 长文本片段
            f"`{settings_policy.get('folder', '.settings')}/`; local-only files use "  # AGENTS 长文本片段
            f"`{settings_policy.get('local_default_file', '.settings/project.local.json')}` "  # AGENTS 长文本片段
            f"or `{settings_policy.get('folder', '.settings')}/<name>.local.json`, and "  # AGENTS 长文本片段
            f"remote workspaces use "  # AGENTS 长文本片段
            f"`{settings_policy.get('remote_default_file', '.settings/project.remote.json')}` "  # AGENTS 长文本片段
            f"or `{settings_policy.get('folder', '.settings')}/<name>.remote.json`."  # AGENTS 长文本片段
        ),
        (
            f"- Security rule: never copy "  # AGENTS 长文本片段
            f"`{settings_policy.get('folder', '.settings')}/*.local.json` such as "  # AGENTS 长文本片段
            f"`{settings_policy.get('folder', '.settings')}/server_list.local.json` to a "  # AGENTS 长文本片段
            f"remote server; keep local private config local and use `.remote.json` files "  # AGENTS 长文本片段
            f"for remote project settings instead."  # AGENTS 长文本片段
        ),
        (
            "- Root-level work artifacts: keep `tests/`, `smoke/` and `smoke-*`, "  # AGENTS 长文本片段
            "`reports/`, `runs/` at work-folder root; do not place them under the primary "  # AGENTS 长文本片段
            "project root."  # AGENTS 长文本片段
        ),
        (
            "- Remote deployment, conda, runtime, backup, and archive path details live in "  # AGENTS 长文本片段
            "`docs/dir_manager/planned_structure.json`; root AGENTS.md is only the entry "  # AGENTS 长文本片段
            "rule index."  # AGENTS 长文本片段
        ),
        (
            "- Remote deployment boundary: do not sync local skill-development content to "  # AGENTS 长文本片段
            "remote servers; deploy only explicit runtime/deployment artifacts unless the "  # AGENTS 长文本片段
            "user explicitly overrides."  # AGENTS 长文本片段
        ),
        (
            "- New feature structure: keep new work inside the confirmed local structure "  # AGENTS 长文本片段
            "and primary project root; read the local JSON governance config before "  # AGENTS 长文本片段
            "assuming detailed maintainability or script layout rules."  # AGENTS 长文本片段
        ),
        "- Do not add new top-level directories or move ownership boundaries without updating this contract.",  # AGENTS 受管段落渲染输入值
        (
            f"- Dir manager gate: review directory create/move/delete/rename plans with "  # AGENTS 长文本片段
            f"`{dir_contract.get('folder', 'docs/dir_manager')}/DIR_MANAGER.md` before "  # AGENTS 长文本片段
            f"changing folder structure."  # AGENTS 长文本片段
        ),
        f"- Required command before folder changes: `{project_command(project, profile, 'manage_dirs.py', 'review', '<project>', '--input', 'change.json')}`.",  # AGENTS 受管段落渲染输入值
        "- If directory review blocks the change, refuse default execution, explain the risk, and ask for explicit user force-confirmation before proceeding.",  # AGENTS 受管段落渲染输入值
    ]

    # 校验 directory_contract 的渲染分支条件。
    if primary_root and str(profile.get("kind", "")).strip().lower() == "skill":

        # skill release evals 是根级决策边界，保留短规则。
        list_lines.insert(4, f"- Skill-local release content: keep eval assets under `{primary_root.rstrip('/')}/evals/`; they stay in the skill package.")

    # 返回 directory_contract 的 AGENTS 渲染载荷。
    return "\n".join(list_lines)

# 定义 remote_server_contract 的AGENTS 渲染处理入口。
