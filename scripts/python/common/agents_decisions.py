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
from typing import Any


# 定义 decision_request 的脚本治理处理入口。
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

    # 收集 normalized options 条目，保持 decision_request 的处理顺序稳定。
    list_normalized_options = []  # normalized options 用于本步治理判断

    # 逐项推进 decision_request 的候选项检查。
    for option in options or []:

        # 调用 append 完成 decision_request 的当前动作。
        list_normalized_options.append(
            {
                "label": str(option.get("label", "")),
                "value": option.get("value"),
                "description": str(option.get("description", "")),
                "recommended": bool(option.get("recommended", False)),
            }
        )

    # 检查 decision_request 的当前条件是否需要进入专门分支。
    if default is None:

        # 逐项推进 decision_request 的候选项检查。
        for option in list_normalized_options:

            # 检查 decision_request 的当前条件是否需要进入专门分支。
            if option["recommended"]:

                # 保留 default 中间值，支撑 decision_request 的当前计算步骤。
                default = option["value"]  # default 用于本步治理判断

                # 分隔 decision_request 的控制流边界。
                break

    # 返回 decision_request 已整理完成的调用载荷。
    return {
        "kind": kind,
        "required": required,
        "question": question,
        "options": list_normalized_options,
        "default": default,
        "risk": risk,
        "next_action": next_action,
        "context": context or {},
    }


