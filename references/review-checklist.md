# AGENTS.md Review Checklist

Use this list for generated or edited governance. Check only sections affected by the task; run the full list before release.

## Entry And Design

- [ ] Repository facts were inspected before policy was inferred.
- [ ] Explicit AGENTS work continued past a healthy-root check; planning-only triggers stopped after the check.
- [ ] `default_conversation_language` is explicit, and natural-language responses stay in that configured language unless the user explicitly switches languages; Plan Mode follows the same rule.
- [ ] `use_remote_server`, `use_codebase_memory_mcp`, directory policy, and `extra_requirements` are explicit.
- [ ] Every interview group was confirmed. Write intent defaults to no review subagent; supplied or explicitly requested `design_review` evidence has `reviewer_type="subagent"`, matching `reviewed_answers_hash` / profile hash, and no pending confirmations.
- [ ] Read-only intent did not dispatch a reviewer.
- [ ] All non-testing subagents default to disabled. Authorization is a proactive, explicit current-task user request that names the role or purpose; generic multi-agent wording, complexity, ratings, risk, and agent judgment do not authorize dispatch.
- [ ] When authorized non-testing roles have no count, dispatch exactly three; honor an explicit count and do not carry authorization into another task.
- [ ] Work with an executable test surface uses one isolated `TESTER` with exclusive ownership of `tests/**`; pure read-only/planning work and documentation-only changes without a test surface do not require one. RED, BLOCKED, and SCOPE_REJECTED receipts include a structured failure report with concrete symptoms, expected/actual details, root cause, minimal fix, traceable evidence, residual jobs, and modification status.
- [ ] The canonical reviewer uses `fork_turns=none`, checks the approved design at INITIAL/every 10 minutes/CORRECTION/FINAL, is read-only, and reads worker state only from the current work-folder root `AGENTS.md`.
- [ ] Routine test-hash confirmation is prohibited: the Agent autonomously confirms only authoritative agreement, corrects report-only mismatches, and stops for user review without autonomous rerun when provenance conflicts or is insufficient.
- [ ] New test files use functional or behavioral semantic names with digit-free stems, including no `v1`, `v2`, `1`, `2`, `part1`, or `part2`; existing tests are not bulk-renamed.

## Content

- [ ] Root guidance is an operational index; detail lives in the nearest owner config or reference.
- [ ] Document registration ran only after an explicit user request; when enabled, its catalog, knowledge pointers, interface mappings, duplicate decisions, and Markdown hashes are current, while disabled skills created no registry state.
- [ ] Human text outside managed blocks is unchanged.
- [ ] No placeholder, obvious restatement, duplicated policy, or background without a decision remains.
- [ ] Compression preserved requirement strength, scope, exceptions, triggers, commands, paths, thresholds, and interfaces.
- [ ] Global, project, scoped, SKILL, prompt, reference, and memory-summary byte budgets pass.
- [ ] `agents/openai.yaml` keeps `short_description` at 25–64 characters and `default_prompt` as one concise `Use $agents-md-generator ...` sentence; detailed governance remains in `SKILL.md` and references.
- [ ] Scoped AGENTS contains verified local differences, not inherited root prose.
- [ ] Markdown formulas use `$...$` or `$$...$$` where applicable.

## Coding And Output Policy

- [ ] Generated root `AGENTS.md` must include Coding Behavior Baseline language skill routing from `.agents/global-rule-overrides.json`.
- [ ] `coding_behavior.language_skill_routing` has exactly `shared`, `python`, and `script`; `shared` is rendered once.
- [ ] Managed language-route refresh migrates the complete default route set and preserves any user-customized route value.
- [ ] Python remains with `readable-python-generator`; bat/cmd, shell/bash, PowerShell, and Tcl remain with `readable-script-generator`; wrappers that call Python remain script targets.
- [ ] The root retains readable formatting, the one-line compression prohibition, and the obfuscated-code prohibition.
- [ ] `script_output_policy` renders configured `Kind`, INFO/WARNING/ERR templates, Python `--quiet`, and the machine-readable exemption.

## Structure And Remote Safety

- [ ] Every managed root renders exactly one `Workspace boundary`: current and exact-routed verified remote work-folder changes need no additional confirmation; official codebase-memory start/refresh/rebuild/recovery is exempt only for the bound project and configured runtime cache/root persistence artifact; necessary side-effect-free reads remain allowed outside those boundaries; every other external write is prohibited until the user proactively requests the exact action, after which full disclosure and exactly one confirmation are required; target or scope changes invalidate it.
- [ ] Installed-skill installation, replacement, or direct modification always obtains exactly one explicit confirmation, even when it appears necessary for the task; no old double-confirmation language remains.
- [ ] Installed skill identity uses only the skill directory and root `SKILL.md`; CLI and settings are reported as separate capabilities, with the current remote CLI preferred and the legacy entry used only as fallback.
- [ ] The root-level file whitelist uses `allowed_root_files`; root work artifacts stay at the work-folder root and skill-local `evals/` remains allowed.
- [ ] Exactly one root `tests/` exists; Python tests live in one-level `tests/<feature>/` folders, root Python is limited to `tests/__init__.py`, and nested `tests/` directories are absent.
- [ ] Structure mutations were reviewed; blocked changes stopped unless force-confirmed and archived. `confirm-structure-fix` authorizes only the reviewed conservative repair.
- [ ] Remote registry and task-route table stay in `.agents/agents-control.json`; the root keeps only the pointer and runtime policy.
- [ ] Failed primary validation triggers the automatic fallback rule. Unmatched remote tasks must update AGENTS.md/profile before validation continues.
- [ ] Remote directory policy validates conda/runtime/archive paths. For every mutation, source and target paths must both stay inside the governed remote plan.
- [ ] Remote uploads are manifest-only; whole-folder/bundle uploads and `.git/`, `git/`, `github/`, `dist/`, and `ref/` sources are blocked, while directories expand to hashed per-file entries.
- [ ] `.settings/*.local.json` never reaches remote systems; remote `.settings/*.remote.json` remains allowed.
- [ ] Codebase-memory is root-only, ignored, persistent, `full`, ready, and has matching live/disk counts.

## Source And Runtime Gates

- [ ] Except for `__init__.py` and `__main__.py`, functional source and Python test names contain no digits, do not start with `_`, summarize the file function in lowercase English words, and keep the stem within 30 characters.
- [ ] Changed functional source and Python tests have current Agent semantic-review evidence whose revisions, path hash, summaries, and pass verdicts match the reviewed diff.
- [ ] Handwritten source over the configured 64KB UTF-8 limit has a valid decomposition plan.
- [ ] An installed skill copy with an oversized governed source resolves a complete bundled decomposition plan under `references/decomposition-plans/`, and an incomplete bundled plan still blocks validation.
- [ ] Changes to `scripts/python/docs/manage_docs_release.py`, `scripts/python/release/install_skill.py`, `scripts/python/detect/check_freshness.py`, or `scripts/python/verify/source_governance_config.py` update `references/script-guide.md`, this checklist, and `references/evaluation-scenarios.md` in the same review span.
- [ ] Release-document, install-target, source-readability, and decomposition-plan behavior each have a named verification command or evaluation scenario; undocumented gate changes block release review.
- [ ] Opaque source evidence excludes root and scoped `AGENTS.md` governance metadata, so freshness-only updates do not invalidate runtime source evidence.
- [ ] Readability rejects compressed, minified, overlong, or obfuscated source.
- [ ] Non-GUI script layout follows project config; exceptions are explicit.
- [ ] Long tasks follow the configured thread heartbeat policy only when supported and approved.
- [ ] Installed skills are not edited directly without explicit authorization.

## Verification

- [ ] Run the smallest targeted tests first.
- [ ] Run `quick_validate.py`, unit tests, `audit_skill.py`, `verify_agents.py`, docs `verify`, and `evaluate_skill.py` when changing this skill.
- [ ] `verify_agents.py` uses `--installed-skill-dir skills/agents-md-generator` for source-mode self-verification.
- [ ] Release/merge work also runs review governance, skill evals, release gates, receipt checks, and install-skip validation.
- [ ] `review_governance.py --mode release` is rerun after companion documentation changes and its deterministic findings are either resolved or recorded as an explicit reviewer decision.
- [ ] Dirty-worktree findings are separated from the committed diff; removed evolution/experience commands remain absent.
- [ ] Handoff names, memory schema/index, global baseline freshness, and generated-root freshness pass.
- [ ] Actual output is recorded; skipped checks and remaining risk are explicit.
