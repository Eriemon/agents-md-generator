"""为分类脚本目录补齐兄弟任务模块导入路径。"""

# 延迟解析注解，避免启动钩子引入额外运行时依赖。
from __future__ import annotations

# 标准库提供模块搜索路径和文件系统路径模型。
import sys
from pathlib import Path

# 发布分类入口必须在导入兄弟模块前禁止写入字节码缓存。
sys.dont_write_bytecode = True  # 防止直接执行入口污染发布源码树

# importlib 可能在执行启动钩子前已经写入自身的字节码缓存。
def _remove_entry_bytecode_cache() -> None:
    """删除当前启动钩子在执行前生成的 importlib 字节码缓存。

    参数：无。
    返回：无。
    """

    # 当前模块的缓存路径由 importlib 写入模块元数据。
    object_cached_path = globals().get("__cached__")  # 当前入口缓存路径。

    # 直接执行入口时通常没有可删除的当前模块缓存。
    if not object_cached_path:

        # 没有缓存路径时保持启动钩子的正常流程。
        return

    # 缓存清理只针对当前入口，不触碰其他模块的运行时文件。
    path_cached_file = Path(str(object_cached_path))  # 当前入口字节码文件。

    # 缓存文件删除失败时仍保持启动钩子可用。
    try:

        # 删除 importlib 在执行入口前写入的自身缓存。
        path_cached_file.unlink(missing_ok=True)

        # 自身缓存删除后，空的缓存目录也不应留在发布源码树中。
        path_cached_directory = path_cached_file.parent  # 当前入口缓存目录。

        # 仅空的标准缓存目录允许被清理。
        if path_cached_directory.name == "__pycache__" and not any(path_cached_directory.iterdir()):

            # 仅删除确认为空的标准缓存目录。
            path_cached_directory.rmdir()

    # 文件系统拒绝清理时不能阻断启动钩子的路径补齐业务。
    except OSError:

        # 缓存清理失败不能阻断启动钩子的路径补齐业务。
        return

# 启动钩子模块加载完成后立即移除可能产生的自身缓存。
_remove_entry_bytecode_cache()

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
