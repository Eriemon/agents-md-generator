"""实现文档治理 CLI 的发布前后强门禁。"""

# worktree 硬阻断结果在读取发布产物前返回。
def blocked_release_result(path_project: Path, dict_worktree_policy: dict[str, Any]) -> dict[str, Any]:
    """构造 worktree 策略硬阻断结果。

    参数：path_project 为项目根，dict_worktree_policy 为策略报告。
    返回：不可安装的发布门禁结果。
    """

    # 固定字段保持 pre 和 post 阶段机器合同一致。
    return {
        "project": str(path_project),  # 当前项目根。
        "ok": False,  # 硬阻断永不通过。
        "errors": ["release gate blocked by Git worktree policy"],  # 稳定阻断诊断。
        "checks": {"worktree_policy": dict_worktree_policy},  # 完整策略证据。
        "installable": False,  # 污染仓库不能产生可安装声明。
        "hard_blocking": True,  # 调用方不得降级处理。
        "decision_request": {},  # 硬阻断不请求安装选择。
    }

# 上下文收集器集中路径、版本、Git 和配置事实。
def collect_release_gate_context(
    path_project: Path,
    str_version: str,
    str_skill_dir_raw: str,
    str_phase: str,
    str_install_intent: str,
) -> dict[str, Any]:
    """收集发布门禁后续阶段共享的事实。

    参数：path_project、str_version 和 str_skill_dir_raw 定位目标发布。
    参数：str_phase 和 str_install_intent 描述门禁阶段与安装意图。
    返回：共享发布上下文映射。
    """

    # 项目发布配置决定收据名称和源码治理规则。
    dict_profile = read_json(path_project / ".agents" / "agents-control.json")  # 当前发布治理配置。

    # 相对技能目录按项目根解析，绝对目录保持原位置。
    path_skill_input = Path(str_skill_dir_raw)  # 原始技能目录路径。

    # 统一路径解析器验证技能目录存在性。
    path_skill_dir = resolve_project(  # 已解析技能源码目录。
        str_skill_dir_raw  # 绝对技能目录原样交给解析器。
        if path_skill_input.is_absolute()  # 根据路径形态选择基准。
        else path_project / str_skill_dir_raw  # 相对路径锚定项目根。
    )  # 完成绝对或项目相对技能路径解析。

    # 技能目录叶节点定义发布包名称前缀。
    str_skill_name = path_skill_dir.name  # 当前技能名称。

    # 项目类别决定是否需要安装确认和特定清洗合同。
    str_project_kind = release_project_kind(path_project, path_skill_dir)  # 当前发布项目类别。

    # 版本化目录是发布后验证的目标。
    path_expected_release = path_project / "dist" / f"{str_skill_name}-{str_version}"  # 预期发布目录。

    # ZIP 名称必须与发布目录身份一致。
    path_expected_zip = path_project / "dist" / f"{str_skill_name}-{str_version}.zip"  # 预期发布压缩包。

    # 收据中的 source_path 优先使用项目相对路径。
    str_source_relative = (
        path_skill_dir.relative_to(path_project).as_posix()  # 项目内技能相对路径。
        if path_skill_dir.is_relative_to(path_project)  # 仅项目内路径可相对化。
        else path_skill_dir.name  # 外部技能退化为目录名。
    )  # 收据源码路径表示。

    # 发布收据名称由治理配置控制。
    path_receipt = path_expected_release / receipt_filename(dict_profile)  # 预期发布收据路径。

    # 源码声明版本必须与请求发布版本一致。
    str_source_version = read_skill_version(path_skill_dir)  # 技能源码声明版本。

    # Git 当前分支参与发布分支治理。
    str_git_branch = run_git(path_project, ["branch", "--show-current"]).stdout.strip()  # 当前 Git 分支。

    # 本地分支拓扑规范化后用于精确比较。
    list_branches = sorted(  # 当前本地分支名称。
        normalize_branch_list_line(str_line)  # 去除当前分支和 worktree 标记。
        for str_line in run_git(path_project, ["branch", "--list"]).stdout.splitlines()  # 原始本地分支行。
        if str_line.strip()  # 忽略空白输出。
    )  # 完成本地分支输出规范化。

    # 活跃会话例外不应被误判为未提交源码改动。
    list_status_lines = filter_runtime_status_lines(  # 真实未提交 Git 状态行。
        run_git(path_project, ["status", "--short"]).stdout.splitlines()  # Git 短状态原始行。
    )  # 完成活跃会话状态例外过滤。

    # 所有后续 helper 通过命名字段共享事实。
    return {
        "project": path_project,  # 项目根路径。
        "version": str_version,  # 请求发布版本。
        "phase": str_phase,  # pre 或 post 门禁阶段。
        "install_intent": str_install_intent,  # 用户安装意图。
        "profile": dict_profile,  # 发布治理配置。
        "skill_dir": path_skill_dir,  # 技能源码目录。
        "skill_name": str_skill_name,  # 技能名称。
        "project_kind": str_project_kind,  # 项目类别。
        "expected_release": path_expected_release,  # 本次版本化产物目录。
        "expected_zip": path_expected_zip,  # 预期 ZIP 文件。
        "source_relative": str_source_relative,  # 收据源码相对路径。
        "receipt_path": path_receipt,  # 预期收据路径。
        "source_version": str_source_version,  # 源码声明版本。
        "git_branch": str_git_branch,  # 门禁执行时检出分支。
        "branches": list_branches,  # 本地分支集合。
        "status_lines": list_status_lines,  # 非例外工作区状态。
    }

# 基础 checks 映射公开门禁输入与预期产物位置。
def build_release_checks(dict_context: dict[str, Any]) -> dict[str, Any]:
    """构造发布门禁基础检查证据。

    参数：dict_context 为共享发布上下文。
    返回：后续阶段原位补充的 checks 映射。
    """

    # 常用路径字段先提取为明确类型边界。
    path_project = dict_context["project"]  # checks 路径相对化基准。

    # 技能目录用于计算对项目相对显示值。
    path_skill_dir = dict_context["skill_dir"]  # checks 中展示的技能位置。

    # 预期发布目录和 ZIP 均位于项目 dist 下。
    path_expected_release = dict_context["expected_release"]  # 版本化发布目录。

    # 压缩包路径与目录路径分别记录。
    path_expected_zip = dict_context["expected_zip"]  # 版本化发布 ZIP。

    # 收据路径使用配置驱动的文件名。
    path_receipt = dict_context["receipt_path"]  # 发布收据路径。

    # 返回值保持原有字段名供测试和 CLI 使用。
    return {
        "branch": dict_context["git_branch"],  # 发布治理目标分支。
        "local_branches": dict_context["branches"],  # 门禁观测的本地分支拓扑。
        "phase": dict_context["phase"],  # 门禁阶段。
        "install_intent": dict_context["install_intent"],  # 安装意图。
        "project_kind": dict_context["project_kind"],  # 发布项目类别。
        "skill_dir": (
            path_skill_dir.relative_to(path_project).as_posix()  # 项目内技能显示相对路径。
            if path_skill_dir.is_relative_to(path_project)  # 判断能否安全相对化。
            else str(path_skill_dir)  # 外部路径保留绝对表示。
        ),
        "source_version": dict_context["source_version"],  # checks 记录的技能声明版本。
        "expected_release_dir": path_expected_release.relative_to(path_project).as_posix(),  # 预期目录相对路径。
        "expected_release_zip": path_expected_zip.relative_to(path_project).as_posix(),  # 预期 ZIP 相对路径。
        "receipt_path": path_receipt.relative_to(path_project).as_posix(),  # 预期收据相对路径。
        "status_lines": dict_context["status_lines"],  # 非例外 Git 状态。
    }

# 共同门禁验证版本、文档、源码治理、内容策略和 Git 状态。
def validate_common_release_checks(
    dict_context: dict[str, Any],
    dict_checks: dict[str, Any],
    list_errors: list[str],
) -> list[str]:
    """执行 pre 和 post 共用的发布检查。

    参数：dict_context 和 dict_checks 为发布事实及证据映射。
    参数：list_errors 为共享诊断列表。
    返回：技能源码中的禁止发布路径。
    """

    # 从上下文读取后续检查需要的稳定值。
    path_project = dict_context["project"]  # 共同治理命令执行根。

    # 配置对象驱动文档和源码治理。
    dict_profile = dict_context["profile"]  # 共同治理规则来源。

    # 技能源码目录用于内容扫描。
    path_skill_dir = dict_context["skill_dir"]  # 技能源码根。

    # 请求版本先通过仓库版本策略。
    str_version_error = version_policy_error(dict_context["version"])  # 版本策略诊断。

    # 非空诊断直接加入发布错误。
    if str_version_error:

        # 保留公共策略的具体错误文本。
        list_errors.append(str_version_error)

    # 已初始化文档治理时运行完整验证，否则返回空成功结构。
    dict_docs_verify = (
        verify_docs(path_project)  # 已初始化项目的文档治理报告。
        if docs_governance_initialized(path_project)  # 判断文档治理是否启用。
        else {"project": str(path_project), "checked": [], "errors": []}  # 未启用时的中性结果。
    )  # 当前文档治理验证报告。

    # 文档错误附加稳定前缀便于识别来源。
    if dict_docs_verify.get("errors"):

        # 每条文档诊断独立加入发布错误。
        list_errors.extend(f"docs-verify: {str_item}" for str_item in dict_docs_verify["errors"])

    # checks 明确记录文档门禁状态。
    dict_checks["docs_verify_ok"] = not dict_docs_verify.get("errors")  # 文档治理是否通过。

    # 源码治理报告覆盖涉及的生产和测试文件。
    dict_source_governance = source_governance_report(path_project, dict_profile)  # 源码治理报告。

    # 报告错误使用稳定前缀加入最终诊断。
    list_errors.extend(format_source_governance_errors(dict_source_governance, prefix="source-governance"))

    # checks 公开源码治理总体状态。
    dict_checks["source_governance_ok"] = dict_source_governance["ok"]  # 源码治理是否通过。

    # 技能源码内容扫描识别禁止开发文件。
    dict_source_content = source_release_content_analysis(path_skill_dir)  # 源码发布内容分析。

    # 禁止路径作为收据和结果的共同证据。
    list_forbidden_source_paths = list(dict_source_content["forbidden_paths"])  # 源码禁止发布路径。

    # checks 记录策略版本和实际扫描事实。
    dict_checks["policy_version"] = POLICY_VERSION  # 当前发布内容策略版本。

    # 源码禁止路径完整公开给调用方。
    dict_checks["forbidden_source_paths"] = list_forbidden_source_paths  # 源码内容策略诊断路径。

    # 顶层包含项帮助审计最终包结构。
    dict_checks["source_release_content_top_level"] = dict_source_content["included_top_level_entries"]  # 源码纳入顶层项。

    # 源码中出现禁止内容时阻断发布。
    if list_forbidden_source_paths:

        # 稳定诊断说明问题位于技能源码。
        list_errors.append("release content policy rejected forbidden development content in skill source")

    # 源码声明版本必须匹配发布请求。
    if dict_context["source_version"] and dict_context["source_version"] != dict_context["version"]:

        # 同时回显请求和源码版本。
        list_errors.append(
            "release gate version "
            f"{dict_context['version']} does not match skill source version {dict_context['source_version']}"
        )

    # 发布门禁只允许在 master 上运行。
    if dict_context["git_branch"] != "master":

        # 分支不正确时给出明确要求。
        list_errors.append("release gate requires current branch master")

    # 本地治理分支集合必须精确为 master 和 release。
    if sorted(dict_context["branches"]) != ["master", "release"]:

        # 额外或缺失分支均阻断发布。
        list_errors.append("release gate requires only local branches master and release")

    # 两个阶段都要求干净提交状态。
    if dict_context["status_lines"]:

        # 诊断按阶段使用原有文本合同。
        list_errors.append(f"{dict_context['phase']}-release gate requires a clean committed worktree")

    # 返回源码禁止路径供发布后收据复核。
    return list_forbidden_source_paths

# 收据验证器复核内容策略、身份、清洗和跨版本快照。
def validate_post_release_receipt(
    dict_context: dict[str, Any],
    dict_checks: dict[str, Any],
    dict_release_content: dict[str, Any],
    list_forbidden_source_paths: list[str],
    set_other_release_exclusions: set[str],
    list_errors: list[str],
) -> None:
    """验证发布后收据及其全部治理证据。

    参数：dict_context、dict_checks 和 dict_release_content 提供发布事实。
    参数：list_forbidden_source_paths、set_other_release_exclusions 和 list_errors 提供验证状态。
    返回：无，诊断写入 list_errors。
    """

    # 收据路径是所有后续证据的入口。
    path_receipt = dict_context["receipt_path"]  # post 阶段实际收据入口。

    # 缺少收据时无法继续复核内部字段。
    if not path_receipt.is_file():

        # 使用项目相对路径提供稳定诊断。
        list_errors.append(
            f"missing release receipt: {path_receipt.relative_to(dict_context['project']).as_posix()}"
        )

        # 无收据时立即结束当前阶段。
        return

    # 收据读取器提供对象形式的发布证据。
    dict_receipt = read_release_receipt(path_receipt)  # 发布收据对象。

    # 内容策略记录必须匹配源码和发布包扫描。
    list_policy_errors = verify_release_content_policy(  # 收据内容策略诊断。
        dict_receipt,  # 完整发布收据。
        source_forbidden_paths=list_forbidden_source_paths,  # 源码禁止路径证据。
        release_analysis=dict_release_content,  # 发布包内容扫描。
        require_source_paths=True,  # 仓库发布必须记录源码证据。
    )  # 完成收据策略证据与实际发布扫描比对。

    # checks 公开具体策略错误。
    dict_checks["release_content_policy_errors"] = list_policy_errors  # 发布内容策略错误。

    # 内容策略错误进入最终发布诊断。
    list_errors.extend(list_policy_errors)

    # 收据身份、清单和来源字段必须完全匹配。
    list_errors.extend(
        verify_release_receipt(
            dict_context["project"],  # 当前仓库根。
            path_receipt,  # 收据文件路径。
            dict_context["expected_release"],  # 发布目录根。
            dict_context["skill_name"],  # 预期技能名。
            dict_context["version"],  # 预期版本号。
            dict_context["source_relative"],  # 预期源码相对路径。
            require_repo_dist=True,  # 当前门禁要求仓库 dist 强来源。
        )
    )

    # 清洗收据必须与源码和发布副本一致。
    list_errors.extend(
        verify_release_sanitization(
            dict_context["profile"],  # 清洗规则治理配置。
            dict_context["project_kind"],  # 清洗合同适用项目类别。
            dict_context["skill_dir"],  # 清洗对照源码根。
            dict_context["expected_release"],  # 发布副本目录。
            dict_receipt,  # 清洗验证使用的发布收据。
        )
    )

    # 收据必须保存其他版本产物快照。
    list_recorded_artifacts = dict_receipt.get("other_version_artifacts")  # 收据中的跨版本快照。

    # 非列表字段表示发布过程没有保护历史产物。
    if not isinstance(list_recorded_artifacts, list):

        # 明确指出缺少快照字段。
        list_errors.append("release receipt missing other_version_artifacts snapshot")

        # 无记录可继续比较。
        return

    # 当前快照排除本次目标版本目录和 ZIP。
    list_current_artifacts = dist_artifact_snapshot(  # 当前其他版本产物快照。
        dict_context["project"],  # 历史 dist 快照项目根。
        set_other_release_exclusions,  # 本次目标产物排除集合。
    )  # 完成排除目标版本后的 dist 快照采集。

    # checks 记录受保护历史产物数量。
    dict_checks["other_version_artifact_count"] = len(list_current_artifacts)  # 其他版本产物数量。

    # 历史产物任何漂移都阻断发布后门禁。
    if list_current_artifacts != list_recorded_artifacts:

        # 防止本次发布修改其他版本历史。
        list_errors.append("cross-version release artifacts changed outside the current target release")

# 发布后产物验证器检查目录、ZIP、源码治理、内容和文件奇偶性。
def validate_post_release_artifacts(
    dict_context: dict[str, Any],
    dict_checks: dict[str, Any],
    list_forbidden_source_paths: list[str],
    list_errors: list[str],
) -> None:
    """验证 post 阶段生成的全部发布产物。

    参数：dict_context 和 dict_checks 为发布事实及证据。
    参数：list_forbidden_source_paths 和 list_errors 为验证状态。
    返回：无，诊断原位追加。
    """

    # 预期目录和 ZIP 必须同时存在。
    path_expected_release = dict_context["expected_release"]  # post 阶段验证目录。

    # ZIP 文件用于分发和历史归档。
    path_expected_zip = dict_context["expected_zip"]  # post 阶段验证压缩包。

    # 发布目录缺失时记录错误，但仍检查 ZIP。
    if not path_expected_release.is_dir():

        # 使用项目相对路径形成稳定诊断。
        list_errors.append(
            f"missing release directory: {path_expected_release.relative_to(dict_context['project']).as_posix()}"
        )

    # ZIP 缺失独立报告。
    if not path_expected_zip.is_file():

        # 相对路径避免泄露本地绝对目录。
        list_errors.append(
            f"missing release zip: {path_expected_zip.relative_to(dict_context['project']).as_posix()}"
        )

    # 缺少目录时无法执行内容和收据复核。
    if not path_expected_release.is_dir():

        # 保留已记录的存在性错误并结束。
        return

    # 发布副本必须通过与源码相同的治理规则。
    dict_release_governance = release_source_governance_report(  # 发布副本源码治理报告。
        dict_context["project"],  # 发布副本治理执行项目根。
        path_expected_release,  # 被检查的发布源码副本。
        dict_context["profile"],  # 发布副本适用治理配置。
        source_relative_prefix=dict_context["source_relative"],  # 收据源码前缀。
    )  # 完成发布副本整树源码治理检查。

    # 治理错误使用专用前缀加入最终诊断。
    list_errors.extend(
        format_source_governance_errors(dict_release_governance, prefix="release-source-governance")
    )

    # checks 记录发布副本源码治理状态。
    dict_checks["release_source_governance_ok"] = dict_release_governance["ok"]  # 发布源码治理是否通过。

    # 发布目录内容分析验证顶层结构和禁止路径。
    dict_release_content = release_tree_content_analysis(path_expected_release)  # 发布目录内容分析。

    # checks 公开实际纳入的顶层条目。
    dict_checks["release_content_top_level"] = dict_release_content["included_top_level_entries"]  # 发布顶层内容。

    # 未知顶层条目是发布结构污染证据。
    dict_checks["unexpected_release_top_level_entries"] = dict_release_content["unexpected_top_level_entries"]  # 异常顶层项。

    # 禁止路径必须为空才能形成可安装发布包。
    dict_checks["forbidden_release_paths"] = dict_release_content["forbidden_paths"]  # 发布包禁止路径。

    # 源码成员清单作为发布奇偶性基准。
    list_source_files = release_members(dict_context["skill_dir"], dict_context["skill_dir"])  # 技能源码成员。

    # 发布文件清单排除自描述收据。
    list_release_files = sorted(  # 发布副本成员路径。
        dict_item["path"]  # 当前发布文件相对路径。
        for dict_item in build_release_file_manifest(  # 发布文件清单条目。
            path_expected_release,  # 文件清单扫描起点。
            exclude={dict_context["receipt_path"].name},  # 排除发布收据。
        )  # 生成不含收据的实际文件摘要清单。
    )  # 完成收据外发布成员路径排序。

    # 除确定性清洗内容外，成员路径必须完全一致。
    if list_source_files != list_release_files:

        # 路径奇偶性错误表示漏包或额外文件。
        list_errors.append("release parity mismatch between skill source and dist release directory")

    # 排除本次目标产物后保护其他版本历史。
    set_other_release_exclusions = release_target_exclusions(  # 当前版本产物排除集合。
        dict_context["skill_name"],  # 当前技能名。
        dict_context["version"],  # 当前目标版本。
    )  # 完成本次目录与 ZIP 历史快照排除配置。

    # 收据完成最终内容、清洗和历史快照复核。
    validate_post_release_receipt(
        dict_context,  # 收据复核所需发布身份。
        dict_checks,  # 收据复核写入的检查证据。
        dict_release_content,  # 收据对照的发布内容事实。
        list_forbidden_source_paths,  # 收据对照的源码内容事实。
        set_other_release_exclusions,  # 收据历史快照排除范围。
        list_errors,  # 共享发布诊断。
    )

# 最新版本验证器拒绝发布低于历史最高版本的请求。
def validate_latest_release_version(
    dict_context: dict[str, Any],
    dict_checks: dict[str, Any],
    list_errors: list[str],
) -> None:
    """验证请求版本不早于 dist 中最新发布。

    参数：dict_context 和 dict_checks 为发布事实及证据。
    参数：list_errors 为共享诊断列表。
    返回：无，版本倒退时追加错误。
    """

    # 最新版本目录按技能名从 dist 历史中选择。
    path_latest = latest_release_dir(dict_context["project"], dict_context["skill_name"])  # 最新历史发布目录。

    # 无历史发布时不存在版本倒退风险。
    if path_latest is None:

        # 保持 checks 不增加虚假路径。
        return

    # checks 记录用于比较的历史版本目录。
    dict_checks["latest_release_dir"] = path_latest.relative_to(dict_context["project"]).as_posix()  # 最新发布相对路径。

    # 当前版本元组不得小于历史版本元组。
    if parse_version_tuple(dict_context["version"]) < parse_historical_version_tuple(
        path_latest.name.rsplit("-", 1)[-1]
    ):

        # 阻止覆盖或倒退发布历史。
        list_errors.append("requested release version is older than the latest dist release")

# 结果构造器汇总可安装状态和内容策略状态。
def build_release_gate_result(
    dict_context: dict[str, Any],
    dict_checks: dict[str, Any],
    list_forbidden_source_paths: list[str],
    list_errors: list[str],
) -> dict[str, Any]:
    """构造发布门禁最终结构化结果。

    参数：dict_context、dict_checks 和 list_forbidden_source_paths 为发布证据。
    参数：list_errors 为全部阻断诊断。
    返回：稳定字段的发布门禁结果。
    """

    # 内容策略通过要求源码、发布和收据三个层面均无诊断。
    bool_content_policy_ok = (
        not list_forbidden_source_paths  # 源码无禁止发布路径。
        and not dict_checks.get("forbidden_release_paths", [])  # 发布包无禁止路径。
        and not dict_checks.get("unexpected_release_top_level_entries", [])  # 顶层结构无污染。
        and not dict_checks.get("release_content_policy_errors", [])  # 收据策略记录匹配。
    )  # 发布内容策略总状态。

    # 返回值保持原有 CLI 机器协议。
    return {
        "project": str(dict_context["project"]),  # 结果关联的发布项目根。
        "ok": not list_errors,  # 所有门禁是否通过。
        "errors": list_errors,  # 有序阻断诊断。
        "checks": dict_checks,  # 完整检查证据。
        "installable": not list_errors and dict_context["phase"] == "post",  # post 全绿才可安装。
        "receipt_path": dict_checks["receipt_path"],  # 发布收据相对路径。
        "provenance_mode": "repository-dist",  # 发布来源固定为仓库 dist。
        "validation_level": "strong",  # 当前门禁提供强验证。
        "policy_version": POLICY_VERSION,  # 结果声明的内容策略版本。
        "forbidden_source_paths": list_forbidden_source_paths,  # 结果中的源码内容诊断路径。
        "forbidden_release_paths": dict_checks.get("forbidden_release_paths", []),  # 发布禁止路径证据。
        "release_content_policy_ok": bool_content_policy_ok,  # 内容策略总状态。
    }

# 安装确认助手仅在 skill post 门禁且用户未声明意图时请求选择。
def attach_install_confirmation(
    dict_context: dict[str, Any],
    dict_checks: dict[str, Any],
    dict_result: dict[str, Any],
) -> None:
    """向发布结果附加可选安装确认请求。

    参数：dict_context 和 dict_checks 为发布上下文与证据。
    参数：dict_result 为原位更新的发布结果。
    返回：无。
    """

    # 只有发布后技能包且意图未指定时需要确认。
    bool_confirmation_required = (
        dict_context["phase"] == "post"  # 发布包已经生成并验证。
        and dict_context["install_intent"] == "unspecified"  # 用户尚未选择安装目标。
        and dict_context["project_kind"] == "skill"  # 仅技能项目支持本地安装。
    )  # 是否需要安装确认。

    # 不需要确认时写入稳定中性字段。
    if not bool_confirmation_required:

        # 调用方可直接判断确认开关。
        dict_result["install_confirmation_required"] = False  # 当前无需确认。

        # 空请求避免消费者处理缺失字段。
        dict_result["decision_request"] = {}  # 无安装决策请求。

        # 中性字段写入完成。
        return

    # 结果明确标记调用方必须询问用户。
    dict_result["install_confirmation_required"] = True  # 当前需要安装确认。

    # 问题文本保持原有中文交互合同。
    dict_result["confirmation_question"] = "释放安装版本后，用户尚未说明是否需要安装。是否需要安装当前发布包？"  # 安装确认问题。

    # 安装选项由公共 helper 统一定义。
    dict_result["install_options"] = install_confirmation_options()  # 可选安装目标。

    # 结构化决策请求支持自动化客户端渲染。
    dict_result["decision_request"] = decision_request(  # 结构化安装决策请求。
        "install_confirmation",  # 决策类型。
        question=dict_result["confirmation_question"],  # 用户可见问题。
        options=dict_result["install_options"],  # 安装目标选项。
        default="skip",  # 安全默认是不写入本地技能目录。
        risk="medium",  # 本地安装具有中等文件变更风险。
        next_action="run install_skill.py with the selected target after release validation",  # 选择后的执行动作。
        context={  # 当前发布身份上下文。
            "release_dir": dict_checks["expected_release_dir"],  # 已验证发布目录。
            "version": dict_context["version"],  # 已验证发布版本。
        },
    )

# 公共入口按 pre/post 阶段编排全部发布门禁。
def release_gate(
    project: Path,
    version: str,
    skill_dir_raw: str,
    phase: str,
    install_intent: str,
    test_evidence_raw: str = "",
    bool_require_test_evidence: bool = False,
) -> dict[str, Any]:
    """执行发布前或发布后强治理门禁。

    参数：project、version 和 skill_dir_raw 定位目标发布。
    参数：phase 为 pre/post，install_intent 为用户安装意图。
    参数：test_evidence_raw 非空时启用发布态远程测试收据验证。
    参数：bool_require_test_evidence 为 True 时拒绝缺失收据。
    返回：包含检查证据、错误和可安装状态的结果。
    """

    # worktree 策略必须在读取或生成发布产物前执行。
    dict_worktree_policy = inspect_worktree_policy(project)  # 当前仓库 worktree 策略报告。

    # 额外 worktree 或污染目录触发不可绕过的硬阻断。
    if dict_worktree_policy.get("hard_blocking", False):

        # 返回专用硬阻断载荷。
        return blocked_release_result(project, dict_worktree_policy)

    # 收集后续阶段共享的路径、Git 和配置事实。
    dict_context = collect_release_gate_context(  # 发布门禁上下文。
        project, version, skill_dir_raw, phase, install_intent  # 公共入口全部发布参数。
    )  # 完成路径、Git 和治理配置事实收集。

    # 基础 checks 在后续验证中持续补充。
    dict_checks = build_release_checks(dict_context)  # 发布检查证据映射。

    # 所有阶段共享有序错误列表。
    list_errors: list[str] = []  # 发布门禁阻断诊断。

    # 提供收据时必须与当前 Git tests 树、非测试源码和 freshness 一致。
    dict_test_evidence = validate_project_test_evidence(  # 不透明测试证据结果。
        project,  # 当前发布仓库。
        test_evidence_raw,  # 调用方收据输入。
        bool_required=bool_require_test_evidence,  # CLI 发布态拒绝缺失收据。
    )

    # 门禁结果只公开脱敏统计和稳定错误码。
    dict_checks["test_evidence"] = dict_test_evidence  # 门禁公开脱敏验证结论。

    # 任一证据错误都必须阻断后续可安装结论。
    list_errors.extend(dict_test_evidence["errors"])  # 任一证据错误均 fail closed。

    # 执行版本、文档、源码、内容和 Git 共同检查。
    list_forbidden_source_paths = validate_common_release_checks(  # 共同检查返回的源码策略路径。
        dict_context,  # 共同门禁发布事实。
        dict_checks,  # 共同门禁检查证据。
        list_errors,  # 共同门禁阻断诊断。
    )  # 完成 pre/post 共同治理检查。

    # post 阶段额外验证实际生成的目录、ZIP 和收据。
    if phase == "post":

        # 发布后产物必须通过完整强验证。
        validate_post_release_artifacts(dict_context, dict_checks, list_forbidden_source_paths, list_errors)

    # 两个阶段都拒绝版本低于历史最新发布。
    validate_latest_release_version(dict_context, dict_checks, list_errors)

    # 汇总机器可读门禁结果。
    dict_result = build_release_gate_result(  # 发布门禁结果。
        dict_context,  # 结果使用的发布身份事实。
        dict_checks,  # 结果公开的完整检查证据。
        list_forbidden_source_paths,  # 结果公开的源码策略证据。
        list_errors,  # 全部阻断诊断。
    )  # 完成可安装性和内容策略状态汇总。

    # 根据阶段、项目类型和用户意图附加安装确认。
    attach_install_confirmation(dict_context, dict_checks, dict_result)

    # 返回稳定机器协议。
    return dict_result
