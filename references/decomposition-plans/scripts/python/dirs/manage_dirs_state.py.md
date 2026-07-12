# `manage_dirs_state.py` decomposition plan

## Current Size
Directory state validation remains above 64 KiB during staged extraction.

## Split Boundaries
Separate schema, path, settings, and current-layout validation.

## Target Files
Keep public state orchestration in `manage_dirs_state.py`.

## Exit Criteria
The runtime falls below 64 KiB and directory-governance tests pass.
