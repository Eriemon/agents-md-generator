
from __future__ import annotations

from manage_docs_shared import *
from manage_docs_experience import (
    archive_experience_files,
    current_experience_files,
    latest_historical_experience,
    missing_markdown_sections,
    payload_entries,
    payload_evolution_summary,
    similarity,
    validate_experience_content,
    validate_experience_payload,
    workflow_experience_errors,
    write_experience_request,
)

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
    skill_path = str(layout.get("path") or "skills/agents-md-generator").strip()
    candidate = project / skill_path / "assets" / "templates"
    if candidate.exists() or (project / skill_path).exists():
        return candidate / "evolution"
    return project / "assets" / "templates" / "evolution"

def project_keyword_text(project: Path) -> str:
    profile = control_profile(project)
    facts = inspect_project(project)
    parts: list[str] = [
        str(profile.get("kind", "")),
        str(profile.get("name", "")),
        str(profile.get("purpose", "")),
        str(profile.get("reason", "")),
        str(profile.get("notes", "")),
        str(profile.get("expected_outcome", "")),
        str(facts.get("project_type", "")),
        str(facts.get("framework", "")),
        " ".join(str(item) for item in facts.get("languages", [])),
        " ".join(str(item) for item in facts.get("files", [])),
        " ".join(str(item) for item in facts.get("directories", [])),
    ]
    layout = profile.get("skill_layout", {}) if isinstance(profile.get("skill_layout"), dict) else {}
    parts.append(str(layout.get("path", "")))
    contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract"), dict) else {}
    parts.extend(str(contract.get(key, "")) for key in ("local", "remote", "feature_rules"))
    return "\n".join(parts).lower()

def inferred_evolution_category(project: Path) -> list[str]:
    text = project_keyword_text(project)
    if any(term in text for term in ("vivado", "fpga", "xilinx", "vitis", "verilog", "rtl", "hls")):
        return ["FPGA"]
    if "sort" in text or "sorting" in text or "排序" in text:
        return ["algorithm"]
    if "agents-md" in text or "agents.md" in text or "agent rule" in text or "coding-agent" in text or "agent governance" in text:
        return ["agent-governance"]
    if "docs governance" in text or "docs-governance" in text or "handoff" in text or "experience" in text:
        return ["docs-governance"]
    if any(term in text for term in ("react", "next.js", "vue", "frontend", "ui", "gui")):
        return ["web", "frontend"]
    if any(term in text for term in ("api", "backend", "express", "fastapi", "django", "flask")):
        return ["backend", "api"]
    if any(term in text for term in ("database", "data", "sql", "sqlite", "postgres", "mysql")):
        return ["data", "database"]
    return ["general"]

def inferred_evolution_type_slug(project: Path, category_path: list[str]) -> str:
    profile = control_profile(project)
    facts = inspect_project(project)
    text = project_keyword_text(project)
    if category_path == ["algorithm"] and ("sort" in text or "sorting" in text or "排序" in text):
        return "sort"
    name = str(profile.get("name") or facts.get("project_name") or project.name)
    return slug(name)

def default_evolution_family(project: Path) -> str:
    kind = str(control_profile(project).get("kind") or inspect_project(project).get("project_type") or "").lower()
    return "skill-template" if kind == "skill" or kind == "skill-repo" else "engineering-template"

def expected_family_for_project(project: Path) -> str:
    return "skill-template" if str(control_profile(project).get("kind", "")).lower() == "skill" else "engineering-template"

def safe_template_segment(value: str) -> bool:
    return bool(SAFE_TEMPLATE_SEGMENT_RE.fullmatch(value.strip())) and value.strip() not in {".", ".."}

def infer_evolution_target(project: Path) -> dict[str, Any]:
    category_path = inferred_evolution_category(project)
    return {
        "family": default_evolution_family(project),
        "category_path": category_path,
        "type_slug": inferred_evolution_type_slug(project, category_path),
        "rationale": "Inferred from project control profile, repository facts, and topic keywords.",
        "source": "inferred",
    }

def normalize_evolution_target(project: Path, raw: Any | None) -> tuple[dict[str, Any], list[str]]:
    target = infer_evolution_target(project)
    errors: list[str] = []
    if raw is not None:
        if not isinstance(raw, dict):
            return target, ["evolution_target must be an object when provided"]
        target = {
            "family": str(raw.get("family", "")).strip(),
            "category_path": raw.get("category_path", []),
            "type_slug": str(raw.get("type_slug", "")).strip(),
            "rationale": str(raw.get("rationale", "")).strip(),
            "source": "ai",
        }
    family = str(target.get("family", "")).strip()
    expected_family = expected_family_for_project(project)
    if family not in {"skill-template", "engineering-template"}:
        errors.append("evolution_target family must be skill-template or engineering-template")
    elif family != expected_family:
        kind = str(control_profile(project).get("kind", "engineering") or "engineering")
        errors.append(f"evolution_target family {family} does not match project kind {kind}")
    category_path = target.get("category_path")
    if not isinstance(category_path, list) or not category_path:
        errors.append("evolution_target category_path must be a non-empty list")
        category_path = []
    cleaned_categories: list[str] = []
    for segment in category_path:
        value = str(segment).strip()
        if not safe_template_segment(value):
            errors.append("evolution_target category_path contains unsafe slug")
        else:
            cleaned_categories.append(value)
    type_slug = str(target.get("type_slug", "")).strip()
    if not safe_template_segment(type_slug):
        errors.append("evolution_target type_slug contains unsafe slug")
    rationale = str(target.get("rationale", "")).strip()
    if not rationale:
        errors.append("evolution_target rationale is required")
    target["family"] = family
    target["category_path"] = cleaned_categories
    target["type_slug"] = type_slug
    target["rationale"] = rationale
    return target, errors

def target_schema_label(target: dict[str, Any]) -> str:
    category_path = target.get("category_path", [])
    if not isinstance(category_path, list):
        category_path = []
    return f"{target.get('family', 'unknown')}/{'/'.join(str(item) for item in category_path) or 'general'}"

def evolution_schema_for(target: dict[str, Any]) -> dict[str, Any]:
    family = str(target.get("family", "")).strip()
    raw_path = target.get("category_path", [])
    category_path = tuple(str(item).strip() for item in raw_path) if isinstance(raw_path, list) else tuple()
    candidates = [
        (family, category_path),
        (family, category_path[:1]) if category_path else (family, tuple()),
        (family, ("general",)),
    ]
    for key in candidates:
        schema = EVOLUTION_CATEGORY_SCHEMAS.get(key)
        if schema:
            return schema
    return {}

def target_evidence_summary(project: Path, target: dict[str, Any]) -> list[str]:
    profile = control_profile(project)
    facts = inspect_project(project)
    summary = [
        f"Profile kind: {profile.get('kind', facts.get('project_type', 'unknown'))}",
        f"Profile name: {profile.get('name', facts.get('project_name', project.name))}",
        f"Framework/project type: {facts.get('framework', 'none')} / {facts.get('project_type', 'unknown')}",
        f"Inference rationale: {target.get('rationale', 'not recorded')}",
    ]
    keyword_excerpt = [line for line in project_keyword_text(project).splitlines() if line.strip()][:4]
    if keyword_excerpt:
        summary.extend(f"Keyword evidence: {line[:160]}" for line in keyword_excerpt)
    return summary

def resolved_state_evolution_target(project: Path, raw: Any | None) -> tuple[dict[str, Any], bool]:
    if isinstance(raw, dict):
        target, errors = normalize_evolution_target(project, raw)
        if not errors:
            return target, False
    return infer_evolution_target(project), raw is not None

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

def strip_leading_title(summary: str) -> str:
    lines = summary.splitlines()
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index < len(lines) and lines[index].startswith("# "):
        index += 1
        while index < len(lines) and not lines[index].strip():
            index += 1
    return "\n".join(lines[index:]).strip()

def validate_workflow_schema_for_target(content: str, target: dict[str, Any]) -> list[str]:
    schema = evolution_schema_for(target)
    if not schema:
        return []
    label = target_schema_label(target)
    groups = schema.get("workflow_required_groups", [])
    if isinstance(groups, list):
        for group in groups:
            if isinstance(group, tuple) and not any(contains_term(content, term) for term in group):
                return [f"1-workflow.md: evolution summary does not match workflow schema for {label}"]
    forbidden = schema.get("workflow_forbidden_terms", ())
    if isinstance(forbidden, tuple):
        for term in forbidden:
            if contains_term(content, str(term)):
                return [f"1-workflow.md: evolution summary does not match workflow schema for {label}"]
    return []

def validate_evolution_summaries(project: Path, summaries: dict[str, str], target: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    expected = [spec["filename"] for spec in experience_file_specs(project)[:4]]
    missing = [filename for filename in expected if filename not in summaries]
    if missing:
        errors.append(f"evolution_summary missing files: {', '.join(missing)}")
    for filename in expected:
        content = summaries.get(filename, "")
        if len(content.strip()) < EVOLUTION_SUMMARY_MIN_LENGTH:
            errors.append(f"{filename}: evolution summary content is too short")
        for section in missing_markdown_sections(content, REQUIRED_EVOLUTION_SECTIONS):
            errors.append(f"{filename}: evolution summary missing required section ## {section}")
        if "## Reusable Lessons" in content:
            errors.append(f"{filename}: evolution summary must be a synthesis, not the old reusable-lessons copy format")
    target_info = target or infer_evolution_target(project)
    workflow = summaries.get("1-workflow.md", "")
    if workflow:
        errors.extend(validate_workflow_schema_for_target(workflow, target_info))
    return errors

def write_evolution_request(project: Path, count: int, target: dict[str, Any], reason: str) -> dict[str, Any]:
    schema = evolution_schema_for(target)
    request = {
        "schema_version": 1,
        "project": str(project),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "handoff_count": count,
        "requires_ai_generation": True,
        "reason": reason,
        "target": target,
        "target_schema_label": target_schema_label(target),
        "target_evidence": target_evidence_summary(project, target),
        "flow_requirements": schema.get("flow_requirements", []),
        "mixed_content_risks": schema.get("mixed_content_risks", []),
        "source_versions": {
            spec["filename"]: source_versions_for(project, spec["filename"])
            for spec in experience_file_specs(project)[:4]
        },
        "required_sections": REQUIRED_EVOLUTION_SECTIONS,
        "payload_schema": {
            "evolution_summary": {
                "1-workflow.md": "# Workflow Evolution Template\n\n## Evidence Sources\n..."
            }
        },
    }
    path = evolution_request_file(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return {"request_written": path.relative_to(project).as_posix(), "reason": reason}

def evolution_markdown(topic: dict[str, str], versions: list[dict[str, str]], target: dict[str, Any], summary: str) -> str:
    sources = "\n".join(f"- `{item['path']}`" for item in versions) or "- No source versions available."
    summary_body = strip_leading_title(summary)
    return "\n".join([
        f"# {topic['title']} Evolution Template",
        "",
        f"- Template family: {target['family']}",
        f"- Category path: {'/'.join(target['category_path'])}",
        f"- Target type: {target['type_slug']}",
        f"- Source file: {topic['filename']}",
        f"- Version window: current-plus-latest-history",
        f"- Target source: {target.get('source', 'unknown')}",
        f"- Rationale: {target.get('rationale', 'not recorded')}",
        "",
        "## Source Versions",
        sources,
        "",
        summary_body,
        "",
    ])

def remove_empty_parents(path: Path, stop: Path) -> None:
    current = path
    stop_resolved = stop.resolve()
    while current.exists() and current.is_dir() and current.resolve() != stop_resolved:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent

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
        output = project / output_raw
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

    root = evolution_template_root(project)
    target_dir = root / target["family"]
    for segment in target["category_path"]:
        target_dir = target_dir / segment
    target_dir = target_dir / target["type_slug"]
    root.mkdir(parents=True, exist_ok=True)
    archived = archive_obsolete_evolution_outputs(project, root, target_dir)
    written: list[str] = []
    index_entries: list[dict[str, Any]] = []
    core_specs = experience_file_specs(project)[:4]
    target_dir.mkdir(parents=True, exist_ok=True)
    template_index: list[dict[str, Any]] = []
    for topic in core_specs:
        versions = source_versions_for(project, topic["filename"])
        output = target_dir / topic["filename"]
        output.write_text(evolution_markdown(topic, versions, target, summary_map[topic["filename"]]), encoding="utf-8")
        rel_output = output.relative_to(project).as_posix()
        written.append(rel_output)
        source_paths = [item["path"] for item in versions]
        row = {
            "family": target["family"],
            "category_path": target["category_path"],
            "target_type": target["type_slug"],
            "topic": topic["filename"],
            "output": rel_output,
            "source_versions": source_paths,
            "sha256": file_hash(output),
        }
        template_index.append(row)
        index_entries.append(row)
    index_path = target_dir / "template-index.json"
    index_path.write_text(json.dumps({"schema_version": 1, "target": target, "templates": template_index}, indent=2, sort_keys=True), encoding="utf-8")
    written.append(index_path.relative_to(project).as_posix())
    index = {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "handoff_count": checkpoint,
        "cadence_handoffs": EVOLUTION_CADENCE_HANDOFFS,
        "version_window": "current-plus-latest-history",
        "target": target,
        "templates": index_entries,
    }
    index_path = root / "evolution-index.json"
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    written.append(index_path.relative_to(project).as_posix())
    state["last_evolution_target"] = target
    state["last_evolution_at"] = checkpoint
    clear_fulfilled_requests(
        project,
        state,
        clear_experience=bool(latest_experience_due(count)) and int(state.get("last_experience_at", 0)) >= latest_experience_due(count),
        clear_evolution=True,
    )
    save_state(project, state)
    return {
        "project": str(project),
        "written": written,
        "archived": archived,
        "handoff_count": checkpoint,
        "index": str(index_path),
        "target": target,
        "repaired_legacy_target": repaired_target,
    }

def apply_experience_payload(project: Path, payload_path: str) -> dict[str, Any]:
    from manage_docs_scaffold_session import read_input, scaffold

    scaffold(project)
    state = load_state(project)
    count = int(state.get("handoff_count", 0))
    checkpoint = latest_experience_due(count) or count
    requires_atomic_evolution = checkpoint >= EVOLUTION_CADENCE_HANDOFFS and checkpoint % EVOLUTION_CADENCE_HANDOFFS == 0
    payload = read_input(payload_path)
    entries, errors = validate_experience_payload(project, payload)
    evolution_target, target_errors = normalize_evolution_target(project, payload.get("evolution_target") if "evolution_target" in payload else None)
    errors.extend(target_errors)
    summaries = payload_evolution_summary(payload)
    if requires_atomic_evolution and not summaries:
        errors.append("evolution_summary is required before writing reusable templates")
    if summaries:
        errors.extend(validate_evolution_summaries(project, summaries, evolution_target))
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
    state["last_evolution_target"] = evolution_target
    if summaries:
        state["last_evolution_summary"] = summaries
    else:
        state.pop("last_evolution_summary", None)
    save_state(project, state)
    result: dict[str, Any] = {"project": str(project), "written": written, "archived": archived, "handoff_count": checkpoint}
    if requires_atomic_evolution:
        result["evolution"] = run_evolution(project)
        if result["evolution"].get("errors"):
            result["errors"] = list(result["evolution"]["errors"])
        else:
            refreshed = load_state(project)
            clear_fulfilled_requests(project, refreshed, clear_experience=True, clear_evolution=True)
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
    state = load_state(project)
    count = int(state.get("handoff_count", 0))
    checkpoint = latest_experience_due(count)
    last = int(state.get("last_experience_at", 0))
    if not force and (checkpoint == 0 or last >= checkpoint):
        return {"project": str(project), "skipped": True, "handoff_count": count, "last_experience_at": last}
    return write_experience_request(project, checkpoint or count)

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
