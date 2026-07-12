"""执行源码治理硬门禁，标准输出协议为机器可读 JSON。"""

# 延迟注解避免运行时解析仅用于类型检查的标注。
from __future__ import annotations

# 标准库提供运行时路径控制和文件系统定位能力。
import argparse
import sys
from pathlib import Path

# CLI 初始化助手只在执行入口内开放兄弟任务模块的导入路径。
def prepare_task_import_paths() -> None:
    """把 Python 任务子目录加入当前 CLI 的模块搜索路径。

    参数：无，目录根由当前脚本位置确定。
    返回：无业务返回值，副作用仅限当前进程的 sys.path。
    """

    # Python 脚本根目录包含 common 与 verify 等任务模块。
    path_scripts_python_root = Path(__file__).resolve().parents[1]  # 当前技能的 Python 任务根目录。

    # 每个真实任务目录都可能提供当前 CLI 的运行时依赖。
    for path_task_directory in path_scripts_python_root.iterdir():

        # 文件和其他非目录条目不属于模块搜索根。
        if not path_task_directory.is_dir():

            # 跳过不能承载任务模块的普通文件。
            continue

        # 字符串形式用于和解释器现有搜索路径直接比较。
        str_task_directory = str(path_task_directory)  # 当前候选任务模块目录。

        # 已存在的搜索目录无需重复插入。
        if str_task_directory in sys.path:

            # 保留原有搜索优先级并继续检查其他任务目录。
            continue

        # 新任务目录放到搜索路径前端，确保使用当前技能源码。
        sys.path.insert(0, str_task_directory)

# CLI 主入口加载治理依赖并输出统一结构化结果。
def main() -> int:
    """解析项目参数并执行源码治理检查。

    参数：无，命令行参数由共同解析器从当前进程读取。
    返回：治理通过返回 0，否则返回 1。
    """

    # 关闭字节码写入，避免治理检查污染技能源码目录。
    sys.dont_write_bytecode = True  # 当前治理进程禁止生成 Python 字节码缓存。

    # 兄弟任务目录必须在导入共同运行时之前加入搜索路径。
    prepare_task_import_paths()

    # 延迟导入确保直接执行脚本时也能解析任务分类目录。
    from agents_common import emit_json, parse_args, project_profile, resolve_project
    from source_governance import source_governance_report

    # 共同解析器提供项目路径参数和一致的 CLI 行为。
    argument_parser_source_governance: argparse.ArgumentParser = parse_args(  # 源码治理命令行解析器。
        "Check source-governance hard gates."  # 展示给调用方的命令用途。
    )  # 构造带共同项目参数的解析器。

    # 当前参数对象只用于读取共同解析器声明的项目路径。
    object_arguments = argument_parser_source_governance.parse_args()  # 当前源码治理命令行参数。

    # 项目路径规范化后同时用于画像读取和治理扫描。
    path_project = resolve_project(object_arguments.project)  # 当前待检查项目根目录。

    # 结构化治理载荷是标准输出和退出状态的共同真值。
    dict_governance_result = source_governance_report(  # 当前项目源码治理结果。
        path_project,  # 待扫描项目根目录。
        project_profile(path_project),  # 项目源码治理画像。
    )  # 完成整个项目的源码治理检查。

    # 机器可读 JSON 协议供上层门禁和测试直接消费。
    emit_json(dict_governance_result)

    # 权威成功字段决定调用进程观察到的退出状态。
    return 0 if dict_governance_result["ok"] else 1

# 直接执行模块时把治理结果转换为进程退出码。
if __name__ == "__main__":

    # SystemExit 保持成功与失败状态对自动化调用方可见。
    raise SystemExit(main())
