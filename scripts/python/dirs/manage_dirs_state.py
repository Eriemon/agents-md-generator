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

# 导入 目录状态 所需的依赖模块。
from datetime import datetime
from fnmatch import fnmatch
import json
from pathlib import Path
import re
from typing import Any

# 导入 目录状态 所需的依赖模块。
from agents_common import SKIP_DIRS, read_json, script_command
from workspace_settings_policy import (
    SETTINGS_FOLDER,
    REMOTE_DEFAULT_SETTINGS,
    workspace_settings_contract,
    workspace_settings_location_reason,
)


# 整理 模块入口 需要的 DIR MANAGER DIR 目录状态信息。
DIR_MANAGER_DIR = Path("docs") / "dir_manager"  # 目录治理值

# 整理 模块入口 需要的 CURRENT STRUCTURE 目录状态信息。
CURRENT_STRUCTURE = DIR_MANAGER_DIR / "current_structure.json"  # 目录治理值

# 整理 模块入口 需要的 PLANNED STRUCTURE 目录状态信息。
PLANNED_STRUCTURE = DIR_MANAGER_DIR / "planned_structure.json"  # 目录治理值

# 整理 模块入口 需要的 DIR MANAGER MD 目录状态信息。
DIR_MANAGER_MD = DIR_MANAGER_DIR / "DIR_MANAGER.md"  # 目录治理值

# 整理 模块入口 需要的 CHANGE REVIEWS 目录状态信息。
CHANGE_REVIEWS = DIR_MANAGER_DIR / "change_reviews"  # 目录治理值

# 整理 模块入口 需要的 HISTORY DIR MANAGER 目录状态信息。
HISTORY_DIR_MANAGER = DIR_MANAGER_DIR / "history_dir_manager"  # 目录治理值

# 整理 模块入口 需要的 CRITICAL PREFIXES 目录状态信息。
CRITICAL_PREFIXES = {  # 目录治理值
    ".agents",  # 目录治理值
    ".settings",  # 目录治理值
    "agents",  # 目录治理值
    "assets",  # 目录治理值
    "dist",  # 目录治理值
    "docs",  # 目录治理值
    "docs/dir_manager",  # 目录治理值
    "docs/handoff",  # 目录治理值
    "docs/git_manager",  # 目录治理值
    "references",  # 目录治理值
    "scripts",  # 目录治理值
    "src",  # 目录治理值
    "tests",  # 目录治理值
}

# 整理 模块入口 需要的 GOVERNANCE PREFIXES 目录状态信息。
GOVERNANCE_PREFIXES = {  # 目录治理值
    ".agents",  # 目录治理值
    "docs/dir_manager",  # 目录治理值
    "docs/handoff",  # 目录治理值
    "docs/git_manager",  # 目录治理值
}

# 整理 模块入口 需要的 TAKEOVER PRESERVE ROOT FILES 目录状态信息。
TAKEOVER_PRESERVE_ROOT_FILES = {  # 目录治理值
    "AGENTS.md",  # 目录治理值
    "CLAUDE.md",  # 目录治理值
    "GEMINI.md",  # 目录治理值
    ".gitignore",  # 目录治理值
    ".gitattributes",  # 目录治理值
    ".editorconfig",  # 目录治理值
}

# 整理 模块入口 需要的 ALLOWED ROOT FILES 目录状态信息。
ALLOWED_ROOT_FILES = sorted(TAKEOVER_PRESERVE_ROOT_FILES)  # 目录治理值

# 整理 模块入口 需要的 EPHEMERAL ROOT INPUT FILE RE 目录状态信息。
EPHEMERAL_ROOT_INPUT_FILE_RE = re.compile(  # 目录治理值
    (
        r"^(?:answers|first-answers|recovery|session|stage|handoff|change|allowed-change|"  # 目录输入前缀集合
        r"blocked-change|blocked-remote-change|blocked-remote-source-change)"  # 阻断目录输入前缀
        r"(?:-[a-z0-9._-]+)?\.json$"  # 目录输入可选后缀
    ),  # 目录治理临时输入文件模式
    flags=re.IGNORECASE,  # 目录治理值
)

# 整理 模块入口 需要的 ALLOWED ROOT FILE PATTERNS 目录状态信息。
ALLOWED_ROOT_FILE_PATTERNS = (  # 目录治理值
    "answers.json",  # 目录治理值
    "*-answers.json",  # 目录治理值
    "change.json",  # 目录治理值
    "*-change.json",  # 目录治理值
    "session.json",  # 目录治理值
    "recovery.json",  # 目录治理值
    "handoff.json",  # 目录治理值
    "stage.json",  # 目录治理值
    "changelog.json",  # 目录治理值
)

# 整理 模块入口 需要的 ROOT OPTIONAL WORK DIRS 目录状态信息。
ROOT_OPTIONAL_WORK_DIRS = ("tests", "reports", "runs", "smoke")  # 目录治理值

# 整理 模块入口 需要的 ROOT OPTIONAL WORK DIR PREFIXES 目录状态信息。
ROOT_OPTIONAL_WORK_DIR_PREFIXES = ("smoke-",)  # 目录治理值

# 整理 模块入口 需要的 REMOTE PROTECTED PATH CLASSES 目录状态信息。
REMOTE_PROTECTED_PATH_CLASSES = [  # 目录治理值
    "workspace-root",  # 目录治理值
    "conda-environment-root",  # 目录治理值
    "conda-environment",  # 目录治理值
    "active-run-root",  # 目录治理值
    "active-run",  # 目录治理值
    "backup-run-root",  # 目录治理值
    "backup-run",  # 目录治理值
]

# 整理 模块入口 需要的 STRUCTURE SKIP FILE PATTERNS 目录状态信息。
STRUCTURE_SKIP_FILE_PATTERNS = (  # 目录治理值
    ".agents/active-session.json",  # 目录治理值
    ".agents/session-*.json",  # 目录治理值
    ".agents/release-*.json",  # 目录治理值
)


# 定义 stamp 的目录状态处理入口。
def stamp() -> str:

    # 返回 stamp 的目录状态载荷。
    return datetime.now().strftime("%Y%m%d-%H%M%S")


# 定义 normalize_rel 的目录状态处理入口。
def normalize_rel(raw: str) -> str:

    # 整理 normalize_rel 需要的 value 目录状态信息。
    raw_value = str(raw).replace("\\", "/").strip().strip("/")  # 目录治理值

    # 返回 normalize_rel 的目录状态载荷。
    return re.sub(r"/+", "/", raw_value)


# 定义 invalid_path_reason 的目录状态处理入口。
def invalid_path_reason(raw: str) -> str | None:

    # 整理 invalid_path_reason 需要的 value 目录状态信息。
    raw_value = str(raw).strip()  # 目录治理值

    # 整理 invalid_path_reason 需要的 normalized 目录状态信息。
    normalized = raw_value.replace("\\", "/")  # 目录治理值

    # 校验 invalid_path_reason 的目录状态分支。
    if not raw_value:

        # 返回 invalid_path_reason 的目录状态载荷。
        return "empty path is not allowed"

    # 校验 invalid_path_reason 的目录状态分支。
    if re.match(r"^[A-Za-z]:[/\\]", raw_value) or normalized.startswith("/"):

        # 返回 invalid_path_reason 的目录状态载荷。
        return f"path must stay inside the project and cannot be absolute: {raw_value}"

    # 校验 invalid_path_reason 的目录状态分支。
    if ".." in normalized.split("/"):

        # 返回 invalid_path_reason 的目录状态载荷。
        return f"path must not contain parent traversal: {raw_value}"

    # 校验 invalid_path_reason 的目录状态分支。
    if any(char in raw_value for char in "*?<>|"):

        # 返回 invalid_path_reason 的目录状态载荷。
        return f"path must not contain wildcard or unsafe shell characters: {raw_value}"

    # 返回 invalid_path_reason 的目录状态载荷。
    return None


# 定义 is_skipped 的目录状态处理入口。
def is_skipped(path: Path, root: Path) -> bool:

    # 收集 parts 目录状态条目。
    parts = path.relative_to(root).parts  # 目录治理值

    # 返回 is_skipped 的目录状态载荷。
    return bool(set(parts) & SKIP_DIRS)


# 定义 scan_structure 的目录状态处理入口。
def scan_structure(project: Path) -> dict[str, Any]:

    # 收集 directories 目录状态条目。
    list_directories: list[str] = []  # 目录治理值

    # 收集 files 目录状态条目。
    list_files: list[str] = []  # 目录治理值

    # 逐项检查 scan_structure 目录状态候选。
    for path in sorted(project.rglob("*")):

        # 校验 scan_structure 的目录状态分支。
        if is_skipped(path, project):

            # 分隔 scan_structure 的控制流边界。
            continue

        # 整理 scan_structure 需要的 rel 目录状态信息。
        rel = path.relative_to(project).as_posix()  # 目录治理值

        # 校验 scan_structure 的目录状态分支。
        if path.is_dir():

            # 追加 scan_structure 的目录状态诊断。
            list_directories.append(rel)

        # 校验 scan_structure 的目录状态分支。
        elif path.is_file():

            # 校验 scan_structure 的目录状态分支。
            if any(fnmatch(rel, pattern) for pattern in STRUCTURE_SKIP_FILE_PATTERNS):

                # 分隔 scan_structure 的控制流边界。
                continue

            # 追加 scan_structure 的目录状态诊断。
            list_files.append(rel)

    # 返回 scan_structure 的目录状态载荷。
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_root": "<PROJECT_ROOT>",
        "directories": list_directories,
        "files": list_files,
        "skip_dirs": sorted(SKIP_DIRS),
    }


# 定义 dir_manager_doc 的目录状态处理入口。
def dir_manager_doc(project: Path) -> str:

    # 整理 dir_manager_doc 需要的 review command 目录状态信息。
    review_command = script_command(project, "manage_dirs.py", "review", "<project>", "--input", "change.json")  # 目录治理值

    # 整理 dir_manager_doc 需要的 archive command 目录状态信息。
    archive_command = script_command(project, "manage_dirs.py", "archive", "<project>", "--reason", "force-confirmed directory override")  # 目录治理值

    # 返回 dir_manager_doc 的目录状态载荷。
    return "\n".join([
        "# Directory Manager",
        "",
        "This file is the strict gate for creating, moving, renaming, or deleting local project folders and remote deployment workspace folders.",
        "",
        "## Required Review",
        "- Read this file before changing folder structure.",
        f"- Run `{review_command}` before directory changes.",
        "- Do not move, rename, or delete governance folders without explicit user force-confirmation.",
        "- If review blocks a change, refuse default execution and explain the risk to the user.",
        (
            "- If the user explicitly force-confirms a blocked change, archive old dir "  # AGENTS 长文本片段
            "manager content under `history_dir_manager/YYYYMMDD-HHMMSS/` before changing "  # AGENTS 长文本片段
            "structure."  # AGENTS 长文本片段
        ),
        "",
        "## Blocked By Default",
        "- Paths outside the project, absolute paths, parent traversal, wildcards, or shell-unsafe path characters.",
        "- New top-level folders not listed in `planned_structure.json`.",
        f"- Workspace engineering config files such as `project.local.json`, `project.remote.json`, or `server_list.local.json` outside `{SETTINGS_FOLDER}/`.",
        f"- Any remote attempt to copy `{SETTINGS_FOLDER}/*.local.json` such as `{SETTINGS_FOLDER}/server_list.local.json` into the remote workspace.",
        "- Remote deployment folders not listed in `planned_structure.json` remote_deployment planning.",
        "- Moving or deleting `.agents/`, `docs/dir_manager/`, `docs/handoff/`, or `docs/git_manager/`.",
        "- Moving source, tests, docs, dist, scripts, assets, references, or agents folders to unplanned locations.",
        "- Mixing generated output, release packages, or temporary references into source folders.",
        "",
        "## User Force Override",
        "- Explain why the request is unreasonable or risky.",
        "- State severe hazards such as broken tests, invalid release packages, stale AGENTS.md scopes, broken history links, or failed skill installation.",
        "- Ask the user to explicitly confirm forced directory structure modification.",
        f"- Run `{archive_command}` before applying a force-confirmed folder change.",
        "- Record confirmation and risk in the next handoff.",
        "",
    ])


# 定义 control_profile 的目录状态处理入口。
def control_profile(project: Path) -> dict[str, Any]:

    # 整理 control_profile 需要的 data 目录状态信息。
    dict_data = read_json(project / ".agents" / "agents-control.json")  # 目录治理值

    # 返回 control_profile 的目录状态载荷。
    return dict_data if isinstance(dict_data, dict) else {}


# 定义 display_rel 的目录状态处理入口。
def display_rel(path: Path, project: Path) -> str:

    # 保护 display_rel 中允许失败的外部访问。
    try:

        # 返回 display_rel 的目录状态载荷。
        return path.relative_to(project).as_posix()
    except Exception:

        # 返回 display_rel 的目录状态载荷。
        return path.resolve().as_posix()


# 定义 remote_structure 的目录状态处理入口。
def remote_structure(project: Path) -> str:

    # 保存 profile 映射，维持 remote_structure 的字段关系。
    dict_profile = control_profile(project)  # 目录治理值

    # 整理 remote_structure 需要的 contract 目录状态信息。
    contract = dict_profile.get("directory_contract", {}) if isinstance(dict_profile.get("directory_contract"), dict) else {}  # 目录治理值

    # 整理 remote_structure 需要的 raw 目录状态信息。
    raw = str(contract.get("remote", "")).strip()  # 目录治理值

    # 校验 remote_structure 的目录状态分支。
    if not raw:

        # 返回 remote_structure 的目录状态载荷。
        return "not configured"

    # 校验 remote_structure 的目录状态分支。
    if raw.lower() in {"none", "not configured"}:

        # 返回 remote_structure 的目录状态载荷。
        return "not configured"

    # 校验 remote_structure 的目录状态分支。
    if "no remote workspace is configured" in raw.lower():

        # 返回 remote_structure 的目录状态载荷。
        return "not configured"

    # 返回 remote_structure 的目录状态载荷。
    return raw


# 定义 remote_environment_policy 的目录状态处理入口。
def remote_environment_policy(project: Path) -> dict[str, Any]:

    # 保存 profile 映射，维持 remote_environment_policy 的字段关系。
    dict_profile = control_profile(project)  # 目录治理值

    # 整理 remote_environment_policy 需要的 contract 目录状态信息。
    contract = dict_profile.get("directory_contract", {}) if isinstance(dict_profile.get("directory_contract"), dict) else {}  # 目录治理值

    # 整理 remote_environment_policy 需要的 policy 目录状态信息。
    policy = contract.get("remote_environment_policy", {})  # 目录治理值

    # 返回 remote_environment_policy 的目录状态载荷。
    return policy if isinstance(policy, dict) else {}


# 定义 remote_runtime_archive_policy 的目录状态处理入口。
def remote_runtime_archive_policy(project: Path) -> dict[str, Any]:

    # 保存 profile 映射，维持 remote_runtime_archive_policy 的字段关系。
    dict_profile = control_profile(project)  # 目录治理值

    # 整理 remote_runtime_archive_policy 需要的 contract 目录状态信息。
    contract = dict_profile.get("directory_contract", {}) if isinstance(dict_profile.get("directory_contract"), dict) else {}  # 目录治理值

    # 整理 remote_runtime_archive_policy 需要的 policy 目录状态信息。
    policy = contract.get("remote_runtime_archive_policy", {})  # 目录治理值

    # 返回 remote_runtime_archive_policy 的目录状态载荷。
    return policy if isinstance(policy, dict) else {}


# 定义 remote_deployment_plan 的目录状态处理入口。
def remote_deployment_plan(project: Path) -> dict[str, Any]:

    # 整理 remote_deployment_plan 需要的 workspace 目录状态信息。
    str_workspace = remote_structure(project)  # 目录治理值

    # 保存 environment policy 映射，维持 remote_deployment_plan 的字段关系。
    dict_environment_policy = remote_environment_policy(project)  # 目录治理值

    # 保存 runtime policy 映射，维持 remote_deployment_plan 的字段关系。
    dict_runtime_policy = remote_runtime_archive_policy(project)  # 目录治理值

    # 整理 remote_deployment_plan 需要的 planned 目录状态信息。
    planned = [] if str_workspace == "not configured" else [str_workspace]  # 目录治理值

    # 校验 remote_deployment_plan 的目录状态分支。
    if str_workspace != "not configured":

        # 追加 remote_deployment_plan 的目录状态诊断。
        planned.append(f"{str_workspace.rstrip('/')}/{SETTINGS_FOLDER}/")

        # 整理 remote_deployment_plan 需要的 conda template 目录状态信息。
        str_conda_template = normalize_rel(str(dict_environment_policy.get("path_template", "")).strip())  # 目录治理值

        # 整理 remote_deployment_plan 需要的 active template 目录状态信息。
        str_active_template = normalize_rel(str(dict_runtime_policy.get("active_path_template", "")).strip())  # 目录治理值

        # 整理 remote_deployment_plan 需要的 backup template 目录状态信息。
        str_backup_template = normalize_rel(str(dict_runtime_policy.get("backup_path_template", "")).strip())  # 目录治理值

        # 逐项检查 remote_deployment_plan 目录状态候选。
        for template in [str_conda_template, str_active_template, str_backup_template]:

            # 校验 remote_deployment_plan 的目录状态分支。
            if template:

                # 追加 remote_deployment_plan 的目录状态诊断。
                planned.append(f"{str_workspace.rstrip('/')}/{template}")

        # 校验 remote_deployment_plan 的目录状态分支。
        if str_backup_template:

            # 收集 parts 目录状态条目。
            parts = str_backup_template.split("/")  # 目录治理值

            # 逐项检查 remote_deployment_plan 目录状态候选。
            while len(parts) > 1:

                # 调用 pop 处理 remote_deployment_plan。
                parts.pop()

                # 追加 remote_deployment_plan 的目录状态诊断。
                planned.append(f"{str_workspace.rstrip('/')}/{'/'.join(parts)}")

    # 整理 remote_deployment_plan 需要的 planned 目录状态信息。
    planned = sorted(dict.fromkeys(planned))  # 目录治理值

    # 返回 remote_deployment_plan 的目录状态载荷。
    return {
        "workspace_root": str_workspace,
        "planned_structure": planned,
        "protected_paths": planned,
        "workspace_settings": workspace_settings_contract(),
        "conda_environment": {
            "status": dict_environment_policy.get("status", "disabled"),
            "scope": dict_environment_policy.get("scope", "remote-only"),
            "manager": dict_environment_policy.get("manager", "conda-prefix"),
            "path_template": str(dict_environment_policy.get("path_template", "")).strip(),
            "required_when_remote_configured": bool(dict_environment_policy.get("required_when_remote_configured", True)),
        },
        "runtime_artifacts": {
            "status": dict_runtime_policy.get("status", "disabled"),
            "active_path_template": str(dict_runtime_policy.get("active_path_template", "")).strip(),
            "backup_path_template": str(dict_runtime_policy.get("backup_path_template", "")).strip(),
            "run_id_required": bool(dict_runtime_policy.get("run_id_required", True)),
            "archive_after_verification": bool(dict_runtime_policy.get("archive_after_verification", False)),
            "archive_trigger": str(dict_runtime_policy.get("archive_trigger", "")).strip(),
        },
        "protected_path_classes": list(REMOTE_PROTECTED_PATH_CLASSES),
        "require_review_for_all_mutations": True,
        "review_required_for": ["create", "move", "delete", "rename"],
        "block_on_failed_review": True,
        "force_override_requires_user_confirmation": True,
    }


# 定义 profile_layout_policy 的目录状态处理入口。
def profile_layout_policy(project: Path) -> tuple[str, list[str], bool]:

    # 保存 profile 映射，维持 profile_layout_policy 的字段关系。
    dict_profile = control_profile(project)  # 目录治理值

    # 整理 profile_layout_policy 需要的 contract 目录状态信息。
    contract = dict_profile.get("directory_contract", {}) if isinstance(dict_profile.get("directory_contract"), dict) else {}  # 目录治理值

    # 整理 profile_layout_policy 需要的 primary 目录状态信息。
    str_primary = normalize_rel(str(contract.get("primary_project_root", "")).strip())  # 目录治理值

    # 校验 profile_layout_policy 的目录状态分支。
    if not str_primary:

        # 整理 profile_layout_policy 需要的 kind 目录状态信息。
        kind = str(dict_profile.get("kind", "")).strip().lower()  # 目录治理值

        # 整理 profile_layout_policy 需要的 name 目录状态信息。
        name = str(dict_profile.get("name", "")).strip()  # 目录治理值

        # 整理 profile_layout_policy 需要的 skill layout 目录状态信息。
        skill_layout = dict_profile.get("skill_layout", {}) if isinstance(dict_profile.get("skill_layout"), dict) else {}  # 目录治理值

        # 校验 profile_layout_policy 的目录状态分支。
        if kind == "skill":

            # 整理 profile_layout_policy 需要的 primary 目录状态信息。
            str_primary = normalize_rel(str(skill_layout.get("path", "")).strip()) or (f"skills/{name}" if name else "")  # 目录治理值

        # 校验 profile_layout_policy 的目录状态分支。
        elif kind == "engineering" and name:

            # 整理 profile_layout_policy 需要的 primary 目录状态信息。
            str_primary = f"engineering/{name}"  # 目录治理值

    # 收集 allowed 目录状态条目。
    list_allowed = [  # 目录治理值
        normalize_rel(item)  # 目录治理值
        for item in contract.get("allowed_new_paths", [])  # 目录治理值
        if str(item).strip()  # 目录治理值
    ]

    # 校验 profile_layout_policy 的目录状态分支。
    if not list_allowed and str_primary:

        # 收集 allowed 目录状态条目。
        list_allowed = [str_primary, "tests", "smoke", "reports", "runs", "dist", "docs", ".agents", "ref"]  # 目录治理值

    # 标记 enforce 判断，控制 profile_layout_policy 的分支走向。
    bool_enforce = bool(contract.get("enforce_primary_project_root", False) or str_primary)  # 目录治理值

    # 返回 profile_layout_policy 的目录状态载荷。
    return str_primary, list_allowed, bool_enforce


# 定义 planned_structure 的目录状态处理入口。
def planned_structure(project: Path) -> dict[str, Any]:

    # 收集 primary root、configured paths、enforce primary 目录状态条目。
    tuple_primary_root, tuple_configured_paths, tuple_enforce_primary = profile_layout_policy(project)  # 目录治理值

    # 校验 planned_structure 的目录状态分支。
    if tuple_configured_paths:

        # 收集 current dirs 目录状态条目。
        set_current_dirs = set(tuple_configured_paths)  # 目录治理值
    else:

        # 收集 current dirs 目录状态条目。
        set_current_dirs = {  # 目录治理值
            path.name + "/"  # 目录治理值
            for path in project.iterdir()  # 目录治理值
            if path.is_dir() and path.name not in SKIP_DIRS  # 目录治理值
        }

    # 调用 update 处理 planned_structure。
    set_current_dirs.update({
        f"{SETTINGS_FOLDER}/",
        "docs/",
        "docs/dir_manager/",
        "docs/dir_manager/history_dir_manager/",
        "docs/handoff/",
        "docs/development/",
        "docs/install_configuration/",
        "docs/git_manager/",
    })

    # 收集 current dirs 目录状态条目。
    set_current_dirs = {item if item.endswith("/") else item + "/" for item in set_current_dirs}  # 目录治理值

    # 返回 planned_structure 的目录状态载荷。
    return {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "allowed_new_paths": sorted(set_current_dirs),
        "allowed_root_files": list(ALLOWED_ROOT_FILES),
        "root_optional_work_dirs": list(ROOT_OPTIONAL_WORK_DIRS),
        "root_optional_work_dir_prefixes": list(ROOT_OPTIONAL_WORK_DIR_PREFIXES),
        "workspace_settings": workspace_settings_contract(),
        "primary_project_root": f"{tuple_primary_root}/" if tuple_primary_root else "",
        "allowed_top_level_roots": sorted({
            normalize_rel(item).split("/", 1)[0] + "/"
            for item in set_current_dirs
            if normalize_rel(item)
        }),
        "enforce_primary_project_root": tuple_enforce_primary,
        "protected_paths": sorted(GOVERNANCE_PREFIXES),
        "review_required_for": ["create", "move", "delete", "rename"],
        "remote_deployment": remote_deployment_plan(project),
        "block_on_failed_review": True,
        "force_override_requires_user_confirmation": True,
        "force_override_archive": "docs/dir_manager/history_dir_manager/YYYYMMDD-HHMMSS",
    }


# 定义 load_planned 的目录状态处理入口。
def load_planned(project: Path) -> dict[str, Any]:

    # 整理 load_planned 需要的 planned 目录状态信息。
    planned = read_json(project / PLANNED_STRUCTURE)  # 目录治理值

    # 返回 load_planned 的目录状态载荷。
    return planned if isinstance(planned, dict) else {}


# 定义 allowed_parent_paths 的目录状态处理入口。
def allowed_parent_paths(planned: dict[str, Any]) -> set[str]:

    # 收集 parents 目录状态条目。
    set_parents: set[str] = set()  # 目录治理值

    # 逐项检查 allowed_parent_paths 目录状态候选。
    for item in planned.get("allowed_new_paths", []):

        # 整理 allowed_parent_paths 需要的 normalized 目录状态信息。
        str_normalized = normalize_rel(item)  # 目录治理值

        # 校验 allowed_parent_paths 的目录状态分支。
        if not str_normalized:

            # 分隔 allowed_parent_paths 的控制流边界。
            continue

        # 收集 parts 目录状态条目。
        parts = str_normalized.split("/")  # 目录治理值

        # 逐项检查 allowed_parent_paths 目录状态候选。
        for index in range(1, len(parts)):

            # 调用 add 处理 allowed_parent_paths。
            set_parents.add("/".join(parts[:index]))

    # 返回 allowed_parent_paths 的目录状态载荷。
    return set_parents


# 定义 configured_root_optional_work_dirs 的目录状态处理入口。
def configured_root_optional_work_dirs(planned: dict[str, Any]) -> set[str]:

    # 整理 configured_root_optional_work_dirs 需要的 configured 目录状态信息。
    configured = planned.get("root_optional_work_dirs", [])  # 目录治理值

    # 收集 values 目录状态条目。
    values = {normalize_rel(item) for item in configured if normalize_rel(item)}  # 目录治理值

    # 返回 configured_root_optional_work_dirs 的目录状态载荷。
    return values or set(ROOT_OPTIONAL_WORK_DIRS)


# 定义 configured_root_optional_work_dir_prefixes 的目录状态处理入口。
def configured_root_optional_work_dir_prefixes(planned: dict[str, Any]) -> tuple[str, ...]:

    # 整理 configured_root_optional_work_dir_prefixes 需要的 configured 目录状态信息。
    configured = planned.get("root_optional_work_dir_prefixes", [])  # 目录治理值

    # 收集 values 目录状态条目。
    tuple_values = tuple(normalize_rel(item) for item in configured if normalize_rel(item))  # 目录治理值

    # 返回 configured_root_optional_work_dir_prefixes 的目录状态载荷。
    return tuple_values or ROOT_OPTIONAL_WORK_DIR_PREFIXES


# 定义 root_optional_work_dir_match 的目录状态处理入口。
def root_optional_work_dir_match(path: str, planned: dict[str, Any]) -> bool:

    # 整理 root_optional_work_dir_match 需要的 normalized 目录状态信息。
    str_normalized = normalize_rel(path)  # 目录治理值

    # 校验 root_optional_work_dir_match 的目录状态分支。
    if not str_normalized:

        # 返回 root_optional_work_dir_match 的目录状态载荷。
        return False

    # 整理 root_optional_work_dir_match 需要的 top level 目录状态信息。
    top_level = str_normalized.split("/", 1)[0]  # 目录治理值

    # 校验 root_optional_work_dir_match 的目录状态分支。
    if top_level in configured_root_optional_work_dirs(planned):

        # 返回 root_optional_work_dir_match 的目录状态载荷。
        return True

    # 返回 root_optional_work_dir_match 的目录状态载荷。
    return any(top_level.startswith(prefix) for prefix in configured_root_optional_work_dir_prefixes(planned))


# 定义 nested_workspace_artifact_reason 的目录状态处理入口。
def nested_workspace_artifact_reason(path: str, planned: dict[str, Any]) -> str | None:

    # 整理 nested_workspace_artifact_reason 需要的 normalized 目录状态信息。
    str_normalized = normalize_rel(path)  # 目录治理值

    # 整理 nested_workspace_artifact_reason 需要的 primary root 目录状态信息。
    str_primary_root = normalize_rel(str(planned.get("primary_project_root", "")).strip())  # 目录治理值

    # 校验 nested_workspace_artifact_reason 的目录状态分支。
    if not str_normalized or not str_primary_root:

        # 返回 nested_workspace_artifact_reason 的目录状态载荷。
        return None

    # 整理 nested_workspace_artifact_reason 需要的 prefix 目录状态信息。
    prefix = str_primary_root.rstrip("/") + "/"  # 目录治理值

    # 校验 nested_workspace_artifact_reason 的目录状态分支。
    if str_normalized == str_primary_root or not str_normalized.startswith(prefix):

        # 返回 nested_workspace_artifact_reason 的目录状态载荷。
        return None

    # 整理 nested_workspace_artifact_reason 需要的 relative 目录状态信息。
    relative = str_normalized[len(prefix) :]  # 目录治理值

    # 收集 components 目录状态条目。
    components = [part for part in relative.split("/") if part]  # 目录治理值

    # 校验 nested_workspace_artifact_reason 的目录状态分支。
    if not components:

        # 返回 nested_workspace_artifact_reason 的目录状态载荷。
        return None

    # 收集 allowed dirs 目录状态条目。
    set_allowed_dirs = configured_root_optional_work_dirs(planned)  # 目录治理值

    # 收集 prefixes 目录状态条目。
    tuple_prefixes = configured_root_optional_work_dir_prefixes(planned)  # 目录治理值

    # 逐项检查 nested_workspace_artifact_reason 目录状态候选。
    for component in components:

        # 校验 nested_workspace_artifact_reason 的目录状态分支。
        if component in set_allowed_dirs or any(component.startswith(prefix) for prefix in tuple_prefixes):

            # 返回 nested_workspace_artifact_reason 的目录状态载荷。
            return (
                f"workspace artifact directory must stay at the work-folder root, not under the primary project root: {str_normalized}"
            )

    # 返回 nested_workspace_artifact_reason 的目录状态载荷。
    return None


# 定义 allowed_path 的目录状态处理入口。
def allowed_path(path: str, planned: dict[str, Any]) -> bool:

    # 整理 allowed_path 需要的 normalized 目录状态信息。
    str_normalized = normalize_rel(path)  # 目录治理值

    # 校验 allowed_path 的目录状态分支。
    if root_optional_work_dir_match(str_normalized, planned):

        # 返回 allowed_path 的目录状态载荷。
        return True

    # 整理 allowed_path 需要的 allowed 目录状态信息。
    allowed = [normalize_rel(item) for item in planned.get("allowed_new_paths", []) if str(item).strip()]  # 目录治理值

    # 收集 parents 目录状态条目。
    set_parents = allowed_parent_paths(planned)  # 目录治理值

    # 校验 allowed_path 的目录状态分支。
    if str_normalized in set_parents:

        # 返回 allowed_path 的目录状态载荷。
        return True

    # 返回 allowed_path 的目录状态载荷。
    return any(str_normalized == item or str_normalized.startswith(item.rstrip("/") + "/") for item in allowed)


# 定义 allowed_root_files 的目录状态处理入口。
def allowed_root_files(planned: dict[str, Any]) -> list[str]:

    # 整理 allowed_root_files 需要的 configured 目录状态信息。
    configured = planned.get("allowed_root_files", [])  # 目录治理值

    # 校验 allowed_root_files 的目录状态分支。
    if isinstance(configured, list):

        # 收集 values 目录状态条目。
        values = [str(item).strip() for item in configured if str(item).strip()]  # 目录治理值

        # 校验 allowed_root_files 的目录状态分支。
        if values:

            # 返回 allowed_root_files 的目录状态载荷。
            return values

    # 返回 allowed_root_files 的目录状态载荷。
    return list(ALLOWED_ROOT_FILES)


# 定义 is_allowed_root_file 的目录状态处理入口。
def is_allowed_root_file(name: str, planned: dict[str, Any]) -> bool:

    # 整理 is_allowed_root_file 需要的 normalized 目录状态信息。
    normalized = str(name).strip()  # 目录治理值

    # 校验 is_allowed_root_file 的目录状态分支。
    if normalized in set(allowed_root_files(planned)):

        # 返回 is_allowed_root_file 的目录状态载荷。
        return True

    # 返回 is_allowed_root_file 的目录状态载荷。
    return any(fnmatch(normalized, pattern) for pattern in ALLOWED_ROOT_FILE_PATTERNS)


# 定义 unapproved_root_files 的目录状态处理入口。
def unapproved_root_files(current: dict[str, Any], planned: dict[str, Any]) -> list[str]:

    # 收集 violations 目录状态条目。
    list_violations: list[str] = []  # 目录治理值

    # 逐项检查 unapproved_root_files 目录状态候选。
    for file_path in current.get("files", []):

        # 整理 unapproved_root_files 需要的 normalized 目录状态信息。
        str_normalized = normalize_rel(file_path)  # 目录治理值

        # 校验 unapproved_root_files 的目录状态分支。
        if not str_normalized or "/" in str_normalized:

            # 分隔 unapproved_root_files 的控制流边界。
            continue

        # 校验 unapproved_root_files 的目录状态分支。
        if EPHEMERAL_ROOT_INPUT_FILE_RE.fullmatch(str_normalized):

            # 分隔 unapproved_root_files 的控制流边界。
            continue

        # 校验 unapproved_root_files 的目录状态分支。
        if not is_allowed_root_file(str_normalized, planned):

            # 整理 unapproved_root_files 需要的 explicit reason 目录状态信息。
            explicit_reason = workspace_settings_location_reason(str_normalized)  # 目录治理值

            # 追加 unapproved_root_files 的目录状态诊断。
            list_violations.append(explicit_reason or str_normalized)

    # 返回 unapproved_root_files 的目录状态载荷。
    return list_violations


# 定义 workspace_settings_structure_violations 的目录状态处理入口。
def workspace_settings_structure_violations(current: dict[str, Any]) -> list[str]:

    # 收集 violations 目录状态条目。
    list_violations: list[str] = []  # 目录治理值

    # 逐项检查 workspace_settings_structure_violations 目录状态候选。
    for file_path in current.get("files", []):

        # 整理 workspace_settings_structure_violations 需要的 normalized 目录状态信息。
        str_normalized = normalize_rel(file_path)  # 目录治理值

        # 校验 workspace_settings_structure_violations 的目录状态分支。
        if not str_normalized:

            # 分隔 workspace_settings_structure_violations 的控制流边界。
            continue

        # 整理 workspace_settings_structure_violations 需要的 reason 目录状态信息。
        reason = workspace_settings_location_reason(str_normalized)  # 目录治理值

        # 校验 workspace_settings_structure_violations 的目录状态分支。
        if reason:

            # 追加 workspace_settings_structure_violations 的目录状态诊断。
            list_violations.append(reason)

    # 返回 workspace_settings_structure_violations 的目录状态载荷。
    return sorted(dict.fromkeys(list_violations))


# 定义 verify_json 的目录状态处理入口。
def verify_json(path: Path, errors: list[str]) -> dict[str, Any]:

    # 整理 verify_json 需要的 data 目录状态信息。
    dict_data = read_json(path)  # 目录治理值

    # 校验 verify_json 的目录状态分支。
    if not isinstance(dict_data, dict) or not dict_data:

        # 追加 verify_json 的目录状态诊断。
        errors.append(f"{path.as_posix()}: missing or invalid JSON object")

        # 返回 verify_json 的目录状态载荷。
        return {}

    # 返回 verify_json 的目录状态载荷。
    return dict_data


# 定义 verify_remote_deployment_policy 的目录状态处理入口。
def verify_remote_deployment_policy(planned: dict[str, Any], list_errors: list[str]) -> None:
    """校验 planned-structure 中的 remote_deployment 治理契约。

    数组契约:
        shape/维度: 本函数处理目录治理 JSON 映射，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict 和 list 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义来自 planned-structure schema。
    """

    # 整理 verify_remote_deployment_policy 需要的 remote 目录状态信息。
    remote = planned.get("remote_deployment") if planned else None  # 目录治理值

    # 校验 verify_remote_deployment_policy 的目录状态分支。
    if planned and not isinstance(remote, dict):

        # 追加 verify_remote_deployment_policy 的目录状态诊断。
        list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment must be configured")

    # 校验 verify_remote_deployment_policy 的目录状态分支。
    if isinstance(remote, dict):

        # 校验 verify_remote_deployment_policy 的目录状态分支。
        if not remote.get("workspace_root"):

            # 追加 verify_remote_deployment_policy 的目录状态诊断。
            list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.workspace_root must be configured or `not configured`")

        # 校验 verify_remote_deployment_policy 的目录状态分支。
        if not isinstance(remote.get("planned_structure"), list):

            # 追加 verify_remote_deployment_policy 的目录状态诊断。
            list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.planned_structure must be a list")

        # 校验 verify_remote_deployment_policy 的目录状态分支。
        if not isinstance(remote.get("conda_environment"), dict):

            # 追加 verify_remote_deployment_policy 的目录状态诊断。
            list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.conda_environment must be configured")

        # 校验 verify_remote_deployment_policy 的目录状态分支。
        if not isinstance(remote.get("runtime_artifacts"), dict):

            # 追加 verify_remote_deployment_policy 的目录状态诊断。
            list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.runtime_artifacts must be configured")

        # 校验 verify_remote_deployment_policy 的目录状态分支。
        if not isinstance(remote.get("review_required_for"), list):

            # 追加 verify_remote_deployment_policy 的目录状态诊断。
            list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.review_required_for must be a list")

        # 校验 verify_remote_deployment_policy 的目录状态分支。
        if not isinstance(remote.get("protected_path_classes"), list):

            # 追加 verify_remote_deployment_policy 的目录状态诊断。
            list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.protected_path_classes must be a list")

        # 校验 verify_remote_deployment_policy 的目录状态分支。
        if remote.get("require_review_for_all_mutations") is not True:

            # 追加 verify_remote_deployment_policy 的目录状态诊断。
            list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.require_review_for_all_mutations must be true")

        # 整理 verify_remote_deployment_policy 需要的 conda 目录状态信息。
        conda = remote.get("conda_environment", {}) if isinstance(remote.get("conda_environment"), dict) else {}  # 目录治理值

        # 整理 verify_remote_deployment_policy 需要的 runtime 目录状态信息。
        runtime = remote.get("runtime_artifacts", {}) if isinstance(remote.get("runtime_artifacts"), dict) else {}  # 目录治理值

        # 校验 verify_remote_deployment_policy 的目录状态分支。
        if isinstance(conda, dict) and "path_template" not in conda:

            # 追加 verify_remote_deployment_policy 的目录状态诊断。
            list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.conda_environment.path_template must be configured")

        # 校验 verify_remote_deployment_policy 的目录状态分支。
        if isinstance(runtime, dict):

            # 逐项检查 verify_remote_deployment_policy 目录状态候选。
            for key in ["active_path_template", "backup_path_template", "run_id_required", "archive_after_verification", "archive_trigger"]:

                # 校验 verify_remote_deployment_policy 的目录状态分支。
                if key not in runtime:

                    # 追加 verify_remote_deployment_policy 的目录状态诊断。
                    list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: remote_deployment.runtime_artifacts.{key} must be configured")



# 定义 verify_dir_manager 的目录状态处理入口。
def verify_dir_manager(project: Path) -> dict[str, Any]:

    # 收集 errors 目录状态条目。
    list_errors: list[str] = []  # 目录治理值

    # 收集 checked 目录状态条目。
    list_checked = [  # 目录治理值
        str(DIR_MANAGER_DIR.as_posix()),  # 目录治理值
        str(CHANGE_REVIEWS.as_posix()),  # 目录治理值
        str(HISTORY_DIR_MANAGER.as_posix()),  # 目录治理值
        str(DIR_MANAGER_MD.as_posix()),  # 目录治理值
        str(CURRENT_STRUCTURE.as_posix()),  # 目录治理值
        str(PLANNED_STRUCTURE.as_posix()),  # 目录治理值
    ]

    # 逐项检查 verify_dir_manager 目录状态候选。
    for rel in [DIR_MANAGER_DIR, CHANGE_REVIEWS, HISTORY_DIR_MANAGER]:

        # 校验 verify_dir_manager 的目录状态分支。
        if not (project / rel).is_dir():

            # 追加 verify_dir_manager 的目录状态诊断。
            list_errors.append(f"missing dir manager directory: {rel.as_posix()}")

    # 逐项检查 verify_dir_manager 目录状态候选。
    for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]:

        # 校验 verify_dir_manager 的目录状态分支。
        if not (project / rel).is_file():

            # 追加 verify_dir_manager 的目录状态诊断。
            list_errors.append(f"missing dir manager file: {rel.as_posix()}")

    # 整理 verify_dir_manager 需要的 current 目录状态信息。
    current = verify_json(project / CURRENT_STRUCTURE, list_errors) if (project / CURRENT_STRUCTURE).exists() else {}  # 目录治理值

    # 整理 verify_dir_manager 需要的 planned 目录状态信息。
    planned = verify_json(project / PLANNED_STRUCTURE, list_errors) if (project / PLANNED_STRUCTURE).exists() else {}  # 目录治理值

    # 逐项检查 verify_dir_manager 目录状态候选。
    for key in ["directories", "files"]:

        # 校验 verify_dir_manager 的目录状态分支。
        if current and not isinstance(current.get(key), list):

            # 追加 verify_dir_manager 的目录状态诊断。
            list_errors.append(f"{CURRENT_STRUCTURE.as_posix()}: `{key}` must be a list")

    # 逐项检查 verify_dir_manager 目录状态候选。
    for key in ["allowed_new_paths", "review_required_for", "allowed_root_files"]:

        # 校验 verify_dir_manager 的目录状态分支。
        if planned and not isinstance(planned.get(key), list):

            # 追加 verify_dir_manager 的目录状态诊断。
            list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: `{key}` must be a list")

    # 校验 verify_dir_manager 的目录状态分支。
    if planned and not isinstance(planned.get("workspace_settings"), dict):

        # 追加 verify_dir_manager 的目录状态诊断。
        list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: `workspace_settings` must be configured")

    # 校验 verify_dir_manager 的目录状态分支。
    if planned and not isinstance(planned.get("allowed_top_level_roots"), list):

        # 追加 verify_dir_manager 的目录状态诊断。
        list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: `allowed_top_level_roots` must be a list")

    # 校验 verify_dir_manager 的目录状态分支。
    if planned and not planned.get("block_on_failed_review", False):

        # 追加 verify_dir_manager 的目录状态诊断。
        list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: block_on_failed_review must be true")

    # 校验 verify_dir_manager 的目录状态分支。
    if planned and not planned.get("force_override_archive"):

        # 追加 verify_dir_manager 的目录状态诊断。
        list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: force_override_archive must be configured")

    # 校验 planned-structure 中的远程部署治理契约。
    verify_remote_deployment_policy(planned, list_errors)

    # 校验 verify_dir_manager 的目录状态分支。
    if current and planned:

        # 整理 verify_dir_manager 需要的 settings policy 目录状态信息。
        settings_policy = planned.get("workspace_settings", {}) if isinstance(planned.get("workspace_settings"), dict) else {}  # 目录治理值

        # 校验 verify_dir_manager 的目录状态分支。
        if settings_policy:

            # 校验 verify_dir_manager 的目录状态分支。
            if str(settings_policy.get("folder", "")).strip() != SETTINGS_FOLDER:

                # 追加 verify_dir_manager 的目录状态诊断。
                list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: workspace_settings.folder must be `{SETTINGS_FOLDER}`")

            # 校验 verify_dir_manager 的目录状态分支。
            if str(settings_policy.get("local_default_file", "")).strip() != f"{SETTINGS_FOLDER}/project.local.json":

                # 追加 verify_dir_manager 的目录状态诊断。
                list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: workspace_settings.local_default_file must be `{SETTINGS_FOLDER}/project.local.json`")

            # 校验 verify_dir_manager 的目录状态分支。
            if str(settings_policy.get("remote_default_file", "")).strip() != REMOTE_DEFAULT_SETTINGS:

                # 追加 verify_dir_manager 的目录状态诊断。
                list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: workspace_settings.remote_default_file must be `{REMOTE_DEFAULT_SETTINGS}`")

            # 校验 verify_dir_manager 的目录状态分支。
            if bool(settings_policy.get("local_files_remote_blocked")) is not True:

                # 追加 verify_dir_manager 的目录状态诊断。
                list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: workspace_settings.local_files_remote_blocked must be true")

        # 整理 verify_dir_manager 需要的 primary root 目录状态信息。
        str_primary_root = normalize_rel(str(planned.get("primary_project_root", "")).strip())  # 目录治理值

        # 校验 verify_dir_manager 的目录状态分支。
        if planned.get("enforce_primary_project_root") and str_primary_root:

            # 校验 verify_dir_manager 的目录状态分支。
            bool_primary_root_missing = (  # 主项目根目录未出现在当前目录快照
                str_primary_root not in current.get("directories", [])  # 当前目录快照未直接包含主根
                and not any(path.startswith(str_primary_root + "/") for path in current.get("directories", []))  # 当前目录快照未包含主根子项
            )

            # 检查主项目根目录是否已经落在当前结构中。
            if bool_primary_root_missing:

                # 追加 verify_dir_manager 的目录状态诊断。
                list_errors.append(f"{PLANNED_STRUCTURE.as_posix()}: required primary project root is missing: {str_primary_root}/")

        # 逐项检查 verify_dir_manager 目录状态候选。
        for directory in current.get("directories", []):

            # 整理 verify_dir_manager 需要的 normalized 目录状态信息。
            str_normalized = normalize_rel(directory)  # 目录治理值

            # 校验 verify_dir_manager 的目录状态分支。
            if not str_normalized:

                # 分隔 verify_dir_manager 的控制流边界。
                continue

            # 整理 verify_dir_manager 需要的 nested reason 目录状态信息。
            nested_reason = nested_workspace_artifact_reason(str_normalized, planned)  # 目录治理值

            # 校验 verify_dir_manager 的目录状态分支。
            if nested_reason:

                # 追加 verify_dir_manager 的目录状态诊断。
                list_errors.append(f"{CURRENT_STRUCTURE.as_posix()}: {nested_reason}")

                # 分隔 verify_dir_manager 的控制流边界。
                continue

            # 校验 verify_dir_manager 的目录状态分支。
            if not allowed_path(str_normalized, planned):

                # 追加 verify_dir_manager 的目录状态诊断。
                list_errors.append(f"{CURRENT_STRUCTURE.as_posix()}: directory violates planned structure: {str_normalized}")

        # 调用 extend 处理 verify_dir_manager。
        list_errors.extend(f"{CURRENT_STRUCTURE.as_posix()}: {item}" for item in workspace_settings_structure_violations(current))

        # 逐项检查 verify_dir_manager 目录状态候选。
        for file_path in unapproved_root_files(current, planned):

            # 追加 verify_dir_manager 的目录状态诊断。
            list_errors.append(f"{CURRENT_STRUCTURE.as_posix()}: root-level file violates planned structure: {file_path}")

    # 返回 verify_dir_manager 的目录状态载荷。
    return {"project": str(project), "checked": list_checked, "errors": list_errors}


# 定义 init_dir_manager 的目录状态处理入口。
def init_dir_manager(project: Path) -> dict[str, Any]:

    # 整理 init_dir_manager 需要的 target 目录状态信息。
    target = project / DIR_MANAGER_DIR  # 目录治理值

    # 调用 mkdir 处理 init_dir_manager。
    target.mkdir(parents=True, exist_ok=True)

    # 调用 mkdir 处理 init_dir_manager。
    (project / CHANGE_REVIEWS).mkdir(parents=True, exist_ok=True)

    # 调用 mkdir 处理 init_dir_manager。
    (project / HISTORY_DIR_MANAGER).mkdir(parents=True, exist_ok=True)

    # 校验 init_dir_manager 的目录状态分支。
    if not (project / DIR_MANAGER_MD).exists():

        # 调用 write_text 处理 init_dir_manager。
        (project / DIR_MANAGER_MD).write_text(dir_manager_doc(project), encoding="utf-8")

    # 保存 desired planned 映射，维持 init_dir_manager 的字段关系。
    dict_desired_planned = planned_structure(project)  # 目录治理值

    # 校验 init_dir_manager 的目录状态分支。
    if not (project / PLANNED_STRUCTURE).exists():

        # 调用 write_text 处理 init_dir_manager。
        (project / PLANNED_STRUCTURE).write_text(
            json.dumps(dict_desired_planned, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    else:

        # 保存 planned 映射，维持 init_dir_manager 的字段关系。
        dict_planned = load_planned(project)  # 目录治理值

        # 收集 primary root、configured paths、enforce primary 目录状态条目。
        tuple_primary_root, tuple_configured_paths, tuple_enforce_primary = profile_layout_policy(project)  # 目录治理值

        # 保存 rewritten 映射，维持 init_dir_manager 的字段关系。
        dict_rewritten = dict(dict_planned)  # 目录治理值

        # 标记 changed 判断，控制 init_dir_manager 的分支走向。
        bool_changed = False  # 目录治理值

        # 整理 init_dir_manager 需要的 remote plan 目录状态信息。
        remote_plan = dict_desired_planned.get("remote_deployment", {})  # 目录治理值

        # 校验 init_dir_manager 的目录状态分支。
        if dict_rewritten.get("remote_deployment") != remote_plan:

            # 整理 init_dir_manager 需要的 中间载荷 目录状态信息。
            dict_rewritten["remote_deployment"] = remote_plan  # 目录治理值

            # 标记 changed 判断，控制 init_dir_manager 的分支走向。
            bool_changed = True  # 目录治理值

        # 校验 init_dir_manager 的目录状态分支。
        if tuple_configured_paths:

            # 保存 current compare 映射，维持 init_dir_manager 的字段关系。
            dict_current_compare = dict(dict_planned)  # 目录治理值

            # 保存 desired compare 映射，维持 init_dir_manager 的字段关系。
            dict_desired_compare = dict(dict_desired_planned)  # 目录治理值

            # 调用 pop 处理 init_dir_manager。
            dict_current_compare.pop("generated_at", None)

            # 调用 pop 处理 init_dir_manager。
            dict_desired_compare.pop("generated_at", None)

            # 校验 init_dir_manager 的目录状态分支。
            if dict_current_compare != dict_desired_compare:

                # 保存 rewritten 映射，维持 init_dir_manager 的字段关系。
                dict_rewritten = dict_desired_planned  # 目录治理值

                # 标记 changed 判断，控制 init_dir_manager 的分支走向。
                bool_changed = True  # 目录治理值
        else:

            # 整理 init_dir_manager 需要的 current allowed 目录状态信息。
            current_allowed = [  # 目录治理值
                normalize_rel(item)  # 目录治理值
                for item in dict_rewritten.get("allowed_new_paths", [])  # 目录治理值
                if str(item).strip()  # 目录治理值
            ]

            # 整理 init_dir_manager 需要的 derived top 目录状态信息。
            derived_top = sorted({item.split("/", 1)[0] + "/" for item in current_allowed if item})  # 目录治理值

            # 校验 init_dir_manager 的目录状态分支。
            if dict_rewritten.get("allowed_top_level_roots") != derived_top:

                # 整理 init_dir_manager 需要的 中间载荷 目录状态信息。
                dict_rewritten["allowed_top_level_roots"] = derived_top  # 目录治理值

                # 标记 changed 判断，控制 init_dir_manager 的分支走向。
                bool_changed = True  # 目录治理值

            # 校验 init_dir_manager 的目录状态分支。
            if dict_rewritten.get("primary_project_root", "") != tuple_primary_root:

                # 整理 init_dir_manager 需要的 中间载荷 目录状态信息。
                dict_rewritten["primary_project_root"] = tuple_primary_root  # 目录治理值

                # 标记 changed 判断，控制 init_dir_manager 的分支走向。
                bool_changed = True  # 目录治理值

            # 校验 init_dir_manager 的目录状态分支。
            if dict_rewritten.get("enforce_primary_project_root", False) != tuple_enforce_primary:

                # 整理 init_dir_manager 需要的 中间载荷 目录状态信息。
                dict_rewritten["enforce_primary_project_root"] = tuple_enforce_primary  # 目录治理值

                # 标记 changed 判断，控制 init_dir_manager 的分支走向。
                bool_changed = True  # 目录治理值

            # 校验 init_dir_manager 的目录状态分支。
            if dict_rewritten.get("allowed_root_files") != dict_desired_planned.get("allowed_root_files"):

                # 整理 init_dir_manager 需要的 中间载荷 目录状态信息。
                dict_rewritten["allowed_root_files"] = dict_desired_planned.get("allowed_root_files", [])  # 目录治理值

                # 标记 changed 判断，控制 init_dir_manager 的分支走向。
                bool_changed = True  # 目录治理值

        # 校验 init_dir_manager 的目录状态分支。
        if bool_changed:

            # 整理 init_dir_manager 需要的 中间载荷 目录状态信息。
            dict_rewritten["generated_at"] = dict_desired_planned["generated_at"]  # 目录治理值

            # 调用 write_text 处理 init_dir_manager。
            (project / PLANNED_STRUCTURE).write_text(json.dumps(dict_rewritten, indent=2, sort_keys=True), encoding="utf-8")

    # 保存 structure 映射，维持 init_dir_manager 的字段关系。
    dict_structure = scan_structure(project)  # 目录治理值

    # 调用 write_text 处理 init_dir_manager。
    (project / CURRENT_STRUCTURE).write_text(json.dumps(dict_structure, indent=2, sort_keys=True), encoding="utf-8")

    # 保存 verify 映射，维持 init_dir_manager 的字段关系。
    dict_verify = verify_dir_manager(project)  # 目录治理值

    # 返回 init_dir_manager 的目录状态载荷。
    return {"project": str(project), "written": [str(DIR_MANAGER_MD), str(CURRENT_STRUCTURE), str(PLANNED_STRUCTURE)], "errors": dict_verify["errors"]}


# 定义 archive_dir_manager 的目录状态处理入口。
def archive_dir_manager(project: Path, reason: str = "", review_file: str | None = None) -> dict[str, Any]:

    # 校验 archive_dir_manager 的目录状态分支。
    if not all((project / rel).exists() for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]):

        # 调用 init_dir_manager 处理 archive_dir_manager。
        init_dir_manager(project)

    # 调用 mkdir 处理 archive_dir_manager。
    (project / HISTORY_DIR_MANAGER).mkdir(parents=True, exist_ok=True)

    # 整理 archive_dir_manager 需要的 archive root 目录状态信息。
    archive_root = project / HISTORY_DIR_MANAGER / stamp()  # 目录治理值

    # 调用 mkdir 处理 archive_dir_manager。
    archive_root.mkdir(parents=True, exist_ok=False)

    # 收集 archived 目录状态条目。
    list_archived: list[str] = []  # 目录治理值

    # 逐项检查 archive_dir_manager 目录状态候选。
    for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]:

        # 整理 archive_dir_manager 需要的 source 目录状态信息。
        source = project / rel  # 目录治理值

        # 校验 archive_dir_manager 的目录状态分支。
        if source.is_file():

            # 整理 archive_dir_manager 需要的 target 目录状态信息。
            target = archive_root / rel.name  # 目录治理值

            # 调用 write_bytes 处理 archive_dir_manager。
            target.write_bytes(source.read_bytes())

            # 追加 archive_dir_manager 的目录状态诊断。
            list_archived.append(str(target.relative_to(project).as_posix()))

    # 校验 archive_dir_manager 的目录状态分支。
    if (project / CHANGE_REVIEWS).is_dir():

        # 整理 archive_dir_manager 需要的 reviews target 目录状态信息。
        reviews_target = archive_root / CHANGE_REVIEWS.name  # 目录治理值

        # 调用 mkdir 处理 archive_dir_manager。
        reviews_target.mkdir(parents=True, exist_ok=True)

        # 逐项检查 archive_dir_manager 目录状态候选。
        for review in sorted((project / CHANGE_REVIEWS).glob("*.json")):

            # 整理 archive_dir_manager 需要的 target 目录状态信息。
            target = reviews_target / review.name  # 目录治理值

            # 调用 write_bytes 处理 archive_dir_manager。
            target.write_bytes(review.read_bytes())

            # 追加 archive_dir_manager 的目录状态诊断。
            list_archived.append(str(target.relative_to(project).as_posix()))

    # 保存 manifest 映射，维持 archive_dir_manager 的字段关系。
    dict_manifest = {  # 目录治理值
        "archived_at": datetime.now().isoformat(timespec="seconds"),  # 目录治理值
        "reason": reason or "force-confirmed directory override",  # 目录治理值
        "review_file": review_file or "",  # 目录治理值
        "archived_files": list_archived,  # 目录治理值
        "required_before": "applying any user force-confirmed blocked directory structure change",  # 目录治理值
    }

    # 定位 manifest path 的文件边界，供 archive_dir_manager 后续读写校验使用。
    manifest_path = archive_root / "archive_manifest.json"  # 目录治理值

    # 调用 write_text 处理 archive_dir_manager。
    manifest_path.write_text(json.dumps(dict_manifest, indent=2, sort_keys=True), encoding="utf-8")

    # 追加 archive_dir_manager 的目录状态诊断。
    list_archived.append(str(manifest_path.relative_to(project).as_posix()))

    # 返回 archive_dir_manager 的目录状态载荷。
    return {"project": str(project), "archive_dir": str(archive_root), "archived": list_archived}


