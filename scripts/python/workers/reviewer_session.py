"""提供 reviewer_worker 的阶段触发决策，不改变根 AGENTS.md 的治理状态。"""

# 声明本模块使用的未来语法兼容行为。
from __future__ import annotations

# 导入阶段判断和正则校验所需的标准库能力。
import math
import re

# 导入结构化类型标注，保持 reviewer 输入输出契约可读。
from typing import Any

# 优先使用包内相对导入，兼容直接执行脚本的旧入口。
try:
    from .worker_dispatch_contracts import CANONICAL_WORKER_IDS, LIFECYCLE_PHASES, PHASE_BY_ROLE

# 直接执行时从同目录导入统一 dispatcher 合同。
except ImportError:
    from worker_dispatch_contracts import CANONICAL_WORKER_IDS, LIFECYCLE_PHASES, PHASE_BY_ROLE

# 允许进入 reviewer 生命周期的阶段名称集合。
REVIEW_PHASES: tuple[str, ...] = LIFECYCLE_PHASES  # reviewer 生命周期阶段。

# 周期 reviewer 的默认单调时间间隔为十分钟。
DEFAULT_REVIEW_INTERVAL_SECONDS: float = 600.0  # 周期复核的默认间隔秒数。

# 统一绑定当前唯一 reviewer worker 的身份标识。
DEFAULT_WORKER_ID: str = CANONICAL_WORKER_IDS.get("reviewer", "")  # reviewer worker 的协议身份。

# 只允许小写十六进制形式的 SHA-256 receipt 摘要。
SHA256_PATTERN: re.Pattern[str] = re.compile(r"^[0-9a-f]{64}$")  # receipt 摘要的格式约束。

# 这些原因表示 reviewer 的批准基线已经发生漂移。
BASELINE_MISMATCH_REASONS: frozenset[str] = frozenset(  # 基线漂移的稳定诊断集合。
    {
        "approved plan hash mismatch",  # 批准计划摘要不一致。
        "reviewer worker mismatch",  # reviewer 身份不一致。
        "review receipt hash mismatch",  # reviewer receipt 摘要不一致。
    }
)

# 校验 reviewer 会话是否仍绑定当前批准基线。
def _valid_session(
    dict_session: dict[str, Any],
    str_plan_sha256: str,
    str_worker_id: str,
) -> tuple[bool, str]:
    """验证会话是否仍绑定当前批准计划和 reviewer。

    参数:
        dict_session: 已解析的 reviewer 会话对象。
        str_plan_sha256: 当前批准计划的绑定摘要。
        str_worker_id: 当前允许执行复核的 worker 身份。

    返回:
        tuple[bool, str]: 会话有效标志及稳定原因文本。
    """

    # 会话必须首先满足对象类型约束，避免后续字段访问产生旁路异常。
    if not isinstance(dict_session, dict):

        # 非对象会话只能触发阻断式初始化。
        return False, "missing review session"

    # 会话必须携带可追踪的 reviewer 会话编号。
    if dict_session.get("review_session_id") in (None, ""):

        # 缺少编号时不能证明会话来源连续。
        return False, "missing review session id"

    # 会话中的计划摘要必须精确匹配当前批准基线。
    if dict_session.get("approved_plan_sha256") != str_plan_sha256:

        # 计划漂移要求重新执行阻断式 reviewer。
        return False, "approved plan hash mismatch"

    # 会话中的 worker 身份必须仍是当前唯一 reviewer。
    if dict_session.get("worker_id") != str_worker_id:

        # 身份漂移不能复用旧会话时间戳。
        return False, "reviewer worker mismatch"

    # 所有会话绑定字段一致时允许继续阶段决策。
    return True, "session valid"

# 校验 reviewer 阶段、计划和 worker 的绑定输入。
def _validate_phase_inputs(str_phase: str, str_plan_sha256: str, str_worker_id: str) -> None:
    """校验 reviewer 阶段和身份绑定输入。

    参数:
        str_phase: 当前 reviewer 生命周期阶段。
        str_plan_sha256: 当前批准计划的绑定摘要。
        str_worker_id: 当前 reviewer worker 身份。

    返回:
        None: 所有阶段和身份输入满足合同。

    异常:
        ValueError: 阶段、计划摘要或 worker 身份输入无效时抛出。
    """

    # 阶段名称必须来自受控生命周期集合。
    if not isinstance(str_phase, str) or str_phase not in REVIEW_PHASES:

        # 未知阶段不能被静默降级为周期复核。
        raise ValueError(f"> ERR: [Python] unknown reviewer phase: {str_phase}")

    # 计划摘要必须是非空字符串，作为会话绑定基线。
    if not isinstance(str_plan_sha256, str) or not str_plan_sha256:

        # 缺失计划基线时阻断 reviewer 决策。
        raise ValueError("> ERR: [Python] plan hash must be a non-empty string")

    # worker 身份必须是非空字符串，避免空身份复用会话。
    if not isinstance(str_worker_id, str) or not str_worker_id:

        # 缺失 worker 身份时不能建立 reviewer 责任链。
        raise ValueError("> ERR: [Python] worker id must be a non-empty string")

# 校验 reviewer 使用的单调时间和周期配置。
def _validate_clock_inputs(float_now_monotonic: float, float_interval_seconds: float) -> None:
    """校验 reviewer 单调时钟和周期间隔输入。

    参数:
        float_now_monotonic: 当前单调时钟读数。
        float_interval_seconds: PERIODIC 阶段的最小复核间隔。

    返回:
        None: 时间和间隔输入满足 reviewer 合同。

    异常:
        ValueError: 时间或间隔不是有限的非负数时抛出。
    """

    # 单调时间必须是有限数值，避免 NaN 绕过周期比较。
    if (
        isinstance(float_now_monotonic, bool)
        or not isinstance(float_now_monotonic, (int, float))
        or not math.isfinite(float_now_monotonic)
    ):

        # 无效时钟不能产生可审计的触发时间。
        raise ValueError("> ERR: [Python] now monotonic time must be finite")

    # 周期间隔必须是有限数值，防止无穷值改变触发语义。
    if (
        isinstance(float_interval_seconds, bool)
        or not isinstance(float_interval_seconds, (int, float))
        or not math.isfinite(float_interval_seconds)
    ):

        # 无效间隔不能用于周期门禁。
        raise ValueError("> ERR: [Python] review interval must be finite")

    # 负间隔会把未到期会话错误地视为已到期。
    if float_interval_seconds < 0:

        # 直接拒绝违反单调时间合同的配置。
        raise ValueError("> ERR: [Python] review interval must not be negative")

# 校验 reviewer receipt 的格式和大小写合同。
def _validate_receipt_input(str_receipt_sha256: str | None) -> None:
    """校验可选 reviewer receipt 摘要。

    参数:
        str_receipt_sha256: 可选的最近 reviewer receipt 摘要。

    返回:
        None: receipt 缺失或满足小写 SHA-256 格式。

    异常:
        ValueError: receipt 不是小写 SHA-256 字符串时抛出。
    """

    # receipt 必须是小写 SHA-256 字符串，拒绝非字符串和大小写变体。
    if str_receipt_sha256 is not None and (
        not isinstance(str_receipt_sha256, str)
        or not SHA256_PATTERN.fullmatch(str_receipt_sha256)
    ):

        # 不合规 receipt 不能参与 reviewer 会话比较。
        raise ValueError("> ERR: [Python] review receipt hash must be a lowercase SHA-256 string")

# 编排 reviewer 触发函数的输入类型和时间合同。
def _validate_trigger_inputs(
    str_phase: str,
    str_plan_sha256: str,
    float_now_monotonic: float,
    str_worker_id: str,
    float_interval_seconds: float,
    str_receipt_sha256: str | None,
) -> None:
    """校验 reviewer 触发决策的全部外部输入。

    参数:
        str_phase: 当前 reviewer 生命周期阶段。
        str_plan_sha256: 当前批准计划的绑定摘要。
        float_now_monotonic: 当前单调时钟读数。
        str_worker_id: 当前 reviewer worker 身份。
        float_interval_seconds: PERIODIC 阶段的最小复核间隔。
        str_receipt_sha256: 可选的最近 reviewer receipt 摘要。

    返回:
        None: 所有输入满足 reviewer 触发合同。

    异常:
        ValueError: 任一输入违反 reviewer 触发契约时抛出。
    """

    # 先检查阶段、计划和 worker 的身份边界。
    _validate_phase_inputs(str_phase, str_plan_sha256, str_worker_id)

    # 再检查单调时间和周期配置的数值边界。
    _validate_clock_inputs(float_now_monotonic, float_interval_seconds)

    # 最后检查可选 receipt 的不可变表示。
    _validate_receipt_input(str_receipt_sha256)

# 合并会话绑定和 receipt 一致性，得到当前 reviewer 基线状态。
def _session_binding_state(
    dict_session: dict[str, Any],
    str_plan_sha256: str,
    str_worker_id: str,
    str_receipt_sha256: str | None,
) -> tuple[bool, str]:
    """计算 reviewer 会话的计划、身份和 receipt 绑定状态。

    参数:
        dict_session: 已解析的 reviewer 会话对象。
        str_plan_sha256: 当前批准计划的绑定摘要。
        str_worker_id: 当前 reviewer worker 身份。
        str_receipt_sha256: 可选的最近 reviewer receipt 摘要。

    返回:
        tuple[bool, str]: 会话有效标志及稳定原因文本。
    """

    # 先验证计划和 worker 身份是否仍匹配批准基线。
    tuple_session_state = _valid_session(  # 当前 reviewer 会话的基础绑定结果。
        dict_session,  # 传入待核验的当前 reviewer 会话。
        str_plan_sha256,  # 传入本轮批准计划摘要。
        str_worker_id,  # 传入当前允许执行复核的身份。
    )

    # 提取可复用的会话有效标志。
    bool_session_valid: bool = tuple_session_state[0]  # 当前会话是否满足计划与身份绑定。

    # 提取当前会话的稳定诊断原因。
    str_session_reason: str = tuple_session_state[1]  # 当前会话绑定失败或成功的原因。

    # 只有外部提供 receipt 时才需要比较历史 receipt。
    if bool_session_valid and str_receipt_sha256 is not None:

        # 读取已有摘要，判断同一会话是否发生证据漂移。
        str_previous_receipt = str(dict_session.get("last_receipt_sha256", ""))  # 历史 reviewer receipt 摘要。

        # 不同 receipt 表示同一会话已经发生了证据漂移。
        if str_previous_receipt and str_previous_receipt != str_receipt_sha256:

            # 漂移会使后续触发进入阻断状态。
            bool_session_valid = False  # 当前会话不能继续作为有效基线。

            # 记录可被上层识别的稳定漂移原因。
            str_session_reason = "review receipt hash mismatch"  # receipt 摘要漂移导致基线失效。

    # 返回当前会话能否复用以及对应的审计原因。
    return bool_session_valid, str_session_reason

# 安全读取 reviewer 会话中的历史 receipt 摘要。
def _session_receipt_value(obj_session: object) -> str:
    """安全读取 reviewer 会话中的历史 receipt 摘要。

    参数:
        obj_session: 解析后的 reviewer 会话原始对象。

    返回:
        str: 对象型会话的历史 receipt 摘要；其他类型返回空字符串。
    """

    # 非对象会话只能提供空摘要，避免结果组装阶段再次抛出类型异常。
    if not isinstance(obj_session, dict):

        # 无效会话将由上层按初始化路径重新触发。
        return ""

    # 对象会话的摘要用于保持 reviewer 证据连续性。
    return str(obj_session.get("last_receipt_sha256", ""))

# 计算 PERIODIC 阶段的单调时间触发结果。
def _periodic_decision(
    dict_session: dict[str, Any],
    float_now_monotonic: float,
    float_interval_seconds: float,
) -> tuple[bool, str]:
    """根据历史单调时间决定周期 reviewer 是否到期。

    参数:
        dict_session: 已解析的 reviewer 会话对象。
        float_now_monotonic: 当前单调时钟读数。
        float_interval_seconds: PERIODIC 阶段的最小复核间隔。

    返回:
        tuple[bool, str]: 是否触发以及对应的稳定原因。
    """

    # 读取上一轮 reviewer 的单调时间戳。
    obj_last: object = dict_session.get("last_review_monotonic")  # 上一次 reviewer 单调时间戳。

    # 默认保持不触发，只有缺失、异常或到期时才提升状态。
    bool_trigger = False  # 当前周期窗口是否需要启动 reviewer。

    # 默认原因明确表示周期窗口尚未到期。
    str_reason = "periodic review interval not elapsed"  # 当前周期判断的稳定原因。

    # 没有时间戳表示从未完成过可复用的周期复核。
    if obj_last is None:

        # 首次周期复核需要触发但不额外设置阻断标志。
        bool_trigger = True  # 缺少历史时间戳时启动周期 reviewer。

        # 说明触发原因，供状态机和审计记录复用。
        str_reason = "periodic review has no previous timestamp"  # 首次周期复核缺少历史时间。

    # 非有限或非数值时间戳不能参与间隔计算。
    elif (
        isinstance(obj_last, bool)
        or not isinstance(obj_last, (int, float))
        or not math.isfinite(obj_last)
    ):

        # 异常历史状态必须重新触发周期复核。
        bool_trigger = True  # 无效历史时间戳触发修复性复核。

        # 保留明确原因，避免误报为普通到期。
        str_reason = "invalid previous review timestamp"  # 历史时间戳不能参与间隔运算。

    # 到期判断使用单调时钟，避免墙上时钟回拨影响门禁。
    elif float_now_monotonic - float(obj_last) >= float_interval_seconds:

        # 达到间隔后允许下一轮周期 reviewer。
        bool_trigger = True  # 周期复核时间窗口已到期。

        # 报告可审计的到期原因。
        str_reason = "periodic review interval elapsed"  # 单调时间已跨过复核间隔。

    # 尚未到期时保留默认的非阻断决策。
    return bool_trigger, str_reason

# 根据 reviewer 生命周期阶段计算触发决策。
def reviewer_trigger_decision(
    dict_session: dict[str, Any],

    # 当前 reviewer 生命周期阶段。
    str_phase: str,

    # 当前批准计划的绑定摘要。
    str_plan_sha256: str,

    # 当前单调时钟读数。
    float_now_monotonic: float,

    # 当前 reviewer worker 身份。
    str_worker_id: str = DEFAULT_WORKER_ID,

    # PERIODIC 阶段的最小复核间隔。
    float_interval_seconds: float = DEFAULT_REVIEW_INTERVAL_SECONDS,

    # 可选的最近 reviewer receipt 摘要。
    str_receipt_sha256: str | None = None,
) -> dict[str, object]:
    """根据阶段、计划哈希和单调时间决定是否触发 reviewer。

    参数:
        dict_session: 已解析的 reviewer 会话对象。
        str_phase: 当前生命周期阶段，必须属于 REVIEW_PHASES。
        str_plan_sha256: 当前批准计划的绑定摘要。
        float_now_monotonic: 当前单调时钟读数。
        str_worker_id: 当前 reviewer worker 身份。
        float_interval_seconds: PERIODIC 阶段的最小复核间隔。
        str_receipt_sha256: 可选的最近 reviewer receipt 摘要。

    返回:
        dict[str, object]: 包含 trigger、blocking、reason 和绑定摘要的决策对象。

    异常:
        ValueError: 阶段、绑定摘要、时间或间隔输入违反契约时抛出。
    """

    # 先执行所有外部输入门禁，再访问会话字段。
    _validate_trigger_inputs(
        str_phase,
        str_plan_sha256,
        float_now_monotonic,
        str_worker_id,
        float_interval_seconds,
        str_receipt_sha256,
    )

    # 计算当前会话是否仍能复用批准基线。
    tuple_session_state = _session_binding_state(  # reviewer 计划、身份和 receipt 绑定状态。
        dict_session,  # 本轮状态查询直接读取会话内容。
        str_plan_sha256,  # 使用同一批准摘要进行对照。
        str_worker_id,  # 使用当前 reviewer 身份进行对照。
        str_receipt_sha256,  # 复核新 receipt 与历史值的连续性。
    )

    # 提取会话有效标志供阶段状态机判断。
    bool_session_valid: bool = tuple_session_state[0]  # 当前会话是否仍满足 reviewer 绑定。

    # 提取会话绑定或漂移原因供最终机器结果复用。
    str_reason: str = tuple_session_state[1]  # 当前会话绑定或触发原因。

    # 默认不触发且不阻断，后续分支只提升这两个状态。
    bool_trigger = False  # 当前阶段是否需要启动 reviewer。

    # 强制阶段和基线漂移才会设置阻断标志。
    bool_blocking = False  # 当前 reviewer 是否阻断主流程。

    # 无效绑定必须立即要求阻断式 reviewer。
    if not bool_session_valid:

        # 绑定失效不能被周期时间窗口掩盖。
        bool_trigger = True  # 无效会话总是需要重新触发。

        # 计划、身份或 receipt 漂移均属于阻断条件。
        bool_blocking = True  # 绑定漂移必须阻断主流程。

    # INITIAL、CORRECTION 和 FINAL 都是强制复核阶段。
    elif str_phase in tuple(
        PHASE_BY_ROLE.get(str_role)
        for str_role in ("initial", "correction", "final")
        if PHASE_BY_ROLE.get(str_role)
    ):

        # 这些阶段不受周期时间戳抑制。
        bool_trigger = True  # 强制阶段总是启动 reviewer。

        # 强制阶段必须等待 reviewer 结论。
        bool_blocking = True  # 强制阶段阻断主流程。

        # 使用阶段名称生成稳定的人类可读原因。
        str_reason = f"{str_phase.lower()} review required"  # 强制阶段由阶段名标识复核要求。

    # PERIODIC 阶段只在时间窗口到期时触发。
    else:

        # 把周期时间判断结果纳入统一的状态输出。
        tuple_periodic_state = _periodic_decision(  # 当前 PERIODIC 阶段的时间判断结果。
            dict_session,  # 传入上一轮 reviewer 的会话时间。
            float_now_monotonic,  # 传入当前单调时钟读数。
            float_interval_seconds,  # 传入周期复核的最小间隔。
        )

        # 提取周期窗口是否到期的布尔结果。
        bool_trigger = tuple_periodic_state[0]  # 交给上层的周期触发布尔结果。

        # 提取周期判断给出的稳定原因文本。
        str_reason = tuple_periodic_state[1]  # 上层继续使用周期判断的稳定原因。

    # 汇总阶段、身份和 receipt 字段供调用方审计。
    return {
        "trigger": bool_trigger,
        "blocking": bool_blocking,
        "phase": str_phase,
        "worker_id": str_worker_id,
        "reason": str_reason,
        "plan_sha256": str_plan_sha256,
        "receipt_sha256": str_receipt_sha256 or _session_receipt_value(dict_session),
    }

# 判断 reviewer 触发结果是否表示批准基线漂移。
def is_baseline_mismatch(dict_decision: dict[str, object]) -> bool:
    """判断触发结果是否因计划、worker 或 receipt 绑定漂移而阻断。

    参数:
        dict_decision: reviewer_trigger_decision 返回的决策对象。

    返回:
        bool: 原因是否属于批准基线漂移集合。
    """

    # 只把预先登记的漂移原因识别为基线不匹配。
    return dict_decision.get("reason") in BASELINE_MISMATCH_REASONS
