# Script Guide

Detailed commands are registered as structured JSON under `config/registry/`. The generated `config/registry/registry.sqlite3` is a local FTS5 trigram retrieval index; JSON remains the only editable source of truth. Commands use `python skills/agents-md-generator/scripts/python/...` in this owner repository; external work folders resolve the installed skill runtime.

## Detect

Inspection is read-only and task rating through `detect/task_rating_gate.py` is advisory. The `default_conversation_language` profile field also governs Plan Mode output. Token review is available only for an explicit user request through `detect.token-usage-review`; its registered contract owns the default window, sessions-root boundary, and `codex_sessions_not_found` result.

## Render

Rendering reads project configuration, including `.agents/global-rule-overrides.json`, and preserves text outside managed blocks. If remote routing is enabled, unmatched tasks stop until AGENTS.md/profile is updated. Detailed preview, write, and migration forms belong to `render.render-agents`.

## Core Lifecycle

Keep only the outer lifecycle in ordinary documentation:

```text
python skills/agents-md-generator/scripts/python/docs/manage_docs.py resume-check .
python skills/agents-md-generator/scripts/python/docs/manage_docs.py memory-gate .
python skills/agents-md-generator/scripts/python/docs/manage_docs.py start-session . --input <session.json>
python skills/agents-md-generator/scripts/python/docs/manage_docs.py handoff . --input <handoff.json>
```

Directory mutation review belongs to registry instruction `dirs.manage`. A blocked review stops by default. The directory gate also requires one root `tests/`, with Python tests grouped one level below by function. The complete docs and memory surface, including all 24 `manage_docs.py` operations, belongs to `docs.operations`.

Document registration is separate and optional. Run registry instruction `registry.document-governance` only after an explicit user request; its lifecycle scans the skill Markdown, initializes governed JSON sources, checks drift and adjudications, then finalizes confirmed evidence. Disabled skills skip this gate without creating state. Markdown remains authoritative, and only uncertain adjudications return to the user for confirmation.

## Core Validation

The second retained group is the final validation chain:

```text
python skills/agents-md-generator/scripts/python/verify/quick_validate.py skills/agents-md-generator
python -m unittest discover -s tests -t . -v
python skills/agents-md-generator/scripts/python/verify/audit_skill.py skills/agents-md-generator
python skills/agents-md-generator/scripts/python/verify/verify_agents.py . --installed-skill-dir skills/agents-md-generator
python skills/agents-md-generator/scripts/python/docs/manage_docs.py verify .
python skills/agents-md-generator/scripts/python/verify/evaluate_skill.py skills/agents-md-generator .
```

The registered verification instructions are `verify.quick-validate`, `verify.audit-skill`, `verify.verify-agents`, and `verify.evaluate-skill`. Higher-risk extensions are discoverable through the registry rather than copied here.

## Verify

Use the validation chain above for ordinary completion. `verify/check_source_governance.py` enforces deterministic file-name syntax; `verify/review_governance.py --semantic-review <evidence.json>` owns the complementary functional-summary judgment plus dirty-worktree and committed-diff review. Registry instructions provide detailed parameters. Global baseline repair is registered under `docs.operations` as `sync-global-codex-agents`, and its advisory rating entry remains `detect/task_rating_gate.py`.

## Ask For More Usage

Use the read-only local query command for detailed syntax, examples, prerequisites, outputs, exit codes, relations, and risk warnings:

```text
python skills/agents-md-generator/scripts/python/registry/query_registry.py ask "<question>" [--kind <kind>] [--category <name>] [--limit 1..10] [--json]
```

Useful kinds are `command`, `workflow`, `document`, and `knowledge`; useful command categories are `detect`, `design`, `render`, `docs`, `dirs`, `verify`, `release`, and `registry`. The default kind is `command`, preserving the existing query behavior, and the default result limit is five. The query never executes a returned command; high-risk write operations remain discoverable but carry explicit warnings.

Exit codes are:

- `0`: one or more results.
- `1`: no match.
- `2`: invalid request.
- `3`: missing, corrupt, stale, schema-incompatible, or FTS-incompatible database.

After changing any JSON source, run registry instruction `registry.build`. Its default mode checks drift; `--write` atomically rebuilds SQLite. Never edit `registry.sqlite3` by hand.

## Compatibility

Compatibility wrappers may preserve old public entrypoints, but internal modules such as `render_entrypoints.py` map to the public `render_agents.py` instruction; removed evolution and experience commands remain invalid.

Release installation is exposed by registry instruction `release.install-skill`, whose public entrypoint is `release/install_skill.py`. Only a validated versioned release with `RELEASE_RECEIPT.json` is installable; source readiness does not authorize package, install, commit, push, or deployment.
