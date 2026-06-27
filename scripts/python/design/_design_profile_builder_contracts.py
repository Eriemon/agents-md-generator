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

# 导入设计档案依赖。
import json
from pathlib import Path
import re
from typing import Any

# 导入设计档案依赖。
from design_questions import *
from design_remote_gate import *
from design_profile_contracts import global_rule_overrides_contract
from agents_common import ensure_global_rule_overrides_file, inspect_project, emit_json, resolve_project
from manage_docs import scaffold as scaffold_docs
from workspace_settings_policy import workspace_settings_contract
# 整理 模块入口 需要的 ROOT OPTIONAL WORK DIRS 设计档案信息。
ROOT_OPTIONAL_WORK_DIRS = ("tests", "reports", "runs", "smoke")  # 设计档案值

# 整理 模块入口 需要的 ROOT OPTIONAL WORK DIR PREFIXES 设计档案信息。
ROOT_OPTIONAL_WORK_DIR_PREFIXES = ("smoke-",)  # 设计档案值

# 定义 infer_kind  设计档案入口。
def infer_kind(project: Path) -> str:

    # 校验 infer_kind 的设计档案分支。
    if (
        (project / "SKILL.md").exists()
        or any(path.is_file() for path in project.glob("*/SKILL.md"))
        or any(path.is_file() for path in project.glob("skills/*/SKILL.md"))
    ):

        # 返回 infer_kind 的设计档案载荷。
        return "skill"

    # 返回 infer_kind 的设计档案载荷。
    return "engineering"

# 定义 meaningful_paths  设计档案入口。
def meaningful_paths(facts: dict[str, Any]) -> bool:

    # 收集 files 设计档案条目。
    files = [str(item) for item in facts.get("files", []) if str(item)]  # 设计档案值

    # 收集 directories 设计档案条目。
    directories = [str(item) for item in facts.get("directories", []) if str(item)]  # 设计档案值

    # 收集 ignored files 设计档案条目。
    set_ignored_files = {"AGENTS.md", ".gitignore", ".gitattributes", ".editorconfig"}  # 设计档案值

    # 收集 meaningful files 设计档案条目。
    meaningful_files = [item for item in files if item not in set_ignored_files and not item.startswith(".agents/")]  # 设计档案值

    # 收集 meaningful dirs 设计档案条目。
    meaningful_dirs = [  # 设计档案值
        item  # 设计档案值
        for item in directories  # 设计档案值
        if item  # 设计档案值
        and item not in {"docs", ".agents"}  # 设计档案值
        and not item.startswith("docs/")  # 设计档案值
        and not item.startswith(".agents/")  # 设计档案值
    ]

    # 返回 meaningful_paths 的设计档案载荷。
    return bool(meaningful_files or meaningful_dirs)

# 定义 takeover_required  设计档案入口。
def takeover_required(project: Path) -> tuple[bool, dict[str, Any]]:

    # 收集 facts 设计档案条目。
    facts = inspect_project(project)  # 设计档案值

    # 收集 reasons 设计档案条目。
    reasons = {str(item) for item in facts.get("root_agents_md_trigger_reasons", [])}  # 设计档案值

    # 标记 triggered 判断，控制 takeover_required 的分支走向。
    bool_triggered = bool(reasons & {"agents_version_mismatch", "generator_version_mismatch"})  # 设计档案值

    # 校验 takeover_required 的设计档案分支。
    if not bool_triggered:

        # 返回 takeover_required 的设计档案载荷。
        return False, facts

    # 校验 takeover_required 的设计档案分支。
    if not meaningful_paths(facts):

        # 返回 takeover_required 的设计档案载荷。
        return False, facts

    # 返回 takeover_required 的设计档案载荷。
    return True, facts

# 定义 missing_answers  设计档案入口。
def missing_answers(answers: dict[str, Any], kind: str) -> list[str]:

    # 收集 missing 设计档案条目。
    list_missing: list[str] = []  # 设计档案值

    # 整理 missing_answers 需要的 remote policy required 设计档案信息。
    remote_policy_required = remote_directory_policy_required(answers)  # 设计档案值

    # 逐项检查 missing_answers 设计档案候选。
    for item in questions_for(kind):

        # 整理 missing_answers 需要的 key 设计档案信息。
        str_key = str(item["answer_key"])  # 设计档案值

        # 校验 missing_answers 的设计档案分支。
        if str_key in {"default_conversation_language", USE_REMOTE_SERVER_KEY}:

            # 分隔 missing_answers 的控制流边界。
            continue

        # 校验 missing_answers 的设计档案分支。
        if str_key in REMOTE_DIRECTORY_POLICY_KEYS and not remote_policy_required:

            # 分隔 missing_answers 的控制流边界。
            continue

        # 校验 missing_answers 的设计档案分支。
        if str_key in OPTIONAL_EMPTY_KEYS and str_key in answers:

            # 分隔 missing_answers 的控制流边界。
            continue

        # 校验 missing_answers 的设计档案分支。
        if str_key not in answers or empty(answers[str_key]):

            # 追加 missing_answers 的设计档案诊断。
            list_missing.append(str_key)

    # 校验 missing_answers 的设计档案分支。
    if ALIGNMENT_KEY not in answers:

        # 追加 missing_answers 的设计档案诊断。
        list_missing.append(ALIGNMENT_KEY)

    # 返回 missing_answers 的设计档案载荷。
    return list_missing

# 定义 parse_skill_name  设计档案入口。
def parse_skill_name(skill_path: Path) -> str:

    # 整理 parse_skill_name 需要的 text 设计档案信息。
    text = skill_path.read_text(encoding="utf-8", errors="ignore")  # 设计档案值

    # 整理 parse_skill_name 需要的 match 设计档案信息。
    match = re.search(r"^---\s*\n(.*?)\n---", text, flags=re.DOTALL)  # 设计档案值

    # 校验 parse_skill_name 的设计档案分支。
    if not match:

        # 返回 parse_skill_name 的设计档案载荷。
        return ""

    # 逐项检查 parse_skill_name 设计档案候选。
    for line in match.group(1).splitlines():

        # 校验 parse_skill_name 的设计档案分支。
        if line.strip().startswith("name:"):

            # 返回 parse_skill_name 的设计档案载荷。
            return line.split(":", 1)[1].strip().strip("\"'")

    # 返回 parse_skill_name 的设计档案载荷。
    return ""

# 定义 discover_skill_files  设计档案入口。
def discover_skill_files(project: Path) -> list[Path]:

    # 整理 discover_skill_files 需要的 skip 设计档案信息。
    set_skip = {".git", "dist", "ref", "__pycache__"}  # 设计档案值

    # 收集 files 设计档案条目。
    list_files: list[Path] = []  # 设计档案值

    # 逐项检查 discover_skill_files 设计档案候选。
    for path in project.rglob("SKILL.md"):

        # 整理 discover_skill_files 需要的 relative 设计档案信息。
        relative = path.relative_to(project)  # 设计档案值

        # 校验 discover_skill_files 的设计档案分支。
        if set(relative.parts) & set_skip:

            # 分隔 discover_skill_files 的控制流边界。
            continue

        # 追加 discover_skill_files 的设计档案诊断。
        list_files.append(path)

    # 返回 discover_skill_files 的设计档案载荷。
    return sorted(list_files)

# 定义 skill_layout_contract  设计档案入口。
def skill_layout_contract(project: Path, name: str, answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:

    # 收集 errors 设计档案条目。
    list_errors: list[str] = []  # 设计档案值

    # 标记 takeover mode 判断，控制 skill_layout_contract 的分支走向。
    bool_takeover_mode = bool(answers.get("takeover_mode"))  # 设计档案值

    # 校验 skill_layout_contract 的设计档案分支。
    if not SKILL_NAME_RE.fullmatch(name):

        # 追加 skill_layout_contract 的设计档案诊断。
        list_errors.append("skill name must use lowercase letters, digits, and hyphens only")

    # 整理 skill_layout_contract 需要的 expected 设计档案信息。
    expected = project / "skills" / name / "SKILL.md"  # 设计档案值

    # 收集 files 设计档案条目。
    list_files = discover_skill_files(project)  # 设计档案值

    # 校验 skill_layout_contract 的设计档案分支。
    if expected.exists():

        # 整理 skill_layout_contract 需要的 skill name 设计档案信息。
        str_skill_name = parse_skill_name(expected)  # 设计档案值

        # 校验 skill_layout_contract 的设计档案分支。
        if str_skill_name != name:

            # 追加 skill_layout_contract 的设计档案诊断。
            list_errors.append(f"SKILL.md name must match folder name: {name}")

        # 返回 skill_layout_contract 的设计档案载荷。
        return {"path": f"skills/{name}", "skill_file": f"skills/{name}/SKILL.md"}, list_errors

    # 校验 skill_layout_contract 的设计档案分支。
    if answers.get("has_existing_work") == "yes" and not bool_takeover_mode:

        # 校验 skill_layout_contract 的设计档案分支。
        if not list_files:

            # 追加 skill_layout_contract 的设计档案诊断。
            list_errors.append("skill projects with existing work must already place the skill under skills/<skill-name>/SKILL.md")

        # 逐项检查 skill_layout_contract 设计档案候选。
        for skill_file in list_files:

            # 整理 skill_layout_contract 需要的 relative 设计档案信息。
            relative = skill_file.relative_to(project).as_posix()  # 设计档案值

            # 收集 parts 设计档案条目。
            parts = skill_file.relative_to(project).parts  # 设计档案值

            # 校验 skill_layout_contract 的设计档案分支。
            if len(parts) >= 3 and parts[0] == "skills":

                # 整理 skill_layout_contract 需要的 folder 设计档案信息。
                folder = parts[1]  # 设计档案值

                # 整理 skill_layout_contract 需要的 skill name 设计档案信息。
                str_skill_name = parse_skill_name(skill_file)  # 设计档案值

                # 校验 skill_layout_contract 的设计档案分支。
                if folder != name:

                    # 追加 skill_layout_contract 的设计档案诊断。
                    list_errors.append(f"skill folder must match requested skill name: skills/{name}/")

                # 校验 skill_layout_contract 的设计档案分支。
                if str_skill_name != folder:

                    # 追加 skill_layout_contract 的设计档案诊断。
                    list_errors.append(f"SKILL.md name must match folder name: {folder}")
            else:

                # 追加 skill_layout_contract 的设计档案诊断。
                list_errors.append(f"skill projects must use skills/<skill-name>/SKILL.md; found {relative}")

    # 返回 skill_layout_contract 的设计档案载荷。
    return {"path": f"skills/{name}", "skill_file": f"skills/{name}/SKILL.md"}, list_errors

# 定义 directory_layout_policy  设计档案入口。
def directory_layout_policy(kind: str, name: str) -> dict[str, Any]:

    # 整理 directory_layout_policy 需要的 primary 设计档案信息。
    primary = f"skills/{name}/" if kind == "skill" else f"engineering/{name}/"  # 设计档案值

    # 返回 directory_layout_policy 的设计档案载荷。
    return {
        "primary_project_root": primary,
        "allowed_new_paths": [
            primary,
            "tests/",
            "smoke/",
            "reports/",
            "runs/",
            "dist/",
            "docs/",
            ".agents/",
            "ref/",
        ],
        "root_optional_work_dirs": list(ROOT_OPTIONAL_WORK_DIRS),
        "root_optional_work_dir_prefixes": list(ROOT_OPTIONAL_WORK_DIR_PREFIXES),
        "enforce_primary_project_root": True,
    }

# 定义 engineering_layout_contract  设计档案入口。
def engineering_layout_contract(project: Path, name: str, answers: dict[str, Any]) -> list[str]:

    # 收集 errors 设计档案条目。
    list_errors: list[str] = []  # 设计档案值

    # 整理 engineering_layout_contract 需要的 expected 设计档案信息。
    expected = project / "engineering" / name  # 设计档案值

    # 校验 engineering_layout_contract 的设计档案分支。
    if answers.get("has_existing_work") == "yes" and not expected.exists() and not bool(answers.get("takeover_mode")):

        # 追加 engineering_layout_contract 的设计档案诊断。
        list_errors.append("engineering projects with existing work must already place the project under engineering/<project-name>/")

    # 返回 engineering_layout_contract 的设计档案载荷。
    return list_errors

# 定义 summarize_fields  设计档案入口。
def summarize_fields(answers: dict[str, Any], keys: list[str]) -> dict[str, Any]:

    # 返回 summarize_fields 的设计档案载荷。
    return {key: answers[key] for key in keys if key in answers}

# 定义 review_summary  设计档案入口。
def review_summary(
    answers: dict[str, Any] | None,
    kind: str | None = None,
    current_keys: list[str] | None = None,
    confirmed_keys: list[str] | None = None,
    final: bool = False,
) -> dict[str, Any]:

    # 收集 answers 设计档案条目。
    answers = answers or {}  # 设计档案值

    # 收集 current keys 设计档案条目。
    current_keys = current_keys or []  # 设计档案值

    # 收集 confirmed keys 设计档案条目。
    confirmed_keys = confirmed_keys or []  # 设计档案值

    # 保存 confirmed 映射，维持 review_summary 的字段关系。
    dict_confirmed = summarize_fields(answers, confirmed_keys)  # 设计档案值

    # 保存 current 映射，维持 review_summary 的字段关系。
    dict_current = summarize_fields(answers, current_keys)  # 设计档案值

    # 校验 review_summary 的设计档案分支。
    if final:

        # 整理 review_summary 需要的 summary 设计档案信息。
        str_summary = "请确认完整设计访谈已经一致；如需修正，请提交修正字段后重新确认。"  # 设计档案值

    # 校验 review_summary 的设计档案分支。
    elif current_keys:

        # 整理 review_summary 需要的 summary 设计档案信息。
        str_summary = "请确认当前问题组的答案是否正确；如果否，请修正本组字段并重新确认。"  # 设计档案值
    else:

        # 整理 review_summary 需要的 summary 设计档案信息。
        str_summary = "请用户确认以上理解是否正确；如果否，请修正对应字段后重新确认。"  # 设计档案值

    # 返回 review_summary 的设计档案载荷。
    return {
        "kind": kind or answers.get("development_type", "unconfirmed"),
        "current_group_fields": dict_current,
        "confirmed_fields": dict_confirmed,
        "summary": str_summary,
    }

# 定义 attach_alignment  设计档案入口。
def attach_alignment(payload: dict[str, Any], answers: dict[str, Any] | None = None, kind: str | None = None) -> dict[str, Any]:

    # 收集 answers 设计档案条目。
    answers = answers or {}  # 设计档案值

    # 收集 confirmed keys 设计档案条目。
    confirmed_keys = [key for key in answers if key != ALIGNMENT_KEY]  # 设计档案值

    # 整理 attach_alignment 需要的 中间载荷 设计档案信息。
    payload["review_summary"] = review_summary(answers, kind, [], confirmed_keys, final=False)  # 设计档案值

    # 整理 attach_alignment 需要的 中间载荷 设计档案信息。
    payload["confirmed_so_far"] = payload["review_summary"]["confirmed_fields"]  # 设计档案值

    # 整理 attach_alignment 需要的 中间载荷 设计档案信息。
    payload["confirmation_question"] = "请确认以上理解是否正确？如果正确回答是；如果不正确回答否并指出需要修正的字段。"  # 设计档案值

    # 整理 attach_alignment 需要的 中间载荷 设计档案信息。
    payload["needs_alignment_confirmation"] = answers.get(ALIGNMENT_KEY) is not True  # 设计档案值

    # 返回 attach_alignment 的设计档案载荷。
    return payload

# 定义 engineering_rule_contract  设计档案入口。
def engineering_rule_contract(answers: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:

    # 整理 engineering_rule_contract 需要的 primary raw 设计档案信息。
    primary_raw = answers.get("engineering_rule_primary", "none")  # 设计档案值

    # 校验 engineering_rule_contract 的设计档案分支。
    if isinstance(primary_raw, list):

        # 返回 engineering_rule_contract 的设计档案载荷。
        return None, ["engineering_rule_primary must name one primary rule set, not a list"]

    # 整理 engineering_rule_contract 需要的 primary 设计档案信息。
    primary = str(primary_raw).strip().lower() or "none"  # 设计档案值

    # 整理 engineering_rule_contract 需要的 mode 设计档案信息。
    mode = str(answers.get("engineering_rule_mode", "none" if primary == "none" else "mini")).strip().lower()  # 设计档案值

    # 整理 engineering_rule_contract 需要的 scope 设计档案信息。
    scope = str(answers.get("engineering_rule_scope", "on-demand")).strip().lower()  # 设计档案值

    # 收集 notes 设计档案条目。
    notes = str(answers.get("engineering_rule_notes", "")).strip()  # 设计档案值

    # 校验 engineering_rule_contract 的设计档案分支。
    if primary in {"", "none", "not-configured"}:

        # 校验 engineering_rule_contract 的设计档案分支。
        if mode != "none":

            # 返回 engineering_rule_contract 的设计档案载荷。
            return None, ["engineering_rule_mode must be none when engineering_rule_primary is none"]

        # 返回 engineering_rule_contract 的设计档案载荷。
        return {
            "primary": "none",
            "mode": "none",
            "scope": "on-demand",
            "notes": notes,
            "full_reference_allowed_in_agents": False,
            "compatibility_policy": "no active book-derived rule set configured",
            "compression_policy": "keep only decision-changing rules in generated AGENTS.md",
        }, []

    # 收集 errors 设计档案条目。
    list_errors: list[str] = []  # 设计档案值

    # 校验 engineering_rule_contract 的设计档案分支。
    if "," in primary or "+" in primary:

        # 追加 engineering_rule_contract 的设计档案诊断。
        list_errors.append("engineering_rule_primary must choose one primary active rule set")

    # 校验 engineering_rule_contract 的设计档案分支。
    if primary not in ENGINEERING_RULE_SETS:

        # 追加 engineering_rule_contract 的设计档案诊断。
        list_errors.append(f"unknown engineering_rule_primary: {primary}")

    # 校验 engineering_rule_contract 的设计档案分支。
    if mode == "full":

        # 追加 engineering_rule_contract 的设计档案诊断。
        list_errors.append("full book rules must stay reference-only and must not be pasted into AGENTS.md")

    # 校验 engineering_rule_contract 的设计档案分支。
    elif mode not in ENGINEERING_RULE_MODES or mode == "none":

        # 追加 engineering_rule_contract 的设计档案诊断。
        list_errors.append("engineering_rule_mode must be mini or nano")

    # 校验 engineering_rule_contract 的设计档案分支。
    if scope not in ENGINEERING_RULE_SCOPES:

        # 追加 engineering_rule_contract 的设计档案诊断。
        list_errors.append("engineering_rule_scope must be project-baseline, scoped, or on-demand")

    # 校验 engineering_rule_contract 的设计档案分支。
    if list_errors:

        # 返回 engineering_rule_contract 的设计档案载荷。
        return None, list_errors

    # 返回 engineering_rule_contract 的设计档案载荷。
    return {
        "primary": primary,
        "mode": mode,
        "scope": scope,
        "notes": notes,
        "full_reference_allowed_in_agents": False,
        "compatibility_policy": "one primary active rule set; use other rule sets only as scoped or on-demand guidance",
        "compression_policy": "decision-equivalent compression: keep decision-changing, trigger, tradeoff, and checklist rules",
    }, []

# 定义 normalize_list  设计档案入口。
def normalize_list(value: Any) -> list[str]:

    # 校验 normalize_list 的设计档案分支。
    if isinstance(value, list):

        # 返回 normalize_list 的设计档案载荷。
        return [str(item).strip() for item in value if str(item).strip()]

    # 整理 normalize_list 需要的 raw 设计档案信息。
    raw = str(value).strip()  # 设计档案值

    # 校验 normalize_list 的设计档案分支。
    if not raw:

        # 返回 normalize_list 的设计档案载荷。
        return []

    # 返回 normalize_list 的设计档案载荷。
    return [item.strip() for item in raw.replace("，", ",").split(",") if item.strip()]


# 定义 invalid_remote_relative_template_reason  设计档案入口。
def invalid_remote_relative_template_reason(raw: str) -> str | None:

    # 整理 invalid_remote_relative_template_reason 需要的 value 设计档案信息。
    raw_value = str(raw).strip()  # 设计档案值

    # 整理 invalid_remote_relative_template_reason 需要的 normalized 设计档案信息。
    normalized = raw_value.replace("\\", "/")  # 设计档案值

    # 校验 invalid_remote_relative_template_reason 的设计档案分支。
    if not raw_value:

        # 返回 invalid_remote_relative_template_reason 的设计档案载荷。
        return "template must not be empty"

    # 校验 invalid_remote_relative_template_reason 的设计档案分支。
    if re.match(r"^[A-Za-z]:[/\\]", raw_value) or normalized.startswith("/"):

        # 返回 invalid_remote_relative_template_reason 的设计档案载荷。
        return "template must stay relative to the remote workspace root"

    # 校验 invalid_remote_relative_template_reason 的设计档案分支。
    if ".." in normalized.split("/"):

        # 返回 invalid_remote_relative_template_reason 的设计档案载荷。
        return "template must not contain parent traversal"

    # 校验 invalid_remote_relative_template_reason 的设计档案分支。
    if any(char in raw_value for char in "*?|"):

        # 返回 invalid_remote_relative_template_reason 的设计档案载荷。
        return "template must not contain wildcard or unsafe shell characters"

    # 校验 invalid_remote_relative_template_reason 的设计档案分支。
    if "//" in normalized:

        # 返回 invalid_remote_relative_template_reason 的设计档案载荷。
        return "template must not contain repeated path separators"

    # 返回 invalid_remote_relative_template_reason 的设计档案载荷。
    return None


# 定义 disabled_remote_environment_policy  设计档案入口。
def disabled_remote_environment_policy() -> dict[str, Any]:

    # 返回 disabled_remote_environment_policy 的设计档案载荷。
    return {
        "status": "disabled",
        "scope": "remote-only",
        "manager": "conda-prefix",
        "path_template": "",
        "required_when_remote_configured": True,
    }


# 定义 disabled_remote_runtime_archive_policy  设计档案入口。
def disabled_remote_runtime_archive_policy() -> dict[str, Any]:

    # 返回 disabled_remote_runtime_archive_policy 的设计档案载荷。
    return {
        "status": "disabled",
        "active_path_template": "",
        "backup_path_template": "",
        "run_id_required": True,
        "archive_after_verification": False,
        "archive_trigger": "",
    }


# 定义 remote_environment_policy  设计档案入口。
def remote_environment_policy(answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:

    # 校验 remote_environment_policy 的设计档案分支。
    if not remote_directory_policy_required(answers):

        # 返回 remote_environment_policy 的设计档案载荷。
        return disabled_remote_environment_policy(), []

    # 定位 template 的文件边界，供 remote_environment_policy 后续读写校验使用。
    path_template = str(answers.get("remote_conda_environment_layout", "")).strip()  # 设计档案值

    # 校验 remote_environment_policy 的设计档案分支。
    if not path_template:

        # 返回 remote_environment_policy 的设计档案载荷。
        return {}, ["missing required answer: remote_conda_environment_layout"]

    # 校验 remote_environment_policy 的设计档案分支。
    if path_template.lower() == "disabled":

        # 返回 remote_environment_policy 的设计档案载荷。
        return {}, ["remote_conda_environment_layout cannot be `disabled` when remote structure or remote servers are enabled"]

    # 整理 remote_environment_policy 需要的 invalid 设计档案信息。
    invalid = invalid_remote_relative_template_reason(path_template)  # 设计档案值

    # 校验 remote_environment_policy 的设计档案分支。
    if invalid:

        # 返回 remote_environment_policy 的设计档案载荷。
        return {}, [f"remote_conda_environment_layout {invalid}: {path_template}"]

    # 返回 remote_environment_policy 的设计档案载荷。
    return {
        "status": "enabled",
        "scope": "remote-only",
        "manager": "conda-prefix",
        "path_template": path_template,
        "required_when_remote_configured": True,
    }, []


# 定义 remote_runtime_archive_policy  设计档案入口。
def remote_runtime_archive_policy(answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:

    # 校验 remote_runtime_archive_policy 的设计档案分支。
    if not remote_directory_policy_required(answers):

        # 返回 remote_runtime_archive_policy 的设计档案载荷。
        return disabled_remote_runtime_archive_policy(), []

    # 定位 active path 的文件边界，供 remote_runtime_archive_policy 后续读写校验使用。
    active_path = str(answers.get("remote_run_artifact_active_layout", "")).strip()  # 设计档案值

    # 定位 backup path 的文件边界，供 remote_runtime_archive_policy 后续读写校验使用。
    backup_path = str(answers.get("remote_run_artifact_backup_layout", "")).strip()  # 设计档案值

    # 整理 remote_runtime_archive_policy 需要的 trigger 设计档案信息。
    trigger = str(answers.get("remote_run_archive_trigger", "")).strip()  # 设计档案值

    # 收集 missing 设计档案条目。
    list_missing = []  # 设计档案值

    # 校验 remote_runtime_archive_policy 的设计档案分支。
    if not active_path:

        # 追加 remote_runtime_archive_policy 的设计档案诊断。
        list_missing.append("missing required answer: remote_run_artifact_active_layout")

    # 校验 remote_runtime_archive_policy 的设计档案分支。
    if not backup_path:

        # 追加 remote_runtime_archive_policy 的设计档案诊断。
        list_missing.append("missing required answer: remote_run_artifact_backup_layout")

    # 校验 remote_runtime_archive_policy 的设计档案分支。
    if not trigger:

        # 追加 remote_runtime_archive_policy 的设计档案诊断。
        list_missing.append("missing required answer: remote_run_archive_trigger")

    # 校验 remote_runtime_archive_policy 的设计档案分支。
    if list_missing:

        # 返回 remote_runtime_archive_policy 的设计档案载荷。
        return {}, list_missing

    # 整理 remote_runtime_archive_policy 需要的 invalid 设计档案信息。
    invalid = [  # 设计档案值
        key  # 设计档案值
        for key, raw_value in {  # 设计档案值
            "remote_run_artifact_active_layout": active_path,  # 设计档案值
            "remote_run_artifact_backup_layout": backup_path,  # 设计档案值
            "remote_run_archive_trigger": trigger,  # 设计档案值
        }.items()  # 设计档案值
        if raw_value.lower() == "disabled"  # 设计档案值
    ]

    # 校验 remote_runtime_archive_policy 的设计档案分支。
    if invalid:

        # 返回 remote_runtime_archive_policy 的设计档案载荷。
        return {}, [f"{key} cannot be `disabled` when remote structure or remote servers are enabled" for key in invalid]

    # 收集 template errors 设计档案条目。
    list_template_errors: list[str] = []  # 设计档案值

    # 逐项检查 remote_runtime_archive_policy 设计档案候选。
    for key, raw_value in {
        "remote_run_artifact_active_layout": active_path,
        "remote_run_artifact_backup_layout": backup_path,
    }.items():

        # 整理 remote_runtime_archive_policy 需要的 invalid reason 设计档案信息。
        invalid_reason = invalid_remote_relative_template_reason(raw_value)  # 设计档案值

        # 校验 remote_runtime_archive_policy 的设计档案分支。
        if invalid_reason:

            # 追加 remote_runtime_archive_policy 的设计档案诊断。
            list_template_errors.append(f"{key} {invalid_reason}: {raw_value}")

    # 校验 remote_runtime_archive_policy 的设计档案分支。
    if list_template_errors:

        # 返回 remote_runtime_archive_policy 的设计档案载荷。
        return {}, list_template_errors

    # 返回 remote_runtime_archive_policy 的设计档案载荷。
    return {
        "status": "enabled",
        "active_path_template": active_path,
        "backup_path_template": backup_path,
        "run_id_required": "<run-id>" in active_path or "<run-id>" in backup_path,
        "archive_after_verification": trigger.casefold() == "after required verification passes".casefold(),
        "archive_trigger": trigger,
    }, []


# 定义 skill_design_contract  设计档案入口。
def skill_design_contract(answers: dict[str, Any]) -> dict[str, Any]:

    # 返回 skill_design_contract 的设计档案载荷。
    return {
        "trigger_scenarios": str(answers["trigger_scenarios"]).strip(),
        "patterns": normalize_list(answers["skill_design_patterns"]),
        "resource_plan": str(answers["resource_plan"]).strip(),
        "progressive_disclosure_policy": str(answers["progressive_disclosure_policy"]).strip(),
        "validation_gates": str(answers["validation_gates"]).strip(),
        "validation_method": str(answers["validation_method"]).strip(),
        "validation_granularity": str(answers["validation_granularity"]).strip(),
        "forward_testing_policy": str(answers["forward_testing_policy"]).strip(),
        "reference_material_policy": "temporary inputs only; distill durable constraints and remove local reference paths from generated AGENTS.md",
    }

# 定义 docs_contract  设计档案入口。
def docs_contract(name: str) -> dict[str, Any]:

    # 保存 branch policy 映射，维持 docs_contract 的字段关系。
    dict_branch_policy = git_branch_policy()  # 设计档案值

    # 保存 contract 映射，维持 docs_contract 的字段关系。
    dict_contract = {  # 设计档案值
        "root": "docs",  # 设计档案值
        "handoff": {  # 设计档案值
            "current": "docs/handoff/HANDOFF.md",  # 设计档案值
            "history": "docs/handoff/history_handoff",  # 设计档案值
            "archive_pattern": "HANDOFF-YYYYMMDD-HHMMSS.md",  # 设计档案值
            "required_sections": [  # 设计档案值
                "original_plan_and_steps",  # 设计档案值
                "current_step",  # 设计档案值
                "problems",  # 设计档案值
                "resolved_problems",  # 设计档案值
                "remaining_problems",  # 设计档案值
                "next_work",  # 设计档案值
                "verification_evidence",  # 设计档案值
            ],  # 设计档案值
        },  # 设计档案值
        "development": {  # 设计档案值
            "folder": "docs/development",  # 设计档案值
            "current": "docs/development/DEVELOPMENT.md",  # 设计档案值
            "history": "docs/development/history_development",  # 设计档案值
            "history_pattern": "YYYYMMDD-HHMMSS/DEVELOPMENT.md",  # 设计档案值
            "when": "Write and iteratively refresh the latest DEVELOPMENT.md at installable release time or stage completion.",  # 设计档案值
        },  # 设计档案值
        "install_configuration": {  # 设计档案值
            "folder": "docs/install_configuration",  # 设计档案值
            "targets": ["Codex", "Claude", "OpenClaw"],  # 设计档案值
        },  # 设计档案值
        "git_manager": {  # 设计档案值
            "folder": "docs/git_manager",  # 设计档案值
            "branch_model": "master-and-dist-release",  # 设计档案值
            "branch_policy": dict_branch_policy,  # 设计档案值
            "change_log": "docs/git_manager/CHANGELOG.md",  # 设计档案值
            "history": "docs/git_manager/history_git_manager",  # 设计档案值
            "dist_folder": "dist",  # 设计档案值
            "release_folder_pattern": f"{name}-vx.x.x",  # 设计档案值
            "zip_required": True,  # 设计档案值
        },  # 设计档案值
        "dir_manager": {  # 设计档案值
            "folder": "docs/dir_manager",  # 设计档案值
            "current_structure": "docs/dir_manager/current_structure.json",  # 设计档案值
            "planned_structure": "docs/dir_manager/planned_structure.json",  # 设计档案值
            "history": "docs/dir_manager/history_dir_manager",  # 设计档案值
            "review_required_for": ["create", "move", "delete", "rename"],  # 设计档案值
            "block_on_failed_review": True,  # 设计档案值
            "force_override_requires_user_confirmation": True,  # 设计档案值
            "archive_before_force_override": True,  # 设计档案值
        },  # 设计档案值
        "workspace_settings": workspace_settings_contract(),  # 设计档案值
    }

    # 返回 docs_contract 的设计档案载荷。
    return dict_contract


# 定义 memory_contract  设计档案入口。
def memory_contract(answers: dict[str, Any]) -> dict[str, Any]:

    # 标记 enabled 判断，控制 memory_contract 的分支走向。
    bool_enabled = bool(answers.get("memory_enabled"))  # 设计档案值

    # 整理 memory_contract 需要的 backend 设计档案信息。
    backend = str(answers.get("memory_storage_backend", "sqlite-plus-jsonl")).strip() or "sqlite-plus-jsonl"  # 设计档案值

    # 返回 memory_contract 的设计档案载荷。
    return {
        "enabled": bool_enabled,
        "folder": "docs/memory",
        "storage_backend": backend,
        "database": "docs/memory/memory.sqlite3",
        "events": "docs/memory/events.jsonl",
        "summaries": "docs/memory/summaries.md",
        "guide": "docs/memory/MEMORY.md",
        "capture_scope": str(answers.get("memory_capture_scope", "")).strip(),
        "read_policy": str(answers.get("memory_read_policy", "")).strip(),
        "sensitivity_policy": str(answers.get("memory_sensitivity_policy", "")).strip(),
        "compress_after_events": 20,
    }


# 定义 memory_policy_errors  设计档案入口。
def memory_policy_errors(answers: dict[str, Any]) -> list[str]:

    # 校验 memory_policy_errors 的设计档案分支。
    if not bool(answers.get("memory_enabled")):

        # 返回 memory_policy_errors 的设计档案载荷。
        return []

    # 整理 memory_policy_errors 需要的 backend 设计档案信息。
    backend = str(answers.get("memory_storage_backend", "")).strip()  # 设计档案值

    # 校验 memory_policy_errors 的设计档案分支。
    if backend != "sqlite-plus-jsonl":

        # 返回 memory_policy_errors 的设计档案载荷。
        return ["memory_storage_backend must be sqlite-plus-jsonl when memory_enabled is true"]

    # 返回 memory_policy_errors 的设计档案载荷。
    return []


# 定义 git_branch_policy  设计档案入口。
def git_branch_policy() -> dict[str, Any]:

    # 返回 git_branch_policy 的设计档案载荷。
    return {
        "protected_branches": ["master", "release"],
        "development_branches_allowed": True,
        "release_requires_committed_worktree": True,
        "release_requires_merge_to_master": True,
        "delete_other_local_branches_before_release": True,
        "release_prepare_auto_commit": True,
        "release_prepare_commit_message_template": "release-prepare: stage {branch} for {version}",
        "release_prepare_merge_message_template": "release-prepare: merge {branch} into master for {version}",
        "release_prepare_allowed_paths": ["<primary-project-root>", "tests", "docs", ".agents", "AGENTS.md", "dist"],
        "install_requires_release_artifact": True,
        "source_install_forbidden": True,
        "remote_branch_cleanup_allowed": False,
        "rule": (
            "Before releasing an installable dist package, commit all work, merge "  # 长文本字段片段
            "development branches into master, record the release, and delete local "  # 长文本字段片段
            "branches other than master and release."  # 长文本字段片段
        ),
    }

# 定义 dir_manager_contract  设计档案入口。
def dir_manager_contract() -> dict[str, Any]:

    # 返回 dir_manager_contract 的设计档案载荷。
    return {
        "folder": "docs/dir_manager",
        "current_structure": "docs/dir_manager/current_structure.json",
        "planned_structure": "docs/dir_manager/planned_structure.json",
        "history": "docs/dir_manager/history_dir_manager",
        "review_required_for": [
            "create top-level directories",
            "move directories",
            "delete directories",
            "rename directories",
            "change ownership, generated, release, or governance directories",
        ],
        "block_on_failed_review": True,
        "force_override_requires_user_confirmation": True,
        "archive_before_force_override": True,
    }

# 定义 remote_server_contract  设计档案入口。
def remote_server_contract(project: Path, answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:

    # 整理 remote_server_contract 需要的 enabled 设计档案信息。
    enabled = use_remote_server_enabled(answers)  # 设计档案值

    # 校验 remote_server_contract 的设计档案分支。
    if not enabled:

        # 返回 remote_server_contract 的设计档案载荷。
        return {
            "enabled": False,
            "dependency_required": False,
            "dependency_status": "not_required",
            "server_registry": [],
            "task_routes": [],
            "validation_required": False,
            "validation_status": "not_required",
            "unmatched_task_policy": "block-and-update-agents",
            "failover_policy": "auto-fallback",
            "enforce_remote_task_routing": False,
        }, []

    # 收集 errors 设计档案条目。
    list_errors: list[str] = []  # 设计档案值

    # 整理 remote_server_contract 需要的 dependency 设计档案信息。
    dependency = remote_dependency_summary()  # 设计档案值

    # 校验 remote_server_contract 的设计档案分支。
    if not dependency["installed"]:

        # 返回 remote_server_contract 的设计档案载荷。
        return {}, [f"use_remote_server=true requires installed {REMOTE_SSH_SKILL_NAME} ({REMOTE_SSH_GIT_URL})"]

    # 定位 skill dir 的文件边界，供 remote_server_contract 后续读写校验使用。
    path_skill_dir = Path(str(dependency["skill_dir"]))  # 设计档案值

    # 收集 choices、choice errors 设计档案条目。
    choices, choice_errors = remote_choices(path_skill_dir)  # 设计档案值

    # 调用 extend 处理 remote_server_contract。
    list_errors.extend(choice_errors)

    # 收集 registry 设计档案条目。
    list_registry = normalize_remote_server_registry(choices.get("servers", [])) if not choice_errors else []  # 设计档案值

    # 保存 registry map 映射，维持 remote_server_contract 的字段关系。
    registry_map = server_registry_map(list_registry)  # 设计档案值

    # 收集 raw routes 设计档案条目。
    raw_routes = answers.get(REMOTE_SERVER_TASK_ROUTES_KEY, [])  # 设计档案值

    # 收集 routes 设计档案条目。
    list_routes = normalize_remote_task_routes(raw_routes)  # 设计档案值

    # 校验 remote_server_contract 的设计档案分支。
    if not list_routes:

        # 整理 remote_server_contract 需要的 selected id 设计档案信息。
        selected_id = str(answers.get(REMOTE_SELECTED_SERVER_ID_KEY, "")).strip()  # 设计档案值

        # 整理 remote_server_contract 需要的 selected name 设计档案信息。
        selected_name = str(answers.get(REMOTE_SELECTED_SERVER_NAME_KEY, "")).strip()  # 设计档案值

        # 整理 remote_server_contract 需要的 selected category 设计档案信息。
        selected_category = str(answers.get(REMOTE_SELECTED_SERVER_CATEGORY_KEY, "")).strip()  # 设计档案值

        # 收集 selected functions 设计档案条目。
        selected_functions = answers.get(REMOTE_SELECTED_SERVER_FUNCTIONS_KEY, [])  # 设计档案值

        # 收集 selected tasks 设计档案条目。
        selected_tasks = normalize_remote_task_list(answers.get(REMOTE_SELECTED_SERVER_TASKS_KEY, []))  # 设计档案值

        # 校验 remote_server_contract 的设计档案分支。
        if not selected_id:

            # 追加 remote_server_contract 的设计档案诊断。
            list_errors.append(f"missing required answer: {REMOTE_SELECTED_SERVER_ID_KEY}")

        # 校验 remote_server_contract 的设计档案分支。
        if not selected_name:

            # 追加 remote_server_contract 的设计档案诊断。
            list_errors.append(f"missing required answer: {REMOTE_SELECTED_SERVER_NAME_KEY}")

        # 校验 remote_server_contract 的设计档案分支。
        if answers.get(REMOTE_SELECTION_CONFIRMED_KEY) is not True:

            # 追加 remote_server_contract 的设计档案诊断。
            list_errors.append(f"{REMOTE_SELECTION_CONFIRMED_KEY} must be true when use_remote_server is enabled")

        # 校验 remote_server_contract 的设计档案分支。
        if str(answers.get(REMOTE_VALIDATION_STATUS_KEY, "")).strip().lower() != "verified":

            # 追加 remote_server_contract 的设计档案诊断。
            list_errors.append(f"{REMOTE_VALIDATION_STATUS_KEY} must be verified when use_remote_server is enabled")

        # 校验 remote_server_contract 的设计档案分支。
        if not list_errors:

            # 整理 remote_server_contract 需要的 record 设计档案信息。
            record = remote_server_record(choices.get("servers", []), selected_id) if not choice_errors else None  # 设计档案值

            # 校验 remote_server_contract 的设计档案分支。
            if record is None:

                # 追加 remote_server_contract 的设计档案诊断。
                list_errors.append(f"selected remote server is no longer available in erie-remote-ssh choices: {selected_id}")
            else:

                # 收集 check data、check errors 设计档案条目。
                check_data, check_errors = remote_server_check(path_skill_dir, selected_id)  # 设计档案值

                # 收集 workspace data、workspace errors 设计档案条目。
                workspace_data, workspace_errors = remote_server_workspace_check(path_skill_dir, selected_id)  # 设计档案值

                # 调用 extend 处理 remote_server_contract。
                list_errors.extend(check_errors)

                # 调用 extend 处理 remote_server_contract。
                list_errors.extend(workspace_errors)

                # 校验 remote_server_contract 的设计档案分支。
                if not selected_name:

                    # 整理 remote_server_contract 需要的 selected name 设计档案信息。
                    selected_name = str(record.get("name", "")).strip()  # 设计档案值

                # 校验 remote_server_contract 的设计档案分支。
                if not selected_category:

                    # 整理 remote_server_contract 需要的 selected category 设计档案信息。
                    selected_category = str(record.get("category", "")).strip()  # 设计档案值

                # 校验 remote_server_contract 的设计档案分支。
                if not selected_functions and isinstance(record.get("functions"), list):

                    # 收集 selected functions 设计档案条目。
                    selected_functions = record.get("functions", [])  # 设计档案值

                # 校验 remote_server_contract 的设计档案分支。
                if not selected_tasks and isinstance(record.get("functions"), list):

                    # 收集 selected tasks 设计档案条目。
                    selected_tasks = normalize_remote_task_list(record.get("functions", []))  # 设计档案值

        # 校验 remote_server_contract 的设计档案分支。
        if not list_errors:

            # 收集 functions 设计档案条目。
            functions = [str(item).strip() for item in selected_functions if str(item).strip()] if isinstance(selected_functions, list) else []  # 设计档案值

            # 收集 tasks 设计档案条目。
            tasks = selected_tasks or normalize_remote_task_list(functions)  # 设计档案值

            # 校验 remote_server_contract 的设计档案分支。
            if not tasks:

                # 返回 remote_server_contract 的设计档案载荷。
                return {}, [f"use_remote_server=true requires non-empty {REMOTE_SELECTED_SERVER_TASKS_KEY} or remote server functions"]

            # 校验 remote_server_contract 的设计档案分支。
            if not list_registry and selected_id:

                # 收集 registry 设计档案条目。
                list_registry = [  # 设计档案值
                    {  # 设计档案值
                        "id": selected_id,  # 设计档案值
                        "name": selected_name,  # 设计档案值
                        "category": selected_category,  # 设计档案值
                        "functions": functions,  # 设计档案值
                        "enabled": True,  # 设计档案值
                        "validation_status": "verified",  # 设计档案值
                        "workspace_status": "ok",  # 设计档案值
                    }
                ]

                # 保存 registry map 映射，维持 remote_server_contract 的字段关系。
                registry_map = server_registry_map(list_registry)  # 设计档案值

            # 收集 routes 设计档案条目。
            list_routes = [  # 设计档案值
                {  # 设计档案值
                    "task_name": REMOTE_LEGACY_TASK_NAME,  # 设计档案值
                    "task_key": normalize_remote_task_key(REMOTE_LEGACY_TASK_NAME),  # 设计档案值
                    "primary_server_id": selected_id,  # 设计档案值
                    "fallback_server_ids": [],  # 设计档案值
                    "route_tasks": tasks,  # 设计档案值
                    "route_functions": functions,  # 设计档案值
                    "selection_confirmed": True,  # 设计档案值
                    "validation_status": "verified",  # 设计档案值
                }
            ]

    # 逐项检查 remote_server_contract 设计档案候选。
    for route in list_routes:

        # 调用 extend 处理 remote_server_contract。
        list_errors.extend(validate_route_server_ids(route, registry_map))

        # 收集 primary functions 设计档案条目。
        list_primary_functions = []  # 设计档案值

        # 整理 remote_server_contract 需要的 primary server 设计档案信息。
        primary_server = registry_map.get(str(route.get("primary_server_id", "")).strip(), {})  # 设计档案值

        # 校验 remote_server_contract 的设计档案分支。
        if isinstance(primary_server, dict):

            # 收集 primary functions 设计档案条目。
            list_primary_functions = normalize_remote_task_list(primary_server.get("functions", []))  # 设计档案值

        # 校验 remote_server_contract 的设计档案分支。
        if not route.get("route_tasks"):

            # 整理 remote_server_contract 需要的 中间载荷 设计档案信息。
            route["route_tasks"] = list_primary_functions or [str(route.get("task_name", "")).strip()]  # 设计档案值

        # 校验 remote_server_contract 的设计档案分支。
        if not route.get("route_functions"):

            # 整理 remote_server_contract 需要的 中间载荷 设计档案信息。
            route["route_functions"] = list_primary_functions  # 设计档案值

        # 整理 remote_server_contract 需要的 resolution 设计档案信息。
        resolution = resolve_remote_server_for_task(  # 设计档案值
            {  # 设计档案值
                "enabled": True,  # 设计档案值
                "server_registry": list_registry,  # 设计档案值
                "task_routes": [route],  # 设计档案值
                "unmatched_task_policy": "block-and-update-agents",  # 设计档案值
                "failover_policy": "auto-fallback",  # 设计档案值
            },  # 设计档案值
            str(route.get("task_name", "")),  # 设计档案值
            path_skill_dir,  # 设计档案值
        )

        # 校验 remote_server_contract 的设计档案分支。
        if not resolution.get("ok"):

            # 调用 extend 处理 remote_server_contract。
            list_errors.extend(resolution.get("failures", []) or [str(resolution.get("message", "remote route validation failed"))])
        else:

            # 整理 remote_server_contract 需要的 中间载荷 设计档案信息。
            route["selection_confirmed"] = True  # 设计档案值

            # 整理 remote_server_contract 需要的 中间载荷 设计档案信息。
            route["validation_status"] = "verified"  # 设计档案值

    # 校验 remote_server_contract 的设计档案分支。
    if list_errors:

        # 返回 remote_server_contract 的设计档案载荷。
        return {}, list_errors

    # 返回 remote_server_contract 的设计档案载荷。
    return {
        "enabled": True,
        "dependency_required": True,
        "dependency_status": "installed",
        "server_registry": list_registry,
        "task_routes": list_routes,
        "validation_required": True,
        "validation_status": "verified",
        "unmatched_task_policy": "block-and-update-agents",
        "failover_policy": "auto-fallback",
        "enforce_remote_task_routing": True,
    }, []

# 定义 build_profile  设计档案入口。
