from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "ref",
}

AGENTS_METADATA_RE = re.compile(r"<!--\s*AGENTS-METADATA:\s*(.*?)\s*-->", flags=re.IGNORECASE)
AGENTS_METADATA_PAIR_RE = re.compile(r"([a-zA-Z0-9_]+)\s*=\s*([^;]+)")
RELEASE_CORE_WORKTREE_RULE = "Do not repoint repositories with `git config core.worktree`; use normal checkout/merge or explicit `git worktree` commands instead."
ROOT_AGENTS_SYNC_COMMAND = "python scripts/manage_docs.py sync-root-agents . --write"
GLOBAL_CODEX_AGENTS_SYNC_COMMAND = "python scripts/manage_docs.py sync-global-codex-agents . --write"
GLOBAL_CODEX_AGENTS_PREAMBLE = "<!-- Managed by agents-md-generator: keep manual notes outside the managed global baseline block. -->"
GLOBAL_CODEX_AGENTS_BLOCK_START = "<!-- AGENTS-GENERATED:START global-codex-baseline -->"
GLOBAL_CODEX_AGENTS_BLOCK_END = "<!-- AGENTS-GENERATED:END global-codex-baseline -->"

def resolve_project(raw: str | Path) -> Path:
    project = Path(raw).resolve()
    if not project.exists() or not project.is_dir():
        raise SystemExit(f"Project directory does not exist: {project}")
    return project


def emit_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def codex_home_root(raw: str | None = None) -> Path:
    env_home = raw.strip() if raw else os.environ.get("CODEX_HOME", "").strip()
    if env_home:
        return Path(env_home).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def codex_sessions_root() -> Path:
    return codex_home_root() / "sessions"


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def skill_version_file(root: Path | None = None) -> Path:
    return (root or skill_root()) / "VERSION"


def read_skill_version(root: Path | None = None) -> str:
    path = skill_version_file(root)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def installed_skill_dir(skill_name: str = "agents-md-generator") -> Path | None:
    override = os.environ.get("AGENTS_MD_INSTALLED_SKILL_DIR", "").strip()
    if override:
        path = Path(override).expanduser().resolve()
        return path if path.exists() else None
    codex_home = os.environ.get("CODEX_HOME", "").strip()
    home_root = Path(codex_home).expanduser().resolve() if codex_home else (Path.home() / ".codex").resolve()
    path = home_root / "skills" / skill_name
    return path if path.exists() else None


def read_installed_skill_version(skill_name: str = "agents-md-generator") -> str:
    installed = installed_skill_dir(skill_name)
    if installed is None:
        return ""
    return read_skill_version(installed)


def preferred_skill_version(skill_name: str = "agents-md-generator") -> tuple[str, str]:
    installed = read_installed_skill_version(skill_name)
    if installed:
        return installed, "installed"
    runtime = read_skill_version()
    if runtime:
        return runtime, "runtime"
    return "", "unavailable"


def global_codex_agents_path(codex_home: str | None = None) -> Path:
    return codex_home_root(codex_home) / "AGENTS.md"


def global_codex_agents_template_path(root: Path | None = None) -> Path:
    return (root or skill_root()) / "assets" / "templates" / "global-codex-agents.md"


def render_global_codex_agents_template(root: Path | None = None) -> str:
    path = global_codex_agents_template_path(root)
    if not path.is_file():
        raise SystemExit(f"Missing global Codex AGENTS template: {path}")
    return path.read_text(encoding="utf-8", errors="ignore").rstrip() + "\n"


def extract_global_codex_managed_block(text: str) -> str:
    start = text.find(GLOBAL_CODEX_AGENTS_BLOCK_START)
    end = text.find(GLOBAL_CODEX_AGENTS_BLOCK_END)
    if start == -1 or end == -1 or end < start:
        return ""
    end += len(GLOBAL_CODEX_AGENTS_BLOCK_END)
    return text[start:end]


def global_codex_agents_status(codex_home: str | None = None) -> dict[str, Any]:
    path = global_codex_agents_path(codex_home)
    text = path.read_text(encoding="utf-8", errors="ignore") if path.is_file() else ""
    exists = path.is_file()
    empty = exists and not text.strip()
    managed = GLOBAL_CODEX_AGENTS_BLOCK_START in text and GLOBAL_CODEX_AGENTS_BLOCK_END in text
    expected_block = extract_global_codex_managed_block(render_global_codex_agents_template())
    actual_block = extract_global_codex_managed_block(text) if managed else ""
    baseline_ok = managed and actual_block == expected_block
    repair_reasons: list[str] = []
    requires_user_confirmation = False
    user_message = ""
    if not exists:
        repair_reasons.append("missing_global_codex_agents_md")
    elif empty:
        repair_reasons.append("empty_global_codex_agents_md")
    elif not managed:
        repair_reasons.append("missing_global_codex_agents_managed_block")
        requires_user_confirmation = True
        user_message = (
            "Global .codex/AGENTS.md has manual content but no managed baseline block; "
            "insert the generated baseline block near the top of the file after any opening comments."
        )
    elif not baseline_ok:
        repair_reasons.append("outdated_global_codex_agents_baseline")
    repair_required = bool(repair_reasons)
    return {
        "path": str(path),
        "exists": exists,
        "empty": empty,
        "managed": managed,
        "baseline_ok": baseline_ok,
        "repair_required": repair_required,
        "repair_reasons": repair_reasons,
        "repair_command": GLOBAL_CODEX_AGENTS_SYNC_COMMAND,
        "recommended_action": GLOBAL_CODEX_AGENTS_SYNC_COMMAND,
        "requires_user_confirmation": requires_user_confirmation,
        "user_message": user_message,
    }


def parse_agents_metadata(text: str) -> dict[str, str]:
    match = AGENTS_METADATA_RE.search(text)
    if not match:
        return {}
    body = match.group(1)
    data: dict[str, str] = {}
    for key, value in AGENTS_METADATA_PAIR_RE.findall(body):
        data[key.strip()] = value.strip()
    return data


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def display_path(path: Path, root: Path | None = None) -> str:
    if root is not None:
        try:
            return path.resolve().relative_to(root.resolve()).as_posix()
        except Exception:
            pass
    return path.resolve().as_posix()


def normalize_path_key(raw: str | Path) -> str:
    value = str(raw).strip()
    if not value:
        return ""
    try:
        resolved = Path(value).expanduser().resolve()
    except Exception:
        resolved = Path(value).expanduser()
    return os.path.normcase(str(resolved))


def workspace_has_existing_content(root: Path) -> bool:
    ignored = set(SKIP_DIRS) | {".agents"}
    for path in root.iterdir():
        if path.name in ignored:
            continue
        if path.name == "AGENTS.md":
            continue
        return True
    return False


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


def package_manager(root: Path) -> str:
    package_json = read_json(root / "package.json")
    field = package_json.get("packageManager", "")
    if isinstance(field, str) and "@" in field:
        return field.split("@", 1)[0]
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lockb").exists() or (root / "bun.lock").exists():
        return "bun"
    if (root / "package-lock.json").exists() or (root / "package.json").exists():
        return "npm"
    if (root / "composer.json").exists():
        return "composer"
    if (root / "uv.lock").exists():
        return "uv"
    if (root / "poetry.lock").exists():
        return "poetry"
    if (root / "go.mod").exists():
        return "go"
    return "unknown"


def pm_run(pm: str) -> str:
    return {"pnpm": "pnpm", "yarn": "yarn", "bun": "bun run"}.get(pm, "npm run")


def pm_dlx(pm: str) -> str:
    return {"pnpm": "pnpm dlx", "yarn": "yarn dlx", "bun": "bunx"}.get(pm, "npx")


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
    repair_command = ROOT_AGENTS_SYNC_COMMAND if any(reason in repair_reasons for reason in trigger_reasons) else ""

    matched_sessions = matched_codex_sessions(root)
    session_bootstrap_required = (not root_agents_path.is_file()) and workspace_has_existing_content(root)
    global_codex = global_codex_agents_status()

    structure_fix_confirmation_required = False
    structure_fix_reasons: list[str] = []
    profile = read_json(root / ".agents" / "agents-control.json")
    if isinstance(profile, dict):
        contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract"), dict) else {}
        primary_root = str(contract.get("primary_project_root", "")).strip().strip("/")
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


def extract_context(root: Path) -> dict[str, Any]:
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

    return {
        "documentation": sorted(dict.fromkeys(documentation)),
        "adrs": sorted(dict.fromkeys(adrs)),
        "utilities": sorted(dict.fromkeys(utilities)),
        "quality_configs": sorted(dict.fromkeys(quality_configs)),
        "platform_files": sorted(dict.fromkeys(platform_files)),
        "ide_settings": sorted(dict.fromkeys(ide_settings)),
        "architecture_files": sorted(dict.fromkeys(architecture_files)),
        "dependency_configs": sorted(dict.fromkeys(dependency_configs)),
        "hook_configs": sorted(dict.fromkeys(hook_configs)),
        "github_settings": sorted(dict.fromkeys(github_settings)),
        "directory_coverage_candidates": sorted(dict.fromkeys(directory_coverage_candidates)),
        "reference_projects": sorted(dict.fromkeys(reference_projects)),
        "agent_configs": sorted(dict.fromkeys(agent_configs)),
        "golden_samples": sorted(dict.fromkeys(golden_samples)),
        "ci_rules": workflow_runs(root),
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


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)


def today() -> str:
    return date.today().isoformat()


def current_timestamp() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_args(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("project", nargs="?", default=".", help="Target project directory")
    return parser
