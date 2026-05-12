# AGENTS.md Review Checklist

Run `scripts/verify_agents.py` first, then use this checklist for judgment that scripts cannot fully automate.

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
| Docs governance | `python scripts/manage_docs.py verify <project>` has no errors for strong-control projects |
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
- Missing root `AGENTS.md` triggers an ask-first decision before writing project instructions.
- Existing `docs/` layouts are preflighted; ambiguous or conflicting layouts require user confirmation before AGENTS.md or docs governance writes.
- Strong control requires `.agents/agents-control.json` and the docs governance tree; local reference paths may stay in that profile but must not be copied into AGENTS.md.
- Root-level `experience/` is not allowed; 10 numbered experience files and history belong under `docs/experience/`.
- Experience files must be AI-authored summaries from evidence, not script-authored templates; every fifth handoff should create `.agents/experience-update-request.json` and require an accepted `experience-payload.json`.
- AI experience updates must read the latest available conversation snapshots, up to 10 entries, and the request must disclose when conversation context is missing.
- Experience files must be topic-specific, non-placeholder, not highly homogeneous, and must not copy a full `HANDOFF.md` into every file.
- Every tenth handoff should evolve accepted experience into indexed templates under `assets/templates/evolution/`.
- Directory Contract fixes local structure, remote structure, remote deployment workspace planning, and future feature-addition structure before implementation.
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
