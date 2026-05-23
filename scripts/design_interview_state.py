
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from design_profile_builder import *
from design_questions import *
from design_remote_gate import *
from design_review_gate import (
    answers_without_design_review,
    design_review_request,
    design_review_requires_rework,
    normalize_extra_requirements,
    validate_design_review,
)
from agents_decisions import decision_request

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

def move_to_extra_requirements(project: Path, state: dict[str, Any]) -> dict[str, Any]:
    state["status"] = "awaiting_extra_requirements"
    state.setdefault("answers", {}).pop(DESIGN_REVIEW_KEY, None)
    write_state(project, state)
    return interactive_payload(project, state)

def advance_after_remote_gate(project: Path, state: dict[str, Any]) -> dict[str, Any]:
    index = int(state.get("current_group_index", 0))
    if str(state.get("mode", "interactive")) == "takeover" and index + 1 >= len(state.get("groups", [])):
        return complete_takeover(project, state)
    if index + 1 < len(state.get("groups", [])):
        state["current_group_index"] = index + 1
        state["status"] = "collecting_group"
    else:
        return move_to_extra_requirements(project, state)
    write_state(project, state)
    return interactive_payload(project, state)

def refresh_remote_gate(project: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    answers = state.get("answers", {})
    if not isinstance(answers, dict) or not use_remote_server_enabled(answers):
        return None
    gate = remote_gate_payload(state)
    dependency = remote_dependency_summary()
    gate.update(
        {
            "enabled": True,
            "dependency_required": True,
            "dependency_status": "installed" if dependency["installed"] else "missing",
            "dependency_url": dependency["url"],
            "install_specs": dependency["install_specs"],
            "skill_dir": dependency["skill_dir"],
        }
    )
    set_remote_gate_payload(state, gate)
    if not dependency["installed"]:
        state["status"] = "awaiting_remote_install_completion" if gate.get("install_confirmed") else "awaiting_remote_install_confirmation"
        write_state(project, state)
        return interactive_payload(project, state)

    skill_dir = Path(dependency["skill_dir"])
    discover, discover_errors = remote_discover(skill_dir)
    gate["discover"] = discover
    set_remote_gate_payload(state, gate)
    if discover_errors:
        write_state(project, state)
        return interactive_payload(project, state, errors=discover_errors)
    if discover.get("status") in {"not_configured", "no_enabled_ssh"}:
        state["status"] = "awaiting_remote_configuration_completion" if gate.get("configuration_mode") in {"guided", "manual"} else "awaiting_remote_configuration_confirmation"
        write_state(project, state)
        return interactive_payload(project, state)

    choices, choice_errors = remote_choices(skill_dir)
    gate["choices"] = choices
    set_remote_gate_payload(state, gate)
    if choice_errors:
        write_state(project, state)
        return interactive_payload(project, state, errors=choice_errors)
    if choices.get("status") != "available" or not choices.get("servers"):
        state["status"] = "awaiting_remote_configuration_confirmation"
        write_state(project, state)
        return interactive_payload(project, state, errors=["erie-remote-ssh choices did not return selectable servers"])

    state["status"] = "awaiting_remote_server_route_mapping"
    write_state(project, state)
    return interactive_payload(project, state)

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
    if include_current and state.get("status") in {"awaiting_group_confirmation", "awaiting_extra_requirements", "awaiting_final_alignment", "awaiting_design_review", "completed"}:
        confirmed_indices.add(int(state.get("current_group_index", 0)))
    for index, group in enumerate(groups):
        if index in confirmed_indices and isinstance(group, list):
            keys.extend(question_ids_to_keys([str(item) for item in group]))
    return keys

def remaining_groups_for_state(state: dict[str, Any]) -> list[list[str]]:
    groups = state.get("groups", [])
    index = int(state.get("current_group_index", 0))
    if state.get("status") in {"awaiting_extra_requirements", "awaiting_final_alignment", "awaiting_design_review", "awaiting_review_rework", "completed"}:
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
    remote_gate = remote_gate_payload(state)
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
    elif status == "awaiting_extra_requirements":
        current_group = []
        questions = [
            {
                "question_id": "extra-requirements",
                "answer_key": EXTRA_REQUIREMENTS_KEY,
                "required": True,
                "branch": "all",
                "ask": "完整分组访谈已结束。是否还有额外要补充的需求、约束、风险或偏好？如果没有，请回答 none/无补充。",
                "options": [
                    {"label": "无补充", "value": "none", "description": "记录 extra_requirements=none，然后进入最终一致性确认。", "recommended": True},
                    {"label": "用户输入", "value": "__user_input__", "description": "补充内容会写入控制档案并稳定渲染到 AGENTS.md。", "recommended": False},
                ],
            }
        ]
        review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], confirmed_keys, final=False)
        confirmation_question = "请提交 extra_requirements；没有补充也必须显式记录 none。"
        next_action = "answer_extra_requirements"
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
    elif status == "awaiting_design_review":
        current_group = []
        questions = [
            {
                "question_id": "design-review",
                "answer_key": DESIGN_REVIEW_KEY,
                "required": True,
                "branch": "all",
                "ask": "最终一致性已确认。请执行代理拉起新的审查子智能体审查完整方案，并提交结构化 design_review JSON。",
                "options": [
                    {"label": "提交子智能体审查 JSON", "value": "__user_input__", "description": "必须包含 reviewer_type=subagent、verdict、findings、required_user_confirmations、两个 hash 和 review_summary。", "recommended": True},
                ],
            }
        ]
        review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], confirmed_keys, final=True)
        confirmation_question = "只有子智能体 approve、无待用户确认、且 hash 匹配时，访谈才能 completed。"
        next_action = "submit_design_review"
    elif status == "awaiting_review_rework":
        current_group = []
        questions = []
        review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], confirmed_keys, final=True)
        confirmation_question = "审查要求返工。请确认修正项并提交 review_rework_confirmed=true 加上需要修正的字段；旧 design_review 会失效，之后必须重新最终确认和子智能体审查。"
        next_action = "confirm_review_rework"
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
    elif status == "awaiting_remote_install_confirmation":
        current_group = []
        questions = [
            {
                "question_id": "remote-install",
                "answer_key": REMOTE_INSTALL_CONFIRM_KEY,
                "required": True,
                "branch": "all",
                "ask": "检测到需要远程服务器，但当前环境缺少 erie-remote-ssh。是否确认先安装该技能？如果不安装，需要把 use_remote_server 改为 false 才能继续。",
                "options": [
                    {"label": "安装技能", "value": True, "description": "确认后先完成依赖安装，再继续远程服务器选择。", "recommended": True},
                    {"label": "暂不安装", "value": False, "description": "保持阻断状态，除非把 use_remote_server 改为 false。", "recommended": False},
                ],
            }
        ]
        review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], confirmed_keys, final=False)
        confirmation_question = remote_install_command_hint(Path(remote_gate["skill_dir"])) if remote_gate.get("skill_dir") else remote_install_command_hint()
        next_action = "confirm_remote_ssh_install"
    elif status == "awaiting_remote_install_completion":
        current_group = []
        questions = []
        review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], confirmed_keys, final=False)
        confirmation_question = remote_install_command_hint(Path(remote_gate["skill_dir"])) if remote_gate.get("skill_dir") else remote_install_command_hint()
        next_action = "resume_after_remote_ssh_install"
    elif status == "awaiting_remote_configuration_confirmation":
        current_group = []
        questions = [
            {
                "question_id": "remote-config",
                "answer_key": REMOTE_CONFIGURATION_MODE_KEY,
                "required": True,
                "branch": "all",
                "ask": "当前没有可用的远程服务器列表。是否进入远程服务器配置流程？",
                "options": [
                    {"label": "guided", "value": "guided", "description": "使用 erie-remote-ssh 的 configure --interactive 走引导式配置。", "recommended": True},
                    {"label": "manual", "value": "manual", "description": "用户手动准备 server list 和 SSH 配置，然后回来继续。", "recommended": False},
                    {"label": "cancel", "value": "cancel", "description": "保持阻断状态，除非把 use_remote_server 改为 false。", "recommended": False},
                ],
            }
        ]
        review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], confirmed_keys, final=False)
        confirmation_question = "选择 guided 或 manual 后，完成服务器配置，再执行 --resume 继续。"
        next_action = "confirm_remote_server_configuration"
    elif status == "awaiting_remote_configuration_completion":
        current_group = []
        questions = []
        review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], confirmed_keys, final=False)
        command_hint = ""
        if remote_gate.get("skill_dir") and remote_gate.get("configuration_mode") == "guided":
            command_hint = remote_configure_command_hint(Path(str(remote_gate["skill_dir"])))
        confirmation_question = command_hint or "完成远程服务器配置后，执行 --resume 继续远程服务器选择。"
        next_action = "resume_after_remote_server_configuration"
    elif status == "awaiting_remote_server_route_mapping":
        current_group = []
        server_options = []
        for record in remote_gate.get("choices", {}).get("servers", []):
            if not isinstance(record, dict):
                continue
            server_options.append(
                {
                    "label": str(record.get("id", "")) or str(record.get("name", "")),
                    "value": str(record.get("id", "")) or str(record.get("name", "")),
                    "description": f"{record.get('name', '')} | {record.get('category', 'Uncategorized')} | {'; '.join(record.get('functions', [])) if isinstance(record.get('functions'), list) else ''}".strip(" |"),
                    "recommended": len(server_options) == 0,
                }
            )
        questions = [
            {
                "question_id": "remote-routes",
                "answer_key": REMOTE_SERVER_TASK_ROUTES_KEY,
                "required": True,
                "branch": "all",
                "ask": "请提交远程服务器任务主备路由表；每条路由至少包含 task_name 和 primary_server_id，可选 fallback_server_ids。所有引用的服务器都会先做 check 和 workspace-check，只有校验通过的主备路由才能写入 AGENTS.md。",
                "options": server_options,
            }
        ]
        review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], confirmed_keys, final=False)
        confirmation_question = "用 answer-file 提交 remote_server_task_routes JSON 数组，例如 task_name + primary_server_id + fallback_server_ids。"
        next_action = "map_remote_task_routes"
    else:
        # Resume the current question group when earlier answers still need completion.
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
    if status == "awaiting_remote_install_confirmation":
        payload["decision_request"] = decision_request(
            "remote_dependency_install",
            question="需要远程服务器能力，但 erie-remote-ssh 未安装。是否先安装该技能？",
            options=questions[0].get("options", []) if questions else [],
            default=True,
            risk="medium",
            next_action="install erie-remote-ssh or disable use_remote_server before continuing",
            context={"dependency": REMOTE_SSH_SKILL_NAME, "url": REMOTE_SSH_GIT_URL},
        )
    elif status == "awaiting_remote_configuration_confirmation":
        payload["decision_request"] = decision_request(
            "remote_server_configuration",
            question="当前没有可用的远程服务器列表。是否进入远程服务器配置流程？",
            options=questions[0].get("options", []) if questions else [],
            default="guided",
            risk="high",
            next_action="configure remote server access, then rerun collect_design_profile.py --resume",
            context={"remote_discover": remote_gate.get("discover", {}) if isinstance(remote_gate, dict) else {}},
        )
    elif status == "awaiting_remote_server_route_mapping":
        payload["decision_request"] = decision_request(
            "remote_server_route_mapping",
            question="请确认远程任务到服务器的主备路由后再写入 AGENTS.md。",
            options=questions[0].get("options", []) if questions else [],
            default=questions[0].get("options", [{}])[0].get("value") if questions and questions[0].get("options") else None,
            risk="high",
            next_action="submit remote_server_task_routes with primary and optional fallback server IDs",
            context={"server_count": len(questions[0].get("options", [])) if questions else 0},
        )
    elif status == "awaiting_review_rework":
        pending = state.get("pending_design_review", {}) if isinstance(state.get("pending_design_review"), dict) else {}
        payload["decision_request"] = decision_request(
            "design_review_rework",
            question="子智能体审查未批准或仍有待用户确认事项。请确认并提交修正字段后重新进入最终一致性与审查。",
            options=[
                {"label": "确认返工", "value": True, "description": "提交 review_rework_confirmed=true 和至少一个修正字段。", "recommended": True},
                {"label": "暂不继续", "value": False, "description": "保持阻断状态，不写入控制档案。", "recommended": False},
            ],
            default=True,
            risk="high",
            next_action="submit correction fields, then repeat final alignment and subagent review",
            context={
                "findings": pending.get("findings", []),
                "required_user_confirmations": pending.get("required_user_confirmations", []),
            },
        )
    else:
        payload["decision_request"] = {}
    if mode == "takeover":
        payload["takeover_trigger_reasons"] = list(state.get("takeover_trigger_reasons", []))
    if remote_gate:
        payload["remote_dependency"] = {
            "installed": bool(remote_gate.get("dependency_status") == "installed"),
            "status": remote_gate.get("dependency_status", ""),
            "url": remote_gate.get("dependency_url", REMOTE_SSH_GIT_URL),
            "install_specs": remote_gate.get("install_specs", REMOTE_SSH_INSTALL_SPECS),
        }
        if remote_gate.get("discover"):
            payload["remote_discover"] = remote_gate.get("discover")
        if remote_gate.get("choices"):
            payload["remote_server_choices"] = remote_gate.get("choices", {}).get("servers", [])
    if status == "completed":
        payload["answers_snapshot"] = dict(state.get("answers", {}))
    if status == "awaiting_design_review":
        if isinstance(state.get("design_review_request"), dict):
            payload["design_review_request"] = state["design_review_request"]
        if isinstance(state.get("profile_preview"), dict):
            payload["profile_preview"] = state["profile_preview"]
        payload["answers_for_review"] = answers_without_design_review(dict(state.get("answers", {})))
    if status == "awaiting_review_rework" and isinstance(state.get("pending_design_review"), dict):
        payload["pending_design_review"] = state["pending_design_review"]
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
    default_language = str(answers.get("default_conversation_language", "")).strip()
    local_primary = f"skills/{name_value}/" if kind == "skill" else f"engineering/{name_value}/"
    if kind == "skill":
        synthesized = {
            "development_type": "skill",
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
            "validation_gates": f"python {local_primary}scripts/quick_validate.py {local_primary.rstrip('/')}; python {local_primary}scripts/audit_skill.py {local_primary.rstrip('/')}; python {local_primary}scripts/verify_agents.py . --installed-skill-dir {local_primary.rstrip('/')}; python {local_primary}scripts/manage_docs.py verify .; python {local_primary}scripts/evaluate_skill.py {local_primary.rstrip('/')} .",
            "forward_testing_policy": "Forward-test takeover and governance repair flows with fresh fixtures before claiming readiness.",
            "development_requirements": "Force-take over the existing skill workspace, normalize structure, rebuild governance docs, and restore version-aligned AGENTS control.",
            "expected_outcome": "The existing skill workspace is reorganized under the governed structure and can be maintained through the standard agents-md-generator workflow.",
            "validation_method": "automated scripts plus user review",
            "validation_granularity": "unit tests, AGENTS verification, docs governance verification, and evaluate chain",
        }
    else:
        synthesized = {
            "development_type": "engineering",
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
            ALIGNMENT_KEY: True,
            "reference_materials": answers.get("reference_materials", ["none"]) if kind == "skill" else answers.get("reference_materials", []),
        }
    )
    synthesized.update(answers)
    if default_language:
        synthesized["default_conversation_language"] = default_language
    synthesized[ALIGNMENT_KEY] = True
    policy = git_branch_policy()
    local_primary = str(synthesized.get("local_directory_structure", local_primary)).split(",")[0].strip().rstrip("/")
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
    final_answers.pop(ALIGNMENT_KEY, None)
    final_answers.pop(DESIGN_REVIEW_KEY, None)
    state["answers"] = final_answers
    state.pop("profile_preview", None)
    return move_to_extra_requirements(project, state)

def validate_group_answers(payload: dict[str, Any], expected_keys: list[str]) -> list[str]:
    return validate_group_answers_with_optional(payload, expected_keys, expected_keys)


def validate_group_answers_with_optional(
    payload: dict[str, Any],
    expected_keys: list[str],
    required_keys: list[str],
) -> list[str]:
    provided_keys = set(payload)
    expected = set(expected_keys)
    required = set(required_keys)
    errors: list[str] = []
    extra = sorted(provided_keys - expected)
    missing = sorted(required - provided_keys)
    if extra:
        errors.append(f"out-of-group answers are not allowed for this step: {', '.join(extra)}")
    for key in missing:
        errors.append(f"missing required answer: {key}")
    for key in required_keys:
        if key in OPTIONAL_EMPTY_KEYS and key in payload:
            continue
        if key in payload and empty(payload[key]):
            errors.append(f"missing required answer: {key}")
    return errors

def answer_group(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    group_ids = current_group_ids(state)
    expected_keys = question_ids_to_keys(group_ids)
    merged_answers = dict(state.get("answers", {}))
    merged_answers.update(payload)
    required_keys = list(expected_keys)
    if any(key in expected_keys for key in REMOTE_DIRECTORY_POLICY_KEYS) and not remote_directory_policy_required(merged_answers):
        required_keys = [key for key in expected_keys if key not in REMOTE_DIRECTORY_POLICY_KEYS]
    errors = validate_group_answers_with_optional(payload, expected_keys, required_keys)
    if errors:
        emit_json(interactive_payload(project, state, errors=errors))
        raise SystemExit(1)
    answers = state.setdefault("answers", {})
    answers.update(payload)
    if any(key in expected_keys for key in REMOTE_DIRECTORY_POLICY_KEYS) and not remote_directory_policy_required(answers):
        answers.setdefault("remote_conda_environment_layout", "disabled")
        answers.setdefault("remote_run_artifact_active_layout", "disabled")
        answers.setdefault("remote_run_artifact_backup_layout", "disabled")
        answers.setdefault("remote_run_archive_trigger", "disabled")
    state["status"] = "awaiting_group_confirmation"
    write_state(project, state)
    return interactive_payload(project, state)

def disable_remote_gate_and_continue(project: Path, state: dict[str, Any]) -> dict[str, Any]:
    state.setdefault("answers", {})[USE_REMOTE_SERVER_KEY] = False
    state.pop("remote_server_gate", None)
    return advance_after_remote_gate(project, state)

def answer_remote_install_confirmation(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get(USE_REMOTE_SERVER_KEY) is False:
        return disable_remote_gate_and_continue(project, state)
    if REMOTE_INSTALL_CONFIRM_KEY not in payload or not isinstance(payload[REMOTE_INSTALL_CONFIRM_KEY], bool):
        emit_json(interactive_payload(project, state, errors=[f"{REMOTE_INSTALL_CONFIRM_KEY} must be provided as true or false"]))
        raise SystemExit(1)
    if payload[REMOTE_INSTALL_CONFIRM_KEY]:
        gate = remote_gate_payload(state)
        gate["install_confirmed"] = True
        set_remote_gate_payload(state, gate)
        state["status"] = "awaiting_remote_install_completion"
        write_state(project, state)
        return interactive_payload(project, state)
    emit_json(interactive_payload(project, state, errors=["remote server flow remains blocked until erie-remote-ssh is installed or use_remote_server is changed to false"]))
    raise SystemExit(1)

def answer_remote_configuration_confirmation(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get(USE_REMOTE_SERVER_KEY) is False:
        return disable_remote_gate_and_continue(project, state)
    mode = str(payload.get(REMOTE_CONFIGURATION_MODE_KEY, "")).strip().lower()
    if mode not in {"guided", "manual", "cancel"}:
        emit_json(interactive_payload(project, state, errors=[f"{REMOTE_CONFIGURATION_MODE_KEY} must be guided, manual, or cancel"]))
        raise SystemExit(1)
    if mode == "cancel":
        emit_json(interactive_payload(project, state, errors=["remote server flow remains blocked until configuration is completed or use_remote_server is changed to false"]))
        raise SystemExit(1)
    gate = remote_gate_payload(state)
    gate["configuration_mode"] = mode
    set_remote_gate_payload(state, gate)
    state["status"] = "awaiting_remote_configuration_completion"
    write_state(project, state)
    return interactive_payload(project, state)

def answer_remote_server_route_mapping(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get(USE_REMOTE_SERVER_KEY) is False:
        return disable_remote_gate_and_continue(project, state)
    raw_routes = payload.get(REMOTE_SERVER_TASK_ROUTES_KEY, [])
    routes = normalize_remote_task_routes(raw_routes)
    if not routes:
        emit_json(interactive_payload(project, state, errors=[f"missing required answer: {REMOTE_SERVER_TASK_ROUTES_KEY}"]))
        raise SystemExit(1)
    gate = remote_gate_payload(state)
    dependency = remote_dependency_summary()
    if not dependency["installed"]:
        emit_json(interactive_payload(project, state, errors=["remote server routes cannot be validated because erie-remote-ssh is not installed"]))
        raise SystemExit(1)
    records = gate.get("choices", {}).get("servers", [])
    if not isinstance(records, list):
        records = []
    skill_dir = Path(str(dependency["skill_dir"]))
    registry = normalize_remote_server_registry(records)
    registry_map = server_registry_map(registry)
    errors: list[str] = []
    resolved_routes: list[dict[str, Any]] = []
    validation_results: list[dict[str, Any]] = []
    for route in routes:
        errors.extend(validate_route_server_ids(route, registry_map))
        resolution = resolve_remote_server_for_task(
            {
                "enabled": True,
                "server_registry": registry,
                "task_routes": [route],
                "unmatched_task_policy": "block-and-update-agents",
                "failover_policy": "auto-fallback",
            },
            str(route.get("task_name", "")),
            skill_dir,
        )
        if not resolution.get("ok"):
            errors.extend(resolution.get("failures", []) or [str(resolution.get("message", "remote route validation failed"))])
            continue
        primary_server = registry_map.get(str(route.get("primary_server_id", "")).strip(), {})
        primary_functions = normalize_remote_task_list(primary_server.get("functions", [])) if isinstance(primary_server, dict) else []
        normalized_route = dict(route)
        if not normalized_route.get("route_tasks"):
            normalized_route["route_tasks"] = primary_functions or [str(route.get("task_name", "")).strip()]
        if not normalized_route.get("route_functions"):
            normalized_route["route_functions"] = primary_functions
        normalized_route["selection_confirmed"] = True
        normalized_route["validation_status"] = "verified"
        resolved_routes.append(normalized_route)
        validation_results.append(resolution)
    if errors:
        emit_json(interactive_payload(project, state, errors=errors))
        raise SystemExit(1)
    answers = state.setdefault("answers", {})
    answers[REMOTE_SERVER_TASK_ROUTES_KEY] = resolved_routes
    answers[REMOTE_VALIDATION_STATUS_KEY] = "verified"
    gate["server_registry"] = registry
    gate["task_routes"] = resolved_routes
    gate["route_validation_results"] = validation_results
    gate["validation_status"] = "verified"
    set_remote_gate_payload(state, gate)
    return advance_after_remote_gate(project, state)

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
            if use_remote_server_enabled(state.get("answers", {})):
                result = refresh_remote_gate(project, state)
                if result is not None:
                    return result
        if str(state.get("mode", "interactive")) == "takeover" and index + 1 >= len(state.get("groups", [])):
            return complete_takeover(project, state)
        if index + 1 < len(state.get("groups", [])):
            state["current_group_index"] = index + 1
            state["status"] = "collecting_group"
        else:
            return move_to_extra_requirements(project, state)
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

def group_index_for_key_in_state(state: dict[str, Any], answer_key: str) -> int | None:
    groups = state.get("groups", [])
    for index, group in enumerate(groups if isinstance(groups, list) else []):
        if isinstance(group, list) and answer_key in question_ids_to_keys([str(item) for item in group]):
            return index
    kind = str(state.get("kind") or state.get("answers", {}).get("development_type", "")).strip()
    if kind in {"skill", "engineering"}:
        return group_index_for_key(kind, answer_key)
    return None


def all_answer_keys_for_state(state: dict[str, Any]) -> set[str]:
    kind = str(state.get("kind") or state.get("answers", {}).get("development_type", "")).strip()
    keys = {item["answer_key"] for item in questions_for(kind)} if kind in {"skill", "engineering"} else set()
    keys.add(EXTRA_REQUIREMENTS_KEY)
    return keys


def answer_extra_requirements(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if EXTRA_REQUIREMENTS_KEY not in payload:
        emit_json(interactive_payload(project, state, errors=[f"missing required answer: {EXTRA_REQUIREMENTS_KEY}"]))
        raise SystemExit(1)
    extra = normalize_extra_requirements(payload.get(EXTRA_REQUIREMENTS_KEY))
    state.setdefault("answers", {})[EXTRA_REQUIREMENTS_KEY] = extra
    state["status"] = "awaiting_final_alignment"
    state.pop("profile_preview", None)
    state.pop("design_review_request", None)
    state.setdefault("answers", {}).pop(DESIGN_REVIEW_KEY, None)
    write_state(project, state)
    return interactive_payload(project, state)


def enter_design_review(project: Path, state: dict[str, Any], final_answers: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    final_answers.pop(DESIGN_REVIEW_KEY, None)
    state["answers"] = final_answers
    state["status"] = "awaiting_design_review"
    state["profile_preview"] = profile
    state["design_review_request"] = design_review_request(project, final_answers, profile)
    write_state(project, state)
    payload_out = interactive_payload(project, state)
    payload_out["profile_preview"] = profile
    return payload_out


def finalize_alignment(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if ALIGNMENT_KEY not in payload or not isinstance(payload[ALIGNMENT_KEY], bool):
        emit_json(interactive_payload(project, state, errors=[f"{ALIGNMENT_KEY} must be provided as true or false"]))
        raise SystemExit(1)
    correction_keys = [key for key in payload if key != ALIGNMENT_KEY]
    all_keys = all_answer_keys_for_state(state)
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
        return enter_design_review(project, state, final_answers, profile)

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
    if EXTRA_REQUIREMENTS_KEY in corrections:
        corrections[EXTRA_REQUIREMENTS_KEY] = normalize_extra_requirements(corrections[EXTRA_REQUIREMENTS_KEY])
    state.setdefault("answers", {}).update(corrections)
    state.setdefault("answers", {}).pop(DESIGN_REVIEW_KEY, None)
    indices = [group_index_for_key_in_state(state, key) for key in correction_keys if key != EXTRA_REQUIREMENTS_KEY]
    if not indices:
        state["status"] = "awaiting_final_alignment"
        write_state(project, state)
        return interactive_payload(project, state)
    target_index = min(index for index in indices if index is not None)
    state["current_group_index"] = target_index
    state["status"] = "awaiting_group_confirmation"
    state["confirmed_group_indices"] = [index for index in state.get("confirmed_group_indices", []) if int(index) < target_index]
    write_state(project, state)
    return interactive_payload(project, state)


def submit_design_review(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    review = payload.get(DESIGN_REVIEW_KEY)
    answers = dict(state.get("answers", {}))
    profile = state.get("profile_preview") if isinstance(state.get("profile_preview"), dict) else None
    errors = validate_design_review(project, answers, review, profile, require_approval=False)
    if errors:
        emit_json(interactive_payload(project, state, errors=errors))
        raise SystemExit(1)
    assert isinstance(review, dict)
    if design_review_requires_rework(review):
        state["pending_design_review"] = review
        state.setdefault("answers", {}).pop(DESIGN_REVIEW_KEY, None)
        state["status"] = "awaiting_review_rework"
        write_state(project, state)
        return interactive_payload(project, state)
    answers[DESIGN_REVIEW_KEY] = review
    profile, profile_errors = build_profile(project, answers)
    if profile_errors:
        emit_json(interactive_payload(project, state, errors=profile_errors))
        raise SystemExit(1)
    state["answers"] = answers
    state["profile_preview"] = profile
    state["status"] = "completed"
    state.pop("pending_design_review", None)
    write_state(project, state)
    payload_out = interactive_payload(project, state)
    payload_out["profile_preview"] = profile
    return payload_out


def answer_review_rework(project: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get(REVIEW_REWORK_CONFIRMATION_KEY) is not True:
        emit_json(interactive_payload(project, state, errors=[f"{REVIEW_REWORK_CONFIRMATION_KEY} must be true before rework corrections are accepted"]))
        raise SystemExit(1)
    correction_keys = [key for key in payload if key != REVIEW_REWORK_CONFIRMATION_KEY]
    if not correction_keys:
        emit_json(interactive_payload(project, state, errors=["design review rework requires at least one correction field"]))
        raise SystemExit(1)
    all_keys = all_answer_keys_for_state(state)
    if any(key not in all_keys for key in correction_keys):
        emit_json(interactive_payload(project, state, errors=["review rework corrections must reference known design-answer fields"]))
        raise SystemExit(1)
    corrections = {key: payload[key] for key in correction_keys}
    for key, value in corrections.items():
        if key in OPTIONAL_EMPTY_KEYS:
            continue
        if key == EXTRA_REQUIREMENTS_KEY:
            corrections[key] = normalize_extra_requirements(value)
            continue
        if empty(value):
            emit_json(interactive_payload(project, state, errors=[f"missing required answer: {key}"]))
            raise SystemExit(1)
    answers = state.setdefault("answers", {})
    answers.update(corrections)
    answers.pop(DESIGN_REVIEW_KEY, None)
    state.pop("pending_design_review", None)
    state.pop("design_review_request", None)
    state.pop("profile_preview", None)
    indices = [group_index_for_key_in_state(state, key) for key in correction_keys if key != EXTRA_REQUIREMENTS_KEY]
    if indices:
        target_index = min(index for index in indices if index is not None)
        state["current_group_index"] = target_index
        state["confirmed_group_indices"] = [index for index in state.get("confirmed_group_indices", []) if int(index) < target_index]
        state["status"] = "awaiting_group_confirmation"
    else:
        state["status"] = "awaiting_final_alignment"
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

def explicit_remote_server_error(answers: dict[str, Any]) -> list[str]:
    if USE_REMOTE_SERVER_KEY in answers and isinstance(answers.get(USE_REMOTE_SERVER_KEY), bool):
        return []
    return ["use_remote_server must be explicitly provided before --write"]


def explicit_extra_requirements_error(answers: dict[str, Any]) -> list[str]:
    if EXTRA_REQUIREMENTS_KEY in answers:
        return []
    return ["extra_requirements must be explicitly provided before --write"]


def ensure_design_review_approved_on_write(project: Path, answers: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    errors.extend(ensure_no_pending_interview_on_write(project, answers))
    errors.extend(explicit_remote_server_error(answers))
    errors.extend(explicit_extra_requirements_error(answers))
    if answers.get(ALIGNMENT_KEY) is not True:
        errors.append("alignment_confirmed must be true before --write")
    if DESIGN_REVIEW_KEY not in answers:
        errors.append("design_review must be provided before --write")
        return errors
    errors.extend(validate_design_review(project, answers, answers.get(DESIGN_REVIEW_KEY), profile, require_approval=True))
    return errors

def explicit_default_language_error(answers: dict[str, Any]) -> list[str]:
    if str(answers.get("default_conversation_language", "")).strip():
        return []
    return ["default_conversation_language must be explicitly provided before --write"]

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
