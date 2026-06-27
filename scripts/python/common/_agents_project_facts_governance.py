

# 定义 validate_code_comment_policy_data 的项目事实处理入口。
def validate_code_comment_policy_data(comment_policy: dict[str, Any], *, require_explicit: bool = False) -> list[str]:

    # 返回 validate_code_comment_policy_data 调用载荷。
    return source_governance_config.validate_code_comment_policy_data(comment_policy, require_explicit=require_explicit)


# 定义 validate_global_rule_overrides_data 的项目事实处理入口。
def validate_global_rule_overrides_data(data: dict[str, Any]) -> list[str]:

    # 返回 validate_global_rule_overrides_data 调用载荷。
    return source_governance_config.validate_global_rule_overrides_data(data)


# 定义 load_global_rule_overrides 的项目事实处理入口。
def load_global_rule_overrides(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:

    # 返回 load_global_rule_overrides 调用载荷。
    return source_governance_config.load_global_rule_overrides(root, profile)


# 定义 ensure_global_rule_overrides_file 的项目事实处理入口。
def ensure_global_rule_overrides_file(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:

    # 返回 ensure_global_rule_overrides_file 调用载荷。
    return source_governance_config.ensure_global_rule_overrides_file(root, profile)


# 定义 implementation_constraints_from_profile 的项目事实处理入口。
def implementation_constraints_from_profile(profile: dict[str, Any] | None, root: Path | None = None) -> dict[str, Any]:

    # 返回 implementation_constraints_from_profile 调用载荷。
    return source_governance_config.implementation_constraints_from_profile(profile, root)

# 定义 iter_handwritten_code_files 的项目事实处理入口。
def iter_handwritten_code_files(root: Path, constraints: dict[str, Any]) -> list[Path]:

    # 汇总 allowed exts ，作为 AGENTS 渲染的项目事实候选清单。
    allowed_exts = {str(item).lower() for item in constraints.get("size_limit_extensions", [])}  # 项目事实扫描渲染输入值

    # 汇总 excluded roots ，作为 AGENTS 渲染的项目事实候选清单。
    excluded_roots = {str(item).strip("/\\") for item in constraints.get("size_limit_exclude_roots", [])}  # 项目事实扫描渲染输入值

    # 汇总 files ，作为 AGENTS 渲染的项目事实候选清单。
    list_files: list[Path] = []  # 项目事实扫描渲染输入值

    # 逐项检查 iter_handwritten_code_files 候选项。
    for path in root.rglob("*"):

        # 校验 iter_handwritten_code_files 分支条件。
        if not path.is_file():

            # 分隔 iter_handwritten_code_files 的控制流边界。
            continue

        # 汇总 rel parts ，作为 AGENTS 渲染的项目事实候选清单。
        rel_parts = path.relative_to(root).parts  # 项目事实扫描渲染输入值

        # 校验 iter_handwritten_code_files 分支条件。
        if rel_parts and rel_parts[0] in excluded_roots:

            # 分隔 iter_handwritten_code_files 的控制流边界。
            continue

        # 校验 iter_handwritten_code_files 分支条件。
        if any(part in SKIP_DIRS for part in rel_parts):

            # 分隔 iter_handwritten_code_files 的控制流边界。
            continue

        # 校验 iter_handwritten_code_files 分支条件。
        if path.suffix.lower() in allowed_exts:

            # 追加 iter_handwritten_code_files 诊断。
            list_files.append(path)

    # 返回 iter_handwritten_code_files 调用载荷。
    return sorted(list_files)

# 定义 script_governance_exceptions 的项目事实处理入口。
def script_governance_exceptions(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:

    # 汇总 overrides ，作为 AGENTS 渲染的项目事实候选清单。
    overrides = load_global_rule_overrides(root, profile)["data"]  # 项目事实扫描渲染输入值

    # 解析 script_governance_exceptions 需要的 path 项目事实。
    path = root / str(overrides["tool_script_layout"].get("gui_exception_manifest", ".agents/script-governance-exceptions.json")).strip()  # 项目事实扫描渲染输入值

    # 解析 script_governance_exceptions 需要的 data 项目事实。
    dict_data = read_json(path) if path.exists() else {}  # 项目事实扫描渲染输入值

    # 解析 script_governance_exceptions 需要的 gui startup 项目事实。
    gui_startup = dict_data.get("gui_startup", []) if isinstance(dict_data.get("gui_startup", []), list) else []  # 项目事实扫描渲染输入值

    # 解析 script_governance_exceptions 需要的 normalized 项目事实。
    normalized = sorted(str(item).strip().replace("\\", "/") for item in gui_startup if str(item).strip())  # 项目事实扫描渲染输入值

    # 返回 script_governance_exceptions 调用载荷。
    return {"path": rel(path, root) if path.exists() else path.relative_to(root).as_posix(), "gui_startup": normalized}

# 定义 decomposition_plan_path 的项目事实处理入口。
def decomposition_plan_path(root: Path, relative_file: str, profile: dict[str, Any] | None = None) -> Path:

    # 汇总 overrides ，作为 AGENTS 渲染的项目事实候选清单。
    overrides = load_global_rule_overrides(root, profile)["data"]  # 项目事实扫描渲染输入值

    # 解析 decomposition_plan_path 需要的 plan root 项目事实。
    plan_root = str(overrides["source_file_limits"].get("decomposition_plan_root", "docs/development/decomposition-plans")).strip().strip("/\\")  # 项目事实扫描渲染输入值

    # 解析 decomposition_plan_path 需要的 sanitized 项目事实。
    sanitized = relative_file.replace("\\", "/").replace(":", "")  # 项目事实扫描渲染输入值

    # 返回 decomposition_plan_path 调用载荷。
    return root / plan_root / f"{sanitized}.md"

# 定义 is_agents_md_generator_runtime_root 的项目事实处理入口。
def is_agents_md_generator_runtime_root(root: Path) -> bool:

    # 只把 agents-md-generator 自身仓库识别为 skill runtime 根。
    return (
        root.name == "agents-md-generator"
        and (root / "SKILL.md").is_file()
        and (root / "scripts" / "python").is_dir()
    )

# 定义 managed_script_roots 的项目事实处理入口。
def managed_script_roots(root: Path, profile: dict[str, Any] | None = None) -> list[Path]:

    # 汇总 candidates ，作为 AGENTS 渲染的项目事实候选清单。
    list_candidates = []  # 项目事实扫描渲染输入值

    # agents-md-generator 自身的 scripts/python 是 skill runtime，不是普通项目脚本族。
    if is_agents_md_generator_runtime_root(root):

        # 返回空集合，避免要求 runtime Python 文件配套 shell/bat/PowerShell 包装器。
        return []

    # 校验 managed_script_roots 分支条件。
    if (root / "scripts").is_dir():

        # 追加 managed_script_roots 诊断。
        list_candidates.append(root / "scripts")

    # 汇总 unique ，作为 AGENTS 渲染的项目事实候选清单。
    list_unique: list[Path] = []  # 项目事实扫描渲染输入值

    # 解析 managed_script_roots 需要的 seen 项目事实。
    set_seen: set[str] = set()  # 项目事实扫描渲染输入值

    # 逐项检查 managed_script_roots 候选项。
    for item in list_candidates:

        # 解析 managed_script_roots 需要的 key 项目事实。
        key = normalize_path_key(item)  # 项目事实扫描渲染输入值

        # 校验 managed_script_roots 分支条件。
        if item.is_dir() and key not in set_seen:

            # 调用 add 处理 managed_script_roots。
            set_seen.add(key)

            # 追加 managed_script_roots 诊断。
            list_unique.append(item)

    # 返回 managed_script_roots 调用载荷。
    return list_unique

# 定义 script_layout_facts 的项目事实处理入口。
def script_layout_facts(root: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:

    # 汇总 constraints ，作为 AGENTS 渲染的项目事实候选清单。
    dict_constraints = implementation_constraints_from_profile(profile, root)  # 项目事实扫描渲染输入值

    # 解析 script_layout_facts 需要的 layout 项目事实。
    layout = dict_constraints.get("script_layout", {}) if isinstance(dict_constraints.get("script_layout", {}), dict) else {}  # 项目事实扫描渲染输入值

    # 汇总 families ，作为 AGENTS 渲染的项目事实候选清单。
    families = layout.get("families", {}) if isinstance(layout.get("families", {}), dict) else {}  # 项目事实扫描渲染输入值

    # 解析 script_layout_facts 需要的 required root 项目事实。
    required_root = str(layout.get("required_root", "scripts")).strip("/\\") or "scripts"  # 项目事实扫描渲染输入值

    # 汇总 exceptions ，作为 AGENTS 渲染的项目事实候选清单。
    dict_exceptions = script_governance_exceptions(root, profile)  # 项目事实扫描渲染输入值

    # 解析 script_layout_facts 需要的 gui set 项目事实。
    set_gui_set = set(dict_exceptions["gui_startup"])  # 项目事实扫描渲染输入值

    # 汇总 roots ，作为 AGENTS 渲染的项目事实候选清单。
    list_roots = managed_script_roots(root, profile)  # 项目事实扫描渲染输入值

    # 汇总 triad members ，作为 AGENTS 渲染的项目事实候选清单。
    dict_triad_members: dict[tuple[str, str], set[str]] = {}  # 项目事实扫描渲染输入值

    # 汇总 layout violations ，作为 AGENTS 渲染的项目事实候选清单。
    list_layout_violations: list[str] = []  # 项目事实扫描渲染输入值

    # 汇总 allowed families ，作为 AGENTS 渲染的项目事实候选清单。
    list_allowed_families = list(families)  # 项目事实扫描渲染输入值

    # 解析 script_layout_facts 需要的 extension to family 项目事实。
    extension_to_family = {str(extension).lower(): family for family, extension in families.items()}  # 项目事实扫描渲染输入值

    # 逐项检查 script_layout_facts 候选项。
    for scripts_root in list_roots:

        # 校验 script_layout_facts 分支条件。
        if scripts_root.name != required_root and scripts_root.relative_to(root).as_posix().endswith(f"/{required_root}") is False:

            # 分隔 script_layout_facts 的控制流边界。
            continue

        # 逐项检查 script_layout_facts 候选项。
        for path in sorted(scripts_root.rglob("*")):

            # 校验 script_layout_facts 分支条件。
            if not path.is_file():

                # 分隔 script_layout_facts 的控制流边界。
                continue

            # 定位 rel path 的文件边界，供 script_layout_facts 后续读写校验使用。
            rel_path = path.relative_to(root).as_posix()  # 项目事实扫描渲染输入值

            # 校验 script_layout_facts 分支条件。
            if rel_path in set_gui_set:

                # 分隔 script_layout_facts 的控制流边界。
                continue

            # 解析 script_layout_facts 需要的 relative 项目事实。
            relative = path.relative_to(scripts_root)  # 项目事实扫描渲染输入值

            # 汇总 parts ，作为 AGENTS 渲染的项目事实候选清单。
            parts = relative.parts  # 项目事实扫描渲染输入值

            # 校验 script_layout_facts 分支条件。
            if not parts:

                # 分隔 script_layout_facts 的控制流边界。
                continue

            # 解析 script_layout_facts 需要的 family 项目事实。
            family = parts[0]  # 项目事实扫描渲染输入值

            # 解析 script_layout_facts 需要的 suffix 项目事实。
            suffix = path.suffix.lower()  # 项目事实扫描渲染输入值

            # 校验 script_layout_facts 分支条件。
            if family not in families:

                # 解析 script_layout_facts 需要的 expected family 项目事实。
                expected_family = extension_to_family.get(suffix, "")  # 项目事实扫描渲染输入值

                # 校验 script_layout_facts 分支条件。
                if len(parts) == 1 and expected_family:

                    # 追加 script_layout_facts 诊断。
                    list_layout_violations.append(
                        f"script layout requires {required_root}/{expected_family}/<function>/<name>{suffix}: {path.relative_to(root).as_posix()}"
                    )

                # 校验 script_layout_facts 分支条件。
                elif expected_family:

                    # 追加 script_layout_facts 诊断。
                    list_layout_violations.append(
                        f"unsupported script family under {required_root} (allowed: {', '.join(list_allowed_families)}): {path.relative_to(root).as_posix()}"
                    )

                # 分隔 script_layout_facts 的控制流边界。
                continue

            # 解析 script_layout_facts 需要的 expected extension 项目事实。
            expected_extension = str(families[family]).lower()  # 项目事实扫描渲染输入值

            # 校验 script_layout_facts 分支条件。
            if suffix != expected_extension:

                # 追加 script_layout_facts 诊断。
                list_layout_violations.append(
                    f"script extension {suffix or '<none>'} does not match family `{family}` (expected {expected_extension}): {rel_path}"
                )

                # 分隔 script_layout_facts 的控制流边界。
                continue

            # 校验 script_layout_facts 分支条件。
            if len(parts) < 3:

                # 追加 script_layout_facts 诊断。
                list_layout_violations.append(
                    f"script layout requires {required_root}/{family}/<function>/<name>{expected_extension}: {rel_path}"
                )

                # 分隔 script_layout_facts 的控制流边界。
                continue

            # 定位 function path 的文件边界，供 script_layout_facts 后续读写校验使用。
            function_path = "/".join(parts[1:-1])  # 项目事实扫描渲染输入值

            # 解析 script_layout_facts 需要的 stem 项目事实。
            stem = path.stem  # 项目事实扫描渲染输入值

            # 调用 add 处理 script_layout_facts。
            dict_triad_members.setdefault((function_path, stem), set()).add(family)

    # 汇总 triad gaps ，作为 AGENTS 渲染的项目事实候选清单。
    list_triad_gaps: list[str] = []  # 项目事实扫描渲染输入值

    # 校验 script_layout_facts 分支条件。
    if layout.get("require_full_triad", True):

        # 汇总 required families ，作为 AGENTS 渲染的项目事实候选清单。
        set_required_families = set(families)  # 项目事实扫描渲染输入值

        # 逐项检查 script_layout_facts 候选项。
        for (function_path, stem), present in sorted(dict_triad_members.items()):

            # 校验 script_layout_facts 分支条件。
            if present != set_required_families:

                # 解析 script_layout_facts 需要的 missing 项目事实。
                missing = sorted(set_required_families - present)  # 项目事实扫描渲染输入值

                # 校验 script_layout_facts 分支条件。
                if missing:

                    # 追加 script_layout_facts 诊断。
                    list_triad_gaps.append(f"missing script family variants for {required_root}/<family>/{function_path}/{stem}: {missing}")

    # 返回 script_layout_facts 调用载荷。
    return {
        "gui_script_exemptions": dict_exceptions["gui_startup"],
        "tool_script_layout_violations": list_layout_violations,
        "script_triad_gaps": list_triad_gaps,
    }

# 定义 extract_context 的项目事实处理入口。
def extract_context(root: Path) -> dict[str, Any]:

    # 解析 extract_context 需要的 profile 项目事实。
    profile = project_profile(root)  # 项目事实扫描渲染输入值

    # 汇总 documentation names ，作为 AGENTS 渲染的项目事实候选清单。
    set_documentation_names = {"README.md", "CONTRIBUTING.md", "SECURITY.md", "ARCHITECTURE.md"}  # 项目事实扫描渲染输入值

    # 解析 extract_context 需要的 documentation 项目事实。
    documentation = [name for name in sorted(set_documentation_names) if (root / name).exists()]  # 项目事实扫描渲染输入值

    # 逐项检查 extract_context 候选项。
    for docs_dir in ("docs", "Documentation"):

        # 解析 extract_context 需要的 base 项目事实。
        base = root / docs_dir  # 项目事实扫描渲染输入值

        # 校验 extract_context 分支条件。
        if base.exists():

            # 调用 extend 处理 extract_context。
            documentation.extend(rel(path, root) for path in sorted(base.glob("*.md"))[:12])

    # 汇总 adr dirs ，作为 AGENTS 渲染的项目事实候选清单。
    list_adr_dirs = ["adr", "adrs", "docs/adr", "docs/adrs", "docs/decisions", "architecture/decisions"]  # 项目事实扫描渲染输入值

    # 汇总 adrs ，作为 AGENTS 渲染的项目事实候选清单。
    list_adrs: list[str] = []  # 项目事实扫描渲染输入值

    # 逐项检查 extract_context 候选项。
    for adr_dir in list_adr_dirs:

        # 解析 extract_context 需要的 base 项目事实。
        base = root / adr_dir  # 项目事实扫描渲染输入值

        # 校验 extract_context 分支条件。
        if base.exists():

            # 调用 extend 处理 extract_context。
            list_adrs.extend(rel(path, root) for path in sorted(base.glob("*.md"))[:12])

    # 汇总 utilities ，作为 AGENTS 渲染的项目事实候选清单。
    list_utilities: list[str] = []  # 项目事实扫描渲染输入值

    # 逐项检查 extract_context 候选项。
    for name in ("Makefile", "justfile"):

        # 校验 extract_context 分支条件。
        if (root / name).exists():

            # 追加 extract_context 诊断。
            list_utilities.append(name)

    # 解析 extract_context 需要的 scripts dir 项目事实。
    scripts_dir = root / "scripts"  # 项目事实扫描渲染输入值

    # 校验 extract_context 分支条件。
    if scripts_dir.exists():

        # 调用 extend 处理 extract_context。
        list_utilities.extend(rel(path, root) for path in sorted(scripts_dir.iterdir()) if path.is_file())

    # 汇总 quality names ，作为 AGENTS 渲染的项目事实候选清单。
    list_quality_names = [  # 项目事实扫描渲染输入值
        ".pre-commit-config.yaml",  # 项目事实扫描渲染输入值
        ".pre-commit-config.yml",  # 项目事实扫描渲染输入值
        "ruff.toml",  # 项目事实扫描渲染输入值
        ".ruff.toml",  # 项目事实扫描渲染输入值
        "mypy.ini",  # 项目事实扫描渲染输入值
        "pytest.ini",  # 项目事实扫描渲染输入值
        "tsconfig.json",  # 项目事实扫描渲染输入值
        "eslint.config.js",  # 项目事实扫描渲染输入值
        "eslint.config.mjs",  # 项目事实扫描渲染输入值
        ".eslintrc",  # 项目事实扫描渲染输入值
        ".eslintrc.json",  # 项目事实扫描渲染输入值
        ".prettierrc",  # 项目事实扫描渲染输入值
        ".prettierrc.json",  # 项目事实扫描渲染输入值
        "phpstan.neon",  # 项目事实扫描渲染输入值
    ]

    # 汇总 quality configs ，作为 AGENTS 渲染的项目事实候选清单。
    list_quality_configs = existing_paths(root, list_quality_names)  # 项目事实扫描渲染输入值

    # 汇总 platform names ，作为 AGENTS 渲染的项目事实候选清单。
    list_platform_names = [  # 项目事实扫描渲染输入值
        "Dockerfile",  # 项目事实扫描渲染输入值
        "docker-compose.yml",  # 项目事实扫描渲染输入值
        "docker-compose.yaml",  # 项目事实扫描渲染输入值
        "compose.yml",  # 项目事实扫描渲染输入值
        "compose.yaml",  # 项目事实扫描渲染输入值
        ".devcontainer/devcontainer.json",  # 项目事实扫描渲染输入值
        ".tool-versions",  # 项目事实扫描渲染输入值
        ".python-version",  # 项目事实扫描渲染输入值
        ".nvmrc",  # 项目事实扫描渲染输入值
        "mise.toml",  # 项目事实扫描渲染输入值
        ".mise.toml",  # 项目事实扫描渲染输入值
        "flake.nix",  # 项目事实扫描渲染输入值
        "shell.nix",  # 项目事实扫描渲染输入值
        "Taskfile.yml",  # 项目事实扫描渲染输入值
        "Taskfile.yaml",  # 项目事实扫描渲染输入值
    ]

    # 汇总 platform files ，作为 AGENTS 渲染的项目事实候选清单。
    list_platform_files = existing_paths(root, list_platform_names)  # 项目事实扫描渲染输入值

    # 汇总 ide names ，作为 AGENTS 渲染的项目事实候选清单。
    list_ide_names = [  # 项目事实扫描渲染输入值
        ".editorconfig",  # 项目事实扫描渲染输入值
        ".vscode/settings.json",  # 项目事实扫描渲染输入值
        ".vscode/extensions.json",  # 项目事实扫描渲染输入值
        ".idea/codeStyles/Project.xml",  # 项目事实扫描渲染输入值
        ".idea/inspectionProfiles/Project_Default.xml",  # 项目事实扫描渲染输入值
    ]

    # 汇总 ide settings ，作为 AGENTS 渲染的项目事实候选清单。
    list_ide_settings = existing_paths(root, list_ide_names)  # 项目事实扫描渲染输入值

    # 汇总 workspace settings ，作为 AGENTS 渲染的项目事实候选清单。
    workspace_settings = discover_workspace_settings(root)  # 项目事实扫描渲染输入值

    # 汇总 architecture names ，作为 AGENTS 渲染的项目事实候选清单。
    list_architecture_names = [  # 项目事实扫描渲染输入值
        "CODEOWNERS",  # 项目事实扫描渲染输入值
        ".github/CODEOWNERS",  # 项目事实扫描渲染输入值
        "ARCHITECTURE.md",  # 项目事实扫描渲染输入值
        "docs/architecture.md",  # 项目事实扫描渲染输入值
        "docs/ARCHITECTURE.md",  # 项目事实扫描渲染输入值
        "docs/adr/index.md",  # 项目事实扫描渲染输入值
    ]

    # 汇总 architecture files ，作为 AGENTS 渲染的项目事实候选清单。
    list_architecture_files = existing_paths(root, list_architecture_names)  # 项目事实扫描渲染输入值

    # 汇总 dependency names ，作为 AGENTS 渲染的项目事实候选清单。
    list_dependency_names = [  # 项目事实扫描渲染输入值
        ".github/dependabot.yml",  # 项目事实扫描渲染输入值
        ".github/dependabot.yaml",  # 项目事实扫描渲染输入值
        "renovate.json",  # 项目事实扫描渲染输入值
        ".renovaterc",  # 项目事实扫描渲染输入值
        ".renovaterc.json",  # 项目事实扫描渲染输入值
        "dependabot.yml",  # 项目事实扫描渲染输入值
        "dependabot.yaml",  # 项目事实扫描渲染输入值
    ]

    # 汇总 dependency configs ，作为 AGENTS 渲染的项目事实候选清单。
    list_dependency_configs = existing_paths(root, list_dependency_names)  # 项目事实扫描渲染输入值

    # 汇总 hook names ，作为 AGENTS 渲染的项目事实候选清单。
    list_hook_names = [  # 项目事实扫描渲染输入值
        "lefthook.yml",  # 项目事实扫描渲染输入值
        ".lefthook.yml",  # 项目事实扫描渲染输入值
        "captainhook.json",  # 项目事实扫描渲染输入值
        ".pre-commit-config.yaml",  # 项目事实扫描渲染输入值
        ".pre-commit-config.yml",  # 项目事实扫描渲染输入值
        "Build/hooks/pre-push",  # 项目事实扫描渲染输入值
        ".githooks/pre-commit",  # 项目事实扫描渲染输入值
        ".githooks/pre-push",  # 项目事实扫描渲染输入值
    ]

    # 汇总 hook configs ，作为 AGENTS 渲染的项目事实候选清单。
    list_hook_configs = existing_paths(root, list_hook_names)  # 项目事实扫描渲染输入值

    # 校验 extract_context 分支条件。
    if (root / ".husky").is_dir():

        # 追加 extract_context 诊断。
        list_hook_configs.append(".husky/")

    # 汇总 github names ，作为 AGENTS 渲染的项目事实候选清单。
    list_github_names = [  # 项目事实扫描渲染输入值
        ".github/CODEOWNERS",  # 项目事实扫描渲染输入值
        ".github/copilot-instructions.md",  # 项目事实扫描渲染输入值
        ".github/dependabot.yml",  # 项目事实扫描渲染输入值
        ".github/dependabot.yaml",  # 项目事实扫描渲染输入值
        ".github/renovate.json",  # 项目事实扫描渲染输入值
    ]

    # 汇总 github settings ，作为 AGENTS 渲染的项目事实候选清单。
    list_github_settings = existing_paths(root, list_github_names)  # 项目事实扫描渲染输入值

    # 解析 extract_context 需要的 rulesets dir 项目事实。
    rulesets_dir = root / ".github" / "rulesets"  # 项目事实扫描渲染输入值

    # 校验 extract_context 分支条件。
    if rulesets_dir.exists():

        # 调用 extend 处理 extract_context。
        list_github_settings.extend(rel(path, root) for path in sorted(rulesets_dir.glob("*.json"))[:12])

    # 汇总 coverage names ，作为 AGENTS 渲染的项目事实候选清单。
    list_coverage_names = [  # 项目事实扫描渲染输入值
        "src",  # 项目事实扫描渲染输入值
        "app",  # 项目事实扫描渲染输入值
        "lib",  # 项目事实扫描渲染输入值
        "tests",  # 项目事实扫描渲染输入值
        "test",  # 项目事实扫描渲染输入值
        "docs",  # 项目事实扫描渲染输入值
        "Documentation",  # 项目事实扫描渲染输入值
        "scripts",  # 项目事实扫描渲染输入值
        "tools",  # 项目事实扫描渲染输入值
        "cmd",  # 项目事实扫描渲染输入值
        "internal",  # 项目事实扫描渲染输入值
        "pkg",  # 项目事实扫描渲染输入值
        ".github/workflows",  # 项目事实扫描渲染输入值
    ]

    # 汇总 directory coverage candidates ，作为 AGENTS 渲染的项目事实候选清单。
    directory_coverage_candidates = [  # 项目事实扫描渲染输入值
        name for name in list_coverage_names  # 项目事实扫描渲染输入值
        if (root / name).is_dir() and not (root / name / "AGENTS.md").exists()  # 项目事实扫描渲染输入值
    ]

    # 汇总 reference projects ，作为 AGENTS 渲染的项目事实候选清单。
    list_reference_projects: list[str] = []  # 项目事实扫描渲染输入值

    # 逐项检查 extract_context 候选项。
    for base_name in ("reference-projects", "references/projects", "examples/reference-projects"):

        # 解析 extract_context 需要的 base 项目事实。
        base = root / base_name  # 项目事实扫描渲染输入值

        # 校验 extract_context 分支条件。
        if base.exists() and base.is_dir():

            # 逐项检查 extract_context 候选项。
            for child in sorted(base.iterdir()):

                # 校验 extract_context 分支条件。
                if child.is_dir():

                    # 追加 extract_context 诊断。
                    list_reference_projects.append(rel(child, root))

    # 汇总 agent config names ，作为 AGENTS 渲染的项目事实候选清单。
    list_agent_config_names = [  # 项目事实扫描渲染输入值
        "AGENTS.md",  # 项目事实扫描渲染输入值
        "CLAUDE.md",  # 项目事实扫描渲染输入值
        "GEMINI.md",  # 项目事实扫描渲染输入值
        ".github/copilot-instructions.md",  # 项目事实扫描渲染输入值
        ".cursorrules",  # 项目事实扫描渲染输入值
        ".aider.conf.yml",  # 项目事实扫描渲染输入值
        ".aider.conf.yaml",  # 项目事实扫描渲染输入值
    ]

    # 汇总 agent configs ，作为 AGENTS 渲染的项目事实候选清单。
    agent_configs = [name for name in list_agent_config_names if (root / name).exists()]  # 项目事实扫描渲染输入值

    # 汇总 golden samples ，作为 AGENTS 渲染的项目事实候选清单。
    list_golden_samples: list[str] = []  # 项目事实扫描渲染输入值

    # 汇总 sample patterns ，作为 AGENTS 渲染的项目事实候选清单。
    list_sample_patterns = [  # 项目事实扫描渲染输入值
        "tests/test_*.*",  # 项目事实扫描渲染输入值
        "tests/*_test.*",  # 项目事实扫描渲染输入值
        "src/*.*",  # 项目事实扫描渲染输入值
        "app/*.*",  # 项目事实扫描渲染输入值
        "lib/*.*",  # 项目事实扫描渲染输入值
        "examples/*.*",  # 项目事实扫描渲染输入值
        "samples/*.*",  # 项目事实扫描渲染输入值
    ]

    # 逐项检查 extract_context 候选项。
    for pattern in list_sample_patterns:

        # 逐项检查 extract_context 候选项。
        for path in sorted(root.glob(pattern)):

            # 校验 extract_context 分支条件。
            if path.is_file() and len(list_golden_samples) < 8:

                # 追加 extract_context 诊断。
                list_golden_samples.append(rel(path, root))

    # 保存 script governance 映射，维持 extract_context 的字段关系。
    dict_script_governance = script_layout_facts(root, profile)  # 项目事实扫描渲染输入值

    # 汇总 implementation constraints ，作为 AGENTS 渲染的项目事实候选清单。
    dict_implementation_constraints = implementation_constraints_from_profile(profile, root)  # 项目事实扫描渲染输入值

    # 汇总 overrides ，作为 AGENTS 渲染的项目事实候选清单。
    dict_overrides = load_global_rule_overrides(root, profile)  # 项目事实扫描渲染输入值

    # 返回 extract_context 调用载荷。
    return {
        "documentation": sorted(dict.fromkeys(documentation)),
        "adrs": sorted(dict.fromkeys(list_adrs)),
        "utilities": sorted(dict.fromkeys(list_utilities)),
        "quality_configs": sorted(dict.fromkeys(list_quality_configs)),
        "platform_files": sorted(dict.fromkeys(list_platform_files)),
        "ide_settings": sorted(dict.fromkeys(list_ide_settings)),
        "workspace_settings": sorted(dict.fromkeys(workspace_settings)),
        "architecture_files": sorted(dict.fromkeys(list_architecture_files)),
        "dependency_configs": sorted(dict.fromkeys(list_dependency_configs)),
        "hook_configs": sorted(dict.fromkeys(list_hook_configs)),
        "github_settings": sorted(dict.fromkeys(list_github_settings)),
        "directory_coverage_candidates": sorted(dict.fromkeys(directory_coverage_candidates)),
        "reference_projects": sorted(dict.fromkeys(list_reference_projects)),
        "agent_configs": sorted(dict.fromkeys(agent_configs)),
        "golden_samples": sorted(dict.fromkeys(list_golden_samples)),
        "ci_rules": workflow_runs(root),
        "implementation_constraints": dict_implementation_constraints,
        "global_rule_overrides_path": dict_overrides["path"].relative_to(root).as_posix(),
        "global_rule_overrides_exists": dict_overrides["exists"],
        "global_rule_overrides_valid": not dict_overrides["errors"],
        "global_rule_overrides_errors": list(dict_overrides["errors"]),
        "global_rule_overrides": dict_overrides["data"],
        "gui_script_exemptions": dict_script_governance["gui_script_exemptions"],
        "tool_script_layout_violations": dict_script_governance["tool_script_layout_violations"],
        "script_triad_gaps": dict_script_governance["script_triad_gaps"],
    }

# 定义 detect_scopes 的项目事实处理入口。
def detect_scopes(root: Path) -> dict[str, Any]:

    # 汇总 candidates ，作为 AGENTS 渲染的项目事实候选清单。
    dict_candidates = {  # 项目事实扫描渲染输入值
        "src": "source code patterns",  # 项目事实扫描渲染输入值
        "tests": "test conventions and fixtures",  # 项目事实扫描渲染输入值
        "test": "test conventions and fixtures",  # 项目事实扫描渲染输入值
        "docs": "documentation standards",  # 项目事实扫描渲染输入值
        "frontend": "frontend stack and UI conventions",  # 项目事实扫描渲染输入值
        "web": "frontend stack and UI conventions",  # 项目事实扫描渲染输入值
        "backend": "backend stack and service conventions",  # 项目事实扫描渲染输入值
        "internal": "internal module boundaries",  # 项目事实扫描渲染输入值
        "cmd": "CLI entry points and flags",  # 项目事实扫描渲染输入值
        "scripts": "automation script conventions",  # 项目事实扫描渲染输入值
        ".github/workflows": "CI workflow rules",  # 项目事实扫描渲染输入值
    }

    # 汇总 scopes ，作为 AGENTS 渲染的项目事实候选清单。
    list_scopes = []  # 项目事实扫描渲染输入值

    # 逐项检查 detect_scopes 候选项。
    for path, purpose in dict_candidates.items():

        # 解析 detect_scopes 需要的 full 项目事实。
        full = root / path  # 项目事实扫描渲染输入值

        # 校验 detect_scopes 分支条件。
        if full.exists() and full.is_dir():

            # 追加 detect_scopes 诊断。
            list_scopes.append({"path": path, "purpose": purpose, "agents_file": f"{path}/AGENTS.md"})

    # 汇总 packages ，作为 AGENTS 渲染的项目事实候选清单。
    packages = root / "packages"  # 项目事实扫描渲染输入值

    # 校验 detect_scopes 分支条件。
    if packages.exists():

        # 逐项检查 detect_scopes 候选项。
        for child in sorted(packages.iterdir()):

            # 校验 detect_scopes 分支条件。
            if child.is_dir():

                # 解析 detect_scopes 需要的 path 项目事实。
                path = child.relative_to(root).as_posix()  # 项目事实扫描渲染输入值

                # 追加 detect_scopes 诊断。
                list_scopes.append({"path": path, "purpose": "workspace package-specific rules", "agents_file": f"{path}/AGENTS.md"})

    # 返回 detect_scopes 调用载荷。
    return {"scopes": list_scopes}
