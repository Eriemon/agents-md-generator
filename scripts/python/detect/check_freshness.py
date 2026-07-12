"""核对根 AGENTS.md 的更新时间、验证时间与仓库变更是否一致。"""

# 延迟注解求值支持现代类型合同。
from __future__ import annotations

# CLI、正则、时间与路径依赖支撑新鲜度事实采集。
import argparse
import importlib
import re
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

# 公共工具通过显式源码规格加载，支持从任意工作目录直接执行。
def load_agents_common() -> ModuleType:
    """加载项目解析、JSON 输出和 Git 命令公共模块。

    参数：无。
    返回：已执行初始化的 ``agents_common`` 模块。
    异常：公共模块源码无法建立加载规格时抛出 ImportError。
    """

    # 所有分类目录共同位于 scripts/python 下。
    path_python_root = Path(__file__).resolve().parents[1]  # Python 任务目录共同根

    # 运行阶段登记分类目录，兼容公共模块之间的循环导入合同。
    for path_task_directory in path_python_root.iterdir():

        # 普通文件不参与模块搜索。
        if not path_task_directory.is_dir():

            # 继续寻找其余任务目录。
            continue

        # sys.path 使用字符串路径，并保持源码优先级。
        str_task_directory = str(path_task_directory)  # 当前分类模块搜索路径

        # 已存在目录不重复插入，避免改变既有解析顺序。
        if str_task_directory not in sys.path:

            # 只在函数执行阶段扩展依赖搜索面。
            sys.path.insert(0, str_task_directory)

    # 标准导入器负责 sys.modules 登记和循环依赖处理。
    return importlib.import_module("agents_common")

# 项目路径包装器维持原调用表面。
def resolve_project(path_value: str | Path) -> Path:
    """解析项目根目录。

    参数：path_value 为 CLI 项目路径。
    返回：公共工具规范化后的绝对路径。
    """

    # 路径存在性和解析策略由公共模块统一维护。
    return load_agents_common().resolve_project(path_value)

# Git 包装器让测试继续替换本模块调用点。
def run_git(project: Path, args: list[str]) -> Any:
    """在项目根执行只读 Git 查询。

    参数：project 为仓库根；args 为 Git 子命令参数。
    返回：公共命令执行器的完成结果。
    """

    # 新鲜度检查只读取日志或状态，不修改仓库。
    return load_agents_common().run_git(project, args)

# JSON 包装器保持 CLI 机器可读输出协议。
def emit_json(payload: dict[str, Any]) -> None:
    """输出新鲜度检查载荷。

    参数：payload 为 JSON 兼容结果字典。
    返回：无业务返回值。
    """

    # 序列化格式与其他治理入口保持一致。
    load_agents_common().emit_json(payload)

# 完整更新时间用于秒级比较工作树与提交时间。
TIMESTAMP_RE = re.compile(r"Last updated:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")  # 根规则完整更新时间格式

# 旧版日期格式用于兼容尚未迁移到秒级时间戳的根规则。
DATE_RE = re.compile(r"Last updated:\s*(\d{4}-\d{2}-\d{2})")  # 根规则旧版日期格式

# 验证时间独立于更新时间，证明同步后的规则已通过复核。
VERIFIED_RE = re.compile(r"Last verified:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")  # 根规则完整验证时间格式

# 时间解析器把元数据文本转换为可比较值。
def parse_datetime(raw: str) -> datetime | None:
    """解析 ISO 时间文本。

    参数：raw 为 AGENTS 元数据中的时间文本。
    返回：合法 datetime；格式非法时返回 ``None``。
    """

    # 非法或旧格式时间不应让新鲜度检查崩溃。
    try:

        # 标准库同时接受带时区和不带时区的 ISO 文本。
        return datetime.fromisoformat(raw)

    # 格式错误由调用方按缺失时间处理。
    except ValueError:

        # 可空返回值保留兼容旧元数据的降级路径。
        return None

# Git 时间查询器提供旧日期元数据的精确比较基准。
def git_commit_time_for_file(project: Path, path: Path) -> datetime | None:
    """读取文件最近一次 Git 提交时间。

    参数：project 为仓库根；path 为待查询文件。
    返回：最近提交时间；路径或 Git 查询不可用时返回 ``None``。
    """

    # 仓库内路径优先转为 Git 稳定识别的 POSIX 相对路径。
    try:

        # 相对路径避免绝对路径在不同平台产生查询差异。
        str_rel_path = path.relative_to(project).as_posix()  # Git 日志目标路径

    # 外部路径保留原文本，让 Git 自行报告不可查询状态。
    except ValueError:

        # 字符串回退兼容测试夹具传入的非仓库路径。
        str_rel_path = str(path)  # Git 查询的路径回退值

    # 单条日志的提交者时间提供秒级新鲜度事实。
    command_result = run_git(project, ["log", "-1", "--format=%cI", "--", str_rel_path])  # Git 日志查询结果

    # 未跟踪文件或非 Git 工作区没有可用提交时间。
    if command_result.returncode != 0:

        # 调用方随后尝试文件修改时间或日期回退。
        return None

    # 去除命令结尾换行后再解析 ISO 时间。
    raw = command_result.stdout.strip()  # Git 输出的提交时间文本

    # 空日志与解析失败统一表示没有可靠 Git 时间。
    return parse_datetime(raw) if raw else None

# 文件系统时间作为 Git 不可用时的次级比较事实。
def file_mtime(path: Path) -> datetime | None:
    """读取文件修改时间。

    参数：path 为目标文件。
    返回：本地修改时间；文件不可访问时返回 ``None``。
    """

    # 文件可能在检查期间被删除或拒绝访问。
    try:

        # 本地时间与无时区元数据进入相同的比较路径。
        return datetime.fromtimestamp(path.stat().st_mtime)

    # 文件系统错误仅降低证据强度，不终止治理检查。
    except OSError:

        # 调用方继续使用日期午夜回退值。
        return None

# 输出规范器保证 JSON 时间精度与 AGENTS 元数据一致。
def normalize_datetime(value: datetime) -> str:
    """输出秒级 ISO 时间。

    参数：value 为待序列化时间。
    返回：省略微秒的 ISO 文本。
    """

    # 秒级格式避免文件系统微秒差异造成无意义漂移。
    return value.isoformat(timespec="seconds")

# 比较规范器消除带时区与无时区值不能直接排序的问题。
def comparable_datetime(value: datetime) -> datetime:
    """转换为可直接比较的无时区时间。

    参数：value 为元数据或文件事实时间。
    返回：保留墙钟字段并移除 tzinfo 的 datetime。
    """

    # 仓库元数据以本地墙钟时间记录，比较时只对齐字段值。
    return value.replace(tzinfo=None)

# CLI 编排器汇总元数据时间、Git 变更与最终陈旧判定。
def main() -> None:
    """运行根 AGENTS 新鲜度检查。

    参数：无，参数从命令行读取。
    返回：无业务返回值，结果通过 JSON 协议输出。
    """

    # 解析器只接受可选项目根，便于从仓库内外调用。
    parser = argparse.ArgumentParser(  # 新鲜度检查命令行解析器
        description="Check whether AGENTS.md may be stale versus git history."  # CLI 功能摘要
    )

    # 默认当前目录保持历史 CLI 行为不变。
    parser.add_argument("path_project", nargs="?", default=".")

    # 已解析命名空间提供项目路径参数。
    args = parser.parse_args()  # 新鲜度检查参数

    # 公共解析器统一绝对路径和仓库根定位。
    path_project = resolve_project(args.path_project)  # 待检查项目根目录

    # 新鲜度合同只比较项目根规则文件。
    agents = path_project / "AGENTS.md"  # 根 AGENTS 文件路径

    # 无 Git 证据前保持空变更集合。
    list_changed_files: list[str] = []  # 晚于新鲜度基准的仓库文件

    # 解析后的更新时间可能因文件或元数据缺失而为空。
    last_updated = None  # 根规则更新时间

    # 原始文本保留给调用方审计格式迁移情况。
    last_updated_raw = None  # 根规则更新时间原文

    # 独立验证时间可覆盖更早的更新时间作为新鲜度基准。
    last_verified = None  # 根规则最近验证时间

    # 验证时间原文用于 JSON 证据回显。
    last_verified_raw = None  # 根规则验证时间原文

    # 来源字段解释最终比较值来自元数据、Git 还是文件系统。
    str_comparison_source = "missing"  # 更新时间比较事实来源

    # 新鲜度来源初始与缺失状态一致，后续可能提升为验证时间。
    str_freshness_source = "missing"  # 最终新鲜度基准来源

    # 只有根规则存在时才解析其元数据。
    if agents.exists():

        # 忽略局部编码损坏仍可提取 ASCII 元数据标记。
        text = agents.read_text(encoding="utf-8", errors="ignore")  # 根规则完整文本

        # 验证标记是最强的新鲜度证据候选。
        verified_match = VERIFIED_RE.search(text)  # Last verified 匹配结果

        # 匹配成功时同时保留原文与解析值。
        if verified_match:

            # 捕获组只包含 ISO 时间本体。
            last_verified_raw = verified_match.group(1)  # 验证时间元数据原文

            # 格式非法时解析器返回空并保留原文供诊断。
            last_verified = parse_datetime(last_verified_raw)  # 可比较的验证时间

        # 优先读取带秒的现代更新时间格式。
        timestamp_match = TIMESTAMP_RE.search(text)  # 完整更新时间匹配结果

        # 完整时间戳可直接作为提交变更查询基准。
        if timestamp_match:

            # 元数据原文与解析值分别写入输出合同。
            last_updated_raw = timestamp_match.group(1)  # 更新时间元数据原文

            # ISO 解析失败会使来源保持 missing。
            last_updated = parse_datetime(last_updated_raw)  # 可比较的更新时间

            # 仅合法解析值可以声明来自元数据时间戳。
            str_comparison_source = "metadata_timestamp" if last_updated else "missing"  # 更新时间来源分类

        # 未找到秒级格式时尝试兼容旧版日期标记。
        else:

            # 日期匹配仅证明维护日，精确时间优先向 Git 查询。
            date_match = DATE_RE.search(text)  # 旧版维护日期匹配结果

            # 旧日期存在时启动 Git、文件时间和午夜三级回退。
            if date_match:

                # 保留 YYYY-MM-DD 原文供兼容性报告。
                last_updated_raw = date_match.group(1)  # 旧版维护日期原文

                # 最近提交时间是旧日期格式下的首选精确事实。
                last_updated = git_commit_time_for_file(path_project, agents)  # 根规则最近 Git 提交时间

                # Git 时间可用时明确记录证据来源。
                if last_updated is not None:

                    # 提交时间比仅有日期的元数据更精确。
                    str_comparison_source = "git_commit_time"  # Git 提交时间来源

                # 未跟踪文件继续尝试本地修改时间。
                else:

                    # 文件系统时间保持秒级精度但不具备提交证明。
                    last_updated = file_mtime(agents)  # 根规则本地修改时间

                    # 可访问的 mtime 作为第二级比较来源。
                    if last_updated is not None:

                        # 输出明确区分文件时间与版本库证据。
                        str_comparison_source = "file_mtime"  # 本地文件修改时间来源

                    # 文件时间也不可用时只能把维护日解释为当天午夜。
                    else:

                        # 午夜回退保持旧元数据可比较且诚实降低证据强度。
                        fallback = parse_datetime(f"{last_updated_raw}T00:00:00")  # 旧维护日的午夜时间

                        # 统一写入更新时间变量供后续选择新鲜度基准。
                        last_updated = fallback  # 日期兼容路径的更新时间

                        # 解析失败时仍保持 missing，禁止伪造可用时间。
                        str_comparison_source = (  # 日期回退来源分类
                            "date_midnight_fallback"  # 旧日期成功转换后的来源
                            if fallback  # 仅合法日期允许声明回退来源
                            else "missing"  # 非法日期没有可用比较事实
                        )

    # 更新时间先作为默认的新鲜度基准。
    freshness_time = last_updated  # 当前选择的新鲜度时间

    # 来源与默认时间同步，后续可由更新的验证时间替换。
    str_freshness_source = str_comparison_source  # 当前选择的新鲜度来源

    # 不早于更新时间的验证标记证明规则在更晚时间被复核。
    if last_verified and (
        not last_updated
        or comparable_datetime(last_verified) >= comparable_datetime(last_updated)
    ):

        # 使用较新的验证时间缩小待检查变更范围。
        freshness_time = last_verified  # 最终采用的验证时间

        # 新鲜度来源对外声明为显式验证元数据。
        str_freshness_source = "last_verified"  # 最终验证来源

        # 比较来源同步更新，保持两个兼容字段一致。
        str_comparison_source = "last_verified"  # 兼容输出中的验证来源

    # 有时间基准时查询其后的提交文件。
    if freshness_time:

        # 空提交标题输出只保留文件路径，便于稳定去重。
        git_result = run_git(  # 新鲜度基准后的 Git 文件日志
            path_project,  # Git 仓库根目录
            ["log", "--name-only", "--pretty=format:", f"--since={normalize_datetime(freshness_time)}"],  # 文件日志参数
        )

    # 缺少任何时间事实时以当前工作树变更作为保守证据。
    else:

        # 短状态同时覆盖已跟踪和未跟踪文件。
        git_result = run_git(path_project, ["status", "--short"])  # 当前工作树状态结果

    # Git 命令成功后才解释其标准输出。
    if git_result.returncode == 0:

        # 根规则自身不算“规则之后的项目变化”，其余路径稳定去重。
        list_changed_files = sorted(  # 晚于基准且可能使规则陈旧的文件
            {  # 去重后的变更路径集合
                line.strip()  # 去除 Git 输出前后空白
                for line in git_result.stdout.splitlines()  # 遍历每个日志或状态行
                if line.strip() and not line.strip().endswith("AGENTS.md")  # 排除空行和规则自身
            }
        )

    # 协议同时输出原始元数据、规范时间、来源与具体变更路径。
    emit_json({
        "agents_file": str(agents),
        "last_updated": normalize_datetime(last_updated) if last_updated else None,
        "last_updated_raw": last_updated_raw,
        "last_updated_at": normalize_datetime(last_updated) if last_updated else None,
        "last_verified": normalize_datetime(last_verified) if last_verified else None,
        "last_verified_raw": last_verified_raw,
        "last_verified_at": normalize_datetime(last_verified) if last_verified else None,
        "comparison_source": str_comparison_source,
        "freshness_source": str_freshness_source,
        "stale": bool(list_changed_files) or freshness_time is None,
        "changed_files": list_changed_files,
    })

# 直接执行脚本时启动新鲜度检查 CLI。
if __name__ == "__main__":

    # 导入模块不会产生文件或终端副作用。
    main()

