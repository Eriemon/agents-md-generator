
from __future__ import annotations

import os

from manage_docs_shared import *
from source_governance import format_source_governance_errors, source_governance_report


VERSION_RE = re.compile(r"\bv\d+\.\d+\.\d+\b")


def inferred_skill_dir(project: Path, raw_skill_dir: str | Path | None = None) -> Path | None:
    if raw_skill_dir:
        candidate = Path(raw_skill_dir)
        if not candidate.is_absolute():
            candidate = project / candidate
        return candidate.resolve()
    profile = project_profile(project)
    if isinstance(profile, dict):
        layout = profile.get("skill_layout") if isinstance(profile.get("skill_layout"), dict) else {}
        raw_path = str(layout.get("path") or "").strip()
        if raw_path:
            return (project / raw_path).resolve()
        name = str(profile.get("name") or "").strip()
        if name:
            candidate = project / "skills" / name
            if candidate.exists():
                return candidate.resolve()
    skills_root = project / "skills"
    if skills_root.is_dir():
        candidates = [path for path in skills_root.iterdir() if (path / "VERSION").is_file()]
        if len(candidates) == 1:
            return candidates[0].resolve()
    return None


def first_version(text: str) -> str:
    match = VERSION_RE.search(text)
    return match.group(0) if match else ""


def current_version_section(text: str) -> str:
    match = re.search(r"^##\s+Current Version\s*$", text, flags=re.MULTILINE)
    if not match:
        return ""
    rest = text[match.end() :]
    next_section = re.search(r"^##\s+", rest, flags=re.MULTILINE)
    return rest[: next_section.start()] if next_section else rest


def project_skill_version(project: Path, skill_dir_raw: str | Path | None = None) -> tuple[str, str, Path | None]:
    skill_dir = inferred_skill_dir(project, skill_dir_raw)
    if not skill_dir:
        return "", "unavailable", None
    version = read_skill_version(skill_dir)
    if not version:
        return "", "unavailable", skill_dir
    return version, "project-skill", skill_dir


def version_alignment_gate(project: Path, skill_dir_raw: str | Path | None = None) -> dict[str, Any]:
    expected, version_source, skill_dir = project_skill_version(project, skill_dir_raw)
    checked: list[str] = []
    errors: list[str] = []
    if not expected:
        return {
            "project": str(project),
            "skill_dir": str(skill_dir) if skill_dir else "",
            "expected_version": "",
            "version_source": version_source,
            "checked": checked,
            "errors": [],
            "ok": True,
            "skipped": "no skill VERSION found",
        }
    checked.append(str((skill_dir / "VERSION").relative_to(project).as_posix()) if skill_dir.is_relative_to(project) else str(skill_dir / "VERSION"))

    agents = project / "AGENTS.md"
    if agents.is_file():
        checked.append("AGENTS.md")
        agents_text = agents.read_text(encoding="utf-8", errors="ignore")
        control_match = re.search(r"^-\s+Version:\s*(v\d+\.\d+\.\d+)", agents_text, flags=re.MULTILINE)
        if control_match and control_match.group(1) != expected:
            errors.append(
                f"AGENTS.md control profile version {control_match.group(1)} does not match project skill VERSION {expected}"
            )

    docs_checks = [
        ("docs/development/DEVELOPMENT.md", "development record"),
        ("docs/git_manager/CHANGELOG.md", "changelog"),
    ]
    for rel_path, label in docs_checks:
        path = project / rel_path
        if not path.is_file():
            continue
        checked.append(rel_path)
        actual = first_version(path.read_text(encoding="utf-8", errors="ignore"))
        if actual and actual != expected:
            errors.append(f"{rel_path} {label} version {actual} does not match project skill VERSION {expected}")

    git_manager = project / "docs" / "git_manager" / "GIT_MANAGER.md"
    if git_manager.is_file():
        checked.append("docs/git_manager/GIT_MANAGER.md")
        actual = first_version(current_version_section(git_manager.read_text(encoding="utf-8", errors="ignore")))
        if actual and actual != expected:
            errors.append(
                f"docs/git_manager/GIT_MANAGER.md current version {actual} does not match project skill VERSION {expected}"
            )

    return {
        "project": str(project),
        "skill_dir": str(skill_dir),
        "expected_version": expected,
        "version_source": version_source,
        "checked": checked,
        "errors": errors,
        "ok": not errors,
    }


def sync_root_agents(
    project: Path,
    write: bool = False,
    installed_skill_dir_override: str | Path | None = None,
    *,
    mark_verified: bool = False,
) -> dict[str, Any]:
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

    if write and (sync_required or mark_verified):
        new_last_updated = current_timestamp()
        updated_raw = new_last_updated if sync_required or not last_updated_raw else last_updated_raw
        verified_raw = current_timestamp() if mark_verified else last_verified
        new_last_line = f"<!-- Last updated: {updated_raw} | Last verified: {verified_raw} -->"
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
        "mark_verified": mark_verified,
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
    version_result = version_alignment_gate(project)
    checked.extend(version_result["checked"])
    errors.extend(version_result["errors"])
    for legacy in [project / "HANDOFF.md", project / "DEVELOPMENT.md", project / "experience", project / "docs" / "HANDOFF.md", project / "docs" / "DEVELOPMENT.md"]:
        if legacy.exists():
            try:
                errors.append(f"legacy docs path must be migrated into governed docs layout: {legacy.relative_to(project).as_posix()}")
            except ValueError:
                errors.append(f"legacy docs path must be migrated into governed docs layout: {legacy}")
    return {"project": str(project), "checked": checked, "errors": errors}


def run_json_command(project: Path, argv: list[str]) -> dict[str, Any]:
    result = subprocess.run(argv, cwd=project, text=True, capture_output=True, check=False, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    parsed: dict[str, Any]
    try:
        loaded = json.loads(result.stdout)
        parsed = loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        parsed = {}
    return {
        "argv": argv,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "json": parsed,
    }


def work_folder_gate(project: Path, skill_dir_raw: str, mode: str = "development") -> dict[str, Any]:
    from manage_dirs import structure_gate
    from manage_docs_scaffold_session import resume_check
    from manage_docs_release import branch_gate

    skill_dir = inferred_skill_dir(project, skill_dir_raw)
    resume = resume_check(project)
    structure = structure_gate(project)
    dir_manager = verify_dir_manager(project)
    branch = branch_gate(project)
    version = version_alignment_gate(project, skill_dir)
    source_governance = source_governance_report(project, control_profile(project))
    freshness_command = run_json_command(project, [sys.executable, str(Path(__file__).resolve().parent / "check_freshness.py"), str(project)])
    freshness = freshness_command["json"]
    errors: list[str] = []
    resume_policy = {
        "blocking": False,
        "reason": "work-folder-gate reports active-session state but does not block the current in-progress session; run resume-check before starting new work.",
    }
    if not structure.get("approved", True):
        errors.extend(f"structure-gate: {item}" for item in structure.get("reasons", []))
    errors.extend(f"dir-manager: {item}" for item in dir_manager.get("errors", []))
    if not branch.get("approved", True):
        errors.extend(f"branch-gate: {item}" for item in branch.get("reasons", []))
    errors.extend(f"version-gate: {item}" for item in version.get("errors", []))
    errors.extend(format_source_governance_errors(source_governance, prefix="source-governance"))
    if freshness_command["returncode"] != 0:
        errors.append("check_freshness command failed")
    if freshness.get("stale") is True:
        errors.append("AGENTS.md freshness check is stale")
    if mode == "release" and not skill_dir:
        errors.append("release work-folder gate requires a resolved skill directory")
    return {
        "project": str(project),
        "mode": mode,
        "skill_dir": str(skill_dir) if skill_dir else "",
        "ok": not errors,
        "errors": errors,
        "resume_check": resume,
        "resume_policy": resume_policy,
        "structure_gate": structure,
        "dir_manager": dir_manager,
        "branch_gate": branch,
        "version_gate": version,
        "source_governance": source_governance,
        "freshness": freshness,
    }
