"""把项目治理配置转换为 AGENTS.md 中可执行的精简规则。"""

# 根级门禁压缩已拆分到同目录模块，避免合同聚合分片超过源码尺寸门禁。
from pathlib import Path

# 合同渲染器依赖的规则压缩和 worker 配置来源。
from render_gate_compaction import compact_task_gate_text
from render_foundation import Rule
from tester_worker_profile import SINGLE_TASK_AUTHORIZATION_RECEIPT
from agent_platform import load_agent_config
from manage_worker_state import read_authorized_worker_states
from language_contract import canonical_language, default_language

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

# Codex-native 根只渲染显式 enabled worker 的授权状态。
def canonical_worker_state_rule(project: Path | None = None) -> Rule | None:
    """渲染 Codex-native 受管根的 enabled worker 状态行。

    参数：
        project: 可选目标工作文件夹；已有根文件的授权状态优先保留。
    返回：包含 enabled worker 状态行的 Rule；没有 enabled worker 时返回 None。
    """

    # 目标根存在时读取项目授权配置，缺失配置安全收敛为 disabled。
    path_project = Path(project).resolve() if project is not None else Path(".")  # 目标工作文件夹

    # 授权读取器从 protocol 和项目配置取得 canonical worker 状态。
    dict_states = read_authorized_worker_states(path_project)  # 当前项目的授权状态

    # 只保留显式 enabled 角色，disabled 角色不进入任何文档正文。
    dict_enabled_states = {
        str_worker: str_state  # 当前 enabled worker 状态
        for str_worker, str_state in dict_states.items()  # 遍历协议角色状态
        if str_state == "enabled"  # 仅选择显式授权角色
    }

    # 全部 disabled 时省略整个 worker 状态规则。
    if not dict_enabled_states:

        # 返回 None 让上层不加入空标题或角色名。
        return None

    # 状态行必须保持根级精确列表格式，供状态解析器唯一识别。
    list_state_lines = [
        f"- {str_worker}: {str_state}"  # 根级 worker 授权行。
        for str_worker, str_state in dict_enabled_states.items()  # 按协议顺序渲染 enabled 状态。
    ]

    # 头部和状态行合并成唯一的根级 worker 合同文本。
    str_text = "\n".join([  # 根级 worker 状态合同正文
        "- **Enabled canonical workers:** Codex-native managed roots render only "
        "roles explicitly authorized by project configuration.",
        *list_state_lines,  # 合并动态 worker 状态行
    ])

    # 状态合同只在 Codex-native 画像下由调用方加入根规则。
    return Rule("workers.root-state", "Task-specific gates", str_text, 8)

# 唯一 tester_worker 合同同时声明树哈希、命名和单次授权收据。
def tester_worker_rule() -> Rule:
    """渲染唯一 tester_worker、哈希自主确认和命名合同。

    参数：无。
    返回：可写入 Task-specific gates 的 Rule 对象。
    """

    # 根 AGENTS 必须指向唯一 TOML，不允许调用方临时替换测试智能体。
    str_text = (  # 唯一测试智能体合同正文
        "- **Unique TESTER:** only canonical `tester_worker` "
        "(the configured agent profile's worker file) owns tests/** writes, "
        "deletions, and runs; canonical `gardener_worker` may only list/read tests/** as design evidence; "
        "the main Agent and reviewer remain forbidden from reading tests/**; "
        "never delegate to a generic or second agent. No routine test-hash confirmation: the tester self-confirms "
        "only when its result agrees with the authoritative tests tree or receipt; report-only hash mismatch is "
        "corrected to the authoritative value; conflicting or insufficient provenance stops for user review without "
        "autonomous rerun. New tests use functional/behavioral semantic names, live under tests/<feature>/, have "
        "digit-free stems (including v1, v2, 1, 2, part1, part2), and do not belong in skills or other folders.\n"
        "- **Detailed failure receipt:** on RED, BLOCKED, or SCOPE_REJECTED, the tester must return a structured "
        "`failure_report`, never only `failed` or a failure count; it must include failure_stage, failure_kind, "
        "first_error, failure_summary, failure_count, complete failure_tests with expected/actual/observed/source, "
        "expected_actual, root_cause_class, minimal_fix, evidence with a traceability anchor, residual_jobs, and "
        "modification_status. Missing or vague fields are a record-blocking contract error.\n"
        f"- **Task authorization:** {SINGLE_TASK_AUTHORIZATION_RECEIPT}"
    )  # 唯一测试智能体合同文本

    # 唯一 worker 规则应紧随远程状态合同输出。
    return Rule("testing.unique-worker", "Task-specific gates", str_text, 9)

# 渲染只读 gardener 的触发、范围和删除候选边界。
def gardener_worker_rule() -> Rule:
    """渲染只读 gardener 的触发、范围和删除候选边界。

    参数：无。
    返回：可写入 Task-specific gates 的 Rule 对象。
    """

    # 根规则只保留执行所需的阻断入口，详细报告 schema 留在 skill 文档。
    str_text = (  # 只读 gardener 合同正文
        "- **Canonical gardener role:** after a new unreviewed local Git commit or changed managed-root `AGENTS.md` "
        "refresh, use the isolated read-only gardener (`fork_turns=none`) for tracked `.py`/`.md` under supplied "
        "source/tests roots; it may list/read tests/** only and never touches `dist`, `github`, root `docs`, "
        "`.agents`, `.git`, `.codebase-memory`, or `ref`. Its output is strict JSON; zero-call functions remain "
        "candidates until graph and tester evidence corroborate them; deletion or Markdown changes require review."
    )

    # gardener 规则必须与 tester 规则保持同一受管段落。
    return Rule("gardening.unique-worker", "Task-specific gates", str_text, 9)

# 渲染只读 reviewer 的启停来源、节拍和阻断边界。
def reviewer_worker_rule() -> Rule:
    """渲染只读 reviewer 的启停来源、节拍和阻断边界。

    参数:
        无。
    返回:
        reviewer_worker 的规则对象。
    """

    # 组织 reviewer 的生命周期检查和测试目录隔离合同。
    str_text = (
        "- **Canonical reviewer role:** use the isolated canonical reviewer unless root `AGENTS.md` declares "
        "`- reviewer_worker: disabled`; check the approved plan at INITIAL, every 10 minutes, CORRECTION, "
        "and FINAL. PERIODIC is the only non-blocking phase; reviewer is read-only and never accesses tests/**.\n"
        "- **Canonical authorization:** canonical reviewer_worker and gardener_worker are automatically authorized "
        "only for a managed Codex-native root with explicit enabled state and a matching event; they are not "
        "arbitrary subagents. Arbitrary solution/design/implementation/research roles require proactive "
        "current-task authorization. Missing state is `unconfigured` and blocks; runtime session state cannot "
        "authorize the role."
    )

    # 返回 reviewer 规则对象，供根 AGENTS 模板统一渲染。
    return Rule("reviewing.unique-worker", "Task-specific gates", str_text, 9)

# 会话完成合同固定工作闭环和自然语言默认值。
def conversation_completion_contract(profile: dict | None) -> str:
    """渲染开发会话的完成与阻塞报告合同。

    参数:
        profile: 可选项目配置，用于读取默认会话语言。

    返回:
        会话完成、验证和阻塞报告规则文本。
    """

    # profile 缺失时读取 catalog 的 conversation 默认值。
    str_catalog_language = default_language("conversation")  # catalog conversation 默认语言

    # profile 存在时优先读取显式会话语言配置。
    if profile:

        # 从 profile 读取会话语言，缺失字段仍使用 catalog 默认值。
        str_language_input = profile.get("default_conversation_language", str_catalog_language)  # 会话语言输入

    # profile 缺失时直接使用 catalog 默认值。
    else:

        # 保持无 profile 渲染路径的语言来源可追溯。
        str_language_input = str_catalog_language  # 无 profile 的会话语言输入

    # 旧别名通过 catalog 归一化，渲染器不保存中文旧值。
    str_default_language = canonical_language(str(str_language_input), "conversation")  # canonical 会话语言

    # 三条规则覆盖完成、语言和证据，不重复全局执行基线。
    return "\n".join([
        (
            f"- Natural-language replies, including `<proposed_plan>` content, use `{str_default_language}` "
            "unless the user switches languages; keep technical literals unchanged."
        ),
        "- Finish feasible requested work; preserve user changes and the directory contract.",
        (
            "- Run narrow then final checks; report blockers, completed files, assumptions, "
            "skipped checks, and next steps."
        ),
    ])
