"""聚合设计画像合同、远端策略与组装实现分片。"""

# 延迟注解求值以兼容直接脚本执行。
from __future__ import annotations

# 路径对象定位与当前模块同目录的实现分片。
from pathlib import Path

# 分片加载器保持画像构建器的单模块公开接口。
def _load_module_shards(tuple_shard_names: tuple[str, ...]) -> None:
    """加载设计画像构建器的实现分片。

    参数：tuple_shard_names 为按依赖顺序排列的同目录分片名。
    返回：无业务返回值；分片定义直接写入当前模块命名空间。
    """

    # 当前入口目录是三个画像构建职责分片的共同位置。
    path_shard_dir = Path(__file__).resolve().parent  # 分片文件查找目录。

    # 合同、远端策略和组装逻辑按固定依赖顺序加载。
    for str_shard_name in tuple_shard_names:

        # 当前分片路径同时承担读取和异常定位职责。
        path_shard = path_shard_dir / str_shard_name  # 当前待加载分片。

        # 编译阶段保留分片文件名供 traceback 使用。
        code_shard = compile(path_shard.read_text(encoding="utf-8"), str(path_shard), "exec")  # 当前分片代码对象。

        # 分片共享模块命名空间以继续暴露既有构建器 API。
        exec(code_shard, globals())

# 画像组装依赖前置合同和远端策略定义。
_load_module_shards(
    (
        "profile_contracts.py",
        "remote_profile_policies.py",
        "profile_assembly.py",
    )
)
