from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import SKIP_DIRS, emit_json, resolve_project


MANAGED_PREFIX = "<!-- Managed by agents-md-generator:"


def is_managed(path: Path) -> bool:
    if path.is_symlink():
        return True
    if path.exists() and path.is_file():
        try:
            return path.read_text(encoding="utf-8", errors="ignore").startswith(MANAGED_PREFIX)
        except OSError:
            return False
    return False


def create_link_or_shim(path: Path, warnings: list[str], actions: list[str]) -> None:
    if path.exists() and not is_managed(path):
        warnings.append(f"Preserved existing non-managed {path.name}")
        return
    if path.exists() or path.is_symlink():
        path.unlink()
    try:
        os.symlink("AGENTS.md", path)
        actions.append(f"Created symlink {path.name} -> AGENTS.md")
    except OSError:
        path.write_text(f"{MANAGED_PREFIX} shim -->\n@AGENTS.md\n", encoding="utf-8")
        warnings.append(f"Symlink unavailable; wrote managed shim {path.name}")


def should_skip(path: Path, project: Path, include_skipped: bool = False) -> bool:
    if include_skipped:
        return False
    try:
        parts = path.relative_to(project).parts
    except ValueError:
        parts = path.parts
    return bool(set(parts) & SKIP_DIRS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create CLAUDE.md and GEMINI.md shims for AGENTS.md files.")
    parser.add_argument("project", nargs="?", default=".")
    parser.add_argument("--include-skipped", action="store_true", help="Also scan skipped directories such as ref, vendor, and build outputs.")
    args = parser.parse_args()
    project = resolve_project(args.project)
    actions: list[str] = []
    warnings: list[str] = []
    for agents in sorted(project.rglob("AGENTS.md")):
        if should_skip(agents, project, args.include_skipped):
            continue
        for name in ("CLAUDE.md", "GEMINI.md"):
            create_link_or_shim(agents.parent / name, warnings, actions)
    emit_json({"actions": actions, "warnings": warnings})


if __name__ == "__main__":
    main()
