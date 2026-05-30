# Design UI Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: governance-workflow
- Source file: 4-design-ui.md
- Version window: current-plus-latest-history
- Target source: ai
- Rationale: Inferred from project control profile, repository facts, and topic keywords.
- Source workspace: current governed workspace (local path intentionally omitted)
- Source project: agents-md-generator
- Source handoff window: 76-80

## Source Versions
- `docs/experience/4-design-ui.md`
- `docs/experience/history_experience/20260527-171409/4-design-ui.md`

## Evidence Sources
- Current and previous design-ui experience files, generated command hints, prompt wording, and verifier/review messages.

## Applicable Scenario
- Use when a repository has no GUI but its safety and workflow are conveyed through text-only generated guidance and gate output.

## Distilled Workflow
- Review generated commands, prompts, and warnings as interface affordances.
- Separate owner, external, and release/install audiences in the text contract.
- Prefer short explicit warnings that name the forbidden behavior directly.

## Key Decisions
- Text-only command hints are still UI and can cause unsafe behavior if they imply the wrong ownership boundary.
- Audience-specific command guidance is safer than one mixed generic example.

## Common Problems
- Implicit recommendations in examples cause users to trust the wrong path.
- Prompt, doc, and verifier wording drift leads maintainers to follow whichever string is easiest rather than correct.

## Non-Reusable Content
- Exclude local shell aliases, personal terminal habits, and one-off wording that is not part of the durable contract.

## Application Checklist
- Confirm the text guidance identifies the intended audience and the safe command path.
- Confirm at least one regression protects the user-visible wording.
