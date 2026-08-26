"""提供 canonical worker 生命周期 CLI 和兼容导出。"""

# 延迟类型注解求值，兼容项目支持的 Python 运行环境。
from __future__ import annotations

# CLI 只使用标准库完成参数解析、JSON 输出和路径处理。
import argparse
import json
from pathlib import Path
import sys
from typing import Any

# 让直接脚本入口能够解析同目录共享模块。
def _extend_search_path() -> None:
    """登记 scripts/python 下的兄弟任务目录。

    参数:
        无显式参数；路径由当前文件位置确定。
    返回:
        None；仅更新当前进程的模块搜索路径。
    """

    # 当前文件的上两级是 scripts/python 根目录。
    path_root = Path(__file__).resolve().parents[1]  # 脚本根目录。

    # 只登记实际任务目录，避免引入无效搜索路径。
    list_paths = [str(path_item) for path_item in path_root.iterdir() if path_item.is_dir()]  # 兄弟任务目录。

    # 将未登记目录放到最前面，保持模块解析确定性。
    sys.path[:0] = [str_path for str_path in list_paths if str_path not in sys.path]  # 更新模块搜索路径。

# 注册同目录任务路径后再加载本地模块。
_extend_search_path()

# 动态配置决定平台选择与稳定的 CLI choices。
from agent_platform import load_catalog

# profile 与状态职责已经拆分到受控 shard。
from worker_profile_routing import apply_workers
from worker_state_reporting import preview_workers
from worker_state_reporting import reviewer_session_status
from worker_state_reporting import validate_review_worker
from worker_state_reporting import verify_workers
from worker_state_reporting import worker_status
from manage_worker_state import apply_authorization_state
from manage_worker_state import preview_authorization_state

# dispatcher 负责统一 session、事件和 receipt 状态机。
from worker_dispatch import check_dispatch_event
from worker_dispatch import dispatch_contracts
from worker_dispatch import dispatch_exit_code
from worker_dispatch import dispatch_repair
from worker_dispatch import record_dispatch_result
from worker_dispatch import start_dispatch_session
from worker_dispatch_contracts import CANONICAL_WORKER_IDS, LIFECYCLE_PHASES, worker_repair_config

# reviewer 的 canonical id 供旧 CLI 兼容入口绑定唯一审查角色。
REVIEWER_WORKER_ID: str = CANONICAL_WORKER_IDS.get("reviewer", "")  # reviewer 生命周期身份键。

# 默认阶段沿用协议第二项，保证旧 review-session 与新 dispatcher 一致。
DEFAULT_REVIEW_PHASE: str = LIFECYCLE_PHASES[1] if len(LIFECYCLE_PHASES) > 1 else ""  # 兼容 reviewer 默认阶段。

# repair 阶段从配置补充 tester RED/GREEN，避免 CLI 只接受 reviewer 阶段。
REPAIR_PHASES: tuple[str, ...] = tuple(  # 受管 repair 阶段集合。
    str(str_phase)  # 将配置项规范化为字符串。
    for str_phase in worker_repair_config().get("allowed_phases", [])  # 遍历配置声明的 repair 阶段。
    if str(str_phase).strip()  # 忽略空白阶段，避免生成不可派发选项。
)

# 去重后的阶段集合同时服务 review-session 和 dispatch-repair。
DISPATCH_PHASE_CHOICES: tuple[str, ...] = tuple(dict.fromkeys((*LIFECYCLE_PHASES, *REPAIR_PHASES)))  # review 与 repair 共用的阶段选项。

# 解析 dispatch 载荷并固定 JSON object 边界。
def _dispatch_payload(
    str_payload: str,
    str_field_name: str = "event_payload",
) -> dict[str, object]:
    """解析 dispatch 事件或失败报告载荷。

    参数:
        str_payload: 命令行传入的 JSON 文本。
        str_field_name: 载荷字段名，用于生成可定位的错误。
    返回:
        JSON 对象载荷。
    异常:
        ValueError: 载荷不是合法 JSON 对象。
    """

    # JSON 解析失败必须通过机器协议返回参数错误。
    try:

        # 事件和失败报告都只接受对象，拒绝列表和标量。
        obj_payload = json.loads(str_payload)  # 已解析的 dispatch 对象。

    # 保留原始错误位置，方便修复调用参数。
    except json.JSONDecodeError as object_error:

        # 将解析错误转换为当前 CLI 的 Python 错误前缀。
        raise ValueError(
            f"> ERR: [Python] {str_field_name} is invalid JSON: {object_error}"
        ) from object_error

    # 根类型错误不能被隐式转换。
    if not isinstance(obj_payload, dict):

        # 统一要求 dispatch 载荷使用 JSON object。
        raise ValueError(f"> ERR: [Python] {str_field_name} must be a JSON object")

    # 返回已经确认类型的事件载荷。
    return obj_payload

# 将 dispatch 异常转换为可审计的失败结果。
def _dispatch_failure(
    project: str,
    object_error: Exception,
) -> dict[str, object]:
    """将 dispatch 异常包装为单一 JSON 结果。

    参数:
        project: 当前工作文件夹路径。
        object_error: dispatch 输入或 session 异常。
    返回:
        符合 dispatch schema 的失败结果。
    """

    # 错误文本保留稳定的 Python 前缀，避免 CLI 产生未结构化 traceback。
    str_error = str(object_error)  # dispatch 失败文本。

    # session 错误使用 exit code 3，其余输入错误使用 exit code 2。
    bool_session_error = "session" in str_error.lower()  # 是否为 session 生命周期错误。

    # 状态路径由当前项目根派生，避免返回固定工作目录文本。
    str_state_path = (Path(project).resolve() / "AGENTS.md").as_posix()  # 当前项目根状态文件

    # 返回内部标记供 main 决定退出码，输出前会移除该字段。
    return {
        "schema_version": 1,
        "session_id": None,
        "event_id": None,
        "event_type": None,
        "valid": False,
        "blocking": True,
        "required_dispatches": [],
        "pending_dispatches": [],
        "skipped_dispatches": [],
        "errors": [str_error],
        "state_path": str_state_path,
        "_input_error": not bool_session_error,
    }

# 启动当前 dispatcher 会话并返回机器可读结果。
def _run_dispatch_start(namespace_namespace: argparse.Namespace, str_project: str) -> dict[str, object]:
    """执行 dispatch-start 子命令。

    参数:
        namespace_namespace: 已解析的 worker CLI 参数。
        str_project: 当前项目路径。
    返回:
        dispatch-start JSON 结果。
    """

    # dispatch-start 需要完整计划摘要和单调时钟。
    try:

        # 统一调用 dispatcher 的公共启动接口。
        return start_dispatch_session(
            str_project,
            namespace_namespace.plan_sha256,
            namespace_namespace.task_mode,
            namespace_namespace.has_test_surface,
            namespace_namespace.now_monotonic,
        )

    # 参数或 session 失败都不能输出 traceback 污染 JSON 协议。
    except (TypeError, ValueError, OSError) as object_error:

        # 将异常转换成固定失败 schema。
        return _dispatch_failure(str_project, object_error)

# 检查已记录的 dispatcher 事件和 session 绑定。
def _run_dispatch_check(namespace_namespace: argparse.Namespace, str_project: str) -> dict[str, object]:
    """执行 dispatch-check 子命令。

    参数:
        namespace_namespace: 已解析的 worker CLI 参数。
        str_project: 当前项目路径。
    返回:
        dispatch-check JSON 结果。
    """

    # 事件 payload 解析属于 CLI 输入门禁。
    try:

        # 先解析 JSON，再进入 dispatcher 的事件校验。
        dict_payload = _dispatch_payload(namespace_namespace.event_payload)  # 事件载荷对象。

        # 统一调用 dispatcher 的事件检查接口。
        return check_dispatch_event(
            str_project,
            namespace_namespace.event_type,
            dict_payload,
            namespace_namespace.now_monotonic,
        )

    # 输入、哈希和 session 错误都转换为机器结果。
    except (TypeError, ValueError, OSError) as object_error:

        # 保留 session 错误的 exit code 3 语义。
        return _dispatch_failure(str_project, object_error)

# 记录真实 worker target 与 receipt 结果。
def _run_dispatch_record(namespace_namespace: argparse.Namespace, str_project: str) -> dict[str, object]:
    """执行 dispatch-record 子命令。

    参数:
        namespace_namespace: 已解析的 worker CLI 参数。
        str_project: 当前项目路径。
    返回:
        dispatch-record JSON 结果。
    """

    # record 输入必须完整包含真实 target、receipt 和 verdict。
    try:

        # tester 失败时解析详细报告；成功或其他 worker 可以不携带该字段。
        dict_failure_report = (  # tester 失败报告对象
            _dispatch_payload(namespace_namespace.failure_report, "failure_report")  # 解析报告 JSON
            if namespace_namespace.failure_report is not None  # 仅失败回传需要报告
            else None  # 成功 receipt 不构造失败报告
        )

        # reviewer/gardener 范围拒绝使用独立报告，避免误套 tester 失败字段。
        dict_rejection_report = (
            _dispatch_payload(namespace_namespace.rejection_report, "rejection_report")  # 解析 reviewer/gardener 拒绝载荷。
            if namespace_namespace.rejection_report is not None  # 仅收到拒绝报告时进入解析。
            else None  # 成功 receipt 不附带拒绝报告。
        )

        # 统一记录主 Agent实际协作调用返回的证据。
        return record_dispatch_result(
            str_project,

            # 绑定本次 dispatch 事件的唯一标识和 worker 身份。
            namespace_namespace.event_id,
            namespace_namespace.worker_id,

            # 绑定真实 target、receipt、verdict 和单调时间。
            namespace_namespace.agent_target,
            namespace_namespace.receipt_sha256,
            namespace_namespace.verdict,
            namespace_namespace.now_monotonic,
            dict_failure_report,
            dict_rejection_report,
        )

    # 记录失败不能通过 traceback 绕过单 JSON 协议。
    except (TypeError, ValueError, OSError) as object_error:

        # 返回固定失败结果，由 main 映射方案规定的退出码。
        return _dispatch_failure(str_project, object_error)

# 生成同一 target 的修复 follow-up，并把熔断状态保持为 JSON。
def _run_dispatch_repair(namespace_namespace: argparse.Namespace, str_project: str) -> dict[str, object]:
    """执行 dispatch-repair 子命令。

    参数:
        namespace_namespace: 已解析的 worker CLI 参数。
        str_project: 当前工作文件夹路径。
    返回:
        同一 canonical target 的 repair follow-up 结果。
    """

    # 逗号分隔字段来自主 Agent 的结构化修复上下文。
    list_correction_fields: list[str] = [  # 当前 repair 需要修正的字段。
        str_field.strip()  # 去除单个字段的外围空白。
        for str_field in namespace_namespace.correction_fields.split(",")  # 按 CLI 分隔符拆分字段。
        if str_field.strip()  # 忽略空字段，避免 repair 载荷出现空键。
    ]

    # 统一调用 facade，确保 target 复用和熔断边界不在 CLI 重复实现。
    return dispatch_repair(
        str_project,
        namespace_namespace.event_id,
        namespace_namespace.worker_id,
        namespace_namespace.phase,
        list_correction_fields,
    )

# 读取审查输入并在格式异常时保留原文。
def _load_review_input(path_input: str | Path) -> object:
    """读取 JSON 计划或回退为 UTF-8 文本。

    参数:
        path_input: 计划或执行记录文件路径。
    返回:
        JSON 值；文本不是 JSON 时返回原始字符串。
    """

    # 文件读取失败由调用方看到，不能静默生成空计划。
    str_text = Path(path_input).read_text(encoding="utf-8")  # 计划或执行记录文本。

    # 结构化文件优先进入 JSON 比较流程。
    try:

        # 解析结构化计划，供后续字段级一致性检查。
        return json.loads(str_text)

    # 非 JSON 记录仍按原文参与偏离审查。
    except json.JSONDecodeError:

        # 非 JSON 输入保留原文，避免误判为缺失计划。
        return str_text

# 从兼容映射中读取第一个存在的字段。
def _field(value: object, *names: str) -> object:
    """从映射中按候选字段名读取第一个存在的值。

    参数:
        value: 待读取的 JSON 值。
        names: 按优先级排列的字段名。
    返回:
        第一个存在的字段值；非映射或未命中时返回 None。
    """

    # 非对象值不具备可审查的命名字段。
    if not isinstance(value, dict):

        # 保持缺失语义，不推断字段内容。
        return None

    # 保持候选字段的用户约定优先顺序。
    for str_name in names:

        # 命中后立即返回，防止别名覆盖规范字段。
        if str_name in value:

            # 返回原始值，让调用方决定比较方式。
            return value[str_name]

    # 没有候选字段时保持缺失语义。
    return None

# 组合计划和执行记录的兼容审查字段。
def _review_fields(obj_plan: object, obj_execution: object) -> dict[str, object]:
    """提取范围、越界和设计字段供一致性比较。

    参数:
        obj_plan: 已确认计划对象或文本。
        obj_execution: 实际执行对象或文本。
    返回:
        包含六个规范比较字段的映射。
    """

    # 返回字典直接表达字段来源，避免调用方重复解析别名。
    return {
        "plan_scope": _field(obj_plan, "scope", "in_scope", "in-scope"),
        "execution_scope": _field(obj_execution, "scope", "in_scope", "in-scope"),
        "plan_out": _field(obj_plan, "out_of_scope", "out-of-scope"),
        "execution_out": _field(obj_execution, "out_of_scope", "out-of-scope"),
        "plan_design": _field(obj_plan, "design", "design_contract"),
        "execution_design": _field(obj_execution, "design", "design_contract"),
    }

# 按输入完整性选择计划审查或 reviewer 配置审查。
def _dispatch_validate_review(
    namespace_namespace: argparse.Namespace,
    bool_plan_review: bool,
    bool_partial_plan_inputs: bool,
    str_project: str,
) -> dict[str, Any]:
    """执行 validate-review 子命令的唯一分派路径。

    参数:
        namespace_namespace: 已解析的 CLI 参数集合。
        bool_plan_review: 是否同时提供计划与执行记录。
        bool_partial_plan_inputs: 是否只提供了两个计划输入中的一个。
        str_project: 当前工作文件夹路径。
    返回:
        计划执行审查或 reviewer 配置审查结果。
    """

    # 计划审查必须成对接收输入，禁止半套参数静默切换审查模式。
    if bool_partial_plan_inputs:

        # 失败结果保持机器可读并让主入口返回非零状态。
        return {
            "ok": False,
            "error": "--plan and --execution must be provided together",
            "reviewer": REVIEWER_WORKER_ID,
        }

    # 两个输入齐全时只比较批准计划和实际执行记录。
    if bool_plan_review:

        # 计划路径来自已解析的显式命令行参数。
        return validate_plan_execution(
            namespace_namespace.plan,
            namespace_namespace.execution,
            str_project,
        )

    # 没有计划输入时回退到 reviewer profile 和根状态检查。
    return validate_review_worker(namespace_namespace.codex_home, str_project)

# 验证计划执行记录的结构边界。
def _validate_plan_execution_shapes(
    obj_plan: Any,
    obj_execution: Any,
    dict_fields: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    """校验计划与执行记录的对象形状及三类必需基线。

    参数:
        obj_plan: 已解析的批准计划值。
        obj_execution: 已解析的执行记录值。
        dict_fields: 按兼容字段名提取的比较字段。
    返回:
        范围、范围外和设计三类形状诊断列表。
    """

    # 范围差异使用独立列表，供结果字段直接呈现。
    list_scope: list[str] = []  # 范围偏离诊断。

    # 范围外变化使用独立列表，避免与范围差异混合。
    list_out: list[str] = []  # 越界诊断。

    # 设计变化使用独立列表，便于审查方案基线。
    list_design: list[str] = []  # 设计偏离诊断。

    # 计划和执行记录必须提供可定位的三类一致性基线。
    if not isinstance(obj_plan, dict):

        # 非对象计划没有可核对的批准范围。
        list_scope.append("approved plan must be a JSON object")

    # 对象计划缺少范围时不能默认认为范围为空。
    elif dict_fields["plan_scope"] is None:

        # 缺少批准范围必须阻断一致性结论。
        list_scope.append("approved plan scope is missing")

    # 执行记录也必须保持对象形状。
    if not isinstance(obj_execution, dict):

        # 非对象执行记录无法证明实际范围。
        list_scope.append("execution record must be a JSON object")

    # 对象执行记录缺少范围时不能默认认为没有偏离。
    elif dict_fields["execution_scope"] is None:

        # 缺少执行范围必须阻断一致性结论。
        list_scope.append("execution scope is missing")

    # 批准计划必须显式声明范围外事项。
    if isinstance(obj_plan, dict) and dict_fields["plan_out"] is None:

        # 缺失的范围外边界会掩盖新增工作。
        list_out.append("approved plan out-of-scope boundary is missing")

    # 执行记录必须回显范围外事项，方便复核实际越界。
    if isinstance(obj_execution, dict) and dict_fields["execution_out"] is None:

        # 缺失的执行边界不能被当成一致。
        list_out.append("execution out-of-scope boundary is missing")

    # 批准计划必须保留设计合同，避免 reviewer 只比较路径文字。
    if isinstance(obj_plan, dict) and dict_fields["plan_design"] is None:

        # 设计合同缺失时无法判断实现是否改变方案。
        list_design.append("approved plan design contract is missing")

    # 执行记录必须回显设计合同，才能检测实际设计漂移。
    if isinstance(obj_execution, dict) and dict_fields["execution_design"] is None:

        # 缺少执行设计合同必须阻断通过结论。
        list_design.append("execution design contract is missing")

    # 返回三类形状诊断，交给比较阶段继续追加差异。
    return list_scope, list_out, list_design

# 汇总计划与执行记录之间的字段差异。
def _append_plan_execution_differences(
    dict_fields: dict[str, Any],
    list_scope: list[str],
    list_out: list[str],
    list_design: list[str],
) -> None:
    """将计划与执行记录的字段差异追加到既有诊断列表。

    参数:
        dict_fields: 按兼容字段名提取的比较字段。
        list_scope: 用于追加范围差异的列表。
        list_out: 用于追加范围外差异的列表。
        list_design: 用于追加设计差异的列表。
    返回:
        None；差异直接追加到传入列表。
    """

    # 仅当批准计划给出范围时才比较执行范围。
    if dict_fields["plan_scope"] is not None and dict_fields["execution_scope"] != dict_fields["plan_scope"]:

        # 执行范围与已确认范围不一致。
        list_scope.append("execution scope differs from approved plan scope")

    # 计划明确范围外内容时，执行记录必须保持一致。
    if dict_fields["plan_out"] is not None and dict_fields["execution_out"] != dict_fields["plan_out"]:

        # 记录新增或修改范围外事项。
        list_out.append("execution includes or changes out-of-scope items")

    # 设计合同存在时必须逐值保持一致。
    if dict_fields["plan_design"] is not None and dict_fields["execution_design"] != dict_fields["plan_design"]:

        # 记录执行设计相对批准设计的漂移。
        list_design.append("execution design differs from approved plan design")

# 生成绑定批准计划和执行记录的稳定审查结果。
def validate_plan_execution(
    plan_path: str | Path,
    execution_path: str | Path,
    project: str | Path = ".",
) -> dict[str, Any]:
    """比较批准方案与执行记录，报告范围、越界和设计偏离。

    参数:
        plan_path: 用户已确认的计划文件路径。
        execution_path: 当前执行记录文件路径。
        project: 当前工作文件夹路径，保留作审计上下文。
    返回:
        包含 ok、scope、out-of-scope 和 design 诊断的映射。
    """

    # 当前版本比较计划与执行文件，不额外读取项目目录。
    del project

    # 读取两份审查输入并保留原始数据类型。
    obj_plan = _load_review_input(plan_path)  # 批准计划值。

    # 执行记录用于和批准计划逐项比较。
    obj_execution = _load_review_input(execution_path)  # 执行记录值。

    # 按兼容字段名提取三类 reviewer 重点。
    dict_fields = _review_fields(obj_plan, obj_execution)  # 计划执行比较字段。

    # 先校验计划与执行记录的对象形状和必需基线。
    tuple_shape_diagnostics = _validate_plan_execution_shapes(obj_plan, obj_execution, dict_fields)  # 形状诊断列表。

    # 取出范围、范围外和设计三类可追加诊断列表。
    list_scope = tuple_shape_diagnostics[0]  # 范围诊断列表。

    # 取出范围外诊断列表。
    list_out = tuple_shape_diagnostics[1]  # 范围外诊断列表。

    # 取出设计诊断列表。
    list_design = tuple_shape_diagnostics[2]  # 设计诊断列表。

    # 再比较三类已存在的计划执行字段。
    _append_plan_execution_differences(  # 追加字段差异。
        dict_fields,
        list_scope,
        list_out,
        list_design,
    )

    # 没有任何诊断才允许 reviewer 判定通过。
    bool_ok = not list_scope and not list_out and not list_design  # 计划执行一致状态。

    # 返回稳定字段，供 CLI 和上层审计读取。
    return {
        "ok": bool_ok,
        "scope": list_scope,
        "out-of-scope": list_out,
        "design": list_design,
        "plan": str(plan_path),
        "execution": str(execution_path),
        "reviewer": REVIEWER_WORKER_ID,
    }

# 构造保持参数顺序兼容的 worker 生命周期 CLI。
def _build_parser() -> argparse.ArgumentParser:
    """构造 worker 管理命令行解析器。

    参数:
        无；解析器合同由当前 CLI 版本固定。
    返回:
        配置完成的 argparse.ArgumentParser。
    """

    # parser 统一提供机器可读 JSON 输出入口。
    parser = argparse.ArgumentParser(  # 生命周期 CLI 解析器。
        description="Manage canonical worker profiles and root-only state."  # CLI 帮助文本。
    )

    # 生命周期子命令保持公开名称稳定。
    parser.add_argument(
        "command",
        choices=(
            "status",
            "preview",
            "apply",
            "state-preview",
            "state-apply",
            "verify",
            "validate-review",
            "review-session",
            "dispatch-start",
            "dispatch-check",
            "dispatch-record",
            "dispatch-repair",
        ),
    )

    # project 可继续使用子命令后的定位参数。
    parser.add_argument("project", nargs="?", default=".")

    # --project 为脚本调用方保留显式命名形式。
    parser.add_argument("--project", dest="project_option", default=None)

    # 状态 profile 路径由调用方提供，避免 CLI 固定当前项目案例。
    parser.add_argument("--state-profile", default=None)

    # state-apply 必须绑定 state-preview 产生的摘要。
    parser.add_argument("--expected-preview-sha256", default=None)

    # --codex-home 允许临时隔离 profile 存储位置。
    parser.add_argument("--codex-home", default=None)

    # tester 更新必须由用户显式确认。
    parser.add_argument("--confirm-tester-update", action="store_true")

    # reviewer 更新必须确认完整默认内容的 SHA-256。
    parser.add_argument("--confirm-reviewer-sha256", default="")

    # gardener 更新必须由用户显式确认完整 proposed 内容。
    parser.add_argument("--confirm-gardener-update", action="store_true")

    # 新写入流程使用三个 profile 与 gardener 工具的统一 bundle 收据。
    parser.add_argument("--confirm-profile-bundle-sha256", default="")

    # validate-review 接受批准计划文件。
    parser.add_argument("--plan", default=None)

    # validate-review 接受实际执行记录文件。
    parser.add_argument("--execution", default=None)

    # review-session 公开阶段、计划摘要和可选平台选择。
    parser.add_argument("--phase", choices=DISPATCH_PHASE_CHOICES, default=DEFAULT_REVIEW_PHASE)

    # review-session 使用批准计划摘要绑定当前会话。
    parser.add_argument("--plan-sha256", default=None)

    # 可选单调时钟用于复现 reviewer 间隔判断。
    parser.add_argument("--now-monotonic", type=float, default=None)

    # reviewer 触发间隔保持可配置但默认稳定。
    parser.add_argument("--review-interval", type=float, default=600.0)

    # receipt 摘要用于证明 reviewer 已经完成审查。
    parser.add_argument("--receipt-sha256", default=None)

    # tester 失败必须通过 JSON 载荷提交可执行诊断，不能只给失败结论。
    parser.add_argument("--failure-report", default=None)

    # reviewer/gardener 范围拒绝必须通过 JSON 载荷提交具体原因和重试指引。
    parser.add_argument("--rejection-report", default=None)

    # dispatch-start 使用受控任务模式决定 reviewer/tester 触发。
    parser.add_argument(
        "--task-mode",
        choices=("read_only", "documentation", "implementation", "release"),
        default=None,
    )

    # dispatch-start 需要明确声明是否存在可执行测试面。
    parser.add_argument(
        "--has-test-surface",
        action=argparse.BooleanOptionalAction,
        default=None,
    )

    # dispatch-check 读取固定事件名称和 JSON 载荷。
    parser.add_argument("--event-type", default=None)

    # 事件载荷默认使用空对象，保证 dispatch-check 可解析。
    parser.add_argument("--event-payload", default="{}")

    # dispatch-record 绑定真实协作调用返回的 target 和结论。
    parser.add_argument("--event-id", default=None)

    # dispatch-repair 使用同一事件和原 worker target 生成 follow-up。
    parser.add_argument("--correction-fields", default="")

    # worker 标识缺省为空，由 receipt 绑定阶段补齐。
    parser.add_argument("--worker-id", default=None)

    # target 缺省为空，避免未绑定目标被误记为成功。
    parser.add_argument("--agent-target", default=None)

    # receipt 判定缺省为空，交由阶段白名单校验。
    parser.add_argument("--verdict", default=None)

    # 平台选择必须来自当前 catalog 的公开平台集合。
    parser.add_argument("--agent-platform", choices=tuple(load_catalog()["platforms"]), default=None)

    # 返回支持混合 positional 与 option 的解析器。
    return parser

# state-preview 缺少声明式 profile 时返回机器可读错误。
def _run_state_preview(
    namespace_namespace: argparse.Namespace,
    str_project: str,
) -> dict[str, object]:
    """执行声明式 worker 状态预览。

    参数：
        namespace_namespace：已解析的 CLI 参数。
        str_project：当前项目根路径。
    返回：状态预览机器载荷。
    """

    # profile 是状态预览的必需输入，缺失时不得猜测默认路径。
    if not namespace_namespace.state_profile:

        # 返回稳定错误而不触碰项目文件。
        return {"valid": False, "errors": ["--state-profile is required"], "write": False}

    # 委托状态模块生成 hash-bound preview。
    return preview_authorization_state(str_project, namespace_namespace.state_profile)

# state-apply 缺少 profile 或 preview 摘要时保持 fail-closed。
def _run_state_apply(
    namespace_namespace: argparse.Namespace,
    str_project: str,
) -> dict[str, object]:
    """应用 hash-bound worker 状态 profile。

    参数：
        namespace_namespace：已解析的 CLI 参数。
        str_project：当前项目根路径。
    返回：状态应用机器载荷。
    """

    # apply 的两个输入缺一不可，不能生成未经确认的授权。
    if not namespace_namespace.state_profile or not namespace_namespace.expected_preview_sha256:

        # 返回稳定错误并明确没有发生写入。
        return {
            "valid": False,
            "errors": ["--state-profile and --expected-preview-sha256 are required"],
            "write": False,
        }

    # 委托状态模块执行摘要校验和原子配置写入。
    return apply_authorization_state(
        str_project,
        namespace_namespace.state_profile,
        namespace_namespace.expected_preview_sha256,
    )

# 集中构造命令处理器，避免 main 混入长字典表达式。
def _build_command_handlers(
    namespace_namespace: argparse.Namespace,
    str_project: str,

    # 计划审查状态决定 validate-review 的输入分支。
    bool_plan_review: bool,
    bool_partial_plan_inputs: bool,
) -> dict[str, object]:
    """返回当前 worker CLI 的命令处理器映射。

    参数:
        namespace_namespace: 已解析的命令行参数集合。
        str_project: 当前工作文件夹路径。
        bool_plan_review: 是否使用计划执行审查路径。
        bool_partial_plan_inputs: 是否检测到半套计划输入。
    返回:
        命令名称到延迟执行函数的映射。
    """

    # 处理器延迟执行，保证 status 和 preview 保持只读。
    return {
        "status": lambda: worker_status(namespace_namespace.codex_home, str_project),  # status 只读取 profile、工具和根状态。
        "preview": lambda: preview_workers(namespace_namespace.codex_home, str_project),  # preview 只展示漂移与确认要求。
        "apply": lambda: apply_workers(  # apply 提交已经核对的 profile 更新。
            namespace_namespace.codex_home,
            str_project,
            confirm_tester_update=namespace_namespace.confirm_tester_update,
            confirm_reviewer_sha256=namespace_namespace.confirm_reviewer_sha256,
            confirm_gardener_update=namespace_namespace.confirm_gardener_update,
            confirm_profile_bundle_sha256=namespace_namespace.confirm_profile_bundle_sha256,
        ),
        "state-preview": lambda: _run_state_preview(namespace_namespace, str_project),  # 只读授权预览。
        "state-apply": lambda: _run_state_apply(namespace_namespace, str_project),  # hash-bound 授权应用。
        "verify": lambda: verify_workers(namespace_namespace.codex_home, str_project),  # verify 复核静态合同和动态握手。
        "validate-review": lambda: _dispatch_validate_review(  # validate-review 绑定计划与执行记录。
            namespace_namespace,
            bool_plan_review,
            bool_partial_plan_inputs,
            str_project,
        ),
        "review-session": lambda: reviewer_session_status(  # review-session 绑定当前 receipt 的 reviewer 决策。
            str_project,
            namespace_namespace.phase,
            namespace_namespace.plan_sha256,
            namespace_namespace.now_monotonic,
            namespace_namespace.agent_platform,
            namespace_namespace.review_interval,
            namespace_namespace.receipt_sha256,
        ),
        "dispatch-start": lambda: _run_dispatch_start(  # dispatch-start 生成实现启动决策。
            namespace_namespace,
            str_project,
        ),
        "dispatch-check": lambda: _run_dispatch_check(  # dispatch-check 检查事件和现有 session。
            namespace_namespace,
            str_project,
        ),
        "dispatch-record": lambda: _run_dispatch_record(  # dispatch-record 绑定 target 和 receipt。
            namespace_namespace,
            str_project,
        ),
        "dispatch-repair": lambda: _run_dispatch_repair(  # dispatch-repair 生成同 target 修复消息。
            namespace_namespace,
            str_project,
        ),
    }

# 执行 worker 生命周期命令并输出唯一机器可读结果。
def main() -> None:
    """执行 worker 子命令并输出 JSON。

    参数:
        无；参数来自当前进程命令行。
    返回:
        None；无效结果通过 SystemExit(1) 表达失败。
    异常:
        SystemExit(1)：status、apply 或 reviewer 审查无效时抛出。
    """

    # 构造解析器并允许 project 与 option 交错出现。
    namespace_namespace: argparse.Namespace = _build_parser().parse_intermixed_args()  # 命令行解析结果。

    # 命名 project 优先于兼容 positional。
    str_project = namespace_namespace.project_option or namespace_namespace.project  # 当前工作文件夹路径。

    # 计划执行审查只有在两个输入文件同时存在时才启用。
    bool_plan_inputs = bool(namespace_namespace.plan is not None and namespace_namespace.execution is not None)  # 计划审查输入是否齐全。

    # 记录当前命令是否为计划审查命令。
    bool_is_validate_review = namespace_namespace.command == "validate-review"  # 是否为计划审查命令。

    # review-session 需要一个稳定的批准计划摘要。
    if namespace_namespace.command == "review-session" and not namespace_namespace.plan_sha256:

        # 缺少批准计划摘要时拒绝生成不可绑定的 reviewer 会话。
        raise SystemExit("> ERR: [Python] --plan-sha256 is required for review-session")

    # 分别记录两个计划输入是否缺失。
    bool_plan_missing = namespace_namespace.plan is None  # 批准计划是否缺失。

    # 分别记录执行输入是否缺失。
    bool_execution_missing = namespace_namespace.execution is None  # 执行记录是否缺失。

    # validate-review 只提供一个计划文件时必须 fail-closed。
    bool_partial_plan_inputs = bool(bool_is_validate_review and bool_plan_missing != bool_execution_missing)  # 计划输入是否只提供一半。

    # 仅 validate-review 命令可以消费计划执行输入。
    bool_plan_review = bool(namespace_namespace.command == "validate-review" and bool_plan_inputs)  # 是否选择计划审查。

    # 按公开命令名称选择唯一处理函数。
    tuple_handler_inputs = (namespace_namespace, str_project, bool_plan_review, bool_partial_plan_inputs)  # 调用处理器所需的命令参数。

    # 由参数元组构造当前命令处理器映射。
    dict_handlers = _build_command_handlers(*tuple_handler_inputs)  # 当前命令处理映射。

    # 统一执行选定命令并输出结构化 JSON。
    dict_result = dict_handlers[namespace_namespace.command]()  # 当前命令结果。

    # dispatch 命令拥有独立的四档退出码和单 JSON 协议。
    if namespace_namespace.command.startswith("dispatch-"):

        # 内部输入标记只参与退出码计算，不泄漏到公开 schema。
        bool_input_error = bool(dict_result.pop("_input_error", False))  # dispatch 输入错误标记。

        # 机器可读结果只输出一个 JSON 对象。
        sys.stdout.write(json.dumps(dict_result, ensure_ascii=False, indent=2) + "\n")

        # 按批准方案返回 0/1/2/3。
        raise SystemExit(dispatch_exit_code(dict_result, bool_input_error))

    # 机器可读结果统一使用 UTF-8 JSON 输出。
    sys.stdout.write(json.dumps(dict_result, ensure_ascii=False, indent=2) + "\n")

    # 兼容 status/preview 的 valid 与 validate-review 的 ok 字段。
    bool_valid = dict_result.get("valid", dict_result.get("ok", False))  # CLI 结果有效性。

    # status、preview 和 verify 是只读诊断，即使未安装也返回 JSON 供调用方决策。
    set_read_only_commands = {  # 只读命令集合
        "status",  # 状态查询
        "preview",  # 预览查询
        "state-preview",  # 授权状态预览
        "verify",  # 验证查询
        "review-session",  # reviewer 会话查询
    }

    # 只读命令不得因诊断结果无效而触发生命周期失败。
    bool_read_only_command = namespace_namespace.command in set_read_only_commands  # 当前命令是否只读

    # apply 或 validate-review 的无效结果必须阻止调用链继续。
    if not bool_valid and not bool_read_only_command:

        # 无效结果必须阻止后续生命周期动作。
        raise SystemExit(1)

# 脚本主入口只在直接执行时触发 CLI。
if __name__ == "__main__":

    # 运行已解析的生命周期命令。
    main()
