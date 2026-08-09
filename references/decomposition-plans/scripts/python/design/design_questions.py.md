# design_questions.py decomposition plan

## Current Size
- Current file: `skills/agents-md-generator/scripts/python/design/design_questions.py`
- Current size: `71131 bytes`.
- Temporary exception: shared, skill, engineering, directory, and takeover question contracts remain centralized.

## Split Boundaries
- Keep public question selection and compatibility exports in the current module.
- Extract skill-development question definitions into a dedicated module.
- Extract engineering and directory-contract questions into dedicated modules.
- Preserve question identifiers, ordering, required flags, and answer normalization.

## Target Files
- `skills/agents-md-generator/scripts/python/design/design_questions.py`
- `skills/agents-md-generator/scripts/python/design/design_questions_skill.py`
- `skills/agents-md-generator/scripts/python/design/design_questions_engineering.py`
- `skills/agents-md-generator/scripts/python/design/design_questions_directories.py`

## Exit Criteria
- The current module drops below `65536` bytes.
- Design interview, takeover, profile, and remote-policy tests retain exact question contracts.
- Strict current-project quality and full design tests pass after extraction.
