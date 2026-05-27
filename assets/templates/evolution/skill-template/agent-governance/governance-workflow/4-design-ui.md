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
- Source handoff window: 66-70

## Source Versions
- `docs/experience/4-design-ui.md`
- `docs/experience/history_experience/20260524-172127/4-design-ui.md`

## Evidence Sources
- Latest and previous design-ui experience entries plus gate messages and install/review decision outputs surfaced to the user.

## Applicable Scenario
- Use when a governance-heavy skill has no graphical UI but still exposes important textual interaction surfaces such as block reasons, install prompts, and repair flows.

## Distilled Workflow
- Record explicitly when no visual UI changed so this topic stays honest and does not absorb unrelated implementation notes.
- For text-only interaction surfaces, keep blocking reasons and repair guidance direct enough that users can tell whether the failure is source behavior, release parity, install migration, or freshness drift.
- Preserve explicit non-silent behavior for governance errors instead of masking them with auto-heal flows.

## Key Decisions
- Treat user-facing gate wording as part of the skill interface even without a GUI.
- Prefer explicit block messaging over silent repair when the issue affects governance truth or safety.

## Common Problems
- Reusing this topic for non-UI script details makes the experience set less trustworthy.
- Text-only skills can still regress their interaction surface when prompts or block messages become ambiguous.

## Non-Reusable Content
- Omit temporary screenshots, local paths, and one-conversation wording that does not represent a stable interaction rule.

## Application Checklist
- State whether any real UI changed.
- If not, capture only the genuine interaction-surface lesson.
- Keep block and repair messages explicit for governance-sensitive behavior.
