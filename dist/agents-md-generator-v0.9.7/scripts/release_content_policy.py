from __future__ import annotations

from pathlib import Path
from typing import Any

POLICY_VERSION = "2026-05-26-v2"
TOP_LEVEL_FILE_MODE = "allow-nonforbidden-files"

ALLOWED_TOP_LEVEL_FILES = {
    "README.md",
    "SKILL.md",
    "VERSION",
}

IGNORED_TOP_LEVEL_FILES = {
    "RELEASE_RECEIPT.json",
}

ALLOWED_TOP_LEVEL_DIRS = {
    "agents",
    "assets",
    "config",
    "evals",
    "integration",
    "references",
    "runtime",
    "scripts",
}

FORBIDDEN_EXACT_NAMES = {
    "tests",
    "test",
    "reports",
    "runs",
    "_smoke_runs",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

FORBIDDEN_PREFIXES = ("smoke",)
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}


def is_forbidden_component(name: str) -> bool:
    lowered = name.strip().lower()
    if not lowered:
        return False
    if lowered in FORBIDDEN_EXACT_NAMES:
        return True
    return any(lowered.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)


def is_forbidden_relative_path(relative_path: str) -> bool:
    normalized = relative_path.replace("\\", "/").strip().strip("/")
    if not normalized:
        return False
    parts = [part for part in normalized.split("/") if part]
    if any(is_forbidden_component(part) for part in parts):
        return True
    suffix = Path(parts[-1]).suffix.lower() if parts else ""
    return suffix in FORBIDDEN_SUFFIXES


def analyze_release_content_root(root: Path, *, allow_source_only_repo_local: bool = False) -> dict[str, Any]:
    included_files: list[str] = []
    forbidden_paths: list[str] = []
    unexpected_top_level_entries: set[str] = set()
    source_only_prefixes: set[str] = set()

    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        parts = Path(relative).parts
        if not parts:
            continue
        top_level = parts[0]
        if top_level in source_only_prefixes:
            continue
        if is_forbidden_relative_path(relative):
            forbidden_paths.append(relative)
            continue
        if len(parts) == 1 and top_level in IGNORED_TOP_LEVEL_FILES:
            continue
        if len(parts) == 1 and path.is_dir() and top_level not in ALLOWED_TOP_LEVEL_DIRS:
            unexpected_top_level_entries.add(top_level)
            continue
        if len(parts) > 1 and top_level not in ALLOWED_TOP_LEVEL_DIRS:
            unexpected_top_level_entries.add(top_level)
            continue
        if path.is_file():
            included_files.append(relative)

    included_top_level_entries = sorted({Path(relative).parts[0] for relative in included_files})
    return {
        "policy_version": POLICY_VERSION,
        "top_level_file_mode": TOP_LEVEL_FILE_MODE,
        "allowed_top_level_files": sorted(ALLOWED_TOP_LEVEL_FILES),
        "allowed_top_level_dirs": sorted(ALLOWED_TOP_LEVEL_DIRS),
        "forbidden_exact_names": sorted(FORBIDDEN_EXACT_NAMES),
        "forbidden_prefixes": sorted(FORBIDDEN_PREFIXES),
        "forbidden_suffixes": sorted(FORBIDDEN_SUFFIXES),
        "source_only_prefixes": sorted(source_only_prefixes),
        "included_files": sorted(included_files),
        "included_file_count": len(included_files),
        "included_top_level_entries": included_top_level_entries,
        "unexpected_top_level_entries": sorted(unexpected_top_level_entries),
        "forbidden_paths": sorted(forbidden_paths),
    }


def release_content_policy_receipt(analysis: dict[str, Any], *, forbidden_source_paths: list[str] | None = None) -> dict[str, Any]:
    return {
        "policy_version": analysis["policy_version"],
        "top_level_file_mode": analysis["top_level_file_mode"],
        "allowed_top_level_files": list(analysis["allowed_top_level_files"]),
        "allowed_top_level_dirs": list(analysis["allowed_top_level_dirs"]),
        "forbidden_exact_names": list(analysis["forbidden_exact_names"]),
        "forbidden_prefixes": list(analysis["forbidden_prefixes"]),
        "forbidden_suffixes": list(analysis["forbidden_suffixes"]),
        "included_file_count": analysis["included_file_count"],
        "included_top_level_entries": list(analysis["included_top_level_entries"]),
        "unexpected_top_level_entries": list(analysis["unexpected_top_level_entries"]),
        "forbidden_source_paths": sorted(forbidden_source_paths or []),
        "forbidden_release_paths": list(analysis["forbidden_paths"]),
    }


def validate_recorded_release_content_policy(
    recorded: Any,
    release_analysis: dict[str, Any],
    *,
    forbidden_source_paths: list[str] | None = None,
    require_source_paths: bool = True,
) -> list[str]:
    if not isinstance(recorded, dict):
        return ["release content policy block is missing"]
    expected = release_content_policy_receipt(
        release_analysis,
        forbidden_source_paths=forbidden_source_paths if require_source_paths else None,
    )
    errors: list[str] = []
    for key in (
        "policy_version",
        "top_level_file_mode",
        "allowed_top_level_files",
        "allowed_top_level_dirs",
        "forbidden_exact_names",
        "forbidden_prefixes",
        "forbidden_suffixes",
        "included_file_count",
        "included_top_level_entries",
        "unexpected_top_level_entries",
        "forbidden_release_paths",
    ):
        if recorded.get(key) != expected[key]:
            errors.append(f"release content policy field mismatch: {key}")
    if require_source_paths and recorded.get("forbidden_source_paths") != expected["forbidden_source_paths"]:
        errors.append("release content policy field mismatch: forbidden_source_paths")
    elif not require_source_paths and not isinstance(recorded.get("forbidden_source_paths"), list):
        errors.append("release content policy forbidden_source_paths must be a list")
    return errors
