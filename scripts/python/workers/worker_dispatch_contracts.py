"""定义 canonical worker dispatch 的固定 schema 和 verdict 合同。"""

# 延迟解析类型注解，保持合同模块与 Python 3.10 运行时兼容。
from __future__ import annotations

# 读取运行时 worker 合同和配置路径需要的标准库。
import json
from pathlib import Path

# 读取 protocol 配置作为所有 worker 常量的唯一运行时事实源。
def _bootstrap_protocol_config() -> dict[str, object]:
    """读取最小 protocol 配置；损坏时返回空对象以便 fail-closed。

    参数：
        无；配置路径由当前合同模块位置确定。
    返回：
        protocol 根映射；文件缺失、损坏或根类型错误时返回空映射。
    """

    # protocol 文件是所有 worker 枚举和阶段合同的唯一配置来源。
    path_protocol: Path = (  # worker protocol 配置文件路径，供启动合同读取。
        Path(__file__).resolve().parents[3] / "config" / "workers" / "protocol.json"  # 解析 protocol 文件所在的受管路径。
    )  # worker protocol 配置文件。

    # 启动阶段只读取 JSON，不执行配置文本。
    try:

        # JSON 根对象提供后续常量的受管字段。
        obj_protocol: object = json.loads(  # JSON 解析结果，稍后确认根类型。
            path_protocol.read_text(encoding="utf-8")  # 读取 UTF-8 配置正文。
        )  # 未验证的 protocol 根对象。

    # 配置不可用时返回空对象，所有派生合同会变成空集合并阻断。
    except (OSError, UnicodeError, json.JSONDecodeError):

        # 缺失或损坏配置不能让 worker 继续使用旧常量。
        return {}

    # 只有字典根才能承载协议字段。
    if isinstance(obj_protocol, dict):

        # 返回经过根类型确认的协议映射。
        return obj_protocol

    # 非字典根不能提供可信合同。
    return {}

# 读取一次 protocol，后续模块级常量都从该快照派生。
dict_bootstrap_protocol: dict[str, object] = _bootstrap_protocol_config()  # 模块常量共享的 protocol 配置快照。

# schema 版本控制所有 dispatcher envelope 的兼容边界。
SCHEMA_VERSION: int = int(dict_bootstrap_protocol.get("schema_version", 0))  # 当前 worker schema 版本。

# role card 键名决定 canonical worker 的唯一角色集合。
WORKER_NAMES: tuple[str, ...] = tuple(  # 角色卡名称，约束 canonical worker 集合。
    str(item) for item in dict_bootstrap_protocol.get("role_cards", {})  # 遍历协议角色键。
)  # worker 角色名称。

# task mode 列表控制 dispatcher 接受的任务范围。
TASK_MODES: tuple[str, ...] = tuple(  # dispatcher 允许的任务模式集合。
    str(item) for item in dict_bootstrap_protocol.get("task_modes", [])  # 遍历协议任务模式。
)  # 允许的任务模式。

# event type 列表控制生命周期事件的协议枚举。
EVENT_TYPES: tuple[str, ...] = tuple(  # 生命周期事件的协议枚举集合。
    str(item) for item in dict_bootstrap_protocol.get("event_types", [])  # 遍历协议事件枚举。
)  # 允许的事件类型。

# worker state 列表控制持久化状态机的合法状态。
WORKER_STATES: tuple[str, ...] = tuple(  # worker 持久化状态的协议枚举集合。
    str(item) for item in dict_bootstrap_protocol.get("worker_states", [])  # 遍历协议状态枚举。
)  # 允许的 worker 状态。

# 根授权状态列表控制 AGENTS.md 的唯一授权来源。
ROOT_AUTHORIZATION_STATES: tuple[str, ...] = tuple(  # AGENTS.md 授权状态的唯一枚举集合。
    str(item) for item in dict_bootstrap_protocol.get("root_authorization_states", [])  # 遍历授权状态枚举。
)  # 根授权状态。

# 当前运行平台与 worker 能力要求由 protocol 配置集中声明。
PLATFORM_CONTRACT: dict[str, str] = {
    str(key): str(value).strip()  # 规范化平台合同字段。
    for key, value in (dict_bootstrap_protocol.get("platform_contract", {}) or {}).items()  # 遍历平台合同字段。
    if isinstance(key, str) and isinstance(value, str)  # 过滤非文本配置项。
}  # 平台合同配置。

# canonical_roles 把短角色名绑定到唯一 worker id。
CANONICAL_WORKER_IDS: dict[str, str] = {
    str(key): str(value)  # 规范化角色和 worker id 文本。
    for key, value in (dict_bootstrap_protocol.get("canonical_roles", {}) or {}).items()  # 遍历 protocol 角色映射。
}  # canonical worker 身份映射。

# lifecycle phase 列表控制 reviewer/tester 的阶段顺序。
LIFECYCLE_PHASES: tuple[str, ...] = tuple(  # reviewer/tester 生命周期阶段的受管顺序。
    str(item) for item in dict_bootstrap_protocol.get("lifecycle_phases", [])  # 读取 reviewer/tester 阶段顺序。
)  # 生命周期阶段。

# phase_by_event 把事件名转换为对应阶段。
PHASE_BY_EVENT: dict[str, str] = {
    str(key): str(value)  # 规范化事件和阶段文本。
    for key, value in (dict_bootstrap_protocol.get("phase_by_event", {}) or {}).items()  # 遍历事件阶段映射。
}  # 事件到阶段映射。

# 反向映射让阶段载荷可以生成事件名。
EVENT_BY_PHASE: dict[str, str] = {str(value): str(key) for key, value in PHASE_BY_EVENT.items()}  # 阶段到事件映射。

# event_roles 把稳定角色名绑定到事件名。
EVENT_BY_ROLE: dict[str, str] = {
    str(key): str(value)  # 规范化角色事件文本。
    for key, value in (dict_bootstrap_protocol.get("event_roles", {}) or {}).items()  # 遍历角色事件映射。
}  # 角色到事件映射。

# phase_roles 把稳定角色名绑定到阶段名。
PHASE_BY_ROLE: dict[str, str] = {
    str(key): str(value)  # 规范化角色阶段文本。
    for key, value in (dict_bootstrap_protocol.get("phase_roles", {}) or {}).items()  # 遍历角色阶段映射。
}  # 角色到阶段映射。

# 读取协议中的角色名称并映射到角色卡字段。
def canonical_worker_id(str_role: str) -> str:
    """返回协议声明的 canonical worker ID。

    参数：
        str_role: protocol 中的角色短名。
    返回：
        对应 worker id；角色不存在时返回空字符串。
    """

    # 角色映射是唯一允许生成 worker id 的来源。
    return CANONICAL_WORKER_IDS.get(str_role, "")

# 将协议事件映射为生命周期阶段。
def lifecycle_phase_for_event(str_event_type: str) -> str:
    """返回协议声明的生命周期阶段。

    参数：
        str_event_type: protocol 中的事件类型。
    返回：
        对应阶段名；事件不存在时返回空字符串。
    """

    # 事件阶段映射保证状态机不依赖源码硬编码。
    return PHASE_BY_EVENT.get(str_event_type, "")

# 读取 role card 的指定字段。
def _role_field(str_worker_id: str, str_field_name: str) -> object:
    """读取 role card 的指定字段。

    参数：
        str_worker_id: canonical worker 身份。
        str_field_name: role card 中要读取的字段名。
    返回：
        字段原始值；role card 缺失、损坏或字段不可用时返回空映射。
    """

    # protocol role_cards 决定 worker id 对应的 role card 文件。
    obj_card_names: object = dict_bootstrap_protocol.get("role_cards", {})  # role card 名称映射。

    # role card 文件必须位于技能配置根下的 workers 目录。
    path_config_root: Path = Path(__file__).resolve().parents[3] / "config" / "workers"  # role card 配置根目录。

    # 只有对象映射才能解析当前 worker 的文件名。
    obj_card_name: object = (  # 当前 worker 的 role card 文件名。
        obj_card_names.get(str_worker_id) if isinstance(obj_card_names, dict) else None  # 解析指定 worker 的 role card 名称。
    )

    # 缺少 role card 时返回空值，调用方保持阻断。
    if not isinstance(obj_card_name, str):

        # 非字符串文件名不能构造可信配置路径。
        return {}

    # role card 读取失败必须被转换为空映射，禁止回退到旧合同。
    try:

        # 角色 verdict 只从外部 role card 读取。
        obj_card: object = json.loads(  # role card 解析结果，随后确认根对象。
            (path_config_root / obj_card_name).read_text(encoding="utf-8")  # 读取 role card JSON 正文。
        )  # 未验证的 role card 对象。

    # 损坏 role card 不能回退到 Python 常量。
    except (OSError, UnicodeError, json.JSONDecodeError):

        # 读取失败保持空映射，让上层阻断派发。
        return {}

    # 只有对象 role card 才能提供目标字段。
    if isinstance(obj_card, dict):

        # 返回原始字段，让上层按具体合同继续校验。
        return obj_card.get(str_field_name, {})

    # 非对象 role card 不具备可用合同。
    return {}

# 读取角色卡中的 receipt verdict 字段。
def _role_verdicts(str_worker_id: str) -> object:
    """读取 role card 的 receipt_verdicts。

    参数：
        str_worker_id: canonical worker 身份。
    返回：
        role card 的 receipt_verdicts 原始值。
    """

    # 统一通过字段读取器保持 role card 路径和失败边界一致。
    return _role_field(str_worker_id, "receipt_verdicts")

# 读取角色卡中的对齐 verdict 字段。
def worker_alignment_verdict(str_worker_id: str) -> str:
    """读取角色卡声明的对齐结论。

    参数：
        str_worker_id: canonical worker 身份。
    返回：
        角色允许的对齐 verdict；类型不符时返回空字符串。
    """

    # 对齐 verdict 由 role card 决定，不能从调用方输入推导。
    obj_alignment_verdict: object = _role_field(str_worker_id, "alignment_verdict")  # role card 对齐字段。

    # 只接受字符串 verdict，阻断对象或列表冒充结论。
    return str(obj_alignment_verdict).strip() if isinstance(obj_alignment_verdict, str) else ""

# 读取角色卡中的阻断 verdict 集合。
def worker_blocking_verdicts(str_worker_id: str) -> frozenset[str]:
    """读取角色卡声明的阻断结论集合。

    参数：
        str_worker_id: canonical worker 身份。
    返回：
        角色声明的阻断 verdict 集合；类型不符时返回空集合。
    """

    # 阻断 verdict 从 role card 读取，保证角色职责不能被 CLI 改写。
    obj_blocking_verdicts: object = _role_field(str_worker_id, "blocking_verdicts")  # role card 阻断集合。

    # 只有列表字段才能转换为稳定的 verdict 集合。
    return (
        frozenset(str(item) for item in obj_blocking_verdicts)
        if isinstance(obj_blocking_verdicts, list)
        else frozenset()
    )

# reviewer verdict 列表需要在模块加载时转成稳定集合。
def _reviewer_receipt_verdicts() -> frozenset[str]:
    """读取 reviewer role card 的允许回执 verdict。

    参数：无。
    返回：去重后的 reviewer 回执 verdict 集合。
    """

    # reviewer 状态机只接受 role card 声明的回执结论。
    return frozenset(
        str(item) for item in (_role_verdicts(canonical_worker_id("reviewer")) or [])
    )

# reviewer role card 的结论集合供回执校验拒绝未知状态。
REVIEWER_RECEIPT_VERDICTS: frozenset[str] = _reviewer_receipt_verdicts()  # reviewer 回执合法状态集合。

# tester receipt verdicts 按 tester 生命周期阶段分组。
TESTER_RECEIPT_VERDICTS: dict[str, frozenset[str]] = {  # tester 阶段回执到允许结论的映射。
    str(key): frozenset(str(item) for item in value)  # 规范化 tester 阶段 verdict。
    for key, value in (_role_verdicts(canonical_worker_id("tester")) or {}).items()  # 遍历 tester 阶段。
    if isinstance(value, list)  # 只接受列表形式的阶段 verdict。
}

# gardener verdict 来源与 reviewer 分离，避免两个只读角色交叉授权。
GARDENER_RECEIPT_VERDICTS: frozenset[str] = frozenset(  # gardener 回执状态机使用的允许结论。
    str(item) for item in (_role_verdicts(canonical_worker_id("gardener")) or [])  # 把 gardener 列表转成字符串集合。
)

# tester failure verdicts 选择必须携带结构化诊断的 receipt。
TESTER_FAILURE_VERDICTS: frozenset[str] = frozenset(  # tester 失败诊断触发结论的去重集合。
    str(item)  # 规范化要求 failure_report 的 verdict。
    for item in (_role_field(canonical_worker_id("tester"), "failure_report_required_for") or [])  # 遍历 tester 配置。
)

# 报告字段从 protocol 管理的 report section 加载。
dict_reports: dict[str, object] = (  # protocol 声明的 failure/rejection 报告字段集合。
    dict_bootstrap_protocol.get("reports", {})  # 读取 report schema 原始对象。
    if isinstance(dict_bootstrap_protocol.get("reports", {}), dict)  # 只接受对象根。
    else {}  # 配置损坏时保持空映射并由校验阻断。
)

# tester failure_report 必须暴露配置声明的全部顶层字段。
TESTER_FAILURE_REPORT_FIELDS: frozenset[str] = frozenset(  # tester failure_report 的顶层字段。
    str(item) for item in dict_reports.get("failure_fields", [])  # 规范化 failure_report 顶层字段。
)

# 每条 failure_tests 明细使用这组配置字段。
TESTER_FAILURE_TEST_FIELDS: frozenset[str] = frozenset(  # failure_tests 每个条目的字段。
    str(item) for item in dict_reports.get("failure_test_fields", [])  # 规范化 failure_tests 字段。
)

# evidence 校验只接受配置声明的可追溯锚点。
TESTER_FAILURE_EVIDENCE_ANCHORS: frozenset[str] = frozenset(  # evidence 可用的可追溯锚点。
    str(item) for item in dict_reports.get("failure_evidence_anchors", [])  # 规范化 evidence 锚点。
)

# modification_status 校验使用配置声明的副作用字段。
TESTER_FAILURE_MODIFICATION_FIELDS: frozenset[str] = frozenset(  # 产品、测试与 Git 副作用状态字段。
    str(item) for item in dict_reports.get("failure_modification_fields", [])  # 规范化副作用字段。
)

# 非 tester rejection_report 复用同一组副作用字段。
WORKER_REJECTION_REPORT_FIELDS: frozenset[str] = frozenset(  # reviewer/gardener 拒绝报告的字段集合。
    str(item) for item in dict_reports.get("rejection_fields", [])  # 建立 rejection_report 的字段索引。
)

# receipt 状态改变前先拒绝空泛 failure 文本。
TESTER_FAILURE_VAGUE_TEXTS: frozenset[str] = frozenset(  # 被拒绝的空泛失败文本集合。
    str(item) for item in dict_reports.get("vague_failure_texts", [])  # 规范化空泛文本值。
)

# 摘要字符集由 protocol 声明，配置损坏时为空集合并保持拒绝。
SHA256_CHARACTERS: frozenset[str] = frozenset(  # receipt 哈希字段允许的字符集合。
    str(dict_bootstrap_protocol.get("sha256_characters", ""))  # 读取 protocol 声明的哈希字符集。
)

# 定位 Skill 内的 worker 协议文件，具体角色值由配置决定。
def _worker_protocol_path() -> Path:
    """返回当前 Skill 的 worker 公共协议路径。

    参数：无。
    返回：协议 JSON 的绝对路径。
    """

    # 配置入口固定在 Skill 资源区，避免调用方复制角色字段。
    path_skill_root = Path(__file__).resolve().parents[3]  # 当前 Skill 根目录

    # 返回受管协议文件，后续读取统一经过 JSON 校验。
    return path_skill_root / "config" / "workers" / "protocol.json"

# 加载 worker 协议并拒绝缺失、损坏或错误根类型。
def _load_worker_protocol() -> dict[str, object]:
    """加载 worker 公共协议配置。

    参数：无。
    返回：已解析的协议对象。
    异常：ValueError 表示协议文件不可用。
    """

    # 读取协议文件，保留配置错误的原始路径。
    path_protocol = _worker_protocol_path()  # worker 协议文件

    # 缺少协议时禁止回退到静态角色合同。
    if not path_protocol.is_file():

        # 将缺失事实转换为可执行的阻断提示。
        raise ValueError(
            "> ERR: [Python] worker protocol configuration is missing: "
            + str(path_protocol)
        )

    # 解析 JSON，防止列表或标量伪造角色映射。
    try:

        # 使用标准库读取 UTF-8 配置。
        dict_object_protocol: dict[str, object] = json.loads(  # 解析后的 worker 协议对象
            path_protocol.read_text(encoding="utf-8")  # 读取协议原文
        )

    # 保留 JSON 的行列错误，方便配置修正。
    except json.JSONDecodeError as object_error:

        # 解析失败必须阻断 worker dispatch。
        raise ValueError(
            f"> ERR: [Python] worker protocol configuration is invalid: {object_error}"
        ) from object_error

    # 协议根必须是对象，后续字段才有确定边界。
    if not isinstance(dict_object_protocol, dict):

        # 拒绝隐式构造默认 worker。
        raise ValueError("> ERR: [Python] worker protocol root must be an object")

    # 返回原始映射，由 dispatch_contracts 复制角色对象。
    return dict_object_protocol

# 读取 protocol 声明的角色卡或修复配置，拒绝缺失和非对象内容。
def _load_worker_resource(str_relative_name: str, str_resource_kind: str) -> dict[str, object]:
    """读取受管 worker JSON 资源。

    参数:
        str_relative_name: protocol 声明的资源文件名。
        str_resource_kind: 资源职责名称，用于错误定位。
    返回:
        已确认的 JSON 对象。
    异常:
        ValueError 表示资源缺失、损坏或根类型错误。
    """

    # 所有 worker 资源必须位于 protocol 同目录，防止配置逃逸到外部路径。
    path_resource = (_worker_protocol_path().parent / str_relative_name).resolve()  # 受管 worker 资源路径

    # 资源解析后仍必须保持在 protocol 目录内。
    if not path_resource.is_relative_to(_worker_protocol_path().parent.resolve()) or not path_resource.is_file():

        # 缺失或逃逸资源不能被默认合同替代。
        raise ValueError(
            f"> ERR: [Python] worker {str_resource_kind} resource is missing or outside config: {path_resource}"
        )

    # JSON 解析错误保留资源职责，便于主 Agent直接修复对应文件。
    try:

        # 读取 UTF-8 对象，禁止执行配置中的任何代码。
        object_resource = json.loads(path_resource.read_text(encoding="utf-8"))  # worker 资源对象

    # 资源语法错误必须被标记为对应职责的阻断原因。
    except json.JSONDecodeError as object_error:

        # 资源语法错误必须在派发前阻断。
        raise ValueError(
            f"> ERR: [Python] worker {str_resource_kind} resource is invalid: {object_error}"
        ) from object_error

    # 只有对象根才能提供字段级 worker 合同。
    if not isinstance(object_resource, dict):

        # 拒绝列表或标量伪造角色卡。
        raise ValueError(f"> ERR: [Python] worker {str_resource_kind} resource must be an object")

    # 返回资源对象供调用方合并或读取。
    return object_resource

# 读取 repair.json 中的零派发和重试边界。
def worker_repair_config() -> dict[str, object]:
    """返回 dispatcher 修复配置。

    参数：无。
    返回：repair.json 的对象映射。
    异常：ValueError 表示 repair 配置缺失、损坏或根类型错误。
    """

    # 先读取公共 protocol，确保 repair 路径来自同一事实源。
    dict_protocol = _load_worker_protocol()  # 当前 worker 公共协议对象。

    # 缺少 repair 路径时禁止猜测重试策略。
    str_repair_name = dict_protocol.get("repair_config")  # protocol 声明的 repair 资源名。

    # 只有非空字符串路径才能读取受管 repair 配置。
    if not isinstance(str_repair_name, str) or not str_repair_name.strip():

        # 修复路径不完整必须 fail-closed。
        raise ValueError("> ERR: [Python] worker repair_config is missing")

    # 返回受管修复资源对象。
    return _load_worker_resource(str_repair_name, "repair")

# 返回配置声明的零派发结论，避免在 receipt 代码中重复业务值。
def zero_dispatch_verdict() -> str:
    """返回无 worker 调用时的唯一 receipt 结论。

    参数：无。
    返回：配置声明的零派发 verdict。
    异常：ValueError 表示 verdict 缺失或不是非空字符串。
    """

    # 修复配置是零派发语义的单一来源。
    value_verdict = worker_repair_config().get("zero_dispatch_verdict")  # 配置声明的零派发结论。

    # 非空字符串才能进入 receipt 判定集合；空白值不能产生可验证的零派发收据。
    if not isinstance(value_verdict, str) or not value_verdict.strip():

        # 缺少结论时拒绝生成无动作收据。
        raise ValueError("> ERR: [Python] worker repair zero_dispatch_verdict is invalid")

    # 返回配置中的原始稳定结论。
    return value_verdict.strip()

# 递归解析 worker 合同中的运行时路径占位符。
def _materialize_protocol_value(
    value_template: object,
    dict_bindings: dict[str, object],
) -> object:
    """将协议模板物化为当前运行时使用的值。

    参数:
        value_template: 合同中的标量或路径列表。
        dict_bindings: 协议声明的占位符绑定。
    返回:
        替换占位符后的同类型值。
    """

    # 列表值必须逐项解析，保持角色根目录顺序。
    if isinstance(value_template, list):

        # 递归展开列表中的所有路径模板。
        return [
            _materialize_protocol_value(value_item, dict_bindings)
            for value_item in value_template
        ]

    # 字符串值按配置绑定替换占位符。
    if isinstance(value_template, str):

        # 复制模板文本后逐项应用运行时绑定。
        str_value = value_template  # 当前待物化的合同文本

        # 只替换协议中明确声明的占位符。
        for str_name, value_binding in dict_bindings.items():

            # 当前替换结果作为下一项绑定的输入。
            str_value = str_value.replace("{" + str(str_name) + "}", str(value_binding))  # 应用当前路径绑定

        # 返回已经解析的合同字符串。
        return str_value

    # 其他标量保持配置文件原始类型。
    return value_template

# 返回三类 canonical worker 的运行时职责合同。
def dispatch_contracts() -> dict[str, dict[str, object]]:
    """返回已解析的运行时职责合同。

    参数:
        无。
    返回:
        worker 身份到 task_kind、读写根和拒绝协议的映射。
    异常:
        ValueError 表示协议文件缺失、损坏或角色映射无效。

    """

    # 从唯一协议文件读取所有角色，禁止代码内置权限集合。
    dict_object_protocol = _load_worker_protocol()  # 受管 worker 协议对象

    # 角色映射缺失时直接阻断，避免返回空合同继续派发。
    dict_object_workers = dict_object_protocol.get("workers")  # worker 权限卡映射

    # 只有对象根才能提供可验证的角色合同。
    if not isinstance(dict_object_workers, dict):

        # 保留字段路径供主 Agent修复配置。
        raise ValueError("> ERR: [Python] worker protocol workers must be an object")

    # 路径占位符绑定缺失时禁止发出未解析的权限根。
    dict_bindings = dict_object_protocol.get("path_bindings")  # 运行时路径绑定映射

    # 绑定值必须是对象，才能解析所有角色的路径模板。
    if not isinstance(dict_bindings, dict):

        # 未解析的路径根不能进入任何 worker 合同。
        raise ValueError("> ERR: [Python] worker protocol path_bindings must be an object")

    # 角色卡路径由 protocol 声明，角色卡字段覆盖公共 inline 兼容值。
    dict_role_cards = dict_object_protocol.get("role_cards")  # worker id 到 role card 文件名映射。

    # 只有对象映射才能保证每个 canonical worker 都有独立角色卡。
    if not isinstance(dict_role_cards, dict):

        # 缺少 role cards 时不能退回 Python 内置权限。
        raise ValueError("> ERR: [Python] worker protocol role_cards must be an object")

    # role-card schema 由 protocol 声明，字段要求不再散落在 dispatcher Python 中。
    str_role_schema_name = dict_object_protocol.get("role_card_schema")  # 驱动 role card 字段校验的 schema 文件名。

    # schema 路径必须是 protocol 声明的非空字符串。
    if not isinstance(str_role_schema_name, str) or not str_role_schema_name.strip():

        # 缺少 schema 时不能信任任何外部角色卡。
        raise ValueError("> ERR: [Python] worker protocol role_card_schema is missing")

    # 读取 schema 对象，统一 role card 的必需字段边界。
    dict_role_schema = _load_worker_resource(str_role_schema_name, "role card schema")  # 从受管 JSON 读取 required 字段边界。

    # 读取 schema 的 required 列表，防止空合同绕过字段校验。
    list_required_role_fields = dict_role_schema.get("required")  # role card 必需字段列表。

    # required 列表必须是非空数组，才能验证每个角色卡。
    if not isinstance(list_required_role_fields, list) or not list_required_role_fields:

        # schema 没有 required 列表时阻断角色合同。
        raise ValueError("> ERR: [Python] worker role card schema has no required fields")

    # 逐个复制并物化角色合同，避免调用方修改原始配置载荷。
    dict_contracts: dict[str, dict[str, object]] = {}  # 已解析的 worker 合同映射

    # 逐项读取角色合同，确保每个角色都能物化路径。
    for str_worker_id, dict_worker_contract in dict_object_workers.items():

        # 非法角色条目不允许隐式生成默认权限。
        if not isinstance(str_worker_id, str) or not isinstance(dict_worker_contract, dict):

            # 跳过无效条目，完整性校验在调用方继续执行。
            continue

        # 先合并 inline 兼容字段，再由外部角色卡覆盖事实。
        dict_merged_worker = dict(dict_worker_contract)  # 当前角色的兼容合同副本

        # 角色卡缺失或路径类型错误时阻断派发。
        str_role_card_name = dict_role_cards.get(str_worker_id)  # 从 protocol 映射解析当前 worker 的配置文件。

        # 缺失或空白文件名都不能进入资源读取。
        if not isinstance(str_role_card_name, str) or not str_role_card_name.strip():

            # 每个 canonical worker 都必须拥有独立角色卡。
            raise ValueError(f"> ERR: [Python] role card is missing for {str_worker_id}")

        # 外部角色卡是 worker 权限和 verdict 的最终事实源。
        dict_merged_worker.update(
            _load_worker_resource(str_role_card_name, f"role card {str_worker_id}")
        )

        # 逐项收集当前角色卡缺失的 schema required 字段。
        list_missing_role_fields = [  # 当前角色卡缺失字段列表。
            str_field  # 当前待检查的 required 字段。
            for str_field in list_required_role_fields  # 遍历 schema 声明的必需字段。
            if str_field not in dict_merged_worker  # 只保留当前合同未提供的字段。
        ]

        # 缺失字段必须一次性阻断，禁止生成不完整角色合同。
        if list_missing_role_fields:

            # 角色卡字段缺失时一次性返回完整修复列表。
            raise ValueError(
                f"> ERR: [Python] role card {str_worker_id} is missing: "
                + ", ".join(str(item) for item in list_missing_role_fields)
            )

        # 物化角色合同的每个字段，保留配置键集合。
        dict_contracts[str_worker_id] = {}  # 当前角色的运行时合同

        # 遍历当前角色字段并解析路径占位符。
        for str_field, value_field in dict_merged_worker.items():

            # 将物化后的字段写入当前角色合同。
            dict_contracts[str_worker_id][str_field] = _materialize_protocol_value(value_field, dict_bindings)  # 当前字段的运行时值

    # 返回只包含配置声明且已解析路径的角色合同。
    return dict_contracts

# 返回指定 worker 的范围拒绝结论，供 receipt 校验复用同一事实源。
def worker_scope_rejection_verdict(str_worker_id: str) -> str:
    """读取角色卡声明的范围拒绝结论。

    参数：
        str_worker_id: 需要读取拒绝语义的 canonical worker ID。
    返回：
        角色卡声明的非空范围拒绝 verdict。
    异常：ValueError 表示角色合同缺少有效范围拒绝结论。
    """

    # 角色卡是 worker 通信拒绝状态的唯一配置来源。
    value_verdict = dispatch_contracts().get(str_worker_id, {}).get("scope_rejection")  # 当前 worker 的范围拒绝结论。

    # 只有非空字符串才能作为可回放的拒绝状态。
    if not isinstance(value_verdict, str) or not value_verdict.strip():

        # 缺失结论时阻断当前 receipt，而不是猜测默认值。
        raise ValueError(f"> ERR: [Python] scope rejection verdict is missing for {str_worker_id}")

    # 返回经过去空白的配置结论。
    return value_verdict.strip()

# 校验失败报告的公共文本字段，保证每个结论都能指导修复。
def _validate_failure_report_text(value_report: dict[str, object]) -> list[str]:
    """检查失败阶段、首错、根因和最小修复文本。

    参数:
        value_report: 已确认根类型的 tester 失败报告。
    返回:
        文本字段错误列表；空列表表示文本层通过。
    """

    # 这些字段共同解释失败发生在哪里以及下一步做什么。
    tuple_text_fields = (
        "failure_stage",  # 失败发生阶段。
        "failure_kind",  # 失败分类。
        "first_error",  # 首个可定位错误。
        "failure_summary",  # 失败影响摘要。
        "root_cause_class",  # 根因分类。
        "minimal_fix",  # 最小修复方向。
    )  # 失败报告文本字段。

    # 逐字段拒绝空值、非字符串和固定空泛结论。
    for str_field in tuple_text_fields:

        # 读取当前报告文本，保留字段名称供错误定位。
        value_field = value_report.get(str_field)  # 失败报告文本值。

        # 只有具体文本才足以支撑主 Agent修复。
        if (
            not isinstance(value_field, str)
            or not value_field.strip()
            or value_field.strip().lower() in TESTER_FAILURE_VAGUE_TEXTS
        ):

            # 不回显原文，避免错误载荷携带无界日志。
            return [f"failure_report.{str_field} must be specific non-empty text"]

    # 文本字段全部具体时返回空诊断。
    return []

# 校验失败清单数量和每一项的期望、实际、观察与定位字段。
def _validate_failure_report_items(value_report: dict[str, object]) -> list[str]:
    """检查失败计数与完整明细列表。

    参数:
        value_report: 已确认根类型的 tester 失败报告。
    返回:
        失败数量或明细字段错误列表；空列表表示清单层通过。
    """

    # 失败计数必须保持整数语义，不能使用 bool 或负数。
    value_failure_count = value_report.get("failure_count")  # 报告声明的失败数量。

    # 至少一条明细才能解释失败结论。
    if isinstance(value_failure_count, bool) or not isinstance(value_failure_count, int) or value_failure_count < 1:

        # 返回固定字段错误，要求 tester 提供可执行清单。
        return ["failure_report.failure_count must be a positive integer"]

    # 失败明细数量必须与报告声明严格相等。
    value_failure_tests = value_report.get("failure_tests")  # 失败明细集合。

    # 缺失、空集合或数量漂移都会隐藏失败项。
    if not isinstance(value_failure_tests, list) or len(value_failure_tests) != value_failure_count:

        # 拒绝只返回聚合计数的简化报告。
        return ["failure_report.failure_tests must be a list matching failure_count"]

    # 逐项检查足以复现或定位的事实字段。
    for int_index, value_failure_test in enumerate(value_failure_tests):

        # 每个条目都必须是对象，不能用只有名称的字符串代替。
        if not isinstance(value_failure_test, dict):

            # 返回数组索引，便于 tester 修正具体条目。
            return [f"failure_report.failure_tests[{int_index}] must be an object"]

        # 失败项字段缺失时先返回完整缺失集合。
        list_missing_test_fields = sorted(  # 失败项缺失字段。
            TESTER_FAILURE_TEST_FIELDS - set(value_failure_test)  # 当前失败项字段集合。
        )

        # 缺失字段意味着当前条目仍不能指导主 Agent。
        if list_missing_test_fields:

            # 使用稳定字段顺序，保证修正提示可重复。
            return [
                f"failure_report.failure_tests[{int_index}] is missing: "
                + ", ".join(list_missing_test_fields)
            ]

        # 每个明细字段都要求具体非空文本。
        for str_test_field in ("test_id", "expected", "actual", "observed", "source"):

            # 读取当前明细字段，确保 expected/actual/source 均有内容。
            value_test_field = value_failure_test.get(str_test_field)  # 失败项字段值。

            # 空文本无法形成可执行定位信息。
            if not isinstance(value_test_field, str) or not value_test_field.strip():

                # 返回准确的数组索引和字段名。
                return [
                    f"failure_report.failure_tests[{int_index}].{str_test_field} "
                    "must be non-empty text"
                ]

    # 失败数量和完整明细均通过校验。
    return []

# 校验汇总层 expected_actual，保证总体偏差两端均被说明。
def _validate_failure_report_expected_actual(value_report: dict[str, object]) -> list[str]:
    """检查失败报告的总体期望与实际。

    参数:
        value_report: 已确认根类型的 tester 失败报告。
    返回:
        汇总期望/实际错误列表；空列表表示偏差层通过。
    """

    # 汇总对象必须同时保留 expected 和 actual 两个方向。
    value_expected_actual = value_report.get("expected_actual")  # 汇总期望/实际对象。

    # 非对象无法稳定表达总体偏差。
    if not isinstance(value_expected_actual, dict):

        # 要求 tester 使用固定对象而不是自由文本。
        return ["failure_report.expected_actual must be an object"]

    # 两侧内容都不能为空，避免只报告预期或只报告实际。
    for str_expected_actual_field in ("expected", "actual"):

        # 读取当前汇总侧，保留顶层字段路径。
        value_expected_actual_field = value_expected_actual.get(str_expected_actual_field)  # 汇总侧文本。

        # 空值会让主 Agent无法判断偏差方向。
        if not isinstance(value_expected_actual_field, str) or not value_expected_actual_field.strip():

            # 返回可直接修正的字段路径。
            return [
                "failure_report.expected_actual."
                + str_expected_actual_field
                + " must be non-empty text"
            ]

    # 汇总层的两端语义完整。
    return []

# 校验证据锚点和退出码，保证失败结论能回到事实来源。
def _validate_failure_report_evidence(value_report: dict[str, object]) -> list[str]:
    """检查失败报告的证据对象。

    参数:
        value_report: 已确认根类型的 tester 失败报告。
    返回:
        证据锚点或退出码错误列表；空列表表示证据层通过。
    """

    # evidence 必须是结构化对象，不能只放自然语言。
    value_evidence = value_report.get("evidence")  # 失败证据对象。

    # 非对象证据没有可复核字段边界。
    if not isinstance(value_evidence, dict):

        # 返回稳定的证据类型错误。
        return ["failure_report.evidence must be an object"]

    # 只保留非空锚点，空字符串和空容器不算证据。
    list_evidence_anchors = [  # 失败证据锚点集合。
        str_anchor  # 当前锚点字段名。
        for str_anchor in TESTER_FAILURE_EVIDENCE_ANCHORS  # 遍历允许的证据锚点。
        if value_evidence.get(str_anchor) not in (None, "", [], {})  # 过滤空证据值。
    ]

    # 没有锚点的“已检查”文本仍然无法复现失败。
    if not list_evidence_anchors:

        # 要求 tester 提供命令、作业、收据、路径、哈希或退出码。
        return [
            "failure_report.evidence must include one traceability anchor: "
            + ", ".join(sorted(TESTER_FAILURE_EVIDENCE_ANCHORS))
        ]

    # receipt_path 一旦出现就必须指向真实的非空证据文件。
    value_receipt_path = value_evidence.get("receipt_path")  # tester receipt 证据路径

    # 缺失或空 receipt 不能作为可复核锚点。
    if value_receipt_path not in (None, ""):

        # 只接受字符串路径，避免对象转换掩盖错误值。
        if not isinstance(value_receipt_path, str) or not value_receipt_path.strip():

            # 返回明确的 receipt 路径类型错误。
            return ["failure_report.evidence.receipt_path must be non-empty text"]

        # 路径必须存在且包含可读取内容。
        path_receipt = Path(value_receipt_path)  # 当前 receipt 证据文件

        # 不存在、目录或空文件都不能证明测试回执。
        if not path_receipt.is_file() or path_receipt.stat().st_size == 0:

            # 保留真实路径，便于主 Agent修复证据绑定。
            return [
                "failure_report.evidence.receipt_path must point to a non-empty file"
            ]

    # 若提交退出码，必须保留实际整数语义，不能用 bool 或字符串伪造。
    value_exit_code = value_evidence.get("exit_code")  # 证据中的执行退出码。

    # 未执行的 scope rejection 可以不提供退出码，但不能提供错误类型。
    if value_exit_code is not None and (
        isinstance(value_exit_code, bool) or not isinstance(value_exit_code, int)
    ):

        # 退出码错误会破坏 tester 的执行事实。
        return ["failure_report.evidence.exit_code must be an integer"]

    # 证据锚点和退出码类型均通过。
    return []

# 校验残留任务和副作用状态，防止失败后遗漏清理边界。
def _validate_failure_report_state(value_report: dict[str, object]) -> list[str]:
    """检查残留作业与工作树变更状态。

    参数:
        value_report: 已确认根类型的 tester 失败报告。
    返回:
        残留任务或副作用错误列表；空列表表示状态层通过。
    """

    # residual_jobs 必须显式是列表，空列表代表已经确认无残留。
    value_residual_jobs = value_report.get("residual_jobs")  # 远程残留任务清单。

    # 未结构化的残留状态不能证明任务已清理。
    if not isinstance(value_residual_jobs, list):

        # 要求 tester 回传 [] 或带条目的列表。
        return ["failure_report.residual_jobs must be a list"]

    # 修改状态必须声明产品源码、测试树和 Git 工作树。
    value_modification_status = value_report.get("modification_status")  # 失败阶段变更状态。

    # 非对象无法区分 tester 自身和产品侧副作用。
    if not isinstance(value_modification_status, dict):

        # 拒绝使用缺省副作用状态。
        return ["failure_report.modification_status must be an object"]

    # 缺少任一状态字段都不能安全决定后续清理动作。
    list_missing_modification_fields = sorted(  # 修改状态缺失字段。
        TESTER_FAILURE_MODIFICATION_FIELDS - set(value_modification_status)  # 当前变更状态字段集合。
    )

    # 返回完整缺失字段，便于一次补齐报告。
    if list_missing_modification_fields:

        # 不允许主 Agent替 tester 猜测副作用。
        return [
            "failure_report.modification_status is missing: "
            + ", ".join(list_missing_modification_fields)
        ]

    # 三个状态值都必须是严格布尔值。
    for str_modification_field in (
        "product_source_modified",
        "tests_modified",
        "git_modified",
    ):

        # 读取当前副作用状态，拒绝 0/1 等隐式类型。
        value_modification_field = value_modification_status.get(str_modification_field)  # 变更状态值。

        # 错误类型会使主 Agent误判是否允许继续修复。
        if not isinstance(value_modification_field, bool):

            # 指出具体状态字段，便于 tester 修正回传。
            return [
                "failure_report.modification_status."
                + str_modification_field
                + " must be boolean"
            ]

    # 残留任务和副作用状态均已明确。
    return []

# 校验 tester 失败报告，防止主 Agent只收到一个失败计数而没有修复依据。
def validate_tester_failure_report(value_report: object) -> list[str]:
    """返回 tester 失败报告的字段级错误。

    参数:
        value_report: tester 返回的失败报告对象。
    返回:
        稳定排序的合同错误；空列表表示报告足够详细，可以进入 receipt 状态机。
    """

    # 非对象无法提供字段级诊断，直接拒绝而不猜测报告内容。
    if not isinstance(value_report, dict):

        # 主 Agent需要明确知道缺失的是整个报告而不是某一个字段。
        return ["failure_report must be an object"]

    # 顶层字段缺失时先返回字段名，避免继续读取不完整结构。
    list_missing_fields = sorted(  # 失败报告缺失字段。
        TESTER_FAILURE_REPORT_FIELDS - set(value_report)  # 当前报告字段集合。
    )

    # 缺失字段已经足以阻断，后续结构错误留给下一次回传修正。
    if list_missing_fields:

        # 返回稳定字段顺序，方便主 Agent按清单补齐报告。
        return ["failure_report is missing: " + ", ".join(list_missing_fields)]

    # 各层校验器保持症状、数量、偏差、证据和副作用职责分离。
    tuple_validators = (  # 失败报告分层校验器。
        _validate_failure_report_text,  # 文本层校验器。
        _validate_failure_report_items,  # 失败清单校验器。
        _validate_failure_report_expected_actual,  # 期望实际校验器。
        _validate_failure_report_evidence,  # 证据锚点校验器。
        _validate_failure_report_state,  # 残留和副作用校验器。
    )

    # 按固定顺序返回第一条可执行修正提示。
    for func_validator in tuple_validators:

        # 当前层错误必须原样交给主 Agent，禁止被空泛总结覆盖。
        list_errors = func_validator(value_report)  # 当前失败报告层诊断。

        # 一旦某层不通过，先修正该层再继续后续校验。
        if list_errors:

            # 保留字段级信息，避免主 Agent只能看到失败结论。
            return list_errors

    # 所有失败报告层均通过合同校验。
    return []

# 校验非 tester worker 的 SCOPE_REJECTED 诊断，避免只返回一个状态词。
def validate_worker_rejection_report(value_report: object) -> list[str]:
    """返回 reviewer/gardener 范围拒绝报告的字段级错误。

    参数：
        value_report: canonical non-tester worker 返回的拒绝报告对象。
    返回：
        稳定排序的合同错误；空列表表示报告可以进入同 target repair。
    """

    # 范围拒绝必须使用对象根，不能把自由文本当成协议报告。
    if not isinstance(value_report, dict):

        # 主 Agent需要知道缺少的是完整报告对象。
        return ["rejection_report must be an object"]

    # 一次性返回缺少的顶层字段，避免反复试错。
    list_missing_fields = sorted(  # rejection_report 缺少的顶层字段。
        WORKER_REJECTION_REPORT_FIELDS - set(value_report)  # 当前报告已提供的字段集合。
    )

    # 缺失字段必须先完整补齐，再继续检查字段类型。
    if list_missing_fields:

        # 保留稳定字段顺序，便于同 target repair。
        return ["rejection_report is missing: " + ", ".join(list_missing_fields)]

    # 文本字段必须具体说明拒绝原因和重试方式。
    for str_field in (
        "rejection_stage",
        "reason_code",
        "summary",
        "allowed_request",
        "retry_guidance",
    ):

        # 空泛或空白文本不能指导主 Agent重发请求。
        value_field = value_report.get(str_field)  # 当前拒绝文本字段。

        # 文本缺失或空白会使 retry guidance 无法执行。
        if not isinstance(value_field, str) or not value_field.strip():

            # 返回具体字段路径，保持与 tester failure_report 一致。
            return [f"rejection_report.{str_field} must be non-empty text"]

    # violations、evidence 和 residual_jobs 必须保留结构化边界，违规列表至少有一条事实。
    if not isinstance(value_report.get("violations"), list) or not value_report["violations"]:

        # 没有违规清单就无法解释为何拒绝。
        return ["rejection_report.violations must be a non-empty list"]

    # evidence 对象必须至少保留一个事实锚点。
    if not isinstance(value_report.get("evidence"), dict) or not value_report["evidence"]:

        # 证据对象至少要有一个事实锚点。
        return ["rejection_report.evidence must be a non-empty object"]

    # residual_jobs 使用列表表达已确认的残留任务状态。
    if not isinstance(value_report.get("residual_jobs"), list):

        # 空列表是已经确认无残留的明确状态。
        return ["rejection_report.residual_jobs must be a list"]

    # 修改状态必须明确产品、测试和 Git 副作用。
    value_modification_status = value_report.get("modification_status")  # rejection_report 的副作用状态对象。

    # 没有结构化副作用对象就不能安全执行 retry。
    if not isinstance(value_modification_status, dict):

        # 缺失对象不能支持安全重试。
        return ["rejection_report.modification_status must be an object"]

    # 一次收集所有缺失状态字段，避免只修复一个字段后重复往返。
    list_missing_modification_fields = sorted(  # rejection_report 缺少的副作用字段。
        TESTER_FAILURE_MODIFICATION_FIELDS - set(value_modification_status)  # 已提供的副作用字段集合。
    )

    # 缺少副作用状态时阻断同 target repair，不能由主 Agent猜测。
    if list_missing_modification_fields:

        # 不允许主 Agent猜测 worker 是否已经写入文件。
        return [
            "rejection_report.modification_status is missing: "
            + ", ".join(list_missing_modification_fields)
        ]

    # 三个副作用字段都必须是严格布尔值。
    for str_modification_field in TESTER_FAILURE_MODIFICATION_FIELDS:

        # 当前字段若不是严格 bool，就不能判定 worker 是否改动了文件。
        if not isinstance(value_modification_status.get(str_modification_field), bool):

            # 类型错误会破坏后续同 target repair 的安全判断。
            return [
                "rejection_report.modification_status."
                + str_modification_field
                + " must be boolean"
            ]

    # 所有范围拒绝字段都已具备可执行信息。
    return []
