"""承载 worker dispatch 的周期序列与派发前守卫。"""

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

# 守卫失败统一使用角色路由 shard 的结构化阻断结果。
try:
    from .worker_dispatch_event_routing import _block

# 脚本入口回退到同目录的角色路由 shard。
except ImportError:
    from worker_dispatch_event_routing import _block

# 事件去重由 session-start shard 保持单一实现，避免 guard 与 facade 循环依赖。
try:
    from .worker_dispatch_session_start import _remember_event

# 脚本入口回退到同目录的 session-start shard。
except ImportError:
    from worker_dispatch_session_start import _remember_event

# 校验 control boundary 的周期序号，阻止事件重放或跳号。
def _validate_periodic_sequence(
    event_type: str,
    dict_session: dict[str, Any],
    dict_payload: dict[str, object],
) -> int | None:
    """校验并返回当前 control boundary 的周期序号。

    参数:
        event_type: 当前事件类型。
        dict_session: 已绑定的 session 载荷。
        dict_payload: 已通过字段校验的事件载荷。
    返回:
        当前控制边界序号；非 control boundary 事件返回 None。
    异常:
        ValueError 表示周期序号重复、倒退或无法转换为整数。
    """

    # 非控制边界事件不参与周期序号校验。
    if event_type != CONTROL_BOUNDARY_EVENT:

        # 返回 None 让调用方保持原有 session 周期。
        return None

    # 读取 session 中上一次已确认的周期序号。
    int_previous_sequence = int(dict_session.get("periodic_sequence", 0))  # 已确认的 reviewer 周期边界。

    # 读取本次载荷声明的周期序号。
    int_current_sequence = int(dict_payload["periodic_sequence"])  # 本次请求推进的 reviewer 周期边界。

    # 重复或倒退的周期事件会破坏 reviewer 时序。
    if int_current_sequence <= int_previous_sequence:

        # 只接受严格递增的 control boundary。
        raise ValueError("> ERR: [Python] periodic_sequence must increase")

    # 返回通过校验的新序号，供去重成功后写回 session。
    return int_current_sequence

# 处理事件派发前的运行时、target、授权和去重阻断。
def _check_dispatch_guards(
    dict_result: dict[str, object],
    dict_session: dict[str, Any],

    # session 路径和已校验载荷决定阻断写回边界。
    path_state: Path,
    dict_payload: dict[str, object],

    # runtime 与授权快照共同决定是否允许进入角色路由。
    tuple_gate_inputs: tuple[list[str], dict[str, object]],
    event_type: str,
    str_event_id: str,
) -> dict[str, object] | None:
    """执行派发前的 fail-closed 守卫。

    参数:
        dict_result: 当前事件结果容器。
        dict_session: 已绑定的 session 载荷。
        path_state: session 持久化路径。
        dict_payload: 已通过字段校验的事件载荷。
        tuple_gate_inputs: 运行时错误列表和根 AGENTS 验证结果的组合。
        event_type: 当前事件类型。
        str_event_id: 当前事件摘要。
    返回:
        需要立即返回的阻断或重复结果；无早退时返回 None。
    """

    # 展开运行时和授权输入，保持守卫函数的接口边界稳定。
    list_runtime_errors, dict_validation = tuple_gate_inputs  # 展开 runtime 和授权门禁输入。

    # 环境漂移优先于任何 worker 派发，直接返回阻断。
    if list_runtime_errors:

        # 标记当前结果无效并保留全部环境错误。
        dict_result["valid"] = False  # 环境漂移使本次事件不能形成有效派发。

        # 环境漂移必须停止主 Agent后续动作。
        dict_result["blocking"] = True  # 标记事件不可继续执行。

        # 回传每一项运行时阻断原因。
        dict_result["errors"].extend(list_runtime_errors)  # 保留 runtime gate 的完整诊断。

        # 环境未恢复前不写入新的 worker 动作。
        return dict_result

    # target_lost 是显式的不可自动恢复边界。
    if bool(dict_payload.get("target_lost")):

        # 提取报告 target 丢失的 worker 身份。
        str_lost_worker = str(dict_payload.get("worker_id", ""))  # target 丢失报告中的 worker 身份。

        # 未知身份只能使用稳定的通用阻断标签。
        if str_lost_worker not in WORKER_NAMES:

            # 避免把未知输入映射到任意具体 worker。
            str_lost_worker = "canonical_worker"  # 未知角色不能被误归属到具体 worker。

        # target 丢失要求人工核验已有 agent，禁止自动重启。
        _block(
            dict_result,
            str_lost_worker,
            "canonical agent target is lost; verify the existing agent before retry",
        )

        # 持久化 target 丢失事件的阻断证据。
        _write_session(path_state, dict_session)

        # 在人工核验前停止当前事件。
        return dict_result

    # 根状态验证失败时不允许产生新的派发动作。
    if not dict_validation.get("valid"):

        # 标记状态快照无效并原样带回治理错误。
        dict_result["valid"] = False  # 授权快照失败使事件结果失去执行资格。

        # 授权快照失败必须停止 worker 派发。
        dict_result["blocking"] = True  # 保持 fail-closed 状态。

        # 回传根状态验证错误。
        dict_result["errors"].extend(dict_validation.get("errors", []))  # 保留 AGENTS 状态诊断。

        # 状态修复前停止事件。
        return dict_result

    # 去重检查保证同一事件只计算一次角色派发。
    if not _remember_event(dict_session, event_type, str_event_id):

        # 记录重复事件的无动作结果。
        dict_result["skipped_dispatches"].append(  # 保留重复事件的可追溯原因。
            {"reason": "event already recorded"}
        )

        # 持久化去重观察，保持 session 可追溯。
        _write_session(path_state, dict_session)

        # 重复事件不重新派发 worker。
        return dict_result

    # 所有派发前守卫均通过，调用方可以进入角色路由。
    return None

# 按事件集合调用 reviewer、tester 和 gardener dispatcher。
