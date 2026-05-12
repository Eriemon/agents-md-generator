from __future__ import annotations

import argparse
import re
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, resolve_project


REQUIRED_FILES = [
    "SKILL.md",
    "agents/openai.yaml",
    "references/agents-md-guidance.md",
    "references/book-rules-coverage.md",
    "references/capability-coverage.md",
    "references/skill-design-coverage.md",
    "references/question-bank.md",
    "references/review-checklist.md",
    "references/script-guide.md",
    "references/evaluation-scenarios.md",
    "assets/templates/root-agents.md",
    "assets/templates/scoped-agents.md",
    "scripts/inspect_project.py",
    "scripts/collect_design_profile.py",
    "scripts/extract_commands.py",
    "scripts/extract_context.py",
    "scripts/detect_scopes.py",
    "scripts/render_agents.py",
    "scripts/manage_docs.py",
    "scripts/manage_dirs.py",
    "scripts/install_skill.py",
    "scripts/select_engineering_rules.py",
    "scripts/verify_agents.py",
    "scripts/check_freshness.py",
    "scripts/create_agent_shims.py",
    "scripts/audit_skill.py",
    "scripts/evaluate_skill.py",
]

DISALLOWED_ROOT_DOCS = {"INSTALL.md", "INSTALLATION.md"}
DISALLOWED_CACHE_SUFFIXES = {".pyc", ".pyo"}
LOCAL_REFERENCE_RE = re.compile(
    r"G:[/\\]html|ref[/\\](agent-rules|html)|\b[A-Za-z]:[/\\][^\s`'\"<>)]*",
    flags=re.IGNORECASE,
)
TEMPLATE_PLACEHOLDER_RE = re.compile(r"{{([A-Z0-9_]+)}}")
KNOWN_TEMPLATE_PLACEHOLDERS = {
    "root-agents.md": {
        "TIMESTAMP",
        "VERIFIED_TIMESTAMP",
        "PROJECT_OVERVIEW",
        "CONTROL_PROFILE",
        "DIRECTORY_CONTRACT",
        "RELEASE_CONTRACT",
        "ENGINEERING_RULE_CONTRACT",
        "SKILL_DESIGN_CONTRACT",
        "CONVERSATION_COMPLETION_CONTRACT",
        "EXPERIENCE_LOG_CONTRACT",
        "DOCUMENTATION_GOVERNANCE_CONTRACT",
        "VERIFICATION_STATUS",
        "COMMAND_SOURCE",
        "COMMAND_ROWS",
        "FILE_MAP",
        "GOLDEN_SAMPLE_ROWS",
        "UTILITY_ROWS",
        "HEURISTIC_ROWS",
        "REPOSITORY_SETTINGS",
        "HOOK_POLICY",
        "CI_RULES",
        "GITHUB_SETTINGS",
        "DIRECTORY_COVERAGE",
        "KEY_DECISIONS",
        "ALWAYS_RULES",
        "ASK_FIRST_RULES",
        "NEVER_RULES",
        "CODEBASE_STATE",
        "TERMINOLOGY_ROWS",
        "SCOPE_INDEX",
    },
    "scoped-agents.md": {
        "TIMESTAMP",
        "VERIFIED_TIMESTAMP",
        "SCOPE_NAME",
        "SCOPE_PATH",
        "SCOPE_OVERVIEW",
        "LOCAL_COMMANDS",
        "TESTING_RULES",
        "LOCAL_STRUCTURE",
        "CODE_STYLE",
        "GIT_WORKFLOW",
        "LOCAL_BOUNDARIES",
        "SCOPE_PURPOSE",
    },
}


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def referenced_paths(skill_text: str) -> set[str]:
    paths: set[str] = set()
    for raw in re.findall(r"`([^`]+)`", skill_text):
        value = raw.strip()
        if value.startswith(("references/", "assets/", "scripts/", "agents/")):
            paths.add(value)
    return paths


def contains_local_reference(text: str) -> bool:
    return bool(LOCAL_REFERENCE_RE.search(text))


def has_toc(lines: list[str]) -> bool:
    return any("table of contents" in line.lower() or "目录" in line for line in lines[:30])


def parse_openai_interface(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == "interface:")
    except StopIteration:
        return None
    data: dict[str, str] = {}
    for line in lines[start + 1:]:
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            break
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def validate_openai_yaml(path: Path, errors: list[str]) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    interface = parse_openai_interface(text)
    if interface is None:
        errors.append("agents/openai.yaml: missing interface section")
        return
    for key in ("display_name", "short_description", "default_prompt"):
        value = interface.get(key, "").strip()
        if not value:
            errors.append(f"agents/openai.yaml: missing interface.{key}")
        elif value.lower() in {"todo", "tbd", "placeholder"}:
            errors.append(f"agents/openai.yaml: interface.{key} is a placeholder")
    default_prompt = interface.get("default_prompt", "")
    if default_prompt and "$agents-md-generator" not in default_prompt:
        errors.append("agents/openai.yaml: default_prompt must mention $agents-md-generator")


def audit(skill_dir: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []

    for rel_path in REQUIRED_FILES:
        path = skill_dir / rel_path
        checked.append(rel_path)
        if not path.exists():
            errors.append(f"missing required file: {rel_path}")

    for name in DISALLOWED_ROOT_DOCS:
        if (skill_dir / name).exists():
            errors.append(f"disallowed extra root documentation file: {name}")

    skill_path = skill_dir / "SKILL.md"
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8", errors="ignore")
        fm = parse_frontmatter(text)
        if set(fm) != {"name", "description"}:
            errors.append("SKILL.md frontmatter must contain only name and description")
        if fm.get("name") != "agents-md-generator":
            errors.append("SKILL.md name must be agents-md-generator")
        description = fm.get("description", "")
        if not description.startswith("Use when"):
            errors.append("SKILL.md description must start with 'Use when'")
        if len(description) > 1024:
            errors.append("SKILL.md description must be 1024 characters or fewer")
        if len(text.splitlines()) > 500:
            errors.append("SKILL.md must stay under 500 lines")
        for rel_path in referenced_paths(text):
            checked.append(rel_path)
            if not (skill_dir / rel_path).exists():
                errors.append(f"SKILL.md references missing resource: {rel_path}")
        if contains_local_reference(text):
            errors.append("SKILL.md must not depend on local reference folders")

    validate_openai_yaml(skill_dir / "agents" / "openai.yaml", errors)

    for script in sorted((skill_dir / "scripts").glob("*.py")):
        rel_path = script.relative_to(skill_dir).as_posix()
        if rel_path not in checked:
            checked.append(rel_path)
        try:
            source = script.read_text(encoding="utf-8", errors="ignore")
            compile(source, str(script), "exec")
        except SyntaxError as exc:
            errors.append(f"{rel_path} does not compile: {exc.msg}")

    for path in skill_dir.rglob("*"):
        rel_path = path.relative_to(skill_dir).as_posix()
        rel_parts = path.relative_to(skill_dir).parts
        if ".git" in rel_parts:
            continue
        if "__pycache__" in rel_parts or path.suffix in DISALLOWED_CACHE_SUFFIXES:
            errors.append(f"disallowed generated cache artifact: {rel_path}")
            continue
        if not path.is_file():
            continue
        if path.suffix in {".md", ".yaml", ".yml", ".py"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if rel_parts and rel_parts[0] == "references" and path.suffix == ".md":
                lines = text.splitlines()
                if len(lines) > 100 and not has_toc(lines):
                    errors.append(f"{rel_path}: reference files over 100 lines need a table of contents")
            if "{{" in text and (rel_path == "SKILL.md" or rel_path.startswith("agents/")):
                warnings.append(f"{rel_path}: contains template placeholder syntax outside templates")
            if rel_path.startswith("assets/templates/"):
                template_name = path.name
                known = KNOWN_TEMPLATE_PLACEHOLDERS.get(template_name, set())
                for placeholder in sorted(set(TEMPLATE_PLACEHOLDER_RE.findall(text)) - known):
                    errors.append(f"{template_name}: contains unknown template placeholder: {placeholder}")
            if contains_local_reference(text):
                errors.append(f"{rel_path}: references local-only development material")

    return {
        "skill_dir": str(skill_dir),
        "checked": sorted(set(checked)),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit agents-md-generator skill structure and scripts.")
    parser.add_argument("skill_dir", nargs="?", default=".")
    args = parser.parse_args()
    emit_json(audit(resolve_project(args.skill_dir)))


if __name__ == "__main__":
    main()
