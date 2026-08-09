# source_governance_config.py decomposition plan

## Current Size
- Current file: `skills/agents-md-generator/scripts/python/verify/source_governance_config.py`
- Current size: `80533 bytes` from the latest `verify_agents.py . --installed-skill-dir skills/agents-md-generator` source-governance report.
- Reason for temporary exception: the file still centralizes default governance payload construction, legacy compatibility mapping, config validation, and profile-aware load/ensure helpers in one compatibility-heavy module.

## Split Boundaries
- Keep `load_global_rule_overrides(...)` and `ensure_global_rule_overrides_file(...)` as the stable compatibility facade, because many verifier, render, and docs-governance paths already import those names directly.
- Extract default payload builders and path/reference helpers into a defaults-focused helper module, covering source-governance defaults, script output defaults, implementation constraints, and config path/reference resolution.
- Extract validation-only logic into a focused helper module, covering coding behavior, script output policy, source governance, and top-level global override validation.
- Extract legacy migration and merge helpers into a compatibility-focused helper module, so historical profile migration stays isolated from current validation rules.
- Keep profile-to-implementation constraint projection close to the facade layer only if callers still need one stable import surface after the split.

## Target Files
- `skills/agents-md-generator/scripts/python/verify/source_governance_config.py`
- `skills/agents-md-generator/scripts/python/verify/source_governance_defaults.py`
- `skills/agents-md-generator/scripts/python/verify/source_governance_validation.py`
- `skills/agents-md-generator/scripts/python/verify/source_governance_compat.py`

## Exit Criteria
- `source_governance_config.py` drops back under the configured `65536` byte limit.
- Existing callers of `load_global_rule_overrides(...)`, `ensure_global_rule_overrides_file(...)`, and `implementation_constraints_from_profile(...)` keep the same payload shape and error semantics.
- The local governance config verifier still enforces `coding_behavior`, `script_output_policy`, `source_governance`, and `source_file_limits` with unchanged required fields.
- `python skills/agents-md-generator/scripts/python/verify/verify_agents.py . --installed-skill-dir skills/agents-md-generator` accepts the split without new source-governance or config-contract regressions.
- `python skills/agents-md-generator/scripts/python/verify/audit_skill.py skills/agents-md-generator` and `python skills/agents-md-generator/scripts/python/verify/evaluate_skill.py skills/agents-md-generator .` both pass after the split.
