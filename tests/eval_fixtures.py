from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path
from typing import Any


class EvalFixtures:
    def __init__(self, scripts_dir: Path | None = None) -> None:
        self.scripts_dir = Path(scripts_dir) if scripts_dir is not None else Path(__file__).resolve().parent.parent / "scripts"

    def remote_directory_answers(
        self,
        remote_directory_structure: str = "remote/workspace/demo-skill",
        include_remote_policy: bool = True,
    ) -> dict[str, Any]:
        answers: dict[str, Any] = {
            "local_directory_structure": "engineering/demo-skill/, tests/, dist/, docs/experience/",
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
        answers: dict[str, Any] = {
            "development_type": "skill",
            "default_conversation_language": "\u4e2d\u6587",
            "use_remote_server": use_remote_server,
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
        answers["local_directory_structure"] = f"skills/{name}/, tests/, dist/, docs/experience/"
        answers["feature_directory_rules"] = "scripts in scripts/, detailed policy in references/"
        return answers

    def load_script_module(self, name: str) -> Any:
        spec = importlib.util.spec_from_file_location(name, self.scripts_dir / name)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"unable to load script module: {name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

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

    def ai_experience_payload(
        self,
        project: Path,
        *,
        evolution_target: dict[str, Any] | None = None,
        include_evolution_summary: bool = True,
        evolution_review: dict[str, Any] | None = None,
    ) -> Path:
        profile: dict[str, Any] = {}
        control = project / ".agents" / "agents-control.json"
        if control.exists():
            profile = json.loads(control.read_text(encoding="utf-8"))
        kind = str(profile.get("kind", "skill")).lower()
        summary_target = evolution_target or {
            "family": "skill-template" if kind == "skill" else "engineering-template",
            "category_path": ["agent-governance"] if kind == "skill" else ["general"],
            "type_slug": str(profile.get("name", "demo")),
            "rationale": "Inferred profile-backed eval target.",
        }
        specs = [
            ("1-workflow.md", "Workflow", "Use evidence-first maintenance: inspect facts, write a failing regression, implement narrowly, and verify before release."),
            ("2-scripts.md", "Scripts", "Deterministic scripts should enforce contracts, expose JSON state, and avoid runtime dependencies on repository-only tests."),
            ("3-plan.md", "Plan", "A useful plan names the old failure, target behavior, public interface changes, and exact verification commands."),
            ("4-design-ui.md", "Design UI", "No UI changes are involved; future UI work should include screenshots, accessibility checks, and responsive behavior."),
            ("5-testing.md", "Testing", "Regression tests should run from isolated fixtures so source-tree adjacency cannot hide package defects."),
            ("6-validation.md", "Validation", "Validation must prove the installable package works after leaving the development repository."),
            ("7-release.md", "Release", "Release gates should package only verified source files and then validate the package independently."),
            ("8-installation.md", "Installation", "Installation remains opt-in and must validate receipts before replacing an existing skill."),
            ("9-docs-governance.md", "Docs Governance", "Handoff and experience evidence must make the current state resumable without reading the original conversation."),
            ("10-directory-governance.md", "Directory Governance", "Directory changes require review before mutation and archives before force-confirmed overrides."),
        ]
        payload: dict[str, Any] = {
            "generated_by": "ai",
            "conversation_sources_read": ["conversation-10", "conversation-9"],
            "experience_files": [
                {
                    "filename": filename,
                    "content": "\n".join(
                        [
                            f"# {title} Experience",
                            "",
                            "## Evidence Read",
                            "- Current handoff, recent handoff history, current experience files, project facts, and release evidence.",
                            "",
                            "## Task Context",
                            f"- This {title.lower()} entry records the implemented behavior, the governance constraint, and the failure mode to avoid.",
                            "",
                            "## How To Apply",
                            f"- Inspect the control profile, reproduce the relevant failure, make the smallest change, and rerun the {title.lower()} verification gate.",
                            "",
                            "## Problems And Risks",
                            f"- The main risk is accepting generic {title.lower()} guidance that cannot guide a maintainer through the same class of work.",
                            "",
                            "## Iterated Lessons",
                            f"- {lesson}",
                            "",
                            "## Next Application",
                            f"- Apply this {title.lower()} lesson when maintaining agents-md-generator package governance.",
                            "",
                        ]
                    ),
                }
                for filename, title, lesson in specs
            ],
            "evolution_target": summary_target,
        }
        if evolution_review is None and include_evolution_summary and summary_target:
            evolution_review = self.ai_evolution_review(summary_target)
        if evolution_review is not None:
            payload["evolution_review"] = evolution_review
        if include_evolution_summary:
            payload["evolution_summary"] = {
                filename: "\n".join(
                    [
                        f"# {title} Evolution Template",
                        "",
                        "## Evidence Sources",
                        "- Current and latest historical experience versions for this topic.",
                        "",
                        "## Applicable Scenario",
                        f"- Use when a future {title.lower()} task matches the same repository governance constraints.",
                        "",
                        "## Distilled Workflow",
                        f"- Inspect evidence, identify the concrete {title.lower()} failure, write a regression check, implement narrowly, verify behavior, and update governance evidence.",
                        "",
                        "## Key Decisions",
                        "- Keep deterministic scripts responsible for validation and AI payloads responsible for synthesis.",
                        "",
                        "## Common Problems",
                        "- Do not paste raw handoff content or mix skill-specific guidance into unrelated templates.",
                        "",
                        "## Non-Reusable Content",
                        "- Omit release timestamps, temporary file paths, and conversation-only details.",
                        "",
                        "## Application Checklist",
                        "- Confirm the template family and category match the target repository.",
                        "- Confirm the source experience passed quality validation.",
                        "",
                    ]
                )
                for filename, title, _lesson in specs[:4]
            }
        path = project / "experience-payload.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
