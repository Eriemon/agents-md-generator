"""提供 docs 治理命令共享的路径、JSON、状态和归档辅助函数。"""

# 延迟注解解析避免运行期提前求值跨模块类型。
from __future__ import annotations

# 标准库覆盖 CLI、哈希、JSON、路径、归档和进程能力。
import argparse
import hashlib
import json

# 正则、文件复制和子进程能力服务内容验证与治理命令执行。
import re
import shutil
import subprocess
import zipfile

# 时间、路径和通用类型构成共享函数的公共数据合同。
from datetime import datetime
from pathlib import Path
from typing import Any

# 共享治理合同由公共模块和目录治理模块提供。
from agents_common import (
    ensure_global_rule_overrides_file,
    GLOBAL_CODEX_AGENTS_PREAMBLE,
    GLOBAL_CODEX_AGENTS_META,
    GLOBAL_CODEX_AGENTS_BLOCK_END,
    GLOBAL_CODEX_AGENTS_BLOCK_START,

    # 治理身份和版本事实用于生成受管文档。
    governance_skill_name,
    RELEASE_CORE_WORKTREE_RULE,
    current_timestamp,
    display_path,
    emit_json,

    # 全局 AGENTS 状态与会话发现用于同步证据。
    global_codex_agents_path,
    global_codex_agents_status,
    matched_codex_sessions,
    parse_agents_metadata,
    preferred_skill_version,

    # 项目配置和脚本定位用于渲染可执行命令。
    project_profile,
    read_json,
    root_agents_sync_command,
    render_global_codex_agents_template,
    read_skill_version,

    # 路径解析与会话消息读取支撑命令编排。
    script_command,
    resolve_project,
    session_message_rows,
    global_codex_agents_sync_command,
    governance_script_path,
)
from manage_dirs import init_dir_manager, verify_dir_manager

# 文档治理初始化目录按换行顺序创建。
DOC_DIRS = """docs/handoff
docs/handoff/history_handoff
docs/development
docs/development/history_development
docs/install_configuration
docs/git_manager
docs/git_manager/history_git_manager
docs/dir_manager
docs/dir_manager/change_reviews
docs/dir_manager/history_dir_manager""".splitlines()

# 必需文档清单用于初始化和完整性验证。
REQUIRED_DOC_FILES = """docs/handoff/HANDOFF.md
docs/development/DEVELOPMENT.md
docs/install_configuration/INSTALL_CONFIGURATION.md
docs/git_manager/GIT_MANAGER.md
docs/git_manager/CHANGELOG.md""".splitlines()

# 文档头时间字段用于同步验证和自动更新。
LAST_UPDATED_HEADER_RE = re.compile(  # 文档更新时间头正则
    r"^<!--\s*Last updated:\s*(.*?)\s*\|\s*Last verified:\s*(.*?)\s*-->$",  # 时间字段表达式
    flags=re.MULTILINE,  # 跨行扫描文档头
)  # 用于识别受管文档的更新时间元数据

# 发布副本按敏感值类型使用稳定占位符。
SANITIZED_PLACEHOLDERS = {
    "api_key": "<REDACTED_API_KEY>",  # API 密钥占位符
    "password": "<REDACTED_PASSWORD>",  # 密码占位符
    "email": "<REDACTED_EMAIL>",  # 邮箱占位符
    "local_path": "<REDACTED_LOCAL_PATH>",  # 本地路径占位符
}  # 发布清理占位符映射

# Windows 和类 Unix 用户路径都属于发布副本的敏感信息。
LOCAL_PRIVATE_PATH_RE = re.compile(  # 本地用户路径正则
    r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|/(?:Users|home)/)[^\s\"'`<>\),\]}]+"  # 用户路径表达式
)

# 赋值清理规则保留变量名前缀，只替换敏感值部分。
SANITIZED_ASSIGNMENT_RULES = [
    (
        "api_key",  # API 密钥规则类型
        re.compile(  # API 密钥赋值正则
            r"(?m)^(\s*(?:[A-Z0-9]+_)*(?:API[_-]?KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET)"  # 凭据变量前缀
            r"(?:_[A-Z0-9]+)*\s*[:=]\s*)(.+?)\s*$"  # 凭据赋值内容
        ),
    ),
    (
        "password",  # 密码规则类型
        re.compile(  # 密码赋值正则
            r"(?m)^(\s*[A-Z0-9_]*PASSWORD[A-Z0-9_]*\s*[:=]\s*)(.+?)\s*$"  # 密码赋值内容
        ),
    ),
]  # 行级敏感赋值清理规则

# 行内规则清理不依赖变量名的邮箱和本地路径。
SANITIZED_INLINE_RULES = [
    (
        "email",  # 邮箱规则类型
        re.compile(  # 邮箱地址正则
            r"(?<!\\)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",  # 邮箱地址表达式
            flags=re.IGNORECASE,  # 邮箱域名匹配忽略大小写
        ),  # 用于发布文本中的邮箱定位
    ),
    ("local_path", LOCAL_PRIVATE_PATH_RE),  # 本地路径规则
]  # 行内敏感文本清理规则

# 二进制扫描仅检测高置信敏感特征，不执行内容替换。
SANITIZED_BINARY_PATTERNS = [
    ("api_key", re.compile(br"sk-(?:live|proj|test)-[A-Za-z0-9_-]+")),  # API 密钥字节特征
    ("password", re.compile(br"password", flags=re.IGNORECASE)),  # 密码关键词字节特征
    ("email", re.compile(br"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),  # 邮箱字节特征
]  # 二进制敏感特征规则

# 正则规则声明本身不能被误判为待清理凭据。
def should_skip_sanitized_assignment_value(value: str) -> bool:
    """判断赋值内容是否只是正则构造表达式。

    Args:
        value: 等号或冒号后的原始文本。

    Returns:
        内容以 re.compile 调用开头时为 True。
    """

    # 正则声明本身不应被凭据赋值清理器替换。
    return value.strip().startswith("re.compile(")

# 文档治理状态持久化在项目本地 .agents 目录。
STATE_PATH = ".agents/docs-governance-state.json"  # 文档治理状态路径

# 活动会话文件用于中断恢复和 handoff 一致性检查。
ACTIVE_SESSION_PATH = ".agents/active-session.json"  # 活动会话状态路径

# 活动会话是运行时状态，不应阻断 Git 发布门禁。
IGNORED_RUNTIME_GIT_PATHS = {ACTIVE_SESSION_PATH.replace("\\", "/")}  # Git 忽略的运行时路径

# 旧 experience 请求路径仅用于退役资产清理。
LEGACY_EXPERIENCE_REQUEST_PATH = ".agents/experience-update-request.json"  # 旧经验请求路径

# 旧 evolution 路径集合用于迁移后残留检测。
EVOLUTION_REQUEST_PATH = ".agents/evolution-update-request.json"  # 旧演化更新请求路径

# 导入请求保留仅用于识别旧演化工作流残留。
EVOLUTION_IMPORT_REQUEST_PATH = ".agents/evolution-import-request.json"  # 旧演化导入请求路径

# 导出目录保留仅用于清理旧演化批次产物。
EVOLUTION_EXPORT_ROOT = ".agents/evolution-export"  # 旧演化导出目录

# 审查请求保留仅用于识别旧演化审批残留。
EVOLUTION_REVIEW_REQUEST_PATH = ".agents/evolution-review-request.json"  # 旧演化审查请求路径

# 对话快照为会话证据提供稳定的项目内目录。
CONVERSATION_SNAPSHOT_DIR = ".agents/conversation-snapshots"  # 对话快照目录

# handoff 当前文件和历史目录名称构成固定目录合同。
HANDOFF_CURRENT_FILENAME = "HANDOFF.md"  # 当前 handoff 文件名

# 历史目录名与当前文件名共同限定 handoff 根目录结构。
HANDOFF_HISTORY_DIRNAME = "history_handoff"  # handoff 历史目录名

# 历史文件名允许同秒归档时附加数字后缀。
HANDOFF_HISTORY_RE = re.compile(r"^HANDOFF-\d{8}-\d{6}(?:-\d+)?\.md$")  # handoff 历史文件名正则

# 生成时间字段从 handoff 元数据列表中按完整行提取。
HANDOFF_GENERATED_AT_RE = re.compile(  # handoff 生成时间正则
    r"^- Generated at:\s*(.+?)\s*$",  # 生成时间字段表达式
    flags=re.MULTILINE,  # 在完整 handoff 文本中逐行查找
)  # 用于历史归档时间解析

# 标准章节同时用于模板生成和旧 handoff 结构识别。
HANDOFF_SECTIONS = [
    "Original Plan And Steps",  # 原始计划章节
    "Current Step",  # 当前步骤章节
    "Problems",  # 问题章节
    "Resolved Problems",  # 已解决问题章节
    "Remaining Problems",  # 剩余问题章节
    "Next Work",  # 后续工作章节
    "Verification Evidence",  # 验证证据章节
]  # handoff 标准章节

# 模板路径片段禁止分隔符和相对路径跳转。
SAFE_TEMPLATE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")  # 安全模板片段正则

# 退役状态键在保存时统一剔除，防止旧子系统重新出现。
LEGACY_EVOLUTION_STATE_KEYS = """last_experience_at
last_experience_payload
experience_update_required
experience_request_due_at
experience_request
experience_bootstrapped_from_sessions
last_evolution_at
last_evolution_target
last_evolution_summary
last_evolution_review_at
last_evolution_review_verdict
last_evolution_review_target
last_evolution_review_sources
last_evolution_sink
last_evolution_index""".splitlines()  # 退役 evolution 状态键

# 正式开发记录必须覆盖目标、过程、风险、结果和证据。
REQUIRED_DEVELOPMENT_SECTIONS = """Development Goal
Full Development Plan
Current Progress
Completed Scope
Remaining Scope
Key Problems And Risks
Resolution Strategy And Next Steps
Development Result
Verification
Artifacts And Impact""".splitlines()  # 开发记录必需章节

# 最小长度阻止只有标题的空壳记录通过治理验证。
DEVELOPMENT_MIN_LENGTH = 450  # 正式开发记录最小字符数

# 归档文件名使用本地秒级时间，保持历史目录可排序。
def stamp() -> str:
    """返回适合文件名的本地秒级时间戳。

    Args:
        无。

    Returns:
        YYYYMMDD-HHMMSS 格式时间文本。
    """

    # 固定数字格式避免文件系统不安全字符。
    return datetime.now().strftime("%Y%m%d-%H%M%S")

# 文档治理根目录固定在项目 docs 下。
def docs_root(project: Path) -> Path:
    """返回项目文档根目录。

    Args:
        project: 项目根目录。

    Returns:
        docs 目录路径。
    """

    # 路径构造不要求目录已经存在。
    return project / "docs"

# Git 治理材料集中在 docs/git_manager。
def git_manager_root(project: Path) -> Path:
    """返回项目 Git 治理目录。

    Args:
        project: 项目根目录。

    Returns:
        docs/git_manager 目录路径。
    """

    # 复用文档根合同，避免重复路径字面量。
    return docs_root(project) / "git_manager"

# CHANGELOG 是 Git 治理目录内的固定文件。
def git_changelog_file(project: Path) -> Path:
    """返回项目治理 CHANGELOG 路径。

    Args:
        project: 项目根目录。

    Returns:
        Git 治理 CHANGELOG 文件路径。
    """

    # 调用方负责决定读取或创建文件。
    return git_manager_root(project) / "CHANGELOG.md"

# Git 历史记录使用独立归档子目录。
def git_history_root(project: Path) -> Path:
    """返回 Git 治理历史归档目录。

    Args:
        project: 项目根目录。

    Returns:
        Git 历史归档目录路径。
    """

    # 路径与当前 Git 管理文档保持同一父目录。
    return git_manager_root(project) / "history_git_manager"

# docs 治理状态保存在项目本地 .agents 目录。
def state_file(project: Path) -> Path:
    """返回文档治理状态文件路径。

    Args:
        project: 项目根目录。

    Returns:
        docs-governance-state.json 路径。
    """

    # STATE_PATH 是仓库治理合同中的稳定相对位置。
    return project / STATE_PATH

# 活跃会话状态与持久 handoff 历史保持分离。
def active_session_file(project: Path) -> Path:
    """返回当前活跃治理会话文件路径。

    Args:
        project: 项目根目录。

    Returns:
        active-session.json 路径。
    """

    # 返回路径不创建会话文件。
    return project / ACTIVE_SESSION_PATH

# 演进更新请求存放在项目本地治理目录。
def evolution_request_file(project: Path) -> Path:
    """返回演进更新请求文件路径。

    Args:
        project: 项目根目录。

    Returns:
        演进更新请求路径。
    """

    # 请求位置由 EVOLUTION_REQUEST_PATH 集中定义。
    return project / EVOLUTION_REQUEST_PATH

# 外部演进结果通过独立导入请求进入项目。
def evolution_import_request_file(project: Path) -> Path:
    """返回演进导入请求文件路径。

    Args:
        project: 项目根目录。

    Returns:
        演进导入请求路径。
    """

    # 导入请求与普通更新请求使用不同 schema。
    return project / EVOLUTION_IMPORT_REQUEST_PATH

# 无可写 owner 时演进产物写入项目导出目录。
def evolution_export_root(project: Path) -> Path:
    """返回项目演进导出目录。

    Args:
        project: 项目根目录。

    Returns:
        演进导出目录路径。
    """

    # 目录路径仅描述落点，不在此处创建。
    return project / EVOLUTION_EXPORT_ROOT

# 演进审查请求与更新、导入请求独立存储。
def evolution_review_request_file(project: Path) -> Path:
    """返回演进审查请求文件路径。

    Args:
        project: 项目根目录。

    Returns:
        演进审查请求路径。
    """

    # 独立文件允许审查门禁单独追踪。
    return project / EVOLUTION_REVIEW_REQUEST_PATH

# 会话快照目录保存可审计的对话输入证据。
def conversation_snapshot_dir(project: Path) -> Path:
    """返回治理对话快照目录。

    Args:
        project: 项目根目录。

    Returns:
        对话快照目录路径。
    """

    # 快照目录位于项目本地 .agents 状态树。
    return project / CONVERSATION_SNAPSHOT_DIR

# 状态读取容忍缺失或非对象 JSON，并统一返回字典。
def load_state(project: Path) -> dict[str, Any]:
    """读取项目文档治理状态。

    Args:
        project: 项目根目录。

    Returns:
        状态字典；文件缺失或内容非对象时为空字典。
    """

    # 公共 JSON 读取器处理缺失和解析失败。
    dict_state = read_json(state_file(project))  # 文档治理状态

    # schema 顶层必须是对象，其他类型不向调用方传播。
    return dict_state if isinstance(dict_state, dict) else {}

# 状态写入创建 .agents 目录并使用稳定排序 JSON。
def save_state(project: Path, state: dict[str, Any]) -> None:
    """原子边界内写入文档治理状态。

    Args:
        project: 项目根目录。
        state: 待持久化的状态字典。

    Returns:
        无。

    Shape:
        state 是键值对象，不使用数组维度。

    Dtype:
        状态字段由 JSON 可序列化 Python 类型构成。

    Unit:
        状态值无统一物理单位，各字段按治理 schema 解释。
    """

    # 状态父目录在首次治理时可能尚未创建。
    path_agents_dir = project / ".agents"  # 项目本地治理目录

    # 项目根已存在，当前层只需创建 .agents。
    path_agents_dir.mkdir(exist_ok=True)

    # 稳定排序和缩进便于 diff、审计与人工恢复。
    state_file(project).write_text(json.dumps(state, indent=2, sort_keys=True, default=str), encoding="utf-8")

# 历史演进目录覆盖根资产、档案指定 skill 和 skills 子目录。
def legacy_evolution_roots(project: Path) -> list[Path]:
    """列出项目中可能残留的旧演进模板目录。

    Args:
        project: 项目根目录。

    Returns:
        去重且保持发现顺序的候选目录。
    """

    # 根资产目录是旧版默认演进落点。
    list_roots = [project / "assets" / "templates" / "evolution"]  # 演进目录候选

    # 控制档案可能声明实际 skill 子根。
    dict_profile = project_profile(project)  # 项目治理档案

    # 仅结构化 skill_layout 可以提供路径。
    if isinstance(dict_profile, dict):

        # 非字典布局按未配置处理。
        dict_layout = (  # skill 布局合同
            dict_profile.get("skill_layout")  # 原始 skill 布局值
            if isinstance(dict_profile.get("skill_layout"), dict)  # 仅接受对象布局
            else {}  # 非对象配置回退为空布局
        )  # 标准 skills 子目录的演进模板候选

        # 空路径不形成额外候选。
        str_raw_path = str(dict_layout.get("path") or "").strip()  # skill 相对路径

        # 档案指定路径存在时追加其资产目录。
        if str_raw_path:

            # 候选存在性在清理阶段判断。
            list_roots.append(project / str_raw_path / "assets" / "templates" / "evolution")

    # 标准 skills 目录可能含多个历史 skill 根。
    path_skills_root = project / "skills"  # 标准 skills 根目录

    # 只扫描真实目录，避免不存在根触发异常。
    if path_skills_root.is_dir():

        # 每个 skill 子目录映射到其演进资产位置。
        list_roots.extend(
            path_skill / "assets" / "templates" / "evolution"
            for path_skill in path_skills_root.iterdir()
            if path_skill.is_dir()
        )  # 从治理档案提取的 skill 布局对象

    # 去重列表保留最先发现的路径表达。
    list_deduped: list[Path] = []  # 去重演进目录

    # 路径键集合避免同一目录由多条发现路径重复清理。
    set_seen: set[str] = set()  # 已见规范路径

    # 候选按发现顺序规范化并去重。
    for path_root in list_roots:

        # 已存在路径使用解析后绝对值，未存在路径保留词法表达。
        str_normalized = str(path_root.resolve()) if path_root.exists() else str(path_root)  # 路径去重键

        # 首次出现的目录进入返回列表。
        if str_normalized not in set_seen:

            # 先登记键再追加路径，保持集合与列表同步。
            set_seen.add(str_normalized)

            # 原始 Path 表达供后续展示和删除使用。
            list_deduped.append(path_root)

    # 返回有序去重结果。
    return list_deduped

# 旧演进请求、导出目录、模板目录和状态键按统一事务清理。
def cleanup_legacy_evolution_artifacts(
    project: Path,
    state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """清理已退役的演进文件、目录和状态字段。

    Args:
        project: 项目根目录。
        state: 可选的可变文档治理状态。

    Returns:
        删除文件、目录、状态键和变化标志报告。

    Shape:
        输入为单个项目路径和可选状态对象，输出为固定字段报告对象。

    Dtype:
        路径为 Path，状态和返回报告为 dict[str, Any]。

    Unit:
        文件、目录和状态键均按条目计数，无物理单位。
    """

    # 删除报告使用项目相对展示路径。
    list_removed_files: list[str] = []  # 已删除请求文件

    # 目录删除结果与文件结果分开记录。
    list_removed_dirs: list[str] = []  # 已删除演进目录

    # 四类旧请求文件均可安全直接删除。
    tuple_request_paths = (  # 四类旧演进请求路径
        project / LEGACY_EXPERIENCE_REQUEST_PATH,  # 旧 experience 请求文件
        evolution_request_file(project),  # 旧 evolution 更新请求文件
        evolution_review_request_file(project),  # 旧 evolution 审查请求文件
        evolution_import_request_file(project),  # 旧 evolution 导入请求文件
    )  # 待删除的退役请求文件集合

    # 仅删除实际存在的请求文件。
    for path_request in tuple_request_paths:

        # 缺失请求无需写入报告。
        if path_request.exists():

            # 请求文件不再参与当前演进流程。
            path_request.unlink()

            # 报告使用可移植项目相对路径。
            list_removed_files.append(display_path(path_request, project))

    # 项目导出目录可能包含整批待导入产物。
    path_export_root = evolution_export_root(project)  # 演进导出目录

    # 目录存在时递归清除退役产物。
    if path_export_root.exists():

        # ignore_errors 保持清理操作幂等。
        shutil.rmtree(path_export_root, ignore_errors=True)

        # 记录已处理的导出目录。
        list_removed_dirs.append(display_path(path_export_root, project))

    # 每个旧模板目录独立判断并清理。
    for path_root in legacy_evolution_roots(project):

        # 不存在目录不进入变化报告。
        if path_root.exists():

            # 历史模板树整体退役，不保留部分内容。
            shutil.rmtree(path_root, ignore_errors=True)

            # 记录项目内或绝对展示路径。
            list_removed_dirs.append(display_path(path_root, project))

    # 状态键清理结果按配置顺序记录。
    list_cleaned_keys: list[str] = []  # 已移除旧状态键

    # 未传状态时只执行文件系统清理。
    if isinstance(state, dict):

        # 白名单之外的状态字段必须保留。
        for str_key in LEGACY_EVOLUTION_STATE_KEYS:

            # 仅记录清理前真实存在的字段。
            if str_key in state:

                # pop 使用默认值保证并发式重复清理可恢复。
                state.pop(str_key, None)

                # 报告保留字段清理顺序。
                list_cleaned_keys.append(str_key)

    # changed 聚合三类清理结果。
    return {
        "removed_files": list_removed_files,
        "removed_dirs": list_removed_dirs,
        "cleaned_state_keys": list_cleaned_keys,
        "changed": bool(list_removed_files or list_removed_dirs or list_cleaned_keys),
    }

# 文件哈希只对真实普通文件产生证据。
def file_hash(path: Path) -> str:
    """计算文件 SHA-256 哈希。

    Args:
        path: 待哈希路径。

    Returns:
        十六进制哈希；文件不可用时为空字符串。
    """

    # 目录和缺失路径不构成文件内容证据。
    if not path.exists() or not path.is_file():

        # 空值由调用方识别为无哈希证据。
        return ""

    # 一次性读取文件字节并计算稳定摘要。
    return hashlib.sha256(path.read_bytes()).hexdigest()

# Handoff 列表字段统一渲染为 Markdown 项目符号。
def list_lines(list_values: Any) -> str:
    """把可选标量或列表渲染为 Markdown 列表。

    Args:
        list_values: 待渲染值。

    Returns:
        项目符号文本；无有效值时返回缺省占位项。
    """

    # None 和空字符串都表示未记录。
    if list_values is None or list_values == "":

        # 占位文本保持 handoff 结构完整。
        return "- Not recorded."

    # 单个字符串作为一个列表项处理。
    if isinstance(list_values, str):

        # 新列表避免后续迭代字符串字符。
        list_normalized_values = [list_values]  # 规范化列表值

    # 列表输入可以直接进入内容清理阶段。
    elif isinstance(list_values, list):

        # 浅拷贝避免后续逻辑意外修改调用方列表。
        list_normalized_values = list_values.copy()  # 调用方列表的独立副本

    # 其他标量转换为单项字符串列表。
    else:

        # 保持调用方传入对象的公开字符串表达。
        list_normalized_values = [str(list_values)]  # 标量转换后的单项列表

    # 空白项不进入最终 Markdown。
    list_lines_clean = [  # 去除空白后的 Markdown 列表文本
        str(item).strip()  # 单个列表项的规范文本
        for item in list_normalized_values  # 遍历规范化输入项
        if str(item).strip()  # 丢弃空白列表项
    ]  # 有效列表文本

    # 列表经过清理后可能变为空。
    if not list_lines_clean:

        # 空列表使用与缺失值相同的占位合同。
        return "- Not recorded."

    # 每项添加一个 Markdown 短横线前缀。
    return "\n".join(f"- {str_line}" for str_line in list_lines_clean)

# 阶段名压缩为文件名安全的 ASCII slug。
def slug(value: str) -> str:
    """生成文件名安全的阶段标识。

    Args:
        value: 原始阶段名称。

    Returns:
        小写 slug；无有效字符时为 stage。
    """

    # 非白名单字符折叠为单个短横线边界。
    str_cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")  # 安全阶段标识

    # 空结果使用稳定回退名称。
    return str_cleaned or "stage"

# 默认 handoff 为尚无任务事实的项目提供完整章节骨架。
def default_handoff() -> str:
    """生成尚未记录任务信息时的 handoff 模板。

    Args:
        无。

    Returns:
        包含全部标准章节的 Markdown 文本。
    """

    # 固定模板确保首次初始化结果可重复。
    return """# Handoff

> Latest task handoff. Archive this file before writing the next handoff.

## Original Plan And Steps
- Not recorded yet.

## Current Step
- Not recorded yet.

## Problems
- Not recorded yet.

## Resolved Problems
- Not recorded yet.

## Remaining Problems
- Not recorded yet.

## Next Work
- Not recorded yet.

## Verification Evidence
- Not recorded yet.
"""

# 控制档案读取失败时使用空对象保持文档命令可诊断。
def control_profile(project: Path) -> dict[str, Any]:
    """读取项目的治理控制配置。

    Args:
        project: 项目根目录。

    Returns:
        可用的控制配置；文件内容不是对象时返回空字典。
    """

    # JSON 读取器负责缺失文件和解析错误的兼容处理。
    dict_data = read_json(project / ".agents" / "agents-control.json")  # 控制档案内容

    # 非对象 JSON 不能作为键值治理配置消费。
    return dict_data if isinstance(dict_data, dict) else {}

# 节奏检查点向下对齐到最近的完整间隔。
def cadence_checkpoint(count: int, interval: int) -> int:
    """计算不超过当前计数的最近节奏检查点。

    Args:
        count: 当前累计次数。
        interval: 检查间隔。

    Returns:
        最近检查点；输入非正数时返回零。
    """

    # 非正数不能形成有效检查窗口。
    if count <= 0 or interval <= 0:

        # 零值明确表示尚无可执行检查点。
        return 0

    # 整数除法保持检查点不超过当前计数。
    return (count // interval) * interval

# 节奏窗口以检查点为闭区间结束位置。
def cadence_window_bounds(checkpoint: int, interval: int) -> tuple[int, int]:
    """计算检查点对应的闭区间窗口。

    Args:
        checkpoint: 窗口结束检查点。
        interval: 窗口包含的最大条目数。

    Returns:
        起止计数；无有效检查点时两者均为零。
    """

    # 零检查点表示尚未形成任何窗口。
    if checkpoint <= 0:

        # 无效检查点不形成部分窗口。
        return 0, 0

    # 起点下限为一，避免产生零或负计数。
    return max(1, checkpoint - interval + 1), checkpoint

# Handoff 累计次数字段使用稳定的列表项格式。
def handoff_count_from_markdown(text: str) -> int:
    """从 handoff Markdown 中读取累计交接次数。

    Args:
        text: handoff Markdown 文本。

    Returns:
        已记录的交接次数；缺少字段时返回零。
    """

    # 完整行匹配避免从正文示例中误读计数。
    match_count = re.search(  # handoff 计数字段匹配
        r"^- Handoff count:\s*(\d+)\s*$",  # 累计次数列表项表达式
        text,  # 待解析的完整 handoff 文本
        flags=re.MULTILINE,  # 在完整 handoff 中逐行匹配
    )  # 用于提取累计归档次数

    # 缺失字段兼容尚未写入计数的旧 handoff。
    return int(match_count.group(1)) if match_count else 0

# Handoff 路径由一个根目录、活动文件和历史目录组成。
def handoff_paths(project: Path) -> dict[str, Path]:
    """构造项目 handoff 当前文件与历史目录路径。

    Args:
        project: 项目根目录。

    Returns:
        handoff 根目录、当前文件和历史目录路径映射。
    """

    # 根路径只构造不创建，调用方决定是否执行写操作。
    path_handoff_root = project / "docs" / "handoff"  # 当前与历史 handoff 的共同父目录

    # 稳定键名由审计、归档和恢复流程共同消费。
    return {
        "root": path_handoff_root,
        "current": path_handoff_root / HANDOFF_CURRENT_FILENAME,
        "history": path_handoff_root / HANDOFF_HISTORY_DIRNAME,
    }

# 任一治理资产存在即表示项目不能按全新目录重新初始化。
def docs_governance_initialized(project: Path) -> bool:
    """判断项目是否已经存在文档治理资产。

    Args:
        project: 项目根目录。

    Returns:
        任一治理目录、必需文件或状态文件存在时为真。
    """

    # 任一治理资产存在即视为已初始化，避免覆盖部分已有结构。
    for rel_path in [*DOC_DIRS, *REQUIRED_DOC_FILES, STATE_PATH]:

        # 任一命中都足以保护已有的部分治理结构。
        if (project / rel_path).exists():

            # 提前返回避免无意义地扫描剩余固定路径。
            return True

    # 所有治理路径均缺失时可安全执行首次初始化。
    return False

# Handoff 历史文件名编码秒级生成时间和可选冲突序号。
def handoff_history_filename_for_timestamp(moment: datetime, suffix: int | None = None) -> str:
    """按时间戳生成规范的 handoff 历史文件名。

    Args:
        moment: handoff 生成时间。
        suffix: 同秒冲突时使用的正整数后缀。

    Returns:
        规范的 Markdown 历史文件名。
    """

    # 数字格式保证文件名可排序且跨平台安全。
    str_stamp_value = moment.strftime("%Y%m%d-%H%M%S")  # 历史文件名的排序时间字段

    # 基础名称在添加扩展名或冲突后缀前保持复用。
    str_base = f"HANDOFF-{str_stamp_value}"  # handoff 历史基础名称

    # 首次归档无后缀，同秒冲突时追加数字后缀。
    return f"{str_base}-{suffix}.md" if suffix is not None else f"{str_base}.md"

# 历史路径选择不得覆盖同秒内已经存在的归档。
def unique_handoff_history_path(history_dir: Path, moment: datetime) -> Path:
    """选择不会覆盖既有 handoff 的历史文件路径。

    Args:
        history_dir: handoff 历史目录。
        moment: handoff 生成时间。

    Returns:
        当前不存在的历史文件路径。
    """

    # 优先尝试不带冲突后缀的规范路径。
    path_target = history_dir / handoff_history_filename_for_timestamp(moment)  # 首个无后缀归档候选

    # 冲突序号从一开始并按存在性递增。
    int_suffix = 1  # 下一个归档冲突后缀

    # 同一秒内重复归档时递增后缀，保留每份历史记录。
    while path_target.exists():

        # 当前序号生成新的候选归档路径。
        path_target = history_dir / handoff_history_filename_for_timestamp(  # 冲突后的归档候选
            moment,  # 原始 handoff 生成时间
            suffix=int_suffix,  # 当前可用性探测的数字后缀
        )  # 使用当前数字后缀生成的新路径

        # 下一轮冲突检查使用后续序号。
        int_suffix += 1  # 下一次冲突检测使用的序号

    # 返回首个尚未占用的规范路径。
    return path_target

# 生成时间解析兼容 ISO 8601 的 Z 时区后缀。
def parse_handoff_generated_at(text: str) -> datetime | None:
    """解析 handoff 元数据中的生成时间。

    Args:
        text: handoff Markdown 文本。

    Returns:
        可解析的时区感知或朴素时间；缺失或格式无效时为 None。
    """

    # 正则只读取元数据列表中的生成时间字段。
    match_generated_at = HANDOFF_GENERATED_AT_RE.search(text)  # 生成时间字段匹配

    # 旧 handoff 可能没有生成时间字段。
    if not match_generated_at:

        # 缺失字段由调用方回退到文件时间或当前时间。
        return None

    # 去除字段两端空白后再交给 ISO 解析器。
    str_raw = match_generated_at.group(1).strip()  # 原始生成时间文本

    # 无效历史文本不得中断归档命名审计。
    try:

        # Python 解析器使用显式 UTC 偏移代替 Z。
        return datetime.fromisoformat(str_raw.replace("Z", "+00:00"))

    # 格式错误按不可用时间处理，保留恢复流程。
    except ValueError:

        # None 明确区分无效时间与有效时间对象。
        return None

# Handoff 结构识别要求标准标题和足够多的已知章节。
def looks_like_handoff_markdown(text: str) -> bool:
    """判断 Markdown 是否具备 handoff 文档的基本结构。

    Args:
        text: 待检查的 Markdown 文本。

    Returns:
        标题存在且至少半数标准章节存在时为真。
    """

    # 标题是识别 handoff 文档的必要条件。
    if "# Handoff" not in text:

        # 无标准标题的文档不能作为 handoff 迁移候选。
        return False

    # 章节阈值允许兼容早期模板，同时排除普通 Markdown 文档。
    int_present_sections = sum(  # handoff 已识别标准章节数
        1  # 每个已识别章节贡献一个计数
        for section in HANDOFF_SECTIONS  # 遍历标准章节标题
        if f"## {section}" in text  # 只统计实际出现的标准标题
    )  # 用于结构可信度阈值判断的章节总数

    # 至少三个且不少于半数章节才能形成足够强的结构证据。
    return int_present_sections >= max(3, len(HANDOFF_SECTIONS) // 2)

# 当前 handoff 目录只允许一个活动文件和一个历史子目录。
def audit_current_handoff_entries(
    project: Path,
    handoff_root: Path,
) -> tuple[list[str], list[str]]:
    """审计 handoff 根目录中的活动文件命名。

    Args:
        project: 项目根目录。
        handoff_root: handoff 文档根目录。

    Returns:
        命名错误与额外 Markdown 候选文件列表。
    """

    # 分别保留阻断错误和可能迁移的旧活动文件。
    list_errors: list[str] = []  # 活动目录命名错误

    # 额外 Markdown 单独记录，供迁移建议使用。
    list_candidates: list[str] = []  # 非规范 Markdown 候选文件

    # 尚未创建 handoff 目录时无需检查目录内容。
    if not handoff_root.is_dir():

        # 返回独立列表，供总审计直接合并。
        return list_errors, list_candidates

    # 按稳定顺序检查目录中的每个直接子项。
    for child in sorted(handoff_root.iterdir()):

        # 相对路径用于生成可移植的治理诊断。
        rel_path = child.relative_to(project).as_posix()  # 项目相对路径

        # 规范活动 handoff 必须是普通文件。
        if child.name == HANDOFF_CURRENT_FILENAME:

            # 同名目录会阻断 handoff 更新。
            if not child.is_file():

                # 当前路径类型错误需要精确定位。
                list_errors.append(
                    f"handoff naming drift: current handoff path must be a file: {rel_path}"
                )

            # 当前文件已经完成类型检查，不再进入额外项判断。
            continue

        # 规范历史位置必须是目录。
        if child.name == HANDOFF_HISTORY_DIRNAME:

            # 同名文件会阻断历史归档。
            if not child.is_dir():

                # 历史路径类型错误需要精确定位。
                list_errors.append(
                    f"handoff naming drift: history handoff path must be a directory: {rel_path}"
                )

            # 历史目录已经完成类型检查，不再进入额外项判断。
            continue

        # 额外 Markdown 可能是旧命名的活动 handoff。
        if child.is_file() and child.suffix.lower() == ".md":

            # 单独返回候选文件，支持后续迁移提示。
            list_candidates.append(rel_path)

            # 任一额外 Markdown 都违反唯一活动文件约束。
            list_errors.append(
                "handoff naming drift: current handoff must be exactly "
                f"docs/handoff/{HANDOFF_CURRENT_FILENAME}; found {rel_path}"
            )

        # 非 Markdown 子项同样不属于允许结构。
        else:

            # 诊断同时列出允许的两个目录项。
            list_errors.append(
                "handoff naming drift: docs/handoff only allows "
                f"{HANDOFF_CURRENT_FILENAME} and {HANDOFF_HISTORY_DIRNAME}/; found {rel_path}"
            )

    # 将活动目录审计结果交给总审计编排器。
    return list_errors, list_candidates

# 历史目录只允许符合时间戳约定的 Markdown 归档。
def audit_handoff_history_entries(
    project: Path,
    history_dir: Path,
) -> tuple[list[str], list[str], list[str]]:
    """审计 handoff 历史目录中的归档文件命名。

    Args:
        project: 项目根目录。
        history_dir: handoff 历史归档目录。

    Returns:
        命名错误、已检查路径和无效 Markdown 路径列表。
    """

    # 三类结果分别服务阻断、证据和迁移诊断。
    list_errors: list[str] = []  # 历史目录命名错误

    # 检查证据覆盖历史目录中的每个直接条目。
    list_checked: list[str] = []  # 实际检查的历史路径

    # 格式无效的 Markdown 保留为潜在重命名对象。
    list_invalid_markdown: list[str] = []  # 不符合归档正则的 Markdown

    # 历史目录不存在时不产生内容级错误。
    if not history_dir.is_dir():

        # 返回空结果，由结构治理负责目录缺失问题。
        return list_errors, list_checked, list_invalid_markdown

    # 按稳定顺序审计每个历史归档条目。
    for child in sorted(history_dir.iterdir()):

        # 相对路径同时用于证据和错误消息。
        rel_path = child.relative_to(project).as_posix()  # 项目相对历史路径

        # 所有遍历到的条目都进入审计证据。
        list_checked.append(rel_path)

        # 历史目录禁止嵌套目录和特殊文件。
        if not child.is_file():

            # 非文件条目无法作为 handoff 归档读取。
            list_errors.append(
                "handoff naming drift: history_handoff only allows archived "
                f"markdown files; found {rel_path}"
            )

            # 文件类型不成立时跳过后续扩展名和命名检查。
            continue

        # handoff 历史归档统一使用 Markdown 扩展名。
        if child.suffix.lower() != ".md":

            # 非 Markdown 文件不加入可迁移候选列表。
            list_errors.append(
                f"handoff naming drift: history handoff archive must be markdown: {rel_path}"
            )

            # 扩展名不成立时无需匹配归档正则。
            continue

        # Markdown 文件名必须包含规范时间戳和可选冲突后缀。
        if not HANDOFF_HISTORY_RE.fullmatch(child.name):

            # 单独记录无效 Markdown，支持调用方生成修复建议。
            list_invalid_markdown.append(rel_path)

            # 诊断明确给出两种合法命名形式。
            list_errors.append(
                "handoff naming drift: history handoff archive must match "
                "HANDOFF-YYYYMMDD-HHMMSS.md or HANDOFF-YYYYMMDD-HHMMSS-N.md; "
                f"found {rel_path}"
            )

    # 将历史目录审计结果交给总审计编排器。
    return list_errors, list_checked, list_invalid_markdown

# 汇总活动文件和历史归档的 handoff 命名证据。
def audit_handoff_naming(project: Path) -> dict[str, Any]:
    """审计项目 handoff 目录的完整命名合同。

    Args:
        project: 项目根目录。

    Returns:
        包含阻断状态、错误和检查路径的审计报告。
    """

    # 统一路径构造避免审计层重复拼接目录名称。
    dict_paths = handoff_paths(project)  # handoff 标准路径映射

    # 活动目录审计返回错误和潜在迁移候选。
    tuple_current_audit = audit_current_handoff_entries(  # 活动 handoff 审计结果
        project,  # 活动目录所属项目根
        dict_paths["root"],  # 活动 handoff 所在目录
    )  # 包含活动错误和迁移候选的二元组

    # 解包后的列表继续用于汇总报告字段。
    list_current_errors = tuple_current_audit[0]  # 当前文件及目录类型错误

    # 第二项保留可能迁移为 HANDOFF.md 的旧文件。
    list_candidates = tuple_current_audit[1]  # 旧活动 Markdown 候选

    # 历史目录审计额外返回逐项检查证据。
    tuple_history_audit = audit_handoff_history_entries(  # 历史 handoff 审计结果
        project,  # 历史目录所属项目根
        dict_paths["history"],  # handoff 历史归档目录
    )  # 包含错误、检查证据和无效归档的三元组

    # 历史结果按错误、证据和无效 Markdown 三类展开。
    list_history_errors = tuple_history_audit[0]  # 历史归档类型与命名错误

    # 第二项提供审计实际覆盖的历史路径。
    list_history_checked = tuple_history_audit[1]  # 已检查历史路径

    # 第三项保留需要规范化命名的 Markdown。
    list_invalid_history = tuple_history_audit[2]  # 无效历史 Markdown

    # 汇总两处目录的全部阻断错误。
    list_errors = [*list_current_errors, *list_history_errors]  # 完整命名错误

    # 标准路径始终列入检查范围，历史文件随后追加。
    list_checked = [  # verify 输出 checked 值，列出 handoff 三个入口和已遍历归档
        "docs/handoff",  # 文档治理 handoff 根目录入口
        "docs/handoff/HANDOFF.md",  # 当前任务交接文件固定入口
        "docs/handoff/history_handoff",  # 历史任务交接归档目录入口
        *list_history_checked,  # 逐项遍历确认存在的历史归档文件
    ]  # 审计报告用于证明命名检查范围的路径集合

    # 返回稳定字段，供 verify 和 resume 流程共同消费。
    return {
        "project": str(project),
        "ok": not list_errors,
        "blocking": bool(list_errors),
        "checked": list_checked,
        "errors": list_errors,
        "current_markdown_candidates": list_candidates,
        "invalid_history_markdown": list_invalid_history,
    }

# 读取当前 handoff 及其累计次数，供 memory 和恢复流程复用。
def current_handoff_entry(project: Path) -> dict[str, Any] | None:
    """读取当前 handoff 的路径、内容和累计次数。

    Args:
        project: 项目根目录。

    Returns:
        当前 handoff 条目；文件不存在时为 None。
    """

    # 当前文件路径来自统一 handoff 路径合同。
    path = handoff_paths(project)["current"]  # 当前 handoff 文件路径

    # 缺失或类型错误的路径不能作为当前 handoff。
    if not path.is_file():

        # 明确返回空值，避免调用方读取无效路径。
        return None

    # 容忍历史文件中的无效字节以维持恢复能力。
    str_content = path.read_text(encoding="utf-8", errors="ignore")  # 当前 handoff 文本

    # 返回 memory 摘要所需的最小稳定字段。
    return {
        "path": path.relative_to(project).as_posix(),
        "content": str_content,
        "handoff_count": handoff_count_from_markdown(str_content),
    }

# 安装配置模板记录版本化安装和适配器边界。
def install_configuration_doc() -> str:
    """生成技能安装与适配器配置说明。

    Args:
        无。

    Returns:
        安装配置 Markdown 文本。
    """

    # 相邻字面量维持长说明的单行 Markdown 输出。
    return (
        "# Install Configuration\n\n"
        "## Skill Install Path\n"
        "- Install the skill folder into the target agent skill directory before use.\n"
        "- When replacing an installed skill, first move the old skill to the sibling "
        "`skill_backups/<skill-name>-YYYYMMDD-HHMMSS/` folder.\n"
        "- `v1.0.0` and later do not support evolution templates; replacement installs "
        "should remove any legacy `assets/templates/evolution/` content from the destination skill.\n"
        "- `v1.1.0` and later do not support the experience subsystem; memory under "
        "`docs/memory/` is the long-term project context mechanism.\n\n"
        "## Codex Adapter\n"
        "- Keep `SKILL.md`, `agents/openai.yaml`, `references/`, `scripts/`, and `assets/` together.\n\n"
        "## Claude Adapter\n"
        "- Use `CLAUDE.md` compatibility shims only when requested; preserve existing "
        "non-managed files.\n\n"
        "## OpenClaw Adapter\n"
        "- Treat OpenClaw as an external adapter target and record project-specific setup "
        "here when confirmed.\n\n"
        "## Compatibility Shims\n"
        "- Create shims with the bundled compatibility script after AGENTS.md generation "
        "when requested.\n"
    )

# 默认变更日志为尚未写入发布事实的新仓库提供占位结构。
def default_git_changelog() -> str:
    """生成尚未填写的 Git 变更日志模板。

    Args:
        无。

    Returns:
        Git 变更日志 Markdown 文本。
    """

    # 固定模板保持首次初始化结果可重复。
    return """# Change Log

- Version: not recorded
- Generated at: not recorded
- Summary: not recorded

## Changes
- Record the staged or committed changes for this release or commit here before the next commit.

## Verification
- Record the exact validation commands or evidence used for this change set.
"""

# 开发记录模板使用当前时间区分每次初始化事件。
def default_development_record() -> str:
    """生成带当前时间的默认开发阶段记录。

    Args:
        无。

    Returns:
        开发阶段记录 Markdown 文本。
    """

    # 秒级时间满足文档证据精度且避免微秒噪声。
    str_generated_at = datetime.now().isoformat(timespec="seconds")  # 开发记录生成时间

    # 固定章节与验证器的必需章节合同保持一致。
    return f"""# Development Stage: not recorded

- Generated at: {str_generated_at}
- Version: not recorded
- Status: not recorded

## Development Goal
- Not recorded.

## Full Development Plan
- Not recorded.

## Current Progress
- Not recorded.

## Completed Scope
- Not recorded.

## Remaining Scope
- Not recorded.

## Key Problems And Risks
- Not recorded.

## Resolution Strategy And Next Steps
- Not recorded.

## Development Result
- Not recorded.

## Verification
- Not recorded.

## Artifacts And Impact
- Not recorded.
"""

# 开发记录验证区分未启用占位模板和已开始维护的正式记录。
def validate_development_record(path: Path) -> list[str]:
    """检查开发记录的章节、状态和最小内容长度。

    Args:
        path: 待验证的开发记录路径。

    Returns:
        可操作的验证错误列表。
    """

    # 错误按发现顺序返回，便于稳定测试和逐项修复。
    list_errors: list[str] = []  # 开发记录验证错误

    # 忽略无效字节，确保治理命令仍能报告结构问题。
    text = path.read_text(encoding="utf-8", errors="ignore")  # 开发记录文本

    # 所有诊断共用稳定的项目相对文档路径。
    str_relative_path = path.relative_to(path.parents[2]).as_posix()  # 开发记录相对路径

    # 项目尚未开始维护记录时，完整默认模板是允许状态。
    if (
        "# Development Stage: not recorded" in text
        and "- Version: not recorded" in text
        and "- Status: not recorded" in text
    ):

        # 默认模板没有进一步的内容完整性义务。
        return list_errors

    # 正式记录必须包含每个治理必需章节。
    for section in REQUIRED_DEVELOPMENT_SECTIONS:

        # 章节标题按完整行匹配，避免正文提及造成误判。
        if not re.search(rf"^##\s+{re.escape(section)}\s*$", text, flags=re.MULTILINE):

            # 诊断指出精确缺失的标准章节。
            list_errors.append(f"{str_relative_path}: missing section ## {section}")

    # 已开始维护的记录不得保留状态占位符。
    if "- Status: not recorded" in text:

        # 阻止未明确阶段状态的记录进入交付证据。
        list_errors.append(f"{str_relative_path}: development status is still placeholder text")

    # 过短记录无法承载必需的开发事实。
    if len(text.strip()) < DEVELOPMENT_MIN_LENGTH:

        # 提醒维护者补充开发结果而非仅保留标题。
        list_errors.append(f"{str_relative_path}: development record is too short")

    # 返回全部错误，允许调用方一次性呈现完整修复清单。
    return list_errors

# Git Manager 命令构造器选择仓库运行时或安装态占位路径。
def git_manager_commands(
    project: Path | None = None,
    profile: dict[str, Any] | None = None,
) -> dict[str, str]:
    """生成发布准备、门禁、打包和变更日志命令。

    Args:
        project: 可选的项目根目录，用于解析仓库内脚本路径。
        profile: 可选的脚本命令治理配置。

    Returns:
        按用途命名的四条 Git Manager 命令。
    """

    # 有项目上下文时生成当前仓库可直接执行的命令。
    if project is not None:

        # 发布准备命令负责提交、合并和分支清理。
        str_release_prepare_command = script_command(  # 当前项目发布准备命令
            project,  # release-prepare 命令项目上下文
            "manage_docs.py",  # 发布准备脚本名
            "release-prepare",  # 发布准备子命令
            "<project>",  # 发布准备项目占位参数
            "--version",  # 发布准备版本参数名
            "vX.Y.Z",  # 发布准备版本占位值
            "--skill-dir",  # 发布准备技能目录参数名
            "skills/<skill-name>",  # 发布准备技能目录占位值
            profile=profile,  # 发布准备命令治理配置
        )  # 仓库内 release-prepare 调用文本

        # 发布门禁命令同时覆盖打包前和打包后阶段。
        str_release_gate_command = script_command(  # 当前项目发布门禁命令
            project,  # 门禁执行所用的仓库根目录
            "manage_docs.py",  # 发布门禁脚本名
            "release-gate",  # 发布门禁子命令
            "<project>",  # 发布门禁项目占位参数
            "--version",  # 发布门禁版本参数名
            "vX.Y.Z",  # 发布门禁版本占位值
            "--skill-dir",  # 发布门禁技能目录参数名
            "skills/<skill-name>",  # 发布门禁技能目录占位值
            "--phase",  # 发布门禁阶段参数名
            "pre|post",  # 打包前后阶段占位值
            profile=profile,  # 发布门禁命令治理配置
        )  # 包含版本、技能目录和阶段参数的门禁命令

        # 打包命令生成版本目录、压缩包和发布收据。
        str_package_release_command = script_command(  # 当前项目发布打包命令
            project,  # 打包产物来源的仓库根目录
            "manage_docs.py",  # 发布打包脚本名
            "package-release",  # 发布打包子命令
            "<project>",  # 发布打包项目占位参数
            "--version",  # 发布打包版本参数名
            "vX.Y.Z",  # 发布打包版本占位值
            "--skill-dir",  # 发布打包技能目录参数名
            "skills/<skill-name>",  # 发布打包技能目录占位值
            profile=profile,  # 发布打包命令治理配置
        )  # 生成版本目录和收据的打包命令

        # 变更日志命令负责归档旧记录并写入当前条目。
        str_changelog_command = script_command(  # 当前项目变更日志命令
            project,  # 变更日志归档所属的仓库根目录
            "manage_docs.py",  # 变更日志脚本名
            "git-changelog",  # 变更日志子命令
            "<project>",  # 变更日志项目占位参数
            "--input",  # 变更日志输入参数名
            "changelog.json",  # 变更日志输入文件示例
            profile=profile,  # 变更日志命令治理配置
        )  # 归档并写入当前变更记录的命令

    # 无项目上下文时使用安装技能位置的可移植模板。
    else:

        # 通用发布准备命令保留项目和版本占位符。
        str_release_prepare_command = (  # 通用发布准备命令
            "python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py "
            "release-prepare <project> --version vX.Y.Z --skill-dir skills/<skill-name>"
        )  # 安装技能路径的 release-prepare 示例

        # 通用门禁命令保留 pre 和 post 阶段选项。
        str_release_gate_command = (  # 通用发布门禁命令
            "python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py "
            "release-gate <project> --version vX.Y.Z --skill-dir "
            "skills/<skill-name> --phase pre|post"
        )  # 无仓库上下文时的两阶段门禁示例

        # 通用打包命令保留技能目录占位符。
        str_package_release_command = (  # 通用发布打包命令
            "python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py "
            "package-release <project> --version vX.Y.Z --skill-dir skills/<skill-name>"
        )  # 无仓库上下文时的版本打包示例

        # 通用变更日志命令使用固定输入文件示例。
        str_changelog_command = (  # 通用变更日志命令
            "python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py "
            "git-changelog <project> --input changelog.json"
        )  # 无仓库上下文时的变更日志示例

    # 命名映射让文档渲染职责与命令路由职责解耦。
    return {
        "release_prepare": str_release_prepare_command,
        "release_gate": str_release_gate_command,
        "package_release": str_package_release_command,
        "changelog": str_changelog_command,
    }

# Git Manager 文档根据项目上下文渲染可执行命令或通用占位命令。
def git_manager_doc(
    project: Path | None = None,
    profile: dict[str, Any] | None = None,
) -> str:
    """生成分支、发布包和变更日志治理说明。

    Args:
        project: 可选的项目根目录，用于解析仓库内脚本路径。
        profile: 可选的脚本命令治理配置。

    Returns:
        Git Manager Markdown 文本。
    """

    # 命令构造器统一处理仓库上下文和安装态占位路径。
    dict_commands = git_manager_commands(project, profile)  # Git Manager 命令映射

    # 文档正文引用命名命令，确保说明与运行入口同步。
    return "\n".join([
        "# Git Manager",
        "",
        "## Workspace Management",
        "- Keep all development work in the current working folder and use local branches for isolation.",
        f"- {RELEASE_CORE_WORKTREE_RULE}",
        "",
        "## Branch Configuration",
        "- Protected branches: `master`, `release`.",
        "- Development branches are allowed as temporary local work branches.",
        (
            "- Before releasing an installable `dist/` package, commit all work and merge "
            "development branches into `master`."
        ),
        (
            f"- Use `{dict_commands['release_prepare']}` to auto-commit governed paths from the "
            f"active temporary branch, merge it into `master`, and delete the local branch "
            f"before packaging."
        ),
        "- If a branch has unmerged commits, merge it to `master` before cleanup; never discard it silently.",
        "- After release preparation, delete local branches other than `master` and `release`.",
        "- Do not delete remote branches unless the user explicitly requests remote cleanup.",
        (
            f"- Run `{dict_commands['release_gate']}` before and after packaging to verify branch, "
            "worktree, release artifact, release receipt, and parity gates."
        ),
        "",
        "## Release Configuration",
        "- Place installable releases under `dist/`.",
        "- Name installable release folders as `<name>-vx.x.x` and create a matching zip when required.",
        (
            f"- Build installable releases with `{dict_commands['package_release']}` so the "
            f"versioned release directory, matching zip, and `RELEASE_RECEIPT.json` "
            f"provenance stay aligned."
        ),
        (
            "- Different-version release directories and zip files are immutable history "
            "by default; do not delete, overwrite, or rewrite them during a new packaging "
            "run."
        ),
        (
            "- Rebuilding the same version may replace only the current target release "
            "directory and its matching zip; no other `dist/` artifact may change."
        ),
        (
            "- Installable `dist/` release copies for skill development must be sanitized "
            "before packaging; replace sensitive values in the dist copy only and use "
            "typed placeholders such as `<REDACTED_API_KEY>`, `<REDACTED_PASSWORD>`, "
            "`<REDACTED_EMAIL>`, and `<REDACTED_LOCAL_PATH>`."
        ),
        (
            "- The release receipt must record sanitized files, placeholder types, and "
            "post-sanitization hashes; undeclared or unfinished sanitization blocks "
            "installation."
        ),
        (
            "- Install only from the versioned release directory after receipt validation; "
            "never install directly from the source skill folder."
        ),
        "- Package only after branch cleanup and release records are complete.",
        (
            "- The release commit must include the release artifacts and the current "
            "`docs/git_manager/CHANGELOG.md` entry."
        ),
        (
            "- If the release is for a skill project and the user did not explicitly say "
            "whether to install after release, release handling must ask the install "
            "question instead of silently stopping. Engineering projects must not ask to "
            "install a skill."
        ),
        "",
        "## Change Log",
        (
            "- Update `docs/git_manager/CHANGELOG.md` before each commit that changes "
            "governed release or git-management behavior."
        ),
        (
            "- Archive the previous `CHANGELOG.md` to "
            "`docs/git_manager/history_git_manager/YYYYMMDD-HHMMSS/CHANGELOG.md` before "
            "writing the next current entry."
        ),
        f"- Use `{dict_commands['changelog']}` to rotate and write the current change summary.",
        "",
        "## Current Version",
        "- Record the active version here during release preparation and keep detailed changes in `CHANGELOG.md`.",
        "",
    ])
