"""组装设计访谈状态机返回给 CLI 的交互 payload。"""

# 延迟注解求值，保持模块按文件规格加载时的类型兼容性。
from __future__ import annotations

# 标准库提供路径和结构化业务类型注解。
from pathlib import Path
from typing import Any

# 设计访谈依赖提供决策、预览、问题和远程门禁合同。
from agents_decisions import decision_request
from design_profile_builder import review_summary
from design_questions import (
    ALIGNMENT_KEY,
    DESIGN_REVIEW_KEY,
    EXTRA_REQUIREMENTS_KEY,
    REMOTE_CONFIGURATION_MODE_KEY,

    # 第一段继续整理交互载荷。
    REMOTE_INSTALL_CONFIRM_KEY,
    REMOTE_SERVER_TASK_ROUTES_KEY,

    # 远程技能来源和安装规格用于构建依赖确认载荷。
    REMOTE_SSH_GIT_URL,
    REMOTE_SSH_INSTALL_SPECS,
    REMOTE_SSH_SKILL_NAME,

    # 问题辅助函数负责标识转换、记录展开和选项补齐。
    question_ids_to_keys,
    question_rows,
    with_options,
)

# 远程门禁辅助函数生成配置、安装和候选服务器提示。
from design_remote_gate import (
    remote_configure_command_hint,
    remote_gate_payload,
    remote_install_command_hint,
)

# 设计复核辅助函数剥离不可参与答案哈希的审查字段。
from design_review_gate import answers_without_design_review

# 统一构造交互选项，避免各状态分支重复维护字段形状。
def interactive_option(
    str_label: str,
    value: Any,
    str_description: str,
    is_recommended: bool,
) -> dict[str, Any]:
    """构造设计访谈使用的标准选项记录。

    参数：str_label 为展示标签，value 为提交值，str_description 为选择影响，is_recommended 为推荐标志。
    返回：包含 label、value、description 和 recommended 的 JSON 兼容映射。

    数组契约:
        shape/维度: 本函数处理单个选项记录，不接收数值数组。
        dtype/类型: 字段由 str、bool 和 JSON 兼容值约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段语义遵循交互选项 schema。
    """

    # 返回固定字段顺序的标准交互选项。
    return dict(label=str_label, value=value, description=str_description, recommended=is_recommended)

# 从远程候选问题中提取默认服务器标识。
def first_question_option_value(list_questions: list[dict[str, Any]]) -> Any:
    """读取首个问题的首个候选值。

    参数：list_questions 为当前交互问题记录。
    返回：首个候选项的 value；问题或候选项缺失时返回 None。

    数组契约:
        shape/维度: 输入为一维问题记录列表，不处理数值数组。
        dtype/类型: 元素为 JSON 兼容映射，返回值遵循候选项 value 类型。
        unit/单位: 无物理量单位，元素语义遵循交互问题 schema。
    """

    # 无问题时不存在可用默认值。
    if not list_questions:

        # 返回空默认值维持决策请求合同。
        return None

    # 第一题候选项决定远程路由的默认服务器。
    list_options = list_questions[0].get("options", [])  # 提取第一题候选项

    # 无候选项时不推断默认服务器。
    if not list_options:

        # 返回空默认值避免访问不存在的首项。
        return None

    # 返回首个候选项声明的稳定提交值。
    return list_options[0].get("value")

# 生成没有当前问题键的阶段复核摘要。
def stage_review(
    state: dict[str, Any],
    kind: object,
    list_confirmed_keys: list[str],
    is_final: bool,
) -> Any:
    """汇总远程门禁或设计审查阶段的确认状态。

    参数：state 为访谈状态，kind 为项目类型，list_confirmed_keys 为已确认答案键，is_final 控制最终摘要语义。
    返回：符合设计访谈 review_summary schema 的复核映射。

    数组契约:
        shape/维度: 已确认键为一维业务列表，不处理数值数组。
        dtype/类型: 元素为 str，输出为 JSON 兼容映射，非 ndarray dtype。
        unit/单位: 无物理量单位，字段语义遵循复核摘要 schema。
    """

    # 无当前问题键的阶段直接复用公共摘要生成器。
    return review_summary(
        state.get("answers", {}),
        str(kind) if kind else None,
        [],
        list_confirmed_keys,
        final=is_final,
    )

# 生成远程任务路由映射阶段的交互载荷片段。
def remote_route_mapping_step(
    state: dict[str, Any],
    kind: object,
    list_confirmed_keys: list[str],
    remote_gate: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any], str, str]:
    """生成远程任务路由映射阶段的交互问题和摘要。

    参数：state 为当前访谈状态，kind 为项目类型，list_confirmed_keys 为已确认答案键，remote_gate 为远程门禁载荷。
    返回：当前问题组、问题记录、复核摘要、确认提示和下一动作组成的五元组。

    数组契约:
        shape/维度: 本函数处理访谈状态和远程服务器候选映射，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict、list、str 和 tuple 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义来自 remote_server_task_routes schema。
    """

    # 第一项来源
    list_current_group = []  # 第一项载荷

    # 第二项来源
    list_server_options = []  # 第二项载荷

    # 第二步遍历候选。
    for record in remote_gate.get("choices", {}).get("servers", []):

        # 第三步判断状态。
        if not isinstance(record, dict):

            # 第四步跳过无效项。
            continue

        # 第三项来源
        str_functions = (  # 第三项载荷
            "; ".join(record.get("functions", []))  # 第二百二十三项结构字段
            if isinstance(record.get("functions"), list)  # 第二百四十六项结构字段
            else ""  # 第二百六十九项结构字段
        )

        # 第五步更新载荷。
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

    # 第四项来源
    list_questions = [  # 第四项载荷
        {
            "question_id": "remote-routes",  # 第二百二十二项结构字段
            "answer_key": REMOTE_SERVER_TASK_ROUTES_KEY,  # 第二百四十五项结构字段
            "required": True,  # 第二百六十八项结构字段
            "branch": "all",  # 第二百八十九项结构字段
            "ask": (  # 第三百四项结构字段
                "请提交远程服务器任务主备路由表；每条路由至少包含 task_name 和 primary_server_id，可选 "
                "fallback_server_ids。所有引用的服务器都会先做 check 和 workspace-check，只有校验通过的主备路由才能写入 "
                "AGENTS.md。"
            ),
            "options": list_server_options,  # 第三百十六项结构字段
        }
    ]

    # 第五项来源
    review = review_summary(state.get("answers", {}), str(kind) if kind else None, [], list_confirmed_keys, final=False)  # 第五项载荷

    # 第六项来源
    str_confirmation_question = (  # 第六项载荷
        "用 answer-file 提交 remote_server_task_routes JSON 数组，例如 task_name + "
        "primary_server_id + fallback_server_ids。"
    )

    # 第七项来源
    str_next_action = "map_remote_task_routes"  # 第七项载荷

    # 第六步返回载荷。
    return list_current_group, list_questions, review, str_confirmation_question, str_next_action

# 为基础交互载荷补齐状态专属字段。
def enrich_interactive_payload(
    dict_payload: dict[str, Any],
    status: str,
    str_mode: str,
    state: dict[str, Any],
    list_questions: list[dict[str, Any]],
    remote_gate: dict[str, Any],
) -> None:
    """补充 decision_request、远程依赖和完成态快照字段。

    参数：dict_payload 为待补充载荷，status 为访谈状态，str_mode 为交互模式，state 为状态记录，list_questions 为当前问题，remote_gate 为远程门禁载荷。
    返回：无；函数就地更新 dict_payload。

    数组契约:
        shape/维度: 本函数处理 payload 映射和访谈状态，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict、list 和 str 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义来自 collect_design_profile 交互 JSON 契约。
    """

    # 第七步判断状态。
    if status == "awaiting_remote_install_confirmation":

        # 第八项来源
        dict_payload["decision_request"] = decision_request(  # 第八项载荷
            "remote_dependency_install",  # 第二百二十一项结构字段
            question="需要远程服务器能力，但 erie-remote-ssh 未安装。是否先安装该技能？",  # 第二百四十四项结构字段
            options=list_questions[0].get("options", []) if list_questions else [],  # 第二百六十七项结构字段
            default=True,  # 第二百八十八项载荷表达式
            risk="medium",  # 第三百三项结构字段
            next_action="install erie-remote-ssh or disable use_remote_server before continuing",  # 第三百十五项结构字段
            context={"dependency": REMOTE_SSH_SKILL_NAME, "url": REMOTE_SSH_GIT_URL},  # 第三百二十六项结构字段
        )

    # 第八步切换状态。
    elif status == "awaiting_remote_configuration_confirmation":

        # 第九项来源
        dict_payload["decision_request"] = decision_request(  # 第九项载荷
            "remote_server_configuration",  # 载荷片段阶段一
            question="当前没有可用的远程服务器列表。是否进入远程服务器配置流程？",  # 第二百四十三项结构字段
            options=list_questions[0].get("options", []) if list_questions else [],  # 第二百六十六项结构字段
            default="guided",  # 第二百八十七项结构字段
            risk="high",  # 第三百二项结构字段
            next_action="configure remote server access, then rerun collect_design_profile.py --resume",  # 第三百十四项结构字段
            context={"remote_discover": remote_gate.get("discover", {}) if isinstance(remote_gate, dict) else {}},  # 决策上下文阶段二
        )

    # 第九步切换状态。
    elif status == "awaiting_remote_server_route_mapping":

        # 第十项来源
        dict_payload["decision_request"] = decision_request(  # 第十项载荷
            "remote_server_route_mapping",  # 第二百十九项结构字段
            question="请确认远程任务到服务器的主备路由后再写入 AGENTS.md。",  # 第二百四十二项结构字段
            options=list_questions[0].get("options", []) if list_questions else [],  # 第二百六十五项结构字段
            default=first_question_option_value(list_questions),  # 第二百八十六项结构字段
            risk="high",  # 第三百一项结构字段
            next_action="submit remote_server_task_routes with primary and optional fallback server IDs",  # 后续动作阶段三
            context={"server_count": len(list_questions[0].get("options", [])) if list_questions else 0},  # 决策上下文阶段四
        )

    # 第十步切换状态。
    elif status == "awaiting_review_rework":

        # 第十一项来源
        pending = state.get("pending_design_review", {}) if isinstance(state.get("pending_design_review"), dict) else {}  # 第十一项载荷

        # 第十二项来源
        dict_payload["decision_request"] = decision_request(  # 第十二项载荷
            "design_review_rework",  # 第二百十八项结构字段
            question="子智能体审查未批准或仍有待用户确认事项。请确认并提交修正字段后重新进入最终一致性与审查。",  # 第二百四十一项结构字段
            options=[  # 第二百六十四项载荷表达式
                interactive_option(  # 第二百八十五项结构字段
                    "确认返工",  # 提供返工选项标签
                    True,  # 提交返工确认值
                    "提交 review_rework_confirmed=true 和至少一个修正字段。",  # 说明返工输入合同
                    True,  # 默认建议继续修正
                ),
                {"label": "暂不继续", "value": False, "description": "保持阻断状态，不写入控制档案。", "recommended": False},  # 暂不继续保持阻断状态阶段五
            ],
            default=True,  # 第三百十二项载荷表达式
            risk="high",  # 载荷片段阶段六
            next_action="submit correction fields, then repeat final alignment and subagent review",  # 后续动作阶段七
            context={  # 第三百三十七项载荷表达式
                "findings": pending.get("findings", []),  # 第三百四十项结构字段
                "required_user_confirmations": pending.get("required_user_confirmations", []),  # 载荷片段阶段八
            },
        )

    # 第十一步切换状态。
    elif status == "completed_read_only":

        # 第十三项来源
        dict_payload["decision_request"] = decision_request(  # 第十三项载荷
            "read_only_completed",  # 载荷片段阶段九
            question="只读设计访谈已完成。若后续需要正式写入控制档案，请显式进入写入审查。",  # 只读设计访谈已完成若阶段十
            options=[  # 第二百六十三项载荷表达式
                {"label": "保持只读", "value": "stay_read_only", "description": "保留当前只读结果，不触发子智能体审查。", "recommended": True},  # 第二百八十四项结构字段
                interactive_option(  # 申请写入审查显式切换阶段十一
                    "申请写入审查",  # 提供写入升格标签
                    "enter_write_review",  # 提交写入升格动作
                    "显式切换到写入意图并生成 design_review_request。",  # 说明升格副作用
                    False,  # 默认保持只读边界
                ),
            ],
            default="stay_read_only",  # 载荷片段阶段十二
            risk="medium",  # 第三百二十二项结构字段
            next_action="use --enter-write-review only when the user explicitly requests a write path",  # 第三百三十二项结构字段
        )

    # 第十二步处理兜底。
    else:

        # 第十四项来源
        dict_payload["decision_request"] = {}  # 第十四项载荷

    # 第十三步判断状态。
    if str_mode == "takeover":

        # 第十五项来源
        dict_payload["takeover_trigger_reasons"] = list(state.get("takeover_trigger_reasons", []))  # 第十五项载荷

    # 第十四步判断状态。
    if remote_gate:

        # 第十六项来源
        dict_payload["remote_dependency"] = {  # 第十六项载荷
            "installed": bool(remote_gate.get("dependency_status") == "installed"),  # 载荷片段阶段十三
            "status": remote_gate.get("dependency_status", ""),  # 访谈状态阶段十四
            "url": remote_gate.get("dependency_url", REMOTE_SSH_GIT_URL),  # 第二百六十二项结构字段
            "install_specs": remote_gate.get("install_specs", REMOTE_SSH_INSTALL_SPECS),  # 第二百八十三项结构字段
        }

        # 第十五步判断状态。
        if remote_gate.get("discover"):

            # 第十七项来源
            dict_payload["remote_discover"] = remote_gate.get("discover")  # 第十七项载荷

        # 第十六步判断状态。
        if remote_gate.get("choices"):

            # 第十八项来源
            dict_payload["remote_server_choices"] = remote_gate.get("choices", {}).get("servers", [])  # 第十八项载荷

    # 第十七步判断状态。
    if status in {"completed", "completed_read_only"}:

        # 第十九项来源
        dict_payload["answers_snapshot"] = dict(state.get("answers", {}))  # 第十九项载荷

    # 第十八步判断状态。
    if status == "completed_read_only" and isinstance(state.get("profile_preview"), dict):

        # 第二十项来源
        dict_payload["profile_preview"] = state["profile_preview"]  # 第二十项载荷

    # 第十九步判断状态。
    if status == "awaiting_design_review":

        # 第二十步判断状态。
        if isinstance(state.get("design_review_request"), dict):

            # 第二十一项来源
            dict_payload["design_review_request"] = state["design_review_request"]  # 第二十一项载荷

        # 完成态附带已生成的档案预览，供调用方直接检查。
        if isinstance(state.get("profile_preview"), dict):

            # 第二十二项来源
            dict_payload["profile_preview"] = state["profile_preview"]  # 第二十二项载荷

        # 第二十三项来源
        dict_payload["answers_for_review"] = answers_without_design_review(dict(state.get("answers", {})))  # 第二十三项载荷

    # 返工等待态公开待处理的设计复核记录。
    if status == "awaiting_review_rework" and isinstance(state.get("pending_design_review"), dict):

        # 第二十四项来源
        dict_payload["pending_design_review"] = state["pending_design_review"]  # 第二十四项载荷

# 生成远程依赖安装和服务器配置阶段的交互字段。
def remote_dependency_step(
    state: dict[str, Any],
    status: str,
    kind: object,
    list_confirmed_keys: list[str],
    remote_gate: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any], str, str] | None:
    """处理远程技能安装和服务器配置状态。

    参数：state 为访谈状态，status 为当前状态，kind 为项目类型，list_confirmed_keys 为已确认答案键，remote_gate 为远程门禁载荷。
    返回：当前问题组、问题记录、复核摘要、确认提示和下一动作；非远程依赖状态返回 None。

    数组契约:
        shape/维度: 本函数处理一维问题和确认键列表，不接收数值数组。
        dtype/类型: 字段由 dict、list、str、Path 和 JSON 兼容值约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段语义遵循远程门禁状态 schema。
    """

    # 非远程依赖状态继续交由主状态机处理。
    if status not in {
        "awaiting_remote_install_confirmation",
        "awaiting_remote_install_completion",
        "awaiting_remote_configuration_confirmation",
        "awaiting_remote_configuration_completion",
    }:

        # 返回空值表示当前状态不属于远程依赖处理范围。
        return None

    # 远程依赖状态在本处理器内完成字段组装。
    match status:
        # 缺少远程依赖时先请求用户确认是否安装技能。
        case "awaiting_remote_install_confirmation":

            # 第七十七项来源
            list_current_group = []  # 第七十七项载荷

            # 第七十八项来源
            list_questions = [  # 第七十八项载荷
                {
                    "question_id": "remote-install",  # 第二百七项结构字段
                    "answer_key": REMOTE_INSTALL_CONFIRM_KEY,  # 远程安装确认答案键
                    "required": True,  # 必答约束阶段二十七
                    "branch": "all",  # 安装确认适用于全部项目类型
                    "ask": "检测到需要远程服务器，但当前环境缺少 erie-remote-ssh。是否确认先安装该技能？如果不安装，需要把 use_remote_server 改为 false 才能继续。",  # 访谈问题阶段二十九
                    "options": [  # 第三百七项结构字段
                        {"label": "安装技能", "value": True, "description": "确认后先完成依赖安装，再继续远程服务器选择。", "recommended": True},  # 安装技能确认后先完成阶段三十
                        interactive_option(  # 暂不安装保持阻断状态阶段三十一
                            "暂不安装",  # 提供拒绝安装选项标签
                            False,  # 提交拒绝安装值
                            "保持阻断状态，除非把 use_remote_server 改为 false。",  # 说明拒绝安装后果
                            False,  # 默认建议安装依赖
                        ),
                    ],
                }
            ]

            # 第七十九项来源
            review = stage_review(state, kind, list_confirmed_keys, False)  # 第七十九项载荷

            # 第八十项来源
            path_remote_skill_dir = Path(remote_gate["skill_dir"]) if remote_gate.get("skill_dir") else None  # 第八十项载荷

            # 第八十一项来源
            str_confirmation_question = (  # 第八十一项载荷
                remote_install_command_hint(path_remote_skill_dir)  # 载荷片段阶段三十二
                if path_remote_skill_dir  # 第二百二十九项载荷表达式
                else remote_install_command_hint()  # 载荷片段阶段三十三
            )

            # 第八十二项来源
            str_next_action = "confirm_remote_ssh_install"  # 第八十二项载荷

        # 远程依赖安装完成态要求重新探测技能可用性。
        case "awaiting_remote_install_completion":

            # 第八十三项来源
            list_current_group = []  # 第八十三项载荷

            # 第八十四项来源
            list_questions = []  # 第八十四项载荷

            # 第八十五项来源
            review = stage_review(state, kind, list_confirmed_keys, False)  # 第八十五项载荷

            # 第八十六项来源
            path_remote_skill_dir = Path(remote_gate["skill_dir"]) if remote_gate.get("skill_dir") else None  # 第八十六项载荷

            # 第八十七项来源
            str_confirmation_question = (  # 第八十七项载荷
                remote_install_command_hint(path_remote_skill_dir)  # 第二百五项载荷表达式
                if path_remote_skill_dir  # 第二百二十八项载荷表达式
                else remote_install_command_hint()  # 第二百五十一项载荷表达式
            )

            # 第八十八项来源
            str_next_action = "resume_after_remote_ssh_install"  # 第八十八项载荷

        # 远程配置确认态展示待执行的服务器发现命令。
        case "awaiting_remote_configuration_confirmation":

            # 第八十九项来源
            list_current_group = []  # 第八十九项载荷

            # 第九十项来源
            list_questions = [  # 第九十项载荷
                {
                    "question_id": "remote-config",  # 载荷片段阶段三十四
                    "answer_key": REMOTE_CONFIGURATION_MODE_KEY,  # 第二百二十七项结构字段
                    "required": True,  # 必答约束阶段三十五
                    "branch": "all",  # 适用分支阶段三十六
                    "ask": "当前没有可用的远程服务器列表。是否进入远程服务器配置流程？",  # 第二百九十二项结构字段
                    "options": [  # 第三百六项结构字段
                        interactive_option(  # 使用的走引导式配置阶段三十七
                            "guided",  # 提供引导配置选项标签
                            "guided",  # 提交引导配置模式
                            "使用 erie-remote-ssh 的 configure --interactive 走引导式配置。",  # 说明配置命令
                            True,  # 默认建议引导配置
                        ),
                        interactive_option(  # 用户手动准备和配置然阶段三十八
                            "manual",  # 提供手动配置选项标签
                            "manual",  # 提交手动配置模式
                            "用户手动准备 server list 和 SSH 配置，然后回来继续。",  # 说明手动准备责任
                            False,  # 不默认选择手动配置
                        ),
                        interactive_option(  # 第三百三十五项结构字段
                            "cancel",  # 提供取消配置选项标签
                            "cancel",  # 提交取消配置动作
                            "保持阻断状态，除非把 use_remote_server 改为 false。",  # 说明取消后的阻断结果
                            False,  # 不默认取消远程配置
                        ),
                    ],
                }
            ]

            # 第九十一项来源
            review = stage_review(state, kind, list_confirmed_keys, False)  # 第九十一项载荷

            # 第九十二项来源
            str_confirmation_question = "选择 guided 或 manual 后，完成服务器配置，再执行 --resume 继续。"  # 第九十二项载荷

            # 第九十三项来源
            str_next_action = "confirm_remote_server_configuration"  # 第九十三项载荷

        # 配置完成态重新读取服务器清单并进入选择流程。
        case "awaiting_remote_configuration_completion":

            # 第九十四项来源
            list_current_group = []  # 第九十四项载荷

            # 第九十五项来源
            list_questions = []  # 第九十五项载荷

            # 第九十六项来源
            review = stage_review(state, kind, list_confirmed_keys, False)  # 第九十六项载荷

            # 第九十七项来源
            str_command_hint = ""  # 第九十七项载荷

            # 第三十八步判断状态。
            if remote_gate.get("skill_dir") and remote_gate.get("configuration_mode") == "guided":

                # 第九十八项来源
                str_command_hint = remote_configure_command_hint(Path(str(remote_gate["skill_dir"])))  # 第九十八项载荷

            # 第九十九项来源
            str_confirmation_question = str_command_hint or "完成远程服务器配置后，执行 --resume 继续远程服务器选择。"  # 第九十九项载荷

            # 第一百项来源
            str_next_action = "resume_after_remote_server_configuration"  # 第一百项载荷

    # 返回远程依赖阶段统一的交互字段。
    return list_current_group, list_questions, review, str_confirmation_question, str_next_action

# 生成写入完成态和只读完成态的交互字段。
def completion_step(
    state: dict[str, Any],
    status: str,
    kind: object,
    str_mode: str,
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any], str, str] | None:
    """处理设计访谈完成状态。

    参数：state 为访谈状态，status 为当前状态，kind 为项目类型，str_mode 为交互模式。
    返回：当前问题组、问题记录、复核摘要、确认提示和下一动作；非完成状态返回 None。

    数组契约:
        shape/维度: 本函数返回一维问题列表，不接收数值数组。
        dtype/类型: 字段由 dict、list 和 str 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段语义遵循设计访谈完成态 schema。
    """

    # 非完成状态继续交由其他状态处理器解析。
    if status not in {"completed", "completed_read_only"}:

        # 返回空值表示该状态尚未进入访谈完成阶段。
        return None

    # 完成状态在本处理器内生成写入或只读后续动作。
    match status:
        # 第三十段继续整理交互载荷。
        case "completed":

            # 第六十五项来源
            list_current_group = []  # 第六十五项载荷

            # 第六十六项来源
            list_questions = []  # 第六十六项载荷

            # 第六十七项来源
            review = review_summary(  # 第六十七项载荷
                state.get("answers", {}),  # 第二百九项结构字段
                str(kind) if kind else None,  # 载荷片段阶段二十二
                [],
                [key for key in state.get("answers", {}) if key != ALIGNMENT_KEY],  # 载荷片段阶段二十三
                final=True,  # 第二百七十六项载荷表达式
            )

            # 第三十一步判断状态。
            if str_mode == "takeover":

                # 第六十八项来源
                str_confirmation_question = (  # 第六十八项载荷
                    "接管最小访谈已完成。将 answers_snapshot 保存为 JSON 后，使用 --answers <file> --write "
                    "写入控制档案并继续执行 takeover 整理链。"
                )

                # 第六十九项来源
                str_next_action = "export_answers_and_run_takeover_write"  # 第六十九项载荷

            # 第三十二步处理兜底。
            else:

                # 第七十项来源
                str_confirmation_question = "设计访谈已完成。将 answers_snapshot 保存为 JSON 后，使用 --answers <file> --write 写入控制档案。"  # 第七十项载荷

                # 第七十一项来源
                str_next_action = "export_answers_and_run_batch_write"  # 第七十一项载荷

        # 只读完成态保留预览结果但禁止写入受管文件。
        case "completed_read_only":

            # 第七十二项来源
            list_current_group = []  # 第七十二项载荷

            # 第七十三项来源
            list_questions = []  # 第七十三项载荷

            # 第七十四项来源
            review = review_summary(  # 第七十四项载荷
                state.get("answers", {}),  # 载荷片段阶段二十四
                str(kind) if kind else None,  # 第二百三十一项载荷表达式
                [],
                [key for key in state.get("answers", {}) if key != ALIGNMENT_KEY],  # 载荷片段阶段二十五
                final=True,  # 第二百七十五项载荷表达式
            )

            # 第七十五项来源
            str_confirmation_question = (  # 第七十五项载荷
                "只读设计访谈已完成。保留 answers_snapshot 和 profile_preview 供解释、规划或人工复核使用；"
                "只有显式执行写入升格后才会触发子智能体审查。"
            )

            # 第七十六项来源
            str_next_action = "stay_read_only_or_enter_write_review"  # 第七十六项载荷

    # 返回完成阶段统一的交互字段。
    return list_current_group, list_questions, review, str_confirmation_question, str_next_action

# 为未知或未完成状态生成恢复访谈提示。
def fallback_interview_step(
    state: dict[str, Any],
    kind: object,
    list_group_ids: list[str],
    list_confirmed_keys: list[str],
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any], str, str]:
    """生成未识别状态的恢复交互字段。

    参数：state 为访谈状态，kind 为项目类型，list_group_ids 为当前问题编号，list_confirmed_keys 为已确认答案键。
    返回：当前问题组、问题记录、复核摘要、恢复提示和下一动作。

    数组契约:
        shape/维度: 问题编号和确认键为一维业务列表，不处理数值数组。
        dtype/类型: 元素由 str 和 JSON 兼容映射约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段语义遵循设计访谈状态 schema。
    """

    # 未完成状态继续展示状态机计算出的当前问题组。
    list_questions = question_rows(list_group_ids)  # 展开恢复时需要重新展示的问题

    # 恢复摘要区分当前问题键和已经确认的历史字段。
    review = review_summary(  # 生成恢复链路的非最终摘要
        state.get("answers", {}),  # 提供当前答案快照
        str(kind) if kind else None,  # 提供可选项目类型
        question_ids_to_keys(list_group_ids),  # 标识当前待回答字段
        list_confirmed_keys,  # 保留历史确认字段
        final=False,  # 恢复状态不生成最终摘要
    )

    # 返回恢复访谈所需的统一交互字段。
    return (
        list_group_ids,
        list_questions,
        review,
        "检测到未完成的设计访谈，请先 resume 或 reset，不要静默开启新链路。",
        "resume_or_reset_interview",
    )

# 生成设计审查等待态和返工态的交互字段。
def design_review_step(
    state: dict[str, Any],
    status: str,
    kind: object,
    list_confirmed_keys: list[str],
) -> tuple[list[str], list[dict[str, Any]], Any, str, str] | None:
    """处理设计审查提交和审查返工状态。

    参数：state 为访谈状态，status 为当前状态，kind 为项目类型，list_confirmed_keys 为已确认答案键。
    返回：当前问题组、问题记录、复核摘要、确认提示和下一动作；非设计审查状态返回 None。

    数组契约:
        shape/维度: 问题和确认键为一维业务列表，不处理数值数组。
        dtype/类型: 元素由 str 和 JSON 兼容映射约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段语义遵循设计审查状态 schema。
    """

    # 非审查状态继续交由主状态机处理。
    if status not in {"awaiting_design_review", "awaiting_review_rework"}:

        # 返回空值表示当前状态不属于设计审查处理范围。
        return None

    # 审查状态在本处理器内生成提交或返工动作。
    match status:
        # 设计复核阶段输出只读材料并等待审查结论。
        case "awaiting_design_review":

            # 第五十五项来源
            list_current_group = []  # 第五十五项载荷

            # 第五十六项来源
            list_questions = [  # 第五十六项载荷
                {
                    "question_id": "design-review",  # 载荷片段阶段十九
                    "answer_key": DESIGN_REVIEW_KEY,  # 答案字段阶段二十
                    "required": True,  # 第二百五十六项结构字段
                    "branch": "all",  # 第二百七十七项结构字段
                    "ask": "最终一致性已确认。请执行代理拉起新的审查子智能体审查完整方案，并提交结构化 design_review JSON。",  # 访谈问题阶段二十一
                    "options": [  # 第三百八项结构字段
                        {
                            "label": "提交子智能体审查 JSON",  # 第三百二十项展示标签
                            "value": "__user_input__",  # 第三百三十项提交值
                            "description": (  # 第三百三十六项选择说明
                                "必须包含 reviewer_type=subagent、verdict、findings、"
                                "required_user_confirmations、两个 hash 和 review_summary。"
                            ),
                            "recommended": True,  # 第三百三十九项推荐状态
                        },
                    ],
                }
            ]

            # 第五十七项来源
            review = stage_review(state, kind, list_confirmed_keys, True)  # 第五十七项载荷

            # 第五十八项来源
            str_confirmation_question = "只有子智能体 approve、无待用户确认、且 hash 匹配时，访谈才能 completed。"  # 第五十八项载荷

            # 第五十九项来源
            str_next_action = "submit_design_review"  # 第五十九项载荷

        # 复核返工阶段携带拒绝原因重新进入修正流程。
        case "awaiting_review_rework":

            # 第六十项来源
            list_current_group = []  # 第六十项载荷

            # 第六十一项来源
            list_questions = []  # 第六十一项载荷

            # 第六十二项来源
            review = stage_review(state, kind, list_confirmed_keys, True)  # 第六十二项载荷

            # 第六十三项来源
            str_confirmation_question = (  # 第六十三项载荷
                "审查要求返工。请确认修正项并提交 review_rework_confirmed=true 加上需要修正的字段；"
                "旧 design_review 会失效，之后必须重新最终确认和子智能体审查。"
            )

            # 第六十四项来源
            str_next_action = "confirm_review_rework"  # 第六十四项载荷

    # 返回设计审查阶段统一的交互字段。
    return list_current_group, list_questions, review, str_confirmation_question, str_next_action

# 选择主状态机需要消费的实际分派状态。
def resolved_dispatch_status(
    status: str,
    remote_step: object,
    completion_result: object,
    design_review_result: object,
    local_interview_result: object,
) -> str:
    """按处理器优先级解析内部哨兵状态。

    参数：status 为原始状态，remote_step 为远程处理结果，completion_result 为完成态结果。
    design_review_result 为审查结果，local_interview_result 为本地访谈结果。
    返回：主 match 使用的原始状态或内部已处理哨兵。

    数组契约:
        shape/维度: 本函数只判断处理结果是否存在，不处理数值数组。
        dtype/类型: 状态为 str，处理结果为可选业务对象，非 ndarray dtype。
        unit/单位: 无物理量单位，返回值仅用于模块内部状态分派。
    """

    # 远程依赖结果具有最高分派优先级。
    if remote_step is not None:

        # 返回远程依赖已处理哨兵。
        return "remote_dependency_handled"

    # 完成态结果优先于设计审查结果。
    if completion_result is not None:

        # 返回完成态已处理哨兵。
        return "completion_handled"

    # 设计审查结果覆盖原始审查状态。
    if design_review_result is not None:

        # 返回设计审查已处理哨兵。
        return "design_review_handled"

    # 本地访谈结果覆盖原始收集和对齐状态。
    if local_interview_result is not None:

        # 返回本地访谈已处理哨兵。
        return "local_interview_handled"

    # 未被辅助处理器消费时保留原始状态。
    return status

# 生成问题收集、组确认、补充需求和最终对齐阶段的交互字段。
def local_interview_step(
    state: dict[str, Any],
    status: str,
    kind: object,
    list_group_ids: list[str],
    list_confirmed_keys: list[str],
) -> tuple[list[str], list[dict[str, Any]], Any, str, str] | None:
    """处理设计访谈的本地收集与对齐状态。

    参数：state 为访谈状态，status 为当前状态，kind 为项目类型，list_group_ids 为当前问题编号，list_confirmed_keys 为已确认答案键。
    返回：当前问题组、问题记录、复核摘要、确认提示和下一动作；非本地访谈状态返回 None。

    数组契约:
        shape/维度: 问题和确认键为一维业务列表，不处理数值数组。
        dtype/类型: 元素由 str 和 JSON 兼容映射约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段语义遵循设计访谈状态 schema。
    """

    # 非本地访谈状态继续交由其他处理器解析。
    if status not in {
        "collecting_group",
        "awaiting_group_confirmation",
        "awaiting_extra_requirements",
        "awaiting_final_alignment",
    }:

        # 返回空值表示当前状态不属于本地访谈处理范围。
        return None

    # 收集与分组确认默认沿用当前问题组，后续阶段按协议清空。
    list_current_group = list_group_ids  # 保留原状态机的当前分组语义

    # 本地访谈状态在本处理器内生成问题和确认动作。
    match status:
        # 收集阶段展示当前问题组并等待用户回答。
        case "collecting_group":

            # 第三十七项来源
            list_questions = question_rows(list_group_ids)  # 第三十七项载荷

            # 第三十八项来源
            review = review_summary(  # 第三十八项载荷
                state.get("answers", {}),  # 第二百十五项结构字段
                str(kind) if kind else None,  # 第二百三十八项载荷表达式
                question_ids_to_keys(list_group_ids),  # 第二百六十一项载荷表达式
                list_confirmed_keys,  # 第二百八十二项载荷表达式
                final=False,  # 第二百九十八项载荷表达式
            )

            # 第三十九项来源
            str_confirmation_question = "请先回答当前问题组；提交后脚本会返回该组确认摘要。"  # 第三十九项载荷

            # 第四十项来源
            str_next_action = "answer_current_group"  # 第四十项载荷

        # 分组确认阶段要求用户核对刚完成的一组答案。
        case "awaiting_group_confirmation":

            # 第四十一项来源
            list_questions = question_rows(list_group_ids)  # 第四十一项载荷

            # 第四十二项来源
            review = review_summary(  # 第四十二项载荷
                state.get("answers", {}),  # 第二百十四项结构字段
                str(kind) if kind else None,  # 第二百三十七项载荷表达式
                question_ids_to_keys(list_group_ids),  # 问题键映射阶段十五
                [key for key in list_confirmed_keys if key not in question_ids_to_keys(list_group_ids)],  # 第二百八十一项载荷表达式
                final=False,  # 第二百九十七项载荷表达式
            )

            # 第四十三项来源
            str_confirmation_question = "请确认当前问题组是否正确；如果否，请修正本组字段并重新确认。"  # 第四十三项载荷

            # 第四十四项来源
            str_next_action = "confirm_current_group"  # 第四十四项载荷

        # 额外需求阶段收集既有问题之外的补充约束。
        case "awaiting_extra_requirements":

            # 第四十五项来源
            list_current_group = []  # 第四十五项载荷

            # 初始化额外需求问题，随后逐项填充稳定的交互协议字段。
            dict_extra_question: dict[str, Any] = {}  # 第四十六项问题载荷

            # 标识额外需求问题，供回答路由精确匹配。
            dict_extra_question["question_id"] = "extra-requirements"  # 第二百十三项结构字段

            # 绑定额外需求答案键，供状态持久化使用。
            dict_extra_question["answer_key"] = EXTRA_REQUIREMENTS_KEY  # 第二百三十六项结构字段

            # 要求用户显式回答，即使没有补充也必须提交 none。
            dict_extra_question["required"] = True  # 第二百五十九项结构字段

            # 对所有项目类型展示该问题。
            dict_extra_question["branch"] = "all"  # 第二百八十项结构字段

            # 提示用户补充既有问题之外的需求、约束、风险或偏好。
            dict_extra_question["ask"] = (  # 第二百九十六项结构字段
                "完整分组访谈已结束。是否还有额外要补充的需求、约束、风险或偏好？"
                "如果没有，请回答 none/无补充。"
            )

            # 提供无补充和自由输入两种明确选择。
            list_options = [  # 第三百十项结构字段
                interactive_option(  # 第三百二十一项结构字段
                    "无补充",  # 提供无补充选项标签
                    "none",  # 提交显式无补充值
                    "记录 extra_requirements=none，然后进入最终一致性确认。",  # 说明后续状态迁移
                    True,  # 默认建议完成补充字段
                ),
                interactive_option(  # 第三百三十一项结构字段
                    "用户输入",  # 提供自由输入选项标签
                    "__user_input__",  # 提交自由输入占位值
                    "补充内容会写入控制档案并稳定渲染到 AGENTS.md。",  # 说明补充内容去向
                    False,  # 不默认推断用户补充
                ),
            ]

            # 将选择列表写入问题协议。
            dict_extra_question["options"] = list_options  # 绑定额外需求阶段的交互选择

            # 交互载荷使用问题列表协议，即使当前阶段只有一个问题。
            list_questions = [dict_extra_question]  # 第四十六项载荷

            # 第四十七项来源
            review = stage_review(state, kind, list_confirmed_keys, False)  # 第四十七项载荷

            # 第四十八项来源
            str_confirmation_question = "请提交 extra_requirements；没有补充也必须显式记录 none。"  # 第四十八项载荷

            # 第四十九项来源
            str_next_action = "answer_extra_requirements"  # 第四十九项载荷

        # 最终对齐阶段确认完整访谈结果符合用户理解。
        case "awaiting_final_alignment":

            # 第五十项来源
            list_current_group = []  # 第五十项载荷

            # 第五十一项来源
            list_questions = [  # 第五十一项载荷
                with_options(  # 问题选项补全阶段十六
                    {
                        "question_id": "alignment",  # 载荷片段阶段十七
                        "answer_key": ALIGNMENT_KEY,  # 第二百五十八项结构字段
                        "required": True,  # 第二百七十九项结构字段
                        "branch": "all",  # 适用分支阶段十八
                        "ask": "请确认完整设计访谈已经一致；如果否，请提交需要修正的字段并重新确认。",  # 第三百九项结构字段
                    }
                )
            ]

            # 第五十二项来源
            review = review_summary(  # 第五十二项载荷
                state.get("answers", {}),  # 第二百十一项结构字段
                str(kind) if kind else None,  # 第二百三十四项载荷表达式
                [],
                [key for key in state.get("answers", {}) if key != ALIGNMENT_KEY],  # 第二百五十七项结构字段
                final=True,  # 第二百七十八项载荷表达式
            )

            # 第五十三项来源
            str_confirmation_question = "请确认整个设计访谈已经完整一致；如果需要修正，请附带修正字段重新提交。"  # 第五十三项载荷

            # 第五十四项来源
            str_next_action = "confirm_final_alignment"  # 第五十四项载荷

    # 返回本地访谈阶段统一的交互字段。
    return list_current_group, list_questions, review, str_confirmation_question, str_next_action

# 根据完整访谈状态构建 CLI 返回载荷。
def build_interactive_payload(
    project: Path,
    state: dict[str, Any],
    status_override: str | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """根据访谈状态生成下一步问题、确认动作和辅助决策信息。

    参数：project 为项目根目录，state 为访谈状态，status_override 为可选状态覆盖，errors 为可选错误列表。
    返回：包含问题、复核、决策、远程门禁和完成态信息的交互载荷。

    数组契约:
        shape/维度: 本函数处理 AGENTS 状态、JSON 记录或文件路径，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict、list、str、Path 等 Python 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义以 AGENTS 治理配置和状态文件 schema 为准。
    """

    from design_interview_state import (
        confirmed_keys_for_state,
        current_group_ids,
        normalize_intent,
        remaining_groups_for_state,
        review_policy_for_state,
        state_path,
    )

    # 第二十五项来源
    status = status_override or str(state.get("status", "collecting_group"))  # 第二十五项载荷

    # 第二十六项来源
    str_mode = str(state.get("mode", "interactive"))  # 第二十六项载荷

    # 第二十七项来源
    str_intent = normalize_intent(state.get("intent"))  # 第二十七项载荷

    # 第二十八项来源
    list_group_ids = current_group_ids(state)  # 第二十八项载荷

    # 第二十九项来源
    kind = state.get("kind") or state.get("inferred_kind")  # 第二十九项载荷

    # 第三十项来源
    list_confirmed_keys = confirmed_keys_for_state(state)  # 第三十项载荷

    # 第三十一项来源
    review = review_summary(state.get("answers", {}), str(kind) if kind else None)  # 第三十一项载荷

    # 第三十二项来源
    str_confirmation_question = ""  # 第三十二项载荷

    # 第三十三项来源
    str_next_action = ""  # 第三十三项载荷

    # 第三十五项来源
    list_current_group = list_group_ids  # 第三十五项载荷

    # 第三十六项来源
    remote_gate = remote_gate_payload(state)  # 第三十六项载荷

    # 远程依赖和配置状态由独立处理器组装。
    tuple_remote_dependency_step = remote_dependency_step(  # 接收远程依赖阶段五元组
        state, status, kind, list_confirmed_keys, remote_gate  # 传递远程状态组装所需上下文
    )

    # 完成状态由独立处理器生成写入或只读后续动作。
    tuple_completion_step = completion_step(state, status, kind, str_mode)  # 接收完成阶段五元组

    # 设计审查状态由独立处理器生成提交或返工动作。
    tuple_design_review_step = design_review_step(  # 接收设计审查阶段五元组
        state, status, kind, list_confirmed_keys  # 传递审查状态组装所需上下文
    )

    # 本地访谈状态由独立处理器生成问题和对齐动作。
    tuple_local_interview_step = local_interview_step(  # 接收本地访谈阶段五元组
        state, status, kind, list_group_ids, list_confirmed_keys  # 传递本地访谈组装所需上下文
    )

    # 主状态机按处理器优先级解析并消费实际分派状态。
    match resolved_dispatch_status(
        status,
        tuple_remote_dependency_step,
        tuple_completion_step,
        tuple_design_review_step,
        tuple_local_interview_step,
    ):

        # 远程依赖处理器的结果接入统一载荷字段。
        case "remote_dependency_handled":

            # 第一百十一项来源
            list_current_group, list_questions, review, str_confirmation_question, str_next_action = (  # 第一百十一项载荷
                tuple_remote_dependency_step  # 解包远程处理器返回的统一字段
            )

        # 完成态处理器的结果接入统一载荷字段。
        case "completion_handled":

            # 第一百十二项来源
            list_current_group, list_questions, review, str_confirmation_question, str_next_action = (  # 第一百十二项载荷
                tuple_completion_step  # 解包完成处理器返回的统一字段
            )

        # 设计审查处理器的结果接入统一载荷字段。
        case "design_review_handled":

            # 第一百十三项来源
            list_current_group, list_questions, review, str_confirmation_question, str_next_action = (  # 第一百十三项载荷
                tuple_design_review_step  # 解包设计审查处理器返回的统一字段
            )

        # 本地访谈处理器的结果接入统一载荷字段。
        case "local_interview_handled":

            # 第一百十四项来源
            list_current_group, list_questions, review, str_confirmation_question, str_next_action = (  # 第一百十四项载荷
                tuple_local_interview_step  # 解包本地访谈处理器返回的统一字段
            )

        # 路由映射态为已选服务器分配主用和回退任务路线。
        case "awaiting_remote_server_route_mapping":

            # 第一百一项来源
            tuple_remote_route_step = remote_route_mapping_step(  # 保存远程路由阶段五元组
                state,  # 提供路由阶段访谈状态
                kind,  # 提供路由项目类型
                list_confirmed_keys,  # 提供路由已确认字段
                remote_gate,  # 提供候选服务器门禁载荷
            )

            # 第一百二项来源
            list_current_group = tuple_remote_route_step[0]  # 接入路由问题组

            # 第一百三项来源
            list_questions = tuple_remote_route_step[1]  # 接入路由问题记录

            # 第一百四项来源
            review = tuple_remote_route_step[2]  # 接入路由复核摘要

            # 第一百五项来源
            str_confirmation_question = tuple_remote_route_step[3]  # 接入路由确认提示

            # 第一百六项来源
            str_next_action = tuple_remote_route_step[4]  # 接入路由下一动作
        case _:

            # 第一百七项来源
            tuple_fallback_step = fallback_interview_step(  # 保存未知状态恢复五元组
                state,  # 提供恢复阶段访谈状态
                kind,  # 提供恢复项目类型
                list_group_ids,  # 提供恢复问题编号
                list_confirmed_keys,  # 提供恢复已确认字段
            )

            # 第一百八项来源
            list_current_group = tuple_fallback_step[0]  # 接入恢复问题组

            # 第一百九项来源
            list_questions = tuple_fallback_step[1]  # 接入恢复问题记录

            # 第一百十项来源
            review = tuple_fallback_step[2]  # 接入恢复复核摘要

            # 恢复提示沿用辅助函数确定的用户引导文案。
            str_confirmation_question = tuple_fallback_step[3]  # 接入恢复确认提示

            # 恢复动作要求用户继续或重置现有访谈链。
            str_next_action = tuple_fallback_step[4]  # 接入恢复下一动作

    # 汇总各状态处理器生成的最终交互字段。
    dict_payload: dict[str, Any] = {  # 形成 CLI 返回的完整载荷
        "project": str(project),  # 项目根路径阶段四十
        "mode": str_mode,  # 交互模式阶段四十一
        "intent": str_intent,  # 第二百四十七项结构字段
        "status": status,  # 访谈状态阶段四十二
        "kind": kind,  # 载荷片段阶段四十三
        "inferred_kind": state.get("inferred_kind"),  # 第三百五项结构字段
        "review_policy": review_policy_for_state(state, status),  # 载荷片段阶段四十四
        "current_group": list_current_group,  # 载荷片段阶段四十五
        "questions": list_questions,  # 第三百三十四项结构字段
        "remaining_groups": remaining_groups_for_state(state),  # 载荷片段阶段四十六
        "review_summary": review,  # 第三百四十一项结构字段
        "confirmed_so_far": review["confirmed_fields"],  # 第三百四十三项结构字段
        "confirmation_question": str_confirmation_question,  # 第三百四十四项结构字段
        "next_action": str_next_action,  # 第三百四十五项结构字段
        "session_state_path": str(state_path(project)),  # 第三百四十六项结构字段
        "errors": errors or [],  # 错误集合阶段四十七
    }

    # 第四十步更新载荷。
    enrich_interactive_payload(
        dict_payload,
        status,
        str_mode,
        state,
        list_questions,
        remote_gate,
    )

    # 第四十一步返回载荷。
    return dict_payload
