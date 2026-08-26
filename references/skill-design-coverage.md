# Skill Design Coverage

This file maps design patterns to their authoritative implementation. It is a map, not a manual.

## Patterns

| Pattern | Use |
|---|---|
| Tool Wrapper | Put deterministic or fragile operations in `scripts/` |
| Generator | Keep stable output shapes in `assets/` templates |
| Reviewer | Keep criteria in `references/` and automate deterministic checks |
| Inversion | Ask for intent that repository facts cannot reveal |
| Pipeline | Run route, inspect, design, generate, and verify in order |

Patterns may be combined; gate conditions control progress: do not skip steps or proceed when a required step fails.

## Progressive Disclosure

- Use progressive disclosure: Map, not manual.
- `SKILL.md` owns trigger, stop lines, workflow order, and safety boundaries.
- `references/script-guide.md` owns command syntax; `references/review-checklist.md` owns review evidence.
- `.agents/agents-control.json` owns project remote routes; `.agents/global-rule-overrides.json` is the local JSON governance config for configurable coding/output rules.
- The configured global instruction file owns cross-repository defaults; project and scoped files own narrower facts.
- Generated documents point to owners instead of copying their full policy.
- Distill saved HTML into decision-changing rules. Do not copy downloaded CSS or JS.

## Contract Coverage

- `default_conversation_language` locks natural-language replies to it unless the user switches languages.
- `use_remote_server` is explicit. Routes include primary/fallback checks, an automatic fallback gate, and an unmatched-task blocking gate.
- Remote structure remains separate from remote server enablement. Remote mutation governance for all actions validates both endpoints and protected path classes.
- The root-level file whitelist uses `allowed_root_files`; structure repair requires `confirm-structure-fix`.
- Codebase-memory requires root-only persistent evidence and a ready full index.
- Coding Behavior Baseline language skill routing comes from `coding_behavior.language_skill_routing`: `shared` is rendered once, Python belongs to `readable-python-generator`, and scripts belong to `readable-script-generator`.
- Memory summaries are bounded retrieval views; SQLite and JSONL preserve full history.
- The Documentation Governance Contract points current context to `docs/handoff/HANDOFF.md`, durable context to `docs/memory/`, and directory changes to `docs/dir_manager/`.
- Tester failure receipts are enforced by the worker dispatch validator, rendered tester rule, profile handshake, and the `tester_failure_receipt_contract` eval; a bare failure count cannot be recorded.
- The verification loop uses `python skills/agents-md-generator/scripts/python/verify/quick_validate.py skills/agents-md-generator`, audit, AGENTS verification, docs verification, and evaluation.

## Review Gate

Do not use any non-testing subagent by default. Only the user's proactive and explicit request in the current task that names the role or purpose authorizes one; a generic multi-agent request, write intent, governance risk, complexity, ratings, and agent judgment do not. Use exactly three authorized non-testing subagents when the user omits the count, honor an explicit count, and never carry authorization into another task. Explicitly requested review evidence follows `SKILL.md` and `references/review-checklist.md`. Work with an executable test surface uses one isolated `TESTER` with exclusive ownership of `tests/**`; pure read-only/planning work and documentation-only changes without a test surface do not require one. Release and installation are separate scopes and never follow automatically from source readiness.
