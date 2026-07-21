"""验证设计访谈中的远程依赖、服务器注册表与任务路由合同。"""

# 延迟注解求值避免运行时解析跨模块类型。
from __future__ import annotations

# 标准库覆盖 JSON 协议、路径发现、CLI 执行和任务名规范化。
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from design_questions import (
    REMOTE_SSH_GIT_URL,
    REMOTE_SSH_INSTALL_SPECS,
    REMOTE_SSH_SKILL_NAME,
    USE_REMOTE_SERVER_KEY,
    remote_directory_policy_required,
)

# 判断访谈答案是否进入远程依赖与路由流程。
def use_remote_server_enabled(answers: dict[str, Any]) -> bool:
    """判断设计答案是否启用远程服务器。

    参数：answers 为设计访谈答案映射。
    返回：启用远程服务器时为 True。
    """

    # 统一布尔转换兼容 JSON 中的缺失值和显式 false。
    return bool(answers.get(USE_REMOTE_SERVER_KEY))

# 将列表或分隔文本整理为稳定的任务名称集合。
def normalize_remote_task_list(raw: Any) -> list[str]:
    """将远程任务输入规范化为去重名称列表。

    参数：raw 为列表或分隔文本形式的任务输入。
    返回：保持首次出现顺序的非空任务名称。
    """

    # 列表输入逐项转成去除外围空白的文本。
    if isinstance(raw, list):

        # 保留输入顺序供路由优先级继续使用。
        list_values = [  # 尚未去重的任务名称。
            str(item).strip()  # 当前列表元素的规范化文本。
            for item in raw  # 原始列表中的任务名称元素。
        ]

    # 文本输入允许常见的中英文逗号、分号和换行分隔。
    elif isinstance(raw, str):

        # 正则切分同时消除每个名称的外围空白。
        list_values = [  # 从分隔文本提取的任务名称。
            part.strip()  # 当前切分片段的规范化文本。
            for part in re.split(  # 按中英文常见分隔符切分文本。
                r"[\r\n,，;；]+",  # 支持的任务分隔符集合。
                raw,  # 待切分任务文本。
            )
        ]

    # 其他类型不构造隐式任务名称。
    else:

        # 空输入使调用方获得稳定的列表合同。
        list_values = []  # 非列表和非文本输入的空结果。

    # 输出列表只保留每个名称的首次出现位置。
    list_normalized: list[str] = []  # 已规范化且去重的任务名称。

    # casefold 键用于执行不区分大小写的去重。
    set_seen: set[str] = set()  # 已接收任务名称的比较键。

    # 逐项过滤空名称和大小写不同的重复项。
    for value in list_values:

        # 空切分片段不应成为可选择任务。
        if not value:

            # 继续处理后续非空名称。
            continue

        # 比较键不改变最终展示名称的原始大小写。
        key = value.casefold()  # 当前任务名称的去重键。

        # 已出现的比较键不重复写入输出列表。
        if key in set_seen:

            # 保留首次出现的展示名称和顺序。
            continue

        # 登记比较键后再追加对应展示名称。
        set_seen.add(key)

        # 首次出现的非空任务进入规范化结果。
        list_normalized.append(value)

    # 返回可直接用于路由和服务器功能字段的名称列表。
    return list_normalized

# 统一单个任务名称的空值与空白处理。
def normalize_remote_task_name(raw: Any) -> str:
    """规范化单个远程任务名称。

    参数：raw 为任意任务名称输入。
    返回：去除外围空白的任务名称文本。
    """

    # 空值回退为空字符串，其他值保留其文本表达。
    return str(raw or "").strip()

# 构造任务路由查找使用的稳定比较键。
def normalize_remote_task_key(raw: Any) -> str:
    """构造远程任务名称的不区分大小写索引键。

    参数：raw 为任意任务名称输入。
    返回：经过名称规范化和 casefold 的任务键。
    """

    # casefold 支持比 lower 更完整的不区分大小写比较。
    return normalize_remote_task_name(raw).casefold()

# 验证并去重远程服务器注册表记录。
def normalize_remote_server_registry(raw: Any) -> list[dict[str, Any]]:
    """规范化远程服务器注册表并按标识去重。

    参数：raw 为待验证的注册表载荷。
    返回：包含有效服务器标识的规范化记录列表。
    """

    # 注册表根必须是 JSON 数组。
    if not isinstance(raw, list):

        # 类型损坏时不猜测单条记录结构。
        return []

    # 输出记录只保留路由和展示需要的受控字段。
    list_registry: list[dict[str, Any]] = []  # 规范化服务器记录。

    # 服务器标识在同一注册表中必须唯一。
    set_seen: set[str] = set()  # 已接收的服务器标识。

    # 输入顺序决定服务器选择界面的展示顺序。
    for item in raw:

        # 非映射数组元素不能解释为服务器记录。
        if not isinstance(item, dict):

            # 继续检查后续结构有效的记录。
            continue

        # 标识字段是去重和路由引用的唯一主键。
        server_id = str(item.get("id", "")).strip()  # 当前服务器标识。

        # 空标识或重复标识都不能进入注册表。
        if not server_id or server_id in set_seen:

            # 保留首个合法记录作为该标识的事实来源。
            continue

        # 先登记主键，避免后续重复记录覆盖首次事实。
        set_seen.add(server_id)

        # 只复制治理合同允许的服务器属性。
        list_registry.append(
            {
                "id": server_id,  # 路由引用的稳定服务器主键。
                "name": str(item.get("name", "")).strip(),  # 用户可读服务器名称。
                "category": str(item.get("category", "")).strip(),  # 服务器用途分类。
                "functions": normalize_remote_task_list(  # 服务器声明的能力名称。
                    item.get("functions", [])
                ),
                "enabled": bool(item.get("enabled", False)),  # 是否允许任务路由选择。
                "validation_status": str(  # 基础连接检查状态。
                    item.get("validation_status", "")
                ).strip(),
                "workspace_status": str(  # 远程工作区检查状态。
                    item.get("workspace_status", "")
                ).strip(),
            }
        )

    # 返回顺序稳定且字段收窄后的服务器事实。
    return list_registry

# 验证并去重任务到服务器的路由记录。
def normalize_remote_task_routes(raw: Any) -> list[dict[str, Any]]:
    """规范化任务到远程服务器的路由配置。

    参数：raw 为待验证的任务路由载荷。
    返回：去重任务名、主服务器和回退服务器的路由列表。
    """

    # 路由根必须是 JSON 数组。
    if not isinstance(raw, list):

        # 类型损坏时返回空合同而不合成路由。
        return []

    # 输出顺序保持用户确认的任务优先级。
    list_routes: list[dict[str, Any]] = []  # 规范化任务路由。

    # 任务比较键阻止大小写不同的重复路由。
    set_seen: set[str] = set()  # 已接收任务的比较键。

    # 逐条收窄路由字段并过滤损坏记录。
    for item in raw:

        # 非映射元素不能表达任务到服务器的关系。
        if not isinstance(item, dict):

            # 继续检查后续合法路由记录。
            continue

        # 展示名称保留用户输入的大小写和内部字符。
        str_task_name = normalize_remote_task_name(  # 当前路由任务名称。
            item.get("task_name", "")  # 原始任务名称字段。
        )

        # 比较键用于确保每个任务只有一条路由。
        str_task_key = normalize_remote_task_key(str_task_name)  # 当前任务路由键。

        # 空任务或重复任务不进入正式路由合同。
        if not str_task_name or not str_task_key or str_task_key in set_seen:

            # 首条有效任务路由继续作为唯一事实来源。
            continue

        # 登记任务键后再解析服务器引用。
        set_seen.add(str_task_key)

        # 主服务器是路由解析时的首选目标。
        primary_server_id = (  # 当前任务首选服务器标识。
            str(item.get("primary_server_id", "")).strip()  # 原始主服务器字段。
        )

        # 回退列表只保留不同于主服务器的唯一标识。
        list_fallback_server_ids: list[str] = []  # 当前任务回退服务器顺序。

        # 单条路由内部独立执行回退标识去重。
        set_seen_fallbacks: set[str] = set()  # 已接收回退服务器标识。

        # 输入回退顺序决定自动故障切换顺序。
        for server_id in normalize_remote_task_list(
            item.get("fallback_server_ids", [])
        ):

            # 主服务器和已出现回退项不重复尝试。
            if server_id == primary_server_id or server_id in set_seen_fallbacks:

                # 继续保留后续首次出现的服务器标识。
                continue

            # 登记回退标识后加入最终尝试顺序。
            set_seen_fallbacks.add(server_id)

            # 当前回退服务器将在主服务器失败后尝试。
            list_fallback_server_ids.append(server_id)

        # 显式 route_tasks 优先，兼容旧 server_tasks 字段。
        list_route_tasks = normalize_remote_task_list(  # 当前路由承担的任务名称。
            item.get(  # 新旧任务字段的兼容选择。
                "route_tasks",  # 当前合同任务字段。
                item.get("server_tasks", []),  # 旧合同任务字段回退值。
            )
        )

        # 函数能力字段同样兼容旧 source_functions 名称。
        list_route_functions = normalize_remote_task_list(  # 当前路由声明的能力名称。
            item.get(  # 新旧能力字段的兼容选择。
                "route_functions",  # 当前合同能力字段。
                item.get("source_functions", []),  # 旧合同能力字段回退值。
            )
        )

        # 收窄后的记录可直接持久化到控制合同。
        list_routes.append(
            {
                "task_name": str_task_name,  # 用户确认的任务展示名称。
                "task_key": str_task_key,  # 不区分大小写的路由索引键。
                "primary_server_id": primary_server_id,  # 首选服务器标识。
                "fallback_server_ids": list_fallback_server_ids,  # 故障切换服务器顺序。
                "route_tasks": list_route_tasks,  # 路由覆盖的任务集合。
                "route_functions": list_route_functions,  # 路由依赖的服务器能力。
                "selection_confirmed": bool(  # 用户是否确认服务器选择。
                    item.get("selection_confirmed", False)
                ),
                "validation_status": str(  # 路由最近一次验证状态。
                    item.get("validation_status", "")
                ).strip(),
            }
        )

    # 返回任务唯一且服务器顺序稳定的路由列表。
    return list_routes

# 在兼容目录中定位远程 SSH 默认设置文件。
def remote_settings_path(skill_dir: Path) -> Path | None:
    """定位远程 SSH skill 支持的默认设置文件。

    参数：skill_dir 为远程 SSH skill 安装根。
    返回：首个存在的 assets 或 config 设置路径；均缺失时为 None。
    """

    # 新版 assets 布局优先，同时兼容旧版 config 布局。
    for relative in ("assets/defaults.json", "config/defaults.json"):

        # 候选路径始终限制在已安装 skill 根之下。
        candidate = skill_dir / relative  # 当前待验证设置文件。

        # 只有真实文件才能证明该目录契约可用。
        if candidate.is_file():

            # 返回首个兼容布局，确保新版布局优先。
            return candidate

    # 两种设置布局均缺失时依赖不完整。
    return None

# 远程 CLI 入口解析与技能身份分离，避免内部目录升级影响安装判定。
def remote_ssh_entry_path(skill_dir: Path) -> Path | None:
    """定位远程 SSH skill 支持的命令行入口。

    参数：skill_dir 为已经通过技能身份检查的安装根。
    返回：首个存在的新版或旧版 CLI 入口；均缺失时为 None。
    """

    # 新版 runtime 入口优先，旧版根脚本仅作为已发布版本兼容回退。
    tuple_candidates = (  # 按稳定优先级排列的受支持 CLI 入口
        skill_dir / "scripts" / "python" / "runtime" / "remote_ssh.py",  # 新版运行入口
        skill_dir / "scripts" / "remote_ssh.py",  # 已发布旧版兼容入口
    )

    # 固定顺序检查避免选择结果受目录枚举顺序影响。
    for path_candidate in tuple_candidates:

        # 只有真实文件可以作为可执行的 Python CLI 入口。
        if path_candidate.is_file():

            # 返回首个可用入口并停止兼容路径探测。
            return path_candidate

    # 两个公开入口均缺失时由调用方报告运行能力错误。
    return None

# 从显式覆盖或 Codex 默认目录发现可用远程 SSH skill。
def remote_skill_dir() -> Path | None:
    """从 Codex skill 根定位已安装的远程 SSH skill。

    参数：无。
    返回：包含根 SKILL.md 的 erie-remote-ssh 目录；未安装时为 None。
    """

    # 测试和定制安装可通过显式环境变量提供候选根。
    override = os.environ.get(  # 用户指定的远程 SSH skill 目录。
        "AGENTS_MD_REMOTE_SSH_SKILL_DIR",  # 环境覆盖键。
        "",  # 未设置覆盖时的空路径。
    ).strip()

    # 显式覆盖优先于 Codex 默认安装位置。
    list_candidates: list[Path] = []  # 待验证的远程 SSH skill 根。

    # 非空覆盖路径先解析为绝对路径。
    if override:

        # 环境覆盖作为第一候选，支持隔离测试与定制部署。
        list_candidates.append(Path(override).resolve())

    # CODEX_HOME 存在时按其 skills 子目录定位安装副本。
    codex_home = os.environ.get("CODEX_HOME", "").strip()  # Codex 用户数据根。

    # 显式 Codex 根优先于用户主目录回退。
    if codex_home:

        # 解析后的路径消除相对段对结构验证的影响。
        list_candidates.append(
            (Path(codex_home).resolve() / "skills" / REMOTE_SSH_SKILL_NAME).resolve()
        )

    # 未设置 CODEX_HOME 时使用标准 ~/.codex/skills 布局。
    else:

        # 用户主目录回退与 Codex 默认安装器保持一致。
        list_candidates.append(
            (Path.home() / ".codex" / "skills" / REMOTE_SSH_SKILL_NAME).resolve()
        )

    # 安装身份只由技能目录和根 SKILL.md 决定。
    for candidate in list_candidates:

        # 内部 CLI 与设置布局属于独立能力，不能改写安装事实。
        if candidate.is_dir() and (candidate / "SKILL.md").is_file():

            # 返回首个满足技能身份合同的候选根。
            return candidate

    # 所有候选均缺少目录或根说明文件时才视为未安装。
    return None

# 汇总远程 SSH 依赖发现结果和可执行安装规格。
def remote_dependency_summary() -> dict[str, Any]:
    """汇总远程 SSH 依赖的安装状态与安装规格。

    参数：无。
    返回：包含安装身份、CLI/设置能力、仓库和安装规格的摘要。
    """

    # 目录发现结果同时决定 installed 状态和展示路径。
    path_skill_dir = remote_skill_dir()  # 已验证的远程 SSH skill 根。

    # CLI 和设置路径仅在技能身份成立后独立探测。
    path_cli = (  # 当前安装副本的可用 CLI 入口
        remote_ssh_entry_path(path_skill_dir) if path_skill_dir else None  # 身份成立后探测运行能力
    )

    # 设置能力缺失应进入配置或能力诊断，而不是重新安装分支。
    path_settings = (  # 当前安装副本的可用默认设置
        remote_settings_path(path_skill_dir) if path_skill_dir else None  # 身份成立后探测配置能力
    )

    # 摘要供访谈流程分别处理安装、运行和配置状态。
    return {
        "installed": path_skill_dir is not None,  # 技能身份是否通过目录与 SKILL.md 检查。
        "skill_dir": (  # 已安装目录展示值。
            str(path_skill_dir) if path_skill_dir else None
        ),
        "runtime_available": path_cli is not None,  # 受支持 CLI 入口是否可用。
        "cli_path": str(path_cli) if path_cli else None,  # 实际选中的 CLI 入口。
        "settings_available": path_settings is not None,  # 默认设置文件是否可用。
        "settings_path": (  # 实际选中的设置文件路径。
            str(path_settings) if path_settings else None
        ),
        "url": REMOTE_SSH_GIT_URL,  # 缺失依赖时使用的仓库地址。
        "install_specs": list(REMOTE_SSH_INSTALL_SPECS),  # skill 安装参数副本。
    }

# 构造远程 SSH CLI 的解释器、设置文件与附加参数。
def remote_ssh_command(skill_dir: Path, subcommand: str, *extra: str) -> list[str]:
    """构造调用远程 SSH CLI 的 Python 命令。

    参数：skill_dir 为 skill 根，subcommand 为子命令，extra 为附加参数。
    返回：可传给 subprocess 的命令参数列表。
    异常：技能已安装但缺少受支持 CLI 入口时抛出 FileNotFoundError。
    """

    # 入口能力由统一解析器决定，命令和配置提示不得各自猜测路径。
    path_entry = remote_ssh_entry_path(skill_dir)  # 当前选中的远程 SSH CLI 入口

    # 已安装但缺少公开入口时报告能力错误，不改写为未安装。
    if path_entry is None:

        # 稳定错误文本供发现和配置流程给出精确恢复建议。
        raise FileNotFoundError(
            "> ERR: [Python] erie-remote-ssh is installed but no supported CLI entry was found"
        )

    # 使用当前解释器保证 CLI 与调用方处于同一 Python 环境。
    list_command = [  # subprocess 接收的远程 SSH 命令参数。
        sys.executable,  # 当前进程 Python 解释器。
        str(path_entry),  # 统一解析后的远程 SSH CLI 入口。
        subcommand,  # 本次调用的 CLI 子命令。
    ]

    # 兼容布局探测结果决定是否显式传入设置文件。
    settings_path = remote_settings_path(skill_dir)  # 当前 skill 的默认设置路径。

    # 找到真实设置文件时覆盖 CLI 的内部默认查找。
    if settings_path is not None:

        # 显式参数保证 assets 与 config 两种布局行为一致。
        list_command.extend(["--settings", str(settings_path)])

    # 调用方参数保持原始顺序追加在公共参数之后。
    list_command.extend(extra)

    # 返回无需 shell 字符串拼接的安全参数列表。
    return list_command

# 执行远程 SSH CLI 并完整捕获结果供策略层解析。
def run_remote_ssh(
    skill_dir: Path, subcommand: str, *extra: str
) -> subprocess.CompletedProcess[str]:
    """执行远程 SSH CLI 并捕获文本输出。

    参数：skill_dir 为 skill 根，subcommand 为子命令，extra 为附加参数。
    返回：包含退出码、标准输出和标准错误的完成进程。
    """

    # 先构造命令，把入口能力缺失转换到与子进程失败相同的返回通道。
    try:

        # 无 shell 参数列表由统一 CLI 入口解析器生成。
        list_command = remote_ssh_command(skill_dir, subcommand, *extra)  # 远程 CLI 参数

    # 入口缺失属于可诊断能力状态，不应向上泄漏文件异常。
    except FileNotFoundError as object_error:

        # 127 表示命令入口不可用，stderr 保留精确能力错误。
        return subprocess.CompletedProcess(
            args=[],
            returncode=127,
            stdout="",
            stderr=str(object_error),
        )

    # 不抛出非零退出码，让发现和检查函数解释领域状态码。
    return subprocess.run(
        list_command,  # 无 shell 的 CLI 参数。
        text=True,  # 标准流按文本解码。
        capture_output=True,  # 调用方需要解析 stdout 与 stderr。
        check=False,  # 领域状态码由上层显式处理。
        env=dict(  # 子进程继承环境并禁止污染安装目录。
            os.environ, PYTHONDONTWRITEBYTECODE="1"
        ),
    )

# 解析远程检查命令输出的冒号分隔字段。
def parse_remote_kv(stdout: str) -> dict[str, str]:
    """解析远程 SSH CLI 输出中的键值行。

    参数：stdout 为 CLI 标准输出文本。
    返回：由首个等号切分并去除空白的键值映射。
    """

    # 重复键使用后出现的值，与普通 CLI 状态覆盖语义一致。
    dict_data: dict[str, str] = {}  # 解析后的远程检查字段。

    # 逐物理行识别形如 key: value 的状态记录。
    for line in stdout.splitlines():

        # 无分隔符的提示行不属于机器字段。
        if ": " not in line:

            # 继续查找后续结构化状态行。
            continue

        # 只在首个分隔符切分，保留值内的冒号。
        key, raw_value = line.split(": ", 1)  # 当前字段名与原始值。

        # 去除两侧空白后写入标准字段映射。
        dict_data[key.strip()] = raw_value.strip()  # 当前 CLI 状态字段值。

    # 返回连接和工作区检查可直接消费的状态字段。
    return dict_data

# 解析远程 SSH JSON 标准输出并验证对象根类型。
def remote_json_payload(
    completed_process: subprocess.CompletedProcess[str], command_name: str
) -> tuple[dict[str, Any], list[str]]:
    """解析远程 SSH 命令返回的 JSON 对象。

    参数：completed_process 为命令结果，command_name 为诊断中的子命令名。
    返回：对象类型载荷与 JSON 解码或根类型错误列表。
    """

    # 解析错误独立返回，避免发现流程直接抛出 JSON 异常。
    list_errors: list[str] = []  # 当前命令的 JSON 结构错误。

    # 空标准输出按空对象处理，保留后续默认字段逻辑。
    try:

        # 非空输出必须是合法 JSON，空输出则使用稳定空载荷。
        dict_loaded_payload = (  # 尚未收窄根类型的 JSON 值。
            json.loads(completed_process.stdout)  # 解析非空标准输出。
            if completed_process.stdout.strip()  # 是否存在可解析文本。
            else {}  # 空输出的默认对象。
        )

    # JSON 解码失败需要作为远程配置阻断原因展示。
    except json.JSONDecodeError:

        # 损坏文本不能继续作为部分发现结果使用。
        dict_loaded_payload = {}  # 解码失败后的空载荷。

        # 错误消息明确指出产生无效 JSON 的子命令。
        list_errors.append(
            f"erie-remote-ssh {command_name} did not return valid JSON"
        )

    # 协议要求根节点是对象，数组或标量均视为损坏。
    if not isinstance(dict_loaded_payload, dict):

        # 根类型错误时丢弃不兼容值。
        dict_loaded_payload = {}  # 根类型收窄失败后的空对象。

        # 子命令名称保留在诊断中以便直接复现。
        list_errors.append(
            f"erie-remote-ssh {command_name} JSON must be an object"
        )

    # 返回可安全写入默认字段的对象和解析错误。
    return dict_loaded_payload, list_errors

# 提取远程命令失败时最具体的 stderr、stdout 或退出码摘要。
def remote_failure_summary(
    completed_process: subprocess.CompletedProcess[str], command_name: str
) -> str:
    """构造远程 SSH 命令失败摘要。

    参数：completed_process 为命令结果，command_name 为子命令名。
    返回：优先 stderr、其次 stdout、最后退出码的非空摘要。
    """

    # 原始错误流最接近 SSH 或配置失败的真实原因。
    return (
        completed_process.stderr.strip()  # 远程命令标准错误。
        or completed_process.stdout.strip()  # 无 stderr 时保留标准输出诊断。
        or (  # 两个输出流均为空时回退到退出码。
            f"unexpected {command_name} return code "
            f"{completed_process.returncode}"
        )
    )

# 执行远程服务器发现并补齐交互状态字段。
def remote_discover(skill_dir: Path) -> tuple[dict[str, Any], list[str]]:
    """调用远程发现命令并验证 JSON 结果。

    参数：skill_dir 为远程 SSH skill 根。
    返回：发现结果载荷与阻止使用该结果的错误列表。
    """

    # discover 的退出码 3 和 4 表示需要配置或没有可用服务器。
    completed_process_result = run_remote_ssh(  # 驱动发现状态机的 CLI 结果。
        skill_dir,  # 执行 discover 的 skill 根。
        "discover",  # 服务器发现子命令。
        "--json",  # 请求结构化协议输出。
    )

    # 公共解析器收窄 JSON 根类型并保留解码错误。
    tuple_payload_result = remote_json_payload(  # 发现载荷与解析错误元组。
        completed_process_result,  # 待解析的发现命令结果。
        "discover",  # 错误消息使用的子命令名。
    )

    # 分别提取类型安全的发现对象和错误列表。
    dict_data = tuple_payload_result[0]  # 远程发现 JSON 对象。

    # 错误列表后续继续追加退出码诊断。
    list_errors = tuple_payload_result[1]  # 远程发现解析错误。

    # 默认状态使空或部分载荷仍可被访谈状态机消费。
    dict_data.setdefault("status", "failed")

    # 消息字段用于向用户解释发现阶段的下一步。
    dict_data.setdefault("message", "")

    # next_action 驱动配置或重新发现的交互分支。
    dict_data.setdefault("next_action", "")

    # 保留原始退出码用于状态机区分领域结果。
    dict_data["returncode"] = (  # 发现流程领域状态码。
        completed_process_result.returncode  # discover 进程退出码。
    )

    # 约定之外的退出码属于真实命令失败。
    if completed_process_result.returncode not in {0, 3, 4}:

        # 优先展示远程 CLI 给出的具体失败原因。
        str_summary = remote_failure_summary(  # discover 命令失败摘要。
            completed_process_result,  # 失败的发现命令结果。
            "discover",  # 摘要中的子命令名。
        )

        # 命令失败与 JSON 解析错误可以同时保留。
        list_errors.append(f"erie-remote-ssh discover failed: {str_summary}")

    # 返回状态机可消费的发现载荷和完整错误集合。
    return dict_data, list_errors

# 获取可选服务器列表并验证 servers 数组合同。
def remote_choices(skill_dir: Path) -> tuple[dict[str, Any], list[str]]:
    """调用远程服务器选项命令并验证记录列表。

    参数：skill_dir 为远程 SSH skill 根。
    返回：选项结果载荷与命令或解析错误列表。
    """

    # choices 的退出码 4 表示当前没有可选择服务器。
    completed_process_result = run_remote_ssh(  # 驱动服务器选择界面的 CLI 结果。
        skill_dir,  # 提供 choices CLI 的安装根。
        "choices",  # 枚举可选服务器的子命令。
        "--json",  # choices 使用的机器协议开关。
    )

    # 公共解析器统一处理空输出、无效 JSON 和非对象根。
    tuple_payload_result = remote_json_payload(  # 选项载荷与解析错误元组。
        completed_process_result,  # 包含服务器选项 JSON 的进程结果。
        "choices",  # 选项解析诊断中的命令标签。
    )

    # 分别提取服务器选项对象和解析错误。
    dict_data = tuple_payload_result[0]  # 远程服务器选项 JSON 对象。

    # 错误列表后续继续追加 servers 字段与退出码诊断。
    list_errors = tuple_payload_result[1]  # 远程服务器选项解析错误。

    # servers 字段必须是列表，后续再由注册表规范化器收窄元素。
    list_servers = dict_data.get("servers", [])  # 原始服务器选项列表。

    # 非列表字段不能进入服务器选择界面。
    if not isinstance(list_servers, list):

        # 损坏字段回退为空列表，保持载荷 schema 稳定。
        list_servers = []  # 根字段类型损坏后的空选项。

        # 明确指出 choices 协议缺少 servers 数组。
        list_errors.append(
            "erie-remote-ssh choices JSON must contain a servers list"
        )

    # 写回类型收窄后的服务器列表。
    dict_data["servers"] = list_servers  # 已验证为列表的服务器选项。

    # 缺失状态按失败处理，防止空对象被误判为成功。
    dict_data.setdefault("status", "failed")

    # 原始退出码与 discover 载荷保持一致。
    dict_data["returncode"] = (  # choices 流程领域状态码。
        completed_process_result.returncode  # 服务器枚举命令的领域退出码。
    )

    # 成功和无可选服务器之外的退出码均属于命令失败。
    if completed_process_result.returncode not in {0, 4}:

        # 捕获 CLI 提供的最具体失败摘要。
        str_summary = remote_failure_summary(  # 服务器枚举失败的用户可读摘要。
            completed_process_result,  # 未能提供选项的进程结果。
            "choices",  # 选项失败摘要中的命令标签。
        )

        # 追加领域上下文后交给访谈流程展示。
        list_errors.append(f"erie-remote-ssh choices failed: {str_summary}")

    # 返回结构稳定的选项载荷和全部诊断。
    return dict_data, list_errors

# 按用户选择器查找远程服务器记录。
def remote_server_record(
    records: list[dict[str, Any]], selector: str
) -> dict[str, Any] | None:
    """按服务器标识或名称查找注册表记录。

    参数：records 为服务器记录，selector 为标识或名称选择器。
    返回：首个匹配记录；没有匹配项时为 None。
    """

    # 比较键允许按标识或展示名称进行不区分大小写查找。
    str_selector_fold = selector.strip().casefold()  # 服务器选择器比较键。

    # 记录顺序决定重复名称情况下的首选结果。
    for record in records:

        # 损坏的非映射记录不能参与字段查找。
        if not isinstance(record, dict):

            # 继续检查后续类型有效的服务器记录。
            continue

        # 标识或名称任一匹配即可返回完整注册表记录。
        if str_selector_fold in {
            str(record.get("id", "")).casefold(),  # 服务器标识比较值。
            str(record.get("name", "")).casefold(),  # 展示名称比较值。
        }:

            # 返回首个匹配项以保持选择结果稳定。
            return record

    # 所有记录均不匹配时返回缺失状态。
    return None

# 验证指定服务器的 SSH 连接与基础配置状态。
def remote_server_check(
    skill_dir: Path, server_id: str
) -> tuple[dict[str, str], list[str]]:
    """执行指定服务器的基础连接检查。

    参数：skill_dir 为远程 SSH skill 根，server_id 为服务器标识。
    返回：解析后的检查字段与命令失败错误列表。
    """

    # check 子命令验证服务器配置、认证和基础连接。
    completed_process_result = run_remote_ssh(  # 决定候选能否继续的连接检查结果。
        skill_dir,  # 执行基础 check 的 skill 根。
        "check",  # 基础连接检查子命令。
        "--server",  # 服务器选择参数。
        server_id,  # 待检查服务器标识。
    )

    # 状态字段从 CLI 的冒号分隔输出提取。
    dict_data = parse_remote_kv(  # 服务器基础检查字段。
        completed_process_result.stdout  # check 输出的冒号分隔字段。
    )

    # 命令退出码和领域 status 字段分别产生诊断。
    list_errors: list[str] = []  # 当前服务器基础检查错误。

    # 非零退出码表示 CLI 或 SSH 层失败。
    if completed_process_result.returncode != 0:

        # 公共摘要优先保留真实 stderr 或 stdout。
        str_summary = remote_failure_summary(  # 服务器 check 失败摘要。
            completed_process_result,  # 失败的基础检查结果。
            "check",  # 连接失败摘要中的命令标签。
        )

        # 服务器标识加入错误文本，支持多服务器故障切换诊断。
        list_errors.append(
            f"erie-remote-ssh check failed for {server_id}: {str_summary}"
        )

    # 即使退出码为零，领域状态仍必须明确为 ok。
    if dict_data.get("status") != "ok":

        # 缺失或异常状态阻止该服务器被选中。
        list_errors.append(
            f"erie-remote-ssh check did not return ok status for {server_id}"
        )

    # 返回原始检查字段和可组合的错误列表。
    return dict_data, list_errors

# 验证指定服务器是否提供可用远程工作区。
def remote_server_workspace_check(
    skill_dir: Path, server_id: str
) -> tuple[dict[str, str], list[str]]:
    """执行指定服务器的远程工作区检查。

    参数：skill_dir 为远程 SSH skill 根，server_id 为服务器标识。
    返回：解析后的工作区字段与命令失败错误列表。
    """

    # workspace-check 在基础连接通过后验证远程工作目录。
    completed_process_result = run_remote_ssh(  # 决定候选能否承载任务的工作区结果。
        skill_dir,  # 提供工作区检查 CLI 的安装根。
        "workspace-check",  # 验证远程工作目录的子命令。
        "--server",  # 工作区检查的服务器选择开关。
        server_id,  # 待验证工作区所属服务器。
    )

    # 解析工作区路径和状态等机器字段。
    dict_data = parse_remote_kv(  # 服务器工作区检查字段。
        completed_process_result.stdout  # workspace-check 输出的状态字段。
    )

    # 错误列表可与基础连接错误统一聚合。
    list_errors: list[str] = []  # 当前服务器工作区检查错误。

    # 非零退出码表示工作区访问或远程命令失败。
    if completed_process_result.returncode != 0:

        # 公共摘要保证输出流为空时仍包含退出码。
        str_summary = remote_failure_summary(  # 工作区检查失败摘要。
            completed_process_result,  # 失败的工作区检查结果。
            "workspace-check",  # 工作区失败摘要中的命令标签。
        )

        # 服务器标识把错误绑定到具体故障切换候选。
        list_errors.append(
            f"erie-remote-ssh workspace-check failed for {server_id}: {str_summary}"
        )

    # 工作区领域状态必须明确通过才能参与任务路由。
    if dict_data.get("status") != "ok":

        # 异常状态与进程退出错误可以同时保留。
        list_errors.append(
            f"erie-remote-ssh workspace-check did not return ok status for {server_id}"
        )

    # 返回工作区事实和当前候选的全部诊断。
    return dict_data, list_errors

# 提供远程 SSH skill 缺失时的安装恢复指引。
def remote_install_command_hint(skill_dir: Path | None = None) -> str:
    """生成远程 SSH skill 的安装命令提示。

    参数：skill_dir 为可选安装目录，用于兼容调用方签名。
    返回：包含仓库和安装规格的 skill 安装命令。
    """

    # 兼容参数保留旧调用签名，安装指引不依赖当前残缺目录。
    if skill_dir is not None:

        # 已提供目录时仍要求从受控仓库重新安装完整依赖。
        return (
            f"Install `{REMOTE_SSH_SKILL_NAME}` from {REMOTE_SSH_GIT_URL}, "
            "then rerun `python scripts/collect_design_profile.py <project> --resume`."
        )

    # 未发现任何目录时使用相同的受控安装来源。
    return (
        f"Install `{REMOTE_SSH_SKILL_NAME}` from {REMOTE_SSH_GIT_URL}, "
        "then rerun `python scripts/collect_design_profile.py <project> --resume`."
    )

# 构造远程服务器交互配置命令。
def remote_configure_command_hint(skill_dir: Path) -> str:
    """生成远程服务器交互配置命令提示。

    参数：skill_dir 为远程 SSH skill 根。
    返回：调用已解析远程 CLI configure 的完整命令或能力错误文本。
    """

    # 配置提示复用运行命令的入口解析顺序。
    path_entry = remote_ssh_entry_path(skill_dir)  # 配置提示绑定的 CLI 路径

    # 入口缺失时返回精确能力诊断，不展示不可执行的旧路径。
    if path_entry is None:

        # 文本与执行链保持一致，便于状态机和用户识别同一问题。
        return "erie-remote-ssh is installed but no supported CLI entry was found"

    # 基础命令指向统一解析后的 CLI 入口。
    str_command = f"python {path_entry} configure"  # 远程服务器交互配置命令

    # 兼容布局探测结果用于显式传入实际设置文件。
    path_settings = remote_settings_path(skill_dir)  # 当前 skill 设置文件路径。

    # 找到设置文件时避免 CLI 再按单一旧布局猜测。
    if path_settings is not None:

        # 配置命令绑定到已经通过结构验证的设置文件。
        str_command += f" --settings {path_settings}"  # 绑定已发现设置文件。

    # 设计访谈要求用户在交互流程中明确完成服务器配置。
    str_command += " --interactive"  # 要求交互收集服务器配置。

    # 返回可直接展示给用户的恢复命令。
    return str_command

# 从设计状态读取类型安全的远程门禁分区。
def remote_gate_payload(state: dict[str, Any]) -> dict[str, Any]:
    """读取设计状态中的远程门禁载荷。

    参数：state 为设计访谈持久化状态。
    返回：类型有效的远程门禁映射；缺失或损坏时返回空映射。
    shape/维度：输入输出均为键值映射，不使用数值数组维度。
    dtype/类型：字段由 dict、list、str 与 bool 等 JSON 兼容类型组成。
    unit/单位：状态字段没有物理单位，含义由远程门禁 schema 定义。
    """

    # 缺失分区使用空映射，避免状态恢复阶段产生 KeyError。
    dict_gate = state.get("remote_server_gate", {})  # 原始远程服务器门禁载荷。

    # 非映射旧状态不参与远程依赖和路由决策。
    return dict_gate if isinstance(dict_gate, dict) else {}

# 将远程门禁分区原地写回设计状态。
def set_remote_gate_payload(state: dict[str, Any], payload: dict[str, Any]) -> None:
    """将远程门禁载荷写入设计状态。

    参数：state 为可变设计状态，payload 为待保存的远程门禁映射。
    返回：无；函数原地更新 state。
    shape/维度：输入是两个键值映射，不使用数值数组维度。
    dtype/类型：payload 字段保持 JSON 兼容的 Python 业务类型。
    unit/单位：门禁状态不含物理量单位。
    """

    # 单一键写入保持访谈状态 schema 的远程分区边界。
    state["remote_server_gate"] = payload  # 最新远程门禁持久化载荷。

# 构造服务器标识到规范化记录的快速索引。
def server_registry_map(registry: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """按规范化服务器标识索引注册表记录。

    参数：registry 为规范化服务器记录列表。
    返回：服务器标识到记录的映射。
    """

    # 仅索引映射类型且标识非空的记录。
    return {
        str(item.get("id", "")).strip(): item  # 服务器标识对应的完整记录。
        for item in registry  # 规范化注册表输入顺序。
        if isinstance(item, dict)  # 排除损坏的非映射元素。
        and str(item.get("id", "")).strip()  # 排除无法路由的空标识。
    }

# 将主服务器和回退服务器展开为实际尝试顺序。
def ordered_route_server_ids(route: dict[str, Any]) -> list[str]:
    """按主服务器优先顺序展开任务路由目标。

    参数：route 为规范化任务路由记录。
    返回：主服务器在前、回退服务器在后的去重标识列表。
    """

    # 实际尝试顺序以主服务器字段开头。
    str_primary = str(  # 路由展开使用的首选服务器标识。
        route.get("primary_server_id", "")  # 路由首选服务器字段。
    ).strip()

    # 输出列表同时承担顺序保持和重复过滤。
    list_ordered: list[str] = []  # 服务器实际尝试顺序。

    # 非空主服务器始终位于回退列表之前。
    if str_primary:

        # 登记首选服务器作为第一个尝试目标。
        list_ordered.append(str_primary)

    # 规范化回退列表并保留用户确认的顺序。
    for server_id in normalize_remote_task_list(route.get("fallback_server_ids", [])):

        # 主服务器或更早回退项不重复加入尝试顺序。
        if server_id not in list_ordered:

            # 首次出现的回退服务器追加到队尾。
            list_ordered.append(server_id)

    # 返回故障切换执行器可直接遍历的服务器标识。
    return list_ordered

# 按任务比较键选择唯一的远程路由记录。
def match_remote_task_route(
    task_routes: list[dict[str, Any]], task_name: str
) -> dict[str, Any] | None:
    """按规范化任务名查找远程路由。

    参数：task_routes 为路由列表，task_name 为待执行任务名。
    返回：首个匹配路由；没有匹配项时为 None。
    """

    # 调用方任务名称先转换为与持久化路由一致的比较键。
    str_task_key = normalize_remote_task_key(task_name)  # 待匹配任务路由键。

    # 空任务名称不能隐式选择任意服务器。
    if not str_task_key:

        # 缺失任务键由上层转换为明确阻断结果。
        return None

    # 路由列表按用户确认顺序查找首个匹配项。
    for route in task_routes:

        # 损坏的非映射路由不参与任务匹配。
        if not isinstance(route, dict):

            # 继续检查后续结构有效的路由记录。
            continue

        # 持久化任务名称重新规范化以兼容旧合同。
        if normalize_remote_task_key(route.get("task_name", "")) == str_task_key:

            # 返回完整路由供服务器引用和能力检查使用。
            return route

    # 没有匹配路由时不允许猜测默认服务器。
    return None

# 校验任务路由引用的主服务器和回退服务器存在于注册表。
def validate_route_server_ids(
    route: dict[str, Any], registry: dict[str, dict[str, Any]]
) -> list[str]:
    """验证路由引用的服务器均存在且已启用。

    参数：route 为任务路由，registry 为服务器索引。
    返回：未知或禁用服务器的错误说明列表。
    """

    # 每个未知引用独立报告，便于一次修复整条路由。
    list_errors: list[str] = []  # 当前路由服务器引用错误。

    # 任务名仅用于让错误消息指向具体路由。
    str_task_name = (  # 路由错误展示使用的任务名称。
        str(route.get("task_name", "")).strip()  # 路由任务展示字段。
        or "<unknown>"  # 缺失任务名时的诊断占位符。
    )

    # 引用校验要求路由提供可解析的主服务器。
    str_primary = str(  # 注册表校验使用的主服务器标识。
        route.get("primary_server_id", "")  # 待验证主服务器字段。
    ).strip()

    # 缺失主服务器时无需执行注册表查找。
    if not str_primary:

        # 阻断消息明确指出缺少必填字段。
        list_errors.append(f"route `{str_task_name}` is missing primary_server_id")

    # 非空主服务器必须存在于当前注册表。
    elif str_primary not in registry:

        # 未知主服务器意味着合同与服务器事实已经漂移。
        list_errors.append(
            f"route `{str_task_name}` references unknown primary server `{str_primary}`"
        )

    # 每个回退服务器同样必须在注册表中可解析。
    for server_id in normalize_remote_task_list(route.get("fallback_server_ids", [])):

        # 未知回退项会在故障切换时产生不可执行分支。
        if server_id not in registry:

            # 报告具体任务和回退服务器标识。
            list_errors.append(
                f"route `{str_task_name}` references unknown fallback server `{server_id}`"
            )

    # 返回全部未知引用，空列表表示结构引用完整。
    return list_errors

# 构造服务器通过双重检查后的选择结果。
def selected_remote_server_result(
    route: dict[str, Any], server_id: str, registry: dict[str, dict[str, Any]],
    check_data: dict[str, str], workspace_data: dict[str, str],
    attempted_server_ids: list[str], failures: list[str],
) -> dict[str, Any]:
    """封装成功远程路由解析结果。

    参数：route 为匹配路由，server_id 为选中服务器，registry 为服务器索引，
    check_data 和 workspace_data 为双重检查字段，attempted_server_ids 为尝试顺序，
    failures 为选中前失败摘要。
    返回：状态为 selected 的远程服务器解析结果。
    """

    # dict 调用避免把运行时结果误识别为静态参数配置表。
    return dict(
        ok=True,
        decision="selected",
        matched_route=route,
        selected_server_id=server_id,
        selected_server=registry.get(server_id, {}),
        check=check_data,
        workspace_check=workspace_data,
        attempted_server_ids=attempted_server_ids,
        failures=failures,
    )

# 构造所有服务器检查失败后的阻断结果。
def failed_remote_server_result(
    route: dict[str, Any], attempted_server_ids: list[str], failures: list[str]
) -> dict[str, Any]:
    """封装远程候选全部失败的解析结果。

    参数：route 为匹配路由，attempted_server_ids 为尝试顺序，failures 为失败摘要。
    返回：状态为 blocked 且包含完整尝试证据的解析结果。
    """

    # dict 调用把运行时证据与大规模静态配置表区分开。
    return dict(
        ok=False,
        decision="blocked",
        message=(
            "All primary and fallback remote servers for the matched task "
            "failed validation."
        ),
        matched_route=route,
        attempted_server_ids=attempted_server_ids,
        failures=failures,
    )

# 选择任务路由并按主服务器、回退服务器顺序执行双重检查。
def resolve_remote_server_for_task(
    contract: dict[str, Any], task_name: str, skill_dir: Path | None = None
) -> dict[str, Any]:
    """为任务选择首个通过连接与工作区检查的服务器。

    参数：contract 为远程合同，task_name 为任务名，skill_dir 为可选 skill 根。
    返回：包含匹配状态、选中服务器、尝试记录与错误的解析结果。
    """

    # 远程路由必须由当前工作目录合同显式启用。
    if not isinstance(contract, dict) or not contract.get("enabled"):

        # 禁止在未治理工作目录中隐式选择远程服务器。
        return {
            "ok": False,  # 路由解析未成功。
            "decision": "blocked",  # 调用方必须停止远程执行。
            "message": (  # 未启用远程路由的阻断原因。
                "Remote server routing is not enabled for this work folder."
            ),
        }

    # 持久化路由先执行类型收窄、任务去重和回退去重。
    list_routes = normalize_remote_task_routes(  # 当前合同中的规范化任务路由。
        contract.get("task_routes", [])  # 持久化任务路由集合。
    )

    # 任务名称必须匹配已登记路由，不能使用默认服务器兜底。
    dict_route = match_remote_task_route(list_routes, task_name)  # 匹配的任务路由。

    # 缺失路由表示当前 AGENTS 合同未授权该任务。
    if dict_route is None:

        # 返回可操作消息要求先更新当前工作目录治理合同。
        return {
            "ok": False,  # 没有完成服务器解析。
            "decision": "blocked",  # 未授权任务必须停止。
            "message": (  # 缺失任务路由的恢复指引。
                "No registered remote server route matches this task. "
                "Update the current work folder AGENTS.md before continuing."
            ),
        }

    # 注册表规范化后按服务器标识构造快速索引。
    dict_registry = server_registry_map(  # 服务器标识到事实记录的索引。
        normalize_remote_server_registry(  # 收窄持久化注册表。
            contract.get("server_registry", [])  # 持久化服务器事实列表。
        )
    )

    # 路由中的所有服务器引用必须存在于当前注册表。
    list_route_errors = validate_route_server_ids(  # 当前路由引用错误。
        dict_route,  # 当前任务匹配路由。
        dict_registry,  # 可引用服务器事实索引。
    )

    # 结构引用错误在调用任何外部命令之前阻断。
    if list_route_errors:

        # 一次返回全部未知服务器，减少反复修复合同。
        return {
            "ok": False,  # 路由引用验证失败。
            "decision": "blocked",  # 外部连接尚未开始。
            "message": "; ".join(list_route_errors),  # 合并后的引用错误。
            "matched_route": dict_route,  # 产生错误的任务路由。
        }

    # 依赖摘要决定是否能调用 erie-remote-ssh runtime。
    dict_dependency = remote_dependency_summary()  # 远程 SSH 安装事实。

    # 显式调用参数优先于本地 Codex 安装发现结果。
    path_active_skill_dir = skill_dir  # 本次解析使用的远程 SSH skill 根。

    # 未显式提供目录时使用已经验证的安装摘要路径。
    if path_active_skill_dir is None and dict_dependency.get("installed"):

        # 摘要路径来自结构完整性检查，可安全转回 Path。
        path_active_skill_dir = Path(  # 从安装摘要恢复的 runtime 根。
            str(dict_dependency.get("skill_dir", ""))  # 安装摘要中的目录文本。
        )

    # 缺失可用 runtime 时不能执行连接检查。
    if path_active_skill_dir is None or not str(path_active_skill_dir):

        # 阻断消息明确指出需要安装的依赖名称。
        return {
            "ok": False,  # 依赖预检未通过。
            "decision": "blocked",  # 无 runtime 时禁止远程执行。
            "message": (  # 缺失远程依赖的阻断原因。
                f"Remote dependency `{REMOTE_SSH_SKILL_NAME}` is not installed."
            ),
            "matched_route": dict_route,  # 已匹配但无法执行的路由。
        }

    # 尝试列表为成功和最终失败结果提供完整故障切换证据。
    list_attempted_server_ids: list[str] = []  # 已执行检查的服务器标识。

    # 每个失败候选保留服务器标识和两个检查阶段的诊断。
    list_failures: list[str] = []  # 按尝试顺序累计的服务器失败摘要。

    # 主服务器失败后按照用户确认顺序尝试回退服务器。
    for server_id in ordered_route_server_ids(dict_route):

        # 先登记尝试记录，确保异常结果也能解释执行顺序。
        list_attempted_server_ids.append(server_id)

        # 基础连接检查必须先于工作区检查。
        tuple_check_data, tuple_check_errors = remote_server_check(  # 连接字段与错误。
            path_active_skill_dir,  # 已验证远程 SSH runtime 根。
            server_id,  # 当前故障切换候选服务器。
        )

        # 基础检查通过时才访问远程工作区，避免重复失败噪声。
        tuple_workspace_data, tuple_workspace_errors = (  # 工作区字段与错误。
            remote_server_workspace_check(  # 基础连接通过后的工作区验证。
                path_active_skill_dir,  # 工作区验证使用的 runtime 目录。
                server_id,  # 基础连接已通过的候选服务器。
            )
            if not tuple_check_errors  # 仅对连接成功候选访问工作区。
            else ({}, [])  # 连接失败时跳过远程工作区命令。
        )

        # 两个检查阶段的错误合并为当前服务器失败原因。
        list_server_errors = (  # 当前服务器全部验证错误。
            tuple_check_errors  # 基础连接阶段错误。
            + tuple_workspace_errors  # 工作区验证阶段错误。
        )

        # 任一检查失败时保留摘要并继续故障切换。
        if list_server_errors:

            # 服务器标识与错误文本共同形成可读尝试记录。
            list_failures.append(
                f"{server_id}: {'; '.join(list_server_errors)}"
            )

            # 当前候选失败后进入下一个回退服务器。
            continue

        # 首个通过双重检查的服务器连同尝试证据一起返回。
        return selected_remote_server_result(
            dict_route, server_id, dict_registry,
            tuple_check_data, tuple_workspace_data,
            list_attempted_server_ids, list_failures,
        )

    # 所有主服务器和回退服务器失败时返回完整尝试证据。
    return failed_remote_server_result(
        dict_route, list_attempted_server_ids, list_failures
    )
