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

# 紧凑根模板使用的等价短语，仍逐项绑定同一授权语义。
WORKSPACE_BOUNDARY_COMPACT_SNIPPETS = {  # 紧凑工作区片段映射
    "current work folder": (  # 本地工作区紧凑映射
        "current/verified remote work folders",  # 兼容旧模板的完整工作区标签
        "current/verified work folders",  # 当前预算下的工作区标签
    ),  # 本地工作区紧凑短语
    "verified remote-server work folder": (  # 远程工作区紧凑映射
        "current/verified remote work folders",  # 兼容旧模板的远程工作区标签
        "current/verified work folders",  # 当前预算下的远程标签
    ),  # 远程工作区紧凑短语
    "Changes inside either work folder require no additional confirmation": (  # 工作区内直行映射
        "changes inside either need no additional confirmation",  # 工作区内直行短语
        "changes inside either need no confirmation",  # 更短工作区内短语
    ),  # 工作区内直行紧凑短语
    "remote changes remain allowed only when the configured task route matches that folder": (  # 远程路由映射
        "remote changes require matching task route",  # 远程路由短语
        "remote changes require route",  # 更短的远程路由短语
        "remote changes need route",  # 最短远程路由短语
    ),  # 远程路由紧凑短语
    "Official codebase-memory start, index refresh, rebuild, or recovery for the project bound to either work folder": (  # 图谱操作映射
        "Official codebase-memory start/index/rebuild/recovery for folder/cache/root artifact",  # 图谱操作短语
    ),  # 图谱操作紧凑短语
    "including its configured runtime cache and root persistence artifact": (  # 图谱持久化映射
        "folder/cache/root artifact",  # 图谱持久化短语
    ),  # 图谱持久化紧凑短语
    "also requires no additional confirmation": (  # 图谱授权映射
        "needs no additional confirmation",  # 图谱授权短语
        "needs no confirmation",  # 更短图谱授权短语
    ),  # 图谱授权紧凑短语
    "beyond those boundaries must be necessary and side-effect free": (  # 边界外读取映射
        "Necessary, side-effect-free external reads only",  # 边界外读取短语
        "Necessary, side-effect-free reads only",  # 更紧凑的边界外读取短语
        "Necessary side-effect-free reads only",  # 最短边界外读取短语
        "Necessary side-effect-free reads",  # 当前预算下的边界外读取短语
    ),  # 边界外读取紧凑短语
    "Every other external write is prohibited by default": (  # 外部写入默认禁令映射
        "Other external writes are prohibited",  # 外部写入紧凑短语
        "other external writes prohibited",  # 更短外部写入短语
    ),  # 外部写入默认禁令紧凑短语
    "only after the user proactively and explicitly requests the exact action": (  # 写入授权映射
        "unless the user proactively and explicitly requests the exact action",  # 写入授权短语
        "the user must proactively and explicitly request the exact action",  # 写入授权兼容短语
        "unless user proactively requests exact action",  # 最短写入授权短语
        "unless user proactively requests action",  # 更短写入授权短语
    ),  # 外部写入授权紧凑短语
    "exact normalized target, action, scope, risks, alternatives, and recovery limits": (  # 风险披露映射
        "normalized target/action/scope/risks/alternatives/recovery limits",  # 风险披露短语
    ),  # 风险披露紧凑短语
    "obtain exactly one explicit user confirmation": (  # 单次确认映射
        "obtain one confirmation",  # 单次确认紧凑短语
    ),
    "target or scope change invalidates that confirmation": (  # 授权失效映射
        "Target/scope changes invalidate it",  # 授权失效短语
        "Target/scope changes invalidate",  # 更短授权失效短语
    ),  # 授权失效紧凑短语
    "Any target or scope change invalidates that confirmation.": (  # 变异表兼容映射
        "Target/scope changes invalidate",  # 当前根规则授权失效短语
    ),  # 变异表授权失效紧凑短语
    "installed skill always requires exactly one explicit user confirmation": (  # 安装态授权映射
        "installed skill always requires one explicit user confirmation",  # 安装态授权短语
        "installed skill requires one explicit user confirmation",  # 安装态授权兼容短语
    ),  # 安装态授权紧凑短语
}

# 判断根正文是否包含标准片段或已批准的紧凑等价片段。
def workspace_boundary_snippet_present(text: str, str_required_snippet: str) -> bool:
    """判断工作区边界必需片段是否以标准或紧凑形式出现。

    参数：text 为根 AGENTS 正文；str_required_snippet 为标准片段。
    返回：标准片段或其紧凑等价片段存在时为 True。
    """

    # 标准长句优先保持完全兼容。
    if str_required_snippet in text:

        # 旧模板已经保留完整授权语义。
        return True

    # 紧凑模板只接受当前映射明确列出的等价短语。
    for str_compact_snippet in WORKSPACE_BOUNDARY_COMPACT_SNIPPETS.get(
        str_required_snippet,
        (),
    ):

        # 任一受控短语命中即可完成当前片段核验。
        if str_compact_snippet in text:

            # 当前紧凑片段属于已登记的等价语义。
            return True

    # 没有标准或受控短语时保留缺失状态。
    return False

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
        if not workspace_boundary_snippet_present(text, str_snippet)  # 只收集原句和紧凑句均缺失的片段
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
