"""agents-md-generator 技能评估用例实现运行时发布分片。"""

# 延迟注解避免运行时解析评估专用类型。
from __future__ import annotations

# 评估核心显式提供路径、进程、夹具和结构化结果合同。
from eval_runtime_core import (
    Any,
    EvalFixtures,
    Path,
    REPO_ROOT,
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

# 外部项目运行时场景验证治理命令只引用已安装技能。
def case_governance_runtime_de_vendoring(
    case: dict[str, Any],
    helper: EvalFixtures,
) -> dict[str, Any]:
    """评估外部项目拒绝仓库内 vendored 治理运行时。

    Args:
        case: 当前评估用例元数据。
        helper: 提供受管项目和安装副本的夹具助手。

    Returns:
        已安装运行时路由与旧本地脚本基线的对比结果。
    """

    # 两条正式命令分别覆盖文档治理和目录治理入口。
    str_docs_command = (  # 已安装文档治理命令
        "python <codex-home>/skills/agents-md-generator/scripts/python/docs/"  # 安装态文档任务目录
        "manage_docs.py resume-check <project>"  # 恢复检查公开命令
    )

    # 目录审查同样必须由安装态运行时提供。
    str_dirs_command = (  # 已安装目录治理命令
        "python <codex-home>/skills/agents-md-generator/scripts/python/dirs/"  # 安装态目录任务目录
        "manage_dirs.py review <project> --input change.json"  # 目录变更审查命令
    )

    # 临时项目隔离规则篡改和验证器输出。
    with tempfile.TemporaryDirectory() as tmp:

        # 项目根直接使用临时目录，避免嵌套路径影响命令检测。
        path_project = Path(tmp)  # 外部受管项目根

        # 渲染助手同时返回技能目录和模拟安装副本。
        tuple_fixture = helper.make_rendered_governed_skill_project(  # 外部项目渲染结果
            path_project,  # 接收根规则和技能配置的项目
            name="demo-skill",  # 使用非所有者名称触发外部仓库规则
        )

        # 第一项用于构造禁止出现的项目内脚本路径。
        path_skill = tuple_fixture[0]  # 外部项目技能目录

        # 第二项提供验证器解析版本和运行时的安装态来源。
        path_installed = tuple_fixture[1]  # 模拟已安装技能根

        # 原始根规则应完整包含两条安装态治理命令。
        path_agents = path_project / "AGENTS.md"  # 外部项目根规则路径

        # 未篡改文本用于证明生成器默认路由正确。
        str_agents = path_agents.read_text(encoding="utf-8", errors="ignore")  # 未篡改根规则文本

        # 将文档命令替换为项目本地入口以触发去 vendoring 门禁。
        str_bad_agents = str_agents.replace(  # 注入非法本地运行时的规则文本
            str_docs_command,  # 待替换的正确安装态命令
            "python scripts/manage_docs.py resume-check <project>",  # 非法项目本地命令
        )

        # 验证器必须读取实际落盘的非法规则而非内存字符串。
        path_agents.write_text(str_bad_agents, encoding="utf-8")

        # 正式验证器应报告非所有者仓库引用本地运行时。
        dict_verify = run_json_script(  # 去 vendoring 验证结果
            "verify_agents.py",  # 根规则验证入口
            path_project,  # 已写入非法命令的外部项目
            cwd=REPO_ROOT,  # 从仓库根解析正式验证器
            env={"AGENTS_MD_INSTALLED_SKILL_DIR": str(path_installed)},  # 注入隔离安装副本
        )

    # 禁止片段覆盖根 scripts 和技能目录下两种本地引用。
    path_skill_script = Path("skills") / path_skill.name / "scripts" / "manage_docs.py"  # 技能内脚本相对路径

    # 命令前缀与相对路径组合为根规则中禁止出现的文本。
    str_skill_local = f"python {path_skill_script.as_posix()}"  # 技能内本地命令片段

    # 错误片段与验证器公开诊断合同保持一致。
    str_forbidden_error = (  # 验证器预期错误片段
        "project-local governance runtime command is forbidden for non-owner repositories"  # 非所有者阻断诊断
    )

    # 有技能路径同时证明正确渲染和非法修改阻断。
    dict_with_checks = {  # 外部项目运行时治理断言
        "agents_use_installed_runtime": str_docs_command in str_agents,  # 文档命令是否来自安装态
        "agents_use_installed_dir_manager_runtime": str_dirs_command in str_agents,  # 目录命令是否来自安装态
        "agents_omit_project_local_runtime": "python scripts/manage_docs.py" not in str_agents  # 根脚本引用是否缺失
        and str_skill_local not in str_agents,  # 原始规则是否排除本地运行时
        "verify_rejects_vendored_runtime": any(  # 非法命令诊断是否存在
            str_forbidden_error in str_error  # 当前错误是否命中禁止 vendoring 诊断
            for str_error in dict_verify.get("errors", [])  # 遍历验证器全部错误
        ),  # 篡改后的规则是否被验证器阻断
    }

    # 无治理基线不提供安装态路由或本地脚本阻断能力。
    dict_without_checks = {  # 缺少去 vendoring 治理的历史基线
        str_key: False  # 当前能力在旧基线中不可用
        for str_key in dict_with_checks  # 完整外部运行时能力名称
    }

    # 验证器载荷保留用于定位命令检测失败原因。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={"verify": dict_verify},
        without_skill_detail={
            "baseline": (
                "older routing let external workspaces reference project-local governance "
                "scripts and encouraged runtime vendoring"
            )
        },
    )

# 所有者夹具助手创建包含仓库内治理入口的真实技能项目。
def prepare_owner_runtime_fixture(
    path_workspace: Path,
    helper: EvalFixtures,
) -> tuple[Path, Path, str, str]:
    """创建所有者项目并写入允许存在的本地治理命令。

    Args:
        path_workspace: 本场景的隔离工作区根。
        helper: 提供受管项目渲染能力的夹具助手。

    Returns:
        项目根、安装运行时根、本地命令和根规则文本。
    """

    # 所有者项目名称必须与当前技能包名称一致。
    path_project = path_workspace / "owner"  # agents-md-generator 所有者项目根

    # 当前版本同时注入源码和夹具安装态，排除版本漂移干扰。
    str_version = (SKILL_DIR / "VERSION").read_text(encoding="utf-8").strip()  # 当前技能版本

    # 渲染结果第一项是项目内技能源码根。
    tuple_rendered = helper.make_rendered_governed_skill_project(  # 所有者项目渲染结果
        path_project,  # 接收所有者根规则的隔离项目
        name="agents-md-generator",  # 使用包名建立所有者身份
        project_version=str_version,  # 源码声明当前版本
        installed_version=str_version,  # 夹具安装态保持同版
    )

    # 项目内技能根承载允许存在的本地治理入口。
    path_skill = tuple_rendered[0]  # 项目内 agents-md-generator 技能根

    # 最小本地入口证明所有者仓库确实携带治理运行时。
    path_local_docs = path_skill / "scripts" / "python" / "docs" / "manage_docs.py"  # 本地文档治理入口

    # 递归创建任务分类目录以写入最小入口。
    path_local_docs.parent.mkdir(parents=True, exist_ok=True)

    # 文件内容只需证明入口存在，不参与被测命令执行。
    path_local_docs.write_text("print('owner local runtime')\n", encoding="utf-8")

    # 所有者命令使用仓库内标准任务分类路径。
    path_relative_docs = Path("skills") / "agents-md-generator" / "scripts" / "python" / "docs" / "manage_docs.py"  # 本地入口相对路径

    # 相对路径拼接恢复检查参数形成完整规则命令。
    str_local_command = f"python {path_relative_docs.as_posix()} resume-check <project>"  # 所有者本地治理命令

    # 根规则文件是所有者命令检测的正式输入面。
    path_agents = path_project / "AGENTS.md"  # 所有者项目根规则路径

    # 读取文本后仅在缺失时补充兼容章节。
    str_agents = path_agents.read_text(encoding="utf-8", errors="ignore")  # 初始根规则文本

    # 兼容旧夹具未自动渲染所有者命令的情况。
    if str_local_command not in str_agents:

        # 追加内容保持 Markdown 章节边界清晰。
        str_agents += f"\n## Owner Runtime Command\n- `{str_local_command}`\n"  # 补充所有者命令章节

    # 验证器读取落盘后的完整所有者规则。
    path_agents.write_text(str_agents, encoding="utf-8")

    # 安装运行时复制当前技能源码，模拟本地 Codex 已安装状态。
    path_installed = path_workspace / "installed-runtime" / "agents-md-generator"  # 隔离安装运行时根

    # 忽略字节码缓存，确保安装副本只含可发布内容。
    shutil.copytree(SKILL_DIR, path_installed, ignore=shutil.ignore_patterns("__pycache__"))

    # 调用方负责同步全局规则并从安装态执行验证器。
    return path_project, path_installed, str_local_command, str_agents

# 安装态验证助手同步全局规则并执行所有者项目验证。
def verify_owner_from_installed_runtime(
    path_workspace: Path,
    path_project: Path,
    path_installed: Path,
) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
    """从隔离安装副本验证所有者项目。

    Args:
        path_workspace: 隔离工作区根。
        path_project: 待验证的所有者项目根。
        path_installed: 模拟已安装技能根。

    Returns:
        验证器进程结果和解析后的 JSON 载荷。
    """

    # 隔离 Codex 主目录承载同步生成的全局规则。
    path_codex_home = path_workspace / "codex-home"  # 临时 Codex 主目录

    # 同步命令要求目标主目录预先存在。
    path_codex_home.mkdir()

    # 子进程环境禁止字节码并显式绑定安装态运行时。
    dict_environment = dict(  # 安装态验证环境
        os.environ,  # 继承基础系统环境
        PYTHONDONTWRITEBYTECODE="1",  # 禁止污染安装副本
        CODEX_HOME=str(path_codex_home),  # 指向隔离全局规则根
        AGENTS_MD_INSTALLED_SKILL_DIR=str(path_installed),  # 绑定安装态技能
    )

    # 文档入口执行全局规则同步。
    path_docs_entry = path_installed / "scripts" / "python" / "docs" / "manage_docs.py"  # 安装态文档入口

    # 验证入口执行所有者识别合同。
    path_verify_entry = path_installed / "scripts" / "python" / "verify" / "verify_agents.py"  # 安装态验证入口

    # 全局规则同步建立验证器需要的托管基线。
    subprocess.run(
        [
            sys.executable,  # 当前隔离 Python 解释器
            str(path_docs_entry),  # 安装态文档治理入口
            "sync-global-codex-agents",  # 请求同步全局托管规则
            str(path_project),  # 所有者项目上下文
            "--write",  # 允许写入隔离 Codex 主目录
            "--codex-home",  # 显式覆盖主目录位置
            str(path_codex_home),  # 全局规则写入目标
        ],
        cwd=REPO_ROOT,  # 从仓库根解析运行依赖
        text=True,  # 以文本形式捕获诊断
        capture_output=True,  # 避免污染评估 JSON 协议
        check=True,  # 同步失败立即终止场景
        env=dict_environment,  # 应用隔离安装态环境
    )

    # 验证命令必须直接使用安装副本中的公开入口。
    process_result = subprocess.run(  # 安装态所有者验证进程
        [sys.executable, str(path_verify_entry), str(path_project)],  # 验证器完整命令
        cwd=REPO_ROOT,  # 保持与正式验证命令相同工作目录
        text=True,  # 标准流按文本协议处理
        capture_output=True,  # 收集 JSON 或错误诊断
        check=False,  # 由结构化载荷表达验证失败
        env=dict_environment,  # 使用隔离安装态环境
    )

    # 空标准输出转换为带 stderr 的稳定错误载荷。
    dict_verify = (
        json.loads(process_result.stdout)  # 解析正常机器输出
        if process_result.stdout.strip()  # 标准输出非空时采用 JSON 协议
        else {"errors": [process_result.stderr]}  # 否则保留子进程错误
    )  # 所有者项目验证载荷

    # 进程参数和结构化载荷共同证明安装态执行事实。
    return process_result, dict_verify

# 所有者仓库场景验证安装态验证器接受源码内治理命令。
def case_installed_runtime_owner_repo_local_commands(
    case: dict[str, Any],
    helper: EvalFixtures,
) -> dict[str, Any]:
    """评估安装态验证器不会误判所有者仓库的本地命令。

    Args:
        case: 当前评估用例元数据。
        helper: 提供所有者受管项目渲染能力的夹具助手。

    Returns:
        安装态所有者识别能力与误判基线的结构化对比结果。
    """

    # 临时工作区隔离所有者源码、安装副本和全局规则。
    with tempfile.TemporaryDirectory() as tmp:

        # 路径对象作为所有夹具目录的共同父级。
        path_workspace = Path(tmp)  # 所有者运行时场景工作区

        # 夹具组合包含项目、安装副本、命令和根规则文本。
        tuple_fixture = prepare_owner_runtime_fixture(path_workspace, helper)  # 所有者项目夹具

        # 项目根是同步全局规则和运行验证器的共同目标。
        path_project = tuple_fixture[0]  # 待验证所有者项目根

        # 安装副本提供本次验证的真实运行入口。
        path_installed = tuple_fixture[1]  # 模拟安装技能根

        # 本地命令用于证明所有者仓库豁免没有删改规则。
        str_local_command = tuple_fixture[2]  # 根规则内本地治理命令

        # 根规则文本是命令保留断言的事实来源。
        str_agents = tuple_fixture[3]  # 所有者根规则文本

        # 从安装副本执行同步和验证形成运行时证据。
        tuple_verification = verify_owner_from_installed_runtime(  # 安装态验证结果
            path_workspace,  # 提供隔离 Codex 主目录的父级
            path_project,  # 接受安装态验证的所有者项目
            path_installed,  # 提供公开命令入口的安装副本
        )

        # 子进程参数证明验证器并非从源码目录直接调用。
        process_result = tuple_verification[0]  # 验证器子进程结果

        # JSON 载荷提供所有者识别和错误集合证据。
        dict_verify = tuple_verification[1]  # 验证器结构化载荷

    # 所有者项目不得出现仅适用于外部仓库的阻断诊断。
    str_forbidden_error = (  # 非所有者仓库专用诊断
        "project-local governance runtime command is forbidden for non-owner repositories"  # 所有者场景禁止出现
    )

    # 错误集合只计算一次，供两个兼容断言复用。
    bool_has_error = any(  # 是否错误触发非所有者诊断
        str_forbidden_error in str_error  # 当前诊断是否命中误判文本
        for str_error in dict_verify.get("errors", [])  # 验证器返回的全部错误
    )

    # 预期入口用于反查子进程参数确实来自安装副本。
    path_verify_entry = path_installed / "scripts" / "python" / "verify" / "verify_agents.py"  # 预期安装态入口

    # 有技能路径证明安装态调用、命令保留和所有者豁免。
    dict_with_checks = {  # 所有者仓库运行时断言
        "installed_runtime_invoked": str(path_verify_entry) in " ".join(process_result.args),  # 是否调用安装态入口
        "owner_repo_keeps_local_command": str_local_command in str_agents,  # 是否保留本地命令
        "verify_accepts_owner_local_runtime": not bool_has_error,  # 是否接受所有者运行时
        "no_non_owner_runtime_error": not bool_has_error,  # 是否排除外部仓库诊断
    }

    # 旧基线能调用入口和保留命令，但会错误拒绝所有者仓库。
    dict_without_checks = {  # 所有者识别缺失的历史基线
        "installed_runtime_invoked": True,  # 基线仍能调用安装入口
        "owner_repo_keeps_local_command": True,  # 基线仍保留本地命令
        "verify_accepts_owner_local_runtime": False,  # 基线会拒绝所有者运行时
        "no_non_owner_runtime_error": False,  # 基线会产生误判诊断
    }

    # 验证器原始载荷保留用于定位所有者识别失败。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={"verify": dict_verify},
        without_skill_detail={
            "baseline": (
                "installed verification can misclassify the source repository as a non-owner "
                "and reject required local governance commands"
            )
        },
    )

# 交接命令助手运行直接验证、复合门禁、修复和复验。
def run_handoff_naming_commands(path_project: Path, path_skill: Path) -> dict[str, Any]:
    """运行交接命名漂移的治理闭环命令。

    Args:
        path_project: 已发生交接文件改名的隔离项目根。
        path_skill: 工作目录门禁使用的项目内技能根。

    Returns:
        修复前验证、工作目录门禁、修复和复验结果。
    """

    # 文档验证应直接报告 handoff naming drift。
    dict_verify = run_json_script(  # 修复前文档验证结果
        "manage_docs.py",  # 文档治理入口
        "verify",  # 请求验证现有治理文档
        path_project,  # 包含非法交接文件名的项目
        cwd=REPO_ROOT,  # 从仓库根解析正式运行时
    )

    # 工作目录门禁必须传播文档验证的命名错误。
    dict_work_folder = run_json_script(  # 修复前工作目录门禁结果
        "manage_docs.py",  # 复合门禁使用同一治理入口
        "work-folder-gate",  # 请求开发工作目录检查
        path_project,  # 当前命名漂移项目
        "--skill-dir",  # 指定项目内技能相对根
        str(Path("skills") / path_skill.name),  # 示例技能路径
        "--mode",  # 指定工作目录执行模式
        "development",  # 使用开发态门禁集合
        cwd=REPO_ROOT,  # 保持正式入口解析上下文
    )

    # 专用修复命令恢复固定 HANDOFF.md 文件名。
    dict_repair = run_json_script(  # 交接命名修复结果
        "manage_docs.py",  # 修复命令治理入口
        "repair-handoff-names",  # 请求恢复固定文件名
        path_project,  # 接收修复写入的项目
        "--write",  # 明确允许执行文件改名
        cwd=REPO_ROOT,  # 从仓库根运行正式修复器
    )

    # 修复后的完整文档验证必须恢复通过。
    dict_repaired_verify = run_json_script(  # 修复后文档验证结果
        "manage_docs.py",  # 复验仍使用文档治理入口
        "verify",  # 请求完整文档合同检查
        path_project,  # 已恢复固定文件名的项目
        cwd=REPO_ROOT,  # 使用与修复前一致的运行上下文
    )

    # 四阶段结果使用稳定名称供断言和详情复用。
    return {  # 交接命名治理命令结果
        "verify": dict_verify,  # 修复前直接验证载荷
        "work_folder": dict_work_folder,  # 修复前复合门禁载荷
        "repair": dict_repair,  # 固定文件名修复载荷
        "repaired_verify": dict_repaired_verify,  # 修复后复验载荷
    }

# 交接文件命名场景验证固定文件名能够被检测并自动修复。
def case_handoff_naming_gate(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估交接文件改名后的阻断、修复和复验链路。

    Args:
        case: 当前评估用例元数据。
        helper: 提供受管项目和 Git 提交夹具的评估助手。

    Returns:
        命名治理闭环与静默覆盖基线的结构化对比结果。
    """

    # 临时项目隔离错误改名提交和修复写入。
    with tempfile.TemporaryDirectory() as tmp:

        # 项目根承载受管文档和独立 Git 历史。
        path_project = Path(tmp)  # 交接命名场景项目根

        # 渲染结果第一项用于定位技能相对目录。
        tuple_rendered = helper.make_rendered_governed_skill_project(  # 受管项目渲染结果
            path_project,  # 接收交接文件夹具的隔离项目
            name="demo-skill",  # 使用常规外部技能名称
        )

        # 技能根只用于构造工作目录门禁参数。
        path_skill = tuple_rendered[0]  # 项目内示例技能根

        # 将唯一合法文件名改成非法名称以形成命名漂移。
        path_current = path_project / "docs" / "handoff" / "HANDOFF.md"  # 合法交接文件路径

        # 改名目标保留同一目录，只改变受治理文件名。
        path_renamed = path_current.with_name("RENAMED.md")  # 非法改名后的交接路径

        # 文件系统改名制造需要检测的真实漂移。
        path_current.rename(path_renamed)

        # 提交改名使文档治理读取真实版本库状态。
        helper.git_commit_all(path_project, "rename handoff incorrectly")

        # scaffold 必须拒绝通过新建文件掩盖已有改名漂移。
        tuple_scaffold = run_script(  # scaffold 阻断进程结果
            "manage_docs.py",  # scaffold 所属文档任务入口
            "scaffold",  # 请求补齐文档骨架
            path_project,  # 已发生交接改名的项目
            cwd=REPO_ROOT,  # 使用仓库正式 scaffold 运行上下文
        )

        # 退出码证明 scaffold 主动阻断而非静默继续。
        int_scaffold_code = tuple_scaffold[0]  # scaffold 改名阻断退出码

        # 标准输出提供精确固定文件名诊断。
        str_scaffold_stdout = tuple_scaffold[1]  # scaffold 标准输出

        # 后续四条命令完成阻断传播、修复和复验。
        dict_commands = run_handoff_naming_commands(path_project, path_skill)  # 交接命名命令结果

        # 直接验证载荷负责证明底层命名检查生效。
        dict_verify = dict_commands["verify"]  # 命名修复前直接验证载荷

        # 复合门禁载荷负责证明错误能传播到开发入口。
        dict_work_folder = dict_commands["work_folder"]  # 命名修复前工作目录载荷

        # 修复载荷负责证明固定文件名能够无错误恢复。
        dict_repair = dict_commands["repair"]  # 固定交接文件名修复载荷

        # 复验载荷负责证明修复后完整文档合同重新通过。
        dict_repaired_verify = dict_commands["repaired_verify"]  # 文件名恢复后复验载荷

    # 两组错误集合分别证明直接验证和复合门禁都能发现漂移。
    list_verify_errors = dict_verify.get("errors", [])  # 文档验证错误集合

    # 复合门禁错误集合证明上层门禁没有吞掉根因。
    list_work_folder_errors = dict_work_folder.get("errors", [])  # 工作目录门禁错误集合

    # 固定诊断片段用于校验 scaffold 明确指出合法文件名。
    str_scaffold_error = "current handoff must be exactly docs/handoff/HANDOFF.md"  # scaffold 命名诊断

    # 有技能路径覆盖阻断、传播、修复和最终放行。
    dict_with_checks = {  # 交接文件命名治理断言
        "scaffold_blocked_on_rename": int_scaffold_code != 0  # scaffold 是否返回失败
        and str_scaffold_error in str_scaffold_stdout,  # 输出是否包含固定文件名诊断
        "verify_rejects_rename": any(  # 直接验证是否发现命名漂移
            "handoff naming drift" in str_error  # 当前错误是否命中命名漂移
            for str_error in list_verify_errors  # 文档验证返回的全部错误
        ),
        "work_folder_gate_rejects_rename": any(  # 复合门禁是否传播命名漂移
            "docs-verify: handoff naming drift" in str_error  # 当前错误是否保留来源前缀
            for str_error in list_work_folder_errors  # 工作目录门禁返回的全部错误
        ),
        "repair_succeeds": not dict_repair.get("errors")  # 修复过程是否无错误
        and not bool(dict_repair.get("handoff_naming", {}).get("blocking")),  # 修复后是否解除阻断
        "verify_passes_after_repair": not dict_repaired_verify.get("errors"),  # 修复后完整验证是否无错误
    }

    # 静默覆盖基线无法提供任一命名治理能力。
    dict_without_checks = {  # 缺少交接命名治理的历史基线
        str_key: False  # 当前命名治理能力在旧基线中不可用
        for str_key in dict_with_checks  # 完整交接命名能力名称
    }

    # 各阶段原始结果保留用于定位命名治理闭环断点。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={
            "verify": dict_verify,
            "work_folder_gate": dict_work_folder,
            "repair": dict_repair,
            "repaired_verify": dict_repaired_verify,
        },
        without_skill_detail={
            "baseline": (
                "a weaker baseline silently replaces the renamed handoff and loses naming "
                "drift evidence"
            )
        },
    )

# 扩展发布场景从拆分模块显式回导，保持原公开映射稳定。
from eval_runtime_release_extended_cases import (
    case_governance_cli_entrypoint_smoke,
    case_release_content_evals_install_contract,
    case_release_sanitizer_regex_constant,
    case_workspace_settings_gate,
)
