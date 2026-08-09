"""校验受管根工作区边界合同。"""

# 受管根工作区边界使用固定前缀执行唯一性检查。
WORKSPACE_BOUNDARY_PREFIX = "- **Workspace boundary:**"  # 工作区边界规则前缀

# 每个片段对应治理内直行边界或不可由画像与压缩器删除的外部修改保护。
WORKSPACE_BOUNDARY_REQUIRED_SNIPPETS = (  # 工作区边界强制语义片段
    "current work folder",  # 当前本地允许根
    "verified remote-server work folder",  # 已验证远程允许根
    "Changes inside either work folder require no additional confirmation",  # 治理内文件修改直行
    "remote changes remain allowed only when the configured task route matches that folder",  # 远程路由约束
    "Official codebase-memory start, index refresh, rebuild, or recovery for the project bound to either work folder",  # 绑定项目图操作直行
    "including its configured runtime cache and root persistence artifact",  # 索引写入面完整边界
    "also requires no additional confirmation",  # 索引操作无需重复确认
    "beyond those boundaries must be necessary and side-effect free",  # 边界外只读无副作用限制
    "Every other external write is prohibited by default",  # 其他外部写入默认禁止
    "only after the user proactively and explicitly requests the exact action",  # 用户必须主动提出精确动作
    "exact normalized target, action, scope, risks, alternatives, and recovery limits",  # 完整风险披露
    "obtain exactly one explicit user confirmation",  # 外部写入披露后的单次显式确认
    "target or scope change invalidates that confirmation",  # 变化后单次确认失效
    "installed skill always requires exactly one explicit user confirmation",  # 已安装技能操作始终单次确认
)

# 旧双确认语义不得残留，否则会与单次确认合同形成冲突。
WORKSPACE_BOUNDARY_FORBIDDEN_SNIPPETS = (  # 工作区边界禁止的旧授权片段
    "two separate explicit user confirmations",  # 旧双确认数量语义
    "first approves the exception in principle",  # 旧原则确认语义
    "second approves the exact action",  # 旧精确动作确认语义
    "invalidates both confirmations",  # 旧双确认同时失效语义
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

    # 显式收集旧双确认残留，确保生成器真正删除旧功能而不是叠加新文本。
    list_forbidden_snippets = [  # 当前根文件仍存在的冲突授权片段
        str_snippet  # 保留命中的旧授权片段供诊断定位
        for str_snippet in WORKSPACE_BOUNDARY_FORBIDDEN_SNIPPETS  # 遍历全部旧双确认语义
        if str_snippet in text  # 只收集仍残留在根规则中的冲突片段
    ]

    # 唯一性与内容均满足时无需修改共享错误列表。
    if int_rule_count == 1 and not list_missing_snippets and not list_forbidden_snippets:

        # True 允许根验证入口保持无需同步的状态。
        return True

    # 统一错误文本明确要求刷新受管根工作区边界。
    errors.append(
        f"{file}: invalid managed-root workspace boundary contract; "
        f"count={int_rule_count}, missing={list_missing_snippets}, "
        f"forbidden={list_forbidden_snippets}"
    )

    # False 通知根验证入口追加正式同步提示。
    return False
