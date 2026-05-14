# Workflow Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 1-workflow.md
- Version window: current-plus-latest-history
- Target source: inferred
- Rationale: Inferred from project control profile, repository facts, and topic keywords.

## Source Versions
- `docs/experience/1-workflow.md`
- `docs/experience/history_experience/20260514-134203/1-workflow.md`

# Workflow Evolution Template

## Evidence Sources
- Current and latest historical experience versions for this topic.

## Applicable Scenario
- Use when a future governance workflow task matches the same repository governance constraints and needs reusable guidance rather than a copied experience note.

## Distilled Workflow
- Inspect repository facts and the control profile, align AGENTS rules and docs governance behavior, update scripts, run focused tests, verify the repository, and make the release/install decision only after validation passes.

## Key Decisions
- Keep deterministic scripts responsible for validation and file movement; keep AI-authored payloads responsible for synthesis and judgment.
- Use release and installation decisions as the final governance checkpoint instead of treating them as unrelated afterthoughts.

## Common Problems
- Raw handoff copies, duplicated template-family text, and stale docs governance state can make a skill workflow look complete when it is not.

## Non-Reusable Content
- Omit release timestamps, temporary file paths, and conversation-only details that do not change future implementation choices.

## Application Checklist
- Confirm repository facts and control profile were inspected.
- Confirm scripts, tests, verify, docs governance, release, and install decisions all align with the target repository.
