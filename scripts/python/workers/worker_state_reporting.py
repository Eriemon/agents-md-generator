"""提供 worker 状态、reviewer 会话和只读验证报告。"""

# 延迟类型注解求值，兼容项目支持的 Python 运行环境。
from __future__ import annotations

# reviewer 状态使用标准库读取统一 session 并维护稳定事件字段。
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any

# dispatcher 是 reviewer 会话唯一的事件状态入口。
from worker_dispatch import check_dispatch_event
from worker_dispatch import dispatch_contracts

# worker_dispatch_contracts 提供阶段和身份的唯一枚举来源。
from worker_dispatch_contracts import CANONICAL_WORKER_IDS
from worker_dispatch_contracts import EVENT_BY_PHASE
from worker_dispatch_contracts import PHASE_BY_ROLE
from worker_dispatch_contracts import canonical_worker_id
from manage_worker_state import validate_worker_states
from reviewer_session import is_baseline_mismatch
from reviewer_session import reviewer_trigger_decision

# 历史私有会话路径函数仍需解析项目默认平台配置。
from agent_platform import load_agent_config
from agent_platform import resolve_agent_profile

# worker profile 提供握手和静态合同。
from gardener_worker_profile import GARDENER_WORKER_SHA256
from gardener_worker_profile import ensure_gardener_worker_profile
from gardener_worker_profile import gardener_worker_handshake

# reviewer profile 提供内容哈希和动态握手合同。
from reviewer_worker_profile import REVIEWER_WORKER_SHA256
from reviewer_worker_profile import ensure_reviewer_worker_profile
from reviewer_worker_profile import reviewer_worker_handshake

# tester profile 提供只读状态和动态握手合同。
from tester_worker_profile import ensure_tester_worker_profile
from tester_worker_profile import tester_worker_handshake

# profile routing 提供 gardener 工具和 bundle 读回视图。
from worker_profile_routing import _gardener_tool_status
from worker_profile_routing import _profile_lifecycle_views

# reviewer 的 canonical id 绑定方案复核和历史 session。
REVIEWER_WORKER_ID: str = canonical_worker_id("reviewer")  # reviewer 状态索引键。

# tester 的 canonical id 绑定测试阶段和同实例复用。
TESTER_WORKER_ID: str = canonical_worker_id("tester")  # tester 阶段状态使用的唯一键。

# gardener 的 canonical id 绑定提交后只读整理阶段。
GARDENER_WORKER_ID: str = canonical_worker_id("gardener")  # gardener 只读审查使用的唯一键。

# correction 阶段名用于旧 session 的序号递增判断。
CORRECTION_PHASE: str = PHASE_BY_ROLE.get("correction", "")  # 兼容 reviewer correction 阶段名。

# 按项目和平台配置解析 reviewer 会话位置。
def _review_session_path(project: str | Path, str_agent_platform: str | None) -> Path:
    """按选定平台解析 reviewer 会话状态路径。

    参数:
        project: 当前项目根目录。
        str_agent_platform: 可选的平台标识。
    返回:
        reviewer 会话状态文件路径。
    """

    # 解析项目根，保证状态位置不依赖调用方当前目录。
    path_project = Path(project).resolve()  # reviewer 会话绑定的项目绝对路径。

    # 从当前脚本位置定位 skill 根，避免复制绝对路径。
    path_skill_root = Path(__file__).resolve().parents[3]  # agent 配置的项目根。

    # 显式平台优先，否则读取项目默认平台配置。
    if str_agent_platform:

        # 选定平台的 profile 决定生成器状态根。
        profile = resolve_agent_profile(str_agent_platform)  # 解析调用方指定的平台 profile。

    # 未指定平台时回退到当前项目的默认治理配置。
    else:

        # 未指定平台时沿用当前项目的默认治理配置。
        profile = load_agent_config(path_skill_root)  # 读取项目默认平台 profile。

    # 会话文件固定放在 profile 生成器状态根目录。
    return profile.generator_state_root(path_project) / "reviewer-session.json"

# 生成 reviewer 阶段到 dispatcher 事件的稳定映射。
def _reviewer_phase_events(
    int_periodic_sequence: int,
    str_plan_sha256: str,
) -> dict[str, tuple[str, dict[str, object]]]:
    """构造 reviewer 各阶段使用的 dispatcher 事件和载荷。

    参数:
        int_periodic_sequence: 下一次 PERIODIC 事件序号。
        str_plan_sha256: 当前批准计划摘要。
    返回:
        阶段名称到事件名称及载荷的映射。
    """

    # 阶段和事件均由 protocol 的双向映射生成，避免复制生命周期枚举。
    dict_phase_payloads: dict[str, dict[str, object]] = {
        PHASE_BY_ROLE.get("initial", ""): {},  # INITIAL 只需要阶段身份。
        PHASE_BY_ROLE.get("periodic", ""): {"periodic_sequence": int_periodic_sequence},  # PERIODIC 绑定序号。
        PHASE_BY_ROLE.get("correction", ""): {"plan_sha256": str_plan_sha256},  # CORRECTION 绑定批准计划。
        PHASE_BY_ROLE.get("final", ""): {},  # FINAL 事件不附加额外载荷。
    }  # reviewer 阶段到事件载荷的映射。

    # 只返回协议声明过且具备事件映射的阶段。
    return {
        str_phase: (EVENT_BY_PHASE.get(str_phase, ""), dict_payload)  # 阶段事件和载荷绑定。
        for str_phase, dict_payload in dict_phase_payloads.items()  # 遍历协议阶段映射。
        if str_phase and EVENT_BY_PHASE.get(str_phase)  # 过滤空阶段和未声明事件。
    }

# 处理统一 dispatcher session 的 reviewer 事件映射。
def _reviewer_dispatch_session_status(
    project: str | Path,
    str_phase: str,
    str_plan_sha256: str,
    float_now_monotonic: float | None,
    float_interval_seconds: float,
    str_receipt_sha256: str | None,
) -> dict[str, object]:
    """读取统一 session 并返回 reviewer 事件决策。

    参数:
        project: 当前项目根目录。
        str_phase: 当前治理阶段。
        str_plan_sha256: 已批准计划摘要。
        float_now_monotonic: 可选的单调时钟值。
        float_interval_seconds: reviewer 触发间隔秒数。
        str_receipt_sha256: 可选的 receipt 摘要。
    返回:
        reviewer dispatcher 事件结果或 fail-closed 阻断映射。
    异常:
        OSError, TypeError, ValueError: 状态损坏时返回阻断结果。
    """

    # 统一状态文件缺失时禁止回退第二套 reviewer 会话。
    path_dispatch_session = Path(project).resolve() / ".agents" / "worker-session.json"  # 当前 dispatcher session 文件。

    # 缺少统一 session 时必须先恢复当前状态机。
    if not path_dispatch_session.is_file():

        # 缺失 session 的事实必须以阻断报告返回。
        return {
            "trigger": False,
            "blocking": True,
            "phase": str_phase,
            "worker_id": REVIEWER_WORKER_ID,
            "reason": "worker dispatch session is missing",
            "plan_sha256": str_plan_sha256,
        }

    # 读取统一 session 的周期序号，保证 PERIODIC 事件单调递增。
    try:

        # 读取当前 dispatcher session 的 JSON 对象。
        dict_dispatch_session = json.loads(path_dispatch_session.read_text(encoding="utf-8"))  # 当前审查使用的 session 映射。

        # 列表或标量不能提供周期序号。
        if not isinstance(dict_dispatch_session, dict):

            # 结构错误必须使用 CLI 统一错误前缀。
            raise ValueError("> ERR: [Python] worker dispatch session root must be an object")

        # 将 session 的周期字段转换为下一次事件序号。
        int_periodic_sequence = int(dict_dispatch_session.get("periodic_sequence", 0)) + 1  # 下一次 PERIODIC 序号。

    # 损坏或不完整 session 必须阻断 reviewer。
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as object_error:

        # 不回退到旧 reviewer 状态文件。
        return {
            "trigger": False,
            "blocking": True,
            "phase": str_phase,
            "worker_id": REVIEWER_WORKER_ID,
            "reason": f"worker dispatch session is invalid: {object_error}",
            "plan_sha256": str_plan_sha256,
        }

    # 生命周期阶段映射到批准方案的统一事件。
    dict_phase_events = _reviewer_phase_events(int_periodic_sequence, str_plan_sha256)  # reviewer 阶段事件映射。

    # 未知阶段保留原阶段值，由 dispatcher 参数校验拒绝。
    str_dispatch_event, dict_dispatch_payload = dict_phase_events.get(str_phase, (str_phase, {}))  # 当前 reviewer 统一事件。

    # dispatcher 结果只写入统一 session，不创建第二份 reviewer 状态。
    try:

        # 先固定当前事件使用的单调时间。
        float_dispatch_now = time.monotonic() if float_now_monotonic is None else float_now_monotonic  # 当前事件检查使用的单调时钟。

        # 将阶段事件参数收束为一个可复用的调用元组。
        tuple_event_args = (project, str_dispatch_event, dict_dispatch_payload, float_dispatch_now)  # dispatcher 事件检查参数。

        # 将阶段事件交给统一 dispatcher 进行状态校验。
        dict_dispatch_result = check_dispatch_event(*tuple_event_args)  # 当前阶段的 dispatcher 事件检查结果。

    # session/事件错误必须以 reviewer 阻断返回。
    except (TypeError, ValueError, OSError) as object_error:

        # 不回退到旧 reviewer 状态文件，避免双状态分叉。
        return {
            "trigger": False,
            "blocking": True,
            "phase": str_phase,
            "worker_id": REVIEWER_WORKER_ID,
            "reason": str(object_error),
            "plan_sha256": str_plan_sha256,
        }

    # 将 dispatcher 结果投影为兼容 review-session CLI 的字段。
    return {
        **dict_dispatch_result,
        "trigger": bool(dict_dispatch_result.get("required_dispatches")),
        "phase": str_phase,
        "worker_id": REVIEWER_WORKER_ID,
        "plan_sha256": str_plan_sha256,
    }

# 检查旧 reviewer 会话路径所需的平台与根 worker 前提。
def _legacy_reviewer_gate(
    project: str | Path,
    str_phase: str,
    str_plan_sha256: str,
    str_agent_platform: str | None,
) -> tuple[dict[str, object] | None, Path | None]:
    """返回旧 reviewer 状态路径或其 fail-closed 阻断结果。

    参数:
        project: 当前项目根目录。
        str_phase: 当前 reviewer 阶段。
        str_plan_sha256: 已批准计划摘要。
        str_agent_platform: 可选的平台标识。
    返回:
        阻断结果和空路径，或空阻断结果及旧会话路径。
    """

    # 先阻断无效根状态，避免生成不可追溯的 reviewer 触发。
    dict_state_validation = validate_worker_states(project, bool_include_nested=False)  # 根 worker 状态报告。

    # 平台能力决定旧 reviewer 路径是否仍可使用。
    path_skill_root = Path(__file__).resolve().parents[3]  # 当前 skill 配置根目录。

    # 根据显式平台或项目默认配置解析 reviewer 能力。
    profile = resolve_agent_profile(str_agent_platform) if str_agent_platform else load_agent_config(path_skill_root)  # 当前平台 profile。

    # 非 Codex-native 平台不能伪造 reviewer 能力。
    if profile.worker_support != "codex-native":

        # 返回平台能力阻断报告。
        return (
            {
                "trigger": False,
                "blocking": True,
                "phase": str_phase,
                "worker_id": REVIEWER_WORKER_ID,
                "reason": f"{REVIEWER_WORKER_ID} is unsupported on the selected platform",
                "plan_sha256": str_plan_sha256,
            },
            None,
        )

    # 根状态无效时保留详细错误供调用方修复。
    if not dict_state_validation.get("valid", False):

        # 返回根状态阻断报告。
        return (
            {
                "trigger": True,
                "blocking": True,
                "phase": str_phase,
                "worker_id": REVIEWER_WORKER_ID,
                "reason": "root worker state is invalid",
                "plan_sha256": str_plan_sha256,
                "errors": dict_state_validation.get("errors", []),
            },
            None,
        )

    # 根级显式禁用优先于旧 reviewer 会话文件。
    if dict_state_validation.get("states", {}).get(REVIEWER_WORKER_ID) == "disabled":

        # 返回禁用状态，避免旧 receipt 被误认为有效触发。
        return (
            {
                "trigger": False,
                "blocking": True,
                "phase": str_phase,
                "worker_id": REVIEWER_WORKER_ID,
                "reason": f"{REVIEWER_WORKER_ID} is disabled at root",
                "plan_sha256": str_plan_sha256,
            },
            None,
        )

    # 所有前提通过后才解析旧 reviewer 会话文件。
    return None, _review_session_path(project, str_agent_platform)

# 读取旧 reviewer 会话并执行 receipt/间隔触发决策。
def _legacy_reviewer_decision(
    path_session: Path,
    project: str | Path,
    str_phase: str,

    # 计划和时间绑定当前 reviewer 触发。
    str_plan_sha256: str,
    float_now_monotonic: float | None,

    # 间隔与 receipt 保留旧 CLI 的完整语义。
    float_interval_seconds: float,
    str_receipt_sha256: str | None,
) -> dict[str, object]:
    """在旧 reviewer 状态文件上保持兼容触发行为。

    参数:
        path_session: reviewer 旧会话文件路径。
        project: 当前项目根目录，保留兼容签名语义。
        str_phase: 当前 reviewer 阶段。
        str_plan_sha256: 已批准计划摘要。
        float_now_monotonic: 可选的单调时钟。
        float_interval_seconds: reviewer 触发间隔秒数。
        str_receipt_sha256: 可选的 receipt 摘要。
    返回:
        reviewer 触发决策和规范化旧会话状态。
    """

    # 缺失旧会话按空状态处理，交由统一触发器决定是否首次触发。
    try:

        # 缺失文件视为空文本，保留首次 PERIODIC 触发语义。
        str_session_text = path_session.read_text(encoding="utf-8") if path_session.is_file() else ""  # 旧会话文本。

        # 只在有文本时解析旧会话 JSON。
        dict_loaded_session = json.loads(str_session_text) if str_session_text else {}  # 已解析的旧会话对象。

        # 标量或列表不能作为 reviewer 会话状态。
        dict_session: dict[str, object] = dict_loaded_session if isinstance(dict_loaded_session, dict) else {}  # 规范化状态映射。
    
    # 文件损坏时不要传播旧状态解析异常。
    except (OSError, UnicodeError, json.JSONDecodeError):

        # 损坏旧状态按空会话交给触发器 fail-closed 处理。
        dict_session = {}  # 使用空会话重新计算 reviewer 触发。

    # 统一使用单调时钟，避免系统时间回拨影响 reviewer 间隔。
    float_now = time.monotonic() if float_now_monotonic is None else float_now_monotonic  # 本次决策单调时间。

    # 将触发器输入收束为稳定的调用元组。
    tuple_decision_args = (dict_session, str_phase, str_plan_sha256, float_now)  # reviewer 基础决策参数。

    # 统一触发器负责间隔、receipt 和基线漂移判断。
    dict_reviewer_options = {"float_interval_seconds": float_interval_seconds, "str_receipt_sha256": str_receipt_sha256}  # reviewer 间隔和 receipt 参数。

    # 生成旧 reviewer 的兼容触发结果。
    dict_decision = reviewer_trigger_decision(*tuple_decision_args, **dict_reviewer_options)  # reviewer 触发结果。

    # 只有新 receipt 完成基线校验后才写回旧会话。
    if (
        dict_decision["trigger"]
        and not is_baseline_mismatch(dict_decision)
        and str_receipt_sha256 is not None
    ):

        # 新 receipt 通过基线检查后才更新旧会话。
        dict_session.update(
            {
                "schema_version": 1,
                "review_session_id": dict_session.get("review_session_id") or hashlib.sha256(
                    f"{str_plan_sha256}:{str_phase}".encode("utf-8")
                ).hexdigest()[:16],
                "approved_plan_sha256": str_plan_sha256,
                "worker_id": REVIEWER_WORKER_ID,
                "phase": str_phase,
                "last_review_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "last_review_monotonic": float_now,
                "last_receipt_sha256": dict_decision.get("receipt_sha256", ""),
                "correction_seq": (  # correction 阶段才递增旧 session 的修复序号。
                    int(dict_session.get("correction_seq", 0)) + (1 if str_phase == CORRECTION_PHASE else 0)
                ),
            }
        )

        # 旧 reviewer 会话目录缺失时才创建。
        path_session.parent.mkdir(parents=True, exist_ok=True)

        # 将状态序列化为稳定 JSON，保证后续 receipt 可复算。
        str_session_json = json.dumps(dict_session, ensure_ascii=False, indent=2, sort_keys=True)  # 稳定序列化旧会话。

        # 保留文本文件末尾换行。
        str_session_json += "\n"  # 确保兼容状态文件以稳定 EOF 结束。

        # 回写已确认的 reviewer 会话。
        path_session.write_text(str_session_json, encoding="utf-8")

    # 保留路径和状态，兼容原 review-session CLI 的可观察字段。
    dict_decision["session_path"] = str(path_session)  # 旧 reviewer 会话路径。

    # 附加本次 reviewer 决策使用的状态。
    dict_decision["state"] = dict_session  # 本次 reviewer 决策使用的状态。

    # 返回包含触发结论、路径和状态的完整报告。
    return dict_decision

# reviewer-session 公共入口保留历史签名并委托统一状态机。
def reviewer_session_status(
    project: str | Path,
    str_phase: str,

    # 计划摘要和单调时间共同绑定当前审查阶段。
    str_plan_sha256: str,
    float_now_monotonic: float | None,

    # 平台参数和间隔参数保留历史 CLI 兼容性。
    str_agent_platform: str | None,
    float_interval_seconds: float,

    # receipt 摘要用于绑定本次 reviewer 结果。
    str_receipt_sha256: str | None = None,
) -> dict[str, object]:
    """读取统一 reviewer session 并返回当前阶段决策。

    参数:
        project: 当前项目根目录。
        str_phase: 当前治理阶段名称。
        str_plan_sha256: 已批准计划摘要。
        float_now_monotonic: 可选的单调时钟值。
        str_agent_platform: 保留历史平台参数以维持 CLI 兼容。
        float_interval_seconds: reviewer 触发间隔秒数。
        str_receipt_sha256: 可选的 reviewer receipt 摘要。
    返回:
        reviewer 触发决策及会话状态报告。
    异常:
        OSError, TypeError, ValueError: 当前 session 或事件输入损坏时返回阻断报告。
    """

    # 统一 dispatcher session 存在时优先使用新状态机。
    path_dispatch_session = Path(project).resolve() / ".agents" / "worker-session.json"  # 统一 dispatcher session 文件。

    # 只有当前统一 session 存在时才进入新状态机。
    if path_dispatch_session.is_file():

        # 将新状态机参数收束为稳定调用元组。
        tuple_dispatch_identity = (project, str_phase, str_plan_sha256)  # dispatcher 项目和阶段参数。

        # 记录 dispatcher 的时钟与 receipt 参数。
        tuple_dispatch_runtime = (float_now_monotonic, float_interval_seconds, str_receipt_sha256)  # dispatcher 时钟和 receipt 参数。

        # 合并 dispatcher reviewer 调用参数。
        tuple_dispatch_args = tuple_dispatch_identity + tuple_dispatch_runtime  # 组合统一状态机调用边界。

        # 返回统一 dispatcher 的阶段结果。
        return _reviewer_dispatch_session_status(*tuple_dispatch_args)

    # 旧项目没有 dispatcher session 时保持 reviewer-session 兼容触发。
    tuple_legacy_gate_args = (project, str_phase, str_plan_sha256, str_agent_platform)  # 旧 reviewer 前提参数。

    # 读取旧 reviewer 的前提检查结果。
    tuple_legacy_gate_result = _legacy_reviewer_gate(*tuple_legacy_gate_args)  # 旧 reviewer 前提结果。

    # 读取旧 reviewer 可能返回的阻断映射。
    dict_blocking = tuple_legacy_gate_result[0]  # 旧 reviewer 阻断结果。

    # 读取通过前提检查后的旧会话路径。
    path_session = tuple_legacy_gate_result[1]  # 取得兼容旧状态的实际落盘位置。

    # 旧 reviewer 阻断结果优先返回。
    if dict_blocking is not None:

        # 返回平台、根状态或禁用原因。
        return dict_blocking

    # 将旧会话参数交给兼容触发器。
    tuple_legacy_identity = (path_session, project, str_phase, str_plan_sha256)  # 旧 reviewer 身份参数。

    # 记录旧 reviewer 的时间和 receipt 参数。
    tuple_legacy_runtime = (float_now_monotonic, float_interval_seconds, str_receipt_sha256)  # 旧 reviewer 运行参数。

    # 合并旧 reviewer 兼容触发器参数。
    tuple_legacy_decision_args = tuple_legacy_identity + tuple_legacy_runtime  # 旧 reviewer 决策参数。

    # 调用旧会话兼容触发器。
    return _legacy_reviewer_decision(*tuple_legacy_decision_args)

# 读取三个 worker 的动态隔离握手令牌。
def _worker_handshakes() -> dict[str, str]:
    """返回三个 worker 的稳定握手令牌。

    参数:
        无显式参数；令牌由三个 profile 模块动态计算。
    返回:
        worker 名称到握手令牌的映射。
    """

    # 返回统一的三个 worker 握手映射，避免调用方各自拼接。
    return {
        TESTER_WORKER_ID: tester_worker_handshake(),
        REVIEWER_WORKER_ID: reviewer_worker_handshake(),
        GARDENER_WORKER_ID: gardener_worker_handshake(),
    }

# 汇总 profile、工具和根状态的只读证据。
def worker_status(codex_home: str | Path | None = None, project: str | Path = ".") -> dict[str, Any]:
    """只读返回三个 worker、gardener 工具和根状态。

    参数:
        codex_home: 可选的 Codex 配置目录。
        project: 当前工作文件夹路径。
    返回:
        包含三个 profile、工具 bundle、握手和 worker_state 的状态映射。
    """

    # profile 检查只读，不会创建或覆盖配置。
    dict_tester = ensure_tester_worker_profile(codex_home, write=False)  # tester 配置状态。

    # reviewer profile 负责验证隔离配置与用户确认哈希。
    dict_reviewer = ensure_reviewer_worker_profile(codex_home, write=False)  # reviewer 隔离配置状态。

    # gardener profile 负责验证只读扫描工具的隔离配置。
    dict_gardener = ensure_gardener_worker_profile(codex_home, write=False)  # gardener profile 当前合同状态。

    # gardener 工具必须与源码字节相同，缺失或漂移都会阻止整体有效。
    dict_gardener_tool = _gardener_tool_status(codex_home, write=False)  # gardener 工具安装状态。

    # 根状态只读取根 AGENTS.md，避免状态查询越过 tests/** 边界。
    dict_state = validate_worker_states(  # 根 AGENTS 启停声明。
        project,  # 当前项目根路径。
        bool_include_nested=False,  # 状态报告不递归读取嵌套 AGENTS.md。
    )

    # 项目授权状态覆盖 profile 能力字段，防止存在 TOML 就被误报为 enabled。
    dict_authorized_states = dict_state.get("states", {})  # 当前项目显式授权状态

    # 每个 profile 都回填项目授权态，供 status 和后续 dispatch 读取同一事实源。
    if isinstance(dict_authorized_states, dict):

        # 按 canonical role 顺序覆盖 profile 能力字段。
        for str_worker_id, dict_profile in (
            (TESTER_WORKER_ID, dict_tester),
            (REVIEWER_WORKER_ID, dict_reviewer),
            (GARDENER_WORKER_ID, dict_gardener),
        ):

            # 缺少显式状态时保持 fail-closed 的 unconfigured。
            str_authorized_state = str(dict_authorized_states.get(str_worker_id, "unconfigured"))  # 项目授权状态

            # 回填可审计的项目授权状态。
            dict_profile["authorized_state"] = str_authorized_state  # 项目授权状态回读

            # 只有显式 enabled 才允许状态报告声称启用。
            dict_profile["enabled"] = str_authorized_state == "enabled"  # 项目授权覆盖 profile 能力

            # dispatch 授权与状态字段保持同一 fail-closed 判定。
            dict_profile["dispatch_authorized"] = str_authorized_state == "enabled"  # 派发授权结果

    # 三个子检查全部有效才报告整体有效。
    bool_tester_valid = bool(dict_tester.get("existing_validation", {}).get("valid"))  # tester profile 通过验证。

    # reviewer profile 的验证结果独立保留。
    bool_reviewer_valid = bool(dict_reviewer.get("existing_validation", {}).get("valid"))  # reviewer profile 通过合同验证。

    # 保留 gardener 合同结果，便于与工具读回结果区分。
    bool_gardener_valid = bool(dict_gardener.get("existing_validation", {}).get("valid"))  # gardener TOML 合同当前有效。

    # gardener 工具读回证据独立参与整体有效判定。
    bool_gardener_tool_valid = bool(dict_gardener_tool.get("valid"))  # gardener 工具通过哈希验证。

    # 根 AGENTS 状态决定启停声明是否合规。
    bool_state_valid = bool(dict_state.get("valid"))  # 根状态通过治理检查。

    # 三个 profile 合同都通过后才进入整体 profile 有效状态。
    bool_profiles_valid = bool_tester_valid and bool_reviewer_valid and bool_gardener_valid  # 三个 worker profile 均已通过。

    # profile、工具读回和根状态全部通过才开放整体有效标志。
    bool_valid = bool_profiles_valid and bool_gardener_tool_valid and bool_state_valid  # worker 总体通过。

    # 返回完整只读证据，不隐藏任一子检查结果。
    dict_profiles = {
        TESTER_WORKER_ID: dict_tester,  # tester 配置摘要和读回状态。
        REVIEWER_WORKER_ID: dict_reviewer,  # reviewer 确认哈希和合同状态。
        GARDENER_WORKER_ID: dict_gardener,  # gardener 配置与隔离状态。
    }

    # 返回完整只读状态，保留每一条子证据和 bundle 视图。
    return {
        "valid": bool_valid,
        TESTER_WORKER_ID: dict_tester,
        REVIEWER_WORKER_ID: dict_reviewer,
        GARDENER_WORKER_ID: dict_gardener,
        "gardener_tool": dict_gardener_tool,
        "worker_state": dict_state,
        "handshakes": _worker_handshakes(),
        "dispatch_contracts": dispatch_contracts(),
        **_profile_lifecycle_views(dict_profiles, dict_gardener_tool),
    }

# 展示 worker 漂移和显式写入确认要求。
def preview_workers(codex_home: str | Path | None = None, project: str | Path = ".") -> dict[str, Any]:
    """预览三个配置及 gardener 工具的漂移、状态和修复收据，不写入任何文件。

    参数:
        codex_home: 可选的 Codex 配置目录。
        project: 当前工作文件夹路径。
    返回:
        带有 requires_user_confirmation 的只读预览映射。
    """

    # status 与 preview 共用同一只读验证口径。
    dict_result = worker_status(codex_home, project)  # 当前 worker 状态。

    # 任一 profile 漂移都必须在 apply 前展示 proposed 内容。
    bool_tester_confirmation = dict_result[TESTER_WORKER_ID].get("status") == "needs-refresh"  # tester proposed 需要用户确认。

    # reviewer 的刷新状态单独保留，便于审计提示。
    bool_reviewer_refresh = dict_result[REVIEWER_WORKER_ID].get("status") == "needs-refresh"  # reviewer proposed 内容发生漂移。

    # reviewer API 可能直接返回确认要求。
    bool_reviewer_confirmation = bool(dict_result[REVIEWER_WORKER_ID].get("requires_user_confirmation"))  # reviewer 写入需要用户确认。

    # gardener 漂移也必须先展示 proposed 内容并取得显式确认。
    bool_gardener_confirmation = dict_result[GARDENER_WORKER_ID].get("status") == "needs-refresh"  # gardener profile 等待用户授权。

    # gardener 工具漂移同样不能绕过显式确认。
    bool_gardener_tool_confirmation = dict_result["gardener_tool"].get("status") == "needs-refresh"  # gardener 工具需要确认。

    # tester 或 reviewer 任一确认来源为真都阻止无收据 apply。
    bool_confirmation = bool_tester_confirmation or bool_reviewer_refresh  # 汇总 tester 与 reviewer 的确认要求。

    # gardener profile 的确认要求继续叠加到统一状态。
    bool_confirmation = bool_confirmation or bool_reviewer_confirmation or bool_gardener_confirmation  # 叠加 reviewer 与 gardener profile 状态。

    # gardener 工具漂移也必须阻止无收据写入。
    bool_confirmation = bool_confirmation or bool_gardener_tool_confirmation  # 完成全部确认来源汇总。

    # 预览只汇总确认需求，不把它解释成已授权写入。
    dict_result["requires_user_confirmation"] = bool_confirmation  # 预览确认要求。

    # 返回完整只读预览证据。
    return dict_result

# 组合静态配置和动态握手验证结果。
def verify_workers(codex_home: str | Path | None = None, project: str | Path = ".") -> dict[str, Any]:
    """验证配置、根状态和动态握手合同。

    参数:
        codex_home: 可选的 Codex 配置目录。
        project: 当前工作文件夹路径。
    返回:
        包含三个握手、三个配置和 gardener 工具哈希的映射。
    """

    # 静态状态检查不能被握手结果掩盖。
    dict_result = worker_status(codex_home, project)  # 静态状态结果。

    # 三个握手分别验证模型、隔离记忆和工作约束。
    dict_handshakes = _worker_handshakes()  # 动态握手结果。

    # 将握手对象挂到静态状态结果上。
    dict_result["handshakes"] = dict_handshakes  # 三个 worker 的握手证据。

    # 返回固定 reviewer 哈希，供审计复算。
    dict_result["reviewer_sha256"] = REVIEWER_WORKER_SHA256  # reviewer 配置确认哈希。

    # 返回 gardener 配置哈希，供三份 bundle 复算。
    dict_result["gardener_sha256"] = GARDENER_WORKER_SHA256  # 暴露 gardener profile 内容摘要供复核。

    # 返回包含静态配置与动态握手的完整证据。
    return dict_result

# 对 reviewer profile 与根状态执行专属验证。
def validate_review_worker(codex_home: str | Path | None = None, project: str | Path = ".") -> dict[str, Any]:
    """执行 reviewer 专属验证，确保它只读、隔离并可定位根状态。

    参数:
        codex_home: 可选的 Codex 配置目录。
        project: 当前工作文件夹路径。
    返回:
        reviewer profile、握手、根状态和 valid 标志的映射。
    """

    # 保留 tester 对照结果，同时检查 reviewer 专属状态。
    dict_result = verify_workers(codex_home, project)  # 完整 worker 验证。

    # 提取 reviewer 专属状态，避免与 tester 结果混淆。
    dict_reviewer = dict_result[REVIEWER_WORKER_ID]  # reviewer 运行状态。

    # reviewer profile 与根状态都必须独立有效。
    bool_reviewer_valid = bool(dict_reviewer.get("existing_validation", {}).get("valid"))  # reviewer profile 已通过验证。

    # 根状态必须同时满足根目录禁用边界和格式合同。
    bool_state_valid = bool(dict_result["worker_state"].get("valid"))  # 根状态已通过验证。

    # reviewer 合同需同时满足 profile 与根状态检查。
    dict_result["valid"] = bool_reviewer_valid and bool_state_valid  # reviewer 总体有效。

    # 返回 reviewer 专属验证结果。
    return dict_result
