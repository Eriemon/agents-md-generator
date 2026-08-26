"""承载 worker dispatch 的 session 创建、复用和启动幂等逻辑。"""

# 延迟解析类型注解，保持事件 shard 与 Python 3.10 运行时兼容。
from __future__ import annotations

# 动态 gardener 模块规格需要标准库的显式类型收窄。
from typing import cast

# 事件与 receipt shard 共享同一份低层 session 和合同实现。
try:

    # 包内入口先导入事件路由需要的标准类型。
    from .worker_dispatch_shared import (
        Any,
        Callable,
        Iterable,
        ModuleSpec,
        ModuleType,
        Path,
    )

    # 包内入口再导入生命周期常量。
    from .worker_dispatch_shared import (
        DEFAULT_REVIEW_INTERVAL_SECONDS,
        CANONICAL_WORKER_IDS,
        EVENT_BY_PHASE,
        EVENT_BY_ROLE,
        EVENT_TYPES,
        PHASE_BY_ROLE,

        # worker 合同查询函数提供 reviewer 的阻断状态集合。
        worker_blocking_verdicts,
        SCHEMA_VERSION,
        TASK_MODES,
        WORKER_NAMES,
    )

    # 包内入口显式列出 session 和 envelope 辅助函数。
    from .worker_dispatch_shared import (
        _authorized,
        _bound_session,
        _envelope,
        _new_session,
        _require_monotonic,
    )

    # 包内入口分组导入摘要和持久化辅助函数。
    from .worker_dispatch_shared import (
        _require_sha256,
        _runtime_gate,
        _session_path,
        _sha256_text,
        _write_session,
    )

    # 包内入口最后导入事件摘要、审核策略和运行时模块。
    from .worker_dispatch_shared import (
        build_event_id,
        importlib,
        reviewer_trigger_decision,
        sys,
        validate_worker_states,
        zero_dispatch_verdict,
    )

# 脚本入口没有 package context 时回退到同目录 shared shard。
except ImportError:

    # 同目录入口先导入事件路由需要的标准类型。
    from worker_dispatch_shared import (
        Any,
        Callable,
        Iterable,
        ModuleSpec,
        ModuleType,
        Path,
    )

    # 同目录入口再导入生命周期常量。
    from worker_dispatch_shared import (
        DEFAULT_REVIEW_INTERVAL_SECONDS,
        CANONICAL_WORKER_IDS,
        EVENT_BY_PHASE,
        EVENT_BY_ROLE,
        EVENT_TYPES,
        PHASE_BY_ROLE,

        # fallback 入口复用同一 reviewer 阻断状态集合。
        worker_blocking_verdicts,
        SCHEMA_VERSION,
        TASK_MODES,
        WORKER_NAMES,
    )

    # 同目录入口显式列出 session 和 envelope 辅助函数。
    from worker_dispatch_shared import (
        _authorized,
        _bound_session,
        _envelope,
        _new_session,
        _require_monotonic,
    )

    # 同目录入口分组导入摘要和持久化辅助函数。
    from worker_dispatch_shared import (
        _require_sha256,
        _runtime_gate,
        _session_path,
        _sha256_text,
        _write_session,
    )

    # 同目录入口最后导入事件摘要、审核策略和运行时模块。
    from worker_dispatch_shared import (
        build_event_id,
        importlib,
        reviewer_trigger_decision,
        sys,
        validate_worker_states,
        zero_dispatch_verdict,
    )

# canonical worker id 由 protocol 映射决定，所有事件路由复用这些稳定键。
REVIEWER_WORKER_ID: str = CANONICAL_WORKER_IDS.get("reviewer", "")  # reviewer 状态和 target 的索引键。

# tester 串行 target 使用 protocol 声明的稳定身份键。
TESTER_WORKER_ID: str = CANONICAL_WORKER_IDS.get("tester", "")  # tester 串行 target 的索引键。

# gardener 只读审查使用 protocol 声明的稳定身份键。
GARDENER_WORKER_ID: str = CANONICAL_WORKER_IDS.get("gardener", "")  # gardener 只读审查的索引键。

# lifecycle 阶段和事件名称均由 protocol 的角色映射派生。
PERIODIC_PHASE: str = PHASE_BY_ROLE.get("periodic", "")  # reviewer 周期复核阶段。

# 初始事件对应 reviewer 的首次复核阶段。
INITIAL_PHASE: str = PHASE_BY_ROLE.get("initial", "")  # reviewer 初始复核阶段。

# correction 阶段保证 tester failure 后先经过 reviewer 修正授权。
CORRECTION_PHASE: str = PHASE_BY_ROLE.get("correction", "")  # reviewer 修正复核阶段。

# final 阶段是实现完成前的最后 reviewer 门禁。
FINAL_PHASE: str = PHASE_BY_ROLE.get("final", "")  # reviewer 最终复核阶段。

# 初始事件由 protocol 的阶段反向映射确定。
INITIAL_EVENT: str = EVENT_BY_PHASE.get(INITIAL_PHASE, "")  # 初始复核事件名。

# 周期事件由 protocol 的阶段反向映射确定。
PERIODIC_EVENT: str = EVENT_BY_PHASE.get(PERIODIC_PHASE, "")  # 周期复核事件名。

# correction 事件由 protocol 的阶段反向映射确定。
CORRECTION_EVENT: str = EVENT_BY_PHASE.get(CORRECTION_PHASE, "")  # 修正复核事件名。

# FINAL 阶段对应的事件由 protocol 反向映射确定。
FINAL_EVENT: str = EVENT_BY_PHASE.get(FINAL_PHASE, "")  # 最终复核事件名。

# 角色事件和状态集合控制三个 dispatcher 的路由边界。
REVIEWER_BLOCKING_VERDICTS: frozenset[str] = worker_blocking_verdicts(REVIEWER_WORKER_ID)  # reviewer 未解决阻断结论。

# commit 事件表示提交后需要 gardener 只读整理。
COMMIT_EVENT: str = EVENT_BY_ROLE.get("commit", "")  # 提交后触发 gardener 的事件名。

# AGENTS 刷新事件表示治理文件变更后的 gardener 整理。
AGENTS_REFRESH_EVENT: str = EVENT_BY_ROLE.get("agents_refresh", "")  # AGENTS 刷新后触发 gardener 的事件名。

# control boundary 事件驱动 reviewer 周期和序号校验。
CONTROL_BOUNDARY_EVENT: str = EVENT_BY_ROLE.get("control_boundary", "")  # 周期控制边界事件名。

# tester 事件集合只接受 protocol 声明的 TEST_ 前缀事件。
TEST_EVENTS: frozenset[str] = frozenset(  # tester 生命周期事件集合。
    str_event for str_event in EVENT_TYPES if str_event.startswith("TEST_")  # 筛出配置声明的 tester 事件。
)

# reviewer 事件集合覆盖四个阶段，排除 tester 和 gardener 路由。
REVIEW_EVENTS: frozenset[str] = frozenset(  # reviewer dispatcher 只从这四类事件创建派发项。
    {INITIAL_EVENT, PERIODIC_EVENT, CORRECTION_EVENT, FINAL_EVENT}  # 汇总四个 reviewer 阶段事件。
)

# gardener 事件集合仅覆盖提交和治理刷新两个来源。
GARDENER_EVENTS: frozenset[str] = frozenset(  # gardener 触发事件集合。
    {COMMIT_EVENT, AGENTS_REFRESH_EVENT}  # 汇总提交和治理刷新事件。
)

# session 初始化复用角色路由的低层结果和派发动作。
try:
    from .worker_dispatch_event_routing import (
        _dispatch_item,
        _reviewer_dispatch,
        _result,
    )

# 脚本入口回退到同目录的角色路由 shard。
except ImportError:
    from worker_dispatch_event_routing import (
        _dispatch_item,
        _reviewer_dispatch,
        _result,
    )

# session 启动事件使用该相对路径字段返回可复核的状态位置。
WORKER_SESSION_STATE_PATH: Path = Path(".agents") / "worker-session.json"  # worker session 状态相对路径。

# 登记事件摘要并拒绝同一 session 的重复触发。
def _remember_event(
    dict_session: dict[str, Any],
    str_event_type: str,
    str_event_id: str,
) -> bool:
    """记录事件去重信息。

    参数:
        dict_session 为当前 session；str_event_type 为事件类型；str_event_id 为事件摘要。
    返回:
        首次事件为 True，重复事件为 False。

    """

    # 复用 session 中持久化的事件列表。
    list_events = dict_session.setdefault("trigger_events", [])  # 已记录事件列表

    # 扫描历史摘要，确保事件只进入一次生命周期。
    for dict_event in list_events:

        # 仅字典事件且摘要相同才构成重复。
        if (
            isinstance(dict_event, dict)
            and dict_event.get("event_id") == str_event_id
        ):

            # 重复事件不再追加新的记录。
            return False

    # 首次事件先记录为未完成，等待主 Agent 收据闭合。
    list_events.append(
        {
            "event_type": str_event_type,
            "event_id": str_event_id,
            "project_root": dict_session.get("project_root", ""),
            "recorded": False,
        }
    )

    # 告知调用方本次事件已成功登记。
    return True

# 生成运行时前提失败时的统一启动结果。
def _start_runtime_block_result(list_runtime_errors: list[str]) -> dict[str, object]:
    """构造 runtime gate 失败时的启动阻断结果。

    参数:
        list_runtime_errors: 当前项目的运行时前提错误列表。
    返回:
        不写 session 且标记 blocking 的启动结果。
    """

    # runtime gate 未通过时不能伪造 session 身份或 worker 派发。
    dict_result: dict[str, object] = dict(  # 先建立不含派发队列的启动阻断底稿。
        schema_version=SCHEMA_VERSION,  # 固定 worker envelope schema 版本。
        session_id=None,  # 阻断结果不创建 session 身份。
        event_id=None,  # runtime gate 失败没有可提交的事件摘要。
        event_type=INITIAL_EVENT,  # 仍保留 protocol 声明的 initial 事件类型。
        valid=False,  # 运行前提失败时结果不可执行。
        blocking=True,  # 运行前提失败必须停止主 Agent。
    )

    # 补齐空队列和错误路径，保持启动结果 schema 完整。
    dict_result.update(
        {
            "required_dispatches": [],
            "pending_dispatches": [],
            "skipped_dispatches": [],
            "errors": list_runtime_errors,
            "state_path": WORKER_SESSION_STATE_PATH.as_posix(),
        }
    )

    # 返回不写 session 的固定阻断结果。
    return dict_result

# 生成根授权状态失败时的统一启动结果。
def _start_validation_block_result(
    str_plan_sha256: str,
    dict_validation: dict[str, object],
) -> dict[str, object]:
    """构造 worker 状态验证失败时的启动阻断结果。

    参数:
        str_plan_sha256: 已通过摘要校验的方案摘要。
        dict_validation: 根 AGENTS worker 状态验证结果。
    返回:
        不写 session 且绑定确定性失败事件摘要的结果。
    """

    # 失败事件摘要绑定当前方案和 initial 阶段，保证诊断可复现。
    str_event_id = _sha256_text(  # 状态未配置时的确定性失败事件摘要。
        f"unconfigured\0{str_plan_sha256}\0{INITIAL_EVENT}"  # 绑定方案摘要和 initial 阶段。
    )

    # 状态未通过时原样保留治理验证错误，不创建新的派发项。
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": None,
        "event_id": str_event_id,
        "event_type": INITIAL_EVENT,
        "valid": False,
        "blocking": True,
        "required_dispatches": [],
        "pending_dispatches": [],
        "skipped_dispatches": [],
        "errors": dict_validation.get("errors", []),
        "state_path": WORKER_SESSION_STATE_PATH.as_posix(),
    }

# 生成既有 session 绑定失败时的统一启动结果。
def _start_binding_error_result(
    str_plan_sha256: str,
    object_error: Exception,
) -> dict[str, object]:
    """构造既有 session 无法复用时的阻断结果。

    参数:
        str_plan_sha256: 已通过摘要校验的方案摘要。
        object_error: session 读取或绑定校验异常。
    返回:
        不覆盖既有 session 且标记 blocking 的结果。
    """

    # 失败事件摘要保留 session-error 标签和当前方案绑定。
    str_event_id = _sha256_text(  # 既有 session 复用失败的确定性事件摘要。
        f"session-error\0{str_plan_sha256}\0{INITIAL_EVENT}"  # 用 session-error 标签区分读取失败路径。
    )

    # 复用失败时禁止创建新身份，避免绕过原 session 的生命周期。
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": None,
        "event_id": str_event_id,
        "event_type": INITIAL_EVENT,
        "valid": False,
        "blocking": True,
        "required_dispatches": [],
        "pending_dispatches": [],
        "skipped_dispatches": [],
        "errors": [str(object_error)],
        "state_path": WORKER_SESSION_STATE_PATH.as_posix(),
    }

# 读取并核对已有 session，保持方案、模式和测试面绑定不可漂移。
def _reuse_existing_start_session(
    path_project: Path,
    str_plan_sha256: str,
    task_mode: str,
    bool_has_test_surface: bool,
) -> dict[str, Any]:
    """读取已存在的 worker session 并检查启动参数绑定。

    参数:
        path_project: 已规范化的项目根路径。
        str_plan_sha256: 当前批准方案摘要。
        task_mode: 当前任务模式。
        bool_has_test_surface: 当前测试面事实。
    返回:
        通过绑定检查的 session 载荷。
    异常:
        OSError 或 ValueError 表示 session 无法安全复用。
    """

    # 读取 session 时同时校验项目根、方案摘要和活动状态。
    tuple_bound_session: tuple[Path, dict[str, Any]] = _bound_session(path_project)  # 已核对的 session 绑定。

    # 从绑定结果中取出既有 session 载荷，保留原身份。
    dict_session: dict[str, Any] = tuple_bound_session[1]  # 既有 session 载荷。

    # 三个启动参数必须完全匹配，防止复用到另一项任务。
    if (
        dict_session.get("plan_sha256") != str_plan_sha256
        or dict_session.get("task_mode") != task_mode
        or dict_session.get("has_test_surface") != bool_has_test_surface
    ):

        # 绑定漂移时阻断而不是覆盖既有 session。
        raise ValueError("> ERR: [Python] existing worker session binding mismatch")

    # 返回保留原身份的 session，供 INITIAL 幂等判定复用。
    return dict_session

# 回放已经登记的 INITIAL 事件，确保重复调用不重复 spawn。
def _replay_initial_event(
    dict_session: dict[str, Any],
    dict_states: dict[str, str],
    str_event_id: str,
    float_now_monotonic: float,
) -> dict[str, object]:
    """回放既有 INITIAL 事件和其持久化 target。

    参数:
        dict_session: 已绑定的 session 载荷。
        dict_states: 根 AGENTS 验证后的 worker 状态映射。
        str_event_id: INITIAL 事件摘要。
        float_now_monotonic: 当前单调时间。
    返回:
        幂等启动结果，不生成新的 worker target。
    """

    # 找到当前事件的历史记录，保留 recorded 和 blocking 事实。
    dict_existing_event = next(  # 当前 INITIAL 事件的历史记录。
        (
            dict_event  # 选择当前事件的历史记录对象。
            for dict_event in dict_session.get("trigger_events", [])  # 遍历 session 事件记录。
            if isinstance(dict_event, dict)  # 只接受结构化事件对象。
            and dict_event.get("event_id") == str_event_id  # 绑定当前 INITIAL 摘要。
        ),
        {},
    )

    # 只回显同一事件仍未闭合的 pending target。
    list_existing_pending = [  # 当前 INITIAL 事件的待回执 target 列表。
        dict_pending  # 保留原始 pending 条目以确保 target 不漂移。
        for dict_pending in dict_session.get("pending_dispatches", [])  # 遍历 session 对账队列。
        if isinstance(dict_pending, dict)  # 只接受结构化 pending 条目。
        and dict_pending.get("event_id") == str_event_id  # 只回显当前事件条目。
    ]

    # 结果副本可重建动作描述，但不修改 session 的 target 队列。
    dict_idempotent_result = _result(  # 重复 INITIAL 调用的结果副本。
        dict_session,  # 绑定原 session 身份。
        INITIAL_EVENT,  # 保留 initial 事件类型。
        str_event_id,  # 回放原事件摘要。
    )

    # 未闭合事件仅在结果副本中重建 reviewer 描述。
    if not dict_existing_event.get("recorded"):

        # 复用已持久化 target，禁止第二次 spawn。
        _reviewer_dispatch(
            dict_idempotent_result,
            dict_session,
            dict_states,
            INITIAL_EVENT,
            {},
            float_now_monotonic,
        )

    # 把已有 pending 标记回填到结果，保持 target 对账一致。
    dict_idempotent_result["pending_dispatches"] = list_existing_pending  # 回放同一事件的待回执索引。

    # 重复调用只回放结果，不产生新的 worker 动作。
    dict_idempotent_result["no_action_taken"] = True  # 标记 dispatcher 没有创建新动作。

    # 未闭合事件继续阻断后续流程，已闭合事件允许继续观察。
    dict_idempotent_result["blocking"] = not bool(dict_existing_event.get("recorded"))  # 回放事件的阻断属性。

    # pending 索引缺失时继续 fail-closed，避免主 Agent猜测 target。
    if not dict_existing_event.get("recorded"):

        # 提示调用方继续使用原事件和已经登记的 target。
        dict_idempotent_result["errors"] = [  # pending target 缺失时的稳定阻断诊断。
            "> ERR: [Python] INITIAL event is already pending; reuse its persisted worker target"  # 指示继续使用持久化 target。
        ]

    # 返回幂等结果，不覆盖 session 或 pending 队列。
    return dict_idempotent_result

# 持久化首次 INITIAL 事件和 reviewer 派发队列。
def _persist_initial_event(
    path_state: Path,
    dict_session: dict[str, Any],
    dict_states: dict[str, str],
    str_event_id: str,
    float_now_monotonic: float,
) -> dict[str, object]:
    """写入首次 INITIAL 事件并生成 reviewer 派发结果。

    参数:
        path_state: 当前 worker session 持久化路径。
        dict_session: 已绑定且尚未闭合的 session 载荷。
        dict_states: 根 AGENTS 验证后的 worker 状态映射。
        str_event_id: INITIAL 事件摘要。
        float_now_monotonic: 当前单调时间。
    返回:
        包含 reviewer INITIAL 派发项和 pending 对账索引的结果。
    """

    # 先写入已登记事件，再计算首次 reviewer 派发。
    _write_session(path_state, dict_session)

    # 创建启动事件的结构化决策结果。
    dict_result = _result(dict_session, INITIAL_EVENT, str_event_id)  # 首次 reviewer 派发的结果容器。

    # 首次事件只要求 reviewer INITIAL，实际调用由主 Agent执行。
    _reviewer_dispatch(
        dict_result,
        dict_session,
        dict_states,
        INITIAL_EVENT,
        {},
        float_now_monotonic,
    )

    # 为当前结果的每个角色建立 receipt 对账行。
    dict_session["pending_dispatches"] = [  # INITIAL 尚未收到 receipt 的角色索引。
        {
            "event_id": str_event_id,  # receipt 必须回指同一 INITIAL 摘要。
            "worker_id": dict_item["worker_id"],  # 主 Agent需要调用的 canonical 角色。
            "phase": dict_item["phase"],  # 主 Agent需要执行的生命周期阶段。
            "agent_target": dict_item.get("agent_target"),  # 首次 spawn 为空，follow-up 固定为已知 target。
        }
        for dict_item in dict_result["required_dispatches"]  # 为每个角色建立 receipt 对账行。
    ]

    # 回填当前 INITIAL 事件的派发数量和阻断属性。
    for dict_event in dict_session["trigger_events"]:

        # 只修改当前启动事件，不影响历史事件记录。
        if dict_event.get("event_id") == str_event_id:

            # 把实际角色数量写入事件记录。
            dict_event["required_dispatches"] = len(dict_result["required_dispatches"])  # 当前事件产生的角色数量。

            # 让事件记录继承 reviewer INITIAL 的阻断结果。
            dict_event["blocking"] = bool(dict_result["blocking"])  # 当前事件的阻断属性。

    # 持久化完整启动决策和 pending 队列。
    _write_session(path_state, dict_session)

    # 返回主 Agent执行的结构化决策。
    return dict_result

# 按批准输入创建新的 managed session。
def _create_start_session(
    path_project: Path,
    str_plan_sha256: str,
    task_mode: str,
    bool_has_test_surface: bool,
    float_now_monotonic: float,
    dict_states: dict[str, str],
) -> dict[str, Any]:
    """按批准方案创建新的 managed session。

    参数:
        path_project: 已规范化的项目根路径。
        str_plan_sha256: 已通过摘要校验的方案摘要。
        task_mode: 当前任务模式。
        bool_has_test_surface: 当前测试面事实。
        float_now_monotonic: session 生命周期起始时间。
        dict_states: 根 AGENTS 验证后的 worker 状态。
    返回:
        包含 session_id、绑定字段和 worker 状态的初始 session。
    """

    # 统一委托低层 session 构造器，保持身份和状态初始化单一实现。
    return _new_session(
        path_project,
        str_plan_sha256,
        task_mode,
        bool_has_test_surface,
        float_now_monotonic,
        dict_states,
    )

# 创建或复用 managed session，并生成首次 reviewer 派发决策。
def start_dispatch_session(
    project: str | Path,
    plan_sha256: str,
    task_mode: str,
    has_test_surface: bool,
    now_monotonic: float,
) -> dict[str, object]:
    """绑定 session 并生成 IMPLEMENTATION_START 决策。

    参数:
        project: 受管项目根路径。
        plan_sha256: 已批准方案摘要。
        task_mode: 当前任务模式。
        has_test_surface: 是否存在测试面。
        now_monotonic: session 起始单调时间。
    返回:
        固定 schema 的启动结果。
    异常:
        ValueError 表示输入无效。

    """

    # 先校验用户确认方案的完整摘要。
    str_plan_sha256 = _require_sha256(plan_sha256, "plan_sha256")  # 批准方案摘要

    # 任务模式必须来自方案允许集合。
    if task_mode not in TASK_MODES:

        # 未知模式不能选择隐式生命周期。
        raise ValueError(f"> ERR: [Python] unknown task_mode: {task_mode}")

    # 测试面标志必须是明确布尔值。
    if not isinstance(has_test_surface, bool):

        # 拒绝用字符串或整数伪造测试面状态。
        raise ValueError("> ERR: [Python] has_test_surface must be boolean")

    # 校验 session 起始单调时间。
    float_now = _require_monotonic(now_monotonic)  # session 起始时钟

    # 归一化受管项目根路径。
    path_project = Path(project).resolve()  # 用绝对路径固定本次 session 创建范围

    # 读取 Codex-native 运行前提阻断原因。
    list_runtime_errors: list[str] = _runtime_gate(path_project)  # 收集创建前的环境阻断原因。

    # 运行前提失败时返回固定阻断 schema，不写 session。
    if list_runtime_errors:

        # 保留所有环境阻断原因供主 Agent处理。
        return _start_runtime_block_result(list_runtime_errors)

    # 读取根 AGENTS 中三个 canonical worker 的状态，session 不进入 tests/**。
    dict_validation: dict[str, object] = validate_worker_states(  # worker 状态验证结果。
        path_project,  # 当前项目根路径。
        bool_include_nested=False,  # session 只验证根 AGENTS.md。
    )

    # 提取已验证状态映射供后续职责判断。
    dict_states: dict[str, str] = dict_validation.get("states", {})  # 提取通过验证的三个 worker 状态。

    # 状态验证失败时不能创建可派发 session。
    if not dict_validation.get("valid"):

        # 返回状态文件中的详细阻断原因。
        return _start_validation_block_result(str_plan_sha256, dict_validation)

    # 定位可能已经存在的 session 状态文件。
    path_existing_state = _session_path(path_project)  # 既有 session 路径。

    # 存在状态时复用并核对其方案绑定。
    if path_existing_state.is_file():

        # 复用失败时返回稳定结果，且不触碰原文件。
        try:

            # 只复用与当前方案、模式和测试面完全一致的 session。
            dict_session: dict[str, Any] = _reuse_existing_start_session(  # 读取并复用已绑定的 session。
                path_project,  # 用当前项目根重用既有 session 身份。
                str_plan_sha256,  # 当前批准方案摘要。
                task_mode,  # 当前任务模式。
                has_test_surface,  # 当前测试面事实。
            )

        # session 读取或绑定失败时返回稳定阻断结果。
        except (OSError, ValueError) as object_error:

            # closed、inactive、corrupt 和 binding drift 均交给统一阻断结果。
            return _start_binding_error_result(str_plan_sha256, object_error)

    # 没有状态文件时按当前批准方案创建新 session。
    else:

        # 新 session 绑定方案、任务模式、测试面和根授权状态，并闭合可审计的输入边界。
        def create_initial_session() -> dict[str, Any]:
            """创建当前分支的新 session。

            参数：无。
            返回：当前批准输入对应的新 session 载荷。
            """

            # 复用模块级 helper，保证初始化逻辑不复制。
            return _create_start_session(
                path_project,
                str_plan_sha256,
                task_mode,
                has_test_surface,
                float_now,
                dict_states,
            )

        # 生成包含 session_id 的初始 session 载荷。
        dict_session = create_initial_session()  # 保存批准输入和 worker 授权态。

    # 为本次 session 生成唯一 IMPLEMENTATION_START 摘要。
    str_event_id = build_event_id(  # 生成不会因字段顺序变化的 INITIAL 摘要。
        dict_session,  # 绑定新建或复用的 session 身份
        INITIAL_EVENT,  # 使用 protocol 声明的启动事件类型
        {},  # 启动阶段没有额外载荷字段
    )

    # 登记启动事件，防止重复触发 INITIAL。
    bool_first_event = _remember_event(  # 登记事件并返回是否为首次触发。
        dict_session,  # 写入当前 session 的 trigger_events。
        INITIAL_EVENT,  # 使用 protocol 声明的 initial 事件。
        str_event_id,  # 绑定本次方案和 session 的事件摘要。
    )

    # 重复启动必须幂等返回，不能在既有 reviewer 未回执时再次 spawn。
    if not bool_first_event:

        # 只回放已登记的事件和 target，不生成第二次 spawn。
        return _replay_initial_event(
            dict_session,
            dict_states,
            str_event_id,
            float_now,
        )

    # 重新定位 session 状态路径并写入首次派发决策。
    path_state = _session_path(path_project)  # 取得启动事件要写入的 session 文件。

    # 首次路径由独立 helper 负责写入 pending 和事件回填。
    return _persist_initial_event(
        path_state,
        dict_session,
        dict_states,
        str_event_id,
        float_now,
    )
