# Workflow Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: governance-workflow
- Source file: 1-workflow.md
- Version window: current-plus-latest-history
- Target source: ai
- Rationale: Inferred from project control profile, repository facts, and topic keywords.
- Source workspace: current governed workspace (local path intentionally omitted)
- Source project: agents-md-generator
- Source handoff window: 66-70

## Source Versions
- `docs/experience/1-workflow.md`
- `docs/experience/history_experience/20260524-172127/1-workflow.md`

## Evidence Sources
- Latest and immediately previous workflow experience entries for this repository.
- The latest handoff window, release receipt evidence, installed audit result, and confidence-gate findings.

## Applicable Scenario
- Use when a future agents-md-generator task asks for factual confidence across source, release, install, and governance closure instead of stopping at source-side green tests.

## Distilled Workflow
- Inspect repository facts and the current control profile before classifying the problem.
- Align AGENTS.md rules and docs governance behavior with the intended agent-governance contract before changing scripts or release flows.
- Reproduce the failure with a targeted regression or gate result, then implement the smallest script or contract change that closes the real loophole.
- Run focused tests, then the full verify/eval/audit chain, then rebuild the versioned release, rerun release gates, and validate both install-skip and replace-install behavior.
- Finish by updating handoff and cadence artifacts, marking AGENTS freshness on the final state, and rerunning confidence so repository governance and installed behavior agree.

## Key Decisions
- Treat release and installation as mandatory parts of the reusable skill-governance workflow, not optional afterthoughts.
- Return to the earliest failing proof stage whenever a later gate disproves the current confidence claim.
- Keep release/install commands serial so each gate reads a stable artifact tree.

## Common Problems
- Source-green changes can still fail after packaging or replacement install if preserved artifacts bypass installed-safety checks.
- Parallel release/install execution can create noisy transient failures that hide the real state of the release artifact.
- Confidence often remains blocked by stale governance freshness even after functional fixes are complete.

## Non-Reusable Content
- Omit exact timestamps, temporary branch names, local absolute paths, and conversation-only details that do not affect future governance decisions.

## Application Checklist
- Inspect repository facts or control-profile facts before implementation.
- Keep AGENTS.md and docs governance rule alignment visible in the reusable workflow.
- Add or rerun a regression that proves the old governance or install behavior was wrong.
- Run focused tests and full verify/audit/eval gates.
- Rebuild the release, rerun release/install proof, and confirm installed behavior.
- Close handoff cadence and rerun freshness/confidence on the final state.
