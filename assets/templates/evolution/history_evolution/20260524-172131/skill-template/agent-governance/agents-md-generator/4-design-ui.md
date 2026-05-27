# Design UI Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 4-design-ui.md
- Version window: current-plus-latest-history
- Target source: ai
- Rationale: The recent evidence concerns a Codex skill that generates and verifies AGENTS.md agent-governance rules, including config-backed policy rendering, validation scripts, release packaging, and install decision handling.

## Source Versions
- `docs/experience/4-design-ui.md`
- `docs/experience/history_experience/20260521-171008/4-design-ui.md`

## Evidence Sources
Use generated AGENTS.md sections, decision_request JSON, CLI prompts, SKILL.md wording, agents/openai.yaml, and reference docs. For non-visual governance work, treat CLI and conversational output as the user interface.

## Applicable Scenario
Apply when a skill changes how agents or users see governance choices, confirmation prompts, generated root summaries, or install decisions. It is especially useful when strict policy must remain readable in a small AGENTS.md file.

## Distilled Workflow
Design the visible root summary before writing detailed examples. Classify each sentence as command, config pointer, or example. Keep commands in AGENTS.md, editable detail in JSON, examples in references, and mutation choices in structured decision_request output. Use recommended safe defaults for install or destructive operations.

## Key Decisions
Compact UI is safer than verbose root docs when the root has a hard size limit. A generated summary must still name the governing config and the non-negotiable bans. Prompts must distinguish validation from mutation.

## Common Problems
Common UI failures include burying the config path, trimming required phrases, overloading a prompt with multiple decisions, or implying installation happened when only validation ran.

## Non-Reusable Content
Do not copy the exact v0.7.0 policy text into a generic template. Reuse the display pattern: concise command, config pointer, detailed reference, explicit confirmation.

## Application Checklist
Draft the generated summary, move examples to references, verify root size, check decision_request defaults, test missing or weakened text, and confirm no unrequested mutation occurs.
