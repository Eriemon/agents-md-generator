# Workflow Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 1-workflow.md
- Version window: current-plus-latest-history
- Target source: ai
- Rationale: The recent evidence concerns a Codex skill that generates and verifies AGENTS.md agent-governance rules, including config-backed policy rendering, validation scripts, release packaging, and install decision handling.

## Source Versions
- `docs/experience/1-workflow.md`
- `docs/experience/history_experience/20260521-171008/1-workflow.md`

## Evidence Sources
Use recent exact-cwd handoffs, the control profile, root AGENTS.md, release receipts, review_governance output, and confidence gate output. The relevant evidence must show repository facts or control profile inspection before synthesis, AGENTS.md or agent rule alignment, script/test/verify execution, and release or install decision handling.

## Applicable Scenario
Apply this template when maintaining a Codex skill that changes generated AGENTS.md behavior, agent rule files, docs governance, or verification gates. It is for skill-template agent-governance work, not hardware or deployment execution.

## Distilled Workflow
Inspect repository facts and the control profile, translate the user rule into a small public contract, write failing tests, implement script and config changes, render and verify AGENTS.md, synchronize references and evals, package the release, validate install intent, write handoff, clear cadence requests, mark freshness, and rerun confidence. This workflow chain keeps design alignment, validation, release, and installation decisions in one closure loop.

## Key Decisions
Keep root AGENTS.md concise, put detailed policy in config or references, and make verification reject both missing generated text and weakened source config. Use --target skip when installation has not been explicitly confirmed.

## Common Problems
Common failures include latest-dist mismatch after version bump, stale AGENTS freshness after release commits, over-compressed root sections that hide required governance phrases, and pending experience requests after handoff.

## Non-Reusable Content
Do not copy project-specific version numbers, local paths, or one-off command transcripts into the template. Keep the reusable sequence and gate rationale only.

## Application Checklist
Confirm facts, write red tests, implement narrowly, run unit/audit/verify/eval gates, package dist, validate install decision, write handoff, clear cadence, mark freshness, and run final confidence.
