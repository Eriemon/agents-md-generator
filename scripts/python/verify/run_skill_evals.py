"""执行 agents-md-generator 的正式 skill-effectiveness 评估。"""

from __future__ import annotations

# 评估运行时依赖同一 verify 目录下的分片模块。
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from eval_runtime_core import emit_json, load_evals
from eval_runtime_foundation_cases import *  # noqa: F403 - handler table names are imported deliberately.
from eval_runtime_policy_cases import *  # noqa: F403 - handler table names are imported deliberately.


def evaluate_cases(evals: dict[str, object], *, external_skill_dir: Path | None = None) -> dict[str, object]:
    """运行 evals.json 中登记的所有评估用例。"""

    helper = EvalFixtures(SCRIPTS_DIR)
    handlers = {
        "detect_missing_root_agents": case_missing_root_agents,
        "generator_version_takeover": case_version_mismatch_takeover,
        "root_level_whitelist_gate": case_root_whitelist,
        "evolution_removed_contract": case_evolution_removed_contract,
        "experience_removed_contract": case_experience_removed_contract,
        "generic_audit_split": case_generic_audit_split,
        "evaluate_failure_classification": case_evaluate_classification,
        "install_release_completeness": case_install_release_completeness,
        "review_governance_companion_checks": case_review_governance_companion_checks,
        "design_review_gate": case_design_review_gate,
        "source_governance_test_boundary": case_source_governance_test_boundary,
        "source_governance_size_readability_contract": case_source_governance_size_readability_contract,
        "root_version_sync_contract": case_root_version_sync_contract,
        "source_repo_render_version_contract": case_source_repo_render_version_contract,
        "language_skill_routing_contract": case_language_skill_routing_contract,
        "script_output_policy_contract": case_script_output_policy_contract,
        "plan_mode_language_lock_contract": case_plan_mode_language_lock_contract,
        "codex_token_usage_review_contract": case_codex_token_usage_review_contract,
        "governance_runtime_de_vendoring": case_governance_runtime_de_vendoring,
        "installed_runtime_owner_repo_local_commands": case_installed_runtime_owner_repo_local_commands,
        "handoff_naming_gate": case_handoff_naming_gate,
        "workspace_settings_gate": case_workspace_settings_gate,
        "release_content_evals_install_contract": case_release_content_evals_install_contract,
        "release_sanitizer_regex_constant": case_release_sanitizer_regex_constant,
        "root_workspace_artifact_gate": case_root_workspace_artifact_gate,
        "task_rating_gate_contract": case_task_rating_gate_contract,
        "memory_governance_gate": case_memory_governance_gate,
        "governance_cli_entrypoint_smoke": case_governance_cli_entrypoint_smoke,
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
