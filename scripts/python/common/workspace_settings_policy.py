"""定义本地与远端工作区设置文件的路径治理合同。"""

# future 注解推迟求值，避免运行时解析仅用于类型检查的联合类型。
from __future__ import annotations

# 标准库提供路径解析、正则匹配和结构化类型标注。
import re
from pathlib import Path
from typing import Any

# 工作区设置统一收敛到仓库根下的隐藏配置目录。
SETTINGS_FOLDER = ".settings"  # 工作区设置目录名。

# 本地配置后缀用于阻止私有设置进入远端工作区。
LOCAL_SETTINGS_SUFFIX = ".local.json"  # 本地专用设置文件后缀。

# 远端配置后缀用于识别允许同步到服务器的设置文件。
REMOTE_SETTINGS_SUFFIX = ".remote.json"  # 远端专用设置文件后缀。

# 默认本地配置路径写入渲染后的目录治理合同。
LOCAL_DEFAULT_SETTINGS = f"{SETTINGS_FOLDER}/project.local.json"  # 默认本地设置相对路径。

# 默认远端配置路径写入渲染后的目录治理合同。
REMOTE_DEFAULT_SETTINGS = f"{SETTINGS_FOLDER}/project.remote.json"  # 默认远端设置相对路径。

# 本地规则只接受设置目录直属的单层 JSON 文件。
WORKSPACE_SETTINGS_LOCAL_RE = re.compile(  # 编译本地配置的完整路径约束。
    r"^\.settings/[^/]+\.local\.json$",  # 本地设置文件的完整相对路径模式。
    flags=re.IGNORECASE,  # 文件后缀匹配不区分大小写。
)

# 远端规则与本地规则保持相同的单层目录边界。
WORKSPACE_SETTINGS_REMOTE_RE = re.compile(  # 编译远端配置的完整路径约束。
    r"^\.settings/[^/]+\.remote\.json$",  # 远端设置文件的完整相对路径模式。
    flags=re.IGNORECASE,  # 远端配置扩展名允许不同大小写。
)

# 通用 JSON 规则用于区分错误后缀和错误目录层级。
WORKSPACE_SETTINGS_JSON_RE = re.compile(  # 编译设置目录的通用 JSON 约束。
    r"^\.settings/[^/]+\.json$",  # 设置目录直属 JSON 文件模式。
    flags=re.IGNORECASE,  # 文件扩展名检查不区分大小写。
)

# 根目录规则定位尚未迁入设置目录的配置文件。
ROOT_SETTINGS_FILE_RE = re.compile(  # 编译根目录误放配置的识别规则。
    r"^[^/]+\.(?:local|remote)\.json$",  # 仓库根下的本地或远端设置文件模式。
    flags=re.IGNORECASE,  # 配置后缀检查不区分大小写。
)

# 路径归一化函数隔离不同平台分隔符带来的匹配差异。
def normalize_rel(str_raw_path: str) -> str:
    """把输入路径转换为无首尾斜杠的 POSIX 风格相对路径。

    参数：
        str_raw_path: 待检查的路径文本。
    返回：
        折叠重复分隔符后的相对路径文本。
    """

    # 所有治理规则共享同一份稳定的路径表示。
    return re.sub(r"/+", "/", str(str_raw_path).replace("\\", "/").strip().strip("/"))

# 渲染器通过该合同生成 AGENTS 中的工作区设置规则。
def workspace_settings_contract() -> dict[str, Any]:
    """返回工作区设置文件的路径、后缀和远端同步合同。

    参数：无外部业务参数。
    返回：可直接嵌入控制画像的工作区设置合同映射。
    """

    # 字段名保持与既有控制画像和验证器消费者兼容。
    return {
        "folder": SETTINGS_FOLDER,  # 设置目录名。
        "local_default_file": LOCAL_DEFAULT_SETTINGS,  # 默认本地设置文件。
        "remote_default_file": REMOTE_DEFAULT_SETTINGS,  # 默认远端设置文件。
        "local_file_pattern": f"{SETTINGS_FOLDER}/<name>{LOCAL_SETTINGS_SUFFIX}",  # 本地设置命名模式。
        "remote_file_pattern": f"{SETTINGS_FOLDER}/<name>{REMOTE_SETTINGS_SUFFIX}",  # 远端设置命名模式。
        "local_suffix": LOCAL_SETTINGS_SUFFIX,  # 本地设置后缀。
        "remote_suffix": REMOTE_SETTINGS_SUFFIX,  # 远端设置后缀。
        "local_files_remote_blocked": True,  # 本地配置禁止复制到远端。
    }

# 本地分类函数供目录扫描与远端同步检查共同复用。
def is_workspace_settings_local(str_path: str) -> bool:
    """判断路径是否为设置目录直属的本地专用 JSON 文件。

    参数：
        str_path: 待分类的仓库相对路径。
    返回：
        路径满足本地设置命名合同时返回真。
    """

    # 完整匹配避免子目录文件或附加后缀被误判为本地设置。
    return WORKSPACE_SETTINGS_LOCAL_RE.fullmatch(normalize_rel(str_path)) is not None

# 远端分类函数限定服务器可消费的设置文件命名。
def is_workspace_settings_remote(str_path: str) -> bool:
    """判断路径是否为设置目录直属的远端专用 JSON 文件。

    参数：
        str_path: 待分类的仓库相对路径。
    返回：
        路径满足远端设置命名合同时返回真。
    """

    # 完整匹配保证普通 JSON 文件不会获得远端配置类别。
    return WORKSPACE_SETTINGS_REMOTE_RE.fullmatch(normalize_rel(str_path)) is not None

# 路径类别用于项目检测结果和目录治理报告。
def workspace_settings_path_classes(str_path: str) -> list[str]:
    """返回工作区设置路径对应的治理类别列表。

    参数：
        str_path: 待分类的仓库相对路径。
    返回：
        按通用类别到具体类别排列的字符串列表。
    """

    # 先统一分隔符再判断设置目录边界。
    str_normalized_path = normalize_rel(str_path)  # 供位置合同逐层验证的相对路径。

    # 设置目录之外的文件不参与工作区设置分类。
    if not str_normalized_path.startswith(f"{SETTINGS_FOLDER}/"):

        # 空列表明确表示该路径与设置治理无关。
        return []

    # 所有设置目录成员先获得通用类别。
    list_path_classes = ["workspace-settings"]  # 当前路径的治理类别集合。

    # 本地配置需要额外标记远端阻断语义。
    if is_workspace_settings_local(str_normalized_path):

        # 具体类别供同步检查器识别本地专用文件。
        list_path_classes.append("workspace-settings-local")

    # 远端配置获得服务器运行时可用类别。
    elif is_workspace_settings_remote(str_normalized_path):

        # 具体类别区分经过命名约束的远端设置文件。
        list_path_classes.append("workspace-settings-remote")

    # 其他 JSON 文件仍需进入错误后缀诊断路径。
    elif str_normalized_path.endswith(".json"):

        # 通用 JSON 类别保留待验证但尚未合法的配置文件。
        list_path_classes.append("workspace-settings-json")

    # 调用方按稳定顺序消费完整类别集合。
    return list_path_classes

# 位置诊断函数集中解释设置文件应如何迁移或改名。
def workspace_settings_location_reason(str_path: str) -> str | None:
    """返回工作区设置路径违反目录或后缀合同的原因。

    参数：
        str_path: 待验证的仓库相对路径。
    返回：
        合法或无关路径返回空值，否则返回稳定英文诊断正文。
    """

    # 位置验证统一使用折叠分隔符后的仓库相对路径。
    str_normalized_path = normalize_rel(str_path)  # 规范化后的仓库相对路径。

    # 空输入不代表仓库中存在违规设置文件。
    if not str_normalized_path:

        # 调用方无需为缺失路径生成诊断。
        return None

    # 根目录设置文件必须迁入统一设置目录。
    if ROOT_SETTINGS_FILE_RE.fullmatch(str_normalized_path):

        # 诊断同时提供本地和远端两种合法命名形式。
        return (
            f"workspace config `{str_normalized_path}` must move under `{SETTINGS_FOLDER}/` as "
            f"`{SETTINGS_FOLDER}/<name>{LOCAL_SETTINGS_SUFFIX}` or `{SETTINGS_FOLDER}/<name>{REMOTE_SETTINGS_SUFFIX}`"
        )

    # 只有设置目录成员需要继续检查层级和后缀。
    if str_normalized_path.startswith(f"{SETTINGS_FOLDER}/"):

        # 只有显式采用设置后缀的嵌套文件才违反配置层级合同。
        if str_normalized_path.count("/") != 1:

            # 验证归档和质量证据可放在 .settings 子目录，但真实设置文件不可嵌套。
            if str_normalized_path.lower().endswith(
                (LOCAL_SETTINGS_SUFFIX, REMOTE_SETTINGS_SUFFIX)
            ):

                # 稳定诊断指明允许的直属目录边界。
                return f"workspace config `{str_normalized_path}` must live directly under `{SETTINGS_FOLDER}/`"

            # 非配置证据不参与 workspace settings 位置约束。
            return None

        # 单层 JSON 路径仍需满足合法文件名形状。
        if (
            str_normalized_path.endswith(".json")
            and not WORKSPACE_SETTINGS_JSON_RE.fullmatch(str_normalized_path)
        ):

            # 该分支区分文件名问题和目录嵌套问题。
            return (
                f"workspace config `{str_normalized_path}` must use a single filename "
                f"directly under `{SETTINGS_FOLDER}/`"
            )

        # 普通 JSON 必须选择本地或远端专用后缀。
        if str_normalized_path.endswith(".json") and not (
            WORKSPACE_SETTINGS_LOCAL_RE.fullmatch(str_normalized_path)
            or WORKSPACE_SETTINGS_REMOTE_RE.fullmatch(str_normalized_path)
        ):

            # 后缀诊断保留两种受支持配置类型。
            return (
                f"workspace settings json `{str_normalized_path}` must use `{LOCAL_SETTINGS_SUFFIX}` or "
                f"`{REMOTE_SETTINGS_SUFFIX}` suffix"
            )

    # 无关路径或满足合同的设置文件不产生位置错误。
    return None

# 远端诊断在通用位置合同之上增加本地配置隔离规则。
def remote_workspace_settings_reason(str_path: str) -> str | None:
    """返回设置文件不允许复制到远端工作区的原因。

    参数：
        str_path: 待验证的仓库相对路径。
    返回：
        可安全用于远端或无关时返回空值，否则返回稳定诊断正文。
    """

    # 远端同步检查先消除平台分隔符和重复斜杠差异。
    str_normalized_path = normalize_rel(str_path)  # 供远端复制策略检查的相对路径。

    # 目录或命名错误优先于远端专用规则报告。
    str_location_reason = workspace_settings_location_reason(str_normalized_path)  # 通用位置诊断。

    # 已有位置错误时直接保留最具体的首要原因。
    if str_location_reason:

        # 调用方无需重复生成远端后缀诊断。
        return str_location_reason

    # 本地专用文件永远不能进入服务器工作区。
    if is_workspace_settings_local(str_normalized_path):

        # 诊断明确指出发生风险的具体文件。
        return f"local-only workspace settings must never be copied to remote workspaces: `{str_normalized_path}`"

    # 设置目录中的其他 JSON 必须使用远端专用后缀。
    if (
        str_normalized_path.startswith(f"{SETTINGS_FOLDER}/")
        and str_normalized_path.endswith(".json")
        and not is_workspace_settings_remote(str_normalized_path)
    ):

        # 远端诊断同时给出目录、后缀和原始路径。
        return (
            f"remote workspace settings json must use `{REMOTE_SETTINGS_SUFFIX}` "
            f"under `{SETTINGS_FOLDER}/`: `{str_normalized_path}`"
        )

    # 合法远端设置或非设置文件无需阻断同步。
    return None

# 项目检测器通过目录扫描收集实际存在的设置文件。
def discover_workspace_settings(path_root: Path) -> list[str]:
    """发现仓库设置目录直属的 JSON 文件。

    参数：
        path_root: 待扫描项目根目录。
    返回：
        按路径排序的 POSIX 风格仓库相对路径列表。
    """

    # 扫描边界严格限定为项目根下的设置目录。
    path_settings_dir = path_root / SETTINGS_FOLDER  # 工作区设置目录绝对路径。

    # 缺少设置目录属于合法的未配置状态。
    if not path_settings_dir.is_dir():

        # 空列表让检测器保持无副作用和确定性。
        return []

    # 发现结果只收集直属 JSON 普通文件。
    list_discovered_paths: list[str] = []  # 已发现设置文件的相对路径。

    # 排序后的候选保证跨平台报告顺序稳定。
    for path_candidate in sorted(path_settings_dir.glob("*.json")):

        # 目录或特殊节点不作为配置文件上报。
        if path_candidate.is_file():

            # 输出统一使用 POSIX 分隔符便于后续正则匹配。
            list_discovered_paths.append(path_candidate.relative_to(path_root).as_posix())

    # 返回检测器可以直接序列化的稳定路径列表。
    return list_discovered_paths
