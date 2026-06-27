"""构造 agents-md-generator 回归评估所需的项目夹具。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

RUNTIME_DIR = Path(__file__).resolve().parent
SCRIPTS_PYTHON_DIR = RUNTIME_DIR.parent
SCRIPTS_DIR = SCRIPTS_PYTHON_DIR.parent
SKILL_DIR = SCRIPTS_DIR.parent
REPO_ROOT = Path.cwd().resolve()


class EvalFixtures:
    """集中生成评估脚本复用的项目答案、文件树和命令夹具。"""

    def __init__(self, scripts_dir: Path | None = None) -> None:
        self.scripts_dir = Path(scripts_dir) if scripts_dir is not None else SCRIPTS_DIR

    def remote_directory_answers(
        self,
        remote_directory_structure: str = "remote/workspace/demo-skill",
        include_remote_policy: bool = True,
    ) -> dict[str, Any]:
        """生成远程目录治理场景使用的访谈答案。"""

        answers: dict[str, Any] = {
            "local_directory_structure": "engineering/demo-skill/, tests/, dist/",
            "remote_directory_structure": remote_directory_structure,
            "feature_directory_rules": "features in src/features/<name>/ with tests nearby",
            "directory_contract_confirmed": True,
        }

        if include_remote_policy:

            answers.update(
                {
                    "remote_conda_environment_layout": ".conda/<env-name>/",
                    "remote_run_artifact_active_layout": "runs/<run-id>/",
                    "remote_run_artifact_backup_layout": "backups/runs/<run-id>/",
                    "remote_run_archive_trigger": "after required verification passes",
                }
            )

        return answers

    def skill_answers(
        self,
        name: str = "demo-skill",
        remote_directory_structure: str = "not configured",
        include_remote_policy: bool = False,
        use_remote_server: bool = False,
    ) -> dict[str, Any]:
        """生成 skill 项目治理场景的完整访谈答案。"""

        answers: dict[str, Any] = {
            "development_type": "skill",
            "default_conversation_language": "\u4e2d\u6587",
            "use_remote_server": use_remote_server,
            "memory_enabled": True,
            "memory_storage_backend": "sqlite-plus-jsonl",
            "memory_capture_scope": "handoff summaries, user-confirmed project preferences, durable decisions, validation lessons, and release lessons",
            "memory_read_policy": "read latest handoff plus relevant docs/memory summaries before implementation",
            "memory_sensitivity_policy": "do not store secrets, credentials, or raw local private paths",
            "skill_purpose": "Create verified AGENTS.md files.",
            "skill_reason": "Keep agent onboarding deterministic.",
            "development_requirements": "Collect facts and render AGENTS.md with strict design-review gates.",
            "expected_outcome": "Verified AGENTS.md guidance exists.",
            "validation_method": "automated scripts plus user review",
            "validation_granularity": "unit tests, AGENTS verification, skill audit, full evaluate chain",
            "reference_materials": ["none"],
            "audience": "maintainers",
            "name": name,
            "design_notes": "Keep SKILL.md concise.",
            "trigger_scenarios": "Use when a repo needs AGENTS.md generation or review.",
            "skill_design_patterns": ["Tool Wrapper", "Generator", "Reviewer", "Inversion", "Pipeline"],
            "resource_plan": "scripts/ for deterministic checks, references/ for policy, assets/ for templates",
            "progressive_disclosure_policy": "Keep SKILL.md lean and move detailed policy to references.",
            "validation_gates": "quick_validate.py, audit_skill.py, verify_agents.py, evaluate_skill.py",
            "forward_testing_policy": "Forward-test complex workflows.",
            "git_management": "yes-local-only",
            "branch_model": "master-and-dist-release",
            "release_contract": f"dist/{name}-vx.x.x plus zip",
            "has_existing_work": "yes",
            "alignment_confirmed": True,
        }

        answers.update(
            self.remote_directory_answers(
                remote_directory_structure=remote_directory_structure,
                include_remote_policy=include_remote_policy,
            )
        )
        answers["local_directory_structure"] = f"skills/{name}/, tests/, dist/"
        answers["feature_directory_rules"] = "scripts in scripts/, detailed policy in references/"

        return answers

    def load_script_module(self, name: str) -> Any:
        """按文件名从当前脚本目录加载待测模块。"""

        spec = importlib.util.spec_from_file_location(name, self.script_path(name))

        if spec is None or spec.loader is None:

            raise RuntimeError(f"unable to load script module: {name}")
        module = importlib.util.module_from_spec(spec)

        spec.loader.exec_module(module)

        return module

    def script_path(self, name: str) -> Path:
        """按脚本文件名解析任务分类后的运行时路径。"""

        candidates = sorted((self.scripts_dir / "python").glob(f"*/{name}"))
        return candidates[0] if candidates else self.scripts_dir / name

    def add_approved_design_review(
        self,
        project: Path,
        answers: dict[str, Any],
        reviewer_type: str = "subagent",
        verdict: str = "approve",
        required_user_confirmations: list[Any] | None = None,
        hash_override: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        reviewed = dict(answers)

        reviewed.setdefault("extra_requirements", "none")
        module = self.load_script_module("design_review_gate.py")
        hashes = module.design_review_hashes(project, reviewed)

        if hash_override:

            hashes.update(hash_override)

        reviewed["design_review"] = {
            "reviewer_type": reviewer_type,
            "verdict": verdict,
            "findings": [] if verdict == "approve" else ["design gap requires correction"],
            "required_user_confirmations": required_user_confirmations or [],
            "reviewed_answers_hash": hashes["reviewed_answers_hash"],
            "reviewed_profile_hash": hashes["reviewed_profile_hash"],
            "review_summary": "Subagent reviewed the complete design profile and approved the plan.",
        }

        return reviewed

    def write_reviewed_answers(self, project: Path, path: Path, answers: dict[str, Any], env: dict[str, str] | None = None) -> dict[str, Any]:
        explicit_answers = dict(answers)

        explicit_answers.setdefault("use_remote_server", False)

        explicit_answers.setdefault("memory_enabled", True)

        explicit_answers.setdefault("memory_storage_backend", "sqlite-plus-jsonl")

        explicit_answers.setdefault(
            "memory_capture_scope",
            "handoff summaries, user-confirmed project preferences, durable decisions, validation lessons, and release lessons",
        )

        explicit_answers.setdefault(
            "memory_read_policy",
            "read latest handoff plus relevant docs/memory summaries before implementation",
        )

        explicit_answers.setdefault(
            "memory_sensitivity_policy",
            "do not store secrets, credentials, or raw local private paths",
        )
        old_env = {key: os.environ.get(key) for key in (env or {})}

        try:

            if env:

                os.environ.update(env)
            reviewed = self.add_approved_design_review(project, explicit_answers)
        finally:

            for key, value in old_env.items():

                if value is None:

                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        path.write_text(json.dumps(reviewed), encoding="utf-8")

        return reviewed

    def make_installed_skill_fixture(self, root: Path, version: str = "v0.4.3") -> Path:
        skill = root / "codex-home" / "skills" / "agents-md-generator"

        skill.mkdir(parents=True)

        (skill / "SKILL.md").write_text(
            "---\nname: agents-md-generator\ndescription: Use when testing installed version\n---\n# Skill\n",
            encoding="utf-8",
        )

        (skill / "VERSION").write_text(version + "\n", encoding="utf-8")

        return skill

    def write_release_governance_profile(self, root: Path, kind: str = "skill", name: str = "agents-md-generator") -> None:

        (root / ".agents").mkdir(exist_ok=True)
        primary_root = f"skills/{name}" if kind == "skill" else f"engineering/{name}"

        (root / ".agents" / "agents-control.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": kind,
                    "name": name,
                    "git_management": "yes-local-only",
                    "branch_model": "master-and-dist-release",
                    "git_branch_policy": {
                        "protected_branches": ["master", "release"],
                        "development_branches_allowed": True,
                        "release_prepare_allowed_paths": [f"skills/{name}", "tests", "docs", ".agents", "AGENTS.md", "dist"],
                    },
                    "directory_contract": {
                        "confirmed": True,
                        "local": f"{primary_root}/, tests/, dist/",
                        "remote": "not configured",
                        "features": "features stay inside the governed project root",
                        "primary_project_root": primary_root,
                        "feature_directory_rules": "keep new work inside the primary project root",
                    },
                    "release_contract": {
                        "current_version": "v0.4.4",
                        "protected_branches": ["master", "release"],
                        "dist_pattern": f"dist/{name}-vx.x.x",
                        "zip_required": True,
                        "receipt_file": "RELEASE_RECEIPT.json",
                        "install_source_policy": "versioned-dist-release-only",
                        "repo_install_validation_level": "strong",
                        "external_install_validation_level": "reduced_assurance",
                        "sanitization_required": kind == "skill",
                        "sanitization_scope": "broad" if kind == "skill" else "not-applicable",
                        "sanitization_mode": "auto-redact-dist-copy" if kind == "skill" else "disabled",
                        "sanitization_receipt_required": kind == "skill",
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def make_governed_skill_project(self, root: Path, name: str = "agents-md-generator", version: str = "v0.4.3") -> Path:
        skill = root / "skills" / name

        skill.mkdir(parents=True)

        (skill / "scripts").mkdir(exist_ok=True)

        (skill / "references").mkdir(exist_ok=True)

        (skill / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Use when testing\n---\n# Skill\n",
            encoding="utf-8",
        )

        (skill / "VERSION").write_text(version + "\n", encoding="utf-8")

        (skill / "README.md").write_text("# Demo Skill\n", encoding="utf-8")

        (skill / "scripts" / "quick_validate.py").write_text(
            "from pathlib import Path\n\n\ndef quick_validate_path() -> Path:\n    return Path.home() / '.codex' / 'skills' / '.system' / 'skill-creator' / 'scripts' / 'quick_validate.py'\n",
            encoding="utf-8",
        )
        quick_validate_cmd = f"python skills/{name}/scripts/python/verify/quick_validate.py skills/{name}"

        (skill / "references" / "review-checklist.md").write_text(
            "\n".join(
                [
                    "# Review Checklist",
                    "",
                    "| Gate | Required evidence |",
                    "|------|-------------------|",
                    f"| Structure | `{quick_validate_cmd}` passes for this skill |",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        (skill / "references" / "skill-design-coverage.md").write_text(
            "\n".join(
                [
                    "# Skill Design Coverage",
                    "",
                    f"- Validation gates such as `{quick_validate_cmd}`, skill audit, AGENTS.md verification, and full evaluate chain.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        (root / "docs").mkdir(exist_ok=True)

        (root / "docs" / "note.md").write_text("release governance\n", encoding="utf-8")

        self.write_release_governance_profile(root, kind="skill", name=name)

        return skill

    def init_basic_git_repo(self, root: Path) -> None:

        subprocess.run(["git", "init", "-b", "master"], cwd=root, check=True, capture_output=True, text=True)

        subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True, text=True)

        subprocess.run(["git", "config", "user.email", "test-user.invalid"], cwd=root, check=True, capture_output=True, text=True)

    def git_commit_all(self, root: Path, message: str, when: str | None = None) -> None:
        env = dict(os.environ)

        if when:
            env["GIT_AUTHOR_DATE"] = when
            env["GIT_COMMITTER_DATE"] = when

        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True, env=env)

        subprocess.run(["git", "commit", "-m", message], cwd=root, check=True, capture_output=True, text=True, env=env)

    def init_governed_git_repo(self, root: Path) -> None:

        subprocess.run(["git", "init", "-b", "master"], cwd=root, check=True, capture_output=True, text=True)

        subprocess.run(["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True, text=True)

        subprocess.run(["git", "config", "user.email", "test-user.invalid"], cwd=root, check=True, capture_output=True, text=True)

        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)

        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True, text=True)

        subprocess.run(["git", "checkout", "-b", "release"], cwd=root, check=True, capture_output=True, text=True)

        subprocess.run(["git", "checkout", "master"], cwd=root, check=True, capture_output=True, text=True)

    def make_rendered_governed_skill_project(
        self,
        root: Path,
        name: str = "demo-skill",
        project_version: str = "v0.4.4",
        installed_version: str = "v0.4.3",
    ) -> tuple[Path, Path]:
        skill = self.make_governed_skill_project(root, name=name, version=project_version)
        answers = self.skill_answers(name=name)
        answers_path = root / "answers.json"

        self.write_reviewed_answers(root, answers_path, answers)

        subprocess.run(
            [sys.executable, str(self.script_path("collect_design_profile.py")), str(root), "--answers", str(answers_path), "--write"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        self.init_governed_git_repo(root)
        installed_skill = self.make_installed_skill_fixture(root.parent / f"{root.name}-installed", version=installed_version)

        subprocess.run(
            [sys.executable, str(self.script_path("render_agents.py")), str(root), "--write"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=dict(os.environ, AGENTS_MD_INSTALLED_SKILL_DIR=str(installed_skill)),
        )

        return skill, installed_skill

    def make_release_receipt(self, release_dir: Path, skill_name: str, version: str, validation_level: str = "reduced_assurance") -> None:
        files = []

        for path in sorted(release_dir.rglob("*")):

            if path.is_file() and path.name != "RELEASE_RECEIPT.json":

                files.append(
                    {
                        "path": path.relative_to(release_dir).as_posix(),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )

        (release_dir / "RELEASE_RECEIPT.json").write_text(
            json.dumps(
                {
                    "skill_name": skill_name,
                    "version": version,
                    "source_path": f"skills/{skill_name}",
                    "generated_at": "2026-05-14T18:00:00",
                    "current_branch": "master",
                    "local_branches": ["master", "release"],
                    "worktree_clean": True,
                    "phase_results": {"pre": True, "post": True},
                    "packaging_mode": "standalone-copy",
                    "validation_level": validation_level,
                    "provenance_mode": "repository-dist" if validation_level == "strong" else "external-copy",
                    "sanitization": {
                        "enabled": True,
                        "scope": "broad",
                        "mode": "auto-redact-dist-copy",
                        "files": [],
                        "receipt_required": True,
                    },
                    "files": files,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def write_codex_session_fixture(self, codex_home: Path, cwd: Path, session_id: str, lines: list[tuple[str, str]]) -> Path:
        session_file = codex_home / "sessions" / "2026" / "05" / "13" / f"rollout-{session_id}.jsonl"

        session_file.parent.mkdir(parents=True, exist_ok=True)

        rows: list[dict[str, Any]] = [
            {
                "timestamp": "2026-05-13T10:00:00.000Z",
                "type": "session_meta",
                "payload": {
                    "id": session_id,
                    "timestamp": "2026-05-13T10:00:00.000Z",
                    "cwd": str(cwd),
                    "originator": "Codex Desktop",
                },
            }
        ]

        for role, text in lines:

            rows.append(
                {
                    "timestamp": "2026-05-13T10:00:01.000Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message" if role == "user" else "agent_message",
                        "message": text,
                    },
                }
            )

        session_file.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

        return session_file

    def ai_evolution_review(
        self,
        target: dict[str, Any],
        *,
        verdict: str = "approve",
        approved_target: dict[str, Any] | None = None,
        original_target: dict[str, Any] | None = None,
        session_ids: list[str] | None = None,
        session_paths: list[str] | None = None,
        session_reread_performed: bool = False,
        session_reread_reason: str = "",
        full_explanation: dict[str, str] | None = None,
    ) -> dict[str, Any]:

        return {
            "verdict": verdict,
            "approved_target": approved_target or target,
            "original_target": original_target or target,
            "evidence_read": {
                "conversation_snapshot_paths": [".agents/conversation-snapshots/example-handoff-10.json"],
                "handoff_paths": ["docs/handoff/HANDOFF.md"],
                "docs_paths": ["docs/git_manager/CHANGELOG.md", "docs/development/DEVELOPMENT.md"],
                "release_evidence_paths": [],
                "session_ids": session_ids or [],
                "session_paths": session_paths or [],
            },
            "session_reread_performed": session_reread_performed,
            "session_reread_reason": session_reread_reason,
            "full_explanation": full_explanation
            or {
                "development_flow": "Read repository facts, updated scripts, ran focused tests, and verified docs governance.",
                "design_flow": "Kept deterministic scripts responsible for contracts and blocked template writes until review matched the target.",
                "problem_analysis": "The risk was allowing a plausible summary to evolve templates without matching repository evidence.",
                "classification_rationale": "The approved target matches repository kind, governance vocabulary, and current docs evidence.",
                "release_alignment": "The summary aligns with handoff, changelog, development, and release evidence.",
            },
        }

