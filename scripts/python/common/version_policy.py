"""集中管理 agents-md-generator 发布版本格式策略。"""

# 延迟解析注解，保持直接导入和命令行入口兼容性。
from __future__ import annotations

# 正则表达式负责识别可选 v 前缀的三段语义版本。
import re

# 版本目录和元数据共用同一基础格式。
VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")  # 三段语义版本格式

# 当前版本解析额外执行单数字 patch 发布策略。
def parse_version_tuple(value: str) -> tuple[int, int, int]:
    """解析当前发布版本并实施 patch 位数限制。

    参数：value 为带可选 v 前缀的三段版本文本。
    返回：major、minor、patch 组成的整数元组。
    异常：格式非法或 patch 大于 9 时抛出 ValueError。
    """

    # 去除调用方输入两端空白，避免目录名比较受格式噪音影响。
    str_version = value.strip()  # 规范化后的版本文本

    # 历史解析器负责完成基础格式和整数转换。
    tuple_version = parse_historical_version_tuple(str_version)  # 三段整数版本

    # 当前发布要求 patch 用尽后递增 minor，不允许两位 patch。
    if tuple_version[2] > 9:

        # 诊断同时给出合法范围和正确的版本进位方式。
        raise ValueError(
            f"> ERR: [Python] invalid version: {value}; patch version must be between 0 and 9, "
            "roll over the minor version instead"
        )

    # 调用方使用整数元组进行版本先后比较。
    return tuple_version

# 历史版本解析允许读取旧目录，不叠加当前发布限制。
def parse_historical_version_tuple(value: str) -> tuple[int, int, int]:
    """解析历史发布目录中的三段语义版本。

    参数：value 为带可选 v 前缀的历史版本文本。
    返回：major、minor、patch 组成的整数元组。
    异常：文本不符合三段数字格式时抛出 ValueError。
    """

    # 历史目录比较同样忽略版本文本两端空白。
    str_version = value.strip()  # 规范化后的历史版本文本

    # 完整匹配避免接受版本后缀或额外目录文本。
    match_version = VERSION_PATTERN.fullmatch(str_version)  # 版本格式匹配结果

    # 缺少任意版本段都应阻止后续整数转换。
    if not match_version:

        # 统一错误前缀满足人类可读诊断输出合同。
        raise ValueError(f"> ERR: [Python] invalid version: {value}; expected vX.Y.Z")

    # 三个捕获组按 major、minor、patch 顺序转换为整数。
    return tuple(int(str_part) for str_part in match_version.groups())

# 非异常式接口便于审计器把策略错误收集到结构化报告。
def version_policy_error(value: str) -> str:
    """返回当前版本策略的诊断文本。

    参数：value 为待检查的发布版本文本。
    返回：合法时为空字符串，非法时为 ValueError 的诊断文本。
    """

    # 解析器是版本策略的唯一事实源，避免重复实现判断条件。
    try:

        # 成功解析即代表当前发布版本满足全部规则。
        parse_version_tuple(value)

    # 版本格式和 patch 范围错误统一转换为返回值。
    except ValueError as exc_version:

        # 审计调用方将诊断并入自己的错误集合。
        return str(exc_version)

    # 空文本明确表示没有发现版本策略问题。
    return ""
