# manage_dirs_review.py decomposition plan

## Current Size

The directory review module is above the configured source-size threshold after adding the manifest-only upload review route. This plan preserves the existing public review contract while allowing the review orchestration to shrink.

## Split Boundaries

Keep local and remote directory mutation rules together until their shared result schema is stable. The structure/takeover candidate and repair helpers now live in `manage_dirs_structure.py`; upload-item routing remains in `manage_dirs_upload.py`, and remote path policy remains in `manage_dirs_remote.py`.

## Target Files

- `skills/agents-md-generator/scripts/python/dirs/manage_dirs_review.py`
- `skills/agents-md-generator/scripts/python/dirs/manage_dirs_compat.py`
- `skills/agents-md-generator/scripts/python/dirs/manage_dirs_structure.py`
- `skills/agents-md-generator/scripts/python/dirs/manage_dirs_upload.py`
- `skills/agents-md-generator/scripts/python/dirs/manage_dirs_remote.py`

## Exit Criteria

The public `manage_dirs.py review` JSON contract remains backward compatible, structure/takeover helpers remain import-compatible through `manage_dirs_review.py`, manifest-only upload blockers remain non-overridable, remote and local path rules keep their current behavior, and the narrow remote tester regression is green.
