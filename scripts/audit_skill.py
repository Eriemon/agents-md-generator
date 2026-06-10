from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, resolve_project
from agents_project_facts import decomposition_plan_path, load_global_rule_overrides
from source_governance_config import validate_script_output_policy_data


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
    "references/code-comment-policy.md",
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
    "scripts/check_source_governance.py",
    "scripts/codex_token_usage_review.py",
    "scripts/inspect_project.py",
    "scripts/collect_design_profile.py",
    "scripts/design_review_gate.py",
    "scripts/extract_commands.py",
    "scripts/extract_context.py",
    "scripts/detect_scopes.py",
    "scripts/render_agents.py",
    "scripts/manage_docs.py",
    "scripts/manage_dirs.py",
    "scripts/manage_dirs_review.py",
    "scripts/manage_dirs_state.py",
    "scripts/agents_decisions.py",
    "scripts/install_skill.py",
    "scripts/review_governance.py",
    "scripts/select_engineering_rules.py",
    "scripts/verify_agents.py",
    "scripts/check_freshness.py",
    "scripts/quick_validate.py",
    "scripts/run_confidence_gate.py",
    "scripts/source_governance.py",
    "scripts/source_governance_config.py",
    "scripts/create_agent_shims.py",
    "scripts/audit_skill.py",
    "scripts/evaluate_skill.py",
]

SELF_DISALLOWED_ROOT_DOCS = {"README.md", "CHANGELOG.md", "INSTALL.md", "INSTALLATION.md"}
DISALLOWED_CACHE_SUFFIXES = {".pyc", ".pyo"}
LOCAL_REFERENCE_RE = re.compile(
    r"G:[/\\]html|ref[/\\](agent-rules|html)|\b[A-Za-z]:[/\\][^\s`'\"<>)]*",
    flags=re.IGNORECASE,
)
SKILL_NAME_RE = re.compile(r"^[a-z0-9-]+$")
TEMPLATE_PLACEHOLDER_RE = re.compile(r"{{([A-Z0-9_]+)}}")
KNOWN_TEMPLATE_PLACEHOLDERS = {
    "root-agents.md": {
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
        "CODE_COMMENT_POLICY",
        "SCRIPT_OUTPUT_POLICY",
        "EXPERIENCE_LOG_CONTRACT",
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
    "future remote server validation must start with the matched task route primary server",
    "automatically try registered fallback servers",
    "stop for unmatched tasks until AGENTS.md is updated",
    "Code Comment Policy",
    "code_comment_policy",
    "禁止未经明确要求的批量 AI 注释",
    "Python/C/C++/Verilog",
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
        "unmatched remote tasks must update AGENTS.md",
        "root-level file whitelist",
        "confirm-structure-fix",
        "source and target paths must both stay inside the governed remote plan",
        "1000",
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
        "update AGENTS.md before validation continues",
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
CODE_COMMENT_ALIGNMENT_RULES = {
    "references/code-comment-policy.md": (
        "Python",
        "C/C++",
        "Verilog/SystemVerilog",
        "Good",
        "Bad",
        "不能把语句、注释、函数粘连到一起",
    ),
    "references/review-checklist.md": (
        "Generated root `AGENTS.md` must include `## Code Comment Policy`",
        ".agents/global-rule-overrides.json",
        "Python/C/C++/Verilog",
        "配置化注释策略",
    ),
    "references/script-guide.md": (
        "`render_agents.py` emits `## Code Comment Policy`",
        "code_comment_policy",
        "`verify_agents.py` rejects managed root `AGENTS.md` files that omit or weaken the code-comment policy",
    ),
    "references/skill-design-coverage.md": (
        "Code Comment Policy",
        "code_comment_policy",
        "Python/C/C++/Verilog",
    ),
    "references/evaluation-scenarios.md": (
        "code_comment_policy_contract",
        "禁止未经明确要求的批量 AI 注释",
        "弱化策略",
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
    "`python skills/agents-md-generator/scripts/codex_token_usage_review.py --hours 48`",
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
    "code_comment_policy_contract",
    "codex_token_usage_review_contract",
    "task_rating_gate_contract",
    "memory_governance_gate",
}


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}
    data: dict[str, str] = {}
    current_key: str | None = None
    current_multiline: list[str] = []
    for line in text[4:end].splitlines():
        if current_key is not None:
            if line.startswith((" ", "\t")):
                current_multiline.append(line.strip())
                continue
            data[current_key] = " ".join(part for part in current_multiline if part).strip()
            current_key = None
            current_multiline = []
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip()
        normalized_value = value.strip().strip('"')
        if normalized_value in {">", ">-", "|", "|-"}:
            current_key = normalized_key
            current_multiline = []
            continue
        data[normalized_key] = normalized_value
    if current_key is not None:
        data[current_key] = " ".join(part for part in current_multiline if part).strip()
    return data


def referenced_paths(skill_text: str) -> set[str]:
    paths: set[str] = set()
    for raw in re.findall(r"`([^`]+)`", skill_text):
        value = raw.strip()
        if "<" in value or ">" in value:
            continue
        if value.startswith(("references/", "assets/", "scripts/", "agents/")):
            paths.add(value)
    return paths


def contains_local_reference(text: str) -> bool:
    return bool(LOCAL_REFERENCE_RE.search(text))


def has_toc(lines: list[str]) -> bool:
    return any("table of contents" in line.lower() or "目录" in line for line in lines[:30])


def is_agents_md_generator_skill(skill_dir: Path, frontmatter: dict[str, str] | None = None) -> bool:
    name = (frontmatter or {}).get("name", "").strip()
    return skill_dir.name == "agents-md-generator" or name == "agents-md-generator"


def parse_openai_interface(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == "interface:")
    except StopIteration:
        return None
    data: dict[str, str] = {}
    for line in lines[start + 1:]:
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            break
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def parse_group_assignment(script_text: str, name: str) -> list[list[str]] | None:
    match = re.search(rf"^{name}\s*=\s*(.+)$", script_text, flags=re.MULTILINE)
    if not match:
        return None
    try:
        value = ast.literal_eval(match.group(1).strip())
    except (SyntaxError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    groups: list[list[str]] = []
    for item in value:
        if not isinstance(item, list):
            return None
        groups.append([str(part) for part in item])
    return groups


def format_group_list(groups: list[list[str]]) -> str:
    return ", ".join(f"`[{','.join(group)}]`" for group in groups)


def validate_skill_contract_alignment(skill_dir: Path, skill_text: str, errors: list[str]) -> None:
    collect_path = skill_dir / "scripts" / "collect_design_profile.py"
    questions_path = skill_dir / "scripts" / "design_questions.py"
    if not collect_path.exists() or not questions_path.exists():
        return
    group_text = questions_path.read_text(encoding="utf-8", errors="ignore")
    common_groups = parse_group_assignment(group_text, "COMMON_GROUPS")
    takeover_common_groups = parse_group_assignment(group_text, "TAKEOVER_COMMON_GROUPS")
    if not common_groups or not takeover_common_groups:
        errors.append("scripts/design_questions.py: unable to parse COMMON_GROUPS and TAKEOVER_COMMON_GROUPS for audit alignment")
        return
    if common_groups != takeover_common_groups:
        errors.append("scripts/design_questions.py: COMMON_GROUPS and TAKEOVER_COMMON_GROUPS must stay aligned")
    formatted_common = format_group_list(common_groups)
    for label in COMMON_GROUP_LABELS:
        match = re.search(rf"{re.escape(label)}\s+(.+?)\.", skill_text, flags=re.DOTALL)
        if match is None or formatted_common not in match.group(1):
            errors.append("SKILL.md common question groups must match collect_design_profile.py")
            break


def validate_reference_alignment(skill_dir: Path, errors: list[str]) -> None:
    for rel_path, snippets in REFERENCE_ALIGNMENT_RULES.items():
        path = skill_dir / rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not all(snippet in text for snippet in snippets):
            errors.append(f"{rel_path}: missing aligned default-language and remote-server governance guidance")
    for rel_path, snippets in CODE_COMMENT_ALIGNMENT_RULES.items():
        path = skill_dir / rel_path
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not all(snippet in text for snippet in snippets):
            errors.append(f"{rel_path}: missing code-comment governance guidance")


def validate_skill_rule_hardening(text: str, errors: list[str]) -> None:
    if not all(snippet in text for snippet in SKILL_REQUIRED_SNIPPETS):
        errors.append("SKILL.md: missing local-root or remote-mutation hardening guidance")
    if not all(snippet in text for snippet in SKILL_TOKEN_USAGE_SNIPPETS):
        errors.append("SKILL.md: missing explicit Codex token usage routing guidance")


def validate_openai_yaml(path: Path, errors: list[str], *, self_skill: bool) -> None:
    if not self_skill:
        return
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    interface = parse_openai_interface(text)
    if interface is None:
        errors.append("agents/openai.yaml: missing interface section")
        return
    for key in ("display_name", "short_description", "default_prompt"):
        value = interface.get(key, "").strip()
        if not value:
            errors.append(f"agents/openai.yaml: missing interface.{key}")
        elif value.lower() in {"todo", "tbd", "placeholder"}:
            errors.append(f"agents/openai.yaml: interface.{key} is a placeholder")
    default_prompt = interface.get("default_prompt", "")
    if default_prompt and "$agents-md-generator" not in default_prompt:
        errors.append("agents/openai.yaml: default_prompt must mention $agents-md-generator")
    normalized_prompt = default_prompt.lower()
    for snippet in OPENAI_REQUIRED_PROMPT_SNIPPETS:
        if default_prompt and snippet.lower() not in normalized_prompt:
            errors.append("agents/openai.yaml: default_prompt must keep explicit default-language and remote task-routing rules")
            break
    for snippet in OPENAI_TOKEN_USAGE_PROMPT_SNIPPETS:
        if default_prompt and snippet.lower() not in normalized_prompt:
            errors.append("agents/openai.yaml: default_prompt must document explicit Codex token usage routing")
            break
    if default_prompt and TAKEOVER_REMOTE_PROMPT_RULE.lower() not in normalized_prompt:
        errors.append("agents/openai.yaml: takeover prompt must separate remote structure governance from remote server enablement and task-route mapping")


def validate_global_baseline_template(path: Path, errors: list[str]) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    required_snippets = (
        "timed follow-up",
        "1000 lines",
        "scripts/python/<function>/<name>.py",
        "scripts/shell/<function>/<name>.sh",
        "scripts/bat/<function>/<name>.bat",
        "scripts/powershell/<function>/<name>.ps1",
        "local JSON governance configuration",
    )
    for snippet in required_snippets:
        if snippet not in text:
            errors.append(f"assets/templates/global-codex-agents.md: missing global baseline rule snippet `{snippet}`")
    forbidden_snippets = (
        ".agents/script-governance-exceptions.json",
        "docs/development/decomposition-plans",
        "skills/agents-md-generator",
    )
    for snippet in forbidden_snippets:
        if snippet in text:
            errors.append(f"assets/templates/global-codex-agents.md: must not leak repository-specific detail `{snippet}`")


def validate_evals_contract(path: Path, errors: list[str], *, self_skill: bool) -> None:
    if not self_skill or not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"evals/evals.json: invalid JSON: {exc.msg}")
        return
    if not isinstance(data, dict):
        errors.append("evals/evals.json: root must be a JSON object")
        return
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("evals/evals.json: cases must be a non-empty list")
        return

    ids: set[str] = set()
    duplicate_ids: set[str] = set()
    covered_patterns: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"evals/evals.json: case {index} must be an object")
            continue
        case_id = str(case.get("id", "")).strip()
        if not case_id:
            errors.append(f"evals/evals.json: case {index} is missing id")
        elif case_id in ids:
            duplicate_ids.add(case_id)
        else:
            ids.add(case_id)
        for key in ("kind", "handler", "description"):
            if not str(case.get(key, "")).strip():
                errors.append(f"evals/evals.json: case {case_id or index} is missing {key}")
        patterns = case.get("patterns")
        if not isinstance(patterns, list) or not patterns:
            errors.append(f"evals/evals.json: case {case_id or index} must list Skill design patterns")
            continue
        normalized_patterns = {str(pattern).strip() for pattern in patterns if str(pattern).strip()}
        if not normalized_patterns:
            errors.append(f"evals/evals.json: case {case_id or index} must list Skill design patterns")
            continue
        unknown_patterns = sorted(normalized_patterns - REQUIRED_SKILL_DESIGN_PATTERNS)
        if unknown_patterns:
            errors.append(f"evals/evals.json: case {case_id or index} uses unknown Skill design patterns {unknown_patterns}")
        covered_patterns.update(normalized_patterns & REQUIRED_SKILL_DESIGN_PATTERNS)

    if duplicate_ids:
        errors.append(f"evals/evals.json: duplicate case ids {sorted(duplicate_ids)}")
    missing_cases = sorted(REQUIRED_EVAL_CASE_IDS - ids)
    if missing_cases:
        errors.append(f"evals/evals.json: missing required effectiveness cases {missing_cases}")
    missing_patterns = sorted(REQUIRED_SKILL_DESIGN_PATTERNS - covered_patterns)
    if missing_patterns:
        errors.append(f"evals/evals.json: missing required Skill design pattern coverage {missing_patterns}")


def validate_script_output_default_config(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"config/script-output-policy-default.json: invalid JSON: {exc.msg}")
        return
    if not isinstance(data, dict):
        errors.append("config/script-output-policy-default.json: root must be a JSON object")
        return
    for item in validate_script_output_policy_data(data, require_explicit=True):
        errors.append(f"config/script-output-policy-default.json: {item}")


def skill_project_root(skill_dir: Path) -> Path:
    if skill_dir.parent.name == "skills":
        return skill_dir.parents[1]
    return skill_dir


def has_repo_governance(project_root: Path) -> bool:
    return (project_root / ".agents" / "global-rule-overrides.json").is_file()


def validate_decomposition_plan(project_root: Path, relative_path: str) -> list[str]:
    plan_path = decomposition_plan_path(project_root, relative_path)
    if not plan_path.is_file():
        return [f"{relative_path} exceeds configured line limit and requires decomposition plan `{plan_path.relative_to(project_root).as_posix()}`"]
    text = plan_path.read_text(encoding="utf-8", errors="ignore")
    required_sections = load_global_rule_overrides(project_root)["data"]["source_file_limits"].get("required_plan_sections", [])
    missing = [section for section in required_sections if f"## {section}" not in text]
    if missing:
        return [f"{plan_path.relative_to(project_root).as_posix()}: missing decomposition plan sections {missing}"]
    return []


def audit(skill_dir: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    checked: list[str] = []
    project_root = skill_project_root(skill_dir)
    skill_path = skill_dir / "SKILL.md"
    frontmatter = parse_frontmatter(skill_path.read_text(encoding="utf-8", errors="ignore")) if skill_path.exists() else {}
    self_skill = is_agents_md_generator_skill(skill_dir, frontmatter)

    required_files = CORE_REQUIRED_FILES + (SELF_REQUIRED_FILES if self_skill else [])
    for rel_path in required_files:
        path = skill_dir / rel_path
        checked.append(rel_path)
        if not path.exists():
            errors.append(f"missing required file: {rel_path}")

    if self_skill:
        for name in SELF_DISALLOWED_ROOT_DOCS:
            if (skill_dir / name).exists():
                errors.append(f"disallowed extra root documentation file: {name}")
    if self_skill and (skill_dir / "AGENTS.md").exists():
        errors.append("disallowed skill root AGENTS.md")

    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8", errors="ignore")
        fm = frontmatter
        if set(fm) != {"name", "description"}:
            errors.append("SKILL.md frontmatter must contain only name and description")
        name = fm.get("name", "")
        if not SKILL_NAME_RE.fullmatch(name):
            errors.append("SKILL.md name must match [a-z0-9-]+")
        if name and name != skill_dir.name:
            errors.append("SKILL.md name must match the skill directory name")
        description = fm.get("description", "")
        if not description.startswith("Use when"):
            errors.append("SKILL.md description must start with 'Use when'")
        if len(description) > 1024:
            errors.append("SKILL.md description must be 1024 characters or fewer")
        if len(text.splitlines()) > 500:
            errors.append("SKILL.md must stay under 500 lines")
        for rel_path in referenced_paths(text):
            checked.append(rel_path)
            if not (skill_dir / rel_path).exists():
                errors.append(f"SKILL.md references missing resource: {rel_path}")
        if contains_local_reference(text):
            errors.append("SKILL.md must not depend on local reference folders")
        if self_skill:
            validate_skill_contract_alignment(skill_dir, text, errors)
            validate_skill_rule_hardening(text, errors)

    version_path = skill_dir / "VERSION"
    if self_skill and version_path.exists():
        version_text = version_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not re.fullmatch(r"v\d+\.\d+\.\d+", version_text):
            errors.append("VERSION must use semantic format vX.Y.Z")

    validate_openai_yaml(skill_dir / "agents" / "openai.yaml", errors, self_skill=self_skill)
    if self_skill:
        validate_reference_alignment(skill_dir, errors)
        validate_global_baseline_template(skill_dir / "assets" / "templates" / "global-codex-agents.md", errors)
        validate_evals_contract(skill_dir / "evals" / "evals.json", errors, self_skill=self_skill)
        validate_script_output_default_config(skill_dir / "config" / "script-output-policy-default.json", errors)

    for script in sorted((skill_dir / "scripts").glob("*.py")):
        rel_path = script.relative_to(skill_dir).as_posix()
        if rel_path not in checked:
            checked.append(rel_path)
        try:
            source = script.read_text(encoding="utf-8", errors="ignore")
            compile(source, str(script), "exec")
        except SyntaxError as exc:
            errors.append(f"{rel_path} does not compile: {exc.msg}")
        line_count = source.count("\n") + 1
        if line_count > 1000 and has_repo_governance(project_root):
            relative_to_project = script.relative_to(project_root).as_posix() if script.is_relative_to(project_root) else rel_path
            errors.extend(validate_decomposition_plan(project_root, relative_to_project))

    for path in skill_dir.rglob("*"):
        rel_path = path.relative_to(skill_dir).as_posix()
        rel_parts = path.relative_to(skill_dir).parts
        if ".git" in rel_parts:
            continue
        if "__pycache__" in rel_parts or path.suffix in DISALLOWED_CACHE_SUFFIXES:
            errors.append(f"disallowed generated cache artifact: {rel_path}")
            continue
        if not path.is_file():
            continue
        if path.suffix in {".md", ".yaml", ".yml", ".py"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if rel_parts and rel_parts[0] == "references" and path.suffix == ".md":
                lines = text.splitlines()
                if len(lines) > 100 and not has_toc(lines):
                    errors.append(f"{rel_path}: reference files over 100 lines need a table of contents")
            if "{{" in text and (rel_path == "SKILL.md" or rel_path.startswith("agents/")):
                warnings.append(f"{rel_path}: contains template placeholder syntax outside templates")
            if rel_path.startswith("assets/templates/"):
                template_name = path.name
                known = KNOWN_TEMPLATE_PLACEHOLDERS.get(template_name, set())
                for placeholder in sorted(set(TEMPLATE_PLACEHOLDER_RE.findall(text)) - known):
                    errors.append(f"{template_name}: contains unknown template placeholder: {placeholder}")
            if contains_local_reference(text):
                errors.append(f"{rel_path}: references local-only development material")

    return {
        "skill_dir": str(skill_dir),
        "checked": sorted(set(checked)),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit agents-md-generator skill structure and scripts.")
    parser.add_argument("skill_dir", nargs="?", default=".")
    args = parser.parse_args()
    emit_json(audit(resolve_project(args.skill_dir)))


if __name__ == "__main__":
    main()
