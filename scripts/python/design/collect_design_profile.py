"""收集、恢复并验证 AGENTS 项目的强制设计画像。"""

# 延迟注解求值兼容分片模块的运行时加载顺序。
from __future__ import annotations

# CLI 与动态模块加载支持直接脚本执行。
import argparse
import importlib
import sys

# 公共设计入口必须在导入兄弟模块前关闭字节码写入，避免污染可发布源码树。
sys.dont_write_bytecode = True  # 设计访谈 CLI 的源码树缓存保护。

# 路径、可调用合同和结构化类型描述公共接口。
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

# 设计画像构建器提供最终画像组装和写入合同。
from design_profile_builder import attach_alignment, build_profile, takeover_required, write_profile

# 画像构建器完成兄弟任务路径引导后再加载共享知识图谱门禁。
from codebase_memory_mcp import enforce_codebase_memory_write_gate

# 问题模块负责读取调用方提供的 JSON 答案。
from design_questions import read_json_object

# 状态机模块提供访谈生命周期和所有回答动作。
from design_interview_state import (
    answer_extra_requirements,
    answer_codebase_memory_install_confirmation,
    answer_group,
    answer_remote_configuration_confirmation,
    answer_remote_install_confirmation,
    answer_remote_server_route_mapping,
    advance_after_codebase_memory_gate,

    # 审查返工和问题组确认处理访谈的人机确认阶段。
    answer_review_rework,
    confirm_group,
    ensure_design_review_approved_on_write,
    enter_write_review,
    explicit_default_language_error,

    # 对齐、初始状态和交互载荷构成访谈核心生命周期。
    finalize_alignment,
    initial_state,
    initial_takeover_state,
    interactive_payload,
    is_active_state,

    # 兼容问题、持久化状态和远程刷新连接外围治理流程。
    legacy_question_payload,
    read_state,
    refresh_remote_gate,
    refresh_codebase_memory_gate,
    state_path,
    submit_design_review,
    write_state,
)

# 需要远程依赖重新检查的状态集合保持单一声明来源。
REMOTE_REFRESH_STATUSES = {  # 等待远程条件变化的访谈状态
    "awaiting_remote_install_completion",  # 等待远程安装实际完成
    "awaiting_remote_configuration_completion",  # 等待远程配置实际完成
    "awaiting_remote_install_confirmation",  # 等待用户确认安装结果
    "awaiting_remote_configuration_confirmation",  # 等待用户确认配置结果
    "awaiting_remote_server_route_mapping",  # 等待远程服务器路由映射
}

# 知识图谱安装等待态在恢复时重新检测本地二进制和 Codex 配置。
CODEBASE_MEMORY_REFRESH_STATUSES = {  # 恢复时必须重查本地依赖的知识图谱状态
    "awaiting_codebase_memory_install_confirmation",  # 等待人工安装确认
    "awaiting_codebase_memory_install_completion",  # 等待外部安装完成
}

# 回答处理器按状态路由到同签名的状态机动作。
ANSWER_HANDLER_BY_STATUS: dict[  # 访谈状态到回答动作的映射
    str,  # 访谈状态标识类型
    Callable[[Path, dict[str, Any], dict[str, Any]], dict[str, Any]],  # 回答动作签名
] = {
    "collecting_group": answer_group,  # 收集当前问题组答案
    "awaiting_group_confirmation": confirm_group,  # 确认当前问题组答案
    "awaiting_codebase_memory_install_confirmation": answer_codebase_memory_install_confirmation,  # 知识图谱安装确认动作
    "awaiting_remote_install_confirmation": answer_remote_install_confirmation,  # 确认远程安装
    "awaiting_remote_configuration_confirmation": answer_remote_configuration_confirmation,  # 确认远程配置
    "awaiting_remote_server_route_mapping": answer_remote_server_route_mapping,  # 提交路由映射
    "awaiting_extra_requirements": answer_extra_requirements,  # 提交额外要求
    "awaiting_final_alignment": finalize_alignment,  # 确认最终对齐
    "awaiting_design_review": submit_design_review,  # 提交设计审查
    "awaiting_review_rework": answer_review_rework,  # 提交审查返工
}

# 公共 CLI 模块按需加载，避免导入当前模块时修改 sys.path。
def load_agents_common() -> ModuleType:
    """加载跨任务目录共享的 ``agents_common`` 模块。

    参数：无。
    返回：已加载的公共 CLI 模块。
    异常：公共模块加载规格不完整时抛出 ``ImportError``。
    """

    # common 任务目录包含项目解析和 JSON 输出合同。
    path_common_dir = Path(__file__).resolve().parents[1] / "common"  # 公共任务模块目录

    # 显式规格加载优先于通配导入，保持依赖表面可审查。
    spec_agents_common = importlib.util.spec_from_file_location(  # 公共模块加载规格
        "agents_common",  # 公共模块运行时名称
        path_common_dir / "agents_common.py",  # 公共模块源码位置
    )

    # 缺失加载器说明源码布局不完整，不能继续执行 CLI。
    if spec_agents_common is None or spec_agents_common.loader is None:

        # 抛出稳定错误供入口调用方定位缺失公共依赖。
        raise ImportError("> ERR: [Python] cannot load agents_common module")

    # 模块对象承载公共 CLI 的路径解析和 JSON 输出函数。
    module_agents_common = importlib.util.module_from_spec(spec_agents_common)  # 公共 CLI 模块

    # 执行公共模块后再向调用点暴露其稳定接口。
    spec_agents_common.loader.exec_module(module_agents_common)

    # 返回已完成初始化的公共模块对象。
    return module_agents_common

# 项目解析包装器保持现有测试和调用方可替换的模块级接口。
def resolve_project(path_value: str | Path) -> Path:
    """解析并规范化项目根目录。

    参数：path_value 为 CLI 提供的项目路径。
    返回：已规范化的项目根目录。
    """

    # 公共模块执行项目边界和存在性检查。
    return load_agents_common().resolve_project(path_value)

# JSON 输出包装器统一交给公共 CLI 协议编码。
def emit_json(dict_payload: dict[str, Any]) -> None:
    """输出结构化 CLI 结果。

    参数：dict_payload 为待编码的结果载荷。
    返回：无。
    """

    # 公共输出器维持所有治理入口一致的机器格式。
    load_agents_common().emit_json(dict_payload)

# 参数构造器集中维护旧式画像与交互访谈的兼容 CLI 表面。
def build_argument_parser() -> argparse.ArgumentParser:
    """构建设计画像 CLI 参数解析器。

    参数：无。
    返回：已登记全部兼容参数的解析器。
    """

    # 入口摘要同时覆盖画像收集和强制设计验证。
    parser = argparse.ArgumentParser(  # 后续 add_argument 调用共享的画像 CLI 实例
        description="Collect and validate the mandatory AGENTS.md design profile."  # 帮助页说明强制设计画像职责
    )

    # 项目参数默认使用调用进程的当前目录。
    parser.add_argument("project", nargs="?", default=".")

    # kind 仅服务于保留的旧式平铺问题输出。
    parser.add_argument(
        "--kind",
        choices=["skill", "engineering"],
        default=None,
        help="Legacy flat-question output for the confirmed branch.",
    )

    # answers 指向批量画像构建所需的完整答案集。
    parser.add_argument(
        "--answers",
        default=None,
        help="JSON file containing the full aligned answer set.",
    )

    # answer-file 只承载当前交互步骤的局部答案。
    parser.add_argument(
        "--answer-file",
        default=None,
        help="JSON file containing answers for the current interactive interview step.",
    )

    # intent 区分只读访谈和最终写入审查路径。
    parser.add_argument(
        "--intent",
        choices=["write", "read_only"],
        default="write",
        help=(
            "Intent for interactive interviews: write completes without default subagent review, "
            "read_only completes without writes; use --enter-write-review for explicit design review."
        ),
    )

    # write 明确授权生成治理配置和文档产物。
    # 显式确认参数只授权解除 Git 索引跟踪，不删除本地产物。
    # 独立确认参数保护 codebase-memory 的本地持久化副本。
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write .agents/agents-control.json and create docs governance artifacts.",
    )

    # 确认开关只解除 Git 索引跟踪，不删除根级本地产物。
    parser.add_argument(
        "--confirm-codebase-memory-untrack",
        action="store_true",
        help="User confirmed removing .codebase-memory from the Git index while keeping local files.",
    )

    # start 启动普通分组设计访谈。
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start or restart the grouped interactive design interview.",
    )

    # start-takeover 为缺少健康根规则的旧项目启动最小接管访谈。
    parser.add_argument(
        "--start-takeover",
        action="store_true",
        help="Start the minimal takeover interview for an old workspace that lacks a healthy root AGENTS.md.",
    )

    # enter-write-review 把已完成的只读结果升级到写入审批。
    parser.add_argument(
        "--enter-write-review",
        action="store_true",
        help="Escalate a completed read_only interview into the explicit write review gate.",
    )

    # resume 恢复未完成的普通访谈。
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume the current unfinished grouped interactive design interview.",
    )

    # resume-takeover 仅恢复接管模式访谈。
    parser.add_argument(
        "--resume-takeover",
        action="store_true",
        help="Resume the current unfinished takeover interview.",
    )

    # reset-interview 显式放弃当前状态，以允许重新开始。
    parser.add_argument(
        "--reset-interview",
        action="store_true",
        help="Abandon the current interactive design interview so a new one can start.",
    )

    # 返回完整解析器供 CLI 入口和测试共享。
    return parser

# 启动动作负责区分已有会话、普通访谈和旧项目接管访谈。
def start_interview(path_project: Path, namespace_args: argparse.Namespace) -> None:
    """启动普通或接管设计访谈。

    参数：path_project 为项目根；namespace_args 为已解析 CLI 参数。
    返回：无；结果直接写入状态并输出。
    异常：接管初始化参数无效时抛出 ``SystemExit(1)``。
    """

    # 先读取持久化状态，禁止覆盖仍在进行的访谈。
    dict_state = read_state(path_project)  # 启动前访谈状态

    # 活动状态只能恢复，不能被新的启动请求替换。
    if is_active_state(dict_state):

        # 返回带 resume_required 的现有访谈载荷。
        emit_json(
            interactive_payload(
                path_project,
                dict_state or initial_state(path_project),
                status_override="resume_required",  # 强制调用方恢复既有审查
            )
        )

        # 已输出恢复提示后结束启动动作。
        return

    # 显式接管请求需要验证旧项目是否满足接管前提。
    if namespace_args.start_takeover:

        # 接管初始化可能因项目事实不足而拒绝执行。
        try:

            # 接管状态只收集恢复根治理所需的最小问题集。
            dict_state = initial_takeover_state(  # 新建接管访谈状态
                path_project,  # 需要接管治理的项目根目录
                intent=namespace_args.intent,  # 保留调用方读写意图
            )

        # ValueError 保留接管前置检查的业务诊断。
        except ValueError as error:

            # 失败载荷明确声明 takeover 模式。
            emit_json({"project": str(path_project), "mode": "takeover", "errors": [str(error)]})

            # 非零退出码阻止调用方误判访谈已经创建。
            raise SystemExit(1) from error

    # 普通启动会依据根规则健康状态自动选择完整或接管访谈。
    else:

        # 项目事实检查决定是否必须先恢复根 AGENTS 治理。
        bool_takeover_required, _ = takeover_required(path_project)  # 是否必须接管旧项目

        # 选择结果保持调用方 intent，不隐式升级只读请求。
        dict_state = (  # 新建普通或接管访谈状态
            initial_takeover_state(path_project, intent=namespace_args.intent)  # 自动接管状态
            if bool_takeover_required  # 根规则不健康时进入接管
            else initial_state(path_project, intent=namespace_args.intent)  # 健康项目完整访谈
        )

    # 状态必须先落盘，确保随后输出的恢复路径有效。
    write_state(path_project, dict_state)

    # 输出首个问题组或接管问题的交互载荷。
    emit_json(interactive_payload(path_project, dict_state))

# 写入审查升级动作拒绝无来源状态的直接调用。
def enter_review(path_project: Path) -> None:
    """把已完成的只读访谈升级到写入审查。

    参数：path_project 为项目根目录。
    返回：无；结果直接输出。
    异常：缺少访谈状态时抛出 ``SystemExit(1)``。
    """

    # 升级必须基于已经完成的只读访谈状态。
    dict_state = read_state(path_project)  # 待升级访谈状态

    # 缺失状态时要求调用方先启动访谈。
    if not dict_state:

        # 输出稳定的交互模式错误载荷。
        emit_json(
            {
                "project": str(path_project),
                "mode": "interactive",
                "errors": ["no interview state found; run --start first"],
            }
        )

        # 拒绝没有设计上下文的写入审查。
        raise SystemExit(1)

    # 状态机验证当前完成态并生成写入审查请求。
    emit_json(enter_write_review(path_project, dict_state))

# 恢复动作同时处理本地状态和可能变化的远程依赖。
def resume_interview(path_project: Path, bool_takeover: bool) -> None:
    """恢复普通或接管访谈并刷新远程等待状态。

    参数：path_project 为项目根；bool_takeover 表示仅接受接管访谈。
    返回：无；恢复后的载荷直接输出。
    异常：没有匹配的活动访谈时抛出 ``SystemExit(1)``。
    """

    # 恢复只读取当前项目唯一的持久化访谈状态。
    dict_state = read_state(path_project)  # 待恢复访谈状态

    # 已完成、已放弃或缺失状态均不能恢复。
    if not is_active_state(dict_state):

        # 输出普通交互模式下的无活动状态诊断。
        emit_json(
            {
                "project": str(path_project),
                "mode": "interactive",
                "errors": ["no active design interview state to resume"],
            }
        )

        # 非零退出码表明恢复请求未执行。
        raise SystemExit(1)

    # is_active_state 成功后状态按合同必须存在。
    if dict_state is None:

        # 防御性错误揭示状态机合同被破坏，而非用户输入问题。
        raise RuntimeError("> ERR: [Python] active interview state is missing")

    # 接管恢复开关不能用于普通访谈。
    if bool_takeover and str(dict_state.get("mode", "interactive")) != "takeover":

        # 输出 takeover 模式专用的状态不匹配诊断。
        emit_json(
            {
                "project": str(path_project),
                "mode": "takeover",
                "errors": ["no active takeover interview state to resume"],
            }
        )

        # 阻止普通访谈被错误地沿接管路径恢复。
        raise SystemExit(1)

    # 状态标识决定是否需要先重查远程条件。
    str_status = str(dict_state.get("status", ""))  # 恢复时访谈状态标识

    # 远程等待状态可能在两次 CLI 调用之间发生变化。
    if str_status in REMOTE_REFRESH_STATUSES:

        # 远程门禁返回非空载荷时应优先向调用方报告新状态。
        dict_refreshed = refresh_remote_gate(path_project, dict_state)  # 远程门禁刷新载荷

        # 非空刷新结果已经包含下一步操作信息。
        if dict_refreshed is not None:

            # 输出刷新后的远程等待或确认载荷。
            emit_json(dict_refreshed)

            # 避免随后又输出刷新前的交互载荷。
            return

    # 人工安装完成后恢复命令必须先重查依赖，不能相信旧状态。
    if str_status in CODEBASE_MEMORY_REFRESH_STATUSES:

        # 本轮真实依赖探测决定继续阻断还是恢复后续流程。
        dict_refreshed = refresh_codebase_memory_gate(path_project, dict_state)  # 知识图谱刷新响应

        # 非空载荷表示二进制或 MCP 配置仍未就绪。
        if dict_refreshed is not None:

            # 输出最新安装门禁事实而不是旧状态快照。
            emit_json(dict_refreshed)

            # 未就绪时不得继续远程或问题组状态迁移。
            return

        # 依赖就绪后恢复知识图谱门禁之后的原有流程。
        emit_json(advance_after_codebase_memory_gate(path_project, dict_state))

        # 恢复路径已输出唯一交互载荷。
        return

    # 非远程状态或无刷新变化时输出当前交互问题。
    emit_json(interactive_payload(path_project, dict_state))

# 重置动作保留状态文件并记录 abandoned 终态。
def reset_interview(path_project: Path) -> None:
    """将当前访谈标记为已放弃。

    参数：path_project 为项目根目录。
    返回：无；统一的 abandoned 载荷直接输出。
    """

    # 已存在状态需要显式写入 abandoned 标识。
    dict_state = read_state(path_project)  # 待放弃访谈状态

    # 无状态时仍返回相同的幂等重置结果。
    if dict_state:

        # abandoned 状态阻止后续 resume 误恢复旧访谈。
        dict_state["status"] = "abandoned"  # 访谈终止状态

        # 持久化终态，为审计和重新启动保留证据。
        write_state(path_project, dict_state)

    # 重置结果始终暴露规范状态文件位置。
    emit_json(
        {
            "project": str(path_project),
            "mode": "interactive",
            "status": "abandoned",
            "errors": [],
            "session_state_path": str(state_path(path_project)),
        }
    )

# 回答动作根据持久化状态选择唯一的状态机处理器。
def answer_interview(path_project: Path, path_answer_file: Path) -> None:
    """把答案文件路由到当前访谈状态处理器。

    参数：path_project 为项目根；path_answer_file 为答案 JSON 文件。
    返回：无；状态机结果直接输出。
    异常：没有活动访谈或状态不可回答时抛出 ``SystemExit(1)``。
    """

    # 每次回答都重新读取状态，避免使用过期的进程内快照。
    dict_state = read_state(path_project)  # 等待回答的访谈状态

    # 只有活动状态可以接收新的答案文件。
    if not is_active_state(dict_state):

        # 输出缺少活动访谈的稳定错误载荷。
        emit_json(
            {
                "project": str(path_project),
                "mode": "interactive",
                "errors": ["no active design interview state; run --start first"],
            }
        )

        # 阻止答案在没有对应问题时被静默忽略。
        raise SystemExit(1)

    # 活动状态按合同必须携带实际状态字典。
    if dict_state is None:

        # 防御性错误揭示状态机活动判断与返回值不一致。
        raise RuntimeError("> ERR: [Python] answer state is missing")

    # 答案文件解析失败时保留 read_json_object 的结构诊断。
    dict_payload = read_json_object(path_answer_file.resolve())  # 当前交互步骤答案

    # collecting_group 是旧状态缺失 status 字段时的兼容默认值。
    str_status = str(dict_state.get("status", "collecting_group"))  # 回答前访谈状态

    # 显式类型标注让状态到处理器的可空关系可审查。
    callable_handler: (  # 当前状态对应的可空回答动作
        Callable[[Path, dict[str, Any], dict[str, Any]], dict[str, Any]] | None  # 状态机动作签名
    ) = ANSWER_HANDLER_BY_STATUS.get(str_status)  # 当前状态回答处理器

    # 未登记状态不能消费答案，否则可能跳过强制门禁。
    if callable_handler is None:

        # 交互载荷保留当前状态并附加不可回答诊断。
        emit_json(
            interactive_payload(
                path_project,
                dict_state,
                errors=[f"cannot answer interview in status: {str_status}"],
            )
        )

        # 非零退出码要求调用方先处理状态漂移。
        raise SystemExit(1)

    # 已登记处理器负责验证答案并推进持久化状态。
    emit_json(callable_handler(path_project, dict_state, dict_payload))

# 写入语言门禁确保生成规则不会依赖隐式语言猜测。
def validate_write_language(path_project: Path, dict_answers: dict[str, Any]) -> None:
    """验证写入模式必须显式确认默认语言。

    参数：path_project 为项目根；dict_answers 为完整答案。
    返回：无。
    异常：默认语言未显式确认时抛出 ``SystemExit(1)``。
    """

    # 写入模式要求答案显式包含默认会话语言。
    list_language_errors = explicit_default_language_error(dict_answers)  # 默认语言确认错误

    # 非空错误集合阻止画像进入写入阶段。
    if list_language_errors:

        # 对齐载荷同时返回原始答案摘要和语言诊断。
        emit_json(
            attach_alignment(
                {"project": str(path_project), "errors": list_language_errors},
                dict_answers,
                dict_answers.get("development_type"),
            )
        )

        # 语言未确认时禁止生成 AGENTS 治理配置。
        raise SystemExit(1)

# 画像构建包装器把领域校验错误统一转换为 CLI 失败。
def build_valid_profile(path_project: Path, dict_answers: dict[str, Any]) -> dict[str, Any]:
    """构建画像并把验证失败转换为 CLI 诊断。

    参数：path_project 为项目根；dict_answers 为完整答案。
    返回：通过验证的设计画像。
    异常：画像验证失败时抛出 ``SystemExit(1)``。
    """

    # 构建器同时返回可空画像和全部对齐错误。
    dict_profile, list_errors = build_profile(  # 画像与验证错误
        path_project,  # 画像所属项目根目录
        dict_answers,  # 完整强制问题答案
    )

    # 任一对齐错误都会阻止画像被视为有效。
    if list_errors:

        # 错误载荷保留 development_type 以解释问题分支。
        emit_json(
            attach_alignment(
                {"project": str(path_project), "errors": list_errors},
                dict_answers,
                dict_answers.get("development_type"),
            )
        )

        # 非零退出码阻止调用方消费无效画像。
        raise SystemExit(1)

    # 无错误时构建器按合同必须返回画像对象。
    if dict_profile is None:

        # 防御性错误揭示构建器成功合同被破坏。
        raise RuntimeError("> ERR: [Python] validated design profile is missing")

    # 返回已通过全部领域校验的画像。
    return dict_profile

# 写入动作在审查批准后才允许持久化画像。
def write_valid_profile(
    path_project: Path,
    dict_answers: dict[str, Any],
    dict_profile: dict[str, Any],
    dict_result: dict[str, Any],
    *,
    confirm_codebase_memory_untrack: bool = False,
) -> None:
    """执行写入前审查门禁并持久化设计画像。

    参数：path_project 为项目根；dict_answers 为答案；dict_profile 为画像；
    dict_result 为输出载荷；confirm_codebase_memory_untrack 表示用户是否确认解除产物的 Git 跟踪。
    返回：无；成功时原位补充 ``written`` 字段。
    异常：设计审查未批准时抛出 ``SystemExit(1)``。
    """

    # 结构化设计审查证据必须与答案和画像哈希对齐。
    list_pending_errors = ensure_design_review_approved_on_write(  # 尚未解决的审查错误
        path_project,  # 被写入项目根目录
        dict_answers,  # 审查所依据的完整答案
        dict_profile,  # 审查所依据的设计画像
    )

    # 审查未通过时返回恢复访谈所需的上下文。
    if list_pending_errors:

        # 对齐载荷将审查错误绑定到当前画像类型。
        dict_payload = attach_alignment(  # 写入审查失败载荷
            {"project": str(path_project), "errors": list_pending_errors},  # 审查错误摘要
            dict_answers,  # 产生当前画像的答案
            dict_profile.get("kind"),  # 当前画像类型
        )

        # 访谈状态存在时向调用方提供恢复入口。
        dict_state = read_state(path_project)  # 待恢复审查访谈状态

        # 仅活动或已完成访谈才能生成 pending_interview 上下文。
        if dict_state:

            # resume_required 防止调用方把待审查状态误判为完成。
            dict_payload["pending_interview"] = interactive_payload(  # 待恢复访谈上下文
                path_project,  # 审查未完成的项目根目录
                dict_state,  # 等待恢复的访谈状态
                status_override="resume_required",  # 标记设计审查尚未批准
            )

        # 输出完整审查失败载荷后再终止写入。
        emit_json(dict_payload)

        # 非零退出码声明画像尚未写入。
        raise SystemExit(1)

    # 审查通过后仍需满足知识图谱依赖、索引和 Git 产物边界。
    dict_codebase_gate = enforce_codebase_memory_write_gate(  # 画像写入前知识图谱门禁结果
        path_project,  # 待写入画像的项目根
        dict_profile,  # 已通过审查的控制画像
        apply=True,  # 执行必要的忽略规则修复
        confirm_untrack=confirm_codebase_memory_untrack,  # 用户解除跟踪确认
    )

    # 门禁失败载荷包含缺依赖、缺索引或 Git 污染的精确诊断。
    if not dict_codebase_gate.get("ok"):

        # 机器可读诊断供调用方完成恢复动作。
        emit_json(dict_codebase_gate)

        # 任何知识图谱门禁失败都阻止画像写入。
        raise SystemExit(1)

    # 全部门禁通过后写入画像并记录实际产物路径。
    dict_result["written"] = str(  # 已写入画像文件路径
        write_profile(path_project, dict_profile)  # 审查通过后的画像产物
    )

# 批量画像动作兼容旧式问题输出和完整答案构建。
def collect_profile(path_project: Path, namespace_args: argparse.Namespace) -> None:
    """输出旧式问题或构建完整设计画像。

    参数：path_project 为项目根；namespace_args 为已解析 CLI 参数。
    返回：无；最终结果直接输出。
    """

    # 未提供答案文件时维持旧式问题查询接口。
    if not namespace_args.answers:

        # kind 决定返回 skill 或 engineering 的平铺问题集。
        emit_json(legacy_question_payload(path_project, namespace_args.kind))

        # 问题输出完成后不进入画像构建路径。
        return

    # 批量模式要求答案文件包含全部强制问题。
    dict_answers = read_json_object(  # 完整对齐答案
        Path(namespace_args.answers).resolve()  # 调用方提供的完整答案文件
    )

    # 只有写入模式需要额外执行显式默认语言门禁。
    if namespace_args.write:

        # 语言确认失败会在画像构建前终止。
        validate_write_language(path_project, dict_answers)

    # 所有模式都必须构建并验证同一份画像。
    dict_profile = build_valid_profile(path_project, dict_answers)  # 已验证设计画像

    # 成功载荷包含画像和答案对齐摘要。
    dict_result: dict[str, Any] = attach_alignment(  # 对齐信息与画像结果
        {"project": str(path_project), "profile": dict_profile, "errors": []},  # 画像成功摘要
        dict_answers,  # 用于构建画像的完整答案
        dict_profile.get("kind"),  # 已确认画像类型
    )

    # 写入开关启用设计审查和最终持久化。
    if namespace_args.write:

        # 审查未批准时该调用直接终止，不会修改成功载荷。
        write_valid_profile(
            path_project,
            dict_answers,
            dict_profile,
            dict_result,
            confirm_codebase_memory_untrack=namespace_args.confirm_codebase_memory_untrack,
        )

    # 只读验证和成功写入共享同一最终输出结构。
    emit_json(dict_result)

# CLI 编排器按互斥优先级分派访谈和批量画像动作。
def main() -> None:
    """解析参数并分派设计画像或交互访谈流程。

    参数：无。
    返回：无。
    异常：输入合同、访谈状态或画像验证失败时抛出 ``SystemExit(1)``。
    """

    # 显式类型标注确保 Namespace 属性由唯一解析器提供。
    namespace_args: argparse.Namespace = build_argument_parser().parse_args()  # 已解析 CLI 参数

    # 项目解析在任何状态读取或写入之前执行。
    path_project = resolve_project(namespace_args.project)  # 被治理项目根目录

    # write 只能与完整 answers 文件一起使用。
    if namespace_args.write and not namespace_args.answers:

        # 输出缺少写入输入的稳定参数诊断。
        emit_json({"project": str(path_project), "errors": ["--write requires --answers <file>"]})

        # 参数合同失败使用非零退出码。
        raise SystemExit(1)

    # 启动选项优先于其余访谈动作。
    if namespace_args.start or namespace_args.start_takeover:

        # 启动普通或显式接管访谈。
        start_interview(path_project, namespace_args)

        # 单次 CLI 调用只执行一个状态动作。
        return

    # 写入审查升级要求已有完成的只读访谈。
    if namespace_args.enter_write_review:

        # 执行只读到写入审查的状态升级。
        enter_review(path_project)

        # 审查升级完成后结束本次调用。
        return

    # 恢复选项读取并输出当前未完成访谈。
    if namespace_args.resume or namespace_args.resume_takeover:

        # resume_takeover 同时作为模式约束传入。
        resume_interview(path_project, namespace_args.resume_takeover)

        # 恢复载荷输出后结束本次调用。
        return

    # 重置显式放弃当前访谈状态。
    if namespace_args.reset_interview:

        # 重置动作保持幂等并记录 abandoned 状态。
        reset_interview(path_project)

        # 重置完成后不再处理答案或画像。
        return

    # 局部答案文件由当前活动状态决定处理器。
    if namespace_args.answer_file:

        # 答案路径在处理器内规范化和解析。
        answer_interview(path_project, Path(namespace_args.answer_file))

        # 单步回答完成后结束本次调用。
        return

    # 没有交互动作时进入旧式问题或批量画像路径。
    collect_profile(path_project, namespace_args)

# 直接脚本执行进入 CLI，模块导入仅暴露可测试函数。
if __name__ == "__main__":

    # 执行参数解析和设计画像工作流。
    main()

