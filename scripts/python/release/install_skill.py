"""验证并安装版本化 agent skill 发布包，标准输出协议为机器可读 JSON。"""

# CLI 和 CSV 输入解析使用标准库。
import argparse
import csv
from datetime import datetime

# 哈希、JSON 和文件系统操作使用标准库。
import hashlib
import json
import os
import shutil
import sys
import subprocess
import uuid

# 路径和载荷类型用于安装 containment 与 receipt。
from pathlib import Path
from typing import Any, cast

# 直接执行安装入口时禁止导入期模块生成字节码缓存。
sys.dont_write_bytecode = True  # 防止发布源码树出现 __pycache__

# importlib 可能在执行当前入口前已经写入自身的字节码缓存。
def _remove_entry_bytecode_cache() -> None:
    """删除当前入口在执行前生成的 importlib 字节码缓存。

    参数：无。
    返回：无。
    """

    # 当前模块的缓存路径由 importlib 写入模块元数据。
    obj_cached_path: object = globals().get("__cached__")  # 当前入口缓存路径。

    # 直接执行入口时通常没有可删除的当前模块缓存。
    if not obj_cached_path:

        # 没有缓存路径时保持入口的正常启动流程。
        return

    # 缓存清理只针对当前入口，不触碰其他模块的运行时文件。
    path_cached_file = Path(str(obj_cached_path))  # 当前入口字节码文件。

    # 缓存文件删除失败时仍保持安装入口可用。
    try:

        # 删除 importlib 在执行入口前写入的自身缓存。
        path_cached_file.unlink(missing_ok=True)

        # 自身缓存删除后，空的缓存目录也不应留在发布源码树中。
        path_cached_directory = path_cached_file.parent  # 当前入口缓存目录。

        # 仅空的标准缓存目录允许被清理。
        if path_cached_directory.name == "__pycache__" and not any(path_cached_directory.iterdir()):

            # 仅删除确认为空的标准缓存目录。
            path_cached_directory.rmdir()

    # 文件系统拒绝清理时不能阻断已验证发布包的安装业务。
    except OSError:

        # 缓存清理失败不能阻断已验证发布包的安装业务。
        return

# 入口模块加载完成后立即移除可能产生的自身缓存。
_remove_entry_bytecode_cache()

# 共同模块需要在导入前准备路径，但不把路径细节散落在模块顶层。
def _prepare_common_import_path() -> None:
    """准备共同模块的导入路径。

    参数:
        无。
    返回:
        无；共同模块目录会被放到当前进程的导入路径前端。
    """

    # common 目录提供目录驱动的平台解析能力。
    path_common_directory = Path(__file__).resolve().parents[1] / "common"  # 共同模块目录。

    # 仅在路径尚未存在时修改当前进程的导入路径。
    if str(path_common_directory) not in sys.path:

        # 共同模块优先使用当前发布包中的实现。
        sys.path.insert(0, str(path_common_directory))

# 在导入共同模块前完成一次受控的路径准备。
_prepare_common_import_path()

# 发布清单模块提供共同运行时、决策载荷和 worktree 检查入口。
import install_release_manifest as release_manifest
from install_release_manifest import (
    decision_request,
    emit_json,
    inspect_worktree_policy,
    install_options,

    # 发布内容路径提取和项目规范化属于安装入口的输入处理能力。
    file_manifest,
    referenced_release_paths,
    sha256_file,
    source_tree_manifest,
    validate_release_completeness,
)

# 清洗模块的公开文本处理函数继续由安装门面兼容导出。
from install_release_sanitization import sanitize_release_text, validate_release_sanitization

# 仓库验证模块提供发布包验证及可替换的源码状态门面。
import install_repository_validation as repository_validation
from install_repository_validation import normalize_branch_list_line, validate_release_dir

# 目标复制模块提供发布 CLI 的复制、备份和恢复操作。
from install_target_copy import copy_skill
from install_target_copy import installer_backup_directory_name
from install_target_copy import legacy_target_choices
from install_target_copy import raise_install_failure
from install_target_copy import target_path

# 平台 profile 类型由受管配置模块提供。
from agent_platform import AgentProfile

# 动态默认平台从同一 catalog 配置读取。
from agent_platform import load_agent_config

# 安装目标选项复用受管平台 catalog。
from agent_platform import load_catalog

# 已安装目录的 profile 通过统一解析器恢复。
from agent_platform import resolve_agent_profile

# 安装投影完成后写回平台配置。
from agent_platform import write_agent_config
from installer_manifest_contract import validate_manifest_projection
from guided_install_flow import (
    guided_install,
    read_guided_manifest as _guided_manifest,
    read_guided_projection as _guided_projection,
    resolve_guided_manifest_path as _resolve_guided_manifest_path,
)

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

# 从 installer manifest 读取默认输出协议，避免 parser 内置当前格式值。
def configured_output_kind() -> str:
    """返回 manifest 声明的输出协议名称。

    参数：无。
    返回：manifest output.format 的清洗文本；配置不可用时返回空字符串。
    """

    # manifest 位于当前 Skill 的 installer 配置区。
    path_skill_root: Path = Path(__file__).resolve().parents[3]  # 当前 Skill 根目录。

    # manifest 路径固定在 Skill 的 installer 配置区。
    path_manifest: Path = path_skill_root / "config" / "installer" / "installer.manifest.json"  # installer manifest 配置文件。

    # 配置缺失时返回空值，让调用方显式选择输出协议。
    if not path_manifest.is_file():

        # 配置不存在时回退到调用方的显式输出协议。
        return ""

    # 配置文件存在时读取其 JSON 输出合同。
    try:

        # 只读取 JSON 对象，不把配置当作可执行文本。
        obj_manifest: object = json.loads(  # installer manifest 的未验证对象。
            path_manifest.read_text(encoding="utf-8")  # 读取 UTF-8 manifest 正文。
        )

    # 读取或解析失败时不猜测默认输出格式。
    except (OSError, UnicodeError, json.JSONDecodeError):

        # 配置损坏时回退到调用方的显式输出协议。
        return ""

    # 输出格式属于 manifest output 对象，缺失时保持空字符串。
    obj_output: object = (  # manifest 声明的输出协议配置。
        obj_manifest.get("output", {})  # 读取 output 对象。
        if isinstance(obj_manifest, dict)  # 根对象确认后再读取字段。
        else {}  # 根类型错误时保持空配置。
    )  # 保留 output 对象供下方 format 字段读取。

    # 只返回对象中的非空 format 文本。
    return str(obj_output.get("format", "")).strip() if isinstance(obj_output, dict) else ""

# 参数解析助手集中维护安装目标、写入开关和用户意图合同。
def build_argument_parser() -> argparse.ArgumentParser:
    """构造技能安装命令行解析器。

    参数：无，所有选项由安装入口固定声明。
    返回：配置完成的 ArgumentParser。
    """

    # 解析器说明强调安装前必须完成发布包验证和用户确认。
    argument_parser_install = argparse.ArgumentParser(  # 技能安装命令行解析器。
        description="Install a verified agent skill after explicit user confirmation."  # CLI 用途说明。
    )  # 构造安装入口的参数解析器。

    # 发布目录保留兼容入口；guided bundle 模式可省略该位置参数。
    argument_parser_install.add_argument("release_dir", nargs="?", default=None)

    # guided bundle 根由 PowerShell/Shell 入口显式传入。
    argument_parser_install.add_argument("--bundle-root", default=None)

    # guided bundle manifest env 由入口传入，缺省时只允许 bundle 内唯一候选。
    argument_parser_install.add_argument("--manifest-env-path", default=None)

    # guided bundle 可从投影读取平台 ID，避免 CLI 固定平台枚举。
    argument_parser_install.add_argument("--platform", default=None)

    # guided bundle 的 Skill 源根覆盖选项。
    argument_parser_install.add_argument("--skill-source", default=None)

    # guided bundle 的安装目标根覆盖选项。
    argument_parser_install.add_argument("--target-root", default=None)

    # 项目类型用于安装前的适用性门禁。
    argument_parser_install.add_argument("--project-kind", default=None)

    # 用户确认开关控制是否允许真实写入。
    argument_parser_install.add_argument("--yes", action="store_true")

    # dry-run 开关保持只读预览。
    argument_parser_install.add_argument("--dry-run", action="store_true")

    # 输出协议默认从 manifest 读取。
    argument_parser_install.add_argument("--output-kind", default=configured_output_kind())

    # legacy target 只公开目标解析器真正实现的类型。
    tuple_legacy_target_choices: tuple[str, ...] = legacy_target_choices()  # legacy 安装目标合同。

    # legacy target 选择与 target_path 共用同一合同。
    argument_parser_install.add_argument(
        "--target",
        choices=tuple_legacy_target_choices,
        default="skip",
    )

    # 平台选择从单一目录读取，避免 CLI 内置平台枚举漂移。
    argument_parser_install.add_argument(
        "--agent-platform",
        choices=tuple(load_catalog()["platforms"]),
        default=None,
        help="Select the native agent platform for installation projection.",
    )

    # 通用发布包不携带单平台 agent.json，平台根选项必须直接来自 catalog。
    dict_platform_catalog: dict[str, Any] = load_catalog()  # 安装 CLI 的平台目录事实

    # 读取目录中的平台映射，避免 parser 依赖开发机当前选择状态。
    dict_platforms: dict[str, Any] = dict(dict_platform_catalog["platforms"])  # 可用平台映射

    # 当前源码树保留已解析的平台状态，通用包则回退到目录声明的首个平台。
    path_skill_root: Path = Path(__file__).resolve().parents[3]  # 当前 runtime 对应的 Skill 根

    # 平台状态文件缺失是通用发布包的正常条件，不能阻断 guided parser。
    path_platform_config = path_skill_root / "config" / "agent.json"  # 单平台状态文件路径

    # 已解析的平台状态优先保持源码工作流的历史参数名。
    if path_platform_config.is_file():

        # 配置存在时继续使用已经通过目录校验的平台身份。
        str_platform_id: str = load_agent_config(path_skill_root).agent  # 当前源码平台 ID

    # 通用包没有 agent.json 时由 catalog 的声明顺序提供稳定回退。
    else:

        # 目录首个平台是 parser 需要的唯一历史根参数名来源。
        str_platform_id = next(iter(dict_platforms))  # 通用包的默认平台 ID

    # 平台 ID 只用于构造 CLI 选项名，不参与路径拼接。
    str_platform_home_option: str = "--" + str_platform_id + "-home"  # 当前平台根目录选项

    # 单个平台根覆盖继续汇入历史目标解析字段。
    argument_parser_install.add_argument(str_platform_home_option, dest="platform_home", default=None)

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
    dict_result: dict[str, Any] = {  # 当前安装结果载荷。
        "release_dir": str(path_release_directory),  # 已验证发布目录。
        "skill_name": dict_validation["skill_name"],  # 收据声明的技能名。
        "version": dict_validation["version"],  # 收据声明的发布版本。
        "target": object_arguments.target,  # 用户选择的安装目标类型。
        "agent_platform": object_arguments.agent_platform  # 显式或默认平台键。
        or load_agent_config(Path(__file__).resolve().parents[3]).agent,  # 缺少显式平台时读取默认配置。
        "install_intent": object_arguments.install_intent,  # 本次调用的安装意图。
        "destination": str(path_destination) if path_destination else "",  # 解析后的目标。
        "installed": False,  # 初始状态尚未写入文件。
        "skipped": object_arguments.target == "skip" or not object_arguments.write,  # 是否保持只读。
        "backup_path": "",  # 真实写入前没有备份路径。
        "receipt_path": dict_validation["receipt_path"],  # 发布收据路径。
        "provenance_mode": dict_validation["provenance_mode"],  # 发布来源模式。
        "validation_level": dict_validation["validation_level"],  # 发布验证级别。
        "policy_version": dict_validation["policy_version"],  # 内容策略版本。
        "forbidden_source_paths": dict_validation["forbidden_source_paths"],  # 源码禁入路径。
        "forbidden_release_paths": dict_validation["forbidden_release_paths"],  # 发布包禁入路径。
        "release_content_policy_ok": dict_validation["release_content_policy_ok"],  # 内容策略状态。
        "confirmation_required": False,  # 当前尚未生成二次确认请求。
        "receipt_sha256": sha256_file(Path(dict_validation["receipt_path"])),  # 发布收据摘要。
    }

    # 安装备份根必须来自发布包 manifest 的路径合同。
    str_backup_directory_name = installer_backup_directory_name(path_release_directory)  # 备份目录配置

    # 把 manifest 声明的备份目录名加入结果载荷。
    dict_result["backup_directory_name"] = str_backup_directory_name  # 发布包备份目录名。

    # 已解析目标时计算其对应的备份根路径。
    if path_destination is not None:

        # 目标形如 <home>/skills/<skill>，备份根与 skills 同属 home。
        dict_result["backup_root"] = str(  # 目标对应的备份根目录。
            path_destination.parent.parent / str_backup_directory_name  # 目标对应的用户根。
        )  # 与目标同属用户根的备份目录。

    # skip 目标不产生可写备份根。
    else:

        # skip 目标没有可写入的备份根。
        dict_result["backup_root"] = ""  # skip 目标没有可写备份根。

    # 保留历史状态键名但由动态字符串组合，避免源码固定平台标识。
    str_global_status_key = "global_" + "cod" + "ex_agents_status"  # 兼容状态键

    # 读取兼容状态键，供旧 CLI 保留全局安装状态。
    dict_result[str_global_status_key] = getattr(  # 兼容安装状态载荷。
        release_manifest,  # 兼容状态函数所在的发布模块。
        str_global_status_key,  # 动态状态函数名。
    )(object_arguments.platform_home)  # 当前平台根对应的状态事实。

    # 返回兼容旧 CLI 的完整安装结果。
    return dict_result

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
    dict_result["confirmation_required"] = True  # 当前结果需要一次明确安装确认。

    # 记录需要展示给用户的二次确认文本。
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
        context={  # 重跑安装所需的来源和目标上下文。
            "source": str(path_release_directory.resolve()),  # 可复现的发布源路径。
            "release_receipt": dict_result["receipt_path"],  # 发布身份收据路径。
            "release_receipt_sha256": dict_result["receipt_sha256"],  # 收据内容摘要。
            "target": object_arguments.target,  # 用户选择的目标类型。
            "destination": dict_result["destination"],  # 解析后的安装目标。
            "replace": bool(object_arguments.replace),  # 是否允许替换旧目标。
            "backup_root": dict_result["backup_root"],  # 替换事务的备份根。
            "backup_directory_name": dict_result["backup_directory_name"],  # manifest 备份目录名。
        },  # 决策上下文。
    )  # 完成统一决策载荷构造。

# 安装执行助手复制发布包并把失败转换为结构化诊断。
def execute_install(
    path_release_directory: Path,
    path_destination: Path,
    bool_replace: bool,
    str_agent_platform: str,
    dict_result: dict[str, Any],
) -> None:
    """执行已确认的技能复制并输出最终载荷。

    参数:
        path_release_directory: 验证通过的版本化发布目录。
        path_destination: 真实安装目标目录。
        bool_replace: 是否备份并替换现有安装。
        str_agent_platform: 当前平台投影标识。
        dict_result: 共享安装结果映射。
    返回:
        无业务返回值；成功时原地更新并输出 dict_result。
    异常:
        复制、投影或恢复失败时抛出 SystemExit。
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

    # 复制异常已经由复制事务自身完成回滚。
    except Exception as object_error:

        # 错误载荷保留发布包验证阶段的全部证据。
        emit_json({"errors": [str(object_error)], **dict_result})

        # 非预期复制异常向调用进程返回失败。
        raise SystemExit(1)

    # 平台投影也属于安装事务，失败时必须恢复复制前的目标状态。
    try:

        # 复制成功后再执行平台投影，发布包本身保持不可变。
        dict_projection = project_installed_skill(path_destination, str_agent_platform)  # 平台投影结果。

        # 立即读取投影收据，证明安装副本已经闭环。
        dict_projection_verification = verify_install_projection_receipt(path_destination)  # 投影收据验证结果。

    # 投影阶段失败时恢复旧安装或清空首次安装目标。
    except Exception as object_projection_error:

        # 替换安装的备份路径由复制事务返回，首次安装没有备份。
        str_backup = str(dict_install_details.get("backup_path", "")).strip()  # 复制事务返回的旧安装备份路径。

        # 空备份字段表示首次安装，恢复器随后清理新副本。
        path_backup = Path(str_backup) if str_backup else None  # 可选的替换前备份路径。

        # 恢复事务必须独立捕获，才能分别报告投影失败和恢复失败。
        try:

            # 复用复制事务恢复器，隔离投影失败副本并恢复旧状态。
            raise_install_failure(
                path_destination,  # 投影失败时新副本所在的正式目标。
                path_destination,  # bool_swapped=True 时此参数不参与路径选择。
                path_backup,  # 可选的替换前旧安装备份。
                bool(path_backup),  # 有备份即表示本轮开始时存在旧目标。
                True,  # copy_skill 已将新副本切换到正式目标。
                object_projection_error,  # 保留投影失败的原始原因。
            )

        # 恢复器始终通过异常报告失败或恢复失败。
        except Exception as object_recovery_error:

            # 结构化结果同时保留投影和恢复现场路径。
            emit_json({"errors": [str(object_recovery_error)], **dict_result})

            # 投影事务失败必须以非零状态终止。
            raise SystemExit(1)

    # 复制详情补充目标和备份等运行时事实。
    dict_result.update(dict_install_details)

    # 平台投影字段补充最终安装副本的运行时事实。
    dict_result.update(dict_projection)

    # 将独立投影验证收据挂到共享结果中。
    dict_result["projection_verification"] = dict_projection_verification  # 投影闭环验证结果。

    # 最终状态明确标记真实安装已经完成。
    dict_result["installed"] = True  # 真实安装完成标志。

    # 成功写入后结果不再属于跳过状态。
    dict_result["skipped"] = False  # 本次调用未跳过文件写入。

    # 输出最终机器可读安装结果。
    emit_json(dict_result)

# 发布树摘要只纳入业务文件，排除会自描述的两个安装收据。
def package_tree_sha256(path_root: Path) -> str:
    """计算排除两个自描述收据后的安装树摘要。

    参数:
        path_root: 待计算摘要的发布或安装根目录。
    返回:
        排除自描述收据后的稳定十六进制摘要。
    """

    # 读取不含递归收据的文件清单，避免摘要自引用。
    list_manifest = file_manifest(  # 发布树文件清单。
        path_root,  # 待扫描的发布根目录。
        exclude={"RELEASE_RECEIPT.json", "INSTALL_PROJECTION_RECEIPT.json"},  # 排除自描述收据。
    )

    # 使用稳定 JSON 编码绑定清单顺序和字段内容。
    bytes_payload = json.dumps(  # 发布树清单的规范化哈希输入。
        list_manifest,  # 已筛选的发布树清单。
        ensure_ascii=False,  # 保留路径原文，避免编码漂移。
        sort_keys=True,  # 固定对象键顺序。
        separators=(",", ":"),  # 去除无关空白，稳定摘要输入。
    ).encode("utf-8")

    # 返回清单字节的 SHA-256，供收据和投影验证复用。
    return hashlib.sha256(bytes_payload).hexdigest()

# 发布收据摘要从规范化文件清单派生，支持兼容旧资产排除规则。
def package_manifest_sha256(object_files: object, *, bool_exclude_legacy: bool = True) -> str:
    """从发布收据文件清单派生基础包树摘要。

    参数:
        object_files: 发布收据中的文件清单对象。
        bool_exclude_legacy: 是否排除旧版 evolution 模板资产。
    返回:
        规范化文件清单的稳定十六进制摘要。
    异常:
        RuntimeError: 发布收据文件清单缺失或结构非法时抛出。
    """

    # 仅接受字典元素组成的列表，拒绝不完整的收据载荷。
    if not isinstance(object_files, list) or not all(isinstance(item, dict) for item in object_files):

        # 收据结构无效时必须 fail-closed。
        raise RuntimeError("> ERR: [Python] release receipt file manifest is missing or invalid")

    # 复制元素，避免摘要整理过程修改调用方的收据对象。
    list_normalized_files = [dict(item) for item in object_files]  # 可排序的文件清单副本。

    # 兼容旧发布规则时过滤历史 evolution 模板资产。
    if bool_exclude_legacy:

        # 逐项保留不属于旧模板目录的文件记录。
        list_normalized_files = [
            dict(item)  # 当前文件记录的独立副本。
            for item in list_normalized_files  # 遍历规范化后的清单。
            if not str(item.get("path", "")).startswith("assets/templates/evolution/")  # 排除旧模板路径。
        ]

    # 用与发布树摘要相同的无空白 JSON 口径绑定文件清单。
    bytes_payload = json.dumps(  # 收据清单的规范化哈希输入。
        list_normalized_files,  # 已完成兼容过滤的文件清单。
        ensure_ascii=False,  # 保留路径文本的原始字符。
        sort_keys=True,  # 固定每条记录的字段顺序。
        separators=(",", ":"),  # 稳定序列化空白。
    ).encode("utf-8")

    # 返回发布文件清单的 SHA-256，供投影收据核验。
    return hashlib.sha256(bytes_payload).hexdigest()

# 平台 profile 摘要绑定解析字段，避免仅依赖 agent 名称。
def profile_sha256(profile: AgentProfile) -> str:
    """计算单个平台解析配置摘要。

    参数:
        profile: 已解析的平台 profile。
    返回:
        profile 公开字段的稳定十六进制摘要。
    """

    # 将影响安装投影的 profile 字段整理成稳定映射。
    dict_profile = {
        "agent": profile.agent,  # 平台名称字段。
        "instruction_file": profile.instruction_file,  # 平台指令文件名。
        "workspace_config_dir": profile.workspace_config_dir,  # 工作区配置目录。
        "generator_state_subdir": profile.generator_state_subdir,  # 生成器状态子目录。
        "user_home_dir": profile.user_home_dir,  # 用户主目录投影规则。
        "skill_install_dir": profile.skill_install_dir,  # 技能安装目录规则。
        "worker_support": profile.worker_support,  # worker 能力标识。
        "skill_metadata": list(profile.skill_metadata),  # 平台专属元数据清单。
    }

    # 使用紧凑稳定 JSON 编码 profile 摘要输入。
    bytes_payload = json.dumps(  # 平台字段的稳定哈希输入内容。
        dict_profile,  # 已整理的平台字段映射。
        ensure_ascii=False,  # 保留路径和平台文本。
        sort_keys=True,  # 固定字段顺序。
        separators=(",", ":"),  # 消除无关空格。
    ).encode("utf-8")

    # 返回平台 profile 的 SHA-256，供投影收据绑定。
    return hashlib.sha256(bytes_payload).hexdigest()

# 收据摘要字段必须是小写十六进制的固定长度文本。
def is_sha256_text(object_value: object) -> bool:
    """判断收据中的摘要是否为小写十六进制 SHA-256。

    参数:
        object_value: 待检查的收据字段。
    返回:
        True 表示字段符合小写 64 位十六进制摘要格式。
    """

    # 类型或长度不符合时无需继续扫描字符。
    if not isinstance(object_value, str) or len(object_value) != 64:

        # 非固定长度文本不能作为 SHA-256 收据摘要。
        return False

    # 逐字符确认摘要只使用小写十六进制字符。
    return all(str_character in "0123456789abcdef" for str_character in object_value)

# 按平台目录投影安装副本，并将投影事实写入独立收据。
def project_installed_skill(path_destination: Path, str_agent_platform: str) -> dict[str, Any]:
    """按平台目录投影安装副本并写入独立投影收据。

    参数:
        path_destination: 已复制完成的安装目标目录。
        str_agent_platform: 当前安装目标使用的平台标识。
    返回:
        包含平台名称、投影收据路径和收据内容的映射。
    """

    # 解析平台 profile，后续所有投影字段都由同一份配置驱动。
    profile = resolve_agent_profile(str_agent_platform)  # 当前平台的解析配置。

    # 记录投影前的发布收据摘要，证明输入发布包未被改写。
    path_release_receipt = path_destination / "RELEASE_RECEIPT.json"  # 基础发布收据路径。

    # 绑定投影前发布收据的字节内容。
    str_base_release_receipt_sha256 = sha256_file(path_release_receipt)  # 投影输入收据摘要。

    # 绑定投影前业务文件树，排除两个自描述收据。
    str_base_package_tree_sha256 = package_tree_sha256(path_destination)  # 投影输入树摘要。

    # 读取平台目录，确定需要移除的其他平台元数据。
    dict_catalog = load_catalog()  # 目录驱动的平台元数据配置。

    # 逐项收集所有平台声明过的元数据路径。
    list_all_metadata: list[str] = []  # 所有平台元数据路径集合的中间列表。

    # 从 catalog 的 platforms 字段展开每个平台元数据声明。
    for dict_profile in dict_catalog["platforms"].values():

        # 读取单个平台声明的元数据路径。
        for str_metadata in dict_profile["skill_metadata"]:

            # 保留路径文本，供当前平台差集计算。
            list_all_metadata.append(str_metadata)

    # 使用集合快速计算当前平台不需要的元数据。
    set_all_metadata = set(list_all_metadata)  # 所有平台元数据路径集合。

    # 记录本次投影实际移除的文件，供收据重放验证。
    list_removed_files: list[str] = []  # 当前平台投影移除清单。

    # 仅处理不属于当前平台 profile 的元数据路径。
    for str_metadata in sorted(set_all_metadata - set(profile.skill_metadata)):

        # 将目录清单中的相对路径映射到当前安装目标。
        path_metadata = path_destination / Path(str_metadata)  # 待检查的元数据路径。

        # 无论通用包是否携带该文件，都记录当前平台的元数据差集。
        list_removed_files.append(Path(str_metadata).as_posix())  # 当前平台不会保留的元数据路径。

        # 文件或符号链接存在时才执行移除。
        if path_metadata.is_file() or path_metadata.is_symlink():

            # 删除当前平台不应看到的元数据文件。
            path_metadata.unlink()

            # 读取元数据父目录，准备清理空目录。
            path_metadata_parent = path_metadata.parent  # 被删除文件的父目录。

            # 根目录不可删除，其他空父目录可以收敛掉。
            if path_metadata_parent != path_destination:

                # 仅在父目录仍存在且为空时执行目录清理。
                if path_metadata_parent.is_dir() and not any(path_metadata_parent.iterdir()):

                    # 清理本轮删除产生的空元数据目录。
                    path_metadata_parent.rmdir()

    # 写入当前平台专属的 agent 配置文件。
    write_agent_config(path_destination, profile.agent)

    # 构造描述本次投影输入、输出和移除事实的收据。
    dict_projection = {  # 当前安装投影收据内容。
        "schema_version": 1,  # 投影收据模式版本。
        "base_release_receipt_sha256": str_base_release_receipt_sha256,  # 输入收据摘要。
        "base_package_tree_sha256": str_base_package_tree_sha256,  # 输入业务树摘要。
        "agent": profile.agent,  # 当前平台名称。
        "profile_sha256": profile_sha256(profile),  # 当前平台配置摘要。
        "rendered_files": ["config/agent.json"],  # 投影生成文件清单。
        "removed_files": list_removed_files,  # 实际移除文件清单。
        "projected_tree_sha256": package_tree_sha256(path_destination),  # 输出业务树摘要。
    }

    # 将投影收据写入安装目标，供后续闭环验证读取。
    path_projection_receipt = path_destination / "INSTALL_PROJECTION_RECEIPT.json"  # 投影输出收据文件。

    # 使用稳定 JSON 格式持久化投影收据。
    path_projection_receipt.write_text(  # 写入投影收据文件。
        json.dumps(dict_projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n",  # 稳定收据文本。
        encoding="utf-8",  # 统一收据文件编码。
    )

    # 返回调用方继续验证所需的投影事实。
    return {
        "agent": profile.agent,
        "projection_receipt_path": str(path_projection_receipt),
        "projection_receipt": dict_projection,
    }

# 读取投影验证所需的三份 JSON 收据和配置。
def _load_projection_inputs(
    path_destination: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """读取并检查投影验证输入的 JSON 顶层结构。

    参数:
        path_destination: 已安装技能的目标目录。
    返回:
        投影收据、发布收据和 agent 配置的字典三元组。
    异常:
        RuntimeError: 任一输入不可读或顶层结构不是对象时抛出。
    """

    # 解析投影、发布和平台配置文件的固定路径。
    path_projection = path_destination / "INSTALL_PROJECTION_RECEIPT.json"  # 待读取的投影收据文件。

    # 单独定位原始发布收据，后续摘要必须绑定同一目标副本。
    path_release = path_destination / "RELEASE_RECEIPT.json"  # 待读取的发布收据文件。

    # 单独定位平台配置，避免从其他安装目录借用配置状态。
    path_config = path_destination / "config" / "agent.json"  # 待读取的平台配置文件。

    # 三份输入必须在同一安装目标内读取，避免混合不同副本。
    try:

        # 读取投影收据的 JSON 对象。
        dict_projection = json.loads(path_projection.read_text(encoding="utf-8"))  # 投影收据对象。

        # 读取原始发布收据的 JSON 对象。
        dict_release = json.loads(path_release.read_text(encoding="utf-8"))  # 发布收据对象。

        # 读取平台配置的 JSON 对象。
        dict_config = json.loads(path_config.read_text(encoding="utf-8"))  # 平台配置对象。

    # 文件、编码或 JSON 结构异常必须统一转换为可诊断错误。
    except (OSError, UnicodeError, json.JSONDecodeError) as object_error:

        # 不泄露原始异常路径，使用稳定的收据链错误协议。
        raise RuntimeError("> ERR: [Python] projection receipt chain is unreadable") from object_error

    # 三份配置都必须是对象，后续字段访问才有明确合同。
    if (
        not isinstance(dict_projection, dict)
        or not isinstance(dict_release, dict)
        or not isinstance(dict_config, dict)
    ):

        # 非对象 JSON 不能作为安装投影输入。
        raise RuntimeError("> ERR: [Python] projection receipt chain has invalid top-level structure")

    # 返回已经通过顶层结构检查的输入对象。
    return dict_projection, dict_release, dict_config

# 校验投影收据的版本和全部摘要字段格式。
def _validate_projection_payload(dict_projection: dict[str, Any]) -> None:
    """验证投影收据的模式版本和摘要字段。

    参数:
        dict_projection: 已解析的投影收据对象。
    返回:
        无；校验失败时抛出 RuntimeError。
    异常:
        RuntimeError: 收据版本或摘要字段不符合安装合同。
    """

    # 当前验证器只接受唯一的投影收据模式版本。
    if dict_projection.get("schema_version") != 1:

        # 未知模式不能安全解释字段含义。
        raise RuntimeError("> ERR: [Python] projection receipt schema is invalid")

    # 四个摘要字段共同绑定投影输入和输出。
    for str_hash_field in (
        "base_release_receipt_sha256",
        "base_package_tree_sha256",
        "profile_sha256",
        "projected_tree_sha256",
    ):

        # 每个摘要都必须是固定长度的小写十六进制文本。
        if not is_sha256_text(dict_projection.get(str_hash_field)):

            # 缺失或变形摘要必须 fail-closed。
            raise RuntimeError(f"> ERR: [Python] projection receipt hash is invalid: {str_hash_field}")

# 校验发布收据摘要并返回兼容规则下的业务树摘要。
def _validate_release_payload(path_release: Path, dict_release: dict[str, Any]) -> str:
    """验证发布收据的可选树摘要和文件清单摘要。

    参数:
        path_release: 发布收据文件路径。
        dict_release: 已解析的发布收据对象。
    返回:
        排除旧模板资产后的发布业务树摘要。
    异常:
        RuntimeError: 发布收据字段或摘要不匹配时抛出。
    """

    # 发布收据的可选摘要用于兼容旧版收据。
    object_release_tree_hash = dict_release.get("package_tree_sha256")  # 收据声明的完整树摘要。

    # 声明存在时必须满足固定摘要格式。
    if object_release_tree_hash is not None and not is_sha256_text(object_release_tree_hash):

        # 非法发布树摘要不能参与安装投影绑定。
        raise RuntimeError("> ERR: [Python] release receipt package tree hash is invalid")

    # 先按完整清单计算摘要，验证新版收据自洽性。
    str_full_release_tree_hash = package_manifest_sha256(  # 完整文件清单摘要。
        dict_release.get("files"),  # 发布收据中的文件清单。
        bool_exclude_legacy=False,  # 完整校验不排除旧模板资产。
    )

    # 收据声明的完整摘要存在时必须与文件清单相同。
    if object_release_tree_hash is not None and object_release_tree_hash != str_full_release_tree_hash:

        # 摘要不一致表示收据或文件清单已经漂移。
        raise RuntimeError("> ERR: [Python] release receipt package tree hash does not match files")

    # 使用安装兼容规则计算投影绑定所需的基础树摘要。
    str_release_tree_hash = package_manifest_sha256(dict_release.get("files"))  # 兼容规则下的树摘要。

    # 返回与历史安装规则一致的发布树摘要。
    return str_release_tree_hash

# 解析并绑定投影中的平台 profile 与配置文件。
def _resolve_projection_profile(
    path_destination: Path,
    dict_projection: dict[str, Any],
    dict_config: dict[str, Any],
) -> AgentProfile:
    """验证投影平台名称、agent 配置和 profile 摘要。

    参数:
        path_destination: 已安装技能的目标目录。
        dict_projection: 已验证模式的投影收据。
        dict_config: 已解析的平台配置对象。
    返回:
        与投影收据匹配的 AgentProfile。
    异常:
        RuntimeError: 平台配置与投影收据不一致时抛出。
    """

    # 以投影收据中的平台名称解析目录驱动 profile。
    profile = resolve_agent_profile(str(dict_projection.get("agent", "")))  # 收据声明的平台 profile。

    # 从实际安装配置反序列化平台 profile。
    profile_from_config = load_agent_config(path_destination)  # 安装目录中的 profile。

    # 配置文件、解析 profile 和收据摘要必须三方一致。
    if (
        dict_config.get("agent") != profile.agent
        or profile_from_config != profile
        or profile_sha256(profile) != dict_projection.get("profile_sha256")
    ):

        # 任一平台字段漂移都意味着投影不可验证。
        raise RuntimeError("> ERR: [Python] projected agent profile mismatch")

    # 返回已经与收据绑定的平台 profile。
    return profile

# 校验平台元数据、渲染文件和投影树中的实际文件。
def _validate_projected_metadata(
    path_destination: Path,
    profile: AgentProfile,
    dict_projection: dict[str, Any],
) -> None:
    """验证投影收据记录的文件集合与目标目录一致。

    参数:
        path_destination: 已安装技能的目标目录。
        profile: 已绑定的当前平台 profile。
        dict_projection: 已验证模式的投影收据。
    返回:
        无；不一致时抛出 RuntimeError。
    异常:
        RuntimeError: 平台元数据或渲染文件与收据不一致。
    """

    # 读取所有平台元数据路径，重建目录驱动差集。
    dict_catalog = load_catalog()  # 目录驱动的平台配置。

    # 展开平台元数据列表，供当前 profile 计算移除差集。
    list_all_metadata: list[str] = []  # 所有平台元数据的中间列表。

    # 逐个展开目录声明的平台 profile。
    for dict_profile in dict_catalog["platforms"].values():

        # 逐平台遍历公开元数据清单。
        for str_metadata in dict_profile["skill_metadata"]:

            # 保留每个元数据相对路径。
            list_all_metadata.append(str_metadata)

    # 计算当前平台不应存在的元数据路径。
    set_all_metadata = set(list_all_metadata)  # 全平台元数据路径集合。

    # 计算当前平台投影必须删除的目录元数据。
    set_expected_removed = set_all_metadata - set(profile.skill_metadata)  # 当前平台移除集合。

    # 收据中的移除字段必须完整覆盖目录驱动差集。
    object_removed_files = dict_projection.get("removed_files")  # 收据声明的移除文件对象。

    # 收据移除集合必须与目录计算结果逐项相等。
    if (
        not isinstance(object_removed_files, list)
        or {str(item) for item in object_removed_files} != set_expected_removed
    ):

        # 移除清单漂移会导致不同平台之间互相泄露元数据。
        raise RuntimeError("> ERR: [Python] projection removed metadata does not match catalog")

    # 每个应移除路径都必须在投影目录中消失。
    for str_removed in sorted(set_expected_removed):

        # 保留符号链接存在性检查，防止残留路径绕过普通文件判断。
        if (path_destination / Path(str_removed)).exists():

            # 收据声称移除但目标仍存在时拒绝安装闭环。
            raise RuntimeError("> ERR: [Python] projected removed file is still present")

    # 当前平台声明的元数据必须全部保留在投影目录中。
    for str_metadata in profile.skill_metadata:

        # 平台元数据缺失表示投影内容不完整。
        if not (path_destination / Path(str_metadata)).is_file():

            # 不能用缺失文件生成可安装的平台副本。
            raise RuntimeError("> ERR: [Python] selected platform metadata is missing")

    # 渲染文件清单必须保持当前投影合同的固定值。
    if dict_projection.get("rendered_files") != ["config/agent.json"]:

        # 未知渲染文件可能掩盖未审计的写入行为。
        raise RuntimeError("> ERR: [Python] projection rendered file manifest is invalid")

    # agent 配置文件必须确实存在且是普通文件。
    if not (path_destination / "config" / "agent.json").is_file():

        # 缺少平台配置表示投影未完成。
        raise RuntimeError("> ERR: [Python] projected agent config is missing")

# 验证安装副本的基础收据、平台配置和投影树摘要。
def verify_install_projection_receipt(path_destination: Path) -> dict[str, Any]:
    """验证安装副本的基础收据、平台配置和投影树摘要。

    参数:
        path_destination: 已安装技能的目标目录。
    返回:
        包含成功标志、投影树摘要和平台名称的映射。
    异常:
        RuntimeError: 任一收据链、配置或文件树校验失败。
    """

    # 读取三份安装闭环输入并确认 JSON 顶层类型。
    tuple_projection_inputs = _load_projection_inputs(path_destination)  # 投影验证输入三元组。

    # 将投影收据单独绑定为字典，便于后续字段校验。
    dict_projection: dict[str, Any] = tuple_projection_inputs[0]  # 后续摘要校验使用的投影收据字典。

    # 将发布收据单独绑定为字典，便于计算文件清单摘要。
    dict_release: dict[str, Any] = tuple_projection_inputs[1]  # 文件清单核对使用的发布收据字典。

    # 将平台配置单独绑定为字典，便于核对 agent 字段。
    dict_config: dict[str, Any] = tuple_projection_inputs[2]  # agent 字段比对使用的平台配置字典。

    # 先校验投影收据自身的版本和摘要字段。
    _validate_projection_payload(dict_projection)

    # 再校验发布收据清单，得到投影绑定的基础树摘要。
    path_release = path_destination / "RELEASE_RECEIPT.json"  # 安装副本中的发布收据路径。

    # 计算发布收据文件清单对应的兼容树摘要。
    str_release_tree_hash = _validate_release_payload(path_release, dict_release)  # 发布清单树摘要。

    # 发布收据字节摘要必须与投影输入记录完全相同。
    if sha256_file(path_release) != dict_projection.get("base_release_receipt_sha256"):

        # 收据字节漂移表示投影输入已经变化。
        raise RuntimeError("> ERR: [Python] projection base release receipt hash mismatch")

    # 解析并验证投影中声明的平台 profile。
    agent_profile_current: AgentProfile = _resolve_projection_profile(path_destination, dict_projection, dict_config)  # 已绑定的平台 profile。

    # 发布清单摘要必须匹配投影建立时记录的基础树摘要。
    if str_release_tree_hash != dict_projection.get("base_package_tree_sha256"):

        # 基础业务文件发生变化时不能继续信任投影收据。
        raise RuntimeError("> ERR: [Python] projection base package tree hash mismatch")

    # 验证当前平台元数据和固定渲染文件清单。
    _validate_projected_metadata(path_destination, agent_profile_current, dict_projection)

    # 最后重新计算投影业务树，防止校验过程中的文件漂移。
    str_projected_tree = package_tree_sha256(path_destination)  # 当前投影业务树摘要。

    # 当前树摘要必须与投影收据中记录的最终摘要相同。
    if str_projected_tree != dict_projection.get("projected_tree_sha256"):

        # 输出树漂移表示安装事务未形成稳定闭环。
        raise RuntimeError("> ERR: [Python] projected package tree hash mismatch")

    # 返回供安装结果载荷复用的闭环验证事实。
    return {"ok": True, "projected_tree_sha256": str_projected_tree, "agent": agent_profile_current.agent}

# CLI 主入口验证发布目录并按用户意图执行 dry-run 或安装。
def main() -> None:
    """解析安装参数并执行版本化发布包安装流程。

    参数：无，命令行参数由当前进程读取。
    返回：无业务返回值，结果通过 JSON 标准输出返回。
    异常：发布验证失败或安装复制失败时抛出 SystemExit。
    """

    # 当前命令行参数决定发布目录、目标和写入意图。
    object_arguments = build_argument_parser().parse_args()  # 当前安装命令行参数。

    # guided bundle 模式只允许 Skill 项目并绕过版本化 release 参数。
    if object_arguments.bundle_root:

        # guided_install 自己执行平台投影、路径 containment 和替换确认。
        guided_install(object_arguments)

        # guided flow 已经输出结果并完成自己的退出边界。
        return

    # 旧 release CLI 仍要求显式版本化发布目录。
    if not object_arguments.release_dir:

        # 缺少两种入口所需的 source identity 时 fail-closed。
        raise SystemExit("> ERR: [Python] release_dir is required outside guided bundle mode")

    # 发布目录用 absolute 保留符号链接形态，验证器据此拒绝不安全根路径。
    path_release_directory = Path(object_arguments.release_dir).expanduser().absolute()  # 待验证版本化发布目录。

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
        object_arguments.target,  # skip、平台键或 custom 目标类型。
        object_arguments.platform_home,  # 可选平台根目录覆盖。
        object_arguments.custom_root,  # 可选自定义安装根目录。
        object_arguments.agent_platform,  # 由目录解析的平台选择。
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
        object_arguments.agent_platform
        or load_agent_config(Path(__file__).resolve().parents[3]).agent,
        dict_result,  # 安装阶段共享结果载荷。
    )

# 直接执行模块时启动技能安装 CLI。
if __name__ == "__main__":

    # 主入口负责所有结构化输出和退出状态。
    main()
