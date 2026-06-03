from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, resolve_project
from manage_dirs_review import (
    apply_structure_fix,
    review_change,
    structure_gate,
    takeover_fix,
)
from manage_dirs_state import (
    CURRENT_STRUCTURE,
    DIR_MANAGER_DIR,
    DIR_MANAGER_MD,
    PLANNED_STRUCTURE,
    archive_dir_manager,
    init_dir_manager,
    scan_structure,
    verify_dir_manager,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Review and verify strict project directory management gates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("project", nargs="?", default=".")
    scan_parser.add_argument("--write", action="store_true")

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("project", nargs="?", default=".")

    review_parser = subparsers.add_parser("review")
    review_parser.add_argument("project", nargs="?", default=".")
    review_parser.add_argument("--input", required=True)
    review_parser.add_argument("--dry-run", action="store_true")

    structure_parser = subparsers.add_parser("structure-gate")
    structure_parser.add_argument("project", nargs="?", default=".")

    apply_fix_parser = subparsers.add_parser("apply-structure-fix")
    apply_fix_parser.add_argument("project", nargs="?", default=".")

    takeover_fix_parser = subparsers.add_parser("takeover-fix")
    takeover_fix_parser.add_argument("project", nargs="?", default=".")

    archive_parser = subparsers.add_parser("archive")
    archive_parser.add_argument("project", nargs="?", default=".")
    archive_parser.add_argument("--reason", default="force-confirmed directory override")
    archive_parser.add_argument("--review-file", default="")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("project", nargs="?", default=".")

    args = parser.parse_args()
    project = resolve_project(args.project)
    if args.command == "scan":
        structure = scan_structure(project)
        if args.write:
            (project / DIR_MANAGER_DIR).mkdir(parents=True, exist_ok=True)
            (project / CURRENT_STRUCTURE).write_text(json.dumps(structure, indent=2, sort_keys=True), encoding="utf-8")
        emit_json(structure)
    elif args.command == "init":
        emit_json(init_dir_manager(project))
    elif args.command == "review":
        result = review_change(project, args.input, dry_run=args.dry_run)
        emit_json(result)
        if not result["approved"]:
            raise SystemExit(1)
    elif args.command == "structure-gate":
        result = structure_gate(project)
        emit_json(result)
        if not result["approved"]:
            raise SystemExit(1)
    elif args.command == "apply-structure-fix":
        result = apply_structure_fix(project)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)
    elif args.command == "takeover-fix":
        result = takeover_fix(project)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)
    elif args.command == "archive":
        emit_json(archive_dir_manager(project, reason=args.reason, review_file=args.review_file))
    elif args.command == "verify":
        result = verify_dir_manager(project)
        emit_json(result)
        if result["errors"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
