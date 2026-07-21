"""校验 AGENTS 中记录的命令与路径合同。"""

# 标准库提供 JSON 解析、正则匹配、路径建模和通用载荷类型。
import json
import re
from pathlib import Path
from typing import Any

from verify_agents_runtime_shared import (
    PROJECT_LOCAL_GOVERNANCE_RUNTIME_RE,
    mapping_value_or_empty,
    shared_task_dependencies,
)

# 路径候选助手排除 URL、保留文件名和无效路径字符。
def is_path_reference(raw: str) -> bool:
    """判断一段文本是否更像仓库内路径引用，而不是 URL 或保留文件名。

    参数:
        raw: 待判断的原始文本片段。

    返回:
        当文本更像仓库内路径引用时返回 True；否则返回 False。
    """

    # URL、邮件链接和保留文件名都不应被当成仓库内路径引用。
    if raw.startswith(("http://", "https://", "mailto:")) or raw in {
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        "__init__.py",
    }:

        # 这些外部链接或保留文件名不属于路径引用候选。
        return False

    # 含空白字符的片段通常不是路径字面量，直接排除可减少误判。
    if any(char.isspace() for char in raw):

        # 空白字符会打断路径 token，因此这里直接返回 False。
        return False

    # 含通配或非法路径字符的片段同样不按仓库路径处理。
    if any(char in raw for char in "*?<>|,"):

        # 这些字符更像 glob 或无效字面量，不属于稳定路径引用。
        return False

    # 剩余片段可以继续按路径引用候选参与后续校验。
    return True

# 契约示例助手判断路径是否属于配置声明的展示白名单。
def is_expected_contract_example_path(raw: str, profile: dict[str, Any]) -> bool:
    """判断路径样例是否属于目录契约允许展示的受控示例。

    参数:
        raw: 待判断的路径样例文本。
        profile: 当前项目 profile 映射，用于读取 settings 目录契约。

    返回:
        当路径样例属于受控展示白名单时返回 True；否则返回 False。
    """

    # 先抽出目录契约和 settings 策略，后续据此构造允许展示的路径示例集合。
    dict_directory_contract = mapping_value_or_empty(profile, "directory_contract")  # 目录契约配置映射

    # 继续抽取 settings 子策略，用它构造允许展示的本地/远程样例路径。
    dict_settings_policy = mapping_value_or_empty(dict_directory_contract, "workspace_settings_policy")  # 构造受控样例所需的 settings 子策略

    # 计算 settings 根目录和本地/远程默认文件路径，兼容 profile 留空时的默认值。
    str_settings_folder = str(dict_settings_policy.get("folder", ".settings")).strip() or ".settings"  # 受控样例使用的 settings 根目录

    # 先准备 profile 留空时的默认样例路径，避免同一段默认值在多处重复拼接。
    str_default_local = (Path(str_settings_folder) / "project.local.json").as_posix()  # 本地默认样例路径

    # 远程样例路径单独保留，避免后续默认值回退继续重复拼接字符串。
    str_default_remote = (Path(str_settings_folder) / "project.remote.json").as_posix()  # 远程默认样例路径

    # 计算本地默认文件路径，兼容 profile 省略该字段时回退到约定值。
    str_local_default_candidate = str(dict_settings_policy.get("local_default_file", str_default_local)).strip()  # 受控样例里的本地默认配置候选值

    # 候选值为空时回退到本地默认样例路径，保证允许白名单与正文示例保持同一落点。
    str_local_default = str_local_default_candidate or str_default_local  # 受控样例里的本地默认配置文件

    # 计算远程默认文件路径，兼容 profile 省略该字段时回退到约定值。
    str_remote_default_candidate = str(dict_settings_policy.get("remote_default_file", str_default_remote)).strip()  # 受控样例里的远程默认配置候选值

    # 远程样例经常受部署约束影响，这里只在候选值为空时才退回默认路径，避免白名单漂移。
    str_remote_default = str_remote_default_candidate or str_default_remote  # 受控样例里的远程默认配置文件

    # 这些样例路径可以出现在 Directory Contract 或规则说明里，不应被误报为非法路径引用。
    str_server_list_example = (Path(str_settings_folder) / "server_list.local.json").as_posix()  # 受控服务器清单样例

    # 额外允许的后缀样例只保留文件名层级，避免目录契约示例被仓库路径检查误报。
    tuple_extra_examples = (".local.json", ".remote.json", "RELEASE_RECEIPT.json")  # 额外允许的文件名样例

    # 汇总所有受控样例路径，后续只要命中这个白名单就不应再报路径不存在。
    set_allowed_examples = {str_local_default, str_remote_default, str_server_list_example, *tuple_extra_examples}  # 允许出现在契约示例中的受控路径集合

    # 只接受落在受控样例白名单中的路径文本。
    return raw in set_allowed_examples

# JSON 读取助手在文件缺失或载荷损坏时返回空映射。
def read_json(path: Path) -> dict:
    """读取 JSON 文件，并在读取失败时回退为空映射。

    参数:
        path: 待读取的 JSON 文件路径。

    返回:
        成功时返回解析后的 JSON 对象；失败时返回空映射。
    """

    # 读取失败不能阻断 AGENTS verifier，因此这里统一吞掉文件与 JSON 解析异常。
    try:

        # 解析成功后直接把 JSON 对象交给上游调用方继续使用。
        return json.loads(path.read_text(encoding="utf-8"))

    # 文件缺失或内容非法时统一回退为空映射，保持上游校验流程可继续运行。
    except Exception:

        # 失败场景回退为空映射，避免调用方重复包一层文件异常处理。
        return {}

# Make 目标发现助手读取项目声明的公开构建目标。
def make_targets(root: Path) -> set[str]:
    """提取 Makefile 里声明的目标名称集合。

    参数:
        root: 当前项目根目录。

    返回:
        Makefile 存在时返回其中的目标集合；否则返回空集合。
    """

    # Makefile 是 make 命令可用目标的唯一数据源，缺文件时直接返回空集合。
    path_makefile = root / "Makefile"  # 当前项目根目录下的 Makefile 路径

    # 没有 Makefile 时不再继续解析，避免无意义的文件读取。
    if not path_makefile.exists():

        # 缺少 Makefile 时没有可校验的目标名称，直接返回空集合。
        return set()

    # 读取 Makefile 全文后，用固定正则抽出声明在行首的目标名。
    str_makefile_text = path_makefile.read_text(encoding="utf-8", errors="ignore")  # 用于提取目标名的 Makefile 全文

    # 返回 Makefile 中解析到的目标名称集合，供命令引用校验复用。
    return set(re.findall(r"^([A-Za-z0-9_.-]+):", str_makefile_text, flags=re.MULTILINE))

# package.json 助手读取脚本名集合供命令合同核验。
def package_scripts(root: Path) -> set[str]:
    """提取 package.json 里声明的 scripts 名称集合。

    参数:
        root: 当前项目根目录。

    返回:
        package.json 中 scripts 字段的键集合；缺失或类型错误时返回空集合。
    """

    # package.json 是 npm/pnpm/yarn/bun 脚本命令的唯一数据源。
    dict_package = read_json(root / "package.json")  # 供 npm 类脚本校验使用的 package.json 根映射

    # 抽取 scripts 子块，后续只需要它的键名集合。
    dict_scripts = mapping_value_or_empty(dict_package, "scripts")  # 供 npm 类命令查找脚本名的 scripts 子块

    # 只返回 scripts 键名集合，供命令存在性校验复用。
    return set(dict_scripts)

# Composer 助手读取 PHP 项目公开的脚本名集合。
def composer_scripts(root: Path) -> set[str]:
    """提取 composer.json 里声明的 scripts 名称集合。

    参数:
        root: 当前项目根目录。

    返回:
        composer.json 中 scripts 字段的键集合；缺失或类型错误时返回空集合。
    """

    # composer.json 是 composer run 命令的唯一数据源。
    dict_composer = read_json(root / "composer.json")  # 供 composer run 校验使用的 composer.json 根映射

    # 读取 scripts 子块，后续只需要它的键名集合来校验 composer run。
    dict_scripts = mapping_value_or_empty(dict_composer, "scripts")  # 供 composer run 查找键名的 scripts 子块

    # 只返回 composer scripts 键名集合，供 composer run 相关校验直接复用。
    return set(dict_scripts)

# Make 命令验证助手返回缺失目标对应的诊断文本。
def make_target_command_error(list_tokens: list[str], command: str, project: Path) -> str | None:
    """检查命令文本是否引用了不存在的 Makefile 目标。

    参数:
        list_tokens: 命令按空白切分后的 token 列表。
        command: 文档里出现的原始命令文本。
        project: 当前项目根目录。

    返回:
        命中缺失 Makefile 目标时返回诊断文本；否则返回 None。
    """

    # 只有 make <target> 形态才会继续核对目标名是否存在。
    if list_tokens[0] != "make" or len(list_tokens) < 2:

        # 非 make 目标调用不属于当前检查范围。
        return None

    # make 命令只允许引用 Makefile 中真实存在的目标名称。
    if list_tokens[1] not in make_targets(project):

        # 把缺失的 Makefile 目标名直接写入诊断，方便回到命令文本修复。
        return f"documented command `{command}` references missing Makefile target `{list_tokens[1]}`"

    # 目标存在时，不需要返回额外诊断。
    return None

# 包管理命令解析助手从 token 序列中提取脚本名称。
def package_command_script_name(list_tokens: list[str]) -> str | None:
    """解析 npm、pnpm、yarn、bun 命令实际引用的脚本名。

    参数:
        list_tokens: 命令按空白切分后的 token 列表。

    返回:
        成功定位时返回最终脚本键名；无法稳定定位时返回 None。
    """

    # npm run 的脚本名位于第三个 token。
    if list_tokens[0] == "npm" and len(list_tokens) >= 3 and list_tokens[1] == "run":

        # npm run 只有第三个 token 才是最终参与 scripts 匹配的键名。
        return list_tokens[2]

    # npm test 是对 package.json test script 的快捷调用。
    if list_tokens[0] == "npm" and len(list_tokens) >= 2 and list_tokens[1] == "test":

        # 把快捷命令统一映射成 test 脚本键，复用同一套存在性校验。
        return "test"

    # bun run 与 npm run 一样，第三个 token 才是脚本键名。
    if list_tokens[0] == "bun" and len(list_tokens) >= 3 and list_tokens[1] == "run":

        # 这里返回真正被 bun run 解析的脚本键。
        return list_tokens[2]

    # 其他包管理器脚本命令通常把第二个 token 当作脚本名。
    if len(list_tokens) >= 2:

        # pnpm、yarn 与 bun 的常规脚本调用都以第二个 token 命名脚本。
        return list_tokens[1]

    # token 数量不足时，无法稳定定位脚本键名。
    return None

# 包管理命令验证助手返回未声明脚本对应的诊断文本。
def package_script_command_error(list_tokens: list[str], command: str, project: Path) -> str | None:
    """检查 npm、pnpm、yarn、bun 命令是否引用了不存在的 package.json script。

    参数:
        list_tokens: 命令按空白切分后的 token 列表。
        command: 文档里出现的原始命令文本。
        project: 当前项目根目录。

    返回:
        命中缺失 package.json script 时返回诊断文本；否则返回 None。
    """

    # 只处理四类 package.json script 命令；其他命令直接跳过。
    if list_tokens[0] not in {"npm", "pnpm", "yarn", "bun"}:

        # 非包管理器脚本命令不属于当前检查范围。
        return None

    # 先读取 package.json scripts，缺数据源时不对脚本名做误报。
    set_package_scripts = package_scripts(project)  # 当前项目 package.json 中可调用的 scripts 集合

    # 缺少 scripts 数据源时，这条命令暂时不输出配置缺失诊断。
    if not set_package_scripts:

        # 没有 package.json scripts 可校验时，直接把命令视为未知但不报错。
        return None

    # 这些包管理器子命令不是 script 调用入口，因此这里直接跳过校验。
    if (
        list_tokens[0] in {"pnpm", "yarn"}
        and len(list_tokens) >= 2
        and list_tokens[1] in {"dlx", "exec", "install", "add", "remove"}
    ):

        # 非 script 子命令不需要去 package.json scripts 里核对名字。
        return None

    # bun 的 x/install/add/remove 同样不是 package.json script 名称。
    if (
        list_tokens[0] == "bun"
        and len(list_tokens) >= 2
        and list_tokens[1] in {"x", "install", "add", "remove"}
    ):

        # bun 的这些子命令走独立语义，不对应 package.json scripts 键。
        return None

    # 统一提取本次命令真正引用的 script 名称，后续再做存在性比对。
    str_script_name = package_command_script_name(list_tokens)  # 当前命令最终映射到的 package.json scripts 键名

    # token 数量不足以确定 script 名称时，直接结束校验。
    if not str_script_name:

        # 无法定位脚本名时不输出误导性诊断。
        return None

    # package.json 不存在对应 script 时，返回精确的缺失脚本诊断。
    if str_script_name not in set_package_scripts:

        # 直接回显缺失的 script 名称，方便同步更新 package.json 或文档命令。
        return f"documented command `{command}` references missing package.json script `{str_script_name}`"

    # 命中的 package.json script 存在时，不需要额外诊断。
    return None

# Composer 命令验证助手返回未声明脚本对应的诊断文本。
def composer_script_command_error(list_tokens: list[str], command: str, project: Path) -> str | None:
    """检查 composer run 命令是否引用了不存在的 composer.json script。

    参数:
        list_tokens: 命令按空白切分后的 token 列表。
        command: 文档里出现的原始命令文本。
        project: 当前项目根目录。

    返回:
        命中缺失 composer.json script 时返回诊断文本；否则返回 None。
    """

    # 只有 composer run <script> 形态才需要继续做 scripts 键存在性检查。
    if list_tokens[0] != "composer" or len(list_tokens) < 3 or list_tokens[1] != "run":

        # 非 composer run 命令不属于当前检查范围。
        return None

    # 读取 composer scripts 键集合，再核对第三个 token 是否是受管脚本键名。
    set_composer_scripts = composer_scripts(project)  # 当前仓库 PHP 侧文档命令可引用的 composer scripts 键集合

    # 只有 composer scripts 数据源存在时，才对第三个 token 做存在性比对。
    if set_composer_scripts and list_tokens[2] not in set_composer_scripts:

        # 回显缺失的 composer script 名称，方便回到 composer.json 或文档修复。
        return f"documented command `{command}` references missing composer.json script `{list_tokens[2]}`"

    # 命中的 composer script 存在，或者当前仓库没有 composer scripts 时，不报错。
    return None

# 配置命令验证助手核对文档命令是否由项目配置事实支撑。
def config_backed_command_error(command: str, project: Path) -> str | None:
    """检查命令文本是否引用了配置文件中不存在的 Makefile 或脚本条目。

    参数:
        command: 文档里出现的命令文本。
        project: 当前项目根目录。

    返回:
        命中缺失配置项时返回诊断文本；否则返回 None。
    """

    # 先按空白切分命令 token，后续所有分支都基于这个 token 视图判断。
    list_tokens = command.split()  # 命令 token 列表

    # 空命令没有可校验的后端配置引用，直接视为无错误。
    if not list_tokens:

        # 没有 token 时既不会命中 make，也不会命中脚本型命令。
        return None

    # make 目标错误优先返回，因为它不依赖 package/composer 的额外分支判断。
    str_make_error = make_target_command_error(list_tokens, command, project)  # Makefile 目标诊断

    # 命中 Makefile 目标缺失时，直接返回最精确的根因。
    if str_make_error:

        # Makefile 目标缺失不需要继续做 package/composer 分支判断。
        return str_make_error

    # 包管理器脚本错误次之，覆盖 npm/pnpm/yarn/bun 这四类命令。
    str_package_error = package_script_command_error(list_tokens, command, project)  # 当前命令命中的 package.json script 诊断

    # 包管理器命令引用缺失脚本时，直接返回对应诊断。
    if str_package_error:

        # package.json scripts 缺失时，不需要继续尝试 composer 分支。
        return str_package_error

    # 最后再检查 composer run，对 PHP 侧脚本键保持同样的存在性约束。
    return composer_script_command_error(list_tokens, command, project)

# 脚本路径验证助手核对文档命令引用的入口是否真实存在。
def documented_script_path_error(command: str, project: Path) -> str | None:
    """检查 Python 命令是否引用了仓库中不存在的脚本路径。

    参数:
        command: 文档里出现的命令文本。
        project: 当前项目根目录。

    返回:
        命中缺失脚本路径时返回诊断文本；否则返回 None。
    """

    # 先切分命令 token，只对 python <script>.py 这一类调用继续做路径存在性检查。
    list_tokens = command.split()  # 供 python <script>.py 识别使用的命令 token 列表

    # 非 python 脚本调用或 token 不足时，不属于当前脚本路径检查范围。
    if len(list_tokens) < 2 or list_tokens[0] != "python":

        # 不是目标命令形态时直接返回无错误。
        return None

    # 已安装 skill 运行时路径不在当前仓库树内，因此这里跳过本地存在性检查。
    if list_tokens[1].startswith("<codex-home>/"):

        # 安装态命令路径由安装时保证，不在当前仓库做相对路径存在性校验。
        return None

    # 把脚本路径锚定到项目根目录，后续据此检查仓库里是否真的存在目标文件。
    path_candidate = project / list_tokens[1]  # 文档命令引用的候选脚本路径

    # 只有显式 .py 路径不存在时，才返回缺失脚本诊断。
    if list_tokens[1].endswith(".py") and not path_candidate.exists():

        # 直接回显缺失的脚本相对路径，方便同步更新命令或补齐文件。
        return f"documented command `{command}` references missing script `{list_tokens[1]}`"

    # 命令引用的脚本路径存在时，不需要返回额外诊断。
    return None

# 治理命令验证入口阻止外部仓库引用源码仓库私有运行时。
def validate_governance_runtime_commands(
    text: str,
    file: str,
    project: Path,
    installed_skill_dir_override: str | Path | None,
    errors: list[str],
) -> None:
    """校验非 owner 仓库是否错误引用了 project-local governance runtime 命令。

    参数:
        text: 当前待检查的 AGENTS.md 全文。
        file: 当前错误信息应写回的文件标识。
        project: 当前项目根目录。
        installed_skill_dir_override: 可选的安装态 skill 目录覆盖路径。
        errors: 共享错误列表，函数会直接向其中追加诊断。

    返回:
        无业务返回值；所有问题都通过 `errors` 原地返回。
    """

    # 先拿到 owner 状态判定依赖，后续要区分 owner 与非 owner 仓库的命令约束。
    dict_shared_dependencies = shared_task_dependencies()  # owner 状态校验依赖

    # 先判断当前项目是否属于 owner 仓库；只有非 owner 仓库才禁止 project-local runtime 命令。
    dict_owner_status = dict_shared_dependencies["evolution_owner_status"](  # owner 仓库状态
        project,  # 当前项目根目录
        override_dir=installed_skill_dir_override,  # 安装态 skill 目录覆盖值
    )

    # owner 仓库允许继续使用 project-local runtime，因此这里直接跳过。
    if dict_owner_status.get("enabled"):

        # owner 仓库不需要执行这条非 owner 约束检查。
        return

    # 非 owner 仓库命中任意 project-local runtime 命令时，都要登记固定治理诊断。
    for obj_match in PROJECT_LOCAL_GOVERNANCE_RUNTIME_RE.finditer(text):

        # 直接回显命中的具体命令片段，方便替换成安装态 runtime 命令。
        errors.append(
            f"{file}: project-local governance runtime command is forbidden for non-owner "
            f"repositories; use installed agents-md-generator runtime instead ({obj_match.group(0)})",
        )
