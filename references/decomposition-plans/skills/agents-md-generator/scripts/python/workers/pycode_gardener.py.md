# pycode_gardener.py decomposition plan

## Current Size

- Measured source: `skills/agents-md-generator/scripts/python/workers/pycode_gardener.py`.
- The module is above the configured 64 KiB UTF-8 source budget and remains a temporary facade until the read-only gardener workflow is split.

## Split Boundaries

- The current module owns event dispatch status, immutable snapshot selection, Git object reads, path filtering, AST/Markdown finding extraction, report assembly, CLI parsing, and the public `main()` contract.
- A snapshot boundary shard should own trigger validation, Git ref/object reads, regular-file checks, link-component rejection, snapshot manifests, and byte/hash receipts.
- A source-analysis shard should own AST definition traversal, export discovery, candidate metadata, Python finding extraction, Markdown finding extraction, and qualified-name construction.
- A report boundary shard should own scope payloads, blocked/empty reports, diagnostic schema assembly, and CLI serialization; it must not acquire broader file-system or Git authority.

## Target Files

- Facade retained: `skills/agents-md-generator/scripts/python/workers/pycode_gardener.py`.
- Snapshot destination: `skills/agents-md-generator/scripts/python/workers/gardener_snapshot.py`, including Git object reads, path safety, candidate filtering, and immutable snapshot evidence.
- Analysis destination: `skills/agents-md-generator/scripts/python/workers/gardener_analysis.py`, including AST and Markdown source findings.
- Report destination: `skills/agents-md-generator/scripts/python/workers/gardener_report.py`, including report contracts and CLI result formatting.
- The facade must preserve the public functions used by `manage_workers.py` and keep the read-only worker boundary explicit.

## Exit Criteria

- The same trigger, commit/base validation, forbidden-path filtering, symlink rejection, snapshot digest, finding locations, and report schema remain behaviorally identical.
- The canonical tester reruns the worker lifecycle and source-finding scenarios after the extraction; the reviewer rechecks the approved plan at CORRECTION and FINAL.
- The aggregate facade and each destination module remain below the configured source budget, or each oversized destination receives its own valid plan.
- No worker shard gains write, delete, remote upload, or test-tree mutation authority as a side effect of the split.
