from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any
from datetime import datetime

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


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def backup_root_for(destination: Path) -> Path:
    return destination.parent.parent / "skill_backups"


def unique_backup_path(destination: Path) -> Path:
    root = backup_root_for(destination)
    base = root / f"{destination.name}-{stamp()}"
    candidate = base
    index = 2
    while candidate.exists():
        candidate = Path(f"{base}-{index}")
        index += 1
    return candidate


def protected_evolution_files(root: Path) -> list[Path]:
    evolution = root / "assets" / "templates" / "evolution"
    candidates: list[Path] = []
    for family in ("engineering-template", "skill-template"):
        family_root = evolution / family
        if family_root.is_dir():
            candidates.extend(path for path in sorted(family_root.rglob("*")) if path.is_file())
    return candidates


def conflict_copy_path(target: Path) -> Path:
    candidate = target.with_name(f"{target.stem}.installed-template-conflict{target.suffix}")
    index = 2
    while candidate.exists():
        candidate = target.with_name(f"{target.stem}.installed-template-conflict-{index}{target.suffix}")
        index += 1
    return candidate


def preserve_evolution_templates(backup: Path, destination: Path) -> tuple[list[str], list[dict[str, str]]]:
    preserved: list[str] = []
    conflicts: list[dict[str, str]] = []
    for old_path in protected_evolution_files(backup):
        relative = old_path.relative_to(backup)
        target = destination / relative
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_path, target)
            preserved.append(relative.as_posix())
            continue
        if target.read_bytes() == old_path.read_bytes():
            preserved.append(relative.as_posix())
            continue
        conflict_target = conflict_copy_path(target)
        shutil.copy2(old_path, conflict_target)
        conflicts.append({
            "relative_path": relative.as_posix(),
            "installed_version": str(conflict_target),
            "new_version": str(target),
        })
    return preserved, conflicts


def copy_skill(skill_dir: Path, destination: Path, replace: bool) -> dict[str, Any]:
    backup_path: Path | None = None
    preserved: list[str] = []
    conflicts: list[dict[str, str]] = []
    if destination.exists():
        if not replace:
            raise FileExistsError(f"target already exists: {destination}")
        backup_path = unique_backup_path(destination)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(destination), str(backup_path))
    destination.parent.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".git")
    shutil.copytree(skill_dir, destination, ignore=ignore)
    if backup_path is not None:
        preserved, conflicts = preserve_evolution_templates(backup_path, destination)
    return {
        "backup_path": str(backup_path) if backup_path else "",
        "template_preserved": preserved,
        "template_conflicts": conflicts,
    }


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
        "backup_path": "",
        "template_preserved": [],
        "template_conflicts": [],
        "confirmation_question": "发布包验证完成。是否安装这个技能？请选择是或否；默认是否，跳过安装。",
        "options": install_options(),
    }
    if args.target == "skip" or not args.write:
        emit_json(result)
        return
    assert destination is not None
    try:
        install_details = copy_skill(skill_dir, destination, args.replace)
    except SystemExit:
        raise
    except Exception as exc:
        emit_json({"errors": [str(exc)], **result})
        raise SystemExit(1)
    result.update(install_details)
    result["installed"] = True
    result["skipped"] = False
    emit_json(result)


if __name__ == "__main__":
    main()
