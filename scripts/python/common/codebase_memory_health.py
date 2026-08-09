"""提供 codebase-memory 索引范围与 WAL 健康的纯验证合同。"""

# 标准库只负责字节级文件处理、路径匹配和类型注解。
from fnmatch import fnmatch
from pathlib import Path
import time
from typing import Any

# UTC 时间戳为每次 WAL 观测提供可审计顺序证据。
from datetime import datetime, timezone

# 固定错误载荷让调用方无需解析自然语言诊断。
def health_error(str_code: str, str_message: str) -> dict[str, str]:
    """构造稳定的 codebase-memory 健康错误。

    参数：str_code 为固定错误码，str_message 为不含敏感内容的诊断。
    返回：包含 code 和 message 的错误对象。
    """

    # 字段保持最小，便于 CLI、渲染器和发布门禁共同消费。
    return {"code": str_code, "message": str_message}

# 受管区渲染器稳定排序规则并固定使用 LF。
def render_cbmignore_managed_block(dict_contract: dict[str, Any]) -> str:
    """渲染唯一的 .cbmignore 受管区块。

    参数：dict_contract 为 scope_policy 映射。
    返回：带结束换行的稳定 LF 文本。
    """

    # marker 文本由项目合同定义，不能由实现硬编码替代。
    str_start = str(dict_contract.get("managed_start", ""))  # 受管区开始 marker。

    # 结束 marker 与开始 marker 共同界定唯一可写区域。
    str_end = str(dict_contract.get("managed_end", ""))  # 受管区结束 marker。

    # 去重和排序保证重复执行不会产生无意义漂移。
    list_rules = sorted(  # 稳定的受管忽略规则。
        {
            str(item).strip()  # 当前规范化规则。
            for item in dict_contract.get("required_excludes", [])  # 合同必需排除项。
            if str(item).strip()  # 空规则不进入文件。
        }
    )

    # marker 和规则各占一行，末尾换行便于后续人工追加内容。
    return "\n".join([str_start, *list_rules, str_end, ""])

# 字节边界助手找到 marker 所在整行的结束位置。
def marker_line_end(bytes_content: bytes, int_marker_end: int) -> int:
    """返回 marker 行及其换行符之后的字节偏移。

    参数：bytes_content 为完整文件，int_marker_end 为 marker 末尾偏移。
    返回：保留 marker 后首个完整换行的切片边界。
    """

    # LF 是两种常见换行的共同终止字节。
    int_newline = bytes_content.find(b"\n", int_marker_end)  # marker 行后的 LF 位置。

    # 文件末行没有换行时边界就是文件结尾。
    if int_newline < 0:

        # 返回完整长度避免截断 marker 外字节。
        return len(bytes_content)

    # 包含 LF，使 marker 后人工内容从下一字节原样保留。
    return int_newline + 1

# .cbmignore 检查器只管理 marker 内字节。
def inspect_cbmignore(
    path_project: Path,
    dict_contract: dict[str, Any],
    bool_apply: bool,
) -> dict[str, Any]:
    """检查或幂等更新根 .cbmignore 受管区。

    参数：path_project 为项目根，dict_contract 为 scope_policy。
    参数：bool_apply 控制是否允许写入 marker 内或追加唯一受管区。
    返回：包含 ok、errors、changed 和 path 的结构化结果。
    """

    # 合同路径必须相对项目根解析。
    path_ignore = path_project / str(dict_contract.get("cbmignore_path", ".cbmignore"))  # 范围文件路径。

    # marker 使用 UTF-8 字节搜索，避免改写 marker 外换行和编码。
    bytes_start = str(dict_contract.get("managed_start", "")).encode("utf-8")  # 开始 marker 字节。

    # 结束 marker 采用相同编码合同。
    bytes_end = str(dict_contract.get("managed_end", "")).encode("utf-8")  # 结束 marker 字节。

    # 受管区渲染结果固定为 UTF-8 与 LF。
    bytes_managed = render_cbmignore_managed_block(dict_contract).encode("utf-8")  # 新受管区字节。

    # 缺少文件时只允许显式 apply 创建。
    if not path_ignore.is_file():

        # 只读检查必须 fail closed，不能把缺失解释为全量纳入。
        if not bool_apply:

            # 固定错误码供七阶段门禁识别范围缺失。
            return {
                "ok": False,
                "errors": [health_error("CBM_SCOPE_MISSING", ".cbmignore is missing")],
                "changed": False,
                "path": str(path_ignore),
            }

        # 新文件只包含受管区，不生成推测性人工内容。
        path_ignore.write_bytes(bytes_managed)

        # 创建成功后返回完整证据。
        return {"ok": True, "errors": [], "changed": True, "path": str(path_ignore)}

    # 现有文件必须按字节读取，保证人工区不被文本规范化。
    bytes_original = path_ignore.read_bytes()  # 写入前完整字节。

    # marker 计数必须同时为零或同时为一。
    int_start_count = bytes_original.count(bytes_start)  # 开始 marker 数量。

    # 结束 marker 独立计数以识别半个区块。
    int_end_count = bytes_original.count(bytes_end)  # 结束 marker 数量。

    # 重复、缺半或空 marker 都不能自动猜测修复边界。
    if not bytes_start or not bytes_end or int_start_count != int_end_count or int_start_count > 1:

        # marker 结构异常在 apply 模式下同样阻断。
        return {
            "ok": False,
            "errors": [health_error("CBM_SCOPE_MARKERS", ".cbmignore managed markers are invalid")],
            "changed": False,
            "path": str(path_ignore),
        }

    # 没有 marker 时 apply 只在文件末尾追加，不修改既有字节。
    if int_start_count == 0:

        # 只读模式把未受管文件视为范围 marker 缺失。
        if not bool_apply:

            # 错误区分文件缺失与 marker 缺失。
            return {
                "ok": False,
                "errors": [health_error("CBM_SCOPE_MARKERS", ".cbmignore managed markers are missing")],
                "changed": False,
                "path": str(path_ignore),
            }

        # 非空人工内容没有结尾换行时只追加分隔 LF，不改写原字节。
        bytes_separator = b"" if not bytes_original or bytes_original.endswith(b"\n") else b"\n"  # 追加分隔字节。

        # 原文件作为严格前缀逐字节保留。
        bytes_updated = bytes_original + bytes_separator + bytes_managed  # 追加后的完整内容。

    # 唯一 marker 对允许原位替换受管区。
    else:

        # 开始 marker 的唯一位置已由计数证明。
        int_start = bytes_original.find(bytes_start)  # 受管区起始字节。

        # 结束 marker 必须位于开始 marker 之后。
        int_end = bytes_original.find(bytes_end)  # 结束 marker 起始字节。

        # 反序或嵌套形态不能自动修复。
        if int_start < 0 or int_end <= int_start:

            # 固定 marker 错误阻止覆盖未知人工内容。
            return {
                "ok": False,
                "errors": [health_error("CBM_SCOPE_MARKERS", ".cbmignore managed markers are out of order")],
                "changed": False,
                "path": str(path_ignore),
            }

        # 替换边界包含结束 marker 整行。
        int_after_end = marker_line_end(bytes_original, int_end + len(bytes_end))  # 受管区后首字节。

        # 只读检查比较逻辑行，不把 CRLF 与 LF 差异误判为规则漂移。
        if not bool_apply:

            # UTF-8 是受管区生成和解析的固定编码。
            try:

                # splitlines 保留规则顺序但忽略平台换行表示。
                list_actual_lines = bytes_original[int_start:int_after_end].decode("utf-8").splitlines()  # 实际受管逻辑行。

            # 受管区编码损坏时不能安全解释规则。
            except UnicodeDecodeError:

                # 编码异常归入 marker/受管边界不可验证。
                return {
                    "ok": False,
                    "errors": [health_error("CBM_SCOPE_MARKERS", ".cbmignore managed block is not UTF-8")],
                    "changed": False,
                    "path": str(path_ignore),
                }

            # 预期逻辑行来自同一稳定渲染器。
            list_expected_lines = bytes_managed.decode("utf-8").splitlines()  # 合同受管逻辑行。

            # 规则缺失、增加或顺序变化均要求显式 apply 更新。
            if list_actual_lines != list_expected_lines:

                # 固定错误码标识规则语义漂移。
                return {
                    "ok": False,
                    "errors": [health_error("CBM_SCOPE_REQUIRED_RULE", ".cbmignore managed rules are stale")],
                    "changed": False,
                    "path": str(path_ignore),
                }

            # 换行表示差异不影响只读范围语义。
            return {"ok": True, "errors": [], "changed": False, "path": str(path_ignore)}

        # marker 外前缀和后缀完全复用原始字节。
        bytes_updated = bytes_original[:int_start] + bytes_managed + bytes_original[int_after_end:]  # 新完整内容。

    # 只读模式不能修复受管区漂移。
    if bytes_updated != bytes_original and not bool_apply:

        # 每条缺失规则使用同一固定错误码。
        return {
            "ok": False,
            "errors": [health_error("CBM_SCOPE_REQUIRED_RULE", ".cbmignore required managed rules are stale")],
            "changed": False,
            "path": str(path_ignore),
        }

    # apply 仅在真实差异时写入，保证幂等。
    if bytes_updated != bytes_original:

        # 单次写入完整字节，marker 外片段保持原样。
        path_ignore.write_bytes(bytes_updated)

    # changed 表示本轮是否实际需要内容变化。
    return {
        "ok": True,
        "errors": [],
        "changed": bytes_updated != bytes_original,
        "path": str(path_ignore),
    }

# 简化的 gitignore 顺序匹配器覆盖目录、glob 和显式 allow 规则。
def path_is_ignored(str_relative_path: str, list_rules: list[str]) -> bool:
    """判断项目相对文件是否被最终规则排除。

    参数：str_relative_path 为 POSIX 文件路径，list_rules 为有序规则。
    返回：最后一个匹配规则决定的排除状态。
    """

    # 默认纳入，只有匹配排除规则后才改变状态。
    bool_ignored = False  # 当前最终排除状态。

    # gitignore 语义由后出现的匹配规则覆盖前一条。
    for str_raw_rule in list_rules:

        # 规则规范化只影响受管语义判断，不回写人工区。
        str_rule = str_raw_rule.strip()  # 本轮路径匹配规则正文。

        # 空行、marker 和注释不参与路径判断。
        if not str_rule or str_rule.startswith("#"):

            # 继续检查后续真实规则。
            continue

        # 感叹号表示重新纳入匹配路径。
        bool_include = str_rule.startswith("!")  # 当前是否为 allow 规则。

        # 匹配正文移除 allow 前缀和根锚定斜杠。
        str_pattern = str_rule.lstrip("!").lstrip("/")  # 当前匹配模式。

        # 目录规则匹配自身全部后代。
        if str_pattern.endswith("/"):

            # 去掉末尾斜杠后执行前缀边界匹配。
            str_prefix = str_pattern.rstrip("/")  # 当前目录前缀。

            # 目录本身或任一后代都视为匹配。
            bool_matches = (  # 当前目录规则是否命中。
                str_relative_path == str_prefix  # 目录自身精确命中。
                or str_relative_path.startswith(str_prefix + "/")  # 任一后代路径命中。
            )

        # 文件与 glob 规则同时支持完整路径和叶名匹配。
        else:

            # 完整路径优先，叶名兼容无目录的通配模式。
            bool_matches = (  # 当前文件或 glob 规则是否命中。
                fnmatch(str_relative_path, str_pattern)  # 完整相对路径命中。
                or fnmatch(Path(str_relative_path).name, str_pattern)  # 叶名兼容命中。
            )

        # 只有当前规则命中时才覆盖最终状态。
        if bool_matches:

            # allow 规则清除排除状态，普通规则设置排除。
            bool_ignored = not bool_include  # 当前命中规则决定的排除结论。

    # 所有规则处理完成后的状态才是最终结论。
    return bool_ignored

# 范围分类器用真实项目树验证保护路径与治理历史比例。
def classify_index_scope(path_project: Path, dict_contract: dict[str, Any]) -> dict[str, Any]:
    """分类根 .cbmignore 对真实项目文件的作用。

    参数：path_project 为项目根，dict_contract 为 scope_policy。
    返回：包含计数、比例、保护路径证据和固定错误的报告。
    """

    # 范围文件缺失时复用只读检查的固定诊断。
    dict_ignore_check = inspect_cbmignore(path_project, dict_contract, False)  # .cbmignore 只读证据。

    # marker 或规则错误优先返回，不继续推测索引范围。
    if not dict_ignore_check.get("ok", False):

        # 保留原错误码并标记最终证据不完整。
        return {**dict_ignore_check, "evidence_complete": False}

    # UTF-8 规则是受管区生成合同的一部分。
    path_ignore = path_project / str(dict_contract.get("cbmignore_path", ".cbmignore"))  # 已验证范围文件。

    # 行顺序必须保留，后规则才能覆盖前规则。
    list_rules = path_ignore.read_text(encoding="utf-8").splitlines()  # 实际有序忽略规则。

    # .git 内部元数据不属于代码图谱候选。
    list_files = sorted(  # 真实项目普通文件集合。
        path_file  # 当前真实普通文件。
        for path_file in path_project.rglob("*")  # 遍历项目树全部后代。
        if path_file.is_file() and ".git" not in path_file.relative_to(path_project).parts  # 只保留非 Git 普通文件。
    )

    # 统一 POSIX 相对路径用于跨平台匹配。
    list_relative_files = [path_file.relative_to(path_project).as_posix() for path_file in list_files]  # 文件相对路径。

    # 最终纳入集合排除每个被规则命中的文件。
    list_included = [path for path in list_relative_files if not path_is_ignored(path, list_rules)]  # 纳入文件。

    # 治理历史采用稳定路径族分类，不把当前合同文档计入历史。
    list_governance = [
        path  # 当前仍被纳入的治理文件。
        for path in list_included  # 遍历最终纳入路径。
        if path.startswith(".agents/")  # 代理治理状态。
        or "/history_" in path  # 任一历史归档目录。
        or path.startswith("docs/memory/")  # 长期会话记忆。
        or path.startswith("docs/handoff/")  # 交接与历史交接。
    ]  # 最终仍纳入的治理历史文件。

    # 空索引以零比例表示，但仍会由保护路径检查发现问题。
    float_governance_ratio = len(list_governance) / len(list_included) if list_included else 0.0  # 治理历史比例。

    # 所有独立范围错误共同返回，便于一次修复完整。
    list_errors: list[dict[str, str]] = []  # 范围分类诊断。

    # 每个保护路径下至少一个真实文件且不得被排除。
    for str_protected in dict_contract.get("protected_paths", []):

        # 目录声明去除末尾斜杠后用于边界匹配。
        str_prefix = str(str_protected).strip().strip("/")  # 当前保护路径。

        # 根文件精确匹配，目录匹配全部后代。
        list_protected_files = [
            path  # 当前保护根下的真实文件。
            for path in list_relative_files  # 遍历真实文件集合。
            if path == str_prefix or path.startswith(str_prefix + "/")  # 精确根或任一后代。
        ]  # 当前保护路径真实文件。

        # 已存在保护根只有在全部文件被排除时才视为失去索引覆盖。
        if list_protected_files and all(path_is_ignored(path, list_rules) for path in list_protected_files):

            # 不回显内部文件名，只标识合同保护根。
            list_errors.append(
                health_error("CBM_SCOPE_PROTECTED", f"protected path is excluded: {str_protected}")
            )

    # 治理历史比例必须不超过合同上限。
    if float_governance_ratio > float(dict_contract.get("max_governance_ratio", 0.05)):

        # 诊断只包含聚合比例，不暴露治理文件路径。
        list_errors.append(
            health_error("CBM_SCOPE_GOVERNANCE_RATIO", "included governance history exceeds the configured ratio")
        )

    # 计数和比例足以复核范围，不返回完整路径清单。
    return {
        "ok": not list_errors,
        "errors": list_errors,
        "evidence_complete": not list_errors,
        "included_file_count": len(list_included),
        "excluded_file_count": len(list_relative_files) - len(list_included),
        "governance_file_count": len(list_governance),
        "governance_ratio": float_governance_ratio,
    }

# WAL 评估器只消费调用方已经绑定项目的数值证据。
def evaluate_wal_health(
    int_database_bytes: int,
    list_wal_samples: list[int],
    list_processes: list[dict[str, Any]],
    dict_contract: dict[str, Any],
) -> dict[str, Any]:
    """按固定阈值评估 WAL 样本和匹配进程。

    参数：int_database_bytes 为数据库字节数，list_wal_samples 为 WAL 样本。
    参数：list_processes 为已绑定项目的进程证据，dict_contract 为 wal_health。
    返回：包含 ok、errors 和聚合观测值的结果。
    """

    # 空列表按零 WAL 处理，避免健康首次索引被误判。
    int_wal_bytes = int(list_wal_samples[-1]) if list_wal_samples else 0  # 最后一次 WAL 字节数。

    # 每项阈值独立产生固定错误码。
    list_errors: list[dict[str, str]] = []  # WAL 健康诊断。

    # 绝对上限不依赖数据库大小。
    if int_wal_bytes > int(dict_contract.get("absolute_limit_bytes", 0)):

        # 固定码区分绝对容量异常。
        list_errors.append(health_error("CBM_WAL_ABSOLUTE_LIMIT", "WAL exceeds the absolute byte limit"))

    # 比例阈值按数据库当前大小计算。
    int_ratio_limit = int_database_bytes * int(dict_contract.get("database_ratio_limit", 0))  # 普通比例上限。

    # 非零 WAL 超过计算阈值时阻断。
    if int_wal_bytes > int_ratio_limit and int_wal_bytes > 0:

        # 固定码区分 WAL 与数据库比例异常。
        list_errors.append(health_error("CBM_WAL_RATIO_LIMIT", "WAL exceeds the database ratio limit"))

    # 足够样本且严格递增表示写入仍未稳定。
    int_sample_count = int(dict_contract.get("sample_count", 3))  # 合同要求样本数。

    # 只取最后一个完整窗口，避免更早历史掩盖当前趋势。
    list_window = [int(item) for item in list_wal_samples[-int_sample_count:]]  # 当前趋势窗口。

    # 每一对相邻样本都必须严格增长，且最后值非零。
    if (
        len(list_window) == int_sample_count
        and int_wal_bytes > 0
        and all(int_next > int_previous for int_previous, int_next in zip(list_window, list_window[1:]))
    ):

        # 固定码标识持续增长而非单点容量异常。
        list_errors.append(health_error("CBM_WAL_GROWING", "WAL samples are strictly increasing"))

    # 只有达到长寿命阈值的匹配进程参与多进程风险。
    list_long_processes = [
        item  # 当前达到年龄阈值的匹配进程。
        for item in list_processes  # 遍历已绑定项目进程。
        if int(item.get("age_seconds", 0)) >= int(dict_contract.get("long_process_seconds", 0))  # 达到长寿命阈值。
    ]  # 长寿命匹配进程。

    # 多进程容量门槛取绝对值与数据库比例中的较大者。
    int_long_limit = max(  # 长寿命多进程 WAL 上限。
        int(dict_contract.get("long_wal_absolute_bytes", 0)),  # 长进程绝对字节阈值。
        int_database_bytes * int(dict_contract.get("long_wal_ratio_limit", 0)),  # 长进程数据库比例阈值。
    )

    # 进程数和 WAL 容量必须同时越界才阻断。
    if (
        len(list_long_processes) >= int(dict_contract.get("long_process_count", 0))
        and int_wal_bytes > int_long_limit
    ):

        # 固定码区分并发会话风险。
        list_errors.append(
            health_error(
                "CBM_WAL_MULTI_PROCESS",
                "large WAL is shared by multiple long-lived processes",
            )
        )

    # 仅返回聚合进程数和字节数，不泄漏命令行或环境。
    return {
        "ok": not list_errors,
        "errors": list_errors,
        "database_bytes": int_database_bytes,
        "wal_bytes": int_wal_bytes,
        "sample_count": len(list_wal_samples),
        "process_count": len(list_processes),
    }

# 基线收集器拒绝在缺少唯一绑定元数据时扫描外部缓存。
def collect_wal_baseline(
    path_project: Path,
    dict_dependency: dict[str, Any],
    dict_indexed_project: dict[str, Any],
    dict_contract: dict[str, Any],
) -> dict[str, Any]:
    """验证 WAL 基线是否有唯一项目绑定证据。

    参数：path_project 为项目根，dict_dependency 与 dict_indexed_project 为上游证据。
    参数：dict_contract 为 wal_health 合同。
    返回：无法唯一绑定时固定 fail-closed；明确 absent 时返回零基线。
    """

    # 官方项目列表明确 absent 是无需数据库路径的唯一健康空状态。
    if dict_indexed_project.get("state") == "absent" and dict_dependency.get("cache_root"):

        # 零样本表示项目尚无数据库和 WAL。
        return {
            "ok": True,
            "errors": [],
            "state": "absent",
            "samples": [0 for _ in range(int(dict_contract.get("sample_count", 3)))],
            "project": str(path_project),
        }

    # 缓存根、数据库路径和项目路径必须由上游唯一绑定证据显式提供。
    path_cache_root = Path(str(dict_dependency.get("cache_root", ""))).resolve()  # 已配置缓存根。

    # 数据库路径只能来自上游唯一项目绑定结果。
    path_database = Path(str(dict_indexed_project.get("database_path", ""))).resolve()  # 绑定数据库。

    # 项目路径用于阻止同名索引误绑定当前工作目录。
    path_bound_project = Path(str(dict_indexed_project.get("project_path", ""))).resolve()  # 绑定项目根。

    # 缓存根字段来自已验证的 Codex MCP 配置。
    bool_cache_root_present = bool(dict_dependency.get("cache_root"))  # 缓存根字段是否存在。

    # 数据库路径字段来自唯一项目记录的文件映射。
    bool_database_path_present = bool(dict_indexed_project.get("database_path"))  # 数据库字段是否存在。

    # 项目路径字段用于与当前受管根执行精确比较。
    bool_project_path_present = bool(dict_indexed_project.get("project_path"))  # 项目字段是否存在。

    # 三个来源字段缺一不可，空路径不能参与解析后的路径比较。
    bool_has_binding_fields = bool_cache_root_present and bool_database_path_present and bool_project_path_present  # 必需字段结论。

    # 数据库必须直接位于缓存根，且项目根必须与当前受管项目完全一致。
    bool_paths_match = path_database.parent == path_cache_root and path_bound_project == path_project.resolve()  # 路径绑定结论。

    # 字段、路径和实体同时成立才构成可采样的唯一绑定。
    bool_unique_binding = bool_has_binding_fields and bool_paths_match and path_database.is_file()  # 最终绑定结论。

    # 任一绑定字段缺失或错配时禁止扫描相似文件名猜测数据库。
    if not bool_unique_binding:

        # 固定错误码供治理入口稳定识别证据缺失。
        return {
            "ok": False,
            "errors": [
                health_error(
                    "CBM_WAL_EVIDENCE_UNAVAILABLE",
                    "database and WAL evidence cannot be uniquely bound to the indexed project",
                )
            ],
            "samples": [],
            "project": str(path_project),
        }

    # SQLite WAL 与主数据库使用固定同路径后缀，不遍历缓存目录。
    path_wal = Path(f"{path_database}-wal")  # 唯一绑定数据库对应 WAL。

    # 合同采样次数至少为一次，避免空窗口误报健康。
    int_sample_count = max(1, int(dict_contract.get("sample_count", 3)))  # WAL 采样次数。

    # 采样间隔允许测试和显式合同使用零值，生产合同保持有限等待。
    float_interval_seconds = max(0.0, float(dict_contract.get("sample_interval_seconds", 0)))  # 采样间隔。

    # 只记录字节数，不返回数据库、WAL 或外部缓存路径。
    list_wal_samples: list[int] = []  # 连续 WAL 字节样本。

    # 时间戳与字节样本按相同索引一一对应。
    list_sample_times: list[str] = []  # WAL 采样 UTC 时间。

    # 固定次数采样用于区分稳定大文件和持续增长写入。
    for int_index in range(int_sample_count):

        # 先记录观测时刻，再读取同一次样本的文件大小。
        list_sample_times.append(datetime.now(timezone.utc).isoformat())

        # WAL 尚未创建或已 checkpoint 清空时样本为零。
        list_wal_samples.append(path_wal.stat().st_size if path_wal.is_file() else 0)

        # 最后一次采样后不再额外等待。
        if int_index + 1 < int_sample_count and float_interval_seconds:

            # 标准库 sleep 只受合同中的短采样间隔控制。
            time.sleep(float_interval_seconds)

    # 进程证据只保留公开字段，命令行、环境和路径不得进入返回载荷。
    list_processes = [
        {
            "pid": int(item.get("pid", 0)),  # 匿名进程标识。
            "start_time": str(item.get("start_time", "")),  # UTC 启动时间。
            "age_seconds": int(item.get("age_seconds", 0)),  # 阈值所需年龄。
        }
        for item in dict_indexed_project.get("processes", [])  # 上游匹配进程证据。
        if isinstance(item, dict)  # 损坏进程项不参与评估。
    ]

    # 主数据库大小只读取一次，保证同一次评估使用一致基准。
    int_database_bytes = path_database.stat().st_size  # 唯一绑定数据库字节数。

    # 纯评估函数统一执行绝对值、比例、增长和多进程阈值。
    dict_health = evaluate_wal_health(int_database_bytes, list_wal_samples, list_processes, dict_contract)  # WAL 健康聚合。

    # 返回最小聚合证据，不回显外部缓存路径或进程命令行。
    return {
        **dict_health,
        "state": "indexed",
        "samples": list_wal_samples,
        "sample_times": list_sample_times,
        "processes": list_processes,
        "project": str(path_project),
    }
