"""实现 agents-md-generator 的规则合同评估场景。"""

# 延迟注解避免评估运行时提前解析共享类型。
from __future__ import annotations

# 评估核心显式提供路径、夹具、执行器与结构化结果合同。
from eval_runtime_core import (
    Any,
    EvalFixtures,
    Path,
    REPO_ROOT,
    SCRIPTS_PYTHON_DIR,
    SCRIPT_DIR,
    SKILL_DIR,

    # 序列化、进程和临时目录模块支撑隔离策略场景。
    build_case_result,
    json,
    run_json_script,
    run_script,
    script_path,
    subprocess,
    tempfile,
)

# Worktree 策略模块路径同时服务源码取证和案例详情。
PATH_WORKTREE_POLICY = SCRIPTS_PYTHON_DIR / "common" / "git_worktree_policy.py"  # worktree 策略模块绝对路径

# 案例详情使用跨平台相对路径，避免泄露执行主机位置。
PATH_WORKTREE_POLICY_RELATIVE = Path("scripts/python/common/git_worktree_policy.py")  # worktree 策略模块发布相对路径

# 污染夹具在项目父目录创建治理明确禁止的保留目录。
def collect_worktree_pollution_report() -> tuple[dict[str, Any], str]:
    """执行额外 worktree 目录污染场景并固化门禁报告。

    Args:
        None: 本函数自行创建并释放隔离项目，不接收外部参数。

    Returns:
        branch-gate 报告与被检测目录的规范化绝对路径。
    """

    # 临时目录隔离 Git 初始化与故意创建的保留目录。
    with tempfile.TemporaryDirectory() as str_temporary_directory:

        # 隔离项目作为 branch-gate 的受管仓库输入。
        path_project = Path(str_temporary_directory) / "governed-project"  # worktree 污染场景项目根

        # 创建项目根以满足 Git 初始化的目录前置条件。
        path_project.mkdir()

        # Git 元数据使门禁能够执行真实 worktree porcelain 检测。
        subprocess.run(
            ["git", "init", "--quiet", str(path_project)],  # 初始化隔离仓库的非交互命令
            check=True,  # 夹具初始化失败时立即终止案例
            capture_output=True,  # 避免 Git 提示污染结构化评估输出
            text=True,  # 将潜在初始化诊断保留为文本
        )

        # 父目录保留名模拟被严格策略禁止的额外 worktree 污染。
        path_forbidden_directory = path_project.parent / ".worktrees"  # 故意创建的阻断目录

        # 真实创建目录以验证检测器行为而非只检查源码字符串。
        path_forbidden_directory.mkdir()

        # branch-gate 应在读取普通分支配置前硬阻断目录污染。
        dict_branch_report = run_json_script(  # 污染仓库的 branch-gate 决策与检查详情
            "manage_docs.py",  # 文档治理公开命令入口
            "branch-gate",  # 分支与 worktree 策略检查动作
            path_project,  # 已注入父目录污染的隔离仓库
            cwd=REPO_ROOT,  # 使用当前源码仓库中的治理运行时
        )

        # 临时目录释放前固化规范化阻断路径。
        str_forbidden_directory = str(path_forbidden_directory.resolve())  # 报告应列出的污染目录

    # 返回可在临时目录释放后继续断言的纯数据证据。
    return dict_branch_report, str_forbidden_directory

# 正向断言合并真实行为、实现检测器与公开技能规则三层证据。
def build_worktree_prohibition_checks(
    dict_branch_report: dict[str, Any],
    str_forbidden_directory: str,
) -> dict[str, bool]:
    """构建额外 worktree 禁止合同的分层检查。

    Args:
        dict_branch_report: branch-gate 对污染夹具生成的结构化报告。
        str_forbidden_directory: 报告应登记的规范化污染目录。

    Returns:
        覆盖真实阻断、实现机制与技能规则的布尔检查映射。
    """

    # 策略源码证明 Git 元数据和保留目录检测机制均已实现。
    str_policy_text = PATH_WORKTREE_POLICY.read_text(encoding="utf-8")  # worktree 策略源码

    # 发布门禁源码用于验证 worktree 检查早于普通配置加载。
    str_release_text = (SCRIPTS_PYTHON_DIR / "docs" / "_manage_docs_release_package.py").read_text(  # 发布门禁源码
        encoding="utf-8"  # 按仓库统一编码读取发布治理实现
    )

    # 渲染入口源码证明硬阻断不能被人工确认降级。
    str_render_text = (SCRIPTS_PYTHON_DIR / "render" / "_render_agents_entrypoints.py").read_text(  # 渲染入口源码
        encoding="utf-8"  # 按仓库统一编码读取渲染入口实现
    )

    # 技能说明必须向调用 agent 明确禁止创建或使用额外 worktree。
    str_skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")  # 技能公开规则文本

    # 嵌套检查载荷包含 worktree 策略的硬阻断事实。
    dict_worktree_report = dict_branch_report.get("checks", {}).get(  # 分支门禁中的 worktree 专项检查
        "worktree_policy",  # worktree 策略子报告键
        {},  # 旧报告缺少该键时保持断言失败而非异常
    )

    # 行为断言要求阻断且不允许 force confirmation 或普通覆盖。
    bool_behavior_blocks = (  # 污染目录是否触发不可确认的硬阻断
        dict_branch_report.get("decision") == "blocked"  # 总决策是否阻断
        and not dict_branch_report.get("approved")  # 报告是否拒绝批准继续
        and not dict_branch_report.get("force_confirmation_required")  # 是否不提供人工确认路径
        and not dict_branch_report.get("override_allowed")  # 是否不允许普通覆盖
        and bool(dict_worktree_report.get("hard_blocking"))  # 子报告是否声明硬阻断
        and str_forbidden_directory in dict_worktree_report.get("forbidden_directories", [])  # 是否登记污染目录
    )

    # 返回检查键保持 eval 配置的既有公开合同。
    return {
        "behavior_blocks_reserved_parent_directory": bool_behavior_blocks,  # 真实污染是否被硬阻断
        "porcelain_detector_present": '["worktree", "list", "--porcelain"]' in str_policy_text,  # 是否读取 worktree 清单
        "linked_worktree_blocked": "linked_current_worktree" in str_policy_text,  # 是否拒绝链接 worktree
        "core_worktree_blocked": '["config", "--get", "core.worktree"]' in str_policy_text,  # 是否检查 core.worktree
        "reserved_directories_blocked": all(  # 是否覆盖全部治理保留目录名
            str_name in str_policy_text  # 当前保留名是否存在于检测器
            for str_name in (".worktrees", ".git-worktrees", "git-worktrees")  # 治理声明的保留目录名
        ),
        "branch_gate_checks_before_profile": str_release_text.index("inspect_worktree_policy(project)")  # 是否先检查污染
        < str_release_text.index("agents-control.json"),  # worktree 检查是否早于普通配置读取
        "hard_block_cannot_be_confirmed": "dict_branch.get(\"hard_blocking\", False) or" in str_render_text,  # 是否禁止确认硬阻断
        "skill_forbids_creation": "forbid creating or using additional Git worktrees" in str_skill_text  # 是否声明禁止额外 worktree
        and "git worktree add" in str_skill_text,  # 是否明确禁止创建命令
    }

# 公开案例把分层证据转换为统一的有技能与无技能对照结果。
def case_additional_worktree_prohibition_contract(
    case: dict[str, Any],
    _helper: EvalFixtures,
) -> dict[str, Any]:
    """实际执行额外 worktree 污染场景并检查完整禁止合同。

    Args:
        case: 当前评估案例定义。
        _helper: 为统一案例签名保留但本场景无需使用的夹具助手。

    Returns:
        包含真实阻断证据与无检测器基线的案例结果。
    """

    # 隔离夹具返回门禁报告和临时目录释放后仍可比较的路径文本。
    tuple_pollution_evidence = collect_worktree_pollution_report()  # worktree 污染行为证据组

    # 第一项是 branch-gate 的完整结构化报告。
    dict_branch_report = tuple_pollution_evidence[0]  # 污染仓库分支门禁报告

    # 第二项是临时目录释放后仍可断言的规范化路径。
    str_forbidden_directory = tuple_pollution_evidence[1]  # 被门禁登记的污染目录文本

    # 三层正向检查共同证明禁止合同不仅存在于文档中。
    dict_with_checks = build_worktree_prohibition_checks(  # worktree 禁止合同正向能力检查
        dict_branch_report,  # branch-gate 真实执行报告
        str_forbidden_directory,  # 报告应登记的污染目录
    )

    # 无检测器基线不能保证任一额外 worktree 阻断能力。
    dict_without_checks = {  # 无技能路径的能力对照
        str_name: False  # 当前禁止能力在朴素分支指导中缺失
        for str_name in dict_with_checks  # 覆盖全部正向检查键
    }

    # 统一结果保留完整行为报告以便失败时定位门禁决策。
    return build_case_result(
        case,  # 当前案例元数据
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "policy_module": PATH_WORKTREE_POLICY_RELATIVE.as_posix(),  # 策略模块跨平台相对路径
            "behavior_report": dict_branch_report,  # branch-gate 完整行为报告
        },
        without_skill_detail={
            "baseline": "branch-only guidance without a detector can still create or tolerate additional worktrees"  # 基线缺陷说明
        },
    )

# 版本同步场景固定区分旧根规则、安装态生成器与项目技能三个版本。
VERSION_ROOT_STALE = "v0.4.2"  # 同步前根 AGENTS 元数据版本

# 安装态版本应写入 agents_version 与 generator_version 元数据。
VERSION_GENERATOR_FIXTURE = "v0.4.3"  # 隔离安装态生成器版本

# 项目技能版本只应写入 Control Profile 的 Version 字段。
VERSION_PROJECT_SKILL = "v0.4.4"  # 项目控制档案应采用的技能版本

# 根规则夹具故意制造生成器元数据和项目技能版本同时漂移。
def prepare_root_version_sync_fixture(
    path_project: Path,
    helper: EvalFixtures,
) -> Path:
    """创建根 AGENTS 版本漂移夹具并返回安装态技能目录。

    Args:
        path_project: 承载根规则与项目技能的隔离项目根。
        helper: 提供安装态技能结构的评估夹具助手。

    Returns:
        使用固定生成器版本构建的安装态技能目录。
    """

    # 项目技能版本应独立于安装态生成器版本参与控制档案同步。
    path_skill_directory = path_project / "skills" / "demo-skill"  # 项目技能目录

    # 创建技能父目录以写入项目版本源文件。
    path_skill_directory.mkdir(parents=True)

    # VERSION 文件是控制档案项目版本的权威来源。
    (path_skill_directory / "VERSION").write_text(
        f"{VERSION_PROJECT_SKILL}\n",  # 项目技能版本文本
        encoding="utf-8",  # 仓库版本文件统一编码
    )

    # 安装态夹具提供生成器自身版本和可执行治理资产。
    path_installed_skill = helper.make_installed_skill_fixture(  # 版本同步场景安装态技能根
        path_project,  # 隔离项目根
        version=VERSION_GENERATOR_FIXTURE,  # 与项目技能不同的生成器版本
    )

    # 旧根规则同时携带过期生成器元数据和控制档案版本。
    list_agents_lines = [  # 同步前根 AGENTS 文本行
        "<!-- FOR AI AGENTS - Human readability is a side effect, not a goal -->",  # 根规则文件标识
        "<!-- Managed by agent: keep sections and order; edit content outside AGENTS-GENERATED blocks -->",  # 托管边界声明
        "<!-- Last updated: 2026-05-14T10:00:00 | Last verified: never -->",  # 固定旧鲜度元数据
        f"<!-- AGENTS-METADATA: agents_version={VERSION_ROOT_STALE}; "  # 旧生成器元数据起始片段
        f"generator_version={VERSION_ROOT_STALE}; default_language=中文 -->",  # 旧生成器元数据结束片段
        "# AGENTS.md",  # 根规则标题
        "<!-- AGENTS-GENERATED:START control-profile -->",  # 控制档案托管块起点
        "## Control Profile",  # 控制档案标题
        "- Strong control: complete.",  # 完整治理强度
        f"- Version: {VERSION_ROOT_STALE}.",  # 故意过期的项目技能版本
        "<!-- AGENTS-GENERATED:END control-profile -->",  # 控制档案托管块终点
        "",  # 文件结尾换行
    ]

    # 写入旧根规则供 preview 和 write 两阶段同步处理。
    (path_project / "AGENTS.md").write_text(
        "\n".join(list_agents_lines),  # 保持托管块逐行结构
        encoding="utf-8",  # 根规则统一编码
    )

    # 调用方使用安装态路径执行三阶段同步闭环。
    return path_installed_skill

# 同步证据助手顺序执行预览、写入和二次预览。
def collect_root_version_sync_evidence(
    path_project: Path,
    path_installed_skill: Path,
) -> dict[str, Any]:
    """收集根版本同步前后报告与最终规则文本。

    Args:
        path_project: 已写入版本漂移规则的隔离项目根。
        path_installed_skill: 为同步命令提供运行时版本的安装态技能根。

    Returns:
        包含预览、写入、同步文本与复检报告的证据映射。
    """

    # 环境变量显式路由至隔离安装态技能，避免读取开发源码版本。
    dict_environment = {  # sync-root-agents 安装态路由环境
        "AGENTS_MD_INSTALLED_SKILL_DIR": str(path_installed_skill)  # 隔离安装态技能绝对路径
    }

    # 首次预览应报告控制档案与根元数据的版本漂移。
    dict_preview = run_json_script(  # 写入前同步诊断
        "manage_docs.py",  # 写入阶段复用文档治理命令入口
        "sync-root-agents",  # 写入阶段选择根规则同步动作
        path_project,  # 含过期规则的隔离项目
        cwd=REPO_ROOT,  # 写入阶段加载当前治理实现
        env=dict_environment,  # 注入隔离安装态生成器
    )

    # write 阶段应分别采用生成器版本和项目技能版本修复两个层面。
    dict_applied = run_json_script(  # 根规则同步写入报告
        "manage_docs.py",  # 幂等复检仍通过公开文档治理入口
        "sync-root-agents",  # 幂等复检再次选择根规则同步动作
        path_project,  # 待修复的隔离项目
        "--write",  # 应用预览中的同步变更
        cwd=REPO_ROOT,  # 复检阶段加载当前治理实现
        env=dict_environment,  # 复检沿用写入时的生成器版本来源
    )

    # 写入后的规则文本证明两个版本来源没有被错误合并。
    str_synced_text = (path_project / "AGENTS.md").read_text(encoding="utf-8")  # 同步后根规则文本

    # 二次预览必须无漂移，证明建议的修复命令能够真正闭环。
    dict_after_sync = run_json_script(  # 写入后同步复检报告
        "manage_docs.py",  # 文档治理公开入口
        "sync-root-agents",  # 根规则同步动作
        path_project,  # 已修复的隔离项目
        cwd=REPO_ROOT,  # 使用当前治理实现
        env=dict_environment,  # 保持同一安装态版本来源
    )

    # 证据映射在临时目录释放前固化所有需要的文本与结构。
    return {
        "preview": dict_preview,  # 写入前漂移报告
        "applied": dict_applied,  # 同步写入报告
        "synced_text": str_synced_text,  # 双版本来源修复后的根规则快照
        "after_sync": dict_after_sync,  # 写入后二次预览
    }

# 公开案例验证生成器元数据与项目控制档案使用各自权威版本。
def case_root_version_sync_contract(
    case: dict[str, Any],
    helper: EvalFixtures,
) -> dict[str, Any]:
    """验证根规则同步正确区分生成器版本与项目技能版本。

    Args:
        case: 当前评估案例定义。
        helper: 提供安装态技能结构的评估夹具助手。

    Returns:
        包含同步闭环检查与三阶段报告的案例结果。
    """

    # 临时项目隔离过期根规则、项目技能和安装态生成器。
    with tempfile.TemporaryDirectory() as str_temporary_directory:

        # 隔离根承载同步命令的全部输入与输出。
        path_project = Path(str_temporary_directory)  # 根版本同步场景项目

        # 夹具返回同步命令必须使用的安装态技能根。
        path_installed_skill = prepare_root_version_sync_fixture(path_project, helper)  # 安装态生成器夹具

        # 三阶段执行在临时目录存续期间固化报告和最终文本。
        dict_evidence = collect_root_version_sync_evidence(  # 根版本同步闭环证据
            path_project,  # 含版本漂移的隔离项目
            path_installed_skill,  # 固定生成器版本的安装态技能
        )

    # 同步后根元数据必须采用安装态生成器版本。
    str_expected_metadata = (  # 根 AGENTS 应包含的生成器元数据片段
        f"agents_version={VERSION_GENERATOR_FIXTURE}; "  # agents 规则生成器版本
        f"generator_version={VERSION_GENERATOR_FIXTURE}; default_language=中文"  # 生成器版本与默认语言
    )

    # 正向检查同时覆盖漂移发现、正确写入和幂等复检。
    dict_with_checks = {  # 根版本同步合同检查
        "preview_detects_control_profile_drift": "control_profile_version_mismatch"  # 预览是否定位控制档案漂移
        in dict_evidence["preview"].get("reasons", []),  # 首次预览诊断原因
        "write_updates_root_metadata": str_expected_metadata in dict_evidence["synced_text"],  # 根元数据是否采用生成器版本
        "write_updates_control_profile_to_project_skill_version": f"- Version: {VERSION_PROJECT_SKILL}."  # 控制档案是否采用项目版本
        in dict_evidence["synced_text"],  # 项目版本应出现在控制档案块中
        "write_does_not_force_control_profile_to_generator_version": f"- Version: {VERSION_GENERATOR_FIXTURE}."  # 是否避免混用生成器版本
        not in dict_evidence["synced_text"],  # 生成器版本不应替代项目版本
        "second_preview_is_clean": not dict_evidence["after_sync"].get("sync_required")  # 二次预览是否无需同步
        and dict_evidence["after_sync"].get("reasons") == [],  # 二次预览是否无残留原因
    }

    # 旧同步基线无法保证任一双版本来源闭环能力。
    dict_without_checks = {  # 无技能路径的同步能力对照
        str_name: False  # 当前同步保证在旧基线中缺失
        for str_name in dict_with_checks  # 对照根同步合同的每项能力
    }

    # 返回三阶段报告使失败能够区分预览、写入和幂等性问题。
    return build_case_result(
        case,  # 根版本同步案例元数据
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "preview": dict_evidence["preview"],  # 初次发现版本漂移的预览
            "applied": dict_evidence["applied"],  # 双版本来源同步写入报告
            "after_sync": dict_evidence["after_sync"],  # 写入后的幂等性复检
        },
        without_skill_detail={
            "baseline": (
                "older sync-root-agents guidance could leave Control Profile version drift behind "
                "or force it to the generator version after the suggested repair command ran"
            )  # 旧同步基线无法区分两个版本来源
        },
    )

# 源码渲染场景使用明显不同的版本以检测安装态污染。
VERSION_SOURCE_RENDER = "v9.9.9"  # 源码仓库 VERSION 声明值

# 旧安装态版本不得泄漏进源码仓库生成的根规则。
VERSION_STALE_INSTALLED = "v1.0.4"  # 隔离安装态技能的过期版本

# 渲染夹具创建最小技能源码、控制档案与不同版本的安装态运行时。
def prepare_source_render_fixture(
    path_root: Path,
    helper: EvalFixtures,
) -> tuple[Path, Path]:
    """准备源码仓库渲染版本优先级夹具。

    Args:
        path_root: 承载源码工作区与安装态技能的隔离根。
        helper: 提供安装态技能结构的评估夹具助手。

    Returns:
        源码项目根与过期安装态技能根组成的元组。
    """

    # workspace 子目录模拟包含 agents-md-generator 源码的真实项目。
    path_project = path_root / "workspace"  # 源码渲染场景项目根

    # 技能源目录提供 VERSION 与最小公开技能说明。
    path_skill_directory = path_project / "skills" / "agents-md-generator"  # 源码技能根

    # 创建技能树后再写入渲染器发现所需的源码文件。
    path_skill_directory.mkdir(parents=True)

    # 控制档案目录承载最小项目治理配置。
    (path_project / ".agents").mkdir()

    # 最小 SKILL 文档使项目被识别为 agents-md-generator 源码仓库。
    str_skill_document = (  # 源码技能识别文档
        "---\n"
        "name: agents-md-generator\n"
        "description: Use when testing source render version\n"
        "---\n"
        "# Skill\n"
    )

    # 写入公开技能元数据以完成源码仓库识别。
    (path_skill_directory / "SKILL.md").write_text(
        str_skill_document,  # 最小技能文档文本
        encoding="utf-8",  # 技能文档统一编码
    )

    # 源码 VERSION 应覆盖安装态技能携带的旧版本。
    (path_skill_directory / "VERSION").write_text(
        f"{VERSION_SOURCE_RENDER}\n",  # 源码发布版本文本
        encoding="utf-8",  # 版本文件统一编码
    )

    # 最小控制档案选择 skill 项目与中文对话规则。
    dict_control_profile = {  # 渲染器输入控制档案
        "kind": "skill",  # 项目类型
        "name": "agents-md-generator",  # 项目名称
        "default_conversation_language": "中文",  # 默认对话语言
        "git_management": "no-git-management",  # 关闭无关 Git 治理文本
    }

    # 写入控制档案供 render_agents 显式加载。
    (path_project / ".agents" / "agents-control.json").write_text(
        json.dumps(dict_control_profile),  # 序列化最小渲染配置
        encoding="utf-8",  # 控制档案统一编码
    )

    # 安装态技能故意落后，以验证版本选择来自源码而非运行时位置。
    path_installed_skill = helper.make_installed_skill_fixture(  # 过期安装态技能根
        path_root,  # 隔离资产共同根
        version=VERSION_STALE_INSTALLED,  # 与源码不同的旧版本
    )

    # 调用方需要项目根和安装态根执行公开渲染命令。
    return path_project, path_installed_skill

# 公开案例验证源码 VERSION 对根元数据和控制档案具有优先级。
def case_source_repo_render_version_contract(
    case: dict[str, Any],
    helper: EvalFixtures,
) -> dict[str, Any]:
    """验证源码仓库渲染不会泄漏过期安装态技能版本。

    Args:
        case: 当前评估案例定义。
        helper: 提供安装态技能结构的评估夹具助手。

    Returns:
        包含渲染版本优先级检查与进程诊断的案例结果。
    """

    # 临时根隔离源码工作区和故意过期的安装态技能。
    with tempfile.TemporaryDirectory() as str_temporary_directory:

        # 隔离根承载本案例全部渲染资产。
        path_root = Path(str_temporary_directory)  # 源码渲染案例临时根

        # 夹具元组提供公开渲染命令的项目与安装态输入。
        tuple_fixture = prepare_source_render_fixture(path_root, helper)  # 源码渲染输入路径组

        # 第一项是包含 VERSION 和控制档案的源码项目根。
        path_project = tuple_fixture[0]  # 待渲染源码项目

        # 第二项是携带故意过期版本的安装态技能根。
        path_installed_skill = tuple_fixture[1]  # 渲染运行时安装态技能

        # 公开渲染命令应执行成功并把生成规则写到标准输出。
        tuple_process = run_script(  # render_agents 进程退出码与输出组
            "render_agents.py",  # 根 AGENTS 渲染入口
            path_project,  # 包含源码版本的项目根
            "--profile",  # 显式控制档案参数
            path_project / ".agents" / "agents-control.json",  # 项目治理配置路径
            cwd=REPO_ROOT,  # 使用当前源码中的渲染实现
            env={  # 渲染命令的隔离安装态路由环境
                "AGENTS_MD_INSTALLED_SKILL_DIR": str(path_installed_skill)  # 注入过期安装态运行时
            },
        )

    # 进程元组第一项用于判断渲染是否成功。
    int_return_code = tuple_process[0]  # 判断公开渲染流程是否正常完成的进程状态码

    # 标准输出包含待检查的完整生成 AGENTS 文本。
    str_standard_output = tuple_process[1]  # render_agents 标准输出

    # 标准错误保留公开命令失败时的诊断上下文。
    str_standard_error = tuple_process[2]  # render_agents 标准错误

    # 根元数据中的两个生成器字段都必须采用源码 VERSION。
    str_expected_metadata = (  # 源码仓库应生成的根 AGENTS 元数据
        f"<!-- AGENTS-METADATA: agents_version={VERSION_SOURCE_RENDER}; "
        f"generator_version={VERSION_SOURCE_RENDER}; default_language=中文 -->"
    )

    # 正向检查覆盖命令成功、两个源码版本落点和旧版本排除。
    dict_with_checks = {  # 源码版本渲染合同检查
        "render_succeeds": int_return_code == 0,  # 公开渲染命令是否成功
        "metadata_uses_source_version": str_expected_metadata in str_standard_output,  # 根元数据是否采用源码版本
        "control_profile_uses_source_version": f"- Version: {VERSION_SOURCE_RENDER}."  # 控制档案是否采用源码版本
        in str_standard_output,  # 完整渲染规则文本
        "stale_installed_metadata_absent": f"agents_version={VERSION_STALE_INSTALLED}"  # 是否排除安装态旧版本
        not in str_standard_output,  # 旧安装态 agents_version 不得出现在生成文本中
    }

    # 旧渲染基线不能保证源码版本优先级。
    dict_without_checks = {  # 无技能路径的版本选择对照
        str_name: False  # 当前源码版本保证在旧基线中缺失
        for str_name in dict_with_checks  # 覆盖全部渲染合同键
    }

    # 返回输出头和标准错误以支持失败诊断且避免复制完整规则。
    return build_case_result(
        case,  # 源码版本渲染案例元数据
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "stdout_head": str_standard_output[:300],  # 渲染规则前缀诊断
            "stderr": str_standard_error,  # 渲染进程错误诊断
        },
        without_skill_detail={
            "baseline": "a stale installed skill can leak its version into source-release root metadata"  # 旧渲染基线缺陷
        },
    )

# 语言技能路由片段覆盖配置来源、代码可读性和 Python/脚本双向约束。
REQUIRED_LANGUAGE_ROUTING_SNIPPETS = (  # 生成根规则必须包含的路由语义
    "编码行为配置来源：`.agents/global-rule-overrides.json`",  # 编码行为配置来源
    "注释质量：只允许非显然意图、不变量、风险、生成边界或公共 API 行为注释",  # 注释语义边界
    "严禁把代码压缩到一行",  # 禁止压缩代码
    "炫技代码",  # 禁止不可读技巧
    "语言技能路由（Python）：",  # Python 路由标题
    "readable-python-generator",  # Python 最终责任技能
    "语言技能路由（脚本）：",  # 脚本路由标题
    "readable-script-generator",  # 脚本最终责任技能
    "Python 目标继续使用 `readable-python-generator`",  # 跨语言冲突归属
    "脚本包装器调用 Python",  # 脚本包装器归属
)

# 解析公开命令输出时统一保留结构化错误，避免空 stdout 隐藏诊断。
def parse_verify_process(tuple_process: tuple[int, str, str]) -> dict[str, Any]:
    """把 verify_agents 进程输出转换为结构化报告。

    Args:
        tuple_process: run_script 返回的退出码、标准输出与标准错误。

    Returns:
        标准输出 JSON，或在无 JSON 时包含标准错误的回退报告。
    """

    # 元组第二项是 verify_agents 的机器可读标准输出。
    str_standard_output = tuple_process[1]  # 验证器标准输出

    # 元组第三项提供启动或解析失败时的诊断文本。
    str_standard_error = tuple_process[2]  # 验证器标准错误

    # 非空标准输出按公开 JSON 合同解析。
    if str_standard_output.strip():

        # 返回真实验证器报告供案例断言检查错误类型。
        return json.loads(str_standard_output)

    # 空输出路径保留 stderr，确保失败详情不会在评估结果中丢失。
    return {"errors": [str_standard_error]}

# 缺失路由场景只篡改渲染文本并执行一次验证器。
def verify_missing_language_routing(
    path_agents: Path,
    str_agents_text: str,
    path_project: Path,
) -> dict[str, Any]:
    """验证删除脚本技能名称后根规则会被拒绝。

    Args:
        path_agents: 待篡改的根 AGENTS 文件。
        str_agents_text: 渲染器生成的完整原始规则文本。
        path_project: verify_agents 检查的隔离项目根。

    Returns:
        删除路由语义后的结构化验证报告。
    """

    # 只替换脚本技能名称，保留其他治理文本以定位单一缺失原因。
    str_missing_text = str_agents_text.replace(  # 缺少脚本技能路由的根规则文本
        "readable-script-generator",  # 必需脚本技能名称
        "script helper",  # 不满足治理合同的泛化替代文本
    )

    # 写入单点篡改文本供真实验证器检查。
    path_agents.write_text(str_missing_text, encoding="utf-8")

    # 公开验证命令应报告 language skill routing 缺失。
    tuple_process = run_script(  # 缺失路由规则的验证器进程输出组
        "verify_agents.py",  # 根规则验证入口
        path_project,  # 已篡改规则的隔离项目
        cwd=REPO_ROOT,  # 使用当前验证实现
    )

    # 统一解析函数保留 JSON 报告或 stderr 回退诊断。
    return parse_verify_process(tuple_process)

# 弱化配置场景恢复原始规则后只修改 Python 路由配置源。
def verify_weakened_language_config(
    path_agents: Path,
    str_agents_text: str,
    path_config: Path,
    dict_config: dict[str, Any],
    path_project: Path,
) -> dict[str, Any]:
    """验证把 Python 路由弱化为通用助手后配置会被拒绝。

    Args:
        path_agents: 用于恢复原始渲染文本的根 AGENTS 文件。
        str_agents_text: 未篡改的完整根规则文本。
        path_config: 语言技能路由配置源路径。
        dict_config: 渲染器写出的原始配置载荷。
        path_project: verify_agents 检查的隔离项目根。

    Returns:
        弱化 Python 路由配置后的结构化验证报告。
    """

    # 恢复原始根规则以隔离配置源弱化这一单一变量。
    path_agents.write_text(str_agents_text, encoding="utf-8")

    # JSON 往返创建深副本，避免修改原始配置证据。
    dict_weakened_config = json.loads(  # 允许安全篡改的配置副本
        json.dumps(dict_config, ensure_ascii=False)  # 保留中文路由文本
    )

    # Python 路由被替换为不满足双技能合同的泛化指导。
    dict_weakened_config.get("coding_behavior", {}).get("language_skill_routing", {})[  # 待弱化的路由映射
        "python"  # Python 任务路由键
    ] = "Python 任务使用通用代码助手。"

    # 写回弱化配置供真实验证器发现源配置违约。
    path_config.write_text(
        json.dumps(dict_weakened_config, ensure_ascii=False, indent=2),  # 可读的弱化配置文本
        encoding="utf-8",  # 配置源统一编码
    )

    # 验证器应拒绝 coding_behavior.language_skill_routing 弱化。
    tuple_process = run_script(  # 弱化配置的验证器进程输出组
        "verify_agents.py",  # 根规则与配置验证入口
        path_project,  # 含弱化配置的隔离项目
        cwd=REPO_ROOT,  # 以当前验证器检查配置源弱化
    )

    # 统一解析函数保留结构化错误供案例断言。
    return parse_verify_process(tuple_process)

# 证据助手执行渲染、正常验证和两个单点破坏测试。
def collect_language_routing_evidence() -> dict[str, Any]:
    """收集语言技能路由的渲染与负向验证证据。

    Args:
        None: 本函数自行创建并释放隔离项目，不接收外部参数。

    Returns:
        包含渲染文本、配置和三份验证报告的证据映射。
    """

    # 临时工作区隔离生成规则与两次故意篡改。
    with tempfile.TemporaryDirectory() as str_temporary_directory:

        # workspace 子目录模拟包含 Python 源码的普通项目。
        path_project = Path(str_temporary_directory) / "workspace"  # 语言路由评估项目根

        # 创建项目根与源码目录供渲染器进行语言发现。
        path_project.mkdir()

        # 源码目录为语言发现提供明确的 Python 文件位置。
        (path_project / "src").mkdir()

        # 最小 Python 文件触发 Python 与脚本双技能路由规则生成。
        (path_project / "src" / "main.py").write_text(
            "print('demo')\n",  # 可解析的最小 Python 源码
            encoding="utf-8",  # 测试源码统一编码
        )

        # write 模式生成根规则和 global-rule-overrides 配置源。
        tuple_render = run_script(  # 根规则渲染进程输出组
            "render_agents.py",  # 根规则渲染入口
            path_project,  # 含 Python 源码的隔离项目
            "--write",  # 将规则与配置写入项目
            cwd=REPO_ROOT,  # 使用当前渲染实现
        )

        # 根规则路径用于读取原文并执行单点篡改。
        path_agents = path_project / "AGENTS.md"  # 渲染后的根规则路径

        # 成功渲染后读取完整规则；缺失文件保留空文本供断言失败。
        str_agents_text = (  # 渲染后的根规则文本
            path_agents.read_text(encoding="utf-8", errors="ignore")  # 成功渲染后的完整规则
            if path_agents.exists()  # 仅在渲染器真正写出文件时读取
            else ""  # 缺失文件保留空文本以触发能力检查失败
        )

        # 未篡改规则应通过公开验证器。
        dict_verify = run_json_script(  # 原始语言路由规则验证报告
            "verify_agents.py",  # 未篡改规则的公开验证入口
            path_project,  # 未篡改的隔离项目
            cwd=REPO_ROOT,  # 以当前实现确认完整输出政策可被接受
        )

        # 删除脚本技能名称后验证器必须拒绝缺失路由语义。
        dict_missing_verify = verify_missing_language_routing(  # 缺失路由负向报告
            path_agents,  # 待篡改根规则路径
            str_agents_text,  # 原始规则文本
            path_project,  # 删除路由文本后的验证目标
        )

        # 配置源路径承载渲染器写出的语言技能路由合同。
        path_config = path_project / ".agents" / "global-rule-overrides.json"  # 编码行为配置源

        # 缺失配置时保留空映射，使配置写入检查明确失败。
        dict_config = (  # 原始编码行为配置
            json.loads(path_config.read_text(encoding="utf-8"))  # 解析渲染器写出的配置
            if path_config.exists()  # 仅在配置文件存在时读取
            else {}  # 缺失配置保留空映射以使检查失败
        )

        # 弱化 Python 路由配置后验证器必须报告配置源违约。
        dict_weakened_verify = verify_weakened_language_config(  # 弱化配置负向报告
            path_agents,  # 恢复原始规则的文件路径
            str_agents_text,  # 原始根规则文本
            path_config,  # 语言路由配置源路径
            dict_config,  # 原始配置证据
            path_project,  # 弱化配置后的验证目标
        )

    # 临时目录释放后仅返回纯文本和结构化证据。
    return {
        "render_code": tuple_render[0],  # 根规则渲染退出码
        "render_stderr": tuple_render[2],  # 根规则渲染错误诊断
        "agents_text": str_agents_text,  # 完整原始根规则文本
        "verify": dict_verify,  # 原始规则验证报告
        "missing_verify": dict_missing_verify,  # 删除脚本技能名称后的拒绝证据
        "weakened_verify": dict_weakened_verify,  # Python 路由改为通用助手后的拒绝证据
        "config": dict_config,  # 渲染器写出的原始配置
    }

# 公开案例将多层语言路由证据转换为稳定能力键。
def case_language_skill_routing_contract(
    case: dict[str, Any],
    _helper: EvalFixtures,
) -> dict[str, Any]:
    """验证语言技能路由能够生成、验证并拒绝两类弱化。

    Args:
        case: 当前评估案例定义。
        _helper: 为统一案例签名保留但本场景无需使用的夹具助手。

    Returns:
        包含渲染、正向验证与负向破坏检查的案例结果。
    """

    # 隔离场景固化渲染文本、配置源和三份验证报告。
    dict_evidence = collect_language_routing_evidence()  # 语言技能路由分层证据

    # 两类负向报告分别证明渲染文本和配置源都受治理。
    list_missing_errors = dict_evidence["missing_verify"].get("errors", [])  # 缺失路由错误列表

    # 配置弱化错误应精确指向语言技能路由配置键。
    list_weakened_errors = dict_evidence["weakened_verify"].get("errors", [])  # 弱化配置错误列表

    # 正向检查覆盖规则生成、配置写入、正常接受与双重拒绝。
    dict_with_checks = {  # 语言技能路由合同检查
        "render_succeeded": dict_evidence["render_code"] == 0,  # 根规则渲染是否成功
        "rendered_language_skill_routing": "## Coding Behavior Baseline"  # 是否生成全局编码行为章节
        in dict_evidence["agents_text"]  # 全局基线章节是否出现
        or "## Local conventions" in dict_evidence["agents_text"],  # 或项目局部约定章节
        "policy_rules": all(  # 是否包含全部双技能路由语义
            str_snippet in dict_evidence["agents_text"]  # 当前必需片段是否出现
            for str_snippet in REQUIRED_LANGUAGE_ROUTING_SNIPPETS  # 遍历治理要求的路由片段
        ),
        "verify_accepts_policy": dict_evidence["verify"].get("errors") == [],  # 原始规则是否被接受
        "verify_rejects_missing_policy": bool(list_missing_errors)  # 删除脚本技能后是否产生错误
        and any("language skill routing" in str_item for str_item in list_missing_errors),  # 错误是否命中路由语义
        "verify_rejects_weakened_policy": bool(list_weakened_errors)  # 弱化 Python 配置后是否产生错误
        and any(  # 错误是否命中配置源键
            "coding_behavior.language_skill_routing" in str_item  # 当前错误是否指向路由配置
            for str_item in list_weakened_errors  # 遍历弱化配置错误
        ),
        "config_written": bool(  # 是否写出结构化语言路由配置
            dict_evidence["config"].get("coding_behavior", {}).get("language_skill_routing")  # 双技能路由映射
        ),
    }

    # 无治理基线不能保证任一双技能路由能力。
    dict_without_checks = {  # 无技能路径的语言路由对照
        str_name: False  # 当前路由能力在朴素生成中缺失
        for str_name in dict_with_checks  # 对照每项语言路由保证
    }

    # 返回三份报告和渲染 stderr 以定位生成或验证失败。
    return build_case_result(
        case,  # 语言技能路由案例元数据
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "verify": dict_evidence["verify"],  # 未篡改规则验证报告
            "missing_verify": dict_evidence["missing_verify"],  # 删除路由后的拒绝报告
            "weakened_verify": dict_evidence["weakened_verify"],  # 弱化配置后的拒绝报告
            "render_stderr": dict_evidence["render_stderr"],  # 渲染失败诊断
        },
        without_skill_detail={
            "baseline": (
                "unguided baseline may create AGENTS.md but does not lock language-specific "
                "skill routing or reject its removal"
            )  # 无治理生成基线缺陷
        },
    )

# 扩展策略场景从拆分模块显式回导，保持原公开映射稳定。
from eval_runtime_policy_extended_cases import (
    case_codex_token_usage_review_contract,
    case_plan_mode_language_lock_contract,
    case_script_output_policy_contract,
)
