"""把项目治理配置转换为 AGENTS.md 中可执行的精简规则。"""

# 根级门禁压缩已拆分到同目录模块，避免合同聚合分片超过源码尺寸门禁。
from render_gate_compaction import compact_task_gate_text

# 远程服务器合同只渲染路由入口与失败回退边界。
def remote_server_contract(profile: dict | None) -> str:
    """渲染远程服务器路由合同。

    参数:
        profile: 项目设计配置；为空时不启用远程服务器合同。

    返回:
        适合写入 AGENTS.md 的远程服务器规则文本，未启用时为空字符串。
    """

    # 校验 remote_server_contract 的渲染分支条件。
    if not profile:

        # 返回 remote_server_contract 的 AGENTS 渲染载荷。
        return ""

    # 整理 remote_server_contract 需要的 contract 渲染片段。
    contract = profile.get("remote_server_contract", {})  # AGENTS 受管段落渲染输入值

    # 缺少远程合同配置时保持对应受管段落为空。
    if not contract:

        # 空字符串让上层聚合器自然跳过该合同。
        return ""

    # 显式 enabled 开关决定是否公开远程路由规则。
    if not contract.get("enabled"):

        # 关闭状态不应向 AGENTS.md 泄露未启用配置。
        return ""

    # 返回 compact 入口规则，完整 registry 和 route 表只保留在机器可读 profile。
    return "\n".join([
        "- Remote server usage: enabled.",
        "- Route source: `.agents/agents-control.json` field `remote_server_contract`.",
        "- Resolve primary and fallback servers from the route source at execution time. "
        "Do not copy server registry, functions, runner, or absolute remote paths into "
        "root AGENTS.md.",
        "- If the matched primary remote server fails `check` or `workspace-check`, "
        "automatically try registered fallback servers in route order.",
        "- If no registered task route matches the requested task, stop and update the "
        "current work folder AGENTS.md/profile before continuing.",
        "- If the user wants a different task-to-server mapping, update the profile "
        "through agents-md-generator first; do not bypass the route table ad hoc.",
    ])

# 发布合同聚合分支、安装来源、历史包和推送限制。
def release_contract(profile: dict | None, project: Path) -> str:
    """渲染仓库发布与 Git 管理合同。

    参数:
        profile: 项目设计配置；为空时不输出发布合同。
        project: 用于判断脚本指南是否存在的项目根目录。

    返回:
        适合写入 AGENTS.md 的发布规则文本，缺少配置时为空字符串。
    """

    # 没有项目配置时，上层不应生成推测性的发布规则。
    if not profile:

        # 空文本表示发布合同未配置。
        return ""

    # 分支策略提供受保护分支集合。
    policy = profile.get("git_branch_policy", {})  # 项目 Git 分支策略

    # 缺省保护主分支和发布分支，避免生成宽松合同。
    protected = policy.get("protected_branches", ["master", "release"])  # 受保护分支名称

    # Markdown 代码样式让分支名称在规则文本中保持清晰。
    protected_text = ", ".join(f"`{item}`" for item in protected)  # 渲染后的分支列表

    # 指向当前仓库存在的脚本指南；外部项目只保留安装版指南描述，避免虚构本地路径。
    path_script_guide = (
        project / "skills" / "agents-md-generator" / "references" / "script-guide.md"  # 仓库内指南组成路径
    )  # 仓库内脚本指南候选路径

    # 最终指南文本在源码路径和安装版引用之间选择。
    str_script_guide = (  # 最终脚本指南引用文本
        "skills/agents-md-generator/references/script-guide.md"  # 源码仓库内指南引用
        if path_script_guide.is_file()  # 源码仓库含脚本指南
        else "the installed agents-md-generator script-guide reference"  # 安装版指南引用
    )  # 可在目标项目中解析的指南描述

    # 发布规则按稳定顺序输出，便于受管段落漂移检查。
    return "\n".join([
        f"- Git management: {git_management_text(profile.get('git_management', 'not specified'))}.",
        f"- Branch model: {profile.get('branch_model', 'not specified')}; protected branches: {protected_text}.",
        "- Development branches are allowed only as temporary local work branches.",
        f"- {RELEASE_CORE_WORKTREE_RULE}",
        f"- Release details live in `.agents/agents-control.json`, `docs/git_manager/`, "
        f"and `{str_script_guide}`; root AGENTS.md keeps only blocking rules.",
        "- Install only from a versioned `dist/<name>-vX.Y.Z/` release directory "
        "containing a validated `RELEASE_RECEIPT.json`; source directory installs "
        "are forbidden.",
        "- Different-version release directories and matching zip files are immutable history by default.",
        "- Keep the release commit and current `docs/git_manager/CHANGELOG.md` entry together.",
        "- Do not push to a remote unless the user explicitly asks.",
    ])

# Git 管理枚举在这里转换为面向执行者的完整描述。
def git_management_text(value: str) -> str:
    """把 Git 管理模式转换为可读策略文本。

    参数:
        value: 配置中的 Git 管理模式。

    返回:
        已知模式的规范描述；未知值保持原文本。
    """

    # 保存 mapping 映射，维持 git_management_text 的字段关系。
    dict_mapping = {
        "yes-local-only": (  # 本地提交但默认不推送
            "enabled locally; allow local branches and commits, but do not push "
            "remotely by default"
        ),  # 本地 Git 管理模式
        "no-git-management": (  # 不参与 Git 操作的工作流
            "disabled for this workflow; do not treat git operations as part of the "
            "normal execution path"
        ),  # 禁用 Git 管理模式
        "read-only": (  # 禁止 Git 写入的兼容模式
            "legacy read-only mode; do not execute git writes and limit the workflow "
            "to planning/documentation unless the user overrides"
        ),  # 只读兼容模式
        "remote-allowed": "enabled with remote collaboration allowed when the user explicitly asks",  # 用户授权后允许远程协作
    }

    # 未知模式原样返回，保留前向兼容并避免静默改写配置。
    return dict_mapping.get(str(value), str(value))

# 工程规则合同只保留会改变代理决策的压缩字段。
def engineering_rule_contract(profile: dict | None) -> str:
    """渲染工程规则集选择与压缩策略。

    参数:
        profile: 项目设计配置；为空时输出安全的未配置合同。

    返回:
        工程规则集、模式、作用域和兼容策略文本。
    """

    # 无配置时输出明确的 none 合同，而不是推断工程规则集。
    if not profile:

        # 安全缺省值要求后续添加工程偏好前先征询用户。
        return "\n".join([
            "- Primary rule set: none.",
            "- Mode: none.",
            "- Ask the user before adding any book-derived engineering bias to AGENTS.md.",
            "- Do not paste full book rules into AGENTS.md.",
        ])

    # 工程合同承载规则集、模式、范围和压缩策略。
    contract = profile.get("engineering_rule_contract", {})  # 工程规则合同配置

    # 主规则集缺失时明确渲染 none。
    primary = contract.get("primary", "none")  # 主工程规则集

    # 模式描述规则集如何参与代理决策。
    mode = contract.get("mode", "none")  # 工程规则启用模式

    # 作用域限制工程规则影响的任务范围。
    scope = contract.get("scope", "on-demand")  # 工程规则适用范围

    # 汇总 lines，作为 AGENTS 受管段落拼装顺序。
    list_lines = [
        f"- Primary rule set: {primary}.",  # 当前主工程规则集
        f"- Mode: {mode}.",  # 工程规则运行模式
        f"- Scope: {scope}.",  # 工程规则作用范围
        f"- Compatibility: {contract.get('compatibility_policy', 'one primary active rule set')}.",  # 规则集兼容策略
        f"- Compression: {contract.get('compression_policy', 'keep only decision-changing rules')}.",  # 规则压缩策略
        "- Do not paste full book rules into AGENTS.md; keep full material reference-only.",  # 完整材料引用边界
    ]

    # 可选备注只在配置存在时追加，避免空行噪声。
    notes = contract.get("notes")  # 工程规则补充说明

    # 备注作为最后一条规则，不改变核心字段顺序。
    if notes:

        # 追加 engineering_rule_contract 的 AGENTS 渲染行。
        list_lines.append(f"- Notes: {notes}.")

    # 聚合后的文本直接进入任务专用门禁段落。
    return "\n".join(list_lines)

# Skill 项目需要额外公开触发、资源和验证边界。
def skill_design_contract(profile: dict | None, project: Path) -> str:
    """渲染 Codex Skill 的设计与验证合同。

    参数:
        profile: 项目设计配置；非 Skill 项目不会输出该合同。
        project: 当前项目根目录，保留给路径相关合同扩展使用。

    返回:
        Skill 触发、资源、渐进披露和验证规则文本。
    """

    # 该合同只适用于明确标记为 Skill 的项目。
    if not profile or profile.get("kind") != "skill":

        # 普通项目不渲染 Skill 专属规则。
        return ""

    # Skill 合同提供触发、资源和验证策略。
    contract = profile.get("skill_design_contract", {})  # Skill 设计合同配置

    # patterns 同时兼容既有字符串和结构化列表格式。
    patterns = contract.get("patterns", [])  # Skill 设计模式配置

    # 旧版字符串配置无需再次拼接。
    if isinstance(patterns, str):

        # 字符串形式已经是最终可展示文本。
        patterns_text = patterns  # 兼容旧版模式文本

    # 列表配置清理空元素后转为稳定展示文本。
    else:

        # 列表模式过滤空值后按声明顺序连接。
        patterns_text = ", ".join(  # 设计模式列表文本
            str(item) for item in patterns if str(item).strip()  # 有效设计模式条目
        )  # 列表形式的设计模式文本

    # Skill 合同优先覆盖项目级验证方法。
    validation_method = contract.get(  # 最终验证方法
        "validation_method",  # Skill 合同验证方法字段
        profile.get("validation_method", "not specified"),  # 项目级验证方法回退
    )  # Skill 验证方法

    # Skill 合同优先覆盖项目级验证粒度。
    validation_granularity = contract.get(  # 最终验证粒度
        "validation_granularity",  # Skill 合同验证粒度字段
        profile.get("validation_granularity", "not specified"),  # 项目级验证粒度回退
    )  # Skill 验证粒度

    # 空白前向测试策略回退为明确的未配置文本。
    str_forward_policy = (
        str(contract.get("forward_testing_policy", "not specified")).strip()  # 原始前向测试策略
        or "not specified"  # 空策略的显式回退值
    )  # 前向测试策略

    # Skill 设计字段按执行流程顺序输出。
    list_lines = [
        f"- Trigger scenarios: {contract.get('trigger_scenarios', 'not specified')}.",  # 触发场景
        f"- Design patterns: {patterns_text or 'not specified'}.",  # 设计模式
        f"- Resource boundaries: {contract.get('resource_plan', 'not specified')}.",  # 资源边界
        f"- Progressive disclosure: {contract.get('progressive_disclosure_policy', 'not specified')}.",  # 渐进披露策略
        f"- Validation gates: {contract.get('validation_gates', 'not specified')}.",  # 验证门禁
        f"- Forward testing: {str_forward_policy}.",  # 前向测试要求
        f"- Validation method: {validation_method}; granularity: {validation_granularity}.",  # 验证方法与粒度
        f"- Reference material policy: {contract.get('reference_material_policy', 'temporary inputs only')}.",  # 参考材料保留策略
    ]

    # Skill 合同字段按声明顺序拼装为 Markdown 列表。
    return "\n".join(list_lines)

# 会话完成合同固定工作闭环和自然语言默认值。
def conversation_completion_contract(profile: dict | None) -> str:
    """渲染开发会话的完成与阻塞报告合同。

    参数:
        profile: 可选项目配置，用于读取默认会话语言。

    返回:
        会话完成、验证和阻塞报告规则文本。
    """

    # profile 缺失时沿用项目默认中文会话约定。
    default_language = (
        profile.get("default_conversation_language", "中文")  # profile 会话语言
        if profile  # 优先读取项目配置
        else "中文"  # 无 profile 时的默认语言
    )  # 自然语言回复默认语言

    # 三条规则覆盖完成、语言和证据，不重复全局执行基线。
    return "\n".join([
        (
            f"- Natural-language replies, including `<proposed_plan>` content, use "
            f"`{default_language}` unless the user switches language; keep tags, code, "
            "commands, logs, errors, and proper nouns unchanged."
        ),
        "- Finish feasible requested work; preserve user changes and the directory contract.",
        (
            "- Run narrow then final checks; report blockers, completed files, assumptions, "
            "skipped checks, and next steps."
        ),
    ])

# 记忆合同公开权威路径、读写门禁与历史引导命令。
def memory_contract(profile: dict | None, project: Path) -> str:
    """渲染项目级持久记忆的使用合同。

    参数:
        profile: 项目设计配置；未启用记忆时不输出合同。
        project: 用于生成仓库内管理命令的项目根目录。

    返回:
        记忆路径、读取策略、初始化门禁和查询命令文本。
    """

    # 没有 profile 时不能判断记忆是否启用。
    if not profile:

        # 未配置记忆合同的项目保持该段为空。
        return ""

    # 原始配置先独立取值，避免重复读取和类型分支。
    value_memory_contract = profile.get("memory_contract", {})  # 原始记忆合同配置

    # 非映射合同按空映射处理。
    contract = (
        value_memory_contract if isinstance(value_memory_contract, dict) else {}  # 记忆合同映射
    )  # 规范化后的记忆合同映射

    # 标记 enabled 判断，控制 memory_contract 的分支走向。
    bool_enabled = bool(  # 兼容新旧记忆启用字段
        contract.get("enabled", profile.get("memory_enabled", False))  # 新旧启用字段
    )  # 记忆功能启用状态

    # enabled 和旧版 memory_enabled 均未开启时跳过渲染。
    if not bool_enabled:

        # 禁用状态不公开记忆命令。
        return ""

    # 指南路径指向项目记忆的人工入口。
    guide = contract.get("guide", "docs/memory/MEMORY.md")  # 记忆指南路径

    # 后端名称让执行者知道权威数据形态。
    backend = contract.get("storage_backend", "sqlite-plus-jsonl")  # 记忆存储后端

    # 长版缺省策略压缩为适合根规则的短文本。
    # 读取策略控制新工作开始前需要加载的记忆范围。
    str_read_policy = contract.get(  # 最终记忆读取策略
        "read_policy",  # 读取策略字段名
        "read latest handoff plus relevant docs/memory summaries before implementation",  # 缺省读取策略
    )  # 记忆读取策略

    # 已知缺省策略使用更紧凑但等价的表述。
    if str_read_policy == "read latest handoff plus relevant docs/memory summaries before implementation":

        # 压缩文本保持与详细缺省策略相同的执行语义。
        str_read_policy = (
            "latest handoff + relevant memory summaries before work"  # 精简读取策略
        )  # 根规则中的压缩读取策略

    # 敏感信息策略明确禁止写入持久记忆的内容。
    # 敏感性策略决定持久记忆禁止记录的内容。
    str_sensitivity = contract.get(  # 最终敏感信息策略
        "sensitivity_policy",  # 敏感信息策略字段名
        "do not store secrets, credentials, or raw local private paths",  # 缺省敏感性策略
    )  # 记忆敏感信息策略

    # 缺省敏感策略保持规范措辞，避免不同 profile 产生漂移。
    if str_sensitivity == "do not store secrets, credentials, or raw local private paths":

        # 规范缺省文本避免不同来源产生无意义漂移。
        str_sensitivity = (
            "do not store secrets, credentials, or raw local private paths"  # 规范敏感性文本
        )  # 规范敏感信息规则文本

    # 查询命令提供任务相关记忆检索入口。
    str_read_command = project_command(  # 任务记忆查询入口
        project, profile, "manage_docs.py", "memory-read", "<project>",  # 查询命令主体
        "--query", "\"<task>\"", "--limit", "5",  # 查询文本与返回上限
    )  # 任务记忆查询命令

    # 门禁命令在新工作前验证记忆基础设施完整性。
    str_gate_command = project_command(  # 记忆基础设施检查入口
        project, profile, "manage_docs.py", "memory-gate", "<project>"  # 门禁命令主体
    )  # 记忆完整性门禁命令

    # 初始化命令保留显式确认参数，避免未经授权创建记忆。
    str_init_command = project_command(  # 经授权的记忆初始化入口
        project, profile, "manage_docs.py", "memory-init", "<project>",  # 初始化命令主体
        "--confirm-create",  # 显式初始化授权参数
    )  # 记忆初始化授权命令

    # 历史引导命令按时间导入同一工作目录的旧会话。
    str_bootstrap_command = project_command(  # 历史会话导入入口
        project, profile, "manage_docs.py", "memory-bootstrap-sessions", "<project>"  # 引导命令主体
    )  # 历史会话引导命令

    # 记忆合同按路径、读取、门禁、历史、查询和敏感性排序。
    return "\n".join([
        f"- Root: `{contract.get('folder', 'docs/memory')}`; guide: `{guide}`; backend: `{backend}`.",
        f"- Read {str_read_policy}.",
        f"- Gate with `{str_gate_command}`; if missing, ask before `{str_init_command}`.",
        f"- Historical work runs `{str_bootstrap_command}` for exact-cwd sessions in timestamp order.",
        f"- Query with `{str_read_command}`; write/compress through memory CLI; handoff appends.",
        f"- Sensitivity: {str_sensitivity}.",
    ])

# 文档治理合同连接恢复、会话、handoff 和目录审查命令。
def documentation_governance_contract(profile: dict | None, project: Path) -> str:
    """渲染项目文档生命周期与目录治理合同。

    参数:
        profile: 项目设计配置；为空时不输出文档治理合同。
        project: 用于生成仓库内治理命令的项目根目录。

    返回:
        恢复检查、会话登记、handoff 和目录审查规则文本。
    """

    # 没有 profile 时不能生成仓库专属文档命令。
    if not profile:

        # 未配置项目不输出推测性的文档治理合同。
        return ""

    # 文档合同定义根目录、handoff 和目录管理入口。
    contract = profile.get("docs_contract", {})  # 文档治理合同配置

    # handoff 子合同提供当前交接文件路径。
    handoff = contract.get("handoff", {})  # 交接文档配置

    # 目录管理子合同提供详细文档位置。
    dir_manager = contract.get("dir_manager", {})  # 目录治理文档配置

    # 当前 handoff 路径在开始与完成规则中复用。
    str_handoff_path = handoff.get(  # 当前交接文档路径
        "current", "docs/handoff/HANDOFF.md"  # handoff 当前文件字段
    )  # 交接文档的实际读取路径

    # 恢复检查用于识别上次会话是否中断。
    str_resume_check = project_command(  # 恢复状态检查入口
        project, profile, "manage_docs.py", "resume-check", "<project>"  # 检查命令主体
    )  # 会话恢复检查命令

    # 恢复修复命令需要显式 recovery 输入。
    str_resume_repair = project_command(  # 中断状态修复入口
        project, profile, "manage_docs.py", "resume-repair", "<project>",  # 修复命令主体
        "--input", "recovery.json",  # 恢复数据输入参数
    )  # 中断会话修复命令

    # 会话登记命令在实际修改前创建受管状态。
    str_start_session = project_command(  # 新工作登记入口
        project, profile, "manage_docs.py", "start-session", "<project>",  # 登记命令主体
        "--input", "session.json",  # 会话数据输入参数
    )  # 新工作会话登记命令

    # 完成命令以结构化输入更新 handoff 和项目记忆。
    str_handoff_command = project_command(  # 完成工作交接入口
        project, profile, "manage_docs.py", "handoff", "<project>",  # 交接命令主体
        "--input", "handoff.json",  # 交接数据输入参数
    )  # 完成会话交接命令

    # 目录审查命令在文件夹变更前验证治理计划。
    str_directory_review = project_command(  # 目录变更审查入口
        project, profile, "manage_dirs.py", "review", "<project>",  # 目录审查主体
        "--input", "change.json",  # 目录计划输入参数
    )  # 目录变更审查命令

    # 文档治理规则保持生命周期顺序，便于执行者逐项遵循。
    list_lines = [
        f"- Docs root: `{contract.get('root', 'docs')}`; latest handoff is "
        f"`{str_handoff_path}`.",
        (
            f"- Before new work, read "
            f"`{str_handoff_path}`, run `{str_resume_check}`, and use "
            f"`{str_resume_repair}` "
            f"if interrupted."
        ),
        f"- Start work with `{str_start_session}`.",  # 会话登记规则
        (
            f"- Every completed development conversation must write "
            f"`{str_handoff_path}`; use `{str_handoff_command}` "
            f"at task completion."
        ),
        (
            "- Memory, development, install configuration, git-manager, handoff history, "
            "and archive naming details live under `docs/`; root AGENTS.md keeps only "
            "entry rules."
        ),
        (
            f"- Directory changes require "
            f"`{str_directory_review}`; "
            f"blocked reviews require explicit user force-confirmation and risk capture in "
            f"handoff."
        ),
        (
            f"- Dir manager details live in `{dir_manager.get('folder', 'docs/dir_manager')}/`; "
            f"review outcomes decide whether folder mutation may proceed."
        ),
    ]

    # 聚合文本直接进入任务专用门禁段落。
    return "\n".join(list_lines)

# 合同筛选器把长合同压缩为根文件需要的阻断行。
def filtered_contract_rules(
    text: str,
    rule_prefix: str,
    fragments: tuple[str, ...],
    priority: int,
) -> list[Rule]:
    """从合同文本中选择包含指定片段的规则。

    参数:
        text: 完整合同文本。
        rule_prefix: 生成稳定规则 ID 的类别前缀。
        fragments: 决定保留哪些行的匹配片段。
        priority: 选中规则的统一优先级。

    返回:
        仅包含会改变根级执行行为的 Rule 列表。
    """

    # 空合同不产生任何根级规则。
    if not text:

        # 返回新列表，避免调用方共享可变状态。
        return []

    # 结果按原合同顺序累积，以保持受管输出稳定。
    list_rules: list[Rule] = []  # 筛选后的根级规则

    # 每个合同行只要命中一个决策片段即可保留。
    for index, str_line in enumerate(text.splitlines()):

        # 非阻断信息继续保留在详细合同来源中。
        if not any(fragment in str_line for fragment in fragments):

            # 跳过不会改变根级执行决策的合同行。
            continue

        # 稳定索引保留原合同中的规则身份和顺序。
        list_rules.append(
            Rule(f"{rule_prefix}.{index}", "Task-specific gates", str_line, priority)
        )

    # 调用方负责与其他规则类别合并和最终去重。
    return list_rules

# 目录入口聚合器集中处理项目根、设置和变更审查边界。
def directory_gate_rules(profile: dict, project: Path) -> tuple[list[Rule], dict]:
    """构建目录与工作区设置的阻断规则。

    参数:
        profile: 已确认存在的项目设计配置。
        project: 用于生成目录审查命令的项目根目录。

    返回:
        目录规则列表，以及供远程规则复用的规范化目录合同。
    """

    # 目录合同提供项目根、设置和远程目录策略。
    value_directory = profile.get("directory_contract", {})  # 原始目录合同

    # 非映射目录合同按空映射处理。
    dict_directory = (
        value_directory if isinstance(value_directory, dict) else {}  # 目录合同映射
    )  # 规范化目录合同

    # 目录管理合同提供指南目录等治理入口。
    value_dir_manager = profile.get("dir_manager_contract", {})  # 原始目录管理合同

    # 目录管理配置类型异常时回退为空映射。
    dict_dir_manager = (
        value_dir_manager if isinstance(value_dir_manager, dict) else {}  # 目录管理映射
    )  # 规范化目录管理合同

    # 工作区设置策略从规范化目录合同中读取。
    value_settings = dict_directory.get("workspace_settings_policy", {})  # 原始设置策略

    # 非映射设置策略按空映射处理。
    dict_settings = (
        value_settings if isinstance(value_settings, dict) else {}  # 工作区设置映射
    )  # 规范化工作区设置策略

    # 主根为空时不生成项目根限制规则。
    str_primary_root = str(dict_directory.get("primary_project_root", "")).strip()  # 项目主根

    # 私有设置目录为本地与远程文件提供共同前缀。
    str_settings_folder = dict_settings.get("folder", ".settings")  # 私有设置目录

    # 本地设置文件缺省落在私有设置目录下。
    str_local_settings = str(  # 最终本地设置路径
        dict_settings.get(  # 本地设置文件配置
            "local_default_file", f"{str_settings_folder}/project.local.json"  # 本地设置回退
        )
    ).strip()  # 本地设置文件

    # 远程设置文件与本地敏感配置保持分离。
    str_remote_settings = str(  # 最终远程设置路径
        dict_settings.get(  # 远程设置文件配置
            "remote_default_file", f"{str_settings_folder}/project.remote.json"  # 远程设置回退
        )
    ).strip()  # 远程设置文件

    # 目录指南位置用于构造审查说明路径。
    str_dir_guide = dict_dir_manager.get("folder", "docs/dir_manager")  # 目录指南位置

    # 审查命令复用项目正确的脚本入口解析。
    str_review_command = project_command(  # 目录审查命令文本
        project, profile, "manage_dirs.py", "review", "<project>",  # 审查命令主体
        "--input", "change.json",  # 审查计划输入参数
    )  # 可直接写入规则的目录审查命令

    # 设置边界文本组合本地、远程和禁止同步路径。
    str_settings_rule = (  # 工作区私有设置阻断文本
        f"- **Workspace settings:** keep local config in `{str_local_settings}`, remote "
        f"config in `{str_remote_settings}`, and never copy "
        f"`{str_settings_folder}/*.local.json` such as "
        f"`{str_settings_folder}/server_list.local.json` to remote servers."
    )  # 私有设置不得外传的规则

    # 目录变更规则保留审查入口和治理指南位置。
    str_review_rule = (  # 目录变更审查阻断文本
        f"- **Directory changes:** review create/move/delete/rename plans with "
        f"`{str_dir_guide}/DIR_MANAGER.md` and run `{str_review_command}` before "
        "mutating governed folders."
    )  # 目录变更审查入口规则

    # 两条目录规则在任何主根配置下都必须存在。
    list_rules = [  # 不依赖主根配置的目录规则
        Rule("settings.local-private", "Task-specific gates", str_settings_rule, 10),  # 私有设置边界
        Rule("directory.review", "Task-specific gates", str_review_rule, 10),  # 目录审查入口
        Rule(  # 阻断审查的显式确认要求
            "directory.blocked-review",  # 阻断审查规则 ID
            "Task-specific gates",  # 阻断审查所属段落
            "- **Blocked directory review:** stop by default; proceed only after explicit "
            "user force-confirmation and record the risk in handoff.",
            10,  # 阻断审查规则优先级
        ),
    ]  # 必须始终存在的目录治理规则

    # 主根仅在 profile 明确配置时进入受管规则。
    if str_primary_root:

        # 主根规则优先于普通目录布局建议。
        list_rules.append(
            Rule(
                "directory.primary-root",
                "Task-specific gates",
                f"- **Project root:** keep feature work inside `{str_primary_root}` "
                "unless the directory contract is updated.",
                10,
            )
        )

    # 同时返回目录合同，避免通过 profile 写入临时渲染状态。
    return list_rules, dict_directory

# 远程规则聚合器只保留部署边界、结构索引和路由合同。
def remote_gate_rules(profile: dict, dict_directory: dict) -> list[Rule]:
    """构建远程部署与服务器路由规则。

    参数:
        profile: 已确认存在的项目设计配置。
        dict_directory: 已规范化的目录合同。

    返回:
        远程部署、规划结构和路由入口规则。
    """

    # 远程规则随启用的部署和路由合同累积。
    list_rules: list[Rule] = []  # 远程阻断规则

    # Skill 开发源码默认不能作为部署内容同步到服务器。
    if str(profile.get("kind", "")).strip().lower() == "skill":

        # 部署规则区分开发内容和明确的运行时产物。
        list_rules.append(
            Rule(
                "remote.no-skill-dev-sync",
                "Task-specific gates",
                "- **Remote deployment:** do not sync local skill-development content "
                "to servers; deploy only explicit runtime/deployment artifacts unless "
                "the user overrides.",
                10,
            )
        )

    # 远程环境策略决定是否公开规划结构入口。
    value_environment = dict_directory.get("remote_environment_policy", {})  # 远程环境策略

    # 非映射环境策略按空映射处理。
    dict_environment = (
        value_environment if isinstance(value_environment, dict) else {}  # 远程环境映射
    )  # 规范化环境策略

    # 远程归档策略同样依赖规划结构文件。
    value_runtime = dict_directory.get("remote_runtime_archive_policy", {})  # 远程归档策略

    # 非映射归档策略按空映射处理。
    dict_runtime = (
        value_runtime if isinstance(value_runtime, dict) else {}  # 远程归档映射
    )  # 规范化归档策略

    # 任一远程策略启用都要求输出规划结构索引。
    bool_planned_structure = (
        dict_environment.get("status") == "enabled"  # 远程环境已启用
        or dict_runtime.get("status") == "enabled"  # 远程归档已启用
    )  # 是否需要远程规划结构入口

    # 启用任一远程目录策略时要求以 planned_structure 为权威来源。
    if bool_planned_structure:

        # 根规则只保留结构索引，不复制具体服务器路径。
        list_rules.append(
            Rule(
                "remote.planned-structure",
                "Task-specific gates",
                "- **Remote structure:** keep deployment, conda/runtime, backup, and "
                "archive path details in `docs/dir_manager/planned_structure.json`; root "
                "AGENTS.md is only the entry rule index.",
                15,
            )
        )

    # 路由合同只在 profile 明确启用时返回文本。
    str_remote_contract = remote_server_contract(profile)  # 远程服务器路由合同

    # 远程合同启用时作为单个紧凑规则加入。
    if str_remote_contract:

        # 完整路由表仍留在 profile，根文件只承载入口文本。
        list_rules.append(
            Rule("remote.routes", "Task-specific gates", str_remote_contract, 10)
        )

    # 返回与当前 profile 匹配的远程规则。
    return list_rules

# 任务专用门禁从完整 profile 中筛选高影响执行入口。
def task_specific_gates(profile: dict | None, project: Path) -> str:
    """生成会改变执行行为的仓库级阻断入口。

    参数:
        profile: 项目设计配置；为空时返回配置缺失提示。
        project: 用于生成仓库内治理命令的项目根目录。

    返回:
        按优先级去重后的任务专用门禁文本。
    """

    # 未确认强控制时只保留不能被误解为已完成治理的入口提示。
    if not profile:

        # 返回未配置 profile 时仍有决策意义的入口规则。
        return (
            "- AGENTS generation: collect a confirmed design profile before claiming "
            "strict controlled output."
        )

    # 目录聚合器同时返回远程规则所需的规范化目录合同。
    tuple_gate_context = directory_gate_rules(profile, project)  # 目录规则与合同二元组

    # 二元组首项是已构造的目录规则集合。
    list_rules = tuple_gate_context[0]  # 当前已聚合的根级规则

    # 二元组次项供远程规则读取目录策略。
    dict_directory = tuple_gate_context[1]  # 远程规则复用的目录合同

    # 远程部署和路由规则紧随目录边界加入。
    list_rules.extend(remote_gate_rules(profile, dict_directory))

    # 读取显式布尔选择，避免把缺失值或整数误解释为启用状态。
    value_codebase_memory_choice = profile.get("use_codebase_memory_mcp")  # 知识图谱显式选择值

    # 知识图谱开关无论启用或禁用都必须形成明确的根级规则。
    if isinstance(value_codebase_memory_choice, bool) and value_codebase_memory_choice:

        # 启用态规则公开索引、持久化、架构分析和调试查询门禁。
        list_rules.append(
            Rule(
                "codebase-memory.enabled",
                "Task-specific gates",
                "- **Codebase memory MCP:** enabled; keep root `/.codebase-memory/` ignored and untracked; "
                "before managed writes require a `full` + persistence index, ready status, architecture analysis, "
                "and matching live/disk node and edge counts. During code debugging, use `get_architecture`, "
                "`search_graph`, `trace_path`, and `detect_changes` first; report graph failure before fallback.",
                5,
            )
        )

    # 禁用态规则禁止探测或查询，但仍保留本地产物 Git 边界。
    elif isinstance(value_codebase_memory_choice, bool) and not value_codebase_memory_choice:

        # 禁用规则明确阻止后续代理擅自启动知识图谱工作流。
        list_rules.append(
            Rule(
                "codebase-memory.disabled",
                "Task-specific gates",
                "- **Codebase memory MCP:** disabled; do not detect, configure, index, or query the MCP; "
                "keep root `/.codebase-memory/` ignored and untracked.",
                5,
            )
        )

    # 每个详细合同声明其根级筛选片段与优先级。
    list_contract_groups = [
        (
            release_contract(profile, project),  # 发布合同文本
            "release",  # 发布规则 ID 前缀
            ("Install only", "Do not push", RELEASE_CORE_WORKTREE_RULE,  # 发布阻断片段
             "Release details live", "Different-version release"),  # 发布来源与历史包片段
            20,  # 发布阻断规则优先级
        ),
        (
            engineering_rule_contract(profile),  # 工程规则合同文本
            "engineering",  # 工程规则 ID 前缀
            ("Primary rule set:", "Mode:", "Do not paste full book rules"),  # 工程合同筛选片段
            25,  # 工程规则优先级
        ),
        (
            documentation_governance_contract(profile, project),  # 文档治理合同文本
            "docs",  # 文档规则 ID 前缀
            ("Before new work", "Start work", "Every completed"),  # 文档阻断片段
            20,  # 文档治理优先级
        ),
        (
            memory_contract(profile, project),  # 记忆合同文本
            "memory",  # 记忆规则 ID 前缀
            ("Root:", "Read ", "Gate with", "Historical", "Query with"),  # 记忆入口片段
            30,  # 记忆规则优先级
        ),
        (
            skill_design_contract(profile, project),  # Skill 设计合同文本
            "skill",  # Skill 规则 ID 前缀
            ("Validation gates:", "Forward testing:"),  # Skill 完成门禁片段
            25,  # Skill 规则优先级
        ),
    ]  # 合同文本、规则类别、筛选片段和优先级

    # 同一筛选器保证各合同类别采用一致的根级压缩逻辑。
    for text, rule_prefix, fragments, priority in list_contract_groups:

        # 当前合同的阻断行追加到统一规则集合。
        list_rules.extend(
            filtered_contract_rules(text, rule_prefix, fragments, priority)
        )

    # 根文件只保留阻断条件和入口；完整命令手册留在其权威文档。
    return compact_task_gate_text(render_rule_list(list_rules))

# 修改前阅读清单只选取当前项目真实存在的事实。
def read_before_changing(context: dict) -> str:
    """生成当前仓库可读入口，不输出空表格或占位行。

    参数:
        context: 项目探测阶段生成的文档、工具和样例事实。

    返回:
        按优先级去重后的修改前阅读规则文本。
    """

    # 汇总 read rules，作为可检查上下文入口。
    list_rules: list[Rule] = []  # 修改前必须读取的候选规则

    # 架构和政策文档优先级最高。
    for index, str_line in enumerate(key_decisions(context).splitlines()):

        # 每个关键决策行保留独立 ID，便于稳定去重。
        list_rules.append(Rule(f"read.decisions.{index}", "Read before changing", str_line, 20))

    # 自动化脚本、质量配置和平台文件帮助代理复用现有入口。
    for index, str_line in enumerate(codebase_state(context).splitlines()):

        # 项目状态行在架构决策之后输出。
        list_rules.append(Rule(f"read.state.{index}", "Read before changing", str_line, 40))

    # hook 和 GitHub 设置只有被发现时才输出。
    for index, str_line in enumerate(hook_policy(context).splitlines()):

        # 钩子规则提醒修改者复用现有提交治理。
        list_rules.append(Rule(f"read.hooks.{index}", "Read before changing", str_line, 30))

    # GitHub 设置作为平台侧治理入口单独排列。
    for index, str_line in enumerate(github_settings(context).splitlines()):

        # 平台规则与本地钩子使用相同优先级。
        list_rules.append(Rule(f"read.github.{index}", "Read before changing", str_line, 30))

    # 目录覆盖提示在具体工具和样例之后生效。
    for index, str_line in enumerate(directory_coverage(context).splitlines()):

        # 缺少局部规则的目录以最低优先级提示。
        list_rules.append(Rule(f"read.directory.{index}", "Read before changing", str_line, 50))

    # 真实 utilities 和 golden samples 以普通 bullet 形式写入，避免裸表格行。
    for index, str_path in enumerate(context.get("utilities", [])[:6]):

        # 工具入口提醒代理先阅读现有自动化实现。
        list_rules.append(Rule(
            f"read.utility.{index}",
            "Read before changing",
            f"- Inspect existing automation `{str_path}` before adding new project "
            "tooling.",
            40,
        ))

    # 黄金样例提供最接近的实现与测试模式。
    for index, str_path in enumerate(context.get("golden_samples", [])[:4]):

        # 样例规则避免代理在已有模式时重新发明结构。
        list_rules.append(Rule(
            f"read.sample.{index}",
            "Read before changing",
            f"- Use `{str_path}` as the nearest implementation/test pattern before "
            "inventing a new one.",
            40,
        ))

    # 统一渲染器负责最终排序、过滤和去重。
    return render_rule_list(list_rules)

# 统一规则渲染器负责条件过滤、稳定排序和 ID 去重。
def render_rule_list(rules: list[Rule]) -> str:
    """按 ID 去重并按优先级输出规则。

    参数:
        rules: 带条件、优先级和稳定 ID 的候选规则。

    返回:
        由有效规则文本按稳定顺序拼接成的 Markdown。
    """

    # 已输出 ID 集合阻止同一规则重复进入根文件。
    set_seen: set[str] = set()  # 已输出的稳定规则 ID

    # 保留去重后的文本行。
    list_lines: list[str] = []  # 去重后的规则文本行

    # 优先级低的数值先输出，文本作为稳定排序兜底。
    for rule in sorted(rules, key=lambda item: (item.priority, item.id)):

        # 条件关闭、ID 重复或文本为空的规则不会进入输出。
        if not rule.condition or rule.id in set_seen or not rule.text.strip():

            # 跳过无效规则并继续检查后续候选。
            continue

        # 先登记 ID，确保多行规则也只被采纳一次。
        set_seen.add(rule.id)

        # 空白子行不应在最终受管段落中形成占位行。
        list_lines.extend(line for line in rule.text.splitlines() if line.strip())

    # 规则之间仅使用单个换行符连接。
    return "\n".join(list_lines)

# 编码行为基线从全局覆盖配置读取，不在渲染器内硬编码策略。
def coding_behavior_baseline(project: Path, profile: dict | None, facts: dict | None = None) -> str:
    """渲染项目编码行为覆盖策略。

    参数:
        project: 用于定位全局覆盖配置的项目根目录。
        profile: 可选项目配置，用于解析覆盖文件路径。
        facts: 可选项目事实，保留给兼容调用方。

    返回:
        注释、格式化、尺寸和测试边界规则文本。
    """

    # 定位 config path 的文件边界，供 coding_behavior_baseline 后续读写校验使用。
    str_config_path = local_rule_config_path(project, profile)  # 编码行为配置路径

    # 编码行为与源码治理从同一规则覆盖文件读取。
    dict_overrides = load_global_rule_overrides(project, profile)["data"]  # 当前项目规则覆盖

    # 编码行为字段提供注释、格式和语言技能路由。
    policy = dict_overrides.get(  # 编码行为策略
        "coding_behavior", {}  # 编码行为策略字段
    )  # 编码行为策略映射

    # 文件命名配置提供长度、字符和语义复核合同。
    dict_naming = dict_overrides.get("source_governance", {}).get(  # 文件命名治理配置
        "file_naming_gate", {}  # 文件命名门禁字段
    )

    # 注释策略约束允许保留的语义说明类型。
    comment_quality = str(policy.get("comment_quality", "")).strip()  # 注释质量规则

    # 格式策略约束换行、空白和可读性。
    formatting = str(policy.get("formatting", "")).strip()  # 源码格式规则

    # 非映射路由配置按空配置处理。
    value_routing = policy.get("language_skill_routing", {})  # 原始语言技能路由

    # 路由映射类型异常时不输出语言专属规则。
    routing = value_routing if isinstance(value_routing, dict) else {}  # 最终语言路由映射

    # 共同门禁集中保存跨语言的修改前思考和过程内验证要求。
    shared_route = str(routing.get("shared", "")).strip()  # 语言技能共同门禁

    # Python 路由只保留目标范围和最终语言所有权。
    python_route = str(routing.get("python", "")).strip()  # Python 技能路由规则

    # 脚本路由覆盖仓库支持的 bat、shell、PowerShell 和 Tcl。
    script_route = str(routing.get("script", "")).strip()  # 脚本技能路由规则

    # 汇总 lines，作为 AGENTS 编码行为输出。
    list_lines = [
        f"- 编码行为配置来源：`{str_config_path}`；用户可手动修改该 JSON 后重新渲染。",  # 配置来源
        f"- 注释质量：{comment_quality}",  # 注释语义边界
        f"- {formatting}",  # 源码格式边界
    ]

    # 启用命名门禁时把代理执行所需的硬规则直接投影到根规则。
    if dict_naming.get("enabled"):

        # 长度值只从已验证配置读取，避免渲染器复制治理阈值。
        int_max_chars = dict_naming.get("max_stem_chars", 30)  # 文件名词干长度上限

        # 命名语法规则追加到编码行为段落。
        list_lines.append(
            f"- 文件命名：除 `__init__.py` 外，禁止数字和下划线开头；名称必须总结文件功能，"
            f"不超过 {int_max_chars} 个英文字符。"
        )

        # 语义复核不能由正则替代，必须保留独立 Agent 判断证据。
        if dict_naming.get("semantic_review_required"):

            # 独立规则明确正则检查之外的 Agent 责任。
            list_lines.append("- 文件命名语义：变更文件必须通过 Agent 语义复核并保留匹配修订与路径哈希的证据。")

    # 仅在配置存在时输出共同门禁，避免空标题进入根规则。
    if shared_route:

        # 共同门禁追加一次，后续语言路由不得重复该正文。
        list_lines.append(f"- 语言技能共同门禁：{shared_route}")

    # 仅在配置存在时输出 Python 路由，避免空规则。
    if python_route:

        # Python 路由追加在通用编码行为规则之后。
        list_lines.append(f"- 语言技能路由（Python）：{python_route}")

    # 脚本路由独立判断，允许项目只配置一种语言族。
    if script_route:

        # 脚本路由作为编码行为段落的最后一项。
        list_lines.append(f"- 语言技能路由（脚本）：{script_route}")

    # 所有编码行为规则按配置顺序连接。
    return "\n".join(list_lines)

# 脚本输出合同统一 INFO、WARNING、ERR 与 quiet 行为。
def script_output_policy(project: Path, profile: dict | None) -> str:
    """渲染脚本过程输出和机器可读输出边界。

    参数:
        project: 用于定位全局覆盖配置的项目根目录。
        profile: 可选项目配置，用于解析覆盖文件路径。

    返回:
        输出前缀、Kind 来源和 quiet 行为规则文本。
    """

    # 输出策略文本需要指明其权威配置来源。
    str_config_path = local_rule_config_path(project, profile)  # 输出策略配置路径

    # 脚本输出格式和 Python quiet 行为来自同一策略块。
    policy = load_global_rule_overrides(project, profile)["data"].get(  # 脚本输出策略
        "script_output_policy", {}  # 脚本输出策略字段
    )  # 脚本输出策略映射

    # 非映射格式配置按空映射处理并使用安全缺省值。
    value_formats = policy.get("format", {})  # 原始输出格式配置

    # 格式配置类型异常时采用各通道缺省前缀。
    formats = value_formats if isinstance(value_formats, dict) else {}  # 最终输出格式映射

    # Python 子策略控制过程性 INFO 的静默开关。
    value_python_policy = policy.get("python", {})  # 原始 Python 输出策略

    # Python 输出配置类型异常时使用 quiet 缺省约定。
    python_policy = (  # 最终 Python 输出策略
        value_python_policy if isinstance(value_python_policy, dict) else {}  # Python 输出映射
    )  # 规范化 Python 输出策略

    # 过程性日志前缀来自治理 JSON，渲染时只做默认值兜底。
    info_prefix = formats.get("info", "> INFO: [{kind}]")  # INFO 日志前缀模板

    # 非致命问题沿用策略配置中的 warning 格式。
    warning_prefix = formats.get("warning", "> WARNING: [{kind}]")  # 可恢复风险消息格式

    # 阻断失败采用 error 格式并保留动态 Kind。
    error_prefix = formats.get("error", "> ERR: [{kind}]")  # 阻断失败消息格式

    # quiet 开关来自 Python 输出策略，缺省沿用脚本约定。
    quiet_flag = python_policy.get("quiet_flag", "--quiet")  # Python 静默开关文本

    # 输出合同同时说明配置来源和各通道行为。
    return "\n".join([
        f"- 配置来源：`{str_config_path}`；`Kind` 列表只从该 JSON 读取，代码不得内置业务枚举。",
        (
            f"- "
            f"格式：`{info_prefix}`、`{warning_prefix}`、`{error_prefix}`；Python "
            f"过程性 INFO 默认打印，`{quiet_flag}` 关闭 "
            f"INFO/progress，WARNING 和 ERR 继续可见；机器可读输出不套前缀。"
        ),
    ])

# 模板值聚合器集中生成各受管 AGENTS.md 段落。
def template_values(project: Path, profile: dict | None = None, template_dir: Path | None = None) -> dict[str, str]:
    """构建 AGENTS.md 模板渲染所需的全部命名值。

    参数:
        project: 当前项目根目录。
        profile: 可选项目设计配置；缺失时从项目加载。
        template_dir: 可选模板目录，保留给兼容调用方。

    返回:
        模板占位符名称到已渲染文本的映射。
    """

    # 项目事实驱动概览、文件映射和仓库设置渲染。
    facts = inspect_project(project)  # 当前项目探测事实

    # 命令事实用于命令表和来源摘要。
    commands = extract_commands(project)["commands"]  # 已发现项目命令

    # 作用域事实用于生成局部 AGENTS 索引。
    scopes = detect_scopes(project)["scopes"]  # 已发现规则作用域

    # 上下文事实为阅读清单和仓库治理段落提供输入。
    context = extract_context(project)  # 文档、工具和治理上下文

    # 命令来源按字典序去重，确保模板输出稳定。
    command_source = (
        ", ".join(sorted({item["source"] for item in commands}))  # 非空命令来源集合
        if commands  # 仅在发现命令时生成来源摘要
        else ""  # 未发现命令时不输出来源
    )  # 命令发现来源摘要

    # profile 缺失时沿用项目的中文会话缺省值。
    default_language = (
        profile.get("default_conversation_language", "中文")  # profile 语言配置
        if profile  # 仅在配置存在时读取语言字段
        else "中文"  # 未提供 profile 时使用中文
    )  # 模板默认会话语言

    # 未能解析项目版本时显式标记 unknown。
    project_version = resolved_project_version(project, profile) or "unknown"  # 项目版本

    # 生成器版本同时写入 AGENTS 与 generator 元数据字段。
    str_generator_version = resolved_generator_version(  # 解析后的生成器版本
        project, profile, project_version  # 生成器版本解析上下文
    )  # 当前生成器版本

    # 所有模板占位符在单一映射中构造，避免调用方二次推断。
    return {
        "TIMESTAMP": current_timestamp(),  # 本次渲染时间
        "VERIFIED_TIMESTAMP": "never",  # 尚未执行验证的缺省标记
        "AGENTS_VERSION": str_generator_version,  # AGENTS 元数据版本
        "GENERATOR_VERSION": str_generator_version,  # 生成器实现版本
        "DEFAULT_LANGUAGE": default_language,  # 自然语言默认值
        "PROJECT_OVERVIEW": project_overview(facts, str_generator_version),  # 项目概览
        "CONTROL_PROFILE": control_profile(profile, project, project_version),  # 强控制配置
        "DIRECTORY_CONTRACT": directory_contract(profile, project),  # 目录治理合同
        "REMOTE_SERVER_CONTRACT": remote_server_contract(profile),  # 远程路由合同
        "RELEASE_CONTRACT": release_contract(profile, project),  # 发布与 Git 合同
        "ENGINEERING_RULE_CONTRACT": engineering_rule_contract(profile),  # 工程规则合同
        "SKILL_DESIGN_CONTRACT": skill_design_contract(profile, project),  # Skill 设计合同
        "CONVERSATION_COMPLETION_CONTRACT": conversation_completion_contract(profile),  # 会话完成合同
        "TASK_SPECIFIC_GATES": task_specific_gates(profile, project),  # 高影响任务门禁
        "CODING_BEHAVIOR_BASELINE": coding_behavior_baseline(project, profile, facts),  # 编码行为规则
        "SCRIPT_OUTPUT_POLICY": script_output_policy(project, profile),  # 脚本输出规则
        "MEMORY_CONTRACT": memory_contract(profile, project),  # 持久记忆合同
        "DOCUMENTATION_GOVERNANCE_CONTRACT": documentation_governance_contract(profile, project),  # 文档生命周期合同
        "VERIFICATION_STATUS": "unverified",  # 新渲染结果验证状态
        "COMMAND_SOURCE": command_source,  # 命令探测来源
        "COMMAND_ROWS": command_rows(commands),  # 命令表格行
        "FILE_MAP": file_map(facts).rstrip(),  # 项目文件映射
        "GOLDEN_SAMPLE_ROWS": golden_sample_rows_from_context(context),  # 黄金样例行
        "UTILITY_ROWS": utility_rows(context),  # 工具入口行
        "HEURISTIC_ROWS": heuristic_rows(),  # 启发式说明行
        "REPOSITORY_SETTINGS": "\n".join(
            line
            for line in [
                f"- CI: {', '.join(facts['ci'])}" if facts["ci"] else "",
                f"- Package manager: {facts['package_manager']}" if facts["package_manager"] != "unknown" else "",
            ]
            if line
        ),
        "READ_BEFORE_CHANGING": read_before_changing(context),  # 修改前阅读入口
        "HOOK_POLICY": hook_policy(context),  # Git 钩子策略
        "CI_RULES": ci_rules(context),  # 持续集成规则
        "GITHUB_SETTINGS": github_settings(context),  # GitHub 仓库设置
        "DIRECTORY_COVERAGE": directory_coverage(context),  # 局部规则覆盖提示
        "KEY_DECISIONS": key_decisions(context),  # 架构与政策决策
        "ALWAYS_RULES": bullet_lines([
            "Preserve user changes and hand-written guidance.",
            "Add tests or verification for changed behavior.",
            "Show verification output before claiming completion.",
        ]),
        "ASK_FIRST_RULES": bullet_lines([
            "Adding dependencies.",
            "Changing CI/CD, public APIs, schemas, migrations, or security-sensitive code.",
            "Running destructive or expensive commands.",
        ]),
        "NEVER_RULES": bullet_lines([
            "Sync local skill-development content to remote servers during deployment "
            "unless the user explicitly overrides.",
            "Commit secrets, credentials, or sensitive data.",
            "Modify generated/vendor files unless explicitly requested.",
            "Fabricate commands, files, owners, branches, or policies.",
        ]),
        "CODEBASE_STATE": codebase_state(context),  # 当前代码库治理状态
        "TERMINOLOGY_ROWS": "",  # 兼容旧模板的空术语表
        "SCOPE_INDEX": scope_index(scopes).rstrip(),  # 局部规则作用域索引
    }

# 手工内容提取器保护生成块之外的用户维护文本。
def manual_content(existing: str) -> str:
    """从既有 AGENTS.md 中提取不受生成器管理的手工内容。

    参数:
        existing: 当前 AGENTS.md 的完整文本。

    返回:
        移除受管生成块并清理旧兼容段后的手工文本。
    """

    # 空文件没有可保留的手工内容。
    if not existing.strip():

        # 返回空文本，避免生成空 Human Notes 标题。
        return ""

    # 固定模板标题和边界句不属于用户手工内容。
    set_generated_boilerplate = {
        "# AGENTS.md",  # 根 AGENTS 标题模板
        "**Precedence:** the closest `AGENTS.md` to the files being changed wins. "
        "Explicit user prompts override this file.",
        "### Always Do",  # Always Do 边界标题
        "### Ask First",  # 旧版操作确认标题
        "### Never Do",  # 旧版禁止操作标题
        "Use this order: explicit user prompt, closest AGENTS.md, parent AGENTS.md, general repository docs.",  # 旧版冲突优先级句
    }

    # 这些旧版普通段落整体由当前生成器替代。
    set_generated_plain_blocks = {
        "## Agent Work Loop",  # 根 AGENTS 固定工作循环段
        "## Boundaries",  # 根 AGENTS 边界段
        "## When Instructions Conflict",  # 根 AGENTS 冲突处理段
    }

    # 元数据注释通过前缀识别，兼容动态时间和版本内容。
    tuple_generated_prefixes = (
        "<!-- Last updated:", "<!-- AGENTS-METADATA:"  # 动态时间与版本元数据
    )  # 动态生成元数据前缀

    # 保留行按原文件顺序累积。
    list_kept: list[str] = []  # 用户维护的手工内容行

    # 标记块状态用于跳过当前生成器管理的显式区域。
    bool_skipping_marker = False  # 是否位于生成标记块内

    # 普通块状态兼容迁移前没有显式标记的旧段落。
    bool_skipping_plain_block = False  # 是否位于旧版固定段落内

    # 逐项检查 manual_content 渲染候选。
    for line in existing.splitlines():

        # 去除外围空白后匹配标题和模板固定句。
        stripped = line.strip()  # 当前行的规范匹配文本

        # 进入显式生成块后跳过直至结束标记。
        if line.startswith(GENERATED_START):

            # 开始标记后的文本属于生成器管理范围。
            bool_skipping_marker = True  # 开始跳过受管生成块

            # 显式标记出现后清除旧版普通块状态。
            bool_skipping_plain_block = False  # 显式标记优先于旧版块状态

            # 分隔 manual_content 的控制流边界。
            continue

        # 结束标记恢复对后续手工文本的采集。
        if line.startswith(GENERATED_END):

            # 结束标记恢复后续手工内容采集。
            bool_skipping_marker = False  # 离开受管生成块

            # 结束标记自身不属于手工内容。
            continue

        # 受管标记块内部的所有行都直接跳过。
        if bool_skipping_marker:

            # 继续扫描以寻找对应结束标记。
            continue

        # 生成器身份和动态元数据注释不能进入 Human Notes。
        if (
            line.startswith("<!-- FOR AI")
            or line.startswith("<!-- Managed by agent:")
            or line.startswith(tuple_generated_prefixes)
        ):

            # 元数据由下一次渲染重新生成。
            continue

        # Human Notes 标题是容器，不是用户正文。
        if stripped == "## Human Notes":

            # Human Notes 标题明确恢复手工正文采集。
            bool_skipping_plain_block = False  # 从旧版块跳过状态恢复

            # 避免重复输出 Human Notes 标题。
            continue

        # 遇到旧版固定段落标题时开始整体跳过。
        if stripped in set_generated_plain_blocks:

            # 固定标题后的内容由当前模板重新生成。
            bool_skipping_plain_block = True  # 进入旧版固定段落

            # 固定标题由当前模板重新生成。
            continue

        # 新的二级标题代表旧版固定段落结束。
        if bool_skipping_plain_block and stripped.startswith("## "):

            # 新二级标题结束旧版固定段落范围。
            bool_skipping_plain_block = False  # 恢复普通手工内容采集

        # 仍处于旧版固定段落时跳过当前行。
        if bool_skipping_plain_block:

            # 继续寻找下一个二级标题边界。
            continue

        # 只有非模板固定句才被保留为用户内容。
        if stripped not in set_generated_boilerplate:

            # 原始行保留缩进和内部空白。
            list_kept.append(line)

    # 合并后只清理整体首尾空白，不改变正文布局。
    text = "\n".join(list_kept).strip()  # 最终手工正文

    # 全部内容均属于模板时不生成 Human Notes。
    if not text:

        # 空字符串让上层跳过手工段落。
        return ""

    # 非空手工内容统一放回 Human Notes 容器。
    return f"\n## Human Notes\n\n{text}\n"
