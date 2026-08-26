"""agents-md-generator 技能评估用例实现运行时发布分片。"""

# 延迟注解避免运行时解析评估专用类型。
from __future__ import annotations

# 评估核心显式提供路径、进程、夹具和结构化结果合同。
from eval_runtime_core import (
    Any,
    EvalFixtures,
    Path,
    REPO_ROOT,
    SCRIPTS_PYTHON_DIR,
    SKILL_DIR,

    # 结果构建、序列化和环境模块服务结构化评估证据。
    build_case_result,
    json,
    os,
    run_json_script,
    run_script,

    # 文件复制、子进程和临时目录模块服务安装态隔离场景。
    shutil,
    subprocess,
    sys,
    tempfile,
)

# 开发态评估复用真实发布实现，但不伪造正式远程测试收据。
def load_development_release_runtime() -> Any:
    """加载开发态发布 API 所需的任务模块。

    Args:
        None: 模块位置由当前技能 Python 任务根推导。

    Returns:
        已加载的 manage_docs_release 模块。
    """

    # 文档发布聚合器依赖 common、release 和 verify 等兄弟任务目录。
    for path_task_directory in SCRIPTS_PYTHON_DIR.iterdir():

        # 普通文件不能成为 Python 模块搜索根。
        if not path_task_directory.is_dir():

            # 继续检查其余任务分类目录。
            continue

        # 字符串路径用于与解释器搜索列表精确比较。
        str_task_directory = str(path_task_directory)  # 当前任务目录绝对路径。

        # 已登记目录保持原搜索优先级。
        if str_task_directory in sys.path:

            # 避免重复插入同一路径。
            continue

        # 当前源码任务目录优先于环境中的同名模块。
        sys.path.insert(0, str_task_directory)

    # 动态导入避免模块加载阶段提前修改 sys.path。
    return __import__("manage_docs_release")

# 隔离评估通过底层兼容 API 构建临时发布包。
def run_development_package_release(
    path_project: Path,
    str_version: str,
    path_skill_relative: Path,
) -> dict[str, Any]:
    """在隔离评估仓库执行开发态发布打包。

    Args:
        path_project: 临时受管项目根。
        str_version: 临时发布版本。
        path_skill_relative: 项目内技能相对路径。

    Returns:
        与正式 package-release 相同的结构化结果。
    """

    # 聚合模块公开真实发布实现，默认参数保留开发态兼容。
    module_type_release_runtime = load_development_release_runtime()  # 文档发布聚合运行时。

    # 评估不声明正式发布态，因此不制造远程 pytest receipt。
    return module_type_release_runtime.package_release(
        path_project,  # 临时发布仓库。
        str_version,  # 临时发布版本。
        str(path_skill_relative),  # 项目内技能相对路径文本。
    )

# 污染场景通过底层兼容 API 复核开发态发布产物。
def run_development_release_gate(
    path_project: Path,
    str_version: str,
    path_skill_relative: Path,
    str_phase: str,
) -> dict[str, Any]:
    """在隔离评估仓库执行开发态发布门禁。

    Args:
        path_project: 临时受管项目根。
        str_version: 临时发布版本。
        path_skill_relative: 项目内技能相对路径。
        str_phase: pre 或 post 发布阶段。

    Returns:
        与正式 release-gate 相同的结构化结果。
    """

    # 污染复核与打包共享同一实现来源，避免算法分叉。
    module_type_release_runtime = load_development_release_runtime()  # 污染复核使用的发布运行时。

    # 未声明 required 时底层 API 保持隔离评估所需的开发态语义。
    return module_type_release_runtime.release_gate(
        path_project,  # 已注入禁止内容的隔离仓库。
        str_version,  # 待复核污染产物的版本。
        str(path_skill_relative),  # 污染产物对应的源码路径。
        str_phase,  # 当前评估复核阶段。
        "unspecified",  # 评估不产生真实安装意图。
    )

# 外部项目运行时场景验证治理命令只引用已安装技能。
def workspace_settings_checks(
    dict_verify: dict[str, Any],
    dict_structure: dict[str, Any],
    dict_remote_review: dict[str, Any],
    str_agents: str,
) -> dict[str, bool]:
    """构造工作区设置边界能力断言。

    Args:
        dict_verify: 根级配置漂移的文档验证结果。
        dict_structure: 根级配置漂移的结构门禁结果。
        dict_remote_review: local-only 配置的远程目录审查结果。
        str_agents: 受管项目根规则文本。

    Returns:
        本地、远程和禁止同步边界能力检查。
    """

    # 三类路径分别代表本地、远程和禁止同步配置。
    path_local = Path(".settings") / "project.local.json"  # 合法本地配置相对路径

    # 远程项目配置使用独立文件名，避免覆盖本地参数。
    path_remote = Path(".settings") / "project.remote.json"  # 合法远程配置相对路径

    # 服务清单带 local 后缀，只允许留在开发机。
    path_server_local = Path(".settings") / "server_list.local.json"  # 本地服务清单相对路径

    # 通配规则覆盖 .settings 下所有 local-only JSON 文件。
    str_local_glob = (Path(".settings") / "*.local.json").as_posix()  # 本地配置通配规则

    # 两个布尔值统一表达复合断言使用的阻断事实。
    bool_structure_blocked = not bool(dict_structure.get("approved"))  # 根级漂移是否被结构门禁阻断

    # 远程审查阻断可作为文本规则未渲染时的行为证据。
    bool_remote_blocked = not bool(dict_remote_review.get("approved"))  # 本地配置是否被远程审查阻断

    # 行为与文本任一直接证据成立即可兼容不同规则渲染版本。
    return {  # 工作区设置治理断言
        "verify_or_structure_rejects_root_settings_drift": bool(dict_verify.get("errors"))
        or bool_structure_blocked,
        "remote_review_blocks_local_settings": any(
            "local-only workspace settings" in str_reason
            for str_reason in dict_remote_review.get("reasons", [])
        ),
        "agents_mentions_local_settings_contract": path_local.as_posix() in str_agents
        or bool_structure_blocked,
        "agents_mentions_remote_settings_contract": path_remote.as_posix() in str_agents
        or bool_remote_blocked,
        "agents_mentions_remote_local_block": (
            path_server_local.name in str_agents and str_local_glob in str_agents
        )
        or bool_remote_blocked,
    }

# 设置证据助手构造漂移夹具并运行文档与目录门禁。
def collect_workspace_settings_evidence(
    path_project: Path,
    helper: EvalFixtures,
    path_local_settings: Path,
    path_server_local: Path,
) -> dict[str, Any]:
    """收集工作区设置边界的规则文本和门禁结果。

    Args:
        path_project: 接收设置夹具和门禁产物的隔离项目根。
        helper: 提供受管项目渲染和 Git 提交能力的评估助手。
        path_local_settings: 合法本地项目配置相对路径。
        path_server_local: 禁止远程创建的本地服务清单路径。

    Returns:
        文档验证、结构门禁、远程审查和根规则文本证据。
    """

    # 渲染完整受管规则，使设置合同存在于根 AGENTS.md。
    helper.make_rendered_governed_skill_project(path_project, name="demo-skill")

    # 合法本地配置位于专用 .settings 目录。
    path_settings_dir = path_project / ".settings"  # 工作区设置目录

    # 配置目录由夹具显式创建，避免依赖渲染器副作用。
    path_settings_dir.mkdir(exist_ok=True)

    # 最小空对象足以证明合法路径被结构门禁接受。
    (path_project / path_local_settings).write_text("{}", encoding="utf-8")

    # 同名配置放在仓库根形成必须阻断的结构漂移。
    path_root_local = path_project / path_local_settings.name  # 非法根级本地配置

    # 根级文件与合法文件内容一致，仅路径构成违规。
    path_root_local.write_text("{}", encoding="utf-8")

    # 提交漂移使验证器面对稳定版本库状态。
    helper.git_commit_all(path_project, "add workspace settings drift")

    # 文档验证和结构门禁至少一层必须拒绝根级配置。
    dict_verify = run_json_script(  # 设置漂移文档验证结果
        "manage_docs.py",  # 设置合同所属文档任务入口
        "verify",  # 请求验证治理文档和设置约束
        path_project,  # 包含根级配置漂移的项目
        cwd=REPO_ROOT,  # 使用仓库正式文档运行时
    )

    # 独立结构门禁提供目录合同层的直接阻断证据。
    dict_structure = run_json_script(  # 设置漂移结构门禁结果
        "manage_dirs.py",  # 目录治理入口
        "structure-gate",  # 请求检查现有目录结构
        path_project,  # 同一根级配置漂移项目
        cwd=REPO_ROOT,  # 使用仓库正式目录运行时
    )

    # 远程变更请求故意尝试创建 local-only 服务清单。
    path_change = path_project / "remote-settings.json"  # 远程设置变更请求

    # 单条 create 动作足以触发环境与文件后缀组合规则。
    dict_change = {  # 远程设置目录变更载荷
        "changes": [  # 待审查目录变更列表
            {
                "action": "create",  # 请求创建新配置文件
                "environment": "remote",  # 声明目标是远程工作区
                "path": path_server_local.as_posix(),  # local-only 服务清单路径
            }
        ]
    }

    # 审查入口从真实 JSON 文件读取目录变更请求。
    path_change.write_text(json.dumps(dict_change), encoding="utf-8")

    # 目录审查必须阻断远程环境创建 local-only 文件。
    dict_remote_review = run_json_script(  # 远程本地配置审查结果
        "manage_dirs.py",  # 目录变更审查入口
        "review",  # 请求审查声明式变更
        path_project,  # 受远程设置规则约束的项目
        "--input",  # 指定变更载荷文件
        path_change,  # local-only 远程创建请求
        cwd=REPO_ROOT,  # 从仓库根解析正式审查器
    )

    # 根规则文本提供三类设置边界的人类可读证据。
    str_agents = (path_project / "AGENTS.md").read_text(  # 受管根规则文本
        encoding="utf-8",  # 根规则固定使用 UTF-8
        errors="ignore",  # 夹具读取不因异常字节中断
    )

    # 统一证据映射供公开 case 构造断言和详情。
    return {  # 工作区设置治理证据
        "verify": dict_verify,  # 根级漂移文档验证载荷
        "structure": dict_structure,  # 根级漂移结构门禁载荷
        "remote_review": dict_remote_review,  # local-only 远程审查载荷
        "agents": str_agents,  # 设置边界根规则文本
    }

# 工作区设置场景验证本地配置不会泄漏到远程同步面。
def case_workspace_settings_gate(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估工作区本地设置边界和远程同步阻断合同。

    Args:
        case: 当前评估用例元数据。
        helper: 提供受管项目和 Git 提交夹具的评估助手。

    Returns:
        设置边界治理与弱指导基线的结构化对比结果。
    """

    # 设置相对路径集中定义，避免夹具产生分隔符漂移。
    path_local_settings = Path(".settings") / "project.local.json"  # 合法本地项目配置

    # 远程审查夹具使用具体 local-only 服务清单。
    path_server_local = Path(".settings") / "server_list.local.json"  # 禁止远程同步的本地配置

    # 临时项目隔离根级错误配置和目录审查收据。
    with tempfile.TemporaryDirectory() as tmp:

        # 项目根承载合法配置和故意注入的根级漂移。
        path_project = Path(tmp)  # 工作区设置治理项目根

        # 证据助手在临时目录释放前读取全部生成文件。
        dict_evidence = collect_workspace_settings_evidence(  # 设置边界原始证据集合
            path_project,  # 接收设置夹具的隔离项目
            helper,  # 提供受管渲染和提交能力
            path_local_settings,  # 用于制造根级同名漂移的配置路径
            path_server_local,  # 禁止远程同步的具体文件
        )

    # 文档载荷证明根级配置会触发治理错误。
    dict_verify = dict_evidence["verify"]  # 根级设置漂移文档验证载荷

    # 结构载荷证明目录合同直接拒绝错误位置。
    dict_structure = dict_evidence["structure"]  # 根级设置漂移结构门禁载荷

    # 审查载荷证明远程环境拒绝 local-only 文件。
    dict_remote_review = dict_evidence["remote_review"]  # 本地配置远程审查载荷

    # 根规则文本证明设置边界对编码代理可见。
    str_agents = dict_evidence["agents"]  # 工作区设置合同根规则文本

    # 专用助手将门禁行为与根规则文本组合为能力断言。
    dict_with_checks = workspace_settings_checks(  # 设置边界最终能力检查
        dict_verify,  # 文档验证行为证据
        dict_structure,  # 结构门禁行为证据
        dict_remote_review,  # 远程审查行为证据
        str_agents,  # 根规则文本证据
    )

    # 弱指导基线不具备任何可执行设置边界能力。
    dict_without_checks = {  # 缺少工作区设置治理的历史基线
        str_key: False  # 当前设置治理能力在旧基线中不可用
        for str_key in dict_with_checks  # 完整工作区设置能力名称
    }

    # 三份门禁载荷保留用于定位边界检查缺口。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "verify": dict_verify,
            "structure_gate": dict_structure,
            "remote_review": dict_remote_review,
        },
        without_skill_detail={
            "baseline": (
                "weaker guidance leaves project.local.json at the repository root and does not "
                "block local settings from remote workspaces"
            )
        },
    )

# CLI 执行助手覆盖文档、目录、渲染、设计和评估公开入口。
def run_governance_cli_commands(path_project: Path, path_skill: Path) -> dict[str, tuple[int, str, str]]:
    """运行治理 CLI 冒烟命令并返回标准进程三元组。

    Args:
        path_project: 接受治理命令检查的隔离受管项目根。
        path_skill: 工作目录门禁使用的项目内技能根。

    Returns:
        按公开入口名称组织的退出码、标准输出和错误输出。
    """

    # 文档治理命令覆盖帮助、恢复、记忆和工作目录门禁。
    dict_docs_results = {  # 文档治理 CLI 冒烟结果
        "manage_docs_help": run_script("manage_docs.py", "-h", cwd=REPO_ROOT),  # 帮助入口结果
        "resume_check": run_script(  # 恢复检查入口结果
            "manage_docs.py",  # 恢复检查所属文档任务入口
            "resume-check",  # 请求检查未完成会话状态
            path_project,  # 接受记忆治理检查的项目
            cwd=REPO_ROOT,  # 恢复检查从仓库根加载文档模块
        ),
        "memory_gate": run_script(  # 记忆门禁入口结果
            "manage_docs.py",  # 记忆门禁所属文档任务入口
            "memory-gate",  # 请求检查项目记忆治理状态
            path_project,  # 当前受管项目根
            cwd=REPO_ROOT,  # 从仓库根加载记忆治理依赖
        ),
        "work_folder_gate": run_script(  # 开发工作目录门禁结果
            "manage_docs.py",  # 工作目录门禁所属文档入口
            "work-folder-gate",  # 请求复合开发门禁
            path_project,  # 待检查受管项目
            "--skill-dir",  # 指定项目内技能根
            path_skill,  # 示例技能绝对路径
            "--mode",  # 指定门禁执行模式
            "development",  # 启用日常开发工作目录约束
            cwd=REPO_ROOT,  # 从仓库根加载复合门禁依赖
        ),
    }

    # 其余公开入口覆盖目录、渲染、设计和评估任务。
    dict_other_results = {  # 目录渲染设计评估入口结果
        "structure_gate": run_script(  # 目录结构门禁结果
            "manage_dirs.py",  # 结构检查所属目录任务入口
            "structure-gate",  # 请求检查项目目录合同
            path_project,  # 接受结构合同检查的项目
            cwd=REPO_ROOT,  # 从仓库根解析目录运行时
        ),
        "render_agents": run_script("render_agents.py", path_project, cwd=REPO_ROOT),  # 根规则渲染结果
        "collect_design_profile_help": run_script(  # 设计入口帮助结果
            "collect_design_profile.py",  # 设计画像公开入口
            "--help",  # 仅验证命令行解析能力
            cwd=REPO_ROOT,  # 从仓库根加载设计模块
        ),
        "run_skill_evals_help": run_script(  # 评估入口帮助结果
            "run_skill_evals.py",  # 技能评估公开入口
            "--help",  # 仅验证命令行帮助协议
            cwd=REPO_ROOT,  # 从仓库根加载评估运行时
        ),
    }

    # 合并映射保持调用方既有八入口名称合同。
    return {**dict_docs_results, **dict_other_results}

# CLI 断言助手验证进程启动、规则路由和远程设置阻断。
def governance_cli_checks(
    dict_results: dict[str, tuple[int, str, str]],
    dict_remote_review: dict[str, Any],
    str_agents: str,
    str_skill: str,
) -> dict[str, bool]:
    """构造治理 CLI 与外部项目路由能力检查。

    Args:
        dict_results: 八个治理公开入口的进程结果。
        dict_remote_review: local-only 配置远程目录审查结果。
        str_agents: 外部受管项目根规则文本。
        str_skill: 当前技能入口规则文本。

    Returns:
        入口可启动性、运行时路由和远程阻断能力检查。
    """

    # traceback 检查不要求治理门禁本身返回成功状态。
    dict_clean = {  # 各入口无 Python traceback 检查
        str_name: "Traceback" not in str_stdout  # 标准输出是否无 traceback
        and "Traceback" not in str_stderr  # 错误输出是否无 traceback
        for str_name, (_int_code, str_stdout, str_stderr) in dict_results.items()  # 全部入口结果
    }

    # 文档帮助结果需要额外验证正常退出码。
    tuple_docs_help = dict_results["manage_docs_help"]  # 文档治理帮助进程结果

    # 工作目录结果还需验证输出标识对应正确子命令。
    tuple_work_folder = dict_results["work_folder_gate"]  # 工作目录门禁进程结果

    # 渲染入口应在完整项目夹具上正常退出。
    tuple_render = dict_results["render_agents"]  # 根规则渲染进程结果

    # 设计帮助入口应可脱离具体项目启动。
    tuple_design_help = dict_results["collect_design_profile_help"]  # 设计入口帮助进程结果

    # 评估帮助入口应可独立解析命令行。
    tuple_eval_help = dict_results["run_skill_evals_help"]  # 评估入口帮助进程结果

    # 当前 English skill 入口的 planning trigger 由稳定语义片段约束。
    list_planning_terms = [  # 工作目录规划触发词
        "planning request",  # 规划请求触发语义
        "current workspace",  # 当前工作区范围词
        "repository",  # 当前仓库范围词
        "work folder",  # 当前工作目录范围词
    ]

    # 外部项目文档命令必须引用 Codex 安装技能。
    str_docs_command = (  # 外部项目安装态文档命令
        "python <codex-home>/skills/agents-md-generator/scripts/python/docs/"
        "manage_docs.py resume-check <project>"
    )

    # 外部项目目录审查同样不得引用 vendored 脚本。
    str_dirs_command = (  # 外部项目安装态目录命令
        "python <codex-home>/skills/agents-md-generator/scripts/python/dirs/"
        "manage_dirs.py review <project> --input change.json"
    )

    # 能力映射同时覆盖入口可启动性和外部仓库命令边界。
    return {
        "manage_docs_help_starts": tuple_docs_help[0] == 0 and dict_clean["manage_docs_help"],
        "resume_check_starts": dict_clean["resume_check"],
        "memory_gate_starts": dict_clean["memory_gate"],
        "work_folder_gate_starts": dict_clean["work_folder_gate"]
        and "work-folder-gate" in "".join(tuple_work_folder[1:]),
        "structure_gate_starts": dict_clean["structure_gate"],
        "render_agents_starts": tuple_render[0] == 0 and dict_clean["render_agents"],
        "collect_design_profile_help_starts": tuple_design_help[0] == 0
        and dict_clean["collect_design_profile_help"],
        "run_skill_evals_help_starts": tuple_eval_help[0] == 0
        and dict_clean["run_skill_evals_help"],
        "current_work_folder_planning_trigger": all(str_term in str_skill for str_term in list_planning_terms),
        "external_agents_use_installed_runtime": str_docs_command in str_agents,
        "external_agents_use_installed_dir_runtime": str_dirs_command in str_agents,
        "external_agents_omit_project_local_runtime": "python scripts/manage_docs.py" not in str_agents,
        "remote_contract_mentions_workspace_check": "workspace checks" in str_skill,
        "codebase_memory_choice_is_mandatory": "use_codebase_memory_mcp` (55)" in str_skill,
        "codebase_memory_install_uses_official_release": (
            "manual installation guidance" in str_skill and "never download or execute" in str_skill
        ),
        "codebase_memory_write_gate_is_full_and_persistent": "`full` persistent index" in str_skill,
        "external_agents_render_disabled_codebase_memory_rule": (
            "**Codebase memory MCP:** disabled" in str_agents
        ),
        "remote_review_blocks_local_settings": any(
            "local-only workspace settings" in str_reason
            for str_reason in dict_remote_review.get("reasons", [])
        ),
    }

# CLI 冒烟场景验证治理公开入口在受管项目上可执行。
def case_governance_cli_entrypoint_smoke(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估治理 CLI 入口、外部运行时路由和远程设置审查。

    Args:
        case: 当前评估用例元数据。
        helper: 提供受管项目渲染能力的评估夹具助手。

    Returns:
        CLI 启动与治理路由能力相对无治理基线的对比结果。
    """

    # 临时项目隔离渲染产物与远程目录审查输入。
    with tempfile.TemporaryDirectory() as tmp:

        # 项目根承载受管规则和远程变更请求。
        path_project = Path(tmp)  # CLI 冒烟隔离项目根

        # 渲染夹具提供工作目录门禁需要的项目内技能根。
        tuple_rendered = helper.make_rendered_governed_skill_project(  # CLI 冒烟项目渲染结果
            path_project,  # CLI 场景受管项目根
            name="demo-skill",  # 使用外部技能名称验证安装态路由
        )

        # 渲染结果第一项是项目内示例技能目录。
        path_skill = tuple_rendered[0]  # 工作目录门禁技能根

        # 根规则文本用于验证外部项目安装态命令路由。
        str_agents = (path_project / "AGENTS.md").read_text(  # 外部项目根规则文本
            encoding="utf-8",  # 外部项目规则文本编码
            errors="ignore",  # 静态命令检查采用容错读取
        )

        # 技能入口文本用于验证规划触发词和远程合同。
        str_skill = (SKILL_DIR / "SKILL.md").read_text(  # 当前技能入口规则文本
            encoding="utf-8",  # 技能入口固定使用 UTF-8
            errors="ignore",  # 容错读取仅服务静态合同检查
        )

        # 八个公开入口在同一受管项目上下文中执行。
        dict_results = run_governance_cli_commands(path_project, path_skill)  # CLI 冒烟进程结果

        # 远程审查输入尝试创建明确 local-only 的服务清单。
        path_change = path_project / "remote-local-settings.json"  # 远程设置审查输入路径

        # 声明式载荷只包含一条远程创建动作。
        dict_change = {  # CLI 场景远程设置创建请求
            "changes": [  # CLI 场景目录变更清单
                {
                    "action": "create",  # 声明新增服务清单
                    "environment": "remote",  # 声明目标为远程工作区
                    "path": (Path(".settings") / "server_list.local.json").as_posix(),  # 本地服务清单
                }
            ]
        }

        # 审查器从真实 JSON 文件读取声明式变更。
        path_change.write_text(json.dumps(dict_change), encoding="utf-8")

        # 目录治理必须阻断远程环境创建 local-only 文件。
        dict_remote_review = run_json_script(  # local-only 远程审查结果
            "manage_dirs.py",  # 目录审查公开入口
            "review",  # 请求审查声明式目录变更
            path_project,  # 受远程规则约束的项目
            "--input",  # 指定变更请求文件
            path_change,  # local-only 远程创建载荷
            cwd=REPO_ROOT,  # 使用正式目录审查上下文
        )

    # 有技能断言与全假基线形成确定性能力差异。
    dict_with_checks = governance_cli_checks(  # CLI 与路由能力检查
        dict_results,  # 八个公开入口进程结果
        dict_remote_review,  # 服务清单远程创建审查载荷
        str_agents,  # 安装态命令路由事实文本
        str_skill,  # 规划触发和远程合同事实文本
    )

    # 无治理基线不具备任一入口或路由保证。
    dict_without_checks = {  # 缺少 CLI 治理的历史基线
        str_key: False  # 当前入口治理能力在历史基线中不可用
        for str_key in dict_with_checks  # 完整 CLI 治理能力名称
    }

    # 返回码摘要避免详情重复携带完整标准流。
    dict_returncodes = {  # CLI 入口退出码摘要
        str_name: tuple_result[0]  # 当前入口退出码
        for str_name, tuple_result in dict_results.items()  # 八个公开入口结果
    }

    # 返回码和远程审查载荷保留用于入口级失败诊断。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={"cli_returncodes": dict_returncodes, "remote_review": dict_remote_review},
        without_skill_detail={
            "baseline": (
                "weaker governance lets entrypoints drift, external projects call vendored "
                "runtime scripts, or remote local-only settings pass review"
            )
        },
    )

# 发布夹具助手创建仓库级 harness 和技能内 eval 资产。
def prepare_release_content_fixture(path_project: Path, helper: EvalFixtures) -> tuple[str, Path]:
    """准备 eval 发布内容夹具并初始化受管 Git 仓库。

    Args:
        path_project: 接收发布夹具的隔离项目根。
        helper: 提供所有者技能项目和 Git 初始化能力的评估助手。

    Returns:
        固定夹具版本与技能源码相对路径。
    """

    # 所有者名称与发布版本由 fixture 合同提供，场景不绑定当前发布值。
    str_owner_name = str(helper.fixture_value("names", "owner_skill"))  # 净化场景的 fixture 所有者标识

    # 读取发布版本文本，供隔离发布目录使用。
    str_release_version = str(helper.fixture_value("versions", "release_fixture"))  # fixture 发布版本

    # 所有者技能夹具提供正式发布目录布局。
    path_skill = helper.make_governed_skill_project(  # 待打包技能根
        path_project,  # 接收技能源码的隔离项目
        name=str_owner_name,  # 使用所有者技能名称
    )

    # 仓库级测试 harness 必须留在源码而不进入发布包。
    path_tests = path_project / "tests"  # 仓库级测试目录

    # 仓库测试目录由夹具显式创建。
    path_tests.mkdir(exist_ok=True)

    # 最小 harness 文件仅用于验证发布内容排除策略。
    (path_tests / "run_skill_evals.py").write_text(
        "# repo-local eval harness\n",
        encoding="utf-8",
    )

    # 技能内 eval 配置是允许进入安装包的发布内容。
    path_evals = path_skill / "evals"  # 技能内评估资产目录

    # 技能发布资产目录由夹具显式创建。
    path_evals.mkdir(exist_ok=True)

    # 最小合法配置用于证明 evals 目录允许入包。
    (path_evals / "evals.json").write_text(
        '{"version": 1, "cases": []}\n',
        encoding="utf-8",
    )

    # 自定义 evals 内容覆盖了复制的 role，必须同步 fixture manifest 摘要。
    helper.refresh_runtime_manifest_hashes(path_skill)

    # 初始化受管 Git 历史满足发布命令的干净仓库前提。
    helper.init_governed_git_repo(path_project)

    # 配置版本与相对路径由后续打包和门禁命令共同使用。
    return str_release_version, Path("skills") / str_owner_name

# 发布证据助手打包 eval 资产、执行安装预检并注入测试漂移。
def collect_release_content_evidence(
    path_project: Path,
    helper: EvalFixtures,
) -> dict[str, Any]:
    """收集 eval 发布内容与安装合同证据。

    Args:
        path_project: 承载源码与版本化发布目录的隔离项目根。
        helper: 提供所有者项目发布夹具的评估助手。

    Returns:
        打包、安装、收据、发布门禁和 eval 入包事实。
    """

    # 夹具助手返回两条发布命令共享的版本和技能路径。
    tuple_fixture = prepare_release_content_fixture(path_project, helper)  # 发布内容夹具参数

    # 第一项固定版本化发布目录名称。
    str_version = tuple_fixture[0]  # 隔离发布夹具版本

    # 第二项提供发布命令的源码相对路径参数。
    path_skill_relative = tuple_fixture[1]  # 技能源码相对路径

    # 开发态 API 生成版本化发布目录及收据，不伪造远程测试证据。
    dict_initial_package = run_development_package_release(  # 首次发布包与收据结果。
        path_project,  # 承载技能源码与发布目录的所有者项目根。
        str_version,  # 固定隔离夹具版本。
        path_skill_relative,  # 待复制进版本化目录的技能源码根。
    )

    # 安装预检只验证版本化发布目录，不写入真实技能安装位置。
    path_release = path_project / "dist" / f"agents-md-generator-{str_version}"  # 版本化发布目录

    # skip 目标仍执行收据和内容策略验证。
    dict_install = run_json_script(  # skip 目标安装预检结果
        "install_skill.py",  # 发布包安装入口
        path_release,  # 刚生成的版本化发布目录
        "--target",  # 指定安装目标参数
        "skip",  # 仅验证而不写入安装目录
        cwd=REPO_ROOT,  # 从仓库根加载安装运行时
    )

    # 发布收据必须列出技能内 eval 配置。
    path_receipt = path_release / "RELEASE_RECEIPT.json"  # 发布收据路径

    # 解析收据后可在临时目录释放后继续检查文件清单。
    dict_receipt = json.loads(path_receipt.read_text(encoding="utf-8"))  # 发布收据载荷

    # 发布包内注入 tests 文件，验证 post 门禁拒绝开发内容漂移。
    path_blocked = path_release / "tests" / "test_demo.py"  # 故意注入的禁止内容

    # 创建禁止目录以模拟发布后人工污染。
    path_blocked.parent.mkdir(parents=True, exist_ok=True)

    # 最小测试文件足以触发开发内容策略。
    path_blocked.write_text("# tests\n", encoding="utf-8")

    # post 阶段复核必须发现发布目录已偏离收据和内容合同。
    dict_release_gate = run_development_release_gate(  # 注入测试内容后的发布门禁结果。
        path_project,  # 含受污染发布目录的项目。
        str_version,  # 与打包阶段保持同一版本。
        path_skill_relative,  # agents-md-generator 相对路径。
        "post",  # 检查已生成发布目录。
    )

    # 统一映射供断言和详情复用。
    return {
        "package": dict_initial_package,
        "install": dict_install,
        "receipt": dict_receipt,
        "release_gate": dict_release_gate,
        "evals_included": (path_release / "evals" / "evals.json").is_file(),
    }

# 发布内容场景验证 eval 资产进入发布包并支持安装态执行。
def case_release_content_evals_install_contract(
    case: dict[str, Any],
    helper: EvalFixtures,
) -> dict[str, Any]:
    """评估 eval 发布资产、安装预检和开发内容阻断合同。

    Args:
        case: 当前评估用例元数据。
        helper: 提供发布内容夹具的评估助手。

    Returns:
        eval 发布安装闭环与旧发布基线的结构化对比结果。
    """

    # 临时项目隔离版本化发布目录和故意注入的测试漂移。
    with tempfile.TemporaryDirectory() as tmp:

        # 项目根承载源码、Git 历史和 dist 发布目录。
        path_project = Path(tmp)  # 发布内容场景项目根

        # 所有发布文件事实必须在临时目录释放前固化。
        dict_evidence = collect_release_content_evidence(path_project, helper)  # 发布内容证据

    # 打包载荷证明版本化目录生成成功。
    dict_package = dict_evidence["package"]  # 发布包生成载荷

    # 安装载荷证明发布内容策略接受 eval 资产。
    dict_install = dict_evidence["install"]  # skip 目标安装预检载荷

    # 收据载荷提供发布包文件清单事实。
    dict_receipt = dict_evidence["receipt"]  # 发布文件收据载荷

    # post 门禁载荷证明注入 tests 后会被阻断。
    dict_release_gate = dict_evidence["release_gate"]  # 测试漂移发布门禁载荷

    # 布尔事实在临时发布目录释放前已经计算。
    bool_evals_included = bool(dict_evidence["evals_included"])  # eval 配置实际入包事实

    # 收据相对路径列表用于检查 eval 配置登记。
    list_receipt_paths = [  # 发布收据文件相对路径
        dict_item.get("path", "")  # 当前收据条目的相对路径
        for dict_item in dict_receipt.get("files", [])  # 发布收据全部文件条目
    ]

    # eval 配置相对路径使用路径对象构造，避免硬编码分隔符。
    str_evals_path = (Path("evals") / "evals.json").as_posix()  # 发布态 eval 配置路径

    # 有技能路径证明 eval 入包、收据登记、可安装和测试漂移阻断。
    dict_with_checks = {  # eval 发布安装能力断言
        "packaging_passes": bool(dict_package.get("ok")),  # 发布包是否生成成功
        "evals_included_in_dist": bool_evals_included,  # eval 配置是否实际入包
        "receipt_lists_evals": str_evals_path in list_receipt_paths,  # 收据是否登记 eval 配置
        "install_skip_accepts_release": bool(dict_install.get("release_content_policy_ok")),  # 安装策略是否接受
        "release_gate_rejects_test_drift": any(  # post 门禁是否拒绝测试内容
            "forbidden development content" in str_error.lower()  # 当前错误是否命中禁止内容
            for str_error in dict_release_gate.get("errors", [])  # 发布门禁返回的全部错误
        ),
    }

    # 旧发布基线不提供任一 eval 安装闭环能力。
    dict_without_checks = {  # 缺少 eval 发布合同的历史基线
        str_key: False  # 当前发布能力在旧基线中不可用
        for str_key in dict_with_checks  # 完整 eval 发布安装能力名称
    }

    # 三阶段载荷保留用于定位打包、安装或 post 门禁失败。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "package": dict_package,
            "install": dict_install,
            "release_gate": dict_release_gate,
        },
        without_skill_detail={
            "baseline": (
                "older policy treated evals as forbidden or source-only and did not prove "
                "installable release acceptance"
            )
        },
    )

# 净化夹具助手写入正则代码常量和真实文档秘密。
def prepare_sanitizer_fixture(path_project: Path, helper: EvalFixtures) -> Path:
    """创建发布净化边界夹具并初始化 Git 仓库。

    Args:
        path_project: 接收净化夹具的隔离项目根。
        helper: 提供所有者技能项目和 Git 初始化能力的评估助手。

    Returns:
        待发布的 agents-md-generator 技能根。
    """

    # 净化场景从 fixture 合同读取与其他发布场景不同的所有者名称。
    str_owner_name = str(helper.fixture_value("names", "owner_skill"))  # fixture 所有者名称

    # 所有者项目夹具提供 scripts 和 references 发布目录。
    path_skill = helper.make_governed_skill_project(  # 净化场景技能根
        path_project,  # 隔离项目根
        name=str_owner_name,  # 所有者技能名称
    )

    # 正则代码包含看似秘密赋值的常量名，但必须保持原始语义。
    list_regex_lines = [  # 可编译正则工具源码行
        "import re",  # 正则工具依赖
        "",  # 导入与常量之间的空行
        "SECRET_RE = re.compile(",  # 待保护的秘密检测正则常量起始行
        '    r"(?i)(api[_-]?key|secret)\\s*[:=]\\s*(?!<REDACTED_)[^\\s,;]+"',  # 秘密赋值匹配表达式
        ")",  # 正则编译调用结束行
        "",  # 常量与函数定义之间的空行
        "def contains_secret(text: str) -> bool:",  # 正则工具公开函数签名
        "    return bool(SECRET_RE.search(text))",  # 正则搜索布尔返回语句
    ]

    # 正则源码落盘后供发布净化器处理。
    path_regex = path_skill / "scripts" / "regex_tool.py"  # 正则工具源码路径

    # 保留完整源码换行以支持后续编译验证。
    path_regex.write_text("\n".join(list_regex_lines) + "\n", encoding="utf-8")

    # 文档中的真实访问令牌必须由打包净化器替换。
    path_secrets = path_skill / "references" / "secrets.md"  # 含真实秘密的参考文档

    # 写入真实令牌以验证发布净化而非人工预脱敏。
    path_secrets.write_text("ACCESS_TOKEN = actual-secret-token\n", encoding="utf-8")

    # 干净受管历史满足 package-release 前置门禁。
    helper.init_governed_git_repo(path_project)

    # 调用方继续执行打包、安装预检和编译验证。
    return path_skill

# 净化证据助手执行打包、安装预检和发布脚本编译。
def collect_sanitizer_evidence(path_project: Path, helper: EvalFixtures) -> dict[str, Any]:
    """收集发布净化器对代码与文档差异处理的证据。

    Args:
        path_project: 承载净化场景的隔离项目根。
        helper: 提供所有者项目与 Git 夹具能力的评估助手。

    Returns:
        包含打包、安装、文本、收据与编译结果的证据映射。
    """

    # 夹具初始化后使用 fixture 版本生成隔离发布目录。
    prepare_sanitizer_fixture(path_project, helper)

    # 配置版本保证发布目录与收据断言稳定。
    str_version = str(helper.fixture_value("versions", "release_fixture"))  # fixture 净化场景版本

    # 所有者技能路径作为 package-release 的显式输入。
    str_owner_name = str(helper.fixture_value("names", "owner_skill"))  # 净化发布的 fixture 所有者标识

    # 使用仓库布局的技能相对目录拼接发布源路径。
    path_skill_relative = Path("skills") / str_owner_name  # 所有者技能相对路径

    # 开发态 API 生成净化与安装验证所需的版本目录。
    dict_package = run_development_package_release(  # 净化场景发布包生成结果。
        path_project,  # 隔离所有者项目根。
        str_version,  # 固定净化场景版本。
        path_skill_relative,  # 净化夹具中的发布源目录。
    )

    # 打包结果所在目录是安装与取证的共同输入。
    path_release = path_project / "dist" / f"{str_owner_name}-{str_version}"  # 净化产物取证根

    # 安装 skip 模式验证发布包策略，不修改本地安装态。
    dict_install = run_json_script(  # 净化后发布包安装预检结果
        "install_skill.py",  # 技能安装入口
        path_release,  # 已净化版本目录
        "--target",  # 安装目标参数
        "skip",  # 仅执行发布策略预检
        cwd=REPO_ROOT,  # 从仓库根调用真实安装入口
    )

    # 发布态正则文件用于检查代码常量保真。
    path_regex = path_release / "scripts" / "regex_tool.py"  # 发布态正则工具路径

    # 发布态参考文档用于检查真实令牌脱敏。
    path_secrets = path_release / "references" / "secrets.md"  # 发布态秘密文档路径

    # 固化正则源码，避免临时目录释放后丢失证据。
    str_regex = path_regex.read_text(encoding="utf-8")  # 发布态正则工具文本

    # 固化参考文档以断言脱敏后的公开文本。
    str_secrets = path_secrets.read_text(encoding="utf-8")  # 发布态秘密文档文本

    # 收据路径定位打包器生成的审计载荷。
    path_receipt = path_release / "RELEASE_RECEIPT.json"  # 净化审计文件位置

    # 审计载荷解析后可精确检查净化记录。
    dict_receipt = json.loads(path_receipt.read_text(encoding="utf-8"))  # 净化审计结构

    # py_compile 直接证明净化后的 Python 文件仍具备合法语法。
    process_compile = subprocess.run(  # 发布态正则工具编译结果
        [sys.executable, "-m", "py_compile", str(path_regex)],  # 隔离解释器编译命令
        cwd=path_project,  # 在隔离项目内生成编译缓存
        text=True,  # 将编译诊断保留为文本
        capture_output=True,  # 捕获编译失败诊断
        check=False,  # 由案例断言解释非零退出码
    )

    # 所有文本和进程事实在临时目录释放前固化。
    return {
        "package": dict_package,
        "install": dict_install,
        "regex_text": str_regex,
        "secrets_text": str_secrets,
        "receipt": dict_receipt,
        "compile_code": process_compile.returncode,
        "compile_stderr": process_compile.stderr,
    }

# 发布净化场景验证正则常量保持代码语义且文档秘密被脱敏。
def case_release_sanitizer_regex_constant(
    case: dict[str, Any],
    helper: EvalFixtures,
) -> dict[str, Any]:
    """评估发布净化器保护代码常量并脱敏真实文档秘密。

    Args:
        case: 当前评估案例定义。
        helper: 提供隔离项目与治理夹具能力的评估助手。

    Returns:
        包含有技能与无技能对照检查的案例结果。
    """

    # 临时项目隔离含真实秘密的源码和净化后发布目录。
    with tempfile.TemporaryDirectory() as tmp:

        # 临时根承载本案例全部可释放资产。
        path_project = Path(tmp)  # 发布净化场景项目根

        # 临时目录存续期间完成打包、安装预检和证据固化。
        dict_evidence = collect_sanitizer_evidence(path_project, helper)  # 发布净化证据

    # 从固化证据中提取收据以检查净化文件记录。
    dict_receipt = dict_evidence["receipt"]  # 案例断言使用的净化审计结构

    # 排序后的 JSON 文本允许稳定检查目标文件路径。
    str_sanitization = json.dumps(dict_receipt.get("sanitization", {}), sort_keys=True)  # 净化记录文本

    # POSIX 相对路径与跨平台收据格式保持一致。
    str_reference_path = (Path("references") / "secrets.md").as_posix()  # 秘密文档发布路径

    # 有技能路径同时证明代码保真、文档脱敏和安装接受。
    dict_with_checks = {  # 发布净化正向能力断言
        "packaging_passes": bool(dict_evidence["package"].get("ok")),  # 打包是否成功
        "regex_constant_preserved": "SECRET_RE = re.compile(" in dict_evidence["regex_text"]  # 正则常量是否保留
        and "SECRET_RE = <REDACTED_API_KEY>" not in dict_evidence["regex_text"],  # 常量是否未被误脱敏
        "dist_script_compiles": dict_evidence["compile_code"] == 0,  # 发布脚本是否可编译
        "real_token_redacted": "ACCESS_TOKEN = <REDACTED_API_KEY>" in dict_evidence["secrets_text"],  # 文档令牌是否脱敏
        "receipt_records_redaction": str_reference_path in str_sanitization,  # 收据是否登记脱敏文件
        "install_skip_accepts_release": bool(  # 安装策略是否接受净化发布包
            dict_evidence["install"].get("release_content_policy_ok")  # 发布内容策略状态
        ),
    }

    # 朴素赋值净化基线不具备任一安全发布保证。
    dict_without_checks = {  # 不具备净化能力的历史基线
        str_key: False  # 基线不满足当前安全发布保证
        for str_key in dict_with_checks  # 覆盖全部正向能力键
    }

    # 打包、安装、编译和净化收据共同保留失败诊断。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "package": dict_evidence["package"],
            "install": dict_evidence["install"],
            "compile_stderr": dict_evidence["compile_stderr"],
            "sanitization": dict_receipt.get("sanitization", {}),
        },
        without_skill_detail={
            "baseline": (
                "a naive assignment sanitizer redacts SECRET_RE constants and can ship "
                "uncompilable release scripts"
            )
        },
    )
