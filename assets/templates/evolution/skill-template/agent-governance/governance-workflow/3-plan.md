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
- Source handoff window: 66-70

## Source Versions
- `docs/experience/3-plan.md`
- `docs/experience/history_experience/20260524-172127/3-plan.md`

## Evidence Sources
- Latest and previous planning experience entries plus the release/install confidence checkpoint results.

## Applicable Scenario
- Use when a skill task begins as a feature implementation but the success criterion expands into factual confidence across packaging, installation, and governance proof.

## Distilled Workflow
- Translate confidence into separate failing conditions for source behavior, release parity, replace-install behavior, installed audit, and governance freshness.
- Work through those checkpoints in order and expand the plan immediately when a later stage uncovers a new real loophole.
- Do not stop at the first green layer; continue until every requested proof stage has either passed or been intentionally removed from scope.

## Key Decisions
- Treat newly discovered late-stage loopholes as mandatory scope when the user asked for certainty.
- Keep release/install sequencing explicit so dependent commands are never run in parallel by accident.

## Common Problems
- Plans that stop at unit tests are too weak for release-oriented skill work.
- Governance freshness is easy to under-plan even though it can block final confidence after every functional stage is green.

## Non-Reusable Content
- Omit one-off release timestamps, local backup paths, and temporary command noise that do not change future planning decisions.

## Application Checklist
- Name each proof stage explicitly.
- Replan immediately when a later gate disproves the current claim.
- Reserve time for post-handoff cadence and freshness closure on checkpoint boundaries.
