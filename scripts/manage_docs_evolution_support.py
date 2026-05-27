from __future__ import annotations

from manage_docs_shared import *
from manage_docs_experience import missing_markdown_sections, recent_conversation_context


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
    text = project_keyword_text(project)
    if category_path == ["algorithm"] and ("sort" in text or "sorting" in text or "排序" in text):
        return "sort"
    if category_path == ["agent-governance"]:
        return "governance-workflow"
    if category_path == ["docs-governance"]:
        return "workspace-governance"
    if category_path == ["FPGA"]:
        return "fpga-workflow"
    if category_path == ["web", "frontend"]:
        return "frontend-workflow"
    if category_path == ["backend", "api"]:
        return "api-workflow"
    if category_path == ["data", "database"]:
        return "data-workflow"
    return "general-workflow"


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


def evolution_review_request_file(project: Path) -> Path:
    return project / ".agents/evolution-review-request.json"


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
    sink = evolution_template_sink(project)
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
        "evolution_sink": sink,
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


def write_evolution_import_request(
    project: Path,
    checkpoint: int,
    target: dict[str, Any],
    bundle_dir: Path,
    sink: dict[str, Any],
) -> dict[str, Any]:
    path = evolution_import_request_file(project)
    request = {
        "schema_version": 1,
        "project": str(project),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "handoff_count": checkpoint,
        "target": target,
        "bundle_dir": bundle_dir.relative_to(project).as_posix(),
        "sink": sink,
        "reason": "installed agents-md-generator skill is unavailable or not writable; import is required to publish reusable templates",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return {"import_request_written": path.relative_to(project).as_posix()}


def evolution_markdown(
    topic: dict[str, str],
    versions: list[dict[str, str]],
    target: dict[str, Any],
    summary: str,
    provenance: dict[str, Any],
) -> str:
    sources = "\n".join(f"- `{item['path']}`" for item in versions) or "- No source versions available."
    summary_body = strip_leading_title(summary)
    source_project = str(provenance.get("source_project_name", "not recorded"))
    source_workspace_label = "current governed workspace (local path intentionally omitted)"
    if not str(provenance.get("source_workspace", "")).strip():
        source_workspace_label = "not recorded"
    source_window = provenance.get("source_handoff_window", {})
    start = source_window.get("start_handoff_count", "?")
    end = source_window.get("end_handoff_count", "?")
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
        f"- Source workspace: {source_workspace_label}",
        f"- Source project: {source_project}",
        f"- Source handoff window: {start}-{end}",
        "",
        "## Source Versions",
        sources,
        "",
        summary_body,
        "",
    ])
