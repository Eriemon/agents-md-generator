# _agents_project_facts_discovery.py decomposition plan

## Current Size
- Current file: `skills/agents-md-generator/scripts/python/common/_agents_project_facts_discovery.py`
- Current size: `72564 bytes`.
- Temporary exception: repository discovery, framework detection, command extraction, and project fact normalization still share one helper module.

## Split Boundaries
- Keep the public discovery orchestration and result assembly in the current module.
- Extract package-manager and framework detectors into a focused discovery helper.
- Extract command and path evidence normalization into a focused facts helper.
- Preserve current fact keys, ordering, and unknown-value behavior.

## Target Files
- `skills/agents-md-generator/scripts/python/common/_agents_project_facts_discovery.py`
- `skills/agents-md-generator/scripts/python/common/_agents_project_facts_frameworks.py`
- `skills/agents-md-generator/scripts/python/common/_agents_project_facts_commands.py`

## Exit Criteria
- The current module drops below `65536` bytes.
- Project inspection and detection tests preserve their existing JSON contracts.
- Strict current-project quality and the full repository unit suite pass after extraction.
