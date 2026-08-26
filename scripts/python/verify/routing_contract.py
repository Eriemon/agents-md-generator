"""语言技能路由默认文案与校验辅助。"""

# 延迟注解解析避免运行时解析仅用于类型检查的参数。
from __future__ import annotations

# 标准库提供环境变量读取、JSON 路由配置和跨平台路径处理。
import json
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

    # 平台目录和显式隔离根统一由技能目录解析结果提供。
    try:

        # 延迟加载平台目录，兼容源码态和安装态运行入口。
        from agent_platform import load_agent_config, resolve_agent_home

    # 平台目录缺失或损坏时按未安装处理，禁止猜测安装位置。
    except (ModuleNotFoundError, FileNotFoundError, ValueError):

        # 无法证明平台配置有效时返回保守的未安装结果。
        return False

    # 当前文件向上三级定位技能根目录。
    path_skill_root: Path = Path(__file__).resolve().parents[3]  # 当前技能根目录

    # 读取技能根对应的平台配置档案。
    try:

        # 平台配置作为后续用户根和安装目录的唯一来源。
        profile_agent = load_agent_config(path_skill_root)  # 当前平台配置档案

    # 配置文件缺失或内容非法时保持 fail-closed 安装判断。
    except (FileNotFoundError, ValueError):

        # 无法读取档案时不能把任意目录当作已安装技能。
        return False

    # 环境变量只作为平台用户根的显式覆盖输入。
    str_raw_home = os.environ.get("AGENT_HOME", "").strip() or os.environ.get("CODEX_HOME", "").strip()  # 用户根覆盖文本

    # 解析平台用户根后再检查固定技能安装目录。
    path_agent_home = resolve_agent_home(path_skill_root, str_raw_home, profile_agent.agent)  # 平台用户根目录

    # 目录存在即构成当前渲染进程可加载该技能的安装证据。
    return (path_agent_home / profile_agent.skill_install_dir / skill_name).is_dir()

# 读取 packaged structured route defaults，配置缺失时才进入兼容 fallback。
def _load_structured_route_defaults() -> dict[str, object]:
    """读取语言路由的结构化默认配置。

    参数：无。

    返回：包含 shared、python、script 三条结构化路由的映射；来源不可用时返回空映射。
    """

    # 项目 override 优先于 packaged 默认，安装态仍使用 Skill 内配置。
    list_route_config_paths = [
        Path.cwd() / ".agents" / "global-rule-overrides.json",  # 当前项目的治理覆盖配置
        Path(__file__).resolve().parents[3] / "config" / "language-routes.json",  # Skill 内置路由配置
    ]  # 路由配置候选路径

    # 按项目覆盖优先、内置配置兜底的顺序读取路由来源。
    for path_route_config in list_route_config_paths:

        # 缺失的项目 override 不能阻断 packaged defaults 的读取。
        if not path_route_config.is_file():

            # 继续尝试下一个受管配置来源。
            continue

        # 解析当前候选配置，拒绝执行任何配置文本。
        try:

            # 只读取 JSON 对象，不执行任何配置文本。
            object_route_config = json.loads(path_route_config.read_text(encoding="utf-8"))  # 路由配置对象

        # 读取或解析失败时继续尝试下一个受管来源。
        except (OSError, UnicodeError, json.JSONDecodeError):

            # 当前来源损坏时继续使用后续受管默认，而不是返回半解析结果。
            continue

        # 非对象配置不能提供结构化路由，继续读取下一个来源。
        if not isinstance(object_route_config, dict):

            # 保持 fail-closed，同时允许 packaged defaults 修复项目 override 缺失。
            continue

        # packaged 配置直接以 routes 为根事实；override 则读取嵌套 structured 节点。
        if isinstance(object_route_config.get("routes"), dict):

            # 当前来源已经提供结构化路由记录。
            dict_structured = object_route_config["routes"]  # packaged 路由记录

        # 项目覆盖只在 packaged 路由缺失时解析 structured 节点。
        else:

            # 项目 override 可能同时保留旧字符串和新的结构化路由。
            dict_coding_behavior = object_route_config.get("coding_behavior", {})  # 项目编码行为配置

            # 从编码行为配置提取语言技能路由节点。
            if isinstance(dict_coding_behavior, dict):

                # 读取当前项目声明的语言技能路由对象。
                dict_language_routes = dict_coding_behavior.get("language_skill_routing", {})  # 语言技能路由节点

            # 非字典编码行为不能提供项目路由覆盖。
            else:

                # 配置根类型不正确时使用空路由节点。
                dict_language_routes = {}  # 空项目语言路由节点

            # 从语言技能路由节点提取结构化覆盖记录。
            if isinstance(dict_language_routes, dict):

                # 读取当前项目声明的结构化路由对象。
                dict_structured = dict_language_routes.get("structured", {})  # 结构化路由节点

            # 非字典路由节点不能提供结构化覆盖。
            else:

                # 路由节点根类型不正确时使用空结构化节点。
                dict_structured = {}  # 空结构化路由节点

        # 只有完整 route contract 才能覆盖 packaged defaults，并阻止半成品配置。
        bool_complete_routes = isinstance(dict_structured, dict) and all(  # 判断三条角色路由字段是否完整
            isinstance(dict_structured.get(str_route_name), dict)  # 当前角色记录必须是对象
            and isinstance(dict_structured[str_route_name].get("id"), str)  # 角色标识必须是字符串
            and bool(dict_structured[str_route_name]["id"].strip())  # 角色标识不能是空文本
            and isinstance(dict_structured[str_route_name].get("target_families"), list)  # 目标族必须是列表
            and isinstance(dict_structured[str_route_name].get("full_text"), str)  # 完整路由必须是字符串
            and bool(dict_structured[str_route_name]["full_text"].strip())  # 完整路由不能为空
            and isinstance(dict_structured[str_route_name].get("compact_text"), str)  # 紧凑路由必须是字符串
            and bool(dict_structured[str_route_name]["compact_text"].strip())  # 紧凑路由不能为空
            and isinstance(dict_structured[str_route_name].get("boundaries"), list)  # 边界列表必须存在
            for str_route_name in ("shared", "python", "script")  # 遍历三个角色路由
        )  # 三条路由字段完整性结果

        # 完整配置可以直接交给构造器，避免回退到不确定文本。
        if bool_complete_routes:

            # 返回可直接交给路由构造器的统一结构。
            return {"routes": dict_structured}

    # 所有受管来源都缺失或不完整时交由调用方产生稳定阻断。
    return {}

# 路由构造必须分别处理两个 owner 的四种安装组合。
def build_language_skill_routes(
    python_installed: bool,
    script_installed: bool,
    language_skill_routing: dict[str, object] | None = None,
) -> tuple[str, str, str]:
    """按两个 owner 技能的独立安装状态构造共同门禁与语言路由。

    参数：
        python_installed: Python readable 技能是否已安装。
        script_installed: 脚本 readable 技能是否已安装。
        language_skill_routing: 可选的项目治理路由文案覆盖。

    返回：
        共同门禁、Python 路由与脚本路由组成的三元组。

    异常：
        ValueError：结构化路由缺少角色记录或当前文本为空。
    """

    # 治理配置缺失时使用与 JSON 合同一致的受管默认文案。
    dict_route_defaults = _load_structured_route_defaults().get("routes", {})  # packaged 结构化路由默认值

    # 只有字典形式的默认路由才能接受项目覆盖。
    dict_route_overrides = dict_route_defaults if isinstance(dict_route_defaults, dict) else {}  # 默认路由映射

    # 项目覆盖只合并结构化路由，保留内置字段边界。
    if isinstance(language_skill_routing, dict):

        # 项目治理只覆盖结构化对象；旧版字符串覆盖留给兼容 fallback。
        dict_route_overrides = {
            **dict_route_overrides,  # 保留 packaged 默认路由字段
            **{  # 项目角色覆盖映射
                str_key: value_route  # 当前角色的结构化覆盖记录
                for str_key, value_route in language_skill_routing.items()  # 遍历项目角色覆盖
                if isinstance(value_route, dict)  # 仅接受角色对象覆盖
            },
        }  # 合并后的三条语言路由

    # 结构化路由是唯一事实源，缺少任一角色记录时立即拒绝构造路由。
    if not all(isinstance(dict_route_overrides.get(str_key), dict) for str_key in ("shared", "python", "script")):

        # 错误文本保持项目机器输出协议，供调用方稳定分类。
        raise ValueError("> ERR: [Python] structured language route records are missing")

    # 每个 owner 的安装状态独立决定使用 full_text 还是 compact_text。
    dict_route_states = {
        "shared": python_installed and script_installed,  # 双技能共同门禁是否可展开
        "python": python_installed,  # Python owner 是否可展开
        "script": script_installed,  # 脚本 owner 是否可展开
    }  # 三条路由的当前安装态

    # 按固定角色顺序保存最终可渲染文本。
    dict_result_routes: dict[str, str] = {}  # 通过安装态选择后的路由文本

    # 为每个角色选择当前安装态对应的文本字段。
    for str_route_name, bool_full_text in dict_route_states.items():

        # 锁定本次循环的角色记录，后续只读取该角色的文本字段。
        dict_route = dict_route_overrides[str_route_name]  # 当前角色的结构化路由记录

        # 依据 owner 安装态选择 full 或 compact 文本字段。
        str_route_key = "full_text" if bool_full_text else "compact_text"  # 当前安装态文本字段

        # 单 Python owner 不得泄露未安装的脚本 companion 名称。
        if str_route_name == "python" and python_installed and not script_installed:

            # 选择不包含脚本技能名的 Python owner 文案。
            str_route_key = "full_text_without_script"  # Python-only 文案字段

        # 单脚本 owner 不得泄露未安装的 Python companion 名称。
        if str_route_name == "script" and script_installed and not python_installed:

            # 选择不包含 Python 技能名的 script owner 文案。
            str_route_key = "full_text_without_python"  # 脚本 owner 的 companion 隔离文案字段

        # 清理当前角色文本外围空白，保持渲染结果稳定。
        str_route_text = str(dict_route.get(str_route_key, "")).strip()  # 当前角色最终路由文本

        # 缺少目标文本时阻止渲染出空路由。
        if not str_route_text:

            # 将缺失文本转换为可定位的机器错误。
            raise ValueError(
                f"> ERR: [Python] structured language route is missing {str_route_key}: {str_route_name}"
            )

        # 将已确认的文本写入角色结果映射。
        dict_result_routes[str_route_name] = str_route_text  # 当前角色可渲染路由

    # 返回 shared、python、script 的稳定三元组。
    return (
        dict_result_routes["shared"],
        dict_result_routes["python"],
        dict_result_routes["script"],
    )

# 当前进程的 Python owner 安装事实决定动态默认路由。
BOOL_READABLE_PYTHON_INSTALLED = readable_skill_is_installed(READABLE_PYTHON_SKILL)  # Python owner 安装状态

# 脚本 owner 独立探测，禁止由 Python owner 状态推断。
BOOL_READABLE_SCRIPT_INSTALLED = readable_skill_is_installed(READABLE_SCRIPT_SKILL)  # 脚本 owner 安装状态

# 默认治理合同固定要求两个 owner，不能受执行机安装态影响。
tuple_default_language_skill_routes = build_language_skill_routes(  # 双技能治理默认路由
    True,  # 配置默认值固定启用 Python owner
    True,  # 配置默认值固定启用脚本目标 owner
)

# 首项固定对应共同门禁，供配置默认值和 verifier 共用。
DEFAULT_LANGUAGE_SKILL_ROUTING_SHARED = tuple_default_language_skill_routes[0]  # 共同门禁默认文本

# 次项固定对应 Python 路由，避免共同门禁与所有权文本混用。
DEFAULT_LANGUAGE_SKILL_ROUTING_PYTHON = tuple_default_language_skill_routes[1]  # Python 默认路由

# 第三项固定对应脚本路由，避免跨语言默认值误用。
DEFAULT_LANGUAGE_SKILL_ROUTING_SCRIPT = tuple_default_language_skill_routes[2]  # 脚本默认路由

# 共同门禁必须保留修改前思考、过程内验证和禁止事后补做三类约束。
SHARED_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS = (  # 共同门禁强制短语
    "think through the change",  # 修改前思考边界
    "both gates must pass during the task",  # 实现过程内门禁边界
    "before continuing",  # 门禁完成边界
    "readable-python-generator",  # Python owner 的共同加载要求
    "readable-script-generator",  # 脚本 owner 的共同加载要求
    "load both",  # 两个 owner 必须在修改前共同加载
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
    "进行 bat/cmd、shell/bash、PowerShell、Tcl、Node-only JavaScript（.js/.mjs）和 "
    "static Dockerfile 脚本生成、审查、重构、修复、解释、添加/规范中文语义注释时优先使用 "
    "`readable-script-generator`；"  # 历史脚本触发声明
    "必须先思考，"
    "必须同时使用 readable-python-generator 和 readable-script-generator，两个技能的门禁条件都满足后才能继续；"
    "目标必须是这些脚本语言。Python 目标继续使用 `readable-python-generator`；"
    "脚本包装器调用 Python 外部命令时仍按脚本目标处理。脚本目标最终由 `readable-script-generator` 负责。"
)

# 收集 Python 路由必须命中的精确短语，供 verifier 和测试共享。
PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS = (  # 供根规则校验器阻断最终所有权缺失
    "readable-python-generator is the final owner",  # Python 最终所有权必须保留
    "task classification",  # Python owner 继续承担任务分类
    "comment",  # Python owner 继续承担注释质量检查
    "naming",  # Python owner 继续承担变量命名检查
    "quality gates",  # Python owner 继续承担最终质量门禁
    "must not claim Python ownership",  # companion 不得接管 Python 职责
)

# 列出脚本路由必须覆盖的目标语言、包装器边界与最终归属，避免脚本侧规则被弱化。
SCRIPT_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS = (  # 脚本强制短语
    "bat/cmd",  # 批处理目标仍属于脚本侧
    "shell/bash",  # Shell 目标仍属于脚本侧
    "PowerShell",  # PowerShell 目标继续沿用脚本技能收口
    "Tcl",  # Tcl 目标继续保留在脚本技能范围内
    "Node-only JavaScript",  # 新增 Node-only JavaScript 目标
    "static Dockerfile",  # static Dockerfile 只允许静态分析
    "browser JavaScript",  # 浏览器脚本边界
    "readable-script-generator is the final owner",  # 脚本最终所有权必须保留
    "Python remains on readable-python-generator",  # 跨语言目标必须移交 Python 技能
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
tuple_forbidden_language_skill_routes = forbidden_language_skill_route_snippets(  # 双技能合同无禁用 owner
    True,  # 禁用检查允许 Python owner 出现在跨语言边界
    True,  # 禁用检查允许脚本 owner 出现在跨语言边界
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
SHARED_ROUTE_PREFIX = "- Shared language-skill gate: "  # 共同门禁前缀

# 收集 Python 路由行前缀，供逐行抽取时定位单条规则。
PYTHON_ROUTE_PREFIX = "- Language-skill route (Python): "  # Python 路由前缀

# 使用脚本前缀从 AGENTS 行文本中切出脚本规则，避免跨行命中误判。
SCRIPT_ROUTE_PREFIX = "- Language-skill route (scripts): "  # 脚本路由前缀

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
