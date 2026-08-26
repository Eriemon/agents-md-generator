"""检查产品源是否把运行时业务值写死在 Python 代码或注释中。"""

# 当前门禁只使用标准库读取配置、语法树和注释令牌。
from __future__ import annotations

# AST/tokenize 分别覆盖字符串常量和注释内容。
import ast
import io
import sys
import tokenize
from pathlib import Path
from typing import Any

# 运行时合同 loader 在函数边界内动态加载，避免模块导入产生路径副作用。
def _load_runtime_contract_loaders() -> tuple[Any, Any]:
    """返回共享 runtime contract loader。

    参数：无；共享目录由当前 verify 模块位置解析。
    返回：load_json_role 与 load_runtime_manifest 函数元组。
    """

    # 共享 loader 路径由当前 verify 模块目录动态解析。
    path_common_dir = Path(__file__).resolve().parents[1] / "common"  # 共享运行时目录

    # 直接脚本加载时补充共享模块搜索路径。
    if str(path_common_dir) not in sys.path:

        # 只影响当前验证进程的模块解析。
        sys.path.insert(0, str(path_common_dir))

    # 读取共享 runtime contract loader。
    from runtime_contracts import load_json_role, load_runtime_manifest

    # 返回两个 loader，调用方负责绑定具体项目根。
    return load_json_role, load_runtime_manifest

# 递归收集 JSON 结构中的叶子文本。
def _collect_text(value: object, list_values: list[str]) -> None:
    """把合同对象中的文本叶子追加到列表。

    参数：value 为待递归对象，list_values 为结果列表。
    返回：无业务返回值；列表会被原地追加。
    """

    # 字符串叶子是可能进入源码的业务值。
    if isinstance(value, str) and value.strip():

        # 去除空白后保存稳定比较文本。
        list_values.append(value.strip())

        # 字符串叶子不再继续递归。
        return

    # 列表逐项递归，保留合同顺序。
    if isinstance(value, list):

        # 每个列表项继续交给相同收集逻辑。
        for item in value:

            # 递归收集当前列表项的叶子文本。
            _collect_text(item, list_values)

        # 列表分支完成后返回调用方。
        return

    # 映射只递归 value，字段名由协议定义而非业务值。
    if isinstance(value, dict):

        # 逐项遍历合同值。
        for item in value.values():

            # 递归收集当前字段的叶子文本。
            _collect_text(item, list_values)

# 展开 JSON pointer 的单个字段段。
def _pointer_step_values(list_current: list[object], string_token: str) -> list[object]:
    """返回单个 pointer 段的下一层候选对象。

    参数:
        list_current: 当前 pointer 层的候选对象。
        string_token: 当前 pointer 字段或通配段。
    返回:
        下一层匹配对象列表。
    """

    # 每一层重新建立下一批候选对象。
    list_next: list[object] = []  # 下一层匹配集合

    # 在当前候选集合中处理通配和普通字段。
    for object_item in list_current:

        # 通配段只展开列表对象。
        if string_token == "*" and isinstance(object_item, list):

            # 把列表元素全部加入下一层候选。
            list_next.extend(object_item)

        # 普通段只读取映射中存在的字段。
        elif isinstance(object_item, dict) and string_token in object_item:

            # 保存当前字段对应的对象值。
            list_next.append(object_item[string_token])

    # 返回当前 pointer 段的下一层匹配。
    return list_next

# 按 JSON pointer 展开 policy 声明的合同值。
def _pointer_values(object_value: object, string_pointer: str) -> list[object]:
    """按 JSON pointer（支持单段通配）提取合同值。

    参数:
        object_value: 待查询合同对象。
        string_pointer: 相对字段指针。
    返回:
        匹配指针的对象列表，未命中时为空列表。
    """

    # 过滤空指针段，保留合同声明顺序。
    list_tokens = [token for token in string_pointer.split("/") if token]  # 指针段列表

    # 当前匹配集合从合同根对象开始。
    list_current: list[object] = [object_value]  # 当前匹配对象集合

    # 按指针段逐层委托单段展开逻辑。
    for string_token in list_tokens:

        # 进入下一指针段继续匹配。
        list_current = _pointer_step_values(list_current, string_token)  # 当前层匹配结果

    # 返回最终指针层的匹配对象。
    return list_current

# 收集 Python 文件中的字符串和注释证据。
def _source_literals(path_file: Path) -> list[tuple[int, str, str]]:
    """返回文件中的字符串/注释三元组。

    参数：path_file 为待扫描 Python 文件。
    返回：行号、类别和文本组成的列表。
    """

    # 读取 UTF-8 源码，保持门禁与项目编码合同一致。
    string_source = path_file.read_text(encoding="utf-8")  # 当前文件源码文本

    # 统一保存字符串常量和注释的行号、类别与内容。
    list_literals: list[tuple[int, str, str]] = []  # 当前文件原始字面量证据

    # AST 只提取字符串常量，避免把标识符误报为业务值。
    tree = ast.parse(string_source, filename=str(path_file))  # 当前文件 AST

    # 记录 AST 字符串常量的起始行。
    for node in ast.walk(tree):

        # 只收集字符串常量，忽略数字和标识符。
        if isinstance(node, ast.Constant) and isinstance(node.value, str):

            # 保存字符串常量的源码位置和文本。
            list_literals.append((node.lineno, "string", node.value))

    # tokenize 提取注释，确保注释也受反硬编码门禁约束。
    for token in tokenize.generate_tokens(io.StringIO(string_source).readline):

        # 注释文本和字符串一样需要执行业务值匹配。
        if token.type == tokenize.COMMENT:

            # 记录注释 token 的源码行和原始文本。
            list_literals.append((token.start[0], "comment", token.string))

    # 返回全部原始证据，调用方再排除协议字面量。
    return list_literals

# 按 token 边界判断一段文本是否包含独立合同值。
def _contains_business_value(string_text: str, string_value: str) -> bool:
    """按 token 边界匹配合同值，避免文件名子串误报。

    参数：string_text 为待检查文本；string_value 为合同业务值。
    返回：文本中存在独立合同值且不是文件后缀时返回 True。
    """

    # 从文本首个候选位置开始查找合同值。
    int_start = string_text.find(string_value)  # 当前候选起点

    # 逐个候选位置检查左右 token 边界。
    while int_start >= 0:

        # 计算当前合同值的结束位置。
        int_end = int_start + len(string_value)  # 当前候选结束位置

        # 左侧边界阻止更长标识符中的子串误报。
        bool_left = int_start == 0 or not (string_text[int_start - 1].isalnum() or string_text[int_start - 1] == "_")  # 左边界状态

        # 检查候选结尾，阻止更长标识符中的子串误报。
        bool_right = int_end == len(string_text) or not (string_text[int_end].isalnum() or string_text[int_end] == "_")  # 右边界状态

        # 文件名后缀中的同名片段不算独立业务值。
        bool_file_suffix = (
            int_end < len(string_text) - 1  # 候选后仍有文件后缀空间
            and string_text[int_end] == "."  # 候选后紧接后缀分隔符
            and string_text[int_end + 1].isalnum()  # 分隔符后是后缀字符
        )  # 文件后缀状态

        # 只有独立 token 且不是文件后缀时命中业务值。
        if bool_left and bool_right and not bool_file_suffix:

            # 当前文本包含一个独立合同值。
            return True

        # 从下一个位置继续查找，覆盖同一文本的多次出现。
        int_start = string_text.find(string_value, int_start + 1)  # 下一候选起点

    # 所有候选都不是独立业务值。
    return False

# 收集单个 value source 声明指向的业务值叶子。
def _collect_source_business_values(
    dict_source: object,
    dict_binding: dict[str, object],
    func_load_json_role: Any,
    list_business_values: list[str],
) -> None:
    """把一个 policy value source 的业务文本追加到结果列表。

    参数：dict_source 为 policy value source；dict_binding 为 runtime binding；
    func_load_json_role 为 role loader；list_business_values 为累计列表。
    返回：无；结果原地追加到 list_business_values。
    """

    # 非对象声明不具备 role/pointer 字段，直接忽略。
    if not isinstance(dict_source, dict):

        # policy 错误形状由上层 schema 负责报告。
        return

    # 读取 value source 对应的 role 名称。
    str_role_name = str(dict_source.get("role", ""))  # 当前来源声明要读取的 role 名称

    # 加载已经绑定摘要的 role 对象。
    dict_role = func_load_json_role(dict_binding, str_role_name)  # 当前来源 role 的已校验内容

    # 读取可选 JSON pointer 列表。
    list_pointers = dict_source.get("pointers", [])  # value source 指针列表

    # 没有指针时扫描完整 role 对象。
    if not isinstance(list_pointers, list) or not list_pointers:

        # 递归收集 role 中所有业务值叶子。
        _collect_text(dict_role, list_business_values)

        # 完整 role 已经收集完毕。
        return

    # 有指针时仅扫描每个指针的命中对象。
    for string_pointer in list_pointers:

        # 非字符串指针不参与 JSON pointer 展开。
        if not isinstance(string_pointer, str):

            # 忽略不符合 policy schema 的指针值。
            continue

        # 展开指针命中对象并收集其叶子文本。
        for object_value in _pointer_values(dict_role, string_pointer):

            # 当前指针命中值追加到统一业务值列表。
            _collect_text(object_value, list_business_values)

# 汇总 policy 声明的所有业务值叶子。
def _collect_policy_business_values(
    dict_policy: dict[str, object],
    dict_binding: dict[str, object],
    func_load_json_role: Any,
) -> list[str]:
    """根据 policy value_sources 返回业务值候选列表。

    参数：dict_policy 为参数化策略；dict_binding 为 runtime binding；func_load_json_role 为 role loader。
    返回：policy 声明的业务值文本列表。
    """

    # 汇总所有 value source 的业务值叶子。
    list_business_values: list[str] = []  # 当前业务值候选列表

    # 按 policy 声明顺序处理 value source。
    for dict_source in dict_policy.get("value_sources", []):

        # 把单个来源交给独立 helper，避免主流程深层嵌套。
        _collect_source_business_values(
            dict_source,
            dict_binding,
            func_load_json_role,
            list_business_values,
        )

    # 返回所有 policy 业务值候选。
    return list_business_values

# 扫描一个源码文本中的业务值命中。
def _scan_literal_hits(
    path_file: Path,
    line_number: int,
    kind: str,
    text: str,
    set_business_values: set[str],
    path_project_root: Path,
) -> list[dict[str, object]]:
    """返回一条源码证据中的参数化命中记录。

    参数：path_file、line_number、kind、text 为源码证据；set_business_values 为业务值集合；path_project_root 为相对路径根。
    返回：当前证据命中的脱敏记录列表。
    """

    # 长业务值优先匹配，避免短值遮蔽更具体命中。
    list_hits: list[dict[str, object]] = []  # 当前证据命中列表

    # 逐项检查 policy 业务值的 token 边界。
    for business_value in sorted(set_business_values, key=len, reverse=True):

        # 只记录独立 token 命中的业务值。
        if _contains_business_value(text, business_value):

            # 保存相对路径、行号和类别，不回显业务值文本。
            list_hits.append(
                {
                    "file": path_file.relative_to(path_project_root).as_posix(),
                    "line": line_number,
                    "kind": kind,
                    "value_category": "runtime-contract",
                }
            )

    # 返回当前源码证据的脱敏命中。
    return list_hits

# 非 Python 消费表面按行保留普通文本，覆盖脚本、模板和 Markdown。
def _plain_text_literals(path_file: Path) -> list[tuple[int, str, str]]:
    """返回非 Python 文件的逐行文本证据。

    参数：path_file 为脚本、模板或当前文档文件。
    返回：行号、plain_text 类别和文本组成的列表。
    """

    # UTF-8 文本是当前脚本、模板和 Markdown 的统一编码合同。
    string_source = path_file.read_text(encoding="utf-8")  # 当前消费文件文本

    # 每行作为普通文本扫描，避免业务值藏在非 Python 注释或模板语法中。
    list_literals = [  # 非 Python 文本证据
        (int_line_number, "plain_text", str_line)  # 当前行的参数化扫描证据
        for int_line_number, str_line in enumerate(string_source.splitlines(), 1)  # 保留真实行号
    ]  # 完成普通文本证据收集

    # 返回逐行文本，调用方统一执行业务值 token 检查。
    return list_literals

# 扫描所有目标 Python 文件并汇总参数化命中。
def _scan_parameterization_files(
    list_files: list[Path],
    set_business_values: set[str],
    path_project_root: Path,
) -> list[dict[str, object]]:
    """返回所有目标文件中的参数化命中记录。

    参数：list_files 为目标 Python 文件；set_business_values 为业务值集合；path_project_root 为相对路径根。
    返回：脱敏命中列表。
    """

    # 累计所有源码文件的脱敏命中。
    list_hits: list[dict[str, object]] = []  # 参数化扫描命中列表

    # 遍历目标文件并交给单条证据 helper。
    for path_file in list_files:

        # Python 使用 AST/tokenize，其余消费表面使用逐行文本扫描。
        func_literal_loader = _source_literals if path_file.suffix.casefold() == ".py" else _plain_text_literals  # 当前文件证据加载器

        # 执行按扩展名选择的证据加载器。
        list_literals = func_literal_loader(path_file)  # 当前文件的参数化证据

        # 当前文件同时检查字符串、注释、docstring 或普通文本。
        for line_number, kind, text in list_literals:

            # 合并当前源码证据命中，保持文件顺序。
            list_hits.extend(
                _scan_literal_hits(
                    path_file, line_number, kind,
                    text, set_business_values, path_project_root,
                )
            )

    # 返回所有目标文件的脱敏命中。
    return list_hits

# 根据配置判断文件是否落入排除目录。
def _is_excluded_path(
    path_file: Path,
    path_project_root: Path,
    set_excluded_roots: set[str],
) -> bool:
    """判断文件相对路径是否落入配置声明的排除目录。

    参数：path_file 为候选文件；path_project_root 为项目根；set_excluded_roots 为排除目录名集合。
    返回：候选文件位于排除目录时返回 True，否则返回 False。
    """

    # 将候选路径绑定到项目根；解析失败时交由上层边界拒绝。
    try:

        # 保存候选文件相对项目根的目录段。
        tuple_path_parts = path_file.resolve().relative_to(path_project_root.resolve()).parts  # 候选文件相对路径段

    # 相对路径解析失败表示候选在项目边界外。
    except ValueError:

        # 项目外路径由上层 Skill 根边界负责拒绝。
        return False

    # 只要任一目录段命中策略集合，就跳过当前文件。
    return any(str_part in set_excluded_roots for str_part in tuple_path_parts)

# 根据表面 base 选择受管项目根。
def _surface_base_path(
    dict_surface: dict[str, object],
    path_skill_root: Path,
    path_project_root: Path,
) -> Path | None:
    """返回消费表面的 project 或 skill 根。

    参数：dict_surface 为消费表面配置；path_skill_root 与 path_project_root 为受管边界。
    返回：已选择的根路径；未知 base 返回 None。
    """

    # base 只允许绑定已解析的两类受管根。
    str_surface_base = str(dict_surface.get("base", "")).strip().casefold()  # 表面根类型

    # skill 表面绑定技能根。
    if str_surface_base == "skill":

        # 返回技能侧消费根。
        return path_skill_root

    # project 表面绑定项目根。
    if str_surface_base == "project":

        # 返回项目侧消费根。
        return path_project_root

    # 未知 base 不猜测路径。
    return None

# 将配置声明的消费表面根追加到请求列表。
def _append_consumer_surface_roots(
    dict_policy: dict[str, object],
    list_requested_roots: list[Path],
    path_skill_root: Path,
    path_project_root: Path,
    bool_narrow_scan: bool,
) -> None:
    """追加非窄扫描模式下的消费表面根。

    参数:
        dict_policy: 参数化策略对象。
        list_requested_roots: 待扩展的扫描根列表。
        path_skill_root: 技能侧受管根。
        path_project_root: 项目侧受管根。
        bool_narrow_scan: 是否已有显式目标。
    返回:
        无；列表原地追加有效消费根。
    """

    # 显式窄扫描目标不再扩展完整消费面。
    if bool_narrow_scan:

        # 调用方已声明范围，保持边界最小化。
        return

    # 遍历配置声明的所有消费表面。
    for dict_surface in dict_policy.get("consumer_surfaces", {}).values():

        # 非对象表面由 schema gate 报告，当前跳过。
        if not isinstance(dict_surface, dict):

            # 不从损坏配置推测路径。
            continue

        # 解析表面 base 到已验证的受管根。
        path_surface_base = _surface_base_path(dict_surface, path_skill_root, path_project_root)  # 表面绑定根

        # 未知 base 不参与路径展开。
        if path_surface_base is None:

            # 保留 schema 层的具体错误，不扩大扫描范围。
            continue

        # 将有效文本根绑定到表面 base。
        for str_surface_root in dict_surface.get("roots", []):

            # 只有非空字符串才能形成相对路径。
            if isinstance(str_surface_root, str) and str_surface_root.strip():

                # 将表面相对根追加到统一请求列表。
                list_requested_roots.append(path_surface_base / str_surface_root)

# 收敛请求根到项目边界内的绝对路径。
def _resolve_requested_roots(
    list_requested_roots: list[Path],
    path_project_root: Path,
    path_skill_root: Path,
) -> list[Path]:
    """返回项目边界内的扫描根。

    参数:
        list_requested_roots: 调用方和策略请求的根列表。
        path_project_root: 项目边界锚点。
        path_skill_root: 技能边界锚点。
    返回:
        已解析且仍在项目根内的扫描根列表。
    """

    # 保存通过范围边界的扫描根。
    list_roots: list[Path] = []  # 受管参数化扫描根

    # 逐项解析调用方和策略请求。
    for path_requested_root in list_requested_roots:

        # 后续边界判断只使用绝对路径。
        path_requested_resolved = path_requested_root.resolve()  # 当前请求扫描根

        # 项目根请求收敛到 Skill 产品根。
        if path_requested_resolved == path_project_root:

            # 使用技能根承载默认产品扫描。
            list_roots.append(path_skill_root)

            # 当前请求已完成范围收敛，不再执行后续分支。
            continue

        # 项目根内的目标保留为窄扫描根。
        if path_requested_resolved.is_relative_to(path_project_root):

            # 记录通过边界验证的目标。
            list_roots.append(path_requested_resolved)

    # 返回收敛后的扫描根。
    return list_roots

# 判断单个文件是否符合策略扩展名和排除目录。
def _is_allowed_parameterization_file(
    path_file: Path,
    set_consumer_extensions: set[str],
    path_project_root: Path,
    set_excluded_roots: set[str],
) -> bool:
    """判断文件是否可进入参数化扫描清单。

    参数:
        path_file: 候选文件。
        set_consumer_extensions: 策略声明的扩展名集合。
        path_project_root: 项目边界。
        set_excluded_roots: 排除目录集合。
    返回:
        候选文件符合全部门禁时返回 True。
    """

    # 目录、符号链接和不支持扩展名都直接排除。
    bool_file_shape = (  # 候选文件形状检查结果
        path_file.is_file()  # 文件必须真实存在
        and not path_file.is_symlink()  # 符号链接不得跨越边界
        and (  # 至少满足一个策略扩展名条件
            path_file.suffix.casefold() in set_consumer_extensions  # 扩展名命中策略
            or path_file.name in set_consumer_extensions  # 特殊文件名命中策略
        )
    )  # 完成候选文件形状判断

    # 只有通过形状和排除目录检查的文件才可扫描。
    return bool_file_shape and not _is_excluded_path(path_file, path_project_root, set_excluded_roots)

# 展开扫描根并返回策略允许的文件。
def _collect_parameterization_files(
    list_roots: list[Path],
    set_consumer_extensions: set[str],
    path_project_root: Path,
    set_excluded_roots: set[str],
) -> list[Path]:
    """收集受管根下的参数化消费文件。

    参数:
        list_roots: 已收敛的扫描根。
        set_consumer_extensions: 文件扩展名筛选集合。
        path_project_root: 项目边界。
        set_excluded_roots: 排除目录集合。
    返回:
        按根顺序收集的消费文件列表。
    """

    # 保存当前待扫描消费文件。
    list_files: list[Path] = []  # 参数化消费文件

    # 按调用方提供的目标顺序展开目录或单文件。
    for path_root in list_roots:

        # 显式文件目标直接按策略筛选。
        if path_root.is_file():

            # 通过策略筛选后加入清单。
            bool_allowed_file = _is_allowed_parameterization_file(  # 显式文件筛选结果
                path_root,  # 当前显式文件
                set_consumer_extensions,  # 递归遍历当前策略扩展名
                path_project_root,  # 递归检查所在项目边界
                set_excluded_roots,  # 递归过滤目录集合
            )  # 完成显式文件筛选

            # 只有通过扩展名和排除目录检查的文件才加入。
            if bool_allowed_file:

                # 显式文件不再递归展开。
                list_files.append(path_root)

            # 当前根已经作为单文件处理完毕。
            continue

        # 不存在或非目录目标保持 fail-closed。
        if not path_root.is_dir():

            # 缺失可选目标不产生扫描文件。
            continue

        # 递归加入目录中的策略声明消费文件。
        for path_file in path_root.rglob("*"):

            # 复用统一文件筛选，避免分支间规则漂移。
            bool_allowed_file = _is_allowed_parameterization_file(  # 递归文件筛选结果
                path_file,  # 当前递归文件
                set_consumer_extensions,  # 策略扩展名集合
                path_project_root,  # 项目边界
                set_excluded_roots,  # 排除目录集合
            )  # 完成递归文件筛选

            # 只有通过筛选的递归文件才写入清单。
            if bool_allowed_file:

                # 保持目录递归发现顺序。
                list_files.append(path_file)

    # 返回稳定的消费文件清单。
    return list_files

# 从 policy 业务值候选中构造扫描过滤集合。
def _policy_scan_values(
    dict_policy: dict[str, object],
    list_business_values: list[str],
) -> tuple[set[str], set[str]]:
    """返回业务值和排除目录过滤集合。

    参数:
        dict_policy: 参数化策略对象。
        list_business_values: value_sources 展开的业务值。
    返回:
        可扫描业务值集合与排除目录集合。
    """

    # 协议字面量不属于需要参数化的业务值。
    list_allowed_literals = dict_policy.get("allowed_protocol_literals", [])  # policy 协议白名单

    # 规范化协议白名单，供业务值过滤使用。
    set_protocol_literals = {str(item).strip() for item in list_allowed_literals if str(item).strip()}  # 规范化协议白名单

    # 从候选叶子中剔除协议和过短文本。
    set_business_values = {item for item in list_business_values if item not in set_protocol_literals and len(item) > 2}  # 可扫描业务值

    # 排除目录保持由 policy 声明。
    list_excluded_roots = dict_policy.get("excluded_roots", [])  # policy 排除目录

    # 将排除目录文本归一化为路径片段集合。
    set_excluded_roots = {str(item).strip() for item in list_excluded_roots if str(item).strip()}  # 规范化排除目录

    # 返回两类过滤结果供路径展开复用。
    return set_business_values, set_excluded_roots

# 从 policy 读取默认扫描根和消费扩展名。
def _policy_scan_inputs(
    dict_policy: dict[str, object],
    list_target_roots: list[Path] | None,
    path_skill_root: Path,
) -> tuple[list[Path], set[str]]:
    """返回请求扫描根和消费扩展名。

    参数:
        dict_policy: 参数化策略对象。
        list_target_roots: 调用方可选的窄扫描根。
        path_skill_root: 技能侧受管根。
    返回:
        请求扫描根列表与扩展名集合。
    """

    # 显式目标优先于 policy 默认根。
    if list_target_roots:

        # 保留调用方声明的窄扫描顺序。
        list_requested_roots = list(list_target_roots)  # 显式请求根

    # 没有显式根时从 policy scan_roots 绑定技能根。
    else:

        # 默认根从 policy scan_roots 绑定到技能根。
        list_requested_roots = [path_skill_root / str(item) for item in dict_policy.get("scan_roots", [])]  # 将 policy scan_roots 绑定为默认扫描输入

    # 消费表面扩展名由 policy 统一声明。
    list_surface_extensions = [  # 消费表面扩展名来源
        extension  # 当前表面扩展名
        for dict_surface in dict_policy.get("consumer_surfaces", {}).values()  # 遍历消费表面
        if isinstance(dict_surface, dict)  # 只读取对象表面
        for extension in dict_surface.get("extensions", [])  # 遍历表面扩展名
    ]  # 完成扩展名来源收集

    # 扫描比较使用大小写归一化扩展名。
    set_consumer_extensions = {str(extension).casefold() for extension in list_surface_extensions}  # 消费扩展名集合

    # 返回请求根和扩展名边界。
    return list_requested_roots, set_consumer_extensions

# 读取 parameterization policy 的内容摘要。
def _parameterization_policy_sha256(dict_binding: dict[str, object]) -> str:
    """返回 policy role 的当前内容摘要。

    参数:
        dict_binding: 已校验的 runtime manifest binding。
    返回:
        parameterization policy 的内容摘要。
    异常:
        ValueError 表示 manifest 缺少对应 role。
    """

    # 按 manifest role 名称查找唯一 policy 记录。
    for obj_role in dict_binding["roles"].values():

        # 只接受结构完整且 role 名称匹配的记录。
        if isinstance(obj_role, dict) and obj_role.get("name") == "parameterization_policy":

            # 返回当前 role 的内容摘要。
            return str(obj_role["content_sha256"])

    # 缺少摘要时不能生成可追溯扫描收据。
    raise ValueError("> ERR: [Python] parameterization policy role is missing")

# 对产品 Python 根执行参数化扫描。
def check_parameterization(
    path_project_root: Path,
    list_target_roots: list[Path] | None = None,
    path_manifest: Path | None = None,
) -> dict[str, object]:
    """检查配置业务值是否被写入产品 Python。

    参数：path_project_root 为项目根，list_target_roots 为可选扫描根。
    参数：path_manifest 为可选 runtime manifest 覆盖路径。
    返回：包含命中、扫描文件和合同摘要的机器映射。
    """

    # 技能根从当前项目的标准目录解析，避免安装绝对路径。
    path_skill_root = path_project_root / "skills" / "agents-md-generator"  # 当前技能可信根

    # 两类根统一解析为绝对边界。
    path_project_root_resolved = path_project_root.resolve()  # 当前项目绝对根

    # 后续扫描只使用解析后的技能根。
    path_skill_root_resolved = path_skill_root.resolve()  # 当前 Skill 绝对根

    # 运行时导入共享合同 loader，避免模块级导入副作用。
    tuple_contract_loaders = _load_runtime_contract_loaders()  # 共享合同 loader 元组

    # 拆出 JSON role loader，供 policy role 读取使用。
    func_load_json_role = tuple_contract_loaders[0]  # 读取参数化 role 的共享函数

    # 拆出 runtime manifest loader，供根和摘要绑定使用。
    func_load_runtime_manifest = tuple_contract_loaders[1]  # 读取根和摘要绑定的共享函数

    # 解析 runtime manifest，获得当前合同 hash。
    dict_binding = func_load_runtime_manifest(path_project_root, path_skill_root, path_manifest)  # 已校验的运行时 manifest 绑定

    # 读取参数化策略和所有业务值来源。
    dict_policy = func_load_json_role(dict_binding, "parameterization_policy")  # 参数化策略对象

    # 展开 policy value_sources 叶子文本。
    list_business_values = _collect_policy_business_values(dict_policy, dict_binding, func_load_json_role)  # policy 业务值叶子

    # 从 policy 候选中构造业务值和排除目录过滤器。
    tuple_scan_values = _policy_scan_values(dict_policy, list_business_values)  # 扫描过滤集合元组

    # 拆出可扫描业务值集合。
    set_business_values = tuple_scan_values[0]  # policy 叶子过滤后的业务值

    # 拆出排除目录集合。
    set_excluded_roots = tuple_scan_values[1]  # policy 声明的排除目录

    # 默认扫描范围由 scan_roots 和 consumer_surfaces 共同声明。
    tuple_scan_inputs = _policy_scan_inputs(dict_policy, list_target_roots, path_skill_root_resolved)  # 请求根与扩展名元组

    # 拆出请求扫描根列表。
    list_requested_roots = tuple_scan_inputs[0]  # 请求扫描根

    # 拆出消费扩展名集合。
    set_consumer_extensions = tuple_scan_inputs[1]  # 当前 policy 表面归一化扩展名集合

    # 将 project/skill base 的表面根解析到对应受管根。
    _append_consumer_surface_roots(
        dict_policy,
        list_requested_roots,
        path_skill_root_resolved,
        path_project_root_resolved,
        bool(list_target_roots),
    )

    # 收敛请求根并展开策略允许的消费文件。
    list_roots = _resolve_requested_roots(list_requested_roots, path_project_root_resolved, path_skill_root_resolved)  # 受管扫描根

    # 从受管扫描根收集策略允许的消费文件。
    list_files = _collect_parameterization_files(  # 消费文件收集结果
        list_roots,  # 递归展开的已收敛根
        set_consumer_extensions,  # 递归文件扩展名筛选
        path_project_root_resolved,  # 递归路径的项目边界
        set_excluded_roots,  # 递归路径排除目录
    )  # 完成消费文件收集

    # 委托独立 helper 扫描目标文件并生成脱敏命中证据。
    list_hits = _scan_parameterization_files(list_files, set_business_values, path_project_root_resolved)  # 所有目标文件的命中

    # 读取参数化 role 的当前内容摘要。
    str_policy_sha256 = _parameterization_policy_sha256(dict_binding)  # policy 内容摘要

    # 返回稳定 JSON 载荷，调用方再决定是否阻断。
    return {
        "ok": not list_hits,
        "errors": list_hits,
        "checked_files": [str(path_file) for path_file in list_files],
        "runtime_manifest_sha256": dict_binding["manifest_sha256"],
        "manifest_sha256": dict_binding["manifest_sha256"],
        "parameterization_policy_sha256": str_policy_sha256,
    }

# 保留测试和 registry 使用的验证语义名称。
def validate_parameterization(
    path_project_root: Path,
    list_target_roots: list[Path] | None = None,
    path_manifest: Path | None = None,
) -> dict[str, object]:
    """调用 check_parameterization 并返回同一机器合同。

    参数：path_project_root 为项目根；list_target_roots 为可选扫描根；path_manifest 为可选 manifest。
    返回：与 check_parameterization 相同的结构化扫描报告。
    """

    # 两个入口保持完全相同的扫描和错误语义。
    return check_parameterization(path_project_root, list_target_roots, path_manifest)
