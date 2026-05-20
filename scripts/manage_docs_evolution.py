
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
        review_request = evolution_review_request_file(project)
        if review_request.exists():
            review_request.unlink()

def evolution_review_request_file(project: Path) -> Path:
    return project / EVOLUTION_REVIEW_REQUEST_PATH

def target_identity(target: dict[str, Any]) -> tuple[str, tuple[str, ...], str]:
    raw_path = target.get("category_path", [])
    category_path = tuple(str(item).strip() for item in raw_path) if isinstance(raw_path, list) else tuple()
    return (
        str(target.get("family", "")).strip(),
        category_path,
        str(target.get("type_slug", "")).strip(),
    )

def targets_match(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return target_identity(left) == target_identity(right)

def release_alignment_evidence(project: Path, checkpoint: int) -> dict[str, Any]:
    docs_paths = [
        path.relative_to(project).as_posix()
        for path in [
            project / "docs" / "handoff" / "HANDOFF.md",
            project / "docs" / "git_manager" / "CHANGELOG.md",
            project / "docs" / "development" / "DEVELOPMENT.md",
        ]
        if path.exists()
    ]
    release_receipts = [
        path.relative_to(project).as_posix()
        for path in sorted((project / "dist").glob("*/RELEASE_RECEIPT.json"), reverse=True)[:3]
    ] if (project / "dist").is_dir() else []
    return {
        "latest_handoff_path": "docs/handoff/HANDOFF.md",
        "handoff_window": handoff_window(project, checkpoint),
        "docs_paths": docs_paths,
        "recent_conversation_snapshot_paths": [
            item.get("path", "")
            for item in recent_conversation_context(project, limit=10)
            if item.get("path")
        ],
        "release_receipt_paths": release_receipts,
    }

def evolution_review_contract(project: Path, checkpoint: int, target: dict[str, Any]) -> dict[str, Any]:
    return {
        "independent_review_required": True,
        "review_scope": "evolution-only",
        "blocking": True,
        "allowed_verdicts": sorted(ALLOWED_EVOLUTION_REVIEW_VERDICTS),
        "must_check_release_alignment": True,
        "exact_cwd_sessions_only": True,
        "reject_requires_session_reread": True,
        "required_explanation_sections": REQUIRED_EVOLUTION_REVIEW_REQUEST_SECTIONS,
        "release_alignment_evidence": release_alignment_evidence(project, checkpoint),
        "target_schema_label": target_schema_label(target),
    }

def exact_cwd_session_inventory(project: Path) -> dict[str, list[str]]:
    sessions = matched_codex_sessions(project)
    return {
        "session_ids": [str(item.get("id", "")).strip() for item in sessions if str(item.get("id", "")).strip()],
        "session_paths": [str(item.get("path", "")).replace("\\", "/") for item in sessions if str(item.get("path", "")).strip()],
    }

def normalize_evolution_review(
    project: Path,
    raw: Any | None,
    payload_target: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    errors: list[str] = []
    conflicts: list[str] = []
    if raw is None:
        return None, ["evolution_review is required before writing reusable templates"], conflicts
    if not isinstance(raw, dict):
        return None, ["evolution_review must be an object"], conflicts
    verdict = str(raw.get("verdict", "")).strip()
    if verdict not in ALLOWED_EVOLUTION_REVIEW_VERDICTS:
        errors.append("evolution_review verdict must be approve, reject, or approve_with_override")
    approved_target, approved_errors = normalize_evolution_target(project, raw.get("approved_target"))
    original_target, original_errors = normalize_evolution_target(project, raw.get("original_target"))
    errors.extend(f"evolution_review approved_target: {item}" for item in approved_errors)
    errors.extend(f"evolution_review original_target: {item}" for item in original_errors)
    evidence_read = raw.get("evidence_read")
    if not isinstance(evidence_read, dict):
        errors.append("evolution_review evidence_read must be an object")
        evidence_read = {}
    session_ids = [str(item).strip() for item in evidence_read.get("session_ids", [])] if isinstance(evidence_read.get("session_ids", []), list) else []
    session_paths = [str(item).replace("\\", "/").strip() for item in evidence_read.get("session_paths", [])] if isinstance(evidence_read.get("session_paths", []), list) else []
    inventory = exact_cwd_session_inventory(project)
    allowed_ids = set(inventory["session_ids"])
    allowed_paths = set(inventory["session_paths"])
    if any(item and item not in allowed_ids for item in session_ids):
        errors.append("evolution_review session_ids must match exact-cwd Codex sessions only")
    if any(item and item not in allowed_paths for item in session_paths):
        errors.append("evolution_review session_paths must match exact-cwd Codex sessions only")
    reread = bool(raw.get("session_reread_performed"))
    reread_reason = str(raw.get("session_reread_reason", "")).strip()
    if verdict == "reject":
        conflicts.append("review rejected current target as not release-aligned")
        if not reread:
            errors.append("evolution_review reject verdict requires session_reread_performed=true")
        if not reread_reason:
            errors.append("evolution_review reject verdict requires session_reread_reason")
        if not session_ids and not session_paths and allowed_ids:
            errors.append("evolution_review reject verdict must cite exact-cwd Codex sessions that were reread")
    explanation = raw.get("full_explanation")
    if not isinstance(explanation, dict):
        errors.append("evolution_review full_explanation must be an object")
        explanation = {}
    for field in REQUIRED_EVOLUTION_REVIEW_EXPLANATION_FIELDS:
        if not str(explanation.get(field, "")).strip():
            errors.append(f"evolution_review full_explanation.{field} is required")
    if verdict == "approve":
        if not targets_match(approved_target, payload_target):
            errors.append("evolution_review approved_target must match payload evolution_target before writing reusable templates")
    elif verdict == "approve_with_override":
        if not targets_match(approved_target, payload_target):
            conflicts.append("approved_target differs from payload evolution_target")
            errors.append("evolution_review approved_target must match payload evolution_target before writing reusable templates")
    normalized = {
        "verdict": verdict,
        "approved_target": approved_target,
        "original_target": original_target,
        "evidence_read": {
            "conversation_snapshot_paths": [
                str(item).strip()
                for item in evidence_read.get("conversation_snapshot_paths", [])
            ] if isinstance(evidence_read.get("conversation_snapshot_paths", []), list) else [],
            "handoff_paths": [
                str(item).strip()
                for item in evidence_read.get("handoff_paths", [])
            ] if isinstance(evidence_read.get("handoff_paths", []), list) else [],
            "docs_paths": [
                str(item).strip()
                for item in evidence_read.get("docs_paths", [])
            ] if isinstance(evidence_read.get("docs_paths", []), list) else [],
            "release_evidence_paths": [
                str(item).strip()
                for item in evidence_read.get("release_evidence_paths", [])
            ] if isinstance(evidence_read.get("release_evidence_paths", []), list) else [],
            "session_ids": session_ids,
            "session_paths": session_paths,
        },
        "session_reread_performed": reread,
        "session_reread_reason": reread_reason,
        "full_explanation": {
            field: str(explanation.get(field, "")).strip()
            for field in REQUIRED_EVOLUTION_REVIEW_EXPLANATION_FIELDS
        },
    }
    return normalized, errors, conflicts

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

def write_evolution_review_request(
    project: Path,
    count: int,
    target: dict[str, Any],
    reason: str,
    *,
    conflicts: list[str] | None = None,
    review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_targets = [target]
    inferred = infer_evolution_target(project)
    if not targets_match(inferred, target):
        candidate_targets.append(inferred)
    request = {
        "schema_version": 1,
        "project": str(project),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "handoff_count": count,
        "blocking": True,
        "reason": reason,
        "target": target,
        "candidate_targets": candidate_targets,
        "conflicts": conflicts or [],
        "review_contract": evolution_review_contract(project, count, target),
        "required_sections": REQUIRED_EVOLUTION_REVIEW_REQUEST_SECTIONS,
        "exact_cwd_sessions": exact_cwd_session_inventory(project),
        "release_alignment_evidence": release_alignment_evidence(project, count),
        "payload_schema": {
            "evolution_review": {
                "verdict": "approve",
                "approved_target": target,
                "original_target": target,
                "evidence_read": {
                    "session_ids": [],
                    "session_paths": [],
                },
                "session_reread_performed": False,
                "session_reread_reason": "",
                "full_explanation": {
                    field: "..."
                    for field in REQUIRED_EVOLUTION_REVIEW_EXPLANATION_FIELDS
                },
            }
        },
    }
    if isinstance(review, dict):
        request["submitted_review"] = review
    path = evolution_review_request_file(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return {"review_request_written": path.relative_to(project).as_posix(), "reason": reason}

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
            "review": {
                "verdict": review["verdict"],
                "approved_target": review["approved_target"],
            },
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
                "templates": template_index,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    written.append(index_path.relative_to(project).as_posix())
    index = {
        "schema_version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "handoff_count": checkpoint,
        "cadence_handoffs": EVOLUTION_CADENCE_HANDOFFS,
        "version_window": "current-plus-latest-history",
        "target": target,
        "review": {
            "verdict": review["verdict"],
            "approved_target": review["approved_target"],
        },
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
    state["last_evolution_target"] = evolution_target
    if summaries:
        state["last_evolution_summary"] = summaries
    else:
        state.pop("last_evolution_summary", None)
    if requires_atomic_evolution and normalized_review:
        state["last_evolution_review_at"] = checkpoint
        state["last_evolution_review_verdict"] = normalized_review["verdict"]
        state["last_evolution_review_target"] = normalized_review["approved_target"]
        state["last_evolution_review_sources"] = normalized_review["evidence_read"]
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
