"""校验技能公开产品文件、版本元数据与 README PNG 插图合同。"""

# 延迟类型标注求值，保持发布工具兼容 Python 3.10。
from __future__ import annotations

# 标准库足以完成文本、版本、正则与 PNG 头检查。
import re
from pathlib import Path
from typing import Any

# 每个受管理技能必须提供这些公开入口文件。
REQUIRED_PUBLIC_FILES = (
    "SKILL.md",  # Codex 技能执行入口
    "VERSION",  # 发布版本事实源
    "LICENSE",  # 公开许可声明
    "README.md",  # 英文产品说明
    "README-CN.md",  # 中文产品说明
    "SECURITY.md",  # 安全问题报告入口
    "pyproject.toml",  # Python 元数据合同
    "CONTRIBUTING.md",  # 贡献流程入口
    "CITATION.cff",  # 学术引用元数据
)

# 双语产品说明必须都声明本地 PNG 插图。
README_FILES = (
    "README.md",  # 英文产品说明入口
    "README-CN.md",  # 中文产品说明入口
)

# PNG 头和最小尺寸防止占位图进入正式包。
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"  # PNG 文件签名

# 宽度阈值保证产品页插图在桌面阅读时仍然清晰。
MIN_README_IMAGE_WIDTH = 1600  # README 插图最低像素宽度

# 高度阈值保证宽屏截图不会被压缩成不可读缩略图。
MIN_README_IMAGE_HEIGHT = 900  # README 插图最低像素高度

# Markdown 图片语法只提取目标路径，不解析标题文本。
README_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")  # 图片目标匹配器

# 公开说明不得遗留未完成占位符。
PLACEHOLDER_PATTERN = re.compile(  # 占位文本匹配器
    r"TODO|TBD|PLACEHOLDER|待补充|待填写|\{[^{}]+\}",  # 中英文占位符模式
    re.IGNORECASE,  # 忽略占位符大小写差异
)

# 版本文本统一移除 v 前缀后再比较。
def _normalized_version(value: str) -> str:
    """归一化版本文本。

    参数:
        value: VERSION、pyproject 或 CITATION 中的版本文本。

    返回:
        去除 v 前缀后的语义版本文本。

    异常:
        无；不符合版本模式的文本原样归一化。
    """

    # 去除空白和可选前缀，保持不同元数据写法可比较。
    str_normalized = value.strip().lstrip("vV")  # 版本比较主体

    # 只捕获主版本与可选预发布后缀，避免正文日期误判。
    match_version = re.search(  # 提取语义版本片段
        r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?",  # 主版本和预发布后缀模式
        str_normalized,  # 在归一化版本文本中搜索模式
    )

    # 不符合模式时保留归一化原文，便于输出精确诊断。
    return match_version.group(0) if match_version else str_normalized

# 公开文本读取失败时返回空文本，允许一次报告全部缺陷。
def _read_text(path_file: Path) -> str:
    """读取 UTF-8 文本文件。

    参数:
        path_file: 需要读取的公开文本路径。

    返回:
        文件文本；读取失败时返回空字符串。

    异常:
        无；文件系统错误被转换为空文本。
    """

    # 读取失败不应阻断其他公开文件的独立检查。
    try:

        # 统一替换坏字节，确保报告始终可序列化。
        return path_file.read_text(encoding="utf-8", errors="replace")

    # 不存在或不可读文件由调用方按缺失内容继续报告。
    except OSError:

        # 返回空文本让后续正则检查安全结束。
        return ""

# 仅读取 PNG 头部即可完成静态尺寸检查。
def _png_dimensions(path_image: Path) -> tuple[int, int] | None:
    """读取 PNG IHDR 尺寸。

    参数:
        path_image: README 引用的候选 PNG 路径。

    返回:
        `(width, height)`；文件不是完整 PNG 时返回 None。

    异常:
        无；读取失败统一返回 None。
    """

    # 头部 24 字节包含签名、IHDR 标记和宽高字段。
    try:

        # 只读取门禁所需的最小字节范围。
        bytes_header = path_image.read_bytes()[:24]  # PNG 头部字节

    # 图片缺失或不可读时交由上层生成稳定错误。
    except OSError:

        # None 表示不能证明它是有效 PNG。
        return None

    # 签名或固定头长度不满足时拒绝继续解析。
    if len(bytes_header) < 24 or not bytes_header.startswith(PNG_SIGNATURE):

        # 截断或非 PNG 内容不能作为插图证据。
        return None

    # IHDR 标记缺失时宽高字段不具备 PNG 语义。
    if bytes_header[12:16] != b"IHDR":

        # 返回 None 让调用方报告格式错误。
        return None

    # PNG 宽高按网络字节序存储，转换为整数供尺寸门禁比较。
    int_width = int.from_bytes(bytes_header[16:20], "big")  # 插图宽度

    # 高度字段紧随宽度字段并使用相同字节序。
    int_height = int.from_bytes(bytes_header[20:24], "big")  # 插图高度

    # 返回已验证头部中的尺寸事实。
    return int_width, int_height

# 提取 Markdown 图片目标并剥离可选标题。
def _readme_asset_references(path_readme: Path) -> list[str]:
    """提取 README 图片目标。

    参数:
        path_readme: 双语 README 文件路径。

    返回:
        Markdown 图片目标的稳定列表。

    异常:
        无；不可读 README 返回空列表。
    """

    # 读取文本后按 Markdown 图片语法收集目标。
    str_readme = _read_text(path_readme)  # 当前语言入口的完整 README 文本

    # 列表保存双语说明中声明的本地资源。
    list_references: list[str] = []  # 图片目标列表

    # 每个图片目标都要单独做路径和格式门禁。
    for str_target in README_IMAGE_PATTERN.findall(str_readme):

        # 去掉目标两端空白，避免空格改变路径判定。
        str_reference = str_target.strip()  # 原始图片引用

        # 尖括号包裹的路径允许空格，因此先取括号内部。
        if str_reference.startswith("<") and ">" in str_reference:

            # 截取尖括号内的完整资源路径。
            str_reference = str_reference[1 : str_reference.index(">")]  # 尖括号内的资源路径

        # 普通目标的第一个空白前内容才是路径。
        else:

            # 标题文本不应被当作资源路径。
            str_reference = str_reference.split()[0] if str_reference.split() else ""  # 普通目标的首个路径词

        # 空目标没有可验证的资产路径，仍由缺失资源规则报告。
        if str_reference:

            # 保留清理后的相对或绝对目标。
            list_references.append(str_reference)

    # 返回去重前列表，调用方决定是否保留重复插图证据。
    return list_references

# 收集公开文件存在性与符号链接问题。
def _required_file_report(root: Path) -> tuple[list[str], list[str], list[str]]:
    """检查必需公开文件。

    参数:
        root: 技能源码或 dist 根目录。

    返回:
        `(missing, checked, errors)` 三元组。

    异常:
        无；路径问题转换为稳定错误文本。
    """

    # 缺失列表先固定顺序，避免报告受文件系统遍历顺序影响。
    list_missing = [  # 缺少的公开入口文件
        str_name  # 返回缺失文件名
        for str_name in REQUIRED_PUBLIC_FILES  # 遍历公开文件合同
        if not (root / str_name).is_file()  # 只接受普通文件
    ]

    # 错误列表同时记录缺失项，供 CLI 直接返回。
    list_errors = [  # 缺失文件诊断
        f"missing required public file: {str_name}"  # 稳定错误文本
        for str_name in list_missing  # 遍历缺失文件
    ]

    # checked 记录存在的合同文件，便于审计显示覆盖范围。
    list_checked: list[str] = []  # 已检查文件列表

    # 逐项拒绝符号链接，防止公开入口逃逸技能根目录。
    for str_name in REQUIRED_PUBLIC_FILES:

        # 计算当前公开文件的绝对候选路径。
        path_file = root / str_name  # 当前公开文件路径

        # 只对已存在的文件记录 checked 状态。
        if path_file.exists():

            # 记录存在的公开入口。
            list_checked.append(str_name)

            # 符号链接不能作为正式公开文件证据。
            if path_file.is_symlink():

                # 记录具体文件名，避免调用方再次遍历目录。
                list_errors.append(f"required public file is symlink: {str_name}")

    # 返回缺失、已检查和符号链接错误。
    return list_missing, list_checked, list_errors

# 收集三处版本元数据的一致性报告。
def _version_report(root: Path) -> tuple[dict[str, str], list[str]]:
    """检查 VERSION、pyproject 与 CITATION 版本。

    参数:
        root: 技能源码或 dist 根目录。

    返回:
        `(versions, errors)` 版本映射及诊断列表。

    异常:
        无；读取失败转为缺失元数据错误。
    """

    # 版本映射保存每个元数据文件的归一化版本。
    dict_versions: dict[str, str] = {}  # 版本事实集合

    # 错误列表承载缺失声明和不一致结果。
    list_errors: list[str] = []  # 版本门禁错误

    # VERSION 是技能发布版本的首要事实源。
    path_version = root / "VERSION"  # VERSION 文件路径

    # 只在普通文件存在时读取版本主体。
    str_version = _normalized_version(_read_text(path_version)) if path_version.is_file() else ""  # 源码 VERSION 的归一化值

    # 记录可用的 VERSION 事实供其他元数据比较。
    if str_version:

        # 保存源码版本作为比较基线。
        dict_versions["VERSION"] = str_version  # 保存源码版本比较基线

    # 读取 TOML 项目元数据，后续从中抽取 project.version。
    str_pyproject = _read_text(root / "pyproject.toml")  # 读取 TOML 项目元数据文本

    # 读取 TOML 常见的键值格式。
    match_pyproject = re.search(  # 提取 TOML project.version 的匹配对象
        r"(?m)^\s*version\s*=\s*[\"']([^\"']+)[\"']",  # 限定 TOML version 键并捕获引号值
        str_pyproject,  # 在 TOML 文本中匹配版本字段
    )

    # 缺失声明直接进入错误载荷。
    if match_pyproject:

        # 写入归一化版本供一致性比较。
        dict_versions["pyproject.toml"] = _normalized_version(match_pyproject.group(1))  # 保存 TOML 版本

    # pyproject 没有版本字段时必须明确报错。
    else:

        # 不允许通过空元数据绕过版本一致性门禁。
        list_errors.append("pyproject.toml must declare project version")

    # CITATION.cff 同样必须声明版本。
    str_citation = _read_text(root / "CITATION.cff")  # Citation 元数据文本

    # CFF 版本字段通常使用无引号 YAML 标量。
    match_citation = re.search(  # 解析 CFF 引用版本声明
        r"(?m)^\s*version:\s*([^#\r\n]+)",  # CFF version 字段模式
        str_citation,  # 把 CFF 文本交给版本字段正则解析
    )

    # 存在声明时纳入版本事实集合。
    if match_citation:

        # 清理行尾空白并去除可选 v 前缀。
        dict_versions["CITATION.cff"] = _normalized_version(match_citation.group(1).strip())  # 记录 Citation 版本事实

    # 缺少 Citation 版本时阻断公开包。
    else:

        # 保持错误文本可被 CLI 的 error_kinds 分类。
        list_errors.append("CITATION.cff must declare version")

    # 多处元数据必须收敛到同一个版本值。
    list_version_values = list(dict_versions.values())  # 参与比较的版本列表

    # 只有存在版本事实时才比较集合基数。
    if list_version_values and len(set(list_version_values)) != 1:

        # 不同版本会让 dist 和源码产生不可追溯漂移。
        list_errors.append("public skill version metadata mismatch")

    # 返回版本事实与独立诊断。
    return dict_versions, list_errors

# 检查许可证、贡献和安全文件中的公开文本质量。
def _text_contract_report(root: Path) -> list[str]:
    """检查许可证与公共说明文本。

    参数:
        root: 技能源码或 dist 根目录。

    返回:
        许可证、占位符相关错误列表。

    异常:
        无；不可读文件由空文本策略处理。
    """

    # 错误列表只记录违反公开文本合同的事实。
    list_errors: list[str] = []  # 文本合同错误

    # Apache 2.0 是当前公开技能包最低许可要求。
    str_license = _read_text(root / "LICENSE")  # 许可证文本

    # 缺失文件已由必需文件报告记录，存在时检查关键法律标识。
    if str_license and ("Apache License" not in str_license or "Version 2.0" not in str_license):

        # 许可证不完整时拒绝公开发布。
        list_errors.append("LICENSE must contain Apache License Version 2.0")

    # 安全、贡献和引用文件不得留下未完成占位符。
    for str_name in ("SECURITY.md", "CONTRIBUTING.md", "CITATION.cff"):

        # 读取当前公开说明文本。
        str_content = _read_text(root / str_name)  # 当前公开文件文本

        # 只在文件有内容时检查占位符。
        if str_content and PLACEHOLDER_PATTERN.search(str_content):

            # 记录文件名，避免把具体占位符全文暴露到日志。
            list_errors.append(f"public file contains placeholder text: {str_name}")

    # 返回文本合同错误。
    return list_errors

# 检查 README 图片必须是本地高分辨率 PNG。
def _readme_contract_report(
    root: Path,
    *,
    enforce_resolution: bool,
) -> tuple[list[str], list[str], dict[str, list[dict[str, Any]]]]:
    """检查双语 README 插图合同。

    参数:
        root: 技能源码或 dist 根目录。
        enforce_resolution: 是否执行正式发布的最小像素门禁。

    返回:
        `(errors, assets, images)` 错误、资产路径和 README 图像事实。

    异常:
        无；路径和读取错误转为稳定诊断。
    """

    # 错误和资产列表保持分离，收据只记录通过路径。
    list_errors: list[str] = []  # README 插图错误

    # 资产列表只保存已经通过路径和尺寸检查的 PNG。
    list_assets: list[str] = []  # README 本地资产

    # 图像事实供 CLI 直接显示尺寸，而不是让调用方重新读取 PNG。
    dict_images: dict[str, list[dict[str, Any]]] = {}  # 双语 README 图像事实

    # 双语 README 逐个执行同一套图片规则。
    for str_name in README_FILES:

        # 计算当前 README 的文件路径。
        path_readme = root / str_name  # 当前 README 路径

        # 缺失 README 已由公开文件报告记录。
        if not path_readme.is_file():

            # 继续检查另一种语言的入口。
            continue

        # 读取 README 文本以检查禁止的矢量或流程图占位内容。
        str_readme = _read_text(path_readme)  # 当前 README 文本

        # Mermaid 不是正式插图资产，必须在发布前被替换为 PNG。
        if "```mermaid" in str_readme or re.search(r"(?im)^\s*(flowchart|graph\s+TD)\b", str_readme):

            # 记录语言入口，便于修复双语不一致。
            list_errors.append(f"README must use raster illustrations instead of Mermaid: {str_name}")

        # 提取 Markdown 图片目标并要求至少一个本地 PNG。
        list_references = _readme_asset_references(path_readme)  # 当前 README 图片引用

        # 没有插图说明技能产品页未完成。
        if not list_references:

            # 明确要求本地 PNG 资产而不是远程链接。
            list_errors.append(f"README must include a local PNG illustration: {str_name}")

        # 每个引用都要通过路径、格式和分辨率检查。
        for str_reference in list_references:

            # SVG 作为插图被明确禁止。
            if str_reference.lower().endswith(".svg"):

                # 输出语言入口而不重复整段 Markdown。
                list_errors.append(f"README illustration must not be SVG: {str_name}")

            # 远程 URL 不属于技能包自包含资产。
            if str_reference.startswith(("http://", "https://", "//")):

                # 远程资源使离线安装和审计不可复现。
                list_errors.append(f"README illustration must be local: {str_name}")

                # 远程路径无法继续做本地解析。
                continue

            # 规范化本地目标并验证它仍在技能根目录内。
            path_asset = (path_readme.parent / str_reference).resolve()  # 规范化插图路径

            # root.resolve 是路径越界比较的固定边界。
            path_root_resolved = root.resolve()  # 技能根绝对路径

            # 相对路径失败表示 README 试图跳出技能包。
            try:

                # 只有位于根目录内的资产才允许继续校验。
                path_asset.relative_to(path_root_resolved)

            # 越界路径不能作为公开资产。
            except ValueError:

                # 记录语言入口，避免暴露宿主机路径。
                list_errors.append(f"README illustration escapes skill root: {str_name}")

                # 不再读取越界目标。
                continue

            # 符号链接或缺失文件都不能证明资产已随包交付。
            if path_asset.is_symlink() or not path_asset.is_file():

                # 记录原始引用便于修复 README。
                list_errors.append(f"README illustration is missing: {str_reference}")

                # 后续尺寸读取没有安全输入。
                continue

            # 读取 PNG 头和 IHDR 尺寸。
            tuple_dimensions = _png_dimensions(path_asset)  # 插图尺寸事实

            # 无效 PNG 不能用扩展名伪装通过。
            if tuple_dimensions is None:

                # 记录原始引用便于替换坏资产。
                list_errors.append(f"README illustration is not a valid PNG: {str_reference}")

                # 不对无效头部做尺寸比较。
                continue

            # 拆出宽高后执行最小清晰度门禁。
            int_width = tuple_dimensions[0]  # 插图像素宽度

            # 宽度读取后单独保存高度，供双向清晰度比较。
            int_height = tuple_dimensions[1]  # 插图像素高度

            # 正式发布包必须清晰；轻量源码预检仍证明 PNG 有效但不替代设计评审。
            if enforce_resolution and (
                int_width < MIN_README_IMAGE_WIDTH or int_height < MIN_README_IMAGE_HEIGHT
            ):

                # 记录引用，保留具体修复目标。
                list_errors.append(f"README illustration is below minimum resolution: {str_reference}")

            # 保留每个 README 引用的可验证尺寸事实。
            dict_images.setdefault(str_name, []).append(
                {
                    "path": str_reference,
                    "width": int_width,
                    "height": int_height,
                }
            )

            # 保存相对路径，供审计和收据复核。
            str_relative_asset = path_asset.relative_to(path_root_resolved).as_posix()  # 资产相对路径

            # 资产通过所有门禁后才进入收据路径集合。
            list_assets.append(str_relative_asset)

    # 去重并排序，避免双语 README 共用图片造成收据漂移。
    list_assets = sorted(set(list_assets))  # 稳定资产路径

    # 返回插图错误、通过路径和尺寸事实。
    return list_errors, list_assets, dict_images

# 扫描包内所有 PNG，拒绝未被 README 引用的坏图像资产。
def _unreferenced_png_report(root: Path) -> list[str]:
    """检查技能根目录中的 PNG 签名。

    参数:
        root: 技能源码或 dist 根目录。

    返回:
        坏 PNG 资产的稳定错误列表。

    异常:
        无；遍历或读取失败按坏资产报告。
    """

    # 收集所有 PNG，避免坏资产通过“不被 README 引用”绕过审计。
    list_errors: list[str] = []  # PNG 签名错误列表

    # 文件名排序保证双语包和不同文件系统产生相同报告。
    for path_image in sorted(root.rglob("*.png")):

        # 符号链接不应被跟随或作为图像证据。
        if path_image.is_symlink() or not path_image.is_file():

            # 跳过非普通文件，公开入口门禁负责报告链接。
            continue

        # 头部无法解析时明确标注 PNG 签名问题。
        if _png_dimensions(path_image) is None:

            # 使用相对路径避免把宿主绝对路径写入机器合同。
            str_relative = path_image.relative_to(root).as_posix()  # PNG 相对路径

            # 记录无效 PNG 签名错误。
            list_errors.append(f"PNG asset has invalid PNG signature: {str_relative}")

    # 返回所有坏 PNG 资产诊断。
    return list_errors

# 对外公开的技能包文件合同入口。
def validate_public_skill_files(
    root: Path,
    *,
    expected_version: str | None = None,
    strict_metadata: bool = True,
) -> dict[str, Any]:
    """校验公开技能文件、版本一致性和 PNG 插图合同。

    参数:
        root: 技能源码或版本化 dist 根目录。
        expected_version: 可选的外部版本期望，用于复核 dist 命名。
        strict_metadata: 是否执行版本、许可证和占位文本强校验。

    返回:
        包含 ok、errors、checked、required_files、assets 和 versions 的报告。

    异常:
        无；所有文件系统问题都转换为结构化错误。
    """

    # 首先收集公开入口、缺失文件和符号链接问题。
    tuple_required_report = _required_file_report(root)  # 公开入口报告

    # 拆出缺失文件集合供结果和版本检查复用。
    tuple_list_missing = tuple_required_report[0]  # 缺失公开文件

    # 拆出已经存在的合同文件集合。
    tuple_list_checked = tuple_required_report[1]  # 已检查公开文件

    # 拆出必需文件相关错误并继续聚合其他门禁。
    tuple_list_errors = tuple_required_report[2]  # 公开入口错误

    # 使用语义明确的局部副本承接后续错误扩展。
    list_missing = tuple_list_missing  # 缺失公开文件列表

    # 保存已存在并实际检查过的公开入口。
    list_checked = tuple_list_checked  # 已检查公开文件列表

    # 保存入口检查产生的错误，后续继续追加版本和图片诊断。
    list_errors = tuple_list_errors  # 当前公开合同错误列表

    # 正式发布门禁收集三处元数据；预检模式只保留 VERSION 事实。
    if strict_metadata:

        # 严格模式必须证明版本元数据完整且一致。
        tuple_version_report = _version_report(root)  # 版本元数据报告

        # 取出三处元数据的归一化版本。
        dict_versions = tuple_version_report[0]  # 三处元数据的版本事实

        # 取出版本元数据错误供总报告聚合。
        list_version_errors = tuple_version_report[1]  # 版本错误列表

        # 合并版本错误，保留先后顺序。
        list_errors.extend(list_version_errors)  # 合并版本错误

    # 轻量预检只保留 VERSION，不阻断结构化图像检查。
    else:

        # 轻量预检仍读取 VERSION，保证发布目录命名可被复用。
        path_version = root / "VERSION"  # 预检版本文件路径

        # 只有普通 VERSION 文件才能形成可记录的版本事实。
        str_version = _normalized_version(_read_text(path_version)) if path_version.is_file() else ""  # 预检版本文本

        # 缺失 VERSION 已由公开文件存在性门禁报告。
        dict_versions = {"VERSION": str_version} if str_version else {}  # 预检版本事实

    # 外部期望存在时必须与 VERSION 事实一致。
    str_version = dict_versions.get("VERSION", "")  # 当前技能版本

    # 仅在两个版本值都存在时比较期望。
    if expected_version and str_version and _normalized_version(expected_version) != str_version:

        # 版本命名漂移会让 dist 与源码不可追溯。
        list_errors.append("public skill version does not match expected release version")

    # 正式发布模式检查许可证、安全、贡献和引用文件文本。
    if strict_metadata:

        # 轻量预检不把占位元数据误判为图像合同失败。
        list_errors.extend(_text_contract_report(root))  # 合并公开文本错误

    # 检查双语 README 的本地 PNG 资产；严格模式再执行清晰度门禁。
    tuple_readme_report = _readme_contract_report(root, enforce_resolution=strict_metadata)  # README 图片报告

    # 取出双语 README 的错误列表。
    list_readme_errors = tuple_readme_report[0]  # 双语 README 的阻断诊断

    # 取出通过分辨率和路径检查的资产。
    list_asset_paths = tuple_readme_report[1]  # 已通过清晰度门禁的 PNG 资产路径

    # 取出 README 逐引用的宽高事实。
    dict_readme_images = tuple_readme_report[2]  # 双语 README 图像尺寸

    # 合并 README 错误，避免隐藏双语入口问题。
    list_errors.extend(list_readme_errors)  # 合并 README 错误

    # 合并未被 README 引用的坏 PNG，防止二进制垃圾进入发布包。
    list_errors.extend(_unreferenced_png_report(root))  # 合并 PNG 签名错误

    # 返回稳定字段，供 CLI、审计和发布收据共享。
    return {
        "ok": not list_errors,  # 没有错误才允许继续发布
        "errors": list_errors,  # 全部阻断原因
        "checked": sorted(set(list_checked)),  # 已检查的公开文件
        "required_files": list(REQUIRED_PUBLIC_FILES),  # 当前合同文件清单
        "missing_required_files": sorted(list_missing),  # 报告缺失的公开入口文件
        "asset_paths": list_asset_paths,  # 通过的本地 PNG 路径
        "readme_images": dict_readme_images,  # README 图像尺寸事实
        "versions": dict_versions,  # 版本元数据事实
    }
