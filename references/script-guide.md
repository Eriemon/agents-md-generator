# Script Guide

All scripts use Python standard library only.

## Table of Contents

- [Detect](#detect)
- [Extract](#extract)
- [Render](#render)
- [Docs Governance](#docs-governance)
- [Verify](#verify)
- [Compatibility](#compatibility)

## Detect

```bash
python scripts/inspect_project.py /path/to/project
python scripts/detect_scopes.py /path/to/project
```

Outputs JSON facts for language, framework, package manager, CI, AI configs, directories, files, whether root `AGENTS.md` exists, and suggested scoped AGENTS.md directories.

## Extract

```bash
python scripts/collect_design_profile.py /path/to/project
python scripts/collect_design_profile.py /path/to/project --kind skill
python scripts/collect_design_profile.py /path/to/project --kind engineering
python scripts/collect_design_profile.py /path/to/project --answers answers.json
python scripts/collect_design_profile.py /path/to/project --answers answers.json --write
python scripts/select_engineering_rules.py --list
python scripts/select_engineering_rules.py --task refactor --mode mini --scope on-demand
python scripts/extract_commands.py /path/to/project
python scripts/extract_context.py /path/to/project
```

`collect_design_profile.py` first emits only question 1 plus branch options, because the user must confirm skill versus engineering development. After that answer, rerun with `--kind skill` or `--kind engineering` to emit the branch questions in order. Every question includes `options` with `label`, `value`, `description`, and `recommended` so the caller can provide selectable choices before accepting custom input. With `--answers`, it validates required answers and produces a normalized control profile plus `review_summary`, `confirmed_so_far`, and `confirmation_question`. With `--write`, it writes `.agents/agents-control.json` and scaffolds the `docs/` governance tree only when `alignment_confirmed=true`.

Optional book-derived engineering rule fields are `engineering_rule_primary`, `engineering_rule_mode`, `engineering_rule_scope`, and `engineering_rule_notes`. Use exactly one primary rule set. `mini` and `nano` are allowed modes; `full` is rejected for generated AGENTS.md output and stays reference-only. Scope must be `project-baseline`, `scoped`, or `on-demand`.

Skill development profiles also require `trigger_scenarios`, `skill_design_patterns`, `resource_plan`, `progressive_disclosure_policy`, `validation_gates`, `forward_testing_policy`, `development_requirements`, `expected_outcome`, `validation_method`, and `validation_granularity`. These fields render the Control Profile and Skill Design Contract and are verified before strong-control Skill projects can be written. User-developed Skills must use `skills/<skill-name>/SKILL.md`; `SKILL.md` frontmatter `name` must match the folder name and use only lowercase letters, digits, and hyphens. The generator's self-hosted source directory is the only legacy exception.

`select_engineering_rules.py` lists supported book-derived rule sets, recommends a primary rule set for task types such as `legacy`, `refactor`, `reliability`, `domain`, `data`, and `architecture`, rejects `full` for AGENTS.md output, and reports known equal-active conflicts or overlaps before those answers are written into the control profile.

`extract_commands.py` extracts candidate commands from Makefile, package.json, pyproject.toml, composer.json, go.mod, and GitHub Actions workflow `run:` lines. Commands are candidates, not verified execution results.

`extract_context.py` extracts docs, ADRs, utilities, quality configs, platform files, IDE/editor settings, architecture/ownership files, dependency automation configs, hook configs, GitHub settings/rulesets, reference projects, directory coverage candidates, agent configs, golden sample candidates, and CI rules for template sections that should point to existing files instead of copying prose.

## Render

```bash
python scripts/render_agents.py /path/to/project
python scripts/render_agents.py /path/to/project --profile /path/to/project/.agents/agents-control.json
python scripts/render_agents.py /path/to/project --write
python scripts/render_agents.py /path/to/project --profile /path/to/project/.agents/agents-control.json --write --confirm-docs-layout
python scripts/render_agents.py /path/to/project --template-dir /path/to/templates
```

Default mode is dry-run and prints the compressed root draft. `--profile` enables strong-control sections from `.agents/agents-control.json`; without it, output must say strong control is not configured. `--write` writes AGENTS.md files inside the target project, creates the `docs/` governance tree when a profile is present, and preserves hand-written content outside generated sections. Root and scoped AGENTS.md files must stay within 100 lines; if preserved hand-written content breaks that limit, `--write` fails before changing files. It must not create a root-level `experience/`; all experience summaries belong under `docs/experience/` as 10 numbered files. If docs preflight reports an ambiguous or conflicting existing `docs/` layout, `--write` exits before writing AGENTS.md or docs governance unless `--confirm-docs-layout` records explicit user confirmation. `--template-dir` is mainly for tests or deliberate template overrides; otherwise use bundled templates in `assets/templates/`.

## Docs Governance

```bash
python scripts/manage_docs.py preflight /path/to/project
python scripts/manage_docs.py scaffold /path/to/project
python scripts/manage_docs.py start-session /path/to/project --input session.json
python scripts/manage_docs.py resume-check /path/to/project
python scripts/manage_docs.py resume-repair /path/to/project --input recovery.json
python scripts/manage_docs.py handoff /path/to/project --input handoff.json
python scripts/manage_docs.py experience /path/to/project
python scripts/manage_docs.py experience /path/to/project --force
python scripts/manage_docs.py experience /path/to/project --payload experience-payload.json
python scripts/manage_docs.py evolve /path/to/project --force
python scripts/manage_docs.py development /path/to/project --stage release --input stage.json
python scripts/manage_docs.py verify /path/to/project
python scripts/manage_dirs.py init /path/to/project
python scripts/manage_dirs.py scan /path/to/project --write
python scripts/manage_dirs.py review /path/to/project --input change.json
python scripts/manage_dirs.py archive /path/to/project --reason "force-confirmed directory override"
python scripts/manage_dirs.py verify /path/to/project
```

`preflight` is read-only. It checks whether `docs/` is absent, already has a complete AGENTS.md governance tree, or has an ambiguous/conflicting existing layout. It returns `status`, `docs_exists`, `safe_to_scaffold`, `conflicts`, `requires_user_confirmation`, and `question`. If confirmation is required, ask the user before writing AGENTS.md or scaffolding docs governance.

`scaffold` creates `docs/handoff/`, `docs/handoff/history_handoff/`, `docs/experience/`, `docs/experience/history_experience/`, `docs/development/`, `docs/install_configuration/`, `docs/git_manager/`, and `docs/dir_manager/` including `change_reviews/` and `history_dir_manager/`. It also creates the latest handoff placeholder, install and git manager baselines, dir manager baselines, and 10 numbered experience files: fixed `1-workflow.md`, `2-scripts.md`, `3-plan.md`, `4-design-ui.md`, plus project-specific `5-*.md` through `10-*.md`.

`handoff` archives the previous `docs/handoff/HANDOFF.md` to `docs/handoff/history_handoff/HANDOFF-YYYYMMDD-HHMMSS.md`, writes the new latest handoff, increments `.agents/docs-governance-state.json`, and creates an AI experience update request every five handoffs. The input JSON can include `original_plan`, `current_step`, `problems`, `resolved`, `remaining`, `next`, `verification`, `conversation_summary`, `conversation_excerpt`, and `conversation_log_path`. Conversation fields are saved under `.agents/conversation-snapshots/` so future experience updates can read the latest 10 conversation materials.

`start-session` writes `.agents/active-session.json` after the current handoff is read and before task execution begins. `resume-check` compares that active session with the current `HANDOFF.md` hash and optional conversation log; an unchanged handoff with an active session is reported as an interrupted session. `resume-repair` writes a recovery handoff and clears the active session before the next request is handled.

`experience` without `--payload` does not write lessons. It writes `.agents/experience-update-request.json` when five new handoffs have accumulated, or immediately with `--force`. The request includes project facts, current and historical handoffs, current and historical experience files, target filenames, quality rules, and up to 10 recent conversation snapshots. If no conversation material exists, it sets `conversation_context_missing=true` instead of pretending the context is complete.

`experience --payload experience-payload.json` applies AI-authored lessons. The payload must declare `generated_by=ai` and provide all 10 files. The script validates that content is not a raw HANDOFF.md copy, not placeholder text, and not highly homogeneous across files. `1-workflow.md` must be detailed and include a complete workflow chain, logic chain, feedback/closure loop, and Mermaid `flowchart`. Existing current experience files are moved to `docs/experience/history_experience/YYYYMMDD-HHMMSS/` before accepted payload content is written. Files `5-*.md` through `10-*.md` remain selected deterministically from project facts such as testing, validation, release, installation, docs governance, directory governance, and remote deployment.

`evolve` writes automatic evolution templates after accepted experience passes quality checks. Every 10 completed handoffs, payload application triggers the same flow automatically. It reads the current plus latest historical versions of `1-workflow.md`, `2-scripts.md`, `3-plan.md`, and `4-design-ui.md`, then writes indexed templates under `assets/templates/evolution/skill-template/<type>/` and `assets/templates/evolution/engineering-template/<type>/`.

`development` writes a stage record under `docs/development/` for installable releases or stage completion. The input JSON can include `goal`, `completed_scope`, `verification`, `artifacts`, `version`, and `remaining_risks`.

`manage_dirs.py` is the strict local and remote deployment folder gate. `init` creates `DIR_MANAGER.md`, `current_structure.json`, `planned_structure.json`, `change_reviews/`, and `history_dir_manager/`; `planned_structure.json` includes `remote_deployment` with a workspace root, planned remote structure, protected remote paths, and review requirements, or `not configured` when no remote workspace is confirmed. `review` accepts JSON such as `{"changes":[{"action":"create","path":"features"}]}` and returns `approved`, `decision`, `reasons`, `risks`, `user_message`, `force_confirmation_required`, and `force_override_archive_required`. Blocked reviews exit non-zero and must be shown to the user before any force-confirmed folder change. If the user explicitly force-confirms a blocked change, run `archive` before applying it; this preserves the old dir manager content under `docs/dir_manager/history_dir_manager/YYYYMMDD-HHMMSS/`.

## Verify

```bash
python scripts/verify_agents.py /path/to/project
python scripts/verify_agents.py /path/to/project --include-skipped
python scripts/check_freshness.py /path/to/project
python scripts/audit_skill.py /path/to/agents-md-generator
python scripts/evaluate_skill.py /path/to/agents-md-generator /path/to/project
python scripts/install_skill.py /path/to/agents-md-generator --target skip
python scripts/install_skill.py /path/to/agents-md-generator --target codex --write
python scripts/install_skill.py /path/to/agents-md-generator --target custom --custom-root /path/to/skills --write
```

`verify_agents.py` checks generated markers, unresolved placeholders, path references, core structure, docs governance structure, dir manager files, config-backed package/Make/composer commands, and the 100 line AGENTS.md limit. For strong-control Skill projects, it also requires an exact `## Skill Design Contract` section with design patterns, resource boundaries, progressive disclosure, validation gates, and forward-testing policy. By default it skips development/reference/build trees such as `ref/`, `.git/`, `vendor/`, `dist/`, `build/`, `target/`, and `node_modules/`; use `--include-skipped` only when intentionally auditing those directories. `check_freshness.py` compares Last updated metadata with git history when available. `audit_skill.py` checks this skill's structure, frontmatter, referenced resources, and Python script compilation.

`install_skill.py` is a post-release install confirmation helper. Dry-run mode emits yes/no options and defaults to skip. It installs only with `--write`, supports `codex` and `custom` targets, and refuses to overwrite an existing skill unless `--replace` records explicit user confirmation. Replacement first moves the old installed skill to the sibling `skill_backups/<skill-name>-YYYYMMDD-HHMMSS/` folder, then preserves old `assets/templates/evolution/{engineering-template,skill-template}` files. If an evolved template conflicts with the new release, the installer keeps the new file, copies the old file as an `.installed-template-conflict` sibling, and reports `template_conflicts` for manual merge.

`evaluate_skill.py` runs the fact-level validation chain in one read-only command: unit tests, official skill quick validation, skill audit, AGENTS.md verification, and a render leak check. It emits JSON with each command, exit code, parsed errors, checked files, unresolved template placeholders, and local-reference leaks.

For reference capability coverage, read `references/capability-coverage.md`. It records which external generator capabilities are implemented, which are intentionally not copied, and where each behavior lives in this skill. For Skill design coverage, read `references/skill-design-coverage.md`; it records the distilled saved-HTML guidance and the contract checks. For book-derived engineering rule integration, read `references/book-rules-coverage.md`; it records the mini/nano/full policy, one-primary-rule-set constraint, and reference-only boundary for full material.

## Compatibility

```bash
python scripts/create_agent_shims.py /path/to/project
```

Creates CLAUDE.md and GEMINI.md next to each AGENTS.md. It prefers relative symlinks; if symlinks are unavailable it writes a managed shim. Existing non-managed files are preserved.

By default it skips development/reference/build trees such as `ref/`, `.git/`, `vendor/`, `dist/`, `build/`, `target/`, and `node_modules/`; use `--include-skipped` only for intentional audits.
