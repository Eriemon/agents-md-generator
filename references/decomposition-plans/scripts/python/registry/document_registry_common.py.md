# document_registry_common.py decomposition plan

## Current Size

- Current file: `skills/agents-md-generator/scripts/python/registry/document_registry_common.py`
- Current size: `69311 bytes`.
- Temporary exception: document scanning, declared registry layout, migration review, initialization, and finalization remain in one compatibility module.

## Split Boundaries

- Keep public orchestration functions and existing import compatibility in `document_registry_common.py`.
- Extract manifest-driven owner layout and schema-template loading into a focused layout helper.
- Extract initial governance payload construction and migration review projection into an initialization helper.
- Keep scan primitives and finalized document validation separated from filesystem writes.

## Target Files

- `skills/agents-md-generator/scripts/python/registry/document_registry_common.py`
- `skills/agents-md-generator/scripts/python/registry/document_registry_layout.py`
- `skills/agents-md-generator/scripts/python/registry/document_registry_initialization.py`

## Exit Criteria

- The current module drops below `65536` bytes.
- Public document-governance CLI behavior and import contracts remain backward compatible.
- Manifest role paths and schema paths remain filename-independent and registry-root safe.
- Strict current-project quality, registry tests, audit, and full `python -m pytest -q` pass.
