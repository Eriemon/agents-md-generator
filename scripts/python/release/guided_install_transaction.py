"""执行 guided 安装的复制、恢复和 receipt 事务。"""

# 事务模块使用现代注解并避免依赖调用方工作目录。
from __future__ import annotations

# 复制、恢复和 receipt 需要标准库文件系统与 JSON 能力。
import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime

# 路径和结构化载荷类型用于事务边界。
from pathlib import Path
from typing import Any

# 源树清单必须复用发布 runtime 的同一实现。
from install_release_manifest import source_tree_manifest

# 构造 guided 事务的路径状态。
def _transaction_paths(
    path_boundary: Path,
    path_platform_home: Path,
    dict_platform: dict[str, str],
    dict_manifest: dict[str, str],
    str_skill_name: str,
) -> dict[str, Any]:
    """创建 staging、backup、lock、quarantine 和安装父路径。

    参数:
        path_boundary: 本轮安装 containment 根。
        path_platform_home: 已验证的平台根。
        dict_platform: 平台投影记录。
        dict_manifest: guided manifest 映射。
        str_skill_name: Skill 名称。
    返回:
        绑定安装父目录及四个事务路径的对象。
    异常:
        SystemExit: 跨卷或已有锁导致事务无法安全开始。
    """

    # staging 和隔离目录均保持在同一 containment 根内。
    path_staging: Path = path_boundary / (  # 当前事务 staging 路径。
        f"{dict_manifest['STAGING_PREFIX']}{uuid.uuid4().hex}"  # 使用 manifest 前缀隔离本轮副本。
    )

    # 备份根承载被替换的旧安装目录。
    path_backup_root: Path = path_boundary / dict_manifest["BACKUP_DIRECTORY_NAME"]  # 替换旧 Skill 时使用的受管备份根。

    # 锁路径承载当前事务的独占所有权。
    path_lock: Path = path_boundary / dict_manifest["LOCK_FILE_NAME"]  # 事务锁路径。

    # 隔离根承载复制或恢复失败的副本。
    path_quarantine_root: Path = path_boundary / dict_manifest["QUARANTINE_DIRECTORY_NAME"]  # 失败隔离根。

    # 安装父目录由平台根和受管子目录共同决定。
    path_install_parent: Path = (  # 受管技能父目录。
        path_platform_home / dict_platform["skill_install_dir"]  # 仅使用 projection 声明的安装子目录。
    ).resolve()

    # 安装父目录必须是平台根下的一层受管路径。
    if (
        not path_install_parent.is_relative_to(path_boundary)
        or path_install_parent.parent != path_platform_home
    ):

        # 越界父目录不能进入备份或 staging 事务。
        raise SystemExit(
            "> ERR: [Python] installer parent directory is outside the allowed one-level boundary"
        )

    # 备份、staging 和交换动作必须位于同一文件系统。
    int_boundary_device: int = os.stat(path_boundary).st_dev  # containment 根所在设备号。

    # 目标父目录若存在，必须与 containment 根共享设备。
    int_target_device: int = (  # 目标父目录设备号。
        os.stat(path_install_parent).st_dev  # 读取已存在父目录的文件系统设备号。
        if path_install_parent.exists()  # 已存在父目录才需要实际 stat。
        else int_boundary_device  # 缺失父目录沿用 containment 根设备号。
    )

    # 跨卷动作不能保证事务原子性。
    if int_boundary_device != int_target_device:

        # 在复制开始前拒绝不可恢复的事务布局。
        raise SystemExit(
            "> ERR: [Python] installer target crosses a filesystem boundary"
        )

    # 旧锁无论是否陈旧都必须人工核验后清除。
    if path_lock.exists() or path_lock.is_symlink():

        # 并发或残留事务不能被自动覆盖。
        raise SystemExit(
            f"> ERR: [Python] installer transaction lock already exists: {path_lock}"
        )

    # 将同根事务路径集中，避免后续调用拆错锁或隔离边界。
    return {
        "path_install_parent": path_install_parent,  # 受管一层父目录供目标切换。
        "path_staging": path_staging,  # 当前 staging 副本路径。
        "path_backup_root": path_backup_root,  # 替换旧目标的备份根。
        "path_lock": path_lock,  # 当前事务独占锁。
        "path_quarantine_root": path_quarantine_root,  # 失败副本隔离根。
    }

# 创建事务锁文件并写入源身份。
def _acquire_lock(path_lock: Path, str_source_manifest_hash: str) -> None:
    """独占创建 guided 安装锁。

    参数:
        path_lock: 事务锁路径。
        str_source_manifest_hash: 本次源树清单摘要。
    返回:
        无；锁文件创建成功表示已获得事务所有权。
    异常:
        SystemExit: 锁竞争导致无法获得事务所有权。
    """

    # x 模式把检查和创建合并为单个文件系统动作。
    try:

        # 锁内容绑定进程和源身份，便于残留事务核验。
        with path_lock.open("x", encoding="utf-8") as file_lock:

            # 记录最小恢复事实，不写入任何凭据。
            file_lock.write(
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "source_manifest_sha256": str_source_manifest_hash,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )

    # 竞争创建失败时不触碰源和目标。
    except FileExistsError as object_error:

        # 保留锁路径，便于人工审计残留事务。
        raise SystemExit(
            f"> ERR: [Python] installer transaction lock could not be acquired: {path_lock}"
        ) from object_error

# 计算稳定源清单摘要。
def _manifest_hash(list_manifest: list[dict[str, Any]]) -> str:
    """计算源树清单的规范 SHA-256 摘要。

    参数:
        list_manifest: source_tree_manifest 返回的节点列表。
    返回:
        清单规范 JSON 的 SHA-256 十六进制摘要。
    """

    # 清单摘要必须独立于 JSON 空白和字典插入顺序。
    bytes_manifest: bytes = json.dumps(  # 规范化清单字节。
        list_manifest,  # 以节点事实作为摘要输入。
        ensure_ascii=False,  # 保留非 ASCII 相对路径语义。
        sort_keys=True,  # 消除映射键顺序差异。
        separators=(",", ":"),  # 固定 JSON 分隔符，保证跨平台摘要相同。
    ).encode("utf-8")

    # 返回本轮源或副本的身份摘要。
    return hashlib.sha256(bytes_manifest).hexdigest()

# 备份现有目标并验证 staging 副本。
def _copy_to_destination(
    context: dict[str, Any],
) -> dict[str, Any]:
    """完成备份、staging 复制和目标切换。

    参数:
        context: 已绑定源、目标、事务路径和源树清单的复制上下文。
    返回:
        绑定旧目标备份路径、备份状态、staging 摘要和 final 摘要的对象。
    异常:
        Exception: 复制或身份复核失败，由上层恢复事务。
    """

    # 将复制上下文拆成局部事实，保持后续事务分支易读。
    path_source: Path = context["path_source"]  # 版本化 Skill 源目录。

    # 局部目标路径只来自已验证的上下文。
    path_destination: Path = context["path_destination"]  # receipt 写入的最终目标目录。

    # 父目录已经通过一层 containment 检查。
    path_install_parent: Path = context["path_install_parent"]  # containment 校验过的技能父目录。

    # staging 路径由 manifest 前缀和随机标识组成。
    path_staging: Path = context["path_staging"]  # 本轮 staging 副本。

    # 备份根由 manifest 声明并受 boundary 保护。
    path_backup_root: Path = context["path_backup_root"]  # 替换事务的备份根。

    # 技能名已经通过安全叶节点检查。
    str_skill_name: str = context["str_skill_name"]  # 目标路径技能名称。

    # 目标存在状态绑定事务开始时的可见状态。
    bool_destination_exists: bool = context["bool_destination_exists"]  # 是否需要备份旧目标。

    # 源树清单是 staging 和 final 的共同比较基准。
    list_source_manifest: list[dict[str, Any]] = context["list_source_manifest"]  # 比较 staging 与 final 的原始清单。

    # 记录替换事务的旧目标和两次副本摘要。
    path_backup_target: Path | None = None  # 旧目标备份路径。

    # 标记旧目标是否已经移入受控备份根。
    bool_destination_backed_up: bool = False  # 替换前的旧目标转移状态。

    # staging 摘要用于证明复制阶段没有漂移。
    str_staging_manifest_hash: str = ""  # staging 清单身份摘要。

    # final 摘要用于证明正式目标与源树一致。
    str_final_manifest_hash: str = ""  # final 安装副本身份摘要。

    # 已有目标必须先移入受控备份根。
    if bool_destination_exists:

        # 备份目录可以创建，但其父 containment 已经固定。
        path_backup_root.mkdir(parents=True, exist_ok=True)

        # 秒级时间戳只用于人类定位，冲突由后缀解决。
        str_backup_stamp: str = datetime.now().strftime("%Y%m%d-%H%M%S")  # 备份时间戳。

        # 首选备份名同时包含技能名和时间戳。
        path_backup_target = path_backup_root / f"{str_skill_name}-{str_backup_stamp}"  # 首选备份路径。

        # 冲突后缀从 2 开始，避免覆盖同秒备份。
        int_backup_suffix: int = 2  # 冲突备份的起始后缀。

        # 同秒安装不得覆盖已有备份。
        while path_backup_target.exists() or path_backup_target.is_symlink():

            # 逐步增加后缀保持备份路径唯一。
            path_backup_target = path_backup_root / (  # 冲突备份路径。
                f"{str_skill_name}-{str_backup_stamp}-{int_backup_suffix}"  # 递增后缀保持备份唯一。
            )

            # 下一轮循环使用新的冲突后缀。
            int_backup_suffix += 1  # 下一次冲突使用的后缀。

        # 先完成旧目标转移，再建立 staging 副本。
        shutil.move(str(path_destination), str(path_backup_target))

        # 记录旧目标已经脱离正式安装路径。
        bool_destination_backed_up = True  # 旧目标已进入受控备份根。

        # 人类摘要只报告备份已发生，不输出完整目录内容。
        print("> INFO: [Python] Existing destination backed up before staging copy.")

    # 完整复制源目录后才切换正式目标。
    shutil.copytree(path_source, path_staging, symlinks=True)

    # staging 清单必须与复制前源事实完全一致。
    list_staging_manifest: list[dict[str, Any]] = source_tree_manifest(  # 复核 staging 节点类型与字节身份。
        path_staging  # staging 副本的事实根。
    )

    # 计算 staging 清单摘要供源树对账。
    str_staging_manifest_hash = _manifest_hash(list_staging_manifest)  # staging 副本身份摘要。

    # 内容或节点类型漂移都必须停止目标切换。
    if list_staging_manifest != list_source_manifest:

        # 复制输入或文件系统变化时拒绝形成半套安装。
        raise RuntimeError(
            "> ERR: [Python] staging source manifest does not match the source"
        )

    # staging 中不允许出现链接或其他特殊节点。
    if any(
        dict_entry.get("kind") not in {"file", "directory"}
        for dict_entry in list_staging_manifest
    ):

        # 防止复制阶段引入外部对象。
        raise RuntimeError("> ERR: [Python] staging contains unsafe nodes")

    # 只在确认进入事务后创建受管技能父目录。
    if not path_install_parent.exists():

        # 父目录是一层固定边界，不递归创建任意路径。
        path_install_parent.mkdir()

    # staging 原子移动到正式目标完成安装切换。
    shutil.move(str(path_staging), str(path_destination))

    # 切换后再次清单化，证明目标仍与源一致。
    list_final_manifest: list[dict[str, Any]] = source_tree_manifest(  # 复核正式目标的节点类型与字节身份。
        path_destination  # final 安装副本的事实根。
    )

    # 计算 final 清单摘要供正式目标闭环对账。
    str_final_manifest_hash = _manifest_hash(list_final_manifest)  # final 摘要确认正式目标与源清单闭环。

    # final 清单漂移表示安装副本身份未闭环。
    if list_final_manifest != list_source_manifest:

        # 不留下看似成功但内容不一致的目标。
        raise RuntimeError(
            "> ERR: [Python] final destination manifest does not match the source"
        )

    # post-switch 身份文件必须仍然存在。
    if not (path_destination / "SKILL.md").is_file() or not (
        path_destination / "VERSION"
    ).is_file():

        # 身份缺失时让上层走隔离和恢复路径。
        raise RuntimeError(
            "> ERR: [Python] installed destination is missing Skill identity files"
        )

    # 将复制闭环结果集中成不可变对象供收据和恢复逻辑读取。
    return {
        "path_backup_target": path_backup_target,  # 可选旧目标备份路径。
        "bool_destination_backed_up": bool_destination_backed_up,  # 备份完成与否决定恢复路径。
        "str_staging_manifest_hash": str_staging_manifest_hash,  # staging 副本摘要。
        "str_final_manifest_hash": str_final_manifest_hash,  # 正式目标摘要。
    }

# 写入失败恢复收据。
def _write_recovery_receipt(
    context: dict[str, Any],
    path_recovery_receipt: Path,
    list_recovery_errors: list[str],
    path_quarantine: Path,
) -> None:
    """写入当前 guided 恢复现场的 JSON 收据。

    参数:
        context: 复制失败现场、摘要和锁路径的恢复上下文。
        path_recovery_receipt: 收据目标路径。
        list_recovery_errors: 当前恢复错误列表。
        path_quarantine: 失败副本隔离路径。
    返回:
        无；收据成功写入磁盘。
    """

    # 收据保留失败路径和三阶段清单摘要，禁止静默清理现场。
    dict_receipt: dict[str, Any] = {  # 绑定失败路径、摘要和锁状态的恢复 receipt。
        "schema_version": 1,  # 恢复收据结构版本。
        "recovery_errors": list_recovery_errors,  # 已收集的隔离和恢复错误。
        "quarantine": str(path_quarantine),  # 失败副本隔离位置。
        "backup": str(context["path_backup_target"]) if context["path_backup_target"] else "",  # 旧目标备份位置。
        "destination": str(context["path_destination"]),  # 正式目标路径。
        "source_manifest_sha256": context["str_source_manifest_hash"],  # 源树输入指纹。
        "staging_manifest_sha256": context["str_staging_manifest_hash"],  # staging 观测指纹。
        "final_manifest_sha256": context["str_final_manifest_hash"],  # 正式目标侧的恢复观测指纹。
        "lock_path": str(context["path_lock"]),  # 仍需人工核验的事务锁。
    }

    # 写入带缩进的 JSON，便于人工核验恢复边界。
    path_recovery_receipt.write_text(  # 恢复收据落盘动作。
        json.dumps(dict_receipt, ensure_ascii=False, indent=2) + "\n",  # 保留可人工审计的 JSON 排版。
        encoding="utf-8",  # 收据统一使用 UTF-8 编码。
    )

# 复制失败时隔离新副本并恢复旧目标。
def _recover_copy_failure(
    context: dict[str, Any],
) -> None:
    """处理复制失败、隔离失败和旧目标恢复。

    参数:
        context: 复制失败现场、摘要、隔离根和锁边界的恢复上下文。
    返回:
        无；成功恢复后抛出安装失败，恢复不完整时保留锁。
    异常:
        SystemExit: 总是以结构化安装失败结束。
    """

    # 恢复逻辑只从上下文读取复制阶段已经确认的事实。
    exception_object_error: Exception = context["object_error"]  # 原始复制失败原因。

    # 失败副本移动必须继续受到同一 containment 根保护。
    path_boundary: Path = context["path_boundary"]  # 失败副本允许停留的边界。

    # staging 可能是尚未切换或切换前遗留的副本。
    path_staging: Path = context["path_staging"]  # 需要检查的 staging 路径。

    # 正式目标用于判断失败副本和恢复位置。
    path_destination: Path = context["path_destination"]  # 安装目标路径。

    # 旧目标备份可能为空，表示本轮是首次安装。
    path_backup_target: Path | None = context["path_backup_target"]  # 可选旧目标备份。

    # 该标记决定失败时是否允许把目标移入隔离根。
    bool_destination_backed_up: bool = context["bool_destination_backed_up"]  # 旧目标转移状态。

    # 隔离根由 manifest 声明并已受 boundary 检查。
    path_quarantine_root: Path = context["path_quarantine_root"]  # manifest 声明的失败副本隔离目录。

    # 锁路径必须在恢复完成前保持可见。
    path_lock: Path = context["path_lock"]  # 恢复阶段必须继续持有的锁文件。

    # 三阶段摘要原样写入恢复收据。
    str_source_manifest_hash: str = context["str_source_manifest_hash"]  # 源树摘要。

    # staging 摘要记录复制阶段的观测结果。
    str_staging_manifest_hash: str = context["str_staging_manifest_hash"]  # 复制中间态的源树指纹。

    # final 摘要记录切换后的目标观测结果。
    str_final_manifest_hash: str = context["str_final_manifest_hash"]  # 正式目标的切换后指纹。

    # 收据后缀只能来自已验证 manifest。
    str_recovery_suffix: str = context["str_recovery_suffix"]  # 恢复文件后缀。

    # 恢复错误必须逐项保留，不能用最后一个异常覆盖前因。
    list_recovery_errors: list[str] = []  # 恢复阶段错误列表。

    # 为本轮失败副本预留唯一隔离路径。
    path_quarantine: Path = path_quarantine_root / uuid.uuid4().hex  # 失败副本路径。

    # 隔离根创建失败也进入恢复收据。
    try:

        # 为失败副本预留受控隔离边界。
        path_quarantine_root.mkdir(parents=True, exist_ok=True)

    # 记录隔离根创建失败，后续保留原锁。
    except OSError as object_recovery_error:

        # 错误字段带阶段前缀，便于收据消费者分类。
        list_recovery_errors.append(f"quarantine_root:{object_recovery_error}")

    # 只移动仍在 containment 根内的失败副本。
    path_failed_copy: Path | None = (  # 可见失败副本路径。
        path_staging  # staging 尚未切换时优先隔离 staging。
        if path_staging.exists()  # 仅在 staging 节点仍可见时选择它。
        else path_destination  # 旧目标已备份时正式目标承载失败副本。
        if bool_destination_backed_up  # 只有发生替换转移才允许移动正式目标。
        else None  # 首次安装失败且无副本时不生成移动动作。
    )

    # 失败副本隔离失败时必须保留路径和错误。
    if (
        path_failed_copy is not None
        and path_failed_copy.exists()
        and path_failed_copy.is_relative_to(path_boundary)
    ):

        # 将失败副本移出正式目标路径。
        try:

            # 隔离动作保持在已验证 containment 根内。
            shutil.move(str(path_failed_copy), str(path_quarantine))

        # 隔离失败时继续生成恢复收据。
        except OSError as object_recovery_error:

            # 记录具体隔离失败，不删除现场。
            list_recovery_errors.append(f"quarantine:{object_recovery_error}")

    # 有旧备份且正式目标空缺时优先恢复原可见状态。
    if path_backup_target is not None and path_backup_target.exists() and not path_destination.exists():

        # 恢复动作同样必须单独记录错误。
        try:

            # 将旧目标移回事务开始时的正式位置。
            shutil.move(str(path_backup_target), str(path_destination))

        # 恢复失败时保持备份和锁以供人工处理。
        except OSError as object_recovery_error:

            # 记录恢复阶段错误，阻止伪造成功。
            list_recovery_errors.append(f"restore:{object_recovery_error}")

    # 隔离根存在时收据与隔离副本同处一处。
    path_recovery_receipt: Path = (  # 恢复收据路径。
        path_quarantine_root / f"{uuid.uuid4().hex}{str_recovery_suffix}"  # 隔离根存在时收据靠近失败现场。
        if path_quarantine_root.exists()  # 仅复用已经创建的隔离根。
        else path_boundary / f"{uuid.uuid4().hex}{str_recovery_suffix}"  # 隔离根失败时退回 containment 根。
    )

    # 先写收据，再尝试清理锁，保证现场可追踪。
    try:

        # 收据包含当前所有可见恢复路径和摘要。
        _write_recovery_receipt(
            context,  # 复制失败现场和摘要来源。
            path_recovery_receipt,
            list_recovery_errors,  # 当前收集的恢复错误。
            path_quarantine,  # 失败副本的隔离路径。
        )

    # 收据写失败也必须留在恢复错误列表中。
    except OSError as object_recovery_error:

        # 保留原始收据写入失败原因。
        list_recovery_errors.append(f"receipt:{object_recovery_error}")

    # 只有收据写入和恢复步骤都成功时才清理锁。
    if not list_recovery_errors:

        # 锁删除失败应当重新写入收据并保留锁。
        try:

            # 恢复成功后释放本次事务锁。
            path_lock.unlink()

        # 锁清理失败属于恢复不完整状态。
        except OSError as object_recovery_error:

            # 记录锁清理错误并尝试更新恢复收据。
            list_recovery_errors.append(f"lock_cleanup:{object_recovery_error}")

            # 更新收据失败也必须保留在错误列表中。
            try:

                # 收据包含最新锁状态，方便下次人工核验。
                _write_recovery_receipt(
                    context,  # 复用同一失败现场上下文。
                    path_recovery_receipt,
                    list_recovery_errors,  # 锁清理后的完整错误列表。
            path_quarantine,  # 将本轮失败副本位置写入恢复收据。
                )

            # 二次收据失败不覆盖首次错误。
            except OSError as object_receipt_error:

                # 记录收据更新失败，明确恢复仍不完整。
                list_recovery_errors.append(f"receipt_after_lock:{object_receipt_error}")

    # 任何恢复错误都要求人工保留锁并检查现场。
    if list_recovery_errors:

        # 抛出包含收据和全部错误的结构化失败。
        raise SystemExit(
            "> ERR: [Python] installation recovery incomplete; receipt="
            + str(path_recovery_receipt)
            + "; errors="
            + str(list_recovery_errors)
        ) from exception_object_error

    # 完整恢复后抛出原始安装失败和收据位置。
    raise SystemExit(
        "> ERR: [Python] installation failed before completion; receipt="
        + str(path_recovery_receipt)
        + "; error="
        + str(exception_object_error)
    ) from exception_object_error

# 构造成功安装 receipt 的平台、目标和清单载荷。
def _build_success_receipt(context: dict[str, Any]) -> dict[str, Any]:
    """构造成功安装 receipt 的机器可读载荷。

    参数:
        context: 成功安装身份、清单摘要和收尾路径的上下文。
    返回:
        可写入 installer.receipt.json 的完整映射。
    """

    # 返回最终安装副本的机器可读身份载荷。
    return {
        "schema_version": 1,  # 收据结构版本。
        "platform_id": context["dict_platform"]["platform_id"],  # 选择的平台稳定 ID。
        "platform_display_name": context["dict_platform"]["display_name"],  # 选择的平台显示名。
        "skill_name": context["str_skill_name"],  # 安装技能名称。
        "source_path": str(context["path_destination"].parent),  # 安装目标的用户根父路径。
        "destination_path": str(context["path_destination"]),  # 最终安装目录绝对路径。
        "projection_sha256": context["str_projection_hash"],  # 平台菜单来源摘要。
        "catalog_sha256": context["str_catalog_hash"],  # 注册平台来源摘要。
        "project_kind": context["str_project_kind"],  # 适用性门禁确认的项目类型。
        "source_manifest_sha256": context["str_source_manifest_hash"],  # 源树输入摘要。
        "staging_manifest_sha256": context["str_staging_manifest_hash"],  # staging 中间副本指纹。
        "final_manifest_sha256": context["str_final_manifest_hash"],  # 正式目标闭环指纹。
        "source_manifest_entry_count": len(context["list_source_manifest"]),  # 源树条目计数。
        "source_manifest": context["list_source_manifest"],  # 完整源树事实清单。
        "manifest_sha256": context["dict_manifest"]["MANIFEST_SHA256"],  # bundle manifest 完整性指纹。
    }

# 写入最终安装 receipt 并清理锁。
def _write_success_receipt(
    context: dict[str, Any],
) -> None:
    """写入成功收据并释放安装锁。

    参数:
        context: 成功安装身份、清单摘要和收尾路径的上下文。
    返回:
        无；成功时写入 receipt 并删除锁。
    异常:
        SystemExit: receipt 或锁清理失败。
    """

    # 构造成功 receipt，集中保留安装身份和三阶段摘要。
    dict_receipt: dict[str, Any] = _build_success_receipt(context)  # 最终 receipt 载荷。

    # 收据写入和锁清理复用成功目标路径。
    path_destination: Path = context["path_destination"]  # receipt 实际写入的目标目录。

    # manifest 提供失败恢复收据的后缀。
    dict_manifest: dict[str, str] = context["dict_manifest"]  # 成功事务使用的 bundle manifest。

    # 收据失败时仍在同一隔离边界生成恢复文件。
    path_quarantine_root: Path = context["path_quarantine_root"]  # receipt 失败的隔离目录。

    # 成功事务最后释放独占锁。
    path_lock: Path = context["path_lock"]  # 安装事务锁文件。

    # 成功收据必须落在最终 Skill 目录内。
    try:

        # 先写入身份收据，再释放事务锁。
        (path_destination / "installer.receipt.json").write_text(  # 成功安装收据文件。
            json.dumps(dict_receipt, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    # 收据失败时写入恢复收据并保持锁。
    except OSError as object_error:

        # 收据失败的恢复文件使用 manifest 声明的后缀。
        try:

            # 隔离根可能尚不存在，成功副本仍必须保留。
            path_quarantine_root.mkdir(parents=True, exist_ok=True)

            # receipt 写入失败时为人工恢复保留独立收据。
            path_recovery_receipt: Path = (  # 成功收据失败的恢复文件。
                path_quarantine_root  # 使用同一隔离根保存恢复证据。
                / f"{uuid.uuid4().hex}{dict_manifest['RECOVERY_RECEIPT_SUFFIX']}"  # 使用 manifest 后缀。
            )

            # 记录成功收据失败和当前锁路径。
            path_recovery_receipt.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "recovery_errors": [f"success_receipt:{object_error}"],
                        "destination": str(path_destination),
                        "source_manifest_sha256": context["str_source_manifest_hash"],
                        "staging_manifest_sha256": context["str_staging_manifest_hash"],
                        "final_manifest_sha256": context["str_final_manifest_hash"],
                        "lock_path": str(path_lock),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        # 二次恢复收据失败时保留原始 receipt 错误。
        except OSError as object_recovery_error:

            # 锁保留是此时唯一安全的人工恢复信号。
            raise SystemExit(
                "> ERR: [Python] success receipt and recovery receipt failed; original="
                + str(object_error)
                + "; recovery="
                + str(object_recovery_error)
                + "; lock preserved: "
                + str(path_lock)
            ) from object_error

        # 收据失败但恢复文件成功时仍禁止成功结论。
        raise SystemExit(
            "> ERR: [Python] installation receipt could not be written; lock preserved: "
            + str(path_lock)
            + "; recovery="
            + str(path_recovery_receipt)
        ) from object_error

    # 收据落盘后释放锁，完成事务闭环。
    try:

        # 成功 receipt 已存在，锁可以安全清理。
        path_lock.unlink()

    # 锁清理失败时写入可见恢复收据。
    except OSError as object_error:

        # 清理失败不删除成功目标，保留锁供人工核验。
        try:

            # 恢复收据仍使用同一受控隔离根。
            path_quarantine_root.mkdir(parents=True, exist_ok=True)

            # 锁清理失败时生成独立的恢复证据路径。
            path_recovery_receipt = path_quarantine_root / (  # 锁清理失败收据。
                f"{uuid.uuid4().hex}{dict_manifest['RECOVERY_RECEIPT_SUFFIX']}"  # 使用 manifest 声明的后缀。
            )

            # 将锁清理失败事实写入恢复收据。
            path_recovery_receipt.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "recovery_errors": [f"lock_cleanup:{object_error}"],
                        "destination": str(path_destination),
                        "source_manifest_sha256": context["str_source_manifest_hash"],
                        "staging_manifest_sha256": context["str_staging_manifest_hash"],
                        "final_manifest_sha256": context["str_final_manifest_hash"],
                        "lock_path": str(path_lock),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        # 恢复收据失败时不覆盖锁清理原因。
        except OSError:

            # 仅以空路径标记收据不可用，锁仍保留。
            path_recovery_receipt = None  # 收据写入失败状态。

        # 成功目标存在但锁未释放，必须报告人工恢复边界。
        raise SystemExit(
            "> ERR: [Python] installation completed but lock cleanup failed: "
            + str(path_lock)
            + "; receipt="
            + str(path_recovery_receipt)
        ) from object_error
