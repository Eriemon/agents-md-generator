"""为 Python 3.10 提供受限的标准库 TOML 读取后备实现。"""

# 延迟注解求值保持兼容项目支持的 Python 版本。
from __future__ import annotations

# 后备解析只需要 AST 字面量、正则和类型标注。
import ast
import re
from typing import Any

# 定义受限 TOML 输入的统一解析异常类型。
class TOMLDecodeError(ValueError):
    """表示受限 TOML 文本无法解析。"""

# 解析当前配置使用的字符串、布尔值、整数和数组基础值。
def _parse_value(str_value: str) -> Any:
    """解析角色配置实际使用的 TOML 基础值。

    参数：str_value 为去除外围空白的 TOML 值文本。
    返回：解析后的基础 Python 值。
    异常：不支持的裸值抛出 TOMLDecodeError。
    """

    # TOML 基础字符串直接转为 Python 字符串字面量。
    if str_value.startswith('"') and str_value.endswith('"'):

        # 返回安全字面量解析得到的字符串值。
        return ast.literal_eval(str_value)

    # 布尔值使用 TOML 的小写拼写。
    if str_value in {"true", "false"}:

        # 将 TOML 小写布尔拼写转换为 Python 布尔值。
        return str_value == "true"

    # 简单整数足以覆盖当前角色配置的可选字段。
    if re.fullmatch(r"[-+]?\d+", str_value):

        # 将已验证的整数字符串转换为整数。
        return int(str_value)

    # 数组值转换布尔拼写后交给安全字面量解析。
    if str_value.startswith("[") and str_value.endswith("]"):

        # 先调整 TOML 布尔字面量，再交给 AST 安全解析。
        str_python = str_value.replace("true", "True").replace("false", "False")  # Python 字面量数组文本

        # 返回数组字面量解析结果。
        return ast.literal_eval(str_python)

    # 当前配置不允许隐式接受未知裸值，防止语义被静默扩大。
    raise TOMLDecodeError(f"> ERR: [Python] unsupported TOML value: {str_value}")

# 解析当前 worker 配置所需的平面 TOML 文本子集。
def loads(str_text: str) -> dict[str, Any]:
    """解析当前 worker 配置所需的平面 TOML 子集。

    参数：str_text 为待解析的平面 TOML 文本。
    返回：顶层字段名到 Python 值的字典。
    异常：语法或值不受支持时抛出 TOMLDecodeError。
    """

    # 结果只承载顶层字段，避免错误地接受嵌套表语义。
    dict_result: dict[str, Any] = {}  # 顶层键值解析结果

    # 预先拆分物理行，保留多行字符串的读取顺序。
    list_lines = str_text.splitlines()  # 配置物理行列表

    # 当前扫描位置使用零基索引，跨行值读取时持续递增。
    int_index = 0  # 当前待读取的物理行索引

    # 逐行处理基础字段和多行开发者指令。
    while int_index < len(list_lines):

        # 读取并规范化当前配置物理行。
        str_line = list_lines[int_index].strip()  # 当前配置物理行文本

        # 消费已经读取的物理行，避免循环重复处理。
        int_index += 1  # 前移到下一条物理行

        # 空行和整行注释不改变配置状态。
        if not str_line or str_line.startswith("#"):

            # 跳过不承载字段的行。
            continue

        # 顶层键名只接受字母、数字、下划线和连字符。
        match_key = re.match(r"^([A-Za-z0-9_-]+)\s*=\s*(.*)$", str_line)  # 顶层键值匹配结果

        # 无法匹配顶层键值结构时停止解析。
        if not match_key:

            # 把原始行文本放入错误，便于定位配置问题。
            raise TOMLDecodeError(f"> ERR: [Python] invalid TOML line: {str_line}")

        # 读取键名和等号后的值文本。
        str_key = match_key.group(1)  # 当前配置字段名称

        # 去除值文本外围空白，保留字符串内部空白。
        str_value = match_key.group(2).strip()  # 当前配置字段值文本

        # 三引号字符串跨行收集，保留内容中的换行。
        if str_value.startswith('"""'):

            # 去掉首行三引号，保留其余内容。
            str_tail = str_value[3:]  # 首行三引号后的尾部文本

            # 多行值按物理行累积，最终使用换行拼接。
            list_value_lines: list[str] = []  # 当前多行值物理行

            # 同一行闭合时无需读取后续物理行。
            if str_tail.endswith('"""'):

                # 保存单行三引号值的内部文本。
                list_value_lines.append(str_tail[:-3])

            # 未闭合时继续读取后续物理行。
            else:

                # 先保存首行三引号后的尾部文本。
                list_value_lines.append(str_tail)

                # 多行值尚未看到结束标记。
                bool_closed = False  # 多行值是否已找到闭合标记

                # 逐行读取直到结束标记或输入耗尽。
                while int_index < len(list_lines):

                    # 读取当前多行字符串物理行。
                    str_multiline = list_lines[int_index]  # 当前多行物理行文本

                    # 消费已经加入多行值处理的物理行。
                    int_index += 1  # 前移多行读取索引

                    # 检查当前行是否包含结束三引号。
                    if str_multiline.endswith('"""'):

                        # 保存闭合标记之前的文本。
                        list_value_lines.append(str_multiline[:-3])

                        # 标记多行值已经正常闭合。
                        bool_closed = True  # 当前多行值已闭合

                        # 结束当前多行值读取。
                        break

                    # 未闭合行原样加入多行值内容。
                    list_value_lines.append(str_multiline)

                # 输入耗尽仍未闭合时拒绝不完整配置。
                if not bool_closed:

                    # 使用固定错误类型报告未闭合三引号。
                    raise TOMLDecodeError("> ERR: [Python] unterminated multiline string")

            # 保存已完成解析的多行字符串字段。
            dict_result[str_key] = "\n".join(list_value_lines)  # 写入多行字符串字段

            # 继续读取下一个顶层字段。
            continue

        # 非字符串字段严格按基础值解析并写入结果字典。
        dict_result[str_key] = _parse_value(str_value)  # 写入基础值字段

    # 返回普通字典，保持与 tomllib.loads 相同的调用形状。
    return dict_result
