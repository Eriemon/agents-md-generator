---
name: agents-md-generator
description: Use when creating, updating, compressing, reviewing, or verifying AGENTS.md and other AI coding-agent rules; when a managed root AGENTS.md is missing, malformed, stale, or version-incompatible; when the user explicitly mentions AGENTS.md, agent rules, or scoped AGENTS.md; when a managed skill README needs a functional illustration set; or when a request about the current workspace, repository, or work folder says 计划, 规划, or 准备 and therefore requires a root AGENTS.md check first.
---

# AGENTS.md Generator

Generate operational agent rules from repository facts and confirmed human policy. Keep roots short, place local rules near their scope, preserve human text outside managed blocks, and verify every write.

## Route

- Explicit AGENTS creation, update, compression, review, or repair enters the full workflow even when the root is healthy.
- A current-workspace `计划` / `规划` / `准备` request first checks root and global AGENTS state. If the managed root is healthy, report that result and return to the user's task; otherwise report the exact defect and continue to design or takeover.
- Use `read_only` for explanation, planning, state checks, and read-only review; use `design` while collecting policy; use `write` for approved managed changes; use `governance_high_risk` for release or merge review. None of these modes authorizes a non-testing subagent. Only the user's proactive and explicit request in the current task does, and it must name the role or purpose.
- If the user explicitly asks for Codex Token usage statistics, use registry instruction `detect.token-usage-review`; do not enter the AGENTS design interview. Use it only when `$CODEX_HOME/sessions` or `~/.codex/sessions` exists, and keep any sessions-root override inside that active sessions tree. Generic cost, optimization, and session-health questions do not trigger this branch.
- External work folders call the installed skill runtime. Only this owner repository uses repo-local `python skills/agents-md-generator/scripts/python/...` paths.
- 当技能开发需要链接 GitHub 仓库时，统一使用 `github/` 现有 checkout 合同：先完成版本化 `dist/` 发布与安装，再执行只写本地 checkout 的镜像、计划和复核；策略为 `existing-only`，工具不创建远程仓库或执行 push。

## Inspect

1. Read applicable AGENTS files, the latest handoff, memory guidance, and repository governance.
2. Use registry instructions `detect.inspect-project` and `detect.detect-scopes`.
3. Check global `~/.codex/AGENTS.md` or `$CODEX_HOME/AGENTS.md` for the managed baseline and version.
4. Treat missing metadata as a full-design trigger. Use takeover only for a version-mismatched old workspace with landed content.
5. For strong-control work, pass `memory-gate`; bootstrap exact-cwd Codex sessions when required.
6. When codebase-memory MCP is enabled, require a ready `full` persistent index, successful architecture analysis, root-only artifacts, and matching live/disk counts before writes.

The global v4 baseline owns only cross-repository defaults: instruction scope, managed entry, reuse-first execution, advisory task rating, frozen goal/success/in-scope/out-of-scope boundaries, decision-complete plans, user-opt-in-only non-testing subagents, executable-test-surface routing to one isolated TESTER that owns `tests/**`, comprehension-driven prose/table/Mermaid selection, the four-part `Coding Behavior Baseline`, `Done When`, dual Python/script preflight, comments/documentation, environment/dependency safety, installed-skill protection, and Markdown `$...$` / `$$...$$` formulas. Generic multi-agent requests, task complexity, ratings, risk, and agent judgment do not authorize non-testing subagents. Project thresholds, layouts, exceptions, long-task rules, language detail, and releases stay in project governance.

## Design

Use registry instruction `design.collect-profile`, resume unfinished state, and submit one returned group at a time.

- Ask every returned question and show its options. Do not infer mandatory `default_conversation_language` (32), `use_remote_server` (45), or `use_codebase_memory_mcp` (55).
- The selected language governs all natural-language replies, including Plan Mode `<proposed_plan>` content, unless the user switches languages.
- Skill development groups are `[1,32,45,55]`, `[50,51,52,53,54]`, `[2,3,4]`, `[5,6,7]`, `[8,9,10]`, `[22,23,24]`, `[25,26,27]`, `[28,29,30]`, `[31]`, `[42,43,44,46,47,48,49]`, `[20,21]`.
- Engineering development groups are `[1,32,45,55]`, `[50,51,52,53,54]`, `[11,12,13]`, `[14,15,16]`, `[17,18,19]`, `[33,34,35]`, `[36,37,38]`, `[39,40,41]`, `[42,43,44,46,47,48,49]`, `[20,21]`.
- After each group, show `review_summary` and `confirmed_so_far`, then obtain confirmation. Record `extra_requirements`, including explicit `none`, and require final alignment.
- Read-only intent ends with `answers_snapshot` and `profile_preview`; it creates no design review. Write intent also defaults to no review subagent. Enter `design_review` only when the user proactively and explicitly requests a design-review subagent in the current task; an explicitly requested review still requires `reviewer_type="subagent"`, matching `reviewed_answers_hash` and `reviewed_profile_hash`, no unresolved findings, and no required user confirmations.
- `--answers ... --write` rejects missing mandatory answers, alignment, extra requirements, or directory policy. When explicit review evidence is supplied, validate it rather than making it a default prerequisite.
- If remote servers are enabled, require installed/configured `erie-remote-ssh`, explicit task routes, checked primary/fallback servers, and workspace checks. Resolve the matched route at runtime, automatically try registered fallbacks after primary failure, and stop unmatched tasks until AGENTS.md/profile is updated.
- Detect an installed skill only from its directory and root `SKILL.md`. Treat CLI entry and settings discovery as separate capabilities; prefer the Python runtime `remote_ssh.py` entry, retain the legacy scripts-level entry only as a compatibility fallback, and never report a present skill as uninstalled because its internal layout changed.
- Remote structure governance is separate from remote-server enablement and task-route mapping. Validate relative conda/runtime/archive templates and reject traversal, wildcards, unsafe shell characters, empty values, and repeated separators.
- If codebase-memory MCP is requested but unavailable, provide manual installation guidance, never download or execute the installer automatically, and require restart before resuming.

## Generate

1. Run structure, branch, directory, memory, and codebase-memory gates required by the profile.
2. Use registry instruction `render.render-agents`; preview first and write only after approval.
3. Preserve text outside `AGENTS-GENERATED` blocks. Templates define root and scoped shape; do not absorb legacy evolution templates.
4. Keep the root an operational index. Put detailed remote registries in `.agents/agents-control.json`, directory policy in `docs/dir_manager/planned_structure.json`, and configurable coding/output rules in `.agents/global-rule-overrides.json`.
5. Create scoped AGENTS only for verified local differences. Do not restate inherited root rules.
6. Keep `.settings/` as work-folder configuration; allow remote `.settings/*.remote.json` and never copy `.settings/*.local.json`, including `.settings/server_list.local.json`, to remote systems.

### README illustration contract

When a user asks this skill to create README illustrations for a skill, treat the request as a functional design deliverable, not as a decorative image task:

1. Write a visual brief from the skill's real inputs, decisions, outputs, gates, and boundaries before generating anything.
2. Use Image2/ImageGen to generate original raster artwork. SVG is forbidden as a README illustration; Mermaid is also forbidden in the public image assets.
3. Make the main image a horizontal 16:9 overview that is legible in a repository README. Add style-consistent detail images for each major capability instead of repeating or cropping the hero.
4. Use panels, tables, relationship maps, code fragments, state cards, or formulas only when they clarify the function. Avoid generic stock imagery, empty neon decoration, and a linear checklist with no functional information.
5. Provide matching English and Chinese PNGs when the skill has bilingual READMEs, keep them local under `assets/readme/`, and reference every image from the README that explains it.
6. Validate PNG signatures, dimensions, local paths, and absence of SVG/remote metadata before copying images into the source package or `dist/`.

Managed roots render `coding_behavior.language_skill_routing` exactly as `shared`, `python`, and `script`: shared think-first/in-process gates appear 只渲染一次; Python remains owned by `readable-python-generator`; bat/cmd, shell/bash, PowerShell, and Tcl remain owned by `readable-script-generator`; a script wrapper that invokes Python is still a script target. Preserve line separation, 严禁把代码压缩到一行, and reject 炫技代码. Render `script_output_policy` from configuration rather than hard-coded business enums.

## Safety

- Do not invent commands, paths, owners, frameworks, CI rules, security policies, or coverage targets.
- Keep every proposed solution and plan inside the frozen user goal. Include only requested behavior, minimal integration, and current mandatory gates; mark every speculative feature, refactor, abstraction, compatibility layer, optimization, or configuration as out of scope unless the user explicitly reopens the boundary.
- Formal plans must be detailed enough to execute without additional design questions: name exact steps, inputs, outputs, files or interfaces, preconditions, failure handling, checks, and stop conditions. Use prose, tables, Mermaid, or a combination only where each form improves comprehension.
- Do not dispatch non-testing subagents by default, including solution, design, or plan reviewers, implementation agents, and parallel workers. Only the user's proactive and explicit request in the current task authorizes them, and it must name the role or purpose. A generic request to use multi-agent, complexity, task ratings, risk, or agent judgment is not authorization. If the user omits the count, use exactly three authorized non-testing subagents; an explicit count overrides that default, and authorization never carries into another task.
- When work has an executable test surface, use exactly one `fork_turns=none` TESTER. Pure read-only or planning work and documentation-only changes without a test surface do not require one.
- Only that TESTER may inspect, change, or run `tests/**`. It reports symptoms, counts, feedback, and suggestions; the mother agent changes non-test product files and sends the result back to the same TESTER for revalidation. Routine test-hash confirmation is prohibited: the Agent autonomously confirms an authoritative agreement, corrects report-only mismatches, and stops for user review without autonomous rerun when provenance conflicts or is insufficient.
- New test files use functional or behavioral semantic names; filename stems must not contain digits, including v1, v2, 1, 2, part1, and part2. Do not bulk-rename existing tests.
- Every managed root must render exactly one `Workspace boundary` rule. Modify inside the current work folder and the verified remote-server work folder without additional confirmation; remote changes still require an exact configured task route. Official codebase-memory start, index refresh, rebuild, or recovery for the project bound to either work folder, including its configured runtime cache and root persistence artifact, also needs no additional confirmation. Necessary side-effect-free reads remain allowed beyond those boundaries. Every other external write is prohibited by default and enters the process only after the user proactively and explicitly requests the exact action; then disclose the normalized target, action, scope, risks, alternatives, and recovery limits and obtain exactly one explicit confirmation. A target or scope change invalidates that confirmation.
- The canonical TESTER is `tester_worker` from `~/.codex/agents/tester_worker.toml`; generation and AGENTS refresh must create or validate that file, use `gpt-5.6-luna` with reasoning `max`, and preserve its backup before refreshing drifted content. Do not delegate `tests/**` to a generic or second test agent.
- A single-task authorization receipt is confirmed once across the skill, AGENTS.md, and CLI; reuse it for the same target and scope, and re-confirm only when the target, scope, or material risk changes.
- Generated roots always include a state-aware, fail-closed remote work-folder contract: resolve the exact configured route and verified workspace, and keep deployment, conda/runtime, backup, and archive lifecycle details in `docs/dir_manager/planned_structure.json`.
- `allowed_root_files` governs root-level exceptions. Root-level files outside the governed primary project root require review; allow the conservative structure-fix attempt only after explicit confirmation, then rerun `structure-gate`.
- Before local directory create/move/delete/rename, follow registry instruction `dirs.manage` in review mode. A blocked result stops by default; force-confirmed work archives prior governance before mutation.
- Except for `__init__.py` and `__main__.py`, functional source and Python test file stems use lowercase English functional words, never start with `_`, contain no digits, and stay within 30 characters. Deterministic checks do not replace the required Agent semantic review evidence.
- Keep exactly one `tests/` at the work-folder root. Root Python is limited to `tests/__init__.py`; place tests one level below by function as `tests/<feature>/*.py`, and never create nested `tests/` directories.
- `remote_deployment.protected_path_classes` and `require_review_for_all_mutations=true` govern remote changes. Every remote `create`, `move`, `delete`, or `rename` must keep both source and target paths inside the governed remote plan, report path classes, keep unverified artifacts in active runs, move verified artifacts to backups, and block destructive protected-path actions by default.
- Do not deploy skill-development content to remote systems unless explicitly authorized; deploy only named runtime artifacts.
- Keep `/.codebase-memory/` ignored and root-only. Ask before removing tracked entries from the Git index; preserve local files.
- Always obtain exactly one explicit user confirmation before installing, replacing, or directly modifying an installed skill, even when the action appears necessary for the current task.

## Docs And Memory

- Before new work, follow the lifecycle commands below; repair an interrupted session before continuing, then start a session after reading the latest handoff.
- Document registration is an optional gate. Enter it only when the user explicitly requests document registration or document-governance migration; otherwise report it as skipped and do not create its governance state.
- For an opted-in skill, use registry instruction `registry.document-governance` to scan, initialize, check, and finalize the document catalog, knowledge pointers, interface mappings, and duplicate adjudications. Markdown remains authoritative; uncertain adjudications require explicit user confirmation.
- Use `docs/memory/` for long-term context. Do not recreate the removed evolution or experience subsystems.
- `memory-compress` creates a bounded retrieval view; the SQLite/JSONL sources remain authoritative.
- At completion, write `docs/handoff/HANDOFF.md`. Archive older handoffs under `history_handoff/HANDOFF-YYYYMMDD-HHMMSS[-N].md`; repair naming drift explicitly.
- Keep install, Git/release, and directory governance under their existing `docs/` owners. Do not duplicate those manuals in AGENTS.md.

## Verify

The skill document keeps only two outer command groups. The first is the managed lifecycle:

```text
python skills/agents-md-generator/scripts/python/docs/manage_docs.py resume-check .
python skills/agents-md-generator/scripts/python/docs/manage_docs.py memory-gate .
python skills/agents-md-generator/scripts/python/docs/manage_docs.py start-session . --input <session.json>
python skills/agents-md-generator/scripts/python/docs/manage_docs.py handoff . --input <handoff.json>
```

The second is the validation chain. Run the smallest relevant checks while editing, then the applicable final chain:

```text
python skills/agents-md-generator/scripts/python/verify/quick_validate.py skills/agents-md-generator
python -m unittest discover -s tests -t . -v
python skills/agents-md-generator/scripts/python/verify/audit_skill.py skills/agents-md-generator
python skills/agents-md-generator/scripts/python/verify/verify_agents.py . --installed-skill-dir skills/agents-md-generator
python skills/agents-md-generator/scripts/python/docs/manage_docs.py verify .
python skills/agents-md-generator/scripts/python/verify/evaluate_skill.py skills/agents-md-generator .
```

For release/merge risk also run `review_governance.py`; changed functional source or Python tests require `--semantic-review <evidence.json>` with matching base/head revisions, changed-path hash, functional summaries, and pass verdicts. For aggregate evidence run `run_confidence_gate.py`; for formal effectiveness run `run_skill_evals.py`. Release packaging, installation, commit, push, and remote mutation require their own explicit scope. Never claim an unrun check passed.

## More Usage

Detailed command syntax, examples, prerequisites, outputs, exit codes, and risk boundaries live in `config/registry/` and its generated SQLite FTS5 index. Ask the local registry instead of expanding this document:

```text
python skills/agents-md-generator/scripts/python/registry/query_registry.py ask "<question>" [--kind <kind>] [--category <name>] [--limit 1..10] [--json]
```

The query is read-only and never executes returned commands. Exit codes are `0` for hits, `1` for no match, `2` for request errors, and `3` for a missing, corrupt, stale, or incompatible index. Rebuild after JSON changes with registry instruction `registry.build`.

## Resources

- `references/script-guide.md`: compact command entry and registry query contract.
- `references/review-checklist.md`: review and verification gates.
- `references/skill-design-coverage.md`: design-pattern and progressive-disclosure map.
- `references/coding-behavior-language-routing.md`: language routing owner.
- `references/script-output-policy.md`: process-output policy.
- `references/evaluation-scenarios.md`: regression scenarios.
- `references/github-skill-release.md`: existing-repository checkout, dist mirror, plan, and remote-publication boundaries.
- `references/public-skill-package.md`: required public files and PNG-only bilingual README contract.
- `assets/templates/`: generated Markdown shapes.
