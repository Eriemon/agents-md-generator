"""检测可能需要 scoped AGENTS.md 的项目目录。"""

# 延迟解析注解，保持命令行入口的直接执行兼容性。
from __future__ import annotations

# 标准库提供解释器控制和文件系统路径模型。
import sys
from pathlib import Path

# 路径引导函数保证入口可从任意任务目录直接执行。
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

# 共享扫描模块导入前先补齐兄弟任务目录。
_add_sibling_task_paths()

# CLI 运行期间禁止在技能源码目录写入字节码缓存。
sys.dont_write_bytecode = True  # 当前检测入口的缓存写入保护

# 共享项目扫描函数保持检测逻辑和渲染阶段一致。
from agents_common import emit_json, detect_scopes, parse_args, resolve_project

# CLI 入口仅编排参数解析、项目定位和结构化输出。
def main() -> None:
    """执行目录候选检测入口。

    参数：无，命令行参数从当前进程读取。
    返回：无，目录候选以 JSON 写入标准输出。
    """

    # 解析器描述会作为该入口的公开帮助文本。
    parser = parse_args("Detect directories that may need scoped AGENTS.md files.")  # 当前检测入口参数解析器

    # 读取项目路径参数并交由共享解析逻辑规范化。
    args = parser.parse_args()  # 命令行参数命名空间

    # 稳定 JSON 输出供渲染器、测试和外部自动化复用。
    emit_json(detect_scopes(resolve_project(args.project)))

# 作为模块导入时不得读取参数或写出结果。
if __name__ == "__main__":

    # 仅直接执行当前文件时启动检测流程。
    main()
