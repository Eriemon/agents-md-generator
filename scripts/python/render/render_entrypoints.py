"""实现根级与作用域 AGENTS.md 的渲染入口。"""

# 共享忽略目录保证 scoped 扫描与项目发现一致。
from agents_common import SKIP_DIRS
from codebase_memory_mcp import enforce_codebase_memory_write_gate
from tester_worker_profile import ensure_tester_worker_profile

# 根正文按稳定顺序连接项目事实、命令和局部约束。
def generated_root_body(
    project: Path,
    dict_values: dict[str, str],
    manual: str = "",
) -> str:
    """生成默认模板和自定义模板共享的根正文。

    参数：project 为仓库根。
    参数：dict_values 为已发现并渲染的项目事实。
    参数：manual 为受管块之外的人工文本。
    返回：以单个换行结尾的根 AGENTS.md 正文。
    """

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
        compact_section("project", "Project", project_section(dict_values)),  # 项目身份受管段。
        commands_section(dict_values),  # 已发现命令受管段。
        compact_section("task-specific-gates", "Task-specific gates", dict_values["TASK_SPECIFIC_GATES"]),  # 项目专用门禁段。
        compact_section("local-conventions", "Local conventions", local_conventions_section(dict_values)),  # 本地执行约定段。
        compact_section("read-before-changing", "Read before changing", dict_values["READ_BEFORE_CHANGING"]),  # 修改前必读段。
        compact_section("scoped-instructions", "Scoped instructions", scoped_instructions(project)),  # 下级规则索引段。
        (
            "## When Instructions Conflict\n"
            "Use this order: explicit user prompt, closest AGENTS.md, "
            "parent AGENTS.md, general repository docs."
        ),
    ]  # 根文件候选段落。

    # 人工文本只在实际存在时附加，避免空段落改变末尾格式。
    if manual:

        # 受管正文之后保留人工维护区域。
        list_parts.append(manual)

    # 空段落在连接前过滤，正文统一保留一个末尾换行。
    return "\n".join(str_part for str_part in list_parts if str(str_part).strip()).rstrip() + "\n"

# 项目摘要只保留影响代理执行的身份和控制字段。
def project_section(dict_values: dict[str, str]) -> str:
    """渲染项目身份和控制摘要。

    参数：dict_values 为项目事实映射。
    返回：去重后的项目摘要行。
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
        elif str_stripped.startswith("Global .codex/AGENTS.md:"):

            # 统一后的状态行避免把完整全局文件正文复制到项目摘要。
            str_stripped = (
                "Global .codex/AGENTS.md: present with a managed baseline; "
                "read the current work folder root AGENTS.md first."
            )  # 规范化后的全局基线行

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

# 单行本地约定压缩保留 verifier 所需的固定短语。
def _compact_local_convention_line(str_line: str) -> str | None:
    """压缩一条本地约定，保留机器校验所需的固定短语。

    参数：str_line 为已经去除空白合同块中的一行。
    返回：压缩后的规则行；被上层合同吸收的行返回 None。
    """

    # 会话合同压缩为语言、完成和证据三条可执行规则。
    if str_line.startswith("- Natural-language replies"):

        # 技术字面量保持不变，只修正当前项目要求的语言表述。
        str_line = (
            str_line.replace(  # 先替换会话语言规则中的旧表述
                "unless the user switches languages",  # 待替换的旧语言短语
                "unless the user switches language",  # 当前项目的语言短语
            ).replace(
                "; keep technical literals unchanged",  # 被移除的冗余后缀
                "",  # 后缀删除结果
            )
        )  # 修正后的会话语言规则

        # 当前分支已完成会话规则压缩。
        return str_line

    # 已被完成规则覆盖的解释行不再进入根级文件。
    if str_line.startswith("- Finish feasible requested work"):

        # None 表示当前行由完成合同的权威入口承载。
        return None

    # 完成检查规则保留阻断、跳过和用户修改保护。
    if str_line.startswith("- Run narrow then final checks"):

        # 压缩文本保留交付后仍需公开的证据边界。
        str_line = (  # 精简后的完成检查规则
            "- Run narrow then final checks; report blockers, skipped checks, next steps; "
            "preserve user changes"
        )

        # 当前分支已完成完成检查规则压缩。
        return str_line

    # 注释规则保留硬门禁，省略不会改变执行的解释性修饰语。
    if str_line.startswith("- 注释质量："):

        # 根级规则必须直接暴露注释的允许范围和禁止行为。
        str_line = (  # 精简后的注释质量规则
            "- 注释质量：只允许非显然意图、不变量、风险、生成边界或公共 API 行为注释；"
            "禁止复述代码；禁止未经明确要求的批量 AI 注释；不能把语句、注释、函数粘连到一起；"
            "严禁把代码压缩到一行；炫技代码"
        )

        # 当前分支已完成注释规则压缩。
        return str_line

    # 输出格式规则保留人读前缀与机器输出边界。
    if str_line.startswith("- 格式："):

        # 根级规则必须保留三类消息级别和 quiet 行为。
        str_line = (  # 精简后的输出格式规则
            "- 格式：`> INFO: [{kind}]`/`> WARNING: [{kind}]`/`> ERR: [{kind}]`；"
            "Python 过程性 INFO 默认打印，`--quiet` 关闭，WARNING 和 ERR 继续可见；"
            "机器可读输出不套前缀。"
        )

        # 当前分支已完成输出格式规则压缩。
        return str_line

    # 已被更高层的生成合同覆盖的行不再重复输出。
    if str_line.startswith("- 生成代码须"):

        # 生成合同已经在上层负责该行的执行语义。
        return None

    # 文件命名规则只保留长度与语义复核这两个硬条件。
    if str_line.startswith("- 文件命名："):

        # 根级摘要不复制完整命名治理说明。
        str_line = "- 文件命名：不超过 30 个英文字符；Agent 语义复核。"  # 精简后的文件命名规则

        # 当前行已经转换为根级可执行的命名摘要。
        return str_line

    # 已被文件命名规则吸收的语义细则不再重复输出。
    if str_line.startswith("- 文件命名语义："):

        # None 表示当前行由上一条命名规则承载。
        return None

    # 双技能共同门禁必须仍能被逐行校验器识别。
    if str_line.startswith("- 语言技能共同门禁："):

        # 共同门禁正文用于判断是否已同时安装两个语言技能。
        str_route_body = str_line.split("：", 1)[1].strip()  # 当前语言共同门禁正文

        # 共同门禁仅在两个语言技能都可用时替换。
        bool_both_skills = (
            "readable-python-generator" in str_route_body  # Python 技能共同门禁标记
            and "readable-script-generator" in str_route_body  # 脚本技能共同门禁标记
        )  # 共同门禁双技能可用状态

        # 双技能已安装时投影完整共同门禁，否则保留原始配置行。
        if bool_both_skills:

            # 共同门禁文本必须保留先思考、同时加载和不得事后补做。
            str_line = (  # 固定的双技能共同门禁
                "- 语言技能共同门禁：创建或修改 Python、bat/cmd、shell/bash、PowerShell、Tcl 代码时必须先思考并同时加载 "
                "`readable-python-generator` 与 `readable-script-generator`；两个技能组成当前可执行的语言门禁，"
                "两个技能的门禁必须在过程中满足，全部通过后才能继续，不得事后补做。"
            )

        # 共同门禁分支已经决定当前规则的最终文本。
        return str_line

    # Python 路由必须保留最终所有权和共同门禁边界。
    if str_line.startswith("- 语言技能路由（Python）："):

        # Python 路由正文用于判断是否已同时安装两个语言技能。
        str_route_body = str_line.split("：", 1)[1].strip()  # 当前 Python 路由正文

        # Python 路由仅在两个语言技能都可用时替换。
        bool_both_skills = (
            "readable-python-generator" in str_route_body  # Python 路由安装标记
            and "readable-script-generator" in str_route_body  # 脚本路由安装标记
        )  # Python 路由双技能可用状态

        # 双技能已安装时投影 Python 的最终所有权。
        if bool_both_skills:

            # Python 仍由 Python 技能负责，脚本技能不能接管。
            str_line = (  # 固定的 Python 路由门禁
                "- 语言技能路由（Python）：进行 Python 代码生成、修改、注释和规范化时，Python 最终仍由 "
                "`readable-python-generator` 负责；任务分类、注释质量、变量命名、质量门禁；"
                "创建或修改时必须加载该技能；不得由 `readable-script-generator` 接管。"
            )

        # Python 路由分支已经决定当前规则的最终文本。
        return str_line

    # 脚本路由必须保留脚本技能的最终所有权和 Python 边界。
    if str_line.startswith("- 语言技能路由（脚本）："):

        # 脚本分支先剥离规则前缀，再判断双技能是否齐全。
        str_route_body = str_line.split("：", 1)[1].strip()  # 当前脚本路由正文

        # 脚本目标的双技能判定决定是否投影脚本所有权。
        bool_both_skills = (
            "readable-python-generator" in str_route_body  # 脚本分支的 Python 安装标记
            and "readable-script-generator" in str_route_body  # 脚本分支的脚本安装标记
        )  # 脚本路由双技能可用状态

        # 双技能已安装时投影脚本语言的最终所有权。
        if bool_both_skills:

            # 脚本包装器按脚本目标路由，不能被 Python 技能接管。
            str_line = (  # 固定的脚本路由门禁
                "- 语言技能路由（脚本）：bat/cmd、shell/bash、PowerShell、Tcl 脚本目标最终由 "
                "`readable-script-generator` 负责；Python 目标继续使用 `readable-python-generator`；"
                "Python 专属技能边界：调用 Python 外部命令的脚本包装器仍按脚本目标处理。"
            )

        # 脚本路由输出在此返回，避免回落到默认规则。
        return str_line

    # 未命中特殊合同时保留原始规则行。
    return str_line

# 本地约定段落只负责组合合同和稳定去重。
def local_conventions_section(dict_values: dict[str, str]) -> str:
    """合并本仓库的执行约定。

    参数：dict_values 为项目事实映射。
    返回：按合同顺序连接的本地约定。
    """

    # 三个合同分别约束完成行为、编码方式和脚本输出。
    list_blocks = [
        dict_values["CONVERSATION_COMPLETION_CONTRACT"],  # 对话完成合同。
        dict_values["CODING_BEHAVIOR_BASELINE"],  # 编码行为合同。
        dict_values["SCRIPT_OUTPUT_POLICY"],  # 脚本输出合同。
    ]  # 本地约定候选块。

    # 根 AGENTS 只携带可执行的最小合同，详细解释仍由 JSON 和参考文档承载。
    list_compact_lines: list[str] = []  # 精简后的本地约定行。

    # 按稳定顺序压缩每条合同，保留 verifier 所需的固定短语。
    for str_block in list_blocks:

        # 空合同不进入输出，避免预算被占位内容消耗。
        if not str_block.strip():

            # 当前块没有可执行规则时继续读取下一块。
            continue

        # 逐行处理时保留原始顺序，便于受管块稳定更新。
        for str_line in str_block.splitlines():

            # 空行只承担源码格式，不需要复制到根级索引。
            if not str_line.strip():

                # 受管根统一由 compact_section 负责段落分隔。
                continue

            # 单行 helper 统一处理固定文本和路由分支。
            str_compact_line = _compact_local_convention_line(str_line)  # 单行压缩结果

            # 被更高层合同吸收的行不进入结果。
            if str_compact_line is None:

                # 当前行没有独立执行价值。
                continue

            # 压缩后的行仍保持一行一个规则，避免改变机器读取边界。
            list_compact_lines.append(str_compact_line)

    # 非空合同去除边缘空白后连接，避免重复生成解释段落。
    return "\n".join(str_line.strip() for str_line in list_compact_lines if str_line.strip())

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
) -> str:
    """渲染根 AGENTS.md。

    参数：project 为仓库根。
    参数：template_dir 为可选自定义模板目录。
    参数：profile 为可选强控制配置。
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
    dict_values = template_values(project, profile, template_dir)  # 根模板替换事实。

    # 人工区域去除边缘空白后进入统一正文。
    str_manual = manual_content(str_existing).strip()  # 待保留人工文本。

    # 默认和自定义模板路径共享完全相同的生成正文。
    str_generated_body = generated_root_body(project, dict_values, str_manual)  # 统一根正文。

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

    # 普通分支治理确认不能覆盖 worktree 硬阻断。
    # 显式确认参数只授权解除 Git 索引跟踪，不删除本地产物。
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

# 初始结构检查只负责确认门禁，不提前执行文件迁移。
def enforce_structure_confirmation(
    project: Path,
    bool_confirm_fix: bool,
) -> None:
    """验证结构阻断是否已获得用户确认。

    参数：project 为仓库根。
    参数：bool_confirm_fix 表示用户是否确认推荐修复。
    返回：已批准或已确认时返回；否则输出 JSON 并退出。
    异常：治理阻断时抛出 SystemExit(1)。
    """

    # 初始门禁必须在分支检查之前保持只读。
    dict_structure = structure_gate(project)  # 写入前结构检查。

    # 已批准结构或显式确认修复都可进入分支门禁。
    if dict_structure.get("approved", True) or bool_confirm_fix:

        # 此阶段不执行迁移，避免污染后续分支检查。
        return

    # 未确认的阻断不得修改 AGENTS.md 或 docs。
    emit_json(
        {
            "errors": [
                "structure governance requires user confirmation before writing AGENTS.md or docs governance"
            ],
            "structure_gate": dict_structure,
            "requires_user_confirmation": True,
        }
    )

    # 非零退出阻止调用方误判写入成功。
    raise SystemExit(1)

# 已确认结构修复在分支门禁通过后执行并复检。
def apply_confirmed_structure_fix(
    project: Path,
    bool_confirm_fix: bool,
) -> None:
    """执行可选结构修复并验证最终状态。

    参数：project 为仓库根。
    参数：bool_confirm_fix 表示用户是否要求执行修复。
    返回：未请求或修复通过时返回；失败时输出 JSON 并退出。
    异常：修复或复检失败时抛出 SystemExit(1)。
    """

    # 未确认修复时保持文件系统不变。
    if not bool_confirm_fix:

        # 普通批准路径无需迁移。
        return

    # 用户确认后执行结构治理器给出的修复。
    dict_fix = apply_structure_fix(project)  # 结构修复执行报告。

    # 文件操作错误必须在任何规则写入前返回。
    if dict_fix.get("errors"):

        # 错误载荷保留修复器的具体诊断。
        emit_json(
            {
                "errors": [
                    "structure governance fix failed before writing AGENTS.md or docs governance"
                ],
                "structure_fix": dict_fix,
            }
        )

        # 修复失败终止渲染写入。
        raise SystemExit(1)

    # 修复后重新检查，不能依赖操作成功即推断门禁通过。
    dict_structure = structure_gate(project)  # 修复后的结构检查。

    # 复检通过后继续文档预检。
    if dict_structure.get("approved", True):

        # 最终结构已满足治理合同。
        return

    # 同时返回修复报告和复检报告便于定位残留问题。
    emit_json(
        {
            "errors": [
                "structure governance remains blocked after the confirmed structure fix attempt"
            ],
            "structure_fix": dict_fix,
            "structure_gate": dict_structure,
        }
    )

    # 复检失败保持非零退出。
    raise SystemExit(1)

# 分支门禁保持 worktree 硬阻断不可确认覆盖。
def enforce_branch_gate(
    project: Path,
    bool_confirm_governance: bool,
) -> None:
    """验证分支与单工作树治理合同。

    参数：project 为仓库根。
    参数：bool_confirm_governance 表示是否确认普通分支整理风险。
    返回：通过时无返回；阻断时输出 JSON 并退出。
    异常：硬阻断或未确认普通阻断时抛出 SystemExit(1)。
    """

    # 分支检查先返回 hard_blocking 与普通批准状态。
    dict_branch = branch_gate(project)  # 当前 Git 治理报告。

    # 硬阻断始终失败；普通阻断可由显式确认继续。
    bool_blocked = dict_branch.get("hard_blocking", False) or (  # Git 治理是否禁止本次写入。
        not dict_branch.get("approved", True)  # 普通分支门禁未批准。
        and not bool_confirm_governance  # 未获得普通分支风险确认。
    )  # 当前写入是否被 Git 治理阻断。

    # 已批准或已确认普通风险时继续。
    if not bool_blocked:

        # 单工作树政策已满足。
        return

    # worktree 硬阻断与普通分支确认使用不同错误文本。
    str_error = (
        "Git worktree governance is hard-blocking and cannot be confirmed away"  # worktree 硬阻断摘要。
        if dict_branch.get("hard_blocking", False)  # 按硬阻断类型选择诊断。
        else "branch governance requires user confirmation before writing AGENTS.md or docs governance"  # 普通阻断摘要。
    )  # Git 治理阻断摘要。

    # 机器载荷说明普通阻断是否仍可确认。
    emit_json(
        {
            "errors": [str_error],
            "branch_gate": dict_branch,
            "requires_user_confirmation": not dict_branch.get("hard_blocking", False),
        }
    )

    # 阻断状态不允许进入文档脚手架或文件写入。
    raise SystemExit(1)

# 强控制写入前完成结构、分支和文档布局治理。
def prepare_controlled_write(
    project: Path,
    profile: dict,
    args: argparse.Namespace,
) -> None:
    """执行强控制项目写入前治理。

    参数：project 为仓库根。
    参数：profile 为已加载的强控制配置。
    参数：args 提供三个用户确认开关。
    返回：所有门禁通过并完成必要脚手架后返回。
    异常：任一治理门禁失败时抛出 SystemExit(1)。
    """

    # 初始结构检查仅确认风险，不在分支检查前迁移文件。
    enforce_structure_confirmation(project, args.confirm_structure_fix)

    # worktree 与分支治理必须在任何项目文件修改之前通过。
    enforce_branch_gate(project, args.confirm_branch_governance)

    # 分支门禁通过后再闭合知识图谱门禁，避免其 `.gitignore` 写入污染预检事实。
    dict_codebase_gate = enforce_codebase_memory_write_gate(  # 根规则写入前知识图谱门禁结果
        project,  # 待写入根规则的项目
        profile,  # 已加载的强控制画像
        apply=True,  # 执行必要忽略规则修复
        confirm_untrack=args.confirm_codebase_memory_untrack,  # 用户解除跟踪确认
    )

    # 未通过依赖、索引或 Git 边界时阻止任何后续文件迁移。
    if not dict_codebase_gate.get("ok"):

        # 输出精确机器可读门禁诊断。
        emit_json(dict_codebase_gate)

        # 写入路径以非零状态终止。
        raise SystemExit(1)

    # 分支门禁通过后才执行用户确认的结构迁移。
    apply_confirmed_structure_fix(project, args.confirm_structure_fix)

    # docs preflight 判断现有布局是否需要用户确认。
    dict_docs = preflight_docs(project)  # 文档布局预检报告。

    # 未确认的新文档布局不能自动创建。
    if dict_docs["requires_user_confirmation"] and not args.confirm_docs_layout:

        # JSON 载荷保留预检证据和确认标记。
        emit_json(
            {
                "errors": [
                    "docs layout requires user confirmation before writing AGENTS.md or docs governance"
                ],
                "docs_preflight": dict_docs,
                "requires_user_confirmation": True,
            }
        )

        # 文档布局阻断保持非零退出。
        raise SystemExit(1)

    # 全局规则覆盖文件在文档脚手架之前建立。
    ensure_global_rule_overrides_file(project, profile)

    # 治理目录和文档按项目配置创建或同步。
    scaffold_docs(project)

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

    # 每次受管生成写入前都检查并自动引导唯一 tester_worker 配置。
    if args.write:

        # 生成前确保唯一 tester_worker 配置可用并记录结果。
        dict_tester_result = ensure_tester_worker_profile(  # tester_worker 配置结果。
            write=True,  # 写入或刷新 tester_worker 配置。
            confirm_update=args.confirm_tester_worker_update,  # 复用单次授权收据。
        )

        # 写回验证失败必须阻止 AGENTS 落盘，保留明确失败证据。
        dict_final_validation = dict_tester_result.get("final_validation", {})  # 最终 TOML 验证。

        # 无效配置不得进入 AGENTS.md 写入流程。
        if isinstance(dict_final_validation, dict) and not dict_final_validation.get("valid", False):

            # 以稳定错误前缀报告配置验证失败。
            raise SystemExit(
                "> ERR: [Python] tester_worker.toml failed TOML or role validation"
            )

    # 自定义模板目录转换为绝对位置。
    path_template_dir = (
        Path(args.template_dir).resolve()  # 显式模板绝对位置。
        if args.template_dir  # 仅显式模板位置需要解析。
        else None  # 未指定时使用内置模板。
    )  # 可选模板目录。

    # profile 加载器解析显式文件或项目默认控制配置。
    profile = load_profile(path_project, args.profile)  # 当前强控制配置。

    # 初始根文本支持默认只读草稿路径。
    str_root_text = render_root(path_project, path_template_dir, profile)  # 当前根规则草稿。

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
        str_root_text = render_root(path_project, path_template_dir, profile)  # 治理后的根规则文本。

    # 根文件和必要 scoped 文件形成原子校验候选。
    list_pending = collect_pending_writes(path_project, str_root_text, path_template_dir)  # 待写入文件。

    # 所有文本在落盘前共同通过大小门禁。
    validate_pending_sizes(path_project, list_pending)

    # 非强控制项目仍需要默认全局规则覆盖文件。
    if profile is None:

        # 空 profile 触发默认覆盖配置初始化。
        ensure_global_rule_overrides_file(path_project, profile)

    # 门禁全部通过后按候选顺序写入。
    for path_file, str_text in list_pending:

        # UTF-8 写入保持生成文件跨平台一致。
        path_file.write_text(str_text, encoding="utf-8")

# 直接执行 shard 时进入 CLI；被 render_agents.py exec 时同样保留入口合同。
if __name__ == "__main__":

    # 模块入口只调用已拆分的编排函数。
    main()
