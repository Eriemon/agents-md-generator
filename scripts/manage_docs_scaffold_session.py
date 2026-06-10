
from __future__ import annotations

from manage_docs_shared import *
from manage_docs_sync_verify import verify_docs
from manage_dirs import CURRENT_STRUCTURE, DIR_MANAGER_MD, PLANNED_STRUCTURE

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

def rotate_current_development_if_needed(project: Path) -> str:
    target = project / "docs" / "development" / "DEVELOPMENT.md"
    if not target.exists():
        return ""
    text = target.read_text(encoding="utf-8", errors="ignore")
    if "- Version: not recorded" in text and "- Status: not recorded" in text:
        return ""
    history_dir = project / "docs" / "development" / "history_development" / stamp()
    history_dir.mkdir(parents=True, exist_ok=True)
    archived_target = history_dir / "DEVELOPMENT.md"
    shutil.move(str(target), str(archived_target))
    return archived_target.relative_to(project).as_posix()

def migrate_legacy_docs(project: Path) -> list[str]:
    migrated: list[str] = []
    docs_root = project / "docs"

    legacy_handoffs = [project / "HANDOFF.md", docs_root / "HANDOFF.md"]
    handoff_target = project / "docs" / "handoff" / "HANDOFF.md"
    for legacy in legacy_handoffs:
        if legacy.exists() and legacy.is_file():
            if handoff_target.exists():
                rotate_handoff(project)
            handoff_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(legacy), str(handoff_target))
            migrated.append(handoff_target.relative_to(project).as_posix())
            break

    legacy_developments = [project / "DEVELOPMENT.md", docs_root / "DEVELOPMENT.md"]
    development_target = project / "docs" / "development" / "DEVELOPMENT.md"
    for legacy in legacy_developments:
        if legacy.exists() and legacy.is_file():
            if development_target.exists():
                rotate_current_development_if_needed(project)
            development_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(legacy), str(development_target))
            migrated.append(development_target.relative_to(project).as_posix())
            break

    legacy_experience = project / "experience"
    if legacy_experience.exists() and legacy_experience.is_dir():
        current_experience_root = project / "docs" / "experience"
        has_current_experience = any(current_experience_root.glob("[0-9]*-*.md"))
        if has_current_experience:
            archive_experience_files(project)
        current_experience_root.mkdir(parents=True, exist_ok=True)
        for legacy_file in sorted(legacy_experience.rglob("*.md")):
            target = current_experience_root / legacy_file.name
            if target.exists():
                target = current_experience_root / f"legacy-{legacy_file.name}"
            shutil.move(str(legacy_file), str(target))
            migrated.append(target.relative_to(project).as_posix())
        shutil.rmtree(legacy_experience)
    return migrated

def scaffold(project: Path, refresh_existing_state: bool = True) -> dict[str, Any]:
    from manage_docs_memory import init_memory, memory_enabled

    created: list[str] = []
    profile = project_profile(project)
    for rel_path in DOC_DIRS:
        path = project / rel_path
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(rel_path)
    migrated = migrate_legacy_docs(project)
    handoff_naming = audit_handoff_naming(project)
    files = {
        "docs/handoff/HANDOFF.md": default_handoff(),
        "docs/development/DEVELOPMENT.md": default_development_record(),
        "docs/install_configuration/INSTALL_CONFIGURATION.md": install_configuration_doc(),
        "docs/git_manager/GIT_MANAGER.md": git_manager_doc(project, profile),
        "docs/git_manager/CHANGELOG.md": default_git_changelog(),
    }
    for rel_path, content in files.items():
        if rel_path == "docs/handoff/HANDOFF.md" and handoff_naming["blocking"]:
            continue
        path = project / rel_path
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(rel_path)
    state = load_state(project)
    state_missing = not (project / STATE_PATH).exists()
    state.setdefault("handoff_count", 0)
    state.setdefault("last_experience_at", 0)
    cleanup = cleanup_legacy_evolution_artifacts(project, state)
    should_refresh_dir_manager = refresh_existing_state or any(
        not (project / rel).exists()
        for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]
    )
    if should_refresh_dir_manager:
        state["dir_manager_last_scan"] = datetime.now().isoformat(timespec="seconds")
        save_state(project, state)
        dir_result = init_dir_manager(project)
        created.extend(path for path in dir_result.get("written", []) if path not in created)
    elif state_missing:
        save_state(project, state)
    created.extend(path for path in ensure_experience_files(project) if path not in created)
    memory_result = None
    errors = list(handoff_naming["errors"])
    if memory_enabled(project):
        memory_result = init_memory(project)
        created.extend(path for path in memory_result.get("created", []) if path not in created)
        errors.extend(f"memory: {item}" for item in memory_result.get("errors", []))
    return {
        "project": str(project),
        "created": created,
        "migrated": migrated,
        "state": state,
        "cleanup": cleanup,
        "memory": memory_result,
        "handoff_naming": handoff_naming,
        "errors": errors,
    }

def read_input(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    data = read_json(Path(path).resolve())
    if not isinstance(data, dict):
        raise SystemExit(f"Input must be a JSON object: {path}")
    return data

def rotate_handoff(project: Path) -> str | None:
    paths = handoff_paths(project)
    current = paths["current"]
    if not current.exists():
        return None
    history = paths["history"]
    history.mkdir(parents=True, exist_ok=True)
    target = unique_handoff_history_path(history, datetime.now())
    shutil.move(str(current), str(target))
    return target.relative_to(project).as_posix()

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
    from manage_docs_evolution import write_experience
    from manage_docs_memory import write_handoff_memory

    scaffold_result = scaffold(project)
    if scaffold_result.get("errors"):
        return {
            "project": str(project),
            "errors": scaffold_result["errors"],
            "handoff_naming": scaffold_result.get("handoff_naming", {}),
        }
    archived = rotate_handoff(project)
    state = load_state(project)
    cleanup_legacy_evolution_artifacts(project, state)
    count = int(state.get("handoff_count", 0)) + 1
    data = read_input(input_path)
    target = handoff_paths(project)["current"]
    target.write_text(handoff_markdown(data, count), encoding="utf-8")
    snapshot = maybe_write_conversation_snapshot(project, data, count)
    state["handoff_count"] = count
    save_state(project, state)
    active = active_session_file(project)
    if active.exists():
        active.unlink()
    result = {"project": str(project), "written": str(target), "archived": archived, "handoff_count": count}
    memory_result = write_handoff_memory(project, data, count, target)
    if memory_result is not None:
        result["memory"] = memory_result
        if memory_result.get("errors"):
            result["errors"] = [f"memory: {item}" for item in memory_result["errors"]]
    if snapshot:
        result["conversation_snapshot"] = snapshot
    if count % 5 == 0:
        result["experience"] = write_experience(project, force=True)
    return result

def write_active_session(project: Path, input_path: str | None) -> dict[str, Any]:
    from manage_docs_memory import memory_read_recommendation

    # Starting a session in an already-governed repository should not rewrite
    # tracked dir-manager baselines or docs-governance timestamps.
    scaffold_result = scaffold(project, refresh_existing_state=False)
    if scaffold_result.get("errors"):
        return {
            "project": str(project),
            "errors": scaffold_result["errors"],
            "blocking": True,
            "handoff_naming": scaffold_result.get("handoff_naming", {}),
        }
    data = read_input(input_path)
    cleanup = cleanup_legacy_evolution_artifacts(project)
    handoff = handoff_paths(project)["current"]
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
    result = {"project": str(project), "written": str(active_session_file(project)), "active_session": active, "cleanup": cleanup}
    recommendation = memory_read_recommendation(project, str(active.get("task", "current task")))
    if recommendation:
        result["memory_read_recommendation"] = recommendation
    return result

def read_active_session(project: Path) -> dict[str, Any]:
    active = read_json(active_session_file(project))
    return active if isinstance(active, dict) else {}

def resume_check(project: Path, conversation_log: str | None = None) -> dict[str, Any]:
    from manage_docs_memory import memory_read_recommendation

    naming = audit_handoff_naming(project)
    if naming["blocking"]:
        result = {
            "project": str(project),
            "status": "blocked",
            "interrupted": False,
            "blocking": True,
            "reasons": naming["errors"],
            "handoff_naming": naming,
        }
        recommendation = memory_read_recommendation(project, "resume current task")
        if recommendation:
            result["memory_read_recommendation"] = recommendation
        return result
    active = read_active_session(project)
    if not active:
        result = {
            "project": str(project),
            "status": "clean",
            "interrupted": False,
            "blocking": False,
            "reasons": ["no active session found"],
        }
        recommendation = memory_read_recommendation(project, "current task")
        if recommendation:
            result["memory_read_recommendation"] = recommendation
        return result
    handoff = handoff_paths(project)["current"]
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

    result = {
        "project": str(project),
        "status": "interrupted" if interrupted else "clean",
        "interrupted": interrupted,
        "blocking": False,
        "active_session": active,
        "current_handoff_hash": current_hash,
        "reasons": reasons,
    }
    recommendation = memory_read_recommendation(project, str(active.get("task", "resume current task")))
    if recommendation:
        result["memory_read_recommendation"] = recommendation
    return result

def resume_repair(project: Path, input_path: str | None) -> dict[str, Any]:
    check = resume_check(project)
    if check.get("blocking"):
        return {
            "project": str(project),
            "skipped": True,
            "interrupted": False,
            "blocking": True,
            "errors": check["reasons"],
            "resume_check": check,
        }
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

def repair_handoff_names(project: Path, write: bool = False) -> dict[str, Any]:
    paths = handoff_paths(project)
    handoff_root = paths["root"]
    history_dir = paths["history"]
    current_path = paths["current"]
    renamed: list[dict[str, str]] = []
    skipped: list[str] = []
    errors: list[str] = []

    handoff_root.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)

    current_candidates = [
        path for path in sorted(handoff_root.iterdir())
        if path.is_file() and path.suffix.lower() == ".md" and path.name != HANDOFF_CURRENT_FILENAME
    ] if handoff_root.is_dir() else []
    extra_current = [
        path.relative_to(project).as_posix()
        for path in sorted(handoff_root.iterdir())
        if path.name not in {HANDOFF_CURRENT_FILENAME, HANDOFF_HISTORY_DIRNAME} and not (path.is_file() and path.suffix.lower() == ".md")
    ] if handoff_root.is_dir() else []
    if extra_current:
        errors.extend(
            f"cannot repair handoff naming automatically because docs/handoff contains non-governed entries: {item}"
            for item in extra_current
        )
    if current_path.exists():
        if current_candidates:
            errors.append("cannot repair handoff naming automatically because docs/handoff contains HANDOFF.md plus additional markdown candidates")
    elif len(current_candidates) == 1:
        source = current_candidates[0]
        if write:
            source.rename(current_path)
        renamed.append({"from": source.relative_to(project).as_posix(), "to": current_path.relative_to(project).as_posix()})
    elif len(current_candidates) > 1:
        errors.append("cannot repair handoff naming automatically because docs/handoff contains multiple markdown candidates")
    else:
        skipped.append("no current handoff rename candidate found")

    for path in sorted(history_dir.iterdir()) if history_dir.is_dir() else []:
        rel_path = path.relative_to(project).as_posix()
        if not path.is_file():
            errors.append(f"cannot repair history handoff naming automatically because a non-file entry exists: {rel_path}")
            continue
        if HANDOFF_HISTORY_RE.fullmatch(path.name):
            continue
        if path.suffix.lower() != ".md":
            errors.append(f"cannot repair history handoff naming automatically because a non-markdown file exists: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not looks_like_handoff_markdown(text):
            errors.append(f"cannot repair history handoff naming automatically because file does not look like a handoff: {rel_path}")
            continue
        generated_at = parse_handoff_generated_at(text)
        moment = generated_at or datetime.fromtimestamp(path.stat().st_mtime)
        target = unique_handoff_history_path(history_dir, moment)
        if target == path:
            skipped.append(rel_path)
            continue
        if write:
            path.rename(target)
        renamed.append({"from": rel_path, "to": target.relative_to(project).as_posix()})

    naming = audit_handoff_naming(project)
    return {
        "project": str(project),
        "write_requested": write,
        "renamed": renamed,
        "skipped": skipped,
        "errors": errors,
        "blocking": bool(errors) or naming["blocking"],
        "handoff_naming": naming,
    }

def write_development(project: Path, stage: str, input_path: str | None) -> dict[str, Any]:
    scaffold(project)
    data = read_input(input_path)
    target = project / "docs" / "development" / "DEVELOPMENT.md"
    archived = ""
    if target.exists():
        text = target.read_text(encoding="utf-8", errors="ignore")
        if "- Version: not recorded" not in text or "- Status: not recorded" not in text:
            history_dir = project / "docs" / "development" / "history_development" / stamp()
            history_dir.mkdir(parents=True, exist_ok=True)
            archived_target = history_dir / "DEVELOPMENT.md"
            shutil.move(str(target), str(archived_target))
            archived = archived_target.relative_to(project).as_posix()
    target.write_text(
        "\n".join([
            f"# Development Stage: {stage}",
            "",
            f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
            f"- Version: {data.get('version', 'not recorded')}",
            f"- Status: {data.get('current_status', 'not recorded')}",
            "",
            "## Development Goal",
            list_lines(data.get("goal")),
            "",
            "## Full Development Plan",
            list_lines(data.get("full_plan")),
            "",
            "## Current Progress",
            list_lines(data.get("current_status")),
            "",
            "## Completed Scope",
            list_lines(data.get("completed_scope")),
            "",
            "## Remaining Scope",
            list_lines(data.get("remaining_scope")),
            "",
            "## Key Problems And Risks",
            list_lines(data.get("remaining_risks") or data.get("problems")),
            "",
            "## Resolution Strategy And Next Steps",
            list_lines(data.get("next_steps") or data.get("next")),
            "",
            "## Development Result",
            list_lines(data.get("results")),
            "",
            "## Verification",
            list_lines(data.get("verification")),
            "",
            "## Artifacts And Impact",
            list_lines(data.get("artifacts")),
            "",
        ]),
        encoding="utf-8",
    )
    return {"project": str(project), "written": str(target), "archived": archived}

def changelog_markdown(data: dict[str, Any]) -> str:
    return "\n".join([
        "# Change Log",
        "",
        f"- Version: {data.get('version', 'not recorded')}",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Summary: {data.get('summary', 'not recorded')}",
        "",
        "## Changes",
        list_lines(data.get("changes")),
        "",
        "## Verification",
        list_lines(data.get("verification")),
        "",
    ])

def rotate_git_changelog(project: Path) -> str | None:
    current = git_changelog_file(project)
    if not current.exists():
        return None
    text = current.read_text(encoding="utf-8", errors="ignore")
    if "- Version: not recorded" in text and "- Summary: not recorded" in text:
        return None
    history_dir = git_history_root(project) / stamp()
    history_dir.mkdir(parents=True, exist_ok=True)
    target = history_dir / "CHANGELOG.md"
    shutil.move(str(current), str(target))
    return target.relative_to(project).as_posix()

def write_git_changelog(project: Path, input_path: str | None) -> dict[str, Any]:
    scaffold(project)
    data = read_input(input_path)
    target = git_changelog_file(project)
    archived = rotate_git_changelog(project)
    target.write_text(changelog_markdown(data), encoding="utf-8")
    state = load_state(project)
    state["last_git_changelog_at"] = datetime.now().isoformat(timespec="seconds")
    state["last_git_changelog_version"] = str(data.get("version", "")).strip()
    save_state(project, state)
    return {
        "project": str(project),
        "written": target.relative_to(project).as_posix(),
        "archived": archived or "",
        "version": str(data.get("version", "")).strip(),
    }
