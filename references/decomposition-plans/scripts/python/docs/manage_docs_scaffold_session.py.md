# manage_docs_scaffold_session.py decomposition plan

## Current Size
- Current file: `skills/agents-md-generator/scripts/python/docs/manage_docs_scaffold_session.py`
- Current size: `66746 bytes`.
- Temporary exception: governance scaffolding and session lifecycle transitions still share one module.

## Split Boundaries
- Keep public scaffold and session command handlers in the current module.
- Extract governance-tree scaffold rendering into a focused helper.
- Extract start, resume, repair, and completion state transitions into a session helper.
- Preserve state-file schemas, exit codes, and command payloads.

## Target Files
- `skills/agents-md-generator/scripts/python/docs/manage_docs_scaffold_session.py`
- `skills/agents-md-generator/scripts/python/docs/manage_docs_scaffold.py`
- `skills/agents-md-generator/scripts/python/docs/manage_docs_session_state.py`

## Exit Criteria
- The current module drops below `65536` bytes.
- Docs lifecycle, session recovery, and synchronization tests retain exact behavior.
- Strict current-project quality and docs verification pass after extraction.
