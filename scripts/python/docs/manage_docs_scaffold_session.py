"""维护文档治理脚手架、会话启动、恢复检查和 handoff 写入逻辑。"""

# 延迟注解求值，保持 Python 3.10 运行兼容性。
from __future__ import annotations

# 标准库负责时间、JSON、文件移动、路径和类型注解。
from datetime import datetime
import json
from pathlib import Path
import shutil
from typing import Any

# 显式导入会话、交接和脚手架职责所依赖的共享合同。
from manage_docs_shared import (
    # 文档结构与 handoff 命名常量。
    DOC_DIRS,
    HANDOFF_CURRENT_FILENAME,
    HANDOFF_HISTORY_DIRNAME,
    HANDOFF_HISTORY_RE,
    REQUIRED_DOC_FILES,
    STATE_PATH,

    # 会话、命名审计和遗留资产辅助函数。
    active_session_file,
    audit_handoff_naming,
    cleanup_legacy_evolution_artifacts,
    conversation_snapshot_dir,

    # 默认文档渲染和路径辅助函数。
    default_development_record,
    default_git_changelog,
    default_handoff,

    # docs、Git 和 handoff 正式路径解析函数。
    docs_root,
    file_hash,
    git_changelog_file,
    git_history_root,
    git_manager_doc,
    handoff_paths,

    # 共享状态、文本和时间处理函数。
    install_configuration_doc,
    list_lines,
    load_state,

    # handoff 内容识别和生成时间解析函数。
    looks_like_handoff_markdown,
    parse_handoff_generated_at,
    project_profile,
    read_json,

    # 状态写入、时间戳和唯一历史路径函数。
    save_state,
    stamp,
    unique_handoff_history_path,
)
from manage_docs_memory import init_memory, memory_enabled, memory_read_recommendation, write_handoff_memory
from manage_docs_sync_verify import verify_docs
from manage_dirs import CURRENT_STRUCTURE, DIR_MANAGER_MD, PLANNED_STRUCTURE, init_dir_manager

# 在写入 docs 脚手架前识别安全、冲突和待确认状态。
def preflight_docs(project: Path) -> dict[str, Any]:
    """检查 docs 现状是否允许初始化治理脚手架。

    参数：project 为待检查的项目根目录。
    返回：包含状态、冲突清单和用户确认要求的预检结果。
    """

    # docs 根是后续保留路径和文件类型检查的共同基准。
    path_docs = docs_root(project)  # 项目 docs 根目录

    # 仅在现有结构有歧义或冲突时向用户请求写入授权。
    str_question = "是否允许在现有 docs/ 下添加 AGENTS.md governance 子目录和记录文件？"  # 冲突确认问题

    # 不存在的 docs 根可以由脚手架安全创建。
    if not path_docs.exists():

        # 新项目无需用户确认即可初始化完整文档结构。
        return {
            "project": str(project),  # 新建 docs 的项目根
            "status": "safe",  # 预检结论
            "docs_exists": False,  # docs 根不存在
            "safe_to_scaffold": True,  # 允许直接初始化
            "conflicts": [],  # 没有既有结构冲突
            "requires_user_confirmation": False,  # 无需额外授权
            "question": "",  # 不生成确认问题
        }

    # 同名普通文件会阻止创建 docs 目录。
    if not path_docs.is_dir():

        # 文件类型冲突必须由用户处理或明确授权后再继续。
        return {
            "project": str(project),  # 已验证项目根
            "status": "conflict",  # 明确的路径类型冲突
            "docs_exists": True,  # docs 名称已被占用
            "safe_to_scaffold": False,  # 禁止直接初始化
            "conflicts": ["docs exists but is not a directory"],  # 冲突原因
            "requires_user_confirmation": True,  # 需要用户决策
            "question": str_question,  # 显示统一确认问题
        }

    # 保留目录和必需文档共同构成脚手架占用的路径集合。
    list_reserved_paths = [*DOC_DIRS, *REQUIRED_DOC_FILES]  # 受管 docs 路径

    # 冲突清单只记录路径类型不符合合同的条目。
    list_conflicts: list[str] = []  # 预检发现的路径冲突

    # 该标志区分未初始化目录与部分初始化的受管结构。
    bool_reserved_exists = False  # 是否已有受管路径

    # 逐项核对保留路径的目录或文件类型。
    for rel_path in list_reserved_paths:

        # 当前绝对路径用于执行存在性和类型判断。
        path_reserved = project / rel_path  # 当前受管路径

        # 只有已存在的保留路径才可能产生兼容性冲突。
        if path_reserved.exists():

            # 任一命中都表示 docs 已经存在部分治理结构。
            bool_reserved_exists = True  # 已发现受管路径

            # 目录合同不接受同名普通文件。
            if rel_path in DOC_DIRS and not path_reserved.is_dir():

                # 保留具体相对路径，便于用户定位目录冲突。
                list_conflicts.append(f"{rel_path} exists but is not a directory")

            # 必需文档合同不接受同名目录或其他非文件对象。
            if rel_path in REQUIRED_DOC_FILES and not path_reserved.is_file():

                # 文件类型错误与目录冲突分开报告。
                list_conflicts.append(f"{rel_path} exists but is not a file")

    # 完整 verifier 负责检查已有文档内容和同步合同。
    dict_docs_result = verify_docs(project)  # docs 治理验证结果

    # 已有结构完全合规时，脚手架操作是幂等且安全的。
    if not dict_docs_result["errors"]:

        # 合规 docs 根可以直接刷新缺省治理文件。
        return {
            "project": str(project),  # 被检查项目
            "status": "safe",  # 已有结构验证通过
            "docs_exists": True,  # docs 根已存在
            "safe_to_scaffold": True,  # 允许幂等刷新
            "conflicts": [],  # verifier 未发现错误
            "requires_user_confirmation": False,  # 合规结构无需确认
            "question": "",  # 合规路径没有提问
        }

    # 部分受管结构存在时，verifier 错误属于明确治理冲突。
    if bool_reserved_exists:

        # 合并内容错误，同时避免重复报告已识别的类型冲突。
        list_conflicts.extend(item for item in dict_docs_result["errors"] if item not in list_conflicts)

        # 不完整的受管结构需要用户确认后才能覆盖或补齐。
        return {
            "project": str(project),  # 冲突结构所属项目
            "status": "conflict",  # 已有治理结构不合规
            "docs_exists": True,  # 冲突 docs 根确实存在
            "safe_to_scaffold": False,  # 禁止无授权覆盖
            "conflicts": list_conflicts,  # 类型与内容错误合集
            "requires_user_confirmation": True,  # 冲突写入必须授权
            "question": str_question,  # 冲突场景确认问题
        }

    # 普通 docs 内容需要完整列出，供用户判断是否允许接管。
    list_existing_paths = [  # 现有 docs 相对路径
        path_entry.relative_to(project).as_posix()  # 项目相对路径文本
        for path_entry in sorted(path_docs.rglob("*"))  # 稳定排序的 docs 条目
        if path_entry.is_file() or path_entry.is_dir()  # 排除特殊文件系统对象
    ]

    # 空目录也要给出明确的“尚未初始化”原因。
    list_conflicts = list_existing_paths or [  # 歧义场景展示内容
        "docs/ exists but AGENTS.md governance structure is not initialized"  # 空 docs 的歧义原因
    ]  # 需要用户审阅的既有结构

    # 未命中保留路径的既有 docs 属于待用户判断的歧义状态。
    return {
        "project": str(project),  # 歧义 docs 所属项目
        "status": "ambiguous",  # 普通 docs 与治理结构关系未知
        "docs_exists": True,  # 普通 docs 根已经存在
        "safe_to_scaffold": False,  # 未授权前禁止写入
        "conflicts": list_conflicts,  # 展示既有 docs 内容
        "requires_user_confirmation": True,  # 请求用户确认接管
        "question": str_question,  # 歧义场景接管问题
    }

# 在覆盖 DEVELOPMENT.md 前归档已有的有效开发记录。
def rotate_current_development_if_needed(project: Path) -> str:
    """按需将当前开发记录移动到带时间戳的历史目录。

    参数：project 为项目根目录。
    返回：归档文件的项目相对路径；无需归档时返回空字符串。
    """

    # 当前开发记录是判断是否需要轮换的唯一正式入口。
    path_current = project / "docs" / "development" / "DEVELOPMENT.md"  # 当前开发记录

    # 首次初始化尚无开发记录，因此没有归档对象。
    if not path_current.exists():

        # 空路径明确表示本次没有产生历史文件。
        return ""

    # 文本内容用于区分默认占位记录与真实开发事实。
    str_current_record = path_current.read_text(encoding="utf-8", errors="ignore")  # 当前记录正文

    # 未记录版本和状态的默认模板不值得进入历史归档。
    if "- Version: not recorded" in str_current_record and "- Status: not recorded" in str_current_record:

        # 保留占位文件供后续写入流程直接覆盖。
        return ""

    # 每次轮换使用独立时间戳目录，避免覆盖旧开发记录。
    path_history_dir = project / "docs" / "development" / "history_development" / stamp()  # 本次归档目录

    # 父目录可能尚未由脚手架创建，需要递归补齐。
    path_history_dir.mkdir(parents=True, exist_ok=True)

    # 历史文件保留正式文件名，日期由父目录表达。
    path_archived = path_history_dir / "DEVELOPMENT.md"  # 归档后的开发记录

    # 移动而非复制，确保后续写入创建唯一的当前记录。
    shutil.move(str(path_current), str(path_archived))

    # 调用方只需要可记录在 JSON 结果中的项目相对路径。
    return path_archived.relative_to(project).as_posix()

# 将仓库根或旧 docs 根中的记录迁移到当前治理目录。
def migrate_legacy_docs(project: Path) -> list[str]:
    """迁移旧版 handoff 和 development 文件并保留现有历史。

    参数：project 为项目根目录。
    返回：本次迁移目标的项目相对路径列表。
    """

    # 结果列表按 handoff、development 的稳定顺序记录迁移产物。
    list_migrated: list[str] = []  # 已迁移文件路径

    # 旧版文件可能直接位于 docs 根，需要作为第二候选位置检查。
    path_docs_root = project / "docs"  # 旧版文档候选根

    # 仓库根位置优先于旧 docs 根位置，避免同名来源不确定。
    list_legacy_handoffs = [project / "HANDOFF.md", path_docs_root / "HANDOFF.md"]  # handoff 迁移来源

    # 所有旧 handoff 最终归一到当前正式文件路径。
    path_handoff_target = project / "docs" / "handoff" / "HANDOFF.md"  # 正式 handoff 目标

    # 只迁移第一个实际存在的 handoff 来源。
    for path_legacy in list_legacy_handoffs:

        # 非文件候选不参与迁移，避免移动目录或特殊对象。
        if path_legacy.exists() and path_legacy.is_file():

            # 正式 handoff 已存在时先轮换，防止迁移覆盖当前记录。
            if path_handoff_target.exists():

                # 轮换函数负责生成唯一的历史文件名。
                rotate_handoff(project)

            # 旧项目可能尚未建立正式 handoff 目录。
            path_handoff_target.parent.mkdir(parents=True, exist_ok=True)

            # 移动来源可避免旧路径继续被其他工具误识别。
            shutil.move(str(path_legacy), str(path_handoff_target))

            # 对外结果使用跨平台的项目相对路径。
            list_migrated.append(path_handoff_target.relative_to(project).as_posix())

            # 单一正式 handoff 只允许选择一个旧来源。
            break

    # development 迁移使用与 handoff 相同的候选优先级。
    list_legacy_developments = [
        project / "DEVELOPMENT.md",  # 仓库根旧开发记录
        path_docs_root / "DEVELOPMENT.md",  # docs 根旧开发记录
    ]  # 开发记录迁移候选

    # 旧开发记录统一迁移到当前 development 正式位置。
    path_development_target = project / "docs" / "development" / "DEVELOPMENT.md"  # 正式开发记录目标

    # development 同样只接受首个存在的来源。
    for path_legacy in list_legacy_developments:

        # 候选必须是普通文件才能进入迁移流程。
        if path_legacy.exists() and path_legacy.is_file():

            # 正式记录存在时先按内容决定是否需要归档。
            if path_development_target.exists():

                # 占位记录会保留原位，真实记录会移动到历史目录。
                rotate_current_development_if_needed(project)

            # 确保迁移目标的父目录在旧项目中存在。
            path_development_target.parent.mkdir(parents=True, exist_ok=True)

            # 将唯一来源移动到当前正式开发记录位置。
            shutil.move(str(path_legacy), str(path_development_target))

            # 记录迁移后的项目相对路径供命令结果展示。
            list_migrated.append(path_development_target.relative_to(project).as_posix())

            # 找到首个来源后停止，避免第二个候选覆盖结果。
            break

    # 空列表表示没有发现任何旧版文档。
    return list_migrated

# 创建或刷新 docs 治理所需的目录、文件、状态和记忆资产。
def scaffold(project: Path, refresh_existing_state: bool = True) -> dict[str, Any]:
    """幂等初始化文档治理结构并同步目录与记忆状态。

    参数：project 为项目根目录。
    参数：refresh_existing_state 控制是否强制刷新目录管理资产。
    返回：包含创建、迁移、清理、记忆和错误信息的结果映射。

    数组契约：本函数不处理数值数组；shape、dtype 和 unit 均不适用。
    """

    # 所有新建路径统一收集，供 CLI 和测试确认幂等结果。
    list_created: list[str] = []  # 本次创建或刷新路径

    # 项目画像决定 GIT_MANAGER.md 等默认内容的项目类型字段。
    dict_profile = project_profile(project)  # 当前项目控制画像

    # 先建立全部受管目录，确保后续文件写入无需单独创建父目录。
    for rel_path in DOC_DIRS:

        # 当前目录路径由项目根和治理合同中的相对路径组成。
        path_directory = project / rel_path  # 待检查的受管目录

        # 已存在目录保持不变，避免幂等调用重复报告创建。
        if not path_directory.exists():

            # 递归创建可以兼容尚无 docs 根的空项目。
            path_directory.mkdir(parents=True, exist_ok=True)

            # 目录结果保留治理合同中的相对路径格式。
            list_created.append(rel_path)

    # 旧版根级文档必须先迁移，避免默认文件覆盖真实记录。
    list_migrated = migrate_legacy_docs(project)  # 已迁移的旧文档

    # handoff 命名冲突会阻止创建新的当前 handoff。
    dict_handoff_naming = audit_handoff_naming(project)  # handoff 命名审计结果

    # 默认正文只用于缺失文件，不覆盖迁移或用户维护的内容。
    dict_default_files = {  # 受管文件及其默认正文
        "docs/handoff/HANDOFF.md": default_handoff(),  # 当前交接模板
        "docs/development/DEVELOPMENT.md": default_development_record(),  # 当前开发记录模板
        "docs/install_configuration/INSTALL_CONFIGURATION.md": install_configuration_doc(),  # 安装配置模板
        "docs/git_manager/GIT_MANAGER.md": git_manager_doc(project, dict_profile),  # Git 治理说明
        "docs/git_manager/CHANGELOG.md": default_git_changelog(),  # 当前变更日志模板
    }

    # 按映射顺序写入所有尚不存在的默认文档。
    for rel_path, str_content in dict_default_files.items():

        # 命名审计阻断时保留现场，不创建可能掩盖冲突的新 handoff。
        if rel_path == "docs/handoff/HANDOFF.md" and dict_handoff_naming["blocking"]:

            # 其他默认文档仍可独立初始化。
            continue

        # 文件绝对路径用于存在性判断和 UTF-8 写入。
        path_document = project / rel_path  # 当前默认文档路径

        # 已存在文件始终由用户或既有流程拥有，不在脚手架中覆盖。
        if not path_document.exists():

            # 默认治理文档统一使用 UTF-8 编码。
            path_document.write_text(str_content, encoding="utf-8")

            # 返回结果记录实际写入的项目相对路径。
            list_created.append(rel_path)

    # 状态文件承载 handoff 计数和目录扫描时间等持久事实。
    dict_state = load_state(project)  # docs 治理状态

    # 在加载缺省值后单独记录文件是否原本缺失。
    bool_state_missing = not (project / STATE_PATH).exists()  # 状态文件原先是否缺失

    # 旧状态没有计数字段时从零开始，保留已有计数。
    dict_state.setdefault("handoff_count", 0)

    # 清理过程同步移除已退休 evolution 字段和遗留文件。
    dict_cleanup = cleanup_legacy_evolution_artifacts(project, dict_state)  # 遗留资产清理结果

    # 显式刷新或任一目录管理资产缺失时都要重新生成目录快照。
    bool_refresh_dir_manager = refresh_existing_state or any(  # 是否刷新目录管理资产
        not (project / rel_path).exists()  # 当前资产是否缺失
        for rel_path in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]  # 必需目录管理资产
    )

    # 刷新路径同时更新扫描时间并保存最新状态。
    if bool_refresh_dir_manager:

        # 秒级时间满足文档展示和状态比较，不引入无意义微秒差异。
        dict_state["dir_manager_last_scan"] = datetime.now().isoformat(timespec="seconds")  # 最近目录扫描时间

        # 先保存扫描时间，使目录管理器读取到一致状态。
        save_state(project, dict_state)

        # 目录管理器负责写入说明、当前结构和规划结构文件。
        dict_dir_result = init_dir_manager(project)  # 目录管理初始化结果

        # 合并目录管理器产物，同时保持 created 列表无重复项。
        list_created.extend(path for path in dict_dir_result.get("written", []) if path not in list_created)

    # 未刷新目录资产时，首次创建仍必须落盘缺省状态。
    elif bool_state_missing:

        # 保存 handoff_count 等基础字段供后续会话命令使用。
        save_state(project, dict_state)

    # 未启用记忆时保持 None，以区别“已运行且无新增”的结果。
    dict_memory_result: dict[str, Any] | None = None  # 记忆初始化结果

    # handoff 命名错误始终进入脚手架顶层错误清单。
    list_errors = list(dict_handoff_naming["errors"])  # 汇总错误信息

    # 仅在项目画像启用记忆时创建数据库和事件资产。
    if memory_enabled(project):

        # 初始化函数返回创建路径和任何存储错误。
        dict_memory_result = init_memory(project)  # 已启用记忆的初始化结果

        # 将记忆资产加入统一 created 清单并保持去重。
        list_created.extend(path for path in dict_memory_result.get("created", []) if path not in list_created)

        # 错误前缀标明来源，便于 CLI 使用者定位记忆子系统。
        list_errors.extend(f"memory: {item}" for item in dict_memory_result.get("errors", []))

    # 结果保留既有 JSON 字段，供 CLI、测试和恢复流程稳定消费。
    return {
        "project": str(project),  # 项目根路径
        "created": list_created,  # 本次创建或刷新资产
        "migrated": list_migrated,  # 旧版文档迁移结果
        "state": dict_state,  # 最新 docs 治理状态
        "cleanup": dict_cleanup,  # scaffold 清理证据
        "memory": dict_memory_result,  # 可选记忆初始化结果
        "handoff_naming": dict_handoff_naming,  # handoff 命名审计
        "errors": list_errors,  # 所有子流程错误
    }

# 读取可选 JSON 输入并强制顶层对象合同。
def read_input(path: str | None) -> dict[str, Any]:
    """读取命令输入文件并验证其顶层为 JSON 对象。

    参数：path 为可选输入文件路径。
    返回：输入对象；未提供路径时返回空映射。
    异常：顶层不是对象时抛出 SystemExit。
    """

    # 无输入文件表示调用方接受命令的全部缺省字段。
    if not path:

        # 新映射避免调用方意外共享可变缺省对象。
        return {}

    # 绝对路径消除命令工作目录变化造成的输入歧义。
    dict_data = read_json(Path(path).resolve())  # 已解析 JSON 内容

    # 会话和 handoff 命令只接受具名字段对象，不接受数组或标量。
    if not isinstance(dict_data, dict):

        # 错误包含原始路径，便于 CLI 使用者修正输入来源。
        raise SystemExit(f"> ERR: [Python] input must be a JSON object: {path}")

    # 验证后的对象可安全交给各命令读取字段。
    return dict_data

# 将当前 handoff 移入唯一命名的历史文件。
def rotate_handoff(project: Path) -> str | None:
    """按需归档当前 handoff，避免新交接覆盖历史。

    参数：project 为项目根目录。
    返回：归档文件的项目相对路径；无当前文件时返回 None。
    """

    # 共享路径解析器集中维护当前文件和历史目录合同。
    dict_paths = handoff_paths(project)  # handoff 路径集合

    # 当前文件是唯一需要移动的正式 handoff。
    path_current = dict_paths["current"]  # 当前 handoff 路径

    # 首次写入没有历史来源，直接通知调用方未归档。
    if not path_current.exists():

        # None 与空字符串区分“没有文件”和路径文本。
        return None

    # 历史目录统一存放所有带时间戳的旧 handoff。
    path_history = dict_paths["history"]  # handoff 历史目录

    # 旧项目可能尚未初始化历史目录，需要递归创建。
    path_history.mkdir(parents=True, exist_ok=True)

    # 唯一路径生成器处理同秒多次写入的文件名冲突。
    path_target = unique_handoff_history_path(path_history, datetime.now())  # 本次归档目标

    # 移动保证当前位置为空，供新 handoff 原子式写入。
    shutil.move(str(path_current), str(path_target))

    # 项目相对路径适合写入 JSON 结果和审计记录。
    return path_target.relative_to(project).as_posix()

# 按固定章节顺序渲染当前 handoff Markdown。
def handoff_markdown(data: dict[str, Any], count: int) -> str:
    """将结构化交接数据渲染为标准 handoff 文档。

    参数：data 为交接字段映射。
    参数：count 为递增后的 handoff 序号。
    返回：包含所有必需章节的 Markdown 文本。
    """

    # 兼容设计画像使用的完整字段名以及早期 plan 别名。
    value_original_plan = data.get("original_plan_and_steps") or data.get("original_plan") or data.get("plan")  # 原始计划内容

    # 固定章节即使没有内容也会由 list_lines 渲染明确占位文本。
    return "\n".join([
        "# Handoff",  # 文档标题
        "",  # 标题与元数据分隔
        f"- Handoff count: {count}",  # 递增交接序号
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",  # 生成时间
        "",  # 元数据与章节分隔
        "## Original Plan And Steps",  # 原始计划章节
        list_lines(value_original_plan),  # 原始计划条目
        "",  # 计划与当前步骤分隔
        "## Current Step",  # 当前步骤章节
        list_lines(data.get("current_step")),  # 当前执行位置
        "",  # 当前步骤与问题分隔
        "## Problems",  # 当前问题章节
        list_lines(data.get("problems")),  # 未解决问题条目
        "",  # 问题与已解决项分隔
        "## Resolved Problems",  # 已解决问题章节
        list_lines(data.get("resolved") or data.get("resolved_problems")),  # 已解决条目
        "",  # 已解决项与剩余项分隔
        "## Remaining Problems",  # 剩余问题章节
        list_lines(data.get("remaining") or data.get("remaining_problems")),  # 剩余问题条目
        "",  # 剩余项与后续工作分隔
        "## Next Work",  # 后续工作章节
        list_lines(data.get("next") or data.get("next_work")),  # 后续动作条目
        "",  # 后续工作与验证分隔
        "## Verification Evidence",  # 验证证据章节
        list_lines(data.get("verification") or data.get("verification_evidence")),  # 验证证据条目
        "",  # 保留文档末尾换行
    ])

# 在 handoff 输入包含对话证据时写入受管快照。
def maybe_write_conversation_snapshot(project: Path, data: dict[str, Any], count: int) -> str | None:
    """按需保存对话摘要、摘录和日志片段。

    参数：project 为项目根目录。
    参数：data 为 handoff 输入字段。
    参数：count 为当前 handoff 序号。
    返回：快照的项目相对路径；没有对话证据时返回 None。
    """

    # 仅这三个输入字段属于可持久化的对话证据范围。
    dict_fields = {  # 对话证据字段
        "conversation_summary": data.get("conversation_summary"),  # 对话摘要
        "conversation_excerpt": data.get("conversation_excerpt"),  # 对话摘录
        "conversation_log_path": data.get("conversation_log_path"),  # 原始日志路径
    }

    # 三个字段全部为空时不创建无意义的快照文件。
    if not any(str(value or "").strip() for value in dict_fields.values()):

        # None 明确表示调用方无需记录 conversation_snapshot。
        return None

    # 快照目录由共享路径合同定位，避免各命令自行拼接。
    path_snapshot_dir = conversation_snapshot_dir(project)  # 对话快照目录

    # 首次捕获对话证据时递归创建目录。
    path_snapshot_dir.mkdir(parents=True, exist_ok=True)

    # 日志不可用时保留空摘录，不阻断摘要和显式摘录的保存。
    str_log_excerpt = ""  # 从日志文件读取的有限摘录

    # 原始路径文本写入快照，解析路径仅用于本地读取。
    str_log_path = str(dict_fields.get("conversation_log_path") or "").strip()  # 输入日志路径文本

    # 只有调用方提供路径时才尝试读取外部日志。
    if str_log_path:

        # Path 对象用于判断绝对路径和文件边界。
        path_log = Path(str_log_path)  # 待读取的对话日志

        # 相对日志路径以项目根为基准，保持 CLI 行为确定。
        if not path_log.is_absolute():

            # 拼接后的路径只用于读取，不改变快照中记录的原始文本。
            path_log = project / path_log  # 项目内日志绝对位置

        # 目录或缺失路径不会作为文本读取，也不会阻断 handoff。
        if path_log.exists() and path_log.is_file():

            # 八千字符上限防止大型日志显著膨胀治理仓库。
            str_log_excerpt = path_log.read_text(encoding="utf-8", errors="ignore")[:8000]  # 有界日志摘录

    # 快照保留 handoff 关联、捕获时间和全部可用对话证据。
    dict_snapshot = {  # 对话快照内容
        "handoff_count": count,  # 关联的 handoff 序号
        "captured_at": datetime.now().isoformat(timespec="seconds"),  # 捕获时间
        "source": "handoff input",  # 证据来源类型
        "conversation_summary": dict_fields.get("conversation_summary") or "",  # 输入摘要
        "conversation_excerpt": dict_fields.get("conversation_excerpt") or "",  # 输入摘录
        "conversation_log_path": str_log_path,  # 输入日志路径
        "conversation_log_excerpt": str_log_excerpt,  # 文件日志摘录
    }

    # 时间戳和 handoff 序号共同降低快照命名冲突风险。
    path_target = path_snapshot_dir / f"{stamp()}-handoff-{count}.json"  # 快照输出文件

    # 稳定排序和缩进便于代码审查及后续证据读取。
    path_target.write_text(
        json.dumps(dict_snapshot, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # 项目相对路径可安全写入 handoff 结果和状态文件。
    return str(path_target.relative_to(project).as_posix())

# 写入新 handoff，并同步归档、状态、会话和记忆证据。
def write_handoff(project: Path, input_path: str | None) -> dict[str, Any]:
    """完成一次受管 handoff 写入事务。

    参数：project 为项目根目录。
    参数：input_path 为可选 handoff JSON 输入路径。
    返回：写入、归档、计数、快照、记忆及错误结果。
    """

    # 写入前补齐受管目录和默认资产，并复用其阻断错误。
    dict_scaffold_result = scaffold(project)  # 脚手架初始化结果

    # 目录、命名或记忆初始化错误会阻止 handoff 覆盖当前文件。
    if dict_scaffold_result.get("errors"):

        # 阻断结果保留命名审计详情供调用方修复现场。
        return {
            "project": str(project),  # 被处理项目
            "errors": dict_scaffold_result["errors"],  # 脚手架阻断错误
            "handoff_naming": dict_scaffold_result.get("handoff_naming", {}),  # 命名审计详情
        }

    # 先归档旧 handoff，确保当前位置只保留最新交接。
    str_archived = rotate_handoff(project)  # 可选历史 handoff 路径

    # 持久状态提供当前 handoff_count 和已退休字段现场。
    dict_state = load_state(project)  # handoff 计数状态

    # handoff 写入同时清除旧 evolution 资产，避免状态继续漂移。
    cleanup_legacy_evolution_artifacts(project, dict_state)

    # 新 handoff 使用严格递增序号，不依赖历史文件数量推断。
    int_count = int(dict_state.get("handoff_count", 0)) + 1  # 本次 handoff 序号

    # 输入读取器保证顶层对象合同，缺省时提供空映射。
    dict_data = read_input(input_path)  # 结构化 handoff 输入

    # 当前 handoff 路径由共享合同定位，避免重复拼接。
    path_target = handoff_paths(project)["current"]  # 当前 handoff 输出路径

    # 标准 Markdown 渲染后统一以 UTF-8 写入。
    path_target.write_text(handoff_markdown(dict_data, int_count), encoding="utf-8")

    # 对话证据存在时生成与本次序号绑定的可选快照。
    str_snapshot = maybe_write_conversation_snapshot(project, dict_data, int_count)  # 可选对话快照路径

    # 只有 handoff 正文成功写入后才推进持久计数。
    dict_state["handoff_count"] = int_count  # 最新 handoff 序号

    # 保存状态使下一次 handoff 延续当前计数。
    save_state(project, dict_state)

    # handoff 代表会话完成，因此需要移除活动 session 标记。
    path_active_session = active_session_file(project)  # 活动 session 状态文件

    # 未启动 session 的兼容调用不应因缺失文件失败。
    if path_active_session.exists():

        # 删除标记后 resume-check 会正确报告 clean。
        path_active_session.unlink()

    # 基础结果在可选记忆和快照字段加入前保持稳定合同。
    dict_result = {  # handoff 命令结果
        "project": str(project),  # handoff 写入项目
        "written": str(path_target),  # 当前 handoff 文件
        "archived": str_archived,  # 可选历史归档
        "handoff_count": int_count,  # 本次递增序号
    }

    # 记忆子系统按项目画像决定是否真正写入 handoff 摘要。
    dict_memory_result = write_handoff_memory(project, dict_data, int_count, path_target)  # 可选记忆写入结果

    # None 表示项目未启用记忆，不在结果中伪造 memory 区块。
    if dict_memory_result is not None:

        # 已运行的记忆写入结果完整暴露给调用方审计。
        dict_result["memory"] = dict_memory_result  # 记忆写入证据

        # 记忆失败不回滚已写 handoff，但必须进入顶层错误清单。
        if dict_memory_result.get("errors"):

            # 前缀标识错误来自记忆后处理而非 handoff 文件写入。
            dict_result["errors"] = [f"memory: {item}" for item in dict_memory_result["errors"]]  # 记忆错误

    # 仅在实际生成快照时增加可选结果字段。
    if str_snapshot:

        # 相对路径将 handoff 结果与对话证据建立关联。
        dict_result["conversation_snapshot"] = str_snapshot  # 对话快照路径

    # 调用方据此确认写入、归档及所有可选后处理证据。
    return dict_result

# 启动受管会话并记录其 handoff 基线。
def write_active_session(project: Path, input_path: str | None) -> dict[str, Any]:
    """写入活动 session 状态，供恢复检查识别中断和 handoff 漂移。

    参数：project 为项目根目录。
    参数：input_path 为可选 session JSON 输入路径。
    返回：活动 session、清理结果及可选记忆读取建议。
    """

    # 已治理仓库启动会话时不刷新目录基线或文档治理时间戳。
    dict_scaffold_result = scaffold(project, refresh_existing_state=False)  # 非刷新脚手架结果

    # 脚手架错误意味着 session 基线不可信，必须阻断启动。
    if dict_scaffold_result.get("errors"):

        # 阻断结果保留命名审计，支持调用方直接定位 handoff 冲突。
        return {
            "project": str(project),  # session 启动项目
            "errors": dict_scaffold_result["errors"],  # 启动阻断错误
            "blocking": True,  # 明确禁止继续工作
            "handoff_naming": dict_scaffold_result.get("handoff_naming", {}),  # 启动阻断命名证据
        }

    # 输入对象提供任务、当前步骤和可选会话摘要。
    dict_data = read_input(input_path)  # session 启动输入

    # 启动新会话前移除已退休 evolution 状态，避免恢复结果误报。
    dict_cleanup = cleanup_legacy_evolution_artifacts(project)  # session 启动清理证据

    # 当前 handoff 的哈希和时间构成后续漂移检测基线。
    path_handoff = handoff_paths(project)["current"]  # session 基线文件

    # 活动状态同时保存用户任务语义和 handoff 文件事实。
    dict_active = {  # 活动 session 状态
        "task": dict_data.get("task", "not recorded"),  # 当前任务
        "current_step": dict_data.get("current_step", "not recorded"),  # 当前执行步骤
        "conversation_summary": dict_data.get("conversation_summary", ""),  # 会话摘要
        "started_at": datetime.now().isoformat(timespec="seconds"),  # 会话启动时间
        "handoff_path": "docs/handoff/HANDOFF.md",  # 基线 handoff 相对路径
        "handoff_hash": file_hash(path_handoff),  # 基线内容哈希
        "handoff_mtime": path_handoff.stat().st_mtime if path_handoff.exists() else 0,  # 基线修改时间
    }

    # 活动状态属于项目本地控制资产，固定落在 .agents。
    path_agents_dir = project / ".agents"  # 项目控制目录

    # 脚手架通常已创建父目录，exist_ok 保持独立调用兼容性。
    path_agents_dir.mkdir(exist_ok=True)

    # 稳定排序的 JSON 便于 resume-check 和代码审查读取差异。
    path_active_session = active_session_file(project)  # 活动 session 文件

    # 状态正文统一以 UTF-8 和缩进 JSON 写入。
    path_active_session.write_text(
        json.dumps(dict_active, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # 基础结果证明写入位置、活动状态和启动前清理事实。
    dict_result = {  # start-session 返回载荷
        "project": str(project),  # session 状态所属项目
        "written": str(path_active_session),  # session 状态写入位置
        "active_session": dict_active,  # 本次写入状态
        "cleanup": dict_cleanup,  # session 前清理证据
    }

    # 启用记忆时建议按当前任务查询历史上下文。
    dict_recommendation = memory_read_recommendation(  # 启动后的记忆查询建议
        project,  # 查询当前项目记忆
        str(dict_active.get("task", "current task")),  # session 任务检索词
    )  # 可选记忆读取建议

    # 未启用记忆时不增加空建议字段。
    if dict_recommendation:

        # 建议包含可直接执行的 memory-read 命令和治理策略。
        dict_result["memory_read_recommendation"] = dict_recommendation  # 记忆读取建议

    # 调用方可据此确认会话已启动并恢复相关历史上下文。
    return dict_result

# 读取活动 session，并将无效顶层内容降级为空状态。
def read_active_session(project: Path) -> dict[str, Any]:
    """读取项目活动 session 的 JSON 对象。

    参数：project 为项目根目录。
    返回：有效 session 映射；文件缺失或顶层非对象时返回空映射。
    """

    # 共享路径函数保证读取位置与 start-session 写入位置一致。
    value_active = read_json(active_session_file(project))  # 活动 session 原始 JSON

    # 仅对象符合 session 字段合同，其他 JSON 类型视为无活动状态。
    return value_active if isinstance(value_active, dict) else {}

# 判断当前仓库是否存在需恢复的中断会话或命名阻断。
def resume_check(project: Path, conversation_log: str | None = None) -> dict[str, Any]:
    """结合 handoff 基线、活动状态和可选日志检查恢复状态。

    参数：project 为项目根目录。
    参数：conversation_log 为可选对话日志路径。
    返回：状态、阻断标志、中断原因和记忆读取建议。
    """

    # handoff 命名冲突优先级最高，避免在错误文件上推断会话状态。
    dict_naming = audit_handoff_naming(project)  # resume 入口命名审计

    # 多个当前 handoff 或非法历史名称会直接阻断恢复。
    if dict_naming["blocking"]:

        # 阻断结果不混淆为 interrupted，要求先修复命名现场。
        dict_result = {  # 命名阻断检查结果
            "project": str(project),  # 命名阻断项目
            "status": "blocked",  # 恢复状态
            "interrupted": False,  # 尚未进入中断判断
            "blocking": True,  # 禁止继续工作
            "reasons": dict_naming["errors"],  # 命名错误原因
            "handoff_naming": dict_naming,  # 完整命名审计
        }

        # 即使命名阻断，历史记忆仍可帮助理解当前恢复任务。
        dict_recommendation = memory_read_recommendation(project, "resume current task")  # 阻断场景记忆建议

        # 未启用记忆时保持结果不含空建议字段。
        if dict_recommendation:

            # 建议提供受管 memory-read 命令而不绕过命名修复。
            dict_result["memory_read_recommendation"] = dict_recommendation  # 阻断场景历史查询

        # 命名阻断确定后无需读取活动 session。
        return dict_result

    # 活动 session 是判断上一轮工作是否结束的持久证据。
    dict_active = read_active_session(project)  # 当前活动 session

    # 没有活动状态表示上一次会话已正常 handoff 或从未启动。
    if not dict_active:

        # clean 结果仍说明没有活动 session，避免“无原因”的模糊结论。
        dict_clean_result = {  # 未发现活动会话时的 clean 状态载荷
            "project": str(project),  # 未发现活动会话的项目根
            "status": "clean",  # 可开始新会话的状态结论
            "interrupted": False,  # 不需要恢复上一轮会话
            "blocking": False,  # 当前治理状态不阻断新工作
            "reasons": ["no active session found"],  # 未发现活动状态文件的原因
        }

        # 新任务仍应读取相关长期记忆，而非只在中断时读取。
        dict_recommendation = memory_read_recommendation(project, "current task")  # 新任务记忆建议

        # 记忆未启用时省略建议字段。
        if dict_recommendation:

            # 建议保留项目记忆政策和可执行查询命令。
            dict_clean_result["memory_read_recommendation"] = dict_recommendation  # 新任务历史查询

        # 无活动状态时无需继续比较 handoff 哈希。
        return dict_clean_result

    # 当前 handoff 与 session 启动时保存的基线进行内容比较。
    path_handoff = handoff_paths(project)["current"]  # resume 比较文件

    # 空哈希同时表达文件缺失，供后续分支明确报告。
    str_current_hash = file_hash(path_handoff)  # 当前 handoff 内容哈希

    # 原因列表可以同时记录 handoff 状态和日志中断标记。
    list_reasons: list[str] = []  # 恢复状态判断依据

    # 初始按未中断处理，任何可靠中断证据都将其置为 True。
    bool_interrupted = False  # 是否需要恢复上一会话

    # 活动 session 存在且 handoff 未更新，说明没有完成正常交接。
    if str_current_hash and str_current_hash == dict_active.get("handoff_hash"):

        # 未变化的基线是中断会话的主要判定证据。
        bool_interrupted = True  # handoff 未变化导致中断

        # 原因文本直接说明比较关系。
        list_reasons.append("HANDOFF.md has not changed since active session started")

    # 活动 session 存在但当前 handoff 丢失，同样需要恢复处理。
    elif not str_current_hash:

        # 文件缺失使正常交接无法得到证明。
        bool_interrupted = True  # handoff 缺失导致中断

        # 缺失原因供 resume-repair 决定恢复输入。
        list_reasons.append("HANDOFF.md is missing while an active session exists")

    # handoff 已变化时保留 clean 结论及变化原因。
    else:

        # handoff 已变化表示另一路径完成了交接，当前状态不视为中断。
        list_reasons.append("HANDOFF.md changed after active session started")

    # 可选日志提供强制停止、断网等额外中断证据。
    if conversation_log:

        # 绝对路径避免恢复命令在不同工作目录下读取错误日志。
        path_log = Path(conversation_log).resolve()  # 对话日志绝对路径

        # 缺失日志不覆盖 handoff 基线作出的结论。
        if path_log.exists():

            # 小写文本支持英文标记的不区分大小写匹配。
            str_log_text = path_log.read_text(encoding="utf-8", errors="ignore").lower()  # 对话日志正文

            # 英文和中文标记覆盖常见异常终止描述。
            if any(
                str_marker in str_log_text
                for str_marker in ["stop", "stopped", "interrupted", "断网", "强制停止", "中断"]
            ):

                # 日志证据可以将原本 clean 的 handoff 比较结果提升为中断。
                bool_interrupted = True  # 日志标记证明中断

                # 独立原因保留日志证据来源。
                list_reasons.append("conversation log contains interruption markers")

    # 最终结果保留活动状态和当前哈希，支持后续恢复审计。
    dict_result = {  # 活动会话恢复检查结果
        "project": str(project),  # 活动会话所属项目
        "status": "interrupted" if bool_interrupted else "clean",  # 活动会话结论
        "interrupted": bool_interrupted,  # 是否需要恢复
        "blocking": False,  # 命名已通过，不阻断修复命令
        "active_session": dict_active,  # 活动 session 证据
        "current_handoff_hash": str_current_hash,  # 当前 handoff 哈希
        "reasons": list_reasons,  # 状态判断依据
    }

    # 记忆查询使用活动 session 中的真实任务文本提高召回相关性。
    dict_recommendation = memory_read_recommendation(  # 活动任务历史查询建议
        project,  # 查询活动任务项目记忆
        str(dict_active.get("task", "resume current task")),  # 恢复任务检索词
    )  # 当前任务记忆建议

    # 未启用记忆时不添加空区块。
    if dict_recommendation:

        # 建议帮助恢复流程在实现前读取历史摘要。
        dict_result["memory_read_recommendation"] = dict_recommendation  # 恢复任务历史查询

    # 调用方依据 blocking 和 interrupted 选择新工作或恢复流程。
    return dict_result

# 在确认中断后通过受管 handoff 结束并记录恢复会话。
def resume_repair(project: Path, input_path: str | None) -> dict[str, Any]:
    """根据恢复检查结果写入恢复 handoff。

    参数：project 为项目根目录。
    参数：input_path 为恢复 handoff 的可选 JSON 输入路径。
    返回：跳过、阻断或已完成恢复写入的结果。
    """

    # 修复前重新检查现场，避免使用调用方可能过期的状态结论。
    dict_check = resume_check(project)  # 最新恢复检查结果

    # 命名阻断必须先由专用修复命令处理，不能写入新 handoff。
    if dict_check.get("blocking"):

        # 阻断结果完整携带原检查证据供用户决策。
        return {
            "project": str(project),  # 恢复阻断项目
            "skipped": True,  # 未执行恢复写入
            "interrupted": False,  # 中断判断被命名问题阻断
            "blocking": True,  # 禁止继续恢复
            "errors": dict_check["reasons"],  # 阻断原因
            "resume_check": dict_check,  # 原始检查证据
        }

    # clean 会话无需生成额外 handoff 或修改状态。
    if not dict_check["interrupted"]:

        # 跳过结果说明当前证据为何不需要恢复。
        return {
            "project": str(project),  # 无需恢复项目
            "skipped": True,  # clean 状态跳过写入
            "interrupted": False,  # 当前会话状态干净
            "reasons": dict_check["reasons"],  # 跳过依据
        }

    # 中断会话通过标准 handoff 路径归档旧记录并清除活动状态。
    dict_result = write_handoff(project, input_path)  # 恢复 handoff 写入结果

    # recovery 标志区分普通完成 handoff 与中断恢复写入。
    dict_result["recovery"] = True  # 本次写入属于恢复

    # 保留进入修复前已经确认的中断事实。
    dict_result["interrupted"] = True  # 原会话确认为中断

    # 嵌入检查快照使恢复结果具备可审计因果链。
    dict_result["resume_check"] = dict_check  # 恢复前检查证据

    # 调用方可同时验证恢复 handoff 和触发恢复的原始原因。
    return dict_result

# 预览或执行当前及历史 handoff 的规范命名修复。
def repair_handoff_names(project: Path, write: bool = False) -> dict[str, Any]:
    """修复可安全推断的 handoff 文件名并拒绝歧义现场。

    参数：project 为项目根目录。
    参数：write 控制仅预览或实际执行重命名。
    返回：重命名计划、跳过项、错误和修复后命名审计。
    """

    # 共享路径合同统一定位当前目录、历史目录和正式文件。
    dict_paths = handoff_paths(project)  # 命名修复路径合同

    # 根目录只允许当前文件和历史子目录两个受管入口。
    path_handoff_root = dict_paths["root"]  # 命名扫描根目录

    # 历史目录中的 Markdown 文件必须采用带时间戳的正式名称。
    path_history_dir = dict_paths["history"]  # 历史名称扫描目录

    # 当前文件始终规范为固定的 HANDOFF.md 名称。
    path_current = dict_paths["current"]  # 正式当前 handoff

    # dry-run 和 write 模式共享同一重命名结果合同。
    list_renamed: list[dict[str, str]] = []  # 可执行或已执行重命名

    # 已规范或没有候选的项目进入跳过清单。
    list_skipped: list[str] = []  # 无需修改的路径或原因

    # 自动修复不猜测歧义来源，所有不安全现场进入错误清单。
    list_errors: list[str] = []  # 阻止自动重命名的问题

    # 空项目也允许预览修复，因此先补齐 handoff 根目录。
    path_handoff_root.mkdir(parents=True, exist_ok=True)

    # 历史目录必须存在，后续才能稳定枚举候选文件。
    path_history_dir.mkdir(parents=True, exist_ok=True)

    # 根目录中的其他 Markdown 文件可能是误命名的当前 handoff。
    list_current_candidates = [  # 当前 handoff 重命名候选
        path_entry  # 候选 Markdown 文件
        for path_entry in sorted(path_handoff_root.iterdir())  # 稳定枚举根目录
        if path_entry.is_file()  # 仅普通文件可成为候选
        and path_entry.suffix.lower() == ".md"  # 限定 Markdown 后缀
        and path_entry.name != HANDOFF_CURRENT_FILENAME  # 排除正式当前文件
    ] if path_handoff_root.is_dir() else []  # 非目录时使用空非受管条目列表

    # 非受管且非 Markdown 的根目录条目无法安全解释为 handoff。
    list_extra_current = [  # 根目录中的非受管条目
        path_entry.relative_to(project).as_posix()  # 项目相对路径
        for path_entry in sorted(path_handoff_root.iterdir())  # 枚举未知根条目
        if path_entry.name not in {HANDOFF_CURRENT_FILENAME, HANDOFF_HISTORY_DIRNAME}  # 排除受管名称
        and not (path_entry.is_file() and path_entry.suffix.lower() == ".md")  # 排除可识别候选
    ] if path_handoff_root.is_dir() else []  # 非目录时没有可报告的未知根条目

    # 根目录出现未知条目时拒绝自动修复，防止误移动用户资产。
    if list_extra_current:

        # 每个未知条目单独报告，便于用户逐项确认。
        list_errors.extend(
            f"cannot repair handoff naming automatically because docs/handoff contains non-governed entries: {item}"
            for item in list_extra_current
        )

    # 正式当前文件存在时，其他 Markdown 候选构成多当前文件冲突。
    if path_current.exists():

        # 任一额外候选都无法自动判断应该归档还是删除。
        if list_current_candidates:

            # 错误明确指出正式文件与额外 Markdown 并存。
            list_errors.append(
                "cannot repair handoff naming automatically because docs/handoff contains "
                "HANDOFF.md plus additional markdown candidates"
            )

    # 正式文件缺失且只有一个 Markdown 候选时可以确定迁移目标。
    elif len(list_current_candidates) == 1:

        # 单一候选是唯一可安全推断的当前 handoff 来源。
        path_source = list_current_candidates[0]  # 当前 handoff 来源候选

        # dry-run 只记录计划，write 模式才修改文件系统。
        if write:

            # 同目录 rename 将候选转换为正式当前文件。
            path_source.rename(path_current)

        # 结果无论预览或写入都展示相同的来源和目标。
        list_renamed.append(
            {
                "from": path_source.relative_to(project).as_posix(),  # 原候选路径
                "to": path_current.relative_to(project).as_posix(),  # 正式当前路径
            }
        )

    # 多个 Markdown 候选无法自动选择哪一个是当前 handoff。
    elif len(list_current_candidates) > 1:

        # 要求用户先消除候选歧义再重跑修复。
        list_errors.append(
            "cannot repair handoff naming automatically because docs/handoff contains "
            "multiple markdown candidates"
        )

    # 没有正式文件和候选时记录可解释的跳过原因。
    else:

        # 没有正式文件也没有候选时无需执行当前文件重命名。
        list_skipped.append("no current handoff rename candidate found")

    # 历史目录中的每个条目独立验证并按生成时间规范命名。
    for path_entry in sorted(path_history_dir.iterdir()) if path_history_dir.is_dir() else []:

        # 相对路径用于所有错误、跳过和重命名结果。
        str_relative_path = path_entry.relative_to(project).as_posix()  # 当前历史条目路径

        # 历史目录中的子目录或特殊对象不能自动重命名。
        if not path_entry.is_file():

            # 非文件错误保留具体路径以支持人工处理。
            list_errors.append(
                "cannot repair history handoff naming automatically because a non-file "
                f"entry exists: {str_relative_path}"
            )

            # 当前条目不可读取，直接检查下一个历史条目。
            continue

        # 已符合正式历史文件名的条目保持不变。
        if HANDOFF_HISTORY_RE.fullmatch(path_entry.name):

            # 合规文件无需加入 skipped，审计器会统一证明其状态。
            continue

        # 非 Markdown 文件不属于可识别的历史 handoff。
        if path_entry.suffix.lower() != ".md":

            # 文件类型错误不能通过简单改名安全修复。
            list_errors.append(
                "cannot repair history handoff naming automatically because a non-markdown "
                f"file exists: {str_relative_path}"
            )

            # 跳过正文解析，继续检查其他历史条目。
            continue

        # Markdown 正文用于确认文件确实具备 handoff 章节合同。
        str_text = path_entry.read_text(encoding="utf-8", errors="ignore")  # 历史文件正文

        # 普通 Markdown 文档不能仅凭所在目录被当作 handoff 改名。
        if not looks_like_handoff_markdown(str_text):

            # 内容不匹配时报告文件路径并保留原文件。
            list_errors.append(
                "cannot repair history handoff naming automatically because file does not "
                f"look like a handoff: {str_relative_path}"
            )

            # 不可信正文不参与时间提取或目标路径生成。
            continue

        # 优先使用文档自身记录的生成时间，保持历史语义准确。
        datetime_generated_at = parse_handoff_generated_at(str_text)  # 可选文档生成时间

        # 旧文档缺少生成时间时，以文件修改时间作为可审计退化依据。
        datetime_moment = datetime_generated_at or datetime.fromtimestamp(path_entry.stat().st_mtime)  # 命名时间依据

        # 唯一路径生成器避免同一秒历史文件互相覆盖。
        path_target = unique_handoff_history_path(path_history_dir, datetime_moment)  # 规范历史目标

        # 路径生成结果与当前文件相同表示无需修改。
        if path_target == path_entry:

            # 显式记录异常但已规范的历史候选。
            list_skipped.append(str_relative_path)

            # 当前条目已满足目标命名，继续检查其他文件。
            continue

        # 实际重命名只在调用方明确请求 write 时发生。
        if write:

            # 同目录 rename 保留文件内容和时间事实。
            path_entry.rename(path_target)

        # dry-run 与 write 结果使用一致的重命名映射。
        list_renamed.append(
            {
                "from": str_relative_path,  # 原历史路径
                "to": path_target.relative_to(project).as_posix(),  # 规范历史路径
            }
        )

    # 写入模式审计修复后现场，dry-run 审计仍反映当前未修改现场。
    dict_naming = audit_handoff_naming(project)  # 最终 handoff 命名审计

    # blocking 合并修复过程错误和最终审计结论。
    return {
        "project": str(project),  # 命名修复项目
        "write_requested": write,  # 是否实际修改文件
        "renamed": list_renamed,  # 重命名计划或结果
        "skipped": list_skipped,  # 无需修改项目
        "errors": list_errors,  # 自动修复拒绝原因
        "blocking": bool(list_errors) or dict_naming["blocking"],  # 最终阻断状态
        "handoff_naming": dict_naming,  # 修复后审计证据
    }

# 写入当前开发阶段记录，并归档已有的非占位内容。
def write_development(project: Path, stage: str, input_path: str | None) -> dict[str, Any]:
    """渲染 DEVELOPMENT.md 并保留上一份真实开发记录。

    参数：project 为项目根目录。
    参数：stage 为当前开发阶段名称。
    参数：input_path 为可选开发记录 JSON 输入路径。
    返回：当前写入路径和可选归档路径。
    """

    # 写入前确保 development 目录和默认治理资产存在。
    scaffold(project)

    # 输入读取器保证开发字段来自 JSON 对象。
    dict_data = read_input(input_path)  # 开发记录输入

    # 当前开发记录固定落在 development 正式路径。
    path_target = project / "docs" / "development" / "DEVELOPMENT.md"  # development 正式文件

    # 空字符串表示本次只覆盖默认占位记录或首次写入。
    str_archived = ""  # 可选历史开发记录路径

    # 已有文件需要先判断是默认模板还是真实开发记录。
    if path_target.exists():

        # 版本和状态占位符共同标识可直接覆盖的默认模板。
        str_existing = path_target.read_text(encoding="utf-8", errors="ignore")  # 已有开发记录正文

        # 任一占位符已被真实内容替换时，旧记录必须进入历史目录。
        if "- Version: not recorded" not in str_existing or "- Status: not recorded" not in str_existing:

            # 时间戳子目录让每次开发阶段写入保留独立历史。
            path_history_dir = (
                project / "docs" / "development" / "history_development" / stamp()  # 时间戳历史位置
            )  # 本次开发记录归档目录

            # 递归创建兼容尚无历史目录的旧项目。
            path_history_dir.mkdir(parents=True, exist_ok=True)

            # 历史文件保持正式名称，归档时间由父目录表达。
            path_archived = path_history_dir / "DEVELOPMENT.md"  # 历史开发记录

            # 移动旧记录后当前位置可安全写入新阶段。
            shutil.move(str(path_target), str(path_archived))

            # 返回结果使用跨平台项目相对路径。
            str_archived = path_archived.relative_to(project).as_posix()  # 已归档记录路径

    # 固定章节顺序保证 handoff 和开发审计工具稳定读取。
    path_target.write_text(
        "\n".join([
            f"# Development Stage: {stage}",  # 阶段标题
            "",  # 开发标题后空行
            f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",  # 开发记录时间
            f"- Version: {dict_data.get('version', 'not recorded')}",  # 阶段版本
            f"- Status: {dict_data.get('current_status', 'not recorded')}",  # 当前状态
            "",  # 元数据与目标分隔
            "## Development Goal",  # 开发目标章节
            list_lines(dict_data.get("goal")),  # 开发目标条目
            "",  # 目标与计划分隔
            "## Full Development Plan",  # 完整计划章节
            list_lines(dict_data.get("full_plan")),  # 完整计划条目
            "",  # 计划与进度分隔
            "## Current Progress",  # 当前进度章节
            list_lines(dict_data.get("current_status")),  # 当前进度条目
            "",  # 进度与完成范围分隔
            "## Completed Scope",  # 已完成范围章节
            list_lines(dict_data.get("completed_scope")),  # 已完成范围条目
            "",  # 完成与剩余范围分隔
            "## Remaining Scope",  # 剩余范围章节
            list_lines(dict_data.get("remaining_scope")),  # 剩余范围条目
            "",  # 剩余范围与风险分隔
            "## Key Problems And Risks",  # 问题风险章节
            list_lines(dict_data.get("remaining_risks") or dict_data.get("problems")),  # 风险条目
            "",  # 风险与策略分隔
            "## Resolution Strategy And Next Steps",  # 后续策略章节
            list_lines(dict_data.get("next_steps") or dict_data.get("next")),  # 策略条目
            "",  # 策略与结果分隔
            "## Development Result",  # 开发结果章节
            list_lines(dict_data.get("results")),  # 开发结果条目
            "",  # 结果与验证分隔
            "## Verification",  # 验证章节
            list_lines(dict_data.get("verification")),  # 开发验证条目
            "",  # 验证与产物分隔
            "## Artifacts And Impact",  # 产物影响章节
            list_lines(dict_data.get("artifacts")),  # 产物影响条目
            "",  # development 末尾换行
        ]),
        encoding="utf-8",
    )

    # 返回路径合同区分当前文件和可选归档文件。
    return {
        "project": str(project),  # 开发记录所属项目
        "written": str(path_target),  # 新阶段记录文件
        "archived": str_archived,  # development 历史文件
    }

# 将结构化 Git 变更数据渲染为当前 CHANGELOG.md。
def changelog_markdown(data: dict[str, Any]) -> str:
    """渲染固定章节的 Git 变更日志。

    参数：data 为版本、摘要、变更和验证字段。
    返回：标准 CHANGELOG.md 文本。
    """

    # 固定字段和章节保证发布流程可以稳定审计版本证据。
    return "\n".join([
        "# Change Log",  # changelog 标题
        "",  # changelog 标题后空行
        f"- Version: {data.get('version', 'not recorded')}",  # 发布版本
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",  # 变更日志时间
        f"- Summary: {data.get('summary', 'not recorded')}",  # 变更摘要
        "",  # 元数据与变更分隔
        "## Changes",  # 变更章节
        list_lines(data.get("changes")),  # 变更条目
        "",  # 变更与验证分隔
        "## Verification",  # 变更日志验证标题
        list_lines(data.get("verification")),  # 验证条目
        "",  # 变更日志终止空行
    ])

# 在写入新 CHANGELOG.md 前归档已有的真实变更记录。
def rotate_git_changelog(project: Path) -> str | None:
    """按需将当前变更日志移动到时间戳历史目录。

    参数：project 为项目根目录。
    返回：归档文件的项目相对路径；无需归档时返回 None。
    """

    # 共享路径函数定位当前变更日志正式文件。
    path_current = git_changelog_file(project)  # 待归档的当前变更日志

    # 首次写入没有可归档的旧文件。
    if not path_current.exists():

        # None 明确表示未生成历史归档。
        return None

    # 版本与摘要占位符共同标识默认模板。
    str_current = path_current.read_text(encoding="utf-8", errors="ignore")  # 当前变更日志正文

    # 默认模板可直接覆盖，无需制造无价值历史。
    if "- Version: not recorded" in str_current and "- Summary: not recorded" in str_current:

        # 保留模板原位供写入函数覆盖。
        return None

    # 每次归档使用独立时间戳目录，避免版本日志相互覆盖。
    path_history_dir = git_history_root(project) / stamp()  # 本次 Git 历史目录

    # 递归创建支持尚未初始化历史目录的旧项目。
    path_history_dir.mkdir(parents=True, exist_ok=True)

    # 历史文件保留正式名称，时间信息由父目录表达。
    path_target = path_history_dir / "CHANGELOG.md"  # 归档变更日志

    # 移动当前文件为新日志写入腾出正式路径。
    shutil.move(str(path_current), str(path_target))

    # 项目相对路径适合写入命令 JSON 结果。
    return path_target.relative_to(project).as_posix()

# 写入当前 Git 变更日志并同步最近版本状态。
def write_git_changelog(project: Path, input_path: str | None) -> dict[str, Any]:
    """归档旧日志、写入新日志并更新 docs 治理状态。

    参数：project 为项目根目录。
    参数：input_path 为可选 changelog JSON 输入路径。
    返回：当前写入、归档和版本信息。
    """

    # 写入前确保 Git 文档和历史目录治理结构存在。
    scaffold(project)

    # 输入对象提供版本、摘要、变更和验证字段。
    dict_data = read_input(input_path)  # 变更日志输入

    # 当前日志正式路径由共享合同定位。
    path_target = git_changelog_file(project)  # changelog 写入目标

    # 真实旧日志先进入历史目录，默认模板则直接覆盖。
    str_archived = rotate_git_changelog(project)  # 可选归档路径

    # 渲染后的标准 Markdown 统一使用 UTF-8 写入。
    path_target.write_text(changelog_markdown(dict_data), encoding="utf-8")

    # 状态记录最近一次 changelog 写入时间和版本。
    dict_state = load_state(project)  # changelog 持久状态

    # 秒级时间避免无意义的微秒差异进入状态文件。
    dict_state["last_git_changelog_at"] = datetime.now().isoformat(timespec="seconds")  # 最近日志写入时间

    # 版本文本去除输入首尾空白后再持久化。
    str_version = str(dict_data.get("version", "")).strip()  # 当前 changelog 版本

    # 状态版本供发布和文档验证流程读取。
    dict_state["last_git_changelog_version"] = str_version  # 最近日志版本

    # 同步写入时间和版本，避免半更新状态。
    save_state(project, dict_state)

    # 返回合同使用项目相对路径，便于跨平台审计。
    return {
        "project": str(project),  # 变更日志所属项目
        "written": path_target.relative_to(project).as_posix(),  # 当前日志路径
        "archived": str_archived or "",  # 可选历史日志路径
        "version": str_version,  # 本次写入版本
    }
