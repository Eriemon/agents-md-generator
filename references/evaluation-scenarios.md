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
| AGENTS.md compression | Root generated `AGENTS.md` stays within 12KB, scoped AGENTS files are not blocked by the old line rule, and over-limit root manual content blocks writes |
| Outdated AGENTS.md | Reports freshness risk from git history |
| Scoped directories | Creates scoped files only for distinct local rules |
| Cross-agent shims | Creates CLAUDE.md/GEMINI.md without overwriting existing non-managed files |
| Docs governance | Strong-control generation creates `docs/handoff/HANDOFF.md`, archives old handoffs under `history_handoff`, keeps 10 numbered experience files, creates AI experience update requests every five handoffs, applies accepted AI payloads with archives under `history_experience`, and records development stages |
| Experience quality | AI-authored experience updates read recent handoff evidence plus up to 10 conversation snapshots, reject raw handoff copies or highly homogeneous files, and keep the first four experience files topic-specific |
| Auto evolution | Every tenth completed handoff distills accepted core experience files into indexed guidance under exactly one matching family, either `assets/templates/evolution/skill-template/<category>/<type>/` for skills or `assets/templates/evolution/engineering-template/<category>/<type>/` for engineering projects |
| interrupted session | `start-session` creates an active session, `resume-check` detects an unchanged HANDOFF.md after interruption, and `resume-repair` writes a recovery handoff |
| Directory governance | Strong-control generation creates `docs/dir_manager/`; planned local and remote deployment directory changes are governed, unsafe top-level, governance, or project-outside path changes are blocked, remote deployments do not sync local skill-development content by default, and force-confirmed blocked changes archive old dir manager content under `history_dir_manager/<timestamp>/` |
| Release install confirmation | After validation, `install_skill.py` defaults to skip and installs only when Codex or custom target plus `--write` are explicit |
| Bad paths | Verification reports missing or suspicious path references |
| Placeholder leak | Verification reports unresolved `{{PLACEHOLDER}}` tokens |
