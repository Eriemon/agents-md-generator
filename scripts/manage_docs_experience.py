
from __future__ import annotations

from manage_docs_shared import *

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

def recent_handoff_history(project: Path, limit: int = 10) -> list[dict[str, Any]]:
    history = project / "docs" / "handoff" / "history_handoff"
    if not history.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(history.glob("HANDOFF-*.md"), reverse=True)[:limit]:
        content = path.read_text(encoding="utf-8", errors="ignore")
        rows.append({
            "path": path.relative_to(project).as_posix(),
            "content": content,
            "handoff_count": handoff_count_from_markdown(content),
        })
    return rows

def current_experience_files(project: Path) -> dict[str, str]:
    root = project / "docs" / "experience"
    return {
        path.name: path.read_text(encoding="utf-8", errors="ignore")
        for path in sorted(root.glob("[0-9]*-*.md"))
        if path.is_file()
    }

def project_content_evidence(project: Path, limit: int = 14) -> list[str]:
    facts = inspect_project(project)
    evidence = list(facts.get("files", []))
    if len(evidence) < limit:
        evidence.extend(path for path in facts.get("directories", []) if path not in evidence)
    return evidence[:limit]

def session_bundle(project: Path) -> list[dict[str, Any]]:
    bundles: list[dict[str, Any]] = []
    for session in matched_codex_sessions(project):
        path = Path(session["path"])
        bundles.append(
            {
                **session,
                "messages": session_message_rows(path),
            }
        )
    return bundles

def format_message_excerpt(messages: list[dict[str, str]], limit: int = 6) -> str:
    if not messages:
        return "- No extracted user or assistant message content was available from the matched session transcript."
    lines = []
    for row in messages[:limit]:
        prefix = "User" if row.get("role") == "user" else "Assistant"
        text = " ".join(str(row.get("message", "")).split())
        lines.append(f"- {prefix}: {text[:220]}")
    return "\n".join(lines)

def bootstrap_topic_content(
    project: Path,
    spec: dict[str, str],
    *,
    scope_label: str,
    sessions: list[dict[str, Any]],
    current_files: list[str],
) -> str:
    session_ids = ", ".join(item["id"] for item in sessions if item.get("id")) or "none"
    session_paths = [display_path(Path(item["path"])) for item in sessions[:4] if item.get("path")]
    current_file_lines = "\n".join(f"- `{path}`" for path in current_files[:10]) or "- No current file evidence was detected."
    session_path_lines = "\n".join(f"- `{path}`" for path in session_paths) or "- No matching Codex session transcript file was available."
    excerpts = "\n\n".join(
        [
            f"### Session `{item.get('id', 'unknown')}`\n{format_message_excerpt(item.get('messages', []))}"
            for item in sessions[:4]
        ]
    ) or "### Session Evidence\n- No matching Codex session transcripts were found for this exact working directory."
    common_context = [
        f"# {spec['title']} Experience",
        "",
        "## Evidence Read",
        f"- Scope: {scope_label}.",
        f"- Matched Codex sessions (exact cwd only): {session_ids}.",
        "- Current repository facts discovered from the working directory.",
        "- Existing repository files and directories that were already present before AGENTS governance scaffolding.",
        "",
        "### Matched Session Files",
        session_path_lines,
        "",
        "### Current Workspace Evidence",
        current_file_lines,
        "",
        "### Session Excerpts",
        excerpts,
        "",
        "## Task Context",
        f"- The current working directory already contained project content but did not yet contain a root `AGENTS.md`. This bootstrap experience records how the existing code and the exact-cwd Codex session history should be read together before the workspace is normalized.",
        f"- This `{spec['title']}` record is generated from session evidence plus landed repository content so future agents can understand what work was underway, what files mattered, and what governance repairs were required.",
        "",
        "## How To Apply",
        "- First inspect whether the root `AGENTS.md` is missing and whether the workspace already contains meaningful files or directories.",
        "- Then read only the Codex sessions whose `session_meta.payload.cwd` exactly matches the current working directory; do not mix in adjacent or similarly named workspaces.",
        "- Use the matched sessions to reconstruct the recent user intent, combine that with the current file tree, and only then create the governed docs layout, latest experience files, and any required structure migration plan.",
        "- If directory structure is not compliant, ask whether to normalize it before changing files. The recommended default is yes, but the confirmation must still be explicit.",
        "",
        "## Problems And Risks",
        "- If session matching is too broad, another repository's history can contaminate the current experience files and make the generated AGENTS guidance unsafe.",
        "- If the workspace layout is normalized without asking first, the agent can silently move the wrong files or create governance output in the wrong place.",
        "- If only the current file tree is used and the Codex session history is ignored, the resulting experience files can miss the real reason the repository is in its current partial state.",
    ]
    if spec["filename"] == "1-workflow.md":
        common_context.extend(
            [
                "",
                "## Iterated Lessons",
                "- 完整流程链: detect missing root AGENTS.md -> confirm the workspace already has landed content -> read exact-cwd Codex sessions -> extract user and assistant intent from those sessions -> inspect the current file tree -> ask whether to normalize structure when the layout violates the contract -> migrate legacy docs paths -> generate history experience snapshots per matched session -> synthesize the latest current experience set -> continue with AGENTS generation and verification.",
                "- 完整逻辑链: the working directory is the identity boundary; the exact cwd selects the session transcripts; the transcripts explain why current files exist; the current files confirm what was actually landed; the structure gate decides whether reorganization must be confirmed; the docs bootstrap turns those inputs into governed memory under `docs/experience/` and `docs/experience/history_experience/`.",
                "- 闭环: if exact-cwd sessions are found, archive them as historical experience first; if no exact-cwd sessions are found, mark the conversation context as missing and generate the latest experience from landed files only; if structure is invalid, stop and ask before reorganizing; after normalization, regenerate current experience so the governed state reflects the repaired repository.",
                "- For path handling, always render workspace evidence as normalized repository-relative paths such as `src/main.py` or absolute filesystem paths with real separators. Never collapse them into unreadable joined strings.",
                "",
                "```mermaid",
                "flowchart TD",
                "    A[Missing root AGENTS.md detected] --> B[Check whether workspace already has landed content]",
                "    B --> C[Match exact-cwd Codex sessions]",
                "    C --> D[Inspect current files and directories]",
                "    D --> E[Ask whether to normalize structure when contract violations exist]",
                "    E --> F[Migrate legacy docs paths into governed docs layout]",
                "    F --> G[Write per-session history_experience snapshots]",
                "    G --> H[Write latest current docs/experience files]",
                "    H --> I[Continue AGENTS generation and verification]",
                "```",
                "",
                "## Next Application",
                "- Reuse this bootstrap only for workspaces that already contain real content but still lack a root `AGENTS.md`.",
                "- Keep the exact-cwd rule strict so that neighboring repositories never leak into the current experience set.",
                "- After the initial bootstrap, switch back to the normal handoff and experience cadence instead of regenerating history on every run.",
            ]
        )
    else:
        common_context.extend(
            [
                "",
                "## Iterated Lessons",
                f"- `{spec['title']}` bootstrap records should capture both the current repository evidence and the matching Codex session excerpts so later agents can understand not only what files exist, but why they exist and what restructuring or governance work was already being discussed.",
                "- The bootstrap process should remain conservative: exact-cwd matching only, no silent directory normalization, and no fabricated narrative beyond what the file tree and the matched session excerpts support.",
                "- User-visible paths should stay normalized and readable. Repository-relative evidence such as `src/main.py`, `docs/experience/1-workflow.md`, or `engineering/demo-app/` is easier to audit than collapsed raw path strings.",
                "",
                "## Next Application",
                f"- Use this `{spec['title']}` template when the next missing-AGENTS bootstrap needs to recover context from local Codex sessions and landed files before ordinary docs governance begins.",
                "- If exact-cwd session evidence is missing, say that clearly and lean harder on file evidence instead of pretending the missing conversation details are known.",
            ]
        )
    return "\n".join(common_context).strip() + "\n"

def write_bootstrap_experience_set(
    project: Path,
    root: Path,
    *,
    scope_label: str,
    sessions: list[dict[str, Any]],
    current_files: list[str],
) -> list[str]:
    written: list[str] = []
    root.mkdir(parents=True, exist_ok=True)
    for spec in experience_file_specs(project):
        target = root / spec["filename"]
        target.write_text(
            bootstrap_topic_content(
                project,
                spec,
                scope_label=scope_label,
                sessions=sessions,
                current_files=current_files,
            ),
            encoding="utf-8",
        )
        written.append(target.relative_to(project).as_posix())
    return written

def bootstrap_experience(project: Path, force: bool = False) -> dict[str, Any]:
    from manage_docs_scaffold_session import scaffold
    pre_scaffold_files = project_content_evidence(project)
    sessions = session_bundle(project)
    scaffold(project)
    facts = inspect_project(project)
    if not facts.get("session_history_bootstrap_required") and not force:
        return {
            "project": str(project),
            "skipped": True,
            "reason": "workspace does not require initial session bootstrap",
            "matched_session_count": facts.get("matched_session_count", 0),
            "matched_session_ids": facts.get("matched_session_ids", []),
        }
    current_files = pre_scaffold_files
    experience_root = project / "docs" / "experience"
    current_existing = list(experience_root.glob("[0-9]*-*.md"))
    if current_existing:
        archive_experience_files(project)
    history_written: list[str] = []
    for session in sessions:
        session_dir = experience_root / "history_experience" / f"{stamp()}-{slug(session.get('id', 'session'))}"
        history_written.extend(
            write_bootstrap_experience_set(
                project,
                session_dir,
                scope_label=f"matched session {session.get('id', 'unknown')}",
                sessions=[session],
                current_files=current_files,
            )
        )
    current_written = write_bootstrap_experience_set(
        project,
        experience_root,
        scope_label="latest current bootstrap",
        sessions=sessions,
        current_files=current_files,
    )
    state = load_state(project)
    state["experience_bootstrapped_from_sessions"] = True
    state["last_session_bootstrap_at"] = datetime.now().isoformat(timespec="seconds")
    state["matched_session_count"] = len(sessions)
    state["matched_session_ids"] = [item.get("id", "") for item in sessions if item.get("id")]
    save_state(project, state)
    return {
        "project": str(project),
        "skipped": False,
        "requires_user_confirmation": False,
        "matched_session_count": len(sessions),
        "matched_session_ids": [item.get("id", "") for item in sessions if item.get("id")],
        "history_written": history_written,
        "current_experience_written": current_written,
        "conversation_context_missing": len(sessions) == 0,
        "session_history_match_scope": "exact-cwd",
        "sessions_root": display_path(codex_sessions_root()),
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
    checkpoint = latest_experience_due(count) or count
    requires_atomic_evolution = checkpoint >= EVOLUTION_CADENCE_HANDOFFS and checkpoint % EVOLUTION_CADENCE_HANDOFFS == 0
    conversations = recent_conversation_context(project, limit=10)
    handoff_window_payload = handoff_window(project, checkpoint)
    conversation_window_payload = recent_conversation_window(project)
    request = {
        "schema_version": 1,
        "project": str(project),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "handoff_count": count,
        "cadence_checkpoint": checkpoint,
        "requires_ai_generation": True,
        "requires_atomic_evolution": requires_atomic_evolution,
        "ai_must_read_recent_conversations": True,
        "conversation_context_limit": 10,
        "conversation_context_missing": not conversations,
        "conversation_context": conversations,
        "project_facts": inspect_project(project),
        "control_profile": control_profile(project),
        "current_handoff": latest_handoff.read_text(encoding="utf-8", errors="ignore") if latest_handoff.exists() else "",
        "recent_handoff_history": recent_handoff_history(project, limit=10),
        "handoff_window": handoff_window_payload,
        "recent_conversation_window": conversation_window_payload,
        "current_experience": current_experience_files(project),
        "historical_experience": latest_historical_experience(project, filenames),
        "target_files": specs,
        "detail_requirements": {
            spec["filename"]: detail_requirements_for(spec["filename"])
            for spec in specs
        },
        "quality_rules": [
            "AI must generate topic-specific lessons; scripts only collect evidence and apply validated payloads.",
            "Experience files must be detailed and project-specific; concise placeholders are not acceptable.",
            f"Summaries must cover the current cadence window {handoff_window_payload['start_handoff_count']}-{handoff_window_payload['end_handoff_count']} rather than the entire repository history.",
            "Every experience file must include sections: Evidence Read, Task Context, How To Apply, Problems And Risks, Iterated Lessons, and Next Application.",
            "Each non-workflow experience file must be detailed enough for a future maintainer to understand the task, implementation path, problems, and reuse conditions.",
            "Each topic must name concrete changed artifacts, failed risks, verification evidence, and future reuse conditions rather than broad process advice.",
            "1-workflow.md must describe a complete skill or engineering development workflow, including the full process chain, logic chain, feedback/closure loops, and a Mermaid flowchart.",
            "Do not copy a full HANDOFF.md into experience files.",
            "Do not write highly similar content across the 10 experience files.",
            "4-design-ui.md must say 暂无 UI 经验 when no UI work was involved.",
            "Reusable evolution templates require AI-authored evolution_summary entries with synthesis sections; scripts must not copy Iterated Lessons directly into templates.",
        ],
        "payload_schema": {
            "generated_by": "ai",
            "experience_files": [{"filename": "1-workflow.md", "content": "# Workflow Experience\\n..."}],
            "evolution_target": {"family": "skill-template", "category_path": ["agent-governance"], "type_slug": "agents-md-generator", "rationale": "..."},
            "evolution_summary": {"1-workflow.md": "# Workflow Evolution Template\\n\\n## Evidence Sources\\n..."},
        },
    }
    if requires_atomic_evolution:
        from manage_docs_evolution import (
            evolution_review_contract,
            evolution_schema_for,
            infer_evolution_target,
            release_alignment_evidence,
            target_schema_label,
        )

        evolution_target = infer_evolution_target(project)
        schema = evolution_schema_for(evolution_target)
        request["evolution_target"] = evolution_target
        request["target_schema_label"] = target_schema_label(evolution_target)
        request["flow_requirements"] = schema.get("flow_requirements", [])
        request["mixed_content_risks"] = schema.get("mixed_content_risks", [])
        request["requires_extra_evolution_review"] = True
        request["review_scope"] = "evolution-only"
        request["review_blocking"] = True
        request["review_contract"] = evolution_review_contract(project, checkpoint, evolution_target)
        request["release_alignment_evidence"] = release_alignment_evidence(project, checkpoint)
    return request

def write_experience_request(project: Path, count: int) -> dict[str, Any]:
    request = build_experience_request(project, count)
    target = experience_request_file(project)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    state = load_state(project)
    state["experience_update_required"] = True
    state["experience_request_due_at"] = int(request.get("cadence_checkpoint", count))
    state["experience_request"] = target.relative_to(project).as_posix()
    if isinstance(request.get("evolution_target"), dict):
        state["last_evolution_target"] = request["evolution_target"]
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

def payload_evolution_summary(payload: dict[str, Any]) -> dict[str, str]:
    raw = payload.get("evolution_summary")
    summaries: dict[str, str] = {}
    if isinstance(raw, dict):
        for filename, content in raw.items():
            summaries[str(filename)] = str(content)
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                filename = str(item.get("filename", "")).strip()
                content = str(item.get("content", ""))
                if filename:
                    summaries[filename] = content
    return summaries

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

def workflow_experience_errors(content: str) -> list[str]:
    errors: list[str] = []
    lowered = content.lower()
    if len(content.strip()) < WORKFLOW_EXPERIENCE_MIN_LENGTH:
        errors.append("1-workflow.md: AI workflow experience content is too short")
    if "```mermaid" not in lowered or "flowchart" not in lowered:
        errors.append("1-workflow.md: must include a Mermaid flowchart")
    required_terms = [
        ("流程链", "process chain", "workflow chain"),
        ("逻辑链", "logic chain"),
        ("闭环", "closure loop", "feedback loop"),
    ]
    for terms in required_terms:
        if not any(term in lowered for term in terms):
            errors.append(f"1-workflow.md: must describe {terms[0]}")
    phase_terms = [
        ("plan", "计划", "规划"),
        ("develop", "开发", "implementation"),
        ("test", "测试", "验证", "仿真"),
        ("release", "发布", "释放", "dist"),
    ]
    for terms in phase_terms:
        if not any(term in lowered for term in terms):
            errors.append(f"1-workflow.md: missing workflow phase {terms[0]}")
    return errors

def missing_markdown_sections(content: str, sections: list[str]) -> list[str]:
    missing: list[str] = []
    for section in sections:
        if not re.search(rf"^##\s+{re.escape(section)}\s*$", content, flags=re.MULTILINE):
            missing.append(section)
    return missing

def validate_experience_content(filename: str, content: str) -> list[str]:
    errors: list[str] = []
    minimum = WORKFLOW_EXPERIENCE_MIN_LENGTH if filename == "1-workflow.md" else EXPERIENCE_MIN_LENGTH
    if len(content.strip()) < minimum:
        errors.append(f"{filename}: AI experience content is too short")
    for section in missing_markdown_sections(content, REQUIRED_EXPERIENCE_SECTIONS):
        errors.append(f"{filename}: missing required section ## {section}")
    if "Iterate this file from completed handoffs" in content or "Awaiting AI experience summary" in content:
        errors.append(f"{filename}: contains placeholder experience text")
    if "## Original Plan And Steps" in content and "## Verification Evidence" in content:
        errors.append(f"{filename}: must not copy full HANDOFF.md sections")
    if filename == "4-design-ui.md" and "暂无 UI 经验" not in content and not re.search(r"\b(ui|gui|visual|design)\b", content, flags=re.IGNORECASE):
        errors.append("4-design-ui.md: must either record 暂无 UI 经验 or contain UI/design-specific lessons")
    if filename == "1-workflow.md":
        errors.extend(workflow_experience_errors(content))
    else:
        errors.extend(validate_topic_specificity(filename, content))
    return errors

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
        errors.extend(validate_experience_content(filename, content))
    for index, left_name in enumerate(expected):
        for right_name in expected[index + 1:]:
            left = entries.get(left_name, "")
            right = entries.get(right_name, "")
            if left and right and similarity(left, right) > 0.78:
                errors.append(f"{left_name} and {right_name}: experience files are too similar")
    return entries, errors
