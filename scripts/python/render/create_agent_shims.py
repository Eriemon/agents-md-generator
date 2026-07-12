"""为项目中的 AGENTS.md 创建 CLAUDE.md 与 GEMINI.md 兼容入口。"""

# 延迟注解解析，保持直接脚本执行与类型标注兼容。
from __future__ import annotations

# 标准库负责命令行解析、模块加载、符号链接、路径和进程环境访问。
import argparse
import importlib
import os
from pathlib import Path
import sys
from typing import Any

# 受管前缀区分本工具生成的 shim 与用户手写文件。
MANAGED_PREFIX = "<!-- Managed by agents-md-generator:"  # 兼容文件所有权标记。

# 公共模块在 main 执行期加载，导入本模块不会修改 sys.path。
def load_common_module() -> Any:
    """加载 agents_common 公共模块。

    参数：无。
    返回：提供跳过目录、项目解析和 JSON 输出的模块对象。
    """

    # render 的父目录包含 common 等兄弟任务模块目录。
    path_python_root = Path(__file__).resolve().parents[1]  # Python 任务模块共同根目录。

    # 逐个登记目录，支持从任意工作目录直接运行脚本。
    for path_task_dir in path_python_root.iterdir():

        # 普通文件不能作为顶层模块搜索位置。
        if not path_task_dir.is_dir():

            # 跳过任务根目录中的非目录成员。
            continue

        # Python 导入器使用字符串形式保存搜索目录。
        str_task_dir = str(path_task_dir)  # 当前兄弟任务目录绝对路径。

        # 已存在的搜索位置保持原有优先级。
        if str_task_dir in sys.path:

            # 继续检查剩余任务目录。
            continue

        # 源码任务目录优先于环境中可能存在的同名模块。
        sys.path.insert(0, str_task_dir)

    # 路径就绪后加载公共治理能力。
    return importlib.import_module("agents_common")

# 所有权判断只认可符号链接或带受管前缀的普通文件。
def is_managed(path_candidate: Path) -> bool:
    """判断候选兼容文件是否由本工具管理。

    参数：path_candidate 为 CLAUDE.md 或 GEMINI.md 候选路径。
    返回：符号链接或带受管标记的文件返回 True。
    """

    # 任意符号链接都可由本工具安全重建为 AGENTS.md 入口。
    if path_candidate.is_symlink():

        # 链接目标即使暂时失效也仍属于可替换 shim。
        return True

    # 缺失路径和目录都不属于受管普通文件。
    if not path_candidate.exists() or not path_candidate.is_file():

        # 非普通文件必须由创建流程按缺失候选处理。
        return False

    # 文件读取失败时按用户内容处理，避免误删不可检查对象。
    try:

        # 只有文件首部的生成器标记能证明所有权。
        str_file_text = path_candidate.read_text(encoding="utf-8", errors="ignore")  # 候选文件文本。

        # 前缀匹配避免把正文中偶然出现的标记当作所有权证明。
        return str_file_text.startswith(MANAGED_PREFIX)

    # 权限、锁定或瞬时文件系统错误均采用保守保留策略。
    except OSError:

        # 无法读取时不允许后续流程删除候选文件。
        return False

# 创建流程优先使用链接，平台不支持时写入受管文本 shim。
def create_link_or_shim(
    path_target: Path,
    list_warnings: list[str],
    list_actions: list[str],
) -> None:
    """创建或刷新单个代理兼容入口。

    参数：path_target 为兼容文件路径；list_warnings 收集保留或降级信息；list_actions 收集成功链接动作。
    返回：无；文件系统结果通过两个列表反馈。
    """

    # 用户手写的同名文件不属于本工具所有，必须原样保留。
    if path_target.exists() and not is_managed(path_target):

        # 警告进入机器 JSON，不直接污染标准输出协议。
        list_warnings.append(f"Preserved existing non-managed {path_target.name}")

        # 保留完成后不再尝试链接或覆盖。
        return

    # 旧受管文件或链接先移除，确保目标类型可以切换。
    if path_target.exists() or path_target.is_symlink():

        # 所有权已确认后才允许删除现有入口。
        path_target.unlink()

    # Windows 权限或文件系统能力可能拒绝创建符号链接。
    try:

        # 相对目标让项目目录移动后链接仍然有效。
        os.symlink("AGENTS.md", path_target)

        # 操作摘要记录实际创建的入口名称。
        list_actions.append(f"Created symlink {path_target.name} -> AGENTS.md")

    # 链接不可用时使用显式受管文本，后续运行仍能识别所有权。
    except OSError:

        # 文本 shim 使用 Codex 兼容引用语法指向同目录 AGENTS.md。
        path_target.write_text(
            f"{MANAGED_PREFIX} shim -->\n@AGENTS.md\n",
            encoding="utf-8",
        )

        # 降级原因进入 warnings，调用者可区分链接与文本入口。
        list_warnings.append(f"Symlink unavailable; wrote managed shim {path_target.name}")

# 跳过判定复用公共排除目录，同时允许显式覆盖扫描范围。
def should_skip(
    path_candidate: Path,
    path_project: Path,
    set_skip_dirs: set[str],
    bool_include_skipped: bool = False,
) -> bool:
    """判断 AGENTS.md 候选是否位于默认排除目录。

    参数：path_candidate 为候选文件；path_project 为扫描根；set_skip_dirs 为排除名集合；bool_include_skipped 控制是否忽略排除规则。
    返回：默认应跳过候选时为 True。
    """

    # 显式 include-skipped 要求扫描所有可发现候选。
    if bool_include_skipped:

        # 调用者已经接受 ref、vendor 和构建目录的额外范围。
        return False

    # 正常候选应以项目根为基准检查每一级目录名。
    try:

        # 相对路径排除项目根之前的宿主目录名称。
        tuple_path_parts = path_candidate.relative_to(path_project).parts  # 项目内候选路径片段。

    # 防御性支持不在扫描根内的路径输入。
    except ValueError:

        # 越界候选使用完整路径片段执行同一排除规则。
        tuple_path_parts = path_candidate.parts  # 无法相对化的候选路径片段。

    # 任一片段命中公共排除集合即跳过该 AGENTS.md。
    return bool(set(tuple_path_parts) & set_skip_dirs)

# CLI 入口负责项目扫描、兼容文件创建和机器 JSON 汇总。
def main() -> None:
    """执行代理兼容入口创建命令。

    参数：无；命令行可指定项目根和 include-skipped 开关。
    返回：无；结果通过标准输出 JSON 协议返回。
    """

    # 公共模块提供项目校验、跳过目录和 JSON 序列化能力。
    module_agents_common_context = load_common_module()  # AGENTS 公共治理上下文。

    # 解析器描述本命令只处理 AGENTS.md 的两个兼容入口。
    argument_parser = argparse.ArgumentParser(  # shim 创建命令解析器。
        description="Create CLAUDE.md and GEMINI.md shims for AGENTS.md files.",  # CLI 帮助摘要。
    )

    # 项目根缺省为当前工作目录。
    argument_parser.add_argument("project", nargs="?", default=".")

    # 显式开关允许调用者把公共跳过目录纳入扫描。
    argument_parser.add_argument(
        "--include-skipped",  # 扩展候选目录范围的命令行开关。
        action="store_true",  # 参数出现时记录布尔真值。
        help="Also scan skipped directories such as ref, vendor, and build outputs.",  # 开关帮助文本。
    )

    # Namespace 保存项目位置和扫描范围开关。
    namespace_args: argparse.Namespace = argument_parser.parse_args()  # 当前命令行解析结果。

    # 公共路径校验拒绝不存在或非目录的扫描根。
    path_project: Path = module_agents_common_context.resolve_project(namespace_args.project)  # 已验证项目根目录。

    # 成功动作与降级警告分开汇总，保持机器合同稳定。
    list_actions: list[str] = []  # 已创建符号链接的动作摘要。

    # 警告包含用户文件保留和符号链接降级情况。
    list_warnings: list[str] = []  # 未覆盖文件或文本 shim 摘要。

    # 排序确保跨文件系统运行的动作顺序稳定。
    for path_agents_file in sorted(path_project.rglob("AGENTS.md")):

        # 默认排除依赖、参考材料和构建产物目录。
        if should_skip(
            path_agents_file,
            path_project,
            module_agents_common_context.SKIP_DIRS,
            namespace_args.include_skipped,
        ):

            # 跳过目录不产生文件系统动作或警告。
            continue

        # 每个 AGENTS.md 对应两种外部代理兼容入口。
        for str_shim_name in ("CLAUDE.md", "GEMINI.md"):

            # 入口与 AGENTS.md 保持同目录，内部引用使用相对目标。
            path_shim_target = path_agents_file.parent / str_shim_name  # 当前待创建的兼容文件。

            # 所有权检查和平台降级由单文件函数统一处理。
            create_link_or_shim(path_shim_target, list_warnings, list_actions)

    # 标准输出保持单个 JSON 对象，供其它治理命令组合使用。
    module_agents_common_context.emit_json(
        {
            "actions": list_actions,  # 已完成链接动作列表。
            "warnings": list_warnings,  # 保留和降级警告列表。
        }
    )

# 直接执行脚本时启动 CLI，模块导入保持无文件系统副作用。
if __name__ == "__main__":

    # main 完成扫描、写入与 JSON 输出。
    main()
