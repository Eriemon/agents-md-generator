# 导入 远程门禁 所需的依赖模块。
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

# 导入 远程门禁 所需的依赖模块。
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断
from design_questions import *

# 定义 use_remote_server_enabled 的远程门禁处理入口。
def use_remote_server_enabled(answers: dict[str, Any]) -> bool:

    # 返回 use_remote_server_enabled 已整理完成的调用载荷。
    return bool(answers.get(USE_REMOTE_SERVER_KEY))

# 定义 normalize_remote_task_list 的远程门禁处理入口。
def normalize_remote_task_list(raw: Any) -> list[str]:

    # 检查 normalize_remote_task_list 的当前条件是否需要进入专门分支。
    if isinstance(raw, list):

        # 收集 values 条目，保持 normalize_remote_task_list 的处理顺序稳定。
        list_values = [str(item).strip() for item in raw]  # values 用于本步治理判断

    # 检查 normalize_remote_task_list 的当前条件是否需要进入专门分支。
    elif isinstance(raw, str):

        # 收集 values 条目，保持 normalize_remote_task_list 的处理顺序稳定。
        list_values = [part.strip() for part in re.split(r"[\r\n,，;；]+", raw)]  # values 用于本步治理判断
    else:

        # 收集 values 条目，保持 normalize_remote_task_list 的处理顺序稳定。
        list_values = []  # values 用于本步治理判断

    # 保留 normalized 中间值，支撑 normalize_remote_task_list 的当前计算步骤。
    list_normalized: list[str] = []  # normalized 用于本步治理判断

    # 保留 seen 中间值，支撑 normalize_remote_task_list 的当前计算步骤。
    set_seen: set[str] = set()  # seen 用于本步治理判断

    # 逐项推进 normalize_remote_task_list 的候选项检查。
    for value in list_values:

        # 检查 normalize_remote_task_list 的当前条件是否需要进入专门分支。
        if not value:

            # 分隔 normalize_remote_task_list 的控制流边界。
            continue

        # 保留 key 中间值，支撑 normalize_remote_task_list 的当前计算步骤。
        key = value.casefold()  # key 用于本步治理判断

        # 检查 normalize_remote_task_list 的当前条件是否需要进入专门分支。
        if key in set_seen:

            # 分隔 normalize_remote_task_list 的控制流边界。
            continue

        # 调用 add 完成 normalize_remote_task_list 的当前动作。
        set_seen.add(key)

        # 调用 append 完成 normalize_remote_task_list 的当前动作。
        list_normalized.append(value)

    # 返回 normalize_remote_task_list 已整理完成的调用载荷。
    return list_normalized


# 定义 normalize_remote_task_name 的远程门禁处理入口。
def normalize_remote_task_name(raw: Any) -> str:

    # 返回 normalize_remote_task_name 已整理完成的调用载荷。
    return str(raw or "").strip()


# 定义 normalize_remote_task_key 的远程门禁处理入口。
def normalize_remote_task_key(raw: Any) -> str:

    # 返回 normalize_remote_task_key 已整理完成的调用载荷。
    return normalize_remote_task_name(raw).casefold()


# 定义 normalize_remote_server_registry 的远程门禁处理入口。
def normalize_remote_server_registry(raw: Any) -> list[dict[str, Any]]:

    # 检查 normalize_remote_server_registry 的当前条件是否需要进入专门分支。
    if not isinstance(raw, list):

        # 返回 normalize_remote_server_registry 已整理完成的调用载荷。
        return []

    # 保留 registry 中间值，支撑 normalize_remote_server_registry 的当前计算步骤。
    list_registry: list[dict[str, Any]] = []  # registry 用于本步治理判断

    # 保留 seen 中间值，支撑 normalize_remote_server_registry 的当前计算步骤。
    set_seen: set[str] = set()  # seen 用于本步治理判断

    # 逐项推进 normalize_remote_server_registry 的候选项检查。
    for item in raw:

        # 检查 normalize_remote_server_registry 的当前条件是否需要进入专门分支。
        if not isinstance(item, dict):

            # 分隔 normalize_remote_server_registry 的控制流边界。
            continue

        # 保留 server id 中间值，支撑 normalize_remote_server_registry 的当前计算步骤。
        server_id = str(item.get("id", "")).strip()  # server id 用于本步治理判断

        # 检查 normalize_remote_server_registry 的当前条件是否需要进入专门分支。
        if not server_id or server_id in set_seen:

            # 分隔 normalize_remote_server_registry 的控制流边界。
            continue

        # 调用 add 完成 normalize_remote_server_registry 的当前动作。
        set_seen.add(server_id)

        # 调用 append 完成 normalize_remote_server_registry 的当前动作。
        list_registry.append(
            {
                "id": server_id,
                "name": str(item.get("name", "")).strip(),
                "category": str(item.get("category", "")).strip(),
                "functions": normalize_remote_task_list(item.get("functions", [])),
                "enabled": bool(item.get("enabled", False)),
                "validation_status": str(item.get("validation_status", "")).strip(),
                "workspace_status": str(item.get("workspace_status", "")).strip(),
            }
        )

    # 返回 normalize_remote_server_registry 已整理完成的调用载荷。
    return list_registry


# 定义 normalize_remote_task_routes 的远程门禁处理入口。
def normalize_remote_task_routes(raw: Any) -> list[dict[str, Any]]:

    # 检查 normalize_remote_task_routes 的当前条件是否需要进入专门分支。
    if not isinstance(raw, list):

        # 返回 normalize_remote_task_routes 已整理完成的调用载荷。
        return []

    # 收集 routes 条目，保持 normalize_remote_task_routes 的处理顺序稳定。
    list_routes: list[dict[str, Any]] = []  # routes 用于本步治理判断

    # 保留 seen 中间值，支撑 normalize_remote_task_routes 的当前计算步骤。
    set_seen: set[str] = set()  # seen 用于本步治理判断

    # 逐项推进 normalize_remote_task_routes 的候选项检查。
    for item in raw:

        # 检查 normalize_remote_task_routes 的当前条件是否需要进入专门分支。
        if not isinstance(item, dict):

            # 分隔 normalize_remote_task_routes 的控制流边界。
            continue

        # 保留 task name 中间值，支撑 normalize_remote_task_routes 的当前计算步骤。
        str_task_name = normalize_remote_task_name(item.get("task_name", ""))  # task name 用于本步治理判断

        # 保留 task key 中间值，支撑 normalize_remote_task_routes 的当前计算步骤。
        str_task_key = normalize_remote_task_key(str_task_name)  # task key 用于本步治理判断

        # 检查 normalize_remote_task_routes 的当前条件是否需要进入专门分支。
        if not str_task_name or not str_task_key or str_task_key in set_seen:

            # 分隔 normalize_remote_task_routes 的控制流边界。
            continue

        # 调用 add 完成 normalize_remote_task_routes 的当前动作。
        set_seen.add(str_task_key)

        # 保留 primary server id 中间值，支撑 normalize_remote_task_routes 的当前计算步骤。
        primary_server_id = str(item.get("primary_server_id", "")).strip()  # primary server id 用于本步治理判断

        # 收集 fallback server ids 条目，保持 normalize_remote_task_routes 的处理顺序稳定。
        list_fallback_server_ids: list[str] = []  # fallback server ids 用于本步治理判断

        # 收集 seen fallbacks 条目，保持 normalize_remote_task_routes 的处理顺序稳定。
        set_seen_fallbacks: set[str] = set()  # seen fallbacks 用于本步治理判断

        # 逐项推进 normalize_remote_task_routes 的候选项检查。
        for server_id in normalize_remote_task_list(item.get("fallback_server_ids", [])):

            # 检查 normalize_remote_task_routes 的当前条件是否需要进入专门分支。
            if server_id == primary_server_id or server_id in set_seen_fallbacks:

                # 分隔 normalize_remote_task_routes 的控制流边界。
                continue

            # 调用 add 完成 normalize_remote_task_routes 的当前动作。
            set_seen_fallbacks.add(server_id)

            # 调用 append 完成 normalize_remote_task_routes 的当前动作。
            list_fallback_server_ids.append(server_id)

        # 收集 route tasks 条目，保持 normalize_remote_task_routes 的处理顺序稳定。
        list_route_tasks = normalize_remote_task_list(item.get("route_tasks", item.get("server_tasks", [])))  # route tasks 用于本步治理判断

        # 收集 route functions 条目，保持 normalize_remote_task_routes 的处理顺序稳定。
        list_route_functions = normalize_remote_task_list(item.get("route_functions", item.get("source_functions", [])))  # route functions 用于本步治理判断

        # 调用 append 完成 normalize_remote_task_routes 的当前动作。
        list_routes.append(
            {
                "task_name": str_task_name,
                "task_key": str_task_key,
                "primary_server_id": primary_server_id,
                "fallback_server_ids": list_fallback_server_ids,
                "route_tasks": list_route_tasks,
                "route_functions": list_route_functions,
                "selection_confirmed": bool(item.get("selection_confirmed", False)),
                "validation_status": str(item.get("validation_status", "")).strip(),
            }
        )

    # 返回 normalize_remote_task_routes 已整理完成的调用载荷。
    return list_routes


# 定义 remote_settings_path 的远程门禁处理入口。
def remote_settings_path(skill_dir: Path) -> Path | None:

    # 逐项推进 remote_settings_path 的候选项检查。
    for relative in ("assets/defaults.json", "config/defaults.json"):

        # 保留 candidate 中间值，支撑 remote_settings_path 的当前计算步骤。
        candidate = skill_dir / relative  # candidate 用于本步治理判断

        # 检查 remote_settings_path 的当前条件是否需要进入专门分支。
        if candidate.is_file():

            # 返回 remote_settings_path 已整理完成的调用载荷。
            return candidate

    # 返回 remote_settings_path 已整理完成的调用载荷。
    return None


# 定义 remote_skill_dir 的远程门禁处理入口。
def remote_skill_dir() -> Path | None:

    # 保留 override 中间值，支撑 remote_skill_dir 的当前计算步骤。
    override = os.environ.get("AGENTS_MD_REMOTE_SSH_SKILL_DIR", "").strip()  # override 用于本步治理判断

    # 收集 candidates 条目，保持 remote_skill_dir 的处理顺序稳定。
    list_candidates: list[Path] = []  # candidates 用于本步治理判断

    # 检查 remote_skill_dir 的当前条件是否需要进入专门分支。
    if override:

        # 调用 append 完成 remote_skill_dir 的当前动作。
        list_candidates.append(Path(override).resolve())

    # 保留 codex home 中间值，支撑 remote_skill_dir 的当前计算步骤。
    codex_home = os.environ.get("CODEX_HOME", "").strip()  # codex home 用于本步治理判断

    # 检查 remote_skill_dir 的当前条件是否需要进入专门分支。
    if codex_home:

        # 调用 append 完成 remote_skill_dir 的当前动作。
        list_candidates.append((Path(codex_home).resolve() / "skills" / REMOTE_SSH_SKILL_NAME).resolve())
    else:

        # 调用 append 完成 remote_skill_dir 的当前动作。
        list_candidates.append((Path.home() / ".codex" / "skills" / REMOTE_SSH_SKILL_NAME).resolve())

    # 逐项推进 remote_skill_dir 的候选项检查。
    for candidate in list_candidates:

        # 检查 remote_skill_dir 的当前条件是否需要进入专门分支。
        if (
            candidate.is_dir()
            and (candidate / "SKILL.md").is_file()
            and (candidate / "scripts" / "remote_ssh.py").is_file()
            and remote_settings_path(candidate) is not None
        ):

            # 返回 remote_skill_dir 已整理完成的调用载荷。
            return candidate

    # 返回 remote_skill_dir 已整理完成的调用载荷。
    return None

# 定义 remote_dependency_summary 的远程门禁处理入口。
def remote_dependency_summary() -> dict[str, Any]:

    # 保留 skill dir 中间值，支撑 remote_dependency_summary 的当前计算步骤。
    skill_dir = remote_skill_dir()  # skill dir 用于本步治理判断

    # 返回 remote_dependency_summary 已整理完成的调用载荷。
    return {
        "installed": skill_dir is not None,
        "skill_dir": str(skill_dir) if skill_dir else "",
        "url": REMOTE_SSH_GIT_URL,
        "install_specs": list(REMOTE_SSH_INSTALL_SPECS),
    }

# 定义 remote_ssh_command 的远程门禁处理入口。
def remote_ssh_command(skill_dir: Path, subcommand: str, *extra: str) -> list[str]:

    # 保留 command 中间值，支撑 remote_ssh_command 的当前计算步骤。
    list_command = [  # command 用于本步治理判断
        sys.executable,  # command 用于本步治理判断
        str(skill_dir / "scripts" / "remote_ssh.py"),  # command 用于本步治理判断
        subcommand,  # command 用于本步治理判断
    ]

    # 定位 settings path 的文件边界，供 remote_ssh_command 后续读写校验使用。
    settings_path = remote_settings_path(skill_dir)  # settings path 用于本步治理判断

    # 检查 remote_ssh_command 的当前条件是否需要进入专门分支。
    if settings_path is not None:

        # 调用 extend 完成 remote_ssh_command 的当前动作。
        list_command.extend(["--settings", str(settings_path)])

    # 调用 extend 完成 remote_ssh_command 的当前动作。
    list_command.extend(extra)

    # 返回 remote_ssh_command 已整理完成的调用载荷。
    return list_command

# 定义 run_remote_ssh 的远程门禁处理入口。
def run_remote_ssh(skill_dir: Path, subcommand: str, *extra: str) -> subprocess.CompletedProcess[str]:

    # 返回 run_remote_ssh 已整理完成的调用载荷。
    return subprocess.run(
        remote_ssh_command(skill_dir, subcommand, *extra),
        text=True,
        capture_output=True,
        check=False,
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
    )

# 定义 parse_remote_kv 的远程门禁处理入口。
def parse_remote_kv(stdout: str) -> dict[str, str]:

    # 保留 data 中间值，支撑 parse_remote_kv 的当前计算步骤。
    dict_data: dict[str, str] = {}  # data 用于本步治理判断

    # 逐项推进 parse_remote_kv 的候选项检查。
    for line in stdout.splitlines():

        # 检查 parse_remote_kv 的当前条件是否需要进入专门分支。
        if ": " not in line:

            # 分隔 parse_remote_kv 的控制流边界。
            continue

        # 保留 key、value 中间值，支撑 parse_remote_kv 的当前计算步骤。
        key, raw_value = line.split(": ", 1)  # key、value 用于本步治理判断

        # 保留 中间载荷 中间值，支撑 parse_remote_kv 的当前计算步骤。
        dict_data[key.strip()] = raw_value.strip()  # 中间载荷 用于本步治理判断

    # 返回 parse_remote_kv 已整理完成的调用载荷。
    return dict_data

# 定义 remote_discover 的远程门禁处理入口。
def remote_discover(skill_dir: Path) -> tuple[dict[str, Any], list[str]]:

    # 保留 result 中间值，支撑 remote_discover 的当前计算步骤。
    completed_process_result = run_remote_ssh(skill_dir, "discover", "--json")  # result 用于本步治理判断

    # 收集 errors 条目，保持 remote_discover 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 保护 remote_discover 中允许失败的外部访问。
    try:

        # 保留 data 中间值，支撑 remote_discover 的当前计算步骤。
        dict_data = json.loads(completed_process_result.stdout) if completed_process_result.stdout.strip() else {}  # data 用于本步治理判断
    except json.JSONDecodeError:

        # 保留 data 中间值，支撑 remote_discover 的当前计算步骤。
        dict_data = {}  # data 用于本步治理判断

        # 调用 append 完成 remote_discover 的当前动作。
        list_errors.append("erie-remote-ssh discover did not return valid JSON")

    # 检查 remote_discover 的当前条件是否需要进入专门分支。
    if not isinstance(dict_data, dict):

        # 保留 data 中间值，支撑 remote_discover 的当前计算步骤。
        dict_data = {}  # data 用于本步治理判断

        # 调用 append 完成 remote_discover 的当前动作。
        list_errors.append("erie-remote-ssh discover JSON must be an object")

    # 调用 setdefault 完成 remote_discover 的当前动作。
    dict_data.setdefault("status", "failed")

    # 调用 setdefault 完成 remote_discover 的当前动作。
    dict_data.setdefault("message", "")

    # 调用 setdefault 完成 remote_discover 的当前动作。
    dict_data.setdefault("next_action", "")

    # 保留 中间载荷 中间值，支撑 remote_discover 的当前计算步骤。
    dict_data["returncode"] = completed_process_result.returncode  # 中间载荷 用于本步治理判断

    # 检查 remote_discover 的当前条件是否需要进入专门分支。
    if completed_process_result.returncode not in {0, 3, 4}:

        # 保留 summary 中间值，支撑 remote_discover 的当前计算步骤。
        summary = completed_process_result.stderr.strip() or completed_process_result.stdout.strip() or f"unexpected discover return code {result.returncode}"  # summary 用于本步治理判断

        # 调用 append 完成 remote_discover 的当前动作。
        list_errors.append(f"erie-remote-ssh discover failed: {summary}")

    # 返回 remote_discover 已整理完成的调用载荷。
    return dict_data, list_errors

# 定义 remote_choices 的远程门禁处理入口。
def remote_choices(skill_dir: Path) -> tuple[dict[str, Any], list[str]]:

    # 保留 result 中间值，支撑 remote_choices 的当前计算步骤。
    completed_process_result = run_remote_ssh(skill_dir, "choices", "--json")  # result 用于本步治理判断

    # 收集 errors 条目，保持 remote_choices 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 保护 remote_choices 中允许失败的外部访问。
    try:

        # 保留 data 中间值，支撑 remote_choices 的当前计算步骤。
        dict_data = json.loads(completed_process_result.stdout) if completed_process_result.stdout.strip() else {}  # data 用于本步治理判断
    except json.JSONDecodeError:

        # 保留 data 中间值，支撑 remote_choices 的当前计算步骤。
        dict_data = {}  # data 用于本步治理判断

        # 调用 append 完成 remote_choices 的当前动作。
        list_errors.append("erie-remote-ssh choices did not return valid JSON")

    # 检查 remote_choices 的当前条件是否需要进入专门分支。
    if not isinstance(dict_data, dict):

        # 保留 data 中间值，支撑 remote_choices 的当前计算步骤。
        dict_data = {}  # data 用于本步治理判断

        # 调用 append 完成 remote_choices 的当前动作。
        list_errors.append("erie-remote-ssh choices JSON must be an object")

    # 收集 servers 条目，保持 remote_choices 的处理顺序稳定。
    list_servers = dict_data.get("servers", [])  # servers 用于本步治理判断

    # 检查 remote_choices 的当前条件是否需要进入专门分支。
    if not isinstance(list_servers, list):

        # 收集 servers 条目，保持 remote_choices 的处理顺序稳定。
        list_servers = []  # servers 用于本步治理判断

        # 调用 append 完成 remote_choices 的当前动作。
        list_errors.append("erie-remote-ssh choices JSON must contain a servers list")

    # 保留 中间载荷 中间值，支撑 remote_choices 的当前计算步骤。
    dict_data["servers"] = list_servers  # 中间载荷 用于本步治理判断

    # 调用 setdefault 完成 remote_choices 的当前动作。
    dict_data.setdefault("status", "failed")

    # 保留 中间载荷 中间值，支撑 remote_choices 的当前计算步骤。
    dict_data["returncode"] = completed_process_result.returncode  # 中间载荷 用于本步治理判断

    # 检查 remote_choices 的当前条件是否需要进入专门分支。
    if completed_process_result.returncode not in {0, 4}:

        # 保留 summary 中间值，支撑 remote_choices 的当前计算步骤。
        summary = completed_process_result.stderr.strip() or completed_process_result.stdout.strip() or f"unexpected choices return code {result.returncode}"  # summary 用于本步治理判断

        # 调用 append 完成 remote_choices 的当前动作。
        list_errors.append(f"erie-remote-ssh choices failed: {summary}")

    # 返回 remote_choices 已整理完成的调用载荷。
    return dict_data, list_errors

# 定义 remote_server_record 的远程门禁处理入口。
def remote_server_record(records: list[dict[str, Any]], selector: str) -> dict[str, Any] | None:

    # 保留 selector fold 中间值，支撑 remote_server_record 的当前计算步骤。
    selector_fold = selector.strip().casefold()  # selector fold 用于本步治理判断

    # 逐项推进 remote_server_record 的候选项检查。
    for record in records:

        # 检查 remote_server_record 的当前条件是否需要进入专门分支。
        if not isinstance(record, dict):

            # 分隔 remote_server_record 的控制流边界。
            continue

        # 检查 remote_server_record 的当前条件是否需要进入专门分支。
        if selector_fold in {str(record.get("id", "")).casefold(), str(record.get("name", "")).casefold()}:

            # 返回 remote_server_record 已整理完成的调用载荷。
            return record

    # 返回 remote_server_record 已整理完成的调用载荷。
    return None

# 定义 remote_server_check 的远程门禁处理入口。
def remote_server_check(skill_dir: Path, server_id: str) -> tuple[dict[str, str], list[str]]:

    # 保留 result 中间值，支撑 remote_server_check 的当前计算步骤。
    completed_process_result = run_remote_ssh(skill_dir, "check", "--server", server_id)  # result 用于本步治理判断

    # 保留 data 中间值，支撑 remote_server_check 的当前计算步骤。
    dict_data = parse_remote_kv(completed_process_result.stdout)  # data 用于本步治理判断

    # 收集 errors 条目，保持 remote_server_check 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 检查 remote_server_check 的当前条件是否需要进入专门分支。
    if completed_process_result.returncode != 0:

        # 保留 summary 中间值，支撑 remote_server_check 的当前计算步骤。
        summary = completed_process_result.stderr.strip() or completed_process_result.stdout.strip() or f"check failed with return code {result.returncode}"  # summary 用于本步治理判断

        # 调用 append 完成 remote_server_check 的当前动作。
        list_errors.append(f"erie-remote-ssh check failed for {server_id}: {summary}")

    # 检查 remote_server_check 的当前条件是否需要进入专门分支。
    if dict_data.get("status") != "ok":

        # 调用 append 完成 remote_server_check 的当前动作。
        list_errors.append(f"erie-remote-ssh check did not return ok status for {server_id}")

    # 返回 remote_server_check 已整理完成的调用载荷。
    return dict_data, list_errors

# 定义 remote_server_workspace_check 的远程门禁处理入口。
def remote_server_workspace_check(skill_dir: Path, server_id: str) -> tuple[dict[str, str], list[str]]:

    # 保留 result 中间值，支撑 remote_server_workspace_check 的当前计算步骤。
    completed_process_result = run_remote_ssh(skill_dir, "workspace-check", "--server", server_id)  # result 用于本步治理判断

    # 保留 data 中间值，支撑 remote_server_workspace_check 的当前计算步骤。
    dict_data = parse_remote_kv(completed_process_result.stdout)  # data 用于本步治理判断

    # 收集 errors 条目，保持 remote_server_workspace_check 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 检查 remote_server_workspace_check 的当前条件是否需要进入专门分支。
    if completed_process_result.returncode != 0:

        # 优先复用远程命令 stderr/stdout，避免吞掉真实 SSH 失败原因。
        summary = completed_process_result.stderr.strip() or completed_process_result.stdout.strip()  # 远程 workspace-check 失败摘要

        # stderr/stdout 为空时补充退出码，保证诊断文本非空。
        if not summary:

            # 空输出失败仍要返回可读摘要，便于交互流程展示阻断原因。
            summary = f"workspace-check failed with return code {completed_process_result.returncode}"  # 空输出失败兜底摘要

        # 调用 append 完成 remote_server_workspace_check 的当前动作。
        list_errors.append(f"erie-remote-ssh workspace-check failed for {server_id}: {summary}")

    # 检查 remote_server_workspace_check 的当前条件是否需要进入专门分支。
    if dict_data.get("status") != "ok":

        # 调用 append 完成 remote_server_workspace_check 的当前动作。
        list_errors.append(f"erie-remote-ssh workspace-check did not return ok status for {server_id}")

    # 返回 remote_server_workspace_check 已整理完成的调用载荷。
    return dict_data, list_errors

# 定义 remote_install_command_hint 的远程门禁处理入口。
def remote_install_command_hint(skill_dir: Path | None = None) -> str:

    # 检查 remote_install_command_hint 的当前条件是否需要进入专门分支。
    if skill_dir is not None:

        # 返回 remote_install_command_hint 已整理完成的调用载荷。
        return f"Install `{REMOTE_SSH_SKILL_NAME}` from {REMOTE_SSH_GIT_URL}, then rerun `python scripts/python/design/collect_design_profile.py <project> --resume`."

    # 返回 remote_install_command_hint 已整理完成的调用载荷。
    return f"Install `{REMOTE_SSH_SKILL_NAME}` from {REMOTE_SSH_GIT_URL}, then rerun `python scripts/python/design/collect_design_profile.py <project> --resume`."

# 定义 remote_configure_command_hint 的远程门禁处理入口。
def remote_configure_command_hint(skill_dir: Path) -> str:

    # 保留 command 中间值，支撑 remote_configure_command_hint 的当前计算步骤。
    command = f"python {skill_dir / 'scripts' / 'remote_ssh.py'} configure"  # command 用于本步治理判断

    # 定位 settings path 的文件边界，供 remote_configure_command_hint 后续读写校验使用。
    settings_path = remote_settings_path(skill_dir)  # settings path 用于本步治理判断

    # 检查 remote_configure_command_hint 的当前条件是否需要进入专门分支。
    if settings_path is not None:

        # 保留 command 中间值，支撑 remote_configure_command_hint 的当前计算步骤。
        command += f" --settings {settings_path}"  # command 用于本步治理判断

    # 保留 command 中间值，支撑 remote_configure_command_hint 的当前计算步骤。
    command += " --interactive"  # command 用于本步治理判断

    # 返回 remote_configure_command_hint 已整理完成的调用载荷。
    return command

# 定义 remote_gate_payload 的远程门禁处理入口。
def remote_gate_payload(state: dict[str, Any]) -> dict[str, Any]:

    # 保留 gate 中间值，支撑 remote_gate_payload 的当前计算步骤。
    """说明 remote_gate_payload 在 AGENTS 治理流程中的状态处理职责。
    
    数组契约:
        shape/维度: 本函数处理 AGENTS 状态、JSON 记录或文件路径，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict、list、str、Path 等 Python 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义以 AGENTS 治理配置和状态文件 schema 为准。
    """

    # 明确该赋值在远程门禁流程中的业务用途。
    gate = state.get("remote_server_gate", {})  # gate 用于本步治理判断

    # 返回 remote_gate_payload 已整理完成的调用载荷。
    return gate if isinstance(gate, dict) else {}

# 定义 set_remote_gate_payload 的远程门禁处理入口。
def set_remote_gate_payload(state: dict[str, Any], payload: dict[str, Any]) -> None:

    # 保留 中间载荷 中间值，支撑 set_remote_gate_payload 的当前计算步骤。
    """说明 set_remote_gate_payload 在 AGENTS 治理流程中的状态处理职责。
    
    数组契约:
        shape/维度: 本函数处理 AGENTS 状态、JSON 记录或文件路径，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict、list、str、Path 等 Python 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义以 AGENTS 治理配置和状态文件 schema 为准。
    """

    # 说明下方代码段在远程门禁流程中的职责。
    state["remote_server_gate"] = payload  # 中间载荷 用于本步治理判断


# 定义 server_registry_map 的远程门禁处理入口。
def server_registry_map(registry: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:

    # 返回 server_registry_map 已整理完成的调用载荷。
    return {
        str(item.get("id", "")).strip(): item
        for item in registry
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }


# 定义 ordered_route_server_ids 的远程门禁处理入口。
def ordered_route_server_ids(route: dict[str, Any]) -> list[str]:

    # 保留 primary 中间值，支撑 ordered_route_server_ids 的当前计算步骤。
    primary = str(route.get("primary_server_id", "")).strip()  # primary 用于本步治理判断

    # 保留 ordered 中间值，支撑 ordered_route_server_ids 的当前计算步骤。
    list_ordered: list[str] = []  # ordered 用于本步治理判断

    # 检查 ordered_route_server_ids 的当前条件是否需要进入专门分支。
    if primary:

        # 调用 append 完成 ordered_route_server_ids 的当前动作。
        list_ordered.append(primary)

    # 逐项推进 ordered_route_server_ids 的候选项检查。
    for server_id in normalize_remote_task_list(route.get("fallback_server_ids", [])):

        # 检查 ordered_route_server_ids 的当前条件是否需要进入专门分支。
        if server_id not in list_ordered:

            # 调用 append 完成 ordered_route_server_ids 的当前动作。
            list_ordered.append(server_id)

    # 返回 ordered_route_server_ids 已整理完成的调用载荷。
    return list_ordered


# 定义 match_remote_task_route 的远程门禁处理入口。
def match_remote_task_route(task_routes: list[dict[str, Any]], task_name: str) -> dict[str, Any] | None:

    # 保留 task key 中间值，支撑 match_remote_task_route 的当前计算步骤。
    str_task_key = normalize_remote_task_key(task_name)  # task key 用于本步治理判断

    # 检查 match_remote_task_route 的当前条件是否需要进入专门分支。
    if not str_task_key:

        # 返回 match_remote_task_route 已整理完成的调用载荷。
        return None

    # 逐项推进 match_remote_task_route 的候选项检查。
    for route in task_routes:

        # 检查 match_remote_task_route 的当前条件是否需要进入专门分支。
        if not isinstance(route, dict):

            # 分隔 match_remote_task_route 的控制流边界。
            continue

        # 检查 match_remote_task_route 的当前条件是否需要进入专门分支。
        if normalize_remote_task_key(route.get("task_name", "")) == str_task_key:

            # 返回 match_remote_task_route 已整理完成的调用载荷。
            return route

    # 返回 match_remote_task_route 已整理完成的调用载荷。
    return None


# 定义 validate_route_server_ids 的远程门禁处理入口。
def validate_route_server_ids(route: dict[str, Any], registry: dict[str, dict[str, Any]]) -> list[str]:

    # 收集 errors 条目，保持 validate_route_server_ids 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 保留 task name 中间值，支撑 validate_route_server_ids 的当前计算步骤。
    task_name = str(route.get("task_name", "")).strip() or "<unknown>"  # task name 用于本步治理判断

    # 保留 primary 中间值，支撑 validate_route_server_ids 的当前计算步骤。
    primary = str(route.get("primary_server_id", "")).strip()  # primary 用于本步治理判断

    # 检查 validate_route_server_ids 的当前条件是否需要进入专门分支。
    if not primary:

        # 调用 append 完成 validate_route_server_ids 的当前动作。
        list_errors.append(f"route `{task_name}` is missing primary_server_id")

    # 检查 validate_route_server_ids 的当前条件是否需要进入专门分支。
    elif primary not in registry:

        # 调用 append 完成 validate_route_server_ids 的当前动作。
        list_errors.append(f"route `{task_name}` references unknown primary server `{primary}`")

    # 逐项推进 validate_route_server_ids 的候选项检查。
    for server_id in normalize_remote_task_list(route.get("fallback_server_ids", [])):

        # 检查 validate_route_server_ids 的当前条件是否需要进入专门分支。
        if server_id not in registry:

            # 调用 append 完成 validate_route_server_ids 的当前动作。
            list_errors.append(f"route `{task_name}` references unknown fallback server `{server_id}`")

    # 返回 validate_route_server_ids 已整理完成的调用载荷。
    return list_errors


# 定义 resolve_remote_server_for_task 的远程门禁处理入口。
def resolve_remote_server_for_task(contract: dict[str, Any], task_name: str, skill_dir: Path | None = None) -> dict[str, Any]:

    # 检查 resolve_remote_server_for_task 的当前条件是否需要进入专门分支。
    if not isinstance(contract, dict) or not contract.get("enabled"):

        # 返回 resolve_remote_server_for_task 已整理完成的调用载荷。
        return {
            "ok": False,
            "decision": "blocked",
            "message": "Remote server routing is not enabled for this work folder.",
        }

    # 收集 routes 条目，保持 resolve_remote_server_for_task 的处理顺序稳定。
    list_routes = normalize_remote_task_routes(contract.get("task_routes", []))  # routes 用于本步治理判断

    # 保留 route 中间值，支撑 resolve_remote_server_for_task 的当前计算步骤。
    route = match_remote_task_route(list_routes, task_name)  # route 用于本步治理判断

    # 检查 resolve_remote_server_for_task 的当前条件是否需要进入专门分支。
    if route is None:

        # 返回 resolve_remote_server_for_task 已整理完成的调用载荷。
        return {
            "ok": False,
            "decision": "blocked",
            "message": "No registered remote server route matches this task. Update the current work folder AGENTS.md before continuing.",
        }

    # 保留 registry 中间值，支撑 resolve_remote_server_for_task 的当前计算步骤。
    dict_registry = server_registry_map(normalize_remote_server_registry(contract.get("server_registry", [])))  # registry 用于本步治理判断

    # 收集 route errors 条目，保持 resolve_remote_server_for_task 的处理顺序稳定。
    list_route_errors = validate_route_server_ids(route, dict_registry)  # route errors 用于本步治理判断

    # 检查 resolve_remote_server_for_task 的当前条件是否需要进入专门分支。
    if list_route_errors:

        # 返回 resolve_remote_server_for_task 已整理完成的调用载荷。
        return {
            "ok": False,
            "decision": "blocked",
            "message": "; ".join(list_route_errors),
            "matched_route": route,
        }

    # 保留 dependency 中间值，支撑 resolve_remote_server_for_task 的当前计算步骤。
    dict_dependency = remote_dependency_summary()  # dependency 用于本步治理判断

    # 保留 active skill dir 中间值，支撑 resolve_remote_server_for_task 的当前计算步骤。
    path_active_skill_dir = skill_dir  # active skill dir 用于本步治理判断

    # 检查 resolve_remote_server_for_task 的当前条件是否需要进入专门分支。
    if path_active_skill_dir is None and dict_dependency.get("installed"):

        # 保留 active skill dir 中间值，支撑 resolve_remote_server_for_task 的当前计算步骤。
        path_active_skill_dir = Path(str(dict_dependency.get("skill_dir", "")))  # active skill dir 用于本步治理判断

    # 检查 resolve_remote_server_for_task 的当前条件是否需要进入专门分支。
    if path_active_skill_dir is None or not str(path_active_skill_dir):

        # 返回 resolve_remote_server_for_task 已整理完成的调用载荷。
        return {
            "ok": False,
            "decision": "blocked",
            "message": f"Remote dependency `{REMOTE_SSH_SKILL_NAME}` is not installed.",
            "matched_route": route,
        }

    # 收集 attempted server ids 条目，保持 resolve_remote_server_for_task 的处理顺序稳定。
    list_attempted_server_ids: list[str] = []  # attempted server ids 用于本步治理判断

    # 收集 failures 条目，保持 resolve_remote_server_for_task 的处理顺序稳定。
    list_failures: list[str] = []  # failures 用于本步治理判断

    # 逐项推进 resolve_remote_server_for_task 的候选项检查。
    for server_id in ordered_route_server_ids(route):

        # 调用 append 完成 resolve_remote_server_for_task 的当前动作。
        list_attempted_server_ids.append(server_id)

        # 收集 check data、check errors 条目，保持 resolve_remote_server_for_task 的处理顺序稳定。
        tuple_check_data, tuple_check_errors = remote_server_check(path_active_skill_dir, server_id)  # check data、check errors 用于本步治理判断

        # 收集 workspace data、workspace errors 条目，保持 resolve_remote_server_for_task 的处理顺序稳定。
        workspace_data, workspace_errors = remote_server_workspace_check(path_active_skill_dir, server_id) if not tuple_check_errors else ({}, [])  # workspace data、workspace errors 用于本步治理判断

        # 收集 errors 条目，保持 resolve_remote_server_for_task 的处理顺序稳定。
        errors = tuple_check_errors + workspace_errors  # errors 用于本步治理判断

        # 检查 resolve_remote_server_for_task 的当前条件是否需要进入专门分支。
        if errors:

            # 调用 append 完成 resolve_remote_server_for_task 的当前动作。
            list_failures.append(f"{server_id}: {'; '.join(errors)}")

            # 分隔 resolve_remote_server_for_task 的控制流边界。
            continue

        # 返回 resolve_remote_server_for_task 已整理完成的调用载荷。
        return {
            "ok": True,
            "decision": "selected",
            "matched_route": route,
            "selected_server_id": server_id,
            "selected_server": dict_registry.get(server_id, {}),
            "check": tuple_check_data,
            "workspace_check": workspace_data,
            "attempted_server_ids": list_attempted_server_ids,
            "failures": list_failures,
        }

    # 返回 resolve_remote_server_for_task 已整理完成的调用载荷。
    return {
        "ok": False,
        "decision": "blocked",
        "message": "All primary and fallback remote servers for the matched task failed validation.",
        "matched_route": route,
        "attempted_server_ids": list_attempted_server_ids,
        "failures": list_failures,
    }


