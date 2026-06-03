from __future__ import annotations

import argparse
import json
from typing import Any


SUPPORTED_RULE_SETS = [
    "a-philosophy-of-software-design",
    "clean-architecture",
    "clean-code",
    "code-complete",
    "designing-data-intensive-applications",
    "domain-driven-design",
    "domain-driven-design-distilled",
    "implementing-domain-driven-design",
    "patterns-of-enterprise-application-architecture",
    "refactoring",
    "refactoring-guru",
    "release-it",
    "the-pragmatic-programmer",
    "working-effectively-with-legacy-code",
]

ALLOWED_MODES = ["mini", "nano"]
ALLOWED_SCOPES = ["project-baseline", "scoped", "on-demand"]

TASK_RECOMMENDATIONS = {
    "architecture": {
        "primary": "a-philosophy-of-software-design",
        "reason": "use when complexity, module boundaries, and abstraction depth are the main risk",
    },
    "clean-code": {
        "primary": "clean-code",
        "reason": "use when local readability, naming, function shape, and maintainability are the main risk",
    },
    "data": {
        "primary": "designing-data-intensive-applications",
        "reason": "use when source of truth, consistency, events, streams, storage, or schema evolution dominate",
    },
    "domain": {
        "primary": "domain-driven-design",
        "reason": "use when business meaning, bounded contexts, ubiquitous language, and model boundaries dominate",
    },
    "legacy": {
        "primary": "working-effectively-with-legacy-code",
        "reason": "use when behavior is poorly characterized and changes need tests before cleanup",
    },
    "refactor": {
        "primary": "refactoring",
        "reason": "use when preserving behavior while changing structure is the main work",
    },
    "reliability": {
        "primary": "release-it",
        "reason": "use when production failure semantics, bounds, retries, recovery, and operations dominate",
    },
}

CONFLICT_PAIRS = {
    frozenset({"domain-driven-design", "patterns-of-enterprise-application-architecture"}): "domain model pressure conflicts with transaction-script/table-module pressure when both are equal active guidance",
    frozenset({"implementing-domain-driven-design", "patterns-of-enterprise-application-architecture"}): "implementation-heavy DDD conflicts with enterprise-application pattern pressure when both arbitrate the same model layer",
}

OVERLAP_PAIRS = {
    frozenset({"a-philosophy-of-software-design", "clean-code"}): "both push local code-shape simplification; choose one primary",
    frozenset({"clean-code", "code-complete"}): "both cover local construction discipline; choose one primary",
    frozenset({"clean-code", "the-pragmatic-programmer"}): "both cover broad engineering hygiene; choose one primary",
    frozenset({"code-complete", "the-pragmatic-programmer"}): "both cover broad construction practice; choose one primary",
    frozenset({"domain-driven-design", "domain-driven-design-distilled"}): "distilled DDD is a narrower substitute for full DDD pressure",
    frozenset({"domain-driven-design", "implementing-domain-driven-design"}): "implementation DDD overlaps with full DDD model guidance",
    frozenset({"domain-driven-design-distilled", "implementing-domain-driven-design"}): "both target DDD implementation choices at different depths",
    frozenset({"refactoring", "refactoring-guru"}): "both target refactoring choices; choose one primary",
}


def emit_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def contract(primary: str, mode: str, scope: str, notes: str = "") -> dict[str, Any]:
    return {
        "primary": primary,
        "mode": mode,
        "scope": scope,
        "notes": notes,
        "full_reference_allowed_in_agents": False,
        "compatibility_policy": "one primary active rule set; use secondary rule sets only as scoped or on-demand guidance",
        "compression_policy": "decision-equivalent compression: keep decision-changing, trigger, tradeoff, and checklist rules",
    }


def validate(primary: str, secondaries: list[str], mode: str, scope: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if primary not in SUPPORTED_RULE_SETS:
        errors.append(f"unknown primary rule set: {primary}")
    if mode == "full":
        errors.append("full book rules must stay reference-only and must not be pasted into AGENTS.md")
    elif mode not in ALLOWED_MODES:
        errors.append("mode must be mini or nano")
    if scope not in ALLOWED_SCOPES:
        errors.append("scope must be project-baseline, scoped, or on-demand")

    for secondary in secondaries:
        if secondary not in SUPPORTED_RULE_SETS:
            errors.append(f"unknown secondary rule set: {secondary}")
            continue
        pair = frozenset({primary, secondary})
        if pair in CONFLICT_PAIRS:
            errors.append(f"conflicting active rule sets: {primary} + {secondary}: {CONFLICT_PAIRS[pair]}")
        elif pair in OVERLAP_PAIRS:
            warnings.append(f"overlapping rule sets: {primary} + {secondary}: {OVERLAP_PAIRS[pair]}")
    return errors, warnings


def list_payload() -> dict[str, Any]:
    return {
        "supported_rule_sets": SUPPORTED_RULE_SETS,
        "allowed_modes": ALLOWED_MODES,
        "allowed_scopes": ALLOWED_SCOPES,
        "task_recommendations": TASK_RECOMMENDATIONS,
        "conflict_pairs": [" + ".join(sorted(pair)) for pair in sorted(CONFLICT_PAIRS, key=lambda item: sorted(item))],
        "overlap_pairs": [" + ".join(sorted(pair)) for pair in sorted(OVERLAP_PAIRS, key=lambda item: sorted(item))],
        "policy": {
            "primary": "choose exactly one equal active rule set",
            "full": "reference-only",
            "compression": "decision-equivalent, not sentence-equivalent",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Select and validate a book-derived engineering rule contract.")
    parser.add_argument("--list", action="store_true", help="List supported rule sets, modes, scopes, and task recommendations.")
    parser.add_argument("--task", choices=sorted(TASK_RECOMMENDATIONS), default=None, help="Recommend a primary rule set for a task type.")
    parser.add_argument("--primary", default=None, help="Primary active rule set.")
    parser.add_argument("--secondary", action="append", default=[], help="Secondary rule set to check for equal-active conflicts.")
    parser.add_argument("--mode", default="mini", help="Compression mode: mini or nano. full is rejected for AGENTS.md.")
    parser.add_argument("--scope", default="on-demand", help="Scope: project-baseline, scoped, or on-demand.")
    parser.add_argument("--notes", default="", help="Short local notes to carry into the profile.")
    args = parser.parse_args()

    if args.list:
        emit_json(list_payload())
        return

    recommended = TASK_RECOMMENDATIONS.get(args.task or "")
    primary = normalize(args.primary) or (recommended["primary"] if recommended else "")
    mode = normalize(args.mode)
    scope = normalize(args.scope)
    secondaries = [normalize(item) for item in args.secondary if normalize(item)]

    if not primary:
        emit_json({"errors": ["choose --primary or --task"], "warnings": []})
        raise SystemExit(1)

    errors, warnings = validate(primary, secondaries, mode, scope)
    payload = {
        "contract": contract(primary, mode, scope, args.notes.strip()),
        "errors": errors,
        "recommendation": recommended,
        "secondary_rule_sets": secondaries,
        "warnings": warnings,
    }
    emit_json(payload)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
