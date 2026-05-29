# Evaluation Scenarios

Use these scenarios to forward-test the skill after changes.

Coverage mapping rule:
- `skills/agents-md-generator/evals/evals.json` is for with-skill versus without-skill comparisons and other explicit effectiveness proofs.
- `tests/test_agents_md_scripts.py` is for deterministic script, state-machine, path, receipt, and render/verify regressions that do not need an external without-skill baseline.
- manual governance gates are reserved for workspace-specific branch, release-artifact, install, and confidence checks whose truth depends on real repository state.

| Scenario | Expected result |
|----------|-----------------|
| Minimal project | Generates concise AGENTS.md without inventing commands or frameworks |
| TypeScript package | Detects package manager, scripts, test runner, and package.json source |
| Python project | Detects pyproject.toml, ruff/mypy/pytest where configured |
| Go project | Detects go.mod and suggests gofmt, go test, go build |
| PHP project | Detects composer scripts and framework hints |
| Hybrid project | Keeps root thin and avoids mixing frontend/backend commands |
| Existing AGENTS.md | Preserves hand-written content outside generated markers |
| AGENTS.md compression | Root generated `AGENTS.md` stays within 16KB, scoped AGENTS files are not blocked by the old line rule, and over-limit root manual content blocks writes |
| Outdated AGENTS.md | Reports freshness risk from git history |
| Scoped directories | Creates scoped files only for distinct local rules |
| Cross-agent shims | Creates CLAUDE.md/GEMINI.md without overwriting existing non-managed files |
| Docs governance | Strong-control generation creates `docs/handoff/HANDOFF.md`, archives old handoffs under `history_handoff`, keeps 10 numbered experience files, creates AI experience update requests every five handoffs, applies accepted AI payloads with archives under `history_experience`, and records development stages |
| Handoff naming gate | Renaming `docs/handoff/HANDOFF.md` or introducing non-standard history archive names causes `scaffold`, `verify`, work-folder/release gates, and confidence-sensitive flows to fail until `repair-handoff-names --write` repairs the governed names |
| Workspace settings gate | Strong-control generation documents `.settings/project.local.json` and `.settings/project.remote.json`, structure governance rejects workspace config json outside `.settings/`, and remote review blocks all `.settings/*.local.json` such as `.settings/server_list.local.json` |
| Experience quality | AI-authored experience updates read recent handoff evidence plus up to 10 conversation snapshots, reject raw handoff copies or highly homogeneous files, and keep the first four experience files topic-specific |
| Auto evolution | Every-tenth-handoff evolution stays atomic for both owner repositories and ordinary governed workspaces; ordinary workspaces must target `installed-sink` or `export-pending`, and must not keep active local reusable template folders after cleanup |
| Evolution import fallback | A workspace without a writable installed skill writes `.agents/evolution-export/<timestamp>/` and `.agents/evolution-import-request.json`, and `manage_docs.py import-evolution` later publishes that bundle into the installed skill template library |
| Extra evolution review | The tenth-handoff request requires extra evolution review metadata, missing `evolution_review` blocks payload apply with `.agents/evolution-review-request.json`, `approve_with_override` blocks until the payload target matches the approved target, and review session evidence must stay exact-cwd only |
| Legacy local evolution cleanup | If an ordinary user work folder already contains mistaken local `assets/templates/evolution/` output, governance commands archive it under dir-manager history and remove it from the active workspace before continuing sink-based evolution |
| Skill effectiveness evals | `python tests/run_skill_evals.py skills/agents-md-generator/evals/evals.json` reports with-skill versus without-skill deltas, recent high-risk regressions, machine-readable case summaries, all five Skill design patterns, and tests-only eval-helper boundaries |
| Code comment policy contract | `code_comment_policy_contract` proves generated root AGENTS.md includes `## Code Comment Policy`, writes configurable `code_comment_policy`, states `禁止未经明确要求的批量 AI 注释`, and makes `verify_agents.py` reject managed roots that lose the section or 弱化策略 |
| Plan Mode language lock contract | `plan_mode_language_lock_contract` proves the default-language rule also covers Plan Mode `<proposed_plan>` body text, and `verify_agents.py` rejects managed roots that keep only the generic reply-language rule without the Plan Mode lock |
| Version semantics split | When installed `agents-md-generator` version and target project skill `VERSION` differ, `sync-root-agents` still reports clean root metadata if metadata matches the generator version, while `version_alignment_gate` and `verify_agents.py` still enforce the project version only on Control Profile and release-doc records |
| Governance review gate | `review_governance.py` detects governance-sensitive script, CLI, gate, eval, checklist, and version-release documentation drift; non-release modes emit `review_dispatch_policy=optional|none`, `--mode release` emits `required_for_release`, and `work-folder-gate` aggregates resume, structure, dir-manager, branch, version, and freshness checks before confidence-sensitive work |
| Governance runtime de-vendoring | External workspaces render governance commands through the installed `agents-md-generator` runtime such as `python <codex-home>/skills/agents-md-generator/scripts/manage_docs.py ...`, and `verify_agents.py` rejects project-local commands like `python scripts/manage_docs.py ...` or `python skills/<project-skill>/scripts/manage_docs.py ...` |
| Design review hard gate | `collect_design_profile.py --write` rejects aligned answers until `extra_requirements` is explicit and a new subagent `design_review` approves the full answers/profile with matching hashes; `--intent read_only` must stop at `completed_read_only` without a reviewer, and `--enter-write-review` is required before that same interview can enter subagent review |
| Missing root routing effectiveness | With-skill detects missing root `AGENTS.md` and emits rebuild-required routing; without-skill baseline lacks that structured trigger behavior |
| Takeover routing effectiveness | With-skill routes version-mismatched landed workspaces into takeover mode; without-skill baseline does not distinguish the compatibility path |
| Root whitelist gate effectiveness | With-skill blocks unexpected root drift and requires structure-fix confirmation; without-skill baseline leaves the repository ungoverned |
| Root workspace artifact gate | With-skill allows root `tests/`, `smoke*`, `reports/`, and `runs/`, but blocks the same directories when nested under `skills/<skill-name>/...` or `engineering/<project-name>/...`; without-skill baseline does not enforce that boundary |
| Exact-cwd evolution review effectiveness | With-skill blocks tenth-handoff evolution review payloads that cite non exact-cwd sessions and writes `.agents/evolution-review-request.json`; without-skill baseline would not enforce that evidence boundary |
| Generic audit/evaluate effectiveness | With-skill allows generic target skills to pass core audit checks while still preserving self-skill hardening, and generic evaluate reports machine-readable failure categories instead of only flat error strings |
| Source governance test boundary | `source_governance_test_boundary` proves eval helpers moved to `tests/`, production script paths no longer keep `run_skill_evals.py` or `eval_fixtures.py`, and source-governance gates block regressions |
| Release completeness effectiveness | With-skill install validation rejects releases whose `SKILL.md` references missing formal content such as `config/defaults.json`; without-skill baseline only validates receipt shape and can miss the gap |
| Install merge effectiveness | Replacing an installed skill merges reusable template sections and index provenance when both versions are parseable; fallback conflict copies appear only for non-parseable files and are reported in the install result |
| interrupted session | `start-session` creates an active session, `resume-check` detects an unchanged HANDOFF.md after interruption, and `resume-repair` writes a recovery handoff |
| Directory governance | Strong-control generation creates `docs/dir_manager/`; planned local and remote deployment directory changes are governed, unsafe top-level, governance, or project-outside path changes are blocked, remote deployments do not sync local skill-development content by default, and force-confirmed blocked changes archive old dir manager content under `history_dir_manager/<timestamp>/` |
| Release install confirmation | After validation, only skill-development release flows ask about `install_skill.py`; engineering releases do not prompt for skill installation |
| Release content policy | `package-release`, `release-gate`, and `install_skill.py` allow governed skill-local `evals/` in installable dist releases, reject `tests/`, `test/`, `smoke*`, `_smoke_runs/`, `reports/`, `runs/`, and cache artifacts, and record machine-readable `release_content_policy` evidence in receipts |
| Old workspace takeover | A landed workspace with missing or stale root `AGENTS.md` enters takeover mode, asks only for minimal identity fields, generates a strong-control profile, and then uses forced local directory takeover instead of a full design interview |
| Bad paths | Verification reports missing or suspicious path references |
| Placeholder leak | Verification reports unresolved `{{PLACEHOLDER}}` tokens |
