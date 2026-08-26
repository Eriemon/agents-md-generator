"""校验根 AGENTS 与强控制治理合同。"""

# 标准库提供正则匹配、路径建模和通用配置载荷类型。
import re
import subprocess
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

# 共享运行时提供合同片段、配置规整和批量诊断助手。
from verify_agents_runtime_shared import (
    CODING_BEHAVIOR_LANGUAGE_ROUTING_REQUIRED_SNIPPETS,
    SCRIPT_OUTPUT_POLICY_REQUIRED_SNIPPETS,
    append_failed_checks,
    append_missing_text_requirements,
    first_section_body,
    list_value_or_empty,
    mapping_value_or_empty,

    # 文本规整、段落提取和兼容性判断位于基础配置助手之后。
    normalized_nonempty_strings,
    section_body,
    shared_task_dependencies,
    uses_legacy_language_skill_routing_rules,
    validate_language_skill_route_lines,
)
# 命令合同模块提供容错 JSON 配置读取能力。
from command_contracts import read_json
from verify_language_contracts import validate_language_profile

# 持久化验收使用固定清单文件名，不把路径片段散落在控制流中。
ARTIFACT_MANIFEST_NAME = "artifact.json"  # 知识图谱持久化清单文件名

# 压缩图数据库是 full 加 persistence 模式的第二项根级证据。
ARTIFACT_GRAPH_NAME = "graph.db.zst"  # 知识图谱压缩数据库文件名

# 知识图谱公共合同按文件位置加载，避免 CLI 入口在导入期修改 sys.path。
def load_codebase_memory_contract_module() -> ModuleType:
    """从 common 目录加载知识图谱单一事实源模块。

    参数:
        无。

    返回:
        已执行并可读取合同常量与构造器的模块对象。

    异常:
        RuntimeError: 无法创建模块规格或加载器时抛出。
    """

    # 公共合同文件位于 verify 同级的 common 目录。
    path_contract = Path(__file__).resolve().parents[1] / "common" / "codebase_memory_mcp.py"  # 知识图谱合同路径

    # 独立模块名避免覆盖调用进程中可能存在的安装副本。
    module_type_spec = importlib.util.spec_from_file_location("agents_codebase_memory_contract", path_contract)  # 模块加载规格

    # 缺失加载器表示仓库结构或 Python 导入机制已损坏。
    if module_type_spec is None or module_type_spec.loader is None:

        # 根合同无法读取单一事实源时必须明确阻断。
        raise RuntimeError("> ERR: [Python] 无法加载知识图谱公共合同模块")

    # 模块对象在执行前由标准导入工具创建。
    module_type_contract = importlib.util.module_from_spec(module_type_spec)  # 知识图谱合同模块

    # 执行源码后模块公开合同常量和构造函数。
    module_type_spec.loader.exec_module(module_type_contract)

    # 返回加载完成的单一事实源模块。
    return module_type_contract

# 画像与渲染文本校验先返回可信布尔选择，供文件系统合同继续使用。
def validated_codebase_memory_choice(
    text: str,
    file: str,
    profile: dict[str, Any],
    errors: list[str],
) -> bool | None:
    """核验知识图谱显式选择、结构化合同和根规则文本。

    参数:
        text: 当前根 AGENTS 完整文本。
        file: 错误信息使用的文件标识。
        profile: 强控制结构化画像。
        errors: 累积静态校验错误的可变列表。

    返回:
        合法显式选择返回布尔值；字段缺失或类型错误时返回 None。
    """

    # 强控制画像必须显式保存布尔选择，禁止用字段缺失推断默认值。
    raw_enabled = profile.get("use_codebase_memory_mcp")  # 原始知识图谱启用选择

    # 非布尔值无法安全决定后续持久化产物门禁。
    if not isinstance(raw_enabled, bool):

        # 精确错误说明画像缺少显式产品选择。
        errors.append(f"{file}: strong-control profile must explicitly set use_codebase_memory_mcp")

        # None 阻止调用方继续按真值解释损坏画像。
        return None

    # 结构化子合同必须与用户显式选择逐字段一致。
    module_type_contract = load_codebase_memory_contract_module()  # 画像校验使用的知识图谱模块

    # 画像子合同必须与公共构造器派生结果完全相同。
    if profile.get("codebase_memory_mcp_contract") != module_type_contract.codebase_memory_contract(raw_enabled):

        # 合同漂移必须在根文件验收中阻断。
        errors.append(f"{file}: codebase_memory_mcp_contract does not match the explicit choice")

    # 根规则必须向执行代理公开当前启用或禁用状态。
    str_expected_rule = (  # 当前选择对应的根规则片段
        "**Codebase memory MCP:** enabled"  # 启用态根规则
        if raw_enabled  # 显式启用选择
        else "**Codebase memory MCP:** disabled"  # 禁用态根规则
    )

    # 缺失根规则会让后续代理无法执行画像中的知识图谱边界。
    if str_expected_rule not in text:

        # 错误文本保留期望状态，便于精确修复渲染退化。
        errors.append(f"{file}: missing rendered codebase-memory-mcp {'enabled' if raw_enabled else 'disabled'} rule")

    # 返回经过类型核验的布尔选择供持久化产物校验。
    return raw_enabled

# 仓库边界校验确保知识图谱产物仅本地持久化且不进入 Git。
def validate_codebase_memory_artifacts(
    project: Path,
    file: str,
    bool_enabled: bool,
    errors: list[str],
) -> None:
    """核验忽略规则、Git 跟踪状态与根级持久化产物。

    参数:
        project: 当前受管项目根目录。
        file: 错误信息使用的文件标识。
        bool_enabled: 已通过类型校验的知识图谱选择。
        errors: 累积静态校验错误的可变列表。

    返回:
        无业务返回值；发现的仓库边界问题直接追加到 errors。
    """

    # 根忽略文件是本地知识图谱产物不得提交的第一层边界。
    path_gitignore = project / ".gitignore"  # 项目根 Git 忽略文件

    # 公共模块提供产物目录和根锚定忽略规则。
    module_type_contract = load_codebase_memory_contract_module()  # 仓库边界使用的知识图谱模块

    # 局部名称缩短后续 Git 和路径合同表达式。
    str_artifact_directory = module_type_contract.ARTIFACT_DIRECTORY  # 根级知识图谱产物目录名

    # 根锚定规则禁止同名嵌套目录意外放宽。
    str_ignore_rule = module_type_contract.IGNORE_RULE  # 知识图谱根忽略规则

    # 缺失忽略文件时使用空集合，统一进入精确缺规则诊断。
    set_ignore_lines = (  # 规整后的根忽略规则集合
        {str_line.strip() for str_line in path_gitignore.read_text(encoding="utf-8").splitlines()}  # 规整已有规则
        if path_gitignore.is_file()  # 根忽略文件存在
        else set()  # 缺失文件对应空规则集合
    )

    # 本地知识图谱目录必须由根级精确规则排除。
    if str_ignore_rule not in set_ignore_lines:

        # 缺失忽略规则会产生发布污染风险。
        errors.append(f"{file}: root .gitignore must contain {str_ignore_rule}")

    # Git 索引查询验证历史文件也没有继续被跟踪。
    process_tracked = subprocess.run(  # 知识图谱目录 Git 跟踪查询
        ["git", "ls-files", "--", str_artifact_directory],  # 精确查询本地产物目录
        cwd=project,  # 在当前受管项目执行查询
        capture_output=True,  # 捕获跟踪文件清单
        text=True,  # 以文本形式解析 Git 输出
        encoding="utf-8",  # 固定跨平台输出编码
        errors="replace",  # 非法字节不应中断治理检查
        check=False,  # 返回码由下方合同显式判断
    )

    # 成功查询且存在输出表示本地产物仍污染版本历史。
    if process_tracked.returncode == 0 and process_tracked.stdout.strip():

        # 跟踪污染必须先解除才能通过根合同验收。
        errors.append(f"{file}: {str_artifact_directory} must not contain Git-tracked files")

    # 禁用知识图谱时只要求仓库边界，不要求持久化产物存在。
    if not bool_enabled:

        # 禁用路径完成校验后直接结束。
        return

    # 启用态清单与图数据库只允许位于固定的根隐藏目录。
    path_artifact = project / str_artifact_directory  # 启用态持久化证据查找目录

    # 清单与压缩图数据库共同构成完整持久化证据。
    if not (path_artifact / ARTIFACT_MANIFEST_NAME).is_file() or not (path_artifact / ARTIFACT_GRAPH_NAME).is_file():

        # 任一关键产物缺失都不能声称 full persistence 已完成。
        errors.append(f"{file}: enabled codebase-memory-mcp requires root persistence artifacts")

    # 全仓扫描清单文件，阻止子目录形成第二个知识图谱根。
    for path_nested in project.glob(f"**/{str_artifact_directory}/{ARTIFACT_MANIFEST_NAME}"):  # 候选知识图谱清单

        # 根 .cbmignore 明确排除的授权快照不属于当前项目边界。
        if module_type_contract.is_path_excluded_by_cbmignore(project, path_nested):

            # 继续检查项目边界内的其他候选清单。
            continue

        # 只有项目根固定目录允许保存持久化清单。
        if path_nested.parent != path_artifact:

            # 嵌套产物会破坏单一项目根和发布边界。
            errors.append(
                f"{file}: nested codebase-memory artifact is forbidden: "
                f"{path_nested.relative_to(project).as_posix()}"
            )

# 公开根合同入口组合画像、渲染文本与文件系统三层证据。
def validate_codebase_memory_mcp_contract(
    text: str,
    file: str,
    project: Path,
    profile: dict[str, Any],
    errors: list[str],
) -> None:
    """静态核验显式开关、根规则、忽略项和持久化产物位置。

    参数:
        text: 当前根 AGENTS 完整文本。
        file: 错误信息使用的文件标识。
        project: 当前受管项目根目录。
        profile: 强控制结构化画像。
        errors: 累积静态校验错误的可变列表。

    返回:
        无业务返回值；发现的问题直接追加到 errors。
    """

    # 首先核验显式选择、画像子合同和用户可见根规则。
    bool_enabled = validated_codebase_memory_choice(text, file, profile, errors)  # 已校验知识图谱选择

    # 损坏选择已产生精确诊断，不能继续推断文件系统要求。
    if bool_enabled is None:

        # 返回避免将缺失字段误判为禁用选择。
        return

    # 合法布尔选择进入忽略、Git 跟踪和持久化产物验收。
    validate_codebase_memory_artifacts(project, file, bool_enabled, errors)

# 远程路由助手核对服务器注册表及每条任务路由引用。
def validate_remote_route_data(file: str, dict_remote_contract: dict[str, Any], errors: list[str]) -> None:
    """验证已启用远程契约的数据结构和服务器引用。

    参数：file 为错误来源，dict_remote_contract 为远程配置，errors 为诊断列表。
    返回：无业务返回值，发现的问题直接追加到 errors。
    """

    # 注册表提供主备服务器引用的权威标识集合。
    list_registry = list_value_or_empty(dict_remote_contract, "server_registry")  # 注册服务器列表。

    # 开启远程契约后必须声明至少一个服务器。
    if not list_registry:

        # 缺失注册表会使所有任务路由无法解析。
        errors.append(f"{file}: remote_server_contract.enabled requires server_registry")

    # 任务路由描述任务与主备服务器之间的映射。
    list_routes = list_value_or_empty(dict_remote_contract, "task_routes")  # 远程任务路由列表。

    # 空路由列表无法指导执行层分发任务。
    if not list_routes:

        # 配置启用但没有路由时登记根因。
        errors.append(f"{file}: remote_server_contract.enabled requires task_routes")

    # 只保留有效对象中的非空服务器标识。
    list_registry_id_candidates = [  # 注册表中的服务器标识候选值。
        str(object_item.get("id", "")).strip()  # 当前注册项声明的服务器标识。
        for object_item in list_registry  # 遍历所有注册服务器配置项。
        if isinstance(object_item, dict)  # 非对象项不能提供服务器标识。
    ]

    # 集合用于主服务器和备用服务器的常数时间引用检查。
    set_registry_ids = {str_item for str_item in list_registry_id_candidates if str_item}  # 有效服务器标识集合。

    # 每条任务路由必须包含任务、主服务器和路由任务清单。
    for object_route in list_routes:

        # 非对象路由无法表达结构化字段。
        if not isinstance(object_route, dict):

            # 类型错误单独报告后跳过该元素。
            errors.append(f"{file}: remote_server_contract.task_routes must contain objects")

            # 当前无效元素不能继续读取路由字段。
            continue

        # 任务名称标识当前路由条目的业务入口。
        str_task_name = str(object_route.get("task_name", "")).strip()  # 当前远程任务名称。

        # 主服务器标识确定路由的首选执行目标。
        str_primary_server_id = str(object_route.get("primary_server_id", "")).strip()  # 当前主服务器标识。

        # 备用服务器列表保持配置声明的故障转移顺序。
        list_fallback_server_ids = normalized_nonempty_strings(  # 当前备用服务器标识列表。
            object_route.get("fallback_server_ids")  # 原始备用服务器配置值。
        )  # 去除空白和空值后的备用服务器序列。

        # 路由任务清单决定哪些执行任务命中当前条目。
        list_route_tasks = normalized_nonempty_strings(object_route.get("route_tasks"))  # 当前路由覆盖任务列表。

        # 缺少任务名称会让路由条目无法被明确识别。
        if not str_task_name:

            # 报告字段缺失而不是继续制造服务器相关噪声。
            errors.append(f"{file}: remote_server_contract.task_routes requires task_name")

        # 主服务器字段必须存在且引用注册表。
        if not str_primary_server_id:

            # 只有备用服务器的路由不具备首选目标。
            errors.append(f"{file}: remote_server_contract.task_routes requires primary_server_id")

        # 非空主服务器仍必须来自注册表。
        elif str_primary_server_id not in set_registry_ids:

            # 未知主服务器标识会使运行时路由失真。
            errors.append(
                f"{file}: remote_server_contract.task_routes references "
                f"unknown primary_server_id `{str_primary_server_id}`"
            )

        # 备用服务器逐项核对注册表引用。
        for str_fallback_server_id in list_fallback_server_ids:

            # 未注册备用目标不能进入自动故障转移链。
            if str_fallback_server_id not in set_registry_ids:

                # 诊断回显具体未知标识便于修正配置。
                errors.append(
                    f"{file}: remote_server_contract.task_routes references "
                    f"unknown fallback_server_id `{str_fallback_server_id}`"
                )

        # 空任务清单无法让执行层匹配当前路由。
        if not list_route_tasks:

            # 明确要求 route_tasks 字段完整存在。
            errors.append(f"{file}: remote_server_contract.task_routes requires route_tasks")

# 远程服务器验证入口核对注册表、任务路由和渲染约束。
def validate_remote_server_contract(text: str, file: str, dict_profile: dict[str, Any], errors: list[str]) -> None:
    """校验强控制项目的 Remote Server Contract 渲染内容。

    参数:
        text: 当前待检查的 AGENTS.md 全文。
        file: 当前错误信息应写回的文件标识。
        dict_profile: 当前项目 profile 映射，用于读取 `remote_server_contract` 配置。
        errors: 诊断累积列表，函数会直接向其中追加错误信息。

    返回:
        无业务返回值；所有诊断都通过 `errors` 原地返回。
    """

    # 先把远程契约规整成映射，避免后续字段访问被错误类型打断。
    dict_remote_contract = mapping_value_or_empty(dict_profile, "remote_server_contract")  # 规范化后的远程契约配置

    # 缺少远程契约配置时，不需要强行要求 AGENTS 输出对应段落。
    if not dict_remote_contract:

        # 直接结束校验，让无远程配置的项目保持静默通过。
        return

    # 列出远程契约允许回退命中的标题集合，兼容老段落名和 task-specific gates 回退入口。
    tuple_remote_section_headings = ("## Remote Server Contract", "## Task-specific gates")  # 远程契约候选标题

    # 提取远程契约正文，后续所有固定短语都在这一段中检查。
    str_remote_body = first_section_body(text, tuple_remote_section_headings)  # 远程服务器契约段落正文

    # 强控制 profile 一旦声明远程契约，就必须在 AGENTS 中看到对应段落。
    if str_remote_body is None:

        # 直接指出缺段落问题，避免用户误以为是字段内容校验失败。
        errors.append(
            f"{file}: strong-control profile with enabled remote_server_contract requires remote task-specific gates",
        )

        # 缺少正文时，后续短语检查没有意义，立即停止。
        return

    # 远程能力被禁用时，只保留段落存在性判断，不强制写出详细负信息。
    if not dict_remote_contract.get("enabled"):

        # 结束禁用场景校验，避免对关闭特性的项目追加无效错误。
        return

    # 数据层验证独立检查注册表、任务字段和主备服务器引用。
    validate_remote_route_data(file, dict_remote_contract, errors)

    # 逐条检查正文短语，防止 AGENTS 渲染时丢掉关键执行约束。
    append_missing_text_requirements(
        str_remote_body,
        [
            (
                "Route source: `.agents/agents-control.json` field `remote_server_contract`.",
                f"{file}: Remote Server Contract must point to `.agents/agents-control.json` remote_server_contract",
            ),
            (
                "Resolve primary and fallback servers from the route source at execution time",
                f"{file}: Remote Server Contract must keep remote routing details in the profile source",
            ),
            (
                "automatically try registered fallback servers in route order",
                f"{file}: Remote Server Contract must enforce automatic fallback routing",
            ),
            (
                "stop and update the current work folder AGENTS.md/profile before continuing",
                f"{file}: Remote Server Contract must enforce unmatched-task blocking",
            ),
        ],
        errors,
    )

# 远程目录策略助手核对环境模板、归档字段和总规则指针。
def validate_remote_directory_policies(
    str_directory_body: str,
    file: str,
    dict_remote_environment: dict[str, Any],
    dict_remote_runtime: dict[str, Any],
    errors: list[str],
) -> None:
    """验证目录合同中的远程环境和运行时归档配置。

    参数：str_directory_body 为正文，file 为文件标识。
    参数：dict_remote_environment 与 dict_remote_runtime 为远程策略。
    参数：errors 为共享诊断列表。
    返回：无业务返回值，发现的问题直接追加到 errors。
    """

    # 启用远程环境时必须声明可解析的路径模板。
    if dict_remote_environment.get("status") == "enabled":

        # 路径模板确定远程隔离环境的实际落点。
        str_remote_environment_template = str(  # 远程环境路径模板。
            dict_remote_environment.get("path_template", "")  # profile 中声明的原始模板。
        ).strip()  # 去除配置值两端空白。

        # 空模板表示启用状态仍不可执行。
        if not str_remote_environment_template:

            # 诊断明确定位到远程环境策略字段。
            errors.append(
                f"{file}: directory_contract.remote_environment_policy."
                f"path_template must be configured when enabled"
            )

    # 启用运行时归档时必须同时具备当前、备份和触发字段。
    if dict_remote_runtime.get("status") == "enabled":

        # 当前路径模板确定在线运行目录。
        str_active_path = str(dict_remote_runtime.get("active_path_template", "")).strip()  # 当前运行目录模板。

        # 备份路径模板确定历史运行目录的归档落点。
        str_backup_path = str(dict_remote_runtime.get("backup_path_template", "")).strip()  # 历史备份目录模板。

        # 触发器说明何时把当前目录转换为历史快照。
        str_archive_trigger = str(dict_remote_runtime.get("archive_trigger", "")).strip()  # 归档触发条件。

        # 三项字段统一检查可避免半配置状态被误认为可执行。
        append_failed_checks(
            errors,
            [
                (
                    bool(str_active_path),
                    f"{file}: directory_contract.remote_runtime_archive_policy."
                    f"active_path_template must be configured when enabled",
                ),
                (
                    bool(str_backup_path),
                    f"{file}: directory_contract.remote_runtime_archive_policy."
                    f"backup_path_template must be configured when enabled",
                ),
                (
                    bool(str_archive_trigger),
                    f"{file}: directory_contract.remote_runtime_archive_policy."
                    f"archive_trigger must be configured when enabled",
                ),
            ],
        )

    # 任一远程策略启用时正文都必须引用部署总规则。
    bool_remote_policy_enabled = (  # 是否存在需要总规则指针的远程目录策略。
        dict_remote_environment.get("status") == "enabled"  # 远程环境策略已启用。
        or dict_remote_runtime.get("status") == "enabled"  # 运行时归档策略已启用。
    )

    # 总规则路径缺失会让远程执行缺少完整目录合同。
    if bool_remote_policy_enabled:

        # Path 构造避免把仓库相对路径误判为硬编码运行路径。
        str_planned_structure_path = (Path("docs") / "dir_manager" / "planned_structure.json").as_posix()  # 部署总规则路径。

        # 已回显总规则路径时无需登记诊断。
        if str_planned_structure_path not in str_directory_body:

            # 错误提示保留公开文档路径便于用户定位。
            errors.append(
                f"{file}: Directory Contract must point remote deployment policy "
                f"to `{str_planned_structure_path}`"
            )

# 目录验证入口核对本地配置、远程环境和运行时归档合同。
def validate_directory_contract(text: str, file: str, dict_profile: dict[str, Any], errors: list[str]) -> None:
    """校验强控制项目的 Directory Contract 段落是否保留关键目录约束。

    参数:
        text: 当前待检查的 AGENTS.md 全文。
        file: 当前错误信息应写回的文件标识。
        dict_profile: 当前项目 profile 映射，用于读取 directory_contract 配置。
        errors: 共享错误列表，函数会直接向其中追加诊断。

    返回:
        无业务返回值；所有问题都通过 `errors` 原地返回。
    """

    # 读取目录契约配置块，后续所有字段都从这份 profile 映射展开。
    dict_directory_contract = mapping_value_or_empty(dict_profile, "directory_contract")  # 从 profile 中提取目录契约配置

    # 提取目录契约正文，缺少段落时立刻终止这条验证链。
    str_directory_body = first_section_body(text, ("## Directory Contract", "## Task-specific gates"))  # 定位目录契约在根文件中的正文块

    # 强控制项目缺少目录契约正文时，后续路径和远程规则检查都没有继续意义。
    if str_directory_body is None:

        # 直接登记缺段落根因，让调用方优先恢复目录契约入口。
        errors.append(f"{file}: strong-control profile requires directory task-specific gates")

        # 没有正文可检时，停止当前目录契约校验。
        return

    # 汇总 settings 子策略，后续要核对 local/remote 默认文件是否被正文点名。
    dict_settings_policy = mapping_value_or_empty(dict_directory_contract, "workspace_settings_policy")  # 提取 workspace settings 子策略

    # 汇总远程环境子策略，后续据此判断是否必须声明远程环境路径模板。
    dict_remote_environment = mapping_value_or_empty(dict_directory_contract, "remote_environment_policy")  # 提取远程环境子策略

    # 汇总远程归档子策略，后续据此检查 active、backup 和 trigger 三元组。
    dict_remote_runtime = mapping_value_or_empty(dict_directory_contract, "remote_runtime_archive_policy")  # 提取远程归档子策略

    # 读取 settings 根目录，后续要用它检查 `*.local.json` 的本地限定语句。
    str_settings_folder = str(dict_settings_policy.get("folder", ".settings")).strip() or ".settings"  # 用于拼接 local-only 规则的 settings 根目录

    # 读取本地 settings 默认文件路径，用它校验本地配置落点是否被正文回显。
    str_local_default_path = (Path(".settings") / "project.local.json").as_posix()  # 本地默认 settings 文件约定值

    # 先读取 profile 覆盖的本地 settings 默认文件候选值，再决定是否回退到约定值。
    str_local_default_candidate = str(dict_settings_policy.get("local_default_file", str_local_default_path)).strip()  # 本地 settings 默认文件候选值

    # 候选值为空时回退到约定值，得到正文必须回显的本地 settings 默认文件路径。
    str_local_default = str_local_default_candidate or str_local_default_path  # 读取本地默认 settings 文件路径

    # 读取远程 settings 默认文件路径，用它校验远程配置落点是否被正文回显。
    str_remote_default_path = (Path(".settings") / "project.remote.json").as_posix()  # 远程默认 settings 文件约定值

    # 这里先拿到 profile 对远程 settings 默认文件的显式覆盖，后面再决定是否退回仓库约定值。
    str_remote_default_candidate = str(dict_settings_policy.get("remote_default_file", str_remote_default_path)).strip()  # 远程 settings 默认文件候选值

    # 只有远程候选值为空时才回退到约定值，避免远程部署正文示例被旧默认值覆盖。
    str_remote_default = str_remote_default_candidate or str_remote_default_path  # 读取远程默认 settings 文件路径

    # 读取主工程根目录边界，只有显式配置时才要求正文同步回显。
    str_primary_root = str(dict_directory_contract.get("primary_project_root", "")).strip().rstrip("/")  # 主工程根目录边界

    # 一次性执行所有无条件目录正文检查，确保 settings 约束和目录 review 入口都还在。
    append_failed_checks(
        errors,
        [
            (
                str_local_default in str_directory_body,
                (
                    f"{file}: Directory Contract must include local workspace "
                    f"settings path `{str_local_default}`"
                ),
            ),
            (
                str_remote_default in str_directory_body,
                (
                    f"{file}: Directory Contract must include remote workspace "
                    f"settings path `{str_remote_default}`"
                ),
            ),
            (
                f"`{(Path(str_settings_folder) / '*.local.json').as_posix()}`" in str_directory_body
                or (Path(str_settings_folder) / "*.local.json").as_posix() in str_directory_body,
                f"{file}: Directory Contract must state that local wildcard settings are local-only",
            ),
            (
                "server_list.local.json" in str_directory_body,
                (
                    f"{file}: Directory Contract must explicitly forbid "
                    f"copying server_list.local.json to remote servers"
                ),
            ),
            (
                "manage_dirs.py" in str_directory_body
                and "review" in str_directory_body,
                f"{file}: directory gates must include directory review command",
            ),
        ],
    )

    # 只有 profile 明确声明主工程根目录时，才要求正文同步回显这条边界。
    if str_primary_root and str_primary_root not in str_directory_body:

        # 把缺失的主工程边界直接回显到错误消息里，方便定位渲染漏项。
        errors.append(f"{file}: directory gates must include primary project root `{str_primary_root}`")

    # 远程字段和文档指针由专用助手统一核对。
    validate_remote_directory_policies(
        str_directory_body,
        file,
        dict_remote_environment,
        dict_remote_runtime,
        errors,
    )

# 记忆合同验证入口核对 exact-cwd 会话治理和文档指针。
def validate_strong_control_memory_contract(
    text: str,
    file: str,
    dict_profile: dict[str, Any],
    errors: list[str],
) -> None:
    """校验强控制项目的 memory 契约正文是否完整。

    参数:
        text: 当前待检查的 AGENTS.md 全文。
        file: 当前错误信息应写回的文件标识。
        dict_profile: 当前项目 profile 映射。
        errors: 共享错误列表，函数会直接向其中追加诊断。

    返回:
        无业务返回值；所有问题都通过 `errors` 原地返回。
    """

    # 读取 memory 契约配置，后续据此判断是否必须出现 memory CLI 和文档指针。
    dict_memory_contract = mapping_value_or_empty(dict_profile, "memory_contract")  # memory 契约配置

    # 记录 memory 是否启用，未启用时整个 memory 契约链路直接静默跳过。
    bool_memory_enabled = bool(dict_memory_contract.get("enabled", dict_profile.get("memory_enabled", False)))  # memory 是否启用

    # memory 未启用时，不需要强行要求根文件保留对应段落。
    if not bool_memory_enabled:

        # 直接结束当前 memory 契约校验，避免误伤无记忆仓库。
        return

    # 先确认根文件里确实保留了 memory 入口，否则正文短语检查没有目标。
    if "## Memory Contract" not in text and "## Task-specific gates" not in text:

        # 缺少 memory 入口段时直接登记强控制根因。
        errors.append(f"{file}: missing memory task-specific gates")

    # 抽出 memory 段落正文，后续统一核对 memory CLI 和文档指针。
    str_memory_body = first_section_body(text, ("## Memory Contract", "## Task-specific gates")) or ""  # memory 契约正文

    # 批量核对 memory 正文必备短语，避免根文件静默丢掉 exact-cwd 会话治理规则。
    append_missing_text_requirements(
        str_memory_body,
        [
            (
                (Path("docs") / "memory" / "MEMORY.md").as_posix(),
                f"{file}: Memory Contract must point to the governed memory guide",
            ),
            ("memory-read", f"{file}: Memory Contract must include memory-read guidance"),
            ("memory-gate", f"{file}: Memory Contract must include memory-gate guidance"),
            (
                "memory-bootstrap-sessions",
                (
                    f"{file}: Memory Contract must include exact-cwd "
                    f"session bootstrap guidance"
                ),
            ),
        ],
        errors,
    )

# 分支策略助手核对不可放宽的 worktree 配置真值。
def validate_worktree_branch_policy(dict_profile: dict[str, Any], file: str, errors: list[str]) -> None:
    """验证 profile 中的额外 worktree 禁令和污染目录集合。

    参数：dict_profile 为项目画像，file 为文件标识，errors 为诊断列表。
    返回：无业务返回值，配置问题直接追加到 errors。
    """

    # 分支策略提供不可配置放宽的 worktree 基础合同。
    dict_branch_policy = dict_profile.get("git_branch_policy", {})  # 当前 profile 的分支治理配置。

    # 固定目录集合确保常见 worktree 污染名称全部受阻。
    set_required_directory_names = {  # 不可放宽的 worktree 目录名称。
        ".worktrees",  # 点前缀复数目录。
        "worktrees",  # 普通复数目录。
        ".git-worktrees",  # Git 点前缀目录。
        "git-worktrees",  # Git 普通目录。
    }

    # profile 中声明的目录名称用于检查固定集合是否完整。
    set_configured_directory_names = (  # 当前 profile 实际禁止的 worktree 目录集合。
        set(dict_branch_policy.get("forbidden_worktree_directory_names", []))  # 映射中的禁止目录列表。
        if isinstance(dict_branch_policy, dict)  # 只从有效分支策略映射读取。
        else set()  # 非映射配置不能声明任何有效目录。
    )

    # 强控制分支策略必须明确禁止所有额外 worktree。
    if not isinstance(dict_branch_policy, dict) or not dict_branch_policy.get("additional_worktrees_forbidden"):

        # 开关缺失或关闭都会破坏不可放宽的分支隔离合同。
        errors.append(f"{file}: git_branch_policy.additional_worktrees_forbidden must be true")

    # 配置目录集合必须覆盖所有固定污染名称。
    if not set_required_directory_names.issubset(set_configured_directory_names):

        # 缺少任一固定名称都会留下可绕过的工作树目录。
        errors.append(
            f"{file}: git_branch_policy.forbidden_worktree_directory_names "
            f"must include all fixed reserved names"
        )

# 发布合同验证入口核对 worktree 禁令和版本化安装规则。
def validate_strong_control_release_contract(
    text: str,
    file: str,
    dict_profile: dict[str, Any],
    errors: list[str],
) -> None:
    """校验强控制项目的 Release Contract 段落是否完整。

    参数:
        text: 当前待检查的 AGENTS.md 全文。
        file: 当前错误信息应写回的文件标识。
        dict_profile: 当前项目 profile 映射。
        errors: 共享错误列表，函数会直接向其中追加诊断。

    返回:
        无业务返回值；所有问题都通过 `errors` 原地返回。
    """

    # profile 数据层禁令先于渲染正文检查执行。
    validate_worktree_branch_policy(dict_profile, file, errors)

    # git 托管模式为空时，不要求根文件额外保留 Release Contract。
    str_git_management = str(dict_profile.get("git_management", "")).strip()  # git 托管模式

    # 只有声明了 git 托管的强控制项目，才要求 Release Contract 同步存在。
    if str_git_management not in {"yes-local-only", "remote-allowed"}:

        # 非 git 托管项目不进入 Release Contract 校验链路。
        return

    # 提取 Release Contract 正文，用它核对 git 工作树禁令和紧凑发布指针。
    str_release_body = first_section_body(text, ("## Release Contract", "## Task-specific gates"))  # 提取 Release Contract 正文块

    # 缺少 release 段落时先给出根因，不再继续做正文短语校验。
    if str_release_body is None:

        # 强控制 git 项目必须显式保留 Release Contract 入口。
        errors.append(f"{file}: git-managed strong-control project requires ## Release Contract")

        # 缺少 release 段落时，当前 release 校验链路在这里结束。
        return

    # 段落必须同时禁止额外 worktree、创建命令和 core.worktree 重定向。
    tuple_required_worktree_phrases = (  # 发布正文必须保留的 worktree 禁令片段。
        "Do not create or use additional Git worktrees",  # 总体禁令。
        "git worktree add",  # 创建命令禁令。
        "git config core.worktree",  # 工作目录重定向禁令。
        ".worktrees",  # 点前缀污染目录。
        ".git-worktrees",  # Git 专用点前缀污染目录。
        "local branches for isolation",  # 本地分支替代方案。
    )

    # 缺少任一固定短语都表示根规则未完整表达硬禁令。
    if any(str_phrase not in str_release_body for str_phrase in tuple_required_worktree_phrases):

        # 直接提示缺的是 core.worktree 禁令，方便回到 Release Contract 修复。
        errors.append(
            f"{file}: Release Contract must explicitly forbid "
            f"additional worktrees, `git worktree add`, `git config core.worktree`, "
            f"reserved worktree directories, and local-branch isolation"
        )

        # 缺少 core.worktree 禁令时，不再继续检查紧凑发布短语。
        return

    # 入口和禁令都存在时，再批量核对紧凑发布正文必须回显的固定短语。
    append_missing_text_requirements(
        str_release_body,
        [
            (
                (Path(".agents") / "agents-control.json").as_posix(),
                (
                    f"{file}: Release Contract must include compact "
                    f"release governance phrase `.agents/agents-control.json`"
                ),
            ),
            (
                (Path("docs") / "git_manager").as_posix() + "/",
                (
                    f"{file}: Release Contract must include compact "
                    f"release governance phrase `docs/git_manager/`"
                ),
            ),
            (
                "script-guide",
                (
                    f"{file}: Release Contract must include compact "
                    f"release governance phrase `script-guide`"
                ),
            ),
            (
                "RELEASE_RECEIPT.json",
                (
                    f"{file}: Release Contract must include compact "
                    f"release governance phrase `RELEASE_RECEIPT.json`"
                ),
            ),
            (
                "source directory installs are forbidden",
                (
                    f"{file}: Release Contract must include compact "
                    f"release governance phrase "
                    f"`source directory installs are forbidden`"
                ),
            ),
            (
                "Different-version release directories and matching zip files are immutable history",
                (
                    f"{file}: Release Contract must include compact "
                    f"release governance phrase "
                    f"`Different-version release directories and matching zip files are immutable history`"
                ),
            ),
        ],
        errors,
    )

# 技能合同验证入口核对触发场景、设计模式和验证门禁。
def validate_strong_control_skill_contract(
    text: str,
    file: str,
    dict_profile: dict[str, Any],
    errors: list[str],
) -> None:
    """校验强控制 skill 项目的 Skill Design Contract 段落是否完整。

    参数:
        text: 当前待检查的 AGENTS.md 全文。
        file: 当前错误信息应写回的文件标识。
        dict_profile: 当前项目 profile 映射。
        errors: 共享错误列表，函数会直接向其中追加诊断。

    返回:
        无业务返回值；所有问题都通过 `errors` 原地返回。
    """

    # 只有 skill 项目才要求保留 Skill Design Contract。
    if dict_profile.get("kind") != "skill":

        # 非 skill 项目不进入 Skill Design Contract 校验链路。
        return

    # 提取 Skill Design Contract 正文，缺段落时直接阻断后续 skill 特定检查。
    str_contract_body = first_section_body(text, ("## Skill Design Contract", "## Task-specific gates"))  # skill 设计契约正文

    # 缺少 skill 设计契约时，根文件已经不满足最小设计门禁。
    if str_contract_body is None:

        # 直接登记 skill 设计契约缺失，并停止 skill 专属检查。
        errors.append(f"{file}: strong-control skill project requires ## Skill Design Contract")

        # 没有 skill 契约正文时，当前 skill 校验链路在这里结束。
        return

    # 先检查 skill 契约的必备标题短语，再检查是否还留着 not specified 占位文本。
    append_missing_text_requirements(
        str_contract_body,
        [
            ("Validation gates:", f"{file}: Skill Design Contract missing Validation gates:"),
            ("Forward testing:", f"{file}: Skill Design Contract missing Forward testing:"),
        ],
        errors,
    )

    # 这些占位文本一旦还在，就说明 skill 设计契约没有真正完成落盘。
    for str_vague_marker in (
        "Trigger scenarios: not specified",
        "Design patterns: not specified",
        "Resource boundaries: not specified",
        "Progressive disclosure: not specified",
        "Validation gates: not specified",
        "Forward testing: not specified",
    ):

        # 发现占位文本时直接登记 unresolved default，避免发布时带着模板残留通过。
        if str_vague_marker in str_contract_body:

            # 保留原始 marker 内容，方便回到具体行修复。
            errors.append(f"{file}: Skill Design Contract contains unresolved default: {str_vague_marker}")

    # 提取 Validation gates 行，后续用它核对 quick_validate、audit 和 verify 三个关键词。
    obj_gates_match = re.search(r"Validation gates:\s*(.+)", str_contract_body, flags=re.IGNORECASE)  # 捕获 Validation gates 行里的门禁说明文本

    # 把匹配结果规整成小写文本，便于做大小写无关的关键词检查。
    str_gates_text = obj_gates_match.group(1).lower() if obj_gates_match else ""  # 小写化门禁正文

    # 批量核对 skill 设计契约的核心门禁关键词，避免 AGENTS 根文件只保留空壳标题。
    append_failed_checks(
        errors,
        [
            (
                "quick_validate" in str_gates_text,
                (
                    f"{file}: Skill Design Contract validation gates "
                    f"must include quick_validate"
                ),
            ),
            ("audit" in str_gates_text, f"{file}: Skill Design Contract validation gates must include audit"),
            ("verify" in str_gates_text, f"{file}: Skill Design Contract validation gates must include verify"),
        ],
    )

# 本地配置验证入口核对治理文件与渲染文本的一致性。
def validate_strong_control_local_config(
    text: str,
    file: str,
    project: Path,
    dict_profile: dict[str, Any],
    errors: list[str],
) -> None:
    """校验强控制根文件的本地治理配置入口与细粒度规则边界。

    参数:
        text: 当前待检查的 AGENTS.md 全文。
        file: 当前错误信息应写回的文件标识。
        project: 当前项目根目录路径。
        dict_profile: 当前项目 profile 映射。
        errors: 共享错误列表，函数会直接向其中追加诊断。

    返回:
        无业务返回值；所有问题都通过 `errors` 原地返回。
    """

    # 读取一次共享依赖映射，后续通过局部句柄访问本地治理配置加载器。
    dict_shared_dependencies = shared_task_dependencies()  # 跨任务共享依赖映射

    # 读取本地治理配置，用它核对根文件指针与配置子块结构。
    dict_config = dict_shared_dependencies["load_global_rule_overrides"](project, dict_profile)  # 本地治理配置加载结果

    # 计算配置文件相对路径，后续同时用于正文指针检查和错误回显。
    str_config_path = dict_config["path"].relative_to(project).as_posix()  # 本地治理配置相对路径

    # 先检查根文件是否回指了本地治理配置文件，以及该文件是否真实存在。
    append_failed_checks(
        errors,
        [
            (
                str_config_path in text,
                (
                    f"{file}: strong-control root must reference local "
                    f"governance config `{str_config_path}`"
                ),
            ),
            (dict_config["exists"], f"{file}: missing local governance config `{str_config_path}`"),
        ],
    )

    # 配置文件存在但结构有误时，把每条配置错误折叠进 AGENTS 校验结果。
    for str_config_error in dict_config["errors"]:

        # 保留底层配置错误原文，方便从 AGENTS verifier 直接回跳到配置修复。
        errors.append(f"{file}: invalid local governance config `{str_config_path}`: {str_config_error}")

    # 这些细粒度本地规则必须待在 JSON config 中，不能重新回流到根 AGENTS 文本。
    for str_forbidden_snippet in (
        "Single-file maintainability",
        (Path("docs") / "development" / "decomposition-plans").as_posix() + "/",
        (Path(".agents") / "script-governance-exceptions.json").as_posix(),
        "Project tool scripts must live under",
        (Path("scripts") / "<family>" / "<function>" / "<name>.<ext>").as_posix(),
    ):

        # 根文件重新出现这些细节时，说明本地规则没有正确留在 JSON config 层。
        if str_forbidden_snippet in text:

            # 直接回显越界的片段内容，方便定位是哪条细节重新泄露到了根文件。
            errors.append(
                f"{file}: local rule detail must move to JSON config instead "
                f"of AGENTS text ({str_forbidden_snippet})"
            )

# 强控制聚合入口串联目录、记忆、发布和技能合同验证。
def validate_strong_control(text: str, file: str, project: Path, errors: list[str]) -> None:
    """校验强控制根 AGENTS 是否保留 profile、docs 和治理入口的关键约束。

    参数:
        text: 当前待检查的 AGENTS.md 全文。
        file: 当前错误信息应写回的文件标识。
        project: 当前项目根目录路径。
        errors: 共享错误列表，函数会直接向其中追加诊断。

    返回:
        无业务返回值；所有问题都通过 `errors` 原地返回。
    """

    # 先缓存强控制链路要用到的 docs 校验依赖，避免当前 helper 再次探测导入路径。
    dict_shared_dependencies = shared_task_dependencies()  # 强控制根文件校验依赖

    # 不是强控制根文件时直接跳过，避免普通仓库被强控制规则误伤。
    if "Strong control: complete" not in text:

        # 当前文件不在强控制路径上时，不需要继续执行强控制专属校验。
        return

    # 先检查强控制根文件的必备段落与控制档案入口是否存在。
    append_failed_checks(
        errors,
        [
            ("## Project" in text, f"{file}: missing strong-control section ## Project"),
            ("## Task-specific gates" in text, f"{file}: missing strong-control section ## Task-specific gates"),
            ("## Local conventions" in text, f"{file}: missing strong-control section ## Local conventions"),
            ("## Read before changing" in text, f"{file}: missing strong-control section ## Read before changing"),
            (
                (project / ".agents" / "agents-control.json").exists(),
                f"{file}: strong control requires .agents/agents-control.json",
            ),
        ],
    )

    # 复用 docs verifier 的结果，保持 handoff、memory 和 development 文档门禁一致。
    dict_docs_result = dict_shared_dependencies["verify_docs"](project)  # docs 校验结果

    # 把 docs verifier 的底层诊断折叠回 AGENTS 校验输出。
    errors.extend(f"{file}: {item}" for item in dict_docs_result["errors"])

    # 读取控制档案后，再联动检查语言锁、memory、release 和本地治理配置入口。
    dict_profile = read_json(project / ".agents" / "agents-control.json")  # 控制档案映射

    # 默认会话语言必须显式落盘，避免强控制根文件和设计画像脱节。
    if not str(dict_profile.get("default_conversation_language", "")).strip():

        # 直接回显缺少默认语言的根因，方便恢复强控制最小契约。
        errors.append(f"{file}: strong-control profile must explicitly set default_conversation_language")

    # 语言和 Worker 授权配置由独立合同模块校验，避免根入口继续膨胀。
    validate_language_profile(file, dict_profile, errors)

    # 知识图谱选择需同时核验画像、根规则和本地产物仓库边界。
    validate_codebase_memory_mcp_contract(text, file, project, dict_profile, errors)

    # memory 启用时，正文必须同时保留 memory 段落入口和四条关键治理提示。
    validate_strong_control_memory_contract(text, file, dict_profile, errors)

    # 额外需求只要不是 none，就必须在 Control Profile 正文中真实回显。
    str_extra_requirements = str(dict_profile.get("extra_requirements", "")).strip()  # 额外需求文本

    # 避免控制档案记录了额外需求，但渲染后的 AGENTS 根文件没有同步展示。
    if (
        str_extra_requirements
        and str_extra_requirements.casefold() != "none"
        and str_extra_requirements not in text
    ):

        # 把 extra_requirements 缺失问题直接登记到错误列表。
        errors.append(f"{file}: Control Profile must render extra_requirements from .agents/agents-control.json")

    # 先检查目录契约，确认 settings 和目录 review 约束仍与 profile 对齐。
    validate_directory_contract(text, file, dict_profile, errors)

    # 再检查远程服务器契约，补充 SSH 与远端治理规则的缺口。
    validate_remote_server_contract(text, file, dict_profile, errors)

    # git 托管与 skill 契约都用独立 helper 校验，避免把强控制总入口堆成超长函数。
    validate_strong_control_release_contract(text, file, dict_profile, errors)

    # skill 类型项目再叠加 skill 专属契约校验，确保设计门禁不会被遗漏。
    validate_strong_control_skill_contract(text, file, dict_profile, errors)

    # 根文件还必须回指本地治理配置，并确保细粒度规则没有回流到根 AGENTS 文本。
    validate_strong_control_local_config(text, file, project, dict_profile, errors)

# 语言路由验证入口核对 Python 与脚本技能的责任边界。
def validate_coding_behavior_language_routing(
    text: str,
    file: str,
    project: Path,
    profile: dict,
    installed_version: str | None,
    errors: list[str],
) -> bool:
    """校验根 AGENTS 是否继续保留 Coding Behavior Baseline 的语言技能路由契约。

    参数:
        text: 当前待检查的 AGENTS.md 全文。
        file: 当前错误信息应写回的文件标识。
        project: 当前项目根目录路径。
        profile: 当前项目 profile 映射，用于读取本地治理配置。
        installed_version: 当前安装态版本，用于决定是否启用历史路由兼容验收。
        errors: 共享错误列表，函数会直接向其中追加诊断。

    返回:
        当语言技能路由正文与本地配置都满足要求时返回 True；否则返回 False。
    """

    # 先拿到 coding_behavior 配置读取依赖，后续要核对语言技能路由与 JSON 子块。
    dict_shared_dependencies = shared_task_dependencies()  # 语言技能路由配置依赖

    # 旧 Code Comment Policy 段落已经退役；一旦重新出现就说明根文件还在泄露旧契约。
    if section_body(text, "## Code Comment Policy") is not None:

        # 直接登记旧段落残留问题，并停止继续检查新版语言技能路由契约。
        errors.append(
            f"{file}: retired Code Comment Policy section must move to "
            f"Coding Behavior Baseline language skill routing"
        )

        # 旧段落仍在时，当前文件不可能满足新版路由契约。
        return False

    # 先尝试新版标题，兼容把语言技能路由挂在 Coding Behavior Baseline 的根文件。
    str_body = first_section_body(text, ("## Coding Behavior Baseline", "## Local conventions"))  # 语言技能路由正文

    # 新标题没有命中时，再单独尝试旧版 Local conventions 入口。
    if str_body is None:

        # 回退到旧版 Local conventions 入口，兼容尚未完全迁移的受管根文件。
        str_body = section_body(text, "## Local conventions")  # 旧版 Local conventions 正文

    # 两种入口都找不到时，强控制根文件已经丢失语言技能路由总段落。
    if str_body is None:

        # 把缺段落根因直接回显，方便重新渲染受管根文件。
        errors.append(
            f"{file}: missing language skill routing in Coding Behavior "
            f"Baseline or Local conventions; refresh the managed root AGENTS.md"
        )

        # 找不到承载正文时，无法继续做短语或配置联动检查。
        return False

    # 预算压缩时详细路由合同位于同一文件的 Contract reference notes。
    str_reference_body = section_body(text, "## Contract reference notes")  # 根文件内的详细路由合同正文。

    # 只有存在引用区时才合并，避免缺失合同被默认文本掩盖。
    if str_reference_body:

        # verifier 继续对根文件内的完整合同执行相同短语和逐行检查。
        str_body = f"{str_body}\n{str_reference_body}"  # 合并指针段与引用段供同一门禁校验。

    # 初始化总体验证状态，后续每层失败都会把它拉成 False。
    bool_is_valid = True  # 语言技能路由总体验证状态

    # 旧安装态验证历史根文件时保留兼容路由验收，当前版本仍严格要求双技能文本。
    bool_use_legacy_rules = uses_legacy_language_skill_routing_rules(installed_version)  # 是否启用历史路由兼容验收

    # 逐条核对正文必备短语，确保双技能分流规则没有被弱化成自由描述。
    for str_required_snippet in CODING_BEHAVIOR_LANGUAGE_ROUTING_REQUIRED_SNIPPETS:

        # 缺失任何一条固定短语，都说明根文件没有完整保留语言技能路由契约。
        if str_required_snippet not in str_body:

            # 把缺失短语原样写回诊断，方便直接回到段落中补齐。
            errors.append(
                f"{file}: Coding Behavior Baseline language skill routing "
                f"missing required rule `{str_required_snippet}`"
            )

            # 记录正文缺句导致的失败状态，后续即使配置有效也不能判通过。
            bool_is_valid = False  # 正文缺失固定短语

    # 给逐行校验 helper 起一个局部短别名，避免保留完整函数名时把当前语句拉成长行。
    fn_validate_route_lines = validate_language_skill_route_lines  # 逐行语言路由 helper 短别名

    # 逐行 helper 会补足 Python 与脚本边界句式检查，先单独取回它的布尔结果。
    bool_route_lines_valid = fn_validate_route_lines(str_body, file, errors, use_legacy_rules=bool_use_legacy_rules)  # 逐行语言路由校验结果

    # 再把逐行结果并入总体验证状态，保持短语层和逐行层同时成立才算通过。
    bool_is_valid = bool_route_lines_valid and bool_is_valid  # 合并逐行路由检查结果

    # 读取本地治理 JSON，后续只检查 coding_behavior 相关文件存在性与子块结构。
    dict_config = dict_shared_dependencies["load_global_rule_overrides"](project, profile)  # 语言技能路由引用的本地治理配置

    # 提取受控 JSON 的相对路径，用它判断正文引用是否落在真实配置文件上。
    str_config_path = dict_config["path"].relative_to(project).as_posix()  # coding_behavior 配置相对路径

    # 根文件显式引用本地 config 时，必须继续保证 config 文件存在且 coding_behavior 子块有效。
    if str_config_path in str_body:

        # 指针存在但配置文件缺失时，直接把根因登记到错误列表。
        if not dict_config["exists"]:

            # 保持缺配置文件的诊断粒度不变，方便修复真实文件落点。
            errors.append(f"{file}: missing local coding behavior config `{str_config_path}`")

            # config 指针悬空时，整条路由校验必须失败。
            bool_is_valid = False  # 本地 coding_behavior 配置文件缺失

        # 只把 coding_behavior 相关错误回折到这条路由验证里，避免混入无关配置噪声。
        for str_config_error in dict_config["errors"]:

            # 只有 coding_behavior 子块错误才属于语言技能路由验证范围。
            if "coding_behavior" in str_config_error:

                # 直接透传底层配置错误，方便从 verifier 结果回跳到 JSON 修复。
                errors.append(
                    f"{file}: invalid Coding Behavior Baseline language "
                    f"skill routing config `{str_config_path}`: "
                    f"{str_config_error}"
                )

                # coding_behavior 子块结构错误时，整条语言路由校验必须失败。
                bool_is_valid = False  # 本地 coding_behavior 子块结构错误

    # 返回三层验证合并后的最终布尔结果，供调用方决定是否继续通过。
    return bool_is_valid

# 输出策略验证入口核对日志前缀和机器可读协议豁免。
def validate_script_output_policy(
    text: str,
    file: str,
    project: Path,
    profile: dict,
    errors: list[str],
) -> bool:
    """校验根 AGENTS 是否保留 Script Output Policy 的固定前缀与本地配置指针。

    参数:
        text: 当前待检查的 AGENTS.md 全文。
        file: 当前错误信息应写回的文件标识。
        project: 当前项目根目录路径。
        profile: 当前项目 profile 映射，用于读取本地治理配置。
        errors: 共享错误列表，函数会直接向其中追加诊断。

    返回:
        当脚本输出策略正文与本地配置都满足要求时返回 True；否则返回 False。
    """

    # 先拿到 script_output_policy 配置读取依赖，后续要核对正文指针与 JSON 子块。
    dict_shared_dependencies = shared_task_dependencies()  # 脚本输出策略配置依赖

    # 先尝试新版标题，兼容把脚本输出策略单列成独立段落的根文件。
    str_body = first_section_body(text, ("## Script Output Policy", "## Local conventions"))  # 优先读取独立脚本输出策略段落

    # 新标题未命中时，再尝试旧版 Local conventions 入口。
    if str_body is None:

        # 回退到旧版 Local conventions 入口，兼容尚未迁移完成的根文件布局。
        str_body = section_body(text, "## Local conventions")  # 使用旧版 Local conventions 作为兼容回退正文

    # 两种入口都找不到时，说明根文件已经丢失 Script Output Policy 总段落。
    if str_body is None:

        # 直接提示需要刷新受管根文件，避免调用方继续排查不存在的正文。
        errors.append(f"{file}: missing script output policy in Local conventions; refresh the managed root AGENTS.md")

        # 找不到承载正文时，脚本输出策略不具备继续核对的基础。
        return False

    # 预算压缩时 Script Output Policy 详细合同位于同一文件的引用区。
    str_reference_body = section_body(text, "## Contract reference notes")  # 根文件内的脚本输出合同正文。

    # 引用区存在时追加到同一验证正文，不改变 required snippet 门禁。
    if str_reference_body:

        # 继续检查根文件内的完整输出策略，而不是放宽为指针存在。
        str_body = f"{str_body}\n{str_reference_body}"  # 合并指针段与引用段供输出策略校验。

    # 初始化总体验证状态，后续只要正文或配置有缺口就会置为 False。
    bool_is_valid = True  # 脚本输出策略总体验证状态

    # 逐条核对 INFO/WARNING/ERR 等固定短语，确保输出协议没有被自由改写。
    for str_required_snippet in SCRIPT_OUTPUT_POLICY_REQUIRED_SNIPPETS:

        # 缺失任何固定短语都说明根文件没有完整保留输出协议。
        if str_required_snippet not in str_body:

            # 把缺失短语原样回显，方便直接回到正文补齐。
            errors.append(f"{file}: Script Output Policy missing required rule `{str_required_snippet}`")

            # 固定短语缺失意味着输出协议已经被弱化。
            bool_is_valid = False  # 正文缺失固定输出协议短语

    # 重新读取脚本输出策略引用的治理配置，后续要检查 config 指针和子块结构是否仍然有效。
    dict_config = dict_shared_dependencies["load_global_rule_overrides"](project, profile)  # 脚本输出策略引用的本地治理配置

    # 这里把治理配置文件路径转成仓库相对路径，后续只在正文真的引用它时才判断 Script Output Policy 的回指是否悬空。
    str_config_path = dict_config["path"].relative_to(project).as_posix()  # 脚本输出策略正文引用的治理配置相对路径

    # 只有正文真的引用了本地 config，才继续检查 script_output_policy 子块的文件存在性和结构错误。
    if str_config_path in str_body:

        # config 指针存在但文件缺失时，直接把根因登记到错误列表。
        if not dict_config["exists"]:

            # 这里直接回显悬空的配置路径，提示先补文件再检查子块结构。
            errors.append(f"{file}: missing local script output policy config `{str_config_path}`")

            # 配置文件路径存在引用但文件缺席时，本轮校验整体判失败。
            bool_is_valid = False  # 根文件引用的 script_output_policy 配置文件不存在

        # 只把 script_output_policy 子块的错误折叠回这条输出策略验证链路。
        for str_config_error in dict_config["errors"]:

            # 只有 script_output_policy 相关错误才属于当前验证范围。
            if "script_output_policy" in str_config_error:

                # 这里保留原始子块错误文本，方便直接回跳到 JSON 配置修复。
                errors.append(f"{file}: invalid script output policy config `{str_config_path}`: {str_config_error}")

                # 子块结构不合规时，脚本输出策略验证不能继续判定为通过。
                bool_is_valid = False  # script_output_policy 子块结构不合法

    # 返回正文与配置两层检查合并后的最终布尔结果。
    return bool_is_valid
