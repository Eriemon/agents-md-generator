# `design_questions.py` decomposition plan

## Current Size
Question contracts remain above 64 KiB during compatibility migration.

## Split Boundaries
Separate skill, engineering, and directory question definitions.

## Target Files
Keep public selection and compatibility exports in `design_questions.py`.

## Exit Criteria
The runtime falls below 64 KiB and design interview tests preserve ordering and identifiers.
