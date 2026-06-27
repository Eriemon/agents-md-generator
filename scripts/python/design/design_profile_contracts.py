"""设计档案中可独立复用的治理契约。"""

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

from typing import Any


def global_rule_overrides_contract() -> dict[str, Any]:
    """返回项目本地全局规则覆盖文件的契约描述。"""

    return {
        "path": ".agents/global-rule-overrides.json",
        "details_mode": "json-config",
    }


