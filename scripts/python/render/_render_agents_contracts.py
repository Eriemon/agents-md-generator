def remote_server_contract(profile: dict | None) -> str:

    # 校验 remote_server_contract 的渲染分支条件。
    if not profile:

        # 返回 remote_server_contract 的 AGENTS 渲染载荷。
        return ""

    # 整理 remote_server_contract 需要的 contract 渲染片段。
    contract = profile.get("remote_server_contract", {})  # AGENTS 受管段落渲染输入值

    # 校验 remote_server_contract 的渲染分支条件。
    if not contract:

        # 返回 remote_server_contract 的 AGENTS 渲染载荷。
        return ""

    # 校验 remote_server_contract 的渲染分支条件。
    if not contract.get("enabled"):

        # 返回 remote_server_contract 的 AGENTS 渲染载荷。
        return ""

    # 返回 compact 入口规则，完整 registry 和 route 表只保留在机器可读 profile。
    return "\n".join([
        "- Remote server usage: enabled.",
        "- Route source: `.agents/agents-control.json` field `remote_server_contract`.",
        "- Resolve primary and fallback servers from the route source at execution time. Do not copy server registry, functions, runner, or absolute remote paths into root AGENTS.md.",
        "- If the matched primary remote server fails `check` or `workspace-check`, automatically try registered fallback servers in route order.",
        "- If no registered task route matches the requested task, stop and update the current work folder AGENTS.md/profile before continuing.",
        "- If the user wants a different task-to-server mapping, update the profile through agents-md-generator first; do not bypass the route table ad hoc.",
    ])

# 定义 release_contract 的AGENTS 渲染处理入口。
def release_contract(profile: dict | None, project: Path) -> str:

    # 校验 release_contract 的渲染分支条件。
    if not profile:

        # 返回 release_contract 的 AGENTS 渲染载荷。
        return ""

    # 整理 release_contract 需要的 policy 渲染片段。
    policy = profile.get("git_branch_policy", {})  # AGENTS 受管段落渲染输入值

    # 整理 release_contract 需要的 protected 渲染片段。
    protected = policy.get("protected_branches", ["master", "release"])  # AGENTS 受管段落渲染输入值

    # 整理 release_contract 需要的 protected text 渲染片段。
    protected_text = ", ".join(f"`{item}`" for item in protected)  # AGENTS 受管段落渲染输入值

    # 指向当前仓库存在的脚本指南；外部项目只保留安装版指南描述，避免虚构本地路径。
    str_script_guide = "skills/agents-md-generator/references/script-guide.md" if (project / "skills" / "agents-md-generator" / "references" / "script-guide.md").is_file() else "the installed agents-md-generator script-guide reference"  # AGENTS 受管段落渲染输入值

    # 返回 release_contract 的 AGENTS 渲染载荷。
    return "\n".join([
        f"- Git management: {git_management_text(profile.get('git_management', 'not specified'))}.",
        f"- Branch model: {profile.get('branch_model', 'not specified')}; protected branches: {protected_text}.",
        "- Development branches are allowed only as temporary local work branches.",
        f"- {RELEASE_CORE_WORKTREE_RULE}",
        f"- Release details live in `.agents/agents-control.json`, `docs/git_manager/`, and `{str_script_guide}`; root AGENTS.md keeps only blocking rules.",
        "- Install only from a versioned `dist/<name>-vX.Y.Z/` release directory containing a validated `RELEASE_RECEIPT.json`; source directory installs are forbidden.",
        "- Different-version release directories and matching zip files are immutable history by default.",
        "- Keep the release commit and current `docs/git_manager/CHANGELOG.md` entry together.",
        "- Do not push to a remote unless the user explicitly asks.",
    ])

# 定义 git_management_text 的AGENTS 渲染处理入口。
def git_management_text(value: str) -> str:

    # 保存 mapping 映射，维持 git_management_text 的字段关系。
    dict_mapping = {  # AGENTS 受管段落渲染输入值
        "yes-local-only": "enabled locally; allow local branches and commits, but do not push remotely by default",  # AGENTS 受管段落渲染输入值
        "no-git-management": "disabled for this workflow; do not treat git operations as part of the normal execution path",  # AGENTS 受管段落渲染输入值
        "read-only": "legacy read-only mode; do not execute git writes and limit the workflow to planning/documentation unless the user overrides",  # AGENTS 受管段落渲染输入值
        "remote-allowed": "enabled with remote collaboration allowed when the user explicitly asks",  # AGENTS 受管段落渲染输入值
    }

    # 返回 git_management_text 的 AGENTS 渲染载荷。
    return dict_mapping.get(str(value), str(value))

# 定义 engineering_rule_contract 的AGENTS 渲染处理入口。
def engineering_rule_contract(profile: dict | None) -> str:

    # 校验 engineering_rule_contract 的渲染分支条件。
    if not profile:

        # 返回 engineering_rule_contract 的 AGENTS 渲染载荷。
        return "\n".join([
            "- Primary rule set: none.",
            "- Mode: none.",
            "- Ask the user before adding any book-derived engineering bias to AGENTS.md.",
            "- Do not paste full book rules into AGENTS.md.",
        ])

    # 整理 engineering_rule_contract 需要的 contract 渲染片段。
    contract = profile.get("engineering_rule_contract", {})  # AGENTS 受管段落渲染输入值

    # 整理 engineering_rule_contract 需要的 primary 渲染片段。
    primary = contract.get("primary", "none")  # AGENTS 受管段落渲染输入值

    # 整理 engineering_rule_contract 需要的 mode 渲染片段。
    mode = contract.get("mode", "none")  # AGENTS 受管段落渲染输入值

    # 整理 engineering_rule_contract 需要的 scope 渲染片段。
    scope = contract.get("scope", "on-demand")  # AGENTS 受管段落渲染输入值

    # 汇总 lines，作为 AGENTS 受管段落拼装顺序。
    list_lines = [  # AGENTS 受管段落渲染输入值
        f"- Primary rule set: {primary}.",  # AGENTS 受管段落渲染输入值
        f"- Mode: {mode}.",  # AGENTS 受管段落渲染输入值
        f"- Scope: {scope}.",  # AGENTS 受管段落渲染输入值
        f"- Compatibility: {contract.get('compatibility_policy', 'one primary active rule set')}.",  # AGENTS 受管段落渲染输入值
        f"- Compression: {contract.get('compression_policy', 'keep only decision-changing rules')}.",  # AGENTS 受管段落渲染输入值
        "- Do not paste full book rules into AGENTS.md; keep full material reference-only.",  # AGENTS 受管段落渲染输入值
    ]

    # 汇总 notes，作为 AGENTS 受管段落拼装顺序。
    notes = contract.get("notes")  # AGENTS 受管段落渲染输入值

    # 校验 engineering_rule_contract 的渲染分支条件。
    if notes:

        # 追加 engineering_rule_contract 的 AGENTS 渲染行。
        list_lines.append(f"- Notes: {notes}.")

    # 返回 engineering_rule_contract 的 AGENTS 渲染载荷。
    return "\n".join(list_lines)

# 定义 skill_design_contract 的AGENTS 渲染处理入口。
def skill_design_contract(profile: dict | None, project: Path) -> str:

    # 校验 skill_design_contract 的渲染分支条件。
    if not profile or profile.get("kind") != "skill":

        # 返回 skill_design_contract 的 AGENTS 渲染载荷。
        return ""

    # 整理 skill_design_contract 需要的 contract 渲染片段。
    contract = profile.get("skill_design_contract", {})  # AGENTS 受管段落渲染输入值

    # 汇总 patterns，作为 AGENTS 受管段落拼装顺序。
    patterns = contract.get("patterns", [])  # AGENTS 受管段落渲染输入值

    # 校验 skill_design_contract 的渲染分支条件。
    if isinstance(patterns, str):

        # 整理 skill_design_contract 需要的 patterns text 渲染片段。
        patterns_text = patterns  # AGENTS 受管段落渲染输入值
    else:

        # 整理 skill_design_contract 需要的 patterns text 渲染片段。
        patterns_text = ", ".join(str(item) for item in patterns if str(item).strip())  # AGENTS 受管段落渲染输入值

    # 整理 skill_design_contract 需要的 validation method 渲染片段。
    validation_method = contract.get('validation_method', profile.get('validation_method', 'not specified'))  # AGENTS 受管段落渲染输入值

    # 整理 skill_design_contract 需要的 validation granularity 渲染片段。
    validation_granularity = contract.get('validation_granularity', profile.get('validation_granularity', 'not specified'))  # AGENTS 受管段落渲染输入值

    # 整理 skill_design_contract 需要的 forward policy 渲染片段。
    str_forward_policy = str(contract.get('forward_testing_policy', 'not specified')).strip() or 'not specified'  # AGENTS 受管段落渲染输入值

    # 汇总 lines，作为 AGENTS 受管段落拼装顺序。
    list_lines = [  # AGENTS 受管段落渲染输入值
        f"- Trigger scenarios: {contract.get('trigger_scenarios', 'not specified')}.",  # AGENTS 受管段落渲染输入值
        f"- Design patterns: {patterns_text or 'not specified'}.",  # AGENTS 受管段落渲染输入值
        f"- Resource boundaries: {contract.get('resource_plan', 'not specified')}.",  # AGENTS 受管段落渲染输入值
        f"- Progressive disclosure: {contract.get('progressive_disclosure_policy', 'not specified')}.",  # AGENTS 受管段落渲染输入值
        f"- Validation gates: {contract.get('validation_gates', 'not specified')}.",  # AGENTS 受管段落渲染输入值
        f"- Forward testing: {str_forward_policy}.",  # AGENTS 受管段落渲染输入值
        f"- Validation method: {validation_method}; granularity: {validation_granularity}.",  # AGENTS 受管段落渲染输入值
        f"- Reference material policy: {contract.get('reference_material_policy', 'temporary inputs only')}.",  # AGENTS 受管段落渲染输入值
    ]

    # 返回 skill_design_contract 的 AGENTS 渲染载荷。
    return "\n".join(list_lines)

# 定义 conversation_completion_contract 的AGENTS 渲染处理入口。
def conversation_completion_contract(profile: dict | None) -> str:

    # 整理 conversation_completion_contract 需要的 default language 渲染片段。
    default_language = profile.get('default_conversation_language', '中文') if profile else '中文'  # AGENTS 受管段落渲染输入值

    # 返回 conversation_completion_contract 的 AGENTS 渲染载荷。
    return "\n".join([
        "- Finish all requested development work in the current conversation whenever feasible.",
        (
            f"- All natural-language responses must use the configured default language "  # AGENTS 长文本片段
            f"(`{default_language}`) unless the user explicitly switches languages. In "  # AGENTS 长文本片段
            f"Plan Mode, any content inside `<proposed_plan>` must use the configured "  # AGENTS 长文本片段
            f"default language (`{default_language}`) unless the user explicitly switches "  # AGENTS 长文本片段
            f"languages. Keep the `<proposed_plan>` tags unchanged; code, commands, logs, "  # AGENTS 长文本片段
            f"raw error text, and proper nouns may remain in their original form."  # AGENTS 长文本片段
        ),
        "- If work cannot be completed, report blockers, completed files, unverified assumptions, and exact next steps.",
        "- Run the smallest relevant checks during development and final verification before completion claims.",
        "- Preserve user changes and never rewrite the directory contract silently.",
    ])

# 定义 memory_contract 的AGENTS 渲染处理入口。
def memory_contract(profile: dict | None, project: Path) -> str:

    # 校验 memory_contract 的渲染分支条件。
    if not profile:

        # 返回 memory_contract 的 AGENTS 渲染载荷。
        return ""

    # 整理 memory_contract 需要的 contract 渲染片段。
    contract = profile.get("memory_contract", {}) if isinstance(profile.get("memory_contract", {}), dict) else {}  # AGENTS 受管段落渲染输入值

    # 标记 enabled 判断，控制 memory_contract 的分支走向。
    bool_enabled = bool(contract.get("enabled", profile.get("memory_enabled", False)))  # AGENTS 受管段落渲染输入值

    # 校验 memory_contract 的渲染分支条件。
    if not bool_enabled:

        # 返回 memory_contract 的 AGENTS 渲染载荷。
        return ""

    # 整理 memory_contract 需要的 guide 渲染片段。
    guide = contract.get("guide", "docs/memory/MEMORY.md")  # AGENTS 受管段落渲染输入值

    # 整理 memory_contract 需要的 backend 渲染片段。
    backend = contract.get("storage_backend", "sqlite-plus-jsonl")  # AGENTS 受管段落渲染输入值

    # 整理 memory_contract 需要的 read policy 渲染片段。
    str_read_policy = contract.get("read_policy", "read latest handoff plus relevant docs/memory summaries before implementation")  # AGENTS 受管段落渲染输入值

    # 校验 memory_contract 的渲染分支条件。
    if str_read_policy == "read latest handoff plus relevant docs/memory summaries before implementation":

        # 整理 memory_contract 需要的 read policy 渲染片段。
        str_read_policy = "latest handoff + relevant memory summaries before work"  # AGENTS 受管段落渲染输入值

    # 整理 memory_contract 需要的 sensitivity 渲染片段。
    str_sensitivity = contract.get("sensitivity_policy", "do not store secrets, credentials, or raw local private paths")  # AGENTS 受管段落渲染输入值

    # 校验 memory_contract 的渲染分支条件。
    if str_sensitivity == "do not store secrets, credentials, or raw local private paths":

        # 整理 memory_contract 需要的 sensitivity 渲染片段。
        str_sensitivity = "do not store secrets, credentials, or raw local private paths"  # AGENTS 受管段落渲染输入值

    # 整理 memory_contract 需要的 read command 渲染片段。
    str_read_command = project_command(project, profile, "manage_docs.py", "memory-read", "<project>", "--query", "\"<task>\"", "--limit", "5")  # AGENTS 受管段落渲染输入值

    # 整理 memory_contract 需要的 gate command 渲染片段。
    str_gate_command = project_command(project, profile, "manage_docs.py", "memory-gate", "<project>")  # AGENTS 受管段落渲染输入值

    # 整理 memory_contract 需要的 init command 渲染片段。
    str_init_command = project_command(project, profile, "manage_docs.py", "memory-init", "<project>", "--confirm-create")  # AGENTS 受管段落渲染输入值

    # 整理 memory_contract 需要的 bootstrap command 渲染片段。
    str_bootstrap_command = project_command(project, profile, "manage_docs.py", "memory-bootstrap-sessions", "<project>")  # AGENTS 受管段落渲染输入值

    # 返回 memory_contract 的 AGENTS 渲染载荷。
    return "\n".join([
        f"- Root: `{contract.get('folder', 'docs/memory')}`; guide: `{guide}`; backend: `{backend}`.",
        f"- Read {str_read_policy}.",
        f"- Gate with `{str_gate_command}`; if missing, ask before `{str_init_command}`.",
        f"- Historical work runs `{str_bootstrap_command}` for exact-cwd sessions in timestamp order.",
        f"- Query with `{str_read_command}`; write/compress through memory CLI; handoff appends.",
        f"- Sensitivity: {str_sensitivity}.",
    ])

# 定义 documentation_governance_contract 的AGENTS 渲染处理入口。
def documentation_governance_contract(profile: dict | None, project: Path) -> str:

    # 校验 documentation_governance_contract 的渲染分支条件。
    if not profile:

        # 返回 documentation_governance_contract 的 AGENTS 渲染载荷。
        return ""

    # 整理 documentation_governance_contract 需要的 contract 渲染片段。
    contract = profile.get("docs_contract", {})  # AGENTS 受管段落渲染输入值

    # 整理 documentation_governance_contract 需要的 handoff 渲染片段。
    handoff = contract.get("handoff", {})  # AGENTS 受管段落渲染输入值

    # 整理 documentation_governance_contract 需要的 dir manager 渲染片段。
    dir_manager = contract.get("dir_manager", {})  # AGENTS 受管段落渲染输入值

    # 汇总 lines，作为 AGENTS 受管段落拼装顺序。
    list_lines = [  # AGENTS 受管段落渲染输入值
        f"- Docs root: `{contract.get('root', 'docs')}`; latest handoff is `{handoff.get('current', 'docs/handoff/HANDOFF.md')}`.",  # AGENTS 受管段落渲染输入值
        (
            f"- Before new work, read "  # AGENTS 长文本片段
            f"`{handoff.get('current', 'docs/handoff/HANDOFF.md')}`, run "  # AGENTS 长文本片段
            f"`{project_command(project, profile, 'manage_docs.py', 'resume-check', '<project>')}`, "  # AGENTS 长文本片段
            f"and use "  # AGENTS 长文本片段
            f"`{project_command(project, profile, 'manage_docs.py', 'resume-repair', '<project>', '--input', 'recovery.json')}` "  # AGENTS 长文本片段
            f"if interrupted."  # AGENTS 长文本片段
        ),
        f"- Start work with `{project_command(project, profile, 'manage_docs.py', 'start-session', '<project>', '--input', 'session.json')}`.",  # AGENTS 受管段落渲染输入值
        (
            f"- Every completed development conversation must write "  # AGENTS 长文本片段
            f"`{handoff.get('current', 'docs/handoff/HANDOFF.md')}`; use "  # AGENTS 长文本片段
            f"`{project_command(project, profile, 'manage_docs.py', 'handoff', '<project>', '--input', 'handoff.json')}` "  # AGENTS 长文本片段
            f"at task completion."  # AGENTS 长文本片段
        ),
        (
            "- Memory, development, install configuration, git-manager, handoff history, "  # AGENTS 长文本片段
            "and archive naming details live under `docs/`; root AGENTS.md keeps only "  # AGENTS 长文本片段
            "entry rules."  # AGENTS 长文本片段
        ),
        (
            f"- Directory changes require "  # AGENTS 长文本片段
            f"`{project_command(project, profile, 'manage_dirs.py', 'review', '<project>', '--input', 'change.json')}`; "  # AGENTS 长文本片段
            f"blocked reviews require explicit user force-confirmation and risk capture in "  # AGENTS 长文本片段
            f"handoff."  # AGENTS 长文本片段
        ),
        (
            f"- Dir manager details live in `{dir_manager.get('folder', 'docs/dir_manager')}/`; "  # AGENTS 长文本片段
            f"review outcomes decide whether folder mutation may proceed."  # AGENTS 长文本片段
        ),
    ]

    # 返回 documentation_governance_contract 的 AGENTS 渲染载荷。
    return "\n".join(list_lines)

# 定义 task_specific_gates 的AGENTS 渲染处理入口。
def task_specific_gates(profile: dict | None, project: Path) -> str:
    """生成会改变执行行为的仓库级阻断入口。"""

    # 未确认强控制时只保留不能被误解为已完成治理的入口提示。
    if not profile:

        # 返回未配置 profile 时仍有决策意义的入口规则。
        return "- AGENTS generation: collect a confirmed design profile before claiming strict controlled output."

    # 汇总 gate rules，作为根文件中的阻断规则集合。
    list_rules: list[Rule] = []

    # 读取目录契约字段，根文件只保留执行入口和边界。
    dict_directory = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract", {}), dict) else {}
    dict_dir_manager = profile.get("dir_manager_contract", {}) if isinstance(profile.get("dir_manager_contract", {}), dict) else {}
    dict_settings = dict_directory.get("workspace_settings_policy", {}) if isinstance(dict_directory.get("workspace_settings_policy", {}), dict) else {}
    str_primary_root = str(dict_directory.get("primary_project_root", "")).strip()
    str_settings_folder = dict_settings.get("folder", ".settings")
    str_local_settings = str(dict_settings.get("local_default_file", f"{str_settings_folder}/project.local.json")).strip()
    str_remote_settings = str(dict_settings.get("remote_default_file", f"{str_settings_folder}/project.remote.json")).strip()

    # 项目主根影响新功能放置，属于高优先级入口规则。
    if str_primary_root:
        list_rules.append(Rule(
            "directory.primary-root",
            "Task-specific gates",
            f"- **Project root:** keep feature work inside `{str_primary_root}` unless the directory contract is updated.",
            10,
        ))

    # 本地私有配置外传是安全边界，始终保留。
    list_rules.append(Rule(
        "settings.local-private",
        "Task-specific gates",
        f"- **Workspace settings:** keep local config in `{str_local_settings}`, remote config in `{str_remote_settings}`, and never copy `{str_settings_folder}/*.local.json` such as `{str_settings_folder}/server_list.local.json` to remote servers.",
        10,
    ))

    # 目录变更必须走目录治理 review。
    list_rules.append(Rule(
        "directory.review",
        "Task-specific gates",
        f"- **Directory changes:** review create/move/delete/rename plans with `{dict_dir_manager.get('folder', 'docs/dir_manager')}/DIR_MANAGER.md` and run `{project_command(project, profile, 'manage_dirs.py', 'review', '<project>', '--input', 'change.json')}` before mutating governed folders.",
        10,
    ))
    list_rules.append(Rule(
        "directory.blocked-review",
        "Task-specific gates",
        "- **Blocked directory review:** stop by default; proceed only after explicit user force-confirmation and record the risk in handoff.",
        10,
    ))

    # skill 开发内容默认不能被部署到远端。
    if str(profile.get("kind", "")).strip().lower() == "skill":
        list_rules.append(Rule(
            "remote.no-skill-dev-sync",
            "Task-specific gates",
            "- **Remote deployment:** do not sync local skill-development content to servers; deploy only explicit runtime/deployment artifacts unless the user overrides.",
            10,
        ))

    dict_remote_environment = dict_directory.get("remote_environment_policy", {}) if isinstance(dict_directory.get("remote_environment_policy", {}), dict) else {}
    dict_remote_runtime = dict_directory.get("remote_runtime_archive_policy", {}) if isinstance(dict_directory.get("remote_runtime_archive_policy", {}), dict) else {}
    if dict_remote_environment.get("status") == "enabled" or dict_remote_runtime.get("status") == "enabled":
        list_rules.append(Rule(
            "remote.planned-structure",
            "Task-specific gates",
            "- **Remote structure:** keep deployment, conda/runtime, backup, and archive path details in `docs/dir_manager/planned_structure.json`; root AGENTS.md is only the entry rule index.",
            15,
        ))

    # 远程任务启用时只保留 profile 指针和执行期解析规则。
    str_remote_contract = remote_server_contract(profile)
    if str_remote_contract:
        list_rules.append(Rule(
            "remote.routes",
            "Task-specific gates",
            str_remote_contract,
            10,
        ))

    # 发布规则只保留阻断级操作边界。
    str_release_contract = release_contract(profile, project)
    if str_release_contract:
        for index, str_line in enumerate(str_release_contract.splitlines()):
            if any(fragment in str_line for fragment in ["Install only", "Do not push", RELEASE_CORE_WORKTREE_RULE, "Release details live", "Different-version release"]):
                list_rules.append(Rule(f"release.{index}", "Task-specific gates", str_line, 20))

    # 工程规则只有在启用时才进入根文件，且只保留模式和引用边界。
    str_engineering_contract = engineering_rule_contract(profile)
    if str_engineering_contract:
        for index, str_line in enumerate(str_engineering_contract.splitlines()):
            if any(fragment in str_line for fragment in ["Primary rule set:", "Mode:", "Do not paste full book rules"]):
                list_rules.append(Rule(f"engineering.{index}", "Task-specific gates", str_line, 25))

    # 文档恢复和交接会影响任务入口和收尾。
    str_docs_contract = documentation_governance_contract(profile, project)
    if str_docs_contract:
        for index, str_line in enumerate(str_docs_contract.splitlines()):
            if any(fragment in str_line for fragment in ["Before new work", "Start work", "Every completed", "Directory changes"]):
                list_rules.append(Rule(f"docs.{index}", "Task-specific gates", str_line, 20))

    # 记忆启用时保留读取入口，避免重复敏感信息句。
    str_memory_contract = memory_contract(profile, project)
    if str_memory_contract:
        for index, str_line in enumerate(str_memory_contract.splitlines()):
            if any(fragment in str_line for fragment in ["Root:", "Read ", "Gate with", "Historical", "Query with"]):
                list_rules.append(Rule(f"memory.{index}", "Task-specific gates", str_line, 30))

    # skill 项目的验证和前测策略会改变完成条件，保留为 compact 指针。
    str_skill_contract = skill_design_contract(profile, project)
    if str_skill_contract:
        for index, str_line in enumerate(str_skill_contract.splitlines()):
            if any(fragment in str_line for fragment in ["Validation gates:", "Forward testing:"]):
                list_rules.append(Rule(f"skill.{index}", "Task-specific gates", str_line, 25))

    # 返回按 ID 去重后的规则正文。
    return render_rule_list(list_rules)


def read_before_changing(context: dict) -> str:
    """生成当前仓库可读入口，不输出空表格或占位行。"""

    # 汇总 read rules，作为可检查上下文入口。
    list_rules: list[Rule] = []

    # 架构和政策文档优先级最高。
    for index, str_line in enumerate(key_decisions(context).splitlines()):
        list_rules.append(Rule(f"read.decisions.{index}", "Read before changing", str_line, 20))

    # 自动化脚本、质量配置和平台文件帮助代理复用现有入口。
    for index, str_line in enumerate(codebase_state(context).splitlines()):
        list_rules.append(Rule(f"read.state.{index}", "Read before changing", str_line, 40))

    # hook 和 GitHub 设置只有被发现时才输出。
    for index, str_line in enumerate(hook_policy(context).splitlines()):
        list_rules.append(Rule(f"read.hooks.{index}", "Read before changing", str_line, 30))

    for index, str_line in enumerate(github_settings(context).splitlines()):
        list_rules.append(Rule(f"read.github.{index}", "Read before changing", str_line, 30))

    for index, str_line in enumerate(directory_coverage(context).splitlines()):
        list_rules.append(Rule(f"read.directory.{index}", "Read before changing", str_line, 50))

    # 真实 utilities 和 golden samples 以普通 bullet 形式写入，避免裸表格行。
    for index, str_path in enumerate(context.get("utilities", [])[:6]):
        list_rules.append(Rule(
            f"read.utility.{index}",
            "Read before changing",
            f"- Inspect existing automation `{str_path}` before adding new project tooling.",
            40,
        ))

    for index, str_path in enumerate(context.get("golden_samples", [])[:4]):
        list_rules.append(Rule(
            f"read.sample.{index}",
            "Read before changing",
            f"- Use `{str_path}` as the nearest implementation/test pattern before inventing a new one.",
            40,
        ))

    return render_rule_list(list_rules)


def render_rule_list(rules: list[Rule]) -> str:
    """按 ID 去重并按优先级输出规则。"""

    # 已输出 ID 集合阻止同一规则重复进入根文件。
    set_seen: set[str] = set()

    # 保留去重后的文本行。
    list_lines: list[str] = []

    # 优先级低的数值先输出，文本作为稳定排序兜底。
    for rule in sorted(rules, key=lambda item: (item.priority, item.id)):
        if not rule.condition or rule.id in set_seen or not rule.text.strip():
            continue

        set_seen.add(rule.id)
        list_lines.extend(line for line in rule.text.splitlines() if line.strip())

    return "\n".join(list_lines)


def coding_behavior_baseline(project: Path, profile: dict | None, facts: dict | None = None) -> str:

    # 定位 config path 的文件边界，供 coding_behavior_baseline 后续读写校验使用。
    str_config_path = local_rule_config_path(project, profile)  # AGENTS 受管段落渲染输入值

    # 整理 coding_behavior_baseline 需要的 policy 渲染片段。
    policy = load_global_rule_overrides(project, profile)["data"].get("coding_behavior", {})  # AGENTS 受管段落渲染输入值

    # 整理 coding_behavior_baseline 需要的 comment quality 渲染片段。
    comment_quality = str(policy.get("comment_quality", "")).strip()  # AGENTS 受管段落渲染输入值

    # 整理 coding_behavior_baseline 需要的 formatting 渲染片段。
    formatting = str(policy.get("formatting", "")).strip()  # AGENTS 受管段落渲染输入值

    # 整理 coding_behavior_baseline 需要的 routing 渲染片段。
    routing = policy.get("language_skill_routing", {}) if isinstance(policy.get("language_skill_routing", {}), dict) else {}  # AGENTS 受管段落渲染输入值

    # 整理 coding_behavior_baseline 需要的 python route 渲染片段。
    python_route = str(routing.get("python", "")).strip()  # AGENTS 受管段落渲染输入值

    # 整理 coding_behavior_baseline 需要的 script route 渲染片段。
    script_route = str(routing.get("script", "")).strip()  # AGENTS 受管段落渲染输入值

    # 汇总 lines，作为 AGENTS 编码行为输出。
    list_lines = [
        f"- 编码行为配置来源：`{str_config_path}`；用户可手动修改该 JSON 后重新渲染。",
        f"- 注释质量：{comment_quality}",
        f"- {formatting}",
    ]

    if python_route:
        list_lines.append(f"- 语言技能路由（Python）：{python_route}")

    if script_route:
        list_lines.append(f"- 语言技能路由（脚本）：{script_route}")

    # 返回 coding_behavior_baseline 的 AGENTS 渲染载荷。
    return "\n".join(list_lines)

# 定义 script_output_policy 的AGENTS 渲染处理入口。
def script_output_policy(project: Path, profile: dict | None) -> str:

    # 定位 config path 的文件边界，供 script_output_policy 后续读写校验使用。
    str_config_path = local_rule_config_path(project, profile)  # AGENTS 受管段落渲染输入值

    # 整理 script_output_policy 需要的 policy 渲染片段。
    policy = load_global_rule_overrides(project, profile)["data"].get("script_output_policy", {})  # AGENTS 受管段落渲染输入值

    # 汇总 formats，作为 AGENTS 受管段落拼装顺序。
    formats = policy.get("format", {}) if isinstance(policy.get("format", {}), dict) else {}  # AGENTS 受管段落渲染输入值

    # 整理 script_output_policy 需要的 python policy 渲染片段。
    python_policy = policy.get("python", {}) if isinstance(policy.get("python", {}), dict) else {}  # AGENTS 受管段落渲染输入值

    # 过程性日志前缀来自治理 JSON，渲染时只做默认值兜底。
    info_prefix = formats.get("info", "> INFO: [{kind}]")  # INFO 日志前缀模板

    # WARNING 前缀单独命名，保持最终 AGENTS 行宽可控。
    warning_prefix = formats.get("warning", "> WARNING: [{kind}]")  # WARNING 日志前缀模板

    # ERR 前缀单独命名，避免业务枚举硬编码在长 f-string 内。
    error_prefix = formats.get("error", "> ERR: [{kind}]")  # ERR 日志前缀模板

    # quiet 开关来自 Python 输出策略，缺省沿用脚本约定。
    quiet_flag = python_policy.get("quiet_flag", "--quiet")  # Python 静默开关文本

    # 返回 script_output_policy 的 AGENTS 渲染载荷。
    return "\n".join([
        f"- 配置来源：`{str_config_path}`；`Kind` 列表只从该 JSON 读取，代码不得内置业务枚举。",
        (
            f"- "  # AGENTS 长文本片段
            f"格式：`{info_prefix}`、`{warning_prefix}`、`{error_prefix}`；Python "  # AGENTS 长文本片段
            f"过程性 INFO 默认打印，`{quiet_flag}` 关闭 "  # AGENTS 长文本片段
            f"INFO/progress，WARNING 和 ERR 继续可见；机器可读输出不套前缀。"  # AGENTS 长文本片段
        ),
    ])

# 定义 template_values 的AGENTS 渲染处理入口。
def template_values(project: Path, profile: dict | None = None, template_dir: Path | None = None) -> dict[str, str]:

    # 汇总 facts，作为 AGENTS 受管段落拼装顺序。
    facts = inspect_project(project)  # AGENTS 受管段落渲染输入值

    # 汇总 commands，作为 AGENTS 受管段落拼装顺序。
    commands = extract_commands(project)["commands"]  # AGENTS 受管段落渲染输入值

    # 汇总 scopes，作为 AGENTS 受管段落拼装顺序。
    scopes = detect_scopes(project)["scopes"]  # AGENTS 受管段落渲染输入值

    # 整理 template_values 需要的 context 渲染片段。
    context = extract_context(project)  # AGENTS 受管段落渲染输入值

    # 整理 template_values 需要的 command source 渲染片段。
    command_source = ", ".join(sorted({item["source"] for item in commands})) if commands else ""  # AGENTS 受管段落渲染输入值

    # 整理 template_values 需要的 default language 渲染片段。
    default_language = profile.get("default_conversation_language", "中文") if profile else "中文"  # AGENTS 受管段落渲染输入值

    # 整理 template_values 需要的 project version 渲染片段。
    project_version = resolved_project_version(project, profile) or "unknown"  # AGENTS 受管段落渲染输入值

    # 整理 template_values 需要的 generator version 渲染片段。
    str_generator_version = resolved_generator_version(project, profile, project_version)  # AGENTS 受管段落渲染输入值

    # 返回 template_values 的 AGENTS 渲染载荷。
    return {
        "TIMESTAMP": current_timestamp(),
        "VERIFIED_TIMESTAMP": "never",
        "AGENTS_VERSION": str_generator_version,
        "GENERATOR_VERSION": str_generator_version,
        "DEFAULT_LANGUAGE": default_language,
        "PROJECT_OVERVIEW": project_overview(facts, str_generator_version),
        "CONTROL_PROFILE": control_profile(profile, project, project_version),
        "DIRECTORY_CONTRACT": directory_contract(profile, project),
        "REMOTE_SERVER_CONTRACT": remote_server_contract(profile),
        "RELEASE_CONTRACT": release_contract(profile, project),
        "ENGINEERING_RULE_CONTRACT": engineering_rule_contract(profile),
        "SKILL_DESIGN_CONTRACT": skill_design_contract(profile, project),
        "CONVERSATION_COMPLETION_CONTRACT": conversation_completion_contract(profile),
        "TASK_SPECIFIC_GATES": task_specific_gates(profile, project),
        "CODING_BEHAVIOR_BASELINE": coding_behavior_baseline(project, profile, facts),
        "SCRIPT_OUTPUT_POLICY": script_output_policy(project, profile),
        "MEMORY_CONTRACT": memory_contract(profile, project),
        "DOCUMENTATION_GOVERNANCE_CONTRACT": documentation_governance_contract(profile, project),
        "VERIFICATION_STATUS": "unverified",
        "COMMAND_SOURCE": command_source,
        "COMMAND_ROWS": command_rows(commands),
        "FILE_MAP": file_map(facts).rstrip(),
        "GOLDEN_SAMPLE_ROWS": golden_sample_rows_from_context(context),
        "UTILITY_ROWS": utility_rows(context),
        "HEURISTIC_ROWS": heuristic_rows(),
        "REPOSITORY_SETTINGS": "\n".join(
            line
            for line in [
                f"- CI: {', '.join(facts['ci'])}" if facts["ci"] else "",
                f"- Package manager: {facts['package_manager']}" if facts["package_manager"] != "unknown" else "",
            ]
            if line
        ),
        "READ_BEFORE_CHANGING": read_before_changing(context),
        "HOOK_POLICY": hook_policy(context),
        "CI_RULES": ci_rules(context),
        "GITHUB_SETTINGS": github_settings(context),
        "DIRECTORY_COVERAGE": directory_coverage(context),
        "KEY_DECISIONS": key_decisions(context),
        "ALWAYS_RULES": bullet_lines([
            "Preserve user changes and hand-written guidance.",
            "Add tests or verification for changed behavior.",
            "Show verification output before claiming completion.",
        ]),
        "ASK_FIRST_RULES": bullet_lines([
            "Adding dependencies.",
            "Changing CI/CD, public APIs, schemas, migrations, or security-sensitive code.",
            "Running destructive or expensive commands.",
        ]),
        "NEVER_RULES": bullet_lines([
            "Sync local skill-development content to remote servers during deployment unless the user explicitly overrides.",
            "Commit secrets, credentials, or sensitive data.",
            "Modify generated/vendor files unless explicitly requested.",
            "Fabricate commands, files, owners, branches, or policies.",
        ]),
        "CODEBASE_STATE": codebase_state(context),
        "TERMINOLOGY_ROWS": "",
        "SCOPE_INDEX": scope_index(scopes).rstrip(),
    }

# 定义 manual_content 的AGENTS 渲染处理入口。
def manual_content(existing: str) -> str:

    # 校验 manual_content 的渲染分支条件。
    if not existing.strip():

        # 返回 manual_content 的 AGENTS 渲染载荷。
        return ""

    # 整理 manual_content 需要的 generated boilerplate 渲染片段。
    set_generated_boilerplate = {  # AGENTS 受管段落渲染输入值
        "# AGENTS.md",  # 根 AGENTS 标题模板
        "**Precedence:** the closest `AGENTS.md` to the files being changed wins. Explicit user prompts override this file.",  # AGENTS 受管段落渲染输入值
        "### Always Do",  # Always Do 边界标题
        "### Ask First",  # Ask First 边界标题
        "### Never Do",  # Never Do 边界标题
        "Use this order: explicit user prompt, closest AGENTS.md, parent AGENTS.md, general repository docs.",  # AGENTS 受管段落渲染输入值
    }

    # 汇总 generated plain blocks，作为 AGENTS 受管段落拼装顺序。
    set_generated_plain_blocks = {  # AGENTS 受管段落渲染输入值
        "## Agent Work Loop",  # 根 AGENTS 固定工作循环段
        "## Boundaries",  # 根 AGENTS 边界段
        "## When Instructions Conflict",  # 根 AGENTS 冲突处理段
    }

    # 汇总 generated prefixes，作为 AGENTS 受管段落拼装顺序。
    tuple_generated_prefixes = ("<!-- Last updated:", "<!-- AGENTS-METADATA:")  # AGENTS 受管段落渲染输入值

    # 汇总 kept，作为 AGENTS 受管段落拼装顺序。
    list_kept = []  # AGENTS 受管段落渲染输入值

    # 标记 skipping marker 判断，控制 manual_content 的分支走向。
    bool_skipping_marker = False  # AGENTS 受管段落渲染输入值

    # 标记 skipping plain block 判断，控制 manual_content 的分支走向。
    bool_skipping_plain_block = False  # AGENTS 受管段落渲染输入值

    # 逐项检查 manual_content 渲染候选。
    for line in existing.splitlines():

        # 整理 manual_content 需要的 stripped 渲染片段。
        stripped = line.strip()  # AGENTS 受管段落渲染输入值

        # 校验 manual_content 的渲染分支条件。
        if line.startswith(GENERATED_START):

            # 标记 skipping marker 判断，控制 manual_content 的分支走向。
            bool_skipping_marker = True  # AGENTS 受管段落渲染输入值

            # 标记 skipping plain block 判断，控制 manual_content 的分支走向。
            bool_skipping_plain_block = False  # AGENTS 受管段落渲染输入值

            # 分隔 manual_content 的控制流边界。
            continue

        # 校验 manual_content 的渲染分支条件。
        if line.startswith(GENERATED_END):

            # 标记 skipping marker 判断，控制 manual_content 的分支走向。
            bool_skipping_marker = False  # AGENTS 受管段落渲染输入值

            # 分隔 manual_content 的控制流边界。
            continue

        # 校验 manual_content 的渲染分支条件。
        if bool_skipping_marker:

            # 分隔 manual_content 的控制流边界。
            continue

        # 校验 manual_content 的渲染分支条件。
        if line.startswith("<!-- FOR AI") or line.startswith("<!-- Managed by agent:") or line.startswith(tuple_generated_prefixes):

            # 分隔 manual_content 的控制流边界。
            continue

        # 校验 manual_content 的渲染分支条件。
        if stripped == "## Human Notes":

            # 标记 skipping plain block 判断，控制 manual_content 的分支走向。
            bool_skipping_plain_block = False  # AGENTS 受管段落渲染输入值

            # 分隔 manual_content 的控制流边界。
            continue

        # 校验 manual_content 的渲染分支条件。
        if stripped in set_generated_plain_blocks:

            # 标记 skipping plain block 判断，控制 manual_content 的分支走向。
            bool_skipping_plain_block = True  # AGENTS 受管段落渲染输入值

            # 分隔 manual_content 的控制流边界。
            continue

        # 校验 manual_content 的渲染分支条件。
        if bool_skipping_plain_block and stripped.startswith("## "):

            # 标记 skipping plain block 判断，控制 manual_content 的分支走向。
            bool_skipping_plain_block = False  # AGENTS 受管段落渲染输入值

        # 校验 manual_content 的渲染分支条件。
        if bool_skipping_plain_block:

            # 分隔 manual_content 的控制流边界。
            continue

        # 校验 manual_content 的渲染分支条件。
        if stripped not in set_generated_boilerplate:

            # 追加 manual_content 的 AGENTS 渲染行。
            list_kept.append(line)

    # 整理 manual_content 需要的 text 渲染片段。
    text = "\n".join(list_kept).strip()  # AGENTS 受管段落渲染输入值

    # 校验 manual_content 的渲染分支条件。
    if not text:

        # 返回 manual_content 的 AGENTS 渲染载荷。
        return ""

    # 返回 manual_content 的 AGENTS 渲染载荷。
    return f"\n## Human Notes\n\n{text}\n"

# 定义 render_root 的AGENTS 渲染处理入口。
