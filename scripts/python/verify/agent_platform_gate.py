"""验证活动源码和文档没有绕过平台代理目录。"""

# 延迟注解求值保持命令行验证器兼容项目支持的 Python 版本。
from __future__ import annotations

# 验证器使用标准库完成哈希、路径、正则和迭代处理。
import hashlib
from pathlib import Path
import re
import sys
from typing import Any, Iterable

# 活动后缀控制硬编码扫描覆盖的代码和文档类型。
ACTIVE_SUFFIXES = frozenset({".py", ".md", ".ps1", ".psm1", ".sh", ".bash", ".bat", ".cmd", ".tcl"})  # 活动扫描后缀

# 跳过目录保持验证器不读取测试、制品和不可变历史。
SKIP_PARTS = frozenset({".git", "tests", "dist", "history", "__pycache__"})  # 扫描跳过目录段

# 延迟导入 common 模块，避免模块导入阶段修改 sys.path。
def _load_catalog() -> dict[str, object]:
    """在函数执行期加载平台代理目录。

    参数：无。
    返回：平台代理目录字典。
    """

    # 直接执行时仅在调用期登记 common 目录，避免导入副作用。
    path_common_dir: Path = Path(__file__).resolve().parents[1] / "common"  # common 模块所在目录

    # 仅在当前进程尚未登记时追加本地模块目录。
    if str(path_common_dir) not in sys.path:

        # 将 common 目录加入导入搜索路径，供本次函数调用使用。
        sys.path.insert(0, str(path_common_dir))

    # 延迟导入平台目录读取函数，保持脚本导入无副作用。
    from agent_platform import load_catalog

    # 返回已经解析的平台目录。
    return load_catalog()

# 从目录提取需要禁止硬编码的平台用户目录名。
def _platform_tokens() -> tuple[str, ...]:
    """从目录提取需要禁止硬编码的平台用户目录名。

    参数：无。
    返回：排序后的平台代理用户目录片段。
    """

    # 读取当前源码使用的平台代理目录。
    dict_catalog: dict[str, object] = _load_catalog()  # 目录内容

    # 将目录平台条目的用户目录字段转换为稳定元组。
    return tuple(
        sorted(
            {
                str_profile["user_home_dir"]
                for str_profile in dict_catalog["platforms"].values()
            }
        )
    )

# 枚举通过后缀和目录边界检查的活动文本文件。
def _candidate_files(path_root: Path) -> Iterable[Path]:
    """枚举活动文本文件，跳过清单和不可变历史。

    参数：path_root 为待扫描的项目根目录。
    返回：活动文件路径迭代器。
    """

    # 只按稳定路径顺序遍历根目录下的候选项。
    for path_file in sorted(path_root.rglob("*")):

        # 非普通文件和不受支持的后缀不进入硬编码检查。
        if not path_file.is_file() or path_file.suffix.lower() not in ACTIVE_SUFFIXES:

            # 跳过当前不符合活动文件合同的路径。
            continue

        # 跳过目录段命中排除集合的路径。
        if set(path_file.relative_to(path_root).parts) & SKIP_PARTS:

            # 保持测试、制品和历史目录不被扫描。
            continue

        # 验证器自身不应把平台目录字符串误判为待审查源码。
        if path_file.name in {"agent-platform-gate.py"}:

            # 跳过当前 gate 实现文件。
            continue

        # 返回当前通过全部筛选的活动文件路径。
        yield path_file

# 扫描活动路径并返回硬编码平台目录的可审计结果。
def active_platform_hardcoding_gate(
    path_roots: Iterable[Path],
) -> dict[str, object]:
    """扫描活动路径并返回可审计的硬编码错误与清单摘要。

    参数：path_roots 为待扫描的项目根目录迭代器。
    返回：包含错误、文件清单摘要和整体状态的结果字典。
    """

    # 目录返回的 token 集合决定本次硬编码扫描的匹配边界。
    tuple_tokens: tuple[str, ...] = _platform_tokens()  # 平台用户目录 token

    # 正则对象负责在活动文本中查找完整 token。
    pattern_regex: re.Pattern[str] = re.compile(  # 平台目录匹配表达式
        "|".join(  # 合并全部 token 的正则分支
            rf"(?<![A-Za-z0-9_]){re.escape(str_token)}(?![A-Za-z0-9_])"  # 当前 token 的边界表达式
            for str_token in tuple_tokens  # 遍历平台 token
        )
    )

    # 错误列表保存命中的活动路径文本。
    list_errors: list[str] = []  # 硬编码错误列表

    # checked 列表保存参与摘要计算的相对路径。
    list_checked: list[str] = []  # 已检查文件清单

    # 清单摘要绑定路径和原始文本，供结果复核。
    hash_manifest: Any = hashlib.sha256()  # 活动文件清单摘要

    # 按调用方声明的根目录逐项扫描活动文件。
    for path_root in path_roots:

        # 统一当前根目录的绝对路径语义。
        path_root = path_root.resolve()  # 当前扫描根的规范化路径

        # 遍历当前根目录内通过候选筛选的活动文件。
        for path_file in _candidate_files(path_root):

            # 平台目录配置本身不属于硬编码源码审查对象。
            if path_file.name in {"agent-platforms.json", "agent.json"}:

                # 跳过配置文件，避免把合法目录值报告为错误。
                continue

            # 使用相对路径作为跨根目录稳定的审计键。
            str_relative = path_file.relative_to(path_root).as_posix()  # 当前文件相对路径

            # 读取可替换错误的文本，保证单个异常字节不终止整个清单。
            str_text = path_file.read_text(encoding="utf-8", errors="replace")  # 当前文件文本

            # 将当前路径加入已检查文件清单。
            list_checked.append(str_relative)

            # 先写入路径字段，固定清单条目边界。
            hash_manifest.update(str_relative.encode("utf-8"))

            # 写入路径和文本摘要之间的分隔符。
            hash_manifest.update(b"\0")

            # 写入当前文件的 UTF-8 文本字节。
            hash_manifest.update(str_text.encode("utf-8"))

            # 以换行结束当前清单记录。
            hash_manifest.update(b"\n")

            # 命中平台代理 token 时保留可审计错误。
            if pattern_regex.search(str_text):

                # 报告相对路径而不暴露不必要的绝对路径。
                list_errors.append(f"active platform path hardcoded: {str_relative}")

    # 返回整体状态、错误清单和可复核的文件摘要。
    return {
        "ok": not list_errors,
        "errors": list_errors,
        "checked_files": sorted(list_checked),
        "render_manifest_sha256": hash_manifest.hexdigest(),
    }
