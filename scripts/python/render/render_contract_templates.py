"""实现模板占位值构建与手工内容提取。"""

# 渲染聚合器先加载合同分片，再把本文件函数写入同一公开命名空间。
def template_values(project: Path, profile: dict | None = None, template_dir: Path | None = None) -> dict[str, str]:
    """构建 AGENTS.md 模板渲染所需的全部命名值。

    参数:
        project: 当前项目根目录。
        profile: 可选项目设计配置；缺失时从项目加载。
        template_dir: 可选模板目录，保留给兼容调用方。

    返回:
        模板占位符名称到已渲染文本的映射。
    """

    # 项目事实驱动概览、文件映射和仓库设置渲染。
    facts = inspect_project(project)  # 当前项目探测事实

    # 命令事实用于命令表和来源摘要。
    commands = extract_commands(project)["commands"]  # 已发现项目命令

    # 作用域事实用于生成局部 AGENTS 索引。
    scopes = detect_scopes(project)["scopes"]  # 已发现规则作用域

    # 上下文事实为阅读清单和仓库治理段落提供输入。
    context = extract_context(project)  # 文档、工具和治理上下文

    # 命令来源按字典序去重，确保模板输出稳定。
    command_source = (
        ", ".join(sorted({item["source"] for item in commands}))  # 非空命令来源集合
        if commands  # 仅在发现命令时生成来源摘要
        else ""  # 未发现命令时不输出来源
    )  # 命令发现来源摘要

    # profile 缺失时沿用项目的中文会话缺省值。
    default_language = (
        profile.get("default_conversation_language", "中文")  # profile 语言配置
        if profile  # 仅在配置存在时读取语言字段
        else "中文"  # 未提供 profile 时使用中文
    )  # 模板默认会话语言

    # 未能解析项目版本时显式标记 unknown。
    project_version = resolved_project_version(project, profile) or "unknown"  # 项目版本

    # 生成器版本同时写入 AGENTS 与 generator 元数据字段。
    str_generator_version = resolved_generator_version(  # 解析后的生成器版本
        project, profile, project_version  # 生成器版本解析上下文
    )  # 当前生成器版本

    # 所有模板占位符在单一映射中构造，避免调用方二次推断。
    return {
        "TIMESTAMP": current_timestamp(),  # 本次渲染时间
        "VERIFIED_TIMESTAMP": "never",  # 尚未执行验证的缺省标记
        "AGENTS_VERSION": str_generator_version,  # AGENTS 元数据版本
        "GENERATOR_VERSION": str_generator_version,  # 生成器实现版本
        "DEFAULT_LANGUAGE": default_language,  # 自然语言默认值
        "PROJECT_OVERVIEW": project_overview(facts, str_generator_version),  # 项目概览
        "CONTROL_PROFILE": control_profile(profile, project, project_version),  # 强控制配置
        "DIRECTORY_CONTRACT": directory_contract(profile, project),  # 目录治理合同
        "REMOTE_SERVER_CONTRACT": remote_server_contract(profile),  # 远程路由合同
        "RELEASE_CONTRACT": release_contract(profile, project),  # 发布与 Git 合同
        "ENGINEERING_RULE_CONTRACT": engineering_rule_contract(profile),  # 工程规则合同
        "SKILL_DESIGN_CONTRACT": skill_design_contract(profile, project),  # Skill 设计合同
        "CONVERSATION_COMPLETION_CONTRACT": conversation_completion_contract(profile),  # 会话完成合同
        "TASK_SPECIFIC_GATES": task_specific_gates(profile, project),  # 高影响任务门禁
        "CODING_BEHAVIOR_BASELINE": coding_behavior_baseline(project, profile, facts),  # 编码行为规则
        "SCRIPT_OUTPUT_POLICY": script_output_policy(project, profile),  # 脚本输出规则
        "MEMORY_CONTRACT": memory_contract(profile, project),  # 持久记忆合同
        "DOCUMENTATION_GOVERNANCE_CONTRACT": documentation_governance_contract(profile, project),  # 文档生命周期合同
        "VERIFICATION_STATUS": "unverified",  # 新渲染结果验证状态
        "COMMAND_SOURCE": command_source,  # 命令探测来源
        "COMMAND_ROWS": command_rows(commands),  # 命令表格行
        "FILE_MAP": file_map(facts).rstrip(),  # 项目文件映射
        "GOLDEN_SAMPLE_ROWS": golden_sample_rows_from_context(context),  # 黄金样例行
        "UTILITY_ROWS": utility_rows(context),  # 工具入口行
        "HEURISTIC_ROWS": heuristic_rows(),  # 启发式说明行
        "REPOSITORY_SETTINGS": "\n".join(
            line
            for line in [
                f"- CI: {', '.join(facts['ci'])}" if facts["ci"] else "",
                f"- Package manager: {facts['package_manager']}" if facts["package_manager"] != "unknown" else "",
            ]
            if line
        ),
        "READ_BEFORE_CHANGING": read_before_changing(context),  # 修改前阅读入口
        "HOOK_POLICY": hook_policy(context),  # Git 钩子策略
        "CI_RULES": ci_rules(context),  # 持续集成规则
        "GITHUB_SETTINGS": github_settings(context),  # GitHub 仓库设置
        "DIRECTORY_COVERAGE": directory_coverage(context),  # 局部规则覆盖提示
        "KEY_DECISIONS": key_decisions(context),  # 架构与政策决策
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
            "Sync local skill-development content to remote servers during deployment "
            "unless the user explicitly overrides.",
            "Commit secrets, credentials, or sensitive data.",
            "Modify generated/vendor files unless explicitly requested.",
            "Fabricate commands, files, owners, branches, or policies.",
        ]),
        "CODEBASE_STATE": codebase_state(context),  # 当前代码库治理状态
        "TERMINOLOGY_ROWS": "",  # 兼容旧模板的空术语表
        "SCOPE_INDEX": scope_index(scopes).rstrip(),  # 局部规则作用域索引
    }

# 手工内容提取器保护生成块之外的用户维护文本。
def manual_content(existing: str) -> str:
    """从既有 AGENTS.md 中提取不受生成器管理的手工内容。

    参数:
        existing: 当前 AGENTS.md 的完整文本。

    返回:
        移除受管生成块并清理旧兼容段后的手工文本。
    """

    # 空文件没有可保留的手工内容。
    if not existing.strip():

        # 返回空文本，避免生成空 Human Notes 标题。
        return ""

    # 固定模板标题和边界句不属于用户手工内容。
    set_generated_boilerplate = {
        "# AGENTS.md",  # 根 AGENTS 标题模板
        "**Precedence:** the closest `AGENTS.md` to the files being changed wins. "
        "Explicit user prompts override this file.",
        "### Always Do",  # Always Do 边界标题
        "### Ask First",  # 旧版操作确认标题
        "### Never Do",  # 旧版禁止操作标题
        "Use this order: explicit user prompt, closest AGENTS.md, parent AGENTS.md, general repository docs.",  # 旧版冲突优先级句
    }

    # 这些旧版普通段落整体由当前生成器替代。
    set_generated_plain_blocks = {
        "## Agent Work Loop",  # 根 AGENTS 固定工作循环段
        "## Boundaries",  # 根 AGENTS 边界段
        "## When Instructions Conflict",  # 根 AGENTS 冲突处理段
    }

    # 元数据注释通过前缀识别，兼容动态时间和版本内容。
    tuple_generated_prefixes = (
        "<!-- Last updated:", "<!-- AGENTS-METADATA:"  # 动态时间与版本元数据
    )  # 动态生成元数据前缀

    # 保留行按原文件顺序累积。
    list_kept: list[str] = []  # 用户维护的手工内容行

    # 标记块状态用于跳过当前生成器管理的显式区域。
    bool_skipping_marker = False  # 是否位于生成标记块内

    # 普通块状态兼容迁移前没有显式标记的旧段落。
    bool_skipping_plain_block = False  # 是否位于旧版固定段落内

    # 逐项检查 manual_content 渲染候选。
    for line in existing.splitlines():

        # 去除外围空白后匹配标题和模板固定句。
        stripped = line.strip()  # 当前行的规范匹配文本

        # 进入显式生成块后跳过直至结束标记。
        if line.startswith(GENERATED_START):

            # 开始标记后的文本属于生成器管理范围。
            bool_skipping_marker = True  # 开始跳过受管生成块

            # 显式标记出现后清除旧版普通块状态。
            bool_skipping_plain_block = False  # 显式标记优先于旧版块状态

            # 分隔 manual_content 的控制流边界。
            continue

        # 结束标记恢复对后续手工文本的采集。
        if line.startswith(GENERATED_END):

            # 结束标记恢复后续手工内容采集。
            bool_skipping_marker = False  # 离开受管生成块

            # 结束标记自身不属于手工内容。
            continue

        # 受管标记块内部的所有行都直接跳过。
        if bool_skipping_marker:

            # 继续扫描以寻找对应结束标记。
            continue

        # 生成器身份和动态元数据注释不能进入 Human Notes。
        if (
            line.startswith("<!-- FOR AI")
            or line.startswith("<!-- Managed by agent:")
            or line.startswith(tuple_generated_prefixes)
        ):

            # 元数据由下一次渲染重新生成。
            continue

        # Human Notes 标题是容器，不是用户正文。
        if stripped == "## Human Notes":

            # Human Notes 标题明确恢复手工正文采集。
            bool_skipping_plain_block = False  # 从旧版块跳过状态恢复

            # 避免重复输出 Human Notes 标题。
            continue

        # 遇到旧版固定段落标题时开始整体跳过。
        if stripped in set_generated_plain_blocks:

            # 固定标题后的内容由当前模板重新生成。
            bool_skipping_plain_block = True  # 进入旧版固定段落

            # 固定标题由当前模板重新生成。
            continue

        # 新的二级标题代表旧版固定段落结束。
        if bool_skipping_plain_block and stripped.startswith("## "):

            # 新二级标题结束旧版固定段落范围。
            bool_skipping_plain_block = False  # 恢复普通手工内容采集

        # 仍处于旧版固定段落时跳过当前行。
        if bool_skipping_plain_block:

            # 继续寻找下一个二级标题边界。
            continue

        # 只有非模板固定句才被保留为用户内容。
        if stripped not in set_generated_boilerplate:

            # 原始行保留缩进和内部空白。
            list_kept.append(line)

    # 合并后只清理整体首尾空白，不改变正文布局。
    text = "\n".join(list_kept).strip()  # 最终手工正文

    # 全部内容均属于模板时不生成 Human Notes。
    if not text:

        # 空字符串让上层跳过手工段落。
        return ""

    # 非空手工内容统一放回 Human Notes 容器。
    return f"\n## Human Notes\n\n{text}\n"

