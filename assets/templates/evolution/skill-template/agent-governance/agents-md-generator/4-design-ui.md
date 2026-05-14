# Design UI Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 4-design-ui.md
- Version window: current-plus-latest-history
- Target source: inferred
- Rationale: Inferred from project control profile, repository facts, and topic keywords.

## Source Versions
- `docs/experience/4-design-ui.md`
- `docs/experience/history_experience/20260514-134203/4-design-ui.md`

# Design UI Evolution Template

## Evidence Sources
- Current and latest historical experience versions for this topic.

## Applicable Scenario
- Use when a future design ui task matches the same repository governance constraints and needs reusable guidance rather than a copied experience note.

## Distilled Workflow
- Inspect evidence, identify the concrete design ui failure, write a regression check, implement narrowly, verify targeted behavior, and update governance evidence only after the check passes.

## Key Decisions
- Keep deterministic scripts responsible for validation and file movement; keep AI-authored payloads responsible for synthesis and judgment.

## Common Problems
- Do not paste raw handoff content, do not duplicate the same text across template families, and do not mix skill-specific guidance into engineering templates.

## Non-Reusable Content
- Omit release timestamps, temporary file paths, and conversation-only details that do not change future implementation choices.

## Application Checklist
- Confirm the template family and category match the target repository.
- Confirm the experience source passed quality validation.
- Confirm the resulting guidance is a synthesis, not a copy.
