"""提供项目事实采集所需的源码、脚本布局和作用域治理职责。"""

# 代码注释策略校验委托给统一源码治理配置模块。
def validate_code_comment_policy_data(comment_policy: dict[str, Any], *, require_explicit: bool = False) -> list[str]:
    """验证代码注释策略结构和显式字段要求。

    Args:
        comment_policy: 待验证的代码注释策略。
        require_explicit: 是否要求策略显式声明所有必需字段。

    Returns:
        策略合同错误列表。
    """

    # 统一模块维护策略 schema，当前包装器保持既有导出接口。
    return source_governance_config.validate_code_comment_policy_data(comment_policy, require_explicit=require_explicit)

# 全局规则覆盖校验保持项目事实模块的兼容导出。
def validate_global_rule_overrides_data(data: dict[str, Any]) -> list[str]:
    """验证全局规则覆盖配置。

    Args:
        data: 待验证的规则覆盖数据。

    Returns:
        配置合同错误列表。
    """

    # 实际 schema 校验由配置所有者执行。
    return source_governance_config.validate_global_rule_overrides_data(data)

# 规则覆盖读取委托给共享配置实现。
def load_global_rule_overrides(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """读取项目的全局规则覆盖配置。

    Args:
        root: 项目根目录。
        profile: 可选项目 profile。

    Returns:
        包含配置数据和来源证据的读取结果。
    """

    # 保留公开入口，避免调用方依赖内部模块路径。
    return source_governance_config.load_global_rule_overrides(root, profile)

# 覆盖文件创建同样复用统一配置所有者。
def ensure_global_rule_overrides_file(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """确保项目具有可用的全局规则覆盖文件。

    Args:
        root: 项目根目录。
        profile: 可选项目 profile。

    Returns:
        覆盖文件状态及其规范化数据。
    """

    # 共享实现负责默认值、写入和合同校验。
    return source_governance_config.ensure_global_rule_overrides_file(root, profile)

# 实现约束解析保持与项目 profile 事实采集入口相邻。
def implementation_constraints_from_profile(profile: dict[str, Any] | None, root: Path | None = None) -> dict[str, Any]:
    """从项目 profile 和规则覆盖中解析实现约束。

    Args:
        profile: 可选项目 profile。
        root: 可选项目根目录。

    Returns:
        规范化实现约束映射。
    """

    # 配置模块是约束默认值和覆盖合并的唯一来源。
    return source_governance_config.implementation_constraints_from_profile(profile, root)

# 手写源码扫描排除生成物、依赖目录和配置声明的根目录。
def iter_handwritten_code_files(root: Path, constraints: dict[str, Any]) -> list[Path]:
    """枚举受源码尺寸治理约束的手写代码文件。

    Args:
        root: 项目根目录。
        constraints: 包含扩展名和排除根目录的实现约束。

    Returns:
        按路径排序的手写代码文件列表。
    """

    # 扩展名统一为小写，保证 Windows 与 Linux 扫描结果一致。
    set_allowed_extensions = {
        str(item).lower()  # 配置声明的单个源码扩展名
        for item in constraints.get("size_limit_extensions", [])  # 逐项规范配置扩展名
    }  # 参与尺寸治理的源码扩展名

    # 排除根目录按项目相对路径首段匹配。
    set_excluded_roots = {
        str(item).strip("/\\")  # 配置声明的单个排除根目录
        for item in constraints.get("size_limit_exclude_roots", [])  # 逐项规范排除根目录
    }  # 不参与手写源码治理的根目录

    # 命中文件在遍历完成后统一排序。
    list_files: list[Path] = []  # 手写源码候选文件

    # 递归扫描后依次排除目录、生成物和非目标扩展名。
    for path_candidate in root.rglob("*"):

        # 目录不属于源码文件候选。
        if not path_candidate.is_file():

            # 继续检查下一文件系统条目。
            continue

        # 相对路径分段用于根目录和跳过目录判断。
        tuple_relative_parts = path_candidate.relative_to(root).parts  # 候选文件相对路径分段

        # 配置排除的顶层目录不进入后续治理。
        if tuple_relative_parts and tuple_relative_parts[0] in set_excluded_roots:

            # 排除整棵受配置控制的目录树。
            continue

        # 通用依赖与缓存目录在任意层级都跳过。
        if any(str_part in SKIP_DIRS for str_part in tuple_relative_parts):

            # 排除生成物、依赖和版本控制内部目录。
            continue

        # 只有合同声明的源码扩展名进入结果。
        if path_candidate.suffix.lower() in set_allowed_extensions:

            # 保存真实文件路径供尺寸门禁读取。
            list_files.append(path_candidate)

    # 稳定排序避免文件系统枚举次序影响诊断。
    return sorted(list_files)

# GUI 启动脚本例外来自受管清单，不在扫描逻辑中硬编码。
def script_governance_exceptions(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """读取并规范化脚本治理例外清单。

    Args:
        root: 项目根目录。
        profile: 可选项目 profile。

    Returns:
        例外清单路径及 GUI 启动脚本相对路径。
    """

    # 规则覆盖决定例外清单相对路径。
    dict_overrides = load_global_rule_overrides(root, profile)["data"]  # 全局规则覆盖数据

    # 缺省路径与项目生成的配置合同保持一致。
    str_manifest_path = str(  # GUI 例外清单配置值
        dict_overrides["tool_script_layout"].get(  # 从脚本布局规则读取清单路径
            "gui_exception_manifest",  # GUI 例外清单字段名
            ".agents/script-governance-exceptions.json",  # 缺省 GUI 例外清单路径
        )
    ).strip()  # GUI 例外清单相对路径

    # 绝对路径用于读取项目内的 GUI 例外声明。
    path_manifest = root / str_manifest_path  # GUI 例外清单绝对路径

    # 缺失清单等价于没有显式例外。
    dict_manifest = read_json(path_manifest) if path_manifest.exists() else {}  # 例外清单数据

    # 非列表旧格式输入按空例外处理。
    list_gui_startup = (
        dict_manifest.get("gui_startup", [])  # 清单中的 GUI 启动脚本列表
        if isinstance(dict_manifest.get("gui_startup", []), list)  # 仅接受列表格式
        else []  # 非列表配置降级为空条目
    )  # GUI 启动脚本原始条目

    # 输出统一使用正斜杠并移除空条目。
    list_normalized = sorted(  # 规范化后的 GUI 启动脚本路径
        str(item).strip().replace("\\", "/")  # 单个例外路径统一分隔符
        for item in list_gui_startup  # 逐项处理 GUI 启动脚本
        if str(item).strip()  # 丢弃空白例外条目
    )  # 规范化 GUI 启动脚本路径

    # 路径证据在清单缺失时仍保持项目相对形式。
    return {
        "path": rel(path_manifest, root) if path_manifest.exists() else path_manifest.relative_to(root).as_posix(),
        "gui_startup": list_normalized,
    }

# 分解计划路径由规则覆盖中的根目录和目标源码路径共同派生。
def decomposition_plan_path(root: Path, relative_file: str, profile: dict[str, Any] | None = None) -> Path:
    """计算目标源码文件对应的分解计划路径。

    Args:
        root: 项目根目录。
        relative_file: 目标源码的项目相对路径。
        profile: 可选项目 profile。

    Returns:
        分解计划 Markdown 的绝对路径。
    """

    # 规则覆盖提供项目允许使用的分解计划根目录。
    dict_overrides = load_global_rule_overrides(root, profile)["data"]  # 分解计划规则覆盖数据

    # 首尾分隔符清理避免绝对路径覆盖项目根目录。
    str_plan_root = str(  # 分解计划根目录配置值
        dict_overrides["source_file_limits"].get(  # 从尺寸规则读取计划根目录
            "decomposition_plan_root",  # 分解计划根目录字段名
            "docs/development/decomposition-plans",  # 缺省分解计划目录
        )
    ).strip().strip("/\\")  # 分解计划项目相对根目录

    # Windows 盘符冒号不能进入计划文件的相对路径。
    str_sanitized_file = relative_file.replace("\\", "/").replace(":", "")  # 安全目标文件标识

    # 目标源码路径直接映射为同名 Markdown 计划。
    return root / str_plan_root / f"{str_sanitized_file}.md"

# 受管脚本根目录保持去重并只返回当前实际存在的目录。
def managed_script_roots(root: Path, profile: dict[str, Any] | None = None) -> list[Path]:
    """发现项目中受脚本布局治理的根目录。

    Args:
        root: 项目根目录。
        profile: 保留用于兼容公开调用合同的可选 profile。

    Returns:
        去重后的现有脚本根目录列表。
    """

    # 当前目录合同只治理项目根下的 scripts 目录。
    path_scripts = root / "scripts"  # 标准脚本根目录候选

    # 缺失目录时返回空列表，避免声明不存在的治理范围。
    if not path_scripts.is_dir():

        # 空列表表示当前项目没有受管脚本根目录。
        return []

    # 单一标准根目录无需额外去重状态。
    return [path_scripts]

# 单个脚本路径检查返回布局诊断或可计入变体组的结构化成员。
def script_layout_path_result(
    root: Path,
    path_scripts_root: Path,
    path_script: Path,
    str_required_root: str,
    dict_families: dict[str, Any],
    dict_extension_to_family: dict[str, str],
) -> dict[str, Any]:
    """检查一个脚本文件的家族、扩展名和层级。

    Args:
        root: 项目根目录。
        path_scripts_root: 当前受管脚本根目录。
        path_script: 待检查脚本文件。
        str_required_root: 规则要求的脚本根目录名称。
        dict_families: 脚本家族与扩展名映射。
        dict_extension_to_family: 扩展名到家族的反向映射。

    Returns:
        包含可选违规文本、变体组键和家族名称的结果。
    """

    # 项目相对路径用于全部用户可见诊断。
    str_relative_path = path_script.relative_to(root).as_posix()  # 脚本项目相对路径

    # 脚本根内的分段决定家族和功能层级。
    tuple_parts = path_script.relative_to(path_scripts_root).parts  # 脚本根内路径分段

    # 空分段不产生有效成员或诊断。
    if not tuple_parts:

        # 稳定空结果供扫描编排直接跳过。
        return {"violation": "", "triad_key": None, "family": ""}

    # 第一层必须是配置声明的脚本家族。
    str_family = tuple_parts[0]  # 当前脚本家族目录

    # 扩展名用于判断脚本是否落在正确的语言家族。
    str_suffix = path_script.suffix.lower()  # 当前脚本扩展名

    # 非家族目录中的已知脚本扩展名需要明确迁移诊断。
    if str_family not in dict_families:

        # 扩展名可推导文件应该进入的家族。
        str_expected_family = dict_extension_to_family.get(str_suffix, "")  # 扩展名对应家族

        # 未知扩展名不属于脚本布局治理范围。
        if not str_expected_family:

            # 不生成误导性的家族诊断。
            return {"violation": "", "triad_key": None, "family": ""}

        # 直接位于脚本根的文件给出完整目标布局。
        if len(tuple_parts) == 1:

            # 诊断同时说明允许家族、功能层、扩展名和实际散落路径。
            str_violation = (
                f"script layout requires {str_required_root}/{str_expected_family}/"
                f"<function>/<name>{str_suffix}: {str_relative_path}"
            )  # 根目录散落脚本诊断

        # 其他未知首层目录报告允许的家族集合。
        else:

            # 家族顺序沿用配置声明顺序。
            str_allowed = ", ".join(dict_families)  # 允许的脚本家族文本

            # 诊断文本向调用方解释散落脚本的合法迁移范围。
            str_violation = (
                f"unsupported script family under {str_required_root} "
                f"(allowed: {str_allowed}): {str_relative_path}"
            )  # 未支持家族诊断

        # 非法家族不能进入变体完整性统计。
        return {"violation": str_violation, "triad_key": None, "family": ""}

    # 合法家族的文件扩展名必须与配置严格一致。
    str_expected_extension = str(dict_families[str_family]).lower()  # 家族要求的扩展名

    # 扩展名漂移会导致脚本执行器路由错误。
    if str_suffix != str_expected_extension:

        # 空扩展名使用可读占位符呈现。
        str_actual_suffix = str_suffix or "<none>"  # 诊断使用的实际扩展名

        # 违规文本同时给出期望扩展名和实际脚本位置。
        str_violation = (
            f"script extension {str_actual_suffix} does not match family `{str_family}` "
            f"(expected {str_expected_extension}): {str_relative_path}"
        )  # 家族扩展名不匹配诊断

        # 扩展名错误文件不计入完整变体组。
        return {"violation": str_violation, "triad_key": None, "family": ""}

    # 家族、功能和文件名三层是最小合法布局。
    if len(tuple_parts) < 3:

        # 诊断展示缺失的功能层合同。
        str_violation = (
            f"script layout requires {str_required_root}/{str_family}/"
            f"<function>/<name>{str_expected_extension}: {str_relative_path}"
        )  # 层级不足诊断

        # 层级不足时无法建立稳定变体组键。
        return {"violation": str_violation, "triad_key": None, "family": ""}

    # 功能子路径允许多层目录，但排除家族和文件名。
    str_function_path = "/".join(tuple_parts[1:-1])  # 脚本功能路径

    # 变体键让不同语言目录中的同名功能脚本归为一组。
    tuple_triad_key = (str_function_path, path_script.stem)  # 变体组功能与名称键

    # 合法成员由调用方累计到对应变体组。
    return {"violation": "", "triad_key": tuple_triad_key, "family": str_family}

# 完整变体门禁比较每个功能脚本实际家族与配置家族集合。
def script_triad_gaps(
    dict_triad_members: dict[tuple[str, str], set[str]],
    dict_families: dict[str, Any],
    str_required_root: str,
) -> list[str]:
    """生成脚本变体组缺失家族诊断。

    Args:
        dict_triad_members: 变体组键到实际家族集合的映射。
        dict_families: 配置声明的全部脚本家族。
        str_required_root: 规则要求的脚本根目录名称。

    Returns:
        按变体组排序的缺失家族诊断列表。
    """

    # 所有变体组共享同一必需家族集合。
    set_required_families = set(dict_families)  # 必需脚本家族集合

    # 缺失诊断在遍历每个变体组时累积。
    list_gaps: list[str] = []  # 变体组缺失诊断

    # 排序保证不同文件系统得到相同诊断次序。
    for tuple_triad_key, set_present in sorted(dict_triad_members.items()):

        # 差集直接给出当前功能脚本缺少的家族。
        list_missing = sorted(set_required_families - set_present)  # 当前变体组缺失家族

        # 完整变体组不产生诊断。
        if not list_missing:

            # 继续检查下一功能脚本。
            continue

        # 键的两部分分别用于还原功能路径和脚本名称。
        str_function_path = tuple_triad_key[0]  # 变体组功能路径

        # 脚本名称用于构造可定位的缺失家族诊断。
        str_stem = tuple_triad_key[1]  # 变体组脚本名称

        # 单条诊断列出当前组的全部缺失家族。
        list_gaps.append(
            f"missing script family variants for {str_required_root}/<family>/"
            f"{str_function_path}/{str_stem}: {list_missing}"
        )

    # 返回完整变体缺口列表。
    return list_gaps

# 脚本布局事实覆盖家族目录、扩展名与完整变体组约束。
def script_layout_facts(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    """检查脚本家族布局并生成治理事实。

    Args:
        root: 项目根目录。
        profile: 可选项目 profile。

    Returns:
        GUI 例外、布局违规和脚本变体缺口。
    """

    # 实现约束是脚本布局配置的权威来源。
    dict_constraints = implementation_constraints_from_profile(profile, root)  # 项目实现约束

    # 非映射布局配置按空配置处理。
    dict_layout = (
        dict_constraints.get("script_layout", {})  # 实现约束中的脚本布局配置
        if isinstance(dict_constraints.get("script_layout", {}), dict)  # 仅接受映射格式
        else {}  # 非映射布局配置降级为空配置
    )  # 脚本布局配置

    # 家族映射决定目录名称与文件扩展名。
    dict_families = (
        dict_layout.get("families", {})  # 布局配置中的语言家族映射
        if isinstance(dict_layout.get("families", {}), dict)  # 仅接受家族映射
        else {}  # 非映射家族配置降级为空配置
    )  # 脚本家族配置

    # 空配置仍使用标准 scripts 根目录。
    str_required_root = str(dict_layout.get("required_root", "scripts")).strip("/\\") or "scripts"  # 必需脚本根名称

    # 显式例外决定哪些入口不参加通用脚本布局检查。
    dict_exceptions = script_governance_exceptions(root, profile)  # 脚本治理例外清单

    # 集合形式支持扫描期间常数时间的路径匹配。
    set_gui_exemptions = set(dict_exceptions["gui_startup"])  # GUI 启动脚本例外集合

    # 反向映射用于为散落脚本推导目标家族。
    dict_extension_to_family = {
        str(str_extension).lower(): str_family  # 单个扩展名对应的脚本家族
        for str_family, str_extension in dict_families.items()  # 逐项反转家族与扩展名
    }  # 扩展名到脚本家族映射

    # 变体成员表记录每个功能目前覆盖的脚本家族。
    dict_triad_members: dict[tuple[str, str], set[str]] = {}  # 变体组实际家族集合

    # 布局违规由所有受管脚本扫描结果共同累积。
    list_violations: list[str] = []  # 脚本布局违规

    # 每个受管根只在名称符合配置时参与扫描。
    for path_scripts_root in managed_script_roots(root, profile):

        # 支持项目根 scripts 以及嵌套但同名的配置根目录。
        bool_matches_root = (
            path_scripts_root.name == str_required_root  # 项目根的标准脚本目录
            or path_scripts_root.relative_to(root).as_posix().endswith(f"/{str_required_root}")  # 嵌套标准脚本目录
        )  # 当前目录是否匹配必需脚本根

        # 名称不符的候选根目录不属于当前布局合同。
        if not bool_matches_root:

            # 继续检查下一受管根目录。
            continue

        # 排序扫描保证违规与变体累计结果稳定。
        for path_script in sorted(path_scripts_root.rglob("*")):

            # 目录不参与脚本文件布局检查。
            if not path_script.is_file():

                # 继续处理下一条目。
                continue

            # 例外匹配使用项目相对正斜杠路径。
            str_relative_path = path_script.relative_to(root).as_posix()  # GUI 例外匹配路径

            # GUI 启动脚本按显式清单退出布局治理。
            if str_relative_path in set_gui_exemptions:

                # 例外文件不进入违规或变体统计。
                continue

            # 单文件 helper 统一生成违规或合法成员事实。
            dict_result = script_layout_path_result(  # 单个脚本的布局检查结果
                root,  # 项目根用于生成相对诊断路径
                path_scripts_root,  # 当前受管脚本根目录
                path_script,  # 当前待检查脚本文件
                str_required_root,  # 配置要求的标准脚本根名称
                dict_families,  # 允许的脚本家族与扩展名映射
                dict_extension_to_family,  # 扩展名到目标家族的反向索引
            )  # 当前脚本布局检查结果

            # 布局违规按扫描顺序直接累计。
            if dict_result["violation"]:

                # 单文件最多产生一条最具体诊断。
                list_violations.append(str(dict_result["violation"]))

            # 合法成员才具有变体组键。
            elif dict_result["triad_key"] is not None:

                # 类型来自 helper 的稳定内部合同。
                tuple_triad_key = dict_result["triad_key"]  # 当前脚本变体组键

                # 同一功能与名称下累计实际家族。
                dict_triad_members.setdefault(tuple_triad_key, set()).add(str(dict_result["family"]))

    # 配置可关闭完整变体组要求。
    list_gaps = (
        script_triad_gaps(dict_triad_members, dict_families, str_required_root)  # 完整变体组缺口
        if dict_layout.get("require_full_triad", True)  # 仅在配置要求时检查完整变体组
        else []  # 关闭完整变体组要求时不产生缺口
    )  # 脚本变体组缺口

    # 返回渲染与验证共同消费的稳定字段。
    return {
        "gui_script_exemptions": dict_exceptions["gui_startup"],
        "tool_script_layout_violations": list_violations,
        "script_triad_gaps": list_gaps,
    }

# 文档事实覆盖根目录指南和常见 ADR 目录。
def documentation_context(root: Path) -> dict[str, list[str]]:
    """收集项目文档和架构决策记录。

    Args:
        root: 项目根目录。

    Returns:
        去重排序后的 documentation 与 adrs 字段。
    """

    # 根目录常见指南按名称排序后检查。
    set_documentation_names = {
        "README.md",  # 项目入口说明
        "CONTRIBUTING.md",  # 贡献流程
        "SECURITY.md",  # 安全策略
        "ARCHITECTURE.md",  # 架构说明
    }  # 根目录文档候选名称

    # 文档列表只保留项目根目录真实存在的候选文件。
    list_documentation = [
        str_name  # 已存在的根文档名称
        for str_name in sorted(set_documentation_names)  # 按稳定顺序检查文档候选
        if (root / str_name).exists()  # 过滤缺失的文档候选
    ]  # 已存在的根目录文档

    # 两种常见文档目录只读取第一层 Markdown。
    for str_docs_dir in ("docs", "Documentation"):

        # 当前候选目录相对项目根解析。
        path_docs = root / str_docs_dir  # 当前文档目录

        # 缺失目录不贡献文档事实。
        if not path_docs.exists():

            # 继续检查下一种目录命名。
            continue

        # 每个目录限制十二个文件，避免上下文无限增长。
        list_documentation.extend(
            rel(path_item, root)
            for path_item in sorted(path_docs.glob("*.md"))[:12]
        )

    # ADR 目录覆盖常见单复数和架构子目录约定。
    list_adr_dirs = [
        "adr",  # 根目录单数形式
        "adrs",  # 根目录复数形式
        "docs/adr",  # 文档单数形式
        "docs/adrs",  # 文档复数形式
        "docs/decisions",  # 决策记录目录
        "architecture/decisions",  # 架构决策目录
    ]  # ADR 目录候选

    # ADR 结果跨多个候选目录累积后统一去重。
    list_adrs: list[str] = []  # 已发现 ADR 文件

    # 每个候选目录独立限制文件数量。
    for str_adr_dir in list_adr_dirs:

        # 当前 ADR 目录相对项目根解析。
        path_adr_dir = root / str_adr_dir  # 当前 ADR 目录

        # 缺失目录不参与文件枚举。
        if not path_adr_dir.exists():

            # 继续检查下一 ADR 约定。
            continue

        # 项目相对路径供生成文档直接引用。
        list_adrs.extend(
            rel(path_item, root)
            for path_item in sorted(path_adr_dir.glob("*.md"))[:12]
        )

    # 去重排序保证跨平台输出稳定。
    return {
        "documentation": sorted(dict.fromkeys(list_documentation)),
        "adrs": sorted(dict.fromkeys(list_adrs)),
    }

# 工具事实覆盖执行入口、质量配置、平台文件和编辑器设置。
def tooling_context(root: Path) -> dict[str, list[str]]:
    """收集项目工具链与工作区配置事实。

    Args:
        root: 项目根目录。

    Returns:
        工具、质量、平台、IDE 和工作区设置字段。
    """

    # 根目录构建工具和 scripts 文件共同组成 utilities。
    list_utilities = [
        str_name  # 已存在的根构建工具名称
        for str_name in ("Makefile", "justfile")  # 逐项检查根构建工具
        if (root / str_name).exists()  # 过滤缺失的构建工具
    ]  # 已存在的根构建工具

    # 标准脚本目录用于补充项目工具入口事实。
    path_scripts = root / "scripts"  # 标准脚本目录

    # 根 scripts 下的普通文件可作为项目工具入口。
    if path_scripts.exists():

        # 子目录由脚本布局事实单独治理。
        list_utilities.extend(
            rel(path_item, root)
            for path_item in sorted(path_scripts.iterdir())
            if path_item.is_file()
        )

    # 各配置类别保持声明式候选列表。
    list_quality_configs = existing_paths(  # 已存在的质量工具配置
        root,  # 项目根用于解析质量配置候选
        [
            ".pre-commit-config.yaml", ".pre-commit-config.yml", "ruff.toml", ".ruff.toml",  # Python 质量配置
            "mypy.ini", "pytest.ini", "tsconfig.json", "eslint.config.js", "eslint.config.mjs",  # 类型测试与前端质量配置
            ".eslintrc", ".eslintrc.json", ".prettierrc", ".prettierrc.json", "phpstan.neon",  # 前端与 PHP 质量配置
        ],
    )  # 质量工具配置

    # 平台文件刻画项目运行与开发环境。
    list_platform_files = existing_paths(  # 已存在的平台与环境配置
        root,  # 项目根用于解析平台文件候选
        [
            "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml",  # 容器平台配置
            ".devcontainer/devcontainer.json", ".tool-versions", ".python-version", ".nvmrc",  # 开发容器与运行时版本配置
            "mise.toml", ".mise.toml", "flake.nix", "shell.nix", "Taskfile.yml", "Taskfile.yaml",  # 环境管理与任务运行配置
        ],
    )  # 平台和环境配置

    # IDE 文件用于识别项目采用的编辑器工作流。
    list_ide_settings = existing_paths(  # 已存在的编辑器与 IDE 配置
        root,  # 项目根用于解析 IDE 配置候选
        [
            ".editorconfig", ".vscode/settings.json", ".vscode/extensions.json",  # 编辑器与 VS Code 配置
            ".idea/codeStyles/Project.xml", ".idea/inspectionProfiles/Project_Default.xml",  # JetBrains 代码样式与检查配置
        ],
    )  # 编辑器与 IDE 设置

    # 工作区设置由专用发现器处理本地配置边界。
    list_workspace_settings = discover_workspace_settings(root)  # 工作区本地设置文件

    # 每类结果独立去重排序。
    return {
        "utilities": sorted(dict.fromkeys(list_utilities)),
        "quality_configs": sorted(dict.fromkeys(list_quality_configs)),
        "platform_files": sorted(dict.fromkeys(list_platform_files)),
        "ide_settings": sorted(dict.fromkeys(list_ide_settings)),
        "workspace_settings": sorted(dict.fromkeys(list_workspace_settings)),
    }

# 治理资料覆盖架构、依赖、钩子、GitHub、目录覆盖和参考项目。
def repository_governance_context(root: Path) -> dict[str, list[str]]:
    """收集仓库治理配置和覆盖候选。

    Args:
        root: 项目根目录。

    Returns:
        仓库治理相关的分类路径字段。
    """

    # 静态候选通过共享 existing_paths 统一检查。
    list_architecture_files = existing_paths(  # 已存在的架构治理文件
        root,  # 项目根用于解析架构文件候选
        [
            "CODEOWNERS", ".github/CODEOWNERS", "ARCHITECTURE.md",  # 代码所有权与架构入口
            "docs/architecture.md", "docs/ARCHITECTURE.md", "docs/adr/index.md",  # 文档树中的架构入口
        ],
    )  # 架构治理文件

    # 依赖更新配置反映自动化维护工具的启用情况。
    list_dependency_configs = existing_paths(  # 已存在的依赖更新配置
        root,  # 项目根用于解析依赖配置候选
        [
            ".github/dependabot.yml", ".github/dependabot.yaml", "renovate.json",  # 常见依赖更新机器人配置
            ".renovaterc", ".renovaterc.json", "dependabot.yml", "dependabot.yaml",  # 根目录依赖更新配置
        ],
    )  # 依赖更新配置

    # 钩子配置用于识别提交前和推送前治理入口。
    list_hook_candidates = [
        "lefthook.yml", ".lefthook.yml", "captainhook.json",  # 通用钩子管理器配置
        ".pre-commit-config.yaml", ".pre-commit-config.yml",  # pre-commit 钩子配置
        "Build/hooks/pre-push", ".githooks/pre-commit", ".githooks/pre-push",  # 项目自定义 Git 钩子
    ]  # 常见仓库钩子配置候选

    # 解析后的钩子列表仅保留现有路径，并供后续补充 Husky 事实。
    list_hook_configs = existing_paths(  # 已存在的仓库钩子配置
        root,  # 项目根用于解析钩子候选
        list_hook_candidates,  # 待验证的钩子配置路径
    )  # 提交与推送钩子配置

    # Husky 目录作为整体治理资产记录。
    if (root / ".husky").is_dir():

        # 目录后缀斜杠区分文件路径。
        list_hook_configs.append(".husky/")

    # GitHub 设置用于识别平台侧的仓库治理表面。
    list_github_settings = existing_paths(  # 已存在的 GitHub 仓库设置
        root,  # 项目根用于解析 GitHub 设置候选
        [
            ".github/CODEOWNERS", ".github/copilot-instructions.md",  # 所有权与代理说明
            ".github/dependabot.yml", ".github/dependabot.yaml", ".github/renovate.json",  # GitHub 依赖治理配置
        ],
    )  # GitHub 仓库设置文件

    # Rulesets 目录中的 JSON 文件补充动态仓库规则事实。
    path_rulesets = root / ".github" / "rulesets"  # GitHub 规则集目录

    # Ruleset JSON 作为动态 GitHub 治理事实。
    if path_rulesets.exists():

        # 限制数量避免大型仓库上下文膨胀。
        list_github_settings.extend(
            rel(path_item, root)
            for path_item in sorted(path_rulesets.glob("*.json"))[:12]
        )

    # 缺少局部 AGENTS.md 的常见目录成为覆盖候选。
    list_directory_coverage = [
        str_name  # 缺少局部规则文件的目录名称
        for str_name in [  # 逐项检查常见局部治理目录
            "src", "app", "lib", "tests", "test", "docs", "Documentation", "scripts",  # 主要源码测试文档目录
            "tools", "cmd", "internal", "pkg", ".github/workflows",  # 工具与平台自动化目录
        ]
        if (root / str_name).is_dir() and not (root / str_name / "AGENTS.md").exists()  # 仅保留缺少局部规则的现有目录
    ]  # 局部规则覆盖候选目录

    # 参考项目结果跨常见根目录累积。
    list_reference_projects: list[str] = []  # 参考项目目录

    # 三种常见参考项目根目录均支持多个子项目。
    for str_base_name in ("reference-projects", "references/projects", "examples/reference-projects"):

        # 当前参考项目根目录。
        path_base = root / str_base_name  # 参考项目根目录候选

        # 非目录候选不参与子项目枚举。
        if not path_base.is_dir():

            # 继续检查下一目录约定。
            continue

        # 仅子目录构成参考项目。
        list_reference_projects.extend(
            rel(path_child, root)
            for path_child in sorted(path_base.iterdir())
            if path_child.is_dir()
        )

    # 已存在的代理配置用于识别多工具治理表面。
    list_agent_configs = [
        str_name  # 已存在的代理配置路径
        for str_name in [  # 逐项检查常见代理配置
            "AGENTS.md", "CLAUDE.md", "GEMINI.md", ".github/copilot-instructions.md",  # 主流代理规则文件
            ".cursorrules", ".aider.conf.yml", ".aider.conf.yaml",  # 编辑器代理配置文件
        ]
        if (root / str_name).exists()  # 过滤缺失的代理配置
    ]  # 已存在的代理规则配置

    # 所有分类字段去重并稳定排序。
    return {
        "architecture_files": sorted(dict.fromkeys(list_architecture_files)),
        "dependency_configs": sorted(dict.fromkeys(list_dependency_configs)),
        "hook_configs": sorted(dict.fromkeys(list_hook_configs)),
        "github_settings": sorted(dict.fromkeys(list_github_settings)),
        "directory_coverage_candidates": sorted(dict.fromkeys(list_directory_coverage)),
        "reference_projects": sorted(dict.fromkeys(list_reference_projects)),
        "agent_configs": sorted(dict.fromkeys(list_agent_configs)),
    }

# 黄金样例从常见源码与测试模式中按上限选取。
def golden_sample_paths(root: Path, limit: int = 8) -> list[str]:
    """选择用于推断项目风格的代表性文件。

    Args:
        root: 项目根目录。
        limit: 最大样例数量。

    Returns:
        按模式优先级选取的项目相对文件路径。
    """

    # 模式顺序优先测试，再选择主要源码与示例。
    list_patterns = [
        "tests/test_*.*", "tests/*_test.*", "src/*.*", "app/*.*",  # 优先测试与主要源码
        "lib/*.*", "examples/*.*", "samples/*.*",  # 次选库文件与示例
    ]  # 黄金样例文件模式

    # 黄金样例按模式优先级累积并受数量上限约束。
    list_samples: list[str] = []  # 已选黄金样例

    # 达到上限后仍允许外层自然结束，保持流程简单。
    for str_pattern in list_patterns:

        # 单模式内部按文件名排序。
        for path_candidate in sorted(root.glob(str_pattern)):

            # 只收集普通文件且不超过调用方上限。
            if path_candidate.is_file() and len(list_samples) < limit:

                # 保存项目相对路径供后续审阅。
                list_samples.append(rel(path_candidate, root))

    # 模式可能重叠，因此返回前执行稳定去重。
    return list(dict.fromkeys(list_samples))[:limit]

# 项目上下文汇总文档、工具、平台、治理和样例事实。
def extract_context(root: Path) -> dict[str, Any]:
    """收集 AGENTS 生成所需的项目治理上下文。

    Args:
        root: 项目根目录。

    Returns:
        规范化且去重的项目上下文字段映射。
    """

    # Profile 连接脚本治理和实现约束解析。
    dict_profile = project_profile(root)  # 脚本治理使用的项目配置

    # 文档事实构成渲染上下文的说明性部分。
    dict_documentation = documentation_context(root)  # 文档与 ADR 事实

    # 工具链事实描述项目采用的质量与开发入口。
    dict_tooling = tooling_context(root)  # 工具链与工作区事实

    # 仓库事实描述平台规则、钩子和代理配置。
    dict_repository = repository_governance_context(root)  # 仓库治理事实

    # 脚本治理事实补充布局违规和完整变体组状态。
    dict_script_governance = script_layout_facts(root, dict_profile)  # 脚本布局治理事实

    # 实现约束为最终上下文提供尺寸和目录合同。
    dict_constraints = implementation_constraints_from_profile(dict_profile, root)  # 实现约束

    # 规则覆盖结果保留来源和解析状态供渲染层追踪。
    dict_overrides = load_global_rule_overrides(root, dict_profile)  # 全局规则覆盖结果

    # 合并分类 helper 与动态治理字段，保持原有 CLI 合同。
    return {
        **dict_documentation,
        **dict_tooling,
        **dict_repository,
        "golden_samples": golden_sample_paths(root),
        "ci_rules": workflow_runs(root),
        "implementation_constraints": dict_constraints,
        "global_rule_overrides_path": dict_overrides["path"].relative_to(root).as_posix(),
        "global_rule_overrides_exists": dict_overrides["exists"],
        "global_rule_overrides_valid": not dict_overrides["errors"],
        "global_rule_overrides_errors": list(dict_overrides["errors"]),
        "global_rule_overrides": dict_overrides["data"],
        "gui_script_exemptions": dict_script_governance["gui_script_exemptions"],
        "tool_script_layout_violations": dict_script_governance["tool_script_layout_violations"],
        "script_triad_gaps": dict_script_governance["script_triad_gaps"],
    }

# 作用域建议只包含实际存在的常见目录和工作区 package。
def detect_scopes(root: Path) -> dict[str, Any]:
    """发现适合设置局部 AGENTS.md 的项目作用域。

    Args:
        root: 项目根目录。

    Returns:
        作用域路径、用途和建议 AGENTS.md 路径列表。
    """

    # 常见目录用途形成稳定的作用域建议顺序。
    dict_candidate_purposes = {  # 项目目录与局部规则用途映射
        "src": "source code patterns",  # 主源码目录
        "tests": "test conventions and fixtures",  # 复数测试目录
        "test": "test conventions and fixtures",  # 单数测试目录
        "docs": "documentation standards",  # 文档目录
        "frontend": "frontend stack and UI conventions",  # 前端模块目录
        "web": "frontend stack and UI conventions",  # Web 模块目录
        "backend": "backend stack and service conventions",  # 后端模块目录
        "internal": "internal module boundaries",  # 内部模块目录
        "cmd": "CLI entry points and flags",  # 命令行入口目录
        "scripts": "automation script conventions",  # 自动化脚本目录
        ".github/workflows": "CI workflow rules",  # CI 工作流目录
    }

    # 结果只包含当前真实存在的目录。
    list_scopes: list[dict[str, str]] = []  # 局部 AGENTS 作用域建议

    # 标准目录按声明顺序检查，保持输出稳定。
    for str_relative_path, str_purpose in dict_candidate_purposes.items():

        # 候选路径相对项目根解析。
        path_candidate = root / str_relative_path  # 当前标准作用域目录

        # 文件或缺失路径不构成目录作用域。
        if not path_candidate.is_dir():

            # 继续检查下一标准目录。
            continue

        # 每个作用域附带建议的局部规则文件位置。
        list_scopes.append(
            {
                "path": str_relative_path,  # 作用域项目相对路径
                "purpose": str_purpose,  # 建议承载的规则类别
                "agents_file": f"{str_relative_path}/AGENTS.md",  # 局部规则文件
            }
        )

    # 工作区 package 目录按子目录动态扩展作用域。
    path_packages = root / "packages"  # 工作区 package 根目录

    # 缺失 packages 时无需执行子目录枚举。
    if path_packages.is_dir():

        # 排序保证跨文件系统的 package 建议顺序一致。
        for path_child in sorted(path_packages.iterdir()):

            # package 根下的普通文件不构成作用域。
            if not path_child.is_dir():

                # 继续检查下一个 package 条目。
                continue

            # 相对路径同时用于作用域和局部规则文件。
            str_package_path = path_child.relative_to(root).as_posix()  # Package 相对路径

            # Package 使用统一的工作区专属规则用途。
            list_scopes.append(
                {
                    "path": str_package_path,  # Package 作用域路径
                    "purpose": "workspace package-specific rules",  # Package 规则用途
                    "agents_file": f"{str_package_path}/AGENTS.md",  # Package 规则文件
                }
            )

    # 包装字段保持 detect_scopes CLI 的稳定 JSON 合同。
    return {"scopes": list_scopes}
