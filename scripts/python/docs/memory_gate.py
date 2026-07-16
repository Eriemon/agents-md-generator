"""实现项目 memory 检索、校验、会话引导和 handoff 写入。"""

# 摘要视图辅助函数独立维护，避免门禁分片超过源码尺寸限制。
from memory_views import (
    bounded_memory_markdown,
    export_full_memory_if_requested,
    memory_index_line,
    memory_summary_lines,
    partition_memory_items,
)

# 关键词检索按 FTS、词项索引和 LIKE 回退顺序执行。
def search_memory_items(
    connection: Any,
    list_terms: list[str],
    limit: int,
) -> tuple[list[dict[str, Any]], str, bool]:
    """按稳定优先级检索 memory 条目。

    Args:
        connection: 已打开的 memory SQLite 连接。
        list_terms: 规范化查询词列表。
        limit: 最大返回条目数。

    Returns:
        命中条目、检索后端名称和 LIKE 回退命中标志。
    """

    # FTS5 提供首选的相关性检索结果。
    list_selected = search_memory_fts(connection, list_terms, limit)  # FTS5 命中条目

    # 首选后端命中时无需执行更宽松的检索。
    if list_selected:

        # False 表示没有进入 LIKE 模糊回退。
        return list_selected, "fts5", False

    # 词项索引在 FTS 无结果时提供确定性回退。
    list_selected = search_memory_terms(connection, list_terms, limit)  # 词项索引命中条目

    # 词项索引命中仍属于结构化检索。
    if list_selected:

        # 返回实际命中的后端供调用方生成证据。
        return list_selected, "term-index", False

    # LIKE 是最后一级兼容检索，可能得到更宽松的匹配。
    list_selected = search_memory_like(connection, list_terms, limit)  # LIKE 模糊命中条目

    # 后端名称区分模糊命中与全部无结果。
    str_backend = "like" if list_selected else "none"  # 最终检索后端名称

    # 回退标志只在 LIKE 实际命中时为真。
    return list_selected, str_backend, bool(list_selected)

# 空查询按更新时间返回最新 memory 条目。
def latest_memory_items(connection: Any, limit: int) -> list[dict[str, Any]]:
    """读取最近更新的 memory 条目。

    Args:
        connection: 已打开的 memory SQLite 连接。
        limit: 最大返回条目数。

    Returns:
        按更新时间倒序排列的 memory 条目。
    """

    # 参数化 LIMIT 避免把调用方数值拼入 SQL。
    rows = connection.execute(  # 执行更新时间倒序查询并保留原始数据库行
        f"SELECT {MEMORY_ITEM_SELECT_COLUMNS} FROM memory_items "
        "ORDER BY updated_at DESC LIMIT ?",
        (limit,),  # 参数化查询的最大返回数量
    ).fetchall()  # 最近更新的数据库行集合

    # 数据库行统一转换为公开 memory 字段结构。
    return [row_to_memory_item(row) for row in rows]

# Memory 读取入口保证初始化完成后再选择查询后端。
def read_memory(project: Path, query: str, limit: int = 5) -> dict[str, Any]:
    """查询项目 memory 并报告实际检索后端。

    Args:
        project: 项目根目录。
        query: 用户查询文本；空文本表示读取最近条目。
        limit: 最大返回条目数。

    Returns:
        包含条目、后端、回退状态和错误的查询报告。
    """

    # 初始化确保数据库和索引结构可供查询。
    dict_init_result = init_memory(project)  # 摘要压缩前的存储初始化结果

    # 初始化错误阻止继续连接不完整的数据库。
    if dict_init_result.get("errors"):

        # 保留查询上下文，便于 CLI 直接呈现失败报告。
        return {
            "project": str(project),
            "query": query,
            "limit": limit,
            "count": 0,
            "items": [],
            "errors": list(dict_init_result["errors"]),
        }

    # 查询词决定使用相关性检索还是最新条目读取。
    list_terms = query_terms(query)  # 规范化查询词

    # 数据库路径来自统一 memory 目录合同。
    dict_paths = memory_paths(project)  # 摘要压缩输出路径集合

    # 连接在查询结束后立即关闭，避免 Windows 文件锁残留。
    with closing(connect_memory_db(dict_paths["database"])) as connection:

        # 非空查询按逐级回退策略检索。
        if list_terms:

            # 三元组同时携带命中条目和后端证据。
            tuple_search_result = search_memory_items(  # 分级检索结果及其后端证据
                connection,  # 当前 memory 数据库连接
                list_terms,  # 已规范化的查询词
                limit,  # 调用方要求的最大命中数
            )  # 关键词检索返回的三元结果

            # 第一项是供调用方展示的命中记录。
            list_selected = tuple_search_result[0]  # 相关性检索命中条目

            # 第二项用于解释本次查询选择了哪种索引。
            str_search_backend = tuple_search_result[1]  # 实际采用的检索后端

            # 第三项区分结构化索引与模糊 LIKE 回退。
            bool_fallback_used = tuple_search_result[2]  # LIKE 回退命中状态

        # 空查询直接读取最近更新的条目。
        else:

            # latest 后端不属于模糊回退。
            list_selected = latest_memory_items(connection, limit)  # 最新 memory 条目

            # 空查询的后端证据明确标记为最新记录读取。
            str_search_backend = "latest"  # 最新条目读取后端

            # 未执行模糊查询时回退标志固定为假。
            bool_fallback_used = False  # 空查询没有 LIKE 回退

    # 查询成功报告保持 CLI 和内部调用的稳定字段。
    return {
        "project": str(project),
        "query": query,
        "limit": limit,
        "count": len(list_selected),
        "items": list_selected,
        "search_backend": str_search_backend,
        "fallback_used": bool_fallback_used,
        "guide": memory_contract(project)["guide"],
        "errors": [],
    }

# Memory 压缩把数据库事实重新生成到人类可读摘要文件。
def compress_memory(project: Path, str_full_output: str | None = None) -> dict[str, Any]:
    """重建项目 memory 摘要 Markdown。

    Args:
        project: 项目根目录。
        str_full_output: 可选的完整 Markdown 导出相对路径。

    Returns:
        写入路径、条目数量和错误列表组成的压缩报告。
    """

    # 初始化错误会使数据库内容不足以生成权威摘要。
    dict_init_result = init_memory(project)  # memory 初始化报告

    # 初始化失败时不覆盖既有摘要文件。
    if dict_init_result.get("errors"):

        # 报告明确标记本次没有写入文件。
        return {
            "project": str(project),
            "written": False,
            "items": 0,
            "errors": list(dict_init_result["errors"]),
        }

    # 数据库条目是摘要文件的唯一内容来源。
    list_items = db_items(project)  # 全部 memory 条目

    # summaries 路径来自统一 memory 目录合同。
    dict_paths = memory_paths(project)  # memory 路径映射

    # 项目配置决定最近详情、旧索引和总字节预算。
    dict_summary_policy = memory_contract(project)["summary_policy"]  # 有界摘要策略。

    # 单条字符预算避免某个长 handoff 独占摘要文件。
    int_summary_limit = int(dict_summary_policy["per_summary_chars"])  # 单条摘要字符上限。

    # 分区结果同时驱动有界视图统计与完整导出排序。
    dict_partition = partition_memory_items(list_items, dict_summary_policy)  # 摘要条目分区

    # Markdown 渲染器根据分区和单条预算生成稳定文本。
    str_summary = bounded_memory_markdown(dict_partition, int_summary_limit)  # 完整摘要 Markdown

    # 总预算是最后一道防线；正常配置下条目级预算应先保证通过。
    int_max_bytes = int(dict_summary_policy["max_bytes"])  # 摘要文件字节上限。

    # 配置异常或标题过长导致超限时拒绝覆盖已有摘要。
    if len(str_summary.encode("utf-8")) > int_max_bytes:

        # 返回可操作诊断，完整历史仍在权威存储中。
        return {
            "project": str(project),
            "written": False,
            "items": len(list_items),
            "errors": [f"bounded memory summary exceeds {int_max_bytes} UTF-8 bytes"],
        }

    # 写入受管 summaries 文件并覆盖旧压缩结果。
    dict_paths["summaries"].write_text(str_summary, encoding="utf-8")

    # 可选完整视图只能写入 memory 根下的新文件，且不能覆盖有界摘要。
    tuple_full_export = export_full_memory_if_requested(  # 完整导出写入结果
        project,  # 有界摘要所属项目
        dict_paths,  # memory 持久化路径
        dict_partition,  # 有界视图使用的稳定条目分区
        str_full_output,  # 用户显式提供的完整导出路径
    )

    # 写入证据和错误由完整导出助手统一返回。
    str_full_written = tuple_full_export[0]  # 可选完整导出相对路径

    # 错误列表决定是否保留有界摘要并提前返回。
    list_full_errors = tuple_full_export[1]  # 完整导出错误

    # 完整导出失败时保留已经写入的有界摘要。
    if list_full_errors:

        # 返回错误但不回滚安全的默认摘要文件。
        return {
            "project": str(project),
            "written": rel(project, dict_paths["summaries"]),
            "items": len(list_items),
            "errors": list_full_errors,
        }

    # 返回项目相对路径作为可移植写入证据。
    return {
        "project": str(project),
        "written": rel(project, dict_paths["summaries"]),
        "items": len(list_items),
        "detailed_items": len(dict_partition["recent"]),
        "indexed_items": len(dict_partition["indexed"]),
        "omitted_items": dict_partition["omitted"],
        "max_bytes": int_max_bytes,
        "full_written": str_full_written,
        "errors": [],
    }

# 摘要安全检查拒绝密钥材料和本地私有路径。
def unsafe_summary_text(text: str) -> list[str]:
    """检查 memory 摘要是否泄露敏感文本。

    Args:
        text: 待检查的摘要文本。

    Returns:
        检测到的敏感内容错误列表。
    """

    # 两类密钥模式共享同一阻断诊断。
    list_errors: list[str] = []  # 摘要安全错误

    # 凭据赋值和私钥正文都禁止进入长期 memory。
    if SECRET_RE.search(text) or PRIVATE_KEY_RE.search(text):

        # 诊断不回显实际敏感内容。
        list_errors.append("memory summary contains an unredacted secret-like assignment")

    # 用户目录绝对路径会泄露本地身份和目录布局。
    if LOCAL_PRIVATE_PATH_RE.search(text):

        # 仅报告类别，不复制原始路径。
        list_errors.append("memory summary contains a raw local private path")

    # 返回全部安全错误，支持一次修复多个类别。
    return list_errors

# 强控制项目必须启用完整 memory 治理合同。
def strong_control_profile(project: Path) -> bool:
    """判断项目档案是否启用了强控制特征。

    Args:
        project: 项目根目录。

    Returns:
        任一强控制字段存在时为 True。
    """

    # 项目档案承载对齐、目录、文档和项目类型合同。
    dict_profile = project_profile(project)  # 项目治理档案

    # 缺失档案按非强控制项目处理。
    if not dict_profile:

        # False 允许未受管项目跳过强制 memory 初始化。
        return False

    # 任一强控制信号都要求 memory 治理启用。
    return bool(
        dict_profile.get("alignment_confirmed")
        or dict_profile.get("directory_contract")
        or dict_profile.get("docs_contract")
        or dict_profile.get("kind")
    )

# 精确工作目录匹配的 Codex 会话用于历史 memory 引导。
def matched_session_ids(project: Path) -> list[str]:
    """读取与项目工作目录精确匹配的会话 ID。

    Args:
        project: 项目根目录。

    Returns:
        非空 Codex 会话 ID 列表。
    """

    # 空 ID 不构成可追踪的引导证据。
    return [
        str(item.get("id", "")).strip()  # 已处理状态中的非空会话标识
        for item in matched_codex_sessions(project)
        if str(item.get("id", "")).strip()
    ]

# Bootstrap 状态记录已经导入的精确工作目录会话。
def bootstrap_state(project: Path) -> dict[str, Any]:
    """读取 memory 会话引导状态。

    Args:
        project: 项目根目录。

    Returns:
        可用的引导状态对象；缺失或类型错误时为空字典。
    """

    # 状态路径来自统一 memory 目录合同。
    path_state = memory_paths(project)["bootstrap_state"]  # bootstrap 状态路径

    # 缺失状态文件按尚未引导处理。
    dict_data = read_json(path_state) if path_state.is_file() else {}  # bootstrap 状态内容

    # 非对象 JSON 不能提供 processed_sessions 字段。
    return dict_data if isinstance(dict_data, dict) else {}

# Bootstrap 完整性要求每个精确工作目录会话都有处理记录。
def bootstrap_errors(project: Path) -> list[str]:
    """检查历史 Codex 会话是否全部写入 bootstrap 状态。

    Args:
        project: 项目根目录。

    Returns:
        缺失会话引导记录的治理错误列表。
    """

    # 当前可发现会话构成引导完整性的权威输入。
    list_sessions = matched_session_ids(project)  # 精确工作目录会话 ID

    # 没有历史会话时无需引导。
    if not list_sessions:

        # 空错误列表表示 bootstrap 完整。
        return []

    # 状态中的 processed_sessions 记录已导入会话。
    dict_state = bootstrap_state(project)  # bootstrap 状态对象

    # 仅接受结构化且具有非空 ID 的处理条目。
    list_processed = [
        str(item.get("id", "")).strip()  # Bootstrap 状态中的会话标识
        for item in dict_state.get("processed_sessions", [])  # Bootstrap 状态记录来源
        if isinstance(item, dict) and str(item.get("id", "")).strip()  # 过滤无标识或非对象状态项
    ]  # 已处理会话 ID

    # 差集保持当前会话发现顺序，便于稳定诊断。
    list_missing = [
        str_session_id  # 当前发现顺序中的会话标识
        for str_session_id in list_sessions  # 保留会话发现的稳定顺序
        if str_session_id not in list_processed  # 排除已经完成引导的会话
    ]  # 尚未引导的会话 ID

    # 任一缺失会话都会阻断强控制 memory 门禁。
    if list_missing:

        # 单条诊断列出全部缺失 ID，避免重复命令建议。
        return [
            "docs/memory/bootstrap-state.json missing exact-cwd Codex session "
            "bootstrap entries: " + ", ".join(list_missing)
        ]

    # 所有匹配会话均已进入 bootstrap 状态。
    return []

# Memory 必需路径检查同时生成覆盖证据和缺失诊断。
def memory_path_findings(
    project: Path,
    dict_paths: dict[str, Path],
) -> tuple[list[str], list[str]]:
    """检查 memory 根目录和必需文件是否存在。

    Args:
        project: 项目根目录。
        dict_paths: memory 路径映射。

    Returns:
        已检查项目相对路径和缺失错误列表。
    """

    # 已检查路径与缺失诊断分别累计。
    list_checked: list[str] = []  # 已检查 memory 路径

    # 路径错误与覆盖证据分开累计。
    list_errors: list[str] = []  # memory 路径缺失错误

    # 固定遍历次序保证检查证据和错误输出稳定。
    for str_key in [
        "folder",  # 所有 memory 文件共同使用的根路径
        "database",  # SQLite 数据库
        "events",  # 追加事件日志
        "summaries",  # 人类可读摘要
        "guide",  # Memory 使用指南
    ]:

        # 映射值是当前必需资产的绝对路径。
        path_required = dict_paths[str_key]  # 当前 memory 必需路径

        # 报告使用项目相对路径保持跨机器可移植。
        str_relative_path = rel(project, path_required)  # 当前资产相对路径

        # checked 证明门禁实际覆盖该路径。
        list_checked.append(str_relative_path)

        # folder 是唯一要求目录类型的资产。
        if str_key == "folder" and not path_required.is_dir():

            # 缺失根目录使用目录专用诊断。
            list_errors.append(f"missing memory directory: {str_relative_path}")

        # 其余资产都必须是普通文件。
        elif str_key != "folder" and not path_required.is_file():

            # 文件缺失诊断保留精确相对路径。
            list_errors.append(f"missing memory file: {str_relative_path}")

    # 返回覆盖证据和路径级错误。
    return list_checked, list_errors

# 数据库基础 schema 必须包含 memory_items 表及全部公开列。
def memory_database_schema_findings(
    project: Path,
    path_database: Path,
    connection: Any,
) -> tuple[list[str], bool]:
    """检查 memory 数据表和必需列。

    Args:
        project: 项目根目录。
        path_database: memory SQLite 文件路径。
        connection: 已打开的 SQLite 连接。

    Returns:
        schema 错误列表和基础 schema 完整标志。
    """

    # 数据库相对路径作为所有 schema 诊断前缀。
    str_database = rel(project, path_database)  # 主表 schema 诊断路径前缀

    # sqlite_master 提供 memory_items 表存在性证据。
    row_table = connection.execute(  # 查询主表是否已经建立
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_items'"  # 主表存在性查询
    ).fetchone()  # memory_items 表记录

    # 主表缺失时无法继续执行列和索引覆盖检查。
    if not row_table:

        # False 阻止调用方执行依赖主表的计数查询。
        return [f"{str_database}: missing memory_items table"], False

    # PRAGMA 列表用于核对公开 memory 字段合同。
    set_columns = {
        str(item[1])  # PRAGMA 行中的列名字段
        for item in connection.execute("PRAGMA table_info(memory_items)").fetchall()  # 主表列元数据
    }  # memory_items 实际列名

    # 差集按名称排序以产生稳定诊断。
    list_missing_columns = sorted(MEMORY_REQUIRED_COLUMNS - set_columns)  # 缺失必需列

    # 任一列缺失都会阻断后续索引一致性证明。
    if list_missing_columns:

        # 单条诊断列出全部缺失列。
        return [
            f"{str_database}: schema missing columns: {', '.join(list_missing_columns)}"
        ], False

    # 空错误和 True 表示主表合同完整。
    return [], True

# 搜索 schema 必须覆盖全文、短词项和常用排序索引。
def memory_search_schema_findings(
    project: Path,
    path_database: Path,
    connection: Any,
) -> tuple[list[str], bool]:
    """检查 memory 搜索表和索引对象。

    Args:
        project: 项目根目录。
        path_database: memory SQLite 文件路径。
        connection: 已打开的 SQLite 连接。

    Returns:
        搜索 schema 错误列表和完整标志。
    """

    # 数据库相对路径作为搜索 schema 诊断前缀。
    str_database = rel(project, path_database)  # 索引覆盖诊断路径前缀

    # sqlite_master 同时枚举搜索表和索引对象。
    set_objects = {
        str(item[0])  # sqlite_master 行中的对象名称
        for item in connection.execute(  # 表与索引对象元数据
            "SELECT name FROM sqlite_master WHERE type IN ('table', 'index')"  # 搜索对象枚举查询
        ).fetchall()
    }  # 数据库表与索引名称

    # 必需集合对应 FTS、词项索引和常用过滤排序路径。
    set_required_objects = {
        "memory_items_fts",  # 全文搜索虚拟表
        "memory_item_terms",  # 短词项倒排表
        "idx_memory_items_updated_at",  # 更新时间排序索引
        "idx_memory_items_sequence",  # 历史顺序索引
        "idx_memory_items_kind",  # 条目类型过滤索引
        "idx_memory_item_terms_term",  # 词项匹配索引
    }  # memory 搜索必需对象

    # 排序差集使错误消息在不同 SQLite 版本间稳定。
    list_missing_objects = sorted(set_required_objects - set_objects)  # 缺失搜索对象

    # 缺失对象阻止索引覆盖计数验证。
    if list_missing_objects:

        # 诊断列出每个缺失表或索引。
        return [
            f"{str_database}: search schema missing objects: "
            + ", ".join(list_missing_objects)
        ], False

    # 空错误和 True 表示搜索 schema 完整。
    return [], True

# 索引计数必须覆盖主表中的每个 memory 条目。
def memory_index_coverage_errors(
    project: Path,
    path_database: Path,
    connection: Any,
) -> list[str]:
    """检查 FTS 和短词项索引的条目覆盖率。

    Args:
        project: 项目根目录。
        path_database: memory SQLite 文件路径。
        connection: 已打开的 SQLite 连接。

    Returns:
        索引计数不一致错误列表。
    """

    # 三类计数分别代表主表、FTS 和词项索引覆盖。
    int_item_count = connection.execute(  # 统计权威主表条目数量
        "SELECT COUNT(*) FROM memory_items"  # 权威条目总数查询
    ).fetchone()[0]  # 主表条目数

    # FTS 计数用于证明全文索引覆盖全部主表条目。
    int_fts_count = connection.execute(  # 统计全文索引条目数量
        "SELECT COUNT(*) FROM memory_items_fts"  # 全文索引总数查询
    ).fetchone()[0]  # FTS 索引条目数

    # 去重 item_id 计数用于证明短词项索引覆盖。
    int_term_item_count = connection.execute(  # 统计词项索引覆盖数量
        "SELECT COUNT(DISTINCT item_id) FROM memory_item_terms"  # 词项索引覆盖查询
    ).fetchone()[0]  # 词项索引覆盖条目数

    # 数据库相对路径作为计数诊断前缀。
    str_database = rel(project, path_database)  # 数据库相对路径

    # 两类索引错误允许同时报告。
    list_errors: list[str] = []  # 索引覆盖错误

    # FTS 行数必须与主表严格一致。
    if int_item_count != int_fts_count:

        # 诊断同时展示两侧计数以支持重建判断。
        list_errors.append(
            f"{str_database}: FTS index row count mismatch: "
            f"memory_items={int_item_count}, memory_items_fts={int_fts_count}"
        )

    # 非空主表要求每个条目至少拥有一条词项索引记录。
    if int_item_count and int_term_item_count != int_item_count:

        # 空主表不要求词项索引存在条目。
        list_errors.append(
            f"{str_database}: short-term index coverage mismatch: "
            f"memory_items={int_item_count}, indexed_items={int_term_item_count}"
        )

    # 返回全部索引覆盖错误。
    return list_errors

# 数据库验证编排基础 schema、搜索 schema 和索引覆盖检查。
def memory_database_errors(project: Path, path_database: Path) -> list[str]:
    """验证 memory SQLite 数据库结构和索引一致性。

    Args:
        project: 项目根目录。
        path_database: memory SQLite 文件路径。

    Returns:
        数据库打开、schema 和索引覆盖错误列表。
    """

    # 缺失数据库由路径检查负责报告，当前层无需重复。
    if not path_database.exists():

        # 空列表避免重复 missing memory file 诊断。
        return []

    # SQLite 损坏或锁定错误转换为治理诊断。
    try:

        # 只读验证结束后立即释放数据库连接。
        with closing(sqlite3.connect(path_database)) as connection:

            # 基础表和列合同是所有后续检查的前提。
            tuple_list_schema_errors, tuple_bool_schema_ok = memory_database_schema_findings(  # 主表合同检查结果
                project,  # 项目根目录
                path_database,  # 当前 SQLite 文件
                connection,  # 已打开的数据库连接
            )

            # 主表 schema 不完整时直接返回精确错误。
            if not tuple_bool_schema_ok:

                # 不执行可能因缺表缺列失败的搜索检查。
                return tuple_list_schema_errors

            # 搜索表与索引对象必须完整。
            tuple_list_search_errors, tuple_bool_search_ok = memory_search_schema_findings(  # 搜索对象检查结果
                project,  # 搜索诊断相对路径基准
                path_database,  # 待核对搜索对象的数据库
                connection,  # 执行 sqlite_master 查询的连接
            )

            # 搜索 schema 不完整时跳过覆盖计数查询。
            if not tuple_bool_search_ok:

                # 基础 schema 已通过，只返回搜索对象错误。
                return tuple_list_search_errors

            # 完整 schema 下执行 FTS 与词项索引覆盖检查。
            return memory_index_coverage_errors(project, path_database, connection)

    # SQLite 数据库错误保留异常摘要但不泄露内容。
    except sqlite3.DatabaseError as exc:

        # 统一相对路径前缀便于定位受损数据库。
        return [f"{rel(project, path_database)}: SQLite open failed: {exc}"]

# Events JSONL 每行都必须可解析且不包含敏感摘要文本。
def memory_event_errors(project: Path, path_events: Path) -> list[str]:
    """验证 memory events JSONL 的语法和摘要安全性。

    Args:
        project: 项目根目录。
        path_events: memory events.jsonl 路径。

    Returns:
        JSONL 解析和敏感文本错误列表。
    """

    # 缺失 events 文件由路径检查负责报告。
    if not path_events.exists():

        # 摘要缺失已由统一路径检查报告，此处不重复。
        return []

    # 每行错误保留原始行号，便于精确修复。
    list_errors: list[str] = []  # events 验证错误

    # 忽略无效字节以继续检查剩余事件行。
    list_lines = path_events.read_text(  # 读取全部事件行以保留原始行号
        encoding="utf-8",  # 事件日志文本编码
        errors="ignore",  # 摘要扫描忽略不可解码字节
    ).splitlines()  # events JSONL 行

    # 行号从一开始，与编辑器和诊断格式一致。
    for int_index, str_line in enumerate(list_lines, start=1):

        # 空行不构成事件，也不产生错误。
        if not str_line.strip():

            # 跳过空白分隔行并继续检查后续事件。
            continue

        # 单行 JSON 解析失败不阻断后续行验证。
        try:

            # 事件对象用于提取 title 和 summary 安全文本。
            dict_event = json.loads(str_line)  # 当前 memory 事件

        # JSONDecodeError 提供精确列位置和原因。
        except json.JSONDecodeError as exc:

            # 诊断附加项目相对文件路径和事件行号。
            list_errors.append(
                f"{rel(project, path_events)}:{int_index}: invalid JSONL event: {exc}"
            )

            # 无效 JSON 不能继续执行字段级安全检查。
            continue

        # 标题与摘要共同构成事件的人类可读长期文本。
        str_summary = " ".join(  # 合并需执行安全检查的长期文本字段
            str(dict_event.get(str_key, ""))  # 当前标题或摘要字段文本
            for str_key in ("title", "summary")  # 需要安全扫描的长期文本字段
        )  # 当前事件可读摘要文本

        # 每个敏感文本错误附加事件行号。
        for str_issue in unsafe_summary_text(str_summary):

            # 诊断不回显实际事件内容。
            list_errors.append(
                f"{rel(project, path_events)}:{int_index}: {str_issue}"
            )

    # 返回全部事件语法和安全错误。
    return list_errors

# Summaries Markdown 只执行长期文本安全检查。
def memory_summary_errors(project: Path, path_summaries: Path) -> list[str]:
    """检查 memory summaries Markdown 是否包含敏感文本。

    Args:
        project: 项目根目录。
        path_summaries: memory summaries Markdown 路径。

    Returns:
        带项目相对路径的摘要安全错误列表。
    """

    # 缺失摘要文件由路径检查负责报告。
    if not path_summaries.exists():

        # 当前层避免重复文件缺失诊断。
        return []

    # 忽略无效字节以仍能发现可读敏感片段。
    str_text = path_summaries.read_text(  # 读取压缩摘要以执行敏感信息扫描
        encoding="utf-8",  # 摘要文档文本编码
        errors="ignore",  # 损坏字节容错策略
    )  # summaries Markdown 文本

    # 每个安全错误附加稳定的项目相对路径。
    return [
        f"{rel(project, path_summaries)}: {str_issue}"
        for str_issue in unsafe_summary_text(str_text)
    ]

# Memory 总验证汇总合同、路径、数据库、事件、摘要和 bootstrap 证据。
def verify_memory(project: Path) -> dict[str, Any]:
    """验证项目 memory 治理资产和索引完整性。

    Args:
        project: 项目根目录。

    Returns:
        启用状态、检查路径和完整错误列表组成的验证报告。
    """

    # Memory 合同决定是否启用后续资产检查。
    dict_contract = memory_contract(project)  # 项目 memory 合同

    # 禁用状态对强控制项目构成阻断错误。
    if not dict_contract["enabled"]:

        # 非强控制项目允许显式禁用 memory。
        list_errors = (
            ["memory governance must be enabled for strong-control work folders"]  # 强控制禁用诊断
            if strong_control_profile(project)  # 强控制工作目录判定
            else []  # 普通项目允许显式禁用 memory
        )  # memory 禁用错误

        # 禁用报告不声明任何已检查资产。
        return {
            "project": str(project),
            "enabled": False,
            "checked": [],
            "errors": list_errors,
        }

    # 启用合同只保留非 disabled 类配置错误。
    list_contract_errors = [
        str_item  # 合同校验返回的单项诊断
        for str_item in memory_contract_errors(dict_contract)  # 合同诊断迭代来源
        if "disabled" not in str_item  # 禁用状态已由上方分支处理
    ]  # memory 合同配置错误

    # 合同错误会使路径映射不再可靠。
    if list_contract_errors:

        # 直接返回配置错误，避免派生误导性文件诊断。
        return {
            "project": str(project),
            "enabled": True,
            "checked": [],
            "errors": list_contract_errors,
        }

    # 验证阶段统一定位数据库、日志、摘要和引导状态。
    dict_paths = memory_paths(project)  # 验证职责使用的 memory 路径

    # 基础路径检查同时生成 checked 证据。
    tuple_list_checked, tuple_list_errors = memory_path_findings(project, dict_paths)  # 路径覆盖与错误结果

    # 数据库结构与索引覆盖错误追加到总报告。
    tuple_list_errors.extend(memory_database_errors(project, dict_paths["database"]))

    # Events JSONL 语法和安全错误追加到总报告。
    tuple_list_errors.extend(memory_event_errors(project, dict_paths["events"]))

    # Summaries Markdown 安全错误追加到总报告。
    tuple_list_errors.extend(memory_summary_errors(project, dict_paths["summaries"]))

    # Bootstrap 状态也属于验证覆盖证据。
    tuple_list_checked.append(rel(project, dict_paths["bootstrap_state"]))

    # 历史精确工作目录会话必须全部完成引导。
    tuple_list_errors.extend(bootstrap_errors(project))

    # 返回所有验证职责汇总后的稳定报告字段。
    return {
        "project": str(project),
        "enabled": True,
        "checked": tuple_list_checked,
        "errors": tuple_list_errors,
    }

# Memory 初始化门禁区分现有资产错误和需要授权创建的缺失资产。
def memory_gate(project: Path) -> dict[str, Any]:
    """检查 memory 是否可用并给出授权初始化建议。

    Args:
        project: 项目根目录。

    Returns:
        门禁状态、缺失路径、验证错误和建议命令组成的报告。
    """

    # 门禁合同决定启用状态和初始化授权策略。
    dict_contract = memory_contract(project)  # Memory 门禁合同

    # 缺失资产发现需要完整的受管路径集合。
    dict_paths = memory_paths(project)  # 初始化门禁使用的 memory 路径

    # 复用基础路径检查并只保留缺失资产路径。
    tuple_ignored_checked, tuple_list_path_errors = memory_path_findings(project, dict_paths)  # 门禁路径发现结果

    # 从结构化缺失诊断提取项目相对路径。
    list_missing = [
        str_error.split(": ", 1)[1]  # 从缺失诊断中提取项目相对路径
        for str_error in tuple_list_path_errors  # 缺失路径诊断迭代来源
        if ": " in str_error  # 仅解析标准路径缺失诊断
    ]  # 需要初始化创建的 memory 路径

    # 完整验证提供 schema、安全和 bootstrap 错误。
    dict_verify = verify_memory(project)  # memory 完整验证报告

    # 复制错误列表避免修改验证报告对象。
    list_errors = list(dict_verify.get("errors", []))  # 门禁累计错误

    # 缺失路径补充统一的授权型诊断。
    for str_missing in list_missing:

        # 统一消息用于 UI 判断创建授权需求。
        str_error = f"missing memory path: {str_missing}"  # 缺失路径授权诊断

        # 避免与已有完全相同诊断重复。
        if str_error not in list_errors:

            # 保留路径发现顺序追加错误。
            list_errors.append(str_error)

    # 禁用合同和缺失资产都需要用户授权初始化。
    bool_disabled = not bool(dict_contract.get("enabled"))  # memory 合同禁用标志

    # 任一条件成立都禁止无授权地初始化项目资产。
    bool_requires_authorization = bool(bool_disabled or list_missing)  # 初始化授权需求

    # 建议命令包含明确的 confirm-create 安全开关。
    str_command = (
        "python skills/agents-md-generator/scripts/python/docs/manage_docs.py "
        "memory-init <project> --confirm-create"
    )  # memory 初始化授权命令

    # 返回 UI 和 CLI 共同消费的稳定门禁字段。
    return {
        "project": str(project),
        "ok": not list_errors and not bool_requires_authorization,
        "enabled": bool(dict_contract.get("enabled")),
        "missing": list_missing,
        "checked": dict_verify.get("checked", []),
        "requires_user_authorization": bool_requires_authorization,
        "recommended_authorization_command": (
            str_command if bool_requires_authorization else ""
        ),
        "errors": list_errors,
    }

# Memory 长期文本在写入前统一替换三类敏感内容。
def sanitize_memory_text(text: str) -> str:
    """清理 memory 文本中的凭据、私钥和本地路径。

    Args:
        text: 待清理的原始文本。

    Returns:
        使用类型化占位符替换敏感内容后的文本。
    """

    # 凭据赋值保留键名前缀，便于理解原始语义。
    str_sanitized = SECRET_RE.sub(  # 替换疑似凭据赋值内容
        lambda match: f"{match.group(1)}=<REDACTED_SECRET>",  # 保留凭据键名但隐藏值
        text,  # 原始 memory 文本
    )  # 已清理凭据赋值的文本

    # 私钥正文整体替换，禁止保留任何密钥片段。
    str_sanitized = PRIVATE_KEY_RE.sub(  # 移除完整私钥文本块
        "<REDACTED_PRIVATE_KEY>",  # 私钥正文替换标记
        str_sanitized,  # 已移除凭据的文本
    )  # 已清理私钥材料的文本

    # 本地用户路径替换为类型化占位符。
    str_sanitized = LOCAL_PRIVATE_PATH_RE.sub(  # 隐去本地用户目录路径
        "<REDACTED_LOCAL_PATH>",  # 本地路径替换标记
        str_sanitized,  # 已移除私钥的文本
    )  # 已清理本地路径的文本

    # 返回可安全写入长期 memory 的文本。
    return str_sanitized

# 会话摘要只保留前十条可读消息并限制总长度。
def compact_session_summary(
    messages: list[dict[str, str]],
    limit: int = 700,
) -> str:
    """把 Codex 会话消息压缩为安全的单行摘要。

    Args:
        messages: 按时间排序的用户和助手消息。
        limit: 摘要最大字符数。

    Returns:
        已清理敏感文本并截断的单行摘要。
    """

    # 无可读消息时写入明确占位说明。
    if not messages:

        # 占位内容区分空会话与读取失败。
        return "No user or assistant message content was available in this Codex session."

    # 每条消息转换为角色前缀的单行片段。
    list_parts: list[str] = []  # 会话摘要消息片段

    # 最多处理前十条消息以限制摘要成本和长度。
    for dict_row in messages[:10]:

        # 非用户角色统一按助手消息显示。
        str_role = "User" if dict_row.get("role") == "user" else "Assistant"  # 消息角色标签

        # 折叠原始消息中的换行和连续空白。
        str_message = " ".join(  # 折叠当前消息中的空白字符
            str(dict_row.get("message", "")).split()  # 当前消息的空白分词
        )  # 单行消息文本

        # 空消息不占用摘要配额。
        if not str_message:

            # 继续扫描后续可读消息。
            continue

        # 角色标签保留对话归属信息。
        list_parts.append(f"{str_role}: {str_message}")

    # 拼接后统一执行敏感信息清理。
    str_summary = sanitize_memory_text(" | ".join(list_parts))  # 安全会话摘要

    # 字符上限在清理后应用，避免截断占位符。
    return str_summary[:limit].rstrip()

# 单个历史会话先转换为临时输入，再通过统一写入入口持久化。
def write_bootstrap_session(
    project: Path,
    dict_session: dict[str, Any],
    int_sequence: int,
) -> dict[str, Any]:
    """把一个匹配会话写入项目 memory。

    Args:
        project: 项目根目录。
        dict_session: 匹配到的 Codex 会话元数据。
        int_sequence: 本次写入使用的全局顺序号。

    Returns:
        Memory 写入结果以及用于更新引导状态的会话记录。
    """

    # 会话标识同时用于来源引用和临时文件隔离。
    str_session_id = str(dict_session.get("id", "")).strip()  # Codex 会话标识

    # 会话文件只读取有限消息，防止历史引导生成过大的摘要。
    path_session = Path(str(dict_session.get("path", "")))  # Codex 会话文件

    # 消息提取上限约束单次引导的输入规模。
    list_messages = session_message_rows(path_session, limit=24)  # 会话消息记录

    # 摘要在进入数据库前完成敏感信息清理和长度限制。
    str_summary = compact_session_summary(list_messages)  # 可持久化会话摘要

    # 临时输入沿用 write_memory 的公开数据合同。
    dict_input_data = {  # Memory 写入载荷
        "kind": "codex-session",  # 会话历史条目类型
        "title": f"Codex session {str_session_id}",  # 可检索会话标题
        "summary": str_summary,  # 已清理敏感信息的会话摘要
        "source_path": "",  # 会话来源使用匿名 source_ref 而非本地路径
        "source_ref": f"codex-session:{str_session_id}",  # 匿名会话来源引用
        "source_timestamp": str(dict_session.get("timestamp", "")),  # 会话来源时间戳
        "sequence": int_sequence,  # 当前会话的全局历史序号
        "tags": ["codex-session", "history", "memory-bootstrap"],  # 历史引导检索标签
        "sensitivity": "normal",  # 历史会话默认敏感级别
        "created_at": str(dict_session.get("timestamp", "")) or now_iso(),  # 原会话创建时间
        "updated_at": now_iso(),  # 本次历史引导写入时间
    }  # 符合通用 write_memory 合同的会话载荷

    # 每个会话使用独立临时文件，避免覆盖其他未完成写入。
    path_temp = project / ".agents" / f"memory-session-{str_session_id}.json"  # 临时输入文件

    # 临时目录可能尚未由其他治理命令创建。
    path_temp.parent.mkdir(exist_ok=True)

    # JSON 文件作为通用写入入口的稳定交换格式。
    path_temp.write_text(
        json.dumps(dict_input_data, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # 数据库和事件日志由统一写入入口保持一致。
    dict_result = write_memory(project, path_temp)  # Memory 写入结果

    # 临时载荷不属于仓库事实，写入完成后尽力删除。
    try:

        # 写入完成后移除仅供桥接使用的 JSON 文件。
        path_temp.unlink()

    # Windows 文件占用不应覆盖已经成功的 memory 写入结果。
    except OSError:

        # 清理失败留给后续会话治理统一处理。
        pass

    # 状态记录使用哈希而不暴露工作站上的绝对会话路径。
    dict_session_record = {  # 已处理会话状态
        "id": str_session_id,  # 已完成引导的会话标识
        "timestamp": str(dict_session.get("timestamp", "")),  # 原始会话时间
        "path_hash": hashlib.sha256(str(dict_session.get("path", "")).encode("utf-8")).hexdigest(),  # 隐去绝对路径的指纹
        "source_hash": file_hash(path_session),  # 会话文件内容完整性指纹
        "sequence": int_sequence,  # Bootstrap 状态中的全局历史序号
    }  # 不含绝对路径的已处理会话证据

    # 调用方同时需要写入结果和状态记录来决定是否继续。
    return {"result": dict_result, "session_record": dict_session_record}

# 历史引导只处理当前项目精确工作目录匹配且尚未记录的会话。
def bootstrap_sessions(project: Path) -> dict[str, Any]:
    """按时间顺序把当前项目的 Codex 历史会话引导进 memory。

    Args:
        project: 项目根目录。

    Returns:
        匹配数量、成功写入会话和压缩结果组成的报告。
    """

    # 引导前先保证 memory 存储结构可用。
    dict_init_result = init_memory(project)  # 历史会话引导前的初始化结果

    # 初始化失败时不得创建部分引导状态。
    if dict_init_result.get("errors"):

        # 失败报告保留稳定字段，便于 CLI 消费。
        return {
            "project": str(project),
            "processed": 0,
            "processed_session_ids": [],
            "errors": list(dict_init_result["errors"]),
        }

    # 稳定排序确保相同输入每次得到相同序号。
    list_sessions = sorted(  # 按时间和会话标识固定历史处理顺序
        matched_codex_sessions(project),  # 精确工作目录匹配会话
        key=lambda item: (str(item.get("timestamp", "")), str(item.get("id", ""))),  # 稳定排序键
    )

    # 已持久化状态用于实现可重复执行。
    dict_state = bootstrap_state(project)  # 历史引导状态

    # 非列表旧状态按空集合处理，避免传播损坏结构。
    list_processed_sessions = (
        list(dict_state.get("processed_sessions", []))  # 复制既有状态记录
        if isinstance(dict_state.get("processed_sessions"), list)  # 只接受列表状态
        else []  # 损坏或旧格式状态按空记录处理
    )  # 已处理会话状态列表

    # 标识集合用于常量时间判断会话是否已经导入。
    set_processed_ids = {
        str(item.get("id", "")).strip()  # 状态条目中的会话标识
        for item in list_processed_sessions  # 已处理状态中的结构化条目
        if isinstance(item, dict) and str(item.get("id", "")).strip()  # 过滤无效状态项
    }  # 已处理会话标识集合

    # 本轮列表只记录新成功写入的会话。
    list_written_ids: list[str] = []  # 本次成功写入的会话标识

    # 新序号从既有状态中的最大值继续递增。
    int_sequence = max(  # 从历史最大序号继续分配
        [int(item.get("sequence") or 0) for item in list_processed_sessions if isinstance(item, dict)] or [0]  # 已用序号
    )  # 当前最大顺序号

    # 新会话逐个写入，任一失败都保留已成功结果并立即停止。
    for dict_session in list_sessions:

        # 当前标识决定跳过与写入状态更新。
        str_session_id = str(dict_session.get("id", "")).strip()  # 当前会话标识

        # 缺失标识或已处理会话不应重复写入。
        if not str_session_id or str_session_id in set_processed_ids:

            # 跳过不会推进顺序号或改变状态文件。
            continue

        # 每个待写入会话占用一个连续顺序号。
        int_sequence += 1  # 当前新会话占用下一序号

        # 单会话 helper 隔离临时文件生命周期和写入载荷构造。
        dict_written = write_bootstrap_session(project, dict_session, int_sequence)  # 单会话写入报告

        # 内层结果用于判断当前会话是否真正写入成功。
        dict_result = dict_written["result"]  # 当前历史会话的写入状态

        # 写入失败时不把当前会话登记为已处理。
        if dict_result.get("errors"):

            # 返回本次已经完成的会话，支持后续安全续跑。
            return {
                "project": str(project),
                "processed": len(list_written_ids),
                "processed_session_ids": list_written_ids,
                "errors": dict_result["errors"],
            }

        # 成功记录进入持久化 bootstrap 状态。
        list_processed_sessions.append(dict_written["session_record"])

        # 本轮结果单独保留，供 CLI 报告增量。
        list_written_ids.append(str_session_id)

    # 完整状态在本轮写入结束后一次性落盘。
    dict_new_state = {  # 新历史引导状态
        "generated_at": now_iso(),  # Bootstrap 状态生成时间
        "match_scope": "exact-cwd",  # 会话匹配边界
        "matched_session_count": len(list_sessions),  # 本次发现的精确目录会话数
        "processed_sessions": list_processed_sessions,  # 历史与本轮已处理会话记录
    }  # 覆盖全部历史与本轮会话的引导状态

    # 路径映射定位 bootstrap 状态与压缩摘要输出。
    dict_paths = memory_paths(project)  # Bootstrap 状态持久化路径集合

    # 状态父目录在首次引导时可能尚不存在。
    dict_paths["bootstrap_state"].parent.mkdir(parents=True, exist_ok=True)

    # 状态文件采用稳定键排序以减少无意义 diff。
    dict_paths["bootstrap_state"].write_text(
        json.dumps(dict_new_state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # 引导完成后同步重建人类可读摘要。
    dict_compress = compress_memory(project)  # Memory 压缩报告

    # 成功报告同时给出状态文件证据和压缩错误。
    return {
        "project": str(project),
        "matched_session_count": len(list_sessions),
        "processed": len(list_written_ids),
        "processed_session_ids": list_written_ids,
        "bootstrap_state": rel(project, dict_paths["bootstrap_state"]),
        "compression": dict_compress,
        "errors": dict_compress.get("errors", []),
    }

# 推荐信息只在项目声明了有效 memory 合同时出现。
def memory_read_recommendation(project: Path, query: str = "current task") -> dict[str, Any] | None:
    """生成当前项目的 memory 读取建议。

    Args:
        project: 项目根目录。
        query: 建议命令使用的默认查询。

    Returns:
        有效合同时返回读取建议，否则返回 ``None``。
    """

    # 合同同时提供读取策略和指南路径。
    dict_contract = memory_contract(project)  # 读取建议所依据的 memory 合同

    # 无效合同不能生成看似可执行的建议。
    if memory_contract_errors(dict_contract):

        # 缺失有效策略时调用方不应展示 memory 命令。
        return None

    # 命令保持公开 CLI 的稳定参数格式。
    return {
        "enabled": True,
        "policy": dict_contract["read_policy"],
        "guide": dict_contract["guide"],
        "command": (
            "python skills/agents-md-generator/scripts/python/docs/manage_docs.py "
            f'memory-read <project> --query "{query}" --limit 5'
        ),
    }

# Handoff 摘要兼容当前字段名和历史别名，避免旧会话丢失语义。
def handoff_summary(data: dict[str, Any], count: int) -> str:
    """把 handoff 结构压缩为可检索的单行摘要。

    Args:
        data: Handoff 输入数据。
        count: Handoff 顺序号。

    Returns:
        保留计划、进度、问题和验证证据的单行文本。
    """

    # 每个分段优先读取当前字段，再兼容历史字段别名。
    list_parts = [  # Handoff 摘要分段
        f"Handoff #{count}.",  # Handoff 顺序标题
        "Plan: "  # 原始计划分段前缀
        + list_lines(data.get("original_plan_and_steps") or data.get("original_plan") or data.get("plan")).replace(  # 兼容计划字段别名
            "\n",  # 原计划中的换行符
            " ",  # 单行摘要使用的空格替换值
        ),
        "Current step: " + list_lines(data.get("current_step")).replace("\n", " "),  # 当前执行位置
        "Resolved: " + list_lines(data.get("resolved") or data.get("resolved_problems")).replace("\n", " "),  # 已解决事项
        "Remaining: " + list_lines(data.get("remaining") or data.get("remaining_problems")).replace("\n", " "),  # 未解决事项
        "Next: " + list_lines(data.get("next") or data.get("next_work")).replace("\n", " "),  # 后续工作
        "Verification: "  # 验证证据分段前缀
        + list_lines(data.get("verification") or data.get("verification_evidence")).replace("\n", " "),  # 验证证据
    ]  # 兼容新旧 handoff 字段的可检索文本分段

    # 空分段不应在最终摘要中产生多余空格。
    return " ".join(str_part for str_part in list_parts if str_part.strip()).strip()

# Handoff 写入复用通用 memory 入口，并按事件阈值触发摘要压缩。
def write_handoff_memory(
    project: Path,
    data: dict[str, Any],
    count: int,
    handoff_path: Path,
) -> dict[str, Any] | None:
    """把已生成的 handoff 记录写入项目 memory。

    Args:
        project: 项目根目录。
        data: Handoff 输入数据。
        count: Handoff 顺序号。
        handoff_path: 已生成的 handoff 文件路径。

    Returns:
        写入报告；项目未启用 memory 时返回 ``None``。
    """

    # 未启用 memory 的项目保持 handoff 流程无副作用。
    if not memory_enabled(project):

        # None 明确表示项目策略选择不写入 memory。
        return None

    # 初始化确保统一写入入口所需的数据库和日志存在。
    init_memory(project)

    # 临时载荷引用真实 handoff 文件及其内容哈希。
    dict_temp_input = {  # 引用 handoff 文件与哈希的 memory 载荷
        "kind": "handoff",  # Handoff memory 条目类型
        "title": f"Handoff #{count}",  # 可检索 handoff 标题
        "summary": handoff_summary(data, count),  # 单行可检索 handoff 摘要
        "source_path": rel(project, handoff_path),  # 项目相对 handoff 路径
        "source_hash": file_hash(handoff_path),  # Handoff 文件内容完整性指纹
        "tags": ["handoff", "session"],  # Handoff 会话检索标签
        "sensitivity": "normal",  # Handoff 默认敏感级别
    }  # 指向真实 handoff 文件及哈希的写入载荷

    # 固定临时路径只在当前同步调用范围内使用。
    path_temp = project / ".agents" / "memory-handoff-input.json"  # Handoff 专用交换文件

    # 首次 handoff 前确保治理临时目录存在。
    path_temp.parent.mkdir(exist_ok=True)

    # 通用入口从 UTF-8 JSON 读取 handoff memory 条目。
    path_temp.write_text(
        json.dumps(dict_temp_input, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # 通用入口负责同步数据库、搜索索引和事件日志。
    dict_result = write_memory(project, path_temp)  # Handoff memory 写入报告

    # 临时输入不是项目交付物，写入后尽力删除。
    try:

        # 成功写入后移除一次性交换文件。
        path_temp.unlink()

    # 文件锁等清理异常不应伪装成数据库写入失败。
    except OSError:

        # 残留文件由后续治理清理流程识别。
        pass

    # 事件数决定是否达到合同声明的压缩周期。
    dict_paths = memory_paths(project)  # 事件计数所需日志路径集合

    # 非空 JSONL 行数就是当前压缩阈值计数基准。
    int_event_count = sum(  # 统计事件日志中的非空记录
        1  # 每个非空事件贡献一次计数
        for str_line in dict_paths["events"].read_text(encoding="utf-8", errors="ignore").splitlines()  # 事件日志行
        if str_line.strip()  # 空白行不计入事件数量
    )  # 当前事件总数

    # 写入报告附带事件计数，支持调用方展示压缩边界。
    dict_result["event_count"] = int_event_count  # 暴露压缩周期计数证据

    # 合同缺省值保持与 memory 初始化配置一致。
    int_threshold = int(memory_contract(project).get("compress_after_events", 20) or 20)  # 压缩事件阈值

    # 只在正阈值的整数倍触发压缩，避免每次 handoff 重写摘要。
    if int_threshold > 0 and int_event_count % int_threshold == 0:

        # 压缩证据与本次 handoff 写入结果一并返回。
        dict_result["compression"] = compress_memory(project)  # 达阈值后的压缩报告

    # 返回写入证据以及可选的压缩报告。
    return dict_result
