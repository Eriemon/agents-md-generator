"""agents-md-generator 技能评估用例项目生命周期分片。"""

# 延迟类型注解，避免评估上下文尚未装载时解析共享类型。
from __future__ import annotations

# 分片显式声明使用的运行时符号，避免依赖隐式全局上下文。
from eval_runtime_core import (
    Any,
    EvalFixtures,
    Path,
    REPO_ROOT,
    SKILL_DIR,

    # 共享执行器和序列化工具支撑各隔离评估场景。
    build_case_result,
    json,
    run_json_script,
    run_script,
    tempfile,
)

# 通用验证脚本路径同时用于主说明引用和审计覆盖断言。
PATH_GENERIC_VALIDATE_SCRIPT = Path("scripts") / "validate_demo_skill.py"  # 通用验证脚本相对路径

# 缺失配置路径用于构造发布包完整性阻断场景。
PATH_MISSING_DEFAULTS = Path("config") / "defaults.json"  # 故意缺失的配置相对路径

# 缺失根规则场景验证检查器能主动触发治理生成。
def case_missing_root_agents(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估受管项目缺失根 AGENTS.md 时的触发与重建路由。

    Args:
        case: 当前评估用例元数据。
        helper: 负责构造隔离安装副本的夹具助手。

    Returns:
        有技能与无技能基线的结构化对比结果。
    """

    # 临时根目录隔离评估生成物和安装夹具。
    with tempfile.TemporaryDirectory() as tmp:

        # 根目录承载工作区和模拟安装副本两类资源。
        path_root = Path(tmp)  # 缺失根规则场景的隔离根

        # 空工作区刻意不创建 AGENTS.md，以触发缺失规则路径。
        path_project = path_root / "workspace"  # 待检查的模拟项目

        # 检查器要求项目目录真实存在。
        path_project.mkdir()

        # 安装副本提供版本元数据和完整 skill 运行文件。
        path_installed_skill = helper.make_installed_skill_fixture(path_root)  # 模拟本地安装目录

        # 项目检查结果是本用例的权威行为证据。
        dict_facts = run_json_script(  # 缺失根规则的检查器输出
            "inspect_project.py",  # 项目治理检查入口
            path_project,  # 本次检查的缺失根规则项目
            cwd=REPO_ROOT,  # 使用真实仓库解析缺失根规则检查器
            env={"AGENTS_MD_INSTALLED_SKILL_DIR": str(path_installed_skill)},  # 注入隔离安装副本
        )

        # 有技能路径必须同时指出触发、重建和具体缺失原因。
        dict_with_checks = {  # 受管检查器的预期断言
            "trigger_required": bool(dict_facts.get("root_agents_md_trigger_required")),  # 是否要求生成根规则
            "rebuild_required": bool(dict_facts.get("root_agents_md_rebuild_required")),  # 是否要求重建根规则
            "missing_root_reason": "missing_root_agents_md"  # 是否准确报告缺失原因
            in dict_facts.get("root_agents_md_trigger_reasons", []),  # 检查器返回的全部缺失根规则原因
        }

        # 无技能基线不具备治理路由能力，所有能力断言均为假。
        dict_without_checks = {  # 无治理工具的基线断言
            "trigger_required": False,  # 基线不触发根规则治理
            "rebuild_required": False,  # 基线不要求重建根规则
            "missing_root_reason": False,  # 基线不提供缺失原因
        }

        # 统一结果结构由评估汇总器计算通过率和差异。
        return build_case_result(
            case,
            with_skill_checks=dict_with_checks,
            without_skill_checks=dict_without_checks,
            with_skill_detail={"facts": dict_facts},
            without_skill_detail={
                "baseline": (
                    "unguided baseline does not emit trigger or rebuild routing "
                    "for missing root AGENTS.md"
                )
            },
        )

# 版本元数据漂移场景验证检查器进入兼容接管模式。
def case_version_mismatch_takeover(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估生成器版本落后于规则版本时的接管路由。

    Args:
        case: 当前评估用例元数据。
        helper: 负责构造指定版本安装副本的夹具助手。

    Returns:
        版本检查和设计会话启动行为的对比结果。
    """

    # 隔离目录防止接管会话状态写入真实仓库。
    with tempfile.TemporaryDirectory() as tmp:

        # 根目录同时容纳版本漂移项目和指定版本安装副本。
        path_root = Path(tmp)  # 版本接管场景的隔离根

        # 最小 Python 项目使检查器识别到真实工作区结构。
        path_project = path_root / "workspace"  # 模拟版本漂移项目

        # 接管流程要求项目根和源码目录已经存在。
        path_project.mkdir()

        # 源码目录使夹具具备可识别的 Python 项目结构。
        (path_project / "src").mkdir()

        # 示例源码仅用于形成可识别项目，不参与版本断言。
        (path_project / "src" / "main.py").write_text(
            "print('demo')\n",
            encoding="utf-8",
        )

        # 安装版本代表当前可用的规则基线。
        path_installed_skill = helper.make_installed_skill_fixture(  # v0.6.2 模拟安装副本
            path_root,  # 指定版本安装副本所在隔离根
            version="v0.6.2",  # 当前安装技能的语义版本
        )  # 指定版本的模拟安装副本

        # 根规则故意记录落后一版的生成器版本。
        str_agents_content = (
            "<!-- AGENTS-METADATA: agents_version=v0.6.2; "
            "generator_version=v0.6.1; default_language=中文 -->\n"
            "# AGENTS.md\n"
        )  # 触发 generator_version_mismatch 的规则文本

        # 漂移规则写入项目根，供检查和会话启动命令共同读取。
        (path_project / "AGENTS.md").write_text(
            str_agents_content,
            encoding="utf-8",
        )

        # 检查器应识别版本不一致并要求治理接管。
        dict_facts = run_json_script(  # 项目版本兼容性事实
            "inspect_project.py",  # 版本兼容性检查入口
            path_project,  # 本次检查的版本漂移项目
            cwd=REPO_ROOT,  # 使用真实仓库解析版本检查器
            env={"AGENTS_MD_INSTALLED_SKILL_DIR": str(path_installed_skill)},  # 注入指定版本安装副本
        )

        # 启动设计会话验证路由决定确实落到 takeover 模式。
        dict_started = run_json_script(  # 设计会话启动结果
            "collect_design_profile.py",  # 设计接管会话入口
            path_project,  # 本次启动接管会话的项目
            "--start",  # 请求创建新的设计治理会话
            cwd=REPO_ROOT,  # 使用真实仓库解析设计会话入口
            env={"AGENTS_MD_INSTALLED_SKILL_DIR": str(path_installed_skill)},  # 接管会话使用同一安装副本
        )

        # 有技能路径同时验证检查事实和会话执行结果。
        dict_with_checks = {  # 版本漂移接管断言
            "trigger_required": bool(dict_facts.get("root_agents_md_trigger_required")),  # 版本漂移是否触发治理
            "generator_version_mismatch": "generator_version_mismatch"  # 检查事实是否包含版本漂移
            in dict_facts.get("root_agents_md_trigger_reasons", []),  # 版本检查返回的全部治理触发原因
            "takeover_mode": dict_started.get("mode") == "takeover",  # 会话是否进入接管模式
            "takeover_reason": "generator_version_mismatch"  # 接管原因是否对应生成器版本漂移
            in dict_started.get("takeover_trigger_reasons", []),  # 会话返回的全部接管原因
        }

        # 无技能基线不会解析生成器元数据或发起接管会话。
        dict_without_checks = {  # 无治理工具的兼容性基线
            "trigger_required": False,  # 基线不解析生成器版本
            "generator_version_mismatch": False,  # 基线不识别生成器版本漂移
            "takeover_mode": False,  # 基线不具备接管会话模式
            "takeover_reason": False,  # 基线不提供接管原因
        }

        # 结构化结果保留两条命令的原始事实供失败诊断。
        return build_case_result(
            case,
            with_skill_checks=dict_with_checks,
            without_skill_checks=dict_without_checks,
            with_skill_detail={"facts": dict_facts, "start": dict_started},
            without_skill_detail={
                "baseline": (
                    "unguided baseline sees an AGENTS.md file but does not route "
                    "into compatibility takeover"
                )
            },
        )

# 白名单控制配置集中描述示例 skill 仓库允许的根路径。
def root_whitelist_control() -> dict[str, Any]:
    """构造根目录白名单场景的最小治理配置。

    Args:
        无外部业务参数。

    Returns:
        包含项目分类和目录合同的治理配置。
    """

    # 配置只保留目录门禁识别本场景所需的字段。
    return {  # 最小 skill 仓库目录治理配置
        "kind": "skill",  # 项目分类决定默认目录合同
        "name": "demo-skill",  # 被治理的示例技能名称
        "directory_contract": {  # 示例技能的目录边界合同
            "primary_project_root": (Path("skills") / "demo-skill").as_posix() + "/",  # 功能源码唯一主根
            "allowed_new_paths": [  # 根目录允许新增的治理路径
                (Path("skills") / "demo-skill").as_posix() + "/",  # 标准技能源码目录
                "tests/",  # 仓库级测试目录
                "dist/",  # 版本化发布包目录
                "docs/",  # 项目治理文档目录
                ".agents/",  # 机器治理状态目录
                "ref/",  # 只读参考资料目录
            ],
            "enforce_primary_project_root": True,  # 禁止功能源码脱离主根
            "remote": "not configured",  # 本夹具不启用远程部署
        },
    }

# 白名单夹具写入治理配置、标准技能和刻意越界文件。
def prepare_root_whitelist_project(path_project: Path) -> None:
    """准备包含根目录漂移的最小技能项目。

    Args:
        path_project: 已存在的隔离项目根目录。

    Returns:
        无业务返回值，夹具文件直接写入 path_project。
    """

    # 治理配置目录必须先存在才能写入目录合同。
    (path_project / ".agents").mkdir()

    # 控制文件是目录门禁读取白名单的唯一来源。
    (path_project / ".agents" / "agents-control.json").write_text(
        json.dumps(root_whitelist_control(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 最小 skill 主目录使项目分类与目录合同保持一致。
    path_skill = path_project / "skills" / "demo-skill"  # 模拟 skill 源目录

    # 递归创建标准 skill 布局。
    path_skill.mkdir(parents=True)

    # SKILL.md frontmatter 提供项目识别所需的名称和描述。
    (path_skill / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Use when testing\n---\n# Demo\n",
        encoding="utf-8",
    )

    # PROJECT-NOTES.md 不在根白名单内，代表需要治理确认的漂移。
    (path_project / "PROJECT-NOTES.md").write_text("# Drift\n", encoding="utf-8")

# 根级白名单场景验证目录漂移会被阻断并要求确认修复。
def case_root_whitelist(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估 skill 仓库根目录出现未授权文件时的治理行为。

    Args:
        case: 当前评估用例元数据。
        helper: 评估夹具助手；本场景仅保留统一函数签名。

    Returns:
        结构门禁和项目检查器的对比结果。
    """

    # 临时项目承载刻意制造的根目录漂移。
    with tempfile.TemporaryDirectory() as tmp:

        # 项目根包含目录合同、标准 skill 与刻意越界的说明文件。
        path_project = Path(tmp)  # 根白名单场景项目

        # 专用助手准备目录合同和刻意越界的说明文件。
        prepare_root_whitelist_project(path_project)

        # 结构门禁给出阻断决定和具体越界路径。
        dict_gate = run_json_script(  # 根目录结构门禁结果
            "manage_dirs.py",  # 目录结构门禁入口
            "structure-gate",  # 请求执行根目录结构门禁
            path_project,  # 包含越界说明文件的示例项目
            cwd=REPO_ROOT,  # 使用仓库目录结构治理运行时
        )

        # 项目检查器应把同一漂移映射为修复确认要求。
        dict_facts = run_json_script(  # 项目结构治理事实
            "inspect_project.py",  # 项目治理事实检查入口
            path_project,  # 需要提取结构修复事实的项目
            cwd=REPO_ROOT,  # 使用仓库项目检查运行时
        )

        # 有技能路径要求门禁阻断、原因可定位且修复需确认。
        dict_with_checks = {  # 根白名单治理断言
            "blocked": not bool(dict_gate.get("approved")),  # 越界说明文件是否被阻断
            "unexpected_file_reason": any(  # 阻断原因是否准确定位未知文件
                "PROJECT-NOTES.md" in str_item  # 当前原因是否指向越界文件
                for str_item in dict_gate.get("reasons", [])  # 目录门禁返回的全部阻断原因
            ),
            "confirmation_required": bool(dict_facts.get("structure_fix_confirmation_required")),  # 修复是否要求确认
        }

        # 无技能基线缺少白名单与确认门禁能力。
        dict_without_checks = {  # 无治理工具的目录基线
            "blocked": False,  # 基线允许根目录漂移
            "unexpected_file_reason": False,  # 基线不定位越界文件
            "confirmation_required": False,  # 基线不要求修复确认
        }

        # 原始门禁与检查事实随结果保留，便于定位失败断言。
        return build_case_result(
            case,
            with_skill_checks=dict_with_checks,
            without_skill_checks=dict_without_checks,
            with_skill_detail={"structure_gate": dict_gate, "facts": dict_facts},
            without_skill_detail={
                "baseline": (
                    "unguided baseline allows root drift because it has no "
                    "governed whitelist or confirmation gate"
                )
            },
        )

# evolution 退役场景验证 CLI 与文档同时删除旧合同。
def case_evolution_removed_contract(case: dict[str, Any], _helper: EvalFixtures) -> dict[str, Any]:
    """评估 evolution 命令退役后的代码与文档一致性。

    Args:
        case: 当前评估用例元数据。
        _helper: 未使用的夹具助手，保留统一用例签名。

    Returns:
        CLI 移除状态和三处文档声明的对比结果。
    """

    # SKILL.md 是用户可见的功能边界声明。
    str_skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")  # skill 主说明文本

    # 脚本指南记录旧命令的明确退役版本。
    str_script_guide = (SKILL_DIR / "references" / "script-guide.md").read_text(  # CLI 退役说明
        encoding="utf-8"  # 脚本指南固定使用 UTF-8
    )  # CLI 参考指南文本

    # 评估场景文档证明退役行为仍被回归覆盖。
    str_scenarios = (SKILL_DIR / "references" / "evaluation-scenarios.md").read_text(  # 退役回归场景说明
        encoding="utf-8"  # 评估场景固定使用 UTF-8
    )  # 评估场景说明文本

    # CLI 帮助同时检查标准输出和错误输出，兼容 argparse 行为。
    tuple_help_result = run_script("manage_docs.py", "-h", cwd=REPO_ROOT)  # 帮助命令执行结果

    # 退出码和两路输出分别用于诊断与命令存在性判断。
    int_returncode, str_stdout, str_stderr = tuple_help_result  # 帮助命令结果字段

    # 合并文本避免旧命令从另一输出流逃过检查。
    str_help_text = str_stdout + str_stderr  # 完整 CLI 帮助文本

    # 有技能路径要求命令消失且所有治理文档同步声明退役。
    dict_with_checks = {  # evolution 退役合同断言
        "cli_removed": "import-evolution" not in str_help_text  # 旧命令是否从帮助中消失
        and " evolve " not in f" {str_help_text} ",  # 兼容旧命令别名的词边界检查
        "skill_declares_removal": (  # 技能旧子系统退役声明检查
            "removed evolution or experience subsystems" in str_skill_text  # 技能退役声明锚点
        ),  # 技能正文声明旧子系统已移除
        "script_guide_declares_removal": "removed evolution and experience commands remain invalid"  # 指南退役声明锚点
        in str_script_guide,  # 指南正文命中旧子系统退役合同
        "scenarios_cover_removal": "Evolution removed" in str_scenarios,  # 评估文档是否覆盖退役回归
    }

    # 旧版本基线仍暴露 evolution 合同，所有退役断言为假。
    dict_without_checks = {  # evolution 仍存在的历史基线
        "cli_removed": False,  # 旧基线仍暴露 evolution 命令
        "skill_declares_removal": False,  # 历史主说明不声明退役
        "script_guide_declares_removal": False,  # 历史脚本指南保留旧命令
        "scenarios_cover_removal": False,  # 历史场景不覆盖退役回归
    }

    # 返回码作为 CLI 探测健康度证据随评估结果保存。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={"help_returncode": int_returncode},
        without_skill_detail={
            "baseline": (
                "older versions still exposed evolution commands and atomic "
                "evolution contract docs"
            )
        },
    )

# experience 项目准备助手初始化治理配置、文档骨架和 memory。
def prepare_experience_project(path_root: Path, helper: EvalFixtures) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    """准备 experience 退役场景的治理项目。

    Args:
        path_root: 隔离场景根目录。
        helper: 提供标准 skill 治理配置的夹具助手。

    Returns:
        项目路径、脚手架结果和 memory 初始化结果。
    """

    # 模拟项目承载脚手架、memory 数据和交接记录。
    path_project = path_root / "workspace"  # experience 退役验证项目

    # 项目根与机器治理目录必须先于控制文件存在。
    path_project.mkdir()

    # 机器治理目录保存本场景的唯一控制配置。
    (path_project / ".agents").mkdir()

    # 标准 skill 回答生成完整文档与 memory 合同配置。
    dict_profile = helper.skill_answers(name="demo-skill")  # 模拟项目治理配置

    # 管理命令从唯一控制文件读取项目治理策略。
    (path_project / ".agents" / "agents-control.json").write_text(
        json.dumps(dict_profile),
        encoding="utf-8",
    )

    # 脚手架结果用于确认不再创建 docs/experience。
    dict_scaffold = run_json_script(  # 文档脚手架执行结果
        "manage_docs.py",  # 文档脚手架入口
        "scaffold",  # 请求生成标准治理文档骨架
        path_project,  # 接收标准文档骨架的隔离项目
    )

    # memory 初始化替代旧 experience 状态持久化职责。
    dict_memory_init = run_json_script(  # memory 初始化结果
        "manage_docs.py",  # memory 初始化入口
        "memory-init",  # 请求初始化替代 experience 的记忆后端
        path_project,  # 需要初始化记忆治理的项目
        "--confirm-create",  # 显式授权创建记忆存储
    )

    # 调用方继续执行多轮交接并汇总证据。
    return path_project, dict_scaffold, dict_memory_init

# 单轮交接载荷助手集中维护正式 handoff 所需字段。
def experience_handoff_payload(int_index: int) -> dict[str, list[str]]:
    """构造指定轮次的交接输入。

    Args:
        int_index: 从零开始的交接轮次索引。

    Returns:
        可序列化到 handoff 输入文件的字段映射。
    """

    # 每轮只改变当前步骤，其余字段保持稳定以隔离周期行为。
    return {  # 当前轮次交接载荷
        "original_plan": ["exercise v1.1.0 experience removal cadence"],  # 原始验证计划
        "current_step": [f"handoff {int_index + 1}"],  # 当前交接轮次
        "resolved": ["memory records handoff without experience governance"],  # 已验证的记忆接管事实
        "remaining": ["none"],  # 当前轮次无遗留工作
        "next": ["continue validation"],  # 下一轮继续验证交接计数
        "verification": ["eval handoff loop"],  # 本轮使用的回归证据
    }

# 多轮交接助手复现旧 experience 周期请求触发边界。
def run_experience_handoffs(path_project: Path) -> list[dict[str, Any]]:
    """连续执行五轮真实文档交接。

    Args:
        path_project: 已初始化 memory 的治理项目。

    Returns:
        按执行顺序保存的五轮交接结果。
    """

    # 五轮交接覆盖旧实现产生周期 experience 请求的边界。
    list_handoff_results: list[dict[str, Any]] = []  # 每轮交接命令结果

    # 每轮使用独立输入文件，避免命令复用旧载荷。
    for int_index in range(5):

        # 每轮独立路径保留交接输入证据。
        path_handoff_input = path_project / f"handoff-{int_index}.json"  # 当前轮次交接输入

        # 输入字段覆盖交接合同要求的计划、状态和验证证据。
        dict_handoff_input = experience_handoff_payload(int_index)  # 即将写盘的本轮 handoff 输入

        # 每次命令读取磁盘 JSON，贴近正式治理入口。
        path_handoff_input.write_text(
            json.dumps(dict_handoff_input, ensure_ascii=False),
            encoding="utf-8",
        )

        # 真实交接命令应把记录追加到 memory，而非 experience 请求。
        dict_handoff_result = run_json_script(  # 当前轮次交接结果
            "manage_docs.py",  # 正式交接治理入口
            "handoff",  # 请求写入正式交接记录
            path_project,  # 接收交接记录的治理项目
            "--input",  # 指定磁盘交接载荷
            path_handoff_input,  # 当前轮次独立输入文件
        )

        # 保存全部轮次以验证每次 memory 写入都成功。
        list_handoff_results.append(dict_handoff_result)

    # 五轮结果交由证据汇总助手统一检查。
    return list_handoff_results

# experience 状态读取助手汇总最终验证、状态键和交接事件数。
def read_experience_evidence(path_project: Path) -> tuple[dict[str, Any], dict[str, Any], int]:
    """读取五轮交接后的治理证据。

    Args:
        path_project: 已完成五轮交接的治理项目。

    Returns:
        最终验证结果、治理状态和交接事件数量。
    """

    # 五轮完成后执行正式文档治理验证。
    dict_verify = run_json_script(  # 最终文档治理验证结果
        "manage_docs.py",  # 文档治理验证入口
        "verify",  # 请求执行最终文档治理验证
        path_project,  # 已完成五轮交接的项目
    )

    # 状态文件不得残留旧 experience 周期字段。
    dict_state = json.loads(  # 最终文档治理状态映射
        (path_project / ".agents" / "docs-governance-state.json").read_text(  # 持久化治理状态文本
            encoding="utf-8"  # 状态文件固定使用 UTF-8
        )
    )  # 最终文档治理状态

    # JSONL 事件用于确认五次交接均进入 memory。
    str_events = (path_project / "docs" / "memory" / "events.jsonl").read_text(  # 五轮交接记忆事件流
        encoding="utf-8"  # JSONL 事件固定使用 UTF-8
    )  # memory 事件流文本

    # 事件计数兼容紧凑和带空格两种 JSON 序列化形式。
    int_handoff_event_count = sum(  # memory 中交接事件总数
        1  # 每个匹配事件贡献一次交接计数
        for str_line in str_events.splitlines()  # memory JSONL 中的逐行事件
        if '"kind": "handoff"' in str_line or '"kind":"handoff"' in str_line  # 兼容两种 JSON 间距
    )  # memory 中记录的交接事件数量

    # 三类证据由断言构建助手共同消费。
    return dict_verify, dict_state, int_handoff_event_count

# experience 断言助手把命令事实转换为稳定的回归检查。
def experience_checks(path_project: Path, dict_evidence: dict[str, Any]) -> dict[str, bool]:
    """构造 experience 退役场景的行为断言。

    Args:
        path_project: 当前隔离治理项目。
        dict_evidence: 脚手架、memory、交接、验证和状态证据。

    Returns:
        experience 退役与 memory 接管检查映射。
    """

    # 这些字段只属于已退役的 experience 周期治理。
    set_legacy_state_keys = {  # 禁止出现在新状态文件中的旧字段
        "last_experience_at",  # 旧体验更新时间字段
        "experience_update_required",  # 旧体验更新请求开关
        "experience_request_due_at",  # 旧体验请求到期时间
        "last_experience_handoff_count",  # 旧体验周期交接计数
        "experience_request_created_at",  # 旧体验请求创建时间
    }

    # 全部断言共同证明 experience 消失且 memory 完整接管。
    return {  # experience 退役后的行为断言
        "scaffold_succeeds": dict_evidence["scaffold"].get("errors") == [],  # 脚手架是否成功
        "scaffold_omits_experience_dir": not (path_project / "docs" / "experience").exists(),  # 是否省略旧体验目录
        "memory_init_succeeds": dict_evidence["memory_init"].get("errors") == [],  # memory 初始化是否无错误
        "fifth_handoff_no_experience_request": not (  # 第五次交接是否仍不生成旧请求
            path_project / ".agents" / "experience-update-request.json"  # 已退役的周期请求文件
        ).exists(),
        "state_has_no_experience_fields": not any(  # 状态是否清除全部旧字段
            str_key in dict_evidence["state"]  # 当前旧字段是否仍留在状态中
            for str_key in set_legacy_state_keys  # 全部禁止保留的 experience 字段
        ),
        "verify_passes_without_experience": dict_evidence["verify"].get("errors") == [],  # 无体验目录时验证是否通过
        "memory_records_handoffs": all(  # 每轮交接是否均写入 memory
            bool(dict_result.get("memory", {}).get("ok"))  # 当前交接的记忆写入状态
            for dict_result in dict_evidence["handoffs"]  # 五轮真实交接结果
        )
        and dict_evidence["handoff_event_count"] >= 5,  # 事件流至少包含五次交接
    }

# experience 退役场景验证五次交接后只使用 memory 治理。
def case_experience_removed_contract(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估 experience 目录和周期请求从文档治理中彻底移除。

    Args:
        case: 当前评估用例元数据。
        helper: 提供最小 skill 项目治理配置的夹具助手。

    Returns:
        脚手架、memory、交接和验证行为的对比结果。
    """

    # 临时项目允许连续执行真实文档治理命令而不污染仓库。
    with tempfile.TemporaryDirectory() as tmp:

        # 根目录承载交接项目及其五轮 memory 状态。
        path_root = Path(tmp)  # experience 退役场景隔离根

        # 专用助手准备治理项目、文档骨架和 memory 后端。
        tuple_prepared = prepare_experience_project(path_root, helper)  # 项目准备结果元组

        # 各准备结果使用独立类型语义变量，避免元组解包命名歧义。
        path_project: Path = tuple_prepared[0]  # 承载五轮交接的隔离项目根

        # 脚手架结果用于验证旧目录不再生成。
        dict_scaffold: dict[str, Any] = tuple_prepared[1]  # 文档脚手架结果

        # memory 初始化结果证明新后端已接管持久化职责。
        dict_memory_init: dict[str, Any] = tuple_prepared[2]  # 新记忆后端的创建状态

        # 五轮真实交接证明 memory 接管旧 experience 周期职责。
        list_handoff_results = run_experience_handoffs(path_project)  # 五轮交接命令结果

        # 最终验证、治理状态和事件计数构成验收事实。
        tuple_evidence = read_experience_evidence(path_project)  # 最终治理证据元组

        # 最终验证结果确认项目不依赖 experience 目录。
        dict_verify: dict[str, Any] = tuple_evidence[0]  # 最终文档验证结果

        # 状态映射用于检查旧周期字段已经删除。
        dict_state: dict[str, Any] = tuple_evidence[1]  # 最终治理状态

        # 事件计数确认五轮交接均写入 memory。
        int_handoff_event_count: int = tuple_evidence[2]  # memory 交接事件数

        # 聚合映射让断言助手只接收一个稳定证据边界。
        dict_evidence = {  # experience 退役命令与状态证据
            "scaffold": dict_scaffold,  # 用于确认体验目录缺席的脚手架证据
            "memory_init": dict_memory_init,  # 用于确认记忆后端可用的初始化证据
            "handoffs": list_handoff_results,  # 五轮交接结果
            "verify": dict_verify,  # 无 experience 依赖的最终验证证据
            "state": dict_state,  # 用于排查旧周期字段的状态快照
            "handoff_event_count": int_handoff_event_count,  # 五轮操作落入事件流的计数证据
        }

        # 稳定断言只依赖上述真实命令和磁盘状态。
        dict_with_checks = experience_checks(path_project, dict_evidence)  # experience 退役检查映射

        # 关键命令和最终状态键随结果返回用于失败诊断。
        dict_with_detail = {  # experience 退役运行证据
            "scaffold": dict_scaffold,  # 脚手架原始结果
            "memory_init": dict_memory_init,  # memory 初始化原始结果
            "fifth_handoff": list_handoff_results[-1],  # 第五轮交接原始结果
            "verify": dict_verify,  # 最终文档验证原始结果
            "state_keys": sorted(dict_state.keys()),  # 最终状态实际字段集合
        }

    # 旧 experience 基线会创建目录和周期请求，且不依赖 memory。
    dict_without_checks = {  # experience 旧治理基线
        "scaffold_succeeds": True,  # 旧脚手架本身可成功
        "scaffold_omits_experience_dir": False,  # 旧脚手架仍创建体验目录
        "memory_init_succeeds": False,  # 旧基线不初始化 memory
        "fifth_handoff_no_experience_request": False,  # 旧基线会生成周期请求
        "state_has_no_experience_fields": False,  # 旧状态仍包含体验字段
        "verify_passes_without_experience": False,  # 删除体验目录后旧验证失败
        "memory_records_handoffs": False,  # 旧交接不写入 memory
    }

    # 隔离目录退出后仍保留纯 JSON 证据，供汇总器比较。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail=dict_with_detail,
        without_skill_detail={
            "baseline": (
                "older experience governance scaffolded docs/experience and produced "
                "cadence requests around the fifth handoff instead of relying only on memory"
            ),
        },
    )

# 通用审计场景验证公共检查不依赖本项目私有文件。
def case_generic_audit_split(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估通用 skill 通过公共审计而不触发自治理专用合同。

    Args:
        case: 当前评估用例元数据。
        helper: 未使用的夹具助手，保留统一用例签名。

    Returns:
        通用审计错误、警告和脚本覆盖的对比结果。
    """

    # 临时目录构造不含 agents-md-generator 私有结构的合法 skill。
    with tempfile.TemporaryDirectory() as tmp:

        # skill 根包含标准脚本、agent 配置和说明文件。
        path_skill = Path(tmp) / "demo-skill"  # 通用审计夹具根

        # 公共审计识别 scripts 与 agents 两类标准目录。
        (path_skill / "scripts").mkdir(parents=True)

        # agents 目录提供最小代理资源边界。
        (path_skill / "agents").mkdir()

        # SKILL.md 明确引用待审计脚本和 agent 配置。
        list_skill_lines = [  # 通用 skill 主说明行
            "---",  # YAML frontmatter 起始边界
            "name: demo-skill",  # 示例技能的稳定名称
            "description: Use when testing generic skill audit behavior",  # 公共审计触发描述
            "---",  # 通用审计夹具 frontmatter 结束边界
            "# Demo Skill",  # 通用审计夹具正文标题
            "",  # 主说明标题前的空行
            "Use `scripts/validate_demo_skill.py` and `agents/openai.yaml`.",  # 公共审计应解析的双重引用
        ]

        # 尾部换行保持 Markdown 文件符合仓库文本约定。
        (path_skill / "SKILL.md").write_text(
            "\n".join(
                list_skill_lines
            )
            + "\n",
            encoding="utf-8",
        )

        # README 是通用 skill 可选说明，不应被私有发布规则误判。
        (path_skill / "README.md").write_text("# Demo Skill\n", encoding="utf-8")

        # agent 配置提供最小默认提示接口。
        (path_skill / "agents" / "openai.yaml").write_text(
            "interface:\n  default_prompt: placeholder\n",
            encoding="utf-8",
        )

        # 验证脚本保持成功退出，以隔离审计职责边界断言。
        (path_skill / "scripts" / "validate_demo_skill.py").write_text(
            "print('ok')\n",
            encoding="utf-8",
        )

        # 公共审计入口应接受该最小通用 skill。
        dict_audit = run_json_script(  # 通用 skill 审计结果
            "audit_skill.py",  # 公共审计入口
            path_skill,  # 接受公共审计的示例技能
            cwd=REPO_ROOT,  # 使用仓库正式审计运行时
        )

        # 有技能路径要求零诊断且确实检查引用的验证脚本。
        dict_with_checks = {  # 通用审计职责断言
            "errors_empty": dict_audit.get("errors") == [],  # 公共审计错误为空
            "warnings_empty": dict_audit.get("warnings") == [],  # 公共审计警告是否为空
            "generic_script_checked": PATH_GENERIC_VALIDATE_SCRIPT.as_posix()  # 是否覆盖通用验证脚本
            in dict_audit.get("checked", []),  # 公共审计实际检查路径
        }

        # 旧自审计实现会因缺少私有合同而拒绝通用 skill。
        dict_without_checks = {  # 私有审计错误套用的历史基线
            "errors_empty": False,  # 私有审计会产生错误
            "warnings_empty": False,  # 私有审计不具备无警告保证
            "generic_script_checked": False,  # 私有审计不覆盖通用验证脚本
        }

        # 完整审计载荷随结果返回用于失败定位。
        return build_case_result(
            case,
            with_skill_checks=dict_with_checks,
            without_skill_checks=dict_without_checks,
            with_skill_detail={"audit": dict_audit},
            without_skill_detail={
                "baseline": (
                    "legacy self-only audit would reject generic skills for missing "
                    "agents-md-generator private files and contracts"
                )
            },
        )

# 评估分类场景验证目标仓库行为错误拥有机器可读类别。
def case_evaluate_classification(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估失败验证脚本被归类为目标仓库行为错误。

    Args:
        case: 当前评估用例元数据。
        helper: 未使用的夹具助手，保留统一用例签名。

    Returns:
        evaluate 总状态、类别计数和命令分类的对比结果。
    """

    # 临时仓库包含一个故意失败的 skill 验证脚本。
    with tempfile.TemporaryDirectory() as tmp:

        # 目标根容纳标准 skills 布局和故意失败的验证脚本。
        path_root = Path(tmp)  # evaluate 分类场景仓库根

        # 标准 skills 布局确保 evaluate 使用目标仓库模式。
        path_skill = path_root / "skills" / "demo-skill"  # 待评估 skill 根目录

        # 脚本与配置目录形成最小可验证 skill。
        path_skill.mkdir(parents=True)

        # scripts 目录承载故意失败的验证入口。
        (path_skill / "scripts").mkdir()

        # config 目录承载技能引用的配置文件。
        (path_skill / "config").mkdir()

        # 主说明同时引用验证脚本和默认配置。
        str_skill_text = (
            "---\n"
            "name: demo-skill\n"
            "description: Use when testing evaluate classification\n"
            "---\n"
            "# Demo\n\n"
            "Use `scripts/validate_demo_skill.py` and `config/defaults.json`.\n"
        )  # 分类评估夹具的主说明

        # evaluate 从磁盘发现引用和可执行验证入口。
        (path_skill / "SKILL.md").write_text(
            str_skill_text,
            encoding="utf-8",
        )

        # 有效配置排除缺失引用等无关错误类别。
        (path_skill / "config" / "defaults.json").write_text(
            '{"mode":"demo"}\n',
            encoding="utf-8",
        )

        # 验证脚本故意失败以触发 target_repo_behavior_error。
        (path_skill / "scripts" / "validate_demo_skill.py").write_text(
            "raise SystemExit('expected validation failure')\n",
            encoding="utf-8",
        )

        # 正式 evaluate 入口返回聚合状态和机器可读错误分类。
        dict_result = run_json_script(  # 目标 skill 评估结果
            "evaluate_skill.py",  # 综合 skill 评估入口
            path_skill,  # 待综合评估的示例技能
            path_root,  # 隔离根作为综合评估目标项目
            cwd=REPO_ROOT,  # 使用仓库综合评估运行时
        )

        # 分类列表用于确认失败来自 validate_script 命令。
        list_classifications = dict_result.get("classified_errors", [])  # 机器可读错误分类记录

        # 有技能路径要求总状态失败且行为类别与命令来源明确。
        dict_with_checks = {  # evaluate 分类合同断言
            "evaluate_not_ok": not bool(dict_result.get("ok")),  # 故意失败是否反映到总状态
            "behavior_category_count": int(  # 行为失败是否进入分类计数
                dict_result.get("category_counts", {}).get(  # 综合评估分类计数映射
                    "target_repo_behavior_error",  # 目标项目行为错误分类
                    0,  # 分类不存在时按零次处理
                )
            )
            > 0,  # 行为失败分类是否至少出现一次
            "validate_classified": any(  # 验证失败是否进入目标行为错误分类
                dict_item.get("category") == "target_repo_behavior_error"  # 当前记录是否属于目标行为错误
                and dict_item.get("command") == "validate_script"  # 当前记录是否来自验证脚本
                for dict_item in list_classifications  # 综合评估返回的全部失败分类
            ),
        }

        # 旧输出只有扁平错误文本，不提供行为类别或命令来源。
        dict_without_checks = {  # 未分类 evaluate 历史基线
            "evaluate_not_ok": True,  # 旧输出同样可显示失败
            "behavior_category_count": False,  # 旧输出缺少行为分类计数
            "validate_classified": False,  # 旧输出不分类验证失败
        }

        # 完整 evaluate 载荷随结果保留以支持分类失败诊断。
        return build_case_result(
            case,
            with_skill_checks=dict_with_checks,
            without_skill_checks=dict_without_checks,
            with_skill_detail={"evaluate": dict_result},
            without_skill_detail={
                "baseline": (
                    "older evaluate output reported flat errors without "
                    "machine-readable behavior classification"
                )
            },
        )

# 发布完整性场景验证安装器拒绝主说明引用的缺失文件。
def case_install_release_completeness(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    """评估安装前的发布包引用完整性检查。

    Args:
        case: 当前评估用例元数据。
        helper: 提供有效发布收据的夹具助手。

    Returns:
        安装阻断状态和缺失引用诊断的对比结果。
    """

    # 临时导出目录模拟仓库外的降级保证发布包。
    with tempfile.TemporaryDirectory() as tmp:

        # 根目录承载仓库外的版本化导出包。
        path_root = Path(tmp)  # 安装完整性场景隔离根

        # 版本化目录命名满足安装器的发布来源合同。
        path_release_dir = path_root / "export" / "demo-skill-v0.4.3"  # 不完整发布目录

        # config 目录存在但故意缺少被引用的 defaults.json。
        (path_release_dir / "config").mkdir(parents=True)

        # scripts 目录承载已存在的验证入口。
        (path_release_dir / "scripts").mkdir(parents=True)

        # 主说明明确引用缺失配置，形成完整性检查目标。
        list_skill_lines = [  # 不完整发布包的主说明行
            "---",  # 发布完整性夹具 frontmatter 起始边界
            "name: demo-skill",  # 不完整发布包中的技能名称
            "description: Use when testing release completeness",  # 发布完整性测试描述
            "---",  # 发布完整性夹具 frontmatter 结束边界
            "# Demo Skill",  # 发布完整性夹具正文标题
            "",  # 发布说明标题与引用段之间的空行
            "Use `config/defaults.json` during validation.",  # 故意指向缺失配置的发布说明
        ]

        # 安装器从 SKILL.md 提取必须随包存在的相对引用。
        (path_release_dir / "SKILL.md").write_text(
            "\n".join(list_skill_lines) + "\n",
            encoding="utf-8",
        )

        # 有效验证脚本排除执行入口缺失等无关阻断。
        (path_release_dir / "scripts" / "validate_demo_skill.py").write_text(
            "print('ok')\n",
            encoding="utf-8",
        )

        # 收据准确记录现有文件，缺口只能由引用完整性检查发现。
        helper.make_release_receipt(
            path_release_dir,
            "demo-skill",
            "v0.4.3",
            validation_level="reduced_assurance",
        )

        # target=skip 运行全部验证但不写入真实 Codex skill 目录。
        tuple_install_result = run_script(  # 安装验证命令结果
            "install_skill.py",  # 正式安装验证入口
            path_release_dir,  # 接受安装校验的不完整发布目录
            "--target",  # 指定安装目标参数
            "skip",  # 仅验证发布包而不复制
            cwd=REPO_ROOT,  # 使用仓库正式安装运行时
        )

        # 返回码与两路输出分别证明阻断和可定位诊断。
        int_returncode, str_stdout, str_stderr = tuple_install_result  # 安装验证结果字段

        # 合并输出兼容诊断写入 stdout 或 stderr 的实现差异。
        str_combined = str_stdout + str_stderr  # 完整安装诊断文本

        # 有技能路径必须阻断并明确指出缺失的配置引用。
        dict_with_checks = {  # 发布包引用完整性断言
            "install_blocked": int_returncode != 0,  # 缺失引用是否阻止安装
            "missing_reference_reported": PATH_MISSING_DEFAULTS.as_posix() in str_combined,  # 安装错误是否定位缺失配置
        }

        # 旧安装检查只验证收据形状，无法发现说明文件引用缺口。
        dict_without_checks = {  # 不完整发布包被接受的历史基线
            "install_blocked": False,  # 旧安装器会放行不完整包
            "missing_reference_reported": False,  # 旧安装器不报告缺失引用
        }

        # 原始输出随结果保留，便于确认具体安装阻断原因。
        return build_case_result(
            case,
            with_skill_checks=dict_with_checks,
            without_skill_checks=dict_without_checks,
            with_skill_detail={"stdout": str_stdout, "stderr": str_stderr},
            without_skill_detail={
                "baseline": (
                    "pre-completeness install validation only confirmed receipt shape "
                    "and could miss SKILL.md referenced content gaps"
                )
            },
        )

# 受管技能需要仓库根提供拆分计划和治理配置。
def managed_project_root(path_skill_dir: Path) -> Path:
    """解析外部技能可用的受管项目根。

    参数：path_skill_dir 为待评估技能根目录。
    返回：标准 skills 布局下的受管仓库根；未发现时返回技能根。
    """

    # 规范路径用于比较候选根下的标准技能位置。
    path_resolved_skill = path_skill_dir.resolve()  # 外部技能规范路径

    # 由近到远查找同时具备治理标记和标准技能布局的祖先。
    for path_candidate in (path_resolved_skill, *path_resolved_skill.parents):

        # 控制文件证明候选目录是受管项目根。
        path_control = path_candidate / ".agents" / "agents-control.json"  # 项目治理标记

        # 标准布局绑定同名技能，避免借用无关祖先治理。
        path_expected_skill = path_candidate / "skills" / path_resolved_skill.name  # 候选技能位置

        # 两项事实同时匹配时才扩大项目边界。
        if path_control.is_file() and path_expected_skill.resolve() == path_resolved_skill:

            # 返回最近的可信受管根。
            return path_candidate

    # 独立安装技能保持自身最小项目边界。
    return path_resolved_skill

# 外部通用 skill 健康场景复用公共 audit 和 evaluate 入口。
def case_external_generic_health(skill_dir: Path, case: dict[str, Any]) -> dict[str, Any]:
    """评估调用方提供的外部通用 skill 健康状态。

    Args:
        skill_dir: 外部 skill 根目录；受管项目根由目录事实解析。
        case: 当前评估用例元数据。

    Returns:
        公共审计和综合评估状态的对比结果。
    """

    # 受管源码技能从仓库根读取治理计划，独立安装保持自身边界。
    path_project_root = managed_project_root(skill_dir)  # 外部技能评估项目根

    # 综合评估先完成其拥有的瞬态缓存清理生命周期。
    dict_evaluate = run_json_script(  # 外部 skill 综合评估结果
        "evaluate_skill.py",  # 外部 skill 综合评估入口
        skill_dir,  # 外部调用方指定的评估技能
        path_project_root,  # 受管仓库根或独立技能最小边界
        cwd=REPO_ROOT,  # 外部健康检查复用正式综合评估运行时
    )

    # 严格审计随后检查综合评估留下的最终技能状态。
    dict_audit = run_json_script(  # 外部 skill 公共审计结果
        "audit_skill.py",  # 外部 skill 公共审计入口
        skill_dir,  # 外部调用方指定的技能目录
        cwd=REPO_ROOT,  # 使用仓库公共审计运行时
    )

    # 有技能路径要求两层健康检查同时通过。
    dict_with_checks = {  # 外部通用 skill 健康断言
        "audit_green": dict_audit.get("errors") == [],  # 公共审计是否无错误
        "evaluate_green": bool(dict_evaluate.get("ok")),  # 综合评估是否整体健康
    }

    # 无评估工具基线不提供任何外部 skill 健康证据。
    dict_without_checks = {  # 缺少健康检查的基线
        "audit_green": False,  # 基线无公共审计证据
        "evaluate_green": False,  # 基线无综合评估证据
    }

    # 两层原始载荷随结果返回以区分结构或行为失败。
    return build_case_result(
        case,
        with_skill_checks=dict_with_checks,
        without_skill_checks=dict_without_checks,
        with_skill_detail={"audit": dict_audit, "evaluate": dict_evaluate},
        without_skill_detail={"baseline": "no external-skill confidence evidence"},
    )

