"""提供 docs 治理命令共享的路径、JSON、状态和归档辅助函数。"""

# 导入 文档治理共享 所需的依赖模块。
from __future__ import annotations

# 分类脚本可从任意任务目录直接执行，这里补齐兄弟任务模块路径。
import sys
from pathlib import Path

_scripts_python_root = Path(__file__).resolve().parents[1]
for _task_dir in _scripts_python_root.iterdir():
    if _task_dir.is_dir():
        _task_path = str(_task_dir)
        if _task_path not in sys.path:
            sys.path.insert(0, _task_path)

# 导入 文档治理共享 所需的依赖模块。
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil

# 分隔当前密集代码块，保留原有执行顺序。
import subprocess
import sys
from typing import Any
import zipfile

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断

# 导入 文档治理共享 所需的依赖模块。
from agents_common import (
    ensure_global_rule_overrides_file,
    GLOBAL_CODEX_AGENTS_PREAMBLE,
    GLOBAL_CODEX_AGENTS_META,
    GLOBAL_CODEX_AGENTS_BLOCK_END,
    GLOBAL_CODEX_AGENTS_BLOCK_START,
    governance_skill_name,
    RELEASE_CORE_WORKTREE_RULE,

    # 分隔当前密集代码块，保留原有执行顺序。
    current_timestamp,
    display_path,
    emit_json,
    global_codex_agents_path,
    global_codex_agents_status,
    matched_codex_sessions,

    # 再次分隔当前长代码块，降低连续语句密度。
    parse_agents_metadata,
    preferred_skill_version,
    project_profile,
    read_json,
    root_agents_sync_command,
    render_global_codex_agents_template,

    # 分隔导入清单的后续成员，避免超长连续导入块。
    read_skill_version,
    script_command,
    resolve_project,
    session_message_rows,
    global_codex_agents_sync_command,
    governance_script_path,
)
from manage_dirs import init_dir_manager, verify_dir_manager

# 保留 DOC DIRS 中间值，支撑 模块入口 的当前计算步骤。
DOC_DIRS = [  # DOC DIRS 用于本步治理判断
    "docs/handoff",  # DOC DIRS 用于本步治理判断
    "docs/handoff/history_handoff",  # DOC DIRS 用于本步治理判断
    "docs/development",  # DOC DIRS 用于本步治理判断
    "docs/development/history_development",  # DOC DIRS 用于本步治理判断
    "docs/install_configuration",  # DOC DIRS 用于本步治理判断
    "docs/git_manager",  # DOC DIRS 用于本步治理判断
    "docs/git_manager/history_git_manager",  # DOC DIRS 用于本步治理判断
    "docs/dir_manager",  # DOC DIRS 用于本步治理判断
    "docs/dir_manager/change_reviews",  # DOC DIRS 用于本步治理判断
    "docs/dir_manager/history_dir_manager",  # DOC DIRS 用于本步治理判断
]

# 保留 REQUIRED DOC FILES 中间值，支撑 模块入口 的当前计算步骤。
REQUIRED_DOC_FILES = [  # REQUIRED DOC FILES 用于本步治理判断
    "docs/handoff/HANDOFF.md",  # REQUIRED DOC FILES 用于本步治理判断
    "docs/development/DEVELOPMENT.md",  # REQUIRED DOC FILES 用于本步治理判断
    "docs/install_configuration/INSTALL_CONFIGURATION.md",  # REQUIRED DOC FILES 用于本步治理判断
    "docs/git_manager/GIT_MANAGER.md",  # REQUIRED DOC FILES 用于本步治理判断
    "docs/git_manager/CHANGELOG.md",  # REQUIRED DOC FILES 用于本步治理判断
]

# 保留 LAST UPDATED HEADER RE 中间值，支撑 模块入口 的当前计算步骤。
LAST_UPDATED_HEADER_RE = re.compile(r"^<!--\s*Last updated:\s*(.*?)\s*\|\s*Last verified:\s*(.*?)\s*-->$", flags=re.MULTILINE)  # LAST UPDATED HEADER RE 用于本步治理判断

# 保留 SANITIZED PLACEHOLDERS 中间值，支撑 模块入口 的当前计算步骤。
SANITIZED_PLACEHOLDERS = {  # SANITIZED PLACEHOLDERS 用于本步治理判断
    "api_key": "<REDACTED_API_KEY>",  # SANITIZED PLACEHOLDERS 用于本步治理判断
    "password": "<REDACTED_PASSWORD>",  # SANITIZED PLACEHOLDERS 用于本步治理判断
    "email": "<REDACTED_EMAIL>",  # SANITIZED PLACEHOLDERS 用于本步治理判断
    "local_path": "<REDACTED_LOCAL_PATH>",  # SANITIZED PLACEHOLDERS 用于本步治理判断
}

# 保留 LOCAL PRIVATE PATH RE 中间值，支撑 模块入口 的当前计算步骤。
LOCAL_PRIVATE_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|/(?:Users|home)/)[^\s\"'`<>\),\]}]+")  # LOCAL PRIVATE PATH RE 用于本步治理判断

# 保留 SANITIZED ASSIGNMENT RULES 中间值，支撑 模块入口 的当前计算步骤。
SANITIZED_ASSIGNMENT_RULES = [  # SANITIZED ASSIGNMENT RULES 用于本步治理判断
    (  # SANITIZED ASSIGNMENT RULES 用于本步治理判断
        "api_key",  # SANITIZED ASSIGNMENT RULES 用于本步治理判断
        re.compile(r"(?m)^(\s*(?:[A-Z0-9]+_)*(?:API[_-]?KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET)(?:_[A-Z0-9]+)*\s*[:=]\s*)(.+?)\s*$"),  # SANITIZED ASSIGNMENT RULES 用于本步治理判断
    ),  # SANITIZED ASSIGNMENT RULES 用于本步治理判断
    (  # SANITIZED ASSIGNMENT RULES 用于本步治理判断
        "password",  # SANITIZED ASSIGNMENT RULES 用于本步治理判断
        re.compile(r"(?m)^(\s*[A-Z0-9_]*PASSWORD[A-Z0-9_]*\s*[:=]\s*)(.+?)\s*$"),  # SANITIZED ASSIGNMENT RULES 用于本步治理判断
    ),  # SANITIZED ASSIGNMENT RULES 用于本步治理判断
]

# 保留 SANITIZED INLINE RULES 中间值，支撑 模块入口 的当前计算步骤。
SANITIZED_INLINE_RULES = [  # SANITIZED INLINE RULES 用于本步治理判断
    ("email", re.compile(r"(?<!\\)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", flags=re.IGNORECASE)),  # SANITIZED INLINE RULES 用于本步治理判断
    ("local_path", LOCAL_PRIVATE_PATH_RE),  # SANITIZED INLINE RULES 用于本步治理判断
]

# 保留 SANITIZED BINARY PATTERNS 中间值，支撑 模块入口 的当前计算步骤。
SANITIZED_BINARY_PATTERNS = [  # SANITIZED BINARY PATTERNS 用于本步治理判断
    ("api_key", re.compile(br"sk-(?:live|proj|test)-[A-Za-z0-9_-]+")),  # SANITIZED BINARY PATTERNS 用于本步治理判断
    ("password", re.compile(br"password", flags=re.IGNORECASE)),  # SANITIZED BINARY PATTERNS 用于本步治理判断
    ("email", re.compile(br"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),  # SANITIZED BINARY PATTERNS 用于本步治理判断
]

# 定义 should_skip_sanitized_assignment_value 的文档治理共享处理入口。
def should_skip_sanitized_assignment_value(value: str) -> bool:

    # 返回 should_skip_sanitized_assignment_value 已整理完成的调用载荷。
    return value.strip().startswith("re.compile(")

# 保留 STATE PATH 中间值，支撑 模块入口 的当前计算步骤。
STATE_PATH = ".agents/docs-governance-state.json"  # STATE PATH 用于本步治理判断

# 保留 ACTIVE SESSION PATH 中间值，支撑 模块入口 的当前计算步骤。
ACTIVE_SESSION_PATH = ".agents/active-session.json"  # ACTIVE SESSION PATH 用于本步治理判断

# 保留 IGNORED RUNTIME GIT PATHS 中间值，支撑 模块入口 的当前计算步骤。
IGNORED_RUNTIME_GIT_PATHS = {ACTIVE_SESSION_PATH.replace("\\", "/")}  # IGNORED RUNTIME GIT PATHS 用于本步治理判断

# 保留 LEGACY EXPERIENCE REQUEST PATH 中间值，支撑 模块入口 的当前计算步骤。
LEGACY_EXPERIENCE_REQUEST_PATH = ".agents/experience-update-request.json"  # LEGACY EXPERIENCE REQUEST PATH 用于本步治理判断

# 保留 EVOLUTION REQUEST PATH 中间值，支撑 模块入口 的当前计算步骤。
EVOLUTION_REQUEST_PATH = ".agents/evolution-update-request.json"  # EVOLUTION REQUEST PATH 用于本步治理判断

# 保留 EVOLUTION IMPORT REQUEST PATH 中间值，支撑 模块入口 的当前计算步骤。
EVOLUTION_IMPORT_REQUEST_PATH = ".agents/evolution-import-request.json"  # EVOLUTION IMPORT REQUEST PATH 用于本步治理判断

# 保留 EVOLUTION EXPORT ROOT 中间值，支撑 模块入口 的当前计算步骤。
EVOLUTION_EXPORT_ROOT = ".agents/evolution-export"  # EVOLUTION EXPORT ROOT 用于本步治理判断

# 保留 EVOLUTION REVIEW REQUEST PATH 中间值，支撑 模块入口 的当前计算步骤。
EVOLUTION_REVIEW_REQUEST_PATH = ".agents/evolution-review-request.json"  # EVOLUTION REVIEW REQUEST PATH 用于本步治理判断

# 保留 CONVERSATION SNAPSHOT DIR 中间值，支撑 模块入口 的当前计算步骤。
CONVERSATION_SNAPSHOT_DIR = ".agents/conversation-snapshots"  # CONVERSATION SNAPSHOT DIR 用于本步治理判断

# 保留 HANDOFF CURRENT FILENAME 中间值，支撑 模块入口 的当前计算步骤。
HANDOFF_CURRENT_FILENAME = "HANDOFF.md"  # HANDOFF CURRENT FILENAME 用于本步治理判断

# 保留 HANDOFF HISTORY DIRNAME 中间值，支撑 模块入口 的当前计算步骤。
HANDOFF_HISTORY_DIRNAME = "history_handoff"  # HANDOFF HISTORY DIRNAME 用于本步治理判断

# 保留 HANDOFF HISTORY RE 中间值，支撑 模块入口 的当前计算步骤。
HANDOFF_HISTORY_RE = re.compile(r"^HANDOFF-\d{8}-\d{6}(?:-\d+)?\.md$")  # HANDOFF HISTORY RE 用于本步治理判断

# 保留 HANDOFF GENERATED AT RE 中间值，支撑 模块入口 的当前计算步骤。
HANDOFF_GENERATED_AT_RE = re.compile(r"^- Generated at:\s*(.+?)\s*$", flags=re.MULTILINE)  # HANDOFF GENERATED AT RE 用于本步治理判断

# 保留 HANDOFF SECTIONS 中间值，支撑 模块入口 的当前计算步骤。
HANDOFF_SECTIONS = [  # HANDOFF SECTIONS 用于本步治理判断
    "Original Plan And Steps",  # HANDOFF SECTIONS 用于本步治理判断
    "Current Step",  # HANDOFF SECTIONS 用于本步治理判断
    "Problems",  # HANDOFF SECTIONS 用于本步治理判断
    "Resolved Problems",  # HANDOFF SECTIONS 用于本步治理判断
    "Remaining Problems",  # HANDOFF SECTIONS 用于本步治理判断
    "Next Work",  # HANDOFF SECTIONS 用于本步治理判断
    "Verification Evidence",  # HANDOFF SECTIONS 用于本步治理判断
]

# 保留 SAFE TEMPLATE SEGMENT RE 中间值，支撑 模块入口 的当前计算步骤。
SAFE_TEMPLATE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")  # SAFE TEMPLATE SEGMENT RE 用于本步治理判断

# 保留 LEGACY EVOLUTION STATE KEYS 中间值，支撑 模块入口 的当前计算步骤。
LEGACY_EVOLUTION_STATE_KEYS = [  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "last_experience_at",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "last_experience_payload",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "experience_update_required",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "experience_request_due_at",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "experience_request",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "experience_bootstrapped_from_sessions",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "last_evolution_at",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "last_evolution_target",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "last_evolution_summary",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "last_evolution_review_at",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "last_evolution_review_verdict",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "last_evolution_review_target",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "last_evolution_review_sources",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "last_evolution_sink",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
    "last_evolution_index",  # LEGACY EVOLUTION STATE KEYS 用于本步治理判断
]

# 保留 REQUIRED DEVELOPMENT SECTIONS 中间值，支撑 模块入口 的当前计算步骤。
REQUIRED_DEVELOPMENT_SECTIONS = [  # REQUIRED DEVELOPMENT SECTIONS 用于本步治理判断
    "Development Goal",  # REQUIRED DEVELOPMENT SECTIONS 用于本步治理判断
    "Full Development Plan",  # REQUIRED DEVELOPMENT SECTIONS 用于本步治理判断
    "Current Progress",  # REQUIRED DEVELOPMENT SECTIONS 用于本步治理判断
    "Completed Scope",  # REQUIRED DEVELOPMENT SECTIONS 用于本步治理判断
    "Remaining Scope",  # REQUIRED DEVELOPMENT SECTIONS 用于本步治理判断
    "Key Problems And Risks",  # REQUIRED DEVELOPMENT SECTIONS 用于本步治理判断
    "Resolution Strategy And Next Steps",  # REQUIRED DEVELOPMENT SECTIONS 用于本步治理判断
    "Development Result",  # REQUIRED DEVELOPMENT SECTIONS 用于本步治理判断
    "Verification",  # REQUIRED DEVELOPMENT SECTIONS 用于本步治理判断
    "Artifacts And Impact",  # REQUIRED DEVELOPMENT SECTIONS 用于本步治理判断
]

# 保留 DEVELOPMENT MIN LENGTH 中间值，支撑 模块入口 的当前计算步骤。
DEVELOPMENT_MIN_LENGTH = 450  # DEVELOPMENT MIN LENGTH 用于本步治理判断
def stamp() -> str:

    # 返回 stamp 已整理完成的调用载荷。
    return datetime.now().strftime("%Y%m%d-%H%M%S")

# 定义 docs_root 的文档治理共享处理入口。
def docs_root(project: Path) -> Path:

    # 返回 docs_root 已整理完成的调用载荷。
    return project / "docs"

# 定义 git_manager_root 的文档治理共享处理入口。
def git_manager_root(project: Path) -> Path:

    # 返回 git_manager_root 已整理完成的调用载荷。
    return docs_root(project) / "git_manager"

# 定义 git_changelog_file 的文档治理共享处理入口。
def git_changelog_file(project: Path) -> Path:

    # 返回 git_changelog_file 已整理完成的调用载荷。
    return git_manager_root(project) / "CHANGELOG.md"

# 定义 git_history_root 的文档治理共享处理入口。
def git_history_root(project: Path) -> Path:

    # 返回 git_history_root 已整理完成的调用载荷。
    return git_manager_root(project) / "history_git_manager"

# 定义 state_file 的文档治理共享处理入口。
def state_file(project: Path) -> Path:

    # 返回 state_file 已整理完成的调用载荷。
    return project / STATE_PATH

# 定义 active_session_file 的文档治理共享处理入口。
def active_session_file(project: Path) -> Path:

    # 返回 active_session_file 已整理完成的调用载荷。
    return project / ACTIVE_SESSION_PATH

# 定义 evolution_request_file 的文档治理共享处理入口。
def evolution_request_file(project: Path) -> Path:

    # 返回 evolution_request_file 已整理完成的调用载荷。
    return project / EVOLUTION_REQUEST_PATH

# 定义 evolution_import_request_file 的文档治理共享处理入口。
def evolution_import_request_file(project: Path) -> Path:

    # 返回 evolution_import_request_file 已整理完成的调用载荷。
    return project / EVOLUTION_IMPORT_REQUEST_PATH

# 定义 evolution_export_root 的文档治理共享处理入口。
def evolution_export_root(project: Path) -> Path:

    # 返回 evolution_export_root 已整理完成的调用载荷。
    return project / EVOLUTION_EXPORT_ROOT

# 定义 evolution_review_request_file 的文档治理共享处理入口。
def evolution_review_request_file(project: Path) -> Path:

    # 返回 evolution_review_request_file 已整理完成的调用载荷。
    return project / EVOLUTION_REVIEW_REQUEST_PATH

# 定义 conversation_snapshot_dir 的文档治理共享处理入口。
def conversation_snapshot_dir(project: Path) -> Path:

    # 返回 conversation_snapshot_dir 已整理完成的调用载荷。
    return project / CONVERSATION_SNAPSHOT_DIR

# 定义 load_state 的文档治理共享处理入口。
def load_state(project: Path) -> dict[str, Any]:

    # 保留 state 中间值，支撑 load_state 的当前计算步骤。
    state = read_json(state_file(project))  # state 用于本步治理判断

    # 返回 load_state 已整理完成的调用载荷。
    return state if isinstance(state, dict) else {}

# 定义 save_state 的文档治理共享处理入口。
def save_state(project: Path, state: dict[str, Any]) -> None:

    # 保留 agents dir 中间值，支撑 save_state 的当前计算步骤。
    """说明 save_state 在 AGENTS 治理流程中的状态处理职责。
    
    数组契约:
        shape/维度: 本函数处理 AGENTS 状态、JSON 记录或文件路径，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict、list、str、Path 等 Python 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义以 AGENTS 治理配置和状态文件 schema 为准。
    """

    # 说明下方代码段在文档治理共享流程中的职责。
    agents_dir = project / ".agents"  # agents dir 用于本步治理判断

    # 调用 mkdir 完成 save_state 的当前动作。
    agents_dir.mkdir(exist_ok=True)

    # 调用 write_text 完成 save_state 的当前动作。
    state_file(project).write_text(json.dumps(state, indent=2, sort_keys=True, default=str), encoding="utf-8")

# 定义 legacy_evolution_roots 的文档治理共享处理入口。
def legacy_evolution_roots(project: Path) -> list[Path]:

    # 收集 roots 条目，保持 legacy_evolution_roots 的处理顺序稳定。
    list_roots = [project / "assets" / "templates" / "evolution"]  # roots 用于本步治理判断

    # 保留 profile 中间值，支撑 legacy_evolution_roots 的当前计算步骤。
    profile = project_profile(project)  # profile 用于本步治理判断

    # 检查 legacy_evolution_roots 的当前条件是否需要进入专门分支。
    if isinstance(profile, dict):

        # 保留 layout 中间值，支撑 legacy_evolution_roots 的当前计算步骤。
        layout = profile.get("skill_layout") if isinstance(profile.get("skill_layout"), dict) else {}  # layout 用于本步治理判断

        # 定位 raw path 的文件边界，供 legacy_evolution_roots 后续读写校验使用。
        raw_path = str(layout.get("path") or "").strip()  # raw path 用于本步治理判断

        # 检查 legacy_evolution_roots 的当前条件是否需要进入专门分支。
        if raw_path:

            # 调用 append 完成 legacy_evolution_roots 的当前动作。
            list_roots.append(project / raw_path / "assets" / "templates" / "evolution")

    # 保留 skills root 中间值，支撑 legacy_evolution_roots 的当前计算步骤。
    skills_root = project / "skills"  # skills root 用于本步治理判断

    # 检查 legacy_evolution_roots 的当前条件是否需要进入专门分支。
    if skills_root.is_dir():

        # 调用 extend 完成 legacy_evolution_roots 的当前动作。
        list_roots.extend(path / "assets" / "templates" / "evolution" for path in skills_root.iterdir() if path.is_dir())

    # 保留 deduped 中间值，支撑 legacy_evolution_roots 的当前计算步骤。
    list_deduped: list[Path] = []  # deduped 用于本步治理判断

    # 保留 seen 中间值，支撑 legacy_evolution_roots 的当前计算步骤。
    set_seen: set[str] = set()  # seen 用于本步治理判断

    # 逐项推进 legacy_evolution_roots 的候选项检查。
    for path in list_roots:

        # 保留 normalized 中间值，支撑 legacy_evolution_roots 的当前计算步骤。
        normalized = str(path.resolve()) if path.exists() else str(path)  # normalized 用于本步治理判断

        # 检查 legacy_evolution_roots 的当前条件是否需要进入专门分支。
        if normalized not in set_seen:

            # 调用 add 完成 legacy_evolution_roots 的当前动作。
            set_seen.add(normalized)

            # 调用 append 完成 legacy_evolution_roots 的当前动作。
            list_deduped.append(path)

    # 返回 legacy_evolution_roots 已整理完成的调用载荷。
    return list_deduped

# 定义 cleanup_legacy_evolution_artifacts 的文档治理共享处理入口。
def cleanup_legacy_evolution_artifacts(project: Path, state: dict[str, Any] | None = None) -> dict[str, Any]:

    # 收集 removed files 条目，保持 cleanup_legacy_evolution_artifacts 的处理顺序稳定。
    """说明 cleanup_legacy_evolution_artifacts 在 AGENTS 治理流程中的状态处理职责。
    
    数组契约:
        shape/维度: 本函数处理 AGENTS 状态、JSON 记录或文件路径，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict、list、str、Path 等 Python 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义以 AGENTS 治理配置和状态文件 schema 为准。
    """

    # 说明下方代码段在文档治理共享流程中的职责。
    list_removed_files: list[str] = []  # removed files 用于本步治理判断

    # 收集 removed dirs 条目，保持 cleanup_legacy_evolution_artifacts 的处理顺序稳定。
    list_removed_dirs: list[str] = []  # removed dirs 用于本步治理判断

    # 逐项推进 cleanup_legacy_evolution_artifacts 的候选项检查。
    for path in (
        project / LEGACY_EXPERIENCE_REQUEST_PATH,
        evolution_request_file(project),
        evolution_review_request_file(project),
        evolution_import_request_file(project),
    ):

        # 检查 cleanup_legacy_evolution_artifacts 的当前条件是否需要进入专门分支。
        if path.exists():

            # 调用 unlink 完成 cleanup_legacy_evolution_artifacts 的当前动作。
            path.unlink()

            # 调用 append 完成 cleanup_legacy_evolution_artifacts 的当前动作。
            list_removed_files.append(display_path(path, project))

    # 保留 export root 中间值，支撑 cleanup_legacy_evolution_artifacts 的当前计算步骤。
    path_export_root = evolution_export_root(project)  # export root 用于本步治理判断

    # 检查 cleanup_legacy_evolution_artifacts 的当前条件是否需要进入专门分支。
    if path_export_root.exists():

        # 调用 rmtree 完成 cleanup_legacy_evolution_artifacts 的当前动作。
        shutil.rmtree(path_export_root, ignore_errors=True)

        # 调用 append 完成 cleanup_legacy_evolution_artifacts 的当前动作。
        list_removed_dirs.append(display_path(path_export_root, project))

    # 逐项推进 cleanup_legacy_evolution_artifacts 的候选项检查。
    for root in legacy_evolution_roots(project):

        # 检查 cleanup_legacy_evolution_artifacts 的当前条件是否需要进入专门分支。
        if root.exists():

            # 调用 rmtree 完成 cleanup_legacy_evolution_artifacts 的当前动作。
            shutil.rmtree(root, ignore_errors=True)

            # 调用 append 完成 cleanup_legacy_evolution_artifacts 的当前动作。
            list_removed_dirs.append(display_path(root, project))

    # 收集 cleaned keys 条目，保持 cleanup_legacy_evolution_artifacts 的处理顺序稳定。
    list_cleaned_keys: list[str] = []  # cleaned keys 用于本步治理判断

    # 检查 cleanup_legacy_evolution_artifacts 的当前条件是否需要进入专门分支。
    if isinstance(state, dict):

        # 逐项推进 cleanup_legacy_evolution_artifacts 的候选项检查。
        for key in LEGACY_EVOLUTION_STATE_KEYS:

            # 检查 cleanup_legacy_evolution_artifacts 的当前条件是否需要进入专门分支。
            if key in state:

                # 调用 pop 完成 cleanup_legacy_evolution_artifacts 的当前动作。
                state.pop(key, None)

                # 调用 append 完成 cleanup_legacy_evolution_artifacts 的当前动作。
                list_cleaned_keys.append(key)

    # 返回 cleanup_legacy_evolution_artifacts 已整理完成的调用载荷。
    return {
        "removed_files": list_removed_files,
        "removed_dirs": list_removed_dirs,
        "cleaned_state_keys": list_cleaned_keys,
        "changed": bool(list_removed_files or list_removed_dirs or list_cleaned_keys),
    }

# 定义 file_hash 的文档治理共享处理入口。
def file_hash(path: Path) -> str:

    # 检查 file_hash 的当前条件是否需要进入专门分支。
    if not path.exists() or not path.is_file():

        # 返回 file_hash 已整理完成的调用载荷。
        return ""

    # 返回 file_hash 已整理完成的调用载荷。
    return hashlib.sha256(path.read_bytes()).hexdigest()

# 定义 list_lines 的文档治理共享处理入口。
def list_lines(list_values: Any) -> str:

    # 检查 list_lines 的当前条件是否需要进入专门分支。
    if list_values is None or list_values == "":

        # 返回 list_lines 已整理完成的调用载荷。
        return "- Not recorded."

    # 检查 list_lines 的当前条件是否需要进入专门分支。
    if isinstance(list_values, str):

        # 收集 values 条目，保持 list_lines 的处理顺序稳定。
        list_values = [list_values]  # values 用于本步治理判断

    # 检查 list_lines 的当前条件是否需要进入专门分支。
    if not isinstance(list_values, list):

        # 收集 values 条目，保持 list_lines 的处理顺序稳定。
        list_values = [str(list_values)]  # values 用于本步治理判断

    # 收集 lines 条目，保持 list_lines 的处理顺序稳定。
    lines = [str(item).strip() for item in list_values if str(item).strip()]  # lines 用于本步治理判断

    # 检查 list_lines 的当前条件是否需要进入专门分支。
    if not lines:

        # 返回 list_lines 已整理完成的调用载荷。
        return "- Not recorded."

    # 返回 list_lines 已整理完成的调用载荷。
    return "\n".join(f"- {line}" for line in lines)

# 定义 slug 的文档治理共享处理入口。
def slug(value: str) -> str:

    # 保留 cleaned 中间值，支撑 slug 的当前计算步骤。
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")  # cleaned 用于本步治理判断

    # 返回 slug 已整理完成的调用载荷。
    return cleaned or "stage"

# 定义 default_handoff 的文档治理共享处理入口。
def default_handoff() -> str:

    # 返回 default_handoff 已整理完成的调用载荷。
    return "\n".join([
        "# Handoff",
        "",
        "> Latest task handoff. Archive this file before writing the next handoff.",
        "",
        "## Original Plan And Steps",
        "- Not recorded yet.",
        "",
        "## Current Step",
        "- Not recorded yet.",
        "",
        "## Problems",
        "- Not recorded yet.",
        "",
        "## Resolved Problems",
        "- Not recorded yet.",
        "",
        "## Remaining Problems",
        "- Not recorded yet.",
        "",
        "## Next Work",
        "- Not recorded yet.",
        "",
        "## Verification Evidence",
        "- Not recorded yet.",
        "",
    ])

# 定义 control_profile 的文档治理共享处理入口。
def control_profile(project: Path) -> dict[str, Any]:

    # 保留 data 中间值，支撑 control_profile 的当前计算步骤。
    dict_data = read_json(project / ".agents" / "agents-control.json")  # data 用于本步治理判断

    # 返回 control_profile 已整理完成的调用载荷。
    return dict_data if isinstance(dict_data, dict) else {}

# 定义 cadence_checkpoint 的文档治理共享处理入口。
def cadence_checkpoint(count: int, interval: int) -> int:

    # 检查 cadence_checkpoint 的当前条件是否需要进入专门分支。
    if count <= 0 or interval <= 0:

        # 返回 cadence_checkpoint 已整理完成的调用载荷。
        return 0

    # 返回 cadence_checkpoint 已整理完成的调用载荷。
    return (count // interval) * interval

# 定义 cadence_window_bounds 的文档治理共享处理入口。
def cadence_window_bounds(checkpoint: int, interval: int) -> tuple[int, int]:

    # 检查 cadence_window_bounds 的当前条件是否需要进入专门分支。
    if checkpoint <= 0:

        # 返回 cadence_window_bounds 已整理完成的调用载荷。
        return 0, 0

    # 返回 cadence_window_bounds 已整理完成的调用载荷。
    return max(1, checkpoint - interval + 1), checkpoint

# 定义 handoff_count_from_markdown 的文档治理共享处理入口。
def handoff_count_from_markdown(text: str) -> int:

    # 保留 match 中间值，支撑 handoff_count_from_markdown 的当前计算步骤。
    match = re.search(r"^- Handoff count:\s*(\d+)\s*$", text, flags=re.MULTILINE)  # match 用于本步治理判断

    # 返回 handoff_count_from_markdown 已整理完成的调用载荷。
    return int(match.group(1)) if match else 0

# 定义 handoff_paths 的文档治理共享处理入口。
def handoff_paths(project: Path) -> dict[str, Path]:

    # 保留 handoff root 中间值，支撑 handoff_paths 的当前计算步骤。
    handoff_root = project / "docs" / "handoff"  # handoff root 用于本步治理判断

    # 返回 handoff_paths 已整理完成的调用载荷。
    return {
        "root": handoff_root,
        "current": handoff_root / HANDOFF_CURRENT_FILENAME,
        "history": handoff_root / HANDOFF_HISTORY_DIRNAME,
    }

# 定义 docs_governance_initialized 的文档治理共享处理入口。
def docs_governance_initialized(project: Path) -> bool:

    # 逐项推进 docs_governance_initialized 的候选项检查。
    for rel_path in [*DOC_DIRS, *REQUIRED_DOC_FILES, STATE_PATH]:

        # 检查 docs_governance_initialized 的当前条件是否需要进入专门分支。
        if (project / rel_path).exists():

            # 返回 docs_governance_initialized 已整理完成的调用载荷。
            return True

    # 返回 docs_governance_initialized 已整理完成的调用载荷。
    return False

# 定义 handoff_history_filename_for_timestamp 的文档治理共享处理入口。
def handoff_history_filename_for_timestamp(moment: datetime, suffix: int | None = None) -> str:

    # 保留 stamp value 中间值，支撑 handoff_history_filename_for_timestamp 的当前计算步骤。
    stamp_value = moment.strftime("%Y%m%d-%H%M%S")  # stamp value 用于本步治理判断

    # 保留 base 中间值，支撑 handoff_history_filename_for_timestamp 的当前计算步骤。
    base = f"HANDOFF-{stamp_value}"  # base 用于本步治理判断

    # 返回 handoff_history_filename_for_timestamp 已整理完成的调用载荷。
    return f"{base}-{suffix}.md" if suffix is not None else f"{base}.md"

# 定义 unique_handoff_history_path 的文档治理共享处理入口。
def unique_handoff_history_path(history_dir: Path, moment: datetime) -> Path:

    # 保留 target 中间值，支撑 unique_handoff_history_path 的当前计算步骤。
    target = history_dir / handoff_history_filename_for_timestamp(moment)  # target 用于本步治理判断

    # 保留 suffix 中间值，支撑 unique_handoff_history_path 的当前计算步骤。
    int_suffix = 1  # suffix 用于本步治理判断

    # 在循环条件满足时持续推进处理。
    while target.exists():

        # 保留 target 中间值，支撑 unique_handoff_history_path 的当前计算步骤。
        target = history_dir / handoff_history_filename_for_timestamp(moment, suffix=int_suffix)  # target 用于本步治理判断

        # 保留 suffix 中间值，支撑 unique_handoff_history_path 的当前计算步骤。
        int_suffix += 1  # suffix 用于本步治理判断

    # 返回 unique_handoff_history_path 已整理完成的调用载荷。
    return target

# 定义 parse_handoff_generated_at 的文档治理共享处理入口。
def parse_handoff_generated_at(text: str) -> datetime | None:

    # 保留 match 中间值，支撑 parse_handoff_generated_at 的当前计算步骤。
    match = HANDOFF_GENERATED_AT_RE.search(text)  # match 用于本步治理判断

    # 检查 parse_handoff_generated_at 的当前条件是否需要进入专门分支。
    if not match:

        # 返回 parse_handoff_generated_at 已整理完成的调用载荷。
        return None

    # 保留 raw 中间值，支撑 parse_handoff_generated_at 的当前计算步骤。
    raw = match.group(1).strip()  # raw 用于本步治理判断

    # 保护 parse_handoff_generated_at 中允许失败的外部访问。
    try:

        # 返回 parse_handoff_generated_at 已整理完成的调用载荷。
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:

        # 返回 parse_handoff_generated_at 已整理完成的调用载荷。
        return None

# 定义 looks_like_handoff_markdown 的文档治理共享处理入口。
def looks_like_handoff_markdown(text: str) -> bool:

    # 检查 looks_like_handoff_markdown 的当前条件是否需要进入专门分支。
    if "# Handoff" not in text:

        # 返回 looks_like_handoff_markdown 已整理完成的调用载荷。
        return False

    # 收集 present sections 条目，保持 looks_like_handoff_markdown 的处理顺序稳定。
    present_sections = sum(1 for section in HANDOFF_SECTIONS if f"## {section}" in text)  # 已出现 handoff 标准章节数

    # 返回 looks_like_handoff_markdown 已整理完成的调用载荷。
    return present_sections >= max(3, len(HANDOFF_SECTIONS) // 2)

# 定义 audit_handoff_naming 的文档治理共享处理入口。
def audit_handoff_naming(project: Path) -> dict[str, Any]:

    # 收集 paths 条目，保持 audit_handoff_naming 的处理顺序稳定。
    dict_paths = handoff_paths(project)  # paths 用于本步治理判断

    # 保留 handoff root 中间值，支撑 audit_handoff_naming 的当前计算步骤。
    handoff_root = dict_paths["root"]  # handoff root 用于本步治理判断

    # 保留 history dir 中间值，支撑 audit_handoff_naming 的当前计算步骤。
    history_dir = dict_paths["history"]  # history dir 用于本步治理判断

    # 收集 errors 条目，保持 audit_handoff_naming 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 收集 current markdown candidates 条目，保持 audit_handoff_naming 的处理顺序稳定。
    list_current_markdown_candidates: list[str] = []  # current markdown candidates 用于本步治理判断

    # 保留 invalid history markdown 中间值，支撑 audit_handoff_naming 的当前计算步骤。
    list_invalid_history_markdown: list[str] = []  # invalid history markdown 用于本步治理判断

    # 保留 checked 中间值，支撑 audit_handoff_naming 的当前计算步骤。
    list_checked: list[str] = [  # checked 用于本步治理判断
        "docs/handoff",  # checked 用于本步治理判断
        "docs/handoff/HANDOFF.md",  # checked 用于本步治理判断
        "docs/handoff/history_handoff",  # checked 用于本步治理判断
    ]

    # 检查 audit_handoff_naming 的当前条件是否需要进入专门分支。
    if handoff_root.exists() and handoff_root.is_dir():

        # 逐项推进 audit_handoff_naming 的候选项检查。
        for child in sorted(handoff_root.iterdir()):

            # 定位 rel path 的文件边界，供 audit_handoff_naming 后续读写校验使用。
            rel_path = child.relative_to(project).as_posix()  # rel path 用于本步治理判断

            # 检查 audit_handoff_naming 的当前条件是否需要进入专门分支。
            if child.name == HANDOFF_CURRENT_FILENAME:

                # 检查 audit_handoff_naming 的当前条件是否需要进入专门分支。
                if not child.is_file():

                    # 调用 append 完成 audit_handoff_naming 的当前动作。
                    list_errors.append(f"handoff naming drift: current handoff path must be a file: {rel_path}")

                # 分隔 audit_handoff_naming 的控制流边界。
                continue

            # 检查 audit_handoff_naming 的当前条件是否需要进入专门分支。
            if child.name == HANDOFF_HISTORY_DIRNAME:

                # 检查 audit_handoff_naming 的当前条件是否需要进入专门分支。
                if not child.is_dir():

                    # 调用 append 完成 audit_handoff_naming 的当前动作。
                    list_errors.append(f"handoff naming drift: history handoff path must be a directory: {rel_path}")

                # 分隔 audit_handoff_naming 的控制流边界。
                continue

            # 检查 audit_handoff_naming 的当前条件是否需要进入专门分支。
            if child.is_file() and child.suffix.lower() == ".md":

                # 调用 append 完成 audit_handoff_naming 的当前动作。
                list_current_markdown_candidates.append(rel_path)

                # 调用 append 完成 audit_handoff_naming 的当前动作。
                list_errors.append(
                    f"handoff naming drift: current handoff must be exactly docs/handoff/{HANDOFF_CURRENT_FILENAME}; found {rel_path}"
                )
            else:

                # 调用 append 完成 audit_handoff_naming 的当前动作。
                list_errors.append(
                    f"handoff naming drift: docs/handoff only allows {HANDOFF_CURRENT_FILENAME} and {HANDOFF_HISTORY_DIRNAME}/; found {rel_path}"
                )

    # 检查 audit_handoff_naming 的当前条件是否需要进入专门分支。
    if history_dir.exists() and history_dir.is_dir():

        # 逐项推进 audit_handoff_naming 的候选项检查。
        for child in sorted(history_dir.iterdir()):

            # 定位 rel path 的文件边界，供 audit_handoff_naming 后续读写校验使用。
            rel_path = child.relative_to(project).as_posix()  # rel path 用于本步治理判断

            # 调用 append 完成 audit_handoff_naming 的当前动作。
            list_checked.append(rel_path)

            # 检查 audit_handoff_naming 的当前条件是否需要进入专门分支。
            if not child.is_file():

                # 调用 append 完成 audit_handoff_naming 的当前动作。
                list_errors.append(f"handoff naming drift: history_handoff only allows archived markdown files; found {rel_path}")

                # 分隔 audit_handoff_naming 的控制流边界。
                continue

            # 检查 audit_handoff_naming 的当前条件是否需要进入专门分支。
            if child.suffix.lower() != ".md":

                # 调用 append 完成 audit_handoff_naming 的当前动作。
                list_errors.append(f"handoff naming drift: history handoff archive must be markdown: {rel_path}")

                # 分隔 audit_handoff_naming 的控制流边界。
                continue

            # 检查 audit_handoff_naming 的当前条件是否需要进入专门分支。
            if not HANDOFF_HISTORY_RE.fullmatch(child.name):

                # 调用 append 完成 audit_handoff_naming 的当前动作。
                list_invalid_history_markdown.append(rel_path)

                # 调用 append 完成 audit_handoff_naming 的当前动作。
                list_errors.append(
                    "handoff naming drift: history handoff archive must match "
                    f"HANDOFF-YYYYMMDD-HHMMSS.md or HANDOFF-YYYYMMDD-HHMMSS-N.md; found {rel_path}"
                )

    # 返回 audit_handoff_naming 已整理完成的调用载荷。
    return {
        "project": str(project),
        "ok": not list_errors,
        "blocking": bool(list_errors),
        "checked": list_checked,
        "errors": list_errors,
        "current_markdown_candidates": list_current_markdown_candidates,
        "invalid_history_markdown": list_invalid_history_markdown,
    }

# 定义 current_handoff_entry 的文档治理共享处理入口。
def current_handoff_entry(project: Path) -> dict[str, Any] | None:

    # 保留 path 中间值，支撑 current_handoff_entry 的当前计算步骤。
    path = handoff_paths(project)["current"]  # path 用于本步治理判断

    # 检查 current_handoff_entry 的当前条件是否需要进入专门分支。
    if not path.exists() or not path.is_file():

        # 返回 current_handoff_entry 已整理完成的调用载荷。
        return None

    # 保留 content 中间值，支撑 current_handoff_entry 的当前计算步骤。
    content = path.read_text(encoding="utf-8", errors="ignore")  # content 用于本步治理判断

    # 返回 current_handoff_entry 已整理完成的调用载荷。
    return {
        "path": path.relative_to(project).as_posix(),
        "content": content,
        "handoff_count": handoff_count_from_markdown(content),
    }

# 定义 install_configuration_doc 的文档治理共享处理入口。
def install_configuration_doc() -> str:

    # 返回 install_configuration_doc 已整理完成的调用载荷。
    return "\n".join([
        "# Install Configuration",
        "",
        "## Skill Install Path",
        "- Install the skill folder into the target agent skill directory before use.",
        "- When replacing an installed skill, first move the old skill to the sibling `skill_backups/<skill-name>-YYYYMMDD-HHMMSS/` folder.",
        (
            "- `v1.0.0` and later do not support evolution templates; replacement "  # AGENTS 长文本片段
            "installs should remove any legacy `assets/templates/evolution/` content from "  # AGENTS 长文本片段
            "the destination skill."  # AGENTS 长文本片段
        ),
        "- `v1.1.0` and later do not support the experience subsystem; memory under `docs/memory/` is the long-term project context mechanism.",
        "",
        "## Codex Adapter",
        "- Keep `SKILL.md`, `agents/openai.yaml`, `references/`, `scripts/`, and `assets/` together.",
        "",
        "## Claude Adapter",
        "- Use `CLAUDE.md` compatibility shims only when requested; preserve existing non-managed files.",
        "",
        "## OpenClaw Adapter",
        "- Treat OpenClaw as an external adapter target and record project-specific setup here when confirmed.",
        "",
        "## Compatibility Shims",
        "- Create shims with the bundled compatibility script after AGENTS.md generation when requested.",
        "",
    ])

# 定义 default_git_changelog 的文档治理共享处理入口。
def default_git_changelog() -> str:

    # 返回 default_git_changelog 已整理完成的调用载荷。
    return "\n".join([
        "# Change Log",
        "",
        "- Version: not recorded",
        "- Generated at: not recorded",
        "- Summary: not recorded",
        "",
        "## Changes",
        "- Record the staged or committed changes for this release or commit here before the next commit.",
        "",
        "## Verification",
        "- Record the exact validation commands or evidence used for this change set.",
        "",
    ])

# 定义 default_development_record 的文档治理共享处理入口。
def default_development_record() -> str:

    # 返回 default_development_record 已整理完成的调用载荷。
    return "\n".join([
        "# Development Stage: not recorded",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "- Version: not recorded",
        "- Status: not recorded",
        "",
        "## Development Goal",
        "- Not recorded.",
        "",
        "## Full Development Plan",
        "- Not recorded.",
        "",
        "## Current Progress",
        "- Not recorded.",
        "",
        "## Completed Scope",
        "- Not recorded.",
        "",
        "## Remaining Scope",
        "- Not recorded.",
        "",
        "## Key Problems And Risks",
        "- Not recorded.",
        "",
        "## Resolution Strategy And Next Steps",
        "- Not recorded.",
        "",
        "## Development Result",
        "- Not recorded.",
        "",
        "## Verification",
        "- Not recorded.",
        "",
        "## Artifacts And Impact",
        "- Not recorded.",
        "",
    ])

# 定义 validate_development_record 的文档治理共享处理入口。
def validate_development_record(path: Path) -> list[str]:

    # 收集 errors 条目，保持 validate_development_record 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 保留 text 中间值，支撑 validate_development_record 的当前计算步骤。
    text = path.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

    # 检查 validate_development_record 的当前条件是否需要进入专门分支。
    if "# Development Stage: not recorded" in text and "- Version: not recorded" in text and "- Status: not recorded" in text:

        # 返回 validate_development_record 已整理完成的调用载荷。
        return list_errors

    # 逐项推进 validate_development_record 的候选项检查。
    for section in REQUIRED_DEVELOPMENT_SECTIONS:

        # 检查 validate_development_record 的当前条件是否需要进入专门分支。
        if not re.search(rf"^##\s+{re.escape(section)}\s*$", text, flags=re.MULTILINE):

            # 调用 append 完成 validate_development_record 的当前动作。
            list_errors.append(f"{path.relative_to(path.parents[2]).as_posix()}: missing section ## {section}")

    # 检查 validate_development_record 的当前条件是否需要进入专门分支。
    if "- Status: not recorded" in text:

        # 调用 append 完成 validate_development_record 的当前动作。
        list_errors.append(f"{path.relative_to(path.parents[2]).as_posix()}: development status is still placeholder text")

    # 检查 validate_development_record 的当前条件是否需要进入专门分支。
    if len(text.strip()) < DEVELOPMENT_MIN_LENGTH:

        # 调用 append 完成 validate_development_record 的当前动作。
        list_errors.append(f"{path.relative_to(path.parents[2]).as_posix()}: development record is too short")

    # 返回 validate_development_record 已整理完成的调用载荷。
    return list_errors

# 定义 git_manager_doc 的文档治理共享处理入口。
def git_manager_doc(project: Path | None = None, profile: dict[str, Any] | None = None) -> str:

    # 保留 release prepare command 中间值，支撑 git_manager_doc 的当前计算步骤。
    release_prepare_command = (  # release prepare command 用于本步治理判断
        script_command(project, "manage_docs.py", "release-prepare", "<project>", "--version", "vX.Y.Z", "--skill-dir", "skills/<skill-name>", profile=profile)  # release prepare command 用于本步治理判断
        if project is not None  # release prepare command 用于本步治理判断
        else "python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py release-prepare <project> --version vX.Y.Z --skill-dir skills/<skill-name>"  # release prepare command 用于本步治理判断
    )

    # 保留 release gate command 中间值，支撑 git_manager_doc 的当前计算步骤。
    release_gate_command = (  # release gate command 用于本步治理判断
        script_command(  # release gate 子命令完整示例文本
            project,  # release gate 命令归属项目
            "manage_docs.py",  # release gate 所在治理脚本
            "release-gate",  # 发布治理门禁子命令
            "<project>",  # release gate 项目占位参数
            "--version",  # release gate 版本参数名
            "vX.Y.Z",  # release gate 版本占位
            "--skill-dir",  # release gate skill 目录参数名
            "skills/<skill-name>",  # release gate skill 目录占位
            "--phase",  # release gate 阶段参数名
            "pre|post",  # release gate 阶段占位
            profile=profile,  # release gate 命令使用的项目治理档案
        )
        if project is not None  # 当前项目存在时使用本仓库脚本路径
        else (  # 无项目上下文时保留安装技能路径模板
            "python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py "  # fallback 命令的脚本路径前缀
            "release-gate <project> --version vX.Y.Z --skill-dir "  # fallback 命令的 release-gate 参数前半段
            "skills/<skill-name> --phase pre|post"  # fallback 命令的 skill 目录和阶段占位
        )
    )

    # 保留 package release command 中间值，支撑 git_manager_doc 的当前计算步骤。
    package_release_command = (  # package-release 命令示例进入 Git Manager 文档
        script_command(project, "manage_docs.py", "package-release", "<project>", "--version", "vX.Y.Z", "--skill-dir", "skills/<skill-name>", profile=profile)  # 当前项目存在时使用本仓库脚本路径
        if project is not None  # 当前项目存在时渲染可直接执行的命令
        else "python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py package-release <project> --version vX.Y.Z --skill-dir skills/<skill-name>"  # 无项目上下文时保留安装技能路径模板
    )

    # 保留 changelog command 中间值，支撑 git_manager_doc 的当前计算步骤。
    changelog_command = (  # changelog command 用于本步治理判断
        script_command(project, "manage_docs.py", "git-changelog", "<project>", "--input", "changelog.json", profile=profile)  # changelog command 用于本步治理判断
        if project is not None  # changelog command 用于本步治理判断
        else "python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py git-changelog <project> --input changelog.json"  # changelog command 用于本步治理判断
    )

    # 返回 git_manager_doc 已整理完成的调用载荷。
    return "\n".join([
        "# Git Manager",
        "",
        "## Workspace Management",
        "- Keep current development work in the working folder unless the user requests a separate worktree.",
        f"- {RELEASE_CORE_WORKTREE_RULE}",
        "",
        "## Branch Configuration",
        "- Protected branches: `master`, `release`.",
        "- Development branches are allowed as temporary local work branches.",
        "- Before releasing an installable `dist/` package, commit all work and merge development branches into `master`.",
        (
            f"- Use `{release_prepare_command}` to auto-commit governed paths from the "  # AGENTS 长文本片段
            f"active temporary branch, merge it into `master`, and delete the local branch "  # AGENTS 长文本片段
            f"before packaging."  # AGENTS 长文本片段
        ),
        "- If a branch has unmerged commits, merge it to `master` before cleanup; never discard it silently.",
        "- After release preparation, delete local branches other than `master` and `release`.",
        "- Do not delete remote branches unless the user explicitly requests remote cleanup.",
        f"- Run `{release_gate_command}` before and after packaging to verify branch, worktree, release artifact, release receipt, and parity gates.",
        "",
        "## Release Configuration",
        "- Place installable releases under `dist/`.",
        "- Name installable release folders as `<name>-vx.x.x` and create a matching zip when required.",
        (
            f"- Build installable releases with `{package_release_command}` so the "  # AGENTS 长文本片段
            f"versioned release directory, matching zip, and `RELEASE_RECEIPT.json` "  # AGENTS 长文本片段
            f"provenance stay aligned."  # AGENTS 长文本片段
        ),
        (
            "- Different-version release directories and zip files are immutable history "  # AGENTS 长文本片段
            "by default; do not delete, overwrite, or rewrite them during a new packaging "  # AGENTS 长文本片段
            "run."  # AGENTS 长文本片段
        ),
        "- Rebuilding the same version may replace only the current target release directory and its matching zip; no other `dist/` artifact may change.",
        (
            "- Installable `dist/` release copies for skill development must be sanitized "  # AGENTS 长文本片段
            "before packaging; replace sensitive values in the dist copy only and use "  # AGENTS 长文本片段
            "typed placeholders such as `<REDACTED_API_KEY>`, `<REDACTED_PASSWORD>`, "  # AGENTS 长文本片段
            "`<REDACTED_EMAIL>`, and `<REDACTED_LOCAL_PATH>`."  # AGENTS 长文本片段
        ),
        (
            "- The release receipt must record sanitized files, placeholder types, and "  # AGENTS 长文本片段
            "post-sanitization hashes; undeclared or unfinished sanitization blocks "  # AGENTS 长文本片段
            "installation."  # AGENTS 长文本片段
        ),
        "- Install only from the versioned release directory after receipt validation; never install directly from the source skill folder.",
        "- Package only after branch cleanup and release records are complete.",
        "- The release commit must include the release artifacts and the current `docs/git_manager/CHANGELOG.md` entry.",
        (
            "- If the release is for a skill project and the user did not explicitly say "  # AGENTS 长文本片段
            "whether to install after release, release handling must ask the install "  # AGENTS 长文本片段
            "question instead of silently stopping. Engineering projects must not ask to "  # AGENTS 长文本片段
            "install a skill."  # AGENTS 长文本片段
        ),
        "",
        "## Change Log",
        "- Update `docs/git_manager/CHANGELOG.md` before each commit that changes governed release or git-management behavior.",
        "- Archive the previous `CHANGELOG.md` to `docs/git_manager/history_git_manager/YYYYMMDD-HHMMSS/CHANGELOG.md` before writing the next current entry.",
        f"- Use `{changelog_command}` to rotate and write the current change summary.",
        "",
        "## Current Version",
        "- Record the active version here during release preparation and keep detailed changes in `CHANGELOG.md`.",
        "",
    ])


