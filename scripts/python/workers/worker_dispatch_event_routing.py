"""承载 worker dispatch 的角色路由、事件持久化和派发守卫。"""

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

# session 状态相对路径统一由 Path 组合，避免在不同运行根目录硬编码字符串。
WORKER_SESSION_STATE_PATH: Path = Path(".agents") / "worker-session.json"  # worker session 状态相对路径。

# 创建新的 worker 派发项并绑定 canonical target。
def _dispatch_item(
    dict_session: dict[str, Any],
    str_worker_id: str,
    str_phase: str,
    bool_blocking: bool,
) -> dict[str, object]:
    """创建 spawn 或 followup 项。

    参数:
        dict_session 为当前 session；str_worker_id 为角色；str_phase 为阶段；bool_blocking 为阻断标记。
    返回:
        主 Agent执行所需的派发项。
    异常:
        ValueError 表示 target 丢失或身份未知。

    """

    # 读取目标 worker 的唯一状态记录。
    dict_worker = dict_session["worker_states"][str_worker_id]  # 依据 worker 状态决定首次或复用派发

    # 复用已有 target，保证后续阶段只 followup。
    str_agent_target = dict_worker.get("agent_target")  # 复用该 target 可禁止第二次 spawn

    # 未启动且无 target 时才允许首次 spawn。
    if dict_worker.get("state") == "not_started" and not str_agent_target:

        # 记录首个派发动作。
        str_action = "spawn"  # 未启动记录只允许创建一次新 worker

    # 已有非空 target 时必须复用原 worker。
    elif isinstance(str_agent_target, str) and str_agent_target.strip():

        # 记录复用已有 worker 的后续动作。
        str_action = "followup"  # 已有 target 的阶段只能沿原 agent 链继续

    # 其他组合说明状态已漂移，不能猜测动作。
    else:

        # 第二次 spawn 或空 target 都按合同拒绝。
        raise ValueError(
            f"> ERR: [Python] {str_worker_id} target is missing; second spawn is forbidden"
        )

    # 生成带有当前阶段和项目绑定的最小权限 envelope。
    dict_task_envelope = _envelope(  # 把角色权限固定在本次阶段和方案上
        str_worker_id,  # envelope 选择唯一 canonical 角色
        str_phase,  # envelope 绑定当前生命周期位置
        Path(dict_session["project_root"]),  # envelope 限定可读写项目根
        str(dict_session["plan_sha256"]),  # envelope 继承批准方案摘要
        str(dict_session["task_mode"]),  # envelope 继承任务模式合同
    )

    # 返回主 Agent 可直接执行的派发描述，不执行 spawn/followup。
    dict_communication = {  # 主 Agent 可逐字传递的通信载荷
        "target": str_agent_target if str_action == "followup" else None,  # 绑定首次或复用目标
        "payload": dict_task_envelope,  # 保留完整权限 envelope
    }

    # 返回动作、目标和通信载荷，避免主 Agent重新拼装消息。
    return {
        "worker_id": str_worker_id,
        "action": str_action,
        "agent_type": str_worker_id,
        "fork_turns": "none",
        "agent_target": str_agent_target if str_action == "followup" else None,
        "phase": str_phase,
        "blocking": bool_blocking,
        "task_envelope": dict_task_envelope,
        "communication": dict_communication,
    }

# 创建一次事件决策的固定结果底稿。
def _result(
    dict_session: dict[str, Any],
    str_event_type: str,
    str_event_id: str,
) -> dict[str, object]:
    """创建 dispatch 结果底稿。

    参数:
        dict_session 为当前 session；str_event_type 为事件类型；str_event_id 为事件摘要。
    返回:
        固定 schema 的结果对象。

    """

    # 结果底稿先声明为有效，后续阻断函数再收紧状态。
    return {
        "schema_version": SCHEMA_VERSION,
        "session_id": dict_session["session_id"],
        "event_id": str_event_id,
        "event_type": str_event_type,
        "valid": True,
        "blocking": False,
        "required_dispatches": [],
        "pending_dispatches": [],
        "skipped_dispatches": [],
        "no_action_taken": False,
        "errors": [],
        "state_path": WORKER_SESSION_STATE_PATH.as_posix(),
    }

# 把一个 worker 的拒绝原因写入事件结果并锁定阻断态。
def _block(
    dict_result: dict[str, object],
    str_worker_id: str,
    str_reason: str,
) -> None:
    """追加 worker 阻断错误。

    参数:
        dict_result 为当前结果；str_worker_id 为角色；str_reason 为原因。
    返回:
        None。

    """

    # 复用结果对象的错误列表，保持统一 schema。
    list_errors = dict_result["errors"]  # 事件错误列表

    # 追加带 worker 身份的稳定错误文本。
    list_errors.append(f"{str_worker_id}: {str_reason}")

    # 任何 worker 阻断都会使整个事件无效。
    dict_result["valid"] = False  # 结果有效标志

    # 阻断态禁止主 Agent继续执行后续动作。
    dict_result["blocking"] = True  # 结果阻断标志

# 判断 reviewer 是否应在当前控制边界重新派发。
def _reviewer_due(
    dict_session: dict[str, Any],
    float_now_monotonic: float,
) -> tuple[bool, str]:
    """判断 reviewer PERIODIC 是否到期。

    参数:
        dict_session 为当前 session；float_now_monotonic 为当前时钟。
    返回:
        触发标志和原因文本。

    """

    # 读取上次 reviewer 收据对应的单调时间。
    obj_last_monotonic: object = dict_session.get("last_reviewer_monotonic")  # 用历史时间判断周期是否到期

    # 首次周期检查没有历史收据，必须立即触发。
    if obj_last_monotonic is None:

        # 返回触发标志和可读原因。
        return True, "periodic reviewer has no previous receipt"

    # 组装 reviewer_trigger_decision 需要的历史状态。
    dict_reviewer_state = {
        "review_session_id": dict_session["session_id"],  # 让周期决策锁定当前 session
        "approved_plan_sha256": dict_session["plan_sha256"],  # 防止 reviewer 跨方案复用
        "worker_id": REVIEWER_WORKER_ID,  # 固定周期决策的角色来源
        "last_review_monotonic": obj_last_monotonic,  # 计算距离上次审查的时间
        "last_receipt_sha256": (  # 用历史收据证明 reviewer 链连续
            dict_session["worker_states"][REVIEWER_WORKER_ID].get(  # 读取 reviewer 状态中的最近收据
                "last_receipt_sha256"  # 固定收据摘要字段
            )  # 缺失时由下方空字符串兜底
            or ""  # 首次周期没有历史收据摘要
        ),
    }

    # 交由 reviewer 规则计算时间间隔和收据连续性。
    dict_decision = reviewer_trigger_decision(  # 计算本次控制边界的 reviewer 触发结论
        dict_reviewer_state,  # 输入历史时间和收据链
        PERIODIC_PHASE,  # 控制边界使用协议声明的周期阶段
        str(dict_session["plan_sha256"]),  # 触发决策继承批准方案
        float_now_monotonic,  # 触发决策使用当前单调时钟
        REVIEWER_WORKER_ID,  # 触发决策只面向 reviewer
        DEFAULT_REVIEW_INTERVAL_SECONDS,  # 采用合同规定的审查间隔
        dict_reviewer_state["last_receipt_sha256"],  # 把上次收据传入连续性检查
    )

    # 返回规则计算出的触发标志和原因。
    return bool(dict_decision.get("trigger")), str(dict_decision.get("reason", ""))

# 计算 reviewer 的阶段、到期条件和下一次派发动作。
def _reviewer_dispatch(
    dict_result: dict[str, object],
    dict_session: dict[str, Any],
    dict_states: dict[str, str],
    str_event_type: str,
    dict_payload: dict[str, object],
    float_now_monotonic: float,
) -> None:
    """追加 reviewer 阶段决策。

    参数:
        dict_result: 当前事件结果对象。
        dict_session: 已绑定 worker session。
        dict_states: root AGENTS 的 canonical worker 状态映射。
        str_event_type: 当前生命周期事件名称。
        dict_payload: 事件载荷。
        float_now_monotonic: 当前单调时间。
    返回:
        None。

    """

    # 仅 implementation/release 任务需要 reviewer 生命周期。
    if dict_session["task_mode"] not in {"implementation", "release"}:

        # 其他任务记录跳过原因，不伪造 reviewer 派发。
        dict_result["skipped_dispatches"].append(
            {"worker_id": REVIEWER_WORKER_ID, "reason": "task mode has no reviewer trigger"}
        )

        # 当前事件没有 reviewer 动作，返回主流程。
        return

    # 读取 reviewer 根授权结果。
    tuple_authorization: tuple[bool, str] = _authorized(dict_states, REVIEWER_WORKER_ID)  # 读取 reviewer 是否可被主流程调度

    # 提取授权布尔值，决定是否继续构造派发项。
    bool_allowed: bool = tuple_authorization[0]  # 分离允许标志以决定阻断或派发

    # 提取失败原因，供阻断或跳过结果使用。
    str_reason: str = tuple_authorization[1]  # 保留未授权原因供结果收据解释

    # 未授权时区分显式 disabled 与未配置。
    if not bool_allowed:

        # 显式 disabled 是合同允许的无动作结果。
        if str_reason == "worker is explicitly disabled":

            # 记录 reviewer 被配置为 disabled。
            dict_result["skipped_dispatches"].append(
                {"worker_id": REVIEWER_WORKER_ID, "reason": str_reason}
            )

            # 不把显式禁用升级成阻断。
            return

        # 未配置 reviewer 必须阻断主流程。
        _block(dict_result, REVIEWER_WORKER_ID, str_reason)

        # 阻断结果不能继续拼装派发项。
        return

    # correction 和 completion 是强制 reviewer 阶段，其余事件按映射处理。
    bool_trigger = str_event_type in {  # 标记必须立即触发 reviewer 的两个阶段
        CORRECTION_EVENT,  # 修复提交后不能跳过复核
        FINAL_EVENT,  # 完成请求必须经过最终复核
    }

    # 将外部事件名称映射为 reviewer 合同阶段。
    dict_event_phases = {  # 当前事件到 reviewer 阶段的反向查找表。
        str_event: str_phase  # 使用阶段映射生成事件键。
        for str_phase, str_event in EVENT_BY_PHASE.items()  # 遍历 protocol 阶段到事件映射。
    }

    # 未识别的控制边界按 periodic 阶段处理。
    str_phase = dict_event_phases.get(str_event_type, PERIODIC_PHASE)  # 当前 reviewer 派发阶段。

    # 控制边界事件需要先处理上次 reviewer 的阻断 verdict。
    if str_event_type == PERIODIC_EVENT:

        # 这些历史 verdict 未解决前禁止新动作。
        if dict_session.get("reviewer_last_verdict") in REVIEWER_BLOCKING_VERDICTS:

            # 把历史审查阻断传递给当前事件。
            _block(
                dict_result,
                REVIEWER_WORKER_ID,
                "last reviewer verdict blocks new actions",
            )

            # 阻断后不再计算周期触发。
            return

        # 计算当前 reviewer 周期是否已到期。
        tuple_reviewer_due: tuple[bool, str] = _reviewer_due(  # 读取周期到期及原因
            dict_session,  # 提供 reviewer 历史状态
            float_now_monotonic,  # 提供本次边界的比较时钟
        )

        # 提取周期触发标志。
        bool_trigger: bool = tuple_reviewer_due[0]  # 决定本次是否新增 reviewer 派发

        # 提取周期未触发或触发的原因文本。
        str_reason: str = tuple_reviewer_due[1]  # 未派发时解释周期条件

        # 控制边界统一进入 PERIODIC 阶段。
        str_phase = PERIODIC_PHASE  # 控制边界派发归入协议声明的周期阶段

        # 未到期时只记录跳过，不重复派发。
        if not bool_trigger:

            # 保留当前周期未派发的原因。
            dict_result["skipped_dispatches"].append(
                {"worker_id": REVIEWER_WORKER_ID, "reason": str_reason}
            )

            # 未到期事件不产生待调度项。
            return

    # correction 只能在 reviewer 明确要求时重新审查。
    if str_event_type == CORRECTION_EVENT:

        # 修复事件必须继续绑定原批准方案。
        if dict_payload.get("plan_sha256") != dict_session["plan_sha256"]:

            # 方案漂移时阻断 correction 复核。
            _block(
                dict_result,
                REVIEWER_WORKER_ID,
                "correction plan hash differs from session plan",
            )

            # 方案不一致不能继续派发。
            return

        # 没有待修复项时不重复触发 correction。
        if not dict_session.get("reviewer_correction_required"):

            # 记录 correction 无需执行的原因。
            dict_result["skipped_dispatches"].append(
                {"worker_id": REVIEWER_WORKER_ID, "reason": "correction is not required"}
            )

            # 无 correction 合同项时返回空动作结果。
            return

    # 完成前要求 tester FINAL 和 gardener 队列都已经闭合。
    if str_event_type == FINAL_EVENT:

        # 有测试面时缺少 tester FINAL 必须阻断完成。
        if (
            dict_session.get("has_test_surface")
            and not dict_session.get("tester_final_completed")
        ):

            # reviewer 不能替代缺失的 tester FINAL 收据。
            _block(dict_result, REVIEWER_WORKER_ID, "tester final receipt is missing")

            # 测试证据缺失时停止完成请求。
            return

        # gardener 尚有待派发项时不能进入最终审查。
        if dict_session.get("pending_dispatches"):

            # 保持完成边界的顺序约束。
            _block(dict_result, REVIEWER_WORKER_ID, "pending gardener dispatch remains")

            # 待派发队列清空前停止完成请求。
            return

    # 只有前置条件全部通过时才生成主 Agent 派发项。
    try:

        # 生成 reviewer 当前阶段的 spawn/followup 描述。
        dict_item = _dispatch_item(  # 为 reviewer 生成主 Agent 可执行的动作描述
            dict_session,  # 动作继承当前 session 的 target 和方案
            REVIEWER_WORKER_ID,  # 动作锁定 reviewer canonical 身份
            str_phase,  # 动作锁定当前 reviewer 阶段
            str_phase in {INITIAL_PHASE, CORRECTION_PHASE, FINAL_PHASE},  # 强制阶段阻断后续流程
        )

    # target 缺失等合同错误要转成结果阻断。
    except ValueError as object_error:

        # 去掉统一错误前缀，保留 worker 语义原因。
        _block(
            dict_result,
            REVIEWER_WORKER_ID,
            str(object_error).replace("> ERR: [Python] ", ""),
        )

        # 阻断后不追加不完整派发项。
        return

    # 将 reviewer 派发项交给主 Agent 执行。
    dict_result["required_dispatches"].append(dict_item)

# 计算 tester RED/GREEN/FINAL 的唯一生命周期派发。
def _tester_dispatch(
    dict_result: dict[str, object],
    dict_session: dict[str, Any],
    dict_states: dict[str, str],
    str_event_type: str,
) -> None:
    """追加 tester 阶段决策。

    参数:
        dict_result 为结果；dict_session 为 session；dict_states 为根状态；str_event_type 为测试事件。
    返回:
        None。

    """

    # 没有测试面时 tester 合同明确为跳过。
    if not dict_session.get("has_test_surface"):

        # 记录没有测试面的无动作结果。
        dict_result["skipped_dispatches"].append(
            {"worker_id": TESTER_WORKER_ID, "reason": "no test surface"}
        )

        # 明确区分 dispatcher 跳过与 worker scope rejection。
        dict_result["no_action_taken"] = True  # 当前事件没有调用任何 worker

        # 不生成 tester 派发项。
        return

    # 测试面存在时必须再次核对根 AGENTS 的 tester 授权。
    tuple_authorization: tuple[bool, str] = _authorized(dict_states, TESTER_WORKER_ID)  # 读取 tester 是否仍在根合同中启用

    # 提取 tester 是否允许执行。
    bool_allowed: bool = tuple_authorization[0]  # 决定 tester 是否可以进入测试阶段

    # 提取 tester 未授权原因。
    str_reason: str = tuple_authorization[1]  # 保存 tester 未授权的具体原因

    # 未授权 tester 不能进入任何测试阶段。
    if not bool_allowed:

        # 将 tester 状态写成阻断结果。
        _block(dict_result, TESTER_WORKER_ID, str_reason)

        # 未授权时不生成派发项。
        return

    # 事件名称去掉 TEST_ 后即为 tester 阶段值。
    str_phase = str_event_type.removeprefix("TEST_")  # 把事件名转换成 receipt phase

    # 生成本阶段 tester 派发描述。
    try:

        # tester 每个阶段都是阻断性证据节点。
        dict_item = _dispatch_item(  # 为 tester 生成当前测试阶段的阻断动作
            dict_session,  # 动作沿用唯一 tester target
            TESTER_WORKER_ID,  # 动作角色必须匹配唯一 tester target
            str_phase,  # 动作绑定 RED/GREEN/FINAL 阶段
            True,  # 测试收据失败必须阻断主流程
        )

    # target 缺失时返回可解释的 tester 阻断。
    except ValueError as object_error:

        # 把底层合同异常写入统一结果结构。
        _block(
            dict_result,
            TESTER_WORKER_ID,
            str(object_error).replace("> ERR: [Python] ", ""),
        )

        # 不把异常路径当作已生成派发项。
        return

    # 交由主 Agent 执行唯一 tester 派发。
    dict_result["required_dispatches"].append(dict_item)

# 加载 gardener 事件策略，兼容包内、脚本和受控模块入口。
def _load_gardener_dispatchers() -> tuple[
    Callable[[str, str, bool], str],
    Callable[[str, Iterable[str]], bool],
]:
    """加载 gardener 的刷新和去重策略函数。

    参数:
        无；模块位置决定 workers/pycode_gardener.py 的候选路径。
    返回:
        刷新状态函数与事件去重函数。
    异常:
        ImportError: gardener 模块缺失、加载器不可用或函数合同不完整。
    """

    # 包内入口优先复用同一 workers 模块身份。
    try:

        # 包调用保持相对导入语义。
        from .pycode_gardener import refresh_dispatch_status, should_dispatch_gardener

        # 返回包内实现，避免重复动态加载。
        return refresh_dispatch_status, should_dispatch_gardener

    # 脚本入口或受控加载入口可能没有 package context。
    except ImportError:

        # 脚本入口优先尝试 workers 目录顶层导入。
        try:

            # 直接执行管理 CLI 时 workers 目录通常在搜索路径中。
            from pycode_gardener import refresh_dispatch_status, should_dispatch_gardener

            # 返回已经存在的脚本入口实现。
            return refresh_dispatch_status, should_dispatch_gardener

        # 测试通过文件规格加载 dispatcher 时走同目录 fallback。
        except ModuleNotFoundError as object_import_error:

            # gardener 源码与 dispatcher 位于同一 workers 目录。
            path_module = Path(__file__).with_name("pycode_gardener.py")  # gardener 源码路径。

            # 缺失只读审查模块时拒绝伪造刷新状态。
            if not path_module.is_file():

                # 保留带固定前缀的导入阻断信息。
                raise ModuleNotFoundError(
                    "> ERR: [Python] worker pycode_gardener module is unavailable"
                ) from object_import_error

            # 为 fallback 模块建立独立加载规格。
            module_type_spec: ModuleSpec | None = cast(  # gardener fallback 加载规格。
                ModuleSpec | None,  # 声明动态规格的静态类型。
                importlib.util.spec_from_file_location(  # 读取 gardener 源文件加载规格。
                    "agents_md_worker_pycode_gardener",  # 隔离 gardener 动态模块，避免覆盖 CLI 已加载模块。
                    path_module,  # 当前 skill 源码中的 gardener 文件。
                ),
            )

            # 缺少 loader 时不能执行只读审查逻辑。
            if module_type_spec is None or module_type_spec.loader is None:

                # 将不完整的加载规格收敛为标准 ImportError。
                raise ImportError(
                    "> ERR: [Python] worker pycode_gardener fallback loader is unavailable"
                )

            # 创建 fallback 模块对象并预先登记名称。
            module_type_gardener: ModuleType = importlib.util.module_from_spec(module_type_spec)  # gardener fallback 模块对象。

            # 为 dataclasses 和模块内注解解析登记 gardener 模块。
            sys.modules[module_type_gardener.__name__] = module_type_gardener  # gardener 模块注册结果。

            # 执行原始 gardener 源码，避免复制只读策略。
            module_type_spec.loader.exec_module(module_type_gardener)

            # 提取策略函数并检查其可调用合同。
            func_refresh = getattr(module_type_gardener, "refresh_dispatch_status", None)  # 刷新状态函数。

            # 提取事件集合去重函数，避免重复触发同一 gardener 扫描。
            func_should_dispatch = getattr(module_type_gardener, "should_dispatch_gardener", None)  # 去重策略函数。

            # 任一策略缺失都必须阻断 gardener 派发。
            if not callable(func_refresh) or not callable(func_should_dispatch):

                # 禁止用不完整模块继续形成治理证据。
                raise ImportError(
                    "> ERR: [Python] worker pycode_gardener fallback contract is incomplete"
                )

            # 返回已经完成 callable 校验的两个策略函数。
            return func_refresh, func_should_dispatch

# 计算 commit 或治理刷新后的 gardener 全扫描派发。
def _gardener_dispatch(
    dict_result: dict[str, object],
    dict_session: dict[str, Any],
    dict_states: dict[str, str],
    str_event_type: str,
    dict_payload: dict[str, object],
) -> None:
    """处理 commit 和 AGENTS refresh gardener 事件。

    参数:
        dict_result: 当前事件结果对象。
        dict_session: 已绑定 worker session。
        dict_states: root AGENTS 的 canonical worker 状态映射。
        str_event_type: commit 或 AGENTS refresh 事件名称。
        dict_payload: 事件摘要和验证结果载荷。
    返回:
        None。

    """

    # 只有提交和治理刷新事件进入 gardener 生命周期。
    if str_event_type not in {COMMIT_EVENT, AGENTS_REFRESH_EVENT}:

        # 其他事件保持无动作，不扩大 gardener 触发范围。
        return

    # 提交或治理刷新进入园丁阶段前必须核对根授权。
    tuple_authorization: tuple[bool, str] = _authorized(dict_states, GARDENER_WORKER_ID)  # gardener 授权结果

    # 把园丁授权结果分离出来，决定全扫描能否继续。
    bool_allowed: bool = tuple_authorization[0]  # gardener 是否允许

    # 保存园丁被拒绝的原因以形成稳定阻断或跳过记录。
    str_reason: str = tuple_authorization[1]  # gardener 拒绝原因

    # 未授权时区分显式禁用和未配置阻断。
    if not bool_allowed:

        # 显式 disabled 只记录跳过。
        if str_reason == "worker is explicitly disabled":

            # 保留 gardener 被禁用的配置事实。
            dict_result["skipped_dispatches"].append(
                {"worker_id": GARDENER_WORKER_ID, "reason": str_reason}
            )

            # 禁用态不产生待执行项。
            return

        # 未配置 gardener 是治理合同阻断。
        _block(dict_result, GARDENER_WORKER_ID, str_reason)

        # 阻断态不继续加载园丁实现。
        return

    # 园丁辅助函数的动态加载失败必须转成当前事件的阻断结果。
    try:

        # 统一加载包内、脚本或受控文件入口的 gardener 策略。
        tuple_gardener_dispatchers = _load_gardener_dispatchers()  # gardener 策略函数集合。

    # 导入路径或 fallback 合同异常不能污染机器结果。
    except (ImportError, OSError) as object_error:

        # 保留固定错误前缀之外的可读原因。
        _block(
            dict_result,
            GARDENER_WORKER_ID,
            str(object_error).replace("> ERR: [Python] ", ""),
        )

        # 没有完整只读策略时不生成 gardener 派发。
        return

    # 分离刷新策略函数，供 AGENTS refresh 事件使用。
    func_refresh_dispatch_status = tuple_gardener_dispatchers[0]  # AGENTS refresh 状态判断函数。

    # 分离去重策略函数，供 commit/refresh 事件使用。
    func_should_dispatch_gardener = tuple_gardener_dispatchers[1]  # gardener 事件去重函数。

    # AGENTS refresh 必须先经过刷新状态验证。
    if str_event_type == AGENTS_REFRESH_EVENT:

        # 计算治理刷新是否达到全扫描条件。
        str_refresh_status = func_refresh_dispatch_status(  # 判定治理刷新是否允许 gardener 全扫
            str(dict_payload.get("before_sha256", "")),  # 传入刷新前字节摘要
            str(dict_payload.get("after_sha256", "")),  # 传入刷新后字节摘要
            bool(dict_payload.get("verify_agents_ok")),  # 传入 verify_agents 成功标记
        )

        # 非全扫描状态不产生 gardener 派发。
        if str_refresh_status != "dispatch_full_scan":

            # 记录刷新策略返回的跳过原因。
            dict_result["skipped_dispatches"].append(
                {"worker_id": GARDENER_WORKER_ID, "reason": str_refresh_status}
            )

            # 等待下一次满足条件的刷新事件。
            return

    # 将当前事件摘要作为 gardener 去重键。
    str_event_id = str(dict_result["event_id"])  # 用事件摘要去重 gardener 全扫描

    # 已审查事件不得再次触发全扫描。
    if not func_should_dispatch_gardener(
        str_event_id,  # 当前事件摘要
        dict_session.get("gardener_reviewed_event_ids", []),  # 已审查事件集合
    ):

        # 记录 gardener 去重后的无动作结果。
        dict_result["skipped_dispatches"].append(
            {"worker_id": GARDENER_WORKER_ID, "reason": "event already reviewed"}
        )

        # 重复事件不进入待派发队列。
        return

    # 为新的提交或治理刷新生成 gardener 派发项。
    try:

        # gardener 派发是阻断性审查，必须有最终收据。
        dict_item = _dispatch_item(  # 为新治理证据生成 gardener 阻断动作
            dict_session,  # 动作继承当前 session 的 target 绑定
            GARDENER_WORKER_ID,  # 角色字段固定到 gardener，避免误派给其他 target
            "COMMIT" if str_event_type == COMMIT_EVENT else "AGENTS_REFRESH",  # 动作区分提交和刷新来源
            True,  # 园丁失败必须阻断完成边界
        )

    # target 缺失时记录 gardener 合同阻断。
    except ValueError as object_error:

        # 把底层错误转成统一阻断字段。
        _block(
            dict_result,
            GARDENER_WORKER_ID,
            str(object_error).replace("> ERR: [Python] ", ""),
        )

        # 不追加不完整的 gardener 派发项。
        return

    # 把新的 gardener 派发交给主 Agent。
    dict_result["required_dispatches"].append(dict_item)

# 按事件类型把 reviewer、tester 和 gardener 派发到各自的 canonical worker。
def _route_check_dispatches(
    dict_result: dict[str, object],
    dict_session: dict[str, Any],
    dict_states: dict[str, str],
    event_type: str,
    dict_payload: dict[str, object],
    float_now_monotonic: float,
) -> None:
    """计算当前事件的角色派发项。

    参数:
        dict_result: 当前事件结果容器。
        dict_session: 已绑定的 session 载荷。
        dict_states: 根 AGENTS 验证后的 worker 状态映射。
        event_type: 当前事件类型。
        dict_payload: 已通过字段校验的事件载荷。
        float_now_monotonic: 当前单调时间。
    返回:
        无；角色派发项直接写入 dict_result。
    """

    # tester 失败后即使历史 receipt 已落盘，也必须开启 reviewer correction 门禁。
    if event_type == CORRECTION_EVENT:

        # 读取持久化 tester 状态，避免依赖主 Agent 的临时记忆。
        dict_tester_state = dict_session.get("worker_states", {}).get(TESTER_WORKER_ID, {})  # tester 持久化状态。

        # 只有 failed tester 状态才要求 correction 标志。
        if isinstance(dict_tester_state, dict) and dict_tester_state.get("state") == "failed":

            # 收到 reviewer CORRECTION 前不允许恢复实现或继续测试。
            dict_session["reviewer_correction_required"] = True  # failed tester 状态驱动 correction 派发。

    # implementation、control、correction、completion 由 reviewer 处理。
    if event_type in REVIEW_EVENTS:

        # 计算 reviewer 阶段并追加待派发项。
        _reviewer_dispatch(
            dict_result,
            dict_session,
            dict_states,
            event_type,
            dict_payload,
            float_now_monotonic,
        )

    # 三个测试事件由同一个 tester target 串行处理。
    if event_type in TEST_EVENTS:

        # 计算 tester 当前阶段的派发项。
        _tester_dispatch(dict_result, dict_session, dict_states, event_type)

    # 提交和治理刷新事件由 gardener 处理。
    if event_type in GARDENER_EVENTS:

        # 计算 gardener 是否需要全扫描。
        _gardener_dispatch(
            dict_result,
            dict_session,
            dict_states,
            event_type,
            dict_payload,
        )

# 写入 dispatcher-only 结果、pending 对账队列和事件记录。
def _persist_check_progress(
    path_state: Path,
    dict_session: dict[str, Any],
    dict_result: dict[str, object],
    str_event_id: str,
) -> dict[str, object]:
    """持久化事件派发进度并返回结果。

    参数:
        path_state: session 持久化路径。
        dict_session: 当前 session 载荷。
        dict_result: 已完成角色路由的事件结果。
        str_event_id: 当前事件摘要。
    返回:
        已写入 session 的事件结果。
    """

    # 没有新派发项且没有阻断时记录 dispatcher-only 的无动作结论。
    if not dict_result["required_dispatches"] and not dict_result["blocking"]:

        # dispatcher 已判断无需 worker，不伪造 worker rejection。
        dict_result["no_action_taken"] = True  # 标记没有新的 worker 动作。

        # 标记本次结论由 dispatcher 直接产生。
        dict_result["dispatcher_only"] = True  # 让 receipt 流程跳过不存在的 worker 回执等待。

        # 写入配置声明的零派发 verdict。
        dict_result["verdict"] = zero_dispatch_verdict()  # 记录无动作的唯一结论。

    # 只有当前事件有新派发项时才追加 receipt 对账索引。
    if dict_result["required_dispatches"]:

        # 复制前一事件尚未回执的角色，避免清空旧 pending 队列。
        list_pending_dispatches = list(  # 当前 session 尚未闭合的 receipt 项。
            dict_session.get("pending_dispatches", [])  # 读取已有对账队列。
        )

        # 将当前事件的角色项追加到保留的对账队列。
        list_pending_dispatches.extend(  # 合并新旧事件的待回执项。
            [
                {
                    "event_id": str_event_id,  # receipt 必须引用当前事件身份。
                    "worker_id": dict_item["worker_id"],  # 对账项锁定主 Agent 要调用的角色。
                    "phase": dict_item["phase"],  # 对账项保留主 Agent 要执行的阶段。
                    "agent_target": dict_item.get("agent_target"),  # 对账项绑定本阶段允许的 target。
                }
                for dict_item in dict_result["required_dispatches"]  # 为每个角色建立当前事件索引。
            ]
        )

        # 写回合并后的队列，供后续 receipt 按事件和 worker 对账。
        dict_session["pending_dispatches"] = list_pending_dispatches  # 保存所有尚未闭合的派发项。

    # 回填事件记录的派发数量和阻断属性。
    for dict_event in dict_session["trigger_events"]:

        # 只更新本次事件记录。
        if dict_event.get("event_id") == str_event_id:

            # 保存主 Agent需要执行的角色数量。
            dict_event["required_dispatches"] = len(  # 记录当前事件产生的角色数量。
                dict_result["required_dispatches"]  # 从派发结果计算准确数量。
            )

            # 保存当前事件是否阻断后续流程。
            dict_event["blocking"] = bool(dict_result["blocking"])  # 保存角色阻断是否传递到事件。

            # 无派发且未阻断的事件由 dispatcher 自行闭合。
            if not dict_result["required_dispatches"] and not dict_result["blocking"]:

                # 持久化配置声明的 zero-dispatch 事实。
                dict_event["recorded"] = True  # 标记事件已由 dispatcher 闭合。

                # 记录该事件没有创建 worker 动作。
                dict_event["no_action_taken"] = True  # 关闭等待 worker receipt 的分支。

                # 写入配置声明的零派发结论。
                dict_event["verdict"] = zero_dispatch_verdict()  # 固化 dispatcher-only 结果。

    # 提交事件结果和待派发队列到磁盘。
    _write_session(path_state, dict_session)

    # 返回主 Agent的角色派发决策。
    return dict_result
