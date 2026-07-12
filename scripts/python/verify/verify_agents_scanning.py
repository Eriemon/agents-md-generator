"""扫描 AGENTS 文件并聚合仓库级诊断。"""

# 标准库提供正则解析、路径遍历与通用载荷类型。
import re
from pathlib import Path
from typing import Any

# 命令合同模块负责识别配置来源、脚本路径和运行时命令错误。
from verify_agents_command_contracts import (
    config_backed_command_error,
    documented_script_path_error,
    is_expected_contract_example_path,
    is_path_reference,
    validate_governance_runtime_commands,
)
# 根合同模块负责语言路由、输出策略和强控制语义核验。
from verify_agents_root_contracts import (
    validate_coding_behavior_language_routing,
    validate_language_skill_route_lines,
    validate_script_output_policy,
    validate_strong_control,
)
# 共享运行时提供正则、大小阈值、标记校验和延迟依赖。
from verify_agents_runtime_shared import (
    COMMAND_RE,
    LANGUAGE_LOCK_RE,
    PATH_RE,
    PLAN_LANGUAGE_LOCK_RE,
    ROOT_AGENTS_MAX_BYTES,
    ROOT_AGENTS_MAX_KB,

    # 共享依赖和标记校验位于正则与阈值常量之后。
    shared_task_dependencies,
    validate_markers,
)

# 分解计划验证入口检查超大源码是否具备可执行拆分合同。
def validate_decomposition_plan(project: Path, relative_path: str, profile: dict | None = None) -> list[str]:
    """校验超大源码对应的分解计划是否存在且包含必备章节。

    参数:
        project: 当前项目根目录。
        relative_path: 触发分解计划要求的源码相对路径。
        profile: 可选的项目 profile，用于读取必备章节配置。

    返回:
        缺少分解计划或章节时返回诊断列表；通过时返回空列表。
    """

    # 先拿到分解计划路径与治理配置 helper，后续要比对计划文件和必备章节。
    dict_shared_dependencies = shared_task_dependencies()  # 分解计划校验依赖

    # 先定位该源码路径应该对应的分解计划文件位置。
    path_plan = dict_shared_dependencies["decomposition_plan_path"](project, relative_path, profile)  # 分解计划路径

    # 分解计划文件缺失时，直接回显期望路径，方便创建正确文件。
    if not path_plan.is_file():

        # 这里保留相对路径诊断，便于从 verifier 输出直接定位缺失计划。
        return [
            (
                f"oversized source file `{relative_path}` requires "
                f"decomposition plan `{path_plan.relative_to(project).as_posix()}`"
            )
        ]

    # 读取计划正文后，再核对 source_file_limits 中要求的章节标题是否齐全。
    str_plan_text = path_plan.read_text(encoding="utf-8", errors="ignore")  # 用于章节匹配的分解计划正文

    # 读取 source_file_limits 里声明的必备章节标题。
    dict_rule_overrides = dict_shared_dependencies["load_global_rule_overrides"](project, profile)  # 本地治理配置快照

    # 从治理配置里提取分解计划的必备章节标题，后续据此检查计划正文是否齐全。
    list_required_sections = dict_rule_overrides["data"]["source_file_limits"].get("required_plan_sections", [])  # 分解计划必备章节标题列表

    # 根据正文缺口筛出尚未补齐的章节标题。
    list_missing_sections = [section for section in list_required_sections if f"## {section}" not in str_plan_text]  # 分解计划中缺失的章节标题

    # 缺章时返回固定诊断，提醒补齐受控的分解计划结构。
    if list_missing_sections:

        # 直接回显缺失章节列表，方便回到计划文档补齐标题。
        return [
            (
                f"{path_plan.relative_to(project).as_posix()}: missing "
                f"decomposition plan sections {list_missing_sections}"
            )
        ]

    # 分解计划文件和章节都满足要求时，返回空诊断列表。
    return []

# 路径过滤助手判断 AGENTS 文件是否位于默认排除范围。
def should_skip(path: Path, project: Path, include_skipped: bool = False) -> bool:
    """判断某个路径是否应从 verifier 的普通扫描范围里跳过。

    参数:
        path: 当前待判断的文件或目录路径。
        project: 当前项目根目录。
        include_skipped: 为 True 时强制不过滤任何跳过目录。

    返回:
        当路径命中跳过目录且未开启 include_skipped 时返回 True；否则返回 False。
    """

    # 先取 skip 目录集合，后续要判断当前路径是否退出普通扫描范围。
    dict_shared_dependencies = shared_task_dependencies()  # skip 目录集合访问依赖

    # 调试或全量扫描模式会显式要求把原本应跳过的路径也纳入检查。
    if include_skipped:

        # 调用方已经要求不过滤任何路径，因此这里直接返回 False。
        return False

    # 优先把路径转成相对 project 的 parts，失败时再回退到原始绝对路径 parts。
    try:

        # 相对 parts 更接近仓库视角，适合和 SKIP_DIRS 直接做集合相交。
        tuple_parts = path.relative_to(project).parts  # 相对路径片段

    # 路径不在 project 内时，退回绝对路径 parts 继续做跳过目录判断。
    except ValueError:

        # 绝对路径 parts 仍能支持与 SKIP_DIRS 做交集判断。
        tuple_parts = path.parts  # 绝对路径片段

    # 只要路径片段命中任一跳过目录，就把该路径排除在普通扫描范围之外。
    return bool(set(tuple_parts) & dict_shared_dependencies["skip_dirs"])

# 元数据验证入口核对根规则与安装技能的版本一致性。
def validate_root_metadata_versions(
    file: str,
    dict_metadata: dict[str, str],
    installed_version: str | None,
    errors: list[str],
) -> bool:
    """校验根 AGENTS 的版本元数据，并返回是否需要刷新根文件。

    参数:
        file: 当前错误信息应写回的文件标识。
        dict_metadata: 根 AGENTS 解析出的元数据映射。
        installed_version: 当前安装态 agents-md-generator 版本。
        errors: 共享错误列表，函数会直接向其中追加诊断。

    返回:
        命中版本元数据缺口或安装态漂移时返回 True；否则返回 False。
    """

    # 初始化根修复标记，任一关键缺口都会要求输出 sync 命令。
    bool_repair_required = False  # 是否需要追加根文件修复命令

    # 逐条核对版本元数据字段，缺失时统一拉起根修复标记。
    for bool_is_invalid, str_error_text in (
        (
            not dict_metadata.get("agents_version")
            or not dict_metadata.get("generator_version"),
            "AGENTS.md: missing AGENTS metadata version",
        ),
        (
            not dict_metadata.get("agents_version"),
            "AGENTS.md: missing agents version metadata",
        ),
        (
            not dict_metadata.get("generator_version"),
            "AGENTS.md: missing generator version metadata",
        ),
    ):

        # 只有当前元数据条件命中缺口时，才继续登记诊断并拉起修复标记。
        if bool_is_invalid:

            # 先把具体的元数据缺口文本写入错误列表。
            errors.append(str_error_text)

            # 元数据字段缺失时，最终必须输出根文件修复命令。
            bool_repair_required = True  # 版本元数据缺口要求刷新根文件

    # 只有拿到安装态版本时，才继续比较 agents_version 与 generator_version 是否对齐。
    if installed_version:

        # 逐个比对两个版本字段，任何一处与安装态不一致都必须提示刷新根文件。
        for str_key_name, str_label in (
            ("agents_version", "agents version"),
            ("generator_version", "generator version"),
        ):

            # 提取当前字段声明的版本值，空字符串表示该字段未配置。
            str_declared_version = str(dict_metadata.get(str_key_name, "")).strip()  # 根文件声明的版本值

            # 只有字段非空且与安装态不一致时，才登记版本漂移错误。
            if str_declared_version and str_declared_version != installed_version:

                # 先回显当前字段的版本漂移信息，方便核对根文件与安装态差异。
                errors.append(
                    f"AGENTS.md: {str_label} {str_declared_version} does not match "
                    f"installed agents-md-generator version {installed_version}"
                )

                # 已声明版本与安装态漂移时，需要统一提示刷新根文件。
                bool_repair_required = True  # 已声明版本与安装态漂移

    # 缺少安装态版本时，只能退回到基础可观测性错误提示。
    else:

        # 无法读取安装态版本时，至少要把基础可观测性缺口回显出来。
        errors.append("AGENTS.md: installed agents-md-generator version is unavailable")

    # 返回当前版本元数据链路是否需要根文件修复。
    return bool_repair_required

# 默认语言验证入口核对响应语言和 Plan Mode 锁定规则。
def validate_root_default_language_contract(
    text: str,
    dict_metadata: dict[str, str],
    errors: list[str],
) -> bool:
    """校验根 AGENTS 的默认语言元数据与语言锁表达式。

    参数:
        text: 根 AGENTS.md 的全文内容。
        dict_metadata: 根 AGENTS 解析出的元数据映射。
        errors: 共享错误列表，函数会直接向其中追加诊断。

    返回:
        命中默认语言元数据或语言锁缺口时返回 True；否则返回 False。
    """

    # 默认情况下先认为语言契约不要求额外修复，后续命中缺口时再拉起刷新标记。
    bool_repair_required = False  # 默认语言契约是否需要刷新根文件

    # 读取默认会话语言，后续据此决定是否继续检查语言锁正则。
    str_default_language = str(dict_metadata.get("default_language", "")).strip()  # 根文件声明的默认语言

    # 缺少默认语言元数据时，说明语言锁契约已经失去锚点。
    if not str_default_language:

        # 先回显默认语言缺口，提示根文件缺少语言锁的锚点字段。
        errors.append("AGENTS.md: missing default language metadata")

        # 默认语言字段缺失时，根文件必须重新同步。
        return True

    # 普通回复语言锁缺失时，根文件没有真正强制默认语言约束。
    if not LANGUAGE_LOCK_RE.search(text):

        # 直接登记普通回复语言锁缺失，避免根文件静默放松默认语言要求。
        errors.append("AGENTS.md: missing enforced default-language reply rule")

        # 普通回复语言锁缺失时，需要统一提示刷新根文件。
        bool_repair_required = True  # 普通回复语言锁缺失

    # Plan Mode 语言锁缺失时，计划内容仍可能泄露到错误语言。
    if not PLAN_LANGUAGE_LOCK_RE.search(text):

        # 直接登记 Plan Mode 语言锁缺失，避免计划内容落到错误语言。
        errors.append("AGENTS.md: missing enforced Plan Mode default-language rule")

        # Plan Mode 语言锁缺失时，需要统一提示刷新根文件。
        bool_repair_required = True  # Plan Mode 语言锁缺失

    # 返回当前默认语言契约是否需要刷新根文件。
    return bool_repair_required

# 根文件验证入口聚合版本、语言和强控制专属合同。
def validate_root_agents_file(
    text: str,
    file: str,
    project: Path,
    profile: dict[str, Any], installed_version: str | None,
    root_repair_command: str, errors: list[str],
) -> None:
    """校验根 AGENTS.md 的受管元数据、语言锁和根修复指引。

    参数:
        text: 根 AGENTS.md 的全文内容。
        file: 当前错误信息应写回的文件标识。
        project: 当前项目根目录。
        profile: 当前项目 profile 映射。
        installed_version: 当前安装态 agents-md-generator 版本。
        root_repair_command: 用于刷新根 AGENTS 元数据的修复命令。
        errors: 共享错误列表，函数会直接向其中追加诊断。

    返回:
        无业务返回值；所有问题都通过 `errors` 原地返回。
    """

    # 先取根 AGENTS 元数据解析依赖，后续要联动版本、语言锁和刷新提示。
    dict_shared_dependencies = shared_task_dependencies()  # 根文件元数据校验依赖

    # 计算根文件字节大小，用来执行 ROOT_AGENTS_MAX_BYTES 上限检查。
    int_size_bytes = len(text.encode("utf-8"))  # 根 AGENTS.md 的字节大小

    # 根文件超出体积上限时，直接登记固定诊断。
    if int_size_bytes > ROOT_AGENTS_MAX_BYTES:

        # 把根文件超限结果直接写入错误列表，方便调用方优先处理体积问题。
        errors.append(
            f"{file}: exceeds {ROOT_AGENTS_MAX_KB}KB limit ({int_size_bytes} bytes)"
        )

    # 判断当前根文件是否走 managed-root 契约，未受管时不做版本与语言锁检查。
    bool_managed_root = "Managed by agent:" in text or (project / ".agents" / "agents-control.json").exists()  # 当前根文件是否受管

    # 非受管根文件不需要执行 managed-root 专属校验。
    if not bool_managed_root:

        # 非受管根文件不走 managed-root 契约，因此这里直接结束校验。
        return

    # 解析根文件元数据映射，后续会检查 version 和 default_language 字段。
    dict_metadata = dict_shared_dependencies["parse_agents_metadata"](text)  # 根 AGENTS 元数据映射

    # 版本元数据与默认语言锁都通过独立 helper 校验，再统一汇总刷新标记。
    bool_repair_required = validate_root_metadata_versions(file, dict_metadata, installed_version, errors)  # 版本元数据链路是否要求刷新根文件

    # 叠加默认语言契约的刷新标记，任一子契约失配都必须统一输出 root sync 指引。
    bool_repair_required = validate_root_default_language_contract(text, dict_metadata, errors) or bool_repair_required  # 汇总后的根文件刷新标记

    # 给根语言路由校验 helper 起局部短别名，避免完整函数名把调用行推过当前项目长行门限。
    fn_validate_root_language_route = validate_coding_behavior_language_routing  # 根语言路由 helper 短别名

    # 继续检查语言技能路由正文，失败时要求重新同步受管根文件。
    bool_language_route_valid = fn_validate_root_language_route(text, file, project, profile, installed_version, errors)  # 根文件语言技能路由验证结果

    # 继续检查脚本输出策略正文，失败时同样要求重新同步受管根文件。
    bool_script_output_valid = validate_script_output_policy(text, file, project, profile, errors)  # 根文件脚本输出策略验证结果

    # 任一根文件子契约失败时，都需要提示运行 root sync 命令。
    if not bool_language_route_valid or not bool_script_output_valid:

        # 任一根文件子契约失配时，都要把最终状态拉成需要刷新。
        bool_repair_required = True  # 根文件子契约失配时需要统一刷新

    # 根文件任一关键契约失配时，统一追加一次 sync 指引。
    if bool_repair_required:

        # 汇总追加一次根文件同步指引，避免同一轮校验给出多条重复命令。
        errors.append(
            f"AGENTS.md: run `{root_repair_command}` to refresh root metadata "
            f"before continuing"
        )

# 路径引用扫描入口收集缺失或不适用的文档路径警告。
def collect_path_reference_warnings(
    text: str,
    agents_path: Path,
    file: str,
    project: Path,
    profile: dict[str, Any],
) -> list[str]:
    """扫描 AGENTS 文本中的路径引用，并返回可能失效的警告列表。

    参数:
        text: 当前待检查的 AGENTS.md 全文。
        agents_path: 当前正在扫描的 AGENTS.md 路径。
        file: 当前警告信息应写回的文件标识。
        project: 当前项目根目录。
        profile: 当前项目 profile 映射。

    返回:
        可能失效的路径引用警告列表。
    """

    # 初始化当前文件的路径引用警告列表。
    list_warnings: list[str] = []  # 当前文件的路径引用警告

    # 逐个提取反引号路径片段，并用仓库路径规则过滤掉 URL 或保留文件名。
    for obj_match in PATH_RE.finditer(text):

        # 提取当前命中的原始路径片段，后续所有存在性判断都围绕它展开。
        str_raw = obj_match.group(1).strip()  # 当前反引号里的原始路径文本

        # 非仓库路径引用的片段不属于当前 warning 规则的处理范围。
        if not is_path_reference(str_raw):

            # URL、保留文件名等非仓库路径文本在这里直接跳过。
            continue

        # 先按当前 AGENTS 所在目录解析路径，优先尊重近端相对引用。
        path_local_candidate = (agents_path.parent / str_raw).resolve()  # 以当前 AGENTS 目录为基准的候选路径

        # 再按仓库根目录解析路径，兼容根相对路径写法。
        path_root_candidate = (project / str_raw).resolve()  # 以仓库根目录为基准的候选路径

        # 只对既不落地、又不是示例路径、又不是目录占位的文本发出警告。
        if (
            not path_local_candidate.exists()
            and not path_root_candidate.exists()
            and not str_raw.endswith("/")
            and not is_expected_contract_example_path(str_raw, profile)
        ):

            # 只有真正无法解析的路径片段，才把 warning 折叠进当前文件结果。
            list_warnings.append(f"{file}: referenced path may not exist: {str_raw}")

    # 返回当前文件累积到的路径引用警告。
    return list_warnings

# 命令扫描入口收集文档中无法由项目事实支撑的命令错误。
def collect_documented_command_errors(text: str, file: str, project: Path) -> list[str]:
    """扫描 AGENTS 文本中的命令引用，并返回配置缺口或脚本缺失诊断。

    参数:
        text: 当前待检查的 AGENTS.md 全文。
        file: 当前错误信息应写回的文件标识。
        project: 当前项目根目录。

    返回:
        当前文件中命中的命令类诊断列表。
    """

    # 初始化当前文件的命令类诊断列表。
    list_errors: list[str] = []  # 当前文件的命令诊断

    # 逐个扫描反引号命令片段，并过滤掉明显不是可执行命令的路径或文档文件名。
    for obj_match in COMMAND_RE.finditer(text):

        # 提取当前命中的命令文本，后续会继续判断它是否需要做配置与脚本校验。
        str_command = obj_match.group(1).strip()  # 当前反引号里的命令文本

        # 路径样式或文档文件名不属于当前命令类校验范围。
        if (
            not str_command
            or "/" in str_command
            or str_command.endswith((".md", ".json", ".toml", ".yml", ".yaml"))
        ):

            # 显然不是可执行命令的片段在这里直接跳过。
            continue

        # 先检查命令是否引用了不存在的 Makefile、package.json 或 composer.json 条目。
        str_config_error = config_backed_command_error(str_command, project)  # 命令后端配置诊断

        # 只有真的命中配置后端缺口时，才继续把它折叠回当前文件错误列表。
        if str_config_error:

            # 命中配置后端缺口时，把诊断折叠回当前文件错误列表。
            list_errors.append(f"{file}: {str_config_error}")

        # 再检查 python 命令里引用的脚本路径是否真实存在于仓库。
        str_script_error = documented_script_path_error(str_command, project)  # Python 脚本路径诊断

        # 只有真的命中 Python 脚本路径缺口时，才继续把它折叠回当前文件错误列表。
        if str_script_error:

            # 命中 Python 脚本路径缺口时，把诊断折叠回当前文件错误列表。
            list_errors.append(f"{file}: {str_script_error}")

    # 返回当前文件累积到的命令类诊断。
    return list_errors

# 单文件扫描入口汇总标记、根合同、路径和命令诊断。
def scan_agents_file(
    path_agents: Path,
    project: Path,
    path_root_agents: Path,
    dict_profile: dict[str, Any], str_installed_version: str | None,
    str_root_repair_command: str,
    installed_skill_dir_override: str | Path | None,
) -> tuple[list[str], list[str]]:
    """扫描单个 AGENTS.md，并返回当前文件的错误与警告列表。

    参数:
        path_agents: 当前待扫描的 AGENTS.md 路径。
        project: 当前项目根目录。
        path_root_agents: 仓库根 AGENTS.md 路径。
        dict_profile: 当前项目 profile 映射。
        str_installed_version: 当前安装态 agents-md-generator 版本。
        str_root_repair_command: 根 AGENTS 刷新命令。
        installed_skill_dir_override: 可选的安装态 skill 目录覆盖路径。

    返回:
        第一个列表是当前文件的错误，第二个列表是当前文件的警告。
    """

    # 初始化当前文件的错误与警告容器，避免跨文件串味。
    list_file_errors: list[str] = []  # 当前 AGENTS.md 的错误集合

    # 警告单独收集，避免和阻断性错误混在同一个返回列表里。
    list_file_warnings: list[str] = []  # 当前 AGENTS.md 的警告集合

    # 计算当前 AGENTS 的仓库相对路径，后续所有诊断都会回显这个标识。
    str_relative_file = str(path_agents.relative_to(project).as_posix())  # 当前 AGENTS.md 的仓库相对路径

    # 读取当前 AGENTS 正文，后续所有文本校验都基于这份字符串进行。
    str_agents_text = path_agents.read_text(encoding="utf-8", errors="ignore")  # 当前 AGENTS.md 全文

    # 根文件会额外执行版本元数据、语言锁和修复命令校验。
    if path_agents == path_root_agents:

        # 根文件命中时，继续执行 managed-root 专属校验链。
        validate_root_agents_file(
            str_agents_text, str_relative_file, project, dict_profile,
            str_installed_version, str_root_repair_command, list_file_errors,
        )

    # 每个 AGENTS 文件都要检查 runtime 越界、受管 marker 和强控制 profile。
    validate_governance_runtime_commands(
        str_agents_text,
        str_relative_file,
        project,
        installed_skill_dir_override,
        list_file_errors,
    )

    # 受管 marker 必须独立校验，避免 runtime 越界错误淹没元数据结构缺口。
    validate_markers(str_agents_text, str_relative_file, list_file_errors)

    # 强控制项目的 profile、docs 和本地治理入口也要在同一轮单文件扫描里检查。
    validate_strong_control(str_agents_text, str_relative_file, project, list_file_errors)

    # 模板占位符残留意味着文件仍停留在未渲染状态。
    if "{{" in str_agents_text or "}}" in str_agents_text:

        # 把模板占位符残留直接记成错误，避免未渲染文本混入发布产物。
        list_file_errors.append(f"{str_relative_file}: unresolved template placeholder")

    # 根 AGENTS.md 缺少 Precedence 说明时，说明最小阅读入口没有完整落盘。
    if path_agents == path_root_agents and "Precedence" not in str_agents_text:

        # 缺少 Precedence 说明时，直接回显根文件入口缺口。
        list_file_errors.append("AGENTS.md: missing precedence statement")

    # 叠加当前文件中可能失效的路径引用警告。
    list_file_warnings.extend(
        collect_path_reference_warnings(
            str_agents_text, path_agents, str_relative_file, project, dict_profile,
        )
    )

    # 叠加当前文件中命中的配置缺口或脚本路径缺失诊断。
    list_file_errors.extend(
        collect_documented_command_errors(
            str_agents_text,
            str_relative_file,
            project,
        )
    )

    # 返回当前文件的错误与警告，供仓库级 verify 汇总。
    return list_file_errors, list_file_warnings
