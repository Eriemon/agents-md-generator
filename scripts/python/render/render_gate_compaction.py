"""压缩根 AGENTS.md 门禁，同时保留触发条件、停止线和权威入口。"""

# 文档与 memory 生命周期规则共享有状态的合并边界。
def compact_lifecycle_gate_line(
    str_line: str,
    bool_docs_added: bool,
    bool_memory_added: bool,
) -> tuple[bool, str | None, bool, bool]:
    """合并文档与 memory 生命周期规则。

    参数:
        str_line: 当前待压缩的根级规则行。
        bool_docs_added: 文档生命周期入口是否已经写入。
        bool_memory_added: memory 合并入口是否已经写入。

    返回:
        是否已处理、可选替换文本和两个更新后的状态标记。
    """

    # 首条文档规则后补充统一的开始与完成动作。
    if str_line.startswith("- Before new work"):

        # 从 run 片段提取恢复命令，保留外部工作区可执行的安装路径。
        str_resume_check = (  # 提取出的恢复检查命令
            str_line.split("run `", 1)[1].split("`", 1)[0]  # 受管恢复命令正文
            if "run `" in str_line  # 当前行包含可提取命令时进入正文分支
            else "manage_docs.py resume-check <project>"  # 缺少命令时使用稳定回退入口
        )

        # owner 仓库保留项目内可复制命令，外部工作区保留完整安装技能命令。
        bool_owner_relative = str_resume_check.startswith(  # 是否为 owner 仓库相对命令
            "python skills/agents-md-generator/"  # owner 仓库命令前缀
        )

        # 根据 owner 仓库边界选择可复制的恢复命令显示文本。
        str_resume_display = (
            f"`{str_resume_check}`"  # 可复制的恢复命令
            if (  # 可公开命令的路径条件
                "<codex-home>/skills/agents-md-generator/" in str_resume_check  # 已安装路径
                or bool_owner_relative  # owner 仓库相对路径
            )
            else "manage_docs.py resume-check"  # 外部路径的稳定短入口
        )  # 面向调用方的恢复命令显示文本

        # 合并生命周期时所有项目都保留 handoff 读取边界。
        str_replacement = (
            f"- Before work: read `docs/handoff/HANDOFF.md`; {str_resume_display}; "  # 生命周期读取入口
            "Start with `start-session`; write `handoff` at completion."  # 生命周期完成动作
        )  # owner 与外部项目共享完整生命周期入口

        # 告知调用方该行已完成合并。
        return True, str_replacement, True, bool_memory_added

    # 文档入口已合并后丢弃重复的开始与完成说明。
    if bool_docs_added and str_line.startswith(
        ("- Start work", "- Every completed", "- Start with `start-session`")
    ):

        # None 表示该重复行不写入最终规则。
        return True, None, bool_docs_added, bool_memory_added

    # memory 根规则改写为包含读取、门禁、bootstrap 和检索的单一入口。
    if str_line.startswith("- Root: `docs/memory`"):

        # 精炼文本保留权威存储与四个必要动作。
        str_replacement = (
            "- **Memory:** docs/memory/MEMORY.md; memory-gate; memory-bootstrap-sessions/memory-read"  # memory 入口文本
        )  # memory 合并入口替换文本

        # 更新 memory 状态以过滤后续重复细则。
        return True, str_replacement, bool_docs_added, True

    # memory 入口已写入后删除其余逐条展开的命令说明。
    if bool_memory_added and str_line.startswith(
        ("- Read ", "- Gate with", "- Historical", "- Query with", "- Sensitivity:")
    ):

        # 后续细则由合并入口和权威文档共同承载。
        return True, None, bool_docs_added, bool_memory_added

    # 未命中生命周期规则时交给普通政策压缩器。
    return False, None, bool_docs_added, bool_memory_added

# 运行环境政策单独处理 worktree、知识图谱、目录和私有设置边界。
def compact_runtime_policy_gate_line(str_line: str) -> tuple[bool, str | None]:
    """压缩单条运行环境根级政策。

    参数:
        str_line: 当前待判断的根级规则行。

    返回:
        是否已处理以及可选的精炼替换文本。
    """

    # 工作区边界保留验收短语，并移除不改变授权范围的重复连接语。
    if str_line.startswith("- **Workspace boundary:**"):

        # 固定替换保留 verifier 要求的全部授权短语和单次确认边界。
        str_replacement = (  # 工作区边界紧凑合同
            "- **Workspace boundary:** current work folder; verified remote-server work folder. Changes inside either "
            "work folder require no additional confirmation; remote changes remain allowed only when the configured "
            "task route matches that folder. Official codebase-memory start, index refresh, rebuild, or recovery for "
            "the project bound to either work folder, including its configured runtime cache and root persistence "
            "artifact, also requires no additional confirmation. External reads beyond those boundaries must be "
            "necessary and "
            "side-effect free. Every other external write is prohibited by default; only after the user proactively "
            "and explicitly requests the exact action. Disclose exact normalized target, action, scope, risks, "
            "alternatives, and recovery limits; obtain exactly one explicit user confirmation. "
            "Any target or scope change invalidates that confirmation. installed skill always requires exactly one "
            "explicit user confirmation."
        )  # 工作区边界的等价紧凑合同

        # 当前行由保留全部验证短语的紧凑合同替代。
        return True, str_replacement

    # 远程工作区合同保留完整可验证句子，避免压缩后丢失安全语义。
    if str_line.startswith("- **Remote workspace management:**"):

        # 保留完整正文，供渲染门禁和人工审计稳定识别。
        str_replacement = (
            "- **Remote workspace management:** Remote workspace management is state-aware "
            "and fail-closed."
        )  # 远程工作区完整状态合同

        # 当前远程管理规则由可验证的完整状态合同替代。
        return True, str_replacement

    # worktree 规则保留全部禁止入口和分支替代方案。
    if str_line.startswith("- Do not create or use additional Git worktrees"):

        # 单行规则覆盖命令、目录名和允许的隔离方式。
        str_replacement = (  # worktree 紧凑合同
            "- Do not create or use additional Git worktrees: forbid `git worktree add`, "
            "`git config core.worktree`, .worktrees, worktrees, .git-worktrees, "
            "git-worktrees; use local branches for isolation."
        )  # 额外 worktree 硬阻断规则

        # 当前行由完整但紧凑的 worktree 规则替代。
        return True, str_replacement

    # 知识图谱启用规则保留写入门禁和调试工具顺序。
    if str_line.startswith("- **Codebase memory MCP:** enabled"):

        # 精炼文本仍要求持久化 full 索引和 live/disk 计数一致。
        str_replacement = (
            "- **Codebase memory MCP:** enabled; full; debug "
            "`get_architecture`/search_graph/trace_path/`detect_changes`; report graph failure before fallback"
        )  # 知识图谱写入与调试停止线

        # 当前行由紧凑知识图谱规则替代。
        return True, str_replacement

    # 远程部署规则保留源码与运行时产物的安全边界。
    if str_line.startswith("- **Remote deployment:**"):

        # 根文件保留旧版部署禁同步短语，详细载荷仍由远程计划承载。
        str_replacement = (
            "- **Remote deployment:** do not sync local skill-development content to servers"  # 禁止部署本地开发源码
        )  # 远程开发部署紧凑合同

        # 当前部署规则由紧凑安全文本替代。
        return True, str_replacement

    # 远程结构规则保留可检索的旧标题，同时把细节交给规划文件。
    if str_line.startswith("- **Remote structure:**"):

        # 具体部署、运行时和归档细节统一放在 planned_structure 中。
        str_replacement = "- **Remote structure:** planned_structure"  # 远程目录规划入口

        # 当前结构规则由紧凑入口替代。
        return True, str_replacement

    # 目录规则在外部工作区保留已安装运行时的完整路径。
    if str_line.startswith("- **Directory changes:**"):

        # owner repo 可使用短命令名，外部工作区必须保留安装路径。
        if "<codex-home>" in str_line:

            # 外部工作区继续引用已安装技能下的目录审查命令。
            str_replacement = str_line  # 外部工作区目录审查规则

        # owner repo 不需要重复已安装技能的绝对路径。
        else:

            # owner repo 保留一次短入口，避免丢失控制平面审查边界。
            str_replacement = "- **Directory changes:** manage_dirs.py review"  # owner repo 目录审查规则

        # 当前目录规则由位置感知文本替代。
        return True, str_replacement

    # 私有设置规则只保留本地、远程和禁止部署三类路径。
    if str_line.startswith("- **Workspace settings:**"):

        # 精炼文本仍明确禁止部署任何 local 配置。
        str_replacement = (
            "- **Workspace settings:** `.settings/project.local.json`/`.settings/project.remote.json`; "
            "no deploy `.settings/*.local.json`/server_list.local.json"
        )  # 工作区设置、远程部署与结构入口

        # 当前行由紧凑设置边界替代。
        return True, str_replacement

    # 主服务器检查失败时仍保留按路由顺序尝试备用服务器的动作。
    if str_line.startswith("- If the matched primary remote server fails"):

        # 精炼文本保留两个检查命令和备用服务器路由顺序。
        str_replacement = (
            "- Primary `check`/`workspace-check` failure: automatically try registered fallback servers in route order."  # 主备服务器故障切换合同
        )

        # 当前主服务器失败规则由完整动作摘要替代。
        return True, str_replacement

    # 任务映射变化仍必须先更新 profile，禁止绕过路由表。
    if str_line.startswith("- If the user wants a different task-to-server mapping"):

        # 精炼文本保留 profile 更新入口和路由表硬阻断。
        str_replacement = (
            "- Different task-server mapping: update profile via agents-md-generator; never bypass route table."  # 任务到服务器映射合同
        )

        # 当前映射规则由最小变更边界替代。
        return True, str_replacement

    # 未命中运行环境规则时由普通政策压缩器继续判断。
    return False, None

# 普通政策压缩器处理不依赖跨行状态的根级规则。
def compact_policy_gate_line(str_line: str) -> tuple[bool, str | None]:
    """压缩单条无状态根级政策。

    参数:
        str_line: 当前待判断的根级规则行。

    返回:
        是否已处理以及可选的精炼替换文本。
    """

    # 验证清单只保留来源指针和必需门禁类别。
    if str_line.startswith("- Validation gates:"):

        # 精炼文本避免在根文件重复整条命令手册。
        str_replacement = (
            "- Validation gates: `quick_validate`, tests, audit, AGENTS/docs `verify`, evaluation."  # 验证门禁入口
        )  # 最终验证清单替换文本

        # 当前行由精炼验证规则替代。
        return True, str_replacement

    # 高风险前向测试压缩为需要覆盖的功能类别。
    if str_line.startswith("- Forward testing:"):

        # 类别列表保留触发范围但不复制实现细节。
        str_replacement = (
            "- Forward testing: compression; install, release"  # 前向测试类别摘要
        )  # 前向测试摘要替换文本

        # 当前行由精炼前向测试规则替代。
        return True, str_replacement

    # 未配置书籍规则时删除两个无决策价值的占位行。
    if str_line in ("- Primary rule set: none.", "- Mode: none."):

        # None 表示占位行不进入根级规则。
        return True, None

    # 运行环境规则由专用压缩器处理，降低单函数分支复杂度。
    tuple_runtime_result = compact_runtime_policy_gate_line(str_line)  # 运行环境政策压缩结果

    # 运行环境规则命中后直接返回其替换合同。
    if tuple_runtime_result[0]:

        # 专用压缩器已经给出处理标记和可选替换文本。
        return tuple_runtime_result

    # 发布来源规则只保留三个权威位置。
    if str_line.startswith("- Release details live"):

        # 根文件指向 profile、git 文档和脚本指南。
        str_replacement = (
            "- Release policy lives in `.agents/agents-control.json`, `docs/git_manager/`, and "
            "skills/agents-md-generator/references/script-guide.md"
        )  # 发布政策权威入口

        # 当前行由紧凑发布来源指针替代。
        return True, str_replacement

    # profile 提供的主源码根必须原样保留，只压缩其外围措辞。
    if str_line.startswith("- **Project root:**"):

        # 短语替换不会把外部工程目录误写成 owner 仓库路径。
        str_old_boundary = "unless the directory contract is updated."  # 匹配原目录合同边界。

        # 新短语保留目录合同变更这一必要条件。
        str_new_boundary = "unless its directory contract changes."  # 定义压缩后的变更条件。

        # 首次替换只调整动词，不接触反引号内的动态目录根。
        str_replacement = str_line.replace("keep feature work inside", "feature work stays in")  # 保留 profile 路径。

        # 第二次替换缩短目录合同边界的外围措辞。
        str_replacement = str_replacement.replace(str_old_boundary, str_new_boundary)  # 保留合同条件。

        # 根索引保留动态源码根，但省略已在目录合同中定义的条件句。
        str_root = str_line.split("`")[1] if "`" in str_line else "skills/agents-md-generator/"  # 保留的源码根

        # 用保留的源码根构造位置稳定的紧凑规则。
        str_replacement = f"- **Project root:** `{str_root}`"  # 主源码根紧凑规则

        # 当前行由紧凑主源码根规则替代。
        return True, str_replacement

    # 阻断审查只需保留默认停止、强制确认和风险记录三个动作。
    if str_line.startswith("- **Blocked directory review:**"):

        # 精炼文本不改变用户强制确认或 handoff 风险留痕要求。
        str_replacement = None  # 目录审查命令保留在目录合同与 handoff 文档中

        # 当前行由紧凑阻断审查规则替代。
        return True, str_replacement

    # 历史包不可变规则同时承载安装源与 push 停止线。
    if str_line.startswith("- Different-version release directories"):

        # 合并文本保留版本目录、zip、receipt、source install 和 push 边界。
        str_replacement = (
            "- Different-version release directories and matching zip files are immutable history; "
            "validated install only from dist/<name>-vX.Y.Z/ with RELEASE_RECEIPT.json; "
            "source directory installs are forbidden; push only on explicit request"
        )  # 发布历史和安装授权边界

        # 当前行由合并后的发布停止线替代。
        return True, str_replacement

    # 已被历史包规则吸收的安装和 push 单行不再重复输出。
    if str_line.startswith(("- Install only from", "- Do not push to a remote")):

        # None 表示删除已被上层合并的重复规则。
        return True, None

    # 未启用书籍规则时只保留参考而非复制全文。
    if str_line.startswith("- Do not paste full book rules"):

        # 精炼文本保留 reference-only 的硬边界。
        return True, "- Keep full book rules reference-only"

    # 未命中无状态压缩规则时由调用方保留原文。
    return False, None

# 根级门禁压缩器合并同一子系统的重复入口。
def compact_task_gate_text(str_rules: str) -> str:
    """压缩根级门禁，同时保留触发、停止线和权威入口。

    参数:
        str_rules: 已按优先级渲染的完整根级规则文本。

    返回:
        去除重复细则后的根级门禁文本。
    """

    # 结果列表保持输入顺序并承载精炼后的规则。
    list_result: list[str] = []  # 精炼后的根级规则

    # 文档状态用于过滤已经合并的生命周期细则。
    bool_docs_added = False  # 文档生命周期合并标记

    # memory 状态用于过滤已经合并的检索细则。
    bool_memory_added = False  # 记忆入口合并标记

    # 每行先经过有状态生命周期压缩，再经过无状态政策压缩。
    for str_line in str_rules.splitlines():

        # 生命周期压缩返回处理状态、替换文本和更新后的跨行标记。
        tuple_lifecycle_result = compact_lifecycle_gate_line(  # 生命周期压缩结果
            str_line,  # 当前根级规则行
            bool_docs_added,  # 当前文档合并状态
            bool_memory_added,  # 当前 memory 合并状态
        )

        # 处理标记决定是否跳过后续无状态压缩。
        bool_handled = tuple_lifecycle_result[0]  # 生命周期规则处理标记

        # 替换文本为 None 时表示当前规则已经被合并吸收。
        str_replacement = tuple_lifecycle_result[1]  # 生命周期规则替换文本

        # 文档状态跨行保留，避免重复输出开始与完成入口。
        bool_docs_added = tuple_lifecycle_result[2]  # 更新后的文档合并状态

        # memory 状态跨行保留，避免重复输出检索入口。
        bool_memory_added = tuple_lifecycle_result[3]  # 更新后的 memory 合并状态

        # 已处理规则只在存在替换文本时写入结果。
        if bool_handled:

            # None 代表当前行已被先前合并入口吸收。
            if str_replacement is not None:

                # 多行替换文本按逻辑行重新加入结果集合。
                list_result.extend(str_replacement.splitlines())

            # 当前行已完成处理，不再进入无状态政策判断。
            continue

        # 无状态政策压缩只返回处理状态和可选替换文本。
        tuple_policy_result = compact_policy_gate_line(str_line)  # 单行政策压缩结果

        # 处理标记决定当前规则是否已经完成政策压缩。
        bool_handled = tuple_policy_result[0]  # 单行政策处理标记

        # 替换文本为 None 时表示当前政策规则不再单独输出。
        str_replacement = tuple_policy_result[1]  # 单行政策替换文本

        # 已处理政策同样只在有替换文本时写入。
        if bool_handled:

            # 被上层合并的重复行保持不输出。
            if str_replacement is not None:

                # 政策替换均为单行，但 splitlines 保持接口一致。
                list_result.extend(str_replacement.splitlines())

            # 当前行处理完成后继续下一条输入规则。
            continue

        # 未命中任何压缩规则时原样保留输入行。
        list_result.append(str_line)

    # 以标准换行重新组装稳定的根级门禁文本。
    return "\n".join(list_result)

