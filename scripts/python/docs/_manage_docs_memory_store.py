"""维护 docs/memory 的事件、摘要、会话 bootstrap 和校验流程。"""

# 导入 memory 管理 所需的依赖模块。
from __future__ import annotations

# 分类脚本可从任意任务目录直接执行，这里补齐兄弟任务模块路径。
import sys
from pathlib import Path

_scripts_python_root = Path(__file__).resolve().parents[1]
for _task_dir in _scripts_python_root.iterdir():
    if _task_dir.is_dir():
        _task_path = str(_task_dir)
        if _task_path not in sys.path:
            sys.path.insert(0, _task_path)

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
from manage_docs_shared import file_hash, list_lines, matched_codex_sessions, project_profile, read_json, session_message_rows

# 整理 模块入口 需要的 MEMORY TABLE SQL 记忆信息。
MEMORY_TABLE_SQL = "\n".join(  # 创建记忆条目持久化主表的语句
    [
        "CREATE TABLE IF NOT EXISTS memory_items (",  # 创建记忆主表结构
        "  id TEXT PRIMARY KEY,",  # 唯一标识记忆条目
        "  kind TEXT NOT NULL,",  # 区分记忆条目类别
        "  title TEXT NOT NULL,",  # 存放记忆条目标题
        "  summary TEXT NOT NULL,",  # 存放记忆条目摘要
        "  source_path TEXT NOT NULL,",  # 记录记忆来源文件位置
        "  source_hash TEXT NOT NULL,",  # 记录来源文件内容哈希
        "  source_ref TEXT NOT NULL DEFAULT '',",  # 记录来源会话引用
        "  source_timestamp TEXT NOT NULL DEFAULT '',",  # 记录来源事件时间
        "  sequence INTEGER NOT NULL DEFAULT 0,",  # 保留来源事件排序序号
        "  tags_json TEXT NOT NULL,",  # 存放检索标签序列化文本
        "  created_at TEXT NOT NULL,",  # 记录首次入库时间
        "  updated_at TEXT NOT NULL,",  # 记录最近更新时间
        "  sensitivity TEXT NOT NULL",  # 标记记忆敏感级别
        ")",  # 结束记忆主表结构
    ]
)

# 整理 模块入口 需要的 MEMORY FTS SQL 记忆信息。
MEMORY_FTS_SQL = "\n".join(  # 创建记忆条目全文检索索引表的语句
    [
        "CREATE VIRTUAL TABLE IF NOT EXISTS memory_items_fts USING fts5(",  # 创建全文检索虚拟表
        "  item_id UNINDEXED,",  # 关联记忆主表条目
        "  kind,",  # 索引记忆类别文本
        "  title,",  # 索引记忆标题文本
        "  summary,",  # 索引记忆摘要文本
        "  source_path,",  # 索引来源位置文本
        "  source_ref,",  # 索引来源引用文本
        "  tags_json,",  # 索引标签序列化文本
        "  sensitivity,",  # 索引敏感级别文本
        "  tokenize='trigram'",  # 使用三元切分支持中文检索
        ")",  # 结束全文检索虚拟表
    ]
)

# 整理 模块入口 需要的 MEMORY TERMS SQL 记忆信息。
MEMORY_TERMS_SQL = "\n".join(  # 创建记忆条目短词倒排索引表的语句
    [
        "CREATE TABLE IF NOT EXISTS memory_item_terms (",  # 创建短词倒排表结构
        "  item_id TEXT NOT NULL,",  # 关联记忆主表条目
        "  term TEXT NOT NULL,",  # 存放可匹配短词
        "  PRIMARY KEY (item_id, term)",  # 避免同一短词重复入库
        ")",  # 结束短词倒排表结构
    ]
)

# 整理 模块入口 需要的 MEMORY ITEM SELECT COLUMNS 记忆信息。
MEMORY_ITEM_SELECT_COLUMNS = (  # 记忆库记录检索流程输入值
    "id, kind, title, summary, source_path, source_hash, source_ref, "  # 记忆库记录检索流程输入值
    "source_timestamp, sequence, tags_json, created_at, updated_at, sensitivity"  # 记忆库记录检索流程输入值
)

# 整理 模块入口 需要的 MEMORY ITEM KEYS 记忆信息。
MEMORY_ITEM_KEYS = [  # 记忆库记录检索流程输入值
    "id",  # 记忆库记录检索流程输入值
    "kind",  # 记忆库记录检索流程输入值
    "title",  # 记忆库记录检索流程输入值
    "summary",  # 记忆库记录检索流程输入值
    "source_path",  # 记忆库记录检索流程输入值
    "source_hash",  # 记忆库记录检索流程输入值
    "source_ref",  # 记忆库记录检索流程输入值
    "source_timestamp",  # 记忆库记录检索流程输入值
    "sequence",  # 记忆库记录检索流程输入值
    "tags_json",  # 记忆库记录检索流程输入值
    "created_at",  # 记忆库记录检索流程输入值
    "updated_at",  # 记忆库记录检索流程输入值
    "sensitivity",  # 记忆库记录检索流程输入值
]

# 整理 模块入口 需要的 MEMORY REQUIRED COLUMNS 记忆信息。
MEMORY_REQUIRED_COLUMNS = set(MEMORY_ITEM_KEYS)  # 记忆库记录检索流程输入值

# 整理 模块入口 需要的 MEMORY SEARCH TEXT KEYS 记忆信息。
MEMORY_SEARCH_TEXT_KEYS = [  # 记忆库记录检索流程输入值
    "kind",  # 记忆库记录检索流程输入值
    "title",  # 记忆库记录检索流程输入值
    "summary",  # 记忆库记录检索流程输入值
    "source_path",  # 记忆库记录检索流程输入值
    "source_ref",  # 记忆库记录检索流程输入值
    "tags_json",  # 记忆库记录检索流程输入值
    "sensitivity",  # 记忆库记录检索流程输入值
]

# 整理 模块入口 需要的 MEMORY SEARCH INDEXES 记忆信息。
MEMORY_SEARCH_INDEXES = {  # 记忆库记录检索流程输入值
    "idx_memory_items_updated_at": "CREATE INDEX IF NOT EXISTS idx_memory_items_updated_at ON memory_items(updated_at)",  # 记忆库记录检索流程输入值
    "idx_memory_items_sequence": "CREATE INDEX IF NOT EXISTS idx_memory_items_sequence ON memory_items(sequence)",  # 记忆库记录检索流程输入值
    "idx_memory_items_kind": "CREATE INDEX IF NOT EXISTS idx_memory_items_kind ON memory_items(kind)",  # 记忆库记录检索流程输入值
    "idx_memory_item_terms_term": "CREATE INDEX IF NOT EXISTS idx_memory_item_terms_term ON memory_item_terms(term)",  # 记忆库记录检索流程输入值
}

# 整理 模块入口 需要的 DEFAULT CAPTURE SCOPE 记忆信息。
DEFAULT_CAPTURE_SCOPE = (  # 记忆库记录检索流程输入值
    "handoff summaries, user-confirmed project preferences, durable decisions, "  # 记忆库记录检索流程输入值
    "validation lessons, and release lessons"  # 记忆库记录检索流程输入值
)

# 整理 模块入口 需要的 DEFAULT READ POLICY 记忆信息。
DEFAULT_READ_POLICY = "read latest handoff plus relevant docs/memory summaries before implementation"  # 记忆库记录检索流程输入值

# 整理 模块入口 需要的 DEFAULT SENSITIVITY POLICY 记忆信息。
DEFAULT_SENSITIVITY_POLICY = "do not store secrets, credentials, or raw local private paths"  # 记忆库记录检索流程输入值

# 整理 模块入口 需要的 SUPPORTED BACKENDS 记忆信息。
SUPPORTED_BACKENDS = {"sqlite-plus-jsonl"}  # 记忆库记录检索流程输入值

# 整理 模块入口 需要的 SECRET RE 记忆信息。
SECRET_RE = re.compile(  # 记忆库记录检索流程输入值
    r"(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password)\s*[:=]\s*(?!<REDACTED_)[^\s,;]+"  # 记忆库记录检索流程输入值
)

# 整理 模块入口 需要的 PRIVATE KEY RE 记忆信息。
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")  # 记忆库记录检索流程输入值

# 整理 模块入口 需要的 LOCAL PRIVATE PATH RE 记忆信息。
LOCAL_PRIVATE_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|/(?:Users|home)/)[^\s]+")  # 记忆库记录检索流程输入值

# 定义 now_iso 的memory 管理处理入口。
def now_iso() -> str:

    # 返回 now_iso 的 memory 载荷。
    return datetime.now().isoformat(timespec="seconds")

# 定义 rel 的memory 管理处理入口。
def rel(project: Path, path: Path) -> str:

    # 保护 rel 中允许失败的外部访问。
    try:

        # 返回 rel 的 memory 载荷。
        return path.relative_to(project).as_posix()
    except ValueError:

        # 返回 rel 的 memory 载荷。
        return path.as_posix()

# 定义 memory_contract 的memory 管理处理入口。
def memory_contract(project: Path) -> dict[str, Any]:

    # 整理 memory_contract 需要的 profile 记忆信息。
    profile = project_profile(project)  # 记忆库记录检索流程输入值

    # 整理 memory_contract 需要的 contract 记忆信息。
    contract = profile.get("memory_contract", {}) if isinstance(profile.get("memory_contract", {}), dict) else {}  # 记忆库记录检索流程输入值

    # 标记 enabled 判断，控制 memory_contract 的分支走向。
    bool_enabled = bool(contract.get("enabled", profile.get("memory_enabled", False)))  # 记忆库记录检索流程输入值

    # 整理 memory_contract 需要的 folder 记忆信息。
    folder = str(contract.get("folder", "docs/memory")).strip() or "docs/memory"  # 记忆库记录检索流程输入值

    # 返回 memory_contract 的 memory 载荷。
    return {
        "enabled": bool_enabled,
        "folder": folder,
        "storage_backend": str(contract.get("storage_backend", profile.get("memory_storage_backend", "sqlite-plus-jsonl"))).strip() or "sqlite-plus-jsonl",
        "database": str(contract.get("database", f"{folder}/memory.sqlite3")).strip() or f"{folder}/memory.sqlite3",
        "events": str(contract.get("events", f"{folder}/events.jsonl")).strip() or f"{folder}/events.jsonl",
        "summaries": str(contract.get("summaries", f"{folder}/summaries.md")).strip() or f"{folder}/summaries.md",
        "guide": str(contract.get("guide", f"{folder}/MEMORY.md")).strip() or f"{folder}/MEMORY.md",
        "bootstrap_state": str(contract.get("bootstrap_state", f"{folder}/bootstrap-state.json")).strip() or f"{folder}/bootstrap-state.json",
        "capture_scope": str(contract.get("capture_scope", profile.get("memory_capture_scope", DEFAULT_CAPTURE_SCOPE))).strip() or DEFAULT_CAPTURE_SCOPE,
        "read_policy": str(contract.get("read_policy", profile.get("memory_read_policy", DEFAULT_READ_POLICY))).strip() or DEFAULT_READ_POLICY,
        "sensitivity_policy": str(
            contract.get(
                "sensitivity_policy",
                profile.get("memory_sensitivity_policy", DEFAULT_SENSITIVITY_POLICY),
            )
        ).strip() or DEFAULT_SENSITIVITY_POLICY,
        "compress_after_events": int(contract.get("compress_after_events", 20) or 20),
    }

# 定义 memory_enabled 的memory 管理处理入口。
def memory_enabled(project: Path) -> bool:

    # 返回 memory_enabled 的 memory 载荷。
    return bool(memory_contract(project).get("enabled"))

# 定义 memory_contract_errors 的memory 管理处理入口。
def memory_contract_errors(contract: dict[str, Any]) -> list[str]:

    # 汇总 errors，作为记忆库读写和压缩候选清单。
    list_errors: list[str] = []  # 记忆库记录检索流程输入值

    # 校验 memory_contract_errors 的 memory 分支条件。
    if not contract.get("enabled"):

        # 追加 memory_contract_errors 的 memory 诊断。
        list_errors.append("memory governance is disabled for this project")

    # 整理 memory_contract_errors 需要的 backend 记忆信息。
    backend = str(contract.get("storage_backend", "")).strip()  # 记忆库记录检索流程输入值

    # 校验 memory_contract_errors 的 memory 分支条件。
    if backend not in SUPPORTED_BACKENDS:

        # 追加 memory_contract_errors 的 memory 诊断。
        list_errors.append(f"memory_storage_backend must be sqlite-plus-jsonl; got {backend or '<empty>'}")

    # 返回 memory_contract_errors 的 memory 载荷。
    return list_errors

# 定义 memory_paths 的memory 管理处理入口。
def memory_paths(project: Path) -> dict[str, Path]:

    # 保存 contract 映射，维持 memory_paths 的字段关系。
    dict_contract = memory_contract(project)  # 记忆库记录检索流程输入值

    # 返回 memory_paths 的 memory 载荷。
    return {
        "folder": project / str(dict_contract["folder"]),
        "database": project / str(dict_contract["database"]),
        "events": project / str(dict_contract["events"]),
        "summaries": project / str(dict_contract["summaries"]),
        "guide": project / str(dict_contract["guide"]),
        "bootstrap_state": project / str(dict_contract["bootstrap_state"]),
    }

# 定义 migrate_memory_schema 的memory 管理处理入口。
def migrate_memory_schema(conn: sqlite3.Connection) -> None:

    # 汇总 columns，作为记忆库读写和压缩候选清单。
    columns = {str(item[1]) for item in conn.execute("PRAGMA table_info(memory_items)").fetchall()}  # 记忆库记录检索流程输入值

    # 汇总 migrations，作为记忆库读写和压缩候选清单。
    dict_migrations = {  # 记忆库记录检索流程输入值
        "source_ref": "ALTER TABLE memory_items ADD COLUMN source_ref TEXT NOT NULL DEFAULT ''",  # 记忆库记录检索流程输入值
        "source_timestamp": "ALTER TABLE memory_items ADD COLUMN source_timestamp TEXT NOT NULL DEFAULT ''",  # 记忆库记录检索流程输入值
        "sequence": "ALTER TABLE memory_items ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0",  # 记忆库记录检索流程输入值
    }

    # 逐项检查 migrate_memory_schema 记忆候选。
    for column, statement in dict_migrations.items():

        # 校验 migrate_memory_schema 的 memory 分支条件。
        if column not in columns:

            # 调用 execute 处理 migrate_memory_schema。
            conn.execute(statement)

    # 调用 commit 处理 migrate_memory_schema。
    conn.commit()

# 定义 memory_base_schema_complete 的memory 管理处理入口。
def memory_base_schema_complete(conn: sqlite3.Connection) -> bool:

    # 汇总 columns，作为记忆库读写和压缩候选清单。
    columns = {str(item[1]) for item in conn.execute("PRAGMA table_info(memory_items)").fetchall()}  # 记忆库记录检索流程输入值

    # 返回 memory_base_schema_complete 的 memory 载荷。
    return MEMORY_REQUIRED_COLUMNS.issubset(columns)

# 定义 normalize_search_token 的memory 管理处理入口。
def normalize_search_token(value: str) -> str:

    # 返回 normalize_search_token 的 memory 载荷。
    return value.strip().lower()

# 定义 query_terms 的memory 管理处理入口。
def query_terms(query: str) -> list[str]:

    # 返回 query_terms 的 memory 载荷。
    return [normalize_search_token(term) for term in re.findall(r"[\w.-]+", query) if term.strip()]

# 定义 memory_search_text 的memory 管理处理入口。
def memory_search_text(item: dict[str, Any]) -> str:

    # 返回 memory_search_text 的 memory 载荷。
    return " ".join(str(item.get(key, "")) for key in MEMORY_SEARCH_TEXT_KEYS)

# 定义 memory_index_terms 的memory 管理处理入口。
def memory_index_terms(item: dict[str, Any]) -> list[str]:

    # 整理 memory_index_terms 需要的 text 记忆信息。
    text = memory_search_text(item).lower()  # 记忆库记录检索流程输入值

    # 汇总 terms，作为记忆库读写和压缩候选清单。
    set_terms: set[str] = set()  # 记忆库记录检索流程输入值

    # 逐项检查 memory_index_terms 记忆候选。
    for token in re.findall(r"[\w.-]+", text):

        # 整理 memory_index_terms 需要的 normalized 记忆信息。
        str_normalized = normalize_search_token(token)  # 记忆库记录检索流程输入值

        # 校验 memory_index_terms 的 memory 分支条件。
        if 1 <= len(str_normalized) <= 64:

            # 调用 add 处理 memory_index_terms。
            set_terms.add(str_normalized)

    # 逐项检查 memory_index_terms 记忆候选。
    for cjk_run in re.findall(r"[\u3400-\u9fff]+", text):

        # 逐项检查 memory_index_terms 记忆候选。
        for index in range(max(len(cjk_run) - 1, 0)):

            # 调用 add 处理 memory_index_terms。
            set_terms.add(cjk_run[index : index + 2])

    # 返回 memory_index_terms 的 memory 载荷。
    return sorted(set_terms)[:512]

# 定义 row_to_memory_item 的memory 管理处理入口。
def row_to_memory_item(row: tuple[Any, ...]) -> dict[str, Any]:

    # 返回 row_to_memory_item 的 memory 载荷。
    return dict(zip(MEMORY_ITEM_KEYS, row))

# 定义 sync_memory_search_item 的memory 管理处理入口。
def sync_memory_search_item(conn: sqlite3.Connection, item: dict[str, Any]) -> None:

    # 整理 sync_memory_search_item 需要的 item id 记忆信息。
    item_id = str(item.get("id", "")).strip()  # 记忆库记录检索流程输入值

    # 校验 sync_memory_search_item 的 memory 分支条件。
    if not item_id:

        # 返回 sync_memory_search_item 的 memory 载荷。
        return

    # 调用 execute 处理 sync_memory_search_item。
    conn.execute("DELETE FROM memory_items_fts WHERE item_id = ?", (item_id,))

    # 调用 execute 处理 sync_memory_search_item。
    conn.execute("DELETE FROM memory_item_terms WHERE item_id = ?", (item_id,))

    # 调用 execute 处理 sync_memory_search_item。
    conn.execute(
        """
        INSERT INTO memory_items_fts
        (item_id, kind, title, summary, source_path, source_ref, tags_json, sensitivity)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item_id,
            str(item.get("kind", "")),
            str(item.get("title", "")),
            str(item.get("summary", "")),
            str(item.get("source_path", "")),
            str(item.get("source_ref", "")),
            str(item.get("tags_json", "")),
            str(item.get("sensitivity", "")),
        ),
    )

    # 调用 executemany 处理 sync_memory_search_item。
    conn.executemany(
        "INSERT OR IGNORE INTO memory_item_terms (item_id, term) VALUES (?, ?)",
        [(item_id, term) for term in memory_index_terms(item)],
    )

# 定义 rebuild_memory_search_index 的memory 管理处理入口。
def rebuild_memory_search_index(conn: sqlite3.Connection) -> None:

    # 调用 execute 处理 rebuild_memory_search_index。
    conn.execute("DELETE FROM memory_items_fts")

    # 调用 execute 处理 rebuild_memory_search_index。
    conn.execute("DELETE FROM memory_item_terms")

    # 汇总 rows，作为记忆库读写和压缩候选清单。
    rows = conn.execute(f"SELECT {MEMORY_ITEM_SELECT_COLUMNS} FROM memory_items").fetchall()  # 记忆库记录检索流程输入值

    # 逐项检查 rebuild_memory_search_index 记忆候选。
    for row in rows:

        # 调用 sync_memory_search_item 处理 rebuild_memory_search_index。
        sync_memory_search_item(conn, row_to_memory_item(row))

# 定义 ensure_memory_search_schema 的memory 管理处理入口。
def ensure_memory_search_schema(conn: sqlite3.Connection) -> None:

    # 校验 ensure_memory_search_schema 的 memory 分支条件。
    if not memory_base_schema_complete(conn):

        # 返回 ensure_memory_search_schema 的 memory 载荷。
        return

    # 调用 execute 处理 ensure_memory_search_schema。
    conn.execute(MEMORY_FTS_SQL)

    # 调用 execute 处理 ensure_memory_search_schema。
    conn.execute(MEMORY_TERMS_SQL)

    # 逐项检查 ensure_memory_search_schema 记忆候选。
    for statement in MEMORY_SEARCH_INDEXES.values():

        # 调用 execute 处理 ensure_memory_search_schema。
        conn.execute(statement)

    # 整理 ensure_memory_search_schema 需要的 item count 记忆信息。
    item_count = conn.execute("SELECT COUNT(*) FROM memory_items").fetchone()[0]  # 记忆库记录检索流程输入值

    # 整理 ensure_memory_search_schema 需要的 fts count 记忆信息。
    fts_count = conn.execute("SELECT COUNT(*) FROM memory_items_fts").fetchone()[0]  # 记忆库记录检索流程输入值

    # 整理 ensure_memory_search_schema 需要的 term item count 记忆信息。
    term_item_count = conn.execute("SELECT COUNT(DISTINCT item_id) FROM memory_item_terms").fetchone()[0]  # 记忆库记录检索流程输入值

    # 校验 ensure_memory_search_schema 的 memory 分支条件。
    if item_count != fts_count or (item_count and term_item_count == 0):

        # 调用 rebuild_memory_search_index 处理 ensure_memory_search_schema。
        rebuild_memory_search_index(conn)

    # 调用 commit 处理 ensure_memory_search_schema。
    conn.commit()

# 定义 connect_memory_db 的memory 管理处理入口。
def connect_memory_db(path: Path) -> sqlite3.Connection:

    # 整理 connect_memory_db 需要的 conn 记忆信息。
    conn = sqlite3.connect(path)  # 记忆库记录检索流程输入值

    # 调用 execute 处理 connect_memory_db。
    conn.execute(MEMORY_TABLE_SQL)

    # 调用 migrate_memory_schema 处理 connect_memory_db。
    migrate_memory_schema(conn)

    # 调用 ensure_memory_search_schema 处理 connect_memory_db。
    ensure_memory_search_schema(conn)

    # 调用 commit 处理 connect_memory_db。
    conn.commit()

    # 返回 connect_memory_db 的 memory 载荷。
    return conn

# 定义 memory_guide 的memory 管理处理入口。
def memory_guide(contract: dict[str, Any]) -> str:

    # 返回 memory_guide 的 memory 载荷。
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
            "Do not store secrets, credentials, or raw local private paths. Use typed redaction placeholders when a sensitive fact must be referenced.",
            "",
        ]
    )

# 定义 default_memory_contract 的memory 管理处理入口。
def default_memory_contract() -> dict[str, Any]:

    # 返回 default_memory_contract 的 memory 载荷。
    return {
        "enabled": True,
        "folder": "docs/memory",
        "storage_backend": "sqlite-plus-jsonl",
        "database": "docs/memory/memory.sqlite3",
        "events": "docs/memory/events.jsonl",
        "summaries": "docs/memory/summaries.md",
        "guide": "docs/memory/MEMORY.md",
        "bootstrap_state": "docs/memory/bootstrap-state.json",
        "capture_scope": DEFAULT_CAPTURE_SCOPE,
        "read_policy": DEFAULT_READ_POLICY,
        "sensitivity_policy": DEFAULT_SENSITIVITY_POLICY,
        "compress_after_events": 20,
    }

# 定义 write_enabled_memory_contract 的memory 管理处理入口。
def write_enabled_memory_contract(project: Path) -> bool:

    # 定位 profile path 的文件边界，供 write_enabled_memory_contract 后续读写校验使用。
    profile_path = project / ".agents" / "agents-control.json"  # 记忆库记录检索流程输入值

    # 调用 mkdir 处理 write_enabled_memory_contract。
    profile_path.parent.mkdir(parents=True, exist_ok=True)

    # 保存 profile 映射，维持 write_enabled_memory_contract 的字段关系。
    dict_profile = read_json(profile_path) if profile_path.is_file() else {}  # 记忆库记录检索流程输入值

    # 校验 write_enabled_memory_contract 的 memory 分支条件。
    if not isinstance(dict_profile, dict):

        # 保存 profile 映射，维持 write_enabled_memory_contract 的字段关系。
        dict_profile = {}  # 记忆库记录检索流程输入值

    # 整理 write_enabled_memory_contract 需要的 existing 记忆信息。
    existing = dict_profile.get("memory_contract", {}) if isinstance(dict_profile.get("memory_contract"), dict) else {}  # 记忆库记录检索流程输入值

    # 保存 contract 映射，维持 write_enabled_memory_contract 的字段关系。
    dict_contract = {**default_memory_contract(), **existing, "enabled": True}  # 记忆库记录检索流程输入值

    # 整理 write_enabled_memory_contract 需要的 中间载荷 记忆信息。
    dict_profile["memory_enabled"] = True  # 记忆库记录检索流程输入值

    # 整理 write_enabled_memory_contract 需要的 中间载荷 记忆信息。
    dict_profile["memory_storage_backend"] = dict_contract["storage_backend"]  # 记忆库记录检索流程输入值

    # 整理 write_enabled_memory_contract 需要的 中间载荷 记忆信息。
    dict_profile["memory_capture_scope"] = dict_contract["capture_scope"]  # 记忆库记录检索流程输入值

    # 整理 write_enabled_memory_contract 需要的 中间载荷 记忆信息。
    dict_profile["memory_read_policy"] = dict_contract["read_policy"]  # 记忆库记录检索流程输入值

    # 整理 write_enabled_memory_contract 需要的 中间载荷 记忆信息。
    dict_profile["memory_sensitivity_policy"] = dict_contract["sensitivity_policy"]  # 记忆库记录检索流程输入值

    # 整理 write_enabled_memory_contract 需要的 中间载荷 记忆信息。
    dict_profile["memory_contract"] = dict_contract  # 记忆库记录检索流程输入值

    # 调用 write_text 处理 write_enabled_memory_contract。
    profile_path.write_text(json.dumps(dict_profile, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    # 返回 write_enabled_memory_contract 的 memory 载荷。
    return True

# 定义 init_memory 的memory 管理处理入口。
def init_memory(project: Path, *, confirm_create: bool = False, require_confirmation: bool = False) -> dict[str, Any]:

    # 整理 init_memory 需要的 profile 记忆信息。
    profile = project_profile(project)  # 记忆库记录检索流程输入值

    # 整理 init_memory 需要的 explicit contract 记忆信息。
    explicit_contract = profile.get("memory_contract") if isinstance(profile.get("memory_contract"), dict) else {}  # 记忆库记录检索流程输入值

    # 整理 init_memory 需要的 explicitly disabled 记忆信息。
    explicitly_disabled = isinstance(explicit_contract, dict) and explicit_contract.get("enabled") is False  # 记忆库记录检索流程输入值

    # 保存 contract 映射，维持 init_memory 的字段关系。
    dict_contract = memory_contract(project)  # 记忆库记录检索流程输入值

    # 汇总 contract errors，作为记忆库读写和压缩候选清单。
    list_contract_errors = memory_contract_errors(dict_contract)  # 记忆库记录检索流程输入值

    # 汇总 paths，作为记忆库读写和压缩候选清单。
    dict_paths = memory_paths(project)  # 记忆库记录检索流程输入值

    # 汇总 missing paths，作为记忆库读写和压缩候选清单。
    missing_paths = [  # 记忆库记录检索流程输入值
        rel(project, path)  # 记忆库记录检索流程输入值
        for key, path in dict_paths.items()  # 记忆库记录检索流程输入值
        if key != "bootstrap_state" and ((key == "folder" and not path.is_dir()) or (key != "folder" and not path.is_file()))  # 记忆库记录检索流程输入值
    ]

    # 校验 init_memory 的 memory 分支条件。
    if explicitly_disabled and list_contract_errors and not confirm_create and not require_confirmation:

        # 返回 init_memory 的 memory 载荷。
        return {
            "project": str(project),
            "enabled": dict_contract["enabled"],
            "created": [],
            "paths": {key: rel(project, value) for key, value in dict_paths.items()},
            "errors": list_contract_errors,
        }

    # 校验 init_memory 的 memory 分支条件。
    if require_confirmation and (list_contract_errors or missing_paths) and not confirm_create:

        # 返回 init_memory 的 memory 载荷。
        return {
            "project": str(project),
            "enabled": dict_contract["enabled"],
            "created": [],
            "paths": {key: rel(project, value) for key, value in dict_paths.items()},
            "missing": missing_paths,
            "requires_user_authorization": True,
            "errors": ["memory-init requires explicit --confirm-create before creating or enabling docs/memory"],
        }

    # 校验 init_memory 的 memory 分支条件。
    if list_contract_errors and not confirm_create:

        # 返回 init_memory 的 memory 载荷。
        return {
            "project": str(project),
            "enabled": dict_contract["enabled"],
            "created": [],
            "paths": {key: rel(project, value) for key, value in dict_paths.items()},
            "errors": list_contract_errors,
        }

    # 校验 init_memory 的 memory 分支条件。
    if confirm_create and list_contract_errors:

        # 调用 write_enabled_memory_contract 处理 init_memory。
        write_enabled_memory_contract(project)

        # 保存 contract 映射，维持 init_memory 的字段关系。
        dict_contract = memory_contract(project)  # 记忆库记录检索流程输入值

        # 汇总 contract errors，作为记忆库读写和压缩候选清单。
        list_contract_errors = [item for item in memory_contract_errors(dict_contract) if "disabled" not in item]  # 记忆库记录检索流程输入值

        # 汇总 paths，作为记忆库读写和压缩候选清单。
        dict_paths = memory_paths(project)  # 记忆库记录检索流程输入值

        # 校验 init_memory 的 memory 分支条件。
        if list_contract_errors:

            # 返回 init_memory 的 memory 载荷。
            return {
                "project": str(project),
                "enabled": dict_contract["enabled"],
                "created": [],
                "paths": {key: rel(project, value) for key, value in dict_paths.items()},
                "errors": list_contract_errors,
            }

    # 汇总 created，作为记忆库读写和压缩候选清单。
    list_created: list[str] = []  # 记忆库记录检索流程输入值

    # 调用 mkdir 处理 init_memory。
    dict_paths["folder"].mkdir(parents=True, exist_ok=True)

    # 逐项检查 init_memory 记忆候选。
    for key in ("events", "summaries", "guide"):

        # 整理 init_memory 需要的 path 记忆信息。
        path = dict_paths[key]  # 记忆库记录检索流程输入值

        # 校验 init_memory 的 memory 分支条件。
        if not path.exists():

            # 校验 init_memory 的 memory 分支条件。
            if key == "events":

                # 整理 init_memory 需要的 content 记忆信息。
                str_content = ""  # 记忆库记录检索流程输入值

            # 校验 init_memory 的 memory 分支条件。
            elif key == "summaries":

                # 整理 init_memory 需要的 content 记忆信息。
                str_content = "# Memory Summaries\n\nNo memory items recorded yet.\n"  # 初始 memory 摘要文件正文
            else:

                # 整理 init_memory 需要的 content 记忆信息。
                str_content = memory_guide(dict_contract)  # 记忆库记录检索流程输入值

            # 调用 write_text 处理 init_memory。
            path.write_text(str_content, encoding="utf-8")

            # 追加 init_memory 的 memory 诊断。
            list_created.append(rel(project, path))

    # 校验 init_memory 的 memory 分支条件。
    if not dict_paths["database"].exists():

        # 追加 init_memory 的 memory 诊断。
        list_created.append(rel(project, dict_paths["database"]))

    # 保护 init_memory 中允许失败的外部访问。
    try:

        # 进入上下文并在退出时回收资源。
        with closing(connect_memory_db(dict_paths["database"])):
            pass
    except sqlite3.DatabaseError as exc:

        # 返回 init_memory 的 memory 载荷。
        return {
            "project": str(project),
            "enabled": dict_contract["enabled"],
            "created": list_created,
            "paths": {key: rel(project, value) for key, value in dict_paths.items()},
            "errors": [f"{rel(project, dict_paths['database'])}: SQLite open failed: {exc}"],
        }

    # 返回 init_memory 的 memory 载荷。
    return {
        "project": str(project),
        "enabled": dict_contract["enabled"],
        "created": list_created,
        "paths": {key: rel(project, value) for key, value in dict_paths.items()},
        "requires_user_authorization": False,
        "errors": [],
    }

# 定义 normalize_tags 的memory 管理处理入口。
def normalize_tags(raw: Any) -> list[str]:

    # 校验 normalize_tags 的 memory 分支条件。
    if isinstance(raw, list):

        # 返回 normalize_tags 的 memory 载荷。
        return [str(item).strip() for item in raw if str(item).strip()]

    # 校验 normalize_tags 的 memory 分支条件。
    if raw is None:

        # 返回 normalize_tags 的 memory 载荷。
        return []

    # 返回 normalize_tags 的 memory 载荷。
    return [item.strip() for item in str(raw).replace("，", ",").split(",") if item.strip()]

# 定义 source_hash_for 的memory 管理处理入口。
def source_hash_for(project: Path, source_path: str) -> str:

    # 校验 source_hash_for 的 memory 分支条件。
    if not source_path:

        # 返回 source_hash_for 的 memory 载荷。
        return ""

    # 整理 source_hash_for 需要的 path 记忆信息。
    path = project / source_path  # 记忆库记录检索流程输入值

    # 返回 source_hash_for 的 memory 载荷。
    return file_hash(path) if path.exists() and path.is_file() else ""

# 定义 source_path_errors 的memory 管理处理入口。
def source_path_errors(project: Path, source_path: str) -> list[str]:

    # 校验 source_path_errors 的 memory 分支条件。
    if not source_path:

        # 返回 source_path_errors 的 memory 载荷。
        return []

    # 定位 raw path 的文件边界，供 source_path_errors 后续读写校验使用。
    path_raw_path = Path(source_path)  # 记忆库记录检索流程输入值

    # 校验 source_path_errors 的 memory 分支条件。
    if path_raw_path.is_absolute():

        # 返回 source_path_errors 的 memory 载荷。
        return ["source_path must be project-relative"]

    # 保护 source_path_errors 中允许失败的外部访问。
    try:

        # 调用 relative_to 处理 source_path_errors。
        (project / path_raw_path).resolve().relative_to(project.resolve())
    except ValueError:

        # 返回 source_path_errors 的 memory 载荷。
        return ["source_path must stay inside the project"]

    # 返回 source_path_errors 的 memory 载荷。
    return []

# 定义 memory_item_id 的memory 管理处理入口。
def memory_item_id(item: dict[str, Any], created_at: str) -> str:

    # 校验 memory_item_id 的 memory 分支条件。
    if str(item.get("id", "")).strip():

        # 返回 memory_item_id 的 memory 载荷。
        return str(item["id"]).strip()

    # 整理 memory_item_id 需要的 seed 记忆信息。
    seed = "|".join(  # 记忆库记录检索流程输入值
        [  # 记忆库记录检索流程输入值
            str(item.get("kind", "note")),  # 记忆库记录检索流程输入值
            str(item.get("title", "")),  # 记忆库记录检索流程输入值
            str(item.get("summary", "")),  # 记忆库记录检索流程输入值
            str(item.get("source_path", "")),  # 记忆库记录检索流程输入值
            created_at,  # 记忆库记录检索流程输入值
        ]
    )

    # 返回 memory_item_id 的 memory 载荷。
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

# 定义 read_memory_input 的memory 管理处理入口。
def read_memory_input(path: str | Path) -> dict[str, Any]:

    # 整理 read_memory_input 需要的 data 记忆信息。
    dict_data = read_json(Path(path).resolve())  # 记忆库记录检索流程输入值

    # 校验 read_memory_input 的 memory 分支条件。
    if not isinstance(dict_data, dict):

        # 抛出 read_memory_input 已确认的阻断原因。
        raise SystemExit(f"Input must be a JSON object: {path}")

    # 返回 read_memory_input 的 memory 载荷。
    return dict_data

# 定义 append_event 的memory 管理处理入口。
def append_event(events_path: Path, event: dict[str, Any]) -> None:

    # 调用 mkdir 处理 append_event。
    events_path.parent.mkdir(parents=True, exist_ok=True)

    # 进入上下文并在退出时回收资源。
    with events_path.open("a", encoding="utf-8") as handle:

        # 调用 write 处理 append_event。
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

# 定义 write_memory 的memory 管理处理入口。
def write_memory(project: Path, input_path: str | Path) -> dict[str, Any]:

    # 保存 init result 映射，维持 write_memory 的字段关系。
    dict_init_result = init_memory(project)  # 记忆库记录检索流程输入值

    # 校验 write_memory 的 memory 分支条件。
    if dict_init_result.get("errors"):

        # 返回 write_memory 的 memory 载荷。
        return {"project": str(project), "written": False, "errors": list(dict_init_result["errors"])}

    # 保存 data 映射，维持 write_memory 的字段关系。
    dict_data = read_memory_input(input_path)  # 记忆库记录检索流程输入值

    # 整理 write_memory 需要的 created at 记忆信息。
    str_created_at = str(dict_data.get("created_at") or now_iso())  # 记忆库记录检索流程输入值

    # 整理 write_memory 需要的 updated at 记忆信息。
    str_updated_at = str(dict_data.get("updated_at") or str_created_at)  # 记忆库记录检索流程输入值

    # 汇总 tags，作为记忆库读写和压缩候选清单。
    list_tags = normalize_tags(dict_data.get("tags") or dict_data.get("tags_json"))  # 记忆库记录检索流程输入值

    # 保存 item 映射，维持 write_memory 的字段关系。
    dict_item = {  # 记忆库记录检索流程输入值
        "id": "",  # 记忆库记录检索流程输入值
        "kind": str(dict_data.get("kind") or "note").strip() or "note",  # 记忆库记录检索流程输入值
        "title": str(dict_data.get("title") or "Untitled memory").strip() or "Untitled memory",  # 记忆库记录检索流程输入值
        "summary": str(dict_data.get("summary") or "").strip(),  # 记忆库记录检索流程输入值
        "source_path": str(dict_data.get("source_path") or "").strip(),  # 记忆库记录检索流程输入值
        "source_hash": str(dict_data.get("source_hash") or "").strip(),  # 记忆库记录检索流程输入值
        "source_ref": str(dict_data.get("source_ref") or "").strip(),  # 记忆库记录检索流程输入值
        "source_timestamp": str(dict_data.get("source_timestamp") or "").strip(),  # 记忆库记录检索流程输入值
        "sequence": int(dict_data.get("sequence") or 0),  # 记忆库记录检索流程输入值
        "tags_json": json.dumps(list_tags, ensure_ascii=False, sort_keys=True),  # 记忆库记录检索流程输入值
        "created_at": str_created_at,  # 记忆库记录检索流程输入值
        "updated_at": str_updated_at,  # 记忆库记录检索流程输入值
        "sensitivity": str(dict_data.get("sensitivity") or "normal").strip() or "normal",  # 记忆库记录检索流程输入值
    }

    # 整理 write_memory 需要的 中间载荷 记忆信息。
    dict_item["id"] = memory_item_id({**dict_data, **dict_item}, str_created_at)  # 记忆库记录检索流程输入值

    # 校验 write_memory 的 memory 分支条件。
    if not dict_item["summary"]:

        # 返回 write_memory 的 memory 载荷。
        return {"project": str(project), "written": False, "errors": ["memory summary must not be empty"]}

    # 汇总 path errors，作为记忆库读写和压缩候选清单。
    list_path_errors = source_path_errors(project, dict_item["source_path"])  # 记忆库记录检索流程输入值

    # 校验 write_memory 的 memory 分支条件。
    if list_path_errors:

        # 返回 write_memory 的 memory 载荷。
        return {"project": str(project), "written": False, "errors": list_path_errors}

    # 汇总 unsafe errors，作为记忆库读写和压缩候选清单。
    list_unsafe_errors = unsafe_summary_text(" ".join(str(dict_item.get(key, "")) for key in ["title", "summary", "source_path"]))  # 记忆库记录检索流程输入值

    # 校验 write_memory 的 memory 分支条件。
    if list_unsafe_errors:

        # 返回 write_memory 的 memory 载荷。
        return {"project": str(project), "written": False, "errors": list_unsafe_errors}

    # 校验 write_memory 的 memory 分支条件。
    if not dict_item["source_hash"]:

        # 整理 write_memory 需要的 中间载荷 记忆信息。
        dict_item["source_hash"] = source_hash_for(project, dict_item["source_path"])  # 记忆库记录检索流程输入值

    # 汇总 paths，作为记忆库读写和压缩候选清单。
    dict_paths = memory_paths(project)  # 记忆库记录检索流程输入值

    # 进入上下文并在退出时回收资源。
    with closing(connect_memory_db(dict_paths["database"])) as conn:

        # 调用 execute 处理 write_memory。
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_items
            (id, kind, title, summary, source_path, source_hash, source_ref, source_timestamp, sequence, tags_json, created_at, updated_at, sensitivity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dict_item["id"],
                dict_item["kind"],
                dict_item["title"],
                dict_item["summary"],
                dict_item["source_path"],
                dict_item["source_hash"],
                dict_item["source_ref"],
                dict_item["source_timestamp"],
                dict_item["sequence"],
                dict_item["tags_json"],
                dict_item["created_at"],
                dict_item["updated_at"],
                dict_item["sensitivity"],
            ),
        )

        # 调用 sync_memory_search_item 处理 write_memory。
        sync_memory_search_item(conn, dict_item)

        # 调用 commit 处理 write_memory。
        conn.commit()

    # 调用 append_event 处理 write_memory。
    append_event(dict_paths["events"], {"event": "memory_write", **dict_item})

    # 返回 write_memory 的 memory 载荷。
    return {
        "project": str(project),
        "written": dict_item,
        "ok": True,
        "id": dict_item["id"],
        "item": dict_item,
        "events": rel(project, dict_paths["events"]),
        "errors": [],
    }

# 定义 db_items 的memory 管理处理入口。
def db_items(project: Path) -> list[dict[str, Any]]:

    # 汇总 paths，作为记忆库读写和压缩候选清单。
    dict_paths = memory_paths(project)  # 记忆库记录检索流程输入值

    # 进入上下文并在退出时回收资源。
    with closing(connect_memory_db(dict_paths["database"])) as conn:

        # 汇总 rows，作为记忆库读写和压缩候选清单。
        rows = conn.execute(f"SELECT {MEMORY_ITEM_SELECT_COLUMNS} FROM memory_items ORDER BY updated_at DESC").fetchall()  # 记忆库记录检索流程输入值

    # 返回 db_items 的 memory 载荷。
    return [row_to_memory_item(row) for row in rows]

# 定义 fts_query 的memory 管理处理入口。
def fts_query(terms: list[str]) -> str:

    # 汇总 fts terms，作为记忆库读写和压缩候选清单。
    fts_terms = [term for term in terms if len(term) >= 3]  # 记忆库记录检索流程输入值

    # 返回 fts_query 的 memory 载荷。
    return " OR ".join(f'"{term.replace(chr(34), chr(34) + chr(34))}"' for term in fts_terms)

# 定义 search_memory_fts 的memory 管理处理入口。
def search_memory_fts(conn: sqlite3.Connection, terms: list[str], limit: int) -> list[dict[str, Any]]:

    # 整理 search_memory_fts 需要的 query 记忆信息。
    str_query = fts_query(terms)  # 记忆库记录检索流程输入值

    # 校验 search_memory_fts 的 memory 分支条件。
    if not str_query:

        # 返回 search_memory_fts 的 memory 载荷。
        return []

    # FTS 查询 SQL 单独命名，避免 execute 参数中混入长三引号文本。
    str_select_columns = ", ".join("m." + key for key in MEMORY_ITEM_KEYS)  # FTS 查询返回列

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

    # 汇总 rows，作为记忆库读写和压缩候选清单。
    rows = conn.execute(  # 全文索引查询命中的记忆条目记录
        str_sql,  # 全文索引查询语句文本
        (str_query, limit),  # 记忆库记录检索流程输入值
    ).fetchall()  # 记忆库记录检索流程输入值

    # 返回 search_memory_fts 的 memory 载荷。
    return [row_to_memory_item(row) for row in rows]

# 定义 search_memory_terms 的memory 管理处理入口。
def search_memory_terms(conn: sqlite3.Connection, terms: list[str], limit: int) -> list[dict[str, Any]]:

    # 汇总 indexed terms，作为记忆库读写和压缩候选清单。
    indexed_terms = [term for term in terms if term]  # 记忆库记录检索流程输入值

    # 校验 search_memory_terms 的 memory 分支条件。
    if not indexed_terms:

        # 返回 search_memory_terms 的 memory 载荷。
        return []

    # 汇总 placeholders，作为记忆库读写和压缩候选清单。
    placeholders = ", ".join("?" for _ in indexed_terms)  # 记忆库记录检索流程输入值

    # term 查询 SQL 单独命名，便于和动态占位符参数分离。
    str_select_columns = ", ".join("m." + key for key in MEMORY_ITEM_KEYS)  # term 查询返回列

    # term SQL 由固定行拼接，避免把 Python 注释写入 SQL 字符串。
    str_sql = "\n".join(  # 通过短词索引匹配记忆条目的查询语句
        [
            f"SELECT {str_select_columns}",  # 读取短词命中的记忆条目列
            "FROM memory_item_terms t",  # 使用短词倒排索引来源
            "JOIN memory_items m ON m.id = t.item_id",  # 回连记忆主表补全字段
            f"WHERE t.term IN ({placeholders})",  # 按用户检索短词筛选
            "GROUP BY m.id",  # 同一记忆条目合并多词命中
            "ORDER BY COUNT(DISTINCT t.term) DESC, m.updated_at DESC",  # 优先返回多词命中新条目
            "LIMIT ?",  # 限制短词候选数量
        ]
    )

    # 汇总 rows，作为记忆库读写和压缩候选清单。
    rows = conn.execute(  # 短词索引查询命中的记忆条目记录
        str_sql,  # 短词索引查询语句文本
        (*indexed_terms, limit),  # 记忆库记录检索流程输入值
    ).fetchall()  # 记忆库记录检索流程输入值

    # 返回 search_memory_terms 的 memory 载荷。
    return [row_to_memory_item(row) for row in rows]

# 定义 search_memory_like 的memory 管理处理入口。
def search_memory_like(conn: sqlite3.Connection, terms: list[str], limit: int) -> list[dict[str, Any]]:

    # 汇总 like terms，作为记忆库读写和压缩候选清单。
    like_terms = [term for term in terms if term][:5]  # 记忆库记录检索流程输入值

    # 校验 search_memory_like 的 memory 分支条件。
    if not like_terms:

        # 返回 search_memory_like 的 memory 载荷。
        return []

    # 汇总 columns，作为记忆库读写和压缩候选清单。
    list_columns = ["kind", "title", "summary", "source_path", "source_ref", "tags_json", "sensitivity"]  # 记忆库记录检索流程输入值

    # 汇总 predicates，作为记忆库读写和压缩候选清单。
    list_predicates: list[str] = []  # 记忆库记录检索流程输入值

    # 汇总 params，作为记忆库读写和压缩候选清单。
    list_params: list[str] = []  # 记忆库记录检索流程输入值

    # 逐项检查 search_memory_like 记忆候选。
    for term in like_terms:

        # 逐项检查 search_memory_like 记忆候选。
        for column in list_columns:

            # 追加 search_memory_like 的 memory 诊断。
            list_predicates.append(f"{column} LIKE ?")

            # 追加 search_memory_like 的 memory 诊断。
            list_params.append(f"%{term}%")

    # LIKE 回退查询 SQL 单独命名，保持搜索条件和值绑定分离。
    str_predicate_sql = " OR ".join(list_predicates)  # LIKE 回退条件表达式

    # LIKE SQL 由固定行拼接，避免把 Python 注释写入 SQL 字符串。
    str_sql = "\n".join(  # 全文索引不可用时按字段模糊匹配的查询语句
        [
            f"SELECT {MEMORY_ITEM_SELECT_COLUMNS}",  # 读取模糊匹配记忆条目列
            "FROM memory_items",  # 直接扫描记忆主表
            f"WHERE {str_predicate_sql}",  # 应用多字段模糊匹配条件
            "ORDER BY updated_at DESC",  # 优先返回最近更新条目
            "LIMIT ?",  # 限制回退候选数量
        ]
    )

    # 汇总 rows，作为记忆库读写和压缩候选清单。
    rows = conn.execute(  # 记忆库记录检索流程输入值
        str_sql,  # memory LIKE 回退检索 SQL
        (*list_params, limit),  # 记忆库记录检索流程输入值
    ).fetchall()  # 记忆库记录检索流程输入值

    # 返回 search_memory_like 的 memory 载荷。
    return [row_to_memory_item(row) for row in rows]

# 定义 read_memory 的memory 管理处理入口。
