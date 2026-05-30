## Current Size

`scripts/manage_dirs.py` is above the configured 1000-line threshold because it currently combines local structure-gate logic, remote structure review, archive flow, and shared path-class validation in one runtime file.

## Split Boundaries

Future decomposition should separate:

- local structure scan and normalization planning
- remote mutation review and protected-path enforcement
- shared path classification and result-formatting helpers

The current file stays authoritative until those boundaries are extracted without changing CLI behavior.

## Target Files

Planned target modules:

- `scripts/manage_dirs.py` as the CLI entrypoint and argument router
- `scripts/manage_dirs_local.py` for local structure-gate and normalization logic
- `scripts/manage_dirs_remote.py` for remote review, archive, and runtime-stage policy logic

## Exit Criteria

This decomposition plan is complete when:

- `scripts/manage_dirs.py` is back under the configured line limit
- extracted modules have clear single-purpose ownership
- existing `manage_dirs.py` CLI commands keep the same observable behavior and validation output
