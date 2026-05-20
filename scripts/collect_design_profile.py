from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, resolve_project
from design_profile_builder import *
from design_questions import *
from design_interview_state import *
from design_remote_gate import *


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
            state = initial_takeover_state(project) if required else initial_state(project)
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
        if str(state.get("status", "")) in {
            "awaiting_remote_install_completion",
            "awaiting_remote_configuration_completion",
            "awaiting_remote_install_confirmation",
            "awaiting_remote_configuration_confirmation",
            "awaiting_remote_server_route_mapping",
        }:
            refreshed = refresh_remote_gate(project, state)
            if refreshed is not None:
                emit_json(refreshed)
                return
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
        if status == "awaiting_remote_install_confirmation":
            emit_json(answer_remote_install_confirmation(project, state, payload))
            return
        if status == "awaiting_remote_configuration_confirmation":
            emit_json(answer_remote_configuration_confirmation(project, state, payload))
            return
        if status == "awaiting_remote_server_route_mapping":
            emit_json(answer_remote_server_route_mapping(project, state, payload))
            return
        if status == "awaiting_extra_requirements":
            emit_json(answer_extra_requirements(project, state, payload))
            return
        if status == "awaiting_final_alignment":
            emit_json(finalize_alignment(project, state, payload))
            return
        if status == "awaiting_design_review":
            emit_json(submit_design_review(project, state, payload))
            return
        if status == "awaiting_review_rework":
            emit_json(answer_review_rework(project, state, payload))
            return
        emit_json(interactive_payload(project, state, errors=[f"cannot answer interview in status: {status}"]))
        raise SystemExit(1)

    if not args.answers:
        emit_json(legacy_question_payload(project, args.kind))
        return

    answers = read_json_object(Path(args.answers).resolve())
    if args.write:
        language_errors = explicit_default_language_error(answers)
        if language_errors:
            emit_json(attach_alignment({"project": str(project), "errors": language_errors}, answers, answers.get("development_type")))
            raise SystemExit(1)
    profile, errors = build_profile(project, answers)
    if errors:
        emit_json(attach_alignment({"project": str(project), "errors": errors}, answers, answers.get("development_type")))
        raise SystemExit(1)
    assert profile is not None
    result: dict[str, Any] = attach_alignment({"project": str(project), "profile": profile, "errors": []}, answers, profile.get("kind"))
    if args.write:
        pending_errors = ensure_design_review_approved_on_write(project, answers, profile)
        if pending_errors:
            payload = attach_alignment({"project": str(project), "errors": pending_errors}, answers, profile.get("kind"))
            state = read_state(project)
            if state:
                payload["pending_interview"] = interactive_payload(project, state, status_override="resume_required")
            emit_json(payload)
            raise SystemExit(1)
        result["written"] = str(write_profile(project, profile))
    emit_json(result)


if __name__ == "__main__":
    main()
