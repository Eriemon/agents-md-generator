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
from typing import Any


# 保留 SUPPORTED RULE SETS 中间值，支撑 模块入口 的当前计算步骤。
SUPPORTED_RULE_SETS = [  # SUPPORTED RULE SETS 用于本步治理判断
    "a-philosophy-of-software-design",  # SUPPORTED RULE SETS 用于本步治理判断
    "clean-architecture",  # SUPPORTED RULE SETS 用于本步治理判断
    "clean-code",  # SUPPORTED RULE SETS 用于本步治理判断
    "code-complete",  # SUPPORTED RULE SETS 用于本步治理判断
    "designing-data-intensive-applications",  # SUPPORTED RULE SETS 用于本步治理判断
    "domain-driven-design",  # SUPPORTED RULE SETS 用于本步治理判断
    "domain-driven-design-distilled",  # SUPPORTED RULE SETS 用于本步治理判断
    "implementing-domain-driven-design",  # SUPPORTED RULE SETS 用于本步治理判断
    "patterns-of-enterprise-application-architecture",  # SUPPORTED RULE SETS 用于本步治理判断
    "refactoring",  # SUPPORTED RULE SETS 用于本步治理判断
    "refactoring-guru",  # SUPPORTED RULE SETS 用于本步治理判断
    "release-it",  # SUPPORTED RULE SETS 用于本步治理判断
    "the-pragmatic-programmer",  # SUPPORTED RULE SETS 用于本步治理判断
    "working-effectively-with-legacy-code",  # SUPPORTED RULE SETS 用于本步治理判断
]

# 保留 ALLOWED MODES 中间值，支撑 模块入口 的当前计算步骤。
ALLOWED_MODES = ["mini", "nano"]  # ALLOWED MODES 用于本步治理判断

# 保留 ALLOWED SCOPES 中间值，支撑 模块入口 的当前计算步骤。
ALLOWED_SCOPES = ["project-baseline", "scoped", "on-demand"]  # ALLOWED SCOPES 用于本步治理判断

# 保留 TASK RECOMMENDATIONS 中间值，支撑 模块入口 的当前计算步骤。
TASK_RECOMMENDATIONS = {  # TASK RECOMMENDATIONS 用于本步治理判断
    "architecture": {  # TASK RECOMMENDATIONS 用于本步治理判断
        "primary": "a-philosophy-of-software-design",  # TASK RECOMMENDATIONS 用于本步治理判断
        "reason": "use when complexity, module boundaries, and abstraction depth are the main risk",  # TASK RECOMMENDATIONS 用于本步治理判断
    },  # TASK RECOMMENDATIONS 用于本步治理判断
    "clean-code": {  # TASK RECOMMENDATIONS 用于本步治理判断
        "primary": "clean-code",  # TASK RECOMMENDATIONS 用于本步治理判断
        "reason": "use when local readability, naming, function shape, and maintainability are the main risk",  # TASK RECOMMENDATIONS 用于本步治理判断
    },  # TASK RECOMMENDATIONS 用于本步治理判断
    "data": {  # TASK RECOMMENDATIONS 用于本步治理判断
        "primary": "designing-data-intensive-applications",  # TASK RECOMMENDATIONS 用于本步治理判断
        "reason": "use when source of truth, consistency, events, streams, storage, or schema evolution dominate",  # TASK RECOMMENDATIONS 用于本步治理判断
    },  # TASK RECOMMENDATIONS 用于本步治理判断
    "domain": {  # TASK RECOMMENDATIONS 用于本步治理判断
        "primary": "domain-driven-design",  # TASK RECOMMENDATIONS 用于本步治理判断
        "reason": "use when business meaning, bounded contexts, ubiquitous language, and model boundaries dominate",  # TASK RECOMMENDATIONS 用于本步治理判断
    },  # TASK RECOMMENDATIONS 用于本步治理判断
    "legacy": {  # TASK RECOMMENDATIONS 用于本步治理判断
        "primary": "working-effectively-with-legacy-code",  # TASK RECOMMENDATIONS 用于本步治理判断
        "reason": "use when behavior is poorly characterized and changes need tests before cleanup",  # TASK RECOMMENDATIONS 用于本步治理判断
    },  # TASK RECOMMENDATIONS 用于本步治理判断
    "refactor": {  # TASK RECOMMENDATIONS 用于本步治理判断
        "primary": "refactoring",  # TASK RECOMMENDATIONS 用于本步治理判断
        "reason": "use when preserving behavior while changing structure is the main work",  # TASK RECOMMENDATIONS 用于本步治理判断
    },  # TASK RECOMMENDATIONS 用于本步治理判断
    "reliability": {  # TASK RECOMMENDATIONS 用于本步治理判断
        "primary": "release-it",  # TASK RECOMMENDATIONS 用于本步治理判断
        "reason": "use when production failure semantics, bounds, retries, recovery, and operations dominate",  # TASK RECOMMENDATIONS 用于本步治理判断
    },  # TASK RECOMMENDATIONS 用于本步治理判断
}

# 保留 CONFLICT PAIRS 中间值，支撑 模块入口 的当前计算步骤。
CONFLICT_PAIRS = {  # CONFLICT PAIRS 用于本步治理判断
    frozenset({  # 领域模型与企业应用模式冲突组合
        "domain-driven-design",  # 战术 DDD 规则集
        "patterns-of-enterprise-application-architecture",  # 企业应用架构规则集
    }): (
        "domain model pressure conflicts with transaction-script/table-module "  # 领域模型冲突说明前半段
        "pressure when both are equal active guidance"  # 领域模型冲突说明后半段
    ),
    frozenset({  # 实践 DDD 与企业应用模式冲突组合
        "implementing-domain-driven-design",  # 实践 DDD 规则集
        "patterns-of-enterprise-application-architecture",  # 企业应用架构规则集
    }): (
        "implementation-heavy DDD conflicts with enterprise-application pattern "  # 实践 DDD 冲突说明前半段
        "pressure when both arbitrate the same model layer"  # 实践 DDD 冲突说明后半段
    ),
}

# 保留 OVERLAP PAIRS 中间值，支撑 模块入口 的当前计算步骤。
OVERLAP_PAIRS = {  # OVERLAP PAIRS 用于本步治理判断
    frozenset({"a-philosophy-of-software-design", "clean-code"}): "both push local code-shape simplification; choose one primary",  # OVERLAP PAIRS 用于本步治理判断
    frozenset({"clean-code", "code-complete"}): "both cover local construction discipline; choose one primary",  # OVERLAP PAIRS 用于本步治理判断
    frozenset({"clean-code", "the-pragmatic-programmer"}): "both cover broad engineering hygiene; choose one primary",  # OVERLAP PAIRS 用于本步治理判断
    frozenset({"code-complete", "the-pragmatic-programmer"}): "both cover broad construction practice; choose one primary",  # OVERLAP PAIRS 用于本步治理判断
    frozenset({"domain-driven-design", "domain-driven-design-distilled"}): "distilled DDD is a narrower substitute for full DDD pressure",  # OVERLAP PAIRS 用于本步治理判断
    frozenset({"domain-driven-design", "implementing-domain-driven-design"}): "implementation DDD overlaps with full DDD model guidance",  # OVERLAP PAIRS 用于本步治理判断
    frozenset({"domain-driven-design-distilled", "implementing-domain-driven-design"}): "both target DDD implementation choices at different depths",  # OVERLAP PAIRS 用于本步治理判断
    frozenset({"refactoring", "refactoring-guru"}): "both target refactoring choices; choose one primary",  # OVERLAP PAIRS 用于本步治理判断
}


# 定义 emit_json 的脚本治理处理入口。
def emit_json(data: dict[str, Any]) -> None:

    # 调用 print 完成 emit_json 的当前动作。
    print(json.dumps(data, indent=2, sort_keys=True))


# 定义 normalize 的脚本治理处理入口。
def normalize(value: str | None) -> str:

    # 返回 normalize 已整理完成的调用载荷。
    return (value or "").strip().lower()


# 定义 contract 的脚本治理处理入口。
def contract(primary: str, mode: str, scope: str, notes: str = "") -> dict[str, Any]:

    # 返回 contract 已整理完成的调用载荷。
    return {
        "primary": primary,
        "mode": mode,
        "scope": scope,
        "notes": notes,
        "full_reference_allowed_in_agents": False,
        "compatibility_policy": "one primary active rule set; use secondary rule sets only as scoped or on-demand guidance",
        "compression_policy": "decision-equivalent compression: keep decision-changing, trigger, tradeoff, and checklist rules",
    }


# 定义 validate 的脚本治理处理入口。
def validate(primary: str, secondaries: list[str], mode: str, scope: str) -> tuple[list[str], list[str]]:

    # 收集 errors 条目，保持 validate 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 收集 warnings 条目，保持 validate 的处理顺序稳定。
    list_warnings: list[str] = []  # warnings 用于本步治理判断

    # 检查 validate 的当前条件是否需要进入专门分支。
    if primary not in SUPPORTED_RULE_SETS:

        # 调用 append 完成 validate 的当前动作。
        list_errors.append(f"unknown primary rule set: {primary}")

    # 检查 validate 的当前条件是否需要进入专门分支。
    if mode == "full":

        # 调用 append 完成 validate 的当前动作。
        list_errors.append("full book rules must stay reference-only and must not be pasted into AGENTS.md")

    # 检查 validate 的当前条件是否需要进入专门分支。
    elif mode not in ALLOWED_MODES:

        # 调用 append 完成 validate 的当前动作。
        list_errors.append("mode must be mini or nano")

    # 检查 validate 的当前条件是否需要进入专门分支。
    if scope not in ALLOWED_SCOPES:

        # 调用 append 完成 validate 的当前动作。
        list_errors.append("scope must be project-baseline, scoped, or on-demand")

    # 逐项推进 validate 的候选项检查。
    for secondary in secondaries:

        # 检查 validate 的当前条件是否需要进入专门分支。
        if secondary not in SUPPORTED_RULE_SETS:

            # 调用 append 完成 validate 的当前动作。
            list_errors.append(f"unknown secondary rule set: {secondary}")

            # 分隔 validate 的控制流边界。
            continue

        # 保留 pair 中间值，支撑 validate 的当前计算步骤。
        pair = frozenset({primary, secondary})  # pair 用于本步治理判断

        # 检查 validate 的当前条件是否需要进入专门分支。
        if pair in CONFLICT_PAIRS:

            # 调用 append 完成 validate 的当前动作。
            list_errors.append(f"conflicting active rule sets: {primary} + {secondary}: {CONFLICT_PAIRS[pair]}")

        # 检查 validate 的当前条件是否需要进入专门分支。
        elif pair in OVERLAP_PAIRS:

            # 调用 append 完成 validate 的当前动作。
            list_warnings.append(f"overlapping rule sets: {primary} + {secondary}: {OVERLAP_PAIRS[pair]}")

    # 返回 validate 已整理完成的调用载荷。
    return list_errors, list_warnings


# 定义 list_payload 的脚本治理处理入口。
def list_payload() -> dict[str, Any]:

    # 返回 list_payload 已整理完成的调用载荷。
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


# 定义 main 的脚本治理处理入口。
def main() -> None:

    # 保留 parser 中间值，支撑 main 的当前计算步骤。
    parser = argparse.ArgumentParser(description="Select and validate a book-derived engineering rule contract.")  # parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--list", action="store_true", help="List supported rule sets, modes, scopes, and task recommendations.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--task", choices=sorted(TASK_RECOMMENDATIONS), default=None, help="Recommend a primary rule set for a task type.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--primary", default=None, help="Primary active rule set.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--secondary", action="append", default=[], help="Secondary rule set to check for equal-active conflicts.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--mode", default="mini", help="Compression mode: mini or nano. full is rejected for AGENTS.md.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--scope", default="on-demand", help="Scope: project-baseline, scoped, or on-demand.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--notes", default="", help="Short local notes to carry into the profile.")

    # 收集 args 条目，保持 main 的处理顺序稳定。
    args = parser.parse_args()  # args 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if args.list:

        # 调用 emit_json 完成 main 的当前动作。
        emit_json(list_payload())

        # 返回 main 已整理完成的调用载荷。
        return

    # 保留 recommended 中间值，支撑 main 的当前计算步骤。
    recommended = TASK_RECOMMENDATIONS.get(args.task or "")  # recommended 用于本步治理判断

    # 保留 primary 中间值，支撑 main 的当前计算步骤。
    primary = normalize(args.primary) or (recommended["primary"] if recommended else "")  # primary 用于本步治理判断

    # 保留 mode 中间值，支撑 main 的当前计算步骤。
    str_mode = normalize(args.mode)  # mode 用于本步治理判断

    # 保留 scope 中间值，支撑 main 的当前计算步骤。
    str_scope = normalize(args.scope)  # scope 用于本步治理判断

    # 收集 secondaries 条目，保持 main 的处理顺序稳定。
    secondaries = [normalize(item) for item in args.secondary if normalize(item)]  # secondaries 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if not primary:

        # 调用 emit_json 完成 main 的当前动作。
        emit_json({"errors": ["choose --primary or --task"], "warnings": []})

        # 抛出 main 已确认的阻断原因。
        raise SystemExit(1)

    # 收集 errors、warnings 条目，保持 main 的处理顺序稳定。
    tuple_errors, tuple_warnings = validate(primary, secondaries, str_mode, str_scope)  # errors、warnings 用于本步治理判断

    # 保留 payload 中间值，支撑 main 的当前计算步骤。
    dict_payload = {  # payload 用于本步治理判断
        "contract": contract(primary, str_mode, str_scope, args.notes.strip()),  # payload 用于本步治理判断
        "errors": tuple_errors,  # payload 用于本步治理判断
        "recommendation": recommended,  # payload 用于本步治理判断
        "secondary_rule_sets": secondaries,  # payload 用于本步治理判断
        "warnings": tuple_warnings,  # payload 用于本步治理判断
    }

    # 调用 emit_json 完成 main 的当前动作。
    emit_json(dict_payload)

    # 检查 main 的当前条件是否需要进入专门分支。
    if tuple_errors:

        # 抛出 main 已确认的阻断原因。
        raise SystemExit(1)


# 检查 模块入口 的当前条件是否需要进入专门分支。
if __name__ == "__main__":

    # 调用 main 完成 模块入口 的当前动作。
    main()


