# `manage_docs_scaffold_session.py` decomposition plan

## Current Size
Session scaffolding remains above 64 KiB while lifecycle contracts are preserved.

## Split Boundaries
Separate scaffold, session, recovery, and handoff orchestration.

## Target Files
Keep the public lifecycle entry points in `manage_docs_scaffold_session.py`.

## Exit Criteria
The runtime falls below 64 KiB and docs lifecycle tests pass.
