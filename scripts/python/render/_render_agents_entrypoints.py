def render_root(project: Path, template_dir: Path | None = None, profile: dict | None = None) -> str:

    # 整理 render_root 需要的 existing 渲染片段。
    existing = (project / "AGENTS.md").read_text(encoding="utf-8", errors="ignore") if (project / "AGENTS.md").exists() else ""  # AGENTS 受管段落渲染输入值

    # 校验 render_root 的渲染分支条件。
    if template_dir is None:

        # 汇总 values，作为 AGENTS 受管段落拼装顺序。
        dict_values = template_values(project, profile, template_dir)  # AGENTS 受管段落渲染输入值

        # 整理 render_root 需要的 manual 渲染片段。
        manual = manual_content(existing).strip()  # AGENTS 受管段落渲染输入值

        # 整理 render_root 需要的 engineering max 渲染片段。
        engineering_max = 6 if profile and profile.get("engineering_rule_contract", {}).get("primary") != "none" else 2  # AGENTS 受管段落渲染输入值

        # 整理 render_root 需要的 context body 渲染片段。
        context_body = "\n".join([dict_values["KEY_DECISIONS"], dict_values["UTILITY_ROWS"], dict_values["CODEBASE_STATE"]])  # AGENTS 受管段落渲染输入值

        # 汇总 scopes，作为 AGENTS 受管段落拼装顺序。
        scopes = detect_scopes(project)["scopes"]  # AGENTS 受管段落渲染输入值

        # 整理 render_root 需要的 agent work loop 渲染片段。
        agent_work_loop = "\n".join([  # AGENTS 受管段落渲染输入值
            "## Agent Work Loop",  # 根 AGENTS 工作循环标题
            "1. Read the nearest `AGENTS.md` before editing files.",  # AGENTS 受管段落渲染输入值
            "2. Inspect existing patterns and generated facts before adding code.",  # AGENTS 受管段落渲染输入值
            "3. Run the smallest relevant check after each change.",  # AGENTS 受管段落渲染输入值
            "4. Run final verification and show command output before claiming completion.",  # AGENTS 受管段落渲染输入值
            (
                "5. Complete the assigned development task in the current conversation "  # AGENTS 长文本片段
                "whenever feasible; if blocked, report blockers, completed work, and exact "  # AGENTS 长文本片段
                "next steps."  # AGENTS 长文本片段
            ),
        ])  # AGENTS 受管段落渲染输入值

        # 定义 compose 的AGENTS 渲染处理入口。
        def compose(control_max: int, skill_max: int, include_auxiliary: bool = True) -> str:

            # 汇总 parts，作为 AGENTS 受管段落拼装顺序。
            list_parts = [  # AGENTS 受管段落渲染输入值
                "<!-- FOR AI AGENTS - Human readability is a side effect, not a goal -->",  # AGENTS 受管段落渲染输入值
                "<!-- Managed by agent: keep sections and order; edit content outside AGENTS-GENERATED blocks -->",  # AGENTS 受管段落渲染输入值
                f"<!-- Last updated: {dict_values['TIMESTAMP']} | Last verified: {dict_values['VERIFIED_TIMESTAMP']} -->",  # AGENTS 受管段落渲染输入值
                (
                    f"<!-- AGENTS-METADATA: agents_version={dict_values['AGENTS_VERSION']}; "  # AGENTS 长文本片段
                    f"generator_version={dict_values['GENERATOR_VERSION']}; "  # AGENTS 长文本片段
                    f"default_language={dict_values['DEFAULT_LANGUAGE']} -->"  # AGENTS 长文本片段
                ),
                "# AGENTS.md",  # 根 AGENTS 标题行
                "**Precedence:** the closest `AGENTS.md` to the files being changed wins. Explicit user prompts override this file.",  # AGENTS 受管段落渲染输入值
                compact_section("project-overview", "Project Overview", dict_values["PROJECT_OVERVIEW"], 3),  # AGENTS 受管段落渲染输入值
                compact_section("control-profile", "Control Profile", dict_values["CONTROL_PROFILE"], control_max),  # AGENTS 受管段落渲染输入值
                compact_section("directory-contract", "Directory Contract", dict_values["DIRECTORY_CONTRACT"], 18),  # AGENTS 受管段落渲染输入值
                compact_section("remote-server-contract", "Remote Server Contract", dict_values["REMOTE_SERVER_CONTRACT"], 18),  # AGENTS 受管段落渲染输入值
                compact_section("release-contract", "Release Contract", dict_values["RELEASE_CONTRACT"], 11),  # AGENTS 受管段落渲染输入值
                compact_section("engineering-rule-contract", "Engineering Rule Contract", dict_values["ENGINEERING_RULE_CONTRACT"], engineering_max),  # AGENTS 受管段落渲染输入值
                compact_section("skill-design-contract", "Skill Design Contract", dict_values["SKILL_DESIGN_CONTRACT"], skill_max),  # AGENTS 受管段落渲染输入值
                "\n".join([  # AGENTS 受管段落渲染输入值
                    f"{GENERATED_START} commands -->",  # AGENTS 受管段落渲染输入值
                    f"## Commands ({dict_values['VERIFICATION_STATUS']})",  # 命令表标题行
                    f"> Source: {dict_values['COMMAND_SOURCE']} - verify before relying on these commands.",  # AGENTS 受管段落渲染输入值
                    "| Task | Command | ~Time | Source |",  # AGENTS 受管段落渲染输入值
                    "|------|---------|-------|--------|",  # AGENTS 受管段落渲染输入值
                    limit_command_rows(dict_values["COMMAND_ROWS"]),  # AGENTS 受管段落渲染输入值
                    "<!-- AGENTS-GENERATED:END commands -->",  # AGENTS 受管段落渲染输入值
                ]),  # AGENTS 受管段落渲染输入值
                compact_section("coding-behavior-baseline", "Coding Behavior Baseline", dict_values["CODING_BEHAVIOR_BASELINE"], 7),  # AGENTS 受管段落渲染输入值
                compact_section("script-output-policy", "Script Output Policy", dict_values["SCRIPT_OUTPUT_POLICY"], 6),  # AGENTS 受管段落渲染输入值
                compact_section("conversation-completion-contract", "Conversation Completion Contract", dict_values["CONVERSATION_COMPLETION_CONTRACT"], 3),  # AGENTS 受管段落渲染输入值
                compact_section("memory-contract", "Memory Contract", dict_values["MEMORY_CONTRACT"], 6),  # AGENTS 受管段落渲染输入值
                compact_section("documentation-governance-contract", "Documentation Governance Contract", dict_values["DOCUMENTATION_GOVERNANCE_CONTRACT"], 9),  # AGENTS 受管段落渲染输入值
                compact_section("directory-coverage", "Directory Coverage", dict_values["DIRECTORY_COVERAGE"], 2),  # AGENTS 受管段落渲染输入值
            ]

            # 校验 compose 的渲染分支条件。
            if include_auxiliary:

                # 追加 compose 的 AGENTS 渲染行。
                list_parts.append(agent_work_loop)

            # 仓库上下文存在非占位信息时才渲染该辅助段落。
            bool_has_repository_context = (  # repository context 是否包含有效内容
                "Link ADRs or architecture docs here" not in dict_values["KEY_DECISIONS"]  # 多行表达式输入文本
                or "Add migrations, tech debt" not in dict_values["CODEBASE_STATE"]  # 代码库状态已替换占位内容
                or "Existing utility" in dict_values["UTILITY_ROWS"]  # 工具表仍含默认工具占位
            )

            # 校验 compose 的渲染分支条件。
            if bool_has_repository_context:

                # 追加 compose 的 AGENTS 渲染行。
                list_parts.append(compact_section("repository-context", "Repository Context", context_body, 10))

            # 校验 compose 的渲染分支条件。
            if "No hook framework detected" not in dict_values["HOOK_POLICY"]:

                # 追加 compose 的 AGENTS 渲染行。
                list_parts.append(compact_section("hook-policy", "Hook Policy", dict_values["HOOK_POLICY"], 3))

            # 校验 compose 的渲染分支条件。
            if "No GitHub settings or rulesets detected" not in dict_values["GITHUB_SETTINGS"]:

                # 追加 compose 的 AGENTS 渲染行。
                list_parts.append(compact_section("github-settings", "GitHub Settings", dict_values["GITHUB_SETTINGS"], 3))

            # 校验 compose 的渲染分支条件。
            if include_auxiliary and scopes:

                # 追加 compose 的 AGENTS 渲染行。
                list_parts.append(compact_section("scope-index", "Scoped AGENTS.md", dict_values["SCOPE_INDEX"], 4))

            # 调用 extend 处理 compose。
            list_parts.extend([
                "\n".join([
                    "## Boundaries",
                    "### Always Do",
                    limit_lines(dict_values["ALWAYS_RULES"], 2),
                    "### Ask First",
                    limit_lines(dict_values["ASK_FIRST_RULES"], 2),
                    "### Never Do",
                    limit_lines(dict_values["NEVER_RULES"], 2),
                ]),
                "## When Instructions Conflict",
                "Use this order: explicit user prompt, closest AGENTS.md, parent AGENTS.md, general repository docs.",
            ])

            # 校验 compose 的渲染分支条件。
            if manual:

                # 追加 compose 的 AGENTS 渲染行。
                list_parts.append(manual)

            # 返回 compose 的 AGENTS 渲染载荷。
            return "\n".join(list_parts).rstrip() + "\n"

        # 整理 render_root 需要的 rendered 渲染片段。
        str_rendered = compose(control_max=10, skill_max=8)  # AGENTS 受管段落渲染输入值

        # 校验 render_root 的渲染分支条件。
        if len(str_rendered.encode("utf-8")) > ROOT_AGENTS_MAX_BYTES:

            # 整理 render_root 需要的 rendered 渲染片段。
            str_rendered = compose(control_max=9, skill_max=8)  # AGENTS 受管段落渲染输入值

        # 校验 render_root 的渲染分支条件。
        if len(str_rendered.encode("utf-8")) > ROOT_AGENTS_MAX_BYTES:

            # 整理 render_root 需要的 rendered 渲染片段。
            str_rendered = compose(control_max=8, skill_max=8)  # AGENTS 受管段落渲染输入值

        # 校验 render_root 的渲染分支条件。
        if len(str_rendered.encode("utf-8")) > ROOT_AGENTS_MAX_BYTES:

            # 整理 render_root 需要的 rendered 渲染片段。
            str_rendered = compose(control_max=7, skill_max=8)  # AGENTS 受管段落渲染输入值

        # 校验 render_root 的渲染分支条件。
        if len(str_rendered.encode("utf-8")) > ROOT_AGENTS_MAX_BYTES:

            # 整理 render_root 需要的 rendered 渲染片段。
            str_rendered = compose(control_max=7, skill_max=7)  # AGENTS 受管段落渲染输入值

        # 校验 render_root 的渲染分支条件。
        if len(str_rendered.encode("utf-8")) > ROOT_AGENTS_MAX_BYTES:

            # 整理 render_root 需要的 rendered 渲染片段。
            str_rendered = compose(control_max=7, skill_max=7, include_auxiliary=False)  # AGENTS 受管段落渲染输入值

        # 返回 render_root 的 AGENTS 渲染载荷。
        return str_rendered

    # 整理 render_root 需要的 template 渲染片段。
    str_template = load_template(template_dir or default_template_dir(), "root-agents.md")  # AGENTS 受管段落渲染输入值

    # 汇总 values，作为 AGENTS 受管段落拼装顺序。
    dict_values = template_values(project, profile, template_dir)  # AGENTS 受管段落渲染输入值

    # 整理 render_root 需要的 rendered 渲染片段。
    str_rendered = replace_placeholders(str_template, dict_values).rstrip()  # AGENTS 受管段落渲染输入值

    # 整理 render_root 需要的 metadata 渲染片段。
    metadata = (
        f"<!-- AGENTS-METADATA: agents_version={dict_values['AGENTS_VERSION']}; "  # AGENTS 长文本片段
        f"generator_version={dict_values['GENERATOR_VERSION']}; "  # AGENTS 长文本片段
        f"default_language={dict_values['DEFAULT_LANGUAGE']} -->"  # AGENTS 长文本片段
    )

    # 返回 render_root 的 AGENTS 渲染载荷。
    return metadata + "\n" + str_rendered + manual_content(existing) + "\n"

# 定义 generated_root_body 的 AGENTS 渲染处理入口。
def generated_root_body(project: Path, dict_values: dict[str, str], manual: str = "") -> str:
    """生成默认和模板路径共享的根 AGENTS.md 正文。"""

    list_parts = [
        "<!-- FOR AI AGENTS - Human readability is a side effect, not a goal -->",
        "<!-- Managed by agent: keep sections and order; edit content outside AGENTS-GENERATED blocks -->",
        f"<!-- Last updated: {dict_values['TIMESTAMP']} | Last verified: {dict_values['VERIFIED_TIMESTAMP']} -->",
        (
            f"<!-- AGENTS-METADATA: agents_version={dict_values['AGENTS_VERSION']}; "
            f"generator_version={dict_values['GENERATOR_VERSION']}; "
            f"default_language={dict_values['DEFAULT_LANGUAGE']} -->"
        ),
        "# AGENTS.md",
        "**Precedence:** the closest `AGENTS.md` to the files being changed wins. Explicit user prompts override this file.",
        compact_section("project", "Project", project_section(dict_values)),
        commands_section(dict_values),
        compact_section("task-specific-gates", "Task-specific gates", dict_values["TASK_SPECIFIC_GATES"]),
        compact_section("local-conventions", "Local conventions", local_conventions_section(dict_values)),
        compact_section("read-before-changing", "Read before changing", dict_values["READ_BEFORE_CHANGING"]),
        compact_section("scoped-instructions", "Scoped instructions", scoped_instructions(project)),
        "## When Instructions Conflict\nUse this order: explicit user prompt, closest AGENTS.md, parent AGENTS.md, general repository docs.",
    ]

    if manual:
        list_parts.append(manual)

    return "\n".join(part for part in list_parts if str(part).strip()).rstrip() + "\n"


# 定义 project_section 的 AGENTS 渲染处理入口。
def project_section(dict_values: dict[str, str]) -> str:
    """保留项目身份和会影响执行的控制摘要。"""

    list_lines: list[str] = []

    for line in dict_values["PROJECT_OVERVIEW"].splitlines():
        stripped = line.strip()
        if stripped and "Root AGENTS.md:" not in stripped:
            list_lines.append(stripped)

    for line in dict_values["CONTROL_PROFILE"].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "- Strong control: not configured.":
            continue
        if stripped.startswith(("- Strong control:", "- Development type:", "- Name:", "- Version:", "- Default conversation language:", "- Purpose/reason:", "- Additional user requirements:")):
            list_lines.append(stripped)

    return render_unique_lines(list_lines)


# 定义 commands_section 的 AGENTS 渲染处理入口。
def commands_section(dict_values: dict[str, str]) -> str:
    """只在发现真实命令时渲染 Commands 段。"""

    str_rows = limit_command_rows(dict_values["COMMAND_ROWS"]).strip()
    if not str_rows:
        return ""

    return "\n".join([
        f"{GENERATED_START} commands -->",
        "## Commands",
        "| Task | Command | ~Time | Source |",
        "|------|---------|-------|--------|",
        str_rows,
        "<!-- AGENTS-GENERATED:END commands -->",
    ])


# 定义 local_conventions_section 的 AGENTS 渲染处理入口。
def local_conventions_section(dict_values: dict[str, str]) -> str:
    """合并本仓库会改变日常执行行为的本地约定。"""

    list_blocks = [
        dict_values["CONVERSATION_COMPLETION_CONTRACT"],
        dict_values["CODING_BEHAVIOR_BASELINE"],
        dict_values["SCRIPT_OUTPUT_POLICY"],
    ]

    return "\n".join(block.strip() for block in list_blocks if block.strip())


# 定义 scoped_instructions 的 AGENTS 渲染处理入口。
def scoped_instructions(project: Path) -> str:
    """只索引已有且包含真实本地覆盖内容的 scoped AGENTS.md。"""

    list_lines: list[str] = []

    for agents_path in sorted(project.rglob("AGENTS.md")):
        if agents_path == project / "AGENTS.md":
            continue
        if any(part in SKIP_DIRS for part in agents_path.relative_to(project).parts):
            continue
        if not scoped_agents_has_local_overrides(agents_path):
            continue
        rel_path = agents_path.relative_to(project).as_posix()
        list_lines.append(f"- `./{rel_path}` - local override rules for this subtree.")

    return "\n".join(list_lines)


# 定义 scoped_agents_has_local_overrides 的 AGENTS 渲染处理入口。
def scoped_agents_has_local_overrides(agents_path: Path) -> bool:
    """判断 scoped AGENTS.md 是否包含生成套话之外的本地差异。"""

    try:
        text = agents_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False

    return bool(manual_content(text).strip())


# 定义 render_unique_lines 的 AGENTS 渲染处理入口。
def render_unique_lines(lines: list[str]) -> str:
    """按出现顺序去重并忽略空行。"""

    set_seen: set[str] = set()
    list_rendered: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped in set_seen:
            continue
        set_seen.add(stripped)
        list_rendered.append(stripped)

    return "\n".join(list_rendered)


# 定义 scope_requires_local_agents 的 AGENTS 渲染处理入口。
def scope_requires_local_agents(scope_dir: Path) -> bool:
    """只有存在真实局部配置时才自动创建 scoped AGENTS.md。"""

    tuple_local_markers = (
        "AGENTS.local.md",
        "package.json",
        "pyproject.toml",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "Makefile",
        ".pre-commit-config.yaml",
    )

    return any((scope_dir / marker).exists() for marker in tuple_local_markers)


# 定义 render_root 的 AGENTS 渲染处理入口。
from agents_common import SKIP_DIRS

def render_root(project: Path, template_dir: Path | None = None, profile: dict | None = None) -> str:
    """渲染共享规则集合的根 AGENTS.md。"""

    path_agents = project / "AGENTS.md"
    existing = path_agents.read_text(encoding="utf-8", errors="ignore") if path_agents.exists() else ""
    dict_values = template_values(project, profile, template_dir)
    manual = manual_content(existing).strip()
    generated_body = generated_root_body(project, dict_values, manual)

    if template_dir is None:
        return generated_body

    str_template = load_template(template_dir or default_template_dir(), "root-agents.md")
    if "{{GENERATED_BODY}}" not in str_template:
        str_template = str_template.rstrip() + "\n{{GENERATED_BODY}}\n"

    dict_template_values = dict(dict_values)
    dict_template_values["GENERATED_BODY"] = generated_body.rstrip()

    return replace_placeholders(str_template, dict_template_values).rstrip() + "\n"


# 定义 render_scoped 的AGENTS 渲染处理入口。
def render_scoped(scope: dict[str, str], template_dir: Path | None = None) -> str:

    # 整理 render_scoped 需要的 path 渲染片段。
    path = scope["path"]  # AGENTS 受管段落渲染输入值

    # 整理 render_scoped 需要的 template 渲染片段。
    str_template = load_template(template_dir or default_template_dir(), "scoped-agents.md")  # AGENTS 受管段落渲染输入值

    # 汇总 values，作为 AGENTS 受管段落拼装顺序。
    dict_values = {  # AGENTS 受管段落渲染输入值
        "TIMESTAMP": current_timestamp(),  # AGENTS 受管段落渲染输入值
        "VERIFIED_TIMESTAMP": "never",  # AGENTS 受管段落渲染输入值
        "SCOPE_NAME": path,  # AGENTS 受管段落渲染输入值
        "SCOPE_PATH": path,  # AGENTS 受管段落渲染输入值
        "SCOPE_OVERVIEW": f"{scope['purpose']}.",  # AGENTS 受管段落渲染输入值
        "LOCAL_COMMANDS": "Use root AGENTS.md commands unless this directory has its own package/config file.",  # AGENTS 受管段落渲染输入值
        "TESTING_RULES": "Run the narrowest relevant tests for files changed in this scope.",  # AGENTS 受管段落渲染输入值
        "LOCAL_STRUCTURE": "Document local key files here after inspecting this directory.",  # AGENTS 受管段落渲染输入值
        "CODE_STYLE": "Follow nearby files in this scope before introducing new patterns.",  # AGENTS 受管段落渲染输入值
        "GIT_WORKFLOW": "Follow root git workflow unless this scope documents a stricter local rule.",  # AGENTS 受管段落渲染输入值
        "LOCAL_BOUNDARIES": "- Ask before changing local public APIs, generated files, or ownership boundaries.",  # AGENTS 受管段落渲染输入值
        "SCOPE_PURPOSE": scope["purpose"],  # AGENTS 受管段落渲染输入值
    }

    # 返回 render_scoped 的 AGENTS 渲染载荷。
    return replace_placeholders(str_template, dict_values).rstrip() + "\n"

# 定义 main 的AGENTS 渲染处理入口。
def main() -> None:

    # 整理 main 需要的 parser 渲染片段。
    parser = argparse.ArgumentParser(description="Render AGENTS.md from discovered project facts.")  # AGENTS 受管段落渲染输入值

    # 调用 add_argument 处理 main。
    parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 处理 main。
    parser.add_argument("--write", action="store_true", help="Write AGENTS.md files. Default prints root draft only.")

    # 调用 add_argument 处理 main。
    parser.add_argument("--template-dir", default=None, help="Directory containing root-agents.md and scoped-agents.md.")

    # 调用 add_argument 处理 main。
    parser.add_argument("--profile", default=None, help="Path to .agents/agents-control.json for strong-control rendering.")

    # 调用 add_argument 处理 main。
    parser.add_argument("--confirm-docs-layout", action="store_true", help="User confirmed that docs governance may be added under the existing docs/ layout.")

    # 调用 add_argument 处理 main。
    parser.add_argument(
        "--confirm-structure-fix",
        action="store_true",
        help="User explicitly confirmed applying recommended structure normalization before writing.",
    )

    # 调用 add_argument 处理 main。
    parser.add_argument(
        "--confirm-branch-governance",
        action="store_true",
        help="User explicitly confirmed continuing after a blocked branch governance check.",
    )

    # 汇总 args，作为 AGENTS 受管段落拼装顺序。
    args = parser.parse_args()  # AGENTS 受管段落渲染输入值

    # 整理 main 需要的 project 渲染片段。
    project = resolve_project(args.project)  # AGENTS 受管段落渲染输入值

    # 整理 main 需要的 template dir 渲染片段。
    template_dir = Path(args.template_dir).resolve() if args.template_dir else None  # AGENTS 受管段落渲染输入值

    # 整理 main 需要的 profile 渲染片段。
    profile = load_profile(project, args.profile)  # AGENTS 受管段落渲染输入值

    # 整理 main 需要的 root text 渲染片段。
    str_root_text = render_root(project, template_dir, profile)  # AGENTS 受管段落渲染输入值

    # 校验 main 的渲染分支条件。
    if not args.write:

        # 调用 print 处理 main。
        print(str_root_text)

        # 返回 main 的 AGENTS 渲染载荷。
        return

    # 校验 main 的渲染分支条件。
    if profile:

        # 整理 main 需要的 structure result 渲染片段。
        structure_result = structure_gate(project)  # AGENTS 受管段落渲染输入值

        # 校验 main 的渲染分支条件。
        if not structure_result.get("approved", True) and not args.confirm_structure_fix:

            # 调用 emit_json 处理 main。
            emit_json({
                "errors": ["structure governance requires user confirmation before writing AGENTS.md or docs governance"],
                "structure_gate": structure_result,
                "requires_user_confirmation": True,
            })

            # 抛出 main 已确认的阻断原因。
            raise SystemExit(1)

        # 整理 main 需要的 branch result 渲染片段。
        branch_result = branch_gate(project)  # AGENTS 受管段落渲染输入值

        # 校验 main 的渲染分支条件。
        if not branch_result.get("approved", True) and not args.confirm_branch_governance:

            # 调用 emit_json 处理 main。
            emit_json({
                "errors": ["branch governance requires user confirmation before writing AGENTS.md or docs governance"],
                "branch_gate": branch_result,
                "requires_user_confirmation": True,
            })

            # 抛出 main 已确认的阻断原因。
            raise SystemExit(1)

        # 校验 main 的渲染分支条件。
        if args.confirm_structure_fix:

            # 整理 main 需要的 structure fix 渲染片段。
            structure_fix = apply_structure_fix(project)  # AGENTS 受管段落渲染输入值

            # 校验 main 的渲染分支条件。
            if structure_fix.get("errors"):

                # 调用 emit_json 处理 main。
                emit_json({
                    "errors": ["structure governance fix failed before writing AGENTS.md or docs governance"],
                    "structure_fix": structure_fix,
                })

                # 抛出 main 已确认的阻断原因。
                raise SystemExit(1)

            # 整理 main 需要的 structure result 渲染片段。
            structure_result = structure_gate(project)  # AGENTS 受管段落渲染输入值

            # 校验 main 的渲染分支条件。
            if not structure_result.get("approved", True):

                # 调用 emit_json 处理 main。
                emit_json({
                    "errors": ["structure governance remains blocked after the confirmed structure fix attempt"],
                    "structure_fix": structure_fix,
                    "structure_gate": structure_result,
                })

                # 抛出 main 已确认的阻断原因。
                raise SystemExit(1)

        # 整理 main 需要的 docs preflight 渲染片段。
        docs_preflight = preflight_docs(project)  # AGENTS 受管段落渲染输入值

        # 校验 main 的渲染分支条件。
        if docs_preflight["requires_user_confirmation"] and not args.confirm_docs_layout:

            # 调用 emit_json 处理 main。
            emit_json({
                "errors": ["docs layout requires user confirmation before writing AGENTS.md or docs governance"],
                "docs_preflight": docs_preflight,
                "requires_user_confirmation": True,
            })

            # 抛出 main 已确认的阻断原因。
            raise SystemExit(1)

        # 调用 ensure_global_rule_overrides_file 处理 main。
        ensure_global_rule_overrides_file(project, profile)

        # 调用 scaffold_docs 处理 main。
        scaffold_docs(project)

        # 整理 main 需要的 root text 渲染片段。
        str_root_text = render_root(project, template_dir, profile)  # AGENTS 受管段落渲染输入值

    # 汇总 pending writes，作为 AGENTS 受管段落拼装顺序。
    list_pending_writes: list[tuple[Path, str]] = [(project / "AGENTS.md", str_root_text)]  # AGENTS 受管段落渲染输入值

    # 逐项检查 main 渲染候选。
    for scope in detect_scopes(project)["scopes"]:

        # 整理 main 需要的 scope dir 渲染片段。
        scope_dir = project / scope["path"]  # AGENTS 受管段落渲染输入值

        # 校验 main 的渲染分支条件。
        if scope_dir.exists():

            # 定位 agents path 的文件边界，供 main 后续读写校验使用。
            agents_path = scope_dir / "AGENTS.md"  # AGENTS 受管段落渲染输入值

            # 校验 main 的渲染分支条件。
            if not agents_path.exists() and scope_requires_local_agents(scope_dir):

                # 追加 main 的 AGENTS 渲染行。
                list_pending_writes.append((agents_path, render_scoped(scope, template_dir)))

    # 汇总 errors，作为 AGENTS 受管段落拼装顺序。
    list_errors = root_size_errors([(path.relative_to(project).as_posix(), text) for path, text in list_pending_writes])  # AGENTS 受管段落渲染输入值

    # 校验 main 的渲染分支条件。
    if list_errors:

        # 调用 emit_json 处理 main。
        emit_json({"errors": list_errors, "max_bytes": ROOT_AGENTS_MAX_BYTES})

        # 抛出 main 已确认的阻断原因。
        raise SystemExit(1)

    # 校验 main 的渲染分支条件。
    if args.write and profile is None:

        # 调用 ensure_global_rule_overrides_file 处理 main。
        ensure_global_rule_overrides_file(project, profile)

    # 逐项检查 main 渲染候选。
    for path, text in list_pending_writes:

        # 调用 write_text 处理 main。
        path.write_text(text, encoding="utf-8")

# 校验 模块入口 的渲染分支条件。
if __name__ == "__main__":

    # 调用 main 处理 模块入口。
    main()
