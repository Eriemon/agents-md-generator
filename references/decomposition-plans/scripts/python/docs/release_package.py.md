# release_package.py decomposition plan

## Current Size
- Current file: `skills/agents-md-generator/scripts/python/docs/release_package.py`
- Current size: `67208 bytes`.
- Temporary exception: release preparation, package creation, branch cleanup, and release-member discovery still share the aggregate release shard.

## Split Boundaries
- Keep the public release preparation and package orchestration entry points in the current module.
- Extract branch cleanup checks and decision payload construction into a branch-gate helper.
- Extract release-member discovery and project-kind classification into a release-layout helper.
- Preserve the aggregate shard execution contract and replaceable `release_gate` hook used by focused verification.

## Target Files
- `skills/agents-md-generator/scripts/python/docs/release_package.py`
- `skills/agents-md-generator/scripts/python/docs/release_branch_gate.py`
- `skills/agents-md-generator/scripts/python/docs/release_layout.py`

## Exit Criteria
- The current module drops below `65536` bytes.
- Release preparation, package intent propagation, branch cleanup, receipt, and immutable-history checks pass unchanged.
- Strict current-project Python quality, source governance, release gates, and the complete pytest receipt remain green.
