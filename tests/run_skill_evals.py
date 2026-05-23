from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
TESTS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TESTS_DIR.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
REPO_ROOT = SKILL_DIR
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

from agents_common import emit_json
from eval_fixtures import EvalFixtures


def run_script(name: str, *args: object, cwd: Path | None = None, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    command_env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", AGENTS_MD_INSTALLED_SKILL_DIR=str(SKILL_DIR))
    if env:
        command_env.update(env)
    import subprocess

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / name), *map(str, args)],
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=command_env,
    )
    return result.returncode, result.stdout, result.stderr


def run_json_script(name: str, *args: object, cwd: Path | None = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    returncode, stdout, stderr = run_script(name, *args, cwd=cwd, env=env)
    if returncode != 0 and not stdout.strip():
        raise RuntimeError(f"{name} failed with {returncode}: {stderr}")
    return json.loads(stdout)


def load_evals(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("evals.json must be an object")
    return data


def pass_count(checks: dict[str, bool]) -> int:
    return sum(1 for value in checks.values() if value)


def build_case_result(
    case: dict[str, Any],
    *,
    with_skill_checks: dict[str, bool],
    without_skill_checks: dict[str, bool],
    with_skill_detail: dict[str, Any],
    without_skill_detail: dict[str, Any],
) -> dict[str, Any]:
    with_count = pass_count(with_skill_checks)
    without_count = pass_count(without_skill_checks)
    improved = with_count > without_count
    passed = all(with_skill_checks.values()) and improved
    return {
        "id": case["id"],
        "kind": case["kind"],
        "patterns": case.get("patterns", []),
        "description": case.get("description", ""),
        "passed": passed,
        "with_skill": {
            **with_skill_detail,
            "expectation_checks": with_skill_checks,
        },
        "without_skill": {
            **without_skill_detail,
            "expectation_checks": without_skill_checks,
        },
        "comparison": {
            "with_skill_pass_count": with_count,
            "without_skill_pass_count": without_count,
            "improved": improved,
        },
    }


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


def case_exact_cwd_evolution_review(case: dict[str, Any], helper: EvalFixtures) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project = root / "workspace"
        codex_home = root / "codex-home"
        matched = helper.write_codex_session_fixture(
            codex_home,
            project,
            "019-review-match",
            [("user", "review the evolution target"), ("assistant", "read exact cwd sessions first")],
        )
        other = helper.write_codex_session_fixture(
            codex_home,
            root / "other-workspace",
            "019-review-other",
            [("user", "wrong workspace"), ("assistant", "ignore this")],
        )
        (project / ".agents").mkdir(parents=True)
        (project / ".agents" / "agents-control.json").write_text(
            json.dumps(
                {
                    "kind": "skill",
                    "name": "demo-skill",
                    "skill_layout": {"path": "skills/agents-md-generator"},
                }
            ),
            encoding="utf-8",
        )
        run_json_script("manage_docs.py", "scaffold", project, cwd=REPO_ROOT)
        for index in range(1, 11):
            handoff_input = project / f"handoff-{index}.json"
            handoff_input.write_text(
                json.dumps({"current_step": f"step {index}", "conversation_summary": f"summary {index}"}),
                encoding="utf-8",
            )
            run_json_script("manage_docs.py", "handoff", project, "--input", handoff_input, cwd=REPO_ROOT)
            if index == 5:
                run_json_script("manage_docs.py", "experience", project, "--payload", helper.ai_experience_payload(project), cwd=REPO_ROOT)

        target = {
            "family": "skill-template",
            "category_path": ["agent-governance"],
            "type_slug": "demo-skill",
            "rationale": "Skill governance target.",
        }
        payload_path = helper.ai_experience_payload(
            project,
            evolution_target=target,
            evolution_review=helper.ai_evolution_review(
                target,
                verdict="reject",
                session_ids=["019-review-match", "019-review-other"],
                session_paths=[matched.as_posix(), other.as_posix()],
                session_reread_performed=True,
                session_reread_reason="classification did not match release-aligned evidence",
            ),
        )
        returncode, stdout, _stderr = run_script(
            "manage_docs.py",
            "experience",
            project,
            "--payload",
            payload_path,
            cwd=REPO_ROOT,
            env={"CODEX_HOME": str(codex_home)},
        )
        request_path = project / ".agents" / "evolution-review-request.json"
        with_checks = {
            "blocked": returncode != 0,
            "exact_cwd_error": "evolution_review session_paths must match exact-cwd Codex sessions only" in stdout,
            "review_request_written": request_path.is_file(),
        }
        without_checks = {
            "blocked": False,
            "exact_cwd_error": False,
            "review_request_written": False,
        }
        return build_case_result(
            case,
            with_skill_checks=with_checks,
            without_skill_checks=without_checks,
            with_skill_detail={"stdout": stdout, "review_request_path": request_path.as_posix()},
            without_skill_detail={"baseline": "unguided baseline would not enforce exact-cwd review evidence before template evolution"},
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
    project = skill_dir.parent
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
            "skills/agents-md-generator/scripts/run_confidence_gate.py": "import argparse\nargparse.ArgumentParser()\n",
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
            (project / rel_path).write_text(text, encoding="utf-8")
        helper.init_basic_git_repo(project)
        helper.git_commit_all(project, "eval: baseline")
        import subprocess

        base = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project, check=True, capture_output=True, text=True).stdout.strip()
        (project / "skills" / "agents-md-generator" / "scripts" / "run_confidence_gate.py").write_text(
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


def case_isolated_eval_runtime_dependency(case: dict[str, Any], _helper: EvalFixtures) -> dict[str, Any]:
    script_text = (SCRIPT_DIR / "run_skill_evals.py").read_text(encoding="utf-8")
    fixture_path = SCRIPT_DIR / "eval_fixtures.py"
    legacy_loader = "def load_test" + "_helper"
    legacy_spec_loader = "spec_from_file" + "_location"
    with_checks = {
        "repo_tests_not_loaded": legacy_loader not in script_text and legacy_spec_loader not in script_text,
        "packaged_fixture_exists": fixture_path.is_file(),
        "packaged_fixture_imported": "from eval_fixtures import EvalFixtures" in script_text,
    }
    without_checks = {
        "repo_tests_not_loaded": False,
        "packaged_fixture_exists": False,
        "packaged_fixture_imported": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={"run_skill_evals": "uses packaged eval_fixtures.py instead of repository tests"},
        without_skill_detail={"baseline": "v0.6.5 imported tests/test_agents_md_scripts.py and failed after packaging or installation"},
    )


def case_code_comment_policy_contract(case: dict[str, Any], _helper: EvalFixtures) -> dict[str, Any]:
    required_snippets = (
        "配置来源：`.agents/global-rule-overrides.json`",
        "默认只允许非显然意图、不变量、风险、生成边界或公共 API 行为注释",
        "禁止未经明确要求的批量 AI 注释",
        "行为变化时必须更新旧注释",
        "Python：公共函数/类使用规范 docstring",
        "C/C++：函数、模块核心功能、变量定义和特定功能说明放在代码上方",
        "Verilog/SystemVerilog：信号声明、参数定义、assign 和 always 块内寄存器赋值使用右侧注释",
    )
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "workspace"
        project.mkdir()
        (project / "src").mkdir()
        (project / "src" / "main.py").write_text("print('demo')\n", encoding="utf-8")
        render_returncode, _render_stdout, render_stderr = run_script("render_agents.py", project, "--write", cwd=REPO_ROOT)
        agents_path = project / "AGENTS.md"
        agents_text = agents_path.read_text(encoding="utf-8", errors="ignore") if agents_path.exists() else ""
        verify = run_json_script("verify_agents.py", project, cwd=REPO_ROOT)
        missing_text = agents_text.replace("## Code Comment Policy", "## Code Comment Policy Removed")
        agents_path.write_text(missing_text, encoding="utf-8")
        missing_returncode, missing_stdout, missing_stderr = run_script("verify_agents.py", project, cwd=REPO_ROOT)
        missing_verify = json.loads(missing_stdout) if missing_stdout.strip() else {"errors": [missing_stderr]}
        agents_path.write_text(agents_text, encoding="utf-8")
        config_path = project / ".agents" / "global-rule-overrides.json"
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        weakened_config = json.loads(json.dumps(config, ensure_ascii=False))
        weakened_config.get("code_comment_policy", {}).pop("python", None)
        config_path.write_text(json.dumps(weakened_config, ensure_ascii=False, indent=2), encoding="utf-8")
        weakened_returncode, weakened_stdout, weakened_stderr = run_script("verify_agents.py", project, cwd=REPO_ROOT)
        weakened_verify = json.loads(weakened_stdout) if weakened_stdout.strip() else {"errors": [weakened_stderr]}
    missing_errors = missing_verify.get("errors", [])
    weakened_errors = weakened_verify.get("errors", [])
    with_checks = {
        "render_succeeded": render_returncode == 0,
        "rendered_policy": "## Code Comment Policy" in agents_text,
        "policy_rules": all(snippet in agents_text for snippet in required_snippets),
        "verify_accepts_policy": verify.get("errors") == [],
        "verify_rejects_missing_policy": bool(missing_errors) and any("Code Comment Policy" in item for item in missing_errors),
        "verify_rejects_weakened_policy": bool(weakened_errors) and any("code_comment_policy" in item for item in weakened_errors),
        "config_written": bool(config.get("code_comment_policy")),
    }
    without_checks = {
        "render_succeeded": False,
        "rendered_policy": False,
        "policy_rules": False,
        "verify_accepts_policy": False,
        "verify_rejects_missing_policy": False,
        "verify_rejects_weakened_policy": False,
        "config_written": False,
    }
    return build_case_result(
        case,
        with_skill_checks=with_checks,
        without_skill_checks=without_checks,
        with_skill_detail={
            "verify": verify,
            "missing_verify": missing_verify,
            "weakened_verify": weakened_verify,
            "render_stderr": render_stderr,
        },
        without_skill_detail={"baseline": "unguided baseline may create AGENTS.md but does not lock comment-generation policy or reject its removal"},
    )


def evaluate_cases(evals: dict[str, Any], *, external_skill_dir: Path | None = None) -> dict[str, Any]:
    helper = EvalFixtures(SCRIPT_DIR)
    handlers = {
        "detect_missing_root_agents": case_missing_root_agents,
        "generator_version_takeover": case_version_mismatch_takeover,
        "root_level_whitelist_gate": case_root_whitelist,
        "exact_cwd_evolution_review": case_exact_cwd_evolution_review,
        "generic_audit_split": case_generic_audit_split,
        "evaluate_failure_classification": case_evaluate_classification,
        "install_release_completeness": case_install_release_completeness,
        "review_governance_companion_checks": case_review_governance_companion_checks,
        "design_review_gate": case_design_review_gate,
        "isolated_eval_runtime_dependency": case_isolated_eval_runtime_dependency,
        "code_comment_policy_contract": case_code_comment_policy_contract,
    }
    cases = evals.get("cases", [])
    if not isinstance(cases, list):
        raise SystemExit("evals.json cases must be a list")
    results: list[dict[str, Any]] = []
    for case in cases:
        handler_name = str(case.get("handler", "")).strip()
        handler = handlers.get(handler_name)
        if handler is None:
            raise SystemExit(f"unknown eval handler: {handler_name}")
        results.append(handler(case, helper))
    if external_skill_dir is not None:
        results.append(
            case_external_generic_health(
                external_skill_dir,
                {
                    "id": "healthy_external_skill_generic_path",
                    "kind": "external_smoke",
                    "patterns": ["Tool Wrapper", "Pipeline"],
                    "description": "A healthy real external skill should pass generic audit/evaluate through the current toolchain.",
                },
            )
        )
    summary = {
        "case_count": len(results),
        "passed_cases": sum(1 for item in results if item["passed"]),
        "improved_cases": sum(1 for item in results if item["comparison"]["improved"]),
        "stable_cases": sum(1 for item in results if item["passed"]),
    }
    summary["ok"] = summary["case_count"] > 0 and summary["passed_cases"] == summary["case_count"]
    return {
        "version": int(evals.get("version", 1)),
        "evals_path": str(evals.get("_path", "")),
        "cases": results,
        "summary": summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repository-local skill effectiveness evaluations.")
    parser.add_argument("evals_path", nargs="?", default=str(SKILL_DIR / "evals" / "evals.json"))
    parser.add_argument("--external-skill-dir", default=None)
    args = parser.parse_args()

    evals_path = Path(args.evals_path).expanduser().resolve()
    evals = load_evals(evals_path)
    evals["_path"] = str(evals_path)
    external_skill_dir = Path(args.external_skill_dir).expanduser().resolve() if args.external_skill_dir else None
    emit_json(evaluate_cases(evals, external_skill_dir=external_skill_dir))


if __name__ == "__main__":
    main()
