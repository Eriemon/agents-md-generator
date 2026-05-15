from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any
from datetime import datetime

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from agents_common import emit_json, global_codex_agents_status, resolve_project


def fail_json(message: str) -> None:
    emit_json({"errors": [message]})
    raise SystemExit(1)


def parse_skill_name(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^---\s*\n(.*?)\n---", text, flags=re.DOTALL)
    if not match:
        raise SystemExit(json.dumps({"errors": ["SKILL.md frontmatter is required"]}, indent=2))
    for line in match.group(1).splitlines():
        if line.strip().startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    raise SystemExit(json.dumps({"errors": ["SKILL.md frontmatter must include name"]}, indent=2))


def parse_release_dir(release_dir: Path) -> tuple[str, str]:
    match = re.fullmatch(r"(.+)-(v\d+\.\d+\.\d+)", release_dir.name)
    if not match:
        fail_json(f"release directory must be a versioned release directory like <name>-vX.Y.Z: {release_dir}")
    return match.group(1), match.group(2)


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_receipt(release_dir: Path) -> tuple[Path, dict[str, Any]]:
    receipt_path = release_dir / "RELEASE_RECEIPT.json"
    if not receipt_path.is_file():
        fail_json(f"missing RELEASE_RECEIPT.json: {receipt_path}")
    try:
        data = json.loads(receipt_path.read_text(encoding="utf-8"))
    except Exception:
        fail_json(f"invalid RELEASE_RECEIPT.json: {receipt_path}")
    if not isinstance(data, dict):
        fail_json(f"invalid RELEASE_RECEIPT.json: {receipt_path}")
    return receipt_path, data


def is_probably_text_bytes(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n")


SANITIZED_PLACEHOLDERS = {
    "api_key": "<REDACTED_API_KEY>",
    "password": "<REDACTED_PASSWORD>",
    "email": "<REDACTED_EMAIL>",
    "local_path": "<REDACTED_LOCAL_PATH>",
}
SANITIZED_ASSIGNMENT_RULES = [
    (
        "api_key",
        re.compile(r"(?im)^(\s*[A-Z0-9_]*(?:API[_-]?KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET|TOKEN)[A-Z0-9_]*\s*[:=]\s*)(.+?)\s*$"),
    ),
    (
        "password",
        re.compile(r"(?im)^(\s*[A-Z0-9_]*PASSWORD[A-Z0-9_]*\s*[:=]\s*)(.+?)\s*$"),
    ),
]
SANITIZED_INLINE_RULES = [
    ("email", re.compile(r"(?<!\\)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", flags=re.IGNORECASE)),
    ("local_path", re.compile(r"[A-Za-z]:\\Users\\[^\r\n]+")),
    ("local_path", re.compile(r"/(?:Users|home)/[^\s]+")),
]
SANITIZED_BINARY_PATTERNS = [
    ("api_key", re.compile(br"sk-(?:live|proj|test)-[A-Za-z0-9_-]+")),
    ("password", re.compile(br"password", flags=re.IGNORECASE)),
    ("email", re.compile(br"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
]


def sanitize_release_text(text: str) -> tuple[str, list[dict[str, str]]]:
    redacted = text
    matches: list[dict[str, str]] = []
    for rule_name, pattern in SANITIZED_ASSIGNMENT_RULES:
        placeholder = SANITIZED_PLACEHOLDERS[rule_name]
        hit = False

        def replace_assignment(match: re.Match[str]) -> str:
            nonlocal hit
            hit = True
            return f"{match.group(1)}{placeholder}"

        updated = pattern.sub(replace_assignment, redacted)
        if hit:
            matches.append({"rule": rule_name, "placeholder": placeholder})
            redacted = updated
    for rule_name, pattern in SANITIZED_INLINE_RULES:
        placeholder = SANITIZED_PLACEHOLDERS[rule_name]
        updated, count = pattern.subn(placeholder, redacted)
        if count:
            matches.append({"rule": rule_name, "placeholder": placeholder})
            redacted = updated
    return redacted, matches


def detect_binary_sensitive_matches(data: bytes) -> list[str]:
    hits: list[str] = []
    for rule_name, pattern in SANITIZED_BINARY_PATTERNS:
        if pattern.search(data):
            hits.append(rule_name)
    return sorted(set(hits))


def file_manifest(release_dir: Path, *, exclude: set[str] | None = None) -> list[dict[str, str]]:
    excluded = exclude or set()
    manifest: list[dict[str, str]] = []
    for path in sorted(release_dir.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(release_dir).as_posix()
        if relative in excluded:
            continue
        manifest.append({"path": relative, "sha256": sha256_file(path)})
    return manifest


def normalize_branch_list_line(line: str) -> str:
    return line.strip().lstrip("*+ ").strip()


def infer_repo_root(release_dir: Path) -> Path | None:
    if release_dir.parent.name != "dist":
        return None
    root = release_dir.parent.parent
    if not root.exists():
        return None
    result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return None
    try:
        repo_root = Path(result.stdout.strip()).resolve()
    except Exception:
        return None
    return repo_root if repo_root == root.resolve() else None


def verify_repo_release_state(repo_root: Path) -> list[str]:
    errors: list[str] = []
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=repo_root, text=True, capture_output=True, check=False)
    branches = subprocess.run(["git", "branch", "--list"], cwd=repo_root, text=True, capture_output=True, check=False)
    status = subprocess.run(["git", "status", "--short"], cwd=repo_root, text=True, capture_output=True, check=False)
    if any(item.returncode != 0 for item in [branch, branches, status]):
        return ["unable to inspect repository git state for strong release install validation"]
    current_branch = branch.stdout.strip()
    local_branches = sorted(normalize_branch_list_line(line) for line in branches.stdout.splitlines() if line.strip())
    status_lines = [line for line in status.stdout.splitlines() if line.strip()]
    if current_branch != "master":
        errors.append("strong install validation requires current branch master")
    if local_branches != ["master", "release"]:
        errors.append("strong install validation requires only local branches master and release")
    if status_lines:
        errors.append("strong install validation requires a clean committed worktree")
    return errors


def validate_release_dir(release_dir: Path) -> dict[str, Any]:
    skill_name, version = parse_release_dir(release_dir)
    receipt_path, receipt = read_receipt(release_dir)
    errors: list[str] = []
    if str(receipt.get("skill_name", "")).strip() != skill_name:
        errors.append("release receipt skill_name does not match release directory name")
    if str(receipt.get("version", "")).strip() != version:
        errors.append("release receipt version does not match release directory version")
    expected_files = file_manifest(release_dir, exclude={receipt_path.name})
    actual_files = receipt.get("files")
    if not isinstance(actual_files, list):
        errors.append("release receipt files list is missing")
    else:
        normalized = []
        for item in actual_files:
            if not isinstance(item, dict):
                errors.append("release receipt files list contains invalid entries")
                continue
            normalized.append({"path": str(item.get("path", "")).strip(), "sha256": str(item.get("sha256", "")).strip()})
        if normalized != expected_files:
            errors.append("release receipt file manifest does not match release directory contents")
    repo_root = infer_repo_root(release_dir)
    validation_level = "strong" if repo_root is not None else "reduced_assurance"
    provenance_mode = "repository-dist" if repo_root is not None else "external-copy"
    expected_validation = "strong" if repo_root is not None else "reduced_assurance"
    if str(receipt.get("validation_level", "")).strip() != expected_validation:
        errors.append("release receipt validation_level does not match the installation source")
    sanitization = receipt.get("sanitization")
    if not isinstance(sanitization, dict):
        errors.append("release receipt sanitization block is missing")
    else:
        if bool(sanitization.get("enabled")) is not True:
            errors.append("release receipt sanitization enabled flag is missing or false")
        if str(sanitization.get("scope", "")).strip() != "broad":
            errors.append("release receipt sanitization scope is missing or invalid")
        if str(sanitization.get("mode", "")).strip() != "auto-redact-dist-copy":
            errors.append("release receipt sanitization mode is missing or invalid")
        if bool(sanitization.get("receipt_required")) is not True:
            errors.append("release receipt sanitization receipt_required flag is missing or false")
        files = sanitization.get("files")
        if not isinstance(files, list):
            errors.append("release receipt sanitization files list is missing")
        else:
            declared: dict[str, dict[str, Any]] = {}
            for item in files:
                if not isinstance(item, dict):
                    errors.append("release receipt sanitization files list contains invalid entries")
                    continue
                rel_path = str(item.get("path", "")).strip()
                if not rel_path:
                    errors.append("release receipt sanitization file entry is missing path")
                    continue
                rules = item.get("rules")
                if not isinstance(rules, list) or not all(str(value).strip() for value in rules):
                    errors.append(f"release receipt sanitization rules are missing for {rel_path}")
                placeholders = item.get("placeholders")
                if not isinstance(placeholders, list) or not all(str(value).strip() for value in placeholders):
                    errors.append(f"release receipt sanitization placeholders are missing for {rel_path}")
                declared[rel_path] = item
            expected_declared: set[str] = set()
            for path in sorted(release_dir.rglob("*")):
                if not path.is_file() or path.name == receipt_path.name:
                    continue
                relative = path.relative_to(release_dir).as_posix()
                data = path.read_bytes()
                if is_probably_text_bytes(data):
                    text = data.decode("utf-8")
                    sanitized_text, matches = sanitize_release_text(text)
                    if matches:
                        expected_declared.add(relative)
                        row = declared.get(relative)
                        if row is None:
                            errors.append(f"release receipt is missing sanitization record for {relative}")
                        elif str(row.get("sha256", "")).strip() != sha256_file(path):
                            errors.append(f"release receipt sanitization hash mismatch for {relative}")
                        if normalize_line_endings(text) != normalize_line_endings(sanitized_text):
                            errors.append(f"release directory still contains unsanitized sensitive content: {relative}")
                else:
                    hits = detect_binary_sensitive_matches(data)
                    if hits:
                        errors.append(f"release directory contains sensitive binary content: {relative}")
            unexpected = sorted(set(declared) - expected_declared)
            for relative in unexpected:
                errors.append(f"release receipt declares unexpected sanitized file: {relative}")
    if repo_root is not None:
        errors.extend(verify_repo_release_state(repo_root))
    if not (release_dir / "SKILL.md").is_file():
        errors.append("release directory is missing SKILL.md")
    return {
        "skill_name": skill_name,
        "version": version,
        "receipt_path": str(receipt_path),
        "repo_root": str(repo_root) if repo_root else "",
        "validation_level": validation_level,
        "provenance_mode": provenance_mode,
        "errors": errors,
    }


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
    parser.add_argument("release_dir")
    parser.add_argument("--target", choices=["skip", "codex", "custom"], default="skip")
    parser.add_argument("--codex-home", default=None)
    parser.add_argument("--custom-root", default=None)
    parser.add_argument("--write", action="store_true", help="Actually copy the skill. Default is dry-run.")
    parser.add_argument("--replace", action="store_true", help="Replace an existing installed skill after user confirmation.")
    args = parser.parse_args()

    release_dir = resolve_project(args.release_dir)
    validation = validate_release_dir(release_dir)
    if validation["errors"]:
        emit_json({"errors": validation["errors"]})
        raise SystemExit(1)
    skill_name = validation["skill_name"]
    destination = target_path(skill_name, args.target, args.codex_home, args.custom_root)
    result: dict[str, Any] = {
        "release_dir": str(release_dir),
        "skill_name": skill_name,
        "version": validation["version"],
        "target": args.target,
        "destination": str(destination) if destination else "",
        "installed": False,
        "skipped": args.target == "skip" or not args.write,
        "backup_path": "",
        "template_preserved": [],
        "template_conflicts": [],
        "receipt_path": validation["receipt_path"],
        "provenance_mode": validation["provenance_mode"],
        "validation_level": validation["validation_level"],
        "global_codex_agents_status": global_codex_agents_status(args.codex_home),
        "confirmation_question": "发布包验证完成。是否安装这个技能？请选择是或否；默认是否，跳过安装。",
        "options": install_options(),
    }
    if args.target == "skip" or not args.write:
        emit_json(result)
        return
    assert destination is not None
    try:
        install_details = copy_skill(release_dir, destination, args.replace)
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
