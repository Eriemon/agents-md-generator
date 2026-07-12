# `audit_skill.py` decomposition plan

## Current Size
Skill audit orchestration remains above 64 KiB while audit contracts are preserved.

## Split Boundaries
Separate layout, documentation, runtime, eval, and resource audits.

## Target Files
Keep public audit orchestration and result assembly in `audit_skill.py`.

## Exit Criteria
The runtime falls below 64 KiB and all audit tests pass.
