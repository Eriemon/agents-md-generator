"""为分类脚本目录补齐兄弟任务模块导入路径。"""

from __future__ import annotations

import sys
from pathlib import Path


def _add_sibling_task_paths() -> None:
    """把 scripts/python 下的任务目录加入模块搜索路径。"""

    scripts_python_root = Path(__file__).resolve().parents[1]

    for task_dir in scripts_python_root.iterdir():
        if task_dir.is_dir():
            task_path = str(task_dir)
            if task_path not in sys.path:
                sys.path.insert(0, task_path)


_add_sibling_task_paths()
