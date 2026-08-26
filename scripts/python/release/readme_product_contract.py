"""校验双语 README 的产品页结构、作者引用和原有视觉分组。"""

# 延迟类型标注求值，保持发布工具兼容 Python 3.10。
from __future__ import annotations

# 标准库足以完成文本、路径和 Markdown/HTML 资源解析。
import re
from pathlib import Path
from typing import Any

# 普通用户合同由独立模块负责，视觉合同继续留在本模块。
import readme_user_contract

# 双语产品页是受管理技能公开合同的一部分。
README_PRODUCT_FILES = ("README.md", "README-CN.md")  # 双语产品页入口

# Markdown 图片目标需要保留，供产品页按原文顺序解析。
MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")  # Markdown 图片模式

# 该正则在产品页中提取 HTML 图片 src，并保留头部徽章的原文顺序。
HTML_IMAGE_PATTERN = re.compile(  # 用于区分本地插图和远程徽章的 HTML src 规则
    r"<img\b[^>]*?\bsrc=[\"']([^\"']+)[\"']",  # 捕获 img 标签中的 src 地址
    re.IGNORECASE,  # 允许 README HTML 属性大小写混用
)

# 该正则从图片前文本提取章节标题，供三章功能图归属使用。
HEADING_PATTERN = re.compile(  # 用于把功能图绑定到最近章节的标题规则
    r"(?im)^(?:#{2,4}\s+|<h[2-4][^>]*>)([^<\r\n]+)",  # 同时识别 Markdown 和 HTML 标题文本
)

# 产品页日期使用 ISO 格式，避免只写模糊的“最新版本”。
RELEASE_DATE_PATTERN = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")  # 发布日期模式

# 这些词会把落地页重新拉回内部报告语气。
FORBIDDEN_MARKETING_TERMS = ("evidence", "checklist", "证据", "清单")  # 报告化词语

# 作者姓名是产品归属信息的固定标记。
AUTHOR_MARKERS = ("Jiyuan Liu", "He Li")  # 作者姓名

# 双语页面统一保留英文学校归属，中文页面可追加本地化文本。
AFFILIATION_MARKERS = ("Southeast University",)  # 英文机构标记

# 引用和许可链接共同构成产品页的公共归属入口。
FOOTER_MARKERS = ("CITATION.cff", "LICENSE", "Apache License 2.0")  # 页脚标记

# 现有仓库图像已经覆盖产品三章，不要求重新绘制新文件。
FEATURE_STEMS = (  # 普通用户旅程页面引用的功能图文件名
    "project-facts",  # 项目事实图
    "project-facts-cn",  # 中文项目事实图
    "design-profile",  # 设计画像图
    "design-profile-cn",  # 中文设计画像图
    "rule-rendering",  # 规则生成图
    "rule-rendering-cn",  # 中文规则生成图
    "evidence-guard",  # 英文交付确认图
    "evidence-guard-cn",  # 中文交付确认图
)

# 产品叙事需要多个标题来承载痛点、能力、上手和归属。
MIN_PRODUCT_HEADINGS = 5  # 产品标题最低数量

# 头部至少保留许可、版本和目标三类徽章语义。
MIN_BADGE_REFERENCES = 3  # 徽章语义最低数量

# 读取公开文案，保持文件系统异常可诊断。
def _read_text(path_file: Path) -> str:
    """读取 UTF-8 文本。

    参数:
        path_file: 待读取的公开文档路径。

    返回:
        UTF-8 文本；文件不可读时返回空字符串。

    异常:
        无；文件系统异常转换为空文本。
    """

    # 读取失败不应掩盖另一语言页面的独立诊断。
    try:

        # 公开文案统一替换坏字节，保证报告可序列化。
        str_content = path_file.read_text(encoding="utf-8", errors="replace")  # 文件文本

        # 返回已经规范化的页面文本。
        return str_content

    # 文件缺失或不可读时交由上层报告入口问题。
    except OSError:

        # 空文本让调用方继续检查另一种语言。
        return ""

# 收集 Markdown 和 HTML 图片目标，保持页面出现顺序。
def _sorted_image_matches(str_readme: str) -> list[tuple[int, str]]:
    """按文档位置收集图片目标。

    参数:
        str_readme: 当前语言 README 的完整文本。

    返回:
        按出现位置排序的 `(位置, 目标)` 列表。

    异常:
        无；正则只访问传入文本。
    """

    # Markdown 目标记录其起始位置，供最终稳定排序。
    list_markdown = [  # Markdown 图片位置和目标
        (match_image.start(), match_image.group(1).strip().split()[0])  # Markdown 图片的起始坐标和目标
        for match_image in MARKDOWN_IMAGE_PATTERN.finditer(str_readme)  # 遍历 Markdown 图片语法
        if match_image.group(1).strip()  # 过滤空 Markdown 目标
    ]

    # HTML src 目标同样保留原文位置。
    list_html = [  # 收集头部徽章的 HTML src
        (match_image.start(), match_image.group(1).strip())  # HTML 徽章的起始坐标和目标
        for match_image in HTML_IMAGE_PATTERN.finditer(str_readme)  # 收集徽章和正文的 HTML src
        if match_image.group(1).strip()  # 跳过未填写 src 的 HTML 标签
    ]

    # 合并两种语法后按文档位置排序。
    list_matches = sorted(list_markdown + list_html, key=lambda tuple_match: tuple_match[0])  # 排序后的图片目标

    # 返回包含位置的稳定匹配列表。
    return list_matches

# 提供公开入口使用的图片目标列表。
def extract_image_references(str_readme: str) -> list[str]:
    """提取 README 中按原文顺序去重的图片路径。

    参数:
        str_readme: 当前语言 README 的完整文本。

    返回:
        Markdown/HTML 图片目标的稳定列表。

    异常:
        无；正则匹配只处理文本，不访问文件系统。
    """

    # 先保留出现顺序，再使用字典键完成稳定去重。
    list_targets = [str_target for _, str_target in _sorted_image_matches(str_readme)]  # 图片目标顺序

    # 字典键天然保持第一次出现的顺序。
    dict_unique_targets = dict.fromkeys(list_targets)  # 唯一图片目标

    # 转回列表供现有公开合同复用。
    list_references = list(dict_unique_targets)  # 去重后的图片引用

    # 返回稳定顺序的唯一目标集合。
    return list_references

# 识别原始头部保留的 shields 徽章。
def is_remote_badge_reference(str_readme: str, str_reference: str) -> bool:
    """判断目标是否为原始 shields 徽章。

    参数:
        str_readme: 当前 README 文本，用于确认目标处在徽章链接中。
        str_reference: 提取出的图片目标。

    返回:
        目标是 shields 徽章时返回 True，否则返回 False。

    异常:
        无；仅执行字符串和正则判断。
    """

    # 远程徽章只允许原始 shields.io URL。
    str_lowered = str_reference.strip().lower()  # 规范化图片目标

    # 非远程目标不属于徽章例外。
    if not str_lowered.startswith(("http://", "https://", "//")):

        # 本地 PNG 由普通资产合同继续检查。
        return False

    # URL 本身必须包含 shields.io 域名。
    bool_shields_url = "shields.io/" in str_lowered  # 远程地址是否来自徽章服务

    # 读取目标附近文本，确认它确实在头部链接上下文中。
    int_reference_position = str_readme.find(str_reference)  # 图片目标位置

    # 上下文窗口用于确认远程目标确实位于头部徽章链接。
    str_context = str_readme[max(0, int_reference_position - 160) : int_reference_position + 40]  # 徽章链接上下文窗口

    # 链接上下文或 URL badge 语义共同构成放行条件。
    bool_link_context = "<a" in str_context.lower() or "badge" in str_lowered  # 目标是否带有徽章链接语义

    # 仅放行原始 shields 徽章，其余远程图片仍然失败。
    return bool_shields_url and bool_link_context

# 判断本地图片目标是否违反 PNG 合同。
def _is_forbidden_reference(str_reference: str) -> bool:
    """判断目标是否为远程、绝对路径或非 PNG。

    参数:
        str_reference: README 中提取出的图片目标。

    返回:
        目标违反本地 PNG 合同时返回 True。

    异常:
        无；仅执行字符串判断。
    """

    # 统一大小写后识别远程协议和绝对路径。
    str_lowered = str_reference.strip().lower()  # 让协议、盘符和后缀判断统一使用小写

    # Windows 与 POSIX 绝对路径都不能随技能包交付。
    bool_absolute = str_lowered.startswith(("http://", "https://", "//", "/"))  # 远程或 POSIX 路径

    # Windows 盘符路径也必须在包边界内解析。
    bool_windows_absolute = re.match(r"^[a-z]:[\\/]", str_lowered) is not None  # Windows 绝对路径

    # 本地图只接受 PNG，远程 shields 由上下文函数单独放行。
    return bool_absolute or bool_windows_absolute or not str_lowered.endswith(".png")

# 解析图片路径并拒绝技能根目录之外的目标。
def _resolve_asset(root: Path, path_readme: Path, str_reference: str) -> Path | None:
    """解析 README 图片并拒绝越界路径。

    参数:
        root: 技能源码或 dist 根目录。
        path_readme: 当前 README 文件路径。
        str_reference: 本地图片目标。

    返回:
        根目录内的普通 PNG 路径；非法目标返回 None。

    异常:
        无；路径解析异常按非法目标处理。
    """

    # 远程、矢量和绝对路径在文件系统访问前直接拒绝。
    if _is_forbidden_reference(str_reference):

        # None 让页面报告保留原始引用。
        return None

    # 规范化资产和根路径，用于安全边界比较。
    path_asset = (path_readme.parent / str_reference).resolve()  # 图片绝对路径

    # 根目录是所有相对路径安全比较的固定边界。
    path_root = root.resolve()  # 技能根绝对路径

    # relative_to 失败表示 README 试图跳出技能包。
    try:

        # 保存相对结果，同时完成越界检查。
        path_relative = path_asset.relative_to(path_root)  # 技能根内相对路径

    # 越界路径不能成为公开资产。
    except ValueError:

        # 返回 None 让调用方生成稳定诊断。
        return None

    # 符号链接不能把公开入口重定向到技能根之外。
    if path_asset.is_symlink() or not path_asset.is_file():

        # 缺失或链接目标不具备安装资产语义。
        return None

    # 相对路径变量用于保留边界检查语义，结果本身返回绝对路径。
    _ = path_relative  # 保留路径边界检查结果

    # 返回通过边界和普通文件检查的本地 PNG。
    return path_asset

# 查找图片前最近的产品章节标题。
def _heading_before(str_readme: str, int_position: int) -> str:
    """提取图片前最近的章节标题。

    参数:
        str_readme: 当前语言 README 文本。
        int_position: 图片目标在 README 中的位置。

    返回:
        最近标题文本；无标题时返回空字符串。

    异常:
        无；标题匹配只访问字符串。
    """

    # 图片必须归属于此前最近的章节。
    list_headings = list(HEADING_PATTERN.finditer(str_readme, 0, int_position))  # 图片前标题

    # 没有标题表示图片未被产品章节承载。
    if not list_headings:

        # 空标题由角色报告转换为分组错误，并返回空事实避免虚构图片归属。
        return ""

    # 最近标题负责归属当前功能图片。
    return list_headings[-1].group(1).strip()

# 生成缺失标记的稳定文本错误。
def _missing_marker_errors(
    str_name: str,
    str_readme: str,
    tuple_markers: tuple[str, ...],
    str_message: str,
) -> list[str]:
    """收集页面中缺失的固定标记。

    参数:
        str_name: README 文件名。
        str_readme: 页面完整文本。
        tuple_markers: 需要逐项检查的标记。
        str_message: 错误消息中的标记类别。

    返回:
        缺失标记对应的稳定错误列表。

    异常:
        无；仅执行内存字符串检查。
    """

    # 缺失列表保持合同顺序，便于双语诊断对比。
    list_missing = [str_marker for str_marker in tuple_markers if str_marker not in str_readme]  # 缺失标记

    # 每项保留页面名和标记类别，方便直接修复。
    list_errors = [  # 标记缺失错误
        f"README product page is missing {str_message} marker {str_marker}: {str_name}"  # 缺失标记错误文本
        for str_marker in list_missing  # 遍历当前类别的缺失项
    ]

    # 返回当前类别的独立错误列表。
    return list_errors

# 检查语言切换、产品叙事和作者引用文本。
def _page_text_errors(
    str_name: str,
    str_readme: str,
    expected_version: str | None,
) -> tuple[list[str], list[str]]:
    """检查单页语言、叙事、版本和归属文本。

    参数:
        str_name: README 文件名。
        str_readme: 页面完整文本。
        expected_version: 可选的期望版本文本。

    返回:
        `(errors, headings)` 文本错误和页面标题列表。

    异常:
        无；所有检查均为内存字符串操作。
    """

    # 标题列表承载产品章节和图片归属信息。
    list_headings = [  # 产品章节标题
        match_heading.group(1).strip()  # 当前标题文本
        for match_heading in HEADING_PATTERN.finditer(str_readme)  # 遍历页面章节标题
    ]

    # 文本错误按固定顺序输出，保证双语收据可比较。
    list_errors = _missing_marker_errors(  # 语言切换错误
        str_name,  # 当前 README 文件名
        str_readme,  # 当前页面文本
        ("README.md", "English", "README-CN.md", "中文"),  # 双语切换固定标记
        "language switch",  # 双语切换错误类别
    )

    # 语言切换错误需要区分两种入口，避免一个缺失掩盖另一个。
    if "README.md" in str_readme and "English" in str_readme:

        # 英文入口已经完整，不追加诊断。
        list_errors = [  # 保留现有错误并过滤英文入口错误
            str_error  # 需要保留的既有诊断
            for str_error in list_errors  # 遍历当前诊断集合
            if "README.md" not in str_error and "English" not in str_error  # 过滤英文入口诊断
        ]

    # 中文入口同样保留独立检查结果。
    if "README-CN.md" in str_readme and "中文" in str_readme:

        # 完整中文入口不需要继续报告。
        list_errors = [  # 去掉已经满足中文入口的诊断
            str_error  # 当前待保留的诊断文本
            for str_error in list_errors  # 遍历中文入口诊断集合
            if "README-CN.md" not in str_error and "中文" not in str_error  # 过滤中文入口诊断
        ]

    # 标题不足时要求重新组织产品叙事。
    if len(list_headings) < MIN_PRODUCT_HEADINGS:

        # 标题数量是落地页的最低结构约束。
        list_errors = list_errors + [  # 标题数量错误
            f"README product page needs at least {MIN_PRODUCT_HEADINGS} headings: {str_name}"  # 标题不足诊断
        ]

    # 页面应同时有开始使用或安装行动入口。
    bool_has_start_action = any(  # 行动入口状态
        str_marker in str_readme  # 行动入口匹配结果
        for str_marker in ("Get started", "Install", "开始使用", "安装")  # 遍历可接受行动词
    )

    # 没有行动入口的页面无法承担产品落地页职责。
    if not bool_has_start_action:

        # 行动入口错误保持稳定英文文本。
        list_errors = list_errors + [  # 行动入口错误
            f"README product page must include a start action: {str_name}"  # 行动入口诊断
        ]

    # 版本和发布日期必须能够被用户直接看到。
    bool_has_version = (  # 页面版本状态
        not expected_version  # 未传入外部版本时不比较
        or expected_version.lstrip("vV") in str_readme  # 页面含无前缀版本
        or expected_version in str_readme  # 页面含完整版本
    )

    # 版本缺失时阻断页面与发布目录的漂移。
    if not bool_has_version:

        # 页面版本漂移时阻断镜像。
        list_errors = list_errors + [  # 版本错误
            f"README product page must show release version {expected_version}: {str_name}"  # 版本诊断
        ]

    # ISO 日期让版本亮点具有明确时间语义。
    if not RELEASE_DATE_PATTERN.search(str_readme):

        # 模糊日期不满足公开发布页合同。
        list_errors = list_errors + [  # 日期错误
            f"README product page must show an ISO release date: {str_name}"  # 日期诊断
        ]

    # 作者和实验室归属必须完整保留。
    list_errors = list_errors + _missing_marker_errors(  # 作者归属错误
        str_name,  # 作者归属的页面名
        str_readme,  # 作者归属检查使用的页面正文
        AUTHOR_MARKERS + AFFILIATION_MARKERS + ("HIQC",),  # 作者学校和实验室标记
        "attribution",  # 作者学校实验室错误类别
    )

    # 引用和许可入口必须共同出现在页脚。
    list_errors = list_errors + _missing_marker_errors(  # 页脚入口错误
        str_name,  # 页脚入口的页面名
        str_readme,  # 页脚入口检查使用的页面正文
        FOOTER_MARKERS,  # 引用和许可固定标记
        "footer",  # 页脚引用许可错误类别
    )

    # 公开落地页可引用图片文件名，但用户可见正文不得出现内部报告式措辞。
    str_visible_readme = readme_user_contract._plain_text(str_readme)  # 去除图片与链接目标

    # 只扫描用户真正能读到的页面文字，避免资产路径触发误报。
    list_forbidden_terms = [  # 报告化词语命中
        str_marker  # 命中的报告化词语
        for str_marker in FORBIDDEN_MARKETING_TERMS  # 遍历报告化词语
        if str_marker.lower() in str_visible_readme.lower()  # 仅保留可见正文中的词语
    ]

    # 每个命中词单独报告，避免复制整段文案。
    list_errors = list_errors + [  # 报告化措辞错误
        f"README product page contains report-style term {str_marker}: {str_name}"  # 报告化词语诊断
        for str_marker in list_forbidden_terms  # 展开命中的报告化词语
    ]

    # 返回文本结构供图片和总合同阶段复用。
    return list_errors, list_headings

# 解析单个图片目标并生成语义事实。
def _single_image_fact(
    root: Path,
    path_readme: Path,
    str_readme: str,
    str_reference: str,
) -> tuple[str, dict[str, Any] | None]:
    """解析单个图片目标。

    参数:
        root: 技能源码或 dist 根目录。
        path_readme: 当前 README 路径。
        str_readme: 当前页面文本。
        str_reference: 当前图片目标。

    返回:
        `(error, fact)`；通过时错误为空，非法目标的事实为 None。

    异常:
        无；路径异常转换为错误文本。
    """

    # 原始 shields 徽章保留远程语义，不作为功能插图资产。
    if is_remote_badge_reference(str_readme, str_reference):

        # badge-remote 角色供头部徽章数量检查使用。
        dict_badge_fact = {  # 远程徽章事实
            "role": "badge-remote",  # 远程徽章角色
            "heading": "",  # 徽章不归属功能章节
            "remote": True,  # 标记为远程来源
        }

        # 远程徽章不产生图片错误。
        return "", dict_badge_fact

    # 其他远程、绝对或非 PNG 目标必须立即失败。
    if _is_forbidden_reference(str_reference):

        # 保留原始目标，便于维护者定位文档行。
        return f"README product image must be local PNG: {str_reference}", None

    # 本地图片必须留在技能根目录内并且是普通文件。
    path_asset = _resolve_asset(root, path_readme, str_reference)  # 本地图片路径

    # 缺失或越界目标不能继续生成图片事实。
    if path_asset is None:

        # 越界或缺失目标不创建虚假图片事实。
        return f"README product image is missing or escapes skill root: {str_reference}", None

    # 记录文件名角色，识别仓库原有功能图。
    str_role = path_asset.stem.lower()  # 图片文件名角色

    # 用首个引用位置归属最近的产品章节。
    int_position = str_readme.find(str_reference)  # 用首次出现位置确定章节归属

    # 标题归属用于阻止三张图挤在同一段。
    str_heading = _heading_before(str_readme, int_position)  # 图片所属章节

    # 保存本地图的角色、章节和离线属性。
    dict_image_fact = {  # 本地图片事实
        "role": str_role,  # 文件名语义角色
        "heading": str_heading,  # 最近产品章节
        "remote": False,  # 本地资产标记
    }

    # 返回通过路径边界检查的本地图片事实。
    return "", dict_image_fact

# 收集单页全部图片目标和语义事实。
def _page_image_facts(
    root: Path,
    path_readme: Path,
    str_readme: str,
) -> tuple[list[str], list[str], dict[str, dict[str, Any]]]:
    """解析单页图片并区分原有本地图和 shields 徽章。

    参数:
        root: 技能源码或 dist 根目录。
        path_readme: 当前 README 路径。
        str_readme: 当前页面文本。

    返回:
        `(errors, references, images)` 图片错误、目标列表和语义事实。

    异常:
        无；路径和文件异常转成稳定错误。
    """

    # 图片引用顺序必须与页面顺序一致，便于定位视觉布局。
    list_references = extract_image_references(str_readme)  # 当前页面图片引用

    # 每个目标交给单图解析器，避免主流程堆叠路径分支。
    list_results = [  # 图片解析结果
        _single_image_fact(root, path_readme, str_readme, str_reference)  # 单图解析结果
        for str_reference in list_references  # 页面图片目标
    ]

    # 只输出非空错误，保持通过页面的诊断集合为空。
    list_errors = [  # 图片错误列表
        str_error  # 非空图片错误文本
        for str_error, _ in list_results  # 逐项读取单图结果
        if str_error  # 过滤通过项
    ]

    # 只保存解析成功的目标事实。
    dict_images = {  # 图片语义事实
        str_reference: dict_fact  # 图片目标到语义事实
        for str_reference, (_, dict_fact) in zip(list_references, list_results)  # 对齐解析结果
        if dict_fact is not None  # 过滤非法目标
    }

    # 返回本页完整图片事实。
    return list_errors, list_references, dict_images

# 检查 Hero、徽章和三章原有功能图的角色分组。
def _page_role_errors(
    str_name: str,
    dict_images: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str], list[str], list[str]]:
    """检查页面视觉角色。

    参数:
        str_name: README 文件名。
        dict_images: 图片目标到角色/章节事实的映射。

    返回:
        `(errors, hero, badges, features)` 角色错误及三类图片列表。

    异常:
        无；仅访问已解析的图片事实。
    """

    # Hero 角色使用现有 hero.png 或 hero-cn.png。
    list_hero_images = [  # Hero 图片列表
        str_reference  # 现有 Hero 引用
        for str_reference, dict_image in dict_images.items()  # 遍历首屏候选图片事实
        if dict_image["role"].startswith("hero")  # 识别 Hero 文件名
    ]

    # shields 和未来本地徽章均保留 badge 语义。
    list_badge_images = [  # 徽章图片列表
        str_reference  # 头部徽章引用
        for str_reference, dict_image in dict_images.items()  # 遍历头部徽章候选事实
        if "badge" in dict_image["role"]  # 识别徽章语义
    ]

    # 只把仓库已有功能图文件名作为三章候选。
    list_feature_images = [  # 原有功能图片列表
        str_reference  # 原有功能图引用
        for str_reference, dict_image in dict_images.items()  # 遍历页面图片事实
        if dict_image["role"] in FEATURE_STEMS  # 识别功能图文件名
    ]

    # 每张功能图都必须归属于独立标题。
    set_feature_headings = {  # 功能章节标题集合
        dict_images[str_reference]["heading"]  # 功能图所属标题
        for str_reference in list_feature_images  # 遍历功能图引用
        if dict_images[str_reference]["heading"]  # 过滤无标题目标
    }

    # 角色错误集中在这里，页面主流程只负责合并结果。
    list_errors: list[str] = []  # 角色错误列表

    # 缺少 Hero 时产品页无法建立第一屏视觉记忆。
    if not list_hero_images:

        # 只要求复用现有 Hero，不引入新绘图义务。
        list_errors = list_errors + [  # Hero 缺失错误
            f"README product page must include the existing hero PNG: {str_name}"  # Hero 缺失诊断
        ]

    # 头部徽章数量保证原始头部语义未被删掉。
    if len(list_badge_images) < MIN_BADGE_REFERENCES:

        # 徽章不足时提醒恢复许可、版本和目标入口。
        list_errors = list_errors + [  # 徽章数量错误
            f"README product page must preserve at least {MIN_BADGE_REFERENCES} badges: {str_name}"  # 徽章缺失诊断
        ]

    # 四类用户旅程图必须各自拥有产品章节标题。
    if len(list_feature_images) < 4 or len(set_feature_headings) < 4:

        # 该错误专门阻止图片再次连成一块。
        list_errors = list_errors + [  # 功能分组错误
            f"README product page must separate four user journey chapters: {str_name}"  # 功能分组诊断
        ]

    # 返回排序前的图片列表，收据由上层保持原文顺序。
    return list_errors, list_hero_images, list_badge_images, list_feature_images

# 生成单个 README 的产品页报告。
def _page_report(
    root: Path,
    str_name: str,
    expected_version: str | None,
    expected_repository_url: str | None,
    strict_metadata: bool,
) -> dict[str, Any]:
    """生成单个 README 的产品页报告。

    参数:
        root: 技能源码或版本化 dist 根目录。
        str_name: README 文件名。
        expected_version: 可选的公开版本文本。
        expected_repository_url: 可选的项目 GitHub 仓库 URL。
        strict_metadata: 是否把发布合同缺口作为阻断错误。

    返回:
        包含页面事实、图片分组和错误列表的字典。

    异常:
        无；所有检查失败均转换为结构化字段。
    """

    # 页面路径是所有检查的共同输入。
    path_readme = root / str_name  # 当前 README 路径

    # 缺失入口不能继续解析产品页结构。
    if not path_readme.is_file():

        # 保留相对文件名，避免报告泄露宿主路径。
        return {  # 缺失页面报告
            "ok": False,
            "errors": [f"README product page is missing: {str_name}"],
            "images": {},
            "headings": [],
            "user_contract": {"ok": False, "errors": [f"README user page is missing: {str_name}"]},
        }

    # 读取页面文本，作为语言和图片合同的共同输入。
    str_readme = _read_text(path_readme)  # 页面主流程需要的完整正文

    # 先取得标题、版本和作者归属诊断。
    tuple_text_report = _page_text_errors(str_name, str_readme, expected_version)  # 文本报告

    # 拆出文本错误，保持后续错误顺序稳定。
    list_errors = tuple_text_report[0]  # 文本错误列表

    # 普通用户合同与原有视觉合同共享同一份页面文本。
    dict_user_contract = readme_user_contract.validate_user_readme_page(  # 用户页面报告
        str_name,  # 当前双语页面名称
        str_readme,  # 当前页面完整正文
        expected_repository_url=expected_repository_url,  # 项目 GitHub 映射
        strict_metadata=strict_metadata,  # 预览或发布严格度
    )  # 用户页面合同结果

    # 预览模式只把真实用户内容缺口作为错误，URL 发布缺口保留为警告。
    list_errors = list_errors + list(dict_user_contract["errors"])  # 合并用户页面错误

    # 保存标题列表供图片章节归属和发布报告使用。
    list_headings = tuple_text_report[1]  # 页面标题列表

    # 再解析本地图片及原始徽章引用。
    tuple_image_report = _page_image_facts(root, path_readme, str_readme)  # 图片报告

    # 把图片路径错误追加到页面诊断中。
    list_errors = list_errors + tuple_image_report[0]  # 合并图片错误

    # 保存页面图片的原文顺序。
    list_references = tuple_image_report[1]  # 页面图片引用

    # 保存已经通过边界检查的图片事实。
    dict_images = tuple_image_report[2]  # 页面图片事实

    # 根据文件名角色检查 Hero、徽章和三章功能图。
    tuple_role_report = _page_role_errors(str_name, dict_images)  # 角色报告

    # 合并角色错误，阻止不完整页面继续发布。
    list_errors = list_errors + tuple_role_report[0]  # 合并角色错误

    # 保存首屏 Hero 引用供发布收据展示。
    list_hero_images = tuple_role_report[1]  # 首屏 Hero 引用

    # 保存头部徽章引用供语言页完整性检查。
    list_badge_images = tuple_role_report[2]  # 头部徽章引用集合

    # 保存原有三章功能图引用供布局检查。
    list_feature_images = tuple_role_report[3]  # 三章功能图引用

    # 重新汇总功能图所属的独立标题。
    set_feature_headings = {  # 三章标题集合
        dict_images[str_reference]["heading"]  # 当前功能图标题
        for str_reference in list_feature_images  # 遍历原有功能图
        if dict_images[str_reference]["heading"]  # 过滤没有标题的引用
    }

    # 返回双语总报告和发布收据复用的稳定字段。
    return {  # 单页产品报告
        "ok": not list_errors,
        "errors": list_errors,
        "images": dict_images,
        "headings": list_headings,
        "hero_images": list_hero_images,
        "badge_images": list_badge_images,
        "feature_images": list_feature_images,
        "feature_headings": sorted(set_feature_headings),
        "image_references": list_references,
        "user_contract": dict_user_contract,
    }

# 对外提供双语 README 产品页合同入口。
def validate_readme_product(
    root: Path,
    expected_version: str | None = None,
    *,
    expected_repository_url: str | None = None,
    strict_metadata: bool = True,
) -> dict[str, Any]:
    """校验双语 README 的产品页结构。

    参数:
        root: 技能源码或版本化 dist 根目录。
        expected_version: 可选的公开版本文本，例如 `v2.1.0`。
        expected_repository_url: 可选的项目 GitHub 仓库 URL。
        strict_metadata: 是否把发布合同缺口作为阻断错误。

    返回:
        包含 `ok`、错误列表和双语页面事实的产品合同报告。

    异常:
        无；文件系统问题均转换为结构化错误。
    """

    # 双语页面分别校验，避免一页通过掩盖另一页缺陷。
    dict_pages: dict[str, dict[str, Any]] = {}  # 双语页面报告

    # 固定语言顺序逐页生成报告，方便定位单页问题。
    for str_name in README_PRODUCT_FILES:

        # 将共享发布参数送入当前语言的结构化合同检查。
        dict_page_report = _page_report(  # 生成当前语言的产品页事实
            root,  # 技能根目录
            str_name,  # 需要解析的语言页面
            expected_version,  # 期望发布版本
            expected_repository_url,  # 期望 GitHub 仓库地址
            strict_metadata,  # 当前公开合同严格度
        )

        # 把单页结果写入固定语言键，保持后续汇总顺序。
        dict_pages[str_name] = dict_page_report  # 固定语言页面报告

    # 总错误列表按固定语言顺序聚合，保证发布报告稳定。
    list_errors = [  # 产品页错误
        str_error  # 当前错误文本
        for str_name in README_PRODUCT_FILES  # 按语言顺序遍历
        for str_error in dict_pages[str_name]["errors"]  # 展开页面错误
    ]

    # 汇总普通用户合同的预览、发布和警告状态。
    list_warnings: list[str] = []  # 用户合同警告

    # 固定语言顺序复制每页警告，保持报告可复现。
    for str_name in README_PRODUCT_FILES:

        # 当前页面警告独立追加到总警告集合。
        list_page_warnings = dict_pages[str_name]["user_contract"].get("warnings", [])  # 当前页面警告列表

        # 页面警告进入总报告，供预览调用方展示。
        list_warnings.extend(list_page_warnings)  # 汇总当前页面警告

    # 汇总两个页面的预览状态，避免单语通过掩盖另一页缺口。
    bool_preview_ready = all(  # 双语页面是否均可预览
        dict_pages[str_name]["user_contract"].get("preview_ready", False)  # 当前页面预览状态
        for str_name in README_PRODUCT_FILES  # 遍历双语页面
    )

    # 只有错误和警告都清空时才允许进入发布阶段。
    bool_publish_ready = not list_errors and not list_warnings  # 双语合同发布状态

    # 返回结构化产品合同，供公开校验、GitHub CLI 和发布工具复用。
    return {  # 双语产品合同报告
        "ok": bool_preview_ready if not strict_metadata else bool_publish_ready,
        "errors": list_errors,
        "warnings": list_warnings,
        "preview_ready": bool_preview_ready,
        "publish_ready": bool_publish_ready,
        "repository_url": next(
            (
                dict_pages[str_name]["user_contract"].get("repository_url", "")
                for str_name in README_PRODUCT_FILES
                if dict_pages[str_name]["user_contract"].get("repository_url")
            ),
            "",
        ),
        "files": dict_pages,
        "required_files": list(README_PRODUCT_FILES),
    }

