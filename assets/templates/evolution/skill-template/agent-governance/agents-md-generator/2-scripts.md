# Scripts Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 2-scripts.md
- Version window: current-plus-latest-history
- Target source: ai
- Rationale: The recent evidence concerns a Codex skill that generates and verifies AGENTS.md agent-governance rules, including config-backed policy rendering, validation scripts, release packaging, and install decision handling.

## Source Versions
- `docs/experience/2-scripts.md`
- `docs/experience/history_experience/20260521-171008/2-scripts.md`

## Evidence Sources
Use changed script paths, tests, audit findings, eval cases, and command JSON output. Identify which script owns config defaults, rendering, verification, audit alignment, eval comparison, release packaging, or installation validation.

## Applicable Scenario
Apply when changing a Codex skill script that affects generated agent governance, local JSON contracts, public CLI behavior, or release/install safety. The template fits Python tool-wrapper scripts and deterministic verification helpers.

## Distilled Workflow
Map the command, function, JSON field, and validation boundary before editing. Add a failing test at the CLI or rendered-output surface, implement a small helper, update downstream scripts that consume the contract, and add audit/eval coverage so companion docs cannot drift. Validate raw user-editable config separately from merged defaults.

## Key Decisions
Treat config keys and enum values as public interfaces. Keep generated text and source config checks independent. Preserve backward compatibility for absent old files while rejecting explicit weakened governance in strong-control workspaces.

## Common Problems
Common failures include defaults masking a bad local file, renderer hard-coding text that should come from config, verifier checking the whole file instead of the managed section, and audit checks missing companion docs.

## Non-Reusable Content
Do not copy exact temporary file names or branch-specific timestamps. Preserve script ownership and validation-boundary lessons.

## Application Checklist
Name the script boundary, add negative tests, implement helpers, update render/verify/audit/eval consumers, run focused tests, run full validation, package, and verify installed or skipped install behavior.
