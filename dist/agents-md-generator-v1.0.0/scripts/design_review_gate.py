from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from design_profile_builder import build_profile
from design_questions import DESIGN_REVIEW_KEY, EXTRA_REQUIREMENTS_KEY, normalize_extra_requirements


DESIGN_REVIEW_REQUIRED_FIELDS = [
    "reviewer_type",
    "verdict",
    "findings",
    "required_user_confirmations",
    "reviewed_answers_hash",
    "reviewed_profile_hash",
    "review_summary",
]
def answers_without_design_review(answers: dict[str, Any]) -> dict[str, Any]:
    clean = {key: value for key, value in answers.items() if key != DESIGN_REVIEW_KEY}
    if EXTRA_REQUIREMENTS_KEY in clean:
        clean[EXTRA_REQUIREMENTS_KEY] = normalize_extra_requirements(clean.get(EXTRA_REQUIREMENTS_KEY))
    return clean


def stable_json_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def profile_for_design_review(project: Path, answers: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    clean_answers = answers_without_design_review(answers)
    profile, errors = build_profile(project, clean_answers)
    if errors:
        return None, errors
    assert profile is not None
    profile.pop(DESIGN_REVIEW_KEY, None)
    return profile, []


def design_review_hashes(project: Path, answers: dict[str, Any], profile: dict[str, Any] | None = None) -> dict[str, str]:
    clean_answers = answers_without_design_review(answers)
    profile_for_hash = profile
    if profile_for_hash is None:
        profile_for_hash, errors = profile_for_design_review(project, clean_answers)
        if errors:
            raise ValueError("; ".join(errors))
    assert profile_for_hash is not None
    profile_for_hash = {key: value for key, value in profile_for_hash.items() if key != DESIGN_REVIEW_KEY}
    return {
        "reviewed_answers_hash": stable_json_hash(clean_answers),
        "reviewed_profile_hash": stable_json_hash(profile_for_hash),
    }


def design_review_request(project: Path, answers: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    hashes = design_review_hashes(project, answers, profile)
    return {
        "kind": "design_review",
        "required_reviewer_type": "subagent",
        "required_fields": DESIGN_REVIEW_REQUIRED_FIELDS,
        "reviewed_answers_hash": hashes["reviewed_answers_hash"],
        "reviewed_profile_hash": hashes["reviewed_profile_hash"],
        "instructions": [
            "Spawn a new review subagent after final alignment.",
            "Ask the subagent to review the full answers and profile for design, gate, folder, version, branch, and user-confirmation risks.",
            "Submit the returned JSON as design_review; do not write .agents/agents-control.json until it approves with matching hashes and no pending user confirmations.",
        ],
    }


def validate_design_review(
    project: Path,
    answers: dict[str, Any],
    review: Any,
    profile: dict[str, Any] | None = None,
    require_approval: bool = True,
) -> list[str]:
    if not isinstance(review, dict):
        return ["design_review must be provided before --write"]
    errors: list[str] = []
    for field in DESIGN_REVIEW_REQUIRED_FIELDS:
        if field not in review:
            errors.append(f"design_review.{field} is required")
    if errors:
        return errors
    if review.get("reviewer_type") != "subagent":
        errors.append("design_review.reviewer_type must be subagent")
    verdict = str(review.get("verdict", "")).strip().lower()
    if verdict not in {"approve", "reject"}:
        errors.append("design_review.verdict must be approve or reject")
    if not isinstance(review.get("findings"), list):
        errors.append("design_review.findings must be a list")
    confirmations = review.get("required_user_confirmations")
    if not isinstance(confirmations, list):
        errors.append("design_review.required_user_confirmations must be a list")
        confirmations = []
    if not str(review.get("review_summary", "")).strip():
        errors.append("design_review.review_summary must be non-empty")
    try:
        hashes = design_review_hashes(project, answers, profile)
    except ValueError as exc:
        errors.append(f"design_review hash could not be computed: {exc}")
        hashes = {}
    if hashes and review.get("reviewed_answers_hash") != hashes["reviewed_answers_hash"]:
        errors.append("design_review.reviewed_answers_hash does not match current answers")
    if hashes and review.get("reviewed_profile_hash") != hashes["reviewed_profile_hash"]:
        errors.append("design_review.reviewed_profile_hash does not match current profile")
    if require_approval and verdict == "reject":
        errors.append("design_review verdict reject requires rework before --write")
    if require_approval and confirmations:
        errors.append("design_review.required_user_confirmations must be empty before --write")
    return errors


def design_review_requires_rework(review: dict[str, Any]) -> bool:
    confirmations = review.get("required_user_confirmations")
    return str(review.get("verdict", "")).strip().lower() == "reject" or (isinstance(confirmations, list) and bool(confirmations))
