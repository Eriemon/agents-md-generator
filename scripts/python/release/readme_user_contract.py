"""校验双语 README 是否能让普通使用者完成安装和调用。"""

# 延迟解析注解，保持发布脚本在旧环境中的直接导入能力。
from __future__ import annotations

# 正则表达式负责识别章节标题、GitHub 地址和公开禁用词。
import re

# URL 解析器负责归一化网页地址和 clone 地址。
from urllib.parse import urlsplit

# 双语章节词表是公开 README 合同的唯一标题事实源。
README_MARKERS = {  # 双语用户流程章节标题
    "README.md": {  # 英文页面章节映射
        "purpose": ("What it does", "Why use it"),  # 用途章节标题
        "install": ("Install", "Get started"),  # 安装章节标题
        "prepare": ("Before you start", "What you need"),  # 准备章节标题
        "invoke": ("How to use", "How to call"),  # 调用章节标题
        "preview": ("Preview", "Review and confirm"),  # 预览章节标题
        "result": ("What you get", "Result", "Output"),  # 交付章节标题
    },
    "README-CN.md": {  # 中文页面章节映射
        "purpose": ("有什么用", "它能做什么"),  # 中文用途标题供章节扫描
        "install": ("安装", "开始使用"),  # 中文安装标题供入口扫描
        "prepare": ("需要准备什么", "准备事项"),  # 中文准备标题供合同扫描
        "invoke": ("如何调用", "如何使用"),  # 中文调用标题供流程扫描
        "preview": ("预览", "确认"),  # 中文预览标题供确认扫描
        "result": ("最终得到什么", "结果", "交付物"),  # 中文交付标题供结果扫描
    },
}

# 公开页面禁止泄露维护者专用流程和本地安装路线。
PUBLIC_FORBIDDEN_PATTERN = re.compile(  # 普通用户页面禁用词
    r"dist/|registry|mirror checkout|source skill directory|"
    r"versioned package directory|本地开发|版本化 dist|github 镜像|"
    r"发布回执|源技能目录|维护者流程|维护者工作流",
    re.IGNORECASE,  # 禁用词大小写不敏感选项
)

# 安装章节只接受 GitHub 仓库网页地址，不接受文件或分支链接。
GITHUB_URL_PATTERN = re.compile(  # GitHub 仓库地址格式
    r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
    r"(?:\.git)?(?:[^\s)>`]*)?",
    re.IGNORECASE,  # 地址匹配大小写不敏感选项
)

# 返回指定语言章节的标题同义词。
def _markers(str_file_name: str, str_section: str) -> tuple[str, ...]:
    """读取页面语言对应的章节标题。

    参数：str_file_name 为 README 文件名，str_section 为章节字段。
    返回：当前语言对应的标题同义词元组。
    异常：未知文件名或字段时抛出 ValueError 或 KeyError。
    """

    # 文件名查表能避免中英文合同发生隐式回退。
    dict_file_markers = README_MARKERS.get(str_file_name)  # 当前页面语言词表

    # 未知页面必须显式失败，不能套用另一语言的合同。
    if dict_file_markers is None:

        # 错误文本保留 Python 过程性错误前缀。
        raise ValueError(f"> ERR: [Python] unsupported README file name: {str_file_name}")

    # 返回当前字段的标题同义词。
    return dict_file_markers[str_section]

# 归一化 GitHub 地址，供 README 和发布映射共同比较。
def normalize_repository_url(str_value: str) -> str:
    """把 GitHub 地址归一化成仓库网页地址。

    参数：str_value 为 HTTPS、HTTPS clone 或 SSH clone 地址。
    返回：不含 `.git`、查询参数和片段的 HTTPS 仓库地址；无效值为空。
    异常：无。
    """

    # 清除 Markdown 包裹符和句末标点，避免比较受到排版影响。
    str_text = str_value.strip().strip("<>[](){}.,;:，。；：")  # 去除地址外层噪声

    # SSH clone 形态先转换为标准 HTTPS 形态。
    if str_text.startswith("<REDACTED_EMAIL>:"):

        # 转换后继续复用统一 URL 解析逻辑。
        str_text = "https://github.com/" + str_text.removeprefix("<REDACTED_EMAIL>:")  # 统一地址协议

    # 分离协议、主机和路径并忽略查询与片段。
    obj_parts = urlsplit(str_text)  # 已拆分协议主机与路径的地址对象

    # 仓库路径必须恰好包含 owner 与 repository 两段。
    tuple_path_parts = tuple(  # 仓库路径分量
        filter(None, obj_parts.path.strip("/").split("/"))  # 去除空路径段
    )

    # 只允许官方主机和 HTTP(S) 网页协议。
    bool_valid_url = (  # 地址基础结构状态
        obj_parts.scheme.lower() in {"http", "https"}  # 网页协议检查
        # 以下两项保持在同一布尔表达式中，确保仓库形态完整。
        and obj_parts.netloc.lower() == "github.com"  # 官方主机检查
        and len(tuple_path_parts) == 2  # owner 与仓库段数量检查
    )

    # 有效路径才能读取 owner 名称。
    str_owner = tuple_path_parts[0] if len(tuple_path_parts) == 2 else ""  # 公开仓库 owner 段

    # 有效路径才能读取仓库名称并去掉 clone 后缀。
    str_repository = (  # 去除 clone 后缀后的仓库段
        tuple_path_parts[1].removesuffix(".git")  # 合法路径的仓库名称
        # 路径不足两段时不产生可比较的仓库名。
        if len(tuple_path_parts) == 2  # owner 与仓库段存在
        else ""  # 缺少路径段时返回空值
    )

    # owner 字符集校验阻止路径注入与空名称。
    bool_valid_url = bool_valid_url and bool(  # owner 合法状态
        re.fullmatch(r"[A-Za-z0-9_.-]+", str_owner),  # owner 字符集检查
    )

    # repository 字符集校验保证链接可以直接复制。
    bool_valid_url = bool_valid_url and bool(  # 仓库字符集通过后的整体状态
        re.fullmatch(r"[A-Za-z0-9_.-]+", str_repository),  # 仓库字符集检查
    )

    # 只有完整合法地址才形成公开仓库 URL。
    str_normalized_url = (  # 规范化仓库网页地址
        f"https://github.com/{str_owner}/{str_repository}" if bool_valid_url else ""  # 规范化地址只在结构校验通过时暴露
    )

    # 失败时返回空值，避免调用方误用原始输入。
    return str_normalized_url

# 截取指定标题下的 Markdown 正文。
def _section_text(str_text: str, tuple_markers: tuple[str, ...]) -> str:
    """提取标题对应的章节正文。

    参数：str_text 为 README 文本，tuple_markers 为标题同义词。
    返回：标题正文；找不到时为空字符串。
    异常：无。
    """

    # 标题列表同时提供章节起点和终止边界。
    list_headings = list(  # 页面标题匹配结果
        re.finditer(r"(?im)^#{2,4}\s+([^\r\n]+)", str_text),  # 识别 Markdown 章节标题
    )

    # 按原文顺序寻找首个语义匹配标题。
    for int_index, obj_heading in enumerate(list_headings):

        # 小写化标题后比较同义词。
        str_heading = obj_heading.group(1).strip().lower()  # 当前标题文本

        # 不匹配的标题继续交给下一轮搜索。
        if not any(  # 当前标题是否命中目标章节
            str_marker.lower() in str_heading for str_marker in tuple_markers
        ):

            # 当前标题没有命中目标章节。
            continue

        # 下一个标题起点决定当前正文终点。
        int_end = (  # 当前章节结束偏移
            list_headings[int_index + 1].start()  # 下一个标题确定正文结束位置
            if int_index + 1 < len(list_headings)  # 存在下一个标题时截断正文
            else len(str_text)  # 最后一个标题延伸到文本末尾
        )

        # 返回命中标题之后的正文。
        return str_text[obj_heading.end() : int_end]

    # 没有命中标题时返回空正文供调用方报告缺口。
    return ""

# 提取安装章节中的 GitHub 地址并按出现顺序去重。
def _repository_urls(str_text: str) -> list[str]:
    """提取安装章节中的归一化 GitHub 仓库地址。

    参数：str_text 为安装章节 Markdown 正文。
    返回：按首次出现顺序排列的有效仓库 URL。
    异常：无。
    """

    # 将每个匹配地址转换成统一仓库网页 URL。
    list_urls = [  # 安装章节地址
        normalize_repository_url(obj_match.group(0))  # 当前匹配转换为归一化地址
        for obj_match in GITHUB_URL_PATTERN.finditer(str_text)  # 按原文顺序遍历地址
    ]

    # 字典键顺序保留首次出现顺序，同时过滤无效值。
    dict_unique = dict.fromkeys(  # 稳定去重地址
        str_url for str_url in list_urls if str_url  # 过滤空地址
    )

    # 返回供安装合同使用的 URL 列表。
    return list(dict_unique)

# 去掉图片和链接目标，只保留普通用户可见正文。
def _plain_text(str_text: str) -> str:
    """移除 Markdown 图片和链接目标。

    参数：str_text 为 README 完整 Markdown 文本。
    返回：用于内部术语扫描的用户可见正文。
    异常：无。
    """

    # Markdown 与 HTML 图片文件名都不属于用户流程正文。
    str_without_images = re.sub(  # 删除两种图片块
        r"!\[[^\]]*\]\([^)]*\)|<img\b[^>]*>", "", str_text, flags=re.IGNORECASE  # 删除图片语法
    )

    # 链接保留可见文字，避免目标路径触发误报。
    str_without_links = re.sub(  # 移除链接目标而保留页面标签
        r"\[([^\]]+)\]\([^)]*\)", r"\1", str_without_images  # Markdown 链接仅保留用户可见标签
    )

    # 返回用户可见的纯正文。
    return str_without_links

# 生成单页普通用户 README 合同报告。
def validate_user_readme_page(
    str_file_name: str,
    str_text: str,
    *,
    expected_repository_url: str | None = None,
    strict_metadata: bool = True,
) -> dict[str, object]:
    """生成单页普通用户 README 合同报告。

    参数：str_file_name 为 README 文件名，str_text 为完整文本。
    参数：expected_repository_url 为项目 GitHub 映射，strict_metadata 为发布严格度。
    返回：预览状态、发布状态、错误、警告和仓库 URL 事实。
    异常：未知 README 文件名时抛出 ValueError。
    """

    # 普通用户页面固定回答六个问题。
    list_errors: list[str] = []  # 页面章节错误

    # 检查六类章节标题及其正文。
    for str_section in ("purpose", "install", "prepare", "invoke", "preview", "result"):

        # 当前字段的标题同义词由页面语言决定。
        tuple_markers = _markers(str_file_name, str_section)  # 当前章节词表

        # 空正文表示标题缺失或没有用户说明。
        str_body = _section_text(str_text, tuple_markers)  # 当前章节正文

        # 记录可直接修正的章节缺口。
        if not str_body.strip():

            # 页面不能遗漏普通使用者所需的任何一步。
            list_errors.append(  # 章节缺口诊断
                f"README user page is missing section `{str_section}`: {str_file_name}"
            )

    # 维护者术语扫描只针对可见正文。
    str_visible = _plain_text(str_text).lower()  # 页面可见正文

    # 公开页面不得出现内部开发、打包或镜像词汇。
    if PUBLIC_FORBIDDEN_PATTERN.search(str_visible):

        # 命中维护者词时阻止页面回到内部说明。
        list_errors.append(  # 维护者术语诊断
            f"README user page contains maintainer-only term: {str_file_name}"
        )

    # 安装章节提供 URL、AI 句式和本地命令检查范围。
    str_install = _section_text(  # 安装章节正文
        str_text, _markers(str_file_name, "install")  # 读取安装章节
    )

    # 收集并去重用户需要复制的 GitHub 地址。
    list_urls = _repository_urls(str_install)  # 安装章节仓库地址

    # 页面 URL 缺失时保持空字符串。
    str_repository_url = list_urls[0] if list_urls else ""  # 页面安装地址

    # 预览阶段可把缺 URL 提示放入警告列表。
    list_warnings: list[str] = []  # 页面预览警告

    # 严格发布错误和预览错误共享安装诊断。
    list_install_errors: list[str] = []  # 安装合同错误

    # URL 数量歧义必须被用户看到。
    if len(list_urls) != 1:

        # 生成明确的单 URL 诊断。
        str_url_issue = (  # URL 数量诊断
            "README install section must contain exactly one GitHub repository URL: "
            f"{str_file_name}"
        )

        # 严格模式阻断，预览模式保留警告。
        if strict_metadata:

            # 正式发布不能容忍安装入口歧义。
            list_install_errors.append(str_url_issue)

        # 预览模式把入口问题保留为可修复提示。
        else:

            # 预览诊断写入警告集合，不阻断当前预览。
            list_warnings.append(str_url_issue)

    # 配置映射归一化后再与页面地址比较。
    str_expected_url = normalize_repository_url(  # 项目 GitHub 映射
        expected_repository_url or ""  # 映射缺失时使用空字符串
    )

    # 不一致会把用户带到错误技能，任何模式都阻断。
    if str_expected_url and str_repository_url and str_expected_url != str_repository_url:

        # 映射不一致是不可降级的安全问题。
        list_install_errors.append(  # 映射冲突诊断
            f"README install URL does not match repository mapping: {str_file_name}"
        )

    # 映射存在但页面缺失时按严格度分类。
    if str_expected_url and not str_repository_url:

        # 生成可执行的缺 URL 修复提示。
        str_missing_issue = (  # URL 缺失诊断
            "README install section is missing the mapped GitHub URL: "
            f"{str_file_name}"
        )

        # 正式发布阻断，预览阶段显式警告。
        if strict_metadata:

            # 发布前必须补齐项目映射地址。
            list_install_errors.append(str_missing_issue)

        # 预览允许先看内容，同时提示最终修复地址。
        else:

            # 缺失地址只在预览阶段作为可修复警告保留。
            list_warnings.append(str_missing_issue)

    # 当前语言的 AI 安装句必须出现在安装章节。
    pattern_install: re.Pattern[str]  # 安装句式正则

    # 根据页面文件名选择对应语言的安装句式。
    if str_file_name == "README.md":

        # 英文句式要求 AI 助手从 GitHub 仓库安装技能。
        pattern_install = re.compile(  # 英文 AI 安装句式
            r"Ask your AI(?: assistant)? to install (?:the )?skill from "
            r"https://github\.com/",
            re.IGNORECASE,  # 英文句式忽略大小写
        )

    # 中文页面使用对应语言的 AI 安装句式。
    else:

        # 中文句式要求 AI 从 GitHub URL 安装技能。
        pattern_install = re.compile(  # 中文 AI 安装句式
            r"让\s*AI\s*安装\s*https://github\.com/[^\s，。]+\s*中(?:的)?技能",  # 中文安装句正文
            re.IGNORECASE,  # 中文句式忽略大小写
        )

    # 检查用户是否得到可复制的 AI 安装表达。
    bool_has_sentence = bool(pattern_install.search(str_install))  # AI 安装句状态

    # 有 URL 或严格模式下不能缺少 AI 安装句。
    if not bool_has_sentence and (str_repository_url or strict_metadata):

        # 公开安装说明必须指向 AI-from-GitHub 调用方式。
        list_install_errors.append(  # AI 安装句诊断
            "README install section must use the AI-from-GitHub sentence: "
            f"{str_file_name}"
        )

    # 安装章节不允许出现本地命令或内部包目录。
    str_lower_install = str_install.lower()  # 小写安装正文

    # 每个命令标记独立报告，帮助作者修正文案。
    for str_marker in (
        "powershell",
        "python ",
        "bash ",
        "pip install",
        "git clone",
        "dist/",
        "install_skill.py",
    ):

        # 命中内部命令即使在代码块中也不能公开。
        if str_marker.lower() in str_lower_install:

            # 说明应删除的本地安装方式。
            list_install_errors.append(  # 本地安装诊断
                f"README install section contains a local installation command "
                f"`{str_marker}`: {str_file_name}"
            )

    # 页面可预览条件是章节完整且没有安装阻断错误。
    bool_preview_ready = not list_errors and not list_install_errors  # 页面预览状态

    # 正式发布还要求预览没有 URL 警告。
    bool_publish_ready = bool_preview_ready and not list_warnings  # 页面发布状态

    # 严格模式使用发布状态，预览模式使用预览状态。
    bool_ok = bool_preview_ready if not strict_metadata else bool_publish_ready  # 当前模式结果

    # 返回公开报告需要的稳定字段。
    return {  # 页面合同报告
        "ok": bool_ok,
        "preview_ready": bool_preview_ready,
        "publish_ready": bool_publish_ready,
        "errors": list_errors + list_install_errors,
        "warnings": list_warnings,
        "preview_errors": list_errors,
        "publish_errors": list_install_errors,
        "repository_url": str_repository_url,
        "repository_url_source": "readme" if str_repository_url else "missing",
    }
