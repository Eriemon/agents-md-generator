from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import SKIP_DIRS, emit_json, parse_agents_metadata, read_installed_skill_version, resolve_project
from manage_docs import verify_docs


COMMAND_RE = re.compile(r"`([^`\n]+)`")
PATH_RE = re.compile(r"`([^`\n]+(?:/|\\|\.md|\.json|\.toml|\.yml|\.yaml|\.py|\.ts|\.tsx|\.go|\.php)[^`\n]*)`")
ROOT_AGENTS_MAX_BYTES = 12 * 1024


def validate_markers(text: str, file: str, errors: list[str]) -> None:
    starts = len(re.findall(r"AGENTS-GENERATED:START", text))
    ends = len(re.findall(r"AGENTS-GENERATED:END", text))
    if starts != ends:
        errors.append(f"{file}: generated marker mismatch ({starts} starts, {ends} ends)")


def section_body(text: str, heading: str) -> str | None:
    match = re.search(rf"^{re.escape(heading)}\s*$", text, flags=re.MULTILINE)
    if not match:
        return None
    start = match.end()
    next_heading = re.search(r"^##\s+", text[start:], flags=re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def validate_strong_control(text: str, file: str, project: Path, errors: list[str]) -> None:
    required_sections = [
        "## Control Profile",
        "## Directory Contract",
        "## Release Contract",
        "## Engineering Rule Contract",
        "## Conversation Completion Contract",
        "## Documentation Governance Contract",
    ]
    if "Strong control: complete" not in text:
        return
    for section in required_sections:
        if section not in text:
            errors.append(f"{file}: missing strong-control section {section}")
    if not (project / ".agents" / "agents-control.json").exists():
        errors.append(f"{file}: strong control requires .agents/agents-control.json")
    docs_result = verify_docs(project)
    errors.extend(f"{file}: {item}" for item in docs_result["errors"])
    profile = read_json(project / ".agents" / "agents-control.json")
    if profile.get("kind") == "skill":
        contract_body = section_body(text, "## Skill Design Contract")
        if contract_body is None:
            errors.append(f"{file}: strong-control skill project requires ## Skill Design Contract")
            return
        required_phrases = [
            "Trigger scenarios:",
            "Design patterns:",
            "Resource boundaries:",
            "Progressive disclosure:",
            "Validation gates:",
            "Forward testing:",
        ]
        for phrase in required_phrases:
            if phrase not in contract_body:
                errors.append(f"{file}: Skill Design Contract missing {phrase}")
        vague_markers = [
            "Trigger scenarios: not specified",
            "Design patterns: not specified",
            "Resource boundaries: not specified",
            "Progressive disclosure: not specified",
            "Validation gates: not specified",
            "Forward testing: not specified",
        ]
        for marker in vague_markers:
            if marker in contract_body:
                errors.append(f"{file}: Skill Design Contract contains unresolved default: {marker}")
        gates_match = re.search(r"Validation gates:\s*(.+)", contract_body, flags=re.IGNORECASE)
        gates_text = gates_match.group(1).lower() if gates_match else ""
        for required_gate in ("quick_validate", "audit", "verify"):
            if required_gate not in gates_text:
                errors.append(f"{file}: Skill Design Contract validation gates must include {required_gate}")


def is_path_reference(raw: str) -> bool:
    if raw.startswith(("http://", "https://", "mailto:")):
        return False
    if raw in {"AGENTS.md", "CLAUDE.md", "GEMINI.md"}:
        return False
    if any(char.isspace() for char in raw):
        return False
    if any(char in raw for char in "*?<>|,"):
        return False
    return True


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def make_targets(root: Path) -> set[str]:
    path = root / "Makefile"
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="ignore")
    return set(re.findall(r"^([A-Za-z0-9_.-]+):", text, flags=re.MULTILINE))


def package_scripts(root: Path) -> set[str]:
    package = read_json(root / "package.json")
    scripts = package.get("scripts", {}) if isinstance(package.get("scripts"), dict) else {}
    return set(scripts)


def composer_scripts(root: Path) -> set[str]:
    composer = read_json(root / "composer.json")
    scripts = composer.get("scripts", {}) if isinstance(composer.get("scripts"), dict) else {}
    return set(scripts)


def config_backed_command_error(command: str, project: Path) -> str | None:
    tokens = command.split()
    if not tokens:
        return None
    if tokens[0] == "make" and len(tokens) >= 2:
        if tokens[1] not in make_targets(project):
            return f"documented command `{command}` references missing Makefile target `{tokens[1]}`"
    if tokens[0] in {"npm", "pnpm", "yarn", "bun"}:
        scripts = package_scripts(project)
        if not scripts:
            return None
        if tokens[0] in {"pnpm", "yarn"} and len(tokens) >= 2 and tokens[1] in {"dlx", "exec", "install", "add", "remove"}:
            return None
        if tokens[0] == "bun" and len(tokens) >= 2 and tokens[1] in {"x", "install", "add", "remove"}:
            return None
        if tokens[0] == "npm" and len(tokens) >= 3 and tokens[1] == "run":
            script = tokens[2]
        elif tokens[0] == "npm" and len(tokens) >= 2 and tokens[1] == "test":
            script = "test"
        elif tokens[0] == "bun" and len(tokens) >= 3 and tokens[1] == "run":
            script = tokens[2]
        elif len(tokens) >= 2:
            script = tokens[1]
        else:
            return None
        if script not in scripts:
            return f"documented command `{command}` references missing package.json script `{script}`"
    if tokens[0] == "composer" and len(tokens) >= 3 and tokens[1] == "run":
        scripts = composer_scripts(project)
        if scripts and tokens[2] not in scripts:
            return f"documented command `{command}` references missing composer.json script `{tokens[2]}`"
    return None


def should_skip(path: Path, project: Path, include_skipped: bool = False) -> bool:
    if include_skipped:
        return False
    try:
        parts = path.relative_to(project).parts
    except ValueError:
        parts = path.parts
    return bool(set(parts) & SKIP_DIRS)


def verify(project: Path, include_skipped: bool = False) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []
    installed_version = read_installed_skill_version()
    for agents in sorted(project.rglob("AGENTS.md")):
        if should_skip(agents, project, include_skipped):
            continue
        checked.append(str(agents.relative_to(project).as_posix()))
        text = agents.read_text(encoding="utf-8", errors="ignore")
        if agents == project / "AGENTS.md":
            size = len(text.encode("utf-8"))
            if size > ROOT_AGENTS_MAX_BYTES:
                errors.append(f"{checked[-1]}: exceeds 12KB limit ({size} bytes)")
            managed_root = "Managed by agent:" in text or (project / ".agents" / "agents-control.json").exists()
            if managed_root:
                metadata = parse_agents_metadata(text)
                if not metadata.get("agents_version") or not metadata.get("generator_version"):
                    errors.append("AGENTS.md: missing AGENTS metadata version")
                elif installed_version and metadata.get("agents_version") != installed_version:
                    errors.append(
                        f"AGENTS.md: agents version {metadata.get('agents_version')} does not match installed agents-md-generator version {installed_version}"
                    )
                elif not installed_version:
                    errors.append("AGENTS.md: installed agents-md-generator version is unavailable")
                if not metadata.get("default_language"):
                    errors.append("AGENTS.md: missing default language metadata")
        validate_markers(text, checked[-1], errors)
        validate_strong_control(text, checked[-1], project, errors)
        if "{{" in text or "}}" in text:
            errors.append(f"{checked[-1]}: unresolved template placeholder")
        if "Precedence" not in text and agents == project / "AGENTS.md":
            errors.append("AGENTS.md: missing precedence statement")

        for match in PATH_RE.finditer(text):
            raw = match.group(1).strip()
            if not is_path_reference(raw):
                continue
            candidate = (agents.parent / raw).resolve()
            root_candidate = (project / raw).resolve()
            if not candidate.exists() and not root_candidate.exists() and not raw.endswith("/"):
                warnings.append(f"{checked[-1]}: referenced path may not exist: {raw}")

        for match in COMMAND_RE.finditer(text):
            command = match.group(1).strip()
            if not command or "/" in command or command.endswith((".md", ".json", ".toml", ".yml", ".yaml")):
                continue
            config_error = config_backed_command_error(command, project)
            if config_error:
                errors.append(f"{checked[-1]}: {config_error}")
            if command.startswith(("make ", "npm ", "pnpm ", "yarn ", "bun ", "python ", "pytest", "go ", "composer ", "ruff ", "mypy ", "npx ")):
                continue
    return {"checked_files": checked, "errors": errors, "warnings": warnings}


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify AGENTS.md generated content.")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--include-skipped", action="store_true", help="Also scan skipped directories such as ref, vendor, and build outputs.")
    args = parser.parse_args()
    emit_json(verify(resolve_project(args.project), args.include_skipped))


if __name__ == "__main__":
    main()
