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
    if str_line.startswith(("- Before new work", "- Before work")):

        # 已包含稳定 handoff 前缀的输入直接保留，避免二次压缩丢失动作顺序。
        if "Start with `start-session`; write `handoff` at completion" in str_line:

            # 当前行已经满足恢复与交接硬短语，只更新文档合并状态。
            return True, str_line, True, bool_memory_added

        # 提取并保留源合同中的完整命令路径，再补充启动与完成交接动作。
        str_original_contract = str_line.split(": ", 1)[1] if ": " in str_line else str_line  # 原始文档合同正文

        # 去除源合同句末标点，避免拼接交接动作时形成重复标点。
        str_original_contract = str_original_contract.rstrip(".")  # 去除源合同句末标点

        # owner repo 根索引使用短入口，外部项目则保留安装版完整路径。
        if "python skills/agents-md-generator/" in str_original_contract:

            # 只压缩本仓库路径，不改变外部工作区的可执行命令合同。
            tuple_owner_path_replacements = (
                ("python skills/agents-md-generator/scripts/python/docs/manage_docs.py", "manage_docs.py"),  # 保持 docs 交接入口简洁
                ("python skills/agents-md-generator/scripts/python/dirs/manage_dirs.py", "manage_dirs.py"),  # 保持 dirs 审查入口简洁
            )  # owner repo 命令短入口映射

            # 逐项替换 owner repo 的长路径，保留外部项目路径原文。
            for str_long_path, str_short_path in tuple_owner_path_replacements:

                # 当前替换只影响当前仓库的命令文本。
                str_original_contract = str_original_contract.replace(str_long_path, str_short_path)  # 当前 owner 路径替换

            # owner repo 保留仓库顶层可复现的文档治理命令。
            str_original_contract = (
                "read `docs/handoff/HANDOFF.md`; run `python skills/agents-md-generator/scripts/python/docs/"
                "manage_docs.py resume-check <project>`; "
                "repair `resume-repair`"
            )  # owner repo 生命周期短合同

        # 外部项目复用安装态 resume-check 路径，避免重复展开同一安装根。
        if "<codex-home>" in str_original_contract:

            # 只保留外部运行时必须可执行的检查路径和恢复动作。
            str_original_contract = (
                "read `docs/handoff/HANDOFF.md`; run `python <codex-home>/skills/agents-md-generator/"
                "scripts/python/docs/manage_docs.py resume-check <project>`; repair `resume-repair`"
            )  # 外部项目生命周期短合同

        # 组合启动、恢复、命令路径和完成交接的稳定根规则。
        str_replacement = (
            "- Before work: Start with `start-session`; write `handoff` at completion; "
            f"{str_original_contract}."
        )  # 生命周期入口替换文本

        # 返回已保留源路径的生命周期合同并更新文档合并状态。
        return (
            True,
            str_replacement,
            True,
            bool_memory_added,
        )

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
            "- **Memory:** docs/memory/MEMORY.md; memory-gate; memory-bootstrap-sessions/memory-read; "
            "bootstrap exact-cwd sessions"  # memory 入口文本
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

# 无动态状态的运行环境政策使用前缀映射，避免主压缩器堆积分支。
def _compact_static_runtime_policy_line(str_line: str) -> tuple[bool, str | None]:
    """
    压缩不依赖当前行动态值的运行环境政策。

    参数:
        str_line: 当前待判断的根级规则行。
    返回:
        命中静态政策时返回 True 和替换文本，否则返回 False 和 None。
    """

    # 逐项按前缀选择替换正文或删除标记，命中后结束当前行处理。
    for str_prefix, str_replacement in (
        (
            "- **Workspace boundary:**",  # 工作区授权合同前缀
            None,  # 完整 workspace 合同由根级 Contract reference notes 承载
        ),
        (
            "- **gardener_worker:**",  # gardener 受管只读前缀
            (
                "- **gardener_worker:** canonical read-only; `fork_turns=none`; tracked `.py`/`.md`; list/read "
                "tests/**; never touches dist/github/root docs/.agents/.git/.codebase-memory/ref; strict JSON; "
                "zero-call needs graph+tester; deletion gate."
            ),
        ),
        (
            "- **reviewer_worker:**",  # reviewer 阶段门禁前缀
            (
                "- **reviewer_worker:** canonical; read-only; never tests/**; INITIAL/10m/CORRECTION/FINAL; PERIODIC."
            ),  # reviewer 短合同
        ),
        (
            "- **Unique TESTER:**",  # tester 唯一所有权前缀
            None,  # TESTER provenance 细则移至根引用区
        ),
        (
            "- **远程上传边界：**",  # manifest-only 传输前缀
            (
                "- **远程上传边界：** manifest-only；禁整体上传/同步/镜像/递归打包；禁传 "
                "`.git/`/`git/`/`github/`/`dist/`/`ref/`/archives；仅传清单/窄目录；制品单列；"
                "禁改名/复制/重打包/绕过。"
            ),
        ),
            (
                "- Do not create or use additional Git worktrees",  # 隔离入口阻断前缀
                (
                "- Do not create or use additional Git worktrees: forbid `git worktree add`, "
                "`git config core.worktree`; reserve `.worktrees`/`.git-worktrees`; use local branches for isolation."
            ),
        ),
        (
            "- **Codebase memory MCP:** enabled",  # 图谱门禁前缀
            "- **Codebase memory MCP:** enabled/full; use `get_architecture`/`search_graph`/`trace_path`/"
            "`detect_changes`; "
            "report graph failure before fallback",
        ),
        (
            "- **Remote deployment:**",  # 远程部署规则前缀
            "- **Remote deployment:** do not sync local skill-development content to servers; runtime artifacts only.",  # 远程运行时边界
        ),  # 运行时上传边界由 manifest-only 合同承载
        (
            "- **Remote structure:**",  # 远程结构合同前缀
            "- **Remote structure:** lifecycle details use the remote workspace management entry; root AGENTS.md "
            "is only the entry index.",  # 远程结构摘要
        ),  # 远程结构规划前缀
        ("- Remote server usage:", None),  # 路由源与 workspace 状态已承载远程启用事实
            (
                "- **Workspace settings:**",  # 本地设置隔离前缀
            (
                "- **Workspace settings:** `.settings/project.local.json`/`.settings/project.remote.json`;"
                "`.settings/*.local.json` stays local; forbid remote `server_list.local.json`."
            ),
        ),
        (
            "- If the matched primary remote server fails",  # 主服务器失败规则前缀
            "- Primary `check`/`workspace-check` failure: automatically try registered fallback "
            "servers in route order.",
        ),  # 备用服务器动作前缀
        (
            "- If the user wants a different task-to-server mapping",  # 任务映射规则前缀
            "- If the user wants a different task-to-server mapping, update the profile; never bypass the route table.",  # 路由映射更新入口
        ),  # 任务路由更新前缀
    ):  # 静态合同顺序与原始政策发现顺序一致

        # 命中静态规则后直接返回其完整替换文本。
        if str_line.startswith(str_prefix):

            # True 区分“已处理但删除正文”的 None 替换。
            return True, str_replacement

    # 未命中静态规则时交给动态状态压缩器继续判断。
    return False, None

# 运行环境政策单独处理 worktree、知识图谱、目录和私有设置边界。
def compact_runtime_policy_gate_line(str_line: str) -> tuple[bool, str | None]:
    """压缩单条运行环境根级政策。

    参数:
        str_line: 当前待判断的根级规则行。

    返回:
        是否已处理以及可选的精炼替换文本。
    """

    # 静态合同先由前缀映射处理，主函数只保留动态状态分支。
    tuple_static_result = _compact_static_runtime_policy_line(str_line)  # 静态运行环境合同结果

    # 静态规则无论保留还是删除正文，都应在此结束当前行处理。
    if tuple_static_result[0]:

        # 返回静态合同的处理标记和替换文本。
        return tuple_static_result

    # 远程工作区合同压缩为一行，并保留路由、验证工作区和动态状态事实。
    if str_line.startswith(("- **Remote workspace management:**", "- Remote workspace:")):

        # 保留动态状态，避免压缩器覆盖画像事实。
        str_state_marker = "remote workspace state:"  # 状态字段的稳定解析标记

        # 状态标记存在时读取画像中的动态值。
        if str_state_marker in str_line:

            # 状态值取自当前规则正文，不能使用固定文本覆盖画像。
            str_state = str_line.split(str_state_marker, 1)[1].strip()  # 读取画像中的远程状态

        # 状态标记缺失时仅兼容旧版压缩输入。
        else:

            # 旧版输入没有动态状态，使用受控默认值。
            str_state = "enabled"  # 旧输入缺少状态时的保守默认值

        # 规则正文保留 fail-closed、精确路由、验证工作区、结构入口和动态状态。
        str_replacement = (
            "- **Remote workspace management:** state-aware/fail-closed; resolve exact task route and verified "
            "workspace; unmatched/unverified stop. Keep lifecycle details in "
            "`docs/dir_manager/planned_structure.json`; "
            f"remote workspace state: {str_state}"
        )  # 远程工作区完整状态合同

        # 当前远程管理规则由可验证的完整状态合同替代。
        return True, str_replacement

    # 目录规则在外部工作区保留已安装运行时的完整路径。
    if str_line.startswith("- **Directory changes:**"):

        # owner repo 可使用短命令名，外部工作区必须保留安装路径。
        if "<codex-home>" in str_line:

            # 外部工作区保留安装态命令，但删除非阻断解释文本。
            str_replacement = (
                "- **Directory changes:** run `python <codex-home>/skills/agents-md-generator/"
                "scripts/python/dirs/manage_dirs.py review <project> --input change.json`."
            )  # 外部工作区目录审查规则

        # owner repo 不需要重复已安装技能的绝对路径。
        else:

            # owner repo 保留一次短入口，避免丢失控制平面审查边界。
            str_replacement = "- **Directory changes:** manage_dirs.py review"  # owner repo 目录审查规则

        # 当前目录规则由位置感知文本替代。
        return True, str_replacement

    # 未命中运行环境规则时由普通政策压缩器继续判断。
    return False, None

# 远程路由只投影执行时解析、回退和停止边界。
def _compact_remote_route_line(str_line: str) -> tuple[bool, str | None]:
    """压缩远程路由入口，保留根文件必需的停止短语。

    参数：str_line 为远程路由原文。
    返回：命中时返回替换结果，否则返回未处理标记。
    """

    # 路由映射集中保存，避免普通政策函数继续增加分支。
    tuple_route_replacements = (  # 远程路由前缀到根级短合同的映射
        (
            "- Resolve primary and fallback servers",  # 主备服务器解析前缀
            "- Resolve primary/fallback servers from the route source at execution time; no "
            "registry/runner/absolute remote paths in root AGENTS.md.",
        ),
        (
            "- If the matched primary remote server fails",  # 主服务器失败前缀
            "- Primary `check`/`workspace-check` failure: automatically try registered fallback "
            "servers in route order.",
        ),
        (
            "- If no registered task route matches",  # 未匹配任务前缀
            "- If no registered task route matches, stop and update the current work-folder "
            "AGENTS.md/profile before continuing.",
        ),
        (
            "- Task-server mapping:",  # 任务映射前缀
            "- Different task-server mapping: update profile; never bypass route table.",  # 任务映射短合同
        ),
        (
            "- Route source:",  # 路由来源前缀
            "- Route source: `.agents/agents-control.json` field `remote_server_contract`.",  # 路由来源短合同
        ),
    )

    # 逐项匹配保持来源顺序，未命中时让调用方保留原文。
    for str_prefix, str_replacement in tuple_route_replacements:

        # 当前路由前缀命中后返回稳定短合同。
        if str_line.startswith(str_prefix):

            # None 表示该行由其他合同承载或不需要单独输出。
            return True, str_replacement

    # 非路由行继续交给普通政策压缩器。
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

        # 根索引保留仓库顶层测试命令和其余验证类别，具体实现由 SKILL.md 承载。
        return True, (
            "- Validation gates: `quick_validate`; tests, audit: `python -m unittest discover -s tests -t . -v`; "
            "AGENTS/docs `verify`; evaluation."
        )

    # 输出策略保留 Kind 来源和 Python 过程性日志的执行语义。
    if str_line.startswith("- 配置来源："):

        # 具体命令留在 registry，根索引只保留不可丢失的政策锚点。
        return True, (
            "- Script Output Policy: `Kind` 列表只从 JSON 读取；Python 过程性 INFO 默认打印；"
            "`--quiet` 关闭；WARNING 和 ERR 继续可见；机器可读输出不套前缀。"
        )

    # 高风险前向测试压缩为需要覆盖的功能类别。
    if str_line.startswith("- Forward testing:"):

        # 根索引保留前向测试的三类执行门禁。
        return True, "- Forward testing: compression/install/release."

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

        # 根文件同时指向发布政策并保留版本制品、安装和 push 停止线。
        str_replacement = (
            "- Release policy lives in `.agents/agents-control.json`, `docs/git_manager/`, and "
            "`skills/agents-md-generator/references/script-guide.md`; Different-version release directories and "
            "matching zip files are immutable history; install `dist/<name>-vX.Y.Z/` only with "
            "`RELEASE_RECEIPT.json`; source directory installs are forbidden; push requested."
        )  # 发布政策权威入口

        # 当前行由紧凑发布来源指针替代。
        return True, str_replacement

    # profile 提供的主源码根已由项目画像和目录合同承载，根门禁不重复复制路径。
    if str_line.startswith("- **Project root:**"):

        # 只有 owner repo 使用固定短路径，其他项目必须保留画像中的动态根。
        if "skills/agents-md-generator/" in str_line:

            # owner repo 的详细 feature 规则继续由本地治理配置承载。
            return True, "- **Project root:** primary project root `skills/agents-md-generator/`; features stay inside."

        # demo 或 engineering fixture 的主根必须保持调用方画像事实。
        return True, str_line.replace("keep feature work inside it", "features stay inside")

    # 阻断审查只需保留默认停止、强制确认和风险记录三个动作。
    if str_line.startswith("- **Blocked directory review:**"):

        # 精炼文本不改变用户强制确认或 handoff 风险留痕要求。
        str_replacement = None  # 目录审查命令保留在目录合同与 handoff 文档中

        # 当前行由紧凑阻断审查规则替代。
        return True, str_replacement

    # 历史包不可变规则同时承载安装源与 push 停止线。
    if str_line.startswith("- Different-version release directories"):

        # 发布政策入口已经承载版本制品和安装停止线。
        return True, None

    # 已被历史包规则吸收的安装和 push 单行不再重复输出。
    if str_line.startswith(("- Install only from", "- Do not push to a remote")):

        # None 表示删除已被上层合并的重复规则。
        return True, None

    # 未启用书籍规则时明确保留完整规则仅作参考的边界。
    if str_line.startswith("- Do not paste full book rules"):

        # 保留停止复制全文的机器可检索合同。
        return True, "- Do not paste full book rules into AGENTS.md. Keep full book rules reference-only."

    # 低信息密度的受管入口统一缩短，但不删除其停止条件和权威路径。
    tuple_short_policy_lines = (  # 低信息密度入口的精简映射
        (
            "- Before work:",  # 开工前置合同前缀。
            "- Before work: Start with `start-session`; run "
            "`python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py "
            "resume-check <project>` and "
            "`python <codex-home>/skills/agents-md-generator/scripts/python/dirs/manage_dirs.py review "
            "<project> --input change.json`; repair interruptions with `resume-repair`; write `handoff` "
            "at completion.",  # 生命周期入口保留恢复检查与会话交接顺序
        ),
        (
            "- **Task authorization:**",  # 单次授权收据前缀。
            "- **Task authorization:** one receipt covers skill/AGENTS.md/CLI; "
            "target/scope/risk changes invalidate.",  # 授权变化边界。
        ),
    )

    # 逐项匹配时保持动态目录和命令内容只出现在替换正文中。
    for str_prefix, str_replacement in tuple_short_policy_lines:

        # 当前行命中后返回固定短合同，未命中则继续保留原文。
        if str_line.startswith(str_prefix):

            # 替换结果保留当前规则的动作、停止线和风险边界。
            return True, str_replacement

    # 路由来源由独立 helper 压缩，避免与普通政策分支耦合。
    tuple_route_result = _compact_remote_route_line(str_line)  # 远程路由压缩结果

    # 命中路由合同时直接返回其替换文本。
    if tuple_route_result[0]:

        # helper 已保留运行时解析、回退和停止短语。
        return tuple_route_result

    # 未命中无状态压缩规则时由调用方保留原文。
    return False, None

# 合并同一远程路由的来源、回退和停止规则，避免根文件重复展开控制面事实。
def compact_remote_route_lines(list_lines: list[str]) -> list[str]:
    """把远程路由的多行事实压成一个可检索入口。

    参数：list_lines 为已完成普通政策压缩的根规则行。
    返回：保留同等执行语义的根规则行。
    """

    # 路由来源是稳定锚点，其余路由行可安全并入同一条规则。
    str_anchor_prefix = "- Route source:"  # 远程路由来源行前缀

    # 需要并入来源行的远程路由规则前缀集合。
    tuple_route_prefixes = (  # 远程路由规则前缀集合
        str_anchor_prefix,  # 来源规则前缀
        "- Resolve primary/fallback servers",  # 主备解析前缀
        "- Resolve primary and fallback servers",  # 兼容旧解析前缀
        "- Primary `check`/`workspace-check` failure:",  # 主备失败前缀
        "- If no registered task route matches",  # 路由缺失前缀
        "- If the user wants a different task-to-server mapping",  # 映射变更前缀
        "- Different task-server mapping:",  # 简短映射前缀
    )

    # 没有完整路由事实时保持原列表，兼容非远程项目。
    if not any(str_line.startswith(str_anchor_prefix) for str_line in list_lines):

        # 非远程项目没有可压缩的路由事实。
        return list_lines

    # 合并行保留来源、解析时机、回退动作和不匹配停止线。
    str_route_summary = (
        "- Route source: `.agents/agents-control.json` field `remote_server_contract`. "
        "Resolve primary and fallback servers from the route source at execution time; no registry/runner/absolute "
        "remote paths in root AGENTS.md. Primary `check`/`workspace-check` failure: automatically try registered "
        "fallback servers in route order. If no registered task route matches the requested task, stop and update the "
        "current work folder AGENTS.md/profile before continuing. Mapping: update profile; no bypass."
    )

    # 只在首个来源位置写入汇总，后续路由行由同一合同吸收。
    list_compact: list[str] = []  # 合并后的根规则行

    # 仅允许来源锚点插入一次汇总规则。
    bool_inserted = False  # 是否已写入路由汇总

    # 逐行移除已并入来源锚点的重复路由事实。
    for str_line in list_lines:

        # 首次遇到来源行时写入完整远程路由合同。
        if str_line.startswith(str_anchor_prefix) and not bool_inserted:

            # 来源行承载所有路由解析、回退和停止语义。
            list_compact.append(str_route_summary)

            # 标记来源汇总已经写入。
            bool_inserted = True  # 防止重复写入路由汇总

            # 当前来源行已被汇总规则替换。
            continue

        # 后续路由行已经由来源汇总承载。
        if str_line.startswith(tuple_route_prefixes):

            # 不再重复输出同一控制面事实。
            continue

        # 非路由规则保持原有顺序。
        list_compact.append(str_line)

    # 返回去除重复路由规则后的行集合。
    return list_compact

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

    # 远程路由事实只保留一个可检索入口，避免控制面重复占用根预算。
    list_result = compact_remote_route_lines(list_result)  # 合并远程路由重复事实

    # 以标准换行重新组装稳定的根级门禁文本。
    return "\n".join(list_result)

