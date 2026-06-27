def read_memory(project: Path, query: str, limit: int = 5) -> dict[str, Any]:

    # 保存 init result 映射，维持 read_memory 的字段关系。
    dict_init_result = init_memory(project)  # 记忆库记录检索流程输入值

    # 校验 read_memory 的 memory 分支条件。
    if dict_init_result.get("errors"):

        # 返回 read_memory 的 memory 载荷。
        return {"project": str(project), "query": query, "limit": limit, "count": 0, "items": [], "errors": list(dict_init_result["errors"])}

    # 汇总 terms，作为记忆库读写和压缩候选清单。
    list_terms = query_terms(query)  # 记忆库记录检索流程输入值

    # 标记 fallback used 判断，控制 read_memory 的分支走向。
    bool_fallback_used = False  # 记忆库记录检索流程输入值

    # 整理 read_memory 需要的 search backend 记忆信息。
    str_search_backend = "latest"  # 记忆库记录检索流程输入值

    # 汇总 paths，作为记忆库读写和压缩候选清单。
    dict_paths = memory_paths(project)  # 记忆库记录检索流程输入值

    # 进入上下文并在退出时回收资源。
    with closing(connect_memory_db(dict_paths["database"])) as conn:

        # 校验 read_memory 的 memory 分支条件。
        if list_terms:

            # 汇总 selected，作为记忆库读写和压缩候选清单。
            list_selected = search_memory_fts(conn, list_terms, limit)  # 记忆库记录检索流程输入值

            # 校验 read_memory 的 memory 分支条件。
            if list_selected:

                # 整理 read_memory 需要的 search backend 记忆信息。
                str_search_backend = "fts5"  # 记忆库记录检索流程输入值
            else:

                # 汇总 selected，作为记忆库读写和压缩候选清单。
                list_selected = search_memory_terms(conn, list_terms, limit)  # 记忆库记录检索流程输入值

                # 校验 read_memory 的 memory 分支条件。
                if list_selected:

                    # 整理 read_memory 需要的 search backend 记忆信息。
                    str_search_backend = "term-index"  # 记忆库记录检索流程输入值
                else:

                    # 汇总 selected，作为记忆库读写和压缩候选清单。
                    list_selected = search_memory_like(conn, list_terms, limit)  # 记忆库记录检索流程输入值

                    # 标记 fallback used 判断，控制 read_memory 的分支走向。
                    bool_fallback_used = bool(list_selected)  # 记忆库记录检索流程输入值

                    # 整理 read_memory 需要的 search backend 记忆信息。
                    str_search_backend = "like" if list_selected else "none"  # 记忆库记录检索流程输入值
        else:

            # 汇总 rows，作为记忆库读写和压缩候选清单。
            rows = conn.execute(f"SELECT {MEMORY_ITEM_SELECT_COLUMNS} FROM memory_items ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()  # 记忆库记录检索流程输入值

            # 汇总 selected，作为记忆库读写和压缩候选清单。
            list_selected = [row_to_memory_item(row) for row in rows]  # 记忆库记录检索流程输入值

    # 返回 read_memory 的 memory 载荷。
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

# 定义 compress_memory 的memory 管理处理入口。
def compress_memory(project: Path) -> dict[str, Any]:

    # 保存 init result 映射，维持 compress_memory 的字段关系。
    dict_init_result = init_memory(project)  # 记忆库记录检索流程输入值

    # 校验 compress_memory 的 memory 分支条件。
    if dict_init_result.get("errors"):

        # 返回 compress_memory 的 memory 载荷。
        return {"project": str(project), "written": False, "items": 0, "errors": list(dict_init_result["errors"])}

    # 汇总 items，作为记忆库读写和压缩候选清单。
    list_items = db_items(project)  # 记忆库记录检索流程输入值

    # 汇总 paths，作为记忆库读写和压缩候选清单。
    dict_paths = memory_paths(project)  # 记忆库记录检索流程输入值

    # 汇总 lines，作为记忆库读写和压缩候选清单。
    list_lines = ["# Memory Summaries", "", f"- Updated at: {now_iso()}", ""]  # memory 摘要文档头部行

    # 校验 compress_memory 的 memory 分支条件。
    if not list_items:

        # 追加 compress_memory 的 memory 诊断。
        list_lines.append("No memory items recorded yet.")

    # 逐项检查 compress_memory 记忆候选。
    for item in sorted(list_items, key=lambda row: (int(row.get("sequence") or 0), str(row.get("updated_at", "")))):

        # 汇总 tags，作为记忆库读写和压缩候选清单。
        tags = ", ".join(json.loads(item.get("tags_json") or "[]"))  # 记忆库记录检索流程输入值

        # 调用 extend 处理 compress_memory。
        list_lines.extend(
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

    # 调用 write_text 处理 compress_memory。
    dict_paths["summaries"].write_text("\n".join(list_lines).rstrip() + "\n", encoding="utf-8")

    # 返回 compress_memory 的 memory 载荷。
    return {"project": str(project), "written": rel(project, dict_paths["summaries"]), "items": len(list_items), "errors": []}

# 定义 unsafe_summary_text 的memory 管理处理入口。
def unsafe_summary_text(text: str) -> list[str]:

    # 汇总 errors，作为记忆库读写和压缩候选清单。
    list_errors: list[str] = []  # 记忆库记录检索流程输入值

    # 校验 unsafe_summary_text 的 memory 分支条件。
    if SECRET_RE.search(text) or PRIVATE_KEY_RE.search(text):

        # 追加 unsafe_summary_text 的 memory 诊断。
        list_errors.append("memory summary contains an unredacted secret-like assignment")

    # 校验 unsafe_summary_text 的 memory 分支条件。
    if LOCAL_PRIVATE_PATH_RE.search(text):

        # 追加 unsafe_summary_text 的 memory 诊断。
        list_errors.append("memory summary contains a raw local private path")

    # 返回 unsafe_summary_text 的 memory 载荷。
    return list_errors

# 定义 strong_control_profile 的memory 管理处理入口。
def strong_control_profile(project: Path) -> bool:

    # 整理 strong_control_profile 需要的 profile 记忆信息。
    profile = project_profile(project)  # 记忆库记录检索流程输入值

    # 校验 strong_control_profile 的 memory 分支条件。
    if not profile:

        # 返回 strong_control_profile 的 memory 载荷。
        return False

    # 返回 strong_control_profile 的 memory 载荷。
    return bool(
        profile.get("alignment_confirmed")
        or profile.get("directory_contract")
        or profile.get("docs_contract")
        or profile.get("kind")
    )

# 定义 matched_session_ids 的memory 管理处理入口。
def matched_session_ids(project: Path) -> list[str]:

    # 返回 matched_session_ids 的 memory 载荷。
    return [str(item.get("id", "")).strip() for item in matched_codex_sessions(project) if str(item.get("id", "")).strip()]

# 定义 bootstrap_state 的memory 管理处理入口。
def bootstrap_state(project: Path) -> dict[str, Any]:

    # 整理 bootstrap_state 需要的 path 记忆信息。
    path = memory_paths(project)["bootstrap_state"]  # 记忆库记录检索流程输入值

    # 整理 bootstrap_state 需要的 data 记忆信息。
    dict_data = read_json(path) if path.is_file() else {}  # 记忆库记录检索流程输入值

    # 返回 bootstrap_state 的 memory 载荷。
    return dict_data if isinstance(dict_data, dict) else {}

# 定义 bootstrap_errors 的memory 管理处理入口。
def bootstrap_errors(project: Path) -> list[str]:

    # 汇总 sessions，作为记忆库读写和压缩候选清单。
    list_sessions = matched_session_ids(project)  # 记忆库记录检索流程输入值

    # 校验 bootstrap_errors 的 memory 分支条件。
    if not list_sessions:

        # 返回 bootstrap_errors 的 memory 载荷。
        return []

    # 保存 state 映射，维持 bootstrap_errors 的字段关系。
    dict_state = bootstrap_state(project)  # 记忆库记录检索流程输入值

    # 整理 bootstrap_errors 需要的 processed 记忆信息。
    processed = [  # 记忆库记录检索流程输入值
        str(item.get("id", "")).strip()  # 记忆库记录检索流程输入值
        for item in dict_state.get("processed_sessions", [])  # 记忆库记录检索流程输入值
        if isinstance(item, dict) and str(item.get("id", "")).strip()  # 记忆库记录检索流程输入值
    ]

    # 整理 bootstrap_errors 需要的 missing 记忆信息。
    missing = [session_id for session_id in list_sessions if session_id not in processed]  # 记忆库记录检索流程输入值

    # 校验 bootstrap_errors 的 memory 分支条件。
    if missing:

        # 返回 bootstrap_errors 的 memory 载荷。
        return [
            "docs/memory/bootstrap-state.json missing exact-cwd Codex session bootstrap entries: "
            + ", ".join(missing)
        ]

    # 返回 bootstrap_errors 的 memory 载荷。
    return []

# 定义 verify_memory 的memory 管理处理入口。
def verify_memory(project: Path) -> dict[str, Any]:

    # 保存 contract 映射，维持 verify_memory 的字段关系。
    dict_contract = memory_contract(project)  # 记忆库记录检索流程输入值

    # 校验 verify_memory 的 memory 分支条件。
    if not dict_contract["enabled"]:

        # 汇总 errors，作为记忆库读写和压缩候选清单。
        list_errors = ["memory governance must be enabled for strong-control work folders"] if strong_control_profile(project) else []  # 记忆库记录检索流程输入值

        # 返回 verify_memory 的 memory 载荷。
        return {"project": str(project), "enabled": False, "checked": [], "errors": list_errors}

    # 汇总 contract errors，作为记忆库读写和压缩候选清单。
    contract_errors = [item for item in memory_contract_errors(dict_contract) if "disabled" not in item]  # 记忆库记录检索流程输入值

    # 校验 verify_memory 的 memory 分支条件。
    if contract_errors:

        # 返回 verify_memory 的 memory 载荷。
        return {"project": str(project), "enabled": True, "checked": [], "errors": contract_errors}

    # 汇总 paths，作为记忆库读写和压缩候选清单。
    dict_paths = memory_paths(project)  # 记忆库记录检索流程输入值

    # 汇总 errors，作为记忆库读写和压缩候选清单。
    list_errors: list[str] = []  # 记忆库记录检索流程输入值

    # 汇总 checked，作为记忆库读写和压缩候选清单。
    list_checked: list[str] = []  # 记忆库记录检索流程输入值

    # 逐项检查 verify_memory 记忆候选。
    for key in ["folder", "database", "events", "summaries", "guide"]:

        # 整理 verify_memory 需要的 path 记忆信息。
        path = dict_paths[key]  # 记忆库记录检索流程输入值

        # 追加 verify_memory 的 memory 诊断。
        list_checked.append(rel(project, path))

        # 校验 verify_memory 的 memory 分支条件。
        if key == "folder" and not path.is_dir():

            # 追加 verify_memory 的 memory 诊断。
            list_errors.append(f"missing memory directory: {rel(project, path)}")

        # 校验 verify_memory 的 memory 分支条件。
        elif key != "folder" and not path.is_file():

            # 追加 verify_memory 的 memory 诊断。
            list_errors.append(f"missing memory file: {rel(project, path)}")

    # 校验 verify_memory 的 memory 分支条件。
    if dict_paths["database"].exists():

        # 保护 verify_memory 中允许失败的外部访问。
        try:

            # 进入上下文并在退出时回收资源。
            with closing(sqlite3.connect(dict_paths["database"])) as conn:

                # 整理 verify_memory 需要的 row 记忆信息。
                row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_items'").fetchone()  # 记忆库记录检索流程输入值

                # 校验 verify_memory 的 memory 分支条件。
                if not row:

                    # 追加 verify_memory 的 memory 诊断。
                    list_errors.append(f"{rel(project, dict_paths['database'])}: missing memory_items table")
                else:

                    # 汇总 columns，作为记忆库读写和压缩候选清单。
                    columns = {str(item[1]) for item in conn.execute("PRAGMA table_info(memory_items)").fetchall()}  # 记忆库记录检索流程输入值

                    # 汇总 required columns，作为记忆库读写和压缩候选清单。
                    required_columns = MEMORY_REQUIRED_COLUMNS  # 记忆库记录检索流程输入值

                    # 汇总 missing columns，作为记忆库读写和压缩候选清单。
                    missing_columns = sorted(required_columns - columns)  # 记忆库记录检索流程输入值

                    # 校验 verify_memory 的 memory 分支条件。
                    if missing_columns:

                        # 追加 verify_memory 的 memory 诊断。
                        list_errors.append(f"{rel(project, dict_paths['database'])}: schema missing columns: {', '.join(missing_columns)}")

                    # 汇总 objects，作为记忆库读写和压缩候选清单。
                    objects = {  # 记忆库记录检索流程输入值
                        str(item[0])  # 记忆库记录检索流程输入值
                        for item in conn.execute(  # 记忆库记录检索流程输入值
                            "SELECT name FROM sqlite_master WHERE type IN ('table', 'index')"  # 记忆库记录检索流程输入值
                        ).fetchall()  # 记忆库记录检索流程输入值
                    }

                    # 汇总 required search objects，作为记忆库读写和压缩候选清单。
                    set_required_search_objects = {  # 记忆库记录检索流程输入值
                        "memory_items_fts",  # 记忆库记录检索流程输入值
                        "memory_item_terms",  # 记忆库记录检索流程输入值
                        "idx_memory_items_updated_at",  # 记忆库记录检索流程输入值
                        "idx_memory_items_sequence",  # 记忆库记录检索流程输入值
                        "idx_memory_items_kind",  # 记忆库记录检索流程输入值
                        "idx_memory_item_terms_term",  # 记忆库记录检索流程输入值
                    }

                    # 汇总 missing search objects，作为记忆库读写和压缩候选清单。
                    missing_search_objects = sorted(set_required_search_objects - objects)  # 记忆库记录检索流程输入值

                    # 校验 verify_memory 的 memory 分支条件。
                    if missing_search_objects:

                        # 追加 verify_memory 的 memory 诊断。
                        list_errors.append(f"{rel(project, dict_paths['database'])}: search schema missing objects: {', '.join(missing_search_objects)}")

                    # 校验 verify_memory 的 memory 分支条件。
                    if not missing_columns and not missing_search_objects:

                        # 整理 verify_memory 需要的 item count 记忆信息。
                        item_count = conn.execute("SELECT COUNT(*) FROM memory_items").fetchone()[0]  # 记忆库记录检索流程输入值

                        # 整理 verify_memory 需要的 fts count 记忆信息。
                        fts_count = conn.execute("SELECT COUNT(*) FROM memory_items_fts").fetchone()[0]  # 记忆库记录检索流程输入值

                        # 整理 verify_memory 需要的 term item count 记忆信息。
                        term_item_count = conn.execute("SELECT COUNT(DISTINCT item_id) FROM memory_item_terms").fetchone()[0]  # 记忆库记录检索流程输入值

                        # 校验 verify_memory 的 memory 分支条件。
                        if item_count != fts_count:

                            # 追加 verify_memory 的 memory 诊断。
                            list_errors.append((
                                f"{rel(project, dict_paths['database'])}: FTS index row count mismatch: "  # AGENTS 长文本片段
                                f"memory_items={item_count}, memory_items_fts={fts_count}"  # AGENTS 长文本片段
                            ))

                        # 校验 verify_memory 的 memory 分支条件。
                        if item_count and term_item_count != item_count:

                            # 追加 verify_memory 的 memory 诊断。
                            list_errors.append((
                                f"{rel(project, dict_paths['database'])}: short-term index coverage mismatch: "  # AGENTS 长文本片段
                                f"memory_items={item_count}, indexed_items={term_item_count}"  # AGENTS 长文本片段
                            ))
        except sqlite3.DatabaseError as exc:

            # 追加 verify_memory 的 memory 诊断。
            list_errors.append(f"{rel(project, dict_paths['database'])}: SQLite open failed: {exc}")

    # 校验 verify_memory 的 memory 分支条件。
    if dict_paths["events"].exists():

        # 逐项检查 verify_memory 记忆候选。
        for index, line in enumerate(dict_paths["events"].read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):

            # 校验 verify_memory 的 memory 分支条件。
            if not line.strip():

                # 分隔 verify_memory 的控制流边界。
                continue

            # 保护 verify_memory 中允许失败的外部访问。
            try:

                # 整理 verify_memory 需要的 event 记忆信息。
                event = json.loads(line)  # 记忆库记录检索流程输入值
            except json.JSONDecodeError as exc:

                # 追加 verify_memory 的 memory 诊断。
                list_errors.append(f"{rel(project, dict_paths['events'])}:{index}: invalid JSONL event: {exc}")

                # 分隔 verify_memory 的控制流边界。
                continue

            # 逐项检查 verify_memory 记忆候选。
            for issue in unsafe_summary_text(" ".join(str(event.get(key, "")) for key in ["title", "summary"])):

                # 追加 verify_memory 的 memory 诊断。
                list_errors.append(f"{rel(project, dict_paths['events'])}:{index}: {issue}")

    # 校验 verify_memory 的 memory 分支条件。
    if dict_paths["summaries"].exists():

        # 逐项检查 verify_memory 记忆候选。
        for issue in unsafe_summary_text(dict_paths["summaries"].read_text(encoding="utf-8", errors="ignore")):

            # 追加 verify_memory 的 memory 诊断。
            list_errors.append(f"{rel(project, dict_paths['summaries'])}: {issue}")

    # 追加 verify_memory 的 memory 诊断。
    list_checked.append(rel(project, dict_paths["bootstrap_state"]))

    # 调用 extend 处理 verify_memory。
    list_errors.extend(bootstrap_errors(project))

    # 返回 verify_memory 的 memory 载荷。
    return {"project": str(project), "enabled": True, "checked": list_checked, "errors": list_errors}

# 定义 memory_gate 的memory 管理处理入口。
def memory_gate(project: Path) -> dict[str, Any]:

    # 保存 contract 映射，维持 memory_gate 的字段关系。
    dict_contract = memory_contract(project)  # 记忆库记录检索流程输入值

    # 汇总 paths，作为记忆库读写和压缩候选清单。
    dict_paths = memory_paths(project)  # 记忆库记录检索流程输入值

    # 汇总 missing，作为记忆库读写和压缩候选清单。
    list_missing: list[str] = []  # 记忆库记录检索流程输入值

    # 逐项检查 memory_gate 记忆候选。
    for key in ["folder", "database", "events", "summaries", "guide"]:

        # 整理 memory_gate 需要的 path 记忆信息。
        path = dict_paths[key]  # 记忆库记录检索流程输入值

        # 校验 memory_gate 的 memory 分支条件。
        if key == "folder" and not path.is_dir():

            # 追加 memory_gate 的 memory 诊断。
            list_missing.append(rel(project, path))

        # 校验 memory_gate 的 memory 分支条件。
        elif key != "folder" and not path.is_file():

            # 追加 memory_gate 的 memory 诊断。
            list_missing.append(rel(project, path))

    # 保存 verify 映射，维持 memory_gate 的字段关系。
    dict_verify = verify_memory(project)  # 记忆库记录检索流程输入值

    # 汇总 errors，作为记忆库读写和压缩候选清单。
    list_errors = list(dict_verify.get("errors", []))  # 记忆库记录检索流程输入值

    # 校验 memory_gate 的 memory 分支条件。
    if list_missing:

        # 调用 extend 处理 memory_gate。
        list_errors.extend(f"missing memory path: {item}" for item in list_missing if f"missing memory path: {item}" not in list_errors)

    # 整理 memory_gate 需要的 disabled 记忆信息。
    disabled = not dict_contract.get("enabled")  # 记忆库记录检索流程输入值

    # 标记 requires authorization 判断，控制 memory_gate 的分支走向。
    bool_requires_authorization = bool(disabled or list_missing)  # 记忆库记录检索流程输入值

    # 整理 memory_gate 需要的 command 记忆信息。
    str_command = "python skills/agents-md-generator/scripts/python/docs/manage_docs.py memory-init <project> --confirm-create"  # 记忆库记录检索流程输入值

    # 返回 memory_gate 的 memory 载荷。
    return {
        "project": str(project),
        "ok": not list_errors and not bool_requires_authorization,
        "enabled": bool(dict_contract.get("enabled")),
        "missing": list_missing,
        "checked": dict_verify.get("checked", []),
        "requires_user_authorization": bool_requires_authorization,
        "recommended_authorization_command": str_command if bool_requires_authorization else "",
        "errors": list_errors,
    }

# 定义 sanitize_memory_text 的memory 管理处理入口。
def sanitize_memory_text(text: str) -> str:

    # 整理 sanitize_memory_text 需要的 sanitized 记忆信息。
    sanitized = SECRET_RE.sub(lambda match: f"{match.group(1)}=<REDACTED_SECRET>", text)  # 记忆库记录检索流程输入值

    # 整理 sanitize_memory_text 需要的 sanitized 记忆信息。
    sanitized = PRIVATE_KEY_RE.sub("<REDACTED_PRIVATE_KEY>", sanitized)  # 记忆库记录检索流程输入值

    # 整理 sanitize_memory_text 需要的 sanitized 记忆信息。
    sanitized = LOCAL_PRIVATE_PATH_RE.sub("<REDACTED_LOCAL_PATH>", sanitized)  # 记忆库记录检索流程输入值

    # 返回 sanitize_memory_text 的 memory 载荷。
    return sanitized

# 定义 compact_session_summary 的memory 管理处理入口。
def compact_session_summary(messages: list[dict[str, str]], limit: int = 700) -> str:

    # 校验 compact_session_summary 的 memory 分支条件。
    if not messages:

        # 返回 compact_session_summary 的 memory 载荷。
        return "No user or assistant message content was available in this Codex session."

    # 汇总 parts，作为记忆库读写和压缩候选清单。
    list_parts: list[str] = []  # 记忆库记录检索流程输入值

    # 逐项检查 compact_session_summary 记忆候选。
    for row in messages[:10]:

        # 整理 compact_session_summary 需要的 role 记忆信息。
        role = "User" if row.get("role") == "user" else "Assistant"  # 记忆库记录检索流程输入值

        # 整理 compact_session_summary 需要的 message 记忆信息。
        message = " ".join(str(row.get("message", "")).split())  # 记忆库记录检索流程输入值

        # 校验 compact_session_summary 的 memory 分支条件。
        if not message:

            # 分隔 compact_session_summary 的控制流边界。
            continue

        # 追加 compact_session_summary 的 memory 诊断。
        list_parts.append(f"{role}: {message}")

    # 整理 compact_session_summary 需要的 summary 记忆信息。
    str_summary = sanitize_memory_text(" | ".join(list_parts))  # 记忆库记录检索流程输入值

    # 返回 compact_session_summary 的 memory 载荷。
    return str_summary[:limit].rstrip()

# 定义 bootstrap_sessions 的memory 管理处理入口。
def bootstrap_sessions(project: Path) -> dict[str, Any]:

    # 保存 init result 映射，维持 bootstrap_sessions 的字段关系。
    dict_init_result = init_memory(project)  # 记忆库记录检索流程输入值

    # 校验 bootstrap_sessions 的 memory 分支条件。
    if dict_init_result.get("errors"):

        # 返回 bootstrap_sessions 的 memory 载荷。
        return {"project": str(project), "processed": 0, "processed_session_ids": [], "errors": list(dict_init_result["errors"])}

    # 汇总 sessions，作为记忆库读写和压缩候选清单。
    sessions = sorted(matched_codex_sessions(project), key=lambda item: (str(item.get("timestamp", "")), str(item.get("id", ""))))  # 记忆库记录检索流程输入值

    # 保存 state 映射，维持 bootstrap_sessions 的字段关系。
    dict_state = bootstrap_state(project)  # 记忆库记录检索流程输入值

    # 整理 bootstrap_sessions 需要的 processed existing 记忆信息。
    processed_existing = {  # 记忆库记录检索流程输入值
        str(item.get("id", "")).strip()  # 记忆库记录检索流程输入值
        for item in dict_state.get("processed_sessions", [])  # 记忆库记录检索流程输入值
        if isinstance(item, dict) and str(item.get("id", "")).strip()  # 记忆库记录检索流程输入值
    }

    # 汇总 processed sessions，作为记忆库读写和压缩候选清单。
    processed_sessions = list(dict_state.get("processed_sessions", [])) if isinstance(dict_state.get("processed_sessions"), list) else []  # 记忆库记录检索流程输入值

    # 汇总 written ids，作为记忆库读写和压缩候选清单。
    list_written_ids: list[str] = []  # 记忆库记录检索流程输入值

    # 整理 bootstrap_sessions 需要的 sequence 记忆信息。
    sequence = max([int(item.get("sequence") or 0) for item in processed_sessions if isinstance(item, dict)] or [0])  # 记忆库记录检索流程输入值

    # 逐项检查 bootstrap_sessions 记忆候选。
    for session in sessions:

        # 整理 bootstrap_sessions 需要的 session id 记忆信息。
        session_id = str(session.get("id", "")).strip()  # 记忆库记录检索流程输入值

        # 校验 bootstrap_sessions 的 memory 分支条件。
        if not session_id or session_id in processed_existing:

            # 分隔 bootstrap_sessions 的控制流边界。
            continue

        # 整理 bootstrap_sessions 需要的 sequence 记忆信息。
        sequence += 1  # 记忆库记录检索流程输入值

        # 定位 path 的文件边界，供 bootstrap_sessions 后续读写校验使用。
        path_path = Path(str(session.get("path", "")))  # 记忆库记录检索流程输入值

        # 汇总 messages，作为记忆库读写和压缩候选清单。
        messages = session_message_rows(path_path, limit=24)  # 记忆库记录检索流程输入值

        # 整理 bootstrap_sessions 需要的 summary 记忆信息。
        str_summary = compact_session_summary(messages)  # 记忆库记录检索流程输入值

        # 保存 input data 映射，维持 bootstrap_sessions 的字段关系。
        dict_input_data = {  # 记忆库记录检索流程输入值
            "kind": "codex-session",  # 记忆库记录检索流程输入值
            "title": f"Codex session {session_id}",  # 记忆库记录检索流程输入值
            "summary": str_summary,  # 记忆库记录检索流程输入值
            "source_path": "",  # 记忆库记录检索流程输入值
            "source_ref": f"codex-session:{session_id}",  # 记忆库记录检索流程输入值
            "source_timestamp": str(session.get("timestamp", "")),  # 记忆库记录检索流程输入值
            "sequence": sequence,  # 记忆库记录检索流程输入值
            "tags": ["codex-session", "history", "memory-bootstrap"],  # 记忆库记录检索流程输入值
            "sensitivity": "normal",  # 记忆库记录检索流程输入值
            "created_at": str(session.get("timestamp", "")) or now_iso(),  # 记忆库记录检索流程输入值
            "updated_at": now_iso(),  # 记忆库记录检索流程输入值
        }

        # 定位 temp path 的文件边界，供 bootstrap_sessions 后续读写校验使用。
        temp_path = project / ".agents" / f"memory-session-{session_id}.json"  # 记忆库记录检索流程输入值

        # 调用 mkdir 处理 bootstrap_sessions。
        temp_path.parent.mkdir(exist_ok=True)

        # 调用 write_text 处理 bootstrap_sessions。
        temp_path.write_text(json.dumps(dict_input_data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

        # 保存 result 映射，维持 bootstrap_sessions 的字段关系。
        dict_result = write_memory(project, temp_path)  # 记忆库记录检索流程输入值

        # 保护 bootstrap_sessions 中允许失败的外部访问。
        try:

            # 调用 unlink 处理 bootstrap_sessions。
            temp_path.unlink()
        except OSError:
            pass

        # 校验 bootstrap_sessions 的 memory 分支条件。
        if dict_result.get("errors"):

            # 返回 bootstrap_sessions 的 memory 载荷。
            return {"project": str(project), "processed": len(list_written_ids), "processed_session_ids": list_written_ids, "errors": dict_result["errors"]}

        # 追加 bootstrap_sessions 的 memory 诊断。
        processed_sessions.append(
            {
                "id": session_id,
                "timestamp": str(session.get("timestamp", "")),
                "path_hash": hashlib.sha256(str(session.get("path", "")).encode("utf-8")).hexdigest(),
                "source_hash": file_hash(path_path),
                "sequence": sequence,
            }
        )

        # 追加 bootstrap_sessions 的 memory 诊断。
        list_written_ids.append(session_id)

    # 保存 state 映射，维持 bootstrap_sessions 的字段关系。
    dict_state = {  # 记忆库记录检索流程输入值
        "generated_at": now_iso(),  # 记忆库记录检索流程输入值
        "match_scope": "exact-cwd",  # 记忆库记录检索流程输入值
        "matched_session_count": len(sessions),  # 记忆库记录检索流程输入值
        "processed_sessions": processed_sessions,  # 记忆库记录检索流程输入值
    }

    # 汇总 paths，作为记忆库读写和压缩候选清单。
    dict_paths = memory_paths(project)  # 记忆库记录检索流程输入值

    # 调用 mkdir 处理 bootstrap_sessions。
    dict_paths["bootstrap_state"].parent.mkdir(parents=True, exist_ok=True)

    # 调用 write_text 处理 bootstrap_sessions。
    dict_paths["bootstrap_state"].write_text(json.dumps(dict_state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    # 汇总 compress，作为记忆库读写和压缩候选清单。
    dict_compress = compress_memory(project)  # 记忆库记录检索流程输入值

    # 返回 bootstrap_sessions 的 memory 载荷。
    return {
        "project": str(project),
        "matched_session_count": len(sessions),
        "processed": len(list_written_ids),
        "processed_session_ids": list_written_ids,
        "bootstrap_state": rel(project, dict_paths["bootstrap_state"]),
        "compression": dict_compress,
        "errors": dict_compress.get("errors", []),
    }

# 定义 memory_read_recommendation 的memory 管理处理入口。
def memory_read_recommendation(project: Path, query: str = "current task") -> dict[str, Any] | None:

    # 保存 contract 映射，维持 memory_read_recommendation 的字段关系。
    dict_contract = memory_contract(project)  # 记忆库记录检索流程输入值

    # 校验 memory_read_recommendation 的 memory 分支条件。
    if memory_contract_errors(dict_contract):

        # 返回 memory_read_recommendation 的 memory 载荷。
        return None

    # 返回 memory_read_recommendation 的 memory 载荷。
    return {
        "enabled": True,
        "policy": dict_contract["read_policy"],
        "guide": dict_contract["guide"],
        "command": f"python skills/agents-md-generator/scripts/python/docs/manage_docs.py memory-read <project> --query \"{query}\" --limit 5",
    }

# 定义 handoff_summary 的memory 管理处理入口。
def handoff_summary(data: dict[str, Any], count: int) -> str:

    # 汇总 parts，作为记忆库读写和压缩候选清单。
    list_parts = [  # 记忆库记录检索流程输入值
        f"Handoff #{count}.",  # handoff 记忆摘要标题句
        "Plan: " + list_lines(data.get("original_plan") or data.get("plan")).replace("\n", " "),  # 记忆库记录检索流程输入值
        "Current step: " + list_lines(data.get("current_step")).replace("\n", " "),  # 记忆库记录检索流程输入值
        "Resolved: " + list_lines(data.get("resolved") or data.get("resolved_problems")).replace("\n", " "),  # 记忆库记录检索流程输入值
        "Remaining: " + list_lines(data.get("remaining") or data.get("remaining_problems")).replace("\n", " "),  # 记忆库记录检索流程输入值
        "Next: " + list_lines(data.get("next") or data.get("next_work")).replace("\n", " "),  # 记忆库记录检索流程输入值
        "Verification: " + list_lines(data.get("verification") or data.get("verification_evidence")).replace("\n", " "),  # 记忆库记录检索流程输入值
    ]

    # 返回 handoff_summary 的 memory 载荷。
    return " ".join(part for part in list_parts if part.strip()).strip()

# 定义 write_handoff_memory 的memory 管理处理入口。
def write_handoff_memory(project: Path, data: dict[str, Any], count: int, handoff_path: Path) -> dict[str, Any] | None:

    # 校验 write_handoff_memory 的 memory 分支条件。
    if not memory_enabled(project):

        # 返回 write_handoff_memory 的 memory 载荷。
        return None

    # 调用 init_memory 处理 write_handoff_memory。
    init_memory(project)

    # 保存 temp input 映射，维持 write_handoff_memory 的字段关系。
    dict_temp_input = {  # 记忆库记录检索流程输入值
        "kind": "handoff",  # 记忆库记录检索流程输入值
        "title": f"Handoff #{count}",  # handoff 记忆条目标题
        "summary": handoff_summary(data, count),  # 记忆库记录检索流程输入值
        "source_path": rel(project, handoff_path),  # 记忆库记录检索流程输入值
        "source_hash": file_hash(handoff_path),  # 记忆库记录检索流程输入值
        "tags": ["handoff", "session"],  # 记忆库记录检索流程输入值
        "sensitivity": "normal",  # 记忆库记录检索流程输入值
    }

    # 定位 temp path 的文件边界，供 write_handoff_memory 后续读写校验使用。
    temp_path = project / ".agents" / "memory-handoff-input.json"  # 记忆库记录检索流程输入值

    # 调用 mkdir 处理 write_handoff_memory。
    temp_path.parent.mkdir(exist_ok=True)

    # 调用 write_text 处理 write_handoff_memory。
    temp_path.write_text(json.dumps(dict_temp_input, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    # 保存 result 映射，维持 write_handoff_memory 的字段关系。
    dict_result = write_memory(project, temp_path)  # 记忆库记录检索流程输入值

    # 保护 write_handoff_memory 中允许失败的外部访问。
    try:

        # 调用 unlink 处理 write_handoff_memory。
        temp_path.unlink()
    except OSError:
        pass

    # 汇总 paths，作为记忆库读写和压缩候选清单。
    dict_paths = memory_paths(project)  # 记忆库记录检索流程输入值

    # 整理 write_handoff_memory 需要的 event count 记忆信息。
    event_count = sum(1 for line in dict_paths["events"].read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip())  # 记忆库记录检索流程输入值

    # 整理 write_handoff_memory 需要的 中间载荷 记忆信息。
    dict_result["event_count"] = event_count  # 记忆库记录检索流程输入值

    # 整理 write_handoff_memory 需要的 threshold 记忆信息。
    int_threshold = int(memory_contract(project).get("compress_after_events", 20) or 20)  # 记忆库记录检索流程输入值

    # 校验 write_handoff_memory 的 memory 分支条件。
    if int_threshold > 0 and event_count % int_threshold == 0:

        # 整理 write_handoff_memory 需要的 中间载荷 记忆信息。
        dict_result["compression"] = compress_memory(project)  # 记忆库记录检索流程输入值

    # 返回 write_handoff_memory 的 memory 载荷。
    return dict_result
