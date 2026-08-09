"""验证不透明远程测试收据而不读取或枚举 tests 内容。"""

# 标准库负责规范 JSON 哈希和 UTC freshness 计算。
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

# 产品模块名称虽以 test_ 开头，但不属于 pytest 测试收集边界。
__test__ = False  # 禁止 pytest 把收据验证函数当作测试用例。

# 发布证据最多允许距当前时间二十四小时，超窗必须重新远程验证。
DEFAULT_FRESHNESS_SECONDS = 24 * 60 * 60  # 默认远程证据有效期。

# Git pathspec 在列出候选前排除测试、派生收据、运行态和历史归档。
SOURCE_MANIFEST_EXCLUDES = (  # 非测试发布清单的固定排除边界。
    ":(exclude,glob)AGENTS.md",  # 根规则属于治理元数据，不是运行时技能源码。
    ":(exclude,glob)**/AGENTS.md",  # 作用域规则同样不进入发布源码哈希。
    ":(exclude,glob)tests/**",  # TESTER 独占测试树。
    ":(exclude,glob)docs/git_manager/test-evidence-*.json",  # 收据自引用路径。
    ":(exclude,glob).agents/semantic-review-*.json",  # 临时语义审查证据。
    ":(exclude,glob).settings/**",  # 本地运行配置。
    ":(exclude,glob).codebase-memory/**",  # 图谱持久化产物。
    ":(exclude,glob)dist/**",  # 版本化发布产物。
    ":(exclude,glob)docs/handoff/**",  # 收尾交接历史。
    ":(exclude,glob)docs/memory/**",  # 项目记忆运行态。
    ":(exclude,glob)**/history/**",  # 通用历史目录。
    ":(exclude,glob)**/archive/**",  # 通用归档目录。
)

# 收据顶层字段必须完整，缺失时一律 fail closed。
REQUIRED_FIELDS = frozenset(  # 不透明收据固定顶层字段。
    {
        "schema",  # 收据 schema 版本。
        "kind",  # 收据类型标识。
        "test_commit_sha",  # TESTER 提交绑定。
        "tests_tree_hash",  # 不透明 tests 树哈希。
        "tests_file_count",  # 测试文件聚合计数。
        "tests_byte_count",  # 测试字节聚合计数。
        "source_manifest_hash",  # 非测试源码清单哈希。
        "remote_server_id",  # 远程服务器不透明标识。
        "remote_fingerprint_hash",  # 远程环境指纹哈希。
        "remote_cwd_hash",  # 远程目录哈希。
        "validation_archive_hash",  # 验证归档哈希。
        "remote_pytest",  # 三阶段远程 pytest 证据。
        "skill_pressure_report_hash",  # 技能压力报告哈希。
        "tests_outside_staged_count",  # tests 外暂存计数。
        "receipt_sha256",  # 排除自身后的收据哈希。
    }
)

# 三类远程 pytest 证据共同覆盖定向、回归和全量验证。
REQUIRED_REMOTE_PHASES = ("targeted", "regression", "full")  # 固定远程验证阶段顺序。

# 每个远程阶段使用相同的最小不透明字段集合。
REQUIRED_REMOTE_FIELDS = frozenset(  # 单阶段必需字段。
    {"command_hash", "exit_code", "count", "timestamp"}  # 单阶段完整字段集合。
)

# 固定错误对象让发布门禁无需解析自然语言。
def evidence_error(str_code: str, str_message: str) -> str:
    """构造不透明测试证据错误。

    参数：str_code 为稳定错误码，str_message 为脱敏诊断。
    返回：包含固定 code 和脱敏 message 的错误字符串。
    """

    # 错误载荷不携带测试路径、文件名或源码。
    return f"[{str_code}] {str_message}"

# 规范哈希排除自哈希字段并固定 JSON 序列化参数。
def canonical_receipt_sha256(dict_receipt: dict[str, Any]) -> str:
    """复算不透明测试收据的自哈希。

    参数：dict_receipt 为原始收据对象。
    返回：排除 receipt_sha256 后的 canonical JSON SHA-256。
    """

    # 浅复制足以移除唯一顶层自引用字段。
    dict_payload = dict(dict_receipt)  # 待哈希收据副本。

    # 自哈希值本身不得进入摘要输入。
    dict_payload.pop("receipt_sha256", None)

    # sort_keys 和紧凑 separators 构成固定跨平台字节合同。
    bytes_canonical = json.dumps(  # 规范 JSON 字节来源文本。
        dict_payload,  # 排除自哈希后的收据对象。
        ensure_ascii=False,  # 保留 UTF-8 字符语义。
        sort_keys=True,  # 固定对象键顺序。
        separators=(",", ":"),  # 移除非语义空白。
    ).encode("utf-8")

    # SHA-256 十六进制字符串是收据公开绑定值。
    return hashlib.sha256(bytes_canonical).hexdigest()

# ISO-8601 解析器统一处理 Z 与显式时区。
def parse_utc_timestamp(str_timestamp: str) -> datetime | None:
    """解析带时区的 ISO-8601 时间戳。

    参数：str_timestamp 为远程证据或当前 UTC 时间。
    返回：规范化 UTC datetime；无效或无时区时为 None。
    """

    # Z 后缀转换为标准库可直接解析的显式 UTC 偏移。
    str_normalized = str_timestamp.strip().replace("Z", "+00:00")  # 可解析时间文本。

    # 语法错误不向外传播平台异常。
    try:

        # 解析结果必须继续验证时区存在。
        datetime_value = datetime.fromisoformat(str_normalized)  # 原始时区时间对象。

    # 非法日期或时区格式统一返回 None。
    except ValueError:

        # 调用方将 None 转为固定 freshness 错误。
        return None

    # naive 时间无法证明远程证据的新鲜度。
    if datetime_value.tzinfo is None:

        # 明确拒绝依赖本地时区猜测。
        return None

    # 所有比较在 UTC 下完成。
    return datetime_value.astimezone(timezone.utc)

# 元数据验证器只处理 schema、自哈希和当前树绑定。
def validate_receipt_metadata(
    dict_receipt: dict[str, Any],
    str_expected_tests_tree_hash: str,
    str_expected_source_manifest_hash: str,
) -> list[str]:
    """验证收据元数据和当前源码绑定。

    参数：dict_receipt 为收据对象。
    参数：str_expected_tests_tree_hash 为当前 tests 树哈希。
    参数：str_expected_source_manifest_hash 为当前非测试源码清单哈希。
    返回：全部脱敏元数据错误。
    """

    # 每项独立错误共同返回，便于 TESTER 一次重签。
    list_errors: list[str] = []  # 元数据诊断。

    # 必需字段集合必须全部存在。
    if not REQUIRED_FIELDS.issubset(dict_receipt):

        # 缺失字段属于公开 schema 名称，不包含测试路径或内容。
        list_missing_fields = sorted(REQUIRED_FIELDS - set(dict_receipt))  # 缺失收据字段。

        # 精确字段名帮助 TESTER 重签完整收据。
        list_errors.append(
            evidence_error(
                "TEST_EVIDENCE_SCHEMA",
                "test evidence payload is missing: " + ", ".join(list_missing_fields),
            )
        )

    # 固定版本和 kind 防止误用其他 JSON。
    if dict_receipt.get("schema") != 1 or dict_receipt.get("kind") != "opaque-test-evidence":

        # 合同标识错误要求重新生成收据。
        list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", "test evidence schema or kind is invalid"))

    # 自哈希必须绑定除自身外的全部字段。
    if str(dict_receipt.get("receipt_sha256", "")) != canonical_receipt_sha256(dict_receipt):

        # 任一内容变化都会触发完整性错误。
        list_errors.append(evidence_error("TEST_EVIDENCE_RECEIPT_HASH", "test evidence receipt hash does not match"))

    # 当前 tests 树必须与 TESTER 收据一致。
    if str(dict_receipt.get("tests_tree_hash", "")) != str_expected_tests_tree_hash:

        # 不回显实际 hash。
        list_errors.append(evidence_error("TEST_EVIDENCE_TESTS_HASH", "tests tree hash does not match"))

    # 当前非测试源码清单必须与收据一致。
    if str(dict_receipt.get("source_manifest_hash", "")) != str_expected_source_manifest_hash:

        # 源码漂移要求远程重跑和重签。
        list_errors.append(evidence_error("TEST_EVIDENCE_SOURCE_HASH", "source manifest hash does not match"))

    # tests 边界外暂存任何内容都阻断发布。
    if dict_receipt.get("tests_outside_staged_count") != 0:

        # 不列出越界路径。
        list_errors.append(evidence_error("TEST_EVIDENCE_STAGE_BOUNDARY", "staged content escaped the tests boundary"))

    # 文件数和字节数必须是非负整数聚合。
    for str_count_field in ("tests_file_count", "tests_byte_count"):

        # 当前字段值只用于类型与范围判断。
        object_count = dict_receipt.get(str_count_field)  # 当前聚合计数。

        # bool 不接受为整数计数。
        if isinstance(object_count, bool) or not isinstance(object_count, int) or object_count < 0:

            # 统一 schema 错误不泄漏具体规模。
            list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", "test evidence counts are invalid"))

    # 返回全部元数据诊断。
    return list_errors

# 单阶段验证器隔离远程结果与 freshness 分支。
def validate_remote_phase(
    str_phase: str,
    object_phase: Any,
    datetime_now: datetime,
    int_freshness_seconds: int,
) -> list[str]:
    """验证一个远程 pytest 阶段。

    参数：str_phase 为阶段名，object_phase 为阶段载荷。
    参数：datetime_now 为当前 UTC，int_freshness_seconds 为最大年龄。
    返回：当前阶段的脱敏错误列表。
    """

    # 阶段错误保持独立，便于调用方聚合。
    list_errors: list[str] = []  # 当前阶段诊断。

    # 缺失、类型或字段不完整时不能继续验证。
    if not isinstance(object_phase, dict) or not REQUIRED_REMOTE_FIELDS.issubset(object_phase):

        # 阶段名是唯一公开定位信息。
        return [evidence_error("TEST_EVIDENCE_SCHEMA", f"remote pytest phase is incomplete: {str_phase}")]

    # command hash 必须是真实的固定长度 SHA-256，不接受空值或任意占位字符串。
    str_command_hash = object_phase.get("command_hash")  # 当前阶段命令摘要。

    # 非法命令摘要不能形成可审计的阶段证据。
    if (
        not isinstance(str_command_hash, str)
        or len(str_command_hash) != 64
        or any(str_character not in "0123456789abcdef" for str_character in str_command_hash.lower())
    ):

        # 命令摘要无效时不能把阶段结果当作可审计证据。
        list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", f"remote command hash is invalid: {str_phase}"))

    # exit code 必须是非布尔整数，避免 True/False 被 Python 当作 1/0 接受。
    object_exit_code = object_phase.get("exit_code")  # 当前阶段退出码。

    # 非法退出码必须单独报告为 schema 错误。
    if isinstance(object_exit_code, bool) or not isinstance(object_exit_code, int):

        # 类型错误与非零失败分别保持可诊断。
        list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", f"remote exit code is invalid: {str_phase}"))

    # count 必须是非布尔非负整数，防止伪造阶段规模。
    object_count = object_phase.get("count")  # 当前阶段用例计数。

    # 非法计数不能进入远程阶段摘要。
    if isinstance(object_count, bool) or not isinstance(object_count, int) or object_count < 0:

        # 计数错误阻断发布证据。
        list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", f"remote test count is invalid: {str_phase}"))

    # 任一非零退出直接阻断。
    if object_exit_code != 0:

        # 不返回命令文本或日志。
        list_errors.append(evidence_error("TEST_EVIDENCE_REMOTE_FAILURE", f"remote pytest failed: {str_phase}"))

    # 阶段时间必须是带时区的 ISO-8601。
    datetime_phase = parse_utc_timestamp(str(object_phase.get("timestamp", "")))  # 当前阶段 UTC 时间。

    # 无效时间不能证明 freshness。
    if datetime_phase is None:

        # 返回后不执行年龄计算。
        list_errors.append(evidence_error("TEST_EVIDENCE_FRESHNESS", f"remote timestamp is invalid: {str_phase}"))

        # 保留已发现的非零退出错误。
        return list_errors

    # 当前 UTC 与阶段 UTC 的差值构成证据年龄。
    float_age_seconds = (datetime_now - datetime_phase).total_seconds()  # 当前阶段证据年龄。

    # 未来时间或超窗时间都视为不新鲜。
    if float_age_seconds < 0 or float_age_seconds > int_freshness_seconds:

        # 不回显精确时间。
        list_errors.append(evidence_error("TEST_EVIDENCE_FRESHNESS", f"remote pytest is stale: {str_phase}"))

    # 返回当前阶段全部错误。
    return list_errors

# 三阶段聚合器同时生成严格脱敏统计。
def validate_remote_pytest(
    object_remote_pytest: Any,
    str_now_utc: str,
    int_freshness_seconds: int,
) -> dict[str, Any]:
    """验证三阶段远程 pytest 证据。

    参数：object_remote_pytest 为阶段映射，str_now_utc 为当前 UTC。
    参数：int_freshness_seconds 为最大证据年龄。
    返回：errors 错误列表和 summary 脱敏阶段统计。
    """

    # 当前时间错误时所有阶段都无法证明新鲜度。
    datetime_now = parse_utc_timestamp(str_now_utc)  # 规范化当前 UTC。

    # 非对象载荷使用空映射完成稳定阶段循环。
    dict_remote = object_remote_pytest if isinstance(object_remote_pytest, dict) else {}  # 安全阶段映射。

    # 顶层结构错误单独记录。
    list_errors = (  # 远程聚合诊断。
        []
        if isinstance(object_remote_pytest, dict)  # 合法对象无需结构错误。
        else [evidence_error("TEST_EVIDENCE_SCHEMA", "remote pytest evidence must be an object")]  # 非对象诊断。
    )

    # 当前时间无效时记录一次聚合错误。
    if datetime_now is None:

        # 使用 epoch 占位只为保持 helper 类型稳定，阶段仍会由聚合错误阻断。
        datetime_now = datetime.fromtimestamp(0, tz=timezone.utc)  # 不可信时间占位。

        # 调用方必须提供带时区的当前 UTC。
        list_errors.append(evidence_error("TEST_EVIDENCE_FRESHNESS", "current UTC timestamp is invalid"))

    # 每个固定阶段独立验证。
    for str_phase in REQUIRED_REMOTE_PHASES:

        # 阶段 helper 返回的错误直接追加。
        list_errors.extend(
            validate_remote_phase(
                str_phase,  # 当前固定阶段名。
                dict_remote.get(str_phase),  # 当前阶段载荷。
                datetime_now,  # 已规范化或占位的 UTC。
                int_freshness_seconds,  # 最大允许年龄。
            )
        )

    # 摘要只保留允许的聚合远程统计。
    dict_summary = {  # 脱敏远程阶段统计。
        str_phase: {  # 当前阶段允许公开的聚合统计。
            "exit_code": dict_remote.get(str_phase, {}).get("exit_code"),  # 远程退出码。
            "count": dict_remote.get(str_phase, {}).get("count"),  # 远程聚合用例计数。
            "timestamp": dict_remote.get(str_phase, {}).get("timestamp"),  # 远程完成时间。
        }
        for str_phase in REQUIRED_REMOTE_PHASES  # 按固定三阶段顺序生成摘要。
    }

    # 字典字段避免调用方依赖二元组位置语义。
    return {"errors": list_errors, "summary": dict_summary}

# 公开验证器只消费调用方提供的 opaque hash 和时间事实。
def validate_test_evidence_payload(
    dict_receipt: dict[str, Any],
    *,
    str_expected_tests_tree_hash: str,
    str_expected_source_manifest_hash: str,
    str_now_utc: str,
    int_freshness_seconds: int,
) -> dict[str, Any]:
    """验证不透明远程测试收据的结构、绑定和 freshness。

    参数：dict_receipt 为不透明测试收据对象。
    参数：str_expected_tests_tree_hash 为当前 tests 树哈希。
    参数：str_expected_source_manifest_hash 为当前非测试源码清单哈希。
    参数：str_now_utc 为当前 UTC 时间。
    参数：int_freshness_seconds 为最大证据年龄秒数。
    返回：包含 ok、errors 和脱敏 summary 的验证结果。
    """

    # 公开合同要求对象；非对象立即 fail closed。
    if not isinstance(dict_receipt, dict):

        # 不对非对象执行任何字段访问。
        return {
            "ok": False,
            "errors": [evidence_error("TEST_EVIDENCE_SCHEMA", "test evidence payload must be an object")],
        }

    # 元数据和绑定检查与远程阶段检查相互独立。
    list_errors = validate_receipt_metadata(  # 全部收据元数据诊断。
        dict_receipt,  # 当前收据对象。
        str_expected_tests_tree_hash,  # 当前不透明 tests 树哈希。
        str_expected_source_manifest_hash,  # 当前非测试源码清单哈希。
    )

    # 首次调用提取三阶段阻断字符串。
    list_remote_errors = list(  # 阻止非零或过期远程 pytest 进入发布的字符串列表。
        validate_remote_pytest(  # 执行三阶段远程证据校验。
            dict_receipt.get("remote_pytest"),  # 本次收据的阶段映射。
            str_now_utc,  # 本轮验证基准 UTC。
            int_freshness_seconds,  # 本轮允许的最大证据年龄。
        )["errors"]
    )

    # 第二次纯函数调用提取允许公开的阶段统计。
    dict_remote_summary = dict(  # 返回给调用方且不含命令哈希的三阶段统计映射。
        validate_remote_pytest(  # 复算确定性的三阶段脱敏统计。
            dict_receipt.get("remote_pytest"),  # 本次摘要的阶段映射。
            str_now_utc,  # 摘要 freshness 的比较基准。
            int_freshness_seconds,  # 摘要采用的有效期上限。
        )["summary"]
    )

    # 远程错误加入最终诊断。
    list_errors.extend(list_remote_errors)

    # 最终结果不返回 commit、服务器、cwd、archive 或测试路径。
    return {
        "ok": not list_errors,
        "errors": list_errors,
        "summary": {
            "tests_tree_hash": dict_receipt.get("tests_tree_hash", ""),
            "tests_file_count": dict_receipt.get("tests_file_count", 0),
            "tests_byte_count": dict_receipt.get("tests_byte_count", 0),
            "remote_pytest": dict_remote_summary,
        },
    }

# Git 调用统一关闭 shell，并把错误转换为收据门禁可处理的异常。
def run_project_git(path_project: Path, list_args: list[str]) -> subprocess.CompletedProcess[bytes]:
    """执行只读 Git 查询并返回原始字节。

    参数：path_project 为仓库根，list_args 为不含 git 的参数。
    返回：成功完成且保留原始 stdout/stderr 的进程结果。
    异常：Git 查询失败时抛出 RuntimeError。
    """

    # 字节输出避免文件名经过终端转义或区域编码改写。
    completed_process_git = subprocess.run(  # 当前只读 Git 查询结果。
        ["git", *list_args],  # 不经 shell 的 Git 参数。
        cwd=path_project,  # 查询所属仓库根。
        check=False,  # 退出码由当前函数转换为异常。
        capture_output=True,  # 保留原始 stdout 和 stderr 字节。
    )

    # 非零退出不能产生可供发布信任的聚合事实。
    if completed_process_git.returncode != 0:

        # 固定异常正文避免泄漏路径或 tests 相关 Git 诊断。
        raise RuntimeError("> ERR: [Python] Git evidence query failed")

    # 调用方消费未经文本规范化的稳定字节。
    return completed_process_git

# 源码清单只读取 Git 已先行排除 tests 和运行态路径后的文件。
def source_manifest_sha256(path_project: Path) -> str:
    """计算当前非测试发布源码的确定性清单哈希。

    参数：path_project 为 Git 仓库根。
    返回：按路径、内容 SHA-256 和字节数绑定的清单 SHA-256。
    异常：Git 查询失败或候选不是普通文件时抛出 RuntimeError。
    """

    # exclude pathspec 由 Git 在输出路径前应用，调用方不会接收 tests 成员。
    completed_process_paths = run_project_git(  # 已排除非发布边界的路径查询。
        path_project,  # 当前发布仓库根。
        [
            "ls-files",  # 使用 Git 索引与工作树候选查询。
            "--cached",  # 纳入已跟踪文件。
            "--others",  # 纳入未跟踪产品候选。
            "--exclude-standard",  # 应用仓库忽略规则。
            "-z",  # 使用无歧义 NUL 分隔。
            "--",  # 终止 Git 选项解析。
            ".",  # 查询当前项目全域。
            *SOURCE_MANIFEST_EXCLUDES,  # 在输出前应用固定排除边界。
        ],
    )

    # 空成员来自终止 NUL，不进入路径集合。
    list_relative_bytes = sorted(  # 稳定字节序路径集合。
        bytes_relative  # 当前非空仓库相对路径字节。
        for bytes_relative in completed_process_paths.stdout.split(b"\0")  # 遍历 NUL 分隔候选。
        if bytes_relative  # 排除终止 NUL 产生的空成员。
    )

    # 整体摘要逐成员吸收无歧义的 NUL 分隔事实。
    hash_manifest = hashlib.sha256()  # 非测试源码清单聚合摘要。

    # 每个候选只在 Git 完成排除后才读取内容。
    for bytes_relative in list_relative_bytes:

        # Git -z 路径使用 UTF-8；surrogateescape 保留异常字节的可逆语义。
        str_relative = bytes_relative.decode("utf-8", errors="surrogateescape")  # 当前仓库相对路径。

        # 路径锚定仓库根，候选不存在时让调用方 fail closed。
        path_source = path_project / str_relative  # 当前非测试源码文件。

        # 只允许普通文件进入发布清单。
        if not path_source.is_file():

            # Git 候选与工作树不一致时不能签发稳定收据。
            raise RuntimeError("> ERR: [Python] source manifest candidate is not a regular file")

        # 单文件字节同时提供内容摘要与精确规模。
        bytes_source = path_source.read_bytes()  # 当前源码原始字节。

        # 单文件摘要绑定未经规范化的原始内容。
        str_source_sha256 = hashlib.sha256(bytes_source).hexdigest()  # 当前源码内容摘要。

        # 路径、内容摘要和大小以 NUL 分隔，避免串联歧义。
        bytes_manifest_record = b"\0".join(  # 当前文件无歧义清单记录。
            (
                bytes_relative,  # 仓库相对路径。
                str_source_sha256.encode("ascii"),  # 文件内容摘要。
                str(len(bytes_source)).encode("ascii"),  # 文件原始字节数。
            )
        ) + b"\n"

        # 聚合摘要按稳定路径顺序吸收当前记录。
        hash_manifest.update(bytes_manifest_record)

    # 十六进制摘要供 TESTER 收据和发布门禁共享。
    return hash_manifest.hexdigest()

# tests 只通过 Git tree id 绑定，不列出任何成员。
def tests_tree_hash(path_project: Path) -> str:
    """读取 HEAD 中不透明 tests 树哈希。

    参数：path_project 为 Git 仓库根。
    返回：HEAD:tests 的 Git tree id。
    """

    # rev-parse 只返回树对象身份，不枚举测试路径或内容。
    completed_process_tree = run_project_git(  # 当前不透明测试树查询结果。
        path_project, ["rev-parse", "HEAD:tests"]  # 仓库根与不透明树查询参数。
    )

    # Git 对象 ID 使用 ASCII 十六进制。
    return completed_process_tree.stdout.decode("ascii").strip()

# 收据提交必须已进入当前历史，防止绑定未合并或旁支测试。
def test_commit_is_ancestor(path_project: Path, str_test_commit_sha: str) -> bool:
    """判断 TESTER 提交是否为当前 HEAD 祖先。

    参数：path_project 为仓库根，str_test_commit_sha 为收据提交。
    返回：提交存在且为 HEAD 祖先时为 True。
    """

    # merge-base --is-ancestor 以退出码表达拓扑结论且不输出路径。
    completed_process_ancestor = subprocess.run(  # TESTER 提交拓扑检查。
        ["git", "merge-base", "--is-ancestor", str_test_commit_sha, "HEAD"],  # 拓扑查询参数。
        cwd=path_project,  # 祖先关系判定所在仓库。
        check=False,  # 退出码直接表示祖先关系。
        capture_output=True,  # 禁止诊断意外写入终端。
    )

    # 只有精确成功状态可作为发布证据。
    return completed_process_ancestor.returncode == 0

# 项目级入口集中路径解析、Git 绑定、freshness 和脱敏结果。
def validate_project_test_evidence(
    path_project: Path,
    str_receipt_raw: str,
    int_freshness_seconds: int = DEFAULT_FRESHNESS_SECONDS,
    bool_required: bool = False,
) -> dict[str, Any]:
    """验证项目当前状态与不透明远程测试收据。

    参数：path_project 为仓库根，str_receipt_raw 为绝对或项目相对收据路径。
    参数：int_freshness_seconds 为最大证据年龄。
    参数：bool_required 表示当前调用是否属于必须提供收据的发布态。
    返回：包含 enabled、ok、errors 和脱敏 summary 的结果。
    """

    # 未提供参数表示兼容开发态，不制造发布证据结论。
    if not str_receipt_raw:

        # 发布态不能把缺失收据降级为开发态跳过。
        if bool_required:

            # 固定错误码供 prepare、gate 和 package 统一 fail closed。
            return {
                "enabled": True,
                "ok": False,
                "errors": [
                    evidence_error("TEST_EVIDENCE_REQUIRED", "test evidence receipt is required")
                ],
                "summary": {},
            }

        # enabled 明确区分兼容跳过与验证通过。
        return {"enabled": False, "ok": True, "errors": [], "summary": {}}

    # 相对收据路径始终锚定项目根，避免启动目录漂移。
    path_receipt_input = Path(str_receipt_raw)  # 原始收据路径对象。

    # 规范化路径供存在性检查和 UTF-8 读取共同使用。
    path_receipt = (  # 规范化收据绝对路径。
        path_receipt_input  # 调用方已提供的绝对路径。
        if path_receipt_input.is_absolute()  # 绝对输入不再改变基准。
        else path_project / path_receipt_input  # 相对输入锚定项目根。
    ).resolve()

    # 缺失或非文件收据立即 fail closed。
    if not path_receipt.is_file():

        # 不回显本机绝对路径。
        return {
            "enabled": True,
            "ok": False,
            "errors": [evidence_error("TEST_EVIDENCE_MISSING", "test evidence receipt is unavailable")],
            "summary": {},
        }

    # JSON、Git 或文件清单错误统一转为稳定门禁诊断。
    try:

        # 收据必须是 UTF-8 JSON 对象。
        object_receipt = json.loads(path_receipt.read_text(encoding="utf-8"))  # 原始收据载荷。

        # 当前两个哈希事实分别绑定不透明 tests 树和非测试源码。
        str_tests_tree_hash = tests_tree_hash(path_project)  # 当前提交的不透明测试树哈希。

        # 非测试源码摘要排除收据、运行态与治理历史。
        str_source_manifest_hash = source_manifest_sha256(path_project)  # 当前非测试源码摘要。

    # 解析失败和 Git/文件竞态都不得继续发布。
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError) as exception_error:

        # 只公开错误类别，不公开测试或本地路径。
        return {
            "enabled": True,
            "ok": False,
            "errors": [evidence_error("TEST_EVIDENCE_UNAVAILABLE", type(exception_error).__name__)],
            "summary": {},
        }

    # payload 验证器负责 schema、自哈希、树绑定和三阶段 freshness。
    dict_result = validate_test_evidence_payload(  # 收据结构、绑定与新鲜度结果。
        object_receipt,  # 已解析的原始收据载荷。
        str_expected_tests_tree_hash=str_tests_tree_hash,  # 当前不透明测试树绑定。
        str_expected_source_manifest_hash=str_source_manifest_hash,  # 当前非测试源码绑定。
        str_now_utc=datetime.now(timezone.utc).isoformat(),  # 本轮新鲜度基准。
        int_freshness_seconds=int_freshness_seconds,  # 最大允许证据年龄。
    )

    # 非对象载荷无法读取提交字段，payload 结果已经包含 schema 错误。
    if isinstance(object_receipt, dict) and not test_commit_is_ancestor(
        path_project,
        str(object_receipt.get("test_commit_sha", "")),
    ):

        # 拓扑错误不回显提交 SHA。
        dict_result["errors"].append(
            evidence_error("TEST_EVIDENCE_COMMIT", "test evidence commit is not an ancestor of HEAD")
        )

        # 祖先关系失败覆盖 payload 其余字段可能形成的成功结论。
        dict_result["ok"] = False  # 当前项目测试证据最终失败状态。

    # enabled 明确声明本轮执行了发布态验证。
    return {"enabled": True, **dict_result}
