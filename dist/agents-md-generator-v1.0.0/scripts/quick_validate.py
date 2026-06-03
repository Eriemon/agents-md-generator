from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import resolve_project


def quick_validate_path() -> Path:
    return Path.home() / ".codex" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the installed skill-creator quick_validate helper.")
    parser.add_argument("skill_dir", nargs="?", default=".")
    args = parser.parse_args()

    skill_dir = resolve_project(args.skill_dir)
    validator = quick_validate_path()
    if not validator.exists():
        raise SystemExit(f"quick_validate helper not found: {validator}")

    result = subprocess.run(
        [sys.executable, str(validator), str(skill_dir)],
        cwd=skill_dir.parent,
        text=True,
        capture_output=True,
        check=False,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    raise SystemExit(result.returncode)
