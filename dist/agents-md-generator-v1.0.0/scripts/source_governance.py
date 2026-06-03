from __future__ import annotations

import ast
import fnmatch
import io
import os
import tokenize
from pathlib import Path
from typing import Any

from source_governance_config import load_global_rule_overrides, load_skill_source_governance, read_json


COMMENT_CHECK_EXTENSIONS = {".py", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh"}


def relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def effective_source_governance(project: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    overrides = load_global_rule_overrides(project, profile)
    raw = read_json(overrides["path"]) if overrides["path"].is_file() else {}
    if isinstance(raw, dict) and isinstance(raw.get("source_governance"), dict):
        return {
            "config_path": overrides["path"],
            "config_source": "project-local",
            "config": overrides["data"].get("source_governance", {}),
            "errors": [item for item in overrides["errors"] if item.startswith("source_governance")],
        }
    skill = load_skill_source_governance()
    return {
        "config_path": skill["path"],
        "config_source": "skill-local",
        "config": skill["data"],
        "errors": list(skill["errors"]),
    }


def iter_candidate_files(root: Path, config: dict[str, Any]) -> list[Path]:
    excluded_roots = {str(item).strip("/\\") for item in config.get("excluded_roots", [])}
    files: list[Path] = []
    for current_root, dir_names, file_names in os.walk(root):
        current_path = Path(current_root)
        try:
            relative_parts = current_path.relative_to(root).parts
        except ValueError:
            relative_parts = ()
        dir_names[:] = [name for name in dir_names if not relative_parts[:1] or name not in excluded_roots]
        if relative_parts and relative_parts[0] in excluded_roots:
            continue
        for file_name in file_names:
            path = current_path / file_name
            files.append(path)
    return sorted(files)


def line_count(path: Path) -> int:
    return path.read_text(encoding="utf-8", errors="ignore").count("\n") + 1


def decomposition_plan_path(project_root: Path, relative_file: str) -> Path:
    overrides = load_global_rule_overrides(project_root)["data"]
    source_limits = overrides.get("source_file_limits", {}) if isinstance(overrides.get("source_file_limits", {}), dict) else {}
    plan_root = str(source_limits.get("decomposition_plan_root", "docs/development/decomposition-plans")).strip().strip("/\\")
    sanitized = relative_file.replace("\\", "/").replace(":", "")
    return project_root / plan_root / f"{sanitized}.md"


def has_valid_decomposition_plan(project_root: Path, relative_file: str) -> bool:
    plan_path = decomposition_plan_path(project_root, relative_file)
    if not plan_path.is_file():
        return False
    text = plan_path.read_text(encoding="utf-8", errors="ignore")
    overrides = load_global_rule_overrides(project_root)["data"]
    source_limits = overrides.get("source_file_limits", {}) if isinstance(overrides.get("source_file_limits", {}), dict) else {}
    required_sections = source_limits.get("required_plan_sections", [])
    return all(f"## {section}" in text for section in required_sections)


def oversized_source_files(
    root: Path,
    config: dict[str, Any],
    *,
    prefix: str = "",
    project_root: Path | None = None,
    source_relative_prefix: str = "",
) -> list[dict[str, Any]]:
    max_lines = int(config.get("max_lines", 0))
    extensions = {str(item).lower() for item in config.get("hard_fail_extensions", [])}
    violations: list[dict[str, Any]] = []
    for path in iter_candidate_files(root, config):
        if path.suffix.lower() not in extensions:
            continue
        count = line_count(path)
        if count <= max_lines:
            continue
        rel_path = relative_path(path, root)
        plan_rel_path = f"{source_relative_prefix.rstrip('/')}/{rel_path}" if source_relative_prefix else rel_path
        if project_root is not None and has_valid_decomposition_plan(project_root, plan_rel_path):
            continue
        if prefix:
            rel_path = f"{prefix}/{rel_path}"
        violations.append({"path": rel_path, "line_count": count, "max_lines": max_lines})
    return violations


def path_matches_test_only(rel_path: str, config: dict[str, Any]) -> str:
    patterns = config.get("test_only_patterns", {}) if isinstance(config.get("test_only_patterns", {}), dict) else {}
    for pattern in patterns.get("path_globs", []):
        normalized = str(pattern).replace("\\", "/")
        if fnmatch.fnmatch(rel_path, normalized):
            return normalized
    return ""


def test_code_boundary_violations(root: Path, config: dict[str, Any], *, prefix: str = "") -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for path in iter_candidate_files(root, config):
        rel_path = relative_path(path, root)
        matched = path_matches_test_only(rel_path, config)
        if not matched:
            continue
        full_path = f"{prefix}/{rel_path}" if prefix else rel_path
        violations.append({"path": full_path, "pattern": matched})
    return violations


def extract_python_comment_violations(path: Path, config: dict[str, Any]) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    gate = config.get("comment_policy_gate", {})
    python_gate = gate.get("python", {}) if isinstance(gate.get("python", {}), dict) else {}
    ai_markers = [str(item).lower() for item in gate.get("forbid_ai_comment_markers", [])]
    violations: list[str] = []
    if python_gate.get("require_public_api_docstring", False):
        try:
            tree = ast.parse(text or "\n")
        except SyntaxError as exc:
            line_no = getattr(exc, "lineno", 0) or 0
            violations.append(f"python syntax error prevents comment policy parsing (line {line_no})")
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
                    if ast.get_docstring(node, clean=False) is None:
                        violations.append(f"public API `{node.name}` is missing a docstring (line {node.lineno})")
    if python_gate.get("forbid_trailing_comment", False) or ai_markers:
        try:
            for token in tokenize.generate_tokens(io.StringIO(text).readline):
                if token.type != tokenize.COMMENT:
                    continue
                line_text = text.splitlines()[token.start[0] - 1] if text.splitlines() else ""
                if python_gate.get("forbid_trailing_comment", False) and line_text[: token.start[1]].strip():
                    violations.append(f"trailing Python comment is not allowed (line {token.start[0]})")
                if ai_markers and any(marker in token.string.lower() for marker in ai_markers):
                    violations.append(f"AI-generated comment marker is not allowed (line {token.start[0]})")
        except tokenize.TokenError as exc:
            line_no = exc.args[1][0] if len(exc.args) > 1 and isinstance(exc.args[1], tuple) and exc.args[1] else 0
            violations.append(f"python tokenize error prevents comment policy parsing (line {line_no})")
    return violations


def extract_c_cpp_comment_violations(path: Path, config: dict[str, Any]) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    gate = config.get("comment_policy_gate", {})
    c_cpp_gate = gate.get("c_cpp", {}) if isinstance(gate.get("c_cpp", {}), dict) else {}
    ai_markers = [str(item).lower() for item in gate.get("forbid_ai_comment_markers", [])]
    violations: list[str] = []
    if not c_cpp_gate.get("forbid_trailing_comment", False) and not ai_markers:
        return violations
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        comment_index = line.find("//")
        block_index = line.find("/*")
        indexes = [index for index in [comment_index, block_index] if index >= 0]
        if not indexes:
            continue
        index = min(indexes)
        if c_cpp_gate.get("forbid_trailing_comment", False) and line[:index].strip() and not stripped.startswith("#define"):
            violations.append(f"trailing C/C++ comment is not allowed (line {line_no})")
        if ai_markers and any(marker in line[index:].lower() for marker in ai_markers):
            violations.append(f"AI-generated comment marker is not allowed (line {line_no})")
    return violations


def comment_policy_violations(root: Path, config: dict[str, Any], *, prefix: str = "") -> list[dict[str, str]]:
    gate = config.get("comment_policy_gate", {})
    if not isinstance(gate, dict) or gate.get("enabled") is not True:
        return []
    violations: list[dict[str, str]] = []
    for path in iter_candidate_files(root, config):
        if path.suffix.lower() not in COMMENT_CHECK_EXTENSIONS:
            continue
        messages: list[str] = []
        if path.suffix.lower() == ".py":
            messages.extend(extract_python_comment_violations(path, config))
        else:
            messages.extend(extract_c_cpp_comment_violations(path, config))
        rel_path = relative_path(path, root)
        if prefix:
            rel_path = f"{prefix}/{rel_path}"
        for message in messages:
            violations.append({"path": rel_path, "message": message})
    return violations


def source_governance_report(project: Path, profile: dict[str, Any] | None = None) -> dict[str, Any]:
    effective = effective_source_governance(project, profile)
    config = effective["config"]
    oversized = oversized_source_files(project, config, project_root=project)
    boundary = test_code_boundary_violations(project, config)
    comments = comment_policy_violations(project, config)
    errors = list(effective["errors"])
    return {
        "project": str(project),
        "config_path": str(effective["config_path"]),
        "config_source": effective["config_source"],
        "config_errors": list(effective["errors"]),
        "oversized_source_files": oversized,
        "test_code_boundary_violations": boundary,
        "comment_policy_violations": comments,
        "errors": errors,
        "ok": not (errors or oversized or boundary or comments),
    }


def release_source_governance_report(
    project: Path,
    release_dir: Path,
    profile: dict[str, Any] | None = None,
    *,
    source_relative_prefix: str = "",
) -> dict[str, Any]:
    effective = effective_source_governance(project, profile)
    config = dict(effective["config"])
    config["excluded_roots"] = []
    prefix = release_dir.relative_to(project).as_posix() if release_dir.is_relative_to(project) else release_dir.name
    oversized = oversized_source_files(
        release_dir,
        config,
        prefix=prefix,
        project_root=project,
        source_relative_prefix=source_relative_prefix,
    )
    boundary = test_code_boundary_violations(release_dir, config, prefix=prefix)
    comments = comment_policy_violations(release_dir, config, prefix=prefix)
    return {
        "project": str(project),
        "release_dir": str(release_dir),
        "config_path": str(effective["config_path"]),
        "config_source": effective["config_source"],
        "config_errors": list(effective["errors"]),
        "oversized_source_files": oversized,
        "test_code_boundary_violations": boundary,
        "comment_policy_violations": comments,
        "errors": list(effective["errors"]),
        "ok": not (effective["errors"] or oversized or boundary or comments),
    }


def format_source_governance_errors(report: dict[str, Any], *, prefix: str = "source governance") -> list[str]:
    errors = [f"{prefix}: {item}" for item in report.get("errors", [])]
    for item in report.get("oversized_source_files", []):
        errors.append(
            f"{prefix}: oversized file `{item['path']}` has {item['line_count']} lines (limit {item['max_lines']})"
        )
    for item in report.get("test_code_boundary_violations", []):
        errors.append(f"{prefix}: test-only design code outside tests `{item['path']}` matched `{item['pattern']}`")
    for item in report.get("comment_policy_violations", []):
        errors.append(f"{prefix}: `{item['path']}` {item['message']}")
    return errors
