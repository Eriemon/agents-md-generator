# audit_skill.py decomposition plan

## Current Size
- Current file: `skills/agents-md-generator/scripts/python/verify/audit_skill.py`
- Current size: `92191 bytes`.
- Temporary exception: structure, references, compilation, eval contracts, source governance, and design-pattern coverage remain in one audit module.

## Split Boundaries
- Keep the public audit entrypoint, aggregate result, and CLI in the current module.
- Extract skill structure and referenced-resource checks into a structure helper.
- Extract eval schema and design-pattern coverage checks into an eval helper.
- Extract Python compilation and source-governance integration into a source helper.

## Target Files
- `skills/agents-md-generator/scripts/python/verify/audit_skill.py`
- `skills/agents-md-generator/scripts/python/verify/audit_skill_structure.py`
- `skills/agents-md-generator/scripts/python/verify/audit_skill_evals.py`
- `skills/agents-md-generator/scripts/python/verify/audit_skill_source.py`

## Exit Criteria
- The current module drops below `65536` bytes.
- Audit JSON keys, error wording contracts, and exit codes remain backward compatible.
- Strict current-project quality, audit tests, and the full repository suite pass.
