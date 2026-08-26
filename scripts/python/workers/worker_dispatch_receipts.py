"""实现 worker receipt 的绑定、状态更新和公共 record 入口。"""

# 延迟解析类型注解，保持 receipt shard 与 Python 3.10 运行时兼容。
from __future__ import annotations

# cast 只记录兼容适配器的静态字段形状，不改变运行时值。
from typing import cast

# 事件与 receipt shard 共享同一份低层 session 和合同实现。
try:

    # 包内入口先导入 receipt 的类型和 verdict 合同。
    from .worker_dispatch_shared import (
        Any,
        GARDENER_RECEIPT_VERDICTS,
        Path,
        REVIEWER_RECEIPT_VERDICTS,
        SCHEMA_VERSION,
    )

    # 包内入口再导入 tester 合同和 session 辅助函数。
    from .worker_dispatch_shared import (
        TESTER_RECEIPT_VERDICTS,
        WORKER_NAMES,

        # session 读取和时间摘要校验共用同一低层边界。
        _bound_session,
        _require_monotonic,
        _require_sha256,
        _write_session,

        # tester 失败报告继续由 shared shard 统一校验。
        TESTER_FAILURE_VERDICTS,
        validate_tester_failure_report,
    )

    from .worker_dispatch_contracts import (
        CANONICAL_WORKER_IDS,
        PHASE_BY_ROLE,

        # receipt 结论依赖 worker 对齐和阻断策略。
        validate_worker_rejection_report,
        worker_alignment_verdict,
        worker_blocking_verdicts,
        worker_scope_rejection_verdict,
        zero_dispatch_verdict,
    )

    # receipt 异常结果复用事件 shard 的统一失败 schema。
    from .worker_dispatch_events import _failure_result

# 脚本入口没有 package context 时回退到同目录 shared shard。
except ImportError:

    # 同目录入口先导入 receipt 的类型和 verdict 合同。
    from worker_dispatch_shared import (
        Any,
        GARDENER_RECEIPT_VERDICTS,
        Path,
        REVIEWER_RECEIPT_VERDICTS,
        SCHEMA_VERSION,
    )

    # 同目录入口再导入 tester 合同和 session 辅助函数。
    from worker_dispatch_shared import (
        TESTER_RECEIPT_VERDICTS,
        WORKER_NAMES,

        # fallback session 读取和时间摘要沿用包内职责。
        _bound_session,
        _require_monotonic,
        _require_sha256,
        _write_session,

        # fallback tester 失败报告也必须使用同一校验合同。
        TESTER_FAILURE_VERDICTS,
        validate_tester_failure_report,
    )

    from worker_dispatch_contracts import (
        CANONICAL_WORKER_IDS,
        PHASE_BY_ROLE,

        # fallback 入口复用相同的 worker 结论处理函数。
        validate_worker_rejection_report,
        worker_alignment_verdict,
        worker_blocking_verdicts,
        worker_scope_rejection_verdict,
        zero_dispatch_verdict,
    )

    # 同目录入口使用事件 shard 的失败结果包装。
    from worker_dispatch_events import _failure_result

# worker session 的公开相对路径，避免在多个 receipt 返回对象中重复拼接。
WORKER_SESSION_STATE_PATH: Path = Path(".agents") / "worker-session.json"  # worker session 相对路径。

# reviewer 身份用于把 receipt 绑定到唯一方案复核角色。
REVIEWER_WORKER_ID: str = CANONICAL_WORKER_IDS.get("reviewer", "")  # reviewer receipt 绑定方案审查 target。

# tester 身份用于把失败报告绑定到唯一测试角色。
TESTER_WORKER_ID: str = CANONICAL_WORKER_IDS.get("tester", "")  # tester receipt 绑定测试阶段 target。

# gardener 身份用于区分只读范围拒绝与测试失败。
GARDENER_WORKER_ID: str = CANONICAL_WORKER_IDS.get("gardener", "")  # gardener receipt 绑定只读整理 target。

# FINAL 阶段名控制 reviewer 完成状态写回。
FINAL_PHASE: str = PHASE_BY_ROLE.get("final", "")  # reviewer 最终阶段名。

# reviewer 对齐 verdict 由合同函数计算，禁止复制字符串枚举。
REVIEWER_ALIGNMENT_VERDICT: str = worker_alignment_verdict(REVIEWER_WORKER_ID)  # reviewer 对齐结论。

# reviewer 阻断 verdict 集合由同一合同模块提供。
REVIEWER_BLOCKING_VERDICTS: frozenset[str] = worker_blocking_verdicts(REVIEWER_WORKER_ID)  # reviewer 阻断结论集合。

# 校验 receipt 输入并读取其绑定的 session 上下文。
def _prepare_receipt_context(
    project: str | Path,
    event_id: str, worker_id: str, agent_target: str,
    receipt_sha256: str, verdict: str, now_monotonic: float,
) -> tuple[str, str, float, Path, dict[str, Any]]:
    """准备 receipt 记录所需的摘要、时钟和 session。

    参数:
        project: 受管项目根路径。
        event_id: 已检查事件的摘要。
        worker_id: canonical worker 身份。
        agent_target: 主 Agent实际调用返回的 target。
        receipt_sha256: worker 回执摘要。
        verdict: worker 回执结论。
        now_monotonic: receipt 记录单调时间。
    返回:
        事件摘要、receipt 摘要、时钟、状态路径和 session 载荷。
    异常:
        ValueError 表示输入或 session 绑定无效。
    """

    # 先校验回执所属事件的摘要格式。
    str_event_id = _require_sha256(event_id, "event_id")  # 事件摘要是 receipt 的主键

    # 再校验 worker 回执内容摘要。
    str_receipt_sha256 = _require_sha256(  # receipt 摘要参与持久化去重
        receipt_sha256,  # 读取调用方提供的 receipt 摘要
        "receipt_sha256",  # 错误定位到 receipt 字段
    )

    # 实际 worker 身份必须属于 canonical 集合；无动作记录允许空身份。
    if worker_id and worker_id not in WORKER_NAMES:

        # 未知身份不能写入任何角色状态。
        raise ValueError(f"> ERR: [Python] unknown canonical worker: {worker_id}")

    # target 必须是字符串；普通派发的非空约束在事件读取后判断。
    if not isinstance(agent_target, str):

        # 非字符串 target 无法支持后续状态绑定。
        raise ValueError("> ERR: [Python] agent_target must be non-empty")

    # verdict 必须是非空、可追溯的收据结论。
    if not isinstance(verdict, str) or not verdict.strip():

        # 空结论不能闭合 dispatch 事件。
        raise ValueError("> ERR: [Python] worker verdict must be non-empty")

    # receipt 时间使用单调时钟，避免墙钟回拨破坏顺序。
    float_now = _require_monotonic(now_monotonic)  # 收据写入单调时间

    # 绑定当前项目的 session，拒绝跨项目写入。
    tuple_bound_session: tuple[Path, dict[str, Any]] = _bound_session(project)  # 取得 receipt 写回所需的已核对 session

    # 返回固定顺序的上下文，供闭合阶段共享同一绑定。
    return (
        str_event_id,
        str_receipt_sha256,
        float_now,
        tuple_bound_session[0],
        tuple_bound_session[1],
    )

# 从 session 中取得待记录的事件对象。
def _find_event_record(
    dict_session: dict[str, Any],
    str_event_id: str,
) -> dict[str, Any]:
    """按事件摘要读取 session 事件记录。

    参数:
        dict_session: 已通过绑定校验的 session。
        str_event_id: 要记录 receipt 的事件摘要。
    返回:
        匹配的事件字典。
    异常:
        ValueError 表示事件没有登记派发记录。
    """

    # 在已登记事件中按摘要查找唯一记录。
    dict_event = next(  # receipt 只能更新同摘要的事件
        (
            dict_candidate  # 候选事件记录
            for dict_candidate in dict_session.get("trigger_events", [])  # session 事件历史
            if isinstance(dict_candidate, dict)  # 忽略损坏的非字典条目
            and dict_candidate.get("event_id") == str_event_id  # 摘要匹配才可更新
        ),
        None,  # 没有匹配记录时交给显式错误分支
    )

    # 没有事件记录就没有可安全闭合的派发。
    if not isinstance(dict_event, dict):

        # 禁止把未知事件伪装成 pending dispatch。
        raise ValueError("> ERR: [Python] session event has no pending dispatch")

    # 返回经过结构确认的事件对象。
    return dict_event

# 校验 receipt verdict，防止未知结论污染 session 状态。
def _validate_receipt_verdict(
    dict_event: dict[str, Any],
    worker_id: str,
    verdict: str,
) -> None:
    """按 worker 和事件阶段拒绝未知 receipt 结论。

    参数:
        dict_event: 已登记的事件记录。
        worker_id: receipt 归属的 canonical worker。
        verdict: worker 返回的阶段结论。
    返回:
        None；合法结论继续进入状态更新。
    异常:
        ValueError: verdict 不属于当前 worker/phase 合同。
    """

    # 事件类型决定 tester 的 phase allowlist。
    str_event_type = str(dict_event.get("event_type", ""))  # 当前 receipt 所属事件类型。

    # 没有必需派发项时只能记录配置声明的无动作结论。
    if not dict_event.get("required_dispatches") and verdict == zero_dispatch_verdict():

        # 配置声明的无动作结论不进入任一 worker 的执行结论集合。
        return

    # reviewer 使用 profile 中的固定结论集合。
    if worker_id == REVIEWER_WORKER_ID:

        # reviewer 不能用任意成功文本绕过对齐状态。
        frozenset_allowed_verdicts: frozenset[str] = REVIEWER_RECEIPT_VERDICTS  # reviewer 分支的允许结论。

    # tester 的成功文本必须与 RED/GREEN/FINAL 阶段一致。
    elif worker_id == TESTER_WORKER_ID:

        # 从 TEST_* 事件名提取 tester 阶段。
        str_phase = str_event_type.removeprefix("TEST_")  # 当前 tester receipt 阶段。

        # 未登记阶段得到空集合，保持 fail-closed。
        frozenset_allowed_verdicts: frozenset[str] = TESTER_RECEIPT_VERDICTS.get(str_phase, frozenset())  # tester 当前阶段的允许结论。

    # gardener 使用只读分析器的固定结论集合。
    else:

        # gardener 未知结论不能进入 reviewed_event_ids。
        frozenset_allowed_verdicts: frozenset[str] = GARDENER_RECEIPT_VERDICTS  # gardener 分析分支的允许结论。

    # 未知结论在任何 worker/session 写入前被拒绝。
    if verdict not in frozenset_allowed_verdicts:

        # 错误文本包含 worker、phase 和 verdict，便于审计失败来源。
        raise ValueError(
            f"> ERR: [Python] {worker_id} verdict is not allowed for {str_event_type}: {verdict}"
        )

# 闭合没有实际派发动作的事件，并记录明确拒绝收据。
def _record_zero_dispatch(
    tuple_receipt_context: tuple[str, str, float, Path, dict[str, Any]],
    dict_event: dict[str, Any],
    worker_id: str,
    agent_target: str,
    verdict: str,
    failure_report: dict[str, Any] | None = None,
) -> dict[str, object]:
    """记录配置声明的 zero-dispatch 结果。

    参数:
        tuple_receipt_context: 已校验的 receipt 身份和 session 写入边界。
        dict_event: 当前事件记录。
        worker_id: receipt 归属 worker。
        agent_target: 主 Agent提供的 target。
        verdict: receipt 结论。
        failure_report: tester 失败时的结构化诊断报告。
    返回:
        无动作确认结果。
    异常:
        ValueError 表示零派发事件使用了错误 verdict。
    """

    # 零派发只能由 repair 配置声明的结论闭合。
    if verdict != zero_dispatch_verdict():

        # 其他结论无法证明没有调用 worker。
        raise ValueError("> ERR: [Python] zero-dispatch event requires configured no-dispatch verdict")

    # zero-dispatch 事件不能伪造任何 worker 或 agent target。
    if worker_id or agent_target:

        # 发现 target 即说明调用方误把普通派发当成无动作事件。
        raise ValueError("> ERR: [Python] NO_DISPATCH_REQUIRED must not carry a worker or agent target")

    # zero-dispatch 事件也不能携带 tester 失败报告。
    if failure_report is not None:

        # 失败报告只能属于真实 tester 派发结果。
        raise ValueError("> ERR: [Python] NO_DISPATCH_REQUIRED must not carry a worker failure report")

    # 标记零派发事件已经收到配置声明的无动作结论。
    dict_event["recorded"] = True  # 零派发拒绝完成事件闭合

    # 记录没有调用任何 worker 的事实。
    dict_event["no_action_taken"] = True  # 明确记录没有调用 worker

    # 可选诊断仍保留在事件收据中，避免主 Agent丢失上下文。
    if failure_report is not None:

        # 失败报告绑定当前 zero-dispatch 事件，供主 Agent继续修复。
        dict_event["failure_report"] = failure_report  # 零派发失败诊断

    # 先保存无动作证据，再返回结构化收据。
    _write_session(tuple_receipt_context[3], tuple_receipt_context[4])

    # 返回可供主 Agent审计的零派发确认。
    dict_result: dict[str, object] = {  # required_dispatches 为空时保留 no_action_taken 与 failure_report 的阻断事实
        "schema_version": SCHEMA_VERSION,  # zero-dispatch 持久化版本号
        "session_id": tuple_receipt_context[4]["session_id"],  # 未执行事件所属 session
        "event_id": tuple_receipt_context[0],  # 未执行事件摘要
        "event_type": dict_event.get("event_type"),  # 未执行事件类型
        "valid": True,  # 未执行收据合法标记
        "blocking": False,  # 无需 worker 时不阻断后续流程
        "worker_id": "",  # 无动作时不伪造 canonical worker
        "agent_target": agent_target,  # 无动作时保持空 target
        "receipt_sha256": tuple_receipt_context[1],  # 未执行收据摘要
        "verdict": verdict,  # dispatcher 配置声明的无动作结论
        "no_action_taken": True,  # 证明没有调用 worker
        "dispatcher_only": True,  # 明确该结果只属于 dispatcher 状态
        "state_path": str(WORKER_SESSION_STATE_PATH).replace("\\", "/"),  # 审计状态文件路径
    }

    # 有失败诊断时直接返回同一份结构化信息，避免主 Agent再次猜测原因。
    if failure_report is not None:

        # 把 tester 的细节报告公开在零派发确认中。
        dict_result["failure_report"] = failure_report  # 零派发失败报告

    # 返回已经完成绑定的 zero-dispatch 收据。
    return dict_result

# 解析当前事件允许接收 receipt 的 worker 集合。
def _pending_worker_ids(
    dict_session: dict[str, Any],
    str_event_id: str,
) -> list[object]:
    """返回当前事件的待回执 worker 身份。

    参数:
        dict_session: 当前 session 载荷。
        str_event_id: 当前事件摘要。
    返回:
        待回执 worker 身份列表。
    """

    # 只从当前事件的待派发索引提取角色。
    list_pending_workers = [  # receipt 对账使用的待回执角色
        dict_item.get("worker_id")  # 读取派发项中的角色字段
        for dict_item in dict_session.get("pending_dispatches", [])  # 遍历 session 待派发索引
        if isinstance(dict_item, dict)  # 忽略损坏派发项
        and dict_item.get("event_id") == str_event_id  # 只纳入同一事件摘要
    ]

    # 返回角色集合，供 target 漂移检查使用。
    return list_pending_workers

# 读取当前事件和 worker 对应的预期 target。
def _pending_worker_target(
    dict_session: dict[str, Any],
    str_event_id: str,
    worker_id: str,
) -> str:
    """返回当前 pending 派发项中的预期 target。

    参数:
        dict_session: 当前 session 载荷。
        str_event_id: 当前事件摘要。
        worker_id: receipt 归属 worker。
    返回:
        已持久化的 follow-up target；首次 spawn 或历史恢复返回空字符串。
    """

    # 只读取当前事件和角色的对账项，避免使用其他阶段的 target。
    dict_pending_item = next(  # 当前 receipt 对应的派发项。
        (
            dict_item  # 候选派发项。
            for dict_item in dict_session.get("pending_dispatches", [])  # 遍历当前 session 对账索引。
            if isinstance(dict_item, dict)  # 只让结构化对账项参与当前 receipt 的 target 查找。
            and dict_item.get("event_id") == str_event_id  # 绑定当前事件摘要。
            and dict_item.get("worker_id") == worker_id  # 绑定当前 worker 身份。
        ),
        None,  # 没有 pending 项时保留历史恢复语义。
    )

    # 首次 spawn 没有预期 target，允许 receipt 写入真实返回值。
    if not isinstance(dict_pending_item, dict):

        # 未找到当前对账项时由历史恢复逻辑继续判定是否合法。
        return ""

    # 读取当前阶段的持久 target，None 表示首次 spawn 而非字符串 target。
    value_expected_target = dict_pending_item.get("agent_target")  # 当前对账项的预期智能体标识。

    # 只有真实字符串 target 才能约束 follow-up receipt。
    return value_expected_target.strip() if isinstance(value_expected_target, str) else ""

# 处理单派发历史 session 的兼容恢复边界。
def _accept_pending_worker(
    dict_event: dict[str, Any],
    list_pending_workers: list[object],
    worker_id: str,
) -> None:
    """确认 worker 是否可为当前事件记录 receipt。

    参数:
        dict_event: 当前事件记录。
        list_pending_workers: 当前事件待回执角色。
        worker_id: receipt 提供的 worker 身份。
    返回:
        None。
    异常:
        ValueError 表示 target 不在允许的 pending 集合中。
    """

    # 已在 pending 集合中的 worker 直接进入记录阶段。
    if worker_id in list_pending_workers:

        # 现行 session 不需要历史恢复标志。
        return

    # 只允许旧版单派发未闭合状态进行一次恢复。
    bool_historical_recovery = (  # 单派发恢复必须同时满足三项条件
        not bool(dict_event.get("recorded"))  # 事件仍未闭合
        and not dict_event.get("dispatch_results")  # 尚无任何 receipt 结果
        and dict_event.get("required_dispatches") == 1  # 原事件只有一个角色
    )

    # 多派发、已有结果或已闭合事件禁止猜测 target。
    if not bool_historical_recovery:

        # 拒绝不在 pending 集合中的 worker。
        raise ValueError("> ERR: [Python] worker is not pending for event")

    # 保留历史恢复痕迹。
    dict_event["recovered_pending_dispatch"] = True  # 标记兼容恢复路径

    # 纳入本次单派发闭合集合。
    list_pending_workers.append(worker_id)  # 允许本次单派发 receipt 继续闭合

# 应用 reviewer receipt 对 session 基线和修复标志的影响。
def _apply_reviewer_receipt(
    dict_session: dict[str, Any],
    dict_worker: dict[str, Any],
    verdict: str,
    float_now: float,
) -> None:
    """更新 reviewer worker 的 session 状态。

    参数:
        dict_session: 当前 session 载荷。
        dict_worker: reviewer 状态记录。
        verdict: reviewer receipt 结论。
        float_now: receipt 单调时间。
    返回:
        None。
    """

    # 控制边界要读取 reviewer 最近结论。
    dict_session["reviewer_last_verdict"] = verdict  # 保存 reviewer 结论供下一次边界判断

    # ALIGNED 收据建立或恢复正常 reviewer 基线。
    if verdict == REVIEWER_ALIGNMENT_VERDICT:

        # 记录最近一次可用 reviewer 收据时间。
        dict_session["last_reviewer_monotonic"] = float_now  # 周期触发使用该时间

        # ALIGNED 结果开放 tester 的后续生命周期。
        dict_session["reviewer_initial_aligned"] = True  # 允许 tester 进入测试生命周期

        # 对齐结果清除历史 correction 阻断。
        dict_session["reviewer_correction_required"] = False  # 清除待修复标志

        # reviewer 当前阶段收到可接受收据。
        dict_worker["state"] = "completed"  # reviewer 当前阶段已闭合

    # 非 ALIGNED 收据必须保留 correction 阻断。
    else:

        # 非 ALIGNED 结果要求主流程先完成修复。
        dict_session["reviewer_correction_required"] = True  # 要求修复后重新复核

        # reviewer 当前阶段未通过，不能进入下一阶段。
        dict_worker["state"] = "failed"  # reviewer 当前阶段未通过

# 应用 tester receipt 对测试阶段和最终完成标志的影响。
def _apply_tester_receipt(
    dict_session: dict[str, Any],
    dict_worker: dict[str, Any],
    dict_event: dict[str, Any],
    str_event_id: str,
    str_receipt_sha256: str,
    verdict: str, failure_report: dict[str, Any] | None = None,
) -> None:
    """更新 tester 阶段记录。

    参数:
        dict_session: 当前 session 载荷。
        dict_worker: tester 状态记录。
        dict_event: 当前测试事件。
        str_event_id: 测试事件摘要。
        str_receipt_sha256: tester receipt 摘要。
        verdict: tester receipt 结论。
        failure_report: 失败结论对应的结构化诊断报告。
    返回:
        None。
    """

    # 从事件类型还原 RED/GREEN/FINAL 阶段名称。
    str_phase = str(dict_event.get("event_type", "")).removeprefix("TEST_")  # 用事件前缀定位 tester 阶段记录

    # RED、阻断和范围拒绝都不能把 tester 标成成功。
    if verdict in TESTER_FAILURE_VERDICTS:

        # 失败状态保留测试证据不足的事实。
        dict_worker["state"] = "failed"  # BLOCKED 或范围拒绝不能成为测试阶段证据

        # tester 失败后必须要求同一 reviewer 复核后续修正。
        dict_session["reviewer_correction_required"] = True  # 失败测试阻断恢复实现，直到 reviewer CORRECTION 对齐

    # 其余结论闭合本阶段 tester 状态。
    else:

        # 成功或可接受结论完成当前阶段。
        dict_worker["state"] = "completed"  # 当前 tester 阶段已收到有效收据

    # 按阶段持久化事件、receipt 和 verdict 三项证据。
    dict_tester_phase: dict[str, object] = {  # tester 阶段确认对象
        "event_id": str_event_id,  # 阶段证据回指不可变事件摘要
        "receipt_sha256": str_receipt_sha256,  # 阶段证据绑定 receipt 内容
        "verdict": verdict,  # 阶段证据保留 worker 结论
    }

    # 失败阶段必须把完整诊断放入 session，便于后续 correction 复核。
    if failure_report is not None:

        # 结构化报告与阶段摘要使用同一份绑定数据。
        dict_tester_phase["failure_report"] = failure_report  # 阶段失败诊断

    # 写入 tester 阶段索引，保留成功和失败两类结论。
    dict_session.setdefault("tester_phases", {})[str_phase] = dict_tester_phase  # 写入 tester 阶段索引

    # 只有非阻断 FINAL 才能开放完成请求。
    if str_phase == FINAL_PHASE and verdict not in TESTER_FAILURE_VERDICTS:

        # 标记测试面已经提供最终闭合证据。
        dict_session["tester_final_completed"] = True  # completion 依赖该最终标志

# 应用 gardener receipt 对去重集合的影响。
def _apply_gardener_receipt(
    dict_session: dict[str, Any],
    str_event_id: str,
    verdict: str,
) -> None:
    """记录成功 gardener 审查过的事件摘要。

    参数:
        dict_session: 当前 session 载荷。
        str_event_id: gardener 事件摘要。
        verdict: gardener receipt 结论。
    返回:
        None。
    """

    # 阻断或范围拒绝不应污染成功审查集合。
    if verdict in REVIEWER_BLOCKING_VERDICTS or verdict == worker_scope_rejection_verdict(GARDENER_WORKER_ID):

        # 保留失败 receipt，不把事件标成已审查。
        return

    # 读取或创建 gardener 事件去重集合。
    list_reviewed_events = dict_session.setdefault(  # 成功收据需要持久化去重状态
        "gardener_reviewed_event_ids",  # 固定集合字段
        [],  # 首次成功收据的初始集合
    )

    # 仅第一次成功 receipt 才追加事件摘要。
    if str_event_id not in list_reviewed_events:

        # 追加后续去重检查使用的审查证据。
        list_reviewed_events.append(str_event_id)

# 写入公共 receipt 状态并生成最终确认结果。
def _finalize_receipt(
    tuple_receipt_context: tuple[str, str, float, Path, dict[str, Any]],
    dict_event: dict[str, Any],

    # worker 身份和结论共同决定持久化状态迁移。
    worker_id: str,
    agent_target: str,
    verdict: str,

    # 两类可选报告分开保存，避免 tester 失败伪装成范围拒绝。
    failure_report: dict[str, Any] | None = None,
    rejection_report: dict[str, Any] | None = None,
) -> dict[str, object]:
    """移除 pending 项、闭合事件并返回 receipt 结果。

    参数:
        tuple_receipt_context: 已校验的 receipt 身份和 session 写入边界。
        dict_event: 当前事件记录。
        worker_id: receipt 归属 worker。
        agent_target: 主 Agent target。
        verdict: receipt 结论。
        failure_report: tester 失败时的结构化诊断报告。
        rejection_report: reviewer/gardener 范围拒绝时的独立诊断报告。
    返回:
        receipt 记录确认结果。
    """

    # 仅保留尚未收到本 worker receipt 的派发项。
    tuple_receipt_context[4]["pending_dispatches"] = [  # 重建剩余 receipt 对账队列
        dict_item  # 保留不属于本次完成动作的派发项
        for dict_item in tuple_receipt_context[4].get("pending_dispatches", [])  # 遍历已有对账队列
        if not (  # 删除同一事件和 worker 的已完成项
            isinstance(dict_item, dict)  # 损坏条目不匹配有效 receipt
            and dict_item.get("event_id") == tuple_receipt_context[0]  # 匹配本次事件摘要
            and dict_item.get("worker_id") == worker_id  # 匹配本次 worker 身份
        )
    ]

    # 没有剩余角色时才把事件标为 recorded。
    if not any(
        isinstance(dict_item, dict)  # 只读取合法的剩余对账项
        and dict_item.get("event_id") == tuple_receipt_context[0]  # 只检查本次事件
        for dict_item in tuple_receipt_context[4].get("pending_dispatches", [])  # 扫描剩余队列
    ):

        # 所有必需 receipt 已到达，事件正式闭合。
        dict_event["recorded"] = True  # 关闭事件的 pending 状态

    # 把 worker 状态和 receipt 历史写回磁盘。
    _write_session(tuple_receipt_context[3], tuple_receipt_context[4])

    # 任一实际 worker 范围拒绝都必须阻断，dispatcher-only zero-dispatch 走另一条路径。
    bool_scope_rejection = verdict == worker_scope_rejection_verdict(worker_id)  # 当前 worker 的范围拒绝结论

    # 返回机器可解析的 receipt 确认。
    dict_result: dict[str, object] = {  # 汇总已写回 session 的 worker receipt
        "schema_version": SCHEMA_VERSION,  # 最终 receipt schema 版本
        "session_id": tuple_receipt_context[4]["session_id"],  # 已写回结果所属 session
        "event_id": tuple_receipt_context[0],  # 已写回事件摘要
        "event_type": dict_event.get("event_type"),  # 已写回事件类型
        "valid": True,  # 最终收据合法标记
        "blocking": (  # 根据 canonical 失败集合和 reviewer 结论计算后续阻断
            verdict in TESTER_FAILURE_VERDICTS  # tester RED/BLOCKED 统一阻断
            or bool_scope_rejection  # 任一 worker SCOPE_REJECTED 统一阻断
            or verdict in REVIEWER_BLOCKING_VERDICTS  # reviewer 专属阻断结论
        ),
        "worker_id": worker_id,  # 已写回收据的角色
        "agent_target": agent_target,  # 已确认的 canonical target
        "receipt_sha256": tuple_receipt_context[1],  # 已绑定收据摘要
        "verdict": verdict,  # 已确认 worker 结论
        "state_path": str(WORKER_SESSION_STATE_PATH).replace("\\", "/"),  # 可复核状态文件路径
    }

    # 失败收据直接携带详细报告，主 Agent不必回读运行日志猜测问题。
    if failure_report is not None:

        # 将报告作为公开 receipt 字段返回给调用方。
        dict_result["failure_report"] = failure_report  # receipt 失败诊断

    # 非 tester 范围拒绝报告独立回传，避免主 Agent把拒绝误判为测试失败。
    if rejection_report is not None:

        # 保留违规、证据和同 target 重试指引。
        dict_result["rejection_report"] = rejection_report  # worker 范围拒绝诊断

    # 返回已持久化的最终 receipt 确认。
    return dict_result

# 校验并记录主 Agent 返回的真实 target 与 worker receipt。
def _normalize_record_arguments(
    tuple_receipt_arguments: tuple[object, ...],
    dict_receipt_options: dict[str, object],
) -> tuple[tuple[str | Path, str, str, str, str, str, float], dict[str, Any] | None, dict[str, Any] | None]:
    """把旧 positional/keyword 调用规范化为固定 receipt 输入。

    参数:
        tuple_receipt_arguments: 兼容旧入口的位置参数。
        dict_receipt_options: 兼容关键字入口的字段映射。
    返回:
        基础 receipt 参数、tester 失败报告和 worker 拒绝报告。
    异常:
        TypeError: 参数数量、名称或报告类型不符合兼容合同。
    """

    # 基础字段保持旧公共接口的固定顺序，报告字段单独延后处理。
    tuple_field_names: tuple[str, ...] = (  # 适配旧入口的七项身份输入，保证 receipt 绑定 session 时顺序不漂移。
        "project",  # 项目根用于定位受管 session 文件。
        "event_id",  # event id 作为 receipt 闭合的主键。
        "worker_id",  # worker id 决定职责和 verdict 合同。
        "agent_target",  # agent target 绑定同一 canonical 实例。
        "receipt_sha256",  # receipt 摘要用于阻止回执内容被替换。
        "verdict",  # verdict 决定阶段是否进入阻断状态。
        "now_monotonic",  # monotonic 时间用于复现事件顺序和间隔。
    )  # receipt 基础字段名称。

    # 位置调用必须提供七个基础字段，报告最多再提供两个字段。
    if tuple_receipt_arguments and len(tuple_receipt_arguments) not in {7, 8, 9}:

        # 参数数量错误不能进入状态写入逻辑。
        raise TypeError("> ERR: [Python] record_dispatch_result received an invalid positional argument count")

    # 位置参数可以与两个独立报告关键字组合，但不能覆盖基础身份字段。
    if tuple_receipt_arguments:

        # 只允许把可选报告追加到完整的七项基础调用后。
        set_allowed_options = {"failure_report", "rejection_report"}  # 可混用的报告字段集合

        # 基础字段关键字会造成位置和关键字的二义性，必须直接拒绝。
        if set(dict_receipt_options) - set_allowed_options:

            # 保持基础 receipt 身份只有一个明确来源。
            raise TypeError("> ERR: [Python] positional receipt fields cannot mix with base keyword fields")

    # 位置调用直接按历史顺序拆出基础字段和两个可选报告。
    if tuple_receipt_arguments:

        # 前七项保持原有 receipt 入口的参数顺序。
        tuple_base_arguments = cast(  # 将旧位置参数转换成内部固定字段形状。
            tuple[str | Path, str, str, str, str, str, float],  # 七个基础字段的静态形状。
            tuple_receipt_arguments[:7],  # 从旧位置参数截取基础字段。
        )  # 规范化后的基础 receipt 参数。

        # 第八项是 tester 失败报告，缺失时允许从关键字报告补齐。
        obj_failure_report: object = (
            tuple_receipt_arguments[7]  # 故障诊断从位置载荷进入状态机
            if len(tuple_receipt_arguments) in {8, 9}  # 第八项存在时走 tester 位置槽位
            else dict_receipt_options.get("failure_report")  # 关键字载荷提供故障诊断
        )  # 位置或关键字中的 tester 失败报告。

        # 第九项是 reviewer/gardener 拒绝报告，缺失时允许从关键字报告补齐。
        obj_rejection_report: object = (
            tuple_receipt_arguments[8]  # 拒绝诊断从位置载荷进入状态机
            if len(tuple_receipt_arguments) == 9  # 长调用才走拒绝位置槽位
            else dict_receipt_options.get("rejection_report")  # 关键字载荷提供拒绝诊断
        )  # 位置或关键字中的 worker 拒绝报告。

    # 没有位置参数时从关键字映射重建相同的基础字段顺序。
    else:

        # 关键字调用必须完整提供七个基础字段。
        list_missing_fields = [str_name for str_name in tuple_field_names if str_name not in dict_receipt_options]  # 缺失的基础字段。

        # 缺字段时在适配层拒绝隐式默认值。
        if list_missing_fields:

            # 调用方必须显式绑定全部 receipt 身份字段。
            raise TypeError(
                "> ERR: [Python] record_dispatch_result missing fields: "
                + ", ".join(list_missing_fields)
            )

        # 从关键字映射按固定顺序构造基础参数。
        tuple_base_arguments = cast(  # 将旧关键字参数转换成内部固定字段形状。
            tuple[str | Path, str, str, str, str, str, float],  # 七个关键字字段的静态形状。
            tuple(dict_receipt_options[str_name] for str_name in tuple_field_names),  # 按固定顺序提取字段。
        )  # 规范化后的关键字 receipt 参数。

        # 读取可选 tester 失败报告，不把缺失值改成空对象。
        obj_failure_report = dict_receipt_options.get("failure_report")  # 关键字 tester 失败报告。

        # 读取可选 worker 拒绝报告，不把缺失值改成空对象。
        obj_rejection_report = dict_receipt_options.get("rejection_report")  # 关键字 worker 拒绝报告。

    # 可选报告只能是映射或 None，阻断错误类型进入持久化。
    if obj_failure_report is not None and not isinstance(obj_failure_report, dict):

        # tester 报告类型错误不能被转换为字符串后继续。
        raise TypeError("> ERR: [Python] failure_report must be an object or null")

    # worker 拒绝报告同样必须保留结构化对象边界。
    if obj_rejection_report is not None and not isinstance(obj_rejection_report, dict):

        # 拒绝原因不能以非结构化文本伪装成完整报告。
        raise TypeError("> ERR: [Python] rejection_report must be an object or null")

    # 返回已检查的基础字段和两个独立报告。
    return (
        tuple_base_arguments,
        cast(dict[str, Any] | None, obj_failure_report),
        cast(dict[str, Any] | None, obj_rejection_report),
    )

# 准备 receipt 的身份、事件和 worker 结论，集中处理跨项目边界。
def _prepare_record_identity(
    tuple_receipt_arguments: tuple[str | Path, str, str, str, str, str, float],
) -> tuple[tuple[str, str, float, Path, dict[str, Any]], dict[str, Any], str, str, str]:
    """准备后续 receipt 状态机共享的身份上下文。

    参数:
        tuple_receipt_arguments: 公共接口规范化后的七项基础字段。
    返回:
        session 上下文、事件对象、worker 身份、target 和 verdict。
    异常:
        ValueError 表示 session、事件项目根或 receipt 身份不合法。
    """

    # 读取并校验受管 session、时钟和 receipt 摘要。
    tuple_receipt_context = _prepare_receipt_context(  # 绑定当前 receipt 的 session 上下文。
        *tuple_receipt_arguments,  # 展开已经规范化的七项身份字段。
    )

    # 读取当前 worker 身份，后续状态槽位由该值决定。
    str_worker_id: str = tuple_receipt_arguments[2]  # 当前 receipt 的 canonical worker 身份。

    # 保存主 Agent 返回的 canonical target。
    str_agent_target: str = tuple_receipt_arguments[3]  # 后续阶段必须继续复用的 worker target。

    # 保存 worker 返回的阶段结论。
    str_verdict: str = tuple_receipt_arguments[5]  # 决定 receipt 状态迁移的 worker verdict。

    # 按事件摘要取得已登记的事件对象。
    dict_event: dict[str, Any] = _find_event_record(  # 定位当前摘要对应的事件历史。
        tuple_receipt_context[4],  # 受管 session 载荷。
        tuple_receipt_context[0],  # 当前 receipt 绑定的事件摘要。
    )

    # 将 receipt 文件所属项目根与事件登记根绑定比较。
    path_receipt_project = tuple_receipt_context[3].parent.parent.resolve()  # 当前 receipt 所属项目根。

    # 读取事件创建时保存的项目根。
    str_event_project_root = str(dict_event.get("project_root", ""))  # 事件登记时的项目根摘要。

    # 跨项目复制不能获得当前 session 的写入资格。
    if str_event_project_root != str(path_receipt_project):

        # 在任何状态变更前拒绝跨项目 receipt。
        raise ValueError("> ERR: [Python] event project root does not match receipt project")

    # 先校验 verdict 合同，再进入 zero-dispatch 或 worker 状态分支。
    _validate_receipt_verdict(dict_event, str_worker_id, str_verdict)

    # 返回所有后续阶段共享的已校验身份。
    return (
        tuple_receipt_context,
        dict_event,
        str_worker_id,
        str_agent_target,
        str_verdict,
    )

# 校验 tester 失败报告、worker target 和范围拒绝报告。
def _validate_record_reports(
    dict_event: dict[str, Any],
    str_worker_id: str,
    str_agent_target: str,
    str_verdict: str,
    failure_report: dict[str, Any] | None,
    rejection_report: dict[str, Any] | None,
) -> None:
    """校验 receipt 进入 session 状态迁移前的报告字段。

    参数:
        dict_event: 当前事件对象。
        str_worker_id: 当前 canonical worker 身份。
        str_agent_target: 主 Agent 返回的 target。
        str_verdict: 当前 worker 结论。
        failure_report: tester 失败报告。
        rejection_report: worker 范围拒绝报告。
    返回:
        无；任何不一致都以 ValueError 终止状态迁移。
    异常:
        ValueError 表示报告、target 或 verdict 与事件合同不一致。
    """

    # tester 失败结论必须先通过详细 failure_report 校验。
    if str_worker_id == TESTER_WORKER_ID and str_verdict in TESTER_FAILURE_VERDICTS:

        # 读取报告字段级诊断。
        list_failure_report_errors = validate_tester_failure_report(failure_report)  # tester 失败报告错误集合。

        # 缺失任一必要字段都保持 fail-closed。
        if list_failure_report_errors:

            # 保留所有字段级原因供主 Agent修正后重传。
            raise ValueError(
                "> ERR: [Python] tester failure_report is incomplete: "
                + " | ".join(list_failure_report_errors)
            )

    # 普通派发必须携带非空 canonical target。
    if dict_event.get("required_dispatches") and not str_agent_target.strip():

        # 缺少 target 时不得进入 worker 状态机。
        raise ValueError("> ERR: [Python] agent_target must be non-empty for dispatched worker")

    # 只有普通派发事件才存在 worker 范围拒绝 verdict。
    str_scope_rejection = (
        worker_scope_rejection_verdict(str_worker_id)  # 从 worker 合同解析范围拒绝结论。
        if dict_event.get("required_dispatches")  # 普通派发事件使用 worker 拒绝合同。
        else ""  # zero-dispatch 事件没有 worker 身份。
    )

    # reviewer/gardener 范围拒绝必须携带独立 rejection_report。
    if str_verdict == str_scope_rejection:

        # 先校验拒绝报告字段完整性。
        list_rejection_errors = validate_worker_rejection_report(rejection_report)  # worker 拒绝报告错误集合。

        # 缺失拒绝证据时不得改变 session。
        if list_rejection_errors:

            # 保留字段级原因供同一 target 修正后重发。
            raise ValueError(
                "> ERR: [Python] worker rejection_report is incomplete: "
                + " | ".join(list_rejection_errors)
    )

# 迁移普通 worker receipt 的 target、事件历史和状态摘要。
def _record_pending_worker_state(
    tuple_receipt_context: tuple[str, str, float, Path, dict[str, Any]],
    dict_event: dict[str, Any],
    str_worker_id: str,
    str_agent_target: str,
    str_verdict: str,
) -> tuple[dict[str, Any], dict[str, object]]:
    """写入普通派发事件的 worker 状态和初始结果。

    参数:
        tuple_receipt_context: 已校验的 session 上下文。
        dict_event: 当前事件对象。
        str_worker_id: 当前 canonical worker 身份。
        str_agent_target: 主 Agent 返回的 target。
        str_verdict: 当前 worker 结论。
    返回:
        已更新的 worker 状态和事件派发结果对象。
    异常:
        ValueError 表示 target 不能沿现有 pending 队列继续。
    """

    # 读取当前事件还未收到 receipt 的 worker 集合。
    list_pending_workers = _pending_worker_ids(  # 读取当前事件的未闭合 worker 集合。
        tuple_receipt_context[4],  # 从当前 session 读取待闭合角色列表。
        tuple_receipt_context[0],  # 用事件摘要隔离本次 pending 队列。
    )

    # 定位当前 worker 的持久化状态槽位。
    dict_worker: dict[str, Any] = tuple_receipt_context[4]["worker_states"][str_worker_id]  # 当前 worker 的持久化状态槽位。

    # follow-up 必须沿用同一 canonical target。
    str_expected_target = _pending_worker_target(  # 读取 follow-up 必须复用的既有 target。
        tuple_receipt_context[4],  # 从 session 状态读取历史 target。
        tuple_receipt_context[0],  # 只读取同一事件的 target 绑定。
        str_worker_id,  # 以当前角色身份选择对应 target。
    )

    # target 替换会把 receipt 转移到未授权 Agent。
    if str_expected_target and str_agent_target != str_expected_target:

        # 在状态写入前拒绝 target substitution。
        raise ValueError("> ERR: [Python] agent_target does not match persisted worker target")

    # 校验 target 属于当前队列或允许的历史恢复路径。
    _accept_pending_worker(dict_event, list_pending_workers, str_worker_id)

    # 保存后续阶段需要复用的 canonical target。
    dict_worker["agent_target"] = str_agent_target  # 当前 worker 的连续 target。

    # 保存最近一次事件身份。
    dict_worker["last_event_id"] = tuple_receipt_context[0]  # 当前 worker 的最近事件。

    # 保存最近一次 receipt 摘要。
    dict_worker["last_receipt_sha256"] = tuple_receipt_context[1]  # 当前 worker 的最近 receipt。

    # 保存最近一次 verdict。
    dict_worker["last_verdict"] = str_verdict  # 当前 worker 的最近结论。

    # 保存后续周期计算使用的单调时间。
    dict_worker["last_monotonic"] = tuple_receipt_context[2]  # 当前 worker 的最近 receipt 时间。

    # 组合当前事件的 worker 状态，避免 follow-up 更换已绑定 target。
    dict_dispatch_result: dict[str, object] = {  # 合并当前事件的角色目标和阶段结论，避免回执在收尾后丢失换绑证据。
        "worker_id": str_worker_id,  # 将状态记录绑定到当前 canonical worker。
        "agent_target": str_agent_target,  # 保存 follow-up 必须复用的 target。
        "receipt_sha256": tuple_receipt_context[1],  # 固定本次 receipt 内容的完整摘要。
        "verdict": str_verdict,  # 记录该阶段是否进入阻断或闭合状态。
    }

    # 返回状态和基础事件结果，报告由独立 helper 挂载。
    return dict_worker, dict_dispatch_result

# 将两类结构化诊断挂载到事件历史。
def _attach_record_diagnostics(
    dict_dispatch_result: dict[str, object],
    failure_report: dict[str, Any] | None,
    rejection_report: dict[str, Any] | None,
) -> None:
    """复制并挂载 tester/worker 诊断，避免调用方后续修改历史。

    参数:
        dict_dispatch_result: 当前事件的派发结果对象。
        failure_report: tester 失败报告。
        rejection_report: worker 范围拒绝报告。
    返回:
        无。
    """

    # 失败诊断必须独立保留在事件历史中。
    if failure_report is not None:

        # 复制 tester 诊断，确保事件历史不受调用方后续修改影响。
        dict_dispatch_result["failure_report"] = dict(failure_report)  # 事件历史中的 tester 失败证据。

    # 范围拒绝诊断必须与失败报告分开保存。
    if rejection_report is not None:

        # 复制顶层对象，保留 worker 拒绝原因。
        dict_dispatch_result["rejection_report"] = dict(rejection_report)  # worker 拒绝诊断。

# 将 worker receipt 应用到角色生命周期状态并完成事件收尾。
def _apply_record_worker_receipt(
    tuple_receipt_context: tuple[str, str, float, Path, dict[str, Any]],
    dict_event: dict[str, Any],
    dict_worker: dict[str, Any],
    str_worker_id: str,
    str_verdict: str,
    failure_report: dict[str, Any] | None,
) -> None:
    """更新 reviewer、tester 和 gardener 的角色状态。

    参数:
        tuple_receipt_context: 已校验的 session 上下文。
        dict_event: 当前事件对象。
        dict_worker: 当前 worker 状态。
        str_worker_id: 当前 canonical worker 身份。
        str_verdict: 当前 worker 结论。
        failure_report: tester 失败报告。
    返回:
        无。
    """

    # reviewer receipt 更新对齐与 correction 生命周期。
    if str_worker_id == REVIEWER_WORKER_ID:

        # reviewer 分支由独立状态职责处理。
        _apply_reviewer_receipt(
            tuple_receipt_context[4],
            dict_worker,
            str_verdict,
            tuple_receipt_context[2],
        )

    # tester receipt 更新阶段状态和 FINAL 完成标志。
    if str_worker_id == TESTER_WORKER_ID:

        # tester 分支由独立阶段职责处理。
        dict_session = tuple_receipt_context[4]  # tester 状态要写回的受管 session。

        # tester 当前阶段需要沿同一事件摘要更新状态。
        str_event_id = tuple_receipt_context[0]  # tester 当前阶段绑定的事件摘要。

        # tester receipt 摘要用于绑定本次状态迁移。
        str_receipt_digest = tuple_receipt_context[1]  # tester 当前 receipt 的内容摘要。

        # 以固定参数顺序提交 tester 状态迁移。
        _apply_tester_receipt(
            dict_session,  # tester 状态写回的 session。
            dict_worker,  # tester 的持久化状态槽位。
            dict_event,  # 当前测试事件对象。

            # 事件与 receipt 摘要共同确定本次测试状态迁移。
            str_event_id,  # 当前测试事件摘要。
            str_receipt_digest,  # 当前 tester receipt 摘要。

            # verdict 与失败诊断共同决定 tester 是否进入阻断态。
            str_verdict,  # 当前 tester 阶段结论。
            failure_report,  # 当前 tester 失败诊断。
        )

    # gardener receipt 更新事件去重集合。
    if str_worker_id == GARDENER_WORKER_ID:

        # gardener 分支由独立去重职责处理。
        _apply_gardener_receipt(
            tuple_receipt_context[4],
            tuple_receipt_context[0],
            str_verdict,
        )

# 记录已规范化的 target 和 worker receipt。
def _record_dispatch_result_impl(
    tuple_receipt_arguments: tuple[str | Path, str, str, str, str, str, float],
    failure_report: dict[str, Any] | None,
    rejection_report: dict[str, Any] | None,
) -> dict[str, object]:
    """记录真实 target 和 worker receipt。

    参数:
        tuple_receipt_arguments: 按公共接口顺序排列的项目、事件、worker、target、摘要、结论和时钟。
        failure_report: tester 失败结论对应的详细诊断报告。
        rejection_report: reviewer/gardener 范围拒绝对应的详细诊断报告。
    返回:
        record 确认结果。
    异常:
        ValueError 表示 target、receipt、事件或身份无效。
    """

    # 准备 receipt 的身份和事件上下文。
    tuple_record_identity = _prepare_record_identity(tuple_receipt_arguments)  # 已校验的身份和事件上下文。

    # session 上下文绑定后续状态迁移的写入边界。
    tuple_receipt_context = tuple_record_identity[0]  # 当前 session、时钟和 receipt 摘要。

    # 事件对象承载 pending、dispatch_results 和 recorded 状态。
    dict_event = tuple_record_identity[1]  # 当前事件历史对象。

    # worker 身份选择对应的 canonical 状态槽位。
    str_worker_id = tuple_record_identity[2]  # 从绑定身份元组取状态槽位键。

    # target 必须沿现有 canonical worker 连续使用。
    str_agent_target = tuple_record_identity[3]  # follow-up 是否沿原 Agent继续的 target。

    # verdict 决定当前阶段的状态迁移结果。
    str_verdict = tuple_record_identity[4]  # 当前 receipt 的 worker 结论。

    # 校验报告、target 和范围拒绝边界。
    _validate_record_reports(
        dict_event,
        str_worker_id,
        str_agent_target,
        str_verdict,
        failure_report,
        rejection_report,
    )

    # 没有待派发项的事件交给 zero-dispatch 专用闭合逻辑。
    if not dict_event.get("required_dispatches"):

        # 无派发事件不能携带 worker、target 或拒绝报告。
        if str_worker_id or str_agent_target or rejection_report is not None:

            # 把无动作事件误用为 worker receipt 会破坏审计语义。
            raise ValueError("> ERR: [Python] NO_DISPATCH_REQUIRED cannot contain worker, target, or rejection fields")

        # SCOPE_REJECTED 是唯一允许的无动作收据。
        return _record_zero_dispatch(
            tuple_receipt_context,
            dict_event,
            str_worker_id,
            str_agent_target,
            str_verdict,
            failure_report,
        )

    # 更新普通派发事件的 worker 状态和基础结果。
    tuple_worker_state = _record_pending_worker_state(  # 先对账状态，避免诊断挂载改变 target 事实。
        tuple_receipt_context,  # 使用已绑定的 session 上下文。
        dict_event,  # 针对当前事件更新状态。
        str_worker_id,  # 选择目标 worker 状态槽位。
        str_agent_target,  # 检查当前 follow-up target。
        str_verdict,  # 保留本次阶段结论。
    )

    # 取出已更新的 worker 状态槽位。
    dict_worker = tuple_worker_state[0]  # 当前 worker 的连续状态。

    # 取出待挂载诊断的事件结果。
    dict_dispatch_result = tuple_worker_state[1]  # 当前派发结果。

    # 将 tester/worker 诊断挂载到事件结果。
    _attach_record_diagnostics(
        dict_dispatch_result,
        failure_report,
        rejection_report,
    )

    # 保存事件派发历史。
    dict_event.setdefault("dispatch_results", []).append(dict_dispatch_result)

    # 应用角色状态迁移。
    _apply_record_worker_receipt(
        tuple_receipt_context,
        dict_event,
        dict_worker,
        str_worker_id,
        str_verdict,
        failure_report,
    )

    # 移除 pending、标记事件并返回最终 receipt。
    return _finalize_receipt(
        *tuple_record_identity,  # 复用已校验的 session、事件、worker、target 和 verdict。
        failure_report,  # 保留失败诊断，便于后续修复。
        rejection_report,  # 保留范围拒绝的重试依据。
    )

# 对外暴露 receipt 记录接口，并把异常转成阻断结果。
def record_dispatch_result(*receipt_arguments: object, **receipt_options: object) -> dict[str, object]:
    """记录 target/receipt，兼容旧 positional/keyword 调用并返回阻断 JSON。

    参数:
        receipt_arguments: 旧接口顺序传入的基础字段和可选报告。
        receipt_options: 基础字段或两类报告的关键字映射。
    返回:
        record 确认或结构化阻断结果。
    """

    # 记录失败时先保存可用于结构化错误的项目根。
    str_project_root: str = str(  # 规范化失败结果使用的项目根文本。
        receipt_arguments[0]  # 位置调用的项目根
        if receipt_arguments  # 位置参数存在时优先绑定项目根
        else receipt_options.get("project", ".")  # 关键字调用的项目根
    )  # 失败结果使用的项目根文本。

    # 正常路径交给内部 receipt 记录实现。
    try:

        # 兼容适配器把两种调用形式收束为固定内部输入。
        tuple_normalized_arguments = _normalize_record_arguments(  # 规范化后的 receipt 调用参数。
            tuple(receipt_arguments),  # 保留调用者的位置参数顺序。
            dict(receipt_options),  # 复制关键字映射，避免内部修改调用方对象。
        )

        # 拆出基础字段和两类独立报告。
        tuple_base_arguments = tuple_normalized_arguments[0]  # 基础 receipt 身份字段。

        # 取出 tester 失败报告，后续只在失败 verdict 下校验它。
        dict_failure_report = tuple_normalized_arguments[1]  # tester 失败报告。

        # worker rejection report 保持与 tester failure report 分离。
        dict_rejection_report = tuple_normalized_arguments[2]  # worker 范围拒绝报告。

        # 持久化真实 target 和 worker 收据。
        return _record_dispatch_result_impl(
            tuple_base_arguments,
            dict_failure_report,
            dict_rejection_report,
        )

    # 公共接口把记录异常转换为结构化阻断。
    except (TypeError, ValueError, OSError) as object_error:

        # 错误结果绑定已解析的项目根，避免异常处理再触发未定义变量。
        return _failure_result(str_project_root, "record", object_error)
