---
name: agents-md-generator
description: Use when creating, updating, verifying, or reviewing AGENTS.md files and AI coding-agent rule files; when a project or current work folder root lacks AGENTS.md; when root AGENTS.md version metadata is missing or mismatched; when the user explicitly mentions AGENTS.md, agent rules, or scoped AGENTS.md; or when the user is talking about the current workspace/current repository/current work folder and says 计划, 规划, or 准备, which must first trigger a root AGENTS.md check.
---

# AGENTS.md Generator

Create operational context files for AI coding agents. Use facts from the repository first, ask only for missing human policy, and verify before claiming the draft is ready.

当用户明确提到 `AGENTS.md`、`agent rules`、`scoped AGENTS.md` 时，直接进入本技能。

当用户在当前工作区、当前工程、当前仓库、或当前工作文件夹语境里说“计划”、“规划”或“准备”时，也要进入本技能，但第一步不是直接设计，而是先检查当前工作文件夹根 `AGENTS.md` 状态。

根 `AGENTS.md` 正常时，只报告“检查通过”，不要自动继续设计流程。根 `AGENTS.md` 缺失、缺少版本元数据、或版本与当前已安装 `agents-md-generator` 不一致时，先报告异常原因，再询问用户是否进入 `AGENTS.md` 设计/重构流程。

## Pipeline

1. **Detect**
   - Run `python scripts/inspect_project.py <project>` to gather language, framework, package manager, CI, AI configs, files, and directories.
   - If `root_agents_md_exists` is false, or the root `AGENTS.md` is missing `agents_version` or `generator_version`, or either version does not match the current local installed `agents-md-generator` version, treat the workspace as trigger-required/rebuild-required.
   - When the user says `计划`, `规划`, or `准备` in the current workspace/current repository/current work folder context, do this root-AGENTS check first. These are trigger entries for inspection routing, not a bypass around the AGENTS.md check.
   - If the root check passes, report that the current work folder root `AGENTS.md` check passed and stop unless the user explicitly asks to continue with AGENTS design/update work.
   - If the root check fails, report the exact missing/mismatched reason and ask whether to enter the AGENTS/docs/workspace design or restructuring flow. Do not silently jump into design work.
   - Run `python scripts/detect_scopes.py <project>` to find directories that may need scoped AGENTS.md files.

2. **Design Interview**
   - Run `python scripts/collect_design_profile.py <project>` and ask question 1 first; do not rely on directory inference as the final answer.
   - Ask the default conversation language question for every project: `中文` by default, `English`, or user-provided custom language.
   - After the user confirms the type, rerun with `--kind skill` or `--kind engineering` to get the mandatory branch questions.
   - Ask every required question in order and present each returned `options` list to the user. Prefer `request_user_input` when available so the user can choose an option or enter a custom answer.
   - Skill development follows questions 2-10, then 22-31, then 20-21; engineering development follows questions 11-19, then 20-21.
   - After each answer group, show the returned `review_summary` and `confirmed_so_far`, then ask the `confirmation_question`. If the user answers no, collect corrections and repeat the summary until the user confirms yes.
   - Save answers to JSON only after the full design is aligned. Set `alignment_confirmed=true` only after user yes/no confirmation succeeds, then run `python scripts/collect_design_profile.py <project> --answers <answers.json> --write` before claiming strong-control AGENTS.md generation.
   - For user-developed Skills, require `skills/<skill-name>/SKILL.md`; the frontmatter `name` must exactly match the folder name and use only lowercase letters, digits, and hyphens. Reject root-level self-hosted skill folders such as `<project>/<skill-name>/SKILL.md`.
   - For engineering projects, require `engineering/<project-name>/` as the project directory contract; do not accept root-level engineering application folders.

3. **Extract**
   - Run `python scripts/extract_commands.py <project>` to collect command candidates from Makefile, package.json, pyproject.toml, composer.json, go.mod, and visible CI workflow `run:` lines.
   - Run `python scripts/extract_context.py <project>` to collect docs, ADRs, utilities, quality configs, agent configs, golden sample candidates, and CI rules.
   - Read `references/agents-md-guidance.md` for section choices and what belongs in AGENTS.md.
   - Read `references/skill-design-coverage.md` when generating or reviewing AGENTS.md for Skill development.
   - Read `references/capability-coverage.md` when comparing this skill to other AGENTS.md generator implementations.
   - Read `references/book-rules-coverage.md` before using book-derived engineering rule sets; choose one primary rule set and keep full material out of AGENTS.md.
   - Run `python scripts/select_engineering_rules.py --list` or `--task <type>` when the user wants book-derived engineering guidance.

4. **Ask Missing Intent**
   - Ask only for preferences that cannot be discovered from files: commit policy, risky operations, approval boundaries, expensive checks, and domain terminology.
   - Use `references/question-bank.md` for focused questions.

5. **Generate**
   - Run `python scripts/render_agents.py <project> --profile <project>/.agents/agents-control.json` first; default is dry-run.
   - Use `--write` only after reviewing the draft and confirming the target path is inside the intended repository.
   - Before `--write` with strong-control docs governance, run `python scripts/manage_docs.py preflight <project>`; if it requires user confirmation, ask before using the existing `docs/` layout.
   - Strong-control generation creates or requires `.agents/agents-control.json` and the `docs/` governance tree. Experience records must live under `docs/experience/` as 10 numbered project-specific files; do not create a root-level `experience/` folder.
   - `render_agents.py --write` writes the root `AGENTS.md` with machine-readable version and default-language metadata. The root file must stay within `12KB`; other `AGENTS.md` files are not subject to this hard size limit.
   - After writing AGENTS.md files, run docs scaffolding for handoff, experience, development, install configuration, and git manager records.
   - Templates in `assets/templates/` define the intended root/scoped shape.
   - Use `--template-dir <dir>` only for controlled tests or intentional template overrides.

6. **Docs Governance**
   - Before executing a new task after reading a prior handoff, run `python scripts/manage_docs.py resume-check <project>`; if it reports an interrupted active session, run `python scripts/manage_docs.py resume-repair <project> --input recovery.json` before handling the new request.
   - At task start, run `python scripts/manage_docs.py start-session <project> --input session.json` after reading `docs/handoff/HANDOFF.md`.
   - Run `python scripts/manage_docs.py scaffold <project>` when docs governance must be prepared without rewriting AGENTS.md.
   - At task completion, run `python scripts/manage_docs.py handoff <project> --input handoff.json`; the current `docs/handoff/HANDOFF.md` is archived before the new latest handoff is written.
   - Every five handoffs, `manage_docs.py` creates `.agents/experience-update-request.json`; AI must read that request plus up to 10 recent conversation snapshots and write an `experience-payload.json`.
   - Apply AI-authored experience with `python scripts/manage_docs.py experience <project> --payload experience-payload.json`; scripts validate, archive, and write, but must not fabricate lesson content.
   - Every ten handoffs, accepted experience evolves indexed templates under the single matching assets/templates/evolution family: skill projects use `skill-template/<category>/<type>/`, engineering projects use `engineering-template/<category>/<type>/`; do not copy the same experience into both families.
   - At installable release or stage completion, run `python scripts/manage_docs.py development <project> --stage <name> --input stage.json`.
   - Keep install setup for Codex, Claude, and OpenClaw under `docs/install_configuration/`; keep branch, release, dist, package naming, protected branch cleanup, `CHANGELOG.md`, changelog history, and current version rules under `docs/git_manager/`.
   - Rotate commit and release summaries with `python scripts/manage_docs.py git-changelog <project> --input changelog.json`; archive the previous current file under `docs/git_manager/history_git_manager/<timestamp>/CHANGELOG.md` before writing the new one.
   - Verify branch, worktree, release artifact, and parity gates with `python scripts/manage_docs.py release-gate <project> --version vX.Y.Z --skill-dir skills/<skill-name> --phase pre|post`.
   - Keep local and remote deployment folder governance under `docs/dir_manager/`; before creating, moving, deleting, or renaming governed folders, run `python scripts/manage_dirs.py review <project> --input change.json`.
   - For remote server deployment tasks, do not sync local skill-development content to servers; deploy only explicit runtime/deployment artifacts unless the user explicitly overrides.
   - If directory review is blocked, refuse default execution, explain the severe risks, and ask for explicit user force-confirmation before changing folder structure.
   - After explicit user force-confirmation and before applying the blocked folder change, run `python scripts/manage_dirs.py archive <project> --reason "force-confirmed directory override"` so old dir manager content is preserved under `docs/dir_manager/history_dir_manager/<timestamp>/`.

7. **Verify**
   - Run `python scripts/verify_agents.py <project>` after generation or edits.
   - Run `python scripts/manage_docs.py verify <project>` when debugging docs governance failures directly.
   - Use `python scripts/audit_skill.py <skill-dir>` when changing this skill itself.
   - Use `python scripts/evaluate_skill.py <skill-dir> <project>` for the full fact-level validation chain after skill edits.
   - Run `python scripts/check_freshness.py <project>` when updating an existing AGENTS.md.
   - Run `python scripts/create_agent_shims.py <project>` only when the user wants CLAUDE.md/GEMINI.md compatibility.
   - After release packaging and successful validation, if the user did not explicitly mention whether to install, you must ask the install question. If yes, use `python scripts/install_skill.py <skill-dir> --target codex --write --replace` or `--target custom --custom-root <dir> --write --replace` when replacing an existing skill; the installer must back up the old skill and preserve evolution templates before replacing. If no or no explicit response, skip installation.

8. **Final Evidence**
   - Report generated files, unresolved warnings, and verification command output.
   - Never label commands verified unless they were actually run.
   - Ensure each completed development conversation writes `docs/handoff/HANDOFF.md`; include conversation summary/excerpt/log references so future AI experience updates can read the latest 10 conversations.

## Rules

- Prefer generated facts for commands, file maps, scopes, and config discovery.
- Preserve hand-written content outside `AGENTS-GENERATED` blocks.
- Do not fabricate commands, files, branches, owners, frameworks, CI rules, security policies, or coverage targets.
- Keep root AGENTS.md thin; put directory-specific details in scoped files.
- Point to README/docs/ADRs instead of copying long explanations.
- Read `references/review-checklist.md` before finalizing.

## Resources

| Resource | Use |
|----------|-----|
| `references/script-guide.md` | Script commands, options, and expected outputs |
| `references/review-checklist.md` | Verification and review gates |
| `references/skill-design-coverage.md` | Skill design patterns, progressive disclosure, and Skill Design Contract checks |
| `references/capability-coverage.md` | Coverage map for borrowed generator capabilities |
| `references/book-rules-coverage.md` | Policy for mini/nano/full engineering rule integration |
| `references/evaluation-scenarios.md` | Regression scenarios to forward-test the skill |
| `assets/templates/root-agents.md` | Root AGENTS.md structure |
| `assets/templates/scoped-agents.md` | Directory-scoped AGENTS.md structure |
| `scripts/manage_docs.py` | Docs governance scaffold, handoff rotation, AI experience requests/payload application, evolution templates, development records, and verification |
| `scripts/manage_dirs.py` | Strict local and remote folder structure scan, planning, review, blocking, and verification |
