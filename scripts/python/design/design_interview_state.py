"""聚合设计访谈状态流转与完成判定分片。"""

# 延迟注解求值以兼容直接脚本执行。
from __future__ import annotations

# 路径对象定位与当前模块同目录的实现分片。
from pathlib import Path

# 分片加载器维持状态机实现的原有导入表面。
def _load_module_shards(tuple_shard_names: tuple[str, ...]) -> None:
    """加载设计访谈状态机的实现分片。

    参数：tuple_shard_names 为按依赖顺序排列的同目录分片名。
    返回：无业务返回值；分片定义直接写入当前模块命名空间。
    """

    # 当前入口目录承载状态流与完成判定两个分片。
    path_shard_dir = Path(__file__).resolve().parent  # 分片文件查找目录。

    # 声明顺序保证完成判定可以复用前序状态流符号。
    for str_shard_name in tuple_shard_names:

        # 当前分片路径提供源码内容与 traceback 文件身份。
        path_shard = path_shard_dir / str_shard_name  # 当前待加载分片。

        # 代码对象保留分片真实位置以支持故障定位。
        code_shard = compile(path_shard.read_text(encoding="utf-8"), str(path_shard), "exec")  # 当前分片代码对象。

        # 分片进入共同命名空间以保持原有状态机 API。
        exec(code_shard, globals())

# 状态流必须先于完成判定加载。
_load_module_shards(("_design_interview_state_flow.py", "_design_interview_state_completion.py"))
