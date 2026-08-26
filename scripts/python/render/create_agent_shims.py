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

# 无符号链接平台使用此最小文本作为可识别的受管入口。
FALLBACK_SHIM_TEXT = "AGENTS.md\n"  # 无符号链接能力时的最小原生入口。

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

    # 只有本工具创建的相对 AGENTS.md 链接才具有可替换所有权。
    if path_candidate.is_symlink():

        # 读取链接目标，确认它确实指向本目录的 AGENTS.md。
        try:

            # 相对链接目标是本工具创建链接的所有权凭据。
            return os.readlink(path_candidate) == "AGENTS.md"

        # 读取链接失败时必须保守视为非受管文件。
        except OSError:

            # 无法确认所有权时禁止删除候选路径。
            return False

    # 缺失路径和目录都不属于受管普通文件。
    if not path_candidate.exists() or not path_candidate.is_file():

        # 非普通文件必须由创建流程按缺失候选处理。
        return False

    # 文件读取失败时按用户内容处理，避免误删不可检查对象。
    try:

        # 只有文件首部的生成器标记能证明所有权。
        str_file_text = path_candidate.read_text(encoding="utf-8", errors="ignore")  # 候选文件文本。

        # 前缀匹配或精确的回退入口都能证明文件由本工具管理。
        return str_file_text.startswith(MANAGED_PREFIX) or str_file_text == FALLBACK_SHIM_TEXT

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

    参数:
        path_target: 待创建或刷新的兼容文件路径。
        list_warnings: 收集用户文件保留和链接降级信息。
        list_actions: 收集成功创建的链接动作。
    返回:
        无；文件系统结果通过两个列表反馈。
    异常:
        RuntimeError: 目标存在且不属于本工具管理时抛出。
    """

    # 用户手写的同名文件不属于本工具所有，必须 fail closed。
    if path_target.exists() and not is_managed(path_target):

        # 未托管文件不能被覆盖，避免删除用户内容。
        raise RuntimeError(
            f"> ERR: [Python] unmanaged platform shim conflict: {path_target.name}"
        )

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

        # 文本 shim 只保留目标文件名，兼容不解释特殊引用语法的平台。
        path_target.write_text(FALLBACK_SHIM_TEXT, encoding="utf-8")

        # 降级原因进入 warnings，调用者可区分链接与文本入口。
        list_warnings.append(f"Symlink unavailable; wrote managed shim {path_target.name}")

# 保存单个 shim 的原始类型和内容，供失败事务回滚。
def _snapshot_path(path_target: Path) -> tuple[str, bytes | str | None]:
    """保存单个 shim 的原始字节或链接目标。

    参数:
        path_target: 待保存快照的兼容入口路径。
    返回:
        类型标识与原始字节或链接目标组成的二元组。
    """

    # 符号链接必须保留链接目标，回滚时不能读取其指向文件。
    if path_target.is_symlink():

        # 保存相对链接目标，确保恢复后仍保持原入口形态。
        return "symlink", os.readlink(path_target)

    # 普通文件需要保留原始字节，避免编码转换损坏用户内容。
    if path_target.is_file():

        # 读取文件字节作为事务快照。
        return "file", path_target.read_bytes()

    # 目标既不是链接也不是普通文件，回滚时应保持缺失。
    return "missing", None

# 按事务快照恢复单个 shim 的原始状态。
def _restore_path(
    path_target: Path,
    tuple_snapshot: tuple[str, bytes | str | None],
) -> None:
    """把 shim 恢复到事务开始时的状态。

    参数:
        path_target: 需要恢复的兼容入口路径。
        tuple_snapshot: `_snapshot_path` 保存的类型与内容二元组。
    返回:
        无；目标路径恢复为事务开始时的状态。
    """

    # 清除本轮可能已经写入的受管入口。
    if path_target.exists() or path_target.is_symlink():

        # 目标已存在时先删除，再按快照类型重建。
        path_target.unlink()

    # 解包快照，分别处理普通文件和符号链接。
    str_kind, object_value = tuple_snapshot  # 快照类型和原始内容值。

    # 普通文件使用原始字节恢复，避免重新编码。
    if str_kind == "file" and isinstance(object_value, bytes):

        # 写回事务开始时保存的文件内容。
        path_target.write_bytes(object_value)

    # 符号链接使用原始目标恢复链接语义。
    elif str_kind == "symlink" and isinstance(object_value, str):

        # 重建原始相对链接。
        os.symlink(object_value, path_target)

# 预检所有会被 shim 事务阻断的用户文件。
def unmanaged_shim_conflicts(
    project: Path,
    set_skip_dirs: set[str],
) -> list[Path]:
    """在任何根文件写入前列出会被 shim 事务阻断的用户文件。

    参数:
        project: 需要递归扫描的项目根目录。
        set_skip_dirs: 默认跳过的目录名称集合。
    返回:
        不属于本工具管理范围、会阻断写入的兼容文件路径列表。
    """

    # 保存预检发现的用户文件冲突，调用方在写入前统一处理。
    list_conflicts: list[Path] = []  # 未托管兼容文件冲突列表。

    # 递归查找项目内的所有 AGENTS.md 根文件。
    for path_agents_file in sorted(project.rglob("AGENTS.md")):

        # 跳过公共排除目录，避免触碰依赖和构建产物。
        if should_skip(path_agents_file, project, set_skip_dirs):

            # 被排除的根文件不参与冲突预检。
            continue

        # 每个根文件都需要检查两种兼容入口名称。
        for str_shim_name in ("CLAUDE.md", "GEMINI.md"):

            # 将兼容入口名称映射到根文件所在目录。
            path_target = path_agents_file.parent / str_shim_name  # 当前根文件对应的兼容入口。

            # 只报告存在且不属于本工具的目标文件。
            if (path_target.exists() or path_target.is_symlink()) and not is_managed(path_target):

                # 记录冲突路径，调用方稍后以 fail-closed 方式返回。
                list_conflicts.append(path_target)

    # 返回稳定顺序的冲突列表，便于机器输出和测试比较。
    return list_conflicts

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

    参数:
        无；命令行可指定项目根和 include-skipped 开关。
    返回:
        无；结果通过标准输出 JSON 协议返回。
    异常:
        SystemExit: 未托管冲突存在时以非零状态结束。
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

    # 未托管冲突必须保留原文件，并以 warning 记录而不是覆盖或伪造写入成功。
    list_errors: list[str] = []  # 未托管文件冲突列表。

    # 先收集全部候选，确保后续冲突预检不会在已写入文件后才发现。
    list_targets: list[Path] = []  # 待创建兼容入口的完整路径列表。

    # 递归扫描项目根内的所有 AGENTS.md 文件。
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
        list_targets.extend(
            path_agents_file.parent / str_shim_name
            for str_shim_name in ("CLAUDE.md", "GEMINI.md")
        )

    # 冲突预检完成后，缺失或受管 shim 仍可继续处理，且不会出现后置冲突半写入。
    set_conflict_paths = {  # 预检发现的未托管冲突路径集合。
        path_target  # 当前候选的目标路径。
        for path_target in list_targets  # 遍历全部候选入口。
        if (path_target.exists() or path_target.is_symlink()) and not is_managed(path_target)  # 只保留用户文件。
    }

    # 将预检冲突转换为稳定的非阻断 warning 文本。
    list_warnings.extend(
        f"> WARNING: [Python] preserved unmanaged platform shim: {path_target.as_posix()}"  # 用户文件保留事实。
        for path_target in sorted(set_conflict_paths)  # 按路径稳定输出 warning。
    )

    # 只为可安全处理的目标保存事务前快照。
    dict_snapshots = {  # 目标路径到原始状态快照的映射。
        path_target: _snapshot_path(path_target)  # 保存当前目标的原始状态。
        for path_target in list_targets  # 遍历全部待处理目标。
        if path_target not in set_conflict_paths  # 排除未托管冲突路径。
    }

    # 链接创建事务失败时必须恢复所有已经改写的目标。
    try:

        # 按候选顺序创建或刷新兼容入口。
        for path_target in list_targets:

            # 冲突目标保持原样，不进入写入事务。
            if path_target in set_conflict_paths:

                # 预检已经记录冲突错误，继续处理其它安全目标。
                continue

            # 创建单个受管链接或文本 shim。
            create_link_or_shim(path_target, list_warnings, list_actions)

    # 任一文件系统异常都触发统一回滚和错误记录。
    except Exception as object_error:

        # 恢复本轮已经处理的每个安全目标。
        for path_target, tuple_snapshot in dict_snapshots.items():

            # 使用事务开始时保存的类型和内容恢复目标。
            _restore_path(path_target, tuple_snapshot)

        # 保留原始错误文本，供机器结果诊断。
        list_errors.append(str(object_error))

    # 标准输出保持单个 JSON 对象，供其它治理命令组合使用。
    module_agents_common_context.emit_json(
        {
            "ok": not list_errors,
            "errors": list_errors,
            "actions": list_actions,  # 已完成链接动作列表。
            "warnings": list_warnings,  # 保留和降级警告列表。
        }
    )

    # 只有真实事务异常才使命令失败，用户文件保留本身不是失败。
    if list_errors:

        # 结构化错误已经输出，CLI 以非零状态通知调用方。
        raise SystemExit(1)

# 直接执行脚本时启动 CLI，模块导入保持无文件系统副作用。
if __name__ == "__main__":

    # main 完成扫描、写入与 JSON 输出。
    main()
