"""组装设计访谈状态机返回给 CLI 的交互 payload。"""

# 导入 脚本治理 所需的依赖模块。
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

# 导入 脚本治理 所需的依赖模块。
from pathlib import Path
from typing import Any

# 导入 脚本治理 所需的依赖模块。
from agents_decisions import decision_request
from design_profile_builder import review_summary
from design_questions import (
    ALIGNMENT_KEY,
    DESIGN_REVIEW_KEY,
    EXTRA_REQUIREMENTS_KEY,
    REMOTE_CONFIGURATION_MODE_KEY,

    # 分隔当前密集代码块，保留原有执行顺序。
    REMOTE_INSTALL_CONFIRM_KEY,
    REMOTE_SERVER_TASK_ROUTES_KEY,
    REMOTE_SSH_GIT_URL,
    REMOTE_SSH_INSTALL_SPECS,
    REMOTE_SSH_SKILL_NAME,
    question_ids_to_keys,

    # 再次分隔当前长代码块，降低连续语句密度。
    question_rows,
    with_options,
)
from design_remote_gate import (
    remote_configure_command_hint,
    remote_gate_payload,

    # 分隔导入清单的后续成员，避免超长连续导入块。
    remote_install_command_hint,
)
from design_review_gate import answers_without_design_review


# 定义 remote_route_mapping_step 的访谈 payload 处理入口。
def remote_route_mapping_step(
    state: dict[str, Any],
    kind: object,
    list_confirmed_keys: list[str],
    remote_gate: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any], str, str]:
    """生成远程任务路由映射阶段的交互问题和摘要。

    数组契约:
        shape/维度: 本函数处理访谈状态和远程服务器候选映射，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict、list、str 和 tuple 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义来自 remote_server_task_routes schema。
    """


    # 收集 current group 条目，保持 build_interactive_payload 的处理顺序稳定。
    list_current_group = []  # current group 用于本步治理判断

    # 收集 server options 条目，保持 build_interactive_payload 的处理顺序稳定。
    list_server_options = []  # server options 用于本步治理判断

    # 逐项推进 build_interactive_payload 的候选项检查。
    for record in remote_gate.get("choices", {}).get("servers", []):

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        if not isinstance(record, dict):

            # 分隔 build_interactive_payload 的控制流边界。
            continue

        # 服务器功能列表只在字段是列表时参与展示，避免旧格式污染提示。
        str_functions = (  # 服务器功能摘要文本
            "; ".join(record.get("functions", []))  # 多行表达式输入文本
            if isinstance(record.get("functions"), list)  # 功能字段是列表时拼接展示
            else ""  # 功能字段不是列表时不展示功能摘要
        )

        # 调用 append 完成 build_interactive_payload 的当前动作。
        list_server_options.append(
            {
                "label": str(record.get("id", "")) or str(record.get("name", "")),
                "value": str(record.get("id", "")) or str(record.get("name", "")),
                "description": (
                    f"{record.get('name', '')} | "
                    f"{record.get('category', 'Uncategorized')} | "
                    f"{str_functions}"
                ).strip(" |"),
                "recommended": len(list_server_options) == 0,
            }
        )

    # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
    list_questions = [  # questions 用于本步治理判断
        {  # questions 用于本步治理判断
            "question_id": "remote-routes",  # questions 用于本步治理判断
            "answer_key": REMOTE_SERVER_TASK_ROUTES_KEY,  # questions 用于本步治理判断
            "required": True,  # questions 用于本步治理判断
            "branch": "all",  # questions 用于本步治理判断
            "ask": (  # 远程路由问题提示文本
                "请提交远程服务器任务主备路由表；每条路由至少包含 task_name 和 primary_server_id，可选 "  # 路由表提交要求前半句
                "fallback_server_ids。所有引用的服务器都会先做 check 和 workspace-check，只有校验通过的主备路由才能写入 "  # 路由校验要求说明
                "AGENTS.md。"  # 路由写入目标说明
            ),  # questions 用于本步治理判断
            "options": list_server_options,  # questions 用于本步治理判断
        }
    ]

    # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
    review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], list_confirmed_keys, final=False)  # review 用于本步治理判断

    # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
    str_confirmation_question = "用 answer-file 提交 remote_server_task_routes JSON 数组，例如 task_name + primary_server_id + fallback_server_ids。"  # confirmation question 用于本步治理判断

    # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
    str_next_action = "map_remote_task_routes"  # next action 用于本步治理判断

    # 返回远程路由阶段的 payload 五元组。
    return list_current_group, list_questions, review, str_confirmation_question, str_next_action


# 定义 enrich_interactive_payload 的访谈 payload 处理入口。
def enrich_interactive_payload(
    dict_payload: dict[str, Any],
    status: str,
    str_mode: str,
    state: dict[str, Any],
    list_questions: list[dict[str, Any]],
    remote_gate: dict[str, Any],
) -> None:
    """补充 decision_request、远程依赖和完成态快照字段。

    数组契约:
        shape/维度: 本函数处理 payload 映射和访谈状态，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict、list 和 str 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义来自 collect_design_profile 交互 JSON 契约。
    """

    # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
    if status == "awaiting_remote_install_confirmation":

        # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
        dict_payload["decision_request"] = decision_request(  # 中间载荷 用于本步治理判断
            "remote_dependency_install",  # 中间载荷 用于本步治理判断
            question="需要远程服务器能力，但 erie-remote-ssh 未安装。是否先安装该技能？",  # 中间载荷 用于本步治理判断
            options=list_questions[0].get("options", []) if list_questions else [],  # 中间载荷 用于本步治理判断
            default=True,  # 中间载荷 用于本步治理判断
            risk="medium",  # 中间载荷 用于本步治理判断
            next_action="install erie-remote-ssh or disable use_remote_server before continuing",  # 中间载荷 用于本步治理判断
            context={"dependency": REMOTE_SSH_SKILL_NAME, "url": REMOTE_SSH_GIT_URL},  # 中间载荷 用于本步治理判断
        )

    # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
    elif status == "awaiting_remote_configuration_confirmation":

        # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
        dict_payload["decision_request"] = decision_request(  # 中间载荷 用于本步治理判断
            "remote_server_configuration",  # 中间载荷 用于本步治理判断
            question="当前没有可用的远程服务器列表。是否进入远程服务器配置流程？",  # 中间载荷 用于本步治理判断
            options=list_questions[0].get("options", []) if list_questions else [],  # 中间载荷 用于本步治理判断
            default="guided",  # 中间载荷 用于本步治理判断
            risk="high",  # 中间载荷 用于本步治理判断
            next_action="configure remote server access, then rerun collect_design_profile.py --resume",  # 中间载荷 用于本步治理判断
            context={"remote_discover": remote_gate.get("discover", {}) if isinstance(remote_gate, dict) else {}},  # 中间载荷 用于本步治理判断
        )

    # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
    elif status == "awaiting_remote_server_route_mapping":

        # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
        dict_payload["decision_request"] = decision_request(  # 中间载荷 用于本步治理判断
            "remote_server_route_mapping",  # 中间载荷 用于本步治理判断
            question="请确认远程任务到服务器的主备路由后再写入 AGENTS.md。",  # 中间载荷 用于本步治理判断
            options=list_questions[0].get("options", []) if list_questions else [],  # 中间载荷 用于本步治理判断
            default=list_questions[0].get("options", [{}])[0].get("value") if list_questions and list_questions[0].get("options") else None,  # 中间载荷 用于本步治理判断
            risk="high",  # 中间载荷 用于本步治理判断
            next_action="submit remote_server_task_routes with primary and optional fallback server IDs",  # 中间载荷 用于本步治理判断
            context={"server_count": len(list_questions[0].get("options", [])) if list_questions else 0},  # 中间载荷 用于本步治理判断
        )

    # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
    elif status == "awaiting_review_rework":

        # 保留 pending 中间值，支撑 build_interactive_payload 的当前计算步骤。
        pending = state.get("pending_design_review", {}) if isinstance(state.get("pending_design_review"), dict) else {}  # pending 用于本步治理判断

        # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
        dict_payload["decision_request"] = decision_request(  # 中间载荷 用于本步治理判断
            "design_review_rework",  # 中间载荷 用于本步治理判断
            question="子智能体审查未批准或仍有待用户确认事项。请确认并提交修正字段后重新进入最终一致性与审查。",  # 中间载荷 用于本步治理判断
            options=[  # 中间载荷 用于本步治理判断
                {"label": "确认返工", "value": True, "description": "提交 review_rework_confirmed=true 和至少一个修正字段。", "recommended": True},  # 中间载荷 用于本步治理判断
                {"label": "暂不继续", "value": False, "description": "保持阻断状态，不写入控制档案。", "recommended": False},  # 中间载荷 用于本步治理判断
            ],  # 中间载荷 用于本步治理判断
            default=True,  # 中间载荷 用于本步治理判断
            risk="high",  # 中间载荷 用于本步治理判断
            next_action="submit correction fields, then repeat final alignment and subagent review",  # 中间载荷 用于本步治理判断
            context={  # 中间载荷 用于本步治理判断
                "findings": pending.get("findings", []),  # 中间载荷 用于本步治理判断
                "required_user_confirmations": pending.get("required_user_confirmations", []),  # 中间载荷 用于本步治理判断
            },  # 中间载荷 用于本步治理判断
        )

    # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
    elif status == "completed_read_only":

        # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
        dict_payload["decision_request"] = decision_request(  # 中间载荷 用于本步治理判断
            "read_only_completed",  # 中间载荷 用于本步治理判断
            question="只读设计访谈已完成。若后续需要正式写入控制档案，请显式进入写入审查。",  # 中间载荷 用于本步治理判断
            options=[  # 中间载荷 用于本步治理判断
                {"label": "保持只读", "value": "stay_read_only", "description": "保留当前只读结果，不触发子智能体审查。", "recommended": True},  # 中间载荷 用于本步治理判断
                {"label": "申请写入审查", "value": "enter_write_review", "description": "显式切换到写入意图并生成 design_review_request。", "recommended": False},  # 中间载荷 用于本步治理判断
            ],  # 中间载荷 用于本步治理判断
            default="stay_read_only",  # 中间载荷 用于本步治理判断
            risk="medium",  # 中间载荷 用于本步治理判断
            next_action="use --enter-write-review only when the user explicitly requests a write path",  # 中间载荷 用于本步治理判断
        )
    else:

        # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
        dict_payload["decision_request"] = {}  # 中间载荷 用于本步治理判断

    # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
    if str_mode == "takeover":

        # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
        dict_payload["takeover_trigger_reasons"] = list(state.get("takeover_trigger_reasons", []))  # 中间载荷 用于本步治理判断

    # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
    if remote_gate:

        # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
        dict_payload["remote_dependency"] = {  # 中间载荷 用于本步治理判断
            "installed": bool(remote_gate.get("dependency_status") == "installed"),  # 中间载荷 用于本步治理判断
            "status": remote_gate.get("dependency_status", ""),  # 中间载荷 用于本步治理判断
            "url": remote_gate.get("dependency_url", REMOTE_SSH_GIT_URL),  # 中间载荷 用于本步治理判断
            "install_specs": remote_gate.get("install_specs", REMOTE_SSH_INSTALL_SPECS),  # 中间载荷 用于本步治理判断
        }

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        if remote_gate.get("discover"):

            # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
            dict_payload["remote_discover"] = remote_gate.get("discover")  # 中间载荷 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        if remote_gate.get("choices"):

            # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
            dict_payload["remote_server_choices"] = remote_gate.get("choices", {}).get("servers", [])  # 中间载荷 用于本步治理判断

    # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
    if status in {"completed", "completed_read_only"}:

        # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
        dict_payload["answers_snapshot"] = dict(state.get("answers", {}))  # 中间载荷 用于本步治理判断

    # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
    if status == "completed_read_only" and isinstance(state.get("profile_preview"), dict):

        # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
        dict_payload["profile_preview"] = state["profile_preview"]  # 中间载荷 用于本步治理判断

    # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
    if status == "awaiting_design_review":

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        if isinstance(state.get("design_review_request"), dict):

            # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
            dict_payload["design_review_request"] = state["design_review_request"]  # 中间载荷 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        if isinstance(state.get("profile_preview"), dict):

            # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
            dict_payload["profile_preview"] = state["profile_preview"]  # 中间载荷 用于本步治理判断

        # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
        dict_payload["answers_for_review"] = answers_without_design_review(dict(state.get("answers", {})))  # 中间载荷 用于本步治理判断

    # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
    if status == "awaiting_review_rework" and isinstance(state.get("pending_design_review"), dict):

        # 保留 中间载荷 中间值，支撑 build_interactive_payload 的当前计算步骤。
        dict_payload["pending_design_review"] = state["pending_design_review"]  # 中间载荷 用于本步治理判断



# 定义 build_interactive_payload 的脚本治理处理入口。
def build_interactive_payload(
    project: Path,
    state: dict[str, Any],
    status_override: str | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """根据访谈状态生成下一步问题、确认动作和辅助决策信息。
    
    数组契约:
        shape/维度: 本函数处理 AGENTS 状态、JSON 记录或文件路径，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict、list、str、Path 等 Python 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义以 AGENTS 治理配置和状态文件 schema 为准。
    """

    # 运行期导入状态查询函数，避免状态机入口模块和 payload 模块在导入期互相等待。
    from design_interview_state import (
        confirmed_keys_for_state,
        current_group_ids,
        normalize_intent,
        remaining_groups_for_state,
        review_policy_for_state,
        state_path,
    )

    # 收集 status 条目，保持 build_interactive_payload 的处理顺序稳定。
    status = status_override or str(state.get("status", "collecting_group"))  # status 用于本步治理判断

    # 保留 mode 中间值，支撑 build_interactive_payload 的当前计算步骤。
    str_mode = str(state.get("mode", "interactive"))  # mode 用于本步治理判断

    # 保留 intent 中间值，支撑 build_interactive_payload 的当前计算步骤。
    str_intent = normalize_intent(state.get("intent"))  # intent 用于本步治理判断

    # 收集 group ids 条目，保持 build_interactive_payload 的处理顺序稳定。
    list_group_ids = current_group_ids(state)  # group ids 用于本步治理判断

    # 保留 kind 中间值，支撑 build_interactive_payload 的当前计算步骤。
    kind = state.get("kind") or state.get("inferred_kind")  # kind 用于本步治理判断

    # 收集 confirmed keys 条目，保持 build_interactive_payload 的处理顺序稳定。
    list_confirmed_keys = confirmed_keys_for_state(state)  # confirmed keys 用于本步治理判断

    # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
    review = review_summary(state.get("answers", {}), str(kind) if kind else None)  # review 用于本步治理判断

    # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
    str_confirmation_question = ""  # confirmation question 用于本步治理判断

    # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
    str_next_action = ""  # next action 用于本步治理判断

    # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
    list_questions: list[dict[str, Any]]  # questions 用于本步治理判断

    # 收集 current group 条目，保持 build_interactive_payload 的处理顺序稳定。
    list_current_group = list_group_ids  # current group 用于本步治理判断

    # 保留 remote gate 中间值，支撑 build_interactive_payload 的当前计算步骤。
    remote_gate = remote_gate_payload(state)  # remote gate 用于本步治理判断

    # 按状态分派下一轮访谈 payload，避免长 elif 链在 AST 中形成深层嵌套。
    match status:

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "collecting_group":

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = question_rows(list_group_ids)  # questions 用于本步治理判断

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(  # review 用于本步治理判断
                state.get("answers", {}),  # review 用于本步治理判断
                str(kind) if kind else None,  # review 用于本步治理判断
                question_ids_to_keys(list_group_ids),  # review 用于本步治理判断
                list_confirmed_keys,  # review 用于本步治理判断
                final=False,  # review 用于本步治理判断
            )

            # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_confirmation_question = "请先回答当前问题组；提交后脚本会返回该组确认摘要。"  # confirmation question 用于本步治理判断

            # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_next_action = "answer_current_group"  # next action 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "awaiting_group_confirmation":

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = question_rows(list_group_ids)  # questions 用于本步治理判断

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(  # review 用于本步治理判断
                state.get("answers", {}),  # review 用于本步治理判断
                str(kind) if kind else None,  # review 用于本步治理判断
                question_ids_to_keys(list_group_ids),  # review 用于本步治理判断
                [key for key in list_confirmed_keys if key not in question_ids_to_keys(list_group_ids)],  # review 用于本步治理判断
                final=False,  # review 用于本步治理判断
            )

            # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_confirmation_question = "请确认当前问题组是否正确；如果否，请修正本组字段并重新确认。"  # confirmation question 用于本步治理判断

            # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_next_action = "confirm_current_group"  # next action 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "awaiting_extra_requirements":

            # 收集 current group 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_current_group = []  # current group 用于本步治理判断

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = [  # questions 用于本步治理判断
                {  # questions 用于本步治理判断
                    "question_id": "extra-requirements",  # questions 用于本步治理判断
                    "answer_key": EXTRA_REQUIREMENTS_KEY,  # questions 用于本步治理判断
                    "required": True,  # questions 用于本步治理判断
                    "branch": "all",  # questions 用于本步治理判断
                    "ask": "完整分组访谈已结束。是否还有额外要补充的需求、约束、风险或偏好？如果没有，请回答 none/无补充。",  # questions 用于本步治理判断
                    "options": [  # questions 用于本步治理判断
                        {"label": "无补充", "value": "none", "description": "记录 extra_requirements=none，然后进入最终一致性确认。", "recommended": True},  # questions 用于本步治理判断
                        {"label": "用户输入", "value": "__user_input__", "description": "补充内容会写入控制档案并稳定渲染到 AGENTS.md。", "recommended": False},  # questions 用于本步治理判断
                    ],  # questions 用于本步治理判断
                }
            ]

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], list_confirmed_keys, final=False)  # review 用于本步治理判断

            # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_confirmation_question = "请提交 extra_requirements；没有补充也必须显式记录 none。"  # confirmation question 用于本步治理判断

            # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_next_action = "answer_extra_requirements"  # next action 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "awaiting_final_alignment":

            # 收集 current group 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_current_group = []  # current group 用于本步治理判断

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = [  # questions 用于本步治理判断
                with_options(  # questions 用于本步治理判断
                    {  # questions 用于本步治理判断
                        "question_id": "alignment",  # questions 用于本步治理判断
                        "answer_key": ALIGNMENT_KEY,  # questions 用于本步治理判断
                        "required": True,  # questions 用于本步治理判断
                        "branch": "all",  # questions 用于本步治理判断
                        "ask": "请确认完整设计访谈已经一致；如果否，请提交需要修正的字段并重新确认。",  # questions 用于本步治理判断
                    }
                )
            ]

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(  # review 用于本步治理判断
                state.get("answers", {}),  # review 用于本步治理判断
                str(kind) if kind else None,  # review 用于本步治理判断
                [],  # review 用于本步治理判断
                [key for key in state.get("answers", {}) if key != ALIGNMENT_KEY],  # review 用于本步治理判断
                final=True,  # review 用于本步治理判断
            )

            # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_confirmation_question = "请确认整个设计访谈已经完整一致；如果需要修正，请附带修正字段重新提交。"  # confirmation question 用于本步治理判断

            # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_next_action = "confirm_final_alignment"  # next action 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "awaiting_design_review":

            # 收集 current group 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_current_group = []  # current group 用于本步治理判断

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = [  # questions 用于本步治理判断
                {  # questions 用于本步治理判断
                    "question_id": "design-review",  # questions 用于本步治理判断
                    "answer_key": DESIGN_REVIEW_KEY,  # questions 用于本步治理判断
                    "required": True,  # questions 用于本步治理判断
                    "branch": "all",  # questions 用于本步治理判断
                    "ask": "最终一致性已确认。请执行代理拉起新的审查子智能体审查完整方案，并提交结构化 design_review JSON。",  # questions 用于本步治理判断
                    "options": [  # questions 用于本步治理判断
                        {
                            "label": "提交子智能体审查 JSON",  # 交互选项字段
                            "value": "__user_input__",  # 交互选项字段
                            "description": "必须包含 reviewer_type=subagent、verdict、findings、required_user_confirmations、两个 hash 和 review_summary。",  # 交互选项字段
                            "recommended": True,  # 交互选项字段
                        },  # questions 用于本步治理判断
                    ],  # questions 用于本步治理判断
                }
            ]

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], list_confirmed_keys, final=True)  # review 用于本步治理判断

            # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_confirmation_question = "只有子智能体 approve、无待用户确认、且 hash 匹配时，访谈才能 completed。"  # confirmation question 用于本步治理判断

            # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_next_action = "submit_design_review"  # next action 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "awaiting_review_rework":

            # 收集 current group 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_current_group = []  # current group 用于本步治理判断

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = []  # questions 用于本步治理判断

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], list_confirmed_keys, final=True)  # review 用于本步治理判断

            # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_confirmation_question = "审查要求返工。请确认修正项并提交 review_rework_confirmed=true 加上需要修正的字段；旧 design_review 会失效，之后必须重新最终确认和子智能体审查。"  # confirmation question 用于本步治理判断

            # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_next_action = "confirm_review_rework"  # next action 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "completed":

            # 收集 current group 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_current_group = []  # current group 用于本步治理判断

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = []  # questions 用于本步治理判断

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(  # review 用于本步治理判断
                state.get("answers", {}),  # review 用于本步治理判断
                str(kind) if kind else None,  # review 用于本步治理判断
                [],  # review 用于本步治理判断
                [key for key in state.get("answers", {}) if key != ALIGNMENT_KEY],  # review 用于本步治理判断
                final=True,  # review 用于本步治理判断
            )

            # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
            if str_mode == "takeover":

                # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
                str_confirmation_question = "接管最小访谈已完成。将 answers_snapshot 保存为 JSON 后，使用 --answers <file> --write 写入控制档案并继续执行 takeover 整理链。"  # confirmation question 用于本步治理判断

                # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
                str_next_action = "export_answers_and_run_takeover_write"  # next action 用于本步治理判断
            else:

                # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
                str_confirmation_question = "设计访谈已完成。将 answers_snapshot 保存为 JSON 后，使用 --answers <file> --write 写入控制档案。"  # confirmation question 用于本步治理判断

                # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
                str_next_action = "export_answers_and_run_batch_write"  # next action 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "completed_read_only":

            # 收集 current group 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_current_group = []  # current group 用于本步治理判断

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = []  # questions 用于本步治理判断

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(  # review 用于本步治理判断
                state.get("answers", {}),  # review 用于本步治理判断
                str(kind) if kind else None,  # review 用于本步治理判断
                [],  # review 用于本步治理判断
                [key for key in state.get("answers", {}) if key != ALIGNMENT_KEY],  # review 用于本步治理判断
                final=True,  # review 用于本步治理判断
            )

            # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_confirmation_question = "只读设计访谈已完成。保留 answers_snapshot 和 profile_preview 供解释、规划或人工复核使用；只有显式执行写入升格后才会触发子智能体审查。"  # confirmation question 用于本步治理判断

            # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_next_action = "stay_read_only_or_enter_write_review"  # next action 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "awaiting_remote_install_confirmation":

            # 收集 current group 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_current_group = []  # current group 用于本步治理判断

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = [  # questions 用于本步治理判断
                {  # questions 用于本步治理判断
                    "question_id": "remote-install",  # questions 用于本步治理判断
                    "answer_key": REMOTE_INSTALL_CONFIRM_KEY,  # questions 用于本步治理判断
                    "required": True,  # questions 用于本步治理判断
                    "branch": "all",  # questions 用于本步治理判断
                    "ask": "检测到需要远程服务器，但当前环境缺少 erie-remote-ssh。是否确认先安装该技能？如果不安装，需要把 use_remote_server 改为 false 才能继续。",  # questions 用于本步治理判断
                    "options": [  # questions 用于本步治理判断
                        {"label": "安装技能", "value": True, "description": "确认后先完成依赖安装，再继续远程服务器选择。", "recommended": True},  # questions 用于本步治理判断
                        {"label": "暂不安装", "value": False, "description": "保持阻断状态，除非把 use_remote_server 改为 false。", "recommended": False},  # questions 用于本步治理判断
                    ],  # questions 用于本步治理判断
                }
            ]

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], list_confirmed_keys, final=False)  # review 用于本步治理判断

            # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
            path_remote_skill_dir = Path(remote_gate["skill_dir"]) if remote_gate.get("skill_dir") else None  # 远程依赖技能目录

            # 安装确认提示优先展示待安装技能目录，缺省时展示通用安装命令。
            str_confirmation_question = (  # 远程依赖安装确认提示
                remote_install_command_hint(path_remote_skill_dir)  # 多行表达式输入文本
                if path_remote_skill_dir  # 存在技能目录时展示定向安装提示
                else remote_install_command_hint()  # 缺少技能目录时展示通用安装提示
            )

            # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_next_action = "confirm_remote_ssh_install"  # next action 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "awaiting_remote_install_completion":

            # 收集 current group 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_current_group = []  # current group 用于本步治理判断

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = []  # questions 用于本步治理判断

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], list_confirmed_keys, final=False)  # review 用于本步治理判断

            # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
            path_remote_skill_dir = Path(remote_gate["skill_dir"]) if remote_gate.get("skill_dir") else None  # 远程依赖技能目录

            # 安装完成后的提示仍复用技能目录，便于用户继续原远程流程。
            str_confirmation_question = (  # 远程依赖安装后续提示
                remote_install_command_hint(path_remote_skill_dir)  # 多行表达式输入文本
                if path_remote_skill_dir  # 存在技能目录时展示定向安装提示
                else remote_install_command_hint()  # 缺少技能目录时展示通用安装提示
            )

            # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_next_action = "resume_after_remote_ssh_install"  # next action 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "awaiting_remote_configuration_confirmation":

            # 收集 current group 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_current_group = []  # current group 用于本步治理判断

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = [  # questions 用于本步治理判断
                {  # questions 用于本步治理判断
                    "question_id": "remote-config",  # questions 用于本步治理判断
                    "answer_key": REMOTE_CONFIGURATION_MODE_KEY,  # questions 用于本步治理判断
                    "required": True,  # questions 用于本步治理判断
                    "branch": "all",  # questions 用于本步治理判断
                    "ask": "当前没有可用的远程服务器列表。是否进入远程服务器配置流程？",  # questions 用于本步治理判断
                    "options": [  # questions 用于本步治理判断
                        {"label": "guided", "value": "guided", "description": "使用 erie-remote-ssh 的 configure --interactive 走引导式配置。", "recommended": True},  # questions 用于本步治理判断
                        {"label": "manual", "value": "manual", "description": "用户手动准备 server list 和 SSH 配置，然后回来继续。", "recommended": False},  # questions 用于本步治理判断
                        {"label": "cancel", "value": "cancel", "description": "保持阻断状态，除非把 use_remote_server 改为 false。", "recommended": False},  # questions 用于本步治理判断
                    ],  # questions 用于本步治理判断
                }
            ]

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], list_confirmed_keys, final=False)  # review 用于本步治理判断

            # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_confirmation_question = "选择 guided 或 manual 后，完成服务器配置，再执行 --resume 继续。"  # confirmation question 用于本步治理判断

            # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_next_action = "confirm_remote_server_configuration"  # next action 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "awaiting_remote_configuration_completion":

            # 收集 current group 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_current_group = []  # current group 用于本步治理判断

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = []  # questions 用于本步治理判断

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], list_confirmed_keys, final=False)  # review 用于本步治理判断

            # 保留 command hint 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_command_hint = ""  # command hint 用于本步治理判断

            # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
            if remote_gate.get("skill_dir") and remote_gate.get("configuration_mode") == "guided":

                # 保留 command hint 中间值，支撑 build_interactive_payload 的当前计算步骤。
                str_command_hint = remote_configure_command_hint(Path(str(remote_gate["skill_dir"])))  # command hint 用于本步治理判断

            # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_confirmation_question = str_command_hint or "完成远程服务器配置后，执行 --resume 继续远程服务器选择。"  # confirmation question 用于本步治理判断

            # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_next_action = "resume_after_remote_server_configuration"  # next action 用于本步治理判断

        # 检查 build_interactive_payload 的当前条件是否需要进入专门分支。
        case "awaiting_remote_server_route_mapping":

            # 远程路由阶段单独组装，避免主状态机承载深层候选遍历。
            # 远程路由阶段返回当前组、问题、摘要、确认提示和下一步动作。
            tuple_remote_route_step = remote_route_mapping_step(  # 远程路由阶段 payload 五元组
                state,  # 访谈状态提供已收集答案和远程选择上下文
                kind,  # 项目类型参与审查摘要生成
                list_confirmed_keys,  # 已确认字段用于排除仍需补问的设计项
                remote_gate,  # 远程门禁载荷提供服务器候选清单
            )

            # 解包当前组字段，保持主 payload 字段名不变。
            list_current_group = tuple_remote_route_step[0]  # 远程路由阶段当前组

            # 解包问题字段，保持问题数组输出契约不变。
            list_questions = tuple_remote_route_step[1]  # 远程路由阶段问题清单

            # 解包审查摘要，供 confirmed_so_far 后续复用。
            review = tuple_remote_route_step[2]  # 远程路由阶段审查摘要

            # 解包确认提示，保持 CLI 提示文本不变。
            str_confirmation_question = tuple_remote_route_step[3]  # 远程路由阶段确认提示

            # 解包下一步动作，保持状态机动作名不变。
            str_next_action = tuple_remote_route_step[4]  # 远程路由阶段下一步动作
        case _:
            # 早前回答仍未完整时，继续返回当前问题组。

            # 收集 questions 条目，保持 build_interactive_payload 的处理顺序稳定。
            list_questions = question_rows(list_group_ids)  # questions 用于本步治理判断

            # 保留 review 中间值，支撑 build_interactive_payload 的当前计算步骤。
            review = review_summary(  # review 用于本步治理判断
                state.get("answers", {}),  # review 用于本步治理判断
                str(kind) if kind else None,  # review 用于本步治理判断
                question_ids_to_keys(list_group_ids),  # review 用于本步治理判断
                list_confirmed_keys,  # review 用于本步治理判断
                final=False,  # review 用于本步治理判断
            )

            # 保留 confirmation question 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_confirmation_question = "检测到未完成的设计访谈，请先 resume 或 reset，不要静默开启新链路。"  # confirmation question 用于本步治理判断

            # 保留 next action 中间值，支撑 build_interactive_payload 的当前计算步骤。
            str_next_action = "resume_or_reset_interview"  # next action 用于本步治理判断

    # 保存 payload 映射，维持 build_interactive_payload 的字段关系。
    dict_payload: dict[str, Any] = {  # payload 用于本步治理判断
        "project": str(project),  # payload 用于本步治理判断
        "mode": str_mode,  # payload 用于本步治理判断
        "intent": str_intent,  # payload 用于本步治理判断
        "status": status,  # payload 用于本步治理判断
        "kind": kind,  # payload 用于本步治理判断
        "inferred_kind": state.get("inferred_kind"),  # payload 用于本步治理判断
        "review_policy": review_policy_for_state(state, status),  # payload 用于本步治理判断
        "current_group": list_current_group,  # payload 用于本步治理判断
        "questions": list_questions,  # payload 用于本步治理判断
        "remaining_groups": remaining_groups_for_state(state),  # payload 用于本步治理判断
        "review_summary": review,  # payload 用于本步治理判断
        "confirmed_so_far": review["confirmed_fields"],  # payload 用于本步治理判断
        "confirmation_question": str_confirmation_question,  # payload 用于本步治理判断
        "next_action": str_next_action,  # payload 用于本步治理判断
        "session_state_path": str(state_path(project)),  # payload 用于本步治理判断
        "errors": errors or [],  # payload 用于本步治理判断
    }

    # 补充 decision_request、远程依赖和完成态快照字段。
    enrich_interactive_payload(
        dict_payload,
        status,
        str_mode,
        state,
        list_questions,
        remote_gate,
    )

    # 返回 build_interactive_payload 已整理完成的调用载荷。
    return dict_payload


