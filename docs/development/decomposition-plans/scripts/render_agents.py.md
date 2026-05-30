## Current Size

`scripts/render_agents.py` is above the configured 1000-line threshold because it currently combines template loading, section rendering, profile-driven contract assembly, and write-time preserved-content merge logic in one renderer.

## Split Boundaries

Future decomposition should separate:

- template loading and evolution guidance lookup
- contract and section rendering helpers
- root/scoped write orchestration plus preserved-content merge logic

The current file remains the single renderer until those seams are extracted safely.

## Target Files

Planned target modules:

- `scripts/render_agents.py` as the top-level CLI and orchestration entrypoint
- `scripts/render_agents_sections.py` for profile-to-section rendering helpers
- `scripts/render_agents_templates.py` for template lookup and managed-block composition

## Exit Criteria

This decomposition plan is complete when:

- `scripts/render_agents.py` is back under the configured line limit
- rendering helpers are split by responsibility without duplicating policy logic
- dry-run and `--write` output remain behaviorally identical for existing workflows
