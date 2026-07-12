"""执行 release 准备、打包、内容策略校验和发布治理检查。"""

# 延迟解析类型注解，避免运行期依赖顺序影响 shard 装载。
from __future__ import annotations

# 标准库路径模型和共享基础设施共同支撑发布策略计算。
from pathlib import Path

# 兄弟任务模块由入口脚本预先加入搜索路径，本模块只声明 release 依赖。
from manage_docs_shared import (
    Any,
    IGNORED_RUNTIME_GIT_PATHS,
    datetime,
    display_path,
    docs_governance_initialized,
)

# 摘要、JSON 与正则能力用于构建可复核的发布证据。
from manage_docs_shared import (
    hashlib,
    json,
    re,
)

# 文件复制、进程调用和归档能力继续由共享治理模块统一导出。
from manage_docs_shared import (
    read_json,
    read_skill_version,
    resolve_project,
    shutil,
    subprocess,
    zipfile,
)

# 会话与同步模块提供发布后文档治理更新能力。
from manage_docs_scaffold_session import write_development, write_git_changelog
from manage_docs_sync_verify import sync_root_agents, verify_docs

# 源码治理报告阻止不合规 Python 进入正式发布包。
from source_governance import (
    format_source_governance_errors,
    release_source_governance_report,
    source_governance_report,
)
from agents_decisions import decision_request

# 内容策略同时用于生成收据和复核安装包边界。
from release_content_policy import (
    POLICY_VERSION,
    analyze_release_content_root,
    release_content_policy_receipt,
    validate_recorded_release_content_policy,
)

# 版本策略拒绝回退、重复或格式无效的发布编号。
from version_policy import parse_historical_version_tuple, parse_version_tuple, version_policy_error
from git_worktree_policy import inspect_worktree_policy

# 安装侧清理原语确保发布生成与安装验证使用同一算法。
from install_release_sanitization import (
    detect_binary_sensitive_matches,
    is_probably_text_bytes,
    normalize_line_endings,
    sanitize_release_text,
    parse_sanitization_declarations,
    validate_against_source,
)

# Git 命令保留原始输出，供上层规则形成可解释诊断。
def run_git(project: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """在指定工作区执行 Git 命令。

    Args:
        project: Git 仓库根目录。
        args: 不含可执行文件名的 Git 参数。

    Returns:
        含退出码和标准输出的进程结果。
    """

    # release gate 需要自行解释 stdout/stderr，因此这里不抛出异常。
    return subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)

# 简单探测只暴露成功标志和首选诊断文本。
def git_ok(project: Path, args: list[str]) -> tuple[bool, str]:
    """执行 Git 命令并压缩结果。

    Args:
        project: Git 仓库根目录。
        args: 不含可执行文件名的 Git 参数。

    Returns:
        命令是否成功以及首选输出文本。
    """

    # 保留完整进程结果，便于同时读取退出码和输出文本。
    completed_process_result = run_git(project, args)  # git 命令执行结果

    # 调用方只关心成功与否和一段可读输出。
    return completed_process_result.returncode == 0, (
        completed_process_result.stdout or completed_process_result.stderr
    ).strip()

# release prepare 白名单约束脏工作区中可随版本推进的路径。
def governed_allowed_paths(profile: dict[str, Any], skill_dir: Path, project: Path) -> list[str]:
    """计算 release prepare 允许变更的路径前缀。

    Args:
        profile: 项目治理配置。
        skill_dir: skill 源目录。
        project: 仓库根目录。

    Returns:
        POSIX 风格的允许路径前缀。
    """

    # git 分支策略可能缺失或来自旧配置，读取前先做对象类型保护。
    dict_policy = profile.get("git_branch_policy", {}) if isinstance(profile.get("git_branch_policy"), dict) else {}  # release 打包校验输入值

    # 显式配置的允许路径优先于默认 skill 仓库布局。
    list_configured = dict_policy.get("release_prepare_allowed_paths")  # release prepare 白名单配置

    # 配置存在时只保留非空路径，并统一使用 POSIX 分隔符。
    if isinstance(list_configured, list) and list_configured:

        # 返回 governed_allowed_paths 的 release 载荷。
        return [str(item).replace("\\", "/").strip().strip("/") for item in list_configured if str(item).strip()]

    # 默认允许当前 skill、测试、文档、治理状态和 dist 历史参与 release 准备。
    str_rel_skill = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else skill_dir.name  # 默认白名单中的 skill 路径

    # 返回路径前缀而不是 glob，后续 status 检查按前缀快速判断。
    return [str_rel_skill, "tests", "docs", ".agents", "AGENTS.md", "dist"]

# 收据文件名同时约束打包端和安装端的发现行为。
def receipt_filename(profile: dict[str, Any]) -> str:
    """读取发布收据文件名。

    Args:
        profile: 项目治理配置。

    Returns:
        配置值或兼容历史版本的默认文件名。
    """

    # release_contract 可能来自用户配置，先限制为字典再取字段。
    dict_release = profile.get("release_contract", {}) if isinstance(profile.get("release_contract"), dict) else {}  # 收据命名契约

    # 空字符串配置视为未配置，避免创建无名文件。
    str_receipt_file = str(dict_release.get("receipt_file", "RELEASE_RECEIPT.json")).strip()  # 收据文件名

    # 收据文件名是 release gate 与安装验证的契约字段。
    return str_receipt_file or "RELEASE_RECEIPT.json"

# 清理契约仅在 skill 发布流程启用，避免误套普通项目。
def release_sanitization_settings(profile: dict[str, Any], project_kind: str) -> dict[str, Any]:
    """汇总发布包敏感信息清理策略。

    Args:
        profile: 项目治理配置。
        project_kind: 当前项目类型。

    Returns:
        归一化后的清理开关、范围、模式和收据要求。
    """

    # sanitization 规则位于 release_contract，旧配置缺失时使用安全默认值。
    dict_release = profile.get("release_contract", {}) if isinstance(profile.get("release_contract"), dict) else {}  # 敏感信息清理契约

    # 只有 skill release 才要求安装包敏感信息清理。
    bool_required = bool(dict_release.get("sanitization_required", False)) and project_kind == "skill"  # 是否强制清理

    # 返回结构字段由下游收据验证依赖，不能改名。
    return {
        "required": bool_required,
        "scope": str(dict_release.get("sanitization_scope", "not-configured")).strip() or "not-configured",
        "mode": str(dict_release.get("sanitization_mode", "not-configured")).strip() or "not-configured",
        "receipt_required": bool(dict_release.get("sanitization_receipt_required", False)) and project_kind == "skill",
    }

# 路径白名单同时接受目录自身和目录内后代。
def matches_governed_path(path: str, allowed: list[str]) -> bool:
    """判断状态路径是否落在发布白名单内。

    Args:
        path: Git 状态中的相对路径。
        allowed: 允许的路径前缀。

    Returns:
        路径是否受白名单覆盖。
    """

    # git 输出可能使用反斜杠或前导 ./，先归一化再做前缀匹配。
    str_normalized = path.replace("\\", "/").strip()  # 归一化后的相对路径

    # 前导 ./ 不应影响 release 白名单判断。
    if str_normalized.startswith("./"):

        # 去除 Git 偶尔附带的当前目录前缀。
        str_normalized = str_normalized[2:]  # 去前缀后的仓库相对路径

    # 逐个前缀检查，允许目录自身及其子路径。
    for prefix in allowed:

        # 校验 matches_governed_path 的 release 分支条件。
        if str_normalized == prefix or str_normalized.startswith(prefix + "/"):

            # 任一白名单前缀命中即可允许该路径。
            return True

    # 没有命中任何治理前缀时视为 release 准备阻塞项。
    return False

# branch --list 的装饰标志不属于真实分支名。
def normalize_branch_list_line(line: str) -> str:
    """清理 Git 分支列表中的装饰标志。

    Args:
        line: Git 输出的一行。

    Returns:
        可用于集合比较的分支名。
    """

    # git branch 可能在当前分支前添加 *，worktree 分支前添加 +。
    return line.strip().lstrip("*+ ").strip()

# rename 状态保留源和目标两端，防止路径治理出现盲区。
def parse_status_paths(line: str) -> list[str]:
    """从 git status --short 单行中解析受影响路径。

    Args:
        line: ``git status --short`` 的单行输出。

    Returns:
        普通状态的单路径，或重命名状态的双路径。
    """

    # status 前两列是状态码，后续部分才是路径主体。
    str_body = line[3:].strip() if len(line) >= 4 else line.strip()  # status 路径主体

    # rename 语法需要同时保留旧路径和新路径，避免越界移动逃过检查。
    if " -> " in str_body:

        # 定位 old path、new path 的文件边界，供 parse_status_paths 后续读写校验使用。
        str_old_path, str_new_path = str_body.split(" -> ", 1)  # rename 两端路径

        # rename 两端都必须接受白名单和敏感路径检查。
        return [str_old_path.strip().replace("\\", "/"), str_new_path.strip().replace("\\", "/")]

    # 普通变更只包含一个路径。
    return [str_body.replace("\\", "/")]

# 仅排除治理工具自身产生且已明确登记的临时文件。
def filter_runtime_paths(paths: list[str]) -> list[str]:
    """移除发布检查忽略的运行期路径。

    Args:
        paths: 从状态行解析出的路径。

    Returns:
        仍需接受发布治理检查的路径。
    """

    # 运行期 git 噪音不应阻塞 release prepare。
    return [path for path in paths if path and path not in IGNORED_RUNTIME_GIT_PATHS]

# 状态行至少含一个有效路径时才参与 dirty 检查。
def filter_runtime_status_lines(lines: list[str]) -> list[str]:
    """过滤只包含运行期临时路径的状态行。

    Args:
        lines: Git 状态输出行。

    Returns:
        至少包含一个受治理路径的原始状态行。
    """

    # 保留原始 status 行文本，便于错误消息展示具体 git 状态。
    list_filtered: list[str] = []  # 过滤后的 status 行

    # 每一行可能包含 rename 的双路径，需要先解析再过滤。
    for line in lines:

        # 空行不携带路径信息，直接跳过。
        if not line.strip():

            # 跳过空行后继续解析下一条 Git 状态。
            continue

        # 只有存在非忽略路径时，才保留这条 status 行。
        list_paths = filter_runtime_paths(parse_status_paths(line))  # 当前 status 行的有效路径

        # 过滤后仍有路径才保留原始状态码供诊断展示。
        if list_paths:

            # 原始文本保留状态码和 rename 展示信息。
            list_filtered.append(line)

    # 返回仍需 release gate 处理的 status 行。
    return list_filtered

# 变更路径和 Git 查询错误作为两类独立发布证据返回。
def changed_paths(project: Path) -> tuple[list[str], list[str]]:
    """读取发布门禁关注的工作区变更。

    Args:
        project: Git 仓库根目录。

    Returns:
        去重路径列表和 Git 查询错误列表。
    """

    # git status 是 release prepare 判断 dirty worktree 的输入。
    completed_process_status = run_git(project, ["status", "--short"])  # release dirty 检查结果

    # git 命令失败时返回错误列表，让调用方统一阻塞 release。
    if completed_process_status.returncode != 0:

        # 没有可信状态输出时不返回任何推测路径。
        return [], ["git status --short failed"]

    # 路径列表用于与 release 白名单做集合比较。
    list_paths: list[str] = []  # 当前工作区变更路径

    # 逐行解析 status，兼容 rename 行携带两个路径。
    for line in completed_process_status.stdout.splitlines():

        # 空状态行不应产生空路径记录。
        if not line.strip():

            # 后续行仍可能包含有效工作区变更。
            continue

        # 普通和 rename 路径统一汇入待治理集合。
        list_paths.extend(parse_status_paths(line))

    # 去重排序后返回，保证错误消息稳定。
    return sorted(set(filter_runtime_paths(list_paths))), []

# 文件摘要写入收据，用于安装前后的逐文件完整性验证。
def sha256_file(path: Path) -> str:
    """计算文件内容的 SHA-256 摘要。

    Args:
        path: 待读取的文件路径。

    Returns:
        小写十六进制摘要。
    """

    # 摘要用于 release 收据、清单和不可变历史校验。
    digest_state = hashlib.sha256()  # 增量哈希器

    # 分块读取避免大文件一次性进入内存。
    with path.open("rb") as handle:

        # 逐项检查 sha256_file 发布候选。
        for chunk in iter(lambda: handle.read(65536), b""):

            # 调用 update 处理 sha256_file。
            digest_state.update(chunk)

    # 十六进制摘要是收据 JSON 中的稳定表示。
    return digest_state.hexdigest()

# 排序后的摘要清单保证收据可复现并支持直接结构比较。
def build_release_file_manifest(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, str]]:
    """构建发布目录的文件路径和摘要清单。

    Args:
        root: 版本化发布目录。
        exclude: 不计入清单的相对路径。

    Returns:
        按路径排序的文件摘要记录。
    """

    # 排除集用于跳过收据自身或调用方明确忽略的文件。
    set_excluded = exclude or set()  # release 清单排除路径

    # manifest 是收据验证和包内容比对的稳定输入。
    list_manifest: list[dict[str, str]] = []  # release 文件清单

    # 排序遍历保证跨平台收据顺序稳定。
    for path in sorted(root.rglob("*")):

        # 目录自身没有内容摘要，清单只记录普通文件。
        if not path.is_file():

            # 继续遍历目录中的实际文件成员。
            continue

        # 清单路径以 release 根目录为基准。
        str_relative = path.relative_to(root).as_posix()  # release 内相对路径

        # 调用方排除的文件不参与内容校验。
        if str_relative in set_excluded:

            # 排除收据自身等已声明的非清单成员。
            continue

        # 每条清单记录绑定规范路径和实时内容摘要。
        list_manifest.append({"path": str_relative, "sha256": sha256_file(path)})

    # 返回按路径排序的稳定清单。
    return list_manifest

# ZIP 成员统一带版本目录前缀，解压不会污染目标父目录。
def write_release_zip(release_dir: Path, zip_path: Path) -> None:
    """把版本目录写成对应的 ZIP 包。

    Args:
        release_dir: 已验证的版本目录。
        zip_path: 目标压缩包路径。

    Returns:
        无；成功时压缩包完整落盘。
    """

    # zip 目录可能是首次创建的 dist 输出目录。
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    # ZipFile 上下文确保写入完成后关闭文件句柄。
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:

        # 包内路径保留 dist/<release-name>/ 前缀，匹配安装包布局。
        for path in sorted(release_dir.rglob("*")):

            # 仅文件成为 ZIP 成员，空目录无需单独记录。
            if path.is_file():

                # 成员名保留版本目录作为安全解压边界。
                archive.write(path, path.relative_to(release_dir.parent).as_posix())

# 当前版本产物由本次命令重建，不纳入历史不可变快照。
def release_target_exclusions(skill_name: str, version: str) -> set[str]:
    """返回当前发布目标的预期产物路径。

    Args:
        skill_name: skill 名称。
        version: 目标版本号。

    Returns:
        版本目录和同名 ZIP 路径集合。
    """

    # 当前版本的 release 目录和 zip 是本次命令的预期输出。
    return {
        f"dist/{skill_name}-{version}/",
        f"dist/{skill_name}-{version}.zip",
    }

# 排除判断兼容目录前缀和单文件两种产物形态。
def is_excluded_dist_artifact(relative_path: str, excluded: set[str]) -> bool:
    """判断 dist 文件是否属于当前发布目标。

    Args:
        relative_path: 相对于项目根的产物路径。
        excluded: 本次构建允许变化的路径集合。

    Returns:
        文件是否应从历史快照排除。
    """

    # dist 快照使用 POSIX 路径，便于和 release 排除项比较。
    str_normalized = relative_path.replace("\\", "/")  # dist 相对路径

    # 排除项可以是目录前缀，也可以是单个 zip 文件。
    for item in excluded:

        # 比较前统一路径分隔符，避免 Windows 输出差异。
        str_entry = item.replace("\\", "/")  # 排除项路径

        # 目录产物通过前缀覆盖其全部成员。
        if str_entry.endswith("/"):

            # 当前版本目录内的所有文件都属于预期输出。
            if str_normalized.startswith(str_entry):

                # 命中目录排除项后无需继续扫描其他规则。
                return True

        # ZIP 等单文件产物要求路径完全一致。
        elif str_normalized == str_entry:

            # 同名版本压缩包也是本次构建的预期输出。
            return True

    # 未命中当前 release 产物时，需要纳入历史 dist 快照。
    return False

# 发布前后快照用于证明旧版本目录和 ZIP 未被改写。
def dist_artifact_snapshot(project: Path, excluded: set[str] | None = None) -> list[dict[str, str]]:
    """记录历史发布产物的文件摘要。

    Args:
        project: 仓库根目录。
        excluded: 当前构建允许变化的产物路径。

    Returns:
        按路径排序的历史文件摘要记录。
    """

    # dist 历史用于判断 package-release 是否意外改写旧产物。
    path_dist_root = project / "dist"  # release 历史产物根目录

    # 没有 dist 目录时表示当前没有历史发布产物。
    if not path_dist_root.exists():

        # 首次发布不存在需要保护的旧版本快照。
        return []

    # 当前 release 的预期输出需要从历史快照中排除。
    set_blocked = excluded or set()  # 本次 release 产物排除项

    # 快照记录历史文件路径和摘要，供发布后对比。
    list_snapshot: list[dict[str, str]] = []  # dist 历史快照

    # 排序遍历保证快照顺序稳定。
    for path in sorted(path_dist_root.rglob("*")):

        # 快照只覆盖实际文件，目录结构由文件路径隐式表达。
        if not path.is_file():

            # 目录节点不参与文件级不可变摘要比较。
            continue

        # 快照路径以项目根为基准，与 git status 输出保持一致。
        str_relative = path.relative_to(project).as_posix()  # 项目内相对路径

        # 当前 release 产物不参与历史不可变性检查。
        if is_excluded_dist_artifact(str_relative, set_blocked):

            # 本次目标稍后由独立收据和 ZIP 校验覆盖。
            continue

        # 历史文件路径与摘要共同构成发布前基线。
        list_snapshot.append({"path": str_relative, "sha256": sha256_file(path)})

    # 返回历史 dist 产物快照。
    return list_snapshot

# 收据解析失败统一映射为空字典，由验证器生成稳定诊断。
def read_release_receipt(path: Path) -> dict[str, Any]:
    """读取并验证发布收据的顶层结构。

    Args:
        path: JSON 收据路径。

    Returns:
        有效对象映射；读取失败或非对象内容返回空字典。
    """

    # 文件缺失、编码损坏和 JSON 损坏统一视为无效收据。
    try:

        # 仅接受 UTF-8 JSON，保持发布包跨平台可复核。
        dict_data = json.loads(path.read_text(encoding="utf-8"))  # 收据顶层 JSON 值

    # 解析异常由调用方转换为带路径的稳定发布诊断。
    except Exception:

        # 空映射明确表示收据不可用。
        return {}

    # 数组或标量 JSON 不满足收据字段契约。
    return dict_data if isinstance(dict_data, dict) else {}

# 文本和二进制清洗原语复用安装验证模块，保持发布与安装判定一致。
# 源码分析允许仓库内 evals 等仅源码成员进入打包清单。
def source_release_content_analysis(skill_dir: Path) -> dict[str, Any]:
    """分析待发布技能源码目录。

    参数：skill_dir 为技能源码根。
    返回：允许仓库本地源码成员的内容策略报告。
    """

    # 源码模式允许发布器随后清洗的仓库本地成员。
    return analyze_release_content_root(skill_dir, allow_source_only_repo_local=True)

# 发布树分析使用安装包的严格顶层内容策略。
def release_tree_content_analysis(release_dir: Path) -> dict[str, Any]:
    """分析已生成的版本化发布目录。

    参数：release_dir 为待验证发布树。
    返回：安装包严格内容策略报告。
    """

    # 最终发布目录不得启用源码专用例外。
    return analyze_release_content_root(release_dir)

# 单文件清洗器返回可选收据记录和可选二进制错误。
def sanitize_release_member(
    path_release_file: Path,
    str_relative_path: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """清洗一个发布成员并生成收据条目。

    参数：path_release_file 为发布副本文件。
    参数：str_relative_path 为相对技能根的位置。
    返回：可选清洗记录与可选阻断错误。
    """

    # 发布副本字节决定文本清洗或二进制保守检测路径。
    bytes_release = path_release_file.read_bytes()  # 当前发布成员字节。

    # 非文本成员不得自动改写，只检测明确敏感模式。
    if not is_probably_text_bytes(bytes_release):

        # 二进制扫描返回命中的敏感类别。
        list_hits = detect_binary_sensitive_matches(bytes_release)  # 二进制敏感规则命中。

        # 无敏感模式时保持文件原样且不生成收据记录。
        if not list_hits:

            # 两个空状态表示成员无需清洗。
            return None, None

        # 二进制敏感内容必须由源码维护者处理。
        str_error = (
            "binary file contains sensitive content and cannot be sanitized safely: "
            f"{str_relative_path}"
        )  # 当前二进制阻断诊断。

        # 错误状态不产生虚假的清洗记录。
        return None, str_error

    # UTF-8 文本交给共享确定性清洗器处理。
    str_text = bytes_release.decode("utf-8")  # 当前发布文本。

    # 清洗器同时返回替换后文本和实际命中规则。
    tuple_sanitization = sanitize_release_text(str_text)  # 文本清洗二元结果。

    # 首项是确定性替换后的文本。
    str_sanitized_text = tuple_sanitization[0]  # 待写回发布副本的文本。

    # 次项记录实际发生替换的规则和占位符。
    list_matches = tuple_sanitization[1]  # 当前成员清洗命中。

    # 没有替换时不重写换行风格或生成收据条目。
    if not list_matches:

        # 文件保持原字节。
        return None, None

    # 清洗文本使用 LF 写回，确保摘要跨平台稳定。
    path_release_file.write_text(
        normalize_line_endings(str_sanitized_text),
        encoding="utf-8",
    )

    # 收据条目聚合规则、占位符和最终文件摘要。
    dict_record = {
        "path": str_relative_path,  # 清洗成员相对位置。
        "rules": sorted({dict_item["rule"] for dict_item in list_matches}),  # 命中规则集合。
        "placeholders": sorted(  # 实际写入发布副本的占位符集合
            {dict_item["placeholder"] for dict_item in list_matches}  # 去重后的占位符来源
        ),  # 实际写入占位符集合。
        "sha256": sha256_file(path_release_file),  # 清洗后文件摘要。
    }

    # 文本清洗成功不产生阻断错误。
    return dict_record, None

# 发布树清洗器遍历源码成员，确保只处理对应发布副本。
def sanitize_release_tree(
    profile: dict[str, Any],
    project_kind: str,
    skill_dir: Path,
    release_dir: Path,
) -> tuple[dict[str, Any], list[str]]:
    """按项目发布合同清洗版本化发布树。

    参数：profile 和 project_kind 决定清洗策略。
    参数：skill_dir 与 release_dir 定位源码和发布副本。
    返回：清洗收据块与阻断错误列表。
    """

    # 策略映射决定是否启用清洗及收据字段。
    dict_settings = release_sanitization_settings(profile, project_kind)  # 当前清洗策略。

    # 基础收据字段即使禁用清洗也保持稳定。
    dict_result: dict[str, Any] = {
        "enabled": dict_settings["required"],  # 是否启用自动清洗。
        "scope": dict_settings["scope"],  # 策略覆盖范围。
        "mode": dict_settings["mode"],  # 确定性清洗模式。
        "files": [],  # 实际清洗成员记录。
    }

    # 强制逐文件记录时显式写入收据合同。
    if dict_settings["receipt_required"]:

        # 安装验证器据此要求 files 证据。
        dict_result["receipt_required"] = True  # 声明安装端必须验证逐文件记录

    # 非 skill 或未启用策略时不扫描文件树。
    if not dict_settings["required"]:

        # 空错误列表表示无需清洗即通过。
        return dict_result, []

    # 文本清洗记录按源码成员排序稳定累积。
    list_records: list[dict[str, Any]] = []  # 实际清洗收据条目。

    # 二进制阻断诊断独立累积，允许一次报告全部文件。
    list_errors: list[str] = []  # 当前清洗错误。

    # 源码树限制发布成员范围，并保证遍历顺序稳定。
    for path_source_file in sorted(skill_dir.rglob("*")):

        # 目录不对应可清洗发布成员。
        if not path_source_file.is_file():

            # 继续检查下一个源码成员。
            continue

        # 源码与发布副本共享同一 POSIX 相对位置。
        str_relative_path = path_source_file.relative_to(skill_dir).as_posix()  # 当前成员位置。

        # 根 AGENTS.md 由发布清洗策略排除。
        if str_relative_path == "AGENTS.md":

            # 生成规则文件不参与敏感值替换。
            continue

        # 缺失发布副本由其他内容策略门禁负责诊断。
        path_release_file = release_dir / str_relative_path  # 对应发布成员。

        # 只处理实际复制到发布树的文件。
        if not path_release_file.is_file():

            # 源码专用成员可能被发布策略排除。
            continue

        # 单文件 helper 返回互斥的记录和错误状态。
        tuple_member_result = sanitize_release_member(  # 当前源码成员的清洗结果
            path_release_file,  # 待清洗的发布副本
            str_relative_path,  # 发布副本相对 skill 根的位置
        )  # 当前成员清洗结果。

        # 首项为实际发生文本替换时的收据记录。
        dict_record = tuple_member_result[0]  # 可选清洗条目。

        # 次项为敏感二进制阻断诊断。
        str_error = tuple_member_result[1]  # 可选清洗错误。

        # 非空记录进入最终 files 列表。
        if dict_record is not None:

            # 文件遍历顺序保持收据稳定。
            list_records.append(dict_record)

        # 二进制错误与其他成员诊断共同返回。
        if str_error is not None:

            # 不安全成员不会生成清洗记录。
            list_errors.append(str_error)

    # 收据 files 字段在遍历完成后一次写入。
    dict_result["files"] = list_records  # 排序稳定的逐文件清洗证据

    # 调用方决定是否因错误停止发布。
    return dict_result, list_errors

# 清洗验证器复用安装侧的声明解析和源码逐文件对照。
def verify_release_sanitization(
    profile: dict[str, Any],
    project_kind: str,
    skill_dir: Path,
    release_dir: Path,
    receipt: dict[str, Any],
) -> list[str]:
    """验证发布收据的清洗声明与源码确定性差异。

    参数：profile 和 project_kind 决定清洗策略。
    参数：skill_dir 与 release_dir 定位源码和发布副本。
    参数：receipt 为待验证发布收据。
    返回：稳定排序语义的清洗诊断列表。
    """

    # 非强制清洗项目不要求 sanitization 收据块。
    dict_settings = release_sanitization_settings(profile, project_kind)  # 本项目发布清洗策略

    # 没有强制策略时保持历史空诊断合同。
    if not dict_settings["required"]:

        # 调用方可继续其他发布收据检查。
        return []

    # 所有顶层策略和逐文件诊断汇总到同一列表。
    list_errors: list[str] = []  # 当前清洗验证诊断。

    # sanitization 必须是映射，缺失时无法继续解析。
    dict_sanitization = receipt.get("sanitization")  # 收据原始清洗块。

    # 缺少映射时返回与历史合同一致的单条错误。
    if not isinstance(dict_sanitization, dict):

        # 文件声明不存在，后续对照没有可信输入。
        return ["release receipt sanitization block is missing"]

    # enabled 明确证明发布器执行过自动清洗。
    if not bool(dict_sanitization.get("enabled")):

        # false 与缺失均不能构成清洗证据。
        list_errors.append("release receipt sanitization enabled flag is missing or false")

    # 收据作用域必须与项目发布策略完全一致。
    if str(dict_sanitization.get("scope", "")).strip() != dict_settings["scope"]:

        # 不同作用域无法证明预期文件集合已经覆盖。
        list_errors.append("release receipt sanitization scope does not match the release policy")

    # 清洗模式必须与发布器配置一致。
    if str(dict_sanitization.get("mode", "")).strip() != dict_settings["mode"]:

        # 未知模式不能用当前确定性算法复核。
        list_errors.append("release receipt sanitization mode does not match the release policy")

    # 要求逐文件收据时必须显式记录该标志。
    if dict_settings["receipt_required"] and not bool(dict_sanitization.get("receipt_required")):

        # 缺失标志表示逐文件证据合同不完整。
        list_errors.append("release receipt sanitization receipt_required flag is missing or false")

    # files 字段承载规则、占位符和摘要。
    object_files = dict_sanitization.get("files")  # 原始清洗文件声明。

    # 非列表声明无法进行路径安全解析。
    if not isinstance(object_files, list):

        # 与历史实现保持立即返回语义。
        return ["release receipt sanitization files list is missing"]

    # 安装侧解析器统一验证成员路径、规则、占位符和摘要字段。
    dict_declared = parse_sanitization_declarations(  # 按安全相对路径索引的清洗声明
        release_dir,  # 已生成的版本目录
        object_files,  # 收据原始逐文件清理声明
        list_errors,  # 追加解析阶段发现的声明错误
    )  # 通过路径边界检查的清洗声明。

    # 源码对照器验证确定性文本清洗、二进制原样性和声明完整性。
    validate_against_source(
        skill_dir,
        release_dir,
        receipt_filename(profile),
        dict_declared,
        list_errors,
    )

    # 诊断顺序沿用策略检查和源码遍历顺序。
    return list_errors

# 收据内容必须与版本目录身份和实时文件摘要完全一致。
def verify_release_content_policy(
    receipt: dict[str, Any],
    *,
    source_forbidden_paths: list[str],
    release_analysis: dict[str, Any],
    require_source_paths: bool,
) -> list[str]:
    """核对收据记录与发布目录的内容策略分析。

    Args:
        receipt: 已解析的发布收据。
        source_forbidden_paths: 源目录中禁止进入发布包的路径。
        release_analysis: 发布目录的实时内容分析。
        require_source_paths: 是否要求收据记录源路径。

    Returns:
        阻止发布的策略错误列表。
    """

    # 先验证收据声明，确保记录值与当前发布树一致。
    list_errors = validate_recorded_release_content_policy(  # 收据与实时发布树的差异
        receipt.get("release_content_policy"),  # 收据中的内容策略声明
        release_analysis,  # 当前发布树内容策略分析
        forbidden_source_paths=source_forbidden_paths,  # 源码侧禁止进入包的路径
        require_source_paths=require_source_paths,  # 是否强制记录源码路径证据
    )

    # 顶层白名单是安装时的结构边界，出现额外入口必须阻断。
    if release_analysis["unexpected_top_level_entries"]:

        # 额外入口可能绕过安装端约定的 skill 布局。
        list_errors.append("release content policy rejected unexpected top-level release entries")

    # 开发期文件不得随版本包进入用户的 skill 安装目录。
    if release_analysis["forbidden_paths"]:

        # 命中开发内容说明复制或清理阶段存在泄漏。
        list_errors.append("release content policy rejected forbidden development content in release")

    # 调用方统一展示全部内容策略诊断。
    return list_errors

# 收据身份字段和文件清单共同构成安装端的信任边界。
def verify_release_receipt(
    project: Path, receipt_path: Path, release_dir: Path,
    skill_name: str, version: str, source_rel: str,
    *, require_repo_dist: bool,
) -> list[str]:
    """验证发布收据的身份字段和文件清单。

    Args:
        project: 仓库根目录。
        receipt_path: 待验证的收据路径。
        release_dir: 已生成的版本目录。
        skill_name: 期望的 skill 名称。
        version: 期望的版本号。
        source_rel: skill 源目录相对路径。
        require_repo_dist: 是否要求仓库级完整验证。

    Returns:
        收据不一致项列表。
    """

    # 解析失败由统一的 invalid receipt 诊断覆盖。
    dict_receipt = read_release_receipt(receipt_path)  # 已解析的发布收据

    # 错误按契约字段顺序累积，确保门禁输出稳定。
    list_errors: list[str] = []  # 收据契约错误

    # 空收据无法继续进行字段级比较。
    if not dict_receipt:

        # 路径加入诊断，便于定位缺失或损坏的收据。
        return [f"invalid release receipt: {display_path(receipt_path, project)}"]

    # skill 名称必须与版本目录的命名主体一致。
    if str(dict_receipt.get("skill_name", "")).strip() != skill_name:

        # 身份不一致的收据不能证明当前 skill 包。
        list_errors.append("release receipt skill_name does not match release directory")

    # 版本字段必须精确匹配本次请求，禁止跨版本复用收据。
    if str(dict_receipt.get("version", "")).strip() != version:

        # 跨版本收据会破坏发布历史的不可变关联。
        list_errors.append("release receipt version does not match requested release version")

    # 源路径用于证明发布包来自预期的仓库子目录。
    if str(dict_receipt.get("source_path", "")).strip().replace("\\", "/") != source_rel:

        # 不同源码位置的收据不可为当前产物背书。
        list_errors.append("release receipt source_path does not match skill source path")

    # 验证级别区分仓库内正式包与外部目录的降级检查。
    str_expected_validation = "strong" if require_repo_dist else "reduced_assurance"  # 收据应声明的验证等级

    # 仓库 dist 包必须声明强验证，外部包只能声明降级保证。
    if str(dict_receipt.get("validation_level", "")).strip() != str_expected_validation:

        # 验证等级必须真实反映可用的仓库上下文。
        list_errors.append("release receipt validation_level is inconsistent with the release source")

    # 实时摘要排除收据自身，避免循环依赖。
    list_expected_files = build_release_file_manifest(  # 发布目录实时文件清单
        release_dir,  # 重新遍历的发布目录
        exclude={receipt_path.name},  # 收据自身不参与循环摘要
    )

    # 收据声明稍后与实时文件清单进行一一比较。
    list_actual_files = dict_receipt.get("files")  # 收据声明的文件记录

    # 缺失清单时不能证明发布内容完整性。
    if not isinstance(list_actual_files, list):

        # 非列表值无法表达稳定的逐文件摘要集合。
        list_errors.append("release receipt files list is missing")

    # 合法列表逐项归一化后再与实时摘要进行稳定比较。
    else:

        # 归一化剥离无关 JSON 类型差异，只保留契约字段。
        list_filtered: list[dict[str, str]] = []  # 归一化后的收据文件记录

        # 每个成员必须同时提供相对路径和 SHA-256 摘要。
        for dict_item in list_actual_files:

            # 非对象成员无法提供 path 和 sha256 契约字段。
            if not isinstance(dict_item, dict):

                # 保留诊断后继续扫描，以一次报告全部无效成员。
                list_errors.append("release receipt files list contains invalid entries")

                # 当前成员不能安全转换为清单记录。
                continue

            # 字段统一转为去空白字符串，匹配生成端序列化方式。
            list_filtered.append(
                {
                    "path": str(dict_item.get("path", "")).strip(),
                    "sha256": str(dict_item.get("sha256", "")).strip(),
                }
            )

        # 顺序和摘要均须一致，防止遗漏、注入或内容漂移。
        if list_filtered != list_expected_files:

            # 任意路径或摘要差异都会阻止安装。
            list_errors.append("release receipt file manifest does not match packaged release contents")

    # 返回全部身份和完整性诊断，保持字段检查顺序。
    return list_errors

# 分支治理需要在同一时点读取分支集合和工作区状态。
def current_branch_and_locals(project: Path) -> tuple[str, list[str], list[str]]:
    """读取当前分支、本地分支集合和有效工作区状态。

    Args:
        project: Git 仓库根目录。

    Returns:
        当前分支名、本地分支名列表和过滤后的状态行。
    """

    # 当前分支用于验证发布操作发生在允许的开发分支。
    completed_process_git_branch_result = run_git(project, ["branch", "--show-current"])  # 当前分支查询结果

    # 本地分支集合用于检测未合并或污染发布流程的分支状态。
    completed_process_git_list_result = run_git(project, ["branch", "--list"])  # 本地分支查询结果

    # 工作区状态用于阻止未声明文件进入版本包。
    completed_process_git_status_result = run_git(project, ["status", "--short"])  # 工作区状态查询结果

    # 三个查询必须全部成功才能形成一致的分支治理快照。
    tuple_git_results = (  # 分支、列表和状态命令结果
        completed_process_git_branch_result,  # 当前分支查询
        completed_process_git_list_result,  # 本地分支列表查询
        completed_process_git_status_result,  # 工作区短状态查询
    )

    # 任一 Git 查询失败都无法形成可信分支证据。
    if any(completed_process_result.returncode != 0 for completed_process_result in tuple_git_results):

        # 空三元组明确告知调用方仓库事实不可读。
        return "", [], []

    # 当前分支名作为发布分支策略的主判据。
    str_current_branch = completed_process_git_branch_result.stdout.strip()  # 当前检出分支

    # 去除 Git 装饰字符后排序，保证跨调用输出稳定。
    list_local_branches = sorted(  # 归一化并排序的本地分支集合
        normalize_branch_list_line(str_line)  # 去除当前分支装饰标志
        for str_line in completed_process_git_list_result.stdout.splitlines()  # 遍历 Git 分支输出
        if str_line.strip()  # 忽略 Git 输出中的空白行
    )  # 仓库内全部本地分支

    # 运行期噪音不参与发布 dirty 判定。
    list_status_lines = filter_runtime_status_lines(  # 排除已登记运行期噪音后的状态行
        completed_process_git_status_result.stdout.splitlines()  # 原始短状态行
    )  # 仍需治理的工作区状态行

    # 三项证据供 prepare gate 同步判断分支和 dirty 状态。
    return str_current_branch, list_local_branches, list_status_lines
