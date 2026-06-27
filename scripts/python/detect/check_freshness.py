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
import re
from datetime import datetime
from pathlib import Path
import sys

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断
from agents_common import emit_json, resolve_project, run_git


# 保留 TIMESTAMP RE 中间值，支撑 模块入口 的当前计算步骤。
TIMESTAMP_RE = re.compile(r"Last updated:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")  # TIMESTAMP RE 用于本步治理判断

# 保留 DATE RE 中间值，支撑 模块入口 的当前计算步骤。
DATE_RE = re.compile(r"Last updated:\s*(\d{4}-\d{2}-\d{2})")  # DATE RE 用于本步治理判断

# 保留 VERIFIED RE 中间值，支撑 模块入口 的当前计算步骤。
VERIFIED_RE = re.compile(r"Last verified:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")  # VERIFIED RE 用于本步治理判断


# 定义 parse_datetime 的脚本治理处理入口。
def parse_datetime(raw: str) -> datetime | None:

    # 保护 parse_datetime 中允许失败的外部访问。
    try:

        # 返回 parse_datetime 已整理完成的调用载荷。
        return datetime.fromisoformat(raw)
    except ValueError:

        # 返回 parse_datetime 已整理完成的调用载荷。
        return None


# 定义 git_commit_time_for_file 的脚本治理处理入口。
def git_commit_time_for_file(project: Path, path: Path) -> datetime | None:

    # 保护 git_commit_time_for_file 中允许失败的外部访问。
    try:

        # 定位 rel path 的文件边界，供 git_commit_time_for_file 后续读写校验使用。
        str_rel_path = path.relative_to(project).as_posix()  # rel path 用于本步治理判断
    except ValueError:

        # 定位 rel path 的文件边界，供 git_commit_time_for_file 后续读写校验使用。
        str_rel_path = str(path)  # rel path 用于本步治理判断

    # 保留 result 中间值，支撑 git_commit_time_for_file 的当前计算步骤。
    command_result = run_git(project, ["log", "-1", "--format=%cI", "--", str_rel_path])  # result 用于本步治理判断

    # 检查 git_commit_time_for_file 的当前条件是否需要进入专门分支。
    if command_result.returncode != 0:

        # 返回 git_commit_time_for_file 已整理完成的调用载荷。
        return None

    # 保留 raw 中间值，支撑 git_commit_time_for_file 的当前计算步骤。
    raw = command_result.stdout.strip()  # raw 用于本步治理判断

    # 返回 git_commit_time_for_file 已整理完成的调用载荷。
    return parse_datetime(raw) if raw else None


# 定义 file_mtime 的脚本治理处理入口。
def file_mtime(path: Path) -> datetime | None:

    # 保护 file_mtime 中允许失败的外部访问。
    try:

        # 返回 file_mtime 已整理完成的调用载荷。
        return datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:

        # 返回 file_mtime 已整理完成的调用载荷。
        return None


# 定义 normalize_datetime 的脚本治理处理入口。
def normalize_datetime(value: datetime) -> str:

    # 返回 normalize_datetime 已整理完成的调用载荷。
    return value.isoformat(timespec="seconds")


# 定义 comparable_datetime 的脚本治理处理入口。
def comparable_datetime(value: datetime) -> datetime:

    # 返回 comparable_datetime 已整理完成的调用载荷。
    return value.replace(tzinfo=None)


# 定义 main 的脚本治理处理入口。
def main() -> None:

    # 保留 parser 中间值，支撑 main 的当前计算步骤。
    parser = argparse.ArgumentParser(description="Check whether AGENTS.md may be stale versus git history.")  # parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("project", nargs="?", default=".")

    # 收集 args 条目，保持 main 的处理顺序稳定。
    args = parser.parse_args()  # args 用于本步治理判断

    # 保留 project 中间值，支撑 main 的当前计算步骤。
    project = resolve_project(args.project)  # project 用于本步治理判断

    # 收集 agents 条目，保持 main 的处理顺序稳定。
    agents = project / "AGENTS.md"  # agents 用于本步治理判断

    # 收集 changed files 条目，保持 main 的处理顺序稳定。
    list_changed_files: list[str] = []  # changed files 用于本步治理判断

    # 保留 last updated 中间值，支撑 main 的当前计算步骤。
    last_updated = None  # last updated 用于本步治理判断

    # 保留 last updated raw 中间值，支撑 main 的当前计算步骤。
    last_updated_raw = None  # last updated raw 用于本步治理判断

    # 保留 last verified 中间值，支撑 main 的当前计算步骤。
    last_verified = None  # last verified 用于本步治理判断

    # 保留 last verified raw 中间值，支撑 main 的当前计算步骤。
    last_verified_raw = None  # last verified raw 用于本步治理判断

    # 保留 comparison source 中间值，支撑 main 的当前计算步骤。
    str_comparison_source = "missing"  # comparison source 用于本步治理判断

    # 保留 freshness source 中间值，支撑 main 的当前计算步骤。
    str_freshness_source = "missing"  # freshness source 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if agents.exists():

        # 保留 text 中间值，支撑 main 的当前计算步骤。
        text = agents.read_text(encoding="utf-8", errors="ignore")  # text 用于本步治理判断

        # 保留 verified match 中间值，支撑 main 的当前计算步骤。
        verified_match = VERIFIED_RE.search(text)  # verified match 用于本步治理判断

        # 检查 main 的当前条件是否需要进入专门分支。
        if verified_match:

            # 保留 last verified raw 中间值，支撑 main 的当前计算步骤。
            last_verified_raw = verified_match.group(1)  # last verified raw 用于本步治理判断

            # 保留 last verified 中间值，支撑 main 的当前计算步骤。
            last_verified = parse_datetime(last_verified_raw)  # last verified 用于本步治理判断

        # 保留 timestamp match 中间值，支撑 main 的当前计算步骤。
        timestamp_match = TIMESTAMP_RE.search(text)  # timestamp match 用于本步治理判断

        # 检查 main 的当前条件是否需要进入专门分支。
        if timestamp_match:

            # 保留 last updated raw 中间值，支撑 main 的当前计算步骤。
            last_updated_raw = timestamp_match.group(1)  # last updated raw 用于本步治理判断

            # 保留 last updated 中间值，支撑 main 的当前计算步骤。
            last_updated = parse_datetime(last_updated_raw)  # last updated 用于本步治理判断

            # 保留 comparison source 中间值，支撑 main 的当前计算步骤。
            str_comparison_source = "metadata_timestamp" if last_updated else "missing"  # comparison source 用于本步治理判断
        else:

            # 保留 date match 中间值，支撑 main 的当前计算步骤。
            date_match = DATE_RE.search(text)  # date match 用于本步治理判断

            # 检查 main 的当前条件是否需要进入专门分支。
            if date_match:

                # 保留 last updated raw 中间值，支撑 main 的当前计算步骤。
                last_updated_raw = date_match.group(1)  # last updated raw 用于本步治理判断

                # 保留 last updated 中间值，支撑 main 的当前计算步骤。
                last_updated = git_commit_time_for_file(project, agents)  # last updated 用于本步治理判断

                # 检查 main 的当前条件是否需要进入专门分支。
                if last_updated is not None:

                    # 保留 comparison source 中间值，支撑 main 的当前计算步骤。
                    str_comparison_source = "git_commit_time"  # comparison source 用于本步治理判断
                else:

                    # 保留 last updated 中间值，支撑 main 的当前计算步骤。
                    last_updated = file_mtime(agents)  # last updated 用于本步治理判断

                    # 检查 main 的当前条件是否需要进入专门分支。
                    if last_updated is not None:

                        # 保留 comparison source 中间值，支撑 main 的当前计算步骤。
                        str_comparison_source = "file_mtime"  # comparison source 用于本步治理判断
                    else:

                        # 保留 fallback 中间值，支撑 main 的当前计算步骤。
                        fallback = parse_datetime(f"{last_updated_raw}T00:00:00")  # fallback 用于本步治理判断

                        # 保留 last updated 中间值，支撑 main 的当前计算步骤。
                        last_updated = fallback  # last updated 用于本步治理判断

                        # 保留 comparison source 中间值，支撑 main 的当前计算步骤。
                        str_comparison_source = "date_midnight_fallback" if fallback else "missing"  # comparison source 用于本步治理判断

    # 保留 freshness time 中间值，支撑 main 的当前计算步骤。
    freshness_time = last_updated  # freshness time 用于本步治理判断

    # 保留 freshness source 中间值，支撑 main 的当前计算步骤。
    str_freshness_source = str_comparison_source  # freshness source 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if last_verified and (not last_updated or comparable_datetime(last_verified) >= comparable_datetime(last_updated)):

        # 保留 freshness time 中间值，支撑 main 的当前计算步骤。
        freshness_time = last_verified  # freshness time 用于本步治理判断

        # 保留 freshness source 中间值，支撑 main 的当前计算步骤。
        str_freshness_source = "last_verified"  # freshness source 用于本步治理判断

        # 保留 comparison source 中间值，支撑 main 的当前计算步骤。
        str_comparison_source = "last_verified"  # comparison source 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if freshness_time:

        # 保留 git result 中间值，支撑 main 的当前计算步骤。
        git_result = run_git(project, ["log", "--name-only", "--pretty=format:", f"--since={normalize_datetime(freshness_time)}"])  # git result 用于本步治理判断
    else:

        # 保留 git result 中间值，支撑 main 的当前计算步骤。
        git_result = run_git(project, ["status", "--short"])  # git result 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if git_result.returncode == 0:

        # 收集 changed files 条目，保持 main 的处理顺序稳定。
        list_changed_files = sorted(  # changed files 用于本步治理判断
            {  # changed files 用于本步治理判断
                line.strip()  # changed files 用于本步治理判断
                for line in git_result.stdout.splitlines()  # changed files 用于本步治理判断
                if line.strip() and not line.strip().endswith("AGENTS.md")  # changed files 用于本步治理判断
            }
        )

    # 调用 emit_json 完成 main 的当前动作。
    emit_json({
        "agents_file": str(agents),
        "last_updated": normalize_datetime(last_updated) if last_updated else None,
        "last_updated_raw": last_updated_raw,
        "last_updated_at": normalize_datetime(last_updated) if last_updated else None,
        "last_verified": normalize_datetime(last_verified) if last_verified else None,
        "last_verified_raw": last_verified_raw,
        "last_verified_at": normalize_datetime(last_verified) if last_verified else None,
        "comparison_source": str_comparison_source,
        "freshness_source": str_freshness_source,
        "stale": bool(list_changed_files) or freshness_time is None,
        "changed_files": list_changed_files,
    })


# 检查 模块入口 的当前条件是否需要进入专门分支。
if __name__ == "__main__":

    # 调用 main 完成 模块入口 的当前动作。
    main()


