"""校验受管根工作区边界合同。"""

# 受管根工作区边界使用固定前缀执行唯一性检查。
WORKSPACE_BOUNDARY_PREFIX = "- **Workspace boundary:**"  # 工作区边界规则前缀

# 每个片段对应一层不可由画像或压缩器删除的外部修改保护。
WORKSPACE_BOUNDARY_REQUIRED_SNIPPETS = (  # 工作区边界强制语义片段
    "current work folder",  # 当前本地允许根
    "verified remote-server work folder",  # 已验证远程允许根
    "necessary and side-effect free",  # 外部只读无副作用限制
    "external modification, stop",  # 外部修改前立即停止
    "exact normalized target, action, scope, risks, alternatives, and recovery limits",  # 完整风险披露
    "two separate explicit user confirmations",  # 两次相互独立确认
    "first approves the exception in principle and the second approves the exact action",  # 确认职责
    "target or scope change invalidates both confirmations",  # 变化后双确认失效
)

# 通用受管根验证器检查工作区边界，不依赖 strong-control 画像状态。
def validate_workspace_boundary_contract(
    text: str,
    file: str,
    errors: list[str],
) -> bool:
    """校验受管根工作区边界的唯一性与完整语义。

    参数:
        text: 当前根 AGENTS.md 全文。
        file: 诊断消息使用的根文件标识。
        errors: 调用方提供的共享错误列表。

    返回:
        规则恰好出现一次且所有强制片段存在时返回 True，否则返回 False。
    """

    # 前缀计数同时阻断缺失和重复规则造成的授权歧义。
    int_rule_count = text.count(WORKSPACE_BOUNDARY_PREFIX)  # 工作区边界规则数量

    # 收集缺失片段后一次性给出稳定诊断，避免逐项产生冗长错误。
    list_missing_snippets = [  # 当前根文件缺少的工作区保护片段
        str_snippet  # 保留原始稳定片段供诊断定位
        for str_snippet in WORKSPACE_BOUNDARY_REQUIRED_SNIPPETS  # 遍历所有最低保护语义
        if str_snippet not in text  # 只收集正文中不存在的片段
    ]

    # 唯一性与内容均满足时无需修改共享错误列表。
    if int_rule_count == 1 and not list_missing_snippets:

        # True 允许根验证入口保持无需同步的状态。
        return True

    # 统一错误文本明确要求刷新受管根工作区边界。
    errors.append(
        f"{file}: invalid managed-root workspace boundary contract; "
        f"count={int_rule_count}, missing={list_missing_snippets}"
    )

    # False 通知根验证入口追加正式同步提示。
    return False
