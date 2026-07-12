"""提供目录结构扫描、审查、修复、归档与验证的统一命令行入口。"""

# 延迟注解解析，避免运行期解析仅供类型检查使用的联合类型。
from __future__ import annotations

# 标准库负责命令行解析、JSON 编码和路径处理。
import argparse
import importlib
import json
from pathlib import Path
import sys
from typing import Any
from typing import Callable

# 三个公开路径常量保持 docs 子系统既有导入合同。
CURRENT_STRUCTURE = "docs/dir_manager/current_structure.json"  # 当前目录结构快照相对路径。

# 文档入口常量供 handoff 与目录治理验证器定位说明文件。
DIR_MANAGER_MD = "docs/dir_manager/DIR_MANAGER.md"  # 目录治理说明文档相对路径。

# 计划快照常量供结构门禁比较当前布局与批准布局。
PLANNED_STRUCTURE = "docs/dir_manager/planned_structure.json"  # 已批准目录结构计划相对路径。

# 直接执行时按需登记兄弟任务目录，避免导入入口即修改进程环境。
def load_task_module(str_module_name: str) -> Any:
    """从 scripts/python 下的任务目录加载指定模块。

    参数：str_module_name 为不含路径和扩展名的模块名称。
    返回：已完成导入的模块对象。
    """

    # dirs 的父目录包含 common、docs、release 等任务模块目录。
    path_python_root = Path(__file__).resolve().parents[1]  # Python 任务模块共同根目录。

    # 仅在命令实际调用跨任务能力时补充模块搜索位置。
    for path_task_dir in path_python_root.iterdir():

        # 普通文件不能作为顶层模块的搜索目录。
        if not path_task_dir.is_dir():

            # 跳过 VERSION 等非目录成员。
            continue

        # sys.path 以字符串形式保存每个模块搜索位置。
        str_task_dir = str(path_task_dir)  # 当前候选任务目录的绝对路径。

        # 已登记目录保持原有搜索优先级，避免重复插入。
        if str_task_dir in sys.path:

            # 继续确认其余兄弟任务目录是否可用。
            continue

        # 新登记目录优先于环境中的同名第三方模块。
        sys.path.insert(0, str_task_dir)

    # 搜索路径就绪后按稳定模块名加载治理实现。
    return importlib.import_module(str_module_name)

# 兼容门面保留 docs 子系统使用的初始化入口。
def init_dir_manager(path_project: Path) -> dict[str, object]:
    """初始化项目的目录治理文档。

    参数：path_project 为项目根目录。
    返回：初始化动作的结构化状态。
    """

    # 状态模块仍是初始化行为的唯一实现来源。
    module_dirs_state_context = load_task_module("manage_dirs_state")  # 目录状态实现上下文。

    # 包装器仅维持历史导入路径，不改变返回载荷。
    return module_dirs_state_context.init_dir_manager(path_project)

# 兼容门面保留 docs 子系统使用的验证入口。
def verify_dir_manager(path_project: Path) -> dict[str, object]:
    """验证项目的目录治理文件。

    参数：path_project 为项目根目录。
    返回：目录治理完整性检查结果。
    """

    # 状态模块集中执行所有文件和字段检查。
    module_dirs_state_context = load_task_module("manage_dirs_state")  # 目录状态验证上下文。

    # 调用方继续接收原实现的完整 JSON 结果。
    return module_dirs_state_context.verify_dir_manager(path_project)

# 兼容门面保留 render 子系统使用的结构门禁入口。
def structure_gate(path_project: Path) -> dict[str, object]:
    """检查当前项目结构是否符合已批准计划。

    参数：path_project 为项目根目录。
    返回：包含 approved 与原因列表的门禁结果。
    """

    # 审查模块拥有结构合规判定的唯一实现。
    module_dirs_review_context = load_task_module("manage_dirs_review")  # 目录结构审查上下文。

    # 包装器保持旧模块导入路径和返回合同。
    return module_dirs_review_context.structure_gate(path_project)

# 兼容门面保留 render 子系统使用的自动修复入口。
def apply_structure_fix(path_project: Path) -> dict[str, object]:
    """应用结构门禁给出的普通修复方案。

    参数：path_project 为项目根目录。
    返回：已执行动作和错误列表组成的修复结果。
    """

    # 审查模块负责验证并实施允许的结构变更。
    module_dirs_review_context = load_task_module("manage_dirs_review")  # 普通结构修复上下文。

    # 调用方继续接收审查模块的原始结果。
    return module_dirs_review_context.apply_structure_fix(path_project)

# 其余子命令通过内部包装器保持分派表简洁。
def review_change(path_project: Path, str_input: str, *, dry_run: bool) -> dict[str, object]:
    """审查输入文件声明的目录变更。

    参数：path_project 为项目根目录；str_input 为变更 JSON；dry_run 控制是否保留审查记录。
    返回：包含批准状态、风险和建议动作的审查结果。
    """

    # 审查模块解析变更并应用目录合同。
    module_dirs_review_context = load_task_module("manage_dirs_review")  # 目录变更审查上下文。

    # 关键字参数保持既有 dry-run 调用语义。
    return module_dirs_review_context.review_change(path_project, str_input, dry_run=dry_run)

# 接管修复只在显式子命令中加载迁移实现。
def takeover_fix(path_project: Path) -> dict[str, object]:
    """迁移需要治理接管的旧工作区布局。

    参数：path_project 为项目根目录。
    返回：接管迁移动作和错误列表。
    """

    # 审查模块负责识别并迁移允许接管的目录形态。
    module_dirs_review_context = load_task_module("manage_dirs_review")  # 接管结构修复上下文。

    # 包装器不改变迁移顺序或错误语义。
    return module_dirs_review_context.takeover_fix(path_project)

# 状态扫描通过内部门面延迟加载目录发现逻辑。
def scan_structure(path_project: Path) -> dict[str, object]:
    """读取项目当前目录结构。

    参数：path_project 为项目根目录。
    返回：可写入 current_structure.json 的结构快照。
    """

    # 状态模块集中维护扫描忽略规则和结构序列化格式。
    module_dirs_state_context = load_task_module("manage_dirs_state")  # 目录扫描实现上下文。

    # 返回值保持状态模块的稳定 JSON schema。
    return module_dirs_state_context.scan_structure(path_project)

# 归档包装器保留原因和审查文件两个关键字合同。
def archive_dir_manager(
    path_project: Path,
    *,
    reason: str,
    review_file: str,
) -> dict[str, object]:
    """归档当前目录治理文档。

    参数：path_project 为项目根目录；reason 为归档原因；review_file 为关联审查记录。
    返回：归档目录和已保存文件列表。
    """

    # 状态模块负责时间戳目录和治理文件复制边界。
    module_dirs_state_context = load_task_module("manage_dirs_state")  # 目录治理归档上下文。

    # 关键字转发保持历史调用方兼容。
    return module_dirs_state_context.archive_dir_manager(
        path_project,
        reason=reason,
        review_file=review_file,
    )

# scan 子命令按需加载状态模块，避免只读导入触发路径环境变更。
def run_scan_command(path_project: Path, namespace_args: argparse.Namespace) -> dict[str, object]:
    """扫描项目目录，并按命令参数决定是否刷新结构快照。

    参数：path_project 为待扫描项目根目录；namespace_args 提供 write 开关。
    返回：当前目录结构的机器可读快照。
    """

    # 扫描结果既用于标准输出，也可作为 current_structure.json 的内容。
    dict_structure = scan_structure(path_project)  # 当前目录结构快照。

    # 未请求落盘时保持 scan 为纯只读命令。
    if not namespace_args.write:

        # 调用方直接接收本次扫描结果。
        return dict_structure

    # 写模式先确保受管文档目录存在。
    path_structure_dir = (path_project / CURRENT_STRUCTURE).parent  # 结构快照父目录。

    # 目录创建仅发生在显式 --write 分支。
    path_structure_dir.mkdir(parents=True, exist_ok=True)

    # 当前结构文件使用稳定排序，便于版本审查和重复运行比较。
    path_structure_file = path_project / CURRENT_STRUCTURE  # 当前结构快照文件。

    # UTF-8 JSON 保留跨平台可读的目录事实。
    path_structure_file.write_text(
        json.dumps(dict_structure, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # 写入完成后仍返回与只读模式相同的扫描载荷。
    return dict_structure

# 命令分派在运行期加载实现模块，避免入口导入产生环境副作用。
def dispatch_manage_dirs_command(
    path_project: Path,
    namespace_args: argparse.Namespace,
) -> dict[str, object]:
    """执行已解析的目录治理子命令。

    参数：path_project 为项目根目录；namespace_args 为 argparse 解析结果。
    返回：所选子命令产生的统一 JSON 对象。
    """

    # 子命令表保持 argparse 名称与实际治理动作一一对应。
    dict_command_handlers: dict[str, Callable[[], dict[str, object]]] = {  # 无参数命令执行器映射。
        "scan": lambda: run_scan_command(path_project, namespace_args),  # 扫描或写入当前结构快照。
        "init": lambda: init_dir_manager(path_project),  # 初始化目录治理文档。
        "review": lambda: review_change(  # 审查声明的目录变更。
            path_project,  # 受目录合同约束的项目根目录。
            namespace_args.input,  # 描述目录操作的 JSON 输入文件。
            dry_run=namespace_args.dry_run,  # 控制审查是否保留落盘证据。
        ),
        "structure-gate": lambda: structure_gate(path_project),  # 校验当前目录布局。
        "apply-structure-fix": lambda: apply_structure_fix(path_project),  # 应用普通结构修复。
        "takeover-fix": lambda: takeover_fix(path_project),  # 应用接管场景迁移。
        "archive": lambda: archive_dir_manager(  # 归档当前目录治理历史。
            path_project,  # 提供待归档治理文档的项目根目录。
            reason=namespace_args.reason,  # 记录本次归档的人工原因。
            review_file=namespace_args.review_file,  # 关联触发归档的审查记录。
        ),
        "verify": lambda: verify_dir_manager(path_project),  # 验证目录治理文件一致性。
    }  # 子命令执行器映射结束。

    # required=True 已保证命令存在于映射中。
    return dict_command_handlers[namespace_args.command]()

# 不同子命令使用各自的成功字段，不能只依赖 JSON 是否为空。
def manage_dirs_command_failed(str_command: str, dict_result: dict[str, object]) -> bool:
    """根据子命令合同判断 CLI 是否需要返回非零退出码。

    参数：str_command 为子命令名称；dict_result 为该命令的 JSON 结果。
    返回：结果应阻断调用方时为 True，否则为 False。
    """

    # 每个谓词只读取对应子命令承诺存在的状态字段。
    dict_failure_checks: dict[str, Callable[[dict[str, object]], bool]] = {  # 子命令失败判定映射。
        "review": lambda dict_payload: not bool(dict_payload["approved"]),  # 未批准的变更必须阻断。
        "structure-gate": lambda dict_payload: not bool(dict_payload["approved"]),  # 非合规结构必须阻断。
        "apply-structure-fix": lambda dict_payload: bool(dict_payload["errors"]),  # 修复错误阻断退出。
        "takeover-fix": lambda dict_payload: bool(dict_payload["errors"]),  # 接管错误阻断退出。
        "verify": lambda dict_payload: bool(dict_payload["errors"]),  # 验证错误阻断退出。
    }

    # scan、init 和 archive 沿用成功退出，除非执行过程直接抛错。
    func_failure_check = dict_failure_checks.get(str_command)  # 当前命令的可选失败谓词。

    # 没有专用失败字段的命令不额外改变退出码。
    if func_failure_check is None:

        # 正常完成即向 shell 返回成功。
        return False

    # 登记命令按其稳定 JSON 字段计算失败状态。
    return func_failure_check(dict_result)

# CLI 构造集中声明子命令参数，执行层只消费 Namespace 合同。
def build_argument_parser() -> argparse.ArgumentParser:
    """构造目录治理命令行解析器。

    参数：无。
    返回：已经注册全部子命令和参数的 ArgumentParser。
    """

    # 顶层说明概括该入口的审查和验证职责。
    parser = argparse.ArgumentParser(  # 目录治理顶层参数解析器。
        description="Review and verify strict project directory management gates.",  # CLI 帮助摘要。
    )

    # 所有操作必须显式选择一个子命令。
    sub_parsers_action_commands: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(  # 目录治理子命令集合。
        dest="command",  # Namespace 中保存所选子命令的字段名。
        required=True,  # 拒绝未指定目录治理动作的调用。
    )

    # scan 支持只读扫描以及显式写入当前结构快照。
    argument_parser_scan: argparse.ArgumentParser = sub_parsers_action_commands.add_parser("scan")  # 结构扫描参数解析器。

    # 项目根目录缺省为当前工作目录。
    argument_parser_scan.add_argument("project", nargs="?", default=".")

    # --write 是唯一允许 scan 落盘的开关。
    argument_parser_scan.add_argument("--write", action="store_true")

    # init 创建受管目录文档的初始状态。
    argument_parser_init: argparse.ArgumentParser = sub_parsers_action_commands.add_parser("init")  # 目录治理初始化解析器。

    # 初始化目标同样允许省略当前目录参数。
    argument_parser_init.add_argument("project", nargs="?", default=".")

    # review 消费变更 JSON，并可选择不保留审查记录。
    argument_parser_review: argparse.ArgumentParser = sub_parsers_action_commands.add_parser("review")  # 目录变更审查解析器。

    # 审查目标限定为一个项目根目录。
    argument_parser_review.add_argument("project", nargs="?", default=".")

    # 输入文件描述 create、move、delete 或 rename 操作。
    argument_parser_review.add_argument("--input", required=True)

    # dry-run 仅返回决策，不写入正式审查历史。
    argument_parser_review.add_argument("--dry-run", action="store_true")

    # 无额外参数的命令共享统一 project 位置参数。
    tuple_simple_commands = (  # 仅接收项目根目录的子命令名称。
        "structure-gate",  # 检查当前结构是否符合计划。
        "apply-structure-fix",  # 应用普通结构自动修复。
        "takeover-fix",  # 迁移需要治理接管的旧布局。
        "verify",  # 验证目录治理文件完整性。
    )

    # 为同形子命令登记一致的位置参数合同。
    for str_command_name in tuple_simple_commands:

        # 每个解析器仍保留独立命令帮助入口。
        argument_parser_simple: argparse.ArgumentParser = sub_parsers_action_commands.add_parser(str_command_name)  # 当前简单子命令解析器。

        # 调用者可显式指定项目，缺省时使用当前目录。
        argument_parser_simple.add_argument("project", nargs="?", default=".")

    # archive 额外记录归档原因和关联审查文件。
    argument_parser_archive: argparse.ArgumentParser = sub_parsers_action_commands.add_parser("archive")  # 目录治理归档解析器。

    # 归档操作只处理指定项目的治理文档。
    argument_parser_archive.add_argument("project", nargs="?", default=".")

    # 缺省原因保持既有强制确认目录覆盖文案。
    argument_parser_archive.add_argument("--reason", default="force-confirmed directory override")

    # 可选审查文件用于把归档与人工决策证据关联。
    argument_parser_archive.add_argument("--review-file", default="")

    # main 使用完整解析器消费命令行参数。
    return parser

# 主入口只负责解析、项目路径校验、JSON 输出和退出码转换。
def main() -> None:
    """执行目录治理 CLI。

    参数：无；命令行参数由 argparse 读取。
    返回：无；成功完成后由解释器返回零退出码。
    异常：子命令合同失败时抛出 SystemExit(1)。
    """

    # 公共模块在执行期加载，直接导入本入口不会修改模块搜索路径。
    module_agents_common_context = load_task_module("agents_common")  # 项目路径与 JSON 输出上下文。

    # 解析器在执行期构造，导入模块不会读取进程参数。
    parser: argparse.ArgumentParser = build_argument_parser()  # 已注册目录治理命令的解析器。

    # Namespace 保留所选子命令及其专用选项。
    namespace_args: argparse.Namespace = parser.parse_args()  # 当前命令行解析结果。

    # 公共路径校验拒绝不存在或非目录的项目参数。
    path_project: Path = module_agents_common_context.resolve_project(namespace_args.project)  # 已验证项目根目录。

    # 分派层返回可稳定序列化的命令结果。
    dict_command_result = dispatch_manage_dirs_command(path_project, namespace_args)  # 目录治理 JSON 结果。

    # 机器协议不添加人类日志前缀。
    module_agents_common_context.emit_json(dict_command_result)

    # 仅合同明确失败的命令返回非零退出码。
    if manage_dirs_command_failed(namespace_args.command, dict_command_result):

        # shell 调用方据此阻止后续目录变更。
        raise SystemExit(1)

# 直接执行脚本时启动 CLI，导入模块保持无副作用。
if __name__ == "__main__":

    # main 负责完整命令生命周期。
    main()
