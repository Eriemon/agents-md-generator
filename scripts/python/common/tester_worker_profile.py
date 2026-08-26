"""管理唯一隔离测试智能体的 Codex TOML 配置。"""

# 延迟注解求值保持治理脚本在 Python 3.10 下可直接执行。
from __future__ import annotations

# 配置生命周期需要可调用类型、时间戳、环境变量、路径和文件复制。
from collections.abc import Callable
from datetime import datetime, timezone
import importlib
import importlib.util

# 环境变量和路径解析支撑角色配置的隔离定位。
import os
from pathlib import Path
import shutil
import sys

# 动态加载器和模块类型支撑旧副本兼容路径。
from importlib.machinery import ModuleSpec
from types import ModuleType

# 共享模块按需加载，避免导入角色配置模块时修改 sys.path。
def _load_local_module(file_name: str, module_name: str) -> ModuleType:
    """从当前 common 目录按文件名加载一个兼容模块。

    参数：file_name 为 common 目录中的源码文件名，module_name 为内部模块名。
    返回：已执行的模块对象。
    异常：ImportError：源码缺失或无法建立模块加载器。
    """

    # 角色模块与兼容依赖始终位于同一 common 目录。
    path_module: Path = Path(__file__).with_name(file_name)  # 兼容模块源码路径

    # 文件加载器不改变解释器全局导入路径。
    module_spec_local: ModuleSpec = importlib.util.spec_from_file_location(  # 本地模块加载规格
        module_name,  # 缓存模块的内部名称
        path_module,  # 当前兼容源码路径
    )

    # 不完整加载规格不能安全执行配置依赖。
    if module_spec_local is None or module_spec_local.loader is None:

        # 统一错误前缀便于上层 CLI 识别依赖缺失。
        raise ImportError(f"> ERR: [Python] cannot load {file_name}")

    # 动态模块对象先保留独立命名空间，避免覆盖调用方模块。
    module_type_local: ModuleType = importlib.util.module_from_spec(module_spec_local)  # 兼容模块对象

    # dataclass 类型解析要求执行期间能在 sys.modules 找到模块。
    module_type_previous: ModuleType | None = sys.modules.get(module_name)  # 原同名模块快照

    # 临时注册当前模块，让执行期的类型解析读取正确命名空间。
    sys.modules[module_name] = module_type_local  # 执行期模块注册

    # 无论执行成功与否都恢复调用方的模块表。
    try:

        # 执行已验证的本地兼容源码。
        module_spec_local.loader.exec_module(module_type_local)

    # 执行成功或异常都必须恢复模块表。
    finally:

        # 结束执行后恢复动态导入前的模块状态。
        if module_type_previous is None:

            # 没有旧模块时移除临时注册，避免污染后续导入。
            sys.modules.pop(module_name, None)

        # 原模块存在时恢复原对象。
        else:

            # 已有旧模块时恢复原对象，保持调用方导入语义。
            sys.modules[module_name] = module_type_previous  # 原模块恢复

    # 返回对象供调用方读取明确的函数或模块属性。
    return module_type_local

# 读取 worker runtime 配置，默认 profile 不内置模型或 reasoning 值。
module_type_runtime: ModuleType = _load_local_module("worker_runtime.py", "worker_runtime")  # 角色共用的 runtime 模块对象。

# tester profile 复用协议声明的模型，不在角色代码中硬编码。
WORKER_MODEL: str = module_type_runtime.WORKER_MODEL  # tester profile 采用的模型名称。

# tester profile 复用协议声明的 reasoning，保持隔离配置一致。
WORKER_REASONING: str = module_type_runtime.WORKER_REASONING  # tester profile 采用的 reasoning 强度。

# 解析用户根，优先使用平台目录模块并保留旧副本回退。
def _resolve_agent_home(path_skill_root: Path, str_raw_home: str | None) -> Path:
    """解析角色配置使用的 Codex 用户根目录。

    参数：path_skill_root 为当前 skill 根，str_raw_home 为可选用户根覆盖。
    返回：规范化的 Codex 用户根路径。
    """

    # 新版平台模块提供完整的用户根解析合同。
    try:

        # 直接按文件加载平台模块，不依赖外部 sys.path 状态。
        module_type_agent_platform: ModuleType = _load_local_module(  # 平台模块对象
            "agent_platform.py", "agents_md_agent_platform"  # 平台模块文件和内部名称
        )

        # 平台解析器参数化支持 agent 选择和用户根覆盖。
        func_resolve_agent_home: Callable[[Path, str | None], Path] = (  # 用户根解析函数
            module_type_agent_platform.resolve_agent_home  # 平台模块的统一解析入口
        )

    # 裁剪旧副本缺少平台模块时回退共享根解析器。
    except (AttributeError, ImportError):

        # 共享兼容解析器保留旧安装副本的环境驱动行为。
        module_type_agents_common: ModuleType = _load_local_module(  # 共享兼容模块对象
            "agents_common.py", "agents_md_agents_common"  # 兼容模块文件和内部名称
        )

        # 旧版函数只接收原始主目录文本，不能传入技能根路径。
        func_resolve_agent_home = module_type_agents_common.agent_home_root  # 旧版用户根解析函数

        # 旧版解析器按环境变量和原始主目录文本完成回退。
        return func_resolve_agent_home(str_raw_home)

    # 返回统一的绝对用户根路径。
    return func_resolve_agent_home(path_skill_root, str_raw_home)

# 延迟选择 Python 内置或本地兼容 TOML 解析器。
def _load_toml_module() -> ModuleType:
    """加载当前运行环境可用的 TOML 解析模块。

    参数：无。
    返回：提供 loads 和 TOMLDecodeError 的 TOML 模块对象。
    异常：ImportError：标准库和本地兼容解析器均不可用。
    """

    # Python 3.11 及以上优先使用标准库实现。
    try:

        # 动态导入避免在模块加载阶段触发版本分支。
        module_type_tomllib: ModuleType = importlib.import_module("tomllib")  # 标准库 TOML 模块

    # Python 3.10 使用技能随附的兼容实现。
    except ModuleNotFoundError:

        # 兼容实现与当前角色文件保持同一 common 目录。
        module_type_tomllib = _load_local_module("toml_compat.py", "toml_compat")  # 本地 TOML 兼容模块

    # 返回选定的 TOML 解析器模块。
    return module_type_tomllib

# Codex 角色配置只保留当前 CLI 实际接受的字段。
DEFAULT_TESTER_WORKER_TOML = (  # 默认唯一测试智能体配置
    f'''# Canonical isolated test-worker profile managed by agents-md-generator.
name = "tester_worker"
description = "唯一的记忆隔离测试智能体；负责 tests/** 的测试树访问、测试编写与验证。"
model = "{WORKER_MODEL}"
model_reasoning_effort = "{WORKER_REASONING}"
developer_instructions = """
你是唯一的 TESTER。fork_turns=none，使用隔离记忆上下文；不得把 tests/** 委托给其他智能体。
收到任务后必须先校验 schema_version、worker_id、task_kind、phase、project_root、
allowed_read_roots、allowed_write_roots、forbidden_actions 和 expected_output；
缺少字段或 task_kind 不是 test 时，在任何工具调用前返回
SCOPE_REJECTED、no_action_taken=true。
只有你可以创建、修改、删除或运行目标工作文件夹中的 tests/**；gardener_worker 仅可列出和读取 tests/** 作为设计证据；实现智能体和 reviewer_worker 仍不得读取 tests/**。
先写并运行 RED 测试，再将失败症状、计数、建议反馈给实现智能体；产品修复后由同一 tester_worker 复跑 GREEN 与最终回归。
The same tester_worker performs RED, GREEN, and final regression, then reports the tests tree hash.
失败、RED、BLOCKED 或 SCOPE_REJECTED 回传绝不能只写 failed、失败计数或一句“测试失败”；
必须返回 failure_report 对象，至少包含 failure_stage、failure_kind、first_error、failure_summary、
failure_count、failure_tests、expected_actual、root_cause_class、minimal_fix、evidence、residual_jobs 和
modification_status。failure_tests 的每一项必须说明 test_id、expected、actual、observed 和 source；
evidence 必须包含命令、作业、收据、路径、哈希或退出码中的至少一个可追溯锚点；residual_jobs 和
modification_status 不得省略。
主 Agent 只有在收到完整 failure_report 后才可以记录失败 receipt；缺字段、空泛文本、期望/实际缺失或没有证据锚点时，必须返回可修正的字段级错误。
Routine test-hash confirmation is prohibited.
Agent autonomously confirms when the canonical tester result agrees with the \
authoritative current tests tree or receipt.
A report-only hash mismatch is corrected to the authoritative value.
Conflicting or insufficient provenance stops for user review without an autonomous rerun.
New test files use functional or behavioral semantic names; filename stems must not \
contain digits, including v1, v2, 1, 2, part1, and part2.
完成前报告 tests/** 最终树哈希；不等待常规用户确认。
遵循目标工作文件夹最近的 AGENTS.md。
修改 tests/** 下的 Python、bat/cmd、shell/bash、PowerShell 或 Tcl 前，先思考并同时加载 readable-python-generator 与
readable-script-generator；两个门禁必须在编辑过程中通过；Python 最终由 readable-python-generator 负责，
脚本最终由 readable-script-generator 负责。
配置握手请求必须返回：TESTER_WORKER_READY。
"""
'''
)  # TOML 文本结束

# 生成的 AGENTS 文本使用同一份稳定授权句，避免重复确认语义漂移。
SINGLE_TASK_AUTHORIZATION_RECEIPT = (  # 单次任务授权收据文本
    "A single-task authorization receipt is confirmed once across the skill, "
    "AGENTS.md, and CLI; it becomes invalid only when the target, scope, or risk changes."
)

# 受管配置必须包含这些不变量，缺一项就不能作为唯一测试智能体。
REQUIRED_INSTRUCTION_FRAGMENTS = (  # tester_worker 指令必需片段
    "fork_turns=none",  # 隔离上下文标记
    "tests/**",  # 测试树所有权标记
    "task_kind",  # envelope 任务类型标记
    "SCOPE_REJECTED",  # 越权拒绝结论
    "no_action_taken",  # 拒绝前无副作用标记
    "gardener_worker 仅可列出和读取 tests/**",  # gardener 只读例外
    "实现智能体和 reviewer_worker 仍不得读取 tests/**",  # 实现与 reviewer 的测试树边界
    "RED",  # 红灯阶段标记
    "same tester_worker",  # 同一 worker 标记
    "GREEN",  # 绿灯阶段标记
    "final regression",  # 最终回归标记
    "failure_report",  # 失败报告对象标记
    "failure_tests",  # 失败明细标记
    "expected_actual",  # 期望/实际标记
    "root_cause_class",  # 根因分类标记
    "minimal_fix",  # 最小修复标记
    "residual_jobs",  # 残留任务标记
    "modification_status",  # 变更状态标记
    "字段级错误",  # 不完整报告的修正反馈标记
    "tests/** 最终树哈希",  # 测试树哈希标记
    "Routine test-hash confirmation is prohibited.",  # 哈希无需常规确认
    (
        "Agent autonomously confirms when the canonical tester result agrees with the "
        "authoritative current tests tree or receipt."
    ),  # 权威一致时自主确认
    "A report-only hash mismatch is corrected to the authoritative value.",  # 报告值错误时纠正
    "Conflicting or insufficient provenance stops for user review without an autonomous rerun.",  # 证据冲突时停线
    (
        "New test files use functional or behavioral semantic names; filename stems "
        "must not contain digits, including v1, v2, 1, 2, part1, and part2."
    ),  # 新测试命名合同
    "readable-python-generator",  # Python 门禁标记
    "readable-script-generator",  # 脚本门禁标记
    "TESTER_WORKER_READY",  # 动态握手标记
)

# 派发 envelope 的 expected_output 必须提前声明完整失败回传字段。
TESTER_FAILURE_OUTPUT_FRAGMENTS = (  # tester 失败输出提示片段
    "failure_report",  # 结构化失败报告对象
    "failure_stage",  # 失败阶段
    "failure_kind",  # 失败类别
    "first_error",  # 首个错误
    "failure_summary",  # 失败影响摘要
    "failure_count",  # 失败条目数量
    "failure_tests",  # 完整失败明细
    "expected_actual",  # 期望和实际
    "root_cause_class",  # 根因分类
    "minimal_fix",  # 最小修复
    "evidence",  # 可追溯证据
    "residual_jobs",  # 残留任务
    "modification_status",  # 变更状态
)  # tester 失败输出合同

# 校验派发提示是否包含 tester 失败回传的完整字段清单。
def _validate_tester_failure_output(value_envelope: dict[str, object]) -> list[str]:
    """返回 expected_output 中缺失的 tester 失败字段。

    参数:
        value_envelope: 已确认是对象的 tester 任务 envelope。
    返回:
        expected_output 缺失字段列表；空列表表示提示完整。
    """

    # 读取任务提示文本，拒绝非字符串的隐式协议。
    str_expected_output = value_envelope.get("expected_output")  # tester 期望输出协议文本

    # 收集缺失提示片段，供主 Agent在派发前修正 envelope。
    list_missing_output_fragments = [  # dispatch 前的字段提示诊断
        str_fragment  # 当前缺失的失败报告字段
        for str_fragment in TESTER_FAILURE_OUTPUT_FRAGMENTS  # 遍历固定失败字段
        if not isinstance(str_expected_output, str) or str_fragment not in str_expected_output  # 检查提示完整性
    ]

    # 返回缺失字段，空列表表示任务提示已经完整。
    return list_missing_output_fragments

# 对 tester envelope 的值域执行 fail-closed 校验，阻止合法字段名承载越权内容。
def _validate_tester_envelope_values(value_envelope: dict[str, object]) -> list[str]:
    """校验 tester envelope 的身份、阶段和读写边界。

    参数：
        value_envelope: 已经确认是对象且包含必需字段的 tester envelope。
    返回：
        具体字段错误列表；空列表表示值域符合当前 tester 合同。
    """

    # 收集值域错误，供拒绝回执一次性反馈给主 Agent。
    list_value_errors: list[str] = []  # 当前 envelope 的字段级错误

    # schema 版本必须与当前 dispatcher 合同一致。
    if value_envelope.get("schema_version") != 1:

        # 版本漂移会让后续字段解释失去共同语义。
        list_value_errors.append("schema_version must equal the configured tester envelope schema")

    # worker 身份必须锁定 canonical tester。
    if value_envelope.get("worker_id") != "tester_worker":

        # 其他角色的 envelope 不得进入 tester 的测试面。
        list_value_errors.append("worker_id must identify tester_worker")

    # tester 只接受配置声明的三个测试生命周期阶段。
    if value_envelope.get("phase") not in {"RED", "GREEN", "FINAL"}:

        # 非 tester 阶段不能获得 tests/** 写入权限。
        list_value_errors.append("phase must be RED, GREEN, or FINAL")

    # 项目根必须是非空字符串，后续路径边界依赖该值。
    if not isinstance(value_envelope.get("project_root"), str) or not str(
        value_envelope.get("project_root")
    ).strip():

        # 空根路径无法验证测试树所属项目。
        list_value_errors.append("project_root must be a non-empty path")

    # tester 的读取范围必须覆盖 Skill 源码和 tests 根。
    value_read_roots = value_envelope.get("allowed_read_roots")  # tester 读取根集合

    # 空列表或非字符串列表不能证明 tester 的读取边界。
    if value_read_roots != ["skills/agents-md-generator", "tests"]:

        # 使用完整声明阻止遗漏源代码或测试树权限。
        list_value_errors.append(
            "allowed_read_roots must match the configured tester source and tests roots"
        )

    # tester 只允许写入 tests 根，不接受其他目标路径。
    if value_envelope.get("allowed_write_roots") != ["tests"]:

        # 写入边界漂移会把测试权限扩大到产品源码。
        list_value_errors.append("allowed_write_roots must contain only the tests root")

    # 禁止动作必须完整覆盖产品、发布、安装和委托边界。
    value_forbidden_actions = value_envelope.get("forbidden_actions")  # tester 禁止动作集合

    # 缺少任一禁止动作都不能让 tester 进入执行阶段。
    if value_forbidden_actions != [
        "modify_product_source",
        "release",
        "install",
        "delegate",
    ]:

        # 保持禁止动作顺序稳定，便于 receipt 和配置 hash 对账。
        list_value_errors.append(
            "forbidden_actions must preserve the configured tester restrictions"
        )

    # 返回全部字段级错误，避免主 Agent反复试错同一 envelope。
    return list_value_errors

# 统一构造 tester scope rejection，向主 Agent返回原因和同一 target 的修复提示。
def _tester_rejection_report(
    str_reason_code: str,
    str_summary: str,
    list_violations: list[dict[str, object]],
) -> dict[str, object]:
    """构造无副作用的 tester rejection report。

    参数：
        str_reason_code: 配置定义的拒绝原因标识。
        str_summary: 当前 envelope 未被接受的具体影响。
        list_violations: 字段级期望、实际和修正列表。
    返回：可持久化并可驱动 follow-up 的 rejection report。
    """

    # 为每项拒绝保留期望、实际、观察和定位，确保主 Agent可直接修复。
    list_failure_tests: list[dict[str, object]] = []  # 每条拒绝的可定位失败明细

    # 逐项复制字段诊断，避免压缩成不可审计的推导式。
    for dict_violation in list_violations:

        # 组装一条可复现的 failure_tests 明细。
        dict_failure_test = {  # 当前字段的拒绝诊断
            "test_id": "envelope." + str(dict_violation.get("field", "unknown")),  # 字段诊断标识
            "expected": str(dict_violation.get("expected", "configured value")),  # 字段期望值
            "actual": str(dict_violation.get("actual", "<missing>")),  # 实际收到值
            "observed": str(dict_violation.get("reason", "envelope value rejected")),  # 观察到的原因
            "source": str(Path(__file__).resolve()),  # 诊断源码定位
        }

        # 将明细按输入顺序保留，便于主 Agent逐项修复。
        list_failure_tests.append(dict_failure_test)

    # 首错取第一项具体诊断，避免只返回聚合的 scope rejected。
    dict_first_violation = list_violations[0] if list_violations else {}  # 首项拒绝诊断

    # 提取第一项拒绝的具体原因，供 failure_report 首错字段使用。
    str_first_error = str(dict_first_violation.get("reason", "tester envelope validation failed"))  # 首个可定位的拒绝原因

    # 统一报告结构，拒绝回执同时满足 failure_report 的可执行字段合同。
    return {
        "failure_stage": "envelope_validation",
        "failure_kind": str_reason_code,
        "first_error": str_first_error,
        "failure_summary": str_summary,
        "failure_count": len(list_failure_tests),
        "failure_tests": list_failure_tests,
        "expected_actual": {
            "expected": "an envelope matching the configured tester contract",
            "actual": str_summary,
        },
        "root_cause_class": "worker_envelope_contract_violation",
        "minimal_fix": (
            "Correct every reported envelope field and resend the complete envelope "
            "to the same tester target."
        ),
        "residual_jobs": [],
        "rejection_stage": "envelope_validation",
        "reason_code": str_reason_code,
        "summary": str_summary,
        "violations": list_violations,
        "allowed_request": {
            "task_kind": "test",
            "phases": ["RED", "GREEN", "FINAL"],
            "read_roots": ["{skill_root}", "{tests_root}"],
            "write_roots": ["{tests_root}"],
            "forbidden_actions": [
                "modify_product_source",
                "release",
                "install",
                "delegate",
            ],
        },
        "retry_guidance": {
            "reuse_target": True,
            "preserve_fields": ["event_id", "worker_id", "plan_sha256", "task_mode"],
            "replace_fields": ["invalid_envelope_fields"],
            "next_operation": "followup_same_tester_target",
        },
        "evidence": {
            "source_paths": [str(Path(__file__).resolve())],
        },
        "modification_status": {
            "product_source_modified": False,
            "tests_modified": False,
            "git_modified": False,
            "tools_called": False,
            "files_read": False,
            "files_written": False,
            "tests_run": False,
        },
    }

# 在任何工具调用前校验 tester envelope，保证越权任务无副作用拒绝。
def validate_tester_worker_envelope(value_envelope: object) -> dict[str, object]:
    """校验 tester 任务 envelope 并返回接受或拒绝回执。

    参数：value_envelope 为主 Agent 传入的 envelope 对象。
    返回：严格的 accepted 或 SCOPE_REJECTED 回执。
    """

    # 缺少对象形状时不能推断任务类型。
    if not isinstance(value_envelope, dict):

        # 非对象在任何路径读取前直接拒绝。
        return {
            "valid": False,
            "worker": "tester_worker",
            "worker_id": "tester_worker",
            "verdict": "SCOPE_REJECTED",
            "reason": "task envelope must be an object",
            "received_task_kind": None,
            "allowed_task_kinds": ["test"],
            "no_action_taken": True,
            "rejection_report": _tester_rejection_report(
                "envelope_not_object",
                "The tester received a non-object task envelope and took no action.",
                [{
                    "field": "envelope",
                    "expected": "object",
                    "actual": type(value_envelope).__name__,
                    "reason": "root type is invalid",
                    "correction": "send the complete structured envelope object",
                }],
            ),
        }

    # 固定字段缺失时拒绝自动推断。
    tuple_required_fields = (
        "schema_version",  # schema 版本字段
        "worker_id",  # worker 身份字段
        "task_kind",  # 任务类型字段
        "phase",  # 生命周期阶段字段
        "project_root",  # 项目根字段
        "allowed_read_roots",  # 允许读取根字段
        "allowed_write_roots",  # 允许写入根字段
        "forbidden_actions",  # 禁止动作字段
        "expected_output",  # 输出协议字段
    )  # tester envelope 必需字段。

    # 收集缺失字段以便主 Agent修正 envelope。
    list_missing_fields = [
        str_field  # 缺失字段名称
        for str_field in tuple_required_fields  # 遍历固定字段
        if str_field not in value_envelope  # 保留未提供字段
    ]  # 缺失字段列表。

    # 任务类型必须严格限制为 test。
    str_task_kind = value_envelope.get("task_kind")  # 收到的任务类型。

    # 缺少字段或任务类型不符时拒绝任务。
    if list_missing_fields or str_task_kind != "test":

        # 为每个缺失或越界字段生成准确诊断，禁止把错误归因到 task_kind。
        list_scope_violations: list[dict[str, object]] = []  # 缺失或越界字段的诊断列表

        # 缺失字段逐项记录真实的缺失状态。
        for str_field in list_missing_fields:

            # 追加一项缺失字段诊断，保留修复动作。
            list_scope_violations.append(
                {
                    "field": str_field,
                    "expected": "configured tester envelope field",
                    "actual": "<missing>",
                    "reason": "required envelope field is missing",
                    "correction": "include the field from dispatch-check",
                }
            )

        # 非 test 任务类型单独报告收到的实际值。
        if str_task_kind != "test" and "task_kind" not in list_missing_fields:

            # 追加 task_kind 的实际收到值，避免错误归因到缺失字段。
            list_scope_violations.append(
                {
                    "field": "task_kind",
                    "expected": "test",
                    "actual": str_task_kind,
                    "reason": "task kind is outside the tester contract",
                    "correction": "send a test envelope to the tester target",
                }
            )

        # 越权任务在任何路径/工具处理前返回拒绝。
        return {
            "valid": False,
            "worker": "tester_worker",
            "worker_id": "tester_worker",
            "verdict": "SCOPE_REJECTED",
            "reason": (
                "missing envelope fields"
                if list_missing_fields
                else "task kind is outside the canonical tester contract"
            ),
            "received_task_kind": str_task_kind,
            "allowed_task_kinds": ["test"],
            "missing_fields": list_missing_fields,
            "no_action_taken": True,
            "rejection_report": _tester_rejection_report(
                "missing_or_wrong_task_kind",
                "The tester envelope is missing required fields or uses a non-test task kind.",
                list_scope_violations,
            ),
        }

    # 字段存在但值越界时仍必须在任何工具调用前拒绝。
    list_value_errors = _validate_tester_envelope_values(value_envelope)  # tester envelope 值域错误

    # 结构化返回具体值域错误，帮助主 Agent修正而不是猜测边界。
    if list_value_errors:

        # 保持拒绝无副作用，并一次性返回全部值校验原因。
        return {
            "valid": False,
            "worker": "tester_worker",
            "worker_id": "tester_worker",
            "verdict": "SCOPE_REJECTED",
            "reason": "tester envelope values are outside the canonical contract",
            "value_errors": list_value_errors,
            "no_action_taken": True,
            "rejection_report": _tester_rejection_report(
                "invalid_envelope_values",
                "One or more tester envelope values are outside the configured contract.",
                [{
                    "field": "envelope",
                    "expected": "configured tester values",
                    "actual": list_value_errors,
                    "reason": "value validation failed",
                    "correction": "replace invalid fields and resend to the same target",
                }],
            ),
        }

    # tester envelope 必须把失败回传字段写进期望输出，不能只写模糊的 receipt。
    list_missing_output_fragments = _validate_tester_failure_output(value_envelope)  # tester 失败提示缺失集合

    # 任务 envelope 不完整时在任何工具调用前拒绝。
    if list_missing_output_fragments:

        # 将缺失片段返回给主 Agent，避免 tester 收到不完整任务合同。
        return {
            "valid": False,
            "worker": "tester_worker",
            "worker_id": "tester_worker",
            "verdict": "SCOPE_REJECTED",
            "reason": "expected_output lacks detailed tester failure contract",
            "missing_output_fragments": list_missing_output_fragments,
            "no_action_taken": True,
            "rejection_report": _tester_rejection_report(
                "missing_failure_contract",
                "The tester envelope does not describe the detailed failure receipt required for this task.",
                [{
                    "field": "expected_output",
                    "expected": "all configured failure fragments",
                    "actual": list_missing_output_fragments,
                    "reason": "required failure contract fragments are absent",
                    "correction": "regenerate the envelope from dispatch-check",
                }],
            ),
        }

    # 合法 test envelope 才能进入测试阶段。
    return {
        "valid": True,
        "worker": "tester_worker",
        "worker_id": "tester_worker",
        "verdict": "ACCEPTED",
        "task_kind": "test",
        "no_action_taken": False,
    }

# 唯一 tester_worker 路径解析函数公开稳定参数和返回约定。
def tester_worker_path(codex_home: str | Path | None = None) -> Path:
    """解析唯一 tester_worker.toml 的规范路径。

    参数：codex_home 为可选 Codex 主目录覆盖值。
    返回：`agents/tester_worker.toml` 的规范路径。
    """

    # 显式参数优先于环境变量，保证隔离运行可复现。
    str_raw_home: str | None = (  # 当前请求的用户根覆盖
        str(codex_home)  # 显式参数优先
        if codex_home is not None  # 参数存在时不读取环境
        else os.environ.get("AGENT_HOME") or os.environ.get("CODEX_HOME")  # 环境变量回退
    )

    # 通过延迟平台解析器获得稳定的 Codex 用户根。
    path_agent_home: Path = _resolve_agent_home(  # 规范化的 Codex 用户根
        Path(__file__).resolve().parents[3],  # 当前 skill 根目录
        str_raw_home,  # 用户根覆盖文本
    )

    # 配置文件固定位于 Codex agents 角色目录。
    return path_agent_home / "agents" / "tester_worker.toml"

# 配置字段检查器只返回缺失或不匹配的合同错误。
def _validation_errors(dict_config: object) -> list[str]:
    """返回配置合同中缺失或不匹配的字段。

    参数：dict_config 为 tomllib 解析后的 TOML 根对象。
    返回：按稳定顺序排列的合同错误文本。
    """

    # 非映射 TOML 根不能被当作 Codex 角色配置。
    if not isinstance(dict_config, dict):

        # 以单项错误保持调用方的结构化诊断稳定。
        return ["TOML root must be a table"]

    # 基础字段和值必须与唯一 worker 的公开身份一致。
    list_errors: list[str] = []  # 配置合同错误集合

    # name 字段锁定唯一角色名称。
    if dict_config.get("name") != "tester_worker":

        # 错误文本说明角色身份不匹配。
        list_errors.append("name must be tester_worker")

    # model 字段锁定用户确认的默认模型。
    if dict_config.get("model") != WORKER_MODEL:

        # 错误文本说明模型选择不匹配。
        list_errors.append(f"model must be {WORKER_MODEL}")

    # reasoning 字段锁定用户确认的最大推理强度。
    if dict_config.get("model_reasoning_effort") != WORKER_REASONING:

        # 错误文本说明推理强度不匹配。
        list_errors.append(f"model_reasoning_effort must be {WORKER_REASONING}")

    # 指令字段承载所有不可由 TOML 顶层表达的隔离约束。
    str_instructions = str(dict_config.get("developer_instructions", ""))  # 规范化后的角色指令文本

    # 缺失指令时先报告空字段，不重复追加片段错误。
    if not str_instructions.strip():

        # 空指令不能安全承载 tests/** 隔离合同。
        list_errors.append("developer_instructions must not be empty")

    # 逐项检查隔离、双技能和握手不变量。
    for str_fragment in REQUIRED_INSTRUCTION_FRAGMENTS:

        # 缺失任一片段都阻止其成为唯一 worker。
        if str_fragment not in str_instructions:

            # 错误文本保留缺失片段，便于修复漂移配置。
            list_errors.append(
                f"developer_instructions missing: {str_fragment}"
            )

    # 调用方需要稳定的错误序列以便报告和验证。
    return list_errors

# TOML 文本解析器同时执行语法和角色合同验证。
def validate_tester_worker_text(str_text: str) -> dict[str, object]:
    """解析并验证 tester_worker TOML 文本。

    参数：str_text 为待解析的 UTF-8 TOML 文本。
    返回：包含 valid、errors 和 config 字段的结构化验证结果。
    """

    # 解析器按调用时环境选择，避免模块导入阶段修改全局导入状态。
    module_type_tomllib: ModuleType = _load_toml_module()  # 当前 TOML 解析器

    # 语法错误和合同错误都转换为机器可读结果，不吞掉具体原因。
    try:

        # TOML 标准库解析结果供后续字段合同复用。
        dict_config = module_type_tomllib.loads(str_text)  # TOML 根配置映射

    # TOML 解码异常进入结构化错误分支。
    except module_type_tomllib.TOMLDecodeError as exc:

        # 语法错误直接返回失败结果，不继续访问不完整配置。
        return {
            "valid": False,
            "errors": [f"invalid TOML: {exc}"],
            "config": {},
        }

    # 只有语法和所有业务不变量都满足才返回 valid。
    list_errors = _validation_errors(dict_config)  # 角色合同错误

    # 解析成功结果进入合同字段检查。
    return {
        "valid": not list_errors,
        "errors": list_errors,
        "config": dict_config,
    }

# 旧配置备份函数保留同目录和可恢复的原文副本。
def _backup_existing(path_config: Path) -> Path:
    """把已有配置复制到同目录唯一备份文件。

    参数：path_config 为已确认存在的 TOML 文件。
    返回：新建的备份文件路径。
    """

    # UTC 微秒和进程号共同避免同一秒内的备份名冲突。
    str_stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")  # 备份时间戳

    # 备份名保留原文件名并使用可检索的 bak 前缀。
    path_backup = path_config.with_name(  # 备份文件路径
        f"{path_config.name}.bak-{str_stamp}-{os.getpid()}"  # 备份文件名
    )  # 组合时间戳和进程号后的备份路径

    # 复制而非移动，确保刷新失败时旧配置仍可恢复。
    shutil.copy2(path_config, path_backup)

    # 返回备份路径供报告和恢复流程复用。
    return path_backup

# 原子写入函数避免半写入的角色配置被读取。
def _write_atomic(path_config: Path, str_text: str) -> None:
    """以同目录临时文件和替换完成 UTF-8 原子写入。

    参数：path_config 为最终 TOML 文件；str_text 为完整配置文本。
    返回：无；失败时保留原文件并传播异常。
    """

    # 同目录临时文件确保 os.replace 不跨文件系统。
    path_temp = path_config.with_name(  # 临时配置文件路径
        f"{path_config.name}.tmp-{os.getpid()}"  # 临时文件名
    )  # 与目标同目录的临时路径

    # 写入、替换和异常清理由一个可恢复事务边界包围。
    try:

        # UTF-8 和 LF 固定配置文件的跨平台字节表示。
        path_temp.write_text(str_text, encoding="utf-8", newline="\n")

        # 原子替换使读者只能看到旧文件或完整新文件。
        os.replace(path_temp, path_config)

    # finally 分支只负责清理本次事务残留。
    finally:

        # 替换异常时清理临时文件，不触碰既有配置或备份。
        if path_temp.exists():

            # 临时文件没有恢复价值，安全地移除本次残留。
            path_temp.unlink()

# 唯一配置入口负责检查、显示、备份、写入和最终读回验证。
def ensure_tester_worker_profile(
    codex_home: str | Path | None = None,
    *,
    write: bool = False,
    confirm_update: bool = False,
) -> dict[str, object]:
    """检查或创建唯一 tester_worker 配置并验证最终读回内容。

    参数：codex_home 为可选 Codex 主目录；write 控制是否落盘；confirm_update 保留调用方确认字段。
    返回：包含原文、备份、最终文本和 TOML 验证结果的结构化报告。
    """

    # 路径解析集中在一个入口，便于真实主目录和隔离测试复用。
    path_config = tester_worker_path(codex_home)  # 唯一配置目标路径

    # 初始存在性和文件类型决定后续读取分支。
    bool_exists = path_config.exists()  # 目标是否存在

    # 目录或其他非文件目标不应被误当作 TOML 文本。
    str_existing = (  # 旧配置完整原文
        path_config.read_text(encoding="utf-8") if bool_exists and path_config.is_file() else ""  # 文件原文
    )  # 旧配置读取结果

    # 先读取和验证已有内容，报告中保留完整原文供确认或审计。
    dict_existing = (  # 旧配置验证结果
        validate_tester_worker_text(str_existing)  # 旧配置验证
        if str_existing  # 仅有原文时执行解析
        else {"valid": False, "errors": ["configuration is missing"], "config": {}}  # 缺失结果
    )  # 旧配置合同结果

    # 缺失、语义漂移或格式差异都需要刷新默认合同。
    bool_needs_refresh = (not bool_exists) or (  # 是否需要备份并刷新
        not dict_existing["valid"] or str_existing != DEFAULT_TESTER_WORKER_TOML  # 漂移判断
    )  # 漂移配置判定

    # 结果保留授权收据和旧内容，调用方可以先展示再决定后续动作。
    dict_result: dict[str, object] = {  # 配置生命周期报告
        "enabled": True,  # Codex-native 策略启用状态，不代表配置文件已安装。
        "path": str(path_config),  # 唯一配置路径
        "exists_before": bool_exists,  # 写入前存在性
        "existing_content": str_existing,  # 写入前完整原文
        "existing_validation": dict_existing,  # 写入前验证结果
        "updated": False,  # 初始更新状态
        "backup_path": "",  # 初始备份路径
        "requires_user_confirmation": False,  # 当前任务收据已覆盖
        "authorization_receipt": SINGLE_TASK_AUTHORIZATION_RECEIPT,  # 单次授权收据
        "confirm_update": confirm_update,  # 调用方确认字段
    }

    # 只读检查不创建目录或改动已有文件。
    if not write:

        # 只读状态区分稳定配置和待刷新配置。
        dict_result["status"] = "valid" if not bool_needs_refresh else "needs-refresh"  # 只读状态

        # 返回只读状态而不触碰配置文件。
        return dict_result

    # 目录创建属于首次配置的正常工作流，且不触碰项目文件。
    path_config.parent.mkdir(parents=True, exist_ok=True)

    # 已有内容先展示给调用方，确认是否需要刷新后才进入写入分支。
    if bool_exists and not bool_needs_refresh:

        # 稳定配置也必须留下完整原文的审计输出。
        sys.stderr.write(
            "> ERR: [Python] existing tester_worker.toml before update decision:\n"
            f"{str_existing}\n"
        )

    # 已有漂移配置先显示并备份，再在当前任务授权范围内刷新默认合同。
    if bool_needs_refresh:

        # 覆盖前先把完整旧内容送到错误流，避免与 AGENTS 正文混流。
        sys.stderr.write(  # 旧配置审计输出
            "> ERR: [Python] existing tester_worker.toml before refresh:\n"
            f"{str_existing}\n"
        )

        # 只有已有普通文件才需要创建恢复副本。
        if bool_exists and path_config.is_file():

            # 复制而非删除旧内容，保证失败时仍有恢复路径。
            path_backup = _backup_existing(path_config)  # 旧配置备份路径

            # 报告备份位置，供用户核对恢复边界。
            dict_result["backup_path"] = str(path_backup)  # 写入备份证据

    # 缺失配置或已备份漂移配置都写入唯一默认内容。
    if not bool_exists or bool_needs_refresh:

        # 原子写入避免读者观察到半份 TOML。
        _write_atomic(path_config, DEFAULT_TESTER_WORKER_TOML)

        # 标记配置已经写入默认合同。
        dict_result["updated"] = True  # 标记配置已刷新

    # 任何写入路径都重新读取并验证，验证失败即报告错误而非假装成功。
    str_final = path_config.read_text(encoding="utf-8")  # 最终配置原文

    # 重新验证最终读回文本，确保写入没有被截断。
    dict_final = validate_tester_worker_text(str_final)  # 最终配置验证结果

    # 保存最终完整配置供调用方展示。
    dict_result["final_content"] = str_final  # 保存最终完整配置

    # 保存最终 TOML 证据供验证和审计复用。
    dict_result["final_validation"] = dict_final  # 保存最终 TOML 证据

    # 派生最终状态，失败状态不能被误报为成功。
    dict_result["status"] = "valid" if dict_final["valid"] else "invalid"  # 最终状态

    # 验证失败时附加错误列表并阻止调用方宣称成功。
    if not dict_final["valid"]:

        # 错误字段与验证器保持同一结构。
        dict_result["errors"] = dict_final["errors"]  # 保存最终错误列表

    # 返回包含更新、备份和最终验证证据的完整报告。
    return dict_result

# 动态角色验证使用稳定短握手令牌。
def tester_worker_handshake() -> str:
    """返回用于动态角色验证的稳定握手令牌。

    参数：无。
    返回：`TESTER_WORKER_READY` 握手文本。
    """

    # 令牌保持短且唯一，便于 CLI wrapper 在 ANSI 日志中精确筛选。
    return "TESTER_WORKER_READY"
