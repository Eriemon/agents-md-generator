"""把项目治理配置转换为 AGENTS.md 中可执行的精简规则。"""

# 根级门禁压缩已拆分到同目录模块，避免合同聚合分片超过源码尺寸门禁。
from pathlib import Path

# 合同渲染器依赖的规则压缩和 worker 配置来源。
from render_gate_compaction import compact_task_gate_text
from render_foundation import Rule
from tester_worker_profile import SINGLE_TASK_AUTHORIZATION_RECEIPT
from agent_platform import load_agent_config

# 双技能路由由独立合同模块提供，渲染器只消费其真实安装态结果。
from routing_contract import (
    DEFAULT_LANGUAGE_SKILL_ROUTING_PYTHON,
    DEFAULT_LANGUAGE_SKILL_ROUTING_SCRIPT,
    DEFAULT_LANGUAGE_SKILL_ROUTING_SHARED,
    build_language_skill_routes,
    readable_skill_is_installed,
)

# 修改前阅读规则的稳定优先级和样例数量上限。
READ_RULE_CONFIG = {  # 修改前阅读规则配置。
    "decisions_priority": 20,  # 决策文档最高优先级。
    "state_priority": 40,  # 项目状态普通优先级。
    "hooks_priority": 30,  # hook 与平台治理优先级。
    "directory_priority": 50,  # 目录覆盖提示优先级。
    "utility_limit": 6,  # 最多读取六个工具入口。
    "sample_limit": 4,  # 最多读取四个黄金样例。
}

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

    # 固定合同同时覆盖状态感知、精确路由和规划结构生命周期。
    str_state = _remote_workspace_state(profile)  # 可审计远程状态标签

    # 规则正文保持固定语义，避免四种画像状态出现漂移。
    str_text = (  # 远程工作文件夹合同正文
        "- **Remote workspace management:** state-aware/fail-closed; before remote file operations resolve the "
        "exact task route and verified workspace, stopping unmatched or unverified states. Keep deployment, "
        "conda/runtime, backup, and archive lifecycle details in `docs/dir_manager/planned_structure.json`; "
        f"remote workspace state: {str_state}."
    )  # 远程合同固定正文

    # 低优先级让工作区和唯一测试智能体规则先于普通合同输出。
    return Rule("remote.workspace-management", "Task-specific gates", str_text, 8)

# 渲染所有根 AGENTS 必须具备的逐项远程上传硬门禁。
def remote_upload_boundary_rule() -> Rule:
    """渲染所有根 AGENTS 必须具备的逐项远程上传硬门禁。

    参数:
        无。
    返回:
        远程逐项上传边界规则对象。
    """

    # 组织 manifest-only、禁传路径和强制覆盖禁止绕过合同。
    str_text = (
        "- **Remote upload boundary:** manifest-only; never upload, mirror, archive, "
        "or recursively package the work folder; "
        "`.git/`, `git/`, `github/`, `dist/`, `ref/`, and archive formats are forbidden. "
        "Transfer only named files or narrow directories required by the verified "
        "remote workspace contract; list runtime artifacts separately and prove "
        "that no workspace copy or forbidden path is included. Renaming, copying, "
        "repackaging, and confirmation bypasses are forbidden."
    )

    # 返回远程上传边界规则对象，供根 AGENTS 模板复用。
    return Rule("remote.upload-boundary", "Task-specific gates", str_text, 7)

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
    dict_contract = profile.get("remote_server_contract", {})  # AGENTS 受管段落渲染输入值

    # 缺少远程合同配置时保持对应受管段落为空。
    if not dict_contract:

        # 空字符串让上层聚合器自然跳过该合同。
        return ""

    # 显式 enabled 开关决定是否公开远程路由规则。
    if not dict_contract.get("enabled"):

        # 关闭状态不应向 AGENTS.md 泄露未启用配置。
        return ""

    # 返回 compact 入口规则，完整 registry 和 route 表只保留在机器可读 profile。
    return "\n".join([
        "- Remote server usage: enabled.",
        "- Route source: `.agents/agents-control.json` field `remote_server_contract`.",
        "- Resolve primary and fallback servers from the route source at execution time; do not copy registry, "
        "runner, or absolute remote paths into root AGENTS.md.",
        "- If the matched primary remote server fails `check` or `workspace-check`, "
        "automatically try registered fallback servers in route order.",
        "- If no registered task route matches the requested task, stop and update the current work folder "
        "AGENTS.md/profile before continuing; stop unmatched tasks until agents.md/profile is updated.",
        "- If the user wants a different task-to-server mapping, update the profile "
        "through agents-md-generator first; do not bypass the route table ad hoc.",
    ])

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

    # 单条规则完整承载最低保护，避免画像分支产生不一致授权语义。
    return Rule(
        "workspace-boundary",  # 工作区边界稳定规则标识
        "Task-specific gates",  # 规则归属任务专用门禁章节
        "- **Workspace boundary:** current work folder; verified remote-server work folder. "
        "Changes inside either work folder require no additional confirmation; remote changes remain allowed only "
        "when the configured task route matches that folder. "
        "Official codebase-memory start, index refresh, rebuild, or recovery for the project bound to either work "
        "folder, including its configured runtime cache and root persistence artifact, also requires no additional "
        "confirmation. External reads beyond those boundaries must be necessary and side-effect-free. "
        "Every other external write is prohibited by default; only after the user proactively and explicitly "
        "requests the exact action. Disclose exact normalized target, action, scope, risks, alternatives, and "
        "recovery limits; obtain exactly one explicit user confirmation. Any target or scope change invalidates "
        "that confirmation. installed skill always requires exactly one explicit user confirmation. "
        "Routine test-hash confirmation is prohibited. The agent may confirm when an authoritative current tests "
        "result agrees with the authoritative current tests tree or receipt. A report-only hash mismatch is "
        "corrected to the authoritative value. Conflicting or insufficient provenance stops for user review "
        "without an autonomous rerun.",
        1,  # 最低保护应先于所有画像专用门禁输出
    )

# 快速收束规则约束昂贵门禁、长任务观测和并行测试边界。
def fast_convergence_rule() -> Rule:
    """构造所有受管根必须执行的快速收束规则。

    参数:
        无外部业务参数；规则不依赖项目画像开关。

    返回:
        包含候选冻结、挂起诊断和有界并行约束的根级规则。
    """

    # 单条规则覆盖昂贵验证的启动、等待、重试和并行回退边界。
    return Rule(
        "execution.fast-convergence",  # 快速收束规则稳定标识
        "Task-specific gates",  # 快速收束只进入任务专用门禁章节
        "- **Fast convergence:** freeze candidate; run narrow checks then one full suite after source/governance "
        "settle. Never repeat unchanged failing/hanging commands without evidence. Long tasks require bounded "
        "timeout plus heartbeat/status/log/artifact or receipt signals; timeout/missing receipt blocks. Inspect "
        "residual jobs before retry. Parallelize independent tests only after proving isolation with bounded "
        "workers; preserve one receipt; serial shared state.",
        2,  # 快速收束紧随工作区边界输出
    )
