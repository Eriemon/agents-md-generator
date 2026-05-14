from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any
import zipfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import codex_sessions_root, display_path, emit_json, inspect_project, matched_codex_sessions, read_json, read_skill_version, resolve_project, session_message_rows
from manage_dirs import init_dir_manager, verify_dir_manager


DOC_DIRS = [
    "docs/handoff",
    "docs/handoff/history_handoff",
    "docs/experience",
    "docs/experience/history_experience",
    "docs/development",
    "docs/development/history_development",
    "docs/install_configuration",
    "docs/git_manager",
    "docs/git_manager/history_git_manager",
    "docs/dir_manager",
    "docs/dir_manager/change_reviews",
    "docs/dir_manager/history_dir_manager",
]
REQUIRED_DOC_FILES = [
    "docs/handoff/HANDOFF.md",
    "docs/development/DEVELOPMENT.md",
    "docs/install_configuration/INSTALL_CONFIGURATION.md",
    "docs/git_manager/GIT_MANAGER.md",
    "docs/git_manager/CHANGELOG.md",
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
EVOLUTION_REQUEST_PATH = ".agents/evolution-update-request.json"
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
REQUIRED_EXPERIENCE_SECTIONS = [
    "Evidence Read",
    "Task Context",
    "How To Apply",
    "Problems And Risks",
    "Iterated Lessons",
    "Next Application",
]
EXPERIENCE_MIN_LENGTH = 900
WORKFLOW_EXPERIENCE_MIN_LENGTH = 1600
REQUIRED_EVOLUTION_SECTIONS = [
    "Evidence Sources",
    "Applicable Scenario",
    "Distilled Workflow",
    "Key Decisions",
    "Common Problems",
    "Non-Reusable Content",
    "Application Checklist",
]
EVOLUTION_SUMMARY_MIN_LENGTH = 450
EXPERIENCE_CADENCE_HANDOFFS = 5
EVOLUTION_CADENCE_HANDOFFS = 10
SAFE_TEMPLATE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
REQUIRED_DEVELOPMENT_SECTIONS = [
    "Development Goal",
    "Full Development Plan",
    "Current Progress",
    "Completed Scope",
    "Remaining Scope",
    "Key Problems And Risks",
    "Resolution Strategy And Next Steps",
    "Development Result",
    "Verification",
    "Artifacts And Impact",
]
DEVELOPMENT_MIN_LENGTH = 450
TOPIC_DETAIL_RULES: dict[str, dict[str, Any]] = {
    "2-scripts.md": {
        "guidance": [
            "Name the exact script, CLI command, function, JSON contract, or code path that changed.",
            "Explain the state transition or validation boundary the script owns, and include the verification command that proved the change.",
        ],
        "required_term_groups": [
            ("script", "scripts", "cli", "python", "manage_docs.py", "render_agents.py", "audit_skill.py", "json"),
            ("command", "function", "state transition", "state transitions", "validation", "validation boundary", "code path", "file path"),
        ],
        "error": "content must include script-specific implementation evidence",
    },
    "3-plan.md": {
        "guidance": [
            "Describe the concrete plan, sequencing, handoff boundary, or acceptance criteria that shaped the work.",
            "Record which failure mode or requirement forced the plan to change before implementation or release.",
        ],
        "required_terms": ("plan", "planning", "task", "sequence", "handoff", "acceptance", "scope", "steps"),
        "minimum_matches": 2,
        "error": "content must include planning-specific evidence",
    },
    "5-testing.md": {
        "guidance": [
            "Record the focused tests, regression checks, or fixtures that proved the old behavior failed and the new behavior passed.",
            "Call out the verification command, expected failure, or assertion surface that protects this topic.",
        ],
        "required_terms": ("test", "tests", "testing", "pytest", "unittest", "regression", "assert", "verification", "fixture"),
        "minimum_matches": 2,
        "error": "content must include testing-specific verification evidence",
    },
    "6-validation.md": {
        "guidance": [
            "Name the validation gate, verify command, or quality check that determines whether the repository is healthy.",
            "Explain why this validation matters and which failure it prevents from leaking downstream.",
        ],
        "required_terms": ("validate", "validation", "verify", "gate", "quality", "errors", "warnings"),
        "minimum_matches": 2,
        "error": "content must include validation-specific gate evidence",
    },
    "7-release.md": {
        "guidance": [
            "Mention the release artifact, dist package, versioned output, or parity check that mattered for this task.",
            "Include the release-specific failure mode, rebuild requirement, or packaging verification step.",
        ],
        "required_terms": ("release", "dist", "package", "zip", "version", "artifact", "parity"),
        "minimum_matches": 2,
        "error": "content must include release-specific artifact evidence",
    },
    "8-installation.md": {
        "guidance": [
            "Explain the installation target, replacement behavior, backup path, or conflict-preservation rule involved in the task.",
            "Document the install-specific guardrails so future replacement work does not overwrite durable user state.",
        ],
        "required_terms": ("install", "installation", "replace", "backup", "conflict", "codex", "target"),
        "minimum_matches": 2,
        "error": "content must include installation-specific evidence",
    },
    "9-docs-governance.md": {
        "guidance": [
            "Name the docs governance workflow, such as handoff rotation, experience cadence, request/payload flow, or governance state repair.",
            "Record the relevant docs path or governance state transition that future maintainers must preserve.",
        ],
        "required_term_groups": [
            ("docs/experience", "docs/handoff", "handoff", "experience update", "governance state"),
            ("governance", "cadence", "request", "payload", "rotation", "archive"),
        ],
        "error": "content must include docs-governance-specific evidence",
    },
    "10-directory-governance.md": {
        "guidance": [
            "Call out the directory structure, folder review, path movement, or archive behavior that constrained the task.",
            "Explain the directory-specific risk so future structure changes can be reviewed before mutation.",
        ],
        "required_terms": ("directory", "directories", "folder", "folders", "path", "paths", "structure", "review"),
        "minimum_matches": 2,
        "error": "content must include directory-governance-specific evidence",
    },
}
EVOLUTION_CATEGORY_SCHEMAS: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {
    ("skill-template", ("agent-governance",)): {
        "flow_requirements": [
            "Workflow must show repository fact inspection or control-profile inspection before synthesis.",
            "Workflow must cover rule/design alignment for AGENTS or agent-governance behavior.",
            "Workflow must cover script/test/verify style execution before final docs governance output.",
            "Workflow must mention release or install decision handling when summarizing reusable skill-governance flow.",
        ],
        "mixed_content_risks": [
            "Do not copy FPGA/Vivado/HLS/XDC/bitstream engineering flows into an agent-governance skill template.",
            "Do not turn the template into a hardware execution checklist when the target is a skill-governance workflow.",
        ],
        "workflow_required_groups": [
            ("repository facts", "fact inspection", "control profile", "inspect facts"),
            ("agents.md", "agent rule", "rule alignment", "design alignment", "docs governance"),
            ("script", "scripts", "test", "verify", "validation"),
            ("release", "install", "installation"),
        ],
        "workflow_forbidden_terms": (
            "engineering tcl",
            "hls",
            "verilog",
            "xdc",
            "bitstream",
            "timing closure",
            "download validation",
            "vivado",
        ),
    },
    ("skill-template", ("docs-governance",)): {
        "flow_requirements": [
            "Workflow must cover handoff rotation, experience cadence, request/payload flow, and verification.",
            "Workflow must keep current docs, history docs, and reusable outputs distinct.",
        ],
        "mixed_content_risks": [
            "Do not replace docs-governance flow with product-engineering execution stages.",
        ],
        "workflow_required_groups": [
            ("handoff", "docs governance", "experience cadence", "request", "payload"),
            ("verify", "validation", "archive", "history"),
        ],
        "workflow_forbidden_terms": ("bitstream", "xdc", "hls", "vivado"),
    },
    ("engineering-template", ("docs-governance",)): {
        "flow_requirements": [
            "Workflow must cover handoff rotation, experience cadence, request/payload flow, and repository verification for an engineering workspace.",
            "Workflow must keep current docs, history docs, and reusable outputs distinct while still treating the repository as an engineering project.",
        ],
        "mixed_content_risks": [
            "Do not replace engineering docs-governance flow with FPGA/algorithm execution chains.",
        ],
        "workflow_required_groups": [
            ("handoff", "docs governance", "experience cadence", "request", "payload"),
            ("verify", "validation", "archive", "history"),
        ],
        "workflow_forbidden_terms": ("bitstream", "xdc", "hls", "vivado"),
    },
    ("engineering-template", ("FPGA",)): {
        "flow_requirements": [
            "Workflow must cover design/develop/simulate/synthesize/implement/validate FPGA stages.",
            "Workflow must mention hardware-specific artifacts or closure steps such as XDC, bitstream, timing, or download validation.",
        ],
        "mixed_content_risks": [
            "Do not replace engineering execution with AGENTS/control-profile/docs-governance skill steps.",
        ],
        "workflow_required_groups": [
            ("design", "规划", "architecture"),
            ("develop", "implementation", "开发", "hls", "verilog"),
            ("simulation", "simulate", "仿真", "test"),
            ("synthesis", "implement", "implementation", "综合"),
            ("bitstream", "timing", "xdc", "download validation", "验证"),
        ],
        "workflow_forbidden_terms": (
            "agents.md",
            "control profile",
            "docs governance",
            "handoff cadence",
            "install confirmation",
        ),
    },
    ("engineering-template", ("algorithm",)): {
        "flow_requirements": [
            "Workflow must cover requirement/design/implementation/test or correctness validation.",
            "Workflow must mention algorithm-oriented validation such as correctness, benchmark, performance, or complexity.",
        ],
        "mixed_content_risks": [
            "Do not replace algorithm engineering flow with AGENTS/docs-governance skill operations.",
        ],
        "workflow_required_groups": [
            ("requirement", "requirements", "需求"),
            ("design", "设计", "plan"),
            ("implement", "implementation", "develop", "开发"),
            ("test", "testing", "验证", "correctness"),
            ("performance", "benchmark", "complexity", "sort", "sorting", "性能"),
        ],
        "workflow_forbidden_terms": (
            "agents.md",
            "control profile",
            "docs governance",
            "handoff cadence",
            "install confirmation",
            "skill install",
        ),
    },
    ("engineering-template", ("web", "frontend")): {
        "flow_requirements": [
            "Workflow must cover UI/frontend design, implementation, testing, and responsive or accessibility validation.",
        ],
        "mixed_content_risks": [
            "Do not replace frontend flow with AGENTS/docs-governance maintenance steps.",
        ],
        "workflow_required_groups": [
            ("design", "layout", "ui", "frontend"),
            ("implement", "development", "develop", "开发"),
            ("test", "validation", "responsive", "accessibility"),
        ],
        "workflow_forbidden_terms": ("agents.md", "control profile", "docs governance", "handoff cadence"),
    },
    ("engineering-template", ("backend", "api")): {
        "flow_requirements": [
            "Workflow must cover API/backend design, implementation, test, and runtime or integration validation.",
        ],
        "mixed_content_risks": [
            "Do not replace backend execution flow with skill-governance maintenance steps.",
        ],
        "workflow_required_groups": [
            ("api", "backend", "service", "interface"),
            ("implement", "development", "develop", "开发"),
            ("test", "validation", "integration", "runtime"),
        ],
        "workflow_forbidden_terms": ("agents.md", "control profile", "docs governance", "handoff cadence"),
    },
    ("engineering-template", ("data", "database")): {
        "flow_requirements": [
            "Workflow must cover schema/query/data implementation plus validation or migration/runtime checks.",
        ],
        "mixed_content_risks": [
            "Do not replace data/database flow with skill-governance maintenance steps.",
        ],
        "workflow_required_groups": [
            ("data", "database", "sql", "schema"),
            ("implement", "development", "develop", "query"),
            ("test", "validation", "migration", "runtime"),
        ],
        "workflow_forbidden_terms": ("agents.md", "control profile", "docs governance", "handoff cadence"),
    },
    ("skill-template", ("general",)): {
        "flow_requirements": [
            "Workflow must still reflect a skill/repository-governance style process rather than a product-engineering execution chain.",
        ],
        "mixed_content_risks": [
            "Do not copy specialized engineering execution chains into a general skill template.",
        ],
        "workflow_required_groups": [
            ("repository facts", "control profile", "facts", "inspect"),
            ("script", "test", "verify", "docs"),
        ],
        "workflow_forbidden_terms": ("hls", "verilog", "xdc", "bitstream", "timing closure"),
    },
    ("engineering-template", ("general",)): {
        "flow_requirements": [
            "Workflow must reflect engineering execution stages rather than AGENTS/docs-governance repository maintenance.",
        ],
        "mixed_content_risks": [
            "Do not copy AGENTS/control-profile/docs-governance flow into a general engineering template.",
        ],
        "workflow_required_groups": [
            ("design", "implement", "develop", "test"),
            ("validate", "verification", "runtime", "release"),
        ],
        "workflow_forbidden_terms": ("agents.md", "control profile", "docs governance", "handoff cadence"),
    },
}


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def docs_root(project: Path) -> Path:
    return project / "docs"


def git_manager_root(project: Path) -> Path:
    return docs_root(project) / "git_manager"


def git_changelog_file(project: Path) -> Path:
    return git_manager_root(project) / "CHANGELOG.md"


def git_history_root(project: Path) -> Path:
    return git_manager_root(project) / "history_git_manager"


def state_file(project: Path) -> Path:
    return project / STATE_PATH


def active_session_file(project: Path) -> Path:
    return project / ACTIVE_SESSION_PATH


def experience_request_file(project: Path) -> Path:
    return project / EXPERIENCE_REQUEST_PATH


def evolution_request_file(project: Path) -> Path:
    return project / EVOLUTION_REQUEST_PATH


def conversation_snapshot_dir(project: Path) -> Path:
    return project / CONVERSATION_SNAPSHOT_DIR


def load_state(project: Path) -> dict[str, Any]:
    state = read_json(state_file(project))
    return state if isinstance(state, dict) else {}


def save_state(project: Path, state: dict[str, Any]) -> None:
    agents_dir = project / ".agents"
    agents_dir.mkdir(exist_ok=True)
    state_file(project).write_text(json.dumps(state, indent=2, sort_keys=True, default=str), encoding="utf-8")


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


def cadence_checkpoint(count: int, interval: int) -> int:
    if count <= 0 or interval <= 0:
        return 0
    return (count // interval) * interval


def latest_experience_due(count: int) -> int:
    return cadence_checkpoint(count, EXPERIENCE_CADENCE_HANDOFFS)


def latest_evolution_due(count: int) -> int:
    return cadence_checkpoint(count, EVOLUTION_CADENCE_HANDOFFS)


def cadence_window_bounds(checkpoint: int, interval: int) -> tuple[int, int]:
    if checkpoint <= 0:
        return 0, 0
    return max(1, checkpoint - interval + 1), checkpoint


def handoff_count_from_markdown(text: str) -> int:
    match = re.search(r"^- Handoff count:\s*(\d+)\s*$", text, flags=re.MULTILINE)
    return int(match.group(1)) if match else 0


def current_handoff_entry(project: Path) -> dict[str, Any] | None:
    path = project / "docs" / "handoff" / "HANDOFF.md"
    if not path.exists() or not path.is_file():
        return None
    content = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "path": path.relative_to(project).as_posix(),
        "content": content,
        "handoff_count": handoff_count_from_markdown(content),
    }


def handoff_window(project: Path, checkpoint: int, limit: int = EXPERIENCE_CADENCE_HANDOFFS) -> dict[str, Any]:
    start, end = cadence_window_bounds(checkpoint, limit)
    if end == 0:
        return {"start_handoff_count": 0, "end_handoff_count": 0, "entries": []}
    entries: list[dict[str, Any]] = []
    current = current_handoff_entry(project)
    if current:
        entries.append(current)
    entries.extend(recent_handoff_history(project, limit=max(limit * 3, 10)))
    deduped: dict[int, dict[str, Any]] = {}
    for row in entries:
        handoff_count = int(row.get("handoff_count", 0))
        if start <= handoff_count <= end and handoff_count not in deduped:
            deduped[handoff_count] = row
    return {
        "start_handoff_count": start,
        "end_handoff_count": end,
        "entries": [deduped[key] for key in sorted(deduped)],
    }


def recent_conversation_window(project: Path, limit: int = EXPERIENCE_CADENCE_HANDOFFS) -> dict[str, Any]:
    entries = recent_conversation_context(project, limit=limit)
    return {
        "count": len(entries),
        "limit": limit,
        "entries": entries,
    }


def detail_requirements_for(filename: str) -> list[str]:
    rule = TOPIC_DETAIL_RULES.get(filename, {})
    guidance = rule.get("guidance")
    if isinstance(guidance, list) and guidance:
        return [str(item) for item in guidance]
    return [
        "Name the exact files, implementation surface, and task-specific boundary that changed.",
        "Explain the main risk or failure mode, then record the verification evidence and future reuse condition.",
    ]


def contains_term(text: str, term: str) -> bool:
    lowered = text.lower()
    needle = term.lower().strip()
    if not needle:
        return False
    if re.fullmatch(r"[A-Za-z0-9_-]+(?: [A-Za-z0-9_-]+)*", needle):
        return re.search(rf"\b{re.escape(needle)}\b", lowered) is not None
    return needle in lowered


def count_term_matches(text: str, terms: tuple[str, ...]) -> int:
    return sum(1 for term in terms if contains_term(text, term))


def validate_topic_specificity(filename: str, content: str) -> list[str]:
    rule = TOPIC_DETAIL_RULES.get(filename)
    if not rule:
        return []
    errors: list[str] = []
    lowered = content.lower()
    required_groups = rule.get("required_term_groups")
    if isinstance(required_groups, list) and required_groups:
        for group in required_groups:
            if isinstance(group, tuple) and not any(contains_term(content, term) for term in group):
                errors.append(f"{filename}: {rule['error']}")
                return errors
        return errors
    required_terms = rule.get("required_terms")
    minimum_matches = int(rule.get("minimum_matches", 1))
    if isinstance(required_terms, tuple) and count_term_matches(content, required_terms) < minimum_matches:
        errors.append(f"{filename}: {rule['error']}")
    return errors


def experience_metadata_block(project: Path, checkpoint: int) -> list[str]:
    start, end = cadence_window_bounds(checkpoint, EXPERIENCE_CADENCE_HANDOFFS)
    conversation = recent_conversation_window(project)
    handoffs = handoff_window(project, checkpoint)
    return [
        f"- Experience cadence: {checkpoint}",
        f"- Covered handoff window: {start}-{end}",
        f"- Source handoff count: {len(handoffs['entries'])}",
        f"- Source conversation count: {conversation['count']}",
        f"- Applied at: {datetime.now().isoformat(timespec='seconds')}",
    ]


def with_experience_metadata(project: Path, content: str, checkpoint: int) -> str:
    lines = content.rstrip().splitlines()
    title = lines[0] if lines and lines[0].startswith("# ") else "# Experience"
    body = lines[1:] if lines and lines[0].startswith("# ") else lines
    while body and not body[0].strip():
        body = body[1:]
    result = [title, ""]
    result.extend(experience_metadata_block(project, checkpoint))
    result.append("")
    result.extend(body)
    return "\n".join(result).rstrip() + "\n"


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
        "- When replacing an installed skill, first move the old skill to the sibling `skill_backups/<skill-name>-YYYYMMDD-HHMMSS/` folder.",
        "- Never delete installed `assets/templates/evolution/engineering-template` or `assets/templates/evolution/skill-template` content during installation.",
        "- If evolved template content conflicts, preserve both versions and report the conflict for manual merge.",
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


def default_git_changelog() -> str:
    return "\n".join([
        "# Change Log",
        "",
        "- Version: not recorded",
        "- Generated at: not recorded",
        "- Summary: not recorded",
        "",
        "## Changes",
        "- Record the staged or committed changes for this release or commit here before the next commit.",
        "",
        "## Verification",
        "- Record the exact validation commands or evidence used for this change set.",
        "",
    ])


def default_development_record() -> str:
    return "\n".join([
        "# Development Stage: not recorded",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "- Version: not recorded",
        "- Status: not recorded",
        "",
        "## Development Goal",
        "- Not recorded.",
        "",
        "## Full Development Plan",
        "- Not recorded.",
        "",
        "## Current Progress",
        "- Not recorded.",
        "",
        "## Completed Scope",
        "- Not recorded.",
        "",
        "## Remaining Scope",
        "- Not recorded.",
        "",
        "## Key Problems And Risks",
        "- Not recorded.",
        "",
        "## Resolution Strategy And Next Steps",
        "- Not recorded.",
        "",
        "## Development Result",
        "- Not recorded.",
        "",
        "## Verification",
        "- Not recorded.",
        "",
        "## Artifacts And Impact",
        "- Not recorded.",
        "",
    ])


def validate_development_record(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    if "# Development Stage: not recorded" in text and "- Version: not recorded" in text and "- Status: not recorded" in text:
        return errors
    for section in REQUIRED_DEVELOPMENT_SECTIONS:
        if not re.search(rf"^##\s+{re.escape(section)}\s*$", text, flags=re.MULTILINE):
            errors.append(f"{path.relative_to(path.parents[2]).as_posix()}: missing section ## {section}")
    if "- Status: not recorded" in text:
        errors.append(f"{path.relative_to(path.parents[2]).as_posix()}: development status is still placeholder text")
    if len(text.strip()) < DEVELOPMENT_MIN_LENGTH:
        errors.append(f"{path.relative_to(path.parents[2]).as_posix()}: development record is too short")
    return errors


def git_manager_doc() -> str:
    return "\n".join([
        "# Git Manager",
        "",
        "## Workspace Management",
        "- Keep current development work in the working folder unless the user requests a separate worktree.",
        "- Do not repoint repositories with `git config core.worktree`; prefer normal branch checkout/merge or explicit `git worktree` commands when separate work folders are required.",
        "",
        "## Branch Configuration",
        "- Protected branches: `master`, `release`.",
        "- Development branches are allowed as temporary local work branches.",
        "- Before releasing an installable `dist/` package, commit all work and merge development branches into `master`.",
        "- Use `python scripts/manage_docs.py release-prepare <project> --version vX.Y.Z --skill-dir skills/<skill-name>` to auto-commit governed paths from the active temporary branch, merge it into `master`, and delete the local branch before packaging.",
        "- If a branch has unmerged commits, merge it to `master` before cleanup; never discard it silently.",
        "- After release preparation, delete local branches other than `master` and `release`.",
        "- Do not delete remote branches unless the user explicitly requests remote cleanup.",
        "- Run `python scripts/manage_docs.py release-gate <project> --version vX.Y.Z --skill-dir skills/<skill-name> --phase pre|post` before and after packaging to verify branch, worktree, release artifact, release receipt, and parity gates.",
        "",
        "## Release Configuration",
        "- Place installable releases under `dist/`.",
        "- Name installable release folders as `<name>-vx.x.x` and create a matching zip when required.",
        "- Build installable releases with `python scripts/manage_docs.py package-release <project> --version vX.Y.Z --skill-dir skills/<skill-name>` so the versioned release directory, matching zip, and `RELEASE_RECEIPT.json` provenance stay aligned.",
        "- Install only from the versioned release directory after receipt validation; never install directly from the source skill folder.",
        "- Package only after branch cleanup and release records are complete.",
        "- The release commit must include the release artifacts and the current `docs/git_manager/CHANGELOG.md` entry.",
        "- If the release is for a skill project and the user did not explicitly say whether to install after release, release handling must ask the install question instead of silently stopping. Engineering projects must not ask to install a skill.",
        "",
        "## Change Log",
        "- Update `docs/git_manager/CHANGELOG.md` before each commit that changes governed release or git-management behavior.",
        "- Archive the previous `CHANGELOG.md` to `docs/git_manager/history_git_manager/YYYYMMDD-HHMMSS/CHANGELOG.md` before writing the next current entry.",
        "- Use `python scripts/manage_docs.py git-changelog <project> --input changelog.json` to rotate and write the current change summary.",
        "",
        "## Current Version",
        "- Record the active version here during release preparation and keep detailed changes in `CHANGELOG.md`.",
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


def scaffold(project: Path) -> dict[str, Any]:
    created: list[str] = []
    for rel_path in DOC_DIRS:
        path = project / rel_path
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created.append(rel_path)
    migrated = migrate_legacy_docs(project)
    files = {
        "docs/handoff/HANDOFF.md": default_handoff(),
        "docs/development/DEVELOPMENT.md": default_development_record(),
        "docs/install_configuration/INSTALL_CONFIGURATION.md": install_configuration_doc(),
        "docs/git_manager/GIT_MANAGER.md": git_manager_doc(),
        "docs/git_manager/CHANGELOG.md": default_git_changelog(),
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
    return {"project": str(project), "created": created, "migrated": migrated, "state": state}


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
    conversations = recent_conversation_context(project, limit=10)
    handoff_window_payload = handoff_window(project, checkpoint)
    conversation_window_payload = recent_conversation_window(project)
    return {
        "schema_version": 1,
        "project": str(project),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "handoff_count": count,
        "cadence_checkpoint": checkpoint,
        "requires_ai_generation": True,
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


def write_experience_request(project: Path, count: int) -> dict[str, Any]:
    request = build_experience_request(project, count)
    target = experience_request_file(project)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    state = load_state(project)
    state["experience_update_required"] = True
    state["experience_request_due_at"] = int(request.get("cadence_checkpoint", count))
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
        summary.strip(),
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
    quality_errors = validate_current_experience_quality(project, include_evolution_cadence=False)
    if quality_errors:
        return {"project": str(project), "skipped": True, "errors": quality_errors, "reason": "experience quality gate failed"}
    target_raw = state.get("last_evolution_target")
    target, target_errors = normalize_evolution_target(project, target_raw if isinstance(target_raw, dict) else None)
    if target_errors:
        return {"project": str(project), "skipped": True, "errors": target_errors, "reason": "evolution target validation failed"}
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
    state["last_evolution_at"] = checkpoint
    save_state(project, state)
    return {"project": str(project), "written": written, "archived": archived, "handoff_count": checkpoint, "index": str(index_path), "target": target}


def apply_experience_payload(project: Path, payload_path: str) -> dict[str, Any]:
    scaffold(project)
    state = load_state(project)
    count = int(state.get("handoff_count", 0))
    checkpoint = latest_experience_due(count) or count
    requires_atomic_evolution = checkpoint >= EVOLUTION_CADENCE_HANDOFFS and checkpoint % EVOLUTION_CADENCE_HANDOFFS == 0
    payload = read_input(payload_path)
    entries, errors = validate_experience_payload(project, payload)
    target, target_errors = normalize_evolution_target(project, payload.get("evolution_target") if "evolution_target" in payload else None)
    errors.extend(target_errors)
    summaries = payload_evolution_summary(payload)
    if requires_atomic_evolution and not summaries:
        errors.append("evolution_summary is required before writing reusable templates")
    if summaries:
        errors.extend(validate_evolution_summaries(project, summaries, target))
    if errors:
        return {"project": str(project), "errors": errors}
    archived = archive_experience_files(project)
    written: list[str] = []
    for spec in experience_file_specs(project):
        target = project / "docs" / "experience" / spec["filename"]
        target.write_text(with_experience_metadata(project, entries[spec["filename"]], checkpoint), encoding="utf-8")
        written.append(str(target))
    state["last_experience_at"] = checkpoint
    state["experience_update_required"] = False
    state.pop("experience_request_due_at", None)
    payload_resolved = Path(payload_path).resolve()
    try:
        state["last_experience_payload"] = payload_resolved.relative_to(project).as_posix()
    except ValueError:
        state["last_experience_payload"] = payload_resolved.name
    state["last_evolution_target"] = target
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
    return result


def write_experience(project: Path, force: bool = False, payload_path: str | None = None) -> dict[str, Any]:
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


def validate_current_experience_quality(project: Path, *, include_evolution_cadence: bool = True) -> list[str]:
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


def run_git(project: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)


def git_ok(project: Path, args: list[str]) -> tuple[bool, str]:
    result = run_git(project, args)
    return result.returncode == 0, (result.stdout or result.stderr).strip()


def governed_allowed_paths(profile: dict[str, Any], skill_dir: Path, project: Path) -> list[str]:
    policy = profile.get("git_branch_policy", {}) if isinstance(profile.get("git_branch_policy"), dict) else {}
    configured = policy.get("release_prepare_allowed_paths")
    if isinstance(configured, list) and configured:
        return [str(item).replace("\\", "/").strip().strip("/") for item in configured if str(item).strip()]
    rel_skill = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else skill_dir.name
    return [rel_skill, "tests", "docs", ".agents", "AGENTS.md", "dist"]


def receipt_filename(profile: dict[str, Any]) -> str:
    release = profile.get("release_contract", {}) if isinstance(profile.get("release_contract"), dict) else {}
    value = str(release.get("receipt_file", "RELEASE_RECEIPT.json")).strip()
    return value or "RELEASE_RECEIPT.json"


def matches_governed_path(path: str, allowed: list[str]) -> bool:
    normalized = path.replace("\\", "/").strip().lstrip("./")
    for prefix in allowed:
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return True
    return False


def parse_status_paths(line: str) -> list[str]:
    body = line[3:].strip() if len(line) >= 4 else line.strip()
    if " -> " in body:
        old_path, new_path = body.split(" -> ", 1)
        return [old_path.strip().replace("\\", "/"), new_path.strip().replace("\\", "/")]
    return [body.replace("\\", "/")]


def changed_paths(project: Path) -> tuple[list[str], list[str]]:
    status = run_git(project, ["status", "--short"])
    if status.returncode != 0:
        return [], ["git status --short failed"]
    paths: list[str] = []
    for line in status.stdout.splitlines():
        if not line.strip():
            continue
        paths.extend(parse_status_paths(line))
    return sorted(set(path for path in paths if path)), []


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_release_file_manifest(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, str]]:
    excluded = exclude or set()
    manifest: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        manifest.append({"path": relative, "sha256": sha256_file(path)})
    return manifest


def write_release_zip(release_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(release_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(release_dir.parent).as_posix())


def read_release_receipt(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def verify_release_receipt(project: Path, receipt_path: Path, release_dir: Path, skill_name: str, version: str, source_rel: str, *, require_repo_dist: bool) -> list[str]:
    receipt = read_release_receipt(receipt_path)
    errors: list[str] = []
    if not receipt:
        return [f"invalid release receipt: {display_path(receipt_path, project)}"]
    if str(receipt.get("skill_name", "")).strip() != skill_name:
        errors.append("release receipt skill_name does not match release directory")
    if str(receipt.get("version", "")).strip() != version:
        errors.append("release receipt version does not match requested release version")
    if str(receipt.get("source_path", "")).strip().replace("\\", "/") != source_rel:
        errors.append("release receipt source_path does not match skill source path")
    expected_validation = "strong" if require_repo_dist else "reduced_assurance"
    if str(receipt.get("validation_level", "")).strip() != expected_validation:
        errors.append("release receipt validation_level is inconsistent with the release source")
    expected_files = build_release_file_manifest(release_dir, exclude={receipt_path.name})
    actual_files = receipt.get("files")
    if not isinstance(actual_files, list):
        errors.append("release receipt files list is missing")
    else:
        filtered = []
        for item in actual_files:
            if not isinstance(item, dict):
                errors.append("release receipt files list contains invalid entries")
                continue
            filtered.append({"path": str(item.get("path", "")).strip(), "sha256": str(item.get("sha256", "")).strip()})
        if filtered != expected_files:
            errors.append("release receipt file manifest does not match packaged release contents")
    return errors


def current_branch_and_locals(project: Path) -> tuple[str, list[str], list[str]]:
    git_branch_result = run_git(project, ["branch", "--show-current"])
    git_list_result = run_git(project, ["branch", "--list"])
    git_status_result = run_git(project, ["status", "--short"])
    if any(result.returncode != 0 for result in [git_branch_result, git_list_result, git_status_result]):
        return "", [], []
    current_branch = git_branch_result.stdout.strip()
    local_branches = sorted(line.strip().lstrip("* ").strip() for line in git_list_result.stdout.splitlines() if line.strip())
    status_lines = [line for line in git_status_result.stdout.splitlines() if line.strip()]
    return current_branch, local_branches, status_lines


def release_prepare(project: Path, version: str, skill_dir_raw: str) -> dict[str, Any]:
    profile = read_json(project / ".agents" / "agents-control.json")
    skill_dir = resolve_project(skill_dir_raw if Path(skill_dir_raw).is_absolute() else project / skill_dir_raw)
    current_branch, local_branches, status_lines = current_branch_and_locals(project)
    protected = sorted((profile.get("git_branch_policy", {}) or {}).get("protected_branches", ["master", "release"]))
    extras = sorted(branch for branch in local_branches if branch not in protected)
    errors: list[str] = []
    checks: dict[str, Any] = {
        "current_branch": current_branch,
        "local_branches": local_branches,
        "protected_branches": protected,
        "prepared_branch": "",
    }
    if not current_branch and not local_branches:
        errors.append("release prepare requires a readable local git repository")
        return {"ok": False, "errors": errors, "checks": checks}
    if current_branch == "master":
        if len(extras) > 1:
            errors.append(f"multiple extra local branches require manual resolution before release prepare: {extras}")
        elif len(extras) == 1:
            errors.append(f"master cannot guess which extra local branch to prepare automatically: {extras[0]}")
        else:
            return {"ok": True, "errors": [], "checks": checks}
        return {"ok": False, "errors": errors, "checks": checks}
    if current_branch in protected:
        errors.append(f"release prepare only handles temporary development branches, found protected branch {current_branch}")
        return {"ok": False, "errors": errors, "checks": checks}
    if extras != [current_branch]:
        errors.append(f"release prepare requires exactly one temporary development branch, found {extras}")
        return {"ok": False, "errors": errors, "checks": checks}
    allowed = governed_allowed_paths(profile, skill_dir, project)
    changed, changed_errors = changed_paths(project)
    errors.extend(changed_errors)
    outside = [path for path in changed if not matches_governed_path(path, allowed)]
    if outside:
        errors.append(f"release prepare found changes outside governed release paths: {outside}")
        return {"ok": False, "errors": errors, "checks": checks}
    stage_targets = sorted(set(path for path in changed if matches_governed_path(path, allowed)))
    if stage_targets and run_git(project, ["add", "--all", "--", *stage_targets]).returncode != 0:
        errors.append("release prepare failed to stage governed release paths")
        return {"ok": False, "errors": errors, "checks": checks}
    diff_cached = run_git(project, ["diff", "--cached", "--quiet"])
    if diff_cached.returncode == 1:
        commit_message = f"release-prepare: stage {current_branch} for {version}"
        commit_result = run_git(project, ["commit", "-m", commit_message])
        if commit_result.returncode != 0:
            errors.append(f"release prepare failed to commit staged changes: {(commit_result.stderr or commit_result.stdout).strip()}")
            return {"ok": False, "errors": errors, "checks": checks}
    elif diff_cached.returncode not in {0, 1}:
        errors.append("release prepare could not inspect staged changes")
        return {"ok": False, "errors": errors, "checks": checks}
    checkout_master = run_git(project, ["checkout", "master"])
    if checkout_master.returncode != 0:
        errors.append(f"release prepare failed to checkout master: {(checkout_master.stderr or checkout_master.stdout).strip()}")
        return {"ok": False, "errors": errors, "checks": checks}
    merge_message = f"release-prepare: merge {current_branch} into master for {version}"
    merge = run_git(project, ["merge", "--no-ff", current_branch, "-m", merge_message])
    if merge.returncode != 0:
        errors.append(f"release prepare failed to merge {current_branch} into master: {(merge.stderr or merge.stdout).strip()}")
        return {"ok": False, "errors": errors, "checks": checks}
    delete_branch = run_git(project, ["branch", "-d", current_branch])
    if delete_branch.returncode != 0:
        errors.append(f"release prepare failed to delete branch {current_branch}: {(delete_branch.stderr or delete_branch.stdout).strip()}")
        return {"ok": False, "errors": errors, "checks": checks}
    final_branch, final_locals, final_status = current_branch_and_locals(project)
    checks.update({
        "prepared_branch": current_branch,
        "current_branch": final_branch,
        "local_branches": final_locals,
        "status_lines": final_status,
    })
    if final_branch != "master":
        errors.append("release prepare did not end on master")
    if sorted(final_locals) != protected:
        errors.append(f"release prepare did not end with only protected branches {protected}")
    if final_status:
        errors.append("release prepare requires a clean worktree after merge and branch cleanup")
    return {"ok": not errors, "errors": errors, "checks": checks}


def copy_release_tree(skill_dir: Path, release_dir: Path) -> None:
    if release_dir.exists():
        shutil.rmtree(release_dir)
    ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "AGENTS.md")
    shutil.copytree(skill_dir, release_dir, ignore=ignore)


def package_release(project: Path, version: str, skill_dir_raw: str) -> dict[str, Any]:
    profile = read_json(project / ".agents" / "agents-control.json")
    skill_dir = resolve_project(skill_dir_raw if Path(skill_dir_raw).is_absolute() else project / skill_dir_raw)
    skill_name = skill_dir.name
    source_rel = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else skill_dir.name
    pre = release_gate(project, version, skill_dir_raw, "pre", "unspecified")
    if pre["errors"]:
        return {"ok": False, "errors": pre["errors"], "pre_gate": pre}
    release_dir = project / "dist" / f"{skill_name}-{version}"
    zip_path = project / "dist" / f"{skill_name}-{version}.zip"
    copy_release_tree(skill_dir, release_dir)
    receipt_path = release_dir / receipt_filename(profile)
    receipt = {
        "skill_name": skill_name,
        "version": version,
        "source_path": source_rel,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "current_branch": "master",
        "local_branches": ["master", "release"],
        "worktree_clean": True,
        "phase_results": {"pre": True, "post": True},
        "packaging_mode": "repository-dist",
        "validation_level": "strong",
        "provenance_mode": "repository-dist",
        "files": build_release_file_manifest(release_dir),
    }
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    write_release_zip(release_dir, zip_path)
    add_result = run_git(project, ["add", "--all", "--", "dist"])
    if add_result.returncode != 0:
        return {"ok": False, "errors": ["package release failed to stage dist artifacts"], "pre_gate": pre}
    diff_cached = run_git(project, ["diff", "--cached", "--quiet"])
    if diff_cached.returncode == 1:
        commit_result = run_git(project, ["commit", "-m", f"package-release: {skill_name} {version}"])
        if commit_result.returncode != 0:
            return {"ok": False, "errors": [f"package release failed to commit dist artifacts: {(commit_result.stderr or commit_result.stdout).strip()}"], "pre_gate": pre}
    elif diff_cached.returncode not in {0, 1}:
        return {"ok": False, "errors": ["package release could not inspect staged release artifacts"], "pre_gate": pre}
    post = release_gate(project, version, skill_dir_raw, "post", "unspecified")
    return {
        "ok": not post["errors"],
        "errors": post["errors"],
        "release_dir": display_path(release_dir, project),
        "release_zip": display_path(zip_path, project),
        "receipt_path": display_path(receipt_path, project),
        "pre_gate": pre,
        "post_gate": post,
    }


def branch_gate(project: Path) -> dict[str, Any]:
    profile = read_json(project / ".agents" / "agents-control.json")
    if not isinstance(profile, dict):
        return {
            "project": str(project),
            "approved": True,
            "decision": "approved",
            "reasons": [],
            "checks": {"skipped": "no control profile"},
            "force_confirmation_required": False,
            "user_message": "",
        }
    if str(profile.get("git_management", "")).strip() == "no-git-management":
        return {
            "project": str(project),
            "approved": True,
            "decision": "approved",
            "reasons": [],
            "checks": {"skipped": "git management disabled"},
            "force_confirmation_required": False,
            "user_message": "",
        }

    policy = profile.get("git_branch_policy", {}) if isinstance(profile.get("git_branch_policy"), dict) else {}
    protected = policy.get("protected_branches", ["master", "release"])
    branch_model = str(profile.get("branch_model", "")).strip()
    git_branch_result = run_git(project, ["branch", "--show-current"])
    git_list_result = run_git(project, ["branch", "--list"])
    git_status_result = run_git(project, ["status", "--short"])
    reasons: list[str] = []
    checks: dict[str, Any] = {
        "branch_model": branch_model,
        "protected_branches": protected,
        "current_branch": "",
        "local_branches": [],
        "status_lines": [],
    }
    if any(result.returncode != 0 for result in [git_branch_result, git_list_result, git_status_result]):
        reasons.append("git branch governance requires a readable local git repository")
    else:
        current_branch = git_branch_result.stdout.strip()
        local_branches = sorted(line.strip().lstrip("* ").strip() for line in git_list_result.stdout.splitlines() if line.strip())
        status_lines = [line for line in git_status_result.stdout.splitlines() if line.strip()]
        checks["current_branch"] = current_branch
        checks["local_branches"] = local_branches
        checks["status_lines"] = status_lines
        if branch_model == "master-and-dist-release":
            if current_branch != "master":
                reasons.append(f"current branch must be master, found {current_branch or 'unknown'}")
            if sorted(local_branches) != sorted(protected):
                reasons.append(f"local branches must match protected branch set {protected}, found {local_branches}")
        if status_lines:
            reasons.append("worktree must be clean before continuing under strict branch governance")
    approved = not reasons
    return {
        "project": str(project),
        "approved": approved,
        "decision": "approved" if approved else "blocked",
        "reasons": reasons,
        "checks": checks,
        "force_confirmation_required": not approved,
        "user_message": "" if approved else "分支治理未通过，默认阻止普通生成/整理流程。若用户仍要继续，必须先明确确认是否进入分支整理或发布治理流程。",
    }


def parse_version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value.strip())
    if not match:
        raise ValueError(f"invalid version: {value}")
    return tuple(int(part) for part in match.groups())


def install_confirmation_options() -> list[dict[str, Any]]:
    return [
        {
            "label": "否，跳过安装",
            "value": "skip",
            "description": "默认选项；保留发布产物，但不安装到本地 skills 目录。",
            "recommended": True,
        },
        {
            "label": "安装到 Codex",
            "value": "codex",
            "description": "将发布包安装到当前本地 Codex skills 目录。",
            "recommended": False,
        },
        {
            "label": "自定义 skills 目录",
            "value": "custom",
            "description": "将发布包安装到用户明确提供的自定义 skills 根目录。",
            "recommended": False,
        },
    ]


def latest_release_dir(project: Path, skill_name: str) -> Path | None:
    releases = []
    for path in (project / "dist").glob(f"{skill_name}-v*"):
        if not path.is_dir():
            continue
        match = re.search(r"v(\d+)\.(\d+)\.(\d+)", path.name)
        if match:
            releases.append((tuple(int(part) for part in match.groups()), path))
    if not releases:
        return None
    releases.sort(key=lambda item: item[0])
    return releases[-1][1]


def release_members(root: Path, prefix: Path) -> list[str]:
    return sorted(path.relative_to(prefix).as_posix() for path in root.rglob("*") if path.is_file())


def release_project_kind(project: Path, skill_dir: Path) -> str:
    profile = read_json(project / ".agents" / "agents-control.json")
    if isinstance(profile, dict):
        kind = str(profile.get("kind", "")).strip().lower()
        if kind in {"skill", "engineering"}:
            return kind
    if (skill_dir / "SKILL.md").is_file():
        return "skill"
    return "engineering"


def release_gate(project: Path, version: str, skill_dir_raw: str, phase: str, install_intent: str) -> dict[str, Any]:
    profile = read_json(project / ".agents" / "agents-control.json")
    skill_dir = resolve_project(skill_dir_raw if Path(skill_dir_raw).is_absolute() else project / skill_dir_raw)
    skill_name = skill_dir.name
    project_kind = release_project_kind(project, skill_dir)
    expected_release = project / "dist" / f"{skill_name}-{version}"
    expected_zip = project / "dist" / f"{skill_name}-{version}.zip"
    source_rel = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else skill_dir.name
    receipt_path = expected_release / receipt_filename(profile)
    source_version = read_skill_version(skill_dir)
    git_branch = run_git(project, ["branch", "--show-current"]).stdout.strip()
    branches = sorted(line.strip().lstrip("* ").strip() for line in run_git(project, ["branch", "--list"]).stdout.splitlines() if line.strip())
    status_lines = [line for line in run_git(project, ["status", "--short"]).stdout.splitlines() if line.strip()]
    errors: list[str] = []
    checks = {
        "branch": git_branch,
        "local_branches": branches,
        "phase": phase,
        "install_intent": install_intent,
        "project_kind": project_kind,
        "skill_dir": skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else str(skill_dir),
        "source_version": source_version,
        "expected_release_dir": expected_release.relative_to(project).as_posix(),
        "expected_release_zip": expected_zip.relative_to(project).as_posix(),
        "receipt_path": expected_release.joinpath(receipt_filename(profile)).relative_to(project).as_posix(),
        "status_lines": status_lines,
    }
    if source_version and source_version != version:
        errors.append(f"release gate version {version} does not match skill source version {source_version}")
    if git_branch != "master":
        errors.append("release gate requires current branch master")
    if sorted(branches) != ["master", "release"]:
        errors.append("release gate requires only local branches master and release")
    if phase == "pre" and status_lines:
        errors.append("pre-release gate requires a clean committed worktree")
    if phase == "post":
        if status_lines:
            errors.append("post-release gate requires a clean committed worktree")
        if not expected_release.is_dir():
            errors.append(f"missing release directory: {expected_release.relative_to(project).as_posix()}")
        if not expected_zip.is_file():
            errors.append(f"missing release zip: {expected_zip.relative_to(project).as_posix()}")
        if expected_release.is_dir():
            source_files = release_members(skill_dir, skill_dir)
            release_files = sorted(item["path"] for item in build_release_file_manifest(expected_release, exclude={receipt_path.name}))
            if source_files != release_files:
                errors.append("release parity mismatch between skill source and dist release directory")
            if not receipt_path.is_file():
                errors.append(f"missing release receipt: {receipt_path.relative_to(project).as_posix()}")
            else:
                errors.extend(
                    verify_release_receipt(
                        project,
                        receipt_path,
                        expected_release,
                        skill_name,
                        version,
                        source_rel,
                        require_repo_dist=True,
                    )
                )
    latest = latest_release_dir(project, skill_name)
    if latest is not None:
        checks["latest_release_dir"] = latest.relative_to(project).as_posix()
        if parse_version_tuple(version) < parse_version_tuple(latest.name.rsplit("-", 1)[-1]):
            errors.append("requested release version is older than the latest dist release")
    result = {
        "project": str(project),
        "ok": not errors,
        "errors": errors,
        "checks": checks,
        "installable": not errors and phase == "post",
        "receipt_path": checks["receipt_path"],
        "provenance_mode": "repository-dist",
        "validation_level": "strong",
    }
    if phase == "post" and install_intent == "unspecified" and project_kind == "skill":
        result["install_confirmation_required"] = True
        result["confirmation_question"] = "释放安装版本后，用户尚未说明是否需要安装。是否需要安装当前发布包？"
        result["install_options"] = install_confirmation_options()
    else:
        result["install_confirmation_required"] = False
    return result


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage AGENTS.md docs governance artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold_parser = subparsers.add_parser("scaffold")
    scaffold_parser.add_argument("project", nargs="?", default=".")
    scaffold_parser.add_argument("--bootstrap-sessions", action="store_true")

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

    changelog_parser = subparsers.add_parser("git-changelog")
    changelog_parser.add_argument("project", nargs="?", default=".")
    changelog_parser.add_argument("--input", default=None)

    bootstrap_parser = subparsers.add_parser("bootstrap-experience")
    bootstrap_parser.add_argument("project", nargs="?", default=".")
    bootstrap_parser.add_argument("--force", action="store_true")

    release_gate_parser = subparsers.add_parser("release-gate")
    release_gate_parser.add_argument("project", nargs="?", default=".")
    release_gate_parser.add_argument("--version", required=True)
    release_gate_parser.add_argument("--skill-dir", required=True)
    release_gate_parser.add_argument("--phase", choices=["pre", "post"], default="pre")
    release_gate_parser.add_argument("--install-intent", choices=["unspecified", "requested", "skipped"], default="unspecified")

    release_prepare_parser = subparsers.add_parser("release-prepare")
    release_prepare_parser.add_argument("project", nargs="?", default=".")
    release_prepare_parser.add_argument("--version", required=True)
    release_prepare_parser.add_argument("--skill-dir", required=True)

    package_release_parser = subparsers.add_parser("package-release")
    package_release_parser.add_argument("project", nargs="?", default=".")
    package_release_parser.add_argument("--version", required=True)
    package_release_parser.add_argument("--skill-dir", required=True)

    branch_gate_parser = subparsers.add_parser("branch-gate")
    branch_gate_parser.add_argument("project", nargs="?", default=".")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("project", nargs="?", default=".")

    args = parser.parse_args()
    project = resolve_project(args.project)
    if args.command == "scaffold":
        result = scaffold(project)
        if getattr(args, "bootstrap_sessions", False):
            result["bootstrap_experience"] = bootstrap_experience(project)
        emit_json(result)
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
    elif args.command == "git-changelog":
        emit_json(write_git_changelog(project, args.input))
    elif args.command == "bootstrap-experience":
        result = bootstrap_experience(project, force=args.force)
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "release-gate":
        result = release_gate(project, args.version, args.skill_dir, args.phase, args.install_intent)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)
    elif args.command == "release-prepare":
        result = release_prepare(project, args.version, args.skill_dir)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)
    elif args.command == "package-release":
        result = package_release(project, args.version, args.skill_dir)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)
    elif args.command == "branch-gate":
        result = branch_gate(project)
        emit_json(result)
        if not result["approved"]:
            raise SystemExit(1)
    elif args.command == "verify":
        result = verify_docs(project)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
