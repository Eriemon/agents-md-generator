"""提供 docs、memory、handoff 和 release 治理命令的统一 CLI 入口。"""

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
import argparse
from pathlib import Path
import sys

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断

# 导入 脚本治理 所需的依赖模块。
from agents_common import emit_json, resolve_project
from manage_docs_release import *
from manage_docs_scaffold_session import *
from manage_docs_shared import *
from manage_docs_memory import *
from manage_docs_sync_verify import *

# 定义 dispatch_manage_docs_command 的脚本治理处理入口。
def dispatch_manage_docs_command(project: Path, args: argparse.Namespace) -> dict[str, object]:
    """执行 manage_docs 子命令并返回统一 JSON 载荷。

    数组契约:
        shape/维度: 本函数处理 CLI 参数和治理 JSON 映射，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出由 argparse.Namespace、Path 和 dict 业务类型约束，非 ndarray dtype。
        unit/单位: 无物理量单位，字段语义来自 manage_docs 子命令契约。
    """

    # 子命令到执行函数的映射保持 CLI 名称和治理函数一一对应。
    dict_command_handlers = {  # 每个 manage_docs command 对应的实际治理动作，替代 main 的分支链
        "scaffold": lambda: scaffold(project),  # 初始化 docs 治理结构
        "preflight": lambda: preflight_docs(project),  # 检查 docs 治理预备条件
        "handoff": lambda: write_handoff(project, args.input),  # 写入交接记录
        "start-session": lambda: write_active_session(project, args.input),  # 写入活跃会话记录
        "resume-check": lambda: resume_check(project, args.conversation_log),  # 检查恢复状态
        "resume-repair": lambda: resume_repair(project, args.input),  # 修复恢复状态
        "memory-init": lambda: init_memory(project, confirm_create=args.confirm_create, require_confirmation=True),  # 初始化 memory 存储
        "memory-gate": lambda: memory_gate(project),  # 检查 memory 门禁
        "memory-bootstrap-sessions": lambda: bootstrap_sessions(project),  # 从会话补齐 memory
        "memory-write": lambda: write_memory(project, args.input),  # 写入 memory 事件
        "memory-compress": lambda: compress_memory(project),  # 压缩 memory 摘要
        "memory-read": lambda: read_memory(project, args.query, args.limit),  # 查询 memory 摘要
        "memory-verify": lambda: verify_memory(project),  # 校验 memory 文件
        "repair-handoff-names": lambda: repair_handoff_names(project, write=args.write),  # 修复 handoff 命名
        "development": lambda: write_development(project, args.stage, args.input),  # 写入开发记录
        "git-changelog": lambda: write_git_changelog(project, args.input),  # 写入 git 变更记录
        "sync-root-agents": lambda: sync_root_agents(  # 同步当前项目根 AGENTS 受管 baseline
            project,  # 当前工作文件夹根目录
            write=args.write,  # 写入模式决定是否落盘
            installed_skill_dir_override=args.installed_skill_dir,  # 可选安装技能目录覆盖
            mark_verified=args.mark_verified,  # 同步后是否标记已验证
        ),
        "sync-global-codex-agents": lambda: sync_global_codex_agents(  # 同步全局 Codex AGENTS baseline
            project,  # 当前项目用于推导全局治理来源
            write=args.write,  # 写入模式决定是否修改全局文件
            codex_home=args.codex_home,  # 用户显式指定的 Codex home
        ),
        "release-gate": lambda: release_gate(  # 执行发布前后治理门禁
            project,  # 发布门禁归属项目
            args.version,  # 发布版本号
            args.skill_dir,  # 待发布技能目录
            args.phase,  # 发布阶段 pre 或 post
            args.install_intent,  # 安装意图用于区分 release 后续动作
        ),
        "release-prepare": lambda: release_prepare(project, args.version, args.skill_dir),  # 准备 release 分支和 changelog
        "package-release": lambda: package_release(project, args.version, args.skill_dir),  # 生成可安装 dist 目录和归档
        "branch-gate": lambda: branch_gate(project),  # 检查当前分支是否允许继续
        "work-folder-gate": lambda: work_folder_gate(project, args.skill_dir, args.mode),  # 检查工作文件夹和 skill 目录关系
        "verify": lambda: verify_docs(project),  # 校验 docs 治理结构
    }

    # argparse 已保证 command 合法；这里直接分派保持失败面清晰。
    return dict_command_handlers[args.command]()


# 定义 manage_docs_command_failed 的脚本治理处理入口。
def manage_docs_command_failed(args: argparse.Namespace, result: dict[str, object]) -> bool:
    """按子命令契约判断 manage_docs 是否需要返回非零退出码。

    数组契约:
        shape/维度: 本函数判断 JSON 映射中的错误字段，不接收数值数组，数组维度不适用。
        dtype/类型: 输入输出为 argparse.Namespace、dict 和 bool 业务类型，非 ndarray dtype。
        unit/单位: 无物理量单位，字段含义来自各治理子命令的 JSON 契约。
    """

    # 子命令失败谓词保留旧分支链的退出码语义。
    dict_failure_checks = {  # manage_docs 子命令失败谓词表
        "scaffold": lambda payload: bool(payload.get("errors")),  # scaffold errors 表示阻断
        "handoff": lambda payload: bool(payload.get("errors")),  # handoff errors 表示阻断
        "start-session": lambda payload: bool(payload.get("errors")),  # start-session errors 表示阻断
        "resume-check": lambda payload: bool(payload.get("blocking")),  # resume-check blocking 表示阻断
        "resume-repair": lambda payload: bool(payload.get("errors")),  # resume-repair errors 表示阻断
        "memory-init": lambda payload: bool(payload.get("errors")),  # memory-init errors 表示阻断
        "memory-gate": lambda payload: bool(  # memory 缺失或需用户授权时阻断
            payload.get("errors") or payload.get("requires_user_authorization")  # memory 门禁阻断字段
        ),
        "memory-bootstrap-sessions": lambda payload: bool(payload.get("errors")),  # bootstrap errors 表示阻断
        "memory-write": lambda payload: bool(payload.get("errors")),  # memory-write errors 表示阻断
        "memory-compress": lambda payload: bool(payload.get("errors")),  # memory-compress errors 表示阻断
        "memory-read": lambda payload: bool(payload.get("errors")),  # memory-read errors 表示阻断
        "memory-verify": lambda payload: bool(payload.get("errors")),  # memory-verify errors 表示阻断
        "repair-handoff-names": lambda payload: bool(  # handoff 命名修复失败或仍阻断时退出
            payload.get("errors")  # handoff 修复错误字段
            or (args.write and payload.get("handoff_naming", {}).get("blocking"))  # 写入后仍有命名阻断
        ),
        "sync-root-agents": lambda payload: bool(payload.get("errors")),  # 根 AGENTS 同步 errors 表示阻断
        "sync-global-codex-agents": lambda payload: bool(payload.get("errors")),  # 全局 baseline 同步 errors 表示阻断
        "release-gate": lambda payload: bool(payload["errors"]),  # release-gate errors 表示阻断
        "release-prepare": lambda payload: bool(payload["errors"]),  # release-prepare errors 表示阻断
        "package-release": lambda payload: bool(payload["errors"]),  # package-release errors 表示阻断
        "branch-gate": lambda payload: not bool(payload["approved"]),  # branch-gate 未批准表示阻断
        "work-folder-gate": lambda payload: not bool(payload["ok"]),  # work-folder-gate 不通过表示阻断
        "verify": lambda payload: bool(payload["errors"]),  # docs verify errors 表示阻断
    }

    # 未登记失败谓词的只读/记录类命令沿用零退出码行为。
    command_failed = dict_failure_checks.get(args.command, lambda payload: False)  # manage_docs 当前失败谓词

    # 返回当前子命令是否应中断调用方流程。
    return command_failed(result)


# 定义 main 的脚本治理处理入口。
def main() -> None:

    # 保留 parser 中间值，支撑 main 的当前计算步骤。
    parser = argparse.ArgumentParser(description="Manage AGENTS.md docs governance artifacts.")  # parser 用于本步治理判断

    # 收集 subparsers 条目，保持 main 的处理顺序稳定。
    subparsers = parser.add_subparsers(dest="command", required=True)  # subparsers 用于本步治理判断

    # 命令注册必须与下方分派链保持一一对应，避免新增治理命令只注册不执行。
    scaffold_parser = subparsers.add_parser("scaffold")  # scaffold parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    scaffold_parser.add_argument("project", nargs="?", default=".")

    # 保留 preflight parser 中间值，支撑 main 的当前计算步骤。
    preflight_parser = subparsers.add_parser("preflight")  # preflight parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    preflight_parser.add_argument("project", nargs="?", default=".")

    # 保留 handoff parser 中间值，支撑 main 的当前计算步骤。
    handoff_parser = subparsers.add_parser("handoff")  # handoff parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    handoff_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    handoff_parser.add_argument("--input", default=None)

    # 保留 start session parser 中间值，支撑 main 的当前计算步骤。
    start_session_parser = subparsers.add_parser("start-session")  # start session parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    start_session_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    start_session_parser.add_argument("--input", default=None)

    # 保留 resume check parser 中间值，支撑 main 的当前计算步骤。
    resume_check_parser = subparsers.add_parser("resume-check")  # resume check parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    resume_check_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    resume_check_parser.add_argument("--conversation-log", default=None)

    # 保留 resume repair parser 中间值，支撑 main 的当前计算步骤。
    resume_repair_parser = subparsers.add_parser("resume-repair")  # resume repair parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    resume_repair_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    resume_repair_parser.add_argument("--input", default=None)

    # 保留 memory init parser 中间值，支撑 main 的当前计算步骤。
    memory_init_parser = subparsers.add_parser("memory-init")  # memory init parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    memory_init_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    memory_init_parser.add_argument("--confirm-create", action="store_true")

    # 保留 memory gate parser 中间值，支撑 main 的当前计算步骤。
    memory_gate_parser = subparsers.add_parser("memory-gate")  # memory gate parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    memory_gate_parser.add_argument("project", nargs="?", default=".")

    # 保留 memory bootstrap parser 中间值，支撑 main 的当前计算步骤。
    memory_bootstrap_parser = subparsers.add_parser("memory-bootstrap-sessions")  # memory bootstrap parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    memory_bootstrap_parser.add_argument("project", nargs="?", default=".")

    # 保留 memory write parser 中间值，支撑 main 的当前计算步骤。
    memory_write_parser = subparsers.add_parser("memory-write")  # memory write parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    memory_write_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    memory_write_parser.add_argument("--input", required=True)

    # 保留 memory compress parser 中间值，支撑 main 的当前计算步骤。
    memory_compress_parser = subparsers.add_parser("memory-compress")  # memory compress parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    memory_compress_parser.add_argument("project", nargs="?", default=".")

    # 保留 memory read parser 中间值，支撑 main 的当前计算步骤。
    memory_read_parser = subparsers.add_parser("memory-read")  # memory read parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    memory_read_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    memory_read_parser.add_argument("--query", required=True)

    # 调用 add_argument 完成 main 的当前动作。
    memory_read_parser.add_argument("--limit", type=int, default=5)

    # 保留 memory verify parser 中间值，支撑 main 的当前计算步骤。
    memory_verify_parser = subparsers.add_parser("memory-verify")  # memory verify parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    memory_verify_parser.add_argument("project", nargs="?", default=".")

    # 保留 repair handoff parser 中间值，支撑 main 的当前计算步骤。
    repair_handoff_parser = subparsers.add_parser("repair-handoff-names")  # repair handoff parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    repair_handoff_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    repair_handoff_parser.add_argument("--write", action="store_true")

    # 保留 development parser 中间值，支撑 main 的当前计算步骤。
    development_parser = subparsers.add_parser("development")  # development parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    development_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    development_parser.add_argument("--stage", required=True)

    # 调用 add_argument 完成 main 的当前动作。
    development_parser.add_argument("--input", default=None)

    # 保留 changelog parser 中间值，支撑 main 的当前计算步骤。
    changelog_parser = subparsers.add_parser("git-changelog")  # changelog parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    changelog_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    changelog_parser.add_argument("--input", default=None)

    # 保留 sync root parser 中间值，支撑 main 的当前计算步骤。
    sync_root_parser = subparsers.add_parser("sync-root-agents")  # sync root parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    sync_root_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    sync_root_parser.add_argument("--write", action="store_true")

    # 调用 add_argument 完成 main 的当前动作。
    sync_root_parser.add_argument("--installed-skill-dir", default=None)

    # 调用 add_argument 完成 main 的当前动作。
    sync_root_parser.add_argument("--mark-verified", action="store_true")

    # 保留 sync global parser 中间值，支撑 main 的当前计算步骤。
    sync_global_parser = subparsers.add_parser("sync-global-codex-agents")  # sync global parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    sync_global_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    sync_global_parser.add_argument("--write", action="store_true")

    # 调用 add_argument 完成 main 的当前动作。
    sync_global_parser.add_argument("--codex-home", default=None)

    # 保留 release gate parser 中间值，支撑 main 的当前计算步骤。
    release_gate_parser = subparsers.add_parser("release-gate")  # release gate parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    release_gate_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    release_gate_parser.add_argument("--version", required=True)

    # 调用 add_argument 完成 main 的当前动作。
    release_gate_parser.add_argument("--skill-dir", required=True)

    # 调用 add_argument 完成 main 的当前动作。
    release_gate_parser.add_argument("--phase", choices=["pre", "post"], default="pre")

    # 调用 add_argument 完成 main 的当前动作。
    release_gate_parser.add_argument("--install-intent", choices=["unspecified", "requested", "skipped"], default="unspecified")

    # 保留 release prepare parser 中间值，支撑 main 的当前计算步骤。
    release_prepare_parser = subparsers.add_parser("release-prepare")  # release prepare parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    release_prepare_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    release_prepare_parser.add_argument("--version", required=True)

    # 调用 add_argument 完成 main 的当前动作。
    release_prepare_parser.add_argument("--skill-dir", required=True)

    # 保留 package release parser 中间值，支撑 main 的当前计算步骤。
    package_release_parser = subparsers.add_parser("package-release")  # package release parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    package_release_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    package_release_parser.add_argument("--version", required=True)

    # 调用 add_argument 完成 main 的当前动作。
    package_release_parser.add_argument("--skill-dir", required=True)

    # 保留 branch gate parser 中间值，支撑 main 的当前计算步骤。
    branch_gate_parser = subparsers.add_parser("branch-gate")  # branch gate parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    branch_gate_parser.add_argument("project", nargs="?", default=".")

    # 保留 work folder gate parser 中间值，支撑 main 的当前计算步骤。
    work_folder_gate_parser = subparsers.add_parser("work-folder-gate")  # work folder gate parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    work_folder_gate_parser.add_argument("project", nargs="?", default=".")

    # 调用 add_argument 完成 main 的当前动作。
    work_folder_gate_parser.add_argument("--skill-dir", required=True)

    # 调用 add_argument 完成 main 的当前动作。
    work_folder_gate_parser.add_argument("--mode", choices=["development", "release"], default="development")

    # 保留 verify parser 中间值，支撑 main 的当前计算步骤。
    verify_parser = subparsers.add_parser("verify")  # verify parser 用于本步治理判断

    # 调用 add_argument 完成 main 的当前动作。
    verify_parser.add_argument("project", nargs="?", default=".")

    # 收集 args 条目，保持 main 的处理顺序稳定。
    args = parser.parse_args()  # args 用于本步治理判断

    # 保留 project 中间值，支撑 main 的当前计算步骤。
    project = resolve_project(args.project)  # project 用于本步治理判断

    # CLI 对外契约是稳定 JSON 输出加退出码，调用方依赖该结构做治理门禁判断。
    dict_command_result = dispatch_manage_docs_command(project, args)  # 子命令执行结果

    # 所有 manage_docs 子命令都通过统一出口写 JSON，保持调用方解析稳定。
    emit_json(dict_command_result)

    # 子命令失败谓词集中在分派表，避免 main 形成深层分支链。
    if manage_docs_command_failed(args, dict_command_result):

        # 抛出 main 已确认的阻断原因。
        raise SystemExit(1)

# 检查 模块入口 的当前条件是否需要进入专门分支。
if __name__ == "__main__":

    # 调用 main 完成 模块入口 的当前动作。
    main()


