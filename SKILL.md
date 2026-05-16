---
name: agents-md-generator
description: Use when creating, updating, verifying, or reviewing AGENTS.md files and AI coding-agent rule files; when a project or current work folder root lacks AGENTS.md; when root AGENTS.md version metadata is missing or mismatched; when the user explicitly mentions AGENTS.md, agent rules, or scoped AGENTS.md; or when the user is talking about the current workspace/current repository/current work folder and says 计划, 规划, or 准备, which must first trigger a root AGENTS.md check.
---

# AGENTS.md Generator

Create operational context files for AI coding agents. Use facts from the repository first, ask only for missing human policy, and verify before claiming the draft is ready.

当用户明确提到 `AGENTS.md`、`agent rules`、`scoped AGENTS.md` 时，直接进入本技能。

当用户在当前工作区、当前工程、当前仓库、或当前工作文件夹语境里说“计划”、“规划”或“准备”时，也要进入本技能，但第一步不是直接设计，而是先检查当前工作文件夹根 `AGENTS.md` 状态。

当前工作区类请求除了检查当前工作文件夹根 `AGENTS.md`，还要检查全局 `~/.codex/AGENTS.md` 或 `$CODEX_HOME/AGENTS.md` 是否存在且包含受管的全局基线区块。这个全局文件只负责入口规则：要求代理先读取当前工作文件夹根 `AGENTS.md`，而不是替代仓库根文件中的本地约束。

根 `AGENTS.md` 正常时，只报告“检查通过”，不要自动继续设计流程。根 `AGENTS.md` 缺失、缺少版本元数据、或版本与当前已安装 `agents-md-generator` 不一致时，先报告异常原因；如果当前工作文件夹已经有落地内容，则进入最小 takeover 流程而不是完整设计访谈。

如果全局 `.codex/AGENTS.md` 缺失、为空、或缺少受管基线区块，不要静默忽略；要明确报告“全局入口规则未落盘”，并给出 `python skills/agents-md-generator/scripts/manage_docs.py sync-global-codex-agents . --write` 作为修复命令。

如果是“已有内容但无根 `AGENTS.md`”的工作文件夹，除了结构检查之外，还要读取精确匹配当前工作目录的 Codex sessions：只接受 `.codex/sessions` 中 `session_meta.payload.cwd` 规范化后与当前工作目录完全一致的会话。先用这些会话和现有落地文件补建 `docs/experience/history_experience/` 历史经验，再生成最新的 `docs/experience/*.md`。

## Pipeline

1. **Detect**
   - Run `python skills/agents-md-generator/scripts/inspect_project.py <project>` to gather language, framework, package manager, CI, AI configs, files, and directories.
   - If `root_agents_md_exists` is false, or the root `AGENTS.md` is missing `agents_version` or `generator_version`, or either version does not match the current local installed `agents-md-generator` version, treat the workspace as trigger-required/rebuild-required.
   - Inspect the global `.codex/AGENTS.md` baseline status too. If it is missing, empty, unmanaged, or outdated, report the exact reason and recommend `python skills/agents-md-generator/scripts/manage_docs.py sync-global-codex-agents . --write`.
   - When the user says `计划`, `规划`, or `准备` in the current workspace/current repository/current work folder context, do this root-AGENTS check first. These are trigger entries for inspection routing, not a bypass around the AGENTS.md check.
   - If the root check passes, report that the current work folder root `AGENTS.md` check passed and stop unless the user explicitly asks to continue with AGENTS design/update work.
   - If the root check fails for an old workspace with landed content, switch to takeover handling instead of the full design interview: only confirm the project type, project/skill name, default conversation language, and remote structure when the facts cannot prove it is `not configured`. Treat remote structure governance as separate from remote-server enablement and task-route mapping: even in takeover mode, still explicitly ask whether remote servers are needed before any remote task route can be written into AGENTS.md.
   - If the workspace already has landed content but no root `AGENTS.md`, mark session bootstrap as required, inspect exact-cwd Codex session history, and prepare forced local workspace takeover before normal AGENTS generation continues.
   - Run `python skills/agents-md-generator/scripts/detect_scopes.py <project>` to find directories that may need scoped AGENTS.md files.

2. **Design Interview**
   - Start grouped interviews with `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --start`; if the workspace qualifies for takeover, `--start` should enter takeover mode automatically. If `.agents/design-interview-state.json` already exists and is unfinished, resume it instead of silently starting over.
   - Use `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --start-takeover` or `--resume-takeover` when the root `AGENTS.md` is missing or outdated for an old workspace and you need the forced takeover path explicitly.
   - Use `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --resume` whenever an earlier design interview is still incomplete.
   - Submit one group at a time with `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --answer-file partial.json`.
   - Ask every returned question in the current group and present each returned `options` list to the user. Prefer `request_user_input` when available so the user can choose an option or enter a custom answer.
   - Question `32` for `default_conversation_language` is mandatory for every AGENTS generation or takeover-restructure flow. Do not skip it, infer it, or silently fall back to `中文`.
   - Question `45` for `use_remote_server` is mandatory for every AGENTS generation or takeover-restructure flow. If the user enables remote servers, do not continue until the remote dependency, configuration, task-route mapping, and validation gates are complete.
   - Skill development groups are `[1,32,45]`, `[2,3,4]`, `[5,6,7]`, `[8,9,10]`, `[22,23,24]`, `[25,26,27]`, `[28,29,30]`, `[31]`, `[42,43,44]`, `[20,21]`.
   - Engineering development groups are `[1,32,45]`, `[11,12,13]`, `[14,15,16]`, `[17,18,19]`, `[33,34,35]`, `[36,37,38]`, `[39,40,41]`, `[42,43,44]`, `[20,21]`.
   - After each answer group, show the returned `review_summary` and `confirmed_so_far`, then ask the `confirmation_question`. If the user answers no, keep the interview on that same group until the group is re-confirmed.
   - New and existing projects both must answer the directory-contract group `[42,43,44]`; do not skip local, remote, or feature-directory rules for new work.
   - A grouped interview is not complete until the final `alignment_confirmed` confirmation succeeds. Takeover mode is the exception: after the minimum confirmation fields are answered, it should auto-synthesize the remaining strong-control answers and finish without expanding into the full question tree.
   - Unfinished interview chains must be resumed or explicitly abandoned with `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --reset-interview`.
   - Save answers to JSON only after the full design is aligned. Set `alignment_confirmed=true` only after user yes/no confirmation succeeds, then run `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --answers <answers.json> --write` before claiming strong-control AGENTS.md generation.
   - `--answers <answers.json> --write` must reject missing `default_conversation_language`; batch writes are formal generation flows and must not rely on an implicit default.
   - If `use_remote_server=yes`, first check whether `erie-remote-ssh` is installed. If it is missing, ask whether to install it from `https://github.com/Eriemon/remote-ssh.git` with install spec `skill=erie-remote-ssh`, `source_path=.`, `dest_name=erie-remote-ssh`.
   - If `use_remote_server=yes` and `erie-remote-ssh discover` reports no configured or enabled server list, ask whether to configure remote servers. Guided configuration uses `remote_ssh.py configure --interactive`; manual configuration remains blocked until the user finishes setup and resumes.
   - If `use_remote_server=yes` and `erie-remote-ssh choices` returns selectable servers, require explicit user task-route mapping even when there is only one enabled server. Each route must include `task_name` plus `primary_server_id`, may include `fallback_server_ids`, and every referenced server must pass `check` plus `workspace-check` before the route can be written into AGENTS.md.
   - When a route omits explicit route tasks, fall back to the selected primary server `functions` so the rendered contract never leaves responsibilities empty.
   - For user-developed Skills, require `skills/<skill-name>/SKILL.md`; the frontmatter `name` must exactly match the folder name and use only lowercase letters, digits, and hyphens. Reject root-level self-hosted skill folders such as `<project>/<skill-name>/SKILL.md`.
   - For engineering projects, require `engineering/<project-name>/` as the project directory contract; do not accept root-level engineering application folders.

3. **Extract**
   - Run `python skills/agents-md-generator/scripts/extract_commands.py <project>` to collect command candidates from Makefile, package.json, pyproject.toml, composer.json, go.mod, and visible CI workflow `run:` lines.
   - Run `python skills/agents-md-generator/scripts/extract_context.py <project>` to collect docs, ADRs, utilities, quality configs, agent configs, golden sample candidates, and CI rules.
   - Read `references/agents-md-guidance.md` for section choices and what belongs in AGENTS.md.
   - Read `references/skill-design-coverage.md` when generating or reviewing AGENTS.md for Skill development.
   - Read `references/capability-coverage.md` when comparing this skill to other AGENTS.md generator implementations.
   - Read `references/book-rules-coverage.md` before using book-derived engineering rule sets; choose one primary rule set and keep full material out of AGENTS.md.
   - Run `python skills/agents-md-generator/scripts/select_engineering_rules.py --list` or `--task <type>` when the user wants book-derived engineering guidance.

4. **Ask Missing Intent**
   - Ask only for preferences that cannot be discovered from files: commit policy, risky operations, approval boundaries, expensive checks, and domain terminology.
   - Use `references/question-bank.md` for focused questions.

5. **Generate**
   - Run `python skills/agents-md-generator/scripts/render_agents.py <project> --profile <project>/.agents/agents-control.json` first; default is dry-run.
   - Use `--write` only after reviewing the draft and confirming the target path is inside the intended repository.
   - For strong-control external work folders, structure governance must pass before `--write` continues. Run `python skills/agents-md-generator/scripts/manage_dirs.py structure-gate <project>` first; if it reports a primary root, top-level folder, or related structure violation, stop normal generation and ask whether to normalize the structure. 默认推荐“是”。
   - For old workspaces in takeover mode, do not continue asking whether to normalize structure. Use `python skills/agents-md-generator/scripts/manage_dirs.py takeover-fix <project>` as the forced local reorganization path after the minimum takeover confirmation completes.
   - Only continue after explicit user confirmation by rerunning `render_agents.py --write --confirm-structure-fix`; do not silently bypass a blocked structure gate.
   - For strong-control external work folders, branch governance must pass before `--write` continues. Run `python skills/agents-md-generator/scripts/manage_docs.py branch-gate <project>` first; if it reports branch or worktree violations, stop normal generation and ask whether to enter branch cleanup or release-governance handling.
   - Only continue after explicit user confirmation by rerunning `render_agents.py --write --confirm-branch-governance`; do not silently bypass a blocked branch gate.
   - When git management is enabled, generated release guidance must explicitly forbid repointing a repository with `git config core.worktree`; prefer normal checkout/merge or explicit `git worktree` commands instead.
   - Before `--write` with strong-control docs governance, run `python skills/agents-md-generator/scripts/manage_docs.py preflight <project>`; if it requires user confirmation, ask before using the existing `docs/` layout.
   - Strong-control generation creates or requires `.agents/agents-control.json` and the `docs/` governance tree. Experience records must live under `docs/experience/` as 10 numbered project-specific files; do not create a root-level `experience/` folder.
   - `render_agents.py --write` writes the root `AGENTS.md` with machine-readable version and default-language metadata plus an explicit natural-language reply rule tied to that configured language. The root file must stay within `16KB`; other `AGENTS.md` files are not subject to this hard size limit.
   - Generated strong-control roots must also write a `## Remote Server Contract` section. When remote usage is enabled, the section must record the registered remote server registry, each task route's primary and fallback servers, an automatic fallback rule for failed primaries, and a blocking rule that unmatched tasks must update AGENTS.md before remote validation continues.
   - After writing AGENTS.md files, run docs scaffolding for handoff, experience, development, install configuration, and git manager records.
   - Templates in `assets/templates/` define the intended root/scoped shape. AGENTS rendering must not scan the whole templates tree; it should use the root/scoped templates plus only the exact matching evolution target when supplemental guidance exists.
   - Use `--template-dir <dir>` only for controlled tests or intentional template overrides.

6. **Docs Governance**
   - If the external work folder already has legacy governance paths such as root `experience/`, root `DEVELOPMENT.md`, root `HANDOFF.md`, or misplaced `docs/HANDOFF.md` / `docs/DEVELOPMENT.md`, automatically migrate them into the governed `docs/` layout before continuing, and preserve history instead of silently overwriting.
   - When the external work folder already has landed content but no root `AGENTS.md`, run `python skills/agents-md-generator/scripts/manage_docs.py bootstrap-experience <project>` after the minimum takeover confirmation so the latest `docs/experience/*.md` and per-session `history_experience` snapshots are generated from exact-cwd Codex sessions plus current file evidence.
   - Before executing a new task after reading a prior handoff, run `python skills/agents-md-generator/scripts/manage_docs.py resume-check <project>`; if it reports an interrupted active session, run `python skills/agents-md-generator/scripts/manage_docs.py resume-repair <project> --input recovery.json` before handling the new request.
   - At task start, run `python skills/agents-md-generator/scripts/manage_docs.py start-session <project> --input session.json` after reading `docs/handoff/HANDOFF.md`.
   - Run `python skills/agents-md-generator/scripts/manage_docs.py scaffold <project>` when docs governance must be prepared without rewriting AGENTS.md.
   - At task completion, run `python skills/agents-md-generator/scripts/manage_docs.py handoff <project> --input handoff.json`; the current `docs/handoff/HANDOFF.md` is archived before the new latest handoff is written.
   - Every five handoffs, `manage_docs.py` creates `.agents/experience-update-request.json`; the current agent must read that request plus the current cadence window and up to 10 recent conversation snapshots, write a detailed `experience-payload.json`, and immediately apply it in the same conversation instead of leaving the request pending.
   - Apply AI-authored experience with `python skills/agents-md-generator/scripts/manage_docs.py experience <project> --payload experience-payload.json`; scripts validate, archive, write standardized cadence metadata, and reject vague or topic-mismatched lesson content, but must not fabricate lesson text.
   - Every ten handoffs, the same payload application must also include valid `evolution_summary` content so experience refresh and evolution complete atomically. Accepted experience evolves indexed templates under the single matching assets/templates/evolution family: skill projects use `skill-template/<category>/<type>/`, engineering projects use `engineering-template/<category>/<type>/`; do not copy the same experience into both families.
   - Evolution validation is two-layered: correct `family/category/type` path is required, and the summary text must also match the target workflow schema. Skill templates must reject engineering-only execution chains; engineering templates must reject skill/repo-governance chains.
   - At installable release or stage completion, run `python skills/agents-md-generator/scripts/manage_docs.py development <project> --stage <name> --input stage.json`.
   - Keep install setup for Codex, Claude, and OpenClaw under `docs/install_configuration/`; keep branch, release, dist, package naming, protected branch cleanup, `CHANGELOG.md`, changelog history, and current version rules under `docs/git_manager/`.
   - Rotate commit and release summaries with `python skills/agents-md-generator/scripts/manage_docs.py git-changelog <project> --input changelog.json`; archive the previous current file under `docs/git_manager/history_git_manager/<timestamp>/CHANGELOG.md` before writing the new one.
   - Prepare temporary development branches for release with `python skills/agents-md-generator/scripts/manage_docs.py release-prepare <project> --version vX.Y.Z --skill-dir skills/<skill-name>`.
   - Build versioned release directories, matching zip packages, and `RELEASE_RECEIPT.json` provenance with `python skills/agents-md-generator/scripts/manage_docs.py package-release <project> --version vX.Y.Z --skill-dir skills/<skill-name>`.
   - Verify branch, worktree, release artifact, release receipt, and parity gates with `python skills/agents-md-generator/scripts/manage_docs.py release-gate <project> --version vX.Y.Z --skill-dir skills/<skill-name> --phase pre|post`.
   - Keep local and remote deployment folder governance under `docs/dir_manager/`; before creating, moving, deleting, or renaming governed folders, run `python skills/agents-md-generator/scripts/manage_dirs.py review <project> --input change.json`.
   - For remote server deployment tasks, do not sync local skill-development content to servers; deploy only explicit runtime/deployment artifacts unless the user explicitly overrides.
   - If directory review is blocked, refuse default execution, explain the severe risks, and ask for explicit user force-confirmation before changing folder structure.
   - After explicit user force-confirmation and before applying the blocked folder change, run `python skills/agents-md-generator/scripts/manage_dirs.py archive <project> --reason "force-confirmed directory override"` so old dir manager content is preserved under `docs/dir_manager/history_dir_manager/<timestamp>/`.

7. **Verify**
   - Run `python skills/agents-md-generator/scripts/verify_agents.py <project>` after generation or edits.
   - For source-mode self-verification of this repository before installation, run `python skills/agents-md-generator/scripts/verify_agents.py . --installed-skill-dir skills/agents-md-generator`.
   - Verification must fail if the root `AGENTS.md` has `default_language` metadata but does not include the enforced reply-language rule, or if strong-control write inputs omit an explicit `default_conversation_language`.
   - Verification must also fail if a strong-control profile enables remote servers but the root `AGENTS.md` is missing `## Remote Server Contract`, any required task route primary server reference, the automatic fallback rule, or the unmatched-task blocking rule.
   - Verification must also fail if the root `AGENTS.md` omits its pointer to `.agents/global-rule-overrides.json`, if that JSON config is missing or malformed, or if generated text still inlines maintainability/script-governance detail that should live in config.
   - Verification must also fail if the config-backed maintainability rules are broken: handwritten source files or project tool scripts exceeding the configured limit must have a decomposition plan at the config-defined location, and non-GUI project tool scripts must satisfy the config-backed `scripts/<family>/<function>/<name>.<ext>` plus mirrored `shell` / `bat` / `powershell` rules.
   - When generating or repairing the global `.codex/AGENTS.md`, write only the shared principles there. Keep long-task heartbeat detail, decomposition-plan detail, and GUI exception detail in the local JSON governance config instead of AGENTS text.
   - Run `python skills/agents-md-generator/scripts/manage_docs.py verify <project>` when debugging docs governance failures directly.
   - Use `python skills/agents-md-generator/scripts/audit_skill.py <skill-dir>` when changing this skill itself.
   - Use `python skills/agents-md-generator/scripts/evaluate_skill.py <skill-dir> <project>` for the full fact-level validation chain after skill edits.
   - Run `python skills/agents-md-generator/scripts/check_freshness.py <project>` when updating an existing AGENTS.md.
   - Run `python skills/agents-md-generator/scripts/create_agent_shims.py <project>` only when the user wants CLAUDE.md/GEMINI.md compatibility.
   - After release packaging and successful validation, ask the install question only for skill development. Engineering projects must not ask whether to install a skill. If the user confirms installation for a skill, use `python skills/agents-md-generator/scripts/install_skill.py dist/<skill-name>-vX.Y.Z --target codex --write --replace` or `--target custom --custom-root <dir> --write --replace` when replacing an existing skill; the installer must reject source directories, require `RELEASE_RECEIPT.json`, back up the old skill, and preserve evolution templates before replacing. If no or no explicit response, skip installation.

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
