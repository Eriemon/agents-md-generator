# Plan Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 3-plan.md
- Version window: current-plus-latest-history
- Target source: inferred
- Rationale: Inferred from project control profile, repository facts, and topic keywords.

## Source Versions
- `docs/experience/3-plan.md`
- `docs/experience/history_experience/20260516-152408/3-plan.md`

## Evidence Sources
- Current and latest historical experience versions for this topic.

## Applicable Scenario
- Use when a future plan task matches the same repository governance constraints and needs reusable guidance rather than a copied experience note.

## Distilled Workflow
- Inspect current evidence, identify the concrete plan failure or requirement, update the smallest responsible script/template/config surface, run the narrow regression for that topic, then rerun repository verification before handoff.

## Key Decisions
- Keep deterministic scripts responsible for validation and file movement; keep AI-authored payloads responsible for synthesis and judgment.
- Preserve the global-principles versus local-config split when recording reusable guidance.

## Common Problems
- Do not paste raw handoff content, do not duplicate the same text across template families, and do not move repository-private detail back into AGENTS prose.

## Non-Reusable Content
- Omit release timestamps, temporary file paths, and conversation-only detail that does not change future implementation choices.

## Application Checklist
- Confirm the template family and category match the target repository.
- Confirm the source experience passed quality validation.
- Confirm the resulting guidance is a synthesis, not a copy.
