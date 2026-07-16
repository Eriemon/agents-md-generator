"""聚合项目事实发现与治理分片，并保持原有公开 API。"""

# 延迟注解求值以兼容直接脚本执行。
from __future__ import annotations

# 路径对象定位与当前模块同目录的实现分片。
from pathlib import Path

# 分片加载器把拆分后的实现注入当前模块命名空间。
def _load_module_shards(tuple_shard_names: tuple[str, ...]) -> None:
    """加载组成项目事实 API 的实现分片。

    参数：tuple_shard_names 为按执行顺序排列的同目录分片名。
    返回：无业务返回值；分片定义直接写入当前模块命名空间。
    """

    # 当前入口所在目录是所有项目事实分片的共同根。
    path_shard_dir = Path(__file__).resolve().parent  # 分片文件查找目录。

    # 严格按声明顺序执行分片，保留跨分片符号依赖。
    for str_shard_name in tuple_shard_names:

        # 单个分片路径同时用于读取源码和编译错误定位。
        path_shard = path_shard_dir / str_shard_name  # 当前待加载分片。

        # 编译后代码对象保留真实文件名，便于异常回溯定位。
        code_shard = compile(path_shard.read_text(encoding="utf-8"), str(path_shard), "exec")  # 当前分片代码对象。

        # 分片共享本模块全局命名空间以维持既有公开 API。
        exec(code_shard, globals())

# 项目事实入口依次装载发现与治理职责分片。
_load_module_shards(("project_facts_discovery.py", "project_facts_governance.py"))
