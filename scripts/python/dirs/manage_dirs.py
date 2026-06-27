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
from pathlib import Path
import sys

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断
from agents_common import emit_json, resolve_project
from manage_dirs_review import (
    apply_structure_fix,
    review_change,
    structure_gate,
    takeover_fix,

    # 分隔当前密集代码块，保留原有执行顺序。
)
from manage_dirs_state import (
    CURRENT_STRUCTURE,
    DIR_MANAGER_DIR,
    DIR_MANAGER_MD,
    PLANNED_STRUCTURE,

    # 再次分隔当前长代码块，降低连续语句密度。
    archive_dir_manager,
    init_dir_manager,
    scan_structure,
    verify_dir_manager,
)


# 定义 run_scan_command 的目录治理处理入口。
def run_scan_command(project: Path, args: argparse.Namespace) -> dict[str, object]:
    """执行 scan 子命令，并在 --write 时刷新当前结构快照。

    数组契约:
        shape/维度: 本函数处理目录结构 JSON，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 Path、argparse.Namespace 和 dict 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义来自目录治理 schema。
    """

    # scan_structure 返回当前目录结构快照，后续可选写入 docs/dir_manager。
    dict_structure = scan_structure(project)  # 当前目录结构快照

    # --write 保持旧行为：同时创建 dir_manager 目录并写入 CURRENT_STRUCTURE。
    if args.write:

        # 创建 dir_manager 目录，确保结构快照文件可以落盘。
        (project / DIR_MANAGER_DIR).mkdir(parents=True, exist_ok=True)

        # 写入当前结构快照，供后续 review/verify 使用。
        (project / CURRENT_STRUCTURE).write_text(
            json.dumps(dict_structure, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    # 返回 scan 子命令的 JSON 载荷。
    return dict_structure


# 定义 dispatch_manage_dirs_command 的目录治理处理入口。
def dispatch_manage_dirs_command(project: Path, args: argparse.Namespace) -> dict[str, object]:
    """执行 manage_dirs 子命令并返回统一 JSON 载荷。

    数组契约:
        shape/维度: 本函数处理 CLI 参数和目录治理 JSON，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 Path、argparse.Namespace 和 dict 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段语义来自 manage_dirs 子命令契约。
    """

    # 子命令映射保持 argparse 注册名和执行函数一一对应。
    dict_command_handlers = {  # manage_dirs 子命令执行表
        "scan": lambda: run_scan_command(project, args),  # 扫描目录结构
        "init": lambda: init_dir_manager(project),  # 初始化目录治理文件
        "review": lambda: review_change(project, args.input, dry_run=args.dry_run),  # 审查目录变更
        "structure-gate": lambda: structure_gate(project),  # 校验目录结构门禁
        "apply-structure-fix": lambda: apply_structure_fix(project),  # 应用结构修复
        "takeover-fix": lambda: takeover_fix(project),  # 应用接管结构修复
        "archive": lambda: archive_dir_manager(  # 归档目录治理历史
            project,  # 目录治理项目根
            reason=args.reason,  # 目录治理归档原因
            review_file=args.review_file,  # 目录治理关联审查文件
        ),
        "verify": lambda: verify_dir_manager(project),  # 校验目录治理文件
    }

    # argparse 已保证 command 合法；这里直接返回对应子命令载荷。
    return dict_command_handlers[args.command]()


# 定义 manage_dirs_command_failed 的目录治理处理入口。
def manage_dirs_command_failed(command: str, result: dict[str, object]) -> bool:
    """按目录治理子命令契约判断是否需要非零退出码。

    数组契约:
        shape/维度: 本函数判断 JSON 映射字段，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出为 str、dict 和 bool 业务类型，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义来自目录治理子命令 JSON 契约。
    """

    # 失败谓词复刻旧分支链的退出码条件。
    dict_failure_checks = {  # 每个目录子命令的 JSON 成功字段如何决定 main 是否 sys.exit(1)
        "review": lambda payload: not bool(payload["approved"]),  # review 未批准即阻断
        "structure-gate": lambda payload: not bool(payload["approved"]),  # 结构门禁未批准即阻断
        "apply-structure-fix": lambda payload: bool(payload["errors"]),  # 结构修复 errors 即阻断
        "takeover-fix": lambda payload: bool(payload["errors"]),  # 接管修复 errors 即阻断
        "verify": lambda payload: bool(payload["errors"]),  # verify 返回 errors 时目录治理失败
    }

    # 未登记失败谓词的命令沿用零退出码行为。
    command_failed = dict_failure_checks.get(command, lambda payload: False)  # 目录治理当前失败谓词

    # 返回当前子命令是否需要中断调用方流程。
    return command_failed(result)


# 定义 main 的脚本治理处理入口。
def main() -> None:

    # 保留 parser 中间值，支撑 main 的当前计算步骤。
    parser = argparse.ArgumentParser(description="Review and verify strict project directory management gates.")  # parser 用于本步治理判断

    # 收集 subparsers 条目，保持 main 的处理顺序稳定。
    subparsers = parser.add_subparsers(dest="command", required=True)  # subparsers 用于本步治理判断

    # 保留 scan parser 中间值，支撑 main 的当前计算步骤。
    scan_parser = subparsers.add_parser("scan")  # scan parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    scan_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    scan_parser.add_argument("--write", action="store_true")

    # 保留 init parser 中间值，支撑 main 的当前计算步骤。
    init_parser = subparsers.add_parser("init")  # init parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    init_parser.add_argument("project", nargs="?", default=".")

    # 保留 review parser 中间值，支撑 main 的当前计算步骤。
    review_parser = subparsers.add_parser("review")  # review parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    review_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    review_parser.add_argument("--input", required=True)

    # 调用 add_argument 完成 main 的当前动作。
    review_parser.add_argument("--dry-run", action="store_true")

    # 保留 structure parser 中间值，支撑 main 的当前计算步骤。
    structure_parser = subparsers.add_parser("structure-gate")  # structure parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    structure_parser.add_argument("project", nargs="?", default=".")

    # 保留 apply fix parser 中间值，支撑 main 的当前计算步骤。
    apply_fix_parser = subparsers.add_parser("apply-structure-fix")  # apply fix parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    apply_fix_parser.add_argument("project", nargs="?", default=".")

    # 保留 takeover fix parser 中间值，支撑 main 的当前计算步骤。
    takeover_fix_parser = subparsers.add_parser("takeover-fix")  # takeover fix parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    takeover_fix_parser.add_argument("project", nargs="?", default=".")

    # 保留 archive parser 中间值，支撑 main 的当前计算步骤。
    archive_parser = subparsers.add_parser("archive")  # archive parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    archive_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    archive_parser.add_argument("--reason", default="force-confirmed directory override")

    # 调用 add_argument 完成 main 的当前动作。
    archive_parser.add_argument("--review-file", default="")

    # 保留 verify parser 中间值，支撑 main 的当前计算步骤。
    verify_parser = subparsers.add_parser("verify")  # verify parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    verify_parser.add_argument("project", nargs="?", default=".")

    # 收集 args 条目，保持 main 的处理顺序稳定。
    args = parser.parse_args()  # args 用于本步治理判断

    # 保留 project 中间值，支撑 main 的当前计算步骤。
    project = resolve_project(args.project)  # project 用于本步治理判断

    # 目录治理子命令统一通过分派函数执行，保持 main 只负责解析和退出码。
    dict_command_result = dispatch_manage_dirs_command(project, args)  # 目录治理子命令执行结果

    # 所有目录治理子命令保持 JSON 输出契约。
    emit_json(dict_command_result)

    # 分派后的失败判断沿用原有退出码语义。
    if manage_dirs_command_failed(args.command, dict_command_result):

        # 抛出 main 已确认的阻断原因。
        raise SystemExit(1)


# 检查 模块入口 的当前条件是否需要进入专门分支。
if __name__ == "__main__":

    # 调用 main 完成 模块入口 的当前动作。
    main()


