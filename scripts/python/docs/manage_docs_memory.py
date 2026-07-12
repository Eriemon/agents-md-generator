"""聚合文档记忆存储与门禁实现分片。"""

# 延迟注解求值以兼容直接脚本执行。
from __future__ import annotations

# 路径对象定位与当前模块同目录的实现分片。
from pathlib import Path

# 分片加载器保持文档记忆工具的既有模块接口。
def _load_module_shards(tuple_shard_names: tuple[str, ...]) -> None:
    """加载文档记忆存储和门禁实现。

    参数：tuple_shard_names 为按依赖顺序排列的同目录分片名。
    返回：无业务返回值；分片定义直接写入当前模块命名空间。
    """

    # 当前入口目录包含记忆存储与门禁两个实现分片。
    path_shard_dir = Path(__file__).resolve().parent  # 分片文件查找目录。

    # 存储实现先加载，门禁分片才能复用其公共能力。
    for str_shard_name in tuple_shard_names:

        # 当前分片路径用于读取源码并保留错误来源。
        path_shard = path_shard_dir / str_shard_name  # 当前待加载分片。

        # 编译结果绑定真实分片路径供异常回溯。
        code_shard = compile(path_shard.read_text(encoding="utf-8"), str(path_shard), "exec")  # 当前分片代码对象。

        # 分片写入共同命名空间以维持历史导入合同。
        exec(code_shard, globals())

# 存储职责必须先于记忆门禁加载。
_load_module_shards(("_manage_docs_memory_store.py", "_manage_docs_memory_gate.py"))
