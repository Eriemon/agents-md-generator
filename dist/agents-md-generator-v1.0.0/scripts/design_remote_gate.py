
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from design_questions import *

def use_remote_server_enabled(answers: dict[str, Any]) -> bool:
    return bool(answers.get(USE_REMOTE_SERVER_KEY))

def normalize_remote_task_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        values = [str(item).strip() for item in raw]
    elif isinstance(raw, str):
        values = [part.strip() for part in re.split(r"[\r\n,，;；]+", raw)]
    else:
        values = []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(value)
    return normalized


def normalize_remote_task_name(raw: Any) -> str:
    return str(raw or "").strip()


def normalize_remote_task_key(raw: Any) -> str:
    return normalize_remote_task_name(raw).casefold()


def normalize_remote_server_registry(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    registry: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        server_id = str(item.get("id", "")).strip()
        if not server_id or server_id in seen:
            continue
        seen.add(server_id)
        registry.append(
            {
                "id": server_id,
                "name": str(item.get("name", "")).strip(),
                "category": str(item.get("category", "")).strip(),
                "functions": normalize_remote_task_list(item.get("functions", [])),
                "enabled": bool(item.get("enabled", False)),
                "validation_status": str(item.get("validation_status", "")).strip(),
                "workspace_status": str(item.get("workspace_status", "")).strip(),
            }
        )
    return registry


def normalize_remote_task_routes(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    routes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        task_name = normalize_remote_task_name(item.get("task_name", ""))
        task_key = normalize_remote_task_key(task_name)
        if not task_name or not task_key or task_key in seen:
            continue
        seen.add(task_key)
        primary_server_id = str(item.get("primary_server_id", "")).strip()
        fallback_server_ids: list[str] = []
        seen_fallbacks: set[str] = set()
        for server_id in normalize_remote_task_list(item.get("fallback_server_ids", [])):
            if server_id == primary_server_id or server_id in seen_fallbacks:
                continue
            seen_fallbacks.add(server_id)
            fallback_server_ids.append(server_id)
        route_tasks = normalize_remote_task_list(item.get("route_tasks", item.get("server_tasks", [])))
        route_functions = normalize_remote_task_list(item.get("route_functions", item.get("source_functions", [])))
        routes.append(
            {
                "task_name": task_name,
                "task_key": task_key,
                "primary_server_id": primary_server_id,
                "fallback_server_ids": fallback_server_ids,
                "route_tasks": route_tasks,
                "route_functions": route_functions,
                "selection_confirmed": bool(item.get("selection_confirmed", False)),
                "validation_status": str(item.get("validation_status", "")).strip(),
            }
        )
    return routes


def remote_settings_path(skill_dir: Path) -> Path | None:
    for relative in ("assets/defaults.json", "config/defaults.json"):
        candidate = skill_dir / relative
        if candidate.is_file():
            return candidate
    return None


def remote_skill_dir() -> Path | None:
    override = os.environ.get("AGENTS_MD_REMOTE_SSH_SKILL_DIR", "").strip()
    candidates: list[Path] = []
    if override:
        candidates.append(Path(override).resolve())
    codex_home = os.environ.get("CODEX_HOME", "").strip()
    if codex_home:
        candidates.append((Path(codex_home).resolve() / "skills" / REMOTE_SSH_SKILL_NAME).resolve())
    else:
        candidates.append((Path.home() / ".codex" / "skills" / REMOTE_SSH_SKILL_NAME).resolve())
    for candidate in candidates:
        if (
            candidate.is_dir()
            and (candidate / "SKILL.md").is_file()
            and (candidate / "scripts" / "remote_ssh.py").is_file()
            and remote_settings_path(candidate) is not None
        ):
            return candidate
    return None

def remote_dependency_summary() -> dict[str, Any]:
    skill_dir = remote_skill_dir()
    return {
        "installed": skill_dir is not None,
        "skill_dir": str(skill_dir) if skill_dir else "",
        "url": REMOTE_SSH_GIT_URL,
        "install_specs": list(REMOTE_SSH_INSTALL_SPECS),
    }

def remote_ssh_command(skill_dir: Path, subcommand: str, *extra: str) -> list[str]:
    command = [
        sys.executable,
        str(skill_dir / "scripts" / "remote_ssh.py"),
        subcommand,
    ]
    settings_path = remote_settings_path(skill_dir)
    if settings_path is not None:
        command.extend(["--settings", str(settings_path)])
    command.extend(extra)
    return command

def run_remote_ssh(skill_dir: Path, subcommand: str, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        remote_ssh_command(skill_dir, subcommand, *extra),
        text=True,
        capture_output=True,
        check=False,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )

def parse_remote_kv(stdout: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in stdout.splitlines():
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        data[key.strip()] = value.strip()
    return data

def remote_discover(skill_dir: Path) -> tuple[dict[str, Any], list[str]]:
    result = run_remote_ssh(skill_dir, "discover", "--json")
    errors: list[str] = []
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        data = {}
        errors.append("erie-remote-ssh discover did not return valid JSON")
    if not isinstance(data, dict):
        data = {}
        errors.append("erie-remote-ssh discover JSON must be an object")
    data.setdefault("status", "failed")
    data.setdefault("message", "")
    data.setdefault("next_action", "")
    data["returncode"] = result.returncode
    if result.returncode not in {0, 3, 4}:
        summary = result.stderr.strip() or result.stdout.strip() or f"unexpected discover return code {result.returncode}"
        errors.append(f"erie-remote-ssh discover failed: {summary}")
    return data, errors

def remote_choices(skill_dir: Path) -> tuple[dict[str, Any], list[str]]:
    result = run_remote_ssh(skill_dir, "choices", "--json")
    errors: list[str] = []
    try:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        data = {}
        errors.append("erie-remote-ssh choices did not return valid JSON")
    if not isinstance(data, dict):
        data = {}
        errors.append("erie-remote-ssh choices JSON must be an object")
    servers = data.get("servers", [])
    if not isinstance(servers, list):
        servers = []
        errors.append("erie-remote-ssh choices JSON must contain a servers list")
    data["servers"] = servers
    data.setdefault("status", "failed")
    data["returncode"] = result.returncode
    if result.returncode not in {0, 4}:
        summary = result.stderr.strip() or result.stdout.strip() or f"unexpected choices return code {result.returncode}"
        errors.append(f"erie-remote-ssh choices failed: {summary}")
    return data, errors

def remote_server_record(records: list[dict[str, Any]], selector: str) -> dict[str, Any] | None:
    selector_fold = selector.strip().casefold()
    for record in records:
        if not isinstance(record, dict):
            continue
        if selector_fold in {str(record.get("id", "")).casefold(), str(record.get("name", "")).casefold()}:
            return record
    return None

def remote_server_check(skill_dir: Path, server_id: str) -> tuple[dict[str, str], list[str]]:
    result = run_remote_ssh(skill_dir, "check", "--server", server_id)
    data = parse_remote_kv(result.stdout)
    errors: list[str] = []
    if result.returncode != 0:
        summary = result.stderr.strip() or result.stdout.strip() or f"check failed with return code {result.returncode}"
        errors.append(f"erie-remote-ssh check failed for {server_id}: {summary}")
    if data.get("status") != "ok":
        errors.append(f"erie-remote-ssh check did not return ok status for {server_id}")
    return data, errors

def remote_server_workspace_check(skill_dir: Path, server_id: str) -> tuple[dict[str, str], list[str]]:
    result = run_remote_ssh(skill_dir, "workspace-check", "--server", server_id)
    data = parse_remote_kv(result.stdout)
    errors: list[str] = []
    if result.returncode != 0:
        summary = result.stderr.strip() or result.stdout.strip() or f"workspace-check failed with return code {result.returncode}"
        errors.append(f"erie-remote-ssh workspace-check failed for {server_id}: {summary}")
    if data.get("status") != "ok":
        errors.append(f"erie-remote-ssh workspace-check did not return ok status for {server_id}")
    return data, errors

def remote_install_command_hint(skill_dir: Path | None = None) -> str:
    if skill_dir is not None:
        return f"Install `{REMOTE_SSH_SKILL_NAME}` from {REMOTE_SSH_GIT_URL}, then rerun `python scripts/collect_design_profile.py <project> --resume`."
    return f"Install `{REMOTE_SSH_SKILL_NAME}` from {REMOTE_SSH_GIT_URL}, then rerun `python scripts/collect_design_profile.py <project> --resume`."

def remote_configure_command_hint(skill_dir: Path) -> str:
    command = f"python {skill_dir / 'scripts' / 'remote_ssh.py'} configure"
    settings_path = remote_settings_path(skill_dir)
    if settings_path is not None:
        command += f" --settings {settings_path}"
    command += " --interactive"
    return command

def remote_gate_payload(state: dict[str, Any]) -> dict[str, Any]:
    gate = state.get("remote_server_gate", {})
    return gate if isinstance(gate, dict) else {}

def set_remote_gate_payload(state: dict[str, Any], payload: dict[str, Any]) -> None:
    state["remote_server_gate"] = payload


def server_registry_map(registry: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id", "")).strip(): item
        for item in registry
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }


def ordered_route_server_ids(route: dict[str, Any]) -> list[str]:
    primary = str(route.get("primary_server_id", "")).strip()
    ordered: list[str] = []
    if primary:
        ordered.append(primary)
    for server_id in normalize_remote_task_list(route.get("fallback_server_ids", [])):
        if server_id not in ordered:
            ordered.append(server_id)
    return ordered


def match_remote_task_route(task_routes: list[dict[str, Any]], task_name: str) -> dict[str, Any] | None:
    task_key = normalize_remote_task_key(task_name)
    if not task_key:
        return None
    for route in task_routes:
        if not isinstance(route, dict):
            continue
        if normalize_remote_task_key(route.get("task_name", "")) == task_key:
            return route
    return None


def validate_route_server_ids(route: dict[str, Any], registry: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    task_name = str(route.get("task_name", "")).strip() or "<unknown>"
    primary = str(route.get("primary_server_id", "")).strip()
    if not primary:
        errors.append(f"route `{task_name}` is missing primary_server_id")
    elif primary not in registry:
        errors.append(f"route `{task_name}` references unknown primary server `{primary}`")
    for server_id in normalize_remote_task_list(route.get("fallback_server_ids", [])):
        if server_id not in registry:
            errors.append(f"route `{task_name}` references unknown fallback server `{server_id}`")
    return errors


def resolve_remote_server_for_task(contract: dict[str, Any], task_name: str, skill_dir: Path | None = None) -> dict[str, Any]:
    if not isinstance(contract, dict) or not contract.get("enabled"):
        return {
            "ok": False,
            "decision": "blocked",
            "message": "Remote server routing is not enabled for this work folder.",
        }
    routes = normalize_remote_task_routes(contract.get("task_routes", []))
    route = match_remote_task_route(routes, task_name)
    if route is None:
        return {
            "ok": False,
            "decision": "blocked",
            "message": "No registered remote server route matches this task. Update the current work folder AGENTS.md before continuing.",
        }
    registry = server_registry_map(normalize_remote_server_registry(contract.get("server_registry", [])))
    route_errors = validate_route_server_ids(route, registry)
    if route_errors:
        return {
            "ok": False,
            "decision": "blocked",
            "message": "; ".join(route_errors),
            "matched_route": route,
        }
    dependency = remote_dependency_summary()
    active_skill_dir = skill_dir
    if active_skill_dir is None and dependency.get("installed"):
        active_skill_dir = Path(str(dependency.get("skill_dir", "")))
    if active_skill_dir is None or not str(active_skill_dir):
        return {
            "ok": False,
            "decision": "blocked",
            "message": f"Remote dependency `{REMOTE_SSH_SKILL_NAME}` is not installed.",
            "matched_route": route,
        }
    attempted_server_ids: list[str] = []
    failures: list[str] = []
    for server_id in ordered_route_server_ids(route):
        attempted_server_ids.append(server_id)
        check_data, check_errors = remote_server_check(active_skill_dir, server_id)
        workspace_data, workspace_errors = remote_server_workspace_check(active_skill_dir, server_id) if not check_errors else ({}, [])
        errors = check_errors + workspace_errors
        if errors:
            failures.append(f"{server_id}: {'; '.join(errors)}")
            continue
        return {
            "ok": True,
            "decision": "selected",
            "matched_route": route,
            "selected_server_id": server_id,
            "selected_server": registry.get(server_id, {}),
            "check": check_data,
            "workspace_check": workspace_data,
            "attempted_server_ids": attempted_server_ids,
            "failures": failures,
        }
    return {
        "ok": False,
        "decision": "blocked",
        "message": "All primary and fallback remote servers for the matched task failed validation.",
        "matched_route": route,
        "attempted_server_ids": attempted_server_ids,
        "failures": failures,
    }
