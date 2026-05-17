# Design UI Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 4-design-ui.md
- Version window: current-plus-latest-history
- Target source: ai
- Rationale: Inferred from project control profile, repository facts, and topic keywords.

## Source Versions
- `docs/experience/4-design-ui.md`
- `docs/experience/history_experience/20260516-225309/4-design-ui.md`

## Evidence Sources
- Current and latest historical `4-design-ui.md` records.
- Handoff window 36-40 showing no GUI or visual interface changes.
- The cadence request and repository facts that define the current work as CLI and docs governance only.

## Applicable Scenario
- Use when this repository has no active UI work and the design topic must accurately record that boundary.
- Also use when future maintainers need guidance for turning this topic back into a real UI/design evidence file once a visual surface exists.

## Distilled Workflow
- Inspect the repository facts and current task scope to decide whether any UI, GUI, visual design, or browser-rendered surface actually changed.
- If no UI changed, explicitly record 暂无 UI 经验 and explain the current interface boundary instead of fabricating visual lessons.
- If UI work does exist, replace the placeholder boundary with concrete design evidence such as screens reviewed, layout decisions, accessibility checks, and responsive risks.
- Verify that the design topic remains UI-specific rather than becoming a duplicate scripts or docs-governance note.

## Key Decisions
- Preserve truthfulness about the absence of UI work.
- Keep the file ready for future visual or interaction evidence without mixing unrelated governance content into it.
- Use design-specific language only when a real visual interface exists.

## Common Problems
- Reusing script or validation prose inside the design topic creates false UI memory.
- Writing only a one-line placeholder fails the repository's quality bar.
- Future UI work can ship without a design record if this boundary is not maintained.

## Non-Reusable Content
- Omit temporary command logs and unrelated release details.
- Do not turn this template into a generic engineering or hardware workflow checklist.

## Application Checklist
- Confirm whether UI work actually happened.
- If not, state 暂无 UI 经验 and describe the real interface boundary.
- If yes, record screenshots, interaction states, accessibility, and responsive validation.
- Ensure the resulting file stays design-specific.
