"""定义设计档案中的远程环境与运行产物归档策略。"""

# 未配置远程结构时写入显式环境禁用合同。
def disabled_remote_environment_policy() -> dict[str, Any]:
    """返回未启用远程环境管理时的显式禁用策略。

    Args:
        None: 禁用策略不依赖访谈输入。

    Returns:
        标记为 disabled 的远程环境策略。
    """

    # 保留管理器与 required 字段，使启用和禁用结构同形。
    return {
        "status": "disabled",
        "scope": "remote-only",
        "manager": "conda-prefix",
        "path_template": "",
        "required_when_remote_configured": True,
    }

# 未配置远程结构时写入显式归档禁用合同。
def disabled_remote_runtime_archive_policy() -> dict[str, Any]:
    """返回未启用远程运行归档时的显式禁用策略。

    Args:
        None: 禁用策略不依赖访谈输入。

    Returns:
        标记为 disabled 的远程归档策略。
    """

    # 禁用合同仍声明 run-id 与验证归档字段的默认边界。
    return dict(
        status="disabled",
        active_path_template="",
        backup_path_template="",
        run_id_required=True,
        archive_after_verification=False,
        archive_trigger="",
    )

# 远程环境策略要求安全的工作区相对 conda 前缀模板。
def remote_environment_policy(answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """构造远程服务器项目环境目录策略。

    Args:
        answers: 当前设计访谈答案。

    Returns:
        远程环境策略与路径验证错误列表。
    """

    # 未启用远程服务器或远程目录结构时使用同形禁用合同。
    if not remote_directory_policy_required(answers):

        # 禁用状态不产生验证错误。
        return disabled_remote_environment_policy(), []

    # 启用状态必须提供工作区相对 conda 环境模板。
    str_path_template = str(answers.get("remote_conda_environment_layout", "")).strip()  # 远程 conda 前缀模板

    # 缺少模板时无法建立隔离环境。
    if not str_path_template:

        # 错误指向访谈中的必填字段键。
        return {}, ["missing required answer: remote_conda_environment_layout"]

    # 启用远程结构后不能再用 disabled 文本绕过环境策略。
    if str_path_template.lower() == "disabled":

        # 长错误拆分为相邻字面量保持可读宽度。
        return {}, [
            "remote_conda_environment_layout cannot be `disabled` when remote "
            "structure or remote servers are enabled"
        ]

    # 通用路径验证器检查绝对路径、遍历和 shell 风险。
    str_invalid_reason = invalid_remote_relative_template_reason(str_path_template)  # 路径模板失败原因

    # 非空原因表示模板违反远程工作区边界。
    if str_invalid_reason:

        # 字段名、原因和原模板共同进入诊断。
        return {}, [f"remote_conda_environment_layout {str_invalid_reason}: {str_path_template}"]

    # 有效模板形成启用态 conda-prefix 合同。
    return {
        "status": "enabled",
        "scope": "remote-only",
        "manager": "conda-prefix",
        "path_template": str_path_template,
        "required_when_remote_configured": True,
    }, []

# 远程归档策略同时验证活动目录、备份目录和触发条件。
def remote_runtime_archive_policy(answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """构造远程运行产物归档与保留策略。

    Args:
        answers: 当前设计访谈答案。

    Returns:
        远程归档策略与配置验证错误列表。
    """

    # 未启用远程结构时保持显式禁用合同。
    if not remote_directory_policy_required(answers):

        # 禁用状态无需路径或触发条件。
        return disabled_remote_runtime_archive_policy(), []

    # 活动目录存放当前运行的可变产物。
    str_active_path = str(answers.get("remote_run_artifact_active_layout", "")).strip()  # 远程活动产物目录模板

    # 备份目录承载验证完成后的历史归档。
    str_backup_path = str(answers.get("remote_run_artifact_backup_layout", "")).strip()  # 远程归档目录模板

    # 触发文本决定何时从活动目录迁移到归档目录。
    str_trigger = str(answers.get("remote_run_archive_trigger", "")).strip()  # 远程归档触发条件

    # 三个字段的缺失错误在一次访谈轮次中完整返回。
    list_missing: list[str] = []  # 远程归档缺失字段错误

    # 活动目录是启用归档策略的必填字段。
    if not str_active_path:

        # 使用稳定字段键便于自动续问。
        list_missing.append("missing required answer: remote_run_artifact_active_layout")

    # 备份目录缺失会导致已验证产物无持久位置。
    if not str_backup_path:

        # 继续收集触发字段错误而非提前返回。
        list_missing.append("missing required answer: remote_run_artifact_backup_layout")

    # 没有触发条件时不能判断归档时机。
    if not str_trigger:

        # 触发条件错误与路径错误一起返回。
        list_missing.append("missing required answer: remote_run_archive_trigger")

    # 缺失字段优先于内容安全验证。
    if list_missing:

        # 不返回部分归档合同。
        return {}, list_missing

    # 启用远程结构时三个字段均不得使用 disabled 占位值。
    list_disabled_keys = [  # 与启用状态冲突的字段键
        key  # 当前字段名称
        for key, raw_value in {  # 启用态归档字段和值
            "remote_run_artifact_active_layout": str_active_path,  # 活动产物模板
            "remote_run_artifact_backup_layout": str_backup_path,  # 归档产物模板
            "remote_run_archive_trigger": str_trigger,  # 归档触发条件
        }.items()
        if raw_value.lower() == "disabled"  # 筛选与启用态冲突的占位值
    ]

    # 任一 disabled 值都会破坏启用态合同。
    if list_disabled_keys:

        # 每个冲突字段生成独立诊断。
        return {}, [
            f"{key} cannot be `disabled` when remote structure or remote servers are enabled"
            for key in list_disabled_keys
        ]

    # 活动与备份路径共享相同的相对路径安全规则。
    list_template_errors: list[str] = []  # 远程归档路径模板错误

    # 两个目录模板逐项验证并保留字段名。
    for key, raw_value in {
        "remote_run_artifact_active_layout": str_active_path,
        "remote_run_artifact_backup_layout": str_backup_path,
    }.items():

        # 通用验证器返回首个路径失败原因。
        str_invalid_reason = invalid_remote_relative_template_reason(raw_value)  # 当前模板失败原因

        # 有失败原因时附加字段级诊断。
        if str_invalid_reason:

            # 原始模板保留在错误中便于直接修正。
            list_template_errors.append(f"{key} {str_invalid_reason}: {raw_value}")

    # 路径错误阻止生成启用态归档合同。
    if list_template_errors:

        # 调用方一次获得活动与备份模板的全部错误。
        return {}, list_template_errors

    # 有效合同记录 run-id 占位符与验证后归档语义。
    return dict(
        status="enabled",
        active_path_template=str_active_path,
        backup_path_template=str_backup_path,
        run_id_required="<run-id>" in str_active_path or "<run-id>" in str_backup_path,
        archive_after_verification=(
            str_trigger.casefold() == "after required verification passes".casefold()
        ),
        archive_trigger=str_trigger,
    ), []

# 技能专用设计合同保留触发、资源和验证事实。
