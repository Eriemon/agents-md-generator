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
- Keep default-language handling aligned across interview prompts, rendered AGENTS.md output, verification rules, and `agents/openai.yaml`; do not let any one layer silently weaken the language contract.
- Keep remote-server governance aligned across interview prompts, dependency gates, rendered AGENTS.md output, verification rules, and `agents/openai.yaml`; do not let any one layer bypass `erie-remote-ssh`.
- Keep remote structure governance separate from remote-server enablement and task-route mapping. A takeover interview may minimize identity questions, but it must still ask `use_remote_server` explicitly before any remote task route can be written and it must still complete the structured directory contract, including remote conda and runtime archive policy when remote structure is configured.
- Keep explicit AGENTS design/update requests separate from `计划` / `规划` / `准备` root-check triggers. Trigger-only checks may stop after reporting root health; explicit governance work must continue into the full interview/update flow.
- Restrict automatic takeover to version-mismatched old workspaces. Missing root files or missing version metadata must stay on the full grouped interview path.

## AGENTS.md Contract

For Skill development, generated AGENTS.md should include a Skill Design Contract with:

- Trigger scenarios that explain when the Skill should load.
- Design patterns selected for the Skill and why they matter.
- Resource boundaries for `SKILL.md`, `references/`, `scripts/`, `assets/`, and `agents/openai.yaml`.
- Progressive disclosure policy so the root instructions stay concise.
- Validation gates such as `python skills/agents-md-generator/scripts/quick_validate.py skills/agents-md-generator`, skill audit, AGENTS.md verification, and full evaluate chain.
- Validation method and validation granularity, including whether acceptance is automated, manual, forward-tested, or a combination.
- Forward-testing policy for complex or high-risk Skills.
- An explicit default-language reply rule in the root `AGENTS.md` whenever `default_language` metadata is present.
- A dedicated remote-server contract in the root `AGENTS.md` whenever remote usage is enabled, including the registered server registry, per-task primary/fallback routes, the automatic fallback gate, and the unmatched-task blocking gate.

Strong-control generated AGENTS.md should also include a Documentation Governance Contract. This contract records `docs/handoff/HANDOFF.md` as the newest handoff, requires time-suffixed handoff history, refreshes 10 numbered `docs/experience/` files every five handoffs, points stage, install, and git management records to `docs/development/`, `docs/install_configuration/`, and `docs/git_manager/`, requires `docs/dir_manager/` review before local or remote deployment folder structure changes, and archives old dir manager content to `docs/dir_manager/history_dir_manager/<timestamp>/` before user force-confirmed blocked changes are applied.

## AGENTS.md Principles

- Use Map, not manual: point agents to files, scripts, docs, and examples instead of pasting long manuals.
- Aggregate scripts: give agents one reliable command or wrapper instead of scattered shell fragments.
- Require a verification loop: code or content changes are not complete until the relevant checks run.
- Prefer automated rule checks when a rule can be verified mechanically.
- Keep task handoff and lesson capture in the docs governance tree instead of relying on memory.
- Keep experience lessons in 10 numbered `docs/experience/` files; never create a root-level `experience/` folder.
- New user-developed Skills belong in `skills/<skill-name>/`, and the `SKILL.md` frontmatter name must match that folder.
- Require selectable interview options and repeated summary confirmation before writing a strong-control profile.
- Require an explicit `default_conversation_language` answer before any AGENTS generation or takeover write; implicit fallback defaults are not acceptable.
- Require an explicit `use_remote_server` decision in interactive AGENTS generation flows; if remote usage is enabled, require erie-remote-ssh install/configure/choices/check/workspace-check completion before write, persist a normalized server registry plus task routes, and fall back to primary-server `functions` when a route omits explicit task responsibilities.
- Require the rendered root `AGENTS.md` to keep the explicit default-language rule and to state that remote validation must start with the matched task route's primary server, automatically try fallback servers after failed validation, and block unmatched tasks until AGENTS is updated.
- Put shared cross-repository principles in global `.codex/AGENTS.md`, but keep repository-specific long-task heartbeat detail, decomposition-plan locations, and GUI script exceptions in a local JSON governance config.
- Root `AGENTS.md` should point to `.agents/global-rule-overrides.json` instead of restating config-level maintainability and script-governance detail.
- The local JSON governance config locks source-file limits, decomposition-plan requirements, and the fixed non-GUI script quartet `scripts/python/<function>/<name>.py`, `scripts/shell/<function>/<name>.sh`, `scripts/bat/<function>/<name>.bat`, and `scripts/powershell/<function>/<name>.ps1`.
- Use a strict directory governance gate for folder moves; blocked reviews require explicit user force-confirmation and old dir manager content archival before execution.
- Keep local reference paths and temporary source folders out of generated AGENTS.md.

## Review Gate

Before claiming a Skill AGENTS.md is strict, verify that:

- The Skill Design Contract is generated from `.agents/agents-control.json`.
- The contract contains design patterns, resource boundaries, progressive disclosure, validation gates, validation method, validation granularity, and forward-testing policy.
- The generation flow explicitly asks for the default conversation language, the rendered root AGENTS.md locks natural-language replies to it, and verification fails if either side is missing.
- The generation flow explicitly asks whether remote servers are enabled, routes missing remote dependencies and server configuration through explicit user confirmation, records task-routed primary/fallback remote servers in AGENTS.md, and verification fails if the remote gate is incomplete.
- Temporary reference material is distilled into stable guidance and not copied as local paths.
- Docs governance verification confirms handoff, history, 10 numbered experience files, development, install configuration, git manager files, and remote deployment directory planning exist.
- The full validation chain reports no unresolved placeholders or local reference leaks.
