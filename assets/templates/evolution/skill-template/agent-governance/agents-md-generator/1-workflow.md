# Workflow Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 1-workflow.md
- Version window: current-plus-latest-history
- Target source: ai
- Rationale: Inferred from project control profile, repository facts, and topic keywords.

## Source Versions
- `docs/experience/1-workflow.md`
- `docs/experience/history_experience/20260516-225309/1-workflow.md`

## Evidence Sources
- Current `docs/experience/1-workflow.md` plus the latest historical workflow snapshot from `docs/experience/history_experience/`.
- Handoff window 36-40 and the recent conversation snapshots referenced by the cadence request.
- Validation evidence from unit tests, audit, verify, docs verify, and evaluate_skill.

## Applicable Scenario
- Use when a future governance workflow task matches this repository's agent-governance constraints and needs reusable guidance rather than a copied handoff note.
- This applies to skill repositories where repository facts and control profile inspection must drive AGENTS behavior changes before release or installation decisions.

## Distilled Workflow
- Inspect repository facts and the control profile before changing behavior.
- Align AGENTS.md rules, interview or routing design, and docs governance expectations so the user-facing contract stays explicit.
- Update the smallest responsible scripts and prompts, then run focused tests, full validation, and repository verification.
- Only after the repository is green should the workflow decide whether release packaging or installation is required.
- When cadence-driven governance is due, apply the AI experience payload and evolution summary in the same conversation so the repository closes its own loop.

## Key Decisions
- Keep health-check intent separate from explicit AGENTS design intent.
- Reserve takeover for compatibility upgrades such as version mismatch instead of all abnormal root states.
- Treat release and installation as governance decisions that follow validation, not as shortcuts to confidence.

## Common Problems
- Routing changes can silently bypass full interviews if exception lists and takeover triggers are coupled.
- Prompt text, tests, and script behavior can drift apart even when commands still succeed.
- Docs governance can remain stale after code work if the cadence request is left pending.

## Non-Reusable Content
- Omit temporary timestamps, one-off backup folder names, and turn-specific narration.
- Do not copy hardware engineering execution chains or unrelated product workflows into this template.

## Application Checklist
- Confirm repository facts or control profile inspection happened first.
- Confirm AGENTS rule or design alignment was explicitly checked.
- Confirm scripts, tests, verify, and validation were rerun after the change.
- Confirm release or install handling was consciously decided rather than implied.
- Confirm docs governance closure finished before claiming completion.
