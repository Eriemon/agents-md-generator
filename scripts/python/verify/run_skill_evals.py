"""执行正式技能效果评估，标准输出协议为机器可读 JSON。"""

# 延迟注解避免运行时解析仅用于类型检查的标注。
from __future__ import annotations

# 标准库提供命令行解析、路径建模和可调用类型。
import argparse
from collections.abc import Callable
import importlib
from pathlib import Path
from types import ModuleType
from typing import Any

# 评估核心提供路径常量、夹具、配置读取和 JSON 输出协议。
from eval_runtime_core import (
    EvalFixtures, REPO_ROOT, SCRIPTS_DIR, SKILL_DIR,
    emit_json, load_evals, load_evaluation_contract,
    load_eval_handlers, run_json_script,
)

# 分片通过模块命名空间公开配置声明的评估实现。
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

# 读取 evaluation contract 并解析其 handler。
def configured_handlers(dict_contract: dict[str, Any] | None = None) -> dict[str, EvalHandler]:
    """加载 contract 声明的 handler 映射。

    参数：dict_contract 为可选已解析评估合同；缺省时读取当前 runtime binding。
    返回：handler ID 到可调用对象的映射。
    异常：handler 模块、callable 或名称合同无效时抛出 SystemExit。
    """

    # 缺省调用通过 runtime contract 解析当前合同。
    dict_contract_data = dict_contract  # 当前评估合同

    # 只有缺省调用才需要从 runtime contract 读取合同。
    if dict_contract_data is None:

        # 从当前项目和技能根加载参数化评估合同。
        dict_contract_data = load_evaluation_contract(REPO_ROOT, SKILL_DIR)["contract"]  # 当前运行时评估合同对象

    # 保存合同声明的 handler 结果，拒绝隐式业务枚举。
    dict_configured_handlers: dict[str, EvalHandler] = {}  # 配置 handler 映射

    # 逐项解析模块和 callable，保持失败可定位。
    for dict_binding in dict_contract_data.get("handlers", []):

        # 每项必须是结构化对象。
        if not isinstance(dict_binding, dict):

            # 非对象 binding 无法提供模块和 callable 字段。
            raise SystemExit("> ERR: [Python] evaluation handler binding is invalid")

        # 读取合同声明的逻辑名称与 Python 标识符。
        str_handler_id = str(dict_binding.get("handler_id", "")).strip()  # handler 逻辑名称

        # 读取合同声明的模块名称。
        str_module_name = str(dict_binding.get("module_name", "")).strip()  # handler 模块名称

        # 读取合同声明的 callable 名称。
        str_callable_name = str(dict_binding.get("callable_name", "")).strip()  # 合同模块中的处理器函数名称

        # 只接受模块和 callable 标识符，避免合同驱动任意路径导入。
        if (
            not str_handler_id
            or not str_module_name.isidentifier()
            or not str_callable_name.isidentifier()
            or not (str_module_name.startswith("eval_runtime_") or str_module_name == "run_skill_evals")
        ):

            # 名称越界或缺失时阻断动态导入。
            raise SystemExit("> ERR: [Python] evaluation handler binding names are invalid")

        # 当前 verify runtime 目录提供声明模块。
        module_type_object_module: ModuleType = importlib.import_module(str_module_name)  # 动态加载合同声明的模块。

        # 从模块中读取合同声明的 callable。
        obj_object_handler: object = getattr(module_type_object_module, str_callable_name, None)  # 读取合同声明的处理器。

        # 缺失 callable 或重复逻辑名称都阻断执行。
        if not callable(obj_object_handler) or str_handler_id in dict_configured_handlers:

            # handler 缺失、非 callable 或 ID 重复时停止执行。
            raise SystemExit("> ERR: [Python] evaluation handler cannot be resolved")

        # 保存已验证 handler 供执行循环使用。
        dict_configured_handlers[str_handler_id] = obj_object_handler  # 已解析处理器映射。

    # 返回完整配置驱动映射。
    return dict_configured_handlers

# 配置驱动的外部案例适配器保留统一 handler 签名。
def case_external_generic_health_configured(
    dict_case: dict[str, Any],
    eval_fixtures: EvalFixtures,
) -> dict[str, Any]:
    """使用评估输入中的外部技能目录执行通用健康案例。

    参数：dict_case 为评估案例；eval_fixtures 为当前执行夹具。
    返回：外部技能健康案例的结构化结果。
    异常：夹具未提供外部技能目录时抛出 SystemExit。
    """

    # 外部目录只从当前执行夹具注入，不从源码推断。
    path_external_skill = getattr(eval_fixtures, "external_skill_dir", None)  # 夹具注入的外部技能根

    # 没有外部目录时当前条件案例不可执行。
    if not isinstance(path_external_skill, Path):

        # 缺失外部输入必须保持 fail-closed。
        raise SystemExit("> ERR: [Python] external evaluation input is unavailable")

    # 复用项目案例模块的唯一外部健康实现。
    return case_external_generic_health(path_external_skill, dict_case)

# 根据 contract activation 判断一个案例是否启用。
def case_is_enabled(
    dict_case: dict[str, Any],
    path_external_skill: Path | None,
    dict_contract: dict[str, Any],
) -> bool:
    """根据 contract 声明的 activation 判断案例是否启用。

    参数：dict_case 为案例配置；path_external_skill 为可选外部技能根；dict_contract 为 activation 合同。
    返回：案例满足 activation 时返回 True。
    异常：activation 结构或 operator 未被合同声明时抛出 SystemExit。
    """

    # 读取当前案例的可选 activation 声明。
    obj_object_activation: object = dict_case.get("activation")  # 当前案例 activation 声明。

    # 没有 activation 的案例默认属于本地评估集合。
    if obj_object_activation is None:

        # 本地案例不依赖外部输入。
        return True

    # activation 必须保持对象形状。
    if not isinstance(obj_object_activation, dict):

        # 结构错误不能被解释为本地案例。
        raise SystemExit("> ERR: [Python] evaluation case activation is invalid")

    # 操作符和输入字段均必须来自独立合同。
    str_operator = str(obj_object_activation.get("operator", "")).strip()  # 当前 activation 运算符条件。

    # 读取 activation 绑定的输入字段。
    str_input = str(obj_object_activation.get("input", "")).strip()  # activation 输入字段。

    # 读取合同允许的 activation 运算符集合。
    list_operators = dict_contract.get("activation_operators", [])  # 合同运算符列表

    # 只允许合同声明的外部技能输入条件。
    if str_operator not in list_operators or str_input != "external_skill_dir":

        # 不支持的 operator/input 组合不能启用案例。
        raise SystemExit("> ERR: [Python] evaluation case activation is unsupported")

    # 外部目录存在时才启用条件案例。
    return path_external_skill is not None

# 案例执行助手逐条解析 handler 并保留未知名称诊断。
def execute_configured_cases(
    list_cases: list[object],
    dict_handlers: dict[str, EvalHandler],
    eval_fixtures: EvalFixtures,
    dict_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    """执行评估配置中登记的全部案例。

    参数：list_cases 为案例定义，dict_handlers 为可调用映射。
    参数：eval_fixtures 为共享临时工程夹具；dict_contract 为 activation/handler 合同。
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

        # 未满足 activation 的案例保持配置顺序但不进入执行结果。
        if not case_is_enabled(object_case, getattr(eval_fixtures, "external_skill_dir", None), dict_contract):

            # 条件未满足时跳过当前案例并继续保持配置顺序。
            continue

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
    eval_fixtures_eval_fixtures: EvalFixtures = EvalFixtures(  # 当前评估执行共享夹具
        SCRIPTS_DIR,  # 当前技能脚本根
        external_skill_dir=external_skill_dir,  # 可选外部技能根
    )

    # cases 顶层字段必须是保持顺序的列表。
    object_cases = dict_evaluations.get("cases", [])  # 原始评估案例配置值。

    # 非列表配置无法维持案例执行顺序。
    if not isinstance(object_cases, list):

        # 固定错误文本指向 evals.json 顶层字段。
        raise SystemExit("> ERR: [Python] evals.json cases must be a list")

    # runtime contract 负责把 case 名称连接到实现模块。
    dict_contract_result = load_evaluation_contract(REPO_ROOT, SKILL_DIR)  # 已校验的评估合同绑定

    # 读取合同对象供 activation 和 handler 解析复用。
    dict_evaluation_contract = dict_contract_result["contract"]  # 已校验的评估合同对象

    # handler 映射从 contract 解析，避免在 Python 中枚举当前案例。
    dict_configured_handlers = configured_handlers(dict_evaluation_contract)  # 合同声明的处理器映射

    # 本地案例通过完整 handler 映射逐条执行。
    list_results = execute_configured_cases(  # 执行全部本地案例并保持配置顺序
        object_cases,  # 配置文件中的有序案例定义
        dict_configured_handlers,  # 合同解析出的处理器映射
        eval_fixtures_eval_fixtures,  # 当前执行共享的临时工程夹具
        dict_evaluation_contract,  # 控制案例启用条件与处理器来源的合同
    )  # 执行全部仓库本地评估案例。

    # 汇总与案例列表使用同一最终结果集合。
    dict_summary = build_evaluation_summary(list_results)  # 当前技能评估汇总。

    # 完整报告保留配置版本、来源、案例证据和最终状态。
    return {
        "version": int(dict_evaluations.get("version", 1)),
        "evals_path": str(dict_evaluations.get("_path", "")),
        "cases": list_results,
        "summary": dict_summary,
    }

# 将评估运行时异常转换为稳定的机器可读失败报告。
def _build_cli_failure_result(
    dict_evaluations: dict[str, object],
    object_error: BaseException,
) -> dict[str, object]:
    """构造评估 CLI 的结构化失败结果。

    参数：
        dict_evaluations 为本次已解析的评估配置；object_error 为评估执行异常。
    返回：
        包含脱敏错误载荷和失败汇总的机器可读映射。
    异常：
        本函数不主动抛出异常，确保失败路径仍能输出 JSON。
    """

    # RuntimeContractError 已经提供经过脱敏的字段级载荷，优先复用该事实。
    object_payload = getattr(object_error, "payload", None)  # 合同异常的结构化错误载荷。

    # 非合同异常使用稳定通用错误，不把 traceback 或本地路径写入 stdout。
    if isinstance(object_payload, dict):

        # 合同异常的载荷已通过 loader 脱敏，可以直接作为错误事实。
        dict_error: dict[str, object] = object_payload  # 当前合同错误对象。

    # 非合同异常必须转换为固定的通用错误对象。
    else:

        # 非合同异常不暴露内部文本，只返回固定错误类别。
        dict_error = {  # 当前通用评估错误对象。
            "error_code": "EVALUATION_RUNTIME_ERROR",  # 通用错误代码。
            "field": "evaluation",  # 通用错误字段。
            "message": "evaluation execution failed",  # 通用错误说明。
            "path_class": "",  # 通用错误不绑定本地路径类别。
        }

    # 失败汇总保持与成功报告相同的字段形状，供 CLI caller 稳定解析。
    dict_summary: dict[str, object] = {
        "case_count": 0,  # 失败路径不伪造已执行的 case 数量。
        "passed_cases": 0,  # 失败路径不伪造通过数量。
        "improved_cases": 0,  # 失败路径不伪造改进数量。
        "stable_cases": 0,  # 失败路径不伪造稳定数量。
        "ok": False,  # 结构化失败必须明确不可用。
    }  # 失败状态汇总。

    # 返回 JSON 输出所需的最小事实集合，不伪造任何评估 case 结果。
    return {
        "version": int(dict_evaluations.get("version", 1)),
        "evals_path": str(dict_evaluations.get("_path", "")),
        "cases": [],
        "summary": dict_summary,
        "error": dict_error,
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
    try:

        # 当前评估配置及来源路径进入正式执行器。
        dict_evaluation_result = evaluate_cases(  # 当前技能效果评估报告。
            dict_evaluations,  # 当前评估配置及来源路径。
            external_skill_dir=path_external_skill,  # 可选外部技能冒烟目标。
        )  # 执行正式技能效果评估。

    # runtime contract 或配置失败也必须落成结构化 JSON。
    except (Exception, SystemExit) as object_error:

        # 失败结果保持 stdout 机器协议完整，并由下方统一返回非零状态。
        dict_evaluation_result = _build_cli_failure_result(  # 将异常转换为机器可读失败报告。
            dict_evaluations,  # 保留本次评估配置版本。
            object_error,  # 传入脱敏合同错误或通用异常。
        )

    # 机器可读报告供置信度门禁和发布验证消费。
    emit_json(dict_evaluation_result)

    # 汇总 ok 字段决定当前评估进程退出状态。
    return 0 if dict_evaluation_result["summary"]["ok"] else 1

# 直接执行模块时把评估状态转换为进程退出码。
if __name__ == "__main__":

    # SystemExit 保持自动化调用方可观察的成功或失败状态。
    raise SystemExit(main())
