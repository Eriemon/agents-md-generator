"""校验项目路径、Git 历史、新鲜度和摘要绑定。"""

# 标准库提供本职责的类型、摘要和时间处理能力。
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

# 项目证据函数由本模块开始。
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
    list_relative_bytes: list[bytes] = []  # 尚未排序的非空仓库相对路径。

    # 逐项删除终止符产生的空成员，保留 Git 原始路径字节。
    for bytes_relative in completed_process_paths.stdout.split(b"\0"):

        # 空成员不是候选文件，不能进入后续文件读取循环。
        if bytes_relative:

            # 只收集 Git 已返回的非空相对路径。
            list_relative_bytes.append(bytes_relative)

    # 按原始路径字节排序，保证清单摘要确定性。
    list_relative_bytes = sorted(list_relative_bytes)  # 稳定源码路径集合。

    # 整体摘要逐成员吸收无歧义的 NUL 分隔事实。
    hash_manifest = hashlib.sha256()  # 非测试源码清单聚合摘要。

    # 每个候选只在 Git 完成排除后才读取内容。
    for bytes_relative in list_relative_bytes:

        # Git -z 路径使用 UTF-8；surrogateescape 保留异常字节的可逆语义。
        str_relative = bytes_relative.decode("utf-8", errors="surrogateescape")  # 当前仓库相对路径。

        # Git pathspec 在不同调用上下文下可能返回已排除的历史候选。
        bool_path_excluded: bool = any(  # 当前路径是否命中既有清单排除规则。
            str_pathspec.startswith(":(exclude,glob)")  # 仅解释 Git 排除 pathspec。
            and fnmatchcase(  # 用同一 glob 语义复核候选路径。
                str_relative,  # 参与 glob 匹配的当前候选路径。
                str_pathspec.removeprefix(":(exclude,glob)"),  # 去除 Git pathspec 前缀。
            )  # 当前候选是否命中该排除模式。
            for str_pathspec in SOURCE_MANIFEST_EXCLUDES  # 遍历已批准的排除规则。
        )  # 排除判定沿用同一份发布清单合同。

        # 已被清单排除的候选不进入发布源码读取流程。
        if bool_path_excluded:

            # 继续检查剩余 Git 候选，避免历史或运行态缺失项阻断当前清单。
            continue

        # 路径锚定仓库根，未排除候选不存在时让调用方 fail closed。
        path_source = path_project / str_relative  # 当前非测试源码文件。

        # Git 候选不能通过符号链接把外部文件伪装成源码成员。
        if path_source.is_symlink() or not path_source.is_file():

            # Git 候选与工作树不一致或含链接时不能签发稳定收据。
            raise RuntimeError(
                "> ERR: [Python] source manifest candidate is not a regular file or is a symbolic link"
            )

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

# immutable-history 仍使用 Git tree id；活动 v2 对其做 SHA-256 包装。
def tests_tree_git_id(path_project: Path) -> str:
    """读取 HEAD 中不透明 tests 树 Git tree id。

    参数：path_project 为 Git 仓库根。
    返回：HEAD:tests 的 Git tree id。
    """

    # rev-parse 只返回树对象身份，不枚举测试路径或内容。
    completed_process_tree = run_project_git(  # 当前不透明测试树查询结果。
        path_project, ["rev-parse", "HEAD:tests"]  # 仓库根与不透明树查询参数。
    )

    # Git 对象 ID 使用 ASCII 十六进制。
    return completed_process_tree.stdout.decode("ascii").strip()

# 活动 v2 使用不透明 tests tree 的 SHA-256 包装作为绑定摘要。
def tests_tree_hash(path_project: Path) -> str:
    """返回活动 pytest v2 使用的 64 字符 tests 树摘要。

    参数：path_project 为 Git 仓库根。
    返回：Git tree id 的 SHA-256 摘要；不枚举 tests 成员。
    """

    # 对不透明 Git tree id 做 SHA-256 包装，满足 v2 字段长度且不泄漏成员。
    str_tree_id = tests_tree_git_id(path_project)  # 当前 HEAD 的不透明 tests tree id。

    # 返回固定长度摘要供活动发布合同绑定。
    return hashlib.sha256(str_tree_id.encode("ascii")).hexdigest()

# 历史 local-test-evidence 使用当前工作树，避免未提交 tests 漂移复用 HEAD 摘要。
def local_tests_tree_hash(path_project: Path) -> str:
    """计算当前本地 tests 工作树的确定性摘要。

    参数：path_project 为 Git 仓库根。
    返回：当前 tests 文件路径、原始内容摘要和字节数的聚合 SHA-256。
    异常：Git 查询失败、越界链接或候选不是普通文件时抛出 RuntimeError。
    """

    # Git 路径查询同时纳入已跟踪和未忽略的新增 tests 文件。
    completed_process_paths = run_project_git(  # 当前本地测试候选路径查询。
        path_project,  # 固定项目根，避免查询结果跨越工作目录。
        [
            "ls-files",  # 让 Git 返回待绑定的 tests 路径集合。
            "--cached",  # 覆盖索引中已经跟踪的测试文件。
            "--others",  # 发现尚未纳入索引的新增测试文件。
            "--exclude-standard",  # 排除忽略规则屏蔽的运行产物。
            "-z",  # 保留特殊文件名的无歧义分隔。
            "--",  # 结束 Git 选项，避免路径被重新解释。
            "tests",  # 将绑定范围限制为 tests 树。
        ],
    )

    # 先建立可排序的原始路径集合，终止 NUL 不代表测试文件。
    list_relative_bytes: list[bytes] = []  # 当前 tests 工作树的路径字节集合。

    # 逐项保留 Git 返回的非空路径，避免把协议终止符算入摘要。
    for bytes_relative in completed_process_paths.stdout.split(b"\0"):

        # 空成员只表示 NUL 结束，不对应任何测试文件。
        if bytes_relative:

            # 保留 Git 原始路径字节，稍后按字节序生成确定性顺序。
            list_relative_bytes.append(bytes_relative)

    # 路径顺序固定后，内容修改才能稳定改变聚合摘要。
    list_relative_bytes = sorted(list_relative_bytes)  # 当前 tests 的确定性路径顺序。

    # 工作树测试摘要只存储聚合值，不把测试成员写入发布收据。
    hash_tests_tree = hashlib.sha256()  # 当前 tests 工作树聚合摘要。

    # 后续链接边界判断统一锚定规范化项目根。
    path_project_root = path_project.resolve()  # 本地项目边界。

    # 每个普通测试文件按路径、内容摘要和字节数吸收确定性事实。
    for bytes_relative in list_relative_bytes:

        # Git 原始路径字节用 surrogateescape 保持可逆本地文件名语义。
        str_relative = bytes_relative.decode("utf-8", errors="surrogateescape")  # 当前测试相对路径。

        # 将相对路径锚定到项目根，避免启动目录改变绑定对象。
        path_test = path_project / str_relative  # 当前工作树测试文件。

        # 解析链接后再次确认候选仍属于本地项目边界。
        path_test_resolved = path_test.resolve()  # 解析后的当前测试路径。

        # 链接不能把本地证据绑定到项目外或不稳定的外部文件。
        try:

            # 解析后的路径必须仍位于当前项目根内。
            path_test_resolved.relative_to(path_project_root)

        # 越界链接不能参与本地测试证据计算。
        except ValueError as exception_error:

            # 只抛出固定诊断，避免回显外部路径。
            raise RuntimeError("> ERR: [Python] local tests candidate is outside the project") from exception_error

        # 只允许项目内普通文件进入本地测试摘要。
        if path_test.is_symlink() or not path_test.is_file():

            # 非普通文件无法提供稳定的当前测试字节。
            raise RuntimeError("> ERR: [Python] local tests candidate is not a regular file")

        # 原始字节同时绑定内容和精确文件规模。
        bytes_test = path_test.read_bytes()  # 当前测试原始字节。

        # 单文件内容摘要避免只依赖文件名或元数据。
        str_test_sha256 = hashlib.sha256(bytes_test).hexdigest()  # 当前测试内容摘要。

        # 路径、内容摘要和字节数共同消除拼接歧义。
        bytes_test_record = b"\0".join(  # 当前测试文件无歧义清单记录。
            (
                bytes_relative,  # Git 返回的仓库相对路径。
                str_test_sha256.encode("ascii"),  # 当前文件的内容摘要。
                str(len(bytes_test)).encode("ascii"),  # 当前文件的原始字节数。
            )
        ) + b"\n"

        # 按稳定路径顺序吸收当前测试文件事实。
        hash_tests_tree.update(bytes_test_record)  # 吸收稳定排序后的当前测试事实。

    # 返回固定长度聚合摘要，收据只保存这一不透明值。
    return hash_tests_tree.hexdigest()

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

# 项目级失败结果保持 enabled/summary 机器协议一致。
def _project_evidence_failure(str_error_code: str, str_message: str) -> dict[str, Any]:
    """构造不回显路径和敏感值的项目级失败结果。

    参数：str_error_code 为稳定错误码，str_message 为脱敏诊断文本。
    返回：enabled=True 且 ok=False 的项目证据结果。
    """

    # 项目入口已经进入发布态验证，因此失败结果必须保持 enabled=True。
    return {
        "enabled": True,
        "ok": False,
        "errors": [evidence_error(str_error_code, str_message)],
        "summary": {},
    }

# 相对路径锚定项目根，并拒绝解析后越界的符号链接。
def _resolve_project_receipt_path(
    path_project: Path,
    str_receipt_raw: str,
) -> tuple[Path, bool]:
    """解析项目证据路径并返回越界标记。

    参数：path_project 为仓库根，str_receipt_raw 为收据相对或绝对路径。
    返回：规范化路径和是否越出项目根的布尔标记。
    """

    # 项目根只解析一次，后续边界判断统一使用同一事实。
    path_project_root: Path = path_project.resolve()  # 规范化后的项目边界。

    # 相对输入必须以项目根为基准，避免启动目录影响发布结果。
    path_receipt_input: Path = Path(str_receipt_raw)  # 调用方提供的原始收据路径。

    # 解析符号链接后再进行边界判断，防止通过链接绕过目录约束。
    path_receipt: Path = (  # 解析后的收据绝对路径。
        path_receipt_input if path_receipt_input.is_absolute() else path_project_root / path_receipt_input  # 绝对输入或项目根相对输入。
    ).resolve()

    # 项目根内路径可继续做文件存在性和 JSON 校验。
    try:

        # relative_to 只验证解析后路径，不读取外部文件。
        path_receipt.relative_to(path_project_root)

    # 越界路径统一转成脱敏布尔标记。
    except ValueError:

        # 返回项目根占位路径，调用方只使用越界标记而不读取它。
        return path_project_root, True

    # 规范化收据路径通过项目边界检查。
    return path_receipt, False

# 收据读取单独封装，使项目入口只处理可预期的输入异常。
def _read_project_receipt(path_receipt: Path) -> Any:
    """读取 UTF-8 JSON 收据而不改变原始载荷。

    参数：path_receipt 为已通过项目边界检查的收据路径。
    返回：JSON 解码后的任意载荷；对象形状由后续合同验证。
    """

    # 保留 JSON 原始类型，供调用方统一执行对象形状门禁。
    return json.loads(path_receipt.read_text(encoding="utf-8"))

# 根据收据类型选择活动摘要或 immutable-history 的旧 Git tree id。
def _project_evidence_hashes(
    path_project: Path,
    dict_receipt: dict[str, Any],
    bool_immutable_history: bool,
) -> tuple[str, str]:
    """计算项目级测试树和非测试源码摘要。

    参数：path_project 为仓库根，dict_receipt 为对象收据。
    参数：bool_immutable_history 表示是否允许旧历史收据。
    返回：期望的 tests 树摘要和当前源码清单摘要。
    """

    # local 收据必须绑定当前工作树中的 tests 文件事实。
    if dict_receipt.get("kind") == LOCAL_EVIDENCE_KIND:

        # 未提交修改和新增测试必须改变本地发布摘要。
        str_expected_tests_tree_hash: str = local_tests_tree_hash(path_project)  # 当前 local tests 工作树摘要。

    # 活动 pytest 也必须绑定实际执行时的当前 tests 工作树。
    else:

        # 本轮远程执行必须绑定上传时可见的 tests 文件事实。
        str_expected_tests_tree_hash = local_tests_tree_hash(path_project)  # 上传清单决定本轮可复核测试边界。

    # 只有没有 runner 的旧收据才切换到 Git tree id 兼容语义。
    if (
        bool_immutable_history
        and dict_receipt.get("kind") != LOCAL_EVIDENCE_KIND
        and "runner" not in dict_receipt
    ):

        # 历史路径必须继续绑定不可枚举的 HEAD:tests tree 对象。
        str_expected_tests_tree_hash = tests_tree_git_id(path_project)  # 旧历史合同使用 HEAD:tests tree id。

    # 源码摘要排除收据、治理、运行态和图谱等自引用路径。
    str_source_manifest_hash: str = source_manifest_sha256(path_project)  # 当前非测试源码摘要。

    # 两个摘要分别绑定测试树和非测试源码状态。
    return str_expected_tests_tree_hash, str_source_manifest_hash

# 项目级提交字段按 local、pytest v2、历史 schema 分流。
def _project_commit_field(dict_receipt: dict[str, Any]) -> str:
    """返回当前收据使用的提交字段名。

    参数：dict_receipt 为已经确认是对象的收据。
    返回：local、pytest v2 或历史收据对应的提交字段名。
    """

    # 历史 local-test-evidence 使用完整 test_commit_sha 绑定 TESTER 来源。
    if dict_receipt.get("kind") == LOCAL_EVIDENCE_KIND:

        # 历史本地合同不接受 pytest v2 的短提交字段。
        return "test_commit_sha"

    # 活动 pytest v2 收据使用 test_commit 字段。
    if "runner" in dict_receipt:

        # v2 提交字段的拓扑检查在项目入口统一执行。
        return "test_commit"

    # immutable-history 旧收据保留原始提交字段名称。
    return "test_commit_sha"

# 读取并绑定项目测试收据上下文。
def _read_project_evidence_context(
    path_project: Path,
    str_receipt_raw: str,
    bool_immutable_history: bool,
) -> tuple[dict[str, Any] | None, tuple[str, str] | None, dict[str, Any] | None]:
    """解析项目收据并计算当前测试与源码摘要。

    参数:
        path_project: 当前项目根目录。
        str_receipt_raw: 项目内收据路径。
        bool_immutable_history: 是否允许旧历史收据合同。

    返回:
        tuple: 收据对象、期望摘要和失败结果；失败时前两项为空。
    """

    # 相对路径解析和项目边界检查先于文件读取。
    tuple_receipt_resolution: tuple[Path, bool] = _resolve_project_receipt_path(  # 收据路径解析结果。
        path_project,  # 项目根目录。
        str_receipt_raw,  # 外部输入的收据路径只在项目根内生效。
    )

    # 拆出规范化路径和项目越界结论供后续门禁使用。
    path_receipt: Path = tuple_receipt_resolution[0]  # 通过解析后的收据路径。

    # 越界标记决定是否可以继续访问规范化路径。
    bool_receipt_outside: bool = tuple_receipt_resolution[1]  # 收据是否越出项目根。

    # 越界路径不回显绝对值，避免路径泄漏和证据旁路。
    if bool_receipt_outside:

        # 稳定错误码足以定位发布配置问题。
        return None, None, _project_evidence_failure(
            "TEST_EVIDENCE_PATH", "test evidence receipt is outside the project"
        )

    # 缺失或非文件收据立即 fail closed。
    if not path_receipt.is_file():

        # 收据缺失时也不回显本机绝对路径。
        return None, None, _project_evidence_failure(
            "TEST_EVIDENCE_MISSING", "test evidence receipt is unavailable"
        )

    # JSON、Git 或文件清单错误统一转为稳定门禁诊断。
    try:

        # 收据原始类型由后续对象门禁统一处理。
        obj_receipt = _read_project_receipt(path_receipt)  # UTF-8 JSON 原始载荷。

        # 非对象收据直接返回结构错误，不计算无意义的仓库绑定。
        if not isinstance(obj_receipt, dict):

            # 发布门禁只接受对象型 local 或 pytest 收据。
            return None, None, _project_evidence_failure(
                "PYTEST_RECEIPT_REQUIRED", "full pytest receipt is required"
            )

        # 活动项目入口先拒绝历史 local 收据，避免走 local tests 工作树摘要路径。
        if obj_receipt.get("kind") == LOCAL_EVIDENCE_KIND and not bool_immutable_history:

            # 本地 unittest 不能替代活动完整 pytest 收据。
            return None, None, _project_evidence_failure(
                "PYTEST_RECEIPT_REQUIRED", "full pytest receipt is required"
            )

        # local/pytest 使用活动摘要，旧收据才使用 Git tree id。
        tuple_expected_hashes: tuple[str, str] = _project_evidence_hashes(  # 当前项目绑定摘要。
            path_project,  # 项目边界和 Git 查询根目录。
            obj_receipt,  # 已通过对象形状检查的收据。
            bool_immutable_history,  # 是否允许旧历史合同。
        )

    # 解析失败和 Git/文件竞态都不得继续发布。
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError) as exception_error:

        # 只公开错误类别，不公开测试或本地路径。
        return None, None, _project_evidence_failure(
            "TEST_EVIDENCE_UNAVAILABLE", type(exception_error).__name__
        )

    # 返回已绑定的收据对象和当前项目摘要。
    return obj_receipt, tuple_expected_hashes, None

# 验证项目测试收据与当前源码状态。
def validate_project_test_evidence(
    path_project: Path,
    str_receipt_raw: str,
    int_freshness_seconds: int | None = None,
    bool_required: bool = False,
    bool_immutable_history: bool = False,
) -> dict[str, Any]:
    """验证项目当前状态与远程或本地测试收据。

    参数：path_project 为仓库根，str_receipt_raw 为绝对或项目相对收据路径。
    参数：int_freshness_seconds 为最大证据年龄。
    参数：bool_required 表示当前调用是否属于必须提供收据的发布态。
    参数：bool_immutable_history 表示是否允许兼容旧 schema=1 历史收据。
    返回：包含 enabled、ok、errors 和脱敏 summary 的结果。
    """

    # 延后解析默认 freshness，避免模块初始化阶段读取尚未完成的 facade 导入。
    if int_freshness_seconds is None:

        # 保持调用方省略参数时仍使用统一的新鲜度合同。
        int_freshness_seconds = DEFAULT_FRESHNESS_SECONDS  # 调用方省略参数时采用统一新鲜度窗口。

    # 未提供收据参数表示兼容开发态，不制造发布证据结论。
    if not str_receipt_raw:

        # 发布态不能把缺失收据降级为开发态跳过。
        if bool_required:

            # 固定错误码供 prepare、gate 和 package 统一 fail closed。
            return _project_evidence_failure("TEST_EVIDENCE_REQUIRED", "test evidence receipt is required")

        # enabled 明确区分兼容跳过与验证通过。
        return {"enabled": False, "ok": True, "errors": [], "summary": {}}

    # 收据解析 helper 统一处理路径、结构和当前摘要绑定。
    tuple_evidence_context = _read_project_evidence_context(  # 当前项目收据上下文。
        path_project,  # 以同一仓库根计算收据边界。
        str_receipt_raw,  # 项目内收据路径。
        bool_immutable_history,  # 旧历史合同开关。
    )

    # 失败结果优先返回，阻断后续 payload 与 Git 复核。
    dict_context_failure = tuple_evidence_context[2]  # 收据上下文失败结果。

    # 上下文失败必须在 payload 复核前停止。
    if dict_context_failure is not None:

        # helper 已生成脱敏 fail-closed 结果。
        return dict_context_failure

    # 成功上下文必须同时包含收据对象和当前摘要。
    dict_receipt = tuple_evidence_context[0]  # 已解析的收据对象。

    # 保存 helper 返回的测试与源码摘要元组。
    tuple_expected_hashes = tuple_evidence_context[1]  # 当前 tests 与源码摘要。

    # 内部上下文缺项时不能继续读取摘要字段。
    if dict_receipt is None or tuple_expected_hashes is None:

        # 防御性分支阻断不完整的内部上下文。
        return _project_evidence_failure(
            "TEST_EVIDENCE_UNAVAILABLE", "test evidence context is incomplete"
        )

    # 解包固定顺序的 tests tree 和源码清单摘要。
    str_expected_tests_tree_hash: str = tuple_expected_hashes[0]  # 当前 tests 树摘要供 payload 绑定。

    # 第二项摘要阻断非测试源码漂移进入发布。
    str_source_manifest_hash: str = tuple_expected_hashes[1]  # 当前源码摘要供 payload 绑定。

    # 活动发布只允许完整 pytest v2；schema-1/local 收据需要显式历史开关。
    if (
        "runner" not in dict_receipt
        and not bool_immutable_history
    ):

        # 不满足活动合同类型时统一报告完整证据缺失。
        return _project_evidence_failure("PYTEST_RECEIPT_REQUIRED", "full pytest receipt is required")

    # payload 验证器负责 local、v2 pytest 或历史 schema 的字段与 freshness 校验。
    dict_result = validate_test_evidence_payload(  # 收据结构、绑定与新鲜度结果。
        dict_receipt,  # 已解析的原始收据载荷。

        # 下面三项绑定当前项目状态和本轮时间事实。
        str_expected_tests_tree_hash=str_expected_tests_tree_hash,  # 当前测试树摘要供合同绑定。
        str_expected_source_manifest_hash=str_source_manifest_hash,  # 源码清单绑定阻断未重测的源码状态。
        str_now_utc=datetime.now(timezone.utc).isoformat(),  # 当前 UTC 供 freshness 比较。

        # 下面三项控制验证窗口、治理复核和历史兼容边界。
        int_freshness_seconds=int_freshness_seconds,  # 当前发布允许的最大证据年龄。
        path_project=path_project,  # 本地合同重新读取项目治理文件。
        bool_immutable_history=bool_immutable_history,  # 仅旧 schema 可使用历史兼容路径。
    )

    # 提交字段绑定当前历史，拒绝未合并或旁支测试结果。
    str_commit_field: str = _project_commit_field(dict_receipt)  # 当前收据提交字段名。

    # 统一转换提交字段值，供 Git 拓扑检查使用。
    str_commit_value: str = str(dict_receipt.get(str_commit_field, ""))  # 收据提交值。

    # 祖先关系失败覆盖 payload 其余字段可能形成的成功结论。
    if not test_commit_is_ancestor(path_project, str_commit_value):

        # 拓扑错误不回显提交 SHA。
        dict_result["errors"].append(
            evidence_error("TEST_EVIDENCE_COMMIT", "test evidence commit is not an ancestor of HEAD")
        )

        # 当前项目测试证据最终失败状态。
        dict_result["ok"] = False  # 祖先关系失败覆盖 payload 成功结论。

    # enabled 明确声明本轮执行了发布态验证。
    return {"enabled": True, **dict_result}

# 依赖导入放在本模块函数定义之后，避免 facade 再导入 helper 时出现部分初始化循环。
try:
    # 导入当前验证职责实际使用的核心合同和错误入口。
    from evidence_validation import (
        DEFAULT_FRESHNESS_SECONDS,
        LOCAL_EVIDENCE_KIND,
        SOURCE_MANIFEST_EXCLUDES,
        evidence_error,
    )

    # 导入跨职责的稳定公共入口。
    from history_receipt_validation import validate_test_evidence_payload

# 包内执行时回退到同一职责目录的相对依赖。
except ImportError:
    # 包内执行时导入同一职责的核心合同和错误入口。
    from .evidence_validation import (
        DEFAULT_FRESHNESS_SECONDS,
        LOCAL_EVIDENCE_KIND,
        SOURCE_MANIFEST_EXCLUDES,
        evidence_error,
    )

    # 导入跨职责的相对公共入口。
    from .history_receipt_validation import validate_test_evidence_payload
