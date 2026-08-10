"""聚合 AGENTS 渲染基础、合同与入口实现分片。"""

# 延迟注解求值以兼容直接脚本执行。
from __future__ import annotations

# 路径对象定位实现分片，sys 维护兄弟任务模块搜索路径。
import sys
from pathlib import Path

# 公开入口负责在加载 shard 前建立其跨任务模块依赖环境。
def _extend_task_module_search_path() -> None:
    """把 scripts/python 下的任务目录加入模块搜索路径。

    参数：无，脚本根由当前入口文件位置确定。
    返回：无，直接更新当前解释器的模块搜索路径。
    """

    # render 目录的父级统一承载 common、docs、dirs 等任务模块。
    path_scripts_python_root = Path(__file__).resolve().parents[1]  # Python 任务脚本根目录。

    # 只有直接子目录可能作为当前 shard 的兄弟模块导入根。
    for path_task_dir in path_scripts_python_root.iterdir():

        # 普通文件不能成为顶层模块搜索目录。
        if not path_task_dir.is_dir():

            # 跳过 scripts/python 根下的非目录条目。
            continue

        # sys.path 使用字符串形式保存搜索目录。
        str_task_dir = str(path_task_dir)  # 当前兄弟任务目录字符串。

        # 已存在的搜索路径保持原有优先级，避免重复插入。
        if str_task_dir in sys.path:

            # 当前目录已经可导入，无需改变解释器状态。
            continue

        # 新发现的仓库任务目录优先于解释器默认模块位置。
        sys.path.insert(0, str_task_dir)

# 分片加载器保持渲染器的单模块公开入口。
def _load_module_shards(tuple_shard_names: tuple[str, ...]) -> None:
    """加载 AGENTS 渲染器的实现分片。

    参数：tuple_shard_names 为按依赖顺序排列的同目录分片名。
    返回：无业务返回值；分片定义直接写入当前模块命名空间。
    """

    # 当前入口目录承载渲染基础、合同与命令入口分片。
    path_shard_dir = Path(__file__).resolve().parent  # 分片文件查找目录。

    # 基础能力和合同必须先于命令入口加载。
    for str_shard_name in tuple_shard_names:

        # 当前分片路径同时用于读取源码与错误定位。
        path_shard = path_shard_dir / str_shard_name  # 当前待加载分片。

        # 编译对象保留真实文件名以支持渲染异常回溯。
        code_shard = compile(path_shard.read_text(encoding="utf-8"), str(path_shard), "exec")  # 当前分片代码对象。

        # 分片共享本模块命名空间以维持渲染公开 API。
        exec(code_shard, globals())

# shard 的跨任务依赖必须先于其源码编译和执行可见。
_extend_task_module_search_path()

# 渲染入口按基础、合同和命令编排顺序加载。
_load_module_shards(
    (
        "render_foundation.py",
        "render_contracts.py",
        "render_contract_templates.py",
        "render_entrypoints.py",
    )
)
