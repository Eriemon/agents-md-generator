from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, extract_commands, parse_args, resolve_project


def main() -> None:
    parser = parse_args("Extract AGENTS.md command candidates from project files.")
    args = parser.parse_args()
    emit_json(extract_commands(resolve_project(args.project)))


if __name__ == "__main__":
    main()

