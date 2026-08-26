"""读取语言 catalog 并提供 canonical 语言归一化。"""

# 延迟类型解析，保持配置 helper 与 Python 3.10 运行兼容。
from __future__ import annotations

# 语言合同只依赖 JSON 和路径标准库。
import json
from pathlib import Path

# 语言 catalog 路径由当前技能根动态推导。
def _language_catalog_path() -> Path:
    """返回当前技能的语言 catalog 路径。

    参数：无。
    返回：语言 catalog 的绝对路径。
    """

    # 当前文件位于 scripts/python/common，向上解析技能根。
    path_skill_root = Path(__file__).resolve().parents[3]  # 当前技能根目录

    # 语言配置属于技能的受管 config 目录。
    return path_skill_root / "config" / "languages.json"

# 读取并校验语言 catalog 根对象。
def load_language_catalog() -> dict[str, object]:
    """读取语言 catalog JSON。

    参数：无。
    返回：语言 catalog 的顶层对象映射。
    异常：ValueError 表示 catalog 缺失、损坏或根类型错误。
    """

    # catalog 缺失时不能回退到源码中的语言字面量。
    path_catalog = _language_catalog_path()  # 语言 catalog 文件

    # 缺少 catalog 时必须立即阻断后续渲染。
    if not path_catalog.is_file():

        # 缺失配置必须阻断语言渲染。
        raise ValueError("> ERR: [Python] language catalog is missing")

    # 解析 UTF-8 JSON 并保留标准错误边界。
    try:

        # catalog 根对象提供默认值和 alias 映射。
        obj_catalog = json.loads(path_catalog.read_text(encoding="utf-8"))  # catalog 解析对象

    # 配置损坏时返回可定位的机器错误。
    except (OSError, UnicodeError, json.JSONDecodeError) as object_error:

        # 不回显完整路径或配置正文，只保留错误类型。
        raise ValueError(
            "> ERR: [Python] language catalog is invalid: " + type(object_error).__name__
        ) from object_error

    # 只有对象根才能提供结构化语言字段。
    if not isinstance(obj_catalog, dict):

        # 标量或数组根无法形成语言合同。
        raise ValueError("> ERR: [Python] language catalog root must be an object")

    # 返回经过根类型确认的 catalog。
    return obj_catalog

# 从 catalog 默认节点读取指定用途的 canonical language ID。
def default_language(str_scope: str) -> str:
    """返回 conversation 或 documentation 的默认语言 ID。

    参数：str_scope 为 catalog defaults 中的用途键。
    返回：canonical language ID。
    异常：ValueError 表示用途缺失或默认语言不可用。
    """

    # 读取默认字段和语言记录，拒绝隐式 fallback。
    dict_catalog = load_language_catalog()  # 当前语言 catalog

    # 读取默认语言节点，为 scope 解析提供数据来源。
    obj_defaults = dict_catalog.get("defaults")  # 默认语言节点

    # 读取 canonical 语言节点，校验默认值是否已声明。
    obj_languages = dict_catalog.get("languages")  # canonical 语言节点

    # 默认节点或语言节点缺失时必须停止解析。
    if not isinstance(obj_defaults, dict) or not isinstance(obj_languages, dict):

        # catalog 结构不完整时阻断渲染。
        raise ValueError("> ERR: [Python] language catalog defaults are invalid")

    # 用途键必须存在且指向已声明语言。
    str_language = str(obj_defaults.get(str_scope, "")).strip()  # 当前用途解析出的 canonical ID

    # 空值或未知 canonical ID 都不能继续渲染。
    if not str_language or str_language not in obj_languages:

        # 缺失或未知默认语言不能由代码猜测。
        raise ValueError("> ERR: [Python] language catalog default is invalid")

    # 返回 canonical ID，渲染器不接触 alias 文本。
    return str_language

# 将用户输入或旧配置别名归一化为 catalog canonical ID。
def canonical_language(str_value: str, str_scope: str) -> str:
    """把语言输入转换为指定用途的 canonical language ID。

    参数：
        str_value：用户或旧配置提供的语言文本。
        str_scope：conversation 或 documentation 用途。
    返回：catalog 声明的 canonical language ID。
    异常：ValueError 表示空值、未知 alias 或用途不允许该语言。
    """

    # 读取 catalog，保证 alias 和文档允许性来自配置。
    dict_catalog = load_language_catalog()  # canonicalization 使用的完整语言 catalog

    # 为 alias 匹配加载已声明的语言记录集合。
    obj_languages = dict_catalog.get("languages")  # alias 匹配语言记录映射

    # 缺少语言映射时不能解释任何用户输入。
    if not isinstance(obj_languages, dict):

        # 语言映射损坏时不能完成输入归一化。
        raise ValueError("> ERR: [Python] language catalog languages are invalid")

    # 规范化待匹配文本，保留 catalog 的大小写语义。
    str_candidate = str(str_value).strip()  # 待匹配的规范化语言文本

    # 空输入必须在 alias 查找前被拒绝。
    if not str_candidate:

        # 空语言值必须由调用方补齐。
        raise ValueError("> ERR: [Python] language value is empty")

    # 按 canonical ID 和 aliases 顺序查找匹配语言。
    for obj_language_id, obj_language in obj_languages.items():

        # 每个语言记录必须是对象才能读取 aliases 和文档权限。
        if not isinstance(obj_language, dict):

            # 损坏记录不能参与 alias 匹配。
            continue

        # canonical ID 自身也是合法输入 alias。
        list_aliases = [str(obj_language_id)] + [str(item) for item in obj_language.get("aliases", [])]  # 当前语言的全部 alias

        # 比较使用大小写不敏感文本，返回配置中的 canonical key。
        if any(str_alias.casefold() == str_candidate.casefold() for str_alias in list_aliases):

            # documentation 只允许 catalog 标记为 document_allowed 的语言。
            if str_scope == "documentation" and not obj_language.get("document_allowed", False):

                # 当前语言不能进入文档渲染。
                raise ValueError("> ERR: [Python] language is not allowed for documentation")

            # 返回 canonical language ID，供 profile 和 renderer 绑定。
            return str(obj_language_id)

    # 未知输入不能回退为当前会话或文档语言。
    raise ValueError("> ERR: [Python] language alias is unknown")

