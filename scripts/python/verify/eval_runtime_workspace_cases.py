"""agents-md-generator 工作区与记忆治理评估用例。"""

# 延迟注解避免运行时解析仅用于类型检查的标注。
from __future__ import annotations

# 评估核心提供路径、夹具、脚本执行器和结果构建合同。
from eval_runtime_core import (
    Any,
    EvalFixtures,
    Path,
    REPO_ROOT,
    SKILL_DIR,

    # 共享结果构建器、序列化模块和隔离目录工具服务各治理场景。
    build_case_result,
    json,
    run_json_script,
    tempfile,
)

# 根合同验证器提供工作区边界的正式唯一性与语义检查。
from verify_workspace_boundary import validate_workspace_boundary_contract

# 技能内评估目录只作为允许存在的发布内容规则证据。
PATH_SKILL_EVALS = Path("skills") / "demo-skill" / "evals"  # 示例技能评估目录相对路径

# 工作区边界变异表逐层删除一个授权保护条件。
def workspace_boundary_weakened_fragments() -> tuple[tuple[str, str], ...]:
    """构建工作区边界压力评估使用的有序变异表。

    参数:
        无。
    返回:
        原始保护片段与弱化替换组成的稳定有序元组。
    """

    # 固定顺序使失败位置能够直接映射到被删除的保护层。
    return (
        ("current work folder", "project folder"),
        ("verified remote-server work folder", "remote folder"),
        ("Changes inside either work folder require no additional confirmation", "Changes may proceed"),
        (
            "remote changes remain allowed only when the configured task route matches that folder",
            "remote changes are allowed",
        ),
        (
            "Official codebase-memory start, index refresh, rebuild, or recovery "
            "for the project bound to either work folder",
            "codebase-memory changes",
        ),
        ("including its configured runtime cache and root persistence artifact", "including related files"),
        ("beyond those boundaries must be necessary and side-effect free", "may be useful"),
        ("Every other external write is prohibited by default", "Other external writes are allowed"),
        (
            "only after the user proactively and explicitly requests the exact action",
            "after the action is considered useful",
        ),
        ("obtain exactly one explicit user confirmation", "obtain user confirmation"),
        ("Any target or scope change invalidates that confirmation.", ""),
        (
            "installed skill always requires exactly one explicit user confirmation",
            "installed skill may proceed",
        ),
    )

# 每个变异必须独立触发正式工作区边界验证器。
def evaluate_workspace_boundary_mutations(str_agents_text: str) -> list[bool]:
    """验证全部工作区边界弱化变异均被正式门禁拒绝。

    参数:
        str_agents_text: 正式渲染的完整根 AGENTS.md 文本。
    返回:
        与有序变异表一一对应的拒绝结论列表。
    """

    # 拒绝列表与变异表保持一一对应关系。
    list_rejections: list[bool] = []  # 每层保护弱化后的阻断结果。

    # 每轮只替换一个保护片段，避免复合变异掩盖失败来源。
    for str_original, str_replacement in workspace_boundary_weakened_fragments():

        # 当前文本仅弱化本轮指定的保护语义。
        str_mutated = str_agents_text.replace(str_original, str_replacement)  # 单项弱化根文本。

        # 正式验证器把当前变异诊断写入独立列表。
        list_errors: list[str] = []  # 当前弱化版本的正式诊断。

        # 返回值与诊断文本共同证明工作区边界被阻断。
        bool_valid = validate_workspace_boundary_contract(str_mutated, "AGENTS.md", list_errors)  # 当前弱化版本是否合法。

        # 只接受明确指向工作区边界的正式拒绝结果。
        list_rejections.append(
            not bool_valid
            and any("workspace boundary" in str_error.casefold() for str_error in list_errors)
        )

    # 返回完整有序结论供能力映射聚合。
    return list_rejections

# 正向能力映射保持评估结果键和历史 JSON 合同稳定。
def workspace_boundary_positive_checks(
    str_agents_text: str,
    list_weakened_rejections: list[bool],
    bool_duplicate_valid: bool,
    list_duplicate_errors: list[str],
) -> dict[str, bool]:
    """构建工作区边界与单次确认能力证据。

    参数：str_agents_text 为正式渲染的完整根规则文本。
    参数：list_weakened_rejections 为有序变异拒绝结论。
    参数：bool_duplicate_valid 为重复边界规则的验证返回值。
    参数：list_duplicate_errors 为重复边界规则的正式诊断。
    返回：键集合稳定的正向能力检查映射。
    """

    # 长片段单独命名，避免能力映射掩盖只读例外的准确边界。
    str_read_only_fragment = "External reads beyond those boundaries must be necessary and side-effect free"  # 边界外只读访问固定片段。

    # 固定键集合维持历史评估 JSON 结构和断言接口。
    return {
        "renders_once": str_agents_text.count("- **Workspace boundary:**") == 1,
        "governed_work_folders_skip_repeat_confirmation": (
            "Changes inside either work folder require no additional confirmation" in str_agents_text
        ),
        "remote_route_must_match": "configured task route matches that folder" in str_agents_text,
        "bound_codebase_memory_operations_skip_confirmation": (
            "Official codebase-memory start, index refresh, rebuild, or recovery" in str_agents_text
            and "also requires no additional confirmation" in str_agents_text
        ),
        "other_external_write_prohibited_by_default": (
            "Every other external write is prohibited by default" in str_agents_text
        ),
        "exact_proactive_request_required": (
            "only after the user proactively and explicitly requests the exact action" in str_agents_text
        ),
        "single_confirmation_after_disclosure": (
            "exact normalized target, action, scope, risks, alternatives, and recovery limits"
            in str_agents_text
            and "obtain exactly one explicit user confirmation" in str_agents_text
        ),
        "changed_scope_invalidates_confirmation": (
            "target or scope change invalidates that confirmation" in str_agents_text
        ),
        "installed_skill_always_confirmed_once": (
            "installed skill always requires exactly one explicit user confirmation" in str_agents_text
        ),
        "authoritative_test_hash_agreement_auto_confirms": (
            "Routine test-hash confirmation is prohibited." in str_agents_text
            and (
                "Agent autonomously confirms when the canonical tester result agrees "
                "with the authoritative current tests tree or receipt."
            ) in str_agents_text
        ),
        "report_only_hash_mismatch_corrected": (
            "A report-only hash mismatch is corrected to the authoritative value." in str_agents_text
        ),
        "conflicting_or_insufficient_provenance_requires_user_review": (
            (
                "Conflicting or insufficient provenance stops for user review "
                "without an autonomous rerun."
            ) in str_agents_text
        ),
        "no_autonomous_rerun_after_provenance_stop": (
            "without an autonomous rerun" in str_agents_text
        ),
        "double_confirmation_removed": (
            "two separate explicit user confirmations" not in str_agents_text
            and "first approves the exception in principle" not in str_agents_text
            and "second approves the exact action" not in str_agents_text
            and "invalidates both confirmations" not in str_agents_text
        ),
        "side_effect_free_read_stays_read_only": str_read_only_fragment in str_agents_text,
        "weakened_contract_rejected": all(list_weakened_rejections),
        "duplicate_contract_rejected": not bool_duplicate_valid and bool(list_duplicate_errors),
    }

# 工作区边界压力场景验证治理内直行不会放宽其他外部写入门禁。
def case_workspace_boundary_authorization_contract(
    case: dict[str, Any],
    helper: EvalFixtures,
) -> dict[str, Any]:
    """评估治理内直行与其他外部写入单次确认合同。

    参数:
        case: 当前评估用例元数据。
        helper: 提供完整受管技能项目渲染能力的夹具助手。

    返回:
        包含压力语义、弱化阻断和重复阻断证据的结构化对比结果。
    """

    # 隔离项目确保文本变异不影响仓库当前根规则。
    with tempfile.TemporaryDirectory() as str_temporary_directory:

        # 临时项目承载正式渲染的受管根 AGENTS.md。
        path_project = Path(str_temporary_directory)  # 外部写入授权评估项目根

        # 项目与安装版本一致，避免无关版本诊断影响边界证据。
        helper.make_rendered_governed_skill_project(
            path_project,  # 指定外部写入授权评估项目根
            name="demo-skill",  # 使用普通受管技能名称
            project_version="v0.4.3",  # 固定评估项目版本
            installed_version="v0.4.3",  # 固定评估安装版本
        )

        # 正式根文本包含生成器实际输出的边界规则。
        str_agents_text = (path_project / "AGENTS.md").read_text(  # 受管根规则文本
            encoding="utf-8",  # 根规则统一使用 UTF-8
            errors="ignore",  # 评估读取不因异常字节终止
        )

        # 每个弱化版本独立调用正式验证器，保持变异顺序与历史证据一致。
        list_weakened_rejections = evaluate_workspace_boundary_mutations(str_agents_text)  # 各保护层弱化阻断结果。

        # 提取正式输出中的唯一工作区边界行。
        str_boundary_rule = next(  # 完整工作区边界规则行
            str_line  # 保留首次匹配的完整规则文本
            for str_line in str_agents_text.splitlines()  # 遍历根规则各行
            if str_line.startswith("- **Workspace boundary:**")  # 固定前缀定位边界规则
        )

        # 重复规则模拟两个可能产生冲突解释的授权来源。
        str_duplicate_text = str_agents_text.replace(  # 重复工作区边界的根文本
            str_boundary_rule,  # 原始唯一边界规则
            f"{str_boundary_rule}\n{str_boundary_rule}",  # 连续写入两条相同规则
        )

        # 重复检查使用独立错误列表保留正式诊断。
        list_duplicate_errors: list[str] = []  # 重复边界验证错误

        # 唯一性验证必须拒绝重复完整规则。
        bool_duplicate_valid = validate_workspace_boundary_contract(  # 重复规则是否合法
            str_duplicate_text,  # 包含两条相同边界的根文本
            "AGENTS.md",  # 固定名称保证诊断文本可复现
            list_duplicate_errors,  # 接收重复规则诊断
        )

    # 正向能力映射由独立构建器保持键集合与语义稳定。
    dict_with_checks = workspace_boundary_positive_checks(  # 工作区边界与单次确认能力证据。
        str_agents_text,  # 正式渲染的完整根规则文本。
        list_weakened_rejections,  # 各保护层弱化后的拒绝结论。
        bool_duplicate_valid,  # 重复边界规则的正式验证返回值。
        list_duplicate_errors,  # 重复边界规则的正式诊断。
    )

    # 无技能基线不提供任何可执行工作区边界或外部写入保护。
    dict_without_checks = {  # 缺少生成器时的能力对照
        str_check_name: False  # 每项边界能力在朴素基线中均缺失
        for str_check_name in dict_with_checks  # 覆盖全部正向检查键
    }

    # 统一结果同时保留渲染规则、弱化结果和重复诊断供失败定位。
    return build_case_result(
        case,  # 当前评估案例元数据
        with_skill_checks=dict_with_checks,  # 使用技能时的压力检查结果
        without_skill_checks=dict_without_checks,  # 无技能历史基线
        with_skill_detail={
            "workspace_boundary_rule": str_boundary_rule,  # 正式生成的完整边界规则
            "weakened_rejections": list_weakened_rejections,  # 各弱化版本阻断结果
            "duplicate_errors": list_duplicate_errors,  # 重复规则正式诊断
        },
        without_skill_detail={
            "baseline": (
                "generic workspace guidance does not separate read-only access "
                "from exact-request single-confirmation external-write approval"
            )
        },
    )

# 根级工作产物场景验证允许仓库根产物并阻断技能内嵌套产物。
def case_root_workspace_artifact_gate(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估工作产物仅允许位于仓库根的目录合同。

    Args:
        case: 当前评估用例元数据。
        helper: 提供受管技能项目渲染能力的夹具助手。

    Returns:
        根目录放行和技能内嵌套阻断的结构化对比结果。
    """

    # 临时项目隔离结构门禁写入和目录夹具。
    with tempfile.TemporaryDirectory() as tmp:

        # 项目根承载受管 skill 和仓库级工作产物。
        path_project = Path(tmp)  # 工作产物目录场景项目根

        # 渲染助手建立完整目录合同和根 AGENTS.md。
        helper.make_rendered_governed_skill_project(path_project, name="demo-skill")

        # 四类工作产物只在仓库根创建，预期全部合法。
        list_root_artifacts = [  # 仓库根允许的工作产物目录
            Path("tests") / "unit",  # 仓库级单元测试目录
            Path("smoke-check"),  # 仓库级冒烟验证目录
            Path("reports") / "output",  # 仓库级报告输出目录
            Path("runs") / "run-001",  # 仓库级运行记录目录
        ]

        # 逐个创建根级产物目录以验证完整允许集合。
        for path_relative in list_root_artifacts:

            # 父目录由 mkdir 递归补齐。
            (path_project / path_relative).mkdir(parents=True, exist_ok=True)

        # 首次结构门禁应允许全部根级工作产物。
        dict_root_gate = run_json_script(  # 根级工作产物结构门禁结果
            "manage_dirs.py",  # 目录治理入口
            "structure-gate",  # 请求检查现有目录结构
            path_project,  # 只包含合法根级产物的项目
            cwd=REPO_ROOT,  # 使用仓库正式目录治理运行时
        )

        # 技能主根内嵌 tests 目录违反工作产物根级边界。
        path_nested_test = path_project / "skills" / "demo-skill" / "tests" / "unit"  # 非法嵌套测试目录

        # 递归创建非法目录以触发真实结构阻断。
        path_nested_test.mkdir(parents=True, exist_ok=True)

        # 第二次门禁应定位并阻断嵌套工作产物。
        dict_nested_gate = run_json_script(  # 嵌套工作产物结构门禁结果
            "manage_dirs.py",  # 复查阶段仍调用正式目录治理入口
            "structure-gate",  # 请求复查变更后的目录结构
            path_project,  # 包含非法技能内 tests 的项目
            cwd=REPO_ROOT,  # 从仓库根解析嵌套结构门禁依赖
        )

        # 根规则文本提供目录合同的人类可读证据。
        str_agents_text = (path_project / "AGENTS.md").read_text(  # 当前根规则文本
            encoding="utf-8",  # 根规则固定使用 UTF-8
            errors="ignore",  # 夹具读取不因异常字节中断
        )

    # 有技能路径必须同时证明根级放行、嵌套阻断和规则可见性。
    dict_with_checks = {  # 根级工作产物治理断言
        "root_gate_passes": bool(dict_root_gate.get("approved")),  # 根级工作产物是否通过
        "nested_gate_blocks": not bool(dict_nested_gate.get("approved")),  # 技能内 tests 是否被阻断
        "nested_reason_mentions_root_rule": any(  # 阻断原因是否解释根级边界
            "work-folder root" in str_reason or "primary project root" in str_reason  # 当前原因是否命中边界措辞
            for str_reason in dict_nested_gate.get("reasons", [])  # 嵌套门禁返回的全部原因
        ),
        "agents_mentions_root_artifact_rule": "Root-level work artifacts" in str_agents_text  # 根规则是否声明工作产物边界
        or not bool(dict_nested_gate.get("approved")),  # 门禁行为可作为兼容证据
        "agents_mentions_skill_local_evals": PATH_SKILL_EVALS.as_posix() in str_agents_text  # 根规则是否声明技能内 eval 例外
        or "skill-local release content" in str_agents_text  # 兼容新版发布内容措辞
        or not bool(dict_nested_gate.get("approved")),  # 结构门禁行为作为最终证据
    }

    # 旧结构治理基线不区分仓库根与技能主根的工作产物。
    dict_without_checks = {  # 缺少根级边界的历史基线
        "root_gate_passes": False,  # 基线不提供根级放行证据
        "nested_gate_blocks": False,  # 基线不阻断嵌套 tests
        "nested_reason_mentions_root_rule": False,  # 基线不解释根级边界
        "agents_mentions_root_artifact_rule": False,  # 基线不声明工作产物规则
        "agents_mentions_skill_local_evals": False,  # 基线不声明 eval 例外
    }

    # 两次真实门禁载荷保留用于定位规则误判。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={"root_gate": dict_root_gate, "nested_gate": dict_nested_gate},
        without_skill_detail={
            "baseline": (
                "older structure governance allowed nested work artifacts "
                "and did not document the root-only boundary clearly"
            )
        },
    )

# 单次评级助手固定命令协议，仅让场景提供项目和任务文本。
def run_task_rating(path_project: Path, str_task: str) -> dict[str, Any]:
    """执行一次机器可读任务评级。

    Args:
        path_project: 评级上下文使用的隔离项目根。
        str_task: 待推断规模与难度的任务文本。

    Returns:
        任务评级脚本产生的结构化报告。
    """

    # 统一入口防止四个场景复制命令行参数协议。
    return run_json_script(
        "task_rating_gate.py",
        "--project",
        path_project,
        "--task-text",
        str_task,
        "--json",
        cwd=REPO_ROOT,
    )

# 任务评级执行助手运行简单、复杂、上下文评级和词序场景。
def task_rating_reports(path_project: Path) -> dict[str, dict[str, Any]]:
    """运行四类任务评级输入。

    Args:
        path_project: 评级命令使用的隔离项目根。

    Returns:
        按场景名称组织的任务评级报告。
    """

    # 简单文档修改应直接采用轻量执行模式。
    str_simple_task = "Update README wording for the install section."  # 简单文档修改描述

    # 简单报告用于证明轻量任务不会触发不必要询问。
    dict_simple = run_task_rating(path_project, str_simple_task)  # 简单任务评级结果

    # 跨服务迁移和发布任务应要求用户确认推断评级。
    str_complex_task = (  # 复杂架构任务描述
        "Build a new architecture across multiple services with migration, release, "
        "remote validation, and complex debugging."
    )

    # 复杂报告用于证明高风险组合任务要求用户确认。
    dict_complex = run_task_rating(path_project, str_complex_task)  # 复杂任务评级结果

    # 用户明确声明噩梦级时不得重复询问评级。
    str_contextual_task = (  # 用户明确评级描述
        "这是噩梦级任务：实现跨仓库架构迁移、发布流程、远程验证和复杂调试。"  # 明示噩梦级上下文
    )

    # 上下文报告用于证明用户自评优先于自动推断。
    dict_contextual = run_task_rating(path_project, str_contextual_task)  # 明确评级结果

    # 仅列举评级顺序不应被误识别为用户自评。
    str_rating_order_task = "请把难度档位写成：噩梦 > 地狱 > 困难 > 普通 > 简单。"  # 评级顺序说明文本

    # 词序报告用于证明枚举词汇不会冒充用户自评。
    dict_rating_order = run_task_rating(path_project, str_rating_order_task)  # 评级词序场景结果

    # 四份报告由统一断言助手比较推断与用户上下文边界。
    return {  # 任务评级场景报告映射
        "simple": dict_simple,  # 简单任务报告
        "complex": dict_complex,  # 复杂任务报告
        "contextual": dict_contextual,  # 用户明确评级报告
        "rating_order": dict_rating_order,  # 评级顺序文本报告
    }

# 全局模板检查助手验证编码、范围、计划、测试和环境安全基线。
def global_template_checks(str_template: str) -> dict[str, bool]:
    """检查全局 Codex AGENTS 模板关键合同。

    Args:
        str_template: 全局规则模板文本。

    Returns:
        各类模板治理合同是否完整的检查映射。
    """

    # 注释基线要求公共合同、关键不变量和行为变更同步文档。
    bool_comments = (  # 注释与文档基线完整性
        "## Comments And Documentation" in str_template  # 是否包含注释治理章节
        and "Comment public contracts" in str_template  # 是否要求注释公共合同
        and "key invariants, non-obvious decisions, generation boundaries, and risk boundaries" in str_template  # 是否覆盖关键语义边界
        and "Do not restate obvious code" in str_template  # 是否禁止复述显然代码
        and "Update stale comments and documentation when behavior changes" in str_template  # 是否要求行为同步文档
    )

    # 复杂实现问题必须先查库文档并复用受支持 API。
    bool_library_reuse = (  # 库手册与成熟 API 复用规则
        "For difficult implementation problems, check library documentation" in str_template  # 检查复杂问题先查库手册
        and "reuse supported APIs before replacement code" in str_template  # 检查替换代码前复用 API
        and "avoid custom substitutes" in str_template  # 检查避免自定义替代实现
    )

    # 双语言技能路由必须同时覆盖 Python 和脚本族。
    bool_language_routing = (  # 语言技能路由完整性
        "## Coding Behavior Baseline" in str_template  # 是否包含编码行为基线
        and "readable-python-generator" in str_template  # 是否路由 Python 技能
        and "readable-script-generator" in str_template  # 是否路由脚本技能
        and "bat/cmd, shell/bash, PowerShell, and Tcl changes" in str_template  # 是否覆盖全部脚本语言族
    )

    # Markdown 公式规则要求行内和块级语法且不误导为代码围栏。
    bool_markdown_math = (  # Markdown 公式合同完整性
        "Markdown documentation formulas" in str_template  # 是否声明公式治理范围
        and "inline \u0060$...$\u0060 or block \u0060$$...$$\u0060" in str_template  # 是否声明两种公式语法
        and "fenced code blocks" not in str_template  # 是否避免错误代码围栏建议
    )

    # Python 环境安全覆盖本地、远程和禁止安装目标。
    bool_environment = (  # Python 环境隔离合同完整性
        "## Environment And Dependency Safety" in str_template  # 是否包含环境安全章节
        and "isolated project environment" in str_template  # 是否要求项目隔离环境
        and "create an isolated environment under the remote workspace" in str_template  # 是否覆盖远程工作区
        and "Never install into system Python" in str_template  # 是否禁止系统 Python
        and "conda \u0060base\u0060" in str_template  # 是否禁止 conda base
        and "sudo pip" in str_template  # 是否阻断提权 pip 安装
        and "pip install --user" in str_template  # 是否禁止用户站点安装
    )

    # 范围纪律冻结目标并阻止审查者把未请求能力带入计划。
    bool_scope_discipline = (  # 目标收紧合同完整性
        "## Scope Discipline" in str_template  # 是否包含范围纪律章节
        and "freeze `Goal`, `Success Criteria`, `In Scope`, and `Out of Scope`" in str_template  # 是否冻结四类范围事实
        and "Treat every other feature, refactor, abstraction" in str_template  # 是否排除未请求功能
        and "Reviewers may identify omissions, contradictions, risks, or unverifiable steps" in str_template  # 是否限制审查职责
    )

    # 非测试智能体默认禁用，只能由当前任务中的用户按角色或目的显式启用。
    bool_review_agent_opt_in = (  # 非测试智能体显式启用合同完整性
        "## Governed Planning And Testing" in str_template  # 是否包含计划与测试章节
        and "Do not use non-testing subagents by default" in str_template  # 是否默认禁用非测试智能体
        and "request in the current task authorizes non-testing subagents" in str_template  # 是否要求当前任务授权
        and "request must name the role or purpose" in str_template  # 是否要求角色或目的
        and "generic request to \"use multi-agent\"" in str_template  # 泛称不得授权
        and "task complexity, ratings, risk, or agent judgment" in str_template  # 推断来源不得授权
        and "use exactly three" in str_template  # 未给数量时默认三个
        and "explicit user-provided count overrides" in str_template  # 显式数量覆盖
        and "Authorization is task-local and does not carry over" in str_template  # 授权不跨任务
    )

    # 测试目录只能由同一隔离测试者操作并形成反馈修复复验循环。
    bool_isolated_testing = (  # 独立测试闭环合同完整性
        "When requested work has an executable test surface" in str_template  # 是否按测试面触发
        and "exactly one isolated `TESTER`" in str_template  # 是否只有一个测试智能体
        and "Pure read-only or planning work" in str_template  # 是否排除无测试面工作
        and "Only that `TESTER` may list, read, create, modify, or run anything under `tests/**`" in str_template  # 是否独占测试目录
        and "The implementing agent must not inspect tests or execute test commands" in str_template  # 是否隔离实现者
        and "problem feedback, and suggested fixes" in str_template  # 是否要求问题反馈
        and "same `TESTER` to re-run verification" in str_template  # 是否要求同一测试者复验
        and "Routine test-hash confirmation is prohibited." in str_template  # 是否禁止常规哈希确认
    )

    # 文档按理解收益选择表现形式，计划同时消除执行期设计决策。
    bool_document_design = (  # 文档与决策完备合同
        "Choose prose, tables, Mermaid flowcharts, or a combination" in str_template  # 是否允许多样表现形式
        and "decision-complete" in str_template  # 是否要求计划决策完备
        and "execution needs no new design choice" in str_template  # 是否排除执行期临时设计
    )

    # 调用方将全部复合合同与其他直接文本断言合并。
    return {  # 全局模板复合检查
        "comments": bool_comments,  # 注释与文档治理合同
        "library_reuse": bool_library_reuse,  # 复杂实现优先复用库能力
        "language_routing": bool_language_routing,  # 双语言技能路由合同
        "markdown_math": bool_markdown_math,  # Markdown 公式合同
        "environment": bool_environment,  # Python 环境隔离合同
        "scope_discipline": bool_scope_discipline,  # 目标收紧合同
        "review_agent_opt_in": bool_review_agent_opt_in,  # 审查智能体显式启用合同
        "isolated_testing": bool_isolated_testing,  # 独立测试闭环合同
        "document_design": bool_document_design,  # 文档与计划完备合同
    }

# 任务评级断言助手比较四份报告和全局模板合同。
def task_rating_contract_checks(
    dict_reports: dict[str, dict[str, Any]],
    dict_template_checks: dict[str, bool],
    str_template: str,
) -> dict[str, bool]:
    """构造任务评级与全局入口治理断言。

    Args:
        dict_reports: 四类任务评级报告。
        dict_template_checks: 全局模板复合合同检查。
        str_template: 全局 Codex AGENTS 模板文本。

    Returns:
        任务评级和模板治理能力检查映射。
    """

    # 各报告使用语义名称缩短后续断言表达式。
    dict_simple = dict_reports["simple"]  # 简单任务评级报告

    # 复杂报告应请求用户确认推断的规模与难度。
    dict_complex = dict_reports["complex"]  # 复杂任务评级报告

    # 上下文报告保留用户明确给出的噩梦级评级。
    dict_contextual = dict_reports["contextual"]  # 明示噩梦级任务报告

    # 词序报告用于排除评级词列表误识别。
    dict_rating_order = dict_reports["rating_order"]  # 难度词枚举场景报告

    # 命名动作和原因集合，避免断言重复读取嵌套字段。
    list_complex_actions = dict_complex.get("recommended_actions", [])  # 复杂任务建议动作

    # 噩梦动作集合同时承载复用研究和分期计划建议。
    list_contextual_actions = dict_contextual.get("recommended_actions", [])  # 噩梦任务建议动作

    # 原因集合只用于排除评级词序被识别为用户自评。
    list_rating_reasons = dict_rating_order.get("reasons", [])  # 词序场景判定原因

    # 长模板片段独立命名，使能力映射保持可扫描。
    str_reuse_rule = "Prefer existing repository patterns, tools, libraries, templates"  # 复用优先规则片段

    # 评级范围片段约束仅对会影响执行模式的任务启用门禁。
    str_rating_scope = "non-trivial enough for rating to affect execution mode"  # 评级适用范围片段

    # 安装保护片段确保触碰已安装技能前始终单次确认。
    str_install_safety = "Always obtain exactly one explicit user confirmation"  # 安装保护单次确认片段

    # 编码基线必须同时包含思考、最小实现、证据和追溯要求。
    list_coding_rules = [  # 编码行为模板关键片段
        "## Coding Behavior Baseline",  # 编码行为章节
        "### 1. Think Before Coding",  # 编码前思考要求
        "Minimum code that solves the problem. Nothing speculative.",  # 最小实现原则
        "fabricating test cases, outputs, or verification evidence",  # 证据真实性边界
        "### Done When",  # 完成条件章节
        "Every changed line must trace directly to the request",  # 变更可追溯要求
    ]

    # 能力映射同时覆盖运行时推断和模板静态合同。
    return {  # 任务评级与全局入口治理断言
        "simple_task_does_not_ask": not bool(dict_simple.get("ask_user_rating"))
        and dict_simple.get("inferred_difficulty") == "simple",  # 简单任务免询问
        "complex_task_asks_rating": bool(dict_complex.get("ask_user_rating"))
        and "ask user to confirm difficulty and scale" in list_complex_actions,  # 复杂任务请求确认
        "contextual_nightmare_preserved": not bool(dict_contextual.get("ask_user_rating"))
        and dict_contextual.get("inferred_difficulty") == "nightmare",  # 明确评级保持不变
        "nightmare_recommends_reuse_and_plan": "reuse-first research" in list_contextual_actions
        and "split into multi-stage project plan" in list_contextual_actions,  # 噩梦任务建议复用分期
        "rating_order_not_user_rating": dict_rating_order.get("inferred_difficulty") == "normal"
        and not any("user rating" in str_reason for str_reason in list_rating_reasons),  # 词序场景避免误判
        "global_template_reuse_first": "## Execution Mode" in str_template
        and str_reuse_rule in str_template,  # 模板要求复用优先
        "global_template_gate": "task_rating_gate.py" in str_template
        and str_rating_scope in str_template
        and "advisory" in str_template,  # 模板声明评级边界
        "global_template_coding_behavior_baseline": all(
            str_rule in str_template for str_rule in list_coding_rules
        )
        and "编码行为基线" not in str_template,  # 编码行为合同完整
        "global_template_comments_baseline": dict_template_checks["comments"],  # 注释治理合同是否完整
        "global_template_language_skill_routing": dict_template_checks["language_routing"],  # 双技能路由是否完整
        "global_template_markdown_math_rule": dict_template_checks["markdown_math"],  # Markdown 公式规则是否完整
        "global_template_remote_python_env_safety": dict_template_checks["environment"],  # 远程 Python 环境安全是否完整
        "global_template_installed_skill_safety": "installed skill directories" in str_template
        and "$CODEX_HOME/skills" in str_template
        and str_install_safety in str_template,  # 已安装技能保护完整
        "global_template_scope_discipline": dict_template_checks["scope_discipline"],  # 目标收紧合同是否完整
        "global_template_review_agent_opt_in": dict_template_checks["review_agent_opt_in"],  # 审查智能体显式启用合同是否完整
        "global_template_isolated_testing": dict_template_checks["isolated_testing"],  # 独立测试闭环是否完整
        "global_template_document_design": dict_template_checks["document_design"],  # 文档与计划完备合同是否完整
    }

# 任务评级场景验证轻量任务、复杂任务和全局规则模板合同。
def case_task_rating_gate_contract(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估任务评级路由和全局入口治理合同。

    Args:
        case: 当前评估用例元数据。
        helper: 未使用的夹具助手，保留统一用例签名。

    Returns:
        任务评级行为与无治理基线的结构化对比结果。
    """

    # 临时项目为四次评级命令提供稳定上下文。
    with tempfile.TemporaryDirectory() as tmp:

        # 评级命令只读取项目路径，不写入真实仓库。
        path_project = Path(tmp)  # 任务评级隔离项目根

        # 四类报告覆盖简单、复杂、明确评级和评级词序。
        dict_reports = task_rating_reports(path_project)  # 任务评级场景报告

    # 全局模板是编码、注释和环境治理的静态事实来源。
    path_template = SKILL_DIR / "assets" / "templates" / "global-codex-agents.md"  # 全局规则模板路径

    # 模板固定使用 UTF-8 编码。
    str_template = path_template.read_text(encoding="utf-8")  # 全局规则模板文本

    # 复合模板合同由专用助手集中判断。
    dict_template_checks = global_template_checks(str_template)  # 编码与环境模板检查

    # 有技能路径同时验证任务推断和全局模板治理。
    dict_with_checks = task_rating_contract_checks(  # 任务评级治理断言
        dict_reports,  # 四类任务评级报告
        dict_template_checks,  # 模板复合合同检查
        str_template,  # 提供直接文本合同的模板内容
    )

    # 无治理基线不具备任何确定性评级或模板合同。
    dict_without_checks = {  # 缺少任务评级治理的历史基线
        str_key: False  # 当前治理能力在基线中均不可用
        for str_key in dict_with_checks  # 完整任务评级治理能力名称
    }

    # 四份运行时报告随结果返回用于定位评级误判。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail=dict_reports,
        without_skill_detail={
            "baseline": (
                "unguided entry behavior asks every task, misses complex planning, "
                "or treats rating vocabulary as confirmed difficulty"
            )
        },
    )

# 非测试智能体案例固定验证显式授权、数量默认值和测试面例外。
def case_global_review_agent_opt_in_contract(
    case: dict[str, Any],
    helper: EvalFixtures,
) -> dict[str, Any]:
    """评估非测试智能体显式启用与独立测试者触发合同。

    参数：case 为当前评估用例元数据，helper 为统一夹具接口。
    返回：非测试智能体授权与测试职责断言的结构化对比结果。
    """

    # 全局模板提供跨仓库的审查智能体和测试者合同。
    path_template = SKILL_DIR / "assets" / "templates" / "global-codex-agents.md"  # 全局模板路径。

    # 技能入口提供 write intent 的默认审查策略。
    path_skill = SKILL_DIR / "SKILL.md"  # 技能入口路径。

    # 写入门禁源码证明缺失审查证据不再阻断默认写入。
    path_completion = (  # 写入完成器路径。
        SKILL_DIR / "scripts" / "python" / "design" / "interview_completion.py"  # 写入完成器源码。
    )

    # 三份文本分别覆盖生成规则、技能路由和确定性写入行为。
    str_template = path_template.read_text(encoding="utf-8")  # 全局规则模板正文。

    # 技能正文用于确认 write intent 不自动派发审查智能体。
    str_skill = path_skill.read_text(encoding="utf-8")  # 当前技能入口正文。

    # 写入完成器源码用于确认审查证据只在显式提供时验证。
    str_completion = path_completion.read_text(encoding="utf-8")  # 设计写入门禁源码。

    # 固定键完整覆盖用户授权、数量、生命周期和隔离 TESTER 合同。
    dict_with_checks = {  # 非测试智能体显式启用断言。
        "default_non_testing_agents_forbidden": (  # 默认非测试智能体禁用能力。
            "Do not use non-testing subagents by default"  # 默认禁用固定语义
            in str_template  # 检查默认禁用规则是否保留在全局模板
        ),
        "current_task_role_or_purpose_required": (  # 当前任务用户显式启用能力。
            "request in the current task authorizes non-testing subagents" in str_template  # 当前任务授权语义
            and "request must name the role or purpose" in str_template  # 角色或目的限定语义
        ),
        "generic_or_inferred_need_not_authorization": (  # 非授权来源排除能力。
            "generic request to \"use multi-agent\"" in str_template  # 泛化多智能体请求语义
            and "task complexity, ratings, risk, or agent judgment" in str_template  # 禁止推断授权语义
        ),
        "omitted_count_defaults_to_three": "use exactly three" in str_template,  # 缺省数量规则
        "explicit_count_overrides_default": "explicit user-provided count overrides" in str_template,  # 显式数量覆盖规则
        "authorization_is_task_local": "Authorization is task-local and does not carry over" in str_template,  # 单任务授权规则
        "isolated_tester_for_executable_surface": (  # 独立测试者触发能力。
            "When requested work has an executable test surface" in str_template  # 可执行测试面触发语义
            and "exactly one isolated `TESTER`" in str_template  # 唯一测试者语义
            and "fork_turns=none" in str_template  # 隔离上下文语义
        ),
        "no_surface_work_skips_tester": (  # 无测试面工作不派发测试者。
            "Pure read-only or planning work and documentation-only changes "  # 无测试面工作类型
            "without a test surface" in str_template  # 检查无测试面时是否跳过测试者
        ),
        "write_intent_skips_default_subagent_design_review": (  # 写入默认跳过审查能力。
            "Write intent also defaults to no review subagent" in str_skill  # 技能路由默认不审查。
            and "if DESIGN_REVIEW_KEY in answers" in str_completion  # 仅显式证据进入审查门禁。
        ),
    }

    # 无治理基线不能证明任何显式启用或测试职责边界。
    dict_without_checks = {  # 无技能对照断言。
        str_key: False  # 无治理基线缺少当前能力。
        for str_key in dict_with_checks  # 遍历七项固定能力键。
    }

    # 返回固定七项断言，供正式 eval 与回归测试共同消费。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={"contract": "non-testing agents opt in; TESTER follows executable surface"},
        without_skill_detail={"baseline": "subagents may be dispatched without explicit role authorization"},
    )

# 记忆治理夹具助手创建未启用记忆的受管项目。
def prepare_memory_project(path_root: Path, helper: EvalFixtures) -> tuple[Path, Path]:
    """创建记忆治理评估所需项目和 Codex 会话根。

    Args:
        path_root: 临时评估根目录。
        helper: 提供项目控制配置的评估夹具。

    Returns:
        隔离项目根与 Codex 会话根。
    """

    # 工作区目录承载待初始化的受管项目。
    path_project = path_root / "workspace"  # 记忆治理评估项目根

    # 治理配置目录保存待初始化项目的控制面事实。
    path_agents = path_project / ".agents"  # 项目治理配置目录

    # 递归创建同时补齐尚不存在的工作区根。
    path_agents.mkdir(parents=True)

    # 初始配置明确关闭记忆，迫使初始化走授权路径。
    dict_profile = helper.skill_answers(name="demo-skill")  # 技能控制配置

    # 关闭标志要求后续初始化必须获得明确授权。
    dict_profile["memory_enabled"] = False  # 明确关闭默认记忆能力

    # 移除已有合同，防止默认夹具绕过缺失记忆路径。
    dict_profile.pop("memory_contract", None)

    # 控制文件是记忆初始化命令读取的唯一配置入口。
    path_control = path_agents / "agents-control.json"  # 项目控制配置路径

    # UTF-8 JSON 保留中文配置且与正式项目格式一致。
    path_control.write_text(json.dumps(dict_profile), encoding="utf-8")

    # 独立 Codex 主目录避免读取开发机真实历史会话。
    path_codex_home = path_root / "codex-home"  # 隔离 Codex 会话根

    # 调用方继续写入唯一的精确工作目录会话。
    return path_project, path_codex_home

# 记忆治理序列助手覆盖授权、初始化、引导和最终门禁。
def run_memory_sequence(
    path_project: Path,
    path_codex_home: Path,
    helper: EvalFixtures,
) -> dict[str, Any]:
    """运行完整记忆治理命令序列并收集证据。

    Args:
        path_project: 待治理的隔离项目根。
        path_codex_home: 仅包含评估会话的 Codex 主目录。
        helper: 提供历史会话夹具的评估助手。

    Returns:
        各阶段命令结果、摘要文本和引导状态。
    """

    # 未授权项目必须先由门禁报告用户授权需求。
    dict_missing_gate = run_json_script(  # 缺失记忆时的授权提示结果
        "manage_docs.py",  # 文档治理命令入口
        "memory-gate",  # 请求检查记忆治理状态
        path_project,  # 尚未初始化记忆的隔离项目
    )

    # 不带确认参数的初始化必须保持拒绝状态。
    dict_denied_init = run_json_script(  # 无确认初始化结果
        "manage_docs.py",  # 复用正式文档治理入口
        "memory-init",  # 请求创建记忆治理存储
        path_project,  # 缺少用户确认的隔离项目
    )

    # 带确认参数后才允许创建正式记忆存储。
    dict_authorized_init = run_json_script(  # 明确授权初始化结果
        "manage_docs.py",  # 使用相同治理入口形成对照
        "memory-init",  # 再次请求初始化记忆存储
        path_project,  # 已获得显式授权的隔离项目
        "--confirm-create",  # 提交不可省略的确认参数
    )

    # 唯一历史会话包含需脱敏的敏感信息和精确项目路径。
    helper.write_codex_session_fixture(
        path_codex_home,
        path_project,
        "019-eval-memory",
        [("user", "请从历史会话初始化 memory，不要保存 password=abc123。")],
    )

    # 所有后续命令只扫描隔离的评估会话目录。
    dict_environment = {"CODEX_HOME": str(path_codex_home)}  # 隔离会话环境覆盖

    # 引导前门禁应阻断，完成历史引导后再次放行。
    dict_unbootstrapped_gate = run_json_script(  # 引导前门禁结果
        "manage_docs.py",  # 文档治理执行入口
        "memory-gate",  # 检查历史会话引导状态
        path_project,  # 已初始化但尚未引导的项目
        env=dict_environment,  # 限定只扫描夹具会话根
    )

    # 引导命令应只吸收精确工作目录匹配的历史会话。
    dict_bootstrap = run_json_script(  # 历史会话引导结果
        "manage_docs.py",  # 历史引导使用的治理入口
        "memory-bootstrap-sessions",  # 请求登记精确目录会话
        path_project,  # 接收历史摘要的隔离项目
        env=dict_environment,  # 指向唯一评估会话来源
    )

    # 已登记历史会话后，最终门禁应恢复通过。
    dict_final_gate = run_json_script(  # 引导后门禁结果
        "manage_docs.py",  # 最终复核仍使用正式入口
        "memory-gate",  # 再次检查完整记忆合同
        path_project,  # 已完成历史引导的项目
        env=dict_environment,  # 保持会话发现范围不变
    )

    # 摘要和状态文件证明脱敏结果及精确会话集合。
    path_memory = path_project / "docs" / "memory"  # 记忆治理产物目录

    # 聚合摘要用于检查敏感信息是否经过统一替换。
    str_summaries = (path_memory / "summaries.md").read_text(encoding="utf-8")  # 聚合摘要文本

    # 引导状态用于验证处理集合没有吸收其他工作目录会话。
    dict_state = json.loads(  # 历史引导状态
        (path_memory / "bootstrap-state.json").read_text(encoding="utf-8")  # 状态文件原始 JSON
    )

    # 证据映射逐项登记，避免把命令序列伪装成参数表。
    dict_evidence: dict[str, Any] = {}  # 记忆治理序列证据

    # 初始门禁证明授权提示可见。
    dict_evidence["missing_gate"] = dict_missing_gate  # 缺失记忆门禁载荷

    # 拒绝结果证明默认初始化保持安全。
    dict_evidence["denied_init"] = dict_denied_init  # 无确认初始化载荷

    # 授权结果证明显式确认能够创建存储。
    dict_evidence["authorized_init"] = dict_authorized_init  # 授权初始化载荷

    # 引导前结果证明未登记会话仍会阻断。
    dict_evidence["unbootstrapped_gate"] = dict_unbootstrapped_gate  # 引导前门禁载荷

    # 引导结果记录实际处理的历史会话。
    dict_evidence["bootstrap"] = dict_bootstrap  # 历史会话引导载荷

    # 最终结果证明完整闭环恢复放行。
    dict_evidence["final_gate"] = dict_final_gate  # 引导后门禁载荷

    # 摘要文本提供敏感值替换证据。
    dict_evidence["summaries"] = str_summaries  # 聚合记忆摘要

    # 状态对象提供精确会话集合证据。
    dict_evidence["state"] = dict_state  # 精确目录会话处理状态

    # 调用方使用统一映射构造能力断言和失败详情。
    return dict_evidence

# 记忆治理断言助手将原始命令证据映射为能力合同。
def memory_governance_checks(dict_evidence: dict[str, Any]) -> dict[str, bool]:
    """构造记忆治理评估断言。

    Args:
        dict_evidence: 完整记忆治理命令序列证据。

    Returns:
        授权、引导、脱敏与最终放行能力检查。
    """

    # 初始门禁证据负责证明缺失状态触发授权要求。
    dict_missing = dict_evidence["missing_gate"]  # 尚未初始化时的门禁载荷

    # 拒绝证据负责证明默认命令不会静默创建存储。
    dict_denied = dict_evidence["denied_init"]  # 缺少确认参数的初始化载荷

    # 授权证据负责证明确认后实际创建数据库。
    dict_authorized = dict_evidence["authorized_init"]  # 明确确认后的初始化载荷

    # 引导前证据应指出尚未登记的精确目录会话。
    dict_unbootstrapped = dict_evidence["unbootstrapped_gate"]  # 历史引导前门禁载荷

    # 最终证据负责证明完整序列恢复门禁通过。
    dict_final = dict_evidence["final_gate"]  # 历史引导后门禁载荷

    # 状态载荷记录本轮识别并处理的会话集合。
    dict_state = dict_evidence["state"]  # 历史会话引导状态

    # 摘要文本提供敏感值已脱敏的直接内容证据。
    str_summaries = dict_evidence["summaries"]  # 完成压缩后的记忆摘要

    # 会话记录先保留完整对象，便于提取稳定标识。
    list_processed = dict_state.get("processed_sessions", [])  # 已处理会话对象

    # 标识序列用于严格比较唯一预期会话。
    list_session_ids = [dict_item.get("id") for dict_item in list_processed]  # 已处理会话标识

    # 初始化返回的创建清单用于确认数据库相对路径。
    list_created = dict_authorized.get("created", [])  # 授权初始化创建清单

    # 路径对象避免在断言中嵌入平台相关分隔符。
    path_database = Path("docs") / "memory" / "memory.sqlite3"  # 预期数据库相对路径

    # 七项能力共同证明记忆治理闭环成立。
    return {  # 记忆治理能力检查
        "missing_gate_requires_authorization": bool(dict_missing.get("requires_user_authorization")),
        "init_without_confirm_rejected": any(
            "--confirm-create" in str_error for str_error in dict_denied.get("errors", [])
        ),
        "authorized_init_created_memory": path_database.as_posix() in list_created,
        "unbootstrapped_session_blocks_gate": any(
            "bootstrap-state" in str_error for str_error in dict_unbootstrapped.get("errors", [])
        ),
        "bootstrap_records_exact_cwd_session": list_session_ids == ["019-eval-memory"],
        "summary_redacts_secret": "password=abc123" not in str_summaries
        and "<REDACTED_SECRET>" in str_summaries,
        "final_gate_passes": bool(dict_final.get("ok")),
    }

# 记忆治理场景验证授权初始化、历史引导和敏感信息脱敏。
def case_memory_governance_gate(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估项目记忆从授权初始化到最终门禁的完整闭环。

    Args:
        case: 当前评估用例元数据。
        helper: 提供控制配置和历史会话夹具的评估助手。

    Returns:
        真实记忆治理能力与无治理基线的结构化对比结果。
    """

    # 临时根隔离项目记忆数据库和 Codex 历史会话。
    with tempfile.TemporaryDirectory() as tmp:

        # 临时路径对象是两个隔离根的共同父目录。
        path_root = Path(tmp)  # 记忆治理临时根

        # 准备函数返回项目根和只服务本场景的会话根。
        tuple_paths = prepare_memory_project(path_root, helper)  # 项目根与会话根组合

        # 第一项是所有治理命令使用的隔离项目根。
        path_project = tuple_paths[0]  # 记忆治理项目根

        # 第二项限制历史发现只读取评估会话。
        path_codex_home = tuple_paths[1]  # 仅含目标历史的会话根

        # 完整命令序列产出后可在临时目录释放前读取所有文件。
        dict_evidence = run_memory_sequence(  # 完整记忆治理序列证据
            path_project,  # 记忆数据库和摘要的写入目标
            path_codex_home,  # 历史会话发现的受限来源
            helper,  # 写入精确工作目录会话的夹具
        )

    # 有技能路径必须满足全部记忆治理能力。
    dict_with_checks = memory_governance_checks(dict_evidence)  # 授权引导脱敏能力检查

    # 无治理基线不提供授权、引导或脱敏保证。
    dict_without_checks = {  # 缺少记忆治理的历史基线
        str_key: False  # 当前能力在基线中不可用
        for str_key in dict_with_checks  # 完整记忆治理能力名称
    }

    # 原始命令结果保留用于定位闭环中断阶段。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "missing_gate": dict_evidence["missing_gate"],
            "unbootstrapped_gate": dict_evidence["unbootstrapped_gate"],
            "bootstrap": dict_evidence["bootstrap"],
            "final_gate": dict_evidence["final_gate"],
        },
        without_skill_detail={
            "baseline": (
                "without the memory gate, missing memory can be skipped, initialized silently, "
                "or populated from unverified history"
            )
        },
    )
