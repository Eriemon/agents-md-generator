"""集中管理 agents-md-generator 发布版本格式策略。"""

from __future__ import annotations

import re


VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_version_tuple(value: str) -> tuple[int, int, int]:
    """解析发布版本号，并要求 patch 段保持单个十进制位。"""

    str_version = value.strip()
    tuple_version = parse_historical_version_tuple(str_version)

    if tuple_version[2] > 9:
        raise ValueError(
            f"invalid version: {value}; patch version must be between 0 and 9, "
            "roll over the minor version instead"
        )

    return tuple_version


def parse_historical_version_tuple(value: str) -> tuple[int, int, int]:
    """解析历史 release 目录中的语义版本，不应用当前发布策略。"""

    str_version = value.strip()
    match = VERSION_PATTERN.fullmatch(str_version)

    if not match:
        raise ValueError(f"invalid version: {value}; expected vX.Y.Z")

    return tuple(int(part) for part in match.groups())


def version_policy_error(value: str) -> str:
    """返回版本策略错误文本；合法版本返回空字符串。"""

    try:
        parse_version_tuple(value)
    except ValueError as exc:
        return str(exc)

    return ""
