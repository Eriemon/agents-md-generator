"""执行技能评估并汇总对比结果。

stdout_protocol: json
"""

# 延迟注解避免运行时解析仅用于类型检查的标注。
from __future__ import annotations

# 标准库提供命令行、JSON、环境、临时目录和路径能力。
import argparse
from collections.abc import Callable
import json
import os
import shutil
import subprocess

# 运行时和临时目录模块用于进程控制及隔离夹具生命周期。
import sys
import tempfile
from pathlib import Path
from typing import Any

# 评估运行时禁止在技能源码目录生成字节码缓存。
sys.dont_write_bytecode = True  # 当前评估进程的字节码写入保护。

# 当前文件目录用于定位评估分片和夹具模块。
SCRIPT_DIR = Path(__file__).resolve().parent  # 评估运行时脚本目录。

# Python 任务根目录用于按任务分类解析被测脚本。
SCRIPTS_PYTHON_DIR = Path(__file__).resolve().parents[1]  # 技能 Python 任务目录。

# 脚本总目录是技能源码与 Python 任务根的共同父级。
SCRIPTS_DIR = SCRIPTS_PYTHON_DIR.parent  # 技能脚本总目录。

# 技能根目录提供安装态覆盖和评估配置定位依据。
SKILL_DIR = SCRIPTS_DIR.parent  # 当前 agents-md-generator 技能根目录。

# 仓库根按调用方当前目录解析，保持既有评估执行合同。
REPO_ROOT = Path.cwd().resolve()  # 当前评估目标仓库根目录。

# 同目录夹具提供可复用的临时工程构造方法。
from eval_runtime_fixtures import EvalFixtures

# 独立评估合同保留映射兼容性并提供计划字段属性。
class EvaluationContract(dict[str, object]):
    """配置驱动的 evaluation contract 容器。"""

    # 公开合同声明的必需案例集合属性。
    @property

    # 暴露合同声明的必需案例集合，供评估入口统一选择。
    def required_case_ids(self) -> frozenset[str]:
        """返回独立合同要求的 case ID 集合。

        参数：无；属性读取已校验合同映射。
        返回：规范化后的案例 ID 不可变集合。
        """

        # 从 JSON 合同字段构造稳定的不可变案例集合。
        return frozenset(str(item) for item in self.get("required_case_ids", []))

    # 公开合同声明的设计模式白名单属性。
    @property

    # 暴露合同允许的设计模式白名单，避免调用方维护枚举。
    def allowed_patterns(self) -> frozenset[str]:
        """返回合同允许的设计模式集合。

        参数：无；属性读取已校验合同映射。
        返回：规范化后的设计模式不可变集合。
        """

        # 将合同列表转换为去重后的不可变模式集合。
        return frozenset(str(item) for item in self.get("allowed_patterns", []))

    # 公开合同声明的动态 handler 属性。
    @property

    # 暴露动态 handler 声明，供解析器按合同加载。
    def handlers(self) -> tuple[dict[str, object], ...]:
        """返回 handler binding 的只读 tuple 视图。

        参数：无；属性读取已校验合同映射。
        返回：仅包含对象声明的 handler tuple。
        """

        # 过滤错误形状并保持声明顺序，供动态加载器解析。
        return tuple(item for item in self.get("handlers", []) if isinstance(item, dict))

# 独立结果容器同时暴露 contract、binding 与计划字段。
class EvaluationContractResult(dict[str, object]):
    """兼容 contract/binding 映射和计划字段属性的加载结果。"""

    # 转发嵌套合同的必需案例集合属性。
    @property

    # 从嵌套 contract 转发必需案例集合，保持顶层兼容接口。
    def required_case_ids(self) -> frozenset[str]:
        """返回独立合同要求的 case ID 集合。

        参数：无；属性转发嵌套合同结果。
        返回：合同计算出的案例 ID 不可变集合。
        """

        # 复用已验证 contract 的规范化集合。
        return self["contract"].required_case_ids

    # 转发嵌套合同的设计模式白名单属性。
    @property

    # 从嵌套 contract 转发设计模式白名单。
    def allowed_patterns(self) -> frozenset[str]:
        """返回合同允许的设计模式集合。

        参数：无；属性转发嵌套合同结果。
        返回：合同计算出的设计模式不可变集合。
        """

        # 复用已验证 contract 的模式集合。
        return self["contract"].allowed_patterns

    # 转发嵌套合同的动态 handler 属性。
    @property

    # 从嵌套 contract 转发动态 handler 声明。
    def handlers(self) -> tuple[dict[str, object], ...]:
        """返回 handler binding 的只读 tuple 视图。

        参数：无；属性转发嵌套合同结果。
        返回：合同计算出的 handler tuple。
        """

        # 复用已验证 contract 的 handler 视图。
        return self["contract"].handlers

# 脚本文件名映射到任务分类目录，供评估子进程解析入口。
SCRIPT_TASK_BY_NAME = {  # 被测脚本名称到任务目录的索引。
    str_script_name: str_task_name  # 当前脚本文件名映射到所属任务目录。
    for str_task_name, list_script_names in {  # 遍历任务分类及其公开脚本清单。
        "detect": [  # 项目事实发现类脚本。
            "inspect_project.py",  # 项目事实检查入口。
            "detect_scopes.py",  # AGENTS 作用域发现入口。
            "extract_commands.py",  # 项目命令提取入口。
            "extract_context.py",  # 仓库上下文提取入口。
            "check_freshness.py",  # 根规则新鲜度检查入口。
            "codex_token_usage_review.py",  # Codex token 使用审查入口。
            "task_rating_gate.py",  # 任务评级门禁入口。
        ],
        "design": [  # 项目设计访谈与画像脚本。
            "collect_design_profile.py",  # 设计画像采集入口。
            "design_questions.py",  # 设计问题清单模块。
            "design_profile_builder.py",  # 项目画像构造模块。
            "design_profile_contracts.py",  # 画像合同校验模块。
            "design_remote_gate.py",  # 远程设计门禁模块。
            "design_review_gate.py",  # 设计复核门禁模块。
            "design_takeover.py",  # 现有项目接管模块。
            "design_interview_state.py",  # 访谈状态机模块。
            "design_interview_payload.py",  # 访谈载荷构造模块。
        ],
        "render": [  # 渲染相关脚本清单。
            "render_agents.py",  # 根规则渲染聚合入口。
            "create_agent_shims.py",  # 兼容代理规则生成入口。
            "render_entrypoints.py",  # 渲染命令行入口分片。
            "render_contracts.py",  # 渲染合同分片。
            "render_foundation.py",  # 渲染基础类型分片。
            "render_gate_compaction.py",  # 渲染门禁压缩分片。
            "render_contract_templates.py",  # 合同模板渲染分片。
        ],
        "docs": [  # 文档生命周期治理脚本。
            "manage_docs.py",  # 文档治理总入口。
            "manage_docs_shared.py",  # 文档治理共享运行时。
            "manage_docs_memory.py",  # 项目记忆治理模块。
            "manage_docs_release.py",  # 发布文档治理模块。
            "manage_docs_scaffold_session.py",  # 会话和脚手架模块。
            "manage_docs_sync_verify.py",  # 文档同步验证模块。
        ],
        "dirs": [  # 目录治理总入口及功能分片。
            "manage_dirs.py",  # 目录治理命令入口。
            "manage_dirs_state.py",  # 目录状态管理模块。
            "manage_dirs_review.py",  # 目录变更复核模块。
            "manage_dirs_remote.py",  # 远程目录策略模块。
            "manage_dirs_upload.py",  # 逐项 manifest-only 上传审查模块。
        ],
        "workers": [  # worker 配置生命周期和根状态模块。
            "manage_workers.py",  # 三个 canonical worker 生命周期入口。
            "pycode_gardener.py",  # 只读 gardener Python 审查入口。
            "manage_worker_state.py",  # 当前根 AGENTS worker 状态入口。
            "reviewer_session.py",  # reviewer 会话触发和阶段收据入口。
        ],
        "verify": [  # 验证、评估和置信度门禁脚本。
            "quick_validate.py",  # 快速技能验证入口。
            "audit_skill.py",  # 技能审计入口。
            "verify_agents.py",  # 根规则验证入口。
            "verify_agents_policy.py",  # 根规则策略模块。
            "evaluate_skill.py",  # 技能综合评估入口。
            "check_source_governance.py",  # 源码治理入口。
            "source_governance.py",  # 源码治理运行时。
            "source_governance_config.py",  # 源码治理配置模块。
            "review_governance.py",  # 治理变更复核入口。
            "run_confidence_gate.py",  # 置信度聚合门禁入口。
            "run_skill_evals.py",  # 技能评估运行入口。
            "eval_runtime_core.py",  # 评估共享核心模块。
            "eval_runtime_foundation_cases.py",  # 基础评估案例分片。
            "eval_runtime_policy_cases.py",  # 策略评估案例分片。
            "eval_runtime_fixtures.py",  # 评估工程夹具模块。
            "agent_platform_gate.py",  # 平台目录与配置门禁模块。
            "evidence_validation.py",  # pytest 收据验证模块。
            "routing_contract.py",  # 语言技能路由合同模块。
        ],
        "release": [  # 安装、内容策略和工程规则选择脚本。
            "install_skill.py",  # 技能安装入口。
            "install_release_manifest.py",  # 发布清单和默认平台解析。
            "install_target_copy.py",  # 安装目标复制与备份。
            "install_repository_validation.py",  # 发布收据和仓库状态验证。
            "install_release_sanitization.py",  # 发布内容清洗。
            "release_content_policy.py",  # 发布内容策略模块。
            "select_engineering_rules.py",  # 工程规则选择入口。
        ],
        "common": [  # 跨任务共享运行时模块。
            "agent_platform.py",  # 平台目录、配置和路径解析模块。
            "agents_common.py",  # AGENTS 共同运行时。
            "agents_decisions.py",  # 结构化决策载荷模块。
            "agents_project_facts.py",  # 项目事实发现模块。
            "tester_worker_profile.py",  # 唯一隔离测试智能体配置模块。
            "reviewer_worker_profile.py",  # 唯一隔离方案审查智能体配置模块。
            "gardener_worker_profile.py",  # 唯一隔离 gardener 智能体配置模块。
            "toml_compat.py",  # TOML 兼容解析模块。
            "workspace_settings_policy.py",  # 工作区配置策略模块。
            "git_worktree_policy.py",  # worktree 硬门禁模块。
        ],
    }.items()  # 遍历任务分类映射。
    for str_script_name in list_script_names  # 为分类内每个脚本生成反向索引。
}

# JSON 输出助手保留评估入口依赖的机器可读协议。
def emit_json(object_payload: object) -> None:
    """把评估载荷写入标准输出。

    参数：object_payload 为可 JSON 序列化的评估结果。
    返回：无业务返回值，副作用是写入机器可读标准输出。
    """

    # 单次输出完整 JSON，避免上层解析到过程性文本。
    sys.stdout.write(json.dumps(object_payload, ensure_ascii=False, indent=2) + "\n")

# 脚本路径助手按文件名解析任务分类后的运行时入口。
def script_path(name: str) -> Path:
    """按脚本文件名返回任务分类后的运行时路径。

    参数：name 为被测脚本文件名。
    返回：对应任务目录中的脚本绝对路径。
    """

    # 反向索引保证评估调用遵循任务分类目录布局。
    return SCRIPTS_PYTHON_DIR / SCRIPT_TASK_BY_NAME[name] / name

# 子进程助手执行技能脚本并完整捕获退出码和输出流。
def run_script(
    name: str,
    *args: object,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """在隔离评估环境中运行指定技能脚本。

    参数：name 为脚本名，args 为位置参数，cwd 为可选工作目录。
    参数：env 为需要覆盖的额外环境变量。
    返回：进程退出码、标准输出和标准错误组成的元组。
    """

    # 基础环境禁止字节码并把安装态技能指向当前源码。
    dict_command_environment = dict(  # 评估子进程环境变量。
        os.environ,  # 继承调用进程基础环境。
        PYTHONDONTWRITEBYTECODE="1",  # 禁止子进程写入字节码。
        PYTHONUTF8="1",  # 统一评估子进程的标准流编码。
        AGENTS_MD_INSTALLED_SKILL_DIR=str(SKILL_DIR),  # 使用当前技能源码作为安装态覆盖。
    )

    # 调用方环境覆盖只影响当前评估子进程。
    if env:

        # 显式覆盖值用于构造特定评估场景。
        dict_command_environment.update(env)

        # 评估隔离只提供 CODEX_HOME 时同步平台别名，避免宿主 AGENT_HOME 抢占夹具。
        if "CODEX_HOME" in env and "AGENT_HOME" not in env:

            # 将兼容别名绑定到同一 Codex 根，防止宿主配置污染评估。
            dict_command_environment["AGENT_HOME"] = str(env["CODEX_HOME"])  # 评估进程的兼容配置根

    # 子进程结果包含结构化退出状态与两条文本输出流。
    completed_process_script: subprocess.CompletedProcess[str] = subprocess.run(  # 当前脚本执行结果。
        [sys.executable, str(script_path(name)), *map(str, args)],  # Python 入口和脚本参数。
        cwd=cwd or REPO_ROOT,  # 调用方工作目录或当前仓库根。
        text=True,  # 输出流按文本解码。
        encoding="utf-8",  # 与子进程 PYTHONUTF8 输出合同保持一致。
        errors="strict",  # 非 UTF-8 输出必须显式失败而不是静默替换。
        capture_output=True,  # 同时捕获标准输出和标准错误。
        check=False,  # 非零退出码由评估逻辑自行解释。
        env=dict_command_environment,  # 当前场景隔离环境。
    )

    # 原始进程三元组供 JSON 和非 JSON 场景共同使用。
    return completed_process_script.returncode, completed_process_script.stdout, completed_process_script.stderr

# JSON 子进程助手解析标准输出并保留无载荷失败诊断。
def run_json_script(
    name: str,
    *args: object,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """运行输出 JSON 的技能脚本并解析结果。

    参数：name 为脚本名，args 为位置参数，cwd 和 env 为执行覆盖值。
    返回：脚本标准输出解析得到的 JSON 映射。
    异常：非零退出且无 JSON 输出时抛出 RuntimeError。
    """

    # 执行结果按退出码、标准输出和标准错误拆分。
    tuple_process_output = run_script(  # 当前 JSON 脚本执行三元组。
        name,  # 被测脚本文件名。
        *args,  # 传递给被测脚本的位置参数。
        cwd=cwd,  # 可选工作目录覆盖。
        env=env,  # 可选环境变量覆盖。
    )

    # 三个位置按公开 run_script 返回合同拆分。
    int_return_code = tuple_process_output[0]  # 当前子进程退出码。

    # 标准输出应承载可解析 JSON 载荷。
    str_stdout = tuple_process_output[1]  # 当前子进程标准输出。

    # 标准错误只在无 JSON 失败时进入异常诊断。
    str_stderr = tuple_process_output[2]  # 当前子进程标准错误。

    # 无标准输出的失败无法提供结构化诊断载荷。
    if int_return_code != 0 and not str_stdout.strip():

        # 错误文本包含脚本名、退出码和标准错误。
        raise RuntimeError(
            "> ERR: [Python] JSON script failed: "
            + f"{name} exited with {int_return_code}: {str_stderr}"
        )

    # 非空标准输出必须符合脚本声明的 JSON 协议。
    return json.loads(str_stdout)

# 评估配置助手读取 evals.json 并验证顶层对象合同。
def load_evals(path: Path) -> dict[str, Any]:
    """读取评估配置文件并校验顶层结构。

    参数：path 为 evals.json 文件路径。
    返回：解析后的评估配置映射。
    异常：顶层不是对象时抛出 SystemExit。
    """

    # UTF-8 JSON 载荷承载评估案例和必备覆盖合同。
    object_evaluation_data = json.loads(path.read_text(encoding="utf-8"))  # 原始评估配置载荷。

    # 评估入口只接受字段化顶层对象。
    if not isinstance(object_evaluation_data, dict):

        # 明确错误前缀供 CLI 和上层门禁识别。
        raise SystemExit("> ERR: [Python] evals.json must be an object")

    # 类型检查后返回结构化评估配置。
    return object_evaluation_data

# 评估合同助手读取独立的 case/handler 配置。
def load_evaluation_contract(
    path_project_root: Path | dict[str, Any] | None = None,
    path_skill_root: Path | None = None,
    path_manifest: Path | None = None,
) -> dict[str, Any]:
    """加载参数化评估合同和其 runtime binding。

    参数：path_project_root 和 path_skill_root 为可选根目录覆盖。
    参数：path_manifest 为可选 runtime manifest 覆盖路径。
    返回：包含合同对象、角色摘要和 runtime binding 的映射。
    异常：合同缺失、摘要漂移或字段类型错误时抛出 RuntimeContractError。
    """

    # 延迟导入保持旧安装副本的模块发现方式兼容。
    try:
        from runtime_contracts import load_json_role, load_runtime_manifest

    # 包内导入用于被安装副本直接调用的相同入口。
    except ImportError:

        # common 目录由当前技能脚本根解析，不写死安装绝对路径。
        path_common_dir = SCRIPTS_PYTHON_DIR / "common"  # 共享运行时模块目录

        # 兼容直接脚本加载时缺少包上下文的入口。
        if str(path_common_dir) not in sys.path:

            # 共享模块目录只加入当前进程的导入范围。
            sys.path.insert(0, str(path_common_dir))

        # 通过解析出的共享目录加载合同实现。
        from runtime_contracts import load_json_role, load_runtime_manifest

    # 已有 binding 直接复用，避免重新解析并可能漂移的 manifest。
    if isinstance(path_project_root, dict) and "roles" in path_project_root:

        # 复用调用方已验证的 binding，避免重复解析 manifest。
        dict_binding = path_project_root  # 复用已验证运行时绑定，避免 manifest 再次解析漂移

    # 没有可复用 binding 时才重新解析调用方指定的运行时根。
    else:

        # 解析调用方提供的根目录或当前评估默认根。
        path_project = path_project_root or REPO_ROOT  # 评估项目根

        # 解析技能根，作为 evaluation contract role 的 containment 基准。
        path_skill = path_skill_root or SKILL_DIR  # 评估技能根

        # 加载并验证 runtime manifest 的全部 role 摘要。
        dict_binding = load_runtime_manifest(path_project, path_skill, path_manifest)  # runtime 合同绑定

    # 从绑定 role 读取评估合同对象。
    dict_contract = EvaluationContract(load_json_role(dict_binding, "evaluation_contract"))  # 参数化评估合同

    # required_case_ids 和 handlers 是最小完整性字段。
    if not isinstance(dict_contract.get("required_case_ids"), list):

        # 合同缺少必需案例列表时拒绝继续执行。
        raise SystemExit("> ERR: [Python] evaluation contract required_case_ids is invalid")

    # 顶层同时暴露计划字段和兼容的 contract/binding 容器。
    return EvaluationContractResult({
        "contract": dict_contract,
        "binding": dict_binding,
        "required_case_ids": dict_contract.required_case_ids,
        "allowed_patterns": dict_contract.allowed_patterns,
        "handlers": dict_contract.handlers,
    })

# 按合同声明动态解析评估 handler，避免实现维护 handler 枚举。
def load_eval_handlers(
    object_contract: EvaluationContract | dict[str, object],
    path_verify_root: Path,
) -> dict[str, Callable[..., object]]:
    """从 evaluation contract 动态解析 handler callable。

    参数：object_contract 为已加载的合同映射；path_verify_root 为 handler 模块解析根。
    返回：handler ID 到可调用对象的映射。
    异常：binding 字段缺失、名称非法、导入失败或 ID 重复时抛出 SystemExit。
    """

    # 直接脚本加载时将 verify 根加入模块解析范围。
    if str(path_verify_root) not in sys.path:

        # 将合同模块所在目录加入当前导入范围。
        sys.path.insert(0, str(path_verify_root))

    # 使用标准库动态加载合同声明的模块。
    import importlib

    # 读取 handler 声明列表，缺失时按空集合处理。
    list_bindings = object_contract.get("handlers", [])  # 合同 handler 声明

    # 建立 handler ID 到可调用对象的唯一索引。
    dict_handlers: dict[str, Callable[..., object]] = {}  # 已解析 handler 映射

    # 逐项校验并加载合同中声明的 handler。
    for object_binding in list_bindings:

        # 每项 binding 必须保持对象形状。
        if not isinstance(object_binding, dict):

            # 错误形状不能安全解析模块和 callable 名称。
            raise SystemExit("> ERR: [Python] evaluation handler binding is invalid")

        # 读取合同分配的 handler ID。
        str_handler_id = str(object_binding.get("handler_id", "")).strip()  # 合同 handler 标识

        # 读取模块名称，后续交给 importlib 解析。
        str_module_name = str(object_binding.get("module_name", "")).strip()  # handler 模块名称

        # 读取模块中的 callable 名称。
        str_callable_name = str(object_binding.get("callable_name", "")).strip()  # handler 函数名称

        # 合同名称必须满足 Python 标识符和非空约束。
        if not str_handler_id or not str_module_name.isidentifier() or not str_callable_name.isidentifier():

            # 非法名称不能进入动态导入。
            raise SystemExit("> ERR: [Python] evaluation handler binding names are invalid")

        # 根据合同模块名称加载 handler 所在模块。
        object_module = importlib.import_module(str_module_name)  # 动态加载的 handler 模块

        # 从模块中读取合同声明的 callable。
        object_handler = getattr(object_module, str_callable_name, None)  # 动态 handler 对象

        # callable 必须存在且 ID 不能重复覆盖已有实现。
        if not callable(object_handler) or str_handler_id in dict_handlers:

            # 缺失、非 callable 或重复 ID 都是合同错误。
            raise SystemExit("> ERR: [Python] evaluation handler cannot be resolved")

        # 登记唯一 handler 供后续案例执行按 ID 查找。
        dict_handlers[str_handler_id] = object_handler  # 已解析 handler 记录

    # 返回完整 handler 映射，调用方不再维护模块枚举。
    return dict_handlers

# 检查计数助手统计单个案例满足的布尔预期数量。
def pass_count(checks: dict[str, bool]) -> int:
    """统计单个评估用例中通过的布尔检查项数量。

    参数：checks 为检查名称到通过状态的映射。
    返回：值为 True 的检查项数量。
    """

    # 布尔过滤保持计数语义直接且无副作用。
    return sum(1 for bool_value in checks.values() if bool_value)

# 案例结果助手构造 with-skill 与 without-skill 的统一对照记录。
def build_case_result(
    case: dict[str, Any],
    *,
    with_skill_checks: dict[str, bool],
    without_skill_checks: dict[str, bool],
    with_skill_detail: dict[str, Any],
    without_skill_detail: dict[str, Any],
) -> dict[str, Any]:
    """按两组技能对照结果构造统一评估案例记录。

    参数：case 为案例定义，with_skill_checks 与 without_skill_checks 为检查状态。
    参数：with_skill_detail 与 without_skill_detail 为两组执行证据。
    返回：包含通过状态、证据和改进计数的案例映射。
    """

    # 启用技能后的通过数量用于判断目标行为是否完整。
    int_with_skill_count = pass_count(with_skill_checks)  # 启用技能后的通过检查数。

    # 未启用技能的通过数量提供对照基线。
    int_without_skill_count = pass_count(without_skill_checks)  # 对照组通过检查数。

    # 改进状态要求启用技能后的通过项严格更多。
    bool_improved = int_with_skill_count > int_without_skill_count  # 技能是否带来可测改进。

    # 案例通过还要求启用技能后的全部预期均成立。
    bool_passed = all(with_skill_checks.values()) and bool_improved  # 当前评估案例最终状态。

    # 统一记录保留案例元数据、两组证据和量化比较。
    return {
        "id": case["id"],
        "kind": case["kind"],
        "patterns": case.get("patterns", []),
        "description": case.get("description", ""),
        "passed": bool_passed,
        "with_skill": {
            **with_skill_detail,
            "expectation_checks": with_skill_checks,
        },
        "without_skill": {
            **without_skill_detail,
            "expectation_checks": without_skill_checks,
        },
        "comparison": {
            "with_skill_pass_count": int_with_skill_count,
            "without_skill_pass_count": int_without_skill_count,
            "improved": bool_improved,
        },
    }
