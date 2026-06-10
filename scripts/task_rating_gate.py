from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import resolve_project


DIFFICULTY_ORDER = ["simple", "normal", "hard", "hell", "nightmare"]
SCALE_ORDER = ["micro", "small", "medium", "large", "project"]

DIFFICULTY_ALIASES = {
    "simple": ["simple", "easy", "trivial", "简单", "輕量", "轻量"],
    "normal": ["normal", "ordinary", "standard", "普通", "一般"],
    "hard": ["hard", "difficult", "困难", "困難"],
    "hell": ["hell", "地狱", "地獄"],
    "nightmare": ["nightmare", "噩梦", "噩夢"],
}
SCALE_ALIASES = {
    "micro": ["micro", "tiny", "one-line", "微型", "极小", "很小"],
    "small": ["small", "小型", "小"],
    "medium": ["medium", "中型", "中等"],
    "large": ["large", "big", "大型", "大"],
    "project": ["project", "program", "项目级", "專案級", "工程级"],
}

COMPLEX_KEYWORDS = {
    "architecture",
    "架构",
    "架構",
    "migration",
    "migrate",
    "迁移",
    "release",
    "发布",
    "remote",
    "远程",
    "debugging",
    "debug",
    "调试",
    "complex",
    "复杂",
    "多模块",
    "multi-module",
    "multiple modules",
    "multiple services",
    "多阶段",
    "multi-stage",
    "refactor",
    "重构",
    "重構",
    "breaking change",
    "public api",
    "schema",
    "database",
    "deployment",
    "部署",
}
UNCLEAR_KEYWORDS = {
    "unclear",
    "unknown",
    "not sure",
    "maybe",
    "不确定",
    "不明",
    "需求不清",
    "看情况",
}
SIMPLE_KEYWORDS = {
    "readme",
    "docs",
    "documentation",
    "wording",
    "typo",
    "comment",
    "rename",
    "文档",
    "说明",
    "错别字",
}


def norm_text(value: str) -> str:
    return value.casefold()


def alias_pattern(alias: str) -> str:
    if re.search(r"[A-Za-z0-9_-]", alias):
        return rf"\b{re.escape(alias.casefold())}\b"
    return re.escape(alias.casefold())


def find_explicit_value(text: str, aliases: dict[str, list[str]], labels: tuple[str, ...]) -> str:
    lowered = norm_text(text)
    label_pattern = "|".join(re.escape(label.casefold()) for label in labels)
    for canonical, names in aliases.items():
        for name in names:
            pattern = rf"(?:{label_pattern})\s*(?:[:=：]|是|为|為)\s*{alias_pattern(name)}"
            if re.search(pattern, lowered):
                return canonical
    return ""


def find_contextual_rating(text: str, aliases: dict[str, list[str]], labels: tuple[str, ...]) -> str:
    lowered = norm_text(text)
    label_pattern = "|".join(re.escape(label.casefold()) for label in labels)
    for canonical, names in aliases.items():
        for name in names:
            alias = alias_pattern(name)
            patterns = (
                rf"{alias}\s*(?:级|級|等级|等級|{label_pattern})",
                rf"(?:任务|task|问题|problem)\s*(?:是|为|為|属于|屬於|算)?\s*{alias}",
            )
            if any(re.search(pattern, lowered) for pattern in patterns):
                return canonical
    return ""


def count_matches(text: str, keywords: set[str]) -> int:
    lowered = norm_text(text)
    return sum(1 for keyword in keywords if keyword.casefold() in lowered)


def max_level(current: str, candidate: str, order: list[str]) -> str:
    return candidate if order.index(candidate) > order.index(current) else current


def infer_from_text(task_text: str, context_summary: str = "") -> dict[str, Any]:
    combined = " ".join(part for part in [task_text, context_summary] if part)
    explicit_difficulty = find_explicit_value(combined, DIFFICULTY_ALIASES, ("difficulty", "难度", "難度"))
    explicit_scale = find_explicit_value(combined, SCALE_ALIASES, ("scale", "规模", "規模"))
    contextual_difficulty = "" if explicit_difficulty else find_contextual_rating(combined, DIFFICULTY_ALIASES, ("difficulty", "难度", "難度"))
    contextual_scale = "" if explicit_scale else find_contextual_rating(combined, SCALE_ALIASES, ("scale", "规模", "規模"))
    user_difficulty = explicit_difficulty or contextual_difficulty
    user_scale = explicit_scale or contextual_scale
    difficulty = user_difficulty or "normal"
    scale = user_scale or "small"
    reasons: list[str] = []

    if explicit_difficulty or explicit_scale:
        reasons.append("explicit user rating found; do not ask again")
    elif user_difficulty or user_scale:
        reasons.append("contextual user rating found; do not ask again")

    complex_hits = count_matches(combined, COMPLEX_KEYWORDS)
    unclear_hits = count_matches(combined, UNCLEAR_KEYWORDS)
    simple_hits = count_matches(combined, SIMPLE_KEYWORDS)

    if complex_hits >= 6:
        if not user_difficulty:
            difficulty = max_level(difficulty, "hell", DIFFICULTY_ORDER)
        if not user_scale:
            scale = max_level(scale, "project", SCALE_ORDER)
        reasons.append("many complex-task signals detected")
    elif complex_hits >= 3:
        if not user_difficulty:
            difficulty = max_level(difficulty, "hard", DIFFICULTY_ORDER)
        if not user_scale:
            scale = max_level(scale, "large", SCALE_ORDER)
        reasons.append("multiple complex-task signals detected")
    elif simple_hits and complex_hits == 0 and unclear_hits == 0:
        difficulty = user_difficulty or "simple"
        scale = user_scale or "micro"
        reasons.append("single low-risk documentation or wording task")

    if unclear_hits:
        reasons.append("unclear requirement signal detected")

    if not reasons:
        reasons.append("no high-risk task signals detected")

    user_rating = bool(user_difficulty or user_scale)
    ask_user_rating = not user_rating and (
        unclear_hits > 0
        or complex_hits >= 3
        or difficulty in {"hard", "hell", "nightmare"}
        or scale in {"large", "project"}
    )

    confidence = "high" if user_rating or (simple_hits and complex_hits == 0 and unclear_hits == 0) else "medium"
    if ask_user_rating and unclear_hits:
        confidence = "low"

    actions = ["inspect existing patterns before editing"]
    if ask_user_rating:
        actions.append("ask user to confirm difficulty and scale")
    if difficulty in {"hell", "nightmare"} or scale == "project":
        actions.append("reuse-first research")
        actions.append("record candidate tools, libraries, templates, open-source projects, fit, risks, and rejection reasons")
    if difficulty == "nightmare" or scale == "project":
        actions.append("split into multi-stage project plan")
        actions.append("keep the project plan adjustable when the user changes requirements")

    return {
        "ask_user_rating": ask_user_rating,
        "inferred_difficulty": difficulty,
        "inferred_scale": scale,
        "confidence": confidence,
        "reasons": reasons,
        "recommended_actions": actions,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Heuristically decide whether a task needs user difficulty/scale rating.")
    parser.add_argument("--project", default=".", help="Current project root. Used for path validation and future context hooks.")
    parser.add_argument("--task-text", required=True, help="User task text to classify.")
    parser.add_argument("--context-summary", default="", help="Optional concise known context for the task.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON. Text mode also emits JSON for stable automation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project = resolve_project(args.project)
    payload = infer_from_text(args.task_text, args.context_summary)
    payload["project"] = str(project)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
