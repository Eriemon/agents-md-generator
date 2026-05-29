from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import (
    SKIP_DIRS,
    decomposition_plan_path,
    emit_json,
    evolution_owner_status,
    global_codex_agents_status,
    inspect_project,
    load_global_rule_overrides,
    parse_agents_metadata,
    project_profile,
    read_installed_skill_version,
    resolve_project,
    root_agents_sync_command,
    global_codex_agents_sync_command,
)
from manage_docs import verify_docs
from source_governance import format_source_governance_errors, source_governance_report


COMMAND_RE = re.compile(r"`([^`\n]+)`")
PATH_RE = re.compile(r"`([^`\n]+(?:/|\\|\.md|\.json|\.toml|\.yml|\.yaml|\.py|\.ts|\.tsx|\.go|\.php)[^`\n]*)`")
ROOT_AGENTS_MAX_BYTES = 16 * 1024
LANGUAGE_LOCK_RE = re.compile(
    r"All natural-language responses must use\s+(.+?)\s+unless the user explicitly switches languages\.",
    flags=re.IGNORECASE,
)
PLAN_LANGUAGE_LOCK_RE = re.compile(
    r"In Plan Mode,\s+any content inside\s+`<proposed_plan>`\s+must use\s+(.+?)\s+unless the user explicitly switches languages\.",
    flags=re.IGNORECASE,
)
CODE_COMMENT_POLICY_REQUIRED_SNIPPETS = (
    "配置来源：`.agents/global-rule-overrides.json`",
    "默认只允许非显然意图、不变量、风险、生成边界或公共 API 行为注释",
    "禁止复述代码",
    "禁止未经明确要求的批量 AI 注释",
    "行为变化时必须更新旧注释",
    "不能把语句、注释、函数粘连到一起",
    "Python：公共函数/类使用规范 docstring",
    "普通说明注释放在代码上方",
    "禁止右侧尾注释",
    "C/C++：函数、模块核心功能、变量定义和特定功能说明放在代码上方",
    "所有权/生命周期",
    "#define",
    "Verilog/SystemVerilog：信号声明、参数定义、assign 和 always 块内寄存器赋值使用右侧注释",
    "module/task/function/generate/always 说明放在语句上方",
)
PROJECT_LOCAL_GOVERNANCE_RUNTIME_RE = re.compile(
    r"`python\s+(?:scripts/|skills/[^/\s]+/scripts/)(?:manage_docs|manage_dirs|verify_agents|evaluate_skill|review_governance|run_confidence_gate|collect_design_profile|render_agents)\.py\b[^`]*`"
)


def validate_markers(text: str, file: str, errors: list[str]) -> None:
    starts = len(re.findall(r"AGENTS-GENERATED:START", text))
    ends = len(re.findall(r"AGENTS-GENERATED:END", text))
    if starts != ends:
        errors.append(f"{file}: generated marker mismatch ({starts} starts, {ends} ends)")


def section_body(text: str, heading: str) -> str | None:
    match = re.search(rf"^{re.escape(heading)}\s*$", text, flags=re.MULTILINE)
    if not match:
        return None
    start = match.end()
    next_heading = re.search(r"^##\s+", text[start:], flags=re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def validate_strong_control(text: str, file: str, project: Path, errors: list[str]) -> None:
    required_sections = [
        "## Control Profile",
        "## Directory Contract",
        "## Release Contract",
        "## Engineering Rule Contract",
        "## Conversation Completion Contract",
        "## Documentation Governance Contract",
    ]
    if "Strong control: complete" not in text:
        return
    for section in required_sections:
        if section not in text:
            errors.append(f"{file}: missing strong-control section {section}")
    if not (project / ".agents" / "agents-control.json").exists():
        errors.append(f"{file}: strong control requires .agents/agents-control.json")
    docs_result = verify_docs(project)
    errors.extend(f"{file}: {item}" for item in docs_result["errors"])
    profile = read_json(project / ".agents" / "agents-control.json")
    if not str(profile.get("default_conversation_language", "")).strip():
        errors.append(f"{file}: strong-control profile must explicitly set default_conversation_language")
    extra_requirements = str(profile.get("extra_requirements", "")).strip()
    if extra_requirements and extra_requirements.casefold() != "none" and extra_requirements not in text:
        errors.append(f"{file}: Control Profile must render extra_requirements from .agents/agents-control.json")
    directory_contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract", {}), dict) else {}
    directory_body = section_body(text, "## Directory Contract")
    if directory_body is None:
        errors.append(f"{file}: strong-control profile requires ## Directory Contract")
    else:
        settings_policy = directory_contract.get("workspace_settings_policy", {}) if isinstance(directory_contract.get("workspace_settings_policy", {}), dict) else {}
        remote_environment = directory_contract.get("remote_environment_policy", {}) if isinstance(directory_contract.get("remote_environment_policy", {}), dict) else {}
        remote_runtime = directory_contract.get("remote_runtime_archive_policy", {}) if isinstance(directory_contract.get("remote_runtime_archive_policy", {}), dict) else {}
        settings_folder = str(settings_policy.get("folder", ".settings")).strip() or ".settings"
        local_default = str(settings_policy.get("local_default_file", ".settings/project.local.json")).strip() or ".settings/project.local.json"
        remote_default = str(settings_policy.get("remote_default_file", ".settings/project.remote.json")).strip() or ".settings/project.remote.json"
        if local_default not in directory_body:
            errors.append(f"{file}: Directory Contract must include local workspace settings path `{local_default}`")
        if remote_default not in directory_body:
            errors.append(f"{file}: Directory Contract must include remote workspace settings path `{remote_default}`")
        if f"`{settings_folder}/*.local.json`" not in directory_body and f"{settings_folder}/*.local.json" not in directory_body:
            errors.append(f"{file}: Directory Contract must state that `{settings_folder}/*.local.json` is local-only")
        if "server_list.local.json" not in directory_body:
            errors.append(f"{file}: Directory Contract must explicitly forbid copying server_list.local.json to remote servers")
        required_root_artifact_phrases = (
            "`tests/`",
            "`smoke/` and `smoke-*`",
            "`reports/`",
            "`runs/`",
            "work-folder root",
            "do not place them under the primary project root",
        )
        for phrase in required_root_artifact_phrases:
            if phrase not in directory_body:
                errors.append(f"{file}: Directory Contract must describe root-level workspace artifact rule `{phrase}`")
        if str(profile.get("kind", "")).strip().lower() == "skill":
            primary_root = str(directory_contract.get("primary_project_root", "")).strip().rstrip("/")
            evals_phrase = f"`{primary_root}/evals/`" if primary_root else "/evals/"
            if evals_phrase not in directory_body:
                errors.append(f"{file}: Directory Contract must state that skill-local evals stay under `{primary_root}/evals/`")
        if remote_environment.get("status") == "enabled":
            path_template = str(remote_environment.get("path_template", "")).strip()
            if not path_template:
                errors.append(f"{file}: directory_contract.remote_environment_policy.path_template must be configured when enabled")
            elif path_template not in directory_body:
                errors.append(f"{file}: Directory Contract must include remote conda environment path `{path_template}`")
        if remote_runtime.get("status") == "enabled":
            active_path = str(remote_runtime.get("active_path_template", "")).strip()
            backup_path = str(remote_runtime.get("backup_path_template", "")).strip()
            trigger = str(remote_runtime.get("archive_trigger", "")).strip()
            if active_path and active_path not in directory_body:
                errors.append(f"{file}: Directory Contract must include remote runtime active path `{active_path}`")
            if backup_path and backup_path not in directory_body:
                errors.append(f"{file}: Directory Contract must include remote runtime backup path `{backup_path}`")
            if trigger and trigger not in directory_body:
                errors.append(f"{file}: Directory Contract must include remote runtime archive trigger `{trigger}`")
    remote_contract = profile.get("remote_server_contract", {}) if isinstance(profile.get("remote_server_contract", {}), dict) else {}
    if remote_contract:
        remote_body = section_body(text, "## Remote Server Contract")
        if remote_body is None:
            errors.append(f"{file}: strong-control profile with remote_server_contract requires ## Remote Server Contract")
        else:
            if remote_contract.get("enabled"):
                registry = remote_contract.get("server_registry", [])
                routes = remote_contract.get("task_routes", [])
                if not isinstance(registry, list) or not registry:
                    errors.append(f"{file}: remote_server_contract.enabled requires server_registry")
                    registry = []
                if not isinstance(routes, list) or not routes:
                    errors.append(f"{file}: remote_server_contract.enabled requires task_routes")
                    routes = []
                registry_ids = {str(item.get("id", "")).strip() for item in registry if isinstance(item, dict) and str(item.get("id", "")).strip()}
                for route in routes:
                    if not isinstance(route, dict):
                        errors.append(f"{file}: remote_server_contract.task_routes must contain objects")
                        continue
                    task_name = str(route.get("task_name", "")).strip()
                    primary_id = str(route.get("primary_server_id", "")).strip()
                    fallback_ids = [str(item).strip() for item in route.get("fallback_server_ids", []) if str(item).strip()] if isinstance(route.get("fallback_server_ids", []), list) else []
                    route_tasks = route.get("route_tasks", [])
                    if not task_name:
                        errors.append(f"{file}: remote_server_contract.task_routes requires task_name")
                    if not primary_id:
                        errors.append(f"{file}: remote_server_contract.task_routes requires primary_server_id")
                    elif primary_id not in registry_ids:
                        errors.append(f"{file}: remote_server_contract.task_routes references unknown primary_server_id `{primary_id}`")
                    for fallback_id in fallback_ids:
                        if fallback_id not in registry_ids:
                            errors.append(f"{file}: remote_server_contract.task_routes references unknown fallback_server_id `{fallback_id}`")
                    if not isinstance(route_tasks, list) or not [str(item).strip() for item in route_tasks if str(item).strip()]:
                        errors.append(f"{file}: remote_server_contract.task_routes requires route_tasks")
                    if task_name and f"`{task_name}`" not in remote_body:
                        errors.append(f"{file}: Remote Server Contract must include the task route `{task_name}`")
                    if primary_id and f"`{primary_id}`" not in remote_body:
                        errors.append(f"{file}: Remote Server Contract must include the primary server `{primary_id}`")
                if "automatically try the registered fallback servers in order" not in remote_body:
                    errors.append(f"{file}: Remote Server Contract must enforce automatic fallback routing")
                if "stop and update the current work folder AGENTS.md before continuing" not in remote_body:
                    errors.append(f"{file}: Remote Server Contract must enforce unmatched-task blocking")
            else:
                if "No remote server task routes are registered right now" not in remote_body:
                    errors.append(f"{file}: Remote Server Contract must state that no remote server task routes are registered when remote usage is disabled")
    git_management = str(profile.get("git_management", "")).strip()
    if git_management in {"yes-local-only", "remote-allowed"}:
        release_body = section_body(text, "## Release Contract")
        if release_body is None:
            errors.append(f"{file}: git-managed strong-control project requires ## Release Contract")
        elif "core.worktree" not in release_body or "Do not repoint repositories" not in release_body:
            errors.append(f"{file}: Release Contract must explicitly forbid `git config core.worktree` for git-managed workflows")
        else:
            release_required_phrases = (
                "`evals/`",
                "`tests/`",
                "`test/`",
                "`smoke*`",
                "`reports/`",
                "`runs/`",
            )
            for phrase in release_required_phrases:
                if phrase not in release_body:
                    errors.append(f"{file}: Release Contract must include release-content policy phrase `{phrase}`")
    if profile.get("kind") == "skill":
        contract_body = section_body(text, "## Skill Design Contract")
        if contract_body is None:
            errors.append(f"{file}: strong-control skill project requires ## Skill Design Contract")
            return
        required_phrases = [
            "Trigger scenarios:",
            "Design patterns:",
            "Resource boundaries:",
            "Progressive disclosure:",
            "Validation gates:",
            "Forward testing:",
        ]
        for phrase in required_phrases:
            if phrase not in contract_body:
                errors.append(f"{file}: Skill Design Contract missing {phrase}")
        vague_markers = [
            "Trigger scenarios: not specified",
            "Design patterns: not specified",
            "Resource boundaries: not specified",
            "Progressive disclosure: not specified",
            "Validation gates: not specified",
            "Forward testing: not specified",
        ]
        for marker in vague_markers:
            if marker in contract_body:
                errors.append(f"{file}: Skill Design Contract contains unresolved default: {marker}")
        gates_match = re.search(r"Validation gates:\s*(.+)", contract_body, flags=re.IGNORECASE)
        gates_text = gates_match.group(1).lower() if gates_match else ""
        for required_gate in ("quick_validate", "audit", "verify"):
            if required_gate not in gates_text:
                errors.append(f"{file}: Skill Design Contract validation gates must include {required_gate}")
    config = load_global_rule_overrides(project, profile)
    config_path = config["path"].relative_to(project).as_posix()
    if config_path not in text:
        errors.append(f"{file}: strong-control root must reference local governance config `{config_path}`")
    if not config["exists"]:
        errors.append(f"{file}: missing local governance config `{config_path}`")
    for item in config["errors"]:
        errors.append(f"{file}: invalid local governance config `{config_path}`: {item}")
    forbidden_snippets = (
        "Single-file maintainability",
        "docs/development/decomposition-plans/",
        ".agents/script-governance-exceptions.json",
        "Project tool scripts must live under",
        "scripts/<family>/<function>/<name>.<ext>",
    )
    for snippet in forbidden_snippets:
        if snippet in text:
            errors.append(f"{file}: local rule detail must move to JSON config instead of AGENTS text ({snippet})")


def validate_code_comment_policy(text: str, file: str, project: Path, profile: dict, errors: list[str]) -> bool:
    body = section_body(text, "## Code Comment Policy")
    if body is None:
        errors.append(f"{file}: missing Code Comment Policy; refresh the managed root AGENTS.md")
        return False
    ok = True
    for snippet in CODE_COMMENT_POLICY_REQUIRED_SNIPPETS:
        if snippet not in body:
            errors.append(f"{file}: Code Comment Policy missing required rule `{snippet}`")
            ok = False
    config = load_global_rule_overrides(project, profile)
    config_path = config["path"].relative_to(project).as_posix()
    if config_path in body:
        if not config["exists"]:
            errors.append(f"{file}: missing local code comment policy config `{config_path}`")
            ok = False
        for item in config["errors"]:
            if "code_comment_policy" in item:
                errors.append(f"{file}: invalid code comment policy config `{config_path}`: {item}")
                ok = False
    return ok


def is_path_reference(raw: str) -> bool:
    if raw.startswith(("http://", "https://", "mailto:")):
        return False
    if raw in {"AGENTS.md", "CLAUDE.md", "GEMINI.md"}:
        return False
    if any(char.isspace() for char in raw):
        return False
    if any(char in raw for char in "*?<>|,"):
        return False
    return True


def is_expected_contract_example_path(raw: str, profile: dict[str, Any]) -> bool:
    directory_contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract", {}), dict) else {}
    settings_policy = (
        directory_contract.get("workspace_settings_policy", {})
        if isinstance(directory_contract.get("workspace_settings_policy", {}), dict)
        else {}
    )
    settings_folder = str(settings_policy.get("folder", ".settings")).strip() or ".settings"
    local_default = str(settings_policy.get("local_default_file", f"{settings_folder}/project.local.json")).strip()
    remote_default = str(settings_policy.get("remote_default_file", f"{settings_folder}/project.remote.json")).strip()
    allowed_examples = {
        local_default or f"{settings_folder}/project.local.json",
        remote_default or f"{settings_folder}/project.remote.json",
        f"{settings_folder}/server_list.local.json",
        ".local.json",
        ".remote.json",
    }
    return raw in allowed_examples


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def make_targets(root: Path) -> set[str]:
    path = root / "Makefile"
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="ignore")
    return set(re.findall(r"^([A-Za-z0-9_.-]+):", text, flags=re.MULTILINE))


def package_scripts(root: Path) -> set[str]:
    package = read_json(root / "package.json")
    scripts = package.get("scripts", {}) if isinstance(package.get("scripts"), dict) else {}
    return set(scripts)


def composer_scripts(root: Path) -> set[str]:
    composer = read_json(root / "composer.json")
    scripts = composer.get("scripts", {}) if isinstance(composer.get("scripts"), dict) else {}
    return set(scripts)


def config_backed_command_error(command: str, project: Path) -> str | None:
    tokens = command.split()
    if not tokens:
        return None
    if tokens[0] == "make" and len(tokens) >= 2:
        if tokens[1] not in make_targets(project):
            return f"documented command `{command}` references missing Makefile target `{tokens[1]}`"
    if tokens[0] in {"npm", "pnpm", "yarn", "bun"}:
        scripts = package_scripts(project)
        if not scripts:
            return None
        if tokens[0] in {"pnpm", "yarn"} and len(tokens) >= 2 and tokens[1] in {"dlx", "exec", "install", "add", "remove"}:
            return None
        if tokens[0] == "bun" and len(tokens) >= 2 and tokens[1] in {"x", "install", "add", "remove"}:
            return None
        if tokens[0] == "npm" and len(tokens) >= 3 and tokens[1] == "run":
            script = tokens[2]
        elif tokens[0] == "npm" and len(tokens) >= 2 and tokens[1] == "test":
            script = "test"
        elif tokens[0] == "bun" and len(tokens) >= 3 and tokens[1] == "run":
            script = tokens[2]
        elif len(tokens) >= 2:
            script = tokens[1]
        else:
            return None
        if script not in scripts:
            return f"documented command `{command}` references missing package.json script `{script}`"
    if tokens[0] == "composer" and len(tokens) >= 3 and tokens[1] == "run":
        scripts = composer_scripts(project)
        if scripts and tokens[2] not in scripts:
            return f"documented command `{command}` references missing composer.json script `{tokens[2]}`"
    return None


def documented_script_path_error(command: str, project: Path) -> str | None:
    tokens = command.split()
    if len(tokens) < 2 or tokens[0] != "python":
        return None
    if tokens[1].startswith("<codex-home>/"):
        return None
    candidate = project / tokens[1]
    if tokens[1].endswith(".py") and not candidate.exists():
        return f"documented command `{command}` references missing script `{tokens[1]}`"
    return None


def validate_governance_runtime_commands(
    text: str,
    file: str,
    project: Path,
    installed_skill_dir_override: str | Path | None,
    errors: list[str],
) -> None:
    owner_status = evolution_owner_status(project, override_dir=installed_skill_dir_override)
    if owner_status.get("enabled"):
        return
    for match in PROJECT_LOCAL_GOVERNANCE_RUNTIME_RE.finditer(text):
        errors.append(
            f"{file}: project-local governance runtime command is forbidden for non-owner repositories; use installed agents-md-generator runtime instead ({match.group(0)})"
        )


def validate_decomposition_plan(project: Path, relative_path: str, profile: dict | None = None) -> list[str]:
    plan_path = decomposition_plan_path(project, relative_path, profile)
    if not plan_path.is_file():
        return [f"oversized source file `{relative_path}` requires decomposition plan `{plan_path.relative_to(project).as_posix()}`"]
    text = plan_path.read_text(encoding="utf-8", errors="ignore")
    required_sections = load_global_rule_overrides(project, profile)["data"]["source_file_limits"].get("required_plan_sections", [])
    missing = [section for section in required_sections if f"## {section}" not in text]
    if missing:
        return [f"{plan_path.relative_to(project).as_posix()}: missing decomposition plan sections {missing}"]
    return []


def should_skip(path: Path, project: Path, include_skipped: bool = False) -> bool:
    if include_skipped:
        return False
    try:
        parts = path.relative_to(project).parts
    except ValueError:
        parts = path.parts
    return bool(set(parts) & SKIP_DIRS)


def verify(project: Path, include_skipped: bool = False, installed_skill_dir_override: str | Path | None = None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []
    profile = project_profile(project)
    facts = inspect_project(project)
    installed_version = read_installed_skill_version(override_dir=installed_skill_dir_override)
    root_repair_command = root_agents_sync_command(project, profile, installed_skill_dir_override)
    for agents in sorted(project.rglob("AGENTS.md")):
        if should_skip(agents, project, include_skipped):
            continue
        checked.append(str(agents.relative_to(project).as_posix()))
        text = agents.read_text(encoding="utf-8", errors="ignore")
        if agents == project / "AGENTS.md":
            root_metadata_repair_required = False
            size = len(text.encode("utf-8"))
            if size > ROOT_AGENTS_MAX_BYTES:
                errors.append(f"{checked[-1]}: exceeds 16KB limit ({size} bytes)")
            managed_root = "Managed by agent:" in text or (project / ".agents" / "agents-control.json").exists()
            if managed_root:
                metadata = parse_agents_metadata(text)
                if not metadata.get("agents_version") or not metadata.get("generator_version"):
                    errors.append("AGENTS.md: missing AGENTS metadata version")
                    root_metadata_repair_required = True
                if not metadata.get("agents_version"):
                    errors.append("AGENTS.md: missing agents version metadata")
                    root_metadata_repair_required = True
                if not metadata.get("generator_version"):
                    errors.append("AGENTS.md: missing generator version metadata")
                    root_metadata_repair_required = True
                if installed_version:
                    if metadata.get("agents_version") and metadata.get("agents_version") != installed_version:
                        errors.append(
                            f"AGENTS.md: agents version {metadata.get('agents_version')} does not match installed agents-md-generator version {installed_version}"
                        )
                        root_metadata_repair_required = True
                    if metadata.get("generator_version") and metadata.get("generator_version") != installed_version:
                        errors.append(
                            f"AGENTS.md: generator version {metadata.get('generator_version')} does not match installed agents-md-generator version {installed_version}"
                        )
                        root_metadata_repair_required = True
                else:
                    errors.append("AGENTS.md: installed agents-md-generator version is unavailable")
                if not metadata.get("default_language"):
                    errors.append("AGENTS.md: missing default language metadata")
                    root_metadata_repair_required = True
                elif not LANGUAGE_LOCK_RE.search(text):
                    errors.append("AGENTS.md: missing enforced default-language reply rule")
                    root_metadata_repair_required = True
                elif not PLAN_LANGUAGE_LOCK_RE.search(text):
                    errors.append("AGENTS.md: missing enforced Plan Mode default-language rule")
                    root_metadata_repair_required = True
                if not validate_code_comment_policy(text, checked[-1], project, profile, errors):
                    root_metadata_repair_required = True
                if root_metadata_repair_required:
                    errors.append(f"AGENTS.md: run `{root_repair_command}` to refresh root metadata before continuing")
        validate_governance_runtime_commands(text, checked[-1], project, installed_skill_dir_override, errors)
        validate_markers(text, checked[-1], errors)
        validate_strong_control(text, checked[-1], project, errors)
        if "{{" in text or "}}" in text:
            errors.append(f"{checked[-1]}: unresolved template placeholder")
        if "Precedence" not in text and agents == project / "AGENTS.md":
            errors.append("AGENTS.md: missing precedence statement")

        for match in PATH_RE.finditer(text):
            raw = match.group(1).strip()
            if not is_path_reference(raw):
                continue
            candidate = (agents.parent / raw).resolve()
            root_candidate = (project / raw).resolve()
            if (
                not candidate.exists()
                and not root_candidate.exists()
                and not raw.endswith("/")
                and not is_expected_contract_example_path(raw, profile)
            ):
                warnings.append(f"{checked[-1]}: referenced path may not exist: {raw}")

        for match in COMMAND_RE.finditer(text):
            command = match.group(1).strip()
            if not command or "/" in command or command.endswith((".md", ".json", ".toml", ".yml", ".yaml")):
                continue
            config_error = config_backed_command_error(command, project)
            if config_error:
                errors.append(f"{checked[-1]}: {config_error}")
            script_error = documented_script_path_error(command, project)
            if script_error:
                errors.append(f"{checked[-1]}: {script_error}")
            if command.startswith(("make ", "npm ", "pnpm ", "yarn ", "bun ", "python ", "pytest", "go ", "composer ", "ruff ", "mypy ", "npx ")):
                continue
    source_governance = source_governance_report(project, profile)
    errors.extend(format_source_governance_errors(source_governance))
    errors.extend(str(item) for item in facts.get("tool_script_layout_violations", []) or [])
    errors.extend(str(item) for item in facts.get("script_triad_gaps", []) or [])
    global_status = global_codex_agents_status(project_root=project, profile=profile)
    if (project / "skills" / "agents-md-generator" / "SKILL.md").is_file() and not global_status["baseline_ok"]:
        reason_text = ", ".join(global_status["repair_reasons"]) or "unknown global Codex AGENTS baseline issue"
        errors.append(
            f"global .codex/AGENTS.md is not healthy for agents-md-generator development ({reason_text}); run `{global_codex_agents_sync_command(project, profile)}`"
        )
    return {"checked_files": checked, "errors": errors, "warnings": warnings, "global_codex_agents_status": global_status}


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify AGENTS.md generated content.")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--include-skipped", action="store_true", help="Also scan skipped directories such as ref, vendor, and build outputs.")
    parser.add_argument("--installed-skill-dir", default=None)
    args = parser.parse_args()
    emit_json(verify(resolve_project(args.project), args.include_skipped, args.installed_skill_dir))


if __name__ == "__main__":
    main()
