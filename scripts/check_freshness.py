from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, resolve_project, run_git


TIMESTAMP_RE = re.compile(r"Last updated:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")
DATE_RE = re.compile(r"Last updated:\s*(\d{4}-\d{2}-\d{2})")


def parse_datetime(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def git_commit_time_for_file(project: Path, path: Path) -> datetime | None:
    try:
        rel_path = path.relative_to(project).as_posix()
    except ValueError:
        rel_path = str(path)
    result = run_git(project, ["log", "-1", "--format=%cI", "--", rel_path])
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    return parse_datetime(raw) if raw else None


def file_mtime(path: Path) -> datetime | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return None


def normalize_datetime(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check whether AGENTS.md may be stale versus git history.")
    parser.add_argument("project", nargs="?", default=".")
    args = parser.parse_args()
    project = resolve_project(args.project)
    agents = project / "AGENTS.md"
    changed_files: list[str] = []
    last_updated = None
    last_updated_raw = None
    comparison_source = "missing"
    if agents.exists():
        text = agents.read_text(encoding="utf-8", errors="ignore")
        timestamp_match = TIMESTAMP_RE.search(text)
        if timestamp_match:
            last_updated_raw = timestamp_match.group(1)
            last_updated = parse_datetime(last_updated_raw)
            comparison_source = "metadata_timestamp" if last_updated else "missing"
        else:
            date_match = DATE_RE.search(text)
            if date_match:
                last_updated_raw = date_match.group(1)
                last_updated = git_commit_time_for_file(project, agents)
                if last_updated is not None:
                    comparison_source = "git_commit_time"
                else:
                    last_updated = file_mtime(agents)
                    if last_updated is not None:
                        comparison_source = "file_mtime"
                    else:
                        fallback = parse_datetime(f"{last_updated_raw}T00:00:00")
                        last_updated = fallback
                        comparison_source = "date_midnight_fallback" if fallback else "missing"

    if last_updated:
        git_result = run_git(project, ["log", "--name-only", "--pretty=format:", f"--since={normalize_datetime(last_updated)}"])
    else:
        git_result = run_git(project, ["status", "--short"])
    if git_result.returncode == 0:
        changed_files = sorted(
            {
                line.strip()
                for line in git_result.stdout.splitlines()
                if line.strip() and not line.strip().endswith("AGENTS.md")
            }
        )

    emit_json({
        "agents_file": str(agents),
        "last_updated": normalize_datetime(last_updated) if last_updated else None,
        "last_updated_raw": last_updated_raw,
        "last_updated_at": normalize_datetime(last_updated) if last_updated else None,
        "comparison_source": comparison_source,
        "stale": bool(changed_files) or last_updated is None,
        "changed_files": changed_files,
    })


if __name__ == "__main__":
    main()
