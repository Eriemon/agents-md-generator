"""选择并验证适用于 AGENTS 的工程规则集压缩合同。"""

# 延迟注解求值保持 CLI 在受支持 Python 版本间兼容。
from __future__ import annotations

# argparse 解析规则选择参数，json 提供稳定机器输出。
import argparse
import json
import sys
from pathlib import Path
from typing import Any

# 直接执行规则选择入口时禁止生成字节码缓存。
sys.dont_write_bytecode = True  # 防止发布源码树出现 __pycache__

# importlib 可能在执行当前入口前已经写入自身的字节码缓存。
def _remove_entry_bytecode_cache() -> None:
    """删除当前入口在执行前生成的 importlib 字节码缓存。

    参数：无。
    返回：无。
    """

    # 当前模块的缓存路径由 importlib 写入模块元数据。
    object_cached_path = globals().get("__cached__")  # 当前入口缓存路径。

    # 直接执行入口时通常没有可删除的当前模块缓存。
    if not object_cached_path:

        # 没有缓存路径时保持入口的正常启动流程。
        return

    # 缓存清理只针对当前入口，不触碰其他模块的运行时文件。
    path_cached_file = Path(str(object_cached_path))  # 当前入口字节码文件。

    # 缓存文件删除失败时仍保持规则选择入口可用。
    try:

        # 删除 importlib 在执行入口前写入的自身缓存。
        path_cached_file.unlink(missing_ok=True)

        # 自身缓存删除后，空的缓存目录也不应留在发布源码树中。
        path_cached_directory = path_cached_file.parent  # 当前入口缓存目录。

        # 仅空的标准缓存目录允许被清理。
        if path_cached_directory.name == "__pycache__" and not any(path_cached_directory.iterdir()):

            # 仅删除确认为空的标准缓存目录。
            path_cached_directory.rmdir()

    # 文件系统拒绝清理时不能阻断规则选择入口的业务输出。
    except OSError:

        # 缓存清理失败不能阻断规则选择入口的业务输出。
        return

# 入口模块加载完成后立即移除可能产生的自身缓存。
_remove_entry_bytecode_cache()

# 支持列表只包含仓库已有参考资料覆盖的工程规则集。
SUPPORTED_RULE_SETS = [  # 可选择的工程规则集标识
    "a-philosophy-of-software-design",  # 复杂度与深模块设计规则
    "clean-architecture",  # 架构边界与依赖方向规则
    "clean-code",  # 局部可读性与命名规则
    "code-complete",  # 代码构造纪律规则
    "designing-data-intensive-applications",  # 数据系统一致性规则
    "domain-driven-design",  # 完整领域驱动设计规则
    "domain-driven-design-distilled",  # 精简领域驱动设计规则
    "implementing-domain-driven-design",  # 实践型领域实现规则
    "patterns-of-enterprise-application-architecture",  # 企业应用架构模式
    "refactoring",  # 行为保持型重构规则
    "refactoring-guru",  # 重构模式速查规则
    "release-it",  # 生产可靠性与恢复规则
    "the-pragmatic-programmer",  # 通用工程实践规则
    "working-effectively-with-legacy-code",  # 遗留代码安全修改规则
]

# 压缩模式禁止完整书籍规则进入 AGENTS 正文。
ALLOWED_MODES = ["mini", "nano"]  # 允许的规则压缩粒度

# 作用域决定规则是项目基线、目录局部还是按需启用。
ALLOWED_SCOPES = ["project-baseline", "scoped", "on-demand"]  # 允许的规则生效范围

# 任务推荐表把主要工程风险映射到一个权威主规则集。
TASK_RECOMMENDATIONS = {  # 任务类型到规则集推荐的映射
    "architecture": {  # 模块边界与复杂度风险任务
        "primary": "a-philosophy-of-software-design",  # 架构任务主规则集
        "reason": "use when complexity, module boundaries, and abstraction depth are the main risk",  # 推荐触发条件
    },
    "clean-code": {  # 可读性与维护性风险任务
        "primary": "clean-code",  # 可读性任务主规则集
        "reason": "use when local readability, naming, function shape, and maintainability are the main risk",  # 可读性风险触发条件
    },
    "data": {  # 数据一致性与存储演进任务
        "primary": "designing-data-intensive-applications",  # 数据任务主规则集
        "reason": "use when source of truth, consistency, events, streams, storage, or schema evolution dominate",  # 数据一致性风险触发条件
    },
    "domain": {  # 领域语义与边界任务
        "primary": "domain-driven-design",  # 领域任务主规则集
        "reason": "use when business meaning, bounded contexts, ubiquitous language, and model boundaries dominate",  # 领域边界风险触发条件
    },
    "legacy": {  # 未表征行为的遗留代码任务
        "primary": "working-effectively-with-legacy-code",  # 遗留任务主规则集
        "reason": "use when behavior is poorly characterized and changes need tests before cleanup",  # 遗留行为表征触发条件
    },
    "refactor": {  # 行为保持型结构调整任务
        "primary": "refactoring",  # 重构任务主规则集
        "reason": "use when preserving behavior while changing structure is the main work",  # 行为保持重构触发条件
    },
    "reliability": {  # 生产失败与恢复任务
        "primary": "release-it",  # 可靠性任务主规则集
        "reason": "use when production failure semantics, bounds, retries, recovery, and operations dominate",  # 生产恢复风险触发条件
    },
}

# 冲突对禁止两个互斥建模范式以同等优先级同时生效。
CONFLICT_PAIRS = {  # 同等激活时产生语义冲突的规则集组合
    frozenset({  # 领域模型与企业应用模式冲突组合
        "domain-driven-design",  # 战术 DDD 规则集
        "patterns-of-enterprise-application-architecture",  # 企业应用架构规则集
    }): (
        "domain model pressure conflicts with transaction-script/table-module "  # 领域模型冲突说明前半段
        "pressure when both are equal active guidance"  # 领域模型冲突说明后半段
    ),
    frozenset({  # 实践 DDD 与企业应用模式冲突组合
        "implementing-domain-driven-design",  # 实践 DDD 规则集
        "patterns-of-enterprise-application-architecture",  # 与实践 DDD 冲突的企业模式集
    }): (
        "implementation-heavy DDD conflicts with enterprise-application pattern "  # 实践 DDD 冲突说明前半段
        "pressure when both arbitrate the same model layer"  # 实践 DDD 冲突说明后半段
    ),
}

# 重叠对提示调用方选择一个主规则集以避免重复治理压力。
OVERLAP_PAIRS = {  # 存在大量重复指导的规则集组合
    frozenset({"a-philosophy-of-software-design", "clean-code"}): (  # 架构简化与整洁代码重叠组合
        "both push local code-shape simplification; choose one primary"  # 重叠原因
    ),
    frozenset({"clean-code", "code-complete"}): (  # 整洁代码与完整构造实践重叠组合
        "both cover local construction discipline; choose one primary"  # 两者都约束局部构造纪律
    ),
    frozenset({"clean-code", "the-pragmatic-programmer"}): (  # 整洁代码与务实工程实践重叠组合
        "both cover broad engineering hygiene; choose one primary"  # 两者都覆盖通用工程卫生
    ),
    frozenset({"code-complete", "the-pragmatic-programmer"}): (  # 完整构造与务实工程实践重叠组合
        "both cover broad construction practice; choose one primary"  # 两者都覆盖广义构造实践
    ),
    frozenset({"domain-driven-design", "domain-driven-design-distilled"}): (  # 完整与精简 DDD 重叠组合
        "distilled DDD is a narrower substitute for full DDD pressure"  # 精简版可替代部分完整 DDD 压力
    ),
    frozenset({"domain-driven-design", "implementing-domain-driven-design"}): (  # 理论与实践 DDD 重叠组合
        "implementation DDD overlaps with full DDD model guidance"  # 实践版复用完整 DDD 模型指导
    ),
    frozenset({"domain-driven-design-distilled", "implementing-domain-driven-design"}): (  # 精简与实践 DDD 重叠组合
        "both target DDD implementation choices at different depths"  # 两者以不同深度约束 DDD 实现
    ),
    frozenset({"refactoring", "refactoring-guru"}): (  # 两类重构指导重叠组合
        "both target refactoring choices; choose one primary"  # 两者都指导重构方案选择
    ),
}

# JSON 输出器维持排序键和可读缩进，便于发布证据复核。
def emit_json(data: dict[str, Any]) -> None:
    """输出工程规则选择结果。

    参数：data 为可序列化的规则合同或错误载荷。
    返回：无。
    """

    # 标准输出只包含稳定 JSON，不混入过程日志。
    sys.stdout.write(f"{json.dumps(data, indent=2, sort_keys=True)}\n")

# 输入规范器消除大小写和首尾空白差异。
def normalize(value: str | None) -> str:
    """规范化 CLI 提供的规则标识。

    参数：value 为可空文本输入。
    返回：去除首尾空白并转为小写的文本。
    """

    # 空值统一转换为空字符串供后续必填检查处理。
    return (value or "").strip().lower()

# 合同构造器集中声明主规则、压缩和兼容策略。
def contract(primary: str, mode: str, scope: str, notes: str = "") -> dict[str, Any]:
    """构造可写入项目画像的工程规则合同。

    参数：primary 为主规则集；mode 为压缩粒度；scope 为作用域；notes 为本地说明。
    返回：包含选择结果和固定治理策略的字典。
    """

    # 固定策略字段防止调用方绕过参考资料和主规则唯一性约束。
    return {
        "primary": primary,
        "mode": mode,
        "scope": scope,
        "notes": notes,
        "full_reference_allowed_in_agents": False,
        "compatibility_policy": (
            "one primary active rule set; use secondary rule sets only as "
            "scoped or on-demand guidance"
        ),
        "compression_policy": (
            "decision-equivalent compression: keep decision-changing, "
            "trigger, tradeoff, and checklist rules"
        ),
    }

# 验证器检查标识合法性、完整书籍禁令和规则集关系。
def validate(primary: str, secondaries: list[str], mode: str, scope: str) -> tuple[list[str], list[str]]:
    """验证工程规则选择合同。

    参数：primary 为主规则集；secondaries 为辅助规则集；mode 为压缩模式；scope 为作用域。
    返回：错误列表和非阻断重叠警告列表。
    """

    # 错误列表包含会使合同不可用的规则选择问题。
    list_errors: list[str] = []  # 阻断合同生成的错误

    # 警告列表只记录可通过选择单一主规则消除的重叠。
    list_warnings: list[str] = []  # 非阻断规则重叠警告

    # 主规则必须来自仓库已覆盖的参考资料集合。
    if primary not in SUPPORTED_RULE_SETS:

        # 未知主规则无法生成可验证合同。
        list_errors.append(f"unknown primary rule set: {primary}")

    # full 模式明确违反 AGENTS 仅保存压缩规则的边界。
    if mode == "full":

        # 提示完整书籍规则只能作为参考资料存在。
        list_errors.append("full book rules must stay reference-only and must not be pasted into AGENTS.md")

    # 其他未知模式同样不能进入合同。
    elif mode not in ALLOWED_MODES:

        # 返回全部允许的压缩粒度。
        list_errors.append("mode must be mini or nano")

    # 作用域必须能映射到项目、目录或按需治理行为。
    if scope not in ALLOWED_SCOPES:

        # 返回三个受支持作用域供调用方修正。
        list_errors.append("scope must be project-baseline, scoped, or on-demand")

    # 每个辅助规则分别检查支持状态和与主规则的关系。
    for secondary in secondaries:

        # 未知辅助规则无法参与冲突或重叠分析。
        if secondary not in SUPPORTED_RULE_SETS:

            # 保留未知标识，方便调用方定位具体输入。
            list_errors.append(f"unknown secondary rule set: {secondary}")

            # 当前未知规则不再参与组合关系查找。
            continue

        # 无序集合让主辅规则交换顺序后仍命中同一关系。
        frozenset_pair: frozenset[str] = frozenset({primary, secondary})  # 当前主辅规则组合

        # 冲突组合不能以同等激活级别进入合同。
        if frozenset_pair in CONFLICT_PAIRS:

            # 错误消息保留组合和具体建模冲突原因。
            list_errors.append(
                f"conflicting active rule sets: {primary} + {secondary}: "
                f"{CONFLICT_PAIRS[frozenset_pair]}"
            )

        # 重叠组合允许按局部或按需使用，但应提示去重。
        elif frozenset_pair in OVERLAP_PAIRS:

            # 警告说明选择单一主规则可消除重复治理压力。
            list_warnings.append(
                f"overlapping rule sets: {primary} + {secondary}: "
                f"{OVERLAP_PAIRS[frozenset_pair]}"
            )

    # 返回全部诊断，让 CLI 一次报告所有选择问题。
    return list_errors, list_warnings

# 列表载荷公开所有可选值和关系摘要。
def list_payload() -> dict[str, Any]:
    """构造 CLI ``--list`` 的能力发现载荷。

    参数：无。
    返回：支持的规则、模式、作用域、推荐和关系摘要。
    """

    # 能力载荷同时服务人工发现和机器参数生成。
    return {
        "supported_rule_sets": SUPPORTED_RULE_SETS,
        "allowed_modes": ALLOWED_MODES,
        "allowed_scopes": ALLOWED_SCOPES,
        "task_recommendations": TASK_RECOMMENDATIONS,
        "conflict_pairs": [
            " + ".join(sorted(set_pair))
            for set_pair in sorted(CONFLICT_PAIRS, key=lambda item: sorted(item))
        ],
        "overlap_pairs": [
            " + ".join(sorted(set_pair))
            for set_pair in sorted(OVERLAP_PAIRS, key=lambda item: sorted(item))
        ],
        "policy": {
            "primary": "choose exactly one equal active rule set",
            "full": "reference-only",
            "compression": "decision-equivalent, not sentence-equivalent",
        },
    }

# CLI 入口解析选择、执行验证并映射失败退出码。
def main() -> None:
    """运行工程规则选择命令。

    参数：无。
    返回：无。
    异常：缺少主规则或合同验证失败时抛出 ``SystemExit(1)``。
    """

    # 根解析器描述规则选择和合同验证职责。
    parser = argparse.ArgumentParser(  # 工程规则选择 CLI 解析器
        description="Select and validate a book-derived engineering rule contract."  # CLI 功能摘要
    )

    # list 输出全部支持值和规则关系，不执行合同验证。
    parser.add_argument(
        "--list",
        action="store_true",
        help="List supported rule sets, modes, scopes, and task recommendations.",
    )

    # task 根据主要工程风险推荐一个主规则集。
    parser.add_argument(
        "--task",
        choices=sorted(TASK_RECOMMENDATIONS),
        default=None,
        help="Recommend a primary rule set for a task type.",
    )

    # primary 允许调用方覆盖任务推荐并显式选择主规则。
    parser.add_argument("--primary", default=None, help="Primary active rule set.")

    # secondary 可重复提供，用于检测同等激活时的冲突或重叠。
    parser.add_argument(
        "--secondary",
        action="append",
        default=[],
        help="Secondary rule set to check for equal-active conflicts.",
    )

    # mode 控制写入 AGENTS 的规则压缩粒度。
    parser.add_argument(
        "--mode",  # 规则压缩模式选项
        default="mini",  # 默认采用较完整的 mini 摘要
        help="Compression mode: mini or nano. full is rejected for AGENTS.md.",  # 模式帮助文本
    )

    # scope 控制主规则在项目结构中的生效边界。
    parser.add_argument("--scope", default="on-demand", help="Scope: project-baseline, scoped, or on-demand.")

    # notes 把简短项目说明携带到最终合同。
    parser.add_argument("--notes", default="", help="Short local notes to carry into the profile.")

    # 类型标注确保后续字段均来自当前解析器定义。
    namespace_args: argparse.Namespace = parser.parse_args()  # 已解析规则选择参数

    # 能力发现模式直接输出支持矩阵。
    if namespace_args.list:

        # 列表载荷不要求调用方选择主规则。
        emit_json(list_payload())

        # 能力发现完成后不进入验证路径。
        return

    # 任务推荐可为空，显式 primary 仍可独立生成合同。
    dict_recommended: dict[str, str] | None = TASK_RECOMMENDATIONS.get(  # 任务规则推荐
        namespace_args.task or ""  # 无任务类型时使用空查找键
    )

    # 显式主规则优先于按任务推导的推荐值。
    str_primary: str = normalize(namespace_args.primary) or (  # 最终主规则集标识
        dict_recommended["primary"] if dict_recommended else ""  # 无推荐时保留空值
    )

    # 模式规范化消除大小写和首尾空白差异。
    str_mode = normalize(namespace_args.mode)  # 最终压缩模式

    # 作用域采用与规则标识相同的规范化策略。
    str_scope = normalize(namespace_args.scope)  # 最终规则作用域

    # 空辅助规则在冲突分析前过滤。
    list_secondaries: list[str] = [  # 规范化辅助规则集
        normalize(item)  # 当前辅助规则标识
        for item in namespace_args.secondary  # 遍历所有重复选项
        if normalize(item)  # 丢弃空白输入
    ]

    # 主规则既未显式提供也无法推荐时拒绝生成空合同。
    if not str_primary:

        # 诊断说明两个合法的主规则来源。
        emit_json({"errors": ["choose --primary or --task"], "warnings": []})

        # 参数缺失使用非零退出码。
        raise SystemExit(1)

    # 验证结果同时包含阻断错误和非阻断重叠提示。
    tuple_errors, tuple_warnings = validate(  # 规则合同验证诊断
        str_primary,  # 主规则标识
        list_secondaries,  # 辅助规则标识列表
        str_mode,  # 压缩模式
        str_scope,  # 生效作用域
    )

    # 最终载荷无论成功失败都保留推荐和辅助规则上下文。
    dict_payload = {  # 规则选择与验证结果
        "contract": contract(str_primary, str_mode, str_scope, namespace_args.notes.strip()),  # 规则合同
        "errors": tuple_errors,  # 阻断错误集合
        "recommendation": dict_recommended,  # 可空任务推荐
        "secondary_rule_sets": list_secondaries,  # 辅助规则上下文
        "warnings": tuple_warnings,  # 非阻断重叠提示
    }

    # 先输出完整诊断，再根据错误决定退出码。
    emit_json(dict_payload)

    # 阻断错误表示合同不可用于项目画像。
    if tuple_errors:

        # 固定退出码 1 供发布脚本识别验证失败。
        raise SystemExit(1)

# 直接脚本执行进入 CLI，模块导入保持无副作用。
if __name__ == "__main__":

    # 执行规则选择、验证和 JSON 输出流程。
    main()

