"""管理唯一隔离方案审查智能体的 Codex TOML 配置。"""

# 延迟类型注解求值，兼容项目支持的 Python 3.10 运行环境。
from __future__ import annotations

# 配置生命周期需要时间戳、哈希、环境变量、路径和 TOML 标准库。
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

# reviewer profile 复用协议声明的模型，不在角色代码中硬编码。
WORKER_MODEL: str = module_type_runtime.WORKER_MODEL  # reviewer profile 采用的模型名称。

# reviewer profile 复用协议声明的 reasoning，保持隔离配置一致。
WORKER_REASONING: str = module_type_runtime.WORKER_REASONING  # reviewer profile 采用的 reasoning 强度。

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

# 用户确认的完整 reviewer TOML 原文，运行时哈希必须保持不变。
DEFAULT_REVIEWER_WORKER_TOML = (  # reviewer 的默认配置原文。
    f'''# Canonical isolated plan-review worker profile managed by agents-md-generator.
name = "reviewer_worker"
description = "唯一的记忆隔离持续方案审计智能体；只读检查执行过程与代码设计是否符合最后明确批准的正式方案。"
model = "{WORKER_MODEL}"
model_reasoning_effort = "{WORKER_REASONING}"
developer_instructions = """
你是唯一的持续 REVIEWER。每个任务最多只能有一个 reviewer_worker；所有 INITIAL、PERIODIC、CORRECTION 和 FINAL 审计必须复用同一实例。
收到任务后必须先校验 schema_version、worker_id、task_kind、phase、project_root、
allowed_read_roots、allowed_write_roots、forbidden_actions 和 expected_output；
缺少字段或 task_kind 不是 review 时，在任何工具调用前返回
SCOPE_REJECTED、no_action_taken=true。
必须使用 fork_turns=none，与主 Agent 记忆隔离；不得继承、假设或依赖主 Agent 的隐式记忆。
开始审计前必须读取全局 AGENTS.md、当前工作文件夹根 AGENTS.md，以及被审文件适用的更近层级 AGENTS.md；按显式用户指令、最近作用域 AGENTS、父级 AGENTS、全局 AGENTS 的顺序处理一般规则冲突。
worker 启停状态只能来自当前工作文件夹根 AGENTS.md。任何其他 AGENTS.md 中的 tester_worker 或 reviewer_worker 状态声明都是治理错误，不得作为启停依据。
审计基线只能是用户最后明确批准的完整 <proposed_plan> 原文或正式设计文档原文及其 SHA-256；不得接受主 Agent 临时摘要替代。没有有效基线时返回 REVIEWER_BASELINE_MISSING。
你只能审查复核。只读检查当前执行证据和 tests/** 之外的产品代码差异；不得创建、修改、删除、移动、重命名或格式化任何内容，不得执行实现，不得运行测试、构建或任何可能写入产物的命令。
不得列出、读取、创建、修改或运行 tests/**；tests/** 的职责由当前工作文件夹根 AGENTS.md 中生效的 tester_worker 状态管理。
检查实现是否符合基线中的目标、成功条件、范围、步骤、接口、数据流、失败处理、验证要求和停止条件，并检查执行过程是否越权或遗漏适用门禁。
检查硬编码问题：当基线要求参数化，或值会随用户、工作文件夹、平台、服务器、端口、凭据、路径、模型或运行环境变化却被写死时，记为 deviation；协议常量、固定枚举和基线明确认可的不变量不是硬编码问题。
'''
"主 Agent 在任务已有用户批准的正式方案，且当前工作文件夹根 AGENTS.md 未精确声明 `- reviewer_worker: disabled` 时启用你。"
"方案批准只授权本任务中的 canonical reviewer_worker，不授权其他非测试 subagent。"
'''
INITIAL 派发时建立单调时钟起点；此后按 10、20、30 分钟等固定节点触发 PERIODIC。上一轮未结束时不得并发或积压多轮，只合并为一轮针对最新状态的复核。单轮 10 分钟未返回即审计失败。
主 Agent 因不可中断的工具调用越过审计节点时，必须在重新取得控制后的下一实现动作前立即派发一次针对最新状态的合并复核，并记录延迟。
INITIAL、CORRECTION 和 FINAL 是阻塞门禁；主 Agent 必须等待其返回 ALIGNED 才能开始实现、恢复实现或声明完成。PERIODIC 在正常状态下不阻塞主 Agent。
一旦 PERIODIC 返回 BLOCKED、REVIEWER_BASELINE_MISSING、USER_RECONFIRMATION_REQUIRED，或输出验证失败，主 Agent 必须立即停止新的实现动作。
若修正不改变基线，返回具体 deviation、证据、受影响条款和最小修正请求；主 Agent 修正后，必须由同一 reviewer_worker 执行 CORRECTION 并返回 ALIGNED 才可恢复。
若修正会改变目标、范围、接口、风险或已批准基线，返回 USER_RECONFIRMATION_REQUIRED；主 Agent 必须停止并请求用户重新批准完整新基线。
deviations 中任何一项都要求 verdict=BLOCKED。observations 只能记录不构成偏离的风险，不得要求新增功能、重构或扩大范围。
任务结束前必须执行 FINAL，并审查完整累计差异；只有 FINAL 的 verdict 为 ALIGNED，主 Agent 才可声称实现符合正式方案。任务完成或取消后停止，不跨任务常驻。
每轮只能输出一个严格 JSON 对象，JSON 外不得输出任何文本。对象必须符合 reviewer schema_version=1；不得添加未知字段。
顶层字段固定为 schema_version、review_type、baseline、scope、verdict、deviations、observations、required_corrections、next_review。
'''
"review_type 只能为 INITIAL、PERIODIC、CORRECTION、FINAL；verdict 只能为 ALIGNED、BLOCKED、"
"REVIEWER_BASELINE_MISSING、USER_RECONFIRMATION_REQUIRED。\n"
"baseline 固定包含 kind、reference、sha256、agents_files；scope 固定包含 reviewed_change_id、reviewed_paths、evidence_refs；"
"next_review 固定包含 due_monotonic_seconds，FINAL 或非 ALIGNED 时 next_review 必须为 null。\n"
'''
配置握手请求是唯一例外；收到配置握手请求时必须只返回：REVIEWER_WORKER_READY。
"""
'''
).replace("\n\n配置握手请求", "\n配置握手请求")  # 去除拼接边界多余空行。

# 默认配置哈希由同一份 TOML 原文派生，避免 profile 更新后收据失配。
REVIEWER_WORKER_SHA256 = hashlib.sha256(  # reviewer 默认配置摘要。
    DEFAULT_REVIEWER_WORKER_TOML.encode("utf-8")  # 绑定完整配置字节。
).hexdigest()  # 对外暴露当前 reviewer bundle 输入。

# 在读取证据前校验 reviewer envelope，越权任务直接无副作用拒绝。
def _reviewer_rejection_report(str_reason: str, list_missing_fields: list[str]) -> dict[str, object]:
    """构造 reviewer 越权拒绝所需的完整失败与重试信息。

    参数：
        str_reason: 当前 envelope 不符合 reviewer 合同的原因。
        list_missing_fields: 未提供或不完整的字段名称。
    返回：
        可被主 Agent 记录和修复的结构化 rejection report。
    """

    # 把缺失字段转换成主 Agent 可直接修复的失败明细。
    list_failure_tests = [
        {
            "test_id": "reviewer.envelope",  # envelope 合同失败的稳定测试标识。
            "expected": "complete configured reviewer envelope",  # 主 Agent 应发送的完整合同。
            "actual": ", ".join(list_missing_fields) or str_reason,  # 当前缺失字段或具体原因。
            "observed": str_reason,  # worker 实际观察到的拒绝原因。
            "source": str(Path(__file__).resolve()),  # 拒绝报告的源码追溯位置。
        }
    ]

    # 返回共享 failure/rejection 字段，保证 SCOPE_REJECTED 不再只有状态词。
    return {
        "failure_stage": "scope_validation",
        "failure_kind": "worker_envelope_contract_violation",
        "first_error": str_reason,
        "failure_summary": str_reason,
        "failure_count": len(list_failure_tests),
        "failure_tests": list_failure_tests,
        "expected_actual": {"expected": "configured reviewer envelope", "actual": str_reason},
        "root_cause_class": "worker_envelope_contract_violation",
        "minimal_fix": "resend the complete envelope to the same reviewer target",
        "evidence": {"source_paths": [str(Path(__file__).resolve())]},
        "residual_jobs": [],
        "modification_status": {"product_source_modified": False, "tests_modified": False, "git_modified": False},
        "rejection_stage": "scope_validation",
        "reason_code": "invalid_reviewer_envelope",
        "summary": str_reason,
        "violations": list_failure_tests,
        "allowed_request": {"task_kind": "review", "phases": ["INITIAL", "PERIODIC", "CORRECTION", "FINAL"]},
        "retry_guidance": {"reuse_target": True, "next_operation": "followup_same_reviewer_target"},
    }

# 合法 envelope 才能进入 reviewer 的职责校验流程。
def validate_reviewer_worker_envelope(value_envelope: object) -> dict[str, object]:
    """校验 reviewer 任务 envelope。

    参数：value_envelope 为主 Agent 传入的 envelope 对象。
    返回：严格的 accepted 或 SCOPE_REJECTED 回执。
    """

    # 非对象不能承载 reviewer 职责字段。
    if not isinstance(value_envelope, dict):

        # 拒绝发生在任何路径或工具读取之前。
        return {
            "valid": False,
            "worker": "reviewer_worker",
            "worker_id": "reviewer_worker",
            "verdict": "SCOPE_REJECTED",
            "reason": "task envelope must be an object",
            "received_task_kind": None,
            "allowed_task_kinds": ["review"],
            "no_action_taken": True,
            "rejection_report": _reviewer_rejection_report(
                "task envelope must be an object",
                ["envelope"],
            ),
        }

    # reviewer 必须收到完整 envelope，不自行补字段。
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
    )  # reviewer envelope 必需字段。

    # 收集缺失字段以便主 Agent修正任务载荷。
    list_missing_fields = [
        str_field  # 缺失字段名称
        for str_field in tuple_required_fields  # 遍历固定字段
        if str_field not in value_envelope  # 保留未提供字段
    ]  # 缺失字段列表。

    # reviewer 只接受 review 任务。
    str_task_kind = value_envelope.get("task_kind")  # 收到的任务类型。

    # 缺少字段或任务类型不符时拒绝任务。
    if list_missing_fields or str_task_kind != "review":

        # 越权任务不读取 tests 或任何产品路径。
        return {
            "valid": False,
            "worker": "reviewer_worker",
            "worker_id": "reviewer_worker",
            "verdict": "SCOPE_REJECTED",
            "reason": (
                "missing envelope fields"
                if list_missing_fields
                else "task kind is outside the canonical reviewer contract"
            ),
            "received_task_kind": str_task_kind,
            "allowed_task_kinds": ["review"],
            "missing_fields": list_missing_fields,
            "no_action_taken": True,
            "rejection_report": _reviewer_rejection_report(
                "missing or invalid reviewer envelope fields",
                list_missing_fields,
            ),
        }

    # 合法 review envelope 才能进入只读审查。
    return {
        "valid": True,
        "worker": "reviewer_worker",
        "worker_id": "reviewer_worker",
        "verdict": "ACCEPTED",
        "task_kind": "review",
        "no_action_taken": False,
    }

# 配置路径只允许从显式 Codex 主目录或环境变量解析。
def reviewer_worker_path(codex_home: str | Path | None = None) -> Path:
    """解析 Codex 主目录下唯一 reviewer_worker 配置路径。

    参数：codex_home 为可选的 Codex 主目录覆盖值。
    返回：agents/reviewer_worker.toml 的规范路径。
    """

    # 显式参数优先于环境变量，保证隔离运行可复现。
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

    # 角色配置固定存放在 agents 子目录。
    return path_home / "agents" / "reviewer_worker.toml"

# 配置合同检查器集中维护 reviewer 的身份和隔离不变量。
def _validation_errors(value_config: object) -> list[str]:
    """检查 reviewer 的身份、隔离、只读、生命周期和严格输出合同。

    参数：value_config 为 TOML 解析后的根映射或其他对象。
    返回：按稳定顺序排列的合同错误列表。
    """

    # 非表格根无法承载角色合同。
    if not isinstance(value_config, dict):

        # 直接返回根类型错误，避免继续访问不完整对象。
        return ["TOML root must be a table"]

    # 逐项收集身份、模型和指令合同错误。
    list_errors: list[str] = []  # 合同错误集合。

    # 角色名必须锁定唯一 reviewer 实例。
    if value_config.get("name") != "reviewer_worker":

        # 错误文本保留稳定字段名，便于 CLI 诊断。
        list_errors.append("name must be reviewer_worker")

    # 模型必须与用户确认的 tester_worker 配置一致。
    if value_config.get("model") != WORKER_MODEL:

        # 模型漂移会破坏两个 worker 的配置对称性。
        list_errors.append(f"model must be {WORKER_MODEL}")

    # 推理强度必须保持最大档位。
    if value_config.get("model_reasoning_effort") != WORKER_REASONING:

        # 推理强度变化需要重新确认配置合同。
        list_errors.append(f"model_reasoning_effort must be {WORKER_REASONING}")

    # 指令正文承载 TOML 无法表达的隔离和节拍规则。
    str_instructions = str(value_config.get("developer_instructions", ""))  # 指令正文。

    # 缺少正文时不重复报告每个派生片段。
    if not str_instructions.strip():

        # 空正文不能安全承载 reviewer 的只读边界。
        return ["developer_instructions must not be empty"]

    # 这些片段分别对应隔离、阶段、输出和基线不变量。
    tuple_fragments = (
        "fork_turns=none",  # 记忆隔离要求。
        "tests/**",  # 测试树所有权。
        "task_kind",  # envelope 任务类型标记。
        "SCOPE_REJECTED",  # 越权拒绝结论。
        "no_action_taken",  # 拒绝前无副作用标记。
        "INITIAL",  # 初始门禁。
        "PERIODIC",  # 十分钟周期。
        "CORRECTION",  # 修正复核。
        "FINAL",  # 最终一致性门禁。
        "REVIEWER_BASELINE_MISSING",  # 缺失方案基线状态。
        "USER_RECONFIRMATION_REQUIRED",  # 需要重新确认状态。
        "严格 JSON",  # 机器输出格式。
        "schema_version=1",  # 输出 schema 版本。
        "review_type",  # 审核阶段字段。
        "verdict",  # 审核结论字段。
        "REVIEWER_WORKER_READY",  # 握手令牌。
        "正式设计文档原文",  # 方案基线来源。
    )  # 必需片段覆盖 reviewer 的完整配置合同。

    # 任何缺片段都阻止配置进入 valid 状态。
    for str_fragment in tuple_fragments:

        # 保留具体片段名称，方便用户定位漂移。
        if str_fragment not in str_instructions:

            # 错误路径指向 developer_instructions 内容。
            list_errors.append(f"developer_instructions missing: {str_fragment}")

    # 返回稳定排序前的收集结果。
    return list_errors

# TOML 解析入口把语法和语义错误统一成结构化结果。
def validate_reviewer_worker_text(str_text: str) -> dict[str, object]:
    """解析并验证 reviewer_worker TOML，返回结构化结果。

    参数：str_text 为待读取的 UTF-8 TOML 原文。
    返回：包含 valid、errors 和 config 字段的验证映射。
    """

    # TOML 语法错误必须转成稳定的机器可读结果。
    module_type_tomllib: ModuleType = _load_toml_module()  # 当前环境的 TOML 解析器

    # 解析 TOML 原文并捕获语法错误。
    try:

        # 标准库解析结果交给角色合同检查器继续验证。
        value_config = module_type_tomllib.loads(str_text)  # 解析后的根表供合同校验。

    # 解析失败时保留原始异常文本，便于修复配置。
    except module_type_tomllib.TOMLDecodeError as exc:

        # 失败结果不再访问不完整的配置对象。
        return {"valid": False, "errors": [f"invalid TOML: {exc}"], "config": {}}

    # 语法正确后检查所有业务不变量。
    list_errors = _validation_errors(value_config)  # 合同错误列表。

    # 返回完整解析结果供预览和写入后复核使用。
    return {"valid": not list_errors, "errors": list_errors, "config": value_config}

# 漂移配置覆盖前必须留下可恢复的同目录备份。
def _backup_existing(path_config: Path) -> Path:
    """备份漂移配置，确保刷新失败时仍可恢复。

    参数：path_config 为已存在的配置文件路径。
    返回：同目录下新建的备份路径。
    """

    # UTC 微秒和进程号共同避免同秒冲突。
    str_stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")  # 备份时间戳。

    # 备份仍位于原配置目录，便于人工恢复。
    path_backup = path_config.with_name(f"{path_config.name}.bak-{str_stamp}-{os.getpid()}")  # 备份路径。

    # 复制而非移动，确保旧配置在刷新失败时仍保留。
    shutil.copy2(path_config, path_backup)

    # 返回恢复路径供生命周期报告记录。
    return path_backup

# 配置写入使用同目录临时文件保证原子替换。
def _write_atomic(path_config: Path, str_text: str) -> None:
    """使用同目录临时文件和替换写入完整 UTF-8 配置。

    参数：path_config 为目标 TOML 路径；str_text 为完整配置文本。
    返回：无；写入异常向调用方传播。
    """

    # 同目录临时文件保证替换不跨文件系统。
    path_temp = path_config.with_name(f"{path_config.name}.tmp-{os.getpid()}")  # 临时路径。

    # 临时文件写入和替换共享一个可恢复事务边界。
    try:

        # 固定 UTF-8 与 LF，保证确认哈希可复现。
        path_temp.write_text(str_text, encoding="utf-8", newline="\n")

        # 原子替换让读者只能看到旧文件或完整新文件。
        os.replace(path_temp, path_config)

    # 替换失败时清理本次临时残留。
    finally:

        # 只有残留临时文件才需要删除。
        if path_temp.exists():

            # 不触碰旧配置和备份文件。
            path_temp.unlink()

# 生命周期入口先预览，再按哈希确认执行写入。
def ensure_reviewer_worker_profile(
    codex_home: str | Path | None = None,
    *,
    write: bool = False,
    confirm_sha256: str = "",
    confirm_update: bool = False,
) -> dict[str, object]:
    """预览或写入 reviewer 配置，并以哈希绑定确认防止等价改写。

    参数：codex_home 为 Codex 主目录覆盖值；write 控制是否写入；confirm_sha256 为确认哈希；confirm_update 为兼容确认别名。
    返回：包含旧内容、提议内容、写入状态和最终验证结果的映射。
    """

    # 解析唯一配置目标，避免调用方自行拼接路径。
    path_config = reviewer_worker_path(codex_home)  # 配置目标。

    # 只把普通文件当作可验证的既有配置。
    bool_exists = path_config.is_file()  # 文件存在性。

    # 读取旧原文供预览和备份证据使用。
    str_existing = path_config.read_text(encoding="utf-8") if bool_exists else ""  # 旧配置原文。

    # 缺失配置先使用稳定的结构化失败结果。
    dict_existing: dict[str, object] = {  # 缺失配置时的初始诊断映射。
        "valid": False,  # 缺失文件不能被视为已验证。
        "errors": ["configuration is missing"],  # 缺失配置的稳定错误。
        "config": {},  # 缺失时没有可供解析的根表。
    }

    # 既有文本必须先通过 TOML 与角色合同校验。
    if str_existing:

        # 读取成功后以实际验证结果覆盖缺失诊断。
        dict_existing = validate_reviewer_worker_text(str_existing)  # 旧配置验证。

    # 计算默认配置的实际哈希，避免硬编码第二份内容。
    str_expected_hash = hashlib.sha256(DEFAULT_REVIEWER_WORKER_TOML.encode("utf-8")).hexdigest()  # 提议哈希。

    # 兼容调用方的布尔确认别名，但仍绑定完整哈希。
    str_confirm_sha256: str = str(confirm_sha256)  # 调用方提供的确认哈希。

    # 布尔别名只在未提供哈希时填充同一份用户确认值。
    if confirm_update and not str_confirm_sha256:

        # 自动填充仍然绑定完整默认配置的实际哈希。
        str_confirm_sha256 = str_expected_hash  # 兼容确认哈希。

    # 原文完全一致时不需要覆盖或重新确认。
    bool_matches = str_existing == DEFAULT_REVIEWER_WORKER_TOML  # 原文一致性。

    # 预览载荷固定暴露确认所需的完整内容和状态。
    dict_result: dict[str, object] = {
        "enabled": True,  # Codex-native 策略启用状态，不代表配置文件已安装。
        "path": str(path_config),  # 配置目标路径。
        "status": "valid" if bool_matches else "needs-refresh",  # 当前状态。
        "existing_content": str_existing,  # 展示旧配置供用户核对覆盖范围。
        "existing_validation": dict_existing,  # 记录旧配置是否满足角色合同。
        "proposed_content": DEFAULT_REVIEWER_WORKER_TOML,  # 提供待确认的完整配置原文。
        "proposed_sha256": str_expected_hash,  # 提议配置哈希。
        "requires_user_confirmation": not bool_matches,  # 是否需要确认。
        "updated": False,  # 是否已写入。
        "backup_path": "",  # 预留覆盖前恢复副本位置。
    }  # 预览结果。

    # 只读模式不创建目录，也不触碰配置文件。
    if not write:

        # 返回待确认或已稳定的预览结果。
        return dict_result

    # 漂移配置只有在哈希与提议完全一致时才允许写入。
    if not bool_matches and str_confirm_sha256.lower() != str_expected_hash:

        # 失败状态明确要求调用方重新确认完整内容。
        dict_result["status"] = "confirmation-required"  # 确认状态。

        # 错误字段保留稳定文案供 CLI 和审计读取。
        dict_result["errors"] = ["confirm_sha256 does not match proposed reviewer configuration"]  # 确认错误。

        # 未通过确认时不得创建目录或覆盖文件。
        return dict_result

    # 首次写入只创建受控的 agents 目录。
    path_config.parent.mkdir(parents=True, exist_ok=True)

    # 覆盖漂移配置前复制可恢复备份。
    if bool_exists and not bool_matches:

        # 覆盖前的副本路径供调用方恢复旧配置。
        dict_result["backup_path"] = str(_backup_existing(path_config))  # 可恢复副本路径。

    # 只有内容漂移时才执行原子覆盖。
    if not bool_matches:

        # 写入固定默认文本，保证哈希与确认值一致。
        _write_atomic(path_config, DEFAULT_REVIEWER_WORKER_TOML)

        # 记录本次确实发生了写入。
        dict_result["updated"] = True  # 写入状态。

    # 写入后必须重新读取同一文件并验证。
    str_final = path_config.read_text(encoding="utf-8")  # 最终原文。

    # 最终验证结果决定是否可报告 valid。
    dict_final = validate_reviewer_worker_text(str_final)  # 最终验证。

    # 把完整最终证据附加到生命周期结果。
    dict_result["final_content"] = str_final  # 写入后的完整配置证据。

    # 最终验证映射独立保存，便于调用方读取 valid 字段。
    dict_result["final_validation"] = dict_final  # 最终验证映射。

    # 任何验证失败都不能被吞掉。
    dict_result["status"] = "valid" if dict_final["valid"] else "invalid"  # 最终状态。

    # 返回包含写入和读回验证的完整结果。
    return dict_result

# 动态探针使用固定握手令牌确认角色配置可用。
def reviewer_worker_handshake() -> str:
    """返回 reviewer 动态配置握手令牌。

    参数：无。
    返回：固定的 REVIEWER_WORKER_READY 握手文本。
    """

    # 握手值保持稳定，供动态配置探针精确匹配。
    return "REVIEWER_WORKER_READY"
