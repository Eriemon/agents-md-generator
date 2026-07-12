"""为分类脚本目录补齐兄弟任务模块导入路径。"""

# 延迟解析注解，避免启动钩子引入额外运行时依赖。
from __future__ import annotations

# 标准库提供模块搜索路径和文件系统路径模型。
import sys
from pathlib import Path

# 设计入口会导入多个兄弟模块，禁止把解释器缓存写入可发布技能源码树。
sys.dont_write_bytecode = True  # 公共设计 CLI 的源码树缓存保护。

# 启动钩子集中维护兄弟任务目录的导入可见性。
def _add_sibling_task_paths() -> None:
    """把 scripts/python 下的任务目录加入模块搜索路径。

    参数：无，目录根由当前文件位置确定。
    返回：无，直接更新当前解释器的模块搜索路径。
    """

    # 当前文件的父级任务目录统一位于 scripts/python 根目录下。
    path_scripts_python_root = Path(__file__).resolve().parents[1]  # Python 脚本根目录

    # 仅目录条目可能成为兄弟任务模块的导入根。
    for path_task_dir in path_scripts_python_root.iterdir():

        # 普通文件不应污染模块搜索路径。
        if path_task_dir.is_dir():

            # sys.path 使用字符串路径保存导入位置。
            str_task_path = str(path_task_dir)  # 兄弟任务目录字符串

            # 已存在的路径保持原有优先级，避免重复插入。
            if str_task_path not in sys.path:

                # 新发现的任务目录优先于解释器默认搜索位置。
                sys.path.insert(0, str_task_path)

# Python 启动导入本模块时立即完成一次路径补齐。
_add_sibling_task_paths()
