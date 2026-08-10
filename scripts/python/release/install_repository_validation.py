"""验证发布目录对应的源码仓库、Git 状态和收据证据。"""

# 标准库提供进程执行、路径和可注入调用类型。
from collections.abc import Callable
from pathlib import Path
import subprocess
from typing import Any

# 发布清单模块提供基础收据、内容策略和 worktree 合同。
from install_release_manifest import (
    ACTIVE_SESSION_PATH,
    POLICY_VERSION,
    analyze_release_content_root,
    file_manifest,
    inspect_worktree_policy,

    # 身份和收据读取函数建立发布包基础事实。
    parse_release_dir,
    read_receipt,
    validate_recorded_release_content_policy,
    validate_release_completeness,
)

# 清洗模块复核发布包的脱敏证据。
from install_release_sanitization import validate_release_sanitization

# 可注入的进程调用器返回具有 returncode/stdout 字段的结果。
ProcessRunner = Callable[..., Any]  # Git 子进程执行合同。

# 分支列表规范化器移除当前分支和 worktree 标记。
def normalize_branch_list_line(str_line: str) -> str:
    """规范化 git branch --list 的单行输出。

    参数：str_line 为 Git 分支列表原始行。
    返回：不含状态标记和两端空白的分支名。
    """

    # Git 使用星号和加号标记当前或其他 worktree 分支。
    return str_line.strip().lstrip("*+ ").strip()

# 状态路径解析器同时支持普通条目和重命名条目。
def parse_status_paths(str_line: str) -> list[str]:
    """提取 git status --short 行涉及的相对路径。

    参数：str_line 为短状态原始行。
    返回：使用 POSIX 分隔符的一个或两个路径。
    """

    # 前三个字符是 XY 状态列和分隔空格。
    str_body = str_line[3:].strip() if len(str_line) >= 4 else str_line.strip()  # 去除状态列后的路径文本。

    # 重命名条目同时包含旧路径和新路径。
    if " -> " in str_body:

        # 首个箭头分隔源路径和目标路径。
        str_old_path, str_new_path = str_body.split(" -> ", 1)  # 重命名两侧路径。

        # 路径分隔符规范化便于跨平台过滤。
        return [str_old_path.strip().replace("\\", "/"), str_new_path.strip().replace("\\", "/")]

    # 普通状态条目只包含一个路径。
    return [str_body.replace("\\", "/")]

# 运行时状态过滤器忽略仅由治理命令维护的活跃会话文件。
def filter_runtime_status_lines(list_lines: list[str]) -> list[str]:
    """过滤不应阻断强发布验证的运行时状态行。

    参数：list_lines 为 git status --short 输出行。
    返回：仍代表真实未提交改动的原始状态行。
    """

    # 活跃会话文件按 POSIX 路径与 Git 输出比较。
    set_ignored = {ACTIVE_SESSION_PATH.as_posix()}  # 允许存在的运行时状态路径。

    # 保留原始状态行供调用方判断工作区是否干净。
    list_filtered: list[str] = []  # 未被运行时例外覆盖的状态行。

    # 每行独立提取路径并排除空白输出。
    for str_line in list_lines:

        # 空行不代表仓库改动。
        if not str_line.strip():

            # 继续检查下一行。
            continue

        # 重命名任一侧不是忽略文件时仍应保留该状态。
        list_paths = [
            str_path  # 当前有效状态路径。
            for str_path in parse_status_paths(str_line)  # 状态行涉及的全部路径。
            if str_path and str_path not in set_ignored  # 排除空值和运行时例外。
        ]  # 当前状态行的非例外路径。

        # 至少一个真实路径意味着工作区不干净。
        if list_paths:

            # 保留 Git 原始状态文本用于稳定判断。
            list_filtered.append(str_line)

    # 空列表表示仅有允许的运行时状态或完全干净。
    return list_filtered

# 仓库推断器只接受仓库根 dist 下的版本化发布目录。
def infer_repo_root(path_release_dir: Path) -> Path | None:
    """推断发布目录所属的本地 Git 仓库根。

    参数：path_release_dir 为待安装发布包根目录。
    返回：严格匹配时返回仓库根，否则返回 None。
    """

    # 任一发布路径链接都会破坏 dist 布局与实际内容的对应关系。
    try:

        # absolute 保留链接形态，resolve 用于发现父目录链接逃逸。
        if path_release_dir.absolute() != path_release_dir.resolve():

            # 不能证明发布内容位于声明的仓库 dist 中。
            return None

    # 无法规范化路径时降级为外部发布包。
    except (OSError, RuntimeError):

        # 不把异常路径当作强来源证据。
        return None

    # 外部复制不位于固定 dist 布局，使用降低保证度验证。
    if path_release_dir.parent.name != "dist":

        # 无法从目录布局建立源码关联。
        return None

    # dist 的父目录是预期仓库根。
    path_candidate_root = path_release_dir.parent.parent  # 布局推断的仓库根候选。

    # 不存在路径不可能是当前本地仓库。
    if not path_candidate_root.exists():

        # 按外部包处理。
        return None

    # Git 自身提供权威顶层目录。
    process_root = subprocess.run(  # Git 仓库根查询结果。
        ["git", "rev-parse", "--show-toplevel"],  # Git 仓库根查询命令。
        cwd=path_candidate_root,  # 在布局候选根执行。
        text=True,  # 标准输出按文本读取。
        capture_output=True,  # 捕获输出用于无噪声判断。
        check=False,  # 非仓库状态由返回码处理。
    )  # 完成权威 Git 顶层路径查询。

    # Git 查询失败时不能建立强来源关系。
    if process_root.returncode != 0:

        # 降级为外部发布包。
        return None

    # Git 输出可能包含平台特定路径表示。
    try:

        # 规范化实际 Git 根后比较路径身份。
        path_git_root = Path(process_root.stdout.strip()).resolve()  # Git 报告的仓库根。

    # 非法路径文本不能作为强验证依据。
    except (OSError, RuntimeError):

        # 无法证明来源时采用降低保证度。
        return None

    # 只有布局候选与 Git 根完全一致才返回强来源。
    return path_git_root if path_git_root == path_candidate_root.resolve() else None

# 源技能路径解析器约束收据 source_path 不得逃逸仓库根。
def source_skill_dir_from_receipt(
    path_repo_root: Path,
    dict_receipt: dict[str, Any],
    str_expected_skill_name: str | None = None,
) -> Path | None:
    """从发布收据解析安全的源码技能目录。

    参数：path_repo_root 为已确认仓库根，dict_receipt 为收据对象。
    参数：str_expected_skill_name 为发布目录声明的技能名。
    返回：存在且位于仓库根内的源码目录，否则返回 None。
    """

    # source_path 为空时收据未提供源码关联。
    str_source_path = str(dict_receipt.get("source_path", "")).strip()  # 收据声明的源码相对路径。

    # 空声明无法定位源码技能。
    if not str_source_path:

        # 调用方将按无源码关联处理。
        return None

    # absolute 保留收据路径形态，resolve 用于发现父目录或自身链接。
    path_unresolved = path_repo_root / str_source_path  # 收据声明的未规范化源码路径。

    # 任一源码路径链接都会削弱发布包与工作树的身份对应关系。
    try:

        # 只有没有链接逃逸的路径才允许建立强来源关联。
        if path_unresolved.absolute() != path_unresolved.resolve():

            # 链接路径不作为强来源证据使用。
            return None

        # resolve 同时折叠父目录片段并得到源码候选根。
        path_candidate = path_unresolved.resolve()  # 规范化源码技能候选路径。

    # 无法规范化的收据路径不能建立强来源关联。
    except (OSError, RuntimeError):

        # 异常路径统一按缺少可信源码处理。
        return None

    # 缺失候选不能用于源码对照。
    if not path_candidate.is_dir():

        # 返回空状态表示来源不可用。
        return None

    # 发布身份已给出时，源码目录叶节点必须与发布技能名一致。
    if str_expected_skill_name:

        # 不能用仓库内其他技能替代当前发布源。
        if path_candidate.name != str_expected_skill_name:

            # 错配目录不提供当前发布的强来源证据。
            return None

        # 源码目录必须携带普通 SKILL.md 才能证明技能身份。
        path_skill_file = path_candidate / "SKILL.md"  # 源码技能声明文件。

        # 声明链接或缺失声明都不能提供强来源证据。
        if path_skill_file.is_symlink() or not path_skill_file.is_file():

            # 继续按无可信源码关联处理。
            return None

    # 路径必须位于规范化仓库根内。
    try:

        # relative_to 成功即证明 containment。
        path_candidate.relative_to(path_repo_root.resolve())

    # 父目录或符号链接逃逸会触发 ValueError。
    except ValueError:

        # 越界 source_path 不得被读取。
        return None

    # 返回已证明安全且存在的源码目录。
    return path_candidate

# Git 检查助手以一致参数执行单个只读命令。
def run_git_inspection(
    callable_runner: ProcessRunner,
    path_repo_root: Path,
    list_arguments: list[str],
) -> Any:
    """运行单个只读 Git 状态命令。

    参数：callable_runner 为进程执行器，path_repo_root 为仓库根。
    参数：list_arguments 为 git 后的命令参数。
    返回：进程执行器结果对象。
    """

    # 所有强验证 Git 调用共享文本捕获和非抛错合同。
    return callable_runner(
        ["git", *list_arguments],  # 完整 Git 命令。
        cwd=path_repo_root,  # 经确认的源码仓库根。
        text=True,  # 分支和状态按文本解析。
        capture_output=True,  # 捕获标准输出和错误。
        check=False,  # 返回码由验证器统一判断。
    )

# 强来源验证器要求单 worktree、固定分支集合和干净提交状态。
def verify_repo_release_state(
    path_repo_root: Path,
    *,
    worktree_inspector: Callable[[Path], dict[str, Any]] | None = None,
    process_runner: ProcessRunner | None = None,
) -> list[str]:
    """验证本地源码仓库满足强发布安装条件。

    参数：path_repo_root 为源码仓库根，worktree_inspector 为可选策略替身。
    参数：process_runner 为可选 Git 进程替身。
    返回：强验证错误列表，通过时为空。
    """

    # 可注入边界支持确定性单元测试。
    func_worktree_inspector = worktree_inspector or inspect_worktree_policy  # 实际 worktree 检查器。

    # 默认使用标准 subprocess.run 执行只读 Git 命令。
    callable_process_runner = process_runner or subprocess.run  # 实际 Git 进程执行器。

    # worktree 污染是优先级最高的硬阻断。
    dict_worktree_policy = func_worktree_inspector(path_repo_root)  # 当前仓库 worktree 策略报告。

    # 硬阻断时不再用分支或状态错误稀释根因。
    if dict_worktree_policy.get("hard_blocking", False):

        # 返回单一稳定诊断。
        return ["strong install validation rejected Git worktree policy violations"]

    # 三个 Git 查询共同证明分支和工作区状态。
    process_branch = run_git_inspection(callable_process_runner, path_repo_root, ["branch", "--show-current"])  # 当前分支结果。

    # 本地分支列表验证发布治理拓扑。
    process_branches = run_git_inspection(callable_process_runner, path_repo_root, ["branch", "--list"])  # 本地分支列表结果。

    # 短状态输出验证工作区清洁性。
    process_status = run_git_inspection(callable_process_runner, path_repo_root, ["status", "--short"])  # 工作区状态结果。

    # 任一 Git 命令失败都使强验证证据不完整。
    if any(
        process_item.returncode != 0  # 当前 Git 检查失败。
        for process_item in (process_branch, process_branches, process_status)  # 三项必要检查结果。
    ):

        # 不基于不完整输出继续推断具体状态。
        return ["unable to inspect repository git state for strong release install validation"]

    # 收集可独立报告的强治理错误。
    list_errors: list[str] = []  # 源码仓库强验证诊断。

    # 当前分支名称直接来自 Git 标准输出。
    str_current_branch = process_branch.stdout.strip()  # 当前检出分支。

    # 规范化并排序本地分支提供确定性比较。
    list_local_branches = sorted(  # 当前本地分支集合。
        normalize_branch_list_line(str_line)  # 去除 Git 状态标记后的分支名。
        for str_line in process_branches.stdout.splitlines()  # Git 本地分支原始行。
        if str_line.strip()  # 忽略空白行。
    )  # 完成本地分支名称规范化和排序。

    # 活跃会话状态例外不应阻断干净提交验证。
    list_status_lines = filter_runtime_status_lines(process_status.stdout.splitlines())  # 真实未提交状态行。

    # 强发布来源必须从 master 分支生成。
    if str_current_branch != "master":

        # 分支错误独立记录。
        list_errors.append("strong install validation requires current branch master")

    # 本地只允许 master 和 release 两条治理分支。
    if list_local_branches != ["master", "release"]:

        # 额外或缺失分支都会阻断强安装。
        list_errors.append("strong install validation requires only local branches master and release")

    # 除活跃会话例外外不得有未提交改动。
    if list_status_lines:

        # 发布包必须对应已提交源码状态。
        list_errors.append("strong install validation requires a clean committed worktree")

    # 返回全部独立 Git 治理诊断。
    return list_errors

# 文件清单验证器把收据条目规范化后与实际目录比较。
def validate_receipt_file_manifest(
    path_release_dir: Path,
    path_receipt: Path,
    dict_receipt: dict[str, Any],
    list_errors: list[str],
) -> None:
    """验证收据 files 字段与发布目录完全一致。

    参数：path_release_dir、path_receipt 和 dict_receipt 描述发布包。
    参数：list_errors 为共享诊断列表。
    返回：无，错误追加到 list_errors。
    """

    # 实际清单排除自描述的发布收据。
    list_expected_files = file_manifest(path_release_dir, exclude={path_receipt.name})  # 实际发布文件清单。

    # 收据 files 字段必须是列表。
    object_actual_files = dict_receipt.get("files")  # 原始收据文件清单。

    # 非列表字段无法进行完整清单比较。
    if not isinstance(object_actual_files, list):

        # 明确报告缺少 files 列表。
        list_errors.append("release receipt files list is missing")

        # 无有效条目可继续规范化。
        return

    # 规范化后的条目只保留 path 和 sha256 合同字段。
    list_normalized: list[dict[str, str]] = []  # 收据文件清单规范化结果。

    # 每个原始条目独立验证类型。
    for object_item in object_actual_files:

        # 非对象条目不能提供文件证据。
        if not isinstance(object_item, dict):

            # 保留错误并继续发现其他无效条目。
            list_errors.append("release receipt files list contains invalid entries")

            # 跳过当前无效值。
            continue

        # 字段统一转为去空白字符串。
        list_normalized.append(
            {
                "path": str(object_item.get("path", "")).strip(),  # 收据相对路径。
                "sha256": str(object_item.get("sha256", "")).strip(),  # 收据内容摘要。
            }
        )

    # 顺序、路径或摘要任一差异都使收据不匹配。
    if list_normalized != list_expected_files:

        # 单一诊断覆盖缺失、额外和摘要漂移。
        list_errors.append("release receipt file manifest does not match release directory contents")

# 发布内容策略验证器同时复核源码和发布包扫描证据。
def validate_release_content(
    path_release_dir: Path,
    path_source_skill: Path | None,
    dict_receipt: dict[str, Any],
    dict_release_content: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """验证发布内容策略及其收据记录。

    参数：path_release_dir 和 path_source_skill 标识发布与可选源码。
    参数：dict_receipt 和 dict_release_content 提供收据及实际扫描。
    返回：策略错误与源码禁止路径两个列表。
    """

    # 无源码关联时禁止路径证据保持空列表。
    list_source_forbidden_paths: list[str] = []  # 源码中允许清洗但需记录的路径。

    # 强验证可扫描源码侧开发内容。
    if path_source_skill is not None:

        # 源码扫描允许仓库本地开发文件存在，但仍记录它们。
        dict_source_content = analyze_release_content_root(  # 源码内容策略扫描结果。
            path_source_skill,  # 收据关联源码技能根。
            allow_source_only_repo_local=True,  # 源码侧允许仓库本地内容。
        )  # 完成源码侧仓库本地内容扫描。

        # 收据策略验证需要源码禁止路径证据。
        list_source_forbidden_paths = list(dict_source_content["forbidden_paths"])  # 源码禁止路径证据。

    # 公共策略验证器复核版本、扫描结果和源码证据。
    list_policy_errors = validate_recorded_release_content_policy(  # 发布内容策略诊断。
        dict_receipt.get("release_content_policy"),  # 收据记录的策略块。
        dict_release_content,  # 实际发布包扫描结果。
        forbidden_source_paths=list_source_forbidden_paths,  # 收据应记录的源码扫描路径。
        require_source_paths=path_source_skill is not None,  # 强验证要求源码证据。
    )  # 完成记录策略与实际扫描结果比对。

    # 发布根不得出现策略外顶层成员。
    if dict_release_content["unexpected_top_level_entries"]:

        # 顶层污染独立报告。
        list_policy_errors.append("release content policy rejected unexpected top-level release entries")

    # 发布副本绝不允许携带开发内容。
    if dict_release_content["forbidden_paths"]:

        # 禁止内容独立报告。
        list_policy_errors.append("release content policy rejected forbidden development content in release")

    # 新版受管理技能的公开文件和 README 插图也必须通过发布门禁。
    if dict_release_content.get("public_skill_required") and dict_release_content.get("public_skill_errors"):

        # 公开文件合同的每条错误都要进入安装阻断结果。
        list_policy_errors.extend(
            f"public skill package contract: {str_error}"
            for str_error in dict_release_content["public_skill_errors"]
        )

    # 两个列表分别用于结果载荷和最终 errors。
    return list_policy_errors, list_source_forbidden_paths

# 公共入口汇总目录名、收据、源码、清洗、Git 和内容策略证据。
def validate_release_dir(path_release_dir: Path) -> dict[str, Any]:
    """完整验证版本化技能发布目录。

    参数：path_release_dir 为待安装发布包根目录。
    返回：包含来源强度、策略证据和错误列表的结构化报告。
    """

    # 目录名提供预期技能名和版本号。
    str_skill_name, str_version = parse_release_dir(path_release_dir)  # 发布目录身份。

    # 收据路径和对象共同用于后续全部证据复核。
    path_receipt, dict_receipt = read_receipt(path_release_dir)  # 发布收据文件及数据。

    # 所有验证层共享一个有序错误列表。
    list_errors: list[str] = []  # 发布目录完整验证诊断。

    # 实际发布内容扫描只执行一次并供策略与结果复用。
    dict_release_content = analyze_release_content_root(path_release_dir)  # 发布内容策略扫描结果。

    # 收据技能名必须与版本化目录名称一致。
    if str(dict_receipt.get("skill_name", "")).strip() != str_skill_name:

        # 身份不一致时拒绝安装。
        list_errors.append("release receipt skill_name does not match release directory name")

    # 收据版本必须与目录版本完全一致。
    if str(dict_receipt.get("version", "")).strip() != str_version:

        # 版本漂移会破坏发布历史身份。
        list_errors.append("release receipt version does not match release directory version")

    # 逐文件清单证明收据覆盖实际发布内容。
    validate_receipt_file_manifest(path_release_dir, path_receipt, dict_receipt, list_errors)

    # 只有仓库根 dist 布局可建立强来源。
    path_repo_root = infer_repo_root(path_release_dir)  # 可选源码仓库根。

    # 来源关系决定安装验证强度。
    str_validation_level = "strong" if path_repo_root is not None else "reduced_assurance"  # 实际验证级别。

    # 结果载荷明确区分仓库发布和外部复制。
    str_provenance_mode = "repository-dist" if path_repo_root is not None else "external-copy"  # 发布来源模式。

    # 收据必须诚实声明实际可达到的验证强度。
    if str(dict_receipt.get("validation_level", "")).strip() != str_validation_level:

        # 来源与声明不一致时阻断安装。
        list_errors.append("release receipt validation_level does not match the installation source")

    # 清洗证据根据是否存在源码关联自动选择验证强度。
    validate_release_sanitization(
        path_release_dir,  # 发布包根。
        path_receipt,  # 发布收据路径。
        dict_receipt,  # 发布收据对象。
        path_repo_root,  # 清洗验证可用的源码仓库根。
        list_errors,  # 共享验证诊断。
        str_skill_name,  # 发布目录声明的技能名。
    )

    # 强来源还必须满足 Git 仓库治理条件。
    if path_repo_root is not None:

        # worktree、分支和清洁性错误加入统一列表。
        list_errors.extend(verify_repo_release_state(path_repo_root))

    # 安全解析收据关联的源码技能目录。
    path_source_skill: Path | None = None  # 可选源码技能根。

    # 外部发布包没有仓库根，不解析收据源码路径。
    if path_repo_root is not None:

        # 强来源仅关联与发布名一致的源码目录。
        path_source_skill = source_skill_dir_from_receipt(  # 解析发布包对应的源码根。
            path_repo_root,  # 已确认的仓库根。
            dict_receipt,  # 读取当前包的脱敏和内容策略记录。
            str_skill_name,  # 绑定当前版本目录的身份键。
        )  # 强来源下的源码技能目录。

    # 内容策略复核发布扫描和可选源码证据。
    tuple_content_validation = validate_release_content(  # 内容策略诊断和源码禁止路径二元组。
        path_release_dir,  # 内容策略目标发布包根。
        path_source_skill,  # 策略证据关联的源码技能根。
        dict_receipt,  # 内容策略收据记录。
        dict_release_content,  # 发布内容实际扫描证据。
    )  # 完成内容策略和源码证据联合复核。

    # 首项是阻断安装的内容策略诊断。
    list_policy_errors = tuple_content_validation[0]  # 发布内容策略错误。

    # 次项是需要写入验证结果的源码禁止路径。
    list_source_forbidden_paths = tuple_content_validation[1]  # 源码内容策略证据。

    # 内容策略错误进入最终安装阻断列表。
    list_errors.extend(list_policy_errors)

    # SKILL.md 引用和必需收据条目提供最后一层完整性检查。
    list_errors.extend(validate_release_completeness(path_release_dir, dict_receipt))

    # 结构化结果同时服务 CLI 输出和测试断言。
    return {
        "skill_name": str_skill_name,  # 已验证目录技能名。
        "version": str_version,  # 已验证目录版本。
        "receipt_path": str(path_receipt),  # 发布收据绝对路径。
        "repo_root": str(path_repo_root) if path_repo_root else "",  # 可选来源仓库根。
        "validation_level": str_validation_level,  # strong 或 reduced_assurance。
        "provenance_mode": str_provenance_mode,  # 当前安装来源模式。
        "policy_version": POLICY_VERSION,  # 当前发布内容策略版本。
        "forbidden_source_paths": list_source_forbidden_paths,  # 收据关联源码的禁止路径。
        "forbidden_release_paths": dict_release_content["forbidden_paths"],  # 发布包禁止路径。
        "release_content_policy_ok": not list_policy_errors,  # 内容策略是否完全通过。
        "errors": list_errors,  # 所有安装阻断诊断。
    }
