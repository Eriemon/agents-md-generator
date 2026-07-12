"""提供 docs、memory、handoff 和 release 治理命令的统一 CLI 入口。"""

# 延迟注解解析，保持命令行入口兼容 Python 3.10。
from __future__ import annotations

# 标准库负责参数解析、模块加载、路径处理和进程退出。
import argparse
import importlib
from pathlib import Path
import sys
from typing import Any, Callable

# 入口必须在动态导入治理分片前关闭字节码写入，避免污染技能源码目录。
sys.dont_write_bytecode = True  # resume-check 等公共命令的进程级缓存保护。

# 治理实现按职责拆分在这些稳定模块中。
DOCS_IMPLEMENTATION_MODULES = (  # 文档治理实现模块加载顺序。
    "manage_docs_release",  # 发布门禁、准备和打包实现。
    "manage_docs_scaffold_session",  # 脚手架、会话和交接实现。
    "manage_docs_shared",  # 文档路径与公共合同实现。
    "manage_docs_memory",  # 记忆初始化、读写和压缩实现。
    "manage_docs_sync_verify",  # AGENTS 同步与文档验证实现。
)

# 直接执行时按需登记兄弟任务目录，导入本模块不会修改搜索路径。
def load_task_module(str_module_name: str) -> Any:
    """从 scripts/python 的任务目录加载模块。

    参数：str_module_name 为不含路径和扩展名的模块名。
    返回：已完成导入的模块对象。
    """

    # docs 的父目录包含 common、release 等兄弟任务目录。
    path_python_root = Path(__file__).resolve().parents[1]  # Python 任务模块共同根目录。

    # 只有真实任务目录可以加入模块搜索范围。
    for path_task_dir in path_python_root.iterdir():

        # 根目录中的普通文件不参与模块发现。
        if not path_task_dir.is_dir():

            # 继续检查其余任务目录。
            continue

        # sys.path 使用字符串形式记录搜索位置。
        str_task_dir = str(path_task_dir)  # 当前任务目录绝对路径。

        # 已登记目录保持原有解析优先级。
        if str_task_dir in sys.path:

            # 避免重复插入相同路径。
            continue

        # 源码任务目录应优先于环境中的同名模块。
        sys.path.insert(0, str_task_dir)

    # 搜索路径就绪后按稳定模块名导入。
    return importlib.import_module(str_module_name)

# 实现查找器保持原聚合入口的公开函数覆盖范围。
def docs_function(str_function_name: str) -> Callable[..., Any]:
    """查找文档治理实现函数。

    参数：str_function_name 为原 manage_docs 聚合入口公开的函数名。
    返回：拥有该名称的首个实现模块中的可调用对象。
    异常：没有模块公开目标函数时抛出 RuntimeError。
    """

    # 固定模块顺序避免同名辅助函数产生不稳定解析。
    for str_module_name in DOCS_IMPLEMENTATION_MODULES:

        # importlib 缓存保证同一进程内不会重复执行模块。
        module_docs_context = load_task_module(str_module_name)  # 当前文档治理实现模块。

        # 仅公开存在且可调用的实现属性。
        if hasattr(module_docs_context, str_function_name):

            # getattr 保留原函数对象的参数和返回行为。
            function_candidate = getattr(module_docs_context, str_function_name)  # 候选治理函数。

            # 非函数同名常量不能作为分派目标。
            if callable(function_candidate):

                # 调用方获得真实实现而非额外行为包装。
                return function_candidate

    # 缺少实现表示聚合入口与职责模块发生漂移。
    raise RuntimeError("> ERR: [Python] docs governance implementation is unavailable")

# 兼容导出供设计和渲染模块初始化文档治理结构。
def scaffold(path_project: Path) -> dict[str, object]:
    """初始化项目文档治理结构。

    参数：path_project 为项目根目录。
    返回：脚手架写入结果与诊断。
    """

    # 脚手架职责仍由原实现模块拥有。
    return docs_function("scaffold")(path_project)

# 兼容导出供渲染流程执行文档前置检查。
def preflight_docs(path_project: Path) -> dict[str, object]:
    """检查文档治理结构是否可以继续工作。

    参数：path_project 为项目根目录。
    返回：前置检查状态和诊断。
    """

    # 包装器不改变原预检结果。
    return docs_function("preflight_docs")(path_project)

# 兼容导出供渲染和发布流程检查当前分支。
def branch_gate(path_project: Path) -> dict[str, object]:
    """检查当前分支是否允许治理动作继续。

    参数：path_project 为项目根目录。
    返回：批准状态、分支事实和原因。
    """

    # 发布模块保持分支判断的事实来源。
    return docs_function("branch_gate")(path_project)

# 兼容导出供 verify_agents 复用文档完整性检查。
def verify_docs(path_project: Path) -> dict[str, object]:
    """验证项目文档治理结构。

    参数：path_project 为项目根目录。
    返回：检查文件列表与错误集合。
    """

    # 同步验证模块执行完整检查链。
    return docs_function("verify_docs")(path_project)

# 兼容导出供发布准备测试复用治理路径匹配规则。
def matches_governed_path(str_path: str, list_prefixes: list[str]) -> bool:
    """判断仓库相对路径是否属于受管前缀。

    参数：str_path 为待检查路径；list_prefixes 为允许的顶层前缀。
    返回：路径命中任一治理前缀时返回真。
    """

    # 发布模块继续拥有路径匹配的单一事实来源。
    return docs_function("matches_governed_path")(str_path, list_prefixes)

# 兼容导出供发布准备复用 Git 分支列表解析规则。
def normalize_branch_list_line(str_line: str) -> str:
    """移除 Git 分支列表中的状态标记和缩进。

    参数：str_line 为 git branch 输出中的单行文本。
    返回：不含当前分支或 linked-worktree 标记的分支名。
    """

    # 发布模块保持分支名称规范化的唯一实现。
    return docs_function("normalize_branch_list_line")(str_line)

# 兼容导出供发布准备和净化回归测试复用文本清洗规则。
def sanitize_release_text(str_source: str) -> tuple[str, list[str]]:
    """清洗发布文本中的本地路径和敏感值。

    参数：str_source 为待进入发布包的文本内容。
    返回：清洗后的文本以及命中规则列表。
    """

    # 发布模块执行与打包流程完全相同的清洗逻辑。
    return docs_function("sanitize_release_text")(str_source)

# 子命令分派表集中维护 CLI 名称和实现函数关系。
def dispatch_manage_docs_command(path_project: Path, namespace_args: argparse.Namespace) -> dict[str, object]:
    """执行 manage_docs 子命令并返回统一 JSON 载荷。

    参数：path_project 为项目根；namespace_args 为已解析命令行参数。
    返回：目标治理函数生成的结构化结果。
    """

    # 每个闭包仅在选中子命令时加载对应实现。
    dict_command_handlers: dict[str, Callable[[], dict[str, object]]] = {
        "scaffold": lambda: scaffold(path_project),  # 初始化文档治理结构。
        "preflight": lambda: preflight_docs(path_project),  # 检查文档治理前置条件。
        "handoff": lambda: docs_function("write_handoff")(path_project, namespace_args.input),  # 写入交接记录。
        "start-session": lambda: docs_function("write_active_session")(path_project, namespace_args.input),  # 写入活跃会话。
        "resume-check": lambda: docs_function("resume_check")(path_project, namespace_args.conversation_log),  # 检查恢复状态。
        "resume-repair": lambda: docs_function("resume_repair")(path_project, namespace_args.input),  # 修复中断状态。
        "memory-init": lambda: docs_function("init_memory")(  # 受授权保护的记忆初始化动作。
            path_project,  # 根规则写入目标所在项目。
            confirm_create=namespace_args.confirm_create,  # 用户创建授权。
            require_confirmation=True,  # CLI 始终执行授权检查。
        ),  # 初始化记忆存储。
        "memory-gate": lambda: docs_function("memory_gate")(path_project),  # 检查记忆门禁。
        "memory-bootstrap-sessions": lambda: docs_function("bootstrap_sessions")(path_project),  # 补录历史会话。
        "memory-write": lambda: docs_function("write_memory")(path_project, namespace_args.input),  # 写入记忆事件。
        "memory-compress": lambda: docs_function("compress_memory")(path_project),  # 压缩记忆摘要。
        "memory-read": lambda: docs_function("read_memory")(path_project, namespace_args.query, namespace_args.limit),  # 查询记忆内容。
        "memory-verify": lambda: docs_function("verify_memory")(path_project),  # 校验记忆文件。
        "repair-handoff-names": lambda: docs_function("repair_handoff_names")(path_project, write=namespace_args.write),  # 修复交接命名。
        "development": lambda: docs_function("write_development")(  # 阶段化开发记录写入动作。
            path_project,  # 开发记录所属项目。
            namespace_args.stage,  # 当前开发阶段。
            namespace_args.input,  # 可选记录输入文件。
        ),  # 写入开发记录。
        "git-changelog": lambda: docs_function("write_git_changelog")(path_project, namespace_args.input),  # 写入 Git 变更记录。
        "sync-root-agents": lambda: docs_function("sync_root_agents")(  # 根规则同步动作。
            path_project,  # 当前项目根目录。
            write=namespace_args.write,  # 是否落盘同步结果。
            installed_skill_dir_override=namespace_args.installed_skill_dir,  # 可选安装技能覆盖。
            mark_verified=namespace_args.mark_verified,  # 是否登记验证时间。
        ),
        "sync-global-codex-agents": lambda: docs_function("sync_global_codex_agents")(  # 全局基线同步动作。
            path_project,  # 治理规则来源项目。
            write=namespace_args.write,  # 是否修改全局规则文件。
            codex_home=namespace_args.codex_home,  # 可选 Codex 主目录。
        ),
        "release-gate": lambda: docs_function("release_gate")(  # 发布阶段检查动作。
            path_project,  # 发布准备记录所属仓库。
            namespace_args.version,  # 目标发布版本。
            namespace_args.skill_dir,  # 待发布技能目录。
            namespace_args.phase,  # 发布前或发布后阶段。
            namespace_args.install_intent,  # 发布后的安装意图。
        ),
        "release-prepare": lambda: docs_function("release_prepare")(  # 发布前准备动作。
            path_project,  # 发布归属项目。
            namespace_args.version,  # 待准备版本。
            namespace_args.skill_dir,  # 技能源码目录。
        ),  # 准备发布分支与记录。
        "package-release": lambda: docs_function("package_release")(  # 版本化发布包生成动作。
            path_project,  # 发布包所属项目。
            namespace_args.version,  # 打包版本号。
            namespace_args.skill_dir,  # 发布内容来源目录。
        ),  # 生成版本发布包。
        "branch-gate": lambda: branch_gate(path_project),  # 检查当前分支合同。
        "work-folder-gate": lambda: docs_function("work_folder_gate")(  # 工作目录边界检查动作。
            path_project,  # 工作文件夹根目录。
            namespace_args.skill_dir,  # 被检查技能目录。
            namespace_args.mode,  # 开发或发布模式。
        ),  # 检查工作目录边界。
        "verify": lambda: verify_docs(path_project),  # 验证文档治理结构。
    }

    # argparse 已保证命令属于已注册集合。
    function_handler = dict_command_handlers[namespace_args.command]  # 当前子命令处理函数。

    # 统一返回结构化载荷供 JSON 出口处理。
    return function_handler()

# 退出码策略按子命令读取各自的阻断字段。
def manage_docs_command_failed(namespace_args: argparse.Namespace, dict_result: dict[str, object]) -> bool:
    """判断子命令结果是否需要非零退出码。

    参数：namespace_args 为命令参数；dict_result 为治理结果。
    返回：结果满足该子命令失败条件时为真。
    """

    # 多数写入和验证命令以 errors 非空表示失败。
    tuple_error_commands = (
        "scaffold",  # 文档脚手架命令。
        "handoff",  # 交接写入命令。
        "start-session",  # 会话启动命令。
        "resume-repair",  # 会话恢复修复命令。
        "memory-init",  # 记忆初始化命令。
        "memory-bootstrap-sessions",  # 历史会话补录命令。
        "memory-write",  # 记忆写入命令。
        "memory-compress",  # 记忆压缩命令。
        "memory-read",  # 记忆查询命令。
        "memory-verify",  # 记忆验证命令。
        "sync-root-agents",  # 根规则同步命令。
        "sync-global-codex-agents",  # 全局规则同步命令。
        "release-gate",  # 发布门禁命令。
        "release-prepare",  # 发布准备命令。
        "package-release",  # 发布打包命令。
        "verify",  # 文档验证命令。
    )

    # 通用错误型命令共享相同退出规则。
    if namespace_args.command in tuple_error_commands:

        # 不区分错误正文结构，只检查集合是否非空。
        return bool(dict_result.get("errors"))

    # 恢复检查使用 blocking 字段表达中断状态。
    if namespace_args.command == "resume-check":

        # 阻断状态要求调用方先执行恢复动作。
        return bool(dict_result.get("blocking"))

    # 记忆门禁还可能要求用户显式授权初始化。
    if namespace_args.command == "memory-gate":

        # 缺失文件或待授权状态都必须阻断。
        return bool(dict_result.get("errors") or dict_result.get("requires_user_authorization"))

    # 写入式命名修复必须确认修复后不再阻断。
    if namespace_args.command == "repair-handoff-names":

        # 只读审查允许报告 blocking，写入后则不允许残留。
        dict_handoff_naming = dict_result.get("handoff_naming", {})  # 交接命名检查结果。

        # 类型异常按空映射处理，避免 CLI 自身崩溃。
        bool_still_blocking = isinstance(dict_handoff_naming, dict) and bool(dict_handoff_naming.get("blocking"))  # 修复后阻断状态。

        # 实现错误始终失败，残留阻断仅在写入模式失败。
        return bool(dict_result.get("errors") or (namespace_args.write and bool_still_blocking))

    # 分支门禁必须显式批准。
    if namespace_args.command == "branch-gate":

        # 缺失 approved 与明确拒绝具有相同语义。
        return not bool(dict_result.get("approved"))

    # 工作目录门禁必须返回 ok=true。
    if namespace_args.command == "work-folder-gate":

        # 未通过时向 shell 返回非零状态。
        return not bool(dict_result.get("ok"))

    # 记录型和只读型命令沿用零退出码行为。
    return False

# 每个子命令都接受同一形式的可选项目根参数。
def add_project_parser(object_subparsers_commands: Any, str_command: str) -> argparse.ArgumentParser:
    """注册带项目参数的子命令解析器。

    参数：object_subparsers_commands 为 argparse 子解析器集合；str_command 为命令名。
    返回：可继续添加命令专用选项的解析器。
    """

    # 子命令名称同时作为 CLI 分派键。
    argument_parser_command: argparse.ArgumentParser = object_subparsers_commands.add_parser(str_command)  # 当前子命令解析器。

    # 缺省项目根保持历史当前目录行为。
    argument_parser_command.add_argument("project", nargs="?", default=".")

    # 调用方继续注册该命令的专用选项。
    return argument_parser_command

# 解析器构建集中声明全部稳定 CLI 参数。
def build_argument_parser() -> argparse.ArgumentParser:
    """构建 manage_docs 命令行解析器。

    参数：无。
    返回：已注册全部治理子命令和选项的解析器。
    """

    # 顶层解析器只负责统一帮助摘要。
    argument_parser_argument_parser: argparse.ArgumentParser = argparse.ArgumentParser(  # manage_docs 顶层解析器。
        description="Manage AGENTS.md docs governance artifacts."  # CLI 帮助摘要。
    )

    # command 是后续分派表的必填键。
    object_subparsers_commands = argument_parser_argument_parser.add_subparsers(  # 治理子命令集合。
        dest="command",  # 分派表使用的命令字段。
        required=True,  # 调用时必须选择子命令。
    )

    # 无专用选项的命令只注册项目参数。
    tuple_simple_commands = (
        "scaffold",  # 初始化治理文档。
        "preflight",  # 检查文档前置条件。
        "memory-gate",  # 判断记忆状态能否继续工作。
        "memory-bootstrap-sessions",  # 将历史会话写入记忆索引。
        "memory-compress",  # 重建长期记忆检索摘要。
        "memory-verify",  # 验证记忆存储。
        "branch-gate",  # 检查当前分支。
        "verify",  # 验证文档结构。
    )

    # 简单命令逐一登记，保持帮助输出顺序。
    for str_command in tuple_simple_commands:

        # 注册返回值无需继续配置。
        add_project_parser(object_subparsers_commands, str_command)

    # 可选输入文件用于交接、会话启动和恢复修复。
    for str_command in ("handoff", "start-session", "resume-repair"):

        # 当前命令共享可选 --input 合同。
        argument_parser_command = add_project_parser(object_subparsers_commands, str_command)  # 输入文件命令解析器。

        # 空输入由对应实现生成默认载荷或报告错误。
        argument_parser_command.add_argument("--input", default=None)

    # 恢复检查可读取指定会话日志。
    argument_parser_resume_check = add_project_parser(object_subparsers_commands, "resume-check")  # 恢复检查解析器。

    # 对话日志覆盖用于恢复证据诊断。
    argument_parser_resume_check.add_argument("--conversation-log", default=None)

    # 记忆初始化必须由显式标志确认创建。
    argument_parser_memory_init = add_project_parser(object_subparsers_commands, "memory-init")  # 记忆初始化解析器。

    # 标志值传给记忆授权门禁。
    argument_parser_memory_init.add_argument("--confirm-create", action="store_true")

    # 记忆写入必须提供结构化输入文件。
    argument_parser_memory_write = add_project_parser(object_subparsers_commands, "memory-write")  # 记忆写入解析器。

    # 写入实现拒绝缺失输入。
    argument_parser_memory_write.add_argument("--input", required=True)

    # 记忆查询需要查询词和可选结果上限。
    argument_parser_memory_read = add_project_parser(object_subparsers_commands, "memory-read")  # 记忆查询解析器。

    # 查询词决定摘要检索主题。
    argument_parser_memory_read.add_argument("--query", required=True)

    # 缺省返回五条最相关记忆。
    argument_parser_memory_read.add_argument("--limit", type=int, default=5)

    # 交接命名修复只有显式 write 才落盘。
    argument_parser_repair = add_project_parser(object_subparsers_commands, "repair-handoff-names")  # 命名修复解析器。

    # 默认模式仅报告拟执行动作。
    argument_parser_repair.add_argument("--write", action="store_true")

    # 开发记录需要阶段并可选输入文件。
    argument_parser_development = add_project_parser(object_subparsers_commands, "development")  # 开发记录解析器。

    # 阶段名称进入开发历史标题。
    argument_parser_development.add_argument("--stage", required=True)

    # 输入文件提供开发记录正文。
    argument_parser_development.add_argument("--input", default=None)

    # Git 变更记录接受可选结构化输入。
    argument_parser_changelog = add_project_parser(object_subparsers_commands, "git-changelog")  # Git 记录解析器。

    # 缺省输入由实现根据仓库事实生成。
    argument_parser_changelog.add_argument("--input", default=None)

    # 根 AGENTS 同步支持写入、安装目录覆盖和验证标记。
    argument_parser_sync_root = add_project_parser(object_subparsers_commands, "sync-root-agents")  # 根规则同步解析器。

    # 无 write 时只返回同步差异。
    argument_parser_sync_root.add_argument("--write", action="store_true")

    # 安装目录覆盖用于源码和安装副本对照。
    argument_parser_sync_root.add_argument("--installed-skill-dir", default=None)

    # 验证标记只在调用方明确要求时更新。
    argument_parser_sync_root.add_argument("--mark-verified", action="store_true")

    # 全局规则同步接受写入标志和 Codex 主目录覆盖。
    argument_parser_sync_global = add_project_parser(object_subparsers_commands, "sync-global-codex-agents")  # 全局同步解析器。

    # 默认只审查全局规则差异。
    argument_parser_sync_global.add_argument("--write", action="store_true")

    # 自定义主目录支持隔离测试和多用户环境。
    argument_parser_sync_global.add_argument("--codex-home", default=None)

    # 发布门禁需要版本、技能目录、阶段和安装意图。
    argument_parser_release_gate = add_project_parser(object_subparsers_commands, "release-gate")  # 发布门禁解析器。

    # 目标版本用于校验发布事实一致性。
    argument_parser_release_gate.add_argument("--version", required=True)

    # 技能目录限定发布源范围。
    argument_parser_release_gate.add_argument("--skill-dir", required=True)

    # 门禁阶段区分打包前和打包后证据。
    argument_parser_release_gate.add_argument("--phase", choices=["pre", "post"], default="pre")

    # 安装意图控制发布后续动作判定。
    argument_parser_release_gate.add_argument(
        "--install-intent",  # 安装意图参数名。
        choices=["unspecified", "requested", "skipped"],  # 支持的安装状态。
        default="unspecified",  # 未声明时的兼容值。
    )

    # 发布准备和打包共享版本与技能目录参数。
    for str_command in ("release-prepare", "package-release"):

        # 两个发布动作拥有相同参数形态。
        argument_parser_command = add_project_parser(object_subparsers_commands, str_command)  # 发布动作解析器。

        # 版本必须与控制画像和发布目录一致。
        argument_parser_command.add_argument("--version", required=True)

        # 技能目录是发布内容来源。
        argument_parser_command.add_argument("--skill-dir", required=True)

    # 工作目录门禁检查技能位置和执行模式。
    argument_parser_work_folder = add_project_parser(object_subparsers_commands, "work-folder-gate")  # 工作目录门禁解析器。

    # 技能目录用于验证开发或发布工作根。
    argument_parser_work_folder.add_argument("--skill-dir", required=True)

    # 开发模式和发布模式采用不同路径约束。
    argument_parser_work_folder.add_argument("--mode", choices=["development", "release"], default="development")

    # 完整解析器供 main 和测试复用。
    return argument_parser_argument_parser

# 主入口统一解析、执行、输出和退出码处理。
def main() -> None:
    """运行 manage_docs 命令行入口。

    参数：无；参数来自当前进程命令行。
    返回：无；命令结果通过 JSON 标准输出返回。
    异常：子命令门禁失败时抛出 SystemExit(1)。
    """

    # 公共模块提供项目路径解析和机器可读 JSON 输出。
    module_agents_common_context = load_task_module("agents_common")  # AGENTS 公共治理上下文。

    # 解析器包含全部稳定子命令合同。
    argument_parser_argument_parser = build_argument_parser()  # manage_docs 命令行解析器。

    # Namespace 保存调用者选择的命令及参数。
    namespace_args: argparse.Namespace = argument_parser_argument_parser.parse_args()  # 当前命令参数。

    # 项目路径解析拒绝不存在或非目录目标。
    path_project: Path = module_agents_common_context.resolve_project(namespace_args.project)  # 已验证项目根。

    # 分派结果保持各实现模块的原始 JSON 结构。
    dict_command_result = dispatch_manage_docs_command(path_project, namespace_args)  # 子命令执行结果。

    # 所有子命令共用机器可读标准输出出口。
    module_agents_common_context.emit_json(dict_command_result)

    # 子命令失败谓词决定 shell 退出状态。
    if manage_docs_command_failed(namespace_args, dict_command_result):

        # 非零状态通知自动化调用方停止后续治理。
        raise SystemExit(1)

# 直接执行脚本时进入 CLI，模块导入保持无副作用。
if __name__ == "__main__":

    # main 负责完整命令生命周期。
    main()
