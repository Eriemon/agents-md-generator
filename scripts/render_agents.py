from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import detect_scopes, emit_json, extract_commands, extract_context, inspect_project, read_skill_version, resolve_project, today
from manage_dirs import apply_structure_fix, structure_gate
from manage_docs import bootstrap_experience, branch_gate, preflight_docs, scaffold as scaffold_docs


GENERATED_START = "<!-- AGENTS-GENERATED:START"
GENERATED_END = "<!-- AGENTS-GENERATED:END"
ROOT_AGENTS_MAX_BYTES = 12 * 1024


def command_rows(commands: list[dict[str, str]]) -> str:
    if not commands:
        return "| Verify manually | Ask user for project commands | unknown | user |"
    return "\n".join(
        f"| {item['task']} | `{item['command']}` | {item.get('time', '~30s')} | {item.get('source', 'unknown')} |"
        for item in commands
    )


def limit_lines(text: str, max_lines: int) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) <= max_lines:
        return "\n".join(lines)
    kept = lines[: max_lines - 1]
    kept.append(f"- Trimmed {len(lines) - len(kept)} additional entries; inspect source files for full detail.")
    return "\n".join(kept)


def limit_command_rows(rows: str, max_rows: int = 5) -> str:
    lines = [line for line in rows.splitlines() if line.strip()]
    if len(lines) <= max_rows:
        return "\n".join(lines)
    return "\n".join(lines[:max_rows] + [f"| More | {len(lines) - max_rows} additional commands omitted | inspect scripts/configs | generated |"])


def compact_section(marker: str, heading: str, body: str, max_body_lines: int | None = None) -> str:
    section_body = limit_lines(body, max_body_lines) if max_body_lines else "\n".join(line for line in body.splitlines() if line.strip())
    return "\n".join([
        f"{GENERATED_START} {marker} -->",
        f"## {heading}",
        section_body,
        f"<!-- AGENTS-GENERATED:END {marker} -->",
    ])


def root_size_errors(paths_to_text: list[tuple[str, str]]) -> list[str]:
    errors: list[str] = []
    for label, text in paths_to_text:
        if label != "AGENTS.md":
            continue
        size = len(text.encode("utf-8"))
        if size > ROOT_AGENTS_MAX_BYTES:
            errors.append(f"{label}: exceeds 12KB limit ({size} bytes); compress hand-written content before writing")
    return errors


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
    lines = [
        f"Primary language: {facts['primary_language']}. Framework: {facts['framework']}. Project type: {facts['project_type']}.",
    ]
    if facts.get("root_agents_md_exists"):
        if facts.get("root_agents_md_rebuild_required"):
            lines.append(f"Root AGENTS.md: present but trigger-required for agents-md-generator regeneration/restructure ({', '.join(facts.get('root_agents_md_trigger_reasons', facts.get('root_agents_md_rebuild_reasons', [])))}).")
        else:
            lines.append("Root AGENTS.md: present and version-aligned with the current local agents-md-generator.")
    else:
        lines.append("Root AGENTS.md: missing. Must trigger agents-md-generator root AGENTS/docs/workspace restructure handling before normal work.")
    return "\n".join(lines)


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
        f"- Version: {read_skill_version() or 'unknown'}.",
        f"- Default conversation language: {profile.get('default_conversation_language', '中文')}.",
        f"- Purpose: {profile.get('purpose', 'unknown')}.",
        f"- Reason: {profile.get('reason', 'unknown')}.",
    ]
    audience = profile.get("audience_or_environment")
    if audience:
        lines.append(f"- Audience/environment: {audience}.")
    if profile.get("development_requirements"):
        lines.append(f"- Development requirements: {profile['development_requirements']}.")
    if profile.get("expected_outcome"):
        lines.append(f"- Expected outcome: {profile['expected_outcome']}.")
    if profile.get("validation_method"):
        lines.append(f"- Validation method: {profile['validation_method']}.")
    if profile.get("validation_granularity"):
        lines.append(f"- Validation granularity: {profile['validation_granularity']}.")
    if profile.get("reference_materials_temporary"):
        lines.append("- Temporary reference materials were used; remove them manually after development and do not copy local reference paths into AGENTS.md.")
    return "\n".join(lines)


def directory_contract(profile: dict | None) -> str:
    if not profile:
        return "- Directory contract: not confirmed. Do not freeze structure until the user confirms local, remote, and feature-addition layout."
    contract = profile.get("directory_contract", {})
    dir_contract = profile.get("dir_manager_contract", {})
    lines = [
        f"- Confirmed: {contract.get('confirmed', False)}.",
        f"- Local structure: {contract.get('local', 'not specified')}.",
        f"- Remote structure: {contract.get('remote', 'not specified')}.",
        "- Remote deployment boundary: do not sync local skill-development content to remote servers; deploy only explicit runtime/deployment artifacts unless the user explicitly overrides.",
        f"- New feature structure: {contract.get('feature_rules', 'not specified')}.",
        "- Do not add new top-level directories or move ownership boundaries without updating this contract.",
        f"- Dir manager gate: review directory create/move/delete/rename plans with `{dir_contract.get('folder', 'docs/dir_manager')}/DIR_MANAGER.md` before changing folder structure.",
        "- Required command before folder changes: `python scripts/manage_dirs.py review <project> --input change.json`.",
        "- If directory review blocks the change, refuse default execution, explain the risk, and ask for explicit user force-confirmation before proceeding.",
        f"- After user force-confirmation and before applying the blocked folder change, archive old dir manager content to `{dir_contract.get('history', 'docs/dir_manager/history_dir_manager')}/YYYYMMDD-HHMMSS/` with `python scripts/manage_dirs.py archive <project> --reason \"force-confirmed directory override\"`.",
    ]
    primary_root = str(contract.get("primary_project_root", "")).strip()
    if primary_root:
        lines.insert(3, f"- Primary project root: `{primary_root}` must be the canonical location for the main skill or project content.")
        lines.insert(4, "- Existing work must already be placed at that primary root before strict control is confirmed.")
    return "\n".join(lines)


def release_contract(profile: dict | None) -> str:
    if not profile:
        return "- Release contract: not configured. Do not claim installable release packaging until the user confirms dist and zip rules."
    release = profile.get("release_contract", {})
    policy = profile.get("git_branch_policy", {})
    protected = policy.get("protected_branches", ["master", "release"])
    protected_text = ", ".join(f"`{item}`" for item in protected)
    return "\n".join([
        f"- Git management: {git_management_text(profile.get('git_management', 'not specified'))}.",
        f"- Branch model: {profile.get('branch_model', 'not specified')}.",
        f"- Protected branches: {protected_text}.",
        "- Development branches are allowed only as temporary local work branches.",
        "- Before releasing an installable `dist/` package: commit all work, merge into `master`, record the release, then delete local branches other than `master` and `release`.",
        f"- Dist folder: `{release.get('dist_folder', 'dist')}`.",
        f"- Release folder pattern: `{release.get('release_folder_pattern', '<name>-vx.x.x')}`.",
        f"- Zip required: {release.get('zip_required', True)}.",
        "- Before and after packaging, run `python scripts/manage_docs.py release-gate <project> --version vX.Y.Z --skill-dir skills/<skill-name> --phase pre|post`.",
        "- Keep the release commit and the current `docs/git_manager/CHANGELOG.md` entry together.",
        "- Do not push to a remote unless the user explicitly asks.",
    ])


def git_management_text(value: str) -> str:
    mapping = {
        "yes-local-only": "enabled locally; allow local branches and commits, but do not push remotely by default",
        "no-git-management": "disabled for this workflow; do not treat git operations as part of the normal execution path",
        "read-only": "legacy read-only mode; do not execute git writes and limit the workflow to planning/documentation unless the user overrides",
        "remote-allowed": "enabled with remote collaboration allowed when the user explicitly asks",
    }
    return mapping.get(str(value), str(value))


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
        f"- Validation method: {contract.get('validation_method', profile.get('validation_method', 'not specified'))}.",
        f"- Validation granularity: {contract.get('validation_granularity', profile.get('validation_granularity', 'not specified'))}.",
        f"- Validation gates: {contract.get('validation_gates', 'not specified')}.",
        f"- Forward testing: {contract.get('forward_testing_policy', 'not specified')}.",
        f"- Reference material policy: {contract.get('reference_material_policy', 'temporary inputs only')}.",
    ])


def conversation_completion_contract(profile: dict | None) -> str:
    return "\n".join([
        "- Finish all requested development work in the current conversation whenever feasible.",
        f"- Default conversation language: {profile.get('default_conversation_language', '中文') if profile else '中文'}. Unless the user explicitly switches language, continue in that language.",
        "- If work cannot be completed, report blockers, completed files, unverified assumptions, and exact next steps.",
        "- Run the smallest relevant checks during development and final verification before completion claims.",
        "- Preserve user changes and never rewrite the directory contract silently.",
    ])


def experience_log_contract(profile: dict | None) -> str:
    folder = "docs/experience"
    pattern = "1-xxxxx.md through 10-xxxxx.md"
    sections = [
        "evidence_read",
        "task_context",
        "how_to_apply",
        "problems_and_risks",
        "iterated_lessons",
        "next_application",
    ]
    required = ["1-workflow.md", "2-scripts.md", "3-plan.md", "4-design-ui.md"]
    conversation_limit = 10
    evolution_every = 10
    if profile:
        contract = profile.get("experience_contract", {})
        folder = contract.get("folder", folder)
        pattern = contract.get("file_pattern", pattern)
        sections = contract.get("required_sections", sections)
        required = contract.get("required_files", required)
        conversation_limit = int(contract.get("conversation_context_limit", conversation_limit))
        evolution_every = int(contract.get("evolution_every_handoffs", evolution_every))
    return "\n".join([
        f"- Maintain 10 project-specific numbered experience files under `{folder}/`.",
        f"- Fixed files: {', '.join(f'`{folder}/{item}`' for item in required)}.",
        f"- Project-specific files use `{pattern}` with names selected from current repository facts.",
        "- AI authors experience content; scripts only collect evidence, validate payloads, archive old files, and write accepted AI summaries.",
        f"- AI must read recent conversation context before experience updates: up to {conversation_limit} latest conversation snapshots.",
        "- Refresh cadence: every 5 completed handoffs creates an AI update request; apply with `manage_docs.py experience --payload experience-payload.json`.",
        f"- Evolution cadence: every {evolution_every} completed handoffs writes indexed templates under `assets/templates/evolution/` after quality checks pass.",
        f"- Required sections: {', '.join(sections)}.",
        "- Archive old current experience files under `docs/experience/history_experience/YYYYMMDD-HHMMSS/` before writing refreshed versions.",
    ])


def documentation_governance_contract(profile: dict | None) -> str:
    if not profile:
        return "\n".join([
            "- Docs governance: not configured.",
            "- Strong-control runs must create `docs/handoff/`, `docs/experience/`, `docs/development/`, `docs/install_configuration/`, `docs/git_manager/`, and `docs/dir_manager/`.",
            "- Run `python scripts/manage_docs.py scaffold <project>` before claiming docs governance is ready.",
        ])
    contract = profile.get("docs_contract", {})
    handoff = contract.get("handoff", {})
    experience = contract.get("experience", {})
    development = contract.get("development", {})
    install = contract.get("install_configuration", {})
    git = contract.get("git_manager", {})
    dir_manager = contract.get("dir_manager", {})
    targets = install.get("targets", ["Codex", "Claude", "OpenClaw"])
    if isinstance(targets, list):
        targets_text = ", ".join(str(item) for item in targets)
    else:
        targets_text = str(targets)
    return "\n".join([
        f"- Docs root: `{contract.get('root', 'docs')}`.",
        f"- Latest handoff: `{handoff.get('current', 'docs/handoff/HANDOFF.md')}` is always the newest task handoff.",
        f"- Experience folder: `{experience.get('folder', 'docs/experience')}` maintains 10 project-specific numbered experience files including `docs/experience/1-workflow.md`, `docs/experience/2-scripts.md`, `docs/experience/3-plan.md`, `docs/experience/4-design-ui.md`, plus `5-*.md` through `10-*.md`.",
        f"- Experience cadence: every 5 completed handoffs create an AI update request using up to {experience.get('conversation_context_limit', 10)} recent conversation snapshots; apply only AI-generated payloads and archive previous current files to `{experience.get('history', 'docs/experience/history_experience')}/YYYYMMDD-HHMMSS/`.",
        f"- Auto evolution: every {experience.get('evolution_every_handoffs', 10)} completed handoffs, distill approved experience into indexed templates under `{experience.get('evolution_templates', 'assets/templates/evolution/<matching-family>/<category>/<type>/')}`; topics stay project-specific and must not be copied into both template families.",
        f"- Git manager: keep the current change summary in `{git.get('folder', 'docs/git_manager')}/CHANGELOG.md`, archive older entries under `{git.get('folder', 'docs/git_manager')}/history_git_manager/YYYYMMDD-HHMMSS/`, and rotate with `manage_docs.py git-changelog`.",
        f"- Dir manager: keep strict local and remote deployment structure review rules under `{dir_manager.get('folder', 'docs/dir_manager')}/`; run `manage_dirs.py review` and keep `history_dir_manager/` archives.",
        "- Directory changes require `python scripts/manage_dirs.py review <project> --input change.json`; blocked reviews require explicit user force-confirmation and risk capture in handoff.",
        f"- Force-confirmed directory overrides must archive old dir manager content to `{dir_manager.get('history', 'docs/dir_manager/history_dir_manager')}/YYYYMMDD-HHMMSS/` before applying the folder change.",
        f"- Handoff history: archive the previous HANDOFF.md to `{handoff.get('history', 'docs/handoff/history_handoff')}` with `{handoff.get('archive_pattern', 'HANDOFF-YYYYMMDD-HHMMSS.md')}` before writing a new one.",
        f"- Development records: keep the latest file at `{development.get('current', 'docs/development/DEVELOPMENT.md')}` and archive older records under `{development.get('history', 'docs/development/history_development')}/YYYYMMDD-HHMMSS/DEVELOPMENT.md`.",
        f"- Install configuration: document skill installation and {targets_text} adapters under `{install.get('folder', 'docs/install_configuration')}`.",
        "- Use `python scripts/manage_docs.py handoff <project> --input handoff.json` at task completion.",
    ])


def template_values(project: Path, profile: dict | None = None) -> dict[str, str]:
    facts = inspect_project(project)
    commands = extract_commands(project)["commands"]
    scopes = detect_scopes(project)["scopes"]
    context = extract_context(project)
    command_source = ", ".join(sorted({item["source"] for item in commands})) if commands else "none detected"
    default_language = profile.get("default_conversation_language", "中文") if profile else "中文"
    current_version = read_skill_version() or "unknown"
    return {
        "TIMESTAMP": today(),
        "VERIFIED_TIMESTAMP": "never",
        "AGENTS_VERSION": current_version,
        "GENERATOR_VERSION": current_version,
        "DEFAULT_LANGUAGE": default_language,
        "PROJECT_OVERVIEW": project_overview(facts),
        "CONTROL_PROFILE": control_profile(profile),
        "DIRECTORY_CONTRACT": directory_contract(profile),
        "RELEASE_CONTRACT": release_contract(profile),
        "ENGINEERING_RULE_CONTRACT": engineering_rule_contract(profile),
        "SKILL_DESIGN_CONTRACT": skill_design_contract(profile),
        "CONVERSATION_COMPLETION_CONTRACT": conversation_completion_contract(profile),
        "EXPERIENCE_LOG_CONTRACT": experience_log_contract(profile),
        "DOCUMENTATION_GOVERNANCE_CONTRACT": documentation_governance_contract(profile),
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
            "Sync local skill-development content to remote servers during deployment unless the user explicitly overrides.",
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
    generated_boilerplate = {
        "# AGENTS.md",
        "**Precedence:** the closest `AGENTS.md` to the files being changed wins. Explicit user prompts override this file.",
        "### Always Do",
        "### Ask First",
        "### Never Do",
        "Use this order: explicit user prompt, closest AGENTS.md, parent AGENTS.md, general repository docs.",
    }
    generated_plain_blocks = {
        "## Agent Work Loop",
        "## Boundaries",
        "## When Instructions Conflict",
    }
    generated_prefixes = ("<!-- Last updated:", "<!-- AGENTS-METADATA:")
    kept = []
    skipping_marker = False
    skipping_plain_block = False
    for line in existing.splitlines():
        stripped = line.strip()
        if line.startswith(GENERATED_START):
            skipping_marker = True
            skipping_plain_block = False
            continue
        if line.startswith(GENERATED_END):
            skipping_marker = False
            continue
        if skipping_marker:
            continue
        if line.startswith("<!-- FOR AI") or line.startswith("<!-- Managed by agent:") or line.startswith(generated_prefixes):
            continue
        if stripped == "## Human Notes":
            skipping_plain_block = False
            continue
        if stripped in generated_plain_blocks:
            skipping_plain_block = True
            continue
        if skipping_plain_block and stripped.startswith("## "):
            skipping_plain_block = False
        if skipping_plain_block:
            continue
        if stripped not in generated_boilerplate:
            kept.append(line)
    text = "\n".join(kept).strip()
    if not text:
        return ""
    return f"\n## Human Notes\n\n{text}\n"


def render_root(project: Path, template_dir: Path | None = None, profile: dict | None = None) -> str:
    existing = (project / "AGENTS.md").read_text(encoding="utf-8", errors="ignore") if (project / "AGENTS.md").exists() else ""
    if template_dir is None:
        values = template_values(project, profile)
        manual = manual_content(existing).strip()
        engineering_max = 6 if profile and profile.get("engineering_rule_contract", {}).get("primary") != "none" else 2
        skill_max = 9 if profile and profile.get("kind") == "skill" else 2
        context_body = "\n".join([values["KEY_DECISIONS"], values["UTILITY_ROWS"], values["CODEBASE_STATE"]])
        parts = [
            "<!-- FOR AI AGENTS - Human readability is a side effect, not a goal -->",
            "<!-- Managed by agent: keep sections and order; edit content outside AGENTS-GENERATED blocks -->",
            f"<!-- Last updated: {values['TIMESTAMP']} | Last verified: {values['VERIFIED_TIMESTAMP']} -->",
            f"<!-- AGENTS-METADATA: agents_version={values['AGENTS_VERSION']}; generator_version={values['GENERATOR_VERSION']}; default_language={values['DEFAULT_LANGUAGE']} -->",
            "# AGENTS.md",
            "**Precedence:** the closest `AGENTS.md` to the files being changed wins. Explicit user prompts override this file.",
            compact_section("project-overview", "Project Overview", values["PROJECT_OVERVIEW"], 2),
            compact_section("control-profile", "Control Profile", values["CONTROL_PROFILE"], 8),
            compact_section("directory-contract", "Directory Contract", values["DIRECTORY_CONTRACT"], 5),
            compact_section("release-contract", "Release Contract", values["RELEASE_CONTRACT"], 9),
            compact_section("engineering-rule-contract", "Engineering Rule Contract", values["ENGINEERING_RULE_CONTRACT"], engineering_max),
            compact_section("skill-design-contract", "Skill Design Contract", values["SKILL_DESIGN_CONTRACT"], skill_max),
            "\n".join([
                f"{GENERATED_START} commands -->",
                f"## Commands ({values['VERIFICATION_STATUS']})",
                "| Task | Command | ~Time | Source |",
                "|------|---------|-------|--------|",
                limit_command_rows(values["COMMAND_ROWS"]),
                "<!-- AGENTS-GENERATED:END commands -->",
            ]),
            compact_section("conversation-completion-contract", "Conversation Completion Contract", values["CONVERSATION_COMPLETION_CONTRACT"], 2),
            compact_section("documentation-governance-contract", "Documentation Governance Contract", values["DOCUMENTATION_GOVERNANCE_CONTRACT"], 8),
            compact_section("directory-coverage", "Directory Coverage", values["DIRECTORY_COVERAGE"], 2),
        ]
        if "Link ADRs or architecture docs here" not in values["KEY_DECISIONS"] or "Add migrations, tech debt" not in values["CODEBASE_STATE"] or "Existing utility" in values["UTILITY_ROWS"]:
            parts.append(compact_section("repository-context", "Repository Context", context_body, 10))
        if "No hook framework detected" not in values["HOOK_POLICY"]:
            parts.append(compact_section("hook-policy", "Hook Policy", values["HOOK_POLICY"], 3))
        if "No GitHub settings or rulesets detected" not in values["GITHUB_SETTINGS"]:
            parts.append(compact_section("github-settings", "GitHub Settings", values["GITHUB_SETTINGS"], 3))
        parts.extend([
            "\n".join([
                "## Boundaries",
                "### Always Do",
                limit_lines(values["ALWAYS_RULES"], 2),
                "### Ask First",
                limit_lines(values["ASK_FIRST_RULES"], 2),
                "### Never Do",
                limit_lines(values["NEVER_RULES"], 2),
            ]),
            "## When Instructions Conflict",
            "Use this order: explicit user prompt, closest AGENTS.md, parent AGENTS.md, general repository docs.",
        ])
        if manual:
            parts.append(manual)
        return "\n".join(parts).rstrip() + "\n"
    template = load_template(template_dir or default_template_dir(), "root-agents.md")
    values = template_values(project, profile)
    rendered = replace_placeholders(template, values).rstrip()
    metadata = f"<!-- AGENTS-METADATA: agents_version={values['AGENTS_VERSION']}; generator_version={values['GENERATOR_VERSION']}; default_language={values['DEFAULT_LANGUAGE']} -->"
    return metadata + "\n" + rendered + manual_content(existing) + "\n"


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
    parser.add_argument("--confirm-docs-layout", action="store_true", help="User confirmed that docs governance may be added under the existing docs/ layout.")
    parser.add_argument("--confirm-structure-fix", action="store_true", help="User explicitly confirmed applying recommended structure normalization before writing.")
    parser.add_argument("--confirm-branch-governance", action="store_true", help="User explicitly confirmed continuing after a blocked branch governance check.")
    args = parser.parse_args()
    project = resolve_project(args.project)
    template_dir = Path(args.template_dir).resolve() if args.template_dir else None
    profile = load_profile(project, args.profile)
    root_text = render_root(project, template_dir, profile)

    if not args.write:
        print(root_text)
        return

    if profile:
        structure_result = structure_gate(project)
        if not structure_result.get("approved", True) and not args.confirm_structure_fix:
            emit_json({
                "errors": ["structure governance requires user confirmation before writing AGENTS.md or docs governance"],
                "structure_gate": structure_result,
                "requires_user_confirmation": True,
            })
            raise SystemExit(1)
        branch_result = branch_gate(project)
        if not branch_result.get("approved", True) and not args.confirm_branch_governance:
            emit_json({
                "errors": ["branch governance requires user confirmation before writing AGENTS.md or docs governance"],
                "branch_gate": branch_result,
                "requires_user_confirmation": True,
            })
            raise SystemExit(1)
        if args.confirm_structure_fix:
            structure_fix = apply_structure_fix(project)
            if structure_fix.get("errors"):
                emit_json({
                    "errors": ["structure governance fix failed before writing AGENTS.md or docs governance"],
                    "structure_fix": structure_fix,
                })
                raise SystemExit(1)
        docs_preflight = preflight_docs(project)
        if docs_preflight["requires_user_confirmation"] and not args.confirm_docs_layout:
            emit_json({
                "errors": ["docs layout requires user confirmation before writing AGENTS.md or docs governance"],
                "docs_preflight": docs_preflight,
                "requires_user_confirmation": True,
            })
            raise SystemExit(1)
        scaffold_docs(project)
        facts = inspect_project(project)
        if facts.get("session_history_bootstrap_required"):
            bootstrap_experience(project)
        root_text = render_root(project, template_dir, profile)
    pending_writes: list[tuple[Path, str]] = [(project / "AGENTS.md", root_text)]
    for scope in detect_scopes(project)["scopes"]:
        scope_dir = project / scope["path"]
        if scope_dir.exists():
            agents_path = scope_dir / "AGENTS.md"
            if not agents_path.exists():
                pending_writes.append((agents_path, render_scoped(scope, template_dir)))
    errors = root_size_errors([(path.relative_to(project).as_posix(), text) for path, text in pending_writes])
    if errors:
        emit_json({"errors": errors, "max_bytes": ROOT_AGENTS_MAX_BYTES})
        raise SystemExit(1)
    for path, text in pending_writes:
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
