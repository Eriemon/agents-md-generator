"""agents-md-generator 技能评估用例实现分片一。"""

from __future__ import annotations

from eval_runtime_core import *  # noqa: F403 - eval case shards share the runner context intentionally.

def case_missing_root_agents(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project = root / "workspace"
        project.mkdir()
        installed_skill = helper.make_installed_skill_fixture(root)
        facts = run_json_script(
            "inspect_project.py",
            project,
            cwd=REPO_ROOT,
            env={"AGENTS_MD_INSTALLED_SKILL_DIR": str(installed_skill)},
        )
        with_checks = {
            "trigger_required": facts.get("root_agents_md_trigger_required") is True,
            "rebuild_required": facts.get("root_agents_md_rebuild_required") is True,
            "missing_root_reason": "missing_root_agents_md" in facts.get("root_agents_md_trigger_reasons", []),
        }
        without_checks = {
            "trigger_required": False,
            "rebuild_required": False,
            "missing_root_reason": False,
        }
        return build_case_result(
            case,
            with_skill_checks=with_checks,
            without_skill_checks=without_checks,
            with_skill_detail={"facts": facts},
            without_skill_detail={"baseline": "unguided baseline does not emit trigger or rebuild routing for missing root AGENTS.md"},
        )


def case_version_mismatch_takeover(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project = root / "workspace"
        project.mkdir()
        (project / "src").mkdir()
        (project / "src" / "main.py").write_text("print('demo')\n", encoding="utf-8")
        installed_skill = helper.make_installed_skill_fixture(root, version="v0.6.2")
        (project / "AGENTS.md").write_text(
            "<!-- AGENTS-METADATA: agents_version=v0.6.2; generator_version=v0.6.1; default_language=中文 -->\n# AGENTS.md\n",
            encoding="utf-8",
        )
        facts = run_json_script(
            "inspect_project.py",
            project,
            cwd=REPO_ROOT,
            env={"AGENTS_MD_INSTALLED_SKILL_DIR": str(installed_skill)},
        )
        started = run_json_script(
            "collect_design_profile.py",
            project,
            "--start",
            cwd=REPO_ROOT,
            env={"AGENTS_MD_INSTALLED_SKILL_DIR": str(installed_skill)},
        )
        with_checks = {
            "trigger_required": facts.get("root_agents_md_trigger_required") is True,
            "generator_version_mismatch": "generator_version_mismatch" in facts.get("root_agents_md_trigger_reasons", []),
            "takeover_mode": started.get("mode") == "takeover",
            "takeover_reason": "generator_version_mismatch" in started.get("takeover_trigger_reasons", []),
        }
        without_checks = {
            "trigger_required": False,
            "generator_version_mismatch": False,
            "takeover_mode": False,
            "takeover_reason": False,
        }
        return build_case_result(
            case,
            with_skill_checks=with_checks,
            without_skill_checks=without_checks,
            with_skill_detail={"facts": facts, "start": started},
            without_skill_detail={"baseline": "unguided baseline sees an AGENTS.md file but does not route into compatibility takeover"},
        )


def case_root_whitelist(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        (project / ".agents").mkdir()
        (project / ".agents" / "agents-control.json").write_text(
            json.dumps(
                {
                    "kind": "skill",
                    "name": "demo-skill",
                    "directory_contract": {
                        "primary_project_root": "skills/demo-skill/",
                        "allowed_new_paths": [
                            "skills/demo-skill/",
                            "tests/",
                            "dist/",
                            "docs/",
                            ".agents/",
                            "ref/",
                        ],
                        "enforce_primary_project_root": True,
                        "remote": "not configured",
                    },
                }
            ),
            encoding="utf-8",
        )
        (project / "skills" / "demo-skill").mkdir(parents=True)
        (project / "skills" / "demo-skill" / "SKILL.md").write_text(
            "---\nname: demo-skill\ndescription: Use when testing\n---\n# Demo\n",
            encoding="utf-8",
        )
        (project / "README.md").write_text("# Drift\n", encoding="utf-8")
        gate = run_json_script("manage_dirs.py", "structure-gate", project, cwd=REPO_ROOT)
        facts = run_json_script("inspect_project.py", project, cwd=REPO_ROOT)
        with_checks = {
            "blocked": gate.get("approved") is False,
            "readme_reason": any("README.md" in item for item in gate.get("reasons", [])),
            "confirmation_required": facts.get("structure_fix_confirmation_required") is True,
        }
        without_checks = {
            "blocked": False,
            "readme_reason": False,
            "confirmation_required": False,
        }
        return build_case_result(
            case,
            with_skill_checks=with_checks,
            without_skill_checks=without_checks,
            with_skill_detail={"structure_gate": gate, "facts": facts},
            without_skill_detail={"baseline": "unguided baseline allows root drift because it has no governed whitelist or confirmation gate"},
        )


def case_evolution_removed_contract(case: dict[str, Any], _helper: EvalFixtures) -> dict[str, Any]:
    skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    script_guide = (SKILL_DIR / "references" / "script-guide.md").read_text(encoding="utf-8")
    scenarios = (SKILL_DIR / "references" / "evaluation-scenarios.md").read_text(encoding="utf-8")
    returncode, stdout, stderr = run_script("manage_docs.py", "-h", cwd=REPO_ROOT)
    help_text = stdout + stderr
    with_checks = {
        "cli_removed": "import-evolution" not in help_text and " evolve " not in f" {help_text} ",
        "skill_declares_removal": "v1.0.0" in skill_text and "不再支持" in skill_text,
        "script_guide_declares_removal": "v1.0.0" in script_guide and "不再支持 evolution" in script_guide,
        "scenarios_cover_removal": "Evolution removed" in scenarios,
    }
    without_checks = {
        "cli_removed": False,
        "skill_declares_removal": False,
        "script_guide_declares_removal": False,
        "scenarios_cover_removal": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={"help_returncode": returncode},
        without_skill_detail={"baseline": "older versions still exposed evolution commands and atomic evolution contract docs"},
    )


def case_experience_removed_contract(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project = root / "workspace"
        project.mkdir()
        (project / ".agents").mkdir()
        profile = helper.skill_answers(name="demo-skill")
        (project / ".agents" / "agents-control.json").write_text(json.dumps(profile), encoding="utf-8")

        scaffold = run_json_script("manage_docs.py", "scaffold", project)
        memory_init = run_json_script("manage_docs.py", "memory-init", project, "--confirm-create")
        handoff_results = []
        for index in range(5):
            handoff_input = project / f"handoff-{index}.json"
            handoff_input.write_text(
                json.dumps(
                    {
                        "original_plan": ["exercise v1.1.0 experience removal cadence"],
                        "current_step": [f"handoff {index + 1}"],
                        "resolved": ["memory records handoff without experience governance"],
                        "remaining": ["none"],
                        "next": ["continue validation"],
                        "verification": ["eval handoff loop"],
                    }
                ),
                encoding="utf-8",
            )
            handoff_results.append(run_json_script("manage_docs.py", "handoff", project, "--input", handoff_input))
        verify = run_json_script("manage_docs.py", "verify", project)
        state = json.loads((project / ".agents" / "docs-governance-state.json").read_text(encoding="utf-8"))
        events = (project / "docs" / "memory" / "events.jsonl").read_text(encoding="utf-8")
        legacy_state_keys = {
            "last_experience_at",
            "experience_update_required",
            "experience_request_due_at",
            "last_experience_handoff_count",
            "experience_request_created_at",
        }
        with_checks = {
            "scaffold_succeeds": scaffold.get("errors") == [],
            "scaffold_omits_experience_dir": not (project / "docs" / "experience").exists(),
            "memory_init_succeeds": memory_init.get("errors") == [],
            "fifth_handoff_no_experience_request": not (project / ".agents" / "experience-update-request.json").exists(),
            "state_has_no_experience_fields": not any(key in state for key in legacy_state_keys),
            "verify_passes_without_experience": verify.get("errors") == [],
            "memory_records_handoffs": all(result.get("memory", {}).get("ok") is True for result in handoff_results)
            and sum(1 for line in events.splitlines() if '"kind": "handoff"' in line or '"kind":"handoff"' in line) >= 5,
        }
        with_detail = {
            "scaffold": scaffold,
            "memory_init": memory_init,
            "fifth_handoff": handoff_results[-1],
            "verify": verify,
            "state_keys": sorted(state.keys()),
        }
    without_checks = {
        "scaffold_succeeds": True,
        "scaffold_omits_experience_dir": False,
        "memory_init_succeeds": False,
        "fifth_handoff_no_experience_request": False,
        "state_has_no_experience_fields": False,
        "verify_passes_without_experience": False,
        "memory_records_handoffs": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail=with_detail,
        without_skill_detail={
            "baseline": "older experience governance scaffolded docs/experience and produced cadence requests around the fifth handoff instead of relying only on memory",
        },
    )


def case_generic_audit_split(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        skill = Path(tmp) / "demo-skill"
        (skill / "scripts").mkdir(parents=True)
        (skill / "agents").mkdir()
        (skill / "SKILL.md").write_text(
            "\n".join(
                [
                    "---",
                    "name: demo-skill",
                    "description: Use when testing generic skill audit behavior",
                    "---",
                    "# Demo Skill",
                    "",
                    "Use `scripts/validate_demo_skill.py` and `agents/openai.yaml`.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (skill / "README.md").write_text("# Demo Skill\n", encoding="utf-8")
        (skill / "agents" / "openai.yaml").write_text("interface:\n  default_prompt: placeholder\n", encoding="utf-8")
        (skill / "scripts" / "validate_demo_skill.py").write_text("print('ok')\n", encoding="utf-8")
        audit = run_json_script("audit_skill.py", skill, cwd=REPO_ROOT)
        with_checks = {
            "errors_empty": audit.get("errors") == [],
            "warnings_empty": audit.get("warnings") == [],
            "generic_script_checked": "scripts/validate_demo_skill.py" in audit.get("checked", []),
        }
        without_checks = {
            "errors_empty": False,
            "warnings_empty": False,
            "generic_script_checked": False,
        }
        return build_case_result(
            case,
            with_skill_checks=with_checks,
            without_skill_checks=without_checks,
            with_skill_detail={"audit": audit},
            without_skill_detail={"baseline": "legacy self-only audit would reject generic skills for missing agents-md-generator private files and contracts"},
        )


def case_evaluate_classification(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        skill = root / "skills" / "demo-skill"
        skill.mkdir(parents=True)
        (skill / "scripts").mkdir()
        (skill / "config").mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: demo-skill\ndescription: Use when testing evaluate classification\n---\n# Demo\n\nUse `scripts/validate_demo_skill.py` and `config/defaults.json`.\n",
            encoding="utf-8",
        )
        (skill / "config" / "defaults.json").write_text('{"mode":"demo"}\n', encoding="utf-8")
        (skill / "scripts" / "validate_demo_skill.py").write_text(
            "raise SystemExit('expected validation failure')\n",
            encoding="utf-8",
        )
        result = run_json_script("evaluate_skill.py", skill, root, cwd=REPO_ROOT)
        classifications = result.get("classified_errors", [])
        with_checks = {
            "evaluate_not_ok": result.get("ok") is False,
            "behavior_category_count": int(result.get("category_counts", {}).get("target_repo_behavior_error", 0)) > 0,
            "validate_classified": any(
                item.get("category") == "target_repo_behavior_error" and item.get("command") == "validate_script"
                for item in classifications
            ),
        }
        without_checks = {
            "evaluate_not_ok": True,
            "behavior_category_count": False,
            "validate_classified": False,
        }
        return build_case_result(
            case,
            with_skill_checks=with_checks,
            without_skill_checks=without_checks,
            with_skill_detail={"evaluate": result},
            without_skill_detail={"baseline": "older evaluate output reported flat errors without machine-readable behavior classification"},
        )


def case_install_release_completeness(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        release_dir = root / "export" / "demo-skill-v0.4.3"
        (release_dir / "config").mkdir(parents=True)
        (release_dir / "scripts").mkdir(parents=True)
        (release_dir / "SKILL.md").write_text(
            "\n".join(
                [
                    "---",
                    "name: demo-skill",
                    "description: Use when testing release completeness",
                    "---",
                    "# Demo Skill",
                    "",
                    "Use `config/defaults.json` during validation.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (release_dir / "scripts" / "validate_demo_skill.py").write_text("print('ok')\n", encoding="utf-8")
        helper.make_release_receipt(release_dir, "demo-skill", "v0.4.3", validation_level="reduced_assurance")
        returncode, stdout, stderr = run_script("install_skill.py", release_dir, "--target", "skip", cwd=REPO_ROOT)
        combined = stdout + stderr
        with_checks = {
            "install_blocked": returncode != 0,
            "missing_reference_reported": "config/defaults.json" in combined,
        }
        without_checks = {
            "install_blocked": False,
            "missing_reference_reported": False,
        }
        return build_case_result(
            case,
            with_skill_checks=with_checks,
            without_skill_checks=without_checks,
            with_skill_detail={"stdout": stdout, "stderr": stderr},
            without_skill_detail={"baseline": "pre-completeness install validation only confirmed receipt shape and could miss SKILL.md referenced content gaps"},
        )


def case_external_generic_health(skill_dir: Path, case: dict[str, Any]) -> dict[str, Any]:
    project = skill_dir
    audit = run_json_script("audit_skill.py", skill_dir, cwd=REPO_ROOT)
    evaluate = run_json_script("evaluate_skill.py", skill_dir, project, cwd=REPO_ROOT)
    with_checks = {
        "audit_green": audit.get("errors") == [],
        "evaluate_green": evaluate.get("ok") is True,
    }
    without_checks = {
        "audit_green": False,
        "evaluate_green": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={"audit": audit, "evaluate": evaluate},
        without_skill_detail={"baseline": "no external-skill confidence evidence"},
    )


def case_review_governance_companion_checks(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        (project / "skills" / "agents-md-generator" / "scripts").mkdir(parents=True)
        (project / "skills" / "agents-md-generator" / "references").mkdir(parents=True)
        (project / "skills" / "agents-md-generator" / "evals").mkdir(parents=True)
        (project / "tests").mkdir()
        (project / "docs" / "git_manager").mkdir(parents=True)
        (project / "docs" / "development").mkdir(parents=True)
        files = {
            "skills/agents-md-generator/scripts/python/verify/run_confidence_gate.py": "import argparse\nargparse.ArgumentParser()\n",
            "skills/agents-md-generator/VERSION": "v0.6.3\n",
            "skills/agents-md-generator/references/script-guide.md": "# Script Guide\n",
            "skills/agents-md-generator/references/review-checklist.md": "# Review Checklist\n",
            "skills/agents-md-generator/references/evaluation-scenarios.md": "# Evaluation Scenarios\n",
            "skills/agents-md-generator/evals/evals.json": '{"version": 1, "cases": []}\n',
            "tests/test_agents_md_scripts.py": "# tests\n",
            "docs/git_manager/CHANGELOG.md": "# Change Log\n- Version: v0.6.3\n",
            "docs/git_manager/GIT_MANAGER.md": "# Git Manager\n## Current Version\n- Active version for this release: `v0.6.3`.\n",
            "docs/development/DEVELOPMENT.md": "# Development\n- Version: v0.6.3\n",
        }
        for rel_path, text in files.items():
            (project / rel_path).parent.mkdir(parents=True, exist_ok=True)
            (project / rel_path).write_text(text, encoding="utf-8")
        helper.init_basic_git_repo(project)
        helper.git_commit_all(project, "eval: baseline")
        import subprocess

        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project, check=True, capture_output=True, text=True).stdout.strip()
        (project / "skills" / "agents-md-generator" / "scripts" / "python" / "verify" / "run_confidence_gate.py").write_text(
            "import argparse\nparser = argparse.ArgumentParser()\nparser.add_argument('--new-gate')\n",
            encoding="utf-8",
        )
        (project / "skills" / "agents-md-generator" / "VERSION").write_text("v0.6.4\n", encoding="utf-8")
        helper.git_commit_all(project, "eval: incomplete gate change")
        review = run_json_script(
            "review_governance.py",
            project,
            "--base",
            base,
            "--head",
            "HEAD",
            "--skill-dir",
            "skills/agents-md-generator",
            "--mode",
            "all",
            cwd=REPO_ROOT,
        )
    codes = {finding.get("code") for finding in review.get("findings", []) if isinstance(finding, dict)}
    with_checks = {
        "review_blocked": review.get("ok") is False,
        "tests_required": "script-change-without-tests" in codes,
        "docs_required": "cli-change-without-script-guide" in codes,
        "evals_required": "gate-change-without-evals" in codes,
        "version_docs_required": "version-change-without-release-docs" in codes,
    }
    without_checks = {
        "review_blocked": False,
        "tests_required": False,
        "docs_required": False,
        "evals_required": False,
        "version_docs_required": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail=review,
        without_skill_detail={"baseline": "unguided review would not deterministically require companion tests, docs, evals, and release docs"},
    )


def case_design_review_gate(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        skill = project / "skills" / "demo-skill"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: demo-skill\ndescription: Use when testing design review gate\n---\n# Demo\n",
            encoding="utf-8",
        )
        answers = helper.skill_answers()
        answers["extra_requirements"] = "none"
        answers_path = project / "answers.json"
        answers_path.write_text(json.dumps(answers), encoding="utf-8")
        blocked_returncode, blocked_stdout, _blocked_stderr = run_script(
            "collect_design_profile.py",
            project,
            "--answers",
            answers_path,
            "--write",
            cwd=REPO_ROOT,
        )
        helper.write_reviewed_answers(project, answers_path, answers)
        approved = run_json_script("collect_design_profile.py", project, "--answers", answers_path, "--write", cwd=REPO_ROOT)
        blocked_errors = json.loads(blocked_stdout).get("errors", []) if blocked_stdout.strip() else []
        with_checks = {
            "unreviewed_write_blocked": blocked_returncode != 0,
            "review_error_reported": "design_review must be provided before --write" in blocked_errors,
            "approved_subagent_write_passed": approved.get("errors") == [],
            "review_persisted": approved.get("profile", {}).get("design_review", {}).get("reviewer_type") == "subagent",
        }
        without_checks = {
            "unreviewed_write_blocked": False,
            "review_error_reported": False,
            "approved_subagent_write_passed": True,
            "review_persisted": False,
        }
        return build_case_result(
            case,
            with_skill_checks=with_checks,
            without_skill_checks=without_checks,
            with_skill_detail={"blocked_errors": blocked_errors, "approved": approved},
            without_skill_detail={"baseline": "old write path accepted aligned answer sets without a final extra-requirements prompt or subagent design-review evidence"},
        )


def case_source_governance_test_boundary(case: dict[str, Any], _helper: EvalFixtures) -> dict[str, Any]:
    runtime_runner = SCRIPT_DIR / "run_skill_evals.py"
    runtime_fixture = SCRIPT_DIR / "eval_runtime_fixtures.py"
    wrapper_runner = REPO_ROOT / "tests" / "run_skill_evals.py"
    legacy_fixture = REPO_ROOT / "tests" / "eval_fixtures.py"
    runtime_text = runtime_runner.read_text(encoding="utf-8")
    core_text = (SCRIPT_DIR / "eval_runtime_core.py").read_text(encoding="utf-8")
    wrapper_text = wrapper_runner.read_text(encoding="utf-8") if wrapper_runner.is_file() else ""
    with_checks = {
        "runtime_runner_exists": runtime_runner.is_file(),
        "runtime_fixture_exists": runtime_fixture.is_file(),
        "tests_wrapper_exists": wrapper_runner.is_file(),
        "legacy_tests_fixture_removed": not legacy_fixture.exists(),
        "runtime_uses_formal_fixture": "eval_runtime_fixtures" in runtime_text or "eval_runtime_fixtures" in core_text,
        "wrapper_delegates_runtime": "RUNTIME_RUNNER_PATH" in wrapper_text,
    }
    without_checks = {
        "runtime_runner_exists": False,
        "runtime_fixture_exists": False,
        "tests_wrapper_exists": False,
        "legacy_tests_fixture_removed": False,
        "runtime_uses_formal_fixture": False,
        "wrapper_delegates_runtime": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={"run_skill_evals": "formal runner lives under scripts/python/verify/; tests/run_skill_evals.py is only a compatibility wrapper"},
        without_skill_detail={"baseline": "older releases kept the real eval runner outside the installable skill runtime or classified it as test-only code"},
    )


def case_source_governance_size_readability_contract(case: dict[str, Any], _helper: EvalFixtures) -> dict[str, Any]:
    def report_for(files: dict[str, str], plans: dict[str, str] | None = None) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for relative, text in files.items():
                path = project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            for relative, text in (plans or {}).items():
                path = project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
            return run_json_script("check_source_governance.py", project, cwd=REPO_ROOT)

    normal = report_for({"src/normal.py": "\n".join(f"VALUE_{index} = {index}" for index in range(40)) + "\n"})
    oversized_text = "".join(f"VALUE_{index} = '{'a' * 120}'\n" for index in range(600))
    oversized = report_for({"src/big.py": oversized_text, "tests/big.py": oversized_text})
    plan = "\n".join(
        [
            "## Current Size",
            "src/big.py exceeds the configured size limit.",
            "## Split Boundaries",
            "Move generated tables into data modules.",
            "## Target Files",
            "src/big_part.py",
            "## Exit Criteria",
            "src/big.py returns below 64KB.",
            "",
        ]
    )
    planned = report_for(
        {"src/big.py": oversized_text},
        {"docs/development/decomposition-plans/src/big.py.md": plan},
    )
    overlong = report_for({"src/long_line.py": f"VALUE = '{'a' * 4100}'\nOTHER = 1\n"})
    compressed = report_for({"src/compressed.js": "var x=1;" + "x=x+1;" * 400 + "\n"})
    dense = report_for({"src/dense.js": "const ok = true;\n" + "{a(),b();}" * 130 + "\n"})
    dense_by_extension_files = {
        "src/dense.js": "const ok = true;\n" + "{a(),b();}" * 130 + "\n",
        "src/dense.css": ".a{" + ";".join(f"--v{index}:{index}" for index in range(170)) + "}\n.short{color:red}\n",
        "src/dense.html": "<main>\n<script>" + "{a(),b();}" * 130 + "</script>\n</main>\n",
        "src/dense.py": "ok = True\nvalues = (" + ",".join("fn()" for _ in range(260)) + ")\n",
        "src/dense.c": "int ok;\nint main(void){" + "a(),b();" * 160 + "return 0;}\n",
        "src/dense.cpp": "int ok;\nint main(){" + "a(),b();" * 160 + "return 0;}\n",
    }
    dense_by_extension = report_for(dense_by_extension_files)
    dense_by_extension_paths = {
        item.get("path")
        for item in dense_by_extension.get("readability_violations", [])
        if "minified or obfuscated dense line" in item.get("message", "")
    }
    oversized_item = (oversized.get("oversized_source_files") or [{}])[0]
    with_checks = {
        "normal_under_64kb_passes": normal.get("ok") is True,
        "oversized_reports_bytes": oversized_item.get("path") == "src/big.py"
        and oversized_item.get("byte_count", 0) > oversized_item.get("max_bytes", 0) == 65536,
        "excluded_tests_skipped": all(item.get("path") != "tests/big.py" for item in oversized.get("oversized_source_files", [])),
        "decomposition_plan_allows_oversize": planned.get("ok") is True,
        "overlong_physical_line_blocked": any(
            "physical line" in item.get("message", "") for item in overlong.get("readability_violations", [])
        ),
        "one_line_compressed_blocked": any(
            "one-line compressed source" in item.get("message", "") for item in compressed.get("readability_violations", [])
        ),
        "minified_dense_line_blocked": any(
            "minified or obfuscated dense line" in item.get("message", "") for item in dense.get("readability_violations", [])
        ),
        "minified_dense_line_requested_styles_blocked": dense_by_extension_paths == set(dense_by_extension_files),
    }
    without_checks = {key: False for key in with_checks}
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={
            "normal": {"ok": normal.get("ok")},
            "oversized": oversized,
            "planned": {"ok": planned.get("ok")},
            "overlong": overlong.get("readability_violations", []),
            "compressed": compressed.get("readability_violations", []),
            "dense": dense.get("readability_violations", []),
            "dense_by_extension": dense_by_extension.get("readability_violations", []),
        },
        without_skill_detail={"baseline": "line-count governance did not measure UTF-8 byte size or block one-line/minified readable-source regressions"},
    )


