"""读取并校验平台目录，避免业务代码散落平台路径常量。"""

# 预先启用延迟注解，保证平台类型声明兼容当前运行环境。
from __future__ import annotations

# 平台目录读取依赖的标准库集中在同一导入组。
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

# 平台目录文件名由发布合同统一引用。
CATALOG_FILE_NAME = "agent-platforms.json"  # 平台目录的固定文件名

# 安装配置文件名必须与平台渲染器保持一致。
CONFIG_FILE_NAME = "agent.json"  # 单平台安装配置的固定文件名

# 当前目录 schema 用整数版本参与兼容性校验。
CATALOG_SCHEMA_VERSION = 1  # 目录结构的 schema 版本

# 目录内容版本独立于结构版本递增。
CATALOG_VERSION = 1  # 平台条目的内容版本

# 平台集合只在目录读取后计算，避免源码固定当前平台案例。
PLATFORM_KEYS: frozenset[str] = frozenset()  # 兼容导出；运行时键集合来自 catalog

# 平台字段清单控制安装文件与目录文件的字段闭合性。
PROFILE_FIELDS = (  # 平台配置字段的闭合集合
    # 指令文件字段决定平台读取的全局规则入口。
    "instruction_file",  # 目录读取的全局指令文件字段
    # 工作区字段决定项目配置的相对目录。
    "workspace_config_dir",  # 项目工作区配置目录字段
    # 状态字段决定生成器状态的可选子目录。
    "generator_state_subdir",  # 生成器状态子目录字段
    # 用户目录字段决定平台用户根目录的映射。
    "user_home_dir",  # 平台用户主目录字段
    # 技能目录字段决定可安装技能的相对位置。
    "skill_install_dir",  # 技能投影安装目录字段
    # worker 字段决定该平台是否支持受管 worker。
    "worker_support",  # worker 能力支持状态字段
    # 元数据字段列出安装时必须投影的描述文件。
    "skill_metadata",  # 安装完整性元数据字段
)  # 单平台配置字段

# 目录顶层字段清单用于拒绝静默拼写漂移。
CATALOG_FIELDS = frozenset(("schema_version", "catalog_version", "platforms"))  # 目录顶层字段

# 不可变配置对象承载通过目录校验的平台字段。
@dataclass(frozen=True)
class AgentProfile:
    """保存一个已经通过目录校验的平台配置。

    参数：字段值来自受管平台目录，并由构造方完成类型校验。
    """

    # 平台标识用于选择目录中的唯一配置条目。
    agent: str  # 受支持的平台名称

    # 全局规则文件名用于拼接用户级指令路径。
    instruction_file: str  # 平台指令文件名

    # 工作区配置目录用于定位项目级配置文件。
    workspace_config_dir: str  # 项目工作区配置目录

    # 状态子目录用于隔离生成器在项目中的持久化数据。
    generator_state_subdir: str  # 生成器状态子目录

    # 用户目录片段用于映射平台专属的主目录结构。
    user_home_dir: str  # 用户主目录片段

    # 技能安装目录用于计算最终投影目标。
    skill_install_dir: str  # 技能安装目录片段

    # worker 支持标记用于控制平台能力分支。
    worker_support: str  # worker 支持状态

    # 元数据路径集合用于安装后的技能完整性校验。
    skill_metadata: tuple[str, ...]  # 平台元数据相对路径

    # 计算项目内的平台状态入口，保持状态目录拼接规则集中。
    def generator_state_root(self, path_project: Path) -> Path:
        """根据项目根目录拼接生成器状态目录。

        参数：path_project 为项目根目录。
        返回：当前平台对应的状态目录。
        """

        # 平台配置目录先承接项目级工作区状态。
        path_root = path_project / self.workspace_config_dir  # 项目工作区配置根

        # 只有目录配置声明了子目录时才追加层级。
        if self.generator_state_subdir:

            # 将平台声明的状态子目录追加到工作区根。
            path_root /= self.generator_state_subdir  # 追加平台声明的状态隔离段

        # 调用方继续使用已经组合完成的状态目录。
        return path_root

    # 计算用户主目录下的技能投影入口，供安装流程复用。
    def skill_install_root(self, path_home: Path, str_skill_name: str) -> Path:
        """根据用户主目录和技能名拼接平台安装目录。

        参数：
            path_home: 平台用户主目录。
            str_skill_name: 要安装的技能名称。
        返回：平台专属的技能安装目录。
        """

        # 用户目录、平台目录和技能名按目录合同保持固定层级。
        path_install_root = (
            path_home / self.user_home_dir / self.skill_install_dir / str_skill_name  # 组合平台技能安装层级
        )  # 平台技能安装根

        # 返回可用于投影和校验的安装位置。
        return path_install_root

# 解析平台目录文件位置，统一默认路径和隔离夹具入口。
def _catalog_path(path_catalog: Path | None) -> Path:
    """解析平台目录文件位置。

    参数：path_catalog 为可选的隔离目录文件路径。
    返回：实际读取的平台目录文件。
    """

    # 测试夹具或调用方显式传入目录时保持该隔离位置。
    if path_catalog is not None:

        # 显式目录优先于源码树中的默认目录。
        return path_catalog

    # 默认目录相对于当前模块固定回溯到技能根。
    path_default_catalog = Path(__file__).resolve().parents[3] / "config" / CATALOG_FILE_NAME  # 默认平台目录文件

    # 调用方未指定目录时使用受管技能配置。
    return path_default_catalog

# 构造带协议前缀的配置异常，避免调用方自行拼接输出格式。
def _error(str_message: str) -> ValueError:
    """构造带 Python 输出协议前缀的配置异常。

    参数：str_message 为面向调用方的具体失败原因。
    返回：带统一输出前缀的 ValueError。
    """

    # 所有配置错误共享人类可读且可聚合的协议前缀。
    error_value = ValueError(f"> ERR: [Python] {str_message}")  # 结构化配置异常

    # 将统一异常交给各校验分支抛出。
    return error_value

# 校验目录字段的相对 POSIX 路径约束，阻断跨目录解析。
def _require_relative_path(str_value: Any, str_field: str, *, allow_empty: bool = False) -> str:
    """校验目录字段为安全的相对 POSIX 路径。

    参数：
        str_value: 待校验的目录字段。
        str_field: 字段名称，用于构造诊断。
        allow_empty: 是否允许空字符串。
    返回：通过校验的原始相对路径文本。
    异常：字段类型、格式或路径层级不符合合同时抛出 ValueError。
    """

    # 非字符串或不允许的空字段不能进入目录解析。
    if not isinstance(str_value, str) or (not str_value and not allow_empty):

        # 配置字段错误必须指出具体字段与约束。
        raise ValueError(f"> ERR: [Python] catalog field {str_field!r} must be a non-empty string")

    # 被允许的空子目录表示平台不增加额外层级。
    if not str_value:

        # 空值只在显式 allow_empty 合同下有效。
        return ""

    # 反斜杠和驱动器符号会破坏 POSIX 相对路径合同。
    if "\\" in str_value or ":" in str_value:

        # 直接拒绝跨平台歧义写法。
        raise ValueError(f"> ERR: [Python] catalog field {str_field!r} must use a relative POSIX path")

    # PurePosixPath 负责识别绝对路径和父级片段。
    path_value = PurePosixPath(str_value)  # 待确认的 POSIX 路径对象

    # 绝对路径、父级跳转和空片段都不能进入受管目录。
    if path_value.is_absolute() or ".." in path_value.parts or "" in path_value.parts:

        # 统一报告目录字段越界风险。
        raise ValueError(f"> ERR: [Python] catalog field {str_field!r} must stay relative")

    # 保留原始相对路径，避免不必要的文本重写。
    return str_value

# 校验平台根指令文件，保证它只引用安全的 Markdown 文件名。
def _require_instruction_file(str_value: Any, str_agent: str) -> str:
    """校验平台根指令文件只能是安全的相对文件名。

    参数：
        str_value: 待校验的指令文件字段。
        str_agent: 产生诊断的平台标识。
    返回：通过相对路径和 Markdown 后缀校验的文件名。
    异常：字段不是安全 Markdown 文件名时抛出 ValueError。
    """

    # 先复用通用路径校验，统一拦截绝对路径和父级片段。
    str_value = _require_relative_path(str_value, "instruction_file")  # 已归一化的指令文件名

    # 根指令文件必须是单层 Markdown 文件，避免路径穿越。
    if "/" in str_value or "\\" in str_value or PurePosixPath(str_value).suffix.lower() != ".md":

        # 不符合文件合同的配置必须在平台维度给出诊断。
        raise ValueError(
            f"> ERR: [Python] platform {str_agent!r} instruction_file must be a Markdown file name"
        )

    # 返回已经通过后缀和层级检查的文件名。
    return str_value

# 校验平台元数据清单，确保每个路径都落在 agents/ 下。
def _require_metadata_paths(list_metadata: Any, str_agent: str) -> list[str]:
    """校验平台 skill 元数据路径不越出技能根。

    参数：
        list_metadata: 待校验的元数据相对路径列表。
        str_agent: 产生诊断的平台标识。
    返回：去除不安全值后的有效元数据路径列表。
    异常：列表为空、路径越界、后缀错误或出现重复项时抛出 ValueError。
    """

    # 元数据清单必须是非空字符串列表，拒绝隐式类型转换。
    if not isinstance(list_metadata, list) or not list_metadata or not all(
        isinstance(item, str) and item for item in list_metadata
    ):

        # 类型不符合目录合同时立即返回平台级错误。
        raise ValueError(
            f"> ERR: [Python] platform {str_agent!r} skill_metadata must be a non-empty string list"
        )

    # 逐项保留通过相对路径校验的元数据条目。
    list_validated: list[str] = []  # 已校验的元数据路径

    # 每个条目必须位于 agents/ 且使用 YAML 后缀。
    for str_metadata in list_metadata:

        # 当前条目还需满足元数据目录和扩展名的专属约束。
        str_validated = _require_relative_path(str_metadata, "skill_metadata")  # 当前平台的可安装元数据文件

        # 元数据路径不能引用技能根外部或非 YAML 文件。
        if not str_validated.startswith("agents/") or PurePosixPath(str_validated).suffix.lower() != ".yaml":

            # 目录层级或文件类型不符合安装合同。
            raise ValueError(
                f"> ERR: [Python] platform {str_agent!r} skill_metadata must stay under agents/"
            )

        # 将当前安全条目加入结果清单。
        list_validated.append(str_validated)

    # 重复路径会造成安装投影不确定，必须拒绝。
    if len(set(list_validated)) != len(list_validated):

        # 保留平台标识以便定位目录中的重复项。
        raise ValueError(f"> ERR: [Python] platform {str_agent!r} skill_metadata contains duplicates")

    # 返回顺序稳定且已完成边界校验的元数据列表。
    return list_validated

# 校验平台目录的顶层字段、平台集合及每个平台的字段类型。
def _validate_catalog(dict_catalog: Mapping[str, Any]) -> dict[str, Any]:
    """校验目录顶层结构并返回普通字典。

    参数：
        dict_catalog: 待校验的平台目录映射。
    返回：保持原字段值的普通字典副本。
    异常：顶层字段、版本、平台条目或路径约束不符合合同时抛出 ValueError。
    """

    # 目录输入必须是映射，防止字符串等值被误当成配置。
    if not isinstance(dict_catalog, Mapping):

        # 顶层类型错误不允许继续访问字段。
        raise ValueError("> ERR: [Python] agent platform catalog must be an object")

    # 顶层字段必须闭合，避免未知键被静默忽略。
    if set(dict_catalog) != CATALOG_FIELDS:

        # 明确报告字段漂移，便于修复目录生成器。
        raise ValueError("> ERR: [Python] agent platform catalog contains unknown or missing top-level fields")

    # 结构版本必须与当前解析器兼容。
    if dict_catalog.get("schema_version") != CATALOG_SCHEMA_VERSION:

        # 结构版本不匹配时拒绝读取后续平台数据。
        raise ValueError("> ERR: [Python] unsupported agent platform catalog schema_version")

    # 内容版本必须与当前发布合同一致。
    if dict_catalog.get("catalog_version") != CATALOG_VERSION:

        # 内容版本不匹配意味着目录来源不受当前代码支持。
        raise ValueError("> ERR: [Python] unsupported agent platform catalog catalog_version")

    # 提取平台映射并校验平台键集合的闭合性。
    dict_platforms = dict_catalog.get("platforms")  # 受支持平台到字段映射的目录分支

    # 目录必须包含至少一个配置平台，具体成员和数量完全由 catalog 决定。
    if not isinstance(dict_platforms, Mapping) or not dict_platforms:

        # 平台集合漂移会影响安装和 worker 路由。
        raise ValueError("> ERR: [Python] agent platform catalog must contain at least one configured platform")

    # 逐个平台检查字段闭合性和字段值约束。
    for str_agent, dict_profile in dict_platforms.items():

        # 每个平台条目必须是字段映射。
        if not isinstance(dict_profile, Mapping):

            # 平台标识用于定位错误目录项。
            raise ValueError(f"> ERR: [Python] platform {str_agent!r} must be an object")

        # 平台字段必须与固定字段清单完全一致。
        if set(dict_profile) != set(PROFILE_FIELDS):

            # 未知或缺失字段会破坏配置闭合性。
            raise ValueError(f"> ERR: [Python] platform {str_agent!r} contains unknown or missing fields")

        # 指令文件必须是单层 Markdown 文件名。
        _require_instruction_file(dict_profile["instruction_file"], str_agent)

        # 工作区配置目录必须保持相对路径。
        _require_relative_path(dict_profile["workspace_config_dir"], "workspace_config_dir")

        # 状态目录允许为空，但不能接受危险路径片段。
        _require_relative_path(dict_profile["generator_state_subdir"], "generator_state_subdir", allow_empty=True)

        # 用户目录片段必须保持相对路径。
        _require_relative_path(dict_profile["user_home_dir"], "user_home_dir")

        # 技能安装目录片段必须保持相对路径。
        _require_relative_path(dict_profile["skill_install_dir"], "skill_install_dir")

        # worker 支持标记只能使用当前合同中的两种状态。
        if dict_profile["worker_support"] not in ("codex-native", "unsupported"):

            # 未知能力状态不能被调用方当作可用能力。
            raise ValueError(f"> ERR: [Python] platform {str_agent!r} worker_support is invalid")

        # 元数据路径集合必须完成目录和后缀校验。
        _require_metadata_paths(dict_profile["skill_metadata"], str_agent)

    # 返回普通字典，避免调用方依赖输入映射的可变实现。
    return dict(dict_catalog)

# 读取默认或调用方指定的平台目录，并完成结构校验。
def load_catalog(path_catalog: Path | None = None) -> dict[str, Any]:
    """读取默认或指定的平台代理目录。

    参数：
        path_catalog: 可选的隔离目录文件路径；为空时读取技能内置目录。
    返回：通过目录合同校验的平台目录字典。
    异常：目录文件无法读取、无法解析或内容不合法时抛出 ValueError。
    """

    # 根据调用方是否提供路径选择目录来源。
    path_source = _catalog_path(path_catalog)  # 实际读取的平台目录路径

    # 读取 JSON 文本并将系统错误转换为稳定的业务异常。
    try:

        # 目录文本必须按 UTF-8 解码以保持跨平台一致性。
        dict_catalog = json.loads(path_source.read_text(encoding="utf-8"))  # JSON 解析后的目录映射

    # 将文件和 JSON 解析失败统一纳入 Python 错误协议。
    except (OSError, json.JSONDecodeError) as exc:

        # 返回包含源路径的诊断，便于定位失效目录。
        raise ValueError(f"> ERR: [Python] cannot read agent platform catalog: {path_source}") from exc

    # 仅向调用方返回经过完整字段校验的目录。
    return _validate_catalog(dict_catalog)

# 计算规范化平台目录的 SHA-256，供证据和发布校验复用。
def catalog_sha256(dict_catalog: Mapping[str, Any]) -> str:
    """返回目录规范 JSON 的 SHA-256。

    参数：
        dict_catalog: 待校验并序列化的平台目录映射。
    返回：规范 JSON 字节序列的十六进制 SHA-256 摘要。
    """

    # 先校验目录，确保摘要只覆盖受支持的结构。
    dict_validated = _validate_catalog(dict_catalog)  # 已校验的平台目录

    # 使用稳定排序和紧凑分隔符生成跨运行一致的字节序列。
    bytes_payload = json.dumps(  # 生成规范目录的序列化输入
        dict_validated,  # 提供已经完成结构校验的目录
        ensure_ascii=False,  # 保留目录中的中文字符
        sort_keys=True,  # 固定键顺序保证摘要稳定
        separators=(",", ":"),  # 使用紧凑分隔符消除格式漂移
    ).encode("utf-8")  # 规范化目录字节

    # 返回规范目录的 SHA-256 十六进制摘要。
    return hashlib.sha256(bytes_payload).hexdigest()

# 从目录中解析单个平台配置，提供类型明确的调用对象。
def resolve_agent_profile(
    str_agent: str,
    dict_catalog: Mapping[str, Any] | None = None,
) -> AgentProfile:
    """从目录解析单个平台配置。

    参数：
        str_agent: 待读取的平台标识。
        dict_catalog: 可选的已加载目录；为空时从默认文件读取。
    返回：指定平台的不可变 AgentProfile 配置对象。
    异常：平台不存在或目录内容不合法时抛出 ValueError。
    """

    # 显式目录仍需复用同一校验器，默认目录也保持相同路径。
    dict_loaded = load_catalog() if dict_catalog is None else _validate_catalog(dict_catalog)  # 已校验目录

    # 平台键缺失时禁止构造不完整的配置对象。
    if str_agent not in dict_loaded["platforms"]:

        # 返回稳定的未知平台诊断，避免静默回退到其他平台。
        raise ValueError(f"> ERR: [Python] unknown agent platform: {str_agent}")

    # 取得目标平台的字段映射并构造不可变配置。
    dict_profile = dict_loaded["platforms"][str_agent]  # 目标平台的字段映射

    # 返回字段来源明确的配置对象，供路径计算和安装流程使用。
    return AgentProfile(
        agent=str_agent,
        instruction_file=dict_profile["instruction_file"],
        workspace_config_dir=dict_profile["workspace_config_dir"],
        generator_state_subdir=dict_profile["generator_state_subdir"],
        user_home_dir=dict_profile["user_home_dir"],
        skill_install_dir=dict_profile["skill_install_dir"],
        worker_support=dict_profile["worker_support"],
        skill_metadata=tuple(dict_profile["skill_metadata"]),
    )

# 读取技能目录中的平台配置，并核对其与目录源的字段一致性。
def load_agent_config(path_skill_root: Path) -> AgentProfile:
    """读取技能目录中的单平台解析结果。

    参数：
        path_skill_root: 当前技能的根目录。
    返回：通过配置文件和平台目录双重校验的 AgentProfile。
    异常：配置文件不可读、字段漂移或与目录源不一致时抛出 ValueError。
    """

    # 配置文件固定位于技能根的 config 子目录。
    path_config = path_skill_root / "config" / CONFIG_FILE_NAME  # 平台安装配置路径

    # 读取配置 JSON，并把文件错误转换为稳定异常。
    try:

        # 配置文件按 UTF-8 解码后再进入映射校验。
        dict_config = json.loads(path_config.read_text(encoding="utf-8"))  # JSON 配置映射

    # 读取或解析失败都表示技能配置不可用。
    except (OSError, json.JSONDecodeError) as exc:

        # 错误中保留配置路径，便于诊断安装位置。
        raise ValueError(f"> ERR: [Python] cannot read agent config: {path_config}") from exc

    # 配置顶层必须是映射对象。
    if not isinstance(dict_config, Mapping):

        # 拒绝以列表或标量伪装的平台配置。
        raise ValueError("> ERR: [Python] agent config must be an object")

    # 配置结构版本必须与当前解析器一致。
    if dict_config.get("schema_version") != CATALOG_SCHEMA_VERSION:

        # 结构版本漂移时停止读取后续字段。
        raise ValueError("> ERR: [Python] unsupported agent config schema_version")

    # 读取目录源以核对配置的来源版本和字段值。
    dict_catalog = load_catalog()  # 当前受管平台目录

    # 配置内容版本必须与目录源保持一致。
    if dict_config.get("catalog_version") != dict_catalog.get("catalog_version"):

        # 版本不一致表示配置由不同目录合同生成。
        raise ValueError("> ERR: [Python] agent config catalog_version does not match catalog")

    # 平台标识必须是非空字符串。
    str_agent = dict_config.get("agent")  # 配置文件声明的平台标识

    # 缺少平台标识时无法安全选择配置分支。
    if not isinstance(str_agent, str) or not str_agent:

        # 直接报告必需字段缺失。
        raise ValueError("> ERR: [Python] agent config misses agent")

    # 配置字段必须严格覆盖版本、平台和平台字段清单。
    if set(dict_config) != frozenset(("schema_version", "catalog_version", "agent", *PROFILE_FIELDS)):

        # 未知或缺失字段会导致配置源与目录脱节。
        raise ValueError("> ERR: [Python] agent config contains unknown or missing fields")

    # 按目录源解析平台，避免直接信任配置文件的路径值。
    agent_profile_config = resolve_agent_profile(str_agent, dict_catalog)  # 目录源中的平台配置

    # 构造目录源应有字段，用于逐项核对配置文件。
    dict_expected = {
        "instruction_file": agent_profile_config.instruction_file,  # 目录规定的指令文件
        "workspace_config_dir": agent_profile_config.workspace_config_dir,  # 目录规定的工作区路径
        "generator_state_subdir": agent_profile_config.generator_state_subdir,  # 目录规定的状态子目录
        "user_home_dir": agent_profile_config.user_home_dir,  # 目录规定的用户目录片段
        "skill_install_dir": agent_profile_config.skill_install_dir,  # 目录规定的安装目录片段
        "worker_support": agent_profile_config.worker_support,  # 目录规定的 worker 能力状态
        "skill_metadata": list(agent_profile_config.skill_metadata),  # 目录规定的元数据路径
    }  # 目录源期望的配置字段

    # 逐字段比较，阻断单字段篡改或旧配置残留。
    for str_field, object_expected in dict_expected.items():

        # 只有完全匹配目录源的字段才允许继续安装。
        if dict_config.get(str_field) != object_expected:

            # 报告不一致字段，便于重建配置文件。
            raise ValueError(f"> ERR: [Python] agent config field does not match catalog: {str_field}")

    # 返回与目录源一致的不可变平台配置。
    return agent_profile_config

# 将平台配置写入技能目录，作为目录解析结果的持久化投影。
def write_agent_config(path_skill_root: Path, str_agent: str) -> AgentProfile:
    """将单平台解析结果写入技能目录并返回该配置。

    参数：
        path_skill_root: 当前技能的根目录。
        str_agent: 要写入的平台标识。
    返回：写入配置文件的 AgentProfile 对象。
    异常：平台目录不合法或配置文件无法写入时抛出 ValueError 或 OSError。
    """

    # 先从受管目录解析平台，拒绝写入未登记的平台。
    agent_profile_config = resolve_agent_profile(str_agent)  # 待写入的平台配置

    # 配置文件固定写入技能根的 config 子目录。
    path_config = path_skill_root / "config" / CONFIG_FILE_NAME  # 平台配置输出路径

    # 确保配置目录存在且不改变既有文件内容结构。
    path_config.parent.mkdir(parents=True, exist_ok=True)

    # 用目录源字段生成闭合的配置映射。
    dict_config = {
        "schema_version": CATALOG_SCHEMA_VERSION,  # 当前配置结构版本
        "catalog_version": load_catalog().get("catalog_version"),  # 当前目录内容版本
        "agent": agent_profile_config.agent,  # 目标平台标识
        "instruction_file": agent_profile_config.instruction_file,  # 平台全局指令文件
        "workspace_config_dir": agent_profile_config.workspace_config_dir,  # 项目配置入口使用目录源的工作区段
        "generator_state_subdir": agent_profile_config.generator_state_subdir,  # 状态持久化位置使用目录源的隔离段
        "user_home_dir": agent_profile_config.user_home_dir,  # 主目录投影采用目录源的用户段
        "skill_install_dir": agent_profile_config.skill_install_dir,  # 技能投影目标采用目录源的安装段
        "worker_support": agent_profile_config.worker_support,  # worker 路由依据目录源的能力标记
        "skill_metadata": list(agent_profile_config.skill_metadata),  # 安装完整性元数据
    }  # 待持久化的平台配置

    # 以稳定缩进写入 UTF-8 配置，保留末尾换行。
    path_config.write_text(
        json.dumps(dict_config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # 返回刚刚写入的目录源配置对象。
    return agent_profile_config

# 解析平台用户主目录，并保留调用方显式提供的隔离根目录。
def resolve_agent_home(
    path_skill_root: Path,
    str_raw_home: str | None = None,
    str_agent: str | None = None,
) -> Path:
    """解析平台用户主目录，保留调用方显式隔离根目录。

    参数：
        path_skill_root: 当前技能根目录，用于读取默认平台配置。
        str_raw_home: 可选的用户主目录文本；为空时使用系统主目录。
        str_agent: 可选的平台标识；为空时读取技能配置中的平台。
    返回：解析后的平台用户主目录路径。
    异常：技能配置或显式主目录无法解析时抛出配置相关异常。
    """

    # 显式平台优先于技能配置，确保隔离测试可以指定平台。
    agent_profile = load_agent_config(path_skill_root) if not str_agent else resolve_agent_profile(str_agent)  # 平台配置

    # 去除调用方主目录文本两端空白，空值表示使用默认目录。
    str_home = str_raw_home.strip() if str_raw_home else ""  # 显式主目录文本

    # 显式主目录必须经过用户目录展开和规范化。
    if str_home:

        # 返回调用方指定且已经解析的主目录。
        return Path(str_home).expanduser().resolve()

    # 没有显式目录时按平台目录片段拼接系统主目录。
    return (Path.home() / agent_profile.user_home_dir).resolve()

# 生成当前平台的全局规则文件显示标签，供日志和报告引用。
def global_instruction_file_label(agent_profile: AgentProfile) -> str:
    """返回当前平台的全局规则文件显示标签。

    参数：
        agent_profile: 已通过目录校验的平台配置。
    返回：包含用户目录片段和指令文件名的显示标签。
    """

    # 将平台用户目录和指令文件名按合同拼接为可读标签。
    return f"Global {agent_profile.user_home_dir}/{agent_profile.instruction_file}"
