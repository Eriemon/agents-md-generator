# `source_governance_config.py` decomposition plan

## Current Size
Configuration normalization remains above 64 KiB during compatibility migration.

## Split Boundaries
Separate defaults, migration, validation, and profile projection.

## Target Files
Keep public configuration assembly in `source_governance_config.py`.

## Exit Criteria
The runtime falls below 64 KiB and source-governance tests pass.
