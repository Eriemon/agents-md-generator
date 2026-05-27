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
- Source handoff window: 66-70

## Source Versions
- `docs/experience/2-scripts.md`
- `docs/experience/history_experience/20260524-172127/2-scripts.md`

## Evidence Sources
- Latest and previous scripts experience entries plus the install_skill regression and installed audit evidence.

## Applicable Scenario
- Use when a release or install helper preserves prior user artifacts and must keep the installed result safe without discarding accumulated reusable templates.

## Distilled Workflow
- Identify every preserve, merge, and fallback branch in the helper before patching only the obvious path.
- Add a regression fixture that mirrors the real installed-state contamination, including structured JSON provenance where relevant.
- Implement one installed-safe rewrite layer that can sanitize strings and structured JSON values, and run every preserved output through it before writing.
- Verify the source helper, then rebuild the release and confirm the installed audit passes on the replaced skill.

## Key Decisions
- Share one sanitizer across preserve, merge, and fallback paths so no branch bypasses the installed-safety contract.
- Validate the installed artifact after replacement instead of assuming source-side proof is enough.

## Common Problems
- Fixing only the merge path leaves unmatched preserved templates or conflict fallbacks unsafe.
- Regex-based sanitization can create packaging drift unless release parity is rechecked immediately after the change.

## Non-Reusable Content
- Omit exact release hashes, temporary fixture names, and one-off local paths that do not change future script decisions.

## Application Checklist
- Enumerate preserve, merge, and fallback branches.
- Add a real installed-state regression fixture.
- Apply one installed-safe rewrite layer before writes.
- Recheck release parity and installed audit after the script change.
