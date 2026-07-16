"""维护目录治理快照、远程部署策略与结构验证状态。"""

# 延迟解析类型注解，避免运行期求值仅供静态检查使用的联合类型。
from __future__ import annotations

# 导入区分为标准库和项目公共治理依赖。
# 标准库负责时间戳、路径匹配、JSON 读取和路径建模。
from datetime import datetime
from fnmatch import fnmatch
import json
from pathlib import Path
import re
from typing import Any

# 公共模块提供项目忽略规则、JSON 读取和可复制命令渲染。
from agents_common import SKIP_DIRS, read_json, script_command
from workspace_settings_policy import (
    SETTINGS_FOLDER,
    REMOTE_DEFAULT_SETTINGS,
    workspace_settings_contract,
    workspace_settings_location_reason,
)

# 目录治理文档统一位于项目的 docs/dir_manager 子树。
DIR_MANAGER_DIR = Path("docs") / "dir_manager"  # 目录治理文档根路径。

# 当前结构快照用于验证工作区是否出现未批准漂移。
CURRENT_STRUCTURE = DIR_MANAGER_DIR / "current_structure.json"  # 当前目录结构快照路径。

# 计划结构快照保存初始化或审查后批准的布局。
PLANNED_STRUCTURE = DIR_MANAGER_DIR / "planned_structure.json"  # 已批准目录结构路径。

# Markdown 文档向用户解释目录治理合同和可执行命令。
DIR_MANAGER_MD = DIR_MANAGER_DIR / "DIR_MANAGER.md"  # 目录治理说明文档路径。

# 每次目录变更审查的结构化证据独立归档。
CHANGE_REVIEWS = DIR_MANAGER_DIR / "change_reviews"  # 目录变更审查记录目录。

# 旧版结构快照进入历史目录，避免覆盖审计证据。
HISTORY_DIR_MANAGER = DIR_MANAGER_DIR / "history_dir_manager"  # 历史目录快照归档位置。

# 关键前缀发生变化时必须经过显式目录审查。
CRITICAL_PREFIXES = {
    ".agents",  # 代理控制档案属于关键项目元数据。
    ".settings",  # 工作区连接与运行配置需要位置审查。
    "agents",  # 代理角色定义目录属于执行控制面。
    "assets",  # 技能资源移动会影响打包内容。
    "dist",  # 发布包目录必须保持版本化布局。
    "docs",  # 文档根承载治理与交接证据。
    "docs/dir_manager",  # 目录治理自身不可未经审查迁移。
    "docs/handoff",  # 交接历史路径影响会话恢复。
    "docs/git_manager",  # Git 治理文档是发布操作依据。
    "references",  # 技能参考资料参与交付打包。
    "scripts",  # 可执行脚本位置影响命令合同。
    "src",  # 通用源码根移动会改变项目入口。
    "tests",  # 测试目录位置影响验证发现。
}

# 治理前缀属于项目控制面，远程部署默认禁止覆盖。
GOVERNANCE_PREFIXES = {
    ".agents",  # 代理控制目录禁止被普通部署覆盖。
    "docs/dir_manager",  # 目录计划和审查证据受保护。
    "docs/handoff",  # 活跃交接与历史记录受保护。
    "docs/git_manager",  # 分支和发布治理说明受保护。
}

# 接管既有项目时保留常见根级代理说明和工具配置。
TAKEOVER_PRESERVE_ROOT_FILES = {
    "AGENTS.md",  # 项目根代理规则在接管时必须保留。
    "CLAUDE.md",  # Claude 项目代理说明保持原位置。
    "GEMINI.md",  # Gemini 项目代理说明避免接管丢失。
    ".gitignore",  # 既有忽略规则不能被初始化覆盖。
    ".gitattributes",  # 行尾与合并属性属于仓库合同。
    ".editorconfig",  # 编辑器格式配置在接管时保留。
}

# 默认允许的根文件沿用接管保留集合并稳定排序。
ALLOWED_ROOT_FILES = sorted(TAKEOVER_PRESERVE_ROOT_FILES)  # 根目录固定白名单。

# 临时回答、会话和审查输入允许留在根目录但不进入长期布局。
EPHEMERAL_ROOT_INPUT_FILE_RE = re.compile(  # 根级临时治理输入匹配器。
    (  # 合并允许前缀与可选场景后缀。
        r"^(?:answers|first-answers|recovery|session|stage|handoff|change|allowed-change|"  # 目录输入前缀集合
        r"blocked-change|blocked-remote-change|blocked-remote-source-change)"  # 阻断目录输入前缀
        r"(?:-[a-z0-9._-]+)?\.json$"  # 目录输入可选后缀
    ),  # 目录治理临时输入文件模式
    flags=re.IGNORECASE,  # 根级治理输入文件名不区分大小写。
)  # 根目录临时治理输入文件名模式。

# 历史兼容模式覆盖仍由旧命令生成的根级 JSON 输入。
ALLOWED_ROOT_FILE_PATTERNS = (
    "answers.json",  # 兼容早期单次访谈回答文件。
    "*-answers.json",  # 允许带阶段前缀的回答文件。
    "change.json",  # 目录审查默认输入文件。
    "*-change.json",  # 允许具名目录变更载荷。
    "session.json",  # 会话启动兼容输入。
    "recovery.json",  # 中断恢复兼容输入。
    "handoff.json",  # 交接生成兼容输入。
    "stage.json",  # Git 阶段治理兼容输入。
    "changelog.json",  # 发布变更日志兼容输入。
)  # 根目录兼容输入文件模式。

# 测试、报告和运行输出目录可按项目需要出现在根级布局。
ROOT_OPTIONAL_WORK_DIRS = ("tests", "reports", "runs", "smoke")  # 可选根级工作目录名。

# 冒烟测试夹具允许使用带场景后缀的根目录。
ROOT_OPTIONAL_WORK_DIR_PREFIXES = ("smoke-",)  # 可选工作目录名前缀。

# 远程清理计划不得删除工作区、环境或运行证据根路径。
REMOTE_PROTECTED_PATH_CLASSES = [
    "workspace-root",  # 远程工作区根不得成为清理目标。
    "conda-environment-root",  # 环境集合根禁止递归删除。
    "conda-environment",  # 具体隔离环境禁止普通覆盖。
    "active-run-root",  # 活跃运行集合根保存当前任务证据。
    "active-run",  # 当前运行目录在验证前受保护。
    "backup-run-root",  # 历史运行归档根需要长期保留。
    "backup-run",  # 单次备份运行不可被部署清理。
]  # 远程部署受保护路径类别。

# 活跃会话和发布过程文件变化频繁，不纳入结构漂移比较。
STRUCTURE_SKIP_FILE_PATTERNS = (
    ".agents/active-session.json",  # 活跃会话状态由文档治理器单独验证。
    ".agents/session-*.json",  # 具名会话输入随任务变化。
    ".agents/release-*.json",  # 发布过程载荷由发布门禁管理。
)  # 结构扫描忽略的临时文件模式。

# 生成归档目录可读且可排序的时间标识。
def stamp() -> str:
    """生成目录治理归档使用的本地时间戳。

    参数：无。
    返回：格式为 YYYYMMDD-HHMMSS 的时间戳字符串。
    """

    # 秒级精度足以区分串行治理动作，并保持文件名可读。
    return datetime.now().strftime("%Y%m%d-%H%M%S")

# 统一目录治理中所有相对路径的比较形式。
def normalize_rel(raw: str) -> str:
    """把用户路径规范为无首尾斜杠的 POSIX 相对路径。

    参数：raw 为待规范化的路径文本。
    返回：合并重复分隔符后的相对路径字符串。
    """

    # 先统一平台分隔符并移除根边界处的空白与斜杠。
    raw_value = str(raw).replace("\\", "/").strip().strip("/")  # 初步规范化路径。

    # 连续斜杠折叠后可用于稳定的前缀和集合比较。
    return re.sub(r"/+", "/", raw_value)

# 在执行目录操作前拒绝越界或不精确的目标路径。
def invalid_path_reason(raw: str) -> str | None:
    """说明目录变更路径为何不能作为项目内相对路径。

    参数：raw 为用户或审查载荷提供的路径。
    返回：非法原因；路径满足安全边界时返回 None。
    """

    # 保留原始分隔符用于错误消息，同时去掉无意义空白。
    raw_value = str(raw).strip()  # 待验证路径文本。

    # 统一分隔符后再检查绝对路径和父级穿越。
    normalized = raw_value.replace("\\", "/")  # 跨平台路径表示。

    # 空字符串无法指向受管项目成员。
    if not raw_value:

        # 返回稳定错误文本供 CLI 和测试断言复用。
        return "empty path is not allowed"

    # 盘符路径和 POSIX 根路径都会逃逸项目根目录。
    if re.match(r"^[A-Za-z]:[/\\]", raw_value) or normalized.startswith("/"):

        # 在错误中保留输入值，便于用户修正审查载荷。
        return f"path must stay inside the project and cannot be absolute: {raw_value}"

    # 任意父级片段都可能把变更目标导向项目之外。
    if ".." in normalized.split("/"):

        # 明确指出父级穿越风险，而非静默改写用户路径。
        return f"path must not contain parent traversal: {raw_value}"

    # 通配符和 shell 特殊字符会让单一路径审查变成范围操作。
    if any(char in raw_value for char in "*?<>|"):

        # 拒绝模糊目标，要求调用方提交精确相对路径。
        return f"path must not contain wildcard or unsafe shell characters: {raw_value}"

    # 未命中危险模式时允许后续目录治理继续处理。
    return None

# 排除缓存和版本控制等不参与结构治理的目录成员。
def is_skipped(path: Path, root: Path) -> bool:
    """判断项目成员是否位于全局忽略目录之下。

    参数：path 为候选成员，root 为项目根目录。
    返回：任一相对路径分段命中 SKIP_DIRS 时为 True。
    """

    # 相对分段比较可同时覆盖顶层和嵌套的忽略目录。
    parts = path.relative_to(root).parts  # 候选成员的相对路径分段。

    # 集合交集避免为每个忽略目录重复遍历路径。
    return bool(set(parts) & SKIP_DIRS)

# 扫描项目并生成可提交、可比较的当前结构快照。
def scan_structure(project: Path) -> dict[str, Any]:
    """扫描项目中纳入治理的目录和文件。

    参数：project 为项目根目录。
    返回：包含生成时间、目录、文件和忽略目录的结构快照。
    """

    # 目录列表独立保存，便于计划结构按类型比较。
    list_directories: list[str] = []  # 扫描到的受管目录相对路径。

    # 文件列表排除过程态证据，避免每次会话产生结构漂移。
    list_files: list[str] = []  # 扫描到的稳定文件相对路径。

    # 递归结果排序后写入快照，确保跨运行输出稳定。
    for path in sorted(project.rglob("*")):

        # 全局忽略目录及其后代都不属于治理快照。
        if is_skipped(path, project):

            # 跳过缓存、版本控制元数据和其他配置忽略项。
            continue

        # 快照只保存可跨机器复用的项目相对路径。
        rel = path.relative_to(project).as_posix()  # 当前成员的 POSIX 相对路径。

        # 目录成员进入独立集合，供顶层和父子结构验证使用。
        if path.is_dir():

            # 记录目录本身，不重复展开其已由 rglob 返回的后代。
            list_directories.append(rel)

        # 普通文件需要进一步过滤活跃过程态证据。
        elif path.is_file():

            # 会话和发布临时文件由专用治理器验证，不参与布局比较。
            if any(fnmatch(rel, pattern) for pattern in STRUCTURE_SKIP_FILE_PATTERNS):

                # 忽略高频变化文件，避免无意义地刷新计划结构。
                continue

            # 保留稳定文件路径供根文件与工作区设置检查使用。
            list_files.append(rel)

    # 返回不含绝对工作区信息的可提交结构快照。
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": "<PROJECT_ROOT>",
        "directories": list_directories,
        "files": list_files,
        "skip_dirs": sorted(SKIP_DIRS),
    }

# 渲染目录变更审查与强制覆盖的用户操作说明。
def dir_manager_doc(project: Path) -> str:
    """渲染目录治理说明和可复制的审查命令。

    参数：project 为项目根目录。
    返回：DIR_MANAGER.md 的完整 Markdown 文本。
    """

    # 审查命令使用项目实际脚本布局，兼容迁移后的入口路径。
    review_command = script_command(  # 当前布局对应的目录变更预审命令。
        project,  # 当前项目用于解析脚本入口。
        "manage_dirs.py",  # 目录治理命令模块名。
        "review",  # 变更预审子命令。
        "<project>",  # 文档中的项目路径占位符。
        "--input",  # 审查载荷参数名。
        "change.json",  # 默认变更输入文件名。
    )  # 目录变更预审命令。

    # 强制覆盖前必须先归档当前目录治理证据。
    archive_command = script_command(  # 强制覆盖前的治理证据归档命令。
        project,  # 当前项目用于选择实际脚本路径。
        "manage_dirs.py",  # 目录治理 CLI 入口。
        "archive",  # 治理证据归档子命令。
        "<project>",  # 用户替换的项目根占位符。
        "--reason",  # 强制覆盖原因参数。
        "force-confirmed directory override",  # 文档建议的归档原因。
    )  # 目录治理归档命令。

    # 固定章节顺序让 AGENTS 指针和人工审查保持一致。
    return "\n".join(
        [
            "# Directory Manager",
            "",
            (
                "This file is the strict gate for creating, moving, renaming, or deleting "
                "local project folders and remote deployment workspace folders."
            ),
            "",
            "## Required Review",
            "- Read this file before changing folder structure.",
            f"- Run `{review_command}` before directory changes.",
            "- Do not move, rename, or delete governance folders without explicit user force-confirmation.",
            "- If review blocks a change, refuse default execution and explain the risk to the user.",
            (
                "- If the user explicitly force-confirms a blocked change, archive old dir "  # AGENTS 长文本片段
                "manager content under `history_dir_manager/YYYYMMDD-HHMMSS/` before changing "
                "structure."
            ),
            "",
            "## Blocked By Default",
            (
                "- Paths outside the project, absolute paths, parent traversal, wildcards, "
                "or shell-unsafe path characters."
            ),
            "- New top-level folders not listed in `planned_structure.json`.",
            (
                "- Workspace engineering config files such as `project.local.json`, "
                f"`project.remote.json`, or `server_list.local.json` outside `{SETTINGS_FOLDER}/`."
            ),
            (
                f"- Any remote attempt to copy `{SETTINGS_FOLDER}/*.local.json` such as "
                f"`{SETTINGS_FOLDER}/server_list.local.json` into the remote workspace."
            ),
            "- Remote deployment folders not listed in `planned_structure.json` remote_deployment planning.",
            "- Moving or deleting `.agents/`, `docs/dir_manager/`, `docs/handoff/`, or `docs/git_manager/`.",
            (
                "- Moving source, tests, docs, dist, scripts, assets, references, or agents "
                "folders to unplanned locations."
            ),
            "- Mixing generated output, release packages, or temporary references into source folders.",
            "",
            "## User Force Override",
            "- Explain why the request is unreasonable or risky.",
            (
                "- State severe hazards such as broken tests, invalid release packages, "
                "stale AGENTS.md scopes, broken history links, or failed skill installation."
            ),
            "- Ask the user to explicitly confirm forced directory structure modification.",
            f"- Run `{archive_command}` before applying a force-confirmed folder change.",
            "- Record confirmation and risk in the next handoff.",
            "",
        ]
    )

# 读取目录策略推导所依赖的项目控制档案。
def control_profile(project: Path) -> dict[str, Any]:
    """读取项目级代理控制档案。

    参数：project 为项目根目录。
    返回：控制档案映射；缺失或非对象内容返回空映射。
    """

    # 控制档案是目录合同和远程策略的唯一项目级来源。
    dict_data = read_json(project / ".agents" / "agents-control.json")  # 原始控制档案。

    # 非映射 JSON 不能提供具名治理字段，按未配置处理。
    return dict_data if isinstance(dict_data, dict) else {}

# 为验证诊断选择项目相对或明确绝对的路径表示。
def display_rel(path: Path, project: Path) -> str:
    """优先以项目相对路径展示诊断目标。

    参数：path 为诊断路径，project 为期望的项目根目录。
    返回：项目内路径使用相对形式，外部路径使用绝对形式。
    """

    # 项目内路径更便于用户直接定位仓库成员。
    try:

        # POSIX 分隔符保证 JSON 诊断跨平台一致。
        return path.relative_to(project).as_posix()

    # 路径位于项目之外时 relative_to 会失败，此处转为明确绝对位置。
    except Exception:

        # 解析后的绝对路径避免模糊显示为相邻项目成员。
        return path.resolve().as_posix()

# 将多种历史远程工作区声明归一为路径或禁用哨兵。
def remote_structure(project: Path) -> str:
    """读取项目配置的远程工作区根路径。

    参数：project 为项目根目录。
    返回：远程路径文本；未启用远程工作区时返回 not configured。
    """

    # 远程目录设置来自项目控制档案而非本机设置文件。
    dict_profile = control_profile(project)  # 远程隔离环境的控制档案来源。

    # directory_contract 缺失或类型错误时按空合同降级。
    contract = (
        dict_profile.get("directory_contract", {})  # 远程根所在的目录合同分区。
        if isinstance(dict_profile.get("directory_contract"), dict)  # 仅接受映射合同。
        else {}  # 损坏配置按未设置远程根处理。
    )  # 目录合同映射。

    # 去除人工编辑可能引入的首尾空白。
    raw = str(contract.get("remote", "")).strip()  # 原始远程工作区声明。

    # 空声明与未配置状态等价。
    if not raw:

        # 使用统一哨兵值简化后续计划生成。
        return "not configured"

    # 接受控制档案中的两种历史禁用写法。
    if raw.lower() in {"none", "not configured"}:

        # 规范化历史值，避免调用方重复判断。
        return "not configured"

    # 兼容旧版自然语言占位说明。
    if "no remote workspace is configured" in raw.lower():

        # 自然语言禁用声明同样折叠为稳定哨兵。
        return "not configured"

    # 已配置路径保持用户原始表达，供远程命令和文档使用。
    return raw

# 提取远程 Python 隔离环境的目录合同。
def remote_environment_policy(project: Path) -> dict[str, Any]:
    """读取远程隔离环境目录策略。

    参数：project 为项目根目录。
    返回：remote_environment_policy 映射；未配置时返回空映射。
    """

    # 环境策略与远程根路径共享同一目录合同来源。
    dict_profile = control_profile(project)  # 远程运行归档的控制档案来源。

    # 类型检查阻止损坏的控制档案向下游传播。
    contract = (
        dict_profile.get("directory_contract", {})  # 隔离环境所在的目录合同分区。
        if isinstance(dict_profile.get("directory_contract"), dict)  # 收窄环境合同类型。
        else {}  # 无效合同不提供环境策略。
    )  # 经过类型收窄的目录合同。

    # 提取环境管理器、路径模板和启用条件。
    policy = contract.get("remote_environment_policy", {})  # 原始远程环境策略。

    # 非对象策略不能作为具名配置消费。
    return policy if isinstance(policy, dict) else {}

# 提取远程运行产物从活跃区到备份区的归档合同。
def remote_runtime_archive_policy(project: Path) -> dict[str, Any]:
    """读取远程运行产物的活跃与归档目录策略。

    参数：project 为项目根目录。
    返回：remote_runtime_archive_policy 映射；无有效配置时为空。
    """

    # 运行归档策略由项目控制档案集中管理。
    dict_profile = control_profile(project)  # 项目控制档案。

    # 损坏的 directory_contract 按未配置处理。
    contract = (
        dict_profile.get("directory_contract", {})  # 运行归档所在的目录合同分区。
        if isinstance(dict_profile.get("directory_contract"), dict)  # 收窄归档合同类型。
        else {}  # 无效合同不启用运行归档。
    )  # 经过类型确认的目录合同。

    # 提取活跃路径、备份路径和归档触发条件。
    policy = contract.get("remote_runtime_archive_policy", {})  # 原始运行归档策略。

    # 仅映射值可参与后续字段读取。
    return policy if isinstance(policy, dict) else {}

# 展开远程根、环境模板和运行模板形成部署保护计划。
def remote_deployment_plan(project: Path) -> dict[str, Any]:
    """构建远程工作区允许路径与保护策略。

    参数：project 为项目根目录。
    返回：远程根、环境、运行产物和变更审查的完整计划映射。
    """

    # 远程根决定其余模板是否需要展开为受管路径。
    str_workspace = remote_structure(project)  # 已规范禁用状态的远程根声明。

    # 隔离环境策略提供 conda 前缀路径和启用条件。
    dict_environment_policy = remote_environment_policy(project)  # 远程环境配置。

    # 运行策略提供活跃目录、备份目录与归档条件。
    dict_runtime_policy = remote_runtime_archive_policy(project)  # 远程产物归档配置。

    # 未配置远程根时不得凭模板创建孤立路径。
    planned = [] if str_workspace == "not configured" else [str_workspace]  # 远程受管路径候选。

    # 只有有效远程根才能承载设置、环境和运行目录。
    if str_workspace != "not configured":

        # 远程设置目录只允许部署非 local 配置。
        planned.append(f"{str_workspace.rstrip('/')}/{SETTINGS_FOLDER}/")

        # 环境模板统一为相对路径，避免重复斜杠影响保护比较。
        str_conda_template = normalize_rel(  # 规范化后的隔离环境模板。
            str(dict_environment_policy.get("path_template", "")).strip()  # 原始环境模板文本。
        )  # 远程隔离环境路径模板。

        # 活跃运行目录用于当前任务写入结果。
        str_active_template = normalize_rel(  # 规范化后的活跃运行目录模板。
            str(dict_runtime_policy.get("active_path_template", "")).strip()  # 原始活跃目录模板。
        )  # 活跃运行产物路径模板。

        # 备份模板定义验证后归档的层级位置。
        str_backup_template = normalize_rel(  # 规范化后的备份归档目录模板。
            str(dict_runtime_policy.get("backup_path_template", "")).strip()  # 原始备份目录模板。
        )  # 历史运行产物备份模板。

        # 三类模板都必须位于远程工作区根之下。
        for template in [str_conda_template, str_active_template, str_backup_template]:

            # 空模板表示对应能力未启用，不生成虚假计划路径。
            if template:

                # 拼接后的绝对远程路径同时进入允许和保护集合。
                planned.append(f"{str_workspace.rstrip('/')}/{template}")

        # 备份层级的父目录也需要预先批准，才能逐级创建。
        if str_backup_template:

            # 路径分段用于由叶到根枚举备份父目录。
            parts = str_backup_template.split("/")  # 备份模板的层级分段。

            # 至少保留一个顶层分段，防止生成远程根自身的空后缀。
            while len(parts) > 1:

                # 移除当前叶节点后得到下一层父目录。
                parts.pop()

                # 父目录加入计划后可通过创建审查而不放宽其他路径。
                planned.append(f"{str_workspace.rstrip('/')}/{'/'.join(parts)}")

    # 去重并排序，保证结构快照和发布收据可重复生成。
    planned = sorted(dict.fromkeys(planned))  # 稳定的远程受管路径集合。

    # 返回远程部署的完整机器可读治理合同。
    return {
        "workspace_root": str_workspace,
        "planned_structure": planned,
        "protected_paths": planned,
        "workspace_settings": workspace_settings_contract(),
        "conda_environment": {
            "status": dict_environment_policy.get("status", "disabled"),
            "scope": dict_environment_policy.get("scope", "remote-only"),
            "manager": dict_environment_policy.get("manager", "conda-prefix"),
            "path_template": str(
                dict_environment_policy.get("path_template", "")
            ).strip(),
            "required_when_remote_configured": bool(
                dict_environment_policy.get("required_when_remote_configured", True)
            ),
        },
        "runtime_artifacts": {
            "status": dict_runtime_policy.get("status", "disabled"),
            "active_path_template": str(
                dict_runtime_policy.get("active_path_template", "")
            ).strip(),
            "backup_path_template": str(
                dict_runtime_policy.get("backup_path_template", "")
            ).strip(),
            "run_id_required": bool(dict_runtime_policy.get("run_id_required", True)),
            "archive_after_verification": bool(
                dict_runtime_policy.get("archive_after_verification", False)
            ),
            "archive_trigger": str(
                dict_runtime_policy.get("archive_trigger", "")
            ).strip(),
        },
        "protected_path_classes": list(REMOTE_PROTECTED_PATH_CLASSES),
        "require_review_for_all_mutations": True,
        "review_required_for": ["create", "move", "delete", "rename"],
        "block_on_failed_review": True,
        "force_override_requires_user_confirmation": True,
    }

# 合并显式目录合同与项目类型默认布局。
def profile_layout_policy(project: Path) -> tuple[str, list[str], bool]:
    """解析项目主根目录、允许路径与强制布局开关。

    参数：project 为项目根目录。
    返回：主项目根、允许新增路径列表和是否强制主根布局。
    """

    # 项目种类和显式目录合同共同决定布局默认值。
    dict_profile = control_profile(project)  # 布局推导使用的项目控制档案。

    # 无有效目录合同时仍可从项目种类推导兼容默认值。
    contract = (
        dict_profile.get("directory_contract", {})  # 本地布局所在的目录合同分区。
        if isinstance(dict_profile.get("directory_contract"), dict)  # 收窄本地布局合同类型。
        else {}  # 无效合同触发项目类型默认布局。
    )  # 项目目录合同。

    # 显式主根配置优先于任何类型推导。
    str_primary = normalize_rel(  # 规范化主项目根。
        str(contract.get("primary_project_root", "")).strip()  # 原始主根配置文本。
    )

    # 旧控制档案缺少主根字段时按项目类型恢复既有布局。
    if not str_primary:

        # 项目类型决定使用 skills 还是 engineering 前缀。
        kind = str(dict_profile.get("kind", "")).strip().lower()  # 规范化项目类型。

        # 项目名称用于构造默认工作目录。
        name = str(dict_profile.get("name", "")).strip()  # 控制档案项目名称。

        # skill_layout 可覆盖技能源码的默认 skills/<name> 路径。
        skill_layout = (
            dict_profile.get("skill_layout", {})  # 技能源码目录覆盖配置。
            if isinstance(dict_profile.get("skill_layout"), dict)  # 仅映射可提供路径覆盖。
            else {}  # 无效技能布局回退到标准路径。
        )  # 技能项目布局映射。

        # 技能项目优先使用显式源码路径。
        if kind == "skill":

            # 缺少覆盖路径时回退到标准技能目录布局。
            str_primary = normalize_rel(str(skill_layout.get("path", "")).strip()) or (  # 技能主根。
                f"skills/{name}" if name else ""  # 使用项目名称构造技能主根。
            )

        # 工程项目遵循 engineering/<name> 的标准主根。
        elif kind == "engineering" and name:

            # 工程名称已去除空白，可直接组成相对路径。
            str_primary = f"engineering/{name}"  # 工程项目标准主根路径。

    # 显式允许路径逐项规范化并丢弃空值。
    list_allowed = [
        normalize_rel(item)  # 当前显式批准路径。
        for item in contract.get("allowed_new_paths", [])  # 遍历显式允许路径。
        if str(item).strip()  # 忽略空配置项。
    ]  # 控制档案允许新增路径。

    # 只配置主根时补齐治理、测试和产物的标准根目录。
    if not list_allowed and str_primary:

        # 默认集合保持功能完整，同时不允许任意新顶层目录。
        list_allowed = [
            str_primary,  # 项目源码主根目录。
            "tests",  # 单元与集成测试根。
            "smoke",  # 固定冒烟测试工作目录。
            "reports",  # 验证和构建报告目录。
            "runs",  # 运行产物根目录。
            "dist",  # 版本化发布包目录。
            "docs",  # 项目治理与开发文档根。
            ".agents",  # 项目代理控制和过程状态。
            "ref",  # 受控参考与审查材料目录。
        ]

    # 显式开关或可推导主根任一存在时都执行主根布局约束。
    bool_enforce = bool(  # 是否执行主项目根存在性约束。
        contract.get("enforce_primary_project_root", False)  # 显式强制开关。
        or str_primary  # 可推导主根时默认启用布局检查。
    )  # 主项目根布局强制状态。

    # 元组让计划生成器一次获得三项相互关联的策略。
    return str_primary, list_allowed, bool_enforce

# 构造初始化时写入的本地与远程目录计划。
def planned_structure(project: Path) -> dict[str, Any]:
    """根据项目档案和现有布局生成初始目录计划。

    参数：project 为项目根目录。
    返回：可写入 planned_structure.json 的完整治理映射。
    """

    # 一次读取主根、允许路径和强制开关，避免三者来源漂移。
    (
        tuple_primary_root,  # 项目主根路径。
        tuple_configured_paths,  # 显式批准路径集合。
        tuple_enforce_primary,  # 主根布局强制开关。
    ) = profile_layout_policy(project)  # 项目布局策略元组。

    # 显式允许路径存在时以控制档案为准。
    if tuple_configured_paths:

        # 集合形式便于后续无重复地补齐治理目录。
        set_current_dirs = set(tuple_configured_paths)  # 配置批准的目录集合。

    # 未配置布局时从当前顶层目录建立保守初始计划。
    else:

        # 忽略缓存和版本控制目录，保留现有业务布局。
        set_current_dirs = {
            path.name + "/"  # 当前发现的顶层目录。
            for path in project.iterdir()  # 遍历项目顶层成员。
            if path.is_dir() and path.name not in SKIP_DIRS  # 仅保留受管目录。
        }  # 从工作区发现的顶层目录集合。

    # 治理文档、设置和会话目录始终属于批准布局。
    set_current_dirs.update(
        {
            f"{SETTINGS_FOLDER}/",
            "docs/",
            "docs/dir_manager/",
            "docs/dir_manager/history_dir_manager/",
            "docs/handoff/",
            "docs/development/",
            "docs/install_configuration/",
            "docs/git_manager/",
        }
    )

    # 计划文件统一用尾斜杠表示目录而非同名文件。
    set_current_dirs = {
        item if item.endswith("/") else item + "/"  # 统一目录尾斜杠。
        for item in set_current_dirs  # 逐项规范目录标记。
    }  # 规范化后的允许目录集合。

    # 读取控制画像以取得当前项目已经批准的目录合同。
    dict_profile = control_profile(project)  # 包含项目目录和远程结构策略的控制画像

    # 非字典目录合同回退为空映射，避免无效画像污染计划文件。
    dict_directory_contract = (  # 完成类型收窄后的项目目录合同
        dict_profile.get("directory_contract", {})  # 控制画像声明的目录策略
        if isinstance(dict_profile.get("directory_contract"), dict)  # 只接受对象形式合同
        else {}  # 无效类型不投影任何目录策略
    )  # 可安全读取下级布局字段的目录合同

    # 测试布局由目录合同投影到批准计划，供结构门禁离线复核。
    dict_tests_layout = (  # 单根 tests 与一层功能目录布局合同
        dict_directory_contract.get("tests_layout", {})  # 项目明确批准的测试布局
        if isinstance(dict_directory_contract.get("tests_layout"), dict)  # 只接受对象形式布局
        else {}  # 无效布局不写入计划策略
    )  # 结构门禁读取的 tests 布局映射

    # 返回包含本地、远程和强制覆盖规则的初始计划。
    return {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "allowed_new_paths": sorted(set_current_dirs),
        "allowed_root_files": list(ALLOWED_ROOT_FILES),
        "root_optional_work_dirs": list(ROOT_OPTIONAL_WORK_DIRS),
        "root_optional_work_dir_prefixes": list(ROOT_OPTIONAL_WORK_DIR_PREFIXES),
        "workspace_settings": workspace_settings_contract(),
        "primary_project_root": f"{tuple_primary_root}/" if tuple_primary_root else "",
        "allowed_top_level_roots": sorted(
            {
                normalize_rel(item).split("/", 1)[0] + "/"
                for item in set_current_dirs
                if normalize_rel(item)
            }
        ),
        "enforce_primary_project_root": tuple_enforce_primary,
        "tests_layout": dict_tests_layout,
        "protected_paths": sorted(GOVERNANCE_PREFIXES),
        "review_required_for": ["create", "move", "delete", "rename"],
        "remote_deployment": remote_deployment_plan(project),
        "block_on_failed_review": True,
        "force_override_requires_user_confirmation": True,
        "force_override_archive": "docs/dir_manager/history_dir_manager/YYYYMMDD-HHMMSS",
    }

# 安全读取既有计划，供验证和兼容同步使用。
def load_planned(project: Path) -> dict[str, Any]:
    """读取已批准的目录结构计划。

    参数：project 为项目根目录。
    返回：计划映射；文件缺失或内容非对象时返回空映射。
    """

    # 计划文件是结构验证和目录变更审查的共同基线。
    planned = read_json(project / PLANNED_STRUCTURE)  # 原始计划结构 JSON。

    # 非对象 JSON 无法提供允许路径和保护字段。
    return planned if isinstance(planned, dict) else {}

# 从深层批准路径推导创建过程必需的父目录。
def allowed_parent_paths(planned: dict[str, Any]) -> set[str]:
    """推导所有已批准路径隐含允许创建的父目录。

    参数：planned 为目录结构计划。
    返回：不含叶节点的规范化父路径集合。
    """

    # 集合去除多个允许路径共享的父目录。
    set_parents: set[str] = set()  # 隐含批准的父级相对路径。

    # 每个显式允许路径都可能贡献若干层父目录。
    for item in planned.get("allowed_new_paths", []):

        # 统一分隔符后再按层级拆分。
        str_normalized = normalize_rel(item)  # 当前允许路径。

        # 空配置项不产生可创建目录。
        if not str_normalized:

            # 跳过空值并继续处理其余有效计划项。
            continue

        # 分段列表用于从顶层逐步重建父路径。
        parts = str_normalized.split("/")  # 当前路径层级。

        # 叶节点由 allowed_new_paths 直接授权，此处只生成其父级。
        for index in range(1, len(parts)):

            # 前 index 个分段组成一层可创建父目录。
            set_parents.add("/".join(parts[:index]))

    # 返回去重后的所有隐含父目录。
    return set_parents

# 解析允许置于工作区根的测试与运行产物目录名。
def configured_root_optional_work_dirs(planned: dict[str, Any]) -> set[str]:
    """读取允许位于工作区根的可选产物目录名。

    参数：planned 为目录结构计划。
    返回：规范化目录名集合；未配置时使用内置默认集合。
    """

    # 项目计划可收紧或扩展默认测试与运行目录集合。
    configured = planned.get("root_optional_work_dirs", [])  # 原始可选目录配置。

    # 去除空值并统一路径分隔符，便于顶层名称比较。
    values = {  # 有效可选工作目录集合。
        normalize_rel(item)  # 当前根级工作目录名。
        for item in configured  # 遍历项目配置的工作目录名。
        if normalize_rel(item)  # 过滤规范化后的空名称。
    }

    # 空配置保留历史默认行为，避免旧计划突然阻断测试目录。
    return values or set(ROOT_OPTIONAL_WORK_DIRS)

# 解析动态场景工作目录可使用的受控名称前缀。
def configured_root_optional_work_dir_prefixes(
    planned: dict[str, Any]
) -> tuple[str, ...]:
    """读取根级可选工作目录的允许前缀。

    参数：planned 为目录结构计划。
    返回：规范化前缀元组；未配置时返回默认前缀。
    """

    # 前缀配置支持 smoke-<scenario> 等动态夹具目录。
    configured = planned.get("root_optional_work_dir_prefixes", [])  # 原始目录前缀配置。

    # 元组保持计划给定顺序并过滤空前缀。
    tuple_values = tuple(  # 保留顺序的有效动态目录前缀。
        normalize_rel(item)  # 当前动态工作目录前缀。
        for item in configured  # 遍历计划配置的动态前缀。
        if normalize_rel(item)  # 过滤空前缀避免匹配所有目录。
    )  # 有效根级工作目录前缀。

    # 旧计划没有该字段时继续允许标准 smoke- 前缀。
    return tuple_values or ROOT_OPTIONAL_WORK_DIR_PREFIXES

# 判定候选路径是否属于根级工作产物目录类别。
def root_optional_work_dir_match(path: str, planned: dict[str, Any]) -> bool:
    """判断路径顶层是否属于允许的工作产物目录。

    参数：path 为候选相对路径，planned 为目录结构计划。
    返回：顶层目录命中固定名称或允许前缀时为 True。
    """

    # 统一路径表示后仅比较首个目录分段。
    str_normalized = normalize_rel(path)  # 规范化候选路径。

    # 空路径不代表任何可选工作目录。
    if not str_normalized:

        # 明确拒绝空值，避免 split 产生虚假顶层名称。
        return False

    # 工作目录必须位于根级，深层路径继承其顶层类别。
    top_level = str_normalized.split("/", 1)[0]  # 候选路径的顶层目录名。

    # 固定名称集合覆盖 tests、reports、runs 等标准目录。
    if top_level in configured_root_optional_work_dirs(planned):

        # 精确命中无需继续检查动态前缀。
        return True

    # 动态场景目录通过受控前缀匹配。
    return any(
        top_level.startswith(prefix)
        for prefix in configured_root_optional_work_dir_prefixes(planned)
    )

# 解释测试或运行产物为何不能嵌入主项目源码根。
def nested_workspace_artifact_reason(path: str, planned: dict[str, Any]) -> str | None:
    """识别被错误放入主项目根下的工作产物目录。

    参数：path 为候选路径，planned 为目录结构计划。
    返回：布局违规原因；路径不违规时返回 None。
    """

    # 候选路径和主根使用同一规范化口径。
    str_normalized = normalize_rel(path)  # 规范化候选相对路径。

    # 主项目根来自已批准计划，而非当前文件系统猜测。
    str_primary_root = normalize_rel(  # 规范化计划主项目根。
        str(planned.get("primary_project_root", "")).strip()  # 计划主根原始文本。
    )  # 计划声明的主项目根。

    # 缺少任一比较对象时无法判定嵌套违规。
    if not str_normalized or not str_primary_root:

        # 保持无诊断结果，由其他结构规则处理空配置。
        return None

    # 尾斜杠确保前缀匹配不会误伤同名相邻目录。
    prefix = str_primary_root.rstrip("/") + "/"  # 主项目根后代路径前缀。

    # 主根自身或主根之外的路径不属于本规则范围。
    if str_normalized == str_primary_root or not str_normalized.startswith(prefix):

        # 交给普通允许路径规则继续判断。
        return None

    # 去除主根前缀后检查内部各层目录名称。
    relative = str_normalized[len(prefix) :]  # 相对主项目根的后缀路径。

    # 空分段不参与目录类别匹配。
    components = [part for part in relative.split("/") if part]  # 主根内部路径分段。

    # 没有内部成员时等价于主根自身。
    if not components:

        # 此边界不构成工作产物嵌套。
        return None

    # 固定工作目录名用于逐层精确匹配。
    set_allowed_dirs = configured_root_optional_work_dirs(planned)  # 允许的产物目录名。

    # 动态工作目录使用计划批准的前缀匹配。
    tuple_prefixes = configured_root_optional_work_dir_prefixes(planned)  # 允许的产物目录前缀。

    # 任一内部层级出现工作目录都违反根级放置合同。
    for component in components:

        # 同时检查固定名称和动态场景前缀。
        if component in set_allowed_dirs or any(
            component.startswith(prefix) for prefix in tuple_prefixes
        ):

            # 返回包含实际路径的可操作诊断。
            return (
                "workspace artifact directory must stay at the work-folder root, "
                "not under the primary project root: "
                f"{str_normalized}"
            )

    # 主根内部未发现受限工作产物目录。
    return None

# 统一判断显式路径、必要父级和工作目录的批准状态。
def allowed_path(path: str, planned: dict[str, Any]) -> bool:
    """判断目录路径是否由计划显式或隐式批准。

    参数：path 为候选目录，planned 为目录结构计划。
    返回：路径属于工作目录、允许路径或必要父目录时为 True。
    """

    # 所有比较都使用无首尾斜杠的统一相对路径。
    str_normalized = normalize_rel(path)  # 规范化候选目录。

    # 根级测试和运行产物按专用动态规则批准。
    if root_optional_work_dir_match(str_normalized, planned):

        # 工作产物目录无需列入每个项目的静态路径清单。
        return True

    # 显式允许路径过滤空项后参与精确和后代匹配。
    allowed = [
        normalize_rel(item)  # 当前批准路径。
        for item in planned.get("allowed_new_paths", [])  # 遍历计划允许路径。
        if str(item).strip()  # 排除空路径声明。
    ]  # 计划批准的规范化路径。

    # 创建深层批准路径前，其父目录也必须可创建。
    set_parents = allowed_parent_paths(planned)  # 隐含批准的父目录集合。

    # 必要父目录不要求自身重复列入允许清单。
    if str_normalized in set_parents:

        # 精确父级命中即可通过结构审查。
        return True

    # 显式路径及其全部后代继承批准状态。
    return any(
        str_normalized == item or str_normalized.startswith(item.rstrip("/") + "/")
        for item in allowed
    )

# 读取项目根可保留的代理说明与工具配置文件白名单。
def allowed_root_files(planned: dict[str, Any]) -> list[str]:
    """读取计划允许保留在项目根的固定文件名。

    参数：planned 为目录结构计划。
    返回：非空文件名列表；无有效配置时使用默认白名单。
    """

    # 项目计划可以覆盖默认代理说明和工具配置文件集合。
    configured = planned.get("allowed_root_files", [])  # 原始根文件白名单。

    # 只有列表类型才可按元素解释为文件名。
    if isinstance(configured, list):

        # 去除空白与空元素，保留配置顺序。
        values = [  # 有效根文件名。
            str(item).strip()  # 当前白名单文件名。
            for item in configured  # 遍历根文件白名单配置。
            if str(item).strip()  # 丢弃空文件名。
        ]

        # 至少一个有效值时尊重项目覆盖配置。
        if values:

            # 返回新列表，避免调用方修改计划原对象。
            return values

    # 缺失或无效配置回退到受控默认集合。
    return list(ALLOWED_ROOT_FILES)

# 合并固定白名单与历史治理输入模式判断根文件合法性。
def is_allowed_root_file(name: str, planned: dict[str, Any]) -> bool:
    """判断根级文件名是否符合固定或兼容模式白名单。

    参数：name 为根级文件名，planned 为目录结构计划。
    返回：文件名被计划或兼容输入模式允许时为 True。
    """

    # 根文件比较保留大小写，仅去除人工输入空白。
    normalized = str(name).strip()  # 待检查根文件名。

    # 项目计划中的固定白名单具有最高优先级。
    if normalized in set(allowed_root_files(planned)):

        # 精确命中后无需执行通配模式检查。
        return True

    # 历史回答和会话输入通过有限模式兼容。
    return any(fnmatch(normalized, pattern) for pattern in ALLOWED_ROOT_FILE_PATTERNS)

# 汇总当前快照中违反根文件合同的成员。
def unapproved_root_files(
    current: dict[str, Any], planned: dict[str, Any]
) -> list[str]:
    """收集当前快照中未获批准的根级文件。

    参数：current 为当前结构快照，planned 为已批准目录计划。
    返回：违规文件名或更具体的工作区设置位置原因列表。
    """

    # 诊断按扫描顺序保留，便于用户逐项修复。
    list_violations: list[str] = []  # 未批准根文件诊断。

    # 只检查 files 清单中的项目成员。
    for file_path in current.get("files", []):

        # 统一分隔符后判断文件是否真正位于根级。
        str_normalized = normalize_rel(file_path)  # 当前文件相对路径。

        # 空值和包含目录分隔符的文件不属于根级规则范围。
        if not str_normalized or "/" in str_normalized:

            # 深层文件由允许路径和专用设置规则验证。
            continue

        # 活跃回答、会话和审查 JSON 是受控过程输入。
        if EPHEMERAL_ROOT_INPUT_FILE_RE.fullmatch(str_normalized):

            # 临时输入不会成为长期根文件白名单的一部分。
            continue

        # 固定白名单和兼容模式都未命中时登记违规。
        if not is_allowed_root_file(str_normalized, planned):

            # 设置文件错位时提供比普通文件名更具体的修复原因。
            explicit_reason = workspace_settings_location_reason(  # 专用设置位置诊断。
                str_normalized  # 当前未批准根文件。
            )

            # 普通根文件保留相对路径，设置文件优先使用策略说明。
            list_violations.append(explicit_reason or str_normalized)

    # 返回所有当前快照中的根级违规项。
    return list_violations

# 检查本地与远程设置文件是否处于指定目录边界。
def workspace_settings_structure_violations(current: dict[str, Any]) -> list[str]:
    """检查工作区设置文件是否位于规定目录并符合本地性边界。

    参数：current 为当前结构快照。
    返回：去重排序后的设置文件位置违规原因。
    """

    # 原因列表允许多个错位文件汇总到一次验证结果。
    list_violations: list[str] = []  # 工作区设置布局诊断。

    # 设置位置规则适用于快照中的每个文件层级。
    for file_path in current.get("files", []):

        # 规范化相对路径后交给统一设置策略判断。
        str_normalized = normalize_rel(file_path)  # 当前文件的标准相对路径。

        # 空快照项没有可验证的文件位置。
        if not str_normalized:

            # 跳过损坏空项，其他结构验证器会报告快照问题。
            continue

        # 策略函数同时覆盖目录错位和 local 文件远程边界。
        reason = workspace_settings_location_reason(str_normalized)  # 当前设置位置诊断。

        # None 表示该文件不是设置文件或位置符合合同。
        if reason:

            # 收集可直接展示给用户的具体违规说明。
            list_violations.append(reason)

    # 去重后排序确保验证输出稳定且没有重复原因。
    return sorted(dict.fromkeys(list_violations))

# 将治理 JSON 的读取与对象类型错误纳入统一诊断。
def verify_json(path: Path, errors: list[str]) -> dict[str, Any]:
    """读取治理 JSON 并把缺失或类型错误写入错误列表。

    参数：path 为 JSON 文件路径，errors 为共享错误列表。
    返回：有效非空映射；验证失败时返回空映射。
    """

    # 公共 JSON 读取器统一处理文件缺失和解析失败。
    dict_data = read_json(path)  # 待验证 JSON 内容。

    # 治理快照必须是非空对象，不能接受数组或标量。
    if not isinstance(dict_data, dict) or not dict_data:

        # 错误携带文件路径，便于调用方区分当前与计划快照。
        errors.append(f"{path.as_posix()}: missing or invalid JSON object")

        # 空映射允许后续验证安全继续并汇总更多问题。
        return {}

    # 返回经过对象类型和非空约束的治理内容。
    return dict_data

# 远程部署字段验证器返回精确到字段路径的合同错误。
def remote_deployment_path_errors(remote: dict[str, Any]) -> list[str]:
    """验证远程部署映射的必填值、容器类型和嵌套字段。

    参数：remote 为 remote_deployment 配置映射。
    返回：保持字段检查顺序的远程部署合同错误。
    """

    # 错误前缀统一指向批准结构文件。
    str_prefix = f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment"  # 远程合同错误前缀。

    # 按公开诊断顺序检查简单字段存在性和容器类型。
    list_checks = [  # 顶层远程合同检查表。
        ("workspace_root", bool(remote.get("workspace_root")), "must be configured or `not configured`"),  # 工作区根锚点。
        ("planned_structure", isinstance(remote.get("planned_structure"), list), "must be a list"),  # 远程规划目录清单。
        ("conda_environment", isinstance(remote.get("conda_environment"), dict), "must be configured"),  # Conda 环境合同。
        ("runtime_artifacts", isinstance(remote.get("runtime_artifacts"), dict), "must be configured"),  # 运行时产物合同。
        ("review_required_for", isinstance(remote.get("review_required_for"), list), "must be a list"),  # 强制评审操作清单。
        ("protected_path_classes", isinstance(remote.get("protected_path_classes"), list), "must be a list"),  # 受保护路径类别。
        ("require_review_for_all_mutations", bool(remote.get("require_review_for_all_mutations")), "must be true"),  # 全变更评审开关。
    ]

    # 顶层字段错误保持原有逐项诊断顺序。
    list_errors = [  # 顶层远程合同错误。
        f"{str_prefix}.{str_field} {str_message}"  # 带完整配置路径的错误文本。
        for str_field, bool_valid, str_message in list_checks  # 按声明顺序遍历字段合同。
        if not bool_valid  # 仅输出未通过的字段。
    ]

    # 有效环境映射必须显式声明路径模板。
    dict_conda = remote.get("conda_environment", {}) if isinstance(remote.get("conda_environment"), dict) else {}  # 隔离环境映射。

    # 字段缺失与空模板具有不同配置语义。
    if "path_template" not in dict_conda:

        # 环境路径错误追加在顶层类型检查之后。
        list_errors.append(f"{str_prefix}.conda_environment.path_template must be configured")

    # 运行产物字段必须覆盖路径、运行标识和归档开关。
    dict_runtime = remote.get("runtime_artifacts", {}) if isinstance(remote.get("runtime_artifacts"), dict) else {}  # 运行产物映射。

    # 逐项验证保持错误消息精确到缺失字段。
    for str_field in [
        "active_path_template",
        "backup_path_template",
        "run_id_required",
        "archive_after_verification",
        "archive_trigger",
    ]:

        # 缺失字段不能由默认值静默掩盖发布配置漂移。
        if str_field not in dict_runtime:

            # 错误路径携带实际字段名，便于直接修复计划 JSON。
            list_errors.append(f"{str_prefix}.runtime_artifacts.{str_field} must be configured")

    # 调用方把本列表合并到完整目录治理验证结果。
    return list_errors

# 验证远程部署计划具备路径保护和强制审查字段。
def verify_remote_deployment_policy(
    planned: dict[str, Any], list_errors: list[str]
) -> None:
    """校验 planned-structure 中的 remote_deployment 治理契约。

    参数：planned 为已批准结构计划，list_errors 为共享错误列表。
    返回：无；发现的远程部署合同错误追加到 list_errors。

    数组契约:
        shape/维度: 本函数处理目录治理 JSON 映射，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict 和 list 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义来自 planned-structure schema。
    """

    # 远程合同缺失时保留 None，以区分空映射和完全未配置。
    remote = planned.get("remote_deployment") if planned else None  # 原始远程部署合同。

    # 非空计划必须提供对象类型的 remote_deployment 分区。
    if planned and not isinstance(remote, dict):

        # 顶层类型错误无法继续安全读取内部字段。
        list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment must be configured")

        # 当前验证器完成诊断后立即返回。
        return

    # 有效映射的内部诊断统一追加到共享错误列表。
    if isinstance(remote, dict):

        # helper 只返回诊断，不产生写入副作用。
        list_errors.extend(remote_deployment_path_errors(remote))

# 确认目录治理的文档、快照和证据目录已经落地。
def verify_manager_paths(project: Path, list_errors: list[str]) -> list[str]:
    """验证目录治理必需目录和文件是否存在。

    参数：project 为项目根目录，list_errors 为共享错误列表。
    返回：本阶段检查过的治理相对路径列表。
    """

    # 检查清单同时作为公开验证结果的 checked 字段。
    list_checked = [
        str(DIR_MANAGER_DIR.as_posix()),  # 目录治理文档根。
        str(CHANGE_REVIEWS.as_posix()),  # 变更审批证据存放位置。
        str(HISTORY_DIR_MANAGER.as_posix()),  # 历史治理快照目录。
        str(DIR_MANAGER_MD.as_posix()),  # 目录治理说明文档。
        str(CURRENT_STRUCTURE.as_posix()),  # 当前结构快照。
        str(PLANNED_STRUCTURE.as_posix()),  # 已批准结构计划。
    ]  # 目录治理必需路径清单。

    # 三个目录分别承载当前状态、审查证据和历史归档。
    for rel in [DIR_MANAGER_DIR, CHANGE_REVIEWS, HISTORY_DIR_MANAGER]:

        # 缺失目录会使后续写入或审计无法完成。
        if not (project / rel).is_dir():

            # 保留相对路径使错误可跨工作区复现。
            list_errors.append(f"missing dir manager directory: {rel.as_posix()}")

    # 说明文档、当前快照和计划快照都是必需文件。
    for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]:

        # 文件缺失与 JSON 内容错误分别报告。
        if not (project / rel).is_file():

            # 调用方可据此选择初始化而非修复内容。
            list_errors.append(f"missing dir manager file: {rel.as_posix()}")

    # 返回固定清单而非仅存在项，完整表达验证覆盖面。
    return list_checked

# 校验当前快照和计划快照的顶层机器可读合同。
def verify_structure_schema(
    current: dict[str, Any], planned: dict[str, Any], list_errors: list[str]
) -> None:
    """验证当前与计划结构快照的顶层字段类型。

    参数：current 为当前快照，planned 为计划快照，list_errors 为共享错误列表。
    返回：无；schema 错误追加到 list_errors。
    """

    # 当前快照的目录和文件都必须保持 JSON 数组合同。
    for key in ["directories", "files"]:

        # 空快照已由 verify_json 报告，此处避免重复错误。
        if current and not isinstance(current.get(key), list):

            # 字段级诊断帮助直接修复损坏快照。
            list_errors.append(f"{CURRENT_STRUCTURE.as_posix()}: `{key}` must be a list")

    # 计划中的三个可枚举白名单同样必须使用数组。
    for key in ["allowed_new_paths", "review_required_for", "allowed_root_files"]:

        # 仅非空计划进入字段类型验证。
        if planned and not isinstance(planned.get(key), list):

            # 错误保留字段名以区分不同计划合同。
            list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: `{key}` must be a list")

    # 工作区设置策略必须是可读取的映射。
    if planned and not isinstance(planned.get("workspace_settings"), dict):

        # 设置策略类型错误会破坏本地文件远程阻断。
        list_errors.append(
            f"{PLANNED_STRUCTURE.as_posix()}: `workspace_settings` must be configured"
        )

    # 顶层允许根用于快速拒绝未经计划的新目录。
    if planned and not isinstance(planned.get("allowed_top_level_roots"), list):

        # 强制数组合同以支持稳定成员比较。
        list_errors.append(
            f"{PLANNED_STRUCTURE.as_posix()}: `allowed_top_level_roots` must be a list"
        )

    # 失败审查必须阻断执行，不能由项目计划关闭。
    if planned and not planned.get("block_on_failed_review", False):

        # 缺失真值表示目录安全门被削弱。
        list_errors.append(
            f"{PLANNED_STRUCTURE.as_posix()}: block_on_failed_review must be true"
        )

    # 强制覆盖前必须声明历史归档目标。
    if planned and not planned.get("force_override_archive"):

        # 无归档位置将丢失覆盖前目录治理证据。
        list_errors.append(
            f"{PLANNED_STRUCTURE.as_posix()}: force_override_archive must be configured"
        )

    # 远程分区由专用验证器检查其嵌套字段。
    verify_remote_deployment_policy(planned, list_errors)

# 确认设置目录、默认文件和远程阻断配置未漂移。
def verify_workspace_settings_policy(
    planned: dict[str, Any], list_errors: list[str]
) -> None:
    """验证计划中的工作区设置路径和远程阻断策略。

    参数：planned 为计划快照，list_errors 为共享错误列表。
    返回：无；设置策略错误追加到 list_errors。
    """

    # schema 验证后再次收窄类型，防止损坏输入引发异常。
    settings_policy = (
        planned.get("workspace_settings", {})  # 原始工作区设置分区。
        if isinstance(planned.get("workspace_settings"), dict)  # 收窄设置策略类型。
        else {}  # 错误类型由 schema 验证记录。
    )  # 可安全读取的工作区设置策略。

    # 空策略的缺失错误已由顶层 schema 验证覆盖。
    if not settings_policy:

        # 无可验证字段时直接返回，继续汇总其他结构问题。
        return

    # 设置目录必须与公共策略常量一致。
    if str(settings_policy.get("folder", "")).strip() != SETTINGS_FOLDER:

        # 固定目录避免本地设置散落到源码或项目根。
        list_errors.append(
            f"{PLANNED_STRUCTURE.as_posix()}: workspace_settings.folder "
            f"must be `{SETTINGS_FOLDER}`"
        )

    # 本地默认文件必须位于受管设置目录。
    if (
        str(settings_policy.get("local_default_file", "")).strip()
        != f"{SETTINGS_FOLDER}/project.local.json"
    ):

        # 明确期望路径供计划生成器或用户修复。
        list_errors.append(
            f"{PLANNED_STRUCTURE.as_posix()}: workspace_settings.local_default_file "
            f"must be `{SETTINGS_FOLDER}/project.local.json`"
        )

    # 远程默认文件路径由公共设置策略统一定义。
    if (
        str(settings_policy.get("remote_default_file", "")).strip()
        != REMOTE_DEFAULT_SETTINGS
    ):

        # 防止计划与部署端读取不同配置文件。
        list_errors.append(
            f"{PLANNED_STRUCTURE.as_posix()}: workspace_settings.remote_default_file "
            f"must be `{REMOTE_DEFAULT_SETTINGS}`"
        )

    # local 文件必须明确禁止复制到远程工作区。
    if not settings_policy.get("local_files_remote_blocked"):

        # 该开关保护本机账号、端口和路径等私有配置。
        list_errors.append(
            f"{PLANNED_STRUCTURE.as_posix()}: "
            "workspace_settings.local_files_remote_blocked must be true"
        )

# 对照批准计划检查主根、目录和根文件的实际布局。
def verify_current_layout(
    current: dict[str, Any], planned: dict[str, Any], list_errors: list[str]
) -> None:
    """比较当前目录快照与已批准布局。

    参数：current 为当前快照，planned 为计划快照，list_errors 为共享错误列表。
    返回：无；布局漂移诊断追加到 list_errors。
    """

    # 主项目根经过规范化后用于直接和后代存在性检查。
    str_primary_root = normalize_rel(  # 规范化后的主项目根。
        str(planned.get("primary_project_root", "")).strip()  # 计划主根配置文本。
    )  # 计划要求的主项目根。

    # 仅启用强制主根且配置非空时检查其存在性。
    if planned.get("enforce_primary_project_root") and str_primary_root:

        # 主根本身或任一后代存在都证明目录已落地。
        bool_primary_root_missing = (
            str_primary_root not in current.get("directories", [])  # 快照未列出主根本身。
            and not any(  # 同时确认没有任何主根后代。
                path.startswith(str_primary_root + "/")  # 当前目录是否属于主根后代。
                for path in current.get("directories", [])  # 遍历快照目录成员。
            )
        )  # 当前快照是否完全缺少主项目根。

        # 缺失主根意味着源码落在了目录合同之外。
        if bool_primary_root_missing:

            # 诊断包含期望路径，便于迁移或修复计划。
            list_errors.append(
                f"{PLANNED_STRUCTURE.as_posix()}: required primary project root "
                f"is missing: {str_primary_root}/"
            )

    # 当前每个目录都必须符合工作产物和允许路径规则。
    for directory in current.get("directories", []):

        # 快照路径先统一分隔符和边界斜杠。
        str_normalized = normalize_rel(directory)  # 当前目录相对路径。

        # 空项不能形成有效布局诊断。
        if not str_normalized:

            # schema 允许空字符串时安全跳过，避免误报根目录。
            continue

        # 主根内部出现 tests/runs 等产物目录需给出专门原因。
        nested_reason = nested_workspace_artifact_reason(  # 嵌套产物目录诊断。
            str_normalized,  # 当前目录路径。
            planned,  # 已批准目录计划。
        )

        # 专门诊断优先于普通未批准路径消息。
        if nested_reason:

            # 当前快照前缀标识实际发生漂移的证据文件。
            list_errors.append(f"{CURRENT_STRUCTURE.as_posix()}: {nested_reason}")

            # 已有精确原因时不再追加泛化重复错误。
            continue

        # 其余目录必须命中显式路径、后代或必要父级。
        if not allowed_path(str_normalized, planned):

            # 保留实际目录路径供目录审查载荷直接引用。
            list_errors.append(
                f"{CURRENT_STRUCTURE.as_posix()}: directory violates planned "
                f"structure: {str_normalized}"
            )

    # 设置文件错位诊断已经去重排序，可批量附加快照来源。
    list_errors.extend(
        f"{CURRENT_STRUCTURE.as_posix()}: {item}"
        for item in workspace_settings_structure_violations(current)
    )

    # 根级文件使用固定白名单、兼容模式和临时输入规则验证。
    for file_path in unapproved_root_files(current, planned):

        # 每个违规文件独立报告，方便逐项移除或纳入计划。
        list_errors.append(
            f"{CURRENT_STRUCTURE.as_posix()}: root-level file violates "
            f"planned structure: {file_path}"
        )

# 编排目录治理的存在性、schema、策略和布局验证。
def verify_dir_manager(project: Path) -> dict[str, Any]:
    """验证目录治理文件、schema、策略和当前布局。

    参数：project 为项目根目录。
    返回：项目路径、检查清单和全部验证错误。
    """

    # 所有验证阶段共享错误列表，以一次返回完整修复面。
    list_errors: list[str] = []  # 目录治理验证错误。

    # 路径验证同时产生公开 checked 清单。
    list_checked = verify_manager_paths(project, list_errors)  # 已检查治理路径。

    # 只在文件存在时读取，缺失错误已由路径验证记录。
    current = (
        verify_json(project / CURRENT_STRUCTURE, list_errors)  # 读取当前结构对象。
        if (project / CURRENT_STRUCTURE).exists()  # 文件存在时执行内容验证。
        else {}  # 缺失已由路径检查报告。
    )  # 当前目录结构快照。

    # 计划快照与当前快照独立读取并汇总解析错误。
    planned = (
        verify_json(project / PLANNED_STRUCTURE, list_errors)  # 读取计划结构对象。
        if (project / PLANNED_STRUCTURE).exists()  # 文件存在时执行计划验证。
        else {}  # 缺失时保持空计划安全继续。
    )  # 已批准目录结构计划。

    # 顶层 schema 和远程嵌套合同始终执行。
    verify_structure_schema(current, planned, list_errors)

    # 只有两份有效快照同时存在时才能比较具体布局。
    if current and planned:

        # 设置策略先验证，保证本地与远程配置边界明确。
        verify_workspace_settings_policy(planned, list_errors)

        # 最后比较主根、目录、设置文件和根级文件布局。
        verify_current_layout(current, planned, list_errors)

    # 返回稳定 schema 供 CLI 决定退出码并渲染 JSON。
    return {"project": str(project), "checked": list_checked, "errors": list_errors}

# 初始化治理目录并同步计划与当前结构快照。
def init_dir_manager(project: Path) -> dict[str, Any]:
    """创建或同步项目目录治理文档和结构快照。

    参数：project 为项目根目录。
    返回：项目路径、写入文件清单和同步后的验证错误。
    """

    # 治理根目录是说明文档、快照和审查记录的共同父级。
    target = project / DIR_MANAGER_DIR  # 目录治理文档绝对路径。

    # 初始化允许重复执行，不删除任何既有治理内容。
    target.mkdir(parents=True, exist_ok=True)

    # 审查记录目录独立于结构快照，便于逐次留证。
    (project / CHANGE_REVIEWS).mkdir(parents=True, exist_ok=True)

    # 强制覆盖前的历史快照统一归档到专用目录。
    (project / HISTORY_DIR_MANAGER).mkdir(parents=True, exist_ok=True)

    # 说明文档仅在缺失时生成，保留已有人工补充。
    if not (project / DIR_MANAGER_MD).exists():

        # 使用当前项目脚本布局渲染可复制命令。
        (project / DIR_MANAGER_MD).write_text(
            dir_manager_doc(project), encoding="utf-8"
        )

    # 期望计划综合项目控制档案、当前布局和远程策略。
    dict_desired_planned = planned_structure(project)  # 本次推导的目录计划。

    # 首次初始化直接写入完整计划结构。
    if not (project / PLANNED_STRUCTURE).exists():

        # 排序键输出便于版本审查和确定性比较。
        (project / PLANNED_STRUCTURE).write_text(
            json.dumps(dict_desired_planned, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    # 已有计划按显式配置或兼容迁移策略选择性同步。
    else:

        # 读取旧计划作为保留用户批准路径的更新基线。
        dict_planned = load_planned(project)  # 当前已批准目录计划。

        # 项目档案决定是否采用完整声明式同步。
        (
            tuple_primary_root,  # 当前档案推导的主根。
            tuple_configured_paths,  # 当前档案的显式允许路径。
            tuple_enforce_primary,  # 当前档案的主根强制策略。
        ) = profile_layout_policy(project)  # 当前项目布局策略。

        # 浅拷贝避免在比较完成前修改读取结果。
        dict_rewritten = dict(dict_planned)  # 待写回计划副本。

        # 变更标志确保没有语义漂移时不刷新时间戳和文件。
        bool_changed = False  # 计划是否需要持久化。

        # 远程策略始终跟随当前项目控制档案同步。
        remote_plan = dict_desired_planned.get("remote_deployment", {})  # 期望远程部署分区。

        # 远程合同变化时更新对应分区而不影响本地允许路径。
        if dict_rewritten.get("remote_deployment") != remote_plan:

            # 替换完整远程分区，防止遗留已废弃嵌套字段。
            dict_rewritten["remote_deployment"] = remote_plan  # 同步后的远程计划。

            # 标记需要写回计划文件。
            bool_changed = True  # 已检测到远程策略变化。

        # 显式 allowed_new_paths 表示控制档案拥有完整计划权威。
        if tuple_configured_paths:

            # 比较副本排除每次生成都会变化的时间戳。
            dict_current_compare = dict(dict_planned)  # 去时间戳前的当前计划。

            # 期望副本同样去除非语义生成时间。
            dict_desired_compare = dict(dict_desired_planned)  # 去时间戳前的期望计划。

            # 当前生成时间不应触发计划重写。
            dict_current_compare.pop("generated_at", None)

            # 期望生成时间也从语义比较中排除。
            dict_desired_compare.pop("generated_at", None)

            # 任一合同字段变化时使用完整声明式计划替换旧版。
            if dict_current_compare != dict_desired_compare:

                # 显式配置模式不保留已从控制档案移除的旧字段。
                dict_rewritten = dict_desired_planned  # 完整同步后的目录计划。

                # 完整计划差异需要持久化。
                bool_changed = True  # 已检测到声明式计划变化。

        # 兼容模式保留旧计划允许路径，仅刷新派生和安全字段。
        else:

            # 现有允许路径用于重新推导顶层根清单。
            current_allowed = [  # 当前计划中的有效允许路径。
                normalize_rel(item)  # 当前保留的批准路径。
                for item in dict_rewritten.get("allowed_new_paths", [])  # 遍历旧计划路径。
                if str(item).strip()  # 忽略旧计划空项。
            ]

            # 顶层清单由允许路径首分段稳定推导。
            derived_top = sorted(  # 当前允许路径对应的顶层根。
                {
                    item.split("/", 1)[0] + "/"  # 当前批准路径的顶层根。
                    for item in current_allowed  # 遍历有效批准路径。
                    if item  # 防止空值生成根斜杠。
                }
            )

            # 派生顶层根变化时修复计划缓存字段。
            if dict_rewritten.get("allowed_top_level_roots") != derived_top:

                # 保留 allowed_new_paths，仅更新其派生索引。
                dict_rewritten["allowed_top_level_roots"] = derived_top  # 同步后的顶层根。

                # 派生索引变化需要写回。
                bool_changed = True  # 已修复顶层根清单。

            # 主根路径应跟随当前项目档案推导结果。
            if dict_rewritten.get("primary_project_root", "") != tuple_primary_root:

                # 更新主根但不改变旧计划批准的其他路径。
                dict_rewritten["primary_project_root"] = tuple_primary_root  # 同步后的主项目根。

                # 主根变化会影响后续布局验证。
                bool_changed = True  # 已同步主项目根。

            # 主根强制开关必须与当前档案策略一致。
            if (
                dict_rewritten.get("enforce_primary_project_root", False)
                != tuple_enforce_primary
            ):

                # 写入布尔策略供验证器决定是否检查主根存在。
                dict_rewritten["enforce_primary_project_root"] = (  # 同步后的主根强制开关。
                    tuple_enforce_primary  # 当前档案的强制策略值。
                )

                # 安全开关变化必须持久化。
                bool_changed = True  # 已同步主根强制策略。

            # 根文件白名单跟随当前生成器安全默认值升级。
            if dict_rewritten.get("allowed_root_files") != dict_desired_planned.get(
                "allowed_root_files"
            ):

                # 替换白名单可纳入新治理文件并移除过时例外。
                dict_rewritten["allowed_root_files"] = (  # 同步后的根文件白名单。
                    dict_desired_planned.get("allowed_root_files", [])  # 当前安全默认白名单。
                )

                # 白名单漂移需要写回计划。
                bool_changed = True  # 已同步根文件白名单。

        # 仅实际合同变化时更新生成时间并写文件。
        if bool_changed:

            # 使用本次期望计划时间标记同步发生时刻。
            dict_rewritten["generated_at"] = dict_desired_planned[  # 最新计划生成时间。
                "generated_at"  # 本次计划推导时间字段。
            ]

            # 确定性 JSON 输出便于后续 freshness 和发布审计。
            (project / PLANNED_STRUCTURE).write_text(
                json.dumps(dict_rewritten, indent=2, sort_keys=True), encoding="utf-8"
            )

    # 计划同步完成后重新扫描工作区，确保当前快照包含新治理文件。
    dict_structure = scan_structure(project)  # 最新项目目录结构。

    # 当前快照每次初始化都刷新，以反映实际文件系统状态。
    (project / CURRENT_STRUCTURE).write_text(
        json.dumps(dict_structure, indent=2, sort_keys=True), encoding="utf-8"
    )

    # 写入完成后立即验证，返回真实治理状态而非假定成功。
    dict_verify = verify_dir_manager(project)  # 初始化后的目录治理验证结果。

    # 公开结果保持既有 CLI JSON schema。
    return {
        "project": str(project),
        "written": [
            str(DIR_MANAGER_MD),
            str(CURRENT_STRUCTURE),
            str(PLANNED_STRUCTURE),
        ],
        "errors": dict_verify["errors"],
    }

# 在强制覆盖前保存完整目录治理和审查证据。
def archive_dir_manager(
    project: Path, reason: str = "", review_file: str | None = None
) -> dict[str, Any]:
    """归档当前目录治理文档、快照和变更审查证据。

    参数：project 为项目根目录，reason 为归档原因，review_file 为关联审查文件。
    返回：项目路径、归档目录和全部归档文件列表。
    """

    # 三个核心治理文件缺失时先初始化完整可归档状态。
    if not all(
        (project / rel).exists()
        for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]
    ):

        # 初始化只补齐治理文件，不执行任何业务目录变更。
        init_dir_manager(project)

    # 历史根目录允许在首次强制覆盖前按需创建。
    (project / HISTORY_DIR_MANAGER).mkdir(parents=True, exist_ok=True)

    # 秒级时间戳为每次归档生成独立且可排序的目录。
    archive_root = project / HISTORY_DIR_MANAGER / stamp()  # 本次归档绝对路径。

    # 同秒重复归档应显式失败，避免覆盖既有证据。
    archive_root.mkdir(parents=True, exist_ok=False)

    # 清单使用项目相对路径写入公开返回和 manifest。
    list_archived: list[str] = []  # 已复制的归档文件路径。

    # 说明文档与两份结构快照构成最小治理证据集。
    for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]:

        # 将项目相对路径解析为当前源文件。
        source = project / rel  # 待归档治理文件。

        # 初始化后仍仅复制实际存在的普通文件。
        if source.is_file():

            # 核心文件在归档根保持扁平稳定名称。
            target = archive_root / rel.name  # 核心治理文件归档目标。

            # 字节复制保留原始编码和换行证据。
            target.write_bytes(source.read_bytes())

            # 记录可跨工作区展示的项目相对路径。
            list_archived.append(str(target.relative_to(project).as_posix()))

    # 变更审查目录存在时一并归档全部 JSON 证据。
    if (project / CHANGE_REVIEWS).is_dir():

        # 审查文件保持在同名子目录，避免与核心快照冲突。
        reviews_target = archive_root / CHANGE_REVIEWS.name  # 审查证据归档目录。

        # 多个审查文件共享归档子目录。
        reviews_target.mkdir(parents=True, exist_ok=True)

        # 文件名排序确保 manifest 清单跨运行稳定。
        for review in sorted((project / CHANGE_REVIEWS).glob("*.json")):

            # 每份审查证据保留原文件名。
            target = reviews_target / review.name  # 当前审查文件归档目标。

            # 原始 JSON 字节作为强制覆盖前审计证据保存。
            target.write_bytes(review.read_bytes())

            # 追加审查归档相对路径到统一清单。
            list_archived.append(str(target.relative_to(project).as_posix()))

    # manifest 记录归档时刻、原因、关联审查与文件集合。
    dict_manifest = {
        "archived_at": datetime.now().isoformat(timespec="seconds"),  # 归档创建时间。
        "reason": reason or "force-confirmed directory override",  # 用户确认的归档原因。
        "review_file": review_file or "",  # 关联目录审查证据路径。
        "archived_files": list_archived,  # manifest 写入前的已归档文件。
        "required_before": (  # 归档动作的强制执行边界。
            "applying any user force-confirmed blocked directory structure change"  # 覆盖前置条件。
        ),
    }  # 本次目录治理归档清单。

    # manifest 固定写入归档根，便于自动验证器发现。
    manifest_path = archive_root / "archive_manifest.json"  # 归档清单文件路径。

    # 排序键 JSON 便于人工审查和确定性测试。
    manifest_path.write_text(
        json.dumps(dict_manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    # manifest 自身也属于本次公开归档结果。
    list_archived.append(str(manifest_path.relative_to(project).as_posix()))

    # 返回既有归档 CLI 所依赖的稳定结果字段。
    return {
        "project": str(project),
        "archive_dir": str(archive_root),
        "archived": list_archived,
    }
