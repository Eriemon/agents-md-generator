# AGENTS.md Review Checklist

Run `python skills/agents-md-generator/scripts/verify_agents.py . --installed-skill-dir skills/agents-md-generator` first, then use this checklist for judgment that scripts cannot fully automate.

## Table of Contents

- [Script Gates](#script-gates)
- [Content Checks](#content-checks)
- [Safety Checks](#safety-checks)
- [Update Checks](#update-checks)

## Script Gates

| Gate | Required evidence |
|------|-------------------|
| Structure | `python skills/agents-md-generator/scripts/quick_validate.py skills/agents-md-generator` passes for this skill |
| Facts | `python skills/agents-md-generator/scripts/inspect_project.py <project>` output reviewed |
| Design profile | grouped design interview completed with `collect_design_profile.py --start/--resume/--answer-file`, `extra_requirements` recorded, final alignment confirmed, and either read-only completion retained as `answers_snapshot`/`profile_preview` or write intent completed with approved subagent `design_review` plus matching hashes before `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --answers answers.json --write` |
| Commands | `python skills/agents-md-generator/scripts/extract_commands.py <project>` output reviewed |
| Context | `python skills/agents-md-generator/scripts/extract_context.py <project>` output reviewed |
| Scopes | `python skills/agents-md-generator/scripts/detect_scopes.py <project>` output reviewed |
| Task rating gate | `python skills/agents-md-generator/scripts/task_rating_gate.py --project <project> --task-text "<user task>" --json` used when a global-entry task may otherwise waste tokens on unnecessary difficulty/scale questions |
| Content | `python skills/agents-md-generator/scripts/verify_agents.py <project>` has no errors and does not scan skipped development/reference trees by default |
| Docs preflight | `python skills/agents-md-generator/scripts/manage_docs.py preflight <project>` is safe, or user confirmation is recorded for an ambiguous/conflicting existing `docs/` layout |
| Session bootstrap | When the workspace already has landed content but no root `AGENTS.md`, `python skills/agents-md-generator/scripts/manage_docs.py bootstrap-experience <project>` has been reviewed and exact-cwd session matching is correct |
| Docs governance | `python skills/agents-md-generator/scripts/manage_docs.py verify <project>` has no errors for strong-control projects |
| Work-folder governance | `python skills/agents-md-generator/scripts/manage_docs.py work-folder-gate <project> --skill-dir skills/<skill-name> --mode development|release` passes when the task depends on resume, structure, branch, version, and freshness state |
| Branch governance | `python skills/agents-md-generator/scripts/manage_docs.py branch-gate <project>` passes before strong-control generation on external work folders |
| Structure governance | `python skills/agents-md-generator/scripts/manage_dirs.py structure-gate <project>` passes or explicit confirmation for normalization is recorded before strong-control generation continues |
| Directory governance | `python skills/agents-md-generator/scripts/manage_dirs.py verify <project>` passes, and folder changes have a passing `manage_dirs.py review` result |
| Book rules | `python skills/agents-md-generator/scripts/select_engineering_rules.py --list` or `--task <type>` used when a book-derived engineering rule set is selected |
| Skill design | `references/skill-design-coverage.md` reviewed when the target is Skill development |
| Freshness | `python skills/agents-md-generator/scripts/check_freshness.py <project>` reviewed for existing AGENTS.md |
| Compatibility | `python skills/agents-md-generator/scripts/create_agent_shims.py <project>` used only when requested |
| Install confirmation | only skill-development release flows ask about `install_skill.py`; source directories must be rejected, release receipts plus `release_content_policy` must validate, forbidden development content must block dry-run and write installs, and replacement installs must show `backup_path` and no unreviewed template loss |
| Skill self-audit | `python skills/agents-md-generator/scripts/audit_skill.py skills/agents-md-generator` has no errors after skill edits |
| Fact-level validation | `python skills/agents-md-generator/scripts/evaluate_skill.py skills/agents-md-generator <project>` returns `"ok": true` after skill edits |
| Skill effectiveness | `python tests/run_skill_evals.py skills/agents-md-generator/evals/evals.json` passes, every case reports with-skill improvement over the without-skill baseline, recent high-risk regressions and all five Skill design patterns are covered, and eval helper implementations stay under `tests/` |
| Automated review governance | `python skills/agents-md-generator/scripts/review_governance.py <project> --base <sha> --head HEAD --skill-dir skills/<skill-name> --mode release` passes before release or merge when governance-sensitive files changed; ordinary `all|code|design` analysis may still emit optional review metadata without requiring reviewer dispatch |
| Confidence gate | `python skills/agents-md-generator/scripts/run_confidence_gate.py <project> --review-base <sha> --external-skill-dir <healthy-skill-dir>` is available when one aggregate pass should summarize quick validation, source governance, docs/work-folder governance, freshness, automated review, verify, evaluate, skill-effectiveness, release, install, and external-skill evaluation evidence |
| Confidence closure | Do not claim complete or 100% confidence unless docs governance, verify, audit, evaluate, skill-effectiveness evals, and the current release/install gates all agree |

`review_governance.py` only evaluates the committed diff between `--base` and `--head`. A dirty worktree is not acceptable substitute evidence; `branch-gate`, `work-folder-gate`, and the confidence gate must still block dirty worktree states before release or completion claims.

## Content Checks

- Every referenced path exists, or is clearly marked as planned/user-supplied.
- Every command has a source such as Makefile, package.json, pyproject.toml, composer.json, go.mod, CI, or user answer.
- Package, Makefile, and composer commands point to scripts or targets that actually exist.
- Context sections point to real docs, ADRs, platform files, IDE settings, dependency configs, reference projects, and golden samples instead of copying them.
- Hook Policy reflects detected hook frameworks and forbids `--no-verify` bypasses.
- GitHub Settings reflects CODEOWNERS, Copilot instructions, dependency configs, and rulesets when present.
- Directory Coverage identifies major directories that may need scoped AGENTS.md files.
- Capability coverage has been checked against `references/capability-coverage.md` before claiming parity with another generator.
- Book-derived engineering rules use exactly one primary active rule set, mode `mini` or `nano`, explicit scope, and no full material in AGENTS.md.
- Strong-control AGENTS.md includes Control Profile, Directory Contract, Release Contract, Engineering Rule Contract, Conversation Completion Contract, and Documentation Governance Contract.
- Strong-control Skill AGENTS.md includes Skill Design Contract with design patterns, resource boundaries, progressive disclosure, validation gates, and forward-testing policy.
- Generated root `AGENTS.md` must include `## Code Comment Policy`, point to `.agents/global-rule-overrides.json`, and summarize the configurable Chinese Python/C/C++/Verilog 配置化注释策略 without embedding long examples in the root file.
- Generated root `AGENTS.md` must include `## Script Output Policy`, point to `.agents/global-rule-overrides.json`, state strict `> INFO: [{kind}]` / `> WARNING: [{kind}]` / `> ERR: [{kind}]` process-output formats, keep `Kind` values config-driven, require Python `--quiet` for INFO/progress suppression, and exempt machine-readable output from prefixes.
- Root `AGENTS.md` stays within `16KB`; scoped `AGENTS.md` files are not rejected for exceeding the old line-count rule.
- Root `AGENTS.md` should point to `.agents/global-rule-overrides.json` instead of repeating maintainability, script-layout, or long-task heartbeat detail in prose.
- Review the config-backed gates from `.agents/global-rule-overrides.json`: source-governance hard-fail extensions use the configured 1000-line limit by default, oversized matches block immediately, eval/smoke/fixture helpers stay under `tests/`, non-GUI tools must satisfy the fixed quartet `scripts/python/<function>/<name>.py`, `scripts/shell/<function>/<name>.sh`, `scripts/bat/<function>/<name>.bat`, and `scripts/powershell/<function>/<name>.ps1`, and `script_output_policy.kinds` remains a configurable non-empty list rather than a code enum.
- Long-running Python automation policy is also config-backed: if a task is expected to run long, the flow must ask first before enabling thread heartbeat follow-up, and completion should delete the heartbeat after continuation.
- Remote governance reminders must keep the explicit automatic fallback rule, the rule that unmatched remote tasks must update AGENTS.md before validation continues, and the rule that source and target paths must both stay inside the governed remote plan.
- Workspace engineering config must live under `.settings/`: `.settings/project.local.json` / `.settings/<name>.local.json` stay local-only, `.settings/project.remote.json` / `.settings/<name>.remote.json` are the remote-safe project config names, and `.settings/server_list.local.json` must never be copied to remote servers.
- Skill and engineering design interviews expose selectable options, repeat `review_summary` confirmation after each answer group, persist unfinished progress in `.agents/design-interview-state.json`, ask the `extra_requirements` supplement question after grouped questions, and set `alignment_confirmed=true` only after the final full-design confirmation.
- Strong-control writes must reject missing `extra_requirements`, missing explicit `use_remote_server`, and any missing, human, rejected, confirmation-pending, or hash-mismatched `design_review`; approved reviews must have `reviewer_type="subagent"` and matching `reviewed_answers_hash` / `reviewed_profile_hash`.
- If subagent `design_review` returns `reject` or non-empty `required_user_confirmations`, the workflow must enter review rework, ask the user to confirm correction items, clear old review evidence, and repeat final alignment plus subagent review before write.
- `--intent read_only` must stop at `completed_read_only`, preserve `answers_snapshot` and `profile_preview`, and must not emit `design_review_request` until `--enter-write-review` is explicitly requested.
- Question `32` for `default_conversation_language` must be explicitly asked and confirmed in every AGENTS generation or takeover-restructure flow; do not infer it from defaults or repository heuristics.
- If `default_conversation_language` is locked in the root contract, Plan Mode must obey the same lock: any content inside `<proposed_plan>` must use that configured default language unless the user explicitly switches languages.
- Question `45` for `use_remote_server` must be explicitly asked in every AGENTS generation or takeover-restructure flow. If the user enables remote servers, the workflow must not bypass the dependency/configuration/task-route-mapping/validation gates.
- When remote servers are enabled, the remote server contract must record a server registry plus one or more task routes. Explicit user route-task assignments win; otherwise each route falls back to the selected primary server `functions` so the task list is never empty.
- Takeover mode may minimize identity questions, but remote structure governance must stay separate from remote-server enablement and task-route mapping; known structure facts do not remove the requirement to ask whether remote servers are needed, and takeover must still complete the structured directory-contract interview, `extra_requirements`, final alignment, and subagent design review before write.
- New and existing projects both must answer the directory-contract group so local structure, remote structure, feature-placement rules, remote conda placement, and remote runtime archive rules are explicit before strong control is written.
- When remote directory policy is enabled, remote conda/runtime path templates must be safe relative templates: no `..`, no wildcards or unsafe shell characters, no repeated separators, and no absolute paths relative to the remote workspace root.
- Skill development profiles include detailed development requirements, development purpose, expected result, validation method, and validation granularity before strong control is written.
- User-developed Skills live under `skills/<skill-name>/SKILL.md`; `SKILL.md` frontmatter `name` exactly matches the folder name and uses lowercase letters, digits, and hyphens.
- If `has_existing_work=yes` for a Skill project, the expected `skills/<skill-name>/SKILL.md` must already exist on disk; answer text alone is not enough.
- If `has_existing_work=yes` for an engineering project, the expected `engineering/<project-name>/` root must already exist on disk.
- When a workspace already has landed content but no root `AGENTS.md`, bootstrap history must read only exact-cwd Codex sessions from `.codex/sessions`; do not mix in neighboring or similarly named repositories.
- Session bootstrap should write one `history_experience` snapshot per matched session and one latest current `docs/experience/*.md` set for the current workspace.
- External work folders with enabled git management must pass branch governance before strong-control generation: current branch, local branch set, and worktree state must match the configured branch model or be explicitly escalated.
- Branch, release, directory, remote, and install prompts should expose a structured `decision_request` object in addition to legacy prose fields so callers can present confirmation consistently without parsing free text.
- `review_governance.py` must fail deterministic companion-change gaps: script changes need tests, CLI changes need script-guide updates, gate changes need review-checklist plus eval/evaluation-scenario coverage, and VERSION changes need DEVELOPMENT, CHANGELOG, and GIT_MANAGER current-version updates.
- `review_governance.py` must expose `review_dispatch_policy`; non-release modes must stay `optional` or `none`, and `required_manual_review=true` is reserved for `--mode release`.
- `check_freshness.py` should use `Last verified` when it is newer than `Last updated`, and `sync-root-agents --mark-verified --write` should mark that verification without rewriting the AGENTS body.
- `sync-root-agents --write` should repair both root metadata and the managed Control Profile `Version:` line when the target project skill `VERSION` changes; release evidence is incomplete if the suggested repair command still leaves Control Profile drift behind.
- `manage_docs.py verify` should enforce split version semantics: root `AGENTS.md` metadata follows the installed `agents-md-generator` version, while the Control Profile plus DEVELOPMENT, CHANGELOG, and GIT_MANAGER follow the target project skill `VERSION` when that file exists.
- `check_source_governance.py` / `evaluate_skill.py` should survive malformed Python by returning structured violations or classified errors; parser crashes in those paths are release blockers because they destroy governance evidence.
- External workspaces must not vendor governance runtime scripts from `agents-md-generator`: generated AGENTS/docs commands should call the installed runtime such as `python <codex-home>/skills/agents-md-generator/scripts/manage_docs.py ...`, and project-local commands like `python scripts/manage_docs.py ...` or `python skills/<project-skill>/scripts/manage_docs.py ...` must be rejected.
- Git-managed Release Contract text must explicitly forbid repointing repositories with `git config core.worktree`; require normal checkout/merge or explicit `git worktree` usage instead.
- If the current file structure violates the governed primary root or allowed top-level roots, the workflow must ask whether to normalize it before modifying files, and the recommended default should be yes.
- Missing root `AGENTS.md` is a mandatory abnormal state for agents-md-generator root AGENTS/docs/workspace handling; the skill must report the problem and ask whether to enter AGENTS design or restructuring.
- Missing `agents_version` or `generator_version`, or either value mismatching the installed `agents-md-generator` version, is also a mandatory abnormal state for root AGENTS/docs/workspace handling; do not treat it as a normal warning.
- Old work folders with landed content plus version-mismatched root `AGENTS.md` may enter takeover mode after confirming only the minimal identity fields first, but they must still complete the structured directory contract before write; missing root files or missing version metadata must stay on the full grouped interview.
- User requests containing `计划`, `规划`, or `准备` should first run the current-workspace/current-repository/current-work-folder root `AGENTS.md` check.
- If that root check passes, the trigger path should only report that the check passed and must not silently continue into AGENTS design work.
- If that root check fails, the trigger path should report the exact abnormal reason and ask whether to enter AGENTS.md design or restructuring.
- Explicit AGENTS.md / agent-rules / scoped-AGENTS requests should continue into the full design or update flow when the root file is healthy; they must not be downgraded to a pass-only check.
- Batch writes with `collect_design_profile.py --answers <answers.json> --write` must reject missing `default_conversation_language`; silent fallback to `中文` is not allowed.
- When remote servers are enabled, missing `erie-remote-ssh` must trigger an install confirmation using the fixed GitHub source, missing server configuration must trigger a configuration confirmation, and remote task routes must be built from `erie-remote-ssh choices`; no ad hoc server guesses are allowed.
- Existing `docs/` layouts are preflighted; ambiguous or conflicting layouts require user confirmation before AGENTS.md or docs governance writes.
- Strong control requires `.agents/agents-control.json` and the docs governance tree; local reference paths may stay in that profile but must not be copied into AGENTS.md.
- Strong-control memory is mandatory: `memory-gate` must fail when memory is disabled or `docs/memory` is missing, `memory-init --confirm-create` must be the only CLI creation path, and `manage_docs.py verify` / `verify_agents.py` / `work-folder-gate` must surface missing, corrupt, or unbootstrapped memory.
- Historical memory bootstrap must read only exact-cwd Codex sessions, sort them by timestamp, write compact timestamped summaries with `source_ref`, `source_timestamp`, and `sequence`, redact secrets/private paths, and record processed sessions in `docs/memory/bootstrap-state.json`.
- Root-level `experience/` is not allowed; 10 numbered experience files and history belong under `docs/experience/`.
- Legacy root or misplaced governance files such as `experience/`, `HANDOFF.md`, `DEVELOPMENT.md`, `docs/HANDOFF.md`, or `docs/DEVELOPMENT.md` must be migrated into the governed `docs/` layout instead of being left in place.
- User-visible path strings must keep real separators and be rendered in a readable normalized form; avoid collapsed Windows path text such as `F:WorkSpace...`.
- Experience files must be AI-authored summaries from evidence, not script-authored templates; every fifth handoff should create `.agents/experience-update-request.json`, and the same conversation should generate and apply an accepted `experience-payload.json` instead of leaving the request pending.
- AI experience updates must read the latest available conversation snapshots, up to 10 entries, and the request must disclose when conversation context is missing.
- Experience files must be topic-specific, non-placeholder, not highly homogeneous, and must not copy a full `HANDOFF.md` into every file.
- Every experience file must contain enough detail for a future maintainer to understand what task was done, how it was done, what failed or was risky, and how to apply the lesson later; require `Evidence Read`, `Task Context`, `How To Apply`, `Problems And Risks`, `Iterated Lessons`, and `Next Application`.
- Experience requests should expose the current five-handoff window, recent conversation window, and per-topic detail requirements so the agent can write the next experience set from the correct evidence slice.
- Topic-specific files such as `2-scripts.md`, `5-testing.md`, and `9-docs-governance.md` should mention their concrete subsystem, verification surface, and reuse boundary; long but generic prose is not acceptable.
- `git_management` must be asked as a user-facing enable/disable choice with `是（默认）` / `否` / `其他`, and `否` should persist as the explicit canonical value `no-git-management` rather than silently collapsing to `read-only`.
- `docs/development/DEVELOPMENT.md` must be the latest iterative development record, and older current records must be archived under `docs/development/history_development/YYYYMMDD-HHMMSS/DEVELOPMENT.md`.
- DEVELOPMENT records must be detailed enough to explain the complete development plan, current progress, development goal, completed scope, remaining scope, risks, results, verification, and next actions.
- `v1.0.0` 起不再支持 evolution 子系统：没有 `manage_docs.py evolve`、没有 `import-evolution`、没有 tenth-handoff atomic evolution 合同、没有 template sink/export/import、也没有任何附加 evolution 评审流程。
- `experience --payload` 必须拒绝 `evolution_target`、`evolution_summary`、`evolution_review` 等 legacy 字段，防止调用方误以为退休功能仍可用。
- Mutating docs-governance commands must clear retired `.agents/evolution-*.json` request files、`.agents/evolution-export/` 和全部 `last_evolution_*` state keys。
- Replacement installs must remove legacy `assets/templates/evolution/` content from the destination skill instead of preserving or merging it.
- Directory Contract fixes local structure, remote structure, remote deployment workspace planning, future feature-addition structure, remote `.conda/<env-name>/` placement, `runs/<run-id>/` active output layout, `backups/runs/<run-id>/` archive layout, and the archive trigger before implementation.
- Directory Contract must include an enforced primary project root for strong-control projects, and dir_manager planning must not silently bless unrelated root-level source folders.
- Directory Contract must also state that root-level work artifacts `tests/`, `smoke/` and `smoke-*`, `reports/`, and `runs/` stay only at the work-folder root and must be blocked when nested under `skills/<skill-name>/...` or `engineering/<project-name>/...`.
- Directory governance must also carry a fixed root-level file whitelist. Files outside the primary project root are blocked unless they are explicitly allowed root governance files such as `AGENTS.md` or `.gitignore`.
- `render_agents.py --write --confirm-structure-fix` means “allow the conservative fix attempt” only. It must rerun `structure-gate` afterward and keep the write blocked if any violation remains.
- Remote deployment tasks must not sync local skill-development content to servers unless the user explicitly overrides; deploy only intended runtime or deployment artifacts.
- Directory changes must pass `docs/dir_manager/DIR_MANAGER.md` review and `python skills/agents-md-generator/scripts/manage_dirs.py review <project> --input change.json`.
- Use `manage_dirs.py review --dry-run` when planning a folder mutation but not yet recording a formal review. The default review path must still write `docs/dir_manager/change_reviews/review-*.json`.
- `manage_dirs.py review` must treat remote `create`, `move`, `delete`, and `rename` uniformly: source and target paths must both stay inside the governed remote plan, destructive actions on protected remote path classes are blocked by default, verified artifacts must move to backups, and unverified artifacts must stay in active runs.
- Blocked directory reviews require a clear refusal, severe-risk explanation, and explicit user force-confirmation before any folder structure change.
- Force-confirmed blocked directory changes require `python skills/agents-md-generator/scripts/manage_dirs.py archive <project> --reason "force-confirmed directory override"` before applying the change, preserving old content under `docs/dir_manager/history_dir_manager/<timestamp>/`.
- Release Contract fixes `dist/<name>-vx.x.x` and matching zip package expectations without remote push.
- User-level `.codex/AGENTS.md` is treated as an entry-point baseline, not a repository rule dump: it must tell agents to read the current work folder root `AGENTS.md` first and must not carry repository-specific branch, release, or layout policy.
- User-level `.codex/AGENTS.md` must include reuse-first behavior and the `task_rating_gate.py` rule: prefer existing tools, libraries, templates, repository-local patterns, and mature open-source code before building from scratch; do not ask difficulty/scale on every task; ask only when the gate recommends it.
- Hell/nightmare or project-scale global-entry tasks should show strict planning, granularity alignment, and reuse-first research evidence, including candidate tools/libraries/templates/open-source projects, fit, risks, and rejection reasons when reuse is not selected.
- For this skill repository, an empty or missing global `.codex/AGENTS.md` is a real governance failure, not a cosmetic warning.
- Skill-development installable releases sanitize the `dist/` copy before packaging; source files stay unchanged and sensitive values are removed or replaced with typed placeholders.
- Release sanitization must preserve code-only regex constants such as `SECRET_RE = re.compile(...)`, must still redact actual token/password assignments in text content, and must leave the generated dist scripts compilable.
- After release packaging and validation, only skill-development flows ask yes/no whether to install; engineering projects must not prompt for skill installation.
- Before installable `dist/` release, local work is committed, development branches are merged into `master`, and local branches other than `master` and `release` are deleted unless the user explicitly changes the branch policy.
- Installable release directories must contain `RELEASE_RECEIPT.json`, repository-local installs must preserve strong branch/worktree validation, copied standalone release folders must be labeled as reduced assurance instead of silently treated as equivalent, and receipt-declared sanitization must explain every allowed content difference from the source skill.
- Installable Skill release content must obey the release-content policy: top-level release members stay within the allowlist, governed skill-local `evals/` may stay installable, and development-only or work-folder-only content such as `tests/`, `test/`, `smoke*`, `_smoke_runs/`, `reports/`, `runs/`, and cache artifacts must be rejected both before packaging and during post-package/install validation.
- Different-version release directories and matching zip files are immutable history by default. Same-version rebuilds may replace only the current target release directory and zip, and release gates must fail if any other `dist/` artifact changes.
- Binary files with sensitive content are a hard failure unless the workflow gains an explicit safe sanitizer for that file type; do not silently ship them.
- Replacement installs back up the old skill to `skill_backups/` and remove any legacy installed `assets/templates/evolution/` content so the retired subsystem is not carried forward.
- Commit and release summaries rotate through `docs/git_manager/CHANGELOG.md`; previous current entries are archived under `docs/git_manager/history_git_manager/YYYYMMDD-HHMMSS/`.
- Release gates run on `master`, with only local `master` and `release` branches present, and post-package validation confirms the release commit includes the dist artifacts and changelog update.
- Commands are labeled verified only when actually executed.
- Root `AGENTS.md` with `default_language` metadata must also contain an explicit reply-language rule stating that natural-language responses stay in that configured language unless the user explicitly switches languages.
- Root `AGENTS.md` with an enabled remote server contract must contain `## Remote Server Contract`, each registered task route with its primary server, fallback relationships, the automatic fallback rule, and a rule that unmatched remote tasks must update AGENTS.md before validation continues.
- Generated markers are balanced and hand-written content outside markers is preserved.
- No `{{PLACEHOLDER}}` tokens remain in generated output.
- Verification skips `ref/`, `.git/`, `vendor/`, build outputs, caches, and dependency folders unless `--include-skipped` is intentionally used.
- Compatibility shim creation uses the same skip boundary and never creates CLAUDE.md/GEMINI.md inside read-only reference trees by default.
- If a global `.codex/AGENTS.md` already has user-written content but no managed baseline block, sync must refuse silent overwrite and must return an explicit confirmation requirement instead.
- Fact-level validation has no errors or warnings, no `ref/**` checked files, no local development-reference leaks, and no unresolved render placeholders.
- Root AGENTS.md is thin and points to scoped files when local rules differ.
- Scoped files do not duplicate root content unless overriding it.
- README-style narrative, marketing, installation history, and copied docs are omitted.
- Reference files over 100 lines include a table of contents near the top.

## Safety Checks

- User prompt precedence is explicit.
- Closest AGENTS.md precedence is explicit.
- Always / Ask First / Never rules are present.
- Secrets, generated files, dependency changes, migrations, CI changes, destructive git operations, and public API changes have clear rules.
- Completion claims require verification output.
- Every completed development conversation writes `docs/handoff/HANDOFF.md`, archives the previous handoff, and refreshes the 10 numbered `docs/experience/` files every five handoffs.
- Handoff naming is strict after docs governance exists: the latest handoff must stay `docs/handoff/HANDOFF.md`, history archives must stay `HANDOFF-YYYYMMDD-HHMMSS.md` or `HANDOFF-YYYYMMDD-HHMMSS-N.md`, and `scaffold` must not hide a rename by creating a fresh placeholder.
- New task starts check `.agents/active-session.json` with `manage_docs.py resume-check`; interrupted sessions require `resume-repair` before new work.

## Update Checks

- Existing hand-written guidance remains unless stale, unsafe, or contradicted by repository facts.
- Stale commands and missing paths are corrected or removed.
- New sections are added surgically; unrelated prose is not rewritten.
- Final diff is reviewed before committing.
