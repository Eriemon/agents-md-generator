# Skill Design Coverage

This file distills the useful guidance from local saved HTML reference material into durable rules for Skill-focused AGENTS.md generation. Do not copy downloaded CSS or JS from saved web pages into the skill; only keep decision-changing constraints.

## Patterns

| Pattern | Use in Skill design |
|---------|---------------------|
| Tool Wrapper | Put repeatable, deterministic, or fragile operations in `scripts/` so agents run tools instead of rewriting logic |
| Generator | Use `assets/` templates when output shape must stay stable across runs |
| Reviewer | Store review criteria in `references/` and automate checks that can be deterministic |
| Inversion | Ask required intent questions before generation when files cannot reveal the answer |
| Pipeline | Encode hard checkpoints such as detect, collect, render, verify, audit, and evaluate |

Patterns can be combined. A strong Skill often uses Inversion to collect intent, Generator to produce stable output, Tool Wrapper for scripts, Reviewer for checks, and Pipeline to enforce order.

## Progressive Disclosure

- Keep `SKILL.md` focused on trigger, core workflow, and resource navigation.
- Move detailed policy, examples, schemas, and checklists into one-level `references/` files.
- Put reusable deterministic code in `scripts/`; test scripts by running them.
- Put output templates and copied starter material in `assets/`.
- Keep `agents/openai.yaml` aligned with `SKILL.md` and regenerate or update it when stale.

## AGENTS.md Contract

For Skill development, generated AGENTS.md should include a Skill Design Contract with:

- Trigger scenarios that explain when the Skill should load.
- Design patterns selected for the Skill and why they matter.
- Resource boundaries for `SKILL.md`, `references/`, `scripts/`, `assets/`, and `agents/openai.yaml`.
- Progressive disclosure policy so the root instructions stay concise.
- Validation gates such as `quick_validate.py`, skill audit, AGENTS.md verification, and full evaluate chain.
- Forward-testing policy for complex or high-risk Skills.

Strong-control generated AGENTS.md should also include a Documentation Governance Contract. This contract records `docs/handoff/HANDOFF.md` as the newest handoff, requires time-suffixed handoff history, refreshes `docs/experience/` lessons every five handoffs, and points stage, install, and git management records to `docs/development/`, `docs/install_configuration/`, and `docs/git_manager/`.

## AGENTS.md Principles

- Use Map, not manual: point agents to files, scripts, docs, and examples instead of pasting long manuals.
- Aggregate scripts: give agents one reliable command or wrapper instead of scattered shell fragments.
- Require a verification loop: code or content changes are not complete until the relevant checks run.
- Prefer automated rule checks when a rule can be verified mechanically.
- Keep task handoff and lesson capture in the docs governance tree instead of relying on memory.
- Keep local reference paths and temporary source folders out of generated AGENTS.md.

## Review Gate

Before claiming a Skill AGENTS.md is strict, verify that:

- The Skill Design Contract is generated from `.agents/agents-control.json`.
- The contract contains design patterns, resource boundaries, progressive disclosure, validation gates, and forward-testing policy.
- Temporary reference material is distilled into stable guidance and not copied as local paths.
- Docs governance verification confirms handoff, history, experience, development, install configuration, and git manager files exist.
- The full validation chain reports no unresolved placeholders or local reference leaks.
