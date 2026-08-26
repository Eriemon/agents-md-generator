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

# 脚本输出策略片段覆盖配置来源、可扩展 Kind 和三类输出格式。
REQUIRED_SCRIPT_OUTPUT_SNIPPETS = (  # 根规则必须生成的输出策略语义
    "Configuration source:",  # 输出策略配置来源
    "the `Kind` catalog is read",  # Kind 扩展边界
    "`> INFO: [{kind}]`",  # 过程信息格式
    "`> WARNING: [{kind}]`",  # 警告格式
    "`> ERR: [{kind}]`",  # 错误格式
    "`--quiet`",  # 过程信息静默开关
    "machine-readable output has no prefix",  # 机器输出例外
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

# 输出策略评估自建最小 Codex home，避免宿主全局治理状态改变案例结果。
def isolated_script_policy_environment(path_temporary_root: Path) -> dict[str, str]:
    """创建脚本输出策略案例使用的隔离代理环境。

    Args:
        path_temporary_root: 当前案例可自动清理的临时根目录。

    Returns:
        仅覆盖 CODEX_HOME 的子进程环境映射。
    """

    # 隔离 Codex home 承载全局基线和可读语言技能存在性证据。
    path_codex_home = path_temporary_root / "codex-home"  # 当前评估专用 Codex home。

    # 技能目录一次创建后供两个最小入口共同使用。
    path_skills_root = path_codex_home / "skills"  # 隔离技能发现根目录。

    # 父级目录必须先存在，后续写入不会访问真实用户 home。
    path_skills_root.mkdir(parents=True)

    # 当前技能发布的全局模板是 verify_agents 正向验证的唯一基线来源。
    path_global_template = SKILL_DIR / "assets" / "templates" / "global-codex-agents.md"  # 当前全局基线模板。

    # 复制受管模板到隔离 home，不修改真实全局 AGENTS。
    (path_codex_home / "AGENTS.md").write_text(  # 隔离全局 AGENTS 文件。
        path_global_template.read_text(encoding="utf-8"),  # 当前技能发布的全局基线正文。
        encoding="utf-8",  # 隔离规则文件统一编码。
    )

    # 两个语言技能的根入口足以证明路由能力存在，不复制真实安装内容。
    for str_skill_name in ("readable-python-generator", "readable-script-generator"):

        # 每个最小技能使用标准 Codex skill 目录布局。
        path_readable_skill = path_skills_root / str_skill_name  # 当前可读语言技能夹具目录。

        # 创建独立目录后写入根 SKILL.md 存在性证据。
        path_readable_skill.mkdir()

        # 最小入口只用于安装态发现，不参与技能行为执行。
        (path_readable_skill / "SKILL.md").write_text(  # 当前可读技能入口文件。
            f"---\nname: {str_skill_name}\ndescription: isolated eval fixture\n---\n",  # 最小技能元数据。
            encoding="utf-8",  # 技能入口统一编码。
        )

    # 同时覆盖两个平台用户根变量，避免宿主 AGENT_HOME 抢占隔离 CODEX_HOME。
    return {
        "CODEX_HOME": str(path_codex_home),
        "AGENT_HOME": str(path_codex_home),
    }

# 缺失输出策略场景只篡改渲染文本并执行一次验证器。
def verify_missing_script_output_policy(
    path_agents: Path,
    str_agents_text: str,
    path_project: Path,
    dict_environment: dict[str, str],
) -> tuple[int, dict[str, Any]]:
    """验证删除 Kind 配置来源后根规则会被拒绝。

    Args:
        path_agents: 待篡改的根 AGENTS 文件。
        str_agents_text: 渲染器生成的完整原始规则文本。
        path_project: verify_agents 检查的隔离项目根。
        dict_environment: 正向与负向验证共享的隔离环境。

    Returns:
        验证器退出码与结构化拒绝报告。
    """

    # 单点替换 Kind 来源规则以隔离缺失策略诊断。
    str_missing_text = str_agents_text.replace(  # 缺少 Kind 来源约束的根规则
        "the `Kind` catalog is read from this JSON",  # 必需配置来源语义
        "the Kind catalog source is missing",  # 故意不满足合同的替代文本
    )

    # 写入篡改规则供真实验证器检查。
    path_agents.write_text(str_missing_text, encoding="utf-8")

    # 公开验证命令应拒绝缺失 Script Output Policy 语义。
    tuple_process = run_script(  # 缺失输出策略的验证器进程输出组
        "verify_agents.py",  # Kind 来源缺失测试的验证入口
        path_project,  # 已删除 Kind 来源语义的项目
        cwd=REPO_ROOT,  # 以当前验证器检查 Kind 来源删除
        env=dict_environment,  # 缺失 Kind 场景沿用已种入的全局基线
    )

    # 返回退出码和统一解析的错误报告。
    return tuple_process[0], parse_verify_process(tuple_process)

# 弱化策略测试恢复原始规则后破坏 warning 格式配置。
def verify_weakened_script_output_config(
    path_agents: Path,
    str_agents_text: str,
    path_config: Path,
    dict_config: dict[str, Any],
    path_project: Path,
    dict_environment: dict[str, str],
) -> tuple[int, dict[str, Any]]:
    """验证移除 warning 引用前缀后配置源会被拒绝。

    Args:
        path_agents: 用于恢复原始渲染文本的根 AGENTS 文件。
        str_agents_text: 未篡改的完整根规则文本。
        path_config: 脚本输出策略配置源路径。
        dict_config: 渲染器写出的原始配置载荷。
        path_project: verify_agents 检查的隔离项目根。
        dict_environment: 正向与负向验证共享的隔离环境。

    Returns:
        验证器退出码与结构化拒绝报告。
    """

    # 恢复原始根规则以隔离配置格式弱化这一单一变量。
    path_agents.write_text(str_agents_text, encoding="utf-8")

    # JSON 往返创建可修改副本并保留原始配置证据。
    dict_weakened_config = json.loads(  # 待弱化的脚本输出配置副本
        json.dumps(dict_config, ensure_ascii=False)  # 保留中文配置值
    )

    # warning 格式故意移除 Markdown 引用前缀以触发策略校验。
    dict_weakened_config.get("script_output_policy", {}).setdefault("format", {})[  # 待破坏的输出格式映射
        "warning"  # warning 输出模板键
    ] = "WARNING [{kind}]"

    # 写回弱化配置供真实验证器检查格式合同。
    path_config.write_text(
        json.dumps(dict_weakened_config, ensure_ascii=False, indent=2),  # 可读的弱化策略配置
        encoding="utf-8",  # 配置文件统一编码
    )

    # 公开验证命令应报告 script_output_policy 配置错误。
    tuple_process = run_script(  # 弱化输出配置的验证器进程输出组
        "verify_agents.py",  # warning 格式弱化测试的验证入口
        path_project,  # 含弱化 warning 格式的项目
        cwd=REPO_ROOT,  # 以当前验证器检查 warning 模板破坏
        env=dict_environment,  # warning 格式场景沿用同一可读技能发现状态
    )

    # 输出格式负向证据同时保留进程状态和配置诊断。
    return tuple_process[0], parse_verify_process(tuple_process)

# 证据助手执行输出策略渲染、正常验证和两个负向测试。
def collect_script_output_policy_evidence() -> dict[str, Any]:
    """收集脚本输出策略的渲染与负向验证证据。

    Args:
        None: 本函数自行创建并释放隔离项目，不接收外部参数。

    Returns:
        包含规则、配置、退出码和三份验证报告的证据映射。
    """

    # 临时工作区隔离生成规则与两次故意策略弱化。
    with tempfile.TemporaryDirectory() as str_temporary_directory:

        # 临时根同时承载隔离项目和不依赖宿主的 Codex home。
        path_temporary_root = Path(str_temporary_directory)  # 当前输出策略案例临时根。

        # 所有渲染与验证子进程共享同一最小全局治理环境。
        dict_environment = isolated_script_policy_environment(path_temporary_root)  # 当前案例隔离环境。

        # workspace 子目录模拟含 Python 源码的普通项目。
        path_project = path_temporary_root / "workspace"  # 输出策略评估项目根

        # 创建项目根后补充用于语言发现的源码目录。
        path_project.mkdir()

        # src 目录承载触发规则渲染的最小 Python 文件。
        (path_project / "src").mkdir()

        # 最小源码足以触发脚本输出治理规则生成。
        (path_project / "src" / "main.py").write_text(
            "print('demo')\n",  # 触发输出策略生成的最小 Python 程序
            encoding="utf-8",  # 输出策略夹具源码编码
        )

        # write 模式生成输出政策规则和对应 JSON 配置源。
        tuple_render = run_script(  # 输出策略规则渲染进程输出组
            "render_agents.py",  # 输出策略夹具的规则渲染入口
            path_project,  # 等待生成输出政策的隔离项目
            "--write",  # 落盘输出策略规则与配置
            cwd=REPO_ROOT,  # 加载当前输出策略渲染实现
            env=dict_environment,  # 渲染阶段使用隔离全局治理环境
        )

        # 根规则路径服务原文读取与缺失策略篡改。
        path_agents = path_project / "AGENTS.md"  # 输出策略生成规则位置

        # 缺失文件保留空文本，使渲染成功检查与策略检查同时失败。
        str_agents_text = (  # 渲染后的完整根规则
            path_agents.read_text(encoding="utf-8", errors="ignore")  # 含 Kind 与格式语义的规则文本
            if path_agents.exists()  # 输出策略规则文件确实生成时读取
            else ""  # 未生成规则时用空文本暴露失败
        )

        # 原始规则与配置应被公开验证器接受。
        dict_verify = run_json_script(  # 未篡改输出策略验证报告
            "verify_agents.py",  # 原始输出策略的验证入口
            path_project,  # 尚未执行负向篡改的项目
            cwd=REPO_ROOT,  # 以当前验证器建立正向基线
            env=dict_environment,  # 正向验证使用隔离全局治理环境
        )

        # 删除 Kind 来源语义后固化退出码和拒绝报告。
        tuple_missing = verify_missing_script_output_policy(  # 缺失策略负向证据组
            path_agents,  # 删除 Kind 来源语义的规则位置
            str_agents_text,  # 保留全部输出格式的原文
            path_project,  # 缺失策略验证目标
            dict_environment,  # 负向文本验证复用同一隔离环境
        )

        # 配置路径承载渲染器写出的可扩展 Kind 与格式合同。
        path_config = path_project / ".agents" / "global-rule-overrides.json"  # 输出策略配置源

        # 缺失配置保留空映射，使配置写入能力明确失败。
        dict_config = (  # 原始全局规则覆盖配置
            json.loads(path_config.read_text(encoding="utf-8"))  # 解析 Kind 与格式配置块
            if path_config.exists()  # 输出政策配置源存在时读取
            else {}  # 配置未生成时用空映射暴露失败
        )

        # 弱化 warning 格式后固化退出码和拒绝报告。
        tuple_weakened = verify_weakened_script_output_config(  # 弱化格式负向证据组
            path_agents,  # warning 测试前恢复规则的文件位置
            str_agents_text,  # 未删除 Kind 来源的根规则原文
            path_config,  # 待改写 warning 模板的配置文件
            dict_config,  # 保留可扩展 Kind 的原始配置
            path_project,  # 弱化配置验证目标
            dict_environment,  # 负向配置验证复用同一隔离环境
        )

    # 临时目录释放后返回纯文本、整数与结构化报告。
    return {
        "render_code": tuple_render[0],  # 输出策略规则渲染退出码
        "render_stderr": tuple_render[2],  # 输出策略渲染错误诊断
        "agents_text": str_agents_text,  # 包含完整输出政策的根规则原文
        "verify": dict_verify,  # 原始输出策略验证报告
        "missing_code": tuple_missing[0],  # 缺失 Kind 来源规则时的退出码
        "missing_verify": tuple_missing[1],  # 缺失 Kind 来源规则的拒绝报告
        "weakened_code": tuple_weakened[0],  # 弱化 warning 格式时的退出码
        "weakened_verify": tuple_weakened[1],  # 弱化 warning 格式的拒绝报告
        "config": dict_config,  # 渲染器写出的完整配置
    }

# 公开案例验证输出策略的生成、扩展性和负向保护。
def case_script_output_policy_contract(
    case: dict[str, Any],
    _helper: EvalFixtures,
) -> dict[str, Any]:
    """验证脚本输出策略能够生成并拒绝文本或配置弱化。

    Args:
        case: 当前评估案例定义。
        _helper: 为统一案例签名保留但本场景无需使用的夹具助手。

    Returns:
        包含输出策略正向能力与负向拒绝证据的案例结果。
    """

    # 隔离场景固化生成规则、配置源和三份验证报告。
    dict_evidence = collect_script_output_policy_evidence()  # 脚本输出策略分层证据

    # 脚本输出配置包含 Kind 列表和各级别格式模板。
    dict_script_output_config = dict_evidence["config"].get("script_output_policy", {})  # 输出策略配置块

    # 两类负向错误分别证明文本语义和配置格式都受治理。
    list_missing_errors = dict_evidence["missing_verify"].get("errors", [])  # 缺失 Kind 来源错误

    # warning 格式弱化应产生 script_output_policy 配置错误。
    list_weakened_errors = dict_evidence["weakened_verify"].get("errors", [])  # 弱化格式错误

    # 正向检查覆盖渲染、配置扩展、正常接受和双重拒绝。
    dict_with_checks = {  # 脚本输出策略合同检查
        "render_succeeded": dict_evidence["render_code"] == 0,  # 输出策略规则是否成功落盘
        "rendered_policy": all(  # 是否生成全部输出格式语义
            str_snippet in dict_evidence["agents_text"]  # 当前格式或 Kind 语义是否出现
            for str_snippet in REQUIRED_SCRIPT_OUTPUT_SNIPPETS  # 遍历输出策略必需片段
        )
        and (  # 是否存在独立或合并后的策略章节
            "## Script Output Policy" in dict_evidence["agents_text"]  # 独立输出策略章节
            or "## Local conventions" in dict_evidence["agents_text"]  # 项目局部约定章节
        ),
        "config_written": bool(dict_script_output_config),  # 是否写出结构化输出策略配置
        "kind_config_extensible": isinstance(dict_script_output_config.get("kinds"), list)  # Kind 是否由列表配置
        and "Verilator" in dict_script_output_config.get("kinds", []),  # 是否保留可扩展示例 Kind
        "verify_accepts_policy": dict_evidence["verify"].get("errors") == [],  # 原始策略是否被接受
        "verify_rejects_missing_policy": bool(list_missing_errors)  # 删除 Kind 来源后是否产生错误
        and any("script output policy" in str_item.casefold() for str_item in list_missing_errors),  # 是否命中输出策略诊断
        "verify_rejects_weakened_policy": bool(list_weakened_errors)  # 弱化 warning 格式后是否产生错误
        and any("script_output_policy" in str_item for str_item in list_weakened_errors),  # 是否命中配置键诊断
    }

    # 无治理基线不能保证任一可配置输出策略能力。
    dict_without_checks = {  # 无技能路径的输出策略对照
        str_name: False  # 当前策略能力在朴素日志指导中缺失
        for str_name in dict_with_checks  # 对照每项输出策略保证
    }

    # 返回正负验证报告、进程诊断和负向退出码。
    return build_case_result(
        case,  # 脚本输出策略案例元数据
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "verify": dict_evidence["verify"],  # 原始策略验证报告
            "missing_verify": dict_evidence["missing_verify"],  # 删除 Kind 来源后的拒绝报告
            "weakened_verify": dict_evidence["weakened_verify"],  # 弱化 warning 格式后的拒绝报告
            "render_stderr": dict_evidence["render_stderr"],  # 输出策略渲染诊断
            "missing_returncode": dict_evidence["missing_code"],  # 缺失策略验证退出码
            "weakened_returncode": dict_evidence["weakened_code"],  # 弱化配置验证退出码
        },
        without_skill_detail={
            "baseline": (
                "unguided baseline may mention log style but does not render configurable Kind "
                "policy or reject weakened output formats"
            )  # 无治理日志基线缺陷
        },
    )

# Plan Mode 证据助手读取规则、技能参考与三层验证实现。
def collect_plan_language_source_texts() -> dict[str, str]:
    """读取 Plan Mode 默认语言合同的全部权威源码文本。

    Args:
        None: 本函数只读取固定仓库资产，不接收外部参数。

    Returns:
        根规则、技能参考和验证器实现组成的文本映射。
    """

    # 每个键对应 eval 需要独立证明的规则或实现层。
    return {
        "agents": (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"),  # 当前仓库根规则文本
        "skill": (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8"),  # 技能公开工作流文本
        "script_guide": (SKILL_DIR / "references" / "script-guide.md").read_text(encoding="utf-8"),  # 脚本指南文本
        "review_checklist": (SKILL_DIR / "references" / "review-checklist.md").read_text(encoding="utf-8"),  # 审查清单文本
        "verify_entry": script_path("verify_agents.py").read_text(encoding="utf-8"),  # 根规则验证入口源码
        "verify_policy": script_path("verify_agents_policy.py").read_text(encoding="utf-8"),  # 语言策略验证源码
        "verify_scanning": (SCRIPT_DIR / "verify_agents_scanning.py").read_text(encoding="utf-8"),  # 规则扫描实现源码
    }

# 负向夹具只保留通用语言锁，故意缺失 proposed_plan 专项规则。
def collect_missing_plan_language_report() -> dict[str, Any]:
    """执行缺少 Plan Mode 语言锁的根规则验证场景。

    Args:
        None: 本函数自行创建并释放隔离项目，不接收外部参数。

    Returns:
        verify_agents 对缺失 Plan Mode 专项规则的结构化报告。
    """

    # 当前技能版本使负向夹具不会因无关元数据漂移而失败。
    str_current_version = (SKILL_DIR / "VERSION").read_text(encoding="utf-8").strip()  # 当前生成器版本

    # 负向夹具的默认语言从 catalog 读取，避免硬编码 locale alias。
    dict_language_catalog = json.loads(  # 语言 catalog 权威对象
        (SKILL_DIR / "config" / "languages.json").read_text(encoding="utf-8")  # 读取技能语言配置
    )

    # 负向根夹具使用 catalog 默认语言触发 Plan Mode 缺失检查。
    str_default_language = str(  # 负向夹具 conversation 默认语言 ID
        dict_language_catalog["defaults"]["conversation"]  # 读取负向夹具默认语言
    )

    # 临时工作区隔离故意不完整的根规则和控制档案。
    with tempfile.TemporaryDirectory() as str_temporary_directory:

        # workspace 子目录模拟受中文默认语言治理的工程项目。
        path_project = Path(str_temporary_directory) / "workspace"  # Plan Mode 负向项目根

        # 创建项目根与控制档案目录。
        path_project.mkdir()

        # 控制档案目录承载默认语言权威配置。
        (path_project / ".agents").mkdir()

        # 工程配置声明中文，但不自动补写缺失的根规则文本。
        dict_control_profile = {  # Plan Mode 负向项目控制档案
            "kind": "engineering",  # 工程项目类型
            "default_conversation_language": str_default_language,  # 触发默认语言 proposed_plan 专项校验
        }

        # 写入控制档案供验证器读取默认语言要求。
        (path_project / ".agents" / "agents-control.json").write_text(
            json.dumps(dict_control_profile, ensure_ascii=False),  # 序列化 Plan Mode 负向配置
            encoding="utf-8",  # Plan Mode 控制档案编码
        )

        # 根规则只包含通用自然语言锁，故意缺少 proposed_plan 约束。
        list_agents_lines = [  # Plan Mode 负向根规则文本行
            f"<!-- AGENTS-METADATA: agents_version={str_current_version}; "  # 当前 agents 版本元数据
            f"generator_version={str_current_version}; default_language={str_default_language} -->",  # 当前生成器与语言元数据
            "# AGENTS.md",  # 负向夹具根规则标题
            "## Conversation Completion Contract",  # 通用对话合同标题
            f"- All natural-language responses must use the configured default language (`{str_default_language}`) "  # 通用语言锁起始片段
            "unless the user explicitly switches languages.",  # 通用语言锁结束片段
            "",  # 负向根规则结尾换行
        ]

        # 写入缺少 Plan Mode 专项语义的根规则。
        (path_project / "AGENTS.md").write_text(
            "\n".join(list_agents_lines),  # 保持规则逐行结构
            encoding="utf-8",  # Plan Mode 负向规则编码
        )

        # 真实验证器应精确报告缺少 Plan Mode default-language rule。
        dict_verify = run_json_script(  # Plan Mode 语言锁负向验证报告
            "verify_agents.py",  # Plan Mode 专项缺失验证入口
            path_project,  # 仅含通用语言锁的隔离项目
            cwd=REPO_ROOT,  # 加载含专项正则的当前验证实现
        )

    # 返回纯结构化报告供案例检查具体错误消息。
    return dict_verify

# 公开案例验证 Plan Mode 语言锁覆盖文档、实现和真实拒绝行为。
def case_plan_mode_language_lock_contract(
    case: dict[str, Any],
    _helper: EvalFixtures,
) -> dict[str, Any]:
    """验证 proposed_plan 内容受默认语言规则和验证器硬约束。

    Args:
        case: 当前评估案例定义。
        _helper: 为统一案例签名保留但本场景无需使用的夹具助手。

    Returns:
        包含多层规则存在性与负向拒绝检查的案例结果。
    """

    # 源码文本映射覆盖根规则、公开文档和验证器实现。
    dict_texts = collect_plan_language_source_texts()  # Plan Mode 合同源码证据

    # 真实负向场景证明缺失专项语言锁会被验证器阻断。
    dict_verify = collect_missing_plan_language_report()  # Plan Mode 负向验证报告

    # 错误列表用于精确匹配专项默认语言规则诊断。
    list_verify_errors = dict_verify.get("errors", [])  # 缺失 Plan Mode 规则错误

    # 正向语言锁单独解析 catalog，避免复用负向夹具的对象状态。
    dict_language_catalog = json.loads(  # 正向语言合同 catalog 对象
        (SKILL_DIR / "config" / "languages.json").read_text(encoding="utf-8")  # 读取正向语言合同配置
    )

    # 正向根语言锁使用同一 catalog ID 对齐现场 AGENTS 元数据。
    str_default_language = str(  # 正向语言锁 conversation 默认语言 ID
        dict_language_catalog["defaults"]["conversation"]  # 读取正向语言锁默认值
    )

    # 合并规则同时约束普通回复与 proposed_plan 的默认语言。
    str_language_lock = (  # 合并语言锁字符串
        f"Natural-language replies, including `<proposed_plan>` content, use `{str_default_language}`"  # 现场根语言锁文本
    )

    # 正向检查覆盖通用规则、专项规则、参考文档和扫描实现。
    dict_with_checks = {  # Plan Mode 默认语言合同检查
        "repo_agents_mentions_combined_language_lock": str_language_lock in dict_texts["agents"],  # 根规则包含合并语言锁
        "skill_mentions_plan_mode_lock": "Plan Mode" in dict_texts["skill"]  # 技能工作流是否提及 Plan Mode
        and "<proposed_plan>" in dict_texts["skill"],  # 技能工作流是否绑定计划标签
        "script_guide_owns_language_input": (  # 脚本指南默认语言字段检查
            "default_conversation_language" in dict_texts["script_guide"]  # 指南默认语言字段锚点
        ),  # 脚本指南拥有默认语言输入字段
        "review_checklist_mentions_plan_mode_lock": "Plan Mode" in dict_texts["review_checklist"]  # 审查清单是否提及 Plan Mode
        and "follows the same rule" in dict_texts["review_checklist"],  # 审查清单是否检查同一语言规则
        "verify_script_has_plan_mode_guard": "verify_agents_scanning" in dict_texts["verify_entry"]  # 验证入口是否加载扫描层
        and "PLAN_LANGUAGE_LOCK_RE" in dict_texts["verify_scanning"]  # 扫描层是否定义专项表达式
        and "PLAN_LANGUAGE_LOCK_RE" in dict_texts["verify_policy"],  # 策略层是否消费专项表达式
        "verify_rejects_missing_plan_mode_lock": bool(list_verify_errors)  # 缺失专项规则是否产生错误
        and any(  # 是否命中准确的 Plan Mode 诊断
            "missing enforced Plan Mode default-language rule" in str_item  # 当前错误是否指向专项语言锁
            for str_item in list_verify_errors  # 遍历负向验证错误
        ),
    }

    # 旧语言治理基线不能保证任一 Plan Mode 专项能力。
    dict_without_checks = {  # 无技能路径的计划语言对照
        str_name: False  # 当前专项能力在通用语言锁基线中缺失
        for str_name in dict_with_checks  # 对照每项 Plan Mode 保证
    }

    # 返回负向验证报告以支持专项规则缺失诊断。
    return build_case_result(
        case,  # Plan Mode 语言锁案例元数据
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={"verify": dict_verify},
        without_skill_detail={
            "baseline": (
                "older language governance locked only generic natural-language replies and left "
                "Plan Mode `<proposed_plan>` body text without a hard verifier guard"
            )  # 旧通用语言治理基线缺陷
        },
    )

# 固定审查时刻与样例事件相隔不足 48 小时，确保统计窗口稳定。
TOKEN_REVIEW_NOW = "2026-05-27T05:36:00Z"  # token 统计夹具当前时刻

# 窗口文本直接传给 CLI，避免测试依赖本机时区或实时时钟。
TOKEN_REVIEW_HOURS = "48"  # token 统计回溯小时数

# 单次 token 审查助手统一公开 CLI 参数和 CODEX_HOME 路由。
def run_token_usage_review(path_sessions_root: Path, path_codex_home: Path) -> dict[str, Any]:
    """运行固定窗口的 Codex token 用量审查命令。

    Args:
        path_sessions_root: 传给 CLI 的待统计 sessions 根。
        path_codex_home: 用于安全边界判断的隔离 CODEX_HOME。

    Returns:
        token 用量审查命令的结构化 JSON 报告。
    """

    # 每个正负场景共享参数，仅 sessions 根与安全边界不同。
    return run_json_script(
        "codex_token_usage_review.py",  # Codex token 用量审查入口
        "--hours",  # 回溯窗口参数
        TOKEN_REVIEW_HOURS,  # 固定四十八小时窗口
        "--now",  # 可重复当前时刻参数
        TOKEN_REVIEW_NOW,  # 固定审查时刻
        "--json",  # 请求机器可读报告
        "--sessions-root",  # 显式会话树参数
        path_sessions_root,  # 当前正负场景待审查目录
        cwd=REPO_ROOT,  # 使用当前 token 审查实现
        env={"CODEX_HOME": str(path_codex_home)},  # 注入安全边界使用的 Codex 根
    )

# 成功夹具写入一条 token_count 事件，精确总量为 110。
def write_token_usage_fixture(path_codex_home: Path) -> None:
    """在隔离 CODEX_HOME 写入最小 token_count 会话事件。

    Args:
        path_codex_home: 将承载 sessions 日期树的隔离 Codex 根。

    Returns:
        本函数只写入 JSONL 夹具，不返回业务值。
    """

    # 日期树与事件时间一致，使扫描器能按日期缩小候选文件范围。
    path_dated_sessions = path_codex_home / "sessions" / "2026" / "05" / "27"  # 固定日期会话目录

    # 创建完整日期树后写入单条结构化事件。
    path_dated_sessions.mkdir(parents=True)

    # last_token_usage 字段模拟 Codex session JSONL 的真实事件结构。
    dict_event = {  # 单会话 token_count 事件
        "timestamp": "2026-05-27T04:00:00Z",  # 位于统计窗口内的事件时刻
        "type": "event_msg",  # Codex 会话事件类型
        "payload": {  # token_count 事件业务载荷
            "type": "token_count",  # token 统计载荷类型
            "info": {  # token_count 事件统计信息容器
                "last_token_usage": {  # 当前事件最后一次 token 使用量
                    "input_tokens": 100,  # 本轮输入 token 数
                    "cached_input_tokens": 20,  # 输入中命中缓存的 token 数
                    "output_tokens": 10,  # 本轮可见输出 token 数
                    "reasoning_output_tokens": 5,  # 本轮推理输出 token 数
                    "total_tokens": 110,  # 工具应汇总的总 token 数
                }
            },
        },
    }

    # JSONL 文件以单行 JSON 和结尾换行模拟真实 Codex 会话日志。
    (path_dated_sessions / "fixture-a.jsonl").write_text(
        json.dumps(dict_event, ensure_ascii=False) + "\n",  # 单条会话事件文本
        encoding="utf-8",  # 会话夹具统一编码
    )

# 行为证据覆盖合法会话树、缺失 Codex 根和越界 sessions 根。
def collect_token_usage_behavior() -> dict[str, Any]:
    """执行 Codex token 审查的一条成功路径和两条拒绝路径。

    Args:
        None: 本函数自行创建并释放隔离目录，不接收外部参数。

    Returns:
        成功统计、缺失根拒绝与越界拒绝三份报告。
    """

    # 临时根隔离合法 Codex home 和两个恶意或无效目录树。
    with tempfile.TemporaryDirectory() as str_temporary_directory:

        # 隔离根承载本案例全部可释放会话资产。
        path_root = Path(str_temporary_directory)  # token 审查场景临时根

        # 合法 Codex home 包含真实结构的 sessions 日期树。
        path_codex_home = path_root / "codex-home"  # 合法 Codex 配置根

        # 写入总量固定的单事件成功夹具。
        write_token_usage_fixture(path_codex_home)

        # 合法 sessions 根应返回总 token 数 110。
        dict_success = run_token_usage_review(  # 合法 Codex 会话树的窗口统计与总量报告
            path_codex_home / "sessions",  # 位于合法 CODEX_HOME 内的会话扫描根
            path_codex_home,  # 用于验证会话目录归属关系的安全边界
        )

        # 缺少 sessions 的 Codex home 用于验证环境前置条件拒绝。
        path_isolated_codex_home = path_root / "no-codex-home"  # 不含 sessions 的 Codex 根

        # 创建空 Codex 根，确保拒绝原因不是父目录不存在。
        path_isolated_codex_home.mkdir()

        # 外部日期树试图通过显式参数绕开缺失的 CODEX_HOME sessions。
        path_bypass_date = path_root / "external-sessions" / "2026" / "05" / "27"  # 绕过尝试日期目录

        # 创建完整外部日期树以证明存在性不能绕过 Codex 根检查。
        path_bypass_date.mkdir(parents=True)

        # 没有合法 Codex sessions 根时工具应拒绝，即使外部目录存在。
        dict_refused = run_token_usage_review(  # 缺失 Codex sessions 根报告
            path_bypass_date.parent.parent.parent,  # 外部 sessions 树根
            path_isolated_codex_home,  # 不含 sessions 的安全边界
        )

        # 越界场景保留合法 Codex home，但请求完全位于其外部的目录。
        path_outside_root = path_root / "outside-sessions"  # Codex 根外的 sessions 候选

        # 创建越界目录以触发安全边界而不是缺失目录诊断。
        path_outside_root.mkdir()

        # 工具应拒绝不属于 CODEX_HOME sessions 树的显式目录。
        dict_outside_tree = run_token_usage_review(  # sessions 根越界拒绝报告
            path_outside_root,  # Codex 根外的现存目录
            path_codex_home,  # 含合法 sessions 的安全边界
        )

    # 三份纯结构化报告可在临时目录释放后继续断言。
    return {
        "success": dict_success,  # 合法会话树汇总报告
        "refused": dict_refused,  # 缺少 Codex sessions 根的拒绝报告
        "outside_tree": dict_outside_tree,  # 显式目录越界拒绝报告
    }

# 公开案例验证显式触发文档、统计正确性和目录安全边界。
def case_codex_token_usage_review_contract(
    case: dict[str, Any],
    _helper: EvalFixtures,
) -> dict[str, Any]:
    """验证 Codex token 用量工具只在受控会话树中执行。

    Args:
        case: 当前评估案例定义。
        _helper: 为统一案例签名保留但本场景无需使用的夹具助手。

    Returns:
        包含触发规则、正确汇总与两类安全拒绝的案例结果。
    """

    # 技能正文必须限制工具仅响应用户明确提出的 token 统计请求。
    str_skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")  # 技能公开触发规则

    # agent 元数据只负责发现与启动，不能复制私人会话日志政策。
    str_openai_text = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")  # 产品入口元数据

    # 脚本指南把详细 sessions 边界委托给结构化注册指令。
    str_script_guide = (SKILL_DIR / "references" / "script-guide.md").read_text(encoding="utf-8")  # token 工具安全指南

    # 公开脚本存在性是行为测试可发现性的前置证明。
    path_token_usage_script = script_path("codex_token_usage_review.py")  # token 审查公开入口路径

    # 三条隔离行为路径共同证明统计和目录边界。
    dict_behavior = collect_token_usage_behavior()  # token 审查行为证据

    # 正向检查覆盖文档触发、安全前置条件、统计总量与两类拒绝。
    dict_with_checks = {  # 显式触发、目录边界和数值汇总三层合同检查
        "script_exists": path_token_usage_script.is_file(),  # 用户可调用的 token 审查入口是否真实存在
        "skill_mentions_explicit_trigger": (  # 技能显式 Token 触发检查
            "If the user explicitly asks for Codex Token usage statistics" in str_skill_text  # 技能显式触发锚点
        ),  # 技能正文包含显式 Token 统计触发条件
        "openai_avoids_policy_duplication": "explicit Codex token-usage request" not in str_openai_text,  # UI 渐进披露边界
        "script_guide_mentions_guard": "registered contract owns the default window, sessions-root boundary"  # 指南是否声明注册边界所有权
        in str_script_guide,  # 安全执行前置条件由注册指令承载
        "script_reports_totals": bool(dict_behavior["success"].get("ok"))  # 合法会话树的统计命令是否成功
        and dict_behavior["success"].get("grand_total", {}).get("total_tokens") == 110,  # 汇总总量是否匹配夹具事件
        "script_refuses_without_codex_root": not dict_behavior["refused"].get("ok")  # 缺少合法会话树时是否拒绝执行
        and dict_behavior["refused"].get("reason") == "codex_sessions_not_found",  # 拒绝诊断是否指向会话树缺失
        "script_rejects_outside_tree": not dict_behavior["outside_tree"].get("ok")  # 显式请求越界目录时是否拒绝执行
        and dict_behavior["outside_tree"].get("reason") == "sessions_root_outside_codex_root",  # 拒绝诊断是否指向目录越界
    }

    # 无治理基线不具备受控会话树统计或拒绝能力。
    dict_without_checks = {  # 无技能路径的 token 审查对照
        str_name: False  # 当前 token 审查能力在朴素基线中缺失
        for str_name in dict_with_checks  # 对照每项统计与安全保证
    }

    # 返回三份行为报告以区分统计错误和安全边界错误。
    return build_case_result(
        case,  # Codex token 用量审查案例元数据
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "success": dict_behavior["success"],  # 总量应为一百一十的成功报告
            "refused": dict_behavior["refused"],  # 缺少 Codex 根拒绝报告
            "outside_tree": dict_behavior["outside_tree"],  # Codex home 外部目录的安全拒绝报告
        },
        without_skill_detail={
            "baseline": "unguided baseline has no controlled internal Codex token usage tool path"  # 无治理 token 工具基线缺陷
        },
    )
