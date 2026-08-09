# manage_dirs_state.py decomposition plan

## Current Size
- Current file: `skills/agents-md-generator/scripts/python/dirs/manage_dirs_state.py`
- Current size: `82124 bytes`.
- Temporary exception: directory snapshots, planning, profile projection, archival, and state persistence remain in one state module.

## Split Boundaries
- Keep existing public constants and compatibility entrypoints in the current module.
- Extract snapshot scanning and normalization into a focused helper.
- Extract planned-structure and remote-profile projection into a planning helper.
- Extract archival and persistence operations into a storage helper.

## Target Files
- `skills/agents-md-generator/scripts/python/dirs/manage_dirs_state.py`
- `skills/agents-md-generator/scripts/python/dirs/manage_dirs_snapshot.py`
- `skills/agents-md-generator/scripts/python/dirs/manage_dirs_planning.py`
- `skills/agents-md-generator/scripts/python/dirs/manage_dirs_storage.py`

## Exit Criteria
- The current module drops below `65536` bytes.
- Directory scan, init, refresh, archive, and review JSON remain backward compatible.
- Strict current-project quality and all directory-governance tests pass.
