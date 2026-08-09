"""组装设计访谈状态机返回给 CLI 的交互 payload。"""

# 延迟注解求值，保持模块按文件规格加载时的类型兼容性。
from __future__ import annotations

# 标准库提供路径和结构化业务类型注解。
from pathlib import Path
from typing import Any

# 设计访谈依赖提供决策、预览、问题和远程门禁合同。
from agents_decisions import decision_request

# 知识图谱合同提供官方发布页，供人工安装指引复用。
from codebase_memory_mcp import RELEASES_URL

# 设计画像摘要用于每个访谈阶段的统一复核字段。
from design_profile_builder import review_summary

# 状态查询助手只读取持久化状态，载荷模块不会触发状态写入。
from design_interview_state import (
    confirmed_keys_for_state,
    current_group_ids,
    normalize_intent,
    remaining_groups_for_state,
    review_policy_for_state,
    state_path,
)

# 问题合同提供状态键、远程依赖来源和用户可见文案。
from design_questions import (
    ALIGNMENT_KEY,
    CODEBASE_MEMORY_INSTALL_CONFIRM_KEY,
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

    数组契约：shape 为单条 JSON 记录，dtype 为 JSON 兼容类型，unit 不适用。
    """

    # 返回固定字段顺序的标准交互选项。
    return dict(label=str_label, value=value, description=str_description, recommended=is_recommended)

# 从远程候选问题中提取默认服务器标识。
def first_question_option_value(list_questions: list[dict[str, Any]]) -> Any:
    """读取首个问题的首个候选值。

    参数：list_questions 为当前交互问题记录。
    返回：首个候选项的 value；问题或候选项缺失时返回 None。

    数组契约：shape 为一维问题列表，dtype 为 JSON 兼容类型，unit 不适用。
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

    数组契约：shape 为一维确认键列表，dtype 为 JSON 兼容类型，unit 不适用。
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

    数组契约：shape 为问题列表和路由映射，dtype 为 JSON 兼容类型，unit 不适用。
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

# 基础设施决策集中处理远程 SSH、知识图谱和服务器路由状态。
def infrastructure_decision_request(
    status: str,
    list_questions: list[dict[str, Any]],
    remote_gate: dict[str, Any],
) -> dict[str, Any] | None:
    """构造基础设施相关决策请求。

    参数:
        status: 当前状态机状态。
        list_questions: 当前状态公开的问题集合。
        remote_gate: 远程服务器依赖与发现证据。

    返回:
        基础设施状态对应的决策请求；非基础设施状态返回 None。

    数组契约:
        shape 为 JSON 映射与问题列表，dtype 为 JSON 兼容类型，unit 不适用。
    """

    # 远程技能缺失时必须先取得用户安装授权。
    if status == "awaiting_remote_install_confirmation":

        # 安装决策包含依赖来源、风险和禁用替代路径。
        return decision_request(
            "remote_dependency_install",
            question="需要远程服务器能力，但 erie-remote-ssh 未安装。是否先安装该技能？",
            options=list_questions[0].get("options", []) if list_questions else [],
            default=True,
            risk="medium",
            next_action="install erie-remote-ssh or disable use_remote_server before continuing",
            context={"dependency": REMOTE_SSH_SKILL_NAME, "url": REMOTE_SSH_GIT_URL},
        )

    # 知识图谱依赖缺失时只允许进入人工安装流程。
    if status == "awaiting_codebase_memory_install_confirmation":

        # 决策上下文明确自动安装始终关闭。
        return decision_request(
            "codebase_memory_install",
            question="已选择使用 codebase-memory-mcp，但本地未安装或未完成 Codex MCP 配置。是否进入人工安装流程？",
            options=list_questions[0].get("options", []) if list_questions else [],
            default=True,
            risk="medium",
            next_action="follow the official release instructions, restart Codex, then resume",
            context={"releases_url": RELEASES_URL, "automatic_install": False},
        )

    # 缺少服务器列表时让用户选择引导式配置流程。
    if status == "awaiting_remote_configuration_confirmation":

        # 发现结果随决策返回，支持用户判断配置成本。
        return decision_request(
            "remote_server_configuration",
            question="当前没有可用的远程服务器列表。是否进入远程服务器配置流程？",
            options=list_questions[0].get("options", []) if list_questions else [],
            default="guided",
            risk="high",
            next_action="configure remote server access, then rerun collect_design_profile.py --resume",
            context={"remote_discover": remote_gate.get("discover", {}) if isinstance(remote_gate, dict) else {}},
        )

    # 服务器存在后要求确认每类任务的主备路由。
    if status == "awaiting_remote_server_route_mapping":

        # 默认值来自首个公开选项，禁止凭空推断服务器标识。
        return decision_request(
            "remote_server_route_mapping",
            question="请确认远程任务到服务器的主备路由后再写入 AGENTS.md。",
            options=list_questions[0].get("options", []) if list_questions else [],
            default=first_question_option_value(list_questions),
            risk="high",
            next_action="submit remote_server_task_routes with primary and optional fallback server IDs",
            context={"server_count": len(list_questions[0].get("options", [])) if list_questions else 0},
        )

    # None 让上层继续检查审查和只读完成态决策。
    return None

# 决策请求构造与完成态快照分离，避免单函数同时承担状态分派和载荷扩展。
def decision_request_for_status(
    status: str,
    state: dict[str, Any],
    list_questions: list[dict[str, Any]],
    remote_gate: dict[str, Any],
) -> dict[str, Any]:
    """按当前状态构造可选的用户决策请求。

    参数:
        status: 当前状态机状态。
        state: 当前持久化访谈状态。
        list_questions: 当前状态公开的问题集合。
        remote_gate: 远程服务器依赖与发现证据。

    返回:
        当前状态对应的决策请求；无需专用决策时返回空映射。

    数组契约:
        shape 为 JSON 映射与问题列表，dtype 为 JSON 兼容类型，unit 不适用。
    """

    # 基础设施状态由独立构造器优先处理。
    dict_infrastructure_request = infrastructure_decision_request(  # 可选基础设施决策请求
        status,  # 当前状态机状态
        list_questions,  # 当前公开问题集合
        remote_gate,  # 远程依赖与发现证据
    )

    # 命中基础设施状态后无需继续检查审查或只读状态。
    if dict_infrastructure_request is not None:

        # 返回完整决策卡片给交互载荷。
        return dict_infrastructure_request

    # 审查拒绝或待确认事项必须通过显式返工决策闭环。
    if status == "awaiting_review_rework":

        # 待处理审查记录为返工决策提供发现项和确认项。
        dict_pending = (  # 待返工审查记录
            state.get("pending_design_review", {})  # 已持久化审查映射
            if isinstance(state.get("pending_design_review"), dict)  # 有效映射分支
            else {}  # 损坏或缺失记录回退为空映射
        )

        # 返工选项要求至少提交一个修正字段。
        return decision_request(
            "design_review_rework",
            question="子智能体审查未批准或仍有待用户确认事项。请确认并提交修正字段后重新进入最终一致性与审查。",
            options=[
                interactive_option(
                    "确认返工",
                    True,
                    "提交 review_rework_confirmed=true 和至少一个修正字段。",
                    True,
                ),
                {"label": "暂不继续", "value": False, "description": "保持阻断状态，不写入控制档案。", "recommended": False},
            ],
            default=True,
            risk="high",
            next_action="submit correction fields, then repeat final alignment and subagent review",
            context={
                "findings": dict_pending.get("findings", []),
                "required_user_confirmations": dict_pending.get("required_user_confirmations", []),
            },
        )

    # 只读完成态必须由用户显式升格后才能进入写入审查。
    if status == "completed_read_only":

        # 默认选项继续保持只读，避免隐式扩大写入权限。
        return decision_request(
            "read_only_completed",
            question="只读设计访谈已完成。若后续需要正式写入控制档案，请显式进入写入审查。",
            options=[
                {"label": "保持只读", "value": "stay_read_only", "description": "保留当前只读结果，不触发子智能体审查。", "recommended": True},
                interactive_option(
                    "申请写入审查",
                    "enter_write_review",
                    "显式切换到写入意图并生成 design_review_request。",
                    False,
                ),
            ],
            default="stay_read_only",
            risk="medium",
            next_action="use --enter-write-review only when the user explicitly requests a write path",
        )

    # 其他状态不需要专用用户决策卡片。
    return {}

# 接管模式和远程门禁字段由独立扩展器就地加入基础载荷。
def enrich_remote_context(
    dict_payload: dict[str, Any],
    str_mode: str,
    state: dict[str, Any],
    remote_gate: dict[str, Any],
) -> None:
    """补充接管原因和远程依赖发现字段。

    参数:
        dict_payload: 待扩展的基础交互载荷。
        str_mode: 当前执行模式。
        state: 当前持久化访谈状态。
        remote_gate: 远程依赖和服务器发现证据。

    返回:
        无业务返回值；函数就地更新 dict_payload。

    数组契约:
        shape 为 JSON 映射，dtype 为 JSON 兼容类型，unit 不适用。
    """

    # 接管模式公开触发原因，供用户理解自动推进依据。
    if str_mode == "takeover":

        # 原因列表复制后写入，避免调用方修改持久化状态。
        dict_payload["takeover_trigger_reasons"] = list(state.get("takeover_trigger_reasons", []))  # 接管触发原因

    # 未启用远程治理时不添加空依赖对象。
    if not remote_gate:

        # 基础载荷保持无远程字段的稳定合同。
        return

    # 远程依赖摘要公开安装状态、来源和安装规格。
    dict_payload["remote_dependency"] = {  # 远程技能依赖摘要
        "installed": bool(remote_gate.get("dependency_status") == "installed"),  # 远程技能安装判定
        "status": remote_gate.get("dependency_status", ""),  # 原始依赖状态
        "url": remote_gate.get("dependency_url", REMOTE_SSH_GIT_URL),  # 依赖来源地址
        "install_specs": remote_gate.get("install_specs", REMOTE_SSH_INSTALL_SPECS),  # 平台安装规格
    }

    # 发现命令证据存在时原样加入交互载荷。
    if remote_gate.get("discover"):

        # 调用方可据此定位无服务器或配置错误原因。
        dict_payload["remote_discover"] = remote_gate.get("discover")  # 远程发现证据

    # 可选服务器存在时只公开规整后的服务器数组。
    if remote_gate.get("choices"):

        # 选择列表用于后续主备路由映射。
        dict_payload["remote_server_choices"] = remote_gate.get("choices", {}).get("servers", [])  # 候选服务器列表

# 完成、设计审查和返工状态由独立扩展器公开对应快照。
def enrich_review_context(dict_payload: dict[str, Any], status: str, state: dict[str, Any]) -> None:
    """补充完成态快照、审查请求和返工记录。

    参数:
        dict_payload: 待扩展的基础交互载荷。
        status: 当前状态机状态。
        state: 当前持久化访谈状态。

    返回:
        无业务返回值；函数就地更新 dict_payload。

    数组契约:
        shape 为 JSON 映射，dtype 为 JSON 兼容类型，unit 不适用。
    """

    # 完成态公开答案快照，供最终结果核对。
    if status in {"completed", "completed_read_only"}:

        # 映射副本避免调用方修改状态机内部答案。
        dict_payload["answers_snapshot"] = dict(state.get("answers", {}))  # 完成态答案快照

    # 只读完成态额外公开未写入的画像预览。
    if status == "completed_read_only" and isinstance(state.get("profile_preview"), dict):

        # 预览允许用户核对而不扩大写入权限。
        dict_payload["profile_preview"] = state["profile_preview"]  # 只读画像预览

    # 等待设计审查时公开审查合同及去除旧审查的输入。
    if status == "awaiting_design_review":

        # 结构化审查请求存在时交给 subagent 执行。
        if isinstance(state.get("design_review_request"), dict):

            # 请求字段定义 reviewer、结论和哈希合同。
            dict_payload["design_review_request"] = state["design_review_request"]  # 设计审查请求

        # 已生成画像预览时与审查请求一并公开。
        if isinstance(state.get("profile_preview"), dict):

            # 审查者使用预览核对最终生成合同。
            dict_payload["profile_preview"] = state["profile_preview"]  # 待审查画像预览

        # 审查输入排除上一轮 design_review，防止自引用哈希。
        dict_payload["answers_for_review"] = answers_without_design_review(dict(state.get("answers", {})))  # 去审查字段答案

    # 返工等待态公开待处理发现项和用户确认事项。
    if status == "awaiting_review_rework" and isinstance(state.get("pending_design_review"), dict):

        # 原始审查记录支持下一轮修正闭环。
        dict_payload["pending_design_review"] = state["pending_design_review"]  # 待返工设计审查

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

    # 专用构造器集中处理所有需要用户决策卡片的状态。
    dict_payload["decision_request"] = decision_request_for_status(  # 当前状态的决策请求
        status,  # 决策卡片选择依据
        state,  # 返工决策上下文来源
        list_questions,  # 决策卡片选项来源
        remote_gate,  # 基础设施决策证据来源
    )

    # 接管原因与远程依赖字段由远程上下文扩展器处理。
    enrich_remote_context(dict_payload, str_mode, state, remote_gate)

    # 完成态、设计审查和返工字段由审查上下文扩展器处理。
    enrich_review_context(dict_payload, status, state)

# 知识图谱依赖步骤与远程 SSH 步骤分离，避免两个安装协议互相耦合。
def codebase_memory_dependency_step(
    state: dict[str, Any],
    status: str,
    kind: object,
    list_confirmed_keys: list[str],
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any], str, str] | None:
    """生成知识图谱人工安装确认与完成等待字段。

    参数:
        state: 当前持久化设计访谈状态。
        status: 当前状态机状态。
        kind: 已确认或推断的项目类型。
        list_confirmed_keys: 已完成确认的答案键集合。

    返回:
        知识图谱安装状态对应的统一五元组；其他状态返回 None。

    数组契约:
        shape 为问题列表和 JSON 映射，dtype 为 JSON 兼容类型，unit 不适用。
    """

    # 非知识图谱安装状态继续交给远程或本地处理器。
    if status not in {
        "awaiting_codebase_memory_install_confirmation",
        "awaiting_codebase_memory_install_completion",
    }:

        # None 表示当前处理器没有消费该状态。
        return None

    # 两种知识图谱状态都不属于普通问题组。
    list_current_group: list[str] = []  # 知识图谱门禁的空问题组

    # 阶段复核保留此前答案与确认键的完整摘要。
    review = stage_review(state, kind, list_confirmed_keys, False)  # 知识图谱门禁阶段复核

    # 首次缺依赖时询问是否按官方文档人工安装。
    if status == "awaiting_codebase_memory_install_confirmation":

        # 单一必答问题明确声明工具不会自动下载安装器。
        list_questions = [  # 人工安装确认问题
            {
                "question_id": "codebase-memory-install",  # 稳定问题标识
                "answer_key": CODEBASE_MEMORY_INSTALL_CONFIRM_KEY,  # 安装确认答案键
                "required": True,  # 知识图谱启用态必须回答
                "branch": "all",  # 所有项目类型共享依赖门禁
                "ask": (  # 人工安装确认问题文本
                    "检测到已启用 codebase-memory-mcp，但当前环境缺少可用依赖或 Codex MCP 配置。"
                    "是否确认按官方 release 手工安装？本工具不会自动下载或执行安装器。"
                ),
                "options": [  # 安装或保持阻断的可选动作
                    interactive_option("查看安装步骤", True, "手工安装后重启 Codex，再恢复当前访谈。", True),  # 推荐人工安装动作
                    interactive_option(  # 保持知识图谱门禁阻断的替代动作
                        "暂不安装",  # 拒绝人工安装的标签
                        False,  # 拒绝安装的布尔答案
                        "保持阻断，除非把 use_codebase_memory_mcp 改为 false。",  # 拒绝后的流程边界
                        False,  # 非推荐选项标记
                    ),
                ],
            }
        ]

        # 安装指引覆盖 Windows、Linux、校验和、重启与恢复步骤。
        str_confirmation_question = (  # 官方人工安装操作说明
            f"官方发布页：{RELEASES_URL}。Windows 下载 windows-amd64.zip 和 checksums，运行 "
            "Unblock-File .\\install.ps1 后执行 .\\install.ps1；Linux 按架构下载 amd64/arm64 "
            "文件并校验 checksum，再执行 ./install.sh。完成后重启 Codex 并 --resume。"
        )

        # 下一动作由状态机的确认答案入口处理。
        str_next_action = "confirm_codebase_memory_mcp_install"  # 人工安装确认动作

    # 已确认安装后保持阻断，直到重启后的依赖探测真实通过。
    else:

        # 完成等待态不重复询问确认问题。
        list_questions = []  # 安装完成等待态问题集合

        # 提示只陈述外部操作，不声称工具已经完成安装。
        str_confirmation_question = (  # 安装完成与恢复说明
            f"完成 {RELEASES_URL} 的人工安装与 Codex MCP 配置后，重启 Codex 并执行 --resume。"  # 外部完成提示
        )

        # 恢复动作会重新执行真实依赖探测。
        str_next_action = "resume_after_codebase_memory_mcp_install"  # 安装后恢复动作

    # 统一五元组与其他状态处理器保持相同协议。
    return list_current_group, list_questions, review, str_confirmation_question, str_next_action

# 远程安装状态生成交互字段。
def remote_installation_step(
    state: dict[str, Any],
    status: str,
    kind: object,
    list_confirmed_keys: list[str],
    remote_gate: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any], str, str]:
    """构造远程技能安装阶段载荷。

    参数：state 为状态，status 为阶段，kind 为类型，list_confirmed_keys 为确认键，remote_gate 为门禁。
    数据合同：list_confirmed_keys 的 shape=(n,)，dtype=str，unit=无量纲；
    state 与 remote_gate 是字段映射，不适用数值 shape、dtype 或 unit。
    返回：安装阶段五元组。
    """

    # 安装阶段无普通问题。
    list_current_group: list[str] = []  # 远程安装门禁的空问题组

    # 安装状态共享复核。
    dict_review = stage_review(state, kind, list_confirmed_keys, False)  # 远程安装阶段复核

    # 已知目录生成安装提示。
    path_remote_skill_dir = Path(remote_gate["skill_dir"]) if remote_gate.get("skill_dir") else None  # 远程技能目录

    # 提示绑定当前副本。
    str_confirmation_question = (  # 远程安装命令提示
        remote_install_command_hint(path_remote_skill_dir)  # 当前副本命令
        if path_remote_skill_dir  # 已探测目录
        else remote_install_command_hint()  # 通用提示
    )

    # 缺少依赖时确认安装。
    if status == "awaiting_remote_install_confirmation":

        # 问题决定安装或阻断。
        list_questions = [  # erie 缺失时的安装决策问题
            {
                "question_id": "remote-install",  # erie 问询标识
                "answer_key": REMOTE_INSTALL_CONFIRM_KEY,  # SSH 技能决策键
                "required": True,  # 安装决策必答
                "branch": "all",  # 全部项目类型
                "ask": "检测到需要远程服务器，但当前环境缺少 erie-remote-ssh。是否确认先安装该技能？如果不安装，需要把 use_remote_server 改为 false 才能继续。",  # 安装问题
                "options": [  # 依赖处置选项
                    {  # 推荐安装选项
                        "label": "安装技能",  # 安装动作标签
                        "value": True,  # 接受安装的布尔值
                        "description": "确认后先完成依赖安装，再继续远程服务器选择。",  # 安装后流程
                        "recommended": True,  # 默认推荐安装依赖
                    },
                    interactive_option(  # 暂缓动作
                        "暂不安装",  # 拒绝安装标签
                        False,  # 拒绝安装值
                        "保持阻断状态，除非把 use_remote_server 改为 false。",  # 阻断边界
                        False,  # 暂不安装不作为默认建议
                    ),
                ],
            }
        ]

        # 确认答案由状态机安装入口处理。
        str_next_action = "confirm_remote_ssh_install"  # 远程技能安装确认动作

    # 确认后等待外部安装。
    else:

        # 等待期不重复提问。
        list_questions = []  # 等待远程技能可用时的空问题集合

        # 恢复时重查依赖。
        str_next_action = "resume_after_remote_ssh_install"  # 远程技能安装后的探测动作

    # 返回安装五元组。
    return list_current_group, list_questions, dict_review, str_confirmation_question, str_next_action

# 远程配置状态生成交互字段。
def remote_configuration_step(
    state: dict[str, Any],
    status: str,
    kind: object,
    list_confirmed_keys: list[str],
    remote_gate: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any], str, str]:
    """构造远程服务器配置阶段载荷。

    参数：state 为状态，status 为阶段，kind 为类型，list_confirmed_keys 为确认键，remote_gate 为门禁。
    数据合同：list_confirmed_keys 的 shape=(n,)，dtype=str，unit=无量纲；
    state 与 remote_gate 是字段映射，不适用数值 shape、dtype 或 unit。
    返回：配置阶段五元组。
    """

    # 配置阶段无普通问题。
    list_current_group: list[str] = []  # 远程配置门禁的空问题组

    # 配置状态共享复核。
    dict_review = stage_review(state, kind, list_confirmed_keys, False)  # 远程配置阶段复核

    # 缺少列表时选择配置模式。
    if status == "awaiting_remote_configuration_confirmation":

        # 选项顺序固定。
        list_questions = [  # 无服务器列表时的配置模式问题
            {
                "question_id": "remote-config",  # 配置问询标识
                "answer_key": REMOTE_CONFIGURATION_MODE_KEY,  # 配置模式键
                "required": True,  # 配置模式必答
                "branch": "all",  # 全部远程项目
                "ask": "当前没有可用的远程服务器列表。是否进入远程服务器配置流程？",  # 配置问题
                "options": [  # 三种配置动作
                    interactive_option(  # 推荐引导式配置
                        "guided",  # 引导模式标签
                        "guided",  # 引导模式值
                        "使用 erie-remote-ssh 的 configure --interactive 走引导式配置。",  # 引导说明
                        True,  # 默认推荐引导模式
                    ),
                    interactive_option(  # 手动准备列表
                        "manual",  # 手动模式标签
                        "manual",  # 手动模式值
                        "用户手动准备 server list 和 SSH 配置，然后回来继续。",  # 手动责任
                        False,  # 非默认模式
                    ),
                    interactive_option(  # 取消并阻断
                        "cancel",  # 取消动作标签
                        "cancel",  # 取消动作值
                        "保持阻断状态，除非把 use_remote_server 改为 false。",  # 取消边界
                        False,  # 非推荐动作
                    ),
                ],
            }
        ]

        # 提示说明恢复动作。
        str_confirmation_question = "选择 guided 或 manual 后，完成服务器配置，再执行 --resume 继续。"  # 配置模式确认提示

        # 模式由确认入口处理。
        str_next_action = "confirm_remote_server_configuration"  # 远程配置确认动作

    # 完成态重读服务器列表。
    else:

        # 等待态不重复提问。
        list_questions = []  # 配置完成等待态问题集合

        # guided 模式可展示命令。
        str_command_hint = ""  # 可选引导式配置命令

        # guided 模式生成命令。
        if remote_gate.get("skill_dir") and remote_gate.get("configuration_mode") == "guided":

            # 命令绑定当前技能副本。
            str_command_hint = remote_configure_command_hint(Path(str(remote_gate["skill_dir"])))  # 引导式配置命令

        # 缺少命令时用通用说明。
        str_confirmation_question = str_command_hint or "完成远程服务器配置后，执行 --resume 继续远程服务器选择。"  # 配置完成提示

        # 恢复时重查列表。
        str_next_action = "resume_after_remote_server_configuration"  # 配置后恢复动作

    # 返回配置五元组。
    return list_current_group, list_questions, dict_review, str_confirmation_question, str_next_action

# 生成远程依赖安装和服务器配置阶段的交互字段。
def remote_dependency_step(
    state: dict[str, Any],
    status: str,
    kind: object,
    list_confirmed_keys: list[str],
    remote_gate: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any], str, str] | None:
    """处理远程依赖状态。

    参数：state、status、kind、list_confirmed_keys、remote_gate 为上下文；返回五元组或 None。
    shape/维度：一维列表；dtype/类型：JSON；unit/单位：无。
    """

    # 先处理知识图谱依赖。
    tuple_codebase_step = codebase_memory_dependency_step(  # 可选知识图谱依赖五元组
        state,  # 当前访谈状态
        status,  # 当前分派状态
        kind,  # 项目类型事实
        list_confirmed_keys,  # 已确认答案键
    )

    # 命中时直接返回。
    if tuple_codebase_step is not None:

        # 统一五元组可直接交给主状态分派器。
        return tuple_codebase_step

    # 安装状态共享专用载荷构造器。
    if status in {"awaiting_remote_install_confirmation", "awaiting_remote_install_completion"}:

        # 安装构造器保持确认与恢复动作的原合同。
        return remote_installation_step(state, status, kind, list_confirmed_keys, remote_gate)

    # 配置状态共享专用载荷构造器。
    if status in {"awaiting_remote_configuration_confirmation", "awaiting_remote_configuration_completion"}:

        # 配置构造器保持模式选择与恢复动作的原合同。
        return remote_configuration_step(state, status, kind, list_confirmed_keys, remote_gate)

    # 其他状态继续交给后续状态处理器。
    return None

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
    """处理本地收集与对齐状态。

    参数：state、status、kind、list_group_ids、list_confirmed_keys 为上下文；返回五元组或 None。
    shape/维度：一维列表；dtype/类型：JSON；unit/单位：无。
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

    # 默认沿用当前组。
    list_current_group = list_group_ids  # 保留原状态机的当前分组语义

    # 生成本地交互字段。
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

# 状态处理器解析集中返回统一五元组，避免主载荷构造器重复解包分支。
def resolve_interactive_step(
    state: dict[str, Any],
    status: str,
    kind: object,
    str_mode: str,
    list_group_ids: list[str],

    # 确认键和远程证据共同决定状态处理器输出。
    list_confirmed_keys: list[str],
    remote_gate: dict[str, Any],
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any], str, str]:
    """按处理器优先级解析当前状态对应的统一交互五元组。

    参数:
        state: 当前持久化设计访谈状态。
        status: 当前状态机状态。
        kind: 已确认或推断的项目类型。
        str_mode: interactive、takeover 或 read-only 模式。
        list_group_ids: 当前本地问题组标识。
        list_confirmed_keys: 已确认答案键集合。
        remote_gate: 远程依赖和服务器发现证据。

    返回:
        当前问题组、问题、复核摘要、确认提示和下一动作组成的五元组。

    数组契约:
        shape 为问题列表和 JSON 映射，dtype 为 JSON 兼容类型，unit 不适用。
    """

    # 四类独立处理器只返回统一五元组或 None。
    tuple_remote_step = remote_dependency_step(state, status, kind, list_confirmed_keys, remote_gate)  # 远程依赖结果

    # 完成态处理器负责只读和写入完成状态。
    tuple_completion = completion_step(state, status, kind, str_mode)  # 完成态结果

    # 设计审查处理器负责等待审查与返工状态。
    tuple_review = design_review_step(state, status, kind, list_confirmed_keys)  # 审查状态结果

    # 本地处理器负责普通问题组、额外要求和最终对齐。
    tuple_local = local_interview_step(state, status, kind, list_group_ids, list_confirmed_keys)  # 本地访谈结果

    # 公共解析器按稳定优先级选择首个已消费状态。
    str_dispatch = resolved_dispatch_status(  # 实际消费当前状态的处理器标识
        status,  # 处理器优先级解析状态
        tuple_remote_step,  # 远程依赖候选结果
        tuple_completion,  # 完成态候选结果
        tuple_review,  # 设计审查候选结果
        tuple_local,  # 本地访谈候选结果
    )

    # 已处理状态名映射回对应五元组，避免重复字段解包。
    dict_handled_steps = {  # 分派标识到处理器结果
        "remote_dependency_handled": tuple_remote_step,  # 远程依赖分派结果
        "completion_handled": tuple_completion,  # 完成态分派结果
        "design_review_handled": tuple_review,  # 审查态分派结果
        "local_interview_handled": tuple_local,  # 本地访谈分派结果
    }

    # 正常处理器命中时结果必为统一五元组。
    tuple_handled = dict_handled_steps.get(str_dispatch)  # 已命中处理器结果

    # 非空结果可直接返回给主载荷构造器。
    if tuple_handled is not None:

        # 类型与统一处理器协议一致。
        return tuple_handled

    # 路由映射状态由需要完整远程门禁上下文的专用步骤处理。
    if str_dispatch == "awaiting_remote_server_route_mapping":

        # 专用步骤同样返回统一五元组。
        return remote_route_mapping_step(state, kind, list_confirmed_keys, remote_gate)

    # 未知或损坏状态进入可恢复的继续/重置交互步骤。
    return fallback_interview_step(state, kind, list_group_ids, list_confirmed_keys)

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

    # 第三十六项来源
    remote_gate = remote_gate_payload(state)  # 第三十六项载荷

    # 状态处理器统一解析为五元组，主函数只负责字段命名。
    tuple_step = resolve_interactive_step(  # 当前状态的统一交互步骤
        state,  # 统一步骤读取的状态记录
        status,  # 统一步骤消费的分派状态
        kind,  # 统一步骤使用的项目类型
        str_mode,  # 当前执行模式

        # 问题组、确认键和远程门禁完成步骤解析上下文。
        list_group_ids,  # 当前问题组标识
        list_confirmed_keys,  # 阶段复核使用的确认键
        remote_gate,  # 路由步骤使用的远程证据
    )

    # 五元组首项是当前问题组标识。
    list_current_group = tuple_step[0]  # 当前问题组

    # 次项是返回给用户的结构化问题集合。
    list_questions = tuple_step[1]  # 当前问题集合

    # 第三项是已确认字段和待确认字段复核摘要。
    review = tuple_step[2]  # 当前阶段复核摘要

    # 第四项是当前状态的人类可读确认提示。
    str_confirmation_question = tuple_step[3]  # 当前确认提示

    # 第五项是客户端或用户应执行的下一动作。
    str_next_action = tuple_step[4]  # 当前下一动作

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
