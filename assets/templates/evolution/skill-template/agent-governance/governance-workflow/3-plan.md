# Plan Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: governance-workflow
- Source file: 3-plan.md
- Version window: current-plus-latest-history
- Target source: ai
- Rationale: Inferred from project control profile, repository facts, and topic keywords.
- Source workspace: current governed workspace (local path intentionally omitted)
- Source project: agents-md-generator
- Source handoff window: 76-80

## Source Versions
- `docs/experience/3-plan.md`
- `docs/experience/history_experience/20260527-171409/3-plan.md`

## Evidence Sources
- Current and previous planning experience files, latest handoffs, and the validation chain that closed the task.

## Applicable Scenario
- Use when a governance fix spans implementation, release, install, and docs cadence rather than a single source patch.

## Distilled Workflow
- Plan around proof stages: boundary decision, red test, narrow fix, doc/spec sync, release artifact, install evidence, docs cadence, freshness.
- Re-plan when inspection changes the root-cause diagnosis.
- Reserve a final repository-closure stage whenever the user asks for factual or 100% confidence.

## Key Decisions
- Lock non-negotiable runtime-boundary assumptions early.
- Treat release/install/docs cadence as part of implementation scope when they are contractual blockers.

## Common Problems
- Planning only around files can hide proof-stage failures.
- Calling the task done at tests passed leaves repository closure incomplete.

## Non-Reusable Content
- Omit incidental command timings, ad hoc shell history, and conversation-only wording.

## Application Checklist
- Confirm the plan names the final closure gates before work begins.
- Confirm cadence checkpoints are considered if the handoff count is near a boundary.
