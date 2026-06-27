"""校验 AGENTS.md、全局 baseline、治理配置和工作区规则完整性。"""

# 导入 AGENTS 校验依赖。
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

# 导入 AGENTS 校验依赖。
import argparse
import json
import re
from pathlib import Path
import sys

# 整理 模块入口 需要的 dont write bytecode 验证信息。
sys.dont_write_bytecode = True  # AGENTS 校验输入值

# 导入 AGENTS 校验依赖。
from agents_common import (
    SKIP_DIRS,
    decomposition_plan_path,
    emit_json,
    evolution_owner_status,
    global_codex_agents_status,
    inspect_project,

    # 分隔当前密集代码块，保留原有执行顺序。
    load_global_rule_overrides,
    parse_agents_metadata,
    project_profile,
    read_installed_skill_version,
    resolve_project,
    root_agents_sync_command,

    # 再次分隔当前长代码块，降低连续语句密度。
    global_codex_agents_sync_command,
)
from manage_docs import verify_docs
from source_governance import format_source_governance_errors, source_governance_report
from verify_agents_policy import (
    CODING_BEHAVIOR_LANGUAGE_ROUTING_REQUIRED_SNIPPETS,
    COMMAND_RE,
    LANGUAGE_LOCK_RE,
    PATH_RE,
    PLAN_LANGUAGE_LOCK_RE,
    PROJECT_LOCAL_GOVERNANCE_RUNTIME_RE,
    ROOT_AGENTS_MAX_BYTES,
    ROOT_AGENTS_MAX_KB,
    SCRIPT_OUTPUT_POLICY_REQUIRED_SNIPPETS,
)

# 定义 validate_markers  校验入口。
def validate_markers(text: str, file: str, errors: list[str]) -> None:

    # 收集 starts 验证条目。
    starts = len(re.findall(r"AGENTS-GENERATED:START", text))  # AGENTS 校验输入值

    # 收集 ends 验证条目。
    ends = len(re.findall(r"AGENTS-GENERATED:END", text))  # AGENTS 校验输入值

    # 校验 validate_markers 的验证分支条件。
    if starts != ends:

        # 追加 validate_markers 的验证诊断。
        errors.append(f"{file}: generated marker mismatch ({starts} starts, {ends} ends)")

# 定义 section_body  校验入口。
def section_body(text: str, heading: str) -> str | None:

    # 整理 section_body 需要的 match 验证信息。
    match = re.search(rf"^{re.escape(heading)}\s*$", text, flags=re.MULTILINE)  # AGENTS 校验输入值

    # 校验 section_body 的验证分支条件。
    if not match:

        # 返回 section_body 的验证载荷。
        return None

    # 整理 section_body 需要的 start 验证信息。
    start = match.end()  # AGENTS 校验输入值

    # 整理 section_body 需要的 next heading 验证信息。
    next_heading = re.search(r"^##\s+", text[start:], flags=re.MULTILINE)  # 当前段落后的下一个二级标题

    # 整理 section_body 需要的 end 验证信息。
    end = start + next_heading.start() if next_heading else len(text)  # AGENTS 校验输入值

    # 返回 section_body 的验证载荷。
    return text[start:end]

# 定义 first_section_body  校验入口。
def first_section_body(text: str, headings: tuple[str, ...]) -> str | None:

    # 逐项检查可兼容的段落标题。
    for heading in headings:

        # 整理 first_section_body 需要的 body 验证信息。
        body = section_body(text, heading)

        # 校验 first_section_body 的验证分支条件。
        if body is not None:

            # 返回 first_section_body 的验证载荷。
            return body

    # 返回 first_section_body 的验证载荷。
    return None

# 定义 validate_remote_server_contract 的 AGENTS 校验入口。
def validate_remote_server_contract(text: str, file: str, dict_profile: dict[str, Any], errors: list[str]) -> None:
    """校验强控制项目的 Remote Server Contract 渲染内容。

    数组契约:
        shape/维度: 本函数处理 AGENTS 文本和控制档案映射，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 str、dict 和 list 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义来自 remote_server_contract schema。
    """

    # 整理 validate_remote_server_contract 需要的 remote contract 验证信息。
    remote_contract = dict_profile.get("remote_server_contract", {}) if isinstance(dict_profile.get("remote_server_contract", {}), dict) else {}  # AGENTS 校验输入值

    # 校验强控制分支。
    if remote_contract:

        # 整理 validate_remote_server_contract 需要的 remote body 验证信息。
        remote_body = first_section_body(text, ("## Remote Server Contract", "## Task-specific gates"))  # 远程服务器契约段落正文

        # 校验强控制分支。
        if remote_body is None:

            # 追加强控制诊断。
            errors.append(f"{file}: strong-control profile with enabled remote_server_contract requires remote task-specific gates")
        else:

            # 校验强控制分支。
            if remote_contract.get("enabled"):

                # 收集 registry 验证条目。
                list_registry = remote_contract.get("server_registry", [])  # AGENTS 校验输入值

                # 收集 routes 验证条目。
                list_routes = remote_contract.get("task_routes", [])  # AGENTS 校验输入值

                # 校验强控制分支。
                if not isinstance(list_registry, list) or not list_registry:

                    # 追加强控制诊断。
                    errors.append(f"{file}: remote_server_contract.enabled requires server_registry")

                    # 收集 registry 验证条目。
                    list_registry = []  # AGENTS 校验输入值

                # 校验强控制分支。
                if not isinstance(list_routes, list) or not list_routes:

                    # 追加强控制诊断。
                    errors.append(f"{file}: remote_server_contract.enabled requires task_routes")

                    # 收集 routes 验证条目。
                    list_routes = []  # AGENTS 校验输入值

                # 收集 registry ids 验证条目。
                registry_ids = {str(item.get("id", "")).strip() for item in list_registry if isinstance(item, dict) and str(item.get("id", "")).strip()}  # AGENTS 校验输入值

                # 逐项检查强控制候选。
                for route in list_routes:

                    # 校验强控制分支。
                    if not isinstance(route, dict):

                        # 追加强控制诊断。
                        errors.append(f"{file}: remote_server_contract.task_routes must contain objects")

                        # 分隔 validate_remote_server_contract 的控制流边界。
                        continue

                    # 整理 validate_remote_server_contract 需要的 task name 验证信息。
                    task_name = str(route.get("task_name", "")).strip()  # AGENTS 校验输入值

                    # 整理 validate_remote_server_contract 需要的 primary id 验证信息。
                    primary_id = str(route.get("primary_server_id", "")).strip()  # AGENTS 校验输入值

                    # fallback server id 只接受列表，避免字符串被逐字符拆分。
                    raw_fallback_ids = route.get("fallback_server_ids", [])  # 备用服务器原始清单

                    # 列表型 fallback id 做去空白处理后参与路由覆盖检查。
                    if isinstance(raw_fallback_ids, list):

                        # 先创建空清单，再逐项追加去空白后的 fallback id。
                        list_fallback_ids: list[str] = []  # 备用服务器清单

                        # 保持原始顺序，便于错误输出和用户配置顺序一致。
                        for item in raw_fallback_ids:

                            # 每个 fallback id 转成字符串后去掉首尾空白。
                            fallback_id = str(item).strip()  # 备用服务器 id 文本

                            # 空白 fallback id 不参与 registry 覆盖检查。
                            if fallback_id:

                                # 收集有效 fallback id，供后续 registry 覆盖校验。
                                list_fallback_ids.append(fallback_id)
                    else:

                        # 非列表 fallback 输入不参与逐项覆盖检查。
                        list_fallback_ids = []  # 非列表 fallback 输入的空清单

                    # 收集 route tasks 验证条目。
                    route_tasks = route.get("route_tasks", [])  # AGENTS 校验输入值

                    # 校验强控制分支。
                    if not task_name:

                        # 追加强控制诊断。
                        errors.append(f"{file}: remote_server_contract.task_routes requires task_name")

                    # 校验强控制分支。
                    if not primary_id:

                        # 追加强控制诊断。
                        errors.append(f"{file}: remote_server_contract.task_routes requires primary_server_id")

                    # 校验强控制分支。
                    elif primary_id not in registry_ids:

                        # 追加强控制诊断。
                        errors.append(f"{file}: remote_server_contract.task_routes references unknown primary_server_id `{primary_id}`")

                    # 逐项检查强控制候选。
                    for fallback_id in list_fallback_ids:

                        # 校验强控制分支。
                        if fallback_id not in registry_ids:

                            # 追加强控制诊断。
                            errors.append(f"{file}: remote_server_contract.task_routes references unknown fallback_server_id `{fallback_id}`")

                    # 校验强控制分支。
                    if not isinstance(route_tasks, list) or not [str(item).strip() for item in route_tasks if str(item).strip()]:

                        # 追加强控制诊断。
                        errors.append(f"{file}: remote_server_contract.task_routes requires route_tasks")

                # 校验强控制分支。
                if "Route source: `.agents/agents-control.json` field `remote_server_contract`." not in remote_body:

                    # 追加强控制诊断。
                    errors.append(f"{file}: Remote Server Contract must point to `.agents/agents-control.json` remote_server_contract")

                # 校验强控制分支。
                if "Resolve primary and fallback servers from the route source at execution time" not in remote_body:

                    # 追加强控制诊断。
                    errors.append(f"{file}: Remote Server Contract must keep remote routing details in the profile source")

                # 校验强控制分支。
                if "automatically try registered fallback servers in route order" not in remote_body:

                    # 追加强控制诊断。
                    errors.append(f"{file}: Remote Server Contract must enforce automatic fallback routing")

                # 校验强控制分支。
                if "stop and update the current work folder AGENTS.md/profile before continuing" not in remote_body:

                    # 追加强控制诊断。
                    errors.append(f"{file}: Remote Server Contract must enforce unmatched-task blocking")
            else:

                # 禁用远程时根 AGENTS.md 不强制输出负信息。
                pass



# 定义 validate_directory_contract 的 AGENTS 校验入口。
def validate_directory_contract(text: str, file: str, dict_profile: dict[str, Any], errors: list[str]) -> None:
    """校验强控制项目的 Directory Contract 渲染内容。

    数组契约:
        shape/维度: 本函数处理 AGENTS 文本和控制档案映射，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 str、dict 和 list 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义来自 directory_contract schema。
    """

    # 整理 validate_directory_contract 需要的 directory contract 验证信息。
    directory_contract = dict_profile.get("directory_contract", {}) if isinstance(dict_profile.get("directory_contract", {}), dict) else {}  # AGENTS 校验输入值

    # 整理 validate_directory_contract 需要的 directory body 验证信息。
    directory_body = first_section_body(text, ("## Directory Contract", "## Task-specific gates"))  # 目录契约段落正文

    # 校验强控制分支。
    if directory_body is None:

        # 追加强控制诊断。
        errors.append(f"{file}: strong-control profile requires directory task-specific gates")
    else:

        # workspace settings 策略仅接受映射，其他类型按缺省策略处理。
        raw_settings_policy = directory_contract.get("workspace_settings_policy", {})  # settings 策略原始片段

        # 标准化后的 settings 策略供后续必备文本校验复用。
        settings_policy = raw_settings_policy if isinstance(raw_settings_policy, dict) else {}  # settings 策略映射

        # remote environment 策略仅接受映射，防止错误类型绕过校验。
        raw_remote_environment = directory_contract.get("remote_environment_policy", {})  # 远程环境策略原始片段

        # 标准化后的 remote environment 策略用于检查 AGENTS 条款。
        remote_environment = raw_remote_environment if isinstance(raw_remote_environment, dict) else {}  # 远程环境策略映射

        # remote runtime archive 策略仅接受映射，其他类型按空策略处理。
        raw_remote_runtime = directory_contract.get("remote_runtime_archive_policy", {})  # 远程运行时归档策略原始片段

        # 标准化后的 remote runtime 策略用于检查禁用/启用说明。
        remote_runtime = raw_remote_runtime if isinstance(raw_remote_runtime, dict) else {}  # 远程运行时归档策略映射

        # 整理 validate_directory_contract 需要的 settings folder 验证信息。
        settings_folder = str(settings_policy.get("folder", ".settings")).strip() or ".settings"  # AGENTS 校验输入值

        # 整理 validate_directory_contract 需要的 local default 验证信息。
        local_default = str(settings_policy.get("local_default_file", ".settings/project.local.json")).strip() or ".settings/project.local.json"  # AGENTS 校验输入值

        # 整理 validate_directory_contract 需要的 remote default 验证信息。
        remote_default = str(settings_policy.get("remote_default_file", ".settings/project.remote.json")).strip() or ".settings/project.remote.json"  # AGENTS 校验输入值

        # 校验强控制分支。
        if local_default not in directory_body:

            # 追加强控制诊断。
            errors.append(f"{file}: Directory Contract must include local workspace settings path `{local_default}`")

        # 校验强控制分支。
        if remote_default not in directory_body:

            # 追加强控制诊断。
            errors.append(f"{file}: Directory Contract must include remote workspace settings path `{remote_default}`")

        # 校验强控制分支。
        if f"`{settings_folder}/*.local.json`" not in directory_body and f"{settings_folder}/*.local.json" not in directory_body:

            # 追加强控制诊断。
            errors.append(f"{file}: Directory Contract must state that `{settings_folder}/*.local.json` is local-only")

        # 校验强控制分支。
        if "server_list.local.json" not in directory_body:

            # 追加强控制诊断。
            errors.append(f"{file}: Directory Contract must explicitly forbid copying server_list.local.json to remote servers")

        # compact root 只要求目录变更入口和主工程边界，不再内联完整目录数据库。
        primary_root = str(directory_contract.get("primary_project_root", "")).strip().rstrip("/")  # AGENTS 校验输入值
        if primary_root and primary_root not in directory_body:

            # 追加强控制诊断。
            errors.append(f"{file}: directory gates must include primary project root `{primary_root}`")

        # 校验强控制分支。
        if "manage_dirs.py" not in directory_body or "review" not in directory_body:

            # 追加强控制诊断。
            errors.append(f"{file}: directory gates must include directory review command")

        # 校验强控制分支。
        if remote_environment.get("status") == "enabled":

            # 定位 template 的文件边界，供 validate_directory_contract 后续读写校验使用。
            path_template = str(remote_environment.get("path_template", "")).strip()  # AGENTS 校验输入值

            # 校验强控制分支。
            if not path_template:

                # 追加强控制诊断。
                errors.append(f"{file}: directory_contract.remote_environment_policy.path_template must be configured when enabled")

        # 校验强控制分支。
        if remote_runtime.get("status") == "enabled":

            # 定位 active path 的文件边界，供 validate_directory_contract 后续读写校验使用。
            active_path = str(remote_runtime.get("active_path_template", "")).strip()  # AGENTS 校验输入值

            # 定位 backup path 的文件边界，供 validate_directory_contract 后续读写校验使用。
            backup_path = str(remote_runtime.get("backup_path_template", "")).strip()  # AGENTS 校验输入值

            # 整理 validate_directory_contract 需要的 trigger 验证信息。
            trigger = str(remote_runtime.get("archive_trigger", "")).strip()  # AGENTS 校验输入值

            # 校验强控制分支。
            if not active_path:

                # 追加强控制诊断。
                errors.append(f"{file}: directory_contract.remote_runtime_archive_policy.active_path_template must be configured when enabled")

            # 校验强控制分支。
            if not backup_path:

                # 追加强控制诊断。
                errors.append(f"{file}: directory_contract.remote_runtime_archive_policy.backup_path_template must be configured when enabled")

            # 校验强控制分支。
            if not trigger:

                # 追加强控制诊断。
                errors.append(f"{file}: directory_contract.remote_runtime_archive_policy.archive_trigger must be configured when enabled")

        # 校验强控制分支。
        if remote_environment.get("status") == "enabled" or remote_runtime.get("status") == "enabled":

            # 校验强控制分支。
            if "docs/dir_manager/planned_structure.json" not in directory_body:

                # 追加强控制诊断。
                errors.append(f"{file}: Directory Contract must point remote deployment policy to `docs/dir_manager/planned_structure.json`")



# 定义 validate_strong_control  校验入口。
def validate_strong_control(text: str, file: str, project: Path, errors: list[str]) -> None:

    # 收集 required sections 验证条目。
    list_required_sections = [  # AGENTS 校验输入值
        "## Project",  # compact 根项目身份段落标题
        "## Task-specific gates",  # compact 根阻断入口段落标题
        "## Local conventions",  # compact 根本地约定段落标题
        "## Read before changing",  # compact 根阅读入口段落标题
    ]

    # 校验强控制分支。
    if "Strong control: complete" not in text:

        # 返回 validate_strong_control 的验证载荷。
        return

    # 逐项检查强控制候选。
    for section in list_required_sections:

        # 校验强控制分支。
        if section not in text:

            # 追加强控制诊断。
            errors.append(f"{file}: missing strong-control section {section}")

    # 校验强控制分支。
    if not (project / ".agents" / "agents-control.json").exists():

        # 追加强控制诊断。
        errors.append(f"{file}: strong control requires .agents/agents-control.json")

    # 整理 validate_strong_control 需要的 docs result 验证信息。
    docs_result = verify_docs(project)  # AGENTS 校验输入值

    # 调用 extend 处理 validate_strong_control。
    errors.extend(f"{file}: {item}" for item in docs_result["errors"])

    # 保存 profile 映射，维持 validate_strong_control 的字段关系。
    dict_profile = read_json(project / ".agents" / "agents-control.json")  # AGENTS 校验输入值

    # 校验强控制分支。
    if not str(dict_profile.get("default_conversation_language", "")).strip():

        # 追加强控制诊断。
        errors.append(f"{file}: strong-control profile must explicitly set default_conversation_language")

    # 整理 validate_strong_control 需要的 memory contract 验证信息。
    memory_contract = dict_profile.get("memory_contract", {}) if isinstance(dict_profile.get("memory_contract", {}), dict) else {}  # AGENTS 校验输入值

    # 标记 memory enabled 判断，控制 validate_strong_control 的分支走向。
    bool_memory_enabled = bool(memory_contract.get("enabled", dict_profile.get("memory_enabled", False)))  # AGENTS 校验输入值

    # 校验强控制分支。
    if bool_memory_enabled:

        # 校验强控制分支。
        if "## Memory Contract" not in text and "## Task-specific gates" not in text:

            # 追加强控制诊断。
            errors.append(f"{file}: missing memory task-specific gates")

        # 整理 validate_strong_control 需要的 memory body 验证信息。
        memory_body = first_section_body(text, ("## Memory Contract", "## Task-specific gates")) or ""  # memory 契约段落正文

        # 校验强控制分支。
        if "docs/memory/MEMORY.md" not in memory_body:

            # 追加强控制诊断。
            errors.append(f"{file}: Memory Contract must point to docs/memory/MEMORY.md")

        # 校验强控制分支。
        if "memory-read" not in memory_body:

            # 追加强控制诊断。
            errors.append(f"{file}: Memory Contract must include memory-read guidance")

        # 校验强控制分支。
        if "memory-gate" not in memory_body:

            # 追加强控制诊断。
            errors.append(f"{file}: Memory Contract must include memory-gate guidance")

        # 校验强控制分支。
        if "memory-bootstrap-sessions" not in memory_body:

            # 追加强控制诊断。
            errors.append(f"{file}: Memory Contract must include exact-cwd session bootstrap guidance")

    # 收集 extra requirements 验证条目。
    extra_requirements = str(dict_profile.get("extra_requirements", "")).strip()  # AGENTS 校验输入值

    # 校验强控制分支。
    if extra_requirements and extra_requirements.casefold() != "none" and extra_requirements not in text:

        # 追加强控制诊断。
        errors.append(f"{file}: Control Profile must render extra_requirements from .agents/agents-control.json")

    # 校验目录契约段落，保持 directory_contract 与 AGENTS 渲染一致。
    validate_directory_contract(text, file, dict_profile, errors)

    # 校验远程服务器契约段落，保持 remote_server_contract 与 AGENTS 渲染一致。
    validate_remote_server_contract(text, file, dict_profile, errors)

    # 整理 validate_strong_control 需要的 git management 验证信息。
    git_management = str(dict_profile.get("git_management", "")).strip()  # AGENTS 校验输入值

    # 校验强控制分支。
    if git_management in {"yes-local-only", "remote-allowed"}:

        # 整理 validate_strong_control 需要的 release body 验证信息。
        release_body = first_section_body(text, ("## Release Contract", "## Task-specific gates"))  # release 契约段落正文

        # 校验强控制分支。
        if release_body is None:

            # 追加强控制诊断。
            errors.append(f"{file}: git-managed strong-control project requires ## Release Contract")

        # 校验强控制分支。
        elif "core.worktree" not in release_body or "Do not repoint repositories" not in release_body:

            # 追加强控制诊断。
            errors.append(f"{file}: Release Contract must explicitly forbid `git config core.worktree` for git-managed workflows")
        else:

            # 收集 release compact 入口规则，避免根 AGENTS.md 内联完整发布清单。
            tuple_release_required_phrases = (  # AGENTS 校验输入值
                ".agents/agents-control.json",  # AGENTS 校验输入值
                "docs/git_manager/",  # AGENTS 校验输入值
                "script-guide",  # AGENTS 校验输入值
                "RELEASE_RECEIPT.json",  # AGENTS 校验输入值
                "source directory installs are forbidden",  # AGENTS 校验输入值
                "Different-version release directories and matching zip files are immutable history",  # AGENTS 校验输入值
            )

            # 逐项检查 compact release 入口规则。
            for phrase in tuple_release_required_phrases:

                # 校验强控制分支。
                if phrase not in release_body:

                    # 追加强控制诊断。
                    errors.append(f"{file}: Release Contract must include compact release governance phrase `{phrase}`")

    # 校验强控制分支。
    if dict_profile.get("kind") == "skill":

        # 整理 validate_strong_control 需要的 contract body 验证信息。
        contract_body = first_section_body(text, ("## Skill Design Contract", "## Task-specific gates"))  # skill 设计契约段落正文

        # 校验强控制分支。
        if contract_body is None:

            # 追加强控制诊断。
            errors.append(f"{file}: strong-control skill project requires ## Skill Design Contract")

            # 返回 validate_strong_control 的验证载荷。
            return

        # 收集 required phrases 验证条目。
        list_required_phrases = [  # AGENTS 校验输入值
            "Validation gates:",  # AGENTS 校验输入值
            "Forward testing:",  # AGENTS 校验输入值
        ]

        # 逐项检查强控制候选。
        for phrase in list_required_phrases:

            # 校验强控制分支。
            if phrase not in contract_body:

                # 追加强控制诊断。
                errors.append(f"{file}: Skill Design Contract missing {phrase}")

        # 收集 vague markers 验证条目。
        list_vague_markers = [  # AGENTS 校验输入值
            "Trigger scenarios: not specified",  # AGENTS 校验输入值
            "Design patterns: not specified",  # AGENTS 校验输入值
            "Resource boundaries: not specified",  # AGENTS 校验输入值
            "Progressive disclosure: not specified",  # AGENTS 校验输入值
            "Validation gates: not specified",  # AGENTS 校验输入值
            "Forward testing: not specified",  # AGENTS 校验输入值
        ]

        # 逐项检查强控制候选。
        for marker in list_vague_markers:

            # 校验强控制分支。
            if marker in contract_body:

                # 追加强控制诊断。
                errors.append(f"{file}: Skill Design Contract contains unresolved default: {marker}")

        # 整理 validate_strong_control 需要的 gates match 验证信息。
        gates_match = re.search(r"Validation gates:\s*(.+)", contract_body, flags=re.IGNORECASE)  # AGENTS 校验输入值

        # 整理 validate_strong_control 需要的 gates text 验证信息。
        gates_text = gates_match.group(1).lower() if gates_match else ""  # AGENTS 校验输入值

        # 逐项检查强控制候选。
        for required_gate in ("quick_validate", "audit", "verify"):

            # 校验强控制分支。
            if required_gate not in gates_text:

                # 追加强控制诊断。
                errors.append(f"{file}: Skill Design Contract validation gates must include {required_gate}")

    # 整理 validate_strong_control 需要的 config 验证信息。
    config = load_global_rule_overrides(project, dict_profile)  # AGENTS 校验输入值

    # 定位 config path 的文件边界，供 validate_strong_control 后续读写校验使用。
    config_path = config["path"].relative_to(project).as_posix()  # AGENTS 校验输入值

    # 校验强控制分支。
    if config_path not in text:

        # 追加强控制诊断。
        errors.append(f"{file}: strong-control root must reference local governance config `{config_path}`")

    # 校验强控制分支。
    if not config["exists"]:

        # 追加强控制诊断。
        errors.append(f"{file}: missing local governance config `{config_path}`")

    # 逐项检查强控制候选。
    for item in config["errors"]:

        # 追加强控制诊断。
        errors.append(f"{file}: invalid local governance config `{config_path}`: {item}")

    # 收集 forbidden snippets 验证条目。
    tuple_forbidden_snippets = (  # AGENTS 校验输入值
        "Single-file maintainability",  # AGENTS 校验输入值
        "docs/development/decomposition-plans/",  # AGENTS 校验输入值
        ".agents/script-governance-exceptions.json",  # AGENTS 校验输入值
        "Project tool scripts must live under",  # AGENTS 校验输入值
        "scripts/<family>/<function>/<name>.<ext>",  # AGENTS 校验输入值
    )

    # 逐项检查强控制候选。
    for snippet in tuple_forbidden_snippets:

        # 校验强控制分支。
        if snippet in text:

            # 追加强控制诊断。
            errors.append(f"{file}: local rule detail must move to JSON config instead of AGENTS text ({snippet})")

# 定义 validate_coding_behavior_language_routing 校验入口。
def validate_coding_behavior_language_routing(text: str, file: str, project: Path, profile: dict, errors: list[str]) -> bool:

    # 旧可见段落已退休，新生成根文件不得继续暴露该概念。
    if section_body(text, "## Code Comment Policy") is not None:
        errors.append(f"{file}: retired Code Comment Policy section must move to Coding Behavior Baseline language skill routing")
        return False

    # 整理 validate_coding_behavior_language_routing 需要的 body 验证信息。
    body = first_section_body(text, ("## Coding Behavior Baseline", "## Local conventions"))  # 编码行为段落正文
    if body is None:
        body = section_body(text, "## Local conventions")

    # 校验 validate_coding_behavior_language_routing 的验证分支条件。
    if body is None:

        # 追加 validate_coding_behavior_language_routing 的验证诊断。
        errors.append(f"{file}: missing language skill routing in Coding Behavior Baseline or Local conventions; refresh the managed root AGENTS.md")

        # 返回 validate_coding_behavior_language_routing 的验证载荷。
        return False

    # 标记 ok 判断，控制 validate_coding_behavior_language_routing 的分支走向。
    bool_ok = True  # AGENTS 校验输入值

    # 逐项检查 validate_coding_behavior_language_routing 验证候选。
    for snippet in CODING_BEHAVIOR_LANGUAGE_ROUTING_REQUIRED_SNIPPETS:

        # 校验 validate_coding_behavior_language_routing 的验证分支条件。
        if snippet not in body:

            # 追加 validate_coding_behavior_language_routing 的验证诊断。
            errors.append(f"{file}: Coding Behavior Baseline language skill routing missing required rule `{snippet}`")

            # 标记 ok 判断，控制 validate_coding_behavior_language_routing 的分支走向。
            bool_ok = False  # AGENTS 校验输入值

    # 整理 validate_coding_behavior_language_routing 需要的 config 验证信息。
    config = load_global_rule_overrides(project, profile)  # AGENTS 校验输入值

    # 定位 config path 的文件边界，供 validate_coding_behavior_language_routing 后续读写校验使用。
    config_path = config["path"].relative_to(project).as_posix()  # AGENTS 校验输入值

    # 校验 validate_coding_behavior_language_routing 的验证分支条件。
    if config_path in body:

        # 校验 validate_coding_behavior_language_routing 的验证分支条件。
        if not config["exists"]:

            # 追加 validate_coding_behavior_language_routing 的验证诊断。
            errors.append(f"{file}: missing local coding behavior config `{config_path}`")

            # 标记 ok 判断，控制 validate_coding_behavior_language_routing 的分支走向。
            bool_ok = False  # AGENTS 校验输入值

        # 逐项检查 validate_coding_behavior_language_routing 验证候选。
        for item in config["errors"]:

            # 校验 validate_coding_behavior_language_routing 的验证分支条件。
            if "coding_behavior" in item:

                # 追加 validate_coding_behavior_language_routing 的验证诊断。
                errors.append(f"{file}: invalid Coding Behavior Baseline language skill routing config `{config_path}`: {item}")

                # 标记 ok 判断，控制 validate_coding_behavior_language_routing 的分支走向。
                bool_ok = False  # AGENTS 校验输入值

    # 返回 validate_coding_behavior_language_routing 的验证载荷。
    return bool_ok

# 定义 validate_script_output_policy  校验入口。
def validate_script_output_policy(text: str, file: str, project: Path, profile: dict, errors: list[str]) -> bool:

    # 整理 validate_script_output_policy 需要的 body 验证信息。
    body = first_section_body(text, ("## Script Output Policy", "## Local conventions"))  # 脚本输出策略段落正文
    if body is None:
        body = section_body(text, "## Local conventions")

    # 校验 validate_script_output_policy 的验证分支条件。
    if body is None:

        # 追加 validate_script_output_policy 的验证诊断。
        errors.append(f"{file}: missing script output policy in Local conventions; refresh the managed root AGENTS.md")

        # 返回 validate_script_output_policy 的验证载荷。
        return False

    # 标记 ok 判断，控制 validate_script_output_policy 的分支走向。
    bool_ok = True  # AGENTS 校验输入值

    # 逐项检查 validate_script_output_policy 验证候选。
    for snippet in SCRIPT_OUTPUT_POLICY_REQUIRED_SNIPPETS:

        # 校验 validate_script_output_policy 的验证分支条件。
        if snippet not in body:

            # 追加 validate_script_output_policy 的验证诊断。
            errors.append(f"{file}: Script Output Policy missing required rule `{snippet}`")

            # 标记 ok 判断，控制 validate_script_output_policy 的分支走向。
            bool_ok = False  # AGENTS 校验输入值

    # 整理 validate_script_output_policy 需要的 config 验证信息。
    config = load_global_rule_overrides(project, profile)  # AGENTS 校验输入值

    # 定位 config path 的文件边界，供 validate_script_output_policy 后续读写校验使用。
    config_path = config["path"].relative_to(project).as_posix()  # AGENTS 校验输入值

    # 校验 validate_script_output_policy 的验证分支条件。
    if config_path in body:

        # 校验 validate_script_output_policy 的验证分支条件。
        if not config["exists"]:

            # 追加 validate_script_output_policy 的验证诊断。
            errors.append(f"{file}: missing local script output policy config `{config_path}`")

            # 标记 ok 判断，控制 validate_script_output_policy 的分支走向。
            bool_ok = False  # AGENTS 校验输入值

        # 逐项检查 validate_script_output_policy 验证候选。
        for item in config["errors"]:

            # 校验 validate_script_output_policy 的验证分支条件。
            if "script_output_policy" in item:

                # 追加 validate_script_output_policy 的验证诊断。
                errors.append(f"{file}: invalid script output policy config `{config_path}`: {item}")

                # 标记 ok 判断，控制 validate_script_output_policy 的分支走向。
                bool_ok = False  # AGENTS 校验输入值

    # 返回 validate_script_output_policy 的验证载荷。
    return bool_ok

# 定义 is_path_reference  校验入口。
def is_path_reference(raw: str) -> bool:

    # 校验 is_path_reference 的验证分支条件。
    if raw.startswith(("http://", "https://", "mailto:")):

        # 返回 is_path_reference 的验证载荷。
        return False

    # 校验 is_path_reference 的验证分支条件。
    if raw in {"AGENTS.md", "CLAUDE.md", "GEMINI.md"}:

        # 返回 is_path_reference 的验证载荷。
        return False

    # 校验 is_path_reference 的验证分支条件。
    if any(char.isspace() for char in raw):

        # 返回 is_path_reference 的验证载荷。
        return False

    # 校验 is_path_reference 的验证分支条件。
    if any(char in raw for char in "*?<>|,"):

        # 返回 is_path_reference 的验证载荷。
        return False

    # 返回 is_path_reference 的验证载荷。
    return True

# 定义 is_expected_contract_example_path  校验入口。
def is_expected_contract_example_path(raw: str, profile: dict[str, Any]) -> bool:

    # 整理 is_expected_contract_example_path 需要的 directory contract 验证信息。
    directory_contract = profile.get("directory_contract", {}) if isinstance(profile.get("directory_contract", {}), dict) else {}  # AGENTS 校验输入值

    # 整理 is_expected_contract_example_path 需要的 settings policy 验证信息。
    settings_policy = (  # AGENTS 校验输入值
        directory_contract.get("workspace_settings_policy", {})  # AGENTS 校验输入值
        if isinstance(directory_contract.get("workspace_settings_policy", {}), dict)  # AGENTS 校验输入值
        else {}  # AGENTS 校验输入值
    )

    # 整理 is_expected_contract_example_path 需要的 settings folder 验证信息。
    settings_folder = str(settings_policy.get("folder", ".settings")).strip() or ".settings"  # AGENTS 校验输入值

    # 整理 is_expected_contract_example_path 需要的 local default 验证信息。
    local_default = str(settings_policy.get("local_default_file", f"{settings_folder}/project.local.json")).strip()  # AGENTS 校验输入值

    # 整理 is_expected_contract_example_path 需要的 remote default 验证信息。
    remote_default = str(settings_policy.get("remote_default_file", f"{settings_folder}/project.remote.json")).strip()  # AGENTS 校验输入值

    # 收集 allowed examples 验证条目。
    set_allowed_examples = {  # AGENTS 校验输入值
        local_default or f"{settings_folder}/project.local.json",  # AGENTS 校验输入值
        remote_default or f"{settings_folder}/project.remote.json",  # AGENTS 校验输入值
        f"{settings_folder}/server_list.local.json",  # AGENTS 校验输入值
        ".local.json",  # AGENTS 校验输入值
        ".remote.json",  # AGENTS 校验输入值
        "RELEASE_RECEIPT.json",  # AGENTS 校验输入值
    }

    # 返回 is_expected_contract_example_path 的验证载荷。
    return raw in set_allowed_examples

# 定义 read_json  校验入口。
def read_json(path: Path) -> dict:

    # 保护 read_json 中允许失败的外部访问。
    try:

        # 返回 read_json 的验证载荷。
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:

        # 返回 read_json 的验证载荷。
        return {}

# 定义 make_targets  校验入口。
def make_targets(root: Path) -> set[str]:

    # 整理 make_targets 需要的 path 验证信息。
    path = root / "Makefile"  # AGENTS 校验输入值

    # 校验 make_targets 的验证分支条件。
    if not path.exists():

        # 返回 make_targets 的验证载荷。
        return set()

    # 整理 make_targets 需要的 text 验证信息。
    text = path.read_text(encoding="utf-8", errors="ignore")  # AGENTS 校验输入值

    # 返回 make_targets 的验证载荷。
    return set(re.findall(r"^([A-Za-z0-9_.-]+):", text, flags=re.MULTILINE))

# 定义 package_scripts  校验入口。
def package_scripts(root: Path) -> set[str]:

    # 保存 package 映射，维持 package_scripts 的字段关系。
    dict_package = read_json(root / "package.json")  # AGENTS 校验输入值

    # 收集 scripts 验证条目。
    scripts = dict_package.get("scripts", {}) if isinstance(dict_package.get("scripts"), dict) else {}  # AGENTS 校验输入值

    # 返回 package_scripts 的验证载荷。
    return set(scripts)

# 定义 composer_scripts  校验入口。
def composer_scripts(root: Path) -> set[str]:

    # 保存 composer 映射，维持 composer_scripts 的字段关系。
    dict_composer = read_json(root / "composer.json")  # AGENTS 校验输入值

    # 收集 scripts 验证条目。
    scripts = dict_composer.get("scripts", {}) if isinstance(dict_composer.get("scripts"), dict) else {}  # AGENTS 校验输入值

    # 返回 composer_scripts 的验证载荷。
    return set(scripts)

# 定义 config_backed_command_error  校验入口。
def config_backed_command_error(command: str, project: Path) -> str | None:

    # 收集 tokens 验证条目。
    tokens = command.split()  # AGENTS 校验输入值

    # 校验配置命令分支。
    if not tokens:

        # 返回配置命令诊断。
        return None

    # 校验配置命令分支。
    if tokens[0] == "make" and len(tokens) >= 2:

        # 校验配置命令分支。
        if tokens[1] not in make_targets(project):

            # 返回配置命令诊断。
            return f"documented command `{command}` references missing Makefile target `{tokens[1]}`"

    # 校验配置命令分支。
    if tokens[0] in {"npm", "pnpm", "yarn", "bun"}:

        # 收集 scripts 验证条目。
        set_scripts = package_scripts(project)  # AGENTS 校验输入值

        # 校验配置命令分支。
        if not set_scripts:

            # 返回配置命令诊断。
            return None

        # 校验配置命令分支。
        if tokens[0] in {"pnpm", "yarn"} and len(tokens) >= 2 and tokens[1] in {"dlx", "exec", "install", "add", "remove"}:

            # 返回配置命令诊断。
            return None

        # 校验配置命令分支。
        if tokens[0] == "bun" and len(tokens) >= 2 and tokens[1] in {"x", "install", "add", "remove"}:

            # 返回配置命令诊断。
            return None

        # 校验配置命令分支。
        if tokens[0] == "npm" and len(tokens) >= 3 and tokens[1] == "run":

            # 整理 config_backed_command_error 需要的 script 验证信息。
            str_script = tokens[2]  # AGENTS 校验输入值

        # 校验配置命令分支。
        elif tokens[0] == "npm" and len(tokens) >= 2 and tokens[1] == "test":

            # 整理 config_backed_command_error 需要的 script 验证信息。
            str_script = "test"  # AGENTS 校验输入值

        # 校验配置命令分支。
        elif tokens[0] == "bun" and len(tokens) >= 3 and tokens[1] == "run":

            # 整理 config_backed_command_error 需要的 script 验证信息。
            str_script = tokens[2]  # AGENTS 校验输入值

        # 校验配置命令分支。
        elif len(tokens) >= 2:

            # 整理 config_backed_command_error 需要的 script 验证信息。
            str_script = tokens[1]  # AGENTS 校验输入值
        else:

            # 返回配置命令诊断。
            return None

        # 校验配置命令分支。
        if str_script not in set_scripts:

            # 返回配置命令诊断。
            return f"documented command `{command}` references missing package.json script `{str_script}`"

    # 校验配置命令分支。
    if tokens[0] == "composer" and len(tokens) >= 3 and tokens[1] == "run":

        # 收集 scripts 验证条目。
        set_scripts = composer_scripts(project)  # AGENTS 校验输入值

        # 校验配置命令分支。
        if set_scripts and tokens[2] not in set_scripts:

            # 返回配置命令诊断。
            return f"documented command `{command}` references missing composer.json script `{tokens[2]}`"

    # 返回配置命令诊断。
    return None

# 定义 documented_script_path_error  校验入口。
def documented_script_path_error(command: str, project: Path) -> str | None:

    # 收集 tokens 验证条目。
    tokens = command.split()  # AGENTS 校验输入值

    # 校验 documented_script_path_error 的验证分支条件。
    if len(tokens) < 2 or tokens[0] != "python":

        # 返回 documented_script_path_error 的验证载荷。
        return None

    # 校验 documented_script_path_error 的验证分支条件。
    if tokens[1].startswith("<codex-home>/"):

        # 返回 documented_script_path_error 的验证载荷。
        return None

    # 整理 documented_script_path_error 需要的 candidate 验证信息。
    candidate = project / tokens[1]  # AGENTS 校验输入值

    # 校验 documented_script_path_error 的验证分支条件。
    if tokens[1].endswith(".py") and not candidate.exists():

        # 返回 documented_script_path_error 的验证载荷。
        return f"documented command `{command}` references missing script `{tokens[1]}`"

    # 返回 documented_script_path_error 的验证载荷。
    return None

# 定义 validate_governance_runtime_commands  校验入口。
def validate_governance_runtime_commands(
    text: str,
    file: str,
    project: Path,
    installed_skill_dir_override: str | Path | None,
    errors: list[str],
) -> None:

    # 收集 owner status 验证条目。
    owner_status = evolution_owner_status(project, override_dir=installed_skill_dir_override)  # AGENTS 校验输入值

    # 校验 validate_governance_runtime_commands 的验证分支条件。
    if owner_status.get("enabled"):

        # 返回 validate_governance_runtime_commands 的验证载荷。
        return

    # 逐项检查 validate_governance_runtime_commands 验证候选。
    for match in PROJECT_LOCAL_GOVERNANCE_RUNTIME_RE.finditer(text):

        # 追加 validate_governance_runtime_commands 的验证诊断。
        errors.append(
            (
                f"{file}: project-local governance runtime command is forbidden for non-owner "  # AGENTS 长文本片段
                f"repositories; use installed agents-md-generator runtime instead "  # AGENTS 长文本片段
                f"({match.group(0)})"  # AGENTS 长文本片段
            )
        )

# 定义 validate_decomposition_plan  校验入口。
def validate_decomposition_plan(project: Path, relative_path: str, profile: dict | None = None) -> list[str]:

    # 定位 plan path 的文件边界，供 validate_decomposition_plan 后续读写校验使用。
    plan_path = decomposition_plan_path(project, relative_path, profile)  # AGENTS 校验输入值

    # 校验 validate_decomposition_plan 的验证分支条件。
    if not plan_path.is_file():

        # 返回 validate_decomposition_plan 的验证载荷。
        return [f"oversized source file `{relative_path}` requires decomposition plan `{plan_path.relative_to(project).as_posix()}`"]

    # 整理 validate_decomposition_plan 需要的 text 验证信息。
    text = plan_path.read_text(encoding="utf-8", errors="ignore")  # AGENTS 校验输入值

    # 收集 required sections 验证条目。
    required_sections = load_global_rule_overrides(project, profile)["data"]["source_file_limits"].get("required_plan_sections", [])  # AGENTS 校验输入值

    # 整理 validate_decomposition_plan 需要的 missing 验证信息。
    missing = [section for section in required_sections if f"## {section}" not in text]  # 缺失分解计划章节

    # 校验 validate_decomposition_plan 的验证分支条件。
    if missing:

        # 返回 validate_decomposition_plan 的验证载荷。
        return [f"{plan_path.relative_to(project).as_posix()}: missing decomposition plan sections {missing}"]

    # 返回 validate_decomposition_plan 的验证载荷。
    return []

# 定义 should_skip  校验入口。
def should_skip(path: Path, project: Path, include_skipped: bool = False) -> bool:

    # 校验 should_skip 的验证分支条件。
    if include_skipped:

        # 返回 should_skip 的验证载荷。
        return False

    # 保护 should_skip 中允许失败的外部访问。
    try:

        # 收集 parts 验证条目。
        parts = path.relative_to(project).parts  # AGENTS 校验输入值
    except ValueError:

        # 收集 parts 验证条目。
        parts = path.parts  # AGENTS 校验输入值

    # 返回 should_skip 的验证载荷。
    return bool(set(parts) & SKIP_DIRS)

# 定义 verify  校验入口。
def verify(project: Path, include_skipped: bool = False, installed_skill_dir_override: str | Path | None = None) -> dict:

    # 收集 errors 验证条目。
    list_errors: list[str] = []  # AGENTS 校验输入值

    # 收集 warnings 验证条目。
    list_warnings: list[str] = []  # AGENTS 校验输入值

    # 收集 checked 验证条目。
    list_checked: list[str] = []  # AGENTS 校验输入值

    # 整理 verify 需要的 profile 验证信息。
    profile = project_profile(project)  # AGENTS 校验输入值

    # 收集 facts 验证条目。
    facts = inspect_project(project)  # AGENTS 校验输入值

    # 整理 verify 需要的 installed version 验证信息。
    installed_version = read_installed_skill_version(override_dir=installed_skill_dir_override)  # AGENTS 校验输入值

    # 整理 verify 需要的 root repair command 验证信息。
    root_repair_command = root_agents_sync_command(project, profile, installed_skill_dir_override)  # AGENTS 校验输入值

    # 逐项检查 verify 验证候选。
    for agents in sorted(project.rglob("AGENTS.md")):

        # 校验总体验证分支。
        if should_skip(agents, project, include_skipped):

            # 分隔 verify 的控制流边界。
            continue

        # 追加总体验证诊断。
        list_checked.append(str(agents.relative_to(project).as_posix()))

        # 整理 verify 需要的 text 验证信息。
        text = agents.read_text(encoding="utf-8", errors="ignore")  # AGENTS 校验输入值

        # 校验总体验证分支。
        if agents == project / "AGENTS.md":

            # 标记根元数据修复分支。
            bool_root_metadata_repair_required = False  # AGENTS 校验输入值

            # 整理 verify 需要的 size 验证信息。
            size = len(text.encode("utf-8"))  # AGENTS 校验输入值

            # 校验总体验证分支。
            if size > ROOT_AGENTS_MAX_BYTES:

                # 追加总体验证诊断。
                list_errors.append(f"{list_checked[-1]}: exceeds {ROOT_AGENTS_MAX_KB}KB limit ({size} bytes)")

            # 整理 verify 需要的 managed root 验证信息。
            managed_root = "Managed by agent:" in text or (project / ".agents" / "agents-control.json").exists()  # AGENTS 校验输入值

            # 校验总体验证分支。
            if managed_root:

                # 整理 verify 需要的 metadata 验证信息。
                metadata = parse_agents_metadata(text)  # AGENTS 校验输入值

                # 校验总体验证分支。
                if not metadata.get("agents_version") or not metadata.get("generator_version"):

                    # 追加总体验证诊断。
                    list_errors.append("AGENTS.md: missing AGENTS metadata version")

                    # 标记根元数据修复分支。
                    bool_root_metadata_repair_required = True  # AGENTS 校验输入值

                # 校验总体验证分支。
                if not metadata.get("agents_version"):

                    # 追加总体验证诊断。
                    list_errors.append("AGENTS.md: missing agents version metadata")

                    # 标记根元数据修复分支。
                    bool_root_metadata_repair_required = True  # AGENTS 校验输入值

                # 校验总体验证分支。
                if not metadata.get("generator_version"):

                    # 追加总体验证诊断。
                    list_errors.append("AGENTS.md: missing generator version metadata")

                    # 标记根元数据修复分支。
                    bool_root_metadata_repair_required = True  # AGENTS 校验输入值

                # 校验总体验证分支。
                if installed_version:

                    # 校验总体验证分支。
                    if metadata.get("agents_version") and metadata.get("agents_version") != installed_version:

                        # 追加总体验证诊断。
                        list_errors.append(
                            (
                                f"AGENTS.md: agents version {metadata.get('agents_version')} does not match "  # AGENTS 长文本片段
                                f"installed agents-md-generator version {installed_version}"  # AGENTS 长文本片段
                            )
                        )

                        # 标记根元数据修复分支。
                        bool_root_metadata_repair_required = True  # AGENTS 校验输入值

                    # 校验总体验证分支。
                    if metadata.get("generator_version") and metadata.get("generator_version") != installed_version:

                        # 追加总体验证诊断。
                        list_errors.append(
                            (
                                f"AGENTS.md: generator version {metadata.get('generator_version')} does not "  # AGENTS 长文本片段
                                f"match installed agents-md-generator version {installed_version}"  # AGENTS 长文本片段
                            )
                        )

                        # 标记根元数据修复分支。
                        bool_root_metadata_repair_required = True  # AGENTS 校验输入值
                else:

                    # 追加总体验证诊断。
                    list_errors.append("AGENTS.md: installed agents-md-generator version is unavailable")

                # 校验总体验证分支。
                if not metadata.get("default_language"):

                    # 追加总体验证诊断。
                    list_errors.append("AGENTS.md: missing default language metadata")

                    # 标记根元数据修复分支。
                    bool_root_metadata_repair_required = True  # AGENTS 校验输入值

                # 校验总体验证分支。
                elif not LANGUAGE_LOCK_RE.search(text):

                    # 追加总体验证诊断。
                    list_errors.append("AGENTS.md: missing enforced default-language reply rule")

                    # 标记根元数据修复分支。
                    bool_root_metadata_repair_required = True  # AGENTS 校验输入值

                # 校验总体验证分支。
                elif not PLAN_LANGUAGE_LOCK_RE.search(text):

                    # 追加总体验证诊断。
                    list_errors.append("AGENTS.md: missing enforced Plan Mode default-language rule")

                    # 标记根元数据修复分支。
                    bool_root_metadata_repair_required = True  # AGENTS 校验输入值

                # 校验总体验证分支。
                if not validate_coding_behavior_language_routing(text, list_checked[-1], project, profile, list_errors):

                    # 标记根元数据修复分支。
                    bool_root_metadata_repair_required = True  # AGENTS 校验输入值

                # 校验总体验证分支。
                if not validate_script_output_policy(text, list_checked[-1], project, profile, list_errors):

                    # 标记根元数据修复分支。
                    bool_root_metadata_repair_required = True  # AGENTS 校验输入值

                # 校验总体验证分支。
                if bool_root_metadata_repair_required:

                    # 追加总体验证诊断。
                    list_errors.append(f"AGENTS.md: run `{root_repair_command}` to refresh root metadata before continuing")

        # 调用 validate_governance_runtime_commands 处理 verify。
        validate_governance_runtime_commands(text, list_checked[-1], project, installed_skill_dir_override, list_errors)

        # 调用 validate_markers 处理 verify。
        validate_markers(text, list_checked[-1], list_errors)

        # 调用 validate_strong_control 处理 verify。
        validate_strong_control(text, list_checked[-1], project, list_errors)

        # 校验总体验证分支。
        if "{{" in text or "}}" in text:

            # 追加总体验证诊断。
            list_errors.append(f"{list_checked[-1]}: unresolved template placeholder")

        # 校验总体验证分支。
        if "Precedence" not in text and agents == project / "AGENTS.md":

            # 追加总体验证诊断。
            list_errors.append("AGENTS.md: missing precedence statement")

        # 逐项检查 verify 验证候选。
        for match in PATH_RE.finditer(text):

            # 整理 verify 需要的 raw 验证信息。
            raw = match.group(1).strip()  # AGENTS 校验输入值

            # 校验总体验证分支。
            if not is_path_reference(raw):

                # 分隔 verify 的控制流边界。
                continue

            # 整理 verify 需要的 candidate 验证信息。
            candidate = (agents.parent / raw).resolve()  # AGENTS 校验输入值

            # 整理 verify 需要的 root candidate 验证信息。
            root_candidate = (project / raw).resolve()  # AGENTS 校验输入值

            # 校验总体验证分支。
            if (
                not candidate.exists()
                and not root_candidate.exists()
                and not raw.endswith("/")
                and not is_expected_contract_example_path(raw, profile)
            ):

                # 追加总体验证诊断。
                list_warnings.append(f"{list_checked[-1]}: referenced path may not exist: {raw}")

        # 逐项检查 verify 验证候选。
        for match in COMMAND_RE.finditer(text):

            # 整理 verify 需要的 command 验证信息。
            command = match.group(1).strip()  # AGENTS 校验输入值

            # 校验总体验证分支。
            if not command or "/" in command or command.endswith((".md", ".json", ".toml", ".yml", ".yaml")):

                # 分隔 verify 的控制流边界。
                continue

            # 整理 verify 需要的 config error 验证信息。
            config_error = config_backed_command_error(command, project)  # AGENTS 校验输入值

            # 校验总体验证分支。
            if config_error:

                # 追加总体验证诊断。
                list_errors.append(f"{list_checked[-1]}: {config_error}")

            # 整理 verify 需要的 script error 验证信息。
            script_error = documented_script_path_error(command, project)  # AGENTS 校验输入值

            # 校验总体验证分支。
            if script_error:

                # 追加总体验证诊断。
                list_errors.append(f"{list_checked[-1]}: {script_error}")

            # 校验总体验证分支。
            if command.startswith(("make ", "npm ", "pnpm ", "yarn ", "bun ", "python ", "pytest", "go ", "composer ", "ruff ", "mypy ", "npx ")):

                # 分隔 verify 的控制流边界。
                continue

    # 整理 verify 需要的 source governance 验证信息。
    source_governance = source_governance_report(project, profile)  # AGENTS 校验输入值

    # 调用 extend 处理 verify。
    list_errors.extend(format_source_governance_errors(source_governance))

    # 调用 extend 处理 verify。
    list_errors.extend(str(item) for item in facts.get("tool_script_layout_violations", []) or [])

    # 调用 extend 处理 verify。
    list_errors.extend(str(item) for item in facts.get("script_triad_gaps", []) or [])

    # 收集 global status 验证条目。
    global_status = global_codex_agents_status(project_root=project, profile=profile)  # AGENTS 校验输入值

    # 校验总体验证分支。
    if (project / "skills" / "agents-md-generator" / "SKILL.md").is_file() and not global_status["baseline_ok"]:

        # 整理 verify 需要的 reason text 验证信息。
        reason_text = ", ".join(global_status["repair_reasons"]) or "unknown global Codex AGENTS baseline issue"  # AGENTS 校验输入值

        # 追加总体验证诊断。
        list_errors.append(
            (
                f"global .codex/AGENTS.md is not healthy for agents-md-generator development "  # AGENTS 长文本片段
                f"({reason_text}); run `{global_codex_agents_sync_command(project, profile)}`"  # AGENTS 长文本片段
            )
        )

    # 返回 verify 的验证载荷。
    return {"checked_files": list_checked, "errors": list_errors, "warnings": list_warnings, "global_codex_agents_status": global_status}

# 定义 main  校验入口。
def main() -> None:

    # 整理 main 需要的 parser 验证信息。
    parser = argparse.ArgumentParser(description="Verify AGENTS.md generated content.")  # AGENTS 校验输入值

    # 调用 add_argument 处理 main。
    parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 处理 main。
    parser.add_argument("--include-skipped", action="store_true", help="Also scan skipped dirs.")

    # 调用 add_argument 处理 main。
    parser.add_argument("--installed-skill-dir", default=None)

    # 收集 args 验证条目。
    args = parser.parse_args()  # AGENTS 校验输入值

    # 调用 emit_json 处理 main。
    emit_json(verify(resolve_project(args.project), args.include_skipped, args.installed_skill_dir))

# 校验 模块入口 的验证分支条件。
if __name__ == "__main__":

    # 调用 main 处理 模块入口。
    main()


