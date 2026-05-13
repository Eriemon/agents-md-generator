# AGENTS.md Review Checklist

Run `scripts/verify_agents.py` first, then use this checklist for judgment that scripts cannot fully automate.

## Table of Contents

- [Script Gates](#script-gates)
- [Content Checks](#content-checks)
- [Safety Checks](#safety-checks)
- [Update Checks](#update-checks)

## Script Gates

| Gate | Required evidence |
|------|-------------------|
| Structure | `quick_validate.py skills/agents-md-generator` passes for this skill |
| Facts | `python scripts/inspect_project.py <project>` output reviewed |
| Design profile | `python scripts/collect_design_profile.py <project> --answers answers.json --write` completed when strong control is required |
| Commands | `python scripts/extract_commands.py <project>` output reviewed |
| Context | `python scripts/extract_context.py <project>` output reviewed |
| Scopes | `python scripts/detect_scopes.py <project>` output reviewed |
| Content | `python scripts/verify_agents.py <project>` has no errors and does not scan skipped development/reference trees by default |
| Docs preflight | `python scripts/manage_docs.py preflight <project>` is safe, or user confirmation is recorded for an ambiguous/conflicting existing `docs/` layout |
| Session bootstrap | When the workspace already has landed content but no root `AGENTS.md`, `python scripts/manage_docs.py bootstrap-experience <project>` has been reviewed and exact-cwd session matching is correct |
| Docs governance | `python scripts/manage_docs.py verify <project>` has no errors for strong-control projects |
| Branch governance | `python scripts/manage_docs.py branch-gate <project>` passes before strong-control generation on external work folders |
| Structure governance | `python scripts/manage_dirs.py structure-gate <project>` passes or explicit confirmation for normalization is recorded before strong-control generation continues |
| Directory governance | `python scripts/manage_dirs.py verify <project>` passes, and folder changes have a passing `manage_dirs.py review` result |
| Book rules | `python scripts/select_engineering_rules.py --list` or `--task <type>` used when a book-derived engineering rule set is selected |
| Skill design | `references/skill-design-coverage.md` reviewed when the target is Skill development |
| Freshness | `python scripts/check_freshness.py <project>` reviewed for existing AGENTS.md |
| Compatibility | `python scripts/create_agent_shims.py <project>` used only when requested |
| Install confirmation | `python scripts/install_skill.py <skill-dir> --target skip` or explicit install target recorded after release validation; replacement installs must show `backup_path` and no unreviewed template loss |
| Skill self-audit | `python scripts/audit_skill.py skills/agents-md-generator` has no errors after skill edits |
| Fact-level validation | `python scripts/evaluate_skill.py skills/agents-md-generator <project>` returns `"ok": true` after skill edits |

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
- Root `AGENTS.md` stays within `12KB`; scoped `AGENTS.md` files are not rejected for exceeding the old line-count rule.
- Skill design interview questions expose selectable options, repeat `review_summary` confirmation after each answer group, and set `alignment_confirmed=true` only after the user confirms the summary.
- Skill development profiles include detailed development requirements, development purpose, expected result, validation method, and validation granularity before strong control is written.
- User-developed Skills live under `skills/<skill-name>/SKILL.md`; `SKILL.md` frontmatter `name` exactly matches the folder name and uses lowercase letters, digits, and hyphens.
- If `has_existing_work=yes` for a Skill project, the expected `skills/<skill-name>/SKILL.md` must already exist on disk; answer text alone is not enough.
- If `has_existing_work=yes` for an engineering project, the expected `engineering/<project-name>/` root must already exist on disk.
- When a workspace already has landed content but no root `AGENTS.md`, bootstrap history must read only exact-cwd Codex sessions from `.codex/sessions`; do not mix in neighboring or similarly named repositories.
- Session bootstrap should write one `history_experience` snapshot per matched session and one latest current `docs/experience/*.md` set for the current workspace.
- External work folders with enabled git management must pass branch governance before strong-control generation: current branch, local branch set, and worktree state must match the configured branch model or be explicitly escalated.
- If the current file structure violates the governed primary root or allowed top-level roots, the workflow must ask whether to normalize it before modifying files, and the recommended default should be yes.
- Missing root `AGENTS.md` is a mandatory abnormal state for agents-md-generator root AGENTS/docs/workspace handling; the skill must report the problem and ask whether to enter AGENTS design or restructuring.
- Missing `agents_version` or `generator_version`, or either value mismatching the installed `agents-md-generator` version, is also a mandatory abnormal state for root AGENTS/docs/workspace handling; do not treat it as a normal warning.
- User requests containing `计划`, `规划`, or `准备` should first run the current-workspace/current-repository/current-work-folder root `AGENTS.md` check.
- If that root check passes, the trigger path should only report that the check passed and must not silently continue into AGENTS design work.
- If that root check fails, the trigger path should report the exact abnormal reason and ask whether to enter AGENTS.md design or restructuring.
- Existing `docs/` layouts are preflighted; ambiguous or conflicting layouts require user confirmation before AGENTS.md or docs governance writes.
- Strong control requires `.agents/agents-control.json` and the docs governance tree; local reference paths may stay in that profile but must not be copied into AGENTS.md.
- Root-level `experience/` is not allowed; 10 numbered experience files and history belong under `docs/experience/`.
- Legacy root or misplaced governance files such as `experience/`, `HANDOFF.md`, `DEVELOPMENT.md`, `docs/HANDOFF.md`, or `docs/DEVELOPMENT.md` must be migrated into the governed `docs/` layout instead of being left in place.
- User-visible path strings must keep real separators and be rendered in a readable normalized form; avoid collapsed Windows path text such as `F:WorkSpace...`.
- Experience files must be AI-authored summaries from evidence, not script-authored templates; every fifth handoff should create `.agents/experience-update-request.json` and require an accepted `experience-payload.json`.
- AI experience updates must read the latest available conversation snapshots, up to 10 entries, and the request must disclose when conversation context is missing.
- Experience files must be topic-specific, non-placeholder, not highly homogeneous, and must not copy a full `HANDOFF.md` into every file.
- Every experience file must contain enough detail for a future maintainer to understand what task was done, how it was done, what failed or was risky, and how to apply the lesson later; require `Evidence Read`, `Task Context`, `How To Apply`, `Problems And Risks`, `Iterated Lessons`, and `Next Application`.
- `git_management` must be asked as a user-facing enable/disable choice with `是（默认）` / `否` / `其他`, and `否` should persist as the explicit canonical value `no-git-management` rather than silently collapsing to `read-only`.
- `docs/development/DEVELOPMENT.md` must be the latest iterative development record, and older current records must be archived under `docs/development/history_development/YYYYMMDD-HHMMSS/DEVELOPMENT.md`.
- DEVELOPMENT records must be detailed enough to explain the complete development plan, current progress, development goal, completed scope, remaining scope, risks, results, verification, and next actions.
- Every tenth handoff should evolve accepted experience into indexed templates under `assets/templates/evolution/`, but only from AI-authored `evolution_summary` synthesis.
- Evolution templates must write to exactly one family that matches the project kind: skill projects use `skill-template/<category>/<type>/`, engineering projects use `engineering-template/<category>/<type>/`.
- AI-provided `evolution_target` values must have a matching family, safe category/type path segments, and a rationale; inferred categories should use repository facts such as FPGA/Vivado, algorithm/sort, agent-governance, docs-governance, web/frontend, backend/api, data/database, or general.
- Obsolete evolution outputs listed by a prior `evolution-index.json` must be archived before cleanup; do not silently delete or keep cross-family copied templates.
- Directory Contract fixes local structure, remote structure, remote deployment workspace planning, and future feature-addition structure before implementation.
- Directory Contract must include an enforced primary project root for strong-control projects, and dir_manager planning must not silently bless unrelated root-level source folders.
- Remote deployment tasks must not sync local skill-development content to servers unless the user explicitly overrides; deploy only intended runtime or deployment artifacts.
- Directory changes must pass `docs/dir_manager/DIR_MANAGER.md` review and `python scripts/manage_dirs.py review <project> --input change.json`.
- Blocked directory reviews require a clear refusal, severe-risk explanation, and explicit user force-confirmation before any folder structure change.
- Force-confirmed blocked directory changes require `python scripts/manage_dirs.py archive <project> --reason "force-confirmed directory override"` before applying the change, preserving old content under `docs/dir_manager/history_dir_manager/<timestamp>/`.
- Release Contract fixes `dist/<name>-vx.x.x` and matching zip package expectations without remote push.
- After release packaging and validation, the user is asked yes/no whether to install; no response or no means skip, and custom/Codex installs require an explicit target.
- Before installable `dist/` release, local work is committed, development branches are merged into `master`, and local branches other than `master` and `release` are deleted unless the user explicitly changes the branch policy.
- Replacement installs back up the old skill to `skill_backups/` and preserve installed evolution templates, reporting conflicts instead of silently overwriting them.
- Commit and release summaries rotate through `docs/git_manager/CHANGELOG.md`; previous current entries are archived under `docs/git_manager/history_git_manager/YYYYMMDD-HHMMSS/`.
- Release gates run on `master`, with only local `master` and `release` branches present, and post-package validation confirms the release commit includes the dist artifacts and changelog update.
- Commands are labeled verified only when actually executed.
- Generated markers are balanced and hand-written content outside markers is preserved.
- No `{{PLACEHOLDER}}` tokens remain in generated output.
- Verification skips `ref/`, `.git/`, `vendor/`, build outputs, caches, and dependency folders unless `--include-skipped` is intentionally used.
- Compatibility shim creation uses the same skip boundary and never creates CLAUDE.md/GEMINI.md inside read-only reference trees by default.
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
- New task starts check `.agents/active-session.json` with `manage_docs.py resume-check`; interrupted sessions require `resume-repair` before new work.

## Update Checks

- Existing hand-written guidance remains unless stale, unsafe, or contradicted by repository facts.
- Stale commands and missing paths are corrected or removed.
- New sections are added surgically; unrelated prose is not rewritten.
- Final diff is reviewed before committing.
