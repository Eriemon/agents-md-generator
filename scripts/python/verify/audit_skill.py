"""审计 agents-md-generator 技能包的结构、引用和治理规则一致性。"""

# 导入 技能审计 所需的依赖模块。
from __future__ import annotations

# 分类脚本可从任意任务目录直接执行，这里补齐兄弟任务模块路径。
import sys
from pathlib import Path

_scripts_python_root = Path(__file__).resolve().parents[1]
for _task_dir in _scripts_python_root.iterdir():
    if _task_dir.is_dir():
        _task_path = str(_task_dir)
        if _task_path not in sys.path:
            sys.path.insert(0, _task_path)

# 导入 技能审计 所需的依赖模块。
import argparse
import ast
import json
import re
from pathlib import Path
import sys

sys.dont_write_bytecode = True

# 导入 技能审计 所需的依赖模块。
from agents_common import SCRIPT_TASK_BY_NAME, emit_json, resolve_project
from agents_project_facts import decomposition_plan_path, load_global_rule_overrides
from source_governance_config import validate_script_output_policy_data
from version_policy import version_policy_error

CORE_REQUIRED_FILES = [
    "SKILL.md",
]

SELF_REQUIRED_FILES = [
    "VERSION",
    "agents/openai.yaml",
    "evals/evals.json",
    "references/agents-md-guidance.md",
    "references/book-rules-coverage.md",
    "references/capability-coverage.md",
    "references/coding-behavior-language-routing.md",
    "references/skill-design-coverage.md",
    "references/question-bank.md",
    "references/review-checklist.md",
    "references/script-guide.md",
    "references/evaluation-scenarios.md",
    "assets/templates/root-agents.md",
    "assets/templates/scoped-agents.md",
    "assets/templates/global-codex-agents.md",
    "config/source-governance.json",
    "config/script-output-policy-default.json",
    "scripts/python/verify/check_source_governance.py",
    "scripts/python/detect/codex_token_usage_review.py",
    "scripts/python/detect/inspect_project.py",
    "scripts/python/design/collect_design_profile.py",
    "scripts/python/design/design_review_gate.py",
    "scripts/python/detect/extract_commands.py",
    "scripts/python/detect/extract_context.py",
    "scripts/python/detect/detect_scopes.py",
    "scripts/python/render/render_agents.py",
    "scripts/python/docs/manage_docs.py",
    "scripts/python/dirs/manage_dirs.py",
    "scripts/python/dirs/manage_dirs_review.py",
    "scripts/python/dirs/manage_dirs_state.py",
    "scripts/python/common/agents_decisions.py",
    "scripts/python/release/install_skill.py",
    "scripts/python/verify/review_governance.py",
    "scripts/python/release/select_engineering_rules.py",
    "scripts/python/verify/verify_agents.py",
    "scripts/python/detect/check_freshness.py",
    "scripts/python/verify/quick_validate.py",
    "scripts/python/verify/run_confidence_gate.py",
    "scripts/python/verify/source_governance.py",
    "scripts/python/verify/source_governance_config.py",
    "scripts/python/render/create_agent_shims.py",
    "scripts/python/verify/audit_skill.py",
    "scripts/python/verify/evaluate_skill.py",
]

SELF_DISALLOWED_ROOT_DOCS = {"CHANGELOG.md", "INSTALL.md", "INSTALLATION.md"}

DISALLOWED_CACHE_SUFFIXES = {".pyc", ".pyo"}

LOCAL_REFERENCE_RE = re.compile(
    r"G:[/\\]html|ref[/\\](agent-rules|html)|\b[A-Za-z]:[/\\][^\s`'\"<>)]*",
    flags=re.IGNORECASE,
)

SKILL_NAME_RE = re.compile(r"^[a-z0-9-]+$")

TEMPLATE_PLACEHOLDER_RE = re.compile(r"{{([A-Z0-9_]+)}}")

KNOWN_TEMPLATE_PLACEHOLDERS = {
    "root-agents.md": {
        "GENERATED_BODY",
        "TIMESTAMP",
        "VERIFIED_TIMESTAMP",
        "PROJECT_OVERVIEW",
        "CONTROL_PROFILE",
        "DIRECTORY_CONTRACT",
        "REMOTE_SERVER_CONTRACT",
        "RELEASE_CONTRACT",
        "ENGINEERING_RULE_CONTRACT",
        "SKILL_DESIGN_CONTRACT",
        "CONVERSATION_COMPLETION_CONTRACT",
        "MEMORY_CONTRACT",
        "CODING_BEHAVIOR_BASELINE",
        "SCRIPT_OUTPUT_POLICY",
        "DOCUMENTATION_GOVERNANCE_CONTRACT",
        "VERIFICATION_STATUS",
        "COMMAND_SOURCE",
        "COMMAND_ROWS",
        "FILE_MAP",
        "GOLDEN_SAMPLE_ROWS",
        "UTILITY_ROWS",
        "HEURISTIC_ROWS",
        "REPOSITORY_SETTINGS",
        "HOOK_POLICY",
        "CI_RULES",
        "GITHUB_SETTINGS",
        "DIRECTORY_COVERAGE",
        "KEY_DECISIONS",
        "EVOLUTION_TEMPLATE_GUIDANCE",
        "ALWAYS_RULES",
        "ASK_FIRST_RULES",
        "NEVER_RULES",
        "CODEBASE_STATE",
        "TERMINOLOGY_ROWS",
        "SCOPE_INDEX",
    },
    "scoped-agents.md": {
        "TIMESTAMP",
        "VERIFIED_TIMESTAMP",
        "SCOPE_NAME",
        "SCOPE_PATH",
        "SCOPE_OVERVIEW",
        "LOCAL_COMMANDS",
        "TESTING_RULES",
        "LOCAL_STRUCTURE",
        "CODE_STYLE",
        "GIT_WORKFLOW",
        "LOCAL_BOUNDARIES",
        "SCOPE_PURPOSE",
    },
}

COMMON_GROUP_LABELS = (
    "Skill development groups are",
    "Engineering development groups are",
)

TAKEOVER_REMOTE_PROMPT_RULE = (
    "remote structure governance as separate from the remote-server enablement and task-route mapping flow"
)

OPENAI_REQUIRED_PROMPT_SNIPPETS = (
    "explicitly ask for and confirm the default conversation language",
    "explicitly ask whether the work folder needs remote servers",
    "future remote server validation must resolve the matched task route primary server from `.agents/agents-control.json`",
    "automatically try registered fallback servers",
    "stop for unmatched tasks until AGENTS.md/profile is updated",
    "Coding Behavior Baseline language skill routing",
    "coding_behavior.language_skill_routing",
    "readable-python-generator",
    "readable-script-generator",
)

OPENAI_TOKEN_USAGE_PROMPT_SNIPPETS = (
    "explicitly asks for codex token usage statistics",
    "codex_token_usage_review.py",
    "keep `--sessions-root` inside the active codex sessions tree",
    "do not trigger this token-usage path for generic cost, optimization, or session-health questions",
    "only in codex environments where `$codex_home/sessions` or `~/.codex/sessions` exists",
)

REFERENCE_ALIGNMENT_RULES = {
    "references/review-checklist.md": (
        "default_conversation_language",
        "natural-language responses stay in that configured language unless the user explicitly switches languages",
        "use_remote_server",
        "automatic fallback rule",
        "unmatched remote tasks must update AGENTS.md/profile",
        "root-level file whitelist",
        "confirm-structure-fix",
        "source and target paths must both stay inside the governed remote plan",
        "64KB UTF-8",
        ".agents/global-rule-overrides.json",
        "thread heartbeat",
        "shell",
        "powershell",
        "extra_requirements",
        "reviewer_type=\"subagent\"",
        "reviewed_answers_hash",
    ),
    "references/script-guide.md": (
        "default_conversation_language",
        "explicit natural-language reply rule",
        "use_remote_server",
        "extra_requirements",
        "design_review",
        "reviewed_profile_hash",
        "task-route table",
        "update AGENTS.md/profile before validation continues",
        "allow the conservative structure-fix attempt",
        "allowed_root_files",
        "path_classes",
        "--installed-skill-dir skills/agents-md-generator",
        ".agents/global-rule-overrides.json",
        "global JSON governance config",
        "codex_token_usage_review.py",
        "只在用户明确要求进行 Codex Token 用量统计时调用",
        "仅在当前环境可解析到 `$CODEX_HOME/sessions` 或 `~/.codex/sessions` 且目录存在时执行",
        "sessions_root_outside_codex_root",
    ),
    "references/skill-design-coverage.md": (
        "default_conversation_language",
        "locks natural-language replies to it",
        "use_remote_server",
        "automatic fallback gate",
        "unmatched-task blocking gate",
        "root-level file whitelist",
        "confirm-structure-fix",
        "remote mutation governance for all actions",
        "global `.codex/AGENTS.md`",
        "local JSON governance config",
    ),
}

LANGUAGE_SKILL_ROUTING_ALIGNMENT_RULES = {
    "references/coding-behavior-language-routing.md": (
        "Python",
        "readable-python-generator",
        "readable-script-generator",
        "bat/cmd",
        "shell/bash",
        "PowerShell",
        "Tcl",
        "脚本包装器调用 Python",
        "不能把语句、注释、函数粘连到一起",
        "严禁把代码压缩到一行",
        "炫技代码",
    ),
    "references/review-checklist.md": (
        "Generated root `AGENTS.md` must include Coding Behavior Baseline language skill routing",  # 语言路由审计片段
        ".agents/global-rule-overrides.json",
        "readable-python-generator",
        "readable-script-generator",
        "严禁把代码压缩到一行",
    ),
    "references/script-guide.md": (
        "`render_agents.py` emits Coding Behavior Baseline language skill routing",  # 语言路由渲染审计证据
        "coding_behavior.language_skill_routing",
        "`verify_agents.py` rejects managed root `AGENTS.md` files that omit or weaken language skill routing",
    ),
    "references/skill-design-coverage.md": (
        "Coding Behavior Baseline language skill routing",
        "coding_behavior.language_skill_routing",
        "readable-script-generator",
    ),
    "references/evaluation-scenarios.md": (
        "language_skill_routing_contract",
        "readable-python-generator",
        "readable-script-generator",
    ),
}

SKILL_REQUIRED_SNIPPETS = (
    "root-level files outside the governed primary project root",
    "allow the conservative structure-fix attempt",
    "rerun `structure-gate`",
    "remote `create`, `move`, `delete`, or `rename` must keep both source and target paths inside the governed remote plan",
    "allowed_root_files",
    "remote_deployment.protected_path_classes",
)

SKILL_TOKEN_USAGE_SNIPPETS = (
    "如果用户明确要求进行 Codex Token 用量统计",
    "`python skills/agents-md-generator/scripts/python/detect/codex_token_usage_review.py --hours 48`",
    "不要进入 AGENTS 设计访谈",
    "当前环境可解析到 `$CODEX_HOME/sessions` 或 `~/.codex/sessions` 且目录存在时执行",
    "`--sessions-root` 只允许等于或位于当前 Codex sessions 根目录之下",
)

REQUIRED_SKILL_DESIGN_PATTERNS = {
    "Tool Wrapper",
    "Generator",
    "Reviewer",
    "Inversion",
    "Pipeline",
}

REQUIRED_EVAL_CASE_IDS = {
    "detect_missing_root_agents",
    "generator_version_takeover",
    "root_level_whitelist_gate",
    "root_workspace_artifact_gate",
    "evolution_removed_contract",
    "generic_audit_split",
    "evaluate_failure_classification",
    "install_release_completeness",
    "release_content_evals_install_contract",
    "review_governance_companion_checks",
    "design_review_gate",
    "source_governance_test_boundary",
    "source_governance_size_readability_contract",
    "language_skill_routing_contract",
    "codex_token_usage_review_contract",
    "task_rating_gate_contract",
    "memory_governance_gate",
    "governance_cli_entrypoint_smoke",
}

STALE_NUMBERED_SHARD_RE = re.compile(r"(?:^|[_./\\])part\d+\.py\b|eval_runtime_cases_part\d|_version_policy_part\d")

# 定义 parse_frontmatter 的技能审计处理入口。
def parse_frontmatter(text: str) -> dict[str, str]:

    # 校验 parse_frontmatter 的技能审计分支。
    if not text.startswith("---\n"):

        # 返回 parse_frontmatter 的技能审计载荷。
        return {}

    # 整理 parse_frontmatter 需要的 end 技能审计信息。
    end = text.find("\n---\n", 4)

    # 校验 parse_frontmatter 的技能审计分支。
    if end == -1:

        # 返回 parse_frontmatter 的技能审计载荷。
        return {}

    # 保存 data 映射，维持 parse_frontmatter 的字段关系。
    dict_data: dict[str, str] = {}

    # 整理 parse_frontmatter 需要的 current key 技能审计信息。
    current_key: str | None = None

    # 收集 current multiline 技能审计条目。
    list_current_multiline: list[str] = []

    # 逐项检查 parse_frontmatter 技能审计候选。
    for line in text[4:end].splitlines():

        # 校验 parse_frontmatter 的技能审计分支。
        if current_key is not None:

            # 校验 parse_frontmatter 的技能审计分支。
            if line.startswith((" ", "\t")):

                # 追加 parse_frontmatter 的技能审计诊断。
                list_current_multiline.append(line.strip())

                # 分隔 parse_frontmatter 的控制流边界。
                continue

            # 整理 parse_frontmatter 需要的 中间载荷 技能审计信息。
            dict_data[current_key] = " ".join(part for part in list_current_multiline if part).strip()

            # 整理 parse_frontmatter 需要的 current key 技能审计信息。
            current_key = None

            # 收集 current multiline 技能审计条目。
            list_current_multiline = []

        # 校验 parse_frontmatter 的技能审计分支。
        if ":" not in line:

            # 分隔 parse_frontmatter 的控制流边界。
            continue

        # 整理 parse_frontmatter 需要的 key、value 技能审计信息。
        key, raw_value = line.split(":", 1)

        # 整理 parse_frontmatter 需要的 normalized key 技能审计信息。
        normalized_key = key.strip()

        # 整理 parse_frontmatter 需要的 normalized value 技能审计信息。
        normalized_value = raw_value.strip().strip('"')

        # 校验 parse_frontmatter 的技能审计分支。
        if normalized_value in {">", ">-", "|", "|-"}:

            # 整理 parse_frontmatter 需要的 current key 技能审计信息。
            current_key = normalized_key

            # 收集 current multiline 技能审计条目。
            list_current_multiline = []

            # 分隔 parse_frontmatter 的控制流边界。
            continue

        # 整理 parse_frontmatter 需要的 中间载荷 技能审计信息。
        dict_data[normalized_key] = normalized_value

    # 校验 parse_frontmatter 的技能审计分支。
    if current_key is not None:

        # 整理 parse_frontmatter 需要的 中间载荷 技能审计信息。
        dict_data[current_key] = " ".join(part for part in list_current_multiline if part).strip()

    # 返回 parse_frontmatter 的技能审计载荷。
    return dict_data

# 定义 referenced_paths 的技能审计处理入口。
def referenced_paths(skill_text: str) -> set[str]:

    # 收集 paths 技能审计条目。
    set_paths: set[str] = set()

    # 逐项检查 referenced_paths 技能审计候选。
    for raw in re.findall(r"`([^`]+)`", skill_text):

        # 整理 referenced_paths 需要的 value 技能审计信息。
        raw_value = raw.strip()

        # 校验 referenced_paths 的技能审计分支。
        if "<" in raw_value or ">" in raw_value:

            # 分隔 referenced_paths 的控制流边界。
            continue

        # 校验 referenced_paths 的技能审计分支。
        if raw_value.startswith(("references/", "assets/", "scripts/", "agents/")):

            # 调用 add 处理 referenced_paths。
            set_paths.add(raw_value)

    # 返回 referenced_paths 的技能审计载荷。
    return set_paths

# 定义 contains_local_reference 的技能审计处理入口。
def contains_local_reference(text: str) -> bool:

    # 返回 contains_local_reference 的技能审计载荷。
    return bool(LOCAL_REFERENCE_RE.search(text))

# 定义 has_toc 的技能审计处理入口。
def has_toc(lines: list[str]) -> bool:

    # 返回 has_toc 的技能审计载荷。
    return any("table of contents" in line.lower() or "目录" in line for line in lines[:30])

# 定义 is_agents_md_generator_skill 的技能审计处理入口。
def is_agents_md_generator_skill(skill_dir: Path, frontmatter: dict[str, str] | None = None) -> bool:

    # 整理 is_agents_md_generator_skill 需要的 name 技能审计信息。
    name = (frontmatter or {}).get("name", "").strip()

    # 返回 is_agents_md_generator_skill 的技能审计载荷。
    return skill_dir.name == "agents-md-generator" or name == "agents-md-generator"

# 定义 skill_directory_name_matches 的技能审计处理入口。
def skill_directory_name_matches(skill_dir: Path, name: str) -> bool:
    """允许普通技能目录和已收据化发布目录两种命名契约。"""

    # 空名称交给调用方的 name 格式门禁处理。
    if not name:

        # 返回 skill_directory_name_matches 的技能审计载荷。
        return False

    # 普通安装目录必须与 frontmatter name 完全一致。
    if skill_dir.name == name:

        # 返回 skill_directory_name_matches 的技能审计载荷。
        return True

    # versioned release 目录采用 <name>-vX.Y.Z，必须由 VERSION 文件佐证。
    str_prefix = f"{name}-"
    if not skill_dir.name.startswith(str_prefix):

        # 返回 skill_directory_name_matches 的技能审计载荷。
        return False

    # 整理 skill_directory_name_matches 需要的 version suffix 技能审计信息。
    str_version_suffix = skill_dir.name[len(str_prefix):]

    # 校验 skill_directory_name_matches 的技能审计分支。
    if version_policy_error(str_version_suffix):

        # 返回 skill_directory_name_matches 的技能审计载荷。
        return False

    # 定位 version path 的文件边界，供 skill_directory_name_matches 后续读写校验使用。
    version_path = skill_dir / "VERSION"

    # 校验 skill_directory_name_matches 的技能审计分支。
    if not version_path.is_file():

        # 返回 skill_directory_name_matches 的技能审计载荷。
        return False

    # 整理 skill_directory_name_matches 需要的 declared version 技能审计信息。
    str_declared_version = version_path.read_text(encoding="utf-8", errors="ignore").strip()

    # 返回 skill_directory_name_matches 的技能审计载荷。
    return str_declared_version == str_version_suffix

# 定义 parse_openai_interface 的技能审计处理入口。
def parse_openai_interface(text: str) -> dict[str, str] | None:

    # 收集 lines 技能审计条目。
    lines = text.splitlines()

    # 保护 parse_openai_interface 中允许失败的外部访问。
    try:

        # 整理 parse_openai_interface 需要的 start 技能审计信息。
        start = next(index for index, line in enumerate(lines) if line.strip() == "interface:")
    except StopIteration:

        # 返回 parse_openai_interface 的技能审计载荷。
        return None

    # 保存 data 映射，维持 parse_openai_interface 的字段关系。
    dict_data: dict[str, str] = {}

    # 逐项检查 parse_openai_interface 技能审计候选。
    for line in lines[start + 1:]:

        # 校验 parse_openai_interface 的技能审计分支。
        if not line.strip():

            # 分隔 parse_openai_interface 的控制流边界。
            continue

        # 校验 parse_openai_interface 的技能审计分支。
        if not line.startswith((" ", "\t")):

            # 分隔 parse_openai_interface 的控制流边界。
            break

        # 整理 parse_openai_interface 需要的 stripped 技能审计信息。
        stripped = line.strip()

        # 校验 parse_openai_interface 的技能审计分支。
        if ":" not in stripped:

            # 分隔 parse_openai_interface 的控制流边界。
            continue

        # 整理 parse_openai_interface 需要的 key、value 技能审计信息。
        key, raw_value = stripped.split(":", 1)

        # 整理 parse_openai_interface 需要的 中间载荷 技能审计信息。
        dict_data[key.strip()] = raw_value.strip().strip('"').strip("'")

    # 返回 parse_openai_interface 的技能审计载荷。
    return dict_data

# 定义 parse_group_assignment 的技能审计处理入口。
def parse_group_assignment(script_text: str, name: str) -> list[list[str]] | None:

    # 整理 parse_group_assignment 需要的 match 技能审计信息。
    match = re.search(rf"^{name}\s*=\s*(.+)$", script_text, flags=re.MULTILINE)

    # 校验 parse_group_assignment 的技能审计分支。
    if not match:

        # 返回 parse_group_assignment 的技能审计载荷。
        return None

    # 保护 parse_group_assignment 中允许失败的外部访问。
    try:

        # 整理 parse_group_assignment 需要的 value 技能审计信息。
        raw_value = ast.literal_eval(match.group(1).strip())
    except (SyntaxError, ValueError):

        # 返回 parse_group_assignment 的技能审计载荷。
        return None

    # 校验 parse_group_assignment 的技能审计分支。
    if not isinstance(raw_value, list):

        # 返回 parse_group_assignment 的技能审计载荷。
        return None

    # 收集 groups 技能审计条目。
    list_groups: list[list[str]] = []

    # 逐项检查 parse_group_assignment 技能审计候选。
    for item in raw_value:

        # 校验 parse_group_assignment 的技能审计分支。
        if not isinstance(item, list):

            # 返回 parse_group_assignment 的技能审计载荷。
            return None

        # 追加 parse_group_assignment 的技能审计诊断。
        list_groups.append([str(part) for part in item])

    # 返回 parse_group_assignment 的技能审计载荷。
    return list_groups

# 定义 format_group_list 的技能审计处理入口。
def format_group_list(groups: list[list[str]]) -> str:

    # 返回 format_group_list 的技能审计载荷。
    return ", ".join(f"`[{','.join(group)}]`" for group in groups)

# 定义 validate_skill_contract_alignment 的技能审计处理入口。
def validate_skill_contract_alignment(skill_dir: Path, skill_text: str, errors: list[str]) -> None:

    # 定位 collect path 的文件边界，供 validate_skill_contract_alignment 后续读写校验使用。
    collect_path = skill_dir / "scripts" / "python" / "design" / "collect_design_profile.py"

    # 定位 questions path 的文件边界，供 validate_skill_contract_alignment 后续读写校验使用。
    questions_path = skill_dir / "scripts" / "python" / "design" / "design_questions.py"

    # 校验 validate_skill_contract_alignment 的技能审计分支。
    if not collect_path.exists() or not questions_path.exists():

        # 返回 validate_skill_contract_alignment 的技能审计载荷。
        return

    # 整理 validate_skill_contract_alignment 需要的 group text 技能审计信息。
    group_text = questions_path.read_text(encoding="utf-8", errors="ignore")

    # 收集 common groups 技能审计条目。
    common_groups = parse_group_assignment(group_text, "COMMON_GROUPS")

    # 收集 takeover common groups 技能审计条目。
    takeover_common_groups = parse_group_assignment(group_text, "TAKEOVER_COMMON_GROUPS")

    # 校验 validate_skill_contract_alignment 的技能审计分支。
    if not common_groups or not takeover_common_groups:

        # 追加 validate_skill_contract_alignment 的技能审计诊断。
        errors.append("scripts/python/design/design_questions.py: unable to parse COMMON_GROUPS and TAKEOVER_COMMON_GROUPS for audit alignment")

        # 返回 validate_skill_contract_alignment 的技能审计载荷。
        return

    # 校验 validate_skill_contract_alignment 的技能审计分支。
    if common_groups != takeover_common_groups:

        # 追加 validate_skill_contract_alignment 的技能审计诊断。
        errors.append("scripts/python/design/design_questions.py: COMMON_GROUPS and TAKEOVER_COMMON_GROUPS must stay aligned")

    # 整理 validate_skill_contract_alignment 需要的 formatted common 技能审计信息。
    str_formatted_common = format_group_list(common_groups)

    # 逐项检查 validate_skill_contract_alignment 技能审计候选。
    for label in COMMON_GROUP_LABELS:

        # 整理 validate_skill_contract_alignment 需要的 match 技能审计信息。
        match = re.search(rf"{re.escape(label)}\s+(.+?)\.", skill_text, flags=re.DOTALL)

        # 校验 validate_skill_contract_alignment 的技能审计分支。
        if match is None or str_formatted_common not in match.group(1):

            # 追加 validate_skill_contract_alignment 的技能审计诊断。
            errors.append("SKILL.md common question groups must match collect_design_profile.py")

            # 分隔 validate_skill_contract_alignment 的控制流边界。
            break

# 定义 validate_reference_alignment 的技能审计处理入口。
def validate_reference_alignment(skill_dir: Path, errors: list[str]) -> None:

    # 逐项检查 validate_reference_alignment 技能审计候选。
    for rel_path, snippets in REFERENCE_ALIGNMENT_RULES.items():

        # 整理 validate_reference_alignment 需要的 path 技能审计信息。
        path = skill_dir / rel_path

        # 校验 validate_reference_alignment 的技能审计分支。
        if not path.exists():

            # 分隔 validate_reference_alignment 的控制流边界。
            continue

        # 整理 validate_reference_alignment 需要的 text 技能审计信息。
        text = path.read_text(encoding="utf-8", errors="ignore")

        # 校验 validate_reference_alignment 的技能审计分支。
        if not all(snippet in text for snippet in snippets):

            # 追加 validate_reference_alignment 的技能审计诊断。
            errors.append(f"{rel_path}: missing aligned default-language and remote-server governance guidance")

    # 逐项检查 validate_reference_alignment 技能审计候选。
    for rel_path, snippets in LANGUAGE_SKILL_ROUTING_ALIGNMENT_RULES.items():

        # 整理 validate_reference_alignment 需要的 path 技能审计信息。
        path = skill_dir / rel_path

        # 校验 validate_reference_alignment 的技能审计分支。
        if not path.exists():

            # 分隔 validate_reference_alignment 的控制流边界。
            continue

        # 整理 validate_reference_alignment 需要的 text 技能审计信息。
        text = path.read_text(encoding="utf-8", errors="ignore")

        # 校验 validate_reference_alignment 的技能审计分支。
        if not all(snippet in text for snippet in snippets):

            # 追加 validate_reference_alignment 的技能审计诊断。
            errors.append(f"{rel_path}: missing language skill routing governance guidance")

# 定义 validate_skill_rule_hardening 的技能审计处理入口。
def validate_skill_rule_hardening(text: str, errors: list[str]) -> None:

    # 校验 validate_skill_rule_hardening 的技能审计分支。
    if not all(snippet in text for snippet in SKILL_REQUIRED_SNIPPETS):

        # 追加 validate_skill_rule_hardening 的技能审计诊断。
        errors.append("SKILL.md: missing local-root or remote-mutation hardening guidance")

    # 校验 validate_skill_rule_hardening 的技能审计分支。
    if not all(snippet in text for snippet in SKILL_TOKEN_USAGE_SNIPPETS):

        # 追加 validate_skill_rule_hardening 的技能审计诊断。
        errors.append("SKILL.md: missing explicit Codex token usage routing guidance")

# 定义 validate_openai_yaml 的技能审计处理入口。
def validate_openai_yaml(path: Path, errors: list[str], *, self_skill: bool) -> None:

    # 校验 validate_openai_yaml 的技能审计分支。
    if not self_skill:

        # 返回 validate_openai_yaml 的技能审计载荷。
        return

    # 校验 validate_openai_yaml 的技能审计分支。
    if not path.exists():

        # 返回 validate_openai_yaml 的技能审计载荷。
        return

    # 整理 validate_openai_yaml 需要的 text 技能审计信息。
    text = path.read_text(encoding="utf-8", errors="ignore")

    # 整理 validate_openai_yaml 需要的 interface 技能审计信息。
    interface = parse_openai_interface(text)

    # 校验 validate_openai_yaml 的技能审计分支。
    if interface is None:

        # 追加 validate_openai_yaml 的技能审计诊断。
        errors.append("agents/openai.yaml: missing interface section")

        # 返回 validate_openai_yaml 的技能审计载荷。
        return

    # 逐项检查 validate_openai_yaml 技能审计候选。
    for key in ("display_name", "short_description", "default_prompt"):

        # 整理 validate_openai_yaml 需要的 value 技能审计信息。
        raw_value = interface.get(key, "").strip()

        # 校验 validate_openai_yaml 的技能审计分支。
        if not raw_value:

            # 追加 validate_openai_yaml 的技能审计诊断。
            errors.append(f"agents/openai.yaml: missing interface.{key}")

        # 校验 validate_openai_yaml 的技能审计分支。
        elif raw_value.lower() in {"todo", "tbd", "placeholder"}:

            # 追加 validate_openai_yaml 的技能审计诊断。
            errors.append(f"agents/openai.yaml: interface.{key} is a placeholder")

    # 整理 validate_openai_yaml 需要的 default prompt 技能审计信息。
    default_prompt = interface.get("default_prompt", "")

    # 校验 validate_openai_yaml 的技能审计分支。
    if default_prompt and "$agents-md-generator" not in default_prompt:

        # 追加 validate_openai_yaml 的技能审计诊断。
        errors.append("agents/openai.yaml: default_prompt must mention $agents-md-generator")

    # 整理 validate_openai_yaml 需要的 normalized prompt 技能审计信息。
    normalized_prompt = default_prompt.lower()

    # 逐项检查 validate_openai_yaml 技能审计候选。
    for snippet in OPENAI_REQUIRED_PROMPT_SNIPPETS:

        # 校验 validate_openai_yaml 的技能审计分支。
        if default_prompt and snippet.lower() not in normalized_prompt:

            # 追加 validate_openai_yaml 的技能审计诊断。
            errors.append("agents/openai.yaml: default_prompt must keep explicit default-language and remote task-routing rules")

            # 分隔 validate_openai_yaml 的控制流边界。
            break

    # 逐项检查 validate_openai_yaml 技能审计候选。
    for snippet in OPENAI_TOKEN_USAGE_PROMPT_SNIPPETS:

        # 校验 validate_openai_yaml 的技能审计分支。
        if default_prompt and snippet.lower() not in normalized_prompt:

            # 追加 validate_openai_yaml 的技能审计诊断。
            errors.append("agents/openai.yaml: default_prompt must document explicit Codex token usage routing")

            # 分隔 validate_openai_yaml 的控制流边界。
            break

    # 校验 validate_openai_yaml 的技能审计分支。
    if default_prompt and TAKEOVER_REMOTE_PROMPT_RULE.lower() not in normalized_prompt:

        # 追加 validate_openai_yaml 的技能审计诊断。
        errors.append("agents/openai.yaml: takeover prompt must separate remote structure governance from remote server enablement and task-route mapping")

# 定义 validate_global_baseline_template 的技能审计处理入口。
def validate_global_baseline_template(path: Path, errors: list[str]) -> None:

    # 校验 validate_global_baseline_template 的技能审计分支。
    if not path.exists():

        # 返回 validate_global_baseline_template 的技能审计载荷。
        return

    # 整理 validate_global_baseline_template 需要的 text 技能审计信息。
    text = path.read_text(encoding="utf-8", errors="ignore")

    # 收集 required snippets 技能审计条目。
    tuple_required_snippets = (
        "AGENTS-GENERATED:META generator=agents-md-generator schema=1 baseline=global-codex-baseline baseline_version=3",
        "## Instruction Scope",
        "## Managed Repository Entry",
        "## Execution Mode",
        "Prefer existing repository patterns, tools, libraries, templates",
        "non-trivial enough for rating to affect execution mode",
        "advisory",
        "timed follow-up",
        "must not compress code into one line",
        "clever or obfuscated code",
        "repository governance",
        "Coding Behavior Baseline",
        "Guidelines for avoiding common LLM coding mistakes",
        "### 1. Think Before Coding",
        "Minimum code that solves the problem. Nothing speculative.",
        "### 3. Surgical Changes",
        "### 4. Work Toward Verifiable Goals",
        "fabricating test cases, outputs, or verification evidence",
        "### Done When",
        "Every changed line must trace directly to the request",
        "## Comments And Documentation",
        "Comment public contracts",
        "key invariants, non-obvious decisions, generation boundaries, and risk boundaries",
        "Do not restate obvious code",
        "Update stale comments and documentation when behavior changes",
        "readable-python-generator",
        "readable-script-generator",
        "Markdown documentation formulas",
        "## Environment And Dependency Safety",
        "isolated project environment",
        "create an isolated environment under the remote workspace",
        "Never install into system Python",
        "conda `base`",
        "sudo pip",
        "pip install --user",
        "installed skill directories",
        "$CODEX_HOME/skills",
        "explicitly requests installation, replacement, or direct modification",
    )

    # 逐项检查 validate_global_baseline_template 技能审计候选。
    for snippet in tuple_required_snippets:

        # 校验 validate_global_baseline_template 的技能审计分支。
        if snippet not in text:

            # 追加 validate_global_baseline_template 的技能审计诊断。
            errors.append(f"assets/templates/global-codex-agents.md: missing global baseline rule snippet `{snippet}`")

    # 收集 forbidden snippets 技能审计条目。
    tuple_forbidden_snippets = (
        ".agents/script-governance-exceptions.json",
        "docs/development/decomposition-plans",
        "skills/agents-md-generator",
        "64KB UTF-8 size limit",
        "scripts/python/<function>/<name>.py",
        "scripts/shell/<function>/<name>.sh",
        "scripts/bat/<function>/<name>.bat",
        "scripts/powershell/<function>/<name>.ps1",
        "do not put formulas in fenced code blocks",
    )

    # 逐项检查 validate_global_baseline_template 技能审计候选。
    for snippet in tuple_forbidden_snippets:

        # 校验 validate_global_baseline_template 的技能审计分支。
        if snippet in text:

            # 追加 validate_global_baseline_template 的技能审计诊断。
            errors.append(f"assets/templates/global-codex-agents.md: must not leak repository-specific detail `{snippet}`")

# 定义 validate_evals_contract 的技能审计处理入口。
def validate_evals_contract(path: Path, errors: list[str], *, self_skill: bool) -> None:

    # 校验 validate_evals_contract 的技能审计分支。
    if not self_skill or not path.exists():

        # 返回 validate_evals_contract 的技能审计载荷。
        return

    # 保护 validate_evals_contract 中允许失败的外部访问。
    try:

        # 整理 validate_evals_contract 需要的 data 技能审计信息。
        dict_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:

        # 追加 validate_evals_contract 的技能审计诊断。
        errors.append(f"evals/evals.json: invalid JSON: {exc.msg}")

        # 返回 validate_evals_contract 的技能审计载荷。
        return

    # 校验 validate_evals_contract 的技能审计分支。
    if not isinstance(dict_data, dict):

        # 追加 validate_evals_contract 的技能审计诊断。
        errors.append("evals/evals.json: root must be a JSON object")

        # 返回 validate_evals_contract 的技能审计载荷。
        return

    # 收集 cases 技能审计条目。
    cases = dict_data.get("cases")

    # 校验 validate_evals_contract 的技能审计分支。
    if not isinstance(cases, list) or not cases:

        # 追加 validate_evals_contract 的技能审计诊断。
        errors.append("evals/evals.json: cases must be a non-empty list")

        # 返回 validate_evals_contract 的技能审计载荷。
        return

    # 收集 ids 技能审计条目。
    set_ids: set[str] = set()

    # 收集 duplicate ids 技能审计条目。
    set_duplicate_ids: set[str] = set()

    # 收集 covered patterns 技能审计条目。
    set_covered_patterns: set[str] = set()

    # 逐项检查 validate_evals_contract 技能审计候选。
    for index, case in enumerate(cases):

        # 校验 validate_evals_contract 的技能审计分支。
        if not isinstance(case, dict):

            # 追加 validate_evals_contract 的技能审计诊断。
            errors.append(f"evals/evals.json: case {index} must be an object")

            # 分隔 validate_evals_contract 的控制流边界。
            continue

        # 整理 validate_evals_contract 需要的 case id 技能审计信息。
        case_id = str(case.get("id", "")).strip()

        # 校验 validate_evals_contract 的技能审计分支。
        if not case_id:

            # 追加 validate_evals_contract 的技能审计诊断。
            errors.append(f"evals/evals.json: case {index} is missing id")

        # 校验 validate_evals_contract 的技能审计分支。
        elif case_id in set_ids:

            # 调用 add 处理 validate_evals_contract。
            set_duplicate_ids.add(case_id)
        else:

            # 调用 add 处理 validate_evals_contract。
            set_ids.add(case_id)

        # 逐项检查 validate_evals_contract 技能审计候选。
        for key in ("kind", "handler", "description"):

            # 校验 validate_evals_contract 的技能审计分支。
            if not str(case.get(key, "")).strip():

                # 追加 validate_evals_contract 的技能审计诊断。
                errors.append(f"evals/evals.json: case {case_id or index} is missing {key}")

        # 收集 patterns 技能审计条目。
        patterns = case.get("patterns")

        # 校验 validate_evals_contract 的技能审计分支。
        if not isinstance(patterns, list) or not patterns:

            # 追加 validate_evals_contract 的技能审计诊断。
            errors.append(f"evals/evals.json: case {case_id or index} must list Skill design patterns")

            # 分隔 validate_evals_contract 的控制流边界。
            continue

        # 收集 normalized patterns 技能审计条目。
        normalized_patterns = {str(pattern).strip() for pattern in patterns if str(pattern).strip()}

        # 校验 validate_evals_contract 的技能审计分支。
        if not normalized_patterns:

            # 追加 validate_evals_contract 的技能审计诊断。
            errors.append(f"evals/evals.json: case {case_id or index} must list Skill design patterns")

            # 分隔 validate_evals_contract 的控制流边界。
            continue

        # 收集 unknown patterns 技能审计条目。
        unknown_patterns = sorted(normalized_patterns - REQUIRED_SKILL_DESIGN_PATTERNS)

        # 校验 validate_evals_contract 的技能审计分支。
        if unknown_patterns:

            # 追加 validate_evals_contract 的技能审计诊断。
            errors.append(f"evals/evals.json: case {case_id or index} uses unknown Skill design patterns {unknown_patterns}")

        # 调用 update 处理 validate_evals_contract。
        set_covered_patterns.update(normalized_patterns & REQUIRED_SKILL_DESIGN_PATTERNS)

    # 校验 validate_evals_contract 的技能审计分支。
    if set_duplicate_ids:

        # 追加 validate_evals_contract 的技能审计诊断。
        errors.append(f"evals/evals.json: duplicate case ids {sorted(duplicate_ids)}")

    # 收集 missing cases 技能审计条目。
    missing_cases = sorted(REQUIRED_EVAL_CASE_IDS - set_ids)

    # 校验 validate_evals_contract 的技能审计分支。
    if missing_cases:

        # 追加 validate_evals_contract 的技能审计诊断。
        errors.append(f"evals/evals.json: missing required effectiveness cases {missing_cases}")

    # 收集 missing patterns 技能审计条目。
    missing_patterns = sorted(REQUIRED_SKILL_DESIGN_PATTERNS - set_covered_patterns)

    # 校验 validate_evals_contract 的技能审计分支。
    if missing_patterns:

        # 追加 validate_evals_contract 的技能审计诊断。
        errors.append(f"evals/evals.json: missing required Skill design pattern coverage {missing_patterns}")

# 定义 validate_script_output_default_config 的技能审计处理入口。
def validate_script_output_default_config(path: Path, errors: list[str]) -> None:

    # 校验 validate_script_output_default_config 的技能审计分支。
    if not path.is_file():

        # 返回 validate_script_output_default_config 的技能审计载荷。
        return

    # 保护 validate_script_output_default_config 中允许失败的外部访问。
    try:

        # 整理 validate_script_output_default_config 需要的 data 技能审计信息。
        dict_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:

        # 追加 validate_script_output_default_config 的技能审计诊断。
        errors.append(f"config/script-output-policy-default.json: invalid JSON: {exc.msg}")

        # 返回 validate_script_output_default_config 的技能审计载荷。
        return

    # 校验 validate_script_output_default_config 的技能审计分支。
    if not isinstance(dict_data, dict):

        # 追加 validate_script_output_default_config 的技能审计诊断。
        errors.append("config/script-output-policy-default.json: root must be a JSON object")

        # 返回 validate_script_output_default_config 的技能审计载荷。
        return

    # 逐项检查 validate_script_output_default_config 技能审计候选。
    for item in validate_script_output_policy_data(dict_data, require_explicit=True):

        # 追加 validate_script_output_default_config 的技能审计诊断。
        errors.append(f"config/script-output-policy-default.json: {item}")

# 定义 validate_runtime_shard_references 的技能审计处理入口。
def validate_runtime_shard_references(skill_dir: Path, errors: list[str]) -> None:
    """阻止运行时入口继续引用 numbered shard 名称。"""

    # 定位 scripts python root 的文件边界，供 validate_runtime_shard_references 后续读写校验使用。
    scripts_python_root = skill_dir / "scripts" / "python"

    # 校验 validate_runtime_shard_references 的技能审计分支。
    if not scripts_python_root.is_dir():

        # 返回 validate_runtime_shard_references 的技能审计载荷。
        return

    # 逐项检查 validate_runtime_shard_references 技能审计候选。
    for path in sorted(scripts_python_root.rglob("*.py")):

        # 定位 rel path 的文件边界，供 validate_runtime_shard_references 后续读写校验使用。
        rel_path = path.relative_to(skill_dir).as_posix()

        # 整理 validate_runtime_shard_references 需要的 text 技能审计信息。
        text = path.read_text(encoding="utf-8", errors="ignore")

        # 校验 validate_runtime_shard_references 的技能审计分支。
        if STALE_NUMBERED_SHARD_RE.search(text):

            # 追加 validate_runtime_shard_references 的技能审计诊断。
            errors.append(f"{rel_path}: stale numbered shard reference")

# 定义 skill_project_root 的技能审计处理入口。
def skill_project_root(skill_dir: Path) -> Path:

    # 校验 skill_project_root 的技能审计分支。
    if skill_dir.parent.name == "skills":

        # 返回 skill_project_root 的技能审计载荷。
        return skill_dir.parents[1]

    # 返回 skill_project_root 的技能审计载荷。
    return skill_dir

# 定义 has_repo_governance 的技能审计处理入口。
def has_repo_governance(project_root: Path) -> bool:

    # 返回 has_repo_governance 的技能审计载荷。
    return (project_root / ".agents" / "global-rule-overrides.json").is_file()

# 定义 validate_decomposition_plan 的技能审计处理入口。
def validate_decomposition_plan(project_root: Path, relative_path: str) -> list[str]:

    # 定位 plan path 的文件边界，供 validate_decomposition_plan 后续读写校验使用。
    plan_path = decomposition_plan_path(project_root, relative_path)

    # 校验 validate_decomposition_plan 的技能审计分支。
    if not plan_path.is_file():

        # 返回 validate_decomposition_plan 的技能审计载荷。
        return [f"{relative_path} exceeds configured size limit and requires decomposition plan `{plan_path.relative_to(project_root).as_posix()}`"]

    # 整理 validate_decomposition_plan 需要的 text 技能审计信息。
    text = plan_path.read_text(encoding="utf-8", errors="ignore")

    # 收集 required sections 技能审计条目。
    required_sections = load_global_rule_overrides(project_root)["data"]["source_file_limits"].get("required_plan_sections", [])

    # 整理 validate_decomposition_plan 需要的 missing 技能审计信息。
    missing = [section for section in required_sections if f"## {section}" not in text]  # 缺失分解计划章节

    # 校验 validate_decomposition_plan 的技能审计分支。
    if missing:

        # 返回 validate_decomposition_plan 的技能审计载荷。
        return [f"{plan_path.relative_to(project_root).as_posix()}: missing decomposition plan sections {missing}"]

    # 返回 validate_decomposition_plan 的技能审计载荷。
    return []

# 定义 audit 的技能审计处理入口。
def audit(skill_dir: Path) -> dict:

    # 收集 errors 技能审计条目。
    list_errors: list[str] = []

    # 收集 warnings 技能审计条目。
    list_warnings: list[str] = []

    # 收集 checked 技能审计条目。
    list_checked: list[str] = []

    # 定位 project root 的文件边界，供 audit 后续读写校验使用。
    path_project_root = skill_project_root(skill_dir)

    # 定位 skill path 的文件边界，供 audit 后续读写校验使用。
    skill_path = skill_dir / "SKILL.md"

    # 整理 audit 需要的 frontmatter 技能审计信息。
    frontmatter = parse_frontmatter(skill_path.read_text(encoding="utf-8", errors="ignore")) if skill_path.exists() else {}

    # 标记 self skill 判断，控制 audit 的分支走向。
    bool_self_skill = is_agents_md_generator_skill(skill_dir, frontmatter)

    # 收集 required files 技能审计条目。
    required_files = CORE_REQUIRED_FILES + (SELF_REQUIRED_FILES if bool_self_skill else [])

    # 逐项检查 audit 技能审计候选。
    for rel_path in required_files:

        # 整理 audit 需要的 path 技能审计信息。
        path = skill_dir / rel_path

        # 追加 audit 的技能审计诊断。
        list_checked.append(rel_path)

        # 校验 audit 的技能审计分支。
        if not path.exists():

            # 追加 audit 的技能审计诊断。
            list_errors.append(f"missing required file: {rel_path}")

    # 校验 audit 的技能审计分支。
    if bool_self_skill:

        # 逐项检查 audit 技能审计候选。
        for name in SELF_DISALLOWED_ROOT_DOCS:

            # 校验 audit 的技能审计分支。
            if (skill_dir / name).exists():

                # 追加 audit 的技能审计诊断。
                list_errors.append(f"disallowed extra root documentation file: {name}")

    # 校验 audit 的技能审计分支。
    if bool_self_skill and (skill_dir / "AGENTS.md").exists():

        # 追加 audit 的技能审计诊断。
        list_errors.append("disallowed skill root AGENTS.md")

    # 校验 audit 的技能审计分支。
    if skill_path.exists():

        # 整理 audit 需要的 text 技能审计信息。
        text = skill_path.read_text(encoding="utf-8", errors="ignore")

        # 整理 audit 需要的 fm 技能审计信息。
        fm = frontmatter

        # 校验 audit 的技能审计分支。
        if set(fm) != {"name", "description"}:

            # 追加 audit 的技能审计诊断。
            list_errors.append("SKILL.md frontmatter must contain only name and description")

        # 整理 audit 需要的 name 技能审计信息。
        name = fm.get("name", "")

        # 校验 audit 的技能审计分支。
        if not SKILL_NAME_RE.fullmatch(name):

            # 追加 audit 的技能审计诊断。
            list_errors.append("SKILL.md name must match [a-z0-9-]+")

        # 校验 audit 的技能审计分支。
        if name and not skill_directory_name_matches(skill_dir, name):

            # 追加 audit 的技能审计诊断。
            list_errors.append("SKILL.md name must match the skill directory name")

        # 整理 audit 需要的 description 技能审计信息。
        description = fm.get("description", "")

        # 校验 audit 的技能审计分支。
        if not description.startswith("Use when"):

            # 追加 audit 的技能审计诊断。
            list_errors.append("SKILL.md description must start with 'Use when'")

        # 校验 audit 的技能审计分支。
        if len(description) > 1024:

            # 追加 audit 的技能审计诊断。
            list_errors.append("SKILL.md description must be 1024 characters or fewer")

        # 校验 audit 的技能审计分支。
        if len(text.splitlines()) > 500:

            # 追加 audit 的技能审计诊断。
            list_errors.append("SKILL.md must stay under 500 lines")

        # 逐项检查 audit 技能审计候选。
        for rel_path in referenced_paths(text):

            # 追加 audit 的技能审计诊断。
            list_checked.append(rel_path)

            # 校验 audit 的技能审计分支。
            if not (skill_dir / rel_path).exists():

                # 追加 audit 的技能审计诊断。
                list_errors.append(f"SKILL.md references missing resource: {rel_path}")

        # 校验 audit 的技能审计分支。
        if contains_local_reference(text):

            # 追加 audit 的技能审计诊断。
            list_errors.append("SKILL.md must not depend on local reference folders")

        # 校验 audit 的技能审计分支。
        if bool_self_skill:

            # 调用 validate_skill_contract_alignment 处理 audit。
            validate_skill_contract_alignment(skill_dir, text, list_errors)

            # 调用 validate_skill_rule_hardening 处理 audit。
            validate_skill_rule_hardening(text, list_errors)

    version_path = skill_dir / "VERSION"

    if bool_self_skill and version_path.exists():

        version_text = version_path.read_text(encoding="utf-8", errors="ignore").strip()

        if not re.fullmatch(r"v\d+\.\d+\.\d+", version_text):

            list_errors.append("VERSION must use semantic format vX.Y.Z")

        str_version_error = version_policy_error(version_text)
        if str_version_error:
            list_errors.append(str_version_error)

    # 调用 validate_openai_yaml 处理 audit。
    validate_openai_yaml(skill_dir / "agents" / "openai.yaml", list_errors, self_skill=bool_self_skill)

    # 校验 audit 的技能审计分支。
    if bool_self_skill:

        # 调用 validate_reference_alignment 处理 audit。
        validate_reference_alignment(skill_dir, list_errors)

        # 调用 validate_global_baseline_template 处理 audit。
        validate_global_baseline_template(skill_dir / "assets" / "templates" / "global-codex-agents.md", list_errors)

        # 调用 validate_evals_contract 处理 audit。
        validate_evals_contract(skill_dir / "evals" / "evals.json", list_errors, self_skill=bool_self_skill)

        # 调用 validate_script_output_default_config 处理 audit。
        validate_script_output_default_config(skill_dir / "config" / "script-output-policy-default.json", list_errors)

        # 调用 validate_runtime_shard_references 处理 audit。
        validate_runtime_shard_references(skill_dir, list_errors)

    scripts_root = skill_dir / "scripts"
    scripts_python_root = scripts_root / "python"

    # 检查 agents-md-generator 自身的任务分类运行时契约。
    if bool_self_skill:

        # 逐项检查 audit 技能审计候选。
        for script in sorted(scripts_root.glob("*.py")):

            # 追加 audit 的技能审计诊断。
            list_errors.append(f"{script.relative_to(skill_dir).as_posix()} is a removed legacy top-level script entry")

        # 逐项检查 audit 技能审计候选。
        for script_name, task_name in sorted(SCRIPT_TASK_BY_NAME.items()):

            # 整理 expected script 需要的技能审计信息。
            expected_script = scripts_python_root / task_name / script_name

            # 校验 audit 的技能审计分支。
            if not expected_script.is_file():

                # 追加 audit 的技能审计诊断。
                list_errors.append(f"missing task-classified script: scripts/python/{task_name}/{script_name}")

        # 收集 scripts to check 条目，保持 audit 的处理顺序稳定。
        list_scripts_to_check = sorted(scripts_python_root.rglob("*.py"))
    else:

        # 收集 scripts to check 条目，保持 audit 的处理顺序稳定。
        list_scripts_to_check = sorted(scripts_root.rglob("*.py"))

    # 逐项检查 audit 技能审计候选。
    for script in list_scripts_to_check:

        # 定位 rel path 的文件边界，供 audit 后续读写校验使用。
        rel_path = script.relative_to(skill_dir).as_posix()

        # 校验 audit 的技能审计分支。
        if rel_path not in list_checked:

            # 追加 audit 的技能审计诊断。
            list_checked.append(rel_path)

        # 保护 audit 中允许失败的外部访问。
        try:

            # 整理 audit 需要的 source 技能审计信息。
            source = script.read_text(encoding="utf-8", errors="ignore")

            # 调用 compile 处理 audit。
            compile(source, str(script), "exec")
        except SyntaxError as exc:

            # 追加 audit 的技能审计诊断。
            list_errors.append(f"{rel_path} does not compile: {exc.msg}")

        # 整理 audit 需要的 byte count 技能审计信息。
        byte_count = len(source.encode("utf-8"))

        # 校验 audit 的技能审计分支。
        if byte_count > 65536 and has_repo_governance(path_project_root):

            # 整理 audit 需要的 relative to project 技能审计信息。
            relative_to_project = script.relative_to(path_project_root).as_posix() if script.is_relative_to(path_project_root) else rel_path

            # 调用 extend 处理 audit。
            list_errors.extend(validate_decomposition_plan(path_project_root, relative_to_project))

    # 逐项检查 audit 技能审计候选。
    for path in skill_dir.rglob("*"):

        # 定位 rel path 的文件边界，供 audit 后续读写校验使用。
        rel_path = path.relative_to(skill_dir).as_posix()

        # 收集 rel parts 技能审计条目。
        rel_parts = path.relative_to(skill_dir).parts

        # 校验 audit 的技能审计分支。
        if ".git" in rel_parts:

            # 分隔 audit 的控制流边界。
            continue

        # 校验 audit 的技能审计分支。
        if "__pycache__" in rel_parts or path.suffix in DISALLOWED_CACHE_SUFFIXES:

            # 追加 audit 的技能审计诊断。
            list_errors.append(f"disallowed generated cache artifact: {rel_path}")

            # 分隔 audit 的控制流边界。
            continue

        # 校验 audit 的技能审计分支。
        if not path.is_file():

            # 分隔 audit 的控制流边界。
            continue

        # 校验 audit 的技能审计分支。
        if path.suffix in {".md", ".yaml", ".yml", ".py"}:

            # 整理 audit 需要的 text 技能审计信息。
            text = path.read_text(encoding="utf-8", errors="ignore")

            # 校验 audit 的技能审计分支。
            if rel_parts and rel_parts[0] == "references" and path.suffix == ".md":

                # 收集 lines 技能审计条目。
                lines = text.splitlines()

                # 校验 audit 的技能审计分支。
                if len(lines) > 100 and not has_toc(lines):

                    # 追加 audit 的技能审计诊断。
                    list_errors.append(f"{rel_path}: reference files over 100 lines need a table of contents")

            # 校验 audit 的技能审计分支。
            if "{{" in text and (rel_path == "SKILL.md" or rel_path.startswith("agents/")):

                # 追加 audit 的技能审计诊断。
                list_warnings.append(f"{rel_path}: contains template placeholder syntax outside templates")

            # 校验 audit 的技能审计分支。
            if rel_path.startswith("assets/templates/"):

                # 整理 audit 需要的 template name 技能审计信息。
                template_name = path.name

                # 整理 audit 需要的 known 技能审计信息。
                known = KNOWN_TEMPLATE_PLACEHOLDERS.get(template_name, set())

                # 逐项检查 audit 技能审计候选。
                for placeholder in sorted(set(TEMPLATE_PLACEHOLDER_RE.findall(text)) - known):

                    # 追加 audit 的技能审计诊断。
                    list_errors.append(f"{template_name}: contains unknown template placeholder: {placeholder}")

            # 校验 audit 的技能审计分支。
            if contains_local_reference(text):

                # 追加 audit 的技能审计诊断。
                list_errors.append(f"{rel_path}: references local-only development material")

    # 返回 audit 的技能审计载荷。
    return {
        "skill_dir": str(skill_dir),
        "checked": sorted(set(list_checked)),
        "errors": list_errors,
        "warnings": list_warnings,
    }

# 定义 main 的技能审计处理入口。
def main() -> None:

    # 整理 main 需要的 parser 技能审计信息。
    parser = argparse.ArgumentParser(description="Audit agents-md-generator skill structure and scripts.")

    # 调用 add_argument 处理 main。
    parser.add_argument("skill_dir", nargs="?", default=".")

    # 收集 args 技能审计条目。
    args = parser.parse_args()

    # 调用 emit_json 处理 main。
    emit_json(audit(resolve_project(args.skill_dir)))

# 校验 模块入口 的技能审计分支。
if __name__ == "__main__":

    # 调用 main 处理 模块入口。
    main()


