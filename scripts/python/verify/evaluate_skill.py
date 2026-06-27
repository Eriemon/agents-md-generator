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
import compileall
import json
import os
import re
import shutil
import subprocess

# 分隔当前密集代码块，保留原有执行顺序。
import sys
from pathlib import Path
from typing import Any

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断
from agents_common import SCRIPT_TASK_BY_NAME, emit_json, resolve_project


# 保留 PLACEHOLDER RE 中间值，支撑 模块入口 的当前计算步骤。
PLACEHOLDER_RE = re.compile(r"{{[A-Z0-9_]+}}")  # PLACEHOLDER RE 用于本步治理判断

# 保留 LOCAL REFERENCE RE 中间值，支撑 模块入口 的当前计算步骤。
LOCAL_REFERENCE_RE = re.compile(r"G:[/\\]html|ref[/\\](agent-rules|html)", flags=re.IGNORECASE)  # LOCAL REFERENCE RE 用于本步治理判断

# 保留 TOOL SKILL DIR 中间值，支撑 模块入口 的当前计算步骤。
TOOL_SKILL_DIR = Path(__file__).resolve().parents[3]  # TOOL SKILL DIR 用于本步治理判断


def tool_script_path(script_name: str) -> Path:
    """返回当前工具 skill 的分类脚本路径。"""

    task_name = SCRIPT_TASK_BY_NAME[script_name]  # 分类目录名由公共映射统一维护

    return TOOL_SKILL_DIR / "scripts" / "python" / task_name / script_name

# 保留 ERROR CATEGORY NAMES 中间值，支撑 模块入口 的当前计算步骤。
ERROR_CATEGORY_NAMES = (  # ERROR CATEGORY NAMES 用于本步治理判断
    "tooling_error",  # ERROR CATEGORY NAMES 用于本步治理判断
    "self_repo_governance_error",  # ERROR CATEGORY NAMES 用于本步治理判断
    "target_repo_governance_error",  # ERROR CATEGORY NAMES 用于本步治理判断
    "target_repo_behavior_error",  # ERROR CATEGORY NAMES 用于本步治理判断
)


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
def run_command(name: str, argv: list[str], cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:

    # 保留 command env 中间值，支撑 run_command 的当前计算步骤。
    command_env = dict(env) if env is not None else dict(os.environ)  # command env 用于本步治理判断

    # 保留 中间载荷 中间值，支撑 run_command 的当前计算步骤。
    command_env["PYTHONDONTWRITEBYTECODE"] = "1"  # 中间载荷 用于本步治理判断

    # 保留 result 中间值，支撑 run_command 的当前计算步骤。
    command_result = subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=False, env=command_env)  # result 用于本步治理判断

    # 返回 run_command 已整理完成的调用载荷。
    return command_entry(name, argv, cwd, command_result)


# 定义 quick_validate_script 的脚本治理处理入口。
def quick_validate_script() -> Path:

    # 收集 candidates 条目，保持 quick_validate_script 的处理顺序稳定。
    list_candidates = [  # candidates 用于本步治理判断
        tool_script_path("quick_validate.py"),  # candidates 用于本步治理判断
        TOOL_SKILL_DIR.parent / ".system" / "skill-creator" / "scripts" / "quick_validate.py",  # candidates 用于本步治理判断
        Path.home() / ".codex" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py",  # candidates 用于本步治理判断
    ]

    # 逐项推进 quick_validate_script 的候选项检查。
    for candidate in list_candidates:

        # 检查 quick_validate_script 的当前条件是否需要进入专门分支。
        if candidate.is_file():

            # 返回 quick_validate_script 已整理完成的调用载荷。
            return candidate

    # 抛出 quick_validate_script 已确认的阻断原因。
    raise FileNotFoundError("quick_validate helper not found in installed skill-creator locations")


# 定义 existing_python_roots 的脚本治理处理入口。
def existing_python_roots(skill_dir: Path) -> list[str]:

    # 收集 roots 条目，保持 existing_python_roots 的处理顺序稳定。
    list_roots: list[str] = []  # roots 用于本步治理判断

    # 逐项推进 existing_python_roots 的候选项检查。
    for name in ("runtime", "integration", "scripts", "tests"):

        # 检查 existing_python_roots 的当前条件是否需要进入专门分支。
        if (skill_dir / name).exists():

            # 调用 append 完成 existing_python_roots 的当前动作。
            list_roots.append(name)

    # 返回 existing_python_roots 已整理完成的调用载荷。
    return list_roots


# 定义 settings_arg 的脚本治理处理入口。
def settings_arg(skill_dir: Path) -> list[str]:

    # 定位 settings path 的文件边界，供 settings_arg 后续读写校验使用。
    settings_path = preferred_settings_path(skill_dir)  # settings path 用于本步治理判断

    # 检查 settings_arg 的当前条件是否需要进入专门分支。
    if settings_path is None:

        # 返回 settings_arg 已整理完成的调用载荷。
        return []

    # 返回 settings_arg 已整理完成的调用载荷。
    return ["--settings", str(settings_path)]


# 定义 preferred_settings_path 的脚本治理处理入口。
def preferred_settings_path(skill_dir: Path) -> Path | None:

    # 逐项推进 preferred_settings_path 的候选项检查。
    for relative in ("assets/defaults.json", "config/defaults.json"):

        # 定位 settings path 的文件边界，供 preferred_settings_path 后续读写校验使用。
        settings_path = skill_dir / relative  # settings path 用于本步治理判断

        # 检查 preferred_settings_path 的当前条件是否需要进入专门分支。
        if settings_path.is_file():

            # 返回 preferred_settings_path 已整理完成的调用载荷。
            return settings_path

    # 返回 preferred_settings_path 已整理完成的调用载荷。
    return None


# 定义 validate_script_env 的脚本治理处理入口。
def validate_script_env(base_env: dict[str, str], skill_dir: Path) -> dict[str, str]:

    # 保留 env 中间值，支撑 validate_script_env 的当前计算步骤。
    dict_env = dict(base_env)  # env 用于本步治理判断

    # 检查 validate_script_env 的当前条件是否需要进入专门分支。
    if skill_dir.name == "erie-remote-ssh":

        # 保留 中间载荷 中间值，支撑 validate_script_env 的当前计算步骤。
        dict_env["ERIE_REMOTE_SSH_SKIP_ISOLATED_VALIDATION"] = "1"  # 中间载荷 用于本步治理判断

    # 返回 validate_script_env 已整理完成的调用载荷。
    return dict_env


# 定义 discover_validate_script 的脚本治理处理入口。
def discover_validate_script(skill_dir: Path) -> Path | None:

    # 保留 scripts dir 中间值，支撑 discover_validate_script 的当前计算步骤。
    scripts_dir = skill_dir / "scripts"  # scripts dir 用于本步治理判断

    # 检查 discover_validate_script 的当前条件是否需要进入专门分支。
    if not scripts_dir.is_dir():

        # 返回 discover_validate_script 已整理完成的调用载荷。
        return None

    # 收集 candidates 条目，保持 discover_validate_script 的处理顺序稳定。
    candidates = sorted(path for path in scripts_dir.glob("validate*.py") if path.name not in {"quick_validate.py"})  # candidates 用于本步治理判断

    # 检查 discover_validate_script 的当前条件是否需要进入专门分支。
    if len(candidates) == 1:

        # 返回 discover_validate_script 已整理完成的调用载荷。
        return candidates[0]

    # 保留 preferred 中间值，支撑 discover_validate_script 的当前计算步骤。
    preferred = scripts_dir / f"validate_{skill_dir.name.replace('-', '_')}.py"  # preferred 用于本步治理判断

    # 检查 discover_validate_script 的当前条件是否需要进入专门分支。
    if preferred in candidates:

        # 返回 discover_validate_script 已整理完成的调用载荷。
        return preferred

    # 返回 discover_validate_script 已整理完成的调用载荷。
    return None


# 定义 cleanup_python_caches 的脚本治理处理入口。
def cleanup_python_caches(skill_dir: Path) -> None:

    # 逐项推进 cleanup_python_caches 的候选项检查。
    for path in skill_dir.rglob("__pycache__"):

        # 检查 cleanup_python_caches 的当前条件是否需要进入专门分支。
        if path.is_dir():

            # 调用 rmtree 完成 cleanup_python_caches 的当前动作。
            shutil.rmtree(path, ignore_errors=True)


# 定义 cleanup_transient_artifacts 的脚本治理处理入口。
def cleanup_transient_artifacts(skill_dir: Path) -> None:

    # 调用 cleanup_python_caches 完成 cleanup_transient_artifacts 的当前动作。
    cleanup_python_caches(skill_dir)


# 定义 render_entry 的脚本治理处理入口。
def render_entry(project: Path, env: dict[str, str] | None = None) -> dict[str, Any]:

    # 保留 argv 中间值，支撑 render_entry 的当前计算步骤。
    list_argv = [sys.executable, str(tool_script_path("render_agents.py")), str(project)]  # argv 用于本步治理判断

    # 保留 command env 中间值，支撑 render_entry 的当前计算步骤。
    command_env = dict(env) if env is not None else dict(os.environ)  # command env 用于本步治理判断

    # 保留 中间载荷 中间值，支撑 render_entry 的当前计算步骤。
    command_env["PYTHONDONTWRITEBYTECODE"] = "1"  # 中间载荷 用于本步治理判断

    # 保留 result 中间值，支撑 render_entry 的当前计算步骤。
    command_result = subprocess.run(  # result 用于本步治理判断
        list_argv,  # result 用于本步治理判断
        cwd=project,  # result 用于本步治理判断
        text=True,  # result 用于本步治理判断
        capture_output=True,  # result 用于本步治理判断
        check=False,  # result 用于本步治理判断
        env=command_env,  # result 用于本步治理判断
    )

    # 保留 entry 中间值，支撑 render_entry 的当前计算步骤。
    dict_entry = command_entry("render_agents", list_argv, project, command_result)  # entry 用于本步治理判断

    # 保留 output 中间值，支撑 render_entry 的当前计算步骤。
    output = command_result.stdout  # output 用于本步治理判断

    # 保留 中间载荷 中间值，支撑 render_entry 的当前计算步骤。
    dict_entry["json"] = {  # 中间载荷 用于本步治理判断
        "unresolved_placeholders": sorted(set(PLACEHOLDER_RE.findall(output))),  # 中间载荷 用于本步治理判断
        "local_reference_leaks": sorted(set(match.group(0) for match in LOCAL_REFERENCE_RE.finditer(output))),  # 中间载荷 用于本步治理判断
    }

    # 返回 render_entry 已整理完成的调用载荷。
    return dict_entry


# 定义 collect_errors 的脚本治理处理入口。
def collect_errors(commands: list[dict[str, Any]]) -> list[str]:

    # 收集 errors 条目，保持 collect_errors 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 逐项推进 collect_errors 的候选项检查。
    for entry in commands:

        # 保留 name 中间值，支撑 collect_errors 的当前计算步骤。
        name = entry["name"]  # name 用于本步治理判断

        # 检查 collect_errors 的当前条件是否需要进入专门分支。
        if entry["returncode"] != 0:

            # 调用 append 完成 collect_errors 的当前动作。
            list_errors.append(f"{name}: command exited with {entry['returncode']}")

        # 保留 parsed 中间值，支撑 collect_errors 的当前计算步骤。
        parsed = entry.get("json")  # parsed 用于本步治理判断

        # 检查 collect_errors 的当前条件是否需要进入专门分支。
        if isinstance(parsed, dict):

            # 逐项推进 collect_errors 的候选项检查。
            for item in parsed.get("errors", []) or []:

                # 调用 append 完成 collect_errors 的当前动作。
                list_errors.append(f"{name}: {item}")

            # 检查 collect_errors 的当前条件是否需要进入专门分支。
            if name == "verify_agents":

                # 逐项推进 collect_errors 的候选项检查。
                for checked in parsed.get("checked_files", []) or []:

                    # 检查 collect_errors 的当前条件是否需要进入专门分支。
                    if str(checked).startswith("ref/"):

                        # 调用 append 完成 collect_errors 的当前动作。
                        list_errors.append(f"verify_agents: checked skipped reference file {checked}")

            # 检查 collect_errors 的当前条件是否需要进入专门分支。
            if name == "render_agents":

                # 逐项推进 collect_errors 的候选项检查。
                for item in parsed.get("unresolved_placeholders", []) or []:

                    # 调用 append 完成 collect_errors 的当前动作。
                    list_errors.append(f"render_agents: unresolved placeholder {item}")

                # 逐项推进 collect_errors 的候选项检查。
                for item in parsed.get("local_reference_leaks", []) or []:

                    # 调用 append 完成 collect_errors 的当前动作。
                    list_errors.append(f"render_agents: local reference leak {item}")

            # 检查 collect_errors 的当前条件是否需要进入专门分支。
            if name == "source_governance":

                # 逐项推进 collect_errors 的候选项检查。
                for item in parsed.get("oversized_source_files", []) or []:

                    # 调用 append 完成 collect_errors 的当前动作。
                    list_errors.append(f"source_governance: oversized file {item.get('path', '')}")

                # 逐项推进 collect_errors 的候选项检查。
                for item in parsed.get("test_code_boundary_violations", []) or []:

                    # 调用 append 完成 collect_errors 的当前动作。
                    list_errors.append(f"source_governance: test-only design code outside tests {item.get('path', '')}")

                # 逐项推进 collect_errors 的候选项检查。
                for item in parsed.get("comment_policy_violations", []) or []:

                    # 调用 append 完成 collect_errors 的当前动作。
                    list_errors.append(f"source_governance: comment policy violation {item.get('path', '')}: {item.get('message', '')}")

                # 逐项推进 collect_errors 的候选项检查。
                for item in parsed.get("readability_violations", []) or []:

                    # 调用 append 完成 collect_errors 的当前动作。
                    list_errors.append(f"source_governance: readability violation {item.get('path', '')}: {item.get('message', '')}")

    # 返回 collect_errors 已整理完成的调用载荷。
    return list_errors


# 定义 error_category_for 的脚本治理处理入口。
def error_category_for(command_name: str, *, self_skill: bool) -> str:

    # 检查 error_category_for 的当前条件是否需要进入专门分支。
    if command_name in {"manage_docs_verify", "verify_agents"}:

        # 返回 error_category_for 已整理完成的调用载荷。
        return "self_repo_governance_error" if self_skill else "target_repo_governance_error"

    # 检查 error_category_for 的当前条件是否需要进入专门分支。
    if command_name in {"source_governance", "validate_script"}:

        # 返回 error_category_for 已整理完成的调用载荷。
        return "target_repo_behavior_error"

    # 检查 error_category_for 的当前条件是否需要进入专门分支。
    if command_name in {"audit_skill", "compileall", "quick_validate"}:

        # 返回 error_category_for 已整理完成的调用载荷。
        return "tooling_error" if self_skill else "target_repo_behavior_error"

    # 返回 error_category_for 已整理完成的调用载荷。
    return "tooling_error"


# 定义 classified_errors 的脚本治理处理入口。
def classified_errors(commands: list[dict[str, Any]], *, self_skill: bool) -> list[dict[str, str]]:

    # 保留 classified 中间值，支撑 classified_errors 的当前计算步骤。
    list_classified: list[dict[str, str]] = []  # classified 用于本步治理判断

    # 逐项推进 classified_errors 的候选项检查。
    for entry in commands:

        # 保留 name 中间值，支撑 classified_errors 的当前计算步骤。
        name = entry["name"]  # name 用于本步治理判断

        # 保留 category 中间值，支撑 classified_errors 的当前计算步骤。
        str_category = error_category_for(name, self_skill=self_skill)  # category 用于本步治理判断

        # 检查 classified_errors 的当前条件是否需要进入专门分支。
        if entry["returncode"] != 0:

            # 调用 append 完成 classified_errors 的当前动作。
            list_classified.append(
                {
                    "category": str_category,
                    "command": name,
                    "message": f"command exited with {entry['returncode']}",
                }
            )

        # 保留 parsed 中间值，支撑 classified_errors 的当前计算步骤。
        parsed = entry.get("json")  # parsed 用于本步治理判断

        # 检查 classified_errors 的当前条件是否需要进入专门分支。
        if isinstance(parsed, dict):

            # 逐项推进 classified_errors 的候选项检查。
            for item in parsed.get("errors", []) or []:

                # 保留 item category 中间值，支撑 classified_errors 的当前计算步骤。
                item_category = str_category  # item category 用于本步治理判断

                # 调用 append 完成 classified_errors 的当前动作。
                list_classified.append(
                    {
                        "category": item_category,
                        "command": name,
                        "message": str(item),
                    }
                )

            # 检查 classified_errors 的当前条件是否需要进入专门分支。
            if name == "verify_agents":

                # 逐项推进 classified_errors 的候选项检查。
                for checked in parsed.get("checked_files", []) or []:

                    # 检查 classified_errors 的当前条件是否需要进入专门分支。
                    if str(checked).startswith("ref/"):

                        # 调用 append 完成 classified_errors 的当前动作。
                        list_classified.append(
                            {
                                "category": "tooling_error",
                                "command": name,
                                "message": f"checked skipped reference file {checked}",
                            }
                        )

            # 检查 classified_errors 的当前条件是否需要进入专门分支。
            if name == "render_agents":

                # 逐项推进 classified_errors 的候选项检查。
                for item in parsed.get("unresolved_placeholders", []) or []:

                    # 调用 append 完成 classified_errors 的当前动作。
                    list_classified.append(
                        {
                            "category": "tooling_error",
                            "command": name,
                            "message": f"unresolved placeholder {item}",
                        }
                    )

                # 逐项推进 classified_errors 的候选项检查。
                for item in parsed.get("local_reference_leaks", []) or []:

                    # 调用 append 完成 classified_errors 的当前动作。
                    list_classified.append(
                        {
                            "category": "tooling_error",
                            "command": name,
                            "message": f"local reference leak {item}",
                        }
                    )

            # 检查 classified_errors 的当前条件是否需要进入专门分支。
            if name == "source_governance":

                # 逐项推进 classified_errors 的候选项检查。
                for item in parsed.get("oversized_source_files", []) or []:

                    # 调用 append 完成 classified_errors 的当前动作。
                    list_classified.append(
                        {
                            "category": str_category,
                            "command": name,
                            "message": f"oversized file {item.get('path', '')}",
                        }
                    )

                # 逐项推进 classified_errors 的候选项检查。
                for item in parsed.get("test_code_boundary_violations", []) or []:

                    # 调用 append 完成 classified_errors 的当前动作。
                    list_classified.append(
                        {
                            "category": str_category,
                            "command": name,
                            "message": f"test-only design code outside tests {item.get('path', '')}",
                        }
                    )

                # 逐项推进 classified_errors 的候选项检查。
                for item in parsed.get("comment_policy_violations", []) or []:

                    # 调用 append 完成 classified_errors 的当前动作。
                    list_classified.append(
                        {
                            "category": str_category,
                            "command": name,
                            "message": f"comment policy violation {item.get('path', '')}: {item.get('message', '')}",
                        }
                    )

                # 逐项推进 classified_errors 的候选项检查。
                for item in parsed.get("readability_violations", []) or []:

                    # 调用 append 完成 classified_errors 的当前动作。
                    list_classified.append(
                        {
                            "category": str_category,
                            "command": name,
                            "message": f"readability violation {item.get('path', '')}: {item.get('message', '')}",
                        }
                    )

    # 返回 classified_errors 已整理完成的调用载荷。
    return list_classified


# 定义 category_counts 的脚本治理处理入口。
def category_counts(classified: list[dict[str, str]]) -> dict[str, int]:

    # 收集 counts 条目，保持 category_counts 的处理顺序稳定。
    counts = {name: 0 for name in ERROR_CATEGORY_NAMES}  # counts 用于本步治理判断

    # 逐项推进 category_counts 的候选项检查。
    for item in classified:

        # 保留 category 中间值，支撑 category_counts 的当前计算步骤。
        category = item.get("category", "")  # category 用于本步治理判断

        # 检查 category_counts 的当前条件是否需要进入专门分支。
        if category in counts:

            # 保留 中间载荷 中间值，支撑 category_counts 的当前计算步骤。
            counts[category] += 1  # 中间载荷 用于本步治理判断

    # 返回 category_counts 已整理完成的调用载荷。
    return counts


# 定义 repo_root_for 的脚本治理处理入口。
def repo_root_for(skill_dir: Path) -> Path:

    # 逐项推进 repo_root_for 的候选项检查。
    for candidate in [skill_dir.parent.parent, skill_dir.parent, skill_dir]:

        # 检查 repo_root_for 的当前条件是否需要进入专门分支。
        if (candidate / "tests").is_dir():

            # 返回 repo_root_for 已整理完成的调用载荷。
            return candidate

    # 返回 repo_root_for 已整理完成的调用载荷。
    return skill_dir.parent.parent if skill_dir.parent != skill_dir else skill_dir


# 定义 compileall_entry 的脚本治理处理入口。
def compileall_entry(skill_dir: Path, repo_root: Path, env: dict[str, str]) -> dict[str, Any]:

    # 收集 roots 条目，保持 compileall_entry 的处理顺序稳定。
    list_roots = existing_python_roots(skill_dir)  # roots 用于本步治理判断

    # 收集 messages 条目，保持 compileall_entry 的处理顺序稳定。
    list_messages: list[str] = []  # messages 用于本步治理判断

    # 保留 ok 中间值，支撑 compileall_entry 的当前计算步骤。
    bool_ok = True  # ok 用于本步治理判断

    # 逐项推进 compileall_entry 的候选项检查。
    for name in list_roots:

        # 保留 target 中间值，支撑 compileall_entry 的当前计算步骤。
        target = skill_dir / name  # target 用于本步治理判断

        # 检查 compileall_entry 的当前条件是否需要进入专门分支。
        if not compileall.compile_dir(str(target), quiet=1, force=False):

            # 保留 ok 中间值，支撑 compileall_entry 的当前计算步骤。
            bool_ok = False  # ok 用于本步治理判断

            # 调用 append 完成 compileall_entry 的当前动作。
            list_messages.append(f"compileall failed for {name}")

    # 保留 payload 中间值，支撑 compileall_entry 的当前计算步骤。
    dict_payload = {"roots": list_roots, "errors": [] if bool_ok else list_messages}  # payload 用于本步治理判断

    # 保留 result 中间值，支撑 compileall_entry 的当前计算步骤。
    command_result = subprocess.CompletedProcess(  # result 用于本步治理判断
        args=[sys.executable, "-m", "compileall", *list_roots],  # result 用于本步治理判断
        returncode=0 if bool_ok else 1,  # result 用于本步治理判断
        stdout=json.dumps(dict_payload),  # result 用于本步治理判断
        stderr="",  # result 用于本步治理判断
    )

    # 返回 compileall_entry 已整理完成的调用载荷。
    return command_entry("compileall", [sys.executable, "-m", "compileall", *list_roots], repo_root, command_result)


# 定义 evaluate 的脚本治理处理入口。
def evaluate(skill_dir: Path, project: Path) -> dict[str, Any]:

    # 保留 repo root 中间值，支撑 evaluate 的当前计算步骤。
    path_repo_root = repo_root_for(skill_dir)  # repo root 用于本步治理判断

    # 保留 self skill 中间值，支撑 evaluate 的当前计算步骤。
    self_skill = skill_dir.name == "agents-md-generator"  # self skill 用于本步治理判断

    # 保留 base env 中间值，支撑 evaluate 的当前计算步骤。
    dict_base_env = dict(  # base env 用于本步治理判断
        os.environ,  # base env 用于本步治理判断
        AGENTS_MD_EVALUATE_RUNNING="1",  # base env 用于本步治理判断
    )

    # 检查 evaluate 的当前条件是否需要进入专门分支。
    if self_skill:

        # 保留 中间载荷 中间值，支撑 evaluate 的当前计算步骤。
        dict_base_env["AGENTS_MD_INSTALLED_SKILL_DIR"] = str(TOOL_SKILL_DIR)  # 中间载荷 用于本步治理判断
    else:

        # 调用 pop 完成 evaluate 的当前动作。
        dict_base_env.pop("AGENTS_MD_INSTALLED_SKILL_DIR", None)

    # 收集 commands 条目，保持 evaluate 的处理顺序稳定。
    list_commands: list[dict[str, Any]] = []  # commands 用于本步治理判断

    # 收集 warnings 条目，保持 evaluate 的处理顺序稳定。
    list_warnings: list[str] = []  # warnings 用于本步治理判断

    # 调用 cleanup_transient_artifacts 完成 evaluate 的当前动作。
    cleanup_transient_artifacts(skill_dir)

    # 调用 append 完成 evaluate 的当前动作。
    list_commands.append(
        run_command(
            "audit_skill",
            [sys.executable, str(tool_script_path("audit_skill.py")), str(skill_dir)],
            path_repo_root,
            dict_base_env,
        )
    )

    # 收集 python roots 条目，保持 evaluate 的处理顺序稳定。
    list_python_roots = existing_python_roots(skill_dir)  # python roots 用于本步治理判断

    # 检查 evaluate 的当前条件是否需要进入专门分支。
    if list_python_roots:

        # 调用 append 完成 evaluate 的当前动作。
        list_commands.append(compileall_entry(skill_dir, path_repo_root, dict_base_env))

        # 调用 cleanup_transient_artifacts 完成 evaluate 的当前动作。
        cleanup_transient_artifacts(skill_dir)

    # 保护 evaluate 中允许失败的外部访问。
    try:

        # 保留 validator 中间值，支撑 evaluate 的当前计算步骤。
        path_validator = quick_validate_script()  # validator 用于本步治理判断
    except FileNotFoundError as exc:

        # 调用 append 完成 evaluate 的当前动作。
        list_warnings.append(str(exc))
    else:

        # 调用 append 完成 evaluate 的当前动作。
        list_commands.append(run_command("quick_validate", [sys.executable, str(path_validator), str(skill_dir)], path_repo_root, dict_base_env))

    # 保留 validate script 中间值，支撑 evaluate 的当前计算步骤。
    validate_script = discover_validate_script(skill_dir)  # validate script 用于本步治理判断

    # 检查 evaluate 的当前条件是否需要进入专门分支。
    if validate_script is not None:

        # 调用 append 完成 evaluate 的当前动作。
        list_commands.append(
            run_command(
                "validate_script",
                [sys.executable, str(validate_script), *settings_arg(skill_dir)],
                path_repo_root,
                validate_script_env(dict_base_env, skill_dir),
            )
        )

    # 保留 manage docs script 中间值，支撑 evaluate 的当前计算步骤。
    manage_docs_script = tool_script_path("manage_docs.py")  # manage docs script 用于本步治理判断

    # 检查 evaluate 的当前条件是否需要进入专门分支。
    if manage_docs_script.is_file() and (project / ".agents" / "agents-control.json").is_file():

        # 调用 append 完成 evaluate 的当前动作。
        list_commands.append(
            run_command("manage_docs_verify", [sys.executable, str(manage_docs_script), "verify", str(project)], path_repo_root, dict_base_env)
        )

    # 保留 verify agents script 中间值，支撑 evaluate 的当前计算步骤。
    verify_agents_script = tool_script_path("verify_agents.py")  # verify agents script 用于本步治理判断

    # 检查 evaluate 的当前条件是否需要进入专门分支。
    if verify_agents_script.is_file() and (project / "AGENTS.md").is_file():

        # 保留 verify argv 中间值，支撑 evaluate 的当前计算步骤。
        list_verify_argv = [sys.executable, str(verify_agents_script), str(project)]  # verify argv 用于本步治理判断

        # 检查 evaluate 的当前条件是否需要进入专门分支。
        if self_skill:

            # 调用 extend 完成 evaluate 的当前动作。
            list_verify_argv.extend(["--installed-skill-dir", str(skill_dir)])

        # 调用 append 完成 evaluate 的当前动作。
        list_commands.append(run_command("verify_agents", list_verify_argv, path_repo_root, dict_base_env))

    # 保留 source governance script 中间值，支撑 evaluate 的当前计算步骤。
    source_governance_script = tool_script_path("check_source_governance.py")  # source governance script 用于本步治理判断

    # 检查 evaluate 的当前条件是否需要进入专门分支。
    if source_governance_script.is_file() and ((project / ".agents" / "global-rule-overrides.json").is_file() or self_skill):

        # 调用 append 完成 evaluate 的当前动作。
        list_commands.append(run_command("source_governance", [sys.executable, str(source_governance_script), str(project)], path_repo_root, dict_base_env))

    # 检查 evaluate 的当前条件是否需要进入专门分支。
    if self_skill:

        # 调用 append 完成 evaluate 的当前动作。
        list_commands.append(render_entry(project, dict_base_env))

    # 调用 cleanup_transient_artifacts 完成 evaluate 的当前动作。
    cleanup_transient_artifacts(skill_dir)

    # 收集 errors 条目，保持 evaluate 的处理顺序稳定。
    list_errors = collect_errors(list_commands)  # errors 用于本步治理判断

    # 收集 structured errors 条目，保持 evaluate 的处理顺序稳定。
    list_structured_errors = classified_errors(list_commands, self_skill=self_skill)  # structured errors 用于本步治理判断

    # 返回 evaluate 已整理完成的调用载荷。
    return {
        "ok": not list_errors,
        "skill_dir": str(skill_dir),
        "project": str(project),
        "commands": list_commands,
        "errors": list_errors,
        "classified_errors": list_structured_errors,
        "category_counts": category_counts(list_structured_errors),
        "warnings": list_warnings,
    }


# 定义 main 的脚本治理处理入口。
def main() -> None:

    # 保留 parser 中间值，支撑 main 的当前计算步骤。
    parser = argparse.ArgumentParser(description="Run the fact-level validation chain for a target skill.")  # parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("skill_dir", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("project", nargs="?", default=None)

    # 收集 args 条目，保持 main 的处理顺序稳定。
    args = parser.parse_args()  # args 用于本步治理判断

    # 保留 skill dir 中间值，支撑 main 的当前计算步骤。
    skill_dir = resolve_project(args.skill_dir)  # skill dir 用于本步治理判断

    # 保留 project 中间值，支撑 main 的当前计算步骤。
    project = resolve_project(args.project) if args.project else repo_root_for(skill_dir)  # project 用于本步治理判断

    # 调用 emit_json 完成 main 的当前动作。
    emit_json(evaluate(skill_dir, project))


# 检查 模块入口 的当前条件是否需要进入专门分支。
if __name__ == "__main__":

    # 调用 main 完成 模块入口 的当前动作。
    main()


