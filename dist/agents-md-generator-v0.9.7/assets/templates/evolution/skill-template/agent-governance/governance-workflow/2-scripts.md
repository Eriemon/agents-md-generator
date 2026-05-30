# Scripts Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: governance-workflow
- Source file: 2-scripts.md
- Version window: current-plus-latest-history
- Target source: ai
- Rationale: Inferred from project control profile, repository facts, and topic keywords.
- Source workspace: current governed workspace (local path intentionally omitted)
- Source project: agents-md-generator
- Source handoff window: 76-80

## Source Versions
- `docs/experience/2-scripts.md`
- `docs/experience/history_experience/20260527-171409/2-scripts.md`

## Evidence Sources
- Current and previous scripts experience files, verifier output, and the latest runtime-routing regressions.

## Applicable Scenario
- Use when governance scripts emit user-visible command paths or when script/runtime ownership is being refactored.

## Distilled Workflow
- Centralize runtime-path choice in one helper, then update every script that serializes those paths into AGENTS, docs, JSON, or verifier output.
- Keep local product/tooling checks separate from installed governance-runtime checks.
- Add a verifier hard-fail for the forbidden script path pattern.

## Key Decisions
- Treat emitted command paths as public interfaces.
- Use one shared helper for routing and dedicated regressions for each user-visible boundary.

## Common Problems
- Shared helpers can contaminate render, verify, and review outputs simultaneously.
- Script refactors that skip docs or eval updates silently create contract drift.

## Non-Reusable Content
- Exclude one-off branch names, temporary fixture paths, and machine-local install directories.

## Application Checklist
- Confirm the helper, the emitters, the verifier, and the repo-local eval harness were all updated together.
- Confirm owner and external path regressions both exist.
