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
import argparse
from pathlib import Path
import sys

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断
from agents_common import emit_json, resolve_project
from design_profile_builder import *
from design_questions import *
from design_interview_state import *
from design_remote_gate import *


# 定义 main 的脚本治理处理入口。
def main() -> None:

    # 保留 parser 中间值，支撑 main 的当前计算步骤。
    parser = argparse.ArgumentParser(description="Collect and validate the mandatory AGENTS.md design profile.")  # parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--kind", choices=["skill", "engineering"], default=None, help="Legacy flat-question output for the confirmed branch.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--answers", default=None, help="JSON file containing the full aligned answer set.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--answer-file", default=None, help="JSON file containing answers for the current interactive interview step.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument(
        "--intent",
        choices=["write", "read_only"],
        default="write",
        help=(
            "Intent for interactive interviews: write keeps the existing review gate, "
            "read_only completes without subagent review."
        ),
    )

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--write", action="store_true", help="Write .agents/agents-control.json and create docs governance artifacts.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--start", action="store_true", help="Start or restart the grouped interactive design interview.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument(
        "--start-takeover",
        action="store_true",
        help="Start the minimal takeover interview for an old workspace that lacks a healthy root AGENTS.md.",
    )

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--enter-write-review", action="store_true", help="Escalate a completed read_only interview into the explicit write review gate.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--resume", action="store_true", help="Resume the current unfinished grouped interactive design interview.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--resume-takeover", action="store_true", help="Resume the current unfinished takeover interview.")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--reset-interview", action="store_true", help="Abandon the current interactive design interview so a new one can start.")

    # 收集 args 条目，保持 main 的处理顺序稳定。
    args = parser.parse_args()  # args 用于本步治理判断

    # 保留 project 中间值，支撑 main 的当前计算步骤。
    project = resolve_project(args.project)  # project 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if args.write and not args.answers:

        # 调用 emit_json 完成 main 的当前动作。
        emit_json({"project": str(project), "errors": ["--write requires --answers <file>"]})

        # 抛出 main 已确认的阻断原因。
        raise SystemExit(1)

    # 检查 main 的当前条件是否需要进入专门分支。
    if args.start or args.start_takeover:

        # 保留 state 中间值，支撑 main 的当前计算步骤。
        state = read_state(project)  # state 用于本步治理判断

        # 检查 main 的当前条件是否需要进入专门分支。
        if is_active_state(state):

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(interactive_payload(project, state or initial_state(project), status_override="resume_required"))

            # 返回 main 已整理完成的调用载荷。
            return

        # 检查 main 的当前条件是否需要进入专门分支。
        if args.start_takeover:

            # 保护 main 中允许失败的外部访问。
            try:

                # 保留 state 中间值，支撑 main 的当前计算步骤。
                state = initial_takeover_state(project, intent=args.intent)  # state 用于本步治理判断
            except ValueError as exc:

                # 调用 emit_json 完成 main 的当前动作。
                emit_json({"project": str(project), "mode": "takeover", "errors": [str(exc)]})

                # 抛出 main 已确认的阻断原因。
                raise SystemExit(1)
        else:

            # 保留 required、  中间值，支撑 main 的当前计算步骤。
            required, _ = takeover_required(project)  # required、  用于本步治理判断

            # 保留 state 中间值，支撑 main 的当前计算步骤。
            state = initial_takeover_state(project, intent=args.intent) if required else initial_state(project, intent=args.intent)  # state 用于本步治理判断

        # 调用 write_state 完成 main 的当前动作。
        write_state(project, state)

        # 调用 emit_json 完成 main 的当前动作。
        emit_json(interactive_payload(project, state))

        # 返回 main 已整理完成的调用载荷。
        return

    # 检查 main 的当前条件是否需要进入专门分支。
    if args.enter_write_review:

        # 保留 state 中间值，支撑 main 的当前计算步骤。
        state = read_state(project)  # state 用于本步治理判断

        # 检查 main 的当前条件是否需要进入专门分支。
        if not state:

            # 调用 emit_json 完成 main 的当前动作。
            emit_json({"project": str(project), "mode": "interactive", "errors": ["no interview state found; run --start first"]})

            # 抛出 main 已确认的阻断原因。
            raise SystemExit(1)

        # 调用 emit_json 完成 main 的当前动作。
        emit_json(enter_write_review(project, state))

        # 返回 main 已整理完成的调用载荷。
        return

    # 检查 main 的当前条件是否需要进入专门分支。
    if args.resume or args.resume_takeover:

        # 保留 state 中间值，支撑 main 的当前计算步骤。
        state = read_state(project)  # state 用于本步治理判断

        # 检查 main 的当前条件是否需要进入专门分支。
        if not is_active_state(state):

            # 调用 emit_json 完成 main 的当前动作。
            emit_json({"project": str(project), "mode": "interactive", "errors": ["no active design interview state to resume"]})

            # 抛出 main 已确认的阻断原因。
            raise SystemExit(1)

        # 检查 main 的当前条件是否需要进入专门分支。
        if args.resume_takeover and str(state.get("mode", "interactive")) != "takeover":

            # 调用 emit_json 完成 main 的当前动作。
            emit_json({"project": str(project), "mode": "takeover", "errors": ["no active takeover interview state to resume"]})

            # 抛出 main 已确认的阻断原因。
            raise SystemExit(1)

        # 检查 main 的当前条件是否需要进入专门分支。
        if str(state.get("status", "")) in {
            "awaiting_remote_install_completion",
            "awaiting_remote_configuration_completion",
            "awaiting_remote_install_confirmation",
            "awaiting_remote_configuration_confirmation",
            "awaiting_remote_server_route_mapping",
        }:

            # 保留 refreshed 中间值，支撑 main 的当前计算步骤。
            refreshed = refresh_remote_gate(project, state)  # refreshed 用于本步治理判断

            # 检查 main 的当前条件是否需要进入专门分支。
            if refreshed is not None:

                # 调用 emit_json 完成 main 的当前动作。
                emit_json(refreshed)

                # 返回 main 已整理完成的调用载荷。
                return

        # 调用 emit_json 完成 main 的当前动作。
        emit_json(interactive_payload(project, state))

        # 返回 main 已整理完成的调用载荷。
        return

    # 检查 main 的当前条件是否需要进入专门分支。
    if args.reset_interview:

        # 保留 state 中间值，支撑 main 的当前计算步骤。
        state = read_state(project)  # state 用于本步治理判断

        # 检查 main 的当前条件是否需要进入专门分支。
        if not state:

            # 调用 emit_json 完成 main 的当前动作。
            emit_json({"project": str(project), "mode": "interactive", "status": "abandoned", "errors": [], "session_state_path": str(state_path(project))})

            # 返回 main 已整理完成的调用载荷。
            return

        # 保留 中间载荷 中间值，支撑 main 的当前计算步骤。
        state["status"] = "abandoned"  # 中间载荷 用于本步治理判断

        # 调用 write_state 完成 main 的当前动作。
        write_state(project, state)

        # 调用 emit_json 完成 main 的当前动作。
        emit_json({"project": str(project), "mode": "interactive", "status": "abandoned", "errors": [], "session_state_path": str(state_path(project))})

        # 返回 main 已整理完成的调用载荷。
        return

    # 检查 main 的当前条件是否需要进入专门分支。
    if args.answer_file:

        # 保留 state 中间值，支撑 main 的当前计算步骤。
        state = read_state(project)  # state 用于本步治理判断

        # 检查 main 的当前条件是否需要进入专门分支。
        if not is_active_state(state):

            # 调用 emit_json 完成 main 的当前动作。
            emit_json({"project": str(project), "mode": "interactive", "errors": ["no active design interview state; run --start first"]})

            # 抛出 main 已确认的阻断原因。
            raise SystemExit(1)

        # 保留 payload 中间值，支撑 main 的当前计算步骤。
        payload = read_json_object(Path(args.answer_file).resolve())  # payload 用于本步治理判断

        # 收集 status 条目，保持 main 的处理顺序稳定。
        str_status = str(state.get("status", "collecting_group"))  # status 用于本步治理判断

        # 检查 main 的当前条件是否需要进入专门分支。
        if str_status == "collecting_group":

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(answer_group(project, state, payload))

            # 返回 main 已整理完成的调用载荷。
            return

        # 检查 main 的当前条件是否需要进入专门分支。
        if str_status == "awaiting_group_confirmation":

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(confirm_group(project, state, payload))

            # 返回 main 已整理完成的调用载荷。
            return

        # 检查 main 的当前条件是否需要进入专门分支。
        if str_status == "awaiting_remote_install_confirmation":

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(answer_remote_install_confirmation(project, state, payload))

            # 返回 main 已整理完成的调用载荷。
            return

        # 检查 main 的当前条件是否需要进入专门分支。
        if str_status == "awaiting_remote_configuration_confirmation":

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(answer_remote_configuration_confirmation(project, state, payload))

            # 返回 main 已整理完成的调用载荷。
            return

        # 检查 main 的当前条件是否需要进入专门分支。
        if str_status == "awaiting_remote_server_route_mapping":

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(answer_remote_server_route_mapping(project, state, payload))

            # 返回 main 已整理完成的调用载荷。
            return

        # 检查 main 的当前条件是否需要进入专门分支。
        if str_status == "awaiting_extra_requirements":

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(answer_extra_requirements(project, state, payload))

            # 返回 main 已整理完成的调用载荷。
            return

        # 检查 main 的当前条件是否需要进入专门分支。
        if str_status == "awaiting_final_alignment":

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(finalize_alignment(project, state, payload))

            # 返回 main 已整理完成的调用载荷。
            return

        # 检查 main 的当前条件是否需要进入专门分支。
        if str_status == "awaiting_design_review":

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(submit_design_review(project, state, payload))

            # 返回 main 已整理完成的调用载荷。
            return

        # 检查 main 的当前条件是否需要进入专门分支。
        if str_status == "awaiting_review_rework":

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(answer_review_rework(project, state, payload))

            # 返回 main 已整理完成的调用载荷。
            return

        # 调用 emit_json 完成 main 的当前动作。
        emit_json(interactive_payload(project, state, errors=[f"cannot answer interview in status: {str_status}"]))

        # 抛出 main 已确认的阻断原因。
        raise SystemExit(1)

    # 检查 main 的当前条件是否需要进入专门分支。
    if not args.answers:

        # 调用 emit_json 完成 main 的当前动作。
        emit_json(legacy_question_payload(project, args.kind))

        # 返回 main 已整理完成的调用载荷。
        return

    # 收集 answers 条目，保持 main 的处理顺序稳定。
    answers = read_json_object(Path(args.answers).resolve())  # answers 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if args.write:

        # 收集 language errors 条目，保持 main 的处理顺序稳定。
        language_errors = explicit_default_language_error(answers)  # language errors 用于本步治理判断

        # 检查 main 的当前条件是否需要进入专门分支。
        if language_errors:

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(attach_alignment({"project": str(project), "errors": language_errors}, answers, answers.get("development_type")))

            # 抛出 main 已确认的阻断原因。
            raise SystemExit(1)

    # 收集 profile、errors 条目，保持 main 的处理顺序稳定。
    profile, errors = build_profile(project, answers)  # profile、errors 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if errors:

        # 调用 emit_json 完成 main 的当前动作。
        emit_json(attach_alignment({"project": str(project), "errors": errors}, answers, answers.get("development_type")))

        # 抛出 main 已确认的阻断原因。
        raise SystemExit(1)

    # 说明该控制语句在脚本治理流程中的分支职责。
    assert profile is not None

    # 保留 result 中间值，支撑 main 的当前计算步骤。
    dict_result: dict[str, Any] = attach_alignment({"project": str(project), "profile": profile, "errors": []}, answers, profile.get("kind"))  # result 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if args.write:

        # 收集 pending errors 条目，保持 main 的处理顺序稳定。
        pending_errors = ensure_design_review_approved_on_write(project, answers, profile)  # pending errors 用于本步治理判断

        # 检查 main 的当前条件是否需要进入专门分支。
        if pending_errors:

            # 保留 payload 中间值，支撑 main 的当前计算步骤。
            payload = attach_alignment({"project": str(project), "errors": pending_errors}, answers, profile.get("kind"))  # payload 用于本步治理判断

            # 保留 state 中间值，支撑 main 的当前计算步骤。
            state = read_state(project)  # state 用于本步治理判断

            # 检查 main 的当前条件是否需要进入专门分支。
            if state:

                # 保留 中间载荷 中间值，支撑 main 的当前计算步骤。
                payload["pending_interview"] = interactive_payload(project, state, status_override="resume_required")  # 中间载荷 用于本步治理判断

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(payload)

            # 抛出 main 已确认的阻断原因。
            raise SystemExit(1)

        # 保留 中间载荷 中间值，支撑 main 的当前计算步骤。
        dict_result["written"] = str(write_profile(project, profile))  # 中间载荷 用于本步治理判断

    # 调用 emit_json 完成 main 的当前动作。
    emit_json(dict_result)


# 检查 模块入口 的当前条件是否需要进入专门分支。
if __name__ == "__main__":

    # 调用 main 完成 模块入口 的当前动作。
    main()


