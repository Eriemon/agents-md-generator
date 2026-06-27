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
import os
from pathlib import Path
import sys

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断
from agents_common import SKIP_DIRS, emit_json, resolve_project


# 保留 MANAGED PREFIX 中间值，支撑 模块入口 的当前计算步骤。
MANAGED_PREFIX = "<!-- Managed by agents-md-generator:"  # MANAGED PREFIX 用于本步治理判断


# 定义 is_managed 的脚本治理处理入口。
def is_managed(path: Path) -> bool:

    # 检查 is_managed 的当前条件是否需要进入专门分支。
    if path.is_symlink():

        # 返回 is_managed 已整理完成的调用载荷。
        return True

    # 检查 is_managed 的当前条件是否需要进入专门分支。
    if path.exists() and path.is_file():

        # 保护 is_managed 中允许失败的外部访问。
        try:

            # 返回 is_managed 已整理完成的调用载荷。
            return path.read_text(encoding="utf-8", errors="ignore").startswith(MANAGED_PREFIX)
        except OSError:

            # 返回 is_managed 已整理完成的调用载荷。
            return False

    # 返回 is_managed 已整理完成的调用载荷。
    return False


# 定义 create_link_or_shim 的脚本治理处理入口。
def create_link_or_shim(path: Path, warnings: list[str], actions: list[str]) -> None:

    # 检查 create_link_or_shim 的当前条件是否需要进入专门分支。
    if path.exists() and not is_managed(path):

        # 调用 append 完成 create_link_or_shim 的当前动作。
        warnings.append(f"Preserved existing non-managed {path.name}")

        # 返回 create_link_or_shim 已整理完成的调用载荷。
        return

    # 检查 create_link_or_shim 的当前条件是否需要进入专门分支。
    if path.exists() or path.is_symlink():

        # 调用 unlink 完成 create_link_or_shim 的当前动作。
        path.unlink()

    # 保护 create_link_or_shim 中允许失败的外部访问。
    try:

        # 调用 symlink 完成 create_link_or_shim 的当前动作。
        os.symlink("AGENTS.md", path)

        # 调用 append 完成 create_link_or_shim 的当前动作。
        actions.append(f"Created symlink {path.name} -> AGENTS.md")
    except OSError:

        # 调用 write_text 完成 create_link_or_shim 的当前动作。
        path.write_text(f"{MANAGED_PREFIX} shim -->\n@AGENTS.md\n", encoding="utf-8")

        # 调用 append 完成 create_link_or_shim 的当前动作。
        warnings.append(f"Symlink unavailable; wrote managed shim {path.name}")


# 定义 should_skip 的脚本治理处理入口。
def should_skip(path: Path, project: Path, include_skipped: bool = False) -> bool:

    # 检查 should_skip 的当前条件是否需要进入专门分支。
    if include_skipped:

        # 返回 should_skip 已整理完成的调用载荷。
        return False

    # 保护 should_skip 中允许失败的外部访问。
    try:

        # 收集 parts 条目，保持 should_skip 的处理顺序稳定。
        parts = path.relative_to(project).parts  # parts 用于本步治理判断
    except ValueError:

        # 收集 parts 条目，保持 should_skip 的处理顺序稳定。
        parts = path.parts  # parts 用于本步治理判断

    # 返回 should_skip 已整理完成的调用载荷。
    return bool(set(parts) & SKIP_DIRS)


# 定义 main 的脚本治理处理入口。
def main() -> None:

    # 保留 parser 中间值，支撑 main 的当前计算步骤。
    parser = argparse.ArgumentParser(description="Create CLAUDE.md and GEMINI.md shims for AGENTS.md files.")  # parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("--include-skipped", action="store_true", help="Also scan skipped directories such as ref, vendor, and build outputs.")

    # 收集 args 条目，保持 main 的处理顺序稳定。
    args = parser.parse_args()  # args 用于本步治理判断

    # 保留 project 中间值，支撑 main 的当前计算步骤。
    project = resolve_project(args.project)  # project 用于本步治理判断

    # 收集 actions 条目，保持 main 的处理顺序稳定。
    list_actions: list[str] = []  # actions 用于本步治理判断

    # 收集 warnings 条目，保持 main 的处理顺序稳定。
    list_warnings: list[str] = []  # warnings 用于本步治理判断

    # 逐项推进 main 的候选项检查。
    for agents in sorted(project.rglob("AGENTS.md")):

        # 检查 main 的当前条件是否需要进入专门分支。
        if should_skip(agents, project, args.include_skipped):

            # 分隔 main 的控制流边界。
            continue

        # 逐项推进 main 的候选项检查。
        for name in ("CLAUDE.md", "GEMINI.md"):

            # 调用 create_link_or_shim 完成 main 的当前动作。
            create_link_or_shim(agents.parent / name, list_warnings, list_actions)

    # 调用 emit_json 完成 main 的当前动作。
    emit_json({"actions": list_actions, "warnings": list_warnings})


# 检查 模块入口 的当前条件是否需要进入专门分支。
if __name__ == "__main__":

    # 调用 main 完成 模块入口 的当前动作。
    main()


