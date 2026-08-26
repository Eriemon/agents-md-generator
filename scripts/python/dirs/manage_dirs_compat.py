"""提供目录审查单项入口的向后兼容参数适配。"""

# 延迟解析类型注解，保持旧运行环境的导入兼容。
from __future__ import annotations

# 标准库类型用于兼容接口的明确参数合同。
from pathlib import Path
from typing import Any

# 上下文入口先验证字段，避免核心审查路径接收半成品载荷。
def _validate_context(dict_context: dict[str, Any]) -> None:
    """校验新兼容入口的上下文边界，避免核心读取缺字段时泄漏异常。

    参数:
        dict_context: 新接口传入的完整审查上下文。
    返回:
        None；上下文不完整或字段类型错误时抛出稳定的 ``TypeError``。
    异常:
        TypeError: 必需字段缺失或字段类型不符合核心实现合同。
    """

    # 必需字段按核心读取顺序固定，错误信息因此可重复审计。
    tuple_required_fields: tuple[str, ...] = (  # 核心读取所需的固定字段。
        "project",  # 项目根路径字段。
        "change",  # 当前变更字段。
        "planned",  # 本地计划字段。
        "remote_plan",  # 远程计划字段。
        "list_reasons",  # 阻断原因回写字段。
        "set_path_classes",  # 路径类别回写字段。
        "list_matched_rules",  # 命中规则回写字段。
    )

    # 缺字段必须在任何下标读取前拒绝，避免把输入错误暴露为 KeyError。
    list_missing_fields = [  # 需要在下标读取前报告的字段。
        str_field  # 当前缺失字段名称。
        for str_field in tuple_required_fields  # 遍历核心必需字段。
        if str_field not in dict_context  # 只保留未提供的字段。
    ]

    # 缺字段时立即拒绝不完整上下文。
    if list_missing_fields:

        # 缺字段错误保持稳定，便于调用方和门禁识别。
        raise TypeError(
            "> ERR: [Python] review_change_item context missing fields: "
            + ", ".join(list_missing_fields)
        )

    # 这些字段由核心直接参与路径运算或结果回写，必须保持可变容器合同。
    tuple_type_requirements = (  # 核心字段的运行期类型合同。
        ("project", Path),  # 项目根必须支持路径运算。
        ("planned", dict),  # 本地计划必须是字典。
        ("remote_plan", dict),  # 远程计划必须是字典。
        ("list_reasons", list),  # 阻断原因必须可追加。
        ("set_path_classes", set),  # 路径类别必须可更新。
        ("list_matched_rules", list),  # 命中规则必须可追加。
    )

    # 按声明顺序检查路径和结果容器字段。
    for str_field, type_expected in tuple_type_requirements:

        # 类型不符时阻止核心直接读取或回写。
        if not isinstance(dict_context[str_field], type_expected):

            # 将类型错误转换为兼容入口的稳定诊断。
            raise TypeError(
                f"> ERR: [Python] review_change_item context field "
                f"`{str_field}` has invalid type"
            )

    # 可选回写容器一旦出现也必须支持 append，不能静默接受标量值。
    tuple_optional_list_fields = (  # 可选回写容器的字段名称。
        "list_absolute_blockers",  # 上传绝对阻断原因容器。
        "list_upload_reviews",  # 上传审查结果容器。
    )

    # 仅检查调用方实际提供的可选字段。
    for str_field in tuple_optional_list_fields:

        # 可选字段若存在则必须是列表或明确的 None。
        if (
            str_field in dict_context
            and dict_context[str_field] is not None
            and not isinstance(dict_context[str_field], list)
        ):

            # 禁止标量值绕过核心的 append 合同。
            raise TypeError(
                f"> ERR: [Python] review_change_item context field "
                f"`{str_field}` has invalid type"
            )

# 兼容入口保留旧调用方的参数顺序。
def review_change_item(
    change: Any,
    dict_planned: dict[str, Any] | None = None,
    dict_remote_plan: dict[str, Any] | None = None,
    list_reasons: list[str] | None = None,
    set_path_classes: set[str] | None = None,
    list_matched_rules: list[str] | None = None,
) -> None:
    """兼容旧单项审查入口并转发到上下文核心。

    参数:
        change: 旧接口的原始变更，或新接口的完整上下文字典。
        dict_planned: 旧接口的本地目录计划。
        dict_remote_plan: 旧接口的远程部署计划。
        list_reasons: 旧接口的阻断原因集合。
        set_path_classes: 旧接口的路径类别集合。
        list_matched_rules: 旧接口的命中规则集合。
    返回:
        None；诊断结果写入调用方提供的集合。
    异常:
        TypeError: 上下文或旧接口参数不完整时抛出稳定错误。
    """

    # 延迟导入核心，避免兼容模块和审查模块循环导入。
    from manage_dirs_review import _review_change_item_context, change_facts

    # 统一收集旧参数，保证半成品调用不会被静默解释。
    tuple_legacy_values: tuple[Any | None, ...] = (
        dict_planned,  # 本地目录计划。
        dict_remote_plan,  # 远程部署计划。
        list_reasons,  # 阻断原因集合。
        set_path_classes,  # 路径类别集合。
        list_matched_rules,  # 命中规则集合。
    )

    # 全部旧参数缺省时使用新的完整上下文接口。
    if all(value is None for value in tuple_legacy_values):

        # 新接口必须传入可按字段读取的对象。
        if not isinstance(change, dict):

            # 非对象上下文无法安全进入审查核心。
            raise TypeError(
                "> ERR: [Python] review_change_item context must be a JSON object"
            )

        # 先验证字段和容器，再进入核心的直接下标读取路径。
        _validate_context(change)

        # 完整上下文交给核心实现并保留集合对象身份。
        _review_change_item_context(change)

        # 新接口完成后不再进入旧参数分支。
        return

    # 旧接口必须一次性提供五个共享结果参数。
    if any(value is None for value in tuple_legacy_values):

        # 半成品旧接口不能形成可审计的审查结果。
        raise TypeError(
            "> ERR: [Python] legacy review_change_item requires all six arguments"
        )

    # 旧接口缺少项目根时上传动作必须失败关闭。
    if isinstance(change, dict) and change_facts(change)["action"] == "upload":

        # 上传审查不能猜测当前进程目录作为项目锚点。
        list_reasons.append("upload review requires project context")

        # 上传动作不进入普通目录规则。
        return

    # 旧接口转换为核心使用的统一上下文载荷。
    dict_context = {
        "project": Path("."),  # 旧接口没有项目根，普通动作不读取该值。
        "change": change,  # 保留原始变更对象。
        "planned": dict_planned,  # 传递本地计划基线。
        "remote_plan": dict_remote_plan,  # 传递远程计划基线。
        "list_reasons": list_reasons,  # 回写阻断原因。
        "set_path_classes": set_path_classes,  # 回写路径类别。
        "list_matched_rules": list_matched_rules,  # 回写命中规则。
    }

    # 统一上下文交给审查核心执行。
    _review_change_item_context(dict_context)
