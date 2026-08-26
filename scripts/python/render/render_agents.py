"""聚合 AGENTS 渲染基础、合同与入口实现分片。"""

# 延迟注解求值以兼容直接脚本执行。
from __future__ import annotations

# 路径对象定位实现分片，sys 维护兄弟任务模块搜索路径。
import sys
import json
from pathlib import Path

# 动态加载渲染分片前禁止入口自身和分片导入产生字节码缓存。
sys.dont_write_bytecode = True  # 渲染入口的缓存副作用保护。

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

    # 分片中的 direct-execution guard 不得在聚合入口加载阶段提前触发。
    globals()["_RENDER_SHARD_LOADING"] = True  # 分片加载状态标记。

    # 分片代码只定义共享实现，不在聚合加载阶段执行公开命令。
    try:

        # 基础能力和合同必须先于命令入口加载。
        for str_shard_name in tuple_shard_names:

            # 当前分片路径同时用于读取源码与错误定位。
            path_shard = path_shard_dir / str_shard_name  # 当前待加载分片。

            # 编译对象保留真实文件名以支持渲染异常回溯。
            code_shard = compile(path_shard.read_text(encoding="utf-8"), str(path_shard), "exec")  # 当前分片代码对象。

            # 分片共享本模块命名空间以维持渲染公开 API。
            exec(code_shard, globals())

    # 无论分片是否加载成功，都清除加载状态标记。
    finally:

        # 清除哨兵后由包装器唯一执行公开 CLI。
        globals().pop("_RENDER_SHARD_LOADING", None)

# 记录渲染分片是否已经注入当前聚合模块。
bool_shards_loaded = False  # 渲染分片载入状态

# 导入聚合模块和直接执行入口都复用同一分片初始化路径。
def _ensure_render_shards() -> None:
    """确保渲染基础、合同和入口分片已经加载。

    参数：无；分片位置由当前聚合入口确定。
    返回：无；分片公开对象写入当前模块命名空间。
    异常：分片加载失败时以 SystemExit(1) 结束命令入口。
    """

    # 模块状态标记由本函数统一更新。
    global bool_shards_loaded

    # 直接导入和 CLI 入口不能重复执行分片副作用。
    if bool_shards_loaded:

        # 已完成加载时保留现有渲染公开 API。
        return

    # shard 的跨任务依赖必须先于源码编译和执行可见。
    _extend_task_module_search_path()

    # 分片加载异常必须先转换为稳定的 CLI 错误输出。
    try:

        # 按声明顺序加载基础、合同、模板和命令入口分片。
        _load_module_shards(
            (
                "render_foundation.py",
                "render_contracts.py",
                "render_contract_templates.py",
                "render_entrypoints.py",
            )
        )

    # 分片加载失败时保留 CLI 可识别的 JSON 错误协议。
    except Exception as object_error:

        # 加载失败通过稳定 JSON 错误协议返回给 CLI 调用方。
        sys.stdout.write(
            json.dumps({"errors": [f"> ERR: [Python] render failed: {object_error}" ]}, ensure_ascii=False) + "\n"
        )

        # 加载失败不能继续暴露不完整的渲染命令集合。
        raise SystemExit(1)

    # 只有全部分片成功后才对后续调用标记为可用。
    bool_shards_loaded = True  # 渲染公开 API 已完成注入

# 渲染入口加载分片并转交命令行处理。
def main() -> None:
    """加载渲染分片并执行其公开命令入口。

    参数:
        无；命令行参数由加载的渲染入口解析。

    返回:
        无；渲染入口负责写入或报告生成结果。

    异常:
        SystemExit: 分片加载失败时以 CLI 错误协议退出。
    """

    # 直接执行时复用已完成或尚未完成的分片初始化。
    _ensure_render_shards()

# 模块导入时也准备公开 API，兼容直接导入调用方。
_ensure_render_shards()

# 只有直接执行入口时才启动渲染 CLI。
if __name__ == "__main__":

    # 直接运行脚本时进入渲染 CLI。
    main()
