from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, resolve_project, run_git


DATE_RE = re.compile(r"Last updated:\s*(\d{4}-\d{2}-\d{2})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check whether AGENTS.md may be stale versus git history.")
    parser.add_argument("project", nargs="?", default=".")
    args = parser.parse_args()
    project = resolve_project(args.project)
    agents = project / "AGENTS.md"
    changed_files: list[str] = []
    last_updated = None
    if agents.exists():
        text = agents.read_text(encoding="utf-8", errors="ignore")
        match = DATE_RE.search(text)
        if match:
            last_updated = match.group(1)

    if last_updated:
        git_result = run_git(project, ["log", "--name-only", "--pretty=format:", f"--since={last_updated} 00:00:00"])
    else:
        git_result = run_git(project, ["status", "--short"])
    if git_result.returncode == 0:
        changed_files = sorted({line.strip() for line in git_result.stdout.splitlines() if line.strip() and not line.strip().endswith("AGENTS.md")})

    emit_json({
        "agents_file": str(agents),
        "last_updated": last_updated,
        "stale": bool(changed_files) or last_updated is None,
        "changed_files": changed_files,
    })


if __name__ == "__main__":
    main()
