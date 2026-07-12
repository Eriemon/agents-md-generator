"""验证发布文本与二进制内容的脱敏证据。"""

# 标准库提供路径、正则表达式和结构化类型。
from pathlib import Path
import re
from typing import Any

# 发布清单模块提供安全路径解析和文件摘要。
from install_release_manifest import resolve_release_member_path, sha256_file

# 每类敏感信息使用稳定占位符，便于收据记录和内容复核。
SANITIZED_PLACEHOLDERS = {
    "api_key": "<REDACTED_API_KEY>",  # API 密钥和访问令牌占位符。
    "password": "<REDACTED_PASSWORD>",  # 密码赋值占位符。
    "email": "<REDACTED_EMAIL>",  # 电子邮件地址占位符。
    "local_path": "<REDACTED_LOCAL_PATH>",  # 用户私有绝对路径占位符。
}

# 赋值规则保留变量名前缀，只替换实际敏感值。
SANITIZED_ASSIGNMENT_RULES = [
    (
        "api_key",  # API 密钥规则名称。
        re.compile(  # 编译 API 密钥赋值检测器。
            r"(?m)^(\s*(?:[A-Z0-9]+_)*(?:API[_-]?KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET)(?:_[A-Z0-9]+)*\s*[:=]\s*)(.+?)\s*$"  # 密钥赋值表达式。
        ),  # 常见密钥变量赋值模式。
    ),
    (
        "password",  # 密码规则名称。
        re.compile(r"(?m)^(\s*[A-Z0-9_]*PASSWORD[A-Z0-9_]*\s*[:=]\s*)(.+?)\s*$"),  # 常见密码变量赋值模式。
    ),
]

# 私有路径覆盖 Windows 驱动器、Unix 用户目录和临时目录。
LOCAL_PRIVATE_PATH_RE = re.compile(  # 编译跨平台私有路径检测器。
    r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|/(?:Users|home|tmp)/)[^\s\"'`<>\),\]}]+"  # 私有路径表达式。
)  # 本地用户绝对路径匹配器。

# 行内规则扫描非赋值形态的邮箱和本地路径。
SANITIZED_INLINE_RULES = [
    (
        "email",  # 电子邮件规则名称。
        re.compile(r"(?<!\\)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", flags=re.IGNORECASE),  # 邮箱匹配器。
    ),
    ("local_path", LOCAL_PRIVATE_PATH_RE),  # 私有绝对路径匹配器。
]

# 明确声明的公开归属邮箱用于作者署名和学术引用，不应被发布清洗器删除。
PUBLIC_ATTRIBUTION_EMAILS = frozenset({"erie@seu.edu.cn"})

# 归一化比较保证大小写变化不会破坏公开归属保留规则。
def is_public_attribution_email(str_email: str) -> bool:
    """判断邮箱是否属于已确认的公开作者归属信息。"""

    return str_email.strip().casefold() in PUBLIC_ATTRIBUTION_EMAILS

# 二进制内容不自动改写，只报告可确认的敏感模式。
SANITIZED_BINARY_PATTERNS = [
    ("api_key", re.compile(br"sk-(?:live|proj|test)-[A-Za-z0-9_-]+")),  # OpenAI 风格密钥字节模式。
    ("password", re.compile(br"password", flags=re.IGNORECASE)),  # 密码关键词字节模式。
    ("email", re.compile(br"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),  # 邮箱字节模式。
]

# 文本识别器要求无 NUL 且可完整 UTF-8 解码。
def is_probably_text_bytes(bytes_data: bytes) -> bool:
    """判断文件字节是否可按发布文本处理。

    参数：bytes_data 为文件原始字节。
    返回：无 NUL 且可 UTF-8 解码时为 True。
    """

    # NUL 通常表示二进制格式，不进入文本替换流程。
    if b"\x00" in bytes_data:

        # 二进制候选由专用敏感模式检查。
        return False

    # UTF-8 解码是文本发布文件的最低合同。
    try:

        # 仅验证编码，不保留临时字符串。
        bytes_data.decode("utf-8")

    # 无效 UTF-8 按二进制处理。
    except UnicodeDecodeError:

        # 调用方随后执行二进制敏感模式扫描。
        return False

    # 两项条件均满足即可安全进入文本清洗。
    return True

# 换行规范化只消除 Windows 与 Unix 文本差异。
def normalize_line_endings(str_text: str) -> str:
    """把 CRLF 统一为 LF。

    参数：str_text 为待比较文本。
    返回：换行规范化后的文本。
    """

    # 内容比较不应因平台换行方式产生误报。
    return str_text.replace("\r\n", "\n")

# 正则常量声明包含敏感关键词，但不是秘密赋值。
def should_skip_sanitized_assignment_value(str_value: str) -> bool:
    """判断赋值值是否为应保留的正则表达式声明。

    参数：str_value 为赋值表达式右侧文本。
    返回：以 re.compile 调用开头时为 True。
    """

    # 保留检测规则自身，避免发布代码被误清洗破坏。
    return str_value.strip().startswith("re.compile(")

# 文本清洗器依次应用赋值规则和行内规则。
def sanitize_release_text(str_text: str) -> tuple[str, list[dict[str, str]]]:
    """清洗发布文本并记录实际命中的规则。

    参数：str_text 为源码文本。
    返回：清洗后文本与 rule/placeholder 记录列表。
    """

    # 后续规则始终在前一规则的输出上继续处理。
    str_redacted = str_text  # 当前清洗文本。

    # 记录仅包含实际发生替换的规则。
    list_matches: list[dict[str, str]] = []  # 本次清洗证据条目。

    # 赋值模式需要保留左侧变量声明。
    for str_rule_name, pattern_assignment in SANITIZED_ASSIGNMENT_RULES:

        # 规则名称决定稳定占位符。
        str_placeholder = SANITIZED_PLACEHOLDERS[str_rule_name]  # 当前赋值规则占位符。

        # 闭包标志区分完全未命中和仅命中应跳过常量。
        bool_replaced = False  # 当前规则是否替换了真实值。

        # 替换回调访问当前规则占位符并更新命中标志。
        def replace_assignment(match_assignment: re.Match[str]) -> str:
            """替换单个敏感赋值，同时保留检测规则常量。

            参数：match_assignment 为当前赋值正则匹配结果。
            返回：原始规则常量或使用占位符替换后的赋值。
            """
            nonlocal bool_replaced

            # re.compile 常量描述检测模式，不是实际秘密。
            if should_skip_sanitized_assignment_value(match_assignment.group(2)):

                # 原样保留完整赋值行。
                return match_assignment.group(0)

            # 真实赋值命中必须进入收据证据。
            bool_replaced = True  # 当前规则已替换真实敏感值。

            # 左侧声明与统一占位符合并为替换文本。
            return f"{match_assignment.group(1)}{str_placeholder}"

        # 对当前文本应用完整赋值规则。
        str_updated = pattern_assignment.sub(replace_assignment, str_redacted)  # 当前规则处理后的文本。

        # 仅真实替换时记录证据并推进文本状态。
        if bool_replaced:

            # 一条规则无论命中次数多少只记录一次。
            list_matches.append({"rule": str_rule_name, "placeholder": str_placeholder})

            # 后续规则基于已清洗结果继续执行。
            str_redacted = str_updated  # 赋值规则处理后的累计文本。

    # 行内模式可直接使用 subn 获取替换数量。
    for str_rule_name, pattern_inline in SANITIZED_INLINE_RULES:

        # 行内规则同样使用稳定占位符。
        str_placeholder = SANITIZED_PLACEHOLDERS[str_rule_name]  # 当前行内规则占位符。

        # 只统计实际替换次数，公开归属邮箱保持原文且不写入清洗收据。
        int_replaced = 0

        # 回调允许对公开归属邮箱执行精确例外，而不是放宽其他邮箱或凭据规则。
        def replace_inline(match_inline: re.Match[str]) -> str:
            """替换单个行内敏感值并保留已确认的公开归属邮箱。"""

            nonlocal int_replaced
            str_match = match_inline.group(0)
            if str_rule_name == "email" and is_public_attribution_email(str_match):
                return str_match
            int_replaced += 1
            return str_placeholder

        # 对当前规则执行可审计的逐匹配替换。
        str_updated = pattern_inline.sub(replace_inline, str_redacted)

        # 至少一次命中才形成清洗证据。
        if int_replaced:

            # 当前规则加入收据所需记录。
            list_matches.append({"rule": str_rule_name, "placeholder": str_placeholder})

            # 下一规则处理最新文本。
            str_redacted = str_updated  # 行内规则处理后的累计文本。

    # 调用方可同时写入发布副本和生成清洗收据。
    return str_redacted, list_matches

# 二进制扫描器返回去重后的敏感规则名称。
def detect_binary_sensitive_matches(bytes_data: bytes) -> list[str]:
    """识别二进制内容中的明确敏感模式。

    参数：bytes_data 为无法安全按 UTF-8 文本处理的字节。
    返回：排序并去重的敏感规则名称。
    """

    # 多个模式可能报告同一类别，最终统一去重。
    list_hits: list[str] = []  # 二进制敏感规则命中项。

    # 二进制只检测不修改，避免破坏文件格式。
    for str_rule_name, pattern_binary in SANITIZED_BINARY_PATTERNS:

        # 任意位置命中即报告该敏感类别。
        if pattern_binary.search(bytes_data):

            # 规则名称用于稳定错误和测试断言。
            list_hits.append(str_rule_name)

    # 排序集合提供确定性输出。
    return sorted(set(list_hits))

# 收据头验证器检查强制清洗模式字段。
def validate_sanitization_header(object_sanitization: object, list_errors: list[str]) -> list[object] | None:
    """验证 sanitization 顶层字段并返回原始文件条目。

    参数：object_sanitization 为收据字段，list_errors 为共享诊断列表。
    返回：files 列表；顶层块或 files 无效时返回 None。
    """

    # sanitization 必须是结构化对象。
    if not isinstance(object_sanitization, dict):

        # 缺少顶层块时无法解析任何文件证据。
        list_errors.append("release receipt sanitization block is missing")

        # 返回空状态阻止后续声明解析。
        return None

    # 自动清洗必须在收据中显式启用。
    if not bool(object_sanitization.get("enabled")):

        # false 或缺失都不构成有效证据。
        list_errors.append("release receipt sanitization enabled flag is missing or false")

    # broad 表示覆盖整个发布文件树。
    if str(object_sanitization.get("scope", "")).strip() != "broad":

        # 其他作用域不足以证明完整发布包安全。
        list_errors.append("release receipt sanitization scope is missing or invalid")

    # 安装器只接受当前自动清洗发布模式。
    if str(object_sanitization.get("mode", "")).strip() != "auto-redact-dist-copy":

        # 未知模式无法按当前合同复核。
        list_errors.append("release receipt sanitization mode is missing or invalid")

    # 每个清洗变更必须由收据记录。
    if not bool(object_sanitization.get("receipt_required")):

        # 缺少强制记录标志降低发布证据强度。
        list_errors.append("release receipt sanitization receipt_required flag is missing or false")

    # files 字段承载逐文件规则、占位符和摘要。
    object_files = object_sanitization.get("files")  # 原始清洗文件条目。

    # 非列表字段无法按顺序解析声明。
    if not isinstance(object_files, list):

        # 明确指出缺失的是文件证据列表。
        list_errors.append("release receipt sanitization files list is missing")

        # 后续没有可验证的声明集合。
        return None

    # 返回原始条目供路径安全解析。
    return object_files

# 声明解析器验证路径边界和每条记录的证据字段。
def parse_sanitization_declarations(
    path_release_dir: Path,
    list_file_entries: list[object],
    list_errors: list[str],
) -> dict[str, dict[str, Any]]:
    """解析并验证 sanitization 文件声明。

    参数：path_release_dir 为发布根，list_file_entries 为原始条目。
    参数：list_errors 为共享诊断列表。
    返回：安全相对路径到声明对象的映射。
    """

    # 只有通过路径边界检查的条目才能进入映射。
    dict_declared: dict[str, dict[str, Any]] = {}  # 安全清洗声明映射。

    # 每个条目独立验证，尽量一次报告全部收据问题。
    for object_item in list_file_entries:

        # 条目必须是 JSON 对象。
        if not isinstance(object_item, dict):

            # 非对象条目无法提供路径和证据字段。
            list_errors.append("release receipt sanitization files list contains invalid entries")

            # 继续解析其他独立条目。
            continue

        # path 字段统一转换为去空白字符串。
        str_relative_path = str(object_item.get("path", "")).strip()  # 当前声明相对路径。

        # 空路径无法定位发布成员。
        if not str_relative_path:

            # 记录精确字段缺失原因。
            list_errors.append("release receipt sanitization file entry is missing path")

            # 继续解析其他条目。
            continue

        # 路径必须先证明位于发布根目录内。
        path_declared = resolve_release_member_path(path_release_dir, str_relative_path)  # 已约束声明路径。

        # 绝对路径、父目录或符号链接逃逸均被拒绝。
        if path_declared is None:

            # 回显原始条目以便修复收据。
            list_errors.append(f"release receipt sanitization file path escapes the release root: {str_relative_path}")

            # 不可信路径不得进入后续文件读取。
            continue

        # rules 必须是包含非空名称的列表。
        object_rules = object_item.get("rules")  # 当前声明规则字段。

        # 缺失规则时记录错误但仍保留安全条目供其他复核。
        if not isinstance(object_rules, list) or not all(str(object_value).strip() for object_value in object_rules):

            # 路径信息帮助发布者定位具体记录。
            list_errors.append(f"release receipt sanitization rules are missing for {str_relative_path}")

        # placeholders 必须与规则一样提供非空列表。
        list_placeholders = object_item.get("placeholders")  # 当前声明占位符字段。

        # 缺失占位符时保留独立诊断。
        if not isinstance(list_placeholders, list) or not all(
            str(object_value).strip()  # 当前占位符必须非空。
            for object_value in list_placeholders  # 声明中的原始占位符。
        ):

            # 具体路径使错误具有可操作性。
            list_errors.append(f"release receipt sanitization placeholders are missing for {str_relative_path}")

        # 安全条目可用于摘要和内容一致性检查。
        dict_declared[str_relative_path] = object_item  # 当前安全路径对应的清洗声明。

    # 返回已过滤的不越界声明集合。
    return dict_declared

# 单个声明摘要检查在缺失记录和错误摘要间保持稳定诊断。
def validate_declared_hash(
    str_relative_path: str,
    path_release_file: Path,
    dict_declared: dict[str, dict[str, Any]],
    list_errors: list[str],
) -> None:
    """验证需要清洗的文件存在对应收据记录且摘要一致。

    参数：str_relative_path 和 path_release_file 标识发布成员。
    参数：dict_declared 为收据声明映射，list_errors 为诊断列表。
    返回：无，错误追加到 list_errors。
    """

    # 当前相对路径应存在清洗声明。
    dict_row = dict_declared.get(str_relative_path)  # 当前发布成员的清洗记录。

    # 缺少记录时无法证明清洗动作。
    if dict_row is None:

        # 回显文件路径定位缺失证据。
        list_errors.append(f"release receipt is missing sanitization record for {str_relative_path}")

        # 无记录时不再读取 sha256 字段。
        return

    # 收据摘要必须匹配最终发布副本。
    if str(dict_row.get("sha256", "")).strip() != sha256_file(path_release_file):

        # 摘要不符表示发布内容或收据发生漂移。
        list_errors.append(f"release receipt sanitization hash mismatch for {str_relative_path}")

# 文本对照助手验证单个源码文本及其发布副本。
def validate_source_text_file(
    str_relative_path: str, bytes_source: bytes,
    bytes_release: bytes, path_release_file: Path,
    dict_declared: dict[str, dict[str, Any]], set_expected_declared: set[str],
    list_errors: list[str],
) -> None:
    """验证单个 UTF-8 源码文本的确定性清洗结果。

    参数：str_relative_path、bytes_source、bytes_release 和 path_release_file 标识文件。
    参数：dict_declared、set_expected_declared 和 list_errors 保存验证状态。
    返回：无，诊断和预期声明集合原位更新。
    """

    # 调用方已证明源码字节可以 UTF-8 解码。
    str_source_text = bytes_source.decode("utf-8")  # 原始源码文本。

    # 使用单一结果变量避免误把二元组成员当作容器类型命名。
    tuple_sanitization_result = sanitize_release_text(str_source_text)  # 文本清洗结果二元组。

    # 二元组首项是期望发布文本。
    str_expected_text = tuple_sanitization_result[0]  # 确定性清洗文本。

    # 二元组次项是实际命中的清洗规则。
    list_matches = tuple_sanitization_result[1]  # 当前源码文件清洗命中记录。

    # 无敏感匹配时发布副本必须与源码字节一致。
    if not list_matches:

        # 任意差异都没有清洗收据依据。
        if bytes_release != bytes_source:

            # 报告未声明的普通文本差异。
            list_errors.append(f"undeclared release diff outside sanitization receipt: {str_relative_path}")

        # 无匹配文件不再执行清洗文本比较。
        return

    # 有清洗匹配的文件必须出现在预期声明集合中。
    set_expected_declared.add(str_relative_path)

    # 检查收据记录存在性和最终文件摘要。
    validate_declared_hash(str_relative_path, path_release_file, dict_declared, list_errors)

    # 清洗后的发布副本仍必须是 UTF-8 文本。
    if not is_probably_text_bytes(bytes_release):

        # 二进制化结果无法证明来自确定性文本替换。
        list_errors.append(f"sanitized release file is not valid UTF-8 text: {str_relative_path}")

        # 无法解码时停止当前文件比较。
        return

    # 发布文本按 UTF-8 解码后规范化换行比较。
    str_actual_text = bytes_release.decode("utf-8")  # 实际清洗发布文本。

    # 除换行风格外必须逐字符一致。
    if normalize_line_endings(str_actual_text) != normalize_line_endings(str_expected_text):

        # 非确定性差异表示发布副本被额外修改。
        list_errors.append(f"sanitized release content mismatch for {str_relative_path}")

# 二进制对照助手拒绝敏感内容和未声明差异。
def validate_source_binary_file(
    str_relative_path: str,
    bytes_source: bytes,
    bytes_release: bytes,
    list_errors: list[str],
) -> None:
    """验证单个源码二进制文件及其发布副本。

    参数：str_relative_path 为成员路径，bytes_source 和 bytes_release 为两侧字节。
    参数：list_errors 为共享诊断列表。
    返回：无，发现问题时追加诊断。
    """

    # 二进制敏感模式命中时不得尝试自动清洗。
    list_hits = detect_binary_sensitive_matches(bytes_source)  # 源码二进制敏感类别。

    # 敏感二进制必须直接阻断发布。
    if list_hits:

        # 长错误拆分以保持可读行宽。
        list_errors.append(
            f"binary file contains sensitive content and cannot be sanitized safely: {str_relative_path}"
        )

        # 已阻断文件无需再报告内容差异。
        return

    # 无敏感命中的二进制发布副本必须保持原样。
    if bytes_release != bytes_source:

        # 二进制差异不能由文本清洗收据解释。
        list_errors.append(f"undeclared binary release diff outside sanitization receipt: {str_relative_path}")

# 源码对照模式验证发布副本只包含确定性清洗差异。
def validate_against_source(
    path_source_skill: Path,
    path_release_dir: Path,
    str_receipt_name: str,
    dict_declared: dict[str, dict[str, Any]],
    list_errors: list[str],
) -> None:
    """对照源码技能验证发布副本和清洗收据。

    参数：path_source_skill、path_release_dir 和 str_receipt_name 定位文件树。
    参数：dict_declared 为声明映射，list_errors 为诊断列表。
    返回：无，所有差异写入 list_errors。
    """

    # 记录源码中实际需要清洗的文件集合。
    set_expected_declared: set[str] = set()  # 根据源码计算的清洗声明路径。

    # 排序遍历确保诊断顺序稳定。
    for path_source_file in sorted(path_source_skill.rglob("*")):

        # 目录不参与内容比较。
        if not path_source_file.is_file():

            # 收据元数据不属于源码与发布内容差异范围。
            continue

        # 源码和发布包使用同一 POSIX 相对路径。
        str_relative_path = path_source_file.relative_to(path_source_skill).as_posix()  # 当前源码成员相对路径。

        # 收据自身不是技能内容对照对象。
        if str_relative_path == str_receipt_name:

            # 继续检查下一个源码成员。
            continue

        # 对照文件必须存在于发布包中才执行字节比较。
        path_release_file = path_release_dir / str_relative_path  # 对应发布成员路径。

        # 缺失成员由其他发布清单验证器报告。
        if not path_release_file.is_file():

            # 避免重复产生清洗层缺失错误。
            continue

        # 两侧字节用于文本清洗或二进制一致性判断。
        bytes_source = path_source_file.read_bytes()  # 原始源码文件字节。

        # 发布副本字节代表实际待安装内容。
        bytes_release = path_release_file.read_bytes()  # 最终发布文件字节。

        # 文本和二进制分别交给低嵌套单文件助手。
        if is_probably_text_bytes(bytes_source):

            # 文本助手同时维护预期声明集合。
            validate_source_text_file(
                str_relative_path, bytes_source,  # 当前路径和源码文本字节。
                bytes_release, path_release_file,  # 发布文本字节和文件路径。
                dict_declared, set_expected_declared,  # 声明映射和预期集合。
                list_errors,  # 共享诊断列表。
            )

        # 非文本源码只能检测和拒绝，不能自动改写。
        else:

            # 二进制助手执行敏感扫描和原样性比较。
            validate_source_binary_file(str_relative_path, bytes_source, bytes_release, list_errors)

    # 收据不得声明源码实际无需清洗的文件。
    list_unexpected = sorted(set(dict_declared) - set_expected_declared)  # 多余清洗声明路径。

    # 每条多余声明独立报告。
    for str_relative_path in list_unexpected:

        # 精确路径帮助删除错误收据条目。
        list_errors.append(f"release receipt declares unexpected sanitized file: {str_relative_path}")

# 外部包模式在没有源码仓库时执行降低保证度的自洽验证。
def validate_external_release(
    path_release_dir: Path,
    str_receipt_name: str,
    dict_declared: dict[str, dict[str, Any]],
    list_errors: list[str],
) -> None:
    """验证无法关联源码仓库的外部发布包。

    参数：path_release_dir 和 str_receipt_name 定位外部包内容。
    参数：dict_declared 为声明映射，list_errors 为诊断列表。
    返回：无，检测结果写入 list_errors。
    """

    # 遍历实际发布内容识别残留敏感信息。
    for path_release_file in sorted(path_release_dir.rglob("*")):

        # 跳过目录和发布收据自身。
        if not path_release_file.is_file() or path_release_file.name == str_receipt_name:

            # 继续检查下一个发布成员。
            continue

        # 相对路径用于收据映射和稳定诊断。
        str_relative_path = path_release_file.relative_to(path_release_dir).as_posix()  # 当前外部发布成员路径。

        # 读取一次字节供文本或二进制分支复用。
        bytes_release = path_release_file.read_bytes()  # 当前外部发布成员字节。

        # UTF-8 文本可直接重新运行清洗器检查残留。
        if is_probably_text_bytes(bytes_release):

            # 文本识别已证明解码安全。
            str_release_text = bytes_release.decode("utf-8")  # 当前外部发布文本。

            # 重新清洗用于识别发布包内仍存在的敏感值。
            tuple_sanitization_result = sanitize_release_text(str_release_text)  # 外部包清洗复核二元组。

            # 首项表示重新清洗后的期望文本。
            str_sanitized_text = tuple_sanitization_result[0]  # 外部包复核清洗文本。

            # 次项表示发布内容仍能命中的规则。
            list_matches = tuple_sanitization_result[1]  # 外部包残留敏感规则。

            # 命中规则时收据必须声明当前文件。
            if list_matches:

                # 声明摘要与实际发布文件必须一致。
                validate_declared_hash(str_relative_path, path_release_file, dict_declared, list_errors)

            # 重新清洗改变内容即证明发布包仍含未清洗信息。
            if normalize_line_endings(str_release_text) != normalize_line_endings(str_sanitized_text):

                # 外部包无法回溯源码，只能直接阻断残留敏感值。
                list_errors.append(
                    f"release directory still contains unsanitized sensitive content: {str_relative_path}"
                )

        # 非文本内容执行保守敏感模式扫描。
        else:

            # 明确模式命中足以阻断外部二进制文件。
            list_hits = detect_binary_sensitive_matches(bytes_release)  # 外部二进制敏感类别。

            # 有命中时报告具体文件。
            if list_hits:

                # 二进制不自动修改，要求发布者处理源文件。
                list_errors.append(f"release directory contains sensitive binary content: {str_relative_path}")

    # 所有声明必须指向真实文件且摘要匹配。
    for str_relative_path, dict_row in dict_declared.items():

        # 声明路径此前已完成根目录边界验证。
        path_release_file = path_release_dir / str_relative_path  # 声明对应的外部发布成员。

        # 不存在文件使收据证据失效。
        if not path_release_file.is_file():

            # 回显声明路径定位无效条目。
            list_errors.append(f"release receipt sanitization file entry points to a missing file: {str_relative_path}")

            # 缺失文件不能计算摘要。
            continue

        # 现存文件摘要必须与收据一致。
        if str(dict_row.get("sha256", "")).strip() != sha256_file(path_release_file):

            # 摘要漂移表示外部包在记录后发生变化。
            list_errors.append(f"release receipt sanitization hash mismatch for {str_relative_path}")

# 公共入口根据收据能否关联源码选择强或降低保证度验证。
def validate_release_sanitization(
    path_release_dir: Path,
    path_receipt: Path,
    dict_receipt: dict[str, Any],
    path_repo_root: Path | None,
    list_errors: list[str],
) -> None:
    """验证发布收据记录的完整清洗证据。

    参数：path_release_dir、path_receipt 和 dict_receipt 描述发布包。
    参数：path_repo_root 为可选源码仓库，list_errors 为共享诊断列表。
    返回：无，所有验证错误追加到 list_errors。
    """

    # 延迟导入打破清洗与仓库验证模块的初始化环。
    from install_repository_validation import source_skill_dir_from_receipt

    # 顶层清洗字段必须先满足模式合同。
    list_file_entries = validate_sanitization_header(  # 通过头部验证的原始文件条目。
        dict_receipt.get("sanitization"),  # 收据原始清洗块。
        list_errors,  # 顶层合同诊断列表。
    )  # 完成清洗块顶层合同检查。

    # 无有效 files 列表时没有可继续复核的声明。
    if list_file_entries is None:

        # 顶层验证已记录具体错误。
        return

    # 安全解析每条文件声明。
    dict_declared = parse_sanitization_declarations(  # 安全且可继续验证的清洗声明映射。
        path_release_dir,  # 发布包路径边界。
        list_file_entries,  # 收据原始文件声明。
        list_errors,  # 声明字段诊断列表。
    )  # 完成逐条路径和证据字段解析。

    # 有源码仓库时尝试从收据定位对应技能目录。
    path_source_skill = (
        source_skill_dir_from_receipt(path_repo_root, dict_receipt)  # 收据关联的源码技能目录。
        if path_repo_root is not None  # 仅源码仓库上下文允许关联。
        else None  # 外部发布包没有源码目录。
    )  # 可选源码技能目录。

    # 源码存在时执行最高保证度的逐文件对照。
    if path_source_skill is not None:

        # 对照验证同时检查清洗差异和多余声明。
        validate_against_source(
            path_source_skill,  # 收据关联源码技能根。
            path_release_dir,  # 最终发布包根。
            path_receipt.name,  # 发布收据文件名。
            dict_declared,  # 源码对照使用的声明映射。
            list_errors,  # 源码对照诊断列表。
        )

        # 强验证完成后无需运行外部包逻辑。
        return

    # 无源码关联时执行外部包自洽和残留检查。
    validate_external_release(
        path_release_dir,  # 降低保证度检查的发布包根。
        path_receipt.name,  # 外部包中需排除的收据名称。
        dict_declared,  # 外部包自洽检查的声明映射。
        list_errors,  # 外部包复核诊断列表。
    )
