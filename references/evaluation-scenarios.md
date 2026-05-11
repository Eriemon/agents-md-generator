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
| Outdated AGENTS.md | Reports freshness risk from git history |
| Scoped directories | Creates scoped files only for distinct local rules |
| Cross-agent shims | Creates CLAUDE.md/GEMINI.md without overwriting existing non-managed files |
| Docs governance | Strong-control generation creates `docs/handoff/HANDOFF.md`, archives old handoffs under `history_handoff`, writes experience summaries, archives old lessons under `history_experience`, and records development stages |
| Bad paths | Verification reports missing or suspicious path references |
| Placeholder leak | Verification reports unresolved `{{PLACEHOLDER}}` tokens |
