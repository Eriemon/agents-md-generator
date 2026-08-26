"""校验远程阶段、历史 schema-1 和统一测试收据载荷。"""

# 标准库提供本职责的类型、摘要和时间处理能力。
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

# 远程阶段与历史载荷函数由本模块开始。
def _validate_remote_phase_shape(str_phase: str, object_phase: Any) -> list[str]:
    """检查远程阶段对象是否具备最小字段集合。

    参数：str_phase 为阶段名。
    参数：object_phase 为阶段载荷。
    返回：阶段缺失或类型错误列表；合法时返回空列表。
    """

    # 阶段字段缺失时不进入值和 freshness 计算。
    bool_phase_shape_valid = (  # 远程阶段字段形状判定表达式。
        isinstance(object_phase, dict)  # 阶段载荷必须是对象。
        and REQUIRED_REMOTE_FIELDS.issubset(object_phase)  # 对象必须包含公开最小字段。
    )  # 远程阶段形状结论。

    # 阶段名是唯一公开定位信息，路径和日志内容不进入错误。
    if not bool_phase_shape_valid:

        # 缺失阶段或错误类型都统一为 schema 错误。
        return [evidence_error("TEST_EVIDENCE_SCHEMA", f"remote pytest phase is incomplete: {str_phase}")]

    # 合法阶段不产生结构错误。
    return []

# 远程阶段执行值只验证摘要、退出码、计数和失败状态。
def _validate_remote_phase_values(str_phase: str, dict_phase: dict[str, Any]) -> list[str]:
    """检查远程阶段的命令摘要、退出码和用例计数。

    参数：str_phase 为阶段名。
    参数：dict_phase 为字段完整的阶段对象。
    返回：阶段值错误列表。
    """

    # 阶段值 helper 保持四类错误相互独立。
    list_errors: list[str] = []  # 远程阶段值诊断。

    # 命令摘要必须是固定长度的十六进制 SHA-256。
    str_command_hash: str | None = dict_phase.get("command_hash")  # 远程阶段命令摘要。

    # 命令摘要 helper 的结果决定是否可以审计该阶段命令。
    bool_command_hash_valid = _is_sha256_text(str_command_hash)  # 远程命令摘要结论。

    # 非法命令摘要不能形成可审计的阶段证据。
    if not bool_command_hash_valid:

        # 阶段名可公开，摘要值不可回显。
        list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", f"remote command hash is invalid: {str_phase}"))

    # 退出码必须是非布尔整数。
    object_exit_code: Any = dict_phase.get("exit_code")  # 远程阶段退出码。

    # 退出码类型结论独立于非零失败结论。
    bool_exit_code_valid = (  # 远程退出码类型判定表达式。
        isinstance(object_exit_code, int)  # 退出码必须属于整数类型。
        and not isinstance(object_exit_code, bool)  # 布尔值不得伪装退出码。
    )  # 远程退出码类型结论。

    # 非法退出码单独报告 schema 错误。
    if not bool_exit_code_valid:

        # 不把 Python 的 bool 子类语义当作退出码。
        list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", f"remote exit code is invalid: {str_phase}"))

    # 计数必须是非布尔非负整数。
    object_count: Any = dict_phase.get("count")  # 远程阶段用例计数。

    # 阶段计数必须与退出码一样拒绝布尔值。
    bool_count_valid = is_non_negative_integer(object_count)  # 远程计数类型结论。

    # 非法计数不能进入阶段摘要。
    if not bool_count_valid:

        # 只报告阶段定位和固定错误码。
        list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", f"remote test count is invalid: {str_phase}"))

    # 合法但非零的退出码表示该阶段失败。
    if bool_exit_code_valid and object_exit_code != 0:

        # 不返回命令文本或远程日志。
        list_errors.append(evidence_error("TEST_EVIDENCE_REMOTE_FAILURE", f"remote pytest failed: {str_phase}"))

    # 返回阶段执行值诊断。
    return list_errors

# 远程阶段 freshness 只比较 UTC 时间，不暴露时间原文。
def _validate_remote_phase_freshness(
    str_phase: str,
    dict_phase: dict[str, Any],
    datetime_now: datetime,
    int_freshness_seconds: int,
) -> list[str]:
    """检查远程阶段时间戳是否位于 freshness 窗口内。

    参数：str_phase 为阶段名。
    参数：dict_phase 为字段完整的阶段对象。
    参数：datetime_now 为规范化后的当前 UTC 时间。
    参数：int_freshness_seconds 为最大允许证据年龄。
    返回：时间格式或 freshness 错误列表。
    """

    # 解析阶段时间并拒绝无时区时间。
    list_errors: list[str] = []  # 远程阶段时间诊断。

    # 收据时间字段先转换为统一的 UTC 类型。
    value_phase_datetime: datetime | None = parse_utc_timestamp(  # 远程阶段时间解析结果。
        str(dict_phase.get("timestamp", ""))  # 只读取公开时间字段。
    )  # 远程阶段完成时间。

    # 无效时间不能证明 freshness。
    if value_phase_datetime is None:

        # 阶段名足以定位收据字段，不返回具体原文。
        return [evidence_error("TEST_EVIDENCE_FRESHNESS", f"remote timestamp is invalid: {str_phase}")]

    # 当前 UTC 与阶段 UTC 的差值构成证据年龄。
    float_age_seconds: float = (datetime_now - value_phase_datetime).total_seconds()  # 远程阶段证据年龄。

    # 未来时间或超窗时间都视为不新鲜。
    bool_timestamp_fresh = 0 <= float_age_seconds <= int_freshness_seconds  # 远程 freshness 结论。

    # 不回显精确时间，只返回稳定 freshness 错误。
    if not bool_timestamp_fresh:

        # 过期或未来阶段必须重新签发证据。
        list_errors.append(evidence_error("TEST_EVIDENCE_FRESHNESS", f"remote pytest is stale: {str_phase}"))

    # 返回阶段时间诊断。
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

    # 结构错误必须先返回，避免把非对象当作阶段映射读取。
    list_errors: list[str] = _validate_remote_phase_shape(str_phase, object_phase)  # 阶段结构诊断。

    # 结构不完整时保留单一错误，和历史收据行为一致。
    if list_errors:

        # 调用方只需修复公开阶段字段集合。
        return list_errors

    # 形状 helper 已经确认字典类型，局部类型绑定供后续 helper 使用。
    dict_phase: dict[str, Any] = object_phase  # 远程阶段字段映射。

    # 追加命令、退出码和计数错误。
    list_errors.extend(_validate_remote_phase_values(str_phase, dict_phase))

    # 追加阶段时间和 freshness 错误。
    list_errors.extend(
        _validate_remote_phase_freshness(
            str_phase,
            dict_phase,
            datetime_now,
            int_freshness_seconds,
        )
    )

    # 返回当前阶段的全部脱敏错误。
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
    value_current_datetime: datetime | None = parse_utc_timestamp(str_now_utc)  # 规范化当前 UTC。

    # 非对象载荷使用空映射完成稳定阶段循环。
    dict_remote: dict[str, Any] = (  # 安全阶段映射选择表达式。
        object_remote_pytest if isinstance(object_remote_pytest, dict) else {}  # 非对象降级为空映射。
    )  # 安全阶段映射。

    # 顶层结构错误单独记录。
    list_errors: list[str] = (  # 远程聚合诊断。
        []
        if isinstance(object_remote_pytest, dict)  # 合法对象无需结构错误。
        else [evidence_error("TEST_EVIDENCE_SCHEMA", "remote pytest evidence must be an object")]  # 非对象诊断。
    )

    # 当前时间无效时记录一次聚合错误。
    if value_current_datetime is None:

        # 使用 epoch 占位只为保持 helper 类型稳定，阶段仍会由聚合错误阻断。
        value_current_datetime = datetime.fromtimestamp(0, tz=timezone.utc)  # 不可信时间占位。

        # 调用方必须提供带时区的当前 UTC。
        list_errors.append(evidence_error("TEST_EVIDENCE_FRESHNESS", "current UTC timestamp is invalid"))

    # 每个固定阶段独立验证。
    for str_phase in REQUIRED_REMOTE_PHASES:

        # 阶段 helper 返回的错误直接追加。
        list_errors.extend(
            validate_remote_phase(
                str_phase,  # 当前固定阶段名。
                dict_remote.get(str_phase),  # 当前阶段载荷。
                value_current_datetime,  # 已规范化或占位的 UTC。
                int_freshness_seconds,  # 最大允许年龄。
            )
        )

    # 摘要只保留允许的聚合远程统计。
    dict_summary: dict[str, Any] = {  # 脱敏远程阶段统计。
        str_phase: {  # 当前阶段允许公开的聚合统计。
            "exit_code": dict_remote.get(str_phase, {}).get("exit_code"),  # 远程退出码。
            "count": dict_remote.get(str_phase, {}).get("count"),  # 远程聚合用例计数。
            "timestamp": dict_remote.get(str_phase, {}).get("timestamp"),  # 远程完成时间。
        }
        for str_phase in REQUIRED_REMOTE_PHASES  # 按固定三阶段顺序生成摘要。
    }

    # 字典字段避免调用方依赖二元组位置语义。
    return {"errors": list_errors, "summary": dict_summary}

# 本地收据可携带治理快照；项目级入口还会读取权威治理文件复核。
def _validate_local_payload(
    dict_receipt: dict[str, Any],
    str_expected_tests_tree_hash: str,
    str_expected_source_manifest_hash: str,
    str_now_utc: str,
    int_freshness_seconds: int,
    path_project: Path | None,
) -> dict[str, Any]:
    """验证扁平本地收据并生成低敏结果。

    参数：dict_receipt 为本地收据对象。
    参数：str_expected_tests_tree_hash 为当前 tests 树摘要。
    参数：str_expected_source_manifest_hash 为当前源码清单摘要。
    参数：str_now_utc 为 freshness 比较基准。
    参数：int_freshness_seconds 为最大证据年龄。
    参数：path_project 为可选项目根；存在时复核权威治理文件。
    返回：包含 ok、errors 和 summary 的本地验证结果。
    """

    # 先聚合扁平字段、仓库摘要和提交绑定错误。
    list_errors: list[str] = validate_local_receipt_metadata(  # 本地元数据和仓库绑定诊断。
        dict_receipt,  # 本地收据原始对象。
        str_expected_tests_tree_hash,  # 当前 tests 树摘要。
        str_expected_source_manifest_hash,  # 当前源码清单摘要。
    )

    # 治理快照冲突并入本地合同的统一错误列表。
    list_errors.extend(validate_local_governance_fields(dict_receipt))

    # runner、命令、计数和 freshness 共同构成本地完整结果。
    dict_local_result: dict[str, Any] = validate_local_test_result(  # 本地执行结果诊断。
        dict_receipt,  # 执行器、命令和计数来自同一份本地收据。
        str_now_utc,  # 当前 UTC 用于计算本地证据年龄。
        int_freshness_seconds,  # 本地合同允许的最大证据年龄。
    )

    # 本地执行器的错误与元数据错误使用同一发布结果。
    list_errors.extend(dict_local_result["errors"])

    # 项目入口必须重新读取权威治理文件，纯 payload 调用可不带项目路径。
    if path_project is not None:

        # 本地证据不能依赖收据自带的治理快照通过项目门禁。
        list_errors.extend(validate_local_project_governance(path_project))

    # 本地摘要只包含低敏执行统计，不公开哈希、路径或治理原文。
    return {
        "ok": not list_errors,
        "errors": list_errors,
        "summary": dict_local_result["summary"],
    }

# v2 pytest 收据的仓库摘要绑定在 payload 层完成，防止只验格式。
def _validate_pytest_payload(
    dict_receipt: dict[str, Any],
    str_expected_tests_tree_hash: str,
    str_expected_source_manifest_hash: str,
) -> dict[str, Any]:
    """验证 pytest v2 收据与当前 tests、源码摘要的绑定。

    参数：dict_receipt 为 pytest v2 收据对象。
    参数：str_expected_tests_tree_hash 为当前 tests 树摘要。
    参数：str_expected_source_manifest_hash 为当前源码清单摘要。
    返回：包含 ok、errors 和 summary 的 pytest 验证结果。
    """

    # 先运行 v2 本体校验，再追加当前仓库绑定结论。
    dict_result: dict[str, Any] = validate_pytest_receipt(dict_receipt)  # pytest 结构和执行结果。

    # 绑定错误单独收集，避免覆盖 v2 本体诊断。
    list_binding_errors: list[str] = []  # pytest 仓库绑定诊断。

    # tests 树摘要必须等于当前项目事实。
    if dict_receipt.get("tests_tree_sha256") != str_expected_tests_tree_hash:

        # 不回显实际摘要值。
        list_binding_errors.append(evidence_error("PYTEST_RECEIPT_TESTS_HASH", "tests tree hash does not match"))

    # 非测试源码摘要同样必须等于当前项目事实。
    if dict_receipt.get("source_manifest_sha256") != str_expected_source_manifest_hash:

        # 源码漂移要求重新执行完整 pytest。
        list_binding_errors.append(evidence_error("PYTEST_RECEIPT_SOURCE_HASH", "source manifest hash does not match"))

    # 合并绑定错误并重算最终 ok 状态。
    dict_result["errors"] = list(dict_result["errors"]) + list_binding_errors  # pytest 全部错误诊断。

    # 当前仓库绑定失败时覆盖本体验证的成功状态。
    dict_result["ok"] = not dict_result["errors"]  # pytest 最终通过结论。

    # 返回 v2 脱敏结果。
    return dict_result

# schema=1 旧不透明收据仅允许在 immutable history 复核路径继续存在。
def _validate_legacy_payload(
    dict_receipt: dict[str, Any],
    str_expected_tests_tree_hash: str,
    str_expected_source_manifest_hash: str,
    str_now_utc: str,
    int_freshness_seconds: int,
) -> dict[str, Any]:
    """复核历史 schema=1 远程阶段收据。

    参数：dict_receipt 为历史不透明收据对象。
    参数：str_expected_tests_tree_hash 为当前 tests 树摘要。
    参数：str_expected_source_manifest_hash 为当前源码清单摘要。
    参数：str_now_utc 为 freshness 比较基准。
    参数：int_freshness_seconds 为最大证据年龄。
    返回：包含 ok、errors 和 summary 的历史验证结果。
    """

    # 旧收据元数据和三阶段远程结果相互独立检查。
    list_errors: list[str] = validate_receipt_metadata(  # 历史元数据诊断。
        dict_receipt,  # 历史 schema 的元数据来源。
        str_expected_tests_tree_hash,  # 历史 tests tree 对象绑定。
        str_expected_source_manifest_hash,  # 历史收据对应的源码状态绑定。
    )

    # 单次调用同时取得远程阻断错误和脱敏阶段摘要。
    dict_remote_result: dict[str, Any] = validate_remote_pytest(  # 历史远程阶段结果。
        dict_receipt.get("remote_pytest"),  # 历史收据中的三阶段载荷。
        str_now_utc,  # 阶段时间使用的当前 UTC 基准。
        int_freshness_seconds,  # 历史合同的 freshness 时间窗。
    )

    # 历史远程阶段错误继续沿用旧合同的聚合语义。
    list_errors.extend(dict_remote_result["errors"])

    # 历史摘要保留既有低敏文件规模和阶段统计字段。
    dict_summary: dict[str, Any] = {
        "tests_tree_hash": dict_receipt.get("tests_tree_hash", ""),  # 历史 tests 树摘要。
        "tests_file_count": dict_receipt.get("tests_file_count", 0),  # 历史 tests 文件数量。
        "tests_byte_count": dict_receipt.get("tests_byte_count", 0),  # 历史 tests 字节数量。
        "remote_pytest": dict_remote_result["summary"],  # 历史远程阶段摘要。
    }  # 历史低敏摘要。

    # 返回旧合同的脱敏结果。
    return {"ok": not list_errors, "errors": list_errors, "summary": dict_summary}

# 公开验证器只消费调用方提供的 opaque hash 和时间事实。
def validate_test_evidence_payload(
    dict_receipt: dict[str, Any],

    # 星号之后的字段必须由调用方按名称绑定。
    *,

    # 这三项摘要和时间事实决定当前收据能否复用。
    str_expected_tests_tree_hash: str,
    str_expected_source_manifest_hash: str,
    str_now_utc: str,
    int_freshness_seconds: int,

    # 项目路径和历史开关只扩展项目级校验边界。
    path_project: Path | None = None,
    bool_immutable_history: bool = False,
) -> dict[str, Any]:
    """验证远程或本地测试收据的结构、绑定和 freshness。

    参数：dict_receipt 为远程或本地测试收据对象。
    参数：str_expected_tests_tree_hash 为当前 tests 树哈希。
    参数：str_expected_source_manifest_hash 为当前非测试源码清单哈希。
    参数：str_now_utc 为当前 UTC 时间。
    参数：int_freshness_seconds 为最大证据年龄秒数。
    参数：path_project 为可选项目根；本地发布路径用它复核治理文件。
    参数：bool_immutable_history 为是否允许旧 schema=1 历史收据。
    返回：包含 ok、errors 和脱敏 summary 的验证结果。
    """

    # 公开合同要求对象；非对象立即 fail closed。
    if not isinstance(dict_receipt, dict):

        # 不对非对象执行任何字段访问。
        return {
            "ok": False,
            "errors": [evidence_error("TEST_EVIDENCE_SCHEMA", "test evidence payload must be an object")],
        }

    # local-test-evidence 只允许显式 immutable-history 复核，活动门禁统一要求 pytest。
    if dict_receipt.get("kind") == LOCAL_EVIDENCE_KIND:

        # 活动发布不得把本地 unittest 收据冒充完整 pytest 收据。
        if not bool_immutable_history:

            # 固定错误码让 release、publication 和 install 统一 fail closed。
            return {
                "ok": False,
                "errors": [evidence_error("PYTEST_RECEIPT_REQUIRED", "full pytest receipt is required")],
                "summary": {},
            }

        # 历史本地收据只在显式兼容路径复核扁平字段、绑定和治理。
        return _validate_local_payload(
            dict_receipt,
            str_expected_tests_tree_hash,
            str_expected_source_manifest_hash,
            str_now_utc,
            int_freshness_seconds,
            path_project,
        )

    # runner 或 schema_version=2 明确进入完整 pytest v2 合同。
    if "runner" in dict_receipt or dict_receipt.get("schema_version") == 2:

        # pytest 位置字段不参与验证，仓库摘要由 helper 绑定。
        return _validate_pytest_payload(
            dict_receipt,
            str_expected_tests_tree_hash,
            str_expected_source_manifest_hash,
        )

    # 其他 schema=1 收据只有 immutable history 复核被显式允许时才可读取。
    if not bool_immutable_history:

        # 活动发布缺少完整 pytest 时必须 fail closed。
        return {
            "ok": False,
            "errors": [evidence_error("PYTEST_RECEIPT_REQUIRED", "full pytest receipt is required")],
            "summary": {},
        }

    # immutable history 路径只复核旧远程阶段收据。
    return _validate_legacy_payload(
        dict_receipt,
        str_expected_tests_tree_hash,
        str_expected_source_manifest_hash,
        str_now_utc,
        int_freshness_seconds,
    )

# 依赖导入放在本模块函数定义之后，避免 facade 再导入 helper 时出现部分初始化循环。
try:
    # 导入当前验证职责实际使用的核心合同和错误入口。
    from evidence_validation import (
        LOCAL_EVIDENCE_KIND,
        REQUIRED_REMOTE_FIELDS,
        REQUIRED_REMOTE_PHASES,
        evidence_error,
        is_non_negative_integer,
    )

    # 继续导入本职责剩余的核心合同名称。
    from evidence_validation import (
        parse_utc_timestamp,
        validate_local_governance_fields,
        validate_local_project_governance,
        validate_local_receipt_metadata,
        validate_local_test_result,
    )

    # 继续导入本职责剩余的核心合同名称。
    from evidence_validation import validate_receipt_metadata

    # 导入跨职责的稳定公共入口。
    from pytest_receipt_validation import validate_pytest_receipt

# 包内执行时回退到同一职责目录的相对依赖。
except ImportError:
    # 包内执行时导入同一职责的核心合同和错误入口。
    from .evidence_validation import (
        LOCAL_EVIDENCE_KIND,
        REQUIRED_REMOTE_FIELDS,
        REQUIRED_REMOTE_PHASES,
        evidence_error,
        is_non_negative_integer,
    )

    # 继续导入本职责剩余的相对合同名称。
    from .evidence_validation import (
        parse_utc_timestamp,
        validate_local_governance_fields,
        validate_local_project_governance,
        validate_local_receipt_metadata,
        validate_local_test_result,
    )

    # 继续导入本职责剩余的相对合同名称。
    from .evidence_validation import validate_receipt_metadata

    # 导入跨职责的相对公共入口。
    from .pytest_receipt_validation import validate_pytest_receipt
