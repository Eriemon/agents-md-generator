"""读取并验证版本化技能发布包的基础清单合同。"""

# 延迟注解避免运行时解析仅用于类型检查的标注。
from __future__ import annotations

# 标准库提供哈希、JSON、环境变量、路径与文本匹配能力。
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import re

# 兼容导出供尚未完成解耦的发布验证分片使用。
import shutil
import subprocess
import sys
from typing import Any

# 发布内容策略版本保持收据合同稳定。
POLICY_VERSION = "2026-05-26-v2"  # 当前收据记录的发布内容策略版本。

# 活跃会话状态属于运行时噪声，不应阻断发布仓库清洁性检查。
ACTIVE_SESSION_PATH = Path(".agents") / "active-session.json"  # 状态过滤器忽略的会话文件。

# 延迟导入器让脚本可从任意工作目录执行，同时避免导入期路径修改。
def load_task_module(str_module_name: str) -> Any:
    """从 scripts/python 的任务目录加载指定模块。

    参数：str_module_name 为不带路径和扩展名的模块名。
    返回：已导入的 Python 模块对象。
    """

    # 所有任务目录均位于当前 release 目录的同级位置。
    path_python_root = Path(__file__).resolve().parents[1]  # 跨任务模块查找的共同父目录。

    # 仅在实际需要跨任务能力时登记兄弟目录。
    for path_task_dir in path_python_root.iterdir():

        # 普通文件不是可搜索模块目录。
        if not path_task_dir.is_dir():

            # 继续检查下一个根目录成员。
            continue

        # Python 导入搜索路径使用字符串目录。
        str_task_dir = str(path_task_dir)  # 当前任务模块搜索目录。

        # 已登记目录无需重复插入。
        if str_task_dir in sys.path:

            # 继续检查下一个任务目录。
            continue

        # 运行期登记保持直接脚本执行兼容性。
        sys.path.insert(0, str_task_dir)

    # 路径就绪后按稳定模块名加载实现。
    return importlib.import_module(str_module_name)

# JSON 输出器保持发布入口标准输出只含机器载荷。
def emit_json(dict_data: dict[str, Any]) -> None:
    """把结构化对象以格式化 JSON 写入标准输出。

    参数：dict_data 为需要输出的机器可读对象。
    返回：无。
    """

    # 单次写入避免 print 前缀规则污染 JSON 协议。
    sys.stdout.write(json.dumps(dict_data, indent=2, ensure_ascii=False) + "\n")

# 版本策略包装器按需加载公共治理实现。
def version_policy_error(str_version: str) -> str:
    """返回版本号违反仓库策略时的诊断。

    参数：str_version 为 vX.Y.Z 版本文本。
    返回：策略通过时为空字符串，否则为错误说明。
    """

    # 公共版本策略仍是唯一规则来源。
    module_version_policy_context = load_task_module("version_policy")  # 版本策略实现模块。

    # 委托实现保持发布和安装规则一致。
    return str(module_version_policy_context.version_policy_error(str_version))

# 项目路径包装器保留安装入口的既有公开门面。
def resolve_project(object_raw_path: str | Path) -> Path:
    """使用公共路径规则解析项目根目录。

    参数：object_raw_path 为字符串或 Path 项目位置。
    返回：规范化项目根目录。
    """

    # 公共模块负责路径存在性和项目语义。
    module_agents_common_context = load_task_module("agents_common")  # 公共项目工具模块。

    # 返回公共解析器的 Path 结果。
    return Path(module_agents_common_context.resolve_project(object_raw_path))

# 全局 AGENTS 状态包装器延迟加载较重的公共治理模块。
def global_codex_agents_status(
    str_codex_home: str | None = None,
    path_project_root: Path | None = None,
    dict_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """读取全局 Codex AGENTS 的安装治理状态。

    参数：str_codex_home、path_project_root 和 dict_profile 为公共检查器输入。
    返回：全局 AGENTS 状态对象。
    """

    # 公共模块在真正生成安装结果时才需要加载。
    module_agents_common_context = load_task_module("agents_common")  # 公共 AGENTS 状态模块。

    # 关键字保持公共函数的原始调用合同。
    return dict(
        module_agents_common_context.global_codex_agents_status(
            codex_home=str_codex_home,  # 可选 Codex 主目录覆盖值。
            project_root=path_project_root,  # 可选项目根目录。
            profile=dict_profile,  # 可选治理配置。
        )
    )

# 决策请求包装器把任意参数原样委托给公共实现。
def decision_request(*tuple_args: Any, **dict_kwargs: Any) -> dict[str, Any]:
    """构造与公共治理一致的交互决策请求。

    参数：tuple_args 和 dict_kwargs 为公共 decision_request 的参数。
    返回：结构化决策请求对象。
    """

    # 延迟加载避免安装模块导入时依赖 common 搜索路径。
    module_agents_decisions_context = load_task_module("agents_decisions")  # 公共决策请求模块。

    # 调用方参数保持不变传递给唯一实现。
    return dict(module_agents_decisions_context.decision_request(*tuple_args, **dict_kwargs))

# worktree 策略包装器确保安装验证使用当前公共治理实现。
def inspect_worktree_policy(path_project: Path) -> dict[str, Any]:
    """检查项目是否违反单 worktree 治理合同。

    参数：path_project 为源码仓库根目录。
    返回：公共 worktree 策略报告。
    """

    # 策略模块只在源码仓库发布验证阶段加载。
    module_worktree_policy_context = load_task_module("git_worktree_policy")  # worktree 治理模块。

    # 结构化结果复制为普通字典供安装报告使用。
    return dict(module_worktree_policy_context.inspect_worktree_policy(path_project))

# 发布内容扫描包装器延迟加载独立策略模块。
def analyze_release_content_root(path_root: Path, *tuple_args: Any, **dict_kwargs: Any) -> Any:
    """扫描发布根目录中的禁止内容。

    参数：path_root 为发布根，tuple_args 为附加位置参数。
    参数：dict_kwargs 为公共扫描器的附加关键字参数。
    返回：公共发布内容扫描结果。
    """

    # 内容策略模块仅在验证实际发布目录时加载。
    module_content_policy_context = load_task_module("release_content_policy")  # 收据策略证据复核模块。

    # 保持扫描器完整参数合同。
    return module_content_policy_context.analyze_release_content_root(path_root, *tuple_args, **dict_kwargs)

# 收据策略包装器验证记录的内容政策证据。
def validate_recorded_release_content_policy(*tuple_args: Any, **dict_kwargs: Any) -> Any:
    """验证发布收据记录的内容策略结果。

    参数：tuple_args 和 dict_kwargs 透传公共策略验证器。
    返回：公共验证器的错误列表。
    """

    # 同一策略模块提供扫描和收据复核能力。
    module_content_policy_context = load_task_module("release_content_policy")  # 发布内容策略模块。

    # 透传参数避免复制策略字段合同。
    return module_content_policy_context.validate_recorded_release_content_policy(*tuple_args, **dict_kwargs)

# SKILL.md 中这些目录前缀代表发布包必须携带的内部引用。
RELEASE_REQUIRED_REFERENCE_PREFIXES = (
    "runtime/",  # 运行时资源目录。
    "integration/",  # 集成合同目录。
    "config/",  # 技能配置目录。
    "scripts/",  # 可执行工具目录。
    "references/",  # 参考资料目录。
    "agents/",  # 代理规则目录。
    "assets/",  # 模板和静态资源目录。
)

# 结构化失败助手统一安装 CLI 的错误协议。
def fail_json(str_message: str) -> None:
    """输出单条结构化错误并终止执行。

    参数：str_message 为面向发布者的具体错误。
    返回：不返回，始终以退出码 1 终止。
    异常：始终抛出 SystemExit。
    """

    # JSON 输出先于退出，保证自动化调用方能读取诊断。
    emit_json({"errors": [str_message]})

    # 非零退出码标记发布包不可继续安装。
    raise SystemExit(1)

# 技能名必须能安全地作为跨平台安装目录的单一叶节点。
def skill_name_error(str_skill_name: str) -> str | None:
    """检查技能名是否会扩大安装目标路径边界。

    参数：str_skill_name 为发布目录或 frontmatter 提供的技能名。
    返回：非法时返回稳定诊断，合法时返回 None。
    """

    # 空名、点目录和点点目录都不能代表可写入的技能叶节点。
    if not str_skill_name or str_skill_name in {".", ".."}:

        # 统一诊断避免调用方暴露实际路径结构。
        return "skill name must be a non-empty safe path component"

    # 跨平台路径分隔符、驱动器和空字节不能进入目录名。
    if any(str_character in str_skill_name for str_character in ("/", "\\", ":", "\x00")):

        # 单一叶节点约束阻断父级和相邻路径解析。
        return "skill name must be a single safe path component"

    # 控制字符以及 Windows 会折叠的尾随空格和点会造成身份歧义。
    if any(ord(str_character) < 32 for str_character in str_skill_name) or str_skill_name[-1] in {" ", "."}:

        # 保持发布目录名与安装目标名的一一对应。
        return "skill name contains an unsafe control or trailing character"

    # Windows 设备名即使带扩展名也不是普通技能目录叶节点。
    str_device_name = str_skill_name.split(".", 1)[0].upper()  # Windows 设备名比较基准。

    # 设备名命中保留集合时必须阻断跨平台安装。
    if str_device_name in {"CON", "PRN", "AUX", "NUL"} or (
        len(str_device_name) == 4
        and str_device_name[:3] in {"COM", "LPT"}
        and str_device_name[3] in "123456789"
    ):

        # 跨平台拒绝避免 Linux 发布包在 Windows 安装时身份漂移。
        return "skill name is reserved by the target operating system"

    # 所有检查通过后，调用方可以把名称作为目录叶节点使用。
    return None

# 路径边界助手检测根路径或任一祖先是否通过链接改变实际位置。
def path_has_symbolic_component(path_candidate: Path) -> bool:
    """判断路径本身或其祖先是否包含符号链接。

    参数：path_candidate 为需要保持物理路径身份的文件或目录。
    返回：路径无法规范化或包含链接时返回 True，否则返回 False。
    """

    # absolute 保留链接形态，resolve 用于发现祖先目录链接。
    try:

        # 路径身份变化即表示实际访问边界与声明路径不一致。
        return path_candidate.absolute() != path_candidate.resolve()

    # 无法判断路径身份时必须按不安全边界处理。
    except (OSError, RuntimeError):

        # 保守返回 True，阻断后续文件系统访问。
        return True

# 技能名解析器只信任 SKILL.md frontmatter。
def parse_skill_name(path_skill_dir: Path) -> str:
    """从技能目录的 SKILL.md frontmatter 读取技能名。

    参数：path_skill_dir 为待安装技能根目录。
    返回：frontmatter 中去除引号的 name 值。
    异常：缺少 frontmatter 或 name 时抛出 SystemExit。
    """

    # 技能根或声明链接不能把名称读取导向发布包之外。
    if path_skill_dir.is_symlink():

        # 在访问声明文件前阻断外部技能根。
        fail_json(f"skill directory must not be a symbolic link: {path_skill_dir}")

    # 技能声明是安装目录名称的唯一来源。
    path_skill_file = path_skill_dir / "SKILL.md"  # 技能 frontmatter 文件路径。

    # 声明链接不能把名称读取导向发布包之外。
    if path_skill_file.is_symlink():

        # 在 read_text 前阻断外部声明文件。
        fail_json(f"SKILL.md must not be a symbolic link: {path_skill_file}")

    # 缺少普通声明文件时不能继续推断安装身份。
    if not path_skill_file.is_file():

        # 使用稳定错误协议报告不完整技能目录。
        fail_json(f"missing SKILL.md: {path_skill_file}")

    # 读取已确认属于当前技能根的声明文本。
    str_skill_text = path_skill_file.read_text(encoding="utf-8", errors="ignore")  # 完整技能声明文本。

    # 仅匹配文件开头的首个 YAML frontmatter 块。
    match_frontmatter = re.search(r"^---\s*\n(.*?)\n---", str_skill_text, flags=re.DOTALL)  # 技能 frontmatter 匹配结果。

    # 无 frontmatter 的目录不构成合法 Codex skill。
    if not match_frontmatter:

        # JSON 文本维持旧有直接调用合同。
        raise SystemExit(json.dumps({"errors": ["> ERR: [Python] SKILL.md frontmatter is required"]}, indent=2))

    # 按行读取可避免引入 YAML 依赖。
    for str_line in match_frontmatter.group(1).splitlines():

        # name 字段允许常见的单引号或双引号包裹。
        if str_line.strip().startswith("name:"):

            # 首个 name 字段定义安装目录名称。
            str_skill_name = str_line.split(":", 1)[1].strip().strip("\"'")  # frontmatter 技能名称。

            # 名称校验结果决定是否可以进入安装目标解析。
            str_skill_name_error = skill_name_error(str_skill_name)  # frontmatter 名称诊断。

            # frontmatter 名称也必须满足安装叶节点合同。
            if str_skill_name_error:

                # 使用统一结构化失败协议终止不安全的名称解析。
                fail_json(str_skill_name_error)

            # 返回已经通过路径边界校验的技能名称。
            return str_skill_name

    # 缺少 name 时不能安全决定安装目标叶节点。
    raise SystemExit(json.dumps({"errors": ["> ERR: [Python] SKILL.md frontmatter must include name"]}, indent=2))

# 发布目录解析器验证名称形态和版本策略。
def parse_release_dir(path_release_dir: Path) -> tuple[str, str]:
    """解析版本化发布目录的技能名和版本号。

    参数：path_release_dir 为待安装发布包根目录。
    返回：技能名与 vX.Y.Z 版本号二元组。
    异常：名称或版本策略非法时通过 fail_json 终止。
    """

    # 发布路径的任一祖先不能通过符号链接改变验证边界。
    try:

        # absolute 保留路径形态，resolve 用于发现根目录或父目录链接。
        path_absolute_release_dir = path_release_dir.absolute()  # 发布目录绝对路径。

        # 解析绝对路径用于比较实际来源边界。
        path_resolved_release_dir = path_absolute_release_dir.resolve()  # 发布目录规范路径。

    # 无法规范化的路径不能进入收据读取阶段。
    except (OSError, RuntimeError):

        # 使用稳定错误协议阻断不可判定的发布身份。
        fail_json(f"release directory path cannot be normalized: {path_release_dir}")

    # 根目录链接或祖先链接都会改变发布内容来源。
    if path_release_dir.is_symlink() or path_absolute_release_dir != path_resolved_release_dir:

        # 在读取收据或扫描内容前阻断链接路径。
        fail_json(f"release directory must not be a symbolic link: {path_release_dir}")

    # 目录名必须完整匹配 <name>-vX.Y.Z。
    match_release_name = re.fullmatch(r"(.+)-(v\d+\.\d+\.\d+)", path_release_dir.name)  # 发布目录名称匹配结果。

    # 非版本化源目录禁止进入安装流程。
    if not match_release_name:

        # 诊断同时回显实际目录便于定位调用错误。
        fail_json(f"release directory must be a versioned release directory like <name>-vX.Y.Z: {path_release_dir}")

    # 版本策略可能进一步拒绝语法合法但治理上不可发布的版本。
    str_version_error = version_policy_error(match_release_name.group(2))  # 当前版本策略诊断。

    # 非空诊断表示版本不允许发布或安装。
    if str_version_error:

        # 使用统一结构化失败协议返回策略原因。
        fail_json(str_version_error)

    # 正则成功且策略通过后两个分组必然可用。
    str_skill_name = match_release_name.group(1)  # 版本目录技能名称。

    # 名称校验结果决定是否可以继续读取收据。
    str_skill_name_error = skill_name_error(str_skill_name)  # 版本目录名称诊断。

    # 发布目录名称不能把安装目标提升到父级或根级路径。
    if str_skill_name_error:

        # 复用 CLI 结构化失败合同，阻断后续收据读取和复制。
        fail_json(str_skill_name_error)

    # 正则和路径叶节点策略均通过后返回发布身份。
    return str_skill_name, match_release_name.group(2)

# Codex 主目录解析器遵循显式参数、环境变量、默认目录的优先级。
def default_codex_home(str_raw_home: str | None) -> Path:
    """解析本地 Codex 主目录。

    参数：str_raw_home 为可选命令行覆盖值。
    返回：展开并规范化后的 Codex 主目录绝对路径。
    """

    # 显式参数拥有最高优先级。
    if str_raw_home:

        # 用户目录符号在规范化前展开。
        return Path(str_raw_home).expanduser().resolve()

    # 未提供参数时读取标准 CODEX_HOME 环境变量。
    str_environment_home = os.environ.get("CODEX_HOME")  # 环境中的 Codex 主目录覆盖值。

    # 有效环境变量优先于用户主目录默认值。
    if str_environment_home:

        # 环境值同样需要展开并规范化。
        return Path(str_environment_home).expanduser().resolve()

    # 最终默认值与 Codex 标准本地布局一致。
    return (Path.home() / ".codex").resolve()

# 交互安装选项由单一函数提供给确认请求。
def install_options() -> list[dict[str, Any]]:
    """返回安装确认界面的固定选项。

    参数：无。
    返回：跳过、Codex 默认目录和自定义目录三个选项。
    """

    # 默认选择跳过安装，避免未经确认修改本地技能目录。
    return [
        {
            "label": "否，跳过安装",  # 用户界面标签。
            "value": "skip",  # CLI 目标值。
            "description": "默认选项；不复制发布包到任何 skills 目录。",  # 选项影响说明。
            "recommended": True,  # 安全默认项。
        },
        {
            "label": "安装到 Codex",  # 默认 Codex 目录选项名称。
            "value": "codex",  # 默认目录对应的目标标识。
            "description": "复制到 $CODEX_HOME/skills/<skill-name> 或 ~/.codex/skills/<skill-name>。",  # 默认目录解析规则说明。
            "recommended": False,  # 需要显式确认。
        },
        {
            "label": "自定义 skills 目录",  # 自定义根目录选项名称。
            "value": "custom",  # 自定义目录对应的目标标识。
            "description": "复制到用户提供的 skills 根目录下的 <skill-name>。",  # 自定义根目录拼接规则说明。
            "recommended": False,  # 自定义写入同样不能作为安全默认值。
        },
    ]

# 文件哈希助手以流式读取支持大型发布成员。
def sha256_file(path_file: Path) -> str:
    """计算单个文件的 SHA-256 十六进制摘要。

    参数：path_file 为需要校验的普通文件。
    返回：小写十六进制 SHA-256 摘要。
    """

    # 新摘要对象按固定块大小增量更新。
    digest_state = hashlib.sha256()  # 当前文件摘要计算器。

    # 二进制读取避免文本编码改变摘要内容。
    with path_file.open("rb") as file_handle:

        # 64 KiB 块兼顾内存占用和读取效率。
        for bytes_chunk in iter(lambda: file_handle.read(65536), b""):

            # 每个原始字节块按顺序进入摘要。
            digest_state.update(bytes_chunk)

    # 文件读取完成后输出最终摘要。
    return digest_state.hexdigest()

# 收据读取器验证文件存在、JSON 语法和顶层类型。
def read_receipt(path_release_dir: Path) -> tuple[Path, dict[str, Any]]:
    """读取发布目录中的 RELEASE_RECEIPT.json。

    参数：path_release_dir 为版本化发布包根目录。
    返回：收据路径与对象形式的收据数据。
    异常：收据缺失或无效时通过 fail_json 终止。
    """

    # 发布根或祖先链接不能把收据读取导向外部目录。
    if path_has_symbolic_component(path_release_dir):

        # 在构造收据路径前阻断根目录链接。
        fail_json(f"release directory must not be a symbolic link: {path_release_dir}")

    # 收据文件名是发布安装合同的固定组成部分。
    path_receipt = path_release_dir / "RELEASE_RECEIPT.json"  # 发布收据文件路径。

    # 收据链接可能把读取动作导向发布根之外。
    if path_receipt.is_symlink():

        # 先拒绝链接再调用 is_file 或 read_text。
        fail_json(f"RELEASE_RECEIPT.json must not be a symbolic link: {path_receipt}")

    # 缺少收据的目录不得视为发布包。
    if not path_receipt.is_file():

        # 回显预期位置帮助调用方选择正确目录。
        fail_json(f"missing RELEASE_RECEIPT.json: {path_receipt}")

    # JSON 解码和文件读取都可能失败，统一转为发布诊断。
    try:

        # UTF-8 是发布收据的固定编码。
        dict_receipt = json.loads(path_receipt.read_text(encoding="utf-8"))  # 解码后的收据对象。

    # 任何读取或解码错误都表示收据不可验证。
    except (OSError, UnicodeError, json.JSONDecodeError):

        # 不暴露平台异常细节，保持稳定的机器合同。
        fail_json(f"invalid RELEASE_RECEIPT.json: {path_receipt}")

    # JSON 数组或标量不符合收据顶层对象合同。
    if not isinstance(dict_receipt, dict):

        # 顶层类型错误与语法错误使用同一稳定诊断。
        fail_json(f"invalid RELEASE_RECEIPT.json: {path_receipt}")

    # 类型验证后可安全作为结构化收据返回。
    return path_receipt, dict_receipt

# 清单构造器记录发布包内每个文件的相对路径和摘要。
def file_manifest(path_release_dir: Path, *, exclude: set[str] | None = None) -> list[dict[str, str]]:
    """构造发布目录的确定性文件清单。

    参数：path_release_dir 为发布包根目录，exclude 为可选相对路径集合。
    返回：按路径排序的 path 和 sha256 映射列表。
    """

    # 根目录或祖先链接不能被清单遍历器当作普通发布树读取。
    if path_has_symbolic_component(path_release_dir):

        # 上层根目录验证器负责给出阻断诊断。
        return []

    # 空排除参数转换为独立集合，避免可变默认值。
    set_excluded = exclude or set()  # 本次不纳入清单的相对路径。

    # 结果保持遍历顺序，便于收据稳定比较。
    list_manifest: list[dict[str, str]] = []  # 发布文件清单条目。

    # 排序后的递归遍历保证跨运行输出确定性。
    for path_member in sorted(path_release_dir.rglob("*")):

        # 符号链接不属于可哈希普通文件，避免摘要跟随外部目标。
        if path_member.is_symlink():

            # 内容策略会单独报告链接违规，清单此处不读取目标。
            continue

        # 目录和其他非普通文件不进入哈希清单。
        if not path_member.is_file():

            # 已排除成员无需计算摘要。
            continue

        # 收据统一使用 POSIX 相对路径以支持跨平台比较。
        str_relative_path = path_member.relative_to(path_release_dir).as_posix()  # 当前成员相对路径。

        # 调用方明确排除的文件不进入结果。
        if str_relative_path in set_excluded:

            # 继续检查下一个发布成员。
            continue

        # 文件路径和内容摘要共同定义清单条目。
        list_manifest.append({"path": str_relative_path, "sha256": sha256_file(path_member)})

    # 完整列表可直接与收据 files 字段比较。
    return list_manifest

# 引用提取器只接受 SKILL.md 代码标记中的发布内部路径。
def referenced_release_paths(str_skill_text: str) -> set[str]:
    """提取 SKILL.md 声明的发布包内部资源路径。

    参数：str_skill_text 为完整技能声明文本。
    返回：去除末尾斜杠且属于受管前缀的相对路径集合。
    """

    # 集合自动消除文档中重复出现的同一路径。
    set_paths: set[str] = set()  # 技能声明引用的发布内部路径。

    # 仅扫描反引号代码标记，避免把普通叙述误判为路径。
    for str_raw_value in re.findall(r"`([^`]+)`", str_skill_text):

        # 去除代码标记内容两端的空白。
        str_reference = str_raw_value.strip()  # 当前候选引用文本。

        # 占位符路径不是具体发布成员。
        if "<" in str_reference or ">" in str_reference:

            # 跳过需要调用方替换的示例路径。
            continue

        # 仅治理约定的发布资源目录。
        if not str_reference.startswith(RELEASE_REQUIRED_REFERENCE_PREFIXES):

            # 普通命令或其他代码标记不参与完整性校验。
            continue

        # 目录引用统一去除末尾斜杠后加入集合。
        set_paths.add(str_reference.rstrip("/"))

    # 路径集合交给完整性验证逐项检查。
    return set_paths

# 安全路径解析器阻止绝对路径、父目录和符号链接逃逸。
def resolve_release_member_path(path_release_dir: Path, str_relative_path: str) -> Path | None:
    """解析并约束发布包成员路径。

    参数：path_release_dir 为发布包根目录，str_relative_path 为 POSIX 相对路径。
    返回：根目录内的规范路径；无效或越界时返回 None。
    """

    # 发布根或祖先链接不能成为外部文件引用的解析锚点。
    if path_has_symbolic_component(path_release_dir):

        # 调用方将把无效路径转换为完整性错误。
        return None

    # 去除字段两端无意义空白，但不折叠内部路径片段。
    str_normalized_path = str_relative_path.strip()  # 标准化后的声明路径。

    # 原始分段用于识别空片段、当前目录和父目录。
    list_path_segments = str_normalized_path.split("/")  # POSIX 路径原始分段。

    # 反斜杠和不规范分段会产生跨平台解释差异。
    if (
        not str_normalized_path  # 空路径不代表发布成员。
        or "\\" in str_normalized_path  # Windows 分隔符不属于 POSIX 收据合同。
        or any(str_segment in {"", ".", ".."} for str_segment in list_path_segments)  # 空段或目录跳转不安全。
    ):

        # 无效声明不得进入文件系统解析。
        return None

    # PurePosixPath 提供独立于宿主平台的绝对路径判断。
    path_posix = PurePosixPath(str_normalized_path)  # POSIX 语义下的发布成员路径。

    # POSIX 绝对路径和伪装驱动器前缀均不属于包内成员。
    if path_posix.is_absolute() or (path_posix.parts and path_posix.parts[0].endswith(":")):

        # 直接拒绝指向发布根之外的声明。
        return None

    # 根目录和候选路径解析同时覆盖符号链接逃逸。
    try:

        # 发布成员任一父节点链接都不能作为包内普通文件使用。
        path_cursor = path_release_dir  # 当前逐级检查的原始成员路径。

        # 逐级检查成员路径，拒绝内部链接和链接逃逸。
        for str_path_segment in path_posix.parts:

            # 当前路径分量加入原始发布根。
            path_cursor = path_cursor / str_path_segment  # 当前分量加入原始路径。

            # 链接成员即使指向根内也不属于普通发布内容。
            if path_cursor.is_symlink():

                # 上层完整性门禁将生成稳定的引用错误。
                return None

        # 规范化根目录作为最终 containment 边界。
        path_resolved_root = path_release_dir.resolve()  # 规范化发布根目录。

        # 使用分段组合避免宿主平台错误解释 POSIX 字符串。
        path_candidate = path_resolved_root.joinpath(*path_posix.parts)  # 待验证发布成员路径。

        # strict=False 允许校验尚未创建但语法合法的引用。
        path_resolved_candidate = path_candidate.resolve(strict=False)  # 解析符号链接后的候选路径。

    # 平台拒绝解析的路径不具备可信发布成员身份。
    except OSError:

        # 无法稳定解析时按不安全路径处理。
        return None

    # relative_to 提供路径语义上的最终根目录约束。
    try:

        # 成功计算相对路径即可证明候选仍在根目录内。
        path_resolved_candidate.relative_to(path_resolved_root)

    # 父目录或符号链接越界会触发 ValueError。
    except ValueError:

        # 越界候选不得参与任何存在性判断。
        return None

    # 返回已证明位于发布根内的规范路径。
    return path_resolved_candidate

# 完整性验证器核对 SKILL.md 引用和收据必需条目。
def validate_release_completeness(path_release_dir: Path, dict_receipt: dict[str, Any]) -> list[str]:
    """验证发布目录包含技能声明引用的全部资源。

    参数：path_release_dir 为发布包根目录，dict_receipt 为发布收据对象。
    返回：稳定排序逻辑生成的完整性错误列表。
    """

    # 发布根或祖先链接不能把完整性检查导向外部目录。
    if path_has_symbolic_component(path_release_dir):

        # 先拒绝根边界，再读取 SKILL.md 或收据清单。
        return ["release directory root must not be a symbolic link"]

    # 错误列表保留发现顺序，便于发布者逐项修复。
    list_errors: list[str] = []  # 发布完整性诊断。

    # SKILL.md 是任何可安装技能的必需入口文件。
    path_skill_file = path_release_dir / "SKILL.md"  # 发布包技能声明路径。

    # 入口链接可能在读取声明前导向发布根之外。
    if path_skill_file.is_symlink():

        # 不对链接目标执行 is_file 或 read_text。
        return ["release directory SKILL.md must not be a symbolic link"]

    # 缺少入口时无法继续提取内部引用。
    if not path_skill_file.is_file():

        # 单一明确错误避免后续派生噪声。
        return ["release directory is missing SKILL.md"]

    # 实际清单排除自描述的收据文件。
    set_actual_manifest = {
        dict_item["path"]  # 当前有效清单条目的相对路径。
        for dict_item in file_manifest(path_release_dir, exclude={"RELEASE_RECEIPT.json"})  # 实际发布文件条目。
        if isinstance(dict_item, dict) and str(dict_item.get("path", "")).strip()  # 仅保留非空对象条目。
    }  # 实际发布成员路径集合。

    # 技能声明以宽容解码读取，完整性判断只依赖可识别路径文本。
    str_skill_text = path_skill_file.read_text(encoding="utf-8", errors="ignore")  # 用于资源引用提取的声明文本。

    # 每个受管引用都必须安全且实际存在于发布包内。
    for str_reference in sorted(referenced_release_paths(str_skill_text)):

        # 安全解析先于任何存在性检查。
        path_reference = resolve_release_member_path(path_release_dir, str_reference)  # 已约束的引用路径。

        # 越界引用即使指向真实外部文件也必须拒绝。
        if path_reference is None:

            # 回显原始引用帮助发布者定位 SKILL.md。
            list_errors.append(f"release directory SKILL.md referenced path escapes the release root: {str_reference}")

            # 不安全引用不得进入后续文件系统判断。
            continue

        # 精确文件条目已经证明引用存在。
        if str_reference in set_actual_manifest:

            # 清单精确命中后无需其他存在性证明。
            continue

        # 空目录或未纳入普通文件清单的安全成员仍可由文件系统证明。
        if path_reference.exists():

            # 文件系统已证明该安全引用存在。
            continue

        # 目录引用可由其任一后代文件证明存在。
        if any(str_path.startswith(str_reference + "/") for str_path in set_actual_manifest):

            # 后代清单条目证明所引用目录存在。
            continue

        # 其余引用在发布包中缺失。
        list_errors.append(f"release directory is missing SKILL.md referenced path: {str_reference}")

    # 收据 files 字段用于确认必需入口被正式记录。
    object_recorded_files = dict_receipt.get("files")  # 原始收据文件清单字段。

    # 仅列表形态提供可验证的文件条目集合。
    if isinstance(object_recorded_files, list):

        # 对象条目的 path 字段构成收据记录集合。
        set_recorded_manifest = {
            str(dict_item.get("path", "")).strip()  # 当前收据条目的相对路径。
            for dict_item in object_recorded_files  # 原始收据文件条目。
            if isinstance(dict_item, dict)  # 忽略非对象噪声条目。
        }  # 收据声明的发布成员路径集合。

        # SKILL.md 必须同时存在于文件系统和收据中。
        if "SKILL.md" not in set_recorded_manifest:

            # 缺失条目会使收据无法完整证明发布内容。
            list_errors.append("release receipt is missing required file entry: SKILL.md")

    # 返回所有独立完整性诊断。
    return list_errors
