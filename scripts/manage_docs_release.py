
from __future__ import annotations

from manage_docs_shared import *
from manage_docs_scaffold_session import write_development, write_git_changelog
from manage_docs_sync_verify import sync_root_agents
from source_governance import (
    format_source_governance_errors,
    release_source_governance_report,
    source_governance_report,
)
from agents_decisions import decision_request

INSTALLABLE_SKILL_TOP_LEVEL_EXCLUDES = {
    "AGENTS.md",
    "_smoke_runs",
    "reports",
    "workflow-state.json",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
INSTALLABLE_SKILL_NESTED_DIR_EXCLUDES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
INSTALLABLE_SKILL_SUFFIX_EXCLUDES = {".pyc", ".pyo"}


def run_git(project: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)

def git_ok(project: Path, args: list[str]) -> tuple[bool, str]:
    result = run_git(project, args)
    return result.returncode == 0, (result.stdout or result.stderr).strip()

def governed_allowed_paths(profile: dict[str, Any], skill_dir: Path, project: Path) -> list[str]:
    policy = profile.get("git_branch_policy", {}) if isinstance(profile.get("git_branch_policy"), dict) else {}
    configured = policy.get("release_prepare_allowed_paths")
    if isinstance(configured, list) and configured:
        return [str(item).replace("\\", "/").strip().strip("/") for item in configured if str(item).strip()]
    rel_skill = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else skill_dir.name
    return [rel_skill, "tests", "docs", ".agents", "AGENTS.md", "dist"]

def receipt_filename(profile: dict[str, Any]) -> str:
    release = profile.get("release_contract", {}) if isinstance(profile.get("release_contract"), dict) else {}
    value = str(release.get("receipt_file", "RELEASE_RECEIPT.json")).strip()
    return value or "RELEASE_RECEIPT.json"

def release_sanitization_settings(profile: dict[str, Any], project_kind: str) -> dict[str, Any]:
    release = profile.get("release_contract", {}) if isinstance(profile.get("release_contract"), dict) else {}
    required = bool(release.get("sanitization_required", False)) and project_kind == "skill"
    return {
        "required": required,
        "scope": str(release.get("sanitization_scope", "not-configured")).strip() or "not-configured",
        "mode": str(release.get("sanitization_mode", "not-configured")).strip() or "not-configured",
        "receipt_required": bool(release.get("sanitization_receipt_required", False)) and project_kind == "skill",
    }

def matches_governed_path(path: str, allowed: list[str]) -> bool:
    normalized = path.replace("\\", "/").strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    for prefix in allowed:
        if normalized == prefix or normalized.startswith(prefix + "/"):
            return True
    return False

def normalize_branch_list_line(line: str) -> str:
    return line.strip().lstrip("*+ ").strip()

def parse_status_paths(line: str) -> list[str]:
    body = line[3:].strip() if len(line) >= 4 else line.strip()
    if " -> " in body:
        old_path, new_path = body.split(" -> ", 1)
        return [old_path.strip().replace("\\", "/"), new_path.strip().replace("\\", "/")]
    return [body.replace("\\", "/")]

def filter_runtime_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if path and path not in IGNORED_RUNTIME_GIT_PATHS]

def filter_runtime_status_lines(lines: list[str]) -> list[str]:
    filtered: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        paths = filter_runtime_paths(parse_status_paths(line))
        if paths:
            filtered.append(line)
    return filtered

def changed_paths(project: Path) -> tuple[list[str], list[str]]:
    status = run_git(project, ["status", "--short"])
    if status.returncode != 0:
        return [], ["git status --short failed"]
    paths: list[str] = []
    for line in status.stdout.splitlines():
        if not line.strip():
            continue
        paths.extend(parse_status_paths(line))
    return sorted(set(filter_runtime_paths(paths))), []

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()

def build_release_file_manifest(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, str]]:
    excluded = exclude or set()
    manifest: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        manifest.append({"path": relative, "sha256": sha256_file(path)})
    return manifest

def write_release_zip(release_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(release_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(release_dir.parent).as_posix())

def release_target_exclusions(skill_name: str, version: str) -> set[str]:
    return {
        f"dist/{skill_name}-{version}/",
        f"dist/{skill_name}-{version}.zip",
    }

def is_excluded_dist_artifact(relative_path: str, excluded: set[str]) -> bool:
    normalized = relative_path.replace("\\", "/")
    for item in excluded:
        entry = item.replace("\\", "/")
        if entry.endswith("/"):
            if normalized.startswith(entry):
                return True
        elif normalized == entry:
            return True
    return False

def dist_artifact_snapshot(project: Path, excluded: set[str] | None = None) -> list[dict[str, str]]:
    dist_root = project / "dist"
    if not dist_root.exists():
        return []
    blocked = excluded or set()
    snapshot: list[dict[str, str]] = []
    for path in sorted(dist_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(project).as_posix()
        if is_excluded_dist_artifact(relative, blocked):
            continue
        snapshot.append({"path": relative, "sha256": sha256_file(path)})
    return snapshot

def read_release_receipt(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}

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


def should_include_release_path(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    parts = relative.parts
    if not parts:
        return True
    if parts[0] in INSTALLABLE_SKILL_TOP_LEVEL_EXCLUDES:
        return False
    if any(part in INSTALLABLE_SKILL_NESTED_DIR_EXCLUDES for part in parts):
        return False
    if path.suffix in INSTALLABLE_SKILL_SUFFIX_EXCLUDES:
        return False
    return True


def release_copy_ignore(directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    root = Path(directory)
    for name in names:
        candidate = root / name
        if candidate.name in INSTALLABLE_SKILL_NESTED_DIR_EXCLUDES:
            ignored.add(name)
            continue
        if candidate.suffix in INSTALLABLE_SKILL_SUFFIX_EXCLUDES:
            ignored.add(name)
    return ignored

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

def sanitize_release_tree(profile: dict[str, Any], project_kind: str, skill_dir: Path, release_dir: Path) -> tuple[dict[str, Any], list[str]]:
    settings = release_sanitization_settings(profile, project_kind)
    result: dict[str, Any] = {
        "enabled": settings["required"],
        "scope": settings["scope"],
        "mode": settings["mode"],
        "files": [],
    }
    if settings["receipt_required"]:
        result["receipt_required"] = True
    if not settings["required"]:
        return result, []
    errors: list[str] = []
    files: list[dict[str, Any]] = []
    for source_path in sorted(skill_dir.rglob("*")):
        if not source_path.is_file():
            continue
        rel_path = source_path.relative_to(skill_dir).as_posix()
        if rel_path == "AGENTS.md":
            continue
        release_path = release_dir / rel_path
        if not release_path.is_file():
            continue
        data = release_path.read_bytes()
        if is_probably_text_bytes(data):
            text = data.decode("utf-8")
            sanitized_text, matches = sanitize_release_text(text)
            if matches:
                release_path.write_text(normalize_line_endings(sanitized_text), encoding="utf-8")
                files.append(
                    {
                        "path": rel_path,
                        "rules": sorted({item["rule"] for item in matches}),
                        "placeholders": sorted({item["placeholder"] for item in matches}),
                        "sha256": sha256_file(release_path),
                    }
                )
        else:
            hits = detect_binary_sensitive_matches(data)
            if hits:
                errors.append(f"binary file contains sensitive content and cannot be sanitized safely: {rel_path}")
    result["files"] = files
    return result, errors

def verify_release_sanitization(
    profile: dict[str, Any],
    project_kind: str,
    skill_dir: Path,
    release_dir: Path,
    receipt: dict[str, Any],
) -> list[str]:
    settings = release_sanitization_settings(profile, project_kind)
    if not settings["required"]:
        return []
    sanitization = receipt.get("sanitization")
    errors: list[str] = []
    if not isinstance(sanitization, dict):
        return ["release receipt sanitization block is missing"]
    if bool(sanitization.get("enabled")) is not True:
        errors.append("release receipt sanitization enabled flag is missing or false")
    if str(sanitization.get("scope", "")).strip() != settings["scope"]:
        errors.append("release receipt sanitization scope does not match the release policy")
    if str(sanitization.get("mode", "")).strip() != settings["mode"]:
        errors.append("release receipt sanitization mode does not match the release policy")
    if settings["receipt_required"] and bool(sanitization.get("receipt_required")) is not True:
        errors.append("release receipt sanitization receipt_required flag is missing or false")
    files = sanitization.get("files")
    if not isinstance(files, list):
        return ["release receipt sanitization files list is missing"]
    declared: dict[str, dict[str, Any]] = {}
    for row in files:
        if not isinstance(row, dict):
            errors.append("release receipt sanitization files list contains invalid entries")
            continue
        rel_path = str(row.get("path", "")).strip()
        if not rel_path:
            errors.append("release receipt sanitization file entry is missing path")
            continue
        rules = row.get("rules")
        if not isinstance(rules, list) or not all(str(item).strip() for item in rules):
            errors.append(f"release receipt sanitization rules are missing for {rel_path}")
        placeholders = row.get("placeholders")
        if not isinstance(placeholders, list) or not all(str(item).strip() for item in placeholders):
            errors.append(f"release receipt sanitization placeholders are missing for {rel_path}")
        declared[rel_path] = row
    expected_declared: set[str] = set()
    for source_path in sorted(skill_dir.rglob("*")):
        if not source_path.is_file():
            continue
        rel_path = source_path.relative_to(skill_dir).as_posix()
        if rel_path == "AGENTS.md":
            continue
        release_path = release_dir / rel_path
        if not release_path.is_file():
            continue
        source_bytes = source_path.read_bytes()
        release_bytes = release_path.read_bytes()
        if is_probably_text_bytes(source_bytes):
            source_text = source_bytes.decode("utf-8")
            expected_text, matches = sanitize_release_text(source_text)
            if matches:
                expected_declared.add(rel_path)
                if rel_path not in declared:
                    errors.append(f"release receipt is missing sanitization record for {rel_path}")
                if not is_probably_text_bytes(release_bytes):
                    errors.append(f"sanitized release file is not valid UTF-8 text: {rel_path}")
                    continue
                actual_text = release_bytes.decode("utf-8")
                if normalize_line_endings(actual_text) != normalize_line_endings(expected_text):
                    errors.append(f"sanitized release content mismatch for {rel_path}")
                row = declared.get(rel_path)
                if isinstance(row, dict):
                    if str(row.get("sha256", "")).strip() != sha256_file(release_path):
                        errors.append(f"release receipt sanitization hash mismatch for {rel_path}")
            elif release_bytes != source_bytes:
                errors.append(f"undeclared release diff outside sanitization receipt: {rel_path}")
        else:
            hits = detect_binary_sensitive_matches(source_bytes)
            if hits:
                errors.append(f"binary file contains sensitive content and cannot be sanitized safely: {rel_path}")
            elif release_bytes != source_bytes:
                errors.append(f"undeclared binary release diff outside sanitization receipt: {rel_path}")
    unexpected = sorted(set(declared) - expected_declared)
    for rel_path in unexpected:
        errors.append(f"release receipt declares unexpected sanitized file: {rel_path}")
    return errors

def verify_release_receipt(project: Path, receipt_path: Path, release_dir: Path, skill_name: str, version: str, source_rel: str, *, require_repo_dist: bool) -> list[str]:
    receipt = read_release_receipt(receipt_path)
    errors: list[str] = []
    if not receipt:
        return [f"invalid release receipt: {display_path(receipt_path, project)}"]
    if str(receipt.get("skill_name", "")).strip() != skill_name:
        errors.append("release receipt skill_name does not match release directory")
    if str(receipt.get("version", "")).strip() != version:
        errors.append("release receipt version does not match requested release version")
    if str(receipt.get("source_path", "")).strip().replace("\\", "/") != source_rel:
        errors.append("release receipt source_path does not match skill source path")
    expected_validation = "strong" if require_repo_dist else "reduced_assurance"
    if str(receipt.get("validation_level", "")).strip() != expected_validation:
        errors.append("release receipt validation_level is inconsistent with the release source")
    expected_files = build_release_file_manifest(release_dir, exclude={receipt_path.name})
    actual_files = receipt.get("files")
    if not isinstance(actual_files, list):
        errors.append("release receipt files list is missing")
    else:
        filtered = []
        for item in actual_files:
            if not isinstance(item, dict):
                errors.append("release receipt files list contains invalid entries")
                continue
            filtered.append({"path": str(item.get("path", "")).strip(), "sha256": str(item.get("sha256", "")).strip()})
        if filtered != expected_files:
            errors.append("release receipt file manifest does not match packaged release contents")
    return errors

def current_branch_and_locals(project: Path) -> tuple[str, list[str], list[str]]:
    git_branch_result = run_git(project, ["branch", "--show-current"])
    git_list_result = run_git(project, ["branch", "--list"])
    git_status_result = run_git(project, ["status", "--short"])
    if any(result.returncode != 0 for result in [git_branch_result, git_list_result, git_status_result]):
        return "", [], []
    current_branch = git_branch_result.stdout.strip()
    local_branches = sorted(normalize_branch_list_line(line) for line in git_list_result.stdout.splitlines() if line.strip())
    status_lines = filter_runtime_status_lines(git_status_result.stdout.splitlines())
    return current_branch, local_branches, status_lines

def release_prepare(project: Path, version: str, skill_dir_raw: str) -> dict[str, Any]:
    profile = read_json(project / ".agents" / "agents-control.json")
    skill_dir = resolve_project(skill_dir_raw if Path(skill_dir_raw).is_absolute() else project / skill_dir_raw)
    current_branch, local_branches, status_lines = current_branch_and_locals(project)
    protected = sorted((profile.get("git_branch_policy", {}) or {}).get("protected_branches", ["master", "release"]))
    extras = sorted(branch for branch in local_branches if branch not in protected)
    errors: list[str] = []
    checks: dict[str, Any] = {
        "current_branch": current_branch,
        "local_branches": local_branches,
        "protected_branches": protected,
        "prepared_branch": "",
    }
    if not current_branch and not local_branches:
        errors.append("release prepare requires a readable local git repository")
        return {"ok": False, "errors": errors, "checks": checks}
    if current_branch == "master":
        if len(extras) > 1:
            errors.append(f"multiple extra local branches require manual resolution before release prepare: {extras}")
        elif len(extras) == 1:
            errors.append(f"master cannot guess which extra local branch to prepare automatically: {extras[0]}")
        else:
            return {"ok": True, "errors": [], "checks": checks}
        return {"ok": False, "errors": errors, "checks": checks}
    if current_branch in protected:
        errors.append(f"release prepare only handles temporary development branches, found protected branch {current_branch}")
        return {"ok": False, "errors": errors, "checks": checks}
    if extras != [current_branch]:
        errors.append(f"release prepare requires exactly one temporary development branch, found {extras}")
        return {"ok": False, "errors": errors, "checks": checks}
    if (project / "AGENTS.md").exists():
        sync_result = sync_root_agents(project, write=True)
        checks["root_agents_sync"] = {
            "updated": sync_result.get("updated", False),
            "reasons": sync_result.get("reasons", []),
        }
        if sync_result.get("errors"):
            errors.extend(sync_result["errors"])
            return {"ok": False, "errors": errors, "checks": checks}
    else:
        checks["root_agents_sync"] = {
            "updated": False,
            "reasons": ["missing_root_agents_md"],
            "skipped": True,
        }
    allowed = governed_allowed_paths(profile, skill_dir, project)
    changed, changed_errors = changed_paths(project)
    errors.extend(changed_errors)
    outside = [path for path in changed if not matches_governed_path(path, allowed)]
    if outside:
        errors.append(f"release prepare found changes outside governed release paths: {outside}")
        return {"ok": False, "errors": errors, "checks": checks}
    stage_targets = sorted(set(path for path in changed if matches_governed_path(path, allowed)))
    if stage_targets and run_git(project, ["add", "--all", "--", *stage_targets]).returncode != 0:
        errors.append("release prepare failed to stage governed release paths")
        return {"ok": False, "errors": errors, "checks": checks}
    diff_cached = run_git(project, ["diff", "--cached", "--quiet"])
    if diff_cached.returncode == 1:
        commit_message = f"release-prepare: stage {current_branch} for {version}"
        commit_result = run_git(project, ["commit", "-m", commit_message])
        if commit_result.returncode != 0:
            errors.append(f"release prepare failed to commit staged changes: {(commit_result.stderr or commit_result.stdout).strip()}")
            return {"ok": False, "errors": errors, "checks": checks}
    elif diff_cached.returncode not in {0, 1}:
        errors.append("release prepare could not inspect staged changes")
        return {"ok": False, "errors": errors, "checks": checks}
    checkout_master = run_git(project, ["checkout", "master"])
    if checkout_master.returncode != 0:
        errors.append(f"release prepare failed to checkout master: {(checkout_master.stderr or checkout_master.stdout).strip()}")
        return {"ok": False, "errors": errors, "checks": checks}
    merge_message = f"release-prepare: merge {current_branch} into master for {version}"
    merge = run_git(project, ["merge", "--no-ff", current_branch, "-m", merge_message])
    if merge.returncode != 0:
        errors.append(f"release prepare failed to merge {current_branch} into master: {(merge.stderr or merge.stdout).strip()}")
        return {"ok": False, "errors": errors, "checks": checks}
    delete_branch = run_git(project, ["branch", "-d", current_branch])
    if delete_branch.returncode != 0:
        errors.append(f"release prepare failed to delete branch {current_branch}: {(delete_branch.stderr or delete_branch.stdout).strip()}")
        return {"ok": False, "errors": errors, "checks": checks}
    final_branch, final_locals, final_status = current_branch_and_locals(project)
    checks.update({
        "prepared_branch": current_branch,
        "current_branch": final_branch,
        "local_branches": final_locals,
        "status_lines": final_status,
    })
    if final_branch != "master":
        errors.append("release prepare did not end on master")
    if sorted(final_locals) != protected:
        errors.append(f"release prepare did not end with only protected branches {protected}")
    if final_status:
        errors.append("release prepare requires a clean worktree after merge and branch cleanup")
    return {"ok": not errors, "errors": errors, "checks": checks}

def copy_release_tree(skill_dir: Path, release_dir: Path) -> None:
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(parents=True, exist_ok=True)
    for source in sorted(skill_dir.iterdir(), key=lambda item: item.name.lower()):
        if source.name in INSTALLABLE_SKILL_TOP_LEVEL_EXCLUDES:
            continue
        target = release_dir / source.name
        if source.is_dir():
            shutil.copytree(source, target, ignore=release_copy_ignore)
        else:
            shutil.copy2(source, target)

def package_release(project: Path, version: str, skill_dir_raw: str) -> dict[str, Any]:
    profile = read_json(project / ".agents" / "agents-control.json")
    skill_dir = resolve_project(skill_dir_raw if Path(skill_dir_raw).is_absolute() else project / skill_dir_raw)
    skill_name = skill_dir.name
    source_rel = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else skill_dir.name
    project_kind = release_project_kind(project, skill_dir)
    pre = release_gate(project, version, skill_dir_raw, "pre", "unspecified")
    if pre["errors"]:
        return {"ok": False, "errors": pre["errors"], "pre_gate": pre}
    release_dir = project / "dist" / f"{skill_name}-{version}"
    zip_path = project / "dist" / f"{skill_name}-{version}.zip"
    other_release_exclusions = release_target_exclusions(skill_name, version)
    before_other_artifacts = dist_artifact_snapshot(project, other_release_exclusions)
    copy_release_tree(skill_dir, release_dir)
    receipt_path = release_dir / receipt_filename(profile)
    sanitization, sanitization_errors = sanitize_release_tree(profile, project_kind, skill_dir, release_dir)
    if sanitization_errors:
        return {
            "ok": False,
            "errors": sanitization_errors,
            "pre_gate": pre,
            "release_dir": display_path(release_dir, project),
        }
    after_other_artifacts = dist_artifact_snapshot(project, other_release_exclusions)
    if before_other_artifacts != after_other_artifacts:
        return {
            "ok": False,
            "errors": ["cross-version release artifacts changed outside the current target release directory or zip"],
            "pre_gate": pre,
            "release_dir": display_path(release_dir, project),
        }
    receipt = {
        "skill_name": skill_name,
        "version": version,
        "source_path": source_rel,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "current_branch": "master",
        "local_branches": ["master", "release"],
        "worktree_clean": True,
        "phase_results": {"pre": True, "post": True},
        "packaging_mode": "repository-dist",
        "validation_level": "strong",
        "provenance_mode": "repository-dist",
        "sanitization": sanitization,
        "files": build_release_file_manifest(release_dir),
        "other_version_artifacts": after_other_artifacts,
    }
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    write_release_zip(release_dir, zip_path)
    add_result = run_git(project, ["add", "--all", "--", "dist"])
    if add_result.returncode != 0:
        return {"ok": False, "errors": ["package release failed to stage dist artifacts"], "pre_gate": pre}
    diff_cached = run_git(project, ["diff", "--cached", "--quiet"])
    if diff_cached.returncode == 1:
        commit_result = run_git(project, ["commit", "-m", f"package-release: {skill_name} {version}"])
        if commit_result.returncode != 0:
            return {"ok": False, "errors": [f"package release failed to commit dist artifacts: {(commit_result.stderr or commit_result.stdout).strip()}"], "pre_gate": pre}
    elif diff_cached.returncode not in {0, 1}:
        return {"ok": False, "errors": ["package release could not inspect staged release artifacts"], "pre_gate": pre}
    post = release_gate(project, version, skill_dir_raw, "post", "unspecified")
    return {
        "ok": not post["errors"],
        "errors": post["errors"],
        "release_dir": display_path(release_dir, project),
        "release_zip": display_path(zip_path, project),
        "receipt_path": display_path(receipt_path, project),
        "pre_gate": pre,
        "post_gate": post,
    }

def branch_gate(project: Path) -> dict[str, Any]:
    profile = read_json(project / ".agents" / "agents-control.json")
    if not isinstance(profile, dict):
        return {
            "project": str(project),
            "approved": True,
            "decision": "approved",
            "reasons": [],
            "checks": {"skipped": "no control profile"},
            "force_confirmation_required": False,
            "user_message": "",
        }
    if str(profile.get("git_management", "")).strip() == "no-git-management":
        return {
            "project": str(project),
            "approved": True,
            "decision": "approved",
            "reasons": [],
            "checks": {"skipped": "git management disabled"},
            "force_confirmation_required": False,
            "user_message": "",
        }

    policy = profile.get("git_branch_policy", {}) if isinstance(profile.get("git_branch_policy"), dict) else {}
    protected = policy.get("protected_branches", ["master", "release"])
    branch_model = str(profile.get("branch_model", "")).strip()
    git_branch_result = run_git(project, ["branch", "--show-current"])
    git_list_result = run_git(project, ["branch", "--list"])
    git_status_result = run_git(project, ["status", "--short"])
    reasons: list[str] = []
    checks: dict[str, Any] = {
        "branch_model": branch_model,
        "protected_branches": protected,
        "current_branch": "",
        "local_branches": [],
        "status_lines": [],
    }
    if any(result.returncode != 0 for result in [git_branch_result, git_list_result, git_status_result]):
        reasons.append("git branch governance requires a readable local git repository")
    else:
        current_branch = git_branch_result.stdout.strip()
        local_branches = sorted(normalize_branch_list_line(line) for line in git_list_result.stdout.splitlines() if line.strip())
        status_lines = filter_runtime_status_lines(git_status_result.stdout.splitlines())
        checks["current_branch"] = current_branch
        checks["local_branches"] = local_branches
        checks["status_lines"] = status_lines
        if branch_model == "master-and-dist-release":
            if current_branch != "master":
                reasons.append(f"current branch must be master, found {current_branch or 'unknown'}")
            if sorted(local_branches) != sorted(protected):
                reasons.append(f"local branches must match protected branch set {protected}, found {local_branches}")
        if status_lines:
            reasons.append("worktree must be clean before continuing under strict branch governance")
    approved = not reasons
    cleanup_plan = []
    if not approved:
        cleanup_plan = [
            "commit or intentionally remove current worktree changes",
            "switch back to master",
            "merge or prepare any temporary development branch",
            "delete local branches other than master and release after merge",
            "rerun branch-gate",
        ]
    classified_reasons = [
        {
            "reason": reason,
            "risk": "high" if "worktree" in reason or "branch" in reason else "medium",
            "category": "branch-governance",
        }
        for reason in reasons
    ]
    return {
        "project": str(project),
        "approved": approved,
        "decision": "approved" if approved else "blocked",
        "reasons": reasons,
        "classified_reasons": classified_reasons,
        "cleanup_plan": cleanup_plan,
        "checks": checks,
        "force_confirmation_required": not approved,
        "user_message": "" if approved else "分支治理未通过，默认阻止普通生成/整理流程。若用户仍要继续，必须先明确确认是否进入分支整理或发布治理流程。",
        "decision_request": {} if approved else decision_request(
            "branch_governance",
            question="分支治理未通过。是否进入分支整理或发布治理流程？",
            options=[
                {"label": "进入治理整理", "value": "cleanup", "description": "按建议步骤整理分支和工作树后重跑门禁。", "recommended": True},
                {"label": "暂停当前任务", "value": "pause", "description": "保留现场，等待人工处理分支状态。", "recommended": False},
            ],
            default="cleanup",
            risk="high",
            next_action="run branch cleanup or release governance before continuing",
            context={"reasons": reasons, "cleanup_plan": cleanup_plan},
        ),
    }

def parse_version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value.strip())
    if not match:
        raise ValueError(f"invalid version: {value}")
    return tuple(int(part) for part in match.groups())

def install_confirmation_options() -> list[dict[str, Any]]:
    return [
        {
            "label": "否，跳过安装",
            "value": "skip",
            "description": "默认选项；保留发布产物，但不安装到本地 skills 目录。",
            "recommended": True,
        },
        {
            "label": "安装到 Codex",
            "value": "codex",
            "description": "将发布包安装到当前本地 Codex skills 目录。",
            "recommended": False,
        },
        {
            "label": "自定义 skills 目录",
            "value": "custom",
            "description": "将发布包安装到用户明确提供的自定义 skills 根目录。",
            "recommended": False,
        },
    ]

def latest_release_dir(project: Path, skill_name: str) -> Path | None:
    releases = []
    for path in (project / "dist").glob(f"{skill_name}-v*"):
        if not path.is_dir():
            continue
        match = re.search(r"v(\d+)\.(\d+)\.(\d+)", path.name)
        if match:
            releases.append((tuple(int(part) for part in match.groups()), path))
    if not releases:
        return None
    releases.sort(key=lambda item: item[0])
    return releases[-1][1]

def release_members(root: Path, prefix: Path) -> list[str]:
    members: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if not should_include_release_path(path, root):
            continue
        relative = path.relative_to(prefix).as_posix()
        members.append(relative)
    return sorted(members)

def release_project_kind(project: Path, skill_dir: Path) -> str:
    profile = read_json(project / ".agents" / "agents-control.json")
    if isinstance(profile, dict):
        kind = str(profile.get("kind", "")).strip().lower()
        if kind in {"skill", "engineering"}:
            return kind
    if (skill_dir / "SKILL.md").is_file():
        return "skill"
    return "engineering"

def release_gate(project: Path, version: str, skill_dir_raw: str, phase: str, install_intent: str) -> dict[str, Any]:
    profile = read_json(project / ".agents" / "agents-control.json")
    skill_dir = resolve_project(skill_dir_raw if Path(skill_dir_raw).is_absolute() else project / skill_dir_raw)
    skill_name = skill_dir.name
    project_kind = release_project_kind(project, skill_dir)
    expected_release = project / "dist" / f"{skill_name}-{version}"
    expected_zip = project / "dist" / f"{skill_name}-{version}.zip"
    source_rel = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else skill_dir.name
    receipt_path = expected_release / receipt_filename(profile)
    source_version = read_skill_version(skill_dir)
    git_branch = run_git(project, ["branch", "--show-current"]).stdout.strip()
    branches = sorted(normalize_branch_list_line(line) for line in run_git(project, ["branch", "--list"]).stdout.splitlines() if line.strip())
    status_lines = filter_runtime_status_lines(run_git(project, ["status", "--short"]).stdout.splitlines())
    errors: list[str] = []
    checks = {
        "branch": git_branch,
        "local_branches": branches,
        "phase": phase,
        "install_intent": install_intent,
        "project_kind": project_kind,
        "skill_dir": skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else str(skill_dir),
        "source_version": source_version,
        "expected_release_dir": expected_release.relative_to(project).as_posix(),
        "expected_release_zip": expected_zip.relative_to(project).as_posix(),
        "receipt_path": expected_release.joinpath(receipt_filename(profile)).relative_to(project).as_posix(),
        "status_lines": status_lines,
    }
    source_governance = source_governance_report(project, profile)
    errors.extend(format_source_governance_errors(source_governance, prefix="source-governance"))
    checks["source_governance_ok"] = source_governance["ok"]
    other_release_exclusions = release_target_exclusions(skill_name, version)
    if source_version and source_version != version:
        errors.append(f"release gate version {version} does not match skill source version {source_version}")
    if git_branch != "master":
        errors.append("release gate requires current branch master")
    if sorted(branches) != ["master", "release"]:
        errors.append("release gate requires only local branches master and release")
    if phase == "pre" and status_lines:
        errors.append("pre-release gate requires a clean committed worktree")
    if phase == "post":
        if status_lines:
            errors.append("post-release gate requires a clean committed worktree")
        if not expected_release.is_dir():
            errors.append(f"missing release directory: {expected_release.relative_to(project).as_posix()}")
        if not expected_zip.is_file():
            errors.append(f"missing release zip: {expected_zip.relative_to(project).as_posix()}")
        if expected_release.is_dir():
            release_governance = release_source_governance_report(project, expected_release, profile)
            errors.extend(format_source_governance_errors(release_governance, prefix="release-source-governance"))
            checks["release_source_governance_ok"] = release_governance["ok"]
            source_files = release_members(skill_dir, skill_dir)
            release_files = sorted(item["path"] for item in build_release_file_manifest(expected_release, exclude={receipt_path.name}))
            if source_files != release_files:
                errors.append("release parity mismatch between skill source and dist release directory")
            if not receipt_path.is_file():
                errors.append(f"missing release receipt: {receipt_path.relative_to(project).as_posix()}")
            else:
                receipt = read_release_receipt(receipt_path)
                errors.extend(
                    verify_release_receipt(
                        project,
                        receipt_path,
                        expected_release,
                        skill_name,
                        version,
                        source_rel,
                        require_repo_dist=True,
                    )
                )
                errors.extend(
                    verify_release_sanitization(
                        profile,
                        project_kind,
                        skill_dir,
                        expected_release,
                        receipt,
                    )
                )
                recorded_other_artifacts = receipt.get("other_version_artifacts")
                if not isinstance(recorded_other_artifacts, list):
                    errors.append("release receipt missing other_version_artifacts snapshot")
                else:
                    current_other_artifacts = dist_artifact_snapshot(project, other_release_exclusions)
                    checks["other_version_artifact_count"] = len(current_other_artifacts)
                    if current_other_artifacts != recorded_other_artifacts:
                        errors.append("cross-version release artifacts changed outside the current target release")
    latest = latest_release_dir(project, skill_name)
    if latest is not None:
        checks["latest_release_dir"] = latest.relative_to(project).as_posix()
        if parse_version_tuple(version) < parse_version_tuple(latest.name.rsplit("-", 1)[-1]):
            errors.append("requested release version is older than the latest dist release")
    result = {
        "project": str(project),
        "ok": not errors,
        "errors": errors,
        "checks": checks,
        "installable": not errors and phase == "post",
        "receipt_path": checks["receipt_path"],
        "provenance_mode": "repository-dist",
        "validation_level": "strong",
    }
    if phase == "post" and install_intent == "unspecified" and project_kind == "skill":
        result["install_confirmation_required"] = True
        result["confirmation_question"] = "释放安装版本后，用户尚未说明是否需要安装。是否需要安装当前发布包？"
        result["install_options"] = install_confirmation_options()
        result["decision_request"] = decision_request(
            "install_confirmation",
            question=result["confirmation_question"],
            options=result["install_options"],
            default="skip",
            risk="medium",
            next_action="run install_skill.py with the selected target after release validation",
            context={"release_dir": checks["expected_release_dir"], "version": version},
        )
    else:
        result["install_confirmation_required"] = False
        result["decision_request"] = {}
    return result
