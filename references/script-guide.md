# Script Guide

All scripts use Python standard library only.

## Detect

```bash
python scripts/inspect_project.py /path/to/project
python scripts/detect_scopes.py /path/to/project
```

Outputs JSON facts for language, framework, package manager, CI, AI configs, directories, files, and suggested scoped AGENTS.md directories.

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

`collect_design_profile.py` first emits only question 1 plus branch options, because the user must confirm skill versus engineering development. After that answer, rerun with `--kind skill` or `--kind engineering` to emit the branch questions in order. With `--answers`, it validates required answers and produces a normalized control profile. With `--write`, it writes `.agents/agents-control.json` and creates `experience/`.

Optional book-derived engineering rule fields are `engineering_rule_primary`, `engineering_rule_mode`, `engineering_rule_scope`, and `engineering_rule_notes`. Use exactly one primary rule set. `mini` and `nano` are allowed modes; `full` is rejected for generated AGENTS.md output and stays reference-only. Scope must be `project-baseline`, `scoped`, or `on-demand`.

Skill development profiles also require `trigger_scenarios`, `skill_design_patterns`, `resource_plan`, `progressive_disclosure_policy`, `validation_gates`, and `forward_testing_policy`. These fields render the Skill Design Contract and are verified for strong-control Skill projects.

`select_engineering_rules.py` lists supported book-derived rule sets, recommends a primary rule set for task types such as `legacy`, `refactor`, `reliability`, `domain`, `data`, and `architecture`, rejects `full` for AGENTS.md output, and reports known equal-active conflicts or overlaps before those answers are written into the control profile.

`extract_commands.py` extracts candidate commands from Makefile, package.json, pyproject.toml, composer.json, go.mod, and GitHub Actions workflow `run:` lines. Commands are candidates, not verified execution results.

`extract_context.py` extracts docs, ADRs, utilities, quality configs, platform files, IDE/editor settings, architecture/ownership files, dependency automation configs, hook configs, GitHub settings/rulesets, reference projects, directory coverage candidates, agent configs, golden sample candidates, and CI rules for template sections that should point to existing files instead of copying prose.

## Render

```bash
python scripts/render_agents.py /path/to/project
python scripts/render_agents.py /path/to/project --profile /path/to/project/.agents/agents-control.json
python scripts/render_agents.py /path/to/project --write
python scripts/render_agents.py /path/to/project --template-dir /path/to/templates
```

Default mode is dry-run and prints the root draft. `--profile` enables strong-control sections from `.agents/agents-control.json`; without it, output must say strong control is not configured. `--write` writes AGENTS.md files inside the target project, creates `experience/` when a profile is present, and preserves hand-written content outside generated sections. `--template-dir` is mainly for tests or deliberate template overrides; otherwise use bundled templates in `assets/templates/`.

## Verify

```bash
python scripts/verify_agents.py /path/to/project
python scripts/verify_agents.py /path/to/project --include-skipped
python scripts/check_freshness.py /path/to/project
python scripts/audit_skill.py /path/to/agents-md-generator
python scripts/evaluate_skill.py /path/to/agents-md-generator /path/to/project
```

`verify_agents.py` checks generated markers, unresolved placeholders, path references, core structure, and config-backed package/Make/composer commands. For strong-control Skill projects, it also requires an exact `## Skill Design Contract` section with design patterns, resource boundaries, progressive disclosure, validation gates, and forward-testing policy. By default it skips development/reference/build trees such as `ref/`, `.git/`, `vendor/`, `dist/`, `build/`, `target/`, and `node_modules/`; use `--include-skipped` only when intentionally auditing those directories. `check_freshness.py` compares Last updated metadata with git history when available. `audit_skill.py` checks this skill's structure, frontmatter, referenced resources, and Python script compilation.

`evaluate_skill.py` runs the fact-level validation chain in one read-only command: unit tests, official skill quick validation, skill audit, AGENTS.md verification, and a render leak check. It emits JSON with each command, exit code, parsed errors, checked files, unresolved template placeholders, and local-reference leaks.

For reference capability coverage, read `references/capability-coverage.md`. It records which external generator capabilities are implemented, which are intentionally not copied, and where each behavior lives in this skill. For Skill design coverage, read `references/skill-design-coverage.md`; it records the distilled saved-HTML guidance and the contract checks. For book-derived engineering rule integration, read `references/book-rules-coverage.md`; it records the mini/nano/full policy, one-primary-rule-set constraint, and reference-only boundary for full material.

## Compatibility

```bash
python scripts/create_agent_shims.py /path/to/project
```

Creates CLAUDE.md and GEMINI.md next to each AGENTS.md. It prefers relative symlinks; if symlinks are unavailable it writes a managed shim. Existing non-managed files are preserved.

By default it skips development/reference/build trees such as `ref/`, `.git/`, `vendor/`, `dist/`, `build/`, `target/`, and `node_modules/`; use `--include-skipped` only for intentional audits.
