def release_prepare(project: Path, version: str, skill_dir_raw: str) -> dict[str, Any]:

    # 整理 release_prepare 需要的 profile 发布信息。
    profile = read_json(project / ".agents" / "agents-control.json")  # release 打包校验输入值

    # 整理 release_prepare 需要的 skill dir 发布信息。
    skill_dir = resolve_project(skill_dir_raw if Path(skill_dir_raw).is_absolute() else project / skill_dir_raw)  # release 打包校验输入值

    # 汇总 current branch、local branches、status lines，作为 release 打包和清理候选清单。
    tuple_current_branch, tuple_local_branches, tuple_status_lines = current_branch_and_locals(project)  # release 打包校验输入值

    # 整理 release_prepare 需要的 protected 发布信息。
    protected = sorted((profile.get("git_branch_policy", {}) or {}).get("protected_branches", ["master", "release"]))  # release 打包校验输入值

    # 汇总 extras，作为 release 打包和清理候选清单。
    extras = sorted(branch for branch in tuple_local_branches if branch not in protected)  # release 打包校验输入值

    # 汇总 errors，作为 release 打包和清理候选清单。
    list_errors: list[str] = []  # release 打包校验输入值

    # 发布版本在进入 git/文件操作前先过策略门禁，避免生成非法历史产物。
    str_version_error = version_policy_error(version)  # release 版本策略诊断

    # 校验 release_prepare 的 release 分支条件。
    if str_version_error:

        # 追加 release_prepare 的 release 诊断。
        list_errors.append(str_version_error)

        # 返回 release_prepare 的 release 载荷。
        return {"ok": False, "errors": list_errors, "checks": {"version": version}}

    # 汇总 checks，作为 release 打包和清理候选清单。
    dict_checks: dict[str, Any] = {  # release 打包校验输入值
        "current_branch": tuple_current_branch,  # release 打包校验输入值
        "local_branches": tuple_local_branches,  # release 打包校验输入值
        "protected_branches": protected,  # release 打包校验输入值
        "prepared_branch": "",  # release 打包校验输入值
    }

    # 校验 release_prepare 的 release 分支条件。
    if not tuple_current_branch and not tuple_local_branches:

        # 追加 release_prepare 的 release 诊断。
        list_errors.append("release prepare requires a readable local git repository")

        # 返回 release_prepare 的 release 载荷。
        return {"ok": False, "errors": list_errors, "checks": dict_checks}

    # 校验 release_prepare 的 release 分支条件。
    if tuple_current_branch == "master":

        # 校验 release_prepare 的 release 分支条件。
        if len(extras) > 1:

            # 追加 release_prepare 的 release 诊断。
            list_errors.append(f"multiple extra local branches require manual resolution before release prepare: {extras}")

        # 校验 release_prepare 的 release 分支条件。
        elif len(extras) == 1:

            # 追加 release_prepare 的 release 诊断。
            list_errors.append(f"master cannot guess which extra local branch to prepare automatically: {extras[0]}")
        else:

            # 返回 release_prepare 的 release 载荷。
            return {"ok": True, "errors": [], "checks": dict_checks}

        # 返回 release_prepare 的 release 载荷。
        return {"ok": False, "errors": list_errors, "checks": dict_checks}

    # 校验 release_prepare 的 release 分支条件。
    if tuple_current_branch in protected:

        # 追加 release_prepare 的 release 诊断。
        list_errors.append(f"release prepare only handles temporary development branches, found protected branch {current_branch}")

        # 返回 release_prepare 的 release 载荷。
        return {"ok": False, "errors": list_errors, "checks": dict_checks}

    # 校验 release_prepare 的 release 分支条件。
    if extras != [tuple_current_branch]:

        # 追加 release_prepare 的 release 诊断。
        list_errors.append(f"release prepare requires exactly one temporary development branch, found {extras}")

        # 返回 release_prepare 的 release 载荷。
        return {"ok": False, "errors": list_errors, "checks": dict_checks}

    # 校验 release_prepare 的 release 分支条件。
    if (project / "AGENTS.md").exists():

        # 整理 release_prepare 需要的 sync override 发布信息。
        sync_override = skill_dir if skill_dir.name == "agents-md-generator" else None  # release 打包校验输入值

        # 整理 release_prepare 需要的 sync result 发布信息。
        sync_result = sync_root_agents(project, write=True, installed_skill_dir_override=sync_override)  # release 打包校验输入值

        # 整理 release_prepare 需要的 中间载荷 发布信息。
        dict_checks["root_agents_sync"] = {  # release 打包校验输入值
            "updated": sync_result.get("updated", False),  # release 打包校验输入值
            "reasons": sync_result.get("reasons", []),  # release 打包校验输入值
        }

        # 校验 release_prepare 的 release 分支条件。
        if sync_result.get("errors"):

            # 调用 extend 处理 release_prepare。
            list_errors.extend(sync_result["errors"])

            # 返回 release_prepare 的 release 载荷。
            return {"ok": False, "errors": list_errors, "checks": dict_checks}
    else:

        # 整理 release_prepare 需要的 中间载荷 发布信息。
        dict_checks["root_agents_sync"] = {  # release 打包校验输入值
            "updated": False,  # release 打包校验输入值
            "reasons": ["missing_root_agents_md"],  # release 打包校验输入值
            "skipped": True,  # release 打包校验输入值
        }

    # 汇总 allowed，作为 release 打包和清理候选清单。
    list_allowed = governed_allowed_paths(profile, skill_dir, project)  # release 打包校验输入值

    # 汇总 changed、changed errors，作为 release 打包和清理候选清单。
    tuple_changed, tuple_changed_errors = changed_paths(project)  # release 打包校验输入值

    # 调用 extend 处理 release_prepare。
    list_errors.extend(tuple_changed_errors)

    # 整理 release_prepare 需要的 outside 发布信息。
    outside = [path for path in tuple_changed if not matches_governed_path(path, list_allowed)]  # release 打包校验输入值

    # 校验 release_prepare 的 release 分支条件。
    if outside:

        # 追加 release_prepare 的 release 诊断。
        list_errors.append(f"release prepare found changes outside governed release paths: {outside}")

        # 返回 release_prepare 的 release 载荷。
        return {"ok": False, "errors": list_errors, "checks": dict_checks}

    # 汇总 stage targets，作为 release 打包和清理候选清单。
    stage_targets = sorted(set(path for path in tuple_changed if matches_governed_path(path, list_allowed)))  # release 打包校验输入值

    # 校验 release_prepare 的 release 分支条件。
    if stage_targets and run_git(project, ["add", "--all", "--", *stage_targets]).returncode != 0:

        # 追加 release_prepare 的 release 诊断。
        list_errors.append("release prepare failed to stage governed release paths")

        # 返回 release_prepare 的 release 载荷。
        return {"ok": False, "errors": list_errors, "checks": dict_checks}

    # 整理 release_prepare 需要的 diff cached 发布信息。
    completed_process_diff_cached = run_git(project, ["diff", "--cached", "--quiet"])  # release 打包校验输入值

    # 校验 release_prepare 的 release 分支条件。
    if completed_process_diff_cached.returncode == 1:

        # 整理 release_prepare 需要的 commit message 发布信息。
        commit_message = f"release-prepare: stage {tuple_current_branch} for {version}"  # release 打包校验输入值

        # 整理 release_prepare 需要的 commit result 发布信息。
        completed_process_commit_result = run_git(project, ["commit", "-m", commit_message])  # release 打包校验输入值

        # 校验 release_prepare 的 release 分支条件。
        if completed_process_commit_result.returncode != 0:

            # 追加 release_prepare 的 release 诊断。
            list_errors.append(f"release prepare failed to commit staged changes: {(commit_result.stderr or commit_result.stdout).strip()}")

            # 返回 release_prepare 的 release 载荷。
            return {"ok": False, "errors": list_errors, "checks": dict_checks}

    # 校验 release_prepare 的 release 分支条件。
    elif completed_process_diff_cached.returncode not in {0, 1}:

        # 追加 release_prepare 的 release 诊断。
        list_errors.append("release prepare could not inspect staged changes")

        # 返回 release_prepare 的 release 载荷。
        return {"ok": False, "errors": list_errors, "checks": dict_checks}

    # 整理 release_prepare 需要的 checkout master 发布信息。
    completed_process_checkout_master = run_git(project, ["checkout", "master"])  # release 打包校验输入值

    # 校验 release_prepare 的 release 分支条件。
    if completed_process_checkout_master.returncode != 0:

        # 追加 release_prepare 的 release 诊断。
        list_errors.append(f"release prepare failed to checkout master: {(checkout_master.stderr or checkout_master.stdout).strip()}")

        # 返回 release_prepare 的 release 载荷。
        return {"ok": False, "errors": list_errors, "checks": dict_checks}

    # 整理 release_prepare 需要的 merge message 发布信息。
    merge_message = f"release-prepare: merge {tuple_current_branch} into master for {version}"  # release 打包校验输入值

    # 整理 release_prepare 需要的 merge 发布信息。
    completed_process_merge = run_git(project, ["merge", "--no-ff", tuple_current_branch, "-m", merge_message])  # release 打包校验输入值

    # 校验 release_prepare 的 release 分支条件。
    if completed_process_merge.returncode != 0:

        # 追加 release_prepare 的 release 诊断。
        list_errors.append(f"release prepare failed to merge {current_branch} into master: {(merge.stderr or merge.stdout).strip()}")

        # 返回 release_prepare 的 release 载荷。
        return {"ok": False, "errors": list_errors, "checks": dict_checks}

    # 整理 release_prepare 需要的 delete branch 发布信息。
    completed_process_delete_branch = run_git(project, ["branch", "-d", tuple_current_branch])  # release 打包校验输入值

    # 校验 release_prepare 的 release 分支条件。
    if completed_process_delete_branch.returncode != 0:

        # 追加 release_prepare 的 release 诊断。
        list_errors.append(f"release prepare failed to delete branch {current_branch}: {(delete_branch.stderr or delete_branch.stdout).strip()}")

        # 返回 release_prepare 的 release 载荷。
        return {"ok": False, "errors": list_errors, "checks": dict_checks}

    # 汇总 final branch、final locals、final status，作为 release 打包和清理候选清单。
    tuple_final_branch, tuple_final_locals, tuple_final_status = current_branch_and_locals(project)  # release 打包校验输入值

    # 调用 update 处理 release_prepare。
    dict_checks.update({
        "prepared_branch": tuple_current_branch,
        "current_branch": tuple_final_branch,
        "local_branches": tuple_final_locals,
        "status_lines": tuple_final_status,
    })

    # 校验 release_prepare 的 release 分支条件。
    if tuple_final_branch != "master":

        # 追加 release_prepare 的 release 诊断。
        list_errors.append("release prepare did not end on master")

    # 校验 release_prepare 的 release 分支条件。
    if sorted(tuple_final_locals) != protected:

        # 追加 release_prepare 的 release 诊断。
        list_errors.append(f"release prepare did not end with only protected branches {protected}")

    # 校验 release_prepare 的 release 分支条件。
    if tuple_final_status:

        # 追加 release_prepare 的 release 诊断。
        list_errors.append("release prepare requires a clean worktree after merge and branch cleanup")

    # 返回 release_prepare 的 release 载荷。
    return {"ok": not list_errors, "errors": list_errors, "checks": dict_checks}

# 定义 copy_release_tree 的release 管理处理入口。
def copy_release_tree(skill_dir: Path, release_dir: Path, included_files: list[str]) -> None:

    # 校验 copy_release_tree 的 release 分支条件。
    if release_dir.exists():

        # 调用 rmtree 处理 copy_release_tree。
        shutil.rmtree(release_dir)

    # 调用 mkdir 处理 copy_release_tree。
    release_dir.mkdir(parents=True, exist_ok=True)

    # 逐项检查 copy_release_tree 发布候选。
    for relative in included_files:

        # 整理 copy_release_tree 需要的 source 发布信息。
        source = skill_dir / relative  # release 打包校验输入值

        # 整理 copy_release_tree 需要的 target 发布信息。
        target = release_dir / relative  # release 打包校验输入值

        # 调用 mkdir 处理 copy_release_tree。
        target.parent.mkdir(parents=True, exist_ok=True)

        # 调用 copy2 处理 copy_release_tree。
        shutil.copy2(source, target)

# 定义 package_release 的release 管理处理入口。
def package_release(project: Path, version: str, skill_dir_raw: str) -> dict[str, Any]:

    # 发布版本在进入 pre-gate 前先过策略门禁，避免非法版本触发后续写入。
    str_version_error = version_policy_error(version)  # release 版本策略诊断

    # 校验 package_release 的 release 分支条件。
    if str_version_error:

        # 返回 package_release 的 release 载荷。
        return {
            "ok": False,
            "errors": [str_version_error],
            "policy_version": POLICY_VERSION,
            "forbidden_source_paths": [],
            "forbidden_release_paths": [],
            "release_content_policy_ok": False,
        }

    # 整理 package_release 需要的 profile 发布信息。
    profile = read_json(project / ".agents" / "agents-control.json")  # release 打包校验输入值

    # 整理 package_release 需要的 skill dir 发布信息。
    skill_dir = resolve_project(skill_dir_raw if Path(skill_dir_raw).is_absolute() else project / skill_dir_raw)  # release 打包校验输入值

    # 整理 package_release 需要的 skill name 发布信息。
    skill_name = skill_dir.name  # release 打包校验输入值

    # 整理 package_release 需要的 source rel 发布信息。
    source_rel = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else skill_dir.name  # release 打包校验输入值

    # 整理 package_release 需要的 project kind 发布信息。
    str_project_kind = release_project_kind(project, skill_dir)  # release 打包校验输入值

    # 保存 pre 映射，维持 package_release 的字段关系。
    dict_pre = release_gate(project, version, skill_dir_raw, "pre", "unspecified")  # release 打包校验输入值

    # 校验 package_release 的 release 分支条件。
    if dict_pre["errors"]:

        # 返回 package_release 的 release 载荷。
        return {
            "ok": False,
            "errors": dict_pre["errors"],
            "pre_gate": dict_pre,
            "policy_version": dict_pre.get("policy_version", POLICY_VERSION),
            "forbidden_source_paths": dict_pre.get("forbidden_source_paths", []),
            "forbidden_release_paths": dict_pre.get("forbidden_release_paths", []),
            "release_content_policy_ok": dict_pre.get("release_content_policy_ok", False),
        }

    # 整理 package_release 需要的 release dir 发布信息。
    release_dir = project / "dist" / f"{skill_name}-{version}"  # release 打包校验输入值

    # 定位 zip path 的文件边界，供 package_release 后续读写校验使用。
    zip_path = project / "dist" / f"{skill_name}-{version}.zip"  # release 打包校验输入值

    # 汇总 other release exclusions，作为 release 打包和清理候选清单。
    set_other_release_exclusions = release_target_exclusions(skill_name, version)  # release 打包校验输入值

    # 汇总 before other artifacts，作为 release 打包和清理候选清单。
    list_before_other_artifacts = dist_artifact_snapshot(project, set_other_release_exclusions)  # release 打包校验输入值

    # 保存 source content 映射，维持 package_release 的字段关系。
    dict_source_content = source_release_content_analysis(skill_dir)  # release 打包校验输入值

    # 汇总 forbidden source paths，作为 release 打包和清理候选清单。
    forbidden_source_paths = dict_source_content["forbidden_paths"]  # release 打包校验输入值

    # 校验 package_release 的 release 分支条件。
    if forbidden_source_paths:

        # 返回 package_release 的 release 载荷。
        return {
            "ok": False,
            "errors": ["package release rejected forbidden development content in skill source"],
            "pre_gate": dict_pre,
            "release_dir": display_path(release_dir, project),
            "policy_version": POLICY_VERSION,
            "forbidden_source_paths": forbidden_source_paths,
            "forbidden_release_paths": [],
            "release_content_policy_ok": False,
        }

    # 调用 copy_release_tree 处理 package_release。
    copy_release_tree(skill_dir, release_dir, dict_source_content["included_files"])

    # 定位 receipt path 的文件边界，供 package_release 后续读写校验使用。
    receipt_path = release_dir / receipt_filename(profile)  # release 打包校验输入值

    # 汇总 sanitization、sanitization errors，作为 release 打包和清理候选清单。
    tuple_sanitization, tuple_sanitization_errors = sanitize_release_tree(profile, str_project_kind, skill_dir, release_dir)  # release 打包校验输入值

    # 校验 package_release 的 release 分支条件。
    if tuple_sanitization_errors:

        # 返回 package_release 的 release 载荷。
        return {
            "ok": False,
            "errors": tuple_sanitization_errors,
            "pre_gate": dict_pre,
            "release_dir": display_path(release_dir, project),
        }

    # 汇总 after other artifacts，作为 release 打包和清理候选清单。
    list_after_other_artifacts = dist_artifact_snapshot(project, set_other_release_exclusions)  # release 打包校验输入值

    # 校验 package_release 的 release 分支条件。
    if list_before_other_artifacts != list_after_other_artifacts:

        # 返回 package_release 的 release 载荷。
        return {
            "ok": False,
            "errors": ["cross-version release artifacts changed outside the current target release directory or zip"],
            "pre_gate": dict_pre,
            "release_dir": display_path(release_dir, project),
        }

    # 保存 release content 映射，维持 package_release 的字段关系。
    dict_release_content = release_tree_content_analysis(release_dir)  # release 打包校验输入值

    # 整理 package_release 需要的 release policy 发布信息。
    release_policy = release_content_policy_receipt(  # release 打包校验输入值
        dict_release_content,  # release 打包校验输入值
        forbidden_source_paths=forbidden_source_paths,  # release 打包校验输入值
    )

    # 保存 receipt 映射，维持 package_release 的字段关系。
    dict_receipt = {  # release 打包校验输入值
        "skill_name": skill_name,  # release 打包校验输入值
        "version": version,  # release 打包校验输入值
        "source_path": source_rel,  # release 打包校验输入值
        "generated_at": datetime.now().isoformat(timespec="seconds"),  # release 打包校验输入值
        "current_branch": "master",  # release 打包校验输入值
        "local_branches": ["master", "release"],  # release 打包校验输入值
        "worktree_clean": True,  # release 打包校验输入值
        "phase_results": {"pre": True, "post": True},  # release 打包校验输入值
        "packaging_mode": "repository-dist",  # release 打包校验输入值
        "validation_level": "strong",  # release 打包校验输入值
        "provenance_mode": "repository-dist",  # release 打包校验输入值
        "sanitization": tuple_sanitization,  # release 打包校验输入值
        "release_content_policy": release_policy,  # release 打包校验输入值
        "files": build_release_file_manifest(release_dir),  # release 打包校验输入值
        "other_version_artifacts": list_after_other_artifacts,  # release 打包校验输入值
    }

    # 调用 write_text 处理 package_release。
    receipt_path.write_text(json.dumps(dict_receipt, indent=2), encoding="utf-8")

    # 调用 write_release_zip 处理 package_release。
    write_release_zip(release_dir, zip_path)

    # 整理 package_release 需要的 add result 发布信息。
    completed_process_add_result = run_git(project, ["add", "--all", "--", "dist"])  # release 打包校验输入值

    # 校验 package_release 的 release 分支条件。
    if completed_process_add_result.returncode != 0:

        # 返回 package_release 的 release 载荷。
        return {"ok": False, "errors": ["package release failed to stage dist artifacts"], "pre_gate": dict_pre}

    # 整理 package_release 需要的 diff cached 发布信息。
    completed_process_diff_cached = run_git(project, ["diff", "--cached", "--quiet"])  # release 打包校验输入值

    # 校验 package_release 的 release 分支条件。
    if completed_process_diff_cached.returncode == 1:

        # 整理 package_release 需要的 commit result 发布信息。
        completed_process_commit_result = run_git(project, ["commit", "-m", f"package-release: {skill_name} {version}"])  # release 打包校验输入值

        # 校验 package_release 的 release 分支条件。
        if completed_process_commit_result.returncode != 0:

            # git commit 失败时优先保留 stderr，缺失时再使用 stdout。
            commit_output = completed_process_commit_result.stderr or completed_process_commit_result.stdout  # dist 提交原始诊断

            # 去掉首尾空白后写入 JSON，保持错误字段稳定。
            commit_failure = commit_output.strip()  # dist 提交失败诊断文本

            # 返回 package_release 的 release 载荷。
            return {
                "ok": False,
                "errors": [f"package release failed to commit dist artifacts: {commit_failure}"],
                "pre_gate": dict_pre,
            }

    # 校验 package_release 的 release 分支条件。
    elif completed_process_diff_cached.returncode not in {0, 1}:

        # 返回 package_release 的 release 载荷。
        return {"ok": False, "errors": ["package release could not inspect staged release artifacts"], "pre_gate": dict_pre}

    # 保存 post 映射，维持 package_release 的字段关系。
    dict_post = release_gate(project, version, skill_dir_raw, "post", "unspecified")  # release 打包校验输入值

    # 返回 package_release 的 release 载荷。
    return {
        "ok": not dict_post["errors"],
        "errors": dict_post["errors"],
        "release_dir": display_path(release_dir, project),
        "release_zip": display_path(zip_path, project),
        "receipt_path": display_path(receipt_path, project),
        "pre_gate": dict_pre,
        "post_gate": dict_post,
        "policy_version": POLICY_VERSION,
        "forbidden_source_paths": forbidden_source_paths,
        "forbidden_release_paths": dict_release_content["forbidden_paths"],
        "release_content_policy_ok": not dict_release_content["unexpected_top_level_entries"] and not dict_release_content["forbidden_paths"],
    }

# 定义 branch_gate 的release 管理处理入口。
def branch_gate(project: Path) -> dict[str, Any]:

    # 整理 branch_gate 需要的 profile 发布信息。
    profile = read_json(project / ".agents" / "agents-control.json")  # release 打包校验输入值

    # 校验 branch_gate 的 release 分支条件。
    if not isinstance(profile, dict):

        # 返回 branch_gate 的 release 载荷。
        return {
            "project": str(project),
            "approved": True,
            "decision": "approved",
            "reasons": [],
            "checks": {"skipped": "no control profile"},
            "force_confirmation_required": False,
            "user_message": "",
        }

    # 校验 branch_gate 的 release 分支条件。
    if str(profile.get("git_management", "")).strip() == "no-git-management":

        # 返回 branch_gate 的 release 载荷。
        return {
            "project": str(project),
            "approved": True,
            "decision": "approved",
            "reasons": [],
            "checks": {"skipped": "git management disabled"},
            "force_confirmation_required": False,
            "user_message": "",
        }

    # 整理 branch_gate 需要的 policy 发布信息。
    policy = profile.get("git_branch_policy", {}) if isinstance(profile.get("git_branch_policy"), dict) else {}  # release 打包校验输入值

    # 整理 branch_gate 需要的 protected 发布信息。
    protected = policy.get("protected_branches", ["master", "release"])  # release 打包校验输入值

    # 整理 branch_gate 需要的 branch model 发布信息。
    branch_model = str(profile.get("branch_model", "")).strip()  # release 打包校验输入值

    # 整理 branch_gate 需要的 git branch result 发布信息。
    completed_process_git_branch_result = run_git(project, ["branch", "--show-current"])  # release 打包校验输入值

    # 整理 branch_gate 需要的 git list result 发布信息。
    completed_process_git_list_result = run_git(project, ["branch", "--list"])  # release 打包校验输入值

    # 整理 branch_gate 需要的 git status result 发布信息。
    completed_process_git_status_result = run_git(project, ["status", "--short"])  # release 打包校验输入值

    # 汇总 reasons，作为 release 打包和清理候选清单。
    list_reasons: list[str] = []  # release 打包校验输入值

    # 汇总 checks，作为 release 打包和清理候选清单。
    dict_checks: dict[str, Any] = {  # release 打包校验输入值
        "branch_model": branch_model,  # release 打包校验输入值
        "protected_branches": protected,  # release 打包校验输入值
        "current_branch": "",  # release 打包校验输入值
        "local_branches": [],  # release 打包校验输入值
        "status_lines": [],  # release 打包校验输入值
    }

    # 校验 branch_gate 的 release 分支条件。
    if any(result.returncode != 0 for result in [completed_process_git_branch_result, completed_process_git_list_result, completed_process_git_status_result]):

        # 追加 branch_gate 的 release 诊断。
        list_reasons.append("git branch governance requires a readable local git repository")
    else:

        # 整理 branch_gate 需要的 current branch 发布信息。
        current_branch = completed_process_git_branch_result.stdout.strip()  # release 打包校验输入值

        # 汇总 local branches，作为 release 打包和清理候选清单。
        local_branches = sorted(normalize_branch_list_line(line) for line in completed_process_git_list_result.stdout.splitlines() if line.strip())  # release 打包校验输入值

        # 汇总 status lines，作为 release 打包和清理候选清单。
        list_status_lines = filter_runtime_status_lines(completed_process_git_status_result.stdout.splitlines())  # release 打包校验输入值

        # 整理 branch_gate 需要的 中间载荷 发布信息。
        dict_checks["current_branch"] = current_branch  # release 打包校验输入值

        # 整理 branch_gate 需要的 中间载荷 发布信息。
        dict_checks["local_branches"] = local_branches  # release 打包校验输入值

        # 整理 branch_gate 需要的 中间载荷 发布信息。
        dict_checks["status_lines"] = list_status_lines  # release 打包校验输入值

        # 校验 branch_gate 的 release 分支条件。
        if branch_model == "master-and-dist-release":

            # 校验 branch_gate 的 release 分支条件。
            if current_branch != "master":

                # 追加 branch_gate 的 release 诊断。
                list_reasons.append(f"current branch must be master, found {current_branch or 'unknown'}")

            # 校验 branch_gate 的 release 分支条件。
            if sorted(local_branches) != sorted(protected):

                # 追加 branch_gate 的 release 诊断。
                list_reasons.append(f"local branches must match protected branch set {protected}, found {local_branches}")

        # 校验 branch_gate 的 release 分支条件。
        if list_status_lines:

            # 追加 branch_gate 的 release 诊断。
            list_reasons.append("worktree must be clean before continuing under strict branch governance")

    # 整理 branch_gate 需要的 approved 发布信息。
    approved = not list_reasons  # release 打包校验输入值

    # 汇总 cleanup plan，作为 release 打包和清理候选清单。
    list_cleanup_plan = []  # release 打包校验输入值

    # 校验 branch_gate 的 release 分支条件。
    if not approved:

        # 汇总 cleanup plan，作为 release 打包和清理候选清单。
        list_cleanup_plan = [  # release 打包校验输入值
            "commit or intentionally remove current worktree changes",  # release 打包校验输入值
            "switch back to master",  # release 打包校验输入值
            "merge or prepare any temporary development branch",  # release 打包校验输入值
            "delete local branches other than master and release after merge",  # release 打包校验输入值
            "rerun branch-gate",  # release 打包校验输入值
        ]

    # 汇总 classified reasons，作为 release 打包和清理候选清单。
    classified_reasons = [  # release 打包校验输入值
        {  # release 打包校验输入值
            "reason": reason,  # release 打包校验输入值
            "risk": "high" if "worktree" in reason or "branch" in reason else "medium",  # release 打包校验输入值
            "category": "branch-governance",  # release 打包校验输入值
        }
        for reason in list_reasons  # release 打包校验输入值
    ]

    # 返回 branch_gate 的 release 载荷。
    return {
        "project": str(project),
        "approved": approved,
        "decision": "approved" if approved else "blocked",
        "reasons": list_reasons,
        "classified_reasons": classified_reasons,
        "cleanup_plan": list_cleanup_plan,
        "checks": dict_checks,
        "force_confirmation_required": not approved,
        "user_message": "" if approved else "分支治理未通过，默认阻止普通生成/整理流程。若用户仍要继续，必须先明确确认是否进入分支整理或发布治理流程。",
        "decision_request": {} if approved else decision_request(
            "branch_governance",
            question="分支治理未通过。是否进入分支整理或发布治理流程？",
            options=[
                {"label": "进入治理整理", "value": "cleanup", "description": "按建议步骤整理分支和工作树后重跑门禁。", "recommended": True},
                {"label": "暂停当前任务", "value": "pause", "description": "保留现场，等待人工处理分支状态。", "recommended": False},
            ],
            default="cleanup",
            risk="high",
            next_action="run branch cleanup or release governance before continuing",
            context={"reasons": list_reasons, "cleanup_plan": list_cleanup_plan},
        ),
    }

# 定义 install_confirmation_options 的release 管理处理入口。
def install_confirmation_options() -> list[dict[str, Any]]:

    # 返回 install_confirmation_options 的 release 载荷。
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

# 定义 latest_release_dir 的release 管理处理入口。
def latest_release_dir(project: Path, skill_name: str) -> Path | None:

    # 汇总 releases，作为 release 打包和清理候选清单。
    list_releases = []  # release 打包校验输入值

    # 逐项检查 latest_release_dir 发布候选。
    for path in (project / "dist").glob(f"{skill_name}-v*"):

        # 校验 latest_release_dir 的 release 分支条件。
        if not path.is_dir():

            # 分隔 latest_release_dir 的控制流边界。
            continue

        # 整理 latest_release_dir 需要的 match 发布信息。
        match = re.search(r"v(\d+)\.(\d+)\.(\d+)", path.name)  # release 打包校验输入值

        # 校验 latest_release_dir 的 release 分支条件。
        if match:

            # 追加 latest_release_dir 的 release 诊断。
            list_releases.append((tuple(int(part) for part in match.groups()), path))

    # 校验 latest_release_dir 的 release 分支条件。
    if not list_releases:

        # 返回 latest_release_dir 的 release 载荷。
        return None

    # 调用 sort 处理 latest_release_dir。
    list_releases.sort(key=lambda item: item[0])

    # 返回 latest_release_dir 的 release 载荷。
    return list_releases[-1][1]

# 定义 release_members 的release 管理处理入口。
def release_members(root: Path, prefix: Path) -> list[str]:

    # 汇总 analysis，作为 release 打包和清理候选清单。
    analysis = analyze_release_content_root(root)  # release 打包校验输入值

    # 校验 release_members 的 release 分支条件。
    if prefix == root:

        # 返回 release_members 的 release 载荷。
        return list(analysis["included_files"])

    # 汇总 members，作为 release 打包和清理候选清单。
    list_members: list[str] = []  # release 打包校验输入值

    # 逐项检查 release_members 发布候选。
    for relative in analysis["included_files"]:

        # 追加 release_members 的 release 诊断。
        list_members.append((root / relative).relative_to(prefix).as_posix())

    # 返回 release_members 的 release 载荷。
    return sorted(list_members)

# 定义 release_project_kind 的release 管理处理入口。
def release_project_kind(project: Path, skill_dir: Path) -> str:

    # 整理 release_project_kind 需要的 profile 发布信息。
    profile = read_json(project / ".agents" / "agents-control.json")  # release 打包校验输入值

    # 校验 release_project_kind 的 release 分支条件。
    if isinstance(profile, dict):

        # 整理 release_project_kind 需要的 kind 发布信息。
        kind = str(profile.get("kind", "")).strip().lower()  # release 打包校验输入值

        # 校验 release_project_kind 的 release 分支条件。
        if kind in {"skill", "engineering"}:

            # 返回 release_project_kind 的 release 载荷。
            return kind

    # 校验 release_project_kind 的 release 分支条件。
    if (skill_dir / "SKILL.md").is_file():

        # 返回 release_project_kind 的 release 载荷。
        return "skill"

    # 返回 release_project_kind 的 release 载荷。
    return "engineering"

# 定义 release_gate 的release 管理处理入口。
