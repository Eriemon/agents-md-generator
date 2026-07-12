"""构造需要用户确认的结构化治理决策请求。"""

# 延迟解析注解，保持跨入口导入兼容性。
from __future__ import annotations

# 标准库提供模块搜索路径、路径模型和安全类型收窄。
import sys
from pathlib import Path
from typing import Any, cast

# 路径引导函数保证共享模块可从任意任务目录直接导入。
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

# 决策工厂保留公开关键字合同，同时集中校验可选字段。
def decision_request(
    kind: str,
    *,
    question: str,
    **dict_fields: Any,
) -> dict[str, Any]:
    """返回可供 CLI 或代理消费的结构化决策请求。

    参数：kind 为决策类别，question 为待确认问题，dict_fields 接收既有可选合同字段。
    返回：包含规范化选项、默认值、风险和上下文的决策请求字典。
    异常：存在未知关键字时抛出 TypeError，保持原公开签名的拒绝行为。
    """

    # 可选字段保持历史默认值，并通过显式类型收窄供后续组装。
    list_options = cast(list[dict[str, Any]] | None, dict_fields.pop("options", None))  # 原始决策选项

    # 默认选择允许文本、布尔值或未指定状态。
    value_default = cast(str | bool | None, dict_fields.pop("default", None))  # 调用方指定的默认值

    # 必答标记决定上层是否允许跳过当前确认。
    bool_required = cast(bool, dict_fields.pop("required", True))  # 是否必须回答

    # 风险级别用于界面提示和治理记录。
    str_risk = cast(str, dict_fields.pop("risk", "medium"))  # 决策风险级别

    # 后续动作向调用方说明确认后的执行方向。
    str_next_action = cast(str, dict_fields.pop("next_action", ""))  # 确认后的动作说明

    # 上下文承载与当前问题直接相关的结构化证据。
    dict_context = cast(dict[str, Any] | None, dict_fields.pop("context", None))  # 决策上下文

    # 原签名不接受未声明关键字，兼容入口继续执行相同拒绝合同。
    if dict_fields:

        # 稳定排序让错误消息在测试和日志中保持确定。
        str_unknown_fields = ", ".join(sorted(dict_fields))  # 未知关键字列表

        # 明确指出首个合同层错误，避免静默吞掉调用方拼写错误。
        raise TypeError(f"> ERR: [Python] unexpected decision_request fields: {str_unknown_fields}")

    # 每个选项统一补齐文本、值、说明和推荐标记。
    list_normalized_options: list[dict[str, Any]] = []  # 规范化后的决策选项

    # 空选项与未传选项都产生稳定的空列表。
    for dict_option in list_options or []:

        # 规范化结果隔离调用方字典，避免后续修改原始载荷。
        list_normalized_options.append(
            {
                "label": str(dict_option.get("label", "")),  # 展示标签
                "value": dict_option.get("value"),  # 选项业务值
                "description": str(dict_option.get("description", "")),  # 选项说明
                "recommended": bool(dict_option.get("recommended", False)),  # 推荐标记
            }
        )

    # 未显式指定默认值时采用第一个推荐选项。
    if value_default is None:

        # 保持调用方提供的选项顺序来决定推荐优先级。
        for dict_option in list_normalized_options:

            # 只有明确推荐的选项才能成为隐式默认值。
            if dict_option["recommended"]:

                # 推荐选项的业务值成为最终默认选择。
                value_default = cast(str | bool | None, dict_option["value"])  # 推导出的默认值

                # 首个推荐项已经满足默认值合同，无需继续扫描。
                break

    # 最终载荷字段顺序保持历史输出稳定。
    return {
        "kind": kind,  # 决策类别
        "required": bool_required,  # 必答标记
        "question": question,  # 待确认问题
        "options": list_normalized_options,  # 规范化选项
        "default": value_default,  # 默认选择
        "risk": str_risk,  # 风险级别
        "next_action": str_next_action,  # 后续动作
        "context": dict_context or {},  # 结构化上下文
    }
