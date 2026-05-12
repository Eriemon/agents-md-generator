from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, resolve_project


def parse_skill_name(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^---\s*\n(.*?)\n---", text, flags=re.DOTALL)
    if not match:
        raise SystemExit(json.dumps({"errors": ["SKILL.md frontmatter is required"]}, indent=2))
    for line in match.group(1).splitlines():
        if line.strip().startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    raise SystemExit(json.dumps({"errors": ["SKILL.md frontmatter must include name"]}, indent=2))


def default_codex_home(raw: str | None) -> Path:
    if raw:
        return Path(raw).expanduser().resolve()
    env_home = os.environ.get("CODEX_HOME")
    if env_home:
        return Path(env_home).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def install_options() -> list[dict[str, Any]]:
    return [
        {
            "label": "否，跳过安装",
            "value": "skip",
            "description": "默认选项；不复制发布包到任何 skills 目录。",
            "recommended": True,
        },
        {
            "label": "安装到 Codex",
            "value": "codex",
            "description": "复制到 $CODEX_HOME/skills/<skill-name> 或 ~/.codex/skills/<skill-name>。",
            "recommended": False,
        },
        {
            "label": "自定义 skills 目录",
            "value": "custom",
            "description": "复制到用户提供的 skills 根目录下的 <skill-name>。",
            "recommended": False,
        },
    ]


def target_path(skill_name: str, target: str, codex_home: str | None, custom_root: str | None) -> Path | None:
    if target == "skip":
        return None
    if target == "codex":
        return default_codex_home(codex_home) / "skills" / skill_name
    if target == "custom":
        if not custom_root:
            raise SystemExit(json.dumps({"errors": ["--custom-root is required when --target custom"]}, indent=2))
        return Path(custom_root).expanduser().resolve() / skill_name
    raise SystemExit(json.dumps({"errors": ["--target must be skip, codex, or custom"]}, indent=2))


def copy_skill(skill_dir: Path, destination: Path, replace: bool) -> None:
    if destination.exists():
        if not replace:
            raise FileExistsError(f"target already exists: {destination}")
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".git")
    shutil.copytree(skill_dir, destination, ignore=ignore)


def main() -> None:
    parser = argparse.ArgumentParser(description="Install a verified Codex skill after explicit user confirmation.")
    parser.add_argument("skill_dir")
    parser.add_argument("--target", choices=["skip", "codex", "custom"], default="skip")
    parser.add_argument("--codex-home", default=None)
    parser.add_argument("--custom-root", default=None)
    parser.add_argument("--write", action="store_true", help="Actually copy the skill. Default is dry-run.")
    parser.add_argument("--replace", action="store_true", help="Replace an existing installed skill after user confirmation.")
    args = parser.parse_args()

    skill_dir = resolve_project(args.skill_dir)
    if not (skill_dir / "SKILL.md").is_file():
        emit_json({"errors": [f"missing SKILL.md: {skill_dir}"]})
        raise SystemExit(1)
    skill_name = parse_skill_name(skill_dir)
    destination = target_path(skill_name, args.target, args.codex_home, args.custom_root)
    result: dict[str, Any] = {
        "skill_dir": str(skill_dir),
        "skill_name": skill_name,
        "target": args.target,
        "destination": str(destination) if destination else "",
        "installed": False,
        "skipped": args.target == "skip" or not args.write,
        "confirmation_question": "发布包验证完成。是否安装这个技能？请选择是或否；默认是否，跳过安装。",
        "options": install_options(),
    }
    if args.target == "skip" or not args.write:
        emit_json(result)
        return
    assert destination is not None
    try:
        copy_skill(skill_dir, destination, args.replace)
    except SystemExit:
        raise
    except Exception as exc:
        emit_json({"errors": [str(exc)], **result})
        raise SystemExit(1)
    result["installed"] = True
    result["skipped"] = False
    emit_json(result)


if __name__ == "__main__":
    main()
