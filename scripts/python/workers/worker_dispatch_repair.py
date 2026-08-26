"""实现 canonical worker repair follow-up 的状态机。"""

# 延迟解析类型注解，保持脚本和包导入均兼容 Python 3.10。
from __future__ import annotations

# repair shard 只读取配置和 session 共享入口，不复制状态机合同。
try:

    # 包内入口使用受管相对导入。
    from .worker_dispatch_contracts import worker_repair_config
    from .worker_dispatch_shared import _bound_session, _write_session

# 脚本入口由调用方登记 worker 目录后回退到同目录导入。
except ImportError:

    # 同目录入口保留兼容导入路径。
    from worker_dispatch_contracts import worker_repair_config
    from worker_dispatch_shared import _bound_session, _write_session

# 规范化 worker target，避免空值绕过同一 Agent 绑定。
def _normalized_target(value_target: object) -> str:
    """返回非空 target 文本，拒绝把空值转换为字符串 ``None``。

    参数：value_target 为 worker 状态或 receipt 中的候选 target。
    返回：去除外围空白的 target 文本；非字符串输入返回空文本。
    """

    # 非字符串状态值不能作为可复用的 Agent 身份。
    if not isinstance(value_target, str):

        # 将 None 或其他错误类型收敛为空 target。
        return ""

    # 保留有效 target 的稳定文本形式。
    return value_target.strip()

# 从结构化 worker 记录中读取兼容 target 字段。
def _target_from_mapping(
    value_mapping: object,
    tuple_target_keys: tuple[str, ...],
) -> str:
    """从一个结构化对象读取第一个有效 target。

    参数：value_mapping 为 worker、pending 或 receipt 对象；tuple_target_keys 为兼容字段顺序。
    返回：第一个非空 target；对象类型或字段均不匹配时返回空文本。
    """

    # 非对象不能提供 target 字段。
    if not isinstance(value_mapping, dict):

        # 让调用方继续检查其他受控来源。
        return ""

    # 兼容不同历史字段名，但始终保持配置声明的优先顺序。
    for str_target_key in tuple_target_keys:

        # 规范化当前字段，避免 None 变成可误用文本。
        str_target = _normalized_target(value_mapping.get(str_target_key))  # 当前字段 target

        # 找到有效 target 后停止读取其他别名。
        if str_target:

            # 返回当前 worker 已确认的 canonical target。
            return str_target

    # 所有候选字段均为空时返回明确的空值。
    return ""

# 从 pending 队列恢复同一事件的 target。
def _pending_worker_target(
    dict_session: dict[str, object],
    str_event_id: str,
    str_worker_id: str,
    tuple_target_keys: tuple[str, ...],
) -> str:
    """从 pending dispatch 队列读取同一事件的 target。

    参数：dict_session 为当前 session；str_event_id 和 str_worker_id 绑定对账项；tuple_target_keys 为字段顺序。
    返回：同一事件的第一个有效 target；没有匹配项时返回空文本。
    """

    # 读取待回执项并保持非对象条目可跳过。
    list_pending_dispatches = dict_session.get("pending_dispatches", [])  # 当前 pending 队列

    # 只有列表形式的 pending 才能继续扫描。
    if not isinstance(list_pending_dispatches, list):

        # 损坏的 pending 根类型不能参与 target 恢复。
        return ""

    # 按 pending 原始顺序寻找同事件 target。
    for dict_pending in list_pending_dispatches:

        # 非目标事件或错误类型不能参与当前修复。
        if not (
            isinstance(dict_pending, dict)
            and dict_pending.get("event_id") == str_event_id
            and dict_pending.get("worker_id") == str_worker_id
        ):

            # 继续检查当前队列中的其他对账项。
            continue

        # 读取 pending 中保存的 canonical target。
        str_agent_target = _target_from_mapping(dict_pending, tuple_target_keys)  # 当前对账项的 canonical target

        # 只有同一事件 target 才能结束 pending 扫描。
        if str_agent_target:

            # 同一事件已有 target 时停止队列扫描。
            return str_agent_target

    # 队列没有提供有效 target 时返回空文本。
    return ""

# 从 trigger_events/events 的 dispatch_results 恢复同一事件 target。
def _history_worker_target(
    dict_session: dict[str, object],
    str_event_id: str,
    str_worker_id: str,
    tuple_target_keys: tuple[str, ...],
) -> str:
    """从同一事件的历史 receipt 读取 canonical target。

    参数：dict_session 为当前 session；str_event_id 和 str_worker_id 绑定历史范围；tuple_target_keys 为字段顺序。
    返回：同一事件的第一个有效 target；没有匹配项时返回空文本。
    """

    # 兼容当前 session 的两种历史集合字段。
    tuple_event_collections = (
        dict_session.get("trigger_events", []),  # 当前 trigger 事件历史
        dict_session.get("events", []),  # 兼容旧事件历史
    )  # 同 session 事件集合

    # 只检查同一事件，禁止从其他事件借用 target。
    for list_events in tuple_event_collections:

        # 损坏的兼容集合不参与恢复。
        if not isinstance(list_events, list):

            # 继续检查另一个受控集合。
            continue

        # 按历史顺序检查当前集合中的事件。
        for dict_event in list_events:

            # 其他事件或错误类型不能参与当前修复。
            if not (
                isinstance(dict_event, dict)
                and dict_event.get("event_id") == str_event_id
            ):

                # 继续检查当前集合的下一条事件。
                continue

            # 读取同一事件保存的首次 dispatch results。
            list_dispatch_results = dict_event.get("dispatch_results", [])  # 同事件 receipt 历史

            # 只有列表形式的历史才能继续读取 receipt。
            if not isinstance(list_dispatch_results, list):

                # 错误的历史根类型不能参与 target 恢复。
                continue

            # 按 receipt 写入顺序寻找当前 worker 的 target。
            for dict_result in list_dispatch_results:

                # 其他 worker 的 receipt 不能替换当前 target。
                if not (
                    isinstance(dict_result, dict)
                    and dict_result.get("worker_id") == str_worker_id
                ):

                    # 继续检查同事件下一个 receipt。
                    continue

                # 从历史 receipt 读取 canonical target。
                str_agent_target = _target_from_mapping(dict_result, tuple_target_keys)  # 同事件同 worker 的历史 target

                # 找到有效历史 target 后停止 receipt 扫描。
                if str_agent_target:

                    # 返回同一 worker 的首次有效 target。
                    return str_agent_target

    # 历史 receipt 没有提供有效 target 时返回空文本。
    return ""

# 沿 worker 状态、pending 和历史 receipt 恢复同一 target。
def _resolve_worker_target(
    dict_session: dict[str, object],
    str_event_id: str,
    str_worker_id: str,
) -> tuple[object, str]:
    """按 worker 状态、pending 和同事件历史恢复 target。

    参数：dict_session 为当前绑定 session；str_event_id 为待修复事件；str_worker_id 为 canonical worker。
    返回：worker 状态对象和可复用 target 组成的二元组。
    """

    # 统一历史字段名，防止修复路径跨事件换绑。
    tuple_target_keys = ("agent_target", "last_agent_target", "target")  # target 兼容字段顺序

    # worker 状态是恢复 target 的第一事实来源。
    dict_worker_states = dict_session.get("worker_states", {})  # session worker 状态映射

    # 从 worker 状态映射读取当前 canonical worker。
    dict_worker = dict_worker_states.get(str_worker_id) if isinstance(dict_worker_states, dict) else None  # 当前 worker 状态记录

    # 优先使用 worker 状态中已确认的 canonical target。
    str_agent_target = _target_from_mapping(dict_worker, tuple_target_keys)  # 状态中可复用的 Agent 目标身份

    # 首次 receipt 可能只把 target 写入同一事件的 pending 队列。
    if not str_agent_target:

        # pending 仅作为首次 receipt 的同事件兜底来源。
        str_agent_target = _pending_worker_target(  # 从 pending 恢复同事件 target
            dict_session,  # pending 恢复使用的 session 对象
            str_event_id,  # pending 绑定的事件摘要
            str_worker_id,  # pending 绑定的 worker 身份
            tuple_target_keys,  # pending 兼容 target 字段
        )

    # 首次 receipt 也可能只写入同一事件的历史 dispatch_results。
    if not str_agent_target:

        # 历史集合仅作为 pending 缺失时的同事件兜底来源。
        str_agent_target = _history_worker_target(  # 从 receipt 历史恢复同事件 target
            dict_session,  # 历史 receipt 使用的 session 对象
            str_event_id,  # 历史查询的事件摘要
            str_worker_id,  # 历史查询的 worker 身份
            tuple_target_keys,  # 历史兼容 target 字段
        )

    # 返回 worker 状态和恢复结果，由主状态机统一判断缺失边界。
    return dict_worker, str_agent_target

# 构造统一 repair 阻断结果。
def _repair_error(str_message: str) -> dict[str, object]:
    """构造统一 repair 阻断结果。

    参数：str_message 为面向主 Agent 的具体错误文本。
    返回：固定 valid/blocking/errors 字段的失败映射。
    """

    # 保持所有 repair 失败路径具有同一机器合同。
    return {
        "valid": False,
        "blocking": True,
        "errors": [str_message],
    }

# 读取并校验 repair 配置的核心字段。
def _repair_contract_fields(
    dict_repair: dict[str, object],
) -> tuple[dict[str, object], str, list[object], list[object]] | None:
    """读取并校验 repair 配置的核心字段。

    参数：dict_repair 为 worker repair.json 的对象。
    返回：熔断配置、target 策略、保留字段和替换字段；配置不完整时返回 None。
    """

    # 读取 repair 状态机的熔断配置。
    dict_breaker = dict_repair.get("circuit_breaker")  # 当前熔断配置

    # 读取 canonical target 复用策略。
    str_target_policy = dict_repair.get("target_policy")  # 当前 target 复用策略

    # 读取 receipt 中必须保持的字段集合。
    list_preserve_fields = dict_repair.get("preserve_fields")  # receipt 保留字段

    # 读取 repair 允许替换的字段集合。
    list_replace_fields = dict_repair.get("replace_fields")  # repair 替换字段

    # 所有字段类型必须明确，不能由 repair 路径猜测默认值。
    if (
        not isinstance(dict_breaker, dict)
        or not isinstance(str_target_policy, str)
        or not str_target_policy.strip()
        or not isinstance(list_preserve_fields, list)
        or not isinstance(list_replace_fields, list)
    ):

        # 缺失配置直接阻断，不创建不可审计的 follow-up。
        return None

    # 返回已经完成类型检查的 repair 核心字段。
    return dict_breaker, str_target_policy, list_preserve_fields, list_replace_fields

# 持久化 repair 尝试次数与熔断窗口。
def _register_repair_attempt(
    path_session: object,
    dict_session: dict[str, object],
    str_event_id: str,
    str_worker_id: str,
    dict_breaker: dict[str, object],
    int_max_attempts: object,
) -> dict[str, object]:
    """持久化 repair 尝试次数与熔断窗口。

    参数：
        path_session 为 session 文件；dict_session 为 session 对象。
        str_event_id 和 str_worker_id 绑定当前事件；dict_breaker 为熔断配置。
        int_max_attempts 为最大尝试次数。
    返回：包含 retry_count、failure_window、reset_requires_new_event 的结果，失败时返回阻断映射。
    """

    # 读取失败窗口长度。
    int_failure_window = dict_breaker.get("failure_window")  # 当前失败窗口长度

    # 读取窗口熔断阈值。
    int_open_after = dict_breaker.get("open_after")  # 当前熔断开启阈值

    # 读取新事件是否重置失败窗口的策略。
    bool_reset_requires_new_event = dict_breaker.get("reset_requires_new_event")  # 新事件窗口策略

    # retry 配置必须完整且使用严格类型。
    if (
        not isinstance(int_max_attempts, int)
        or not isinstance(int_failure_window, int)
        or int_failure_window < 1
        or not isinstance(int_open_after, int)
        or not isinstance(bool_reset_requires_new_event, bool)
    ):

        # 不能使用不完整阈值继续发送 repair 消息。
        return _repair_error("> ERR: [Python] repair retry limits are invalid")

    # 以 event/worker 组合键保存可审计尝试次数。
    dict_attempts = dict_session.setdefault("repair_attempts", {})  # 当前 repair 尝试映射

    # retry 状态必须保持对象根类型。
    if not isinstance(dict_attempts, dict):

        # 损坏的 retry 状态不能被转换为默认字典。
        return _repair_error("> ERR: [Python] repair attempts state is invalid")

    # 当前事件的 retry 次数严格递增并绑定 worker。
    str_attempt_key = f"{str_event_id}:{str_worker_id}"  # 绑定事件和 worker 的 retry 计数键

    # 读取并递增当前事件的 retry 次数。
    int_attempt = int(dict_attempts.get(str_attempt_key, 0)) + 1  # 当前 retry 次数

    # 窗口历史按 worker 保存，支持配置声明的新事件重置。
    dict_history = dict_session.setdefault("repair_history", {})  # 当前 worker repair 历史

    # 历史根类型错误时不能静默重置状态。
    if not isinstance(dict_history, dict):

        # 损坏的历史不能被静默替换。
        return _repair_error("> ERR: [Python] repair history state is invalid")

    # 读取当前 worker 的失败窗口列表。
    list_history = dict_history.setdefault(str_worker_id, [])  # 当前 worker 失败窗口

    # worker 历史必须保持列表类型。
    if not isinstance(list_history, list):

        # 错误类型必须阻断后续 retry。
        return _repair_error("> ERR: [Python] repair worker history is invalid")

    # 新 event_id 按配置清除旧事件窗口，仅在事件切换时重置。
    if bool_reset_requires_new_event and list_history and list_history[-1] != str_event_id:

        # 当前事件开启新的失败窗口。
        list_history.clear()

    # 追加当前事件并裁剪超过配置长度的旧记录。
    list_history.append(str_event_id)
    del list_history[:-int_failure_window]

    # 在生成 follow-up 前持久化 retry 状态，防止重复调用绕过熔断。
    dict_attempts[str_attempt_key] = int_attempt  # 写回当前事件尝试次数

    # 把 retry 状态写回绑定 session 文件。
    _write_session(path_session, dict_session)

    # 返回 retry 状态供主流程判断熔断和构造消息。
    return {
        "valid": True,
        "retry_count": int_attempt,
        "failure_window": int_failure_window,
        "open_after": int_open_after,
        "reset_requires_new_event": bool_reset_requires_new_event,
        "history_length": len(list_history),
    }

# 用同一 target 重新登记 repair pending dispatch。
def _append_repair_pending(
    path_session: object,
    dict_session: dict[str, object],
    str_event_id: str,
    str_worker_id: str,
    str_phase: str,
    str_agent_target: str,
) -> None:
    """用同一 target 重新登记 repair pending dispatch。

    参数：
        path_session 为 session 文件。
        dict_session 为当前 session 对象。
        str_event_id、str_worker_id、str_phase 和 str_agent_target 绑定本次 pending。
    返回：无；更新后的 pending 队列写回 session。
    """

    # 锁定当前 session 的 pending 对账队列并移除旧项。
    list_pending_dispatches = dict_session.setdefault("pending_dispatches", [])  # session 中尚未闭合的 repair 对账项

    # 过滤旧的同事件 pending，避免重复对账项叠加。
    list_pending_dispatches = [  # 过滤后的 pending 队列
        dict_pending  # 保留非目标事件的 pending 记录
        for dict_pending in list_pending_dispatches  # 遍历旧 pending 对账项
        if not (  # 保留非同事件 pending 记录
            isinstance(dict_pending, dict)  # pending 条目必须是对象
            and dict_pending.get("event_id") == str_event_id  # 同一事件条件
            and dict_pending.get("worker_id") == str_worker_id  # 同一 worker 条件
        )
    ]  # 去除旧的同事件 pending

    # 用原 target 写入新的 repair pending 项；当前操作只新增一条同 worker 记录。
    list_pending_dispatches.append(
        {
            "event_id": str_event_id,
            "worker_id": str_worker_id,
            "phase": str_phase,
            "agent_target": str_agent_target,
        }
    )

    # 保存 pending 队列，供 follow-up receipt 继续对账。
    dict_session["pending_dispatches"] = list_pending_dispatches  # 更新后的 pending 队列

    # 将 pending 队列和 target 绑定状态持久化。
    _write_session(path_session, dict_session)

# 生成同一 canonical target 的可记录修复 follow-up。
def dispatch_repair(
    project: str,
    event_id: str,
    worker_id: str,
    phase: str,
    correction_fields: list[str],
) -> dict[str, object]:
    """生成同一 canonical target 的可记录修复 follow-up。

    参数：
        project 为项目根目录。
        event_id、worker_id 和 phase 绑定当前 receipt。
        correction_fields 为需要修正的字段列表。
    返回：同 target follow-up 载荷或结构化熔断结果。
    """

    # 读取 repair 配置与绑定 session。
    dict_repair = worker_repair_config()  # 当前 repair 配置

    # 绑定当前项目的 worker session 文件。
    path_session, dict_session = _bound_session(project)  # 当前项目绑定的 worker session 文件与对象

    # 校验 repair 核心字段，失败时保持 fail-closed。
    tuple_contract = _repair_contract_fields(dict_repair)  # repair 核心字段

    # 缺失核心字段时停止当前 repair。
    if tuple_contract is None:

        # 配置缺失不能生成不可审计消息。
        return _repair_error("> ERR: [Python] repair contract fields are incomplete")

    # 拆出已确认的 repair 配置字段。
    dict_breaker, str_target_policy, list_preserve_fields, list_replace_fields = tuple_contract  # 当前 repair 合同字段

    # 同一事件只能沿状态或历史 receipt 恢复 target。
    tuple_worker_target = _resolve_worker_target(dict_session, event_id, worker_id)  # worker 状态和 target 二元组

    # 分离 worker 状态和 canonical target，避免把二元组误当作状态对象。
    dict_worker = tuple_worker_target[0]  # 恢复的 worker 状态对象

    # 读取恢复的 target，后续 receipt 必须继续使用它。
    str_agent_target = tuple_worker_target[1]  # 供同一 event 的 follow-up receipt 复用

    # 缺少原 target 时禁止重新生成第二个 canonical Agent。
    if not isinstance(dict_worker, dict) or not str_agent_target:

        # 返回结构化错误，要求沿同一 event 复用已有 target。
        return _repair_error("> ERR: [Python] repair target is not persisted for worker")

    # 将恢复的 target 回填 worker 状态，保证后续阶段继续复用。
    dict_worker["agent_target"] = str_agent_target  # 写回 target 供后续 receipt 对账

    # repair 阶段必须来自配置允许集合。
    list_allowed_phases = dict_repair.get("allowed_phases", [])  # 当前 repair 允许阶段

    # 非列表配置不能提供可验证的阶段边界。
    if not isinstance(list_allowed_phases, list) or phase not in list_allowed_phases:

        # 非法阶段不能伪造 follow-up receipt。
        return _repair_error("> ERR: [Python] repair phase is not allowed by configuration")

    # 目标身份和阶段边界校验通过后，写入事件重试计数以阻止跨阈值重放。
    dict_retry_result = _register_repair_attempt(  # 该调用把事件计数、失败窗口和重置开关返回给熔断判断分支
        path_session,  # 绑定 session 文件路径
        dict_session,  # 待写回的 session 对象
        event_id,  # 触发修复的事件摘要
        worker_id,  # 当前修复请求的 canonical worker 身份
        dict_breaker,  # repair 阈值配置
        dict_repair.get("max_attempts"),  # 配置声明的尝试上限
    )  # retry helper 输出

    # retry 状态失败时直接回传结构化阻断。
    if not dict_retry_result.get("valid"):

        # 保留 helper 的字段级诊断和退出语义。
        return dict_retry_result

    # 达到任一阈值后打开熔断，不生成 follow-up；helper 已完成类型校验。
    if (
        dict_retry_result["retry_count"] > dict_repair["max_attempts"]
        or dict_retry_result["history_length"] >= dict_retry_result["open_after"]
    ):

        # 返回原 target 和尝试次数，便于主 Agent请求人工复核。
        return {
            "valid": False,
            "blocking": True,
            "circuit_breaker_open": True,
            "worker_id": worker_id,
            "agent_target": str_agent_target,
            "event_id": event_id,
            "retry_count": dict_retry_result["retry_count"],
            "failure_window": dict_retry_result["failure_window"],
            "errors": ["> ERR: [Python] repair circuit breaker is open"],
        }

    # 消息模板从配置读取，当前字段仅作为 format 参数进入载荷。
    str_template = dict_repair.get("message_template")  # 当前 repair 消息模板

    # 非字符串模板不能安全生成 follow-up。
    if not isinstance(str_template, str) or not str_template.strip():

        # 没有模板时禁止拼接隐式修复文本。
        return _repair_error("> ERR: [Python] repair message template is missing")

    # 将字段列表规范化为模板可读文本。
    str_corrections = ", ".join(  # 当前修复字段文本
        str(value)  # 当前字段的可读文本
        for value in correction_fields  # 遍历主 Agent提供的修复字段
        if str(value).strip()  # 忽略空字段
    )

    # 将绑定字段写入 repair 消息模板。
    str_message = str_template.format(  # 当前 follow-up 消息
        worker_id=worker_id,  # 模板中的 worker 身份
        phase=phase,  # 模板中的生命周期阶段
        event_id=event_id,  # 模板中的事件摘要
        correction_fields=str_corrections,  # 模板中的修复字段
    )

    # 为同一事件重新登记 pending；helper 会移除旧项并保留原 target。
    _append_repair_pending(
        path_session,
        dict_session,
        event_id,
        worker_id,
        phase,
        str_agent_target,
    )

    # 返回主 Agent 可直接发送的 follow-up envelope。
    return {
        "valid": True,
        "blocking": False,
        "operation": "followup",
        "target_reuse": str_target_policy,
        "worker_id": worker_id,
        "agent_target": dict_worker["agent_target"],
        "event_id": event_id,
        "phase": phase,
        "retry_count": dict_retry_result["retry_count"],
        "failure_window": dict_retry_result["failure_window"],
        "reset_requires_new_event": dict_retry_result["reset_requires_new_event"],
        "preserve_fields": list_preserve_fields,
        "replace_fields": list_replace_fields,
        "message": str_message,
    }

# facade 导出的 repair 入口。
__all__ = ("dispatch_repair",)  # 稳定的公共符号
