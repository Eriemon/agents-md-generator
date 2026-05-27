
from __future__ import annotations

from manage_docs_shared import *
from manage_docs_experience import (
    archive_experience_files,
    current_experience_files,
    latest_historical_experience,
    missing_markdown_sections,
    payload_entries,
    recent_conversation_context,
    payload_evolution_summary,
    similarity,
    validate_experience_content,
    validate_experience_payload,
    workflow_experience_errors,
    write_experience_request,
)
from manage_docs_evolution_support import (
    evolution_markdown,
    evolution_review_contract,
    exact_cwd_session_inventory,
    infer_evolution_target,
    normalize_evolution_review,
    normalize_evolution_target,
    release_alignment_evidence,
    resolved_state_evolution_target,
    source_versions_for,
    strip_leading_title,
    target_evidence_summary,
    target_identity,
    target_schema_label,
    targets_match,
    validate_evolution_summaries,
    write_evolution_import_request,
    write_evolution_request,
    write_evolution_review_request,
)

EVOLUTION_REVIEW_REQUEST_PATH = ".agents/evolution-review-request.json"
REQUIRED_EVOLUTION_REVIEW_EXPLANATION_FIELDS = [
    "development_flow",
    "design_flow",
    "problem_analysis",
    "classification_rationale",
    "release_alignment",
]
REQUIRED_EVOLUTION_REVIEW_REQUEST_SECTIONS = [
    "development_flow",
    "design_flow",
    "problem_analysis",
    "classification_rationale",
    "release_alignment",
]
ALLOWED_EVOLUTION_REVIEW_VERDICTS = {"approve", "reject", "approve_with_override"}
LEGACY_EVOLUTION_STATE_KEYS = [
    "last_evolution_at",
    "last_evolution_target",
    "last_evolution_summary",
    "last_evolution_review_at",
    "last_evolution_review_verdict",
    "last_evolution_review_target",
    "last_evolution_review_sources",
]

def evolution_owner_enabled(project: Path) -> bool:
    return bool(evolution_owner_status(project).get("enabled"))


def legacy_local_evolution_root(project: Path) -> Path:
    profile = control_profile(project)
    layout = profile.get("skill_layout", {}) if isinstance(profile.get("skill_layout"), dict) else {}
    skill_path = str(layout.get("path") or "skills/agents-md-generator").strip()
    candidate = project / skill_path / "assets" / "templates"
    if candidate.exists() or (project / skill_path).exists():
        return candidate / "evolution"
    return project / "assets" / "templates" / "evolution"


def evolution_template_root(project: Path) -> Path:
    sink = evolution_template_sink(project)
    if sink["mode"] == "export-pending":
        return evolution_export_root(project)
    return Path(str(sink["template_root"])).resolve()


def sink_export_bundle_dir(project: Path, *, bundle_name: str | None = None) -> Path:
    root = evolution_export_root(project)
    name = bundle_name or stamp()
    return root / name


def sink_write_root(project: Path, sink: dict[str, Any], *, bundle_name: str | None = None) -> Path:
    if sink["mode"] == "export-pending":
        return sink_export_bundle_dir(project, bundle_name=bundle_name)
    return Path(str(sink["template_root"])).resolve()


def sink_target_dir(root: Path, target: dict[str, Any]) -> Path:
    target_dir = root / target["family"]
    for segment in target["category_path"]:
        target_dir = target_dir / segment
    return target_dir / target["type_slug"]


def provenance_summary(project: Path, checkpoint: int) -> dict[str, Any]:
    source_project_name = str(control_profile(project).get("name") or inspect_project(project).get("project_name") or project.name)
    source_window = handoff_window(project, checkpoint)
    compact_entries: list[dict[str, Any]] = []
    for row in source_window.get("entries", []):
        if not isinstance(row, dict):
            continue
        compact_entries.append(
            {
                "path": str(row.get("path", "")).replace("\\", "/"),
                "handoff_count": int(row.get("handoff_count", 0)),
            }
        )
    return {
        "source_workspace": f"workspace:{source_project_name}",
        "source_project_name": source_project_name,
        "source_handoff_window": {
            "start_handoff_count": int(source_window.get("start_handoff_count", 0)),
            "end_handoff_count": int(source_window.get("end_handoff_count", 0)),
            "entries": compact_entries,
        },
    }


def public_sink_metadata(project: Path, sink: dict[str, Any], provenance: dict[str, Any]) -> dict[str, Any]:
    project_root = project.resolve()

    def render_path(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        try:
            candidate = Path(text).resolve()
            return candidate.relative_to(project_root).as_posix()
        except ValueError:
            return f"external:{Path(text).name or 'workspace'}"
        except Exception:
            return text.replace("\\", "/")

    return {
        "mode": sink.get("mode", ""),
        "writable": bool(sink.get("writable")),
        "project_root": ".",
        "source_workspace": provenance.get("source_workspace", ""),
        "export_root": str(sink.get("export_root", "")).replace("\\", "/"),
        "import_request_path": str(sink.get("import_request_path", "")).replace("\\", "/"),
        "template_root": render_path(sink.get("template_root", "")),
        "installed_skill_dir": render_path(sink.get("installed_skill_dir", "")),
        "owner_skill_dir": render_path(sink.get("owner_skill_dir", "")),
    }


def remove_empty_parents(path: Path, stop: Path) -> None:
    current = path
    stop_resolved = stop.resolve()
    while current.exists() and current.is_dir() and current.resolve() != stop_resolved:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def cleanup_non_owner_local_evolution(project: Path) -> dict[str, Any]:
    if evolution_owner_enabled(project):
        return {"project": str(project), "cleaned": False, "reason": "evolution owner project"}
    legacy_root = legacy_local_evolution_root(project)
    archived: list[str] = []
    cleaned = False
    if legacy_root.exists():
        archive_base = project / "docs" / "dir_manager" / "history_dir_manager" / stamp() / "legacy-evolution"
        archive_target = archive_base / legacy_root.relative_to(project)
        archive_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(legacy_root), str(archive_target))
        archived.append(archive_target.relative_to(project).as_posix())
        remove_empty_parents(legacy_root.parent, project)
        cleaned = True
    return {
        "project": str(project),
        "cleaned": cleaned,
        "archived": archived,
        "legacy_root": legacy_root.relative_to(project).as_posix(),
        "reason": "legacy local evolution outputs were cleaned before sink-based template export",
    }

def clear_fulfilled_requests(
    project: Path,
    state: dict[str, Any],
    *,
    clear_experience: bool = False,
    clear_evolution: bool = False,
) -> None:
    if clear_experience:
        request = experience_request_file(project)
        if request.exists():
            request.unlink()
        state["experience_update_required"] = False
        state.pop("experience_request_due_at", None)
        state.pop("experience_request", None)
    if clear_evolution:
        request = evolution_request_file(project)
        if request.exists():
            request.unlink()
        review_request = evolution_review_request_file(project)
        if review_request.exists():
            review_request.unlink()
        import_request = evolution_import_request_file(project)
        if import_request.exists():
            import_request.unlink()

def evolution_review_request_file(project: Path) -> Path:
    return project / EVOLUTION_REVIEW_REQUEST_PATH

def review_from_state(project: Path, state: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    verdict = str(state.get("last_evolution_review_verdict", "")).strip()
    target_raw = state.get("last_evolution_review_target")
    if not verdict and target_raw is None:
        return None, ["evolution_review is required before writing reusable templates"]
    errors: list[str] = []
    if verdict not in ALLOWED_EVOLUTION_REVIEW_VERDICTS:
        errors.append("last_evolution_review_verdict must be approve, reject, or approve_with_override")
    target, target_errors = normalize_evolution_target(project, target_raw)
    errors.extend(f"last_evolution_review_target: {item}" for item in target_errors)
    sources = state.get("last_evolution_review_sources")
    if not isinstance(sources, dict):
        errors.append("last_evolution_review_sources must be an object")
        sources = {}
    return {
        "verdict": verdict,
        "approved_target": target,
        "evidence_read": sources,
    }, errors

def resolve_index_output_path(project: Path, root: Path, output_raw: str) -> Path | None:
    output_text = str(output_raw).strip()
    if not output_text:
        return None
    root_candidate = root / output_text
    if root_candidate.exists():
        return root_candidate
    project_candidate = project / output_text
    if project_candidate.exists():
        return project_candidate
    return root_candidate


def archive_obsolete_evolution_outputs(project: Path, root: Path, target_dir: Path) -> list[str]:
    index_path = root / "evolution-index.json"
    index = read_json(index_path)
    templates = index.get("templates", []) if isinstance(index, dict) else []
    if not isinstance(templates, list):
        return []
    archive_root = root / "history_evolution" / stamp()
    archived: list[str] = []
    target_dir_resolved = target_dir.resolve()
    for row in templates:
        if not isinstance(row, dict):
            continue
        output_raw = str(row.get("output", "")).strip()
        if not output_raw:
            continue
        output = resolve_index_output_path(project, root, output_raw)
        if output is None:
            continue
        if not output.exists() or not output.is_file():
            continue
        try:
            output_resolved = output.resolve()
            output_resolved.relative_to(target_dir_resolved)
            continue
        except ValueError:
            pass
        try:
            relative = output.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        archive = archive_root / relative
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(output), str(archive))
        archived.append(archive.relative_to(project).as_posix())
        remove_empty_parents(output.parent, root)
    return archived

def run_evolution(project: Path, force: bool = False) -> dict[str, Any]:
    cleanup = cleanup_non_owner_local_evolution(project)
    state = load_state(project)
    count = int(state.get("handoff_count", 0))
    checkpoint = latest_evolution_due(count)
    last = int(state.get("last_evolution_at", 0))
    if not force and (checkpoint == 0 or last >= checkpoint):
        return {"project": str(project), "skipped": True, "handoff_count": count, "last_evolution_at": last}
    if checkpoint == 0:
        checkpoint = count
    quality_errors = validate_current_experience_quality(
        project,
        include_evolution_cadence=False,
        allow_legacy_target_repair=True,
    )
    if quality_errors:
        return {"project": str(project), "skipped": True, "errors": quality_errors, "reason": "experience quality gate failed"}
    target, repaired_target = resolved_state_evolution_target(project, state.get("last_evolution_target"))
    summaries = state.get("last_evolution_summary")
    if not isinstance(summaries, dict):
        request = write_evolution_request(project, checkpoint, target, "AI-authored evolution_summary is required before writing reusable templates")
        return {
            "project": str(project),
            "skipped": True,
            "errors": ["evolution_summary is required before writing reusable templates"],
            **request,
        }
    summary_map = {str(key): str(value) for key, value in summaries.items()}
    summary_errors = validate_evolution_summaries(project, summary_map, target)
    if summary_errors:
        request = write_evolution_request(project, checkpoint, target, "evolution_summary failed quality validation")
        return {"project": str(project), "skipped": True, "errors": summary_errors, **request}
    review, review_errors = review_from_state(project, state)
    if review_errors:
        request = write_evolution_review_request(project, checkpoint, target, "evolution_review is missing or invalid in docs-governance state")
        return {"project": str(project), "skipped": True, "errors": review_errors, **request}
    assert review is not None
    if review["verdict"] == "reject":
        request = write_evolution_review_request(project, checkpoint, target, "evolution_review rejected the proposed evolution target", review=review)
        return {
            "project": str(project),
            "skipped": True,
            "errors": ["evolution_review rejected the proposed evolution target"],
            **request,
        }
    if repaired_target and review["verdict"] == "approve" and not targets_match(review["approved_target"], target):
        review["approved_target"] = target
    if not targets_match(review["approved_target"], target):
        request = write_evolution_review_request(
            project,
            checkpoint,
            target,
            "evolution_review approved_target differs from persisted evolution target",
            conflicts=["approved_target differs from persisted evolution target"],
            review=review,
        )
        return {
            "project": str(project),
            "skipped": True,
            "errors": ["evolution_review approved_target must match payload evolution_target before writing reusable templates"],
            **request,
        }

    sink = evolution_template_sink(project)
    bundle_name = stamp() if sink["mode"] == "export-pending" else None
    root = sink_write_root(project, sink, bundle_name=bundle_name)
    target_dir = sink_target_dir(root, target)
    root.mkdir(parents=True, exist_ok=True)
    archived = archive_obsolete_evolution_outputs(project, root, target_dir)
    written: list[str] = []
    index_entries: list[dict[str, Any]] = []
    core_specs = experience_file_specs(project)[:4]
    target_dir.mkdir(parents=True, exist_ok=True)
    template_index: list[dict[str, Any]] = []
    provenance = provenance_summary(project, checkpoint)
    public_sink = public_sink_metadata(project, sink, provenance)
    for topic in core_specs:
        versions = source_versions_for(project, topic["filename"])
        output = target_dir / topic["filename"]
        output.write_text(evolution_markdown(topic, versions, target, summary_map[topic["filename"]], provenance), encoding="utf-8")
        rel_output = display_path(output, project)
        written.append(rel_output)
        source_paths = [item["path"] for item in versions]
        row = {
            "family": target["family"],
            "category_path": target["category_path"],
            "target_type": target["type_slug"],
            "topic": topic["filename"],
            "output": output.relative_to(root).as_posix(),
            "source_versions": source_paths,
            "sha256": file_hash(output),
            "review": {
                "verdict": review["verdict"],
                "approved_target": review["approved_target"],
            },
            "provenance": provenance,
        }
        template_index.append(row)
        index_entries.append(row)
    index_path = target_dir / "template-index.json"
    index_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "target": target,
                "review": {
                    "verdict": review["verdict"],
                    "approved_target": review["approved_target"],
                },
                "provenance": provenance,
                "templates": template_index,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    written.append(display_path(index_path, project))
    index = {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "handoff_count": checkpoint,
        "cadence_handoffs": EVOLUTION_CADENCE_HANDOFFS,
        "version_window": "current-plus-latest-history",
        "target": target,
        "sink": public_sink,
        "provenance": provenance,
        "review": {
            "verdict": review["verdict"],
            "approved_target": review["approved_target"],
        },
        "templates": index_entries,
    }
    index_path = root / "evolution-index.json"
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    written.append(display_path(index_path, project))
    import_request: dict[str, Any] = {}
    if sink["mode"] == "export-pending":
        import_request = write_evolution_import_request(project, checkpoint, target, root, sink)
    state["last_evolution_target"] = target
    state["last_evolution_at"] = checkpoint
    state["last_evolution_sink"] = sink
    state["last_evolution_index"] = display_path(index_path, project)
    clear_fulfilled_requests(
        project,
        state,
        clear_experience=bool(latest_experience_due(count)) and int(state.get("last_experience_at", 0)) >= latest_experience_due(count),
        clear_evolution=sink["mode"] != "export-pending",
    )
    save_state(project, state)
    if sink["mode"] == "export-pending":
        request_path = evolution_request_file(project)
        if request_path.exists():
            request_path.unlink()
        review_request_path = evolution_review_request_file(project)
        if review_request_path.exists():
            review_request_path.unlink()
    result = {
        "project": str(project),
        "written": written,
        "archived": archived,
        "handoff_count": checkpoint,
        "index": str(index_path),
        "target": target,
        "repaired_legacy_target": repaired_target,
        "sink": sink,
        "cleanup": cleanup,
    }
    result.update(import_request)
    return result

def apply_experience_payload(project: Path, payload_path: str) -> dict[str, Any]:
    from manage_docs_scaffold_session import read_input, scaffold

    scaffold(project)
    cleanup = cleanup_non_owner_local_evolution(project)
    state = load_state(project)
    count = int(state.get("handoff_count", 0))
    checkpoint = latest_experience_due(count) or count
    requires_atomic_evolution = checkpoint >= EVOLUTION_CADENCE_HANDOFFS and checkpoint % EVOLUTION_CADENCE_HANDOFFS == 0
    payload = read_input(payload_path)
    entries, errors = validate_experience_payload(project, payload)
    evolution_target, target_errors = normalize_evolution_target(project, payload.get("evolution_target") if "evolution_target" in payload else None)
    if requires_atomic_evolution or "evolution_target" in payload:
        errors.extend(target_errors)
    summaries = payload_evolution_summary(payload)
    if requires_atomic_evolution and not summaries:
        errors.append("evolution_summary is required before writing reusable templates")
    if summaries:
        errors.extend(validate_evolution_summaries(project, summaries, evolution_target))
    review_payload = payload.get("evolution_review")
    normalized_review: dict[str, Any] | None = None
    review_errors: list[str] = []
    review_conflicts: list[str] = []
    if requires_atomic_evolution:
        normalized_review, review_errors, review_conflicts = normalize_evolution_review(project, review_payload, evolution_target)
        errors.extend(review_errors)
        if normalized_review and normalized_review.get("verdict") == "reject":
            errors.append("evolution_review rejected the proposed evolution target")
    if errors:
        result: dict[str, Any] = {"project": str(project), "errors": errors}
        if requires_atomic_evolution:
            reason = review_errors[0] if review_errors else "evolution_review blocked reusable template writing"
            assert evolution_target is not None
            result.update(
                write_evolution_review_request(
                    project,
                    checkpoint,
                    evolution_target,
                    reason,
                    conflicts=review_conflicts,
                    review=normalized_review if isinstance(normalized_review, dict) else review_payload if isinstance(review_payload, dict) else None,
                )
            )
        return result
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
    if requires_atomic_evolution or "evolution_target" in payload or summaries:
        state["last_evolution_target"] = evolution_target
        if summaries:
            state["last_evolution_summary"] = summaries
        else:
            state.pop("last_evolution_summary", None)
    else:
        for key in LEGACY_EVOLUTION_STATE_KEYS:
            state.pop(key, None)
    if requires_atomic_evolution and normalized_review:
        state["last_evolution_review_at"] = checkpoint
        state["last_evolution_review_verdict"] = normalized_review["verdict"]
        state["last_evolution_review_target"] = normalized_review["approved_target"]
        state["last_evolution_review_sources"] = normalized_review["evidence_read"]
    save_state(project, state)
    result: dict[str, Any] = {"project": str(project), "written": written, "archived": archived, "handoff_count": checkpoint, "cleanup": cleanup}
    if requires_atomic_evolution:
        result["evolution"] = run_evolution(project)
        if result["evolution"].get("errors"):
            result["errors"] = list(result["evolution"]["errors"])
        else:
            refreshed = load_state(project)
            clear_fulfilled_requests(
                project,
                refreshed,
                clear_experience=True,
                clear_evolution=result["evolution"].get("sink", {}).get("mode") != "export-pending",
            )
            save_state(project, refreshed)
    else:
        clear_fulfilled_requests(project, state, clear_experience=True)
        save_state(project, state)
    return result

def write_experience(project: Path, force: bool = False, payload_path: str | None = None) -> dict[str, Any]:
    from manage_docs_scaffold_session import scaffold

    if payload_path:
        return apply_experience_payload(project, payload_path)
    scaffold(project)
    cleanup = cleanup_non_owner_local_evolution(project)
    state = load_state(project)
    count = int(state.get("handoff_count", 0))
    checkpoint = latest_experience_due(count)
    last = int(state.get("last_experience_at", 0))
    if not force and (checkpoint == 0 or last >= checkpoint):
        return {"project": str(project), "skipped": True, "handoff_count": count, "last_experience_at": last, "cleanup": cleanup}
    result = write_experience_request(project, checkpoint or count)
    result["cleanup"] = cleanup
    return result


def import_evolution(project: Path, bundle_path: str | None = None) -> dict[str, Any]:
    request_path = evolution_import_request_file(project)
    request = read_json(request_path) if request_path.exists() else {}
    bundle_dir = Path(bundle_path).resolve() if bundle_path else project / str(request.get("bundle_dir", "")).strip()
    if not bundle_dir.exists():
        return {
            "project": str(project),
            "skipped": True,
            "errors": [f"evolution bundle does not exist: {bundle_dir}"],
        }
    sink = evolution_template_sink(project)
    if sink["mode"] == "export-pending":
        return {
            "project": str(project),
            "skipped": True,
            "errors": ["installed agents-md-generator skill is unavailable or not writable; cannot import evolution bundle"],
            "sink": sink,
        }
    destination_root = Path(str(sink["template_root"])).resolve()
    destination_root.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for path in sorted(bundle_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(bundle_dir)
        target = destination_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        written.append(display_path(target, project))
    state = load_state(project)
    state["last_evolution_sink"] = sink
    state["last_imported_evolution_bundle"] = display_path(bundle_dir, project)
    save_state(project, state)
    if request_path.exists():
        request_path.unlink()
    return {
        "project": str(project),
        "skipped": False,
        "bundle_dir": display_path(bundle_dir, project),
        "sink": sink,
        "written": written,
    }

def validate_current_experience_quality(
    project: Path,
    *,
    include_evolution_cadence: bool = True,
    allow_legacy_target_repair: bool = False,
) -> list[str]:
    state = load_state(project)
    errors: list[str] = []
    count = int(state.get("handoff_count", 0))
    experience_due = latest_experience_due(count)
    last_experience = int(state.get("last_experience_at", 0))
    if experience_due and last_experience < experience_due:
        errors.append(f"cadence requires an applied AI experience update at handoff {experience_due}")
    if state.get("experience_update_required") and experience_due:
        errors.append("experience update requires AI-generated payload before it can be considered current")
    evolution_due = latest_evolution_due(count)
    if include_evolution_cadence and evolution_due and int(state.get("last_evolution_at", 0)) < evolution_due:
        errors.append(f"cadence requires completed evolution at handoff {evolution_due}")
    target_raw = state.get("last_evolution_target")
    if target_raw is not None:
        if not isinstance(target_raw, dict):
            if not allow_legacy_target_repair:
                errors.append("last_evolution_target must be an object; run `manage_docs.py evolve <project> --force` or apply a fresh experience payload to repair legacy state")
        else:
            _, target_errors = normalize_evolution_target(project, target_raw)
            for item in target_errors:
                errors.append(f"last_evolution_target: {item}")
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
