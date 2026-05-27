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
from agents_common import (
    ensure_global_rule_overrides_file,
    evolution_owner_status,
    evolution_template_sink,
    GLOBAL_CODEX_AGENTS_PREAMBLE,
    GLOBAL_CODEX_AGENTS_BLOCK_END,
    GLOBAL_CODEX_AGENTS_BLOCK_START,
    governance_skill_name,
    RELEASE_CORE_WORKTREE_RULE,
    codex_sessions_root,
    current_timestamp,
    display_path,
    emit_json,
    global_codex_agents_path,
    global_codex_agents_status,
    inspect_project,
    matched_codex_sessions,
    parse_agents_metadata,
    preferred_skill_version,
    project_profile,
    read_json,
    root_agents_sync_command,
    render_global_codex_agents_template,
    read_skill_version,
    resolve_project,
    session_message_rows,
    global_codex_agents_sync_command,
)
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
LAST_UPDATED_HEADER_RE = re.compile(r"^<!--\s*Last updated:\s*(.*?)\s*\|\s*Last verified:\s*(.*?)\s*-->$", flags=re.MULTILINE)
SANITIZED_PLACEHOLDERS = {
    "api_key": "<REDACTED_API_KEY>",
    "password": "<REDACTED_PASSWORD>",
    "email": "<REDACTED_EMAIL>",
    "local_path": "<REDACTED_LOCAL_PATH>",
}
SANITIZED_ASSIGNMENT_RULES = [
    (
        "api_key",
        re.compile(r"(?m)^(\s*(?:[A-Z0-9]+_)*(?:API[_-]?KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET|TOKEN)(?:_[A-Z0-9]+)*\s*[:=]\s*)(.+?)\s*$"),
    ),
    (
        "password",
        re.compile(r"(?m)^(\s*[A-Z0-9_]*PASSWORD[A-Z0-9_]*\s*[:=]\s*)(.+?)\s*$"),
    ),
]
SANITIZED_INLINE_RULES = [
    ("email", re.compile(r"(?<!\\)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", flags=re.IGNORECASE)),
    ("local_path", re.compile(r"[A-Za-z]:\\Users\\[^\r\n]+")),
    ("local_path", re.compile(r"/(?:Users|home)/[^\s]+")),
]
SANITIZED_BINARY_PATTERNS = [
    ("api_key", re.compile(br"sk-(?:live|proj|test)-[A-Za-z0-9_-]+")),
    ("password", re.compile(br"password", flags=re.IGNORECASE)),
    ("email", re.compile(br"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
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
IGNORED_RUNTIME_GIT_PATHS = {ACTIVE_SESSION_PATH.replace("\\", "/")}
EXPERIENCE_REQUEST_PATH = ".agents/experience-update-request.json"
EVOLUTION_REQUEST_PATH = ".agents/evolution-update-request.json"
EVOLUTION_IMPORT_REQUEST_PATH = ".agents/evolution-import-request.json"
EVOLUTION_EXPORT_ROOT = ".agents/evolution-export"
CONVERSATION_SNAPSHOT_DIR = ".agents/conversation-snapshots"
HANDOFF_CURRENT_FILENAME = "HANDOFF.md"
HANDOFF_HISTORY_DIRNAME = "history_handoff"
HANDOFF_HISTORY_RE = re.compile(r"^HANDOFF-\d{8}-\d{6}(?:-\d+)?\.md$")
HANDOFF_GENERATED_AT_RE = re.compile(r"^- Generated at:\s*(.+?)\s*$", flags=re.MULTILINE)
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

def evolution_import_request_file(project: Path) -> Path:
    return project / EVOLUTION_IMPORT_REQUEST_PATH

def evolution_export_root(project: Path) -> Path:
    return project / EVOLUTION_EXPORT_ROOT

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

def handoff_paths(project: Path) -> dict[str, Path]:
    handoff_root = project / "docs" / "handoff"
    return {
        "root": handoff_root,
        "current": handoff_root / HANDOFF_CURRENT_FILENAME,
        "history": handoff_root / HANDOFF_HISTORY_DIRNAME,
    }

def docs_governance_initialized(project: Path) -> bool:
    for rel_path in [*DOC_DIRS, *REQUIRED_DOC_FILES, STATE_PATH]:
        if (project / rel_path).exists():
            return True
    return False

def handoff_history_filename_for_timestamp(moment: datetime, suffix: int | None = None) -> str:
    stamp_value = moment.strftime("%Y%m%d-%H%M%S")
    base = f"HANDOFF-{stamp_value}"
    return f"{base}-{suffix}.md" if suffix is not None else f"{base}.md"

def unique_handoff_history_path(history_dir: Path, moment: datetime) -> Path:
    target = history_dir / handoff_history_filename_for_timestamp(moment)
    suffix = 1
    while target.exists():
        target = history_dir / handoff_history_filename_for_timestamp(moment, suffix=suffix)
        suffix += 1
    return target

def parse_handoff_generated_at(text: str) -> datetime | None:
    match = HANDOFF_GENERATED_AT_RE.search(text)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None

def looks_like_handoff_markdown(text: str) -> bool:
    if "# Handoff" not in text:
        return False
    present_sections = sum(1 for section in HANDOFF_SECTIONS if f"## {section}" in text)
    return present_sections >= max(3, len(HANDOFF_SECTIONS) // 2)

def audit_handoff_naming(project: Path) -> dict[str, Any]:
    paths = handoff_paths(project)
    handoff_root = paths["root"]
    history_dir = paths["history"]
    errors: list[str] = []
    current_markdown_candidates: list[str] = []
    invalid_history_markdown: list[str] = []
    checked: list[str] = [
        "docs/handoff",
        "docs/handoff/HANDOFF.md",
        "docs/handoff/history_handoff",
    ]

    if handoff_root.exists() and handoff_root.is_dir():
        for child in sorted(handoff_root.iterdir()):
            rel_path = child.relative_to(project).as_posix()
            if child.name == HANDOFF_CURRENT_FILENAME:
                if not child.is_file():
                    errors.append(f"handoff naming drift: current handoff path must be a file: {rel_path}")
                continue
            if child.name == HANDOFF_HISTORY_DIRNAME:
                if not child.is_dir():
                    errors.append(f"handoff naming drift: history handoff path must be a directory: {rel_path}")
                continue
            if child.is_file() and child.suffix.lower() == ".md":
                current_markdown_candidates.append(rel_path)
                errors.append(
                    f"handoff naming drift: current handoff must be exactly docs/handoff/{HANDOFF_CURRENT_FILENAME}; found {rel_path}"
                )
            else:
                errors.append(
                    f"handoff naming drift: docs/handoff only allows {HANDOFF_CURRENT_FILENAME} and {HANDOFF_HISTORY_DIRNAME}/; found {rel_path}"
                )

    if history_dir.exists() and history_dir.is_dir():
        for child in sorted(history_dir.iterdir()):
            rel_path = child.relative_to(project).as_posix()
            checked.append(rel_path)
            if not child.is_file():
                errors.append(f"handoff naming drift: history_handoff only allows archived markdown files; found {rel_path}")
                continue
            if child.suffix.lower() != ".md":
                errors.append(f"handoff naming drift: history handoff archive must be markdown: {rel_path}")
                continue
            if not HANDOFF_HISTORY_RE.fullmatch(child.name):
                invalid_history_markdown.append(rel_path)
                errors.append(
                    "handoff naming drift: history handoff archive must match "
                    f"HANDOFF-YYYYMMDD-HHMMSS.md or HANDOFF-YYYYMMDD-HHMMSS-N.md; found {rel_path}"
                )

    return {
        "project": str(project),
        "ok": not errors,
        "blocking": bool(errors),
        "checked": checked,
        "errors": errors,
        "current_markdown_candidates": current_markdown_candidates,
        "invalid_history_markdown": invalid_history_markdown,
    }

def current_handoff_entry(project: Path) -> dict[str, Any] | None:
    path = handoff_paths(project)["current"]
    if not path.exists() or not path.is_file():
        return None
    content = path.read_text(encoding="utf-8", errors="ignore")
    return {
        "path": path.relative_to(project).as_posix(),
        "content": content,
        "handoff_count": handoff_count_from_markdown(content),
    }

def handoff_window(project: Path, checkpoint: int, limit: int = EXPERIENCE_CADENCE_HANDOFFS) -> dict[str, Any]:
    from manage_docs_experience import recent_handoff_history

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
    from manage_docs_experience import recent_conversation_context

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
    from manage_docs_experience import archive_experience_files

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
        f"- {RELEASE_CORE_WORKTREE_RULE}",
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
        "- Different-version release directories and zip files are immutable history by default; do not delete, overwrite, or rewrite them during a new packaging run.",
        "- Rebuilding the same version may replace only the current target release directory and its matching zip; no other `dist/` artifact may change.",
        "- Installable `dist/` release copies for skill development must be sanitized before packaging; replace sensitive values in the dist copy only and use typed placeholders such as `<REDACTED_API_KEY>`, `<REDACTED_PASSWORD>`, `<REDACTED_EMAIL>`, and `<REDACTED_LOCAL_PATH>`.",
        "- The release receipt must record sanitized files, placeholder types, and post-sanitization hashes; undeclared or unfinished sanitization blocks installation.",
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
