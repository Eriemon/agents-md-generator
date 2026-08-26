"""校验 schema-2 pytest 收据字段、命令和执行计数。"""

# 标准库提供本职责的类型、摘要和时间处理能力。
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

# pytest 收据字段函数由本模块开始。
def _is_sha256_text(object_value: Any) -> bool:
    """判断值是否为合法的 SHA-256 十六进制文本。

    参数：object_value 为待检查的摘要值。
    返回：值为 64 位十六进制字符串时为 True。
    """

    # 大小写只影响表示，摘要长度和字符集必须固定。
    bool_hash_valid = (  # SHA-256 字符串判定表达式。
        isinstance(object_value, str)  # 摘要必须是字符串。
        and len(object_value) == 64  # 摘要必须固定为 64 个字符。
        and all(str_character in "0123456789abcdef" for str_character in object_value.lower())  # 字符必须是十六进制。
    )  # SHA-256 文本格式结论。

    # 返回格式检查结果而不回显摘要内容。
    return bool_hash_valid

# pytest v2 的计数检查复用统一非负整数判定。
def _validate_pytest_count(dict_receipt: dict[str, Any], str_field: str, list_errors: list[str]) -> None:
    """校验一个 pytest 聚合计数的整数和非负不变量。

    参数：dict_receipt 为 pytest 收据对象。
    参数：str_field 为待验证的计数字段名。
    参数：list_errors 为调用方共享的错误列表。
    返回：本函数只追加错误，不返回业务值。
    """

    # 读取单个字段以保持错误定位在公开字段名层面。
    count_value: Any = dict_receipt.get(str_field)  # 当前字段值仅用于类型判定。

    # 非法计数统一追加 schema 错误。
    if not is_non_negative_integer(count_value):

        # 仅回显合同字段名，不泄漏测试规模。
        list_errors.append(evidence_error("PYTEST_RECEIPT_SCHEMA", f"pytest count is invalid: {str_field}"))

# serial 与第一阶段 xdist 模式使用同一 schema-2 入口并保持严格命令绑定。
def _pytest_command_contract(dict_receipt: dict[str, Any]) -> tuple[str | None, list[str]]:
    """解析 schema-2 收据允许的 pytest 逻辑命令。

    参数：dict_receipt 为 pytest 收据对象。
    返回：期望逻辑命令；未知命令 ID 时为空，并附带字段级错误列表。
    """

    # 命令 ID 决定 serial 兼容路径或受控 xdist 扩展路径。
    str_command_id = str(dict_receipt.get("command_id", ""))  # 收据声明的命令标识。

    # 旧 schema-2 收据继续使用原始 serial 命令和字段集合。
    if str_command_id == PYTEST_FULL_COMMAND_ID:

        # serial 收据不得混入并行字段，避免命令哈希与执行形态相互矛盾。
        list_errors = [  # serial 收据中的并行字段诊断。
            evidence_error("PYTEST_RECEIPT_COMMAND", f"pytest serial field is unexpected: {str_field}")  # 混入字段诊断。
            for str_field in sorted(PYTEST_XDIST_FIELDS)  # 稳定顺序检查并行字段。
            if str_field in dict_receipt  # 只报告实际混入的字段。
        ]

        # serial 逻辑命令保持历史 schema-2 的精确摘要输入。
        return PYTEST_FULL_COMMAND, list_errors

    # 任何未登记命令 ID 都不能扩展完整套件的执行形态。
    if str_command_id != PYTEST_XDIST_COMMAND_ID:

        # 未知 ID 不提供可用于摘要比较的候选命令。
        return None, [evidence_error("PYTEST_RECEIPT_COMMAND", "pytest receipt command_id is invalid")]

    # xdist 执行模式和分发方式固定，worker 数允许历史值或四到八。
    dict_expected_fields: dict[str, Any] = {  # 受控 xdist 字段和值。
        "execution_mode": "xdist",  # 并行执行器身份。
        "distribution": PYTEST_XDIST_DISTRIBUTION,  # 同文件固定分发方式。
    }

    # 每个错误指向具体字段，便于签发器修正而不回显命令原文。
    list_errors = [  # xdist 执行形态诊断。
        evidence_error("PYTEST_RECEIPT_COMMAND", f"pytest xdist field is invalid: {str_field}")  # 当前字段诊断。
        for str_field, object_expected in dict_expected_fields.items()  # 遍历固定字段合同。
        if dict_receipt.get(str_field) != object_expected  # 缺失和值漂移统一失败。
    ]

    # worker 数单独检查类型与批准范围，便于拒绝三或九进程请求。
    object_worker_count: Any = dict_receipt.get("worker_count")  # 收据声明的并发数量。

    # 非法 worker 数不能参与命令重建或哈希比较。
    if not _is_allowed_xdist_worker_count(object_worker_count):

        # 只公开字段级错误，不回显任何远程路径或资源信息。
        list_errors.append(evidence_error("PYTEST_RECEIPT_COMMAND", "pytest xdist worker_count is invalid"))

    # 字段错误不改变唯一候选命令，调用方仍可独立报告命令摘要问题。
    int_worker_count = (  # 用于命令重建的安全 worker 数。
        object_worker_count  # 已验证的收据并发数量。
        if _is_allowed_xdist_worker_count(object_worker_count)  # 仅接受已经通过范围检查的整数。
        else PYTEST_XDIST_LEGACY_WORKER_COUNT  # 非法值回退到历史命令以保持错误稳定。
    )  # 安全命令 worker 数。

    # 通过动态 worker 数绑定唯一逻辑命令文本。
    return _xdist_command_text(int_worker_count), list_errors

# pytest v2 的字段、runner、suite 和命令身份分开检查。
def _validate_pytest_contract_fields(dict_receipt: dict[str, Any]) -> list[str]:
    """检查 pytest 收据的公开字段和固定命令身份。

    参数：dict_receipt 为 pytest 收据对象。
    返回：字段、runner、suite 或命令错误列表。
    """

    # 字段 helper 保留 v2 的 schema_version 必填兼容行为。
    list_errors: list[str] = []  # pytest 合同字段诊断。

    # 缺失字段只公开固定合同字段名称。
    list_missing_fields: list[str] = sorted(PYTEST_RECEIPT_FIELDS - set(dict_receipt))  # pytest 缺失字段。

    # 缺失字段会让收据无法完成 v2 校验。
    if list_missing_fields:

        # 错误文本不携带服务器、路径或命令输出。
        list_errors.append(
            evidence_error(
                "PYTEST_RECEIPT_SCHEMA",
                "pytest receipt is missing: " + ", ".join(list_missing_fields),
            )
        )

    # schema_version 必须明确使用 v2。
    bool_schema_valid = dict_receipt.get("schema_version") == 2  # pytest schema 版本结论。

    # 错误版本或缺失版本不能混入完整 pytest 收据路径。
    if not bool_schema_valid:

        # 只公开版本合同错误。
        list_errors.append(evidence_error("PYTEST_RECEIPT_SCHEMA", "pytest receipt schema_version is invalid"))

    # runner 和 suite 固定为完整 pytest 执行事实。
    bool_suite_identity_valid = (  # pytest 执行身份判定表达式。
        dict_receipt.get("runner") == "pytest"  # runner 必须锁定为 pytest。
        and dict_receipt.get("suite") == "full"  # suite 必须覆盖完整套件。
    )  # pytest 执行身份结论。

    # 任何其他执行器或套件范围都不能通过 v2 门禁。
    if not bool_suite_identity_valid:

        # 不回显收据中自报的 runner 或 suite。
        list_errors.append(evidence_error("PYTEST_RECEIPT_SCHEMA", "pytest receipt runner or suite is invalid"))

    # 命令 helper 同时处理 serial 兼容路径和受控 xdist 字段。
    tuple_command_contract = _pytest_command_contract(dict_receipt)  # 逻辑命令与字段诊断。

    # 字段级问题必须保留，不能被后续摘要错误覆盖。
    list_errors.extend(tuple_command_contract[1])

    # 未知命令 ID 没有可接受摘要；已知命令则重建规范 SHA-256。
    str_expected_command: str | None = tuple_command_contract[0]  # 收据应绑定的逻辑命令。

    # 只有已登记命令才具备可计算的可信摘要。
    str_expected_command_sha256: str | None = (  # 期望命令摘要。
        hashlib.sha256(str_expected_command.encode("utf-8")).hexdigest()  # 已登记逻辑命令摘要。
        if str_expected_command is not None  # 未知 ID 不构造伪命令摘要。
        else None  # 未知命令已经由 helper 报错。
    )

    # 命令摘要必须由当前执行形态对应的固定逻辑命令计算。
    if str_expected_command_sha256 is not None and dict_receipt.get("command_sha256") != str_expected_command_sha256:

        # 不回显命令正文或调用方提交的摘要。
        list_errors.append(evidence_error("PYTEST_RECEIPT_COMMAND", "pytest command_sha256 is invalid"))

    # 返回公开字段和命令身份层诊断。
    return list_errors

# pytest v2 的退出码和七类计数必须形成完整终态。
def _validate_pytest_execution_fields(dict_receipt: dict[str, Any]) -> list[str]:
    """检查 pytest 收据的退出码和统计守恒关系。

    参数：dict_receipt 为 pytest 收据对象。
    返回：退出码、计数类型或计数守恒错误列表。
    """

    # 执行 helper 先记录退出状态，再验证统计关系。
    list_errors: list[str] = []  # pytest 执行结果诊断。

    # 非布尔整数才是合法退出码。
    object_exit_code: Any = dict_receipt.get("exit_code")  # pytest 完整套件退出码。

    # 类型判定先于非零失败判定，避免把错误类型当作成功。
    bool_exit_code_valid = (  # pytest 退出码类型判定表达式。
        isinstance(object_exit_code, int)  # pytest 退出状态必须保持数值语义。
        and not isinstance(object_exit_code, bool)  # bool 子类不能冒充套件退出状态。
    )  # pytest 退出码合法性结论。

    # 类型错误不能被当作成功退出。
    if not bool_exit_code_valid:

        # 错误载荷只包含稳定的 schema 错误。
        list_errors.append(evidence_error("PYTEST_RECEIPT_SCHEMA", "pytest exit code is invalid"))

    # 合法但非零退出码代表完整套件失败。
    if bool_exit_code_valid and object_exit_code != 0:

        # 非零结果阻断发布。
        list_errors.append(evidence_error("PYTEST_RECEIPT_FAILURE", "pytest full suite failed"))

    # 每个公开计数都必须是非负整数。
    for str_field in PYTEST_COUNT_FIELDS:

        # 计数 helper 只追加固定 schema 错误。
        _validate_pytest_count(dict_receipt, str_field, list_errors)

    # 只有字段类型全部有效时才计算守恒关系。
    bool_counts_valid = all(  # pytest 计数类型判定表达式。
        is_non_negative_integer(dict_receipt.get(str_field))  # 每个公开计数都必须合法。
        for str_field in PYTEST_COUNT_FIELDS  # 遍历固定的计数集合。
    )  # pytest 计数类型结论。

    # 类型错误已经报告，避免用 None 参与求和。
    if bool_counts_valid:

        # collected 必须等于其余六类终态之和。
        int_collected: int = int(dict_receipt["collected"])  # collected 字段提供完整套件总量。

        # 终态总数提供计数守恒的右侧基准。
        int_terminal: int = sum(  # 终态字段之和用于守恒比较。
            int(dict_receipt[str_field])  # 当前终态字段的整数值。
            for str_field in PYTEST_COUNT_FIELDS[1:]  # 排除 collected 后遍历终态字段。
        )  # pytest 终态计数之和。

        # 不守恒结果无法代表完整 pytest 套件。
        if int_collected != int_terminal:

            # 计数不平衡只公开固定错误码。
            list_errors.append(evidence_error("PYTEST_RECEIPT_COUNTS", "pytest counts do not balance"))

        # 零收集不能形成可审计的完整测试结果。
        if int_collected <= 0:

            # 空套件同样阻断发布。
            list_errors.append(evidence_error("PYTEST_RECEIPT_COUNTS", "pytest receipt collected count is empty"))

    # 返回 pytest 执行层诊断。
    return list_errors

# pytest v2 必须绑定规范 tests、源码摘要和测试提交。
def _validate_pytest_binding_fields(dict_receipt: dict[str, Any]) -> list[str]:
    """检查 pytest 收据的摘要格式与测试提交字段。

    参数：dict_receipt 为 pytest 收据对象。
    返回：摘要或提交绑定错误列表。
    """

    # 绑定 helper 只验证格式，当前仓库值在 payload 层比较。
    list_errors: list[str] = []  # pytest 绑定诊断。

    # 两个公开摘要都必须是真实的 SHA-256 文本。
    for str_field in ("tests_tree_sha256", "source_manifest_sha256"):

        # 不合法摘要不能形成仓库状态绑定。
        if not _is_sha256_text(dict_receipt.get(str_field)):

            # 字段名是公开合同的一部分，可安全用于诊断。
            list_errors.append(evidence_error("PYTEST_RECEIPT_SCHEMA", f"pytest hash is invalid: {str_field}"))

    # pytest 历史提交字段必须是非空字符串。
    object_test_commit: Any = dict_receipt.get("test_commit")  # pytest 测试提交字段。

    # 提交字段只需先通过非空字符串约束，拓扑绑定在项目入口完成。
    bool_test_commit_valid = isinstance(object_test_commit, str) and bool(object_test_commit)  # pytest 提交结论。

    # 空提交字段不能绑定测试结果来源。
    if not bool_test_commit_valid:

        # 不回显提交字段内容。
        list_errors.append(evidence_error("PYTEST_RECEIPT_SCHEMA", "pytest test_commit is invalid"))

    # 返回摘要和提交层诊断。
    return list_errors

# pytest v2 摘要只公开低敏执行统计，不公开路径和服务器细节。
def _build_pytest_summary(dict_receipt: dict[str, Any]) -> dict[str, Any]:
    """构造 pytest 收据的脱敏摘要。

    参数：dict_receipt 为 pytest 收据对象。
    返回：供发布门禁展示的 pytest 聚合摘要。
    """

    # 固定字段白名单投影出低敏 pytest 摘要。
    dict_summary: dict[str, Any] = {
        str_field: dict_receipt.get(str_field)  # 当前低敏 pytest 字段。
        for str_field in PYTEST_SUMMARY_FIELDS  # 固定 pytest 摘要字段顺序。
    }  # pytest 安全摘要。

    # 只有受控并行收据公开执行形态，serial 摘要保持向后兼容。
    if dict_receipt.get("command_id") == PYTEST_XDIST_COMMAND_ID:

        # 三个低敏字段足以解释并行结果，不暴露命令文本或远程包装。
        dict_summary.update(  # 并行 pytest 执行形态摘要。
            {
                str_field: dict_receipt.get(str_field)  # 当前并行字段值。
                for str_field in sorted(PYTEST_XDIST_FIELDS)  # 稳定顺序投影允许字段。
            }
        )

    # 哈希、提交、路径和服务器细节不出现在公开摘要中。
    return dict_summary

# pytest 收据公开入口只编排字段、执行结果和绑定三层检查。
def _policy_mode(
    dict_policy_binding: dict[str, Any],
    dict_receipt: dict[str, Any],
) -> dict[str, Any] | None:
    """从 active policy 解析收据对应的 mode。

    参数：dict_policy_binding 为 policy 或活动绑定；dict_receipt 为待校验收据。
    返回：匹配的 mode 声明，无法匹配时返回 None。
    """

    # 兼容直接传入 policy 映射和包含 policy 的活动绑定。
    dict_policy = dict_policy_binding.get("policy", dict_policy_binding)  # 当前 policy 对象

    # 只从映射中读取模式列表，其他形状按空列表处理。
    list_modes = dict_policy.get("modes", []) if isinstance(dict_policy, dict) else []  # policy 模式列表

    # 优先使用 receipt 显式声明的 mode 名称。
    str_mode_name = str(dict_receipt.get("mode", "")).strip()  # receipt 声明的 policy 模式名称

    # 缺少 mode 时按 receipt suite 选择 policy 默认 mode。
    if not str_mode_name:

        # 读取 policy 默认模式映射。
        dict_defaults = dict_policy.get("default_modes", {}) if isinstance(dict_policy, dict) else {}  # 默认 mode 映射

        # 按 receipt suite 解析对应默认 mode。
        str_mode_name = str(dict_defaults.get(str(dict_receipt.get("suite", "")), "")).strip()  # 默认 mode 标识

    # 在 policy 模式列表中查找最终 mode 声明。
    return next(
        (
            item  # 当前 mode 声明
            for item in list_modes  # 遍历 policy 模式列表
            if isinstance(item, dict) and item.get("mode_name") == str_mode_name  # 匹配目标 mode
        ),
        None,  # 未匹配时返回空值
    )

# 依据 policy mode 校验字段、命令和活动摘要绑定。
def _validate_with_policy(
    dict_receipt: dict[str, Any],
    dict_policy_binding: dict[str, Any],
) -> dict[str, Any]:
    """按 active policy 校验 receipt 字段、命令摘要和绑定摘要。

    参数：dict_receipt 为待校验收据；dict_policy_binding 为 policy 与摘要绑定。
    返回：包含 ok、errors 和脱敏 summary 的结果映射。
    """

    # policy mode 决定 required/forbidden 字段和命令模板。
    dict_mode = _policy_mode(dict_policy_binding, dict_receipt)  # 当前收据匹配的 policy mode

    # 累计 policy、命令和绑定层错误。
    list_errors: list[str] = []  # 当前 receipt 错误列表

    # 未知 mode 不能回退到历史常量规则。
    if not isinstance(dict_mode, dict):

        # 记录 mode 解析失败并返回空摘要。
        list_errors.append(evidence_error("PYTEST_RECEIPT_COMMAND", "pytest receipt mode is invalid"))

        # 当前 mode 不可验证时停止后续 policy 字段检查。
        return {"ok": False, "errors": list_errors, "summary": {}}

    # 当前模式的字段集合完全来自 JSON policy。
    set_required = {str(item) for item in dict_mode.get("required_fields", [])}  # policy 必需字段集合

    # 读取 policy 禁止字段集合。
    set_forbidden = {str(item) for item in dict_mode.get("forbidden_fields", [])}  # policy 禁止字段集合

    # 计算 receipt 缺失和禁止字段差集。
    list_missing = sorted(set_required - set(dict_receipt))  # 缺失字段列表

    # 计算 receipt 命中的禁止字段集合。
    list_forbidden = sorted(set_forbidden & set(dict_receipt))  # 禁止字段列表

    # 缺失字段阻断当前 receipt。
    if list_missing:

        # 记录缺失字段但继续收集其他 policy 诊断。
        list_errors.append(
            evidence_error("PYTEST_RECEIPT_SCHEMA", "pytest receipt is missing: " + ", ".join(list_missing))
        )

    # 禁止字段阻断当前 receipt。
    if list_forbidden:

        # 记录禁止字段命中信息。
        list_errors.append(
            evidence_error("PYTEST_RECEIPT_SCHEMA", "pytest receipt has forbidden fields")
        )

    # mode identity和 runner/suite必须与 policy declaration一致。
    for str_field in ("command_id", "runner", "suite"):

        # 读取当前字段的 policy 期望值。
        object_expected = dict_mode.get(str_field)  # policy 字段期望值

        # 已声明期望值时严格比较 receipt 内容。
        if object_expected is not None and dict_receipt.get(str_field) != object_expected:

            # 记录字段漂移但继续检查命令和摘要。
            list_errors.append(evidence_error("PYTEST_RECEIPT_COMMAND", "pytest policy field is invalid"))

    # 使用 policy template 重建逻辑命令，再比较 command_sha256。
    dict_rules = dict_mode.get("parameter_rules", {})  # policy 参数规则对象

    # 仅投影 policy 声明的命令模板参数。
    dict_parameters = {
        str_name: dict_receipt.get(str_name)  # 当前模板参数值
        for str_name in dict_rules  # policy 声明的参数名称
        if isinstance(dict_rules, dict)  # 仅遍历映射规则
    }

    # 依次展开命令模板并计算其摘要。
    try:

        # 读取 policy 命令模板文本。
        str_template = str(dict_mode.get("command_template", ""))  # policy 命令模板

        # 用 receipt 参数展开逻辑命令。
        str_command = str_template.format(**dict_parameters)  # 展开的逻辑命令

        # 计算逻辑命令的 SHA-256 摘要供 receipt 比对。
        str_command_hash = hashlib.sha256(str_command.encode("utf-8")).hexdigest()  # 命令摘要

    # 模板字段缺失或格式错误时记录空摘要。
    except (KeyError, ValueError):

        # 空摘要将由下一步统一报告命令错误。
        str_command_hash = ""  # 无法生成的命令摘要

    # receipt 命令摘要必须与 policy 重建结果一致。
    if not str_command_hash or dict_receipt.get("command_sha256") != str_command_hash:

        # 记录命令摘要不匹配诊断。
        list_errors.append(evidence_error("PYTEST_RECEIPT_COMMAND", "pytest command_sha256 is invalid"))

    # active receipt extension必须绑定当前 policy/runtime manifest摘要。
    for str_field, str_binding_key in (
        ("policy_sha256", "policy_sha256"),
        ("runtime_manifest_sha256", "runtime_manifest_sha256"),
    ):

        # 读取活动 binding 对应的摘要期望值。
        object_expected = dict_policy_binding.get(str_binding_key)  # 当前绑定摘要

        # 已声明 binding 摘要时拒绝 stale receipt。
        if object_expected is not None and dict_receipt.get(str_field) != object_expected:

            # 记录当前 receipt 与活动 policy/runtime 摘要不一致。
            list_errors.append(evidence_error("PYTEST_RECEIPT_BINDING", "pytest receipt binding is stale"))

    # 返回脱敏字段摘要，不暴露 command 原文或路径。
    dict_summary = {
        str_field: dict_receipt.get(str_field)  # 脱敏摘要字段值
        for str_field in ("runner", "suite", "command_id", "exit_code", "collected", "passed", "failed")  # 摘要字段白名单
        if str_field in dict_receipt  # 只保留 receipt 已提供的字段
    }

    # 返回 policy 校验结果与脱敏摘要。
    return {"ok": not list_errors, "errors": list_errors, "summary": dict_summary}

# 公开入口按是否提供活动 policy 选择参数化或历史兼容校验。
def validate_pytest_receipt(
    dict_receipt: dict[str, Any],
    *,
    policy: dict[str, Any] | None = None,
    binding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """验证完整 pytest 收据的结构和结果。

    参数：dict_receipt 为 pytest 收据对象；policy 与 binding 为可选活动合同覆盖。
    返回：包含 ok、errors 和脱敏 summary 的验证结果。
    异常：输入类型错误通过结构化 errors 返回，不向调用方泄露路径或命令原文。
    """

    # 非对象输入立即 fail closed，避免调用方误用任意 JSON 值。
    if not isinstance(dict_receipt, dict):

        # 只返回固定 schema 错误。
        return {
            "ok": False,
            "errors": [evidence_error("PYTEST_RECEIPT_SCHEMA", "pytest receipt must be an object")],
        }

    # active policy caller 走配置驱动校验，不回退到历史常量路径。
    if policy is not None or binding is not None:

        # 以显式 policy 为主，缺省使用空绑定等待后续字段校验。
        dict_policy_binding = policy if policy is not None else {}  # 活动 policy 绑定

        # 有 runtime binding 时复制映射，避免修改调用方传入对象。
        if binding is not None:

            # 复制 policy 绑定并注入当前 manifest 摘要。
            dict_policy_binding = dict(dict_policy_binding)  # 当前 receipt 的独立绑定

            # 将 manifest 摘要绑定到活动 receipt 校验。
            dict_policy_binding["runtime_manifest_sha256"] = binding.get("manifest_sha256")  # 当前 manifest 摘要

        # 参数化 policy 校验完全由活动合同负责。
        return _validate_with_policy(dict_receipt, dict_policy_binding)

    # 依次收集合约字段、执行状态和摘要绑定问题。
    list_errors: list[str] = _validate_pytest_contract_fields(dict_receipt)  # pytest 字段诊断。

    # 执行层保持退出码和计数错误相互独立。
    list_errors.extend(_validate_pytest_execution_fields(dict_receipt))

    # 绑定层只检查格式，payload 层再绑定当前仓库摘要。
    list_errors.extend(_validate_pytest_binding_fields(dict_receipt))

    # 返回稳定的 v2 pytest 机器协议。
    return {
        "ok": not list_errors,
        "errors": list_errors,
        "summary": _build_pytest_summary(dict_receipt),
    }

# 依赖导入放在本模块函数定义之后，避免 facade 再导入 helper 时出现部分初始化循环。
try:
    # 导入当前验证职责实际使用的核心合同和错误入口。
    from evidence_validation import (
        PYTEST_COUNT_FIELDS,
        PYTEST_FULL_COMMAND,
        PYTEST_FULL_COMMAND_ID,
        PYTEST_RECEIPT_FIELDS,
        PYTEST_SUMMARY_FIELDS,
    )

    # 继续导入本职责剩余的核心合同名称。
    from evidence_validation import (
        PYTEST_XDIST_COMMAND_ID,
        PYTEST_XDIST_DISTRIBUTION,
        PYTEST_XDIST_FIELDS,
        PYTEST_XDIST_LEGACY_WORKER_COUNT,
        _is_allowed_xdist_worker_count,
    )

    # 继续导入本职责剩余的核心合同名称。
    from evidence_validation import (
        _xdist_command_text,
        evidence_error,
        is_non_negative_integer,
    )

# 包内执行时回退到同一职责目录的相对依赖。
except ImportError:
    # 包内执行时导入同一职责的核心合同和错误入口。
    from .evidence_validation import (
        PYTEST_COUNT_FIELDS,
        PYTEST_FULL_COMMAND,
        PYTEST_FULL_COMMAND_ID,
        PYTEST_RECEIPT_FIELDS,
        PYTEST_SUMMARY_FIELDS,
    )

    # 继续导入本职责剩余的相对合同名称。
    from .evidence_validation import (
        PYTEST_XDIST_COMMAND_ID,
        PYTEST_XDIST_DISTRIBUTION,
        PYTEST_XDIST_FIELDS,
        PYTEST_XDIST_LEGACY_WORKER_COUNT,
        _is_allowed_xdist_worker_count,
    )

    # 继续导入本职责剩余的相对合同名称。
    from .evidence_validation import (
        _xdist_command_text,
        evidence_error,
        is_non_negative_integer,
    )

# 历史 local-test-evidence 分支在此处统一附加项目权威治理检查。
