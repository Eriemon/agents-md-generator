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
import re
import subprocess
import sys
from pathlib import Path

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断
from agents_common import SCRIPT_TASK_BY_NAME, resolve_project


STALE_NUMBERED_SHARD_RE = re.compile(r"(?:^|[_./\\])part\d+\.py\b|eval_runtime_cases_part\d|_version_policy_part\d")


def stale_numbered_shard_errors(skill_dir: Path) -> list[str]:
    """检查运行时 Python 入口是否仍引用旧的 numbered shard 名称。"""

    scripts_python_root = skill_dir / "scripts" / "python"  # Python 运行时根目录

    if not scripts_python_root.is_dir():
        return []

    errors: list[str] = []  # 轻量预检错误

    for path in sorted(scripts_python_root.rglob("*.py")):
        relative_path = path.relative_to(skill_dir).as_posix()  # 技能内相对路径
        text = path.read_text(encoding="utf-8", errors="ignore")  # Python 源码文本

        if STALE_NUMBERED_SHARD_RE.search(text):
            errors.append(f"{relative_path}: stale numbered shard reference")

    return errors


def registered_script_errors(skill_dir: Path) -> list[str]:
    """确认脚本登记表中的任务分类入口都真实存在。"""

    scripts_python_root = skill_dir / "scripts" / "python"  # Python 运行时根目录

    if not scripts_python_root.is_dir():
        return []

    errors: list[str] = []  # 登记一致性错误

    for script_name, task_name in sorted(SCRIPT_TASK_BY_NAME.items()):
        script_path = scripts_python_root / task_name / script_name  # 登记脚本路径

        if not script_path.is_file():
            errors.append(f"missing registered task-classified script: scripts/python/{task_name}/{script_name}")

    return errors


def self_governance_preflight_errors(skill_dir: Path) -> list[str]:
    """执行 skill-creator quick_validate 之前的 agents-md-generator 自检。"""

    skill_path = skill_dir / "SKILL.md"  # 技能说明文件

    if skill_dir.name != "agents-md-generator" or not skill_path.is_file():
        return []

    return stale_numbered_shard_errors(skill_dir) + registered_script_errors(skill_dir)


# 定义 quick_validate_path 的脚本治理处理入口。
def quick_validate_path() -> Path:

    # 返回 quick_validate_path 已整理完成的调用载荷。
    return Path.home() / ".codex" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py"


# 定义 main 的脚本治理处理入口。
def main() -> None:

    # 保留 parser 中间值，支撑 main 的当前计算步骤。
    parser = argparse.ArgumentParser(description="Run the installed skill-creator quick_validate helper.")  # parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    parser.add_argument("skill_dir", nargs="?", default=".")

    # 收集 args 条目，保持 main 的处理顺序稳定。
    args = parser.parse_args()  # args 用于本步治理判断

    # 保留 skill dir 中间值，支撑 main 的当前计算步骤。
    skill_dir = resolve_project(args.skill_dir)  # skill dir 用于本步治理判断

    # 先运行本技能自己的轻量入口治理检查，避免外部 quick_validate 漏过运行时分片退化。
    list_preflight_errors = self_governance_preflight_errors(skill_dir)  # 预检错误列表

    if list_preflight_errors:
        for item in list_preflight_errors:
            sys.stderr.write(f"{item}\n")

        raise SystemExit(1)

    # 保留 validator 中间值，支撑 main 的当前计算步骤。
    path_validator = quick_validate_path()  # validator 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if not path_validator.exists():

        # 抛出 main 已确认的阻断原因。
        raise SystemExit(f"quick_validate helper not found: {path_validator}")

    # 保留 result 中间值，支撑 main 的当前计算步骤。
    command_result = subprocess.run(  # result 用于本步治理判断
        [sys.executable, str(path_validator), str(skill_dir)],  # result 用于本步治理判断
        cwd=skill_dir.parent,  # result 用于本步治理判断
        text=True,  # result 用于本步治理判断
        capture_output=True,  # result 用于本步治理判断
        check=False,  # result 用于本步治理判断
        env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1"),  # result 用于本步治理判断
    )

    # 检查 main 的当前条件是否需要进入专门分支。
    if command_result.stdout:

        # 调用 write 完成 main 的当前动作。
        sys.stdout.write(command_result.stdout)

    # 检查 main 的当前条件是否需要进入专门分支。
    if command_result.stderr:

        # 调用 write 完成 main 的当前动作。
        sys.stderr.write(command_result.stderr)

    # 抛出 main 已确认的阻断原因。
    raise SystemExit(command_result.returncode)


if __name__ == "__main__":
    main()
