# Capability Coverage

Use external AGENTS.md generator projects as capability references, not as code to copy wholesale.

## Integration Policy

| Reference capability | This skill coverage |
|----------------------|---------------------|
| Project detection | `inspect_project.py` detects languages, framework, package manager, CI, AI configs, files, and directories |
| Scope detection | `detect_scopes.py` proposes scoped AGENTS.md targets |
| Command extraction | `extract_commands.py` reads Makefile, package.json, pyproject.toml, composer.json, go.mod, and workflow run lines |
| Documentation extraction | `extract_context.py` collects README, docs, ADRs, architecture, ownership, utilities, and golden samples |
| Platform and IDE extraction | `extract_context.py` collects platform files, dev-environment files, editor settings, and quality configs |
| Hook detection | `extract_context.py` collects Lefthook, Husky, CaptainHook, pre-commit, and repo hook files |
| GitHub settings | `extract_context.py` collects CODEOWNERS, Copilot instructions, dependency configs, and rulesets |
| Directory coverage | `extract_context.py` reports major directories that may need scoped AGENTS.md files |
| Generation | `render_agents.py` renders root/scoped AGENTS.md from templates and extracted facts, adds root version/language metadata, and keeps the root `AGENTS.md` within 15KB |
| Docs governance | `manage_docs.py` scaffolds `docs/`, rotates handoff files, writes 10 numbered experience summaries, records development stages, verifies governance files, and uses `resume-check` for interrupted session recovery |
| Directory governance | `manage_dirs.py` scans current structure, records planned local and remote deployment structure, reviews directory change requests, blocks unsafe folder changes, archives old dir manager content for user force-confirmed overrides, and writes review records |
| Structure/content validation | `verify_agents.py`, `audit_skill.py`, and `evaluate_skill.py` gate markers, placeholders, paths, commands, skipped directories, and skill structure |
| Install confirmation | `install_skill.py` is used only for skill-development release flows, asks yes/no install confirmation after release validation, defaults to skip unless Codex or custom target is explicit, rejects source directories, requires `RELEASE_RECEIPT.json`, and preserves backup/template state on replacement |
| Compatibility shims | `create_agent_shims.py` creates CLAUDE.md and GEMINI.md only when requested, preserving non-managed files |
| Hooks guidance | Rendered AGENTS.md includes hook policy and forbids bypassing hooks |

## Deliberate Non-Copy Decisions

- Do not copy Bash scripts when an equivalent Python standard-library implementation exists.
- Do not include large example projects in the skill package.
- Do not hard-code local reference paths in skill files or generated AGENTS.md.
- Do not install hooks automatically; detect and document them, then let the user choose setup.
- Do not install a release package automatically; no answer or no means skip installation, and engineering projects must not be routed into skill-install prompts.
- Do not release an installable `dist/` package from unmerged temporary branches; commit, merge into `master`, and clean local branches except `master` and `release`.
- Do not treat copied standalone release folders as equivalent to repository-local `dist/` installs; they may install only with explicit reduced-assurance labeling after receipt validation.
- Do not overwrite user-accumulated evolution templates during skill installation; preserve both versions and report conflicts.
- Do not duplicate every agent-specific proprietary rule format; keep AGENTS.md canonical and provide shims only for requested compatibility.
- Do not overwrite hand-written docs governance records; archive handoff and numbered experience history before writing new current files.
- Do not apply directory moves directly from the review helper; `manage_dirs.py` only reviews and blocks so agents cannot bypass user intent.
- If a user force-confirms a blocked directory change, archive old dir manager content to `docs/dir_manager/history_dir_manager/<timestamp>/` before applying the change.
