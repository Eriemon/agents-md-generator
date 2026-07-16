"""聚合文档发布策略、打包与门禁实现分片。"""

# 延迟注解求值以兼容直接脚本执行。
from __future__ import annotations

# 路径对象定位与当前模块同目录的实现分片。
from pathlib import Path

# 分片加载器保持文档发布 API 的单模块入口。
def _load_module_shards(tuple_shard_names: tuple[str, ...]) -> None:
    """加载文档发布流程的实现分片。

    参数：tuple_shard_names 为按依赖顺序排列的同目录分片名。
    返回：无业务返回值；分片定义直接写入当前模块命名空间。
    """

    # 当前入口目录包含策略、打包和门禁三个分片。
    path_shard_dir = Path(__file__).resolve().parent  # 分片文件查找目录。

    # 固定加载顺序保留策略、打包和门禁之间的符号依赖。
    for str_shard_name in tuple_shard_names:

        # 当前分片路径用于读取源码和保留错误来源。
        path_shard = path_shard_dir / str_shard_name  # 当前待加载分片。

        # 编译对象绑定真实文件名以支持发布故障定位。
        code_shard = compile(path_shard.read_text(encoding="utf-8"), str(path_shard), "exec")  # 当前分片代码对象。

        # 分片共享当前模块命名空间以维持既有调用合同。
        exec(code_shard, globals())

# 策略定义先于打包和门禁实现加载。
_load_module_shards(
    (
        "release_policy.py",
        "release_package.py",
        "release_gate.py",
    )
)
