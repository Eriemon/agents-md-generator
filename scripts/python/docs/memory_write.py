"""持久化 memory 条目并追加审计事件。"""

# 主表和全文搜索索引共用同一事务，防止查询视图与事实表发生漂移。
def persist_memory_item(database_path: Path, item: dict[str, Any]) -> None:
    """事务写入 memory 条目。

    参数：database_path 为数据库，item 为规范条目；返回 None。
    """

    # 连接生命周期覆盖主表、搜索索引和提交三个原子步骤。
    with closing(connect_memory_db(database_path)) as conn:

        # INSERT OR REPLACE 允许确定性 ID 更新同一条 durable memory。
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_items
            (id, kind, title, summary, source_path, source_hash, source_ref,
             source_timestamp, sequence, tags_json, created_at, updated_at,
             sensitivity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                item["kind"],
                item["title"],
                item["summary"],
                item["source_path"],
                item["source_hash"],
                item["source_ref"],
                item["source_timestamp"],
                item["sequence"],
                item["tags_json"],
                item["created_at"],
                item["updated_at"],
                item["sensitivity"],
            ),
        )

        # 搜索索引使用本次写入的规范化字段立即同步。
        sync_memory_search_item(conn, item)

        # 主表和搜索索引在同一事务中对外可见。
        conn.commit()

# 外部写入入口串联初始化、安全校验、事务持久化和审计事件。
def write_memory(project: Path, input_path: str | Path) -> dict[str, Any]:
    """验证并持久化一条 memory 记录。

    Args:
        project: 项目根目录。
        input_path: 待写入 memory 的 JSON 文件路径。

    Returns:
        包含写入状态、条目标识、审计文件和错误的结果。
    """

    # 写入前复用初始化探测，确保契约、目录和数据库均可用。
    dict_init_result = init_memory(project)  # memory 基础设施检查结果

    # 初始化错误必须原样阻断写入，不能创建部分条目。
    if dict_init_result.get("errors"):

        # 写入失败结果统一包含项目位置和错误列表。
        return {"project": str(project), "written": False, "errors": list(dict_init_result["errors"])}

    # JSON 顶层对象是后续字段归一化的唯一外部输入。
    dict_data = read_memory_input(input_path)  # 原始 memory 写入载荷

    # 外部载荷转换为后续步骤共享的规范主表结构。
    dict_item = build_memory_item(dict_data)  # 本次写入共用的规范化记录

    # 摘要、来源路径与敏感信息必须在数据库连接前完成检查。
    list_item_errors = memory_item_errors(project, dict_item)  # 写入前内容与路径阻断项

    # 任一内容错误都阻断主表和审计流写入。
    if list_item_errors:

        # 内容校验失败保留完整诊断且不产生数据库副作用。
        return {"project": str(project), "written": False, "errors": list_item_errors}

    # 调用方未提供来源哈希时，尝试从合法的仓库内文件计算。
    if not dict_item["source_hash"]:

        # 不存在的可选来源保持空哈希，由条目本身继续提供事实。
        dict_item["source_hash"] = source_hash_for(  # 合法仓库来源的内容哈希
            project, dict_item["source_path"]  # 仓库根与相对来源路径
        )  # 缺省来源哈希

    # 数据库和审计流路径来自当前契约，避免复用初始化前旧值。
    dict_paths = memory_paths(project)  # 本次写入使用的数据库和审计流位置

    # 主表与搜索索引在同一数据库事务中持久化。
    persist_memory_item(dict_paths["database"], dict_item)

    # 数据库提交成功后追加审计事件，避免记录未落库的条目。
    append_event(dict_paths["events"], {"event": "memory_write", **dict_item})

    # 成功结果同时保留兼容 written 字段与结构化 item 字段。
    return {
        "project": str(project),
        "written": dict_item,
        "ok": True,
        "id": dict_item["id"],
        "item": dict_item,
        "events": rel(project, dict_paths["events"]),
        "errors": [],
    }
