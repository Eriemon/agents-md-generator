from __future__ import annotations

from typing import Any


def decision_request(
    kind: str,
    *,
    question: str,
    options: list[dict[str, Any]] | None = None,
    default: str | bool | None = None,
    required: bool = True,
    risk: str = "medium",
    next_action: str = "",
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_options = []
    for option in options or []:
        normalized_options.append(
            {
                "label": str(option.get("label", "")),
                "value": option.get("value"),
                "description": str(option.get("description", "")),
                "recommended": bool(option.get("recommended", False)),
            }
        )
    if default is None:
        for option in normalized_options:
            if option["recommended"]:
                default = option["value"]
                break
    return {
        "kind": kind,
        "required": required,
        "question": question,
        "options": normalized_options,
        "default": default,
        "risk": risk,
        "next_action": next_action,
        "context": context or {},
    }
