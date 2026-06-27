"""维护文档治理脚手架、会话启动、恢复检查和 handoff 写入逻辑。"""

# 导入 脚本治理 所需的依赖模块。
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
from manage_docs_shared import *
from manage_docs_sync_verify import verify_docs
from manage_dirs import CURRENT_STRUCTURE, DIR_MANAGER_MD, PLANNED_STRUCTURE

# 定义 preflight_docs 的脚本治理处理入口。
def preflight_docs(project: Path) -> dict[str, Any]:

    # 收集 docs 条目，保持 preflight_docs 的处理顺序稳定。
    docs = docs_root(project)  # docs 用于本步治理判断

    # 保留 question 中间值，支撑 preflight_docs 的当前计算步骤。
    str_question = "是否允许在现有 docs/ 下添加 AGENTS.md governance 子目录和记录文件？"  # question 用于本步治理判断

    # 检查 preflight_docs 的当前条件是否需要进入专门分支。
    if not docs.exists():

        # 返回 preflight_docs 已整理完成的调用载荷。
        return {
            "project": str(project),
            "status": "safe",
            "docs_exists": False,
            "safe_to_scaffold": True,
            "conflicts": [],
            "requires_user_confirmation": False,
            "question": "",
        }

    # 检查 preflight_docs 的当前条件是否需要进入专门分支。
    if not docs.is_dir():

        # 返回 preflight_docs 已整理完成的调用载荷。
        return {
            "project": str(project),
            "status": "conflict",
            "docs_exists": True,
            "safe_to_scaffold": False,
            "conflicts": ["docs exists but is not a directory"],
            "requires_user_confirmation": True,
            "question": str_question,
        }

    # 收集 reserved paths 条目，保持 preflight_docs 的处理顺序稳定。
    list_reserved_paths = [*DOC_DIRS, *REQUIRED_DOC_FILES]  # reserved paths 用于本步治理判断

    # 收集 conflicts 条目，保持 preflight_docs 的处理顺序稳定。
    list_conflicts: list[str] = []  # conflicts 用于本步治理判断

    # 收集 reserved exists 条目，保持 preflight_docs 的处理顺序稳定。
    bool_reserved_exists = False  # reserved exists 用于本步治理判断

    # 逐项推进 preflight_docs 的候选项检查。
    for rel_path in list_reserved_paths:

        # 保留 path 中间值，支撑 preflight_docs 的当前计算步骤。
        path = project / rel_path  # path 用于本步治理判断

        # 检查 preflight_docs 的当前条件是否需要进入专门分支。
        if path.exists():

            # 收集 reserved exists 条目，保持 preflight_docs 的处理顺序稳定。
            bool_reserved_exists = True  # reserved exists 用于本步治理判断

            # 检查 preflight_docs 的当前条件是否需要进入专门分支。
            if rel_path in DOC_DIRS and not path.is_dir():

                # 调用 append 完成 preflight_docs 的当前动作。
                list_conflicts.append(f"{rel_path} exists but is not a directory")

            # 检查 preflight_docs 的当前条件是否需要进入专门分支。
            if rel_path in REQUIRED_DOC_FILES and not path.is_file():

                # 调用 append 完成 preflight_docs 的当前动作。
                list_conflicts.append(f"{rel_path} exists but is not a file")

    # 保留 docs result 中间值，支撑 preflight_docs 的当前计算步骤。
    docs_result = verify_docs(project)  # docs result 用于本步治理判断

    # 检查 preflight_docs 的当前条件是否需要进入专门分支。
    if not docs_result["errors"]:

        # 返回 preflight_docs 已整理完成的调用载荷。
        return {
            "project": str(project),
            "status": "safe",
            "docs_exists": True,
            "safe_to_scaffold": True,
            "conflicts": [],
            "requires_user_confirmation": False,
            "question": "",
        }

    # 检查 preflight_docs 的当前条件是否需要进入专门分支。
    if bool_reserved_exists:

        # 调用 extend 完成 preflight_docs 的当前动作。
        list_conflicts.extend(item for item in docs_result["errors"] if item not in list_conflicts)

        # 返回 preflight_docs 已整理完成的调用载荷。
        return {
            "project": str(project),
            "status": "conflict",
            "docs_exists": True,
            "safe_to_scaffold": False,
            "conflicts": list_conflicts,
            "requires_user_confirmation": True,
            "question": str_question,
        }

    # 保留 existing 中间值，支撑 preflight_docs 的当前计算步骤。
    existing = [  # existing 用于本步治理判断
        path.relative_to(project).as_posix()  # existing 用于本步治理判断
        for path in sorted(docs.rglob("*"))  # existing 用于本步治理判断
        if path.is_file() or path.is_dir()  # existing 用于本步治理判断
    ]

    # 收集 conflicts 条目，保持 preflight_docs 的处理顺序稳定。
    list_conflicts = existing or ["docs/ exists but AGENTS.md governance structure is not initialized"]  # conflicts 用于本步治理判断

    # 返回 preflight_docs 已整理完成的调用载荷。
    return {
        "project": str(project),
        "status": "ambiguous",
        "docs_exists": True,
        "safe_to_scaffold": False,
        "conflicts": list_conflicts,
        "requires_user_confirmation": True,
        "question": str_question,
    }

# 定义 rotate_current_development_if_needed 的脚本治理处理入口。
def rotate_current_development_if_needed(project: Path) -> str:

    # 保留 target 中间值，支撑 rotate_current_development_if_needed 的当前计算步骤。
    target = project / "docs" / "development" / "DEVELOPMENT.md"  # target 用于本步治理判断

    # 检查 rotate_current_development_if_needed 的当前条件是否需要进入专门分支。
    if not target.exists():

        # 返回 rotate_current_development_if_needed 已整理完成的调用载荷。
        return ""

    # 保留 text 中间值，支撑 rotate_current_development_if_needed 的当前计算步骤。
    text = target.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

    # 检查 rotate_current_development_if_needed 的当前条件是否需要进入专门分支。
    if "- Version: not recorded" in text and "- Status: not recorded" in text:

        # 返回 rotate_current_development_if_needed 已整理完成的调用载荷。
        return ""

    # 保留 history dir 中间值，支撑 rotate_current_development_if_needed 的当前计算步骤。
    history_dir = project / "docs" / "development" / "history_development" / stamp()  # history dir 用于本步治理判断

    # 调用 mkdir 完成 rotate_current_development_if_needed 的当前动作。
    history_dir.mkdir(parents=True, exist_ok=True)

    # 保留 archived target 中间值，支撑 rotate_current_development_if_needed 的当前计算步骤。
    archived_target = history_dir / "DEVELOPMENT.md"  # archived target 用于本步治理判断

    # 调用 move 完成 rotate_current_development_if_needed 的当前动作。
    shutil.move(str(target), str(archived_target))

    # 返回 rotate_current_development_if_needed 已整理完成的调用载荷。
    return archived_target.relative_to(project).as_posix()

# 定义 migrate_legacy_docs 的脚本治理处理入口。
def migrate_legacy_docs(project: Path) -> list[str]:

    # 保留 migrated 中间值，支撑 migrate_legacy_docs 的当前计算步骤。
    list_migrated: list[str] = []  # migrated 用于本步治理判断

    # 保留 docs root 中间值，支撑 migrate_legacy_docs 的当前计算步骤。
    docs_root = project / "docs"  # docs root 用于本步治理判断

    # 收集 legacy handoffs 条目，保持 migrate_legacy_docs 的处理顺序稳定。
    list_legacy_handoffs = [project / "HANDOFF.md", docs_root / "HANDOFF.md"]  # legacy handoffs 用于本步治理判断

    # 保留 handoff target 中间值，支撑 migrate_legacy_docs 的当前计算步骤。
    handoff_target = project / "docs" / "handoff" / "HANDOFF.md"  # handoff target 用于本步治理判断

    # 逐项推进 migrate_legacy_docs 的候选项检查。
    for legacy in list_legacy_handoffs:

        # 检查 migrate_legacy_docs 的当前条件是否需要进入专门分支。
        if legacy.exists() and legacy.is_file():

            # 检查 migrate_legacy_docs 的当前条件是否需要进入专门分支。
            if handoff_target.exists():

                # 调用 rotate_handoff 完成 migrate_legacy_docs 的当前动作。
                rotate_handoff(project)

            # 调用 mkdir 完成 migrate_legacy_docs 的当前动作。
            handoff_target.parent.mkdir(parents=True, exist_ok=True)

            # 调用 move 完成 migrate_legacy_docs 的当前动作。
            shutil.move(str(legacy), str(handoff_target))

            # 调用 append 完成 migrate_legacy_docs 的当前动作。
            list_migrated.append(handoff_target.relative_to(project).as_posix())

            # 分隔 migrate_legacy_docs 的控制流边界。
            break

    # 收集 legacy developments 条目，保持 migrate_legacy_docs 的处理顺序稳定。
    list_legacy_developments = [project / "DEVELOPMENT.md", docs_root / "DEVELOPMENT.md"]  # legacy developments 用于本步治理判断

    # 保留 development target 中间值，支撑 migrate_legacy_docs 的当前计算步骤。
    development_target = project / "docs" / "development" / "DEVELOPMENT.md"  # development target 用于本步治理判断

    # 逐项推进 migrate_legacy_docs 的候选项检查。
    for legacy in list_legacy_developments:

        # 检查 migrate_legacy_docs 的当前条件是否需要进入专门分支。
        if legacy.exists() and legacy.is_file():

            # 检查 migrate_legacy_docs 的当前条件是否需要进入专门分支。
            if development_target.exists():

                # 调用 rotate_current_development_if_needed 完成 migrate_legacy_docs 的当前动作。
                rotate_current_development_if_needed(project)

            # 调用 mkdir 完成 migrate_legacy_docs 的当前动作。
            development_target.parent.mkdir(parents=True, exist_ok=True)

            # 调用 move 完成 migrate_legacy_docs 的当前动作。
            shutil.move(str(legacy), str(development_target))

            # 调用 append 完成 migrate_legacy_docs 的当前动作。
            list_migrated.append(development_target.relative_to(project).as_posix())

            # 分隔 migrate_legacy_docs 的控制流边界。
            break

    # 返回 migrate_legacy_docs 已整理完成的调用载荷。
    return list_migrated

# 定义 scaffold 的脚本治理处理入口。
def scaffold(project: Path, refresh_existing_state: bool = True) -> dict[str, Any]:
    """说明 scaffold 在 AGENTS 治理流程中的状态处理职责。
    
    数组契约:
        shape/维度: 本函数处理 AGENTS 状态、JSON 记录或文件路径，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 dict、list、str、Path 等 Python 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义以 AGENTS 治理配置和状态文件 schema 为准。
    """

    # 说明下方代码段在脚本治理流程中的职责。
    from manage_docs_memory import init_memory, memory_enabled

    # 保留 created 中间值，支撑 scaffold 的当前计算步骤。
    list_created: list[str] = []  # created 用于本步治理判断

    # 保留 profile 中间值，支撑 scaffold 的当前计算步骤。
    profile = project_profile(project)  # profile 用于本步治理判断

    # 逐项推进 scaffold 的候选项检查。
    for rel_path in DOC_DIRS:

        # 保留 path 中间值，支撑 scaffold 的当前计算步骤。
        path = project / rel_path  # path 用于本步治理判断

        # 检查 scaffold 的当前条件是否需要进入专门分支。
        if not path.exists():

            # 调用 mkdir 完成 scaffold 的当前动作。
            path.mkdir(parents=True, exist_ok=True)

            # 调用 append 完成 scaffold 的当前动作。
            list_created.append(rel_path)

    # 保留 migrated 中间值，支撑 scaffold 的当前计算步骤。
    list_migrated = migrate_legacy_docs(project)  # migrated 用于本步治理判断

    # 保留 handoff naming 中间值，支撑 scaffold 的当前计算步骤。
    handoff_naming = audit_handoff_naming(project)  # handoff naming 用于本步治理判断

    # 收集 files 条目，保持 scaffold 的处理顺序稳定。
    dict_files = {  # files 用于本步治理判断
        "docs/handoff/HANDOFF.md": default_handoff(),  # files 用于本步治理判断
        "docs/development/DEVELOPMENT.md": default_development_record(),  # files 用于本步治理判断
        "docs/install_configuration/INSTALL_CONFIGURATION.md": install_configuration_doc(),  # files 用于本步治理判断
        "docs/git_manager/GIT_MANAGER.md": git_manager_doc(project, profile),  # files 用于本步治理判断
        "docs/git_manager/CHANGELOG.md": default_git_changelog(),  # files 用于本步治理判断
    }

    # 逐项推进 scaffold 的候选项检查。
    for rel_path, content in dict_files.items():

        # 检查 scaffold 的当前条件是否需要进入专门分支。
        if rel_path == "docs/handoff/HANDOFF.md" and handoff_naming["blocking"]:

            # 分隔 scaffold 的控制流边界。
            continue

        # 保留 path 中间值，支撑 scaffold 的当前计算步骤。
        path = project / rel_path  # path 用于本步治理判断

        # 检查 scaffold 的当前条件是否需要进入专门分支。
        if not path.exists():

            # 调用 write_text 完成 scaffold 的当前动作。
            path.write_text(content, encoding="utf-8")

            # 调用 append 完成 scaffold 的当前动作。
            list_created.append(rel_path)

    # 保留 state 中间值，支撑 scaffold 的当前计算步骤。
    state = load_state(project)  # state 用于本步治理判断

    # 保留 state missing 中间值，支撑 scaffold 的当前计算步骤。
    state_missing = not (project / STATE_PATH).exists()  # state missing 用于本步治理判断

    # 调用 setdefault 完成 scaffold 的当前动作。
    state.setdefault("handoff_count", 0)

    # 保留 cleanup 中间值，支撑 scaffold 的当前计算步骤。
    cleanup = cleanup_legacy_evolution_artifacts(project, state)  # cleanup 用于本步治理判断

    # 保留 should refresh dir manager 中间值，支撑 scaffold 的当前计算步骤。
    should_refresh_dir_manager = refresh_existing_state or any(  # should refresh dir manager 用于本步治理判断
        not (project / rel).exists()  # should refresh dir manager 用于本步治理判断
        for rel in [DIR_MANAGER_MD, CURRENT_STRUCTURE, PLANNED_STRUCTURE]  # should refresh dir manager 用于本步治理判断
    )

    # 检查 scaffold 的当前条件是否需要进入专门分支。
    if should_refresh_dir_manager:

        # 保留 中间载荷 中间值，支撑 scaffold 的当前计算步骤。
        state["dir_manager_last_scan"] = datetime.now().isoformat(timespec="seconds")  # 中间载荷 用于本步治理判断

        # 调用 save_state 完成 scaffold 的当前动作。
        save_state(project, state)

        # 保留 dir result 中间值，支撑 scaffold 的当前计算步骤。
        dir_result = init_dir_manager(project)  # dir result 用于本步治理判断

        # 调用 extend 完成 scaffold 的当前动作。
        list_created.extend(path for path in dir_result.get("written", []) if path not in list_created)

    # 检查 scaffold 的当前条件是否需要进入专门分支。
    elif state_missing:

        # 调用 save_state 完成 scaffold 的当前动作。
        save_state(project, state)

    # 保留 memory result 中间值，支撑 scaffold 的当前计算步骤。
    memory_result = None  # memory result 用于本步治理判断

    # 收集 errors 条目，保持 scaffold 的处理顺序稳定。
    list_errors = list(handoff_naming["errors"])  # errors 用于本步治理判断

    # 检查 scaffold 的当前条件是否需要进入专门分支。
    if memory_enabled(project):

        # 保留 memory result 中间值，支撑 scaffold 的当前计算步骤。
        memory_result = init_memory(project)  # memory result 用于本步治理判断

        # 调用 extend 完成 scaffold 的当前动作。
        list_created.extend(path for path in memory_result.get("created", []) if path not in list_created)

        # 调用 extend 完成 scaffold 的当前动作。
        list_errors.extend(f"memory: {item}" for item in memory_result.get("errors", []))

    # 返回 scaffold 已整理完成的调用载荷。
    return {
        "project": str(project),
        "created": list_created,
        "migrated": list_migrated,
        "state": state,
        "cleanup": cleanup,
        "memory": memory_result,
        "handoff_naming": handoff_naming,
        "errors": list_errors,
    }

# 定义 read_input 的脚本治理处理入口。
def read_input(path: str | None) -> dict[str, Any]:

    # 检查 read_input 的当前条件是否需要进入专门分支。
    if not path:

        # 返回 read_input 已整理完成的调用载荷。
        return {}

    # 保留 data 中间值，支撑 read_input 的当前计算步骤。
    dict_data = read_json(Path(path).resolve())  # data 用于本步治理判断

    # 检查 read_input 的当前条件是否需要进入专门分支。
    if not isinstance(dict_data, dict):

        # 抛出 read_input 已确认的阻断原因。
        raise SystemExit(f"Input must be a JSON object: {path}")

    # 返回 read_input 已整理完成的调用载荷。
    return dict_data

# 定义 rotate_handoff 的脚本治理处理入口。
def rotate_handoff(project: Path) -> str | None:

    # 收集 paths 条目，保持 rotate_handoff 的处理顺序稳定。
    paths = handoff_paths(project)  # paths 用于本步治理判断

    # 保留 current 中间值，支撑 rotate_handoff 的当前计算步骤。
    current = paths["current"]  # current 用于本步治理判断

    # 检查 rotate_handoff 的当前条件是否需要进入专门分支。
    if not current.exists():

        # 返回 rotate_handoff 已整理完成的调用载荷。
        return None

    # 保留 history 中间值，支撑 rotate_handoff 的当前计算步骤。
    history = paths["history"]  # history 用于本步治理判断

    # 调用 mkdir 完成 rotate_handoff 的当前动作。
    history.mkdir(parents=True, exist_ok=True)

    # 保留 target 中间值，支撑 rotate_handoff 的当前计算步骤。
    target = unique_handoff_history_path(history, datetime.now())  # target 用于本步治理判断

    # 调用 move 完成 rotate_handoff 的当前动作。
    shutil.move(str(current), str(target))

    # 返回 rotate_handoff 已整理完成的调用载荷。
    return target.relative_to(project).as_posix()

# 定义 handoff_markdown 的脚本治理处理入口。
def handoff_markdown(data: dict[str, Any], count: int) -> str:

    # 返回 handoff_markdown 已整理完成的调用载荷。
    return "\n".join([
        "# Handoff",
        "",
        f"- Handoff count: {count}",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Original Plan And Steps",
        list_lines(data.get("original_plan") or data.get("plan")),
        "",
        "## Current Step",
        list_lines(data.get("current_step")),
        "",
        "## Problems",
        list_lines(data.get("problems")),
        "",
        "## Resolved Problems",
        list_lines(data.get("resolved") or data.get("resolved_problems")),
        "",
        "## Remaining Problems",
        list_lines(data.get("remaining") or data.get("remaining_problems")),
        "",
        "## Next Work",
        list_lines(data.get("next") or data.get("next_work")),
        "",
        "## Verification Evidence",
        list_lines(data.get("verification") or data.get("verification_evidence")),
        "",
    ])

# 定义 maybe_write_conversation_snapshot 的脚本治理处理入口。
def maybe_write_conversation_snapshot(project: Path, data: dict[str, Any], count: int) -> str | None:

    # 收集 fields 条目，保持 maybe_write_conversation_snapshot 的处理顺序稳定。
    dict_fields = {  # fields 用于本步治理判断
        "conversation_summary": data.get("conversation_summary"),  # fields 用于本步治理判断
        "conversation_excerpt": data.get("conversation_excerpt"),  # fields 用于本步治理判断
        "conversation_log_path": data.get("conversation_log_path"),  # fields 用于本步治理判断
    }

    # 检查 maybe_write_conversation_snapshot 的当前条件是否需要进入专门分支。
    if not any(str(value or "").strip() for value in dict_fields.values()):

        # 返回 maybe_write_conversation_snapshot 已整理完成的调用载荷。
        return None

    # 保留 snapshot dir 中间值，支撑 maybe_write_conversation_snapshot 的当前计算步骤。
    snapshot_dir = conversation_snapshot_dir(project)  # snapshot dir 用于本步治理判断

    # 调用 mkdir 完成 maybe_write_conversation_snapshot 的当前动作。
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # 保留 log excerpt 中间值，支撑 maybe_write_conversation_snapshot 的当前计算步骤。
    str_log_excerpt = ""  # log excerpt 用于本步治理判断

    # 保留 log path raw 中间值，支撑 maybe_write_conversation_snapshot 的当前计算步骤。
    log_path_raw = str(dict_fields.get("conversation_log_path") or "").strip()  # log path raw 用于本步治理判断

    # 检查 maybe_write_conversation_snapshot 的当前条件是否需要进入专门分支。
    if log_path_raw:

        # 定位 log path 的文件边界，供 maybe_write_conversation_snapshot 后续读写校验使用。
        path_log_path = Path(log_path_raw)  # log path 用于本步治理判断

        # 检查 maybe_write_conversation_snapshot 的当前条件是否需要进入专门分支。
        if not path_log_path.is_absolute():

            # 定位 log path 的文件边界，供 maybe_write_conversation_snapshot 后续读写校验使用。
            path_log_path = project / path_log_path  # log path 用于本步治理判断

        # 检查 maybe_write_conversation_snapshot 的当前条件是否需要进入专门分支。
        if path_log_path.exists() and path_log_path.is_file():

            # 保留 log excerpt 中间值，支撑 maybe_write_conversation_snapshot 的当前计算步骤。
            str_log_excerpt = path_log_path.read_text(encoding="utf-8", errors="ignore")[:8000]  # log excerpt 用于本步治理判断

    # 保留 snapshot 中间值，支撑 maybe_write_conversation_snapshot 的当前计算步骤。
    dict_snapshot = {  # snapshot 用于本步治理判断
        "handoff_count": count,  # snapshot 用于本步治理判断
        "captured_at": datetime.now().isoformat(timespec="seconds"),  # snapshot 用于本步治理判断
        "source": "handoff input",  # snapshot 用于本步治理判断
        "conversation_summary": dict_fields.get("conversation_summary") or "",  # snapshot 用于本步治理判断
        "conversation_excerpt": dict_fields.get("conversation_excerpt") or "",  # snapshot 用于本步治理判断
        "conversation_log_path": log_path_raw,  # snapshot 用于本步治理判断
        "conversation_log_excerpt": str_log_excerpt,  # snapshot 用于本步治理判断
    }

    # 保留 target 中间值，支撑 maybe_write_conversation_snapshot 的当前计算步骤。
    target = snapshot_dir / f"{stamp()}-handoff-{count}.json"  # target 用于本步治理判断

    # 调用 write_text 完成 maybe_write_conversation_snapshot 的当前动作。
    target.write_text(json.dumps(dict_snapshot, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    # 返回 maybe_write_conversation_snapshot 已整理完成的调用载荷。
    return str(target.relative_to(project).as_posix())

# 定义 write_handoff 的脚本治理处理入口。
def write_handoff(project: Path, input_path: str | None) -> dict[str, Any]:
    from manage_docs_memory import write_handoff_memory

    # 保留 scaffold result 中间值，支撑 write_handoff 的当前计算步骤。
    dict_scaffold_result = scaffold(project)  # scaffold result 用于本步治理判断

    # 检查 write_handoff 的当前条件是否需要进入专门分支。
    if dict_scaffold_result.get("errors"):

        # 返回 write_handoff 已整理完成的调用载荷。
        return {
            "project": str(project),
            "errors": dict_scaffold_result["errors"],
            "handoff_naming": dict_scaffold_result.get("handoff_naming", {}),
        }

    # 保留 archived 中间值，支撑 write_handoff 的当前计算步骤。
    archived = rotate_handoff(project)  # archived 用于本步治理判断

    # 保留 state 中间值，支撑 write_handoff 的当前计算步骤。
    state = load_state(project)  # state 用于本步治理判断

    # 调用 cleanup_legacy_evolution_artifacts 完成 write_handoff 的当前动作。
    cleanup_legacy_evolution_artifacts(project, state)

    # 保留 count 中间值，支撑 write_handoff 的当前计算步骤。
    count = int(state.get("handoff_count", 0)) + 1  # count 用于本步治理判断

    # 保留 data 中间值，支撑 write_handoff 的当前计算步骤。
    dict_data = read_input(input_path)  # data 用于本步治理判断

    # 保留 target 中间值，支撑 write_handoff 的当前计算步骤。
    target = handoff_paths(project)["current"]  # target 用于本步治理判断

    # 调用 write_text 完成 write_handoff 的当前动作。
    target.write_text(handoff_markdown(dict_data, count), encoding="utf-8")

    # 保留 snapshot 中间值，支撑 write_handoff 的当前计算步骤。
    snapshot = maybe_write_conversation_snapshot(project, dict_data, count)  # snapshot 用于本步治理判断

    # 保留 中间载荷 中间值，支撑 write_handoff 的当前计算步骤。
    state["handoff_count"] = count  # 中间载荷 用于本步治理判断

    # 调用 save_state 完成 write_handoff 的当前动作。
    save_state(project, state)

    # 保留 active 中间值，支撑 write_handoff 的当前计算步骤。
    active = active_session_file(project)  # active 用于本步治理判断

    # 检查 write_handoff 的当前条件是否需要进入专门分支。
    if active.exists():

        # 调用 unlink 完成 write_handoff 的当前动作。
        active.unlink()

    # 保留 result 中间值，支撑 write_handoff 的当前计算步骤。
    dict_result = {"project": str(project), "written": str(target), "archived": archived, "handoff_count": count}  # result 用于本步治理判断

    # 保留 memory result 中间值，支撑 write_handoff 的当前计算步骤。
    memory_result = write_handoff_memory(project, dict_data, count, target)  # memory result 用于本步治理判断

    # 检查 write_handoff 的当前条件是否需要进入专门分支。
    if memory_result is not None:

        # 保留 中间载荷 中间值，支撑 write_handoff 的当前计算步骤。
        dict_result["memory"] = memory_result  # 中间载荷 用于本步治理判断

        # 检查 write_handoff 的当前条件是否需要进入专门分支。
        if memory_result.get("errors"):

            # 保留 中间载荷 中间值，支撑 write_handoff 的当前计算步骤。
            dict_result["errors"] = [f"memory: {item}" for item in memory_result["errors"]]  # 中间载荷 用于本步治理判断

    # 检查 write_handoff 的当前条件是否需要进入专门分支。
    if snapshot:

        # 保留 中间载荷 中间值，支撑 write_handoff 的当前计算步骤。
        dict_result["conversation_snapshot"] = snapshot  # 中间载荷 用于本步治理判断

    # 返回 write_handoff 已整理完成的调用载荷。
    return dict_result

# 定义 write_active_session 的脚本治理处理入口。
def write_active_session(project: Path, input_path: str | None) -> dict[str, Any]:
    from manage_docs_memory import memory_read_recommendation

    # 已治理仓库启动会话时，不应重写目录基线或文档治理时间戳。

    # 保留 scaffold result 中间值，支撑 write_active_session 的当前计算步骤。
    dict_scaffold_result = scaffold(project, refresh_existing_state=False)  # scaffold result 用于本步治理判断

    # 检查 write_active_session 的当前条件是否需要进入专门分支。
    if dict_scaffold_result.get("errors"):

        # 返回 write_active_session 已整理完成的调用载荷。
        return {
            "project": str(project),
            "errors": dict_scaffold_result["errors"],
            "blocking": True,
            "handoff_naming": dict_scaffold_result.get("handoff_naming", {}),
        }

    # 保留 data 中间值，支撑 write_active_session 的当前计算步骤。
    dict_data = read_input(input_path)  # data 用于本步治理判断

    # 保留 cleanup 中间值，支撑 write_active_session 的当前计算步骤。
    cleanup = cleanup_legacy_evolution_artifacts(project)  # cleanup 用于本步治理判断

    # 保留 handoff 中间值，支撑 write_active_session 的当前计算步骤。
    handoff = handoff_paths(project)["current"]  # handoff 用于本步治理判断

    # 保留 active 中间值，支撑 write_active_session 的当前计算步骤。
    dict_active = {  # active 用于本步治理判断
        "task": dict_data.get("task", "not recorded"),  # active 用于本步治理判断
        "current_step": dict_data.get("current_step", "not recorded"),  # active 用于本步治理判断
        "conversation_summary": dict_data.get("conversation_summary", ""),  # active 用于本步治理判断
        "started_at": datetime.now().isoformat(timespec="seconds"),  # active 用于本步治理判断
        "handoff_path": "docs/handoff/HANDOFF.md",  # active 用于本步治理判断
        "handoff_hash": file_hash(handoff),  # active 用于本步治理判断
        "handoff_mtime": handoff.stat().st_mtime if handoff.exists() else 0,  # active 用于本步治理判断
    }

    # 保留 agents dir 中间值，支撑 write_active_session 的当前计算步骤。
    agents_dir = project / ".agents"  # agents dir 用于本步治理判断

    # 调用 mkdir 完成 write_active_session 的当前动作。
    agents_dir.mkdir(exist_ok=True)

    # 调用 write_text 完成 write_active_session 的当前动作。
    active_session_file(project).write_text(json.dumps(dict_active, indent=2, sort_keys=True), encoding="utf-8")

    # 保留 result 中间值，支撑 write_active_session 的当前计算步骤。
    dict_result = {"project": str(project), "written": str(active_session_file(project)), "active_session": dict_active, "cleanup": cleanup}  # result 用于本步治理判断

    # 保留 recommendation 中间值，支撑 write_active_session 的当前计算步骤。
    recommendation = memory_read_recommendation(project, str(dict_active.get("task", "current task")))  # recommendation 用于本步治理判断

    # 检查 write_active_session 的当前条件是否需要进入专门分支。
    if recommendation:

        # 保留 中间载荷 中间值，支撑 write_active_session 的当前计算步骤。
        dict_result["memory_read_recommendation"] = recommendation  # 中间载荷 用于本步治理判断

    # 返回 write_active_session 已整理完成的调用载荷。
    return dict_result

# 定义 read_active_session 的脚本治理处理入口。
def read_active_session(project: Path) -> dict[str, Any]:

    # 保留 active 中间值，支撑 read_active_session 的当前计算步骤。
    active = read_json(active_session_file(project))  # active 用于本步治理判断

    # 返回 read_active_session 已整理完成的调用载荷。
    return active if isinstance(active, dict) else {}

# 定义 resume_check 的脚本治理处理入口。
def resume_check(project: Path, conversation_log: str | None = None) -> dict[str, Any]:
    from manage_docs_memory import memory_read_recommendation

    # 保留 naming 中间值，支撑 resume_check 的当前计算步骤。
    naming = audit_handoff_naming(project)  # naming 用于本步治理判断

    # 检查 resume_check 的当前条件是否需要进入专门分支。
    if naming["blocking"]:

        # 保留 result 中间值，支撑 resume_check 的当前计算步骤。
        dict_result = {  # result 用于本步治理判断
            "project": str(project),  # result 用于本步治理判断
            "status": "blocked",  # result 用于本步治理判断
            "interrupted": False,  # result 用于本步治理判断
            "blocking": True,  # result 用于本步治理判断
            "reasons": naming["errors"],  # result 用于本步治理判断
            "handoff_naming": naming,  # result 用于本步治理判断
        }

        # 保留 recommendation 中间值，支撑 resume_check 的当前计算步骤。
        recommendation = memory_read_recommendation(project, "resume current task")  # recommendation 用于本步治理判断

        # 检查 resume_check 的当前条件是否需要进入专门分支。
        if recommendation:

            # 保留 中间载荷 中间值，支撑 resume_check 的当前计算步骤。
            dict_result["memory_read_recommendation"] = recommendation  # 中间载荷 用于本步治理判断

        # 返回 resume_check 已整理完成的调用载荷。
        return dict_result

    # 保留 active 中间值，支撑 resume_check 的当前计算步骤。
    dict_active = read_active_session(project)  # active 用于本步治理判断

    # 检查 resume_check 的当前条件是否需要进入专门分支。
    if not dict_active:

        # 保留 result 中间值，支撑 resume_check 的当前计算步骤。
        dict_result = {  # result 用于本步治理判断
            "project": str(project),  # result 用于本步治理判断
            "status": "clean",  # result 用于本步治理判断
            "interrupted": False,  # result 用于本步治理判断
            "blocking": False,  # result 用于本步治理判断
            "reasons": ["no active session found"],  # result 用于本步治理判断
        }

        # 保留 recommendation 中间值，支撑 resume_check 的当前计算步骤。
        recommendation = memory_read_recommendation(project, "current task")  # recommendation 用于本步治理判断

        # 检查 resume_check 的当前条件是否需要进入专门分支。
        if recommendation:

            # 保留 中间载荷 中间值，支撑 resume_check 的当前计算步骤。
            dict_result["memory_read_recommendation"] = recommendation  # 中间载荷 用于本步治理判断

        # 返回 resume_check 已整理完成的调用载荷。
        return dict_result

    # 保留 handoff 中间值，支撑 resume_check 的当前计算步骤。
    handoff = handoff_paths(project)["current"]  # handoff 用于本步治理判断

    # 保留 current hash 中间值，支撑 resume_check 的当前计算步骤。
    current_hash = file_hash(handoff)  # current hash 用于本步治理判断

    # 收集 reasons 条目，保持 resume_check 的处理顺序稳定。
    list_reasons: list[str] = []  # reasons 用于本步治理判断

    # 保留 interrupted 中间值，支撑 resume_check 的当前计算步骤。
    bool_interrupted = False  # interrupted 用于本步治理判断

    # 检查 resume_check 的当前条件是否需要进入专门分支。
    if current_hash and current_hash == dict_active.get("handoff_hash"):

        # 保留 interrupted 中间值，支撑 resume_check 的当前计算步骤。
        bool_interrupted = True  # interrupted 用于本步治理判断

        # 调用 append 完成 resume_check 的当前动作。
        list_reasons.append("HANDOFF.md has not changed since active session started")

    # 检查 resume_check 的当前条件是否需要进入专门分支。
    elif not current_hash:

        # 保留 interrupted 中间值，支撑 resume_check 的当前计算步骤。
        bool_interrupted = True  # interrupted 用于本步治理判断

        # 调用 append 完成 resume_check 的当前动作。
        list_reasons.append("HANDOFF.md is missing while an active session exists")
    else:

        # 调用 append 完成 resume_check 的当前动作。
        list_reasons.append("HANDOFF.md changed after active session started")

    # 检查 resume_check 的当前条件是否需要进入专门分支。
    if conversation_log:

        # 定位 log path 的文件边界，供 resume_check 后续读写校验使用。
        log_path = Path(conversation_log).resolve()  # log path 用于本步治理判断

        # 检查 resume_check 的当前条件是否需要进入专门分支。
        if log_path.exists():

            # 保留 text 中间值，支撑 resume_check 的当前计算步骤。
            text = log_path.read_text(encoding="utf-8", errors="ignore").lower()  # text 用于本步治理判断

            # 检查 resume_check 的当前条件是否需要进入专门分支。
            if any(marker in text for marker in ["stop", "stopped", "interrupted", "断网", "强制停止", "中断"]):

                # 保留 interrupted 中间值，支撑 resume_check 的当前计算步骤。
                bool_interrupted = True  # interrupted 用于本步治理判断

                # 调用 append 完成 resume_check 的当前动作。
                list_reasons.append("conversation log contains interruption markers")

    # 保留 result 中间值，支撑 resume_check 的当前计算步骤。
    dict_result = {  # result 用于本步治理判断
        "project": str(project),  # result 用于本步治理判断
        "status": "interrupted" if bool_interrupted else "clean",  # result 用于本步治理判断
        "interrupted": bool_interrupted,  # result 用于本步治理判断
        "blocking": False,  # result 用于本步治理判断
        "active_session": dict_active,  # result 用于本步治理判断
        "current_handoff_hash": current_hash,  # result 用于本步治理判断
        "reasons": list_reasons,  # result 用于本步治理判断
    }

    # 保留 recommendation 中间值，支撑 resume_check 的当前计算步骤。
    recommendation = memory_read_recommendation(project, str(dict_active.get("task", "resume current task")))  # recommendation 用于本步治理判断

    # 检查 resume_check 的当前条件是否需要进入专门分支。
    if recommendation:

        # 保留 中间载荷 中间值，支撑 resume_check 的当前计算步骤。
        dict_result["memory_read_recommendation"] = recommendation  # 中间载荷 用于本步治理判断

    # 返回 resume_check 已整理完成的调用载荷。
    return dict_result

# 定义 resume_repair 的脚本治理处理入口。
def resume_repair(project: Path, input_path: str | None) -> dict[str, Any]:

    # 保留 check 中间值，支撑 resume_repair 的当前计算步骤。
    dict_check = resume_check(project)  # check 用于本步治理判断

    # 检查 resume_repair 的当前条件是否需要进入专门分支。
    if dict_check.get("blocking"):

        # 返回 resume_repair 已整理完成的调用载荷。
        return {
            "project": str(project),
            "skipped": True,
            "interrupted": False,
            "blocking": True,
            "errors": dict_check["reasons"],
            "resume_check": dict_check,
        }

    # 检查 resume_repair 的当前条件是否需要进入专门分支。
    if not dict_check["interrupted"]:

        # 返回 resume_repair 已整理完成的调用载荷。
        return {
            "project": str(project),
            "skipped": True,
            "interrupted": False,
            "reasons": dict_check["reasons"],
        }

    # 保留 result 中间值，支撑 resume_repair 的当前计算步骤。
    dict_result = write_handoff(project, input_path)  # result 用于本步治理判断

    # 保留 中间载荷 中间值，支撑 resume_repair 的当前计算步骤。
    dict_result["recovery"] = True  # 中间载荷 用于本步治理判断

    # 保留 中间载荷 中间值，支撑 resume_repair 的当前计算步骤。
    dict_result["interrupted"] = True  # 中间载荷 用于本步治理判断

    # 保留 中间载荷 中间值，支撑 resume_repair 的当前计算步骤。
    dict_result["resume_check"] = dict_check  # 中间载荷 用于本步治理判断

    # 返回 resume_repair 已整理完成的调用载荷。
    return dict_result

# 定义 repair_handoff_names 的脚本治理处理入口。
def repair_handoff_names(project: Path, write: bool = False) -> dict[str, Any]:

    # 收集 paths 条目，保持 repair_handoff_names 的处理顺序稳定。
    paths = handoff_paths(project)  # paths 用于本步治理判断

    # 保留 handoff root 中间值，支撑 repair_handoff_names 的当前计算步骤。
    handoff_root = paths["root"]  # handoff root 用于本步治理判断

    # 保留 history dir 中间值，支撑 repair_handoff_names 的当前计算步骤。
    history_dir = paths["history"]  # history dir 用于本步治理判断

    # 定位 current path 的文件边界，供 repair_handoff_names 后续读写校验使用。
    current_path = paths["current"]  # current path 用于本步治理判断

    # 保留 renamed 中间值，支撑 repair_handoff_names 的当前计算步骤。
    list_renamed: list[dict[str, str]] = []  # renamed 用于本步治理判断

    # 保留 skipped 中间值，支撑 repair_handoff_names 的当前计算步骤。
    list_skipped: list[str] = []  # skipped 用于本步治理判断

    # 收集 errors 条目，保持 repair_handoff_names 的处理顺序稳定。
    list_errors: list[str] = []  # errors 用于本步治理判断

    # 调用 mkdir 完成 repair_handoff_names 的当前动作。
    handoff_root.mkdir(parents=True, exist_ok=True)

    # 调用 mkdir 完成 repair_handoff_names 的当前动作。
    history_dir.mkdir(parents=True, exist_ok=True)

    # 收集 current candidates 条目，保持 repair_handoff_names 的处理顺序稳定。
    current_candidates = [  # current candidates 用于本步治理判断
        path for path in sorted(handoff_root.iterdir())  # current candidates 用于本步治理判断
        if path.is_file() and path.suffix.lower() == ".md" and path.name != HANDOFF_CURRENT_FILENAME  # current candidates 用于本步治理判断
    ] if handoff_root.is_dir() else []  # current candidates 用于本步治理判断

    # 保留 extra current 中间值，支撑 repair_handoff_names 的当前计算步骤。
    extra_current = [  # extra current 用于本步治理判断
        path.relative_to(project).as_posix()  # extra current 用于本步治理判断
        for path in sorted(handoff_root.iterdir())  # extra current 用于本步治理判断
        if path.name not in {HANDOFF_CURRENT_FILENAME, HANDOFF_HISTORY_DIRNAME} and not (path.is_file() and path.suffix.lower() == ".md")  # extra current 用于本步治理判断
    ] if handoff_root.is_dir() else []  # extra current 用于本步治理判断

    # 检查 repair_handoff_names 的当前条件是否需要进入专门分支。
    if extra_current:

        # 调用 extend 完成 repair_handoff_names 的当前动作。
        list_errors.extend(
            f"cannot repair handoff naming automatically because docs/handoff contains non-governed entries: {item}"
            for item in extra_current
        )

    # 检查 repair_handoff_names 的当前条件是否需要进入专门分支。
    if current_path.exists():

        # 检查 repair_handoff_names 的当前条件是否需要进入专门分支。
        if current_candidates:

            # 调用 append 完成 repair_handoff_names 的当前动作。
            list_errors.append("cannot repair handoff naming automatically because docs/handoff contains HANDOFF.md plus additional markdown candidates")

    # 检查 repair_handoff_names 的当前条件是否需要进入专门分支。
    elif len(current_candidates) == 1:

        # 保留 source 中间值，支撑 repair_handoff_names 的当前计算步骤。
        source = current_candidates[0]  # source 用于本步治理判断

        # 检查 repair_handoff_names 的当前条件是否需要进入专门分支。
        if write:

            # 调用 rename 完成 repair_handoff_names 的当前动作。
            source.rename(current_path)

        # 调用 append 完成 repair_handoff_names 的当前动作。
        list_renamed.append({"from": source.relative_to(project).as_posix(), "to": current_path.relative_to(project).as_posix()})

    # 检查 repair_handoff_names 的当前条件是否需要进入专门分支。
    elif len(current_candidates) > 1:

        # 调用 append 完成 repair_handoff_names 的当前动作。
        list_errors.append("cannot repair handoff naming automatically because docs/handoff contains multiple markdown candidates")
    else:

        # 调用 append 完成 repair_handoff_names 的当前动作。
        list_skipped.append("no current handoff rename candidate found")

    # 逐项推进 repair_handoff_names 的候选项检查。
    for path in sorted(history_dir.iterdir()) if history_dir.is_dir() else []:

        # 定位 rel path 的文件边界，供 repair_handoff_names 后续读写校验使用。
        rel_path = path.relative_to(project).as_posix()  # rel path 用于本步治理判断

        # 检查 repair_handoff_names 的当前条件是否需要进入专门分支。
        if not path.is_file():

            # 调用 append 完成 repair_handoff_names 的当前动作。
            list_errors.append(f"cannot repair history handoff naming automatically because a non-file entry exists: {rel_path}")

            # 分隔 repair_handoff_names 的控制流边界。
            continue

        # 检查 repair_handoff_names 的当前条件是否需要进入专门分支。
        if HANDOFF_HISTORY_RE.fullmatch(path.name):

            # 分隔 repair_handoff_names 的控制流边界。
            continue

        # 检查 repair_handoff_names 的当前条件是否需要进入专门分支。
        if path.suffix.lower() != ".md":

            # 调用 append 完成 repair_handoff_names 的当前动作。
            list_errors.append(f"cannot repair history handoff naming automatically because a non-markdown file exists: {rel_path}")

            # 分隔 repair_handoff_names 的控制流边界。
            continue

        # 保留 text 中间值，支撑 repair_handoff_names 的当前计算步骤。
        text = path.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

        # 检查 repair_handoff_names 的当前条件是否需要进入专门分支。
        if not looks_like_handoff_markdown(text):

            # 调用 append 完成 repair_handoff_names 的当前动作。
            list_errors.append(f"cannot repair history handoff naming automatically because file does not look like a handoff: {rel_path}")

            # 分隔 repair_handoff_names 的控制流边界。
            continue

        # 保留 generated at 中间值，支撑 repair_handoff_names 的当前计算步骤。
        generated_at = parse_handoff_generated_at(text)  # generated at 用于本步治理判断

        # 保留 moment 中间值，支撑 repair_handoff_names 的当前计算步骤。
        moment = generated_at or datetime.fromtimestamp(path.stat().st_mtime)  # moment 用于本步治理判断

        # 保留 target 中间值，支撑 repair_handoff_names 的当前计算步骤。
        target = unique_handoff_history_path(history_dir, moment)  # target 用于本步治理判断

        # 检查 repair_handoff_names 的当前条件是否需要进入专门分支。
        if target == path:

            # 调用 append 完成 repair_handoff_names 的当前动作。
            list_skipped.append(rel_path)

            # 分隔 repair_handoff_names 的控制流边界。
            continue

        # 检查 repair_handoff_names 的当前条件是否需要进入专门分支。
        if write:

            # 调用 rename 完成 repair_handoff_names 的当前动作。
            path.rename(target)

        # 调用 append 完成 repair_handoff_names 的当前动作。
        list_renamed.append({"from": rel_path, "to": target.relative_to(project).as_posix()})

    # 保留 naming 中间值，支撑 repair_handoff_names 的当前计算步骤。
    naming = audit_handoff_naming(project)  # naming 用于本步治理判断

    # 返回 repair_handoff_names 已整理完成的调用载荷。
    return {
        "project": str(project),
        "write_requested": write,
        "renamed": list_renamed,
        "skipped": list_skipped,
        "errors": list_errors,
        "blocking": bool(list_errors) or naming["blocking"],
        "handoff_naming": naming,
    }

# 定义 write_development 的脚本治理处理入口。
def write_development(project: Path, stage: str, input_path: str | None) -> dict[str, Any]:

    # 调用 scaffold 完成 write_development 的当前动作。
    scaffold(project)

    # 保留 data 中间值，支撑 write_development 的当前计算步骤。
    dict_data = read_input(input_path)  # data 用于本步治理判断

    # 保留 target 中间值，支撑 write_development 的当前计算步骤。
    target = project / "docs" / "development" / "DEVELOPMENT.md"  # target 用于本步治理判断

    # 保留 archived 中间值，支撑 write_development 的当前计算步骤。
    str_archived = ""  # archived 用于本步治理判断

    # 检查 write_development 的当前条件是否需要进入专门分支。
    if target.exists():

        # 保留 text 中间值，支撑 write_development 的当前计算步骤。
        text = target.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

        # 检查 write_development 的当前条件是否需要进入专门分支。
        if "- Version: not recorded" not in text or "- Status: not recorded" not in text:

            # 保留 history dir 中间值，支撑 write_development 的当前计算步骤。
            history_dir = project / "docs" / "development" / "history_development" / stamp()  # history dir 用于本步治理判断

            # 调用 mkdir 完成 write_development 的当前动作。
            history_dir.mkdir(parents=True, exist_ok=True)

            # 保留 archived target 中间值，支撑 write_development 的当前计算步骤。
            archived_target = history_dir / "DEVELOPMENT.md"  # archived target 用于本步治理判断

            # 调用 move 完成 write_development 的当前动作。
            shutil.move(str(target), str(archived_target))

            # 保留 archived 中间值，支撑 write_development 的当前计算步骤。
            str_archived = archived_target.relative_to(project).as_posix()  # archived 用于本步治理判断

    # 调用 write_text 完成 write_development 的当前动作。
    target.write_text(
        "\n".join([
            f"# Development Stage: {stage}",
            "",
            f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
            f"- Version: {dict_data.get('version', 'not recorded')}",
            f"- Status: {dict_data.get('current_status', 'not recorded')}",
            "",
            "## Development Goal",
            list_lines(dict_data.get("goal")),
            "",
            "## Full Development Plan",
            list_lines(dict_data.get("full_plan")),
            "",
            "## Current Progress",
            list_lines(dict_data.get("current_status")),
            "",
            "## Completed Scope",
            list_lines(dict_data.get("completed_scope")),
            "",
            "## Remaining Scope",
            list_lines(dict_data.get("remaining_scope")),
            "",
            "## Key Problems And Risks",
            list_lines(dict_data.get("remaining_risks") or dict_data.get("problems")),
            "",
            "## Resolution Strategy And Next Steps",
            list_lines(dict_data.get("next_steps") or dict_data.get("next")),
            "",
            "## Development Result",
            list_lines(dict_data.get("results")),
            "",
            "## Verification",
            list_lines(dict_data.get("verification")),
            "",
            "## Artifacts And Impact",
            list_lines(dict_data.get("artifacts")),
            "",
        ]),
        encoding="utf-8",
    )

    # 返回 write_development 已整理完成的调用载荷。
    return {"project": str(project), "written": str(target), "archived": str_archived}

# 定义 changelog_markdown 的脚本治理处理入口。
def changelog_markdown(data: dict[str, Any]) -> str:

    # 返回 changelog_markdown 已整理完成的调用载荷。
    return "\n".join([
        "# Change Log",
        "",
        f"- Version: {data.get('version', 'not recorded')}",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Summary: {data.get('summary', 'not recorded')}",
        "",
        "## Changes",
        list_lines(data.get("changes")),
        "",
        "## Verification",
        list_lines(data.get("verification")),
        "",
    ])

# 定义 rotate_git_changelog 的脚本治理处理入口。
def rotate_git_changelog(project: Path) -> str | None:

    # 保留 current 中间值，支撑 rotate_git_changelog 的当前计算步骤。
    current = git_changelog_file(project)  # current 用于本步治理判断

    # 检查 rotate_git_changelog 的当前条件是否需要进入专门分支。
    if not current.exists():

        # 返回 rotate_git_changelog 已整理完成的调用载荷。
        return None

    # 保留 text 中间值，支撑 rotate_git_changelog 的当前计算步骤。
    text = current.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

    # 检查 rotate_git_changelog 的当前条件是否需要进入专门分支。
    if "- Version: not recorded" in text and "- Summary: not recorded" in text:

        # 返回 rotate_git_changelog 已整理完成的调用载荷。
        return None

    # 保留 history dir 中间值，支撑 rotate_git_changelog 的当前计算步骤。
    history_dir = git_history_root(project) / stamp()  # history dir 用于本步治理判断

    # 调用 mkdir 完成 rotate_git_changelog 的当前动作。
    history_dir.mkdir(parents=True, exist_ok=True)

    # 保留 target 中间值，支撑 rotate_git_changelog 的当前计算步骤。
    target = history_dir / "CHANGELOG.md"  # target 用于本步治理判断

    # 调用 move 完成 rotate_git_changelog 的当前动作。
    shutil.move(str(current), str(target))

    # 返回 rotate_git_changelog 已整理完成的调用载荷。
    return target.relative_to(project).as_posix()

# 定义 write_git_changelog 的脚本治理处理入口。
def write_git_changelog(project: Path, input_path: str | None) -> dict[str, Any]:

    # 调用 scaffold 完成 write_git_changelog 的当前动作。
    scaffold(project)

    # 保留 data 中间值，支撑 write_git_changelog 的当前计算步骤。
    dict_data = read_input(input_path)  # data 用于本步治理判断

    # 保留 target 中间值，支撑 write_git_changelog 的当前计算步骤。
    target = git_changelog_file(project)  # target 用于本步治理判断

    # 保留 archived 中间值，支撑 write_git_changelog 的当前计算步骤。
    archived = rotate_git_changelog(project)  # archived 用于本步治理判断

    # 调用 write_text 完成 write_git_changelog 的当前动作。
    target.write_text(changelog_markdown(dict_data), encoding="utf-8")

    # 保留 state 中间值，支撑 write_git_changelog 的当前计算步骤。
    state = load_state(project)  # state 用于本步治理判断

    # 保留 中间载荷 中间值，支撑 write_git_changelog 的当前计算步骤。
    state["last_git_changelog_at"] = datetime.now().isoformat(timespec="seconds")  # 中间载荷 用于本步治理判断

    # 保留 中间载荷 中间值，支撑 write_git_changelog 的当前计算步骤。
    state["last_git_changelog_version"] = str(dict_data.get("version", "")).strip()  # 中间载荷 用于本步治理判断

    # 调用 save_state 完成 write_git_changelog 的当前动作。
    save_state(project, state)

    # 返回 write_git_changelog 已整理完成的调用载荷。
    return {
        "project": str(project),
        "written": target.relative_to(project).as_posix(),
        "archived": archived or "",
        "version": str(dict_data.get("version", "")).strip(),
    }


