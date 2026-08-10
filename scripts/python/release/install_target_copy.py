"""解析安装目标并执行可回滚的技能复制。"""

# 标准库提供 JSON 错误输出、文件复制、时间戳和类型注解。
from datetime import datetime
import json
from pathlib import Path
import shutil
from typing import Any, NoReturn

# 发布清单模块提供 Codex 主目录解析合同。
from install_release_manifest import (
    default_codex_home,
    fail_json,
    file_manifest,
    skill_name_error,
    validate_release_completeness,
)
from install_repository_validation import validate_receipt_file_manifest

# 目标解析器把 CLI 选项转换为最终技能目录。
def target_path(
    str_skill_name: str,
    str_target: str,
    str_codex_home: str | None,
    str_custom_root: str | None,
) -> Path | None:
    """解析安装目标目录。

    参数：str_skill_name 为技能名，str_target 为目标类型。
    参数：str_codex_home 和 str_custom_root 为可选根目录覆盖值。
    返回：skip 时返回 None，其他合法目标返回技能目录。
    异常：custom 缺少根目录或目标类型非法时抛出 SystemExit。
    """

    # 所有目标类型都必须先验证最终目录叶节点。
    str_skill_name_error = skill_name_error(str_skill_name)  # 安装目标名称诊断。

    # 直接调用目标解析器时也不能绕过路径边界校验。
    if str_skill_name_error:

        # 复用安装 CLI 的结构化失败协议。
        fail_json(str_skill_name_error)

    # skip 仅验证发布包，不执行本地文件复制。
    if str_target == "skip":

        # 空目标明确表示调用方不得进入复制阶段。
        return None

    # codex 目标位于解析后的 Codex 主目录 skills 子目录。
    if str_target == "codex":

        # 技能名作为安装目录叶节点，避免覆盖整个 skills 根目录。
        return default_codex_home(str_codex_home) / "skills" / str_skill_name

    # custom 目标要求调用方显式提供自定义根目录。
    if str_target == "custom":

        # 缺少根目录时拒绝推测写入位置。
        if not str_custom_root:

            # JSON 错误载荷保持安装 CLI 的机器可读协议。
            raise SystemExit(json.dumps({"errors": ["--custom-root is required when --target custom"]}, indent=2))

        # 展开用户目录并解析绝对位置后再拼接技能名。
        return Path(str_custom_root).expanduser().resolve() / str_skill_name

    # 其他目标类型均不在公开安装合同内。
    raise SystemExit(json.dumps({"errors": ["--target must be skip, codex, or custom"]}, indent=2))

# 时间戳助手为备份目录提供可排序名称。
def stamp() -> str:
    """返回当前本地时间的备份名称片段。

    参数：无。
    返回：适合目录名称的秒级本地时间字符串。
    """

    # 秒级时间戳兼顾可读性和常规安装唯一性。
    return datetime.now().strftime("%Y%m%d-%H%M%S")

# 备份根与 skills 目录保持同一 Codex 主目录边界。
def backup_root_for(path_destination: Path) -> Path:
    """返回目标技能对应的统一备份根目录。

    参数：path_destination 为最终技能安装目录。
    返回：与 skills 同属一个 Codex 主目录的备份根。
    """

    # destination 形如 <home>/skills/<skill>，向上两级回到 home。
    return path_destination.parent.parent / "skill_backups"

# 唯一路径助手避免同一秒内多次替换相互覆盖。
def unique_backup_path(path_destination: Path) -> Path:
    """返回尚不存在的目标技能备份目录。

    参数：path_destination 为最终技能安装目录。
    返回：包含技能名、时间戳和可选序号的空闲路径。
    """

    # 基础名称组合技能名和当前时间戳。
    path_base = backup_root_for(path_destination) / f"{path_destination.name}-{stamp()}"  # 首选备份目录。

    # 首次候选直接使用基础名称。
    path_candidate = path_base  # 当前待检查的备份目录。

    # 后续重名候选从序号 2 开始递增。
    int_suffix = 2  # 下一个备份目录序号。

    # 已存在时持续寻找首个可用的带序号名称。
    while path_candidate.exists() or path_candidate.is_symlink():

        # 当前序号必须与随后递增的变量一致，避免未定义名称。
        path_candidate = Path(f"{path_base}-{int_suffix}")  # 新的备份目录候选。

        # 下一轮使用更大的序号。
        int_suffix += 1  # 下一候选序号。

    # 不存在的候选可安全交给移动操作。
    return path_candidate

# 同级临时目录保证最终切换保持在同一文件系统内。
def unique_sibling_path(path_destination: Path, str_role: str) -> Path:
    """返回目标目录同级的唯一事务路径。

    参数：path_destination 为最终技能安装目录，str_role 为 staging 或 quarantine。
    返回：与最终目录同级且尚不存在的事务路径。
    """

    # 时间戳名称便于故障诊断，序号避免同一秒内冲突。
    path_base = path_destination.parent / f".{path_destination.name}.{str_role}-{stamp()}"  # 首选事务路径。

    # 首轮直接检查未加序号的可读名称。
    path_candidate = path_base  # 当前待检查路径。

    # 后续重名候选从序号 2 开始。
    int_suffix = 2  # 下一个重名序号。

    # 已存在时递增序号，绝不复用未知残留目录。
    while path_candidate.exists() or path_candidate.is_symlink():

        # 同级路径维持原子切换所需的同卷边界。
        path_candidate = Path(f"{path_base}-{int_suffix}")  # 新事务路径候选。

        # 每轮只递增一次，保持候选名称连续。
        int_suffix += 1  # 下一同级事务目录的后缀值。

    # 返回的路径尚不存在，可安全用于本次事务。
    return path_candidate

# 安装副本必须继续满足发布收据和技能引用完整性。
def validate_installed_copy(
    path_candidate: Path,
    *,
    bool_allow_legacy_evolution: bool = False,
) -> dict[str, object]:
    """验证 staging 或最终安装目录的内容完整性。

    参数：path_candidate 为待验证的安装目录。
    参数：bool_allow_legacy_evolution 仅允许已退役 evolution 文件从安装副本缺失。
    返回：包含 ok 布尔值和 errors 字符串列表的验证结果。
    """

    # 诊断顺序与验证阶段保持一致，便于上层直接回显。
    list_errors: list[str] = []  # 安装副本完整性诊断。

    # 安装副本根不能是指向外部目标的符号链接。
    if path_candidate.is_symlink():

        # 根链接拒绝后不再执行目录遍历或收据读取。
        return {
            "ok": False,
            "errors": [f"installed copy must not be a symbolic link: {path_candidate}"],
        }

    # 收据固定放在候选目录根，避免搜索到外部同名文件。
    path_receipt = path_candidate / "RELEASE_RECEIPT.json"  # 固定发布收据位置。

    # 不完整复制不得进入目录切换阶段。
    if not path_candidate.is_dir():

        # 缺少候选目录意味着复制或切换未完成。
        return {"ok": False, "errors": [f"installed copy is missing: {path_candidate}"]}

    # 安装副本不得保留任何可指向目标目录外的符号链接。
    for path_member in sorted(path_candidate.rglob("*")):

        # 链接只记录相对路径，不读取其目标内容。
        if path_member.is_symlink():

            # 统一错误进入安装态最终阻断列表。
            str_relative_path = path_member.relative_to(path_candidate).as_posix()  # 安装链接相对路径。

            # 不允许链接成员进入后续收据和清单验证。
            list_errors.append(f"installed skill contains symbolic link: {str_relative_path}")

    # 收据链接不能被 is_file 或 read_text 跟随到外部目标。
    if path_receipt.is_symlink():

        # 直接返回避免任何收据目标读取。
        return {
            "ok": False,
            "errors": [
                *list_errors,
                f"installed copy RELEASE_RECEIPT.json must not be a symbolic link: {path_receipt}",
            ],
        }

    # 没有正式收据的目录不能证明来自可安装发布包。
    if not path_receipt.is_file():

        # 返回稳定错误合同，不在验证器内终止进程。
        return {
            "ok": False,
            "errors": [
                *list_errors,
                f"installed copy is missing RELEASE_RECEIPT.json: {path_candidate}",
            ],
        }

    # 收据语法或编码错误都属于不可安装内容。
    try:

        # UTF-8 JSON 是发布收据的固定序列化合同。
        dict_receipt = json.loads(path_receipt.read_text(encoding="utf-8"))  # 安装副本收据对象。

    # 读取、编码和语法错误统一折叠为稳定诊断。
    except (OSError, UnicodeError, json.JSONDecodeError):

        # 调用方只需处理结构化失败，无需区分平台异常。
        return {
            "ok": False,
            "errors": [
                *list_errors,
                f"installed copy has invalid RELEASE_RECEIPT.json: {path_candidate}",
            ],
        }

    # 顶层数组或标量不符合发布收据对象合同。
    if not isinstance(dict_receipt, dict):

        # 类型错误与语法错误共享同一公开诊断。
        return {
            "ok": False,
            "errors": [
                *list_errors,
                f"installed copy has invalid RELEASE_RECEIPT.json: {path_candidate}",
            ],
        }

    # 原始 staging 必须与发布收据逐文件完全一致。
    if not bool_allow_legacy_evolution:

        # 复用发布验证器检查路径集合和每个文件哈希。
        validate_receipt_file_manifest(path_candidate, path_receipt, dict_receipt, list_errors)

    # 清理后的安装态只允许固定 evolution 前缀从收据清单中缺失。
    else:

        # 仅对象条目可参与安装态路径和哈希比较。
        list_expected_files = [
            dict(item)  # 复制条目避免修改原收据对象。
            for item in dict_receipt.get("files", [])  # 发布收据声明的完整文件集合。
            if isinstance(item, dict)  # 非对象条目留给清单不匹配诊断。
            and not str(item.get("path", "")).startswith("assets/templates/evolution/")  # 仅放宽固定退役前缀。
        ]  # 去除唯一获准退役前缀后的预期清单。

        # 实际清单仍排除自描述的发布收据文件。
        list_actual_files = file_manifest(  # 清理后安装副本文件清单。
            path_candidate,  # 当前清理后候选目录。
            exclude={"RELEASE_RECEIPT.json"},  # 收据不自我纳入内容清单。
        )

        # 稳定排序后比较完整对象，同时覆盖路径和 SHA-256。
        list_expected_files.sort(key=lambda item: str(item.get("path", "")))

        # 安装态清单也按相同路径键排序。
        list_actual_files.sort(key=lambda item: str(item.get("path", "")))

        # 除固定退役前缀外的任何差异都必须阻断安装。
        if list_actual_files != list_expected_files:

            # 使用既有稳定诊断，避免泄漏文件内容。
            list_errors.append("release receipt file manifest does not match installed copy contents")

    # 技能声明引用检查补充文件哈希清单无法表达的资源合同。
    list_errors.extend(validate_release_completeness(path_candidate, dict_receipt))

    # 空诊断列表是候选副本完整的唯一成功条件。
    return {"ok": not list_errors, "errors": list_errors}

# 失败副本必须离开正式名称并保留为可审计现场。
def quarantine_failed_copy(path_failed_copy: Path, path_destination: Path) -> Path | None:
    """把本次失败副本移动到唯一隔离目录。

    参数：path_failed_copy 为 staging 或已经换入正式名称的新副本。
    参数：path_destination 为最终技能目录，用于确定同级隔离路径。
    返回：失败副本不存在时返回 None，否则返回保留的隔离目录。
    异常：移动失败时保留原路径并向上抛出文件系统异常。
    """

    # 尚未产生副本时不创建空隔离目录。
    if not path_failed_copy.exists() and not path_failed_copy.is_symlink():

        # 空返回值明确表示本轮没有可保留的失败副本。
        return None

    # 隔离目录与正式目标同级，避免跨卷复制破坏失败现场。
    path_quarantine = unique_sibling_path(path_destination, "quarantine")  # 本次失败副本的保留位置。

    # 移动成功后原路径必须释放，才能恢复正式目标名称。
    shutil.move(str(path_failed_copy), str(path_quarantine))

    # 返回路径供异常诊断和人工恢复使用。
    return path_quarantine

# 旧安装从保留备份复制恢复，并再次验证安装态完整性。
def restore_previous_copy(path_backup: Path, path_destination: Path) -> None:
    """从保留备份恢复旧安装并验证恢复结果。

    参数：path_backup 为切换前旧安装的保留目录。
    参数：path_destination 为需要恢复的正式技能目录。
    返回：无业务返回值；成功表示正式目标已恢复且验证通过。
    异常：目标冲突、复制失败或恢复副本验证失败时抛出 RuntimeError。
    """

    # 恢复前正式名称必须为空，禁止覆盖不明副本。
    if path_destination.exists() or path_destination.is_symlink():

        # 同时存在目标和备份时保留现场，等待人工判定所有权。
        raise RuntimeError("> ERR: [Python] recovery target still exists while backup is preserved")

    # 备份根链接不能在恢复时被 copytree 跟随。
    if path_backup.is_symlink():

        # 保留备份现场并阻断恢复复制。
        raise RuntimeError("> ERR: [Python] recovery backup must not be a symbolic link")

    # 使用复制而非移动，确保恢复成功后 backup 仍可审计和手工回退。
    shutil.copytree(path_backup, path_destination, symlinks=True)

    # 恢复副本必须满足与安装后副本相同的收据和哈希合同。
    dict_recovery_validation = validate_installed_copy(  # 恢复后的安装态验证结果。
        path_destination,  # 已从备份复制回正式名称的旧安装。
        bool_allow_legacy_evolution=True,  # 旧安装沿用唯一退役路径兼容合同。
    )

    # 无法证明完整的恢复副本不能标记为回滚成功。
    if not bool(dict_recovery_validation.get("ok", False)):

        # 恢复失败诊断保留具体校验原因，不删除 backup 或目标现场。
        raise RuntimeError(
            "> ERR: [Python] recovered installation validation failed: "
            + "; ".join(str(item) for item in dict_recovery_validation.get("errors", []))
        )

# staging 构建器在触碰旧安装前完成复制、原始校验和唯一兼容转换。
def prepare_staging_copy(path_skill_dir: Path, path_staging: Path) -> None:
    """构建并验证可进入原子切换阶段的安装副本。

    参数：path_skill_dir 为发布包技能目录，path_staging 为同级临时副本目录。
    返回：无业务返回值；成功表示 staging 已满足安装态合同。
    异常：复制、清理或任一阶段验证失败时向上抛出异常。
    """

    # 发布包根链接不能被 copytree 当作源目录跟随。
    if path_skill_dir.is_symlink():

        # 在 staging 创建前拒绝外部根目录内容。
        raise RuntimeError("> ERR: [Python] release source root must not be a symbolic link")

    # 缓存、字节码和版本库元数据不属于技能安装内容。
    func_ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".git")  # 复制排除规则。

    # 复制失败只会污染 staging；链接保持原形等待安装态拒绝。
    shutil.copytree(path_skill_dir, path_staging, ignore=func_ignore, symlinks=True)

    # 原始 staging 先证明复制过程完整，兼容清理不得掩盖源损坏。
    dict_validation = validate_installed_copy(path_staging)  # 清理前验证结果。

    # 不完整的新副本不得进入任何内容转换步骤。
    if not bool(dict_validation.get("ok", False)):

        # 前缀满足统一 Python 错误输出合同。
        raise RuntimeError(
            "> ERR: [Python] staging validation failed: "
            + "; ".join(str(item) for item in dict_validation.get("errors", []))
        )

    # 历史 evolution 模板是安装态唯一获准移除的退役内容。
    path_legacy_evolution = path_staging / "assets" / "templates" / "evolution"  # staging 内旧模板目录。

    # 只清理 staging 内的已退出内容，不触碰发布源目录。
    if path_legacy_evolution.exists():

        # 清理异常必须进入事务恢复，不能被忽略后继续换入副本。
        shutil.rmtree(path_legacy_evolution)

    # 清理后的 staging 必须满足精确的安装态转换合同。
    dict_validation = validate_installed_copy(  # 切换前安装态验证结果。
        path_staging,  # 旧安装切换前的清理后副本。
        bool_allow_legacy_evolution=True,  # 启用唯一获准的退役路径转换。
    )

    # 不完整的新副本不得触发旧安装备份或最终切换。
    if not bool(dict_validation.get("ok", False)):

        # 转换后失败明确标识 staging 安装态验证阶段。
        raise RuntimeError(
            "> ERR: [Python] staging validation failed: "
            + "; ".join(str(item) for item in dict_validation.get("errors", []))
        )

# 安装失败处理器隔离失败副本并恢复事务开始前的可见状态。
def raise_install_failure(
    path_destination: Path,
    path_staging: Path,
    path_backup: Path | None,
    bool_destination_existed: bool,
    bool_swapped: bool,
    object_install_error: Exception,
) -> NoReturn:
    """执行安装失败恢复并抛出包含现场路径的最终异常。

    参数：path_destination 为正式安装目标目录。
    参数：path_staging 为本轮构建的同级临时副本。
    参数：path_backup 为可选的旧安装备份目录。
    参数：bool_destination_existed 表示事务开始前是否存在旧安装。
    参数：bool_swapped 表示新副本是否已经换入正式名称。
    参数：object_install_error 为触发回滚的原始安装异常。
    返回：本函数始终抛出 RuntimeError，不返回业务值。
    """

    # 隔离路径只在实际发现失败副本后产生。
    path_quarantine: Path | None = None  # 本次失败副本的可审计隔离位置。

    # 已换入的新副本位于正式名称，否则失败现场仍在 staging。
    path_failed_copy = path_destination if bool_swapped else path_staging  # 本轮需要保留的失败副本。

    # 恢复过程本身必须失败可见，并保留所有 backup/quarantine 现场。
    try:

        # 唯一隔离路径保存复制失败、验证失败或 post-swap 失败的真实副本。
        path_quarantine = quarantine_failed_copy(path_failed_copy, path_destination)  # 可审计失败副本位置。

        # 已移走旧安装时从备份复制恢复，并保留原 backup。
        if path_backup is not None and path_backup.exists():

            # 恢复后重新验证 VERSION、收据和逐文件哈希合同。
            restore_previous_copy(path_backup, path_destination)

        # 替换安装若丢失旧目标且没有备份，不能伪报恢复成功。
        elif bool_destination_existed and not path_destination.exists():

            # 缺少旧目标和备份意味着事务无法恢复到进入前状态。
            raise RuntimeError("> ERR: [Python] previous installation is missing and no backup is available")

        # 首次安装失败后正式目标必须保持不存在。
        elif not bool_destination_existed and path_destination.exists():

            # 未释放正式名称会让失败安装被误认为可用安装。
            raise RuntimeError("> ERR: [Python] failed first installation still occupies the target path")

    # 回滚异常必须与原安装异常同时可见，且不得清理诊断现场。
    except Exception as object_recovery_error:

        # 包含已知现场路径，供上层结构化错误载荷和人工恢复使用。
        raise RuntimeError(
            "> ERR: [Python] installation failed and recovery failed; "
            f"backup={path_backup or ''}; quarantine={path_quarantine or ''}; "
            f"install_error={object_install_error}; recovery_error={object_recovery_error}"
        ) from object_recovery_error

    # 回滚成功仍以非零异常结束，并保留 backup/quarantine 供审计。
    raise RuntimeError(
        "> ERR: [Python] installation failed and the previous state was restored; "
        f"backup={path_backup or ''}; quarantine={path_quarantine or ''}; "
        f"install_error={object_install_error}"
    ) from object_install_error

# 复制入口先验证同级 staging，再原子切换并执行 post 验证。
def copy_skill(path_skill_dir: Path, path_destination: Path, bool_replace: bool) -> dict[str, Any]:
    """复制技能目录，并在替换时保留旧版本备份。

    参数：path_skill_dir 为发布包技能目录，path_destination 为安装目录。
    参数：bool_replace 控制已存在目标是否允许替换。
    返回：包含可选备份目录字符串的安装结果。
    异常：目标已存在且禁止替换时抛出 FileExistsError。
    """

    # 默认无旧安装，因此结果中的备份路径为空。
    path_backup: Path | None = None  # 实际生成的旧安装备份目录。

    # staging 与最终目标同级，以保证移动不跨卷。
    path_staging = unique_sibling_path(path_destination, "staging")  # 切换前完整副本。

    # 事务开始时的目标状态决定首次安装与替换安装的恢复合同。
    bool_destination_existed = path_destination.exists() or path_destination.is_symlink()  # 本轮开始前是否存在旧安装。

    # 该标志区分原有目标与本事务已经换入的新副本。
    bool_swapped = False  # 最终目录是否已由本事务的新副本占据。

    # 已存在目标必须按 replace 合同决定拒绝或备份。
    if bool_destination_existed:

        # 未授权替换时不得移动或覆盖用户现有安装。
        if not bool_replace:

            # 明确回显冲突目标，供上层转为结构化错误。
            raise FileExistsError(f"> ERR: [Python] target already exists: {path_destination}")

    # 安装目标的父目录必须先存在。
    path_destination.parent.mkdir(parents=True, exist_ok=True)

    # 任一阶段失败都进入同一回滚与临时目录清理边界。
    try:

        # staging 在旧安装移动前完成两阶段校验和受控内容转换。
        prepare_staging_copy(path_skill_dir, path_staging)

        # 只有完整新副本就绪后才备份旧安装。
        if bool_destination_existed:

            # 唯一备份路径保留本次切换前的可恢复版本。
            path_backup = unique_backup_path(path_destination)  # 本次旧安装备份目录。

            # 备份根可能尚未创建。
            path_backup.parent.mkdir(parents=True, exist_ok=True)

            # 移走旧目标后，最终目录才能接收 staging。
            shutil.move(str(path_destination), str(path_backup))

        # staging 与最终目录同级，移动不跨文件系统。
        shutil.move(str(path_staging), str(path_destination))

        # 从此处开始，异常处理可安全识别最终目录为新副本。
        bool_swapped = True  # 新副本已占据最终目标。

        # 最终路径验证覆盖切换异常和目标路径上的内容损坏。
        dict_final_validation = validate_installed_copy(  # 切换后安装态验证结果。
            path_destination,  # 已换入最终名称的安装副本。
            bool_allow_legacy_evolution=True,  # 最终副本沿用同一转换合同。
        )

        # post 验证失败必须隔离新副本并恢复旧版本或空目标状态。
        if not bool(dict_final_validation.get("ok", False)):

            # 失败进入下方统一回滚边界。
            raise RuntimeError(
                "> ERR: [Python] post-swap validation failed: "
                + "; ".join(str(item) for item in dict_final_validation.get("errors", []))
            )

    # 复制、验证或移动异常都必须恢复进入事务前的可见状态。
    except Exception as object_install_error:

        # 统一失败处理器保留现场、恢复旧状态并重新抛出结构化异常。
        raise_install_failure(
            path_destination,
            path_staging,
            path_backup,
            bool_destination_existed,
            bool_swapped,
            object_install_error,
        )

    # 空字符串维持既有机器可读结果合同。
    return {"backup_path": str(path_backup) if path_backup else ""}
