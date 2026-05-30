from __future__ import annotations

from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents_common import emit_json, parse_args, project_profile, resolve_project
from source_governance import source_governance_report


def main() -> None:
    parser = parse_args("Check source-governance hard gates.")
    args = parser.parse_args()
    project = resolve_project(args.project)
    emit_json(source_governance_report(project, project_profile(project)))


if __name__ == "__main__":
    main()
