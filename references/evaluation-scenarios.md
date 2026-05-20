# Evaluation Scenarios

Use these scenarios to forward-test the skill after changes.

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
| Experience quality | AI-authored experience updates read recent handoff evidence plus up to 10 conversation snapshots, reject raw handoff copies or highly homogeneous files, and keep the first four experience files topic-specific |
| Auto evolution | Every tenth completed handoff distills accepted core experience files into indexed guidance under exactly one matching family, either `assets/templates/evolution/skill-template/<category>/<type>/` for skills or `assets/templates/evolution/engineering-template/<category>/<type>/` for engineering projects |
| Extra evolution review | The tenth-handoff request requires extra evolution review metadata, missing `evolution_review` blocks payload apply with `.agents/evolution-review-request.json`, `approve_with_override` blocks until the payload target matches the approved target, and review session evidence must stay exact-cwd only |
| Skill effectiveness evals | `python skills/agents-md-generator/scripts/run_skill_evals.py skills/agents-md-generator/evals/evals.json` reports with-skill versus without-skill deltas, recent high-risk regressions, machine-readable case summaries, all five Skill design patterns, and packaged runtime independence from repository-only tests |
| Governance review gate | `review_governance.py` detects governance-sensitive script, CLI, gate, eval, checklist, and version-release documentation drift; `work-folder-gate` aggregates resume, structure, dir-manager, branch, version, and freshness checks before confidence-sensitive work |
| Design review hard gate | `collect_design_profile.py --write` rejects aligned answers until `extra_requirements` is explicit and a new subagent `design_review` approves the full answers/profile with matching hashes; reject or pending user confirmations force rework and repeat review |
| Missing root routing effectiveness | With-skill detects missing root `AGENTS.md` and emits rebuild-required routing; without-skill baseline lacks that structured trigger behavior |
| Takeover routing effectiveness | With-skill routes version-mismatched landed workspaces into takeover mode; without-skill baseline does not distinguish the compatibility path |
| Root whitelist gate effectiveness | With-skill blocks unexpected root drift and requires structure-fix confirmation; without-skill baseline leaves the repository ungoverned |
| Exact-cwd evolution review effectiveness | With-skill blocks tenth-handoff evolution review payloads that cite non exact-cwd sessions and writes `.agents/evolution-review-request.json`; without-skill baseline would not enforce that evidence boundary |
| Generic audit/evaluate effectiveness | With-skill allows generic target skills to pass core audit checks while still preserving self-skill hardening, and generic evaluate reports machine-readable failure categories instead of only flat error strings |
| Isolated package eval runtime | A copied or installed agents-md-generator release with no parent `tests/` directory can run `scripts/run_skill_evals.py evals/evals.json`; confidence gate also runs this isolated release-package eval when a matching dist release exists |
| Release completeness effectiveness | With-skill install validation rejects releases whose `SKILL.md` references missing formal content such as `config/defaults.json`; without-skill baseline only validates receipt shape and can miss the gap |
| interrupted session | `start-session` creates an active session, `resume-check` detects an unchanged HANDOFF.md after interruption, and `resume-repair` writes a recovery handoff |
| Directory governance | Strong-control generation creates `docs/dir_manager/`; planned local and remote deployment directory changes are governed, unsafe top-level, governance, or project-outside path changes are blocked, remote deployments do not sync local skill-development content by default, and force-confirmed blocked changes archive old dir manager content under `history_dir_manager/<timestamp>/` |
| Release install confirmation | After validation, only skill-development release flows ask about `install_skill.py`; engineering releases do not prompt for skill installation |
| Old workspace takeover | A landed workspace with missing or stale root `AGENTS.md` enters takeover mode, asks only for minimal identity fields, generates a strong-control profile, and then uses forced local directory takeover instead of a full design interview |
| Bad paths | Verification reports missing or suspicious path references |
| Placeholder leak | Verification reports unresolved `{{PLACEHOLDER}}` tokens |
