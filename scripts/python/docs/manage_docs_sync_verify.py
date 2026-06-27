"""同步并校验 AGENTS、全局 baseline、文档治理和工作区状态。"""

# 导入 脚本治理 所需的依赖模块。
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

# 导入 脚本治理 所需的依赖模块。
import os

# 导入 脚本治理 所需的依赖模块。
from manage_docs_shared import *
from source_governance import format_source_governance_errors, source_governance_report

# 保留 VERSION RE 中间值，支撑 模块入口 的当前计算步骤。
VERSION_RE = re.compile(r"\bv\d+\.\d+\.\d+\b")  # VERSION RE 用于本步治理判断

# 保留 GLOBAL CODEX AGENTS META LINE RE 中间值，支撑 模块入口 的当前计算步骤。
GLOBAL_CODEX_AGENTS_META_LINE_RE = re.compile(r"^<!--\s*AGENTS-GENERATED:META\b.*\bbaseline=global-codex-baseline\b.*-->$")  # GLOBAL CODEX AGENTS META LINE RE 用于本步治理判断

# 保留 CONTROL PROFILE BLOCK RE 中间值，支撑 模块入口 的当前计算步骤。
CONTROL_PROFILE_BLOCK_RE = re.compile(  # CONTROL PROFILE BLOCK RE 用于本步治理判断
    r"(<!--\s*AGENTS-GENERATED:START\s+control-profile\s*-->)(.*?)(<!--\s*AGENTS-GENERATED:END\s+control-profile\s*-->)",  # CONTROL PROFILE BLOCK RE 用于本步治理判断
    flags=re.DOTALL | re.IGNORECASE,  # CONTROL PROFILE BLOCK RE 用于本步治理判断
)

# 保留 PROJECT BLOCK RE 中间值，支撑 模块入口 的当前计算步骤。
PROJECT_BLOCK_RE = re.compile(  # PROJECT BLOCK RE 用于本步治理判断
    r"(<!--\s*AGENTS-GENERATED:START\s+project\s*-->)(.*?)(<!--\s*AGENTS-GENERATED:END\s+project\s*-->)",  # PROJECT BLOCK RE 用于本步治理判断
    flags=re.DOTALL | re.IGNORECASE,  # PROJECT BLOCK RE 用于本步治理判断
)

# 保留 CONTROL PROFILE VERSION RE 中间值，支撑 模块入口 的当前计算步骤。
CONTROL_PROFILE_VERSION_RE = re.compile(r"^-\s+Version:\s*(v\d+\.\d+\.\d+)\.$", flags=re.MULTILINE)  # CONTROL PROFILE VERSION RE 用于本步治理判断

# 保留 DOCS PRIVACY ROOTS 中间值，支撑 模块入口 的当前计算步骤。
DOCS_PRIVACY_ROOTS = [  # DOCS PRIVACY ROOTS 用于本步治理判断
    "docs/handoff",  # DOCS PRIVACY ROOTS 用于本步治理判断
    "docs/development",  # DOCS PRIVACY ROOTS 用于本步治理判断
    "docs/install_configuration",  # DOCS PRIVACY ROOTS 用于本步治理判断
    "docs/git_manager",  # DOCS PRIVACY ROOTS 用于本步治理判断
    "docs/dir_manager",  # DOCS PRIVACY ROOTS 用于本步治理判断
]

# 保留 DOCS PRIVACY TEXT SUFFIXES 中间值，支撑 模块入口 的当前计算步骤。
DOCS_PRIVACY_TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".yaml", ".yml"}  # DOCS PRIVACY TEXT SUFFIXES 用于本步治理判断

# 定义 inferred_skill_dir 的脚本治理处理入口。
def inferred_skill_dir(project: Path, raw_skill_dir: str | Path | None = None) -> Path | None:

    # 检查 inferred_skill_dir 的当前条件是否需要进入专门分支。
    if raw_skill_dir:

        # 保留 candidate 中间值，支撑 inferred_skill_dir 的当前计算步骤。
        path_candidate = Path(raw_skill_dir)  # candidate 用于本步治理判断

        # 检查 inferred_skill_dir 的当前条件是否需要进入专门分支。
        if not path_candidate.is_absolute():

            # 保留 candidate 中间值，支撑 inferred_skill_dir 的当前计算步骤。
            path_candidate = project / path_candidate  # candidate 用于本步治理判断

        # 返回 inferred_skill_dir 已整理完成的调用载荷。
        return path_candidate.resolve()

    # 保留 profile 中间值，支撑 inferred_skill_dir 的当前计算步骤。
    profile = project_profile(project)  # profile 用于本步治理判断

    # 检查 inferred_skill_dir 的当前条件是否需要进入专门分支。
    if isinstance(profile, dict):

        # 保留 layout 中间值，支撑 inferred_skill_dir 的当前计算步骤。
        layout = profile.get("skill_layout") if isinstance(profile.get("skill_layout"), dict) else {}  # layout 用于本步治理判断

        # 定位 raw path 的文件边界，供 inferred_skill_dir 后续读写校验使用。
        raw_path = str(layout.get("path") or "").strip()  # raw path 用于本步治理判断

        # 检查 inferred_skill_dir 的当前条件是否需要进入专门分支。
        if raw_path:

            # 返回 inferred_skill_dir 已整理完成的调用载荷。
            return (project / raw_path).resolve()

        # 保留 name 中间值，支撑 inferred_skill_dir 的当前计算步骤。
        name = str(profile.get("name") or "").strip()  # name 用于本步治理判断

        # 检查 inferred_skill_dir 的当前条件是否需要进入专门分支。
        if name:

            # 保留 candidate 中间值，支撑 inferred_skill_dir 的当前计算步骤。
            path_candidate = project / "skills" / name  # candidate 用于本步治理判断

            # 检查 inferred_skill_dir 的当前条件是否需要进入专门分支。
            if path_candidate.exists():

                # 返回 inferred_skill_dir 已整理完成的调用载荷。
                return path_candidate.resolve()

    # 保留 skills root 中间值，支撑 inferred_skill_dir 的当前计算步骤。
    skills_root = project / "skills"  # skills root 用于本步治理判断

    # 检查 inferred_skill_dir 的当前条件是否需要进入专门分支。
    if skills_root.is_dir():

        # 收集 candidates 条目，保持 inferred_skill_dir 的处理顺序稳定。
        candidates = [path for path in skills_root.iterdir() if (path / "VERSION").is_file()]  # candidates 用于本步治理判断

        # 检查 inferred_skill_dir 的当前条件是否需要进入专门分支。
        if len(candidates) == 1:

            # 返回 inferred_skill_dir 已整理完成的调用载荷。
            return candidates[0].resolve()

    # 返回 inferred_skill_dir 已整理完成的调用载荷。
    return None

# 定义 first_version 的脚本治理处理入口。
def first_version(text: str) -> str:

    # 保留 match 中间值，支撑 first_version 的当前计算步骤。
    match = VERSION_RE.search(text)  # match 用于本步治理判断

    # 返回 first_version 已整理完成的调用载荷。
    return match.group(0) if match else ""

# 定义 current_version_section 的脚本治理处理入口。
def current_version_section(text: str) -> str:

    # 保留 match 中间值，支撑 current_version_section 的当前计算步骤。
    match = re.search(r"^##\s+Current Version\s*$", text, flags=re.MULTILINE)  # Current Version 标题匹配结果

    # 检查 current_version_section 的当前条件是否需要进入专门分支。
    if not match:

        # 返回 current_version_section 已整理完成的调用载荷。
        return ""

    # 保留 rest 中间值，支撑 current_version_section 的当前计算步骤。
    rest = text[match.end() :]  # rest 用于本步治理判断

    # 保留 next section 中间值，支撑 current_version_section 的当前计算步骤。
    next_section = re.search(r"^##\s+", rest, flags=re.MULTILINE)  # 后续二级标题匹配结果

    # 返回 current_version_section 已整理完成的调用载荷。
    return rest[: next_section.start()] if next_section else rest

# 定义 managed_control_profile_version 的脚本治理处理入口。
def managed_control_profile_version(text: str) -> str:

    # 保留 block match 中间值，支撑 managed_control_profile_version 的当前计算步骤。
    block_match = CONTROL_PROFILE_BLOCK_RE.search(text) or PROJECT_BLOCK_RE.search(text)  # block match 用于本步治理判断

    # 检查 managed_control_profile_version 的当前条件是否需要进入专门分支。
    if not block_match:

        # 返回 managed_control_profile_version 已整理完成的调用载荷。
        return ""

    # 保留 version match 中间值，支撑 managed_control_profile_version 的当前计算步骤。
    version_match = CONTROL_PROFILE_VERSION_RE.search(block_match.group(2))  # version match 用于本步治理判断

    # 返回 managed_control_profile_version 已整理完成的调用载荷。
    return version_match.group(1) if version_match else ""

# 定义 replace_managed_control_profile_version 的脚本治理处理入口。
def replace_managed_control_profile_version(text: str, version: str) -> str:
    def replace_block(match: re.Match[str]) -> str:

        # 保留 body 中间值，支撑 replace_block 的当前计算步骤。
        body = CONTROL_PROFILE_VERSION_RE.sub(f"- Version: {version}.", match.group(2), count=1)  # body 用于本步治理判断

        # 返回 replace_block 已整理完成的调用载荷。
        return f"{match.group(1)}{body}{match.group(3)}"

    # 保留 updated 中间值，支撑 replace_managed_control_profile_version 的当前计算步骤。
    updated = CONTROL_PROFILE_BLOCK_RE.sub(replace_block, text, count=1)  # updated 用于本步治理判断

    # 检查 replace_managed_control_profile_version 的当前条件是否需要进入专门分支。
    if updated != text:

        # 返回 replace_managed_control_profile_version 已整理完成的调用载荷。
        return updated

    # 返回 replace_managed_control_profile_version 已整理完成的调用载荷。
    return PROJECT_BLOCK_RE.sub(replace_block, text, count=1)

# 定义 project_skill_version 的脚本治理处理入口。
def project_skill_version(project: Path, skill_dir_raw: str | Path | None = None) -> tuple[str, str, Path | None]:

    # 保留 skill dir 中间值，支撑 project_skill_version 的当前计算步骤。
    skill_dir = inferred_skill_dir(project, skill_dir_raw)  # skill dir 用于本步治理判断

    # 检查 project_skill_version 的当前条件是否需要进入专门分支。
    if not skill_dir:

        # 返回 project_skill_version 已整理完成的调用载荷。
        return "", "unavailable", None

    # 保留 version 中间值，支撑 project_skill_version 的当前计算步骤。
    version = read_skill_version(skill_dir)  # version 用于本步治理判断

    # 检查 project_skill_version 的当前条件是否需要进入专门分支。
    if not version:

        # 返回 project_skill_version 已整理完成的调用载荷。
        return "", "unavailable", skill_dir

    # 返回 project_skill_version 已整理完成的调用载荷。
    return version, "project-skill", skill_dir

# 定义 root_metadata_version 的脚本治理处理入口。
def root_metadata_version(
    project: Path,
    installed_skill_dir_override: str | Path | None = None,
) -> tuple[str, str, str, str, Path | None]:

    # 保留 project version、project version source、project skill dir 中间值，支撑 root_metadata_version 的当前计算步骤。
    tuple_project_version, tuple_project_version_source, tuple_project_skill_dir = project_skill_version(project)  # project version、project version source、project skill dir 用于本步治理判断

    # 检查 root_metadata_version 的当前条件是否需要进入专门分支。
    if installed_skill_dir_override is None and tuple_project_skill_dir and tuple_project_skill_dir.name == "agents-md-generator":
        # 生成器源码仓库必须能在版本安装前验证自身 release 版本。

        # 返回 root_metadata_version 已整理完成的调用载荷。
        return tuple_project_version, tuple_project_version_source, tuple_project_version, tuple_project_version_source, tuple_project_skill_dir

    # 保留 metadata version、version source 中间值，支撑 root_metadata_version 的当前计算步骤。
    metadata_version, version_source = preferred_skill_version(override_dir=installed_skill_dir_override)  # metadata version、version source 用于本步治理判断

    # 返回 root_metadata_version 已整理完成的调用载荷。
    return metadata_version, version_source, tuple_project_version, tuple_project_version_source, tuple_project_skill_dir

# 定义 version_alignment_gate 的脚本治理处理入口。
def version_alignment_gate(project: Path, skill_dir_raw: str | Path | None = None) -> dict[str, Any]:

    # 保留 expected、version source、skill dir 中间值，支撑 version_alignment_gate 的当前计算步骤。
    tuple_expected, tuple_version_source, tuple_skill_dir = project_skill_version(project, skill_dir_raw)  # expected、version source、skill dir 用于本步治理判断

    # 保留 checked 中间值，支撑 version_alignment_gate 的当前计算步骤。
    list_checked: list[str] = []  # checked 用于本步治理判断

    # 收集 errors 条目，保持 version_alignment_gate 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 检查 version_alignment_gate 的当前条件是否需要进入专门分支。
    if not tuple_expected:

        # 返回 version_alignment_gate 已整理完成的调用载荷。
        return {
            "project": str(project),
            "skill_dir": str(tuple_skill_dir) if tuple_skill_dir else "",
            "expected_version": "",
            "version_source": tuple_version_source,
            "checked": list_checked,
            "errors": [],
            "ok": True,
            "skipped": "no skill VERSION found",
        }

    # VERSION 文件位置先命名，兼容项目内相对展示和外部绝对展示。
    version_path = tuple_skill_dir / "VERSION"  # skill 版本文件定位

    # 项目内 skill 使用相对路径进入 checked 清单，外部 skill 保留绝对定位。
    if tuple_skill_dir.is_relative_to(project):

        # 项目内 VERSION 以相对路径展示，避免输出机器私有路径。
        str_checked_version_path = str(version_path.relative_to(project).as_posix())  # 项目内 VERSION 展示路径
    else:

        # 项目外 VERSION 无法相对化，保留原始定位便于排查。
        str_checked_version_path = str(version_path)  # 项目外 VERSION 展示路径

    # 调用 append 完成 version_alignment_gate 的当前动作。
    list_checked.append(str_checked_version_path)

    # 收集 agents 条目，保持 version_alignment_gate 的处理顺序稳定。
    agents = project / "AGENTS.md"  # agents 用于本步治理判断

    # 检查 version_alignment_gate 的当前条件是否需要进入专门分支。
    if agents.is_file():

        # 调用 append 完成 version_alignment_gate 的当前动作。
        list_checked.append("AGENTS.md")

        # 保留 agents text 中间值，支撑 version_alignment_gate 的当前计算步骤。
        agents_text = agents.read_text(encoding="utf-8", errors="ignore")  # agents text 用于本步治理判断

        # 保留 control match 中间值，支撑 version_alignment_gate 的当前计算步骤。
        control_match = re.search(r"^-\s+Version:\s*(v\d+\.\d+\.\d+)", agents_text, flags=re.MULTILINE)  # control match 用于本步治理判断

        # 检查 version_alignment_gate 的当前条件是否需要进入专门分支。
        if control_match and control_match.group(1) != tuple_expected:

            # 调用 append 完成 version_alignment_gate 的当前动作。
            list_errors.append(
                f"AGENTS.md control profile version {control_match.group(1)} does not match project skill VERSION {tuple_expected}"
            )

    # 收集 docs checks 条目，保持 version_alignment_gate 的处理顺序稳定。
    list_docs_checks = [  # docs checks 用于本步治理判断
        ("docs/development/DEVELOPMENT.md", "development record"),  # docs checks 用于本步治理判断
        ("docs/git_manager/CHANGELOG.md", "changelog"),  # docs checks 用于本步治理判断
    ]

    # 逐项推进 version_alignment_gate 的候选项检查。
    for rel_path, label in list_docs_checks:

        # 保留 path 中间值，支撑 version_alignment_gate 的当前计算步骤。
        path = project / rel_path  # path 用于本步治理判断

        # 检查 version_alignment_gate 的当前条件是否需要进入专门分支。
        if not path.is_file():

            # 分隔 version_alignment_gate 的控制流边界。
            continue

        # 调用 append 完成 version_alignment_gate 的当前动作。
        list_checked.append(rel_path)

        # 保留 actual 中间值，支撑 version_alignment_gate 的当前计算步骤。
        str_actual = first_version(path.read_text(encoding="utf-8", errors="ignore"))  # actual 用于本步治理判断

        # 检查 version_alignment_gate 的当前条件是否需要进入专门分支。
        if str_actual and str_actual != tuple_expected:

            # 调用 append 完成 version_alignment_gate 的当前动作。
            list_errors.append(f"{rel_path} {label} version {str_actual} does not match project skill VERSION {tuple_expected}")

    # 保留 git manager 中间值，支撑 version_alignment_gate 的当前计算步骤。
    git_manager = project / "docs" / "git_manager" / "GIT_MANAGER.md"  # git manager 用于本步治理判断

    # 检查 version_alignment_gate 的当前条件是否需要进入专门分支。
    if git_manager.is_file():

        # 调用 append 完成 version_alignment_gate 的当前动作。
        list_checked.append("docs/git_manager/GIT_MANAGER.md")

        # 保留 actual 中间值，支撑 version_alignment_gate 的当前计算步骤。
        str_actual = first_version(current_version_section(git_manager.read_text(encoding="utf-8", errors="ignore")))  # actual 用于本步治理判断

        # 检查 version_alignment_gate 的当前条件是否需要进入专门分支。
        if str_actual and str_actual != tuple_expected:

            # 调用 append 完成 version_alignment_gate 的当前动作。
            list_errors.append(
                f"docs/git_manager/GIT_MANAGER.md current version {str_actual} does not match project skill VERSION {tuple_expected}"
            )

    # 返回 version_alignment_gate 已整理完成的调用载荷。
    return {
        "project": str(project),
        "skill_dir": str(tuple_skill_dir),
        "expected_version": tuple_expected,
        "version_source": tuple_version_source,
        "checked": list_checked,
        "errors": list_errors,
        "ok": not list_errors,
    }

# 定义 sync_root_agents 的脚本治理处理入口。
def sync_root_agents(
    project: Path,
    write: bool = False,
    installed_skill_dir_override: str | Path | None = None,
    *,
    mark_verified: bool = False,
) -> dict[str, Any]:

    # 定位 agents path 的文件边界，供 sync_root_agents 后续读写校验使用。
    agents_path = project / "AGENTS.md"  # agents path 用于本步治理判断

    # 保留 profile 中间值，支撑 sync_root_agents 的当前计算步骤。
    profile = project_profile(project)  # profile 用于本步治理判断

    # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
    if write and profile:

        # 调用 ensure_global_rule_overrides_file 完成 sync_root_agents 的当前动作。
        ensure_global_rule_overrides_file(project, profile)

    # 保留 repair command 中间值，支撑 sync_root_agents 的当前计算步骤。
    repair_command = root_agents_sync_command(project, profile, installed_skill_dir_override)  # repair command 用于本步治理判断

    # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
    if not agents_path.exists():

        # 返回 sync_root_agents 已整理完成的调用载荷。
        return {
            "project": str(project),
            "agents_path": str(agents_path),
            "expected_version": "",
            "version_source": "unavailable",
            "sync_required": False,
            "updated": False,
            "reasons": [],
            "errors": ["root AGENTS.md does not exist; render or write AGENTS.md before syncing metadata"],
            "repair_command": repair_command,
        }

    # 保留 metadata version、version source、project version 中间值，支撑 sync_root_agents 的当前计算步骤。
    tuple_metadata_version, tuple_version_source, tuple_project_version, tuple_project_version_source, tuple_project_skill_dir = root_metadata_version(  # metadata version、version source、project version 用于本步治理判断
        project,  # metadata version、version source、project version 用于本步治理判断
        installed_skill_dir_override,  # metadata version、version source、project version 用于本步治理判断
    )

    # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
    if not tuple_metadata_version:

        # 返回 sync_root_agents 已整理完成的调用载荷。
        return {
            "project": str(project),
            "agents_path": str(agents_path),
            "expected_version": "",
            "version_source": tuple_version_source,
            "project_skill_version": tuple_project_version,
            "project_version_source": tuple_project_version_source,
            "project_skill_dir": str(tuple_project_skill_dir) if tuple_project_skill_dir else "",
            "sync_required": False,
            "updated": False,
            "reasons": [],
            "errors": ["agents-md-generator version is unavailable; cannot sync root AGENTS metadata"],
            "repair_command": repair_command,
        }

    # 保留 text 中间值，支撑 sync_root_agents 的当前计算步骤。
    str_text = agents_path.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

    # 保留 metadata 中间值，支撑 sync_root_agents 的当前计算步骤。
    metadata = parse_agents_metadata(str_text)  # metadata 用于本步治理判断

    # 保留 last updated match 中间值，支撑 sync_root_agents 的当前计算步骤。
    last_updated_match = LAST_UPDATED_HEADER_RE.search(str_text)  # last updated match 用于本步治理判断

    # 保留 last updated raw 中间值，支撑 sync_root_agents 的当前计算步骤。
    last_updated_raw = last_updated_match.group(1).strip() if last_updated_match else ""  # last updated raw 用于本步治理判断

    # 保留 last verified 中间值，支撑 sync_root_agents 的当前计算步骤。
    last_verified = last_updated_match.group(2).strip() if last_updated_match else "never"  # last verified 用于本步治理判断

    # 保留 default language 中间值，支撑 sync_root_agents 的当前计算步骤。
    default_language = metadata.get("default_language", "中文").strip() or "中文"  # default language 用于本步治理判断

    # 收集 reasons 条目，保持 sync_root_agents 的处理顺序稳定。
    list_reasons: list[str] = []  # reasons 用于本步治理判断

    # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
    if not last_updated_match:

        # 调用 append 完成 sync_root_agents 的当前动作。
        list_reasons.append("missing_last_updated_header")

    # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
    elif "T" not in last_updated_raw:

        # 调用 append 完成 sync_root_agents 的当前动作。
        list_reasons.append("legacy_last_updated_format")

    # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
    if not metadata.get("agents_version"):

        # 调用 append 完成 sync_root_agents 的当前动作。
        list_reasons.append("missing_agents_version")

    # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
    elif metadata.get("agents_version") != tuple_metadata_version:

        # 调用 append 完成 sync_root_agents 的当前动作。
        list_reasons.append("agents_version_mismatch")

    # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
    if not metadata.get("generator_version"):

        # 调用 append 完成 sync_root_agents 的当前动作。
        list_reasons.append("missing_generator_version")

    # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
    elif metadata.get("generator_version") != tuple_metadata_version:

        # 调用 append 完成 sync_root_agents 的当前动作。
        list_reasons.append("generator_version_mismatch")

    # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
    if not metadata.get("default_language"):

        # 调用 append 完成 sync_root_agents 的当前动作。
        list_reasons.append("missing_default_language")

    # 保留 control profile version 中间值，支撑 sync_root_agents 的当前计算步骤。
    str_control_profile_version = managed_control_profile_version(str_text)  # control profile version 用于本步治理判断

    # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
    if tuple_project_version and str_control_profile_version and str_control_profile_version != tuple_project_version:

        # 调用 append 完成 sync_root_agents 的当前动作。
        list_reasons.append("control_profile_version_mismatch")

    # 保留 sync required 中间值，支撑 sync_root_agents 的当前计算步骤。
    bool_sync_required = bool(list_reasons)  # sync required 用于本步治理判断

    # 保留 updated 中间值，支撑 sync_root_agents 的当前计算步骤。
    bool_updated = False  # updated 用于本步治理判断

    # 保留 synced text 中间值，支撑 sync_root_agents 的当前计算步骤。
    synced_text = str_text  # synced text 用于本步治理判断

    # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
    if write and (bool_sync_required or mark_verified):

        # 保留 new last updated 中间值，支撑 sync_root_agents 的当前计算步骤。
        new_last_updated = current_timestamp()  # new last updated 用于本步治理判断

        # 保留 updated raw 中间值，支撑 sync_root_agents 的当前计算步骤。
        updated_raw = new_last_updated if bool_sync_required or not last_updated_raw else last_updated_raw  # updated raw 用于本步治理判断

        # 保留 verified raw 中间值，支撑 sync_root_agents 的当前计算步骤。
        verified_raw = current_timestamp() if mark_verified else last_verified  # verified raw 用于本步治理判断

        # 保留 new last line 中间值，支撑 sync_root_agents 的当前计算步骤。
        new_last_line = f"<!-- Last updated: {updated_raw} | Last verified: {verified_raw} -->"  # new last line 用于本步治理判断

        # 保留 new metadata line 中间值，支撑 sync_root_agents 的当前计算步骤。
        new_metadata_line = (  # new metadata line 用于本步治理判断
            f"<!-- AGENTS-METADATA: agents_version={tuple_metadata_version}; "  # new metadata line 用于本步治理判断
            f"generator_version={tuple_metadata_version}; default_language={default_language} -->"  # new metadata line 用于本步治理判断
        )

        # 保留 original text 中间值，支撑 sync_root_agents 的当前计算步骤。
        original_text = str_text  # original text 用于本步治理判断

        # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
        if tuple_project_version and str_control_profile_version and str_control_profile_version != tuple_project_version:

            # 保留 text 中间值，支撑 sync_root_agents 的当前计算步骤。
            str_text = replace_managed_control_profile_version(str_text, tuple_project_version)  # text 用于本步治理判断

        # 收集 lines 条目，保持 sync_root_agents 的处理顺序稳定。
        lines = str_text.splitlines()  # lines 用于本步治理判断

        # 保留 rewritten 中间值，支撑 sync_root_agents 的当前计算步骤。
        list_rewritten: list[str] = []  # rewritten 用于本步治理判断

        # 保留 last inserted 中间值，支撑 sync_root_agents 的当前计算步骤。
        bool_last_inserted = False  # last inserted 用于本步治理判断

        # 保留 metadata inserted 中间值，支撑 sync_root_agents 的当前计算步骤。
        bool_metadata_inserted = False  # metadata inserted 用于本步治理判断

        # 逐项推进 sync_root_agents 的候选项检查。
        for line in lines:

            # 保留 stripped 中间值，支撑 sync_root_agents 的当前计算步骤。
            stripped = line.strip()  # stripped 用于本步治理判断

            # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
            if stripped.startswith("<!-- Last updated:"):

                # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
                if not bool_last_inserted:

                    # 调用 append 完成 sync_root_agents 的当前动作。
                    list_rewritten.append(new_last_line)

                    # 保留 last inserted 中间值，支撑 sync_root_agents 的当前计算步骤。
                    bool_last_inserted = True  # last inserted 用于本步治理判断

                # 分隔 sync_root_agents 的控制流边界。
                continue

            # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
            if stripped.startswith("<!-- AGENTS-METADATA:"):

                # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
                if not bool_metadata_inserted:

                    # 调用 append 完成 sync_root_agents 的当前动作。
                    list_rewritten.append(new_metadata_line)

                    # 保留 metadata inserted 中间值，支撑 sync_root_agents 的当前计算步骤。
                    bool_metadata_inserted = True  # metadata inserted 用于本步治理判断

                # 分隔 sync_root_agents 的控制流边界。
                continue

            # 调用 append 完成 sync_root_agents 的当前动作。
            list_rewritten.append(line)

        # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
        if not bool_last_inserted or not bool_metadata_inserted:

            # 保留 insert at 中间值，支撑 sync_root_agents 的当前计算步骤。
            int_insert_at = 0  # insert at 用于本步治理判断

            # 在循环条件满足时持续推进处理。
            while int_insert_at < len(list_rewritten) and list_rewritten[int_insert_at].startswith("<!--"):

                # 保留 insert at 中间值，支撑 sync_root_agents 的当前计算步骤。
                int_insert_at += 1  # insert at 用于本步治理判断

            # 收集 missing lines 条目，保持 sync_root_agents 的处理顺序稳定。
            list_missing_lines: list[str] = []  # missing lines 用于本步治理判断

            # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
            if not bool_last_inserted:

                # 调用 append 完成 sync_root_agents 的当前动作。
                list_missing_lines.append(new_last_line)

            # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
            if not bool_metadata_inserted:

                # 调用 append 完成 sync_root_agents 的当前动作。
                list_missing_lines.append(new_metadata_line)

            # 保留 中间载荷 中间值，支撑 sync_root_agents 的当前计算步骤。
            list_rewritten[int_insert_at:int_insert_at] = list_missing_lines  # 中间载荷 用于本步治理判断

        # 保留 synced text 中间值，支撑 sync_root_agents 的当前计算步骤。
        synced_text = "\n".join(list_rewritten).rstrip() + "\n"  # synced text 用于本步治理判断

        # 检查 sync_root_agents 的当前条件是否需要进入专门分支。
        if synced_text != original_text:

            # 调用 write_text 完成 sync_root_agents 的当前动作。
            agents_path.write_text(synced_text, encoding="utf-8")

            # 保留 updated 中间值，支撑 sync_root_agents 的当前计算步骤。
            bool_updated = True  # updated 用于本步治理判断

    # 保留 refreshed match 中间值，支撑 sync_root_agents 的当前计算步骤。
    refreshed_match = LAST_UPDATED_HEADER_RE.search(synced_text)  # refreshed match 用于本步治理判断

    # 保留 refreshed raw 中间值，支撑 sync_root_agents 的当前计算步骤。
    refreshed_raw = refreshed_match.group(1).strip() if refreshed_match else last_updated_raw  # refreshed raw 用于本步治理判断

    # 返回 sync_root_agents 已整理完成的调用载荷。
    return {
        "project": str(project),
        "agents_path": str(agents_path),
        "expected_version": tuple_metadata_version,
        "version_source": tuple_version_source,
        "project_skill_version": tuple_project_version,
        "project_version_source": tuple_project_version_source,
        "project_skill_dir": str(tuple_project_skill_dir) if tuple_project_skill_dir else "",
        "default_language": default_language,
        "last_updated_raw": refreshed_raw,
        "sync_required": bool_sync_required,
        "updated": bool_updated,
        "mark_verified": mark_verified,
        "reasons": list_reasons,
        "errors": [],
        "repair_command": repair_command,
    }

# 定义 global_codex_between_is_replaceable_meta 的脚本治理处理入口。
def global_codex_between_is_replaceable_meta(text: str) -> bool:

    # 保留 stripped 中间值，支撑 global_codex_between_is_replaceable_meta 的当前计算步骤。
    stripped = text.strip()  # stripped 用于本步治理判断

    # 检查 global_codex_between_is_replaceable_meta 的当前条件是否需要进入专门分支。
    if not stripped:

        # 返回 global_codex_between_is_replaceable_meta 已整理完成的调用载荷。
        return True

    # 逐项推进 global_codex_between_is_replaceable_meta 的候选项检查。
    for line in stripped.splitlines():

        # 检查 global_codex_between_is_replaceable_meta 的当前条件是否需要进入专门分支。
        if not GLOBAL_CODEX_AGENTS_META_LINE_RE.fullmatch(line.strip()):

            # 返回 global_codex_between_is_replaceable_meta 已整理完成的调用载荷。
            return False

    # 返回 global_codex_between_is_replaceable_meta 已整理完成的调用载荷。
    return True

# 定义 replace_global_codex_block 的脚本治理处理入口。
def replace_global_codex_block(text: str, rendered: str) -> str:

    # 保留 current 中间值，支撑 replace_global_codex_block 的当前计算步骤。
    current = text  # current 用于本步治理判断

    # 保留 start 中间值，支撑 replace_global_codex_block 的当前计算步骤。
    start = current.find(GLOBAL_CODEX_AGENTS_BLOCK_START)  # start 用于本步治理判断

    # 保留 end 中间值，支撑 replace_global_codex_block 的当前计算步骤。
    end = current.find(GLOBAL_CODEX_AGENTS_BLOCK_END)  # end 用于本步治理判断

    # 检查 replace_global_codex_block 的当前条件是否需要进入专门分支。
    if start == -1 or end == -1 or end < start:

        # 返回 replace_global_codex_block 已整理完成的调用载荷。
        return current

    # 保留 search end 中间值，支撑 replace_global_codex_block 的当前计算步骤。
    search_end = start  # search end 用于本步治理判断

    # 在循环条件满足时持续推进处理。
    while True:

        # 保留 preamble start 中间值，支撑 replace_global_codex_block 的当前计算步骤。
        preamble_start = current.rfind(GLOBAL_CODEX_AGENTS_PREAMBLE, 0, search_end)  # preamble start 用于本步治理判断

        # 检查 replace_global_codex_block 的当前条件是否需要进入专门分支。
        if preamble_start == -1:

            # 分隔 replace_global_codex_block 的控制流边界。
            break

        # 保留 between 中间值，支撑 replace_global_codex_block 的当前计算步骤。
        between = current[preamble_start + len(GLOBAL_CODEX_AGENTS_PREAMBLE) : start]  # between 用于本步治理判断

        # 检查 replace_global_codex_block 的当前条件是否需要进入专门分支。
        if not global_codex_between_is_replaceable_meta(between):

            # 分隔 replace_global_codex_block 的控制流边界。
            break

        # 保留 start 中间值，支撑 replace_global_codex_block 的当前计算步骤。
        start = preamble_start  # start 用于本步治理判断

        # 保留 search end 中间值，支撑 replace_global_codex_block 的当前计算步骤。
        search_end = preamble_start  # search end 用于本步治理判断

    # 保留 end 中间值，支撑 replace_global_codex_block 的当前计算步骤。
    end += len(GLOBAL_CODEX_AGENTS_BLOCK_END)  # end 用于本步治理判断

    # 返回 replace_global_codex_block 已整理完成的调用载荷。
    return (current[:start] + rendered + current[end:]).rstrip() + "\n"

# 定义 sync_global_codex_agents 的脚本治理处理入口。
def sync_global_codex_agents(project: Path, write: bool = False, codex_home: str | None = None) -> dict[str, Any]:

    # 保留 target 中间值，支撑 sync_global_codex_agents 的当前计算步骤。
    target = global_codex_agents_path(codex_home)  # target 用于本步治理判断

    # 保留 profile 中间值，支撑 sync_global_codex_agents 的当前计算步骤。
    profile = project_profile(project)  # profile 用于本步治理判断

    # 收集 status 条目，保持 sync_global_codex_agents 的处理顺序稳定。
    status = global_codex_agents_status(codex_home, project_root=project, profile=profile)  # status 用于本步治理判断

    # 保留 repair command 中间值，支撑 sync_global_codex_agents 的当前计算步骤。
    repair_command = global_codex_agents_sync_command(project, profile)  # repair command 用于本步治理判断

    # 保留 result 中间值，支撑 sync_global_codex_agents 的当前计算步骤。
    dict_result = {  # result 用于本步治理判断
        "project": str(project),  # result 用于本步治理判断
        "target_path": str(target),  # result 用于本步治理判断
        "updated": False,  # result 用于本步治理判断
        "write_requested": write,  # result 用于本步治理判断
        "requires_user_confirmation": status["requires_user_confirmation"],  # result 用于本步治理判断
        "user_message": status["user_message"],  # result 用于本步治理判断
        "repair_command": repair_command,  # result 用于本步治理判断
        **status,  # result 用于本步治理判断
    }

    # 检查 sync_global_codex_agents 的当前条件是否需要进入专门分支。
    if not write:

        # 返回 sync_global_codex_agents 已整理完成的调用载荷。
        return dict_result

    # 调用 mkdir 完成 sync_global_codex_agents 的当前动作。
    target.parent.mkdir(parents=True, exist_ok=True)

    # 检查 sync_global_codex_agents 的当前条件是否需要进入专门分支。
    if target.exists() and not target.is_file():

        # 返回 sync_global_codex_agents 已整理完成的调用载荷。
        return {**dict_result, "errors": [f"global Codex AGENTS target is not a file: {target}"]}

    # 保留 rendered 中间值，支撑 sync_global_codex_agents 的当前计算步骤。
    rendered = render_global_codex_agents_template()  # rendered 用于本步治理判断

    # 保留 current 中间值，支撑 sync_global_codex_agents 的当前计算步骤。
    current = target.read_text(encoding="utf-8", errors="ignore") if target.is_file() else ""  # current 用于本步治理判断

    # 检查 sync_global_codex_agents 的当前条件是否需要进入专门分支。
    if not target.exists() or status["empty"]:

        # 保留 new text 中间值，支撑 sync_global_codex_agents 的当前计算步骤。
        str_new_text = rendered  # new text 用于本步治理判断

    # 检查 sync_global_codex_agents 的当前条件是否需要进入专门分支。
    elif status["managed"]:

        # 保留 new text 中间值，支撑 sync_global_codex_agents 的当前计算步骤。
        str_new_text = replace_global_codex_block(current, rendered)  # new text 用于本步治理判断
    else:

        # 返回 sync_global_codex_agents 已整理完成的调用载荷。
        return dict_result

    # 检查 sync_global_codex_agents 的当前条件是否需要进入专门分支。
    if str_new_text != current:

        # 调用 write_text 完成 sync_global_codex_agents 的当前动作。
        target.write_text(str_new_text, encoding="utf-8")

        # 保留 中间载荷 中间值，支撑 sync_global_codex_agents 的当前计算步骤。
        dict_result["updated"] = True  # 中间载荷 用于本步治理判断

    # 保留 refreshed 中间值，支撑 sync_global_codex_agents 的当前计算步骤。
    refreshed = global_codex_agents_status(codex_home, project_root=project, profile=profile)  # refreshed 用于本步治理判断

    # 调用 update 完成 sync_global_codex_agents 的当前动作。
    dict_result.update(refreshed)

    # 保留 中间载荷 中间值，支撑 sync_global_codex_agents 的当前计算步骤。
    dict_result["repair_command"] = repair_command  # 中间载荷 用于本步治理判断

    # 返回 sync_global_codex_agents 已整理完成的调用载荷。
    return dict_result

# 定义 audit_docs_private_paths 的脚本治理处理入口。
def audit_docs_private_paths(project: Path) -> dict[str, Any]:

    # 收集 checked 条目，保持 audit_docs_private_paths 的处理顺序稳定。
    list_checked: list[str] = []  # checked 用于本步治理判断

    # 收集 errors 条目，保持 audit_docs_private_paths 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 逐项推进 audit_docs_private_paths 的候选项检查。
    for rel_root in DOCS_PRIVACY_ROOTS:

        # 保留 root 中间值，支撑 audit_docs_private_paths 的当前计算步骤。
        root = project / rel_root  # root 用于本步治理判断

        # 检查 audit_docs_private_paths 的当前条件是否需要进入专门分支。
        if not root.exists():

            # 分隔当前处理项，继续后续治理目录扫描。
            continue

        # 逐项推进 audit_docs_private_paths 的候选项检查。
        for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):

            # 检查 audit_docs_private_paths 的当前条件是否需要进入专门分支。
            if path.suffix.lower() not in DOCS_PRIVACY_TEXT_SUFFIXES:

                # 分隔当前处理项，继续后续治理文档扫描。
                continue

            # 保护 audit_docs_private_paths 中允许失败的外部访问。
            try:

                # 定位 rel path 的文件边界，供 audit_docs_private_paths 后续读写校验使用。
                rel_path = path.relative_to(project).as_posix()  # rel path 用于本步治理判断
            except ValueError:

                # 定位 rel path 的文件边界，供 audit_docs_private_paths 后续读写校验使用。
                rel_path = str(path)  # rel path 用于本步治理判断

            # 调用 append 完成 audit_docs_private_paths 的当前动作。
            list_checked.append(rel_path)

            # 保留 text 中间值，支撑 audit_docs_private_paths 的当前计算步骤。
            text = path.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

            # 检查 audit_docs_private_paths 的当前条件是否需要进入专门分支。
            if LOCAL_PRIVATE_PATH_RE.search(text):

                # 调用 append 完成 audit_docs_private_paths 的当前动作。
                list_errors.append(f"{rel_path}: raw local private path must be redacted")

    # 返回 audit_docs_private_paths 已整理完成的调用载荷。
    return {"checked": list_checked, "errors": list_errors}

# 定义 verify_docs 的脚本治理处理入口。
def verify_docs(project: Path) -> dict[str, Any]:
    from manage_docs_memory import verify_memory

    # 收集 errors 条目，保持 verify_docs 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 保留 checked 中间值，支撑 verify_docs 的当前计算步骤。
    list_checked: list[str] = []  # checked 用于本步治理判断

    # 逐项推进 verify_docs 的候选项检查。
    for rel_path in DOC_DIRS:

        # 调用 append 完成 verify_docs 的当前动作。
        list_checked.append(rel_path)

        # 检查 verify_docs 的当前条件是否需要进入专门分支。
        if not (project / rel_path).is_dir():

            # 调用 append 完成 verify_docs 的当前动作。
            list_errors.append(f"missing docs governance directory: {rel_path}")

    # 逐项推进 verify_docs 的候选项检查。
    for rel_path in REQUIRED_DOC_FILES:

        # 调用 append 完成 verify_docs 的当前动作。
        list_checked.append(rel_path)

        # 检查 verify_docs 的当前条件是否需要进入专门分支。
        if not (project / rel_path).is_file():

            # 调用 append 完成 verify_docs 的当前动作。
            list_errors.append(f"missing docs governance file: {rel_path}")

    # 保留 handoff naming 中间值，支撑 verify_docs 的当前计算步骤。
    handoff_naming = audit_handoff_naming(project)  # handoff naming 用于本步治理判断

    # 调用 extend 完成 verify_docs 的当前动作。
    list_checked.extend(item for item in handoff_naming["checked"] if item not in list_checked)

    # 调用 extend 完成 verify_docs 的当前动作。
    list_errors.extend(item for item in handoff_naming["errors"] if item not in list_errors)

    # 保留 development current 中间值，支撑 verify_docs 的当前计算步骤。
    development_current = project / "docs" / "development" / "DEVELOPMENT.md"  # development current 用于本步治理判断

    # 检查 verify_docs 的当前条件是否需要进入专门分支。
    if development_current.exists():

        # 调用 extend 完成 verify_docs 的当前动作。
        list_errors.extend(validate_development_record(development_current))

    # 保留 handoff 中间值，支撑 verify_docs 的当前计算步骤。
    handoff = project / "docs" / "handoff" / "HANDOFF.md"  # handoff 用于本步治理判断

    # 检查 verify_docs 的当前条件是否需要进入专门分支。
    if handoff.exists():

        # 保留 text 中间值，支撑 verify_docs 的当前计算步骤。
        text = handoff.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

        # 逐项推进 verify_docs 的候选项检查。
        for section in HANDOFF_SECTIONS:

            # 检查 verify_docs 的当前条件是否需要进入专门分支。
            if f"## {section}" not in text:

                # 调用 append 完成 verify_docs 的当前动作。
                list_errors.append(f"docs/handoff/HANDOFF.md: missing section ## {section}")

    # 保留 dir result 中间值，支撑 verify_docs 的当前计算步骤。
    dir_result = verify_dir_manager(project)  # dir result 用于本步治理判断

    # 调用 extend 完成 verify_docs 的当前动作。
    list_checked.extend(dir_result["checked"])

    # 调用 extend 完成 verify_docs 的当前动作。
    list_errors.extend(dir_result["errors"])

    # 保留 memory result 中间值，支撑 verify_docs 的当前计算步骤。
    memory_result = verify_memory(project)  # memory result 用于本步治理判断

    # 调用 extend 完成 verify_docs 的当前动作。
    list_checked.extend(item for item in memory_result.get("checked", []) if item not in list_checked)

    # 调用 extend 完成 verify_docs 的当前动作。
    list_errors.extend(item for item in memory_result.get("errors", []) if item not in list_errors)

    # 保留 privacy result 中间值，支撑 verify_docs 的当前计算步骤。
    privacy_result = audit_docs_private_paths(project)  # privacy result 用于本步治理判断

    # 调用 extend 完成 verify_docs 的当前动作。
    list_checked.extend(item for item in privacy_result.get("checked", []) if item not in list_checked)

    # 调用 extend 完成 verify_docs 的当前动作。
    list_errors.extend(item for item in privacy_result.get("errors", []) if item not in list_errors)

    # 保留 version result 中间值，支撑 verify_docs 的当前计算步骤。
    dict_version_result = version_alignment_gate(project)  # version result 用于本步治理判断

    # 调用 extend 完成 verify_docs 的当前动作。
    list_checked.extend(dict_version_result["checked"])

    # 调用 extend 完成 verify_docs 的当前动作。
    list_errors.extend(dict_version_result["errors"])

    # 逐项推进 verify_docs 的候选项检查。
    for legacy in [project / "HANDOFF.md", project / "DEVELOPMENT.md", project / "docs" / "HANDOFF.md", project / "docs" / "DEVELOPMENT.md"]:

        # 检查 verify_docs 的当前条件是否需要进入专门分支。
        if legacy.exists():

            # 保护 verify_docs 中允许失败的外部访问。
            try:

                # 调用 append 完成 verify_docs 的当前动作。
                list_errors.append(f"legacy docs path must be migrated into governed docs layout: {legacy.relative_to(project).as_posix()}")
            except ValueError:

                # 调用 append 完成 verify_docs 的当前动作。
                list_errors.append(f"legacy docs path must be migrated into governed docs layout: {legacy}")

    # 返回 verify_docs 已整理完成的调用载荷。
    return {"project": str(project), "checked": list_checked, "errors": list_errors, "handoff_naming": handoff_naming}

# 定义 run_json_command 的脚本治理处理入口。
def run_json_command(project: Path, argv: list[str]) -> dict[str, Any]:

    # 保留 result 中间值，支撑 run_json_command 的当前计算步骤。
    command_result = subprocess.run(argv, cwd=project, text=True, capture_output=True, check=False, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))  # result 用于本步治理判断

    # 保留 parsed 中间值，支撑 run_json_command 的当前计算步骤。
    dict_parsed: dict[str, Any]  # parsed 用于本步治理判断

    # 保护 run_json_command 中允许失败的外部访问。
    try:

        # 保留 loaded 中间值，支撑 run_json_command 的当前计算步骤。
        loaded = json.loads(command_result.stdout)  # loaded 用于本步治理判断

        # 保留 parsed 中间值，支撑 run_json_command 的当前计算步骤。
        dict_parsed = loaded if isinstance(loaded, dict) else {}  # parsed 用于本步治理判断
    except json.JSONDecodeError:

        # 保留 parsed 中间值，支撑 run_json_command 的当前计算步骤。
        dict_parsed = {}  # parsed 用于本步治理判断

    # 返回 run_json_command 已整理完成的调用载荷。
    return {
        "argv": argv,
        "returncode": command_result.returncode,
        "stdout": command_result.stdout,
        "stderr": command_result.stderr,
        "json": dict_parsed,
    }

# 定义 work_folder_gate 的脚本治理处理入口。
def work_folder_gate(project: Path, skill_dir_raw: str, mode: str = "development") -> dict[str, Any]:
    from manage_dirs import structure_gate
    from manage_docs_scaffold_session import resume_check
    from manage_docs_release import branch_gate

    # 保留 skill dir 中间值，支撑 work_folder_gate 的当前计算步骤。
    skill_dir = inferred_skill_dir(project, skill_dir_raw)  # skill dir 用于本步治理判断

    # 保留 resume 中间值，支撑 work_folder_gate 的当前计算步骤。
    resume = resume_check(project)  # resume 用于本步治理判断

    # 保留 docs verify 中间值，支撑 work_folder_gate 的当前计算步骤。
    docs_verify = verify_docs(project) if docs_governance_initialized(project) else {"project": str(project), "checked": [], "errors": []}  # docs verify 用于本步治理判断

    # 保留 structure 中间值，支撑 work_folder_gate 的当前计算步骤。
    structure = structure_gate(project)  # structure 用于本步治理判断

    # 保留 dir manager 中间值，支撑 work_folder_gate 的当前计算步骤。
    dir_manager = verify_dir_manager(project)  # dir manager 用于本步治理判断

    # 保留 branch 中间值，支撑 work_folder_gate 的当前计算步骤。
    branch = branch_gate(project)  # branch 用于本步治理判断

    # 保留 version 中间值，支撑 work_folder_gate 的当前计算步骤。
    dict_version = version_alignment_gate(project, skill_dir)  # version 用于本步治理判断

    # 保留 source governance 中间值，支撑 work_folder_gate 的当前计算步骤。
    source_governance = source_governance_report(project, control_profile(project))  # source governance 用于本步治理判断

    # 保留 freshness script 中间值，支撑 work_folder_gate 的当前计算步骤。
    str_freshness_script = governance_script_path(project, "check_freshness.py")  # freshness script 用于本步治理判断

    # 保留 freshness candidate 中间值，支撑 work_folder_gate 的当前计算步骤。
    path_freshness_candidate = Path(str_freshness_script)  # freshness candidate 用于本步治理判断

    # 检查 work_folder_gate 的当前条件是否需要进入专门分支。
    if not path_freshness_candidate.is_absolute():

        # 保留 freshness candidate 中间值，支撑 work_folder_gate 的当前计算步骤。
        path_freshness_candidate = project / path_freshness_candidate  # freshness candidate 用于本步治理判断

    # 检查 work_folder_gate 的当前条件是否需要进入专门分支。
    if str_freshness_script.startswith("<codex-home>") or not path_freshness_candidate.exists():

        # 保留 fallback dir 中间值，支撑 work_folder_gate 的当前计算步骤。
        fallback_dir = os.environ.get("AGENTS_MD_INSTALLED_SKILL_DIR") or Path(__file__).resolve().parents[3]  # fallback dir 用于本步治理判断

        # 保留 freshness script 中间值，支撑 work_folder_gate 的当前计算步骤。
        str_freshness_script = str(Path(fallback_dir) / "scripts" / "python" / "detect" / "check_freshness.py")  # freshness script 用于本步治理判断

    # 保留 freshness command 中间值，支撑 work_folder_gate 的当前计算步骤。
    dict_freshness_command = run_json_command(project, [sys.executable, str_freshness_script, str(project)])  # freshness command 用于本步治理判断

    # 收集 freshness 条目，保持 work_folder_gate 的处理顺序稳定。
    freshness = dict_freshness_command["json"]  # freshness 用于本步治理判断

    # 收集 errors 条目，保持 work_folder_gate 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 保留 resume policy 中间值，支撑 work_folder_gate 的当前计算步骤。
    dict_resume_policy = {  # resume policy 用于本步治理判断
        "blocking": False,  # resume policy 用于本步治理判断
        "reason": (  # 活动会话不阻断当前流程的说明文本
            "work-folder-gate reports active-session state but does not block the "  # 活动会话门禁说明前半句
            "current in-progress session; run resume-check before starting new work."  # 新工作启动前检查提示
        ),  # resume policy 用于本步治理判断
    }

    # 检查 work_folder_gate 的当前条件是否需要进入专门分支。
    if resume.get("blocking") is True:

        # 调用 extend 完成 work_folder_gate 的当前动作。
        list_errors.extend(f"resume-check: {item}" for item in resume.get("reasons", []))

    # 调用 extend 完成 work_folder_gate 的当前动作。
    list_errors.extend(f"docs-verify: {item}" for item in docs_verify.get("errors", []))

    # 检查 work_folder_gate 的当前条件是否需要进入专门分支。
    if not structure.get("approved", True):

        # 调用 extend 完成 work_folder_gate 的当前动作。
        list_errors.extend(f"structure-gate: {item}" for item in structure.get("reasons", []))

    # 调用 extend 完成 work_folder_gate 的当前动作。
    list_errors.extend(f"dir-manager: {item}" for item in dir_manager.get("errors", []))

    # 检查 work_folder_gate 的当前条件是否需要进入专门分支。
    if not branch.get("approved", True):

        # 调用 extend 完成 work_folder_gate 的当前动作。
        list_errors.extend(f"branch-gate: {item}" for item in branch.get("reasons", []))

    # 调用 extend 完成 work_folder_gate 的当前动作。
    list_errors.extend(f"version-gate: {item}" for item in dict_version.get("errors", []))

    # 调用 extend 完成 work_folder_gate 的当前动作。
    list_errors.extend(format_source_governance_errors(source_governance, prefix="source-governance"))

    # 检查 work_folder_gate 的当前条件是否需要进入专门分支。
    if dict_freshness_command["returncode"] != 0:

        # 调用 append 完成 work_folder_gate 的当前动作。
        list_errors.append("check_freshness command failed")

    # 检查 work_folder_gate 的当前条件是否需要进入专门分支。
    if freshness.get("stale") is True:

        # 调用 append 完成 work_folder_gate 的当前动作。
        list_errors.append("AGENTS.md freshness check is stale")

    # 检查 work_folder_gate 的当前条件是否需要进入专门分支。
    if mode == "release" and not skill_dir:

        # 调用 append 完成 work_folder_gate 的当前动作。
        list_errors.append("release work-folder gate requires a resolved skill directory")

    # 返回 work_folder_gate 已整理完成的调用载荷。
    return {
        "project": str(project),
        "mode": mode,
        "skill_dir": str(skill_dir) if skill_dir else "",
        "ok": not list_errors,
        "errors": list_errors,
        "resume_check": resume,
        "resume_policy": dict_resume_policy,
        "docs_verify": docs_verify,
        "structure_gate": structure,
        "dir_manager": dir_manager,
        "branch_gate": branch,
        "version_gate": dict_version,
        "source_governance": source_governance,
        "freshness": freshness,
    }


