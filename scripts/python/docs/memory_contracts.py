"""归一化并校验项目 memory 治理契约。"""

# 契约函数使用路径与结构化值类型。
from pathlib import Path
from typing import Any

# 项目治理画像是 memory 契约的唯一配置来源。
from manage_docs_shared import project_profile

# 默认采集范围只允许沉淀长期项目事实。
DEFAULT_CAPTURE_SCOPE = (  # 默认允许沉淀的长期项目事实范围
    "handoff summaries, user-confirmed project preferences, durable decisions, "
    "validation lessons, and release lessons"
)

# 默认读取策略要求实现前结合最新交接和相关摘要。
DEFAULT_READ_POLICY = (
    "read latest handoff plus relevant docs/memory summaries before implementation"  # 实现前读取要求
)  # 新会话的默认记忆读取顺序

# 默认敏感边界禁止凭据、秘密和原始本机私有路径持久化。
DEFAULT_SENSITIVITY_POLICY = (
    "do not store secrets, credentials, or raw local private paths"  # 禁止持久化的敏感内容
)  # memory 持久化安全基线

# 后端白名单阻止配置静默落到未实现的存储语义。
SUPPORTED_BACKENDS = {"sqlite-plus-jsonl"}  # 可执行的 memory 持久化后端

# 契约路径统一用 Path 构造默认值，避免手写分隔符和路径漂移。
def normalized_contract_paths(
    dict_contract: dict[str, Any],
    str_folder: str,
) -> dict[str, str]:
    """补齐 memory 契约中的持久化文件路径。

    Args:
        dict_contract: 原始结构化 memory 契约。
        str_folder: 已归一化的 memory 根目录。

    Returns:
        五类持久化文件的可移植 POSIX 路径。
    """

    # 根路径承载所有默认文件，防止各字段落到不同目录。
    path_folder = Path(str_folder)  # memory 默认文件根目录

    # 每个字段优先保留显式配置，空值再回退到统一根目录。
    return {
        "database": str(
            dict_contract.get("database", path_folder / "memory.sqlite3")
        ).strip()
        or (path_folder / "memory.sqlite3").as_posix(),  # SQLite 数据库路径
        "events": str(dict_contract.get("events", path_folder / "events.jsonl")).strip()
        or (path_folder / "events.jsonl").as_posix(),  # 追加事件日志路径
        "summaries": str(
            dict_contract.get("summaries", path_folder / "summaries.md")
        ).strip()
        or (path_folder / "summaries.md").as_posix(),  # 有界摘要视图路径
        "guide": str(dict_contract.get("guide", path_folder / "MEMORY.md")).strip()
        or (path_folder / "MEMORY.md").as_posix(),  # memory 使用指南路径
        "bootstrap_state": str(
            dict_contract.get("bootstrap_state", path_folder / "bootstrap-state.json")
        ).strip()
        or (path_folder / "bootstrap-state.json").as_posix(),  # 会话 bootstrap 状态路径
    }

# 摘要策略只接受对象配置，并为每个预算字段补充稳定默认值。
def normalized_summary_policy(object_policy: Any) -> dict[str, Any]:
    """归一化有界 memory 摘要策略。

    Args:
        object_policy: profile 中尚未验证类型的摘要策略值。

    Returns:
        模式固定且四项预算完整的摘要策略。
    """

    # 非对象值不能提供逐字段预算，按未配置处理。
    dict_policy = object_policy if isinstance(object_policy, dict) else {}  # 类型安全策略

    # 所有预算都转换为整数，错误值由契约校验入口统一报告。
    return {
        "mode": "bounded",  # 摘要固定使用有界模式
        "max_bytes": int(dict_policy.get("max_bytes", 128 * 1024)),  # 总字节预算
        "recent_detail_limit": int(dict_policy.get("recent_detail_limit", 50)),  # 最近详情数
        "per_summary_chars": int(dict_policy.get("per_summary_chars", 600)),  # 单条正文字符数
        "older_index_limit": int(dict_policy.get("older_index_limit", 500)),  # 旧条目索引数
    }

# 项目 profile 是 memory 契约的唯一配置来源，缺省字段在此集中兼容。
def memory_contract(project: Path) -> dict[str, Any]:
    """读取并归一化项目的 memory 治理契约。

    Args:
        project: 项目根目录。

    Returns:
        字段完整、路径和摘要策略已补默认值的 memory 契约。
    """

    # 项目 profile 同时承载新契约和旧版兼容字段。
    dict_profile = project_profile(project)  # 项目治理配置

    # 非对象契约按未配置处理，防止后续字段访问失败。
    dict_contract = (
        dict_profile.get("memory_contract", {})  # 优先读取结构化契约
        if isinstance(dict_profile.get("memory_contract", {}), dict)  # 仅接受对象契约
        else {}  # 非对象契约按未配置处理
    )  # 原始结构化 memory 契约

    # 顶层兼容字段仅用于旧项目迁移，显式 memory_contract 配置优先。
    bool_enabled = bool(  # 新旧字段归一化后的启用状态
        dict_contract.get("enabled", dict_profile.get("memory_enabled", False))  # 新字段优先
    )  # 最终 memory 启用状态

    # 文件缺省值围绕同一个根目录派生，避免目录配置部分漂移。
    str_folder = (
        str(dict_contract.get("folder", "docs/memory")).strip() or "docs/memory"  # 空值回退
    )  # 后续文件缺省值共同使用的 memory 根目录

    # 路径和摘要预算由专用归一化器生成，主合同只负责字段聚合。
    dict_paths = normalized_contract_paths(dict_contract, str_folder)  # memory 文件路径

    # 摘要策略固定有界模式并补齐全部预算字段。
    dict_summary_policy = normalized_summary_policy(  # 有界摘要策略
        dict_contract.get("summary_policy", {})  # 原始摘要策略配置
    )

    # 返回完整字段集合，让调用方无需重复兼容缺省配置。
    return {
        "enabled": bool_enabled,  # 控制 memory CLI 是否执行存储治理
        "folder": str_folder,  # memory 根目录
        "storage_backend": str(
            dict_contract.get(
                "storage_backend",  # 结构化存储后端字段
                dict_profile.get("memory_storage_backend", "sqlite-plus-jsonl"),  # 旧字段回退
            )
        ).strip()
        or "sqlite-plus-jsonl",  # 空值使用受支持后端
        **dict_paths,  # 数据库、事件、摘要、指南和 bootstrap 文件路径
        "capture_scope": str(
            dict_contract.get(
                "capture_scope",  # 结构化采集范围字段
                dict_profile.get("memory_capture_scope", DEFAULT_CAPTURE_SCOPE),  # 兼容旧版采集范围
            )
        ).strip()
        or DEFAULT_CAPTURE_SCOPE,  # 空值使用默认采集范围
        "read_policy": str(
            dict_contract.get(
                "read_policy",  # 结构化读取策略字段
                dict_profile.get("memory_read_policy", DEFAULT_READ_POLICY),  # 兼容旧版读取约束
            )
        ).strip()
        or DEFAULT_READ_POLICY,  # 空值使用默认读取策略
        "sensitivity_policy": str(
            dict_contract.get(
                "sensitivity_policy",  # 结构化敏感信息策略字段
                dict_profile.get("memory_sensitivity_policy", DEFAULT_SENSITIVITY_POLICY),  # 兼容旧版脱敏约束
            )
        ).strip()
        or DEFAULT_SENSITIVITY_POLICY,  # 空值使用默认敏感信息策略
        "compress_after_events": int(
            dict_contract.get("compress_after_events", 20) or 20
        ),  # 触发压缩的事件数
        "summary_policy": dict_summary_policy,  # 有界检索视图策略
    }

# 契约校验只报告阻断 memory 读写的配置问题。
def memory_contract_errors(contract: dict[str, Any]) -> list[str]:
    """检查 memory 契约是否可由当前实现执行。

    Args:
        contract: 已归一化的 memory 契约。

    Returns:
        面向用户的契约错误列表。
    """

    # 错误列表同时供初始化、写入、读取和压缩入口使用。
    list_errors: list[str] = []  # memory 契约阻断项

    # 关闭状态不能执行读写命令，需要向上层提供明确诊断。
    if not contract.get("enabled"):

        # 保持错误文本稳定，供治理命令和测试共同消费。
        list_errors.append("memory governance is disabled for this project")

    # 后端名称归一化为空白无关文本后再匹配支持集合。
    str_backend = str(contract.get("storage_backend", "")).strip()  # 配置的存储后端

    # 当前只实现 sqlite-plus-jsonl，拒绝静默降级到未知后端。
    if str_backend not in SUPPORTED_BACKENDS:

        # 空后端单独显示占位符，避免诊断看起来像被截断。
        list_errors.append(
            "memory_storage_backend must be sqlite-plus-jsonl; "
            f"got {str_backend or '<empty>'}"
        )

    # 摘要策略必须保持有界模式和正数预算。
    dict_summary_policy = contract.get("summary_policy", {})  # 规范化摘要策略

    # 模式漂移会让摘要重新膨胀为全量副本。
    if dict_summary_policy.get("mode") != "bounded":

        # 将不可支持的模式作为契约错误返回。
        list_errors.append("memory summary_policy.mode must be bounded")

    # 每个预算字段都必须能限制对应输出维度。
    tuple_summary_fields = (
        "max_bytes",  # 限制最终 Markdown 视图体积
        "recent_detail_limit",  # 最近详情数量预算
        "per_summary_chars",  # 单条摘要字符预算
        "older_index_limit",  # 历史索引数量预算
    )  # 需要逐项校验的摘要策略字段

    # 逐项拒绝零值和负值，避免生成不可解释的空视图。
    for str_field in tuple_summary_fields:

        # 缺失字段同样按无效预算处理。
        if int(dict_summary_policy.get(str_field, 0) or 0) <= 0:

            # 错误文本包含精确字段，便于修复配置。
            list_errors.append(f"memory summary_policy.{str_field} must be a positive integer")

    # 调用方统一决定错误的呈现方式和退出码。
    return list_errors
