---
name: agents-md-generator
description: Use when creating, updating, verifying, or reviewing AGENTS.md files and AI coding-agent rule files; when the user mentions AGENTS.md, agent rules, scoped AGENTS.md, AI coding context, repository onboarding for agents, stale agent docs, command verification, CLAUDE.md/GEMINI.md compatibility shims, or project instructions for Codex, Claude Code, Gemini CLI, GitHub Copilot, Cursor, and other coding agents.
---

# AGENTS.md Generator

Create operational context files for AI coding agents. Use facts from the repository first, ask only for missing human policy, and verify before claiming the draft is ready.

## Pipeline

1. **Detect**
   - Run `python scripts/inspect_project.py <project>` to gather language, framework, package manager, CI, AI configs, files, and directories.
   - Run `python scripts/detect_scopes.py <project>` to find directories that may need scoped AGENTS.md files.

2. **Design Interview**
   - Run `python scripts/collect_design_profile.py <project>` and ask question 1 first; do not rely on directory inference as the final answer.
   - After the user confirms the type, rerun with `--kind skill` or `--kind engineering` to get the mandatory branch questions.
   - Ask every required question in order. Skill development follows questions 2-10, then 22-27, then 20-21; engineering development follows questions 11-19, then 20-21.
   - Save answers to JSON and run `python scripts/collect_design_profile.py <project> --answers <answers.json> --write` before claiming strong-control AGENTS.md generation.

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
   - Strong-control generation creates or requires `.agents/agents-control.json`, compatibility `experience/`, and the `docs/` governance tree.
   - `render_agents.py --write` writes AGENTS.md and scoped AGENTS.md files, then runs docs scaffolding for handoff, experience, development, install configuration, and git manager records.
   - Templates in `assets/templates/` define the intended root/scoped shape.
   - Use `--template-dir <dir>` only for controlled tests or intentional template overrides.

6. **Docs Governance**
   - Run `python scripts/manage_docs.py scaffold <project>` when docs governance must be prepared without rewriting AGENTS.md.
   - At task completion, run `python scripts/manage_docs.py handoff <project> --input handoff.json`; the current `docs/handoff/HANDOFF.md` is archived before the new latest handoff is written.
   - Every five handoffs, the script summarizes lessons under `docs/experience/` and archives old lesson files under `docs/experience/history_experience/<timestamp>/`.
   - At installable release or stage completion, run `python scripts/manage_docs.py development <project> --stage <name> --input stage.json`.
   - Keep install setup for Codex, Claude, and OpenClaw under `docs/install_configuration/`; keep branch, release, dist, package naming, and current version rules under `docs/git_manager/`.

7. **Verify**
   - Run `python scripts/verify_agents.py <project>` after generation or edits.
   - Run `python scripts/manage_docs.py verify <project>` when debugging docs governance failures directly.
   - Use `python scripts/audit_skill.py <skill-dir>` when changing this skill itself.
   - Use `python scripts/evaluate_skill.py <skill-dir> <project>` for the full fact-level validation chain after skill edits.
   - Run `python scripts/check_freshness.py <project>` when updating an existing AGENTS.md.
   - Run `python scripts/create_agent_shims.py <project>` only when the user wants CLAUDE.md/GEMINI.md compatibility.

8. **Final Evidence**
   - Report generated files, unresolved warnings, and verification command output.
   - Never label commands verified unless they were actually run.
   - Ensure each completed development conversation writes `docs/handoff/HANDOFF.md`; every fifth handoff must also refresh `docs/experience/` lessons.

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
| `scripts/manage_docs.py` | Docs governance scaffold, handoff rotation, experience summaries, development records, and verification |
