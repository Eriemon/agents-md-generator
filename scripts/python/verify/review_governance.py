"""审查变更范围是否满足测试、文档、评测和发布治理契约。"""

# 延迟注解求值避免运行时解析仅用于类型检查的结构。
from __future__ import annotations

# 导入治理审查所需的标准库模块。
import argparse
import hashlib
import importlib
import json
import subprocess
import sys

# 时间与路径类型用于生成审查证据并定位项目资源。
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

# CLI 审查不得在被审查源码树内产生缓存文件。
sys.dont_write_bytecode = True  # 禁止生成 Python 字节码缓存

# 当前入口目录用于报告脚本自身位置。
SCRIPT_DIR = Path(__file__).resolve().parent  # 治理审查脚本目录

# 默认技能目录对应当前脚本向上三级的技能包根目录。
DEFAULT_SKILL_DIR = Path(__file__).resolve().parents[3]  # 默认被审查技能目录

# 门禁入口集合决定哪些变更需要同步审查清单和评测资料。
GATE_SCRIPT_NAMES = {  # 影响治理语义的门禁脚本名
    "check_source_governance.py",  # 源码治理检查入口
    "check_freshness.py",  # 生成内容新鲜度门禁
    "collect_design_profile.py",  # 设计档案收集门禁
    "design_questions.py",  # 设计问题合同入口
    "design_review_gate.py",  # 设计审查门禁
    "design_interview_state.py",  # 设计访谈状态入口
    "design_profile_builder.py",  # 设计档案构建入口
    "source_governance.py",  # 源码治理规则入口
    "source_governance_config.py",  # 源码治理配置入口
    "render_agents.py",  # AGENTS 渲染入口
    "manage_dirs.py",  # 目录治理入口
    "manage_docs.py",  # 文档治理入口
    "manage_docs_release.py",  # 发布文档治理入口
    "manage_docs_sync_verify.py",  # 文档同步验证入口
    "review_governance.py",  # 变更审查治理入口
    "run_confidence_gate.py",  # 事实置信度门禁
    "verify_agents.py",  # AGENTS 合同验证入口
}

# 安装入口与门禁入口共同构成需要维护脚本指南的 CLI 集合。
CLI_SCRIPT_NAMES = GATE_SCRIPT_NAMES | {"install_skill.py"}  # 对外 CLI 脚本名

# 运行时路由集合标识需要评测执行链覆盖的核心脚本。
RUNTIME_ROUTING_SCRIPT_NAMES = {  # 影响运行时任务路由的脚本名
    "agents_common.py",  # 公共运行时路由入口
    "agents_project_facts.py",  # 项目事实路由入口
    "design_takeover.py",  # 设计接管路由入口
    "manage_dirs.py",  # 目录治理路由入口
    "manage_docs_scaffold_session.py",  # 会话脚手架路由入口
    "manage_docs_shared.py",  # 文档共享合同入口
    "manage_docs_sync_verify.py",  # 文档同步路由入口
    "render_agents.py",  # AGENTS 渲染路由入口
    "verify_agents.py",  # AGENTS 验证路由入口
}

# 公共模块按需加载，避免导入审查模块时修改全局搜索路径。
def load_agents_common() -> ModuleType:
    """按需加载跨任务目录共享的 ``agents_common`` 模块。

    参数：无。
    返回：已加载的公共模块。
    """

    # 所有分类脚本目录均位于同一个 Python 根目录下。
    path_python_root = Path(__file__).resolve().parents[1]  # Python 任务目录共同根

    # 逐个登记现有分类目录，保持直接脚本执行兼容性。
    for path_task_directory in path_python_root.iterdir():

        # 普通文件不具备模块搜索目录语义。
        if not path_task_directory.is_dir():

            # 继续寻找其余可用的分类目录。
            continue

        # sys.path 只接受字符串形式的目录位置。
        str_task_directory = str(path_task_directory)  # Python 导入搜索路径

        # 已登记目录保持原有优先级，避免重复插入。
        if str_task_directory not in sys.path:

            # 源码目录优先于环境内可能存在的同名安装模块。
            sys.path.insert(0, str_task_directory)

    # 公共模块在路径准备完成后才执行导入。
    return importlib.import_module("agents_common")

# 路径解析包装器维持原有模块级调用合同。
def resolve_project(path_value: str | Path) -> Path:
    """将输入路径解析为受治理的项目根目录。

    参数：
        path_value: CLI 或调用方提供的项目路径。
    返回：规范化后的项目根目录。
    """

    # 委托公共模块执行路径规范化和项目边界验证。
    return load_agents_common().resolve_project(path_value)

# JSON 输出包装器维持所有治理 CLI 的统一机器接口。
def emit_json(dict_payload: dict[str, Any]) -> None:
    """按公共 CLI 契约输出 JSON 结果。

    参数：
        dict_payload: 待输出的结构化结果。
    返回：无。
    """

    # 公共输出器负责稳定编码和标准输出格式。
    load_agents_common().emit_json(dict_payload)

# Git 包装器统一只读命令的工作目录和标准流捕获策略。
def run_git(project: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """在项目根目录执行只读 Git 命令并捕获结果。

    参数：
        project: Git 项目根目录。
        args: 不含 ``git`` 前缀的参数列表。
    返回：包含退出码和标准流的完成结果。
    """

    # 非抛异常模式让调用方能够生成结构化失败诊断。
    return subprocess.run(
        ["git", *args],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )

# 变更收集器把 Git 输出转换为后续规则统一使用的路径集合。
def changed_files(project: Path, base: str, head: str) -> list[str]:
    """返回两个 Git 修订之间发生变化的规范化文件路径。

    参数：
        project: Git 项目根目录。
        base: 对比基线修订。
        head: 对比目标修订。
    返回：排序后的 POSIX 风格相对路径。
    异常：Git 对比失败时抛出 ``SystemExit`` 并携带 JSON 诊断。
    """

    # Git 完成结果保留退出码和双标准流，便于结构化失败处理。
    completed_process_result = run_git(  # 修订范围文件差异结果
        project,  # Git 命令工作目录
        ["diff", "--name-only", base, head],  # 仅收集修订间文件名
    )

    # 非零退出码表示修订无效或项目状态无法读取。
    if completed_process_result.returncode != 0:

        # git diff 失败时优先保留 stderr，缺失时再使用 stdout。
        str_diff_output: str = (  # Git 原始失败诊断
            completed_process_result.stderr.strip()  # 首选标准错误诊断
            or completed_process_result.stdout.strip()  # 标准错误为空时使用标准输出
        )

        # 没有任何输出时补充固定文本，保证 JSON errors 非空。
        str_diff_error: str = str_diff_output or "git diff failed"  # 保底失败诊断文本

        # 失败诊断保持 CLI 既有 JSON 结构并立即终止审查。
        raise SystemExit(json.dumps({"ok": False, "errors": [str_diff_error]}, indent=2))

    # 排序和斜杠规范化确保跨平台审查结果稳定。
    return sorted(
        line.strip().replace("\\", "/")
        for line in completed_process_result.stdout.splitlines()
        if line.strip()
    )

# 文件名语义复核只覆盖功能源码和 Python 测试，不要求初始化文件摘要。
def semantic_review_paths(changes: list[str]) -> list[str]:
    """返回需要 Agent 判断文件名是否总结功能的变更路径。

    参数：
        changes: Git 对比得到的仓库相对路径。
    返回：需要语义复核的功能源码与 Python 测试路径。
    """

    # 集合查询用于快速判断变更文件是否属于受支持源码类型。
    set_source_extensions = set(  # 文件名功能摘要人工复核使用的源码后缀白名单
        (
            ".py .js .jsx .ts .tsx "  # 覆盖解释器与浏览器执行的功能实现
            ".java .kt .kts .go .rs "  # 覆盖虚拟机和静态编译的后端实现
            ".php .rb .cs .swift "  # 覆盖服务端脚本与移动应用实现
            ".m .mm .c .cc .cpp .cxx "  # 覆盖本地工具链编译的功能实现
            ".h .hh .hpp "  # 覆盖本地编译单元公开的接口契约
            ".css .scss .sass .less .html"  # 覆盖页面结构和视觉行为实现
        ).split()  # 把分组文本转换为精确后缀成员
    )  # 与 tests Python 规则共同限定必须提交功能摘要的源码类型

    # 排序结果使同一变更集合生成稳定的语义证据哈希。
    return sorted(
        str_path
        for str_path in changes
        if Path(str_path).name != "__init__.py"
        and (
            (
                str_path.startswith("tests/")
                and Path(str_path).suffix.lower() == ".py"
            )
            or (
                str_path.startswith(("skills/", "engineering/"))
                and Path(str_path).suffix.lower() in set_source_extensions
            )
        )
    )

# 修订解析器把 HEAD 等别名固定为证据可绑定的提交标识。
def resolve_revision(project: Path, revision: str) -> str:
    """返回 Git 修订对应的完整提交哈希。

    参数：
        project: Git 仓库根目录。
        revision: 需要解析的修订表达式。
    返回：解析成功时为完整提交哈希，失败时为空字符串。
    """

    # Git 解析结果同时保留退出码和标准输出，供失败分支判断。
    completed_process_revision = run_git(project, ["rev-parse", revision])  # 修订解析进程结果

    # 无效修订不能绑定语义证据，因此返回空标识。
    if completed_process_revision.returncode != 0:

        # 空字符串让调用方按证据失配处理，而不是采用不确定值。
        return ""

    # 成功结果去除行尾空白后作为证据中的规范提交标识。
    return completed_process_revision.stdout.strip()

# 语义证据内容检查器验证修订绑定和逐文件裁决。
def validate_semantic_evidence_content(
    project: Path,
    base: str,
    head: str,
    list_required_paths: list[str],
    dict_evidence: dict[str, Any],
    dict_result: dict[str, Any],
) -> dict[str, Any]:
    """验证已解析语义证据的新鲜度、摘要和裁决。

    参数：
        project: Git 仓库根目录。
        base: 对比基线修订。
        head: 对比目标修订。
        list_required_paths: 本次必须复核的功能文件路径。
        dict_evidence: 已成功解析的证据载荷。
        dict_result: 等待补充诊断的基础结果。
    返回：包含覆盖路径和稳定失败代码的语义复核结果。
    """

    # 路径列表哈希把证据绑定到确定的变更文件集合。
    str_expected_hash = hashlib.sha256(  # 当前语义复核路径集合的绑定哈希
        "\n".join(list_required_paths).encode("utf-8")  # 规范排序后的路径字节串
    ).hexdigest()  # 当前变更路径集合的预期哈希

    # 新鲜度错误集中收集，确保一次返回全部修订绑定问题。
    list_stale_errors: list[str] = []  # 修订或路径哈希失配诊断

    # 基线修订必须与证据记录的完整提交哈希一致。
    if dict_evidence.get("base") != resolve_revision(project, base):

        # 登记基线不一致，提示重新生成 revision-bound 证据。
        list_stale_errors.append("semantic review base revision does not match")

    # 目标修订必须与证据记录的完整提交哈希一致。
    if dict_evidence.get("head") != resolve_revision(project, head):

        # 登记目标修订不一致，阻止复用旧提交的审查结果。
        list_stale_errors.append("semantic review head revision does not match")

    # 路径哈希必须覆盖当前全部功能源码变更。
    if dict_evidence.get("changed_path_hash") != str_expected_hash:

        # 路径集合变化后要求重新逐文件复核。
        list_stale_errors.append("semantic review changed path hash does not match")

    # 任一新鲜度错误都会使整份证据失效。
    if list_stale_errors:

        # 返回全部失配原因，减少逐次修复的信息往返。
        dict_result["errors"] = list_stale_errors  # 修订绑定错误列表

        # 标记证据不再对应当前审查快照。
        dict_result["ok"] = False  # 证据新鲜度未通过

        # 稳定代码允许上层门禁区分 stale 与 missing。
        dict_result["failure_code"] = "file-name-semantic-review-stale"  # 修订或路径绑定失效代码

        # 新鲜度失败后不再信任条目级裁决。
        return dict_result

    # 条目数组承载每个文件的功能摘要与 pass 裁决。
    list_entries = dict_evidence.get("entries", [])  # 原始逐文件复核条目

    # 非数组 entries 不能提供可靠的逐文件覆盖关系。
    if not isinstance(list_entries, list):

        # 归一为空数组，让后续覆盖检查输出确定性缺失诊断。
        list_entries = []  # 无效条目结构的安全替代值

    # 以路径建立索引，保证每个目标文件只读取对应摘要与裁决。
    dict_entries = {
        str(item.get("path", "")): item  # 证据条目按仓库相对路径索引
        for item in list_entries  # 逐项读取证据中的文件摘要记录
        if isinstance(item, dict) and str(item.get("path", ""))  # 排除无效条目
    }  # 可参与覆盖校验的有效证据条目

    # 输出实际覆盖路径，便于审查者核对遗漏与多余项。
    dict_result["reviewed_paths"] = sorted(dict_entries)  # 证据已复核路径

    # 条目级错误集中记录缺少摘要、失败裁决和未解决发现。
    list_failed_errors: list[str] = []  # 语义复核内容错误

    # 每个必需路径都必须拥有具体功能摘要和通过裁决。
    for str_path in list_required_paths:

        # 当前路径缺少条目时使用空字典触发两类明确诊断。
        dict_entry = dict_entries.get(str_path, {})  # 当前文件的语义复核条目

        # 空白摘要不能证明文件名概括了真实功能。
        if not str(dict_entry.get("functional_summary", "")).strip():

            # 指明缺失摘要的路径，便于审查者逐项补充。
            list_failed_errors.append(f"missing functional summary for {str_path}")

        # 只有明确的 pass 裁决才允许文件名通过发布门禁。
        if dict_entry.get("verdict") != "pass":

            # 非 pass 或缺失裁决均保留对应文件路径。
            list_failed_errors.append(f"semantic review did not pass for {str_path}")

    # 任一未解决项或无效结构都会使语义复核失败。
    list_unresolved = dict_evidence.get("unresolved_findings", [])  # 尚未关闭的人工发现

    # 顶层未解决发现必须是空数组，禁止用错误类型绕过阻断。
    if not isinstance(list_unresolved, list) or list_unresolved:

        # 汇总顶层未关闭状态，要求审查者先完成裁决。
        list_failed_errors.append("semantic review has unresolved findings")

    # 内容错误存在时写入稳定失败代码并保持全部诊断。
    if list_failed_errors:

        # 返回全部逐文件问题，支持一次完成修复。
        dict_result["errors"] = list_failed_errors  # 语义复核失败诊断

        # 标记功能摘要或裁决合同未完全满足。
        dict_result["ok"] = False  # 语义内容审查未通过

        # 内容失败与证据缺失、新鲜度失败使用不同稳定代码。
        dict_result["failure_code"] = "file-name-semantic-review-failed"  # 内容失败代码

    # 返回经过修订绑定和逐文件覆盖检查的最终诊断。
    return dict_result

# 语义证据校验提交、新鲜路径哈希、覆盖率、摘要和裁决。
def validate_semantic_review(
    project: Path,
    base: str,
    head: str,
    changes: list[str],
    semantic_review_path: Path | None,
) -> dict[str, Any]:
    """验证 Agent 文件名功能摘要证据并返回稳定诊断。

    参数：
        project: Git 仓库根目录。
        base: 对比基线修订。
        head: 对比目标修订。
        changes: 两个修订之间的仓库相对变更路径。
        semantic_review_path: Agent 语义复核证据文件路径。
    返回：覆盖路径、证据状态与稳定失败代码组成的诊断字典。
    """

    # 语义复核只覆盖本次修订中具有功能含义的源码和测试文件。
    list_required_paths = semantic_review_paths(changes)  # 必须获得功能摘要的变更路径

    # 初始结果采用通过状态，后续任一证据缺口都会显式翻转。
    dict_result: dict[str, Any] = {
        "required_paths": list_required_paths,  # 本次必须复核的路径
        "reviewed_paths": [],  # 证据实际覆盖的路径
        "evidence_path": "",  # 仓库内可追踪的证据位置
        "errors": [],  # 语义证据校验错误
        "ok": True,  # 当前证据是否满足全部合同
    }  # 语义复核诊断结果

    # 没有功能源码变更时无需强制提供空语义证据。
    if not list_required_paths:

        # 直接返回稳定的空覆盖通过结果。
        return dict_result

    # 存在复核对象时必须提供真实且可读取的证据文件。
    if semantic_review_path is None or not semantic_review_path.is_file():

        # 缺失证据记录为可由上层稳定识别的阻断原因。
        dict_result["errors"] = ["semantic review evidence is required"]  # 缺失证据诊断

        # 阻止缺少人工判断的变更进入发布链。
        dict_result["ok"] = False  # 证据合同未满足

        # 失败代码区分缺失证据与证据内容失效。
        dict_result["failure_code"] = "file-name-semantic-review-missing"  # 缺失证据代码

        # 返回完整诊断供审查 CLI 聚合。
        return dict_result

    # 优先记录仓库相对路径，避免证据输出泄露本机绝对路径。
    dict_result["evidence_path"] = (
        semantic_review_path.relative_to(project).as_posix()  # 仓库内证据使用相对路径
        if semantic_review_path.is_relative_to(project)  # 判断证据是否属于当前仓库
        else semantic_review_path.as_posix()  # 外部证据保留规范化路径用于诊断
    )  # 实际参与校验的证据路径

    # JSON 解析异常统一转换为证据过期或损坏诊断。
    try:

        # 一次性读取并解析证据，避免多次读取期间内容漂移。
        dict_evidence = json.loads(semantic_review_path.read_text(encoding="utf-8"))  # 语义证据载荷

    # 文件读取失败和 JSON 语法错误都表示证据不可采信。
    except (OSError, json.JSONDecodeError) as obj_error:

        # 原始异常文本保留在诊断中，便于定位损坏原因。
        dict_result["errors"] = [f"semantic review evidence is invalid: {obj_error}"]  # 无效证据诊断

        # 无法解析的证据不能支持通过裁决。
        dict_result["ok"] = False  # 证据解析失败

        # 损坏证据与修订失配共同归入 stale 类别。
        dict_result["failure_code"] = "file-name-semantic-review-stale"  # 失效证据代码

        # 立即返回，避免继续使用不可信的载荷。
        return dict_result

    # 已解析证据交由单一职责检查器验证修订绑定与逐文件内容。
    return validate_semantic_evidence_content(
        project, base, head, list_required_paths, dict_evidence, dict_result
    )

# 发现构造器集中维护机器输出字段及路径排序契约。
def finding(code: str, message: str, paths: list[str], severity: str = "error") -> dict[str, Any]:
    """构造稳定排序的治理发现记录。

    参数：
        code: 机器可读发现代码。
        message: 面向使用者的诊断消息。
        paths: 触发发现的相对路径。
        severity: 发现严重级别。
    返回：可序列化的发现字典。
    """

    # 固定字段顺序便于人工阅读，路径排序保证结果可复现。
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "paths": sorted(paths),
    }

# 调度策略函数将发布模式的人工复核要求显式化。
def review_dispatch_policy(mode: str, changes: list[str]) -> str:
    """根据审查模式和变更状态选择人工审查策略。

    参数：
        mode: 当前审查模式。
        changes: 本次对比得到的文件路径。
    返回：稳定的人工审查调度策略标识。
    """

    # 无变更时不产生无效审查任务。
    if not changes:

        # 明确返回空调度策略。
        return "none"

    # 发布审查必须进入人工复核链。
    if mode == "release":

        # 发布模式使用强制复核策略标识。
        return "required_for_release"

    # 非发布变更保留可选人工复核能力。
    return "optional"

# 路径筛选器为各治理规则提供稳定的作用域查询。
def changed_under(changes: set[str], prefix: str) -> list[str]:
    """筛选指定路径前缀下的变更。

    参数：
        changes: 去重后的变更路径。
        prefix: 目标路径前缀。
    返回：排序后的匹配路径。
    """

    # 字典序输出消除集合遍历顺序差异。
    return sorted(path for path in changes if path.startswith(prefix))

# 文件名提取器隔离不同平台路径输入的解析细节。
def script_name(path: str) -> str:
    """提取脚本路径的文件名。

    参数：
        path: 脚本相对路径。
    返回：路径末尾的文件名。
    """

    # Path 解析同时兼容仓库内相对路径和调用方绝对路径。
    return Path(path).name

# 规则聚合器依据同一变更快照生成全部确定性发现。
def build_findings(changes: list[str], skill_dir_rel: str) -> list[dict[str, Any]]:
    """根据变更集合生成确定性的治理发现。

    参数：
        changes: 本次审查的变更路径。
        skill_dir_rel: 技能目录相对项目根的 POSIX 路径。
    返回：按规则执行顺序生成的发现列表。
    """

    # 集合形式支持后续精确成员检查和路径差集计算。
    set_changed = set(changes)  # 去重后的变更路径

    # 脚本前缀限定生产 Python 入口的治理范围。
    script_prefix = f"{skill_dir_rel.rstrip('/')}/scripts/"  # 技能脚本目录前缀

    # 参考资料前缀用于检查 CLI 和门禁文档同步情况。
    reference_prefix = f"{skill_dir_rel.rstrip('/')}/references/"  # 技能参考资料前缀

    # 评测配置是运行时路由和门禁语义变更的覆盖证据之一。
    str_evals_json: str = f"{skill_dir_rel.rstrip('/')}/evals/evals.json"  # 技能评测配置路径

    # 版本文件变更会触发发布文档同步规则。
    version_file = f"{skill_dir_rel.rstrip('/')}/VERSION"  # 技能版本文件路径

    # Python 脚本变更是测试、文档和评测规则的共同输入。
    list_script_changes = [  # 生产 Python 脚本变更路径
        path  # 当前生产脚本路径
        for path in changed_under(set_changed, script_prefix)  # 遍历技能脚本变更
        if path.endswith(".py")  # 仅纳入 Python 生产脚本
    ]

    # 门禁脚本变更需要同步审查清单和评测场景。
    list_gate_changes: list[str] = [  # 门禁脚本变更路径
        path  # 当前门禁脚本路径
        for path in list_script_changes  # 从生产脚本中筛选 CLI 入口
        if script_name(path) in GATE_SCRIPT_NAMES  # 保留门禁入口
    ]

    # 对外 CLI 变更需要同步脚本使用指南。
    list_cli_changes: list[str] = [  # CLI 脚本变更路径
        path  # 当前 CLI 脚本路径
        for path in list_script_changes  # 从生产脚本中筛选运行时路由
        if script_name(path) in CLI_SCRIPT_NAMES  # 保留对外 CLI 入口
    ]

    # 核心路由变更必须由运行态评测覆盖。
    list_runtime_routing_changes: list[str] = [  # 运行时路由脚本变更路径
        path  # 当前运行时路由脚本路径
        for path in list_script_changes  # 遍历生产脚本变更
        if script_name(path) in RUNTIME_ROUTING_SCRIPT_NAMES  # 保留运行时路由入口
    ]

    # 测试变更为生产脚本修改提供同一审查跨度内的回归证据。
    list_test_changes = [  # Python 测试变更路径
        path  # 当前测试脚本路径
        for path in set_changed  # 遍历全部变更路径
        if path.startswith("tests/") and path.endswith(".py")  # 保留 Python 测试
    ]

    # 发现列表按规则顺序累积，确保 JSON 输出稳定。
    list_findings: list[dict[str, Any]] = []  # 确定性治理发现

    # 生产脚本有变化但测试未变化时提示覆盖缺口。
    if list_script_changes and not list_test_changes:

        # 记录脚本变更缺少测试证据的治理发现。
        list_findings.append(
            finding(
                "script-change-without-tests",
                "Script changes require tests/*.py coverage in the same review span.",
                list_script_changes,
            )
        )

    # CLI 变更必须与使用指南在同一审查跨度内更新。
    if list_cli_changes and f"{reference_prefix}script-guide.md" not in set_changed:

        # 记录 CLI 文档未同步的治理发现。
        list_findings.append(
            finding(
                "cli-change-without-script-guide",
                "CLI or gate script changes require script-guide.md documentation in the same review span.",
                list_cli_changes,
            )
        )

    # 门禁变更必须同步人工审查清单。
    if list_gate_changes and f"{reference_prefix}review-checklist.md" not in set_changed:

        # 记录门禁审查清单未同步的治理发现。
        list_findings.append(
            finding(
                "gate-change-without-review-checklist",
                "Gate behavior changes require review-checklist.md coverage in the same review span.",
                list_gate_changes,
            )
        )

    # 门禁语义变更至少需要评测配置或评测场景文档覆盖。
    if (
        list_gate_changes
        and str_evals_json not in set_changed
        and f"{reference_prefix}evaluation-scenarios.md" not in set_changed
    ):

        # 记录门禁评测资料未同步的治理发现。
        list_findings.append(
            finding(
                "gate-change-without-evals",
                "Gate behavior changes require eval or evaluation-scenarios coverage in the same review span.",
                list_gate_changes,
            )
        )

    # 运行时路由变化需要评测配置或执行器覆盖。
    if (
        list_runtime_routing_changes
        and str_evals_json not in set_changed
        and "tests/evaluation/run_skill_evals.py" not in set_changed
    ):

        # 记录运行态评测执行链未同步的治理发现。
        list_findings.append(
            finding(
                "runtime-routing-change-without-eval-harness",
                (
                    "Governance runtime routing changes require eval coverage "
                    "in evals/evals.json or tests/evaluation/run_skill_evals.py."
                ),
                list_runtime_routing_changes,
            )
        )

    # 版本变更需要三份发布治理文档同步更新。
    if version_file in set_changed:

        # 权威发布文档集合用于计算缺失项。
        set_required_docs = {  # 版本变更要求同步的发布文档
            "docs/development/DEVELOPMENT.md",  # 开发与版本状态说明
            "docs/git_manager/CHANGELOG.md",  # 面向版本的变更记录
            "docs/git_manager/GIT_MANAGER.md",  # Git 发布操作合同
        }

        # 差集结果直接作为发现路径的一部分输出。
        list_missing = sorted(set_required_docs - set_changed)  # 缺失的发布文档路径

        # 仅在确有缺失文档时产生版本治理发现。
        if list_missing:

            # 记录版本文件与缺失发布文档的联合证据。
            list_findings.append(
                finding(
                    "version-change-without-release-docs",
                    "VERSION changes require DEVELOPMENT, CHANGELOG, and GIT_MANAGER current-version updates.",
                    [version_file, *list_missing],
                )
            )

    # 返回完整且确定排序的治理发现序列。
    return list_findings

# 审查请求构造器汇总确定性结果和人工复核焦点。
def review_request(
    project: Path,
    base: str,
    head: str,
    changes: list[str],
    findings: list[dict[str, Any]],
    mode: str,
) -> dict[str, Any]:
    """构造可交给人工或自动审查器的请求载荷。

    参数：
        project: 项目根目录。
        base: 对比基线修订。
        head: 对比目标修订。
        changes: 规范化后的变更路径。
        findings: 确定性治理发现。
        mode: 当前审查模式。
    返回：完整审查请求字典。
    """

    # 调度策略同时驱动策略字段和人工复核布尔值。
    str_dispatch = review_dispatch_policy(mode, changes)  # 人工审查调度策略

    # 请求载荷保留输入修订与确定性发现，供后续审查器消费。
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "base": base,
        "head": head,
        "mode": mode,
        "changed_files": changes,
        "deterministic_findings": findings,
        "review_dispatch_policy": str_dispatch,
        "required_manual_review": str_dispatch == "required_for_release",
        "review_focus": [
            "Confirm the deterministic findings are resolved or intentionally accepted.",
            "Review design consistency for gate semantics, user confirmation wording, and release/install safety.",
            "Review code quality for small focused helpers, stable JSON output, and backwards-compatible fields.",
        ],
    }

# 审查编排器连接变更发现、规则评估和可选请求持久化。
def review_governance(
    project: Path, base: str, head: str,
    skill_dir: Path, mode: str,
    write_request: bool = False,
    semantic_review_path: Path | None = None,
) -> dict[str, Any]:
    """执行变更治理审查并按需写入审查请求文件。

    参数：
        project: Git 项目根目录。
        base: 对比基线修订。
        head: 对比目标修订。
        skill_dir: 被审查技能目录。
        mode: 当前审查模式。
        write_request: 是否写入 ``.agents/review-request.json``。
        semantic_review_path: revision-bound 文件名语义复核证据路径。
    返回：包含发现、调度策略和请求载荷的审查结果。
    """

    # 修订间变更路径是全部治理规则的权威输入。
    list_changes = changed_files(project, base, head)  # 规范化变更路径

    # 项目内技能使用相对路径，外部技能保留规范绝对路径。
    str_skill_dir_rel: str = (  # 规则使用的技能目录路径
        skill_dir.relative_to(project).as_posix()  # 项目内技能相对路径
        if skill_dir.is_relative_to(project)  # 判断技能是否位于项目内
        else skill_dir.as_posix()  # 外部技能使用规范绝对路径
    )

    # 确定性规则只读取同一份变更快照。
    list_findings = build_findings(list_changes, str_skill_dir_rel)  # 治理发现列表

    # Agent 语义证据补足确定性正则无法判断的“文件名是否总结功能”。
    dict_semantic_review = validate_semantic_review(  # 文件名功能语义复核诊断
        project,  # 当前 Git 仓库根目录
        base,  # 证据绑定的基线修订
        head,  # 证据绑定的目标修订
        list_changes,  # 本次修订差异中的文件路径
        semantic_review_path,  # Agent 逐文件功能摘要证据
    )

    # 语义证据失败时把稳定代码并入确定性治理发现。
    if not dict_semantic_review["ok"]:

        # 复用统一发现结构，保持聚合输出和退出码语义一致。
        list_findings.append(
            finding(
                str(dict_semantic_review["failure_code"]),
                "; ".join(dict_semantic_review["errors"]),
                list(dict_semantic_review["required_paths"]),
            )
        )

    # 当前审查模式的策略用于最终结果声明人工复核要求。
    str_dispatch = review_dispatch_policy(mode, list_changes)  # 最终结果采用的复核策略

    # 请求载荷为可选落盘和结果内嵌共用同一结构。
    dict_request = review_request(  # 完整审查请求载荷
        project,  # 审查项目根目录
        base,  # 对比基线修订
        head,  # 对比目标修订
        list_changes,  # 请求内嵌的文件变更快照
        list_findings,  # 请求内嵌的规则诊断快照
        mode,  # 当前审查模式
    )

    # 定位 request path 的文件边界，供 review_governance 后续读写校验使用。
    str_request_path = ""  # 未写入请求时保持空路径

    # 调用方明确要求时才修改项目内的请求证据文件。
    if write_request:

        # 请求文件固定写入项目治理状态目录。
        path_target = project / ".agents" / "review-request.json"  # 审查请求目标文件

        # 确保首次启用请求写入时治理状态目录存在。
        path_target.parent.mkdir(parents=True, exist_ok=True)

        # 稳定缩进和键排序便于审查请求进入版本差异检查。
        path_target.write_text(
            json.dumps(dict_request, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        # 结果只暴露项目相对路径，避免机器相关绝对路径漂移。
        str_request_path = path_target.relative_to(project).as_posix()  # 已写入请求的相对路径

    # 审查是否通过仅由 error 级确定性发现决定。
    return {
        "project": str(project),
        "base": base,
        "head": head,
        "mode": mode,
        "changed_files": list_changes,
        "findings": list_findings,
        "review_dispatch_policy": str_dispatch,
        "required_manual_review": str_dispatch == "required_for_release",
        "semantic_review": dict_semantic_review,
        "ok": not any(item["severity"] == "error" for item in list_findings),
        "review_request": dict_request,
        "review_request_path": str_request_path,
    }

# CLI 入口定义参数合同、输出结果并映射失败退出码。
def main() -> None:
    """解析命令行参数、执行治理审查并输出 JSON。

    参数：无。
    返回：无。
    异常：发现 error 级治理问题时抛出 ``SystemExit(1)``。
    """

    # 参数解析器描述当前入口的治理审查职责。
    parser = argparse.ArgumentParser(  # 治理审查命令行解析器
        description="Review governance-sensitive code and design changes."  # CLI 帮助摘要
    )

    # 项目位置默认为当前工作目录。
    parser.add_argument("project", nargs="?", default=".")

    # 对比基线必须由调用方显式提供。
    parser.add_argument("--base", required=True)

    # 默认以当前 HEAD 作为对比目标。
    parser.add_argument("--head", default="HEAD")

    # 技能目录默认指向脚本所属技能包。
    parser.add_argument("--skill-dir", default=str(DEFAULT_SKILL_DIR))

    # 审查模式决定是否强制人工复核。
    parser.add_argument("--mode", choices=["all", "code", "design", "release"], default="all")

    # 请求写入开关保持默认执行只读。
    parser.add_argument("--write-request", action="store_true")

    # 文件名功能摘要证据由 Agent 生成并绑定当前修订与路径集合。
    parser.add_argument("--semantic-review")

    # 完成参数解析后再加载项目公共运行时依赖。
    namespace_args: argparse.Namespace = parser.parse_args()  # 已验证命令行参数

    # 公共解析器返回规范化且受治理的项目根目录。
    path_project = resolve_project(namespace_args.project)  # 被审查项目根目录

    # 技能目录先按调用方输入构造，随后相对项目解析。
    path_skill_dir = Path(namespace_args.skill_dir)  # 被审查技能目录

    # 相对技能路径以项目根为基准，避免依赖进程启动目录。
    if not path_skill_dir.is_absolute():

        # 合成项目内技能目录的绝对位置。
        path_skill_dir = path_project / path_skill_dir  # 项目内技能绝对路径

    # 相对语义复核证据路径同样以项目根为解析基准。
    path_semantic_review = (  # 用户提供的文件名语义证据位置
        Path(namespace_args.semantic_review)  # 把 CLI 文本转换为可解析路径
        if namespace_args.semantic_review  # 仅在用户提供证据参数时构造路径
        else None  # 未提供证据时交由治理门禁判断是否必需
    )

    # 相对证据路径必须绑定当前项目，避免随启动目录漂移。
    if path_semantic_review is not None and not path_semantic_review.is_absolute():

        # 合成仓库内证据的绝对路径供校验器读取。
        path_semantic_review = path_project / path_semantic_review  # 项目根下的语义证据路径

    # 治理编排器返回完整机器可读结果。
    dict_result = review_governance(  # 最终治理审查结果
        path_project, namespace_args.base, namespace_args.head,  # 项目与修订范围
        path_skill_dir.resolve(), namespace_args.mode,  # 技能目录与审查等级
        write_request=namespace_args.write_request,  # CLI 请求落盘开关
        semantic_review_path=path_semantic_review,  # Agent 文件名功能摘要证据
    )

    # 无论通过与否都先输出诊断载荷。
    emit_json(dict_result)

    # error 级发现必须映射为非零进程退出码。
    if not dict_result["ok"]:

        # 固定退出码 1 表示治理审查未通过。
        raise SystemExit(1)

# 直接脚本执行时进入 CLI，模块导入保持无副作用。
if __name__ == "__main__":

    # 运行参数解析、审查和结果输出完整流程。
    main()

