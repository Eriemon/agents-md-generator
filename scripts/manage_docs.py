from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, inspect_project, read_json, resolve_project
from manage_dirs import init_dir_manager, verify_dir_manager


DOC_DIRS = [
    "docs/handoff",
    "docs/handoff/history_handoff",
    "docs/experience",
    "docs/experience/history_experience",
    "docs/development",
    "docs/install_configuration",
    "docs/git_manager",
    "docs/dir_manager",
    "docs/dir_manager/change_reviews",
    "docs/dir_manager/history_dir_manager",
]
REQUIRED_DOC_FILES = [
    "docs/handoff/HANDOFF.md",
    "docs/install_configuration/INSTALL_CONFIGURATION.md",
    "docs/git_manager/GIT_MANAGER.md",
]
FIXED_EXPERIENCE_TOPICS = [
    ("1-workflow.md", "Workflow", "Workflow lessons for this specific project or skill."),
    ("2-scripts.md", "Scripts", "Code writing, script development, and automation lessons."),
    ("3-plan.md", "Plan", "Task planning, decomposition, sequencing, and handoff lessons."),
    ("4-design-ui.md", "Design UI", "GUI, UI, visual design, and polish lessons. Record no UI lessons yet when not applicable."),
]
DEFAULT_OPTIONAL_EXPERIENCE_TOPICS = [
    ("testing", "Testing"),
    ("validation", "Validation"),
    ("release", "Release"),
    ("installation", "Installation"),
    ("docs-governance", "Docs Governance"),
    ("directory-governance", "Directory Governance"),
]
REMOTE_OPTIONAL_EXPERIENCE_TOPICS = [
    ("testing", "Testing"),
    ("validation", "Validation"),
    ("release", "Release"),
    ("docs-governance", "Docs Governance"),
    ("directory-governance", "Directory Governance"),
    ("remote-deployment", "Remote Deployment"),
]
STATE_PATH = ".agents/docs-governance-state.json"
ACTIVE_SESSION_PATH = ".agents/active-session.json"
EXPERIENCE_REQUEST_PATH = ".agents/experience-update-request.json"
CONVERSATION_SNAPSHOT_DIR = ".agents/conversation-snapshots"
HANDOFF_SECTIONS = [
    "Original Plan And Steps",
    "Current Step",
    "Problems",
    "Resolved Problems",
    "Remaining Problems",
    "Next Work",
    "Verification Evidence",
]


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def docs_root(project: Path) -> Path:
    return project / "docs"


def state_file(project: Path) -> Path:
    return project / STATE_PATH


def active_session_file(project: Path) -> Path:
    return project / ACTIVE_SESSION_PATH


def experience_request_file(project: Path) -> Path:
    return project / EXPERIENCE_REQUEST_PATH


def conversation_snapshot_dir(project: Path) -> Path:
    return project / CONVERSATION_SNAPSHOT_DIR


def load_state(project: Path) -> dict[str, Any]:
    state = read_json(state_file(project))
    return state if isinstance(state, dict) else {}


def save_state(project: Path, state: dict[str, Any]) -> None:
    agents_dir = project / ".agents"
    agents_dir.mkdir(exist_ok=True)
    state_file(project).write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def file_hash(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def list_lines(values: Any) -> str:
    if values is None or values == "":
        return "- Not recorded."
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        values = [str(values)]
    lines = [str(item).strip() for item in values if str(item).strip()]
    if not lines:
        return "- Not recorded."
    return "\n".join(f"- {line}" for line in lines)


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")
    return cleaned or "stage"


def default_handoff() -> str:
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


def control_profile(project: Path) -> dict[str, Any]:
    data = read_json(project / ".agents" / "agents-control.json")
    return data if isinstance(data, dict) else {}


def remote_structure_from_profile(project: Path) -> str:
    profile = control_profile(project)
    contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract"), dict) else {}
    remote = str(contract.get("remote", "")).strip()
    if not remote or remote.lower() in {"none", "not configured", "no remote workspace is configured for this project; default to local-only git management unless the user explicitly requests remote work."}:
        return ""
    return remote


def project_specific_experience_topics(project: Path) -> list[tuple[str, str]]:
    remote = remote_structure_from_profile(project)
    topics = REMOTE_OPTIONAL_EXPERIENCE_TOPICS if remote else DEFAULT_OPTIONAL_EXPERIENCE_TOPICS
    return [(f"{index}-{slug_name}.md", title) for index, (slug_name, title) in enumerate(topics, start=5)]


def experience_file_specs(project: Path) -> list[dict[str, str]]:
    specs = [
        {"filename": filename, "title": title, "focus": focus}
        for filename, title, focus in FIXED_EXPERIENCE_TOPICS
    ]
    for filename, title in project_specific_experience_topics(project):
        focus = f"Project-specific {title.lower()} lessons selected from current repository facts."
        specs.append({"filename": filename, "title": title, "focus": focus})
    return specs[:10]


def experience_markdown(project: Path, spec: dict[str, str], count: int, latest_text: str, generated: bool) -> str:
    facts = inspect_project(project)
    profile = control_profile(project)
    remote = remote_structure_from_profile(project) or "not configured"
    status = "Initialized" if not generated else "Awaiting AI experience summary"
    if spec["filename"] == "4-design-ui.md":
        default_lesson = "- 暂无 UI 经验。AI must replace this placeholder only after reading the required evidence."
    else:
        default_lesson = f"- Awaiting AI experience summary for {spec['title'].lower()}; scripts must not fabricate lessons."
    return "\n".join([
        f"# {spec['title']} Experience",
        "",
        f"- File: {spec['filename']}",
        f"- Status: {status}",
        f"- Handoff count: {count}",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Project type: {facts.get('project_type', 'unknown')}",
        f"- Skill/project name: {profile.get('name', project.name)}",
        f"- Remote deployment structure: {remote}",
        "",
        "## Focus",
        f"- {spec['focus']}",
        "",
        "## Iterated Lessons",
        default_lesson,
        "",
        "## Required AI Evidence",
        "- Current HANDOFF.md.",
        "- Recent handoff history.",
        "- Current and historical experience files.",
        "- Current project facts and control profile.",
        "- Recent conversation snapshots, up to 10 entries.",
        "",
    ])


def ensure_experience_files(project: Path) -> list[str]:
    experience = project / "docs" / "experience"
    experience.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    expected_names = {spec["filename"] for spec in experience_file_specs(project)}
    current_numbered = {path.name for path in experience.glob("[0-9]*-*.md") if path.is_file()}
    if current_numbered and current_numbered != expected_names:
        archive_experience_files(project)
    latest = project / "docs" / "handoff" / "HANDOFF.md"
    latest_text = latest.read_text(encoding="utf-8", errors="ignore") if latest.exists() else ""
    count = int(load_state(project).get("handoff_count", 0))
    for spec in experience_file_specs(project):
        target = experience / spec["filename"]
        if not target.exists():
            target.write_text(experience_markdown(project, spec, count, latest_text, generated=False), encoding="utf-8")
            created.append(f"docs/experience/{spec['filename']}")
    return created


def install_configuration_doc() -> str:
    return "\n".join([
        "# Install Configuration",
        "",
        "## Skill Install Path",
        "- Install the skill folder into the target agent skill directory before use.",
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


def git_manager_doc() -> str:
    return "\n".join([
        "# Git Manager",
        "",
        "## Workspace Management",
        "- Keep current development work in the working folder unless the user requests a separate worktree.",
        "",
        "## Branch Configuration",
        "- Master/main holds the editable source branch.",
        "- Release branches or release folders are recorded before packaging.",
        "",
        "## Release Configuration",
        "- Place installable releases under `dist/`.",
        "- Name installable release folders as `<name>-vx.x.x` and create a matching zip when required.",
        "",
        "## Current Version",
        "- Record the active version and release notes here during release preparation.",
        "",
    ])


def preflight_docs(project: Path) -> dict[str, Any]:
    docs = docs_root(project)
    question = "是否允许在现有 docs/ 下添加 AGENTS.md governance 子目录和记录文件？"
    if not docs.exists():
        return {
            "project": str(project),
            "status": "safe",
            "docs_exists": False,
            "safe_to_scaffold": True,
            "conflicts": [],
            "requires_user_confirmation": False,
            "question": "",
        }
    if not docs.is_dir():
        return {
            "project": str(project),
            "status": "conflict",
            "docs_exists": True,
            "safe_to_scaffold": False,
            "conflicts": ["docs exists but is not a directory"],
            "requires_user_confirmation": True,
            "question": question,
        }

    reserved_paths = [*DOC_DIRS, *REQUIRED_DOC_FILES]
    conflicts: list[str] = []
    reserved_exists = False
    for rel_path in reserved_paths:
        path = project / rel_path
        if path.exists():
            reserved_exists = True
            if rel_path in DOC_DIRS and not path.is_dir():
                conflicts.append(f"{rel_path} exists but is not a directory")
            if rel_path in REQUIRED_DOC_FILES and not path.is_file():
                conflicts.append(f"{rel_path} exists but is not a file")

    docs_result = verify_docs(project)
    if not docs_result["errors"]:
        return {
            "project": str(project),
            "status": "safe",
            "docs_exists": True,
            "safe_to_scaffold": True,
            "conflicts": [],
            "requires_user_confirmation": False,
            "question": "",
        }

    if reserved_exists:
        conflicts.extend(item for item in docs_result["errors"] if item not in conflicts)
        return {
            "project": str(project),
            "status": "conflict",
            "docs_exists": True,
            "safe_to_scaffold": False,
            "conflicts": conflicts,
            "requires_user_confirmation": True,
            "question": question,
        }

    existing = [
        path.relative_to(project).as_posix()
        for path in sorted(docs.rglob("*"))
        if path.is_file() or path.is_dir()
    ]
    conflicts = existing or ["docs/ exists but AGENTS.md governance structure is not initialized"]
    return {
        "project": str(project),
        "status": "ambiguous",
        "docs_exists": True,
        "safe_to_scaffold": False,
        "conflicts": conflicts,
        "requires_user_confirmation": True,
        "question": question,
    }


def scaffold(project: Path) -> dict[str, Any]:
    created: list[str] = []
    for rel_path in DOC_DIRS:
        path = project / rel_path
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(rel_path)
    files = {
        "docs/handoff/HANDOFF.md": default_handoff(),
        "docs/install_configuration/INSTALL_CONFIGURATION.md": install_configuration_doc(),
        "docs/git_manager/GIT_MANAGER.md": git_manager_doc(),
    }
    for rel_path, content in files.items():
        path = project / rel_path
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(rel_path)
    state = load_state(project)
    state.setdefault("handoff_count", 0)
    state.setdefault("last_experience_at", 0)
    state["dir_manager_last_scan"] = datetime.now().isoformat(timespec="seconds")
    save_state(project, state)
    dir_result = init_dir_manager(project)
    created.extend(path for path in dir_result.get("written", []) if path not in created)
    created.extend(path for path in ensure_experience_files(project) if path not in created)
    return {"project": str(project), "created": created, "state": state}


def read_input(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    data = read_json(Path(path).resolve())
    if not isinstance(data, dict):
        raise SystemExit(f"Input must be a JSON object: {path}")
    return data


def rotate_handoff(project: Path) -> str | None:
    current = project / "docs" / "handoff" / "HANDOFF.md"
    if not current.exists():
        return None
    history = project / "docs" / "handoff" / "history_handoff"
    history.mkdir(parents=True, exist_ok=True)
    target = history / f"HANDOFF-{stamp()}.md"
    while target.exists():
        target = history / f"HANDOFF-{stamp()}-{len(list(history.glob('HANDOFF-*.md')))}.md"
    shutil.move(str(current), str(target))
    return str(target)


def handoff_markdown(data: dict[str, Any], count: int) -> str:
    return "\n".join([
        "# Handoff",
        "",
        f"- Handoff count: {count}",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Original Plan And Steps",
        list_lines(data.get("original_plan") or data.get("plan")),
        "",
        "## Current Step",
        list_lines(data.get("current_step")),
        "",
        "## Problems",
        list_lines(data.get("problems")),
        "",
        "## Resolved Problems",
        list_lines(data.get("resolved") or data.get("resolved_problems")),
        "",
        "## Remaining Problems",
        list_lines(data.get("remaining") or data.get("remaining_problems")),
        "",
        "## Next Work",
        list_lines(data.get("next") or data.get("next_work")),
        "",
        "## Verification Evidence",
        list_lines(data.get("verification") or data.get("verification_evidence")),
        "",
    ])


def maybe_write_conversation_snapshot(project: Path, data: dict[str, Any], count: int) -> str | None:
    fields = {
        "conversation_summary": data.get("conversation_summary"),
        "conversation_excerpt": data.get("conversation_excerpt"),
        "conversation_log_path": data.get("conversation_log_path"),
    }
    if not any(str(value or "").strip() for value in fields.values()):
        return None
    snapshot_dir = conversation_snapshot_dir(project)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    log_excerpt = ""
    log_path_raw = str(fields.get("conversation_log_path") or "").strip()
    if log_path_raw:
        log_path = Path(log_path_raw)
        if not log_path.is_absolute():
            log_path = project / log_path
        if log_path.exists() and log_path.is_file():
            log_excerpt = log_path.read_text(encoding="utf-8", errors="ignore")[:8000]
    snapshot = {
        "handoff_count": count,
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "source": "handoff input",
        "conversation_summary": fields.get("conversation_summary") or "",
        "conversation_excerpt": fields.get("conversation_excerpt") or "",
        "conversation_log_path": log_path_raw,
        "conversation_log_excerpt": log_excerpt,
    }
    target = snapshot_dir / f"{stamp()}-handoff-{count}.json"
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return str(target.relative_to(project).as_posix())


def write_handoff(project: Path, input_path: str | None) -> dict[str, Any]:
    scaffold(project)
    archived = rotate_handoff(project)
    state = load_state(project)
    count = int(state.get("handoff_count", 0)) + 1
    data = read_input(input_path)
    target = project / "docs" / "handoff" / "HANDOFF.md"
    target.write_text(handoff_markdown(data, count), encoding="utf-8")
    snapshot = maybe_write_conversation_snapshot(project, data, count)
    state["handoff_count"] = count
    save_state(project, state)
    active = active_session_file(project)
    if active.exists():
        active.unlink()
    result = {"project": str(project), "written": str(target), "archived": archived, "handoff_count": count}
    if snapshot:
        result["conversation_snapshot"] = snapshot
    if count % 5 == 0:
        result["experience"] = write_experience(project, force=True)
    return result


def write_active_session(project: Path, input_path: str | None) -> dict[str, Any]:
    scaffold(project)
    data = read_input(input_path)
    handoff = project / "docs" / "handoff" / "HANDOFF.md"
    active = {
        "task": data.get("task", "not recorded"),
        "current_step": data.get("current_step", "not recorded"),
        "conversation_summary": data.get("conversation_summary", ""),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "handoff_path": "docs/handoff/HANDOFF.md",
        "handoff_hash": file_hash(handoff),
        "handoff_mtime": handoff.stat().st_mtime if handoff.exists() else 0,
    }
    agents_dir = project / ".agents"
    agents_dir.mkdir(exist_ok=True)
    active_session_file(project).write_text(json.dumps(active, indent=2, sort_keys=True), encoding="utf-8")
    return {"project": str(project), "written": str(active_session_file(project)), "active_session": active}


def read_active_session(project: Path) -> dict[str, Any]:
    active = read_json(active_session_file(project))
    return active if isinstance(active, dict) else {}


def resume_check(project: Path, conversation_log: str | None = None) -> dict[str, Any]:
    active = read_active_session(project)
    if not active:
        return {
            "project": str(project),
            "status": "clean",
            "interrupted": False,
            "reasons": ["no active session found"],
        }
    handoff = project / "docs" / "handoff" / "HANDOFF.md"
    current_hash = file_hash(handoff)
    reasons: list[str] = []
    interrupted = False
    if current_hash and current_hash == active.get("handoff_hash"):
        interrupted = True
        reasons.append("HANDOFF.md has not changed since active session started")
    elif not current_hash:
        interrupted = True
        reasons.append("HANDOFF.md is missing while an active session exists")
    else:
        reasons.append("HANDOFF.md changed after active session started")

    if conversation_log:
        log_path = Path(conversation_log).resolve()
        if log_path.exists():
            text = log_path.read_text(encoding="utf-8", errors="ignore").lower()
            if any(marker in text for marker in ["stop", "stopped", "interrupted", "断网", "强制停止", "中断"]):
                interrupted = True
                reasons.append("conversation log contains interruption markers")

    return {
        "project": str(project),
        "status": "interrupted" if interrupted else "clean",
        "interrupted": interrupted,
        "active_session": active,
        "current_handoff_hash": current_hash,
        "reasons": reasons,
    }


def resume_repair(project: Path, input_path: str | None) -> dict[str, Any]:
    check = resume_check(project)
    if not check["interrupted"]:
        return {
            "project": str(project),
            "skipped": True,
            "interrupted": False,
            "reasons": check["reasons"],
        }
    result = write_handoff(project, input_path)
    result["recovery"] = True
    result["interrupted"] = True
    result["resume_check"] = check
    return result


def archive_experience_files(project: Path) -> list[str]:
    experience = project / "docs" / "experience"
    history_root = experience / "history_experience"
    candidates = [
        path for path in sorted(experience.glob("*.md"))
        if path.is_file()
    ]
    if not candidates:
        return []
    target_dir = history_root / stamp()
    target_dir.mkdir(parents=True, exist_ok=True)
    archived: list[str] = []
    for path in candidates:
        target = target_dir / path.name
        shutil.move(str(path), str(target))
        archived.append(str(target))
    return archived


def recent_conversation_context(project: Path, limit: int = 10) -> list[dict[str, Any]]:
    root = conversation_snapshot_dir(project)
    if not root.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json"), reverse=True)[:limit]:
        data = read_json(path)
        if isinstance(data, dict):
            data["path"] = path.relative_to(project).as_posix()
            items.append(data)
    return items


def recent_handoff_history(project: Path, limit: int = 10) -> list[dict[str, str]]:
    history = project / "docs" / "handoff" / "history_handoff"
    if not history.is_dir():
        return []
    rows: list[dict[str, str]] = []
    for path in sorted(history.glob("HANDOFF-*.md"), reverse=True)[:limit]:
        rows.append({"path": path.relative_to(project).as_posix(), "content": path.read_text(encoding="utf-8", errors="ignore")})
    return rows


def current_experience_files(project: Path) -> dict[str, str]:
    root = project / "docs" / "experience"
    return {
        path.name: path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted(root.glob("[0-9]*-*.md"))
        if path.is_file()
    }


def latest_historical_experience(project: Path, filenames: list[str]) -> dict[str, list[dict[str, str]]]:
    history_root = project / "docs" / "experience" / "history_experience"
    result = {name: [] for name in filenames}
    if not history_root.is_dir():
        return result
    for history_dir in sorted((path for path in history_root.iterdir() if path.is_dir()), reverse=True):
        for name in filenames:
            if len(result[name]) >= 2:
                continue
            path = history_dir / name
            if path.is_file():
                result[name].append({
                    "path": path.relative_to(project).as_posix(),
                    "content": path.read_text(encoding="utf-8", errors="ignore"),
                })
    return result


def build_experience_request(project: Path, count: int) -> dict[str, Any]:
    specs = experience_file_specs(project)
    filenames = [spec["filename"] for spec in specs]
    latest_handoff = project / "docs" / "handoff" / "HANDOFF.md"
    conversations = recent_conversation_context(project, limit=10)
    return {
        "schema_version": 1,
        "project": str(project),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "handoff_count": count,
        "requires_ai_generation": True,
        "ai_must_read_recent_conversations": True,
        "conversation_context_limit": 10,
        "conversation_context_missing": not conversations,
        "conversation_context": conversations,
        "project_facts": inspect_project(project),
        "control_profile": control_profile(project),
        "current_handoff": latest_handoff.read_text(encoding="utf-8", errors="ignore") if latest_handoff.exists() else "",
        "recent_handoff_history": recent_handoff_history(project, limit=10),
        "current_experience": current_experience_files(project),
        "historical_experience": latest_historical_experience(project, filenames),
        "target_files": specs,
        "quality_rules": [
            "AI must generate topic-specific lessons; scripts only collect evidence and apply validated payloads.",
            "Do not copy a full HANDOFF.md into experience files.",
            "Do not write highly similar content across the 10 experience files.",
            "4-design-ui.md must say 暂无 UI 经验 when no UI work was involved.",
        ],
        "payload_schema": {
            "generated_by": "ai",
            "experience_files": [{"filename": "1-workflow.md", "content": "# Workflow Experience\\n..."}],
        },
    }


def write_experience_request(project: Path, count: int) -> dict[str, Any]:
    request = build_experience_request(project, count)
    target = experience_request_file(project)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    state = load_state(project)
    state["experience_update_required"] = True
    state["experience_request"] = target.relative_to(project).as_posix()
    save_state(project, state)
    return {
        "project": str(project),
        "request_written": str(target),
        "handoff_count": count,
        "requires_ai_generation": True,
        "conversation_context_missing": request["conversation_context_missing"],
        "conversation_context_count": len(request["conversation_context"]),
        "skipped": True,
    }


def payload_entries(payload: dict[str, Any]) -> dict[str, str]:
    raw = payload.get("experience_files")
    entries: dict[str, str] = {}
    if isinstance(raw, dict):
        for filename, content in raw.items():
            entries[str(filename)] = str(content)
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                filename = str(item.get("filename", "")).strip()
                content = str(item.get("content", ""))
                if filename:
                    entries[filename] = content
    return entries


def normalized_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", text.lower())
        if len(token) > 2 and token not in {"experience", "lessons", "evidence", "read", "current"}
    }


def similarity(left: str, right: str) -> float:
    a = normalized_tokens(left)
    b = normalized_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def validate_experience_payload(project: Path, payload: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    expected = [spec["filename"] for spec in experience_file_specs(project)]
    entries = payload_entries(payload)
    errors: list[str] = []
    if str(payload.get("generated_by", "")).lower() != "ai":
        errors.append("experience payload must declare generated_by=ai")
    missing = [name for name in expected if name not in entries]
    extra = sorted(set(entries) - set(expected))
    if missing:
        errors.append(f"experience payload missing files: {', '.join(missing)}")
    if extra:
        errors.append(f"experience payload contains unexpected files: {', '.join(extra)}")
    for filename in expected:
        content = entries.get(filename, "")
        if len(content.strip()) < 160:
            errors.append(f"{filename}: AI experience content is too short")
        if "Iterate this file from completed handoffs" in content or "Awaiting AI experience summary" in content:
            errors.append(f"{filename}: contains placeholder experience text")
        if "## Original Plan And Steps" in content and "## Verification Evidence" in content:
            errors.append(f"{filename}: must not copy full HANDOFF.md sections")
        if filename == "4-design-ui.md" and "暂无 UI 经验" not in content and not re.search(r"\b(ui|gui|visual|design)\b", content, flags=re.IGNORECASE):
            errors.append("4-design-ui.md: must either record 暂无 UI 经验 or contain UI/design-specific lessons")
    for index, left_name in enumerate(expected):
        for right_name in expected[index + 1:]:
            left = entries.get(left_name, "")
            right = entries.get(right_name, "")
            if left and right and similarity(left, right) > 0.78:
                errors.append(f"{left_name} and {right_name}: experience files are too similar")
    return entries, errors


def source_versions_for(project: Path, filename: str) -> list[dict[str, str]]:
    versions: list[dict[str, str]] = []
    current = project / "docs" / "experience" / filename
    if current.is_file():
        versions.append({
            "path": current.relative_to(project).as_posix(),
            "content": current.read_text(encoding="utf-8", errors="ignore"),
        })
    history_root = project / "docs" / "experience" / "history_experience"
    if history_root.is_dir():
        for history_dir in sorted((path for path in history_root.iterdir() if path.is_dir()), reverse=True):
            path = history_dir / filename
            if path.is_file():
                versions.append({
                    "path": path.relative_to(project).as_posix(),
                    "content": path.read_text(encoding="utf-8", errors="ignore"),
                })
                break
    return versions[:2]


def evolution_template_root(project: Path) -> Path:
    profile = control_profile(project)
    layout = profile.get("skill_layout", {}) if isinstance(profile.get("skill_layout"), dict) else {}
    skill_path = str(layout.get("path") or "agents-md-generator").strip()
    candidate = project / skill_path / "assets" / "templates"
    if candidate.exists() or (project / skill_path).exists():
        return candidate / "evolution"
    return project / "assets" / "templates" / "evolution"


def evolution_slugs(project: Path) -> tuple[str, str]:
    profile = control_profile(project)
    facts = inspect_project(project)
    skill_slug = slug(str(profile.get("name") or facts.get("project_name") or project.name))
    project_type = facts.get("project_type")
    if profile.get("kind") == "skill" and (not project_type or project_type == "unknown"):
        project_type = "skill-repo"
    engineering_slug = slug(str(project_type or profile.get("kind") or "general-engineering"))
    return skill_slug, engineering_slug


def evolution_markdown(topic: dict[str, str], versions: list[dict[str, str]], family: str, target_slug: str) -> str:
    sources = "\n".join(f"- `{item['path']}`" for item in versions) or "- No source versions available."
    lessons: list[str] = []
    for item in versions:
        text = item["content"]
        match = re.search(r"## Iterated Lessons\s*(.*?)(?:\n## |\Z)", text, flags=re.DOTALL)
        lesson = match.group(1).strip() if match else text.strip()
        if lesson:
            lessons.append(lesson)
    body = "\n\n".join(lessons) if lessons else "- No reusable lesson content available."
    return "\n".join([
        f"# {topic['title']} Evolution Template",
        "",
        f"- Template family: {family}",
        f"- Target type: {target_slug}",
        f"- Source file: {topic['filename']}",
        f"- Version window: current-plus-latest-history",
        "",
        "## Source Versions",
        sources,
        "",
        "## Reusable Lessons",
        body,
        "",
    ])


def run_evolution(project: Path, force: bool = False) -> dict[str, Any]:
    state = load_state(project)
    count = int(state.get("handoff_count", 0))
    last = int(state.get("last_evolution_at", 0))
    if not force and (count < 10 or count % 10 != 0 or last == count):
        return {"project": str(project), "skipped": True, "handoff_count": count, "last_evolution_at": last}
    quality_errors = validate_current_experience_quality(project)
    if quality_errors:
        return {"project": str(project), "skipped": True, "errors": quality_errors, "reason": "experience quality gate failed"}
    root = evolution_template_root(project)
    skill_slug, engineering_slug = evolution_slugs(project)
    targets = [
        ("skill-template", skill_slug, root / "skill-template" / skill_slug),
        ("engineering-template", engineering_slug, root / "engineering-template" / engineering_slug),
    ]
    root.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    index_entries: list[dict[str, Any]] = []
    core_specs = experience_file_specs(project)[:4]
    for family, target_slug, target_dir in targets:
        target_dir.mkdir(parents=True, exist_ok=True)
        template_index: list[dict[str, Any]] = []
        for topic in core_specs:
            versions = source_versions_for(project, topic["filename"])
            output = target_dir / topic["filename"]
            output.write_text(evolution_markdown(topic, versions, family, target_slug), encoding="utf-8")
            rel_output = output.relative_to(project).as_posix()
            written.append(rel_output)
            source_paths = [item["path"] for item in versions]
            row = {
                "family": family,
                "target_type": target_slug,
                "topic": topic["filename"],
                "output": rel_output,
                "source_versions": source_paths,
                "sha256": file_hash(output),
            }
            template_index.append(row)
            index_entries.append(row)
        index_path = target_dir / "template-index.json"
        index_path.write_text(json.dumps({"schema_version": 1, "templates": template_index}, indent=2, sort_keys=True), encoding="utf-8")
        written.append(index_path.relative_to(project).as_posix())
    index = {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "handoff_count": count,
        "cadence_handoffs": 10,
        "version_window": "current-plus-latest-history",
        "templates": index_entries,
    }
    index_path = root / "evolution-index.json"
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    written.append(index_path.relative_to(project).as_posix())
    state["last_evolution_at"] = count
    save_state(project, state)
    return {"project": str(project), "written": written, "handoff_count": count, "index": str(index_path)}


def apply_experience_payload(project: Path, payload_path: str) -> dict[str, Any]:
    scaffold(project)
    payload = read_input(payload_path)
    entries, errors = validate_experience_payload(project, payload)
    if errors:
        return {"project": str(project), "errors": errors}
    archived = archive_experience_files(project)
    written: list[str] = []
    for spec in experience_file_specs(project):
        target = project / "docs" / "experience" / spec["filename"]
        target.write_text(entries[spec["filename"]].rstrip() + "\n", encoding="utf-8")
        written.append(str(target))
    state = load_state(project)
    count = int(state.get("handoff_count", 0))
    state["last_experience_at"] = count
    state["experience_update_required"] = False
    payload_resolved = Path(payload_path).resolve()
    try:
        state["last_experience_payload"] = payload_resolved.relative_to(project).as_posix()
    except ValueError:
        state["last_experience_payload"] = payload_resolved.name
    save_state(project, state)
    result: dict[str, Any] = {"project": str(project), "written": written, "archived": archived, "handoff_count": count}
    if count >= 10 and count % 10 == 0:
        result["evolution"] = run_evolution(project)
    return result


def write_experience(project: Path, force: bool = False, payload_path: str | None = None) -> dict[str, Any]:
    if payload_path:
        return apply_experience_payload(project, payload_path)
    scaffold(project)
    state = load_state(project)
    count = int(state.get("handoff_count", 0))
    last = int(state.get("last_experience_at", 0))
    if not force and count - last < 5:
        return {"project": str(project), "skipped": True, "handoff_count": count, "last_experience_at": last}
    return write_experience_request(project, count)


def validate_current_experience_quality(project: Path) -> list[str]:
    state = load_state(project)
    errors: list[str] = []
    if state.get("experience_update_required"):
        errors.append("experience update requires AI-generated payload before it can be considered current")
    entries = current_experience_files(project)
    expected = [spec["filename"] for spec in experience_file_specs(project)]
    for filename in expected:
        content = entries.get(filename, "")
        if not content:
            continue
        if "Awaiting AI experience summary" in content or "Iterate this file from completed handoffs" in content:
            errors.append(f"{filename}: contains placeholder experience text")
        if "## Original Plan And Steps" in content and "## Verification Evidence" in content:
            errors.append(f"{filename}: must not copy full HANDOFF.md sections")
    for index, left_name in enumerate(expected):
        for right_name in expected[index + 1:]:
            left = entries.get(left_name, "")
            right = entries.get(right_name, "")
            if left and right and similarity(left, right) > 0.86:
                errors.append(f"{left_name} and {right_name}: experience files are too similar")
    return errors


def write_development(project: Path, stage: str, input_path: str | None) -> dict[str, Any]:
    scaffold(project)
    data = read_input(input_path)
    target = project / "docs" / "development" / f"{stamp()}-{slug(stage)}.md"
    target.write_text(
        "\n".join([
            f"# Development Stage: {stage}",
            "",
            f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
            f"- Version: {data.get('version', 'not recorded')}",
            "",
            "## Goal",
            list_lines(data.get("goal")),
            "",
            "## Completed Scope",
            list_lines(data.get("completed_scope")),
            "",
            "## Verification",
            list_lines(data.get("verification")),
            "",
            "## Artifacts",
            list_lines(data.get("artifacts")),
            "",
            "## Remaining Risks",
            list_lines(data.get("remaining_risks")),
            "",
        ]),
        encoding="utf-8",
    )
    return {"project": str(project), "written": str(target)}


def verify_docs(project: Path) -> dict[str, Any]:
    errors: list[str] = []
    checked: list[str] = []
    for rel_path in DOC_DIRS:
        checked.append(rel_path)
        if not (project / rel_path).is_dir():
            errors.append(f"missing docs governance directory: {rel_path}")
    for rel_path in REQUIRED_DOC_FILES:
        checked.append(rel_path)
        if not (project / rel_path).is_file():
            errors.append(f"missing docs governance file: {rel_path}")
    handoff = project / "docs" / "handoff" / "HANDOFF.md"
    if handoff.exists():
        text = handoff.read_text(encoding="utf-8", errors="ignore")
        for section in HANDOFF_SECTIONS:
            if f"## {section}" not in text:
                errors.append(f"docs/handoff/HANDOFF.md: missing section ## {section}")
    expected_experience = [spec["filename"] for spec in experience_file_specs(project)]
    for filename in expected_experience:
        checked.append(f"docs/experience/{filename}")
        if not (project / "docs" / "experience" / filename).is_file():
            errors.append(f"missing experience file: docs/experience/{filename}")
    actual_numbered = sorted((project / "docs" / "experience").glob("[0-9]*-*.md")) if (project / "docs" / "experience").is_dir() else []
    if len(actual_numbered) != 10:
        errors.append("docs/experience: expected exactly 10 numbered experience files")
    state = load_state(project)
    if int(state.get("handoff_count", 0)) >= 5:
        errors.extend(f"docs/experience: {item}" for item in validate_current_experience_quality(project))
    dir_result = verify_dir_manager(project)
    checked.extend(dir_result["checked"])
    errors.extend(dir_result["errors"])
    return {"project": str(project), "checked": checked, "errors": errors}


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage AGENTS.md docs governance artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold_parser = subparsers.add_parser("scaffold")
    scaffold_parser.add_argument("project", nargs="?", default=".")

    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("project", nargs="?", default=".")

    handoff_parser = subparsers.add_parser("handoff")
    handoff_parser.add_argument("project", nargs="?", default=".")
    handoff_parser.add_argument("--input", default=None)

    start_session_parser = subparsers.add_parser("start-session")
    start_session_parser.add_argument("project", nargs="?", default=".")
    start_session_parser.add_argument("--input", default=None)

    resume_check_parser = subparsers.add_parser("resume-check")
    resume_check_parser.add_argument("project", nargs="?", default=".")
    resume_check_parser.add_argument("--conversation-log", default=None)

    resume_repair_parser = subparsers.add_parser("resume-repair")
    resume_repair_parser.add_argument("project", nargs="?", default=".")
    resume_repair_parser.add_argument("--input", default=None)

    experience_parser = subparsers.add_parser("experience")
    experience_parser.add_argument("project", nargs="?", default=".")
    experience_parser.add_argument("--force", action="store_true")
    experience_parser.add_argument("--payload", default=None)

    evolve_parser = subparsers.add_parser("evolve")
    evolve_parser.add_argument("project", nargs="?", default=".")
    evolve_parser.add_argument("--force", action="store_true")

    development_parser = subparsers.add_parser("development")
    development_parser.add_argument("project", nargs="?", default=".")
    development_parser.add_argument("--stage", required=True)
    development_parser.add_argument("--input", default=None)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("project", nargs="?", default=".")

    args = parser.parse_args()
    project = resolve_project(args.project)
    if args.command == "scaffold":
        emit_json(scaffold(project))
    elif args.command == "preflight":
        emit_json(preflight_docs(project))
    elif args.command == "handoff":
        emit_json(write_handoff(project, args.input))
    elif args.command == "start-session":
        emit_json(write_active_session(project, args.input))
    elif args.command == "resume-check":
        emit_json(resume_check(project, args.conversation_log))
    elif args.command == "resume-repair":
        emit_json(resume_repair(project, args.input))
    elif args.command == "experience":
        result = write_experience(project, force=args.force, payload_path=args.payload)
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "evolve":
        result = run_evolution(project, force=args.force)
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "development":
        emit_json(write_development(project, args.stage, args.input))
    elif args.command == "verify":
        result = verify_docs(project)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
