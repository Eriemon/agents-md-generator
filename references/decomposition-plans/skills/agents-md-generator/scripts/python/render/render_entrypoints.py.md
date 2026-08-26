# render_entrypoints.py decomposition plan

## Current Size
- Measured source: `skills/agents-md-generator/scripts/python/render/render_entrypoints.py`.
- The shard is above the configured Python budget. It remains the public render CLI boundary while platform transactions finish their stabilization cycle.

## Split Boundaries
- The present module owns argument decoding, orchestration order, and the public `main()` JSON/text contract.
- A platform-state shard should own selection-marker validation, explicit migration retirement, and rollback snapshots.
- A render-write shard should own root/scoped write plans, byte-budget checks, and commit/rollback boundaries.
- Existing template and project-fact shards remain the sole owners of those concerns; platform catalog parsing must stay single-sourced.

## Target Files
- This inventory is an ownership map, not an instruction to create the destination files immediately.
- Facade retained: `skills/agents-md-generator/scripts/python/render/render_entrypoints.py`.
- Platform-state destination: `skills/agents-md-generator/scripts/python/render/render_platform_state.py`, including selection-marker and migration evidence.
- Write-boundary destination: `skills/agents-md-generator/scripts/python/render/render_write_plan.py`, including byte budgets and rollback snapshots.
- The facade must continue importing the shared catalog/config resolver rather than introducing a second platform registry.

## Exit Criteria
- `render_agents.py` and this module preserve their current public output contracts.
- Selection, migration retirement, shim rollback, scoped writes, and size enforcement remain fail-closed after extraction.
- The aggregate module returns below the configured shard budget once the named seams are moved.
- The canonical tester reruns selector-free pytest and the reviewer rechecks the approved plan after the move.
