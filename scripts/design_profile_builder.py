
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from design_questions import *
from design_remote_gate import *
from agents_common import ensure_global_rule_overrides_file, inspect_project, emit_json, resolve_project
from manage_docs import scaffold as scaffold_docs
from workspace_settings_policy import workspace_settings_contract

ROOT_OPTIONAL_WORK_DIRS = ("tests", "reports", "runs", "smoke")
ROOT_OPTIONAL_WORK_DIR_PREFIXES = ("smoke-",)

def infer_kind(project: Path) -> str:
    if (
        (project / "SKILL.md").exists()
        or any(path.is_file() for path in project.glob("*/SKILL.md"))
        or any(path.is_file() for path in project.glob("skills/*/SKILL.md"))
    ):
        return "skill"
    return "engineering"

def meaningful_paths(facts: dict[str, Any]) -> bool:
    files = [str(item) for item in facts.get("files", []) if str(item)]
    directories = [str(item) for item in facts.get("directories", []) if str(item)]
    ignored_files = {"AGENTS.md", ".gitignore", ".gitattributes", ".editorconfig"}
    meaningful_files = [item for item in files if item not in ignored_files and not item.startswith(".agents/")]
    meaningful_dirs = [
        item
        for item in directories
        if item
        and item not in {"docs", ".agents"}
        and not item.startswith("docs/")
        and not item.startswith(".agents/")
    ]
    return bool(meaningful_files or meaningful_dirs)

def takeover_required(project: Path) -> tuple[bool, dict[str, Any]]:
    facts = inspect_project(project)
    reasons = {str(item) for item in facts.get("root_agents_md_trigger_reasons", [])}
    triggered = bool(reasons & {"agents_version_mismatch", "generator_version_mismatch"})
    if not triggered:
        return False, facts
    if not meaningful_paths(facts):
        return False, facts
    return True, facts

def missing_answers(answers: dict[str, Any], kind: str) -> list[str]:
    missing: list[str] = []
    remote_policy_required = remote_directory_policy_required(answers)
    for item in questions_for(kind):
        key = str(item["answer_key"])
        if key in {"default_conversation_language", USE_REMOTE_SERVER_KEY}:
            continue
        if key in REMOTE_DIRECTORY_POLICY_KEYS and not remote_policy_required:
            continue
        if key in OPTIONAL_EMPTY_KEYS and key in answers:
            continue
        if key not in answers or empty(answers[key]):
            missing.append(key)
    if ALIGNMENT_KEY not in answers:
        missing.append(ALIGNMENT_KEY)
    return missing

def parse_skill_name(skill_path: Path) -> str:
    text = skill_path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^---\s*\n(.*?)\n---", text, flags=re.DOTALL)
    if not match:
        return ""
    for line in match.group(1).splitlines():
        if line.strip().startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return ""

def discover_skill_files(project: Path) -> list[Path]:
    skip = {".git", "dist", "ref", "__pycache__"}
    files: list[Path] = []
    for path in project.rglob("SKILL.md"):
        relative = path.relative_to(project)
        if set(relative.parts) & skip:
            continue
        files.append(path)
    return sorted(files)

def skill_layout_contract(project: Path, name: str, answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    takeover_mode = bool(answers.get("takeover_mode"))
    if not SKILL_NAME_RE.fullmatch(name):
        errors.append("skill name must use lowercase letters, digits, and hyphens only")

    expected = project / "skills" / name / "SKILL.md"
    files = discover_skill_files(project)

    if expected.exists():
        skill_name = parse_skill_name(expected)
        if skill_name != name:
            errors.append(f"SKILL.md name must match folder name: {name}")
        return {"path": f"skills/{name}", "skill_file": f"skills/{name}/SKILL.md"}, errors

    if answers.get("has_existing_work") == "yes" and not takeover_mode:
        if not files:
            errors.append("skill projects with existing work must already place the skill under skills/<skill-name>/SKILL.md")
        for skill_file in files:
            relative = skill_file.relative_to(project).as_posix()
            parts = skill_file.relative_to(project).parts
            if len(parts) >= 3 and parts[0] == "skills":
                folder = parts[1]
                skill_name = parse_skill_name(skill_file)
                if folder != name:
                    errors.append(f"skill folder must match requested skill name: skills/{name}/")
                if skill_name != folder:
                    errors.append(f"SKILL.md name must match folder name: {folder}")
            else:
                errors.append(f"skill projects must use skills/<skill-name>/SKILL.md; found {relative}")
    return {"path": f"skills/{name}", "skill_file": f"skills/{name}/SKILL.md"}, errors

def directory_layout_policy(kind: str, name: str) -> dict[str, Any]:
    primary = f"skills/{name}/" if kind == "skill" else f"engineering/{name}/"
    return {
        "primary_project_root": primary,
        "allowed_new_paths": [
            primary,
            "tests/",
            "smoke/",
            "reports/",
            "runs/",
            "dist/",
            "docs/",
            ".agents/",
            "ref/",
        ],
        "root_optional_work_dirs": list(ROOT_OPTIONAL_WORK_DIRS),
        "root_optional_work_dir_prefixes": list(ROOT_OPTIONAL_WORK_DIR_PREFIXES),
        "enforce_primary_project_root": True,
    }

def engineering_layout_contract(project: Path, name: str, answers: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = project / "engineering" / name
    if answers.get("has_existing_work") == "yes" and not expected.exists() and not bool(answers.get("takeover_mode")):
        errors.append("engineering projects with existing work must already place the project under engineering/<project-name>/")
    return errors

def summarize_fields(answers: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: answers[key] for key in keys if key in answers}

def review_summary(
    answers: dict[str, Any] | None,
    kind: str | None = None,
    current_keys: list[str] | None = None,
    confirmed_keys: list[str] | None = None,
    final: bool = False,
) -> dict[str, Any]:
    answers = answers or {}
    current_keys = current_keys or []
    confirmed_keys = confirmed_keys or []
    confirmed = summarize_fields(answers, confirmed_keys)
    current = summarize_fields(answers, current_keys)
    if final:
        summary = "请确认完整设计访谈已经一致；如需修正，请提交修正字段后重新确认。"
    elif current_keys:
        summary = "请确认当前问题组的答案是否正确；如果否，请修正本组字段并重新确认。"
    else:
        summary = "请用户确认以上理解是否正确；如果否，请修正对应字段后重新确认。"
    return {
        "kind": kind or answers.get("development_type", "unconfirmed"),
        "current_group_fields": current,
        "confirmed_fields": confirmed,
        "summary": summary,
    }

def attach_alignment(payload: dict[str, Any], answers: dict[str, Any] | None = None, kind: str | None = None) -> dict[str, Any]:
    answers = answers or {}
    confirmed_keys = [key for key in answers if key != ALIGNMENT_KEY]
    payload["review_summary"] = review_summary(answers, kind, [], confirmed_keys, final=False)
    payload["confirmed_so_far"] = payload["review_summary"]["confirmed_fields"]
    payload["confirmation_question"] = "请确认以上理解是否正确？如果正确回答是；如果不正确回答否并指出需要修正的字段。"
    payload["needs_alignment_confirmation"] = answers.get(ALIGNMENT_KEY) is not True
    return payload

def engineering_rule_contract(answers: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    primary_raw = answers.get("engineering_rule_primary", "none")
    if isinstance(primary_raw, list):
        return None, ["engineering_rule_primary must name one primary rule set, not a list"]
    primary = str(primary_raw).strip().lower() or "none"
    mode = str(answers.get("engineering_rule_mode", "none" if primary == "none" else "mini")).strip().lower()
    scope = str(answers.get("engineering_rule_scope", "on-demand")).strip().lower()
    notes = str(answers.get("engineering_rule_notes", "")).strip()

    if primary in {"", "none", "not-configured"}:
        if mode != "none":
            return None, ["engineering_rule_mode must be none when engineering_rule_primary is none"]
        return {
            "primary": "none",
            "mode": "none",
            "scope": "on-demand",
            "notes": notes,
            "full_reference_allowed_in_agents": False,
            "compatibility_policy": "no active book-derived rule set configured",
            "compression_policy": "keep only decision-changing rules in generated AGENTS.md",
        }, []

    errors: list[str] = []
    if "," in primary or "+" in primary:
        errors.append("engineering_rule_primary must choose one primary active rule set")
    if primary not in ENGINEERING_RULE_SETS:
        errors.append(f"unknown engineering_rule_primary: {primary}")
    if mode == "full":
        errors.append("full book rules must stay reference-only and must not be pasted into AGENTS.md")
    elif mode not in ENGINEERING_RULE_MODES or mode == "none":
        errors.append("engineering_rule_mode must be mini or nano")
    if scope not in ENGINEERING_RULE_SCOPES:
        errors.append("engineering_rule_scope must be project-baseline, scoped, or on-demand")
    if errors:
        return None, errors

    return {
        "primary": primary,
        "mode": mode,
        "scope": scope,
        "notes": notes,
        "full_reference_allowed_in_agents": False,
        "compatibility_policy": "one primary active rule set; use other rule sets only as scoped or on-demand guidance",
        "compression_policy": "decision-equivalent compression: keep decision-changing, trigger, tradeoff, and checklist rules",
    }, []

def normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw:
        return []
    return [item.strip() for item in raw.replace("，", ",").split(",") if item.strip()]


def invalid_remote_relative_template_reason(raw: str) -> str | None:
    value = str(raw).strip()
    normalized = value.replace("\\", "/")
    if not value:
        return "template must not be empty"
    if re.match(r"^[A-Za-z]:[/\\]", value) or normalized.startswith("/"):
        return "template must stay relative to the remote workspace root"
    if ".." in normalized.split("/"):
        return "template must not contain parent traversal"
    if any(char in value for char in "*?|"):
        return "template must not contain wildcard or unsafe shell characters"
    if "//" in normalized:
        return "template must not contain repeated path separators"
    return None


def disabled_remote_environment_policy() -> dict[str, Any]:
    return {
        "status": "disabled",
        "scope": "remote-only",
        "manager": "conda-prefix",
        "path_template": "",
        "required_when_remote_configured": True,
    }


def disabled_remote_runtime_archive_policy() -> dict[str, Any]:
    return {
        "status": "disabled",
        "active_path_template": "",
        "backup_path_template": "",
        "run_id_required": True,
        "archive_after_verification": False,
        "archive_trigger": "",
    }


def remote_environment_policy(answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    if not remote_directory_policy_required(answers):
        return disabled_remote_environment_policy(), []
    path_template = str(answers.get("remote_conda_environment_layout", "")).strip()
    if not path_template:
        return {}, ["missing required answer: remote_conda_environment_layout"]
    if path_template.lower() == "disabled":
        return {}, ["remote_conda_environment_layout cannot be `disabled` when remote structure or remote servers are enabled"]
    invalid = invalid_remote_relative_template_reason(path_template)
    if invalid:
        return {}, [f"remote_conda_environment_layout {invalid}: {path_template}"]
    return {
        "status": "enabled",
        "scope": "remote-only",
        "manager": "conda-prefix",
        "path_template": path_template,
        "required_when_remote_configured": True,
    }, []


def remote_runtime_archive_policy(answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    if not remote_directory_policy_required(answers):
        return disabled_remote_runtime_archive_policy(), []
    active_path = str(answers.get("remote_run_artifact_active_layout", "")).strip()
    backup_path = str(answers.get("remote_run_artifact_backup_layout", "")).strip()
    trigger = str(answers.get("remote_run_archive_trigger", "")).strip()
    missing = []
    if not active_path:
        missing.append("missing required answer: remote_run_artifact_active_layout")
    if not backup_path:
        missing.append("missing required answer: remote_run_artifact_backup_layout")
    if not trigger:
        missing.append("missing required answer: remote_run_archive_trigger")
    if missing:
        return {}, missing
    invalid = [
        key
        for key, value in {
            "remote_run_artifact_active_layout": active_path,
            "remote_run_artifact_backup_layout": backup_path,
            "remote_run_archive_trigger": trigger,
        }.items()
        if value.lower() == "disabled"
    ]
    if invalid:
        return {}, [f"{key} cannot be `disabled` when remote structure or remote servers are enabled" for key in invalid]
    template_errors: list[str] = []
    for key, value in {
        "remote_run_artifact_active_layout": active_path,
        "remote_run_artifact_backup_layout": backup_path,
    }.items():
        invalid_reason = invalid_remote_relative_template_reason(value)
        if invalid_reason:
            template_errors.append(f"{key} {invalid_reason}: {value}")
    if template_errors:
        return {}, template_errors
    return {
        "status": "enabled",
        "active_path_template": active_path,
        "backup_path_template": backup_path,
        "run_id_required": "<run-id>" in active_path or "<run-id>" in backup_path,
        "archive_after_verification": trigger.casefold() == "after required verification passes".casefold(),
        "archive_trigger": trigger,
    }, []


def global_rule_overrides_contract() -> dict[str, Any]:
    return {
        "path": ".agents/global-rule-overrides.json",
        "details_mode": "json-config",
    }

def skill_design_contract(answers: dict[str, Any]) -> dict[str, Any]:
    return {
        "trigger_scenarios": str(answers["trigger_scenarios"]).strip(),
        "patterns": normalize_list(answers["skill_design_patterns"]),
        "resource_plan": str(answers["resource_plan"]).strip(),
        "progressive_disclosure_policy": str(answers["progressive_disclosure_policy"]).strip(),
        "validation_gates": str(answers["validation_gates"]).strip(),
        "validation_method": str(answers["validation_method"]).strip(),
        "validation_granularity": str(answers["validation_granularity"]).strip(),
        "forward_testing_policy": str(answers["forward_testing_policy"]).strip(),
        "reference_material_policy": "temporary inputs only; distill durable constraints and remove local reference paths from generated AGENTS.md",
    }

def docs_contract(name: str) -> dict[str, Any]:
    branch_policy = git_branch_policy()
    contract = {
        "root": "docs",
        "handoff": {
            "current": "docs/handoff/HANDOFF.md",
            "history": "docs/handoff/history_handoff",
            "archive_pattern": "HANDOFF-YYYYMMDD-HHMMSS.md",
            "required_sections": [
                "original_plan_and_steps",
                "current_step",
                "problems",
                "resolved_problems",
                "remaining_problems",
                "next_work",
                "verification_evidence",
            ],
        },
        "experience": {
            "folder": "docs/experience",
            "history": "docs/experience/history_experience",
            "summarize_every_handoffs": 5,
            "ai_generation_required": True,
            "conversation_context_limit": 10,
            "file_count": 10,
            "required_files": ["1-workflow.md", "2-scripts.md", "3-plan.md", "4-design-ui.md"],
            "optional_file_pattern": "5-xxxxx.md through 10-xxxxx.md",
            "topic_policy": "Maintain 10 project-specific numbered experience files. The first four names are fixed; choose files 5-10 from current project facts such as testing, validation, release, installation, docs governance, directory governance, or remote deployment.",
        },
        "development": {
            "folder": "docs/development",
            "current": "docs/development/DEVELOPMENT.md",
            "history": "docs/development/history_development",
            "history_pattern": "YYYYMMDD-HHMMSS/DEVELOPMENT.md",
            "when": "Write and iteratively refresh the latest DEVELOPMENT.md at installable release time or stage completion.",
        },
        "install_configuration": {
            "folder": "docs/install_configuration",
            "targets": ["Codex", "Claude", "OpenClaw"],
        },
        "git_manager": {
            "folder": "docs/git_manager",
            "branch_model": "master-and-dist-release",
            "branch_policy": branch_policy,
            "change_log": "docs/git_manager/CHANGELOG.md",
            "history": "docs/git_manager/history_git_manager",
            "dist_folder": "dist",
            "release_folder_pattern": f"{name}-vx.x.x",
            "zip_required": True,
        },
        "dir_manager": {
            "folder": "docs/dir_manager",
            "current_structure": "docs/dir_manager/current_structure.json",
            "planned_structure": "docs/dir_manager/planned_structure.json",
            "history": "docs/dir_manager/history_dir_manager",
            "review_required_for": ["create", "move", "delete", "rename"],
            "block_on_failed_review": True,
            "force_override_requires_user_confirmation": True,
            "archive_before_force_override": True,
        },
        "workspace_settings": workspace_settings_contract(),
    }
    return contract


def memory_contract(answers: dict[str, Any]) -> dict[str, Any]:
    enabled = bool(answers.get("memory_enabled"))
    backend = str(answers.get("memory_storage_backend", "sqlite-plus-jsonl")).strip() or "sqlite-plus-jsonl"
    return {
        "enabled": enabled,
        "folder": "docs/memory",
        "storage_backend": backend,
        "database": "docs/memory/memory.sqlite3",
        "events": "docs/memory/events.jsonl",
        "summaries": "docs/memory/summaries.md",
        "guide": "docs/memory/MEMORY.md",
        "capture_scope": str(answers.get("memory_capture_scope", "")).strip(),
        "read_policy": str(answers.get("memory_read_policy", "")).strip(),
        "sensitivity_policy": str(answers.get("memory_sensitivity_policy", "")).strip(),
        "compress_after_events": 20,
    }


def memory_policy_errors(answers: dict[str, Any]) -> list[str]:
    if not bool(answers.get("memory_enabled")):
        return []
    backend = str(answers.get("memory_storage_backend", "")).strip()
    if backend != "sqlite-plus-jsonl":
        return ["memory_storage_backend must be sqlite-plus-jsonl when memory_enabled is true"]
    return []


def git_branch_policy() -> dict[str, Any]:
    return {
        "protected_branches": ["master", "release"],
        "development_branches_allowed": True,
        "release_requires_committed_worktree": True,
        "release_requires_merge_to_master": True,
        "delete_other_local_branches_before_release": True,
        "release_prepare_auto_commit": True,
        "release_prepare_commit_message_template": "release-prepare: stage {branch} for {version}",
        "release_prepare_merge_message_template": "release-prepare: merge {branch} into master for {version}",
        "release_prepare_allowed_paths": ["<primary-project-root>", "tests", "docs", ".agents", "AGENTS.md", "dist"],
        "install_requires_release_artifact": True,
        "source_install_forbidden": True,
        "remote_branch_cleanup_allowed": False,
        "rule": "Before releasing an installable dist package, commit all work, merge development branches into master, record the release, and delete local branches other than master and release.",
    }

def dir_manager_contract() -> dict[str, Any]:
    return {
        "folder": "docs/dir_manager",
        "current_structure": "docs/dir_manager/current_structure.json",
        "planned_structure": "docs/dir_manager/planned_structure.json",
        "history": "docs/dir_manager/history_dir_manager",
        "review_required_for": [
            "create top-level directories",
            "move directories",
            "delete directories",
            "rename directories",
            "change ownership, generated, release, or governance directories",
        ],
        "block_on_failed_review": True,
        "force_override_requires_user_confirmation": True,
        "archive_before_force_override": True,
    }

def remote_server_contract(project: Path, answers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    enabled = use_remote_server_enabled(answers)
    if not enabled:
        return {
            "enabled": False,
            "dependency_required": False,
            "dependency_status": "not_required",
            "server_registry": [],
            "task_routes": [],
            "validation_required": False,
            "validation_status": "not_required",
            "unmatched_task_policy": "block-and-update-agents",
            "failover_policy": "auto-fallback",
            "enforce_remote_task_routing": False,
        }, []

    errors: list[str] = []
    dependency = remote_dependency_summary()
    if not dependency["installed"]:
        return {}, [f"use_remote_server=true requires installed {REMOTE_SSH_SKILL_NAME} ({REMOTE_SSH_GIT_URL})"]
    skill_dir = Path(str(dependency["skill_dir"]))
    choices, choice_errors = remote_choices(skill_dir)
    errors.extend(choice_errors)
    registry = normalize_remote_server_registry(choices.get("servers", [])) if not choice_errors else []
    registry_map = server_registry_map(registry)
    raw_routes = answers.get(REMOTE_SERVER_TASK_ROUTES_KEY, [])
    routes = normalize_remote_task_routes(raw_routes)

    if not routes:
        selected_id = str(answers.get(REMOTE_SELECTED_SERVER_ID_KEY, "")).strip()
        selected_name = str(answers.get(REMOTE_SELECTED_SERVER_NAME_KEY, "")).strip()
        selected_category = str(answers.get(REMOTE_SELECTED_SERVER_CATEGORY_KEY, "")).strip()
        selected_functions = answers.get(REMOTE_SELECTED_SERVER_FUNCTIONS_KEY, [])
        selected_tasks = normalize_remote_task_list(answers.get(REMOTE_SELECTED_SERVER_TASKS_KEY, []))
        if not selected_id:
            errors.append(f"missing required answer: {REMOTE_SELECTED_SERVER_ID_KEY}")
        if not selected_name:
            errors.append(f"missing required answer: {REMOTE_SELECTED_SERVER_NAME_KEY}")
        if answers.get(REMOTE_SELECTION_CONFIRMED_KEY) is not True:
            errors.append(f"{REMOTE_SELECTION_CONFIRMED_KEY} must be true when use_remote_server is enabled")
        if str(answers.get(REMOTE_VALIDATION_STATUS_KEY, "")).strip().lower() != "verified":
            errors.append(f"{REMOTE_VALIDATION_STATUS_KEY} must be verified when use_remote_server is enabled")
        if not errors:
            record = remote_server_record(choices.get("servers", []), selected_id) if not choice_errors else None
            if record is None:
                errors.append(f"selected remote server is no longer available in erie-remote-ssh choices: {selected_id}")
            else:
                check_data, check_errors = remote_server_check(skill_dir, selected_id)
                workspace_data, workspace_errors = remote_server_workspace_check(skill_dir, selected_id)
                errors.extend(check_errors)
                errors.extend(workspace_errors)
                if not selected_name:
                    selected_name = str(record.get("name", "")).strip()
                if not selected_category:
                    selected_category = str(record.get("category", "")).strip()
                if not selected_functions and isinstance(record.get("functions"), list):
                    selected_functions = record.get("functions", [])
                if not selected_tasks and isinstance(record.get("functions"), list):
                    selected_tasks = normalize_remote_task_list(record.get("functions", []))
        if not errors:
            functions = [str(item).strip() for item in selected_functions if str(item).strip()] if isinstance(selected_functions, list) else []
            tasks = selected_tasks or normalize_remote_task_list(functions)
            if not tasks:
                return {}, [f"use_remote_server=true requires non-empty {REMOTE_SELECTED_SERVER_TASKS_KEY} or remote server functions"]
            if not registry and selected_id:
                registry = [
                    {
                        "id": selected_id,
                        "name": selected_name,
                        "category": selected_category,
                        "functions": functions,
                        "enabled": True,
                        "validation_status": "verified",
                        "workspace_status": "ok",
                    }
                ]
                registry_map = server_registry_map(registry)
            routes = [
                {
                    "task_name": REMOTE_LEGACY_TASK_NAME,
                    "task_key": normalize_remote_task_key(REMOTE_LEGACY_TASK_NAME),
                    "primary_server_id": selected_id,
                    "fallback_server_ids": [],
                    "route_tasks": tasks,
                    "route_functions": functions,
                    "selection_confirmed": True,
                    "validation_status": "verified",
                }
            ]

    for route in routes:
        errors.extend(validate_route_server_ids(route, registry_map))
        primary_functions = []
        primary_server = registry_map.get(str(route.get("primary_server_id", "")).strip(), {})
        if isinstance(primary_server, dict):
            primary_functions = normalize_remote_task_list(primary_server.get("functions", []))
        if not route.get("route_tasks"):
            route["route_tasks"] = primary_functions or [str(route.get("task_name", "")).strip()]
        if not route.get("route_functions"):
            route["route_functions"] = primary_functions
        resolution = resolve_remote_server_for_task(
            {
                "enabled": True,
                "server_registry": registry,
                "task_routes": [route],
                "unmatched_task_policy": "block-and-update-agents",
                "failover_policy": "auto-fallback",
            },
            str(route.get("task_name", "")),
            skill_dir,
        )
        if not resolution.get("ok"):
            errors.extend(resolution.get("failures", []) or [str(resolution.get("message", "remote route validation failed"))])
        else:
            route["selection_confirmed"] = True
            route["validation_status"] = "verified"
    if errors:
        return {}, errors
    return {
        "enabled": True,
        "dependency_required": True,
        "dependency_status": "installed",
        "server_registry": registry,
        "task_routes": routes,
        "validation_required": True,
        "validation_status": "verified",
        "unmatched_task_policy": "block-and-update-agents",
        "failover_policy": "auto-fallback",
        "enforce_remote_task_routing": True,
    }, []

def build_profile(project: Path, answers: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    kind = answers.get("development_type", infer_kind(project))
    if kind not in {"skill", "engineering"}:
        return None, ["development_type must be skill or engineering"]
    missing = missing_answers(answers, kind)
    if missing:
        return None, [f"missing required answer: {key}" for key in missing]
    rule_contract, rule_errors = engineering_rule_contract(answers)
    if rule_errors:
        return None, rule_errors
    assert rule_contract is not None
    validation_errors: list[str] = []
    remote_environment_contract, remote_environment_errors = remote_environment_policy(answers)
    validation_errors.extend(remote_environment_errors)
    remote_runtime_contract, remote_runtime_errors = remote_runtime_archive_policy(answers)
    validation_errors.extend(remote_runtime_errors)
    validation_errors.extend(memory_policy_errors(answers))
    if validation_errors:
        return None, validation_errors
    remote_contract, remote_errors = remote_server_contract(project, answers)
    if remote_errors:
        return None, remote_errors

    if kind == "skill":
        purpose = answers["skill_purpose"]
        reason = answers["skill_reason"]
        audience = answers["audience"]
        notes_key = "design_notes"
    else:
        purpose = answers["project_purpose"]
        reason = answers["project_reason"]
        audience = answers.get("environment", "")
        notes_key = "reusable_experience"

    name = str(answers["name"]).strip()
    layout: dict[str, Any] | None = None
    if kind == "skill":
        layout, layout_errors = skill_layout_contract(project, name, answers)
        if layout_errors:
            return None, layout_errors
    else:
        layout_errors = engineering_layout_contract(project, name, answers)
        if layout_errors:
            return None, layout_errors

    default_language = str(answers.get("default_conversation_language", "中文")).strip() or "中文"
    profile: dict[str, Any] = {
        "schema_version": 1,
        "kind": kind,
        "name": name,
        "default_conversation_language": default_language,
        "purpose": purpose,
        "reason": reason,
        "alignment_confirmed": bool(answers.get(ALIGNMENT_KEY)),
        "audience_or_environment": audience,
        "reference_materials_temporary": answers.get("reference_materials", []),
        "notes": answers.get(notes_key, ""),
        "git_management": answers["git_management"],
        "branch_model": answers["branch_model"],
        "git_branch_policy": git_branch_policy(),
        "release_contract": {
            "rule": answers["release_contract"],
            "dist_folder": "dist",
            "release_folder_pattern": f"{name}-vx.x.x",
            "zip_required": True,
            "receipt_file": "RELEASE_RECEIPT.json",
            "install_source_policy": "versioned-dist-release-only",
            "repo_install_validation_level": "strong",
            "external_install_validation_level": "reduced_assurance",
            "remote_push_allowed": False,
            "sanitization_required": kind == "skill",
            "sanitization_scope": "broad" if kind == "skill" else "not-applicable",
            "sanitization_mode": "auto-redact-dist-copy" if kind == "skill" else "disabled",
            "sanitization_receipt_required": kind == "skill",
        },
        "existing_work": answers["has_existing_work"],
        "global_rule_overrides": global_rule_overrides_contract(),
        "directory_contract": {
            "confirmed": bool(answers["directory_contract_confirmed"]),
            "local": answers["local_directory_structure"],
            "remote": answers["remote_directory_structure"],
            "feature_rules": answers["feature_directory_rules"],
            "workspace_settings_policy": workspace_settings_contract(),
            "remote_environment_policy": remote_environment_contract,
            "remote_runtime_archive_policy": remote_runtime_contract,
            **directory_layout_policy(kind, name),
        },
        "experience_contract": {
            "folder": "docs/experience",
            "file_pattern": "1-xxxxx.md through 10-xxxxx.md",
            "file_count": 10,
            "required_files": ["1-workflow.md", "2-scripts.md", "3-plan.md", "4-design-ui.md"],
            "project_specific_files": "5-xxxxx.md through 10-xxxxx.md are named from current project facts.",
            "summarize_every_handoffs": 5,
            "ai_generation_required": True,
            "conversation_context_limit": 10,
            "required_sections": [
                "evidence_read",
                "task_context",
                "how_to_apply",
                "problems_and_risks",
                "iterated_lessons",
                "next_application",
            ],
        },
        "dir_manager_contract": dir_manager_contract(),
        "engineering_rule_contract": rule_contract,
        "remote_server_contract": remote_contract,
        "memory_enabled": bool(answers.get("memory_enabled")),
        "memory_storage_backend": str(answers.get("memory_storage_backend", "")).strip(),
        "memory_capture_scope": str(answers.get("memory_capture_scope", "")).strip(),
        "memory_read_policy": str(answers.get("memory_read_policy", "")).strip(),
        "memory_sensitivity_policy": str(answers.get("memory_sensitivity_policy", "")).strip(),
        "memory_contract": memory_contract(answers),
        "development_requirements": answers["development_requirements"],
        "extra_requirements": normalize_extra_requirements(answers.get(EXTRA_REQUIREMENTS_KEY, "none")),
        "expected_outcome": answers["expected_outcome"],
        "validation_method": answers["validation_method"],
        "validation_granularity": answers["validation_granularity"],
        "resource_plan": answers["resource_plan"],
        "forward_testing_policy": answers["forward_testing_policy"],
    }
    primary_root = str(profile["directory_contract"].get("primary_project_root", "")).strip()
    if primary_root and isinstance(profile.get("git_branch_policy"), dict):
        profile["git_branch_policy"]["release_prepare_allowed_paths"] = [
            primary_root,
            "tests",
            "smoke",
            "reports",
            "runs",
            "docs",
            ".agents",
            "AGENTS.md",
            "dist",
        ]
    if kind == "skill":
        profile["skill_layout"] = layout
        profile["skill_design_contract"] = skill_design_contract(answers)
    if isinstance(answers.get(DESIGN_REVIEW_KEY), dict):
        profile[DESIGN_REVIEW_KEY] = answers[DESIGN_REVIEW_KEY]
    profile["docs_contract"] = docs_contract(name)
    if isinstance(profile.get("docs_contract"), dict):
        profile["docs_contract"]["memory"] = profile["memory_contract"]
    return profile, []

def write_profile(project: Path, profile: dict[str, Any]) -> Path:
    agents_dir = project / ".agents"
    agents_dir.mkdir(exist_ok=True)
    path = agents_dir / "agents-control.json"
    path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")
    ensure_global_rule_overrides_file(project, profile)
    scaffold_docs(project)
    return path
