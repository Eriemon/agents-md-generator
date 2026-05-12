# Scripts Evolution Template

- Template family: skill-template
- Target type: agents-md-generator
- Source file: 2-scripts.md
- Version window: current-plus-latest-history

## Source Versions
- `docs/experience/2-scripts.md`
- `docs/experience/history_experience/20260512-165633/2-scripts.md`

## Reusable Lessons
- Script code should model governance state, not pretend to learn. The correct interface is a request/payload split: generate an evidence bundle, require AI-authored JSON, validate that payload, then write files.
- Quality checks belong in deterministic code because they catch repeatable failures: copied HANDOFF sections, placeholder text, missing files, unexpected filenames, and excessive similarity across the 10 experience files.
- Conversation capture should be append-only JSON under .agents so the request can cite the latest 10 entries without assuming the runtime can magically access chat history.

- Script code should model governance state, not pretend to learn. The correct interface is a request/payload split: generate an evidence bundle, require AI-authored JSON, validate that payload, then write files.
- Quality checks belong in deterministic code because they catch repeatable failures: copied HANDOFF sections, placeholder text, missing files, unexpected filenames, and excessive similarity across the 10 experience files.
- Conversation capture should be append-only JSON under .agents so the request can cite the latest 10 entries without assuming the runtime can magically access chat history.
