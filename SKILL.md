---
name: agents-md-generator
description: Use when creating, updating, compressing, reviewing, or verifying AGENTS.md and other AI coding-agent rules; when a managed root AGENTS.md is missing, malformed, stale, or version-incompatible; when the user explicitly mentions AGENTS.md, agent rules, or scoped AGENTS.md; when a managed skill README needs a functional illustration set; or when a request about the current workspace, repository, or work folder is a planning request and therefore requires a root AGENTS.md check first.
---

# AGENTS.md Generator

Generate operational agent rules from repository facts and confirmed policy. Keep roots short, place local rules near scope, preserve human text, and verify writes.

## Route

- Explicit AGENTS creation, update, compression, review, or repair enters the full workflow even when the root is healthy.
- A current-workspace planning request first checks root and global AGENTS state. If the managed root is healthy, report that result and return to the user's task; otherwise report the exact defect and continue to design or takeover.
- Use `read_only` for explanation/planning/state checks/review; `design` for policy collection; `write` for approved changes; `governance_high_risk` for release/merge. None authorizes a non-testing subagent; only a current-task proactive explicit user request naming the role/purpose does.
- If the user explicitly asks for Codex Token usage statistics, use registry instruction `detect.token-usage-review`; do not enter the AGENTS design interview. Use it only when the configured agent sessions directory exists, and keep any sessions-root override inside that active sessions tree.
- External work folders call the installed skill runtime. Only this owner repository uses repo-local `python skills/agents-md-generator/scripts/python/...` paths.
- If no registered task route matches the requested task, stop unmatched tasks until agents.md/profile is updated; then update the current work folder AGENTS.md/profile before continuing.
- When skill development must link a code-hosting repository, use the configured existing-checkout contract: complete versioned release and installation first, then mirror, plan, and review only the local checkout; tools do not create remote repositories or push.

## Inspect

1. Read applicable AGENTS files, the latest handoff, memory, and repository governance.
2. Use registry instructions `detect.inspect-project` and `detect.detect-scopes`.
3. Resolve the selected platform from `config/agent.json`, then check its configured global instruction file for the managed baseline and version. For Codex, that file is `$CODEX_HOME/AGENTS.md`; verify it before relying on user-level rules.
4. Treat missing metadata as a full-design trigger. Use takeover only for a version-mismatched old workspace with landed content.
5. For strong-control work, pass `memory-gate`; bootstrap exact-cwd Codex sessions when required.
6. When codebase-memory MCP is enabled, require a ready `full` persistent index, successful architecture analysis, root-only artifacts, and matching live/disk counts before writes.

The configured global file supplies the active baseline: scope, managed entry, reuse, rating, plans, opt-in subagents, one TESTER for `tests/**`, dual language preflight, docs, safety, install protection, and formulas. Local governance owns thresholds, layouts, exceptions, long tasks, and releases; roots inherit `Coding Behavior Baseline`. Review contradictions before `<proposed_plan>`; ask only when scope, security, cost, or external behavior changes.

## Design

Use registry instruction `design.collect-profile`, resume unfinished state, and submit one returned group at a time.

- Ask every returned question and show its options. Do not infer mandatory answers; use the configured question identifiers and option sets.
- The configured `default_conversation_language` governs all natural-language replies, including Plan Mode `<proposed_plan>` content, unless the user switches languages.
- Skill and Engineering development groups come from the selected profile; never copy a current question list into source or comments.
- After each group, show `review_summary` and `confirmed_so_far`, then obtain confirmation. Record `extra_requirements`, including explicit `none`, and require final alignment.
- Read-only intent ends with `answers_snapshot` and `profile_preview`; it creates no design review. Write intent also defaults to no review subagent. Enter `design_review` only after the user explicitly requests a review subagent and the hashes, findings, and confirmations validate; record `reviewer_type="subagent"` only for that authorized review.
- `--answers ... --write` rejects missing mandatory answers, alignment, extra requirements, or directory policy. When explicit review evidence is supplied, validate it rather than making it a default prerequisite.
- Approved design reviews must bind `reviewed_answers_hash` and `reviewed_profile_hash` to the current answers and profile before write.
- If remote servers are enabled, require configured `erie-remote-ssh`, explicit routes, checked primary/fallback servers, and workspace checks; resolve and fail closed at runtime.
- Detect an installed skill from its directory and root `SKILL.md`; keep CLI and settings discovery separate, and retain the runtime entry with a compatibility fallback.
- Remote structure governance is separate from remote-server enablement and task-route mapping. Validate relative conda/runtime/archive templates and reject traversal, wildcards, unsafe shell characters, empty values, and repeated separators.
- If codebase-memory MCP is requested but unavailable, provide manual installation guidance, never download or execute the installer automatically, and require restart before resuming.
- The design interview's `use_codebase_memory_mcp` (55) choice controls the official MCP gate; enabled writes require a ready full persistent root-only index, while missing dependencies require manual installation guidance and restart.

## Generate

1. Run structure, branch, directory, memory, and codebase-memory gates required by the profile.
2. Use registry instruction `render.render-agents`; preview first and write only after approval.
3. Preserve text outside `AGENTS-GENERATED` blocks. Templates define root and scoped shape; do not absorb legacy evolution templates.
4. Keep the root an operational index. Put detailed remote registries in `.agents/agents-control.json`, directory policy in `docs/dir_manager/planned_structure.json`, and configurable coding/output rules in `.agents/global-rule-overrides.json`.
5. Create scoped AGENTS only for verified local differences. Do not restate inherited root rules.
6. Keep `.settings/` as work-folder configuration; allow remote `.settings/*.remote.json` and never copy `.settings/*.local.json`, including `.settings/server_list.local.json`, to remote systems.

For a confirmed platform, read `config/agent.json` and its catalog before writing; render the configured instruction files and create only the selected state directory. Generate the configured native metadata; installation keeps the selected profile and resolved configuration/docs. Non-default migration requires the configured migration options and confirmation; retire only a managed prior-selection marker.

### README illustration contract

When a user asks this skill to update a skill README, reuse suitable existing visuals first. Create new artwork only when the user explicitly requests new visuals or the repository has no suitable asset; treat that request as a functional design deliverable, not as a decorative image task:

1. Write a visual brief from the skill's real inputs, decisions, outputs, gates, and boundaries before generating anything.
2. If new artwork is explicitly requested, use Image2/ImageGen to generate original raster artwork. SVG is forbidden as a README illustration; Mermaid is also forbidden in the public image assets.
3. Make the main image a horizontal 16:9 overview that is legible in a repository README. Add style-consistent detail images for each major capability instead of repeating or cropping the hero.
4. Use panels, tables, relationship maps, code fragments, state cards, or formulas only when they clarify the function. Avoid generic stock imagery, empty neon decoration, and a linear checklist with no functional information.
5. Provide matching English and Chinese PNGs when the skill has bilingual READMEs, keep them local under `assets/readme/`, and reference every image from the README that explains it.
6. Validate PNG signatures, dimensions, local paths, and absence of SVG/remote metadata before copying new images into the source package or `dist/`. Existing illustrations must not be redrawn merely to refresh README copy.

Source README is authoritative; versioned `dist/` and existing `github/` checkouts consume it and never become alternate sources. Illustrations stay local PNGs; the header may retain shields.io metadata links.

Roots render `shared`, `python`, `script` routes once: Python uses `readable-python-generator`; bat/cmd, shell/bash, PowerShell, Tcl, Node-only JavaScript (`.js`/`.mjs`), and static Dockerfile use `readable-script-generator`; wrappers remain script targets; browser JavaScript and Docker daemon/build stay out. Preserve separation; reject one-line/obfuscated code; load output policy from config.

## Safety

- Do not invent commands, paths, owners, frameworks, CI rules, security policies, or coverage targets.
- Keep every proposed solution and plan inside the frozen user goal. Include only requested behavior, minimal integration, and current mandatory gates; mark every speculative feature, refactor, abstraction, compatibility layer, optimization, or configuration as out of scope unless the user explicitly reopens the boundary.
- Formal plans must be detailed enough to execute without additional design questions: name exact steps, inputs, outputs, files or interfaces, preconditions, failure handling, checks, and stop conditions. Use prose, tables, Mermaid, or a combination only where each form improves comprehension.
- Do not dispatch non-testing subagents by default. Only a proactive current-task request naming the role/purpose authorizes one; generic multi-agent, complexity, rating, risk, or judgment requests do not. If count is omitted, use exactly three; an explicit count overrides it and authorization never carries into another task.
- Canonical workers are narrow governance roles, not arbitrary subagents; automatic authorization requires Codex-native support, a managed root, explicit `enabled` state, and a matching event. Missing state is `unconfigured` and blocks; session state cannot authorize.
- Test ownership follows project authorization: when tester is disabled, the main Agent owns `tests/**`; when tester is explicitly enabled, use exactly one isolated `fork_turns=none` TESTER. Pure read-only or planning work and documentation-only changes without a test surface do not require test ownership.
- Only that TESTER may inspect, change, or run `tests/**`; gardener may read/list it for design evidence but never edits/deletes/runs tests. For RED/BLOCKED/SCOPE_REJECTED, TESTER must return `failure_report` with `failure_stage`, `failure_kind`, `first_error`, `failure_summary`, `failure_count`, `failure_tests`, `expected_actual`, `root_cause_class`, `minimal_fix`, `evidence`, `residual_jobs`, and `modification_status`; each failure item needs `test_id`, `expected`, `actual`, `observed`, and `source`. A bare count is invalid. Main changes product; tester revalidates. Use authoritative evidence and stop on provenance conflict.
- New test files use functional or behavioral semantic names; filename stems must not contain version, case, or sequence literals. Do not bulk-rename existing tests.
- Every managed root renders one `Workspace boundary` rule. Bound work-folder/codebase-memory refreshes need no extra confirmation; remote changes require the exact route. Reads are allowed, but other external writes require exact target disclosure, risk/recovery disclosure, and exactly one user confirmation; target/scope changes invalidate it.
- Canonical tester/reviewer/gardener roles are available only when `config/agent.json` resolves a catalog profile with the configured native-worker capability; profile/tool paths come from its configured user-home directory. They preserve refresh backups and retain `tests/**` ownership and reviewer checkpoints. Other platforms do not claim these roles.
- Gardener reports use `schema_version=1` with fixed findings/rejection/uncertainty/verdict fields. AST zero-call `function_candidates` are never deletion conclusions; corroborate graph, exports, dynamic references, tests, and Markdown before a user decision. Markdown edits or public/dynamic/test-dependent deletions require confirmation.
- A single-task authorization receipt is confirmed once across the skill, AGENTS.md, and CLI; reuse it for the same target and scope, and re-confirm only when the target, scope, or material risk changes.
- Generated roots always include a state-aware, fail-closed remote work-folder contract: resolve the exact configured route and verified workspace, and keep deployment, conda/runtime, backup, and archive lifecycle details in `docs/dir_manager/planned_structure.json`.
- Remote upload is manifest-only: never upload the whole work folder or a bundle; `.git/`, `git/`, `github/`, `dist/`, and `ref/` are forbidden, and selected directories must be expanded and hashed. New tests use `tests/<feature>/test_<behavior>.<ext>`.
- `allowed_root_files` governs root-level exceptions. Root-level files outside the governed primary project root require review; allow the conservative structure-fix attempt only after explicit confirmation, then rerun `structure-gate`.
- Before local directory create/move/delete/rename, follow registry instruction `dirs.manage` in review mode. A blocked result stops by default; force-confirmed work archives prior governance before mutation.
- Except for `__init__.py` and `__main__.py`, functional source and Python test file stems use lowercase English functional words, never start with `_`, contain no digits, and stay within 30 characters. Deterministic checks do not replace the required Agent semantic review evidence.
- Keep exactly one `tests/` at the work-folder root. Root Python is limited to `tests/__init__.py`; place tests one level below by function as `tests/<feature>/*.py`, and never create nested `tests/` directories.
- `remote_deployment.protected_path_classes` and `require_review_for_all_mutations=true` govern remote changes; every remote `create`, `move`, `delete`, or `rename` must keep both source and target paths inside the governed remote plan, report path classes, and block protected destructive actions by default.
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

The skill document keeps two outer command groups. The first is the managed lifecycle:

```text
python skills/agents-md-generator/scripts/python/docs/manage_docs.py resume-check .
python skills/agents-md-generator/scripts/python/docs/manage_docs.py memory-gate .
python skills/agents-md-generator/scripts/python/docs/manage_docs.py start-session . --input <session.json>
python skills/agents-md-generator/scripts/python/docs/manage_docs.py handoff . --input <handoff.json>
```

The second is the validation chain. Run the smallest relevant checks while editing, then the applicable final chain:

```text
python skills/agents-md-generator/scripts/python/verify/quick_validate.py skills/agents-md-generator
python -m pytest -q
python -m unittest discover -s tests -t . -v
python skills/agents-md-generator/scripts/python/verify/audit_skill.py skills/agents-md-generator
python skills/agents-md-generator/scripts/python/verify/verify_agents.py . --installed-skill-dir skills/agents-md-generator
python skills/agents-md-generator/scripts/python/docs/manage_docs.py verify .
python skills/agents-md-generator/scripts/python/verify/evaluate_skill.py skills/agents-md-generator .
```

Canonical worker coordination uses `workers/manage_workers.py dispatch-start`,
`dispatch-check`, and `dispatch-record`; these commands emit one JSON object and
never call `spawn_agent` themselves. `worker_dispatch.py` is the single source
for event IDs, session state, target reuse, task envelopes, and fail-closed
`unconfigured` handling.

Release/install require one complete schema-2 pytest receipt: `runner=pytest`, `suite=full`, selector-free `python -m pytest -q`, counts, current tests/source SHA-256, test commit, and self-hash. Location never changes acceptance; schema-1/non-pytest receipts are history only. The gate also checks AGENTS freshness, manifest/cache exclusions, versioned dist parity, and `install_skill.py --target skip`.

For release/merge risk run `review_governance.py`; changed functional source or Python tests require `--semantic-review <evidence.json>` with matching base/head, changed-path hash, summaries, and pass verdicts. For aggregate evidence run `run_confidence_gate.py`; for formal effectiveness run `run_skill_evals.py`. Release packaging, installation, commit, push, and remote mutation require explicit scope; never claim an unrun check passed.

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
