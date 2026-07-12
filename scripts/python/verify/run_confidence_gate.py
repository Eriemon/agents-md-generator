"""执行 agents-md-generator 的本地置信、治理与发布前证据闭环。"""

# 推迟类型标注求值，避免直接执行脚本时提前解析可选类型。
from __future__ import annotations

# 标准库覆盖参数解析、子进程执行、临时目录和结构化报告处理。
import argparse
from collections import namedtuple
from collections.abc import Callable

# 序列化与环境模块支撑子进程机器协议。
import json
import os

# 路径、文件清理和进程模块构成治理执行边界。
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType
from typing import Any

# 置信门禁不得在技能树内留下缓存文件。
sys.dont_write_bytecode = True  # 禁止当前解释器写入字节码缓存

# 当前脚本目录用于定位同类验证工具。
SCRIPT_DIR = Path(__file__).resolve().parent  # verify 分类脚本根目录

# Python 工具根用于发现跨分类共享模块。
SCRIPTS_PYTHON_DIR = Path(__file__).resolve().parents[1]  # 分类脚本共同父目录

# 技能源根是默认审计和评估对象。
SKILL_DIR = Path(__file__).resolve().parents[3]  # agents-md-generator 源码目录

# 仓库根承载治理文档、测试和发布目录。
REPO_ROOT = Path(__file__).resolve().parents[5]  # 当前 Git 仓库根目录

# 源码仓 wrapper 位于仓库级测试目录。
TESTS_DIR = REPO_ROOT / "tests"  # 兼容评估入口所在目录

# 清理逻辑只处理 Python 解释器生成的缓存后缀。
PYTHON_CACHE_SUFFIXES = (".pyc", ".pyo")  # 可安全删除的缓存文件类型

# runner 策略显式区分强制、可选和用户禁用三种证据语义。
EVAL_RUNNER_POLICIES = {"required", "optional", "disabled"}  # 合法评估执行策略

# 共享模块采用延迟加载，保证导入本文件不会篡改搜索路径。
def load_agents_common() -> ModuleType:
    """按需加载跨任务目录共享的 agents_common 模块。

    Args:
        None: 共享模块位置由当前脚本目录推导。

    Returns:
        已加载的 agents_common 模块对象。
    """

    # 直接执行脚本时仅在首次调用前补齐兄弟任务目录。
    for path_task_directory in SCRIPTS_PYTHON_DIR.iterdir():

        # 非目录资产不可能承载共享 Python 模块。
        if not path_task_directory.is_dir():

            # 跳过文件以减少无意义的 sys.path 项。
            continue

        # 字符串路径用于与解释器当前模块搜索列表比较。
        str_task_directory = str(path_task_directory)  # 当前兄弟任务目录文本

        # 已登记目录无需重复插入模块搜索路径。
        if str_task_directory in sys.path:

            # 保持现有搜索顺序并继续检查其他任务目录。
            continue

        # 运行时调用阶段补齐兄弟任务模块搜索路径。
        sys.path.insert(0, str_task_directory)

    # 延迟导入避免模块加载阶段修改全局解释器搜索路径。
    import agents_common

    # 调用方通过模块属性访问共享映射和 CLI 辅助函数。
    return agents_common

# 项目路径解析保留公共模块的规范化语义。
def resolve_project(path_value: str | Path) -> Path:
    """通过共享 CLI 合同解析项目或技能路径。

    Args:
        path_value: 用户提供的相对或绝对路径。

    Returns:
        共享解析器规范化后的绝对路径。
    """

    # 延迟加载保证模块导入阶段不修改 sys.path。
    return load_agents_common().resolve_project(path_value)

# JSON 输出包装器保留测试可替换的模块级调用点。
def emit_json(dict_payload: dict[str, Any]) -> None:
    """通过共享 CLI 合同输出机器可读 JSON。

    Args:
        dict_payload: 待输出的置信门禁报告。

    Returns:
        本函数只写标准输出，不返回业务值。
    """

    # 保留公开替换点供 CLI 测试和上层集成捕获报告。
    load_agents_common().emit_json(dict_payload)

# 任务映射决定脚本实际所在的分类子目录。
def tool_script_path(script_name: str) -> Path:
    """返回当前工具 skill 的分类脚本路径。

    Args:
        script_name: 公共任务映射中登记的脚本文件名。

    Returns:
        对应分类目录内的脚本绝对路径。
    """

    # 公共模块持有脚本名到任务目录的唯一映射。
    module_type_agents_common = load_agents_common()  # 跨任务目录共享 CLI 模块

    # 分类目录名由公共映射统一维护。
    str_task_name = module_type_agents_common.SCRIPT_TASK_BY_NAME[script_name]  # 脚本所属任务目录名

    # 调用方需要可直接传给 Python 的绝对脚本路径。
    return SCRIPTS_PYTHON_DIR / str_task_name / script_name

# 子进程结果在此转换成后续聚合器消费的稳定字段。
def command_entry(name: str, argv: list[str], cwd: Path, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    """把子命令进程结果转换为统一门禁记录。

    Args:
        name: 置信门禁中的稳定命令名称。
        argv: 已执行的完整命令参数。
        cwd: 子命令执行目录。
        result: subprocess 返回的进程结果。

    Returns:
        包含进程输出和可选 JSON 载荷的命令记录。
    """

    # 基础记录无条件保留原始进程证据，便于失败追溯。
    dict_entry: dict[str, Any] = {  # 当前子命令的标准化执行记录
        "name": name,  # 稳定门禁命令名称
        "argv": argv,  # 实际执行的完整参数列表
        "cwd": str(cwd),  # 子命令实际工作目录
        "returncode": result.returncode,  # 子进程退出状态
        "stdout": result.stdout,  # 捕获的标准输出文本
        "stderr": result.stderr,  # 捕获的标准错误文本
    }

    # 保护 command_entry 中允许失败的外部访问。
    try:

        # 成功解析的载荷用于后续结构化错误聚合。
        dict_entry["json"] = json.loads(result.stdout)  # 可解析的机器报告

    # 非 JSON stdout 仍保留原文，结构化字段明确置空。
    except json.JSONDecodeError:

        # 空结构化字段防止把普通文本误解释为治理报告。
        dict_entry["json"] = None  # 标记当前命令未提供 JSON 报告

    # 返回值同时支持报告聚合与测试断言。
    return dict_entry

# 所有治理命令通过同一环境边界执行，避免运行时版本漂移。
def run_command(name: str, argv: list[str], cwd: Path, *, installed_skill_dir: Path | None = None) -> dict[str, Any]:
    """使用指定治理运行时执行置信门禁子命令。

    Args:
        name: 置信门禁中的稳定命令名称。
        argv: 待执行的完整命令参数。
        cwd: 子命令执行目录。
        installed_skill_dir: 可选安装态治理技能根。

    Returns:
        统一格式的命令执行记录。
    """

    # 显式安装态路径优先，否则使用当前源码技能作为治理运行时。
    path_governance_runtime = installed_skill_dir or SKILL_DIR  # 子命令使用的治理技能根

    # 子进程环境锁定治理技能并继续禁止缓存写入。
    dict_env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", AGENTS_MD_INSTALLED_SKILL_DIR=str(path_governance_runtime))  # 治理子进程环境

    # 捕获输出而不抛异常，使聚合器能够报告全部失败证据。
    completed_process_command_result: subprocess.CompletedProcess[str] = subprocess.run(  # 子命令进程结果
        argv,  # 治理子命令参数
        cwd=cwd,  # 子命令指定的工作目录
        text=True,  # 以字符串形式捕获进程输出
        capture_output=True,  # 同时保留 stdout 与 stderr 证据
        check=False,  # 非零退出码交由证据聚合器解释
        env=dict_env,  # 锁定治理技能并禁用字节码写入的环境
    )  # 捕获标准输出和错误流的子进程结果

    # 统一转换返回码、输出和可选 JSON 载荷。
    return command_entry(name, argv, cwd, completed_process_command_result)

# 跳过记录将策略状态与实际执行记录使用相同的数据形状。
# 命名元组避免动态加载时 dataclass 依赖模块注册状态。
SkippedCommandContext = namedtuple(  # runner 跳过证据的轻量不可变结构
    "SkippedCommandContext",  # 运行时类型名称
    "str_reason str_status int_returncode str_eval_kind str_runner_source",  # 跳过证据字段顺序
)  # 未执行评估所需的最小状态记录

# 未运行的评估也必须留下可审计的结构化证据。
def skipped_command_entry(
    name: str,
    argv: list[str],
    cwd: Path,
    context: SkippedCommandContext,
) -> dict[str, Any]:
    """构造未执行命令的门禁记录，保留 runner 和证据完整性线索。

    Args:
        name: 置信门禁中的稳定命令名称。
        argv: 原计划执行的完整命令参数。
        cwd: 原计划使用的执行目录。
        context: 跳过原因、状态、退出码和 runner 来源证据。

    Returns:
        保留跳过原因和证据完整性的统一命令记录。
    """

    # 跳过载荷区分证据缺口与真实功能失败。
    dict_payload: dict[str, Any] = {  # runner 跳过原因及可用性报告
        "status": context.str_status,  # required、optional 或 disabled 结果状态
        "skipped": True,  # 明确表明记录没有启动 runner
        "reason": context.str_reason,  # 未执行 runner 的具体原因
        "eval_kind": context.str_eval_kind,  # 本地或外部技能评估类别
        "runner_available": False,  # 跳过状态下没有可执行 runner
        "runner_source": context.str_runner_source,  # disabled 或 missing 来源状态
    }

    # required runner 缺失时同时形成结构化阻断错误。
    if context.int_returncode != 0:

        # errors 字段让通用聚合器沿用普通失败处理路径。
        dict_payload["errors"] = [context.str_reason]  # 强制策略的缺失错误

    # 跳过记录沿用普通命令字段以简化聚合逻辑。
    return {
        "name": name,  # 原计划执行的稳定命令名称
        "argv": argv,
        "cwd": str(cwd),
        "returncode": context.int_returncode,
        "stdout": json.dumps(dict_payload),
        "stderr": "",
        "json": dict_payload,
        "skipped": True,
        "eval_kind": context.str_eval_kind,
        "runner_available": False,
        "runner_source": context.str_runner_source,
    }

# 安装态 runner 路径必须由安装技能根推导，不能回落到源码脚本。
def installed_eval_runner_path(agents_generator_root: Path) -> Path:
    """返回安装态发布包内的正式 eval runner 路径。

    Args:
        agents_generator_root: 安装态 agents-md-generator 技能根。

    Returns:
        安装态正式评估 runner 路径。
    """

    # 固定相对布局属于版本化发布包合同。
    return agents_generator_root / "scripts" / "python" / "verify" / "run_skill_evals.py"

# 源码仓 wrapper 只作为开发态兼容回退入口。
def repo_local_eval_runner_path() -> Path:
    """返回源码仓兼容 wrapper 路径。

    Args:
        None: 路径由当前仓库 tests 根固定推导。

    Returns:
        源码仓测试兼容 runner 路径。
    """

    # tests wrapper 保持历史调用接口。
    return TESTS_DIR / "run_skill_evals.py"

# runner 解析顺序确保显式配置不会被本地环境悄然覆盖。
def resolve_eval_runner(eval_runner: Path | None, agents_generator_root: Path) -> tuple[Path, str, bool]:
    """按显式路径、安装态 runtime、源码仓 wrapper 的顺序定位 runner。

    Args:
        eval_runner: 调用方显式指定的可选 runner 路径。
        agents_generator_root: 安装态治理技能根。

    Returns:
        runner 路径、来源标识和可用状态组成的元组。
    """

    # 调用方提供路径时，无论存在与否都作为权威选择返回。
    if eval_runner is not None:

        # 规范路径进入最终证据，避免相对路径随工作目录漂移。
        path_explicit_runner = eval_runner.expanduser().resolve()  # 显式 runner 规范路径

        # 可用性单独返回，让策略层决定缺失是否阻断。
        return path_explicit_runner, "explicit_path", path_explicit_runner.is_file()

    # 安装态 runner 是发布验证的首选运行时。
    # 安装态路径来自调用方选择的治理技能根。
    path_installed_runner = installed_eval_runner_path(agents_generator_root)  # 安装包正式 runner

    # 已安装入口存在时不再探测源码仓兼容脚本。
    if path_installed_runner.is_file():

        # 来源标识进入最终置信报告。
        return path_installed_runner, "installed_runtime", True

    # 开发仓允许回退到 tests wrapper，保持源码验证可运行。
    # wrapper 回退只发生在安装态入口不存在时。
    path_repo_runner = repo_local_eval_runner_path()  # 源码仓兼容 runner

    # wrapper 存在时标记来源，避免把它误称为安装态证据。
    if path_repo_runner.is_file():

        # 源码回退仍属于有效 runner。
        return path_repo_runner, "repo_local_wrapper", True

    # 两类默认入口均缺失时返回预期安装路径辅助诊断。
    return path_installed_runner, "missing", False

# runner 策略在此统一映射成执行记录或跳过记录。
def run_eval_runner_command(
    name: str,
    argv_tail: list[str],
    cwd: Path,
    *,
    # 策略和评估类型共同决定跳过记录语义。
    eval_runner_policy: str,
    eval_kind: str,
    # 可选路径允许调用方锁定 runner 与治理运行时。
    eval_runner: Path | None = None,
    installed_skill_dir: Path | None = None,
) -> dict[str, Any]:
    """运行 eval runner，并按策略区分缺失、禁用和真实执行。

    Args:
        name: 置信门禁中的稳定命令名称。
        argv_tail: 追加在 runner 后的业务参数。
        cwd: runner 执行目录。
        eval_runner_policy: required、optional 或 disabled 策略。
        eval_kind: 写入证据记录的评估类型。
        eval_runner: 调用方显式指定的可选 runner。
        installed_skill_dir: 可选安装态治理技能根。

    Returns:
        已执行或跳过的统一命令记录。

    Raises:
        ValueError: eval runner 策略不受支持。
    """

    # runner 解析必须与当前治理命令使用同一技能版本。
    path_agents_generator_root = installed_skill_dir or SKILL_DIR  # 评估运行时技能根

    # 未知策略属于调用合同错误，不能静默降级。
    if eval_runner_policy not in EVAL_RUNNER_POLICIES:

        # 错误前缀遵循 current-project CLI 输出合同。
        raise ValueError(f"> ERR: [Python] unsupported eval runner policy: {eval_runner_policy}")

    # 解析结果同时携带路径、来源和文件可用性。
    tuple_runner = resolve_eval_runner(eval_runner, path_agents_generator_root)  # runner 定位结果

    # 分解后的字段分别驱动命令构造和证据记录。
    path_runner, str_runner_source, bool_runner_available = tuple_runner  # runner 路径与来源状态

    # 评估统一由当前 Python 解释器启动，避免环境漂移。
    list_argv = [sys.executable, str(path_runner), *argv_tail]  # 完整评估命令参数

    # 用户禁用时不启动进程，但证据完整性必须明确降级。
    if eval_runner_policy == "disabled":

        # 零退出码保留功能兼容，状态字段表达证据缺口。
        return skipped_command_entry(
            name,
            list_argv,
            cwd,
            SkippedCommandContext(
                "eval runner disabled by user", "disabled_by_user", 0, eval_kind, "disabled"
            ),
        )

    # 缺失 runner 的退出码由 required 或 optional 策略决定。
    if not bool_runner_available:

        # 状态名称明确区分阻断缺失与允许继续的证据缺口。
        str_missing_status = "missing_required" if eval_runner_policy == "required" else "missing_optional"  # runner 缺失状态

        # required 形成阻断，optional 仅形成不完整证据。
        return skipped_command_entry(
            name,
            list_argv,
            cwd,
            SkippedCommandContext(
                f"eval runner missing: {path_runner}",
                str_missing_status,
                1 if eval_runner_policy == "required" else 0,
                eval_kind,
                "missing",
            ),
        )

    # runner 可用时通过统一子进程边界执行。
    dict_entry = run_command(name, list_argv, cwd, installed_skill_dir=installed_skill_dir)  # 评估命令执行记录

    # 评估类型让聚合报告区分本地和外部技能证据。
    dict_entry["eval_kind"] = eval_kind  # 当前记录对应的评估范围

    # 成功定位状态独立于评估用例是否通过。
    dict_entry["runner_available"] = True  # runner 文件已确认存在

    # 来源用于判断证据来自安装态还是源码兼容入口。
    dict_entry["runner_source"] = str_runner_source  # runner 实际解析来源

    # 返回记录由统一证据聚合器继续解释。
    return dict_entry

# 缓存清理只删除可重建资产，不触碰源码或报告。
def cleanup_transient_artifacts(skill_dir: Path) -> None:
    """删除技能树内可能干扰审计的 Python 缓存目录。

    Args:
        skill_dir: 待清理的技能根目录。

    Returns:
        本函数只删除瞬态缓存，不返回业务值。
    """

    # 递归查找缓存目录，确保后续审计只观察版本化源码。
    for path in skill_dir.rglob("__pycache__"):

        # 目录检查防止异常同名文件触发递归删除。
        if path.is_dir():

            # 缓存删除失败不掩盖真正的治理诊断。
            shutil.rmtree(path, ignore_errors=True)

# 结构化报告中的 errors 字段统一转换为文本。
def parsed_errors(entry: dict[str, Any]) -> list[str]:
    """从命令记录的结构化 JSON 中提取错误文本。

    Args:
        entry: 统一格式的置信门禁命令记录。

    Returns:
        结构化 errors 字段的字符串列表。
    """

    # JSON 字段可能为空或属于其他机器协议类型。
    # 只有对象报告才能按 errors 键提取诊断。
    if not isinstance(entry.get("json"), dict):

        # 非对象报告没有可安全读取的错误集合。
        return []

    # 统一字符串化避免下游报告出现非序列化错误项。
    dict_parsed = dict(entry["json"])  # 已确认属于对象类型的命令报告

    # errors 缺失时按空集合处理。
    return [str(item) for item in (dict_parsed.get("errors") or [])]

# audit_skill 的缓存污染可在一次清理后安全重试。
def is_cache_only_audit_failure(entry: dict[str, Any]) -> bool:
    """判断 audit_skill 失败是否只由 Python 缓存文件导致。

    Args:
        entry: audit_skill 的统一命令记录。

    Returns:
        仅包含缓存路径错误时返回 True。
    """

    # 仅 audit_skill 允许使用这一恢复策略。
    if entry.get("name") != "audit_skill":

        # 其他门禁失败必须保留原始结果。
        return False

    # 缓存分类依据结构化错误文本，不解析人类可读 stderr。
    list_errors = parsed_errors(entry)  # audit_skill 报告的错误集合

    # 没有错误时不需要触发恢复性重试。
    if not list_errors:

        # 空集合不能证明存在缓存污染。
        return False

    # 只有每项错误都指向 Python 缓存时才允许自动恢复。
    return all("__pycache__" in item or any(suffix in item for suffix in PYTHON_CACHE_SUFFIXES) for item in list_errors)

# 版本读取直接服务发布门禁，缺失值必须显式进入报告。
def current_version(skill_dir: Path) -> str:
    """读取技能 VERSION；缺失时返回 unknown。

    Args:
        skill_dir: 待读取版本的技能根。

    Returns:
        去除空白后的版本文本或 unknown。
    """

    # VERSION 是源码技能与发布包共同使用的版本事实源。
    path_version = skill_dir / "VERSION"  # 技能版本文件路径

    # 缺失文件返回稳定占位值，由后续发布门禁形成诊断。
    return path_version.read_text(encoding="utf-8").strip() if path_version.is_file() else "unknown"

# 不可变上下文防止命令序列在执行中发生路径漂移。
# 字段顺序与关键字构造共同形成内部命令上下文合同。
ConfidenceGateContext = namedtuple(  # 全部门禁命令共享的规范化执行上下文
    "ConfidenceGateContext",  # 置信闭环上下文运行时类型名称
    (
        "path_project path_skill path_evals path_agents_generator "
        "path_external_skill str_review_base str_eval_runner_policy "
        "path_eval_runner str_version str_skill_argument"
    ),
)  # 项目路径、版本和 runner 策略的不可变载体

# 子命令执行器接收稳定名称、参数与可选工作目录。
GateCommandRunner = Callable[[str, list[str], Path], dict[str, Any]]  # 固定运行时的命令执行函数类型

# 公开选项在执行任何治理命令前完成规范化与合同验证。
def confidence_context(
    path_project: Path,
    path_skill: Path,
    dict_options: dict[str, Any],
) -> tuple[ConfidenceGateContext | None, dict[str, Any] | None]:
    """解析置信门禁选项并构造不可变执行上下文。

    Args:
        path_project: 待验证的受管项目根。
        path_skill: 待验证并准备发布的技能根。
        dict_options: 兼容公开关键字参数的门禁选项。

    Returns:
        有效上下文与空错误，或空上下文与缺少 review-base 的报告。

    Raises:
        ValueError: eval runner 策略不受支持。
    """

    # 治理生成器可以与被检查技能分离，默认使用当前技能源码。
    # 规范化路径确保所有子命令引用相同治理运行时。
    path_agents_generator = Path(dict_options.get("agents_generator_dir") or SKILL_DIR).resolve()  # 治理生成器绝对路径

    # 旧 require 标志只允许把策略收紧为 required。
    bool_require_runner = bool(dict_options.get("require_eval_runner"))  # 旧强制 runner 标志

    # 原始策略统一转成字符串后再做白名单验证。
    str_runner_policy = str(dict_options.get("eval_runner_policy", "required"))  # eval runner 执行策略

    # 显式强制标志覆盖其他策略输入。
    if bool_require_runner:

        # required 保持旧 CLI 的强制评估语义。
        str_runner_policy = "required"  # 旧强制标志映射后的策略

    # 未知策略不能静默降级证据完整性。
    if str_runner_policy not in EVAL_RUNNER_POLICIES:

        # 固定错误前缀满足 CLI 诊断合同。
        raise ValueError(f"> ERR: [Python] unsupported eval runner policy: {str_runner_policy}")

    # 自动审查治理必须有明确 Git 基线。
    str_review_base = str(dict_options.get("review_base") or "")  # 自动审查 Git 基线

    # 缺失基线时返回既有机器可读失败协议。
    if not str_review_base:

        # 失败报告不执行任何子命令。
        dict_missing_base = {  # 缺少审查基线的置信门禁报告
            "ok": False,  # 缺少基线时禁止执行自动审查
            "project": str(path_project),  # 未执行命令时仍报告受管项目
            "skill_dir": str(path_skill),  # 待验证技能仍写入提前失败报告
            "version": current_version(path_skill),  # 当前技能版本事实
            "commands": [],  # 提前失败没有任何子命令证据
            "errors": ["review_base is required for automated review governance; pass --review-base <sha>"],  # 缺少审查基线的阻断原因
        }

        # 调用方直接返回该失败报告。
        return None, dict_missing_base

    # 项目内技能使用相对路径，外部技能保留绝对路径。
    str_skill_argument = (  # 治理命令统一使用的技能路径参数
        path_skill.relative_to(path_project).as_posix()  # 项目内技能使用可移植相对路径
        if path_skill.is_relative_to(path_project)  # 判断是否可以使用项目相对路径
        else str(path_skill)  # 项目外技能必须保留绝对路径
    )

    # 可选路径保持 None，存在时统一解析为 Path。
    path_external_skill = (
        Path(str(dict_options["external_skill_dir"])).resolve()  # 已提供外部技能的绝对路径
        if dict_options.get("external_skill_dir")  # 仅解析调用方实际提供的目录
        else None  # 未要求外部评估时不制造路径
    )  # 外部技能绝对路径

    # evals_path 是正式效果评估的必需输入。
    path_evals = Path(dict_options["evals_path"]).resolve()  # 正式评估配置绝对路径

    # 显式 runner 路径仅在调用方提供时解析。
    path_eval_runner = Path(str(dict_options["eval_runner"])).resolve() if dict_options.get("eval_runner") else None  # 显式 runner 绝对路径

    # 直接返回不可变上下文，避免构造后发生局部重写。
    return ConfidenceGateContext(
        path_project=path_project,  # 受管项目根
        path_skill=path_skill,  # 待审计和发布的技能根
        path_evals=path_evals,  # 正式效果评估清单
        # 以下路径和策略锁定治理证据来源。
        path_agents_generator=path_agents_generator,  # 执行治理命令的技能版本
        path_external_skill=path_external_skill,  # 可选通用路径评估对象
        str_review_base=str_review_base,  # 自动审查使用的 Git 基线
        str_eval_runner_policy=str_runner_policy,  # required、optional 或 disabled 策略
        path_eval_runner=path_eval_runner,  # 可选显式评估入口
        str_version=current_version(path_skill),  # 待发布技能当前版本
        str_skill_argument=str_skill_argument,  # 治理子命令使用的技能路径参数
    ), None

# 闭包将所有子命令固定到同一项目和治理运行时。
def make_gate_command_runner(context: ConfidenceGateContext) -> GateCommandRunner:
    """创建固定项目和治理运行时的子命令执行器。

    Args:
        context: 置信门禁不可变执行上下文。

    Returns:
        接收命令名称、参数与可选目录的执行函数。
    """

    # 内层执行器只暴露命令差异，不允许调用方切换治理技能。
    def run_gate_command(
        str_name: str,
        list_argv: list[str],
        path_cwd: Path = context.path_project,
    ) -> dict[str, Any]:
        """使用同一安装态治理根执行一个置信门禁子命令。

        Args:
            str_name: 置信门禁中的稳定命令名称。
            list_argv: 待执行的完整命令参数。
            path_cwd: 子命令工作目录。

        Returns:
            统一格式的命令执行记录。
        """

        # 所有子命令共享同一治理运行时证据来源。
        return run_command(
            str_name,
            list_argv,
            path_cwd,
            installed_skill_dir=context.path_agents_generator,
        )

    # 闭包固定项目与治理生成器，命令构建器只提供业务参数。
    return run_gate_command

# 文档治理子命令共享同一基础参数布局。
def manage_docs_argv(str_action: str, path_project: Path) -> list[str]:
    """构造 manage_docs 的基础动作命令。

    Args:
        str_action: manage_docs 子命令名称。
        path_project: 受管项目根。

    Returns:
        可直接执行的 Python 命令参数列表。
    """

    # 文档治理入口由公共脚本映射定位。
    return [
        sys.executable,
        str(tool_script_path("manage_docs.py")),
        str_action,
        str(path_project),
    ]

# 发布前后阶段使用相同版本与安装意图参数。
def release_gate_argv(context: ConfidenceGateContext, str_phase: str) -> list[str]:
    """构造发布门禁 pre 或 post 阶段命令。

    Args:
        context: 置信门禁不可变执行上下文。
        str_phase: release-gate 阶段名称。

    Returns:
        含版本、技能路径和安装意图的完整命令参数。
    """

    # pre 与 post 阶段除阶段值外必须使用相同发布参数。
    return [
        *manage_docs_argv("release-gate", context.path_project),
        "--version",
        context.str_version,
        "--skill-dir",
        context.str_skill_argument,
        "--phase",
        str_phase,
        "--install-intent",
        "requested",
    ]

# 自动审查固定比较基线与 HEAD，覆盖全部治理类别。
def review_governance_argv(context: ConfidenceGateContext) -> list[str]:
    """构造全模式自动审查治理命令。

    Args:
        context: 置信门禁不可变执行上下文。

    Returns:
        固定 base、HEAD 和技能路径的审查命令参数。
    """

    # 审查范围同时覆盖代码、治理、文档和发布差异。
    return [
        sys.executable,
        str(tool_script_path("review_governance.py")),
        str(context.path_project),
        "--base",
        context.str_review_base,
        "--head",
        "HEAD",
        "--skill-dir",
        context.str_skill_argument,
        "--mode",
        "all",
    ]

# 审计失败仅在全部诊断都属于缓存污染时允许恢复重试。
def run_audit_with_cache_retry(
    context: ConfidenceGateContext,
    callable_run: GateCommandRunner,
) -> dict[str, Any]:
    """运行技能审计，并仅对缓存污染失败执行一次清理重试。

    Args:
        context: 置信门禁不可变执行上下文。
        callable_run: 固定治理运行时的命令执行器。

    Returns:
        首次审计记录或缓存清理后的重试记录。
    """

    # 首次审计使用待发布技能源码。
    dict_audit = callable_run(  # 技能审计命令记录
        "audit_skill",  # 缓存清理后复用原审计命令名称
        [sys.executable, str(tool_script_path("audit_skill.py")), str(context.path_skill)],  # 重试审计参数
        context.path_project,  # 缓存清理后的审计工作目录
    )

    # 只有纯缓存污染允许清理后自动重试。
    if not is_cache_only_audit_failure(dict_audit):

        # 非缓存失败必须保留原始证据。
        return dict_audit

    # 删除瞬态缓存后重新执行同一审计命令。
    cleanup_transient_artifacts(context.path_skill)

    # 返回清理后的权威审计记录。
    return callable_run(
        "audit_skill",
        [sys.executable, str(tool_script_path("audit_skill.py")), str(context.path_skill)],
        context.path_project,
    )

# 核心命令顺序覆盖审计、治理、效果评估和发布前后检查。
def core_gate_commands(
    context: ConfidenceGateContext,
    callable_run: GateCommandRunner,
) -> list[dict[str, Any]]:
    """按发布闭环顺序执行置信门禁核心命令。

    Args:
        context: 置信门禁不可变执行上下文。
        callable_run: 固定治理运行时的命令执行器。

    Returns:
        从审计到发布 post 门禁的有序命令记录。
    """

    # 审计记录可能包含一次缓存清理重试。
    dict_audit = run_audit_with_cache_retry(context, callable_run)  # 技能审计权威记录

    # 所有核心门禁保持既有执行顺序和命令名称。
    return [
        dict_audit,
        callable_run(
            "quick_validate",
            [sys.executable, str(tool_script_path("quick_validate.py")), str(context.path_skill)],
            context.path_project,
        ),
        callable_run(
            "manage_docs_verify",
            manage_docs_argv("verify", context.path_project),
            context.path_project,
        ),
        callable_run(
            "verify_agents",
            [
                sys.executable,
                str(tool_script_path("verify_agents.py")),
                str(context.path_project),
                "--installed-skill-dir",
                str(context.path_agents_generator),
            ],
            context.path_project,
        ),
        callable_run(
            "source_governance",
            [
                sys.executable,
                str(tool_script_path("check_source_governance.py")),
                str(context.path_project),
            ],
            context.path_project,
        ),
        callable_run(
            "evaluate_skill",
            [
                sys.executable,
                str(tool_script_path("evaluate_skill.py")),
                str(context.path_skill),
                str(context.path_project),
            ],
            context.path_project,
        ),
        run_eval_runner_command(
            "run_skill_evals",
            [str(context.path_evals)],
            context.path_project,
            eval_runner_policy=context.str_eval_runner_policy,
            eval_kind="skill_effectiveness_eval",
            eval_runner=context.path_eval_runner,
            installed_skill_dir=context.path_agents_generator,
        ),
        callable_run(
            "work_folder_gate",
            [
                *manage_docs_argv("work-folder-gate", context.path_project),
                "--skill-dir",
                context.str_skill_argument,
                "--mode",
                "release",
            ],
            context.path_project,
        ),
        callable_run(
            "check_freshness",
            [
                sys.executable,
                str(tool_script_path("check_freshness.py")),
                str(context.path_project),
            ],
            context.path_project,
        ),
        callable_run(
            "review_governance",
            review_governance_argv(context),
            context.path_project,
        ),
        callable_run(
            "branch_gate",
            manage_docs_argv("branch-gate", context.path_project),
            context.path_project,
        ),
        callable_run(
            "release_gate_pre",
            release_gate_argv(context, "pre"),
            context.path_project,
        ),
        callable_run(
            "release_gate_post",
            release_gate_argv(context, "post"),
            context.path_project,
        ),
    ]

# 发布目录和外部技能存在时才追加对应的可选证据命令。
def append_optional_gate_commands(
    list_commands: list[dict[str, Any]],
    context: ConfidenceGateContext,
    callable_run: GateCommandRunner,
) -> None:
    """追加已存在发布包预检和可选外部技能评估。

    Args:
        list_commands: 已执行的核心门禁记录列表。
        context: 置信门禁不可变执行上下文。
        callable_run: 固定治理运行时的命令执行器。

    Returns:
        本函数原地追加可选记录，不返回业务值。
    """

    # 已存在版本化发布目录时验证安装器能够接受该包。
    path_release = (  # 当前版本的预期发布目录
        context.path_project  # 版本化发布目录位于项目根 dist 下
        / "dist"  # 发布产物统一位于仓库 dist 目录
        / f"{context.path_skill.name}-{context.str_version}"  # 当前版本发布目录名
    )

    # 缺少发布目录时 pre 阶段仍可运行，不伪造安装证据。
    if path_release.is_dir():

        # skip 目标执行收据和内容策略验证而不写入安装位置。
        list_commands.append(
            callable_run(
                "install_skip",
                [
                    sys.executable,
                    str(tool_script_path("install_skill.py")),
                    str(path_release),
                    "--target",
                    "skip",
                    "--install-intent",
                    "requested",
                ],
                context.path_project,
            )
        )

    # 调用方提供外部技能时追加真实通用路径效果评估。
    if context.path_external_skill is not None:

        # 外部案例使用与本地案例相同的 runner 策略。
        list_commands.append(
            run_eval_runner_command(
                "external_skill_eval",
                [
                    str(context.path_evals),
                    "--external-skill-dir",
                    str(context.path_external_skill),
                ],
                context.path_project,
                eval_runner_policy=context.str_eval_runner_policy,
                eval_kind="external_skill_eval",
                eval_runner=context.path_eval_runner,
                installed_skill_dir=context.path_agents_generator,
            )
        )

# 源码治理的多类发现统一映射为置信门禁错误文本。
def source_governance_errors(dict_report: dict[str, Any]) -> list[str]:
    """提取源码治理报告中的尺寸、边界、注释和可读性错误。

    Args:
        dict_report: source_governance 的结构化 JSON 报告。

    Returns:
        带命令前缀的源码治理错误文本。
    """

    # 四类治理发现使用稳定前缀映射到置信门禁错误列表。
    list_errors = [  # 超限源码文件错误
        f"source_governance: oversized file {dict_item.get('path', '')}"  # 超限文件诊断文本
        for dict_item in dict_report.get("oversized_source_files", [])  # 报告登记的超限文件
    ]

    # 测试专用设计代码不得泄漏到生产目录。
    list_errors.extend(
        f"source_governance: test-only design code outside tests {dict_item.get('path', '')}"
        for dict_item in dict_report.get("test_code_boundary_violations", [])
    )

    # 注释策略发现保留文件与具体诊断。
    list_errors.extend(
        (
            f"source_governance: comment policy violation {dict_item.get('path', '')}: "
            f"{dict_item.get('message', '')}"
        )
        for dict_item in dict_report.get("comment_policy_violations", [])
    )

    # 可读性发现同样保留文件与具体诊断。
    list_errors.extend(
        (
            f"source_governance: readability violation {dict_item.get('path', '')}: "
            f"{dict_item.get('message', '')}"
        )
        for dict_item in dict_report.get("readability_violations", [])
    )

    # 返回完整源码治理错误集合。
    return list_errors

# 自动审查仅把结构化 finding 转换为阻断错误。
def review_governance_errors(dict_report: dict[str, Any]) -> list[str]:
    """提取自动审查治理报告中的结构化发现。

    Args:
        dict_report: review_governance 的结构化 JSON 报告。

    Returns:
        带 finding 代码和消息的错误文本。
    """

    # 非失败报告不贡献置信门禁错误。
    if dict_report.get("ok"):

        # 成功审查报告没有阻断发现。
        return []

    # 仅字典 finding 能提供稳定代码和消息。
    return [
        (
            f"review_governance: {dict_item.get('code', 'finding')}: "
            f"{dict_item.get('message', '')}"
        )
        for dict_item in dict_report.get("findings", [])
        if isinstance(dict_item, dict)
    ]

# 通用治理命令使用 errors、reasons 或布尔状态表达失败。
def standard_command_errors(str_name: str, dict_report: dict[str, Any]) -> list[str]:
    """提取使用通用 errors、reasons 或布尔状态的命令错误。

    Args:
        str_name: 当前门禁命令的稳定名称。
        dict_report: 命令返回的结构化报告。

    Returns:
        由通用字段表达的阻断错误列表。
    """

    # 当前列表只收集无需专用报告解析器的命令错误。
    list_errors: list[str] = []  # 通用治理合同产生的阻断错误

    # 这些命令统一用 errors 数组提供权威诊断。
    if str_name in {
        "audit_skill",
        "manage_docs_verify",
        "verify_agents",
        "evaluate_skill",
        "release_gate_pre",
        "release_gate_post",
        "install_skip",
    }:

        # 命令名前缀保留错误来源，便于最终报告定位。
        list_errors.extend(f"{str_name}: {str_item}" for str_item in dict_report.get("errors", []))

    # 分支门禁用 approved 与 reasons 描述污染或分支阻断。
    if str_name == "branch_gate" and not dict_report.get("approved"):

        # 每项原因独立进入错误列表，避免合并后丢失治理细节。
        list_errors.extend(f"{str_name}: {str_item}" for str_item in dict_report.get("reasons", []))

    # 发布工作目录门禁在 ok 为假时读取 errors。
    if str_name == "work_folder_gate" and not dict_report.get("ok"):

        # 工作目录诊断保持原始顺序。
        list_errors.extend(f"{str_name}: {str_item}" for str_item in dict_report.get("errors", []))

    # 鲜度报告通过 stale 字段表达根规则需要同步。
    if str_name == "check_freshness" and dict_report.get("stale"):

        # 固定消息让上层 CI 可以稳定归类鲜度失败。
        list_errors.append("check_freshness: AGENTS.md freshness check is stale")

    # 调用方继续合并需要专用语义的报告错误。
    return list_errors

# 源码治理、自动审查和效果评估具有各自的报告合同。
def specialized_command_errors(str_name: str, dict_report: dict[str, Any]) -> list[str]:
    """提取需要专用报告语义的治理与效果评估错误。

    Args:
        str_name: 当前门禁命令的稳定名称。
        dict_report: 命令返回的结构化报告。

    Returns:
        由源码治理或效果评估合同表达的阻断错误列表。
    """

    # 专用列表避免通用 errors 逻辑猜测复杂报告字段。
    list_errors: list[str] = []  # 需要专用解释的阻断错误

    # 源码治理解析器覆盖读取、规模和可读性发现。
    if str_name == "source_governance":

        # 专用解析器保留每类发现的路径与消息。
        list_errors.extend(source_governance_errors(dict_report))

    # 自动审查用 findings 而不是 errors 表达问题。
    if str_name == "review_governance":

        # 只接受结构化 finding，忽略无法归因的值。
        list_errors.extend(review_governance_errors(dict_report))

    # 本地正式评估要求汇总字段明确为绿。
    if str_name == "run_skill_evals" and not dict_report.get("summary", {}).get("ok"):

        # 稳定消息指向效果评估用例集合失败。
        list_errors.append("run_skill_evals: skill-effectiveness cases are not all green")

    # 外部技能评估采用独立名称，避免与本地结果混淆。
    if str_name == "external_skill_eval" and not dict_report.get("summary", {}).get("ok"):

        # 外部路径不绿时单独形成置信阻断。
        list_errors.append("external_skill_eval: external skill evaluation case is not green")

    # 专用诊断与通用诊断由上层按执行顺序合并。
    return list_errors

# 单命令解析同时区分功能错误与允许存在的证据缺口。
def structured_command_errors(
    str_name: str,
    dict_entry: dict[str, Any],
    dict_report: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """提取单条结构化命令记录的错误与证据缺口。

    Args:
        str_name: 置信门禁中的稳定命令名称。
        dict_entry: 包含 skipped 等元数据的命令记录。
        dict_report: 命令标准输出解析得到的 JSON 报告。

    Returns:
        错误列表与不完整证据列表组成的元组。
    """

    # optional 或 disabled runner 不阻断功能，但必须标记证据不完整。
    str_status = str(dict_report.get("status", ""))  # 跳过记录状态

    # 证据缺口独立于阻断错误，确保 optional 不伪装为完整证明。
    list_incomplete: list[str] = []  # 当前命令产生的证据缺口

    # 三类跳过状态都必须在最终报告中可见。
    if dict_entry.get("skipped") and str_status in {
        "missing_optional",
        "disabled_by_user",
        "missing_required",
    }:

        # 具体原因优先于稳定状态名。
        list_incomplete.append(
            f"{str_name}: {dict_report.get('reason', str_status)}"
        )

    # optional 或用户禁用状态只形成证据缺口，不检查缺失 summary。
    if str_status in {"missing_optional", "disabled_by_user"}:

        # 跳过记录没有执行结果，不能按 eval 失败解释。
        return [], list_incomplete

    # 跳过且携带 errors 时按普通错误处理。
    list_errors = [
        f"{str_name}: {str_item}"  # 跳过命令声明的单项错误
        for str_item in dict_report.get("errors", [])  # 跳过记录的结构化错误项
        if dict_entry.get("skipped")  # 只有跳过记录在此透传 errors
    ]  # 跳过命令声明的结构化错误

    # 通用合同与专用报告分别解析，避免单函数承担全部命令分支。
    list_errors.extend(standard_command_errors(str_name, dict_report))

    # 效果评估与治理 findings 在专用解析器中补充。
    list_errors.extend(specialized_command_errors(str_name, dict_report))

    # 调用方合并两类证据。
    return list_errors, list_incomplete

# 命令序列按实际执行顺序汇总，保持最终报告可追溯。
def collect_gate_evidence(
    list_commands: list[dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """汇总全部命令记录的错误和证据完整性缺口。

    Args:
        list_commands: 按闭环顺序执行的门禁记录。

    Returns:
        全部错误与不完整证据列表组成的元组。
    """

    # 两类集合必须分开，optional runner 不应伪装为完整绿灯。
    list_errors: list[str] = []  # 阻断置信门禁的错误

    # 不完整证据不改变兼容 ok，但会关闭 evidence_complete。
    list_incomplete: list[str] = []  # 不阻断功能但降低证据完整性的原因

    # 每条命令独立解析，保持报告顺序与执行顺序一致。
    for dict_entry in list_commands:

        # 稳定名称用于所有最终错误前缀。
        str_name = str(dict_entry["name"])  # 当前门禁命令名称

        # 非 JSON 输出仅能使用退出码证明失败。
        object_report = dict_entry.get("json")  # 当前命令可选结构化报告

        # 非对象载荷使用空报告参与通用退出码判断。
        dict_report = object_report if isinstance(object_report, dict) else {}  # 安全结构化报告

        # 没有结构化错误或 reasons 时保留非零退出码。
        # 已有结构化明细时不再追加重复的退出码消息。
        bool_has_detail = bool(dict_report.get("errors")) or (  # 是否已有可解释失败明细
            str_name == "branch_gate"  # 分支门禁使用 reasons 而非 errors
            and not dict_report.get("approved")  # 未批准分支需要检查 reasons
            and bool(dict_report.get("reasons"))  # 确认已有可解释分支诊断
        )

        # 非零退出码必须至少贡献一条错误。
        if dict_entry["returncode"] != 0 and not bool_has_detail:

            # 退出码诊断覆盖文本或空输出命令。
            list_errors.append(
                f"{str_name}: command exited with {dict_entry['returncode']}"
            )

        # 无结构化报告时不存在专用字段可解析。
        if not isinstance(object_report, dict):

            # 继续处理下一条命令。
            continue

        # 专用解析器返回命令错误与证据缺口。
        tuple_evidence = structured_command_errors(  # 当前命令的错误与证据缺口
            str_name,  # 当前命令稳定名称
            dict_entry,  # 当前命令原始执行元数据
            dict_report,  # 已验证为对象类型的机器报告
        )

        # 第一项追加阻断错误。
        list_errors.extend(tuple_evidence[0])

        # 第二项追加证据完整性缺口。
        list_incomplete.extend(tuple_evidence[1])

    # 返回两个有序集合供最终报告分别呈现。
    return list_errors, list_incomplete

# 完整置信门禁把规范化输入、命令证据和最终结论组合成报告。
def confidence_gate(
    project: Path,
    skill_dir: Path,
    **options: Any,
) -> dict[str, Any]:
    """执行完整置信门禁并返回统一证据报告。

    Args:
        project: 待验证的受管项目根。
        skill_dir: 待验证并准备发布的技能根。
        **options: evals、治理生成器、审查基线和 runner 等兼容选项。

    Returns:
        包含命令记录、错误和证据完整性的门禁报告。

    Raises:
        ValueError: eval runner 策略不受支持。
        RuntimeError: 内部上下文构造合同被破坏。
    """

    # 选项解析同时处理旧 runner 强制标志和 review-base 前置条件。
    tuple_context = confidence_context(project, skill_dir, options)  # 执行上下文与提前失败报告

    # 第二项存在时表示 review-base 缺失，无需执行子命令。
    if tuple_context[1] is not None:

        # 类型由 context 构造合同保证为字典。
        return tuple_context[1]

    # 第一项在无提前失败时必定是有效上下文。
    context = tuple_context[0]  # 已通过 review-base 前置检查的执行上下文

    # 防御性检查避免静态类型之外的意外空上下文。
    if context is None:

        # 该路径代表内部合同破坏而非用户输入错误。
        raise RuntimeError("> ERR: [Python] confidence context was not created")

    # 审计前清理目标技能瞬态缓存。
    cleanup_transient_artifacts(context.path_skill)

    # 外部技能存在时也清理其缓存，避免通用路径假失败。
    if context.path_external_skill is not None:

        # 清理仅限 Python 缓存目录。
        cleanup_transient_artifacts(context.path_external_skill)

    # 固定治理运行时的执行器保证所有命令使用同一版本。
    gate_command_runner_run = make_gate_command_runner(context)  # 置信门禁子命令执行器

    # 核心命令从审计顺序执行到 release post。
    list_commands = core_gate_commands(context, gate_command_runner_run)  # 核心门禁命令记录

    # 发布包预检与外部技能评估仅在对应输入存在时追加。
    append_optional_gate_commands(list_commands, context, gate_command_runner_run)

    # 错误和证据缺口分别汇总，防止 optional 被误读为完整。
    tuple_evidence = collect_gate_evidence(list_commands)  # 全部门禁错误与证据缺口

    # 第一项决定功能门禁最终 ok。
    list_errors = tuple_evidence[0]  # 置信门禁阻断错误

    # 第二项决定 evidence_complete，但不改变兼容 ok 语义。
    list_incomplete = tuple_evidence[1]  # 评估证据完整性缺口

    # 旧 CLI 选项产生的弃用警告由调用方显式传入。
    list_deprecation_warnings = list(options.get("deprecation_warnings") or [])  # CLI 弃用警告

    # 最终报告保持既有字段，供测试、发布工具和 CI 消费。
    return {
        "ok": not list_errors,
        "project": str(context.path_project),
        "skill_dir": str(context.path_skill),
        "agents_generator_dir": str(context.path_agents_generator),
        "version": context.str_version,
        "evidence_complete": not list_incomplete,
        "incomplete_evidence": list_incomplete,
        "eval_runner_policy": context.str_eval_runner_policy,
        "deprecation_warnings": list_deprecation_warnings,
        "commands": list_commands,
        "errors": list_errors,
    }

# CLI 入口将用户参数转换为完整置信报告和稳定退出码。
def main() -> int:
    """解析 CLI 参数、执行置信门禁并输出机器可读报告。

    Args:
        None: 参数来自当前进程命令行。

    Returns:
        门禁通过返回 0，否则返回 1。
    """

    # CLI 描述明确该入口只执行仓库本地置信闭环。
    parser = argparse.ArgumentParser(description="Run the repository-local confidence gate for agents-md-generator.")  # 命令行参数解析器

    # 项目位置保留可选位置参数以兼容历史调用。
    parser.add_argument("project", nargs="?", default=".")

    # 技能源路径允许验证非默认副本。
    parser.add_argument("--skill-dir", default=str(SKILL_DIR))

    # 正式评估清单默认来自当前技能源码。
    parser.add_argument("--evals-path", default=str(SKILL_DIR / "evals" / "evals.json"))

    # 治理生成器可指向独立安装态运行时。
    parser.add_argument("--agents-generator-dir", default=str(SKILL_DIR))

    # 外部技能输入用于验证跨技能适用性证据。
    parser.add_argument("--external-skill-dir", default=None)

    # 自动审查必须由调用方提供明确 Git 比较基线。
    parser.add_argument("--review-base", default=None)

    # runner 策略决定缺失或禁用是否阻断最终结论。
    parser.add_argument("--eval-runner-policy", choices=sorted(EVAL_RUNNER_POLICIES), default="required")

    # 显式 runner 路径覆盖安装态和源码仓自动探测。
    parser.add_argument("--eval-runner", default=None)

    # 旧 optional 开关继续解析但会产生弃用警告。
    parser.add_argument("--skip-missing-eval-runner", action="store_true")

    # 旧 required 开关保持向后兼容。
    parser.add_argument("--require-eval-runner", action="store_true")

    # 参数对象只在本入口内转换成显式路径与策略字段。
    args = parser.parse_args()  # 已解析的置信门禁 CLI 参数

    # 互斥旧标志不能同时映射为两个相反策略。
    if args.skip_missing_eval_runner and args.require_eval_runner:

        # 两个旧兼容标志语义冲突，解析阶段直接拒绝。
        parser.error("--skip-missing-eval-runner and --require-eval-runner are mutually exclusive")

    # 新策略参数是兼容标志覆盖前的默认事实源。
    str_eval_runner_policy = args.eval_runner_policy  # 最终 eval runner 策略

    # 弃用警告随机器报告返回，避免污染 JSON 标准输出。
    list_deprecation_warnings: list[str] = []  # 本次调用触发的兼容标志警告

    # skip-missing 旧语义等价于 optional 策略。
    if args.skip_missing_eval_runner:

        # 旧 skip 标志只降低 runner 缺失的阻断等级。
        str_eval_runner_policy = "optional"  # 兼容标志覆盖后的策略

        # 警告给出稳定替代参数，便于调用方迁移。
        list_deprecation_warnings.append("--skip-missing-eval-runner is deprecated; use --eval-runner-policy optional")

    # require 标志恢复必须存在 runner 的历史行为。
    if args.require_eval_runner:

        # 显式强制优先于新参数中可能提供的 optional 值。
        str_eval_runner_policy = "required"  # 强制 runner 的兼容策略

        # 即使语义与默认一致也保留弃用证据。
        list_deprecation_warnings.append("--require-eval-runner is deprecated; use --eval-runner-policy required")

    # 项目路径采用公共解析规则处理相对路径与用户目录。
    path_project = resolve_project(args.project)  # 规范化受管项目根

    # 技能源目录使用相同路径规范化合同。
    path_skill_dir = resolve_project(args.skill_dir)  # 规范化待验证技能根

    # 治理生成器目录允许与被检查技能目录分离。
    path_agents_generator_dir = resolve_project(args.agents_generator_dir)  # 规范化治理运行时技能根

    # 评估清单不要求已存在，由正式 runner 输出权威诊断。
    path_evals = Path(args.evals_path).expanduser().resolve()  # 正式评估配置路径

    # 显式 runner 缺失时保留 None 以启用标准探测顺序。
    path_eval_runner = Path(args.eval_runner).expanduser().resolve() if args.eval_runner else None  # 可选显式 runner 路径

    # 外部技能不是本地发布闭环的必需输入。
    path_external_skill_dir = Path(args.external_skill_dir).expanduser().resolve() if args.external_skill_dir else None  # 可选外部技能根

    # 保存置信度门禁载荷，确保 JSON 与退出状态依据同一证据结论。
    dict_confidence_result = confidence_gate(  # CLI 最终输出的置信门禁报告
        path_project,  # 本次闭环所验证的仓库根
        path_skill_dir,  # 规范化待发布技能根
        evals_path=path_evals,  # 正式效果评估配置
        # 后续参数固定治理运行时、外部评估和兼容策略。
        agents_generator_dir=path_agents_generator_dir,  # 固定治理命令运行时
        external_skill_dir=path_external_skill_dir,  # 可选跨技能评估输入
        review_base=args.review_base,  # 自动审查比较起点
        eval_runner_policy=str_eval_runner_policy,  # 缺失 runner 的处理策略
        eval_runner=path_eval_runner,  # 调用方锁定的评估脚本路径
        require_eval_runner=args.require_eval_runner,  # 旧强制 runner 兼容标志
        deprecation_warnings=list_deprecation_warnings,  # 写入机器报告的兼容参数警告
    )

    # 输出既有机器可读协议，保持上层调用接口不变。
    emit_json(dict_confidence_result)

    # 将权威 ok 字段映射为进程退出码。
    return 0 if dict_confidence_result["ok"] else 1

# 直接执行入口只负责把业务结论转换为进程退出状态。
if __name__ == "__main__":

    # 把置信度门禁状态传递给调用进程。
    raise SystemExit(main())
