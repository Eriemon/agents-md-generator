"""提供 codebase-memory-mcp 的画像、安装、Git 与索引门禁。"""

# 延迟注解求值，避免运行时解析仅用于类型检查的泛型。
from __future__ import annotations

# 标准库负责 JSON 协议、环境发现、正则解析和外部进程调用。
import json
import os
import re
import shutil
import subprocess

# 路径和集合类型用于声明跨平台文件与命令边界。
from pathlib import Path
from typing import Any, Mapping, Sequence

# 上游仓库地址是安装说明与发布入口的共同来源。
REPOSITORY_URL = "https://github.com/DeusData/codebase-memory-mcp"  # 官方上游仓库地址

# 最新发布页用于引导用户选择平台对应的安装包。
RELEASES_URL = "/".join((REPOSITORY_URL, "releases", "latest"))  # 官方最新发布页

# 根级产物目录名称同时约束索引器、Git 和验证器。
ARTIFACT_DIRECTORY = ".codebase-memory"  # 本地持久化知识图谱目录

# 根锚定忽略规则防止同名嵌套目录被意外放宽。
IGNORE_RULE = f"/{ARTIFACT_DIRECTORY}/"  # 根级 Git 忽略规则

# 平台安装脚本名称用于组装指导命令，避免把工作目录写死在合同里。
WINDOWS_INSTALL_SCRIPT = Path("install.ps1")  # Windows 安装脚本相对路径

# Linux 入口只用于生成 chmod 与执行提示，不由治理流程直接调用。
LINUX_INSTALL_SCRIPT = Path("install.sh")  # Linux 人工安装命令的文件名来源

# 嵌套清单扫描模式由目录名和文件名组合，保持路径合同单一来源。
ARTIFACT_MANIFEST_GLOB = (  # 任意层级知识图谱清单匹配模式
    Path("**") / ARTIFACT_DIRECTORY / "artifact.json"  # 递归清单路径组成
).as_posix()

# 环境变量允许测试和显式部署覆盖自动发现结果。
ENVIRONMENT_BINARY_KEY = "AGENTS_MD_CODEBASE_MEMORY_MCP_BIN"  # MCP 可执行文件覆盖键

# 控制画像通过单一构造器保持问卷、渲染和验证合同一致。
def codebase_memory_contract(enabled: bool) -> dict[str, Any]:
    """构造写入控制画像的稳定知识图谱合同。

    参数:
        enabled: 是否启用知识图谱索引与调试路由。

    返回:
        可直接写入项目控制画像的知识图谱合同。
    """

    # 启用态只改变执行与调试语义，磁盘和 Git 边界始终稳定。
    return {
        "enabled": enabled,
        "project_root": ".",
        "artifact_directory": ARTIFACT_DIRECTORY,
        "index_mode": "full",
        "persistence": True,
        "debug_policy": "graph-first" if enabled else "disabled",
        "git_policy": "ignored-untracked",
        "releases_url": RELEASES_URL,
    }

# 安装说明仅提供官方人工路径，不在治理脚本内下载或执行安装包。
def installation_guidance() -> dict[str, Any]:
    """返回不执行自动下载的官方人工安装说明。

    参数:
        无。

    返回:
        包含 Windows、Linux、重启和恢复步骤的安装指导。
    """

    # 平台说明保留资源名称和最小命令，凭据与网络变更仍由用户控制。
    return {
        "repository_url": REPOSITORY_URL,
        "releases_url": RELEASES_URL,
        "automatic_install": False,
        "windows": {
            "asset": "codebase-memory-mcp-windows-amd64.zip（同时下载 checksums 文件）",
            "commands": [
                f"Unblock-File .\\{WINDOWS_INSTALL_SCRIPT}",
                f".\\{WINDOWS_INSTALL_SCRIPT}",
            ],
        },
        "linux": {
            "asset": "按 CPU 选择 linux-amd64 或 linux-arm64 压缩包，并校验 checksum",
            "commands": [
                f"chmod +x ./{LINUX_INSTALL_SCRIPT}",
                f"./{LINUX_INSTALL_SCRIPT}",
            ],
        },
        "restart_codex_required": True,
        "resume_instruction": "安装完成后重启 Codex，再恢复当前任务并重新检测。",
    }

# TOML 字符串解码器隔离引号兼容与错误回退语义。
def _decode_toml_command_value(str_value: str) -> str:
    """解码 command 的 TOML 字面量或双引号字符串。

    参数:
        str_value: 保留外层引号的 command 原始右值。

    返回:
        解码后的命令文本；格式无效时返回空字符串。
    """

    # 单引号字面量无需转义解析，直接剥离外层引号。
    if len(str_value) >= 2 and str_value[0] == str_value[-1] == "'":

        # 字面量内容去除外层单引号后直接返回。
        return str_value[1:-1]

    # 非双引号值不属于本模块支持的安全字符串形式。
    if len(str_value) < 2 or str_value[0] != '"' or str_value[-1] != '"':

        # 未知 TOML 值类型不参与外部命令执行。
        return ""

    # 双引号内容借助 JSON 解码，正确还原 Windows 反斜杠。
    try:

        # JSON 解码可还原双引号字符串中的转义字符。
        return str(json.loads(str_value))

    # 无效转义或未闭合字符串视为没有可用命令。
    except json.JSONDecodeError:

        # 无效配置值不再回退同一文件中的重复声明。
        return ""

# 配置行扫描器只在目标 MCP 节提取 command 声明。
def _command_from_toml_lines(list_lines: Sequence[str]) -> str:
    """从 TOML 行序列提取 codebase-memory-mcp 命令。

    参数:
        list_lines: Codex 配置文件的逐行文本。

    返回:
        目标节中的解码命令；未找到时返回空字符串。
    """

    # 当前节名称驱动逐行状态机，只解析目标节内的键。
    str_section = ""  # 当前 TOML 节名称

    # 逐行扫描保留节顺序，不跨节复用 command。
    for str_line in list_lines:

        # 去除布局空白后再判断节头或键值表达式。
        str_stripped = str_line.strip()  # 当前规范化配置行

        # 新节头会替换后续键值所属的上下文。
        if str_stripped.startswith("[") and str_stripped.endswith("]"):

            # 方括号内部文本是后续键值所属的完整节名。
            str_section = str_stripped[1:-1].strip()  # 当前 TOML 节名

            # 节头行本身不包含 command 键，继续读取下一行。
            continue

        # 非目标节不执行 command 正则，降低误匹配范围。
        if str_section != "mcp_servers.codebase-memory-mcp":

            # 跳过其他 MCP 或普通 Codex 配置节。
            continue

        # 正则仅捕获 command 右值，避免误读同节中的其他配置。
        match_command = re.match(  # command 键匹配结果
            r"command\s*=\s*(.+?)\s*$",  # command 键与完整右值模式
            str_stripped,  # 当前目标节配置行
        )

        # 只有 command 声明才结束扫描并进入安全字符串解码。
        if match_command:

            # 首个目标 command 是 Codex 对该 MCP 的有效配置入口。
            return _decode_toml_command_value(match_command.group(1))

    # 目标节没有合法 command 时返回稳定空值。
    return ""

# TOML 读取器只提取目标 MCP 节的 command，避免引入额外解析依赖。
def _toml_command(path_config: Path) -> str:
    """从 Codex MCP 配置节读取 command。

    参数:
        path_config: Codex 的 TOML 配置文件路径。

    返回:
        目标 MCP 节中的命令文本；配置缺失时返回空字符串。
    """

    # 配置缺失代表尚未通过 Codex 声明 MCP，不把它当作解析异常。
    if not path_config.is_file():

        # 缺少配置文件时以空命令结束发现流程。
        return ""

    # 文件读取与逐行协议解析分离，便于独立控制复杂度。
    list_config_lines = path_config.read_text(encoding="utf-8").splitlines()  # 目标节扫描所用配置行

    # 扫描器负责目标节定位与字符串解码。
    return _command_from_toml_lines(list_config_lines)

# 版本探测隔离外部二进制异常，调用方只消费规范化字符串。
def _binary_version(str_command: str) -> str:
    """执行轻量版本探测并返回规范化版本号。

    参数:
        str_command: 待探测的 MCP 可执行命令。

    返回:
        规范化语义版本；探测失败时返回空字符串。
    """

    # 外部命令限制为只读版本查询，并设置短超时避免阻塞治理入口。
    try:

        # 完整进程结果用于同时判断退出码与标准输出。
        completed_process_version = subprocess.run(  # MCP 版本查询进程结果
            [str_command, "--version"],  # 只读版本查询参数
            capture_output=True,  # 捕获版本查询输出
            text=True,  # 按文本模式返回输出
            encoding="utf-8",  # 使用统一输出编码
            errors="replace",  # 替换无法解码的版本字符
            timeout=10,  # 限制轻量探测耗时
            check=False,  # 由门禁显式判断退出码
        )

    # 命令缺失、不可执行或超时均表示当前依赖不可用。
    except (OSError, subprocess.SubprocessError):

        # 外部进程异常折叠为空版本证据。
        return ""

    # 非零退出不能作为已安装证据。
    if completed_process_version.returncode != 0:

        # 命令拒绝版本查询时按不可用处理。
        return ""

    # 优先抽取语义版本，兼容命令在版本前后附加产品名。
    match_version = re.search(  # 语义版本匹配结果
        r"(?:^|\s)v?(\d+\.\d+\.\d+)(?:\s|$)",  # 可选 v 前缀的三段版本模式
        completed_process_version.stdout,  # 版本查询标准输出
    )

    # 无标准版本片段时保留非空原始输出供诊断。
    return match_version.group(1) if match_version else completed_process_version.stdout.strip()

# 依赖发现按显式程度排序，避免 PATH 偶然命中覆盖用户配置。
def detect_codebase_memory_mcp(
    *,
    environ: Mapping[str, str] | None = None,
    path_value: str | None = None,
) -> dict[str, Any]:
    """按显式覆盖、Codex 配置和 PATH 顺序发现本地依赖。

    参数:
        environ: 可选环境变量映射，主要用于隔离测试。
        path_value: 可选 PATH 文本，显式提供时覆盖环境映射中的值。

    返回:
        安装态、配置态、命令来源、版本和配置路径证据。
    """

    # 复制环境映射，避免后续读取影响调用方持有的可变对象。
    dict_environment = dict(os.environ if environ is None else environ)  # 依赖发现环境快照

    # CODEX_HOME 缺失时回退到标准用户级 Codex 目录。
    path_codex_home = Path(  # Codex 配置根目录
        dict_environment.get("CODEX_HOME", str(Path.home() / ".codex"))  # Codex 根目录文本
    )

    # 环境覆盖具有最高优先级，便于受控部署与测试替身。
    str_override = dict_environment.get(ENVIRONMENT_BINARY_KEY, "").strip()  # 环境指定命令

    # Codex MCP 配置是持久化安装声明的主要来源。
    str_configured = _toml_command(path_codex_home / "config.toml")  # 配置文件指定命令

    # PATH 仅作为最后回退，不代表 Codex 已经配置该 MCP。
    str_path_command = shutil.which(  # PATH 发现的候选命令
        "codebase-memory-mcp",  # PATH 中的标准二进制名称
        path=path_value if path_value is not None else dict_environment.get("PATH"),  # 查询路径文本
    ) or ""  # 系统搜索得到的 MCP 可执行入口

    # 按环境、配置、PATH 的固定优先级选出唯一候选。
    str_command = str_override or str_configured or str_path_command  # 最终候选命令

    # 来源标签用于区分“已安装”与“已为 Codex 配置”。
    str_source = (  # 候选命令来源
        "environment"  # 环境覆盖来源
        if str_override  # 环境覆盖存在时优先
        else "codex-config"  # Codex 配置来源
        if str_configured  # 配置命令存在时采用
        else "path"  # PATH 回退来源
        if str_path_command  # 系统能够定位命令时采用
        else "missing"  # 没有任何候选命令
    )

    # 路径文件或可由系统定位的命令才允许执行版本探测。
    bool_exists = bool(str_command) and (  # 候选命令是否可执行
        Path(str_command).is_file() or bool(shutil.which(str_command))  # 路径或命令解析证据
    )

    # 成功返回版本号才构成真实安装证据。
    str_version = _binary_version(str_command) if bool_exists else ""  # MCP 版本证据

    # 配置态要求显式来源与有效版本同时成立，单纯 PATH 命中仍需配置。
    return {
        "installed": bool(str_version),
        "configured": bool(str_override or str_configured) and bool(str_version),
        "command": str_command,
        "source": str_source,
        "version": str_version,
        "config_path": str(path_codex_home / "config.toml"),
    }

# Git 调用统一禁用 shell，避免项目路径或参数被二次解释。
def _run_git(project: Path, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """在目标项目执行不经过 shell 的 Git 命令。

    参数:
        project: Git 仓库根目录。
        arguments: 不含 `git` 本体的参数序列。

    返回:
        保留退出码、标准输出和标准错误的进程结果。
    """

    # 调用方负责解释退出码，本层只固定安全执行参数与 UTF-8 输出。
    return subprocess.run(
        ["git", *arguments],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

# 已跟踪产物查询为取消跟踪确认门禁提供精确文件清单。
def _tracked_artifacts(project: Path) -> list[str]:
    """返回 Git 已跟踪的根级知识图谱产物。

    参数:
        project: 待检查的 Git 仓库根目录。

    返回:
        Git 索引中位于根级知识图谱目录的相对路径列表。
    """

    # `ls-files` 只读取索引，不扫描或修改本地知识图谱文件。
    completed_process_git = _run_git(  # Git 已跟踪产物查询结果
        project,  # 当前目标仓库
        ["ls-files", "--", ARTIFACT_DIRECTORY],  # 限定根级产物目录的索引查询参数
    )

    # 非 Git 项目或查询失败时不虚构已跟踪文件。
    if completed_process_git.returncode != 0:

        # 查询失败时由其他 Git 门禁负责报告仓库问题。
        return []

    # 空行不会形成取消跟踪目标，返回值保持仓库相对路径。
    return [
        str_line.strip()
        for str_line in completed_process_git.stdout.splitlines()
        if str_line.strip()
    ]

# 忽略规则写入保持幂等，重复治理不会制造无意义 diff。
def _ensure_ignore_rule(project: Path) -> None:
    """在根 .gitignore 中补入唯一规范忽略规则。

    参数:
        project: 待维护忽略规则的项目根目录。

    返回:
        无业务返回值；规则存在时不写文件。
    """

    # 根级文件与合同中的根锚定规则相匹配。
    path_gitignore = project / ".gitignore"  # 项目根 Git 忽略文件

    # 不存在文件按空文本处理，避免为读取单独分支。
    str_existing = (  # 原始 Git 忽略文本
        path_gitignore.read_text(encoding="utf-8")  # 已有忽略规则正文
        if path_gitignore.is_file()  # 文件存在时读取原文
        else ""  # 文件缺失时使用空文本
    )

    # 已有同一规范规则时禁止重复追加。
    if IGNORE_RULE in {str_line.strip() for str_line in str_existing.splitlines()}:

        # 幂等命中时不触碰文件时间戳。
        return

    # 仅在原文件缺少末尾换行时补充分隔符。
    str_prefix = (  # 新规则前的换行分隔符
        "" if not str_existing or str_existing.endswith("\n") else "\n"  # 必要分隔符
    )

    # UTF-8 写入保留原文本，并确保新增规则以换行结束。
    path_gitignore.write_text(f"{str_existing}{str_prefix}{IGNORE_RULE}\n", encoding="utf-8")

# CLI 输出解析从末尾回溯，允许工具在 JSON 前打印过程日志。
def _parse_cli_json(str_stdout: str) -> dict[str, Any]:
    """解析 CLI 在日志行之后输出的最后一个 JSON 对象。

    参数:
        str_stdout: MCP CLI 的完整标准输出。

    返回:
        最后一个合法 JSON 对象；不存在时返回空字典。
    """

    # 反向扫描优先选择工具最终响应，而不是前置日志中的 JSON 片段。
    for str_line in reversed(str_stdout.splitlines()):

        # 布局空白不属于 JSON 载荷。
        str_candidate = str_line.strip()  # 当前候选 JSON 行

        # 非对象起始行不尝试解码。
        if not str_candidate.startswith("{"):

            # 普通过程日志直接跳过。
            continue

        # 单行 JSON 解码失败后继续检查更早的候选行。
        try:

            # 解码结果可能是标量或数组，后续只接受协议对象。
            object_candidate = json.loads(str_candidate)  # 当前 JSON 解码结果

        # 日志中类似 JSON 的普通文本不应中断结果发现。
        except json.JSONDecodeError:

            # 当前候选无效时继续回溯更早的行。
            continue

        # MCP 工具协议只接受对象作为结构化结果。
        if isinstance(object_candidate, dict):

            # 最后出现的合法对象就是 CLI 最终响应。
            return object_candidate

    # 没有合法对象时由调用方结合退出码生成失败证据。
    return {}

# MCP CLI 包装器保留结构化响应并把进程失败折叠进同一载荷。
def _run_tool(str_command: str, str_tool: str, payload: dict[str, Any]) -> dict[str, Any]:
    """调用 codebase-memory-mcp CLI 并保留失败证据。

    参数:
        str_command: 已验证可执行的 MCP 命令。
        str_tool: MCP CLI 工具名称。
        payload: 传给工具的 JSON 对象。

    返回:
        工具响应以及稳定的进程退出码和可选错误文本。
    """

    # 索引可能耗时较长，但仍设置有限超时避免永久挂起。
    completed_process_tool = subprocess.run(  # 汇集工具响应解析与故障诊断所需的完整进程状态
        [str_command, "cli", str_tool, json.dumps(payload)],  # 指定工具名称与序列化业务载荷
        capture_output=True,  # 同时收集结构化响应与错误诊断文本
        text=True,  # 将命令输出转换为可逐行扫描的字符串
        encoding="utf-8",  # 按工具约定编码解析响应与日志文本
        errors="replace",  # 用替代字符保留含异常字节的诊断上下文
        timeout=1800,  # 防止全量索引无限占用治理写入流程
        check=False,  # 保留非零退出以构造结构化失败载荷
    )

    # 最终 JSON 对象作为工具业务载荷基础。
    dict_result = _parse_cli_json(completed_process_tool.stdout)  # MCP 工具结构化结果

    # 工具未显式回传退出码时补入真实进程状态。
    dict_result.setdefault("returncode", completed_process_tool.returncode)

    # 非零退出保留标准错误，缺失时回退到标准输出诊断。
    if completed_process_tool.returncode != 0:

        # 工具错误写入同一业务载荷，便于上层完整回显证据。
        dict_result.setdefault(
            "error",
            completed_process_tool.stderr.strip() or completed_process_tool.stdout.strip(),
        )

    # 调用方在统一映射上判断成功、失败和业务字段。
    return dict_result

# 持久化产物校验把磁盘事实与实时索引计数交叉核对。
def _artifact_errors(project: Path, dict_status: dict[str, Any]) -> list[str]:
    """核验根级持久化产物及磁盘、实时图计数一致性。

    参数:
        project: 已完成索引的项目根目录。
        dict_status: MCP `index_status` 返回的实时状态。

    返回:
        持久化文件、计数或嵌套位置不一致的错误列表。
    """

    # 所有持久化文件必须直接位于项目根的固定目录。
    path_artifact_directory = project / ARTIFACT_DIRECTORY  # 根级知识图谱产物目录

    # 清单记录项目身份和节点、边数量。
    path_manifest = path_artifact_directory / "artifact.json"  # 索引清单路径

    # 压缩图数据库是持久化索引的主体。
    path_graph = path_artifact_directory / "graph.db.zst"  # 压缩图数据库路径

    # 累计错误允许一次返回所有可独立修复的持久化问题。
    list_errors: list[str] = []  # 知识图谱产物错误集合

    # 清单或图数据库任一缺失都表示 persistence 尚未完成。
    if not path_manifest.is_file() or not path_graph.is_file():

        # 缺少持久化双文件时直接返回根因。
        return ["codebase-memory-mcp persistence artifacts are incomplete at project root"]

    # 清单解析错误需要转成稳定门禁诊断。
    try:

        # JSON 对象承载磁盘侧索引身份和统计数据。
        dict_manifest = json.loads(  # 磁盘索引清单
            path_manifest.read_text(encoding="utf-8")  # 索引清单原始文本
        )

    # 文件读取或 JSON 解码失败均视为清单损坏。
    except (OSError, json.JSONDecodeError):

        # 损坏清单不能参与项目身份或计数校验。
        return ["codebase-memory-mcp artifact.json is malformed"]

    # 节点与边计数分别校验，定位具体漂移维度。
    for str_key in ("nodes", "edges"):

        # 实时计数来自 MCP 状态接口。
        integer_live_count = dict_status.get(str_key)  # 当前实时图计数

        # 磁盘计数来自持久化清单。
        integer_disk_count = dict_manifest.get(str_key)  # 当前磁盘清单计数

        # 仅在实时值是整数时比较，接口失败由上层单独报告。
        if isinstance(integer_live_count, int) and integer_live_count != integer_disk_count:

            # 记录具体计数维度，便于判断是否需要重新索引。
            list_errors.append(f"codebase-memory-mcp {str_key} count differs between live index and artifact")

    # 全仓扫描同名清单，阻止子目录产生第二套知识图谱真值。
    for path_nested in project.glob(ARTIFACT_MANIFEST_GLOB):

        # 根级清单是唯一合法位置，其余路径均形成嵌套污染。
        if path_nested.parent != path_artifact_directory:

            # 嵌套相对路径进入诊断，避免暴露本机绝对目录。
            str_nested_path = path_nested.relative_to(project).as_posix()  # 嵌套清单仓库相对路径

            # 将位置证据加入累计错误集合，继续扫描其他嵌套清单。
            list_errors.append(
                f"nested codebase-memory artifact is forbidden: {str_nested_path}"
            )

    # 空列表代表磁盘、实时计数与位置约束全部一致。
    return list_errors

# 画像选择校验把开关与派生合同一致性收口到单一阶段。
def _profile_choice_gate(profile: dict[str, Any]) -> tuple[bool | None, dict[str, Any] | None]:
    """校验显式启用选择及其稳定合同。

    参数:
        profile: 已完成设计复核的项目控制画像。

    返回:
        规范布尔选择与可选阻断载荷；成功时阻断载荷为 None。
    """

    # 开关必须是显式布尔值，缺失时禁止推断默认行为。
    raw_enabled = profile.get("use_codebase_memory_mcp")  # 原始知识图谱启用选择

    # 非布尔值无法区分未回答与用户明确选择。
    if not isinstance(raw_enabled, bool):

        # 决策请求引导调用方回到设计问卷，而不是静默关闭功能。
        return None, {
            "ok": False,
            "errors": ["missing explicit use_codebase_memory_mcp choice"],
            "requires_user_confirmation": True,
            "decision_request": {"kind": "codebase_memory_usage"},
        }

    # 稳定合同必须与显式选择同步，阻止手工画像字段互相矛盾。
    dict_expected = codebase_memory_contract(raw_enabled)  # 当前选择对应的规范合同

    # 任一合同字段漂移都要求重新生成画像。
    if profile.get("codebase_memory_mcp_contract") != dict_expected:

        # 错误只报告合同不一致，不猜测需要覆盖的用户字段。
        return raw_enabled, {
            "ok": False,
            "errors": ["codebase_memory_mcp_contract does not match the explicit choice"],
        }

    # 成功结果同时交付已验证开关，并明确没有阻断载荷。
    return raw_enabled, None

# Git 边界阶段负责确认、忽略规则和保留本地文件的取消跟踪。
def _git_artifact_gate(
    project: Path,
    *,
    enabled: bool,
    apply: bool,
    confirm_untrack: bool,
) -> dict[str, Any] | None:
    """执行知识图谱产物的 Git 边界门禁。

    参数:
        project: 待治理的 Git 仓库根目录。
        enabled: 已通过画像校验的显式启用选择。
        apply: 是否允许维护忽略文件和 Git 索引。
        confirm_untrack: 用户是否确认取消跟踪本地产物。

    返回:
        阻断载荷；Git 边界闭合时返回 None。
    """

    # Git 索引事实决定是否需要用户授权取消跟踪。
    list_tracked = _tracked_artifacts(project)  # 当前已跟踪知识图谱产物

    # 本地文件保留但索引移除属于显式治理变更，不能自动确认。
    if list_tracked and not confirm_untrack:

        # 载荷完整列出待取消跟踪文件，供用户核对风险边界。
        return {
            "ok": False,
            "enabled": enabled,
            "errors": [".codebase-memory contains Git-tracked files"],
            "tracked_files": list_tracked,
            "requires_user_confirmation": True,
            "decision_request": {"kind": "codebase_memory_git_untrack", "keep_local_files": True},
        }

    # 只读预检不修改忽略文件或 Git 索引。
    if not apply:

        # 没有阻断即完成当前 Git 预检阶段。
        return None

    # 根忽略规则确保持久化文件保持本地且不会再次被新增跟踪。
    _ensure_ignore_rule(project)

    # 没有已跟踪产物时无需执行 Git 索引变更。
    if not list_tracked:

        # 忽略规则已经闭合，当前阶段没有失败载荷。
        return None

    # `--cached` 保留工作区文件，仅改变 Git 索引状态。
    completed_process_untrack = _run_git(  # Git 取消跟踪进程结果
        project,  # 当前受管仓库
        ["rm", "-r", "--cached", "--", ARTIFACT_DIRECTORY],  # 仅移除索引的 Git 参数
    )

    # 成功取消跟踪时 Git 边界已经闭合。
    if completed_process_untrack.returncode == 0:

        # None 表示调用方可以继续依赖或索引阶段。
        return None

    # Git 原始错误优先于通用回退文本。
    return {
        "ok": False,
        "errors": [
            completed_process_untrack.stderr.strip() or "failed to untrack .codebase-memory"
        ],
    }

# 依赖阶段区分安装、Codex 配置与只读预检三类结果。
def _dependency_gate(apply: bool) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """校验 MCP 安装与 Codex 配置状态。

    参数:
        apply: 是否即将执行索引副作用。

    返回:
        依赖发现证据与可选提前结束载荷。
    """

    # 启用态首先收集本机安装与 Codex 配置证据。
    dict_dependency = detect_codebase_memory_mcp()  # MCP 依赖发现结果

    # 安装或配置任一缺失都暂停，并返回官方人工安装说明。
    if not dict_dependency["installed"] or not dict_dependency["configured"]:

        # 治理脚本不自动下载，调用方应展示决策请求并等待用户完成安装。
        return dict_dependency, {
            "ok": False,
            "enabled": True,
            "dependency": dict_dependency,
            "errors": ["codebase-memory-mcp is not installed and configured for Codex"],
            "requires_user_confirmation": True,
            "decision_request": {
                "kind": "codebase_memory_install",
                "guidance": installation_guidance(),
            },
        }

    # 应用模式需要继续索引，成功路径没有提前结束载荷。
    if apply:

        # 依赖证据供后续索引阶段读取命令入口。
        return dict_dependency, None

    # 只读预检保留依赖证据，但明确声明没有执行索引。
    return dict_dependency, {
        "ok": True,
        "enabled": True,
        "indexed": False,
        "dependency": dict_dependency,
    }

# 索引阶段闭合 full、persistence、实时状态和架构分析四层证据。
def _index_evidence_gate(project: Path, dict_dependency: dict[str, Any]) -> dict[str, Any]:
    """执行全量持久化索引并核验实时图证据。

    参数:
        project: 待索引的项目根目录。
        dict_dependency: 已通过安装与配置检查的依赖证据。

    返回:
        索引、状态、架构与持久化一致性的最终载荷。
    """

    # 写入前强制 full 与 persistence，保证知识图谱覆盖整个项目并落盘。
    dict_index = _run_tool(  # 全量持久化索引结果
        dict_dependency["command"],  # 已验证的 MCP 命令
        "index_repository",  # 全量索引工具名称
        {"repo_path": str(project.resolve()), "mode": "full", "persistence": True},  # 索引参数
    )

    # 索引命令失败时保留原始工具载荷，禁止继续查询派生状态。
    if dict_index.get("returncode") != 0:

        # 失败载荷携带底层索引证据供安装或配置诊断。
        return {
            "ok": False,
            "enabled": True,
            "errors": ["codebase-memory-mcp full index failed"],
            "index": dict_index,
        }

    # 持久化清单提供后续状态与架构查询所需的稳定项目标识。
    path_manifest = project / ARTIFACT_DIRECTORY / "artifact.json"  # 根级索引清单路径

    # 清单缺失时使用空映射，随后由项目身份检查返回稳定错误。
    dict_manifest = (  # 根级索引清单数据
        json.loads(path_manifest.read_text(encoding="utf-8"))  # 持久化清单对象
        if path_manifest.is_file()  # 清单存在时解析
        else {}  # 清单缺失时交由身份检查处理
    )

    # 项目标识必须来自刚写入的持久化清单，不能从目录名猜测。
    str_indexed_project = str(dict_manifest.get("project", "")).strip()  # MCP 索引项目标识

    # 缺少项目身份时无法可靠查询对应的实时图。
    if not str_indexed_project:

        # 不从文件夹名称猜测索引项目，防止查询到同名旧图。
        return {
            "ok": False,
            "enabled": True,
            "errors": ["codebase-memory-mcp artifact does not identify the indexed project"],
        }

    # 实时状态用于核对索引就绪度以及节点、边计数。
    dict_status = _run_tool(  # MCP 实时索引状态
        dict_dependency["command"],  # 状态查询使用的 MCP 命令
        "index_status",  # 实时状态工具名称
        {"project": str_indexed_project},  # 目标索引项目身份
    )

    # 架构查询证明知识图谱不仅落盘，而且能够提供项目结构分析。
    dict_architecture = _run_tool(  # MCP 架构分析结果
        dict_dependency["command"],  # 架构查询使用的 MCP 命令
        "get_architecture",  # 架构分析工具名称
        {
            "project": str_indexed_project,  # 目标架构项目身份
            "aspects": ["packages", "dependencies", "clusters"],  # 必查架构维度
        },
    )

    # 磁盘产物与实时状态的交叉验证错误形成最终阻断集合基础。
    list_errors = _artifact_errors(project, dict_status)  # 索引与持久化一致性错误

    # 状态或架构接口失败意味着图尚不能用于受管开发。
    if dict_status.get("returncode") != 0 or dict_architecture.get("returncode") != 0:

        # 两类实时查询共享一个就绪度错误，底层载荷仍分别保留。
        list_errors.append("codebase-memory-mcp live index or architecture analysis is not ready")

    # 最终载荷同时保存依赖、索引、状态和架构四层事实证据。
    return {
        "ok": not list_errors,
        "enabled": True,
        "indexed": not list_errors,
        "errors": list_errors,
        "dependency": dict_dependency,
        "index": dict_index,
        "status": dict_status,
        "architecture": dict_architecture,
    }

# 共享写入门禁按画像、Git、依赖和索引阶段依次短路。
def enforce_codebase_memory_write_gate(
    project: Path,
    profile: dict[str, Any],
    *,
    apply: bool,
    confirm_untrack: bool = False,
) -> dict[str, Any]:
    """在受管写入前编排知识图谱四阶段门禁。

    参数:
        project: 待写入治理文件的项目根目录。
        profile: 已完成设计复核的项目控制画像。
        apply: 是否执行忽略、取消跟踪和全量索引副作用。
        confirm_untrack: 用户是否确认从 Git 索引移除本地产物。

    返回:
        包含放行状态、错误、确认请求和索引证据的门禁载荷。
    """

    # 第一阶段元组同时承载规范开关与可能的画像阻断载荷。
    tuple_profile_gate = _profile_choice_gate(profile)  # 画像阶段的开关与阻断二元组

    # 首个元素是通过合同校验后的可选布尔选择。
    bool_enabled = tuple_profile_gate[0]  # 规范化知识图谱启用状态

    # 第二个元素仅在画像合同失败时包含结构化阻断信息。
    dict_profile_block = tuple_profile_gate[1]  # 画像阶段可选阻断载荷

    # 画像错误优先返回，禁止后续产生 Git 或索引副作用。
    if dict_profile_block is not None:

        # 画像阶段已经提供精确错误或用户决策请求。
        return dict_profile_block

    # 防御性检查阻止未来 helper 合同漂移进入副作用阶段。
    if not isinstance(bool_enabled, bool):

        # 内部合同异常使用稳定错误，而不是依赖运行时断言开关。
        return {"ok": False, "errors": ["codebase-memory-mcp profile gate returned no choice"]}

    # 第二阶段闭合本地产物忽略与取消跟踪边界。
    dict_git_block = _git_artifact_gate(  # Git 产物阶段阻断载荷
        project,  # 当前受管项目根目录
        enabled=bool_enabled,  # 已验证的显式启用选择
        apply=apply,  # 是否允许本阶段写入
        confirm_untrack=confirm_untrack,  # 用户取消跟踪确认状态
    )

    # Git 阶段失败时不继续探测或调用 MCP。
    if dict_git_block is not None:

        # Git 阶段载荷保留待确认文件或原始命令错误。
        return dict_git_block

    # 明确禁用时只要求画像与 Git 边界成立。
    if not bool_enabled:

        # 禁用结果明确标记未索引，避免调用方误解为空图成功。
        return {"ok": True, "enabled": False, "indexed": False}

    # 第三阶段元组同时返回依赖证据和可选安装或预检载荷。
    tuple_dependency_gate = _dependency_gate(apply)  # 依赖证据与提前结束二元组

    # 首个元素始终保留依赖发现事实，供索引阶段调用命令。
    dict_dependency = tuple_dependency_gate[0]  # 已安装并配置的 MCP 依赖证据

    # 第二个元素表示缺依赖失败或只读预检成功的提前结束状态。
    dict_dependency_end = tuple_dependency_gate[1]  # 依赖阶段可选结束载荷

    # 缺依赖或只读预检均在索引前结束。
    if dict_dependency_end is not None:

        # 提前结束载荷已经区分失败安装门禁与成功只读预检。
        return dict_dependency_end

    # 第四阶段执行索引并返回完整证据链。
    return _index_evidence_gate(project, dict_dependency)
