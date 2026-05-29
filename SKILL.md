---
name: agents-md-generator
description: Use when creating, updating, verifying, or reviewing AGENTS.md files and AI coding-agent rule files; when a project or current work folder root lacks AGENTS.md; when root AGENTS.md version metadata is missing or mismatched; when the user explicitly mentions AGENTS.md, agent rules, or scoped AGENTS.md; or when the user is talking about the current workspace/current repository/current work folder and says 计划, 规划, or 准备, which must first trigger a root AGENTS.md check.
---

# AGENTS.md Generator

Create operational context files for AI coding agents. Use facts from the repository first, ask only for missing human policy, and verify before claiming the draft is ready.

当用户明确提到 `AGENTS.md`、`agent rules`、`scoped AGENTS.md` 时，直接进入本技能。

当用户在当前工作区、当前工程、当前仓库、或当前工作文件夹语境里说“计划”、“规划”或“准备”时，也要进入本技能，但第一步不是直接设计，而是先检查当前工作文件夹根 `AGENTS.md` 状态。

当前工作区类请求除了检查当前工作文件夹根 `AGENTS.md`，还要检查全局 `~/.codex/AGENTS.md` 或 `$CODEX_HOME/AGENTS.md` 是否存在且包含受管的全局基线区块。这个全局文件只负责入口规则：要求代理先读取当前工作文件夹根 `AGENTS.md`，而不是替代仓库根文件中的本地约束。

入口路由要显式区分 4 类任务：`read_only`（解释、分析、规划、现状检查、只读 review）、`design`（收集/修订答案但尚未申请写入）、`write`（正式生成或更新 AGENTS 控制档案）、`governance_high_risk`（evolution 原子更新、release/merge 前治理审查）。只有 `write` 和 `governance_high_risk` 可以触发审查子智能体；`read_only` 明确禁止。

当根 `AGENTS.md` 通过 `default_language` 把默认自然语言回复锁定为某种语言时，这个约束也必须覆盖 Plan Mode：若代理输出 `<proposed_plan>`，标签内的方案正文必须使用该默认语言，除非用户显式切换语言；`<proposed_plan>` 标签本身保持原样，代码、命令、日志、原始错误文本和专有名词可保留原文。

如果用户明确要求创建、更新、审查或修复 `AGENTS.md` / `agent rules` / `scoped AGENTS.md`，先检查根 `AGENTS.md`，然后继续进入完整设计访谈或更新流程；不要因为根文件健康就提前停止。只有当前工作区类“计划 / 规划 / 准备”探测入口在根 `AGENTS.md` 正常时才只报告“检查通过”。

根 `AGENTS.md` 缺失或缺少版本元数据时，先报告异常原因，然后进入完整设计访谈。只有根 `AGENTS.md` 的 `agents_version` 或 `generator_version` 与当前已安装 `agents-md-generator` 版本不一致，并且当前工作文件夹已经有落地内容时，才允许进入最小 takeover 兼容流程。

如果全局 `.codex/AGENTS.md` 缺失、为空、或缺少受管基线区块，不要静默忽略；要明确报告“全局入口规则未落盘”，并给出 `python skills/agents-md-generator/scripts/manage_docs.py sync-global-codex-agents . --write` 作为修复命令。

如果是“已有内容但无根 `AGENTS.md`”的工作文件夹，除了结构检查之外，还要读取精确匹配当前工作目录的 Codex sessions：只接受 `.codex/sessions` 中 `session_meta.payload.cwd` 规范化后与当前工作目录完全一致的会话。先用这些会话和现有落地文件补建 `docs/experience/history_experience/` 历史经验，再生成最新的 `docs/experience/*.md`。

如果用户明确要求进行 Codex Token 用量统计，例如直接要求“统计 Codex token usage / Token 用量 / token 消耗”，走只读工具分支：直接运行 `python skills/agents-md-generator/scripts/codex_token_usage_review.py --hours 48`，按用户要求决定是否附加 `--verbose` 或 `--json`，不要进入 AGENTS 设计访谈。这个分支只在当前环境可解析到 `$CODEX_HOME/sessions` 或 `~/.codex/sessions` 且目录存在时执行；如果检测不到 Codex sessions 目录，要明确拒绝执行并说明原因。`--sessions-root` 只允许等于或位于当前 Codex sessions 根目录之下，用于测试或诊断时也不能跳出当前 Codex sessions 树。泛化的成本、优化、会话健康、/status 建议等问题不算显式触发。

外部工作区生成的 AGENTS/docs 治理命令必须调用已安装的 `agents-md-generator` 运行时，例如 `python <codex-home>/skills/agents-md-generator/scripts/manage_docs.py ...`。不要把这些 governance runtime 脚本写成目标项目自己的 `scripts/manage_docs.py` / `scripts/manage_dirs.py`，也不要为了让命令可执行而把本 skill 的脚本复制进目标工作区。只有 `agents-md-generator` owner repo 自身允许继续使用 repo-local `python skills/agents-md-generator/scripts/...` 自举路径。

## Pipeline

1. **Detect**
   - Run `python skills/agents-md-generator/scripts/inspect_project.py <project>` to gather language, framework, package manager, CI, AI configs, files, and directories.
   - If `root_agents_md_exists` is false, or the root `AGENTS.md` is missing `agents_version` or `generator_version`, or either version does not match the current local installed `agents-md-generator` version, treat the workspace as trigger-required/rebuild-required.
   - Inspect the global `.codex/AGENTS.md` baseline status too. If it is missing, empty, unmanaged, or outdated, report the exact reason and recommend `python skills/agents-md-generator/scripts/manage_docs.py sync-global-codex-agents . --write`.
   - When the user says `计划`, `规划`, or `准备` in the current workspace/current repository/current work folder context, do this root-AGENTS check first. These are trigger entries for inspection routing, not a bypass around the AGENTS.md check.
   - If the root check passes during a current-workspace/current-repository/current-work-folder `计划` / `规划` / `准备` trigger, report that the current work folder root `AGENTS.md` check passed and stop. If the user explicitly asked to create, update, review, or repair AGENTS governance, continue into the full design/update flow instead of stopping.
   - If the root check fails because the root `AGENTS.md` is missing, missing `agents_version`, or missing `generator_version`, report the exact abnormal reason and continue into the full design interview.
   - If the root check fails because `agents_version` or `generator_version` is version-mismatched in an old workspace with landed content, switch to takeover handling instead of the full design interview: minimize identity questions to project type, project/skill name, and default conversation language, but do not skip the structured directory-contract interview. Takeover must still collect local structure, remote structure, feature-placement rules, and any required remote runtime policy before AGENTS.md can be written.
   - If the workspace already has landed content but no root `AGENTS.md`, mark session bootstrap as required, inspect exact-cwd Codex session history, and prepare forced local workspace takeover before normal AGENTS generation continues.
   - Run `python skills/agents-md-generator/scripts/detect_scopes.py <project>` to find directories that may need scoped AGENTS.md files.

2. **Design Interview**
   - Start grouped interviews with `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --start`; use `--intent read_only` for explanation, analysis, planning, current-state checks, or read-only review, and keep the default write intent only when the user is actually preparing to write/update governed control files. `--start` should enter takeover mode automatically only for version-mismatched old workspaces with landed content. Missing root files or missing version metadata must stay on the full grouped interview. If `.agents/design-interview-state.json` already exists and is unfinished, resume it instead of silently starting over.
   - Use `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --start-takeover` or `--resume-takeover` only when the root `AGENTS.md` is version-mismatched for an old workspace and you need the forced takeover path explicitly.
   - Use `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --resume` whenever an earlier design interview is still incomplete.
   - Submit one group at a time with `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --answer-file partial.json`.
   - Ask every returned question in the current group and present each returned `options` list to the user. Prefer `request_user_input` when available so the user can choose an option or enter a custom answer.
   - Question `32` for `default_conversation_language` is mandatory for every AGENTS generation or takeover-restructure flow. Do not skip it, infer it, or silently fall back to `中文`.
   - Question `45` for `use_remote_server` is mandatory for every AGENTS generation or takeover-restructure flow. If the user enables remote servers, do not continue until the remote dependency, configuration, task-route mapping, and validation gates are complete.
   - Skill development groups are `[1,32,45]`, `[2,3,4]`, `[5,6,7]`, `[8,9,10]`, `[22,23,24]`, `[25,26,27]`, `[28,29,30]`, `[31]`, `[42,43,44,46,47,48,49]`, `[20,21]`.
   - Engineering development groups are `[1,32,45]`, `[11,12,13]`, `[14,15,16]`, `[17,18,19]`, `[33,34,35]`, `[36,37,38]`, `[39,40,41]`, `[42,43,44,46,47,48,49]`, `[20,21]`.
   - After each answer group, show the returned `review_summary` and `confirmed_so_far`, then ask the `confirmation_question`. If the user answers no, keep the interview on that same group until the group is re-confirmed.
   - After all grouped interview questions are confirmed, ask whether the user has extra requirements. Record `extra_requirements="none"` when there is no supplement; otherwise write the user's supplement into the control profile and rendered Control Profile.
   - After the final full-design alignment, `--intent read_only` must stop at a read-only completed state, retain `answers_snapshot` plus `profile_preview`, and must not generate `design_review_request` or spawn a review subagent.
   - After the final full-design alignment, write intent must spawn a new review subagent to review the complete answers and profile. Submit its structured `design_review` JSON with `reviewer_type="subagent"`, `verdict`, `findings`, `required_user_confirmations`, `reviewed_answers_hash`, `reviewed_profile_hash`, and `review_summary`.
   - If the subagent rejects the design or returns any `required_user_confirmations`, stop in rework mode, ask the user to confirm the correction items, apply corrections, clear the old review/hash, and repeat final alignment plus subagent review before writing.
   - New and existing projects both must answer the directory-contract group `[42,43,44,46,47,48,49]`; do not skip local, remote, feature-directory, remote conda, or remote runtime archive rules for new work.
   - The remote directory policy fields (`46-49`) are formal write gates whenever `use_remote_server=true` or `remote_directory_structure != not configured`. They may be stored as disabled only when remote structure is explicitly not configured.
   - When remote directory policy is enabled, reject dangerous templates before write: remote conda and runtime path templates must stay relative to the remote workspace root, and they must not contain `..`, wildcards, unsafe shell characters, empty values, or repeated separators such as `//`.
   - A grouped interview is not complete until `extra_requirements` is recorded and the final `alignment_confirmed` confirmation succeeds. Write intent additionally requires an approved subagent `design_review` with matching hashes before `--write`; read-only intent must stop short of that review gate until the caller explicitly runs `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --enter-write-review`. Takeover mode may still auto-synthesize non-directory descriptive fields after the minimum identity answers, but it must not auto-confirm final alignment, skip the extra-requirements question, bypass the write-intent review gate, or auto-fill the directory contract.
   - Unfinished interview chains must be resumed or explicitly abandoned with `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --reset-interview`.
   - Save answers to JSON only after the full design is aligned and the approved subagent design review is attached. Set `alignment_confirmed=true` only after user yes/no confirmation succeeds, then run `python skills/agents-md-generator/scripts/collect_design_profile.py <project> --answers <answers.json> --write` before claiming strong-control AGENTS.md generation.
   - `--answers <answers.json> --write` must reject missing `default_conversation_language`, missing explicit `use_remote_server`, missing `extra_requirements`, and any missing, non-subagent, rejected, confirmation-pending, or hash-mismatched `design_review`; batch writes are formal generation flows and must not rely on implicit defaults or unreviewed alignment.
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
   - Structure governance now also hard-blocks unapproved root-level files outside the governed primary project root. Only the fixed root whitelist such as `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.gitignore`, `.gitattributes`, and `.editorconfig` may stay at the repository root by default.
   - For old workspaces in explicit or auto-routed takeover mode, do not continue asking whether to normalize structure. Use `python skills/agents-md-generator/scripts/manage_dirs.py takeover-fix <project>` as the forced local reorganization path only after the structured directory contract has been fully confirmed.
   - Only continue after explicit user confirmation by rerunning `render_agents.py --write --confirm-structure-fix`; this flag means “allow the conservative structure-fix attempt”, not “bypass structure governance”.
   - After any confirmed structure-fix attempt, rerun `structure-gate` and keep the write blocked if root-level file drift, directory drift, or any other structure violation remains.
   - For strong-control external work folders, branch governance must pass before `--write` continues. Run `python skills/agents-md-generator/scripts/manage_docs.py branch-gate <project>` first; if it reports branch or worktree violations, stop normal generation and ask whether to enter branch cleanup or release-governance handling.
   - Only continue after explicit user confirmation by rerunning `render_agents.py --write --confirm-branch-governance`; do not silently bypass a blocked branch gate.
   - When git management is enabled, generated release guidance must explicitly forbid repointing a repository with `git config core.worktree`; prefer normal checkout/merge or explicit `git worktree` commands instead.
   - Before `--write` with strong-control docs governance, run `python skills/agents-md-generator/scripts/manage_docs.py preflight <project>`; if it requires user confirmation, ask before using the existing `docs/` layout.
   - Strong-control generation creates or requires `.agents/agents-control.json` and the `docs/` governance tree. Experience records must live under `docs/experience/` as 10 numbered project-specific files; do not create a root-level `experience/` folder.
   - Workspace engineering config belongs under `.settings/`: local-only files use `.settings/project.local.json` or `.settings/<name>.local.json`, remote workspace config uses `.settings/project.remote.json` or `.settings/<name>.remote.json`, and local private `.settings/*.local.json` files must never be copied to remote servers.
   - `render_agents.py --write` writes the root `AGENTS.md` with machine-readable version and default-language metadata plus an explicit natural-language reply rule tied to that configured language. The root file must stay within `16KB`; other `AGENTS.md` files are not subject to this hard size limit.
   - Generated root `AGENTS.md` must include `## Code Comment Policy` from configurable `code_comment_policy` in `.agents/global-rule-overrides.json`: summarize the Chinese Python/C/C++/Verilog policy, allow only non-obvious intent, invariants, risk, generation boundaries, or public API behavior comments, forbid obvious restatement comments, update stale comments when behavior changes, preserve code line/blank-line separation, and forbid bulk AI-generated commenting unless the user explicitly requests it.
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
   - Handoff naming is a hard gate: the latest handoff must remain exactly `docs/handoff/HANDOFF.md`, and history files under `docs/handoff/history_handoff/` must stay `HANDOFF-YYYYMMDD-HHMMSS.md` or `HANDOFF-YYYYMMDD-HHMMSS-N.md`. Do not silently rename, duplicate, or replace those files. If naming drifts, use `python skills/agents-md-generator/scripts/manage_docs.py repair-handoff-names <project> --write` explicitly before normal docs governance continues.
   - Every five handoffs, `manage_docs.py` creates `.agents/experience-update-request.json`; the current agent must read that request plus the current cadence window and up to 10 recent conversation snapshots, write a detailed `experience-payload.json`, and immediately apply it in the same conversation instead of leaving the request pending.
   - 普通用户工作文件夹也要保留自动进化能力：第十次 handoff 的 `experience-update-request` 必须携带 evolution 原子合同，但 active reusable templates 不再写回当前工作区本地 `assets/templates/evolution/`。优先写入本机可写的已安装 `agents-md-generator` 模板库；若不可写，则在当前工作区生成 `.agents/evolution-export/` 待导入包和 `.agents/evolution-import-request.json`。
   - 第十次 handoff 的 `experience-update-request` 必须直接携带自动进化所需的 machine-readable 合同：`requires_atomic_evolution`、规范化后的 `evolution_target`、`target_schema_label`、`flow_requirements`、`mixed_content_risks`、`requires_extra_evolution_review`、`review_scope`、`review_blocking`、`review_contract`、`release_alignment_evidence`、`evolution_sink`，以及 `payload_schema.evolution_summary` 示例。外部 Codex/agent 应只读这一份 request 就能一次性生成 experience 与 evolution payload，而不是先跑 `evolve` 再靠失败反推缺什么。
   - 第十次 handoff 的 evolution 还必须经过 1 个额外的评审智能体。该评审只负责 evolution，不直接写模板；它必须独立检查分类是否匹配仓库事实、release/CHANGELOG/DEVELOPMENT/handoff 证据是否支撑该总结，以及是否需要回读 exact-cwd Codex sessions。
   - Apply AI-authored experience with `python skills/agents-md-generator/scripts/manage_docs.py experience <project> --payload experience-payload.json`; scripts validate, archive, write standardized cadence metadata, and reject vague or topic-mismatched lesson content, but must not fabricate lesson text.
   - Every ten handoffs, the same payload application must also include valid `evolution_summary` content and an `evolution_review` object so experience refresh and evolution complete atomically. `evolution_review` must include `verdict` (`approve` / `reject` / `approve_with_override`), `approved_target`, `original_target`, `evidence_read`, `session_reread_performed`, `session_reread_reason`, and `full_explanation`. Accepted experience evolves indexed templates under the single matching evolution family. Owner repositories may write locally into their own template root; ordinary work folders must write into the installed skill template library or a pending import bundle instead of generating active local templates.
   - Evolution validation is two-layered: correct `family/category/type` path is required, and the summary text must also match the target workflow schema. Skill templates must reject engineering-only execution chains; engineering templates must reject skill/repo-governance chains.
   - If the extra evolution review rejects the target, cites non exact-cwd sessions, or returns `approve_with_override` whose approved target still differs from the payload target, block template writing, write `.agents/evolution-review-request.json`, and require a new aligned payload instead of silently continuing.
   - 如果 `.agents/docs-governance-state.json` 中的 `last_evolution_target` 仍是旧的字符串路径或其他坏格式，不要沿用坏状态继续推断。使用 `python skills/agents-md-generator/scripts/manage_docs.py evolve <project> --force` 或重新应用新的 experience payload 进行修复；修复后的状态必须把 `last_evolution_target` 写回规范对象，而不是文件路径字符串。对普通用户工作文件夹，应清理历史误生成的本地 `assets/templates/evolution/`，但保留新的 sink/export/import 状态字段。
   - At installable release or stage completion, run `python skills/agents-md-generator/scripts/manage_docs.py development <project> --stage <name> --input stage.json`.
   - Keep install setup for Codex, Claude, and OpenClaw under `docs/install_configuration/`; keep branch, release, dist, package naming, protected branch cleanup, `CHANGELOG.md`, changelog history, and current version rules under `docs/git_manager/`.
   - Rotate commit and release summaries with `python skills/agents-md-generator/scripts/manage_docs.py git-changelog <project> --input changelog.json`; archive the previous current file under `docs/git_manager/history_git_manager/<timestamp>/CHANGELOG.md` before writing the new one.
   - Prepare temporary development branches for release with `python skills/agents-md-generator/scripts/manage_docs.py release-prepare <project> --version vX.Y.Z --skill-dir skills/<skill-name>`.
   - Build versioned release directories, matching zip packages, and `RELEASE_RECEIPT.json` provenance with `python skills/agents-md-generator/scripts/manage_docs.py package-release <project> --version vX.Y.Z --skill-dir skills/<skill-name>`. Installable skill releases may include governed skill-local `evals/`, but they must block work-folder-only content such as `tests/`, `test/`, `smoke*`, `reports/`, `runs/`, `_smoke_runs/`, and cache artifacts instead of copying them into `dist/`.
   - Verify branch, worktree, release artifact, release receipt, and parity gates with `python skills/agents-md-generator/scripts/manage_docs.py release-gate <project> --version vX.Y.Z --skill-dir skills/<skill-name> --phase pre|post`. Post-release validation must fail when the release directory or receipt content policy shows forbidden development content or unexpected top-level release entries.
   - Keep local and remote deployment folder governance under `docs/dir_manager/`; before creating, moving, deleting, or renaming governed folders, run `python skills/agents-md-generator/scripts/manage_dirs.py review <project> --input change.json`.
   - `planned_structure.json` must carry machine-checkable directory governance, including `allowed_root_files`, `remote_deployment.protected_path_classes`, and `remote_deployment.require_review_for_all_mutations=true`.
   - `planned_structure.json` and remote directory governance must also carry the `.settings` workspace-config contract: allow `.settings/` as the governed work-folder config root, reject `*.local.json` / `*.remote.json` files outside `.settings/`, allow remote `.settings/*.remote.json`, and block remote `.settings/*.local.json` such as `.settings/server_list.local.json`.
   - Remote review is strict for all mutation types. Every remote `create`, `move`, `delete`, or `rename` must keep both source and target paths inside the governed remote plan, must report path classes, and must enforce runtime stage rules: unverified artifacts stay in active runs, verified artifacts move to backups, and destructive actions on protected remote path classes are blocked by default.
   - For remote server deployment tasks, do not sync local skill-development content to servers; deploy only explicit runtime/deployment artifacts unless the user explicitly overrides.
   - If directory review is blocked, refuse default execution, explain the severe risks, and ask for explicit user force-confirmation before changing folder structure.
   - After explicit user force-confirmation and before applying the blocked folder change, run `python skills/agents-md-generator/scripts/manage_dirs.py archive <project> --reason "force-confirmed directory override"` so old dir manager content is preserved under `docs/dir_manager/history_dir_manager/<timestamp>/`.

7. **Verify**
   - Run `python skills/agents-md-generator/scripts/verify_agents.py <project>` after generation or edits.
   - For source-mode self-verification of this repository before installation, run `python skills/agents-md-generator/scripts/verify_agents.py . --installed-skill-dir skills/agents-md-generator`.
   - Verification must fail if the root `AGENTS.md` has `default_language` metadata but does not include the enforced reply-language rule, or if strong-control write inputs omit an explicit `default_conversation_language`.
   - Verification must also fail if a strong-control profile enables remote servers but the root `AGENTS.md` is missing `## Remote Server Contract`, any required task route primary server reference, the automatic fallback rule, or the unmatched-task blocking rule.
   - Verification must also fail if a governed remote directory policy is enabled but the root `AGENTS.md` omits the remote conda path template, the active runtime path template, the backup runtime path template, or the archive trigger text.
   - Verification must also fail if a strong-control root omits the `.settings` workspace-config contract, weakens the `.local.json` / `.remote.json` naming rule, or fails to forbid copying `.settings/*.local.json` such as `.settings/server_list.local.json` to remote servers.
   - Verification must also fail if the root `AGENTS.md` omits its pointer to `.agents/global-rule-overrides.json`, if that JSON config is missing or malformed, or if generated text still inlines maintainability/script-governance detail that should live in config.
   - Verification must also fail if a managed root `AGENTS.md` omits `## Code Comment Policy`, omits or weakens `code_comment_policy`, loses the Python/C/C++/Verilog language-specific rules, loses the stale-comment update rule, loses the formatting rule that generated code cannot be glued together, or loses the bulk-AI-commenting prohibition.
   - Verification must also fail if the config-backed maintainability rules are broken: handwritten source files matched by the configured source-governance hard-fail extensions exceeding the configured limit must block immediately, and non-GUI project tool scripts must satisfy the fixed config-backed quartet `scripts/python/<function>/<name>.py`, `scripts/shell/<function>/<name>.sh`, `scripts/bat/<function>/<name>.bat`, and `scripts/powershell/<function>/<name>.ps1`.
   - When generating or repairing the global `.codex/AGENTS.md`, write only the shared principles there. Keep long-task heartbeat detail, decomposition-plan detail, and GUI exception detail in the local JSON governance config instead of AGENTS text.
   - Run `python skills/agents-md-generator/scripts/manage_docs.py verify <project>` when debugging docs governance failures directly.
   - `manage_docs.py verify`, `work-folder-gate`, `release-gate`, and `run_confidence_gate.py` must all fail when handoff naming drifts inside `docs/handoff/`; a renamed current handoff must never be masked by `scaffold()` creating a fresh placeholder.
   - Run `python skills/agents-md-generator/scripts/manage_docs.py work-folder-gate <project> --skill-dir skills/<skill-name> --mode development|release` before confidence-sensitive work or release validation when you need one workspace-management gate for resume state, structure, directory governance, branch state, version alignment, and AGENTS freshness.
   - Use `python skills/agents-md-generator/scripts/audit_skill.py <skill-dir>` when changing this skill itself.
   - Use `python skills/agents-md-generator/scripts/evaluate_skill.py <skill-dir> <project>` for the full fact-level validation chain after skill edits.
   - Use `python tests/run_skill_evals.py skills/agents-md-generator/evals/evals.json` for the repo-local skill-effectiveness layer. These evals must compare with-skill and without-skill expectations, report whether the skill actually improves behavior, cover all five Skill design patterns, and cover recent high-risk regressions such as missing-root detection, takeover routing, root-level whitelist gating, root-only workspace artifact gating for `tests/smoke*/reports/runs`, exact-cwd evolution review, generic audit/evaluate behavior, release completeness blocking, release-content policy allowing skill-local `evals/` while blocking work-folder artifacts, configurable code comment policy enforcement, and tests-only source-governance boundaries.
   - Use `python skills/agents-md-generator/scripts/review_governance.py <project> --base <sha> --head <sha> --skill-dir skills/<skill-name> --mode release` before release or merge to deterministically check whether governance-sensitive code, CLI, gate, version, docs, eval, and release-record changes are synchronized. Non-release analysis may use `--mode all|code|design`; those modes still emit deterministic findings but should report `review_dispatch_policy=optional` or `none` instead of implying an automatic reviewer dispatch. Use `--write-request` only when a persistent `.agents/review-request.json` is needed for a follow-up human or subagent review.
   - Use `python skills/agents-md-generator/scripts/run_confidence_gate.py <project> --review-base <sha> --external-skill-dir <healthy-skill-dir>` when you need one aggregate evidence pass that includes quick validation, source governance, docs governance, work-folder governance, freshness, automated review governance, verify, evaluate, skill-effectiveness evals, release gates, install-skip, and healthy external-skill evaluation evidence.
   - Run `python skills/agents-md-generator/scripts/check_freshness.py <project>` when updating an existing AGENTS.md.
   - Run `python skills/agents-md-generator/scripts/create_agent_shims.py <project>` only when the user wants CLAUDE.md/GEMINI.md compatibility.
   - After release packaging and successful validation, ask the install question only for skill development. Engineering projects must not ask whether to install a skill. If the user confirms installation for a skill, use `python skills/agents-md-generator/scripts/install_skill.py dist/<skill-name>-vX.Y.Z --target codex --write --replace` or `--target custom --custom-root <dir> --write --replace` when replacing an existing skill; the installer must reject source directories, require `RELEASE_RECEIPT.json`, reject releases whose content policy shows forbidden development content or unexpected top-level entries, back up the old skill, and structurally merge installed evolution templates before falling back to conflict copies. If no or no explicit response, skip installation.

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
| `references/evaluation-scenarios.md` | Regression scenarios and skill-effectiveness eval coverage for recent high-risk regressions |
| `assets/templates/root-agents.md` | Root AGENTS.md structure |
| `assets/templates/scoped-agents.md` | Directory-scoped AGENTS.md structure |
| `scripts/manage_docs.py` | Skill-local governance runtime; owner repo or installed skill uses it to scaffold docs governance, handoff rotation, AI experience requests/payload application, evolution templates, development records, and verification |
| `scripts/manage_dirs.py` | Skill-local governance runtime; owner repo or installed skill uses it for strict local and remote folder structure scan, planning, review, blocking, and verification |
| `scripts/review_governance.py` | Deterministic companion-change gate that emits optional review metadata for ordinary analysis and required-for-release review metadata for release/merge risk |
| `evals/evals.json` | Repo-local skill-effectiveness cases with with-skill versus without-skill expectations |
