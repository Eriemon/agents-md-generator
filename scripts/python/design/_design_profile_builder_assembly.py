def build_profile(project: Path, answers: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:

    # 整理 build_profile 需要的 kind 设计档案信息。
    kind = answers.get("development_type", infer_kind(project))  # 设计档案值

    # 校验 build_profile 的设计档案分支。
    if kind not in {"skill", "engineering"}:

        # 返回 build_profile 的设计档案载荷。
        return None, ["development_type must be skill or engineering"]

    # 收集 missing 设计档案条目。
    list_missing = missing_answers(answers, kind)  # 设计档案值

    # 校验 build_profile 的设计档案分支。
    if list_missing:

        # 返回 build_profile 的设计档案载荷。
        return None, [f"missing required answer: {key}" for key in list_missing]

    # 收集 rule contract、rule errors 设计档案条目。
    tuple_rule_contract, tuple_rule_errors = engineering_rule_contract(answers)  # 设计档案值

    # 校验 build_profile 的设计档案分支。
    if tuple_rule_errors:

        # 返回 build_profile 的设计档案载荷。
        return None, tuple_rule_errors

    # 说明该控制语句在脚本治理流程中的分支职责。
    assert tuple_rule_contract is not None

    # 收集 validation errors 设计档案条目。
    list_validation_errors: list[str] = []  # 设计档案值

    # 收集 remote environment contract、remote environment errors 设计档案条目。
    tuple_remote_environment_contract, tuple_remote_environment_errors = remote_environment_policy(answers)  # 设计档案值

    # 调用 extend 处理 build_profile。
    list_validation_errors.extend(tuple_remote_environment_errors)

    # 收集 remote runtime contract、remote runtime errors 设计档案条目。
    tuple_remote_runtime_contract, tuple_remote_runtime_errors = remote_runtime_archive_policy(answers)  # 设计档案值

    # 调用 extend 处理 build_profile。
    list_validation_errors.extend(tuple_remote_runtime_errors)

    # 调用 extend 处理 build_profile。
    list_validation_errors.extend(memory_policy_errors(answers))

    # 校验 build_profile 的设计档案分支。
    if list_validation_errors:

        # 返回 build_profile 的设计档案载荷。
        return None, list_validation_errors

    # 收集 remote contract、remote errors 设计档案条目。
    tuple_remote_contract, tuple_remote_errors = remote_server_contract(project, answers)  # 设计档案值

    # 校验 build_profile 的设计档案分支。
    if tuple_remote_errors:

        # 返回 build_profile 的设计档案载荷。
        return None, tuple_remote_errors

    # 校验 build_profile 的设计档案分支。
    if kind == "skill":

        # 整理 build_profile 需要的 purpose 设计档案信息。
        purpose = answers["skill_purpose"]  # 设计档案值

        # 整理 build_profile 需要的 reason 设计档案信息。
        reason = answers["skill_reason"]  # 设计档案值

        # 整理 build_profile 需要的 audience 设计档案信息。
        audience = answers["audience"]  # 设计档案值

        # 整理 build_profile 需要的 notes key 设计档案信息。
        str_notes_key = "design_notes"  # 设计档案值
    else:

        # 整理 build_profile 需要的 purpose 设计档案信息。
        purpose = answers["project_purpose"]  # 设计档案值

        # 整理 build_profile 需要的 reason 设计档案信息。
        reason = answers["project_reason"]  # 设计档案值

        # 整理 build_profile 需要的 audience 设计档案信息。
        audience = answers.get("environment", "")  # 设计档案值

        # 整理 build_profile 需要的 notes key 设计档案信息。
        str_notes_key = "reusable_experience"  # 设计档案值

    # 整理 build_profile 需要的 name 设计档案信息。
    name = str(answers["name"]).strip()  # 设计档案值

    # 整理 build_profile 需要的 layout 设计档案信息。
    tuple_layout: dict[str, Any] | None = None  # 设计档案值

    # 校验 build_profile 的设计档案分支。
    if kind == "skill":

        # 收集 layout、layout errors 设计档案条目。
        tuple_layout, tuple_list_tuple_list_layout_errors = skill_layout_contract(project, name, answers)  # 设计档案值

        # 校验 build_profile 的设计档案分支。
        if tuple_list_tuple_list_layout_errors:

            # 返回 build_profile 的设计档案载荷。
            return None, tuple_list_tuple_list_layout_errors
    else:

        # 收集 layout errors 设计档案条目。
        list_tuple_list_tuple_list_layout_errors = engineering_layout_contract(project, name, answers)  # 设计档案布局错误列表

        # 校验 build_profile 的设计档案分支。
        if list_tuple_list_tuple_list_layout_errors:

            # 返回 build_profile 的设计档案载荷。
            return None, list_tuple_list_tuple_list_layout_errors

    # 整理 build_profile 需要的 default language 设计档案信息。
    default_language = str(answers.get("default_conversation_language", "中文")).strip() or "中文"  # 设计档案值

    # 保存 profile 映射，维持 build_profile 的字段关系。
    dict_profile: dict[str, Any] = {  # 设计档案值
        "schema_version": 1,  # 设计档案值
        "kind": kind,  # 设计档案值
        "name": name,  # 设计档案值
        "default_conversation_language": default_language,  # 设计档案值
        "purpose": purpose,  # 设计档案值
        "reason": reason,  # 设计档案值
        "alignment_confirmed": bool(answers.get(ALIGNMENT_KEY)),  # 设计档案值
        "audience_or_environment": audience,  # 设计档案值
        "reference_materials_temporary": answers.get("reference_materials", []),  # 设计档案值
        "notes": answers.get(str_notes_key, ""),  # 设计档案值
        "git_management": answers["git_management"],  # 设计档案值
        "branch_model": answers["branch_model"],  # 设计档案值
        "git_branch_policy": git_branch_policy(),  # 设计档案值
        "release_contract": {  # 设计档案值
            "rule": answers["release_contract"],  # 设计档案值
            "dist_folder": "dist",  # 设计档案值
            "release_folder_pattern": f"{name}-vx.x.x",  # 设计档案值
            "zip_required": True,  # 设计档案值
            "receipt_file": "RELEASE_RECEIPT.json",  # 设计档案值
            "install_source_policy": "versioned-dist-release-only",  # 设计档案值
            "repo_install_validation_level": "strong",  # 设计档案值
            "external_install_validation_level": "reduced_assurance",  # 设计档案值
            "remote_push_allowed": False,  # 设计档案值
            "sanitization_required": kind == "skill",  # 设计档案值
            "sanitization_scope": "broad" if kind == "skill" else "not-applicable",  # 设计档案值
            "sanitization_mode": "auto-redact-dist-copy" if kind == "skill" else "disabled",  # 设计档案值
            "sanitization_receipt_required": kind == "skill",  # 设计档案值
        },  # 设计档案值
        "existing_work": answers["has_existing_work"],  # 设计档案值
        "global_rule_overrides": global_rule_overrides_contract(),  # 设计档案值
        "directory_contract": {  # 设计档案值
            "confirmed": bool(answers["directory_contract_confirmed"]),  # 设计档案值
            "local": answers["local_directory_structure"],  # 设计档案值
            "remote": answers["remote_directory_structure"],  # 设计档案值
            "feature_rules": answers["feature_directory_rules"],  # 设计档案值
            "workspace_settings_policy": workspace_settings_contract(),  # 设计档案值
            "remote_environment_policy": tuple_remote_environment_contract,  # 设计档案值
            "remote_runtime_archive_policy": tuple_remote_runtime_contract,  # 设计档案值
            **directory_layout_policy(kind, name),  # 设计档案值
        },  # 设计档案值
        "dir_manager_contract": dir_manager_contract(),  # 设计档案值
        "engineering_rule_contract": tuple_rule_contract,  # 设计档案值
        "remote_server_contract": tuple_remote_contract,  # 设计档案值
        "memory_enabled": bool(answers.get("memory_enabled")),  # 设计档案值
        "memory_storage_backend": str(answers.get("memory_storage_backend", "")).strip(),  # 设计档案值
        "memory_capture_scope": str(answers.get("memory_capture_scope", "")).strip(),  # 设计档案值
        "memory_read_policy": str(answers.get("memory_read_policy", "")).strip(),  # 设计档案值
        "memory_sensitivity_policy": str(answers.get("memory_sensitivity_policy", "")).strip(),  # 设计档案值
        "memory_contract": memory_contract(answers),  # 设计档案值
        "development_requirements": answers["development_requirements"],  # 设计档案值
        "extra_requirements": normalize_extra_requirements(answers.get(EXTRA_REQUIREMENTS_KEY, "none")),  # 设计档案值
        "expected_outcome": answers["expected_outcome"],  # 设计档案值
        "validation_method": answers["validation_method"],  # 设计档案值
        "validation_granularity": answers["validation_granularity"],  # 设计档案值
        "resource_plan": answers["resource_plan"],  # 设计档案值
        "forward_testing_policy": answers["forward_testing_policy"],  # 设计档案值
    }

    # 整理 build_profile 需要的 primary root 设计档案信息。
    primary_root = str(dict_profile["directory_contract"].get("primary_project_root", "")).strip()  # 设计档案值

    # 校验 build_profile 的设计档案分支。
    if primary_root and isinstance(dict_profile.get("git_branch_policy"), dict):

        # 整理 build_profile 需要的 中间载荷 设计档案信息。
        dict_profile["git_branch_policy"]["release_prepare_allowed_paths"] = [  # 设计档案值
            primary_root,  # 设计档案值
            "tests",  # 设计档案值
            "smoke",  # 设计档案值
            "reports",  # 设计档案值
            "runs",  # 设计档案值
            "docs",  # 设计档案值
            ".agents",  # 设计档案值
            "AGENTS.md",  # 设计档案值
            "dist",  # 设计档案值
        ]

    # 校验 build_profile 的设计档案分支。
    if kind == "skill":

        # 整理 build_profile 需要的 中间载荷 设计档案信息。
        dict_profile["skill_layout"] = tuple_layout  # 设计档案值

        # 整理 build_profile 需要的 中间载荷 设计档案信息。
        dict_profile["skill_design_contract"] = skill_design_contract(answers)  # 设计档案值

    # 校验 build_profile 的设计档案分支。
    if isinstance(answers.get(DESIGN_REVIEW_KEY), dict):

        # 整理 build_profile 需要的 中间载荷 设计档案信息。
        dict_profile[DESIGN_REVIEW_KEY] = answers[DESIGN_REVIEW_KEY]  # 设计档案值

    # 整理 build_profile 需要的 中间载荷 设计档案信息。
    dict_profile["docs_contract"] = docs_contract(name)  # 设计档案值

    # 校验 build_profile 的设计档案分支。
    if isinstance(dict_profile.get("docs_contract"), dict):

        # 整理 build_profile 需要的 中间载荷 设计档案信息。
        dict_profile["docs_contract"]["memory"] = dict_profile["memory_contract"]  # 设计档案值

    # 返回 build_profile 的设计档案载荷。
    return dict_profile, []

# 定义 write_profile  设计档案入口。
def write_profile(project: Path, profile: dict[str, Any]) -> Path:

    # 整理 write_profile 需要的 agents dir 设计档案信息。
    agents_dir = project / ".agents"  # 设计档案值

    # 调用 mkdir 处理 write_profile。
    agents_dir.mkdir(exist_ok=True)

    # 整理 write_profile 需要的 path 设计档案信息。
    path = agents_dir / "agents-control.json"  # 设计档案值

    # 调用 write_text 处理 write_profile。
    path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")

    # 调用 ensure_global_rule_overrides_file 处理 write_profile。
    ensure_global_rule_overrides_file(project, profile)

    # 调用 scaffold_docs 处理 write_profile。
    scaffold_docs(project)

    # 返回 write_profile 的设计档案载荷。
    return path
