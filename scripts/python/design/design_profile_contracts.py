"""设计档案中可独立复用的治理契约。"""

# 延迟解析注解，保持直接脚本执行兼容性。
from __future__ import annotations

# 标准库提供模块搜索路径、路径模型和通用载荷类型。
import sys
from pathlib import Path
from typing import Any

# 路径引导函数保证本模块从任意任务目录直接导入。
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

# 模块导入阶段先建立跨任务目录的依赖可见性。
_add_sibling_task_paths()

# 公共合同函数集中描述本地规则覆盖文件的稳定接口。
def global_rule_overrides_contract() -> dict[str, Any]:
    """返回项目本地全局规则覆盖文件的契约描述。

    参数：无，契约路径和详情模式由技能规范固定。
    返回：包含相对路径与详情读取模式的字典。
    """

    # 调用方据此定位 JSON 配置并按结构化模式读取详情。
    return {
        "path": ".agents/global-rule-overrides.json",
        "details_mode": "json-config",
    }
