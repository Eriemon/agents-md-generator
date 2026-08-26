"""实现根级与作用域 AGENTS.md 的渲染入口。"""

# CLI 参数和标准输出依赖用于稳定暴露渲染入口。
import argparse
import json
import os
import sys

# 路径类型用于渲染项目根和可选模板目录。
from pathlib import Path
from typing import Any

# 共享忽略目录保证 scoped 扫描与项目发现一致。
from agents_common import SKIP_DIRS
from agents_common import emit_json
from agents_common import ensure_global_rule_overrides_file

# 结构、分支和文档门禁由现有治理模块提供。
from manage_dirs import apply_structure_fix
from manage_dirs import structure_gate
from manage_docs import branch_gate
from manage_docs import preflight_docs
from manage_docs import scaffold as scaffold_docs

# 平台配置用于受控写入前的 worker profile 选择。
from agent_platform import (
    global_instruction_file_label,
    load_agent_config,
    load_catalog,
    resolve_agent_profile,
    write_agent_config,
)

# Codebase-memory 写入门禁和 worker 画像负责渲染前的受管能力检查。
from codebase_memory_mcp import enforce_codebase_memory_write_gate

# 语言路由校验器仍由独立模块负责，渲染器只投影压缩后的稳定合同。
from reviewer_worker_profile import REVIEWER_WORKER_SHA256, ensure_reviewer_worker_profile
from tester_worker_profile import ensure_tester_worker_profile
from gardener_worker_profile import ensure_gardener_worker_profile
from manage_worker_state import read_authorized_worker_states

# 初始结构检查只负责确认门禁，不提前执行文件迁移。
def enforce_structure_confirmation(
    project: Path,
    bool_confirm_fix: bool,
) -> None:
    """验证结构阻断是否已获得用户确认。

    参数：project 为仓库根。
    参数：bool_confirm_fix 表示用户是否确认推荐修复。
    返回：已批准或已确认时返回；否则输出 JSON 并退出。
    异常：治理阻断时抛出 SystemExit(1)。
    """

    # 初始门禁必须在分支检查之前保持只读。
    dict_structure = structure_gate(project)  # 写入前结构检查。

    # 已批准结构或显式确认修复都可进入分支门禁。
    if dict_structure.get("approved", True) or bool_confirm_fix:

        # 此阶段不执行迁移，避免污染后续分支检查。
        return

    # 未确认的阻断不得修改 AGENTS.md 或 docs。
    emit_json(
        {
            "errors": [
                "structure governance requires user confirmation before writing AGENTS.md or docs governance"
            ],
            "structure_gate": dict_structure,
            "requires_user_confirmation": True,
        }
    )

    # 非零退出阻止调用方误判写入成功。
    raise SystemExit(1)

# 已确认结构修复在分支门禁通过后执行并复检。
def apply_confirmed_structure_fix(
    project: Path,
    bool_confirm_fix: bool,
) -> None:
    """执行可选结构修复并验证最终状态。

    参数：project 为仓库根。
    参数：bool_confirm_fix 表示用户是否要求执行修复。
    返回：未请求或修复通过时返回；失败时输出 JSON 并退出。
    异常：修复或复检失败时抛出 SystemExit(1)。
    """

    # 未确认修复时保持文件系统不变。
    if not bool_confirm_fix:

        # 普通批准路径无需迁移。
        return

    # 用户确认后执行结构治理器给出的修复。
    dict_fix = apply_structure_fix(project)  # 结构修复执行报告。

    # 文件操作错误必须在任何规则写入前返回。
    if dict_fix.get("errors"):

        # 错误载荷保留修复器的具体诊断。
        emit_json(
            {
                "errors": [
                    "structure governance fix failed before writing AGENTS.md or docs governance"
                ],
                "structure_fix": dict_fix,
            }
        )

        # 修复失败终止渲染写入。
        raise SystemExit(1)

    # 修复后重新检查，不能依赖操作成功即推断门禁通过。
    dict_structure = structure_gate(project)  # 修复后的结构检查。

    # 复检通过后继续文档预检。
    if dict_structure.get("approved", True):

        # 最终结构已满足治理合同。
        return

    # 同时返回修复报告和复检报告便于定位残留问题。
    emit_json(
        {
            "errors": [
                "structure governance remains blocked after the confirmed structure fix attempt"
            ],
            "structure_fix": dict_fix,
            "structure_gate": dict_structure,
        }
    )

    # 复检失败保持非零退出。
    raise SystemExit(1)

# 分支门禁保持 worktree 硬阻断不可确认覆盖。
def enforce_branch_gate(
    project: Path,
    bool_confirm_governance: bool,
) -> None:
    """验证分支与单工作树治理合同。

    参数：project 为仓库根。
    参数：bool_confirm_governance 表示是否确认普通分支整理风险。
    返回：通过时无返回；阻断时输出 JSON 并退出。
    异常：硬阻断或未确认普通阻断时抛出 SystemExit(1)。
    """

    # 分支检查先返回 hard_blocking 与普通批准状态。
    dict_branch = branch_gate(project)  # 当前 Git 治理报告。

    # 硬阻断始终失败；普通阻断可由显式确认继续。
    bool_blocked = dict_branch.get("hard_blocking", False) or (  # Git 治理是否禁止本次写入。
        not dict_branch.get("approved", True)  # 普通分支门禁未批准。
        and not bool_confirm_governance  # 未获得普通分支风险确认。
    )  # 当前写入是否被 Git 治理阻断。

    # 已批准或已确认普通风险时继续。
    if not bool_blocked:

        # 单工作树政策已满足。
        return

    # worktree 硬阻断与普通分支确认使用不同错误文本。
    str_error = (
        "Git worktree governance is hard-blocking and cannot be confirmed away"  # worktree 硬阻断摘要。
        if dict_branch.get("hard_blocking", False)  # 按硬阻断类型选择诊断。
        else "branch governance requires user confirmation before writing AGENTS.md or docs governance"  # 普通阻断摘要。
    )  # Git 治理阻断摘要。

    # 机器载荷说明普通阻断是否仍可确认。
    emit_json(
        {
            "errors": [str_error],
            "branch_gate": dict_branch,
            "requires_user_confirmation": not dict_branch.get("hard_blocking", False),
        }
    )

    # 阻断状态不允许进入文档脚手架或文件写入。
    raise SystemExit(1)

# 强控制写入前完成结构、分支和文档布局治理。
def prepare_controlled_write(
    project: Path,
    profile: dict,
    args: argparse.Namespace,
) -> None:
    """执行强控制项目写入前治理。

    参数：project 为仓库根。
    参数：profile 为已加载的强控制配置。
    参数：args 提供三个用户确认开关。
    返回：所有门禁通过并完成必要脚手架后返回。
    异常：任一治理门禁失败时抛出 SystemExit(1)。
    """

    # 初始结构检查仅确认风险，不在分支检查前迁移文件。
    enforce_structure_confirmation(project, args.confirm_structure_fix)

    # worktree 与分支治理必须在任何项目文件修改之前通过。
    enforce_branch_gate(project, args.confirm_branch_governance)

    # 分支门禁通过后再闭合知识图谱门禁，避免其 `.gitignore` 写入污染预检事实。
    dict_codebase_gate = enforce_codebase_memory_write_gate(  # 根规则写入前知识图谱门禁结果
        project,  # 待写入根规则的项目
        profile,  # 已加载的强控制画像
        apply=True,  # 执行必要忽略规则修复
        confirm_untrack=args.confirm_codebase_memory_untrack,  # 用户解除跟踪确认
    )

    # 未通过依赖、索引或 Git 边界时阻止任何后续文件迁移。
    if not dict_codebase_gate.get("ok"):

        # 输出精确机器可读门禁诊断。
        emit_json(dict_codebase_gate)

        # 写入路径以非零状态终止。
        raise SystemExit(1)

    # 分支门禁通过后才执行用户确认的结构迁移。
    apply_confirmed_structure_fix(project, args.confirm_structure_fix)

    # docs preflight 判断现有布局是否需要用户确认。
    dict_docs = preflight_docs(project)  # 文档布局预检报告。

    # 未确认的新文档布局不能自动创建。
    if dict_docs["requires_user_confirmation"] and not args.confirm_docs_layout:

        # JSON 载荷保留预检证据和确认标记。
        emit_json(
            {
                "errors": [
                    "docs layout requires user confirmation before writing AGENTS.md or docs governance"
                ],
                "docs_preflight": dict_docs,
                "requires_user_confirmation": True,
            }
        )

        # 文档布局阻断保持非零退出。
        raise SystemExit(1)

    # 全局规则覆盖文件在文档脚手架之前建立。
    ensure_global_rule_overrides_file(project, profile)

    # 治理目录和文档按项目配置创建或同步。
    scaffold_docs(project)

# 写入前完成 Codex worker 配置生命周期，保持 CLI 编排只负责流程顺序。
def _ensure_worker_profiles_for_write(
    args: Any,
    profile_agent: Any,
    path_project: Path,
) -> None:
    """
    在受控写入前验证并刷新三个 canonical worker profile。

    参数:
        args: 已解析的渲染 CLI 参数命名空间。
        profile_agent: 当前选择的平台配置对象。
        path_project: 当前受管项目根目录。
    返回:
        无；未触发 Codex worker 写入时直接返回。
    异常:
        SystemExit: 任一 worker profile 的最终校验失败时抛出。
    """

    # 只有 Codex 平台且用户明确确认时才进入 worker 生命周期。
    if not (
        args.write
        and profile_agent.worker_support == "codex-native"
        and (
            args.confirm_gardener_worker_update
            or args.confirm_profile_bundle_sha256
        )
    ):

        # 其他平台或只读模式不改变 worker 配置。
        return

    # 项目授权状态决定是否允许进入任何 worker profile 写入路径。
    dict_worker_states = read_authorized_worker_states(path_project)  # 项目 canonical worker 状态

    # 全部 disabled 时不创建、刷新或验证任何 worker profile。
    if not any(str_state == "enabled" for str_state in dict_worker_states.values()):

        # 保持根渲染完全 worker-free，等待显式 state-apply。
        return

    # 新 bundle 收据路径委托统一 manager，避免三套确认哈希并行存在。
    if args.confirm_profile_bundle_sha256:

        # 延迟导入避免渲染模块初始化时引入 worker 写入副作用。
        from manage_workers import apply_workers

        # manager 负责验证 proposed 字节、bundle 哈希和原子写入。
        dict_bundle_result = apply_workers(  # 本次 bundle 收据驱动的 worker 配置写入结果。
            project=path_project,  # 当前项目的 profile bundle 应用目标。
            confirm_profile_bundle_sha256=args.confirm_profile_bundle_sha256,  # 用户确认的 bundle 哈希。
        )

        # bundle 收据不匹配或读回失败时禁止 AGENTS 写入。
        if not dict_bundle_result.get("valid", False):

            # 保留 manager 的具体错误供调用方定位收据漂移。
            raise SystemExit(
                "> ERR: [Python] profile bundle confirmation failed: "
                + str(dict_bundle_result.get("errors", dict_bundle_result.get("confirmation", "")))
            )

        # bundle 写入完成后跳过旧的三个单项写入路径。
        return

    # 生成前确保唯一 tester_worker 配置可用并记录结果。
    dict_tester_result = ensure_tester_worker_profile(  # tester_worker 配置结果。
        write=True,  # 写入或刷新 tester_worker 配置。
        confirm_update=args.confirm_tester_worker_update,  # 复用单次授权收据。
    )

    # 写回验证失败必须阻止 AGENTS 落盘，保留明确失败证据。
    dict_final_validation = dict_tester_result.get("final_validation", {})  # 最终 TOML 验证。

    # 无效配置不得进入 AGENTS.md 写入流程。
    if isinstance(dict_final_validation, dict) and not dict_final_validation.get("valid", False):

        # 以稳定错误前缀报告配置验证失败。
        raise SystemExit(
            "> ERR: [Python] tester_worker.toml failed TOML or role validation"
        )

    # reviewer 配置使用用户已确认的哈希收据完成生命周期校验。
    dict_reviewer_result = ensure_reviewer_worker_profile(  # reviewer 配置生命周期结果。
        write=True,  # 请求写入或刷新 reviewer 配置。
        confirm_sha256=REVIEWER_WORKER_SHA256,  # 使用已确认的 reviewer 哈希。
    )

    # 读取 reviewer 的最终验证或既有验证结果。
    dict_reviewer_validation = dict_reviewer_result.get(  # reviewer 最终字段校验结果。
        "final_validation",  # 优先读取本次写入后的验证。
        dict_reviewer_result.get("existing_validation", {}),  # 回退读取既有验证。
    )

    # reviewer 字段校验未通过时停止模板写入。
    if not isinstance(dict_reviewer_validation, dict) or not dict_reviewer_validation.get("valid", False):

        # 以 reviewer 专属错误文本报告配置验证失败。
        raise SystemExit(
            "> ERR: [Python] reviewer_worker.toml is missing or invalid; use workers/manage_workers.py apply"
        )

    # gardener 接管独立 profile 的授权写入结果。
    dict_gardener_result = ensure_gardener_worker_profile(  # gardener worker 返回的受管状态。
        write=True,  # 向 gardener profile 写入或刷新受管字段。
        confirm_update=args.confirm_gardener_worker_update,  # 将当前任务确认传给 gardener 校验。
    )

    # 以 gardener 返回体中的字段优先级解析校验结果。
    dict_gardener_validation = dict_gardener_result.get(  # gardener 字段校验结果。
        "final_validation",  # 优先取 gardener 本次验证。
        dict_gardener_result.get("existing_validation", {}),  # 无新结果时回落到历史状态。
    )

    # gardener 无效时阻止模板正文写入。
    if not isinstance(dict_gardener_validation, dict) or not dict_gardener_validation.get("valid", False):

        # 输出 gardener 配置专用的失败入口。
        raise SystemExit(
            "> ERR: [Python] gardener_worker.toml is missing or invalid; use workers/manage_workers.py apply"
        )
