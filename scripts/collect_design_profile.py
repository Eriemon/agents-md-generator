from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, inspect_project, resolve_project
from manage_docs import scaffold as scaffold_docs


STATE_PATH = ".agents/design-interview-state.json"
TERMINAL_STATUSES = {"completed", "abandoned"}
TAKEOVER_TERMINAL_STATUSES = {"completed", "abandoned"}
TAKEOVER_REASON_KEYS = {
    "missing_root_agents_md",
    "missing_agents_version",
    "missing_generator_version",
    "agents_version_mismatch",
    "generator_version_mismatch",
}

COMMON_QUESTIONS = [
    {
        "question_id": "1",
        "answer_key": "development_type",
        "required": True,
        "branch": "all",
        "ask": "确认是技能开发还是工程开发？技能开发进入（2），工程开发进入（11）。",
    },
    {
        "question_id": "32",
        "answer_key": "default_conversation_language",
        "required": True,
        "branch": "all",
        "ask": "后续默认对话语言是什么？默认用中文；如需英文或其他语言，必须明确写入控制档案并作为 AGENTS.md 强约束。",
    },
]

SKILL_QUESTIONS = [
    ("2", "skill_purpose", "这个技能是干什么的？"),
    ("3", "skill_reason", "为什么要开发这个技能？"),
    ("4", "reference_materials", "这个技能有无参考资料？这些资料只是临时输入，开发完成后需要用户手动删除。"),
    ("5", "audience", "这个技能面向目标人群是什么？科研、商业、个人用户还是其他？"),
    ("6", "name", "这个技能的名称是什么？"),
    ("7", "design_notes", "这个技能的设计有无注意事项或者已有的经验？"),
    ("8", "git_management", "这个技能的设计是否要进行 git 管理，不提交远端？"),
    ("9", "branch_model", "这个技能所在文件夹是否是主分支 master，dist 文件夹中是否是 release 分支？"),
    ("10", "release_contract", "dist 文件夹中释放可安装版本文件夹是否命名为【技能名】-vx.x.x，并同步生成 zip 压缩包？"),
    ("22", "trigger_scenarios", "这个技能应该在什么用户请求、文件类型、项目状态或任务场景下触发？"),
    ("23", "skill_design_patterns", "这个技能采用哪些设计模式：Tool Wrapper、Generator、Reviewer、Inversion、Pipeline，或其他？"),
    ("24", "resource_plan", "这个技能的资源边界是什么？哪些内容进入 SKILL.md、references/、scripts/、assets/、agents/openai.yaml？"),
    ("25", "progressive_disclosure_policy", "这个技能如何保持渐进式披露，例如 SKILL.md 精简、详细规则进入 references/、资源按需加载？"),
    ("26", "validation_gates", "这个技能完成前必须运行哪些验证门禁，例如 quick_validate.py、audit、verify、evaluate 或前端/端到端检查？"),
    ("27", "forward_testing_policy", "复杂或高风险技能是否需要前向测试？如果需要，触发条件和测试方式是什么？"),
    ("28", "development_requirements", "这个技能的详细开发需求是什么？"),
    ("29", "expected_outcome", "这个技能开发完成后的预期结果是什么？"),
    ("30", "validation_method", "这个技能开发完成后如何验证？"),
    ("31", "validation_granularity", "验证方式需要达到什么颗粒度？"),
]

ENGINEERING_QUESTIONS = [
    ("11", "project_purpose", "这个工程是干什么的？"),
    ("12", "project_reason", "为什么要干这个工程？"),
    ("13", "expected_outcome", "这个工程的预期效果和目标是什么？"),
    ("14", "environment", "这个工程是在远程服务器、WSL 或者本地开发？"),
    ("15", "reusable_experience", "这个工程有无经验可以借鉴？"),
    ("16", "name", "这个工程开发的名称是什么？"),
    ("17", "git_management", "这个工程开发是否要进行 git 管理，不提交远端？"),
    ("18", "branch_model", "这个工程所在文件夹是否是主分支 master，dist 文件夹中是否是 release 分支？"),
    ("19", "release_contract", "dist 文件夹中释放可安装版本文件夹是否命名为【工程名】-vx.x.x，并同步生成 zip 压缩包？"),
    ("33", "development_requirements", "这个工程的详细开发需求是什么？"),
    ("34", "resource_plan", "这个工程的资源边界是什么？源码、脚本、测试、文档、部署和发布产物分别放在哪里？"),
    ("35", "validation_method", "这个工程开发完成后如何验证？"),
    ("36", "validation_granularity", "这个工程的验证方式需要达到什么颗粒度？"),
    ("37", "forward_testing_policy", "复杂或高风险工程改动是否需要前向测试？如果需要，触发条件和测试方式是什么？"),
    ("38", "engineering_rule_primary", "这个工程是否启用书籍化工程规则集？如果启用，选择哪一个主规则集？"),
    ("39", "engineering_rule_mode", "工程规则集使用 mini、nano，还是不启用？"),
    ("40", "engineering_rule_scope", "工程规则集作用于整个工程、局部目录，还是按需启用？"),
    ("41", "engineering_rule_notes", "工程规则集还有哪些本地经验或注意事项需要记录？"),
]

DIRECTORY_QUESTIONS = [
    ("42", "local_directory_structure", "请明确本地目录结构约定，包含主目录、tests、dist、docs 等位置。"),
    ("43", "remote_directory_structure", "请明确远程目录结构或远程部署边界；如果没有远程环境，也要明确写出没有配置。"),
    ("44", "feature_directory_rules", "请明确新增功能、脚本、文档、测试等后续内容应该进入哪些目录。"),
]

EXISTING_WORK_QUESTIONS = [
    ("20", "has_existing_work", "当前工作文件夹是否已经存在工程或者技能？"),
    ("21", "directory_contract_confirmed", "是否确认本地目录结构、远程目录结构和新增功能目录规则已经明确并固定为强控制契约？"),
]

DIRECTORY_KEYS = [
    "local_directory_structure",
    "remote_directory_structure",
    "feature_directory_rules",
]
OPTIONAL_EMPTY_KEYS = {"engineering_rule_notes"}
ALIGNMENT_KEY = "alignment_confirmed"
GROUP_CONFIRMATION_KEY = "group_confirmed"
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

ENGINEERING_RULE_SETS = {
    "a-philosophy-of-software-design",
    "clean-architecture",
    "clean-code",
    "code-complete",
    "designing-data-intensive-applications",
    "domain-driven-design",
    "domain-driven-design-distilled",
    "implementing-domain-driven-design",
    "patterns-of-enterprise-application-architecture",
    "refactoring",
    "refactoring-guru",
    "release-it",
    "the-pragmatic-programmer",
    "working-effectively-with-legacy-code",
}
ENGINEERING_RULE_MODES = {"none", "mini", "nano"}
ENGINEERING_RULE_SCOPES = {"project-baseline", "scoped", "on-demand"}

COMMON_GROUPS = [["1", "32"]]
SKILL_GROUPS = [
    ["2", "3", "4"],
    ["5", "6", "7"],
    ["8", "9", "10"],
    ["22", "23", "24"],
    ["25", "26", "27"],
    ["28", "29", "30"],
    ["31"],
    ["42", "43", "44"],
    ["20", "21"],
]
ENGINEERING_GROUPS = [
    ["11", "12", "13"],
    ["14", "15", "16"],
    ["17", "18", "19"],
    ["33", "34", "35"],
    ["36", "37", "38"],
    ["39", "40", "41"],
    ["42", "43", "44"],
    ["20", "21"],
]
TAKEOVER_COMMON_GROUPS = [["1", "32"]]
TAKEOVER_SKILL_GROUPS = [["6"]]
TAKEOVER_ENGINEERING_GROUPS = [["16"]]


QUESTION_OPTIONS: dict[str, list[dict[str, Any]]] = {
    "development_type": [
        {"label": "技能开发", "value": "skill", "description": "为 Codex skill 收集设计、目录和验证契约。", "recommended": True},
        {"label": "工程开发", "value": "engineering", "description": "为普通工程仓库收集 AGENTS.md 控制档案。", "recommended": False},
    ],
    "git_management": [
        {"label": "启用 git 管理", "value": "yes-local-only", "description": "允许本地分支和提交，默认不推送远端。", "recommended": True},
        {"label": "不启用 git 管理", "value": "no-git-management", "description": "不把 git 作为当前技能开发流程的一部分。", "recommended": False},
        {"label": "其他", "value": "__user_input__", "description": "由用户输入自定义 git 管理规则。", "recommended": False},
    ],
    "branch_model": [
        {"label": "master + dist release", "value": "master-and-dist-release", "description": "源码在 master，发布产物在 dist。", "recommended": True},
        {"label": "当前分支为准", "value": "current-branch", "description": "不固定 master，先检查当前分支。", "recommended": False},
    ],
    "release_contract": [
        {"label": "目录和 zip 同步", "value": "dist/<name>-vx.x.x plus zip", "description": "生成同名 release 目录和 zip 包。", "recommended": True},
        {"label": "暂不发布", "value": "no-release", "description": "当前阶段不定义安装包产物。", "recommended": False},
    ],
    "has_existing_work": [
        {"label": "已有项目/技能", "value": "yes", "description": "从当前文件内容生成目录和控制契约。", "recommended": True},
        {"label": "新项目/技能", "value": "no", "description": "先按计划创建结构，再生成契约。", "recommended": False},
    ],
    "directory_contract_confirmed": [
        {"label": "确认目录契约", "value": True, "description": "允许写入本地、远程、新功能目录规则。", "recommended": True},
        {"label": "暂不确认", "value": False, "description": "只输出待确认摘要，不写强控制档案。", "recommended": False},
    ],
    "alignment_confirmed": [
        {"label": "是，理解一致", "value": True, "description": "允许写入强控制档案。", "recommended": True},
        {"label": "否，需要修正", "value": False, "description": "继续修正并重新确认。", "recommended": False},
    ],
    "default_conversation_language": [
        {"label": "中文", "value": "中文", "description": "默认后续对话使用中文。", "recommended": True},
        {"label": "English", "value": "English", "description": "默认后续对话使用英文。", "recommended": False},
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入其他默认语言。", "recommended": False},
    ],
    "skill_design_patterns": [
        {"label": "五模式组合", "value": ["Tool Wrapper", "Generator", "Reviewer", "Inversion", "Pipeline"], "description": "脚本、模板、审查、反问和流水线都启用。", "recommended": True},
        {"label": "生成器为主", "value": ["Tool Wrapper", "Generator"], "description": "强调稳定输出和可执行脚本。", "recommended": False},
        {"label": "审查器为主", "value": ["Reviewer", "Pipeline"], "description": "强调验证、审查和顺序门禁。", "recommended": False},
    ],
    "validation_method": [
        {"label": "自动化 + 人工验收", "value": "automated scripts plus user review", "description": "脚本验证后由用户确认结果是否符合预期。", "recommended": True},
        {"label": "仅自动化", "value": "automated scripts", "description": "以测试、审计、evaluate 链为准。", "recommended": False},
        {"label": "前向测试", "value": "forward testing", "description": "用真实任务或新 fixture 验证行为。", "recommended": False},
    ],
    "validation_granularity": [
        {"label": "完整验证链", "value": "unit tests, AGENTS verification, skill audit, full evaluate chain", "description": "覆盖单测、AGENTS 校验、skill audit 和 evaluate。", "recommended": True},
        {"label": "最小相关验证", "value": "narrow tests plus changed-script verification", "description": "只运行与改动相关的最小验证。", "recommended": False},
    ],
    "engineering_rule_primary": [
        {"label": "不启用规则集", "value": "none", "description": "不启用书籍化工程规则集。", "recommended": True},
        {"label": "refactoring", "value": "refactoring", "description": "适合重构和设计整洁性。", "recommended": False},
        {"label": "legacy-code", "value": "working-effectively-with-legacy-code", "description": "适合遗留工程改造。", "recommended": False},
        {"label": "release-it", "value": "release-it", "description": "适合发布可靠性和交付纪律。", "recommended": False},
    ],
    "engineering_rule_mode": [
        {"label": "none", "value": "none", "description": "不启用规则集模式。", "recommended": True},
        {"label": "mini", "value": "mini", "description": "保留关键决策规则。", "recommended": False},
        {"label": "nano", "value": "nano", "description": "保留最小常驻规则。", "recommended": False},
    ],
    "engineering_rule_scope": [
        {"label": "on-demand", "value": "on-demand", "description": "按需启用规则集。", "recommended": True},
        {"label": "project-baseline", "value": "project-baseline", "description": "对整个工程提供基线约束。", "recommended": False},
        {"label": "scoped", "value": "scoped", "description": "仅作用于特定目录或场景。", "recommended": False},
    ],
}

QUESTION_MAP: dict[str, dict[str, Any]] = {}
for item in COMMON_QUESTIONS:
    QUESTION_MAP[item["question_id"]] = item
for qid, key, ask in SKILL_QUESTIONS + ENGINEERING_QUESTIONS + DIRECTORY_QUESTIONS + EXISTING_WORK_QUESTIONS:
    branch = "skill" if (qid, key, ask) in SKILL_QUESTIONS else "engineering" if (qid, key, ask) in ENGINEERING_QUESTIONS else "all"
    QUESTION_MAP[qid] = {
        "question_id": qid,
        "answer_key": key,
        "required": True,
        "branch": branch,
        "ask": ask,
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_options(answer_key: str) -> list[dict[str, Any]]:
    return [
        {
            "label": "用户输入",
            "value": "__user_input__",
            "description": f"由用户提供 `{answer_key}` 的具体内容。",
            "recommended": True,
        },
        {
            "label": "沿用仓库事实",
            "value": "__repo_fact__",
            "description": "如果仓库事实足够明确，使用探测结果作为答案。",
            "recommended": False,
        },
    ]


def with_options(item: dict[str, Any]) -> dict[str, Any]:
    row = dict(item)
    row.setdefault("options", QUESTION_OPTIONS.get(str(row.get("answer_key", "")), default_options(str(row.get("answer_key", "")))))
    return row


def infer_kind(project: Path) -> str:
    if (
        (project / "SKILL.md").exists()
        or any(path.is_file() for path in project.glob("*/SKILL.md"))
        or any(path.is_file() for path in project.glob("skills/*/SKILL.md"))
    ):
        return "skill"
    return "engineering"


def meaningful_paths(facts: dict[str, Any]) -> bool:
    files = [str(item) for item in facts.get("files", []) if str(item)]
    directories = [str(item) for item in facts.get("directories", []) if str(item)]
    ignored_files = {"AGENTS.md", ".gitignore", ".gitattributes", ".editorconfig"}
    meaningful_files = [item for item in files if item not in ignored_files and not item.startswith(".agents/")]
    meaningful_dirs = [
        item
        for item in directories
        if item
        and item not in {"docs", ".agents"}
        and not item.startswith("docs/")
        and not item.startswith(".agents/")
    ]
    return bool(meaningful_files or meaningful_dirs)


def takeover_required(project: Path) -> tuple[bool, dict[str, Any]]:
    facts = inspect_project(project)
    reasons = {str(item) for item in facts.get("root_agents_md_trigger_reasons", [])}
    triggered = bool(reasons & TAKEOVER_REASON_KEYS)
    if not triggered:
        return False, facts
    if not meaningful_paths(facts):
        return False, facts
    return True, facts


def takeover_groups_for(kind: str) -> list[list[str]]:
    if kind == "skill":
        return TAKEOVER_COMMON_GROUPS + TAKEOVER_SKILL_GROUPS
    if kind == "engineering":
        return TAKEOVER_COMMON_GROUPS + TAKEOVER_ENGINEERING_GROUPS
    raise ValueError(f"unknown kind for takeover: {kind}")


def groups_for(kind: str) -> list[list[str]]:
    if kind == "skill":
        return COMMON_GROUPS + SKILL_GROUPS
    if kind == "engineering":
        return COMMON_GROUPS + ENGINEERING_GROUPS
    raise ValueError(f"unknown kind: {kind}")


def questions_for(kind: str) -> list[dict[str, Any]]:
    return [with_options(QUESTION_MAP[qid]) for group in groups_for(kind) for qid in group]


def question_ids_to_keys(question_ids: list[str]) -> list[str]:
    return [str(QUESTION_MAP[qid]["answer_key"]) for qid in question_ids]


def question_rows(question_ids: list[str]) -> list[dict[str, Any]]:
    return [with_options(QUESTION_MAP[qid]) for qid in question_ids]


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(json.dumps({"errors": [f"could not read answers: {exc}"]}, indent=2))
    if not isinstance(data, dict):
        raise SystemExit(json.dumps({"errors": ["answers must be a JSON object"]}, indent=2))
    return data


def empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def missing_answers(answers: dict[str, Any], kind: str) -> list[str]:
    missing: list[str] = []
    for item in questions_for(kind):
        key = str(item["answer_key"])
        if key == "default_conversation_language":
            continue
        if key in OPTIONAL_EMPTY_KEYS and key in answers:
            continue
        if key not in answers or empty(answers[key]):
            missing.append(key)
    if ALIGNMENT_KEY not in answers:
        missing.append(ALIGNMENT_KEY)
    return missing


def parse_skill_name(skill_path: Path) -> str:
    text = skill_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^---\s*\n(.*?)\n---", text, flags=re.DOTALL)
    if not match:
        return ""
    for line in match.group(1).splitlines():
        if line.strip().startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return ""


def discover_skill_files(project: Path) -> list[Path]:
    skip = {".git", "dist", "ref", "__pycache__"}
    files: list[Path] = []
    for path in project.rglob("SKILL.md"):
        relative = path.relative_to(project)
        if set(relative.parts) & skip:
            continue
        files.append(path)
    return sorted(files)


def skill_layout_contract(project: Path, name: str, answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    takeover_mode = bool(answers.get("takeover_mode"))
    if not SKILL_NAME_RE.fullmatch(name):
        errors.append("skill name must use lowercase letters, digits, and hyphens only")

    expected = project / "skills" / name / "SKILL.md"
    files = discover_skill_files(project)

    if expected.exists():
        skill_name = parse_skill_name(expected)
        if skill_name != name:
            errors.append(f"SKILL.md name must match folder name: {name}")
        return {"path": f"skills/{name}", "skill_file": f"skills/{name}/SKILL.md"}, errors

    if answers.get("has_existing_work") == "yes" and not takeover_mode:
        if not files:
            errors.append("skill projects with existing work must already place the skill under skills/<skill-name>/SKILL.md")
        for skill_file in files:
            relative = skill_file.relative_to(project).as_posix()
            parts = skill_file.relative_to(project).parts
            if len(parts) >= 3 and parts[0] == "skills":
                folder = parts[1]
                skill_name = parse_skill_name(skill_file)
                if folder != name:
                    errors.append(f"skill folder must match requested skill name: skills/{name}/")
                if skill_name != folder:
                    errors.append(f"SKILL.md name must match folder name: {folder}")
            else:
                errors.append(f"skill projects must use skills/<skill-name>/SKILL.md; found {relative}")
    return {"path": f"skills/{name}", "skill_file": f"skills/{name}/SKILL.md"}, errors


def directory_layout_policy(kind: str, name: str) -> dict[str, Any]:
    primary = f"skills/{name}/" if kind == "skill" else f"engineering/{name}/"
    return {
        "primary_project_root": primary,
        "allowed_new_paths": [
            primary,
            "tests/",
            "dist/",
            "docs/",
            ".agents/",
            "ref/",
        ],
        "enforce_primary_project_root": True,
    }


def engineering_layout_contract(project: Path, name: str, answers: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = project / "engineering" / name
    if answers.get("has_existing_work") == "yes" and not expected.exists() and not bool(answers.get("takeover_mode")):
        errors.append("engineering projects with existing work must already place the project under engineering/<project-name>/")
    return errors


def summarize_fields(answers: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: answers[key] for key in keys if key in answers}


def review_summary(
    answers: dict[str, Any] | None,
    kind: str | None = None,
    current_keys: list[str] | None = None,
    confirmed_keys: list[str] | None = None,
    final: bool = False,
) -> dict[str, Any]:
    answers = answers or {}
    current_keys = current_keys or []
    confirmed_keys = confirmed_keys or []
    confirmed = summarize_fields(answers, confirmed_keys)
    current = summarize_fields(answers, current_keys)
    if final:
        summary = "请确认完整设计访谈已经一致；如需修正，请提交修正字段后重新确认。"
    elif current_keys:
        summary = "请确认当前问题组的答案是否正确；如果否，请修正本组字段并重新确认。"
    else:
        summary = "请用户确认以上理解是否正确；如果否，请修正对应字段后重新确认。"
    return {
        "kind": kind or answers.get("development_type", "unconfirmed"),
        "current_group_fields": current,
        "confirmed_fields": confirmed,
        "summary": summary,
    }


def attach_alignment(payload: dict[str, Any], answers: dict[str, Any] | None = None, kind: str | None = None) -> dict[str, Any]:
    answers = answers or {}
    confirmed_keys = [key for key in answers if key != ALIGNMENT_KEY]
    payload["review_summary"] = review_summary(answers, kind, [], confirmed_keys, final=False)
    payload["confirmed_so_far"] = payload["review_summary"]["confirmed_fields"]
    payload["confirmation_question"] = "请确认以上理解是否正确？如果正确回答是；如果不正确回答否并指出需要修正的字段。"
    payload["needs_alignment_confirmation"] = answers.get(ALIGNMENT_KEY) is not True
    return payload


def engineering_rule_contract(answers: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    primary_raw = answers.get("engineering_rule_primary", "none")
    if isinstance(primary_raw, list):
        return None, ["engineering_rule_primary must name one primary rule set, not a list"]
    primary = str(primary_raw).strip().lower() or "none"
    mode = str(answers.get("engineering_rule_mode", "none" if primary == "none" else "mini")).strip().lower()
    scope = str(answers.get("engineering_rule_scope", "on-demand")).strip().lower()
    notes = str(answers.get("engineering_rule_notes", "")).strip()

    if primary in {"", "none", "not-configured"}:
        if mode != "none":
            return None, ["engineering_rule_mode must be none when engineering_rule_primary is none"]
        return {
            "primary": "none",
            "mode": "none",
            "scope": "on-demand",
            "notes": notes,
            "full_reference_allowed_in_agents": False,
            "compatibility_policy": "no active book-derived rule set configured",
            "compression_policy": "keep only decision-changing rules in generated AGENTS.md",
        }, []

    errors: list[str] = []
    if "," in primary or "+" in primary:
        errors.append("engineering_rule_primary must choose one primary active rule set")
    if primary not in ENGINEERING_RULE_SETS:
        errors.append(f"unknown engineering_rule_primary: {primary}")
    if mode == "full":
        errors.append("full book rules must stay reference-only and must not be pasted into AGENTS.md")
    elif mode not in ENGINEERING_RULE_MODES or mode == "none":
        errors.append("engineering_rule_mode must be mini or nano")
    if scope not in ENGINEERING_RULE_SCOPES:
        errors.append("engineering_rule_scope must be project-baseline, scoped, or on-demand")
    if errors:
        return None, errors

    return {
        "primary": primary,
        "mode": mode,
        "scope": scope,
        "notes": notes,
        "full_reference_allowed_in_agents": False,
        "compatibility_policy": "one primary active rule set; use other rule sets only as scoped or on-demand guidance",
        "compression_policy": "decision-equivalent compression: keep decision-changing, trigger, tradeoff, and checklist rules",
    }, []


def normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [item.strip() for item in raw.replace("，", ",").split(",") if item.strip()]


def skill_design_contract(answers: dict[str, Any]) -> dict[str, Any]:
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


def docs_contract(name: str) -> dict[str, Any]:
    branch_policy = git_branch_policy()
    return {
        "root": "docs",
        "handoff": {
            "current": "docs/handoff/HANDOFF.md",
            "history": "docs/handoff/history_handoff",
            "archive_pattern": "HANDOFF-YYYYMMDD-HHMMSS.md",
            "required_sections": [
                "original_plan_and_steps",
                "current_step",
                "problems",
                "resolved_problems",
                "remaining_problems",
                "next_work",
                "verification_evidence",
            ],
        },
        "experience": {
            "folder": "docs/experience",
            "history": "docs/experience/history_experience",
            "summarize_every_handoffs": 5,
            "ai_generation_required": True,
            "conversation_context_limit": 10,
            "file_count": 10,
            "required_files": ["1-workflow.md", "2-scripts.md", "3-plan.md", "4-design-ui.md"],
            "optional_file_pattern": "5-xxxxx.md through 10-xxxxx.md",
            "topic_policy": "Maintain 10 project-specific numbered experience files. The first four names are fixed; choose files 5-10 from current project facts such as testing, validation, release, installation, docs governance, directory governance, or remote deployment.",
            "evolution_every_handoffs": 10,
            "evolution_templates": "assets/templates/evolution/<matching-family>/<category>/<type>/",
        },
        "development": {
            "folder": "docs/development",
            "current": "docs/development/DEVELOPMENT.md",
            "history": "docs/development/history_development",
            "history_pattern": "YYYYMMDD-HHMMSS/DEVELOPMENT.md",
            "when": "Write and iteratively refresh the latest DEVELOPMENT.md at installable release time or stage completion.",
        },
        "install_configuration": {
            "folder": "docs/install_configuration",
            "targets": ["Codex", "Claude", "OpenClaw"],
        },
        "git_manager": {
            "folder": "docs/git_manager",
            "branch_model": "master-and-dist-release",
            "branch_policy": branch_policy,
            "change_log": "docs/git_manager/CHANGELOG.md",
            "history": "docs/git_manager/history_git_manager",
            "dist_folder": "dist",
            "release_folder_pattern": f"{name}-vx.x.x",
            "zip_required": True,
        },
        "dir_manager": {
            "folder": "docs/dir_manager",
            "current_structure": "docs/dir_manager/current_structure.json",
            "planned_structure": "docs/dir_manager/planned_structure.json",
            "history": "docs/dir_manager/history_dir_manager",
            "review_required_for": ["create", "move", "delete", "rename"],
            "block_on_failed_review": True,
            "force_override_requires_user_confirmation": True,
            "archive_before_force_override": True,
        },
    }


def git_branch_policy() -> dict[str, Any]:
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
        "rule": "Before releasing an installable dist package, commit all work, merge development branches into master, record the release, and delete local branches other than master and release.",
    }


def dir_manager_contract() -> dict[str, Any]:
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


def build_profile(project: Path, answers: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    kind = answers.get("development_type", infer_kind(project))
    if kind not in {"skill", "engineering"}:
        return None, ["development_type must be skill or engineering"]
    missing = missing_answers(answers, kind)
    if missing:
        return None, [f"missing required answer: {key}" for key in missing]
    rule_contract, rule_errors = engineering_rule_contract(answers)
    if rule_errors:
        return None, rule_errors
    assert rule_contract is not None

    if kind == "skill":
        purpose = answers["skill_purpose"]
        reason = answers["skill_reason"]
        audience = answers["audience"]
        notes_key = "design_notes"
    else:
        purpose = answers["project_purpose"]
        reason = answers["project_reason"]
        audience = answers.get("environment", "")
        notes_key = "reusable_experience"

    name = str(answers["name"]).strip()
    layout: dict[str, Any] | None = None
    if kind == "skill":
        layout, layout_errors = skill_layout_contract(project, name, answers)
        if layout_errors:
            return None, layout_errors
    else:
        layout_errors = engineering_layout_contract(project, name, answers)
        if layout_errors:
            return None, layout_errors

    default_language = str(answers.get("default_conversation_language", "中文")).strip() or "中文"
    profile: dict[str, Any] = {
        "schema_version": 1,
        "kind": kind,
        "name": name,
        "default_conversation_language": default_language,
        "purpose": purpose,
        "reason": reason,
        "alignment_confirmed": bool(answers.get(ALIGNMENT_KEY)),
        "audience_or_environment": audience,
        "reference_materials_temporary": answers.get("reference_materials", []),
        "notes": answers.get(notes_key, ""),
        "git_management": answers["git_management"],
        "branch_model": answers["branch_model"],
        "git_branch_policy": git_branch_policy(),
        "release_contract": {
            "rule": answers["release_contract"],
            "dist_folder": "dist",
            "release_folder_pattern": f"{name}-vx.x.x",
            "zip_required": True,
            "receipt_file": "RELEASE_RECEIPT.json",
            "install_source_policy": "versioned-dist-release-only",
            "repo_install_validation_level": "strong",
            "external_install_validation_level": "reduced_assurance",
            "remote_push_allowed": False,
            "sanitization_required": kind == "skill",
            "sanitization_scope": "broad" if kind == "skill" else "not-applicable",
            "sanitization_mode": "auto-redact-dist-copy" if kind == "skill" else "disabled",
            "sanitization_receipt_required": kind == "skill",
        },
        "existing_work": answers["has_existing_work"],
        "directory_contract": {
            "confirmed": bool(answers["directory_contract_confirmed"]),
            "local": answers["local_directory_structure"],
            "remote": answers["remote_directory_structure"],
            "feature_rules": answers["feature_directory_rules"],
            **directory_layout_policy(kind, name),
        },
        "experience_contract": {
            "folder": "docs/experience",
            "file_pattern": "1-xxxxx.md through 10-xxxxx.md",
            "file_count": 10,
            "required_files": ["1-workflow.md", "2-scripts.md", "3-plan.md", "4-design-ui.md"],
            "project_specific_files": "5-xxxxx.md through 10-xxxxx.md are named from current project facts.",
            "summarize_every_handoffs": 5,
            "ai_generation_required": True,
            "conversation_context_limit": 10,
            "evolution_every_handoffs": 10,
            "evolution_templates": "assets/templates/evolution/<matching-family>/<category>/<type>/",
            "required_sections": [
                "evidence_read",
                "task_context",
                "how_to_apply",
                "problems_and_risks",
                "iterated_lessons",
                "next_application",
            ],
        },
        "docs_contract": docs_contract(name),
        "dir_manager_contract": dir_manager_contract(),
        "engineering_rule_contract": rule_contract,
        "development_requirements": answers["development_requirements"],
        "expected_outcome": answers["expected_outcome"],
        "validation_method": answers["validation_method"],
        "validation_granularity": answers["validation_granularity"],
        "resource_plan": answers["resource_plan"],
        "forward_testing_policy": answers["forward_testing_policy"],
    }
    primary_root = str(profile["directory_contract"].get("primary_project_root", "")).strip()
    if primary_root and isinstance(profile.get("git_branch_policy"), dict):
        profile["git_branch_policy"]["release_prepare_allowed_paths"] = [primary_root, "tests", "docs", ".agents", "AGENTS.md", "dist"]
    if kind == "skill":
        profile["skill_layout"] = layout
        profile["skill_design_contract"] = skill_design_contract(answers)
    return profile, []


def write_profile(project: Path, profile: dict[str, Any]) -> Path:
    agents_dir = project / ".agents"
    agents_dir.mkdir(exist_ok=True)
    path = agents_dir / "agents-control.json"
    path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")
    scaffold_docs(project)
    return path


def state_path(project: Path) -> Path:
    return project / STATE_PATH


def read_state(project: Path) -> dict[str, Any] | None:
    path = state_path(project)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def write_state(project: Path, state: dict[str, Any]) -> Path:
    path = state_path(project)
    path.parent.mkdir(exist_ok=True)
    state["updated_at"] = now_iso()
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
    return path


def is_active_state(state: dict[str, Any] | None) -> bool:
    return bool(state) and str(state.get("status", "")) not in TERMINAL_STATUSES


def initial_state(project: Path) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mode": "interactive",
        "status": "collecting_group",
        "project": str(project),
        "inferred_kind": infer_kind(project),
        "kind": None,
        "groups": COMMON_GROUPS,
        "current_group_index": 0,
        "answers": {},
        "confirmed_group_indices": [],
        "started_at": now_iso(),
        "updated_at": now_iso(),
    }


def initial_takeover_state(project: Path) -> dict[str, Any]:
    required, facts = takeover_required(project)
    if not required:
        raise ValueError("takeover mode requires a landed workspace with abnormal root AGENTS.md state")
    return {
        "schema_version": 1,
        "mode": "takeover",
        "status": "collecting_group",
        "project": str(project),
        "inferred_kind": infer_kind(project),
        "kind": None,
        "groups": TAKEOVER_COMMON_GROUPS,
        "current_group_index": 0,
        "answers": {},
        "confirmed_group_indices": [],
        "started_at": now_iso(),
        "updated_at": now_iso(),
        "takeover_trigger_reasons": list(facts.get("root_agents_md_trigger_reasons", [])),
        "facts_snapshot": {
            "root_agents_md_exists": facts.get("root_agents_md_exists", False),
            "root_agents_md_trigger_reasons": facts.get("root_agents_md_trigger_reasons", []),
            "structure_fix_reasons": facts.get("structure_fix_reasons", []),
            "session_history_bootstrap_required": facts.get("session_history_bootstrap_required", False),
        },
    }


def current_group_ids(state: dict[str, Any]) -> list[str]:
    groups = state.get("groups", [])
    index = int(state.get("current_group_index", 0))
    if not isinstance(groups, list) or index < 0 or index >= len(groups):
        return []
    group = groups[index]
    return [str(item) for item in group] if isinstance(group, list) else []


def confirmed_keys_for_state(state: dict[str, Any], include_current: bool = False) -> list[str]:
    keys: list[str] = []
    groups = state.get("groups", [])
    confirmed_indices = set(int(item) for item in state.get("confirmed_group_indices", []))
    if include_current and state.get("status") in {"awaiting_group_confirmation", "awaiting_final_alignment", "completed"}:
        confirmed_indices.add(int(state.get("current_group_index", 0)))
    for index, group in enumerate(groups):
        if index in confirmed_indices and isinstance(group, list):
            keys.extend(question_ids_to_keys([str(item) for item in group]))
    return keys


def remaining_groups_for_state(state: dict[str, Any]) -> list[list[str]]:
    groups = state.get("groups", [])
    index = int(state.get("current_group_index", 0))
    if state.get("status") in {"awaiting_final_alignment", "completed"}:
        return []
    return [[str(item) for item in group] for group in groups[index:]] if isinstance(groups, list) else []


def interactive_payload(
    project: Path,
    state: dict[str, Any],
    status_override: str | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    status = status_override or str(state.get("status", "collecting_group"))
    mode = str(state.get("mode", "interactive"))
    group_ids = current_group_ids(state)
    kind = state.get("kind") or state.get("inferred_kind")
    confirmed_keys = confirmed_keys_for_state(state)
    review = review_summary(state.get("answers", {}), str(kind) if kind else None)
    confirmation_question = ""
    next_action = ""
    questions: list[dict[str, Any]]
    current_group = group_ids
    if status == "collecting_group":
        questions = question_rows(group_ids)
        review = review_summary(
            state.get("answers", {}),
            str(kind) if kind else None,
            question_ids_to_keys(group_ids),
            confirmed_keys,
            final=False,
        )
        confirmation_question = "请先回答当前问题组；提交后脚本会返回该组确认摘要。"
        next_action = "answer_current_group"
    elif status == "awaiting_group_confirmation":
        questions = question_rows(group_ids)
        review = review_summary(
            state.get("answers", {}),
            str(kind) if kind else None,
            question_ids_to_keys(group_ids),
            [key for key in confirmed_keys if key not in question_ids_to_keys(group_ids)],
            final=False,
        )
        confirmation_question = "请确认当前问题组是否正确；如果否，请修正本组字段并重新确认。"
        next_action = "confirm_current_group"
    elif status == "awaiting_final_alignment":
        current_group = []
        questions = [
            with_options(
                {
                    "question_id": "alignment",
                    "answer_key": ALIGNMENT_KEY,
                    "required": True,
                    "branch": "all",
                    "ask": "请确认完整设计访谈已经一致；如果否，请提交需要修正的字段并重新确认。",
                }
            )
        ]
        review = review_summary(
            state.get("answers", {}),
            str(kind) if kind else None,
            [],
            [key for key in state.get("answers", {}) if key != ALIGNMENT_KEY],
            final=True,
        )
        confirmation_question = "请确认整个设计访谈已经完整一致；如果需要修正，请附带修正字段重新提交。"
        next_action = "confirm_final_alignment"
    elif status == "completed":
        current_group = []
        questions = []
        review = review_summary(
            state.get("answers", {}),
            str(kind) if kind else None,
            [],
            [key for key in state.get("answers", {}) if key != ALIGNMENT_KEY],
            final=True,
        )
        if mode == "takeover":
            confirmation_question = "接管最小访谈已完成。将 answers_snapshot 保存为 JSON 后，使用 --answers <file> --write 写入控制档案并继续执行 takeover 整理链。"
            next_action = "export_answers_and_run_takeover_write"
        else:
            confirmation_question = "设计访谈已完成。将 answers_snapshot 保存为 JSON 后，使用 --answers <file> --write 写入控制档案。"
            next_action = "export_answers_and_run_batch_write"
    else:  # resume_required
        questions = question_rows(group_ids)
        review = review_summary(
            state.get("answers", {}),
            str(kind) if kind else None,
            question_ids_to_keys(group_ids),
            confirmed_keys,
            final=False,
        )
        confirmation_question = "检测到未完成的设计访谈，请先 resume 或 reset，不要静默开启新链路。"
        next_action = "resume_or_reset_interview"

    payload: dict[str, Any] = {
        "project": str(project),
        "mode": mode,
        "status": status,
        "kind": kind,
        "inferred_kind": state.get("inferred_kind"),
        "current_group": current_group,
        "questions": questions,
        "remaining_groups": remaining_groups_for_state(state),
        "review_summary": review,
        "confirmed_so_far": review["confirmed_fields"],
        "confirmation_question": confirmation_question,
        "next_action": next_action,
        "session_state_path": str(state_path(project)),
        "errors": errors or [],
    }
    if mode == "takeover":
        payload["takeover_trigger_reasons"] = list(state.get("takeover_trigger_reasons", []))
    if status == "completed":
        payload["answers_snapshot"] = dict(state.get("answers", {}))
    return payload


def update_groups_after_common_confirmation(state: dict[str, Any]) -> None:
    kind = str(state.get("answers", {}).get("development_type", "")).strip()
    if kind not in {"skill", "engineering"}:
        raise ValueError("development_type must be skill or engineering after common confirmation")
    state["kind"] = kind
    if str(state.get("mode", "interactive")) == "takeover":
        state["groups"] = takeover_groups_for(kind)
    else:
        state["groups"] = groups_for(kind)


def autogenerated_takeover_answers(project: Path, state: dict[str, Any]) -> dict[str, Any]:
    answers = dict(state.get("answers", {}))
    kind = str(state.get("kind") or answers.get("development_type") or infer_kind(project)).strip()
    name_key = "name"
    if kind == "skill":
        name_value = str(answers.get(name_key) or answers.get("name") or "takeover-skill").strip()
    else:
        name_value = str(answers.get(name_key) or answers.get("name") or "takeover-project").strip()
    default_language = str(answers.get("default_conversation_language", "中文")).strip() or "中文"
    takeover_facts = inspect_project(project)
    remote_structure = "not configured"
    local_primary = f"skills/{name_value}/" if kind == "skill" else f"engineering/{name_value}/"
    if kind == "skill":
        synthesized = {
            "development_type": "skill",
            "default_conversation_language": default_language,
            "name": name_value,
            "skill_purpose": f"Take over and govern the existing `{name_value}` skill workspace.",
            "skill_reason": "Root AGENTS.md is missing or outdated, so the workspace must be brought under strict governance immediately.",
            "reference_materials": ["none"],
            "audience": "existing workspace maintainers",
            "design_notes": "This control profile was generated by takeover mode from repository facts and minimal user confirmation.",
            "trigger_scenarios": "Use when an existing skill workspace needs AGENTS.md takeover, governance repair, or version-aligned regeneration.",
            "skill_design_patterns": ["Tool Wrapper", "Generator", "Reviewer", "Inversion", "Pipeline"],
            "resource_plan": f"{local_primary} for skill source, tests/ for verification, dist/ for release packages, docs/ for governance, and .agents/ for control state.",
            "progressive_disclosure_policy": "Keep SKILL.md concise, move detailed policy into references/, and let scripts own deterministic governance work.",
            "validation_gates": "quick_validate.py, audit_skill.py, verify_agents.py, manage_docs.py verify, evaluate_skill.py",
            "forward_testing_policy": "Forward-test takeover and governance repair flows with fresh fixtures before claiming readiness.",
            "development_requirements": "Force-take over the existing skill workspace, normalize structure, rebuild governance docs, and restore version-aligned AGENTS control.",
            "expected_outcome": "The existing skill workspace is reorganized under the governed structure and can be maintained through the standard agents-md-generator workflow.",
            "validation_method": "automated scripts plus user review",
            "validation_granularity": "unit tests, AGENTS verification, docs governance verification, and evaluate chain",
        }
    else:
        synthesized = {
            "development_type": "engineering",
            "default_conversation_language": default_language,
            "name": name_value,
            "project_purpose": f"Take over and govern the existing `{name_value}` engineering workspace.",
            "project_reason": "Root AGENTS.md is missing or outdated, so the engineering workspace must be reorganized and brought under strict governance.",
            "reusable_experience": "This control profile was generated by takeover mode from repository facts and minimal user confirmation.",
            "development_requirements": "Force-take over the existing engineering workspace, normalize the local directory structure, and rebuild governance records without a full design interview.",
            "expected_outcome": "The engineering workspace is reorganized under the governed project root and all AGENTS/docs governance gates become enforceable.",
            "environment": "local",
            "resource_plan": f"{local_primary} for source and project files, tests/ for verification, dist/ for release artifacts, docs/ for governance, and .agents/ for control state.",
            "validation_method": "automated scripts plus user review",
            "validation_granularity": "unit tests, AGENTS verification, docs governance verification, and evaluate chain",
            "forward_testing_policy": "Forward-test takeover restructuring and governance repair with fresh engineering fixtures before claiming readiness.",
            "engineering_rule_primary": "none",
            "engineering_rule_mode": "none",
            "engineering_rule_scope": "on-demand",
            "engineering_rule_notes": "",
        }
    synthesized.update(
        {
            "git_management": "yes-local-only",
            "branch_model": "master-and-dist-release",
            "release_contract": f"dist/{name_value}-vx.x.x plus zip",
            "has_existing_work": "yes",
            "takeover_mode": True,
            "local_directory_structure": f"{local_primary}, tests/, dist/, docs/experience/, docs/dir_manager/, .agents/",
            "remote_directory_structure": remote_structure,
            "feature_directory_rules": f"Place main project content under `{local_primary}`, keep tests under `tests/`, release artifacts under `dist/`, and governance records under `docs/`.",
            "directory_contract_confirmed": True,
            ALIGNMENT_KEY: True,
            "reference_materials": answers.get("reference_materials", ["none"]) if kind == "skill" else answers.get("reference_materials", []),
        }
    )
    synthesized.update(answers)
    synthesized[ALIGNMENT_KEY] = True
    synthesized["remote_directory_structure"] = answers.get("remote_directory_structure") or remote_structure
    policy = git_branch_policy()
    local_primary = synthesized["local_directory_structure"].split(",")[0].strip().rstrip("/")
    policy["release_prepare_allowed_paths"] = [local_primary, "tests", "docs", ".agents", "AGENTS.md", "dist"]
    synthesized["git_branch_policy"] = policy
    takeover_reasons = list(state.get("takeover_trigger_reasons", []))
    if kind == "skill":
        synthesized["design_notes"] = f"{synthesized['design_notes']} Takeover reasons: {', '.join(takeover_reasons) or 'workspace takeover required'}."
    else:
        synthesized["reusable_experience"] = f"{synthesized['reusable_experience']} Takeover reasons: {', '.join(takeover_reasons) or 'workspace takeover required'}."
    return synthesized


def complete_takeover(project: Path, state: dict[str, Any]) -> dict[str, Any]:
    final_answers = autogenerated_takeover_answers(project, state)
    profile, errors = build_profile(project, final_answers)
    if errors:
        emit_json(interactive_payload(project, state, errors=errors))
        raise SystemExit(1)
    state["answers"] = final_answers
    state["status"] = "completed"
    state["profile_preview"] = profile
    write_state(project, state)
    payload_out = interactive_payload(project, state)
    payload_out["profile_preview"] = profile
    return payload_out


def validate_group_answers(payload: dict[str, Any], expected_keys: list[str]) -> list[str]:
    provided_keys = set(payload)
    expected = set(expected_keys)
    errors: list[str] = []
    extra = sorted(provided_keys - expected)
    missing = sorted(expected - provided_keys)
    if extra:
        errors.append(f"out-of-group answers are not allowed for this step: {', '.join(extra)}")
    for key in missing:
        errors.append(f"missing required answer: {key}")
    for key in expected_keys:
        if key in OPTIONAL_EMPTY_KEYS and key in payload:
            continue
        if key in payload and empty(payload[key]):
            errors.append(f"missing required answer: {key}")
    return errors


def answer_group(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    group_ids = current_group_ids(state)
    expected_keys = question_ids_to_keys(group_ids)
    errors = validate_group_answers(payload, expected_keys)
    if errors:
        emit_json(interactive_payload(project, state, errors=errors))
        raise SystemExit(1)
    state.setdefault("answers", {}).update(payload)
    state["status"] = "awaiting_group_confirmation"
    write_state(project, state)
    return interactive_payload(project, state)


def confirm_group(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if GROUP_CONFIRMATION_KEY not in payload or not isinstance(payload[GROUP_CONFIRMATION_KEY], bool):
        emit_json(interactive_payload(project, state, errors=[f"{GROUP_CONFIRMATION_KEY} must be provided as true or false"]))
        raise SystemExit(1)
    correction_keys = [key for key in payload if key != GROUP_CONFIRMATION_KEY]
    group_ids = current_group_ids(state)
    expected_keys = question_ids_to_keys(group_ids)
    if any(key not in expected_keys for key in correction_keys):
        emit_json(interactive_payload(project, state, errors=["group corrections must stay within the current group"]))
        raise SystemExit(1)

    if payload[GROUP_CONFIRMATION_KEY]:
        if correction_keys:
            emit_json(interactive_payload(project, state, errors=["confirmed groups cannot carry extra correction fields in the same submission"]))
            raise SystemExit(1)
        index = int(state.get("current_group_index", 0))
        confirmed = set(int(item) for item in state.get("confirmed_group_indices", []))
        confirmed.add(index)
        state["confirmed_group_indices"] = sorted(confirmed)
        if index == 0 and state.get("kind") is None:
            update_groups_after_common_confirmation(state)
        if str(state.get("mode", "interactive")) == "takeover" and index + 1 >= len(state.get("groups", [])):
            return complete_takeover(project, state)
        if index + 1 < len(state.get("groups", [])):
            state["current_group_index"] = index + 1
            state["status"] = "collecting_group"
        else:
            state["status"] = "awaiting_final_alignment"
        write_state(project, state)
        return interactive_payload(project, state)

    if correction_keys:
        errors = validate_group_answers({key: payload[key] for key in correction_keys}, correction_keys)
        if errors:
            emit_json(interactive_payload(project, state, errors=errors))
            raise SystemExit(1)
        state.setdefault("answers", {}).update({key: payload[key] for key in correction_keys})
        state["status"] = "awaiting_group_confirmation"
    else:
        state["status"] = "collecting_group"
    write_state(project, state)
    return interactive_payload(project, state)


def group_index_for_key(kind: str, answer_key: str) -> int | None:
    for index, group in enumerate(groups_for(kind)):
        if answer_key in question_ids_to_keys(group):
            return index
    return None


def finalize_alignment(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if ALIGNMENT_KEY not in payload or not isinstance(payload[ALIGNMENT_KEY], bool):
        emit_json(interactive_payload(project, state, errors=[f"{ALIGNMENT_KEY} must be provided as true or false"]))
        raise SystemExit(1)
    correction_keys = [key for key in payload if key != ALIGNMENT_KEY]
    kind = str(state.get("kind") or state.get("answers", {}).get("development_type", "")).strip()
    all_keys = {item["answer_key"] for item in questions_for(kind)}
    if any(key not in all_keys for key in correction_keys):
        emit_json(interactive_payload(project, state, errors=["alignment corrections must reference known design-answer fields"]))
        raise SystemExit(1)

    if payload[ALIGNMENT_KEY]:
        if correction_keys:
            emit_json(interactive_payload(project, state, errors=["final alignment confirmation cannot include extra correction fields in the same submission"]))
            raise SystemExit(1)
        final_answers = dict(state.get("answers", {}))
        final_answers[ALIGNMENT_KEY] = True
        profile, errors = build_profile(project, final_answers)
        if errors:
            emit_json(interactive_payload(project, state, errors=errors))
            raise SystemExit(1)
        state["answers"] = final_answers
        state["status"] = "completed"
        state["profile_preview"] = profile
        write_state(project, state)
        payload_out = interactive_payload(project, state)
        payload_out["profile_preview"] = profile
        return payload_out

    if not correction_keys:
        emit_json(interactive_payload(project, state, errors=["alignment rejection requires correction fields or --reset-interview"]))
        raise SystemExit(1)

    corrections = {key: payload[key] for key in correction_keys}
    for key, value in corrections.items():
        if key in OPTIONAL_EMPTY_KEYS:
            continue
        if empty(value):
            emit_json(interactive_payload(project, state, errors=[f"missing required answer: {key}"]))
            raise SystemExit(1)
    state.setdefault("answers", {}).update(corrections)
    indices = [group_index_for_key(kind, key) for key in correction_keys]
    target_index = min(index for index in indices if index is not None)
    state["current_group_index"] = target_index
    state["status"] = "awaiting_group_confirmation"
    state["confirmed_group_indices"] = [index for index in state.get("confirmed_group_indices", []) if int(index) < target_index]
    write_state(project, state)
    return interactive_payload(project, state)


def ensure_no_pending_interview_on_write(project: Path, answers: dict[str, Any]) -> list[str]:
    state = read_state(project)
    if not is_active_state(state):
        return []
    state_answers = state.get("answers", {}) if isinstance(state, dict) else {}
    if state_answers == {key: answers[key] for key in state_answers if key in answers} and state.get("status") == "completed":
        return []
    return ["design interview is still pending; use --resume or --reset-interview before --write"]


def legacy_question_payload(project: Path, kind: str | None) -> dict[str, Any]:
    inferred = infer_kind(project)
    if not kind:
        return attach_alignment(
            {
                "project": str(project),
                "inferred_kind": inferred,
                "branch_options": ["skill", "engineering"],
                "questions": [with_options(item) for item in COMMON_QUESTIONS],
                "next": "Ask question 1, then rerun with --kind skill or --kind engineering.",
            },
            {"development_type": inferred},
            inferred,
        )
    return attach_alignment(
        {
            "project": str(project),
            "kind": kind,
            "inferred_kind": inferred,
            "questions": questions_for(kind),
            "question_groups": groups_for(kind),
        },
        {"development_type": kind},
        kind,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect and validate the mandatory AGENTS.md design profile.")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--kind", choices=["skill", "engineering"], default=None, help="Legacy flat-question output for the confirmed branch.")
    parser.add_argument("--answers", default=None, help="JSON file containing the full aligned answer set.")
    parser.add_argument("--answer-file", default=None, help="JSON file containing answers for the current interactive interview step.")
    parser.add_argument("--write", action="store_true", help="Write .agents/agents-control.json and create docs governance artifacts.")
    parser.add_argument("--start", action="store_true", help="Start or restart the grouped interactive design interview.")
    parser.add_argument("--start-takeover", action="store_true", help="Start the minimal takeover interview for an old workspace that lacks a healthy root AGENTS.md.")
    parser.add_argument("--resume", action="store_true", help="Resume the current unfinished grouped interactive design interview.")
    parser.add_argument("--resume-takeover", action="store_true", help="Resume the current unfinished takeover interview.")
    parser.add_argument("--reset-interview", action="store_true", help="Abandon the current interactive design interview so a new one can start.")
    args = parser.parse_args()
    project = resolve_project(args.project)

    if args.write and not args.answers:
        emit_json({"project": str(project), "errors": ["--write requires --answers <file>"]})
        raise SystemExit(1)

    if args.start or args.start_takeover:
        state = read_state(project)
        if is_active_state(state):
            emit_json(interactive_payload(project, state or initial_state(project), status_override="resume_required"))
            return
        if args.start_takeover:
            try:
                state = initial_takeover_state(project)
            except ValueError as exc:
                emit_json({"project": str(project), "mode": "takeover", "errors": [str(exc)]})
                raise SystemExit(1)
        else:
            required, _ = takeover_required(project)
            if required:
                state = initial_takeover_state(project)
            else:
                state = initial_state(project)
        write_state(project, state)
        emit_json(interactive_payload(project, state))
        return

    if args.resume or args.resume_takeover:
        state = read_state(project)
        if not is_active_state(state):
            emit_json({"project": str(project), "mode": "interactive", "errors": ["no active design interview state to resume"]})
            raise SystemExit(1)
        if args.resume_takeover and str(state.get("mode", "interactive")) != "takeover":
            emit_json({"project": str(project), "mode": "takeover", "errors": ["no active takeover interview state to resume"]})
            raise SystemExit(1)
        emit_json(interactive_payload(project, state))
        return

    if args.reset_interview:
        state = read_state(project)
        if not state:
            emit_json({"project": str(project), "mode": "interactive", "status": "abandoned", "errors": [], "session_state_path": str(state_path(project))})
            return
        state["status"] = "abandoned"
        write_state(project, state)
        emit_json({"project": str(project), "mode": "interactive", "status": "abandoned", "errors": [], "session_state_path": str(state_path(project))})
        return

    if args.answer_file:
        state = read_state(project)
        if not is_active_state(state):
            emit_json({"project": str(project), "mode": "interactive", "errors": ["no active design interview state; run --start first"]})
            raise SystemExit(1)
        payload = read_json_object(Path(args.answer_file).resolve())
        status = str(state.get("status", "collecting_group"))
        if status == "collecting_group":
            emit_json(answer_group(project, state, payload))
            return
        if status == "awaiting_group_confirmation":
            emit_json(confirm_group(project, state, payload))
            return
        if status == "awaiting_final_alignment":
            emit_json(finalize_alignment(project, state, payload))
            return
        emit_json(interactive_payload(project, state, errors=[f"cannot answer interview in status: {status}"]))
        raise SystemExit(1)

    if not args.answers:
        emit_json(legacy_question_payload(project, args.kind))
        return

    answers = read_json_object(Path(args.answers).resolve())
    profile, errors = build_profile(project, answers)
    if errors:
        emit_json(attach_alignment({"project": str(project), "errors": errors}, answers, answers.get("development_type")))
        raise SystemExit(1)
    assert profile is not None
    result: dict[str, Any] = attach_alignment({"project": str(project), "profile": profile, "errors": []}, answers, profile.get("kind"))
    if args.write:
        pending_errors = ensure_no_pending_interview_on_write(project, answers)
        if pending_errors:
            payload = attach_alignment({"project": str(project), "errors": pending_errors}, answers, profile.get("kind"))
            state = read_state(project)
            if state:
                payload["pending_interview"] = interactive_payload(project, state, status_override="resume_required")
            emit_json(payload)
            raise SystemExit(1)
        if answers.get(ALIGNMENT_KEY) is not True:
            emit_json(attach_alignment({"project": str(project), "errors": ["alignment_confirmed must be true before --write"]}, answers, profile.get("kind")))
            raise SystemExit(1)
        result["written"] = str(write_profile(project, profile))
    emit_json(result)


if __name__ == "__main__":
    main()
