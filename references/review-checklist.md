# AGENTS.md Review Checklist

Run `scripts/verify_agents.py` first, then use this checklist for judgment that scripts cannot fully automate.

## Script Gates

| Gate | Required evidence |
|------|-------------------|
| Structure | `quick_validate.py agents-md-generator` passes for this skill |
| Facts | `python scripts/inspect_project.py <project>` output reviewed |
| Design profile | `python scripts/collect_design_profile.py <project> --answers answers.json --write` completed when strong control is required |
| Commands | `python scripts/extract_commands.py <project>` output reviewed |
| Context | `python scripts/extract_context.py <project>` output reviewed |
| Scopes | `python scripts/detect_scopes.py <project>` output reviewed |
| Content | `python scripts/verify_agents.py <project>` has no errors and does not scan skipped development/reference trees by default |
| Book rules | `python scripts/select_engineering_rules.py --list` or `--task <type>` used when a book-derived engineering rule set is selected |
| Skill design | `references/skill-design-coverage.md` reviewed when the target is Skill development |
| Freshness | `python scripts/check_freshness.py <project>` reviewed for existing AGENTS.md |
| Compatibility | `python scripts/create_agent_shims.py <project>` used only when requested |
| Skill self-audit | `python scripts/audit_skill.py agents-md-generator` has no errors after skill edits |
| Fact-level validation | `python scripts/evaluate_skill.py agents-md-generator <project>` returns `"ok": true` after skill edits |

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
- Strong-control AGENTS.md includes Control Profile, Directory Contract, Release Contract, Engineering Rule Contract, Conversation Completion Contract, and Experience Log Contract.
- Strong-control Skill AGENTS.md includes Skill Design Contract with design patterns, resource boundaries, progressive disclosure, validation gates, and forward-testing policy.
- Strong control requires `.agents/agents-control.json`; local reference paths may stay in that profile but must not be copied into AGENTS.md.
- Directory Contract fixes local structure, remote structure, and future feature-addition structure before implementation.
- Release Contract fixes `dist/<name>-vx.x.x` and matching zip package expectations without remote push.
- Commands are labeled verified only when actually executed.
- Generated markers are balanced and hand-written content outside markers is preserved.
- No `{{PLACEHOLDER}}` tokens remain in generated output.
- Verification skips `ref/`, `.git/`, `vendor/`, build outputs, caches, and dependency folders unless `--include-skipped` is intentionally used.
- Compatibility shim creation uses the same skip boundary and never creates CLAUDE.md/GEMINI.md inside read-only reference trees by default.
- Fact-level validation has no errors or warnings, no `ref/**` checked files, no local development-reference leaks, and no unresolved render placeholders.
- Root AGENTS.md is thin and points to scoped files when local rules differ.
- Scoped files do not duplicate root content unless overriding it.
- README-style narrative, marketing, installation history, and copied docs are omitted.

## Safety Checks

- User prompt precedence is explicit.
- Closest AGENTS.md precedence is explicit.
- Always / Ask First / Never rules are present.
- Secrets, generated files, dependency changes, migrations, CI changes, destructive git operations, and public API changes have clear rules.
- Completion claims require verification output.
- Every completed development conversation adds or updates an `experience/YYYY-MM-DD-<topic>.md` lesson file.

## Update Checks

- Existing hand-written guidance remains unless stale, unsafe, or contradicted by repository facts.
- Stale commands and missing paths are corrected or removed.
- New sections are added surgically; unrelated prose is not rewritten.
- Final diff is reviewed before committing.
