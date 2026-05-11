from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import detect_scopes, extract_commands, extract_context, inspect_project, resolve_project, today


GENERATED_START = "<!-- AGENTS-GENERATED:START"
GENERATED_END = "<!-- AGENTS-GENERATED:END"


def command_rows(commands: list[dict[str, str]]) -> str:
    if not commands:
        return "| Verify manually | Ask user for project commands | unknown | user |"
    return "\n".join(
        f"| {item['task']} | `{item['command']}` | {item.get('time', '~30s')} | {item.get('source', 'unknown')} |"
        for item in commands
    )


def file_map(facts: dict) -> str:
    dirs = facts.get("directories", [])
    if not dirs:
        return "```\n(root files only) -> inspect root files directly\n```\n"
    lines = ["```"]
    for directory in dirs[:12]:
        purpose = "project directory"
        if directory in {"src", "app", "lib"}:
            purpose = "source code"
        elif directory in {"tests", "test", "__tests__"}:
            purpose = "tests and fixtures"
        elif directory in {"docs", "Documentation"}:
            purpose = "documentation"
        elif directory in {"scripts", "tools"}:
            purpose = "automation scripts"
        elif directory.startswith(".github"):
            purpose = "GitHub automation"
        lines.append(f"{directory}/ -> {purpose}")
    lines.append("```")
    return "\n".join(lines) + "\n"


def scope_index(scopes: list[dict[str, str]]) -> str:
    if not scopes:
        return "- None detected. Keep root AGENTS.md concise.\n"
    return "".join(f"- `./{item['agents_file']}` - {item['purpose']}\n" for item in scopes)


def default_template_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "assets" / "templates"


def load_template(template_dir: Path, name: str) -> str:
    path = template_dir / name
    if not path.exists():
        raise SystemExit(f"Template does not exist: {path}")
    return path.read_text(encoding="utf-8")


def replace_placeholders(template: str, values: dict[str, str]) -> str:
    text = template
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    unresolved = sorted(set(re.findall(r"{{([A-Z0-9_]+)}}", text)))
    for key in unresolved:
        text = text.replace("{{" + key + "}}", "")
    return text


def project_overview(facts: dict) -> str:
    return f"Primary language: {facts['primary_language']}. Framework: {facts['framework']}. Project type: {facts['project_type']}."


def golden_sample_rows() -> str:
    return "| Existing code | Inspect nearest similar file | Follow local imports, naming, tests |"


def golden_sample_rows_from_context(context: dict) -> str:
    samples = context.get("golden_samples", [])
    if not samples:
        return golden_sample_rows()
    return "\n".join(f"| Existing pattern | `{path}` | Follow local structure and tests |" for path in samples)


def utility_rows(context: dict) -> str:
    utilities = context.get("utilities", [])
    if not utilities:
        return "| Project automation | Existing scripts/configs before new tools | `scripts/`, Makefile, package config |"
    return "\n".join(f"| Existing utility | Inspect before creating new automation | `{path}` |" for path in utilities)


def ci_rules(context: dict) -> str:
    rules = context.get("ci_rules", [])
    if not rules:
        return "- Follow checks defined in CI workflow files when present.\n- Do not invent required checks that are not visible in repository files."
    return "\n".join(f"- `{item['workflow']}` runs `{item['command']}`." for item in rules)


def key_decisions(context: dict) -> str:
    adrs = context.get("adrs", [])
    architecture = context.get("architecture_files", [])
    docs = context.get("documentation", [])
    lines = [f"- Review `{path}` before changing architecture or policy." for path in adrs[:8]]
    lines.extend(f"- Respect ownership or architecture guidance in `{path}`." for path in architecture[:4])
    if not lines and docs:
        lines = [f"- Use `{path}` as a pointer; do not copy long documentation into AGENTS.md." for path in docs[:4]]
    return "\n".join(lines) if lines else "- Link ADRs or architecture docs here when discovered; do not summarize decisions that are not documented."


def codebase_state(context: dict) -> str:
    configs = context.get("quality_configs", [])
    platform = context.get("platform_files", [])
    ide = context.get("ide_settings", [])
    dependency = context.get("dependency_configs", [])
    reference_projects = context.get("reference_projects", [])
    lines = [f"- Quality config detected: `{path}`." for path in configs]
    lines.extend(f"- Platform/dev-environment file detected: `{path}`." for path in platform)
    lines.extend(f"- Editor/IDE convention detected: `{path}`." for path in ide)
    lines.extend(f"- Dependency automation config detected: `{path}`." for path in dependency)
    lines.extend(f"- Reference project available: `{path}`. Treat as read-only context unless the user asks otherwise." for path in reference_projects)
    if not lines:
        return "- Add migrations, tech debt, and known risks here only when verified from files or user input."
    return "\n".join(lines)


def hook_policy(context: dict) -> str:
    hooks = context.get("hook_configs", [])
    if not hooks:
        return "- No hook framework detected. Treat this as a setup gap; do not bypass hooks with `--no-verify`."
    lines = [f"- Hook framework/config detected: `{path}`." for path in hooks]
    lines.append("- Never bypass hooks with `--no-verify`; fix the underlying failure.")
    return "\n".join(lines)


def github_settings(context: dict) -> str:
    settings = context.get("github_settings", [])
    if not settings:
        return "- No GitHub settings or rulesets detected."
    return "\n".join(f"- GitHub setting/ruleset detected: `{path}`." for path in settings)


def directory_coverage(context: dict) -> str:
    candidates = context.get("directory_coverage_candidates", [])
    if not candidates:
        return "- No uncovered major directories detected."
    return "\n".join(
        f"- Directory coverage candidate: `{path}/` may need scoped AGENTS.md if it has local rules."
        for path in candidates
    )


def heuristic_rows() -> str:
    return "\n".join([
        "| Adding dependency | Ask first |",
        "| Unsure about pattern | Read nearby files and golden samples |",
        "| Command not verified | Mark it unverified or omit it |",
    ])


def bullet_lines(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def load_profile(project: Path, raw: str | None) -> dict | None:
    path = Path(raw).resolve() if raw else project / ".agents" / "agents-control.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Could not parse profile JSON: {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit(f"Profile must be a JSON object: {path}")
    return data


def control_profile(profile: dict | None) -> str:
    if not profile:
        return "\n".join([
            "- Strong control: not configured.",
            "- Run `python scripts/collect_design_profile.py <project> --answers answers.json --write` before claiming strict control.",
            "- Until configured, ask the mandatory design questions before writing controlled AGENTS.md output.",
        ])
    lines = [
        "- Strong control: complete.",
        f"- Development type: {profile.get('kind', 'unknown')}.",
        f"- Name: {profile.get('name', 'unknown')}.",
        f"- Purpose: {profile.get('purpose', 'unknown')}.",
        f"- Reason: {profile.get('reason', 'unknown')}.",
    ]
    audience = profile.get("audience_or_environment")
    if audience:
        lines.append(f"- Audience/environment: {audience}.")
    if profile.get("reference_materials_temporary"):
        lines.append("- Temporary reference materials were used; remove them manually after development and do not copy local reference paths into AGENTS.md.")
    return "\n".join(lines)


def directory_contract(profile: dict | None) -> str:
    if not profile:
        return "- Directory contract: not confirmed. Do not freeze structure until the user confirms local, remote, and feature-addition layout."
    contract = profile.get("directory_contract", {})
    return "\n".join([
        f"- Confirmed: {contract.get('confirmed', False)}.",
        f"- Local structure: {contract.get('local', 'not specified')}.",
        f"- Remote structure: {contract.get('remote', 'not specified')}.",
        f"- New feature structure: {contract.get('feature_rules', 'not specified')}.",
        "- Do not add new top-level directories or move ownership boundaries without updating this contract.",
    ])


def release_contract(profile: dict | None) -> str:
    if not profile:
        return "- Release contract: not configured. Do not claim installable release packaging until the user confirms dist and zip rules."
    release = profile.get("release_contract", {})
    return "\n".join([
        f"- Git management: {profile.get('git_management', 'not specified')}.",
        f"- Branch model: {profile.get('branch_model', 'not specified')}.",
        f"- Dist folder: `{release.get('dist_folder', 'dist')}`.",
        f"- Release folder pattern: `{release.get('release_folder_pattern', '<name>-vx.x.x')}`.",
        f"- Zip required: {release.get('zip_required', True)}.",
        "- Do not push to a remote unless the user explicitly asks.",
    ])


def engineering_rule_contract(profile: dict | None) -> str:
    if not profile:
        return "\n".join([
            "- Primary rule set: none.",
            "- Mode: none.",
            "- Ask the user before adding any book-derived engineering bias to AGENTS.md.",
            "- Do not paste full book rules into AGENTS.md.",
        ])
    contract = profile.get("engineering_rule_contract", {})
    primary = contract.get("primary", "none")
    mode = contract.get("mode", "none")
    scope = contract.get("scope", "on-demand")
    lines = [
        f"- Primary rule set: {primary}.",
        f"- Mode: {mode}.",
        f"- Scope: {scope}.",
        f"- Compatibility: {contract.get('compatibility_policy', 'one primary active rule set')}.",
        f"- Compression: {contract.get('compression_policy', 'keep only decision-changing rules')}.",
        "- Do not paste full book rules into AGENTS.md; keep full material reference-only.",
    ]
    notes = contract.get("notes")
    if notes:
        lines.append(f"- Notes: {notes}.")
    return "\n".join(lines)


def skill_design_contract(profile: dict | None) -> str:
    if not profile or profile.get("kind") != "skill":
        return "\n".join([
            "- Skill design contract: not configured for this project.",
            "- For Skill development, collect a confirmed profile before claiming strict Skill design control.",
        ])
    contract = profile.get("skill_design_contract", {})
    patterns = contract.get("patterns", [])
    if isinstance(patterns, str):
        patterns_text = patterns
    else:
        patterns_text = ", ".join(str(item) for item in patterns if str(item).strip())
    return "\n".join([
        f"- Trigger scenarios: {contract.get('trigger_scenarios', 'not specified')}.",
        f"- Design patterns: {patterns_text or 'not specified'}.",
        f"- Resource boundaries: {contract.get('resource_plan', 'not specified')}.",
        f"- Progressive disclosure: {contract.get('progressive_disclosure_policy', 'not specified')}.",
        f"- Validation gates: {contract.get('validation_gates', 'not specified')}.",
        f"- Forward testing: {contract.get('forward_testing_policy', 'not specified')}.",
        f"- Reference material policy: {contract.get('reference_material_policy', 'temporary inputs only')}.",
    ])


def conversation_completion_contract(profile: dict | None) -> str:
    return "\n".join([
        "- Finish all requested development work in the current conversation whenever feasible.",
        "- If work cannot be completed, report blockers, completed files, unverified assumptions, and exact next steps.",
        "- Run the smallest relevant checks during development and final verification before completion claims.",
        "- Preserve user changes and never rewrite the directory contract silently.",
    ])


def experience_log_contract(profile: dict | None) -> str:
    folder = "experience"
    pattern = "YYYY-MM-DD-<topic>.md"
    sections = ["background", "changes", "verification", "lessons", "reusable_experience", "risks"]
    if profile:
        contract = profile.get("experience_contract", {})
        folder = contract.get("folder", folder)
        pattern = contract.get("file_pattern", pattern)
        sections = contract.get("required_sections", sections)
    return "\n".join([
        f"- Write a lesson file under `{folder}/` after each development conversation.",
        f"- File name pattern: `{folder}/{pattern}`.",
        f"- Required sections: {', '.join(sections)}.",
        "- Capture mistakes, fixes, reusable decisions, verification evidence, and follow-up risks.",
    ])


def template_values(project: Path, profile: dict | None = None) -> dict[str, str]:
    facts = inspect_project(project)
    commands = extract_commands(project)["commands"]
    scopes = detect_scopes(project)["scopes"]
    context = extract_context(project)
    command_source = ", ".join(sorted({item["source"] for item in commands})) if commands else "none detected"
    return {
        "TIMESTAMP": today(),
        "VERIFIED_TIMESTAMP": "never",
        "PROJECT_OVERVIEW": project_overview(facts),
        "CONTROL_PROFILE": control_profile(profile),
        "DIRECTORY_CONTRACT": directory_contract(profile),
        "RELEASE_CONTRACT": release_contract(profile),
        "ENGINEERING_RULE_CONTRACT": engineering_rule_contract(profile),
        "SKILL_DESIGN_CONTRACT": skill_design_contract(profile),
        "CONVERSATION_COMPLETION_CONTRACT": conversation_completion_contract(profile),
        "EXPERIENCE_LOG_CONTRACT": experience_log_contract(profile),
        "VERIFICATION_STATUS": "unverified",
        "COMMAND_SOURCE": command_source,
        "COMMAND_ROWS": command_rows(commands),
        "FILE_MAP": file_map(facts).rstrip(),
        "GOLDEN_SAMPLE_ROWS": golden_sample_rows_from_context(context),
        "UTILITY_ROWS": utility_rows(context),
        "HEURISTIC_ROWS": heuristic_rows(),
        "REPOSITORY_SETTINGS": f"- CI: {', '.join(facts['ci']) if facts['ci'] else 'none detected'}\n- Package manager: {facts['package_manager']}",
        "HOOK_POLICY": hook_policy(context),
        "CI_RULES": ci_rules(context),
        "GITHUB_SETTINGS": github_settings(context),
        "DIRECTORY_COVERAGE": directory_coverage(context),
        "KEY_DECISIONS": key_decisions(context),
        "ALWAYS_RULES": bullet_lines([
            "Preserve user changes and hand-written guidance.",
            "Add tests or verification for changed behavior.",
            "Show verification output before claiming completion.",
        ]),
        "ASK_FIRST_RULES": bullet_lines([
            "Adding dependencies.",
            "Changing CI/CD, public APIs, schemas, migrations, or security-sensitive code.",
            "Running destructive or expensive commands.",
        ]),
        "NEVER_RULES": bullet_lines([
            "Commit secrets, credentials, or sensitive data.",
            "Modify generated/vendor files unless explicitly requested.",
            "Fabricate commands, files, owners, branches, or policies.",
        ]),
        "CODEBASE_STATE": codebase_state(context),
        "TERMINOLOGY_ROWS": "| TBD | Ask the user for domain terms that agents often misunderstand |",
        "SCOPE_INDEX": scope_index(scopes).rstrip(),
    }


def manual_content(existing: str) -> str:
    if not existing.strip():
        return ""
    kept = []
    skipping = False
    for line in existing.splitlines():
        if line.startswith(GENERATED_START) or line.startswith("<!-- FOR AI") or line.startswith("<!-- Managed by agent:"):
            skipping = True
            continue
        if line.startswith(GENERATED_END):
            skipping = False
            continue
        if not skipping:
            kept.append(line)
    text = "\n".join(kept).strip()
    if not text:
        return ""
    return f"\n## Human Notes\n\n{text}\n"


def render_root(project: Path, template_dir: Path | None = None, profile: dict | None = None) -> str:
    existing = (project / "AGENTS.md").read_text(encoding="utf-8", errors="ignore") if (project / "AGENTS.md").exists() else ""
    template = load_template(template_dir or default_template_dir(), "root-agents.md")
    rendered = replace_placeholders(template, template_values(project, profile)).rstrip()
    return rendered + manual_content(existing) + "\n"


def render_scoped(scope: dict[str, str], template_dir: Path | None = None) -> str:
    path = scope["path"]
    template = load_template(template_dir or default_template_dir(), "scoped-agents.md")
    values = {
        "TIMESTAMP": today(),
        "VERIFIED_TIMESTAMP": "never",
        "SCOPE_NAME": path,
        "SCOPE_PATH": path,
        "SCOPE_OVERVIEW": f"{scope['purpose']}.",
        "LOCAL_COMMANDS": "Use root AGENTS.md commands unless this directory has its own package/config file.",
        "TESTING_RULES": "Run the narrowest relevant tests for files changed in this scope.",
        "LOCAL_STRUCTURE": "Document local key files here after inspecting this directory.",
        "CODE_STYLE": "Follow nearby files in this scope before introducing new patterns.",
        "GIT_WORKFLOW": "Follow root git workflow unless this scope documents a stricter local rule.",
        "LOCAL_BOUNDARIES": "- Ask before changing local public APIs, generated files, or ownership boundaries.",
        "SCOPE_PURPOSE": scope["purpose"],
    }
    return replace_placeholders(template, values).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render AGENTS.md from discovered project facts.")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--write", action="store_true", help="Write AGENTS.md files. Default prints root draft only.")
    parser.add_argument("--template-dir", default=None, help="Directory containing root-agents.md and scoped-agents.md.")
    parser.add_argument("--profile", default=None, help="Path to .agents/agents-control.json for strong-control rendering.")
    args = parser.parse_args()
    project = resolve_project(args.project)
    template_dir = Path(args.template_dir).resolve() if args.template_dir else None
    profile = load_profile(project, args.profile)
    root_text = render_root(project, template_dir, profile)

    if not args.write:
        print(root_text)
        return

    if profile:
        (project / "experience").mkdir(exist_ok=True)
    (project / "AGENTS.md").write_text(root_text, encoding="utf-8")
    for scope in detect_scopes(project)["scopes"]:
        scope_dir = project / scope["path"]
        if scope_dir.exists():
            agents_path = scope_dir / "AGENTS.md"
            if not agents_path.exists():
                agents_path.write_text(render_scoped(scope, template_dir), encoding="utf-8")


if __name__ == "__main__":
    main()
