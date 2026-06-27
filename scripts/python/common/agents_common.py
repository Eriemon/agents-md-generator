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

# 导入 AGENTS 共享工具 所需的依赖模块。
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime

# 分隔当前密集代码块，保留原有执行顺序。
from pathlib import Path
from typing import Any


# 保留 SKIP DIRS 中间值，支撑 模块入口 的当前计算步骤。
SKIP_DIRS = {  # SKIP DIRS 用于本步治理判断
    ".git",  # SKIP DIRS 用于本步治理判断
    ".hg",  # SKIP DIRS 用于本步治理判断
    ".svn",  # SKIP DIRS 用于本步治理判断
    ".cache",  # SKIP DIRS 用于本步治理判断
    ".venv",  # SKIP DIRS 用于本步治理判断
    "__pycache__",  # SKIP DIRS 用于本步治理判断
    "node_modules",  # SKIP DIRS 用于本步治理判断
    "vendor",  # SKIP DIRS 用于本步治理判断
    "dist",  # SKIP DIRS 用于本步治理判断
    "build",  # SKIP DIRS 用于本步治理判断
    "target",  # SKIP DIRS 用于本步治理判断
    "ref",  # SKIP DIRS 用于本步治理判断
}

# 保留 AGENTS METADATA RE 中间值，支撑 模块入口 的当前计算步骤。
AGENTS_METADATA_RE = re.compile(r"<!--\s*AGENTS-METADATA:\s*(.*?)\s*-->", flags=re.IGNORECASE)  # AGENTS METADATA RE 用于本步治理判断

# 保留 AGENTS METADATA PAIR RE 中间值，支撑 模块入口 的当前计算步骤。
AGENTS_METADATA_PAIR_RE = re.compile(r"([a-zA-Z0-9_]+)\s*=\s*([^;]+)")  # AGENTS METADATA PAIR RE 用于本步治理判断

# 保留 RELEASE CORE WORKTREE RULE 中间值，支撑 模块入口 的当前计算步骤。
RELEASE_CORE_WORKTREE_RULE = (
    "Do not repoint repositories with `git config core.worktree`; use normal "  # AGENTS 长文本片段
    "checkout/merge or explicit `git worktree` commands instead."  # AGENTS 长文本片段
)

# 保留 GLOBAL CODEX AGENTS PREAMBLE 中间值，支撑 模块入口 的当前计算步骤。
GLOBAL_CODEX_AGENTS_PREAMBLE = "<!-- Managed by agents-md-generator: keep manual notes outside the managed global baseline block. -->"  # GLOBAL CODEX AGENTS PREAMBLE 用于本步治理判断

# 保留 GLOBAL CODEX AGENTS META 中间值，支撑 模块入口 的当前计算步骤。
GLOBAL_CODEX_AGENTS_META = "<!-- AGENTS-GENERATED:META generator=agents-md-generator schema=1 baseline=global-codex-baseline baseline_version=3 -->"  # GLOBAL CODEX AGENTS META 用于本步治理判断

# 保留 GLOBAL CODEX AGENTS BLOCK START 中间值，支撑 模块入口 的当前计算步骤。
GLOBAL_CODEX_AGENTS_BLOCK_START = "<!-- AGENTS-GENERATED:START global-codex-baseline -->"  # GLOBAL CODEX AGENTS BLOCK START 用于本步治理判断

# 保留 GLOBAL CODEX AGENTS BLOCK END 中间值，支撑 模块入口 的当前计算步骤。
GLOBAL_CODEX_AGENTS_BLOCK_END = "<!-- AGENTS-GENERATED:END global-codex-baseline -->"  # GLOBAL CODEX AGENTS BLOCK END 用于本步治理判断

# 保留 INSTALLED GOVERNANCE RUNTIME PLACEHOLDER 中间值，支撑 模块入口 的当前计算步骤。
INSTALLED_GOVERNANCE_RUNTIME_PLACEHOLDER = "<codex-home>/skills/agents-md-generator"  # INSTALLED GOVERNANCE RUNTIME PLACEHOLDER 用于本步治理判断

SCRIPT_TASK_BY_NAME = {  # SCRIPT TASK BY NAME 用于本步治理判断
    "inspect_project.py": "detect",
    "detect_scopes.py": "detect",
    "extract_commands.py": "detect",
    "extract_context.py": "detect",
    "check_freshness.py": "detect",
    "codex_token_usage_review.py": "detect",
    "task_rating_gate.py": "detect",
    "collect_design_profile.py": "design",
    "design_questions.py": "design",
    "design_profile_builder.py": "design",
    "design_profile_contracts.py": "design",
    "design_remote_gate.py": "design",
    "design_review_gate.py": "design",
    "design_takeover.py": "design",
    "design_interview_state.py": "design",
    "design_interview_payload.py": "design",
    "render_agents.py": "render",
    "create_agent_shims.py": "render",
    "manage_docs.py": "docs",
    "manage_docs_shared.py": "docs",
    "manage_docs_memory.py": "docs",
    "manage_docs_release.py": "docs",
    "manage_docs_scaffold_session.py": "docs",
    "manage_docs_sync_verify.py": "docs",
    "manage_dirs.py": "dirs",
    "manage_dirs_state.py": "dirs",
    "manage_dirs_review.py": "dirs",
    "manage_dirs_remote.py": "dirs",
    "quick_validate.py": "verify",
    "audit_skill.py": "verify",
    "verify_agents.py": "verify",
    "verify_agents_policy.py": "verify",
    "evaluate_skill.py": "verify",
    "check_source_governance.py": "verify",
    "source_governance.py": "verify",
    "source_governance_config.py": "verify",
    "review_governance.py": "verify",
    "run_confidence_gate.py": "verify",
    "run_skill_evals.py": "verify",
    "eval_runtime_core.py": "verify",
    "eval_runtime_foundation_cases.py": "verify",
    "eval_runtime_policy_cases.py": "verify",
    "eval_runtime_fixtures.py": "verify",
    "install_skill.py": "release",
    "release_content_policy.py": "release",
    "select_engineering_rules.py": "release",
    "agents_common.py": "common",
    "agents_decisions.py": "common",
    "agents_project_facts.py": "common",
    "workspace_settings_policy.py": "common",
}


# 定义 resolve_project 的AGENTS 共享工具处理入口。
def resolve_project(raw: str | Path) -> Path:

    # 保留 project 中间值，支撑 resolve_project 的当前计算步骤。
    project = Path(raw).resolve()  # project 用于本步治理判断

    # 检查 resolve_project 的当前条件是否需要进入专门分支。
    if not project.exists() or not project.is_dir():

        # 抛出 resolve_project 已确认的阻断原因。
        raise SystemExit(f"Project directory does not exist: {project}")

    # 返回 resolve_project 已整理完成的调用载荷。
    return project

# 定义 emit_json 的AGENTS 共享工具处理入口。
def emit_json(data: dict[str, Any]) -> None:

    # 调用 print 完成 emit_json 的当前动作。
    print(json.dumps(data, indent=2, sort_keys=True))

# 定义 read_json 的AGENTS 共享工具处理入口。
def read_json(path: Path) -> dict[str, Any]:

    # 保护 read_json 中允许失败的外部访问。
    try:

        # 返回 read_json 已整理完成的调用载荷。
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:

        # 返回 read_json 已整理完成的调用载荷。
        return {}

# 定义 codex_home_root 的AGENTS 共享工具处理入口。
def codex_home_root(raw: str | None = None) -> Path:

    # 保留 env home 中间值，支撑 codex_home_root 的当前计算步骤。
    env_home = raw.strip() if raw else os.environ.get("CODEX_HOME", "").strip()  # env home 用于本步治理判断

    # 检查 codex_home_root 的当前条件是否需要进入专门分支。
    if env_home:

        # 返回 codex_home_root 已整理完成的调用载荷。
        return Path(env_home).expanduser().resolve()

    # 返回 codex_home_root 已整理完成的调用载荷。
    return (Path.home() / ".codex").resolve()

# 定义 codex_sessions_root 的AGENTS 共享工具处理入口。
def codex_sessions_root() -> Path:

    # 返回 codex_sessions_root 已整理完成的调用载荷。
    return codex_home_root() / "sessions"

# 定义 skill_root 的AGENTS 共享工具处理入口。
def skill_root() -> Path:

    # 返回 skill_root 已整理完成的调用载荷。
    return Path(__file__).resolve().parents[3]


# 定义 governance_skill_name 的AGENTS 共享工具处理入口。
def governance_skill_name() -> str:

    # 返回 governance_skill_name 已整理完成的调用载荷。
    return "agents-md-generator"

# 定义 skill_version_file 的AGENTS 共享工具处理入口。
def skill_version_file(root: Path | None = None) -> Path:

    # 返回 skill_version_file 已整理完成的调用载荷。
    return (root or skill_root()) / "VERSION"

# 定义 read_skill_version 的AGENTS 共享工具处理入口。
def read_skill_version(root: Path | None = None) -> str:

    # 保留 path 中间值，支撑 read_skill_version 的当前计算步骤。
    path_path = skill_version_file(root)  # path 用于本步治理判断

    # 检查 read_skill_version 的当前条件是否需要进入专门分支。
    if not path_path.exists():

        # 返回 read_skill_version 已整理完成的调用载荷。
        return ""

    # 返回 read_skill_version 已整理完成的调用载荷。
    return path_path.read_text(encoding="utf-8", errors="ignore").strip()

# 定义 installed_skill_dir 的AGENTS 共享工具处理入口。
def installed_skill_dir(skill_name: str = "agents-md-generator", override_dir: str | Path | None = None) -> Path | None:

    # 保留 override 中间值，支撑 installed_skill_dir 的当前计算步骤。
    override = str(override_dir).strip() if override_dir is not None else os.environ.get("AGENTS_MD_INSTALLED_SKILL_DIR", "").strip()  # override 用于本步治理判断

    # 检查 installed_skill_dir 的当前条件是否需要进入专门分支。
    if override:

        # 保留 path 中间值，支撑 installed_skill_dir 的当前计算步骤。
        path = Path(override).expanduser().resolve()  # path 用于本步治理判断

        # 返回 installed_skill_dir 已整理完成的调用载荷。
        return path if path.exists() else None

    # 保留 codex home 中间值，支撑 installed_skill_dir 的当前计算步骤。
    codex_home = os.environ.get("CODEX_HOME", "").strip()  # codex home 用于本步治理判断

    # 保留 home root 中间值，支撑 installed_skill_dir 的当前计算步骤。
    home_root = Path(codex_home).expanduser().resolve() if codex_home else (Path.home() / ".codex").resolve()  # home root 用于本步治理判断

    # 保留 path 中间值，支撑 installed_skill_dir 的当前计算步骤。
    path = home_root / "skills" / skill_name  # path 用于本步治理判断

    # 返回 installed_skill_dir 已整理完成的调用载荷。
    return path if path.exists() else None


# 定义 current_governance_skill_dirs 的AGENTS 共享工具处理入口。
def current_governance_skill_dirs(skill_name: str | None = None, override_dir: str | Path | None = None) -> list[Path]:

    # 保留 target name 中间值，支撑 current_governance_skill_dirs 的当前计算步骤。
    target_name = skill_name or governance_skill_name()  # target name 用于本步治理判断

    # 收集 dirs 条目，保持 current_governance_skill_dirs 的处理顺序稳定。
    list_dirs: list[Path] = []  # dirs 用于本步治理判断

    # 保留 runtime 中间值，支撑 current_governance_skill_dirs 的当前计算步骤。
    runtime = skill_root().resolve()  # runtime 用于本步治理判断

    # 调用 append 完成 current_governance_skill_dirs 的当前动作。
    list_dirs.append(runtime)

    # 保留 installed 中间值，支撑 current_governance_skill_dirs 的当前计算步骤。
    installed = installed_skill_dir(target_name, override_dir=override_dir)  # installed 用于本步治理判断

    # 检查 current_governance_skill_dirs 的当前条件是否需要进入专门分支。
    if installed is not None:

        # 保留 installed resolved 中间值，支撑 current_governance_skill_dirs 的当前计算步骤。
        installed_resolved = installed.resolve()  # installed resolved 用于本步治理判断

        # 检查 current_governance_skill_dirs 的当前条件是否需要进入专门分支。
        if all(existing != installed_resolved for existing in list_dirs):

            # 调用 append 完成 current_governance_skill_dirs 的当前动作。
            list_dirs.append(installed_resolved)

    # 返回 current_governance_skill_dirs 已整理完成的调用载荷。
    return list_dirs


# 定义 source_repo_governance_owner_candidate 的AGENTS 共享工具处理入口。
def source_repo_governance_owner_candidate(project: Path, candidate: Path, target_name: str) -> bool:

    # 保留 skill md 中间值，支撑 source_repo_governance_owner_candidate 的当前计算步骤。
    skill_md = candidate / "SKILL.md"  # skill md 用于本步治理判断

    # 检查 source_repo_governance_owner_candidate 的当前条件是否需要进入专门分支。
    if not skill_md.is_file() or not (candidate / "VERSION").is_file():

        # 返回 source_repo_governance_owner_candidate 已整理完成的调用载荷。
        return False

    # 保留 text 中间值，支撑 source_repo_governance_owner_candidate 的当前计算步骤。
    text = skill_md.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

    # 检查 source_repo_governance_owner_candidate 的当前条件是否需要进入专门分支。
    if not re.search(rf"(?m)^name:\s*{re.escape(target_name)}\s*$", text):

        # 返回 source_repo_governance_owner_candidate 已整理完成的调用载荷。
        return False

    # 定位 profile path 的文件边界，供 source_repo_governance_owner_candidate 后续读写校验使用。
    profile_path = project / ".agents" / "agents-control.json"  # profile path 用于本步治理判断

    # 检查 source_repo_governance_owner_candidate 的当前条件是否需要进入专门分支。
    if profile_path.is_file():

        # 保护 source_repo_governance_owner_candidate 中允许失败的外部访问。
        try:

            # 保留 profile 中间值，支撑 source_repo_governance_owner_candidate 的当前计算步骤。
            profile = json.loads(profile_path.read_text(encoding="utf-8"))  # profile 用于本步治理判断
        except json.JSONDecodeError:

            # 返回 source_repo_governance_owner_candidate 已整理完成的调用载荷。
            return False

        # 检查 source_repo_governance_owner_candidate 的当前条件是否需要进入专门分支。
        if profile.get("kind") == "skill" and profile.get("name") == target_name:

            # 返回 source_repo_governance_owner_candidate 已整理完成的调用载荷。
            return True

    # 保留 scripts dir 中间值，支撑 source_repo_governance_owner_candidate 的当前计算步骤。
    scripts_dir = candidate / "scripts"  # scripts dir 用于本步治理判断

    # 返回 source_repo_governance_owner_candidate 已整理完成的调用载荷。
    scripts_python_dir = scripts_dir / "python"  # AGENTS 共享工具值
    return (
        (scripts_python_dir / "verify" / "verify_agents.py").is_file()
        and (scripts_python_dir / "docs" / "manage_docs.py").is_file()
    )


# 定义 evolution_owner_status 的AGENTS 共享工具处理入口。
def evolution_owner_status(
    project: Path,
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> dict[str, Any]:

    # 保留 target name 中间值，支撑 evolution_owner_status 的当前计算步骤。
    target_name = skill_name or governance_skill_name()  # target name 用于本步治理判断

    # 保留 resolved project 中间值，支撑 evolution_owner_status 的当前计算步骤。
    resolved_project = project.resolve()  # resolved project 用于本步治理判断

    # 收集 active skill dirs 条目，保持 evolution_owner_status 的处理顺序稳定。
    list_active_skill_dirs = current_governance_skill_dirs(target_name, override_dir=override_dir)  # active skill dirs 用于本步治理判断

    # 保留 source repo skill dir 中间值，支撑 evolution_owner_status 的当前计算步骤。
    source_repo_skill_dir = resolved_project / "skills" / target_name  # source repo skill dir 用于本步治理判断

    # 检查 evolution_owner_status 的当前条件是否需要进入专门分支。
    if source_repo_skill_dir.is_dir():

        # 保留 candidate 中间值，支撑 evolution_owner_status 的当前计算步骤。
        candidate = source_repo_skill_dir.resolve()  # candidate 用于本步治理判断

        # 检查 evolution_owner_status 的当前条件是否需要进入专门分支。
        if any(candidate == active for active in list_active_skill_dirs) or source_repo_governance_owner_candidate(
            resolved_project,
            candidate,
            target_name,
        ):

            # 返回 evolution_owner_status 已整理完成的调用载荷。
            return {
                "enabled": True,
                "mode": "source-repo",
                "project_root": str(resolved_project),
                "owner_skill_dir": str(candidate),
            }

    # 检查 evolution_owner_status 的当前条件是否需要进入专门分支。
    if any(resolved_project == active for active in list_active_skill_dirs):

        # 返回 evolution_owner_status 已整理完成的调用载荷。
        return {
            "enabled": True,
            "mode": "installed-skill",
            "project_root": str(resolved_project),
            "owner_skill_dir": str(resolved_project),
        }

    # 返回 evolution_owner_status 已整理完成的调用载荷。
    return {
        "enabled": False,
        "mode": "non-owner",
        "project_root": str(resolved_project),
        "owner_skill_dir": "",
    }


# 定义 path_is_writable 的AGENTS 共享工具处理入口。
def path_is_writable(path: Path) -> bool:

    # 保留 target 中间值，支撑 path_is_writable 的当前计算步骤。
    target = path if path.suffix == "" else path.parent  # target 用于本步治理判断

    # 保护 path_is_writable 中允许失败的外部访问。
    try:

        # 调用 mkdir 完成 path_is_writable 的当前动作。
        target.mkdir(parents=True, exist_ok=True)

        # 保留 probe 中间值，支撑 path_is_writable 的当前计算步骤。
        probe = target / ".write-probe.tmp"  # probe 用于本步治理判断

        # 调用 write_text 完成 path_is_writable 的当前动作。
        probe.write_text("ok\n", encoding="utf-8")

        # 调用 unlink 完成 path_is_writable 的当前动作。
        probe.unlink()

        # 返回 path_is_writable 已整理完成的调用载荷。
        return True
    except Exception:

        # 返回 path_is_writable 已整理完成的调用载荷。
        return False


# 定义 installed_governance_skill_dir 的AGENTS 共享工具处理入口。
def installed_governance_skill_dir(
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> Path | None:

    # 保留 target name 中间值，支撑 installed_governance_skill_dir 的当前计算步骤。
    target_name = skill_name or governance_skill_name()  # target name 用于本步治理判断

    # 保留 installed 中间值，支撑 installed_governance_skill_dir 的当前计算步骤。
    installed = installed_skill_dir(target_name, override_dir=override_dir)  # installed 用于本步治理判断

    # 返回 installed_governance_skill_dir 已整理完成的调用载荷。
    return installed.resolve() if installed is not None else None


# 定义 evolution_template_sink 的AGENTS 共享工具处理入口。
def evolution_template_sink(
    project: Path,
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> dict[str, Any]:

    # 保留 target name 中间值，支撑 evolution_template_sink 的当前计算步骤。
    target_name = skill_name or governance_skill_name()  # target name 用于本步治理判断

    # 收集 status 条目，保持 evolution_template_sink 的处理顺序稳定。
    dict_status = evolution_owner_status(project, skill_name=target_name, override_dir=override_dir)  # status 用于本步治理判断

    # 保留 project root 中间值，支撑 evolution_template_sink 的当前计算步骤。
    project_root = project.resolve()  # project root 用于本步治理判断

    # 检查 evolution_template_sink 的当前条件是否需要进入专门分支。
    if dict_status.get("enabled"):

        # 保留 owner skill dir 中间值，支撑 evolution_template_sink 的当前计算步骤。
        owner_skill_dir = Path(str(dict_status.get("owner_skill_dir", ""))).resolve()  # owner skill dir 用于本步治理判断

        # 保留 template root 中间值，支撑 evolution_template_sink 的当前计算步骤。
        template_root = owner_skill_dir / "assets" / "templates" / "evolution"  # template root 用于本步治理判断

        # 返回 evolution_template_sink 已整理完成的调用载荷。
        return {
            "mode": "owner-local",
            "project_root": str(project_root),
            "owner_skill_dir": str(owner_skill_dir),
            "installed_skill_dir": str(owner_skill_dir),
            "template_root": str(template_root),
            "export_root": ".agents/evolution-export",
            "import_request_path": ".agents/evolution-import-request.json",
            "source_workspace": str(project_root),
            "writable": path_is_writable(template_root),
        }

    # 保留 installed 中间值，支撑 evolution_template_sink 的当前计算步骤。
    installed = installed_governance_skill_dir(target_name, override_dir=override_dir)  # installed 用于本步治理判断

    # 检查 evolution_template_sink 的当前条件是否需要进入专门分支。
    if installed is not None:

        # 保留 template root 中间值，支撑 evolution_template_sink 的当前计算步骤。
        template_root = installed / "assets" / "templates" / "evolution"  # template root 用于本步治理判断

        # 检查 evolution_template_sink 的当前条件是否需要进入专门分支。
        if path_is_writable(template_root):

            # 返回 evolution_template_sink 已整理完成的调用载荷。
            return {
                "mode": "installed-sink",
                "project_root": str(project_root),
                "owner_skill_dir": "",
                "installed_skill_dir": str(installed),
                "template_root": str(template_root),
                "export_root": ".agents/evolution-export",
                "import_request_path": ".agents/evolution-import-request.json",
                "source_workspace": str(project_root),
                "writable": True,
            }

    # 返回 evolution_template_sink 已整理完成的调用载荷。
    return {
        "mode": "export-pending",
        "project_root": str(project_root),
        "owner_skill_dir": "",
        "installed_skill_dir": str(installed) if installed is not None else "",
        "template_root": "",
        "export_root": ".agents/evolution-export",
        "import_request_path": ".agents/evolution-import-request.json",
        "source_workspace": str(project_root),
        "writable": True,
    }

# 定义 read_installed_skill_version 的AGENTS 共享工具处理入口。
def read_installed_skill_version(skill_name: str = "agents-md-generator", override_dir: str | Path | None = None) -> str:

    # 保留 installed 中间值，支撑 read_installed_skill_version 的当前计算步骤。
    installed = installed_skill_dir(skill_name, override_dir=override_dir)  # installed 用于本步治理判断

    # 检查 read_installed_skill_version 的当前条件是否需要进入专门分支。
    if installed is None:

        # 返回 read_installed_skill_version 已整理完成的调用载荷。
        return ""

    # 返回 read_installed_skill_version 已整理完成的调用载荷。
    return read_skill_version(installed)

# 定义 preferred_skill_version 的AGENTS 共享工具处理入口。
def preferred_skill_version(skill_name: str = "agents-md-generator", override_dir: str | Path | None = None) -> tuple[str, str]:

    # 保留 installed 中间值，支撑 preferred_skill_version 的当前计算步骤。
    str_installed = read_installed_skill_version(skill_name, override_dir=override_dir)  # installed 用于本步治理判断

    # 检查 preferred_skill_version 的当前条件是否需要进入专门分支。
    if str_installed:

        # 返回 preferred_skill_version 已整理完成的调用载荷。
        return str_installed, "installed-override" if override_dir else "installed"

    # 保留 runtime 中间值，支撑 preferred_skill_version 的当前计算步骤。
    str_runtime = read_skill_version()  # runtime 用于本步治理判断

    # 检查 preferred_skill_version 的当前条件是否需要进入专门分支。
    if str_runtime:

        # 返回 preferred_skill_version 已整理完成的调用载荷。
        return str_runtime, "runtime"

    # 返回 preferred_skill_version 已整理完成的调用载荷。
    return "", "unavailable"

# 定义 project_profile 的AGENTS 共享工具处理入口。
def project_profile(root: Path) -> dict[str, Any]:

    # 保留 path 中间值，支撑 project_profile 的当前计算步骤。
    path = root / ".agents" / "agents-control.json"  # path 用于本步治理判断

    # 返回 project_profile 已整理完成的调用载荷。
    return read_json(path) if path.exists() else {}

# 定义 primary_project_root_from_profile 的AGENTS 共享工具处理入口。
def primary_project_root_from_profile(profile: dict[str, Any] | None) -> str:

    # 检查 primary_project_root_from_profile 的当前条件是否需要进入专门分支。
    if not isinstance(profile, dict):

        # 返回 primary_project_root_from_profile 已整理完成的调用载荷。
        return ""

    # 保留 directory contract 中间值，支撑 primary_project_root_from_profile 的当前计算步骤。
    directory_contract = profile.get("directory_contract", {})  # directory contract 用于本步治理判断

    # 检查 primary_project_root_from_profile 的当前条件是否需要进入专门分支。
    if not isinstance(directory_contract, dict):

        # 返回 primary_project_root_from_profile 已整理完成的调用载荷。
        return ""

    # 返回 primary_project_root_from_profile 已整理完成的调用载荷。
    return str(directory_contract.get("primary_project_root", "")).strip().strip("/\\")

# 定义 governance_runtime_root 的AGENTS 共享工具处理入口。
def governance_runtime_root(
    root: Path,
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> str:

    # 保留 target name 中间值，支撑 governance_runtime_root 的当前计算步骤。
    target_name = skill_name or governance_skill_name()  # target name 用于本步治理判断

    # 收集 status 条目，保持 governance_runtime_root 的处理顺序稳定。
    dict_status = evolution_owner_status(root, skill_name=target_name, override_dir=override_dir)  # status 用于本步治理判断

    # 检查 governance_runtime_root 的当前条件是否需要进入专门分支。
    if dict_status.get("enabled"):

        # 保留 owner skill dir 中间值，支撑 governance_runtime_root 的当前计算步骤。
        owner_skill_dir = Path(str(dict_status.get("owner_skill_dir", ""))).resolve()  # owner skill dir 用于本步治理判断

        # 保留 resolved root 中间值，支撑 governance_runtime_root 的当前计算步骤。
        resolved_root = root.resolve()  # resolved root 用于本步治理判断

        # 检查 governance_runtime_root 的当前条件是否需要进入专门分支。
        if owner_skill_dir == resolved_root:

            # 返回 governance_runtime_root 已整理完成的调用载荷。
            return "."

        # 保护 governance_runtime_root 中允许失败的外部访问。
        try:

            # 返回 governance_runtime_root 已整理完成的调用载荷。
            return owner_skill_dir.relative_to(resolved_root).as_posix()
        except ValueError:

            # 返回 governance_runtime_root 已整理完成的调用载荷。
            return owner_skill_dir.as_posix()

    # 返回 governance_runtime_root 已整理完成的调用载荷。
    return f"<codex-home>/skills/{target_name}"

# 定义 governance_script_path 的AGENTS 共享工具处理入口。
def governance_script_path(
    root: Path,
    script_name: str,
    *,
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> str:

    # 保留 runtime root 中间值，支撑 governance_script_path 的当前计算步骤。
    str_runtime_root = governance_runtime_root(root, skill_name=skill_name, override_dir=override_dir)  # runtime root 用于本步治理判断

    # 检查 governance_script_path 的当前条件是否需要进入专门分支。
    if str_runtime_root == ".":

        # 保留 local task name 中间值，支撑 governance_script_path 的当前计算步骤。
        str_local_task_name = SCRIPT_TASK_BY_NAME.get(Path(script_name).name, "")  # local task name 用于本步治理判断

        # 检查 governance_script_path 的当前条件是否需要进入专门分支。
        if str_local_task_name:

            # 返回 governance_script_path 已整理完成的调用载荷。
            return f"scripts/python/{str_local_task_name}/{script_name}"

        # 返回 governance_script_path 已整理完成的调用载荷。
        return f"scripts/python/{script_name}"

    # 保留 task name 中间值，支撑 governance_script_path 的当前计算步骤。
    str_task_name = SCRIPT_TASK_BY_NAME.get(Path(script_name).name, "")  # task name 用于本步治理判断

    # 检查 governance_script_path 的当前条件是否需要进入专门分支。
    if str_task_name:

        # 返回 governance_script_path 已整理完成的调用载荷。
        return f"{str_runtime_root}/scripts/python/{str_task_name}/{script_name}"

    # 返回 governance_script_path 已整理完成的调用载荷。
    return f"{str_runtime_root}/scripts/python/{script_name}"

# 定义 managed_scripts_root 的AGENTS 共享工具处理入口。
def managed_scripts_root(root: Path, profile: dict[str, Any] | None = None) -> str:

    # 检查 managed_scripts_root 的当前条件是否需要进入专门分支。
    if (root / "scripts").is_dir():

        # 返回 managed_scripts_root 已整理完成的调用载荷。
        return "scripts"

    # 保留 effective profile 中间值，支撑 managed_scripts_root 的当前计算步骤。
    effective_profile = profile if isinstance(profile, dict) else project_profile(root)  # effective profile 用于本步治理判断

    # 保留 primary root 中间值，支撑 managed_scripts_root 的当前计算步骤。
    str_primary_root = primary_project_root_from_profile(effective_profile)  # primary root 用于本步治理判断

    # 检查 managed_scripts_root 的当前条件是否需要进入专门分支。
    if str_primary_root:

        # 收集 primary scripts 条目，保持 managed_scripts_root 的处理顺序稳定。
        primary_scripts = root / str_primary_root / "scripts"  # primary scripts 用于本步治理判断

        # 检查 managed_scripts_root 的当前条件是否需要进入专门分支。
        if primary_scripts.is_dir():

            # 返回 managed_scripts_root 已整理完成的调用载荷。
            return primary_scripts.relative_to(root).as_posix()

        # 返回 managed_scripts_root 已整理完成的调用载荷。
        return f"{str_primary_root}/scripts"

    # 返回 managed_scripts_root 已整理完成的调用载荷。
    return "scripts"

# 定义 script_command 的AGENTS 共享工具处理入口。
def script_command(
    root: Path,
    script_name: str,
    *args: str,
    profile: dict[str, Any] | None = None,
    override_dir: str | Path | None = None,
) -> str:
    # 治理运行命令不再通过目标项目 scripts 目录解析。
    del profile

    # 定位 script path 的文件边界，供 script_command 后续读写校验使用。
    str_script_path = governance_script_path(root, script_name, override_dir=override_dir)  # script path 用于本步治理判断

    # 收集 segments 条目，保持 script_command 的处理顺序稳定。
    list_segments = ["python", str_script_path, *[str(item) for item in args if str(item).strip()]]  # segments 用于本步治理判断

    # 返回 script_command 已整理完成的调用载荷。
    return " ".join(list_segments)

# 定义 root_agents_sync_command 的AGENTS 共享工具处理入口。
def root_agents_sync_command(root: Path, profile: dict[str, Any] | None = None, installed_skill_dir_override: str | Path | None = None) -> str:

    # 保留 command 中间值，支撑 root_agents_sync_command 的当前计算步骤。
    str_command = script_command(  # command 用于本步治理判断
        root,  # command 用于本步治理判断
        "manage_docs.py",  # command 用于本步治理判断
        "sync-root-agents",  # command 用于本步治理判断
        ".",  # command 用于本步治理判断
        "--write",  # command 用于本步治理判断
        profile=profile,  # command 用于本步治理判断
        override_dir=installed_skill_dir_override,  # command 用于本步治理判断
    )

    # 检查 root_agents_sync_command 的当前条件是否需要进入专门分支。
    if installed_skill_dir_override is not None:

        # 保留 command 中间值，支撑 root_agents_sync_command 的当前计算步骤。
        str_command += f" --installed-skill-dir {Path(installed_skill_dir_override).as_posix()}"  # command 用于本步治理判断

    # 返回 root_agents_sync_command 已整理完成的调用载荷。
    return str_command

# 定义 global_codex_agents_sync_command 的AGENTS 共享工具处理入口。
def global_codex_agents_sync_command(root: Path, profile: dict[str, Any] | None = None) -> str:

    # 返回 global_codex_agents_sync_command 已整理完成的调用载荷。
    return script_command(root, "manage_docs.py", "sync-global-codex-agents", ".", "--write", profile=profile)

# 定义 global_codex_agents_path 的AGENTS 共享工具处理入口。
def global_codex_agents_path(codex_home: str | None = None) -> Path:

    # 返回 global_codex_agents_path 已整理完成的调用载荷。
    return codex_home_root(codex_home) / "AGENTS.md"

# 定义 global_codex_agents_template_path 的AGENTS 共享工具处理入口。
def global_codex_agents_template_path(root: Path | None = None) -> Path:

    # 返回 global_codex_agents_template_path 已整理完成的调用载荷。
    return (root or skill_root()) / "assets" / "templates" / "global-codex-agents.md"

# 定义 render_global_codex_agents_template 的AGENTS 共享工具处理入口。
def render_global_codex_agents_template(root: Path | None = None) -> str:

    # 保留 path 中间值，支撑 render_global_codex_agents_template 的当前计算步骤。
    path_path = global_codex_agents_template_path(root)  # path 用于本步治理判断

    # 检查 render_global_codex_agents_template 的当前条件是否需要进入专门分支。
    if not path_path.is_file():

        # 抛出 render_global_codex_agents_template 已确认的阻断原因。
        raise SystemExit(f"Missing global Codex AGENTS template: {path_path}")

    # 返回 render_global_codex_agents_template 已整理完成的调用载荷。
    return path_path.read_text(encoding="utf-8", errors="ignore").rstrip() + "\n"

# 定义 extract_global_codex_managed_block 的AGENTS 共享工具处理入口。
def extract_global_codex_managed_block(text: str) -> str:

    # 保留 start 中间值，支撑 extract_global_codex_managed_block 的当前计算步骤。
    start = text.find(GLOBAL_CODEX_AGENTS_BLOCK_START)  # start 用于本步治理判断

    # 保留 end 中间值，支撑 extract_global_codex_managed_block 的当前计算步骤。
    end = text.find(GLOBAL_CODEX_AGENTS_BLOCK_END)  # end 用于本步治理判断

    # 检查 extract_global_codex_managed_block 的当前条件是否需要进入专门分支。
    if start == -1 or end == -1 or end < start:

        # 返回 extract_global_codex_managed_block 已整理完成的调用载荷。
        return ""

    # 保留 end 中间值，支撑 extract_global_codex_managed_block 的当前计算步骤。
    end += len(GLOBAL_CODEX_AGENTS_BLOCK_END)  # end 用于本步治理判断

    # 返回 extract_global_codex_managed_block 已整理完成的调用载荷。
    return text[start:end]

# 定义 global_codex_agents_status 的AGENTS 共享工具处理入口。
def global_codex_agents_status(codex_home: str | None = None, project_root: Path | None = None, profile: dict[str, Any] | None = None) -> dict[str, Any]:

    # 保留 path 中间值，支撑 global_codex_agents_status 的当前计算步骤。
    path_path = global_codex_agents_path(codex_home)  # path 用于本步治理判断

    # 保留 text 中间值，支撑 global_codex_agents_status 的当前计算步骤。
    text = path_path.read_text(encoding="utf-8", errors="ignore") if path_path.is_file() else ""  # text 用于本步治理判断

    # 收集 exists 条目，保持 global_codex_agents_status 的处理顺序稳定。
    exists = path_path.is_file()  # exists 用于本步治理判断

    # 保留 empty 中间值，支撑 global_codex_agents_status 的当前计算步骤。
    empty = exists and not text.strip()  # empty 用于本步治理判断

    # 保留 managed 中间值，支撑 global_codex_agents_status 的当前计算步骤。
    managed = GLOBAL_CODEX_AGENTS_BLOCK_START in text and GLOBAL_CODEX_AGENTS_BLOCK_END in text  # managed 用于本步治理判断

    # 保留 expected block 中间值，支撑 global_codex_agents_status 的当前计算步骤。
    str_expected_block = extract_global_codex_managed_block(render_global_codex_agents_template())  # expected block 用于本步治理判断

    # 保留 actual block 中间值，支撑 global_codex_agents_status 的当前计算步骤。
    actual_block = extract_global_codex_managed_block(text) if managed else ""  # actual block 用于本步治理判断

    # 保留 meta ok 中间值，支撑 global_codex_agents_status 的当前计算步骤。
    meta_ok = GLOBAL_CODEX_AGENTS_META in text  # meta ok 用于本步治理判断

    # 保留 baseline ok 中间值，支撑 global_codex_agents_status 的当前计算步骤。
    baseline_ok = managed and meta_ok and actual_block == str_expected_block  # baseline ok 用于本步治理判断

    # 收集 repair reasons 条目，保持 global_codex_agents_status 的处理顺序稳定。
    list_repair_reasons: list[str] = []  # repair reasons 用于本步治理判断

    # 保留 requires user confirmation 中间值，支撑 global_codex_agents_status 的当前计算步骤。
    bool_requires_user_confirmation = False  # requires user confirmation 用于本步治理判断

    # 保留 user message 中间值，支撑 global_codex_agents_status 的当前计算步骤。
    str_user_message = ""  # user message 用于本步治理判断

    # 检查 global_codex_agents_status 的当前条件是否需要进入专门分支。
    if not exists:

        # 调用 append 完成 global_codex_agents_status 的当前动作。
        list_repair_reasons.append("missing_global_codex_agents_md")

    # 检查 global_codex_agents_status 的当前条件是否需要进入专门分支。
    elif empty:

        # 调用 append 完成 global_codex_agents_status 的当前动作。
        list_repair_reasons.append("empty_global_codex_agents_md")

    # 检查 global_codex_agents_status 的当前条件是否需要进入专门分支。
    elif not managed:

        # 调用 append 完成 global_codex_agents_status 的当前动作。
        list_repair_reasons.append("missing_global_codex_agents_managed_block")

        # 保留 requires user confirmation 中间值，支撑 global_codex_agents_status 的当前计算步骤。
        bool_requires_user_confirmation = True  # requires user confirmation 用于本步治理判断

        # 保留 user message 中间值，支撑 global_codex_agents_status 的当前计算步骤。
        str_user_message = (  # user message 用于本步治理判断
            "Global .codex/AGENTS.md has manual content but no managed baseline block; "  # user message 用于本步治理判断
            "insert the generated baseline block near the top of the file after any opening comments."  # user message 用于本步治理判断
        )

    # 检查 global_codex_agents_status 的当前条件是否需要进入专门分支。
    elif not meta_ok:

        # 调用 append 完成 global_codex_agents_status 的当前动作。
        list_repair_reasons.append("missing_global_codex_agents_v3_meta")

    # 检查 global_codex_agents_status 的当前条件是否需要进入专门分支。
    elif actual_block != str_expected_block:

        # 调用 append 完成 global_codex_agents_status 的当前动作。
        list_repair_reasons.append("outdated_global_codex_agents_baseline")

    # 保留 repair required 中间值，支撑 global_codex_agents_status 的当前计算步骤。
    bool_repair_required = bool(list_repair_reasons)  # repair required 用于本步治理判断

    # 同步命令在状态和建议动作中复用，避免两处 fallback 文本漂移。
    str_repair_command = (  # 全局 AGENTS 同步修复命令
        global_codex_agents_sync_command(project_root, profile)  # 多行表达式输入文本
        if project_root  # 项目根存在时使用仓库内命令
        else (  # 项目根缺失时使用已安装治理运行时占位命令
            f"python {INSTALLED_GOVERNANCE_RUNTIME_PLACEHOLDER}/scripts/python/docs/manage_docs.py "  # 已安装治理运行时脚本前缀
            "sync-global-codex-agents . --write"  # 全局 AGENTS 基线写入动作
        )
    )

    # 返回 global_codex_agents_status 已整理完成的调用载荷。
    return {
        "path": str(path_path),
        "exists": exists,
        "empty": empty,
        "managed": managed,
        "baseline_version": "3" if meta_ok else "",
        "baseline_ok": baseline_ok,
        "repair_required": bool_repair_required,
        "repair_reasons": list_repair_reasons,
        "repair_command": str_repair_command,
        "recommended_action": str_repair_command,
        "requires_user_confirmation": bool_requires_user_confirmation,
        "user_message": str_user_message,
    }

# 定义 parse_agents_metadata 的AGENTS 共享工具处理入口。
def parse_agents_metadata(text: str) -> dict[str, str]:

    # 保留 match 中间值，支撑 parse_agents_metadata 的当前计算步骤。
    match = AGENTS_METADATA_RE.search(text)  # match 用于本步治理判断

    # 检查 parse_agents_metadata 的当前条件是否需要进入专门分支。
    if not match:

        # 返回 parse_agents_metadata 已整理完成的调用载荷。
        return {}

    # 保留 body 中间值，支撑 parse_agents_metadata 的当前计算步骤。
    body = match.group(1)  # body 用于本步治理判断

    # 保留 data 中间值，支撑 parse_agents_metadata 的当前计算步骤。
    dict_data: dict[str, str] = {}  # data 用于本步治理判断

    # 逐项推进 parse_agents_metadata 的候选项检查。
    for key, raw_value in AGENTS_METADATA_PAIR_RE.findall(body):

        # 保留 中间载荷 中间值，支撑 parse_agents_metadata 的当前计算步骤。
        dict_data[key.strip()] = raw_value.strip()  # 中间载荷 用于本步治理判断

    # 返回 parse_agents_metadata 已整理完成的调用载荷。
    return dict_data

# 定义 rel 的AGENTS 共享工具处理入口。
def rel(path: Path, root: Path) -> str:

    # 返回 rel 已整理完成的调用载荷。
    return path.resolve().relative_to(root.resolve()).as_posix()

# 定义 display_path 的AGENTS 共享工具处理入口。
def display_path(path: Path, root: Path | None = None) -> str:

    # 检查 display_path 的当前条件是否需要进入专门分支。
    if root is not None:

        # 保护 display_path 中允许失败的外部访问。
        try:

            # 返回 display_path 已整理完成的调用载荷。
            return path.resolve().relative_to(root.resolve()).as_posix()
        except Exception:
            pass

    # 返回 display_path 已整理完成的调用载荷。
    return path.resolve().as_posix()

# 定义 normalize_path_key 的AGENTS 共享工具处理入口。
def normalize_path_key(raw: str | Path) -> str:

    # 保留 value 中间值，支撑 normalize_path_key 的当前计算步骤。
    raw_value = str(raw).strip()  # value 用于本步治理判断

    # 检查 normalize_path_key 的当前条件是否需要进入专门分支。
    if not raw_value:

        # 返回 normalize_path_key 已整理完成的调用载荷。
        return ""

    # 保护 normalize_path_key 中允许失败的外部访问。
    try:

        # 保留 resolved 中间值，支撑 normalize_path_key 的当前计算步骤。
        resolved = Path(raw_value).expanduser().resolve()  # resolved 用于本步治理判断
    except Exception:

        # 保留 resolved 中间值，支撑 normalize_path_key 的当前计算步骤。
        resolved = Path(raw_value).expanduser()  # resolved 用于本步治理判断

    # 返回 normalize_path_key 已整理完成的调用载荷。
    return os.path.normcase(str(resolved))

# 定义 workspace_has_existing_content 的AGENTS 共享工具处理入口。
def workspace_has_existing_content(root: Path) -> bool:

    # 保留 ignored 中间值，支撑 workspace_has_existing_content 的当前计算步骤。
    ignored = set(SKIP_DIRS) | {".agents"}  # ignored 用于本步治理判断

    # 逐项推进 workspace_has_existing_content 的候选项检查。
    for path in root.iterdir():

        # 检查 workspace_has_existing_content 的当前条件是否需要进入专门分支。
        if path.name in ignored:

            # 分隔 workspace_has_existing_content 的控制流边界。
            continue

        # 检查 workspace_has_existing_content 的当前条件是否需要进入专门分支。
        if path.name == "AGENTS.md":

            # 分隔 workspace_has_existing_content 的控制流边界。
            continue

        # 返回 workspace_has_existing_content 已整理完成的调用载荷。
        return True

    # 返回 workspace_has_existing_content 已整理完成的调用载荷。
    return False

# 定义 package_manager 的AGENTS 共享工具处理入口。
def package_manager(root: Path) -> str:

    # 保留 package json 中间值，支撑 package_manager 的当前计算步骤。
    dict_package_json = read_json(root / "package.json")  # package json 用于本步治理判断

    # 保留 field 中间值，支撑 package_manager 的当前计算步骤。
    field = dict_package_json.get("packageManager", "")  # field 用于本步治理判断

    # 检查 package_manager 的当前条件是否需要进入专门分支。
    if isinstance(field, str) and "@" in field:

        # 返回 package_manager 已整理完成的调用载荷。
        return field.split("@", 1)[0]

    # 检查 package_manager 的当前条件是否需要进入专门分支。
    if (root / "pnpm-lock.yaml").exists():

        # 返回 package_manager 已整理完成的调用载荷。
        return "pnpm"

    # 检查 package_manager 的当前条件是否需要进入专门分支。
    if (root / "yarn.lock").exists():

        # 返回 package_manager 已整理完成的调用载荷。
        return "yarn"

    # 检查 package_manager 的当前条件是否需要进入专门分支。
    if (root / "bun.lockb").exists() or (root / "bun.lock").exists():

        # 返回 package_manager 已整理完成的调用载荷。
        return "bun"

    # 检查 package_manager 的当前条件是否需要进入专门分支。
    if (root / "package-lock.json").exists() or (root / "package.json").exists():

        # 返回 package_manager 已整理完成的调用载荷。
        return "npm"

    # 检查 package_manager 的当前条件是否需要进入专门分支。
    if (root / "composer.json").exists():

        # 返回 package_manager 已整理完成的调用载荷。
        return "composer"

    # 检查 package_manager 的当前条件是否需要进入专门分支。
    if (root / "uv.lock").exists():

        # 返回 package_manager 已整理完成的调用载荷。
        return "uv"

    # 检查 package_manager 的当前条件是否需要进入专门分支。
    if (root / "poetry.lock").exists():

        # 返回 package_manager 已整理完成的调用载荷。
        return "poetry"

    # 检查 package_manager 的当前条件是否需要进入专门分支。
    if (root / "go.mod").exists():

        # 返回 package_manager 已整理完成的调用载荷。
        return "go"

    # 返回 package_manager 已整理完成的调用载荷。
    return "unknown"

# 定义 pm_run 的AGENTS 共享工具处理入口。
def pm_run(pm: str) -> str:

    # 返回 pm_run 已整理完成的调用载荷。
    return {"pnpm": "pnpm", "yarn": "yarn", "bun": "bun run"}.get(pm, "npm run")

# 定义 pm_dlx 的AGENTS 共享工具处理入口。
def pm_dlx(pm: str) -> str:

    # 返回 pm_dlx 已整理完成的调用载荷。
    return {"pnpm": "pnpm dlx", "yarn": "yarn dlx", "bun": "bunx"}.get(pm, "npx")

# 定义 run_git 的AGENTS 共享工具处理入口。
def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:

    # 返回 run_git 已整理完成的调用载荷。
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)

# 定义 today 的AGENTS 共享工具处理入口。
def today() -> str:

    # 返回 today 已整理完成的调用载荷。
    return date.today().isoformat()

# 定义 current_timestamp 的AGENTS 共享工具处理入口。
def current_timestamp() -> str:

    # 返回 current_timestamp 已整理完成的调用载荷。
    return datetime.now().isoformat(timespec="seconds")

# 定义 parse_args 的AGENTS 共享工具处理入口。
def parse_args(description: str) -> argparse.ArgumentParser:

    # 保留 parser 中间值，支撑 parse_args 的当前计算步骤。
    parser = argparse.ArgumentParser(description=description)  # parser 用于本步治理判断

    # 调用 add_argument 完成 parse_args 的当前动作。
    parser.add_argument("project", nargs="?", default=".", help="Target project directory")

    # 返回 parse_args 已整理完成的调用载荷。
    return parser

# 导入 AGENTS 共享工具 所需的依赖模块。
from agents_project_facts import (
    command_entry,
    default_implementation_constraints,
    default_global_rule_overrides,
    decomposition_plan_path,
    detect_scopes,
    ensure_global_rule_overrides_file,

    # 分隔当前密集代码块，保留原有执行顺序。
    existing_paths,
    extract_commands,
    extract_context,
    global_rule_overrides_path,
    global_rule_overrides_reference,
    has_any,

    # 再次分隔当前长代码块，降低连续语句密度。
    implementation_constraints_from_profile,
    inspect_project,
    iter_handwritten_code_files,
    list_dirs,
    list_files,
    load_global_rule_overrides,

    # 分隔导入清单的后续成员，避免超长连续导入块。
    managed_script_roots,
    matched_codex_sessions,
    parse_session_meta,
    script_governance_exceptions,
    script_layout_facts,

    # 分隔导入清单末段，保证分组阅读边界清楚。
    session_message_rows,
    validate_global_rule_overrides_data,
    workflow_runs,
)


