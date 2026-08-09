"""语言技能路由默认文案与校验辅助。"""

# 延迟注解解析避免运行时解析仅用于类型检查的参数。
from __future__ import annotations

# 标准库提供环境变量读取和跨平台路径处理。
import os
from pathlib import Path

# Python readable 技能名同时用于安装发现和路由文案校验。
READABLE_PYTHON_SKILL = "readable-python-generator"  # Python owner 技能目录名

# 脚本 readable 技能名与 Python owner 独立发现。
READABLE_SCRIPT_SKILL = "readable-script-generator"  # 脚本 owner 技能目录名

# 安装探测只接受标准技能目录的真实存在性证据。
def readable_skill_is_installed(skill_name: str) -> bool:
    """检查标准 Codex 技能目录中是否存在指定 readable 技能。

    参数:
        skill_name: 待探测的技能目录名。

    返回:
        标准技能目录存在时返回 True，否则返回 False。
    """

    # CODEX_HOME 优先于用户主目录，且不复用仅面向生成器自身的安装目录覆盖变量。
    str_codex_home = os.environ.get("CODEX_HOME", "").strip()  # 显式 Codex 主目录

    # 未配置 CODEX_HOME 时回退到标准用户级 Codex 目录。
    path_codex_home = (  # 实际参与技能发现的 Codex 主目录
        Path(str_codex_home).expanduser()  # 显式主目录路径
        if str_codex_home  # 显式主目录优先
        else Path.home() / ".codex"  # 标准用户级回退目录
    )

    # 目录存在即构成当前渲染进程可加载该技能的安装证据。
    return (path_codex_home / "skills" / skill_name).is_dir()

# 路由构造必须分别处理两个 owner 的四种安装组合。
def build_language_skill_routes(
    python_installed: bool,
    script_installed: bool,
) -> tuple[str, str, str]:
    """按两个 owner 技能的独立安装状态构造共同门禁与语言路由。

    参数:
        python_installed: Python readable 技能是否已安装。
        script_installed: 脚本 readable 技能是否已安装。

    返回:
        共同门禁、Python 路由与脚本路由组成的三元组。
    """

    # 两个 owner 都可用时，共同门禁集中声明双技能前置约束。
    if python_installed and script_installed:

        # 双技能文案只在 shared 字段保存一次，语言路由不再复制全文。
        str_shared_route = (  # 双技能共同前置门禁
            "创建或修改 Python、bat/cmd、shell/bash、PowerShell、Tcl 代码时，"
            "必须先思考并同时加载 `readable-python-generator` 与 `readable-script-generator`；"
            "两个技能组成当前可执行的语言门禁；"
            "两个技能的门禁必须在过程中满足，全部通过后才能继续，不得事后补做。"
        )

    # 任一 owner 不可用时，共同门禁只陈述当前真实可执行的语言约束。
    else:

        # 通用文案不虚构技能名，具体 owner 的加载要求留在对应语言路由。
        str_shared_route = (  # 单 owner 或无 owner 的共同门禁
            "创建或修改 Python、bat/cmd、shell/bash、PowerShell、Tcl 代码前必须先思考；"
            "必须在过程中满足当前可执行的语言门禁，不得事后补做。"
        )

    # Python owner 可用时，Python 路由只保存职责和所有权合同。
    if python_installed:

        # companion 存在时显式阻止脚本技能接管 Python 最终职责。
        str_python_boundary = (  # Python 跨技能所有权边界
            "不得由 `readable-script-generator` 接管。"  # 双 owner 场景拒绝脚本技能接管
            if script_installed  # companion 可用时只保留所有权排除边界
            else "创建或修改时必须加载该技能，该技能门禁满足后才能继续。"  # 单 owner 场景保留加载门禁
        )

        # Python 路由组合触发范围、owner 质量合同与跨技能边界。
        str_python_route = (  # 完整 Python 所有权路由
            "进行 Python 代码生成、修改、注释和规范化时，"
            "Python 最终仍由 `readable-python-generator` 负责，"
            "并遵循其任务分类、注释质量、变量命名和质量门禁；"
            f"{str_python_boundary}"
        )

    # Python owner 缺失时只保留语言专属边界，不虚构具体技能。
    else:

        # 一般边界阻止脚本规则接管 Python 目标。
        str_python_route = "Python 目标保持 Python 专属技能边界，不得由脚本技能接管。"  # Python 一般所有权边界

    # 脚本路由只在对应 owner 可用时点名技能，并按 Python 安装态选择边界措辞。
    if script_installed:

        # Python owner 可用时在脚本路由中保留跨语言移交边界。
        if python_installed:

            # Python 目标必须回到自己的 readable owner。
            str_python_boundary = (  # Python owner 移交边界
                "Python 目标不属于本脚本路由，"
                "Python 目标继续使用 `readable-python-generator`；"
            )

        # Python owner 缺失时只声明脚本路由不拥有 Python 目标。
        else:

            # 无技能名的一般边界避免虚构不可加载的 Python owner。
            str_python_boundary = "Python 目标不属于本脚本路由；"  # Python 目标排除边界

        # 单脚本 owner 场景把自身加载要求附在脚本路由，避免共同门禁虚构 companion。
        str_script_loading = (  # 脚本 owner 的单技能加载要求
            ""  # 双 owner 场景由共同门禁统一声明加载要求
            if python_installed  # Python owner 可用时共同门禁已经覆盖加载动作
            else "创建或修改时必须加载该技能，该技能门禁满足后才能继续。"  # 单脚本 owner 场景补充自身门禁
        )

        # 脚本路由组合目标语言、最终 owner、跨语言移交与包装器边界。
        str_script_route = (  # 完整脚本所有权路由
            "bat/cmd、shell/bash、PowerShell、Tcl 脚本目标最终由 "
            "`readable-script-generator` 负责；"
            f"{str_python_boundary}调用 Python 外部命令的脚本包装器仍按脚本目标处理；"
            f"{str_script_loading}"
        )

    # 脚本 owner 缺失时不得在路由中虚构技能名。
    else:

        # 一般脚本边界仍需保留包装器按目标语言判定的规则。
        str_script_route = (  # 未安装脚本 owner 的一般所有权边界
            "bat/cmd、shell/bash、PowerShell、Tcl 目标保持脚本专属技能边界；"
            "Python 目标不属于本脚本路由；"
            "调用 Python 外部命令的脚本包装器仍按脚本目标处理。"
        )

    # 三段文本供配置默认值、渲染和 verifier 按职责独立复用。
    return str_shared_route, str_python_route, str_script_route

# 当前进程的 Python owner 安装事实决定动态默认路由。
BOOL_READABLE_PYTHON_INSTALLED = readable_skill_is_installed(READABLE_PYTHON_SKILL)  # Python owner 安装状态

# 脚本 owner 独立探测，禁止由 Python owner 状态推断。
BOOL_READABLE_SCRIPT_INSTALLED = readable_skill_is_installed(READABLE_SCRIPT_SKILL)  # 脚本 owner 安装状态

# 默认路由构造结果先保留为具名三元组，避免隐式解包模糊职责。
tuple_default_language_skill_routes = build_language_skill_routes(  # 当前安装态默认路由
    BOOL_READABLE_PYTHON_INSTALLED,  # Python owner 安装事实
    BOOL_READABLE_SCRIPT_INSTALLED,  # 脚本 owner 安装事实
)

# 首项固定对应共同门禁，供配置默认值和 verifier 共用。
DEFAULT_LANGUAGE_SKILL_ROUTING_SHARED = tuple_default_language_skill_routes[0]  # 共同门禁默认文本

# 次项固定对应 Python 路由，避免共同门禁与所有权文本混用。
DEFAULT_LANGUAGE_SKILL_ROUTING_PYTHON = tuple_default_language_skill_routes[1]  # Python 默认路由

# 第三项固定对应脚本路由，避免跨语言默认值误用。
DEFAULT_LANGUAGE_SKILL_ROUTING_SCRIPT = tuple_default_language_skill_routes[2]  # 脚本默认路由

# 共同门禁必须保留修改前思考、过程内验证和禁止事后补做三类约束。
SHARED_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS = (  # 共同门禁强制短语
    "必须先思考",  # 修改前思考边界
    "必须在过程中满足",  # 实现过程内门禁边界
    "不得事后补做",  # 禁止事后补门禁
) + (  # 安装态决定双技能或通用共同门禁短语
    (  # 双技能均可用时必须保留完整共同加载合同
        "readable-python-generator",  # Python owner 的共同加载要求
        "readable-script-generator",  # 脚本 owner 的共同加载要求
        "同时加载",  # 两个 owner 必须在修改前共同加载
        "两个技能的门禁必须在过程中满足",  # 两个门禁都必须在实现过程内完成
        "全部通过后才能继续",  # 两个门禁均通过才允许继续
    )
    if BOOL_READABLE_PYTHON_INSTALLED and BOOL_READABLE_SCRIPT_INSTALLED  # 双安装采用严格共同门禁
    else ("当前可执行的语言门禁",)  # 其他安装态不虚构缺失技能
)

# 历史两字段合同没有独立共同门禁，空值仅用于受管迁移识别。
LEGACY_MANAGED_LANGUAGE_SKILL_ROUTING_SHARED = ""  # 历史共同门禁占位值

# 收集 Python 路由默认文案，确保双技能前置与最终归属同时成立。
LEGACY_MANAGED_LANGUAGE_SKILL_ROUTING_PYTHON = (  # 历史 Python 受管默认路由
    "进行 Python 代码生成、修改、注释、规范化时优先使用 `readable-python-generator`；"  # 历史触发与 owner
    "必须先思考，必须同时使用 readable-python-generator 和 readable-script-generator，"
    "两个技能的门禁条件都满足后才能继续；Python 最终仍由 `readable-python-generator` 负责，"
    "不能改由 `readable-script-generator` 接管，并遵循其任务分类、注释质量、变量命名和质量门禁。"
)

# 收集脚本路由默认文案，确保双技能前置与脚本归属边界同时成立。
LEGACY_MANAGED_LANGUAGE_SKILL_ROUTING_SCRIPT = (  # 历史脚本受管默认路由
    "进行 bat/cmd、shell/bash、PowerShell、Tcl 脚本生成、审查、重构、修复、解释、添加/规范中文语义注释时优先使用 `readable-script-generator`；"  # 历史脚本触发声明
    "必须先思考，"
    "必须同时使用 readable-python-generator 和 readable-script-generator，两个技能的门禁条件都满足后才能继续；"
    "目标必须是这些脚本语言。Python 目标继续使用 `readable-python-generator`；"
    "脚本包装器调用 Python 外部命令时仍按脚本目标处理。脚本目标最终由 `readable-script-generator` 负责。"
)

# 收集 Python 路由必须命中的精确短语，供 verifier 和测试共享。
PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS = (  # 供根规则校验器阻断最终所有权缺失
    (  # 根据当前安装事实选择 Python 最终所有权约束
        "Python 最终仍由 `readable-python-generator` 负责",  # Python 最终所有权必须保留的验收短语
        "任务分类",  # Python owner 继续承担任务分类
        "注释质量",  # Python owner 继续承担注释质量检查
        "变量命名",  # Python owner 继续承担变量命名检查
        "质量门禁",  # Python owner 继续承担最终质量门禁
        "不得由 `readable-script-generator` 接管",  # companion 不得接管 Python 最终职责
    )
    if BOOL_READABLE_PYTHON_INSTALLED and BOOL_READABLE_SCRIPT_INSTALLED  # 双技能均安装时采用严格合同
    else (  # 单技能或无技能场景的 Python 路由合同
        (  # 仅 Python 技能可用时保留 owner 质量合同和加载要求
            "readable-python-generator",  # Python 最终 owner 名称
            "任务分类",  # 单 owner 仍承担任务分类
            "注释质量",  # 单 owner 仍承担注释质量检查
            "变量命名",  # 单 owner 仍承担变量命名检查
            "质量门禁",  # 单 owner 仍承担最终质量门禁
            "创建或修改时必须加载该技能",  # 单 owner 需要显式加载
            "该技能门禁满足后才能继续",  # 单 owner 门禁必须通过
        )
        if BOOL_READABLE_PYTHON_INSTALLED  # Python 技能真实可加载的选择分支
        else ("Python 专属技能边界", "不得由脚本技能接管")  # Python 技能缺失时的一般合同
    )
)

# 列出脚本路由必须覆盖的目标语言、包装器边界与最终归属，避免脚本侧规则被弱化。
SCRIPT_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS = (  # 脚本强制短语
    "bat/cmd",  # 批处理目标仍属于脚本侧
    "shell/bash",  # Shell 目标仍属于脚本侧
    "PowerShell",  # PowerShell 目标继续沿用脚本技能收口
    "Tcl",  # Tcl 目标继续保留在脚本技能范围内
    "调用 Python 外部命令的脚本包装器",  # 包装器调用 Python 仍按脚本目标处理
) + (  # 安装态决定脚本 owner 和跨语言移交约束
    (  # 当前安装状态对应的脚本最终所有权约束
        "脚本目标最终由 `readable-script-generator` 负责",  # 脚本最终所有权必须保留的验收短语
        "Python 目标继续使用 `readable-python-generator`",  # 跨语言目标必须移交 Python 技能
    )
    if BOOL_READABLE_PYTHON_INSTALLED and BOOL_READABLE_SCRIPT_INSTALLED  # 双技能均安装时采用脚本严格合同
    else (  # 单技能或无技能场景的脚本路由合同
        (  # 仅脚本技能可用时保留 owner 和加载要求
            "readable-script-generator",  # 脚本最终 owner 名称
            "创建或修改时必须加载该技能",  # 脚本修改必须先加载唯一可用的 owner
            "该技能门禁满足后才能继续",  # 脚本 owner 门禁通过后才允许继续
            "Python 目标不属于本脚本路由",  # Python 目标不归脚本 owner
        )
        if BOOL_READABLE_SCRIPT_INSTALLED  # 脚本技能真实可加载的选择分支
        else ("脚本专属技能边界", "Python 目标不属于本脚本路由")  # 脚本技能缺失时的一般合同
    )
)

# 禁用短语构造器在函数内处理安装分支，避免模块导入产生可执行控制流。
def forbidden_language_skill_route_snippets(
    python_installed: bool,
    script_installed: bool,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """按安装事实返回两条路由不得出现的技能名。

    参数:
        python_installed: Python readable 技能是否已安装。
        script_installed: 脚本 readable 技能是否已安装。

    返回:
        Python 路由禁用短语与脚本路由禁用短语组成的二元组。
    """

    # 双安装场景允许两条路由共同引用两个 owner。
    if python_installed and script_installed:

        # 空二元组明确表示两条路由都没有禁用技能名。
        return (), ()

    # 仅 Python owner 可用时，脚本一般路由不得引用任何 owner。
    if python_installed:

        # Python 路由只排除缺失 companion，脚本路由排除两个技能名。
        return (READABLE_SCRIPT_SKILL,), (READABLE_PYTHON_SKILL, READABLE_SCRIPT_SKILL)

    # 仅脚本 owner 可用时，Python 一般路由不得引用任何 owner。
    if script_installed:

        # Python 路由排除两个技能名，脚本路由只排除缺失 companion。
        return (READABLE_PYTHON_SKILL, READABLE_SCRIPT_SKILL), (READABLE_PYTHON_SKILL,)

    # 全新环境的两条一般路由都不得虚构任一技能已安装。
    tuple_all_skill_names = (READABLE_PYTHON_SKILL, READABLE_SCRIPT_SKILL)  # 全部 readable owner 名称

    # 两条路由共享同一不可引用集合，但返回独立的二元组位置。
    return tuple_all_skill_names, tuple_all_skill_names

# 当前安装态的禁用短语只计算一次，供 verifier 和测试共享。
tuple_forbidden_language_skill_routes = forbidden_language_skill_route_snippets(  # 两条路由禁用短语
    BOOL_READABLE_PYTHON_INSTALLED,  # 禁用规则的 Python 状态输入
    BOOL_READABLE_SCRIPT_INSTALLED,  # 禁用规则的脚本状态输入
)

# 首项是 Python 路由不得引用的技能名。
PYTHON_LANGUAGE_SKILL_ROUTE_FORBIDDEN_SNIPPETS = tuple_forbidden_language_skill_routes[0]  # Python 禁用短语

# 次项是脚本路由不得引用的技能名。
SCRIPT_LANGUAGE_SKILL_ROUTE_FORBIDDEN_SNIPPETS = tuple_forbidden_language_skill_routes[1]  # 脚本禁用短语

# 默认路由枚举用于安全区分受管文本与用户自定义文本。
def managed_language_skill_route_defaults() -> tuple[set[str], set[str], set[str]]:
    """返回所有生成器已知默认路由，供安全迁移时识别用户自定义文本。

    参数:
        无。

    返回:
        共同门禁、Python 与脚本受管路由集合组成的三元组。
    """

    # 动态路由集合从空列表开始按四种安装组合稳定扩展。
    list_route_triples: list[tuple[str, str, str]] = []  # 四种安装组合的路由三元组

    # 历史两字段合同用空共同门禁标识可自动升级的旧结构。
    set_shared_routes = {LEGACY_MANAGED_LANGUAGE_SKILL_ROUTING_SHARED}  # 共同门禁受管集合

    # 旧固定双技能文案也属于可自动升级的受管默认值。
    set_python_routes = {LEGACY_MANAGED_LANGUAGE_SKILL_ROUTING_PYTHON}  # Python 受管路由集合

    # 脚本集合独立初始化，禁止跨语言文本误判为可迁移默认值。
    set_script_routes = {LEGACY_MANAGED_LANGUAGE_SKILL_ROUTING_SCRIPT}  # 脚本受管路由集合

    # 外层遍历 Python owner 的未安装与已安装状态。
    for bool_python_installed in (False, True):  # 外层 Python 安装状态

        # 内层遍历脚本 owner，形成完整笛卡尔组合。
        for bool_script_installed in (False, True):  # 内层脚本安装状态

            # 每个组合只调用一次生产路由构造器。
            tuple_routes = build_language_skill_routes(  # 当前安装组合的两条路由
                bool_python_installed,  # 当前 Python owner 状态
                bool_script_installed,  # 当前脚本 owner 状态
            )

            # 保存三元组供后续按语言独立加入受管集合。
            list_route_triples.append(tuple_routes)

    # 动态默认分别加入对应语言集合，避免跨语言文本误判。
    for tuple_routes in list_route_triples:  # 当前安装组合路由三元组

        # 首项固定对应共同门禁。
        str_shared_route = tuple_routes[0]  # 当前组合的共同门禁

        # 次项固定对应 Python 路由。
        str_python_route = tuple_routes[1]  # 当前组合的 Python 路由

        # 第三项固定对应脚本路由。
        str_script_route = tuple_routes[2]  # 当前组合的脚本路由

        # 共同门禁默认文本只加入 shared 受管集合。
        set_shared_routes.add(str_shared_route)

        # Python 默认文本只加入 Python 受管集合。
        set_python_routes.add(str_python_route)

        # 脚本默认文本只加入脚本受管集合。
        set_script_routes.add(str_script_route)

    # 三个集合供配置修复逻辑判断整组路由是否可安全刷新。
    return set_shared_routes, set_python_routes, set_script_routes

# 列出历史 Python 路由必须保留的兼容短语，供旧版本根文件验收继续使用。
LEGACY_PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS = (  # 历史 Python 路由兼容短语
    "优先使用 `readable-python-generator`",  # 历史路由会先声明 Python 技能优先归属
    "readable-python-generator",  # 历史路由仍需点名 Python 技能
    "任务分类",  # 历史路由已经固定任务分类边界
    "注释质量",  # 历史路由已经固定注释质量边界
    "变量命名",  # 历史路由已经固定变量命名边界
    "质量门禁",  # 历史路由已经固定质量门禁边界
)

# 列出历史脚本路由必须保留的兼容短语，专门覆盖旧版“脚本优先”写法。
LEGACY_SCRIPT_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS = (  # 历史脚本路由兼容短语
    "优先使用 `readable-script-generator`",  # 历史脚本路由先声明脚本技能优先归属
    "readable-script-generator",  # 历史脚本路由仍需点名脚本技能
    "bat/cmd",  # 历史脚本路由继续覆盖 bat/cmd
    "shell/bash",  # 历史脚本路由把 shell/bash 明确保留在脚本技能范围
    "PowerShell",  # 历史脚本路由继续把 Windows shell 交给脚本技能兜底
    "Tcl",  # 历史脚本路由继续把 EDA/Tcl 脚本留在脚本技能边界内
    "Python 目标继续使用 `readable-python-generator`",  # 历史脚本路由仍保留 Python 目标边界
    "脚本包装器调用 Python",  # 历史脚本路由仍保留包装器边界
)

# 收集共同门禁行前缀，供逐行抽取时定位跨语言规则。
SHARED_ROUTE_PREFIX = "- 语言技能共同门禁："  # 共同门禁前缀用于本步校验判断

# 收集 Python 路由行前缀，供逐行抽取时定位单条规则。
PYTHON_ROUTE_PREFIX = "- 语言技能路由（Python）："  # Python 路由前缀用于本步校验判断

# 使用脚本前缀从 AGENTS 行文本中切出脚本规则，避免跨行命中误判。
SCRIPT_ROUTE_PREFIX = "- 语言技能路由（脚本）："  # 脚本路由前缀用于本步校验判断

# 返回缺失短语列表，供上游 verifier 生成精确的退化诊断。
def missing_language_skill_route_snippets(route_text: str, required_snippets: tuple[str, ...]) -> list[str]:
    """返回路由文本缺失的强制短语。

    参数:
        route_text: 当前待校验的单条路由文本。
        required_snippets: 该路由必须保留的强制短语集合。

    返回:
        按输入顺序保留的缺失短语列表。
    """

    # 返回当前路由中缺失的强制短语，顺序保持与输入短语一致。
    return [snippet for snippet in required_snippets if snippet not in route_text]

# 抽出目标前缀所在的整行文本，避免多行拼接掩盖单行规则退化。
def route_line(body: str, prefix: str) -> str:
    """提取指定前缀的单行路由文本。

    参数:
        body: 待检查的整段 AGENTS 文本。
        prefix: 目标路由所在行的固定前缀。

    返回:
        命中的整行文本；未命中时返回空字符串。
    """

    # 返回首条命中前缀的路由行，避免多行拼接掩盖文本退化。
    return next((line for line in body.splitlines() if line.startswith(prefix)), "")

# 分别校验共同门禁、Python 与脚本路由，阻止 managed root 文案静默退化。
def validate_language_skill_route_lines(
    body: str,
    file: str,
    errors: list[str],
    *,
    use_legacy_rules: bool = False,
) -> bool:
    """逐行校验共同门禁与两个语言路由，避免跨行文本掩盖退化。

    参数:
        body: 待检查的 AGENTS 文本正文。
        file: 当前错误信息应回填的文件标识。
        errors: 累积校验错误的可变列表。
        use_legacy_rules: 为 True 时允许历史单技能路由，同时接受当前严格路由。

    返回:
        当共同门禁与两条语言路由都保留完整强制规则时返回 True，否则返回 False。
    """

    # 汇总三条规则的累计通过状态，任一缺口都会把结果切到失败。
    bool_routes_valid = True  # 三条规则的累计通过状态

    # 抓取共同门禁整行，当前严格合同必须显式保留该行。
    str_shared_route = route_line(body, SHARED_ROUTE_PREFIX)  # 共同门禁整行文本

    # 抓取 Python 路由整行，后续据此选择兼容或当前严格合同。
    str_python_route = route_line(body, PYTHON_ROUTE_PREFIX)  # Python 路由整行文本

    # 抓取脚本路由整行，后续单独核对脚本目标边界。
    str_script_route = route_line(body, SCRIPT_ROUTE_PREFIX)  # 脚本路由整行文本

    # 历史版本只在共同门禁行确实缺失时使用旧两行兼容合同。
    if use_legacy_rules and not str_shared_route:

        # 历史根文件继续使用旧 Python 路由短语集合。
        tuple_python_required_snippets = LEGACY_PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS  # 历史 Python 兼容短语

        # 历史脚本路由继续验证目标语言和包装器边界。
        tuple_script_required_snippets = LEGACY_SCRIPT_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS  # 历史脚本兼容短语

    # 当前合同存在 shared 行时，无论版本分支都按三行结构严格校验。
    else:

        # 共同门禁必须保留当前安装态对应的强制短语。
        if not str_shared_route:

            # 缺少共同门禁整行会让跨语言前置约束失去唯一来源。
            errors.append(f"{file}: Coding Behavior Baseline language skill routing missing shared gate line")

            # 共同门禁缺失后整体校验必须失败。
            bool_routes_valid = False  # 共同门禁整行缺失

        # 共同门禁存在时逐项检查过程内约束。
        else:

            # 每条共同短语都必须位于 shared 行内，不能依靠其他路由补齐。
            for snippet in SHARED_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS:

                # 当前共同短语缺失时登记精确退化点。
                if snippet not in str_shared_route:

                    # 回显缺失短语，方便直接定位配置弱化内容。
                    errors.append(
                        (
                            f"{file}: Coding Behavior Baseline language skill routing shared gate missing "
                            f"required rule `{snippet}`"
                        )
                    )

                    # 保留后续诊断，但整体结果切换到失败。
                    bool_routes_valid = False  # 共同门禁存在缺失短语

        # 当前版本根文件继续使用严格 Python 所有权短语集合。
        tuple_python_required_snippets = PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS  # 当前 Python 路由强制短语集合

        # 严格模式下脚本路由必须保留目标语言、包装器边界和最终归属。
        tuple_script_required_snippets = SCRIPT_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS  # 当前脚本路由强制短语集合

        # 共同门禁正文用于阻止两个语言路由再次完整复制相同文本。
        str_shared_body = str_shared_route.removeprefix(SHARED_ROUTE_PREFIX).strip()  # 不含标题的共同门禁正文

        # 非空共同正文不得再次完整出现在任一语言所有权路由中。
        if str_shared_body and (str_shared_body in str_python_route or str_shared_body in str_script_route):

            # 重复全文会重新引入用户指出的冗余生成问题。
            errors.append(f"{file}: Coding Behavior Baseline language skill routing repeats shared gate text")

            # 重复共同门禁属于严格合同失败。
            bool_routes_valid = False  # 共同门禁全文被重复渲染

    # 检查 Python 路由是否存在，缺失时直接记录错误。
    if not str_python_route:

        # 缺少整行时直接留下结构缺失诊断。
        errors.append(f"{file}: Coding Behavior Baseline language skill routing missing Python route line")

        # 整行缺失已经足以阻塞整体校验结果。
        bool_routes_valid = False  # Python 路由整行缺失

    # Python 路由存在时，再逐项检查必备短语是否完整保留。
    else:

        # 逐项核对 Python 路由必须保留的双技能与归属短语。
        for snippet in tuple_python_required_snippets:

            # 检查当前强制短语是否在 Python 路由中缺失。
            if snippet not in str_python_route:

                # 用缺失短语原样回填报错，方便测试精确命中退化点。
                errors.append(
                    (
                        f"{file}: Coding Behavior Baseline language skill routing Python route missing "
                        f"required rule `{snippet}`"
                    )
                )

                # 继续检查剩余短语，但整体结果保持失败。
                bool_routes_valid = False  # Python 路由存在缺失短语

    # 若脚本整行已经消失，先报告脚本侧 contract 本体缺失。
    if not str_script_route:

        # 缺少脚本整行时直接记录结构断裂，避免遗漏脚本边界退化。
        errors.append(f"{file}: Coding Behavior Baseline language skill routing missing script route line")

        # 脚本整行缺失后，整体校验必须保持失败。
        bool_routes_valid = False  # 脚本路由整行缺失

    # 脚本路由存在时，再逐项检查脚本侧边界与强制短语。
    else:

        # 逐项核对脚本路由必须保留的目标语言、包装器边界与最终归属。
        for snippet in tuple_script_required_snippets:

            # 若脚本边界短语缺失，就逐条回填脚本侧退化诊断。
            if snippet not in str_script_route:

                # 用脚本侧缺失短语直接回填报错，方便定位具体退化项。
                errors.append(
                    (
                        f"{file}: Coding Behavior Baseline language skill routing script route missing "
                        f"required rule `{snippet}`"
                    )
                )

                # 即使继续遍历剩余短语，整体结果也必须保留失败状态。
                bool_routes_valid = False  # 脚本路由存在缺失短语

    # 返回当前逐行校验结果，供上游决定是否阻塞后续流程。
    return bool_routes_valid
