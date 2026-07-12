"""审查变更范围是否满足测试、文档、评测和发布治理契约。"""

# 延迟注解求值避免运行时解析仅用于类型检查的结构。
from __future__ import annotations

# 导入治理审查所需的标准库模块。
import argparse
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
        and "tests/run_skill_evals.py" not in set_changed
    ):

        # 记录运行态评测执行链未同步的治理发现。
        list_findings.append(
            finding(
                "runtime-routing-change-without-eval-harness",
                (
                    "Governance runtime routing changes require eval coverage "
                    "in evals/evals.json or tests/run_skill_evals.py."
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
    project: Path,
    base: str,
    head: str,
    skill_dir: Path,
    mode: str,
    write_request: bool = False,
) -> dict[str, Any]:
    """执行变更治理审查并按需写入审查请求文件。

    参数：
        project: Git 项目根目录。
        base: 对比基线修订。
        head: 对比目标修订。
        skill_dir: 被审查技能目录。
        mode: 当前审查模式。
        write_request: 是否写入 ``.agents/review-request.json``。
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

    # 治理编排器返回完整机器可读结果。
    dict_result = review_governance(  # 最终治理审查结果
        path_project,  # CLI 已解析的项目位置
        namespace_args.base,  # CLI 指定的起始修订
        namespace_args.head,  # CLI 指定的结束修订
        path_skill_dir.resolve(),  # 规范化技能目录
        namespace_args.mode,  # CLI 选择的审查等级
        write_request=namespace_args.write_request,  # CLI 请求落盘开关
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

