"""执行正式技能效果评估，标准输出协议为机器可读 JSON。"""

# 延迟注解避免运行时解析仅用于类型检查的标注。
from __future__ import annotations

# 标准库提供命令行解析、路径建模和可调用类型。
import argparse
from collections.abc import Callable
from pathlib import Path
from typing import Any

# 评估核心提供路径常量、夹具、配置读取和 JSON 输出协议。
from eval_runtime_core import EvalFixtures, SCRIPTS_DIR, SKILL_DIR, emit_json, load_evals, run_json_script

# 三个分片通过模块命名空间公开项目、基础治理和策略案例。
import eval_runtime_project_cases as project_cases
import eval_runtime_foundation_cases as foundation_cases
import eval_runtime_policy_cases as policy_cases
import eval_runtime_release_cases as release_cases
import eval_runtime_workspace_cases as workspace_cases

# Handler 类型固定案例定义、评估夹具和结构化结果合同。
EvalHandler = Callable[[dict[str, Any], EvalFixtures], dict[str, Any]]  # 单个正式评估案例处理器类型。

# 兼容入口允许测试和外部调用方替换脚本执行器。
def case_external_generic_health(path_skill_dir: Path, dict_case: dict[str, Any]) -> dict[str, Any]:
    """使用当前模块的可替换脚本执行器运行外部技能健康检查。

    参数：path_skill_dir 为外部技能目录，dict_case 为评估案例配置。
    返回：外部技能审计和评估的对比结果。
    """

    # 项目案例模块在调用期间共享当前入口公开的执行器。
    func_original_runner = project_cases.run_json_script  # 项目案例原脚本执行器。

    # 注入当前入口可由调用方替换的脚本执行器。
    project_cases.run_json_script = run_json_script  # 本次外部健康检查使用的脚本执行器。

    # 即使案例执行失败，也必须恢复基础模块原状态。
    try:

        # 实际案例逻辑仍由项目案例模块唯一维护。
        return project_cases.case_external_generic_health(path_skill_dir, dict_case)

    # 恢复动作覆盖正常返回和异常退出两条路径。
    finally:

        # 调用结束恢复模块状态，避免替换泄漏到其他案例。
        project_cases.run_json_script = func_original_runner  # 恢复项目案例原脚本执行器。

# 基础 handler 表集中项目发现、审计、安装和源码治理案例。
def foundation_handlers() -> dict[str, EvalHandler]:
    """返回基础技能效果案例的 handler 映射。

    参数：无，handler 均来自基础评估分片。
    返回：evals.json handler 名称到可调用对象的映射。
    """

    # 每个公开名称必须与 evals.json 中登记的 handler 字段一致。
    return {
        "detect_missing_root_agents": project_cases.case_missing_root_agents,
        "generator_version_takeover": project_cases.case_version_mismatch_takeover,
        "root_level_whitelist_gate": project_cases.case_root_whitelist,
        "evolution_removed_contract": project_cases.case_evolution_removed_contract,
        "experience_removed_contract": project_cases.case_experience_removed_contract,
        "generic_audit_split": project_cases.case_generic_audit_split,
        "evaluate_failure_classification": project_cases.case_evaluate_classification,
        "install_release_completeness": project_cases.case_install_release_completeness,
        "review_governance_companion_checks": foundation_cases.case_review_governance_companion_checks,
        "openai_metadata_standard_contract": foundation_cases.case_openai_metadata_standard_contract,
        "design_review_gate": foundation_cases.case_design_review_gate,
        "source_governance_test_boundary": foundation_cases.case_source_governance_test_boundary,
        "source_governance_size_readability_contract": (
            foundation_cases.case_source_governance_size_readability_contract
        ),
    }

# 策略 handler 表集中语言、发布、记忆和治理入口案例。
def policy_handlers() -> dict[str, EvalHandler]:
    """返回治理策略效果案例的 handler 映射。

    参数：无，handler 均来自策略评估分片。
    返回：evals.json handler 名称到可调用对象的映射。
    """

    # 策略映射保持评估清单与具体实现之间的显式连接。
    return {
        "additional_worktree_prohibition_contract": policy_cases.case_additional_worktree_prohibition_contract,
        "root_version_sync_contract": policy_cases.case_root_version_sync_contract,
        "source_repo_render_version_contract": policy_cases.case_source_repo_render_version_contract,
        "language_skill_routing_contract": policy_cases.case_language_skill_routing_contract,
        "script_output_policy_contract": policy_cases.case_script_output_policy_contract,
        "plan_mode_language_lock_contract": policy_cases.case_plan_mode_language_lock_contract,
        "codex_token_usage_review_contract": policy_cases.case_codex_token_usage_review_contract,
        "governance_runtime_de_vendoring": release_cases.case_governance_runtime_de_vendoring,
        "installed_runtime_owner_repo_local_commands": release_cases.case_installed_runtime_owner_repo_local_commands,
        "handoff_naming_gate": release_cases.case_handoff_naming_gate,
        "workspace_settings_gate": release_cases.case_workspace_settings_gate,
        "release_content_evals_install_contract": release_cases.case_release_content_evals_install_contract,
        "release_sanitizer_regex_constant": release_cases.case_release_sanitizer_regex_constant,
        "root_workspace_artifact_gate": workspace_cases.case_root_workspace_artifact_gate,
        "task_rating_gate_contract": workspace_cases.case_task_rating_gate_contract,
        "memory_governance_gate": workspace_cases.case_memory_governance_gate,
        "governance_cli_entrypoint_smoke": release_cases.case_governance_cli_entrypoint_smoke,
    }

# Handler 聚合助手合并两类评估分片并检查命名覆盖边界。
def all_handlers() -> dict[str, EvalHandler]:
    """合并基础与策略评估 handler。

    参数：无，来源由两个分片映射固定。
    返回：供评估执行循环查询的完整 handler 映射。
    """

    # 基础映射作为合并结果的初始内容。
    dict_handlers = foundation_handlers()  # 当前完整 handler 映射的基础部分。

    # 策略映射追加到同一命名空间。
    dict_handlers.update(policy_handlers())

    # 合并结果由案例执行入口只读使用。
    return dict_handlers

# 外部技能案例助手按需追加真实通用技能健康检查。
def append_external_skill_case(list_results: list[dict[str, Any]], path_external_skill: Path | None) -> None:
    """在指定外部技能时追加通用路径健康案例。

    参数：list_results 为案例结果列表，path_external_skill 为可选技能目录。
    返回：无业务返回值，外部案例结果原地追加到 list_results。
    """

    # 未指定外部技能时不扩展仓库本地评估范围。
    if path_external_skill is None:

        # 保持调用方提供的本地案例结果不变。
        return

    # 外部案例定义验证真实通用技能通过当前工具链。
    dict_external_case = {  # 外部技能健康案例定义。
        "id": "healthy_external_skill_generic_path",  # 外部健康案例稳定标识。
        "kind": "external_smoke",  # 案例属于外部真实路径冒烟验证。
        "patterns": ["Tool Wrapper", "Pipeline"],  # 通用技能覆盖的设计模式。
        "description": "A healthy external skill should pass generic audit and evaluation.",  # 案例目标说明。
    }

    # 专用基础案例函数不需要 EvalFixtures 参数。
    list_results.append(
        case_external_generic_health(path_external_skill, dict_external_case)
    )

# 案例执行助手逐条解析 handler 并保留未知名称诊断。
def execute_configured_cases(
    list_cases: list[object],
    dict_handlers: dict[str, EvalHandler],
    eval_fixtures: EvalFixtures,
) -> list[dict[str, Any]]:
    """执行评估配置中登记的全部案例。

    参数：list_cases 为案例定义，dict_handlers 为可调用映射。
    参数：eval_fixtures 为共享临时工程夹具。
    返回：按配置顺序生成的案例结果列表。
    异常：案例不是对象或 handler 未知时抛出 SystemExit。
    """

    # 结果顺序与 evals.json 定义顺序保持一致。
    list_results: list[dict[str, Any]] = []  # 当前已执行的评估案例结果。

    # 每个案例必须解析到一个显式 handler。
    for object_case in list_cases:

        # 非对象案例无法提供 id、kind 和 handler 字段。
        if not isinstance(object_case, dict):

            # 结构错误使用固定前缀向 CLI 调用方报告。
            raise SystemExit("> ERR: [Python] eval case must be an object")

        # Handler 名称经去空白后用于查询显式映射。
        str_handler_name = str(object_case.get("handler", "")).strip()  # 当前案例 handler 名称。

        # 查询结果可能为空，必须在调用前单独验证。
        func_handler: EvalHandler | None = dict_handlers.get(str_handler_name)  # 当前案例可调用 handler。

        # 未知名称表示评估配置和实现发生漂移。
        if func_handler is None:

            # 错误文本回显具体名称便于修正 evals.json。
            raise SystemExit(f"> ERR: [Python] unknown eval handler: {str_handler_name}")

        # Handler 结果追加到与配置一致的顺序位置。
        list_results.append(func_handler(object_case, eval_fixtures))

    # 完整结果列表交给汇总逻辑计算通过状态。
    return list_results

# 汇总助手计算案例数量、通过数量和改进数量。
def build_evaluation_summary(list_results: list[dict[str, Any]]) -> dict[str, Any]:
    """根据案例结果构造评估汇总。

    参数：list_results 为全部本地及外部案例结果。
    返回：包含计数和最终 ok 状态的汇总映射。
    """

    # 计数项分别描述规模、通过、改进与稳定案例。
    dict_summary: dict[str, Any] = {  # 当前技能评估计数汇总。
        "case_count": len(list_results),  # 本次实际执行案例总数。
        "passed_cases": sum(1 for dict_item in list_results if dict_item["passed"]),  # 最终通过案例数。
        "improved_cases": sum(1 for dict_item in list_results if dict_item["comparison"]["improved"]),  # 有改进案例数。
        "stable_cases": sum(1 for dict_item in list_results if dict_item["passed"]),  # 保持稳定通过案例数。
    }

    # 最终状态要求至少有一个案例且所有案例均通过。
    dict_summary["ok"] = (
        dict_summary["case_count"] > 0  # 至少执行一个有效案例。
        and dict_summary["passed_cases"] == dict_summary["case_count"]  # 所有案例均通过。
    )  # 形成汇总层最终状态。

    # 汇总结果供 CLI 退出码和报告共同使用。
    return dict_summary

# 评估入口执行配置案例并返回完整结构化报告。
def evaluate_cases(
    dict_evaluations: dict[str, object],
    *,
    external_skill_dir: Path | None = None,
) -> dict[str, object]:
    """运行 evals.json 中登记的所有评估用例。

    参数：dict_evaluations 为评估配置映射。
    参数：external_skill_dir 为可选真实外部技能目录。
    返回：包含案例记录、汇总和配置来源的评估报告。
    异常：cases 不是列表时抛出 SystemExit。
    """

    # 共享夹具以当前 verify 目录作为技能脚本定位基准。
    eval_fixtures_eval_fixtures: EvalFixtures = EvalFixtures(SCRIPTS_DIR)  # 当前评估执行共享夹具。

    # cases 顶层字段必须是保持顺序的列表。
    object_cases = dict_evaluations.get("cases", [])  # 原始评估案例配置值。

    # 非列表配置无法维持案例执行顺序。
    if not isinstance(object_cases, list):

        # 固定错误文本指向 evals.json 顶层字段。
        raise SystemExit("> ERR: [Python] evals.json cases must be a list")

    # 本地案例通过完整 handler 映射逐条执行。
    list_results = execute_configured_cases(  # 当前全部本地案例结果。
        object_cases,  # evals.json 中的有序案例定义。
        all_handlers(),  # 两个分片合并后的完整处理器映射。
        eval_fixtures_eval_fixtures,  # 当前执行共享的临时工程夹具。
    )  # 执行全部仓库本地评估案例。

    # 调用方指定外部技能时追加真实路径健康案例。
    append_external_skill_case(list_results, external_skill_dir)

    # 汇总与案例列表使用同一最终结果集合。
    dict_summary = build_evaluation_summary(list_results)  # 当前技能评估汇总。

    # 完整报告保留配置版本、来源、案例证据和最终状态。
    return {
        "version": int(dict_evaluations.get("version", 1)),
        "evals_path": str(dict_evaluations.get("_path", "")),
        "cases": list_results,
        "summary": dict_summary,
    }

# CLI 主入口加载评估配置并输出正式技能效果报告。
def main() -> int:
    """解析评估参数并返回技能效果门禁状态。

    参数：无，命令行参数由当前进程读取。
    返回：评估全部通过返回 0，否则返回 1。
    """

    # 解析器支持默认仓库评估文件和可选外部技能目录。
    argument_parser_evals = argparse.ArgumentParser(  # 技能评估命令行解析器。
        description="Run repository-local skill effectiveness evaluations."  # CLI 用途说明。
    )  # 构造技能评估参数解析器。

    # 默认配置位于当前技能的 evals 目录。
    argument_parser_evals.add_argument(
        "evals_path",
        nargs="?",
        default=str(SKILL_DIR / "evals" / "evals.json"),
    )

    # 外部技能目录启用真实通用技能 smoke 案例。
    argument_parser_evals.add_argument("--external-skill-dir", default=None)

    # 当前参数对象决定配置来源和可选外部技能。
    object_arguments = argument_parser_evals.parse_args()  # 当前评估命令行参数。

    # 配置路径规范化后写回报告作为证据来源。
    path_evaluations = Path(object_arguments.evals_path).expanduser().resolve()  # 当前 evals.json 路径。

    # 配置读取助手保证顶层为 JSON 对象。
    dict_evaluations = load_evals(path_evaluations)  # 当前评估配置映射。

    # 报告中的来源路径必须对应本次真实读取文件。
    dict_evaluations["_path"] = str(path_evaluations)  # 本次真实读取的配置来源路径。

    # 可选外部目录只在调用方明确提供时解析。
    path_external_skill = (  # 可选外部真实技能目录。
        Path(object_arguments.external_skill_dir).expanduser().resolve()  # 规范化用户提供的外部目录。
        if object_arguments.external_skill_dir  # 只在参数非空时构造路径。
        else None  # 未指定时仅执行仓库本地案例。
    )  # 完成可选外部技能路径解析。

    # 正式评估报告是 JSON 输出和退出状态的共同真值。
    dict_evaluation_result = evaluate_cases(  # 当前技能效果评估报告。
        dict_evaluations,  # 当前评估配置及来源路径。
        external_skill_dir=path_external_skill,  # 可选外部技能冒烟目标。
    )  # 执行正式技能效果评估。

    # 机器可读报告供置信度门禁和发布验证消费。
    emit_json(dict_evaluation_result)

    # 汇总 ok 字段决定当前评估进程退出状态。
    return 0 if dict_evaluation_result["summary"]["ok"] else 1

# 直接执行模块时把评估状态转换为进程退出码。
if __name__ == "__main__":

    # SystemExit 保持自动化调用方可观察的成功或失败状态。
    raise SystemExit(main())
