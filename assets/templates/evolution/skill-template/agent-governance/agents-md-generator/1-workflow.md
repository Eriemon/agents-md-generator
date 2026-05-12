# Workflow Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 1-workflow.md
- Version window: current-plus-latest-history
- Target source: inferred
- Rationale: Inferred from AGENTS.md generator skill facts and governance-specific repository content.

## Source Versions
- `docs/experience/1-workflow.md`
- `docs/experience/history_experience/20260512-165633/1-workflow.md`

## Evidence Sources
- Current workflow experience, latest historical workflow experience, current control profile, and regression tests for evolution classification.

## Applicable Scenario
- Use this template when maintaining an agent-governance skill that generates, verifies, or evolves AI coding-agent instruction files and docs governance records.

## Distilled Workflow
- Inspect repository facts and the control profile before deciding whether guidance applies.
- Convert user feedback into failing regression tests that assert both the desired output and the forbidden stale output.
- Apply detailed AI-authored experience first, then evolve only from AI-authored synthesis.
- Archive obsolete indexed templates before writing newly classified templates.
- Run focused tests, docs governance verification, skill audit, and full evaluation before claiming completion.

## Key Decisions
- Skill projects write only to `skill-template/<category>/<type>/`; they never write sibling engineering templates for the same experience source.
- Experience files preserve what happened in the project; evolution templates preserve reusable guidance distilled from that evidence.
- Missing synthesis is a request state, not permission to copy source lessons.

## Common Problems
- Copying `## Iterated Lessons` into templates makes unrelated future projects inherit local assumptions.
- Treating `project_type=skill-repo` as an engineering category pollutes `engineering-template/skill-repo/`.
- Short experience files pass structural checks but fail as operational memory.

## Non-Reusable Content
- Do not carry over release timestamps, temporary handoff counts, local branch names, or one-off conversation wording.
- Do not include Vivado, sorting, frontend, or backend assumptions unless the target category actually contains those facts.

## Application Checklist
- Confirm the project kind is `skill`.
- Confirm the target path is under `skill-template/agent-governance/<skill-name>/` or a more precise AI-approved skill category.
- Confirm current experience passed required-section and length validation.
- Confirm the template body is synthesized and does not use the old `Reusable Lessons` copy format.
