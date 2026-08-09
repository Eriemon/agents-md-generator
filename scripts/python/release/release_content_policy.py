"""定义发布目录内容白名单、禁入项和收据一致性规则。"""

# 延迟注解求值以保持 Python 3.10 兼容。
from __future__ import annotations

# 路径对象负责跨平台相对路径和后缀解析。
from pathlib import Path
from typing import Any

# 策略版本写入发布收据，用于检测规则漂移。
POLICY_VERSION = "2026-05-26-v2"  # 当前发布内容策略版本

# 顶层普通文件只排除明确禁入项，不执行封闭白名单。
TOP_LEVEL_FILE_MODE = "allow-nonforbidden-files"  # 顶层文件接纳模式

# 标准技能根文件用于收据说明和兼容校验。
ALLOWED_TOP_LEVEL_FILES = {  # 标准技能根文件集合
    "README.md",  # 技能使用说明
    "SKILL.md",  # Codex 技能入口
    "VERSION",  # 技能版本事实
}

# 收据由打包流程后置生成，不计入内容分析结果。
IGNORED_TOP_LEVEL_FILES = {  # 内容扫描忽略的根文件
    "RELEASE_RECEIPT.json",  # 发布收据本身
}

# 可安装技能允许携带的正式内容目录。
ALLOWED_TOP_LEVEL_DIRS = {  # 非白名单根目录会写入意外顶层项并阻断发布
    "agents",  # 安装后供 Codex 发现的代理元数据
    "assets",  # 技能运行时读取的模板与静态资源
    "config",  # 控制正式运行行为的配置文件
    "docs",  # 完整仓库 ZIP 中的公开治理与交接文档
    "evals",  # 随包交付的技能评估用例
    "integration",  # 对接外部工具所需的集成资产
    "references",  # Agent 执行任务时查阅的治理参考
    "runtime",  # 技能正式执行依赖的运行时资源
    "scripts",  # 安装后可调用的技能实现脚本
}

# 测试、运行报告和工具缓存不得进入安装包。
FORBIDDEN_EXACT_NAMES = {  # 精确命中名称会写入禁入路径并从正式文件清单剔除
    "tests",  # 仓库级复数测试目录不得随包安装
    "test",  # 单数测试目录同样属于开发资产
    "reports",  # 本地验证报告不属于技能运行内容
    "runs",  # 会话运行产物可能包含机器本地事实
    "_smoke_runs",  # 冒烟执行目录仅用于开发验证
    "__pycache__",  # Python 字节码依赖生成环境版本
    ".pytest_cache",  # pytest 状态仅服务测试增量执行
    ".mypy_cache",  # 类型检查索引不参与技能运行
    ".ruff_cache",  # 代码检查索引不参与技能运行
}

# smoke 前缀覆盖带时间戳或场景后缀的冒烟产物。
FORBIDDEN_PREFIXES = ("smoke",)  # 禁入路径分量前缀

# 编译后的 Python 文件不属于源码技能发布内容。
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}  # 禁入文件后缀

# 判断单个路径分量是否属于禁入名称。
def is_forbidden_component(name: str) -> bool:
    """检查一个路径分量是否命中禁入规则。

    参数：
        name: 未规范化的文件或目录名称。
    返回：
        命中精确名称或禁入前缀时返回真。
    """

    # 大小写和首尾空白不应绕过发布策略。
    str_lowered_name = name.strip().lower()  # 规范化路径分量

    # 空路径分量不构成实际文件或目录。
    if not str_lowered_name:

        # 调用方可以继续检查其他有效分量。
        return False

    # 精确禁入名称优先于前缀规则。
    if str_lowered_name in FORBIDDEN_EXACT_NAMES:

        # 明确拒绝测试、报告或缓存目录。
        return True

    # 前缀规则覆盖 smoke 变体名称。
    return any(str_lowered_name.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)

# 判断相对路径是否包含禁入分量或文件后缀。
def is_forbidden_relative_path(relative_path: str) -> bool:
    """检查发布相对路径是否违反内容策略。

    参数：
        relative_path: 使用任意平台分隔符的相对路径。
    返回：
        任一路径分量或最终后缀被禁止时返回真。
    """

    # 统一分隔符并去掉路径两端的冗余斜杠。
    str_normalized_path = relative_path.replace("\\", "/").strip().strip("/")  # 规范化相对路径

    # 空相对路径表示扫描根本身，不属于禁入内容。
    if not str_normalized_path:

        # 根目录由调用方继续遍历。
        return False

    # 去除空分量后再执行名称检查。
    list_path_parts = [part for part in str_normalized_path.split("/") if part]  # 有效路径分量

    # 任一目录层级命中禁入名称即可拒绝整条路径。
    if any(is_forbidden_component(part) for part in list_path_parts):

        # 上层分析器会记录完整相对路径。
        return True

    # 最终文件后缀用于识别 Python 编译产物。
    str_file_suffix = Path(list_path_parts[-1]).suffix.lower()  # 最末路径分量后缀

    # 返回后缀是否属于发布禁入集合。
    return str_file_suffix in FORBIDDEN_SUFFIXES

# 扫描发布根并归类正式文件、禁入路径和意外顶层项。
def _scan_release_root(root: Path) -> tuple[list[str], list[str], set[str]]:
    """收集发布目录的三类内容事实。

    参数：
        root: 待分析的发布内容根目录。
    返回：
        正式文件、禁入路径和意外顶层项组成的元组。
    """

    # 三个容器分别服务收据文件表、阻断列表和顶层结构检查。
    list_included_files: list[str] = []  # 允许进入发布包的文件

    # 污染路径保留完整相对位置供发布门禁报告。
    list_forbidden_paths: list[str] = []  # 命中禁入规则的相对路径

    # 顶层异常使用集合避免同一目录产生重复诊断。
    set_unexpected_entries: set[str] = set()  # 不在目录白名单中的顶层项

    # 稳定排序保证不同文件系统上的收据结果一致。
    for path_entry in sorted(root.rglob("*")):

        # POSIX 形式用于发布收据和跨平台比较。
        str_relative_path = path_entry.relative_to(root).as_posix()  # 当前条目相对路径

        # pathlib 分量用于识别顶层归属。
        tuple_path_parts = Path(str_relative_path).parts  # 当前相对路径分量

        # rglob 正常不会返回空分量，防御分支保持路径索引安全。
        if not tuple_path_parts:

            # 跳过无法形成发布条目的根路径。
            continue

        # 第一个分量决定目录白名单归属。
        str_top_level = tuple_path_parts[0]  # 当前条目的顶层名称

        # 禁入路径优先记录，不再重复归入意外目录。
        if is_forbidden_relative_path(str_relative_path):

            # 完整路径帮助发布门禁定位污染来源。
            list_forbidden_paths.append(str_relative_path)

            # 当前污染项无需继续判断包内容资格。
            continue

        # 后置生成的根收据不参与待发布内容统计。
        if len(tuple_path_parts) == 1 and str_top_level in IGNORED_TOP_LEVEL_FILES:

            # 忽略收据避免自引用导致计数漂移。
            continue

        # 非白名单目录及其子项统一登记顶层名称。
        bool_unexpected_directory = (  # 当前条目是否来自意外顶层目录
            path_entry.is_dir() and len(tuple_path_parts) == 1  # 顶层目录自身
        ) or len(tuple_path_parts) > 1  # 顶层目录内的任意后代

        # 只有目录结构需要受封闭白名单约束。
        if bool_unexpected_directory and str_top_level not in ALLOWED_TOP_LEVEL_DIRS:

            # 集合去重让一个异常目录只产生一个顶层诊断。
            set_unexpected_entries.add(str_top_level)

            # 意外目录内容不计入正式发布文件。
            continue

        # 目录本身不进入发布文件清单。
        if path_entry.is_file():

            # 合法文件保留相对路径供收据记录。
            list_included_files.append(str_relative_path)

    # 返回三个容器，由上层组装稳定策略报告。
    return list_included_files, list_forbidden_paths, set_unexpected_entries

# 分析发布内容根并生成完整策略事实。
def analyze_release_content_root(
    root: Path,
    *,
    allow_source_only_repo_local: bool = False,
) -> dict[str, Any]:
    """分析发布目录并返回内容策略报告。

    参数：
        root: 待分析的技能内容根目录。
        allow_source_only_repo_local: 保留的兼容参数，当前策略不接纳源码专属目录。
    返回：
        策略版本、允许项、正式文件和阻断项组成的报告。
    """

    # 兼容参数显式消费，避免调用方接口漂移。
    _ = allow_source_only_repo_local  # 当前版本不启用源码专属目录例外

    # 扫描过程与报告组装分离，便于验证分类行为。
    tuple_scan_result = _scan_release_root(root)  # 正式文件、污染路径与顶层异常

    # 第一个扫描分量是允许进入发布包的文件清单。
    list_included_files = tuple_scan_result[0]  # 正式发布文件

    # 第二个扫描分量保留所有禁入路径。
    list_forbidden_paths = tuple_scan_result[1]  # 发布包污染路径

    # 第三个扫描分量聚合意外顶层名称。
    set_unexpected_entries = tuple_scan_result[2]  # 非白名单顶层项

    # 顶层集合便于收据快速证明正式内容覆盖范围。
    list_included_top_levels = sorted(  # 正式文件涉及的顶层名称
        {Path(path).parts[0] for path in list_included_files},  # 从每个文件抽取首个分量
    )

    # 返回字段名称保持现有发布收据协议。
    return {
        "policy_version": POLICY_VERSION,  # 本次分析采用的规则身份
        "top_level_file_mode": TOP_LEVEL_FILE_MODE,  # 普通根文件的接纳合同
        "allowed_top_level_files": sorted(ALLOWED_TOP_LEVEL_FILES),  # 技能根标准文件声明
        "allowed_top_level_dirs": sorted(ALLOWED_TOP_LEVEL_DIRS),  # 安装内容功能分区声明
        "forbidden_exact_names": sorted(FORBIDDEN_EXACT_NAMES),  # 开发产物逐级拒绝规则
        "forbidden_prefixes": sorted(FORBIDDEN_PREFIXES),  # 冒烟产物识别前缀
        "forbidden_suffixes": sorted(FORBIDDEN_SUFFIXES),  # Python 编译产物拒绝后缀
        "source_only_prefixes": [],  # 当前策略未启用源码专属例外
        "included_files": sorted(list_included_files),  # 正式文件清单
        "included_file_count": len(list_included_files),  # 收据声明的文件总数
        "included_top_level_entries": list_included_top_levels,  # 正式顶层覆盖
        "unexpected_top_level_entries": sorted(set_unexpected_entries),  # 意外顶层项
        "forbidden_paths": sorted(list_forbidden_paths),  # 发布根内禁入路径
    }

# 从分析报告提取写入发布收据的稳定字段。
def release_content_policy_receipt(
    analysis: dict[str, Any],
    *,
    forbidden_source_paths: list[str] | None = None,
) -> dict[str, Any]:
    """生成发布内容策略的收据区块。

    参数：
        analysis: analyze_release_content_root 生成的策略报告。
        forbidden_source_paths: 源码目录扫描发现的禁入路径。
    返回：
        可序列化并用于安装复核的策略收据。
    """

    # 收据只复制安装复核需要的稳定策略字段。
    return {
        "policy_version": analysis["policy_version"],  # 重放检查采用的规则版本
        "top_level_file_mode": analysis["top_level_file_mode"],  # 普通根文件接纳方式
        "allowed_top_level_files": list(analysis["allowed_top_level_files"]),  # 标准技能根文件声明
        "allowed_top_level_dirs": list(analysis["allowed_top_level_dirs"]),  # 可安装内容目录声明
        "forbidden_exact_names": list(analysis["forbidden_exact_names"]),  # 任意层级禁入名称声明
        "forbidden_prefixes": list(analysis["forbidden_prefixes"]),  # 冒烟产物识别规则
        "forbidden_suffixes": list(analysis["forbidden_suffixes"]),  # 编译产物拒绝规则
        "included_file_count": analysis["included_file_count"],  # 发布文件总量证明
        "included_top_level_entries": list(analysis["included_top_level_entries"]),  # 正式内容覆盖证明
        "unexpected_top_level_entries": list(analysis["unexpected_top_level_entries"]),  # 目录白名单偏差证明
        "forbidden_source_paths": sorted(forbidden_source_paths or []),  # 源码树污染扫描结果
        "forbidden_release_paths": list(analysis["forbidden_paths"]),  # 成品目录污染扫描结果
    }

# 校验收据中的发布内容策略是否匹配当前分析结果。
def validate_recorded_release_content_policy(
    recorded: Any,
    release_analysis: dict[str, Any],
    *,
    forbidden_source_paths: list[str] | None = None,
    require_source_paths: bool = True,
) -> list[str]:
    """比较已记录策略收据与当前发布内容事实。

    参数：
        recorded: 发布收据中的策略区块。
        release_analysis: 对发布目录重新生成的策略报告。
        forbidden_source_paths: 当前源码扫描发现的禁入路径。
        require_source_paths: 是否要求源码污染列表完全一致。
    返回：
        每个不一致字段对应的一条英文兼容错误消息。
    """

    # 缺失或错误类型的策略区块无法继续逐字段比较。
    if not isinstance(recorded, dict):

        # 保留安装器和发布门禁依赖的历史错误文本。
        return ["release content policy block is missing"]

    # 可选模式仅校验源码污染字段为列表，不要求内容一致。
    list_expected_source_paths = forbidden_source_paths if require_source_paths else None  # 收据期望的源码污染路径

    # 当前事实转换为与收据相同的字段集合。
    dict_expected = release_content_policy_receipt(  # 期望的发布内容策略收据
        release_analysis,  # 当前发布目录分析结果
        forbidden_source_paths=list_expected_source_paths,  # 按模式提供源码污染路径
    )

    # 普通字段共享完全相等的校验规则。
    tuple_policy_fields = (  # 必须与当前分析一致的收据字段
        "policy_version",  # 防止旧版规则收据被继续接受
        "top_level_file_mode",  # 约束根文件的开放或封闭模式
        "allowed_top_level_files",  # 核对标准技能文件声明
        "allowed_top_level_dirs",  # 核对可安装功能分区声明
        "forbidden_exact_names",  # 核对开发产物拒绝名称
        "forbidden_prefixes",  # 核对冒烟目录识别方式
        "forbidden_suffixes",  # 核对编译文件拒绝方式
        "included_file_count",  # 证明文件总量没有漂移
        "included_top_level_entries",  # 证明正式内容覆盖范围
        "unexpected_top_level_entries",  # 证明目录白名单没有偏差
        "forbidden_release_paths",  # 证明成品目录没有污染项
    )

    # 错误列表保持字段检查顺序，便于测试和人工诊断。
    list_errors: list[str] = []  # 收据字段不一致消息

    # 逐字段比较保留既有错误消息格式。
    for str_field_name in tuple_policy_fields:

        # 只有值不一致的字段才产生诊断。
        if recorded.get(str_field_name) != dict_expected[str_field_name]:

            # 英文错误文本是安装器对外兼容协议。
            list_errors.append(f"release content policy field mismatch: {str_field_name}")

    # 严格模式要求源码扫描事实完全一致。
    if require_source_paths and recorded.get("forbidden_source_paths") != dict_expected["forbidden_source_paths"]:

        # 单独字段名保持历史诊断可检索。
        list_errors.append("release content policy field mismatch: forbidden_source_paths")

    # 宽松模式仍要求收据提供列表类型以证明字段存在。
    elif not require_source_paths and not isinstance(recorded.get("forbidden_source_paths"), list):

        # 类型错误与内容不一致使用不同兼容消息。
        list_errors.append("release content policy forbidden_source_paths must be a list")

    # 返回全部不一致项供发布或安装门禁聚合。
    return list_errors
