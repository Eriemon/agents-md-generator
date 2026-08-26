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

# 发布合同聚合分支、安装来源、历史包和推送限制。
from agents_common import RELEASE_CORE_WORKTREE_RULE

# 生成发布合同时固定分支与工作树管理边界。
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
    dict_policy = profile.get("git_branch_policy", {})  # 项目 Git 分支策略

    # 缺省保护主分支和发布分支，避免生成宽松合同。
    list_protected = dict_policy.get("protected_branches", ["master", "release"])  # 受保护分支名称

    # Markdown 代码样式让分支名称在规则文本中保持清晰。
    protected_text = ", ".join(f"`{item}`" for item in list_protected)  # 渲染后的分支列表

    # 指向当前仓库存在的脚本指南；外部项目只保留安装版指南描述，避免虚构本地路径。
    path_script_guide = (
        project / "skills" / "agents-md-generator" / "references" / "script-guide.md"  # 仓库内指南组成路径
    )  # 仓库内脚本指南候选路径

    # 最终指南文本在源码路径和安装版引用之间选择。
    str_script_guide = (  # 最终脚本指南引用文本
        (Path("skills") / "agents-md-generator" / "references" / "script-guide.md").as_posix()  # 源码仓库内指南引用
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
    dict_contract = profile.get("engineering_rule_contract", {})  # 工程规则合同配置

    # 主规则集缺失时明确渲染 none。
    str_primary = dict_contract.get("primary", "none")  # 主工程规则集

    # 模式描述规则集如何参与代理决策。
    str_mode = dict_contract.get("mode", "none")  # 工程规则启用模式

    # 作用域限制工程规则影响的任务范围。
    str_scope = dict_contract.get("scope", "on-demand")  # 工程规则适用范围

    # 汇总 lines，作为 AGENTS 受管段落拼装顺序。
    list_lines = [
        f"- Primary rule set: {str_primary}.",  # 当前主工程规则集
        f"- Mode: {str_mode}.",  # 工程规则运行模式
        f"- Scope: {str_scope}.",  # 工程规则作用范围
        f"- Compatibility: {dict_contract.get('compatibility_policy', 'one primary active rule set')}.",  # 规则集兼容策略
        f"- Compression: {dict_contract.get('compression_policy', 'keep only decision-changing rules')}.",  # 规则压缩策略
        "- Do not paste full book rules into AGENTS.md. Keep full book rules reference-only.",  # 完整材料引用边界
    ]

    # 可选备注只在配置存在时追加，避免空行噪声。
    value_notes = dict_contract.get("notes")  # 工程规则补充说明

    # 备注作为最后一条规则，不改变核心字段顺序。
    if value_notes:

        # 追加 engineering_rule_contract 的 AGENTS 渲染行。
        list_lines.append(f"- Notes: {value_notes}.")

    # 聚合后的文本直接进入任务专用门禁段落。
    return "\n".join(list_lines)

# Skill 项目需要额外公开触发、资源和验证边界。
def skill_design_contract(
    profile: dict | None,
    project: Path,
    agent_profile: object | None = None,
) -> str:
    """渲染 Codex Skill 的设计与验证合同。

    参数:
        profile: 项目设计配置；非 Skill 项目不会输出该合同。
        project: 当前项目根目录，保留给路径相关合同扩展使用。
        agent_profile: 本次解析的平台画像，用于决定 Codex worker 规则是否可见。

    返回:
        Skill 触发、资源、渐进披露和验证规则文本。
    """

    # 该合同只适用于明确标记为 Skill 的项目。
    if not profile or profile.get("kind") != "skill":

        # 普通项目不渲染 Skill 专属规则。
        return ""

    # Skill 合同提供触发、资源和验证策略。
    dict_contract = profile.get("skill_design_contract", {})  # Skill 设计合同配置

    # patterns 同时兼容既有字符串和结构化列表格式。
    patterns = dict_contract.get("patterns", [])  # Skill 设计模式配置

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
    validation_method = dict_contract.get(  # 最终验证方法
        "validation_method",  # Skill 合同验证方法字段
        profile.get("validation_method", "not specified"),  # 项目级验证方法回退
    )  # Skill 验证方法

    # Skill 合同优先覆盖项目级验证粒度。
    str_validation_granularity = dict_contract.get(  # 最终验证粒度
        "validation_granularity",  # Skill 合同验证粒度字段
        profile.get("validation_granularity", "not specified"),  # 项目级验证粒度回退
    )  # Skill 验证粒度

    # 空白前向测试策略回退为明确的未配置文本。
    str_forward_policy = (
        str(dict_contract.get("forward_testing_policy", "not specified")).strip()  # 原始前向测试策略
        or "not specified"  # 空策略的显式回退值
    )  # 前向测试策略

    # Skill 设计字段按执行流程顺序输出。
    list_lines = [
        f"- Trigger scenarios: {dict_contract.get('trigger_scenarios', 'not specified')}.",  # 触发场景
        f"- Design patterns: {patterns_text or 'not specified'}.",  # 设计模式
        f"- Resource boundaries: {dict_contract.get('resource_plan', 'not specified')}.",  # 资源边界
        f"- Progressive disclosure: {dict_contract.get('progressive_disclosure_policy', 'not specified')}.",  # 渐进披露策略
        f"- Validation gates: {dict_contract.get('validation_gates', 'not specified')}.",  # 验证门禁
        f"- Forward testing: {str_forward_policy}.",  # 前向测试要求
        f"- Validation method: {validation_method}; granularity: {str_validation_granularity}.",  # 验证方法与粒度
        f"- Reference material policy: {dict_contract.get('reference_material_policy', 'temporary inputs only')}.",  # 参考材料保留策略
    ]

    # Skill 合同字段按声明顺序拼装为 Markdown 列表。
    return "\n".join(list_lines)
