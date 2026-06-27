from __future__ import annotations

# 分类脚本可从任意任务目录直接执行，这里补齐兄弟任务模块路径。
import sys
from pathlib import Path

_scripts_python_root = Path(__file__).resolve().parents[1]
for _task_dir in _scripts_python_root.iterdir():
    if _task_dir.is_dir():
        _task_path = str(_task_dir)
        if _task_path not in sys.path:
            sys.path.insert(0, _task_path)

# 导入 脚本治理 所需的依赖模块。
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断
from agents_common import emit_json, resolve_project


# 保留 SCRIPT DIR 中间值，支撑 模块入口 的当前计算步骤。
SCRIPT_DIR = Path(__file__).resolve().parent  # SCRIPT DIR 用于本步治理判断

# 保留 DEFAULT SKILL DIR 中间值，支撑 模块入口 的当前计算步骤。
DEFAULT_SKILL_DIR = Path(__file__).resolve().parents[3]  # DEFAULT SKILL DIR 用于本步治理判断

# 保留 GATE SCRIPT NAMES 中间值，支撑 模块入口 的当前计算步骤。
GATE_SCRIPT_NAMES = {  # GATE SCRIPT NAMES 用于本步治理判断
    "check_source_governance.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "check_freshness.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "collect_design_profile.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "design_questions.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "design_review_gate.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "design_interview_state.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "design_profile_builder.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "source_governance.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "source_governance_config.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "render_agents.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "manage_dirs.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "manage_docs.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "manage_docs_release.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "manage_docs_sync_verify.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "review_governance.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "run_confidence_gate.py",  # GATE SCRIPT NAMES 用于本步治理判断
    "verify_agents.py",  # GATE SCRIPT NAMES 用于本步治理判断
}

# 保留 CLI SCRIPT NAMES 中间值，支撑 模块入口 的当前计算步骤。
CLI_SCRIPT_NAMES = GATE_SCRIPT_NAMES | {"install_skill.py"}  # CLI SCRIPT NAMES 用于本步治理判断

# 保留 RUNTIME ROUTING SCRIPT NAMES 中间值，支撑 模块入口 的当前计算步骤。
RUNTIME_ROUTING_SCRIPT_NAMES = {  # RUNTIME ROUTING SCRIPT NAMES 用于本步治理判断
    "agents_common.py",  # RUNTIME ROUTING SCRIPT NAMES 用于本步治理判断
    "agents_project_facts.py",  # RUNTIME ROUTING SCRIPT NAMES 用于本步治理判断
    "design_takeover.py",  # RUNTIME ROUTING SCRIPT NAMES 用于本步治理判断
    "manage_dirs.py",  # RUNTIME ROUTING SCRIPT NAMES 用于本步治理判断
    "manage_docs_scaffold_session.py",  # RUNTIME ROUTING SCRIPT NAMES 用于本步治理判断
    "manage_docs_shared.py",  # RUNTIME ROUTING SCRIPT NAMES 用于本步治理判断
    "manage_docs_sync_verify.py",  # RUNTIME ROUTING SCRIPT NAMES 用于本步治理判断
    "render_agents.py",  # RUNTIME ROUTING SCRIPT NAMES 用于本步治理判断
    "verify_agents.py",  # RUNTIME ROUTING SCRIPT NAMES 用于本步治理判断
}


# 定义 run_git 的脚本治理处理入口。
def run_git(project: Path, args: list[str]) -> subprocess.CompletedProcess[str]:

    # 返回 run_git 已整理完成的调用载荷。
    return subprocess.run(["git", *args], cwd=project, text=True, capture_output=True, check=False)


# 定义 changed_files 的脚本治理处理入口。
def changed_files(project: Path, base: str, head: str) -> list[str]:

    # 保留 result 中间值，支撑 changed_files 的当前计算步骤。
    completed_process_result = run_git(project, ["diff", "--name-only", base, head])  # result 用于本步治理判断

    # 检查 changed_files 的当前条件是否需要进入专门分支。
    if completed_process_result.returncode != 0:

        # git diff 失败时优先保留 stderr，缺失时再使用 stdout。
        diff_output = completed_process_result.stderr.strip() or completed_process_result.stdout.strip()  # git diff 原始诊断

        # 没有任何输出时补充固定文本，保证 JSON errors 非空。
        diff_error = diff_output or "git diff failed"  # git diff 失败诊断文本

        # 抛出 changed_files 已确认的阻断原因。
        raise SystemExit(json.dumps({"ok": False, "errors": [diff_error]}, indent=2))

    # 返回 changed_files 已整理完成的调用载荷。
    return sorted(line.strip().replace("\\", "/") for line in completed_process_result.stdout.splitlines() if line.strip())


# 定义 finding 的脚本治理处理入口。
def finding(code: str, message: str, paths: list[str], severity: str = "error") -> dict[str, Any]:

    # 返回 finding 已整理完成的调用载荷。
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "paths": sorted(paths),
    }


# 定义 review_dispatch_policy 的脚本治理处理入口。
def review_dispatch_policy(mode: str, changes: list[str]) -> str:

    # 检查 review_dispatch_policy 的当前条件是否需要进入专门分支。
    if not changes:

        # 返回 review_dispatch_policy 已整理完成的调用载荷。
        return "none"

    # 检查 review_dispatch_policy 的当前条件是否需要进入专门分支。
    if mode == "release":

        # 返回 review_dispatch_policy 已整理完成的调用载荷。
        return "required_for_release"

    # 返回 review_dispatch_policy 已整理完成的调用载荷。
    return "optional"


# 定义 changed_under 的脚本治理处理入口。
def changed_under(changes: set[str], prefix: str) -> list[str]:

    # 返回 changed_under 已整理完成的调用载荷。
    return sorted(path for path in changes if path.startswith(prefix))


# 定义 script_name 的脚本治理处理入口。
def script_name(path: str) -> str:

    # 返回 script_name 已整理完成的调用载荷。
    return Path(path).name


# 定义 build_findings 的脚本治理处理入口。
def build_findings(changes: list[str], skill_dir_rel: str) -> list[dict[str, Any]]:

    # 保留 changed 中间值，支撑 build_findings 的当前计算步骤。
    set_changed = set(changes)  # changed 用于本步治理判断

    # 保留 script prefix 中间值，支撑 build_findings 的当前计算步骤。
    script_prefix = f"{skill_dir_rel.rstrip('/')}/scripts/"  # script prefix 用于本步治理判断

    # 保留 reference prefix 中间值，支撑 build_findings 的当前计算步骤。
    reference_prefix = f"{skill_dir_rel.rstrip('/')}/references/"  # reference prefix 用于本步治理判断

    # 保留 evals json 中间值，支撑 build_findings 的当前计算步骤。
    evals_json = f"{skill_dir_rel.rstrip('/')}/evals/evals.json"  # evals json 用于本步治理判断

    # 保留 version file 中间值，支撑 build_findings 的当前计算步骤。
    version_file = f"{skill_dir_rel.rstrip('/')}/VERSION"  # version file 用于本步治理判断

    # 收集 script changes 条目，保持 build_findings 的处理顺序稳定。
    script_changes = [path for path in changed_under(set_changed, script_prefix) if path.endswith(".py")]  # script changes 用于本步治理判断

    # 收集 gate changes 条目，保持 build_findings 的处理顺序稳定。
    gate_changes = [path for path in script_changes if script_name(path) in GATE_SCRIPT_NAMES]  # gate changes 用于本步治理判断

    # 收集 cli changes 条目，保持 build_findings 的处理顺序稳定。
    cli_changes = [path for path in script_changes if script_name(path) in CLI_SCRIPT_NAMES]  # cli changes 用于本步治理判断

    # 收集 runtime routing changes 条目，保持 build_findings 的处理顺序稳定。
    runtime_routing_changes = [path for path in script_changes if script_name(path) in RUNTIME_ROUTING_SCRIPT_NAMES]  # runtime routing changes 用于本步治理判断

    # 收集 test changes 条目，保持 build_findings 的处理顺序稳定。
    test_changes = [path for path in set_changed if path.startswith("tests/") and path.endswith(".py")]  # test changes 用于本步治理判断

    # 收集 findings 条目，保持 build_findings 的处理顺序稳定。
    list_findings: list[dict[str, Any]] = []  # findings 用于本步治理判断

    # 检查 build_findings 的当前条件是否需要进入专门分支。
    if script_changes and not test_changes:

        # 调用 append 完成 build_findings 的当前动作。
        list_findings.append(
            finding(
                "script-change-without-tests",
                "Script changes require tests/*.py coverage in the same review span.",
                script_changes,
            )
        )

    # 检查 build_findings 的当前条件是否需要进入专门分支。
    if cli_changes and f"{reference_prefix}script-guide.md" not in set_changed:

        # 调用 append 完成 build_findings 的当前动作。
        list_findings.append(
            finding(
                "cli-change-without-script-guide",
                "CLI or gate script changes require script-guide.md documentation in the same review span.",
                cli_changes,
            )
        )

    # 检查 build_findings 的当前条件是否需要进入专门分支。
    if gate_changes and f"{reference_prefix}review-checklist.md" not in set_changed:

        # 调用 append 完成 build_findings 的当前动作。
        list_findings.append(
            finding(
                "gate-change-without-review-checklist",
                "Gate behavior changes require review-checklist.md coverage in the same review span.",
                gate_changes,
            )
        )

    # 检查 build_findings 的当前条件是否需要进入专门分支。
    if gate_changes and evals_json not in set_changed and f"{reference_prefix}evaluation-scenarios.md" not in set_changed:

        # 调用 append 完成 build_findings 的当前动作。
        list_findings.append(
            finding(
                "gate-change-without-evals",
                "Gate behavior changes require eval or evaluation-scenarios coverage in the same review span.",
                gate_changes,
            )
        )

    # 检查 build_findings 的当前条件是否需要进入专门分支。
    if runtime_routing_changes and evals_json not in set_changed and "tests/run_skill_evals.py" not in set_changed:

        # 调用 append 完成 build_findings 的当前动作。
        list_findings.append(
            finding(
                "runtime-routing-change-without-eval-harness",
                "Governance runtime routing changes require eval coverage in evals/evals.json or tests/run_skill_evals.py.",
                runtime_routing_changes,
            )
        )

    # 检查 build_findings 的当前条件是否需要进入专门分支。
    if version_file in set_changed:

        # 收集 required docs 条目，保持 build_findings 的处理顺序稳定。
        set_required_docs = {  # required docs 用于本步治理判断
            "docs/development/DEVELOPMENT.md",  # required docs 用于本步治理判断
            "docs/git_manager/CHANGELOG.md",  # required docs 用于本步治理判断
            "docs/git_manager/GIT_MANAGER.md",  # required docs 用于本步治理判断
        }

        # 保留 missing 中间值，支撑 build_findings 的当前计算步骤。
        missing = sorted(set_required_docs - set_changed)  # missing 用于本步治理判断

        # 检查 build_findings 的当前条件是否需要进入专门分支。
        if missing:

            # 调用 append 完成 build_findings 的当前动作。
            list_findings.append(
                finding(
                    "version-change-without-release-docs",
                    "VERSION changes require DEVELOPMENT, CHANGELOG, and GIT_MANAGER current-version updates.",
                    [version_file, *missing],
                )
            )

    # 返回 build_findings 已整理完成的调用载荷。
    return list_findings


# 定义 review_request 的脚本治理处理入口。
def review_request(project: Path, base: str, head: str, changes: list[str], findings: list[dict[str, Any]], mode: str) -> dict[str, Any]:

    # 保留 dispatch 中间值，支撑 review_request 的当前计算步骤。
    str_dispatch = review_dispatch_policy(mode, changes)  # dispatch 用于本步治理判断

    # 返回 review_request 已整理完成的调用载荷。
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "base": base,
        "head": head,
        "mode": mode,
        "changed_files": changes,
        "deterministic_findings": findings,
        "review_dispatch_policy": str_dispatch,
        "required_manual_review": str_dispatch == "required_for_release",
        "review_focus": [
            "Confirm the deterministic findings are resolved or intentionally accepted.",
            "Review design consistency for gate semantics, user confirmation wording, and release/install safety.",
            "Review code quality for small focused helpers, stable JSON output, and backwards-compatible fields.",
        ],
    }


# 定义 review_governance 的脚本治理处理入口。
def review_governance(project: Path, base: str, head: str, skill_dir: Path, mode: str, write_request: bool = False) -> dict[str, Any]:

    # 收集 changes 条目，保持 review_governance 的处理顺序稳定。
    list_changes = changed_files(project, base, head)  # changes 用于本步治理判断

    # 保留 skill dir rel 中间值，支撑 review_governance 的当前计算步骤。
    skill_dir_rel = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else skill_dir.as_posix()  # skill dir rel 用于本步治理判断

    # 收集 findings 条目，保持 review_governance 的处理顺序稳定。
    list_findings = build_findings(list_changes, skill_dir_rel)  # findings 用于本步治理判断

    # 保留 dispatch 中间值，支撑 review_governance 的当前计算步骤。
    str_dispatch = review_dispatch_policy(mode, list_changes)  # dispatch 用于本步治理判断

    # 保留 request 中间值，支撑 review_governance 的当前计算步骤。
    dict_request = review_request(project, base, head, list_changes, list_findings, mode)  # request 用于本步治理判断

    # 定位 request path 的文件边界，供 review_governance 后续读写校验使用。
    str_request_path = ""  # request path 用于本步治理判断

    # 检查 review_governance 的当前条件是否需要进入专门分支。
    if write_request:

        # 保留 target 中间值，支撑 review_governance 的当前计算步骤。
        target = project / ".agents" / "review-request.json"  # target 用于本步治理判断

        # 调用 mkdir 完成 review_governance 的当前动作。
        target.parent.mkdir(parents=True, exist_ok=True)

        # 调用 write_text 完成 review_governance 的当前动作。
        target.write_text(json.dumps(dict_request, indent=2, sort_keys=True), encoding="utf-8")

        # 定位 request path 的文件边界，供 review_governance 后续读写校验使用。
        str_request_path = target.relative_to(project).as_posix()  # request path 用于本步治理判断

    # 返回 review_governance 已整理完成的调用载荷。
    return {
        "project": str(project),
        "base": base,
        "head": head,
        "mode": mode,
        "changed_files": list_changes,
        "findings": list_findings,
        "review_dispatch_policy": str_dispatch,
        "required_manual_review": str_dispatch == "required_for_release",
        "ok": not any(item["severity"] == "error" for item in list_findings),
        "review_request": dict_request,
        "review_request_path": str_request_path,
    }


# 定义 main 的脚本治理处理入口。
def main() -> None:

    # 保留 parser 中间值，支撑 main 的当前计算步骤。
    parser = argparse.ArgumentParser(description="Review governance-sensitive code and design changes.")  # parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--base", required=True)

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--head", default="HEAD")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--skill-dir", default=str(DEFAULT_SKILL_DIR))

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--mode", choices=["all", "code", "design", "release"], default="all")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--write-request", action="store_true")

    # 收集 args 条目，保持 main 的处理顺序稳定。
    args = parser.parse_args()  # args 用于本步治理判断

    # 保留 project 中间值，支撑 main 的当前计算步骤。
    project = resolve_project(args.project)  # project 用于本步治理判断

    # 保留 skill dir 中间值，支撑 main 的当前计算步骤。
    path_skill_dir = Path(args.skill_dir)  # skill dir 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if not path_skill_dir.is_absolute():

        # 保留 skill dir 中间值，支撑 main 的当前计算步骤。
        path_skill_dir = project / path_skill_dir  # skill dir 用于本步治理判断

    # 保留 result 中间值，支撑 main 的当前计算步骤。
    dict_result = review_governance(project, args.base, args.head, path_skill_dir.resolve(), args.mode, write_request=args.write_request)  # result 用于本步治理判断

    # 调用 emit_json 完成 main 的当前动作。
    emit_json(dict_result)

    # 检查 main 的当前条件是否需要进入专门分支。
    if not dict_result["ok"]:

        # 抛出 main 已确认的阻断原因。
        raise SystemExit(1)


# 检查 模块入口 的当前条件是否需要进入专门分支。
if __name__ == "__main__":

    # 调用 main 完成 模块入口 的当前动作。
    main()


