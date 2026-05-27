from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, resolve_project
from manage_docs_evolution import *
from manage_docs_experience import *
from manage_docs_release import *
from manage_docs_scaffold_session import *
from manage_docs_shared import *
from manage_docs_sync_verify import *


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage AGENTS.md docs governance artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scaffold_parser = subparsers.add_parser("scaffold")
    scaffold_parser.add_argument("project", nargs="?", default=".")
    scaffold_parser.add_argument("--bootstrap-sessions", action="store_true")

    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("project", nargs="?", default=".")

    handoff_parser = subparsers.add_parser("handoff")
    handoff_parser.add_argument("project", nargs="?", default=".")
    handoff_parser.add_argument("--input", default=None)

    start_session_parser = subparsers.add_parser("start-session")
    start_session_parser.add_argument("project", nargs="?", default=".")
    start_session_parser.add_argument("--input", default=None)

    resume_check_parser = subparsers.add_parser("resume-check")
    resume_check_parser.add_argument("project", nargs="?", default=".")
    resume_check_parser.add_argument("--conversation-log", default=None)

    resume_repair_parser = subparsers.add_parser("resume-repair")
    resume_repair_parser.add_argument("project", nargs="?", default=".")
    resume_repair_parser.add_argument("--input", default=None)

    repair_handoff_parser = subparsers.add_parser("repair-handoff-names")
    repair_handoff_parser.add_argument("project", nargs="?", default=".")
    repair_handoff_parser.add_argument("--write", action="store_true")

    experience_parser = subparsers.add_parser("experience")
    experience_parser.add_argument("project", nargs="?", default=".")
    experience_parser.add_argument("--force", action="store_true")
    experience_parser.add_argument("--payload", default=None)

    evolve_parser = subparsers.add_parser("evolve")
    evolve_parser.add_argument("project", nargs="?", default=".")
    evolve_parser.add_argument("--force", action="store_true")

    import_evolution_parser = subparsers.add_parser("import-evolution")
    import_evolution_parser.add_argument("project", nargs="?", default=".")
    import_evolution_parser.add_argument("--bundle", default=None)

    development_parser = subparsers.add_parser("development")
    development_parser.add_argument("project", nargs="?", default=".")
    development_parser.add_argument("--stage", required=True)
    development_parser.add_argument("--input", default=None)

    changelog_parser = subparsers.add_parser("git-changelog")
    changelog_parser.add_argument("project", nargs="?", default=".")
    changelog_parser.add_argument("--input", default=None)

    bootstrap_parser = subparsers.add_parser("bootstrap-experience")
    bootstrap_parser.add_argument("project", nargs="?", default=".")
    bootstrap_parser.add_argument("--force", action="store_true")

    sync_root_parser = subparsers.add_parser("sync-root-agents")
    sync_root_parser.add_argument("project", nargs="?", default=".")
    sync_root_parser.add_argument("--write", action="store_true")
    sync_root_parser.add_argument("--installed-skill-dir", default=None)
    sync_root_parser.add_argument("--mark-verified", action="store_true")

    sync_global_parser = subparsers.add_parser("sync-global-codex-agents")
    sync_global_parser.add_argument("project", nargs="?", default=".")
    sync_global_parser.add_argument("--write", action="store_true")
    sync_global_parser.add_argument("--codex-home", default=None)

    release_gate_parser = subparsers.add_parser("release-gate")
    release_gate_parser.add_argument("project", nargs="?", default=".")
    release_gate_parser.add_argument("--version", required=True)
    release_gate_parser.add_argument("--skill-dir", required=True)
    release_gate_parser.add_argument("--phase", choices=["pre", "post"], default="pre")
    release_gate_parser.add_argument("--install-intent", choices=["unspecified", "requested", "skipped"], default="unspecified")

    release_prepare_parser = subparsers.add_parser("release-prepare")
    release_prepare_parser.add_argument("project", nargs="?", default=".")
    release_prepare_parser.add_argument("--version", required=True)
    release_prepare_parser.add_argument("--skill-dir", required=True)

    package_release_parser = subparsers.add_parser("package-release")
    package_release_parser.add_argument("project", nargs="?", default=".")
    package_release_parser.add_argument("--version", required=True)
    package_release_parser.add_argument("--skill-dir", required=True)

    branch_gate_parser = subparsers.add_parser("branch-gate")
    branch_gate_parser.add_argument("project", nargs="?", default=".")

    work_folder_gate_parser = subparsers.add_parser("work-folder-gate")
    work_folder_gate_parser.add_argument("project", nargs="?", default=".")
    work_folder_gate_parser.add_argument("--skill-dir", required=True)
    work_folder_gate_parser.add_argument("--mode", choices=["development", "release"], default="development")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("project", nargs="?", default=".")

    args = parser.parse_args()
    project = resolve_project(args.project)
    if args.command == "scaffold":
        result = scaffold(project)
        if getattr(args, "bootstrap_sessions", False):
            result["bootstrap_experience"] = bootstrap_experience(project)
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "preflight":
        emit_json(preflight_docs(project))
    elif args.command == "handoff":
        result = write_handoff(project, args.input)
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "start-session":
        result = write_active_session(project, args.input)
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "resume-check":
        result = resume_check(project, args.conversation_log)
        emit_json(result)
        if result.get("blocking"):
            raise SystemExit(1)
    elif args.command == "resume-repair":
        result = resume_repair(project, args.input)
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "repair-handoff-names":
        result = repair_handoff_names(project, write=args.write)
        emit_json(result)
        if result.get("errors") or (args.write and result.get("handoff_naming", {}).get("blocking")):
            raise SystemExit(1)
    elif args.command == "experience":
        result = write_experience(project, force=args.force, payload_path=args.payload)
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "evolve":
        result = run_evolution(project, force=args.force)
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "import-evolution":
        result = import_evolution(project, bundle_path=args.bundle)
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "development":
        emit_json(write_development(project, args.stage, args.input))
    elif args.command == "git-changelog":
        emit_json(write_git_changelog(project, args.input))
    elif args.command == "bootstrap-experience":
        result = bootstrap_experience(project, force=args.force)
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "sync-root-agents":
        result = sync_root_agents(
            project,
            write=args.write,
            installed_skill_dir_override=args.installed_skill_dir,
            mark_verified=args.mark_verified,
        )
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "sync-global-codex-agents":
        result = sync_global_codex_agents(project, write=args.write, codex_home=args.codex_home)
        emit_json(result)
        if result.get("errors"):
            raise SystemExit(1)
    elif args.command == "release-gate":
        result = release_gate(project, args.version, args.skill_dir, args.phase, args.install_intent)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)
    elif args.command == "release-prepare":
        result = release_prepare(project, args.version, args.skill_dir)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)
    elif args.command == "package-release":
        result = package_release(project, args.version, args.skill_dir)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)
    elif args.command == "branch-gate":
        result = branch_gate(project)
        emit_json(result)
        if not result["approved"]:
            raise SystemExit(1)
    elif args.command == "work-folder-gate":
        result = work_folder_gate(project, args.skill_dir, args.mode)
        emit_json(result)
        if not result["ok"]:
            raise SystemExit(1)
    elif args.command == "verify":
        result = verify_docs(project)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
