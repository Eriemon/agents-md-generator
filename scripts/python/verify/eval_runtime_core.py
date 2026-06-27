"""执行 agents-md-generator 的评估用例并汇总技能对比结果。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True
SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPTS_PYTHON_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = SCRIPTS_PYTHON_DIR.parent
SKILL_DIR = SCRIPTS_DIR.parent
REPO_ROOT = Path.cwd().resolve()
for task_dir in sorted(SCRIPTS_PYTHON_DIR.iterdir()):
    if task_dir.is_dir():
        sys.path.insert(0, str(task_dir))

from agents_common import emit_json
from eval_runtime_fixtures import EvalFixtures

SCRIPT_TASK_BY_NAME = {
    script_name: task_name
    for task_name, script_names in {
        "detect": [
            "inspect_project.py",
            "detect_scopes.py",
            "extract_commands.py",
            "extract_context.py",
            "check_freshness.py",
            "codex_token_usage_review.py",
            "task_rating_gate.py",
        ],
        "design": [
            "collect_design_profile.py",
            "design_questions.py",
            "design_profile_builder.py",
            "design_profile_contracts.py",
            "design_remote_gate.py",
            "design_review_gate.py",
            "design_takeover.py",
            "design_interview_state.py",
            "design_interview_payload.py",
        ],
        "render": ["render_agents.py", "create_agent_shims.py"],
        "docs": [
            "manage_docs.py",
            "manage_docs_shared.py",
            "manage_docs_memory.py",
            "manage_docs_release.py",
            "manage_docs_scaffold_session.py",
            "manage_docs_sync_verify.py",
        ],
        "dirs": ["manage_dirs.py", "manage_dirs_state.py", "manage_dirs_review.py", "manage_dirs_remote.py"],
        "verify": [
            "quick_validate.py",
            "audit_skill.py",
            "verify_agents.py",
            "verify_agents_policy.py",
            "evaluate_skill.py",
            "check_source_governance.py",
            "source_governance.py",
            "source_governance_config.py",
            "review_governance.py",
            "run_confidence_gate.py",
            "run_skill_evals.py",
            "eval_runtime_core.py",
            "eval_runtime_foundation_cases.py",
            "eval_runtime_policy_cases.py",
            "eval_runtime_fixtures.py",
        ],
        "release": ["install_skill.py", "release_content_policy.py", "select_engineering_rules.py"],
        "common": [
            "agents_common.py",
            "agents_decisions.py",
            "agents_project_facts.py",
            "workspace_settings_policy.py",
        ],
    }.items()
    for script_name in script_names
}


def script_path(name: str) -> Path:
    """按脚本文件名返回任务分类后的运行时路径。"""

    return SCRIPTS_PYTHON_DIR / SCRIPT_TASK_BY_NAME[name] / name


def run_script(name: str, *args: object, cwd: Path | None = None, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    """在评估环境中运行技能脚本，返回退出码和标准输出。"""

    command_env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", AGENTS_MD_INSTALLED_SKILL_DIR=str(SKILL_DIR))
    if env:
        command_env.update(env)
    import subprocess

    result = subprocess.run(
        [sys.executable, str(script_path(name)), *map(str, args)],
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=command_env,
    )
    return result.returncode, result.stdout, result.stderr


def run_json_script(name: str, *args: object, cwd: Path | None = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    """运行输出 JSON 的脚本，并在失败时保留 stderr 作为诊断信息。"""

    returncode, stdout, stderr = run_script(name, *args, cwd=cwd, env=env)
    if returncode != 0 and not stdout.strip():
        raise RuntimeError(f"{name} failed with {returncode}: {stderr}")
    return json.loads(stdout)


def load_evals(path: Path) -> dict[str, Any]:
    """读取评估配置文件并校验顶层结构。"""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("evals.json must be an object")
    return data


def pass_count(checks: dict[str, bool]) -> int:
    """统计单个评估用例中通过的布尔检查项数量。"""

    return sum(1 for value in checks.values() if value)


def build_case_result(
    case: dict[str, Any],
    *,
    with_skill_checks: dict[str, bool],
    without_skill_checks: dict[str, bool],
    with_skill_detail: dict[str, Any],
    without_skill_detail: dict[str, Any],
) -> dict[str, Any]:
    """按 with/without 技能对照结果构造统一 eval case 记录。"""

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


