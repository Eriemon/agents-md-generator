from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, resolve_project
from manage_docs import scaffold as scaffold_docs


COMMON_QUESTIONS = [
    {
        "question_id": "1",
        "answer_key": "development_type",
        "required": True,
        "branch": "all",
        "ask": "确认是技能开发还是工程开发？技能开发进入（2），工程开发进入（11）。",
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
]

EXISTING_WORK_QUESTIONS = [
    ("20", "has_existing_work", "当前工作文件夹是否已经存在工程或者技能？"),
    ("21", "directory_contract_confirmed", "如果已经存在，是否已根据内容生成并确认本地目录结构、远程目录结构和新增功能目录规则？"),
]

DIRECTORY_KEYS = [
    "local_directory_structure",
    "remote_directory_structure",
    "feature_directory_rules",
]
ALIGNMENT_KEY = "alignment_confirmed"
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
ENGINEERING_RULE_MODES = {"mini", "nano"}
ENGINEERING_RULE_SCOPES = {"project-baseline", "scoped", "on-demand"}


QUESTION_OPTIONS: dict[str, list[dict[str, Any]]] = {
    "development_type": [
        {"label": "技能开发", "value": "skill", "description": "为 Codex skill 收集设计、目录和验证契约。", "recommended": True},
        {"label": "工程开发", "value": "engineering", "description": "为普通工程仓库收集 AGENTS.md 控制档案。", "recommended": False},
    ],
    "git_management": [
        {"label": "本地 git 管理", "value": "yes-local-only", "description": "允许本地分支和提交，默认不推送远端。", "recommended": True},
        {"label": "只读不提交", "value": "read-only", "description": "代理只生成计划或文档，不执行提交。", "recommended": False},
        {"label": "允许远端协作", "value": "remote-allowed", "description": "用户明确要求时可 push 或创建 PR。", "recommended": False},
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
        {"label": "否，需要修正", "value": False, "description": "继续补问并重新摘要确认。", "recommended": False},
    ],
    "skill_design_patterns": [
        {"label": "五模式组合", "value": ["Tool Wrapper", "Generator", "Reviewer", "Inversion", "Pipeline"], "description": "脚本、模板、审查、反问和流水线都启用。", "recommended": True},
        {"label": "生成器为主", "value": ["Tool Wrapper", "Generator"], "description": "强调稳定输出和可执行脚本。", "recommended": False},
        {"label": "审查器为主", "value": ["Reviewer", "Pipeline"], "description": "强调验证、审查和顺序门禁。", "recommended": False},
    ],
    "validation_method": [
        {"label": "自动化 + 人工验收", "value": "automated scripts plus user review", "description": "脚本验证后由用户确认结果是否符合预期。", "recommended": True},
        {"label": "仅自动化", "value": "automated scripts", "description": "以测试、审计、evaluate 链为准。", "recommended": False},
        {"label": "前向测试", "value": "forward testing", "description": "用真实任务或新 fixture 验证技能行为。", "recommended": False},
    ],
    "validation_granularity": [
        {"label": "完整验证链", "value": "unit tests, AGENTS verification, skill audit, full evaluate chain", "description": "覆盖单测、AGENTS 校验、skill audit 和 evaluate。", "recommended": True},
        {"label": "最小相关验证", "value": "narrow tests plus changed-script verification", "description": "只运行与改动相关的最小验证。", "recommended": False},
    ],
}


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


def question(question_id: str, answer_key: str, ask: str, branch: str) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "answer_key": answer_key,
        "required": True,
        "branch": branch,
        "ask": ask,
        "options": QUESTION_OPTIONS.get(answer_key, default_options(answer_key)),
    }


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


def questions_for(kind: str) -> list[dict[str, Any]]:
    rows = [with_options(item) for item in COMMON_QUESTIONS]
    source = SKILL_QUESTIONS if kind == "skill" else ENGINEERING_QUESTIONS
    rows.extend(question(qid, key, ask, kind) for qid, key, ask in source)
    rows.extend(question(qid, key, ask, "all") for qid, key, ask in EXISTING_WORK_QUESTIONS)
    return rows


def read_answers(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(json.dumps({"errors": [f"could not read answers: {exc}"]}, indent=2))
    if not isinstance(data, dict):
        raise SystemExit(json.dumps({"errors": ["answers must be a JSON object"]}, indent=2))
    return data


def missing_answers(answers: dict[str, Any], kind: str) -> list[str]:
    def empty(value: Any) -> bool:
        return value is None or value == "" or value == []

    missing: list[str] = []
    for item in questions_for(kind):
        key = item["answer_key"]
        if key not in answers or empty(answers[key]):
            missing.append(key)
    if ALIGNMENT_KEY not in answers:
        missing.append(ALIGNMENT_KEY)
    if answers.get("has_existing_work") == "yes":
        for key in DIRECTORY_KEYS:
            if key not in answers or empty(answers[key]):
                missing.append(key)
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
    if not SKILL_NAME_RE.fullmatch(name):
        errors.append("skill name must use lowercase letters, digits, and hyphens only")

    expected = project / "skills" / name / "SKILL.md"
    legacy_self = project / name / "SKILL.md"
    files = discover_skill_files(project)

    if expected.exists():
        skill_name = parse_skill_name(expected)
        if skill_name != name:
            errors.append(f"SKILL.md name must match folder name: {name}")
        return {"path": f"skills/{name}", "skill_file": f"skills/{name}/SKILL.md"}, errors

    if name == "agents-md-generator" and legacy_self.exists():
        skill_name = parse_skill_name(legacy_self)
        if skill_name != name:
            errors.append(f"SKILL.md name must match folder name: {name}")
        return {"path": name, "skill_file": f"{name}/SKILL.md", "legacy_self_hosted": True}, errors

    if files and answers.get("has_existing_work") == "yes":
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


def review_summary(answers: dict[str, Any] | None, kind: str | None = None) -> dict[str, Any]:
    answers = answers or {}
    keys = [
        "development_type",
        "name",
        "skill_purpose",
        "skill_reason",
        "development_requirements",
        "expected_outcome",
        "validation_method",
        "validation_granularity",
        "project_purpose",
        "project_reason",
        "environment",
        "git_management",
        "branch_model",
        "release_contract",
        "has_existing_work",
        "directory_contract_confirmed",
    ]
    confirmed = {key: answers[key] for key in keys if key in answers}
    return {
        "kind": kind or answers.get("development_type", "unconfirmed"),
        "confirmed_fields": confirmed,
        "summary": "请用户确认以上理解是否正确；如果否，请修正对应字段后重新确认。",
    }


def attach_alignment(payload: dict[str, Any], answers: dict[str, Any] | None = None, kind: str | None = None) -> dict[str, Any]:
    payload["review_summary"] = review_summary(answers, kind)
    payload["confirmed_so_far"] = payload["review_summary"]["confirmed_fields"]
    payload["confirmation_question"] = "请确认以上理解是否正确？如果正确回答是；如果不正确回答否并指出需要修正的字段。"
    if answers is not None:
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
    elif mode not in ENGINEERING_RULE_MODES:
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
            "topic_policy": "Choose one or more lesson files from the current work content, such as testing, release, or docs governance lessons.",
        },
        "development": {
            "folder": "docs/development",
            "when": "Write records at installable release time or stage completion.",
            "file_pattern": "YYYYMMDD-HHMMSS-<stage>.md",
        },
        "install_configuration": {
            "folder": "docs/install_configuration",
            "targets": ["Codex", "Claude", "OpenClaw"],
        },
        "git_manager": {
            "folder": "docs/git_manager",
            "branch_model": "master-and-dist-release",
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
    profile = {
        "schema_version": 1,
        "kind": kind,
        "name": name,
        "purpose": purpose,
        "reason": reason,
        "alignment_confirmed": bool(answers.get(ALIGNMENT_KEY)),
        "audience_or_environment": audience,
        "reference_materials_temporary": answers.get("reference_materials", []),
        "notes": answers.get(notes_key, ""),
        "git_management": answers["git_management"],
        "branch_model": answers["branch_model"],
        "release_contract": {
            "rule": answers["release_contract"],
            "dist_folder": "dist",
            "release_folder_pattern": f"{name}-vx.x.x",
            "zip_required": True,
            "remote_push_allowed": False,
        },
        "existing_work": answers["has_existing_work"],
        "directory_contract": {
            "confirmed": bool(answers["directory_contract_confirmed"]),
            "local": answers.get("local_directory_structure", ""),
            "remote": answers.get("remote_directory_structure", ""),
            "feature_rules": answers.get("feature_directory_rules", ""),
        },
        "experience_contract": {
            "folder": "docs/experience",
            "file_pattern": "YYYY-MM-DD-<topic>.md",
            "required_each_development_conversation": True,
            "required_sections": ["background", "changes", "verification", "lessons", "reusable_experience", "risks"],
        },
        "docs_contract": docs_contract(name),
        "dir_manager_contract": dir_manager_contract(),
        "engineering_rule_contract": rule_contract,
    }
    if kind == "skill":
        profile["development_requirements"] = answers["development_requirements"]
        profile["expected_outcome"] = answers["expected_outcome"]
        profile["validation_method"] = answers["validation_method"]
        profile["validation_granularity"] = answers["validation_granularity"]
        profile["skill_layout"] = layout
        profile["skill_design_contract"] = skill_design_contract(answers)
    if kind == "engineering":
        profile["expected_outcome"] = answers["expected_outcome"]
    return profile, []


def write_profile(project: Path, profile: dict[str, Any]) -> Path:
    agents_dir = project / ".agents"
    agents_dir.mkdir(exist_ok=True)
    path = agents_dir / "agents-control.json"
    path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")
    scaffold_docs(project)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect and validate the mandatory AGENTS.md design profile.")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--kind", choices=["skill", "engineering"], default=None, help="User-confirmed development type after question 1.")
    parser.add_argument("--answers", default=None, help="JSON file containing user answers.")
    parser.add_argument("--write", action="store_true", help="Write .agents/agents-control.json and create docs governance artifacts.")
    args = parser.parse_args()
    project = resolve_project(args.project)

    if not args.answers:
        inferred = infer_kind(project)
        if not args.kind:
            emit_json(attach_alignment({
                "project": str(project),
                "inferred_kind": inferred,
                "branch_options": ["skill", "engineering"],
                "questions": [with_options(item) for item in COMMON_QUESTIONS],
                "next": "Ask question 1, then rerun with --kind skill or --kind engineering.",
            }, {"development_type": inferred}, inferred))
            return
        emit_json(attach_alignment({
            "project": str(project),
            "kind": args.kind,
            "inferred_kind": inferred,
            "questions": questions_for(args.kind),
        }, {"development_type": args.kind}, args.kind))
        return

    answers = read_answers(Path(args.answers).resolve())
    profile, errors = build_profile(project, answers)
    if errors:
        emit_json(attach_alignment({"project": str(project), "errors": errors}, answers, answers.get("development_type")))
        raise SystemExit(1)
    assert profile is not None
    result: dict[str, Any] = attach_alignment({"project": str(project), "profile": profile, "errors": []}, answers, profile.get("kind"))
    if args.write:
        if answers.get(ALIGNMENT_KEY) is not True:
            emit_json(attach_alignment({"project": str(project), "errors": ["alignment_confirmed must be true before --write"]}, answers, profile.get("kind")))
            raise SystemExit(1)
        result["written"] = str(write_profile(project, profile))
    emit_json(result)


if __name__ == "__main__":
    main()
