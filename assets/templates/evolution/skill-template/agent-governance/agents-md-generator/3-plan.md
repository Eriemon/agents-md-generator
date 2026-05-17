# Plan Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 3-plan.md
- Version window: current-plus-latest-history
- Target source: ai
- Rationale: Inferred from project control profile, repository facts, and topic keywords.

## Source Versions
- `docs/experience/3-plan.md`
- `docs/experience/history_experience/20260516-225309/3-plan.md`

## Evidence Sources
- Current and latest historical `3-plan.md` records.
- Handoff window 36-40, especially the routing-fix implementation plan and the release/install planning notes.
- Verification ordering captured by the recent command evidence.

## Applicable Scenario
- Use when a future task needs a reusable planning pattern for agent-governance work in this repository.
- This template is most useful when behavior, tests, docs, and governance state must all align before the task is done.

## Distilled Workflow
- Start by turning the user-visible behavior into a small acceptance matrix.
- Map each requirement to the owning script, prompt, test, and verification layer.
- Execute in an order that reduces ambiguity: routing logic first, regression expectations second, docs and prompts third, full validation fourth, governance closure last.
- Keep handoff and cadence work inside the plan when the repository contract says they are completion gates.

## Key Decisions
- Plan around ownership boundaries rather than around files alone.
- Separate focused fixes from release/install work, but preserve the relationship between them.
- Treat docs governance and evolution cadence as planned deliverables, not optional cleanup.

## Common Problems
- Plans that skip the acceptance matrix let code, tests, and prompt text interpret the same requirement differently.
- Plans that ignore docs cadence produce a technically fixed repository that still fails governance checks.
- Plans that change too many layers at once make validation failures hard to localize.

## Non-Reusable Content
- Omit turn-specific wording and temporary timestamps.
- Do not include FPGA, HLS, or other hardware execution plans that do not belong to this skill-governance repository.

## Application Checklist
- Write the behavior matrix first.
- Map ownership across scripts, tests, docs, and gates.
- Sequence focused verification before full validation.
- Include governance closure in the definition of done.
