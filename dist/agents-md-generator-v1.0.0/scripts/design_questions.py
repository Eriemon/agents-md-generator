from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, inspect_project, resolve_project
from manage_docs import scaffold as scaffold_docs


STATE_PATH = ".agents/design-interview-state.json"
TERMINAL_STATUSES = {"completed", "completed_read_only", "abandoned"}
TAKEOVER_TERMINAL_STATUSES = {"completed", "completed_read_only", "abandoned"}
TAKEOVER_REASON_KEYS = {
    "agents_version_mismatch",
    "generator_version_mismatch",
}
REMOTE_SSH_SKILL_NAME = "erie-remote-ssh"
REMOTE_SSH_GIT_URL = "https://github.com/Eriemon/remote-ssh.git"
REMOTE_SSH_INSTALL_SPECS = [{"skill": REMOTE_SSH_SKILL_NAME, "source_path": ".", "dest_name": REMOTE_SSH_SKILL_NAME}]
USE_REMOTE_SERVER_KEY = "use_remote_server"
REMOTE_INSTALL_CONFIRM_KEY = "install_remote_ssh_dependency"
REMOTE_CONFIGURATION_MODE_KEY = "remote_server_configuration_mode"
REMOTE_SELECTED_SERVER_ID_KEY = "selected_remote_server_id"
REMOTE_SELECTED_SERVER_NAME_KEY = "selected_remote_server_name"
REMOTE_SELECTED_SERVER_CATEGORY_KEY = "selected_remote_server_category"
REMOTE_SELECTED_SERVER_FUNCTIONS_KEY = "selected_remote_server_functions"
REMOTE_SELECTED_SERVER_TASKS_KEY = "selected_remote_server_tasks"
REMOTE_SERVER_TASK_ROUTES_KEY = "remote_server_task_routes"
REMOTE_SELECTION_CONFIRMED_KEY = "remote_server_selection_confirmed"
REMOTE_VALIDATION_STATUS_KEY = "remote_server_validation_status"
REMOTE_GATE_SECTION_TITLE = "## Remote Server Contract"
REMOTE_GATE_FORCE_RULE = "When the user requests remote server validation for a registered task, you must start with that task route's primary remote server"
REMOTE_ROUTE_FORCE_RULE = "When the user requests remote server validation for a registered task, you must start with that task route's primary remote server"
REMOTE_LEGACY_TASK_NAME = "remote-validation"

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
        "ask": "生成或重构 AGENTS.md 前，必须显式确认后续默认对话语言是什么；该语言必须写入控制档案并作为 AGENTS.md 强约束，不能依赖隐式默认值。",
    },
    {
        "question_id": "45",
        "answer_key": USE_REMOTE_SERVER_KEY,
        "required": True,
        "branch": "all",
        "ask": "本次生成或重构 AGENTS.md 是否需要启用远程服务器链路？如果启用，后续必须完成依赖检查、服务器配置/选择、校验和锁定。",
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
    ("46", "remote_conda_environment_layout", "如果远端工作区需要 conda 环境，请明确该前缀环境固定放在哪里；推荐 `.conda/<env-name>/`。如果远端未配置，可保持 disabled。"),
    ("47", "remote_run_artifact_active_layout", "如果远端会产生运行产物，请明确活动运行目录结构；推荐 `runs/<run-id>/`。如果远端未配置，可保持 disabled。"),
    ("48", "remote_run_artifact_backup_layout", "如果远端会归档运行产物，请明确归档目录结构；推荐 `backups/runs/<run-id>/`。如果远端未配置，可保持 disabled。"),
    ("49", "remote_run_archive_trigger", "请明确远端运行产物何时必须从活动目录归档到 backups；推荐 `after required verification passes`。如果远端未配置，可保持 disabled。"),
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
REMOTE_DIRECTORY_POLICY_KEYS = [
    "remote_conda_environment_layout",
    "remote_run_artifact_active_layout",
    "remote_run_artifact_backup_layout",
    "remote_run_archive_trigger",
]
OPTIONAL_EMPTY_KEYS = {"engineering_rule_notes"}
ALIGNMENT_KEY = "alignment_confirmed"
GROUP_CONFIRMATION_KEY = "group_confirmed"
EXTRA_REQUIREMENTS_KEY = "extra_requirements"
DESIGN_REVIEW_KEY = "design_review"
REVIEW_REWORK_CONFIRMATION_KEY = "review_rework_confirmed"
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NO_EXTRA_REQUIREMENTS = {"", "none", "no", "no extra", "n/a", "无", "没有", "无补充", "无额外补充", "不补充", "无需补充"}

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

COMMON_GROUPS = [["1", "32", "45"]]
SKILL_GROUPS = [
    ["2", "3", "4"],
    ["5", "6", "7"],
    ["8", "9", "10"],
    ["22", "23", "24"],
    ["25", "26", "27"],
    ["28", "29", "30"],
    ["31"],
    ["42", "43", "44", "46", "47", "48", "49"],
    ["20", "21"],
]
ENGINEERING_GROUPS = [
    ["11", "12", "13"],
    ["14", "15", "16"],
    ["17", "18", "19"],
    ["33", "34", "35"],
    ["36", "37", "38"],
    ["39", "40", "41"],
    ["42", "43", "44", "46", "47", "48", "49"],
    ["20", "21"],
]
TAKEOVER_COMMON_GROUPS = [["1", "32", "45"]]
TAKEOVER_SKILL_GROUPS = [["6"], ["42", "43", "44", "46", "47", "48", "49"], ["21"]]
TAKEOVER_ENGINEERING_GROUPS = [["16"], ["42", "43", "44", "46", "47", "48", "49"], ["21"]]


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
    "remote_conda_environment_layout": [
        {"label": ".conda/<env-name>/", "value": ".conda/<env-name>/", "description": "远端 conda 前缀环境固定放在对应工作区根下。", "recommended": True},
        {"label": "disabled", "value": "disabled", "description": "远端未配置或不在本次目录治理范围内。", "recommended": False},
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入其他远端 conda 前缀目录规则。", "recommended": False},
    ],
    "remote_run_artifact_active_layout": [
        {"label": "runs/<run-id>/", "value": "runs/<run-id>/", "description": "远端运行中的活动产物按运行编号进入 runs 目录。", "recommended": True},
        {"label": "disabled", "value": "disabled", "description": "远端未配置或本次不治理运行产物。", "recommended": False},
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入其他远端活动运行目录规则。", "recommended": False},
    ],
    "remote_run_artifact_backup_layout": [
        {"label": "backups/runs/<run-id>/", "value": "backups/runs/<run-id>/", "description": "验证完成后的远端运行产物归档到 backups/runs。", "recommended": True},
        {"label": "disabled", "value": "disabled", "description": "远端未配置或本次不治理运行归档。", "recommended": False},
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入其他远端运行归档目录规则。", "recommended": False},
    ],
    "remote_run_archive_trigger": [
        {"label": "after required verification passes", "value": "after required verification passes", "description": "该仓库要求的验证门禁通过后，活动运行目录必须归档。", "recommended": True},
        {"label": "disabled", "value": "disabled", "description": "远端未配置或本次不治理运行归档触发时机。", "recommended": False},
        {"label": "用户自定义", "value": "__user_input__", "description": "由用户输入其他远端归档触发规则。", "recommended": False},
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
    USE_REMOTE_SERVER_KEY: [
        {"label": "不使用远程", "value": False, "description": "本次 AGENTS 生成不锁定远程服务器，未来如需远程验证必须先更新 AGENTS。", "recommended": True},
        {"label": "使用远程", "value": True, "description": "本次必须完成 erie-remote-ssh 依赖检查、服务器配置/选择、校验和锁定。", "recommended": False},
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

def groups_for(kind: str) -> list[list[str]]:
    if kind == "skill":
        return COMMON_GROUPS + SKILL_GROUPS
    if kind == "engineering":
        return COMMON_GROUPS + ENGINEERING_GROUPS
    raise ValueError(f"unknown kind: {kind}")

def takeover_groups_for(kind: str) -> list[list[str]]:
    if kind == "skill":
        return TAKEOVER_COMMON_GROUPS + TAKEOVER_SKILL_GROUPS
    if kind == "engineering":
        return TAKEOVER_COMMON_GROUPS + TAKEOVER_ENGINEERING_GROUPS
    raise ValueError(f"unknown kind for takeover: {kind}")

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


def normalize_extra_requirements(value: Any) -> str:
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        value = "; ".join(parts)
    normalized = str(value if value is not None else "").strip()
    return "none" if normalized.casefold() in NO_EXTRA_REQUIREMENTS else normalized


def remote_directory_configured(raw: Any) -> bool:
    value = str(raw).strip()
    if not value:
        return False
    lowered = value.lower()
    if lowered in {"none", "not configured", "disabled"}:
        return False
    if "no remote workspace is configured" in lowered:
        return False
    return True


def remote_directory_policy_required(answers: dict[str, Any] | None) -> bool:
    answers = answers or {}
    return bool(answers.get(USE_REMOTE_SERVER_KEY) is True or remote_directory_configured(answers.get("remote_directory_structure", "")))
