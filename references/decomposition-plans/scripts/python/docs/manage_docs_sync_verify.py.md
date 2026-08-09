# manage_docs_sync_verify.py decomposition plan

## Current Size
- Current file: `skills/agents-md-generator/scripts/python/docs/manage_docs_sync_verify.py`
- Current size: `65721 bytes`.
- Temporary exception: root synchronization, global baseline synchronization, and docs verification remain combined just above the limit.

## Split Boundaries
- Keep public sync and verification handlers in the current module.
- Extract root AGENTS synchronization and freshness marking into a root-sync helper.
- Extract global Codex baseline synchronization into a global-sync helper.
- Preserve managed-block replacement, manual-content retention, and verification payloads.

## Target Files
- `skills/agents-md-generator/scripts/python/docs/manage_docs_sync_verify.py`
- `skills/agents-md-generator/scripts/python/docs/manage_docs_root_sync.py`
- `skills/agents-md-generator/scripts/python/docs/manage_docs_global_sync.py`

## Exit Criteria
- The current module drops below `65536` bytes.
- Root synchronization, global baseline, and docs synchronization tests pass unchanged.
- Strict current-project quality and docs verification remain green.
