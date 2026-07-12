"""执行技能仓库的编译、治理、渲染和行为评估链。"""

# 延迟类型标注求值，支持运行时脚本环境。
from __future__ import annotations

# 启动阶段需要登记兄弟任务模块。
import sys
from pathlib import Path

# 分类脚本入口需要在导入公共模块前登记兄弟任务目录。
def extend_task_module_search_path() -> None:
    """把 Python 任务子目录加入当前解释器搜索路径。

    Args:
        None: 搜索根由当前文件位置确定。

    Returns:
        None: 函数只更新当前解释器搜索路径。
    """

    # Python 脚本根包含评估器依赖的公共任务模块。
    path_scripts_python_root = Path(__file__).resolve().parents[1]  # 分类脚本共同父目录

    # 每个任务目录都可能提供裸模块名兼容入口。
    for path_task_directory in path_scripts_python_root.iterdir():

        # 普通文件不能作为模块搜索目录。
        if path_task_directory.is_dir():

            # 字符串路径用于和解释器现有条目比较。
            str_task_path = str(path_task_directory)  # 当前任务目录搜索路径

            # 避免重复插入改变既有模块解析顺序。
            if str_task_path not in sys.path:

                # 兄弟任务模块沿用历史裸模块导入方式。
                sys.path.insert(0, str_task_path)

# 公共依赖加载前执行一次兼容引导。
extend_task_module_search_path()  # 完成分类任务目录引导

# 标准库负责参数解析、编译、序列化和子进程执行。
import argparse
import compileall
import json
import os
import re
import shutil
import subprocess

# 开放类型仅用于外部命令的 JSON 载荷。
from typing import Any

# 评估子进程和当前进程都禁止生成缓存文件。
sys.dont_write_bytecode = True  # 禁止当前评估进程写入缓存

# 公共工具提供脚本分类、项目解析和 JSON 输出。
from agents_common import SCRIPT_TASK_BY_NAME, emit_json, resolve_project

# 渲染结果不得保留未解析的大写占位符。
PLACEHOLDER_RE = re.compile(r"{{[A-Z0-9_]+}}")  # 未解析模板占位符模式

# 发布输出不得泄露历史本地参考资料路径。
LOCAL_REFERENCE_RE = re.compile(  # 本地参考路径泄露模式
    r"G:[/\\]html|ref[/\\](agent-rules|html)",  # 历史本地参考目录
    flags=re.IGNORECASE,  # Windows 路径盘符不区分大小写
)

# 工具技能根用于定位分类脚本和系统校验器。
TOOL_SKILL_DIR = Path(__file__).resolve().parents[3]  # 当前 agents-md-generator 技能目录

# 分类映射是所有工具脚本路径的唯一来源。
def tool_script_path(script_name: str) -> Path:
    """返回当前工具技能的分类脚本路径。

    Args:
        script_name: 已登记的工具脚本文件名。

    Returns:
        工具技能内对应分类目录的脚本路径。
    """

    # 公共映射防止评估器复制目录分类规则。
    str_task_name = SCRIPT_TASK_BY_NAME[script_name]  # 脚本所属任务分类

    # 分类目录与脚本名共同形成稳定工具路径。
    return TOOL_SKILL_DIR / "scripts" / "python" / str_task_name / script_name

# 分类名称区分工具、自仓治理、目标治理和目标行为失败。
ERROR_CATEGORY_NAMES = (
    "tooling_error",  # 工具自身无法执行
    "self_repo_governance_error",  # 当前技能仓库治理失败
    "target_repo_governance_error",  # 被评估项目治理失败
    "target_repo_behavior_error",  # 被评估技能行为失败
)

# 命令结果统一转换成后续错误分类可消费的映射。
def command_entry(name: str, argv: list[str], cwd: Path, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    """序列化单次子进程执行结果并尝试解析 JSON 输出。

    Args:
        name: 评估链中的命令名称。
        argv: 实际执行的参数列表。
        cwd: 子进程工作目录。
        result: subprocess 返回的完成结果。

    Returns:
        包含文本输出、退出码和可选 JSON 的命令记录。
    """

    # 原始输出必须保留，以便非 JSON 命令仍可诊断。
    dict_entry: dict[str, Any] = {  # 标准命令执行记录
        "name": name,  # 评估步骤名称
        "argv": argv,  # 实际命令参数
        "cwd": str(cwd),  # 执行工作目录
        "returncode": result.returncode,  # 子进程退出码
        "stdout": result.stdout,  # 标准输出正文
        "stderr": result.stderr,  # 标准错误正文
    }

    # 结构化输出存在时供各门禁提取详细错误。
    try:

        # 成功解析后保存原始 JSON 载荷。
        dict_entry["json"] = json.loads(result.stdout)  # 结构化命令输出

    # 非 JSON 输出仍需保留为合法命令记录。
    except json.JSONDecodeError:

        # 普通文本命令显式记录无 JSON 载荷。
        dict_entry["json"] = None  # 非结构化输出标记

    # 单一记录格式简化后续错误聚合。
    return dict_entry

# 通用命令运行器统一隔离字节码缓存。
def run_command(name: str, argv: list[str], cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    """运行评估子命令并返回标准命令记录。

    Args:
        name: 评估步骤名称。
        argv: 待执行命令参数。
        cwd: 子进程工作目录。
        env: 可选的完整环境变量映射。

    Returns:
        command_entry 规范化后的执行记录。
    """

    # 复制环境避免原位污染调用方或当前进程。
    dict_command_env = dict(env) if env is not None else dict(os.environ)  # 子进程环境副本

    # 评估过程不得在被测技能中留下缓存目录。
    dict_command_env["PYTHONDONTWRITEBYTECODE"] = "1"  # 禁止写入 Python 字节码

    # 保留失败结果而不抛异常，交由分类器生成稳定诊断。
    completed_process_command_result: subprocess.CompletedProcess[str] = subprocess.run(  # 子进程完成结果
        argv,  # 通用运行器收到的参数
        cwd=cwd,  # 调用方指定的工作目录
        text=True,  # 文本模式输出
        capture_output=True,  # 捕获标准输出和错误
        check=False,  # 非零退出交给错误分类器
        env=dict_command_env,  # 隔离后的子进程环境
    )

    # 所有命令都通过同一序列化边界返回。
    return command_entry(name, argv, cwd, completed_process_command_result)

# 快速校验器优先使用当前工具技能中的受管实现。
def quick_validate_script() -> Path:
    """查找可用的 skill-creator 快速校验脚本。

    Args:
        None: 候选位置由当前工具技能与 Codex 安装根确定。

    Returns:
        首个存在的 quick_validate.py 路径。

    Raises:
        FileNotFoundError: 所有受支持位置均缺少校验脚本。
    """

    # 候选顺序保证仓库实现优先于系统安装回退。
    list_candidates = [  # 快速校验脚本候选路径
        tool_script_path("quick_validate.py"),  # 当前工具技能实现
        TOOL_SKILL_DIR.parent / ".system" / "skill-creator" / "scripts" / "quick_validate.py",  # 同级系统技能
        Path.home() / ".codex" / "skills" / ".system" / "skill-creator" / "scripts" / "quick_validate.py",  # 用户安装回退
    ]

    # 首个真实文件即为本次评估使用的校验器。
    for path_candidate in list_candidates:

        # 目录或缺失路径不能作为命令入口。
        if path_candidate.is_file():

            # 返回最高优先级的可用脚本。
            return path_candidate

    # 缺少校验器属于工具配置错误而非目标技能错误。
    raise FileNotFoundError(
        "> ERR: [Python] quick_validate helper not found in supported skill-creator locations"
    )

# 编译门禁只扫描目标技能实际存在的 Python 根目录。
def existing_python_roots(skill_dir: Path) -> list[str]:
    """返回目标技能中存在的 Python 源码根目录名称。

    Args:
        skill_dir: 待评估技能目录。

    Returns:
        按固定优先级排列的现有源码根名称。
    """

    # 固定列表避免把任意数据目录误当成 Python 源码。
    list_roots: list[str] = []  # 已确认存在的源码根名称

    # 顺序与编译报告和历史评估输出保持一致。
    for str_name in ("runtime", "integration", "scripts", "tests"):

        # 不存在的可选根无需传给 compileall。
        if (skill_dir / str_name).exists():

            # 只记录相对名称，命令工作目录已固定为技能根。
            list_roots.append(str_name)

    # 空列表表示目标技能没有可编译 Python 表面。
    return list_roots

# 设置文件参数只在目标技能真实提供默认配置时启用。
def settings_arg(skill_dir: Path) -> list[str]:
    """构造目标技能验证脚本的可选设置参数。

    Args:
        skill_dir: 待评估技能目录。

    Returns:
        空列表或包含 --settings 与配置路径的参数。
    """

    # 配置发现逻辑集中在 preferred_settings_path。
    path_settings = preferred_settings_path(skill_dir)  # 首选默认设置文件

    # 没有默认配置时保持验证脚本自身默认行为。
    if path_settings is None:

        # 空参数可直接拼接到命令列表。
        return []

    # 显式设置路径保证验证行为可复现。
    return ["--settings", str(path_settings)]

# 默认设置支持资产目录和传统配置目录两种布局。
def preferred_settings_path(skill_dir: Path) -> Path | None:
    """返回目标技能首选的默认设置文件。

    Args:
        skill_dir: 待评估技能目录。

    Returns:
        首个存在的设置文件；没有候选时返回 None。
    """

    # 资产目录是当前布局，config 目录保留向后兼容。
    for str_relative in ("assets/defaults.json", "config/defaults.json"):

        # 每个候选都相对于目标技能根解析。
        path_settings = skill_dir / str_relative  # 当前默认设置候选

        # 只有普通文件可以传给验证脚本。
        if path_settings.is_file():

            # 候选顺序决定首选设置文件。
            return path_settings

    # 缺少设置文件不是技能验证错误。
    return None

# 个别技能需要在统一评估中关闭其内部隔离递归。
def validate_script_env(base_env: dict[str, str], skill_dir: Path) -> dict[str, str]:
    """构造目标技能验证脚本的隔离环境。

    Args:
        base_env: 评估流程基础环境变量。
        skill_dir: 待评估技能目录。

    Returns:
        可安全传给目标验证脚本的环境副本。
    """

    # 环境副本防止技能特例污染其他评估步骤。
    dict_env = dict(base_env)  # 目标验证脚本环境

    # 远程 SSH 技能若递归启动隔离验证会形成自调用。
    if skill_dir.name == "erie-remote-ssh":

        # 专用开关只作用于该技能的验证子进程。
        dict_env["ERIE_REMOTE_SSH_SKIP_ISOLATED_VALIDATION"] = "1"  # 跳过递归隔离验证

    # 其他技能获得未增加特例的基础环境副本。
    return dict_env

# 目标技能可提供一个专用 validate*.py 入口。
def discover_validate_script(skill_dir: Path) -> Path | None:
    """发现目标技能唯一或按名称匹配的验证脚本。

    Args:
        skill_dir: 待评估技能目录。

    Returns:
        可确定的验证脚本路径；没有唯一入口时返回 None。
    """

    # 验证脚本只允许从技能标准 scripts 目录发现。
    path_scripts_directory = skill_dir / "scripts"  # 目标技能脚本目录

    # 没有脚本目录的技能跳过专用验证步骤。
    if not path_scripts_directory.is_dir():

        # None 明确表示无需添加 validate_script 命令。
        return None

    # quick_validate 属于通用门禁，不能重复当作技能专用入口。
    list_candidates = sorted(  # 专用验证脚本候选
        path_candidate  # 当前 validate 脚本
        for path_candidate in path_scripts_directory.glob("validate*.py")  # 脚本目录候选
        if path_candidate.name != "quick_validate.py"  # 排除通用快速校验器
    )

    # 单一候选没有歧义，可以直接执行。
    if len(list_candidates) == 1:

        # 返回唯一专用验证脚本。
        return list_candidates[0]

    # 多候选时按技能名称寻找约定入口。
    path_preferred = (  # 技能名称对应的验证脚本
        path_scripts_directory / f"validate_{skill_dir.name.replace('-', '_')}.py"  # 约定文件名
    )

    # 精确命名候选消除多脚本歧义。
    if path_preferred in list_candidates:

        # 返回与技能名称匹配的入口。
        return path_preferred

    # 多候选且无名称匹配时不猜测执行入口。
    return None

# 评估结束后清理目标技能内产生的 Python 缓存。
def cleanup_python_caches(skill_dir: Path) -> None:
    """删除目标技能中的所有 __pycache__ 目录。

    Args:
        skill_dir: 待清理的技能目录。

    Returns:
        None: 清理失败由 ignore_errors 策略吸收。
    """

    # 递归覆盖运行时、集成、脚本和测试源码根。
    for path_cache in skill_dir.rglob("__pycache__"):

        # 只删除真实目录，避免误处理同名普通文件。
        if path_cache.is_dir():

            # 缓存清理不能覆盖主要评估结果。
            shutil.rmtree(path_cache, ignore_errors=True)

# 临时产物清理入口集中封装当前缓存策略。
def cleanup_transient_artifacts(skill_dir: Path) -> None:
    """清理技能评估产生的非持久化文件。

    Args:
        skill_dir: 待清理的技能目录。

    Returns:
        None: 当前策略只删除 Python 缓存。
    """

    # 独立入口便于未来扩展受治理的临时产物类型。
    cleanup_python_caches(skill_dir)

# 渲染步骤需要额外检查占位符和本地路径泄露。
def render_entry(project: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    """运行 AGENTS 渲染器并补充输出内容检查结果。

    Args:
        project: 待渲染项目根目录。
        env: 可选的完整子进程环境。

    Returns:
        带占位符和本地引用检查结果的命令记录。
    """

    # 渲染器使用当前解释器避免环境版本漂移。
    list_argv = [  # AGENTS 渲染命令参数
        sys.executable,  # 当前 Python 解释器
        str(tool_script_path("render_agents.py")),  # 渲染脚本路径
        str(project),  # 待渲染项目根
    ]

    # 环境副本隔离字节码开关和调用方状态。
    dict_command_env = dict(env) if env is not None else dict(os.environ)  # 渲染子进程环境

    # 渲染过程不得向项目写入 Python 缓存。
    dict_command_env["PYTHONDONTWRITEBYTECODE"] = "1"  # 禁止渲染子进程写字节码

    # 渲染失败也要捕获输出供统一错误分类。
    completed_process_command_result: subprocess.CompletedProcess[str] = subprocess.run(  # 渲染完成结果
        list_argv,  # 专用渲染参数
        cwd=project,  # 项目根作为渲染工作目录
        text=True,  # 渲染输出按文本读取
        capture_output=True,  # 捕获渲染正文和诊断
        check=False,  # 保留非零退出供统一处理
        env=dict_command_env,  # 禁止字节码的渲染环境
    )

    # 标准命令记录保留渲染退出码和文本输出。
    dict_entry = command_entry(  # 渲染命令记录
        "render_agents",  # 命令分类名称
        list_argv,  # 已执行渲染参数
        project,  # 渲染工作目录
        completed_process_command_result,  # 原始完成结果
    )

    # 内容检查只分析渲染器标准输出。
    str_output = completed_process_command_result.stdout  # 待检查的渲染正文

    # 两类泄露事实覆盖普通命令 JSON 载荷。
    dict_entry["json"] = {
        "unresolved_placeholders": sorted(  # 未解析模板占位符
            set(PLACEHOLDER_RE.findall(str_output))  # 去重占位符匹配
        ),
        "local_reference_leaks": sorted(  # 本地参考路径泄露
            set(  # 去重本地参考匹配
                match.group(0)  # 当前本地路径匹配正文
                for match in LOCAL_REFERENCE_RE.finditer(str_output)  # 遍历正文路径匹配
            )
        ),
    }

    # 调用方将内容错误与其他治理命令统一收集。
    return dict_entry

# verify_agents 的扫描范围不得重新纳入明确跳过的参考资料。
def verify_agents_content_errors(dict_parsed: dict[str, Any]) -> list[str]:
    """提取 verify_agents 结果中的参考文件扫描错误。

    Args:
        dict_parsed: verify_agents 的结构化输出。

    Returns:
        所有错误扫描参考文件的诊断文本。
    """

    # 仅 ref 前缀证明验证器越过了跳过边界。
    return [
        f"verify_agents: checked skipped reference file {item_checked}"
        for item_checked in dict_parsed.get("checked_files", []) or []
        if str(item_checked).startswith("ref/")
    ]

# 渲染内容检查分别报告占位符和本地参考路径。
def render_content_errors(dict_parsed: dict[str, Any]) -> list[str]:
    """提取 AGENTS 渲染正文的内容泄露错误。

    Args:
        dict_parsed: render_entry 生成的结构化检查结果。

    Returns:
        未解析占位符和本地路径泄露诊断。
    """

    # 两类错误使用不同前缀以便定位修复来源。
    list_errors = [  # 渲染内容错误
        f"render_agents: unresolved placeholder {item}"  # 当前占位符诊断
        for item in dict_parsed.get("unresolved_placeholders", []) or []  # 占位符集合
    ]

    # 本地参考路径错误追加在占位符之后。
    list_errors.extend(
        f"render_agents: local reference leak {item}"
        for item in dict_parsed.get("local_reference_leaks", []) or []
    )

    # 保持稳定顺序供测试和机器消费方比较。
    return list_errors

# 源码治理输出包含四类需要扁平化的违规记录。
def source_governance_content_errors(dict_parsed: dict[str, Any]) -> list[str]:
    """把源码治理违规记录转换成稳定错误文本。

    Args:
        dict_parsed: source_governance 的结构化输出。

    Returns:
        文件尺寸、测试边界、注释和可读性错误。
    """

    # 文件尺寸错误首先报告，便于优先恢复治理入口。
    list_errors = [  # 源码治理内容错误
        f"source_governance: oversized file {item.get('path', '')}"  # 当前超限文件
        for item in dict_parsed.get("oversized_source_files", []) or []  # 超限文件记录
    ]

    # 测试专用代码越界属于目录职责错误。
    list_errors.extend(
        f"source_governance: test-only design code outside tests {item.get('path', '')}"
        for item in dict_parsed.get("test_code_boundary_violations", []) or []
    )

    # 注释策略错误保留文件和详细消息。
    list_errors.extend(
        f"source_governance: comment policy violation {item.get('path', '')}: {item.get('message', '')}"
        for item in dict_parsed.get("comment_policy_violations", []) or []
    )

    # 可读性错误最后追加，保持原评估输出顺序。
    list_errors.extend(
        f"source_governance: readability violation {item.get('path', '')}: {item.get('message', '')}"
        for item in dict_parsed.get("readability_violations", []) or []
    )

    # 调用方为每条消息保留 source_governance 前缀。
    return list_errors

# 命令专用内容检查与通用 errors 字段分开维护。
def command_content_errors(str_name: str, dict_parsed: dict[str, Any]) -> list[str]:
    """返回指定命令额外暴露的内容级错误。

    Args:
        str_name: 评估步骤名称。
        dict_parsed: 命令结构化输出。

    Returns:
        该命令通用 errors 字段之外的错误文本。
    """

    # 各命令只进入自身定义的内容检查器。
    dict_extractors = {  # 命令到内容检查器的映射
        "verify_agents": verify_agents_content_errors,  # AGENTS 扫描边界检查器
        "render_agents": render_content_errors,  # 渲染正文检查器
        "source_governance": source_governance_content_errors,  # 源码治理检查器
    }

    # 没有专用检查器的命令不产生额外内容错误。
    function_extractor = dict_extractors.get(str_name)  # 当前命令内容检查器

    # 可选调用边界避免为普通命令复制空分支。
    return function_extractor(dict_parsed) if function_extractor is not None else []

# 所有命令错误最终整理成向后兼容的字符串列表。
def collect_errors(commands: list[dict[str, Any]]) -> list[str]:
    """聚合命令退出、结构化和内容级错误。

    Args:
        commands: 按评估顺序排列的命令记录。

    Returns:
        带命令名称前缀的稳定错误文本。
    """

    # 聚合列表保持命令执行顺序。
    list_errors: list[str] = []  # 全部评估错误

    # 每条命令独立解析，避免一个坏载荷影响其他结果。
    for dict_entry in commands:

        # 命令名用于错误前缀和专用检查路由。
        str_name = str(dict_entry["name"])  # 当前评估步骤名称

        # 非映射 JSON 按没有结构化错误处理。
        dict_parsed: dict[str, Any] = (  # 规范化映射载荷
            dict_entry.get("json", {})  # 当前记录的结构化输出
            if isinstance(dict_entry.get("json"), dict)  # 映射载荷可直接使用
            else {}  # 非映射载荷规范为空映射
        )

        # 通用 errors 字段允许缺失或空值。
        list_structured_errors = dict_parsed.get("errors", []) or []  # 通用结构化错误

        # 无详细错误的非零退出需要生成兜底诊断。
        if dict_entry["returncode"] != 0 and not list_structured_errors:

            # 退出码诊断证明命令失败但没有结构化原因。
            list_errors.append(f"{str_name}: command exited with {dict_entry['returncode']}")

        # 通用 errors 字段直接保留命令来源。
        list_errors.extend(f"{str_name}: {item}" for item in list_structured_errors)

        # 命令专用内容错误已经包含稳定命令前缀。
        list_errors.extend(command_content_errors(str_name, dict_parsed))

    # 返回扁平列表以维持公开评估合同。
    return list_errors

# 命令类别根据目标是否为当前工具技能区分治理责任。
def error_category_for(command_name: str, *, self_skill: bool) -> str:
    """返回指定评估命令的错误责任类别。

    Args:
        command_name: 评估步骤名称。
        self_skill: 目标是否为 agents-md-generator 自身。

    Returns:
        ERROR_CATEGORY_NAMES 中的稳定分类名称。
    """

    # 文档和 AGENTS 验证失败归属于相应仓库治理。
    if command_name in {"manage_docs_verify", "verify_agents"}:

        # 自检与目标项目检查使用不同治理类别。
        return "self_repo_governance_error" if self_skill else "target_repo_governance_error"

    # 源码治理和技能专用验证反映目标行为合同。
    if command_name in {"source_governance", "validate_script"}:

        # 这两类错误始终指向被评估技能表面。
        return "target_repo_behavior_error"

    # 通用校验在自检时属于工具链，在外部评估时属于目标行为。
    if command_name in {"audit_skill", "compileall", "quick_validate"}:

        # self_skill 开关确定通用命令的责任归属。
        return "tooling_error" if self_skill else "target_repo_behavior_error"

    # 未登记命令保守归类为工具错误。
    return "tooling_error"

# 分类记录使用固定字段，供计数器和机器消费方复用。
def classified_error_entry(str_category: str, str_command: str, str_message: str) -> dict[str, str]:
    """构造单条结构化错误分类记录。

    Args:
        str_category: 错误责任类别。
        str_command: 产生错误的评估步骤。
        str_message: 去除命令前缀后的错误消息。

    Returns:
        category、command 和 message 映射。
    """

    # 字段形状保持与既有评估 JSON 合同一致。
    return {
        "category": str_category,
        "command": str_command,
        "message": str_message,
    }

# 内容检查消息已经含命令前缀，分类记录只保留正文。
def content_error_message(str_error: str) -> str:
    """移除内容错误中的命令名称前缀。

    Args:
        str_error: command_content_errors 返回的错误文本。

    Returns:
        首个冒号空格之后的消息正文。
    """

    # 缺少分隔符时保留原消息，避免意外丢失诊断。
    tuple_parts = str_error.partition(": ")  # 前缀、分隔符和消息正文

    # partition 第三分量为空表示输入没有标准前缀。
    return tuple_parts[2] if tuple_parts[1] else str_error

# 分类聚合与字符串错误聚合共享同一内容检查器。
def classified_errors(commands: list[dict[str, Any]], *, self_skill: bool) -> list[dict[str, str]]:
    """把命令错误转换成带责任类别的结构化记录。

    Args:
        commands: 按评估顺序排列的命令记录。
        self_skill: 目标是否为当前工具技能。

    Returns:
        保持命令和错误顺序的分类记录列表。
    """

    # 聚合列表供 category_counts 和最终 JSON 直接使用。
    list_classified: list[dict[str, str]] = []  # 全部结构化错误记录

    # 每条命令独立确定默认类别和内容类别。
    for dict_entry in commands:

        # 名称决定责任分类与专用内容检查器。
        str_name = str(dict_entry["name"])  # 分类阶段的命令名称

        # 默认类别由命令类型和自检状态共同确定。
        str_category = error_category_for(str_name, self_skill=self_skill)  # 当前命令责任类别

        # 非零退出始终保留一条结构化记录。
        if dict_entry["returncode"] != 0:

            # 退出码记录与详细结构化错误可以同时存在。
            list_classified.append(
                classified_error_entry(
                    str_category,
                    str_name,
                    f"command exited with {dict_entry['returncode']}",
                )
            )

        # 非映射 JSON 不包含可分类的详细错误。
        dict_parsed: dict[str, Any] = (  # 规范化命令 JSON
            dict_entry.get("json", {})  # 当前分类记录的 JSON 输出
            if isinstance(dict_entry.get("json"), dict)  # 分类载荷必须为映射
            else {}  # 非映射命令没有详细分类字段
        )

        # 通用 errors 字段沿用命令默认责任类别。
        list_classified.extend(
            classified_error_entry(str_category, str_name, str(item))
            for item in dict_parsed.get("errors", []) or []
        )

        # verify/render 的内容错误说明工具越界，其他内容沿用默认类别。
        str_content_category = (  # 专用内容错误类别
            "tooling_error"  # 扫描与渲染越界属于工具错误
            if str_name in {"verify_agents", "render_agents"}  # 两个工具边界命令
            else str_category  # 其他内容沿用命令责任类别
        )

        # 内容检查错误转换为不重复命令前缀的分类记录。
        list_classified.extend(
            classified_error_entry(
                str_content_category,
                str_name,
                content_error_message(str_error),
            )
            for str_error in command_content_errors(str_name, dict_parsed)
        )

    # 最终顺序与原命令执行链保持一致。
    return list_classified

# 分类计数始终包含全部稳定类别，即使某类没有错误。
def category_counts(classified: list[dict[str, str]]) -> dict[str, int]:
    """统计各错误责任类别的记录数量。

    Args:
        classified: classified_errors 生成的结构化记录。

    Returns:
        ERROR_CATEGORY_NAMES 中每个类别的计数。
    """

    # 零值初始化保证最终 JSON 形状稳定。
    dict_counts = {str_name: 0 for str_name in ERROR_CATEGORY_NAMES}  # 分类计数映射

    # 未知类别不进入受治理计数集合。
    for dict_item in classified:

        # 缺失类别按空字符串处理并自然忽略。
        str_category = dict_item.get("category", "")  # 当前错误类别

        # 只累加预先登记的稳定类别。
        if str_category in dict_counts:

            # 当前类别计数增加一次。
            dict_counts[str_category] += 1  # 更新对应类别数量

    # 完整计数映射直接写入评估结果。
    return dict_counts

# 仓库根发现优先选择包含 tests 的最近祖先。
def repo_root_for(skill_dir: Path) -> Path:
    """推断目标技能所属的可测试仓库根目录。

    Args:
        skill_dir: 待评估技能目录。

    Returns:
        最近的含 tests 目录祖先或稳定父目录回退。
    """

    # 候选覆盖标准 skills/name、直接子目录和仓库根技能布局。
    for path_candidate in [skill_dir.parent.parent, skill_dir.parent, skill_dir]:

        # tests 目录是当前仓库评估布局的根标记。
        if (path_candidate / "tests").is_dir():

            # 返回最近顺序中首个匹配根。
            return path_candidate

    # 非标准布局回退到两级父目录，根路径自身则保持不变。
    return skill_dir.parent.parent if skill_dir.parent != skill_dir else skill_dir

# compileall 使用内存载荷模拟普通子进程命令记录。
def compileall_entry(skill_dir: Path, repo_root: Path, env: dict[str, str]) -> dict[str, Any]:
    """编译目标技能的现有 Python 源码根并记录结果。

    Args:
        skill_dir: 待评估技能目录。
        repo_root: 命令记录使用的仓库工作目录。
        env: 与其他评估步骤一致的环境；compileall API 无需读取。

    Returns:
        command_entry 形状的 compileall 执行记录。
    """

    # 仅编译实际存在的标准 Python 根。
    list_roots = existing_python_roots(skill_dir)  # 待编译源码根名称

    # 失败消息按源码根顺序聚合。
    list_messages: list[str] = []  # 编译失败诊断

    # 初始成功状态会被任一失败根翻转。
    bool_ok = True  # 所有源码根是否编译成功

    # compileall API 避免为每个根启动额外解释器。
    for str_name in list_roots:

        # 目标路径相对于技能根解析。
        path_target = skill_dir / str_name  # 当前编译源码根

        # 安静模式仍返回布尔成功状态。
        if not compileall.compile_dir(str(path_target), quiet=1, force=False):

            # 任一失败使聚合命令返回非零状态。
            bool_ok = False  # 标记至少一个源码根编译失败

            # 根名称进入可操作的编译错误。
            list_messages.append(f"compileall failed for {str_name}")

    # 结构化输出与普通 run_command 记录保持一致。
    dict_payload = {  # compileall JSON 载荷
        "roots": list_roots,  # 已执行编译的源码根
        "errors": [] if bool_ok else list_messages,  # 聚合编译错误
    }

    # CompletedProcess 复用 command_entry 的标准序列化路径。
    completed_process_result = subprocess.CompletedProcess(  # 合成编译完成结果
        args=[sys.executable, "-m", "compileall", *list_roots],  # 合成命令参数
        returncode=0 if bool_ok else 1,  # 聚合编译退出码
        stdout=json.dumps(dict_payload),  # 结构化编译输出
        stderr="",  # compileall API 没有独立错误流
    )

    # env 参数用于保持统一签名，编译已在当前隔离进程执行。
    del env

    # 命令参数和载荷共同形成可分类记录。
    return command_entry(
        "compileall",
        [sys.executable, "-m", "compileall", *list_roots],
        repo_root,
        completed_process_result,
    )

# 环境构造隔离递归标记和自检源码覆盖。
def evaluation_environment(bool_self_skill: bool) -> dict[str, str]:
    """构造所有评估子进程共享的基础环境。

    Args:
        bool_self_skill: 目标是否为当前工具技能。

    Returns:
        带递归保护和可选源码覆盖的环境副本。
    """

    # 基础环境阻止评估器递归启动自身。
    dict_base_env = dict(  # 所有评估子进程的基础环境
        os.environ,  # 当前进程环境基线
        AGENTS_MD_EVALUATE_RUNNING="1",  # 阻止递归评估
    )

    # 自检必须将安装技能指向当前源码版本。
    if bool_self_skill:

        # 源码覆盖避免陈旧本地安装影响自检结论。
        dict_base_env["AGENTS_MD_INSTALLED_SKILL_DIR"] = str(TOOL_SKILL_DIR)  # 当前源码技能根

    # 非自检目标删除可能继承的安装技能覆盖。
    else:

        # 删除覆盖变量以恢复目标技能真实安装环境。
        dict_base_env.pop("AGENTS_MD_INSTALLED_SKILL_DIR", None)

    # 调用方将环境传给所有命令运行器。
    return dict_base_env

# 主评估器按固定顺序执行工具、行为和治理门禁。
def evaluate(skill_dir: Path, project: Path) -> dict[str, Any]:
    """运行目标技能的事实级验证链。

    Args:
        skill_dir: 待评估技能目录。
        project: AGENTS 与治理命令使用的项目根。

    Returns:
        命令证据、错误分类、计数和警告组成的评估结果。
    """

    # 子命令统一在包含测试的仓库根执行。
    path_repo_root = repo_root_for(skill_dir)  # 目标技能所属仓库根

    # 自评估需要启用安装技能覆盖和额外治理步骤。
    bool_self_skill = skill_dir.name == "agents-md-generator"  # 是否评估当前工具技能

    # 共享环境统一处理递归保护和源码覆盖。
    dict_base_env = evaluation_environment(bool_self_skill)  # 评估子进程基础环境

    # 命令证据按实际执行顺序保存。
    list_commands: list[dict[str, Any]] = []  # 已执行评估命令记录

    # 可选工具缺失只形成警告，不伪造命令失败。
    list_warnings: list[str] = []  # 非阻断评估警告

    # 运行门禁前移除旧缓存，避免扫描历史产物。
    cleanup_transient_artifacts(skill_dir)

    # 技能审计始终是验证链的首个工具门禁。
    list_commands.append(
        run_command(
            "audit_skill",  # 审计步骤名称
            [sys.executable, str(tool_script_path("audit_skill.py")), str(skill_dir)],  # 审计参数
            path_repo_root,  # 仓库工作目录
            dict_base_env,  # 评估基础环境
        )
    )

    # Python 根存在时追加真实编译门禁。
    list_python_roots = existing_python_roots(skill_dir)  # 当前技能 Python 源码根

    # 非 Python 技能跳过无意义的空 compileall 命令。
    if list_python_roots:

        # 编译记录进入统一命令证据列表。
        list_commands.append(compileall_entry(skill_dir, path_repo_root, dict_base_env))

        # compileall 生成的缓存必须立即清理。
        cleanup_transient_artifacts(skill_dir)

    # 快速校验器可能来自当前技能或系统 skill-creator。
    try:

        # 发现成功后在 else 分支执行，避免捕获运行错误。
        path_validator = quick_validate_script()  # 快速校验脚本路径

    # 候选全部缺失时转成可见但非阻断警告。
    except FileNotFoundError as exc:

        # 错误文本已经带 Python 治理前缀。
        list_warnings.append(str(exc))

    # 成功发现校验器后进入实际命令执行分支。
    else:

        # 参数显式传入目标技能目录。
        list_commands.append(
            run_command(
                "quick_validate",
                [sys.executable, str(path_validator), str(skill_dir)],
                path_repo_root,
                dict_base_env,
            )
        )

    # 技能专用验证入口在通用快速校验之后运行。
    path_validate_script = discover_validate_script(skill_dir)  # 专用验证脚本路径

    # 无唯一入口时不猜测执行任意 validate 脚本。
    if path_validate_script is not None:

        # 专用环境处理 erie-remote-ssh 的递归隔离特例。
        list_commands.append(
            run_command(
                "validate_script",  # 专用验证步骤名称
                [sys.executable, str(path_validate_script), *settings_arg(skill_dir)],  # 验证参数
                path_repo_root,  # 专用验证工作目录
                validate_script_env(dict_base_env, skill_dir),  # 技能专用环境
            )
        )

    # 文档治理只对具有受管控制文件的项目启用。
    path_manage_docs_script = tool_script_path("manage_docs.py")  # 文档治理脚本

    # 脚本和治理标记必须同时存在。
    if path_manage_docs_script.is_file() and (project / ".agents" / "agents-control.json").is_file():

        # verify 子命令检查文档生命周期和目录状态。
        list_commands.append(
            run_command(
                "manage_docs_verify",
                [sys.executable, str(path_manage_docs_script), "verify", str(project)],
                path_repo_root,
                dict_base_env,
            )
        )

    # AGENTS 验证要求目标项目已存在根规则文件。
    path_verify_agents_script = tool_script_path("verify_agents.py")  # AGENTS 验证脚本

    # 缺少 AGENTS.md 的非受管目标不运行该门禁。
    if path_verify_agents_script.is_file() and (project / "AGENTS.md").is_file():

        # 基础参数验证目标项目根。
        list_verify_argv = [  # AGENTS 验证命令参数
            sys.executable,  # AGENTS 验证使用的解释器
            str(path_verify_agents_script),  # 规则验证入口脚本
            str(project),  # 待验证项目根
        ]

        # 自检显式使用当前源码技能作为安装对照。
        if bool_self_skill:

            # 覆盖参数防止读取陈旧本地安装副本。
            list_verify_argv.extend(["--installed-skill-dir", str(skill_dir)])

        # 完整 AGENTS 验证记录进入评估证据。
        list_commands.append(run_command("verify_agents", list_verify_argv, path_repo_root, dict_base_env))

    # 源码治理需要项目配置，自检则始终启用。
    path_source_governance_script = tool_script_path("check_source_governance.py")  # 源码治理脚本

    # 配置存在或目标为工具自身时执行源码治理。
    if path_source_governance_script.is_file() and (
        (project / ".agents" / "global-rule-overrides.json").is_file() or bool_self_skill
    ):

        # 源码治理扫描目标项目并返回结构化违规。
        list_commands.append(
            run_command(
                "source_governance",
                [sys.executable, str(path_source_governance_script), str(project)],
                path_repo_root,
                dict_base_env,
            )
        )

    # 只有当前工具技能能够执行受信任的 AGENTS 渲染自检。
    if bool_self_skill:

        # 渲染内容检查补充占位符和本地路径泄露证据。
        list_commands.append(render_entry(project, dict_base_env))

    # 所有命令完成后再次清理缓存，保证工作树无瞬态污染。
    cleanup_transient_artifacts(skill_dir)

    # 字符串错误维持既有公开输出合同。
    list_errors = collect_errors(list_commands)  # 扁平评估错误

    # 结构化错误为每条诊断补充责任类别。
    list_structured_errors = classified_errors(  # 分类评估错误
        list_commands,  # 已完成的全部命令记录
        self_skill=bool_self_skill,  # 当前目标的自检状态
    )

    # 汇总结果保留所有命令证据和非阻断警告。
    return {
        "ok": not list_errors,  # 没有阻断错误时评估成功
        "skill_dir": str(skill_dir),  # 被评估技能目录
        "project": str(project),  # 被评估项目根
        "commands": list_commands,  # 完整命令证据
        "errors": list_errors,  # 向后兼容错误文本
        "classified_errors": list_structured_errors,  # 责任分类记录
        "category_counts": category_counts(list_structured_errors),  # 分类计数
        "warnings": list_warnings,  # 非阻断工具警告
    }

# 命令行入口解析目标路径并输出机器可读评估结果。
def main() -> int:
    """运行 evaluate_skill 命令行入口。

    Args:
        None: 参数从当前命令行读取。

    Returns:
        评估成功返回 0，否则返回 1。
    """

    # 参数解析器允许省略技能和项目路径。
    argument_parser = argparse.ArgumentParser(  # 命令行参数解析器
        description="Run the fact-level validation chain for a target skill."  # 命令说明
    )

    # 技能目录默认使用当前工作目录。
    argument_parser.add_argument("skill_dir", nargs="?", default=".")

    # 项目根省略时由技能目录自动推断。
    argument_parser.add_argument("project", nargs="?", default=None)

    # 解析后的命名空间只在入口函数内使用。
    namespace_args: argparse.Namespace = argument_parser.parse_args()  # 命令行参数命名空间

    # 技能参数解析为绝对规范路径。
    path_skill_directory = resolve_project(namespace_args.skill_dir)  # CLI 解析后的技能根

    # 项目参数存在时覆盖仓库根自动发现。
    path_project = (  # CLI 选择的项目根
        resolve_project(namespace_args.project)  # 显式项目参数
        if namespace_args.project  # 用户显式提供项目路径
        else repo_root_for(path_skill_directory)  # 从技能目录推断仓库根
    )

    # 主评估器返回可直接序列化的载荷。
    dict_evaluation_result = evaluate(path_skill_directory, path_project)  # 最终评估结果

    # 标准 JSON 输出供测试、CI 和上层门禁消费。
    emit_json(dict_evaluation_result)

    # 退出码与结果中的 ok 字段保持一致。
    return 0 if dict_evaluation_result["ok"] else 1

# 直接执行脚本时把入口返回值转换成进程退出码。
if __name__ == "__main__":

    # SystemExit 保留命令行工具的标准退出语义。
    raise SystemExit(main())
