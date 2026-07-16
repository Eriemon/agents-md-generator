"""组装设计画像并把确认后的画像写入项目治理目录。"""

# 画像主体字段根据项目类型选择不同的问答来源。
def _project_identity(answers: dict[str, Any], str_kind: str) -> tuple[str, str, str, str]:
    """提取项目类型对应的用途、原因、受众和备注字段。

    参数：answers 为已校验的设计问答；str_kind 为 skill 或 engineering。
    返回：依次包含用途、原因、受众或环境以及备注字段名。
    """

    # 技能项目使用面向用户的技能描述字段。
    if str_kind == "skill":

        # 技能用途说明画像解决的问题。
        str_purpose = answers["skill_purpose"]  # 技能用途。

        # 技能创建原因记录治理动机。
        str_reason = answers["skill_reason"]  # 技能创建原因。

        # 目标受众限定技能服务范围。
        str_audience = answers["audience"]  # 技能目标受众。

        # 技能访谈把补充内容保存在设计备注中。
        str_notes_key = "design_notes"  # 技能备注字段名。

    # 工程项目改用运行环境和可复用经验字段表达项目身份。
    else:

        # 工程项目使用项目级用途描述。
        str_purpose = answers["project_purpose"]  # 工程项目用途。

        # 工程立项原因进入画像治理依据。
        str_reason = answers["project_reason"]  # 工程项目原因。

        # 运行环境在工程画像中承担受众字段的对应职责。
        str_audience = answers.get("environment", "")  # 工程运行环境。

        # 工程访谈把补充内容归入可复用经验。
        str_notes_key = "reusable_experience"  # 工程经验字段名。

    # 调用方需要这四项共同组装画像主体。
    return str_purpose, str_reason, str_audience, str_notes_key

# 技能和工程项目采用各自的目录合同验证器。
def _validated_layout(
    project: Path,
    str_name: str,
    str_kind: str,
    answers: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[str]]:
    """验证项目类型对应的目录布局。

    参数：project 为项目根；str_name 为项目名；str_kind 为项目类型；answers 为设计问答。
    返回：技能布局或空值，以及阻断画像生成的目录错误。
    """

    # 技能布局同时生成需要写入画像的结构合同。
    if str_kind == "skill":

        # 布局函数返回技能结构和对应诊断。
        dict_layout, list_layout_errors = skill_layout_contract(project, str_name, answers)  # 技能布局与诊断。

        # 任一布局冲突都会阻断画像落盘。
        if list_layout_errors:

            # 保留验证器给出的稳定错误正文。
            return None, list_layout_errors

        # 已验证的技能布局供画像附加使用。
        return dict_layout, []

    # 工程布局只负责验证，不向画像增加技能结构。
    list_engineering_errors = engineering_layout_contract(project, str_name, answers)  # 工程布局诊断。

    # 工程目录不符合确认内容时停止组装。
    if list_engineering_errors:

        # 调用方统一呈现工程目录问题。
        return None, list_engineering_errors

    # 空布局表示工程项目无需 skill_layout 字段。
    return None, []

# 发布合同集中表达版本目录、校验强度和脱敏边界。
def _release_contract(answers: dict[str, Any], str_name: str, str_kind: str) -> dict[str, Any]:
    """构造发布与安装治理合同。

    参数：answers 为设计问答；str_name 为项目名；str_kind 为项目类型。
    返回：可直接写入画像的发布合同映射。
    """

    # 技能发布必须脱敏，工程项目不应用该步骤。
    bool_skill_release = str_kind == "skill"  # 是否执行技能发布脱敏。

    # 字段保持与历史画像模式兼容。
    return {
        "rule": answers["release_contract"],  # 用户确认的发布规则。
        "dist_folder": "dist",  # 版本化发布根目录。
        "release_folder_pattern": f"{str_name}-vx.x.x",  # 项目发布目录命名模式。
        "zip_required": True,  # 发布包必须同时生成压缩件。
        "receipt_file": "RELEASE_RECEIPT.json",  # 发布证据清单文件。
        "install_source_policy": "versioned-dist-release-only",  # 安装仅接受版本发布目录。
        "repo_install_validation_level": "strong",  # 仓库内安装使用完整校验。
        "external_install_validation_level": "reduced_assurance",  # 外部目标采用降级保证。
        "remote_push_allowed": False,  # 默认禁止发布流程推送远端。
        "sanitization_required": bool_skill_release,  # 技能包发布前必须脱敏。
        "sanitization_scope": "broad" if bool_skill_release else "not-applicable",  # 发布脱敏覆盖范围。
        "sanitization_mode": "auto-redact-dist-copy" if bool_skill_release else "disabled",  # 发布副本脱敏模式。
        "sanitization_receipt_required": bool_skill_release,  # 技能脱敏必须留下凭据。
    }

# 画像后处理集中补充分支白名单、技能合同、审查证据和文档合同。
def finalize_profile_contracts(
    dict_profile: dict[str, Any],
    dict_directory_contract: dict[str, Any],
    dict_layout: dict[str, Any] | None,
    answers: dict[str, Any],
    str_kind: str,
    str_name: str,
) -> dict[str, Any]:
    """补充依赖基础画像字段的派生合同。

    参数:
        dict_profile: 已组装的基础画像。
        dict_directory_contract: 已验证目录合同。
        dict_layout: 技能项目的可选布局映射。
        answers: 设计访谈确认答案。
        str_kind: skill 或 engineering 类型。
        str_name: 已规整项目名称。

    返回:
        已补充分支、技能、审查和文档合同的画像。
    """

    # 发布准备允许路径需要项目主目录事实。
    str_primary_root = str(dict_directory_contract.get("primary_project_root", "")).strip()  # 主要项目目录

    # 分支合同为映射且主目录存在时补充发布范围。
    if str_primary_root and isinstance(dict_profile.get("git_branch_policy"), dict):

        # 固定辅助目录与项目主目录共同构成发布准备白名单。
        dict_profile["git_branch_policy"]["release_prepare_allowed_paths"] = [
            str_primary_root,  # 项目主要源码目录
            "tests",  # 自动化测试目录
            "smoke",  # 冒烟验证目录
            "reports",  # 验证报告目录
            "runs",  # 运行证据目录
            "docs",  # 项目文档目录
            ".agents",  # 智能体治理状态目录
            "AGENTS.md",  # 根级智能体规则文件
            "dist",  # 版本发布目录
        ]

    # 技能画像附加专用布局和设计合同。
    if str_kind == "skill":

        # 前置布局验证保证此处结构可直接使用。
        dict_profile["skill_layout"] = dict_layout  # 已确认技能目录布局

        # 技能设计合同记录触发与交付边界。
        dict_profile["skill_design_contract"] = skill_design_contract(answers)  # 技能专用设计合同

    # 已完成的设计评审作为可选证据随画像保存。
    if isinstance(answers.get(DESIGN_REVIEW_KEY), dict):

        # 原始评审结构已经由上游访谈状态机验证。
        dict_profile[DESIGN_REVIEW_KEY] = answers[DESIGN_REVIEW_KEY]  # 设计评审证据

    # 文档合同以项目名称生成固定治理路径。
    dict_docs_contract = docs_contract(str_name)  # 项目文档治理合同

    # 记忆合同同时进入文档合同，供文档工具独立读取。
    if isinstance(dict_docs_contract, dict):

        # 共用同一映射确保顶层和文档层语义一致。
        dict_docs_contract["memory"] = dict_profile["memory_contract"]  # 文档侧记忆合同

    # 文档合同在完成记忆关联后写入画像。
    dict_profile["docs_contract"] = dict_docs_contract  # 完整文档合同

    # 返回已完成派生合同关联的同一画像映射。
    return dict_profile

# 基础画像组装集中映射已验证输入，不承担错误判断或文件写入。
def assemble_base_profile(
    answers: dict[str, Any],
    str_kind: str,
    str_name: str,
    str_default_language: str,
    tuple_identity: tuple[str, str, str, str],
    dict_contracts: dict[str, Any],
) -> dict[str, Any]:
    """把已验证问答和领域合同组装为基础画像。

    参数:
        answers: 已完成必答项校验的设计答案。
        str_kind: skill 或 engineering 类型。
        str_name: 已规整项目名称。
        str_default_language: 已规整默认会话语言。
        tuple_identity: 用途、原因、受众和说明键组成的身份元组。
        dict_contracts: 规则、远程环境、归档和服务器合同。

    返回:
        尚未补充文档和发布白名单的基础画像。
    """

    # 身份元组最后一项指明类型对应的补充说明答案键。
    str_notes_key = tuple_identity[3]  # 补充说明来源键

    # 目录合同嵌入已验证的本地、远端和工作区策略。
    dict_directory_contract: dict[str, Any] = {
        "confirmed": bool(answers["directory_contract_confirmed"]),  # 目录合同确认状态
        "local": answers["local_directory_structure"],  # 本地目录结构描述
        "remote": answers["remote_directory_structure"],  # 远端目录结构描述
        "feature_rules": answers["feature_directory_rules"],  # 功能目录归属规则
        "workspace_settings_policy": workspace_settings_contract(),  # 工作区设置文件边界
        "remote_environment_policy": dict_contracts["remote_environment"],  # 远端环境配置合同
        "remote_runtime_archive_policy": dict_contracts["remote_archive"],  # 远端运行证据归档合同
        **directory_layout_policy(str_kind, str_name),  # 固定项目布局规则
    }

    # 主画像保持现有字段名和嵌套结构，避免破坏消费者。
    return {
        "schema_version": 1,  # 画像模式版本
        "kind": str_kind,  # 项目开发类型
        "name": str_name,  # 项目标识
        "default_conversation_language": str_default_language,  # 默认响应语言
        "purpose": tuple_identity[0],  # 项目用途
        "reason": tuple_identity[1],  # 项目创建原因
        "alignment_confirmed": bool(answers.get(ALIGNMENT_KEY)),  # 需求对齐状态
        "audience_or_environment": tuple_identity[2],  # 受众或工程环境
        "reference_materials_temporary": answers.get("reference_materials", []),  # 临时参考材料
        "notes": answers.get(str_notes_key, ""),  # 类型对应补充说明
        "git_management": answers["git_management"],  # Git 管理策略
        "branch_model": answers["branch_model"],  # 分支协作模型
        "git_branch_policy": git_branch_policy(),  # 分支治理合同
        "release_contract": _release_contract(answers, str_name, str_kind),  # 发布安装合同
        "existing_work": answers["has_existing_work"],  # 既有工作状态
        "global_rule_overrides": global_rule_overrides_contract(),  # 全局规则覆盖合同
        "directory_contract": dict_directory_contract,  # 完整目录合同
        "dir_manager_contract": dir_manager_contract(),  # 目录管理合同
        "engineering_rule_contract": dict_contracts["engineering_rule"],  # 工程规则合同
        "remote_server_contract": dict_contracts["remote_servers"],  # 远程服务器合同
        "use_codebase_memory_mcp": bool(answers[USE_CODEBASE_MEMORY_MCP_KEY]),  # 知识图谱显式选择
        "codebase_memory_mcp_contract": codebase_memory_contract(bool(answers[USE_CODEBASE_MEMORY_MCP_KEY])),  # 知识图谱治理合同
        "memory_enabled": bool(answers.get("memory_enabled")),  # 项目记忆启用状态
        "memory_storage_backend": str(answers.get("memory_storage_backend", "")).strip(),  # 记忆存储后端
        "memory_capture_scope": str(answers.get("memory_capture_scope", "")).strip(),  # 记忆采集范围
        "memory_read_policy": str(answers.get("memory_read_policy", "")).strip(),  # 记忆读取规则
        "memory_sensitivity_policy": str(answers.get("memory_sensitivity_policy", "")).strip(),  # 敏感信息规则
        "memory_contract": memory_contract(answers),  # 完整记忆合同
        "development_requirements": answers["development_requirements"],  # 开发要求
        "extra_requirements": normalize_extra_requirements(answers.get(EXTRA_REQUIREMENTS_KEY, "none")),  # 附加要求
        "expected_outcome": answers["expected_outcome"],  # 预期交付结果
        "validation_method": answers["validation_method"],  # 验证方法
        "validation_granularity": answers["validation_granularity"],  # 验证粒度
        "resource_plan": answers["resource_plan"],  # 资源计划
        "forward_testing_policy": answers["forward_testing_policy"],  # 前向测试规则
    }

# 主入口先验证问答，再组合所有治理合同。
def build_profile(project: Path, answers: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """根据设计问答构建设计画像。

    参数：project 为项目根目录；answers 为设计访谈的确认答案。
    返回：成功时返回画像和空错误列表，失败时返回空画像和诊断列表。
    """

    # 未显式指定类型时根据项目事实推断。
    str_kind = str(answers.get("development_type", infer_kind(project)))  # 当前项目类型。

    # 画像只支持技能和工程两类合同。
    if str_kind not in {"skill", "engineering"}:

        # 稳定错误正文供 CLI 和测试共同消费。
        return None, ["development_type must be skill or engineering"]

    # 必答项随项目类型变化。
    list_missing_answers = missing_answers(answers, str_kind)  # 尚未确认的必答字段。

    # 缺失项一次性返回，避免生成不完整画像。
    if list_missing_answers:

        # 每个字段保留独立诊断，便于访谈状态机追问。
        return None, [f"missing required answer: {str_key}" for str_key in list_missing_answers]

    # 工程规则合同可能同时给出结构和错误。
    dict_rule_contract, list_rule_errors = engineering_rule_contract(answers)  # 工程规则合同与诊断。

    # 无效规则选择不能进入后续画像组装。
    if list_rule_errors:

        # 原样传递规则验证结果。
        return None, list_rule_errors

    # 远端环境和归档策略分别验证，便于合并全部诊断。
    dict_remote_environment, list_environment_errors = remote_environment_policy(answers)  # 远端环境合同与诊断。

    # 运行时归档规则限制远端证据保存位置。
    dict_remote_archive, list_archive_errors = remote_runtime_archive_policy(answers)  # 远端归档合同与诊断。

    # 三类独立策略错误一次返回给访谈调用方。
    list_policy_errors = list_environment_errors + list_archive_errors + memory_policy_errors(answers)  # 策略诊断合集。

    # 策略错误存在时不继续读取远端服务器配置。
    if list_policy_errors:

        # 合并结果保留各验证器的原有顺序。
        return None, list_policy_errors

    # 服务器合同校验项目配置与问答的一致性。
    dict_remote_servers, list_remote_errors = remote_server_contract(project, answers)  # 远端服务器合同与诊断。

    # 服务器配置冲突会导致运行边界不可信。
    if list_remote_errors:

        # 远端诊断由上层访谈流程呈现。
        return None, list_remote_errors

    # 项目身份助手按固定顺序返回四个主体字段。
    tuple_identity = _project_identity(answers, str_kind)  # 项目身份字段元组。

    # 名称去除访谈输入两端空白。
    str_name = str(answers["name"]).strip()  # 规范化项目名称。

    # 目录验证助手同时返回可选布局和诊断。
    tuple_layout_result = _validated_layout(project, str_name, str_kind, answers)  # 目录验证结果元组。

    # 首项仅在技能项目中包含布局映射。
    dict_layout: dict[str, Any] | None = tuple_layout_result[0]  # 已验证技能布局。

    # 第二项收集阻断画像生成的目录问题。
    list_layout_errors: list[str] = tuple_layout_result[1]  # 目录布局诊断。

    # 布局问题保持画像未写入状态。
    if list_layout_errors:

        # 调用方得到完整目录阻断原因。
        return None, list_layout_errors

    # 空语言回答回退到项目约定的中文。
    str_default_language = str(answers.get("default_conversation_language", "中文")).strip() or "中文"  # 默认会话语言。

    # 领域合同以具名映射传入基础画像组装器。
    dict_contracts = {
        "engineering_rule": dict_rule_contract,  # 基础画像使用的规则引用结果
        "remote_environment": dict_remote_environment,  # 目录合同使用的环境策略
        "remote_archive": dict_remote_archive,  # 目录合同使用的归档策略
        "remote_servers": dict_remote_servers,  # 基础画像使用的服务器清单
    }

    # 基础画像只消费已通过前置校验的输入。
    dict_profile = assemble_base_profile(  # 尚未关联文档合同的基础画像
        answers,  # 必答门禁通过后的答案映射
        str_kind,  # 基础画像类型字段来源
        str_name,  # 基础画像名称字段来源
        str_default_language,  # 基础画像会话语言来源
        tuple_identity,  # 用途原因受众和说明键
        dict_contracts,  # 四类领域校验结果
    )

    # 派生合同后处理不改变基础字段或错误语义。
    dict_profile = finalize_profile_contracts(  # 完整设计画像
        dict_profile,  # 基础设计画像
        dict_profile["directory_contract"],  # 已组装目录合同
        dict_layout,  # 可选技能布局
        answers,  # 设计问答来源
        str_kind,  # 技能专用后处理分支依据
        str_name,  # 文档合同命名来源
    )

    # 空诊断表示画像已完成全部前置验证。
    return dict_profile, []

# 写入入口负责持久化画像并同步依赖的治理文件。
def write_profile(project: Path, profile: dict[str, Any]) -> Path:
    """把设计画像写入项目并初始化关联治理文档。

    参数：project 为项目根目录；profile 为已验证的设计画像。
    返回：写入后的 agents-control.json 路径。
    """

    # .agents 是画像和规则覆盖配置的共同治理目录。
    path_agents_dir = project / ".agents"  # 项目智能体治理目录。

    # 已存在目录保持内容不变，新项目只创建缺失目录。
    path_agents_dir.mkdir(exist_ok=True)

    # 画像采用仓库约定的固定文件名。
    path_profile = path_agents_dir / "agents-control.json"  # 设计画像目标路径。

    # 排序和缩进保证版本差异稳定可审查。
    path_profile.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")

    # 全局覆盖文件根据新画像补齐缺失合同。
    ensure_global_rule_overrides_file(project, profile)

    # 文档脚手架与刚写入的画像保持同步。
    scaffold_docs(project)

    # 调用方使用实际路径生成结构化写入结果。
    return path_profile
