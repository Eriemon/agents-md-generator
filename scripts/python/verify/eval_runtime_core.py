"""执行技能评估并汇总对比结果。

stdout_protocol: json
"""

# 延迟注解避免运行时解析仅用于类型检查的标注。
from __future__ import annotations

# 标准库提供命令行、JSON、环境、临时目录和路径能力。
import argparse
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
        "render": ["render_agents.py", "create_agent_shims.py"],  # 根规则和 shim 渲染入口。
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
        ],
        "release": [  # 安装、内容策略和工程规则选择脚本。
            "install_skill.py",  # 技能安装入口。
            "release_content_policy.py",  # 发布内容策略模块。
            "select_engineering_rules.py",  # 工程规则选择入口。
        ],
        "common": [  # 跨任务共享运行时模块。
            "agents_common.py",  # AGENTS 共同运行时。
            "agents_decisions.py",  # 结构化决策载荷模块。
            "agents_project_facts.py",  # 项目事实发现模块。
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
        AGENTS_MD_INSTALLED_SKILL_DIR=str(SKILL_DIR),  # 使用当前技能源码作为安装态覆盖。
    )

    # 调用方环境覆盖只影响当前评估子进程。
    if env:

        # 显式覆盖值用于构造特定评估场景。
        dict_command_environment.update(env)

    # 子进程结果包含结构化退出状态与两条文本输出流。
    completed_process_script: subprocess.CompletedProcess[str] = subprocess.run(  # 当前脚本执行结果。
        [sys.executable, str(script_path(name)), *map(str, args)],  # Python 入口和脚本参数。
        cwd=cwd or REPO_ROOT,  # 调用方工作目录或当前仓库根。
        text=True,  # 输出流按文本解码。
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
