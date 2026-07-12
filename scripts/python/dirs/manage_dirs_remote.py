"""校验远程工作区路径、运行时归档位置与受保护目录类别。"""

# 延迟解析类型注解，避免运行期求值联合类型。
from __future__ import annotations

# 通用类型用于描述从目录规划 JSON 读取的松散结构。
from typing import Any

# 工作区设置策略定义远程配置目录及其保护原因。
from workspace_settings_policy import (
    SETTINGS_FOLDER,
    remote_workspace_settings_reason,
    workspace_settings_path_classes,
# 依赖列表在此结束，后续定义只暴露纯路径策略。
)

# 路径规范化是所有远程白名单比较的共同入口。
def normalize_rel(str_raw: str) -> str:
    """将远程路径统一为无首尾分隔符的 POSIX 相对形式。

    参数：str_raw 为待规范化的远程路径文本。
    返回：使用正斜杠且移除首尾分隔符的路径。
    """

    # 远程规划合同统一使用正斜杠，避免主机平台影响比较结果。
    return str(str_raw).replace("\\", "/").strip().strip("/")

# 工作区根解析隔离问卷占位符与真实路径。
def remote_workspace_root(dict_remote_plan: dict[str, Any]) -> str:
    """返回已配置的远程工作区根目录，未配置时返回空字符串。

    参数：dict_remote_plan 为远程部署规划字典。
    返回：规范化的工作区根目录或空字符串。
    """

    # 规范化后再识别问卷使用的显式未配置标记。
    str_workspace = normalize_rel(  # 从规划中解析远程工作区根目录。
        str(dict_remote_plan.get("workspace_root", "")).strip()  # 原始工作区字段文本。
    )  # 远程工作区根目录。

    # 空值与问卷占位符都不能授权任何远程路径。
    if str_workspace in {"", "not configured"}:

        # 空根目录由调用方解释为远程目录治理未启用。
        return ""

    # 返回可用于拼接规划项的规范化根目录。
    return str_workspace

# 路径拼接保持工作区根与相对规划项之间只有一个分隔符。
def join_remote_workspace_path(str_workspace: str, str_relative: str) -> str:
    """将远程工作区根目录与规划相对路径安全拼接。

    参数：str_workspace 为根目录；str_relative 为规划相对路径。
    返回：规范化后的远程路径。
    """

    # 先规范化规划项，避免重复分隔符破坏白名单比较。
    str_relative_norm = normalize_rel(str_relative)  # 规范化后的规划相对路径。

    # 未配置根目录时保留调用方提供的路径语义。
    if not str_workspace:

        # 相对路径已经完成跨平台规范化。
        return str_relative_norm

    # 空规划项表示工作区根目录本身。
    if not str_relative_norm:

        # 根目录不需要追加路径分隔符。
        return str_workspace

    # 单个分隔符连接根目录和非空规划项。
    return f"{str_workspace.rstrip('/')}/{str_relative_norm}"

# 白名单判断允许规划项、其后代和创建结构所需的父目录。
def allowed_remote_path(str_path: str, dict_remote_plan: dict[str, Any]) -> bool:
    """判断远程路径是否落在规划项、其父目录或模板前缀内。

    参数：str_path 为待审查路径；dict_remote_plan 为远程部署规划。
    返回：路径处于授权边界时为 True，否则为 False。
    """

    # 没有明确工作区根目录时禁止远程目录变更。
    str_workspace = remote_workspace_root(dict_remote_plan)  # 远程工作区授权根目录。

    # 空根目录不能形成安全的路径边界。
    if not str_workspace:

        # 默认拒绝可防止把相对路径误判为已授权路径。
        return False

    # 调用方路径按工作区相对路径合同转换为完整远程路径。
    str_normalized = join_remote_workspace_path(  # 生成参与白名单比较的完整路径。
        str_workspace,  # 已授权的远程工作区根目录。
        str_path,  # 调用方提交的工作区相对路径。
    )  # 待审查的规范化远程路径。

    # 空规划项不参与授权，避免意外放宽到整个工作区。
    list_allowed = [  # 过滤空值并规范化全部显式规划项。
        normalize_rel(str(item))  # 单个规范化规划项。
        for item in dict_remote_plan.get("planned_structure", [])  # 逐项读取规划结构。
        if str(item).strip()  # 忽略不能形成授权边界的空规划项。
    ]  # 已声明的远程结构白名单。

    # 规划项的父目录允许被创建，以便逐层建立目标结构。
    set_parents: set[str] = set()  # 所有规划项隐含授权的父目录。

    # 每个规划项独立展开父目录，保持白名单来源可追溯。
    for str_item in list_allowed:

        # 路径片段用于构造从一级目录到直接父目录的前缀。
        list_parts = str_item.split("/")  # 当前规划项的路径片段。

        # 完整规划项由后续分支判断，此处只收集严格父目录。
        for int_index in range(1, len(list_parts)):

            # 父目录集合去重，避免重复规划项影响结果。
            set_parents.add("/".join(list_parts[:int_index]))

    # 创建规划结构所需的中间父目录属于授权范围。
    if str_normalized in set_parents:

        # 父目录仅因现有规划项而获得授权。
        return True

    # 逐项匹配精确路径、子路径和含占位符的模板前缀。
    for str_item in list_allowed:

        # 规划项本身及其后代目录均处于同一授权边界内。
        if str_normalized == str_item or str_normalized.startswith(
            str_item.rstrip("/") + "/"
        ):

            # 精确或后代匹配不需要继续检查其他规划项。
            return True

        # 尖括号标记运行编号等动态路径片段。
        if "<" in str_item and ">" in str_item:

            # 动态占位符之前的稳定前缀定义模板授权边界。
            str_prefix = str_item.split("<", 1)[0].rstrip("/")  # 模板稳定前缀。

            # 模板前缀只授权其后代，空前缀不能授权整个工作区。
            if str_prefix and str_normalized.startswith(str_prefix + "/"):

                # 动态实例路径符合已声明的规划模板。
                return True

    # 未命中任何显式或隐含规划边界时拒绝操作。
    return False

# 类别识别为破坏性远程操作提供细粒度保护依据。
def remote_path_classes(
    str_path: str,
    dict_remote_plan: dict[str, Any],
) -> list[str]:
    """识别远程路径所属的工作区、环境、运行与备份类别。

    参数：str_path 为待分类路径；dict_remote_plan 为远程部署规划。
    返回：路径命中的全部治理类别。
    """

    # 所有类别判断均基于同一种相对路径表示。
    str_normalized = normalize_rel(str_path)  # 待分类的规范化远程路径。

    # 空路径没有可保护的远程目录类别。
    if not str_normalized:

        # 调用方可将空列表视为未分类路径。
        return []

    # 所有有效路径至少属于远程路径类别，并附加设置文件类别。
    list_classes = [  # 建立远程基础类别并合并设置文件类别。
        "remote",  # 所有有效路径共有的基础类别。
        *workspace_settings_path_classes(str_normalized),  # 设置文件附加类别。
    ]  # 当前路径的治理类别。

    # 非字典配置视为空配置，避免畸形 JSON 引发属性访问错误。
    value_runtime = dict_remote_plan.get("runtime_artifacts")  # 原始运行时配置值。

    # 仅字典值可作为运行时配置读取。
    dict_runtime = value_runtime if isinstance(value_runtime, dict) else {}  # 运行时目录配置。

    # Conda 配置采用同样的容错边界。
    value_conda = dict_remote_plan.get("conda_environment")  # 原始 Conda 配置值。

    # 仅字典值可作为 Conda 配置读取。
    dict_conda = value_conda if isinstance(value_conda, dict) else {}  # Conda 环境目录配置。

    # 三类模板分别定义环境、活动运行和归档运行的路径根。
    str_conda_template = normalize_rel(  # 提取环境路径模板。
        str(dict_conda.get("path_template", "")).strip()  # 原始环境模板文本。
    )  # Conda 环境路径模板。

    # 活动模板界定尚未归档的运行实例。
    str_active_template = normalize_rel(  # 提取活动运行路径模板。
        str(dict_runtime.get("active_path_template", "")).strip()  # 原始活动模板文本。
    )  # 活动运行路径模板。

    # 备份模板界定已完成验证的归档实例。
    str_backup_template = normalize_rel(  # 提取归档运行路径模板。
        str(dict_runtime.get("backup_path_template", "")).strip()  # 原始归档模板文本。
    )  # 已验证运行归档模板。

    # 占位符之前的稳定部分用于精确根目录和后代分类。
    str_conda_root = (  # 截取 Conda 模板的稳定前缀。
        str_conda_template.split("<", 1)[0].rstrip("/")  # 占位符之前的环境路径。
        if str_conda_template  # 非空模板才产生环境根目录。
        else ""  # 未配置环境模板时不分类环境路径。
    )  # Conda 环境稳定根目录。

    # 活动运行根目录不包含动态运行编号。
    str_active_root = (  # 截取活动运行模板的稳定前缀。
        str_active_template.split("<", 1)[0].rstrip("/")  # 占位符之前的活动路径。
        if str_active_template  # 非空模板才产生活动根目录。
        else ""  # 未配置活动模板时不分类活动路径。
    )  # 活动运行稳定根目录。

    # 归档运行根目录不包含动态运行编号。
    str_backup_root = (  # 截取备份模板的稳定前缀。
        str_backup_template.split("<", 1)[0].rstrip("/")  # 占位符之前的归档路径。
        if str_backup_template  # 非空模板才产生归档根目录。
        else ""  # 未配置归档模板时不分类备份路径。
    )  # 归档运行稳定根目录。

    # 工作区根目录单独标记，供破坏性操作保护规则使用。
    if not str_path or str_normalized == remote_workspace_root(dict_remote_plan):

        # 根目录类别比通用 remote 类别具有更高风险语义。
        list_classes.append("workspace-root")

    # Conda 根目录及其后代采用不同粒度的类别标签。
    if str_conda_root:

        # 精确命中环境根目录时标记根级保护类别。
        if str_normalized == str_conda_root:

            # 根级类别可阻止删除整个环境集合。
            list_classes.append("conda-environment-root")

        # 根目录以下的具体环境属于普通环境类别。
        elif str_normalized.startswith(str_conda_root + "/"):

            # 环境实例仍受远程环境策略约束。
            list_classes.append("conda-environment")

    # 活动运行目录按根目录和具体运行实例区分。
    if str_active_root:

        # 活动运行集合的根目录需要独立保护。
        if str_normalized == str_active_root:

            # 根级标签阻止一次操作影响全部活动运行。
            list_classes.append("active-run-root")

        # 根目录以下为尚未归档的运行实例。
        elif str_normalized.startswith(str_active_root + "/"):

            # 活动运行实例需遵守验证前留存策略。
            list_classes.append("active-run")

    # 备份目录同样区分集合根目录与单个归档实例。
    if str_backup_root:

        # 精确命中备份集合根目录时使用根级类别。
        if str_normalized == str_backup_root:

            # 根级标签避免误删全部已验证归档。
            list_classes.append("backup-run-root")

        # 根目录以下为已归档的具体运行实例。
        elif str_normalized.startswith(str_backup_root + "/"):

            # 归档实例类别支持细粒度保护决策。
            list_classes.append("backup-run")

    # 返回所有命中的类别，调用方负责与保护集合求交集。
    return list_classes

# 运行时策略同时审查目标位置、制品状态和源路径保护类别。
def remote_runtime_reasons(
    str_action: str,
    str_path: str,
    str_target: str | None,
    dict_remote_plan: dict[str, Any],
    str_artifact_state: str,
) -> list[str]:
    """返回远程运行时变更违反位置、归档或保护策略的原因。

    参数：str_action 为操作；str_path 为源路径；str_target 为可选目标；
    dict_remote_plan 为远程规划；str_artifact_state 为制品验证状态。
    返回：全部策略违规原因，合规时为空列表。

    数组契约：不处理数值数组，shape、dtype 与 unit 均不适用。
    """

    # 保留运行制品配置原值，以识别非映射输入。
    value_runtime = dict_remote_plan.get("runtime_artifacts")  # 本次位置审查的配置原值。

    # 非映射输入不能提供验证阶段所需的模板合同。
    dict_runtime = value_runtime if isinstance(value_runtime, dict) else {}  # 位置审查使用的模板映射。

    # 从制品配置提取验证前的暂存位置。
    str_active_template = normalize_rel(  # 读取验证前制品位置模板。
        str(dict_runtime.get("active_path_template", "")).strip()  # 验证前位置字段。
    )  # 待验证制品暂存模板。

    # 从制品配置提取验证后的证据留存位置。
    str_backup_template = normalize_rel(  # 读取已验证制品归档模板。
        str(dict_runtime.get("backup_path_template", "")).strip()  # 验证后位置字段。
    )  # 可信制品留存模板。

    # 原路径用于设置文件保护和破坏性类别判断。
    str_normalized_path = normalize_rel(str_path)  # 规范化后的操作源路径。

    # 移动或重命名检查目标位置，其他操作检查源位置。
    str_normalized = normalize_rel(  # 选择实际需要审查的位置。
        str_target if str_target else str_path  # 有目标时优先审查目标位置。
    )  # 需要满足运行时位置策略的路径。

    # 空路径没有可判定的运行时位置。
    if not str_normalized:

        # 没有路径时不生成误导性的治理原因。
        return []

    # 每项违规独立记录，便于调用方一次展示全部阻断原因。
    list_reasons: list[str] = []  # 当前远程操作的阻断原因。

    # 本地专用设置文件不得通过远程目录操作部署。
    str_settings_reason = remote_workspace_settings_reason(  # 查询本地设置文件保护策略。
        str_normalized_path  # 设置策略审查操作源路径。
    )  # 工作区设置文件边界的阻断原因。

    # 仅在策略识别到受限设置路径时追加原因。
    if str_settings_reason:

        # 保留策略模块提供的精确用户提示。
        list_reasons.append(str_settings_reason)

    # 活动路径的稳定前缀用于识别所有未归档运行实例。
    str_active_root = (  # 截取活动模板的稳定目录前缀。
        str_active_template.split("<run-id>", 1)[0].rstrip("/")  # 去除动态运行编号。
        if str_active_template  # 配置暂存模板时才生成根目录。
        else ""  # 没有暂存模板时跳过活动区位置约束。
    )  # 验证前制品目录根。

    # 备份路径的稳定前缀用于识别所有可信归档实例。
    str_backup_root = (  # 截取备份模板的稳定目录前缀。
        str_backup_template.split("<run-id>", 1)[0].rstrip("/")  # 去除归档运行编号。
        if str_backup_template  # 已声明留存位置时解析归档根。
        else ""  # 没有留存模板时跳过归档区位置约束。
    )  # 验证后证据目录根。

    # 普通运行制品必须位于活动区，但环境、设置和备份顶层除外。
    set_exempt_roots = {  # 汇总不属于普通活动运行制品的顶层目录。
        str_backup_root.split("/", 1)[0] if str_backup_root else "",  # 备份顶层目录。
        ".conda",  # 远程隔离环境目录。
        SETTINGS_FOLDER,  # 受治理的工作区设置目录。
    }  # 不按活动运行制品处理的顶层目录。

    # 活动模板存在时才执行运行制品位置约束。
    if (
        str_active_root
        and not str_normalized.startswith(str_active_root + "/")
        and str_normalized.split("/", 1)[0] not in set_exempt_roots
    ):

        # 提示同时包含期望模板和实际路径，便于修正计划。
        list_reasons.append(
            "remote runtime artifacts must stay under "
            f"`{str_active_template}`; received `{str_normalized}`"
        )

    # 已验证制品必须从活动区迁移到备份归档区。
    if (
        str_artifact_state == "verified"
        and str_backup_root
        and not str_normalized.startswith(str_backup_root + "/")
    ):

        # 归档提示明确给出批准的备份路径模板。
        list_reasons.append(
            "verified remote runtime artifacts must be archived under "
            f"`{str_backup_template}`; received `{str_normalized}`"
        )

    # 未验证制品不得提前进入被视为可信证据的备份区。
    if (
        str_artifact_state not in {"", "verified"}
        and str_backup_root
        and str_normalized.startswith(str_backup_root + "/")
    ):

        # 提示制品先留在活动区完成验证再归档。
        list_reasons.append(
            "unverified remote runtime artifacts must stay in "
            f"`{str_active_template}` before archive; received `{str_normalized}`"
        )

    # 保护类别来自远程规划合同，空白项不能形成有效策略。
    set_protected_classes = {  # 过滤并汇总远程规划声明的保护类别。
        str(item)  # 单个非空保护类别。
        for item in dict_remote_plan.get("protected_path_classes", [])  # 逐项读取保护合同。
        if str(item).strip()  # 忽略不能命中路径类别的空策略项。
    }  # 禁止破坏性操作的远程路径类别。

    # 只有删除、移动和重命名会触发路径类别保护。
    if str_action in {"delete", "move", "rename"}:

        # 源路径类别用于判断操作是否触碰受保护边界。
        set_destructive_classes = set(  # 识别源路径触及的全部治理类别。
            remote_path_classes(str_normalized_path, dict_remote_plan)  # 源路径治理类别。
        )  # 当前破坏性操作涉及的路径类别。

        # 类别交集表示该操作命中了至少一项保护策略。
        set_blocked_classes = (  # 计算本次操作实际触发的保护类别。
            set_destructive_classes & set_protected_classes  # 破坏性类别与保护合同交集。
        )  # 实际命中的受保护类别。

        # 无交集时不添加破坏性操作原因。
        if set_blocked_classes:

            # 排序保证面向用户和测试的原因文本稳定。
            list_reasons.append(
                f"remote {str_action} is blocked for protected path classes "
                f"{sorted(set_blocked_classes)} at `{str_normalized_path}`"
            )

    # 返回所有独立原因，空列表表示远程运行时策略通过。
    return list_reasons
