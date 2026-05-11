from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import detect_scopes, emit_json, parse_args, resolve_project


def main() -> None:
    parser = parse_args("Detect directories that may need scoped AGENTS.md files.")
    args = parser.parse_args()
    emit_json(detect_scopes(resolve_project(args.project)))


if __name__ == "__main__":
    main()

