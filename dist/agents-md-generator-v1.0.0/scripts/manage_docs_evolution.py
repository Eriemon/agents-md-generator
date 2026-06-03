from __future__ import annotations

from pathlib import Path

from manage_docs_shared import *
from manage_docs_experience import (
    archive_experience_files,
    current_experience_files,
    similarity,
    unsupported_evolution_payload_fields,
    validate_experience_content,
    validate_experience_payload,
    write_experience_request,
)


def validate_current_experience_quality(
    project: Path,
    *,
    include_evolution_cadence: bool = True,
    allow_legacy_target_repair: bool = False,
) -> list[str]:
    del include_evolution_cadence
    del allow_legacy_target_repair
    state = load_state(project)
    errors: list[str] = []
    count = int(state.get("handoff_count", 0))
    experience_due = latest_experience_due(count)
    last_experience = int(state.get("last_experience_at", 0))
    if experience_due and last_experience < experience_due:
        errors.append(f"cadence requires an applied AI experience update at handoff {experience_due}")
    if state.get("experience_update_required") and experience_due:
        errors.append("experience update requires AI-generated payload before it can be considered current")
    entries = current_experience_files(project)
    expected = [spec["filename"] for spec in experience_file_specs(project)]
    for filename in expected:
        content = entries.get(filename, "")
        if not content:
            continue
        errors.extend(validate_experience_content(filename, content))
    for index, left_name in enumerate(expected):
        for right_name in expected[index + 1:]:
            left = entries.get(left_name, "")
            right = entries.get(right_name, "")
            if left and right and similarity(left, right) > 0.86:
                errors.append(f"{left_name} and {right_name}: experience files are too similar")
    return errors


def apply_experience_payload(project: Path, payload_path: str) -> dict[str, Any]:
    from manage_docs_scaffold_session import read_input, scaffold

    scaffold(project)
    state = load_state(project)
    cleanup = cleanup_legacy_evolution_artifacts(project, state)
    count = int(state.get("handoff_count", 0))
    checkpoint = latest_experience_due(count) or count
    payload = read_input(payload_path)
    entries, errors = validate_experience_payload(project, payload)
    legacy_fields = unsupported_evolution_payload_fields(payload)
    if legacy_fields:
        errors.append("v1.0.0 no longer supports evolution payload fields: " + ", ".join(legacy_fields))
    if errors:
        return {"project": str(project), "errors": errors}

    archived = archive_experience_files(project)
    written: list[str] = []
    for spec in experience_file_specs(project):
        experience_file = project / "docs" / "experience" / spec["filename"]
        experience_file.write_text(with_experience_metadata(project, entries[spec["filename"]], checkpoint), encoding="utf-8")
        written.append(str(experience_file))

    state["last_experience_at"] = checkpoint
    state["experience_update_required"] = False
    state.pop("experience_request_due_at", None)
    payload_resolved = Path(payload_path).resolve()
    try:
        state["last_experience_payload"] = payload_resolved.relative_to(project).as_posix()
    except ValueError:
        state["last_experience_payload"] = payload_resolved.name
    request_path = experience_request_file(project)
    if request_path.exists():
        request_path.unlink()
    cleanup_legacy_evolution_artifacts(project, state)
    save_state(project, state)
    return {
        "project": str(project),
        "written": written,
        "archived": archived,
        "handoff_count": checkpoint,
        "cleanup": cleanup,
    }


def write_experience(project: Path, force: bool = False, payload_path: str | None = None) -> dict[str, Any]:
    from manage_docs_scaffold_session import scaffold

    if payload_path:
        return apply_experience_payload(project, payload_path)
    scaffold(project)
    state = load_state(project)
    cleanup = cleanup_legacy_evolution_artifacts(project, state)
    count = int(state.get("handoff_count", 0))
    checkpoint = latest_experience_due(count)
    last = int(state.get("last_experience_at", 0))
    if not force and (checkpoint == 0 or last >= checkpoint):
        return {"project": str(project), "skipped": True, "handoff_count": count, "last_experience_at": last, "cleanup": cleanup}
    result = write_experience_request(project, checkpoint or count)
    result["cleanup"] = cleanup
    return result
