"""实现 worker dispatch 的事件验证、阶段路由和公共 start/check 入口。"""

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

# 路由和持久化实现位于独立 shard，避免 facade 与角色路由形成循环依赖。
try:
    # 结构化阻断与派发动作由路由 shard 提供。
    from .worker_dispatch_event_routing import (
        _block,
        _dispatch_item,
        _gardener_dispatch,
        _persist_check_progress,
        _reviewer_dispatch,
        _reviewer_due,
    )

    # 事件结果和角色路由使用同一份 shard 实现。
    from .worker_dispatch_event_routing import (
        _result,
        _route_check_dispatches,
        _tester_dispatch,
    )

# 脚本入口回退到同目录的事件路由 shard。
except ImportError:
    # fallback 入口复用同一结构化阻断与派发动作。
    from worker_dispatch_event_routing import (
        _block,
        _dispatch_item,
        _gardener_dispatch,
        _persist_check_progress,
        _reviewer_dispatch,
        _reviewer_due,
    )

    # fallback 入口复用同一事件结果和角色路由实现。
    from worker_dispatch_event_routing import (
        _result,
        _route_check_dispatches,
        _tester_dispatch,
    )

# 校验事件名称和载荷字段，形成可信事件输入。
def _event_payload(str_event_type: str, obj_payload: object) -> dict[str, object]:
    """校验事件载荷。

    参数:
        str_event_type 为事件名称；obj_payload 为事件载荷。
    返回:
        已确认的字典载荷。
    异常:
        ValueError 表示事件或载荷无效。

    """

    # 事件名称必须来自固定白名单。
    if str_event_type not in EVENT_TYPES:

        # 未知事件不能绕过生命周期合同。
        raise ValueError(f"> ERR: [Python] unknown dispatch event: {str_event_type}")

    # 载荷必须是字典，禁止隐式解析字符串或列表。
    if not isinstance(obj_payload, dict):

        # 结构错误在进入事件摘要前被拒绝。
        raise ValueError("> ERR: [Python] event_payload must be an object")

    # 测试阶段必须同时提供源码和测试树摘要。
    if str_event_type in {str_event for str_event in EVENT_TYPES if str_event.startswith("TEST_")}:

        # 校验被测源码摘要字段。
        _require_sha256(obj_payload.get("source_sha256"), "source_sha256")

        # 校验测试树摘要字段。
        _require_sha256(obj_payload.get("tests_sha256"), "tests_sha256")

    # 提交事件必须使用完整提交摘要。
    if str_event_type == COMMIT_EVENT:

        # 拒绝短 hash 或缺失提交绑定。
        _require_sha256(obj_payload.get("full_commit_sha256"), "full_commit_sha256")

    # 治理刷新需要前后摘要和 verify_agents 成功证据。
    if str_event_type == AGENTS_REFRESH_EVENT:

        # 校验刷新前摘要。
        _require_sha256(obj_payload.get("before_sha256"), "before_sha256")

        # 校验刷新后摘要。
        _require_sha256(obj_payload.get("after_sha256"), "after_sha256")

        # verify_agents 未通过时禁止进入 gardener 全扫描。
        if not bool(obj_payload.get("verify_agents_ok")):

            # 治理验证失败属于硬阻断。
            raise ValueError("> ERR: [Python] AGENTS refresh verify_agents did not pass")

    # 控制边界载荷必须携带非负周期序号。
    if str_event_type == CONTROL_BOUNDARY_EVENT:

        # 读取 reviewer 周期序号。
        int_sequence = obj_payload.get("periodic_sequence")  # 控制边界序号

        # 拒绝布尔值、负数和非整数序号。
        if (
            isinstance(int_sequence, bool)
            or not isinstance(int_sequence, int)
            or int_sequence < 0
        ):

            # 非法序号不能参与事件去重摘要。
            raise ValueError("> ERR: [Python] periodic_sequence must be non-negative")

    # 返回已完成字段校验的原始字典载荷。
    return obj_payload

# session、周期守卫和公共检查入口保持在 facade，具体实现由独立 shard 提供。
try:
    # session 启动函数与周期守卫由独立 shard 提供。
    from .worker_dispatch_session_start import start_dispatch_session
    from .worker_dispatch_event_guards import (
        _check_dispatch_guards,
        _validate_periodic_sequence,
    )

# 脚本入口回退到同目录的 session 与 guard shard。
except ImportError:
    # fallback 入口复用同一 session 与 guard shard。
    from worker_dispatch_session_start import start_dispatch_session
    from worker_dispatch_event_guards import (
        _check_dispatch_guards,
        _validate_periodic_sequence,
    )

# 统一入口校验事件、运行时状态和角色派发结果。
def _check_dispatch_event_impl(
    project: str | Path,
    event_type: str,
    event_payload: dict[str, object],
    now_monotonic: float,
) -> dict[str, object]:
    """检查事件并计算派发动作。

    参数:
        project 为项目根；event_type 为事件名称；event_payload 为载荷；now_monotonic 为当前时钟。
    返回:
        固定 schema 的事件结果。
    异常:
        ValueError 表示 session、事件或摘要无效。

    """

    # 先校验事件名称与载荷字段。
    dict_payload: dict[str, object] = _event_payload(event_type, event_payload)  # 后续摘要只使用已校验载荷。

    # 固定本次决策的单调时间。
    float_now: float = _require_monotonic(now_monotonic)  # 用统一单调时钟推进 reviewer 和 receipt 时序。

    # 读取并核对当前 managed session。
    tuple_bound_session: tuple[Path, dict[str, Any]] = _bound_session(project)  # 先锁定项目和方案绑定。

    # 提取持久化路径和已核对的 session 载荷。
    path_state: Path = tuple_bound_session[0]  # 后续持久化写回同一 worker-session 文件。

    # 从绑定结果中取出已经核对的 session 载荷。
    dict_session: dict[str, Any] = tuple_bound_session[1]  # 后续状态变更作用于已核对 session。

    # 归一化项目路径，供运行时和 worker 状态验证复用。
    path_project: Path = Path(project).resolve()  # 状态验证和运行时检查共享同一绝对根。

    # 复查运行时前提，防止 session 创建后环境漂移。
    list_runtime_errors: list[str] = _runtime_gate(path_project)  # 捕获 session 创建后的治理环境漂移。

    # 读取当前根 AGENTS 的 worker 状态快照，dispatcher 不进入 tests/**。
    dict_validation: dict[str, object] = validate_worker_states(  # 重新读取根授权快照。
        path_project,  # 当前项目根路径。
        bool_include_nested=False,  # dispatcher 只验证根 AGENTS.md。
    )

    # 提取状态映射供各角色派发器使用。
    dict_states: dict[str, str] = dict_validation.get("states", {})  # 将授权快照传给三个角色派发器。

    # 按规范字段生成当前事件摘要。
    str_event_id = build_event_id(  # 生成绑定当前 session 的不可变事件身份。
        dict_session,  # 事件身份使用已核对的 session 命名空间。
        event_type,  # 事件身份区分生命周期事件。
        dict_payload,  # 事件身份使用已校验字段内容。
    )  # 固化当前 session、事件类型和载荷的身份摘要。

    # 创建尚未附加角色决策的事件结果。
    dict_result = _result(dict_session, event_type, str_event_id)  # 建立角色派发器共同写入的结果容器。

    # 控制边界要求周期序号严格递增。
    int_current_sequence = _validate_periodic_sequence(  # 读取并校验 control boundary 序号。
        event_type,  # 当前事件类型。
        dict_session,  # 已绑定 session 的历史序号。
        dict_payload,  # 已校验的当前事件序号。
    )

    # 环境、target、授权和重复事件均在此处 fail-closed。
    dict_guard_result = _check_dispatch_guards(  # 执行事件派发前的统一阻断守卫。
        dict_result,  # 当前事件结果容器。
        dict_session,  # 已绑定 session 载荷。

        # 写回路径和已校验事件载荷。
        path_state,  # 守卫阻断时写回同一 session 文件。
        dict_payload,  # 使用已经通过字段校验的事件载荷。

        # runtime 与授权输入共同决定 fail-closed 守卫。
        (list_runtime_errors, dict_validation),  # 传入 runtime 错误和授权验证结果。
        event_type,  # 角色路由仍使用原始事件名称。
        str_event_id,  # 角色路由与事件记录共享同一摘要。
    )

    # 任何早退结果都已经完成必要的持久化或阻断记录。
    if dict_guard_result is not None:

        # 不再进入角色 dispatcher，保持原事件状态机顺序。
        return dict_guard_result

    # 成功登记 control boundary 后推进 session 周期序号。
    if int_current_sequence is not None:

        # 只在事件去重成功后提交新的周期边界。
        dict_session["periodic_sequence"] = int_current_sequence  # 保存已经确认的 reviewer 周期序号。

    # 按事件集合调用三个角色 dispatcher。
    _route_check_dispatches(
        dict_result,
        dict_session,
        dict_states,
        event_type,
        dict_payload,
        float_now,
    )

    # 统一写回 dispatcher-only、pending 和事件 recorded 状态。
    return _persist_check_progress(
        path_state,
        dict_session,
        dict_result,
        str_event_id,
    )

# 将输入或运行时异常转换为固定阻断结果。
def _failure_result(
    project: str | Path,
    str_event_type: object,
    object_error: Exception,
) -> dict[str, object]:
    """构造事件错误结果。

    参数:
        project 为项目根；str_event_type 为事件名；object_error 为阻断原因。
    返回:
        valid=false、blocking=true 的固定 schema。
    """

    # 统一异常路径中的事件名称文本。
    str_event = str(str_event_type)  # 错误结果事件名称

    # 返回不携带 session 身份的结构化阻断。
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": None,
        "event_id": None,
        "event_type": str_event,
        "valid": False,
        "blocking": True,
        "required_dispatches": [],
        "pending_dispatches": [],
        "skipped_dispatches": [],
        "errors": [str(object_error)],
        "state_path": str(_session_path(project).relative_to(Path(project).resolve())),
    }

# 对外暴露事件检查接口，并把已知异常结构化。
def check_dispatch_event(
    project: str | Path,
    event_type: str,
    event_payload: dict[str, object],
    now_monotonic: float,
) -> dict[str, object]:
    """检查事件并在错误时返回阻断 JSON。

    参数:
        project 为项目根；event_type 为事件名；event_payload 为载荷；now_monotonic 为时钟。
    返回:
        派发决策或结构化阻断结果。
    """

    # 正常路径交给内部实现，保持公共接口稳定。
    try:

        # 计算并持久化当前事件的 worker 决策。
        return _check_dispatch_event_impl(  # 按事件合同写回 session，并把可执行角色项交给主 Agent
            project,
            event_type,
            event_payload,
            now_monotonic,
        )

    # 公共接口把输入、状态和文件异常统一返回为阻断。
    except (TypeError, ValueError, OSError) as object_error:

        # 由错误结果函数保持机器可解析 schema。
        return _failure_result(project, event_type, object_error)
