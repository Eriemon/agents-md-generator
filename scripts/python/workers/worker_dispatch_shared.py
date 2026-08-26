"""承载 worker dispatch 的低层 session、摘要和运行时边界。"""

# 延迟解析类型注解，保持 shared shard 与 Python 3.10 运行时兼容。
from __future__ import annotations

# 摘要、JSON 序列化、时钟和原子文件写入依赖标准库基础模块。
import hashlib
import json
import math
import os
import sys

# fallback 平台模块需要动态加载规格和显式类型声明。
import importlib.util
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable

# 优先走包内导入，保证 dispatcher 与项目治理模块使用同一模块身份。
try:

    # 包内入口保持治理模块的 canonical 模块身份。
    from .manage_worker_state import validate_worker_states
    from .reviewer_session import DEFAULT_REVIEW_INTERVAL_SECONDS, reviewer_trigger_decision

# 直接脚本运行时切换同目录导入，保持 CLI 入口仍能找到治理依赖。
except ImportError:

    # 脚本入口使用同目录名称解析等价治理依赖。
    from manage_worker_state import validate_worker_states
    from reviewer_session import DEFAULT_REVIEW_INTERVAL_SECONDS, reviewer_trigger_decision

# 复用固定 schema 和 verdict 合同，避免多个 shard 各自定义业务枚举。
try:

    # 包内入口先导入事件摘要和 verdict 合同。
    from .worker_dispatch_contracts import (
        EVENT_TYPES,
        CANONICAL_WORKER_IDS,
        EVENT_BY_PHASE,
        EVENT_BY_ROLE,

        # 阶段和事件转换函数共同提供 dispatcher 的身份映射。
        PHASE_BY_ROLE,
        canonical_worker_id,
        worker_alignment_verdict,
        worker_blocking_verdicts,

        # receipt 和基础字符合同由同一 protocol 模块维护。
        GARDENER_RECEIPT_VERDICTS,
        REVIEWER_RECEIPT_VERDICTS,
        SCHEMA_VERSION,
        SHA256_CHARACTERS,
        PLATFORM_CONTRACT,
    )

    # 包内入口单独导入 tester 失败回传门禁，避免破坏已有导入块可读性。
    from .worker_dispatch_contracts import TESTER_FAILURE_VERDICTS, validate_tester_failure_report

    # 包内入口再导入任务状态和合同查询入口。
    from .worker_dispatch_contracts import (
        TASK_MODES,
        TESTER_RECEIPT_VERDICTS,
        WORKER_NAMES,
        WORKER_STATES,

        # runtime 与结果查询入口保持和包内导入相同的职责边界。
        _load_worker_protocol,
        dispatch_contracts,
        zero_dispatch_verdict,
    )

# 脚本入口没有 package context 时回退到同目录合同模块。
except ImportError:

    # 同目录入口先导入事件摘要和 verdict 合同。
    from worker_dispatch_contracts import (
        EVENT_TYPES,
        CANONICAL_WORKER_IDS,
        EVENT_BY_PHASE,
        EVENT_BY_ROLE,

        # fallback 入口复用同一组阶段和事件转换函数。
        PHASE_BY_ROLE,
        canonical_worker_id,
        worker_alignment_verdict,
        worker_blocking_verdicts,

        # fallback 入口也必须绑定相同的 receipt 和字符合同。
        GARDENER_RECEIPT_VERDICTS,
        REVIEWER_RECEIPT_VERDICTS,
        SCHEMA_VERSION,
        SHA256_CHARACTERS,
        PLATFORM_CONTRACT,
    )

    # 脚本入口单独导入 tester 失败回传门禁，保持 fallback 与包内路径一致。
    from worker_dispatch_contracts import TESTER_FAILURE_VERDICTS, validate_tester_failure_report

    # 同目录入口再导入任务状态和合同查询入口。
    from worker_dispatch_contracts import (
        TASK_MODES,
        TESTER_RECEIPT_VERDICTS,
        WORKER_NAMES,
        WORKER_STATES,

        # fallback 入口复用相同的 runtime 和结果查询能力。
        _load_worker_protocol,
        dispatch_contracts,
        zero_dispatch_verdict,
    )

# tester 的 canonical id 绑定测试 dispatch 的角色归属。
TESTER_WORKER_ID: str = CANONICAL_WORKER_IDS.get("tester", "")  # tester worker 的稳定身份。

# 缺失根状态时使用协议声明的 unconfigured 值 fail-closed。
UNCONFIGURED_STATE: str = "unconfigured" if "unconfigured" in WORKER_STATES else ""  # 未配置状态值。

# implementation start 事件作为新 session 的首个生命周期边界。
INITIAL_EVENT: str = EVENT_BY_ROLE.get("implementation_start", "")  # 实现启动事件名。

# control boundary 事件用于周期 reviewer 触发判断。
CONTROL_BOUNDARY_EVENT: str = EVENT_BY_ROLE.get("control_boundary", "")  # 控制边界事件名。

# commit 事件绑定新提交后的 gardener 只读整理。
COMMIT_EVENT: str = EVENT_BY_ROLE.get("commit", "")  # 提交后审查事件名。

# AGENTS refresh 事件绑定根规则刷新后的 gardener 审查。
AGENTS_REFRESH_EVENT: str = EVENT_BY_ROLE.get("agents_refresh", "")  # 根规则刷新事件名。

# periodic 阶段名供 reviewer 间隔判定使用。
PERIODIC_PHASE: str = PHASE_BY_ROLE.get("periodic", "")  # 周期复核阶段名。

# 只接受协议声明的 TEST_* 事件，避免字符串散落在判断逻辑中。
TEST_EVENTS: frozenset[str] = frozenset(  # tester 事件名称集合。
    str_event  # 当前协议事件名。
    for str_event in EVENT_TYPES  # 遍历协议声明的所有事件。
    if str_event.startswith("TEST_")  # 保留 tester 专属阶段。
)

# 摘要计算入口，所有事件身份都使用 UTF-8 字节确定性复算。
def _sha256_text(str_text: str) -> str:
    """计算文本摘要。

    参数:
        str_text 为待摘要文本。
    返回:
        小写十六进制 SHA-256。

    """

    # 固定 UTF-8 编码，避免平台默认编码改变事件摘要。
    bytes_text = str_text.encode("utf-8")  # 待摘要文本的原始字节。

    # 返回不可变摘要，供 session、event、receipt 复用同一身份规则。
    return hashlib.sha256(bytes_text).hexdigest()

# 摘要格式校验入口，计划、事件和 receipt 共用同一拒绝边界。
def _require_sha256(obj_value: object, str_field_name: str) -> str:
    """校验摘要格式。

    参数:
        obj_value 为待检查对象；str_field_name 为诊断字段名。
    返回:
        已确认格式的摘要。
    异常:
        ValueError 表示摘要不是 64 位小写十六进制文本。

    """

    # 长度和类型不合规时，输入不能进入事件身份。
    if not isinstance(obj_value, str) or len(obj_value) != 64:

        # 短摘要不能绑定可恢复 session。
        raise ValueError(f"> ERR: [Python] {str_field_name} must be a lowercase SHA-256")

    # 字符集不合规时，拒绝大写或非 hex 摘要。
    if any(str_character not in SHA256_CHARACTERS for str_character in obj_value):

        # 非标准摘要不能进入去重键。
        raise ValueError(f"> ERR: [Python] {str_field_name} must be a lowercase SHA-256")

    # 返回已经确认格式的摘要文本。
    return obj_value

# 单调时钟校验入口，周期边界禁止 bool、NaN 和无穷值。
def _require_monotonic(obj_value: object) -> float:
    """校验单调时钟。

    参数:
        obj_value 为当前单调时钟读数。
    返回:
        有限浮点时间。
    异常:
        ValueError 表示时间不是有限数值。

    """

    # bool、非数值、NaN 和无穷值都不能作为周期边界时间。
    if (
        isinstance(obj_value, bool)
        or not isinstance(obj_value, (int, float))
        or not math.isfinite(obj_value)
    ):

        # 无效时钟不能参与 reviewer 周期或 receipt 排序。
        raise ValueError("> ERR: [Python] now_monotonic must be finite")

    # 统一转换为可序列化的有限浮点时间。
    float_now = float(obj_value)  # 本次事件的单调时间。

    # 返回已经通过有限性校验的时间。
    return float_now

# session 路径入口，保证所有状态只落在当前受管项目的 .agents 下。
def _session_path(project: str | Path) -> Path:
    """定位 worker session。

    参数:
        project 为当前受管工作文件夹。
    返回:
        .agents/worker-session.json 的绝对路径。

    """

    # 先规范化项目根，阻止相对路径把状态写到错误工作目录。
    path_project = Path(project).resolve()  # 当前受管项目的绝对路径。

    # 返回唯一 session 文件路径，避免并行状态分叉。
    return path_project / ".agents" / "worker-session.json"

# session 读取入口，统一把缺失、损坏和错误根类型转换为可诊断异常。
def _read_session(path_file: Path) -> dict[str, Any]:
    """读取 worker session。

    参数:
        path_file 为 session 文件路径。
    返回:
        JSON 根对象。
    异常:
        ValueError 表示文件缺失、损坏或根类型错误。

    """

    # 缺失文件不能被猜测成空 session，否则会丢失计划绑定。
    if not path_file.is_file():

        # 让上层按 session 错误停止，而不是创建隐式状态。
        raise ValueError("> ERR: [Python] worker session file is missing")

    # 读取原子提交的 UTF-8 文本，保留 JSON 解析的原始错误位置。
    str_text = path_file.read_text(encoding="utf-8")  # 当前 session 文本。

    # JSON 解析失败时保留文件损坏事实并阻断恢复。
    try:

        # 解析根对象，后续类型判断会拒绝列表和标量。
        obj_session: object = json.loads(str_text)  # 解析持久化 JSON，后续类型分支拒绝非对象根。

    # 解析异常必须带上原始位置，便于修复 session 文件。
    except json.JSONDecodeError as object_error:

        # 将底层 JSON 错误转换为统一 Python 错误协议。
        raise ValueError(
            f"> ERR: [Python] worker session JSON is invalid: {object_error}"
        ) from object_error

    # 状态机只接受对象根，避免把数组当作 worker session。
    if not isinstance(obj_session, dict):

        # 根类型错误不能进入后续字段读取。
        raise ValueError("> ERR: [Python] worker session root must be an object")

    # 返回已经通过根类型检查的 session。
    return obj_session

# session 写入入口，临时文件和 os.replace 共同构成原子提交点。
def _write_session(path_file: Path, dict_session: dict[str, Any]) -> None:
    """原子写入 worker session。

    参数:
        path_file 为目标路径；dict_session 为待写入对象。
    返回:
        None。
    异常:
        OSError 表示临时文件或原子替换失败。

    """

    # 只创建当前 session 所需的 .agents 目录。
    path_file.parent.mkdir(parents=True, exist_ok=True)

    # 固定 JSON 文本形态，避免同一状态产生不同回读内容。
    str_json = json.dumps(  # 待提交的完整 session 文本。
        dict_session,  # 序列化所有生命周期字段。
        ensure_ascii=False,  # 保留中文治理文本。
        indent=2,  # 保持人工审查所需缩进。
        sort_keys=True,  # 固定键序，便于差异复核。
    ) + "\n"

    # 临时文件必须与目标同目录，才能保证替换动作不跨文件系统。
    path_temp = path_file.with_name(  # 本次写入专用的临时路径。
        f"{path_file.name}.{os.getpid()}.tmp"  # 用进程号避免临时名冲突。
    )

    # 写入成功后才允许提交目标 session。
    try:

        # 先完整写入临时文件，避免目标出现半份 JSON。
        path_temp.write_text(str_json, encoding="utf-8")

        # 原子替换是本次 session 状态的唯一提交点。
        os.replace(path_temp, path_file)

    # 任何写入失败都只清理本次临时文件，并把异常继续抛出。
    except OSError:

        # 只检查本次生成的临时文件，绝不触碰既有目标。
        if path_temp.exists():

            # 删除未提交的临时状态，避免下次恢复误读。
            path_temp.unlink()

        # 保留底层文件系统错误，交给统一接口转换。
        raise

# 根据 worker 身份下发独立读写边界。
def _envelope(
    str_worker_id: str,
    str_phase: str,
    path_project: Path,
    str_plan_sha256: str,
    str_task_mode: str,
) -> dict[str, object]:
    """根据运行时协议配置构造职责隔离 envelope。

    参数:
        str_worker_id: canonical worker 身份。
        str_phase: 当前生命周期阶段。
        path_project: 受管项目根路径。
        str_plan_sha256: 已批准方案摘要。
        str_task_mode: 当前任务模式。
    返回:
        严格的 worker envelope。
    异常:
        ValueError 表示 worker 或协议配置无效。

    """

    # 只从运行时注册的合同读取角色字段，避免 Python 复制权限案例。
    dict_contracts = dispatch_contracts()  # canonical worker 合同映射

    # 未配置或非对象角色必须立即阻断，禁止隐式回退。
    dict_contract = dict_contracts.get(str_worker_id)  # 当前角色合同

    # 未知 worker 不能获得默认权限。
    if not isinstance(dict_contract, dict):

        # 未注册的角色不允许获得任何默认权限。
        raise ValueError(f"> ERR: [Python] unknown canonical worker: {str_worker_id}")

    # 路径占位符由协议配置绑定，角色合同只保留相对根名称。
    dict_protocol = _load_worker_protocol()  # 完整 worker 协议对象

    # 读取协议定义的路径占位符映射，避免角色代码复制路径案例。
    dict_bindings = dict_protocol.get("path_bindings")  # 协议定义的路径占位符映射

    # 缺少绑定时无法安全解析 read/write roots。
    if not isinstance(dict_bindings, dict):

        # 协议缺少路径绑定时立即停止 envelope 生成。
        raise ValueError("> ERR: [Python] worker protocol path_bindings must be an object")

    # 将合同中的占位符解析为配置值，保留列表和标量结构。
    def materialize(value_template: object) -> object:
        """递归解析协议中的路径占位符。

        参数:
            value_template: 合同中的标量或路径列表。
        返回:
            解析占位符后的配置值。
        """

        # 列表值逐项解析，保持权限根的顺序稳定。
        if isinstance(value_template, list):

            # 列表合同必须逐项展开占位符。
            return [materialize(value_item) for value_item in value_template]

        # 字符串只替换协议声明的占位符，未知占位符保持可诊断状态。
        if isinstance(value_template, str):

            # 复制字符串值后逐个套用配置绑定。
            str_value = value_template  # 当前待展开的合同字符串

            # 按配置声明顺序替换所有路径占位符。
            for str_name, value_binding in dict_bindings.items():

                # 当前替换结果继续作为下一项绑定的输入。
                str_value = str_value.replace("{" + str(str_name) + "}", str(value_binding))  # 应用当前路径占位符绑定

            # 返回已物化的权限根字符串。
            return str_value

        # 标量合同保持配置文件中的原始类型，不做隐式转换。
        return value_template

    # 复制角色合同并注入本次生命周期与批准方案绑定。
    dict_envelope: dict[str, object] = {  # 保存 schema、身份、阶段和权限根作为唯一派发依据
        "schema_version": SCHEMA_VERSION,  # 版本字段用于拒绝旧协议状态
        "worker_id": str_worker_id,  # 身份字段用于锁定 canonical worker
        "task_kind": dict_contract.get("task_kind"),  # 任务类型字段限制角色职责范围
        "phase": str_phase,  # 阶段字段绑定当前生命周期位置
        "project_root": str(path_project),  # 项目根字段绑定本次受管工作区
        "allowed_read_roots": materialize(dict_contract.get("allowed_read_roots", [])),  # 读取根字段限制可观察文件范围
        "allowed_write_roots": materialize(dict_contract.get("allowed_write_roots", [])),  # 写入根字段限制可修改测试面
        "forbidden_actions": materialize(dict_contract.get("forbidden_actions", [])),  # 禁止动作字段阻断越权操作
        "plan_sha256": str_plan_sha256,  # 方案摘要字段绑定用户确认计划
        "task_mode": str_task_mode,  # 任务模式字段约束本次执行边界
        "expected_output": dict_contract.get("expected_output", ""),  # 输出字段要求回传完整结构化收据
    }

    # 缺失关键合同字段时拒绝发出不完整 envelope。
    tuple_required_fields = (  # envelope 合同必须具备的字段
        "task_kind",  # 任务类型字段
        "allowed_read_roots",  # 读取根字段
        "allowed_write_roots",  # 写入根字段
        "forbidden_actions",  # 禁止动作字段
        "expected_output",  # 回执输出字段
    )

    # 收集配置中缺失或空值的关键字段。
    list_missing_fields = [  # worker 合同缺失字段列表
        str_field  # 当前缺失字段名称
        for str_field in tuple_required_fields  # 遍历合同字段
        if str_field not in dict_contract or dict_envelope.get(str_field) in (None, "")  # 筛选缺失值
    ]

    # 将配置错误定位到具体字段，避免主 Agent猜测协议内容。
    if list_missing_fields:

        # 缺少关键字段时拒绝派发不完整的 envelope。
        raise ValueError(
            "> ERR: [Python] worker protocol contract is incomplete: "
            + ", ".join(list_missing_fields)
        )

    # 返回由 runtime manifest/协议配置物化的最小权限 envelope。
    return dict_envelope

# 将根授权状态转换成 session 使用的运行状态。
def _runtime_state(str_root_state: str) -> str:
    """把 enabled、disabled、unconfigured 映射为运行态。

    参数:
        str_root_state 为根 AGENTS 授权状态。
    返回:
        session 可接受的 runtime 状态。
    异常:
        ValueError 表示根状态未知。
    """

    # enabled worker 尚未被调度，初始运行态必须是 not_started。
    if str_root_state == "enabled":

        # 新授权 worker 等待主 Agent 的显式调度。
        return "not_started"

    # disabled 和 unconfigured 都必须保持 fail-closed。
    if str_root_state in {"disabled", "unconfigured"}:

        # 保留根状态，禁止把拒绝态伪装成可运行态。
        return str_root_state

    # 根状态不在固定集合内时拒绝创建 session。
    raise ValueError(f"> ERR: [Python] unknown root worker state: {str_root_state}")

# 为每个 worker 建立尚未绑定事件收据的状态记录。
def _worker_record(str_state: str) -> dict[str, object]:
    """创建 worker 状态记录。

    参数:
        str_state 为根授权映射后的状态。
    返回:
        未绑定 target 和 receipt 的记录。
    异常:
        ValueError 表示根授权状态不在固定状态集合内。

    """

    # 只接受 dispatcher 定义的运行态，防止状态漂移。
    if str_state not in WORKER_STATES:

        # 未知运行态无法安全参与后续事件校验。
        raise ValueError(f"> ERR: [Python] unknown worker runtime state: {str_state}")

    # 返回空绑定记录，等待真实 agent target 和 receipt 写入。
    return {
        "state": str_state,
        "agent_target": None,
        "last_event_id": None,
        "last_receipt_sha256": None,
        "last_verdict": None,
        "last_monotonic": None,
    }

# 按已批准方案和根 worker 状态创建唯一 managed session。
def _new_session(
    path_project: Path,
    str_plan_sha256: str,
    str_task_mode: str,
    bool_has_test_surface: bool,
    float_now_monotonic: float,
    dict_states: dict[str, str],
) -> dict[str, Any]:
    """创建 managed session。

    参数:
        path_project: 受管项目根路径。
        str_plan_sha256: 已批准方案摘要。
        str_task_mode: 当前任务模式。
        bool_has_test_surface: 是否存在测试面。
        float_now_monotonic: session 起始单调时间。
        dict_states: root AGENTS 的 canonical worker 状态映射。
    返回:
        新的 session 对象。

    """

    # 用项目根、方案、任务模式和单调时间构造 session 身份种子。
    str_seed = (
        f"{path_project}\0{str_plan_sha256}\0{str_task_mode}\0{float_now_monotonic:.9f}"  # 项目方案模式时钟共同构成 session 身份
    )

    # 对种子取摘要，得到不可碰撞地绑定本次 session 的标识。
    str_session_id = _sha256_text(str_seed)  # 将批准方案绑定到不可变 session 摘要

    # 把根授权态展开为三个独立 worker 的运行记录。
    dict_worker_states = {
        str_worker_id: _worker_record(  # 为每个 canonical worker 建立独立状态
            _runtime_state(  # 把根授权态转换为运行态
                dict_states.get(str_worker_id, UNCONFIGURED_STATE)  # 缺省按未配置拒绝
            )
        )
        for str_worker_id in WORKER_NAMES  # 覆盖固定的三个 worker
    }

    # 没有测试面时直接禁用 tester，避免伪造测试生命周期。
    if not bool_has_test_surface:

        # 测试面缺失是明确的 disabled，而不是待调度。
        dict_worker_states[TESTER_WORKER_ID]["state"] = "disabled"  # 缺少测试面时禁止 tester 调度

    # 返回带有生命周期、审查和待调度队列的完整 session。
    return {
        "schema_version": SCHEMA_VERSION,
        "session_status": "active",
        "session_id": str_session_id,
        "project_root": str(path_project),
        "plan_sha256": str_plan_sha256,
        "task_mode": str_task_mode,
        "has_test_surface": bool_has_test_surface,
        "started_monotonic": float_now_monotonic,
        "periodic_sequence": 0,
        "last_reviewer_monotonic": None,
        "reviewer_initial_aligned": False,
        "reviewer_last_verdict": None,
        "reviewer_correction_required": False,
        "tester_final_completed": False,
        "worker_states": dict_worker_states,
        "trigger_events": [],
        "gardener_reviewed_event_ids": [],
        "pending_dispatches": [],
    }

# 读取并核对当前项目的 managed session 绑定。
def _bound_session(project: str | Path) -> tuple[Path, dict[str, Any]]:
    """读取当前项目 session。

    参数:
        project 为受管工作文件夹。
    返回:
        session 路径与对象。
    异常:
        ValueError 表示 session 缺失、版本错误或绑定漂移。

    """

    # 将调用方路径归一化为 session 的项目根。
    path_project = Path(project).resolve()  # 用绝对根路径限制 session 读写范围

    # 先验证 Codex-native 运行前提，避免读取不受管状态。
    list_runtime_errors = _runtime_gate(path_project)  # 收集治理入口和平台支持缺口

    # 运行前提失败时保留所有原因供上层形成稳定错误。
    if list_runtime_errors:

        # 聚合运行时阻断原因，拒绝继续绑定 session。
        raise ValueError(
            "> ERR: [Python] runtime gate failed: " + "; ".join(list_runtime_errors)
        )

    # 定位本项目唯一的 worker session 状态文件。
    path_state = _session_path(path_project)  # 指向本项目唯一 worker-session 文件

    # 读取并校验磁盘上的 session 对象。
    dict_session = _read_session(path_state)  # 载入后续事件必须继承的会话状态

    # 读取主 Agent 的 active session 绑定文件。
    path_active = path_project / ".agents" / "active-session.json"  # 读取主 Agent 的活动绑定证据

    # 默认没有可交叉核对的 active session。
    dict_active: dict[str, Any] = {}  # 没有活动文件时保持空绑定以触发状态校验

    # 仅在 active-session 文件存在时加载第二份绑定证据。
    if path_active.is_file():

        # active-session 与 worker-session 必须来自同一项目。
        dict_active = _read_session(path_active)  # 用活动摘要核对方案和启动时间

    # 没有 active 文件时，只允许已有 active 状态继续。
    elif dict_session.get("session_status") != "active":

        # 非 active session 不能被隐式恢复为工作态。
        raise ValueError("> ERR: [Python] active managed session is missing")

    # 版本不匹配意味着状态结构不能安全解释。
    if dict_session.get("schema_version") != SCHEMA_VERSION:

        # 拒绝跨版本复用 worker session。
        raise ValueError("> ERR: [Python] worker session schema is incompatible")

    # session_id 摘要是后续事件身份计算的必要锚点。
    _require_sha256(dict_session.get("session_id"), "session_id")

    # 确认 session 不能跨项目目录移动使用。
    if dict_session.get("project_root") != str(path_project):

        # 项目根漂移会破坏读写边界，立即停止。
        raise ValueError("> ERR: [Python] worker session project root mismatch")

    # 取出三个 canonical worker 的状态表进行完整性检查。
    dict_worker_states = dict_session.get("worker_states")  # 取出集合校验所需的 canonical 状态表

    # 缺少任一 worker 记录时拒绝部分 session。
    if (
        not isinstance(dict_worker_states, dict)
        or set(dict_worker_states) != set(WORKER_NAMES)
    ):

        # 三类 worker 必须同时存在，不能动态补齐。
        raise ValueError("> ERR: [Python] worker session worker states are incomplete")

    # 校验任务模式、测试面标志和单调起始时间的类型。
    if (
        dict_session.get("task_mode") not in TASK_MODES
        or not isinstance(dict_session.get("has_test_surface"), bool)
        or not isinstance(dict_session.get("started_monotonic"), (int, float))
    ):

        # 生命周期字段类型错误会使后续时间判断失真。
        raise ValueError("> ERR: [Python] worker session lifecycle fields are invalid")

    # active session 存在时还要核对人工会话摘要中的方案绑定。
    if dict_active:

        # 提取摘要文本，供方案摘要绑定检查使用。
        str_active_summary = str(dict_active.get("conversation_summary", "")).lower()  # 规范化 active 摘要中的十六进制大小写。

        # 摘要缺少当前方案摘要时禁止继续操作。
        if str(dict_session.get("plan_sha256", "")).lower() not in str_active_summary:

            # 主 Agent 摘要与 worker session 方案不一致。
            raise ValueError("> ERR: [Python] active managed session plan binding mismatch")

        # active session 必须声明可追溯的启动时间。
        if not str(dict_active.get("started_at", "")).strip():

            # 缺少启动时间意味着 active 绑定证据不完整。
            raise ValueError("> ERR: [Python] active managed session start time is missing")

    # 返回已完成边界校验的 session 路径和载荷。
    return path_state, dict_session

# 按事件类型和载荷生成不可变生命周期事件摘要。
def build_event_id(
    dict_session: dict[str, Any],
    str_event_type: str,
    dict_payload: dict[str, object],
) -> str:
    """生成生命周期事件 ID。

    参数:
        dict_session 为当前 session；str_event_type 为事件名称；dict_payload 为事件载荷。
    返回:
        64 位事件摘要。
    异常:
        ValueError 表示事件字段不完整。

    """

    # 事件摘要必须绑定当前 managed session 身份。
    str_session_id = _require_sha256(dict_session.get("session_id"), "session_id")  # 事件摘要的 session 命名空间

    # 启动事件只绑定批准方案，保证 INITIAL 身份稳定。
    if str_event_type == INITIAL_EVENT:

        # 读取并校验当前 session 的方案摘要。
        str_plan_sha256 = _require_sha256(  # INITIAL 必须继承 session 方案摘要
            dict_session.get("plan_sha256"),  # 从 session 读取批准方案
            "plan_sha256",  # 让校验错误指向方案字段
        )

        # 组装启动事件的固定身份输入。
        str_input = f"{str_session_id}\0{str_plan_sha256}\0{INITIAL_EVENT}"  # 固定启动身份组成

        # 返回启动事件摘要，供去重和收据绑定使用。
        return _sha256_text(str_input)

    # 控制边界事件绑定单调递增的周期序号。
    if str_event_type == CONTROL_BOUNDARY_EVENT:

        # 读取周期序号，后续检查其为非负整数。
        int_sequence = dict_payload.get("periodic_sequence")  # reviewer 周期序号

        # 非法序号会破坏 PERIODIC 事件的单调性。
        if (
            isinstance(int_sequence, bool)
            or not isinstance(int_sequence, int)
            or int_sequence < 0
        ):

            # 拒绝布尔值、负数和非整数周期序号。
            raise ValueError("> ERR: [Python] periodic_sequence must be non-negative")

        # 组装 reviewer 周期事件的身份输入。
        str_input = f"{str_session_id}\0{PERIODIC_PHASE}\0{int_sequence}"  # 将周期序号纳入 reviewer 去重键

        # 返回周期边界摘要。
        return _sha256_text(str_input)

    # 三类测试事件共享 phase、源码和测试树摘要。
    if str_event_type in TEST_EVENTS:

        # 从事件名称提取 tester 生命周期阶段。
        str_phase = str_event_type.removeprefix("TEST_")  # 使事件 phase 与 tester receipt 字段一致

        # 载荷 phase 必须与事件名称完全一致。
        if dict_payload.get("phase", str_phase) != str_phase:

            # 阶段漂移会把测试收据绑定到错误事件。
            raise ValueError("> ERR: [Python] test event phase mismatch")

        # 校验实现源码摘要，绑定当前被测试版本。
        str_source_sha256 = _require_sha256(  # 被测源码摘要
            dict_payload.get("source_sha256"),  # 从测试载荷读取被测源码摘要
            "source_sha256",  # 指向源码摘要校验字段
        )

        # 校验测试树摘要，防止跨测试版本复用收据。
        str_tests_sha256 = _require_sha256(  # 测试树摘要
            dict_payload.get("tests_sha256"),  # 从测试载荷读取测试树摘要
            "tests_sha256",  # 指向测试树摘要校验字段
        )

        # 将 session、阶段、源码和测试摘要串成事件身份。
        str_input = (  # tester 摘要同时绑定会话、阶段和两棵树
            f"{str_session_id}\0{str_phase}\0"  # 会话命名空间和测试阶段
            f"{str_source_sha256}\0{str_tests_sha256}"  # 源码版本和测试版本
        )

        # 返回 tester 事件摘要。
        return _sha256_text(str_input)

    # commit 事件绑定完整提交摘要，而非短提交前缀。
    if str_event_type == COMMIT_EVENT:

        # 校验提交内容摘要，作为 gardener 事件身份输入。
        str_commit_sha256 = _require_sha256(  # 完整提交摘要
            dict_payload.get("full_commit_sha256"),  # 从提交载荷读取完整摘要
            "full_commit_sha256",  # 指向完整提交摘要校验字段
        )

        # 返回绑定当前 session 的提交事件摘要。
        return _sha256_text(f"{str_session_id}\0commit\0{str_commit_sha256}")

    # AGENTS refresh 事件必须同时绑定刷新前后的字节摘要。
    if str_event_type == AGENTS_REFRESH_EVENT:

        # 校验刷新前的治理文件摘要。
        str_before_sha256 = _require_sha256(  # 刷新前摘要
            dict_payload.get("before_sha256"),  # 读取治理文件刷新前摘要
            "before_sha256",  # 指向刷新前字节摘要字段
        )

        # 校验刷新后的治理文件摘要。
        str_after_sha256 = _require_sha256(  # 刷新后摘要
            dict_payload.get("after_sha256"),  # 读取治理文件刷新后摘要
            "after_sha256",  # 指向刷新后字节摘要字段
        )

        # 治理文件字节必须真实变化，禁止伪造 refresh 证据。
        if str_before_sha256 == str_after_sha256:

            # 相同摘要不构成 AGENTS refresh。
            raise ValueError("> ERR: [Python] AGENTS refresh bytes did not change")

        # 组装治理刷新事件的身份输入。
        str_input = (  # 用 session 与前后字节摘要证明 AGENTS 确实刷新
            f"{str_session_id}\0agents-refresh\0{str_before_sha256}\0{str_after_sha256}"  # 固定治理刷新身份输入
        )

        # 返回治理刷新事件摘要。
        return _sha256_text(str_input)

    # 其余事件使用排序后的规范 JSON 载荷保持摘要确定性。
    str_payload = json.dumps(  # 通用事件规范载荷
        dict_payload,  # 原始事件字段
        ensure_ascii=False,  # 保留中文字段内容
        sort_keys=True,  # 固定字段顺序
        separators=(",", ":"),  # 去除无关空白
    )

    # 返回通用事件摘要。
    return _sha256_text(f"{str_session_id}\0{str_event_type}\0{str_payload}")

# 判断根 AGENTS 状态是否允许指定 worker 执行。
def _authorized(dict_states: dict[str, str], str_worker_id: str) -> tuple[bool, str]:
    """判断根状态是否授权 worker。

    参数:
        dict_states 为根状态；str_worker_id 为角色身份。
    返回:
        授权标志和原因文本。

    """

    # 缺省状态必须按未配置处理，禁止隐式授权。
    str_state = dict_states.get(str_worker_id, "unconfigured")  # worker 根授权态

    # enabled 是唯一可以进入调度队列的授权态。
    if str_state == "enabled":

        # 返回允许标志和空原因，供上层继续生成派发项。
        return True, ""

    # disabled 保留为可解释的显式跳过结果。
    if str_state == "disabled":

        # 返回禁止标志及稳定拒绝原因。
        return False, "worker is explicitly disabled"

    # 其他状态都按未配置拒绝。
    return False, "worker state is unconfigured"

# 加载平台配置函数，兼容 CLI 和受控模块加载两种入口。
def _load_agent_config() -> Callable[[Path], Any]:
    """加载平台配置读取函数，并兼容受控模块加载入口。

    参数:
        无；模块位置决定 common/agent_platform.py 的候选路径。
    返回:
        可读取并校验平台配置的函数。
    异常:
        ModuleNotFoundError: 顶层导入和同目录 fallback 均不可用。
        ImportError: fallback 模块缺少可执行加载器或目标函数。
    """

    # 正常脚本入口优先复用 Python 搜索路径中的 canonical 模块。
    try:

        # 直接运行 manage_workers.py 时 common 目录通常已由入口加入搜索路径。
        from agent_platform import load_agent_config

    # 测试或受控模块加载未暴露 common 目录时走文件级 fallback。
    except ModuleNotFoundError as object_import_error:

        # worker_dispatch.py 位于 scripts/python/workers，common 与 workers 同级。
        path_module = Path(__file__).resolve().parents[1] / "common" / "agent_platform.py"  # 平台配置模块路径。

        # 缺少 fallback 源文件时保留原始导入失败语义。
        if not path_module.is_file():

            # 不把缺少治理模块误判为平台配置有效。
            raise ModuleNotFoundError(
                "> ERR: [Python] worker agent_platform module is unavailable"
            ) from object_import_error

        # 为 fallback 模块建立独立名称，避免污染 agent_platform 的导入缓存。
        module_type_spec: ModuleSpec | None = importlib.util.spec_from_file_location(  # fallback 模块加载规格。
            "agents_md_worker_agent_platform",  # 与顶层模块区分的内部名称。
            path_module,  # 当前 skill 源码中的平台配置文件。
        )

        # 缺少 loader 时无法安全执行 fallback 源码。
        if module_type_spec is None or module_type_spec.loader is None:

            # 将不完整的导入规格收敛为标准 ImportError。
            raise ImportError(
                "> ERR: [Python] worker agent_platform fallback loader is unavailable"
            )

        # 根据规格创建待执行模块对象。
        module_type_agent_platform: ModuleType = importlib.util.module_from_spec(module_type_spec)  # fallback 平台模块对象。

        # dataclasses 和模块内类型解析要求 fallback 先注册到 sys.modules。
        sys.modules[module_type_agent_platform.__name__] = module_type_agent_platform  # 注册 fallback 模块供 dataclasses 解析。

        # 执行同一份源码，避免复制平台配置逻辑造成漂移。
        module_type_spec.loader.exec_module(module_type_agent_platform)

        # 读取目标函数并由返回标注约束调用方接口。
        func_load_agent_config = getattr(module_type_agent_platform, "load_agent_config", None)  # fallback 配置读取函数。

        # fallback 文件缺少目标函数时拒绝继续运行。
        if not callable(func_load_agent_config):

            # 不允许以空函数替代平台能力检查。
            raise ImportError(
                "> ERR: [Python] worker agent_platform fallback lacks load_agent_config"
            )

        # 返回经过 callable 校验的 fallback 函数。
        return func_load_agent_config

    # 返回正常入口加载的 canonical 函数。
    return load_agent_config

# 检查 dispatcher 依赖的 managed-root 和 Codex-native 前提。
def _runtime_gate(path_project: Path) -> list[str]:
    """验证 Codex-native 与 managed-root 前提。

    参数:
        path_project 为项目绝对路径。
    返回:
        空列表表示通过，否则返回阻断原因。

    """

    # 定位项目根治理文件。
    path_agents = path_project / "AGENTS.md"  # 由此文件确认项目是否受 managed-root 合同管理

    # 定位 worker 状态与路由控制文件。
    path_control = path_project / ".agents" / "agents-control.json"  # 控制文件路径

    # 汇总所有前提失败，避免只报告第一项。
    list_errors: list[str] = []  # 运行时阻断原因

    # 根 AGENTS 缺失时无法确认 worker 合同。
    if not path_agents.is_file():

        # 记录治理入口缺失。
        list_errors.append("managed project root AGENTS.md is missing")

    # 控制文件缺失时不能读取 canonical worker 状态。
    if not path_control.is_file():

        # 记录状态控制入口缺失。
        list_errors.append("managed project .agents/agents-control.json is missing")

    # 已有 AGENTS 时确认其包含受管元数据。
    if path_agents.is_file():

        # 读取治理文本只用于验证受管标记。
        str_agents_text = path_agents.read_text(encoding="utf-8", errors="ignore")  # 只读取元数据标记，不解释业务正文

        # 没有生成或元数据标记时，拒绝按 managed root 运行。
        if "AGENTS-METADATA:" not in str_agents_text and "AGENTS-GENERATED:" not in str_agents_text:

            # 记录根文件来源不可验证。
            list_errors.append("managed project root AGENTS.md metadata is missing")

    # 平台配置加载失败时不能假设 worker 支持存在。
    try:

        # 读取 Codex-native 平台配置入口，并兼容隔离模块加载。
        func_load_agent_config = _load_agent_config()  # 平台配置读取函数。

        # 从当前模块位置解析 skill 根目录。
        path_skill_root = Path(__file__).resolve().parents[3]  # 从模块位置回溯到平台 profile 的 skill 根

        # 读取平台 profile，确认当前运行时支持 canonical worker。
        profile_agent = func_load_agent_config(path_skill_root)  # 用 profile 确认当前进程具备 Codex-native worker 支持

    # 文件或配置内容异常都属于运行时阻断。
    except (ImportError, OSError, ValueError) as object_error:

        # 保留底层异常文本，便于调用方定位环境问题。
        list_errors.append(f"Codex platform profile is unavailable: {object_error}")

    # 配置已加载时验证 protocol 声明的平台身份和 worker 支持标识。
    else:

        # 缺失平台合同时不能把任意 profile 当作受管运行时。
        str_native_agent = str(PLATFORM_CONTRACT.get("native_agent", "")).strip()  # 当前 protocol 声明的 native 平台。

        # 读取 protocol 声明的 canonical worker 能力要求。
        str_required_worker_support = str(PLATFORM_CONTRACT.get("required_worker_support", "")).strip()  # 当前 protocol 声明的 worker 能力。

        # 配置字段不完整时保持 fail-closed。
        if not str_native_agent or not str_required_worker_support:

            # 平台合同不完整不能授予 canonical worker 能力。
            list_errors.append("worker platform contract is incomplete")

        # 当前 profile 必须与受管 protocol 的平台合同完全一致。
        elif (
            getattr(profile_agent, "agent", None) != str_native_agent
            or getattr(profile_agent, "worker_support", None) != str_required_worker_support
        ):

            # 记录平台身份或 worker 支持能力不匹配。
            list_errors.append("canonical workers require the configured native platform contract")

    # 返回完整前提失败列表，空列表表示通过。
    return list_errors

# 公开低层名称供事件和 receipt shard 在包内及脚本入口复用。
__all__ = [str_name for str_name in globals() if not str_name.startswith("__")]  # shard 共享的低层名称。
