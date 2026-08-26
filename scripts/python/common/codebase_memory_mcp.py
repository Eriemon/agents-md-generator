"""提供 codebase-memory-mcp 的画像、安装、Git 与索引门禁。"""

# 延迟注解求值，避免运行时解析仅用于类型检查的泛型。
from __future__ import annotations

# 标准库负责 JSON 协议、环境发现、正则解析和外部进程调用。
import json
import os
import re
import shutil
import subprocess

# 时间类型用于把跨平台进程年龄转换为稳定 UTC 启动时间。
from datetime import datetime, timedelta, timezone

# 路径和集合类型用于声明跨平台文件与命令边界。
from pathlib import Path
from typing import Any, Mapping, Sequence

# 纯健康模块提供范围、WAL 基线和最终分类 hook。
from codebase_memory_health import (
    classify_index_scope,
    collect_wal_baseline,
    inspect_cbmignore,
    path_is_ignored,
)

# codebase-memory 合同值统一来自机器可读配置 catalog。
CODEBASE_MEMORY_CONTRACT_PATH = (  # 合同 catalog 文件路径
    Path(__file__).resolve().parents[3] / "config" / "codebase-memory-contract.json"  # catalog 相对技能根路径
)  # codebase-memory 合同 catalog 路径

# 读取配置文件中的 scope、WAL 和 install 字段，作为后续合同唯一来源。
def _load_codebase_memory_contract() -> dict[str, Any]:
    """读取机器可读的 codebase-memory 合同 catalog。

    参数:
        无。
    返回:
        图谱目录、健康阈值和安装入口配置映射。
    """

    # catalog 文本是后续合同构造器的唯一配置来源。
    return json.loads(CODEBASE_MEMORY_CONTRACT_PATH.read_text(encoding="utf-8"))

# 在模块初始化时绑定配置载荷，供常量和合同函数复用。
CODEBASE_MEMORY_CONTRACT = _load_codebase_memory_contract()  # 该载荷决定图谱目录、健康阈值和安装指令

# 上游仓库地址是安装说明与发布入口的共同来源。
REPOSITORY_URL = str(CODEBASE_MEMORY_CONTRACT["repository_url"])  # 官方上游仓库地址

# 最新发布页用于引导用户选择平台对应的安装包。
RELEASES_URL = "/".join((REPOSITORY_URL, "releases", "latest"))  # 官方最新发布页

# 根级产物目录名称同时约束索引器、Git 和验证器。
ARTIFACT_DIRECTORY = str(CODEBASE_MEMORY_CONTRACT["artifact_directory"])  # 本地持久化知识图谱目录

# 根锚定忽略规则防止同名嵌套目录被意外放宽。
IGNORE_RULE = f"/{ARTIFACT_DIRECTORY}/"  # 根级 Git 忽略规则

# 平台安装脚本名称用于组装指导命令，避免把工作目录写死在合同里。
WINDOWS_INSTALL_SCRIPT = Path(str(CODEBASE_MEMORY_CONTRACT["install_scripts"]["windows"]))  # Windows 安装脚本相对路径

# Linux 入口只用于生成 chmod 与执行提示，不由治理流程直接调用。
LINUX_INSTALL_SCRIPT = Path(str(CODEBASE_MEMORY_CONTRACT["install_scripts"]["linux"]))  # Linux 人工安装命令的文件名来源

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

    # 复制配置节点，避免调用方修改全局 catalog。
    dict_scope_policy = dict(CODEBASE_MEMORY_CONTRACT["scope_policy"])  # 作用域合同配置

    # 复制 WAL 健康节点，隔离调用方对返回对象的修改。
    dict_wal_health = dict(CODEBASE_MEMORY_CONTRACT["wal_health"])  # WAL 健康配置

    # 根据启用状态选择配置声明的调试策略。
    str_debug_policy_key = "debug_policy_enabled" if enabled else "debug_policy_disabled"  # 调试策略键

    # 读取当前启用状态对应的调试策略文本。
    str_debug_policy = str(dict_scope_policy.pop(str_debug_policy_key))  # 当前调试策略

    # 移除未选择的调试策略键，保持输出合同与历史结构一致。
    dict_scope_policy.pop("debug_policy_enabled", None)

    # 删除另一项未选择的调试策略键。
    dict_scope_policy.pop("debug_policy_disabled", None)

    # 从 scope 配置中提取顶层兼容字段。
    dict_contract = {  # 配置驱动的完整知识图谱合同
        "enabled": enabled,  # 当前显式启用状态
        "project_root": dict_scope_policy.pop("project_root"),  # 项目根合同
        "artifact_directory": ARTIFACT_DIRECTORY,  # 根级产物目录
        "index_mode": dict_scope_policy.pop("index_mode"),  # 索引模式
        "persistence": dict_scope_policy.pop("persistence"),  # 持久化开关
        "debug_policy": str_debug_policy,  # profile 调试语义
        "git_policy": dict_scope_policy.pop("git_policy"),  # Git 边界策略
        "releases_url": RELEASES_URL,  # 上游发布入口
        "scope_policy": dict_scope_policy,  # 作用域排除和保护规则
        "wal_health": dict_wal_health,  # WAL 健康阈值
    }

    # 返回配置驱动的知识图谱合同。
    return dict_contract

# 根合同和图谱健康检查共享同一 .cbmignore 路径判定。
def is_path_excluded_by_cbmignore(path_project: Path, path_candidate: Path) -> bool:
    """判断候选路径是否落在项目最终生效的 codebase-memory 排除范围内。

    参数：path_project 为项目根；path_candidate 为待判断的绝对或相对路径。
    返回：候选路径被根 `.cbmignore` 排除时为 True，否则为 False。
    """

    # 缺少范围文件时不猜测排除状态，交由上层合同报告配置缺失。
    path_ignore = path_project / ".cbmignore"  # 根范围规则文件

    # 没有规则文件不能安全地跳过嵌套产物。
    if not path_ignore.is_file():

        # 保守保留嵌套产物阻断行为。
        return False

    # 候选路径必须位于当前项目根下才能参与相对规则匹配。
    try:

        # 统一使用项目相对 POSIX 路径匹配目录排除规则。
        str_relative_path = path_candidate.relative_to(path_project).as_posix()  # 候选相对路径

    # 项目外路径不应被范围规则静默放行。
    except ValueError:

        # 项目外路径保持未排除状态，由调用方继续按安全合同处理。
        return False

    # 读取最终有序规则，让后续 allow 规则覆盖早期排除规则。
    list_rules = path_ignore.read_text(encoding="utf-8").splitlines()  # 根范围规则正文

    # 复用健康模块的 gitignore 语义实现，避免两个扫描器漂移。
    return path_is_ignored(str_relative_path, list_rules)

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

# 缓存根扫描器只读取目标 MCP 的 env 子节。
def _cache_root_from_toml_lines(list_lines: Sequence[str]) -> str:
    """从 TOML 行序列提取 codebase-memory-mcp 缓存根。

    参数：list_lines 为 Codex 配置逐行文本。
    返回：目标 env 子节中的 CBM_CACHE_DIR；缺失或无效时为空字符串。
    """

    # 当前节名称确保同名环境键不会从其他 MCP 泄漏进来。
    str_section = ""  # 缓存根扫描所在节。

    # 逐行状态机与 command 解析使用相同的窄范围策略。
    for str_line in list_lines:

        # 去除布局空白后再识别节头和目标键。
        str_stripped = str_line.strip()  # 缓存配置候选行。

        # 新节头切换后续键值所属上下文。
        if str_stripped.startswith("[") and str_stripped.endswith("]"):

            # 完整节名用于精确匹配目标 MCP 的 env 子节。
            str_section = str_stripped[1:-1].strip()  # 缓存扫描节标识。

            # 节头本身不含缓存根值。
            continue

        # 其他 MCP 或普通配置节中的同名键不得参与绑定。
        if str_section != "mcp_servers.codebase-memory-mcp.env":

            # 继续扫描后续目标节。
            continue

        # 缓存根只接受安全字符串形式，复用 TOML 字符串解码合同。
        match_cache_root = re.match(  # 缓存环境键解析结果。
            r"CBM_CACHE_DIR\s*=\s*(.+?)\s*$",  # 缓存根键与完整右值。
            str_stripped,  # 当前目标 env 配置行。
        )

        # 首个合法声明是 Codex 为该 MCP 注入的运行时缓存根。
        if match_cache_root:

            # 字符串解码失败时稳定返回空值并触发后续 fail-closed。
            return _decode_toml_command_value(match_cache_root.group(1))

    # 目标 env 子节缺少缓存根时返回稳定空值。
    return ""

# TOML 缓存根读取器不扫描其他配置文件或外部目录。
def _toml_cache_root(path_config: Path) -> str:
    """读取 Codex MCP 配置中的 CBM_CACHE_DIR。

    参数：path_config 为 Codex config.toml 路径。
    返回：配置缓存根；文件缺失时为空字符串。
    """

    # 缺少配置文件时无法建立运行时数据库绑定。
    if not path_config.is_file():

        # 空值由 WAL 门禁解释为证据不可用。
        return ""

    # 只读取一次配置文本并交给窄范围行扫描器。
    list_config_lines = path_config.read_text(encoding="utf-8").splitlines()  # 配置逐行文本。

    # 返回目标 env 子节的缓存根。
    return _cache_root_from_toml_lines(list_config_lines)

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

    # 平台配置根由技能目录解析。
    from agent_platform import load_agent_config, resolve_agent_home

    # 当前文件向上三级定位技能源码根目录。
    path_skill_root: Path = Path(__file__).resolve().parents[3]  # 当前技能根目录

    # 档案提供用户根、安装目录和 agent 标识。
    profile_agent = load_agent_config(path_skill_root)  # 当前平台配置档案

    # 环境变量仅覆盖用户根，不改变档案布局。
    str_raw_home = dict_environment.get("AGENT_HOME", "").strip() or dict_environment.get("CODEX_HOME", "").strip()  # 用户根覆盖文本

    # 解析用户根，读取 Codex MCP 配置。
    path_agent_home = resolve_agent_home(path_skill_root, str_raw_home, profile_agent.agent)  # 平台用户根目录

    # 环境覆盖具有最高优先级，便于受控部署与测试替身。
    str_override = dict_environment.get(ENVIRONMENT_BINARY_KEY, "").strip()  # 环境指定命令

    # Codex MCP 配置是持久化安装声明的主要来源。
    path_config = path_agent_home / "config.toml"  # 当前平台主配置路径。

    # 目标 MCP 节中的命令决定 Codex 配置态。
    str_configured = _toml_command(path_config)  # 配置文件指定命令

    # 显式进程环境优先于配置 env 子节，保持受控部署可覆盖。
    str_cache_root = dict_environment.get("CBM_CACHE_DIR", "").strip() or _toml_cache_root(path_config)  # WAL 绑定缓存根。

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
        "config_path": str(path_config),
        "cache_root": str_cache_root,
        "environment": {"CBM_CACHE_DIR": str_cache_root} if str_cache_root else {},
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
            obj_object_candidate: object = json.loads(str_candidate)  # 当前 JSON 解码结果

        # 日志中类似 JSON 的普通文本不应中断结果发现。
        except json.JSONDecodeError:

            # 当前候选无效时继续回溯更早的行。
            continue

        # MCP 工具协议只接受对象作为结构化结果。
        if isinstance(obj_object_candidate, dict):

            # 最后出现的合法对象就是 CLI 最终响应。
            return obj_object_candidate

    # 没有合法对象时由调用方结合退出码生成失败证据。
    return {}

# MCP CLI 包装器保留结构化响应并把进程失败折叠进同一载荷。
def _run_tool(
    str_command: str,
    str_tool: str,
    payload: dict[str, Any],
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """调用 codebase-memory-mcp CLI 并保留失败证据。

    参数:
        str_command: 已验证可执行的 MCP 命令。
        str_tool: MCP CLI 工具名称。
        payload: 传给工具的 JSON 对象。
        environment: 必须显式传播给 CLI 子进程的 MCP 环境。

    返回:
        工具响应以及稳定的进程退出码和可选错误文本。
    """

    # 子进程环境从当前进程复制，再只覆盖已验证的 MCP 专用键。
    dict_process_environment = dict(os.environ)  # CLI 子进程基础环境。

    # 配置中的 CBM_CACHE_DIR 必须与依赖证据一致传递给所有官方调用。
    if environment:

        # 显式 MCP 环境覆盖当前进程中的同名默认值。
        dict_process_environment.update(environment)

    # 索引可能耗时较长，但仍设置有限超时避免永久挂起。
    completed_process_tool = subprocess.run(  # 汇集工具响应解析与故障诊断所需的完整进程状态
        [str_command, "cli", str_tool, json.dumps(payload)],  # 指定工具名称与序列化业务载荷
        capture_output=True,  # 同时收集结构化响应与错误诊断文本
        text=True,  # 将命令输出转换为可逐行扫描的字符串
        encoding="utf-8",  # 按工具约定编码解析响应与日志文本
        errors="replace",  # 用替代字符保留含异常字节的诊断上下文
        env=dict_process_environment,  # 固定 CLI 与 MCP 服务使用相同缓存根。
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

# Windows 进程采集使用系统 CIM 接口精确比较可执行路径。
def _windows_mcp_processes(str_command: str) -> list[dict[str, Any]]:
    """采集与目标 MCP 可执行路径一致的 Windows 进程。

    参数：str_command 为已验证的 MCP 可执行入口。
    返回：原始匹配进程证据；调用方负责匿名化。
    """

    # 目标路径通过子进程环境传递，避免拼接进 PowerShell 表达式。
    dict_environment = dict(os.environ)  # 进程枚举子进程环境。

    # 专用键只服务本次只读进程匹配。
    dict_environment["AGENTS_MD_MCP_PROCESS_PATH"] = str(Path(str_command).resolve())  # CIM 精确匹配目标。

    # PowerShell 只读取 CIM 进程元数据并输出压缩 JSON。
    str_command_text = (
        "$target=[IO.Path]::GetFullPath($env:AGENTS_MD_MCP_PROCESS_PATH);"
        "$now=Get-Date;"
        "@(Get-CimInstance Win32_Process | Where-Object {"
        "$_.ExecutablePath -and [IO.Path]::GetFullPath($_.ExecutablePath) -eq $target"
        "} | ForEach-Object {"
        "[pscustomobject]@{pid=[int]$_.ProcessId;"
        "start_time=$_.CreationDate.ToUniversalTime().ToString('o');"
        "age_seconds=[int]($now-$_.CreationDate).TotalSeconds;"
        "command_line=$_.CommandLine;path=$_.ExecutablePath}"
        "}) | ConvertTo-Json -Compress"
    )  # 只读 CIM 查询表达式。

    # 禁用交互配置并限制枚举耗时。
    completed_process = subprocess.run(  # Windows MCP 进程枚举结果。
        ["powershell", "-NoProfile", "-Command", str_command_text],  # 无配置文件的只读 CIM 命令。
        capture_output=True,  # 捕获 CIM JSON 与诊断。
        text=True,  # 按文本协议读取输出。
        encoding="utf-8",  # 固定 JSON 解码字符集。
        errors="replace",  # 保留异常字符而不中断诊断。
        env=dict_environment,  # 传递精确匹配目标路径。
        timeout=10,  # 限制只读枚举耗时。
        check=False,  # 由本函数解释退出码。
    )

    # 枚举失败或空输出按无可用进程证据处理。
    if completed_process.returncode != 0 or not completed_process.stdout.strip():

        # WAL 容量门仍独立生效，进程条件不使用猜测值。
        return []

    # PowerShell 数组输出始终应为 JSON 列表。
    try:

        # 解码结果先保留为未知对象，再执行列表类型收窄。
        obj_object_processes: object = json.loads(completed_process.stdout)  # Windows 原始进程载荷。

    # 损坏输出不能进入健康评估。
    except json.JSONDecodeError:

        # 稳定回退为空证据。
        return []

    # 单进程输出可能是对象，多进程输出才是数组。
    if isinstance(obj_object_processes, dict):

        # 规范化为统一列表供调用方匿名化。
        return [obj_object_processes]

    # 多进程数组只保留映射项，过滤异常标量。
    if isinstance(obj_object_processes, list):

        # 仅保留符合 MCP 进程证据合同的映射项。
        return [item for item in obj_object_processes if isinstance(item, dict)]

    # 标量或其他 JSON 类型不形成进程证据。
    return []

# POSIX 进程采集通过 ps 的稳定字段匹配可执行名称。
def _posix_mcp_processes(str_command: str) -> list[dict[str, Any]]:
    """采集与目标 MCP 入口同名的 POSIX 进程。

    参数：str_command 为已验证的 MCP 可执行入口。
    返回：带 PID、启动时间、年龄和原始命令行的匹配证据。
    """

    # etimes 提供无需区域解析的进程年龄秒数。
    completed_process = subprocess.run(  # ps 字段采集进程结果。
        ["ps", "-eo", "pid=,etimes=,comm=,args="],  # 稳定机器字段与原始参数。
        capture_output=True,  # 捕获 ps 字段与诊断。
        text=True,  # 按文本行解析进程记录。
        encoding="utf-8",  # 固定跨平台输出字符集。
        errors="replace",  # 保留异常命令字符。
        timeout=10,  # 限制系统进程枚举耗时。
        check=False,  # 由本函数处理 ps 退出码。
    )

    # ps 不可用或失败时返回空证据。
    if completed_process.returncode != 0:

        # 不根据错误文本猜测运行中进程。
        return []

    # 可执行文件名用于过滤无关系统进程。
    str_target_name = Path(str_command).name  # MCP 可执行文件名。

    # 当前 UTC 时间用于从 age_seconds 计算稳定启动时间。
    datetime_now: datetime = datetime.now(timezone.utc)  # 进程采集时间。

    # 匹配结果保留原始命令行，随后由编排器统一匿名化。
    list_processes: list[dict[str, Any]] = []  # POSIX 匹配进程证据。

    # 每行最多拆分四段，命令参数中的空格保留在末段。
    for str_line in completed_process.stdout.splitlines():

        # 空行不属于进程记录。
        list_parts = str_line.strip().split(maxsplit=3)  # 当前 ps 字段。

        # 缺少任一稳定字段时跳过损坏记录。
        if len(list_parts) != 4 or Path(list_parts[2]).name != str_target_name:

            # 忽略当前损坏数值行并继续扫描。
            continue

        # PID 与年龄必须可转换为整数。
        try:

            # 数值转换结果用于构造匿名化前证据。
            int_pid = int(list_parts[0])  # 匹配进程 PID。

            # etimes 是进程自启动后的完整秒数。
            int_age_seconds = int(list_parts[1])  # 匹配进程年龄。

        # 损坏数值字段不进入结果。
        except ValueError:

            # 继续检查下一进程。
            continue

        # 启动时间由同一采集时刻和年龄推导。
        str_start_time = (datetime_now - timedelta(seconds=int_age_seconds)).isoformat()  # UTC 启动时间。

        # 原始命令行仅用于证明匹配来源，编排器不会向外返回。
        list_processes.append(
            {
                "pid": int_pid,
                "start_time": str_start_time,
                "age_seconds": int_age_seconds,
                "command_line": list_parts[3],
                "path": list_parts[2],
            }
        )

    # 返回全部同名可执行进程供调用方进一步收窄。
    return list_processes

# 平台路由器提供单一可替换 hook，便于测试隔离系统进程。
def _collect_matching_mcp_processes(str_command: str) -> list[dict[str, Any]]:
    """采集与 MCP 可执行入口匹配的本机进程。

    参数：str_command 为已验证的 MCP 可执行入口。
    返回：平台采集的原始进程证据。
    """

    # Windows 需要按完整可执行路径匹配。
    if os.name == "nt":

        # CIM 结果保留平台提供的真实启动时间。
        return _windows_mcp_processes(str_command)

    # 其他受支持平台使用 POSIX ps 字段。
    return _posix_mcp_processes(str_command)

# 官方项目列表中的任一损坏记录都会使根路径匹配证据失效。
def _collect_official_root_matches(
    project: Path,
    list_projects: list[Any],
) -> list[dict[str, Any]] | None:
    """收集与当前根精确匹配的官方项目记录。

    参数：project 为当前受管根，list_projects 为官方项目记录列表。
    返回：匹配记录列表；任一记录损坏时返回 None，要求调用方 fail-closed。
    """

    # 当前项目根统一解析后用于跨分隔符精确比较。
    path_resolved_project = project.resolve()  # 当前受管项目规范路径。

    # 匹配集合保持官方记录顺序供后续唯一性判断。
    list_matches: list[dict[str, Any]] = []  # 当前根匹配项目记录。

    # 每个官方记录都必须可安全解析，损坏项不能被忽略为 absent。
    for item in list_projects:

        # 非映射项或空根路径破坏官方身份证据完整性。
        if not isinstance(item, dict) or not str(item.get("root_path", "")).strip():

            # 损坏记录使整个官方身份列表不可用。
            return None

        # 路径解析可能因嵌入空字符或平台非法值失败。
        try:

            # 规范路径用于与当前项目执行精确比较。
            path_record_root = Path(str(item["root_path"])).resolve()  # 官方记录规范根。

        # 任一损坏根路径使整个项目列表证据不可用。
        except (OSError, ValueError):

            # 不把解析失败误判为目标项目不存在。
            return None

        # 只有规范根完全相同的记录进入唯一性判断。
        if path_record_root == path_resolved_project:

            # 保留完整官方记录供名称与数据库映射使用。
            list_matches.append(item)

    # 返回全部精确根匹配供调用方判断唯一性。
    return list_matches

# 根清单只在无官方根匹配时证明首次索引或身份冲突。
def _resolve_unmatched_project_state(project: Path, list_projects: list[Any]) -> dict[str, Any]:
    """解析当前根没有官方匹配记录时的索引状态。

    参数：project 为当前受管根，list_projects 为已验证结构的官方项目列表。
    返回：仅包含 absent 或 unavailable 的状态映射。
    """

    # 只有根持久化清单可以提供当前项目的既有显式身份。
    path_artifact = project / ARTIFACT_DIRECTORY / "artifact.json"  # 当前根索引清单。

    # 无清单且官方列表为空时，才能证明缓存中尚无任何身份冲突。
    if not path_artifact.is_file():

        # 其他项目存在时缺少可信 canonical id，必须阻止同名覆盖风险。
        return {"state": "unavailable" if list_projects else "absent"}

    # 清单损坏时不能把查找失败误判为首次索引。
    try:

        # 只读取显式 project 字段，不按目录名称推导身份。
        dict_artifact = json.loads(path_artifact.read_text(encoding="utf-8"))  # 根清单载荷。

    # 无效 JSON 无法提供可信项目身份。
    except (OSError, json.JSONDecodeError):

        # 保持 fail-closed，等待清单恢复。
        return {"state": "unavailable"}

    # 清单必须是映射并含非空 project 字段。
    str_artifact_project = str(dict_artifact.get("project", "")).strip() if isinstance(dict_artifact, dict) else ""  # 当前根显式项目身份。

    # 缺少项目字段不能作为 absent 证据。
    if not str_artifact_project:

        # 防止损坏清单触发错误首次索引。
        return {"state": "unavailable"}

    # 同一显式项目身份出现在其他根时属于身份冲突。
    bool_identity_conflict = any(  # 显式项目身份冲突结论。
        isinstance(item, dict)  # 官方记录必须保持映射结构。
        and str(item.get("name", "")).strip() == str_artifact_project  # 名称匹配根清单身份。
        for item in list_projects  # 遍历全部官方项目记录。
    )

    # 冲突身份保持不可用，其他显式身份允许首次建立索引。
    return {"state": "unavailable" if bool_identity_conflict else "absent"}

# 当前项目治理配置提供重复根记录的 preferred project name。
def _preferred_index_project_name(project: Path) -> str:
    """读取项目配置声明的 codebase-memory preferred project name。

    参数：project 为当前受管项目根。
    返回：preferred project name；配置缺失或损坏时返回空字符串。
    """

    # preferred name 只从当前项目治理配置读取，不从目录名猜测。
    path_profile = project / ".agents" / "agents-control.json"  # 项目治理配置路径

    # 缺失治理配置时不能安全消解重复根记录。
    if not path_profile.is_file():

        # 缺失配置无法消解重复索引身份。
        return ""

    # 读取配置并保留 JSON 错误的 fail-closed 边界。
    try:

        # 项目画像提供稳定的 canonical index name。
        obj_profile = json.loads(path_profile.read_text(encoding="utf-8"))  # 项目治理对象

    # 配置损坏时不使用任何候选名称。
    except (OSError, UnicodeError, json.JSONDecodeError):

        # 历史项目记录继续保留，当前写入保持阻断。
        return ""

    # 只有对象配置可以提供 preferred project name。
    if not isinstance(obj_profile, dict):

        # 非对象根不参与身份选择。
        return ""

    # 优先读取 codebase_memory_mcp_contract 的显式字段，再回退项目 name。
    obj_contract = obj_profile.get("codebase_memory_mcp_contract", {})  # codebase-memory 合同节点

    # 合同节点存在时优先读取 preferred name。
    if isinstance(obj_contract, dict):

        # 显式 preferred name 是重复缓存记录的唯一选择器。
        str_preferred_name = str(obj_contract.get("preferred_project_name", "")).strip()  # 配置声明的首选项目名

        # 非空首选名可以直接完成重复记录消歧。
        if str_preferred_name:

            # 返回经过配置确认的 preferred name。
            return str_preferred_name

    # 顶层 name 是已确认项目身份的兼容来源。
    return str(obj_profile.get("name", "")).strip()

# 官方项目列表解析器只接受根路径唯一匹配的索引记录。
def _resolve_indexed_project_binding(
    project: Path,
    dict_dependency: dict[str, Any],
) -> dict[str, Any]:
    """把官方项目记录唯一绑定到缓存根中的数据库。

    参数：project 为当前受管根，dict_dependency 为 MCP 命令与缓存根证据。
    返回：indexed、absent 或 unavailable 状态；仅 indexed 包含数据库路径。
    """

    # 项目身份必须来自官方 list_projects，不能从工作目录名猜测。
    dict_projects = _run_tool(  # 项目身份查询载荷。
        dict_dependency["command"],  # 项目枚举所用可执行入口。
        "list_projects",  # 官方项目枚举工具。
        {},  # 项目枚举不接受路径猜测过滤。
        dict_dependency.get("environment"),  # 枚举使用的缓存隔离环境。
    )  # 当前缓存中的官方项目列表响应。

    # 工具失败或载荷损坏时不允许推导数据库路径。
    if dict_projects.get("returncode") != 0 or not isinstance(dict_projects.get("projects"), list):

        # unavailable 会让 WAL 收集器稳定 fail-closed。
        return {"state": "unavailable"}

    # 独立解析官方根记录，避免损坏项被误判为当前项目不存在。
    list_matches = _collect_official_root_matches(project, dict_projects["projects"])  # 当前根匹配的官方项目记录。

    # 重复根记录先尝试使用治理配置声明的 preferred project name 消歧。
    if list_matches is not None and len(list_matches) > 1:

        # 历史记录不删除，只收敛到当前配置的 canonical name。
        str_preferred_name = _preferred_index_project_name(project)  # 配置声明的 preferred name

        # 只保留与 preferred name 一致的历史记录。
        list_matches = [  # 消歧后的官方项目记录
            dict_match  # 保留匹配的完整项目记录
            for dict_match in list_matches  # 遍历同根历史记录
            if str(dict_match.get("name", "")).strip() == str_preferred_name  # 只保留配置首选名
        ]  # 完成重复根记录消歧

    # 损坏记录或消歧后仍重复都无法提供唯一身份绑定。
    if list_matches is None or len(list_matches) > 1:

        # unavailable 阻止错配项目继续索引。
        return {"state": "unavailable"}

    # 零根匹配可能是合法首次索引，也可能是旧项目身份指向其他根。
    if not list_matches:

        # 根清单和官方名称共同决定 absent 或 unavailable。
        return _resolve_unmatched_project_state(project, dict_projects["projects"])

    # 唯一记录名称决定 MCP 官方缓存文件名。
    str_project_name = str(list_matches[0].get("name", "")).strip()  # 官方项目名称。

    # 名称必须是单个安全文件名，禁止路径分隔符逃逸缓存根。
    if not str_project_name or Path(str_project_name).name != str_project_name:

        # 非法名称不能用于构造数据库路径。
        return {"state": "unavailable"}

    # 缓存根必须由 Codex MCP env 合同显式提供。
    str_cache_root = str(dict_dependency.get("cache_root", "")).strip()  # 已配置缓存根文本。

    # 缺少缓存根时即使项目匹配也无法唯一定位数据库。
    if not str_cache_root:

        # 保持 fail-closed，不回退扫描外部目录。
        return {"state": "unavailable"}

    # 官方缓存布局使用项目名加 .db，并要求文件直接位于缓存根。
    path_database = (Path(str_cache_root).resolve() / f"{str_project_name}.db").resolve()  # 项目数据库路径。

    # 父目录复核防止异常项目名绕出缓存根。
    if path_database.parent != Path(str_cache_root).resolve():

        # 路径逃逸按不可用证据处理。
        return {"state": "unavailable"}

    # 最小绑定载荷只提供 WAL 健康所需事实。
    return {
        "state": "indexed",
        "name": str_project_name,
        "project_path": str(project.resolve()),
        "database_path": str(path_database),
    }

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

        # 根范围明确排除的授权快照不属于当前项目扫描树。
        if is_path_excluded_by_cbmignore(project, path_nested):

            # 继续检查其他未被范围规则排除的候选清单。
            continue

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
def _index_evidence_gate(
    project: Path,
    dict_dependency: dict[str, Any],
    *,
    str_project_name: str | None = None,
) -> dict[str, Any]:
    """执行全量持久化索引并核验实时图证据。

    参数:
        project: 待索引的项目根目录。
        dict_dependency: 已通过安装与配置检查的依赖证据。
        str_project_name: 已绑定的索引项目名；首次索引时传 None。

    返回:
        索引、状态、架构与持久化一致性的最终载荷。
    """

    # 写入前强制 full 与 persistence，保证知识图谱覆盖整个项目并落盘。
    dict_index_arguments: dict[str, Any] = {  # full/persistence 索引参数
        "repo_path": str(project.resolve()),  # 绑定项目根路径
        "mode": "full",  # 全量图谱模式
        "persistence": True,  # 写入持久化图谱产物
    }

    # 已有绑定复用原名，避免同根重复项目。
    if str_project_name:

        # 仅传回已通过根路径校验的名称。
        dict_index_arguments["name"] = str_project_name  # 复用已绑定项目名称

    # 使用稳定参数索引，首次仍用官方默认名。
    dict_index = _run_tool(  # 全量持久化索引结果
        dict_dependency["command"],  # 已验证的 MCP 命令
        "index_repository",  # 全量索引工具名称
        dict_index_arguments,  # 带稳定名称的 MCP 索引载荷
        dict_dependency.get("environment"),  # 全量索引的缓存隔离环境。
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
        dict_dependency.get("environment"),  # 状态查询的缓存隔离环境。
    )

    # 架构查询证明知识图谱不仅落盘，而且能够提供项目结构分析。
    dict_architecture = _run_tool(  # MCP 架构分析结果
        dict_dependency["command"],  # 架构查询使用的 MCP 命令
        "get_architecture",  # 架构分析工具名称
        {
            "project": str_indexed_project,  # 目标架构项目身份
            "aspects": ["packages", "dependencies", "clusters"],  # 必查架构维度
        },
        dict_dependency.get("environment"),  # 架构查询的缓存隔离环境。
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
    """在受管写入前编排知识图谱七阶段门禁。

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

    # 第三阶段验证或更新根 .cbmignore 受管范围。
    dict_contract = codebase_memory_contract(bool_enabled)  # 当前启用选择对应完整合同。

    # scope_policy 是范围纯函数的唯一规则来源。
    dict_scope_policy = dict_contract["scope_policy"]  # 根索引范围合同。

    # apply 只允许修改 marker 内或追加唯一受管区。
    dict_scope_result = inspect_cbmignore(project, dict_scope_policy, apply)  # 范围阶段证据。

    # 范围失败时不得探测依赖或写入索引。
    if not dict_scope_result.get("ok", False):

        # 原样返回固定范围错误码和修复边界。
        return dict_scope_result

    # 第四阶段元组同时返回依赖证据和可选安装或预检载荷。
    tuple_dependency_gate = _dependency_gate(apply)  # 依赖证据与提前结束二元组

    # 首个元素始终保留依赖发现事实，供索引阶段调用命令。
    dict_dependency = tuple_dependency_gate[0]  # 已安装并配置的 MCP 依赖证据

    # 第二个元素表示缺依赖失败或只读预检成功的提前结束状态。
    dict_dependency_end = tuple_dependency_gate[1]  # 依赖阶段可选结束载荷

    # 缺依赖或只读预检均在索引前结束。
    if dict_dependency_end is not None:

        # 提前结束载荷已经区分失败安装门禁与成功只读预检。
        return dict_dependency_end

    # 第五阶段先用官方项目列表建立当前根的唯一数据库绑定。
    dict_indexed_project = _resolve_indexed_project_binding(project, dict_dependency)  # 已有项目绑定证据。

    # 只有唯一绑定项目需要采集同一 MCP 可执行入口的进程年龄证据。
    if dict_indexed_project.get("state") == "indexed":

        # 原始进程证据可能包含命令行、环境或可执行路径。
        list_raw_processes = _collect_matching_mcp_processes(dict_dependency["command"])  # 原始匹配进程。

        # WAL 纯函数只接收 PID、启动时间和年龄，敏感字段在边界处剥离。
        list_safe_processes = [
            {
                "pid": int(item.get("pid", 0)),  # 匿名进程标识。
                "start_time": str(item.get("start_time", "")),  # 公开 UTC 启动时间。
                "age_seconds": int(item.get("age_seconds", 0)),  # 阈值所需进程年龄。
            }  # 当前匿名化进程记录。
            for item in list_raw_processes  # 遍历平台采集原始证据。
            if isinstance(item, dict)  # 丢弃损坏的非映射项。
        ]  # 匿名化进程证据。

        # 新映射避免修改项目绑定 helper 的返回对象。
        dict_indexed_project = {**dict_indexed_project, "processes": list_safe_processes}  # WAL 输入证据。

    # 缺少唯一绑定时基线 helper 固定 fail closed。
    dict_wal_baseline = collect_wal_baseline(  # 索引前 WAL 与进程证据。
        project,  # 当前受管项目根。
        dict_dependency,  # 已验证 MCP 依赖与缓存根。
        dict_indexed_project,  # 官方项目列表绑定证据。
        dict_contract["wal_health"],  # 固定 WAL 阈值合同。
    )

    # WAL 证据缺失或异常时不得启动 full index。
    if not dict_wal_baseline.get("ok", False):

        # 原样返回基线固定错误码。
        return dict_wal_baseline

    # 第六阶段执行 full persistent index 并核对基础证据。
    str_index_name: str | None = None  # 首次索引不覆盖官方默认项目名

    # 已有索引时复用根绑定名称，避免派生副本。
    if dict_indexed_project.get("state") == "indexed":

        # 名称已通过根路径校验，可复用。
        str_index_name = str(dict_indexed_project.get("name", "")).strip()  # 已绑定项目名称

    # 复用已绑定名称，避免 full index 产生同根重复项目。
    dict_index_result = _index_evidence_gate(  # 使用稳定名称执行 full index
        project,  # 绑定待更新的知识图谱根
        dict_dependency,  # 已验证 MCP 依赖
        str_project_name=str_index_name,  # 保持当前缓存文件名稳定
    )  # full index 阶段证据。

    # 索引失败时不得用范围分类覆盖原始诊断。
    if not dict_index_result.get("ok", False):

        # 原样返回索引器错误。
        return dict_index_result

    # 第七阶段以真实项目树和最终 .cbmignore 复核索引范围。
    dict_final_verification = classify_index_scope(project, dict_scope_policy)  # 最终范围完整性证据。

    # 最终范围或治理比例失败时不允许写入治理文件。
    if not dict_final_verification.get("ok", False):

        # 原样返回最终验证错误。
        return dict_final_verification

    # 全绿报告明确 evidence_complete，避免 ok 单独被误读。
    return {
        **dict_index_result,
        "ok": True,
        "evidence_complete": True,
        "scope": dict_scope_result,
        "wal_baseline": dict_wal_baseline,
        "final_verification": dict_final_verification,
    }
