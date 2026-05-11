from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, extract_context, parse_args, resolve_project


def main() -> None:
    parser = parse_args("Extract AGENTS.md context candidates from docs, ADRs, utilities, CI, and quality configs.")
    args = parser.parse_args()
    emit_json(extract_context(resolve_project(args.project)))


if __name__ == "__main__":
    main()
