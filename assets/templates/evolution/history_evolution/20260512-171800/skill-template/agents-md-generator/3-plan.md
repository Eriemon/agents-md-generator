# Plan Evolution Template

- Template family: skill-template
- Target type: agents-md-generator
- Source file: 3-plan.md
- Version window: current-plus-latest-history

## Source Versions
- `docs/experience/3-plan.md`
- `docs/experience/history_experience/20260512-165633/3-plan.md`

## Reusable Lessons
- Planning for this skill should put quality gates before downstream automation. Automatic evolution is only useful if the source experience files are genuinely learned summaries, so the v0.4.0 order is quality repair first, evolution second, release packaging last.
- Ambiguous phrases such as recent two versions or latest conversations need operational definitions in the plan. Here, recent two versions means current plus latest history, and recent conversation context means up to 10 saved snapshots or an explicit missing-context marker.
- A plan is safer when it names the no-op state: if the cadence arrives without AI payload, the system writes a request and marks experience_update_required instead of silently producing weak documents.

- Planning for this skill should put quality gates before downstream automation. Automatic evolution is only useful if the source experience files are genuinely learned summaries, so the v0.4.0 order is quality repair first, evolution second, release packaging last.
- Ambiguous phrases such as recent two versions or latest conversations need operational definitions in the plan. Here, recent two versions means current plus latest history, and recent conversation context means up to 10 saved snapshots or an explicit missing-context marker.
- A plan is safer when it names the no-op state: if the cadence arrives without AI payload, the system writes a request and marks experience_update_required instead of silently producing weak documents.
