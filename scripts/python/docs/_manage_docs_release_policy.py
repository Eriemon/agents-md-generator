"""执行 release 准备、打包、内容策略校验和发布治理检查。"""

# 导入 release 管理 所需的依赖模块。
from __future__ import annotations

# 分类脚本可从任意任务目录直接执行，这里补齐兄弟任务模块路径。
import sys
from pathlib import Path

_scripts_python_root = Path(__file__).resolve().parents[1]
for _task_dir in _scripts_python_root.iterdir():
    if _task_dir.is_dir():
        _task_path = str(_task_dir)
        if _task_path not in sys.path:
            sys.path.insert(0, _task_path)

# release 治理复用文档脚本的共享 I/O、JSON、路径和输出工具，当前保持原有导入边界。
from manage_docs_shared import *
from manage_docs_scaffold_session import write_development, write_git_changelog
from manage_docs_sync_verify import sync_root_agents, verify_docs
from source_governance import (
    format_source_governance_errors,
    release_source_governance_report,
    source_governance_report,

    # 分隔当前密集代码块，保留原有执行顺序。
)
from agents_decisions import decision_request
from release_content_policy import (
    POLICY_VERSION,
    analyze_release_content_root,
    release_content_policy_receipt,
    validate_recorded_release_content_policy,
)
from version_policy import parse_historical_version_tuple, parse_version_tuple, version_policy_error

# 定义 run_git 的release 管理处理入口。
def run_git(project: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """在指定工作区执行 git 命令并返回完整进程结果。"""

    # release gate 需要自行解释 stdout/stderr，因此这里不抛出异常。
    return subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)


# 定义 git_ok 的release 管理处理入口。
def git_ok(project: Path, args: list[str]) -> tuple[bool, str]:
    """执行 git 命令并压缩为布尔状态和可展示消息。"""

    # 保留完整进程结果，便于同时读取退出码和输出文本。
    completed_process_result = run_git(project, args)  # git 命令执行结果

    # 调用方只关心成功与否和一段可读输出。
    return completed_process_result.returncode == 0, (
        completed_process_result.stdout or completed_process_result.stderr
    ).strip()


# 定义 governed_allowed_paths 的release 管理处理入口。
def governed_allowed_paths(profile: dict[str, Any], skill_dir: Path, project: Path) -> list[str]:
    """计算 release prepare 阶段允许存在变更的路径前缀。"""

    # git 分支策略可能缺失或来自旧配置，读取前先做对象类型保护。
    dict_policy = profile.get("git_branch_policy", {}) if isinstance(profile.get("git_branch_policy"), dict) else {}  # release 打包校验输入值

    # 显式配置的允许路径优先于默认 skill 仓库布局。
    list_configured = dict_policy.get("release_prepare_allowed_paths")  # release prepare 白名单配置

    # 配置存在时只保留非空路径，并统一使用 POSIX 分隔符。
    if isinstance(list_configured, list) and list_configured:

        # 返回 governed_allowed_paths 的 release 载荷。
        return [str(item).replace("\\", "/").strip().strip("/") for item in list_configured if str(item).strip()]

    # 默认允许当前 skill、测试、文档、治理状态和 dist 历史参与 release 准备。
    str_rel_skill = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else skill_dir.name  # release 打包校验输入值

    # 返回路径前缀而不是 glob，后续 status 检查按前缀快速判断。
    return [str_rel_skill, "tests", "docs", ".agents", "AGENTS.md", "dist"]


# 定义 receipt_filename 的release 管理处理入口。
def receipt_filename(profile: dict[str, Any]) -> str:
    """读取 release 收据文件名，缺省保持历史 RELEASE_RECEIPT.json。"""

    # release_contract 可能来自用户配置，先限制为字典再取字段。
    dict_release = profile.get("release_contract", {}) if isinstance(profile.get("release_contract"), dict) else {}  # release 打包校验输入值

    # 空字符串配置视为未配置，避免创建无名文件。
    str_receipt_file = str(dict_release.get("receipt_file", "RELEASE_RECEIPT.json")).strip()  # 收据文件名

    # 收据文件名是 release gate 与安装验证的契约字段。
    return str_receipt_file or "RELEASE_RECEIPT.json"


# 定义 release_sanitization_settings 的release 管理处理入口。
def release_sanitization_settings(profile: dict[str, Any], project_kind: str) -> dict[str, Any]:
    """汇总 release sanitization 策略，并限定只对 skill 项目强制生效。"""

    # sanitization 规则位于 release_contract，旧配置缺失时使用安全默认值。
    dict_release = profile.get("release_contract", {}) if isinstance(profile.get("release_contract"), dict) else {}  # release 打包校验输入值

    # 只有 skill release 才要求安装包敏感信息清理。
    bool_required = bool(dict_release.get("sanitization_required", False)) and project_kind == "skill"  # 是否强制清理

    # 返回结构字段由下游收据验证依赖，不能改名。
    return {
        "required": bool_required,
        "scope": str(dict_release.get("sanitization_scope", "not-configured")).strip() or "not-configured",
        "mode": str(dict_release.get("sanitization_mode", "not-configured")).strip() or "not-configured",
        "receipt_required": bool(dict_release.get("sanitization_receipt_required", False)) and project_kind == "skill",
    }

# 定义 matches_governed_path 的release 管理处理入口。
def matches_governed_path(path: str, allowed: list[str]) -> bool:
    """判断一个 git status 路径是否落在 release 允许路径内。"""

    # git 输出可能使用反斜杠或前导 ./，先归一化再做前缀匹配。
    str_normalized = path.replace("\\", "/").strip()  # 归一化后的相对路径

    # 前导 ./ 不应影响 release 白名单判断。
    if str_normalized.startswith("./"):

        # 整理 matches_governed_path 需要的 normalized 发布信息。
        str_normalized = str_normalized[2:]  # release 打包校验输入值

    # 逐个前缀检查，允许目录自身及其子路径。
    for prefix in allowed:

        # 校验 matches_governed_path 的 release 分支条件。
        if str_normalized == prefix or str_normalized.startswith(prefix + "/"):

            # 返回 matches_governed_path 的 release 载荷。
            return True

    # 没有命中任何治理前缀时视为 release 准备阻塞项。
    return False


# 定义 normalize_branch_list_line 的release 管理处理入口。
def normalize_branch_list_line(line: str) -> str:
    """清理 git branch 输出中的当前分支标记。"""

    # git branch 可能在当前分支前添加 *，worktree 分支前添加 +。
    return line.strip().lstrip("*+ ").strip()


# 定义 parse_status_paths 的release 管理处理入口。
def parse_status_paths(line: str) -> list[str]:
    """从 git status --short 单行中解析受影响路径。

    # 补充release 管理代码段的职责说明。
    rename 行会返回旧路径和新路径，确保 release gate 同时检查两端。
    """

    # status 前两列是状态码，后续部分才是路径主体。
    str_body = line[3:].strip() if len(line) >= 4 else line.strip()  # status 路径主体

    # rename 语法需要同时保留旧路径和新路径，避免越界移动逃过检查。
    if " -> " in str_body:

        # 定位 old path、new path 的文件边界，供 parse_status_paths 后续读写校验使用。
        str_old_path, str_new_path = str_body.split(" -> ", 1)  # rename 两端路径

        # 返回 parse_status_paths 的 release 载荷。
        return [str_old_path.strip().replace("\\", "/"), str_new_path.strip().replace("\\", "/")]

    # 普通变更只包含一个路径。
    return [str_body.replace("\\", "/")]


# 定义 filter_runtime_paths 的release 管理处理入口。
def filter_runtime_paths(paths: list[str]) -> list[str]:
    """移除 release 检查中忽略的运行期临时路径。"""

    # 运行期 git 噪音不应阻塞 release prepare。
    return [path for path in paths if path and path not in IGNORED_RUNTIME_GIT_PATHS]


# 定义 filter_runtime_status_lines 的release 管理处理入口。
def filter_runtime_status_lines(lines: list[str]) -> list[str]:
    """过滤掉只包含运行期临时路径的 git status 行。"""

    # 保留原始 status 行文本，便于错误消息展示具体 git 状态。
    list_filtered: list[str] = []  # 过滤后的 status 行

    # 每一行可能包含 rename 的双路径，需要先解析再过滤。
    for line in lines:

        # 校验 filter_runtime_status_lines 的 release 分支条件。
        if not line.strip():

            # 分隔 filter_runtime_status_lines 的控制流边界。
            continue

        # 只有存在非忽略路径时，才保留这条 status 行。
        list_paths = filter_runtime_paths(parse_status_paths(line))  # 当前 status 行的有效路径

        # 校验 filter_runtime_status_lines 的 release 分支条件。
        if list_paths:

            # 追加 filter_runtime_status_lines 的 release 诊断。
            list_filtered.append(line)

    # 返回仍需 release gate 处理的 status 行。
    return list_filtered


# 定义 changed_paths 的release 管理处理入口。
def changed_paths(project: Path) -> tuple[list[str], list[str]]:
    """读取当前工作区中 release gate 需要关注的变更路径。"""

    # git status 是 release prepare 判断 dirty worktree 的输入。
    completed_process_status = run_git(project, ["status", "--short"])  # release dirty 检查结果

    # git 命令失败时返回错误列表，让调用方统一阻塞 release。
    if completed_process_status.returncode != 0:

        # 返回 changed_paths 的 release 载荷。
        return [], ["git status --short failed"]

    # 路径列表用于与 release 白名单做集合比较。
    list_paths: list[str] = []  # 当前工作区变更路径

    # 逐行解析 status，兼容 rename 行携带两个路径。
    for line in completed_process_status.stdout.splitlines():

        # 校验 changed_paths 的 release 分支条件。
        if not line.strip():

            # 分隔 changed_paths 的控制流边界。
            continue

        # 调用 extend 处理 changed_paths。
        list_paths.extend(parse_status_paths(line))

    # 去重排序后返回，保证错误消息稳定。
    return sorted(set(filter_runtime_paths(list_paths))), []


# 定义 sha256_file 的release 管理处理入口。
def sha256_file(path: Path) -> str:
    """计算文件内容的 SHA-256 摘要。"""

    # 摘要用于 release 收据、清单和不可变历史校验。
    digest = hashlib.sha256()  # 增量哈希器

    # 分块读取避免大文件一次性进入内存。
    with path.open("rb") as handle:

        # 逐项检查 sha256_file 发布候选。
        for chunk in iter(lambda: handle.read(65536), b""):

            # 调用 update 处理 sha256_file。
            digest.update(chunk)

    # 十六进制摘要是收据 JSON 中的稳定表示。
    return digest.hexdigest()

# 定义 build_release_file_manifest 的release 管理处理入口。
def build_release_file_manifest(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, str]]:
    """构建 release 目录的文件路径和摘要清单。"""

    # 排除集用于跳过收据自身或调用方明确忽略的文件。
    set_excluded = exclude or set()  # release 清单排除路径

    # manifest 是收据验证和包内容比对的稳定输入。
    list_manifest: list[dict[str, str]] = []  # release 文件清单

    # 排序遍历保证跨平台收据顺序稳定。
    for path in sorted(root.rglob("*")):

        # 校验 build_release_file_manifest 的 release 分支条件。
        if not path.is_file():

            # 分隔 build_release_file_manifest 的控制流边界。
            continue

        # 清单路径以 release 根目录为基准。
        str_relative = path.relative_to(root).as_posix()  # release 内相对路径

        # 调用方排除的文件不参与内容校验。
        if str_relative in set_excluded:

            # 分隔 build_release_file_manifest 的控制流边界。
            continue

        # 追加 build_release_file_manifest 的 release 诊断。
        list_manifest.append({"path": str_relative, "sha256": sha256_file(path)})

    # 返回按路径排序的稳定清单。
    return list_manifest


# 定义 write_release_zip 的release 管理处理入口。
def write_release_zip(release_dir: Path, zip_path: Path) -> None:
    """把 release 目录写成对应的 zip 包。"""

    # zip 目录可能是首次创建的 dist 输出目录。
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    # ZipFile 上下文确保写入完成后关闭文件句柄。
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:

        # 包内路径保留 dist/<release-name>/ 前缀，匹配安装包布局。
        for path in sorted(release_dir.rglob("*")):

            # 校验 write_release_zip 的 release 分支条件。
            if path.is_file():

                # 调用 write 处理 write_release_zip。
                archive.write(path, path.relative_to(release_dir.parent).as_posix())


# 定义 release_target_exclusions 的release 管理处理入口。
def release_target_exclusions(skill_name: str, version: str) -> set[str]:
    """返回当前 release 产物在 dirty worktree 检查中的排除项。"""

    # 当前版本的 release 目录和 zip 是本次命令的预期输出。
    return {
        f"dist/{skill_name}-{version}/",
        f"dist/{skill_name}-{version}.zip",
    }


# 定义 is_excluded_dist_artifact 的release 管理处理入口。
def is_excluded_dist_artifact(relative_path: str, excluded: set[str]) -> bool:
    """判断 dist 文件是否属于当前 release 命令预期生成的产物。"""

    # dist 快照使用 POSIX 路径，便于和 release 排除项比较。
    str_normalized = relative_path.replace("\\", "/")  # dist 相对路径

    # 排除项可以是目录前缀，也可以是单个 zip 文件。
    for item in excluded:

        # 整理 is_excluded_dist_artifact 需要的 entry 发布信息。
        str_entry = item.replace("\\", "/")  # 排除项路径

        # 校验 is_excluded_dist_artifact 的 release 分支条件。
        if str_entry.endswith("/"):

            # 校验 is_excluded_dist_artifact 的 release 分支条件。
            if str_normalized.startswith(str_entry):

                # 返回 is_excluded_dist_artifact 的 release 载荷。
                return True

        # 校验 is_excluded_dist_artifact 的 release 分支条件。
        elif str_normalized == str_entry:

            # 返回 is_excluded_dist_artifact 的 release 载荷。
            return True

    # 未命中当前 release 产物时，需要纳入历史 dist 快照。
    return False


# 定义 dist_artifact_snapshot 的release 管理处理入口。
def dist_artifact_snapshot(project: Path, excluded: set[str] | None = None) -> list[dict[str, str]]:
    """记录 dist 目录中非当前 release 产物的文件摘要。"""

    # dist 历史用于判断 package-release 是否意外改写旧产物。
    path_dist_root = project / "dist"  # release 历史产物根目录

    # 没有 dist 目录时表示当前没有历史发布产物。
    if not path_dist_root.exists():

        # 返回 dist_artifact_snapshot 的 release 载荷。
        return []

    # 当前 release 的预期输出需要从历史快照中排除。
    set_blocked = excluded or set()  # 本次 release 产物排除项

    # 快照记录历史文件路径和摘要，供发布后对比。
    list_snapshot: list[dict[str, str]] = []  # dist 历史快照

    # 排序遍历保证快照顺序稳定。
    for path in sorted(path_dist_root.rglob("*")):

        # 校验 dist_artifact_snapshot 的 release 分支条件。
        if not path.is_file():

            # 分隔 dist_artifact_snapshot 的控制流边界。
            continue

        # 快照路径以项目根为基准，与 git status 输出保持一致。
        str_relative = path.relative_to(project).as_posix()  # 项目内相对路径

        # 当前 release 产物不参与历史不可变性检查。
        if is_excluded_dist_artifact(str_relative, set_blocked):

            # 分隔 dist_artifact_snapshot 的控制流边界。
            continue

        # 追加 dist_artifact_snapshot 的 release 诊断。
        list_snapshot.append({"path": str_relative, "sha256": sha256_file(path)})

    # 返回历史 dist 产物快照。
    return list_snapshot

# 定义 read_release_receipt 的release 管理处理入口。
def read_release_receipt(path: Path) -> dict[str, Any]:

    # 保护 read_release_receipt 中允许失败的外部访问。
    try:

        # 整理 read_release_receipt 需要的 data 发布信息。
        dict_data = json.loads(path.read_text(encoding="utf-8"))  # release 打包校验输入值
    except Exception:

        # 返回 read_release_receipt 的 release 载荷。
        return {}

    # 返回 read_release_receipt 的 release 载荷。
    return dict_data if isinstance(dict_data, dict) else {}

# 定义 is_probably_text_bytes 的release 管理处理入口。
def is_probably_text_bytes(data: bytes) -> bool:

    # 校验 is_probably_text_bytes 的 release 分支条件。
    if b"\x00" in data:

        # 返回 is_probably_text_bytes 的 release 载荷。
        return False

    # 保护 is_probably_text_bytes 中允许失败的外部访问。
    try:

        # 调用 decode 处理 is_probably_text_bytes。
        data.decode("utf-8")
    except UnicodeDecodeError:

        # 返回 is_probably_text_bytes 的 release 载荷。
        return False

    # 返回 is_probably_text_bytes 的 release 载荷。
    return True

# 定义 normalize_line_endings 的release 管理处理入口。
def normalize_line_endings(text: str) -> str:

    # 返回 normalize_line_endings 的 release 载荷。
    return text.replace("\r\n", "\n")

# 定义 source_release_content_analysis 的release 管理处理入口。
def source_release_content_analysis(skill_dir: Path) -> dict[str, Any]:

    # 返回 source_release_content_analysis 的 release 载荷。
    return analyze_release_content_root(skill_dir, allow_source_only_repo_local=True)

# 定义 release_tree_content_analysis 的release 管理处理入口。
def release_tree_content_analysis(release_dir: Path) -> dict[str, Any]:

    # 返回 release_tree_content_analysis 的 release 载荷。
    return analyze_release_content_root(release_dir)

# 定义 sanitize_release_text 的release 管理处理入口。
def sanitize_release_text(text: str) -> tuple[str, list[dict[str, str]]]:

    # 整理 sanitize_release_text 需要的 redacted 发布信息。
    redacted = text  # release 打包校验输入值

    # 汇总 matches，作为 release 打包和清理候选清单。
    list_matches: list[dict[str, str]] = []  # release 打包校验输入值

    # 逐项检查 sanitize_release_text 发布候选。
    for rule_name, pattern in SANITIZED_ASSIGNMENT_RULES:

        # 整理 sanitize_release_text 需要的 placeholder 发布信息。
        placeholder = SANITIZED_PLACEHOLDERS[rule_name]  # release 打包校验输入值

        # 标记 hit 判断，控制 sanitize_release_text 的分支走向。
        bool_hit = False  # release 打包校验输入值

        # 定义 replace_assignment 的release 管理处理入口。
        def replace_assignment(match: re.Match[str]) -> str:
            nonlocal bool_hit

            # 校验 replace_assignment 的 release 分支条件。
            if should_skip_sanitized_assignment_value(match.group(2)):

                # 返回 replace_assignment 的 release 载荷。
                return match.group(0)

            # 标记 hit 判断，控制 replace_assignment 的分支走向。
            bool_hit = True  # release 打包校验输入值

            # 返回 replace_assignment 的 release 载荷。
            return f"{match.group(1)}{placeholder}"

        # 整理 sanitize_release_text 需要的 updated 发布信息。
        updated = pattern.sub(replace_assignment, redacted)  # release 打包校验输入值

        # 校验 sanitize_release_text 的 release 分支条件。
        if bool_hit:

            # 追加 sanitize_release_text 的 release 诊断。
            list_matches.append({"rule": rule_name, "placeholder": placeholder})

            # 整理 sanitize_release_text 需要的 redacted 发布信息。
            redacted = updated  # release 打包校验输入值

    # 逐项检查 sanitize_release_text 发布候选。
    for rule_name, pattern in SANITIZED_INLINE_RULES:

        # 整理 sanitize_release_text 需要的 placeholder 发布信息。
        placeholder = SANITIZED_PLACEHOLDERS[rule_name]  # release 打包校验输入值

        # 整理 sanitize_release_text 需要的 updated、count 发布信息。
        updated, count = pattern.subn(placeholder, redacted)  # release 打包校验输入值

        # 校验 sanitize_release_text 的 release 分支条件。
        if count:

            # 追加 sanitize_release_text 的 release 诊断。
            list_matches.append({"rule": rule_name, "placeholder": placeholder})

            # 整理 sanitize_release_text 需要的 redacted 发布信息。
            redacted = updated  # release 打包校验输入值

    # 返回 sanitize_release_text 的 release 载荷。
    return redacted, list_matches

# 定义 detect_binary_sensitive_matches 的release 管理处理入口。
def detect_binary_sensitive_matches(data: bytes) -> list[str]:

    # 汇总 hits，作为 release 打包和清理候选清单。
    list_hits: list[str] = []  # release 打包校验输入值

    # 逐项检查 detect_binary_sensitive_matches 发布候选。
    for rule_name, pattern in SANITIZED_BINARY_PATTERNS:

        # 校验 detect_binary_sensitive_matches 的 release 分支条件。
        if pattern.search(data):

            # 追加 detect_binary_sensitive_matches 的 release 诊断。
            list_hits.append(rule_name)

    # 返回 detect_binary_sensitive_matches 的 release 载荷。
    return sorted(set(list_hits))

# 定义 sanitize_release_tree 的release 管理处理入口。
def sanitize_release_tree(profile: dict[str, Any], project_kind: str, skill_dir: Path, release_dir: Path) -> tuple[dict[str, Any], list[str]]:

    # 汇总 settings，作为 release 打包和清理候选清单。
    dict_settings = release_sanitization_settings(profile, project_kind)  # release 打包校验输入值

    # 保存 result 映射，维持 sanitize_release_tree 的字段关系。
    dict_result: dict[str, Any] = {  # release 打包校验输入值
        "enabled": dict_settings["required"],  # release 打包校验输入值
        "scope": dict_settings["scope"],  # release 打包校验输入值
        "mode": dict_settings["mode"],  # release 打包校验输入值
        "files": [],  # release 打包校验输入值
    }

    # 校验 sanitize_release_tree 的 release 分支条件。
    if dict_settings["receipt_required"]:

        # 整理 sanitize_release_tree 需要的 中间载荷 发布信息。
        dict_result["receipt_required"] = True  # release 打包校验输入值

    # 校验 sanitize_release_tree 的 release 分支条件。
    if not dict_settings["required"]:

        # 返回 sanitize_release_tree 的 release 载荷。
        return dict_result, []

    # 汇总 errors，作为 release 打包和清理候选清单。
    list_errors: list[str] = []  # release 打包校验输入值

    # 汇总 files，作为 release 打包和清理候选清单。
    list_files: list[dict[str, Any]] = []  # release 打包校验输入值

    # 逐项检查 sanitize_release_tree 发布候选。
    for source_path in sorted(skill_dir.rglob("*")):

        # 校验 sanitize_release_tree 的 release 分支条件。
        if not source_path.is_file():

            # 分隔 sanitize_release_tree 的控制流边界。
            continue

        # 定位 rel path 的文件边界，供 sanitize_release_tree 后续读写校验使用。
        rel_path = source_path.relative_to(skill_dir).as_posix()  # release 打包校验输入值

        # 校验 sanitize_release_tree 的 release 分支条件。
        if rel_path == "AGENTS.md":

            # 分隔 sanitize_release_tree 的控制流边界。
            continue

        # 定位 release path 的文件边界，供 sanitize_release_tree 后续读写校验使用。
        release_path = release_dir / rel_path  # release 打包校验输入值

        # 校验 sanitize_release_tree 的 release 分支条件。
        if not release_path.is_file():

            # 分隔 sanitize_release_tree 的控制流边界。
            continue

        # 整理 sanitize_release_tree 需要的 data 发布信息。
        dict_data = release_path.read_bytes()  # release 打包校验输入值

        # 校验 sanitize_release_tree 的 release 分支条件。
        if is_probably_text_bytes(dict_data):

            # 整理 sanitize_release_tree 需要的 text 发布信息。
            text = dict_data.decode("utf-8")  # release 打包校验输入值

            # 汇总 sanitized text、matches，作为 release 打包和清理候选清单。
            tuple_sanitized_text, tuple_matches = sanitize_release_text(text)  # release 打包校验输入值

            # 校验 sanitize_release_tree 的 release 分支条件。
            if tuple_matches:

                # 调用 write_text 处理 sanitize_release_tree。
                release_path.write_text(normalize_line_endings(tuple_sanitized_text), encoding="utf-8")

                # 追加 sanitize_release_tree 的 release 诊断。
                list_files.append(
                    {
                        "path": rel_path,
                        "rules": sorted({item["rule"] for item in tuple_matches}),
                        "placeholders": sorted({item["placeholder"] for item in tuple_matches}),
                        "sha256": sha256_file(release_path),
                    }
                )
        else:

            # 汇总 hits，作为 release 打包和清理候选清单。
            list_hits = detect_binary_sensitive_matches(dict_data)  # release 打包校验输入值

            # 校验 sanitize_release_tree 的 release 分支条件。
            if list_hits:

                # 追加 sanitize_release_tree 的 release 诊断。
                list_errors.append(f"binary file contains sensitive content and cannot be sanitized safely: {rel_path}")

    # 整理 sanitize_release_tree 需要的 中间载荷 发布信息。
    dict_result["files"] = list_files  # release 打包校验输入值

    # 返回 sanitize_release_tree 的 release 载荷。
    return dict_result, list_errors

# 定义 verify_release_sanitization 的release 管理处理入口。
def verify_release_sanitization(
    profile: dict[str, Any],
    project_kind: str,
    skill_dir: Path,
    release_dir: Path,
    receipt: dict[str, Any],
) -> list[str]:

    # 汇总 settings，作为 release 打包和清理候选清单。
    dict_settings = release_sanitization_settings(profile, project_kind)  # release 打包校验输入值

    # 校验 verify_release_sanitization 的 release 分支条件。
    if not dict_settings["required"]:

        # 返回 verify_release_sanitization 的 release 载荷。
        return []

    # 整理 verify_release_sanitization 需要的 sanitization 发布信息。
    sanitization = receipt.get("sanitization")  # release 打包校验输入值

    # 汇总 errors，作为 release 打包和清理候选清单。
    list_errors: list[str] = []  # release 打包校验输入值

    # 校验 verify_release_sanitization 的 release 分支条件。
    if not isinstance(sanitization, dict):

        # 返回 verify_release_sanitization 的 release 载荷。
        return ["release receipt sanitization block is missing"]

    # 校验 verify_release_sanitization 的 release 分支条件。
    if bool(sanitization.get("enabled")) is not True:

        # 追加 verify_release_sanitization 的 release 诊断。
        list_errors.append("release receipt sanitization enabled flag is missing or false")

    # 校验 verify_release_sanitization 的 release 分支条件。
    if str(sanitization.get("scope", "")).strip() != dict_settings["scope"]:

        # 追加 verify_release_sanitization 的 release 诊断。
        list_errors.append("release receipt sanitization scope does not match the release policy")

    # 校验 verify_release_sanitization 的 release 分支条件。
    if str(sanitization.get("mode", "")).strip() != dict_settings["mode"]:

        # 追加 verify_release_sanitization 的 release 诊断。
        list_errors.append("release receipt sanitization mode does not match the release policy")

    # 校验 verify_release_sanitization 的 release 分支条件。
    if dict_settings["receipt_required"] and bool(sanitization.get("receipt_required")) is not True:

        # 追加 verify_release_sanitization 的 release 诊断。
        list_errors.append("release receipt sanitization receipt_required flag is missing or false")

    # 汇总 files，作为 release 打包和清理候选清单。
    files = sanitization.get("files")  # release 打包校验输入值

    # 校验 verify_release_sanitization 的 release 分支条件。
    if not isinstance(files, list):

        # 返回 verify_release_sanitization 的 release 载荷。
        return ["release receipt sanitization files list is missing"]

    # 保存 declared 映射，维持 verify_release_sanitization 的字段关系。
    dict_declared: dict[str, dict[str, Any]] = {}  # release 打包校验输入值

    # 逐项检查 verify_release_sanitization 发布候选。
    for row in files:

        # 校验 verify_release_sanitization 的 release 分支条件。
        if not isinstance(row, dict):

            # 追加 verify_release_sanitization 的 release 诊断。
            list_errors.append("release receipt sanitization files list contains invalid entries")

            # 分隔 verify_release_sanitization 的控制流边界。
            continue

        # 定位 rel path 的文件边界，供 verify_release_sanitization 后续读写校验使用。
        rel_path = str(row.get("path", "")).strip()  # release 打包校验输入值

        # 校验 verify_release_sanitization 的 release 分支条件。
        if not rel_path:

            # 追加 verify_release_sanitization 的 release 诊断。
            list_errors.append("release receipt sanitization file entry is missing path")

            # 分隔 verify_release_sanitization 的控制流边界。
            continue

        # 汇总 rules，作为 release 打包和清理候选清单。
        rules = row.get("rules")  # release 打包校验输入值

        # 校验 verify_release_sanitization 的 release 分支条件。
        if not isinstance(rules, list) or not all(str(item).strip() for item in rules):

            # 追加 verify_release_sanitization 的 release 诊断。
            list_errors.append(f"release receipt sanitization rules are missing for {rel_path}")

        # 汇总 placeholders，作为 release 打包和清理候选清单。
        placeholders = row.get("placeholders")  # release 打包校验输入值

        # 校验 verify_release_sanitization 的 release 分支条件。
        if not isinstance(placeholders, list) or not all(str(item).strip() for item in placeholders):

            # 追加 verify_release_sanitization 的 release 诊断。
            list_errors.append(f"release receipt sanitization placeholders are missing for {rel_path}")

        # 整理 verify_release_sanitization 需要的 中间载荷 发布信息。
        dict_declared[rel_path] = row  # release 打包校验输入值

    # 整理 verify_release_sanitization 需要的 expected declared 发布信息。
    set_expected_declared: set[str] = set()  # release 打包校验输入值

    # 逐项检查 verify_release_sanitization 发布候选。
    for source_path in sorted(skill_dir.rglob("*")):

        # 校验 verify_release_sanitization 的 release 分支条件。
        if not source_path.is_file():

            # 分隔 verify_release_sanitization 的控制流边界。
            continue

        # 定位 rel path 的文件边界，供 verify_release_sanitization 后续读写校验使用。
        rel_path = source_path.relative_to(skill_dir).as_posix()  # release 打包校验输入值

        # 校验 verify_release_sanitization 的 release 分支条件。
        if rel_path == "AGENTS.md":

            # 分隔 verify_release_sanitization 的控制流边界。
            continue

        # 定位 release path 的文件边界，供 verify_release_sanitization 后续读写校验使用。
        release_path = release_dir / rel_path  # release 打包校验输入值

        # 校验 verify_release_sanitization 的 release 分支条件。
        if not release_path.is_file():

            # 分隔 verify_release_sanitization 的控制流边界。
            continue

        # 汇总 source bytes，作为 release 打包和清理候选清单。
        source_bytes = source_path.read_bytes()  # release 打包校验输入值

        # 汇总 release bytes，作为 release 打包和清理候选清单。
        release_bytes = release_path.read_bytes()  # release 打包校验输入值

        # 校验 verify_release_sanitization 的 release 分支条件。
        if is_probably_text_bytes(source_bytes):

            # 整理 verify_release_sanitization 需要的 source text 发布信息。
            source_text = source_bytes.decode("utf-8")  # release 打包校验输入值

            # 汇总 expected text、matches，作为 release 打包和清理候选清单。
            tuple_expected_text, tuple_matches = sanitize_release_text(source_text)  # release 打包校验输入值

            # 校验 verify_release_sanitization 的 release 分支条件。
            if tuple_matches:

                # 调用 add 处理 verify_release_sanitization。
                set_expected_declared.add(rel_path)

                # 校验 verify_release_sanitization 的 release 分支条件。
                if rel_path not in dict_declared:

                    # 追加 verify_release_sanitization 的 release 诊断。
                    list_errors.append(f"release receipt is missing sanitization record for {rel_path}")

                # 校验 verify_release_sanitization 的 release 分支条件。
                if not is_probably_text_bytes(release_bytes):

                    # 追加 verify_release_sanitization 的 release 诊断。
                    list_errors.append(f"sanitized release file is not valid UTF-8 text: {rel_path}")

                    # 分隔 verify_release_sanitization 的控制流边界。
                    continue

                # 整理 verify_release_sanitization 需要的 actual text 发布信息。
                actual_text = release_bytes.decode("utf-8")  # release 打包校验输入值

                # 校验 verify_release_sanitization 的 release 分支条件。
                if normalize_line_endings(actual_text) != normalize_line_endings(tuple_expected_text):

                    # 追加 verify_release_sanitization 的 release 诊断。
                    list_errors.append(f"sanitized release content mismatch for {rel_path}")

                # 整理 verify_release_sanitization 需要的 row 发布信息。
                row = dict_declared.get(rel_path)  # release 打包校验输入值

                # 校验 verify_release_sanitization 的 release 分支条件。
                if isinstance(row, dict):

                    # 校验 verify_release_sanitization 的 release 分支条件。
                    if str(row.get("sha256", "")).strip() != sha256_file(release_path):

                        # 追加 verify_release_sanitization 的 release 诊断。
                        list_errors.append(f"release receipt sanitization hash mismatch for {rel_path}")

            # 校验 verify_release_sanitization 的 release 分支条件。
            elif release_bytes != source_bytes:

                # 追加 verify_release_sanitization 的 release 诊断。
                list_errors.append(f"undeclared release diff outside sanitization receipt: {rel_path}")
        else:

            # 汇总 hits，作为 release 打包和清理候选清单。
            list_hits = detect_binary_sensitive_matches(source_bytes)  # release 打包校验输入值

            # 校验 verify_release_sanitization 的 release 分支条件。
            if list_hits:

                # 追加 verify_release_sanitization 的 release 诊断。
                list_errors.append(f"binary file contains sensitive content and cannot be sanitized safely: {rel_path}")

            # 校验 verify_release_sanitization 的 release 分支条件。
            elif release_bytes != source_bytes:

                # 追加 verify_release_sanitization 的 release 诊断。
                list_errors.append(f"undeclared binary release diff outside sanitization receipt: {rel_path}")

    # 整理 verify_release_sanitization 需要的 unexpected 发布信息。
    unexpected = sorted(set(dict_declared) - set_expected_declared)  # release 打包校验输入值

    # 逐项检查 verify_release_sanitization 发布候选。
    for rel_path in unexpected:

        # 追加 verify_release_sanitization 的 release 诊断。
        list_errors.append(f"release receipt declares unexpected sanitized file: {rel_path}")

    # 返回 verify_release_sanitization 的 release 载荷。
    return list_errors

# 定义 verify_release_content_policy 的release 管理处理入口。
def verify_release_content_policy(
    receipt: dict[str, Any],
    *,
    source_forbidden_paths: list[str],
    release_analysis: dict[str, Any],
    require_source_paths: bool,
) -> list[str]:

    # 汇总 errors，作为 release 打包和清理候选清单。
    errors = validate_recorded_release_content_policy(  # release 打包校验输入值
        receipt.get("release_content_policy"),  # release 打包校验输入值
        release_analysis,  # release 打包校验输入值
        forbidden_source_paths=source_forbidden_paths,  # release 打包校验输入值
        require_source_paths=require_source_paths,  # release 打包校验输入值
    )

    # 校验 verify_release_content_policy 的 release 分支条件。
    if release_analysis["unexpected_top_level_entries"]:

        # 追加 verify_release_content_policy 的 release 诊断。
        errors.append("release content policy rejected unexpected top-level release entries")

    # 校验 verify_release_content_policy 的 release 分支条件。
    if release_analysis["forbidden_paths"]:

        # 追加 verify_release_content_policy 的 release 诊断。
        errors.append("release content policy rejected forbidden development content in release")

    # 返回 verify_release_content_policy 的 release 载荷。
    return errors

# 定义 verify_release_receipt 的release 管理处理入口。
def verify_release_receipt(
    project: Path, receipt_path: Path, release_dir: Path,
    skill_name: str, version: str, source_rel: str,
    *, require_repo_dist: bool,
) -> list[str]:

    # 保存 receipt 映射，维持 verify_release_receipt 的字段关系。
    dict_receipt = read_release_receipt(receipt_path)  # release 打包校验输入值

    # 汇总 errors，作为 release 打包和清理候选清单。
    list_errors: list[str] = []  # release 打包校验输入值

    # 校验 verify_release_receipt 的 release 分支条件。
    if not dict_receipt:

        # 返回 verify_release_receipt 的 release 载荷。
        return [f"invalid release receipt: {display_path(receipt_path, project)}"]

    # 校验 verify_release_receipt 的 release 分支条件。
    if str(dict_receipt.get("skill_name", "")).strip() != skill_name:

        # 追加 verify_release_receipt 的 release 诊断。
        list_errors.append("release receipt skill_name does not match release directory")

    # 校验 verify_release_receipt 的 release 分支条件。
    if str(dict_receipt.get("version", "")).strip() != version:

        # 追加 verify_release_receipt 的 release 诊断。
        list_errors.append("release receipt version does not match requested release version")

    # 校验 verify_release_receipt 的 release 分支条件。
    if str(dict_receipt.get("source_path", "")).strip().replace("\\", "/") != source_rel:

        # 追加 verify_release_receipt 的 release 诊断。
        list_errors.append("release receipt source_path does not match skill source path")

    # 整理 verify_release_receipt 需要的 expected validation 发布信息。
    expected_validation = "strong" if require_repo_dist else "reduced_assurance"  # release 打包校验输入值

    # 校验 verify_release_receipt 的 release 分支条件。
    if str(dict_receipt.get("validation_level", "")).strip() != expected_validation:

        # 追加 verify_release_receipt 的 release 诊断。
        list_errors.append("release receipt validation_level is inconsistent with the release source")

    # 汇总 expected files，作为 release 打包和清理候选清单。
    list_expected_files = build_release_file_manifest(release_dir, exclude={receipt_path.name})  # release 打包校验输入值

    # 汇总 actual files，作为 release 打包和清理候选清单。
    actual_files = dict_receipt.get("files")  # release 打包校验输入值

    # 校验 verify_release_receipt 的 release 分支条件。
    if not isinstance(actual_files, list):

        # 追加 verify_release_receipt 的 release 诊断。
        list_errors.append("release receipt files list is missing")
    else:

        # 汇总 filtered，作为 release 打包和清理候选清单。
        list_filtered = []  # release 打包校验输入值

        # 逐项检查 verify_release_receipt 发布候选。
        for item in actual_files:

            # 校验 verify_release_receipt 的 release 分支条件。
            if not isinstance(item, dict):

                # 追加 verify_release_receipt 的 release 诊断。
                list_errors.append("release receipt files list contains invalid entries")

                # 分隔 verify_release_receipt 的控制流边界。
                continue

            # 追加 verify_release_receipt 的 release 诊断。
            list_filtered.append({"path": str(item.get("path", "")).strip(), "sha256": str(item.get("sha256", "")).strip()})

        # 校验 verify_release_receipt 的 release 分支条件。
        if list_filtered != list_expected_files:

            # 追加 verify_release_receipt 的 release 诊断。
            list_errors.append("release receipt file manifest does not match packaged release contents")

    # 返回 verify_release_receipt 的 release 载荷。
    return list_errors

# 定义 current_branch_and_locals 的release 管理处理入口。
def current_branch_and_locals(project: Path) -> tuple[str, list[str], list[str]]:

    # 整理 current_branch_and_locals 需要的 git branch result 发布信息。
    completed_process_git_branch_result = run_git(project, ["branch", "--show-current"])  # release 打包校验输入值

    # 整理 current_branch_and_locals 需要的 git list result 发布信息。
    completed_process_git_list_result = run_git(project, ["branch", "--list"])  # release 打包校验输入值

    # 整理 current_branch_and_locals 需要的 git status result 发布信息。
    completed_process_git_status_result = run_git(project, ["status", "--short"])  # release 打包校验输入值

    # 校验 current_branch_and_locals 的 release 分支条件。
    if any(result.returncode != 0 for result in [completed_process_git_branch_result, completed_process_git_list_result, completed_process_git_status_result]):

        # 返回 current_branch_and_locals 的 release 载荷。
        return "", [], []

    # 整理 current_branch_and_locals 需要的 current branch 发布信息。
    current_branch = completed_process_git_branch_result.stdout.strip()  # release 打包校验输入值

    # 汇总 local branches，作为 release 打包和清理候选清单。
    local_branches = sorted(normalize_branch_list_line(line) for line in completed_process_git_list_result.stdout.splitlines() if line.strip())  # release 打包校验输入值

    # 汇总 status lines，作为 release 打包和清理候选清单。
    list_status_lines = filter_runtime_status_lines(completed_process_git_status_result.stdout.splitlines())  # release 打包校验输入值

    # 返回 current_branch_and_locals 的 release 载荷。
    return current_branch, local_branches, list_status_lines

# 定义 release_prepare 的release 管理处理入口。
