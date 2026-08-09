"""把项目治理配置转换为 AGENTS.md 中可执行的精简规则。"""

# 根级门禁压缩已拆分到同目录模块，避免合同聚合分片超过源码尺寸门禁。
from render_gate_compaction import compact_task_gate_text
from tester_worker_profile import SINGLE_TASK_AUTHORIZATION_RECEIPT

# 远程工作文件夹状态从画像字段推导为稳定可审计标签。
def _remote_workspace_state(profile: dict | None) -> str:
    """从画像状态推导可审计的远程工作文件夹状态标签。

    参数：profile 为可选项目设计画像。
    返回：profile-missing、disabled、enabled 或 takeover-compressed。
    """

    # 未提供画像时必须显式显示配置缺失，而不是假设本地或远程已就绪。
    if not profile:

        # 缺失画像保持 fail-closed 状态标签。
        return "profile-missing"

    # 远程合同缺失或关闭都归入 fail-closed 的禁用状态。
    value_contract = profile.get("remote_server_contract", {})  # 原始远程合同

    # 非映射合同按空映射处理，避免读取异常字段。
    dict_contract = value_contract if isinstance(value_contract, dict) else {}  # 规范化远程合同

    # 关闭状态不允许继续假设远程工作区已验证。
    if not dict_contract.get("enabled"):

        # 禁用画像保持本地可审计状态。
        return "disabled"

    # 读取画像提供的显式接管模式值。
    value_takeover_mode = profile.get("takeover_mode")  # 画像接管模式原始值

    # 读取远程合同提供的显式接管模式值。
    value_contract_takeover_mode = dict_contract.get("takeover_mode")  # 合同接管模式原始值

    # 合并两个来源的严格布尔接管开关。
    bool_takeover_mode = (  # 显式接管开关
        isinstance(value_takeover_mode, bool) and bool(value_takeover_mode)  # 画像布尔接管开关
        or isinstance(value_contract_takeover_mode, bool) and bool(value_contract_takeover_mode)  # 合同布尔接管开关
    )  # 是否显式启用接管模式

    # 接管模式配合压缩策略时必须显示压缩接管状态。
    str_compression_policy = str(profile.get("compression_policy", "")).lower()  # 画像压缩策略文本

    # 该组合是接管压缩的明确画像信号，不会误判普通 enabled。
    if bool_takeover_mode and "compression" in str_compression_policy:

        # 兼容状态字段命中时保留 fail-closed 远程工作区入口。
        return "takeover-compressed"

    # 兼容其他字符串或布尔状态字段。
    list_state_values = [  # 远程状态候选值
        profile.get("remote_workspace_state"),  # 画像远程工作区状态
        profile.get("remote_state"),  # 兼容远程状态字段
        profile.get("mode"),  # 画像运行模式
        profile.get("takeover"),  # 接管开关
        profile.get("takeover_mode"),  # 接管模式字段
        profile.get("takeover_required"),  # 接管要求字段
        profile.get("compressed"),  # 压缩状态字段
        profile.get("compression_state"),  # 压缩状态枚举
        profile.get("takeover_compressed"),  # 接管压缩字段
        dict_contract.get("workspace_state"),  # 合同远程工作区状态
        dict_contract.get("mode"),  # 合同运行模式
        dict_contract.get("takeover"),  # 合同接管开关
        dict_contract.get("takeover_mode"),  # 合同接管模式
        dict_contract.get("takeover_required"),  # 合同接管要求
        dict_contract.get("compressed"),  # 合同压缩状态
        dict_contract.get("compression_state"),  # 合同压缩状态枚举
        dict_contract.get("takeover_compressed"),  # 合同接管压缩
    ]  # 兼容状态字段集合

    # 字符串状态用于识别接管或压缩模式，普通 compression_policy 不在候选中。
    str_state = " ".join(  # 规范化远程状态文本
        str(value).strip().lower()  # 单个状态标准化
        for value in list_state_values  # 遍历状态候选
        if value is not None  # 排除缺失状态
    )  # 远程状态文本

    # 接管或压缩状态必须明确显示专用标签。
    if "takeover" in str_state or "compressed" in str_state:

        # 接管压缩状态保留 fail-closed 远程工作区入口。
        return "takeover-compressed"

    # 其余启用状态继续要求运行时检查 verified workspace。
    return "enabled"

# 远程工作文件夹合同在所有画像状态下都保留。
def remote_workspace_management_rule(profile: dict | None) -> Rule:
    """渲染所有画像状态都必须保留的远程工作文件夹合同。

    参数：profile 为可选项目设计画像。
    返回：可写入 Task-specific gates 的 Rule 对象。
    """

    # 固定三句同时覆盖状态感知、精确路由和规划结构生命周期。
    str_state = _remote_workspace_state(profile)  # 可审计远程状态标签

    # 规则正文保持固定句子，避免四种画像状态出现语义漂移。
    str_text = (  # 远程工作文件夹合同正文
        "- **Remote workspace management:** Remote workspace management is state-aware "
        "and fail-closed.\n"
        "- Before remote file operations, resolve the exact task route and require a "
        "verified workspace; unmatched or unverified states stop.\n"
        "- Keep deployment, conda/runtime, backup, and archive artifact lifecycle details "
        "in `docs/dir_manager/planned_structure.json`.\n"
        f"- Remote workspace state: {str_state}"
    )  # 远程合同固定正文

    # 低优先级让工作区和唯一测试智能体规则先于普通合同输出。
    return Rule("remote.workspace-management", "Task-specific gates", str_text, 8)

# 唯一 tester_worker 合同同时声明树哈希、命名和单次授权收据。
def tester_worker_rule() -> Rule:
    """渲染唯一 tester_worker、哈希自主确认和命名合同。

    参数：无。
    返回：可写入 Task-specific gates 的 Rule 对象。
    """

    # 根 AGENTS 必须指向唯一 TOML，不允许调用方临时替换测试智能体。
    str_text = (  # 唯一测试智能体合同正文
        "- **Unique TESTER:** Only the canonical `tester_worker` may own tests/**; "
        "`~/.codex/agents/tester_worker.toml`. "
        "Do not delegate tests/** to a generic or second test agent. "
        "Routine test-hash confirmation is prohibited. "
        "Agent autonomously confirms when the canonical tester result agrees "
        "with the authoritative current tests tree or receipt. "
        "A report-only hash mismatch is corrected to the authoritative value. "
        "Conflicting or insufficient provenance stops for user review without "
        "an autonomous rerun. New test files use functional or behavioral "
        "semantic names; filename stems must not contain digits, including v1, "
        "v2, 1, 2, part1, and part2.\n"
        f"- **Task authorization:** {SINGLE_TASK_AUTHORIZATION_RECEIPT}"
    )  # 唯一测试智能体合同文本

    # 唯一 worker 规则应紧随远程状态合同输出。
    return Rule("testing.unique-worker", "Task-specific gates", str_text, 9)

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
            f"- Natural-language replies, including `<proposed_plan>` content, use `{default_language}` "
            "unless the user switches languages; keep technical literals unchanged."
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
            f"- Before new work: read `{str_handoff_path}`; run `{str_resume_check}`. "
            f"If interrupted: `{str_resume_repair}`."
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

# 工作区边界由生成器直接拥有，所有受管根都必须继承且不能由画像关闭。
def workspace_boundary_rule() -> Rule:
    """构造受管根固定生成的工作区修改边界。

    参数:
        无外部业务参数；规则不读取项目画像开关。

    返回:
        包含工作区与外部写入授权边界的根级规则。
    """

    # 单条规则完整承载最低保护，避免多个画像分支产生不一致授权语义。
    return Rule(
        "workspace-boundary",  # 工作区边界稳定规则标识
        "Task-specific gates",  # 规则归属任务专用门禁章节
        "- **Workspace boundary:** current work folder; verified remote-server work folder. "
        "Changes inside either work folder require no additional confirmation; remote changes require the "
        "configured task route. Codebase-memory start, index refresh, rebuild, or recovery for either folder and "
        "its project cache/artifact also needs no additional confirmation. Necessary external reads are "
        "side-effect-free; every other external write requires one explicit confirmation naming the normalized "
        "target, action, scope, risks, alternatives, and recovery limits. Target/scope changes invalidate "
        "confirmation; installed-skill writes always need one.",  # 外部写入单次确认
        1,  # 最低保护应先于所有画像专用门禁输出
    )

# 任务专用门禁从完整 profile 中筛选高影响执行入口。
def task_specific_gates(profile: dict | None, project: Path) -> str:
    """生成会改变执行行为的仓库级阻断入口。

    参数:
        profile: 项目设计配置；为空时返回配置缺失提示。
        project: 用于生成仓库内治理命令的项目根目录。

    返回:
        按优先级去重后的任务专用门禁文本。
    """

    # 固定边界先进入候选集合，任何画像状态都不能关闭最低保护。
    list_base_rules = [
        workspace_boundary_rule(),  # 所有受管根共享的基础门禁
        remote_workspace_management_rule(profile),  # 所有状态共享的远程工作文件夹合同
        tester_worker_rule(),  # 唯一隔离测试智能体和单次授权合同
    ]

    # 未确认强控制时保留边界，并追加不能被误解为已完成治理的入口提示。
    if not profile:

        # 画像收集提示与固定边界通过同一规则渲染器排序和去重。
        list_base_rules.append(
            Rule(
                "agents-generation.profile-required",  # 无画像提示稳定标识
                "Task-specific gates",  # 提示仍归属于任务专用门禁
                "- AGENTS generation: collect a confirmed design profile before claiming "
                "strict controlled output.",  # 未配置画像时的事实停止线
                50,  # 固定边界之后再输出画像收集提示
            )
        )

        # 压缩流程必须保留完整固定边界和无画像提示。
        return compact_task_gate_text(render_rule_list(list_base_rules))

    # 目录聚合器同时返回远程规则所需的规范化目录合同。
    tuple_gate_context = directory_gate_rules(profile, project)  # 目录规则与合同二元组

    # 二元组首项是已构造的目录规则集合。
    list_rules = [  # 当前已聚合的根级规则
        *list_base_rules,  # 不可关闭的基础工作区边界
        *tuple_gate_context[0],  # 当前画像生成的目录规则
    ]

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

    # 读取注释、格式和语言路由策略。
    policy = dict_overrides.get(  # 编码行为策略
        "coding_behavior", {}  # 编码行为策略字段
    )  # 编码行为策略映射

    # 读取文件命名合同。
    dict_naming = dict_overrides.get("source_governance", {}).get(  # 文件命名治理配置
        "file_naming_gate", {}  # 文件命名门禁字段
    )

    # 保留注释质量规则。
    comment_quality = str(policy.get("comment_quality", "")).strip()  # 注释质量规则

    # 保留源码格式规则。
    formatting = str(policy.get("formatting", "")).strip()  # 源码格式规则

    # 读取原始语言路由。
    value_routing = policy.get("language_skill_routing", {})  # 原始语言技能路由

    # 非映射路由按空配置处理。
    routing = value_routing if isinstance(value_routing, dict) else {}  # 最终语言路由映射

    # 读取跨语言共同门禁。
    shared_route = str(routing.get("shared", "")).strip()  # 语言技能共同门禁

    # 读取 Python 最终所有权。
    python_route = str(routing.get("python", "")).strip()  # Python 技能路由规则

    # 读取脚本语言路由。
    script_route = str(routing.get("script", "")).strip()  # 脚本技能路由规则

    # 从 canonical routing contract 读取当前进程真实的四态安装路由。
    from routing_contract import build_language_skill_routes, readable_skill_is_installed

    # 配置文件保存默认合同，运行时安装事实决定实际可执行 owner。
    tuple_runtime_routes = build_language_skill_routes(  # 调用运行时路由构造器
        readable_skill_is_installed("readable-python-generator"),  # Python 技能安装事实
        readable_skill_is_installed("readable-script-generator"),  # 脚本技能安装事实
    )  # 当前进程的语言技能路由元组

    # 运行时路由覆盖配置默认值，供后续渲染保留真实所有权。
    shared_route, python_route, script_route = tuple_runtime_routes  # 当前安装路由

    # 初始化 AGENTS 编码行为行。
    list_lines = [
        f"- 编码行为配置来源：`{str_config_path}`；用户可手动修改该 JSON 后重新渲染。",  # 配置来源
        f"- 注释质量：{comment_quality}",  # 注释语义边界
        f"- {formatting}",  # 源码格式边界
    ]

    # 启用命名门禁时把代理执行所需的硬规则直接投影到根规则。
    if dict_naming.get("enabled"):

        # 长度值只从已验证配置读取，避免渲染器复制治理阈值。
        int_max_chars = dict_naming.get("max_stem_chars", 30)  # 文件名词干长度上限

        # 固定入口按配置顺序渲染为行内代码。
        str_exemptions = "、".join(  # Markdown 文件名列表
            f"`{str(item)}`" for item in dict_naming.get("exemptions", [])  # 按配置遍历例外。
        )

        # 命名语法规则追加到编码行为段落。
        list_lines.append(
            f"- 文件命名：除 {str_exemptions} 外，禁止数字和下划线开头；名称必须总结文件功能，"
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

    # 按配置顺序连接规则。
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
