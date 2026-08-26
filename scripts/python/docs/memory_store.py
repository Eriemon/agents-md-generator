"""维护 memory 事件、摘要和校验。"""

# memory 管理依赖。
from __future__ import annotations

# 分类脚本可从任意任务目录直接执行，这里补齐兄弟任务模块路径。
import sys
from pathlib import Path

# 裸模块兼容路径由函数集中登记，避免模块顶层出现循环控制流。
def extend_task_module_search_path() -> None:
    """把任务子目录加入模块路径。

    参数：无。返回：无。
    """

    # Python 脚本根包含 docs 依赖的公共任务模块。
    path_scripts_python_root = Path(__file__).resolve().parents[1]  # 各任务分类脚本共同父目录

    # 逐个登记目录，保持历史裸模块导入兼容。
    for path_task_directory in path_scripts_python_root.iterdir():

        # 文件资产不能承载可导入的任务模块。
        if path_task_directory.is_dir():

            # sys.path 接收字符串路径，避免依赖隐式 Path 转换。
            str_task_directory = str(path_task_directory)  # 待登记的任务模块目录

            # 已存在的目录不重复插入，保持导入优先级稳定。
            if str_task_directory not in sys.path:

                # 兄弟任务模块必须在后续裸模块导入前可见。
                sys.path.insert(0, str_task_directory)

# 依赖导入前完成一次兼容路径登记。
extend_task_module_search_path()

# 导入 memory 管理 所需的依赖模块。
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

# 导入 memory 管理 所需的依赖模块。
from manage_docs_shared import (
    file_hash,
    list_lines,
    matched_codex_sessions,
    project_profile,
    read_json,
    session_message_rows,
)

# memory 契约归一化与校验独立维护，避免存储实现超过源码尺寸门禁。
from memory_contracts import (
    DEFAULT_CAPTURE_SCOPE,
    DEFAULT_READ_POLICY,
    DEFAULT_SENSITIVITY_POLICY,
    memory_contract,
    memory_contract_errors,
)

# 主表 schema 固定保存条目事实、来源、时间和敏感级别。
MEMORY_TABLE_SQL = """CREATE TABLE IF NOT EXISTS memory_items (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  source_path TEXT NOT NULL,
  source_hash TEXT NOT NULL,
  source_ref TEXT NOT NULL DEFAULT '',
  source_timestamp TEXT NOT NULL DEFAULT '',
  sequence INTEGER NOT NULL DEFAULT 0,
  tags_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  sensitivity TEXT NOT NULL
)"""  # 记忆条目持久化主表语句

# FTS5 trigram 表为中英文长词提供全文召回能力。
MEMORY_FTS_SQL = """CREATE VIRTUAL TABLE IF NOT EXISTS memory_items_fts USING fts5(
  item_id UNINDEXED,
  kind,
  title,
  summary,
  source_path,
  source_ref,
  tags_json,
  sensitivity,
  tokenize='trigram'
)"""  # 记忆条目全文检索索引语句

# 普通倒排表补充 trigram 无法覆盖的短词查询。
MEMORY_TERMS_SQL = """CREATE TABLE IF NOT EXISTS memory_item_terms (
  item_id TEXT NOT NULL,
  term TEXT NOT NULL,
  PRIMARY KEY (item_id, term)
)"""  # 记忆条目短词倒排索引语句

# 固定 SELECT 列顺序必须与 MEMORY_ITEM_KEYS 一一对应。
MEMORY_ITEM_SELECT_COLUMNS = (  # 记忆库记录检索流程输入值
    "id, kind, title, summary, source_path, source_hash, source_ref, "
    "source_timestamp, sequence, tags_json, created_at, updated_at, sensitivity"
)

# 查询位置元组依据该字段序列恢复为条目映射。
MEMORY_ITEM_KEYS = [  # 数据库行恢复时使用的固定字段顺序
    "id",  # 条目主键
    "kind",  # 记忆类别
    "title",  # 条目标题
    "summary",  # 条目摘要
    "source_path",  # 条目来源路径
    "source_hash",  # 来源内容哈希
    "source_ref",  # 来源会话引用
    "source_timestamp",  # 来源事件时间
    "sequence",  # 来源事件序号
    "tags_json",  # 标签 JSON 检索文本
    "created_at",  # 首次创建时间
    "updated_at",  # 最近更新时间
    "sensitivity",  # 敏感级别检索字段
]

# schema 完整性检查复用查询合同中的全部字段。
MEMORY_REQUIRED_COLUMNS = set(MEMORY_ITEM_KEYS)  # 当前主表必须具备的字段集合

# 搜索文本排除内部哈希和时间字段，减少不可读噪声。
MEMORY_SEARCH_TEXT_KEYS = [  # 纳入全文与短词索引的条目字段
    "kind",  # 记忆类别字段
    "title",  # 标题检索文本
    "summary",  # 摘要检索文本
    "source_path",  # 来源路径检索文本
    "source_ref",  # 来源引用检索文本
    "tags_json",  # 标签 JSON 检索字段
    "sensitivity",  # 敏感级别检索文本
]

# 主表排序、分类和短词定位使用固定二级索引集合。
MEMORY_SEARCH_INDEXES = {  # 搜索与常用排序需要的二级索引定义
    "idx_memory_items_updated_at": (  # 最近更新时间排序索引
        "CREATE INDEX IF NOT EXISTS idx_memory_items_updated_at "
        "ON memory_items(updated_at)"
    ),
    "idx_memory_items_sequence": (  # 来源事件序号排序索引
        "CREATE INDEX IF NOT EXISTS idx_memory_items_sequence "
        "ON memory_items(sequence)"
    ),
    "idx_memory_items_kind": (  # 记忆类别筛选索引
        "CREATE INDEX IF NOT EXISTS idx_memory_items_kind ON memory_items(kind)"  # 类别字段索引语句
    ),
    "idx_memory_item_terms_term": (  # 短词精确定位索引
        "CREATE INDEX IF NOT EXISTS idx_memory_item_terms_term "
        "ON memory_item_terms(term)"
    ),
}

# 新项目默认只捕获可复用事实，并通过秘密扫描放行显式脱敏占位符。
SECRET_RE = re.compile(  # memory 文本中的凭据模式
    r"(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password)\s*[:=]\s*(?!<REDACTED_)[^\s,;]+"  # 常见秘密键值模式
)

# PEM 私钥头无论密钥类型都属于不可持久化内容。
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")  # PEM 私钥标记

# Windows 用户盘和 Unix 用户目录绝对路径均视为本机私有位置。
LOCAL_PRIVATE_PATH_RE = re.compile(  # 本机用户目录绝对路径扫描器
    r"(?:[A-Za-z]:[\\/]|/(?:Users|home)/)[^\s]+"  # Windows 与 Unix 用户路径形式
)  # 本机用户目录绝对路径模式

# 统一使用秒级本地时间，避免持久化记录出现不一致的精度。
def now_iso() -> str:
    """生成秒级本地时间。

    参数：无。返回：ISO 8601 文本。
    """

    # 记忆事件只需要秒级排序，不写入运行环境相关的微秒噪声。
    return datetime.now().isoformat(timespec="seconds")

# 路径展示优先使用仓库相对路径，仓库外路径则保留可诊断值。
def rel(project: Path, path: Path) -> str:
    """将路径转换为适合治理结果展示的 POSIX 文本。

    Args:
        project: 项目根目录。
        path: 待展示路径。

    Returns:
        仓库内相对路径或仓库外完整路径。
    """

    # relative_to 对仓库外路径会抛错，此处将其视为合法展示场景。
    try:

        # 仓库内路径保持可移植，避免诊断绑定本机绝对路径。
        return path.relative_to(project).as_posix()

    # 相对转换失败说明目标不位于项目根下，需要保留完整位置。
    except ValueError:

        # 无法相对化的目标按原始层级展示，避免构造错误的仓库内位置。
        return path.as_posix()

# enabled 探测复用完整契约归一化，避免产生第二套兼容规则。
def memory_enabled(project: Path) -> bool:
    """判断项目是否启用 memory 治理。

    Args:
        project: 项目根目录。

    Returns:
        memory 契约是否启用。
    """

    # 返回归一化契约中的最终开关，而不是直接读取潜在旧字段。
    return bool(memory_contract(project).get("enabled"))

# 所有 memory 文件路径都从同一归一化契约派生。
def memory_paths(project: Path) -> dict[str, Path]:
    """解析项目的 memory 持久化路径。

    Args:
        project: 项目根目录。

    Returns:
        以用途命名的绝对 Path 映射。
    """

    # 所有用途路径共同依赖同一份归一化契约。
    dict_contract = memory_contract(project)  # memory 路径配置

    # Path 拼接保留相对配置语义，并由调用方处理创建或验证。
    return {
        "folder": project / str(dict_contract["folder"]),
        "database": project / str(dict_contract["database"]),
        "events": project / str(dict_contract["events"]),
        "summaries": project / str(dict_contract["summaries"]),
        "guide": project / str(dict_contract["guide"]),
        "bootstrap_state": project / str(dict_contract["bootstrap_state"]),
    }

# 增量迁移只补充历史数据库缺失的兼容字段。
def migrate_memory_schema(conn: sqlite3.Connection) -> None:
    """将 memory 主表迁移到当前基础字段集合。

    Args:
        conn: 已创建 memory 主表的数据库连接。

    Returns:
        None: 迁移直接提交到给定数据库连接。
    """

    # 先保留 PRAGMA 行，便于明确其第二列承载字段名。
    list_schema_rows = conn.execute(  # 用于提取既有字段名的 PRAGMA 结果
        "PRAGMA table_info(memory_items)"  # 查询主表字段描述
    ).fetchall()  # 主表 schema 描述行

    # 现有字段集合决定三个兼容迁移是否需要执行。
    set_columns = {str(item[1]) for item in list_schema_rows}  # 控制兼容列 ALTER 的既有字段集合

    # 字段名映射到固定 ALTER 语句，避免动态拼接外部标识符。
    dict_migrations = {  # 可重复检测的 schema 迁移语句
        "source_ref": "ALTER TABLE memory_items ADD COLUMN source_ref TEXT NOT NULL DEFAULT ''",  # 来源引用迁移
        "source_timestamp": "ALTER TABLE memory_items ADD COLUMN source_timestamp TEXT NOT NULL DEFAULT ''",  # 来源时间迁移
        "sequence": "ALTER TABLE memory_items ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0",  # 来源序号迁移
    }

    # 每个迁移语句均可重复检查，已有字段不会再次执行 ALTER TABLE。
    for column, statement in dict_migrations.items():

        # 仅执行当前数据库确实缺失的迁移。
        if column not in set_columns:

            # 迁移语句来自固定映射，不接收外部 SQL 输入。
            conn.execute(statement)

    # 迁移在搜索索引初始化前持久化，保证后续读取看到完整列集。
    conn.commit()

# 搜索表只能在主表字段完整后创建，防止旧数据库查询失败。
def memory_base_schema_complete(conn: sqlite3.Connection) -> bool:
    """判断 memory 主表是否具备当前实现要求的全部字段。

    Args:
        conn: memory 数据库连接。

    Returns:
        必需字段是否全部存在。
    """

    # PRAGMA 的第二列保存字段名，用集合判断避免依赖字段顺序。
    set_columns = {  # 基础 schema 完整性判断使用的字段集合
        str(item[1])  # schema 完整性检查使用的字段名
        for item in conn.execute("PRAGMA table_info(memory_items)").fetchall()  # 完整性检查的 schema 行
    }  # 完整性判断使用的主表字段集合

    # 额外历史字段允许保留，只要求当前字段为必需集合的子集。
    return MEMORY_REQUIRED_COLUMNS.issubset(set_columns)

# 检索 token 统一去除边界空白并折叠大小写。
def normalize_search_token(value: str) -> str:
    """归一化单个 memory 检索词。

    Args:
        value: 原始检索词。

    Returns:
        去除边界空白并转为小写的文本。
    """

    # 保留词内符号，由上游分词规则决定允许的字符。
    return value.strip().lower()

# 查询分词与索引侧共享相同的英文数字符号边界。
def query_terms(query: str) -> list[str]:
    """从用户查询中提取归一化检索词。

    Args:
        query: 用户输入的搜索文本。

    Returns:
        保持出现顺序的非空检索词。
    """

    # 正则保留单词、点和连字符，以支持版本号与路径片段。
    return [normalize_search_token(term) for term in re.findall(r"[\w.-]+", query) if term.strip()]

# 仅聚合契约声明的可检索字段，避免索引内部时间戳等噪声。
def memory_search_text(item: dict[str, Any]) -> str:
    """拼接 memory 条目的全文检索文本。

    Args:
        item: memory 条目字段映射。

    Returns:
        按固定字段顺序连接的检索文本。
    """

    # 缺失字段按空文本处理，兼容迁移中的历史条目。
    return " ".join(str(item.get(key, "")) for key in MEMORY_SEARCH_TEXT_KEYS)

# 短词倒排索引补充 FTS trigram 不擅长的短查询和中文双字查询。
def memory_index_terms(item: dict[str, Any]) -> list[str]:
    """为 memory 条目生成受限的短词倒排集合。

    Args:
        item: memory 条目字段映射。

    Returns:
        排序、去重并限制数量的索引词列表。
    """

    # 索引文本先统一大小写，确保英文词查询不区分大小写。
    str_text = memory_search_text(item).lower()  # 当前条目的可检索文本

    # 集合同时实现英文 token 和中文双字窗口的去重。
    set_terms: set[str] = set()  # 当前条目的短词索引集合

    # 英文、数字、版本号和路径片段使用与查询侧一致的分词边界。
    for token in re.findall(r"[\w.-]+", str_text):

        # 单词 token 与查询侧使用同一个归一化函数。
        str_normalized = normalize_search_token(token)  # 当前归一化索引词

        # 过滤空值、单字符噪声和异常长 token，限制索引膨胀。
        if 1 <= len(str_normalized) <= 64:

            # 集合保证同一条目内的重复词只写入一次。
            set_terms.add(str_normalized)

    # 连续中文文本按双字窗口建立短词索引，支持小于 trigram 的查询。
    for cjk_run in re.findall(r"[\u3400-\u9fff]+", str_text):

        # 长度不足两个字符时不产生窗口。
        for index in range(max(len(cjk_run) - 1, 0)):

            # 相邻双字窗口在中文检索召回率与索引体积之间取平衡。
            set_terms.add(cjk_run[index : index + 2])

    # 确定性排序便于测试和重建，512 上限防止单条记录占用过多索引。
    return sorted(set_terms)[:512]

# SQLite 行顺序由固定 SELECT 列契约定义，此处恢复为字段映射。
def row_to_memory_item(row: tuple[Any, ...]) -> dict[str, Any]:
    """将 memory 查询结果行转换为条目映射。

    Args:
        row: 与 ``MEMORY_ITEM_KEYS`` 顺序一致的数据库行。

    Returns:
        以 memory 字段名为键的条目映射。
    """

    # 固定键序列与 SELECT 常量共同维护行到字段的对应关系。
    return dict(zip(MEMORY_ITEM_KEYS, row))

# 单条同步先清除旧索引，再从主表条目重建两个检索后端。
def sync_memory_search_item(conn: sqlite3.Connection, item: dict[str, Any]) -> None:
    """同步一条 memory 记录的全文与短词索引。

    Args:
        conn: memory 数据库连接。
        item: 含主键和可检索字段的 memory 条目。

    Returns:
        None: 搜索索引直接写入给定数据库连接。
    """

    # 两类搜索表都以主表 ID 作为关联键。
    str_item_id = str(item.get("id", "")).strip()  # 待同步条目的主键

    # 无主键条目无法关联搜索表，直接忽略以保护索引完整性。
    if not str_item_id:

        # 调用方可继续处理其他合法条目。
        return

    # 删除旧全文索引，确保 REPLACE 主表后不保留陈旧字段。
    conn.execute("DELETE FROM memory_items_fts WHERE item_id = ?", (str_item_id,))

    # 短词表同样按主键清空后重建。
    conn.execute("DELETE FROM memory_item_terms WHERE item_id = ?", (str_item_id,))

    # 全文索引保存全部可检索字段的当前快照。
    conn.execute(
        """
        INSERT INTO memory_items_fts
        (item_id, kind, title, summary, source_path, source_ref, tags_json, sensitivity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str_item_id,
            str(item.get("kind", "")),
            str(item.get("title", "")),
            str(item.get("summary", "")),
            str(item.get("source_path", "")),
            str(item.get("source_ref", "")),
            str(item.get("tags_json", "")),
            str(item.get("sensitivity", "")),
        ),
    )

    # 每个去重短词与同一主键建立倒排关系。
    conn.executemany(
        "INSERT OR IGNORE INTO memory_item_terms (item_id, term) VALUES (?, ?)",
        [(str_item_id, term) for term in memory_index_terms(item)],
    )

# 全量重建用于迁移后索引缺失或计数不一致的恢复场景。
def rebuild_memory_search_index(conn: sqlite3.Connection) -> None:
    """从 memory 主表重建全部搜索索引。

    Args:
        conn: memory 数据库连接。

    Returns:
        None: 两类搜索索引直接写入给定数据库连接。
    """

    # 全量恢复以主表为事实来源，先清除现有全文索引。
    conn.execute("DELETE FROM memory_items_fts")

    # 短词倒排表也必须从空状态重建，避免孤立记录。
    conn.execute("DELETE FROM memory_item_terms")

    # 使用固定列契约读取所有主表记录，避免 SELECT 星号受迁移影响。
    list_rows = conn.execute(  # 主表中的全部索引重建来源记录
        f"SELECT {MEMORY_ITEM_SELECT_COLUMNS} FROM memory_items"  # 完整主表字段
    ).fetchall()  # 用于重建索引的主表记录

    # 每条记录复用增量同步逻辑，保持全量与单条索引语义一致。
    for row in list_rows:

        # 数据库行先还原为字段映射，再生成两个搜索索引。
        sync_memory_search_item(conn, row_to_memory_item(row))

# 搜索 schema 初始化同时负责发现并修复索引漂移。
def ensure_memory_search_schema(conn: sqlite3.Connection) -> None:
    """创建 memory 搜索表、索引并修复计数漂移。

    Args:
        conn: 已完成基础迁移的 memory 数据库连接。

    Returns:
        None: schema 与索引修复直接提交到给定连接。
    """

    # 历史损坏数据库不应继续创建依赖缺失字段的搜索结构。
    if not memory_base_schema_complete(conn):

        # 基础 schema 的修复责任留给迁移或上层错误处理。
        return

    # 创建支持中文 trigram 的全文虚拟表。
    conn.execute(MEMORY_FTS_SQL)

    # 创建补充短词查询的普通倒排表。
    conn.execute(MEMORY_TERMS_SQL)

    # 二级索引定义来自固定映射，重复执行 CREATE IF NOT EXISTS 是安全的。
    for statement in MEMORY_SEARCH_INDEXES.values():

        # 逐项建立主表与短词表的常用查询索引。
        conn.execute(statement)

    # 主表记录数是检索覆盖完整性的基准。
    int_item_count = conn.execute("SELECT COUNT(*) FROM memory_items").fetchone()[0]  # 主表条目数

    # 全文表应与主表保持一条记录对应一个索引快照。
    int_fts_count = conn.execute("SELECT COUNT(*) FROM memory_items_fts").fetchone()[0]  # 全文索引条目数

    # 短词表只比较具备至少一个索引词的不同主键数量。
    int_term_item_count = conn.execute(  # 至少拥有一个短词的主表条目数
        "SELECT COUNT(DISTINCT item_id) FROM memory_item_terms"  # 短词覆盖计数
    ).fetchone()[0]  # 短词索引覆盖的条目数

    # 任一搜索后端覆盖不完整时，从主表执行确定性重建。
    if int_item_count != int_fts_count or (int_item_count and int_term_item_count == 0):

        # 主表是事实来源，搜索表不参与冲突合并。
        rebuild_memory_search_index(conn)

    # schema 创建和可能的重建作为同一初始化事务提交。
    conn.commit()

# 打开数据库时集中保证主表、迁移和搜索结构均可用。
def connect_memory_db(path: Path) -> sqlite3.Connection:
    """连接 memory 数据库并确保当前 schema 可用。

    Args:
        path: SQLite 数据库文件路径。

    Returns:
        已完成 schema 初始化的数据库连接。
    """

    # 连接创建后由本函数完成所有 schema 前置条件。
    connection_sqlite_connection: sqlite3.Connection = sqlite3.connect(path)  # 待完成 schema 初始化的数据库连接

    # 主表必须先存在，后续迁移才能读取和补充字段。
    connection_sqlite_connection.execute(MEMORY_TABLE_SQL)

    # 历史数据库补齐当前主表字段。
    migrate_memory_schema(connection_sqlite_connection)

    # 基础字段完整后创建或恢复搜索结构。
    ensure_memory_search_schema(connection_sqlite_connection)

    # 将主表创建、迁移和搜索 schema 作为初始化结果持久化。
    connection_sqlite_connection.commit()

    # 返回仍由调用方管理生命周期的活动连接。
    return connection_sqlite_connection

# memory 指南由契约直接渲染，确保人工文档与机器配置一致。
def memory_guide(contract: dict[str, Any]) -> str:
    """生成项目 memory 治理指南。

    Args:
        contract: 已归一化的 memory 契约。

    Returns:
        可直接写入 ``MEMORY.md`` 的 Markdown 文本。
    """

    # 固定章节用于解释持久化文件和敏感信息边界。
    return "\n".join(
        [
            "# Memory Governance",
            "",
            f"- Enabled: {contract.get('enabled', False)}",
            f"- Storage backend: {contract.get('storage_backend', 'sqlite-plus-jsonl')}",
            f"- Capture scope: {contract.get('capture_scope', DEFAULT_CAPTURE_SCOPE)}",
            f"- Read policy: {contract.get('read_policy', DEFAULT_READ_POLICY)}",
            f"- Sensitivity policy: {contract.get('sensitivity_policy', DEFAULT_SENSITIVITY_POLICY)}",
            "",
            "## Files",
            "- `memory.sqlite3`: query index for durable memory items, including FTS5 and short-term indexes.",
            "- `events.jsonl`: append-only event stream for audit.",
            "- `summaries.md`: compressed human-readable memory.",
            "",
            "## Boundary",
            (
                "Do not store secrets, credentials, or raw local private paths. "
                "Use typed redaction placeholders when a sensitive fact must be referenced."
            ),
            "",
        ]
    )

# 默认契约为显式启用流程提供完整且可序列化的配置。
def default_memory_contract() -> dict[str, Any]:
    """构造新项目使用的默认 memory 契约。

    Args:
        None: 默认值由当前实现定义。

    Returns:
        字段完整且带有界摘要策略的可写入 memory 契约。
    """

    # 默认文件全部位于统一 memory 根目录。
    path_memory_folder = Path("docs") / "memory"  # 默认 memory 根目录

    # 返回新字典，避免调用方修改共享可变状态。
    return {
        "enabled": True,
        "folder": path_memory_folder.as_posix(),
        "storage_backend": "sqlite-plus-jsonl",
        "database": (path_memory_folder / "memory.sqlite3").as_posix(),
        "events": (path_memory_folder / "events.jsonl").as_posix(),
        "summaries": (path_memory_folder / "summaries.md").as_posix(),
        "guide": (path_memory_folder / "MEMORY.md").as_posix(),
        "bootstrap_state": (path_memory_folder / "bootstrap-state.json").as_posix(),
        "capture_scope": DEFAULT_CAPTURE_SCOPE,
        "read_policy": DEFAULT_READ_POLICY,
        "sensitivity_policy": DEFAULT_SENSITIVITY_POLICY,
        "compress_after_events": 20,
        "summary_policy": {  # 有界摘要默认策略
            "mode": "bounded",  # 摘要只作为检索视图
            "max_bytes": 128 * 1024,  # 最大 UTF-8 字节数
            "recent_detail_limit": 50,  # 保留正文的最新事件数量
            "per_summary_chars": 600,  # 单条详情字符数
            "older_index_limit": 500,  # 可回查的历史标题数量
        },
    }

# 显式初始化会把兼容顶层字段与结构化契约一次写回 profile。
def write_enabled_memory_contract(project: Path) -> bool:
    """在项目治理配置中写入已启用的 memory 契约。

    Args:
        project: 项目根目录。

    Returns:
        配置成功写入时恒为 True。
    """

    # 治理配置是启用状态和结构化契约的持久化事实来源。
    path_profile = project / ".agents" / "agents-control.json"  # 项目治理配置文件

    # 初始化场景允许治理目录尚不存在，写入前确保父目录可用。
    path_profile.parent.mkdir(parents=True, exist_ok=True)

    # 已有配置需要保留其他治理字段，新项目则从空配置开始。
    dict_profile = read_json(path_profile) if path_profile.is_file() else {}  # 待更新的项目治理配置

    # 非对象历史配置无法安全合并，按空对象重建 memory 相关字段。
    if not isinstance(dict_profile, dict):

        # 仅舍弃不可解释的顶层值，不影响磁盘上的其他文件。
        dict_profile = {}  # 可写入的项目治理配置

    # 只接受对象形式的既有 memory 契约，避免展开字符串或列表。
    dict_existing_contract = (
        dict_profile.get("memory_contract", {})  # 已有结构化契约覆盖项
        if isinstance(dict_profile.get("memory_contract"), dict)  # 只合并对象契约
        else {}  # 不可合并配置回退为空覆盖项
    )  # 既有 memory 契约覆盖项

    # 用户已有字段覆盖默认值，但显式授权后的 enabled 必须为真。
    dict_contract = {**default_memory_contract(), **dict_existing_contract, "enabled": True}  # 最终启用契约

    # 兼容顶层字段与结构化契约同步写入，供旧版和新版读取端共用。
    dict_profile["memory_enabled"] = True  # 旧读取端使用的启用开关

    # 旧版读取端从顶层字段获取存储后端。
    dict_profile["memory_storage_backend"] = dict_contract["storage_backend"]  # 兼容后端配置

    # 捕获范围同步给尚未读取结构化契约的客户端。
    dict_profile["memory_capture_scope"] = dict_contract["capture_scope"]  # 旧版捕获范围字段

    # 实现前读取要求保持新旧配置面一致。
    dict_profile["memory_read_policy"] = dict_contract["read_policy"]  # 旧版读取策略字段

    # 敏感信息边界必须同步到全部读取端。
    dict_profile["memory_sensitivity_policy"] = dict_contract["sensitivity_policy"]  # 旧版安全策略字段

    # 结构化契约保存完整字段，作为新版读取端事实来源。
    dict_profile["memory_contract"] = dict_contract  # 当前结构化 memory 契约

    # 稳定排序和缩进便于治理审查识别真实配置变化。
    path_profile.write_text(
        json.dumps(dict_profile, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # 写入未抛出异常即可确认启用配置已落盘。
    return True

# 初始化结果统一隐藏本机绝对路径，避免各个提前返回分支重复组装字段。
def memory_init_result(
    project: Path,
    contract: dict[str, Any],
    paths: dict[str, Path],
    **fields: Any,
) -> dict[str, Any]:
    """组装 memory 初始化结果。

    参数：project、contract、paths 为初始化上下文，fields 为可选结果字段。
    返回：路径已转为项目相对形式的结果。
    """

    # 所有初始化出口共享核心字段，避免诊断分支产生 schema 漂移。
    dict_result: dict[str, Any] = {  # 当前待返回的初始化结果
        "project": str(project),  # 项目根用于命令层显示
        "enabled": contract["enabled"],  # 当前 memory 启用状态
        "created": fields.get("created") or [],  # 本次实际创建的设施
        "paths": {  # 转换后的项目相对路径映射
            key: rel(project, value)  # 当前设施的项目相对路径
            for key, value in paths.items()  # 当前契约解析的全部设施路径
        },
        "errors": fields.get("errors") or [],  # 当前初始化阻断项
    }

    # missing 仅在授权探测场景出现，普通结果保持历史字段集合。
    if "missing" in fields:

        # 缺失清单供命令层解释需要创建的设施。
        dict_result["missing"] = fields["missing"]  # 当前缺失的基础设施

    # 授权状态只在调用方明确需要该信号时输出。
    if "requires_user_authorization" in fields:

        # 布尔值保持调用方传入语义，不从错误文本反推。
        dict_result["requires_user_authorization"] = fields["requires_user_authorization"]  # 授权需求状态

    # 统一出口确保所有分支使用同一结果契约。
    return dict_result

# 基础初始化不包含会话 bootstrap 状态，后者由独立恢复流程维护。
def missing_memory_paths(project: Path, paths: dict[str, Path]) -> list[str]:
    """返回缺失的基础 memory 设施路径。

    参数：project 为项目根，paths 为设施路径；返回缺失项的相对路径。
    """

    # bootstrap 状态由会话恢复流程维护，不属于基础初始化设施。
    return [
        rel(project, path)  # 当前缺失设施的项目相对路径
        for key, path in paths.items()  # 当前契约解析的全部设施
        if key != "bootstrap_state"  # 排除独立维护的会话 bootstrap 文件
        and (  # 目录和普通文件使用各自的存在性判定
            (key == "folder" and not path.is_dir())  # memory 根必须为目录
            or (key != "folder" and not path.is_file())  # 其他设施必须为普通文件
        )
    ]

# 每类文本设施使用固定初始语义，已有文件由调用方保持不变。
def initial_memory_text(key: str, contract: dict[str, Any]) -> str:
    """返回 memory 文本设施的初始正文。

    参数：key 为设施类型，contract 为契约；返回对应 UTF-8 正文。
    """

    # 事件流从零事件状态开始，不能伪造初始化事件。
    if key == "events":

        # 空字符串是合法的零事件 JSONL 内容。
        return ""

    # 人工摘要用明确占位符区分零条目与读取失败。
    if key == "summaries":

        # 固定标题保持新建项目的摘要文件可读。
        return "# Memory Summaries\n\nNo memory items recorded yet.\n"

    # guide 必须依据最终契约生成，避免描述授权前状态。
    return memory_guide(contract)

# 文件和数据库创建集中在一个幂等边界内，便于初始化主流程保持只做决策。
def create_memory_facilities(
    project: Path,
    contract: dict[str, Any],
    paths: dict[str, Path],
) -> tuple[list[str], list[str]]:
    """创建缺失的 memory 设施。

    参数：project、contract、paths 为初始化上下文。
    返回：创建路径与数据库错误清单。
    """

    # 创建清单只登记本次新增设施，支持幂等审计。
    list_created: list[str] = []  # 本次创建的项目相对路径

    # 文本设施写入前必须确保 memory 根目录存在。
    paths["folder"].mkdir(parents=True, exist_ok=True)

    # 三类文本设施共享存在性检查和 UTF-8 写入边界。
    for key in ("events", "summaries", "guide"):

        # 目标路径来自治理契约，不在创建阶段重新拼接。
        path_target = paths[key]  # 当前待检查的文本设施路径

        # 已有设施必须保持原内容，初始化只补齐缺失项。
        if path_target.exists():

            # 继续检查下一类文本设施。
            continue

        # 初始正文由设施类型和最终契约共同决定。
        path_target.write_text(initial_memory_text(key, contract), encoding="utf-8")

        # 审计清单只保存项目相对路径。
        list_created.append(rel(project, path_target))

    # 数据库连接会创建缺失文件，因此在连接前登记新增状态。
    if not paths["database"].exists():

        # 数据库路径同样转换为项目相对形式。
        list_created.append(rel(project, paths["database"]))

    # 打开数据库同时验证或建立 schema，损坏状态转换为治理错误。
    try:

        # 上下文结束时立即回收初始化连接。
        with closing(connect_memory_db(paths["database"])):

            # 空主体表示本步骤只验证连接和 schema 副作用。
            pass

    # SQLite 错误不能以未处理堆栈中断命令层。
    except sqlite3.DatabaseError as exc:

        # 错误消息仅包含项目相对数据库位置。
        str_database_path = rel(project, paths["database"])  # 失败数据库的项目相对路径

        # 保留已创建清单并返回数据库阻断项。
        return list_created, [f"{str_database_path}: SQLite open failed: {exc}"]

    # 无错误表示全部基础设施已经可用。
    return list_created, []

# 初始化流程区分只读探测与显式授权创建，不能静默启用治理能力。
def init_memory(
    project: Path,
    *,
    confirm_create: bool = False,
    require_confirmation: bool = False,
) -> dict[str, Any]:
    """检查或初始化项目的 memory 持久化设施。

    Args:
        project: 项目根目录。
        confirm_create: 是否已获得创建并启用 memory 的明确授权。
        require_confirmation: 缺少设施时是否必须返回授权要求而不创建。

    Returns:
        包含创建文件、路径、授权状态和错误的初始化结果。
    """

    # 原始 profile 用于区分显式关闭与尚未配置两种状态。
    dict_profile = project_profile(project)  # 当前项目治理配置

    # 只有对象形式的结构化契约能表达显式关闭状态。
    dict_explicit_contract = (
        dict_profile.get("memory_contract")  # 用户显式提供的原始契约
        if isinstance(dict_profile.get("memory_contract"), dict)  # 显式契约类型保护
        else {}  # 未声明结构化契约时使用空对象
    )  # 未补默认值的原始 memory 契约

    # 显式关闭必须区别于缺省关闭，以免普通探测擅自创建治理设施。
    bool_explicitly_disabled = dict_explicit_contract.get("enabled", True) in (False,)  # 用户是否显式关闭 memory

    # 后续路径和错误检查统一使用字段完整的契约。
    dict_contract = memory_contract(project)  # 归一化 memory 契约

    # 契约错误在任何文件写入前完成收集。
    list_contract_errors = memory_contract_errors(dict_contract)  # 当前契约阻断项

    # 返回结果和创建流程共享同一组解析后路径。
    dict_paths = memory_paths(project)  # memory 持久化路径映射

    # 授权判断需要区分契约错误和物理设施缺失。
    list_missing_paths = missing_memory_paths(project, dict_paths)  # 当前缺失的基础 memory 文件

    # 普通探测遇到显式关闭时只返回诊断，不把状态升级为授权请求。
    if bool_explicitly_disabled and list_contract_errors and not confirm_create and not require_confirmation:

        # 路径仍随结果返回，便于调用方解释当前契约指向。
        return memory_init_result(project, dict_contract, dict_paths, errors=list_contract_errors)

    # 受治理入口缺少配置或文件时必须请求用户授权，不能自行创建。
    if require_confirmation and (list_contract_errors or list_missing_paths) and not confirm_create:

        # 授权结果明确列出缺失项和可执行的确认要求。
        return memory_init_result(
            project,
            dict_contract,
            dict_paths,
            missing=list_missing_paths,
            requires_user_authorization=True,
            errors=["memory-init requires explicit --confirm-create before creating or enabling docs/memory"],
        )

    # 非授权模式同样不能越过无效契约继续创建文件。
    if list_contract_errors and not confirm_create:

        # 保留全部契约错误，供命令层决定文本或 JSON 输出。
        return memory_init_result(project, dict_contract, dict_paths, errors=list_contract_errors)

    # 明确授权允许把关闭状态升级为完整启用契约。
    if confirm_create and list_contract_errors:

        # 启用动作先写治理配置，再从磁盘重新读取事实状态。
        write_enabled_memory_contract(project)

        # 重新归一化，避免继续使用授权前的关闭契约。
        dict_contract = memory_contract(project)  # 授权后的 memory 契约

        # 显式授权解决 disabled 错误，其他后端或字段错误仍必须阻断。
        list_contract_errors = [
            item  # 显式授权后仍需报告的非关闭类错误
            for item in memory_contract_errors(dict_contract)  # 授权后重新校验结果
            if "disabled" not in item  # 授权已处理关闭状态
        ]  # 授权后仍未解决的契约错误

        # 契约可能改变目录，必须同步刷新路径映射。
        dict_paths = memory_paths(project)  # 授权后的 memory 路径

        # 非关闭类错误不能通过创建文件修复。
        if list_contract_errors:

            # 返回授权后真实契约和剩余错误，不写入任何 memory 文件。
            return memory_init_result(project, dict_contract, dict_paths, errors=list_contract_errors)

    # 基础设施创建结果同时保留新增清单和数据库错误。
    tuple_creation_result = create_memory_facilities(project, dict_contract, dict_paths)  # 创建结果二元组

    # 新增清单与错误清单按辅助函数返回契约解包。
    list_created = tuple_creation_result[0]  # 本次新建设施的相对路径

    # 数据库打开失败通过独立错误清单传递。
    list_database_errors = tuple_creation_result[1]  # 基础数据库初始化错误

    # 所有初始化出口通过统一组装器返回稳定字段。
    return memory_init_result(
        project,
        dict_contract,
        dict_paths,
        created=list_created,
        errors=list_database_errors,
        requires_user_authorization=False,
    )

# 标签输入允许字符串或列表，最终统一为稳定的去重文本序列。
def normalize_tags(raw: Any) -> list[str]:
    """归一化 memory 条目的标签输入。

    Args:
        raw: 字符串、列表或其他待归一化标签值。

    Returns:
        去空且保持输入顺序的标签列表。
    """

    # 列表输入逐项转为文本并过滤空标签。
    if isinstance(raw, list):

        # 保留原顺序和重复项，与历史写入行为兼容。
        return [str(item).strip() for item in raw if str(item).strip()]

    # 缺失标签统一为空列表，避免持久化 null。
    if raw is None:

        # 空列表可直接序列化为稳定的 JSON 数组。
        return []

    # 文本输入兼容中英文逗号，并过滤分隔产生的空项。
    return [item.strip() for item in str(raw).replace("，", ",").split(",") if item.strip()]

# 来源哈希仅对仓库内真实文件计算，外部或缺失来源保持空值。
def source_hash_for(project: Path, source_path: str) -> str:
    """计算 memory 来源文件的内容哈希。

    Args:
        project: 项目根目录。
        source_path: 相对项目根目录的来源路径。

    Returns:
        来源文件哈希；路径无效或文件缺失时为空字符串。
    """

    # 未声明来源时不计算哈希，允许记录纯会话事实。
    if not source_path:

        # 空字符串是数据库字段的兼容缺省值。
        return ""

    # 输入已由路径治理校验，本函数只负责定位候选文件。
    path_source = project / source_path  # 待计算哈希的来源文件

    # 仅普通文件具备稳定内容哈希，目录或缺失路径保持空值。
    return file_hash(path_source) if path_source.exists() and path_source.is_file() else ""

# 来源路径验证阻止绝对私有路径和越界路径进入持久化记忆。
def source_path_errors(project: Path, source_path: str) -> list[str]:
    """检查 memory 来源路径是否满足仓库边界。

    Args:
        project: 项目根目录。
        source_path: 待验证的来源路径文本。

    Returns:
        路径治理错误列表。
    """

    # 空来源表示没有关联文件，不构成路径错误。
    if not source_path:

        # 无错误结果保持列表合同一致。
        return []

    # Path 解析用于识别绝对路径和规范化后的越界行为。
    path_raw_source = Path(source_path)  # 未与项目根拼接的来源路径

    # 绝对路径会泄露本机布局，任何平台形式都必须拒绝。
    if path_raw_source.is_absolute():

        # 调用方收到稳定错误文本后阻断写入。
        return ["source_path must be project-relative"]

    # resolve 后再做 relative_to，阻止 ``..`` 或符号链接逃逸项目根。
    try:

        # 成功转换为项目相对路径即证明解析后目标仍在边界内。
        (project / path_raw_source).resolve().relative_to(project.resolve())

    # relative_to 失败明确表示解析后的来源逃逸项目边界。
    except ValueError:

        # 越界路径不得进入主表或审计事件。
        return ["source_path must stay inside the project"]

    # 相对且解析后仍在项目内的来源路径通过治理检查。
    return []

# 稳定标识由来源事实和创建时间共同派生，避免依赖数据库自增状态。
def memory_item_id(item: dict[str, Any], created_at: str) -> str:
    """为 memory 条目生成确定性标识。

    Args:
        item: 待写入的 memory 条目。
        created_at: 条目首次创建时间。

    Returns:
        调用方标识或由内容派生的短哈希标识。
    """

    # 调用方显式提供 ID 时保持原值，支持确定性更新已有条目。
    if str(item.get("id", "")).strip():

        # 去除边界空白，避免视觉相同但主键不同的记录。
        return str(item["id"]).strip()

    # 未提供 ID 时以核心事实和创建时间构造稳定哈希种子。
    str_seed = "|".join(  # memory 标识哈希输入
        [
            str(item.get("kind", "note")),  # 标识种子中的类别字段
            str(item.get("title", "")),  # 标识种子中的标题字段
            str(item.get("summary", "")),  # 标识种子中的摘要字段
            str(item.get("source_path", "")),  # 标识种子中的来源路径
            created_at,  # 标识种子中的首次创建时间
        ]
    )

    # 截取 SHA-256 前 16 位，在可读长度和冲突风险之间取平衡。
    return hashlib.sha256(str_seed.encode("utf-8")).hexdigest()[:16]

# 输入解析在写库前限定顶层 JSON 为对象。
def read_memory_input(path: str | Path) -> dict[str, Any]:
    """读取并验证 memory 写入 JSON。

    Args:
        path: JSON 输入文件路径。

    Returns:
        顶层对象形式的 memory 输入。

    Raises:
        SystemExit: JSON 顶层不是对象。
    """

    # 输入路径先解析为绝对位置，再交由共享 JSON 读取器处理。
    dict_data = read_json(Path(path).resolve())  # 解析后的 memory 输入

    # memory 写入合同只接受字段对象，数组或标量无法归一化。
    if not isinstance(dict_data, dict):

        # CLI 输入合同错误使用 SystemExit，保持现有命令退出语义。
        raise SystemExit(f"> ERR: [Python] Input must be a JSON object: {path}")

    # 返回已确认类型的字段对象。
    return dict_data

# 审计事件使用仅追加 JSONL，避免改写历史记录。
def append_event(events_path: Path, event: dict[str, Any]) -> None:
    """向 memory 审计流追加一条事件。

    Args:
        events_path: JSONL 事件文件路径。
        event: 可序列化的审计事件。

    Returns:
        None: 事件直接追加到文件。
    """

    # 首次写入事件时创建父目录，后续调用保持幂等。
    events_path.parent.mkdir(parents=True, exist_ok=True)

    # 文本追加模式保证历史事件永不被当前写入覆盖。
    with events_path.open("a", encoding="utf-8") as handle:

        # 每条事件序列化为单行并以换行终止，维持 JSONL 边界。
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

# 写入流程先完成治理和敏感信息校验，再原子更新主表与搜索索引。
def normalized_memory_text(data: dict[str, Any], key: str, default: str = "") -> str:
    """清理 memory 文本字段。

    参数：data 为载荷，key 为字段，default 为缺省值；返回清理后文本。
    """

    # 外部值统一转为文本，空值先使用字段缺省值。
    str_value = str(data.get(key) or default).strip()  # 清理后的外部字段文本

    # 纯空白输入在清理后再次回退到缺省值。
    return str_value or default

# 时间字段保持调用方提供值，缺失时建立创建与更新时间的一致初值。
def memory_item_timestamps(data: dict[str, Any]) -> tuple[str, str]:
    """归一化 memory 时间字段。

    参数：data 为原始载荷；返回创建时间和更新时间。
    """

    # 缺失创建时间时使用当前秒级时间建立条目事实基准。
    str_created_at = normalized_memory_text(data, "created_at") or now_iso()  # 条目创建时间

    # 首次写入未提供更新时间时与创建时间保持一致。
    str_updated_at = normalized_memory_text(data, "updated_at") or str_created_at  # 条目最近更新时间

    # 调用方按主表字段顺序解包两个时间值。
    return str_created_at, str_updated_at

# 字段归一化与数据库写入分离，使校验只处理统一的主表契约。
def build_memory_item(data: dict[str, Any]) -> dict[str, Any]:
    """构造 memory 主表条目。

    参数：data 为原始载荷；返回含稳定标识的规范条目。
    """

    # 时间字段单独归一化，确保更新时间可回退到最终创建时间。
    tuple_timestamp_values = memory_item_timestamps(data)  # 主表时间字段二元组

    # 创建时间位于时间契约首位。
    str_created_at = tuple_timestamp_values[0]  # 规范条目的首次时刻

    # 更新时间位于时间契约第二位。
    str_updated_at = tuple_timestamp_values[1]  # 规范条目的末次变更时刻

    # 人工 tags 字段优先于历史 tags_json 兼容字段。
    list_tags = normalize_tags(data.get("tags") or data.get("tags_json"))  # 归一化标签

    # 主表条目在安全检查前完成类型和缺省值归一化。
    dict_item = {  # 待校验并写入数据库的 memory 条目
        "id": "",  # 稳定标识稍后基于规范字段生成
        "kind": normalized_memory_text(data, "kind", "note"),  # 主表类别
        "title": normalized_memory_text(data, "title", "Untitled memory"),  # 人工标题
        "summary": normalized_memory_text(data, "summary"),  # 必填摘要
        "source_path": normalized_memory_text(data, "source_path"),  # 仓库相对来源路径
        "source_hash": normalized_memory_text(data, "source_hash"),  # 可选来源文件哈希
        "source_ref": normalized_memory_text(data, "source_ref"),  # 来源引用
        "source_timestamp": normalized_memory_text(data, "source_timestamp"),  # 原始来源事件时刻
        "sequence": int(data.get("sequence") or 0),  # 来源事件顺序
        "tags_json": json.dumps(list_tags, ensure_ascii=False, sort_keys=True),  # 持久化标签
        "created_at": str_created_at,  # 持久化首次创建时刻
        "updated_at": str_updated_at,  # 持久化最近更新时刻
        "sensitivity": normalized_memory_text(data, "sensitivity", "normal"),  # 敏感级别
    }

    # 显式 ID 优先，否则使用规范化内容生成确定性标识。
    dict_item["id"] = memory_item_id({**data, **dict_item}, str_created_at)  # 稳定主键

    # 返回字段完整的条目供安全检查和持久化复用。
    return dict_item

# 全部安全检查在数据库连接前完成，避免失败载荷留下部分持久化副作用。
def memory_item_errors(project: Path, item: dict[str, Any]) -> list[str]:
    """检查 memory 条目安全性。

    参数：project 为项目根，item 为规范条目；返回阻断错误。
    """

    # 空摘要没有可复用事实，禁止写入占位记录。
    if not item["summary"]:

        # 摘要错误在路径和敏感信息扫描前直接返回。
        return ["memory summary must not be empty"]

    # 来源路径必须保持项目相对且不能越过仓库根。
    list_path_errors = source_path_errors(project, item["source_path"])  # 来源路径错误

    # 路径错误不能通过忽略来源哈希来降级。
    if list_path_errors:

        # 返回全部路径错误，避免写入含本机私有路径的条目。
        return list_path_errors

    # 标题、摘要和路径共同接受秘密、私钥与本机绝对路径扫描。
    str_sensitive_surface = " ".join(  # 汇总后执行一次安全扫描的输入文本
        str(item.get(key, ""))  # 当前安全扫描字段值
        for key in ("title", "summary", "source_path")  # 安全扫描字段白名单
    )  # 需要执行敏感信息检查的文本面

    # 统一安全检查器生成稳定的敏感信息诊断。
    return unsafe_summary_text(str_sensitive_surface)

# 查询命令从主表读取完整字段，字段恢复复用统一行契约。
def db_items(project: Path) -> list[dict[str, Any]]:
    """读取项目中的全部 memory 条目。

    Args:
        project: 项目根目录。

    Returns:
        按更新时间降序排列的 memory 条目。
    """

    # 查询路径始终从当前治理契约解析。
    dict_paths = memory_paths(project)  # 全量查询使用的数据库位置

    # 连接生命周期限制在本次只读查询内。
    with closing(connect_memory_db(dict_paths["database"])) as conn:

        # 固定列顺序与行恢复合同保持一致，并按最近更新优先返回。
        list_rows = conn.execute(  # 按更新时间倒序读取的主表记录
            f"SELECT {MEMORY_ITEM_SELECT_COLUMNS} "
            "FROM memory_items ORDER BY updated_at DESC"
        ).fetchall()  # memory 主表查询结果

    # 每个数据库行恢复为字段映射，避免向调用方泄露位置元组。
    return [row_to_memory_item(row) for row in list_rows]

# FTS 查询只接收 trigram 可处理的词，并对短语引号做转义。
def fts_query(terms: list[str]) -> str:
    """构造安全的 FTS5 查询表达式。

    Args:
        terms: 已归一化的检索词。

    Returns:
        使用 OR 连接的 FTS5 短语表达式。
    """

    # trigram 索引不能有效匹配不足三个字符的词，短词由倒排表承担。
    list_fts_terms = [term for term in terms if len(term) >= 3]  # 可交给 FTS5 的检索词

    # 双写内部引号并包裹为短语，防止用户 token 改变 FTS 语法结构。
    return " OR ".join(
        f'"{term.replace(chr(34), chr(34) + chr(34))}"' for term in list_fts_terms
    )

# FTS 后端承担常规全文查询，并按相关度和更新时间排序。
def search_memory_fts(conn: sqlite3.Connection, terms: list[str], limit: int) -> list[dict[str, Any]]:
    """使用 FTS5 查询 memory 条目。

    Args:
        conn: memory 数据库连接。
        terms: 已归一化的检索词。
        limit: 最大结果数量。

    Returns:
        按相关度排序的 memory 条目。
    """

    # 查询构造器会过滤无法由 trigram 处理的短词。
    str_query = fts_query(terms)  # 绑定到 MATCH 的 FTS5 表达式

    # 没有可用 FTS 词时由上层继续尝试短词或 LIKE 后端。
    if not str_query:

        # 空结果表示当前后端未参与，而不是整个搜索失败。
        return []

    # FTS 查询 SQL 单独命名，避免 execute 参数中混入长三引号文本。
    str_select_columns = ", ".join(  # FTS 回连主表后需要返回的字段
        "m." + key for key in MEMORY_ITEM_KEYS  # 回连主表字段
    )  # FTS 查询返回列

    # FTS SQL 由固定行拼接，避免把 Python 注释写入 SQL 字符串。
    str_sql = "\n".join(  # 通过全文索引匹配记忆条目的查询语句
        [
            f"SELECT {str_select_columns}",  # 读取命中的记忆条目列
            "FROM memory_items_fts",  # 使用全文检索索引来源
            "JOIN memory_items m ON m.id = memory_items_fts.item_id",  # 回连记忆主表补全字段
            "WHERE memory_items_fts MATCH ?",  # 使用全文查询表达式筛选
            "ORDER BY bm25(memory_items_fts), m.updated_at DESC",  # 按相关度和更新时间排序
            "LIMIT ?",  # 限制返回候选数量
        ]
    )

    # 参数绑定隔离查询表达式和结果上限，避免拼接外部输入。
    list_rows = conn.execute(  # 全文索引查询命中的记忆条目记录
        str_sql,  # 全文索引查询语句文本
        (str_query, limit),  # FTS 表达式和最大结果数
    ).fetchall()

    # 查询列顺序与主表字段合同一致，可统一恢复条目映射。
    return [row_to_memory_item(row) for row in list_rows]

# 短词后端用于 FTS trigram 无法覆盖的短 token 与中文双字查询。
def search_memory_terms(conn: sqlite3.Connection, terms: list[str], limit: int) -> list[dict[str, Any]]:
    """使用短词倒排表查询 memory 条目。

    Args:
        conn: memory 数据库连接。
        terms: 已归一化的检索词。
        limit: 最大结果数量。

    Returns:
        按命中词数和更新时间排序的 memory 条目。
    """

    # 空词不生成占位符，其他词保持查询输入顺序。
    list_indexed_terms = [term for term in terms if term]  # 短词索引查询参数

    # 无短词时不执行无意义的 IN 查询。
    if not list_indexed_terms:

        # 空结果允许上层选择其他检索后端。
        return []

    # 每个词对应一个绑定参数，占位符数量由归一化列表决定。
    str_placeholders = ", ".join("?" for _ in list_indexed_terms)  # SQL 参数占位符

    # term 查询 SQL 单独命名，便于和动态占位符参数分离。
    str_select_columns = ", ".join("m." + key for key in MEMORY_ITEM_KEYS)  # 短词查询返回列

    # 短词 SQL 组合受控表名、字段名和动态数量的参数占位符。
    str_sql = "\n".join(  # 通过短词索引匹配记忆条目的查询语句
        [
            f"SELECT {str_select_columns}",  # 读取短词命中的记忆条目列
            "FROM memory_item_terms t",  # 使用短词倒排索引来源
            "JOIN memory_items m ON m.id = t.item_id",  # 回连主表补全条目字段
            f"WHERE t.term IN ({str_placeholders})",  # 按用户检索短词筛选
            "GROUP BY m.id",  # 同一记忆条目合并多词命中
            "ORDER BY COUNT(DISTINCT t.term) DESC, m.updated_at DESC",  # 优先返回多词命中新条目
            "LIMIT ?",  # 限制短词候选数量
        ]
    )

    # 检索词和数量上限全部使用参数绑定。
    list_rows = conn.execute(  # 短词索引查询命中的记忆条目记录
        str_sql,  # 短词索引查询语句文本
        (*list_indexed_terms, limit),  # 短词参数后追加结果上限
    ).fetchall()

    # 数据库行恢复为统一的 memory 条目映射。
    return [row_to_memory_item(row) for row in list_rows]

# LIKE 查询保留为搜索扩展不可用时的兼容回退。
def search_memory_like(conn: sqlite3.Connection, terms: list[str], limit: int) -> list[dict[str, Any]]:
    """使用主表 LIKE 条件回退查询 memory 条目。

    Args:
        conn: memory 数据库连接。
        terms: 已归一化的检索词。
        limit: 最大结果数量。

    Returns:
        匹配查询文本的 memory 条目。
    """

    # 回退扫描最多使用五个词，限制条件数量和数据库负担。
    list_like_terms = [term for term in terms if term][:5]  # LIKE 回退检索词

    # 无检索词时不构造空 WHERE 条件。
    if not list_like_terms:

        # 空结果保持三类搜索后端的共同合同。
        return []

    # 回退只扫描声明为可检索的文本字段。
    list_columns = [
        "kind",  # LIKE 扫描的类别字段
        "title",  # LIKE 扫描的标题字段
        "summary",  # LIKE 扫描的摘要字段
        "source_path",  # LIKE 扫描的来源路径字段
        "source_ref",  # LIKE 扫描的来源引用字段
        "tags_json",  # LIKE 扫描的标签 JSON 字段
        "sensitivity",  # LIKE 扫描的敏感级别字段
    ]  # LIKE 回退扫描字段

    # 条件和值分开收集，确保外部词项不进入 SQL 文本。
    list_predicates: list[str] = []  # 动态 LIKE 条件

    # 参数顺序与嵌套循环产生的条件顺序严格一致。
    list_params: list[str] = []  # LIKE 条件绑定值

    # 每个检索词在全部可检索字段上建立模糊匹配。
    for term in list_like_terms:

        # 字段名来自固定白名单，不接受用户输入。
        for column in list_columns:

            # SQL 文本只拼接受控字段名和参数占位符。
            list_predicates.append(f"{column} LIKE ?")

            # 百分号通配符放入绑定值，保留 SQL 结构安全。
            list_params.append(f"%{term}%")

    # LIKE 回退查询 SQL 单独命名，保持搜索条件和值绑定分离。
    str_predicate_sql = " OR ".join(list_predicates)  # LIKE 回退条件表达式

    # 回退 SQL 使用已构造的受控字段谓词扫描主表。
    str_sql = "\n".join(  # 全文索引不可用时按字段模糊匹配的查询语句
        [
            f"SELECT {MEMORY_ITEM_SELECT_COLUMNS}",  # 读取模糊匹配记忆条目列
            "FROM memory_items",  # 直接扫描记忆主表
            f"WHERE {str_predicate_sql}",  # 应用多字段模糊匹配条件
            "ORDER BY updated_at DESC",  # 优先返回最近更新条目
            "LIMIT ?",  # 限制回退候选数量
        ]
    )

    # 回退查询同样通过参数绑定传递搜索值和结果上限。
    list_rows = conn.execute(  # LIKE 回退匹配的主表记录
        str_sql,  # memory LIKE 回退检索 SQL
        (*list_params, limit),  # LIKE 参数后追加结果上限
    ).fetchall()

    # 位置行统一恢复为 memory 条目字段映射。
    return [row_to_memory_item(row) for row in list_rows]
