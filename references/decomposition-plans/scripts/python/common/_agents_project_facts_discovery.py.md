# `_agents_project_facts_discovery.py` decomposition plan

## Current Size
The discovery runtime remains above 64 KiB while compatibility contracts are preserved.

## Split Boundaries
Extract framework detection and command normalization without changing fact keys.

## Target Files
Keep orchestration in `_agents_project_facts_discovery.py`; use focused discovery helpers.

## Exit Criteria
The runtime falls below 64 KiB and all project-inspection tests pass.
