# Scripts Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 2-scripts.md
- Version window: current-plus-latest-history
- Target source: inferred
- Rationale: Inferred from AGENTS.md generator scripts and docs governance automation.

## Source Versions
- `docs/experience/2-scripts.md`
- `docs/experience/history_experience/20260512-165633/2-scripts.md`

## Evidence Sources
- Current scripts experience, latest historical scripts experience, and `manage_docs.py` behavior for request/payload/evolve flows.

## Applicable Scenario
- Use when changing deterministic governance scripts that collect evidence, validate payloads, move generated assets, or expose CLI JSON state.

## Distilled Workflow
- Keep scripts responsible for facts, validation, state transitions, and file movement.
- Keep AI-authored payloads responsible for judgment, synthesis, and project-specific learning.
- Validate target families, safe path segments, required markdown sections, and no-copy constraints before writing durable artifacts.
- Return structured JSON errors for invalid payloads so the next agent can repair them without guessing.

## Key Decisions
- Store only JSON-safe values in `.agents/docs-governance-state.json`.
- Treat missing `evolution_summary` as a skipped evolution plus request file.
- Archive only files named by the prior `evolution-index.json` to avoid deleting hand-maintained templates.

## Common Problems
- Letting a script write plausible prose turns automation into fabricated memory.
- Broad directory cleanup can delete user-maintained templates.
- Validators that stop at the first error slow down payload repair.

## Non-Reusable Content
- Do not preserve temporary payload paths, local absolute paths, or old release-version strings.
- Do not encode one repository's category as the default for all projects.

## Application Checklist
- Add a failing regression test before changing script behavior.
- Verify invalid payloads fail with actionable JSON errors.
- Verify accepted payloads update state and artifacts in the intended family only.
