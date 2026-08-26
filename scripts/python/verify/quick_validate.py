"""运行 agents-md-generator 自检与已安装 skill-creator 快速验证器。"""

# 延迟注解解析，保持直接脚本执行兼容。
from __future__ import annotations

# 标准库负责命令行、模块加载、环境、正则和路径处理。
import argparse
import importlib
import os
from pathlib import Path
import re

# SQLite、子进程和模块类型支撑可选文档门禁与运行时输出。
import sqlite3
import subprocess
import sys
from types import ModuleType
from typing import Any

# 旧 numbered shard 名称表示源码拆分迁移未完成。
STALE_NUMBERED_SHARD_RE = re.compile(  # 已退役分片名称匹配器。
    r"(?:^|[_./\\])part\d+\.py\b|eval_runtime_cases_part\d|_version_policy_part\d",  # 历史编号分片模式。
)

# 公共模块延迟加载，导入本验证器不会修改 sys.path。
def load_common_module() -> Any:
    """加载 agents_common 公共模块。

    参数：无。
    返回：提供脚本登记表和项目路径校验的模块对象。
    """

    # verify 的父目录包含 common 等兄弟任务模块目录。
    path_python_root = Path(__file__).resolve().parents[1]  # Python 任务模块共同根目录。

    # 直接执行前登记所有兄弟任务目录。
    for path_task_dir in path_python_root.iterdir():

        # 非目录成员不能参与模块搜索。
        if not path_task_dir.is_dir():

            # 跳过任务根中的普通文件。
            continue

        # sys.path 以字符串形式保存搜索位置。
        str_task_dir = str(path_task_dir)  # 当前任务模块目录绝对路径。

        # 已登记目录保持现有优先级。
        if str_task_dir in sys.path:

            # 继续检查其余兄弟目录。
            continue

        # 源码目录优先于环境中的同名模块。
        sys.path.insert(0, str_task_dir)

    # 路径就绪后加载共享治理事实。
    return importlib.import_module("agents_common")

# 源码扫描拒绝仍指向已退役编号分片的运行时入口。
def stale_numbered_shard_errors(path_skill_dir: Path) -> list[str]:
    """查找 Python 源码中的旧 numbered shard 引用。

    参数：path_skill_dir 为待验证技能目录。
    返回：每个陈旧引用对应一条相对路径诊断。
    """

    # 本门禁只检查技能包内标准 Python 运行时目录。
    path_python_root = path_skill_dir / "scripts" / "python"  # Python 运行时根目录。

    # 外部技能没有该布局时不适用本项自检。
    if not path_python_root.is_dir():

        # 空列表表示没有可检查的运行时源码。
        return []

    # 诊断按文件排序追加，确保重复运行输出稳定。
    list_errors: list[str] = []  # 陈旧分片引用诊断。

    # 所有 Python 文件都可能通过字符串或动态加载器引用旧分片。
    for path_source in sorted(path_python_root.rglob("*.py")):

        # 相对路径用于生成可移植诊断。
        str_relative_path = path_source.relative_to(path_skill_dir).as_posix()  # 技能内源码路径。

        # 容错读取允许诊断包含非标准字符的历史源码。
        str_source_text = path_source.read_text(encoding="utf-8", errors="ignore")  # Python 源码文本。

        # 仅命中明确退役命名模式时报告。
        if STALE_NUMBERED_SHARD_RE.search(str_source_text):

            # 消息保留旧测试和调用方依赖的稳定正文。
            list_errors.append(f"{str_relative_path}: stale numbered shard reference")

    # 调用方统一输出全部自检诊断。
    return list_errors

# 脚本登记表必须与版本包中的真实任务目录保持一致。
def registered_script_errors(
    path_skill_dir: Path,
    dict_script_tasks: dict[str, str],
) -> list[str]:
    """检查脚本登记表中的每个入口是否存在。

    参数：path_skill_dir 为技能目录；dict_script_tasks 映射脚本名到任务目录。
    返回：缺失入口对应的稳定诊断列表。
    """

    # 发布登记项只能解析到技能包约定的 scripts/python 分类布局。
    path_python_root = path_skill_dir / "scripts" / "python"  # 登记入口查找基准目录。

    # 不采用标准运行时布局的外部技能无需执行本项检查。
    if not path_python_root.is_dir():

        # 缺少适用目录不等同于登记入口缺失。
        return []

    # 按脚本名排序保证缺失诊断顺序稳定。
    list_errors: list[str] = []  # 登记表与文件系统不一致项。

    # 每个登记项声明脚本应位于哪个任务子目录。
    for str_script_name, str_task_name in sorted(dict_script_tasks.items()):

        # 真实文件位置由运行时根、任务名和脚本名组成。
        path_script = path_python_root / str_task_name / str_script_name  # 登记入口预期路径。

        # 缺失或目录对象都不能充当可执行 Python 入口。
        if not path_script.is_file():

            # 相对路径正文保持历史 quick_validate 合同。
            list_errors.append(
                f"missing registered task-classified script: scripts/python/{str_task_name}/{str_script_name}"
            )

    # 完整列表供主入口一次报告所有缺失项。
    return list_errors

# 可选文档门禁只在目标技能持久配置明确启用后执行。
def document_registry_errors(path_skill_dir: Path) -> list[str]:
    """检查显式启用的文档职责、知识指针和联合 SQLite 索引。

    参数：path_skill_dir 为待验证技能目录。
    返回：未启用时为空；启用后的治理或索引错误列表。
    """

    # registry 任务目录已由 load_common_module 加入模块搜索路径。
    module_type_module_document_registry: ModuleType = importlib.import_module("document_registry_common")  # 文档治理共享模块。

    # 配置缺失或 enabled 非真时可选门禁保持关闭。
    try:

        # 持久配置是唯一启用来源。
        dict_status = module_type_module_document_registry.document_governance_status(path_skill_dir)  # 当前文档门禁状态。

    # 配置存在但损坏时必须阻断而不是按未启用处理。
    except (OSError, ValueError) as object_error:

        # 返回稳定诊断供 quick_validate 前缀化。
        return [f"document registry config invalid: {object_error}"]

    # 未明确启用的技能不执行文档和数据库门禁。
    if not dict_status["enabled"]:

        # 空列表表示条件门禁不适用。
        return []

    # 联合注册表模块提供数据库领域异常和当前性检查。
    module_type_module_registry: ModuleType = importlib.import_module("registry_common")  # 联合注册表共享模块。

    # 文档治理 current 检查和数据库当前性必须共同通过。
    try:

        # 职责、重复裁决、接口映射与正文摘要使用同一完整门禁。
        module_type_module_document_registry.validate_document_governance(  # 当前文档治理验证结果。
            path_skill_dir,
            bool_require_current=True,
        )

        # 命令与知识联合索引必须与全部 JSON 源同步。
        tuple_database_result: tuple[sqlite3.Connection, object] = (  # 数据库当前性检查结果
            module_type_module_registry.ensure_database_current(path_skill_dir)  # 已验证的数据库连接和附加结果
        )

        # Windows 上后续构建需要及时释放只读句柄。
        connection_database: sqlite3.Connection = tuple_database_result[0]  # 已验证只读数据库连接

        # 及时释放只读数据库句柄，避免阻塞 Windows 后续构建。
        connection_database.close()

    # 文档、JSON、文件和 SQLite 领域错误统一成为预检诊断。
    except (OSError, ValueError, module_type_module_registry.RegistryError) as object_error:

        # 具体底层消息保留给维护者定位。
        return [f"document registry gate failed: {object_error}"]

    # 两层门禁均通过时没有诊断。
    return []

# agents-md-generator 自检先于通用 skill-creator 验证运行。
def self_governance_preflight_errors(
    path_skill_dir: Path,
    dict_script_tasks: dict[str, str],
) -> list[str]:
    """执行本技能专用的轻量入口一致性检查。

    参数：path_skill_dir 为技能目录；dict_script_tasks 为运行时脚本登记表。
    返回：陈旧分片与缺失登记入口的合并诊断。
    """

    # 仅名称和 SKILL.md 同时匹配时确认目标是本技能源码或发布包。
    path_skill_manifest = path_skill_dir / "SKILL.md"  # 技能说明文件路径。

    # 文档注册化是跨技能可选门禁，只由目标配置决定是否执行。
    list_document_errors = document_registry_errors(path_skill_dir)  # 当前技能文档注册诊断。

    # 外部技能不应用本仓库脚本登记表，但仍保留其显式启用的文档门禁。
    if path_skill_dir.name != "agents-md-generator" or not path_skill_manifest.is_file():

        # 返回条件文档门禁结果，不追加所有者专用脚本检查。
        return list_document_errors

    # 两类入口退化均应在调用外部验证器之前阻断。
    return (
        stale_numbered_shard_errors(path_skill_dir)
        + registered_script_errors(path_skill_dir, dict_script_tasks)
        + list_document_errors
    )

# 系统 skill-creator 是通用技能结构规则的来源。
def quick_validate_path() -> Path:
    """定位已安装 skill-creator 的 quick_validate.py。

    参数：无。
    返回：源码旁隔离系统技能或当前用户 Codex 主目录下的验证器路径。
    """

    # 源码旁的系统技能目录支持隔离评估和发布前自检。
    path_skill_root = Path(__file__).resolve().parents[3]  # 当前 agents-md-generator 技能根

    # CODEX_HOME 优先保证隔离验证和实际安装使用同一主目录。
    from agent_platform import load_agent_config, resolve_agent_home

    # 读取当前技能对应的平台安装档案。
    profile_agent = load_agent_config(path_skill_root)  # 当前平台配置档案

    # 环境变量只覆盖平台用户根，不改变技能安装目录规则。
    str_raw_home = os.environ.get("AGENT_HOME", "").strip() or os.environ.get("CODEX_HOME", "").strip()  # 用户根覆盖文本

    # 解析平台用户根以构造安装态候选位置。
    path_agent_home = resolve_agent_home(path_skill_root, str_raw_home, profile_agent.agent)  # 平台用户根目录

    # 候选顺序先保证 source-bound 验证可复现，再回退用户安装位置。
    list_candidates: list[Path] = [  # 系统 quick_validate 候选路径
        (  # 源码旁隔离系统技能候选
            path_skill_root.parent  # 源码旁系统技能父目录
            / ".system"  # 隔离系统技能目录
            / "skill-creator"  # 通用技能名称
            / "scripts"  # 系统工具脚本目录
            / "quick_validate.py"  # 通用快速验证入口
        ),
        # 远程环境没有 skill-creator 时使用技能内已通过的结构审计作为安全回退。
        path_skill_root / "scripts" / "python" / "verify" / "audit_skill.py",  # 技能内结构审计回退入口
        (  # 用户平台安装候选
            path_agent_home  # 平台安装候选的用户根起点
            / profile_agent.skill_install_dir  # 平台技能安装目录
            / ".system"  # 安装态系统技能目录
            / "skill-creator"  # 安装态通用技能名称
            / "scripts"  # 安装态工具脚本目录
            / "quick_validate.py"  # 安装态快速验证入口
        ),
    ]

    # 首个真实文件成为当前评估使用的通用校验器。
    for path_candidate in list_candidates:

        # 缺失候选不能阻断后续回退位置的检查。
        if path_candidate.is_file():

            # 返回可执行的系统校验器路径。
            return path_candidate

    # 保留用户目录路径以生成既有的缺失诊断。
    return list_candidates[-1]

# 外部验证器输出逐行添加项目固定级别和 Kind 前缀。
def write_prefixed_lines(str_text: str, *, bool_error: bool) -> None:
    """把外部工具文本按行写入对应标准流。

    参数：str_text 为外部输出；bool_error 决定使用 ERR 或 INFO 前缀及目标流。
    返回：无。
    """

    # 空文本不产生额外终端行。
    if not str_text:

        # 调用方可继续处理另一个输出流。
        return

    # 错误流使用 ERR，普通流使用 INFO。
    str_level = "ERR" if bool_error else "INFO"  # 当前输出严重级别。

    # 目标流与严重级别保持一致。
    file_stream = sys.stderr if bool_error else sys.stdout  # 当前输出目标流。

    # 每个外部输出行都成为独立、可分类的项目日志。
    for str_line in str_text.splitlines():

        # 空行不携带信息，避免生成只有前缀的日志。
        if not str_line:

            # 继续处理下一条非空外部消息。
            continue

        # 固定 Python Kind 便于仓库日志分类器识别。
        file_stream.write(f"> {str_level}: [Python] {str_line}\n")

# 主入口组合专用预检、通用验证器和退出码转发。
def main() -> None:
    """执行 quick_validate 治理链。

    参数：无；命令行可指定待验证技能目录。
    返回：无；验证失败通过 SystemExit 返回非零状态。
    异常：预检失败、验证器缺失或外部验证失败时抛出 SystemExit。
    """

    # 公共模块提供登记表和项目路径校验能力。
    module_agents_common_context = load_common_module()  # AGENTS 公共治理上下文。

    # 解析器只接收一个可选技能目录。
    argument_parser = argparse.ArgumentParser(  # 快速验证命令解析器。
        description="Run the installed skill-creator quick_validate helper.",  # CLI 帮助摘要。
    )

    # 缺省目标是当前工作目录。
    argument_parser.add_argument("skill_dir", nargs="?", default=".")

    # Namespace 保存调用者提供的技能位置。
    namespace_args: argparse.Namespace = argument_parser.parse_args()  # 当前命令行解析结果。

    # 公共路径规则拒绝不存在或非目录目标。
    path_skill_dir: Path = module_agents_common_context.resolve_project(namespace_args.skill_dir)  # 已验证技能目录。

    # 专用预检防止通用工具漏过本技能运行时退化。
    list_preflight_errors = self_governance_preflight_errors(  # 本技能入口治理诊断。
        path_skill_dir,  # 当前 agents-md-generator 源码或发布目录。
        module_agents_common_context.SCRIPT_TASK_BY_NAME,  # 公共脚本任务登记表。
    )

    # 活动路径硬编码门禁必须先于通用校验器执行。
    from agent_platform_gate import active_platform_hardcoding_gate

    # 当前技能树作为唯一输入执行平台路径硬编码门禁。
    dict_platform_gate: dict[str, Any] = active_platform_hardcoding_gate((path_skill_dir,))  # 活动平台门禁结果

    # 将平台门禁错误追加到专用预检诊断集合。
    list_preflight_errors.extend(str_error for str_error in dict_platform_gate["errors"])

    # 任一专用诊断都必须在调用外部验证器前阻断。
    if list_preflight_errors:

        # 所有诊断逐行写入错误流并保持稳定正文。
        for str_error in list_preflight_errors:

            # 复用外部输出写入器，为每条预检诊断添加 ERR 前缀。
            write_prefixed_lines(str_error, bool_error=True)

        # 预检失败使用通用非零状态。
        raise SystemExit(1)

    # 系统验证器路径在执行期解析，支持不同用户主目录。
    path_validator = quick_validate_path()  # 已安装通用技能验证器路径。

    # 缺少系统工具时给出可定位的阻断消息。
    if not path_validator.exists():

        # 错误正文包含期望路径，便于修复安装。
        raise SystemExit(f"> ERR: [Python] quick_validate helper not found: {path_validator}")

    # 子进程环境禁止字节码并强制 UTF-8，避免污染技能包或误解码输出。
    dict_environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")  # 外部验证器环境。

    # 外部工具在技能父目录运行，保持其相对路径假设。
    completed_process_validation = subprocess.run(  # 通用 quick_validate 执行结果。
        [sys.executable, str(path_validator), str(path_skill_dir)],  # Python、验证器和技能目录参数。
        cwd=path_skill_dir.parent,  # 通用验证器的工作目录。
        text=True,  # 以文本方式捕获两个输出流。
        capture_output=True,  # 先捕获再统一添加项目日志前缀。
        check=False,  # 退出码由本入口原样转发。
        env=dict_environment,  # 禁止缓存并启用 UTF-8 的子进程环境。
    )

    # 普通输出逐行映射为 Python INFO 日志。
    write_prefixed_lines(completed_process_validation.stdout, bool_error=False)

    # 错误输出逐行映射为 Python ERR 日志。
    write_prefixed_lines(completed_process_validation.stderr, bool_error=True)

    # 保留外部验证器退出码供自动化门禁判断。
    raise SystemExit(completed_process_validation.returncode)

# 直接执行脚本时启动验证链，模块导入保持无副作用。
if __name__ == "__main__":

    # main 负责完整预检、外部调用和退出码转发。
    main()
