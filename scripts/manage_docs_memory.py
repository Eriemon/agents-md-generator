from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

from manage_docs_shared import file_hash, list_lines, matched_codex_sessions, project_profile, read_json, session_message_rows


MEMORY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS memory_items (
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
)
"""

MEMORY_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS memory_items_fts USING fts5(
  item_id UNINDEXED,
  kind,
  title,
  summary,
  source_path,
  source_ref,
  tags_json,
  sensitivity,
  tokenize='trigram'
)
"""

MEMORY_TERMS_SQL = """
CREATE TABLE IF NOT EXISTS memory_item_terms (
  item_id TEXT NOT NULL,
  term TEXT NOT NULL,
  PRIMARY KEY (item_id, term)
)
"""

MEMORY_ITEM_SELECT_COLUMNS = (
    "id, kind, title, summary, source_path, source_hash, source_ref, "
    "source_timestamp, sequence, tags_json, created_at, updated_at, sensitivity"
)
MEMORY_ITEM_KEYS = [
    "id",
    "kind",
    "title",
    "summary",
    "source_path",
    "source_hash",
    "source_ref",
    "source_timestamp",
    "sequence",
    "tags_json",
    "created_at",
    "updated_at",
    "sensitivity",
]
MEMORY_REQUIRED_COLUMNS = set(MEMORY_ITEM_KEYS)
MEMORY_SEARCH_TEXT_KEYS = [
    "kind",
    "title",
    "summary",
    "source_path",
    "source_ref",
    "tags_json",
    "sensitivity",
]
MEMORY_SEARCH_INDEXES = {
    "idx_memory_items_updated_at": "CREATE INDEX IF NOT EXISTS idx_memory_items_updated_at ON memory_items(updated_at)",
    "idx_memory_items_sequence": "CREATE INDEX IF NOT EXISTS idx_memory_items_sequence ON memory_items(sequence)",
    "idx_memory_items_kind": "CREATE INDEX IF NOT EXISTS idx_memory_items_kind ON memory_items(kind)",
    "idx_memory_item_terms_term": "CREATE INDEX IF NOT EXISTS idx_memory_item_terms_term ON memory_item_terms(term)",
}

DEFAULT_CAPTURE_SCOPE = (
    "handoff summaries, user-confirmed project preferences, durable decisions, "
    "validation lessons, and release lessons"
)
DEFAULT_READ_POLICY = "read latest handoff plus relevant docs/memory summaries before implementation"
DEFAULT_SENSITIVITY_POLICY = "do not store secrets, credentials, or raw local private paths"
SUPPORTED_BACKENDS = {"sqlite-plus-jsonl"}
SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|auth[_-]?token|secret|password)\s*[:=]\s*(?!<REDACTED_)[^\s,;]+"
)
PRIVATE_KEY_RE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
LOCAL_PRIVATE_PATH_RE = re.compile(r"(?:[A-Za-z]:\\Users\\|/(?:Users|home)/)[^\s]+")


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def rel(project: Path, path: Path) -> str:
    try:
        return path.relative_to(project).as_posix()
    except ValueError:
        return path.as_posix()


def memory_contract(project: Path) -> dict[str, Any]:
    profile = project_profile(project)
    contract = profile.get("memory_contract", {}) if isinstance(profile.get("memory_contract", {}), dict) else {}
    enabled = bool(contract.get("enabled", profile.get("memory_enabled", False)))
    folder = str(contract.get("folder", "docs/memory")).strip() or "docs/memory"
    return {
        "enabled": enabled,
        "folder": folder,
        "storage_backend": str(contract.get("storage_backend", profile.get("memory_storage_backend", "sqlite-plus-jsonl"))).strip() or "sqlite-plus-jsonl",
        "database": str(contract.get("database", f"{folder}/memory.sqlite3")).strip() or f"{folder}/memory.sqlite3",
        "events": str(contract.get("events", f"{folder}/events.jsonl")).strip() or f"{folder}/events.jsonl",
        "summaries": str(contract.get("summaries", f"{folder}/summaries.md")).strip() or f"{folder}/summaries.md",
        "guide": str(contract.get("guide", f"{folder}/MEMORY.md")).strip() or f"{folder}/MEMORY.md",
        "bootstrap_state": str(contract.get("bootstrap_state", f"{folder}/bootstrap-state.json")).strip() or f"{folder}/bootstrap-state.json",
        "capture_scope": str(contract.get("capture_scope", profile.get("memory_capture_scope", DEFAULT_CAPTURE_SCOPE))).strip() or DEFAULT_CAPTURE_SCOPE,
        "read_policy": str(contract.get("read_policy", profile.get("memory_read_policy", DEFAULT_READ_POLICY))).strip() or DEFAULT_READ_POLICY,
        "sensitivity_policy": str(contract.get("sensitivity_policy", profile.get("memory_sensitivity_policy", DEFAULT_SENSITIVITY_POLICY))).strip() or DEFAULT_SENSITIVITY_POLICY,
        "compress_after_events": int(contract.get("compress_after_events", 20) or 20),
    }


def memory_enabled(project: Path) -> bool:
    return bool(memory_contract(project).get("enabled"))


def memory_contract_errors(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not contract.get("enabled"):
        errors.append("memory governance is disabled for this project")
    backend = str(contract.get("storage_backend", "")).strip()
    if backend not in SUPPORTED_BACKENDS:
        errors.append(f"memory_storage_backend must be sqlite-plus-jsonl; got {backend or '<empty>'}")
    return errors


def memory_paths(project: Path) -> dict[str, Path]:
    contract = memory_contract(project)
    return {
        "folder": project / str(contract["folder"]),
        "database": project / str(contract["database"]),
        "events": project / str(contract["events"]),
        "summaries": project / str(contract["summaries"]),
        "guide": project / str(contract["guide"]),
        "bootstrap_state": project / str(contract["bootstrap_state"]),
    }


def migrate_memory_schema(conn: sqlite3.Connection) -> None:
    columns = {str(item[1]) for item in conn.execute("PRAGMA table_info(memory_items)").fetchall()}
    migrations = {
        "source_ref": "ALTER TABLE memory_items ADD COLUMN source_ref TEXT NOT NULL DEFAULT ''",
        "source_timestamp": "ALTER TABLE memory_items ADD COLUMN source_timestamp TEXT NOT NULL DEFAULT ''",
        "sequence": "ALTER TABLE memory_items ADD COLUMN sequence INTEGER NOT NULL DEFAULT 0",
    }
    for column, statement in migrations.items():
        if column not in columns:
            conn.execute(statement)
    conn.commit()


def memory_base_schema_complete(conn: sqlite3.Connection) -> bool:
    columns = {str(item[1]) for item in conn.execute("PRAGMA table_info(memory_items)").fetchall()}
    return MEMORY_REQUIRED_COLUMNS.issubset(columns)


def normalize_search_token(value: str) -> str:
    return value.strip().lower()


def query_terms(query: str) -> list[str]:
    return [normalize_search_token(term) for term in re.findall(r"[\w.-]+", query) if term.strip()]


def memory_search_text(item: dict[str, Any]) -> str:
    return " ".join(str(item.get(key, "")) for key in MEMORY_SEARCH_TEXT_KEYS)


def memory_index_terms(item: dict[str, Any]) -> list[str]:
    text = memory_search_text(item).lower()
    terms: set[str] = set()
    for token in re.findall(r"[\w.-]+", text):
        normalized = normalize_search_token(token)
        if 1 <= len(normalized) <= 64:
            terms.add(normalized)
    for cjk_run in re.findall(r"[\u3400-\u9fff]+", text):
        for index in range(max(len(cjk_run) - 1, 0)):
            terms.add(cjk_run[index : index + 2])
    return sorted(terms)[:512]


def row_to_memory_item(row: tuple[Any, ...]) -> dict[str, Any]:
    return dict(zip(MEMORY_ITEM_KEYS, row))


def sync_memory_search_item(conn: sqlite3.Connection, item: dict[str, Any]) -> None:
    item_id = str(item.get("id", "")).strip()
    if not item_id:
        return
    conn.execute("DELETE FROM memory_items_fts WHERE item_id = ?", (item_id,))
    conn.execute("DELETE FROM memory_item_terms WHERE item_id = ?", (item_id,))
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
    conn.executemany(
        "INSERT OR IGNORE INTO memory_item_terms (item_id, term) VALUES (?, ?)",
        [(item_id, term) for term in memory_index_terms(item)],
    )


def rebuild_memory_search_index(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM memory_items_fts")
    conn.execute("DELETE FROM memory_item_terms")
    rows = conn.execute(f"SELECT {MEMORY_ITEM_SELECT_COLUMNS} FROM memory_items").fetchall()
    for row in rows:
        sync_memory_search_item(conn, row_to_memory_item(row))


def ensure_memory_search_schema(conn: sqlite3.Connection) -> None:
    if not memory_base_schema_complete(conn):
        return
    conn.execute(MEMORY_FTS_SQL)
    conn.execute(MEMORY_TERMS_SQL)
    for statement in MEMORY_SEARCH_INDEXES.values():
        conn.execute(statement)
    item_count = conn.execute("SELECT COUNT(*) FROM memory_items").fetchone()[0]
    fts_count = conn.execute("SELECT COUNT(*) FROM memory_items_fts").fetchone()[0]
    term_item_count = conn.execute("SELECT COUNT(DISTINCT item_id) FROM memory_item_terms").fetchone()[0]
    if item_count != fts_count or (item_count and term_item_count == 0):
        rebuild_memory_search_index(conn)
    conn.commit()


def connect_memory_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute(MEMORY_TABLE_SQL)
    migrate_memory_schema(conn)
    ensure_memory_search_schema(conn)
    conn.commit()
    return conn


def memory_guide(contract: dict[str, Any]) -> str:
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


def default_memory_contract() -> dict[str, Any]:
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


def write_enabled_memory_contract(project: Path) -> bool:
    profile_path = project / ".agents" / "agents-control.json"
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile = read_json(profile_path) if profile_path.is_file() else {}
    if not isinstance(profile, dict):
        profile = {}
    existing = profile.get("memory_contract", {}) if isinstance(profile.get("memory_contract"), dict) else {}
    contract = {**default_memory_contract(), **existing, "enabled": True}
    profile["memory_enabled"] = True
    profile["memory_storage_backend"] = contract["storage_backend"]
    profile["memory_capture_scope"] = contract["capture_scope"]
    profile["memory_read_policy"] = contract["read_policy"]
    profile["memory_sensitivity_policy"] = contract["sensitivity_policy"]
    profile["memory_contract"] = contract
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return True


def init_memory(project: Path, *, confirm_create: bool = False, require_confirmation: bool = False) -> dict[str, Any]:
    profile = project_profile(project)
    explicit_contract = profile.get("memory_contract") if isinstance(profile.get("memory_contract"), dict) else {}
    explicitly_disabled = isinstance(explicit_contract, dict) and explicit_contract.get("enabled") is False
    contract = memory_contract(project)
    contract_errors = memory_contract_errors(contract)
    paths = memory_paths(project)
    missing_paths = [
        rel(project, path)
        for key, path in paths.items()
        if key != "bootstrap_state" and ((key == "folder" and not path.is_dir()) or (key != "folder" and not path.is_file()))
    ]
    if explicitly_disabled and contract_errors and not confirm_create and not require_confirmation:
        return {
            "project": str(project),
            "enabled": contract["enabled"],
            "created": [],
            "paths": {key: rel(project, value) for key, value in paths.items()},
            "errors": contract_errors,
        }
    if require_confirmation and (contract_errors or missing_paths) and not confirm_create:
        return {
            "project": str(project),
            "enabled": contract["enabled"],
            "created": [],
            "paths": {key: rel(project, value) for key, value in paths.items()},
            "missing": missing_paths,
            "requires_user_authorization": True,
            "errors": ["memory-init requires explicit --confirm-create before creating or enabling docs/memory"],
        }
    if contract_errors and not confirm_create:
        return {
            "project": str(project),
            "enabled": contract["enabled"],
            "created": [],
            "paths": {key: rel(project, value) for key, value in paths.items()},
            "errors": contract_errors,
        }
    if confirm_create and contract_errors:
        write_enabled_memory_contract(project)
        contract = memory_contract(project)
        contract_errors = [item for item in memory_contract_errors(contract) if "disabled" not in item]
        paths = memory_paths(project)
        if contract_errors:
            return {
                "project": str(project),
                "enabled": contract["enabled"],
                "created": [],
                "paths": {key: rel(project, value) for key, value in paths.items()},
                "errors": contract_errors,
            }
    created: list[str] = []
    paths["folder"].mkdir(parents=True, exist_ok=True)
    for key in ("events", "summaries", "guide"):
        path = paths[key]
        if not path.exists():
            if key == "events":
                content = ""
            elif key == "summaries":
                content = "# Memory Summaries\n\nNo memory items recorded yet.\n"
            else:
                content = memory_guide(contract)
            path.write_text(content, encoding="utf-8")
            created.append(rel(project, path))
    if not paths["database"].exists():
        created.append(rel(project, paths["database"]))
    try:
        with closing(connect_memory_db(paths["database"])):
            pass
    except sqlite3.DatabaseError as exc:
        return {
            "project": str(project),
            "enabled": contract["enabled"],
            "created": created,
            "paths": {key: rel(project, value) for key, value in paths.items()},
            "errors": [f"{rel(project, paths['database'])}: SQLite open failed: {exc}"],
        }
    return {
        "project": str(project),
        "enabled": contract["enabled"],
        "created": created,
        "paths": {key: rel(project, value) for key, value in paths.items()},
        "requires_user_authorization": False,
        "errors": [],
    }


def normalize_tags(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if raw is None:
        return []
    return [item.strip() for item in str(raw).replace("，", ",").split(",") if item.strip()]


def source_hash_for(project: Path, source_path: str) -> str:
    if not source_path:
        return ""
    path = project / source_path
    return file_hash(path) if path.exists() and path.is_file() else ""


def source_path_errors(project: Path, source_path: str) -> list[str]:
    if not source_path:
        return []
    raw_path = Path(source_path)
    if raw_path.is_absolute():
        return ["source_path must be project-relative"]
    try:
        (project / raw_path).resolve().relative_to(project.resolve())
    except ValueError:
        return ["source_path must stay inside the project"]
    return []


def memory_item_id(item: dict[str, Any], created_at: str) -> str:
    if str(item.get("id", "")).strip():
        return str(item["id"]).strip()
    seed = "|".join(
        [
            str(item.get("kind", "note")),
            str(item.get("title", "")),
            str(item.get("summary", "")),
            str(item.get("source_path", "")),
            created_at,
        ]
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def read_memory_input(path: str | Path) -> dict[str, Any]:
    data = read_json(Path(path).resolve())
    if not isinstance(data, dict):
        raise SystemExit(f"Input must be a JSON object: {path}")
    return data


def append_event(events_path: Path, event: dict[str, Any]) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def write_memory(project: Path, input_path: str | Path) -> dict[str, Any]:
    init_result = init_memory(project)
    if init_result.get("errors"):
        return {"project": str(project), "written": False, "errors": list(init_result["errors"])}
    data = read_memory_input(input_path)
    created_at = str(data.get("created_at") or now_iso())
    updated_at = str(data.get("updated_at") or created_at)
    tags = normalize_tags(data.get("tags") or data.get("tags_json"))
    item = {
        "id": "",
        "kind": str(data.get("kind") or "note").strip() or "note",
        "title": str(data.get("title") or "Untitled memory").strip() or "Untitled memory",
        "summary": str(data.get("summary") or "").strip(),
        "source_path": str(data.get("source_path") or "").strip(),
        "source_hash": str(data.get("source_hash") or "").strip(),
        "source_ref": str(data.get("source_ref") or "").strip(),
        "source_timestamp": str(data.get("source_timestamp") or "").strip(),
        "sequence": int(data.get("sequence") or 0),
        "tags_json": json.dumps(tags, ensure_ascii=False, sort_keys=True),
        "created_at": created_at,
        "updated_at": updated_at,
        "sensitivity": str(data.get("sensitivity") or "normal").strip() or "normal",
    }
    item["id"] = memory_item_id({**data, **item}, created_at)
    if not item["summary"]:
        return {"project": str(project), "written": False, "errors": ["memory summary must not be empty"]}
    path_errors = source_path_errors(project, item["source_path"])
    if path_errors:
        return {"project": str(project), "written": False, "errors": path_errors}
    unsafe_errors = unsafe_summary_text(" ".join(str(item.get(key, "")) for key in ["title", "summary", "source_path"]))
    if unsafe_errors:
        return {"project": str(project), "written": False, "errors": unsafe_errors}
    if not item["source_hash"]:
        item["source_hash"] = source_hash_for(project, item["source_path"])
    paths = memory_paths(project)
    with closing(connect_memory_db(paths["database"])) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO memory_items
            (id, kind, title, summary, source_path, source_hash, source_ref, source_timestamp, sequence, tags_json, created_at, updated_at, sensitivity)
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
        sync_memory_search_item(conn, item)
        conn.commit()
    append_event(paths["events"], {"event": "memory_write", **item})
    return {
        "project": str(project),
        "written": item,
        "ok": True,
        "id": item["id"],
        "item": item,
        "events": rel(project, paths["events"]),
        "errors": [],
    }


def db_items(project: Path) -> list[dict[str, Any]]:
    paths = memory_paths(project)
    with closing(connect_memory_db(paths["database"])) as conn:
        rows = conn.execute(f"SELECT {MEMORY_ITEM_SELECT_COLUMNS} FROM memory_items ORDER BY updated_at DESC").fetchall()
    return [row_to_memory_item(row) for row in rows]


def fts_query(terms: list[str]) -> str:
    fts_terms = [term for term in terms if len(term) >= 3]
    return " OR ".join(f'"{term.replace(chr(34), chr(34) + chr(34))}"' for term in fts_terms)


def search_memory_fts(conn: sqlite3.Connection, terms: list[str], limit: int) -> list[dict[str, Any]]:
    query = fts_query(terms)
    if not query:
        return []
    rows = conn.execute(
        f"""
        SELECT {", ".join("m." + key for key in MEMORY_ITEM_KEYS)}
        FROM memory_items_fts
        JOIN memory_items m ON m.id = memory_items_fts.item_id
        WHERE memory_items_fts MATCH ?
        ORDER BY bm25(memory_items_fts), m.updated_at DESC
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()
    return [row_to_memory_item(row) for row in rows]


def search_memory_terms(conn: sqlite3.Connection, terms: list[str], limit: int) -> list[dict[str, Any]]:
    indexed_terms = [term for term in terms if term]
    if not indexed_terms:
        return []
    placeholders = ", ".join("?" for _ in indexed_terms)
    rows = conn.execute(
        f"""
        SELECT {", ".join("m." + key for key in MEMORY_ITEM_KEYS)}
        FROM memory_item_terms t
        JOIN memory_items m ON m.id = t.item_id
        WHERE t.term IN ({placeholders})
        GROUP BY m.id
        ORDER BY COUNT(DISTINCT t.term) DESC, m.updated_at DESC
        LIMIT ?
        """,
        (*indexed_terms, limit),
    ).fetchall()
    return [row_to_memory_item(row) for row in rows]


def search_memory_like(conn: sqlite3.Connection, terms: list[str], limit: int) -> list[dict[str, Any]]:
    like_terms = [term for term in terms if term][:5]
    if not like_terms:
        return []
    columns = ["kind", "title", "summary", "source_path", "source_ref", "tags_json", "sensitivity"]
    predicates: list[str] = []
    params: list[str] = []
    for term in like_terms:
        for column in columns:
            predicates.append(f"{column} LIKE ?")
            params.append(f"%{term}%")
    rows = conn.execute(
        f"""
        SELECT {MEMORY_ITEM_SELECT_COLUMNS}
        FROM memory_items
        WHERE {" OR ".join(predicates)}
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (*params, limit),
    ).fetchall()
    return [row_to_memory_item(row) for row in rows]


def read_memory(project: Path, query: str, limit: int = 5) -> dict[str, Any]:
    init_result = init_memory(project)
    if init_result.get("errors"):
        return {"project": str(project), "query": query, "limit": limit, "count": 0, "items": [], "errors": list(init_result["errors"])}
    terms = query_terms(query)
    fallback_used = False
    search_backend = "latest"
    paths = memory_paths(project)
    with closing(connect_memory_db(paths["database"])) as conn:
        if terms:
            selected = search_memory_fts(conn, terms, limit)
            if selected:
                search_backend = "fts5"
            else:
                selected = search_memory_terms(conn, terms, limit)
                if selected:
                    search_backend = "term-index"
                else:
                    selected = search_memory_like(conn, terms, limit)
                    fallback_used = bool(selected)
                    search_backend = "like" if selected else "none"
        else:
            rows = conn.execute(f"SELECT {MEMORY_ITEM_SELECT_COLUMNS} FROM memory_items ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
            selected = [row_to_memory_item(row) for row in rows]
    return {
        "project": str(project),
        "query": query,
        "limit": limit,
        "count": len(selected),
        "items": selected,
        "search_backend": search_backend,
        "fallback_used": fallback_used,
        "guide": memory_contract(project)["guide"],
        "errors": [],
    }


def compress_memory(project: Path) -> dict[str, Any]:
    init_result = init_memory(project)
    if init_result.get("errors"):
        return {"project": str(project), "written": False, "items": 0, "errors": list(init_result["errors"])}
    items = db_items(project)
    paths = memory_paths(project)
    lines = ["# Memory Summaries", "", f"- Updated at: {now_iso()}", ""]
    if not items:
        lines.append("No memory items recorded yet.")
    for item in sorted(items, key=lambda row: (int(row.get("sequence") or 0), str(row.get("updated_at", "")))):
        tags = ", ".join(json.loads(item.get("tags_json") or "[]"))
        lines.extend(
            [
                f"## {item.get('title', 'Untitled memory')}",
                f"- Kind: {item.get('kind', 'note')}",
                f"- Sequence: {item.get('sequence') or 0}",
                f"- Updated: {item.get('updated_at', '')}",
                f"- Source ref: {item.get('source_ref') or 'not recorded'}",
                f"- Source timestamp: {item.get('source_timestamp') or 'not recorded'}",
                f"- Source: {item.get('source_path') or 'not recorded'}",
                f"- Tags: {tags or 'none'}",
                "",
                str(item.get("summary", "")).strip(),
                "",
            ]
        )
    paths["summaries"].write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return {"project": str(project), "written": rel(project, paths["summaries"]), "items": len(items), "errors": []}


def unsafe_summary_text(text: str) -> list[str]:
    errors: list[str] = []
    if SECRET_RE.search(text) or PRIVATE_KEY_RE.search(text):
        errors.append("memory summary contains an unredacted secret-like assignment")
    if LOCAL_PRIVATE_PATH_RE.search(text):
        errors.append("memory summary contains a raw local private path")
    return errors


def strong_control_profile(project: Path) -> bool:
    profile = project_profile(project)
    if not profile:
        return False
    return bool(
        profile.get("alignment_confirmed")
        or profile.get("directory_contract")
        or profile.get("docs_contract")
        or profile.get("kind")
    )


def matched_session_ids(project: Path) -> list[str]:
    return [str(item.get("id", "")).strip() for item in matched_codex_sessions(project) if str(item.get("id", "")).strip()]


def bootstrap_state(project: Path) -> dict[str, Any]:
    path = memory_paths(project)["bootstrap_state"]
    data = read_json(path) if path.is_file() else {}
    return data if isinstance(data, dict) else {}


def bootstrap_errors(project: Path) -> list[str]:
    sessions = matched_session_ids(project)
    if not sessions:
        return []
    state = bootstrap_state(project)
    processed = [
        str(item.get("id", "")).strip()
        for item in state.get("processed_sessions", [])
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    ]
    missing = [session_id for session_id in sessions if session_id not in processed]
    if missing:
        return [
            "docs/memory/bootstrap-state.json missing exact-cwd Codex session bootstrap entries: "
            + ", ".join(missing)
        ]
    return []


def verify_memory(project: Path) -> dict[str, Any]:
    contract = memory_contract(project)
    if not contract["enabled"]:
        errors = ["memory governance must be enabled for strong-control work folders"] if strong_control_profile(project) else []
        return {"project": str(project), "enabled": False, "checked": [], "errors": errors}
    contract_errors = [item for item in memory_contract_errors(contract) if "disabled" not in item]
    if contract_errors:
        return {"project": str(project), "enabled": True, "checked": [], "errors": contract_errors}
    paths = memory_paths(project)
    errors: list[str] = []
    checked: list[str] = []
    for key in ["folder", "database", "events", "summaries", "guide"]:
        path = paths[key]
        checked.append(rel(project, path))
        if key == "folder" and not path.is_dir():
            errors.append(f"missing memory directory: {rel(project, path)}")
        elif key != "folder" and not path.is_file():
            errors.append(f"missing memory file: {rel(project, path)}")
    if paths["database"].exists():
        try:
            with closing(sqlite3.connect(paths["database"])) as conn:
                row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_items'").fetchone()
                if not row:
                    errors.append(f"{rel(project, paths['database'])}: missing memory_items table")
                else:
                    columns = {str(item[1]) for item in conn.execute("PRAGMA table_info(memory_items)").fetchall()}
                    required_columns = MEMORY_REQUIRED_COLUMNS
                    missing_columns = sorted(required_columns - columns)
                    if missing_columns:
                        errors.append(f"{rel(project, paths['database'])}: schema missing columns: {', '.join(missing_columns)}")
                    objects = {
                        str(item[0])
                        for item in conn.execute(
                            "SELECT name FROM sqlite_master WHERE type IN ('table', 'index')"
                        ).fetchall()
                    }
                    required_search_objects = {
                        "memory_items_fts",
                        "memory_item_terms",
                        "idx_memory_items_updated_at",
                        "idx_memory_items_sequence",
                        "idx_memory_items_kind",
                        "idx_memory_item_terms_term",
                    }
                    missing_search_objects = sorted(required_search_objects - objects)
                    if missing_search_objects:
                        errors.append(f"{rel(project, paths['database'])}: search schema missing objects: {', '.join(missing_search_objects)}")
                    if not missing_columns and not missing_search_objects:
                        item_count = conn.execute("SELECT COUNT(*) FROM memory_items").fetchone()[0]
                        fts_count = conn.execute("SELECT COUNT(*) FROM memory_items_fts").fetchone()[0]
                        term_item_count = conn.execute("SELECT COUNT(DISTINCT item_id) FROM memory_item_terms").fetchone()[0]
                        if item_count != fts_count:
                            errors.append(f"{rel(project, paths['database'])}: FTS index row count mismatch: memory_items={item_count}, memory_items_fts={fts_count}")
                        if item_count and term_item_count != item_count:
                            errors.append(f"{rel(project, paths['database'])}: short-term index coverage mismatch: memory_items={item_count}, indexed_items={term_item_count}")
        except sqlite3.DatabaseError as exc:
            errors.append(f"{rel(project, paths['database'])}: SQLite open failed: {exc}")
    if paths["events"].exists():
        for index, line in enumerate(paths["events"].read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{rel(project, paths['events'])}:{index}: invalid JSONL event: {exc}")
                continue
            for issue in unsafe_summary_text(" ".join(str(event.get(key, "")) for key in ["title", "summary"])):
                errors.append(f"{rel(project, paths['events'])}:{index}: {issue}")
    if paths["summaries"].exists():
        for issue in unsafe_summary_text(paths["summaries"].read_text(encoding="utf-8", errors="ignore")):
            errors.append(f"{rel(project, paths['summaries'])}: {issue}")
    checked.append(rel(project, paths["bootstrap_state"]))
    errors.extend(bootstrap_errors(project))
    return {"project": str(project), "enabled": True, "checked": checked, "errors": errors}


def memory_gate(project: Path) -> dict[str, Any]:
    contract = memory_contract(project)
    paths = memory_paths(project)
    missing: list[str] = []
    for key in ["folder", "database", "events", "summaries", "guide"]:
        path = paths[key]
        if key == "folder" and not path.is_dir():
            missing.append(rel(project, path))
        elif key != "folder" and not path.is_file():
            missing.append(rel(project, path))
    verify = verify_memory(project)
    errors = list(verify.get("errors", []))
    if missing:
        errors.extend(f"missing memory path: {item}" for item in missing if f"missing memory path: {item}" not in errors)
    disabled = not contract.get("enabled")
    requires_authorization = bool(disabled or missing)
    command = "python skills/agents-md-generator/scripts/manage_docs.py memory-init <project> --confirm-create"
    return {
        "project": str(project),
        "ok": not errors and not requires_authorization,
        "enabled": bool(contract.get("enabled")),
        "missing": missing,
        "checked": verify.get("checked", []),
        "requires_user_authorization": requires_authorization,
        "recommended_authorization_command": command if requires_authorization else "",
        "errors": errors,
    }


def sanitize_memory_text(text: str) -> str:
    sanitized = SECRET_RE.sub(lambda match: f"{match.group(1)}=<REDACTED_SECRET>", text)
    sanitized = PRIVATE_KEY_RE.sub("<REDACTED_PRIVATE_KEY>", sanitized)
    sanitized = LOCAL_PRIVATE_PATH_RE.sub("<REDACTED_LOCAL_PATH>", sanitized)
    return sanitized


def compact_session_summary(messages: list[dict[str, str]], limit: int = 700) -> str:
    if not messages:
        return "No user or assistant message content was available in this Codex session."
    parts: list[str] = []
    for row in messages[:10]:
        role = "User" if row.get("role") == "user" else "Assistant"
        message = " ".join(str(row.get("message", "")).split())
        if not message:
            continue
        parts.append(f"{role}: {message}")
    summary = sanitize_memory_text(" | ".join(parts))
    return summary[:limit].rstrip()


def bootstrap_sessions(project: Path) -> dict[str, Any]:
    init_result = init_memory(project)
    if init_result.get("errors"):
        return {"project": str(project), "processed": 0, "processed_session_ids": [], "errors": list(init_result["errors"])}
    sessions = sorted(matched_codex_sessions(project), key=lambda item: (str(item.get("timestamp", "")), str(item.get("id", ""))))
    state = bootstrap_state(project)
    processed_existing = {
        str(item.get("id", "")).strip()
        for item in state.get("processed_sessions", [])
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    processed_sessions = list(state.get("processed_sessions", [])) if isinstance(state.get("processed_sessions"), list) else []
    written_ids: list[str] = []
    sequence = max([int(item.get("sequence") or 0) for item in processed_sessions if isinstance(item, dict)] or [0])
    for session in sessions:
        session_id = str(session.get("id", "")).strip()
        if not session_id or session_id in processed_existing:
            continue
        sequence += 1
        path = Path(str(session.get("path", "")))
        messages = session_message_rows(path, limit=24)
        summary = compact_session_summary(messages)
        input_data = {
            "kind": "codex-session",
            "title": f"Codex session {session_id}",
            "summary": summary,
            "source_path": "",
            "source_ref": f"codex-session:{session_id}",
            "source_timestamp": str(session.get("timestamp", "")),
            "sequence": sequence,
            "tags": ["codex-session", "history", "memory-bootstrap"],
            "sensitivity": "normal",
            "created_at": str(session.get("timestamp", "")) or now_iso(),
            "updated_at": now_iso(),
        }
        temp_path = project / ".agents" / f"memory-session-{session_id}.json"
        temp_path.parent.mkdir(exist_ok=True)
        temp_path.write_text(json.dumps(input_data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        result = write_memory(project, temp_path)
        try:
            temp_path.unlink()
        except OSError:
            pass
        if result.get("errors"):
            return {"project": str(project), "processed": len(written_ids), "processed_session_ids": written_ids, "errors": result["errors"]}
        processed_sessions.append(
            {
                "id": session_id,
                "timestamp": str(session.get("timestamp", "")),
                "path_hash": hashlib.sha256(str(session.get("path", "")).encode("utf-8")).hexdigest(),
                "source_hash": file_hash(path),
                "sequence": sequence,
            }
        )
        written_ids.append(session_id)
    state = {
        "generated_at": now_iso(),
        "match_scope": "exact-cwd",
        "matched_session_count": len(sessions),
        "processed_sessions": processed_sessions,
    }
    paths = memory_paths(project)
    paths["bootstrap_state"].parent.mkdir(parents=True, exist_ok=True)
    paths["bootstrap_state"].write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    compress = compress_memory(project)
    return {
        "project": str(project),
        "matched_session_count": len(sessions),
        "processed": len(written_ids),
        "processed_session_ids": written_ids,
        "bootstrap_state": rel(project, paths["bootstrap_state"]),
        "compression": compress,
        "errors": compress.get("errors", []),
    }


def memory_read_recommendation(project: Path, query: str = "current task") -> dict[str, Any] | None:
    contract = memory_contract(project)
    if memory_contract_errors(contract):
        return None
    return {
        "enabled": True,
        "policy": contract["read_policy"],
        "guide": contract["guide"],
        "command": f"python skills/agents-md-generator/scripts/manage_docs.py memory-read <project> --query \"{query}\" --limit 5",
    }


def handoff_summary(data: dict[str, Any], count: int) -> str:
    parts = [
        f"Handoff #{count}.",
        "Plan: " + list_lines(data.get("original_plan") or data.get("plan")).replace("\n", " "),
        "Current step: " + list_lines(data.get("current_step")).replace("\n", " "),
        "Resolved: " + list_lines(data.get("resolved") or data.get("resolved_problems")).replace("\n", " "),
        "Remaining: " + list_lines(data.get("remaining") or data.get("remaining_problems")).replace("\n", " "),
        "Next: " + list_lines(data.get("next") or data.get("next_work")).replace("\n", " "),
        "Verification: " + list_lines(data.get("verification") or data.get("verification_evidence")).replace("\n", " "),
    ]
    return " ".join(part for part in parts if part.strip()).strip()


def write_handoff_memory(project: Path, data: dict[str, Any], count: int, handoff_path: Path) -> dict[str, Any] | None:
    if not memory_enabled(project):
        return None
    init_memory(project)
    temp_input = {
        "kind": "handoff",
        "title": f"Handoff #{count}",
        "summary": handoff_summary(data, count),
        "source_path": rel(project, handoff_path),
        "source_hash": file_hash(handoff_path),
        "tags": ["handoff", "session"],
        "sensitivity": "normal",
    }
    temp_path = project / ".agents" / "memory-handoff-input.json"
    temp_path.parent.mkdir(exist_ok=True)
    temp_path.write_text(json.dumps(temp_input, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    result = write_memory(project, temp_path)
    try:
        temp_path.unlink()
    except OSError:
        pass
    paths = memory_paths(project)
    event_count = sum(1 for line in paths["events"].read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip())
    result["event_count"] = event_count
    threshold = int(memory_contract(project).get("compress_after_events", 20) or 20)
    if threshold > 0 and event_count % threshold == 0:
        result["compression"] = compress_memory(project)
    return result
