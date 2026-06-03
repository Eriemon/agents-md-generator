# Contributing

Thank you for improving AGENTS.md Generator. This repository is an agent skill first: changes should help an AI coding agent create, review, and verify coding-agent instruction files more reliably.

## Contribution Principles

- Keep `SKILL.md` concise and operational.
- Move detailed background, command behavior, review policy, and long examples into `references/`.
- Keep deterministic repository inspection, rendering, verification, audit, and shim logic in `scripts/`.
- Do not claim a command is verified unless it was actually run.
- Preserve hand-written content outside managed generated blocks.
- Keep generated outputs, temporary profiles, local credentials, and machine-specific paths out of commits.

## Suggested Workflow

1. Open an issue describing the agent behavior, stale-doc problem, verification gap, or documentation improvement.
2. Make a focused change with a clear before/after behavior.
3. Run the relevant static validation and skill audit.
4. Include command output or validation evidence in the pull request.

## Validation

Useful local commands:

```powershell
python scripts/inspect_project.py .
python scripts/detect_scopes.py .
python scripts/render_agents.py .
python scripts/verify_agents.py .
python scripts/audit_skill.py .
```

For script changes, also run a Python syntax check over `scripts/*.py`.

## Documentation Expectations

- Keep the default `README.md` in English.
- Put Chinese user-facing documentation in `README-CN.md`.
- Keep examples short, reproducible, and aligned with the skill's AGENTS.md-only scope.
