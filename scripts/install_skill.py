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
from agents_decisions import decision_request
from release_content_policy import (
    POLICY_VERSION,
    analyze_release_content_root,
    validate_recorded_release_content_policy,
)

ACTIVE_SESSION_PATH = ".agents/active-session.json"


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


EVOLUTION_MERGE_SECTIONS = [
    "Evidence Sources",
    "Applicable Scenario",
    "Distilled Workflow",
    "Key Decisions",
    "Common Problems",
    "Non-Reusable Content",
    "Application Checklist",
]


SANITIZED_PLACEHOLDERS = {
    "api_key": "<REDACTED_API_KEY>",
    "password": "<REDACTED_PASSWORD>",
    "email": "<REDACTED_EMAIL>",
    "local_path": "<REDACTED_LOCAL_PATH>",
}
SANITIZED_ASSIGNMENT_RULES = [
    (
        "api_key",
        re.compile(r"(?m)^(\s*(?:[A-Z0-9]+_)*(?:API[_-]?KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET)(?:_[A-Z0-9]+)*\s*[:=]\s*)(.+?)\s*$"),
    ),
    (
        "password",
        re.compile(r"(?m)^(\s*[A-Z0-9_]*PASSWORD[A-Z0-9_]*\s*[:=]\s*)(.+?)\s*$"),
    ),
]
SANITIZED_INLINE_RULES = [
    ("email", re.compile(r"(?<!\\)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", flags=re.IGNORECASE)),
    ("local_path", re.compile(r"\b[A-Za-z]:[/\\][^\s`'\"<>)]*")),
    ("local_path", re.compile(r"[A-Za-z]:\\Users\\[^\r\n]+")),
    ("local_path", re.compile(r"/(?:Users|home)/[^\s]+")),
]
SANITIZED_BINARY_PATTERNS = [
    ("api_key", re.compile(br"sk-(?:live|proj|test)-[A-Za-z0-9_-]+")),
    ("password", re.compile(br"password", flags=re.IGNORECASE)),
    ("email", re.compile(br"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
]
RELEASE_REQUIRED_REFERENCE_PREFIXES = ("runtime/", "integration/", "config/", "scripts/", "references/", "agents/", "assets/")


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


def sanitize_evolution_value(value: Any) -> Any:
    if isinstance(value, str):
        sanitized, _ = sanitize_release_text(value)
        return normalize_line_endings(sanitized)
    if isinstance(value, list):
        return [sanitize_evolution_value(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_evolution_value(item) for key, item in value.items()}
    return value


def sanitize_protected_evolution_text(path: Path, text: str) -> str:
    if path.suffix == ".json":
        try:
            data = json.loads(text)
        except Exception:
            sanitized, _ = sanitize_release_text(text)
            normalized = normalize_line_endings(sanitized)
            return normalized if normalized.endswith("\n") else normalized + "\n"
        sanitized_data = sanitize_evolution_value(data)
        return json.dumps(sanitized_data, indent=2, sort_keys=True) + "\n"
    sanitized, _ = sanitize_release_text(text)
    normalized = normalize_line_endings(sanitized)
    return normalized if normalized.endswith("\n") else normalized + "\n"


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


def referenced_release_paths(skill_text: str) -> set[str]:
    paths: set[str] = set()
    for raw in re.findall(r"`([^`]+)`", skill_text):
        value = raw.strip()
        if "<" in value or ">" in value:
            continue
        if not value.startswith(RELEASE_REQUIRED_REFERENCE_PREFIXES):
            continue
        paths.add(value.rstrip("/"))
    return paths


def validate_release_completeness(release_dir: Path, receipt: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    skill_path = release_dir / "SKILL.md"
    if not skill_path.is_file():
        return ["release directory is missing SKILL.md"]

    actual_manifest = {
        item["path"]
        for item in file_manifest(release_dir, exclude={"RELEASE_RECEIPT.json"})
        if isinstance(item, dict) and str(item.get("path", "")).strip()
    }
    skill_text = skill_path.read_text(encoding="utf-8", errors="ignore")
    for reference in sorted(referenced_release_paths(skill_text)):
        if reference in actual_manifest:
            continue
        if (release_dir / reference).exists():
            continue
        if any(path.startswith(reference + "/") for path in actual_manifest):
            continue
        errors.append(f"release directory is missing SKILL.md referenced path: {reference}")

    recorded_files = receipt.get("files")
    if isinstance(recorded_files, list):
        recorded_manifest = {str(item.get("path", "")).strip() for item in recorded_files if isinstance(item, dict)}
        for required_name in ("SKILL.md",):
            if required_name not in recorded_manifest:
                errors.append(f"release receipt is missing required file entry: {required_name}")
    return errors


def normalize_branch_list_line(line: str) -> str:
    return line.strip().lstrip("*+ ").strip()


def parse_status_paths(line: str) -> list[str]:
    body = line[3:].strip() if len(line) >= 4 else line.strip()
    if " -> " in body:
        old_path, new_path = body.split(" -> ", 1)
        return [old_path.strip().replace("\\", "/"), new_path.strip().replace("\\", "/")]
    return [body.replace("\\", "/")]


def filter_runtime_status_lines(lines: list[str]) -> list[str]:
    ignored = {ACTIVE_SESSION_PATH.replace("\\", "/")}
    filtered: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        paths = [path for path in parse_status_paths(line) if path and path not in ignored]
        if paths:
            filtered.append(line)
    return filtered


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


def source_skill_dir_from_receipt(repo_root: Path, receipt: dict[str, Any]) -> Path | None:
    source_path = str(receipt.get("source_path", "")).strip()
    if not source_path:
        return None
    candidate = (repo_root / source_path).resolve()
    if not candidate.exists():
        return None
    try:
        candidate.relative_to(repo_root.resolve())
    except ValueError:
        return None
    return candidate


def verify_repo_release_state(repo_root: Path) -> list[str]:
    errors: list[str] = []
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=repo_root, text=True, capture_output=True, check=False)
    branches = subprocess.run(["git", "branch", "--list"], cwd=repo_root, text=True, capture_output=True, check=False)
    status = subprocess.run(["git", "status", "--short"], cwd=repo_root, text=True, capture_output=True, check=False)
    if any(item.returncode != 0 for item in [branch, branches, status]):
        return ["unable to inspect repository git state for strong release install validation"]
    current_branch = branch.stdout.strip()
    local_branches = sorted(normalize_branch_list_line(line) for line in branches.stdout.splitlines() if line.strip())
    status_lines = filter_runtime_status_lines(status.stdout.splitlines())
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
    release_content = analyze_release_content_root(release_dir)
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
            source_skill_dir = source_skill_dir_from_receipt(repo_root, receipt) if repo_root is not None else None
            if source_skill_dir is not None:
                for source_path in sorted(source_skill_dir.rglob("*")):
                    if not source_path.is_file():
                        continue
                    relative = source_path.relative_to(source_skill_dir).as_posix()
                    if relative == receipt_path.name:
                        continue
                    release_path = release_dir / relative
                    if not release_path.is_file():
                        continue
                    source_bytes = source_path.read_bytes()
                    release_bytes = release_path.read_bytes()
                    if is_probably_text_bytes(source_bytes):
                        source_text = source_bytes.decode("utf-8")
                        expected_text, matches = sanitize_release_text(source_text)
                        if matches:
                            expected_declared.add(relative)
                            row = declared.get(relative)
                            if row is None:
                                errors.append(f"release receipt is missing sanitization record for {relative}")
                            elif str(row.get("sha256", "")).strip() != sha256_file(release_path):
                                errors.append(f"release receipt sanitization hash mismatch for {relative}")
                            if not is_probably_text_bytes(release_bytes):
                                errors.append(f"sanitized release file is not valid UTF-8 text: {relative}")
                                continue
                            actual_text = release_bytes.decode("utf-8")
                            if normalize_line_endings(actual_text) != normalize_line_endings(expected_text):
                                errors.append(f"sanitized release content mismatch for {relative}")
                        elif release_bytes != source_bytes:
                            errors.append(f"undeclared release diff outside sanitization receipt: {relative}")
                    else:
                        hits = detect_binary_sensitive_matches(source_bytes)
                        if hits:
                            errors.append(f"binary file contains sensitive content and cannot be sanitized safely: {relative}")
                        elif release_bytes != source_bytes:
                            errors.append(f"undeclared binary release diff outside sanitization receipt: {relative}")
                unexpected = sorted(set(declared) - expected_declared)
                for relative in unexpected:
                    errors.append(f"release receipt declares unexpected sanitized file: {relative}")
            else:
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
                for relative, row in declared.items():
                    release_path = release_dir / relative
                    if not release_path.is_file():
                        errors.append(f"release receipt sanitization file entry points to a missing file: {relative}")
                        continue
                    if str(row.get("sha256", "")).strip() != sha256_file(release_path):
                        errors.append(f"release receipt sanitization hash mismatch for {relative}")
    if repo_root is not None:
        errors.extend(verify_repo_release_state(repo_root))
    source_skill_dir = source_skill_dir_from_receipt(repo_root, receipt) if repo_root is not None else None
    source_forbidden_paths: list[str] = []
    if source_skill_dir is not None:
        source_forbidden_paths = analyze_release_content_root(
            source_skill_dir,
            allow_source_only_repo_local=True,
        )["forbidden_paths"]
    policy_errors = validate_recorded_release_content_policy(
        receipt.get("release_content_policy"),
        release_content,
        forbidden_source_paths=source_forbidden_paths,
        require_source_paths=source_skill_dir is not None,
    )
    if release_content["unexpected_top_level_entries"]:
        policy_errors.append("release content policy rejected unexpected top-level release entries")
    if release_content["forbidden_paths"]:
        policy_errors.append("release content policy rejected forbidden development content in release")
    errors.extend(policy_errors)
    errors.extend(validate_release_completeness(release_dir, receipt))
    return {
        "skill_name": skill_name,
        "version": version,
        "receipt_path": str(receipt_path),
        "repo_root": str(repo_root) if repo_root else "",
        "validation_level": validation_level,
        "provenance_mode": provenance_mode,
        "policy_version": POLICY_VERSION,
        "forbidden_source_paths": source_forbidden_paths,
        "forbidden_release_paths": release_content["forbidden_paths"],
        "release_content_policy_ok": not policy_errors,
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


def split_markdown_sections(text: str) -> tuple[list[str], dict[str, str]]:
    normalized = normalize_line_endings(text)
    lines = normalized.splitlines()
    preamble: list[str] = []
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        if current is None:
            preamble.append(line)
        else:
            sections[current].append(line)
    return preamble, {name: "\n".join(content).strip() for name, content in sections.items()}


def merge_markdown_blocks(old_body: str, new_body: str) -> str:
    blocks: list[str] = []
    seen: set[str] = set()
    for body in (old_body, new_body):
        for block in [item.strip() for item in re.split(r"\n\s*\n", body.strip()) if item.strip()]:
            key = "\n".join(line.strip() for line in block.splitlines()).strip()
            if key and key not in seen:
                seen.add(key)
                blocks.append(block)
    return "\n\n".join(blocks).strip()


def merge_evolution_markdown(old_text: str, new_text: str) -> str | None:
    new_preamble, new_sections = split_markdown_sections(new_text)
    _old_preamble, old_sections = split_markdown_sections(old_text)
    if not all(section in new_sections for section in EVOLUTION_MERGE_SECTIONS):
        return None
    if not all(section in old_sections for section in EVOLUTION_MERGE_SECTIONS):
        return None
    rendered: list[str] = [line for line in new_preamble]
    while rendered and not rendered[-1].strip():
        rendered.pop()
    if rendered:
        rendered.append("")
    for section in EVOLUTION_MERGE_SECTIONS:
        rendered.append(f"## {section}")
        rendered.append(merge_markdown_blocks(old_sections.get(section, ""), new_sections.get(section, "")))
        rendered.append("")
    return "\n".join(rendered).rstrip() + "\n"


def merge_index_json(old_text: str, new_text: str) -> str | None:
    try:
        old_data = json.loads(old_text)
        new_data = json.loads(new_text)
    except Exception:
        return None
    if not isinstance(old_data, dict) or not isinstance(new_data, dict):
        return None
    old_data = sanitize_evolution_value(old_data)
    new_data = sanitize_evolution_value(new_data)
    merged = dict(new_data)
    old_templates = old_data.get("templates", [])
    new_templates = new_data.get("templates", [])
    if isinstance(old_templates, list) and isinstance(new_templates, list):
        rows: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for row in [item for item in old_templates if isinstance(item, dict)] + [item for item in new_templates if isinstance(item, dict)]:
            key = (str(row.get("output", "")).strip(), str(row.get("topic", "")).strip())
            if key not in seen:
                seen.add(key)
                rows.append(row)
        merged["templates"] = rows
    merged["merged_at"] = datetime.now().isoformat(timespec="seconds")
    merged["merge_mode"] = "sectional-preserve-installed"
    return json.dumps(merged, indent=2, sort_keys=True) + "\n"


def merge_protected_evolution_file(old_path: Path, target: Path) -> tuple[str, str | None]:
    old_text = sanitize_protected_evolution_text(old_path, old_path.read_text(encoding="utf-8", errors="ignore"))
    new_text = sanitize_protected_evolution_text(target, target.read_text(encoding="utf-8", errors="ignore"))
    if old_path.name.endswith(".json"):
        merged = merge_index_json(old_text, new_text)
        return ("index", merged)
    merged = merge_evolution_markdown(old_text, new_text)
    return ("markdown", merged)


def conflict_copy_path(target: Path) -> Path:
    candidate = target.with_name(f"{target.stem}.installed-template-conflict{target.suffix}")
    index = 2
    while candidate.exists():
        candidate = target.with_name(f"{target.stem}.installed-template-conflict-{index}{target.suffix}")
        index += 1
    return candidate


def preserve_evolution_templates(backup: Path, destination: Path) -> tuple[list[str], list[dict[str, str]], list[str], list[dict[str, str]], list[str]]:
    preserved: list[str] = []
    conflicts: list[dict[str, str]] = []
    merged: list[str] = []
    fallback_conflicts: list[dict[str, str]] = []
    merged_index_updates: list[str] = []
    for old_path in protected_evolution_files(backup):
        relative = old_path.relative_to(backup)
        target = destination / relative
        sanitized_old_text = sanitize_protected_evolution_text(old_path, old_path.read_text(encoding="utf-8", errors="ignore"))
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(sanitized_old_text, encoding="utf-8")
            preserved.append(relative.as_posix())
            continue
        if target.read_bytes() == old_path.read_bytes():
            current_text = target.read_text(encoding="utf-8", errors="ignore")
            sanitized_current_text = sanitize_protected_evolution_text(target, current_text)
            if sanitized_current_text != current_text:
                target.write_text(sanitized_current_text, encoding="utf-8")
            preserved.append(relative.as_posix())
            continue
        kind, merged_text = merge_protected_evolution_file(old_path, target)
        if merged_text is not None:
            target.write_text(sanitize_protected_evolution_text(target, merged_text), encoding="utf-8")
            merged.append(relative.as_posix())
            if kind == "index":
                merged_index_updates.append(relative.as_posix())
            continue
        conflict_target = conflict_copy_path(target)
        conflict_target.write_text(sanitized_old_text, encoding="utf-8")
        conflict = {
            "relative_path": relative.as_posix(),
            "installed_version": str(conflict_target),
            "new_version": str(target),
        }
        conflicts.append(conflict)
        fallback_conflicts.append(conflict)
    return preserved, conflicts, merged, fallback_conflicts, merged_index_updates


def copy_skill(skill_dir: Path, destination: Path, replace: bool) -> dict[str, Any]:
    backup_path: Path | None = None
    preserved: list[str] = []
    conflicts: list[dict[str, str]] = []
    merged: list[str] = []
    fallback_conflicts: list[dict[str, str]] = []
    merged_index_updates: list[str] = []
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
        preserved, conflicts, merged, fallback_conflicts, merged_index_updates = preserve_evolution_templates(backup_path, destination)
    return {
        "backup_path": str(backup_path) if backup_path else "",
        "template_preserved": preserved,
        "template_conflicts": conflicts,
        "template_merged": merged,
        "merge_fallback_conflicts": fallback_conflicts,
        "merged_index_updates": merged_index_updates,
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
        emit_json(validation)
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
        "template_merged": [],
        "merge_fallback_conflicts": [],
        "merged_index_updates": [],
        "receipt_path": validation["receipt_path"],
        "provenance_mode": validation["provenance_mode"],
        "validation_level": validation["validation_level"],
        "policy_version": validation["policy_version"],
        "forbidden_source_paths": validation["forbidden_source_paths"],
        "forbidden_release_paths": validation["forbidden_release_paths"],
        "release_content_policy_ok": validation["release_content_policy_ok"],
        "global_codex_agents_status": global_codex_agents_status(args.codex_home),
        "confirmation_question": "发布包验证完成。是否安装这个技能？请选择是或否；默认是否，跳过安装。",
        "options": install_options(),
    }
    result["decision_request"] = decision_request(
        "install_confirmation",
        question=result["confirmation_question"],
        options=result["options"],
        default="skip",
        risk="medium",
        next_action="rerun install_skill.py with --write and the selected target when installation is confirmed",
        context={"release_dir": str(release_dir), "target": args.target},
    )
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
