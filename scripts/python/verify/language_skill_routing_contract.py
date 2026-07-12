"""语言技能路由默认文案与校验辅助。"""

# 导入 语言技能路由契约 所需的依赖声明。
from __future__ import annotations

# 收集 Python 与脚本路由共同必须保留的强制短语，供渲染和校验复用。
LANGUAGE_SKILL_ROUTING_REQUIRED_PHRASES = (  # 保留双技能流程的公共硬门禁短语
    "必须先思考",  # 双技能流程先要求显式思考
    "必须同时使用 readable-python-generator 和 readable-script-generator",  # 两个 readable 技能都要显式加载
    "两个技能的门禁条件都满足后才能继续",  # 双技能门禁全部通过后才允许继续
)

# 收集 Python 路由默认文案，确保双技能前置与最终归属同时成立。
DEFAULT_LANGUAGE_SKILL_ROUTING_PYTHON = (
    "进行 Python 代码生成、修改、注释、规范化时优先使用 `readable-python-generator`；"
    "必须先思考，必须同时使用 readable-python-generator 和 readable-script-generator，"
    "两个技能的门禁条件都满足后才能继续；Python 最终仍由 `readable-python-generator` 负责，"
    "不能改由 `readable-script-generator` 接管，并遵循其任务分类、注释质量、变量命名和质量门禁。"
)

# 收集脚本路由默认文案，确保双技能前置与脚本归属边界同时成立。
DEFAULT_LANGUAGE_SKILL_ROUTING_SCRIPT = (
    "进行 bat/cmd、shell/bash、PowerShell、Tcl 脚本生成、审查、重构、修复、解释、添加/规范中文语义注释时优先使用 `readable-script-generator`；"
    "必须先思考，"
    "必须同时使用 readable-python-generator 和 readable-script-generator，两个技能的门禁条件都满足后才能继续；"
    "目标必须是这些脚本语言。Python 目标继续使用 `readable-python-generator`；"
    "脚本包装器调用 Python 外部命令时仍按脚本目标处理。脚本目标最终由 `readable-script-generator` 负责。"
)

# 收集 Python 路由必须命中的精确短语，供 verifier 和测试共享。
PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS = LANGUAGE_SKILL_ROUTING_REQUIRED_PHRASES + (  # 罗列 Python 路由不可删减的契约短语
    "readable-python-generator",  # Python 路由必须点名最终负责技能
    "readable-script-generator",  # Python 路由还要保留脚本技能前置门禁
    "Python 最终仍由 `readable-python-generator` 负责",  # 明确 Python 最终归属不变
    "不能改由 `readable-script-generator` 接管",  # 阻止脚本技能越权接管 Python
)

# 列出脚本路由必须覆盖的目标语言、包装器边界与最终归属，避免脚本侧规则被弱化。
SCRIPT_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS = LANGUAGE_SKILL_ROUTING_REQUIRED_PHRASES + (  # 罗列脚本路由不可删减的归属与边界短语
    "readable-python-generator",  # 脚本路由仍需保留 Python 归属边界
    "readable-script-generator",  # 脚本路由必须点名最终负责技能
    "bat/cmd",  # 批处理目标仍属于脚本侧
    "shell/bash",  # Shell 目标仍属于脚本侧
    "PowerShell",  # PowerShell 目标继续沿用脚本技能收口
    "Tcl",  # Tcl 目标继续保留在脚本技能范围内
    "Python 目标继续使用 `readable-python-generator`",  # 继续保留 Python 目标边界
    "脚本包装器调用 Python",  # 包装器调用 Python 仍按脚本目标处理
    "脚本目标最终由 `readable-script-generator` 负责",  # 明确脚本最终归属不变
)

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

# 分别校验 Python 与脚本路由的强制短语，阻止 managed root 文案静默退化。
def validate_language_skill_route_lines(
    body: str,
    file: str,
    errors: list[str],
    *,
    use_legacy_rules: bool = False,
) -> bool:
    """逐行校验 Python 与脚本路由，避免跨行文本掩盖退化。

    参数:
        body: 待检查的 AGENTS 文本正文。
        file: 当前错误信息应回填的文件标识。
        errors: 累积校验错误的可变列表。
        use_legacy_rules: 为 True 时改用历史单技能路由短语验收旧版本根文件。

    返回:
        当 Python 与脚本两条路由都保留完整强制规则时返回 True，否则返回 False。
    """

    # 汇总两条路由的累计通过状态，任一缺口都会把结果切到失败。
    bool_routes_valid = True  # 两条路由的累计通过状态

    # 根据当前版本分支选择逐行所需短语，避免旧版本根文件被今天的新契约误杀。
    if use_legacy_rules:

        # 旧版根文件改用历史 Python 路由短语集合，避免把历史“优先使用”写法误判成退化。
        tuple_python_required_snippets = LEGACY_PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS  # 历史 Python 路由强制短语集合

        # 旧版根文件的脚本包装器边界也要切回历史脚本短语集合。
        tuple_script_required_snippets = LEGACY_SCRIPT_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS  # 历史脚本路由强制短语集合

    # 当前版本根文件走严格双技能路由分支时，再切到今天的强制短语集合。
    else:

        # 当前版本根文件继续使用严格 Python 双技能路由短语集合。
        tuple_python_required_snippets = PYTHON_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS  # 当前 Python 路由强制短语集合

        # 严格模式下脚本路由必须同时保留双技能门禁、包装器边界和最终归属。
        tuple_script_required_snippets = SCRIPT_LANGUAGE_SKILL_ROUTE_REQUIRED_SNIPPETS  # 当前脚本路由强制短语集合

    # 抓取 Python 路由整行，后续逐项核对 Python 侧强制短语。
    str_python_route = route_line(body, PYTHON_ROUTE_PREFIX)  # Python 路由整行文本

    # 抓取脚本路由整行，后续单独核对脚本目标边界。
    str_script_route = route_line(body, SCRIPT_ROUTE_PREFIX)  # 脚本路由整行文本

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
