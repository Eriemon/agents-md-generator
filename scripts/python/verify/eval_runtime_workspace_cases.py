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

# 技能内评估目录只作为允许存在的发布内容规则证据。
PATH_SKILL_EVALS = Path("skills") / "demo-skill" / "evals"  # 示例技能评估目录相对路径

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

# 全局模板检查助手验证编码、注释、环境和安装安全基线。
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

    # 双语言技能路由必须同时覆盖 Python 和脚本族。
    bool_language_routing = (  # 语言技能路由完整性
        "## Coding Behavior Baseline" in str_template  # 是否包含编码行为基线
        and "readable-python-generator" in str_template  # 是否路由 Python 技能
        and "readable-script-generator" in str_template  # 是否路由脚本技能
        and "bat/cmd, shell/bash, PowerShell, and Tcl scripts" in str_template  # 是否覆盖全部脚本语言族
    )

    # Markdown 公式规则要求行内和块级语法且不误导为代码围栏。
    bool_markdown_math = (  # Markdown 公式合同完整性
        "Markdown documentation formulas" in str_template  # 是否声明公式治理范围
        and "inline \u0060$...$\u0060 or block \u0060$$...$$\u0060 syntax" in str_template  # 是否声明两种公式语法
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

    # 调用方将四个复合合同与其他直接文本断言合并。
    return {  # 全局模板复合检查
        "comments": bool_comments,  # 注释与文档治理合同
        "language_routing": bool_language_routing,  # 双语言技能路由合同
        "markdown_math": bool_markdown_math,  # Markdown 公式合同
        "environment": bool_environment,  # Python 环境隔离合同
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

    # 安装例外片段确保仅用户明确要求时允许触碰安装目录。
    str_install_safety = "explicitly requests installation, replacement, or direct modification"  # 安装保护例外片段

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
