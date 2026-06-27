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
import shutil
import subprocess
import sys
import tempfile

# 分隔当前密集代码块，保留原有执行顺序。
from pathlib import Path
from typing import Any

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断

# 保留 SCRIPT DIR 中间值，支撑 模块入口 的当前计算步骤。
SCRIPT_DIR = Path(__file__).resolve().parent  # SCRIPT DIR 用于本步治理判断

SCRIPTS_PYTHON_DIR = Path(__file__).resolve().parents[1]  # SCRIPTS PYTHON DIR 用于本步治理判断

# 保留 SKILL DIR 中间值，支撑 模块入口 的当前计算步骤。
SKILL_DIR = Path(__file__).resolve().parents[3]  # SKILL DIR 用于本步治理判断

# 保留 REPO ROOT 中间值，支撑 模块入口 的当前计算步骤。
REPO_ROOT = Path(__file__).resolve().parents[5]  # REPO ROOT 用于本步治理判断

# 保留 TESTS DIR 中间值，支撑 模块入口 的当前计算步骤。
TESTS_DIR = REPO_ROOT / "tests"  # TESTS DIR 用于本步治理判断

# 共享 CLI helper 位于同一脚本目录，按文件路径执行时可由解释器直接定位。
from agents_common import SCRIPT_TASK_BY_NAME, emit_json, resolve_project


# 保留 PYTHON CACHE SUFFIXES 中间值，支撑 模块入口 的当前计算步骤。
PYTHON_CACHE_SUFFIXES = (".pyc", ".pyo")  # PYTHON CACHE SUFFIXES 用于本步治理判断

EVAL_RUNNER_POLICIES = {"required", "optional", "disabled"}  # EVAL RUNNER POLICIES 用于本步治理判断


def tool_script_path(script_name: str) -> Path:
    """返回当前工具 skill 的分类脚本路径。"""

    task_name = SCRIPT_TASK_BY_NAME[script_name]  # 分类目录名由公共映射统一维护

    return SCRIPTS_PYTHON_DIR / task_name / script_name


# 定义 command_entry 的脚本治理处理入口。
def command_entry(name: str, argv: list[str], cwd: Path, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:

    # 保留 entry 中间值，支撑 command_entry 的当前计算步骤。
    dict_entry: dict[str, Any] = {  # entry 用于本步治理判断
        "name": name,  # entry 用于本步治理判断
        "argv": argv,  # entry 用于本步治理判断
        "cwd": str(cwd),  # entry 用于本步治理判断
        "returncode": result.returncode,  # entry 用于本步治理判断
        "stdout": result.stdout,  # entry 用于本步治理判断
        "stderr": result.stderr,  # entry 用于本步治理判断
    }

    # 保护 command_entry 中允许失败的外部访问。
    try:

        # 保留 中间载荷 中间值，支撑 command_entry 的当前计算步骤。
        dict_entry["json"] = json.loads(result.stdout)  # 中间载荷 用于本步治理判断
    except json.JSONDecodeError:

        # 保留 中间载荷 中间值，支撑 command_entry 的当前计算步骤。
        dict_entry["json"] = None  # 中间载荷 用于本步治理判断

    # 返回 command_entry 已整理完成的调用载荷。
    return dict_entry


# 定义 run_command 的脚本治理处理入口。
def run_command(name: str, argv: list[str], cwd: Path, *, installed_skill_dir: Path | None = None) -> dict[str, Any]:

    # 保留 env 中间值，支撑 run_command 的当前计算步骤。
    governance_runtime_dir = installed_skill_dir or SKILL_DIR  # env 用于本步治理判断

    # 保留 env 中间值，支撑 run_command 的当前计算步骤。
    dict_env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", AGENTS_MD_INSTALLED_SKILL_DIR=str(governance_runtime_dir))  # env 用于本步治理判断

    # 保留 result 中间值，支撑 run_command 的当前计算步骤。
    command_result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False, env=dict_env)  # result 用于本步治理判断

    # 返回 run_command 已整理完成的调用载荷。
    return command_entry(name, argv, cwd, command_result)


def skipped_command_entry(
    name: str,
    argv: list[str],
    cwd: Path,
    reason: str,
    *,
    status: str,
    returncode: int,
    eval_kind: str,
    runner_source: str,
) -> dict[str, Any]:
    """构造未执行命令的门禁记录，保留 runner 和证据完整性线索。"""

    payload: dict[str, Any] = {
        "status": status,
        "skipped": True,
        "reason": reason,
        "eval_kind": eval_kind,
        "runner_available": False,
        "runner_source": runner_source,
    }

    if returncode != 0:
        payload["errors"] = [reason]

    return {
        "name": name,
        "argv": argv,
        "cwd": str(cwd),
        "returncode": returncode,
        "stdout": json.dumps(payload),
        "stderr": "",
        "json": payload,
        "skipped": True,
        "eval_kind": eval_kind,
        "runner_available": False,
        "runner_source": runner_source,
    }


def installed_eval_runner_path(agents_generator_root: Path) -> Path:
    """返回安装态发布包内的正式 eval runner 路径。"""

    return agents_generator_root / "scripts" / "python" / "verify" / "run_skill_evals.py"


def repo_local_eval_runner_path() -> Path:
    """返回源码仓兼容 wrapper 路径。"""

    return TESTS_DIR / "run_skill_evals.py"


def resolve_eval_runner(eval_runner: Path | None, agents_generator_root: Path) -> tuple[Path, str, bool]:
    """按显式路径、安装态 runtime、源码仓 wrapper 的顺序定位 eval runner。"""

    if eval_runner is not None:
        explicit_path = eval_runner.expanduser().resolve()
        return explicit_path, "explicit_path", explicit_path.is_file()

    installed_runner = installed_eval_runner_path(agents_generator_root)
    if installed_runner.is_file():
        return installed_runner, "installed_runtime", True

    repo_runner = repo_local_eval_runner_path()
    if repo_runner.is_file():
        return repo_runner, "repo_local_wrapper", True

    return installed_runner, "missing", False


def run_eval_runner_command(
    name: str,
    argv_tail: list[str],
    cwd: Path,
    *,
    eval_runner_policy: str,
    eval_kind: str,
    eval_runner: Path | None = None,
    installed_skill_dir: Path | None = None,
) -> dict[str, Any]:
    """运行 eval runner，并按策略区分缺失、禁用和真实执行。"""

    agents_generator_root = installed_skill_dir or SKILL_DIR
    if eval_runner_policy not in EVAL_RUNNER_POLICIES:
        raise ValueError(f"unsupported eval runner policy: {eval_runner_policy}")

    runner_path, runner_source, runner_available = resolve_eval_runner(eval_runner, agents_generator_root)
    argv = [sys.executable, str(runner_path), *argv_tail]

    if eval_runner_policy == "disabled":
        return skipped_command_entry(
            name,
            argv,
            cwd,
            "eval runner disabled by user",
            status="disabled_by_user",
            returncode=0,
            eval_kind=eval_kind,
            runner_source="disabled",
        )

    if not runner_available:
        missing_status = "missing_required" if eval_runner_policy == "required" else "missing_optional"
        return skipped_command_entry(
            name,
            argv,
            cwd,
            f"eval runner missing: {runner_path}",
            status=missing_status,
            returncode=1 if eval_runner_policy == "required" else 0,
            eval_kind=eval_kind,
            runner_source="missing",
        )

    entry = run_command(name, argv, cwd, installed_skill_dir=installed_skill_dir)
    entry["eval_kind"] = eval_kind
    entry["runner_available"] = True
    entry["runner_source"] = runner_source
    return entry


# 定义 cleanup_transient_artifacts 的脚本治理处理入口。
def cleanup_transient_artifacts(skill_dir: Path) -> None:

    # 逐项推进 cleanup_transient_artifacts 的候选项检查。
    for path in skill_dir.rglob("__pycache__"):

        # 检查 cleanup_transient_artifacts 的当前条件是否需要进入专门分支。
        if path.is_dir():

            # 调用 rmtree 完成 cleanup_transient_artifacts 的当前动作。
            shutil.rmtree(path, ignore_errors=True)


# 定义 parsed_errors 的脚本治理处理入口。
def parsed_errors(entry: dict[str, Any]) -> list[str]:

    # 保留 parsed 中间值，支撑 parsed_errors 的当前计算步骤。
    parsed = entry.get("json")  # parsed 用于本步治理判断

    # 检查 parsed_errors 的当前条件是否需要进入专门分支。
    if not isinstance(parsed, dict):

        # 返回 parsed_errors 已整理完成的调用载荷。
        return []

    # 返回 parsed_errors 已整理完成的调用载荷。
    return [str(item) for item in (parsed.get("errors") or [])]


# 定义 is_cache_only_audit_failure 的脚本治理处理入口。
def is_cache_only_audit_failure(entry: dict[str, Any]) -> bool:

    # 检查 is_cache_only_audit_failure 的当前条件是否需要进入专门分支。
    if entry.get("name") != "audit_skill":

        # 返回 is_cache_only_audit_failure 已整理完成的调用载荷。
        return False

    # 收集 errors 条目，保持 is_cache_only_audit_failure 的处理顺序稳定。
    list_errors = parsed_errors(entry)  # errors 用于本步治理判断

    # 检查 is_cache_only_audit_failure 的当前条件是否需要进入专门分支。
    if not list_errors:

        # 返回 is_cache_only_audit_failure 已整理完成的调用载荷。
        return False

    # 返回 is_cache_only_audit_failure 已整理完成的调用载荷。
    return all("__pycache__" in item or any(suffix in item for suffix in PYTHON_CACHE_SUFFIXES) for item in list_errors)


# 定义 current_version 的脚本治理处理入口。
def current_version(skill_dir: Path) -> str:

    # 定位 version path 的文件边界，供 current_version 后续读写校验使用。
    version_path = skill_dir / "VERSION"  # version path 用于本步治理判断

    # 返回 current_version 已整理完成的调用载荷。
    return version_path.read_text(encoding="utf-8").strip() if version_path.is_file() else "unknown"


# 定义 confidence_gate 的脚本治理处理入口。
def confidence_gate(
    project: Path,
    skill_dir: Path,
    *,
    evals_path: Path,
    agents_generator_dir: Path | None = None,
    external_skill_dir: Path | None = None,
    review_base: str | None = None,
    eval_runner_policy: str = "required",
    eval_runner: Path | None = None,
    require_eval_runner: bool | None = None,
    deprecation_warnings: list[str] | None = None,
) -> dict[str, Any]:

    # AGENTS 元数据验证必须读取治理生成器版本，而不是目标 skill 版本。
    agents_generator_root = (agents_generator_dir or SKILL_DIR).resolve()

    if require_eval_runner:
        eval_runner_policy = "required"

    if eval_runner_policy not in EVAL_RUNNER_POLICIES:
        raise ValueError(f"unsupported eval runner policy: {eval_runner_policy}")

    # 保留 version 中间值，支撑 confidence_gate 的当前计算步骤。
    str_version = current_version(skill_dir)  # version 用于本步治理判断

    def run_gate_command(name: str, argv: list[str], cwd: Path = project) -> dict[str, Any]:
        """使用同一个 AGENTS 治理运行时执行 confidence gate 子命令。"""

        return run_command(name, argv, cwd, installed_skill_dir=agents_generator_root)

    # 检查 confidence_gate 的当前条件是否需要进入专门分支。
    if not review_base:

        # 返回 confidence_gate 已整理完成的调用载荷。
        return {
            "ok": False,
            "project": str(project),
            "skill_dir": str(skill_dir),
            "version": str_version,
            "commands": [],
            "errors": ["review_base is required for automated review governance; pass --review-base <sha>"],
        }

    # 保留 skill dir arg 中间值，支撑 confidence_gate 的当前计算步骤。
    skill_dir_arg = skill_dir.relative_to(project).as_posix() if skill_dir.is_relative_to(project) else str(skill_dir)  # skill dir arg 用于本步治理判断

    # 调用 cleanup_transient_artifacts 完成 confidence_gate 的当前动作。
    cleanup_transient_artifacts(skill_dir)

    # 检查 confidence_gate 的当前条件是否需要进入专门分支。
    if external_skill_dir is not None:

        # 调用 cleanup_transient_artifacts 完成 confidence_gate 的当前动作。
        cleanup_transient_artifacts(external_skill_dir)

    # 定义 run_audit 的脚本治理处理入口。
    def run_audit() -> dict[str, Any]:

        # 返回 run_audit 已整理完成的调用载荷。
        return run_gate_command("audit_skill", [sys.executable, str(tool_script_path("audit_skill.py")), str(skill_dir)])

    # 保留 audit entry 中间值，支撑 confidence_gate 的当前计算步骤。
    dict_audit_entry = run_audit()  # audit entry 用于本步治理判断

    # 检查 confidence_gate 的当前条件是否需要进入专门分支。
    if is_cache_only_audit_failure(dict_audit_entry):

        # 调用 cleanup_transient_artifacts 完成 confidence_gate 的当前动作。
        cleanup_transient_artifacts(skill_dir)

        # 保留 audit entry 中间值，支撑 confidence_gate 的当前计算步骤。
        dict_audit_entry = run_audit()  # audit entry 用于本步治理判断

    # 收集 commands 条目，保持 confidence_gate 的处理顺序稳定。
    list_commands = [  # commands 用于本步治理判断
        dict_audit_entry,  # commands 用于本步治理判断
        run_gate_command("quick_validate", [sys.executable, str(tool_script_path("quick_validate.py")), str(skill_dir)]),  # commands 用于本步治理判断
        run_gate_command("manage_docs_verify", [sys.executable, str(tool_script_path("manage_docs.py")), "verify", str(project)]),  # commands 用于本步治理判断
        run_gate_command(  # commands 用于本步治理判断
            "verify_agents",  # commands 用于本步治理判断
            [sys.executable, str(tool_script_path("verify_agents.py")), str(project), "--installed-skill-dir", str(agents_generator_root)],  # commands 用于本步治理判断
        ),  # commands 用于本步治理判断
        run_gate_command("source_governance", [sys.executable, str(tool_script_path("check_source_governance.py")), str(project)]),  # commands 用于本步治理判断
        run_gate_command("evaluate_skill", [sys.executable, str(tool_script_path("evaluate_skill.py")), str(skill_dir), str(project)]),  # commands 用于本步治理判断
        run_eval_runner_command(  # commands 用于本步治理判断
            "run_skill_evals",
            [str(evals_path)],
            project,
            eval_runner_policy=eval_runner_policy,
            eval_kind="skill_effectiveness_eval",
            eval_runner=eval_runner,
            installed_skill_dir=agents_generator_root,
        ),
        run_gate_command(  # commands 用于本步治理判断
            "work_folder_gate",  # commands 用于本步治理判断
            [sys.executable, str(tool_script_path("manage_docs.py")), "work-folder-gate", str(project), "--skill-dir", skill_dir_arg, "--mode", "release"],  # commands 用于本步治理判断
        ),  # commands 用于本步治理判断
        run_gate_command("check_freshness", [sys.executable, str(tool_script_path("check_freshness.py")), str(project)]),  # commands 用于本步治理判断
        run_gate_command(  # commands 用于本步治理判断
            "review_governance",  # commands 用于本步治理判断
            [  # commands 用于本步治理判断
                sys.executable,  # commands 用于本步治理判断
                str(tool_script_path("review_governance.py")),  # commands 用于本步治理判断
                str(project),  # commands 用于本步治理判断
                "--base",  # commands 用于本步治理判断
                review_base,  # commands 用于本步治理判断
                "--head",  # commands 用于本步治理判断
                "HEAD",  # commands 用于本步治理判断
                "--skill-dir",  # commands 用于本步治理判断
                skill_dir_arg,  # commands 用于本步治理判断
                "--mode",  # commands 用于本步治理判断
                "all",  # commands 用于本步治理判断
            ],  # commands 用于本步治理判断
        ),  # commands 用于本步治理判断
        run_gate_command("branch_gate", [sys.executable, str(tool_script_path("manage_docs.py")), "branch-gate", str(project)]),  # commands 用于本步治理判断
        run_gate_command(  # commands 用于本步治理判断
            "release_gate_pre",  # commands 用于本步治理判断
            [
                sys.executable,  # 命令参数成员
                str(tool_script_path("manage_docs.py")),  # 命令参数成员
                "release-gate",  # 命令参数成员
                str(project),  # 命令参数成员
                "--version",  # 命令参数成员
                str_version,  # 命令参数成员
                "--skill-dir",  # 命令参数成员
                skill_dir_arg,  # 命令参数成员
                "--phase",  # 命令参数成员
                "pre",  # 命令参数成员
                "--install-intent",  # 命令参数成员
                "requested",  # 命令参数成员
            ],  # commands 用于本步治理判断
        ),  # commands 用于本步治理判断
        run_gate_command(  # commands 用于本步治理判断
            "release_gate_post",  # commands 用于本步治理判断
            [
                sys.executable,  # 命令参数成员
                str(tool_script_path("manage_docs.py")),  # 命令参数成员
                "release-gate",  # 命令参数成员
                str(project),  # 命令参数成员
                "--version",  # 命令参数成员
                str_version,  # 命令参数成员
                "--skill-dir",  # 命令参数成员
                skill_dir_arg,  # 命令参数成员
                "--phase",  # 命令参数成员
                "post",  # 命令参数成员
                "--install-intent",  # 命令参数成员
                "requested",  # 命令参数成员
            ],  # commands 用于本步治理判断
        ),  # commands 用于本步治理判断
    ]

    # 保留 release dir 中间值，支撑 confidence_gate 的当前计算步骤。
    release_dir = project / "dist" / f"{skill_dir.name}-{str_version}"  # release dir 用于本步治理判断

    # 检查 confidence_gate 的当前条件是否需要进入专门分支。
    if release_dir.is_dir():

        # 调用 append 完成 confidence_gate 的当前动作。
        list_commands.append(
            run_gate_command(
                "install_skip",
                [
                    sys.executable,  # 命令参数成员
                    str(tool_script_path("install_skill.py")),  # 命令参数成员
                    str(release_dir),  # 命令参数成员
                    "--target",  # 命令参数成员
                    "skip",  # 命令参数成员
                    "--install-intent",  # 命令参数成员
                    "requested",  # 命令参数成员
                ],
            )
        )

    # 检查 confidence_gate 的当前条件是否需要进入专门分支。
    if external_skill_dir is not None:

        # 调用 append 完成 confidence_gate 的当前动作。
        list_commands.append(
            run_eval_runner_command(
                "external_skill_eval",
                [
                    str(evals_path),
                    "--external-skill-dir",
                    str(external_skill_dir),
                ],
                project,
                eval_runner_policy=eval_runner_policy,
                eval_kind="external_skill_eval",
                eval_runner=eval_runner,
                installed_skill_dir=agents_generator_root,
            )
        )

    # 收集 errors 条目，保持 confidence_gate 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 收集证据缺口，避免 optional/disabled 被误读为完整绿灯。
    list_incomplete_evidence: list[str] = []  # incomplete evidence 用于本步治理判断

    # 逐项推进 confidence_gate 的候选项检查。
    for entry in list_commands:

        # 保留 name 中间值，支撑 confidence_gate 的当前计算步骤。
        name = entry["name"]  # name 用于本步治理判断

        # 检查 confidence_gate 的当前条件是否需要进入专门分支。
        if entry["returncode"] != 0:

            # 调用 append 完成 confidence_gate 的当前动作。
            list_errors.append(f"{name}: command exited with {entry['returncode']}")

        # 保留 parsed 中间值，支撑 confidence_gate 的当前计算步骤。
        parsed = entry.get("json")  # parsed 用于本步治理判断

        # 检查 confidence_gate 的当前条件是否需要进入专门分支。
        if isinstance(parsed, dict):

            skipped_status = parsed.get("status")

            if entry.get("skipped") and skipped_status in {"missing_optional", "disabled_by_user"}:

                list_incomplete_evidence.append(f"{name}: {parsed.get('reason', skipped_status)}")

                # 分隔 confidence_gate 的控制流边界。
                continue

            if entry.get("skipped") and skipped_status == "missing_required":

                list_incomplete_evidence.append(f"{name}: {parsed.get('reason', skipped_status)}")

            if entry.get("skipped") and parsed.get("errors"):

                # 调用 extend 完成 confidence_gate 的当前动作。
                list_errors.extend(f"{name}: {item}" for item in parsed.get("errors", []))

            # 检查 confidence_gate 的当前条件是否需要进入专门分支。
            if name in {"branch_gate"} and parsed.get("approved") is False:

                # 调用 extend 完成 confidence_gate 的当前动作。
                list_errors.extend(f"{name}: {item}" for item in parsed.get("reasons", []))

            # 检查 confidence_gate 的当前条件是否需要进入专门分支。
            if name in {"release_gate_pre", "release_gate_post"} and parsed.get("errors"):

                # 调用 extend 完成 confidence_gate 的当前动作。
                list_errors.extend(f"{name}: {item}" for item in parsed.get("errors", []))

            # 检查 confidence_gate 的当前条件是否需要进入专门分支。
            if name in {"audit_skill", "manage_docs_verify", "verify_agents", "source_governance", "evaluate_skill"} and parsed.get("errors"):

                # 调用 extend 完成 confidence_gate 的当前动作。
                list_errors.extend(f"{name}: {item}" for item in parsed.get("errors", []))

            # 检查 confidence_gate 的当前条件是否需要进入专门分支。
            if name == "source_governance":

                # 逐项推进 confidence_gate 的候选项检查。
                for item in parsed.get("oversized_source_files", []):

                    # 调用 append 完成 confidence_gate 的当前动作。
                    list_errors.append(f"{name}: oversized file {item.get('path', '')}")

                # 逐项推进 confidence_gate 的候选项检查。
                for item in parsed.get("test_code_boundary_violations", []):

                    # 调用 append 完成 confidence_gate 的当前动作。
                    list_errors.append(f"{name}: test-only design code outside tests {item.get('path', '')}")

                # 逐项推进 confidence_gate 的候选项检查。
                for item in parsed.get("comment_policy_violations", []):

                    # 调用 append 完成 confidence_gate 的当前动作。
                    list_errors.append(f"{name}: comment policy violation {item.get('path', '')}: {item.get('message', '')}")

                # 逐项推进 confidence_gate 的候选项检查。
                for item in parsed.get("readability_violations", []):

                    # 调用 append 完成 confidence_gate 的当前动作。
                    list_errors.append(f"{name}: readability violation {item.get('path', '')}: {item.get('message', '')}")

            # 检查 confidence_gate 的当前条件是否需要进入专门分支。
            if name == "work_folder_gate" and parsed.get("ok") is False:

                # 调用 extend 完成 confidence_gate 的当前动作。
                list_errors.extend(f"{name}: {item}" for item in parsed.get("errors", []))

            # 检查 confidence_gate 的当前条件是否需要进入专门分支。
            if name == "check_freshness" and parsed.get("stale") is True:

                # 调用 append 完成 confidence_gate 的当前动作。
                list_errors.append("check_freshness: AGENTS.md freshness check is stale")

            # 检查 confidence_gate 的当前条件是否需要进入专门分支。
            if name == "review_governance" and parsed.get("ok") is False:

                # 逐项推进 confidence_gate 的候选项检查。
                for item in parsed.get("findings", []):

                    # 检查 confidence_gate 的当前条件是否需要进入专门分支。
                    if isinstance(item, dict):

                        # 调用 append 完成 confidence_gate 的当前动作。
                        list_errors.append(f"review_governance: {item.get('code', 'finding')}: {item.get('message', '')}")

            # 检查 confidence_gate 的当前条件是否需要进入专门分支。
            if name == "run_skill_evals" and parsed.get("summary", {}).get("ok") is not True:

                # 调用 append 完成 confidence_gate 的当前动作。
                list_errors.append(f"{name}: skill-effectiveness cases are not all green")

            # 检查 confidence_gate 的当前条件是否需要进入专门分支。
            if name == "install_skip" and parsed.get("errors"):

                # 调用 extend 完成 confidence_gate 的当前动作。
                list_errors.extend(f"{name}: {item}" for item in parsed.get("errors", []))

            # 检查 confidence_gate 的当前条件是否需要进入专门分支。
            if name == "external_skill_eval" and parsed.get("summary", {}).get("ok") is not True:

                # 调用 append 完成 confidence_gate 的当前动作。
                list_errors.append("external_skill_eval: external skill evaluation case is not green")

    # 返回 confidence_gate 已整理完成的调用载荷。
    return {
        "ok": not list_errors,
        "project": str(project),
        "skill_dir": str(skill_dir),
        "agents_generator_dir": str(agents_generator_root),
        "version": str_version,
        "evidence_complete": not list_incomplete_evidence,
        "incomplete_evidence": list_incomplete_evidence,
        "eval_runner_policy": eval_runner_policy,
        "deprecation_warnings": deprecation_warnings or [],
        "commands": list_commands,
        "errors": list_errors,
    }


# 定义 main 的脚本治理处理入口。
def main() -> None:

    # 保留 parser 中间值，支撑 main 的当前计算步骤。
    parser = argparse.ArgumentParser(description="Run the repository-local confidence gate for agents-md-generator.")  # parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--skill-dir", default=str(SKILL_DIR))

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--evals-path", default=str(SKILL_DIR / "evals" / "evals.json"))

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--agents-generator-dir", default=str(SKILL_DIR))

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--external-skill-dir", default=None)

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--review-base", default=None)

    parser.add_argument("--eval-runner-policy", choices=sorted(EVAL_RUNNER_POLICIES), default="required")

    parser.add_argument("--eval-runner", default=None)

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--skip-missing-eval-runner", action="store_true")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--require-eval-runner", action="store_true")

    # 收集 args 条目，保持 main 的处理顺序稳定。
    args = parser.parse_args()  # args 用于本步治理判断

    if args.skip_missing_eval_runner and args.require_eval_runner:

        # 抛出 main 已确认的阻断原因。
        parser.error("--skip-missing-eval-runner and --require-eval-runner are mutually exclusive")

    eval_runner_policy = args.eval_runner_policy
    deprecation_warnings: list[str] = []
    if args.skip_missing_eval_runner:
        eval_runner_policy = "optional"
        deprecation_warnings.append("--skip-missing-eval-runner is deprecated; use --eval-runner-policy optional")
    if args.require_eval_runner:
        eval_runner_policy = "required"
        deprecation_warnings.append("--require-eval-runner is deprecated; use --eval-runner-policy required")

    # 保留 project 中间值，支撑 main 的当前计算步骤。
    project = resolve_project(args.project)  # project 用于本步治理判断

    # 保留 skill dir 中间值，支撑 main 的当前计算步骤。
    skill_dir = resolve_project(args.skill_dir)  # skill dir 用于本步治理判断

    # 保留 agents generator dir 中间值，支撑 main 的当前计算步骤。
    agents_generator_dir = resolve_project(args.agents_generator_dir)  # agents generator dir 用于本步治理判断

    # 定位 evals path 的文件边界，供 main 后续读写校验使用。
    evals_path = Path(args.evals_path).expanduser().resolve()  # evals path 用于本步治理判断

    eval_runner = Path(args.eval_runner).expanduser().resolve() if args.eval_runner else None

    # 保留 external skill dir 中间值，支撑 main 的当前计算步骤。
    external_skill_dir = Path(args.external_skill_dir).expanduser().resolve() if args.external_skill_dir else None  # external skill dir 用于本步治理判断

    # 调用 emit_json 完成 main 的当前动作。
    emit_json(
        confidence_gate(
            project,
            skill_dir,
            evals_path=evals_path,
            agents_generator_dir=agents_generator_dir,
            external_skill_dir=external_skill_dir,
            review_base=args.review_base,
            eval_runner_policy=eval_runner_policy,
            eval_runner=eval_runner,
            require_eval_runner=args.require_eval_runner,
            deprecation_warnings=deprecation_warnings,
        )
    )


# 检查 模块入口 的当前条件是否需要进入专门分支。
if __name__ == "__main__":

    # 调用 main 完成 模块入口 的当前动作。
    main()


