"""验证并安装版本化 Codex 技能发布包，标准输出协议为机器可读 JSON。"""

# 标准库提供命令行解析、进程调用、路径和载荷类型。
import argparse
import subprocess
from pathlib import Path
from typing import Any, cast

# 发布清单模块提供共同运行时、决策载荷和 worktree 检查入口。
from install_release_manifest import (
    decision_request,
    emit_json,
    global_codex_agents_status,
    inspect_worktree_policy,
    install_options,

    # 发布内容路径提取和项目规范化属于安装入口的输入处理能力。
    referenced_release_paths,
    resolve_project,
    sha256_file,
    validate_release_completeness,
)

# 清洗模块的公开文本处理函数继续由安装门面兼容导出。
from install_release_sanitization import sanitize_release_text, validate_release_sanitization

# 仓库验证模块提供发布包验证及可替换的源码状态门面。
import install_repository_validation as repository_validation
from install_repository_validation import normalize_branch_list_line, validate_release_dir

# 目标复制模块负责解析安装位置并执行备份替换。
from install_target_copy import copy_skill, target_path

# 仓库状态门面保留测试可替换的检查器和进程边界。
def verify_repo_release_state(path_repo_root: Path) -> list[str]:
    """验证源码仓库状态是否与发布收据一致。

    参数：path_repo_root 为发布包所属源码仓库根目录。
    返回：仓库状态错误列表，通过时为空列表。
    """

    # 显式注入策略检查器和进程运行器，保持安装门面可测试。
    return repository_validation.verify_repo_release_state(
        path_repo_root,
        worktree_inspector=inspect_worktree_policy,
        process_runner=subprocess.run,
    )

# 参数解析助手集中维护安装目标、写入开关和用户意图合同。
def build_argument_parser() -> argparse.ArgumentParser:
    """构造技能安装命令行解析器。

    参数：无，所有选项由安装入口固定声明。
    返回：配置完成的 ArgumentParser。
    """

    # 解析器说明强调安装前必须完成发布包验证和用户确认。
    argument_parser_install = argparse.ArgumentParser(  # 技能安装命令行解析器。
        description="Install a verified Codex skill after explicit user confirmation."  # CLI 用途说明。
    )  # 构造安装入口的参数解析器。

    # 发布目录是唯一必填位置参数。
    argument_parser_install.add_argument("release_dir")

    # 目标类型决定仅验证、安装到 Codex 或写入自定义目录。
    argument_parser_install.add_argument("--target", choices=["skip", "codex", "custom"], default="skip")

    # Codex 根目录覆盖值用于隔离测试和非默认本地安装。
    argument_parser_install.add_argument("--codex-home", default=None)

    # 自定义根目录仅在 custom 目标下参与目标路径解析。
    argument_parser_install.add_argument("--custom-root", default=None)

    # 写入开关将默认 dry-run 升级为真实文件复制。
    argument_parser_install.add_argument(
        "--write",
        action="store_true",
        help="Actually copy the skill. Default is dry-run.",
    )

    # 替换开关允许在确认后备份并覆盖现有安装。
    argument_parser_install.add_argument(
        "--replace",
        action="store_true",
        help="Replace an existing installed skill after user confirmation.",
    )

    # 安装意图区分未确认 dry-run 与用户明确要求的安装执行。
    argument_parser_install.add_argument(
        "--install-intent",
        choices=["unspecified", "requested"],
        default="unspecified",
    )

    # 返回完整解析器供主入口读取当前进程参数。
    return argument_parser_install

# 结果载荷助手汇总验证证据和目标安装状态。
def build_install_result(
    path_release_directory: Path,
    dict_validation: dict[str, Any],
    object_arguments: argparse.Namespace,
    path_destination: Path | None,
) -> dict[str, Any]:
    """构造安装 dry-run 与真实写入共享的结果载荷。

    参数：path_release_directory 为已规范化的发布目录。
    参数：dict_validation 为发布包验证结果。
    参数：object_arguments 为安装命令行参数。
    参数：path_destination 为可选安装目标路径。
    返回：包含验证证据及初始安装状态的映射。
    """

    # 载荷字段同时服务 CLI、测试和上层发布门禁。
    return {
        "release_dir": str(path_release_directory),
        "skill_name": dict_validation["skill_name"],
        "version": dict_validation["version"],
        "target": object_arguments.target,
        "install_intent": object_arguments.install_intent,
        "destination": str(path_destination) if path_destination else "",
        "installed": False,
        "skipped": object_arguments.target == "skip" or not object_arguments.write,
        "backup_path": "",
        "receipt_path": dict_validation["receipt_path"],
        "provenance_mode": dict_validation["provenance_mode"],
        "validation_level": dict_validation["validation_level"],
        "policy_version": dict_validation["policy_version"],
        "forbidden_source_paths": dict_validation["forbidden_source_paths"],
        "forbidden_release_paths": dict_validation["forbidden_release_paths"],
        "release_content_policy_ok": dict_validation["release_content_policy_ok"],
        "global_codex_agents_status": global_codex_agents_status(object_arguments.codex_home),
    }

# 确认载荷助手在用户尚未明确安装时给出结构化选择。
def add_confirmation_request(
    dict_result: dict[str, Any],
    path_release_directory: Path,
    object_arguments: argparse.Namespace,
) -> None:
    """按需向 dry-run 结果追加安装确认问题。

    参数：dict_result 为待补充的安装结果映射。
    参数：path_release_directory 为当前发布目录。
    参数：object_arguments 为安装命令行参数。
    返回：无业务返回值，确认字段原地写入 dict_result。
    """

    # 已明确请求安装的调用无需重复生成确认问题。
    if object_arguments.install_intent != "unspecified":

        # 保持调用方已经表达的安装意图不变。
        return

    # 只有未写入或主动跳过时才需要返回确认选择。
    if object_arguments.target != "skip" and object_arguments.write:

        # 真实写入调用已具备明确目标和写入开关。
        return

    # 中文确认文本说明默认行为仍是跳过安装。
    dict_result["confirmation_question"] = "发布包验证完成。是否安装这个技能？请选择是或否；默认是否，跳过安装。"  # 用户确认问题。

    # 公开选项由共同发布清单模块集中维护。
    dict_result["options"] = install_options()  # 安装、跳过等公开选择。

    # 决策请求携带重跑命令所需的发布目录与目标上下文。
    dict_result["decision_request"] = decision_request(  # 结构化安装确认请求。
        "install_confirmation",  # 决策请求类型。
        question=dict_result["confirmation_question"],  # 面向用户的确认文本。
        options=dict_result["options"],  # 可选安装决策列表。
        default="skip",  # 未响应时保持不写入。
        risk="medium",  # 本地技能替换风险等级。
        next_action="rerun install_skill.py with --write after confirmation",  # 确认后的重跑指引。
        context={"release_dir": str(path_release_directory), "target": object_arguments.target},  # 决策上下文。
    )  # 完成统一决策载荷构造。

# 安装执行助手复制发布包并把失败转换为结构化诊断。
def execute_install(
    path_release_directory: Path,
    path_destination: Path,
    bool_replace: bool,
    dict_result: dict[str, Any],
) -> None:
    """执行已确认的技能复制并输出最终载荷。

    参数：path_release_directory 为验证通过的发布目录。
    参数：path_destination 为真实安装目标目录。
    参数：bool_replace 控制是否备份并替换现有安装。
    参数：dict_result 为共享安装结果映射。
    返回：无业务返回值，成功时更新并输出 dict_result。
    异常：复制失败时抛出 SystemExit 并输出结构化错误。
    """

    # 文件复制可能因目标冲突或文件系统错误而失败。
    try:

        # 复制结果包含安装位置和可选备份路径。
        dict_install_details = copy_skill(  # 当前技能复制结果。
            path_release_directory,  # 已验证发布包目录。
            path_destination,  # 当前安装目标目录。
            bool_replace,  # 是否允许替换现有技能。
        )  # 执行备份及发布内容复制。

    # 复制助手主动抛出的退出状态应原样保留。
    except SystemExit:

        # 上层已负责输出对应的结构化错误。
        raise

    # 其他异常统一转为安装错误 JSON。
    except Exception as object_error:

        # 错误载荷保留发布包验证阶段的全部证据。
        emit_json({"errors": [str(object_error)], **dict_result})

        # 非预期复制异常向调用进程返回失败。
        raise SystemExit(1)

    # 复制详情补充目标和备份等运行时事实。
    dict_result.update(dict_install_details)

    # 最终状态明确标记真实安装已经完成。
    dict_result["installed"] = True  # 真实安装完成标志。

    # 成功写入后结果不再属于跳过状态。
    dict_result["skipped"] = False  # 本次调用未跳过文件写入。

    # 输出最终机器可读安装结果。
    emit_json(dict_result)

# CLI 主入口验证发布目录并按用户意图执行 dry-run 或安装。
def main() -> None:
    """解析安装参数并执行版本化发布包安装流程。

    参数：无，命令行参数由当前进程读取。
    返回：无业务返回值，结果通过 JSON 标准输出返回。
    异常：发布验证失败或安装复制失败时抛出 SystemExit。
    """

    # 当前命令行参数决定发布目录、目标和写入意图。
    object_arguments = build_argument_parser().parse_args()  # 当前安装命令行参数。

    # 发布目录规范化后作为验证和复制的统一来源。
    path_release_directory = resolve_project(object_arguments.release_dir)  # 待验证版本化发布目录。

    # 发布验证覆盖收据、内容策略、源码状态和完整性。
    dict_validation = validate_release_dir(path_release_directory)  # 当前发布包验证结果。

    # 任一验证错误都必须在文件复制之前阻断。
    if dict_validation["errors"]:

        # 原始验证载荷提供完整失败证据。
        emit_json(dict_validation)

        # 发布包无效时向调用进程返回失败。
        raise SystemExit(1)

    # 安装目标由技能名、目标类型和可选根目录共同解析。
    path_destination = target_path(  # 当前安装目标目录或 skip 空值。
        dict_validation["skill_name"],  # 验证得到的技能名称。
        object_arguments.target,  # skip、codex 或 custom 目标类型。
        object_arguments.codex_home,  # 可选 Codex 根目录覆盖。
        object_arguments.custom_root,  # 可选自定义安装根目录。
    )  # 解析最终安装目标。

    # 初始结果同时支撑 dry-run 和后续真实复制。
    dict_result = build_install_result(  # 当前安装流程共享结果载荷。
        path_release_directory,  # 当前版本化发布目录。
        dict_validation,  # 完整发布包验证证据。
        object_arguments,  # 提供目标类型、意图和写入开关的参数对象。
        path_destination,  # 可选实际目标目录。
    )  # 构造 dry-run 和安装共享载荷。

    # 未确认安装时向结果追加结构化选择。
    add_confirmation_request(dict_result, path_release_directory, object_arguments)

    # dry-run 或 skip 目标只输出验证结果，不写入文件系统。
    if object_arguments.target == "skip" or not object_arguments.write:

        # 当前结果明确保持 installed=false 和 skipped=true。
        emit_json(dict_result)

        # dry-run 正常完成后结束安装入口。
        return

    # 前述分支已排除 skip，目标路径可安全收窄为 Path。
    path_required_destination = cast(Path, path_destination)  # 已确认写入的实际安装目标。

    # 已确认写入时执行备份、复制和最终结果输出。
    execute_install(
        path_release_directory,  # 复制阶段读取内容的版本化来源目录。
        path_required_destination,  # 已确认安装目标目录。
        object_arguments.replace,  # 是否替换现有技能。
        dict_result,  # 安装阶段共享结果载荷。
    )

# 直接执行模块时启动技能安装 CLI。
if __name__ == "__main__":

    # 主入口负责所有结构化输出和退出状态。
    main()
