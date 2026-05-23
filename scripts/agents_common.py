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


def governance_skill_name() -> str:
    return "agents-md-generator"

def skill_version_file(root: Path | None = None) -> Path:
    return (root or skill_root()) / "VERSION"

def read_skill_version(root: Path | None = None) -> str:
    path = skill_version_file(root)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()

def installed_skill_dir(skill_name: str = "agents-md-generator", override_dir: str | Path | None = None) -> Path | None:
    override = str(override_dir).strip() if override_dir is not None else os.environ.get("AGENTS_MD_INSTALLED_SKILL_DIR", "").strip()
    if override:
        path = Path(override).expanduser().resolve()
        return path if path.exists() else None
    codex_home = os.environ.get("CODEX_HOME", "").strip()
    home_root = Path(codex_home).expanduser().resolve() if codex_home else (Path.home() / ".codex").resolve()
    path = home_root / "skills" / skill_name
    return path if path.exists() else None


def current_governance_skill_dirs(skill_name: str | None = None, override_dir: str | Path | None = None) -> list[Path]:
    target_name = skill_name or governance_skill_name()
    dirs: list[Path] = []
    runtime = skill_root().resolve()
    dirs.append(runtime)
    installed = installed_skill_dir(target_name, override_dir=override_dir)
    if installed is not None:
        installed_resolved = installed.resolve()
        if all(existing != installed_resolved for existing in dirs):
            dirs.append(installed_resolved)
    return dirs


def evolution_owner_status(
    project: Path,
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> dict[str, Any]:
    target_name = skill_name or governance_skill_name()
    resolved_project = project.resolve()
    active_skill_dirs = current_governance_skill_dirs(target_name, override_dir=override_dir)

    source_repo_skill_dir = resolved_project / "skills" / target_name
    if source_repo_skill_dir.is_dir():
        candidate = source_repo_skill_dir.resolve()
        if any(candidate == active for active in active_skill_dirs):
            return {
                "enabled": True,
                "mode": "source-repo",
                "project_root": str(resolved_project),
                "owner_skill_dir": str(candidate),
            }

    if any(resolved_project == active for active in active_skill_dirs):
        return {
            "enabled": True,
            "mode": "installed-skill",
            "project_root": str(resolved_project),
            "owner_skill_dir": str(resolved_project),
        }

    return {
        "enabled": False,
        "mode": "non-owner",
        "project_root": str(resolved_project),
        "owner_skill_dir": "",
    }


def path_is_writable(path: Path) -> bool:
    target = path if path.suffix == "" else path.parent
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".write-probe.tmp"
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink()
        return True
    except Exception:
        return False


def installed_governance_skill_dir(
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> Path | None:
    target_name = skill_name or governance_skill_name()
    installed = installed_skill_dir(target_name, override_dir=override_dir)
    return installed.resolve() if installed is not None else None


def evolution_template_sink(
    project: Path,
    skill_name: str | None = None,
    override_dir: str | Path | None = None,
) -> dict[str, Any]:
    target_name = skill_name or governance_skill_name()
    status = evolution_owner_status(project, skill_name=target_name, override_dir=override_dir)
    project_root = project.resolve()
    if status.get("enabled"):
        owner_skill_dir = Path(str(status.get("owner_skill_dir", ""))).resolve()
        template_root = owner_skill_dir / "assets" / "templates" / "evolution"
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

    installed = installed_governance_skill_dir(target_name, override_dir=override_dir)
    if installed is not None:
        template_root = installed / "assets" / "templates" / "evolution"
        if path_is_writable(template_root):
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

def read_installed_skill_version(skill_name: str = "agents-md-generator", override_dir: str | Path | None = None) -> str:
    installed = installed_skill_dir(skill_name, override_dir=override_dir)
    if installed is None:
        return ""
    return read_skill_version(installed)

def preferred_skill_version(skill_name: str = "agents-md-generator", override_dir: str | Path | None = None) -> tuple[str, str]:
    installed = read_installed_skill_version(skill_name, override_dir=override_dir)
    if installed:
        return installed, "installed-override" if override_dir else "installed"
    runtime = read_skill_version()
    if runtime:
        return runtime, "runtime"
    return "", "unavailable"

def project_profile(root: Path) -> dict[str, Any]:
    path = root / ".agents" / "agents-control.json"
    return read_json(path) if path.exists() else {}

def primary_project_root_from_profile(profile: dict[str, Any] | None) -> str:
    if not isinstance(profile, dict):
        return ""
    directory_contract = profile.get("directory_contract", {})
    if not isinstance(directory_contract, dict):
        return ""
    return str(directory_contract.get("primary_project_root", "")).strip().strip("/\\")

def managed_scripts_root(root: Path, profile: dict[str, Any] | None = None) -> str:
    if (root / "scripts").is_dir():
        return "scripts"
    effective_profile = profile if isinstance(profile, dict) else project_profile(root)
    primary_root = primary_project_root_from_profile(effective_profile)
    if primary_root:
        primary_scripts = root / primary_root / "scripts"
        if primary_scripts.is_dir():
            return primary_scripts.relative_to(root).as_posix()
        return f"{primary_root}/scripts"
    return "scripts"

def script_command(root: Path, script_name: str, *args: str, profile: dict[str, Any] | None = None) -> str:
    script_root = managed_scripts_root(root, profile)
    segments = ["python", f"{script_root}/{script_name}", *[str(item) for item in args if str(item).strip()]]
    return " ".join(segments)

def root_agents_sync_command(root: Path, profile: dict[str, Any] | None = None, installed_skill_dir_override: str | Path | None = None) -> str:
    command = script_command(root, "manage_docs.py", "sync-root-agents", ".", "--write", profile=profile)
    if installed_skill_dir_override is not None:
        command += f" --installed-skill-dir {Path(installed_skill_dir_override).as_posix()}"
    return command

def global_codex_agents_sync_command(root: Path, profile: dict[str, Any] | None = None) -> str:
    return script_command(root, "manage_docs.py", "sync-global-codex-agents", ".", "--write", profile=profile)

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

def global_codex_agents_status(codex_home: str | None = None, project_root: Path | None = None, profile: dict[str, Any] | None = None) -> dict[str, Any]:
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
        "repair_command": global_codex_agents_sync_command(project_root, profile) if project_root else "python scripts/manage_docs.py sync-global-codex-agents . --write",
        "recommended_action": global_codex_agents_sync_command(project_root, profile) if project_root else "python scripts/manage_docs.py sync-global-codex-agents . --write",
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

from agents_project_facts import (
    command_entry,
    default_implementation_constraints,
    default_global_rule_overrides,
    decomposition_plan_path,
    detect_scopes,
    ensure_global_rule_overrides_file,
    existing_paths,
    extract_commands,
    extract_context,
    file_line_count,
    global_rule_overrides_path,
    global_rule_overrides_reference,
    has_any,
    implementation_constraints_from_profile,
    inspect_project,
    iter_handwritten_code_files,
    list_dirs,
    list_files,
    load_global_rule_overrides,
    managed_script_roots,
    matched_codex_sessions,
    parse_session_meta,
    script_governance_exceptions,
    script_layout_facts,
    session_message_rows,
    validate_global_rule_overrides_data,
    workflow_runs,
)
