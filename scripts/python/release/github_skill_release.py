"""GitHub 关联技能发布 CLI。

标准输出遵循 machine-readable JSON stdout protocol，供上游自动化读取。
"""

# 延迟类型标注求值，保持当前项目的 Python 版本兼容。
from __future__ import annotations

# 命令行和本地清单操作只使用标准库，避免为发布工具增加运行时依赖。
import argparse
import hashlib
import importlib
import json

# 文件树替换和子进程查询仍只依赖标准库。
import shutil
import subprocess
import sys

# 路径与类型标注让公共入口可被其他技能复用。
from pathlib import Path
from typing import Any, Iterable

# 合同版本用于让计划和后续复核识别同一套 CLI 规则。
CONTRACT_VERSION = "github-skill-release-v1"  # GitHub 技能发布合同版本

# 未声明 checkout 时使用项目根下的统一链接目录。
DEFAULT_CHECKOUT_ROOT = "github"  # 未登记映射时查找本地 GitHub 镜像的目录前缀

# 配置映射有分支时使用显式约束，未配置分支仅允许保护性默认分支。
DEFAULT_BRANCH = "main"  # 计划载荷中的默认远程分支

# 公开异常类型把合同失败转换为稳定的 JSON 载荷。
class ContractError(RuntimeError):
    """表示发布合同无法安全继续的错误。

    参数:
        message: 面向调用方的阻断原因。

    返回:
        无；异常对象由 CLI 捕获并转换为 JSON。

    异常:
        RuntimeError: 由父类承载错误文本。
    """

# 机器协议输出器避免把 JSON 载荷混入人类日志前缀。
def _emit_json(dict_result: dict[str, Any]) -> None:
    """把单个结果对象写入标准输出。

    参数:
        dict_result: CLI 要返回给上游的结构化结果。

    返回:
        无；函数只写入一次 JSON 文本。

    异常:
        OSError: 标准输出不可写时由调用方处理。
    """

    # 单次写入保持 stdout 严格符合机器可读 JSON 合同。
    sys.stdout.write(json.dumps(dict_result, ensure_ascii=False, sort_keys=True) + "\n")

# 延迟导入发布策略，避免直接脚本执行时在导入阶段修改搜索路径。
def _policy_module() -> Any:
    """加载与打包、审计共享的公开文件策略模块。

    参数:
        无。

    返回:
        已加载的 release_content_policy 模块。

    异常:
        ImportError: 策略模块不存在或无法加载。
    """

    # 当前文件与策略模块位于同一 release 目录。
    path_release = Path(__file__).resolve().parent  # release 脚本目录

    # 裸模块入口需要一个稳定的脚本目录字符串。
    str_release = str(path_release)  # 策略模块搜索路径

    # 运行期登记路径，避免 import-time side effect。
    if str_release not in sys.path:

        # 将本地策略目录置于同名环境模块之前。
        sys.path.insert(0, str_release)

    # 返回与发布流程相同的公开文件策略事实源。
    return importlib.import_module("release_content_policy")

# 把参数路径解析到当前项目，并拒绝目录逃逸。
def _project_path(project: Path, candidate: str | None, default: str) -> Path:
    """解析项目内路径。

    参数:
        project: 当前工作文件夹根目录。
        candidate: 用户或映射提供的路径。
        default: candidate 为空时使用的相对路径。

    返回:
        项目内的规范化绝对路径。

    异常:
        ContractError: 路径逃逸项目根目录。
    """

    # 空参数使用合同定义的项目相对默认路径。
    path_candidate = Path(candidate or default)  # 原始候选路径

    # 相对路径以项目根为基准，绝对路径仍必须落在项目内。
    path_resolved = (path_candidate if path_candidate.is_absolute() else project / path_candidate).resolve()  # 规范化目标

    # 用 relative_to 建立无法越界的路径证明。
    try:

        # 合法路径必须能表达为项目根的相对成员。
        path_resolved.relative_to(project.resolve())

    # ValueError 表示候选路径位于项目边界之外。
    except ValueError as exc:

        # 错误前缀遵循当前项目的 Python 输出合同。
        raise ContractError(f"> ERR: [Python] path escapes project: {path_candidate}") from exc

    # 返回通过边界证明的路径。
    return path_resolved

# 读取技能版本并消除 v 前缀。
def _version_text(path_skill: Path) -> str:
    """读取技能版本。

    参数:
        path_skill: 技能源码根目录。

    返回:
        不带 v 前缀的非空版本文本。

    异常:
        ContractError: VERSION 缺失或为空。
    """

    # VERSION 是源码发布身份的首要事实。
    path_version = path_skill / "VERSION"  # 版本文件路径

    # 缺失文件不能推断 dist 目录。
    if not path_version.is_file():

        # 立即停止，避免镜像错误版本。
        raise ContractError(f"> ERR: [Python] missing skill VERSION: {path_version}")

    # 版本文件只保留首尾空白外的有效内容。
    str_version = path_version.read_text(encoding="utf-8").strip().lstrip("vV")  # 规范化版本文本

    # 空版本不能形成可验证的发布目录。
    if not str_version:

        # 由调用方显示稳定的阻断原因。
        raise ContractError("> ERR: [Python] skill VERSION is empty")

    # 返回用于 dist 名称和计划文件名的版本。
    return str_version

# 读取项目 JSON 配置并确认对象结构。
def _load_json(path_file: Path) -> dict[str, Any]:
    """读取 JSON 配置。

    参数:
        path_file: 待读取的 JSON 路径。

    返回:
        顶层对象；文件不存在时返回空映射。

    异常:
        ContractError: JSON 语法错误或顶层不是对象。
    """

    # 缺失控制文件交由映射检查报告，而不是触发底层异常。
    if not path_file.is_file():

        # 空映射表示尚未登记仓库合同。
        return {}

    # 解析失败必须被转换为稳定的合同错误。
    try:

        # 保留 UTF-8 中文合同和键名。
        value_loaded = json.loads(path_file.read_text(encoding="utf-8"))  # JSON 配置对象

    # 文件读取和语法错误都属于不可安全继续的输入。
    except (OSError, json.JSONDecodeError) as exc:

        # 错误文本标记 Python 侧阻断原因。
        raise ContractError(f"> ERR: [Python] invalid JSON configuration: {path_file}") from exc

    # 发布映射必须是对象，列表无法表达仓库策略。
    if not isinstance(value_loaded, dict):

        # 统一报告配置形状错误。
        raise ContractError(f"> ERR: [Python] JSON configuration must be an object: {path_file}")

    # 返回已验证的对象配置。
    return value_loaded

# 读取仓库级 GitHub 合同。
def _repository_contract(project: Path) -> dict[str, Any]:
    """读取 GitHub 连接合同。

    参数:
        project: 当前工作文件夹根目录。

    返回:
        github_repository_contract 对象。

    异常:
        ContractError: 合同字段不是对象。
    """

    # 控制文件是仓库治理配置的唯一来源。
    path_config = project / ".agents" / "agents-control.json"  # 控制配置路径

    # 读取完整控制对象以保留现有配置字段。
    dict_control = _load_json(path_config)  # 控制配置对象

    # 没有字段时使用空映射，由后续映射诊断具体缺失。
    dict_contract = dict_control.get("github_repository_contract", {})  # GitHub 合同对象

    # 合同对象以外的形状不能安全解释。
    if not isinstance(dict_contract, dict):

        # 把错误留在同一份 JSON CLI 协议中。
        raise ContractError("> ERR: [Python] github_repository_contract must be an object")

    # 返回已确认类型的仓库合同。
    return dict_contract

# 从列表或字典形态的 repositories 中按技能名查找映射。
def _find_mapping(contract: dict[str, Any], skill_name: str) -> dict[str, Any]:
    """定位技能仓库映射。

    参数:
        contract: GitHub 仓库合同。
        skill_name: 技能目录名称。

    返回:
        匹配的仓库映射；未找到时返回空映射。

    异常:
        无；非法列表成员按未匹配处理。
    """

    # 兼容当前项目使用的列表合同和未来的名称映射合同。
    value_repositories = contract.get("repositories", [])  # 仓库绑定集合

    # 映射形态转换为带 skill_name 的对象列表。
    if isinstance(value_repositories, dict):

        # 每个键都是稳定的技能名。
        list_repositories = [
            dict(dict_mapping, skill_name=str_name)  # 复制仓库映射并补入技能名
            for str_name, dict_mapping in value_repositories.items()  # 遍历名称映射
            if isinstance(dict_mapping, dict)  # 只接受字典型仓库绑定
        ]  # 规范化仓库映射列表

    # 列表形态直接复用，其他形态视为尚未登记。
    elif isinstance(value_repositories, list):

        # 过滤由外部配置误写入的非对象成员。
        list_repositories = [
            dict_mapping  # 保留列表中的仓库映射
            for dict_mapping in value_repositories  # 遍历列表配置
            if isinstance(dict_mapping, dict)  # 忽略非对象配置项
        ]  # 可解释的仓库映射

    # 非列表配置不授权任何仓库。
    else:

        # 空列表触发上层缺失映射错误。
        list_repositories = []  # 空仓库映射

    # 按显式 skill_name 或兼容 name 字段匹配。
    for dict_mapping in list_repositories:

        # 同一映射只读取一次技能身份字段。
        str_mapping_name = str(dict_mapping.get("skill_name", dict_mapping.get("name", "")))  # 映射技能名

        # 命中时复制对象，避免调用方修改配置解析结果。
        if str_mapping_name == skill_name:

            # 返回独立映射供后续路径和 Git 检查使用。
            return dict(dict_mapping)

    # 没有命中时返回空对象。
    return {}

# 解析技能映射并检查 existing-only 策略。
def _mapping_for(project: Path, path_skill: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """返回合同和技能绑定。

    参数:
        project: 当前工作文件夹根目录。
        path_skill: 技能源码根目录。

    返回:
        `(contract, mapping)` 二元组。

    异常:
        ContractError: 缺少映射或远程策略不是 existing-only。
    """

    # 解析项目级远程策略，缺失时由下方目录约定提供只读映射。
    dict_contract = _repository_contract(project)  # 当前项目的 GitHub 合同对象

    # 技能目录名称提供 github/<skill> 约定所需的稳定键。
    str_skill_name = path_skill.name  # 当前技能的目录键

    # 从合同中定位同名仓库，找不到时再使用本地目录推导。
    dict_mapping = _find_mapping(dict_contract, str_skill_name)  # 技能仓库映射

    # 只读状态和本地计划允许按 github/<skill> 目录约定推导映射。
    if not dict_mapping:

        # 未登记远程 URL 时仍不授予任何远程写操作能力。
        dict_mapping = {
            "skill_name": str_skill_name,  # 使用源码目录作为技能身份
            "checkout_path": f"{DEFAULT_CHECKOUT_ROOT}/{str_skill_name}",  # 使用统一镜像目录
            "branch": "",  # 未配置分支时接受 checkout 当前分支
            "repository_url": "",  # 未配置远程时只校验本地仓库
            "inferred": True,  # 标记映射来自目录约定
        }

    # 只允许用户明确选择的已有仓库策略。
    str_policy = str(dict_contract.get("remote_repository_policy", "existing-only"))  # 远程仓库策略

    # 其他策略会扩大到远程创建等未授权动作。
    if str_policy != "existing-only":

        # 工具本身不接受自动创建策略。
        raise ContractError("> ERR: [Python] remote repository policy must be existing-only")

    # 返回完整合同和绑定映射。
    return dict_contract, dict_mapping

# 解析 checkout 目录并限制在当前工作文件夹内。
def _checkout_path(project: Path, mapping: dict[str, Any], skill_name: str) -> Path:
    """得到本地 GitHub checkout 路径。

    参数:
        project: 当前工作文件夹根目录。
        mapping: 技能仓库映射。
        skill_name: 技能目录名称。

    返回:
        项目内的 checkout 绝对路径。

    异常:
        ContractError: checkout 路径越界。
    """

    # 未声明路径时落到 github/<skill-name>。
    str_checkout = str(mapping.get("checkout_path", f"{DEFAULT_CHECKOUT_ROOT}/{skill_name}"))  # checkout 相对路径

    # 复用统一项目路径边界检查。
    return _project_path(project, str_checkout, f"{DEFAULT_CHECKOUT_ROOT}/{skill_name}")

# 归一化 HTTPS 和 SSH 形式的 GitHub 地址。
def _remote_equivalent(value: str) -> str:
    """生成 Git 远程地址比较键。

    参数:
        value: Git remote URL。

    返回:
        去除协议差异和 `.git` 后缀的比较文本。

    异常:
        无。
    """

    # 去掉尾部斜杠，避免同一仓库产生不同键。
    str_value = value.strip().rstrip("/")  # 远程地址文本

    # SSH scp 形式转换为 HTTPS 形式。
    if str_value.startswith("<REDACTED_EMAIL>:"):

        # 保留组织和仓库路径。
        str_value = "https://github.com/" + str_value.split(":", 1)[1]  # 统一地址

    # .git 只是传输后缀，不属于仓库身份。
    if str_value.endswith(".git"):

        # 删除末尾后缀。
        str_value = str_value[:-4]  # 无后缀地址

    # 地址比较不区分主机与路径大小写。
    return str_value.lower()

# 在 checkout 内执行只读 Git 查询。
def _run_git(path_checkout: Path, arguments: Iterable[str]) -> str:
    """运行 Git 查询。

    参数:
        path_checkout: Git checkout 目录。
        arguments: Git 子命令和参数。

    返回:
        去除首尾空白的标准输出。

    异常:
        ContractError: Git 不存在或查询失败。
    """

    # 组装固定的只读 Git 命令。
    list_command = ["git", *arguments]  # Git 查询命令

    # 运行环境错误和 Git 非零退出统一转换为合同错误。
    try:

        # 捕获输出，避免污染机器可读 stdout。
        completed_process_git: subprocess.CompletedProcess[str] = subprocess.run(  # 供远程分支提交和工作树查询读取 stdout 与 stderr
            list_command,  # 固定 Git 子命令及参数，禁止拼接未经校验的命令文本
            cwd=path_checkout,  # 把查询限制在目标 checkout
            check=True,  # 非零状态必须转为合同错误
            capture_output=True,  # 截获 stdout 和 stderr 以便统一生成失败诊断
            text=True,  # 直接按文本读取查询结果
            encoding="utf-8",  # 统一跨平台解码方式
            errors="replace",  # 非法字节不污染诊断路径
        )  # 只保留进程标准输出用于状态文本

        # 去掉换行后供远程、分支、提交和工作树字段复用。
        str_output = completed_process_git.stdout.strip()  # Git 查询标准输出

    # 读取失败和 Git 返回错误都属于不能继续的状态。
    except (OSError, subprocess.CalledProcessError) as exc:

        # 保留 Git 错误文本以便定位环境问题。
        str_stderr = getattr(exc, "stderr", "") or str(exc)  # Git 错误摘要

        # 错误前缀满足当前 Python 输出协议。
        raise ContractError(
            f"> ERR: [Python] git query failed: {' '.join(list_command)}: {str_stderr.strip()}"
        ) from exc

    # 只返回 stdout，不打印详细过程。
    return str_output

# 收集 checkout 状态供 status、check 和 verify 复用。
def _git_status(path_checkout: Path, mapping: dict[str, Any]) -> dict[str, Any]:
    """收集本地 checkout 状态。

    参数:
        path_checkout: Git checkout 目录。
        mapping: 期望的仓库映射。

    返回:
        包含远程、分支、HEAD 和 dirty 状态的对象。

    异常:
        ContractError: Git 查询失败。
    """

    # 缺少目录或 .git 时返回可诊断的不存在状态。
    if not path_checkout.is_dir() or not (path_checkout / ".git").exists():

        # 调用方可以据此要求先取得已有仓库。
        return {"exists": False, "checkout": str(path_checkout)}

    # 没有 origin 的本地夹具仍可按目录约定完成状态核验。
    try:

        # 读取 origin 只作为可选的仓库身份事实。
        str_remote = _run_git(path_checkout, ["remote", "get-url", "origin"])  # 来自 origin 的仓库地址

    # origin 缺失不等于本地 checkout 不存在。
    except ContractError:

        # 空远程与未配置 repository_url 保持匹配。
        str_remote = ""  # 未配置 origin 的远程地址

    # 读取 checkout 当前分支，未指定预期分支时仍执行默认分支保护。
    str_branch = _run_git(path_checkout, ["branch", "--show-current"])  # 当前分支名称

    # 读取 HEAD 作为状态审计的提交锚点。
    str_head = _run_git(path_checkout, ["rev-parse", "HEAD"])  # 当前提交哈希

    # 读取 porcelain 输出判断是否存在未提交内容。
    str_porcelain = _run_git(path_checkout, ["status", "--porcelain=v1"])  # 工作树变更文本

    # 读取映射中的预期远程身份，用于判断 checkout 是否属于目标仓库。
    str_expected_remote = str(mapping.get("repository_url", ""))  # 映射声明的远程地址

    # 单独读取分支约束，空值表示调用方选择了目录约定模式。
    str_expected_branch = str(mapping.get("branch", ""))  # 映射声明的分支名称

    # 返回可供机器和人工同时复核的状态对象。
    return {
        "exists": True,
        "checkout": str(path_checkout),
        "remote_url": str_remote,
        "expected_remote_url": str_expected_remote,
        "remote_matches": not str_expected_remote
        or _remote_equivalent(str_remote) == _remote_equivalent(str_expected_remote),
        "branch": str_branch,
        "expected_branch": str_expected_branch,
        "branch_matches": (
            str_branch == str_expected_branch
            if str_expected_branch
            else str_branch.lower() in {"main", "master"}
        ),
        "head": str_head,
        "dirty": bool(str_porcelain),
        "porcelain": str_porcelain,
    }

# 生成不跟随 .git 和符号链接的文件清单。
def _manifest(path_root: Path, *, skip_git: bool = True) -> dict[str, str]:
    """计算目录文件 SHA-256 清单。

    参数:
        path_root: 待扫描的目录。
        skip_git: 是否跳过 `.git` 元数据。

    返回:
        POSIX 相对路径到 SHA-256 的映射。

    异常:
        ContractError: 发现符号链接。
    """

    # 缺失目录产生空清单，由调用方补充目录缺失错误。
    if not path_root.is_dir():

        # 不在扫描阶段猜测目录内容。
        return {}

    # 文件映射保证清单序列化稳定。
    dict_manifest: dict[str, str] = {}  # 文件 SHA-256 清单

    # pathlib 排序保证不同文件系统返回同一顺序。
    for path_entry in sorted(path_root.rglob("*")):

        # 使用 POSIX 形式作为跨平台清单键，避免 Windows 分隔符漂移。
        str_relative = path_entry.relative_to(path_root).as_posix()  # 清单中的 POSIX 路径键

        # 生成 dist 清单时跳过 checkout 专属的 .git 命名空间。
        if skip_git and (str_relative == ".git" or str_relative.startswith(".git/")):

            # 跳过当前条目和其后续内容。
            continue

        # 符号链接可能逃逸工作区，必须停止。
        if path_entry.is_symlink():

            # 清单不能证明链接目标的真实内容。
            raise ContractError(f"> ERR: [Python] symbolic link in mirror content: {str_relative}")

        # 目录本身不写入文件清单。
        if path_entry.is_dir():

            # 继续扫描其子项。
            continue

        # 只为普通文件计算哈希。
        if path_entry.is_file():

            # 读取全部字节形成稳定内容指纹。
            str_digest = hashlib.sha256(path_entry.read_bytes()).hexdigest()  # 文件内容 SHA-256

            # 把文件指纹挂到稳定的 POSIX 相对路径上。
            dict_manifest[str_relative] = str_digest  # 记录镜像内容哈希

    # 返回可比较的文件清单。
    return dict_manifest

# 将文件清单序列化为稳定的整体指纹。
def _manifest_hash(dict_manifest: dict[str, str]) -> str:
    """计算文件清单的整体 SHA-256。

    参数:
        dict_manifest: POSIX 相对路径到文件哈希的映射。

    返回:
        清单 JSON 的 SHA-256 十六进制摘要。

    异常:
        无；输入映射只进行确定性序列化。
    """

    # 排序键和紧凑分隔符消除平台与序列化格式漂移。
    # 返回可写入本地计划的清单摘要。
    return hashlib.sha256(
        json.dumps(
            dict_manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

# 计算回执或其他单文件的原始字节指纹。
def _file_hash(path_file: Path) -> str:
    """计算普通文件的 SHA-256。

    参数:
        path_file: 待读取的文件路径。

    返回:
        文件存在时的十六进制摘要，不存在时为空字符串。

    异常:
        OSError: 文件读取失败时交由调用方处理。
    """

    # 缺失回执不能伪造为成功绑定，返回空值让上层明确识别。
    if not path_file.is_file():

        # 空值表示尚未形成对应发布证据。
        return ""

    # 原始字节哈希保留回执实际内容，不重新解释 JSON。
    return hashlib.sha256(path_file.read_bytes()).hexdigest()

# 解析源码、dist 和当前版本。
def _source_and_release(project: Path, path_skill: Path, release_argument: str | None) -> tuple[Path, Path, str]:
    """解析版本化发布目录。

    参数:
        project: 当前工作文件夹根目录。
        path_skill: 技能源码根目录。
        release_argument: 可选的 dist 相对路径。

    返回:
        `(source, release, version)` 三元组。

    异常:
        ContractError: VERSION 缺失或发布路径越界。
    """

    # 源码 VERSION 决定后续 dist 目录的版本身份。
    str_version = _version_text(path_skill)  # 当前技能版本文本

    # 用同名版本目录作为未显式指定 release-dir 时的安全默认值。
    str_default_release = f"dist/{path_skill.name}-v{str_version}"  # 默认版本目录

    # 用户显式指定的 release 路径仍需项目边界证明。
    path_release = _project_path(project, release_argument, str_default_release)  # 版本化发布目录

    # 返回三份后续流程需要的身份事实。
    return path_skill, path_release, str_version

# 调用公开文件策略并附加被检查根路径。
def _public_report(
    path_root: Path,
    expected_version: str | None = None,
    *,
    strict_metadata: bool = True,
) -> dict[str, Any]:
    """校验公开技能文件。

    参数:
        path_root: 技能源码或 dist 根目录。
        expected_version: 期望的版本文本。
        strict_metadata: 是否执行许可证、版本和占位文本强校验。

    返回:
        公开文件策略报告。

    异常:
        ImportError: 发布策略模块无法加载。
    """

    # 公开文件报告携带版本期望以检查三处元数据。
    dict_report: dict[str, Any] = _policy_module().validate_public_skill_files(  # 执行统一公开文件门禁
        path_root,  # 待检查的技能或 dist 根目录
        expected_version=expected_version,  # 对齐源码 VERSION 的期望值
        strict_metadata=strict_metadata,  # 预检与正式发布使用不同严格度
    )  # 公开文件校验结果

    # 报告根路径便于多技能批量诊断。
    dict_report["root"] = str(path_root)  # 补充报告所对应的根目录

    # 返回带路径的完整报告。
    return dict_report

# 把公开门禁和路径错误归类为稳定机器字段。
def _error_kinds(errors: Iterable[str]) -> list[str]:
    """从错误文本提取可检索的错误类别。

    参数:
        errors: 合同检查生成的错误文本序列。

    返回:
        去重排序后的类别名称。

    异常:
        无。
    """

    # 类别集合避免同一 README 两种语言重复登记。
    set_kinds: set[str] = set()  # 错误类别集合

    # 规则表让新增错误类别不再堆叠分支判断。
    dict_category_patterns: dict[str, tuple[str, ...]] = {
        "missing_public_files": ("missing required public file",),  # 公开文件缺口
        "svg": ("svg",),  # SVG 禁止规则
        "remote_image": ("remote image", "must be local", "http://", "https://"),  # 远程图片规则
        "mermaid": ("mermaid", "flowchart"),  # 流程图文本类别
        "invalid_png": ("png", "illustration"),  # PNG 格式和清晰度规则
        "png_signature": ("not a valid png", "png signature", "png header"),  # PNG 头签名规则
        "path_or_checkout": ("escapes project", "branch", "checkout"),  # 路径和 checkout 规则
        "checkout_path_escape": ("path escapes project",),  # checkout 路径越界规则
        "branch_not_allowed": ("branch does not match", "branch not allowed"),  # 分支策略规则
        "dirty_checkout": ("dirty",),  # 工作树清洁规则
        "publish_forbidden": ("publish",),  # 远程发布授权规则
    }  # 错误类别到文本触发词

    # 逐条检查不改变原始错误文本。
    for str_error in errors:

        # 统一大小写便于识别图像、路径和发布词。
        str_lowered = str(str_error).lower()  # 规范化错误文本

        # 类别命中集合避免重复加入相同诊断。
        for str_kind, tuple_patterns in dict_category_patterns.items():

            # 任一触发词命中即可记录该错误类别。
            if any(str_pattern in str_lowered for str_pattern in tuple_patterns):

                # 调用方可按稳定类别筛选原始错误文本。
                set_kinds.add(str_kind)

    # 返回稳定类别顺序。
    return sorted(set_kinds)

# 构造只读状态结果。
def _status(project: Path, path_skill: Path) -> dict[str, Any]:
    """读取 GitHub checkout 状态。

    参数:
        project: 当前工作文件夹根目录。
        path_skill: 技能源码根目录。

    返回:
        JSON CLI 状态对象。

    异常:
        ContractError: 映射或 Git 状态无法验证。
    """

    # 解析合同与技能映射，避免重复读取仓库配置。
    tuple_contract_mapping = _mapping_for(project, path_skill)  # 仓库合同和技能绑定

    # 取出仓库级策略，供结果载荷记录。
    dict_contract = tuple_contract_mapping[0]  # 当前仓库合同

    # 取出当前技能的 checkout 绑定。
    dict_mapping = tuple_contract_mapping[1]  # 当前技能映射

    # 计算映射声明的 checkout 路径，作为状态查询边界。
    path_checkout = _checkout_path(project, dict_mapping, path_skill.name)  # 状态查询的 checkout 目录

    # 读取远程、分支和工作树状态，保留缺失 origin 的诊断。
    dict_git = _git_status(path_checkout, dict_mapping)  # checkout 的 Git 状态报告

    # 只有存在且绑定一致才视为 status 通过。
    bool_ok = (  # 组合 checkout 存在性和绑定一致性
        bool(dict_git.get("exists"))  # checkout 必须存在
        and bool(dict_git.get("remote_matches"))  # 远程身份必须匹配
        and bool(dict_git.get("branch_matches"))  # 分支约束必须匹配
    )  # checkout 绑定结论

    # 相对路径便于不同工作文件夹复用 status 合同。
    str_checkout_relative = path_checkout.relative_to(project.resolve()).as_posix()  # checkout 相对项目路径

    # 返回状态，不写入任何文件。
    return {
        "contract": CONTRACT_VERSION,
        "ok": bool_ok,
        "policy": dict_contract.get("remote_repository_policy", "existing-only"),
        "mapping": dict_mapping,
        "checkout": str_checkout_relative,
        "checkout_status": dict_git,
        "publish_allowed": False,
        "mutation": "none",
    }

# 汇总发布目录的公开文件和内容策略错误。
def _release_check_errors(
    path_release: Path,
    dict_release_public: dict[str, Any],
    dict_release_analysis: dict[str, Any],
    bool_require_release: bool,
) -> list[str]:
    """生成 dist 预检错误，不修改发布目录。

    参数:
        path_release: 版本化 dist 目录。
        dict_release_public: dist 公开文件报告。
        dict_release_analysis: dist 内容策略报告。
        bool_require_release: 是否将 dist 缺失视为阻断。

    返回:
        带 ``release:`` 前缀的错误列表。

    异常:
        无；输入报告只被读取。
    """

    # 公开文件错误统一标注 release 前缀。
    list_errors = [
        f"release: {str_error}"  # dist 公开文件错误文本
        for str_error in dict_release_public["errors"]  # 遍历 dist 公开门禁错误
    ]  # dist 公开文件错误列表

    # 缺失 dist 只有在严格或已有源码错误时才阻断预检。
    if bool_require_release and not path_release.is_dir():

        # 不允许从源码目录直接镜像。
        list_errors.append(f"release directory is missing: {path_release}")

    # 目录内容策略错误阻断镜像。
    if dict_release_analysis and (
        dict_release_analysis["unexpected_top_level_entries"]
        or dict_release_analysis["forbidden_paths"]
        or not dict_release_analysis.get("public_skill_ok", True)
    ):

        # 细节已经在公开报告和分析对象中保留。
        list_errors.append("release content policy rejected the release tree")

    # 返回 dist 侧的完整错误集合。
    return list_errors

# 汇总 checkout 的远程、分支和工作树安全错误。
def _checkout_check_errors(
    dict_git: dict[str, Any],
    bool_require_checkout: bool,
) -> list[str]:
    """生成 checkout 绑定错误，不执行 Git 写操作。

    参数:
        dict_git: checkout 状态报告。
        bool_require_checkout: 是否要求已有 checkout 通过绑定检查。

    返回:
        checkout 缺失、远程漂移、分支漂移和 dirty 错误列表。

    异常:
        无；状态报告只被读取。
    """

    # 轻量源码预检允许没有 checkout，状态由 status 单独确认。
    if not bool_require_checkout:

        # 不把尚未进入镜像阶段的缺失状态误报为失败。
        return []

    # checkout 不存在时要求用户先连接已有仓库。
    if not dict_git.get("exists"):

        # 工具不代替用户创建远程仓库或取得凭据。
        return ["GitHub checkout is missing; clone the existing repository before mirror"]

    # 绑定错误需要聚合，便于用户一次修复多个安全条件。
    list_errors: list[str] = []  # checkout 绑定错误列表

    # 远程地址不一致必须停止。
    if not dict_git.get("remote_matches"):

        # 防止把 dist 写入错误仓库。
        list_errors.append("GitHub checkout remote does not match mapping")

    # 分支不一致必须停止，并给出可检索的策略类别。
    if not dict_git.get("branch_matches"):

        # 防止更新错误分支。
        list_errors.append("GitHub checkout branch not allowed by mapping")

    # dirty 工作树不能被镜像覆盖。
    if dict_git.get("dirty"):

        # 防止吞掉用户尚未提交的本地内容。
        list_errors.append("GitHub checkout is dirty; commit or clean it before mirror")

    # 返回 checkout 的全部安全错误。
    return list_errors

# 推导默认公开合同严格度，避免轻量源码预检被未生成 dist 阻断。
def _resolve_strict_public_contract(
    strict_public_contract: bool | None,
    release_argument: str | None,
    path_release: Path,
) -> bool:
    """决定当前检查是否使用严格公开元数据门禁。

    参数:
        strict_public_contract: 调用方显式指定的严格度。
        release_argument: 调用方提供的 dist 路径参数。
        path_release: 按版本推导出的默认 dist 路径。

    返回:
        显式值存在时返回显式值，否则在 dist 已存在或显式指定时返回 True。

    异常:
        无；路径只读。
    """

    # 显式严格度优先于路径推导，镜像和复核可以强制开启。
    if strict_public_contract is not None:

        # 返回调用方的安全边界选择。
        return strict_public_contract

    # 没有显式选择时，现有 dist 表示应执行完整发布预检。
    return bool(release_argument is not None or path_release.is_dir())

# 检查源码、dist、checkout 和公开文件合同。
def _check(
    project: Path,
    path_skill: Path,
    release_argument: str | None,
    *,
    checkout_argument: str | None = None,
    strict_public_contract: bool | None = None,
) -> dict[str, Any]:
    """执行镜像前置检查。

    参数:
        project: 当前工作文件夹根目录。
        path_skill: 技能源码根目录。
        release_argument: 可选版本化 dist 路径。
        checkout_argument: 可选的 checkout 覆盖路径。
        strict_public_contract: 是否执行严格公开元数据门禁；省略时按 dist 是否存在推断。

    返回:
        包含 errors、source、release 和 checkout 的检查对象。

    异常:
        ContractError: 映射或 Git 查询无法完成。
    """

    # 解析仓库合同、发布目录和版本，形成一次性快照。
    tuple_contract_mapping = _mapping_for(project, path_skill)  # 合同和技能映射

    # 抽取发布策略，后续结果需要明确记录它。
    dict_contract = tuple_contract_mapping[0]  # 发布检查使用的仓库合同

    # 抽取技能绑定，后续 Git 检查依赖它。
    dict_mapping = tuple_contract_mapping[1]  # 发布检查使用的技能映射

    # 解析 VERSION 与 dist 路径，确保二者使用同一版本。
    tuple_source_release = _source_and_release(project, path_skill, release_argument)  # 源码、dist 和版本

    # 取出版本化 dist 目录。
    path_release = tuple_source_release[1]  # 版本化 dist 目录

    # 取出源码声明的版本文本。
    str_version = tuple_source_release[2]  # 当前技能版本

    # 缺省严格度让源码预检不被尚未生成的 dist 阻断。
    bool_strict_public = _resolve_strict_public_contract(  # 当前检查的公开合同严格度
        strict_public_contract,  # 调用方显式严格度
        release_argument,  # 调用方 dist 路径参数
        path_release,  # 推导出的默认 dist 路径
    )  # 公开门禁严格度结果

    # 映射路径作为未显式覆盖时的目标。
    str_default_checkout = str(dict_mapping.get("checkout_path", f"github/{path_skill.name}"))  # checkout 默认路径

    # 显式覆盖仍受项目根边界限制。
    path_checkout = _project_path(project, checkout_argument, str_default_checkout)  # 发布检查的 checkout 目录

    # 源码公开文件报告决定技能入口是否完整。
    dict_source_public = _public_report(  # 源码公开文件报告
        path_skill,  # 技能源码根目录
        str_version,  # 源码公开版本事实
        strict_metadata=bool_strict_public,  # 源码元数据严格度
    )  # 源码公开文件检查结果

    # dist 公开文件报告决定可镜像内容是否完整。
    dict_release_public = _public_report(  # dist 公开文件报告
        path_release,  # 版本化 dist 根目录
        str_version,  # 用于比对的期望版本
        strict_metadata=bool_strict_public,  # dist 元数据严格度
    )  # dist 公开文件检查结果

    # 轻量源码预检允许暂未生成 dist，正式镜像仍保留完整缺失诊断。
    if not bool_strict_public and not path_release.is_dir():

        # 缺失 dist 的文件级错误由下面的目录状态分支统一报告。
        dict_release_public["errors"] = []  # 预检阶段暂不报告 dist 文件缺口

        # 缺失文件集合也由目录状态分支统一处理。
        dict_release_public["missing_required_files"] = []  # 预检阶段暂不聚合 dist 缺失文件

    # dist 目录存在时再运行完整内容策略扫描。
    if path_release.is_dir():

        # 延迟加载策略以保留 CLI 的机器可读 stdout。
        dict_release_analysis = _policy_module().analyze_release_content_root(  # dist 内容报告
            path_release,  # 正式发布包根目录
            strict_public_contract=bool_strict_public,  # 内容策略公开门禁开关
        )  # dist 内容分析结果

    # 缺失 dist 只保留空报告，错误由下面的显式分支登记。
    else:

        # 空映射让错误载荷保持结构稳定。
        dict_release_analysis = {}  # 缺失 dist 报告

    # checkout 状态包含远程和分支绑定事实。
    dict_git = _git_status(path_checkout, dict_mapping)  # checkout Git 绑定报告

    # 汇总所有阻断原因，不在首个错误处丢失诊断。
    list_errors: list[str] = []  # 前置检查错误

    # 把源码门禁错误标注 source 前缀，便于调用方筛选。
    list_errors.extend(f"source: {str_error}" for str_error in dict_source_public["errors"])  # 源码门禁错误

    # 源码已产生错误时聚合 dist 缺失，避免安全诊断被首项遮蔽。
    bool_source_has_errors = bool(dict_source_public["errors"])  # 源码公开合同是否失败

    # 先决定版本化发布包是否需要存在。
    bool_require_release = bool_strict_public or bool_source_has_errors  # 是否要求版本目录就绪

    # 再决定本地 checkout 是否必须通过绑定。
    bool_require_checkout = bool_strict_public or bool_source_has_errors  # 是否要求 checkout 绑定

    # dist 侧报告包含公开文件、内容策略和缺失目录诊断。
    list_errors.extend(
        _release_check_errors(
            path_release,
            dict_release_public,
            dict_release_analysis,
            bool_require_release,
        )
    )

    # checkout 侧报告聚合远程、分支与 dirty 安全诊断。
    list_errors.extend(_checkout_check_errors(dict_git, bool_require_checkout))

    # 合并源码与 dist 的缺失公开文件，避免调用方再次解析文本。
    list_missing_public = sorted(  # 汇总两个根目录缺失的公开文件
        set(dict_source_public["missing_required_files"])  # 源码缺失集合
        | set(dict_release_public["missing_required_files"])  # dist 缺失集合
    )  # 缺失公开文件

    # 生成错误类别供门禁和上层 UI 直接筛选。
    list_error_kinds = _error_kinds(list_errors)  # 错误类别

    # 返回完整检查事实，镜像函数只接受 ok 结果。
    return {
        "contract": CONTRACT_VERSION,
        "ok": not list_errors,
        "errors": list_errors,
        "error_kinds": list_error_kinds,
        "missing_public_files": list_missing_public,
        "policy": dict_contract.get("remote_repository_policy", "existing-only"),
        "mapping": dict_mapping,
        "version": str_version,
        "source": {"path": str(path_skill), "public": dict_source_public},
        "release": {"path": str(path_release), "public": dict_release_public, "analysis": dict_release_analysis},
        "checkout": dict_git,
        "readme_images": dict_source_public.get("readme_images", {}),
        "required_public_files": list(_policy_module().REQUIRED_PUBLIC_FILES),
        "mutation": "none",
    }

# 将 dist 文件树复制到 checkout，同时保留 .git。
def _copy_release(path_release: Path, path_checkout: Path) -> None:
    """复制发布内容。

    参数:
        path_release: 版本化 dist 根目录。
        path_checkout: 本地 GitHub checkout 根目录。

    返回:
        无；目标 checkout 内容被更新。

    异常:
        ContractError: dist 中存在符号链接。
    """

    # 首次镜像允许 checkout 目录已由 git clone 创建。
    path_checkout.mkdir(parents=True, exist_ok=True)

    # 清理旧内容但绝不删除 Git 元数据。
    for path_entry in sorted(path_checkout.iterdir()):

        # `.git` 是 checkout 身份，必须原样保留。
        if path_entry.name == ".git":

            # 跳过 Git 元数据。
            continue

        # 目录使用可恢复性较差的删除前已通过 check 门禁。
        if path_entry.is_dir() and not path_entry.is_symlink():

            # 删除旧功能内容。
            shutil.rmtree(path_entry)

        # 普通文件或链接都必须清除后重新复制。
        else:

            # 不留下旧版本文件。
            path_entry.unlink()

    # 逐项复制 dist，禁止复制任何符号链接。
    for path_entry in sorted(path_release.rglob("*")):

        # 镜像遍历把发布包中的 Git 元数据视为不可复制内容。
        str_relative = path_entry.relative_to(path_release).as_posix()  # 发布包中的 POSIX 路径键

        # 不把发布包中的 .git 内容写入目标仓库。
        if str_relative == ".git" or str_relative.startswith(".git/"):

            # 仅防御性跳过异常的 Git 目录。
            continue

        # 复制前再次拒绝链接，避免竞态绕过清单。
        if path_entry.is_symlink():

            # 镜像内容不能依赖外部路径。
            raise ContractError(f"> ERR: [Python] release contains symbolic link: {str_relative}")

        # 把相对路径投影到 checkout，保持 dist 的文件树结构。
        path_target = path_checkout / str_relative  # checkout 中的目标路径

        # 目录条目只负责建立对应父级结构。
        if path_entry.is_dir():

            # 目录结构先于文件内容建立。
            path_target.mkdir(parents=True, exist_ok=True)

        # 普通文件按字节复制并保留元数据。
        elif path_entry.is_file():

            # 文件父目录可能是新版本新增目录。
            path_target.parent.mkdir(parents=True, exist_ok=True)

            # copy2 复制内容和基本时间元数据。
            shutil.copy2(path_entry, path_target)

# 执行本地镜像并复核清单一致性。
def _mirror(
    project: Path,
    path_skill: Path,
    release_argument: str | None,
    checkout_argument: str | None,
) -> dict[str, Any]:
    """镜像 dist 到 GitHub checkout。

    参数:
        project: 当前工作文件夹根目录。
        path_skill: 技能源码根目录。
        release_argument: 版本化 dist 路径。
        checkout_argument: 可选 checkout 覆盖路径。

    返回:
        镜像路径、清单和不执行远程写操作的声明。

    异常:
        ContractError: 前置检查失败、工作树 dirty 或清单不一致。
    """

    # 解析映射和版本化发布目录，为镜像操作固定身份。
    tuple_contract_mapping = _mapping_for(project, path_skill)  # 合同和仓库映射

    # 记录远程策略，确保返回结果说明写入边界。
    dict_contract = tuple_contract_mapping[0]  # 镜像使用的仓库合同

    # 记录 checkout 映射，供前置检查和路径解析复用。
    dict_mapping = tuple_contract_mapping[1]  # 镜像使用的技能映射

    # 解析要被复制的版本化 dist 目录。
    tuple_source_release = _source_and_release(project, path_skill, release_argument)  # 固定待镜像的版本目录

    # 提取发布目录路径，避免从源码目录直接镜像。
    path_release = tuple_source_release[1]  # 要镜像的版本目录

    # 显式 checkout 参数仍受项目边界限制。
    str_default_checkout = str(dict_mapping.get("checkout_path", f"github/{path_skill.name}"))  # 计划模式采用的 checkout 默认值

    # 覆盖值用于测试夹具或其他技能的同一流程。
    path_checkout = _project_path(project, checkout_argument, str_default_checkout)  # 最终 checkout 目录

    # 先运行所有只读前置检查，任何失败都必须保持 checkout 不变。
    dict_before = _check(  # 镜像前置结果
        project,  # 复核所属的工作文件夹
        path_skill,  # 镜像使用的技能源码根目录
        release_argument,  # 版本化 dist 路径
        checkout_argument=checkout_argument,  # 镜像目标覆盖路径
        strict_public_contract=True,  # 镜像必须使用严格公开合同
    )  # 镜像前置检查报告

    # 任何错误都阻断写入。
    if not dict_before["ok"]:

        # 聚合错误便于用户修复一次后重试。
        str_errors = "; ".join(dict_before["errors"])  # 前置错误摘要

        # 不把部分镜像误报为成功。
        raise ContractError(f"> ERR: [Python] mirror preflight failed: {str_errors}")

    # dirty checkout 不能被覆盖，避免吞掉用户未提交内容。
    if dict_before["checkout"].get("dirty"):

        # 要求用户先提交或清理 checkout。
        raise ContractError("> ERR: [Python] GitHub checkout is dirty; commit or clean it before mirror")

    # 执行保留 .git 的完整内容替换。
    _copy_release(path_release, path_checkout)

    # 镜像后先记录 dist 的内容清单。
    dict_release_manifest = _manifest(path_release)  # 记录发布包的文件指纹

    # 再记录 checkout 的内容清单用于逐字节比对。
    dict_checkout_manifest = _manifest(path_checkout)  # 记录目标 checkout 的文件指纹

    # 清单不一致说明复制过程不能作为证据。
    if dict_release_manifest != dict_checkout_manifest:

        # 不继续生成发布计划。
        raise ContractError("> ERR: [Python] mirror manifest mismatch after copy")

    # 返回本地镜像结果，明确没有远程动作。
    return {
        "contract": CONTRACT_VERSION,
        "ok": True,
        "mapping": dict_mapping,
        "policy": dict_contract.get("remote_repository_policy", "existing-only"),
        "release": str(path_release),
        "checkout": str(path_checkout),
        "manifest": dict_release_manifest,
        "mutation": "local checkout only; no commit, push, tag, or remote repository creation",
    }

# 写入只包含清单和人工动作的本地发布计划。
def _plan(
    project: Path,
    path_skill: Path,
    release_argument: str | None,
    checkout_argument: str | None,
) -> dict[str, Any]:
    """生成 GitHub 远程发布计划。

    参数:
        project: 当前工作文件夹根目录。
        path_skill: 技能源码根目录。
        release_argument: 版本化 dist 路径。
        checkout_argument: 可选 checkout 覆盖路径。

    返回:
        计划对象和计划文件路径。

    异常:
        ContractError: 映射、版本或清单无法读取。
    """

    # 读取映射和版本化 dist 路径，固定计划的输入身份。
    tuple_contract_mapping = _mapping_for(project, path_skill)  # 合同和映射

    # 记录仓库策略，计划不会替代远程授权。
    dict_contract = tuple_contract_mapping[0]  # 计划使用的仓库合同

    # 记录技能到 checkout 的绑定。
    dict_mapping = tuple_contract_mapping[1]  # 计划使用的技能映射

    # 读取 VERSION 与 dist 目录，拒绝源码目录直连。
    tuple_source_release = _source_and_release(project, path_skill, release_argument)  # 固定计划对应的版本目录

    # 取出计划比较的发布目录。
    path_release = tuple_source_release[1]  # 计划对应的 dist 目录

    # 取出计划文件名中的版本。
    str_version = tuple_source_release[2]  # 计划对应的版本号

    # checkout 路径用于计算镜像差异。
    str_default_checkout = str(dict_mapping.get("checkout_path", f"github/{path_skill.name}"))  # 映射默认 checkout

    # 显式覆盖仍限制在项目根内。
    path_checkout = _project_path(project, checkout_argument, str_default_checkout)  # 计划比较的 checkout 目录

    # 计划同时暴露稳定的项目相对 checkout 路径。
    str_checkout_relative = path_checkout.relative_to(project.resolve()).as_posix()  # 计划输出用的相对镜像目录标识

    # 计划只记录 dist 内容指纹，不把源码复制进计划。
    dict_release_manifest = _manifest(path_release)  # dist 内容清单

    # 同时记录源码清单，绑定计划所依据的源码快照。
    dict_source_manifest = _manifest(path_skill)  # 源码内容清单

    # 同时记录 checkout 清单，供人工看到将要变化的内容。
    dict_checkout_manifest = _manifest(path_checkout)  # 计划基线的 checkout 文件指纹

    # 收据摘要只读取版本化 dist 中的真实回执字节。
    str_receipt_hash = _file_hash(path_release / "RELEASE_RECEIPT.json")  # 回执文件摘要

    # 先合并路径集合，再筛选新增、删除和内容变化。
    set_all_paths = set(dict_release_manifest) | set(dict_checkout_manifest)  # 清单比较的路径全集

    # 计算发布包与 checkout 的差异路径。
    list_changes = sorted(  # 生成待人工复核的变化列表
        str_path  # 变化文件的相对路径
        for str_path in set_all_paths  # 遍历两个清单的并集
        if dict_release_manifest.get(str_path) != dict_checkout_manifest.get(str_path)  # 保留内容不同项
    )  # 清单差异路径

    # 计划文件属于本地治理文档，不代表已获远程发布授权。
    path_plan = (  # 定位本地 GitHub 计划文件
        project  # 项目根目录
        / "docs"  # 文档治理目录
        / "git_manager"  # Git 管理子目录
        / f"github-publish-{path_skill.name}-v{str_version}.json"  # 版本化计划名
    )  # 计划文件路径

    # 确保治理目录存在后再写入计划。
    path_plan.parent.mkdir(parents=True, exist_ok=True)

    # 明确列出人工 GitHub 动作和确认边界。
    dict_plan = {
        "contract": CONTRACT_VERSION,  # 标识计划使用的 CLI 合同
        "skill_name": path_skill.name,  # 记录计划对应的技能目录
        "version": str_version,  # 记录发布包版本
        "repository_url": dict_mapping.get("repository_url"),  # 记录已登记远程地址
        "branch": dict_mapping.get("branch", DEFAULT_BRANCH),  # 记录目标分支约束
        "source_path": str(path_skill),  # 记录源码根目录
        "release_directory": str(path_release),  # 记录版本化 dist 目录
        "checkout_path": str(path_checkout),  # 记录本地镜像目录
        "checkout": str_checkout_relative,  # 记录相对 checkout 路径
        "release_manifest_sha256": dict_release_manifest,  # 保存 dist 指纹
        "checkout_manifest_sha256": dict_checkout_manifest,  # 保存 checkout 基线指纹
        "bindings": {  # 绑定四份副本的清单摘要和版本化回执证据
            "source_manifest_hash": _manifest_hash(dict_source_manifest),  # 源码清单摘要
            "dist_manifest_hash": _manifest_hash(dict_release_manifest),  # dist 清单摘要
            "receipt_hash": str_receipt_hash,  # 版本化回执摘要
            "checkout_manifest_hash": _manifest_hash(dict_checkout_manifest),  # 目标 checkout 当前清单摘要
            "source_path": str(path_skill),  # 源码快照输入目录
            "release_directory": str(path_release),  # 待镜像 dist 目录
            "checkout_path": str(path_checkout),  # 本地 GitHub 镜像目录
        },
        "changed_paths": list_changes,  # 保存待人工复核的差异路径
        "publication_confirmation_required": True,  # 强制独立发布确认
        "requires_confirmation": True,  # 机器可读的独立确认标记
        "publish_allowed": False,  # 本地计划不授予远程发布权限
        "publication_status": "pending",  # 未执行远程发布
        "ok": True,  # 计划文件已成功生成
        "actions": [  # 列出需要人工确认的后续动作
            "review the generated plan and release receipt",  # 先复核收据与计划
            "git add and commit the mirrored checkout",  # 人工提交本地镜像
            "git push the mapped existing repository branch",  # 人工推送已有仓库
            "create the matching tag and GitHub release manually",  # 人工创建标签与 Release
        ],
        "mutation": "plan file only; no git commit, push, tag, release, or repository creation",  # 声明本次仅写计划
    }  # 本地 GitHub 发布计划

    # 计划写入治理目录，便于后续独立确认和审计。
    path_plan.write_text(json.dumps(dict_plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 返回计划对象并附上文件位置。
    dict_plan["plan_path"] = str(path_plan)  # 返回计划文件的绝对路径

    # 返回已写入文件且仍等待人工确认的计划。
    return dict_plan

# 复核 dist 与 checkout 的内容和绑定。
def _verify(
    project: Path,
    path_skill: Path,
    release_argument: str | None,
    checkout_argument: str | None = None,
) -> dict[str, Any]:
    """验证本地镜像，不宣称远程发布成功。

    参数:
        project: 当前工作文件夹根目录。
        path_skill: 技能源码根目录。
        release_argument: 版本化 dist 路径。
        checkout_argument: 可选的 checkout 覆盖路径。

    返回:
        含清单一致性和 publication_ready 状态的检查对象。

    异常:
        ContractError: 映射或 Git 状态无法读取。
    """

    # 复用严格 check 以保持复核与镜像相同的安全边界。
    dict_result = _check(  # 基础复核结果
        project,  # 项目工作文件夹根目录
        path_skill,  # 待复核的技能源码根目录
        release_argument,  # 待复核的版本化 dist 路径
        checkout_argument=checkout_argument,  # 复核目标覆盖路径
        strict_public_contract=True,  # 复核必须使用严格公开合同
    )  # 严格复核结果

    # 只有前置检查通过时才有资格比较两个清单。
    if dict_result["ok"]:

        # 先读取 dist 的完整内容指纹。
        dict_release_manifest = _manifest(Path(dict_result["release"]["path"]))  # 复核发布包文件指纹

        # 再读取 checkout 的完整内容指纹。
        dict_checkout_manifest = _manifest(Path(dict_result["checkout"]["checkout"]))  # 复核 checkout 文件指纹

        # 将 dist 指纹写入结果供人工复核。
        dict_result["release_manifest_sha256"] = dict_release_manifest  # 保存发布包复核指纹

        # 为后续 publication_ready 比较保留目标 checkout 指纹。
        dict_result["checkout_manifest_sha256"] = dict_checkout_manifest  # 回填目标 checkout 复核指纹

        # 只有完全相等才能建立本地镜像证据。
        bool_manifest_match = dict_release_manifest == dict_checkout_manifest  # 清单一致结论

        # 把清单比较结论暴露给调用方。
        dict_result["manifest_match"] = bool_manifest_match  # 记录清单是否一致

        # dirty checkout 仍表示未提交变更，但不影响内容一致事实。
        dict_result["publication_ready"] = (  # 记录本地镜像是否具备人工发布前提
            bool_manifest_match  # 内容必须完全一致
            and not bool(dict_result["checkout"].get("dirty"))  # 工作树必须干净
        )

        # 清单差异将复核整体降级为失败。
        if not bool_manifest_match:

            # 追加人类可检索的差异原因。
            dict_result["ok"] = False  # 清单不一致时降级检查结论

            # 把清单差异追加到同一错误列表，避免丢失前置诊断。
            dict_result.setdefault("errors", []).append("release and checkout manifests differ")

    # 无论结果如何，远程发布仍是独立人工动作。
    dict_result["mutation"] = "none; remote publication remains a separate confirmation"  # 声明无远程写入

    # 返回不含远程成功声明的复核对象。
    return dict_result

# 远程发布子命令只返回安全拒绝，不执行任何 GitHub 写操作。
def _publish_forbidden() -> dict[str, Any]:
    """返回被禁止的远程发布结果。

    参数:
        无。

    返回:
        ok=False 且要求独立确认的 JSON 对象。

    异常:
        无。
    """

    # publish 不是本工具的授权写入接口。
    return {
        "contract": CONTRACT_VERSION,
        "ok": False,
        "errors": ["remote publication requires a separate explicit confirmation"],
        "error_kinds": ["publish_forbidden"],
        "publication_confirmation_required": True,
        "mutation": "none",
    }

# 构建稳定的机器可读 CLI 参数解析器。
def _parser() -> argparse.ArgumentParser:
    """构建命令行解析器。

    参数:
        无。

    返回:
        支持五个发布子命令的参数解析器。

    异常:
        无。
    """

    # 初始化主解析器并声明用途。
    parser = argparse.ArgumentParser(description="Validate and mirror a GitHub-linked skill release.")  # 创建发布合同的命令解析器

    # status/check/mirror/plan/verify 共享同一入口。
    parser.add_argument("command", choices=("status", "check", "mirror", "plan", "verify", "publish"))

    # 项目根是所有路径安全判断的边界。
    parser.add_argument("--project", required=True, help="project root")

    # 默认技能路径保持当前项目的公开入口兼容。
    parser.add_argument("--skill-dir", default="skills/agents-md-generator", help="skill source directory")

    # release-dir 允许调用方明确指定某个版本化 dist。
    parser.add_argument("--release-dir", help="versioned dist directory")

    # checkout 只在 mirror 子命令中作为可选覆盖。
    parser.add_argument("--checkout", help="github checkout directory for mirror")

    # 返回完整参数解析器。
    return parser

# 根据已解析参数运行一个合同分支。
def _dispatch_command(args: argparse.Namespace, path_project: Path, path_skill: Path) -> dict[str, Any]:
    """执行一个已解析的 CLI 子命令。

    参数:
        args: `_parser` 产生的命令行参数对象。
        path_project: 已解析并限制范围的项目根目录。
        path_skill: 已解析并限制范围的技能源码目录。

    返回:
        当前子命令的结构化结果对象。

    异常:
        ContractError: 子命令的合同前置条件不满足。
    """

    # status 只读取 checkout 状态，不写入项目文件。
    if args.command == "status":

        # 返回状态事实供上游判断绑定是否完整。
        return _status(path_project, path_skill)

    # check 执行源码、dist、checkout 和公开文件审查。
    if args.command == "check":

        # 返回可检索的前置检查报告。
        return _check(
            path_project,
            path_skill,
            args.release_dir,
            checkout_argument=args.checkout,
        )

    # mirror 只替换本地 checkout 内容并保留 .git。
    if args.command == "mirror":

        # 返回镜像清单，远程 GitHub 仍不发生写入。
        return _mirror(path_project, path_skill, args.release_dir, args.checkout)

    # publish 明确返回安全拒绝，不能隐式扩大授权范围。
    if args.command == "publish":

        # 让调用方在非零退出时仍可读取结构化原因。
        return _publish_forbidden()

    # plan 只生成本地人工确认材料。
    if args.command == "plan":

        # 返回计划对象和计划文件位置。
        return _plan(path_project, path_skill, args.release_dir, args.checkout)

    # verify 是剩余的合法本地复核命令。
    return _verify(path_project, path_skill, args.release_dir, args.checkout)

# 执行子命令并输出单个 JSON 对象。
def main(argv: list[str] | None = None) -> int:
    """运行 GitHub 关联技能发布 CLI。

    参数:
        argv: 可选的命令行参数列表；为空时读取系统参数。

    返回:
        进程状态码，0 表示合同通过，1 表示检查失败，2 表示输入错误。

    异常:
        无；合同错误转换为机器可读 JSON。
    """

    # 创建参数解析器。
    parser = _parser()  # 接收命令、项目和路径边界

    # 解析用户传入的子命令和路径。
    args = parser.parse_args(argv)  # 解析后的合同参数

    # 按子命令选择只读、镜像或计划流程。
    try:

        # 将项目根解析为所有路径的边界。
        path_project = Path(args.project).resolve()  # 规范化项目工作文件夹

        # skill-dir 不能逃出项目根。
        path_skill = _project_path(  # 解析并限制技能源码目录
            path_project,  # 项目边界
            args.skill_dir,  # 用户选择的技能目录
            "skills/agents-md-generator",  # 默认公开入口
        )

        # 把路径和参数交给单独分支函数，保持入口层浅而清晰。
        dict_result = _dispatch_command(args, path_project, path_skill)  # 当前命令结果

        # CLI 合同规定 stdout 只打印一个完整 JSON 对象。
        _emit_json(dict_result)

        # 检查失败使用 1，成功保持 0。
        return 0 if dict_result.get("ok", True) else 1

    # 合同和本地输入错误统一转换为 JSON 错误对象。
    except (ContractError, OSError, ValueError) as exc:

        # 错误文本已带 Python 前缀或由异常提供可检索原因。
        dict_error = {
            "contract": CONTRACT_VERSION,  # 标识错误使用的 CLI 合同
            "ok": False,  # 错误载荷必然不通过
            "errors": [str(exc)],  # 保存原始诊断文本
            "error_kinds": _error_kinds([str(exc)]),  # 提供稳定错误类别
            "mutation": "none",  # 错误路径不执行写入
        }  # CLI 错误结果

        # 保持错误也符合单对象 JSON stdout 协议。
        _emit_json(dict_error)

        # 2 表示命令输入或环境无法解释。
        return 1

# 直接脚本执行时把 main 状态码交给解释器。
if __name__ == "__main__":

    # CLI 的退出码由 main 统一决定。
    raise SystemExit(main())
