
from __future__ import annotations

import json
import re
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from agents_common import (
    SKIP_DIRS,
    codex_sessions_root,
    display_path,
    global_codex_agents_status,
    managed_scripts_root,
    normalize_path_key,
    package_manager,
    parse_agents_metadata,
    pm_dlx,
    pm_run,
    project_profile,
    read_installed_skill_version,
    read_json,
    read_skill_version,
    rel,
    root_agents_sync_command,
    workspace_has_existing_content,
)
from source_governance import source_governance_report
import source_governance_config
from source_governance_config import (
    default_global_rule_overrides,
    default_implementation_constraints,
    global_rule_overrides_path,
    global_rule_overrides_reference,
    implementation_constraints_from_profile,
    load_global_rule_overrides,
    validate_code_comment_policy_data,
    validate_global_rule_overrides_data,
)
from workspace_settings_policy import discover_workspace_settings

EPHEMERAL_ROOT_INPUT_FILE_RE = re.compile(
    r"^(?:answers|first-answers|recovery|session|stage|handoff|change|allowed-change|blocked-change|blocked-remote-change|blocked-remote-source-change)(?:-[a-z0-9._-]+)?\.json$",
    flags=re.IGNORECASE,
)
ALLOWED_ROOT_FILE_PATTERNS = (
    "answers.json",
    "*-answers.json",
    "change.json",
    "*-change.json",
    "session.json",
    "recovery.json",
    "handoff.json",
    "stage.json",
    "changelog.json",
    "experience-payload.json",
)

def parse_session_meta(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for raw in handle:
                data = json.loads(raw)
                if data.get("type") != "session_meta":
                    continue
                payload = data.get("payload", {})
                if isinstance(payload, dict):
                    return payload
    except Exception:
        return {}
    return {}

def matched_codex_sessions(root: Path) -> list[dict[str, str]]:
    sessions_root = codex_sessions_root()
    if not sessions_root.is_dir():
        return []
    key = normalize_path_key(root)
    matches: list[dict[str, str]] = []
    for path in sorted(sessions_root.rglob("*.jsonl")):
        payload = parse_session_meta(path)
        if not payload:
            continue
        cwd_key = normalize_path_key(payload.get("cwd", ""))
        if not cwd_key or cwd_key != key:
            continue
        matches.append(
            {
                "id": str(payload.get("id", "")).strip(),
                "cwd": str(payload.get("cwd", "")).strip(),
                "timestamp": str(payload.get("timestamp", "")).strip(),
                "path": path.resolve().as_posix(),
            }
        )
    return matches


def session_message_rows(path: Path, limit: int = 48) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for raw in handle:
                try:
                    data = json.loads(raw)
                except Exception:
                    continue
                if data.get("type") != "event_msg":
                    continue
                payload = data.get("payload", {})
                if not isinstance(payload, dict):
                    continue
                message_type = str(payload.get("type", "")).strip()
                role = "user" if message_type == "user_message" else "assistant" if message_type == "agent_message" else ""
                message = str(payload.get("message", "")).strip()
                if not role or not message:
                    continue
                rows.append({"role": role, "message": message})
                if len(rows) >= limit:
                    break
    except Exception:
        return []
    return rows

def list_files(root: Path, max_depth: int = 3) -> list[str]:
    out: list[str] = []
    for path in root.rglob("*"):
        parts = set(path.relative_to(root).parts)
        if parts & SKIP_DIRS:
            continue
        if len(path.relative_to(root).parts) > max_depth:
            continue
        if path.is_file():
            out.append(rel(path, root))
    return sorted(out)

def list_dirs(root: Path, max_depth: int = 2) -> list[str]:
    out: list[str] = []
    for path in root.rglob("*"):
        if not path.is_dir():
            continue
        relative = path.relative_to(root)
        if set(relative.parts) & SKIP_DIRS:
            continue
        if len(relative.parts) <= max_depth:
            out.append(relative.as_posix())
    return sorted(out)

def has_any(root: Path, names: list[str]) -> bool:
    return any((root / name).exists() for name in names)


def existing_paths(root: Path, names: list[str]) -> list[str]:
    return [name for name in names if (root / name).exists()]


def is_allowed_root_file(name: str, allowed_root_files: set[str]) -> bool:
    normalized = str(name).strip()
    if normalized in allowed_root_files:
        return True
    if EPHEMERAL_ROOT_INPUT_FILE_RE.fullmatch(normalized):
        return True
    return any(fnmatch(normalized, pattern) for pattern in ALLOWED_ROOT_FILE_PATTERNS)

def inspect_project(root: Path) -> dict[str, Any]:
    config_files = [name for name in [
        "package.json",
        "pnpm-lock.yaml",
        "package-lock.json",
        "yarn.lock",
        "bun.lock",
        "bun.lockb",
        "pyproject.toml",
        "uv.lock",
        "poetry.lock",
        "composer.json",
        "go.mod",
        "Makefile",
        "justfile",
    ] if (root / name).exists()]
    config_files.extend(discover_workspace_settings(root))

    languages: list[str] = []
    framework = "none"
    project_type = "unknown"

    package_json = read_json(root / "package.json")
    if package_json:
        languages.append("typescript")
        deps = {}
        for key in ("dependencies", "devDependencies"):
            value = package_json.get(key, {})
            if isinstance(value, dict):
                deps.update(value)
        if "next" in deps:
            framework = "next.js"
            project_type = "typescript-nextjs"
        elif "react" in deps:
            framework = "react"
            project_type = "typescript-react"
        elif "vue" in deps:
            framework = "vue"
            project_type = "typescript-vue"
        elif "express" in deps:
            framework = "express"
            project_type = "typescript-node"
        else:
            project_type = "typescript"

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        languages.append("python")
        text = pyproject.read_text(encoding="utf-8", errors="ignore").lower()
        if "django" in text:
            framework = "django"
        elif "fastapi" in text:
            framework = "fastapi"
        elif "flask" in text:
            framework = "flask"
        project_type = "python"

    composer = read_json(root / "composer.json")
    if composer:
        languages.append("php")
        require = composer.get("require", {}) if isinstance(composer.get("require"), dict) else {}
        composer_type = composer.get("type", "")
        if (root / "ext_emconf.php").exists() or "typo3/cms-core" in require:
            framework = "typo3"
            project_type = "php-typo3-extension" if composer_type == "typo3-cms-extension" else "php-typo3"
        elif "laravel/framework" in require:
            framework = "laravel"
            project_type = "php-laravel"
        elif "symfony/framework-bundle" in require:
            framework = "symfony"
            project_type = "php-symfony"
        else:
            project_type = "php"

    if (root / "go.mod").exists():
        languages.append("go")
        project_type = "go-cli" if (root / "cmd").exists() else "go"
        framework = "go"

    skill_files = sorted(path for path in root.glob("*/SKILL.md") if path.is_file())
    skill_files.extend(sorted(path for path in root.glob("skills/*/SKILL.md") if path.is_file()))
    if (root / "SKILL.md").exists() or skill_files:
        if "skill" not in languages:
            languages.append("skill")
        project_type = "skill-repo"
        if framework == "none":
            framework = "codex-skill"

    ci: list[str] = []
    if (root / ".github" / "workflows").exists():
        ci.append("github_actions")
    if (root / ".gitlab-ci.yml").exists():
        ci.append("gitlab_ci")

    ai_configs = [name for name in [
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
        ".cursor",
        ".claude",
        ".windsurf",
    ] if (root / name).exists()]

    root_agents_path = root / "AGENTS.md"
    root_agents_text = root_agents_path.read_text(encoding="utf-8", errors="ignore") if root_agents_path.is_file() else ""
    agents_metadata = parse_agents_metadata(root_agents_text)
    profile = read_json(root / ".agents" / "agents-control.json")
    installed_version = read_installed_skill_version()
    runtime_version = read_skill_version()
    trigger_reasons: list[str] = []
    if not root_agents_path.is_file():
        trigger_reasons.append("missing_root_agents_md")
    else:
        agents_version = agents_metadata.get("agents_version", "")
        generator_version = agents_metadata.get("generator_version", "")
        if not agents_version:
            trigger_reasons.append("missing_agents_version")
        if not generator_version:
            trigger_reasons.append("missing_generator_version")
        if not installed_version:
            trigger_reasons.append("installed_skill_version_unavailable")
        else:
            if agents_version and agents_version != installed_version:
                trigger_reasons.append("agents_version_mismatch")
            if generator_version and generator_version != installed_version:
                trigger_reasons.append("generator_version_mismatch")

    repair_reasons = {
        "missing_agents_version",
        "missing_generator_version",
        "agents_version_mismatch",
        "generator_version_mismatch",
    }
    repair_command = root_agents_sync_command(root, profile) if any(reason in repair_reasons for reason in trigger_reasons) else ""

    matched_sessions = matched_codex_sessions(root)
    session_bootstrap_required = (not root_agents_path.is_file()) and workspace_has_existing_content(root)
    global_codex = global_codex_agents_status(project_root=root, profile=profile)

    structure_fix_confirmation_required = False
    structure_fix_reasons: list[str] = []
    if isinstance(profile, dict):
        contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract"), dict) else {}
        primary_root = str(contract.get("primary_project_root", "")).strip().strip("/")
        allowed_root_files = {
            str(item).strip()
            for item in contract.get("allowed_root_files", ["AGENTS.md", "CLAUDE.md", "GEMINI.md", ".gitignore", ".gitattributes", ".editorconfig"])
            if str(item).strip()
        }
        if primary_root and not (root / primary_root).exists():
            structure_fix_confirmation_required = True
            structure_fix_reasons.append(f"missing primary project root `{primary_root}/`")
        allowed_roots = {
            str(item).strip().strip("/").split("/", 1)[0]
            for item in contract.get("allowed_new_paths", [])
            if str(item).strip()
        }
        if allowed_roots:
            for child in root.iterdir():
                if child.is_file():
                    if not is_allowed_root_file(child.name, allowed_root_files):
                        structure_fix_confirmation_required = True
                        structure_fix_reasons.append(f"root-level file requires review: `{child.name}`")
                    continue
                if child.name in SKIP_DIRS or child.name in {".agents", "AGENTS.md"}:
                    continue
                if child.name not in allowed_roots:
                    structure_fix_confirmation_required = True
                    structure_fix_reasons.append(f"top-level path requires review: `{child.name}`")
        for legacy in [root / "HANDOFF.md", root / "DEVELOPMENT.md", root / "experience", root / "docs" / "HANDOFF.md", root / "docs" / "DEVELOPMENT.md"]:
            if legacy.exists():
                structure_fix_confirmation_required = True
                structure_fix_reasons.append(f"legacy docs path requires migration: `{display_path(legacy, root)}`")

    constraints = implementation_constraints_from_profile(profile, root)
    source_governance = source_governance_report(root, profile)
    script_layout = script_layout_facts(root, profile)
    overrides = load_global_rule_overrides(root, profile)

    return {
        "project_root": str(root),
        "root_agents_md_exists": root_agents_path.is_file(),
        "root_agents_md_metadata": agents_metadata,
        "root_agents_md_version": agents_metadata.get("agents_version", ""),
        "root_agents_md_generator_version": agents_metadata.get("generator_version", ""),
        "root_agents_md_default_language": agents_metadata.get("default_language", ""),
        "current_skill_version": runtime_version,
        "installed_skill_version": installed_version,
        "root_agents_md_trigger_required": bool(trigger_reasons),
        "root_agents_md_trigger_reasons": trigger_reasons,
        "root_agents_md_rebuild_required": bool(trigger_reasons),
        "root_agents_md_rebuild_reasons": trigger_reasons,
        "root_agents_md_repair_command": repair_command,
        "global_codex_agents_exists": global_codex["exists"],
        "global_codex_agents_empty": global_codex["empty"],
        "global_codex_agents_managed": global_codex["managed"],
        "global_codex_agents_baseline_ok": global_codex["baseline_ok"],
        "global_codex_agents_repair_required": global_codex["repair_required"],
        "global_codex_agents_repair_reasons": global_codex["repair_reasons"],
        "global_codex_agents_repair_command": global_codex["repair_command"],
        "global_codex_agents_requires_user_confirmation": global_codex["requires_user_confirmation"],
        "session_history_bootstrap_required": session_bootstrap_required,
        "session_history_match_scope": "exact-cwd",
        "matched_session_count": len(matched_sessions),
        "matched_session_ids": [item["id"] for item in matched_sessions if item["id"]],
        "matched_session_paths": [item["path"] for item in matched_sessions],
        "structure_fix_confirmation_required": structure_fix_confirmation_required,
        "structure_fix_default": "yes",
        "structure_fix_reasons": structure_fix_reasons,
        "implementation_constraints": constraints,
        "global_rule_overrides_path": overrides["path"].relative_to(root).as_posix(),
        "global_rule_overrides_exists": overrides["exists"],
        "global_rule_overrides_valid": not overrides["errors"],
        "global_rule_overrides_errors": list(overrides["errors"]),
        "global_rule_overrides": overrides["data"],
        "source_governance": source_governance,
        "oversized_source_files": source_governance["oversized_source_files"],
        "test_code_boundary_violations": source_governance["test_code_boundary_violations"],
        "comment_policy_violations": source_governance["comment_policy_violations"],
        "tool_script_layout_violations": script_layout["tool_script_layout_violations"],
        "script_triad_gaps": script_layout["script_triad_gaps"],
        "gui_script_exemptions": script_layout["gui_script_exemptions"],
        "primary_language": languages[0] if languages else "unknown",
        "languages": sorted(set(languages)),
        "package_manager": package_manager(root),
        "framework": framework,
        "project_type": project_type,
        "ci": ci,
        "ai_configs": ai_configs,
        "config_files": config_files,
        "directories": list_dirs(root),
        "files": list_files(root),
    }

def command_entry(task: str, command: str, source: str, notes: str = "", seconds: str = "") -> dict[str, str]:
    return {
        "task": task,
        "command": command,
        "source": source,
        "notes": notes,
        "time": seconds or "~30s",
        "verified": "false",
    }

def extract_commands(root: Path) -> dict[str, Any]:
    commands: list[dict[str, str]] = []

    makefile = root / "Makefile"
    if makefile.exists():
        text = makefile.read_text(encoding="utf-8", errors="ignore")
        targets = set(re.findall(r"^([A-Za-z0-9_.-]+):", text, flags=re.MULTILINE))
        mapping = {
            "Setup": ["setup", "install"],
            "Run": ["dev", "serve", "run"],
            "Format": ["format", "fmt"],
            "Lint": ["lint", "check"],
            "Test (all)": ["test", "tests"],
            "Build": ["build"],
            "Typecheck": ["typecheck", "types"],
        }
        for task, candidates in mapping.items():
            for target in candidates:
                if target in targets:
                    commands.append(command_entry(task, f"make {target}", "Makefile"))
                    break

    package_json = read_json(root / "package.json")
    if package_json:
        scripts = package_json.get("scripts", {})
        scripts = scripts if isinstance(scripts, dict) else {}
        pm = package_manager(root)
        run = pm_run(pm)
        dlx = pm_dlx(pm)
        if scripts:
            commands.append(command_entry("Setup", f"{pm} install", "lockfile/package.json", "~install dependencies"))
        script_map = {
            "Run": ["dev", "start"],
            "Format": ["format", "fmt"],
            "Lint": ["lint"],
            "Test (all)": ["test"],
            "Build": ["build"],
            "Typecheck": ["typecheck", "type-check", "types"],
        }
        for task, names in script_map.items():
            for name in names:
                if name in scripts:
                    cmd = f"{pm} test" if task == "Test (all)" and pm in {"npm", "pnpm"} else f"{run} {name}"
                    commands.append(command_entry(task, cmd, "package.json"))
                    break
        deps_text = json.dumps(package_json)
        if "vitest" in deps_text:
            commands.append(command_entry("Test (single)", f"{dlx} vitest run", "package.json", "~single test file", "~2s"))
        elif "jest" in deps_text:
            commands.append(command_entry("Test (single)", f"{dlx} jest", "package.json", "~single test file", "~2s"))

    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8", errors="ignore")
        if "[tool.ruff" in text:
            commands.append(command_entry("Lint", "ruff check .", "pyproject.toml", "", "~10s"))
            commands.append(command_entry("Format", "ruff format .", "pyproject.toml", "", "~5s"))
        if "mypy" in text:
            commands.append(command_entry("Typecheck", "mypy .", "pyproject.toml", "", "~15s"))
        if "pytest" in text or (root / "tests").exists():
            commands.append(command_entry("Test (all)", "pytest", "pyproject.toml/tests", "", "~30s"))

    composer = read_json(root / "composer.json")
    if composer:
        scripts = composer.get("scripts", {}) if isinstance(composer.get("scripts"), dict) else {}
        for task, names in {
            "Lint": ["lint", "cs:check"],
            "Format": ["format", "cs:fix"],
            "Test (all)": ["test"],
            "Typecheck": ["phpstan", "stan"],
        }.items():
            for name in names:
                if name in scripts:
                    commands.append(command_entry(task, f"composer run {name}", "composer.json"))
                    break

    if (root / "go.mod").exists():
        commands.extend([
            command_entry("Format", "gofmt -w .", "go.mod", "", "~5s"),
            command_entry("Test (all)", "go test ./...", "go.mod", "", "~30s"),
            command_entry("Build", "go build ./...", "go.mod", "", "~30s"),
        ])

    workflow_dir = root / ".github" / "workflows"
    if workflow_dir.exists():
        for workflow in sorted(workflow_dir.glob("*.y*ml")):
            text = workflow.read_text(encoding="utf-8", errors="ignore")
            for raw in re.findall(r"^\s*-\s*run:\s*(.+)$|^\s*run:\s*(.+)$", text, flags=re.MULTILINE):
                command = (raw[0] or raw[1]).strip().strip("'\"")
                if not command or command.startswith(("|", ">")):
                    continue
                first_line = command.splitlines()[0].strip()
                if not first_line:
                    continue
                lowered = first_line.lower()
                if any(token in lowered for token in ("lint", "eslint", "ruff", "phpstan")):
                    task = "CI Lint"
                elif any(token in lowered for token in ("test", "pytest", "vitest", "jest", "go test")):
                    task = "CI Test"
                elif any(token in lowered for token in ("build", "compile")):
                    task = "CI Build"
                elif any(token in lowered for token in ("typecheck", "type-check", "tsc", "mypy")):
                    task = "CI Typecheck"
                else:
                    task = "CI Command"
                commands.append(command_entry(task, first_line, rel(workflow, root)))

    seen: set[tuple[str, str]] = set()
    unique = []
    for item in commands:
        key = (item["task"], item["command"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return {"commands": unique}

def workflow_runs(root: Path) -> list[dict[str, str]]:
    rules: list[dict[str, str]] = []
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.exists():
        return rules
    for workflow in sorted(workflow_dir.glob("*.y*ml")):
        text = workflow.read_text(encoding="utf-8", errors="ignore")
        for raw in re.findall(r"^\s*-\s*run:\s*(.+)$|^\s*run:\s*(.+)$", text, flags=re.MULTILINE):
            command = (raw[0] or raw[1]).strip().strip("'\"")
            if not command or command.startswith(("|", ">")):
                continue
            first_line = command.splitlines()[0].strip()
            if first_line:
                rules.append({"workflow": rel(workflow, root), "command": first_line})
    return rules

def default_global_rule_overrides() -> dict[str, Any]:
    return source_governance_config.default_global_rule_overrides()


def default_implementation_constraints() -> dict[str, Any]:
    return source_governance_config.default_implementation_constraints()


def global_rule_overrides_reference(profile: dict[str, Any] | None) -> str:
    return source_governance_config.global_rule_overrides_reference(profile)


def global_rule_overrides_path(root: Path, profile: dict[str, Any] | None = None) -> Path:
    return source_governance_config.global_rule_overrides_path(root, profile)


def validate_code_comment_policy_data(comment_policy: dict[str, Any], *, require_explicit: bool = False) -> list[str]:
    return source_governance_config.validate_code_comment_policy_data(comment_policy, require_explicit=require_explicit)


def validate_global_rule_overrides_data(data: dict[str, Any]) -> list[str]:
    return source_governance_config.validate_global_rule_overrides_data(data)


def load_global_rule_overrides(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    return source_governance_config.load_global_rule_overrides(root, profile)


def ensure_global_rule_overrides_file(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    return source_governance_config.ensure_global_rule_overrides_file(root, profile)


def implementation_constraints_from_profile(profile: dict[str, Any] | None, root: Path | None = None) -> dict[str, Any]:
    return source_governance_config.implementation_constraints_from_profile(profile, root)

def iter_handwritten_code_files(root: Path, constraints: dict[str, Any]) -> list[Path]:
    allowed_exts = {str(item).lower() for item in constraints.get("line_limit_extensions", [])}
    excluded_roots = {str(item).strip("/\\") for item in constraints.get("line_limit_exclude_roots", [])}
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if rel_parts and rel_parts[0] in excluded_roots:
            continue
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if path.suffix.lower() in allowed_exts:
            files.append(path)
    return sorted(files)

def file_line_count(path: Path) -> int:
    try:
        return path.read_text(encoding="utf-8").count("\n") + 1
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore").count("\n") + 1

def script_governance_exceptions(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    overrides = load_global_rule_overrides(root, profile)["data"]
    path = root / str(overrides["tool_script_layout"].get("gui_exception_manifest", ".agents/script-governance-exceptions.json")).strip()
    data = read_json(path) if path.exists() else {}
    gui_startup = data.get("gui_startup", []) if isinstance(data.get("gui_startup", []), list) else []
    normalized = sorted(str(item).strip().replace("\\", "/") for item in gui_startup if str(item).strip())
    return {"path": rel(path, root) if path.exists() else path.relative_to(root).as_posix(), "gui_startup": normalized}

def decomposition_plan_path(root: Path, relative_file: str, profile: dict[str, Any] | None = None) -> Path:
    overrides = load_global_rule_overrides(root, profile)["data"]
    plan_root = str(overrides["source_file_limits"].get("decomposition_plan_root", "docs/development/decomposition-plans")).strip().strip("/\\")
    sanitized = relative_file.replace("\\", "/").replace(":", "")
    return root / plan_root / f"{sanitized}.md"

def managed_script_roots(root: Path, profile: dict[str, Any] | None = None) -> list[Path]:
    candidates = []
    if (root / "scripts").is_dir():
        candidates.append(root / "scripts")
    unique: list[Path] = []
    seen: set[str] = set()
    for item in candidates:
        key = normalize_path_key(item)
        if item.is_dir() and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique

def script_layout_facts(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    constraints = implementation_constraints_from_profile(profile, root)
    layout = constraints.get("script_layout", {}) if isinstance(constraints.get("script_layout", {}), dict) else {}
    families = layout.get("families", {}) if isinstance(layout.get("families", {}), dict) else {}
    required_root = str(layout.get("required_root", "scripts")).strip("/\\") or "scripts"
    exceptions = script_governance_exceptions(root, profile)
    gui_set = set(exceptions["gui_startup"])
    roots = managed_script_roots(root, profile)
    triad_members: dict[tuple[str, str], set[str]] = {}
    layout_violations: list[str] = []
    allowed_families = list(families)
    extension_to_family = {str(extension).lower(): family for family, extension in families.items()}
    for scripts_root in roots:
        if scripts_root.name != required_root and scripts_root.relative_to(root).as_posix().endswith(f"/{required_root}") is False:
            continue
        for path in sorted(scripts_root.rglob("*")):
            if not path.is_file():
                continue
            rel_path = path.relative_to(root).as_posix()
            if rel_path in gui_set:
                continue
            relative = path.relative_to(scripts_root)
            parts = relative.parts
            if not parts:
                continue
            family = parts[0]
            suffix = path.suffix.lower()
            if family not in families:
                expected_family = extension_to_family.get(suffix, "")
                if len(parts) == 1 and expected_family:
                    layout_violations.append(
                        f"script layout requires {required_root}/{expected_family}/<function>/<name>{suffix}: {rel_path}"
                    )
                elif expected_family:
                    layout_violations.append(
                        f"unsupported script family under {required_root} (allowed: {', '.join(allowed_families)}): {rel_path}"
                    )
                continue
            expected_extension = str(families[family]).lower()
            if suffix != expected_extension:
                layout_violations.append(
                    f"script extension {suffix or '<none>'} does not match family `{family}` (expected {expected_extension}): {rel_path}"
                )
                continue
            if len(parts) < 3:
                layout_violations.append(
                    f"script layout requires {required_root}/{family}/<function>/<name>{expected_extension}: {rel_path}"
                )
                continue
            function_path = "/".join(parts[1:-1])
            stem = path.stem
            triad_members.setdefault((function_path, stem), set()).add(family)
    triad_gaps: list[str] = []
    if layout.get("require_full_triad", True):
        required_families = set(families)
        for (function_path, stem), present in sorted(triad_members.items()):
            if present != required_families:
                missing = sorted(required_families - present)
                if missing:
                    triad_gaps.append(f"missing script family variants for {required_root}/<family>/{function_path}/{stem}: {missing}")
    return {
        "gui_script_exemptions": exceptions["gui_startup"],
        "tool_script_layout_violations": layout_violations,
        "script_triad_gaps": triad_gaps,
    }

def extract_context(root: Path) -> dict[str, Any]:
    profile = project_profile(root)
    documentation_names = {"README.md", "CONTRIBUTING.md", "SECURITY.md", "ARCHITECTURE.md"}
    documentation = [name for name in sorted(documentation_names) if (root / name).exists()]
    for docs_dir in ("docs", "Documentation"):
        base = root / docs_dir
        if base.exists():
            documentation.extend(rel(path, root) for path in sorted(base.glob("*.md"))[:12])

    adr_dirs = ["adr", "adrs", "docs/adr", "docs/adrs", "docs/decisions", "architecture/decisions"]
    adrs: list[str] = []
    for adr_dir in adr_dirs:
        base = root / adr_dir
        if base.exists():
            adrs.extend(rel(path, root) for path in sorted(base.glob("*.md"))[:12])

    utilities: list[str] = []
    for name in ("Makefile", "justfile"):
        if (root / name).exists():
            utilities.append(name)
    scripts_dir = root / "scripts"
    if scripts_dir.exists():
        utilities.extend(rel(path, root) for path in sorted(scripts_dir.iterdir()) if path.is_file())

    quality_names = [
        ".pre-commit-config.yaml",
        ".pre-commit-config.yml",
        "ruff.toml",
        ".ruff.toml",
        "mypy.ini",
        "pytest.ini",
        "tsconfig.json",
        "eslint.config.js",
        "eslint.config.mjs",
        ".eslintrc",
        ".eslintrc.json",
        ".prettierrc",
        ".prettierrc.json",
        "phpstan.neon",
    ]
    quality_configs = existing_paths(root, quality_names)

    platform_names = [
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
        ".devcontainer/devcontainer.json",
        ".tool-versions",
        ".python-version",
        ".nvmrc",
        "mise.toml",
        ".mise.toml",
        "flake.nix",
        "shell.nix",
        "Taskfile.yml",
        "Taskfile.yaml",
    ]
    platform_files = existing_paths(root, platform_names)

    ide_names = [
        ".editorconfig",
        ".vscode/settings.json",
        ".vscode/extensions.json",
        ".idea/codeStyles/Project.xml",
        ".idea/inspectionProfiles/Project_Default.xml",
    ]
    ide_settings = existing_paths(root, ide_names)
    workspace_settings = discover_workspace_settings(root)

    architecture_names = [
        "CODEOWNERS",
        ".github/CODEOWNERS",
        "ARCHITECTURE.md",
        "docs/architecture.md",
        "docs/ARCHITECTURE.md",
        "docs/adr/index.md",
    ]
    architecture_files = existing_paths(root, architecture_names)

    dependency_names = [
        ".github/dependabot.yml",
        ".github/dependabot.yaml",
        "renovate.json",
        ".renovaterc",
        ".renovaterc.json",
        "dependabot.yml",
        "dependabot.yaml",
    ]
    dependency_configs = existing_paths(root, dependency_names)

    hook_names = [
        "lefthook.yml",
        ".lefthook.yml",
        "captainhook.json",
        ".pre-commit-config.yaml",
        ".pre-commit-config.yml",
        "Build/hooks/pre-push",
        ".githooks/pre-commit",
        ".githooks/pre-push",
    ]
    hook_configs = existing_paths(root, hook_names)
    if (root / ".husky").is_dir():
        hook_configs.append(".husky/")

    github_names = [
        ".github/CODEOWNERS",
        ".github/copilot-instructions.md",
        ".github/dependabot.yml",
        ".github/dependabot.yaml",
        ".github/renovate.json",
    ]
    github_settings = existing_paths(root, github_names)
    rulesets_dir = root / ".github" / "rulesets"
    if rulesets_dir.exists():
        github_settings.extend(rel(path, root) for path in sorted(rulesets_dir.glob("*.json"))[:12])

    coverage_names = [
        "src",
        "app",
        "lib",
        "tests",
        "test",
        "docs",
        "Documentation",
        "scripts",
        "tools",
        "cmd",
        "internal",
        "pkg",
        ".github/workflows",
    ]
    directory_coverage_candidates = [
        name for name in coverage_names
        if (root / name).is_dir() and not (root / name / "AGENTS.md").exists()
    ]

    reference_projects: list[str] = []
    for base_name in ("reference-projects", "references/projects", "examples/reference-projects"):
        base = root / base_name
        if base.exists() and base.is_dir():
            for child in sorted(base.iterdir()):
                if child.is_dir():
                    reference_projects.append(rel(child, root))

    agent_config_names = [
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".github/copilot-instructions.md",
        ".cursorrules",
        ".aider.conf.yml",
        ".aider.conf.yaml",
    ]
    agent_configs = [name for name in agent_config_names if (root / name).exists()]

    golden_samples: list[str] = []
    sample_patterns = [
        "tests/test_*.*",
        "tests/*_test.*",
        "src/*.*",
        "app/*.*",
        "lib/*.*",
        "examples/*.*",
        "samples/*.*",
    ]
    for pattern in sample_patterns:
        for path in sorted(root.glob(pattern)):
            if path.is_file() and len(golden_samples) < 8:
                golden_samples.append(rel(path, root))

    script_governance = script_layout_facts(root, profile)
    implementation_constraints = implementation_constraints_from_profile(profile, root)
    overrides = load_global_rule_overrides(root, profile)

    return {
        "documentation": sorted(dict.fromkeys(documentation)),
        "adrs": sorted(dict.fromkeys(adrs)),
        "utilities": sorted(dict.fromkeys(utilities)),
        "quality_configs": sorted(dict.fromkeys(quality_configs)),
        "platform_files": sorted(dict.fromkeys(platform_files)),
        "ide_settings": sorted(dict.fromkeys(ide_settings)),
        "workspace_settings": sorted(dict.fromkeys(workspace_settings)),
        "architecture_files": sorted(dict.fromkeys(architecture_files)),
        "dependency_configs": sorted(dict.fromkeys(dependency_configs)),
        "hook_configs": sorted(dict.fromkeys(hook_configs)),
        "github_settings": sorted(dict.fromkeys(github_settings)),
        "directory_coverage_candidates": sorted(dict.fromkeys(directory_coverage_candidates)),
        "reference_projects": sorted(dict.fromkeys(reference_projects)),
        "agent_configs": sorted(dict.fromkeys(agent_configs)),
        "golden_samples": sorted(dict.fromkeys(golden_samples)),
        "ci_rules": workflow_runs(root),
        "implementation_constraints": implementation_constraints,
        "global_rule_overrides_path": overrides["path"].relative_to(root).as_posix(),
        "global_rule_overrides_exists": overrides["exists"],
        "global_rule_overrides_valid": not overrides["errors"],
        "global_rule_overrides_errors": list(overrides["errors"]),
        "global_rule_overrides": overrides["data"],
        "gui_script_exemptions": script_governance["gui_script_exemptions"],
        "tool_script_layout_violations": script_governance["tool_script_layout_violations"],
        "script_triad_gaps": script_governance["script_triad_gaps"],
    }

def detect_scopes(root: Path) -> dict[str, Any]:
    candidates = {
        "src": "source code patterns",
        "tests": "test conventions and fixtures",
        "test": "test conventions and fixtures",
        "docs": "documentation standards",
        "frontend": "frontend stack and UI conventions",
        "web": "frontend stack and UI conventions",
        "backend": "backend stack and service conventions",
        "internal": "internal module boundaries",
        "cmd": "CLI entry points and flags",
        "scripts": "automation script conventions",
        ".github/workflows": "CI workflow rules",
    }
    scopes = []
    for path, purpose in candidates.items():
        full = root / path
        if full.exists() and full.is_dir():
            scopes.append({"path": path, "purpose": purpose, "agents_file": f"{path}/AGENTS.md"})

    packages = root / "packages"
    if packages.exists():
        for child in sorted(packages.iterdir()):
            if child.is_dir():
                path = child.relative_to(root).as_posix()
                scopes.append({"path": path, "purpose": "workspace package-specific rules", "agents_file": f"{path}/AGENTS.md"})
    return {"scopes": scopes}
