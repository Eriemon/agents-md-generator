# Scripts Evolution Template

- Template family: skill-template
- Category path: agent-governance
- Target type: agents-md-generator
- Source file: 2-scripts.md
- Version window: current-plus-latest-history
- Target source: ai
- Rationale: Inferred from project control profile, repository facts, and topic keywords.

## Source Versions
- `docs/experience/2-scripts.md`
- `docs/experience/history_experience/20260516-225309/2-scripts.md`

## Evidence Sources
- Current and latest historical `2-scripts.md` records.
- Script-related handoff evidence across checkpoints 36-40.
- Command evidence from focused unittest runs and the final verification chain.

## Applicable Scenario
- Use when a future agents-md-generator maintenance task changes Python scripts, CLI routing, JSON contracts, or verification aggregation behavior.
- The template fits agent-governance skill work where scripts enforce contracts and surface state transitions clearly.

## Distilled Workflow
- Identify the exact script, function, CLI surface, or JSON boundary that owns the behavior.
- Separate evidence collection from routing or write decisions so a script does not absorb unrelated governance semantics.
- Add or update the smallest focused regression test that exposes the script bug.
- Implement the narrow script change, then rerun targeted tests, repository verify, and the aggregate validation command.

## Key Decisions
- Keep takeover trigger logic narrower than raw root-state reason enumeration.
- Keep aggregate validation scripts explicit about which subcommands they run and which project root they resolve.
- Update prompt or reference files whenever script behavior changes public semantics.

## Common Problems
- A helper script can accidentally become the place where all abnormal states collapse into one branch.
- Aggregators can report misleading success when one required verify step is missing.
- Script changes can look correct locally while docs and tests still describe the old behavior.

## Non-Reusable Content
- Omit one-off command transcripts, local absolute temp paths, and turn-specific commentary.
- Do not convert this template into a hardware, frontend, or unrelated engineering execution guide.

## Application Checklist
- Name the exact script or function that changed.
- State the guarded CLI or JSON contract.
- Record the focused regression command and the final verification command.
- Confirm script behavior, tests, and public docs were updated together.
