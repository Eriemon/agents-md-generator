"""管理 worker profile、gardener 工具和统一 profile bundle 收据。"""

# 延迟类型注解求值，兼容项目支持的 Python 运行环境。
from __future__ import annotations

# profile 生命周期使用标准库完成摘要、备份和原子替换。
import hashlib
import os
from datetime import datetime, timezone
import shutil
from pathlib import Path
from typing import Any

# profile 模块提供三个 worker 的 proposed、写入和握手合同。
from gardener_worker_profile import GARDENER_WORKER_SHA256
from gardener_worker_profile import ensure_gardener_worker_profile
from gardener_worker_profile import gardener_worker_path
from reviewer_worker_profile import REVIEWER_WORKER_SHA256
from reviewer_worker_profile import ensure_reviewer_worker_profile
from tester_worker_profile import ensure_tester_worker_profile

# 根状态验证保持与 profile 写入相同的项目边界。
from manage_worker_state import validate_worker_states
from worker_dispatch_contracts import CANONICAL_WORKER_IDS

# tester 的 canonical id 作为所有 profile 路由的稳定键。
TESTER_WORKER_ID: str = CANONICAL_WORKER_IDS.get("tester", "")  # tester profile 的 canonical 身份键。

# reviewer 的 canonical id 作为只读方案复核的稳定键。
REVIEWER_WORKER_ID: str = CANONICAL_WORKER_IDS.get("reviewer", "")  # reviewer 触发链使用的唯一身份索引。

# gardener 的 canonical id 作为提交后源码整理的稳定键。
GARDENER_WORKER_ID: str = CANONICAL_WORKER_IDS.get("gardener", "")  # gardener 提交后审查使用的唯一身份索引。

# 仅在授权边界内写入 tester profile。
def _write_tester_profile(codex_home: str | Path | None, confirm_update: bool) -> dict[str, object]:
    """按确认标志写入 tester profile。

    参数:
        codex_home: 可选的 Codex 配置目录。
        confirm_update: 用户是否确认 tester 更新。
    返回:
        tester profile 写入报告。
    """

    # 写入动作只在调用方已完成确认后执行。
    return ensure_tester_worker_profile(codex_home, write=True, confirm_update=confirm_update)

# 用 reviewer 内容哈希授权原子配置更新。
def _write_reviewer_profile(codex_home: str | Path | None, confirm_sha256: str) -> dict[str, object]:
    """按确认哈希写入 reviewer profile。

    参数:
        codex_home: 可选的 Codex 配置目录。
        confirm_sha256: 用户确认的 reviewer 内容哈希。
    返回:
        reviewer profile 写入报告。
    """

    # reviewer 写入必须由完整内容哈希授权。
    return ensure_reviewer_worker_profile(codex_home, write=True, confirm_sha256=confirm_sha256)

# 用显式确认授权 gardener profile 更新。
def _write_gardener_profile(codex_home: str | Path | None, confirm_update: bool) -> dict[str, object]:
    """按显式确认写入 gardener profile。

    参数:
        codex_home: 可选的 Codex 配置目录。
        confirm_update: 用户是否确认 gardener 更新。
    返回:
        gardener profile 写入报告。
    """

    # gardener 配置更新使用与 tester 相同的布尔授权边界。
    return ensure_gardener_worker_profile(codex_home, write=True, confirm_update=confirm_update)

# 从当前源码位置定位 gardener 工具源文件。
def _gardener_tool_source_path() -> Path:
    """返回随源码发布的 gardener 工具路径。

    参数:
        无显式参数；路径由当前管理器位置确定。
    返回:
        随源码发布的 gardener 工具路径。
    """

    # 管理器与工具位于同一 workers 目录，使用解析位置避免硬编码项目根。
    return Path(__file__).resolve().with_name("pycode_gardener.py")

# 从 gardener profile 安装根推导工具目标路径。
def _gardener_tool_target_path(codex_home: str | Path | None) -> Path:
    """返回 Codex 主目录下的 gardener 工具安装路径。

    参数:
        codex_home: 可选的 Codex 配置目录。
    返回:
        Codex 主目录下的 gardener 工具安装路径。
    """

    # profile 的同级目录是 agents，先解析 profile 路径避免重复构造安装根。
    path_profile = gardener_worker_path(codex_home)  # profile 路径用于定位工具安装根。

    # 工具固定投影到 profile 同级 tools 下的协议角色目录。
    return path_profile.parent / "tools" / GARDENER_WORKER_ID / "pycode_gardener.py"

# 为 profile 和工具收据计算原始字节摘要。
def _sha256_bytes(bytes_content: bytes) -> str:
    """计算字节内容摘要，供源文件和读回文件共用。

    参数:
        bytes_content: 待摘要的原始字节内容。
    返回:
        十六进制 SHA-256 摘要。
    """

    # 工具和 profile bundle 必须按原始 UTF-8/二进制字节复算。
    return hashlib.sha256(bytes_content).hexdigest()

# 对 gardener 工具执行源目标读回闭环校验。
def _gardener_tool_status(
    codex_home: str | Path | None,
    *,
    write: bool = False,
    confirm_update: bool = False,
) -> dict[str, object]:
    """检查或按确认收据原子安装 gardener 工具。

    参数:
        codex_home: 可选的 Codex 配置目录。
        write: 是否执行已授权的工具写入。
        confirm_update: 是否收到工具刷新确认。
    返回:
        包含源、目标、备份和读回验证状态的报告。
    """

    # 源码和安装目标都必须是普通文件，缺失即 fail-closed。
    path_source = _gardener_tool_source_path()  # 解析随源码发布的工具源文件。

    # 目标路径决定备份、临时文件和最终读回位置。
    path_target = _gardener_tool_target_path(codex_home)  # 解析 Codex 安装目标路径。

    # 源文件缺失时直接返回，阻止无源写入或伪造校验。
    if not path_source.is_file():

        # 缺失源文件必须以不可写的 fail-closed 报告结束。
        return {
            "enabled": True,
            "valid": False,
            "status": "missing-source",
            "path": str(path_target),
            "source_path": str(path_source),
            "source_sha256": "",
            "target_sha256": "",
            "errors": ["gardener tool source is missing"],
            "backup_path": "",
            "updated": False,
            "requires_user_confirmation": False,
        }

    # 先读取源字节，保证后续比较和写入使用同一快照。
    bytes_source = path_source.read_bytes()  # 固定本次操作使用的源内容。

    # 源摘要是后续目标比较和读回验证的唯一基准。
    str_source_hash = _sha256_bytes(bytes_source)  # 计算源快照摘要。

    # 目标缺失按空字节处理，但仍保留普通文件存在性信号。
    bool_target_file = path_target.is_file()  # 记录目标是否已有普通文件。

    # 只有已存在的普通目标才读取旧内容用于摘要比较。
    bytes_target = path_target.read_bytes() if bool_target_file else b""  # 缺失目标按空字节处理。

    # 目标摘要仅在目标存在时有效，缺失目标保持空字符串。
    str_target_hash = _sha256_bytes(bytes_target) if bool_target_file else ""  # 计算目标现状摘要。

    # 只有目标存在且摘要一致时才跳过刷新确认。
    bool_matches = bool_target_file and str_target_hash == str_source_hash  # 判断目标是否已与源一致。

    # 统一记录现有状态，供只读预览和写入流程复用。
    dict_result: dict[str, object] = {
        "enabled": True,  # Codex-native 策略启用状态，不代表工具已安装。
        "valid": bool_matches,  # 现有目标是否已经通过摘要校验。
        "status": "valid" if bool_matches else "needs-refresh",  # 当前工具生命周期状态。
        "path": str(path_target),  # 目标工具的可读路径。
        "source_path": str(path_source),  # 源工具的可读路径。
        "source_sha256": str_source_hash,  # 源快照摘要。
        "target_sha256": str_target_hash,  # 目标现状摘要。
        "existing_validation": {"valid": bool_matches, "errors": [] if bool_matches else ["tool missing or drifted"]},  # 写入前验证结果。
        "final_validation": {"valid": bool_matches, "errors": [] if bool_matches else ["tool missing or drifted"]},  # 当前可作为最终验证的结果。
        "backup_path": "",  # 尚未创建的备份路径。
        "updated": False,  # 尚未发生本次写入。
        "requires_user_confirmation": not bool_matches,  # 摘要漂移是否需要确认。
        "confirm_update": confirm_update,  # 调用方传入的确认标志。
    }

    # 只读查询到此结束，不产生目录、备份或目标文件副作用。
    if not write:

        # 预览必须返回当前比较结果而不是模拟写入成功。
        return dict_result

    # 目标漂移时没有确认不得进入写入分支。
    if not bool_matches and not confirm_update:

        # 记录缺少确认的阻断状态，保证目标保持不变。
        dict_result["status"] = "confirmation-required"  # 标记写入授权缺失。

        # 将可操作的确认要求返回给上层调用方。
        dict_result["errors"] = ["confirm_gardener_update is required for tool refresh"]  # 暴露阻断原因。

        # 保留原目标不变，并要求调用方补齐确认收据。
        return dict_result

    # 仅在确认通过后创建工具目标目录。
    path_target.parent.mkdir(parents=True, exist_ok=True)  # 准备原子替换所需的父目录。

    # 写入前保留已有目标备份，支持失败后的人工恢复。
    if bool_target_file:

        # 使用 UTC 微秒时间戳和进程号避免备份名称冲突。
        str_stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")  # 生成可排序的备份时间戳。

        # 备份与目标同目录，便于人工恢复和审计定位。
        path_backup = path_target.with_name(f"{path_target.name}.bak-{str_stamp}-{os.getpid()}")  # 构造唯一备份文件名。

        # 先复制旧目标，避免直接覆盖失去回滚点。
        shutil.copy2(path_target, path_backup)  # 保存当前目标快照。

        # 把备份路径写入生命周期报告，供调用方保留。
        dict_result["backup_path"] = str(path_backup)  # 记录可恢复的备份位置。

    # 临时文件与目标同目录，保证 os.replace 具备原子替换条件。
    path_temp = path_target.with_name(f"{path_target.name}.tmp-{os.getpid()}")  # 生成本次写入临时路径。

    # 先完整写临时文件，再一次性替换正式目标。
    try:

        # 写入已固定的源快照，避免读取变化中的源文件。
        path_temp.write_bytes(bytes_source)

        # 原子提交工具内容，防止读者看到半写入文件。
        os.replace(path_temp, path_target)

    # 替换完成或中断后都进入临时文件清理阶段。
    finally:

        # 无论替换是否成功，都清理残留临时文件。
        if path_temp.exists():

            # 删除失败中断留下的临时文件，避免污染后续运行。
            path_temp.unlink()

    # 重新读取正式目标，以读回摘要证明实际落盘内容。
    bytes_readback = path_target.read_bytes()  # 读取替换后的目标字节。

    # 计算正式目标读回摘要，用于证明内容已经落盘。
    str_readback_hash = _sha256_bytes(bytes_readback)  # 计算目标读回摘要。

    # 只有源快照与正式目标读回摘要一致才算写入成功。
    bool_readback = str_readback_hash == str_source_hash  # 比较源快照与正式目标。

    # 把读回摘要写入最终生命周期报告。
    dict_result["target_sha256"] = str_readback_hash  # 记录读回摘要。

    # 读回一致才允许报告本次目标已经更新。
    dict_result["updated"] = bool_readback  # 标记写入是否达到读回一致。

    # 最终有效性直接绑定到源目标摘要比较。
    dict_result["valid"] = bool_readback  # 将读回一致映射为最终有效性。

    # 根据读回比较结果生成稳定的生命周期状态。
    dict_result["status"] = "valid" if bool_readback else "readback-failed"  # 生成最终状态。

    # 最终验证只承认目标读回摘要与源快照一致。
    dict_result["final_validation"] = {
        "valid": bool_readback,  # 最终摘要比较是否通过。
        "errors": [] if bool_readback else ["gardener tool readback hash mismatch"],  # 读回失败时的阻断信息。
    }

    # 返回包含备份路径和最终读回结论的完整报告。
    return dict_result

# 按稳定顺序绑定 profile 与工具提案字节。
def _profile_bundle_sha256(
    dict_profiles: dict[str, dict[str, object]],
    dict_tool: dict[str, object] | None = None,
) -> str:
    """按 worker 名称和配置原文计算稳定的兼容 bundle 哈希。

    参数:
        dict_profiles: worker 名称到生命周期报告的映射。
        dict_tool: 可选的 gardener 工具生命周期报告。
    返回:
        由 profile 和工具摘要共同计算的十六进制哈希。
    """

    # 名称、NUL、UTF-8 原文和换行组成可复算的配置清单。
    hash_profile_manifest: Any = hashlib.sha256()  # profile 清单摘要对象，持续接收稳定字节片段。

    # 按 worker 名称排序，保证同一配置在不同运行中的哈希一致。
    for str_name in sorted(dict_profiles):

        # 读取当前 worker 的生命周期报告。
        dict_profile = dict_profiles[str_name]  # 当前 worker 的配置报告。

        # bundle 优先绑定 proposed 原文，确保确认值对应即将写入的字节。
        obj_proposed_content: object = dict_profile.get("proposed_content")  # 当前 worker 的 proposed 原文。

        # final_content 是已写入但需要复用的兼容字段。
        obj_final_content: object = dict_profile.get("final_content")  # 当前 worker 的最终原文。

        # existing_content 是旧配置仍可作为哈希输入时的回退字段。
        obj_existing_content: object = dict_profile.get("existing_content")  # 当前 worker 的现有原文。

        # 将三个候选字段收束为本次 bundle 的 UTF-8 原文。
        str_content = str(obj_proposed_content or obj_final_content or obj_existing_content or "")  # 当前 worker 的待确认配置原文。

        # 追加 worker 名称，区分不同 profile 的边界。
        hash_profile_manifest.update(str_name.encode("utf-8"))

        # 追加 NUL 分隔符，避免名称和内容发生歧义拼接。
        hash_profile_manifest.update(b"\0")

        # 追加 UTF-8 配置原文，绑定实际可读内容。
        hash_profile_manifest.update(str_content.encode("utf-8"))

        # 追加换行分隔符，保持每个 profile 的记录边界稳定。
        hash_profile_manifest.update(b"\n")

    # gardener 工具摘要存在时追加其源和目标摘要。
    if dict_tool is not None:

        # 先写入工具记录标签，区分 profile 内容和工具内容。
        hash_profile_manifest.update(b"gardener_tool\0")

        # 绑定工具源文件摘要，识别源码漂移。
        hash_profile_manifest.update(str(dict_tool.get("source_sha256", "")).encode("ascii"))

        # 用 NUL 分隔源摘要和目标摘要。
        hash_profile_manifest.update(b"\0")

        # 绑定工具目标文件摘要，识别安装副本漂移。
        hash_profile_manifest.update(str(dict_tool.get("target_sha256", "")).encode("ascii"))

        # 以换行收束工具记录，保持清单编码稳定。
        hash_profile_manifest.update(b"\n")

    # 返回完整清单的十六进制摘要，供 receipt 绑定。
    return hash_profile_manifest.hexdigest()

# 汇总 profile 备份、读回和 bundle 观察字段。
def _profile_lifecycle_views(
    dict_profiles: dict[str, dict[str, object]],
    dict_tool: dict[str, object] | None = None,
) -> dict[str, object]:
    """构造 bundle、备份和读回验证的统一可观察字段。

    参数:
        dict_profiles: worker 名称到生命周期报告的映射。
        dict_tool: 可选的 gardener 工具生命周期报告。
    返回:
        面向状态、预览和验证调用方的统一字段映射。
    """

    # 每个字段按 worker 名称排序，便于远程 receipt 稳定比较。
    dict_backup_paths = {
        str_name: str(dict_profile.get("backup_path", ""))  # 当前 worker 的可恢复备份路径。
        for str_name, dict_profile in sorted(dict_profiles.items())  # 固定 worker 排序，稳定 receipt 顺序。
    }

    # 优先暴露最终读回验证，缺失时回退到写入前验证。
    dict_readback = {
        str_name: dict_profile.get(  # 当前 worker 的最终或现有验证字段。
            "final_validation",  # 优先读取写入后的最终验证字段。
            dict_profile.get("existing_validation", {}),  # 缺少最终字段时回退现有验证。
        )
        for str_name, dict_profile in sorted(dict_profiles.items())  # 固定 worker 排序，稳定报告结构。
    }

    # 工具报告存在时追加其专属备份和读回字段。
    if dict_tool is not None:

        # 追加 gardener 工具备份路径，支持工具副本恢复。
        dict_backup_paths["gardener_tool"] = str(dict_tool.get("backup_path", ""))  # 工具副本备份位置。

        # 追加 gardener 工具最终读回验证，避免遗漏工具边界。
        dict_readback["gardener_tool"] = dict_tool.get("final_validation", {})  # 工具副本最终读回验证。

    # 返回统一的 profile、工具、摘要和验证视图。
    return {
        "worker_profiles": dict_profiles,
        "gardener_tool": dict_tool or {},
        "profile_bundle_sha256": _profile_bundle_sha256(dict_profiles, dict_tool),
        "gardener_tool_source_sha256": str((dict_tool or {}).get("source_sha256", "")),
        "gardener_tool_sha256": str((dict_tool or {}).get("target_sha256", "")),
        "backup_paths": dict_backup_paths,
        "readback_validation": dict_readback,
    }

# 为待确认的 profile 写入生成明确提示。
def _confirmation_message(pending: bool) -> str:
    """根据待确认状态返回稳定提示文本。

    参数:
        pending: 是否仍存在未确认的 profile 更新。
    返回:
        需要确认时返回提示文本，否则返回空字符串。
    """

    # 已无待确认动作时保持空提示，避免误导调用方。
    if not pending:

        # 清空确认字段表示生命周期写入已完成。
        return ""

    # 待确认动作必须明确要求查看 proposed 内容并确认。
    return "tester/reviewer/gardener profile update requires explicit confirmation and proposed content review"

# 按统一 bundle 收据原子更新 worker 配置。
def _preview_profile_mapping(
    dict_tester_preview: dict[str, object],
    dict_reviewer_preview: dict[str, object],
    dict_gardener_preview: dict[str, object],
) -> dict[str, dict[str, object]]:
    """构造本次 bundle 使用的三个 profile 预览映射。

    参数:
        dict_tester_preview: tester profile 预览。
        dict_reviewer_preview: reviewer profile 预览。
        dict_gardener_preview: gardener profile 预览。
    返回:
        按 worker 名称固定排序语义的 profile 预览映射。
    """

    # 返回原始预览对象，保证 bundle 哈希绑定实际 proposed 字节。
    return {
        TESTER_WORKER_ID: dict_tester_preview,
        REVIEWER_WORKER_ID: dict_reviewer_preview,
        GARDENER_WORKER_ID: dict_gardener_preview,
    }

# 把同一 bundle 的确认值投影到三个 profile 和工具写入边界。
def apply_workers(
    codex_home: str | Path | None = None,
    project: str | Path = ".",
    *,
    confirm_tester_update: bool = False,
    confirm_reviewer_sha256: str = "",
    confirm_gardener_update: bool = False,
    confirm_profile_bundle_sha256: str = "",
) -> dict[str, Any]:
    """按显式收据更新三个 worker 配置和 gardener 工具；根状态独立管理。

    参数:
        codex_home: 可选的 Codex 配置目录。
        project: 当前工作文件夹路径。
        confirm_tester_update: 是否确认 tester profile 更新。
        confirm_reviewer_sha256: 对 reviewer proposed 内容的确认哈希。
        confirm_gardener_update: 是否确认 gardener profile 与工具更新。
        confirm_profile_bundle_sha256: 三个 profile 与 gardener 工具的统一 bundle 哈希。
    返回:
        包含写入状态、确认要求和根状态的结果映射。
    """

    # 先读取 proposed 状态，防止未确认直接写入。
    dict_tester_preview = ensure_tester_worker_profile(codex_home, write=False)  # tester proposed 配置结果。

    # reviewer 预览记录待确认的 proposed 哈希。
    dict_reviewer_preview = ensure_reviewer_worker_profile(codex_home, write=False)  # reviewer proposed 哈希结果。

    # gardener 预览记录待确认的只读配置内容。
    dict_gardener_preview = ensure_gardener_worker_profile(codex_home, write=False)  # 读取 gardener profile 的文件快照、摘要与授权状态。

    # 只有显式漂移才需要 tester 收据。
    bool_tester_pending = dict_tester_preview.get("status") == "needs-refresh"  # tester 是否存在待确认变更。

    # reviewer 收据必须精确匹配用户确认哈希。
    bool_reviewer_pending = bool(dict_reviewer_preview.get("requires_user_confirmation"))  # reviewer 是否有待确认变更。

    # gardener 漂移必须由当前用户显式确认。
    bool_gardener_pending = dict_gardener_preview.get("status") == "needs-refresh"  # gardener profile 是否等待确认。

    # 工具缺失或漂移也必须取得同一 gardener 更新收据。
    dict_gardener_tool_preview = _gardener_tool_status(codex_home, write=False)  # gardener 工具当前预览状态。

    # 工具预览只有摘要漂移时才需要同一份确认。
    bool_gardener_tool_pending = dict_gardener_tool_preview.get("status") == "needs-refresh"  # gardener 工具是否等待确认。

    # 统一 bundle 绑定三个 profile 和 gardener 工具的 proposed 字节。
    dict_preview_profiles = _preview_profile_mapping(dict_tester_preview, dict_reviewer_preview, dict_gardener_preview)  # 本次 bundle 的 profile 输入。

    # 计算本次预览的唯一 bundle 摘要。
    str_profile_bundle_sha256 = _profile_bundle_sha256(dict_preview_profiles, dict_gardener_tool_preview)  # 当前 proposed bundle 摘要。

    # 旧参数只保留兼容读取，新 bundle 收据不能与旧收据混用。
    bool_legacy_confirmation = bool(confirm_tester_update or confirm_reviewer_sha256 or confirm_gardener_update)  # 兼容旧式单项收据。

    # 当前调用是否提交了新的 bundle 收据。
    bool_bundle_confirmation = bool(confirm_profile_bundle_sha256)  # 新 bundle 收据是否出现。

    # 将 tester 兼容参数转换为带类型前缀的本地确认状态。
    bool_confirm_tester_update = bool(confirm_tester_update)  # 当前 tester 是否获准写入。

    # 将 reviewer 兼容参数转换为带类型前缀的本地授权哈希。
    str_confirm_reviewer_sha256 = str(confirm_reviewer_sha256)  # 当前 reviewer 授权哈希。

    # 规范 gardener 的布尔授权，使工具刷新与 profile 写入共用一份收据。
    bool_confirm_gardener_update = bool(confirm_gardener_update)  # gardener 写入授权状态。

    # 新旧收据同时出现时直接拒绝写入。
    if bool_legacy_confirmation and bool_bundle_confirmation:

        # 混用会让三份 profile 失去同一授权边界。
        return {
            "valid": False,
            "requires_user_confirmation": True,
            "errors": ["profile bundle confirmation cannot mix legacy confirmations"],
            "profile_bundle_sha256": str_profile_bundle_sha256,
            "worker_state": validate_worker_states(project),
        }

    # bundle 收据必须精确匹配当前 proposed 字节。
    if bool_bundle_confirmation and confirm_profile_bundle_sha256.lower() != str_profile_bundle_sha256:

        # 旧 bundle 不能确认当前 profile 内容。
        return {
            "valid": False,
            "requires_user_confirmation": True,
            "errors": ["profile bundle confirmation hash does not match proposed bytes"],
            "profile_bundle_sha256": str_profile_bundle_sha256,
            "worker_state": validate_worker_states(project),
        }

    # 新 bundle 收据通过后映射到三个既有写入确认入口。
    if bool_bundle_confirmation:

        # 由 bundle 收据确定 tester 是否进入写入分支。
        bool_confirm_tester_update = bool(bool_tester_pending)  # tester profile 是否允许写入。

        # 由 bundle 收据确定 reviewer 的内容授权哈希。
        str_confirm_reviewer_sha256 = str(REVIEWER_WORKER_SHA256) if bool_reviewer_pending else ""  # reviewer 内容授权哈希。

        # 由 bundle 收据确定 gardener profile 与工具是否写入。
        bool_confirm_gardener_update = bool(bool_gardener_pending or bool_gardener_tool_pending)  # gardener 写入授权。

    # 使用最终归一化的 reviewer 收据判断 bundle 是否覆盖授权。
    bool_reviewer_hash_ok = str_confirm_reviewer_sha256.lower() == REVIEWER_WORKER_SHA256  # reviewer 收据哈希已匹配。

    # 任一待确认项缺少收据时 fail-closed。
    if (
        (bool_tester_pending and not bool_confirm_tester_update)
        or (bool_reviewer_pending and not bool_reviewer_hash_ok)
        or (bool_gardener_pending and not bool_confirm_gardener_update)
        or (bool_gardener_tool_pending and not bool_confirm_gardener_update)
    ):

        # 返回 proposed 证据，调用方可以重新展示后再申请确认。
        dict_profiles = {
            TESTER_WORKER_ID: dict_tester_preview,  # tester proposed 配置和摘要。
            REVIEWER_WORKER_ID: dict_reviewer_preview,  # reviewer proposed 哈希和合同。
            GARDENER_WORKER_ID: dict_gardener_preview,  # gardener proposed 快照和授权。
        }

        # 返回阻断证据，要求调用方先展示 proposed 内容并取得确认。
        return {
            "valid": False,
            "requires_user_confirmation": True,
            "confirmation": "preview worker profiles and confirm each proposed update before apply",
            "profile_bundle_sha256": str_profile_bundle_sha256,
            TESTER_WORKER_ID: dict_tester_preview,
            REVIEWER_WORKER_ID: dict_reviewer_preview,
            GARDENER_WORKER_ID: dict_gardener_preview,
            "gardener_tool": dict_gardener_tool_preview,
            "worker_state": validate_worker_states(project),
            **_profile_lifecycle_views(dict_profiles, dict_gardener_tool_preview),
        }

    # 收到确认后才允许 tester profile 原子写入。
    dict_tester = _write_tester_profile(codex_home, bool_confirm_tester_update)  # tester profile 原子写入结果。

    # 依据哈希收据完成 reviewer 配置的原子更新。
    dict_reviewer = _write_reviewer_profile(codex_home, str_confirm_reviewer_sha256)  # reviewer 原子更新报告。

    # gardener 配置只在显式确认后原子更新。
    dict_gardener = _write_gardener_profile(codex_home, bool_confirm_gardener_update)  # gardener profile 写入报告。

    # gardener 工具与 profile 使用同一确认收据完成原子更新。
    dict_gardener_tool = _gardener_tool_status(  # gardener 工具原子安装报告。
        codex_home,  # Codex 配置目录。
        write=True,  # 明确进入写入分支。
        confirm_update=bool_confirm_gardener_update,  # 沿用 gardener 更新确认。
    )

    # 写入后仍需检查是否留下 confirmation-required 状态。
    bool_tester_pending_after = dict_tester.get("status") in {"needs-refresh", "confirmation-required"}  # tester 写入后需确认。

    # reviewer 写入后若需确认，整体也必须暂停。
    bool_reviewer_pending_after = dict_reviewer.get("status") == "confirmation-required"  # reviewer 写入后仍需确认。

    # gardener 写入后若仍需确认也必须暂停。
    bool_gardener_pending_after = dict_gardener.get("status") in {"needs-refresh", "confirmation-required"}  # gardener profile 写入后仍待确认。

    # 合并三个 profile 的写入后暂停状态。
    bool_pending = bool_tester_pending_after or bool_reviewer_pending_after or bool_gardener_pending_after  # 写入后的确认状态。

    # 只有三个 profile 都有效且无待确认才算成功。
    bool_tester_valid_after = dict_tester.get("status") == "valid"  # tester profile 写入后通过验证。

    # reviewer 写入后必须同样回到 valid。
    bool_reviewer_valid_after = dict_reviewer.get("status") == "valid"  # reviewer profile 写入后验证有效。

    # gardener 写入后必须通过完整 TOML 合同。
    bool_gardener_valid_after = dict_gardener.get("status") == "valid"  # gardener profile 读回后合同有效。

    # 工具读回哈希必须与源码一致才算安装完成。
    bool_gardener_tool_valid_after = bool(dict_gardener_tool.get("valid"))  # gardener 工具写入后验证有效。

    # 三个 profile 都通过且没有暂停状态，才进入写入成功判定。
    bool_profiles_valid_after = bool_tester_valid_after and bool_reviewer_valid_after and bool_gardener_valid_after  # 三个 profile 读回均有效。

    # 无暂停且 profile 与工具都有效才允许 apply 成功。
    bool_valid = not bool_pending and bool_profiles_valid_after and bool_gardener_tool_valid_after  # 全部写入证据均通过。

    # 只有待确认时才生成提示正文，避免把空状态误报为阻塞。
    str_confirmation = _confirmation_message(bool_pending)  # 写入确认提示。

    # 读取写入动作完成后的根状态证据。
    dict_worker_state = validate_worker_states(project)  # 写入后的根状态。

    # 按 worker 名称整理写入报告，供统一 bundle 计算。
    dict_profiles = {
        TESTER_WORKER_ID: dict_tester,  # tester 写入后的摘要状态。
        REVIEWER_WORKER_ID: dict_reviewer,  # reviewer receipt 哈希通过后的最终配置报告。
        GARDENER_WORKER_ID: dict_gardener,  # gardener 写入后的合同状态。
    }

    # 返回写入结果与根状态，便于记录授权边界。
    return {
        "valid": bool_valid,
        "requires_user_confirmation": bool_pending,
        "confirmation": str_confirmation,
        "profile_bundle_sha256": str_profile_bundle_sha256,
        "profile_bundle_confirmation": (
            confirm_profile_bundle_sha256 if bool_bundle_confirmation else ""
        ),
        TESTER_WORKER_ID: dict_tester,
        REVIEWER_WORKER_ID: dict_reviewer,
        GARDENER_WORKER_ID: dict_gardener,
        "gardener_tool": dict_gardener_tool,
        "worker_state": dict_worker_state,
        **_profile_lifecycle_views(dict_profiles, dict_gardener_tool),
    }
