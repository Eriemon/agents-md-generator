from __future__ import annotations

# 分类脚本可从任意任务目录直接执行，这里补齐兄弟任务模块路径。
import sys
from pathlib import Path

_scripts_python_root = Path(__file__).resolve().parents[1]
for _task_dir in _scripts_python_root.iterdir():
    if _task_dir.is_dir():
        _task_path = str(_task_dir)
        if _task_path not in sys.path:
            sys.path.insert(0, _task_path)

# 导入 脚本治理 所需的依赖模块。
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断
from agents_common import resolve_project


# 保留 DIFFICULTY ORDER 中间值，支撑 模块入口 的当前计算步骤。
DIFFICULTY_ORDER = ["simple", "normal", "hard", "hell", "nightmare"]  # DIFFICULTY ORDER 用于本步治理判断

# 保留 SCALE ORDER 中间值，支撑 模块入口 的当前计算步骤。
SCALE_ORDER = ["micro", "small", "medium", "large", "project"]  # SCALE ORDER 用于本步治理判断

# 保留 DIFFICULTY ALIASES 中间值，支撑 模块入口 的当前计算步骤。
DIFFICULTY_ALIASES = {  # DIFFICULTY ALIASES 用于本步治理判断
    "simple": ["simple", "easy", "trivial", "简单", "輕量", "轻量"],  # DIFFICULTY ALIASES 用于本步治理判断
    "normal": ["normal", "ordinary", "standard", "普通", "一般"],  # DIFFICULTY ALIASES 用于本步治理判断
    "hard": ["hard", "difficult", "困难", "困難"],  # DIFFICULTY ALIASES 用于本步治理判断
    "hell": ["hell", "地狱", "地獄"],  # DIFFICULTY ALIASES 用于本步治理判断
    "nightmare": ["nightmare", "噩梦", "噩夢"],  # DIFFICULTY ALIASES 用于本步治理判断
}

# 保留 SCALE ALIASES 中间值，支撑 模块入口 的当前计算步骤。
SCALE_ALIASES = {  # SCALE ALIASES 用于本步治理判断
    "micro": ["micro", "tiny", "one-line", "微型", "极小", "很小"],  # SCALE ALIASES 用于本步治理判断
    "small": ["small", "小型", "小"],  # SCALE ALIASES 用于本步治理判断
    "medium": ["medium", "中型", "中等"],  # SCALE ALIASES 用于本步治理判断
    "large": ["large", "big", "大型", "大"],  # SCALE ALIASES 用于本步治理判断
    "project": ["project", "program", "项目级", "專案級", "工程级"],  # SCALE ALIASES 用于本步治理判断
}

# 保留 COMPLEX KEYWORDS 中间值，支撑 模块入口 的当前计算步骤。
COMPLEX_KEYWORDS = {  # COMPLEX KEYWORDS 用于本步治理判断
    "architecture",  # COMPLEX KEYWORDS 用于本步治理判断
    "架构",  # COMPLEX KEYWORDS 用于本步治理判断
    "架構",  # COMPLEX KEYWORDS 用于本步治理判断
    "migration",  # COMPLEX KEYWORDS 用于本步治理判断
    "migrate",  # COMPLEX KEYWORDS 用于本步治理判断
    "迁移",  # COMPLEX KEYWORDS 用于本步治理判断
    "release",  # COMPLEX KEYWORDS 用于本步治理判断
    "发布",  # COMPLEX KEYWORDS 用于本步治理判断
    "remote",  # COMPLEX KEYWORDS 用于本步治理判断
    "远程",  # COMPLEX KEYWORDS 用于本步治理判断
    "debugging",  # COMPLEX KEYWORDS 用于本步治理判断
    "debug",  # COMPLEX KEYWORDS 用于本步治理判断
    "调试",  # COMPLEX KEYWORDS 用于本步治理判断
    "complex",  # COMPLEX KEYWORDS 用于本步治理判断
    "复杂",  # COMPLEX KEYWORDS 用于本步治理判断
    "多模块",  # COMPLEX KEYWORDS 用于本步治理判断
    "multi-module",  # COMPLEX KEYWORDS 用于本步治理判断
    "multiple modules",  # COMPLEX KEYWORDS 用于本步治理判断
    "multiple services",  # COMPLEX KEYWORDS 用于本步治理判断
    "多阶段",  # COMPLEX KEYWORDS 用于本步治理判断
    "multi-stage",  # COMPLEX KEYWORDS 用于本步治理判断
    "refactor",  # COMPLEX KEYWORDS 用于本步治理判断
    "重构",  # COMPLEX KEYWORDS 用于本步治理判断
    "重構",  # COMPLEX KEYWORDS 用于本步治理判断
    "breaking change",  # COMPLEX KEYWORDS 用于本步治理判断
    "public api",  # COMPLEX KEYWORDS 用于本步治理判断
    "schema",  # COMPLEX KEYWORDS 用于本步治理判断
    "database",  # COMPLEX KEYWORDS 用于本步治理判断
    "deployment",  # COMPLEX KEYWORDS 用于本步治理判断
    "部署",  # COMPLEX KEYWORDS 用于本步治理判断
}

# 保留 UNCLEAR KEYWORDS 中间值，支撑 模块入口 的当前计算步骤。
UNCLEAR_KEYWORDS = {  # UNCLEAR KEYWORDS 用于本步治理判断
    "unclear",  # UNCLEAR KEYWORDS 用于本步治理判断
    "unknown",  # UNCLEAR KEYWORDS 用于本步治理判断
    "not sure",  # UNCLEAR KEYWORDS 用于本步治理判断
    "maybe",  # UNCLEAR KEYWORDS 用于本步治理判断
    "不确定",  # UNCLEAR KEYWORDS 用于本步治理判断
    "不明",  # UNCLEAR KEYWORDS 用于本步治理判断
    "需求不清",  # UNCLEAR KEYWORDS 用于本步治理判断
    "看情况",  # UNCLEAR KEYWORDS 用于本步治理判断
}

# 保留 SIMPLE KEYWORDS 中间值，支撑 模块入口 的当前计算步骤。
SIMPLE_KEYWORDS = {  # SIMPLE KEYWORDS 用于本步治理判断
    "readme",  # SIMPLE KEYWORDS 用于本步治理判断
    "docs",  # SIMPLE KEYWORDS 用于本步治理判断
    "documentation",  # SIMPLE KEYWORDS 用于本步治理判断
    "wording",  # SIMPLE KEYWORDS 用于本步治理判断
    "typo",  # SIMPLE KEYWORDS 用于本步治理判断
    "comment",  # SIMPLE KEYWORDS 用于本步治理判断
    "rename",  # SIMPLE KEYWORDS 用于本步治理判断
    "文档",  # SIMPLE KEYWORDS 用于本步治理判断
    "说明",  # SIMPLE KEYWORDS 用于本步治理判断
    "错别字",  # SIMPLE KEYWORDS 用于本步治理判断
}


# 定义 norm_text 的脚本治理处理入口。
def norm_text(value: str) -> str:

    # 返回 norm_text 已整理完成的调用载荷。
    return value.casefold()


# 定义 alias_pattern 的脚本治理处理入口。
def alias_pattern(alias: str) -> str:

    # 检查 alias_pattern 的当前条件是否需要进入专门分支。
    if re.search(r"[A-Za-z0-9_-]", alias):

        # 返回 alias_pattern 已整理完成的调用载荷。
        return rf"\b{re.escape(alias.casefold())}\b"

    # 返回 alias_pattern 已整理完成的调用载荷。
    return re.escape(alias.casefold())


# 定义 find_explicit_value 的脚本治理处理入口。
def find_explicit_value(text: str, aliases: dict[str, list[str]], labels: tuple[str, ...]) -> str:

    # 保留 lowered 中间值，支撑 find_explicit_value 的当前计算步骤。
    str_lowered = norm_text(text)  # lowered 用于本步治理判断

    # 保留 label pattern 中间值，支撑 find_explicit_value 的当前计算步骤。
    label_pattern = "|".join(re.escape(label.casefold()) for label in labels)  # label pattern 用于本步治理判断

    # 逐项推进 find_explicit_value 的候选项检查。
    for canonical, names in aliases.items():

        # 逐项推进 find_explicit_value 的候选项检查。
        for name in names:

            # 保留 pattern 中间值，支撑 find_explicit_value 的当前计算步骤。
            pattern = rf"(?:{label_pattern})\s*(?:[:=：]|是|为|為)\s*{alias_pattern(name)}"  # pattern 用于本步治理判断

            # 检查 find_explicit_value 的当前条件是否需要进入专门分支。
            if re.search(pattern, str_lowered):

                # 返回 find_explicit_value 已整理完成的调用载荷。
                return canonical

    # 返回 find_explicit_value 已整理完成的调用载荷。
    return ""


# 定义 find_contextual_rating 的脚本治理处理入口。
def find_contextual_rating(text: str, aliases: dict[str, list[str]], labels: tuple[str, ...]) -> str:

    # 保留 lowered 中间值，支撑 find_contextual_rating 的当前计算步骤。
    str_lowered = norm_text(text)  # lowered 用于本步治理判断

    # 保留 label pattern 中间值，支撑 find_contextual_rating 的当前计算步骤。
    label_pattern = "|".join(re.escape(label.casefold()) for label in labels)  # label pattern 用于本步治理判断

    # 逐项推进 find_contextual_rating 的候选项检查。
    for canonical, names in aliases.items():

        # 逐项推进 find_contextual_rating 的候选项检查。
        for name in names:

            # 收集 alias 条目，保持 find_contextual_rating 的处理顺序稳定。
            str_alias = alias_pattern(name)  # alias 用于本步治理判断

            # 收集 patterns 条目，保持 find_contextual_rating 的处理顺序稳定。
            tuple_patterns = (  # patterns 用于本步治理判断
                rf"{str_alias}\s*(?:级|級|等级|等級|{label_pattern})",  # patterns 用于本步治理判断
                rf"(?:任务|task|问题|problem)\s*(?:是|为|為|属于|屬於|算)?\s*{str_alias}",  # patterns 用于本步治理判断
            )

            # 检查 find_contextual_rating 的当前条件是否需要进入专门分支。
            if any(re.search(pattern, str_lowered) for pattern in tuple_patterns):

                # 返回 find_contextual_rating 已整理完成的调用载荷。
                return canonical

    # 返回 find_contextual_rating 已整理完成的调用载荷。
    return ""


# 定义 count_matches 的脚本治理处理入口。
def count_matches(text: str, keywords: set[str]) -> int:

    # 保留 lowered 中间值，支撑 count_matches 的当前计算步骤。
    str_lowered = norm_text(text)  # lowered 用于本步治理判断

    # 返回 count_matches 已整理完成的调用载荷。
    return sum(1 for keyword in keywords if keyword.casefold() in str_lowered)


# 定义 max_level 的脚本治理处理入口。
def max_level(current: str, candidate: str, order: list[str]) -> str:

    # 返回 max_level 已整理完成的调用载荷。
    return candidate if order.index(candidate) > order.index(current) else current


# 定义 infer_from_text 的脚本治理处理入口。
def infer_from_text(task_text: str, context_summary: str = "") -> dict[str, Any]:

    # 保留 combined 中间值，支撑 infer_from_text 的当前计算步骤。
    combined = " ".join(part for part in [task_text, context_summary] if part)  # combined 用于本步治理判断

    # 保留 explicit difficulty 中间值，支撑 infer_from_text 的当前计算步骤。
    str_explicit_difficulty = find_explicit_value(combined, DIFFICULTY_ALIASES, ("difficulty", "难度", "難度"))  # explicit difficulty 用于本步治理判断

    # 保留 explicit scale 中间值，支撑 infer_from_text 的当前计算步骤。
    str_explicit_scale = find_explicit_value(combined, SCALE_ALIASES, ("scale", "规模", "規模"))  # explicit scale 用于本步治理判断

    # 保留 contextual difficulty 中间值，支撑 infer_from_text 的当前计算步骤。
    contextual_difficulty = "" if str_explicit_difficulty else find_contextual_rating(combined, DIFFICULTY_ALIASES, ("difficulty", "难度", "難度"))  # contextual difficulty 用于本步治理判断

    # 保留 contextual scale 中间值，支撑 infer_from_text 的当前计算步骤。
    contextual_scale = "" if str_explicit_scale else find_contextual_rating(combined, SCALE_ALIASES, ("scale", "规模", "規模"))  # contextual scale 用于本步治理判断

    # 保留 user difficulty 中间值，支撑 infer_from_text 的当前计算步骤。
    user_difficulty = str_explicit_difficulty or contextual_difficulty  # user difficulty 用于本步治理判断

    # 保留 user scale 中间值，支撑 infer_from_text 的当前计算步骤。
    user_scale = str_explicit_scale or contextual_scale  # user scale 用于本步治理判断

    # 保留 difficulty 中间值，支撑 infer_from_text 的当前计算步骤。
    str_difficulty = user_difficulty or "normal"  # difficulty 用于本步治理判断

    # 保留 scale 中间值，支撑 infer_from_text 的当前计算步骤。
    str_scale = user_scale or "small"  # scale 用于本步治理判断

    # 收集 reasons 条目，保持 infer_from_text 的处理顺序稳定。
    list_reasons: list[str] = []  # reasons 用于本步治理判断

    # 检查 infer_from_text 的当前条件是否需要进入专门分支。
    if str_explicit_difficulty or str_explicit_scale:

        # 调用 append 完成 infer_from_text 的当前动作。
        list_reasons.append("explicit user rating found; do not ask again")

    # 检查 infer_from_text 的当前条件是否需要进入专门分支。
    elif user_difficulty or user_scale:

        # 调用 append 完成 infer_from_text 的当前动作。
        list_reasons.append("contextual user rating found; do not ask again")

    # 收集 complex hits 条目，保持 infer_from_text 的处理顺序稳定。
    int_complex_hits = count_matches(combined, COMPLEX_KEYWORDS)  # complex hits 用于本步治理判断

    # 收集 unclear hits 条目，保持 infer_from_text 的处理顺序稳定。
    int_unclear_hits = count_matches(combined, UNCLEAR_KEYWORDS)  # unclear hits 用于本步治理判断

    # 收集 simple hits 条目，保持 infer_from_text 的处理顺序稳定。
    int_simple_hits = count_matches(combined, SIMPLE_KEYWORDS)  # simple hits 用于本步治理判断

    # 检查 infer_from_text 的当前条件是否需要进入专门分支。
    if int_complex_hits >= 6:

        # 检查 infer_from_text 的当前条件是否需要进入专门分支。
        if not user_difficulty:

            # 保留 difficulty 中间值，支撑 infer_from_text 的当前计算步骤。
            str_difficulty = max_level(str_difficulty, "hell", DIFFICULTY_ORDER)  # difficulty 用于本步治理判断

        # 检查 infer_from_text 的当前条件是否需要进入专门分支。
        if not user_scale:

            # 保留 scale 中间值，支撑 infer_from_text 的当前计算步骤。
            str_scale = max_level(str_scale, "project", SCALE_ORDER)  # scale 用于本步治理判断

        # 调用 append 完成 infer_from_text 的当前动作。
        list_reasons.append("many complex-task signals detected")

    # 检查 infer_from_text 的当前条件是否需要进入专门分支。
    elif int_complex_hits >= 3:

        # 检查 infer_from_text 的当前条件是否需要进入专门分支。
        if not user_difficulty:

            # 保留 difficulty 中间值，支撑 infer_from_text 的当前计算步骤。
            str_difficulty = max_level(str_difficulty, "hard", DIFFICULTY_ORDER)  # difficulty 用于本步治理判断

        # 检查 infer_from_text 的当前条件是否需要进入专门分支。
        if not user_scale:

            # 保留 scale 中间值，支撑 infer_from_text 的当前计算步骤。
            str_scale = max_level(str_scale, "large", SCALE_ORDER)  # scale 用于本步治理判断

        # 调用 append 完成 infer_from_text 的当前动作。
        list_reasons.append("multiple complex-task signals detected")

    # 检查 infer_from_text 的当前条件是否需要进入专门分支。
    elif int_simple_hits and int_complex_hits == 0 and int_unclear_hits == 0:

        # 保留 difficulty 中间值，支撑 infer_from_text 的当前计算步骤。
        str_difficulty = user_difficulty or "simple"  # difficulty 用于本步治理判断

        # 保留 scale 中间值，支撑 infer_from_text 的当前计算步骤。
        str_scale = user_scale or "micro"  # scale 用于本步治理判断

        # 调用 append 完成 infer_from_text 的当前动作。
        list_reasons.append("single low-risk documentation or wording task")

    # 检查 infer_from_text 的当前条件是否需要进入专门分支。
    if int_unclear_hits:

        # 调用 append 完成 infer_from_text 的当前动作。
        list_reasons.append("unclear requirement signal detected")

    # 检查 infer_from_text 的当前条件是否需要进入专门分支。
    if not list_reasons:

        # 调用 append 完成 infer_from_text 的当前动作。
        list_reasons.append("no high-risk task signals detected")

    # 保留 user rating 中间值，支撑 infer_from_text 的当前计算步骤。
    bool_user_rating = bool(user_difficulty or user_scale)  # user rating 用于本步治理判断

    # 保留 ask user rating 中间值，支撑 infer_from_text 的当前计算步骤。
    ask_user_rating = not bool_user_rating and (  # ask user rating 用于本步治理判断
        int_unclear_hits > 0  # ask user rating 用于本步治理判断
        or int_complex_hits >= 3  # ask user rating 用于本步治理判断
        or str_difficulty in {"hard", "hell", "nightmare"}  # ask user rating 用于本步治理判断
        or str_scale in {"large", "project"}  # ask user rating 用于本步治理判断
    )

    # 保留 confidence 中间值，支撑 infer_from_text 的当前计算步骤。
    str_confidence = "high" if bool_user_rating or (int_simple_hits and int_complex_hits == 0 and int_unclear_hits == 0) else "medium"  # confidence 用于本步治理判断

    # 检查 infer_from_text 的当前条件是否需要进入专门分支。
    if ask_user_rating and int_unclear_hits:

        # 保留 confidence 中间值，支撑 infer_from_text 的当前计算步骤。
        str_confidence = "low"  # confidence 用于本步治理判断

    # 收集 actions 条目，保持 infer_from_text 的处理顺序稳定。
    list_actions = ["inspect existing patterns before editing"]  # actions 用于本步治理判断

    # 检查 infer_from_text 的当前条件是否需要进入专门分支。
    if ask_user_rating:

        # 调用 append 完成 infer_from_text 的当前动作。
        list_actions.append("ask user to confirm difficulty and scale")

    # 检查 infer_from_text 的当前条件是否需要进入专门分支。
    if str_difficulty in {"hell", "nightmare"} or str_scale == "project":

        # 调用 append 完成 infer_from_text 的当前动作。
        list_actions.append("reuse-first research")

        # 调用 append 完成 infer_from_text 的当前动作。
        list_actions.append("record candidate tools, libraries, templates, open-source projects, fit, risks, and rejection reasons")

    # 检查 infer_from_text 的当前条件是否需要进入专门分支。
    if str_difficulty == "nightmare" or str_scale == "project":

        # 调用 append 完成 infer_from_text 的当前动作。
        list_actions.append("split into multi-stage project plan")

        # 调用 append 完成 infer_from_text 的当前动作。
        list_actions.append("keep the project plan adjustable when the user changes requirements")

    # 返回 infer_from_text 已整理完成的调用载荷。
    return {
        "ask_user_rating": ask_user_rating,
        "inferred_difficulty": str_difficulty,
        "inferred_scale": str_scale,
        "confidence": str_confidence,
        "reasons": list_reasons,
        "recommended_actions": list_actions,
    }


# 定义 parse_args 的脚本治理处理入口。
def parse_args() -> argparse.Namespace:

    # 保留 parser 中间值，支撑 parse_args 的当前计算步骤。
    parser = argparse.ArgumentParser(description="Heuristically decide whether a task needs user difficulty/scale rating.")  # parser 用于本步治理判断

    # 调用 add_argument 完成 parse_args 的当前动作。
    parser.add_argument("--project", default=".", help="Current project root. Used for path validation and future context hooks.")

    # 调用 add_argument 完成 parse_args 的当前动作。
    parser.add_argument("--task-text", required=True, help="User task text to classify.")

    # 调用 add_argument 完成 parse_args 的当前动作。
    parser.add_argument("--context-summary", default="", help="Optional concise known context for the task.")

    # 调用 add_argument 完成 parse_args 的当前动作。
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON. Text mode also emits JSON for stable automation.")

    # 返回 parse_args 已整理完成的调用载荷。
    return parser.parse_args()


# 定义 main 的脚本治理处理入口。
def main() -> None:

    # 收集 args 条目，保持 main 的处理顺序稳定。
    args = parse_args()  # args 用于本步治理判断

    # 保留 project 中间值，支撑 main 的当前计算步骤。
    project = resolve_project(args.project)  # project 用于本步治理判断

    # 保留 payload 中间值，支撑 main 的当前计算步骤。
    dict_payload = infer_from_text(args.task_text, args.context_summary)  # payload 用于本步治理判断

    # 保留 中间载荷 中间值，支撑 main 的当前计算步骤。
    dict_payload["project"] = str(project)  # 中间载荷 用于本步治理判断

    # 调用 print 完成 main 的当前动作。
    print(json.dumps(dict_payload, ensure_ascii=False, indent=2, sort_keys=True))


# 检查 模块入口 的当前条件是否需要进入专门分支。
if __name__ == "__main__":

    # 调用 main 完成 模块入口 的当前动作。
    main()


