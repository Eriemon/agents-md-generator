def release_gate(project: Path, version: str, skill_dir_raw: str, phase: str, install_intent: str) -> dict[str, Any]:

    # 整理 release_gate 需要的 profile 发布信息。
    profile = read_json(project / ".agents" / "agents-control.json")  # release 打包校验输入值

    # 整理 release_gate 需要的 skill dir 发布信息。
    skill_dir = resolve_project(skill_dir_raw if Path(skill_dir_raw).is_absolute() else project / skill_dir_raw)  # release 打包校验输入值

    # 整理 release_gate 需要的 skill name 发布信息。
    skill_name = skill_dir.name  # release 打包校验输入值

    # 整理 release_gate 需要的 project kind 发布信息。
    str_project_kind = release_project_kind(project, skill_dir)  # release 打包校验输入值

    # 整理 release_gate 需要的 expected release 发布信息。
    expected_release = project / "dist" / f"{skill_name}-{version}"  # release 打包校验输入值

    # 整理 release_gate 需要的 expected zip 发布信息。
    expected_zip = project / "dist" / f"{skill_name}-{version}.zip"  # release 打包校验输入值

    # 整理 release_gate 需要的 source rel 发布信息。
    source_rel = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else skill_dir.name  # release 打包校验输入值

    # 定位 receipt path 的文件边界，供 release_gate 后续读写校验使用。
    receipt_path = expected_release / receipt_filename(profile)  # release 打包校验输入值

    # 整理 release_gate 需要的 source version 发布信息。
    source_version = read_skill_version(skill_dir)  # release 打包校验输入值

    # 整理 release_gate 需要的 git branch 发布信息。
    git_branch = run_git(project, ["branch", "--show-current"]).stdout.strip()  # release 打包校验输入值

    # 汇总 branches，作为 release 打包和清理候选清单。
    branches = sorted(normalize_branch_list_line(line) for line in run_git(project, ["branch", "--list"]).stdout.splitlines() if line.strip())  # release 打包校验输入值

    # 汇总 status lines，作为 release 打包和清理候选清单。
    list_status_lines = filter_runtime_status_lines(run_git(project, ["status", "--short"]).stdout.splitlines())  # release 打包校验输入值

    # 汇总 errors，作为 release 打包和清理候选清单。
    list_errors: list[str] = []  # release 打包校验输入值

    # release-gate 是发布前后的共同入口，也必须拒绝非法版本号。
    str_version_error = version_policy_error(version)  # release 版本策略诊断

    # 校验 release_gate 的 release 分支条件。
    if str_version_error:

        # 追加 release_gate 的 release 诊断。
        list_errors.append(str_version_error)

    # 汇总 checks，作为 release 打包和清理候选清单。
    dict_checks = {  # release 打包校验输入值
        "branch": git_branch,  # release 打包校验输入值
        "local_branches": branches,  # release 打包校验输入值
        "phase": phase,  # release 打包校验输入值
        "install_intent": install_intent,  # release 打包校验输入值
        "project_kind": str_project_kind,  # release 打包校验输入值
        "skill_dir": skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else str(skill_dir),  # release 打包校验输入值
        "source_version": source_version,  # release 打包校验输入值
        "expected_release_dir": expected_release.relative_to(project).as_posix(),  # release 打包校验输入值
        "expected_release_zip": expected_zip.relative_to(project).as_posix(),  # release 打包校验输入值
        "receipt_path": expected_release.joinpath(receipt_filename(profile)).relative_to(project).as_posix(),  # release 打包校验输入值
        "status_lines": list_status_lines,  # release 打包校验输入值
    }

    # 整理 release_gate 需要的 docs verify 发布信息。
    docs_verify = verify_docs(project) if docs_governance_initialized(project) else {"project": str(project), "checked": [], "errors": []}  # release 打包校验输入值

    # 校验 release_gate 的 release 分支条件。
    if docs_verify.get("errors"):

        # 调用 extend 处理 release_gate。
        list_errors.extend(f"docs-verify: {item}" for item in docs_verify["errors"])

    # 整理 release_gate 需要的 中间载荷 发布信息。
    dict_checks["docs_verify_ok"] = not docs_verify.get("errors")  # release 打包校验输入值

    # 整理 release_gate 需要的 source governance 发布信息。
    source_governance = source_governance_report(project, profile)  # release 打包校验输入值

    # 调用 extend 处理 release_gate。
    list_errors.extend(format_source_governance_errors(source_governance, prefix="source-governance"))

    # 整理 release_gate 需要的 中间载荷 发布信息。
    dict_checks["source_governance_ok"] = source_governance["ok"]  # release 打包校验输入值

    # 保存 source content 映射，维持 release_gate 的字段关系。
    dict_source_content = source_release_content_analysis(skill_dir)  # release 打包校验输入值

    # 汇总 forbidden source paths，作为 release 打包和清理候选清单。
    forbidden_source_paths = dict_source_content["forbidden_paths"]  # release 打包校验输入值

    # 整理 release_gate 需要的 中间载荷 发布信息。
    dict_checks["policy_version"] = POLICY_VERSION  # release 打包校验输入值

    # 整理 release_gate 需要的 中间载荷 发布信息。
    dict_checks["forbidden_source_paths"] = forbidden_source_paths  # release 打包校验输入值

    # 整理 release_gate 需要的 中间载荷 发布信息。
    dict_checks["source_release_content_top_level"] = dict_source_content["included_top_level_entries"]  # release 打包校验输入值

    # 校验 release_gate 的 release 分支条件。
    if forbidden_source_paths:

        # 追加 release_gate 的 release 诊断。
        list_errors.append("release content policy rejected forbidden development content in skill source")

    # 汇总 other release exclusions，作为 release 打包和清理候选清单。
    set_other_release_exclusions = release_target_exclusions(skill_name, version)  # release 打包校验输入值

    # 校验 release_gate 的 release 分支条件。
    if source_version and source_version != version:

        # 追加 release_gate 的 release 诊断。
        list_errors.append(f"release gate version {version} does not match skill source version {source_version}")

    # 校验 release_gate 的 release 分支条件。
    if git_branch != "master":

        # 追加 release_gate 的 release 诊断。
        list_errors.append("release gate requires current branch master")

    # 校验 release_gate 的 release 分支条件。
    if sorted(branches) != ["master", "release"]:

        # 追加 release_gate 的 release 诊断。
        list_errors.append("release gate requires only local branches master and release")

    # 校验 release_gate 的 release 分支条件。
    if phase == "pre" and list_status_lines:

        # 追加 release_gate 的 release 诊断。
        list_errors.append("pre-release gate requires a clean committed worktree")

    # 校验 release_gate 的 release 分支条件。
    if phase == "post":

        # 校验 release_gate 的 release 分支条件。
        if list_status_lines:

            # 追加 release_gate 的 release 诊断。
            list_errors.append("post-release gate requires a clean committed worktree")

        # 校验 release_gate 的 release 分支条件。
        if not expected_release.is_dir():

            # 追加 release_gate 的 release 诊断。
            list_errors.append(f"missing release directory: {expected_release.relative_to(project).as_posix()}")

        # 校验 release_gate 的 release 分支条件。
        if not expected_zip.is_file():

            # 追加 release_gate 的 release 诊断。
            list_errors.append(f"missing release zip: {expected_zip.relative_to(project).as_posix()}")

        # 校验 release_gate 的 release 分支条件。
        if expected_release.is_dir():

            # 整理 release_gate 需要的 release governance 发布信息。
            release_governance = release_source_governance_report(  # release 打包校验输入值
                project,  # release 打包校验输入值
                expected_release,  # release 打包校验输入值
                profile,  # release 打包校验输入值
                source_relative_prefix=source_rel,  # release 打包校验输入值
            )

            # 调用 extend 处理 release_gate。
            list_errors.extend(format_source_governance_errors(release_governance, prefix="release-source-governance"))

            # 整理 release_gate 需要的 中间载荷 发布信息。
            dict_checks["release_source_governance_ok"] = release_governance["ok"]  # release 打包校验输入值

            # 保存 release content 映射，维持 release_gate 的字段关系。
            dict_release_content = release_tree_content_analysis(expected_release)  # release 打包校验输入值

            # 整理 release_gate 需要的 中间载荷 发布信息。
            dict_checks["release_content_top_level"] = dict_release_content["included_top_level_entries"]  # release 打包校验输入值

            # 整理 release_gate 需要的 中间载荷 发布信息。
            dict_checks["unexpected_release_top_level_entries"] = dict_release_content["unexpected_top_level_entries"]  # release 打包校验输入值

            # 整理 release_gate 需要的 中间载荷 发布信息。
            dict_checks["forbidden_release_paths"] = dict_release_content["forbidden_paths"]  # release 打包校验输入值

            # 汇总 source files，作为 release 打包和清理候选清单。
            list_source_files = release_members(skill_dir, skill_dir)  # release 打包校验输入值

            # 汇总 release files，作为 release 打包和清理候选清单。
            release_files = sorted(item["path"] for item in build_release_file_manifest(expected_release, exclude={receipt_path.name}))  # release 打包校验输入值

            # 校验 release_gate 的 release 分支条件。
            if list_source_files != release_files:

                # 追加 release_gate 的 release 诊断。
                list_errors.append("release parity mismatch between skill source and dist release directory")

            # 校验 release_gate 的 release 分支条件。
            if not receipt_path.is_file():

                # 追加 release_gate 的 release 诊断。
                list_errors.append(f"missing release receipt: {receipt_path.relative_to(project).as_posix()}")
            else:

                # 保存 receipt 映射，维持 release_gate 的字段关系。
                dict_receipt = read_release_receipt(receipt_path)  # release 打包校验输入值

                # 汇总 policy errors，作为 release 打包和清理候选清单。
                list_policy_errors = verify_release_content_policy(  # release 打包校验输入值
                    dict_receipt,  # release 打包校验输入值
                    source_forbidden_paths=forbidden_source_paths,  # release 打包校验输入值
                    release_analysis=dict_release_content,  # release 打包校验输入值
                    require_source_paths=True,  # release 打包校验输入值
                )

                # 整理 release_gate 需要的 中间载荷 发布信息。
                dict_checks["release_content_policy_errors"] = list_policy_errors  # release 打包校验输入值

                # 调用 extend 处理 release_gate。
                list_errors.extend(list_policy_errors)

                # 调用 extend 处理 release_gate。
                list_errors.extend(
                    verify_release_receipt(
                        project,
                        receipt_path,
                        expected_release,
                        skill_name,
                        version,

                        # 分隔当前密集代码块，保留原有执行顺序。
                        source_rel,
                        require_repo_dist=True,
                    )
                )

                # 调用 extend 处理 release_gate。
                list_errors.extend(
                    verify_release_sanitization(
                        profile,
                        str_project_kind,
                        skill_dir,
                        expected_release,
                        dict_receipt,

                        # 分隔当前密集代码块，保留原有执行顺序。
                    )
                )

                # 汇总 recorded other artifacts，作为 release 打包和清理候选清单。
                recorded_other_artifacts = dict_receipt.get("other_version_artifacts")  # release 打包校验输入值

                # 校验 release_gate 的 release 分支条件。
                if not isinstance(recorded_other_artifacts, list):

                    # 追加 release_gate 的 release 诊断。
                    list_errors.append("release receipt missing other_version_artifacts snapshot")
                else:

                    # 汇总 current other artifacts，作为 release 打包和清理候选清单。
                    list_current_other_artifacts = dist_artifact_snapshot(project, set_other_release_exclusions)  # release 打包校验输入值

                    # 整理 release_gate 需要的 中间载荷 发布信息。
                    dict_checks["other_version_artifact_count"] = len(list_current_other_artifacts)  # release 打包校验输入值

                    # 校验 release_gate 的 release 分支条件。
                    if list_current_other_artifacts != recorded_other_artifacts:

                        # 追加 release_gate 的 release 诊断。
                        list_errors.append("cross-version release artifacts changed outside the current target release")

    # 整理 release_gate 需要的 latest 发布信息。
    latest = latest_release_dir(project, skill_name)  # release 打包校验输入值

    # 校验 release_gate 的 release 分支条件。
    if latest is not None:

        # 整理 release_gate 需要的 中间载荷 发布信息。
        dict_checks["latest_release_dir"] = latest.relative_to(project).as_posix()  # release 打包校验输入值

        # 校验 release_gate 的 release 分支条件。
        if parse_version_tuple(version) < parse_historical_version_tuple(latest.name.rsplit("-", 1)[-1]):

            # 追加 release_gate 的 release 诊断。
            list_errors.append("requested release version is older than the latest dist release")

    # 保存 result 映射，维持 release_gate 的字段关系。
    dict_result = {  # release 打包校验输入值
        "project": str(project),  # release 打包校验输入值
        "ok": not list_errors,  # release 打包校验输入值
        "errors": list_errors,  # release 打包校验输入值
        "checks": dict_checks,  # release 打包校验输入值
        "installable": not list_errors and phase == "post",  # release 打包校验输入值
        "receipt_path": dict_checks["receipt_path"],  # release 打包校验输入值
        "provenance_mode": "repository-dist",  # release 打包校验输入值
        "validation_level": "strong",  # release 打包校验输入值
        "policy_version": POLICY_VERSION,  # release 打包校验输入值
        "forbidden_source_paths": forbidden_source_paths,  # release 打包校验输入值
        "forbidden_release_paths": dict_checks.get("forbidden_release_paths", []),  # release 打包校验输入值
        "release_content_policy_ok": not forbidden_source_paths  # release 打包校验输入值
        and not dict_checks.get("forbidden_release_paths", [])  # release 打包校验输入值
        and not dict_checks.get("unexpected_release_top_level_entries", [])  # release 打包校验输入值
        and not dict_checks.get("release_content_policy_errors", []),  # release 打包校验输入值
    }

    # 校验 release_gate 的 release 分支条件。
    if phase == "post" and install_intent == "unspecified" and str_project_kind == "skill":

        # 整理 release_gate 需要的 中间载荷 发布信息。
        dict_result["install_confirmation_required"] = True  # release 打包校验输入值

        # 整理 release_gate 需要的 中间载荷 发布信息。
        dict_result["confirmation_question"] = "释放安装版本后，用户尚未说明是否需要安装。是否需要安装当前发布包？"  # release 打包校验输入值

        # 整理 release_gate 需要的 中间载荷 发布信息。
        dict_result["install_options"] = install_confirmation_options()  # release 打包校验输入值

        # 整理 release_gate 需要的 中间载荷 发布信息。
        dict_result["decision_request"] = decision_request(  # release 打包校验输入值
            "install_confirmation",  # release 打包校验输入值
            question=dict_result["confirmation_question"],  # release 打包校验输入值
            options=dict_result["install_options"],  # release 打包校验输入值
            default="skip",  # release 打包校验输入值
            risk="medium",  # release 打包校验输入值
            next_action="run install_skill.py with the selected target after release validation",  # release 打包校验输入值
            context={"release_dir": dict_checks["expected_release_dir"], "version": version},  # release 打包校验输入值
        )
    else:

        # 整理 release_gate 需要的 中间载荷 发布信息。
        dict_result["install_confirmation_required"] = False  # release 打包校验输入值

        # 整理 release_gate 需要的 中间载荷 发布信息。
        dict_result["decision_request"] = {}  # release 打包校验输入值

    # 返回 release_gate 的 release 载荷。
    return dict_result
