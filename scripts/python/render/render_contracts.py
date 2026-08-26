"""把项目治理配置转换为 AGENTS.md 中可执行的精简规则。"""

# 根级门禁压缩已拆分到同目录模块，避免合同聚合分片超过源码尺寸门禁。
from pathlib import Path

# 合同渲染器依赖的规则压缩和 worker 配置来源。
from render_gate_compaction import compact_task_gate_text
from render_foundation import RELEASE_CORE_WORKTREE_RULE, Rule
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
# 从 render_remote_contracts 导入拆分后的公共合同函数。
from render_remote_contracts import (
    _remote_workspace_state,
    remote_workspace_management_rule,
    remote_upload_boundary_rule,
    remote_server_contract,
)

from render_remote_contracts import (
    remote_gate_rules,
    workspace_boundary_rule,
    fast_convergence_rule,
)

# 从 render_tester_contracts 导入拆分后的公共合同函数。
from render_tester_contracts import (
    canonical_worker_state_rule,
    tester_worker_rule,
    gardener_worker_rule,
    reviewer_worker_rule,
    conversation_completion_contract,
)
from manage_worker_state import canonical_worker_id, read_authorized_worker_states

# 从 render_project_contracts 导入拆分后的公共合同函数。
from render_project_contracts import (
    release_contract,
    git_management_text,
    engineering_rule_contract,
    skill_design_contract,
)

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
    dict_contract = (
        value_memory_contract if isinstance(value_memory_contract, dict) else {}  # 记忆合同映射
    )  # 规范化后的记忆合同映射

    # 标记 enabled 判断，控制 memory_contract 的分支走向。
    bool_enabled = bool(  # 兼容新旧记忆启用字段
        dict_contract.get("enabled", profile.get("memory_enabled", False))  # 新旧启用字段
    )  # 记忆功能启用状态

    # enabled 和旧版 memory_enabled 均未开启时跳过渲染。
    if not bool_enabled:

        # 禁用状态不公开记忆命令。
        return ""

    # 构造项目记忆指南的默认相对路径。
    str_default_guide = (Path("docs") / "memory" / "MEMORY.md").as_posix()  # 记忆指南默认路径

    # 指南路径指向项目记忆的人工入口。
    str_guide = dict_contract.get("guide", str_default_guide)  # 记忆指南路径

    # 后端名称让执行者知道权威数据形态。
    str_backend = dict_contract.get("storage_backend", "sqlite-plus-jsonl")  # 记忆存储后端

    # 读取策略控制新工作开始前需要加载的记忆范围，并压缩长版缺省文本。
    str_read_policy = dict_contract.get(  # 最终记忆读取策略
        "read_policy",  # 读取策略字段名
        "read latest handoff plus relevant docs/memory summaries before implementation",  # 缺省读取策略
    )  # 记忆读取策略

    # 已知缺省策略使用更紧凑但等价的表述。
    if str_read_policy == "read latest handoff plus relevant docs/memory summaries before implementation":

        # 压缩文本保持与详细缺省策略相同的执行语义。
        str_read_policy = (
            "latest handoff + relevant memory summaries before work"  # 精简读取策略
        )  # 根规则中的压缩读取策略

    # 敏感性策略明确禁止写入持久记忆的内容。
    str_sensitivity = dict_contract.get(  # 最终敏感信息策略
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
        f"- Root: `{dict_contract.get('folder', 'docs/memory')}`; guide: `{str_guide}`; backend: `{str_backend}`.",
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
    dict_contract = profile.get("docs_contract", {})  # 文档治理合同配置

    # handoff 子合同提供当前交接文件路径。
    dict_handoff = dict_contract.get("handoff", {})  # 交接文档配置

    # 目录管理子合同提供详细文档位置。
    dict_dir_manager = dict_contract.get("dir_manager", {})  # 目录治理文档配置

    # 构造当前 handoff 文档的默认相对路径。
    str_default_handoff = (Path("docs") / "handoff" / "HANDOFF.md").as_posix()  # handoff 默认路径

    # 当前 handoff 路径在开始与完成规则中复用。
    str_handoff_path = dict_handoff.get(  # 当前交接文档路径
        "current", str_default_handoff  # handoff 当前文件字段
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
        f"- Docs root: `{dict_contract.get('root', 'docs')}`; latest handoff is "
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
            f"- Dir manager details live in `{dict_dir_manager.get('folder', 'docs/dir_manager')}/`; "
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

    # 本地设置默认路径只从 workspace policy 读取，不猜测文件名。
    str_default_local_settings = ""  # 未配置时保持显式未配置状态

    # 本地设置文件缺省落在私有设置目录下。
    str_local_settings = str(  # 最终本地设置路径
        dict_settings.get(  # 本地设置文件配置
            "local_default_file", str_default_local_settings  # 本地设置配置值
        )
    ).strip()  # 本地设置文件

    # 远程设置默认路径只从 workspace policy 读取，不猜测文件名。
    str_default_remote_settings = ""  # remote policy 缺失时保持未配置而不猜测文件名

    # 远程设置文件与本地敏感配置保持分离。
    str_remote_settings = str(  # 最终远程设置路径
        dict_settings.get(  # 远程设置文件配置
            "remote_default_file", str_default_remote_settings  # 远程设置配置值
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
        f"`{str_settings_folder}/*.local.json` or other local-only files to remote servers."
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
                f"- **Project root:** primary project root `{str_primary_root}`; keep feature work inside it.",
                10,
            )
        )

    # 同时返回目录合同，避免通过 profile 写入临时渲染状态。
    return list_rules, dict_directory

# 仅 Codex 配置允许渲染三类 worker 合同。
def _codex_worker_rules_enabled(agent_profile: object | None = None) -> bool:
    """
    按本次解析的平台画像决定是否生成 Codex worker 合同。

    参数:
        agent_profile: 可选平台画像；为空时从当前技能配置读取。
    返回:
        当前平台是否声明 codex-native worker 支持。
    """

    # 已有平台画像优先，避免重复读取技能配置文件。
    if agent_profile is not None:

        # 渲染测试和兼容调用方可能以字典传入平台画像。
        if isinstance(agent_profile, dict):

            # 字典画像同样必须明确声明 Codex-native worker 支持。
            return agent_profile.get("worker_support", "unsupported") == "codex-native"

        # 只有明确声明 codex-native 才生成 worker 合同。
        return getattr(agent_profile, "worker_support", "unsupported") == "codex-native"

    # 无显式画像时定位当前技能根目录。
    path_skill_root = Path(__file__).resolve().parents[3]  # 当前技能配置根目录

    # 读取默认平台配置并判断 worker 支持能力。
    return load_agent_config(path_skill_root).worker_support == "codex-native"

# 组合所有画像状态都必须保留的基础任务门禁。
def _base_task_rules(
    profile: dict | None,
    agent_profile: object | None = None,
    project: Path | None = None,
) -> list[Rule]:
    """构造不受项目画像关闭影响的基础任务规则。

    参数:
        profile: 可选项目设计画像。
        agent_profile: 可选平台画像，用于决定是否加入 worker 合同。
        project: 可选目标工作文件夹，用于继承根级 worker 授权状态。
    返回:
        基础工作区、远程、测试、reviewer 和上传边界规则列表。
    """

    # 固定边界先进入候选集合，任何画像状态都不能关闭最低保护。
    list_base_rules = [  # 基础任务门禁集合。
        workspace_boundary_rule(),  # 所有受管根共享的基础门禁。
        fast_convergence_rule(),  # 所有受管根共享的快速收束门禁。
        remote_workspace_management_rule(profile),  # 远程工作文件夹合同。
        remote_upload_boundary_rule(),  # 逐项远程上传硬门禁。
    ]

    # 非 Codex 平台不声明不存在的 worker 运行时。
    if _codex_worker_rules_enabled(agent_profile):

        # 项目配置决定哪些 canonical worker 合同可以进入根文档。
        dict_worker_states = read_authorized_worker_states(project or Path("."))  # 项目 worker 授权状态

        # 先收集 enabled 角色对应的最小合同，disabled 角色完全省略。
        list_worker_rules: list[Rule] = []  # 当前启用角色的渲染规则

        # 状态规则只在至少一个角色显式 enabled 时出现。
        obj_state_rule = canonical_worker_state_rule(project)  # enabled worker 状态规则

        # 只有非空状态规则才需要加入根门禁集合。
        if obj_state_rule is not None:

            # 记录 enabled worker 的状态摘要，不写入 disabled 角色。
            list_worker_rules.append(obj_state_rule)

        # tester 合同只在 tester 角色显式 enabled 时渲染。
        if dict_worker_states.get(canonical_worker_id("tester")) == "enabled":

            # 插入唯一隔离测试智能体合同。
            list_worker_rules.append(tester_worker_rule())

        # 方案审查合同只接受 reviewer 的显式授权。
        if dict_worker_states.get(canonical_worker_id("reviewer")) == "enabled":

            # 插入唯一只读方案审查合同。
            list_worker_rules.append(reviewer_worker_rule())

        # 冗余审查合同只接受 gardener 的显式授权。
        if dict_worker_states.get(canonical_worker_id("gardener")) == "enabled":

            # 插入唯一只读冗余审查合同。
            list_worker_rules.append(gardener_worker_rule())

        # 在远程上传规则之前插入已授权角色合同。
        list_base_rules[3:3] = list_worker_rules  # 插入已授权角色合同

    # 未确认强控制时保留边界，并追加配置缺失停止线。
    if not profile:

        # 画像收集提示与固定边界通过同一规则渲染器排序和去重。
        list_base_rules.append(  # 画像缺失提示规则。
            Rule(
                "agents-generation.profile-required",  # 无画像提示稳定标识。
                "Task-specific gates",  # 提示所属章节。
                "- AGENTS generation: collect a confirmed design profile before claiming "
                "strict controlled output.",  # 未配置画像时的事实停止线。
                50,  # 固定边界之后再输出画像收集提示。
            )
        )

    # 返回所有必需的基础任务门禁。
    return list_base_rules

# 聚合画像启用时需要筛选的详细合同组。
def _task_contract_groups(
    profile: dict,
    project: Path,
    agent_profile: object | None = None,
) -> list[tuple[str, str, tuple[str, ...], int]]:
    """构造发布、工程、文档、记忆和 skill 合同筛选组。

    参数:
        profile: 已确认的项目设计画像。
        project: 当前项目根目录。
        agent_profile: 当前平台解析后的运行时画像。
    返回:
        合同文本、规则前缀、筛选片段和优先级组成的列表。
    """

    # 每个详细合同声明其根级筛选片段与优先级。
    return [
        (
            release_contract(profile, project),  # 发布合同文本。
            "release",  # 发布规则 ID 前缀。
            (
                "Install only",
                "Do not push",
                RELEASE_CORE_WORKTREE_RULE,
                "Release details live",
                "Different-version release",
            ),  # 发布阻断片段。
            20,  # 发布阻断规则优先级。
        ),
        (
            engineering_rule_contract(profile),  # 工程规则合同文本。
            "engineering",  # 工程规则 ID 前缀。
            ("Primary rule set:", "Mode:", "Do not paste full book rules"),  # 工程合同筛选片段。
            25,  # 工程规则优先级。
        ),
        (
            documentation_governance_contract(profile, project),  # 文档治理合同文本。
            "docs",  # 文档规则 ID 前缀。
            ("Before new work", "Start work", "Every completed"),  # 文档阻断片段。
            20,  # 文档治理优先级。
        ),
        (
            memory_contract(profile, project),  # 记忆合同文本。
            "memory",  # 记忆规则 ID 前缀。
            ("Root:", "Read ", "Gate with", "Historical", "Query with"),  # 记忆入口片段。
            30,  # 记忆规则优先级。
        ),
        (
            skill_design_contract(profile, project, agent_profile),  # Skill 设计合同文本。
            "skill",  # Skill 规则 ID 前缀。
            ("Validation gates:", "Forward testing:"),  # Skill 完成门禁片段。
            25,  # Skill 规则优先级。
        ),
    ]

# 任务专用门禁从完整 profile 中筛选高影响执行入口。
def task_specific_gates(
    profile: dict | None,
    project: Path,
    agent_profile: object | None = None,
) -> str:
    """生成会改变执行行为的仓库级阻断入口。

    参数:
        profile: 项目设计配置；为空时返回配置缺失提示。
        project: 用于生成仓库内治理命令的项目根目录。
        agent_profile: 可选平台画像，用于筛选 worker 相关合同。

    返回:
        按优先级去重后的任务专用门禁文本。
    """

    # 取得候选规则，不在此处重复展开基础边界。
    list_base_rules = _base_task_rules(profile, agent_profile, project)  # 规则聚合输入。

    # 未确认强控制时只压缩基础边界和配置缺失提示。
    if not profile:

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
                "- **Codebase memory MCP:** disabled; do not detect, configure, index, or query the graph; "
                "root `/.codebase-memory/` stays ignored.",
                5,
            )
        )

    # 同一筛选器保证各合同类别采用一致的根级压缩逻辑。
    for text, rule_prefix, fragments, priority in _task_contract_groups(
        profile,
        project,
        agent_profile,
    ):

        # 当前合同的阻断行追加到统一规则集合。
        list_rules.extend(
            filtered_contract_rules(text, rule_prefix, fragments, priority)
        )

    # 根文件只保留阻断条件和入口；完整命令手册留在其权威文档。
    return compact_task_gate_text(render_rule_list(list_rules))

# 将一条修改前阅读事实转换成稳定规则对象。
def _append_read_rule(
    list_rules: list[Rule],
    str_rule_id: str,
    str_line: str,
    int_priority: int,
) -> None:
    """向修改前阅读规则列表追加一条事实。

    参数:
        list_rules: 接收规则对象的列表。
        str_rule_id: 规则稳定标识。
        str_line: 规则正文。
        int_priority: 规则排序优先级。
    返回:
        None；规则直接追加到 list_rules。
    """

    # 统一使用同一章节名称和优先级协议构造规则。
    list_rules.append(  # 追加一条修改前阅读规则。
        Rule(str_rule_id, "Read before changing", str_line, int_priority)
    )

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
        _append_read_rule(
            list_rules,
            f"read.decisions.{index}",
            str_line,
            READ_RULE_CONFIG["decisions_priority"],
        )

    # 自动化脚本、质量配置和平台文件帮助代理复用现有入口。
    for index, str_line in enumerate(codebase_state(context).splitlines()):

        # 项目状态行在架构决策之后输出。
        _append_read_rule(
            list_rules,
            f"read.state.{index}",
            str_line,
            READ_RULE_CONFIG["state_priority"],
        )

    # hook 和 GitHub 设置只有被发现时才输出。
    for index, str_line in enumerate(hook_policy(context).splitlines()):

        # 钩子规则提醒修改者复用现有提交治理。
        _append_read_rule(
            list_rules,
            f"read.hooks.{index}",
            str_line,
            READ_RULE_CONFIG["hooks_priority"],
        )

    # GitHub 设置作为平台侧治理入口单独排列。
    for index, str_line in enumerate(github_settings(context).splitlines()):

        # 平台规则与本地钩子使用相同优先级。
        _append_read_rule(
            list_rules,
            f"read.github.{index}",
            str_line,
            READ_RULE_CONFIG["hooks_priority"],
        )

    # 目录覆盖提示在具体工具和样例之后生效。
    for index, str_line in enumerate(directory_coverage(context).splitlines()):

        # 缺少局部规则的目录以最低优先级提示。
        _append_read_rule(
            list_rules,
            f"read.directory.{index}",
            str_line,
            READ_RULE_CONFIG["directory_priority"],
        )

    # 真实 utilities 和 golden samples 以普通 bullet 形式写入，避免裸表格行。
    for index, str_path in enumerate(context.get("utilities", [])[:READ_RULE_CONFIG["utility_limit"]]):

        # 工具入口提醒代理先阅读现有自动化实现。
        list_rules.append(Rule(
            f"read.utility.{index}",
            "Read before changing",
            f"- Inspect existing automation `{str_path}` before adding new project "
            "tooling.",
            READ_RULE_CONFIG["state_priority"],
        ))

    # 黄金样例提供最接近的实现与测试模式。
    for index, str_path in enumerate(context.get("golden_samples", [])[:READ_RULE_CONFIG["sample_limit"]]):

        # 样例规则避免代理在已有模式时重新发明结构。
        list_rules.append(Rule(
            f"read.sample.{index}",
            "Read before changing",
            f"- Use `{str_path}` as the nearest implementation/test pattern before "
            "inventing a new one.",
            READ_RULE_CONFIG["state_priority"],
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
    dict_policy = dict_overrides.get(  # 编码行为策略
        "coding_behavior", {}  # 编码行为策略字段
    )  # 编码行为策略映射

    # 语言路由文案从当前治理配置读取，避免渲染器复制业务规则枚举。
    dict_language_routes = dict_policy.get("language_skill_routing", {})  # 语言技能路由配置

    # 非对象配置按空覆盖处理，继续使用受管默认路由。
    if not isinstance(dict_language_routes, dict):

        # 保持渲染入口对旧配置的兼容，并在验证阶段报告配置缺口。
        dict_language_routes = {}  # 缺失路由配置的安全回退

    # 读取文件命名合同。
    dict_naming = dict_overrides.get("source_governance", {}).get(  # 文件命名治理配置
        "file_naming_gate", {}  # 文件命名门禁字段
    )

    # 保留注释质量规则。
    comment_quality = str(dict_policy.get("comment_quality", "")).strip()  # 注释质量规则

    # 保留源码格式规则。
    str_formatting = str(dict_policy.get("formatting", "")).strip()  # 源码格式规则

    # 渲染正文保留 verifier 需要的最小注释与单行压缩合同，即使旧配置缺少兼容短语。
    str_required_comment = "Comments must explain"  # 注释最小合同

    # 缺失兼容短语时才扩展当前配置文本。
    if str_required_comment not in comment_quality:

        # 追加兼容短语而不覆盖用户配置的其他注释策略。
        comment_quality = f"{comment_quality}; {str_required_comment}".strip("; ")  # 兼容后的注释规则

    # 评估和根合同都要求显式禁止未经要求的批量 AI 注释。
    str_batch_comment_rule = "without explicit request"  # 批量注释禁止合同

    # 缺少批量注释禁止语义时追加稳定的 exact-fragment。
    if str_batch_comment_rule not in comment_quality:

        # 只补充缺失门禁，不改写配置提供的其他注释策略。
        comment_quality = f"{comment_quality}; {str_batch_comment_rule}".strip("; ")  # 补齐批量注释禁止规则

    # 格式策略同样必须公开不可压缩代码的稳定短语。
    if "compress code into one line" not in str_formatting:

        # 仅补齐缺失硬门禁，不改变现有格式策略正文。
        str_formatting = f"{str_formatting}; compress code into one line".strip("; ")  # 兼容后的格式规则

    # 技能项目开发强制保留双技能门禁；普通项目仍按真实安装态渲染。
    str_profile_kind = str(  # 当前 profile 的项目类型
        (profile or {}).get(  # 读取标准项目类型字段
            "kind",  # 标准项目类型键
            (profile or {}).get("development_type", ""),  # 兼容设计档案类型字段
        )
    ).strip().lower()

    # 检查 profile 是否声明了 Skill 专属设计合同。
    bool_has_skill_contract = bool(  # Skill 合同存在性
        (profile or {}).get("skill_design_contract")  # Skill 设计合同字段
    )  # Skill 合同存在状态

    # 具备 Skill 类型或 Skill 合同配置时使用严格双技能投影。
    bool_skill_project = str_profile_kind == "skill" or bool_has_skill_contract  # 技能项目判定结果

    # 技能项目同样由结构化 route records 生成三条唯一语言合同。
    if bool_skill_project:

        # Skill 也显式声明两个 owner 可用，避免回到旧版字符串 fallback。
        tuple_language_routes: tuple[str, str, str] = build_language_skill_routes(  # Skill 项目的三条语言路由。
            True,  # Skill 项目启用 Python owner。
            True,  # Skill 项目启用脚本 owner。
            dict_language_routes,  # 当前 profile 的结构化路由覆盖。
        )

        # 共同门禁路由控制两个 readable 技能的前置加载要求。
        str_shared_route: str = tuple_language_routes[0]  # Skill 项目的共同语言门禁。

        # Python 路由固定 Python 代码的最终 owner。
        str_python_route: str = tuple_language_routes[1]  # Skill 项目的 Python 所有权路由。

        # 脚本路由固定六类脚本目标的最终 owner。
        str_script_route: str = tuple_language_routes[2]  # Skill 项目的脚本所有权路由。

    # 普通项目根据当前安装态生成可执行路由。
    else:

        # 检查 Python 可读性技能是否实际安装。
        bool_python_installed = readable_skill_is_installed("readable-python-generator")  # Python 技能安装状态

        # 查询本地是否具备脚本路由的实际实现。
        bool_script_installed = readable_skill_is_installed("readable-script-generator")  # 本地脚本技能可用标志

        # 按两个安装状态生成共同门禁及各自语言路由。
        str_shared_route, str_python_route, str_script_route = build_language_skill_routes(  # 普通项目路由三项结果
            bool_python_installed,  # 路由构建器收到的 Python 可用性
            bool_script_installed,  # 路由构建器收到的脚本可用性
            dict_language_routes,  # 当前项目治理路由文案
        )  # 当前安装态路由三元组

    # 初始化 AGENTS 编码行为行。
    list_lines = [
        f"- Coding behavior source: `{str_config_path}`; edit the JSON and rerender when policy changes.",  # 配置来源
        f"- Comment quality: {comment_quality}",  # 注释语义边界
        f"- Formatting: {str_formatting}",  # 源码格式边界
    ]

    # 启用命名门禁时把代理执行所需的硬规则直接投影到根规则。
    if dict_naming.get("enabled"):

        # 长度值只从已验证配置读取，避免渲染器复制治理阈值。
        int_max_chars = dict_naming.get("max_stem_chars", 30)  # 文件名词干长度上限

        # 固定入口按配置顺序渲染为行内代码。
        str_exemptions = ", ".join(  # Markdown 文件名列表
            f"`{str(item)}`" for item in dict_naming.get("exemptions", [])  # 按配置遍历例外。
        )

        # 命名语法规则追加到编码行为段落。
        list_lines.append(
            f"- File naming: names except {str_exemptions} must not start with digits "
            f"or underscores; names must describe their function and stay within "
            f"{int_max_chars} English characters."
        )

        # 语义复核不能由正则替代，必须保留独立 Agent 判断证据。
        if dict_naming.get("semantic_review_required"):

            # 独立规则明确正则检查之外的 Agent 责任。
            list_lines.append(
                "- File naming semantics: changed files require Agent semantic review "
                "with matching revision and path-hash evidence."
            )

    # 仅在配置存在时输出共同门禁，避免空标题进入根规则。
    if str_shared_route:

        # 共同门禁追加一次，后续语言路由不得重复该正文。
        list_lines.append(f"- Shared language-skill gate: {str_shared_route}")

    # 仅在配置存在时输出 Python 路由，避免空规则。
    if str_python_route:

        # Python 路由追加在通用编码行为规则之后。
        list_lines.append(f"- Language-skill route (Python): {str_python_route}")

    # 脚本路由独立判断，允许项目只配置一种语言族。
    if str_script_route:

        # 脚本路由作为编码行为段落的最后一项。
        list_lines.append(f"- Language-skill route (scripts): {str_script_route}")

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
    dict_policy = load_global_rule_overrides(project, profile)["data"].get(  # 脚本输出策略
        "script_output_policy", {}  # 脚本输出策略字段
    )  # 脚本输出策略映射

    # 非映射格式配置按空映射处理并使用安全缺省值。
    value_formats = dict_policy.get("format", {})  # 原始输出格式配置

    # 格式配置类型异常时采用各通道缺省前缀。
    dict_formats = value_formats if isinstance(value_formats, dict) else {}  # 最终输出格式映射

    # Python 子策略控制过程性 INFO 的静默开关。
    value_python_policy = dict_policy.get("python", {})  # 原始 Python 输出策略

    # Python 输出配置类型异常时使用 quiet 缺省约定。
    dict_python_policy = (  # 最终 Python 输出策略
        value_python_policy if isinstance(value_python_policy, dict) else {}  # Python 输出映射
    )  # 规范化 Python 输出策略

    # 过程性日志前缀来自治理 JSON，渲染时只做默认值兜底。
    str_info_prefix = dict_formats.get("info", "> INFO: [{kind}]")  # INFO 日志前缀模板

    # 非致命问题沿用策略配置中的 warning 格式。
    warning_prefix = dict_formats.get("warning", "> WARNING: [{kind}]")  # 可恢复风险消息格式

    # 阻断失败采用 error 格式并保留动态 Kind。
    str_error_prefix = dict_formats.get("error", "> ERR: [{kind}]")  # 阻断失败消息格式

    # quiet 开关来自 Python 输出策略，缺省沿用脚本约定。
    str_quiet_flag = dict_python_policy.get("quiet_flag", "--quiet")  # Python 静默开关文本

    # 输出合同同时说明配置来源和各通道行为。
    return "\n".join([
        (
            f"- Configuration source: `{str_config_path}`; the `Kind` catalog is read "
            "from this JSON and must not be embedded in code."
        ),
        (
            f"- "
            f"Format: `{str_info_prefix}`, `{warning_prefix}`, `{str_error_prefix}`; Python "
            f"process INFO is enabled by default, `{str_quiet_flag}` disables "
            f"INFO/progress, WARNING and ERR remain visible, and machine-readable output has no prefix."
        ),
    ])
