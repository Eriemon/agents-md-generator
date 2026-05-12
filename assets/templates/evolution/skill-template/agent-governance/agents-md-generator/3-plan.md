# Plan Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 3-plan.md
- Version window: current-plus-latest-history
- Target source: inferred
- Rationale: Inferred from AGENTS.md generator planning and governance contracts.

## Source Versions
- `docs/experience/3-plan.md`
- `docs/experience/history_experience/20260512-165633/3-plan.md`

## Evidence Sources
- Current plan experience, latest historical plan experience, user-approved implementation plan, and tests that encode user examples.

## Applicable Scenario
- Use when planning changes to agent-rule generation, docs governance, experience capture, template evolution, install preservation, or release gates.

## Distilled Workflow
- Translate user language into observable acceptance criteria.
- Name source artifacts, target artifacts, forbidden artifacts, and repair behavior.
- Keep examples concrete enough for tests while designing generic helpers that can handle future categories.
- Record no-release or no-install assumptions separately from implementation completion.

## Key Decisions
- A plan for governance automation must cover current state, history state, pending request state, and verification state.
- Classification examples such as FPGA/Vivado and algorithm/sort are acceptance fixtures, not a closed taxonomy.
- Archive-before-cleanup belongs in the plan whenever generated paths move.

## Common Problems
- Planning only the happy path lets stale outputs survive in active directories.
- Saying "make summaries better" without section and length rules leaves implementation subjective.
- Mixing release packaging into a source-only task creates avoidable version drift.

## Non-Reusable Content
- Do not reuse local handoff counts, timestamped history folder names, or branch-specific steps unless the future task has the same release context.

## Application Checklist
- Include one skill fixture and one engineering fixture when taxonomy behavior changes.
- Include at least one malformed payload case.
- Confirm docs and tests describe the same public interface.
