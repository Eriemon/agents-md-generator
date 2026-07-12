# `manage_docs_sync_verify.py` decomposition plan

## Current Size
Synchronization and verification remain above 64 KiB during staged extraction.

## Split Boundaries
Separate drift analysis, managed-text rewriting, and verification reports.

## Target Files
Keep public synchronization orchestration in `manage_docs_sync_verify.py`.

## Exit Criteria
The runtime falls below 64 KiB and docs synchronization tests pass.
