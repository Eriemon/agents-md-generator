# Book Rules Coverage

This skill does not copy whole book-derived rule sets into generated AGENTS.md files. It integrates the reusable mechanism: choose one primary rule set, select the smallest useful compression, keep full material reference-only, and render only decision-changing rules or policies.

Use `scripts/select_engineering_rules.py` to list supported rule sets, recommend a primary rule set from task type, and detect known conflict or overlap before writing the design profile.

## Coverage Policy

| Source idea | Integrated behavior |
|-------------|---------------------|
| `mini` as the normal working size | `engineering_rule_mode=mini` is accepted for a chosen primary rule set |
| `nano` as the tiny fallback | `engineering_rule_mode=nano` is accepted for tight always-on budgets |
| `full` as audit/reference material | `full` is rejected for generated AGENTS.md output and treated as reference-only |
| Start with one primary rule set | `engineering_rule_primary` accepts exactly one active rule set |
| Prefer scoped or on-demand loading | `engineering_rule_scope` records project-baseline, scoped, or on-demand use |
| Avoid active conflicts | The rendered contract says one primary rule set; other rule sets stay scoped or on-demand |
| decision-equivalent compression | Generated output keeps rules that change decisions, triggers, tradeoffs, and final checks |
| traceability | The profile records chosen rule set, mode, scope, and notes so the AGENTS.md decision is auditable |

## Allowed Primary Rule Sets

- `a-philosophy-of-software-design`
- `clean-architecture`
- `clean-code`
- `code-complete`
- `designing-data-intensive-applications`
- `domain-driven-design`
- `domain-driven-design-distilled`
- `implementing-domain-driven-design`
- `patterns-of-enterprise-application-architecture`
- `refactoring`
- `refactoring-guru`
- `release-it`
- `the-pragmatic-programmer`
- `working-effectively-with-legacy-code`

## Deliberate Non-Copy Decisions

- Do not paste full rule files into AGENTS.md; full material is too large for always-on project instructions.
- Do not activate several equal book rule sets at once; overlap and conflicts dilute project-specific control.
- Do not turn AGENTS.md into a book summary; use the directory contract, release contract, and engineering rule contract to guide action.
- Do not preserve prose for its own sake; keep only rules that affect architecture, refactoring, failure handling, data ownership, domain boundaries, review, tests, or repeated implementation choices.

## Review Questions

- Is there exactly one primary active rule set?
- Is the mode `mini` or `nano`, never `full`?
- Is the scope explicit: project-baseline, scoped, or on-demand?
- Does the generated AGENTS.md state that full material is reference-only?
- Are rules phrased as triggers, tradeoff decisions, or final checks instead of long explanations?
