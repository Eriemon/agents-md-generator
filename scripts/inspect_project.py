from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, inspect_project, parse_args, resolve_project


def main() -> None:
    parser = parse_args("Inspect project facts for AGENTS.md generation.")
    args = parser.parse_args()
    emit_json(inspect_project(resolve_project(args.project)))


if __name__ == "__main__":
    main()
