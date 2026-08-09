"""发布打包。"""

# 延迟解析分片注解，使该模块既可聚合加载也可独立导入。
from __future__ import annotations

# 独立导入时显式提供结果路径格式化函数。
from agents_common import display_path
from release_content_policy import POLICY_VERSION

# 聚合加载时保存已注入的真实 hook，独立加载时记录为空。
func_aggregate_release_gate = globals().get("release_gate")  # 分片加载前已有的发布门禁。

# 独立模块公开可替换入口，聚合运行时继续复用原始实现。
def release_gate(
    project: Path,
    version: str,
    skill_dir_raw: str,
    phase: str,
    install_intent: str,
    test_evidence_raw: str = "",
    bool_require_test_evidence: bool = False,
) -> dict[str, Any]:
    """把独立模块调用转交给聚合发布门禁。

    参数：project、version 和 skill_dir_raw 定位发布目标。
    参数：phase 与 install_intent 描述门禁阶段和安装意图。
    参数：test_evidence_raw 非空时启用发布态测试收据透传。
    参数：bool_require_test_evidence 为 True 时拒绝缺失收据。
    返回：聚合发布门禁的结构化验证结果。
    """

    # 分片聚合加载已经提供真实实现时避免重新进入聚合器。
    if callable(func_aggregate_release_gate):

        # 参数原样转发到分片加载前保存的实现。
        if test_evidence_raw or bool_require_test_evidence:

            # 发布态调用透传同一不透明测试收据。
            return func_aggregate_release_gate(
                project,  # 聚合门禁所属仓库。
                version,  # 待验证发布版本。

                # 下组参数固定发布源和阶段语义。
                skill_dir_raw,  # 聚合门禁技能目录。
                phase,  # 聚合门禁 pre/post 阶段。

                # 安装与测试证据状态必须共同透传。
                install_intent,  # 聚合门禁安装意图。
                test_evidence_raw,  # 聚合门禁收据输入。
                bool_require_test_evidence,  # 聚合门禁收据必需状态。
            )

        # 无收据调用保持既有开发态 hook 合同。
        return func_aggregate_release_gate(project, version, skill_dir_raw, phase, install_intent)

    # 独立真实调用才加载完整聚合运行时，导入阶段保持无副作用。
    from manage_docs_release import release_gate as func_release_gate

    # 参数原样转发，保持模块级 hook 的可替换合同。
    if test_evidence_raw or bool_require_test_evidence:

        # 独立模块的发布态调用同样透传收据。
        return func_release_gate(
            project,  # 独立门禁所属仓库。
            version,  # 独立门禁发布版本。

            # 下组参数固定独立门禁的源码和阶段。
            skill_dir_raw,  # 独立门禁技能目录。
            phase,  # 独立门禁 pre/post 阶段。

            # 安装与测试证据保持和聚合入口相同。
            install_intent,  # 独立门禁安装意图。
            test_evidence_raw,  # 独立门禁收据输入。
            bool_require_test_evidence,  # 独立门禁收据必需状态。
        )

    # 无收据调用保持旧五参数入口。
    return func_release_gate(project, version, skill_dir_raw, phase, install_intent)

# 失败结果助手统一发布准备的机器协议。
def prepare_failure(list_errors: list[str], dict_checks: dict[str, Any]) -> dict[str, Any]:
    """构造发布准备失败结果。

    参数：list_errors 为诊断，dict_checks 为证据。
    返回：稳定失败结果。
    """

    # 统一结果形态简化各阶段提前返回。
    return {"ok": False, "errors": list_errors, "checks": dict_checks}

# 分支检查器决定当前拓扑是否可自动准备。
def check_prepare_branches(
    str_current_branch: str,
    list_local_branches: list[str],
    list_protected: list[str],
    dict_checks: dict[str, Any],
) -> dict[str, Any] | None:
    """验证发布准备的本地分支拓扑。

    参数：str_current_branch、list_local_branches 和 list_protected 描述分支状态。
    参数：dict_checks 为返回结果携带的证据。
    返回：可继续时为 None，否则为完整结果。
    """

    # 缺少分支事实表示仓库不可读。
    if not str_current_branch and not list_local_branches:

        # 不执行任何 Git 副作用。
        return prepare_failure(["release prepare requires a readable local git repository"], dict_checks)

    # 保护分支之外的成员是临时开发分支。
    list_extras = sorted(  # 当前临时开发分支集合。
        str_branch for str_branch in list_local_branches if str_branch not in list_protected  # 临时分支
    )  # 完成本地临时分支筛选和排序。

    # master 只在没有临时分支时视为已经准备完成。
    if str_current_branch == "master":

        # 无临时分支可直接返回成功。
        if not list_extras:

            # checks 仍保留当前分支事实。
            return {"ok": True, "errors": [], "checks": dict_checks}

        # 多个候选需要用户决定合并顺序。
        if len(list_extras) > 1:

            # 回显完整候选集合。
            str_error = (
                "multiple extra local branches require manual resolution before release prepare: "
                f"{list_extras}"
            )  # 多临时分支诊断。

        # 单个候选也不能从 master 推断用户意图。
        else:

            # 回显唯一候选分支。
            str_error = (
                "master cannot guess which extra local branch to prepare automatically: "
                f"{list_extras[0]}"
            )  # master 临时分支诊断。

        # master 拓扑异常统一返回失败。
        return prepare_failure([str_error], dict_checks)

    # release 等保护分支不能被当作开发分支。
    if str_current_branch in list_protected:

        # 明确报告实际保护分支。
        str_error = (
            "release prepare only handles temporary development branches, "
            f"found protected branch {str_current_branch}"
        )  # 保护分支诊断。

        # 返回分支类型错误。
        return prepare_failure([str_error], dict_checks)

    # 自动准备要求当前分支是唯一临时分支。
    if list_extras != [str_current_branch]:

        # 不确定拓扑不得自动合并。
        str_error = (
            "release prepare requires exactly one temporary development branch, "
            f"found {list_extras}"
        )  # 临时分支拓扑诊断。

        # 返回可操作的分支集合。
        return prepare_failure([str_error], dict_checks)

    # None 表示可继续同步和提交。
    return None

# 根规则同步器在提交前刷新受管 AGENTS 元数据。
def sync_prepare_agents(
    path_project: Path,
    path_skill_dir: Path,
    dict_checks: dict[str, Any],
) -> list[str]:
    """同步发布准备所需的根 AGENTS.md。

    参数：path_project 和 path_skill_dir 定位项目及技能。
    参数：dict_checks 原位记录同步证据。
    返回：同步错误列表。
    """

    # 缺少根规则时记录跳过而不擅自创建。
    if not (path_project / "AGENTS.md").exists():

        # 中性证据保持调用方字段稳定。
        dict_checks["root_agents_sync"] = {
            "updated": False,  # 根规则未发生同步。
            "reasons": ["missing_root_agents_md"],  # 同步跳过原因。
            "skipped": True,  # 明确同步步骤未运行。
        }

        # 其他治理入口负责判断缺失文件是否阻断。
        return []

    # 自举仓库使用当前技能源码作为同步实现。
    path_override = path_skill_dir if path_skill_dir.name == "agents-md-generator" else None  # 可选同步技能覆盖目录。

    # 写模式同步根规则版本和验证时间。
    dict_sync = sync_root_agents(  # 根 AGENTS 同步报告。
        path_project,  # 待同步项目根。
        write=True,  # 写入最新根规则元数据。
        installed_skill_dir_override=path_override,  # 自举仓库实现覆盖目录。
    )  # 完成根规则写入式同步。

    # checks 只公开稳定证据字段。
    dict_checks["root_agents_sync"] = {
        "updated": dict_sync.get("updated", False),  # 根规则是否被刷新。
        "reasons": dict_sync.get("reasons", []),  # 同步器报告的具体原因。
    }

    # 保留同步器的具体错误文本。
    return list(dict_sync.get("errors", []))

# 改动提交器限制自动暂存范围并创建准备提交。
def commit_prepare_changes(
    path_project: Path,
    path_skill_dir: Path,
    dict_profile: dict[str, Any],
    str_branch: str,
    str_version: str,
) -> list[str]:
    """暂存并提交发布治理范围内的改动。

    参数：path_project、path_skill_dir 和 dict_profile 定义治理范围。
    参数：str_branch 和 str_version 定义提交身份。
    返回：暂存或提交错误列表。
    """

    # 配置和技能路径共同决定允许自动提交的 pathspec。
    list_allowed = governed_allowed_paths(dict_profile, path_skill_dir, path_project)  # 允许发布路径模式。

    # 读取工作区全部变化和解析错误。
    list_changed, list_changed_errors = changed_paths(path_project)  # 改动路径与 Git 诊断。

    # 无法完整读取状态时停止。
    if list_changed_errors:

        # 防止基于不完整状态执行 git add。
        return list(list_changed_errors)

    # 范围外改动必须由用户人工处理。
    list_outside = [  # 不属于发布治理范围的改动。
        str_path for str_path in list_changed if not matches_governed_path(str_path, list_allowed)  # 范围外路径
    ]  # 完成未受管改动筛选。

    # 任意范围外改动阻断自动提交。
    if list_outside:

        # 回显完整路径集合。
        return [f"release prepare found changes outside governed release paths: {list_outside}"]

    # 仅选择实际变化且受治理覆盖的路径。
    list_stage_targets = sorted(  # git add 的受管目标。
        {
            str_path for str_path in list_changed if matches_governed_path(str_path, list_allowed)  # 受管改动
        }
    )  # 完成受管改动去重和排序。

    # 非空目标使用显式 pathspec 暂存。
    if list_stage_targets and run_git(
        path_project,  # 执行合并的仓库根。
        ["add", "--all", "--", *list_stage_targets],
    ).returncode != 0:

        # 暂存失败时不创建提交。
        return ["release prepare failed to stage governed release paths"]

    # cached diff 区分无改动、存在改动和 Git 错误。
    process_diff = run_git(path_project, ["diff", "--cached", "--quiet"])  # 暂存区检查结果。

    # 无暂存差异无需创建新提交。
    if process_diff.returncode == 0:

        # 当前分支已有可合并提交。
        return []

    # 返回码 1 之外表示检查失败。
    if process_diff.returncode != 1:

        # 不推测暂存区状态。
        return ["release prepare could not inspect staged changes"]

    # 提交消息记录来源分支和目标版本。
    str_message = f"release-prepare: stage {str_branch} for {str_version}"  # 发布准备提交消息。

    # 创建受管改动提交。
    process_commit = run_git(path_project, ["commit", "-m", str_message])  # Git 提交结果。

    # Git 拒绝提交时返回底层详情。
    if process_commit.returncode != 0:

        # stderr 优先，空时使用 stdout。
        str_detail = (process_commit.stderr or process_commit.stdout).strip()  # 提交失败详情。

        # 返回稳定前缀和具体 Git 输出。
        return [f"release prepare failed to commit staged changes: {str_detail}"]

    # 提交阶段完成。
    return []

# 分支合并器切换 master、非快进合并并删除开发分支。
def merge_prepare_branch(path_project: Path, str_branch: str, str_version: str) -> list[str]:
    """把临时开发分支合并到 master 后删除。

    参数：path_project 为仓库根，str_branch 为临时分支。
    参数：str_version 为合并提交记录的版本。
    返回：切换、合并或删除错误列表。
    """

    # 切换失败时不得继续合并。
    process_checkout = run_git(path_project, ["checkout", "master"])  # master 切换结果。

    # 保留当前分支并返回 Git 详情。
    if process_checkout.returncode != 0:

        # 选择可用的错误输出。
        str_detail = (process_checkout.stderr or process_checkout.stdout).strip()  # checkout 失败详情。

        # 返回切换阻断诊断。
        return [f"release prepare failed to checkout master: {str_detail}"]

    # 非快进提交保留开发分支边界。
    str_message = f"release-prepare: merge {str_branch} into master for {str_version}"  # 合并提交消息。

    # 显式指定来源分支和提交消息。
    process_merge = run_git(  # Git 合并结果。
        path_project,  # 合并操作仓库根。
        ["merge", "--no-ff", str_branch, "-m", str_message],  # 非快进合并参数。
    )  # 完成非快进合并命令执行。

    # 合并失败时保留仓库现场供用户处理。
    if process_merge.returncode != 0:

        # 合并失败优先采用错误流详情。
        str_detail = (process_merge.stderr or process_merge.stdout).strip()  # 非快进合并失败详情。

        # 不删除尚未合并的开发分支。
        return [f"release prepare failed to merge {str_branch} into master: {str_detail}"]

    # 已合并分支使用安全删除模式。
    process_delete = run_git(path_project, ["branch", "-d", str_branch])  # 分支删除结果。

    # 删除失败仍需阻断最终门禁。
    if process_delete.returncode != 0:

        # 删除失败优先采用错误流，空时退回标准输出。
        str_detail = (process_delete.stderr or process_delete.stdout).strip()  # 临时分支清理失败详情。

        # 要求用户清理残留分支。
        return [f"release prepare failed to delete branch {str_branch}: {str_detail}"]

    # 合并和清理均成功。
    return []

# 收尾检查器确认 master、保护分支集合和干净工作区。
def finish_release_prepare(
    path_project: Path,
    str_prepared_branch: str,
    list_protected: list[str],
    dict_checks: dict[str, Any],
) -> list[str]:
    """验证发布准备完成后的 Git 状态。

    参数：path_project、str_prepared_branch 和 list_protected 描述预期状态。
    参数：dict_checks 原位保存最终状态。
    返回：收尾错误列表。
    """

    # 重新读取权威 Git 状态。
    str_branch, list_branches, list_status = current_branch_and_locals(path_project)  # 合并后的 Git 状态。

    # checks 同时保留来源分支和最终事实。
    dict_checks.update(
        {
            "prepared_branch": str_prepared_branch,
            "current_branch": str_branch,
            "local_branches": list_branches,
            "status_lines": list_status,
        }
    )

    # 各项最终条件独立报告。
    list_errors: list[str] = []  # 发布准备收尾诊断。

    # 流程必须结束在 master。
    if str_branch != "master":

        # 检出分支漂移独立报告。
        list_errors.append("release prepare did not end on master")

    # 本地只保留配置中的保护分支。
    if sorted(list_branches) != list_protected:

        # 回显预期集合。
        list_errors.append(f"release prepare did not end with only protected branches {list_protected}")

    # 合并和删除后工作区必须干净。
    if list_status:

        # 未提交改动阻断后续发布门禁。
        list_errors.append("release prepare requires a clean worktree after merge and branch cleanup")

    # 返回全部收尾诊断。
    return list_errors

# 公共入口编排硬门禁、同步、提交、合并和收尾检查。
def release_prepare(
    project: Path,
    version: str,
    skill_dir_raw: str,
    test_evidence_raw: str = "",
    bool_require_test_evidence: bool = False,
) -> dict[str, Any]:
    """准备临时开发分支进入受管发布状态。

    参数：project 为仓库根，version 为目标版本。
    参数：skill_dir_raw 为相对或绝对技能目录。
    参数：test_evidence_raw 非空时在暂存前验证远程测试收据。
    参数：bool_require_test_evidence 为 True 时拒绝缺失收据。
    返回：包含 Git 证据和错误列表的准备结果。
    """

    # 所有 Git 和文件副作用前执行 worktree 硬门禁。
    dict_worktree = inspect_worktree_policy(project)  # 发布准备 worktree 策略报告。

    # 额外 worktree 或污染目录不可绕过。
    if dict_worktree.get("hard_blocking", False):

        # 硬阻断结果不进入后续路径读取。
        return {
            "ok": False,
            "errors": ["release prepare blocked by Git worktree policy"],
            "checks": {"worktree_policy": dict_worktree},
            "hard_blocking": True,
        }

    # 非法版本不得产生 Git 历史。
    str_version_error = version_policy_error(version)  # 当前版本策略诊断。

    # 版本失败返回最小证据。
    if str_version_error:

        # 不执行同步、暂存或分支操作。
        return {"ok": False, "errors": [str_version_error], "checks": {"version": version}}

    # 读取发布治理配置。
    dict_profile = read_json(project / ".agents" / "agents-control.json")  # 当前发布配置。

    # 相对路径锚定项目根。
    path_raw = Path(skill_dir_raw)  # 原始技能路径。

    # 统一解析技能源码目录。
    path_skill = resolve_project(  # 已验证技能源码根。
        skill_dir_raw if path_raw.is_absolute() else project / skill_dir_raw  # 根据输入形态选择解析基准。
    )  # 完成技能输入路径规范化。

    # 读取初始分支和工作区状态。
    str_branch, list_branches, list_status = current_branch_and_locals(project)  # 初始 Git 状态。

    # 保护分支来自配置并保持排序。
    list_protected = sorted(  # 当前保护分支集合。
        (dict_profile.get("git_branch_policy", {}) or {}).get(  # 分支策略
            "protected_branches", ["master", "release"]  # 保护分支配置和默认值。
        )
    )  # 完成排序。

    # checks 保留自动流程前后的证据。
    dict_checks: dict[str, Any] = {
        "current_branch": str_branch,  # 准备开始时的检出分支。
        "local_branches": list_branches,  # 准备开始时的本地分支。
        "protected_branches": list_protected,  # 流程结束应保留的分支。
        "prepared_branch": "",  # 尚未合并开发分支。
        "status_lines": list_status,  # 准备开始时的工作区状态。
    }

    # 分支拓扑可能直接成功或失败。
    dict_branch_result = check_prepare_branches(  # 可选提前结果。
        str_branch,  # 当前检出分支。
        list_branches,  # 初始本地分支集合。
        list_protected,  # 配置保护分支集合。
        dict_checks,  # 提前结果携带的检查证据。
    )  # 完成分支拓扑可自动化判断。

    # master 已就绪或拓扑不安全时直接返回。
    if dict_branch_result is not None:

        # 已处于完成态时仍不能绕过显式提供的发布测试收据。
        if dict_branch_result.get("ok") and (
            test_evidence_raw or bool_require_test_evidence
        ):

            # 当前状态只读验证，不在 master 上执行同步或提交。
            dict_test_evidence = validate_project_test_evidence(  # 当前不透明测试证据结果。
                project,  # 当前发布仓库。
                test_evidence_raw,  # 调用方收据输入。
                bool_required=bool_require_test_evidence,  # CLI 准备命令拒绝缺失收据。
            )

            # 提前结果只公开脱敏测试统计和错误码。
            dict_checks["test_evidence"] = dict_test_evidence  # 已完成态的测试证据。

            # 无效收据覆盖提前成功结论。
            if dict_test_evidence["errors"]:

                # 保留分支事实和脱敏测试证据。
                return prepare_failure(dict_test_evidence["errors"], dict_checks)

        # 分支检查已形成完整机器载荷。
        return dict_branch_result

    # 提交前刷新根 AGENTS 元数据。
    list_errors = sync_prepare_agents(project, path_skill, dict_checks)  # 根规则同步错误。

    # 同步失败时停止 Git 写操作。
    if list_errors:

        # 返回同步阶段证据。
        return prepare_failure(list_errors, dict_checks)

    # 根同步完成后、任何 Git 暂存前验证当前源码与远程测试证据绑定。
    dict_test_evidence = validate_project_test_evidence(  # 同步后测试证据。
        project,  # 根同步发生的候选仓库。
        test_evidence_raw,  # 待重新绑定同步结果的收据。
        bool_required=bool_require_test_evidence,  # 暂存前采用调用方必需策略。
    )

    # 准备结果记录脱敏测试统计和稳定错误码。
    dict_checks["test_evidence"] = dict_test_evidence  # 发布准备脱敏证据。

    # 同步导致 manifest 漂移或收据本身无效时禁止暂存。
    if dict_test_evidence["errors"]:

        # TESTER 必须基于同步后的源码重新远程验证并重签。
        return prepare_failure(dict_test_evidence["errors"], dict_checks)

    # 暂存并提交受管路径改动。
    list_errors = commit_prepare_changes(  # 提交阶段错误。
        project,  # 收尾分支核验仓库。
        path_skill,  # 技能源码路径。
        dict_profile,  # 受管路径配置。
        str_branch,  # 临时开发分支。
        version,  # 目标发布版本。
    )  # 完成受管改动暂存和提交。

    # 提交失败时保留开发分支。
    if list_errors:

        # 返回提交阶段证据。
        return prepare_failure(list_errors, dict_checks)

    # 合并到 master 并删除开发分支。
    list_errors = merge_prepare_branch(project, str_branch, version)  # 合并阶段错误。

    # 合并或删除失败时停止。
    if list_errors:

        # 返回 Git 操作证据。
        return prepare_failure(list_errors, dict_checks)

    # 重新验证最终分支和工作区。
    list_errors = finish_release_prepare(  # 收尾阶段错误。
        project,  # 当前仓库根。
        str_branch,  # 已合并的开发分支。
        list_protected,  # 允许保留的保护分支。
        dict_checks,  # 准备阶段证据映射。
    )

    # 最终状态决定准备结果。
    return {"ok": not list_errors, "errors": list_errors, "checks": dict_checks}

# 发布树复制器只接收内容策略已经筛选过的成员。
def copy_release_tree(skill_dir: Path, release_dir: Path, included_files: list[str]) -> None:
    """将策略允许的源文件复制到全新的发布目录。

    参数：skill_dir 为技能源码根，release_dir 为版本化发布目录。
    参数：included_files 为相对源码根的允许文件列表。
    返回：无；目标目录被完整重建。
    """

    # 旧的同版本目录必须先清除，防止已删除文件残留到新包。
    if release_dir.exists():

        # 整棵删除确保发布树与当前允许清单完全一致。
        shutil.rmtree(release_dir)

    # 预建空目录，使空文件清单也形成有效发布根。
    release_dir.mkdir(parents=True, exist_ok=True)

    # 每个允许成员保持相对层级复制到版本目录。
    for relative in included_files:

        # 相对成员锚定技能源码根，不能从项目其他位置取文件。
        source = skill_dir / relative  # 当前待复制的源码文件。

        # 目标路径复用相同相对成员以保持包内结构。
        target = release_dir / relative  # 当前文件的发布位置。

        # 嵌套成员复制前创建对应父目录。
        target.parent.mkdir(parents=True, exist_ok=True)

        # copy2 保留文件元数据并写入筛选后的发布树。
        shutil.copy2(source, target)

# 发布收据构造器集中描述可复现打包事实。
def build_package_receipt(
    # 发布身份字段形成收据主键。
    str_skill_name: str,
    str_version: str,
    str_source_relative: str,

    # 策略证据描述清洗和内容边界。
    tuple_sanitization: tuple[Any, ...],
    dict_release_policy: dict[str, Any],

    # 文件系统证据证明当前与历史产物。
    path_release_dir: Path,
    list_other_artifacts: list[str],
) -> dict[str, Any]:
    """构造写入版本目录的发布收据。

    参数：str_skill_name、str_version 和 str_source_relative 标识当前产物。
    参数：tuple_sanitization 和 dict_release_policy 记录发布策略证据。
    参数：path_release_dir 与 list_other_artifacts 证明文件和历史边界。
    返回：可序列化的强验证发布收据。
    """

    # 固定分支与验证字段记录 package-release 完成后的预期状态。
    return {
        "skill_name": str_skill_name,  # 当前技能名称。
        "version": str_version,  # 当前发布版本。
        "source_path": str_source_relative,  # 项目相对源码位置。
        "generated_at": datetime.now().isoformat(timespec="seconds"),  # 收据生成时间。
        "current_branch": "master",  # 打包提交所在保护分支。
        "local_branches": ["master", "release"],  # 允许的发布分支集合。
        "worktree_clean": True,  # post 门禁要求的工作区状态。
        "phase_results": {"pre": True, "post": True},  # 前后门禁声明。
        "packaging_mode": "repository-dist",  # 仓库内版本化打包模式。
        "validation_level": "strong",  # 本仓库来源使用强验证。
        "provenance_mode": "repository-dist",  # 产物来源证明模式。
        "sanitization": tuple_sanitization,  # 敏感内容清洗证据。
        "release_content_policy": dict_release_policy,  # 发布内容策略收据。
        "files": build_release_file_manifest(path_release_dir),  # 文件哈希清单。
        "other_version_artifacts": list_other_artifacts,  # 历史版本不可变快照。
    }

# dist 提交器隔离暂存区检查和提交失败诊断。
def commit_package_artifacts(
    path_project: Path,
    str_skill_name: str,
    str_version: str,
) -> list[str]:
    """暂存并提交当前版本的 dist 产物。

    参数：path_project 为仓库根。
    参数：str_skill_name 和 str_version 组成提交消息。
    返回：空列表表示提交成功，否则返回稳定错误列表。
    """

    # 只暂存 dist 边界，避免吸收尚未完成的源码治理改动。
    completed_process_add = run_git(path_project, ["add", "--all", "--", "dist"])  # dist 暂存结果。

    # 暂存失败时不再检查索引差异。
    if completed_process_add.returncode != 0:

        # 调用方把稳定诊断合并到打包结果。
        return ["package release failed to stage dist artifacts"]

    # cached diff 的返回码区分无变化、有变化和 Git 检查失败。
    completed_process_diff = run_git(path_project, ["diff", "--cached", "--quiet"])  # 索引差异检查结果。

    # 没有新的 dist 变化时无需创建空提交。
    if completed_process_diff.returncode == 0:

        # 空错误列表表示发布提交阶段已经满足。
        return []

    # 非标准返回码说明暂存区无法可靠读取。
    if completed_process_diff.returncode != 1:

        # 索引异常必须阻止 post 门禁继续运行。
        return ["package release could not inspect staged release artifacts"]

    # 有实际产物变化时创建版本化提交。
    completed_process_commit = run_git(  # 发布产物提交结果。
        path_project,  # 发布提交所在仓库。
        ["commit", "-m", f"package-release: {str_skill_name} {str_version}"],  # 稳定提交消息。
    )

    # 成功提交后不产生诊断。
    if completed_process_commit.returncode == 0:

        # 调用方据此进入 post 门禁。
        return []

    # stderr 优先保留 Git 的直接失败原因。
    str_commit_output = completed_process_commit.stderr or completed_process_commit.stdout  # 原始提交诊断。

    # 去除终端换行以保持 JSON 错误字段稳定。
    str_commit_failure = str_commit_output.strip()  # 规范化提交失败文本。

    # 提交失败诊断包含 Git 返回的具体原因。
    return [f"package release failed to commit dist artifacts: {str_commit_failure}"]

# 打包前检先验证版本策略、源码路径和 pre 门禁。
def package_preflight(
    path_project: Path,
    str_version: str,
    str_skill_dir_raw: str,
    str_test_evidence_raw: str = "",
    bool_require_test_evidence: bool = False,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """收集打包上下文，并在写入 dist 前执行失败快速返回。

    参数：path_project 为仓库根。
    参数：str_version 为请求发布版本。
    参数：str_skill_dir_raw 为绝对或项目相对的技能源码目录。
    参数：str_test_evidence_raw 为 pre 门禁使用的不透明测试收据。
    参数：bool_require_test_evidence 为 True 时拒绝缺失收据。
    返回：上下文与可选失败载荷；失败载荷非空时不得继续写入。
    """

    # 版本策略先于路径和 Git 操作，避免非法版本产生任何发布副作用。
    str_version_error = version_policy_error(str_version)  # 非法语义版本诊断。

    # 非法版本直接返回内容策略字段完整的失败合同。
    if str_version_error:

        # 空上下文表明打包流程尚未建立可信输入。
        return {}, {
            "ok": False,  # 版本门禁未通过。
            "errors": [str_version_error],  # 具体版本策略错误。
            "policy_version": POLICY_VERSION,  # 生效的发布内容策略版本。
            "forbidden_source_paths": [],  # 尚未扫描源码。
            "forbidden_release_paths": [],  # 尚未创建发布树。
            "release_content_policy_ok": False,  # 内容策略未验证。
        }

    # 控制配置决定收据名称和发布清洗规则。
    dict_profile = read_json(path_project / ".agents" / "agents-control.json")  # 当前项目控制配置。

    # 原始路径对象用于区分绝对路径和项目相对路径。
    path_skill_input = Path(str_skill_dir_raw)  # 用户提供的技能目录。

    # 相对路径锚定仓库根，绝对路径保持原位置。
    path_skill_dir = resolve_project(  # 已解析技能源码目录。
        str_skill_dir_raw  # 绝对路径原样解析。
        if path_skill_input.is_absolute()  # 根据输入路径形态选择基准。
        else path_project / str_skill_dir_raw  # 相对路径使用项目根。
    )

    # 目录叶节点形成版本目录和 ZIP 的名称前缀。
    str_skill_name = path_skill_dir.name  # 版本目录命名前缀。

    # 收据优先记录仓库相对源码位置，外部路径退化为目录名。
    str_source_relative = (
        path_skill_dir.relative_to(path_project).as_posix()  # 项目内源码相对路径。
        if path_skill_dir.is_relative_to(path_project)  # 仅仓库内路径可相对化。
        else path_skill_dir.name  # 外部源码只公开目录名。
    )  # 收据中的源码位置。

    # 项目类型决定发布树清洗合同。
    str_project_kind = release_project_kind(path_project, path_skill_dir)  # 当前发布项目类型。

    # pre 门禁验证版本、Git 和源码内容的发布前条件。
    dict_pre_gate = release_gate(  # 发布前门禁证据。
        path_project,  # 发布前检查仓库。
        str_version,  # 待验证版本。
        str_skill_dir_raw,  # 待验证源码目录。
        "pre",  # 发布前阶段。
        "unspecified",  # 打包时尚未选择安装目标。
        str_test_evidence_raw,  # 与 post 阶段相同的不透明测试收据。
        bool_require_test_evidence,  # CLI 打包路径的收据必需状态。
    )

    # pre 门禁错误必须在创建版本目录前返回。
    if dict_pre_gate["errors"]:

        # 失败载荷透传内容策略证据，保持 CLI 机器合同。
        return {}, {
            "ok": False,  # pre 门禁未通过。
            "errors": dict_pre_gate["errors"],  # 发布前阻断原因。
            "pre_gate": dict_pre_gate,  # 完整发布前证据。
            "policy_version": dict_pre_gate.get("policy_version", POLICY_VERSION),
            "forbidden_source_paths": dict_pre_gate.get("forbidden_source_paths", []),
            "forbidden_release_paths": dict_pre_gate.get("forbidden_release_paths", []),
            "release_content_policy_ok": dict_pre_gate.get("release_content_policy_ok", False),
        }

    # 后续阶段只依赖命名上下文字段，避免重复解析路径和配置。
    dict_context = {
        "project": path_project,  # 后续打包写入仓库。
        "version": str_version,  # 请求发布版本。
        "skill_dir_raw": str_skill_dir_raw,  # post 门禁使用的原始路径。
        "profile": dict_profile,  # 项目控制配置。
        "skill_dir": path_skill_dir,  # 已解析源码目录。
        "skill_name": str_skill_name,  # 技能名称。
        "source_relative": str_source_relative,  # 收据源码位置。
        "project_kind": str_project_kind,  # 发布项目类型。
        "pre_gate": dict_pre_gate,  # 已通过的 pre 门禁证据。
    }

    # 空失败载荷表示可以安全进入发布树写入阶段。
    return dict_context, None

# 源码内容违规结果保持 package_release 的失败字段稳定。
def forbidden_source_package_result(
    path_project: Path,
    path_release_dir: Path,
    dict_pre_gate: dict[str, Any],
    list_forbidden_source: list[str],
) -> dict[str, Any]:
    """构造禁止开发内容存在时的打包失败结果。

    参数：path_project 和 path_release_dir 定位目标发布。
    参数：dict_pre_gate 保留发布前证据。
    参数：list_forbidden_source 列出实际违规源码路径。
    返回：未创建可安装产物的稳定失败载荷。
    """

    # 源码违规发生在复制前，因此发布树违规列表保持为空。
    return {
        "ok": False,  # 源码内容策略未通过。
        "errors": ["package release rejected forbidden development content in skill source"],
        "pre_gate": dict_pre_gate,  # 已通过的前置证据。
        "release_dir": display_path(path_release_dir, path_project),
        "policy_version": POLICY_VERSION,  # 当前内容策略版本。
        "forbidden_source_paths": list_forbidden_source,  # 实际源码违规。
        "forbidden_release_paths": [],  # 尚未复制发布树。
        "release_content_policy_ok": False,  # 内容策略拒绝。
    }

# 收据终结器从已清洗目录生成内容证据、收据和 ZIP。
def finalize_package_artifacts(
    # 三个路径分别定位目录、压缩包和收据。
    path_release_dir: Path,
    path_zip: Path,
    path_receipt: Path,

    # 前检上下文提供稳定发布身份。
    dict_context: dict[str, Any],

    # 策略证据证明清洗和历史不可变边界。
    tuple_sanitization: tuple[Any, ...],
    list_other_artifacts: list[str],
    list_forbidden_source: list[str],
) -> dict[str, Any]:
    """完成发布目录的最终可安装产物。

    参数：path_release_dir、path_zip 和 path_receipt 定位三个产物。
    参数：dict_context 提供技能名称、版本和源码位置。
    参数：tuple_sanitization、list_other_artifacts 和 list_forbidden_source 提供策略证据。
    返回：供提交和 post 门禁使用的产物映射。
    """

    # 发布目录分析验证复制和清洗后的最终内容。
    dict_release_content = release_tree_content_analysis(path_release_dir)  # 最终发布树分析。

    # 内容策略收据连接源码禁用清单与最终发布树证据。
    dict_release_policy = release_content_policy_receipt(  # 最终内容策略收据。
        dict_release_content,  # 已清洗发布树分析。
        forbidden_source_paths=list_forbidden_source,  # 源码违规证据。
    )  # 已清洗目录的策略收据。

    # 强验证收据记录文件清单、清洗和历史不可变证据。
    dict_receipt = build_package_receipt(  # 当前版本发布收据。
        dict_context["skill_name"],  # 收据技能名称。
        dict_context["version"],  # 收据发布版本。
        dict_context["source_relative"],  # 可移植来源字段。
        tuple_sanitization,  # 清洗证据。
        dict_release_policy,  # 内容策略证据。
        path_release_dir,  # 文件清单根目录。
        list_other_artifacts,  # 历史产物快照。
    )  # 待写入磁盘的强验证收据。

    # JSON 收据使用稳定缩进，便于审计和后续安装验证。
    path_receipt.write_text(json.dumps(dict_receipt, indent=2), encoding="utf-8")

    # ZIP 从已完成清洗和收据写入的版本目录生成。
    write_release_zip(path_release_dir, path_zip)

    # 产物映射保留 post 门禁和最终结果所需的完整证据。
    return {
        "release_dir": path_release_dir,  # 版本化发布目录。
        "release_zip": path_zip,  # 版本化 ZIP。
        "receipt_path": path_receipt,  # 强验证收据。
        "release_content": dict_release_content,  # 最终内容策略分析。
        "forbidden_source_paths": list_forbidden_source,  # 已确认空的源码违规。
    }

# 发布树构建器执行内容筛选、清洗、不可变检查和收据写入。
def create_package_artifacts(
    dict_context: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """根据前检上下文创建版本目录、收据和 ZIP。

    参数：dict_context 为 package_preflight 返回的可信打包上下文。
    返回：产物证据与可选失败载荷；失败时不进入 Git 提交。
    """

    # 仓库根限定 dist 写入和历史快照范围。
    path_project: Path = dict_context["project"]  # 打包产物所属仓库。

    # 版本号参与目录、ZIP 和提交身份构造。
    str_version: str = dict_context["version"]  # 本次产物版本。

    # 控制配置提供收据名称与清洗策略。
    dict_profile: dict[str, Any] = dict_context["profile"]  # 生效发布配置。

    # 源码目录是内容筛选和复制的唯一输入根。
    path_skill_dir: Path = dict_context["skill_dir"]  # 内容复制唯一来源根。

    # 技能名称形成版本化产物前缀。
    str_skill_name: str = dict_context["skill_name"]  # dist 名称前缀。

    # 收据记录可移植的项目相对来源。
    str_source_relative: str = dict_context["source_relative"]  # 可公开源码位置。

    # 项目类型选择对应的发布清洗合同。
    str_project_kind: str = dict_context["project_kind"]  # 清洗策略类别。

    # 已通过的发布前证据随所有失败载荷返回。
    dict_pre_gate: dict[str, Any] = dict_context["pre_gate"]  # 前置门禁证明。

    # 版本化目录和 ZIP 必须共享完全一致的身份前缀。
    path_release_dir = path_project / "dist" / f"{str_skill_name}-{str_version}"  # 目标发布目录。

    # ZIP 与目录共享完全一致的版本身份。
    path_zip = path_project / "dist" / f"{str_skill_name}-{str_version}.zip"  # 目标发布 ZIP。

    # 当前版本目录和 ZIP 从历史产物快照中排除。
    set_exclusions = release_target_exclusions(str_skill_name, str_version)  # 当前版本排除集合。

    # 写入前快照用于证明其他版本产物保持不变。
    list_before_artifacts = dist_artifact_snapshot(path_project, set_exclusions)  # 历史产物初始快照。

    # 源码内容分析只允许策略声明的发布成员。
    dict_source_content = source_release_content_analysis(path_skill_dir)  # 源码内容策略分析。

    # 禁止路径单独提取以驱动复制前快速失败。
    list_forbidden_source = dict_source_content["forbidden_paths"]  # 源码中的禁止路径。

    # 开发缓存或治理私有内容不得进入发布复制阶段。
    if list_forbidden_source:

        # 独立构造器明确区分源码违规与发布树违规。
        dict_failure = forbidden_source_package_result(  # 禁止源码内容失败载荷。
            path_project,  # 源码违规所属仓库。
            path_release_dir,  # 尚未批准的发布目录。
            dict_pre_gate,  # 违规发现前的门禁证明。
            list_forbidden_source,  # 实际违规路径。
        )  # 复制前源码拒绝结果。

        # 空产物映射表示复制阶段尚未开始。
        return {}, dict_failure

    # 复制器按 included_files 重建全新的版本目录。
    copy_release_tree(path_skill_dir, path_release_dir, dict_source_content["included_files"])

    # 收据文件名由项目治理配置统一决定。
    path_receipt = path_release_dir / receipt_filename(dict_profile)  # 当前发布收据路径。

    # 清洗器处理仓库来源信息并返回可审计证据。
    tuple_sanitization, list_sanitization_errors = sanitize_release_tree(  # 清洗结果和错误列表。
        dict_profile,  # 发布清洗配置。
        str_project_kind,  # 项目类型。
        path_skill_dir,  # 清洗来源根。
        path_release_dir,  # 清洗目标树。
    )  # 发布树清洗证据与诊断。

    # 任何清洗失败都阻止收据和 ZIP 声明成功。
    if list_sanitization_errors:

        # 返回清洗诊断和当前版本目录位置。
        return {}, {
            "ok": False,  # 清洗阶段未通过。
            "errors": list_sanitization_errors,  # 清洗器稳定诊断。
            "pre_gate": dict_pre_gate,  # 清洗失败前置证明。
            "release_dir": display_path(path_release_dir, path_project),
        }

    # 清洗完成后重新快照其他版本，检测跨版本副作用。
    list_after_artifacts = dist_artifact_snapshot(path_project, set_exclusions)  # 历史产物最终快照。

    # 其他版本目录或 ZIP 的任何变化都违反不可变历史合同。
    if list_before_artifacts != list_after_artifacts:

        # 当前版本产物保留用于诊断，但打包结果不批准。
        return {}, {
            "ok": False,  # 历史产物不可变检查失败。
            "errors": ["cross-version release artifacts changed outside the current target release directory or zip"],
            "pre_gate": dict_pre_gate,  # 历史不可变检查前置证明。
            "release_dir": display_path(path_release_dir, path_project),
        }

    # 终结器写入收据和 ZIP；None 表示磁盘生成阶段没有失败载荷。
    return finalize_package_artifacts(
        # 三个目标路径共享同一版本身份。
        path_release_dir,  # 发布目录。
        path_zip,  # 发布 ZIP。
        path_receipt,  # 发布收据。

        # 上下文和策略事实进入最终收据。
        dict_context,  # 可信打包上下文。
        tuple_sanitization,  # 清洗证明。
        list_after_artifacts,  # 跨版本不可变证明。
        list_forbidden_source,  # 源码策略结果。
    ), None

# package_release 编排前检、产物生成、提交和 post 门禁。
def package_release(
    project: Path,
    version: str,
    skill_dir_raw: str,
    install_intent: str = "unspecified",
    test_evidence_raw: str = "",
    bool_require_test_evidence: bool = False,
) -> dict[str, Any]:
    """生成、提交并验证仓库内的版本化技能发布包。

    参数：project 为仓库根。
    参数：version 为请求发布版本。
    参数：skill_dir_raw 为绝对或项目相对的技能源码目录。
    参数：install_intent 为调用者声明的发布后安装意图。
    参数：test_evidence_raw 为 pre/post 共用的不透明测试收据。
    参数：bool_require_test_evidence 为 True 时拒绝缺失收据。
    返回：包含前后门禁、产物位置和内容策略证据的打包结果。
    """

    # 前检返回可信上下文或可直接透传的失败合同。
    tuple_preflight = package_preflight(  # 打包前检二元结果。
        project,  # 本次打包产物所属仓库。
        version,  # 请求打包版本。
        skill_dir_raw,  # 技能源目录。
        test_evidence_raw,  # pre/post 共用收据。
        bool_require_test_evidence,  # 将 CLI 收据约束传入前检。
    )

    # 二元结果分别提供可信上下文和可选失败载荷。
    dict_context, dict_failure = tuple_preflight  # 前检上下文与失败合同。

    # 任何前检错误都发生在 dist 写入之前。
    if dict_failure is not None:

        # 失败合同保持版本和 pre 门禁字段兼容。
        return dict_failure

    # 产物构建阶段完成复制、清洗、不可变检查和 ZIP 写入。
    tuple_artifact_result = create_package_artifacts(dict_context)  # 产物二元结果。

    # 产物映射和失败载荷保持互斥。
    dict_artifacts, dict_failure = tuple_artifact_result  # 产物证据与构建失败合同。

    # 内容或清洗错误不进入 Git 暂存与提交。
    if dict_failure is not None:

        # 构建器提供完整阶段诊断。
        return dict_failure

    # dist 提交器只暂存发布边界，并返回稳定错误列表。
    list_commit_errors = commit_package_artifacts(  # 发布产物提交诊断。
        project,  # dist 提交目标仓库。
        dict_context["skill_name"],  # 提交消息技能名称。
        version,  # 提交消息发布版本。
    )  # dist 暂存与提交错误。

    # Git 写入失败时保留 pre 门禁证据。
    if list_commit_errors:

        # post 门禁尚未执行，因此只返回前置证据。
        return {
            "ok": False,  # dist 提交未完成。
            "errors": list_commit_errors,  # 暂存或提交错误。
            "pre_gate": dict_context["pre_gate"],  # 已通过的发布前证据。
        }

    # 提交完成后 post 门禁验证收据、ZIP、Git 状态和内容策略。
    dict_post_gate = release_gate(  # 发布后门禁证据。
        project,  # 已提交 dist 产物的仓库。
        version,  # 已生成产物的版本。
        skill_dir_raw,  # 发布源码目录。
        "post",  # 发布后验证阶段。
        install_intent,  # 调用方安装意图。
        test_evidence_raw,  # 与 pre 阶段相同的测试收据。
        bool_require_test_evidence,  # 与 pre 阶段相同的必需状态。
    )

    # 便于表达最终内容策略结论的发布树分析。
    dict_release_content = dict_artifacts["release_content"]  # post 结果使用的内容分析。

    # 最终结果连接前后门禁与三个版本化产物位置。
    return {
        "ok": not dict_post_gate["errors"],  # post 门禁决定最终状态。
        "errors": dict_post_gate["errors"],  # 发布后阻断原因。
        "release_dir": display_path(dict_artifacts["release_dir"], project),
        "release_zip": display_path(dict_artifacts["release_zip"], project),
        "receipt_path": display_path(dict_artifacts["receipt_path"], project),
        "pre_gate": dict_context["pre_gate"],  # 发布前证据。
        "post_gate": dict_post_gate,  # 发布后证据。
        "policy_version": POLICY_VERSION,  # 生效内容策略版本。
        "forbidden_source_paths": dict_artifacts["forbidden_source_paths"],
        "forbidden_release_paths": dict_release_content["forbidden_paths"],
        "release_content_policy_ok": (
            not dict_release_content["unexpected_top_level_entries"]
            and not dict_release_content["forbidden_paths"]
        ),  # 最终发布树策略结论。
    }

# worktree 硬阻断结果不允许通过人工确认降级。
def blocked_branch_gate_result(
    path_project: Path,
    dict_worktree_policy: dict[str, Any],
) -> dict[str, Any]:
    """构造额外 worktree 策略的硬阻断结果。

    参数：path_project 为仓库根，dict_worktree_policy 为策略检查报告。
    返回：禁止覆盖且不请求确认的分支门禁载荷。
    """

    # 各类 worktree 违规分别形成稳定诊断，便于调用方定位清理对象。
    list_hard_reasons: list[str] = []  # 当前不可覆盖的 worktree 原因。

    # linked 状态说明当前目录本身不是主工作树。
    if dict_worktree_policy.get("linked_current_worktree"):

        # 当前项目必须回到仓库主工作目录后才能继续。
        list_hard_reasons.append("current project is a linked Git worktree")

    # 任何额外注册工作树都违反本仓库的单工作树合同。
    if dict_worktree_policy.get("additional_worktrees"):

        # 注册表违规需要在仓库外部完成移除。
        list_hard_reasons.append("additional registered Git worktrees are forbidden")

    # 常见 worktree 容器目录即使未注册也属于阻断污染。
    if dict_worktree_policy.get("forbidden_directories"):

        # 目录污染必须由用户确认安全后从外部处理。
        list_hard_reasons.append("forbidden worktree container directories were found")

    # 策略检查器的底层错误追加到稳定分类原因之后。
    list_hard_reasons.extend(  # 完整硬阻断诊断。
        str(item)  # 保持底层错误文本。
        for item in dict_worktree_policy.get("errors", [])  # 策略检查器原始错误。
    )

    # 硬阻断结果明确关闭 override 和确认入口。
    return {
        "project": str(path_project),  # worktree 硬阻断仓库。
        "approved": False,  # worktree 污染永不批准。
        "decision": "blocked",  # 统一阻断决策。
        "reasons": list_hard_reasons,  # 用户可见原因。
        "hard_blocking_reasons": list_hard_reasons,  # 机器可读硬阻断原因。
        "classified_reasons": [
            {"reason": reason, "risk": "high", "category": "worktree-governance"}
            for reason in list_hard_reasons
        ],  # 所有 worktree 原因均为高风险。
        "cleanup_plan": [],  # 工具不自动删除工作树。
        "checks": {"worktree_policy": dict_worktree_policy},  # 原始检查证据。
        "hard_blocking": True,  # 调用方不得降级。
        "override_allowed": False,  # 禁止强制确认覆盖。
        "force_confirmation_required": False,  # 外部清理后重新运行。
        "user_message": "检测到禁止的 Git worktree 状态；必须由用户在外部处理后重新运行门禁。",
        "decision_request": {},  # 硬阻断不创建交互选择。
    }

# 无控制配置或关闭 Git 治理时仍保留 worktree 策略证据。
def skipped_branch_gate_result(
    path_project: Path,
    dict_worktree_policy: dict[str, Any],
    str_skip_reason: str,
) -> dict[str, Any]:
    """构造普通 Git 分支治理被配置跳过时的批准结果。

    参数：path_project 标识待检查仓库。
    参数：dict_worktree_policy 保留单工作树证据。
    参数：str_skip_reason 说明普通分支治理跳过原因。
    返回：不需要用户确认的批准载荷。
    """

    # 只有额外 worktree 硬门禁通过后才允许进入本批准路径。
    return {
        "project": str(path_project),  # 跳过普通治理的仓库。
        "approved": True,  # 配置允许跳过普通分支检查。
        "decision": "approved",  # 稳定批准决策。
        "reasons": [],  # 没有普通分支违规。
        "checks": {
            "worktree_policy": dict_worktree_policy,  # 仍保留硬门禁证据。
            "skipped": str_skip_reason,  # 普通分支检查跳过原因。
        },
        "hard_blocking": False,  # 当前 worktree 策略已通过。
        "override_allowed": True,  # 无阻断需要覆盖。
        "force_confirmation_required": False,  # 不请求人工选择。
        "user_message": "",  # 批准结果不显示告警。
    }

# Git 状态收集器统一读取当前分支、本地分支和工作区变化。
def collect_branch_gate_checks(
    path_project: Path,
    dict_profile: dict[str, Any],
    dict_worktree_policy: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """收集普通分支治理证据和违规原因。

    参数：path_project 用于运行只读 Git 查询。
    参数：dict_profile 决定分支模型和保护集合。
    参数：dict_worktree_policy 进入最终检查证据。
    返回：checks 映射与稳定原因列表。
    """

    # 分支策略缺失时使用 master 与 release 的传统保护集合。
    value_policy = dict_profile.get("git_branch_policy", {})  # 原始分支策略配置。

    # 非映射策略按空配置处理，避免不可信类型传播。
    dict_policy = value_policy if isinstance(value_policy, dict) else {}  # 有效分支策略。

    # 保护分支集合参与严格拓扑比较。
    list_protected = dict_policy.get("protected_branches", ["master", "release"])  # 允许的本地分支。

    # 分支模型决定是否要求精确保护集合。
    str_branch_model = str(dict_profile.get("branch_model", "")).strip()  # 当前分支治理模型。

    # 三条只读 Git 命令共同构成普通分支证据。
    completed_process_branch = run_git(path_project, ["branch", "--show-current"])  # 当前分支查询。

    # 本地分支列表用于严格拓扑集合比较。
    completed_process_list = run_git(path_project, ["branch", "--list"])  # 本地分支查询。

    # 短状态输出用于识别非例外工作区变化。
    completed_process_status = run_git(path_project, ["status", "--short"])  # 工作区状态查询。

    # checks 先保存配置和硬门禁报告，Git 成功后再填充动态字段。
    dict_checks: dict[str, Any] = {
        "branch_model": str_branch_model,  # 生效的分支模型。
        "protected_branches": list_protected,  # 期望保护分支。
        "current_branch": "",  # 当前分支占位。
        "local_branches": [],  # 本地分支占位。
        "status_lines": [],  # 非例外状态占位。
        "worktree_policy": dict_worktree_policy,  # 单工作树检查证据。
    }

    # 原因列表只收集可由常规分支整理修复的问题。
    list_reasons: list[str] = []  # 当前普通治理诊断。

    # 任一 Git 命令失败都无法建立可信仓库状态。
    list_git_results = [completed_process_branch, completed_process_list, completed_process_status]  # Git 查询结果。

    # 不可读仓库停止解析 stdout，避免产生误导证据。
    if any(result.returncode != 0 for result in list_git_results):

        # 稳定诊断供 CLI 和测试断言使用。
        list_reasons.append("git branch governance requires a readable local git repository")

        # 返回已收集的配置与失败原因。
        return dict_checks, list_reasons

    # 当前分支输出去除终端换行。
    str_current_branch = completed_process_branch.stdout.strip()  # 严格模型当前分支。

    # worktree 标记和当前分支前缀在比较前统一清洗。
    list_local_branches = sorted(  # 规范化本地分支集合。
        normalize_branch_list_line(str_line)  # 去除 Git 展示标记。
        for str_line in completed_process_list.stdout.splitlines()  # 原始分支输出。
        if str_line.strip()  # 忽略空白行。
    )

    # 活跃会话等运行时例外不应阻断发布准备。
    list_status_lines = filter_runtime_status_lines(  # 真实未提交变化。
        completed_process_status.stdout.splitlines()  # Git 短状态原始行。
    )

    # 动态 Git 事实写回统一 checks 合同。
    dict_checks["current_branch"] = str_current_branch  # 当前分支证据。

    # 规范化集合写入机器可读检查结果。
    dict_checks["local_branches"] = list_local_branches  # 本地分支证据。

    # 过滤后的变化列表证明工作区洁净度。
    dict_checks["status_lines"] = list_status_lines  # 工作区变化证据。

    # 严格发布模型要求位于 master 且本地分支集合精确匹配。
    if str_branch_model == "master-and-dist-release":

        # 非 master 状态必须先通过发布准备流程合并。
        if str_current_branch != "master":

            # 空分支名称使用 unknown 保持诊断可读。
            list_reasons.append(f"current branch must be master, found {str_current_branch or 'unknown'}")

        # 额外或缺失保护分支都会破坏发布拓扑合同。
        if sorted(list_local_branches) != sorted(list_protected):

            # 同时报告期望集合与实际集合便于治理整理。
            list_reasons.append(
                f"local branches must match protected branch set {list_protected}, found {list_local_branches}"
            )

    # 严格分支治理要求没有非例外工作区变化。
    if list_status_lines:

        # 源码改动应先提交或有意移除后再执行发布。
        list_reasons.append("worktree must be clean before continuing under strict branch governance")

    # 调用方统一组装批准或阻断载荷。
    return dict_checks, list_reasons

# 分支阻断交互构造器提供整理或暂停选择。
def branch_cleanup_decision_request(
    list_reasons: list[str],
    list_cleanup_plan: list[str],
) -> dict[str, Any]:
    """构造普通分支治理失败时的用户决策请求。

    参数：list_reasons 为阻断原因。
    参数：list_cleanup_plan 为建议治理顺序。
    返回：可直接写入 branch_gate 结果的交互请求。
    """

    # 整理选项是默认可逆路径，暂停选项保留当前现场。
    return decision_request(
        "branch_governance",  # 交互请求类型。
        question="分支治理未通过。是否进入分支整理或发布治理流程？",
        options=[
            {
                "label": "进入治理整理",
                "value": "cleanup",
                "description": "按建议步骤整理分支和工作树后重跑门禁。",
                "recommended": True,
            },
            {
                "label": "暂停当前任务",
                "value": "pause",
                "description": "保留现场，等待人工处理分支状态。",
                "recommended": False,
            },
        ],
        default="cleanup",  # 默认进入可逆治理整理。
        risk="high",  # 分支和工作区变更属于高风险操作。
        next_action="run branch cleanup or release governance before continuing",
        context={"reasons": list_reasons, "cleanup_plan": list_cleanup_plan},
    )

# 普通分支结果组装器集中交互请求和风险分类。
def build_branch_gate_result(
    path_project: Path,
    dict_checks: dict[str, Any],
    list_reasons: list[str],
) -> dict[str, Any]:
    """根据普通分支检查结果构造最终治理载荷。

    参数：path_project 标识目标仓库。
    参数：dict_checks 保存普通分支检查证据。
    参数：list_reasons 保存可治理违规。
    返回：批准结果或允许用户进入治理整理的阻断结果。
    """

    # 没有原因时门禁批准，否则默认阻断。
    bool_approved = not list_reasons  # 当前普通分支决策。

    # 清理计划只在阻断时展示，避免批准结果携带无关动作。
    list_cleanup_plan = (
        [
            "commit or intentionally remove current worktree changes",  # 先处理未提交变化。
            "switch back to master",  # 再回到发布主分支。
            "merge or prepare any temporary development branch",  # 合并临时开发分支。
            "delete local branches other than master and release after merge",  # 删除多余本地分支。
            "rerun branch-gate",  # 最后重新验证治理状态。
        ]  # 普通分支治理的建议顺序。
        if not bool_approved  # 仅阻断状态需要整理步骤。
        else []  # 批准状态保持空计划。
    )  # 最终清理计划。

    # 原因分类供机器消费者区分高风险分支问题和其他诊断。
    list_classified_reasons = [
        {
            "reason": str_reason,  # 原始治理原因。
            "risk": "high" if "worktree" in str_reason or "branch" in str_reason else "medium",  # 风险级别。
            "category": "branch-governance",  # 普通分支治理类别。
        }
        for str_reason in list_reasons  # 每个原因保留独立分类。
    ]  # 结构化治理原因。

    # 阻断时提供显式整理或暂停选择，批准时保持空请求。
    dict_decision_request = (
        branch_cleanup_decision_request(list_reasons, list_cleanup_plan)  # 阻断交互合同。
        if not bool_approved  # 只有阻断结果请求用户决策。
        else {}  # 批准结果不需要交互。
    )  # 最终决策请求。

    # 返回字段兼容普通生成、发布准备和测试消费者。
    return {
        "project": str(path_project),  # 普通分支决策仓库。
        "approved": bool_approved,  # 普通治理批准状态。
        "decision": "approved" if bool_approved else "blocked",  # 稳定决策文本。
        "reasons": list_reasons,  # 普通分支违规原因。
        "classified_reasons": list_classified_reasons,  # 风险分类原因。
        "cleanup_plan": list_cleanup_plan,  # 建议治理步骤。
        "checks": dict_checks,  # 完整检查证据。
        "hard_blocking": False,  # 普通分支问题可进入整理流程。
        "override_allowed": True,  # 允许用户明确选择治理动作。
        "force_confirmation_required": not bool_approved,  # 阻断时需要确认。
        "user_message": (
            ""
            if bool_approved
            else "分支治理未通过，默认阻止普通生成/整理流程。若用户仍要继续，必须先明确确认是否进入分支整理或发布治理流程。"
        ),  # 用户可见提示。
        "decision_request": dict_decision_request,  # 交互选择合同。
    }

# 分支门禁先执行不可覆盖的 worktree 策略，再检查普通 Git 拓扑。
def branch_gate(project: Path) -> dict[str, Any]:
    """验证单工作树政策和项目配置声明的分支治理合同。

    参数：project 为待检查仓库根。
    返回：包含决策、原因、证据和可选交互请求的治理载荷。
    """

    # worktree 策略优先于任何配置早退，确保禁令无法被关闭 Git 治理绕过。
    dict_worktree_policy = inspect_worktree_policy(project)  # 当前单工作树策略报告。

    # 额外或 linked worktree 必须在仓库外部清理。
    if dict_worktree_policy.get("hard_blocking", False):

        # 硬阻断结果明确禁止确认覆盖。
        return blocked_branch_gate_result(project, dict_worktree_policy)

    # 控制配置决定是否启用普通分支治理。
    value_profile = read_json(project / ".agents" / "agents-control.json")  # 原始项目控制配置。

    # 缺少有效配置时只保留已通过的 worktree 检查。
    if not isinstance(value_profile, dict):

        # 跳过原因进入 checks，便于审计配置缺失。
        return skipped_branch_gate_result(project, dict_worktree_policy, "no control profile")

    # 项目可显式关闭普通 Git 管理，但不能关闭 worktree 禁令。
    if str(value_profile.get("git_management", "")).strip() == "no-git-management":

        # 跳过原因区分主动关闭与配置缺失。
        return skipped_branch_gate_result(project, dict_worktree_policy, "git management disabled")

    # 启用治理时收集 Git 证据并计算普通违规。
    tuple_branch_evidence = collect_branch_gate_checks(  # checks 与原因二元组。
        project,  # 分支检查目标仓库。
        value_profile,  # 已验证映射配置。
        dict_worktree_policy,  # 已通过的单工作树证据。
    )

    # 二元组字段分别交给结果组装器。
    dict_checks, list_reasons = tuple_branch_evidence  # 普通检查证据和原因。

    # 最终组装器保持所有调用面的返回字段一致。
    return build_branch_gate_result(project, dict_checks, list_reasons)

# install_confirmation_options 封装当前发布阶段的独立职责。
# 安装选择集中定义，确保发布门禁和交互层使用同一合同。
def install_confirmation_options() -> list[dict[str, Any]]:
    """返回发布完成后可供交互层展示的安装选项。

    参数：无。
    返回：包含跳过、Codex 默认目录和自定义目录的选项列表。
    """

    # 默认跳过安装，只有用户明确选择时才修改本地技能目录。
    return [
        {
            "label": "否，跳过安装",
            "value": "skip",
            "description": "默认选项；保留发布产物，但不安装到本地 skills 目录。",
            "recommended": True,
        },
        {
            "label": "安装到 Codex",
            "value": "codex",
            "description": "将发布包安装到当前本地 Codex skills 目录。",
            "recommended": False,
        },
        {
            "label": "自定义 skills 目录",
            "value": "custom",
            "description": "将发布包安装到用户明确提供的自定义 skills 根目录。",
            "recommended": False,
        },
    ]

# 最新版本发现器忽略 ZIP 和不符合语义版本命名的目录。
def latest_release_dir(project: Path, skill_name: str) -> Path | None:
    """按语义版本返回 dist 中最新的技能发布目录。

    参数：project 为项目根，skill_name 为发布目录名称前缀。
    返回：最高语义版本目录；不存在有效目录时返回 None。
    """

    # 版本元组用于数值排序，避免字符串排序误判两位数版本。
    list_releases: list[tuple[tuple[int, int, int], Path]] = []  # 已识别的版本目录。

    # 只遍历当前技能名称对应的版本化候选。
    for path in (project / "dist").glob(f"{skill_name}-v*"):

        # 同名前缀 ZIP 不属于可安装发布目录。
        if not path.is_dir():

            # 非目录候选不会进入可安装版本集合。
            continue

        # 目录名必须包含完整三段式版本号。
        match = re.search(r"v(\d+)\.(\d+)\.(\d+)", path.name)  # 当前候选的版本匹配。

        # 仅收录能够转为整数版本元组的规范目录。
        if match:

            # 三段捕获分别转换为主、次和修订版本数值。
            tuple_version = tuple(int(part) for part in match.groups())  # 当前候选的语义版本键。

            # 路径与排序键绑定，排序后仍能返回原目录。
            list_releases.append((tuple_version, path))

    # dist 中没有有效版本目录时显式报告缺失。
    if not list_releases:

        # 调用方用 None 区分首次发布与已有历史版本。
        return None

    # 按数值版本升序排列，末项即最新版本。
    list_releases.sort(key=lambda item: item[0])

    # 排序末项携带最高语义版本对应的目录路径。
    return list_releases[-1][1]

# 成员发现器复用内容策略分析，避免把禁止文件纳入发布清单。
def release_members(root: Path, prefix: Path) -> list[str]:
    """返回发布内容相对于指定前缀的稳定成员列表。

    参数：root 为待分析内容根，prefix 为返回路径的相对基准。
    返回：排序后的允许发布成员路径。
    """

    # 内容分析同时执行顶层和禁止路径策略过滤。
    dict_analysis = analyze_release_content_root(root)  # 当前内容根的策略分析结果。

    # 根目录本身作为前缀时可直接复用分析器的相对路径。
    if prefix == root:

        # 分析器已经保证根相对成员顺序稳定。
        return list(dict_analysis["included_files"])

    # 外层前缀场景需要把根内成员重新表达为前缀相对路径。
    list_members: list[str] = []  # 重定位后的发布成员。

    # 每个允许成员从内容根映射到调用方指定的共同前缀。
    for relative in dict_analysis["included_files"]:

        # POSIX 表示保证收据与 ZIP 成员跨平台稳定。
        str_member = (root / relative).relative_to(prefix).as_posix()  # 当前成员的前缀相对路径。

        # 汇总重定位成员后统一排序。
        list_members.append(str_member)

    # 外层前缀转换完成后再次排序以稳定收据内容。
    return sorted(list_members)

# 项目类型优先服从治理配置，缺省时再依据技能入口推断。
def release_project_kind(project: Path, skill_dir: Path) -> str:
    """读取发布项目类型，并在缺少配置时依据技能入口推断。

    参数：project 为项目根，skill_dir 为待发布源码目录。
    返回：受支持的 skill 或 engineering 项目类型。
    """

    # 控制配置是显式项目类型的唯一治理来源。
    profile = read_json(project / ".agents" / "agents-control.json")  # 项目类型声明配置。

    # 只有映射配置才能安全读取 kind 字段。
    if isinstance(profile, dict):

        # 规范化大小写和空白后再与受支持类型比较。
        str_kind = str(profile.get("kind", "")).strip().lower()  # 配置声明的项目类型。

        # 已知类型直接返回，避免启发式覆盖显式配置。
        if str_kind in {"skill", "engineering"}:

            # 显式治理类型优先于文件系统启发式判断。
            return str_kind

    # 缺少有效声明时，技能入口文件提供可靠的类型证据。
    if (skill_dir / "SKILL.md").is_file():

        # SKILL.md 是技能包的公开入口合同。
        return "skill"

    # 无技能入口的发布目录按工程项目处理。
    return "engineering"
