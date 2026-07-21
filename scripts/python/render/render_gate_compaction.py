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

        # 返回两行文本，避免后续生命周期规则重复展开命令。
        str_replacement = (
            f"{str_line}\n"
            "- Start with `start-session`; write `handoff` at completion."
        )  # 合并后的文档生命周期入口

        # 告知调用方该行已完成合并。
        return True, str_replacement, True, bool_memory_added

    # 文档入口已合并后丢弃重复的开始与完成说明。
    if bool_docs_added and str_line.startswith(("- Start work", "- Every completed")):

        # None 表示该重复行不写入最终规则。
        return True, None, bool_docs_added, bool_memory_added

    # memory 根规则改写为包含读取、门禁、bootstrap 和检索的单一入口。
    if str_line.startswith("- Root: `docs/memory`"):

        # 精炼文本保留权威存储与四个必要动作。
        str_replacement = (
            "- **Memory:** `docs/memory` / `docs/memory/MEMORY.md` uses `sqlite-plus-jsonl`; "
            "read current context, pass `memory-gate`, run `memory-bootstrap-sessions` for "
            "exact-cwd history, and retrieve with `memory-read`."
        )  # 合并后的 memory 治理入口

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

    # 工作区边界已经是验收合同文本，压缩器必须原样保留全部保护层。
    if str_line.startswith("- **Workspace boundary:**"):

        # 原样返回避免允许根、只读限制、披露或双确认语义被通用压缩削弱。
        return True, str_line

    # worktree 规则保留全部禁止入口和分支替代方案。
    if str_line.startswith("- Do not create or use additional Git worktrees"):

        # 单行规则覆盖命令、目录名和允许的隔离方式。
        str_replacement = (
            "- Do not create or use additional Git worktrees: forbid `git worktree add`, "
            "`git config core.worktree`, `.worktrees`, `worktrees`, `.git-worktrees`, and "
            "`git-worktrees`; use local branches for isolation."
        )  # 额外 worktree 硬阻断规则

        # 当前行由完整但紧凑的 worktree 规则替代。
        return True, str_replacement

    # 知识图谱启用规则保留写入门禁和调试工具顺序。
    if str_line.startswith("- **Codebase memory MCP:** enabled"):

        # 精炼文本仍要求持久化 full 索引和 live/disk 计数一致。
        str_replacement = (
            "- **Codebase memory MCP:** enabled; keep root artifacts ignored/untracked; managed "
            "writes require a ready persistent `full` index, architecture, and matching live/disk "
            "counts; debug with `get_architecture`, `search_graph`, `trace_path`, and "
            "`detect_changes`, and report graph failure before fallback."
        )  # 知识图谱写入与调试停止线

        # 当前行由紧凑知识图谱规则替代。
        return True, str_replacement

    # 目录规则在外部工作区保留已安装运行时的完整路径。
    if str_line.startswith("- **Directory changes:**"):

        # owner repo 可使用短命令名，外部工作区必须保留安装路径。
        if "<codex-home>" in str_line:

            # 外部工作区继续引用已安装技能下的目录审查命令。
            str_replacement = str_line  # 外部工作区目录审查规则

        # owner repo 不需要重复已安装技能的绝对路径。
        else:

            # owner repo 可把命令缩短为当前技能中的脚本入口。
            str_replacement = (
                "- **Directory changes:** review create/move/delete/rename with "
                "`manage_dirs.py review` before mutation."
            )  # owner repo 目录审查规则

        # 当前目录规则由位置感知文本替代。
        return True, str_replacement

    # 私有设置规则只保留本地、远程和禁止部署三类路径。
    if str_line.startswith("- **Workspace settings:**"):

        # 精炼文本仍明确禁止部署任何 local 配置。
        str_replacement = (
            "- **Workspace settings:** local `.settings/project.local.json`; remote "
            "`.settings/project.remote.json`; never deploy `.settings/*.local.json` such as "
            "`.settings/server_list.local.json`."
        )  # 工作区设置的本地与远程边界

        # 当前行由紧凑设置边界替代。
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
            "- Validation gates: follow `.agents/agents-control.json`; include `quick_validate`, "
            "tests, audit, AGENTS/docs `verify`, evaluation, and applicable release install-skip."
        )  # 根级验证门禁索引

        # 当前行由精炼验证规则替代。
        return True, str_replacement

    # 高风险前向测试压缩为需要覆盖的功能类别。
    if str_line.startswith("- Forward testing:"):

        # 类别列表保留触发范围但不复制实现细节。
        str_replacement = (
            "- Forward testing: high-risk compression, docs/recovery, install, directory, "
            "release, compatibility, and verification changes."
        )  # 高风险前向测试类别

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
            "`skills/agents-md-generator/references/script-guide.md`; root keeps blocking rules only."
        )  # 发布政策权威入口

        # 当前行由紧凑发布来源指针替代。
        return True, str_replacement

    # 历史包不可变规则同时承载安装源与 push 停止线。
    if str_line.startswith("- Different-version release directories"):

        # 合并文本保留版本目录、zip、receipt、source install 和 push 边界。
        str_replacement = (
            "- Different-version release directories and matching zip files are immutable history; "
            "install only validated `dist/<name>-vX.Y.Z/` with `RELEASE_RECEIPT.json`; source "
            "directory installs are forbidden; push only on explicit request."
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
        return True, "- Keep full book rules reference-only."

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
