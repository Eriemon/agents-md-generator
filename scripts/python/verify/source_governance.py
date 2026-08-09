"""扫描源码规模、可读性、命名、测试边界与注释策略违规。"""

# 延迟解析注解，避免运行期求值仅供静态检查使用的联合类型。
from __future__ import annotations

# 标准库提供语法树、文件匹配、词法分析和路径遍历能力。
import ast
import fnmatch
import io
import os
import re
import tokenize
from pathlib import Path
from typing import Any

# 配置模块提供项目覆盖、技能默认值和 JSON 读取合同。
from source_governance_config import (
    load_global_rule_overrides,
    load_skill_source_governance,
    read_json,
)

# 注释策略当前覆盖 Python 与常见 C/C++ 源码和头文件。
COMMENT_CHECK_EXTENSIONS = {  # 需要执行注释治理的源码扩展名。
    ".py",  # Python 源码使用 tokenize 和 AST 规则。
    ".c",  # C 源文件使用词法状态扫描。
    ".cc",  # GNU 风格 C++ 扩展名。
    ".cpp",  # 通用 C++ 源文件扩展名。
    ".cxx",  # 兼容另一种 C++ 源码命名。
    ".h",  # C 头文件参与块注释检查。
    ".hpp",  # C++ 头文件参与注释策略。
    ".hh",  # GNU 风格 C++ 头文件扩展名。
}

# 编号分片文件名会掩盖代码职责，runtime Python 脚本必须使用功能名。
NUMBERED_PYTHON_MODULE_RE = re.compile(  # 无功能语义的数字分片模块名模式。
    r"^(?:\d+|_?part\d+|.*_part\d+)$"  # 纯数字和 part 编号命名。
)

# 将源码成员转换为稳定的项目相对 POSIX 路径。
def relative_path(path: Path, root: Path) -> str:
    """返回候选源码相对扫描根的 POSIX 路径。

    参数：path 为源码文件，root 为扫描根目录。
    返回：使用正斜杠的相对路径字符串。
    """

    # 路径展示与规则匹配统一使用跨平台分隔符。
    return path.relative_to(root).as_posix()

# 选择项目本地覆盖或技能默认的源码治理配置。
def effective_source_governance(
    project: Path, profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    """解析当前项目实际生效的源码治理配置。

    参数：project 为项目根目录，profile 为可选项目画像。
    返回：配置路径、来源、配置映射和配置错误。
    """

    # 项目覆盖文件在存在有效 source_governance 分区时优先。
    overrides = load_global_rule_overrides(project, profile)  # 全局规则覆盖解析结果。

    # 读取原始 JSON 用于区分显式项目配置与合成默认值。
    raw = (  # 项目覆盖文件原始内容。
        read_json(overrides["path"])  # 显式项目覆盖内容。
        if overrides["path"].is_file()  # 覆盖文件存在时读取。
        else {}  # 缺失覆盖文件时使用空配置。
    )

    # 只有原始文件显式提供映射分区时标记为 project-local。
    if isinstance(raw, dict) and isinstance(raw.get("source_governance"), dict):

        # 返回项目覆盖及仅属于源码治理的配置错误。
        return {
            "config_path": overrides["path"],
            "config_source": "project-local",
            "config": overrides["data"].get("source_governance", {}),
            "errors": [
                item  # 当前源码治理配置错误。
                for item in overrides["errors"]  # 遍历全部覆盖配置错误。
                if item.startswith("source_governance")  # 排除其他规则分区诊断。
            ],
        }

    # 未显式覆盖时使用技能随版本发布的默认源码治理合同。
    skill = load_skill_source_governance()  # 技能本地源码治理配置。

    # 保留技能配置读取错误供报告阻断发布。
    return {
        "config_path": skill["path"],
        "config_source": "skill-local",
        "config": skill["data"],
        "errors": list(skill["errors"]),
    }

# 遍历扫描根并排除配置指定的顶层目录。
def iter_candidate_files(root: Path, config: dict[str, Any]) -> list[Path]:
    """收集源码治理需要检查的普通文件。

    参数：root 为扫描根，config 为源码治理配置。
    返回：排除配置目录后的稳定排序文件列表。
    """

    # 排除项规范为无边界斜杠的顶层目录名。
    excluded_roots = {  # 不参与源码扫描的顶层目录名。
        str(item).strip("/\\")  # 当前排除目录配置。
        for item in config.get("excluded_roots", [])  # 原始排除根列表。
    }

    # 文件列表在遍历完成后统一排序，保证报告确定性。
    list_files: list[Path] = []  # 候选源码文件路径。

    # os.walk 允许原地裁剪子目录，避免无谓扫描大型产物树。
    for current_root, dir_names, file_names in os.walk(root):

        # 当前遍历根转换为 Path 以执行相对路径运算。
        path_current_path = Path(current_root)  # 当前 os.walk 目录。

        # 正常情况下当前目录位于 root 下，异常路径安全降级为空分段。
        try:

            # 相对分段用于判断当前顶层目录类别。
            tuple_relative_parts = path_current_path.relative_to(root).parts  # 当前目录相对分段。

        # 不可相对化时不应用根级排除项，仍允许安全收集文件。
        except ValueError:

            # 空元组表示当前遍历位置没有可判定顶层根。
            tuple_relative_parts = ()  # 无法解析的相对目录分段。

        # 在根目录层裁剪排除目录，深层遍历保留普通同名子目录。
        dir_names[:] = [
            name  # 当前允许继续遍历的子目录名。
            for name in dir_names  # 遍历 os.walk 返回的子目录。
            if not tuple_relative_parts[:1] or name not in excluded_roots  # 根级排除判断。
        ]  # 原地更新 os.walk 后续遍历目录。

        # 已进入排除根时不收集其中任何文件。
        if tuple_relative_parts and tuple_relative_parts[0] in excluded_roots:

            # 跳过排除目录当前层，防止报告产物或第三方代码。
            continue

        # 当前允许目录中的每个普通文件都是后续规则候选。
        for file_name in file_names:

            # 组合当前目录与文件名得到完整路径。
            path = path_current_path / file_name  # 当前候选文件。

            # 保留所有扩展名，具体规则自行选择适用范围。
            list_files.append(path)

    # 排序后的路径列表使违规输出和测试断言稳定。
    return sorted(list_files)

# 读取源码文件的原始字节规模。
def byte_count(path: Path) -> int:
    """计算文件未解码内容的字节数。

    参数：path 为待统计文件。
    返回：文件原始字节长度。
    """

    # 原始字节避免多字节文本被字符数低估。
    return len(path.read_bytes())

# 逐物理行统计原始字节长度以识别高字节长行。
def line_byte_lengths(path: Path) -> list[int]:
    """返回文件每个物理行的原始字节长度。

    参数：path 为待统计文件。
    返回：按文件顺序排列的行字节数列表。
    """

    # splitlines 保持物理行边界且不把换行符计入长度。
    return [len(line) for line in path.read_bytes().splitlines()]

# 根据配置根与源码相对路径定位拆分计划文档。
def decomposition_plan_path(project_root: Path, relative_file: str) -> Path:
    """构造超限源码对应的分解计划路径。

    参数：project_root 为项目根，relative_file 为源码相对路径。
    返回：该源码应使用的 Markdown 分解计划路径。
    """

    # 分解计划根来自项目全局规则覆盖。
    overrides = load_global_rule_overrides(project_root)["data"]  # 全局规则覆盖数据。

    # 尺寸分区决定计划根与必需章节。
    source_limits = (  # 经过类型收窄的源码尺寸合同。
        overrides.get("source_file_limits", {})  # 原始尺寸限制分区。
        if isinstance(overrides.get("source_file_limits", {}), dict)  # 仅接受映射配置。
        else {}  # 无效类型按未配置处理。
    )

    # 计划根去除外围分隔符后才能安全拼接项目根。
    plan_root = (  # 规范化后的分解计划根目录。
        str(  # 将配置值统一转换为路径文本。
            source_limits.get(  # 从尺寸合同选择计划根。
                "decomposition_plan_root",  # 自定义计划目录键。
                "docs/development/decomposition-plans",  # 默认计划目录。
            )
        )
        .strip()  # 去除配置值外围空白。
        .strip("/\\")  # 移除根目录两侧路径分隔符。
    )

    # 文件路径移除盘符冒号并统一分隔符，安全映射为计划文件名。
    sanitized = relative_file.replace("\\", "/").replace(":", "")  # 计划文件安全后缀。

    # 每个源码文件使用自身相对路径加 .md 形成唯一计划位置。
    return project_root / plan_root / f"{sanitized}.md"

# 验证超限源码是否已有包含必需章节的分解计划。
def has_valid_decomposition_plan(project_root: Path, relative_file: str) -> bool:
    """判断源码分解计划是否存在并包含全部必需章节。

    参数：project_root 为项目根，relative_file 为超限源码相对路径。
    返回：计划文件存在且章节完整时为 True。
    """

    # 计划位置与超限报告使用同一映射函数。
    path_plan_path = decomposition_plan_path(project_root, relative_file)  # 预期分解计划路径。

    # 安装副本携带发布时核准的计划，使脱离仓库后仍能独立复核超限源码。
    if not path_plan_path.is_file():

        # Windows 相对路径先归一化，确保安装包内使用统一目录层级。
        str_bundled_relative = relative_file.replace("\\", "/")  # bundled 计划相对路径。

        # bundled 路径保留源码相对层级，避免文件名碰撞。
        path_plan_path = (  # 安装副本内的计划候选。
            project_root  # 安装技能根。
            / "references"  # 发布参考资料目录。
            / "decomposition-plans"  # bundled 分解计划根。
            / f"{str_bundled_relative}.md"  # 当前源码对应计划。
        )

    # 缺失计划不能豁免源码尺寸硬门禁。
    if not path_plan_path.is_file():

        # 显式返回失败供超限报告决定是否阻断。
        return False

    # 忽略异常字节以继续检查 Markdown 标题合同。
    text = path_plan_path.read_text(encoding="utf-8", errors="ignore")  # 分解计划正文。

    # 必需章节来自项目源码尺寸治理配置。
    overrides = load_global_rule_overrides(project_root)["data"]  # 当前全局规则覆盖数据。

    # 章节合同只从合法映射分区读取。
    source_limits = (  # 经过类型确认的尺寸治理分区。
        overrides.get("source_file_limits", {})  # 原始源码尺寸配置。
        if isinstance(overrides.get("source_file_limits", {}), dict)  # 映射类型检查。
        else {}  # 损坏配置使用空合同。
    )

    # 章节名称不含 Markdown 标题前缀，检查时统一补齐。
    required_sections = source_limits.get("required_plan_sections", [])  # 必需计划章节名。

    # 所有配置章节都出现时才允许超限文件继续存在。
    return all(f"## {section}" in text for section in required_sections)

# 收集超过硬字节上限且没有有效分解计划的源码。
def oversized_source_files(
    root: Path,
    config: dict[str, Any],
    *,
    prefix: str = "",
    project_root: Path | None = None,
    source_relative_prefix: str = "",
) -> list[dict[str, Any]]:
    """检查指定扫描根中的源码文件字节规模。

    参数：root 为扫描根，config 为治理配置，prefix 为报告前缀，project_root 为计划根，source_relative_prefix 为源码映射前缀。
    返回：每个未获计划豁免的超限文件诊断。
    """

    # 零上限由配置验证负责，本函数按给定整数执行比较。
    int_max_bytes = int(config.get("max_bytes", 0))  # 单文件允许的最大字节数。

    # 扩展名统一为小写，确保 Windows 和 Linux 扫描口径一致。
    extensions = {  # 触发尺寸硬门禁的源码扩展名。
        str(item).lower()  # 当前配置扩展名。
        for item in config.get("hard_fail_extensions", [])  # 原始硬门禁扩展名。
    }

    # 诊断列表沿用候选文件排序，保持输出稳定。
    list_violations: list[dict[str, Any]] = []  # 超限源码诊断。

    # 每个候选文件先按扩展名筛选，再读取实际字节数。
    for path in iter_candidate_files(root, config):

        # 非硬门禁扩展名不参与源码规模阻断。
        if path.suffix.lower() not in extensions:

            # 跳过文档、数据和其他未配置文件类别。
            continue

        # 原始字节数是当前文件的权威规模证据。
        int_count = byte_count(path)  # 当前文件字节数。

        # 未超过限制的文件无需查找分解计划。
        if int_count <= int_max_bytes:

            # 继续评估下一个候选源码。
            continue

        # 扫描根相对路径用于报告和发布副本映射。
        str_rel_path = relative_path(path, root)  # 当前超限源码相对路径。

        # 发布副本可映射回仓库源码位置以复用分解计划。
        plan_rel_path = (
            f"{source_relative_prefix.rstrip('/')}/{str_rel_path}"  # 仓库源码映射路径。
            if source_relative_prefix  # 发布扫描提供源码前缀时使用映射。
            else str_rel_path  # 普通项目扫描直接使用相对路径。
        )  # 分解计划查询路径。

        # 有效分解计划允许超限文件在受控迁移期继续存在。
        if project_root is not None and has_valid_decomposition_plan(
            project_root, plan_rel_path
        ):

            # 已治理的超限文件不写入硬失败清单。
            continue

        # 发布包或技能子目录前缀只影响报告展示路径。
        if prefix:

            # 前缀拼接后诊断可定位实际扫描副本。
            str_rel_path = f"{prefix}/{str_rel_path}"  # 带扫描上下文的报告路径。

        # 记录实际值与上限，便于制定分解计划。
        list_violations.append(
            {"path": str_rel_path, "byte_count": int_count, "max_bytes": int_max_bytes}
        )

    # 返回全部未获计划豁免的超限文件。
    return list_violations

# 统计单行中常见代码分隔符数量以识别压缩源码。
def minified_marker_count(line: str) -> int:
    """统计代码行中的结构分隔符数量。

    参数：line 为单个物理文本行。
    返回：花括号、分号、逗号和圆括号出现总数。
    """

    # 多类分隔符密集出现是压缩或混淆代码的稳定信号。
    return sum(line.count(marker) for marker in ("{", "}", ";", ",", "(", ")"))

# 检查物理长行、单行压缩文件和高密度混淆行。
def readability_violations(
    root: Path, config: dict[str, Any], *, prefix: str = ""
) -> list[dict[str, str]]:
    """执行跨语言源码可读性硬门禁。

    参数：root 为扫描根，config 为治理配置，prefix 为报告路径前缀。
    返回：物理长行、单行压缩或密集混淆诊断。
    """

    # readability_gate 分区控制阈值和总开关。
    gate = config.get("readability_gate", {})  # 原始可读性门禁配置。

    # 关闭或类型损坏的门禁不扫描文件内容。
    if not isinstance(gate, dict) or not gate.get("enabled"):

        # 返回空诊断保持调用方聚合 schema 稳定。
        return []

    # 可读性检查沿用源码尺寸硬门禁的扩展名范围。
    extensions = {  # 参与可读性扫描的源码扩展名。
        str(item).lower()  # 当前可读性扩展名。
        for item in config.get("hard_fail_extensions", [])  # 可读性沿用的扩展列表。
    }

    # 物理行阈值按原始字节计数，覆盖多字节文本风险。
    int_max_line_bytes = int(gate.get("max_physical_line_bytes", 0))  # 单行字节上限。

    # 单行文件达到该规模后视为压缩源码。
    int_single_line_min_bytes = int(gate.get("single_line_min_bytes", 0))  # 单行压缩判定下限。

    # 密度分析只针对足够长的行，避免误报正常表达式。
    int_minified_line_min_bytes = int(  # 密集行分析最小字节数。
        gate.get("minified_line_min_bytes", 1000)  # 原始密集行阈值。
    )

    # 每个文件可报告长行、单行压缩和密集行三类问题。
    list_violations: list[dict[str, str]] = []  # 可读性违规诊断。

    # 遍历经过排除目录过滤的全部候选文件。
    for path in iter_candidate_files(root, config):

        # 未配置为源码硬门禁的扩展名不读取内容。
        if path.suffix.lower() not in extensions:

            # 跳过非源码或项目未纳入治理的文件。
            continue

        # 相对路径作为所有可读性诊断的文件标识。
        str_rel_path = relative_path(path, root)  # 当前源码报告路径。

        # 发布副本扫描时追加实际包内路径前缀。
        if prefix:

            # 展示路径变化不影响文件读取和阈值计算。
            str_rel_path = f"{prefix}/{str_rel_path}"  # 带发布上下文的报告路径。

        # 原始字节同时用于总规模和物理行长度计算。
        raw = path.read_bytes()  # 当前文件原始内容。

        # 文本解码仅用于非空行与分隔符密度分析。
        text = raw.decode("utf-8", errors="ignore")  # 容错解码后的源码文本。

        # 原始行保留准确的多字节长度。
        raw_lines = raw.splitlines()  # 当前文件物理字节行。

        # 长度列表与物理行号保持一一对应。
        byte_lengths = [len(line) for line in raw_lines]  # 每行原始字节数。

        # 空白行不计入单行压缩文件判定。
        non_empty_lines = [  # 解码文本中的非空物理行。
            line  # 当前非空文本行。
            for line in text.splitlines()  # 当前文件解码物理行。
            if line.strip()  # 排除纯空白物理行。
        ]

        # 文件总字节数用于单行压缩规模门槛。
        total_bytes = len(raw)  # 当前源码总字节数。

        # 第一处物理长行足以证明该文件违反可读性门禁。
        for line_no, length in enumerate(byte_lengths, start=1):

            # 阈值为正且当前行超限时登记诊断。
            if int_max_line_bytes > 0 and length > int_max_line_bytes:

                # 消息同时提供实际长度和配置上限。
                list_violations.append(
                    {
                        "path": str_rel_path,
                        "message": f"physical line {line_no} is {length} bytes (limit {int_max_line_bytes})",
                    }
                )

                # 同一文件只报告首个物理长行，控制输出规模。
                break

        # 只有一个非空行的大文件属于明显压缩源码。
        if len(non_empty_lines) == 1 and total_bytes >= int_single_line_min_bytes:

            # 单行压缩诊断记录文件总字节数。
            list_violations.append(
                {
                    "path": str_rel_path,
                    "message": f"one-line compressed source is not allowed ({total_bytes} bytes)",
                }
            )

        # 每个文本行进一步执行密度启发式检查。
        for line_no, line in enumerate(text.splitlines(), start=1):

            # 优先使用原始字节行，异常边界回退到重新编码长度。
            line_bytes = (  # 当前物理行字节数。
                len(raw_lines[line_no - 1])  # 与解码行对应的原始长度。
                if line_no <= len(raw_lines)  # 原始行索引仍在范围内。
                else len(line.encode("utf-8"))  # 解码产生额外行时的安全回退。
            )

            # 短于密度分析门槛的行不可能触发混淆规则。
            if line_bytes < int_minified_line_min_bytes:

                # 继续检查后续更长的物理行。
                continue

            # 结构分隔符数量与行长度共同衡量代码密度。
            int_marker_count = minified_marker_count(line)  # 当前行代码分隔符总数。

            # 绝对数量或相对密度任一过高都视为压缩混淆。
            if int_marker_count >= 80 or int_marker_count / max(line_bytes, 1) >= 0.08:

                # 报告首个密集行并保留物理行号。
                list_violations.append(
                    {
                        "path": str_rel_path,
                        "message": f"minified or obfuscated dense line {line_no} is not allowed",
                    }
                )

                # 同一文件无需继续枚举更多密集行。
                break

    # 返回所有候选文件的可读性诊断。
    return list_violations

# 判断源码路径是否命中只能出现在测试树中的模式。
def path_matches_test_only(rel_path: str, config: dict[str, Any]) -> str:
    """返回候选路径命中的测试专用 glob。

    参数：rel_path 为源码相对路径，config 为治理配置。
    返回：首个命中模式；未命中时返回空字符串。
    """

    # 类型损坏的测试模式分区按空配置处理。
    patterns = (  # 经过类型收窄的测试专用模式配置。
        config.get("test_only_patterns", {})  # 原始测试边界分区。
        if isinstance(config.get("test_only_patterns", {}), dict)  # 仅接受映射。
        else {}  # 无效配置不匹配任何路径。
    )

    # 路径 glob 按配置顺序检查并返回首个具体证据。
    for pattern in patterns.get("path_globs", []):

        # 统一 glob 分隔符以匹配 POSIX 相对路径。
        normalized = str(pattern).replace("\\", "/")  # 当前测试专用 glob。

        # fnmatch 支持配置中的通配路径合同。
        if fnmatch.fnmatch(rel_path, normalized):

            # 返回命中模式供违规报告解释具体边界。
            return normalized

    # 所有模式均未命中时路径可按普通源码处理。
    return ""

# 识别技能源码或发布副本中的 scripts/python 运行时模块。
def is_python_runtime_script(rel_path: str) -> bool:
    """判断相对路径是否位于 scripts/python 且为 Python 文件。

    参数：rel_path 为候选源码相对路径。
    返回：命中运行时目录边界并以 .py 结尾时为 True。
    """

    # 使用统一分隔符识别 skill runtime 和 release runtime 下的 Python 脚本。
    parts = rel_path.replace("\\", "/").split("/")  # 定位 scripts/python 边界的路径片段。

    # 逐段查找 scripts/python，避免把普通源码目录误判为运行时脚本。
    for index in range(max(len(parts) - 1, 0)):

        # scripts/python 成对出现时才进入运行时脚本命名约束。
        if parts[index] == "scripts" and parts[index + 1] == "python":

            # 只有 Python 文件参与本次功能化命名约束。
            return rel_path.endswith(".py")

    # 未命中 runtime Python 目录时不参与该门禁。
    return False

# 解释运行时模块名是否仍使用无语义的编号分片。
def numbered_python_module_reason(module_name: str) -> str:
    """检查 Python 模块 basename 的编号分片命名。

    参数：module_name 为包含或不包含扩展名的模块名。
    返回：编号分片错误说明；功能命名返回空字符串。
    """

    # 去掉扩展名后检查纯数字、part 数字，以及下划线连接的 part 数字尾缀。
    stem = Path(module_name).stem  # 用于识别顺序编号分片的模块名主体。

    # 编号式模块名缺少功能语义，后续维护者无法从文件名判断职责。
    if NUMBERED_PYTHON_MODULE_RE.fullmatch(stem):

        # 返回调用方可以直接展示的命名错误说明。
        return "Python runtime module name uses a numbered shard suffix; use a functional name"

    # 功能化模块名不产生命名违规。
    return ""

# 收集 scripts/python 运行时模块的功能化命名违规。
def functional_naming_violations(
    root: Path, config: dict[str, Any], *, prefix: str = ""
) -> list[dict[str, str]]:
    """兼容旧报告字段并委托统一文件命名门禁。

    参数：
        root: 需要扫描的工作文件夹根目录。
        config: 已解析的源码治理配置。
        prefix: 报告路径需要附加的显示前缀。
    返回：统一文件命名门禁产生的稳定违规记录。
    """

    # 旧调用入口与新门禁共享实现，避免两个规则集合发生漂移。
    return file_naming_violations(root, config, prefix=prefix)

# 文件命名候选保留生产源码，并额外纳入根 tests 下的 Python 文件。
def iter_naming_files(root: Path, config: dict[str, Any]) -> list[Path]:
    """返回需要执行文件命名检查的源码与 Python 测试。

    参数：
        root: 受管工作文件夹根目录。
        config: 包含源码后缀和排除根目录的治理配置。
    返回：按相对路径排序的文件命名检查候选。
    """

    # 后缀集合沿用源码治理合同，保证不同语言接受同一命名规则。
    set_extensions = {str(item).lower() for item in config.get("hard_fail_extensions", [])}  # 受管源码后缀

    # tests 必须纳入检查，其余治理排除根保持原有边界。
    set_excluded = {  # 不参与功能源码文件名检查的治理根目录
        str(item).strip("/\\")  # 统一排除根的相对路径表示
        for item in config.get("excluded_roots", [])  # 读取项目声明的全部排除根
        if str(item).strip("/\\") != "tests"  # 强制保留根级 tests 命名检查
    }  # 去除 tests 后的有效命名扫描排除集合

    # 候选列表在扫描结束后统一排序，消除文件系统遍历差异。
    list_files: list[Path] = []  # 需要执行文件名门禁的实际文件

    # 递归遍历工作文件夹，同时按后缀和 tests 特例筛选候选。
    for path in root.rglob("*"):

        # 目录和其他非文件条目不参与文件名规则。
        if not path.is_file():

            # 跳过非文件后继续检查下一个遍历结果。
            continue

        # 相对路径部分用于识别顶层排除根和根级 tests。
        tuple_parts = path.relative_to(root).parts  # 当前文件的仓库相对路径部分

        # 受保护或生成目录保持治理排除，不混入功能源码命名结果。
        if tuple_parts and tuple_parts[0] in set_excluded:

            # 排除根内文件由其专用治理规则负责。
            continue

        # tests 中只有 Python 文件属于当前测试命名合同。
        bool_test_python = bool(  # 当前路径是否属于根级 tests 内的 Python 测试
            tuple_parts  # 路径必须含有顶层目录
            and tuple_parts[0] == "tests"  # 测试必须位于唯一根级 tests
            and path.suffix.lower() == ".py"  # 当前规则只覆盖 Python 测试
        )  # 当前候选是否为根级 tests 下的 Python 文件

        # 测试 Python 或配置声明的源码后缀进入确定性命名检查。
        if bool_test_python or path.suffix.lower() in set_extensions:

            # 保存真实路径供后续统一生成相对诊断。
            list_files.append(path)

    # 稳定排序确保相同工作树产生相同违规顺序。
    return sorted(list_files)

# 单文件诊断采用稳定代码，便于 CLI、测试和 Agent 语义复核共享。
def file_name_violation(path: Path, gate: dict[str, Any]) -> tuple[str, str]:
    """返回文件名的首个确定性违规代码和说明。

    参数：
        path: 需要检查的源码或 Python 测试路径。
        gate: 文件命名门禁的不可弱化配置。
    返回：首个违规的稳定代码与英文机器诊断；通过时均为空字符串。
    """

    # 初始化文件等明确豁免项不承担功能摘要命名职责。
    if path.name in gate.get("exemptions", []):

        # 空代码和空消息表示确定性规则通过。
        return "", ""

    # 文件词干是数字、前导字符、长度和模式检查的共同输入。
    str_stem = path.stem  # 不含扩展名的文件名称

    # 任意数字都会形成版本号或顺序编号歧义。
    if re.search(r"\d", str_stem):

        # 稳定代码便于 CLI、评测和审查证据共同断言。
        return "digit-forbidden", "file name stem must not contain digits"

    # 前导下划线会把功能文件伪装成内部实现分片。
    if str_stem.startswith("_"):

        # 返回专门代码，避免与普通字符模式错误混淆。
        return "leading-underscore", "file name stem must not start with underscore"

    # 词干长度超过配置上限时不能保持简洁可识别。
    if len(str_stem) > int(gate.get("max_stem_chars", 30)):

        # 长度诊断保持用户要求的三十字符边界。
        return "stem-too-long", "file name stem exceeds the 30 character limit"

    # Python 与其他源码分别读取配置中的合法字符模式。
    str_pattern = (
        str(gate.get("python_pattern", ""))  # Python 文件允许测试前缀和功能单词
        if path.suffix.lower() == ".py"  # 根据真实扩展名选择规则
        else str(gate.get("source_pattern", ""))  # 其他源码只允许功能化小写单词
    )  # 当前文件词干必须满足的完整正则表达式

    # 不符合语言模式的词干缺少稳定的小写功能命名结构。
    if not re.fullmatch(str_pattern, str_stem):

        # 字符模式错误作为最后一个确定性语法诊断返回。
        return "invalid-stem-chars", "file name stem must use lowercase functional words"

    # 所有确定性语法规则通过时不产生违规。
    return "", ""

# 统一扫描源码和 Python 测试的确定性文件命名违规。
def file_naming_violations(
    root: Path, config: dict[str, Any], *, prefix: str = ""
) -> list[dict[str, str]]:
    """收集数字、前导下划线、超长和字符模式违规。

    参数：
        root: 需要扫描的工作文件夹根目录。
        config: 包含文件命名门禁的源码治理配置。
        prefix: 报告路径需要附加的显示前缀。
    返回：按候选路径顺序排列的确定性文件命名违规。
    """

    # 配置对象决定门禁开关、豁免项、长度与字符模式。
    dict_gate = config.get("file_naming_gate", {})  # 当前项目文件命名门禁配置

    # 缺失、错误类型或显式关闭时保持向后兼容的空报告。
    if not isinstance(dict_gate, dict) or not dict_gate.get("enabled"):

        # 未启用门禁时不扫描文件系统。
        return []

    # 违规列表保留候选扫描顺序，便于稳定比较评测结果。
    list_violations: list[dict[str, str]] = []  # 文件命名违规记录

    # 每个候选文件只报告首个确定性命名错误。
    for path in iter_naming_files(root, config):

        # 元组结果同时携带稳定代码和机器诊断文本。
        tuple_violation = file_name_violation(path, dict_gate)  # 当前文件的首个命名违规

        # 分别提取代码和消息，避免解包变量被误判为元组类型。
        str_code = tuple_violation[0]  # 当前文件的稳定违规代码

        # 消息与代码保持同一规则来源，供 CLI 直接输出。
        str_message = tuple_violation[1]  # 当前文件的机器可读诊断文本

        # 空代码表示当前文件满足所有确定性命名规则。
        if not str_code:

            # 跳过通过项，报告只保留需要修复的文件。
            continue

        # 统一相对路径使报告不泄露本机工作目录。
        str_relative = relative_path(path, root)  # 当前违规文件的根目录相对路径

        # 发布副本扫描可附加前缀，本地扫描保持原始相对路径。
        str_display = f"{prefix}/{str_relative}" if prefix else str_relative  # 最终展示路径

        # 聚合稳定字段，供源码门禁、审查和评测共同消费。
        list_violations.append(
            {"path": str_display, "code": str_code, "message": str_message}
        )

    # 返回完成扫描后的全部确定性命名违规。
    return list_violations

# 收集落在生产源码树中的测试专用文件。
def test_code_boundary_violations(
    root: Path, config: dict[str, Any], *, prefix: str = ""
) -> list[dict[str, str]]:
    """检查测试设计代码是否越过生产源码边界。

    参数：root 为扫描根，config 为治理配置，prefix 为报告前缀。
    返回：命中测试专用模式的文件与模式列表。
    """

    # 报告保留候选文件排序和首个命中模式。
    list_violations: list[dict[str, str]] = []  # 测试边界违规。

    # 所有候选文件都以规范化相对路径匹配 glob。
    for path in iter_candidate_files(root, config):

        # 扫描根相对路径与配置 glob 使用同一分隔符。
        str_rel_path = relative_path(path, root)  # 当前候选文件路径。

        # 返回值同时表示是否违规及具体命中证据。
        str_matched = path_matches_test_only(str_rel_path, config)  # 命中的测试专用模式。

        # 普通生产源码不写入测试边界报告。
        if not str_matched:

            # 普通生产文件继续后续边界扫描。
            continue

        # 发布副本扫描时在路径前加入包内上下文。
        full_path = f"{prefix}/{str_rel_path}" if prefix else str_rel_path  # 违规展示路径。

        # 同时记录文件和触发边界规则的 glob。
        list_violations.append({"path": full_path, "pattern": str_matched})

    # 返回全部生产树测试代码违规。
    return list_violations

# 解析 Python 语法树并标记赋值语句覆盖的物理行。
def python_assignment_comment_lines(text: str) -> set[int]:
    """计算赋值语句覆盖的全部源码行号。

    参数：text 为 Python 源码文本。
    返回：Assign、AnnAssign 与 AugAssign 节点覆盖的行号集合。
    """

    # 语法错误时无法可靠识别赋值尾注释例外。
    try:

        # 空文件使用换行占位，保持 ast.parse 输入有效。
        tree = ast.parse(text or "\n")  # Python 抽象语法树。

    # 语法错误由上层注释策略生成更具体的诊断。
    except SyntaxError:

        # 空集合表示不允许任何赋值尾注释例外。
        return set()

    # 集合合并多行赋值范围并自动去重。
    set_assignment_lines: set[int] = set()  # 赋值节点覆盖的物理行号。

    # 遍历完整语法树以覆盖函数、类和模块级赋值。
    for node in ast.walk(tree):

        # 其他语句类型不能获得赋值尾注释例外。
        if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):

            # 跳过表达式、控制流和定义节点。
            continue

        # 起始行缺失时使用零值，保持范围构造安全。
        start = getattr(node, "lineno", 0) or 0  # 当前赋值起始行。

        # 旧解释器缺少 end_lineno 时退化为单行赋值。
        end = getattr(node, "end_lineno", start) or start  # 当前赋值结束行。

        # 多行赋值的每个物理行都允许右侧用途注释。
        set_assignment_lines.update(range(start, end + 1))

    # 返回词法扫描可直接执行成员判断的行号集合。
    return set_assignment_lines

# 公共 API docstring 扫描独立处理语法错误，不影响后续词法注释诊断。
def python_public_api_comment_violations(text: str) -> list[str]:
    """返回公共 Python 定义缺失 docstring 或语法损坏的诊断。

    参数：text 为待解析的 Python 源码文本。
    返回：语法错误或公共定义 docstring 违规列表。
    """

    # 语法损坏时不能可靠遍历公共定义，必须转换为治理诊断。
    try:

        # 空源码使用换行占位，保持解析器输入有效。
        tree = ast.parse(text or "\n")  # 用于定位公共定义的语法树。

    # 语法错误行号随稳定消息返回，不让整仓扫描中断。
    except SyntaxError as exc:

        # 缺失行号时使用零值保持诊断 schema 稳定。
        int_line_no = getattr(exc, "lineno", 0) or 0  # Python 语法错误行号。

        # 单条语法诊断解释公共 API 扫描无法继续。
        return [f"python syntax error prevents comment policy parsing (line {int_line_no})"]

    # 公共定义按语法树遍历顺序生成确定性诊断。
    list_violations: list[str] = []  # 公共 API docstring 违规列表。

    # 嵌套函数和类同样属于公共定义检查范围。
    for node in ast.walk(tree):

        # 私有定义和非定义节点不得触发公共 API 合同。
        bool_is_public_definition = isinstance(  # 当前节点是否为公共定义。
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)  # 支持的定义节点类型。
        ) and not node.name.startswith("_")  # 下划线前缀表示私有定义。

        # 缺失原始 docstring 的公共定义登记名称和物理行号。
        if bool_is_public_definition and ast.get_docstring(node, clean=False) is None:

            # 诊断直接定位源码定义，便于调用方修复。
            list_violations.append(
                f"public API `{node.name}` is missing a docstring (line {node.lineno})"
            )

    # 返回按语法树顺序收集的公共 API 诊断。
    return list_violations

# 单个注释 token 可同时触发尾注释与生成标记两类独立诊断。
def python_comment_token_violations(
    token: tokenize.TokenInfo,
    lines: list[str],
    python_gate: dict[str, Any],
    ai_markers: list[str],
    assignment_lines: set[int],
) -> list[str]:
    """检查一个 Python 注释 token 并返回策略诊断。

    参数：token 为注释 token，lines 为物理行，python_gate 为语言策略，
    ai_markers 为禁止标记，assignment_lines 为允许尾注释的赋值行。
    返回：当前注释 token 触发的有序诊断。
    """

    # 非空源码按 token 行号定位，空源码保留防御性回退。
    str_line_text = lines[token.start[0] - 1] if lines else ""  # 注释所在完整物理行。

    # 注释列之前存在非空源码时，该 token 属于尾注释候选。
    str_code_before_comment = str_line_text[: token.start[1]].strip()  # 注释前代码片段。

    # 尾注释和生成标记可在同一 token 上独立报告。
    list_violations: list[str] = []  # 当前 token 的策略违规。

    # 普通尾注释受禁止开关约束，同时尊重赋值用途例外。
    if (
        python_gate.get("forbid_trailing_comment", False)
        and str_code_before_comment
        and token.start[0] not in assignment_lines
    ):

        # token 起始行就是尾注释对应的物理行。
        list_violations.append(
            f"trailing Python comment is not allowed (line {token.start[0]})"
        )

    # 生成标记仅在注释 token 内容中执行不区分大小写匹配。
    if ai_markers and any(marker in token.string.lower() for marker in ai_markers):

        # 标记诊断与同一行可能存在的尾注释诊断并存。
        list_violations.append(
            f"AI-generated comment marker is not allowed (line {token.start[0]})"
        )

    # 返回当前 token 的零条、一条或两条诊断。
    return list_violations

# tokenize 扫描只处理真实注释 token，字符串内井号不参与策略匹配。
def python_token_comment_violations(
    text: str,
    python_gate: dict[str, Any],
    ai_markers: list[str],
) -> list[str]:
    """返回 Python 尾注释、生成标记和词法错误诊断。

    参数：text 为源码，python_gate 为语言策略，ai_markers 为禁止标记。
    返回：词法扫描产生的有序注释策略诊断。
    """

    # 赋值尾注释例外由 Python 策略显式控制。
    bool_allow_assignment = bool(  # 是否允许赋值用途尾注释。
        python_gate.get("allow_assignment_trailing_comment", False)  # 原始策略开关。
    )

    # 仅在例外启用时解析赋值覆盖行，避免不必要的 AST 遍历。
    set_assignment_lines = (  # 可接受赋值尾注释的物理行号。
        python_assignment_comment_lines(text)  # 从语法树提取赋值行。
        if bool_allow_assignment  # 策略允许赋值尾注释。
        else set()  # 禁用例外时不放行任何行。
    )

    # token 坐标通过物理行列表映射回完整源码行。
    list_lines = text.splitlines()  # Python 源码物理行。

    # 全部 token 诊断按词法顺序追加。
    list_violations: list[str] = []  # 当前源码的词法注释违规。

    # 未闭合结构等 TokenError 必须转换为治理诊断。
    try:

        # tokenize 能排除字符串中的井号并识别真正注释。
        for token in tokenize.generate_tokens(io.StringIO(text).readline):

            # 非注释 token 不参与本策略检查。
            if token.type != tokenize.COMMENT:

                # 继续读取后续词法 token。
                continue

            # 当前注释的独立诊断追加到文件级结果。
            list_violations.extend(
                python_comment_token_violations(
                    token, list_lines, python_gate, ai_markers, set_assignment_lines
                )
            )

    # 词法错误不应中断其他文件的聚合扫描。
    except tokenize.TokenError as exc:

        # TokenError 第二参数只有在非空元组时才可读取行号。
        bool_has_coordinates = (  # 当前异常是否携带有效坐标。
            len(exc.args) > 1  # 至少包含消息与坐标两个参数。
            and isinstance(exc.args[1], tuple)  # 坐标必须为元组。
            and bool(exc.args[1])  # 坐标元组不能为空。
        )

        # 缺失坐标时使用零值维持错误消息结构。
        int_line_no = exc.args[1][0] if bool_has_coordinates else 0  # Python 词法错误行号。

        # 说明词法失败阻止了完整注释策略扫描。
        list_violations.append(
            f"python tokenize error prevents comment policy parsing (line {int_line_no})"
        )

    # 返回尾注释、生成标记和词法错误三类诊断。
    return list_violations

# 提取 Python 公共 API、尾注释与生成标记违规。
def extract_python_comment_violations(path: Path, config: dict[str, Any]) -> list[str]:
    """检查单个 Python 文件的项目注释策略。

    参数：path 为待检查文件，config 为源码治理配置。
    返回：包含物理行号的注释策略违规说明。
    """

    # 容错读取让损坏源码仍能产生语法或词法诊断。
    text = path.read_text(encoding="utf-8", errors="ignore")  # 待扫描源码文本。

    # 注释策略根分区提供语言策略与跨语言禁止标记。
    gate = config.get("comment_policy_gate", {})  # 聚合扫描启用配置。

    # Python 分区必须为映射，损坏配置按空策略处理。
    raw_python_gate = gate.get("python", {})  # 原始 Python 策略分区。

    # 类型收窄后辅助函数无需重复防御配置结构。
    python_gate = raw_python_gate if isinstance(raw_python_gate, dict) else {}  # Python 专用策略。

    # 统一为小写后执行不区分大小写的生成标记匹配。
    list_ai_markers = [  # 禁止出现在源码注释中的生成标记。
        str(item).lower()  # 当前规范化标记。
        for item in gate.get("forbid_ai_comment_markers", [])  # 原始禁止标记列表。
    ]

    # 诊断顺序保持公共 API 检查先于词法注释检查。
    list_violations: list[str] = []  # 当前文件注释策略违规。

    # 仅在配置明确启用时解析公共定义的 docstring。
    if python_gate.get("require_public_api_docstring", False):

        # 公共定义诊断先写入结果，保持历史排序合同。
        list_violations.extend(python_public_api_comment_violations(text))

    # 尾注释或生成标记任一启用时才运行 tokenize 扫描。
    if python_gate.get("forbid_trailing_comment", False) or list_ai_markers:

        # 词法诊断追加在公共 API 诊断之后。
        list_violations.extend(
            python_token_comment_violations(text, python_gate, list_ai_markers)
        )

    # 返回公共 API、尾注释和标记三类有序诊断。
    return list_violations

# 提取 C/C++ 单行与块注释的策略违规。
def extract_c_cpp_comment_violations(path: Path, config: dict[str, Any]) -> list[str]:
    """检查单个 C/C++ 文件的尾注释和生成标记。

    参数：path 为待检查文件，config 为源码治理配置。
    返回：包含物理行号的注释策略违规说明。
    """

    # 容错解码确保非 UTF-8 字节不会中断整仓治理扫描。
    text = path.read_text(encoding="utf-8", errors="ignore")  # 待扫描 C/C++ 文本。

    # 注释策略根分区提供跨语言共享的禁止标记。
    gate = config.get("comment_policy_gate", {})  # C/C++ 扫描共享策略根。

    # C/C++ 分区类型收窄后才参与尾注释判断。
    c_cpp_gate = (  # 已验证的 C/C++ 策略映射。
        gate.get("c_cpp", {})  # 配置中的 C/C++ 原始内容。
        if isinstance(gate.get("c_cpp", {}), dict)  # 仅接受映射值。
        else {}  # 非映射 C/C++ 配置关闭语言专用规则。
    )

    # 标记规范化后与注释子串执行不区分大小写匹配。
    list_ai_markers = [  # 禁止出现在 C/C++ 注释中的生成标记。
        str(item).lower()  # 当前 C/C++ 禁止标记的小写形式。
        for item in gate.get("forbid_ai_comment_markers", [])  # 跨语言禁止标记源。
    ]

    # 每条诊断只描述单个物理行上的单个策略失败。
    list_violations: list[str] = []  # 当前 C/C++ 文件策略违规。

    # 两类检查均关闭时无需读取行级结构。
    if not c_cpp_gate.get("forbid_trailing_comment", False) and not list_ai_markers:

        # 空列表保持调用方聚合逻辑稳定。
        return list_violations

    # 当前策略按物理行识别最早出现的 // 或 /* 起点。
    for int_line_no, str_line in enumerate(text.splitlines(), start=1):

        # 去除外围空白用于空行和预处理器例外判断。
        str_stripped = str_line.strip()  # 当前行规范化文本。

        # 空白行不可能包含可执行代码后的注释。
        if not str_stripped:

            # 继续检查下一物理行。
            continue

        # 分别定位两种注释起始符，缺失时返回负值。
        int_line_comment_index = str_line.find("//")  # 单行注释起始列。

        # 块注释起点同样可能形成行尾解释。
        int_block_comment_index = str_line.find("/*")  # 块注释起始列。

        # 仅保留真实命中的索引，随后选择物理行最早注释。
        list_indexes = [  # C/C++ 尾注释判定使用的注释起始列集合。
            index  # 保留当前真实存在的注释开放符列号。
            for index in [  # 单行与块注释边界候选。
                int_line_comment_index,  # 双斜线注释开放符所在物理列。
                int_block_comment_index,  # 斜星块注释开放符所在物理列。
            ]
            if index >= 0  # 过滤 find 返回的未命中负值。
        ]

        # 没有注释起始符时本行无需检查。
        if not list_indexes:

            # 继续扫描下一物理行。
            continue

        # 最早注释决定代码前缀和标记检查的切分位置。
        int_comment_index = min(list_indexes)  # 当前行首个注释起始列。

        # 宏定义允许保留同一行注释，避免误伤预处理器合同。
        if (
            c_cpp_gate.get("forbid_trailing_comment", False)
            and str_line[:int_comment_index].strip()
            and not str_stripped.startswith("#define")
        ):

            # 报告当前物理行上的普通尾注释违规。
            list_violations.append(
                f"trailing C/C++ comment is not allowed (line {int_line_no})"
            )

        # 只扫描首个注释起点后的文本，代码字符串不进入本启发式。
        if list_ai_markers and any(
            marker in str_line[int_comment_index:].lower()
            for marker in list_ai_markers
        ):

            # 生成标记诊断与尾注释诊断保持独立。
            list_violations.append(
                f"AI-generated comment marker is not allowed (line {int_line_no})"
            )

    # 返回物理行顺序稳定的 C/C++ 注释诊断。
    return list_violations

# 汇总候选源码中的语言专用注释策略违规。
def comment_policy_violations(
    root: Path, config: dict[str, Any], *, prefix: str = ""
) -> list[dict[str, str]]:
    """扫描源码树并为每条注释违规补充文件路径。

    参数：root 为扫描根，config 为治理配置，prefix 为报告路径前缀。
    返回：包含 path 与 message 的注释策略违规列表。
    """

    # 根门禁决定是否启用所有语言的注释策略扫描。
    gate = config.get("comment_policy_gate", {})  # 注释策略根配置。

    # 缺失、损坏或关闭的配置均不产生注释诊断。
    if not isinstance(gate, dict) or not gate.get("enabled"):

        # 返回空列表保持源码报告 schema 稳定。
        return []

    # 候选文件顺序决定最终诊断顺序。
    list_violations: list[dict[str, str]] = []  # 带文件上下文的注释违规。

    # 遍历已经应用排除根和目录规则的源码候选。
    for path in iter_candidate_files(root, config):

        # 非 Python/C/C++ 扩展名不进入语言注释扫描器。
        if path.suffix.lower() not in COMMENT_CHECK_EXTENSIONS:

            # 跳过不属于受管注释语言的文件。
            continue

        # 单文件扫描器只返回消息，路径由本层统一补充。
        list_messages: list[str] = []  # 当前文件的注释违规消息。

        # Python 使用 tokenize 与 AST 组合检查，避免把字符串误判为注释。
        if path.suffix.lower() == ".py":

            # 追加公共 API、尾注释和生成标记诊断。
            list_messages.extend(extract_python_comment_violations(path, config))

        # C/C++ 扩展名共享轻量的物理行扫描合同。
        else:

            # C/C++ 扫描补充尾注释和标记诊断。
            list_messages.extend(extract_c_cpp_comment_violations(path, config))

        # 报告默认使用扫描根相对路径，避免暴露机器绝对路径。
        str_rel_path = relative_path(path, root)  # 当前候选文件报告路径。

        # 发布副本扫描需要保留 dist 内的包路径上下文。
        if prefix:

            # 发布路径前缀只改变诊断展示上下文。
            str_rel_path = f"{prefix}/{str_rel_path}"  # 注释诊断的包内路径。

        # 单文件消息逐条转换为统一结构化诊断。
        for str_message in list_messages:

            # 路径和消息字段供文本与 JSON 报告共同消费。
            list_violations.append(
                {"path": str_rel_path, "message": str_message}
            )

    # 返回所有受管语言文件的注释策略违规。
    return list_violations

# 编排工作树源码治理的全部检查分区。
def source_governance_report(
    project: Path, profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    """生成项目工作树的结构化源码治理报告。

    参数：project 为项目根，profile 为可选控制配置。
    返回：配置证据、五类违规、错误和总体状态。
    """

    # 有效配置同时包含来源路径、选择结果与配置错误。
    dict_effective = effective_source_governance(project, profile)  # 生效治理上下文。

    # 各检查器共享同一份已经验证和合并的配置。
    dict_config = dict_effective["config"]  # 生效源码治理配置。

    # 尺寸门禁同时验证超限文件是否具备有效分解计划。
    list_oversized = oversized_source_files(  # 源码尺寸违规。
        project,  # 边界检查工作树根。
        dict_config,  # 生效尺寸配置。
        project_root=project,  # 分解计划查找根。
    )

    # 测试边界阻止 fixture 或测试设计代码落入生产树。
    list_boundary = test_code_boundary_violations(  # 测试代码边界违规。
        project,  # 注释检查工作树根。
        dict_config,  # 生效边界配置。
    )

    # 注释策略覆盖公共 API、尾注释与生成标记。
    list_comments = comment_policy_violations(  # 注释策略违规。
        project,  # 可读性检查工作树根。
        dict_config,  # 生效注释配置。
    )

    # 可读性检查覆盖物理长行、单行压缩和密集混淆源码。
    list_readability = readability_violations(  # 源码可读性违规。
        project,  # 工作树扫描根。
        dict_config,  # 生效可读性配置。
    )

    # 工作树源码与 Python 测试执行统一功能命名约束。
    list_naming = file_naming_violations(  # 工作树文件命名违规。
        project,  # 命名检查工作树根。
        dict_config,  # 生效命名配置。
    )

    # 配置错误复制后可安全地作为报告公共字段返回。
    list_errors = list(dict_effective["errors"])  # 配置加载与校验错误。

    # 所有分区均为空时总体状态才可判定为通过。
    return {
        "project": str(project),
        "config_path": str(dict_effective["config_path"]),
        "config_source": dict_effective["config_source"],
        "config_errors": list(dict_effective["errors"]),
        "oversized_source_files": list_oversized,
        "test_code_boundary_violations": list_boundary,
        "comment_policy_violations": list_comments,
        "readability_violations": list_readability,
        "functional_naming_violations": list_naming,
        "file_naming_violations": list_naming,
        "errors": list_errors,
        "ok": not (
            list_errors
            or list_oversized
            or list_boundary
            or list_comments
            or list_readability
            or list_naming
        ),
    }

# 编排版本化发布目录的源码治理复核。
def release_source_governance_report(
    project: Path,
    release_dir: Path,
    profile: dict[str, Any] | None = None,
    *,
    source_relative_prefix: str = "",
) -> dict[str, Any]:
    """生成发布副本的结构化源码治理报告。

    参数：project 为仓库根，release_dir 为发布目录，profile 为可选控制配置，
    source_relative_prefix 为发布文件映射回源树时的相对前缀。
    返回：带发布路径上下文的源码治理报告。
    """

    # 发布检查与工作树检查使用同一治理配置来源。
    dict_effective = effective_source_governance(  # 发布治理上下文。
        project,  # 仓库配置来源根。
        profile,  # 可选控制配置。
    )

    # 浅复制允许发布扫描覆盖排除根而不修改源报告配置。
    dict_config = dict(dict_effective["config"])  # 发布扫描专用配置副本。

    # 发布目录已经是封闭边界，不能再次排除包内同名路径。
    dict_config["excluded_roots"] = []  # 发布扫描不继承仓库根排除项。

    # 包内相对路径优先；外部临时目录回退到发布目录名。
    str_prefix = (  # 发布报告的统一路径前缀。
        release_dir.relative_to(project).as_posix()  # 仓库内发布相对路径。
        if release_dir.is_relative_to(project)  # 发布目录位于仓库内。
        else release_dir.name  # 仓库外发布目录使用 basename。
    )

    # 尺寸检查可通过源相对前缀定位仓库中的分解计划。
    list_oversized = oversized_source_files(  # 发布副本尺寸违规。
        release_dir,  # 发布副本扫描根。
        dict_config,  # 清除排除根后的尺寸配置。
        prefix=str_prefix,  # 尺寸报告包内前缀。
        project_root=project,  # 分解计划仍从仓库根查找。
        source_relative_prefix=source_relative_prefix,  # 发布内容到源树的映射前缀。
    )

    # 包内测试专用文件仍不得混入生产 runtime。
    list_boundary = test_code_boundary_violations(  # 发布测试边界违规。
        release_dir,  # 边界检查发布根。
        dict_config,  # 发布边界配置。
        prefix=str_prefix,  # 边界报告包内前缀。
    )

    # 发布内容必须独立满足注释策略，不能只依赖源树结果。
    list_comments = comment_policy_violations(  # 发布注释策略违规。
        release_dir,  # 注释检查发布根。
        dict_config,  # 发布注释配置。
        prefix=str_prefix,  # 注释报告包内前缀。
    )

    # 打包过程不得引入长行、压缩或混淆形式。
    list_readability = readability_violations(  # 发布可读性违规。
        release_dir,  # 可读性检查发布根。
        dict_config,  # 发布可读性配置。
        prefix=str_prefix,  # 可读性报告包内前缀。
    )

    # 发布包源码与 Python 测试继续执行功能化命名约束。
    list_naming = file_naming_violations(  # 发布文件命名违规。
        release_dir,  # 命名检查发布根。
        dict_config,  # 发布命名配置。
        prefix=str_prefix,  # 命名报告包内前缀。
    )

    # 配置或任一发布内容分区失败时总体状态为 false。
    return {
        "project": str(project),
        "release_dir": str(release_dir),
        "config_path": str(dict_effective["config_path"]),
        "config_source": dict_effective["config_source"],
        "config_errors": list(dict_effective["errors"]),
        "oversized_source_files": list_oversized,
        "test_code_boundary_violations": list_boundary,
        "comment_policy_violations": list_comments,
        "readability_violations": list_readability,
        "functional_naming_violations": list_naming,
        "file_naming_violations": list_naming,
        "errors": list(dict_effective["errors"]),
        "ok": not (
            dict_effective["errors"]
            or list_oversized
            or list_boundary
            or list_comments
            or list_readability
            or list_naming
        ),
    }

# 将结构化源码治理诊断转换为 CLI 可读消息。
def format_source_governance_errors(
    report: dict[str, Any], *, prefix: str = "source governance"
) -> list[str]:
    """格式化源码治理报告中的全部失败项。

    参数：report 为源码治理报告，prefix 为每条消息的上下文前缀。
    返回：保持报告分区顺序的人类可读错误列表。
    """

    # 配置错误优先展示，因为它们可能影响后续检查覆盖范围。
    list_errors = [  # 已格式化的源码治理错误。
        f"{prefix}: {item}"  # 当前配置错误消息。
        for item in report.get("errors", [])  # 原始配置错误集合。
    ]

    # 尺寸错误同时展示实际值与配置阈值。
    for item in report.get("oversized_source_files", []):

        # 相邻字面量换行避免格式化消息本身违反源码长行门禁。
        list_errors.append(
            f"{prefix}: oversized file `{item['path']}` has "
            f"{item['byte_count']} bytes (limit {item['max_bytes']} bytes)"
        )

    # 测试边界错误保留触发违规的具体 glob。
    for item in report.get("test_code_boundary_violations", []):

        # 路径与模式共同提供可复核的边界证据。
        list_errors.append(
            f"{prefix}: test-only design code outside tests `{item['path']}` "
            f"matched `{item['pattern']}`"
        )

    # 注释诊断消息已经携带具体语言规则和物理行号。
    for item in report.get("comment_policy_violations", []):

        # 补充文件路径后即可直接用于 CLI 错误输出。
        list_errors.append(f"{prefix}: `{item['path']}` {item['message']}")

    # 可读性消息携带长行、压缩或密度违规细节。
    for item in report.get("readability_violations", []):

        # 统一前缀使调用方无需理解报告分区。
        list_errors.append(f"{prefix}: `{item['path']}` {item['message']}")

    # 文件命名消息说明确定性违规代码和对应职责名要求。
    for item in report.get(
        "file_naming_violations",
        report.get("functional_naming_violations", []),
    ):

        # 保持与其他文件级错误完全相同的展示结构。
        list_errors.append(f"{prefix}: `{item['path']}` {item['message']}")

    # 返回配置、尺寸、边界、注释、可读性与命名错误的有序集合。
    return list_errors
