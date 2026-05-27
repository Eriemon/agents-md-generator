# Plan Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 3-plan.md
- Version window: current-plus-latest-history
- Target source: ai
- Rationale: The recent evidence concerns a Codex skill that generates and verifies AGENTS.md agent-governance rules, including config-backed policy rendering, validation scripts, release packaging, and install decision handling.

## Source Versions
- `docs/experience/3-plan.md`
- `docs/experience/history_experience/20260521-171008/3-plan.md`

## Evidence Sources
Use the user plan, control profile, previous handoff, targeted red tests, full gate results, release outputs, and final governance requests. Evidence should show how requirements became acceptance criteria and how temporary failures were classified.

## Applicable Scenario
Apply when a multi-step skill-governance task changes generated AGENTS.md behavior, docs governance, release rules, or install decisions. It helps keep planning tied to executable gates rather than prose promises.

## Distilled Workflow
Convert every public-interface statement into a test, script check, audit rule, eval case, or release gate. Sequence the work so expected temporary failures are visible: version bump before package may fail latest-dist checks, release commits may require freshness repair, and handoff cadence may require experience/evolution payloads.

## Key Decisions
Do not claim completion at implementation. Include docs synchronization, package generation, install decision, handoff, cadence clearing, freshness, and confidence in the plan. Keep no-push and no-install assumptions explicit.

## Common Problems
Plans fail when they omit post-release governance, ignore active request files, or treat a shell exit code as success while the JSON output says ok false.

## Non-Reusable Content
Do not retain exact hashes unless the current review base requires them. Keep the sequencing pattern and acceptance criteria.

## Application Checklist
List public interfaces, write red tests, implement, sync docs/evals/audit, package, validate install intent, review committed diff, handle handoff cadence, mark freshness, and rerun confidence.
