
from __future__ import annotations

from manage_docs_shared import *


def sync_root_agents(project: Path, write: bool = False, installed_skill_dir_override: str | Path | None = None) -> dict[str, Any]:
    agents_path = project / "AGENTS.md"
    profile = project_profile(project)
    if write and profile:
        ensure_global_rule_overrides_file(project, profile)
    repair_command = root_agents_sync_command(project, profile, installed_skill_dir_override)
    if not agents_path.exists():
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

    expected_version, version_source = preferred_skill_version(override_dir=installed_skill_dir_override)
    if not expected_version:
        return {
            "project": str(project),
            "agents_path": str(agents_path),
            "expected_version": "",
            "version_source": version_source,
            "sync_required": False,
            "updated": False,
            "reasons": [],
            "errors": ["agents-md-generator version is unavailable; cannot sync root AGENTS metadata"],
            "repair_command": repair_command,
        }

    text = agents_path.read_text(encoding="utf-8", errors="ignore")
    metadata = parse_agents_metadata(text)
    last_updated_match = LAST_UPDATED_HEADER_RE.search(text)
    last_updated_raw = last_updated_match.group(1).strip() if last_updated_match else ""
    last_verified = last_updated_match.group(2).strip() if last_updated_match else "never"
    default_language = metadata.get("default_language", "中文").strip() or "中文"

    reasons: list[str] = []
    if not last_updated_match:
        reasons.append("missing_last_updated_header")
    elif "T" not in last_updated_raw:
        reasons.append("legacy_last_updated_format")
    if not metadata.get("agents_version"):
        reasons.append("missing_agents_version")
    elif metadata.get("agents_version") != expected_version:
        reasons.append("agents_version_mismatch")
    if not metadata.get("generator_version"):
        reasons.append("missing_generator_version")
    elif metadata.get("generator_version") != expected_version:
        reasons.append("generator_version_mismatch")
    if not metadata.get("default_language"):
        reasons.append("missing_default_language")

    sync_required = bool(reasons)
    updated = False
    synced_text = text

    if write and sync_required:
        new_last_updated = current_timestamp()
        new_last_line = f"<!-- Last updated: {new_last_updated} | Last verified: {last_verified} -->"
        new_metadata_line = (
            f"<!-- AGENTS-METADATA: agents_version={expected_version}; "
            f"generator_version={expected_version}; default_language={default_language} -->"
        )
        lines = text.splitlines()
        rewritten: list[str] = []
        last_inserted = False
        metadata_inserted = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("<!-- Last updated:"):
                if not last_inserted:
                    rewritten.append(new_last_line)
                    last_inserted = True
                continue
            if stripped.startswith("<!-- AGENTS-METADATA:"):
                if not metadata_inserted:
                    rewritten.append(new_metadata_line)
                    metadata_inserted = True
                continue
            rewritten.append(line)
        if not last_inserted or not metadata_inserted:
            insert_at = 0
            while insert_at < len(rewritten) and rewritten[insert_at].startswith("<!--"):
                insert_at += 1
            missing_lines: list[str] = []
            if not last_inserted:
                missing_lines.append(new_last_line)
            if not metadata_inserted:
                missing_lines.append(new_metadata_line)
            rewritten[insert_at:insert_at] = missing_lines
        synced_text = "\n".join(rewritten).rstrip() + "\n"
        if synced_text != text:
            agents_path.write_text(synced_text, encoding="utf-8")
            updated = True

    refreshed_match = LAST_UPDATED_HEADER_RE.search(synced_text)
    refreshed_raw = refreshed_match.group(1).strip() if refreshed_match else last_updated_raw

    return {
        "project": str(project),
        "agents_path": str(agents_path),
        "expected_version": expected_version,
        "version_source": version_source,
        "default_language": default_language,
        "last_updated_raw": refreshed_raw,
        "sync_required": sync_required,
        "updated": updated,
        "reasons": reasons,
        "errors": [],
        "repair_command": repair_command,
    }

def replace_global_codex_block(text: str, rendered: str) -> str:
    current = text
    start = current.find(GLOBAL_CODEX_AGENTS_BLOCK_START)
    end = current.find(GLOBAL_CODEX_AGENTS_BLOCK_END)
    if start == -1 or end == -1 or end < start:
        return current
    search_end = start
    while True:
        preamble_start = current.rfind(GLOBAL_CODEX_AGENTS_PREAMBLE, 0, search_end)
        if preamble_start == -1:
            break
        between = current[preamble_start + len(GLOBAL_CODEX_AGENTS_PREAMBLE) : start]
        if between.strip():
            break
        start = preamble_start
        search_end = preamble_start
    end += len(GLOBAL_CODEX_AGENTS_BLOCK_END)
    return (current[:start] + rendered + current[end:]).rstrip() + "\n"

def sync_global_codex_agents(project: Path, write: bool = False, codex_home: str | None = None) -> dict[str, Any]:
    target = global_codex_agents_path(codex_home)
    profile = project_profile(project)
    status = global_codex_agents_status(codex_home, project_root=project, profile=profile)
    repair_command = global_codex_agents_sync_command(project, profile)
    result = {
        "project": str(project),
        "target_path": str(target),
        "updated": False,
        "write_requested": write,
        "requires_user_confirmation": status["requires_user_confirmation"],
        "user_message": status["user_message"],
        "repair_command": repair_command,
        **status,
    }
    if not write:
        return result
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not target.is_file():
        return {**result, "errors": [f"global Codex AGENTS target is not a file: {target}"]}
    rendered = render_global_codex_agents_template()
    current = target.read_text(encoding="utf-8", errors="ignore") if target.is_file() else ""
    if not target.exists() or status["empty"]:
        new_text = rendered
    elif status["managed"]:
        new_text = replace_global_codex_block(current, rendered)
    else:
        return result
    if new_text != current:
        target.write_text(new_text, encoding="utf-8")
        result["updated"] = True
    refreshed = global_codex_agents_status(codex_home, project_root=project, profile=profile)
    result.update(refreshed)
    result["repair_command"] = repair_command
    return result

def verify_docs(project: Path) -> dict[str, Any]:
    from manage_docs_evolution import validate_current_experience_quality

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
    development_current = project / "docs" / "development" / "DEVELOPMENT.md"
    if development_current.exists():
        errors.extend(validate_development_record(development_current))
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
    for legacy in [project / "HANDOFF.md", project / "DEVELOPMENT.md", project / "experience", project / "docs" / "HANDOFF.md", project / "docs" / "DEVELOPMENT.md"]:
        if legacy.exists():
            try:
                errors.append(f"legacy docs path must be migrated into governed docs layout: {legacy.relative_to(project).as_posix()}")
            except ValueError:
                errors.append(f"legacy docs path must be migrated into governed docs layout: {legacy}")
    return {"project": str(project), "checked": checked, "errors": errors}
