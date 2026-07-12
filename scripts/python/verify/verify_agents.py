"""提供 AGENTS 校验的稳定 CLI 与仓库级入口。"""

# 标准库提供命令行解析、运行时控制、路径和通用载荷类型。
import argparse
import sys
from pathlib import Path
from typing import Any

# 入口模块必须在加载任何仓库模块前关闭字节码写入，避免首次导入共享运行时自身落盘。
sys.dont_write_bytecode = True  # 路径式校验入口的缓存写入保护

from verify_agents_runtime_shared import (
    shared_task_dependencies,
    uses_legacy_language_skill_routing_rules,
)
from source_governance import format_source_governance_errors, source_governance_report
from verify_agents_scanning import scan_agents_file, should_skip

# 仓库验证入口汇总根规则、源码治理和全局基线诊断。
def verify(
    project: Path,
    include_skipped: bool = False,
    installed_skill_dir_override: str | Path | None = None,
) -> dict[str, Any]:
    """运行仓库级 AGENTS verifier，并返回扫描结果载荷。

    参数:
        project: 当前项目根目录。
        include_skipped: 为 True 时强制把跳过目录也纳入扫描。
        installed_skill_dir_override: 可选的安装态 skill 目录覆盖路径。

    返回:
        包含 checked_files、errors、warnings 与 global_codex_agents_status 的结果字典。
    """

    # 仓库级 verify 先集中拿到共享 helper，避免循环扫描时反复探测导入路径。
    dict_shared_dependencies = shared_task_dependencies()  # 仓库级校验共享 helper

    # 初始化仓库级错误、警告和已扫描文件列表。
    list_errors: list[str] = []  # 仓库级错误诊断集合

    # 单独保存仓库级 warning，避免和阻断性错误混在同一个列表里。
    list_warnings: list[str] = []  # 仓库级警告诊断集合

    # 记录每个实际参与扫描的 AGENTS.md，相对路径会直接反馈给 CLI 和测试。
    list_checked_files: list[str] = []  # 已扫描 AGENTS.md 相对路径集合

    # 收集项目 profile，后续根文件和路径示例判断都会复用这份配置。
    dict_profile = dict_shared_dependencies["project_profile"](project)  # 当前项目 profile 映射

    # 收集项目事实快照，后续用于补充 script layout 与 triad 缺口诊断。
    dict_facts = dict_shared_dependencies["inspect_project"](project)  # 当前项目事实快照

    # 读取安装态版本，后续根文件版本漂移检查依赖这条事实。
    str_installed_version = dict_shared_dependencies["read_installed_skill_version"](  # 当前安装态 agents-md-generator 版本
        override_dir=installed_skill_dir_override,  # 版本读取时优先覆盖到指定安装目录
    )

    # 生成根文件同步命令，后续根文件契约失配时统一复用它给出修复指引。
    str_root_repair_command = dict_shared_dependencies["root_agents_sync_command"](  # 刷新根 AGENTS.md 的标准命令
        project,  # 让命令锚定当前仓库根目录
        dict_profile,  # 让命令模板匹配当前项目画像
        installed_skill_dir_override,  # 让命令优先指向指定安装态 skill
    )

    # 预先固定根 AGENTS.md 路径，后续用它判断是否进入根文件专属校验链。
    path_root_agents = project / "AGENTS.md"  # 仓库根 AGENTS.md 路径

    # 逐个扫描仓库中的 AGENTS.md 文件，并在同一轮里完成文本、路径与命令诊断。
    for path_agents in sorted(project.rglob("AGENTS.md")):

        # 命中跳过目录的 AGENTS 文件不进入普通扫描链路。
        if should_skip(path_agents, project, include_skipped):

            # 调用方没有要求 include_skipped 时，这些路径在这里直接略过。
            continue

        # 把当前文件登记进 checked_files，便于调用方还原实际扫描范围。
        list_checked_files.append(str(path_agents.relative_to(project).as_posix()))

        # 单文件的文本、路径与命令契约都通过 helper 汇总，降低仓库级 verify 的密度。
        tuple_scan_result = scan_agents_file(  # 当前文件扫描返回的错误与警告元组
            path_agents, project, path_root_agents, dict_profile,  # 当前文件扫描的路径与 profile 上下文
            str_installed_version, str_root_repair_command, installed_skill_dir_override,  # 当前文件扫描的安装态与修复命令上下文
        )

        # 先拆出当前文件的错误列表，方便后续按仓库级错误容器统一汇总。
        list_current_file_errors = tuple_scan_result[0]  # 当前文件的错误列表

        # 再拆出当前文件的警告列表，保持错误和警告的汇总边界清晰。
        list_current_file_warnings = tuple_scan_result[1]  # 当前文件的警告列表

        # 汇总当前文件的错误与警告，保持最终输出仍然按仓库级列表返回。
        list_errors.extend(list_current_file_errors)

        # 警告单独折叠回仓库级容器，避免和错误列表交叉混合。
        list_warnings.extend(list_current_file_warnings)

    # 读取源码治理报告，后续把统一格式化后的治理错误折叠进总错误列表。
    dict_source_governance = source_governance_report(project, dict_profile)  # 当前仓库的源码治理报告

    # 把源码治理报告中的结构化错误折叠回总错误列表。
    list_errors.extend(format_source_governance_errors(dict_source_governance))

    # 追加 tool_script_layout_violations，保留 inspect_project 发现的脚本布局缺口。
    list_errors.extend(
        str(item)
        for item in dict_facts.get("tool_script_layout_violations", []) or []
    )

    # 追加 script_triad_gaps，保留 inspect_project 发现的脚本三元组缺口。
    list_errors.extend(
        str(item)
        for item in dict_facts.get("script_triad_gaps", []) or []
    )

    # 读取全局 baseline 健康状态，后续据此判断是否需要补一条全局同步诊断。
    dict_global_status = dict_shared_dependencies["global_codex_agents_status"](  # 全局 Codex AGENTS baseline 健康状态
        project_root=project,  # 让全局基线检查绑定当前仓库根目录
        profile=dict_profile,  # 让健康判断沿用当前项目画像
    )

    # 本仓库正在开发 agents-md-generator 时，global .codex/AGENTS.md 失配必须直接阻断。
    if (
        (project / "skills" / "agents-md-generator" / "SKILL.md").is_file()
        and not dict_global_status["baseline_ok"]
    ):

        # 汇总全局 baseline 的修复原因，方便把阻断根因一次性回显给调用方。
        list_repair_reasons = dict_global_status["repair_reasons"]  # 全局 baseline 的修复原因列表

        # 把原因列表折叠成单条文本，供最终 global baseline 阻断诊断复用。
        str_reason_text = ", ".join(list_repair_reasons) or "unknown global Codex AGENTS baseline issue"  # 全局 baseline 失配原因文本

        # 把 global .codex/AGENTS.md 的阻断原因整合成一条总诊断。
        list_errors.append(
            (
                f"global .codex/AGENTS.md is not healthy for "
                f"agents-md-generator development ({str_reason_text}); run "
                f"`{dict_shared_dependencies['global_codex_agents_sync_command'](project, dict_profile)}`"
            )
        )

    # 返回仓库级 verifier 载荷，供 CLI 和测试同时消费。
    return {
        "checked_files": list_checked_files,
        "errors": list_errors,
        "warnings": list_warnings,
        "global_codex_agents_status": dict_global_status,
    }

# 命令行入口解析项目范围并输出结构化验证载荷。
def main() -> int:
    """解析命令行参数并输出 AGENTS verifier 的 JSON 结果。

    返回:
        无业务返回值；结果直接通过标准输出发给 CLI 调用方。
    """

    # CLI 主入口先拿到项目解析与 JSON 输出 helper，保持 main 只负责参数编排。
    dict_shared_dependencies = shared_task_dependencies()  # CLI 入口共享 helper

    # 整理 main 需要的 parser 验证信息。
    parser = argparse.ArgumentParser(description="Verify AGENTS.md generated content.")  # AGENTS 校验输入值

    # 注册项目路径参数，缺省时默认扫描当前工作目录。
    parser.add_argument("project", nargs="?", default=".")

    # 注册 include-skipped 开关，允许调用方把跳过目录也纳入扫描。
    parser.add_argument("--include-skipped", action="store_true", help="Also scan skipped dirs.")

    # 注册安装态 skill 目录覆盖参数，便于测试安装态与源码态差异。
    parser.add_argument("--installed-skill-dir", default=None)

    # 解析命令行参数，后续会把这些值直接转交给 verify CLI 入口。
    args = parser.parse_args()  # 当前 CLI 入口解析得到的参数对象

    # 保存 verifier 载荷，确保 JSON 与退出状态来自同一结果。
    dict_verify_result = verify(  # 当前项目的完整 AGENTS 验证载荷。
        dict_shared_dependencies["resolve_project"](args.project),  # 规范化后的项目根目录。
        args.include_skipped,  # 是否扫描默认跳过的目录。
        args.installed_skill_dir,  # 可选安装态技能目录覆盖值。
    )  # 完成仓库验证并保留统一退出依据。

    # 把 verifier 结果作为 JSON 输出给 CLI、测试和上层工具消费。
    dict_shared_dependencies["emit_json"](dict_verify_result)

    # 发现任何权威错误时向调用进程返回失败。
    return 1 if dict_verify_result["errors"] else 0

# 直接执行模块时把主入口状态转换为进程退出码。
if __name__ == "__main__":

    # SystemExit 保持命令行成功与失败状态对外可见。
    raise SystemExit(main())
