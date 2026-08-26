"""管理只读 gardener_worker 的隔离 Codex TOML 配置。"""

# 延迟注解求值保持 Python 3.10 兼容性。
from __future__ import annotations

# 配置生命周期只依赖哈希、环境、路径、备份和 TOML 读取。
from collections.abc import Callable
from datetime import datetime, timezone
import hashlib
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

# 从同一 runtime 模块取得模型，避免 gardener 自行固定模型名称。
WORKER_MODEL: str = module_type_runtime.WORKER_MODEL  # gardener profile 复用的模型名称。

# 从同一 runtime 模块取得 reasoning，保持角色配置与协议一致。
WORKER_REASONING: str = module_type_runtime.WORKER_REASONING  # gardener profile 复用的 reasoning 强度。

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

# 默认只读 gardener 配置文本必须保持稳定，供渲染和哈希校验共用。
DEFAULT_GARDENER_WORKER_TOML = (  # gardener 的默认配置原文
    f'''# Canonical isolated read-only gardener worker profile managed by agents-md-generator.
name = "gardener_worker"
description = "只读检查开发源码和 tests 设计中的冗余、不匹配与删除候选。"
model = "{WORKER_MODEL}"
model_reasoning_effort = "{WORKER_REASONING}"
developer_instructions = """
你是唯一的只读 GARDENER。fork_turns=none；每个任务只复用一个隔离实例，任务结束立即停止，不建立持久记忆。
收到任务后必须先校验 schema_version、worker_id、task_kind、phase、project_root、
allowed_read_roots、allowed_write_roots、forbidden_actions 和 expected_output；
缺少字段或 task_kind 不是 garden 时，在任何工具调用前返回
SCOPE_REJECTED、no_action_taken=true。
只能由主 Agent 在新的未审查本地 Git 提交后，或根 AGENTS.md 受管刷新且内容哈希改变并通过 verify 后派发；不得自行触发、提交或修改。
工作范围只包括主 Agent 提供的当前工作文件夹 source-root 与 tests-root；只读取 tracked 的 .py 和 .md。
允许列出和读取 tests/** 作为设计证据，但绝不创建、修改、删除、移动、重命名、格式化或运行 tests/**；tester_worker 仍是 tests/** 唯一写入和运行者。read-only。
禁止触碰 dist、github、根目录 docs、.agents、.git、.codebase-memory、ref，以及任何路径逃逸、未跟踪文件、子模块、归档和其他扩展名。
文档审查仅限 .md，代码审查仅限 .py；必须核对文档与代码、测试和当前功能是否匹配，并给出理由和用户决策项。
先运行 pycode_gardener.py 工具，再逐项用允许的源代码、Markdown、tests 设计证据和代码图核实；工具候选不是删除结论。
零调用函数只能记录为 function_candidates；必须检查导出、注册、装饰器、字符串引用、动态风险、测试和文档对齐。
只输出严格 schema_version=1 JSON；不得写报告文件或任何缓存。报告必须包含详细函数列表、绝对/相对路径、起止行、哈希、证据、理由、置信度、删除计划、回滚和验证。
GARDENER_WORKER_READY
"""
'''
)  # TOML 文本结束

# 单任务授权收据与其他 canonical worker 保持同一文本。
SINGLE_TASK_AUTHORIZATION_RECEIPT = (  # 单次任务授权收据文本
    "A single-task authorization receipt is confirmed once across the skill, "
    "AGENTS.md, and CLI; it becomes invalid only when the target, scope, or material risk changes."
)

# 角色合同中的固定身份、隔离、范围和握手片段。
REQUIRED_INSTRUCTION_FRAGMENTS = (  # gardener_worker 指令必需片段
    "fork_turns=none",  # 隔离上下文标记
    "tests/**",  # 测试树只读证据标记
    "task_kind",  # envelope 任务类型标记
    "SCOPE_REJECTED",  # 越权拒绝结论
    "no_action_taken",  # 拒绝前无副作用标记
    "read-only",  # 只读身份标记
    "tracked 的 .py 和 .md",  # 文件类型边界标记
    "pycode_gardener.py",  # 工具入口标记
    "GARDENER_WORKER_READY",  # 动态握手标记
    "schema_version=1",  # 输出 schema 标记
    "function_candidates",  # 零调用候选标记
    "dist",  # 禁止目录标记
    "github",  # GitHub 目录隔离标记
    ".agents",  # 项目治理元数据隔离标记
    "根目录 docs",  # 禁止文档范围标记
    "绝不创建、修改、删除、移动、重命名、格式化或运行 tests/**",  # 测试树操作标记
)

# 构造 gardener 范围拒绝的完整诊断报告。
def _gardener_rejection_report(str_reason: str, list_missing_fields: list[str]) -> dict[str, object]:
    """构造 gardener 越权拒绝所需的完整失败与重试信息。

    参数：
        str_reason: 当前 envelope 不符合合同的原因。
        list_missing_fields: 未提供或不完整的字段名称。
    返回：
        可被主 Agent 记录和修复的结构化 rejection report。
    """

    # 缺失字段组成一条稳定、可定位的失败明细。
    list_failure_tests: list[dict[str, str]] = [
        {
            "test_id": "gardener.envelope",  # envelope 合同失败的稳定测试标识。
            "expected": "complete configured gardener envelope",  # 主 Agent 应发送的完整合同。
            "actual": ", ".join(list_missing_fields) or str_reason,  # 当前缺失字段或具体原因。
            "observed": str_reason,  # worker 实际观察到的拒绝原因。
            "source": str(Path(__file__).resolve()),  # 拒绝报告的源码追溯位置。
        }
    ]  # gardener envelope 失败明细。

    # 统一保留主 Agent 修复所需的 failure/rejection 字段。
    return {
        "failure_stage": "scope_validation",
        "failure_kind": "worker_envelope_contract_violation",
        "first_error": str_reason,
        "failure_summary": str_reason,
        "failure_count": len(list_failure_tests),
        "failure_tests": list_failure_tests,
        "expected_actual": {"expected": "configured gardener envelope", "actual": str_reason},
        "root_cause_class": "worker_envelope_contract_violation",
        "minimal_fix": "resend the complete envelope to the same gardener target",
        "evidence": {"source_paths": [str(Path(__file__).resolve())]},
        "residual_jobs": [],
        "modification_status": {"product_source_modified": False, "tests_modified": False, "git_modified": False},
        "rejection_stage": "scope_validation",
        "reason_code": "invalid_gardener_envelope",
        "summary": str_reason,
        "violations": list_failure_tests,
        "allowed_request": {"task_kind": "garden", "phases": ["POST_COMMIT", "AGENTS_REFRESH"]},
        "retry_guidance": {"reuse_target": True, "next_operation": "followup_same_gardener_target"},
    }

# 在读取源码前校验 gardener envelope，越权任务直接无副作用拒绝。
def validate_gardener_worker_envelope(value_envelope: object) -> dict[str, object]:
    """校验 gardener 任务 envelope。

    参数：value_envelope 为主 Agent 传入的 envelope 对象。
    返回：严格的 accepted 或 SCOPE_REJECTED 回执。
    """

    # 非对象不能承载 gardener 的只读边界。
    if not isinstance(value_envelope, dict):

        # 拒绝发生在任何工具或路径读取之前。
        return {
            "valid": False,
            "worker": "gardener_worker",
            "worker_id": "gardener_worker",
            "verdict": "SCOPE_REJECTED",
            "reason": "task envelope must be an object",
            "received_task_kind": None,
            "allowed_task_kinds": ["garden"],
            "no_action_taken": True,
            "rejection_report": _gardener_rejection_report(
                "task envelope must be an object",
                ["envelope"],
            ),
        }

    # gardener 不对缺失 envelope 字段做推断。
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
    )  # gardener envelope 必需字段。

    # 收集缺失字段作为拒绝证据。
    list_missing_fields = [
        str_field  # 缺失字段名称
        for str_field in tuple_required_fields  # 遍历固定字段
        if str_field not in value_envelope  # 保留未提供字段
    ]  # 缺失字段列表。

    # gardener 只接受 garden 任务。
    str_task_kind = value_envelope.get("task_kind")  # 收到的任务类型。

    # 缺少字段或任务类型不符时拒绝任务。
    if list_missing_fields or str_task_kind != "garden":

        # 越权任务不读取源码、tests 或工具路径。
        return {
            "valid": False,
            "worker": "gardener_worker",
            "worker_id": "gardener_worker",
            "verdict": "SCOPE_REJECTED",
            "reason": (
                "missing envelope fields"
                if list_missing_fields
                else "task kind is outside the canonical gardener contract"
            ),
            "received_task_kind": str_task_kind,
            "allowed_task_kinds": ["garden"],
            "missing_fields": list_missing_fields,
            "no_action_taken": True,
            "rejection_report": _gardener_rejection_report(
                "missing or invalid gardener envelope fields",
                list_missing_fields,
            ),
        }

    # 合法 garden envelope 才能进入只读扫描。
    return {
        "valid": True,
        "worker": "gardener_worker",
        "worker_id": "gardener_worker",
        "verdict": "ACCEPTED",
        "task_kind": "garden",
        "no_action_taken": False,
    }

# 配置路径解析函数固定角色文件位置，避免调用方自行拼接目标。
def gardener_worker_path(codex_home: str | Path | None = None) -> Path:
    """解析唯一 gardener_worker.toml 的规范路径。

    参数：codex_home 为可选 Codex 主目录覆盖值。
    返回：`agents/gardener_worker.toml` 的规范路径。
    """

    # 显式主目录优先，便于隔离预览和真实安装共用入口。
    str_raw_home: str | None = (  # 当前请求的用户根覆盖
        str(codex_home)  # 显式参数优先
        if codex_home is not None  # 参数存在时不读取环境
        else os.environ.get("AGENT_HOME") or os.environ.get("CODEX_HOME")  # 环境变量回退
    )

    # 通过延迟平台解析器获得稳定的 Codex 用户根。
    path_home: Path = _resolve_agent_home(  # 规范化的 Codex 用户根
        Path(__file__).resolve().parents[3],  # 当前 skill 根目录
        str_raw_home,  # 用户根覆盖文本
    )

    # 配置固定落在 Codex agents 目录，不允许调用方自拼路径。
    return path_home / "agents" / "gardener_worker.toml"

# 合同检查器只返回稳定顺序的身份和只读配置错误。
def _validation_errors(value_config: object) -> list[str]:
    """检查 gardener_worker 的 TOML 身份与只读合同。

    参数：value_config 为 TOML 解析后的根映射或其他对象。
    返回：按稳定顺序排列的合同错误文本。
    """

    # 非表格根不能承载角色字段。
    if not isinstance(value_config, dict):

        # 根类型错误足以阻止后续字段访问。
        return ["TOML root must be a table"]

    # 基础身份字段必须完全匹配用户确认的角色。
    list_errors: list[str] = []  # 配置合同错误集合

    # name 字段锁定唯一角色名称。
    if value_config.get("name") != "gardener_worker":

        # 错误文本保留稳定字段名，便于 CLI 诊断。
        list_errors.append("name must be gardener_worker")

    # model 字段锁定用户确认的默认模型。
    if value_config.get("model") != WORKER_MODEL:

        # 模型漂移必须阻止配置通过合同验证。
        list_errors.append(f"model must be {WORKER_MODEL}")

    # reasoning 字段锁定用户确认的最大推理强度。
    if value_config.get("model_reasoning_effort") != WORKER_REASONING:

        # 推理强度漂移需要重新确认配置合同。
        list_errors.append(f"model_reasoning_effort must be {WORKER_REASONING}")

    # 指令正文承载 TOML 顶层无法表达的隔离和输出边界。
    str_instructions = str(  # 规范化后的角色指令文本
        value_config.get("developer_instructions", "")  # 指令字段值
    )  # 角色指令正文

    # 缺失指令时不重复追加派生片段错误。
    if not str_instructions.strip():

        # 空指令不能安全承载只读合同。
        return ["developer_instructions must not be empty"]

    # 逐项检查隔离、范围、输出和握手不变量。
    for str_fragment in REQUIRED_INSTRUCTION_FRAGMENTS:

        # 缺失任一固定片段都阻止外部配置被视为有效。
        if str_fragment not in str_instructions:

            # 错误文本保留缺失片段，便于定位漂移。
            list_errors.append(
                f"developer_instructions missing: {str_fragment}"
            )

    # 返回稳定顺序的合同错误。
    return list_errors

# TOML 入口把语法错误和角色合同错误统一成结构化结果。
def validate_gardener_worker_text(str_text: str) -> dict[str, object]:
    """解析并验证 gardener_worker TOML 文本。

    参数：str_text 为待解析的 UTF-8 TOML 原文。
    返回：包含 valid、errors 和 config 字段的结构化验证结果。
    """

    # TOML 语法错误转换为机器可读结果，避免吞掉具体原因。
    module_type_tomllib: ModuleType = _load_toml_module()  # 当前环境的 TOML 解析器

    # 解析 TOML 原文并捕获语法错误。
    try:

        # 解析结果供后续角色合同检查复用。
        value_config = module_type_tomllib.loads(str_text)  # TOML 根配置映射

    # TOML 解码异常进入结构化错误分支。
    except module_type_tomllib.TOMLDecodeError as exc:

        # 失败结果不再访问不完整的配置对象。
        return {"valid": False, "errors": [f"invalid TOML: {exc}"], "config": {}}

    # 语法正确后执行完整角色合同检查。
    list_errors = _validation_errors(value_config)  # 角色合同错误

    # 返回完整解析结果供预览和写入后复核使用。
    return {"valid": not list_errors, "errors": list_errors, "config": value_config}

# 旧配置备份函数保留同目录和可恢复的原文副本。
def _backup_existing(path_config: Path) -> Path:
    """在同目录创建带 UTC 时间戳的可恢复备份。

    参数：path_config 为已确认存在的 TOML 文件。
    返回：同目录下新建的备份文件路径。
    """

    # UTC 微秒和进程号共同避免同一秒内的备份冲突。
    str_stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")  # 备份时间戳

    # 备份名保留原文件名并使用可检索的 bak 前缀。
    path_backup = path_config.with_name(  # 备份文件路径
        f"{path_config.name}.bak-{str_stamp}-{os.getpid()}"  # 备份文件名
    )  # 组合时间戳和进程号后的备份路径

    # 复制而非移动，确保刷新失败时旧配置仍可恢复。
    shutil.copy2(path_config, path_backup)

    # 返回恢复路径供生命周期报告复用。
    return path_backup

# 原子写入函数避免半写入的角色配置被读取。
def _write_atomic(path_config: Path, str_text: str) -> None:
    """以同目录临时文件和替换完成 UTF-8 原子写入。

    参数：path_config 为最终 TOML 文件；str_text 为完整配置文本。
    返回：无；写入异常向调用方传播。
    """

    # 同目录临时文件保证 os.replace 不跨文件系统。
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

# 生命周期入口负责预览、确认、备份、写入和最终读回验证。
def ensure_gardener_worker_profile(
    codex_home: str | Path | None = None,
    *,
    write: bool = False,
    confirm_update: bool = False,
) -> dict[str, object]:
    """只读预览或按确认收据原子写入 gardener 配置。

    参数：codex_home 为可选 Codex 主目录；write 控制是否落盘；confirm_update 控制漂移覆盖确认。
    返回：包含旧内容、提议内容、写入状态和最终验证结果的结构化报告。
    """

    # 目标路径集中解析，避免外部调用者越过配置目录边界。
    path_config = gardener_worker_path(codex_home)  # 唯一配置目标路径

    # 只有普通文件才进入既有配置读取分支。
    bool_exists = path_config.is_file()  # 目标文件是否存在

    # 读取旧原文供预览和最终审计使用。
    str_existing = path_config.read_text(encoding="utf-8") if bool_exists else ""  # 旧配置原文

    # 缺失配置先使用稳定的结构化失败结果。
    dict_existing: dict[str, object] = {  # 缺失配置时的初始诊断映射
        "valid": False,  # 缺失文件不能被视为已验证
        "errors": ["configuration is missing"],  # 缺失配置的稳定错误
        "config": {},  # 缺失时没有可供解析的根表
    }

    # 既有文本必须先通过 TOML 与角色合同校验。
    if str_existing:

        # 读取成功后以实际验证结果覆盖缺失诊断。
        dict_existing = validate_gardener_worker_text(str_existing)  # 旧配置验证

    # 原文一致才是无需覆盖的稳定状态。
    bool_matches = str_existing == DEFAULT_GARDENER_WORKER_TOML  # 原文一致性

    # 计算默认配置的实际哈希，避免维护第二份内容。
    str_expected_hash = hashlib.sha256(  # 提议配置哈希
        DEFAULT_GARDENER_WORKER_TOML.encode("utf-8")  # 默认配置字节
    ).hexdigest()  # 十六进制哈希文本

    # 结果保留授权收据和旧内容，调用方可先展示再决定动作。
    dict_result: dict[str, object] = {  # gardener 生命周期报告
        "enabled": True,  # Codex-native 策略启用状态，不代表配置文件已安装。
        "path": str(path_config),  # 唯一配置路径
        "status": "valid" if bool_matches else "needs-refresh",  # 当前状态
        "existing_content": str_existing,  # 写入前完整原文
        "existing_validation": dict_existing,  # 写入前验证结果
        "proposed_content": DEFAULT_GARDENER_WORKER_TOML,  # 待确认的完整配置原文
        "proposed_sha256": str_expected_hash,  # 待确认配置哈希
        "requires_user_confirmation": not bool_matches,  # 是否需要确认
        "updated": False,  # 是否已写入
        "backup_path": "",  # 预留覆盖前恢复副本位置
        "confirm_update": confirm_update,  # 调用方确认字段
        "authorization_receipt": SINGLE_TASK_AUTHORIZATION_RECEIPT,  # 单次授权收据
    }

    # 预览路径不得创建目录或写入外部配置。
    if not write:

        # 返回只读状态而不触碰配置文件。
        return dict_result

    # 缺失或漂移配置必须显式确认，避免隐式覆盖用户内容。
    if not bool_matches and not confirm_update:

        # 失败状态明确要求调用方提供当前任务确认。
        dict_result["status"] = "confirmation-required"  # 确认状态

        # 错误字段保留稳定文案供 CLI 和审计读取。
        dict_result["errors"] = ["confirm_update is required for gardener profile refresh"]  # 确认错误

        # 未通过确认时不得创建目录或覆盖文件。
        return dict_result

    # 首次写入仅创建受控 agents 目录。
    path_config.parent.mkdir(parents=True, exist_ok=True)

    # 漂移内容覆盖前保留同目录恢复副本。
    if bool_exists and not bool_matches:

        # 覆盖前的副本路径供调用方恢复旧配置。
        dict_result["backup_path"] = str(  # 可恢复副本路径
            _backup_existing(path_config)  # 创建同目录备份
        )  # 保存备份路径文本

    # 只有缺失或漂移时才执行原子替换。
    if not bool_matches:

        # 写入固定默认文本，确保后续哈希可复现。
        _write_atomic(path_config, DEFAULT_GARDENER_WORKER_TOML)

        # 标记配置已经写入默认合同。
        dict_result["updated"] = True  # 写入状态

    # 写入后强制读回并重新验证，失败不得伪报成功。
    str_final = path_config.read_text(encoding="utf-8")  # 最终配置原文

    # 重新验证最终读回文本，确保写入没有被截断。
    dict_final = validate_gardener_worker_text(str_final)  # 最终配置验证结果

    # 保存最终完整配置供调用方展示。
    dict_result["final_content"] = str_final  # 保存最终配置原文

    # 保存最终 TOML 证据供验证和审计复用。
    dict_result["final_validation"] = dict_final  # 保存最终验证映射

    # 派生最终状态，失败状态不能被误报为成功。
    dict_result["status"] = "valid" if dict_final["valid"] else "invalid"  # 最终状态

    # 验证失败时附加错误列表并阻止调用方宣称成功。
    if not dict_final["valid"]:

        # 错误字段与验证器保持同一结构。
        dict_result["errors"] = dict_final["errors"]  # 保存最终错误列表

    # 返回包含更新、备份和最终验证证据的完整报告。
    return dict_result

# 动态角色验证使用稳定短握手令牌。
def gardener_worker_handshake() -> str:
    """返回 gardener 动态配置握手令牌。

    参数：无。
    返回：`GARDENER_WORKER_READY` 握手文本。
    """

    # 令牌保持稳定，供动态配置探针精确匹配。
    return "GARDENER_WORKER_READY"

# 默认配置哈希由同一份原文派生，避免哈希与正文漂移。
GARDENER_WORKER_SHA256 = hashlib.sha256(  # gardener 默认配置哈希
    DEFAULT_GARDENER_WORKER_TOML.encode("utf-8")  # 以 UTF-8 编码固定哈希输入
).hexdigest()  # 对外暴露稳定的 gardener 配置摘要
