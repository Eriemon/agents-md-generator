"""验证位置中立的完整 pytest 收据而不读取或枚举 tests 内容。"""

# 标准库负责规范 JSON 哈希和 UTC freshness 计算。
from datetime import datetime, timezone
import hashlib
import importlib.util
import json

# 文件路径和子进程模块负责读取、绑定和验证收据来源。
from pathlib import Path
import subprocess
import sys

# 动态 sibling loader 使用模块类型注解保持接口明确。
from types import ModuleType
from typing import Any

# 产品模块名称虽以 test_ 开头，但不属于 pytest 测试收集边界。
__test__ = False  # 禁止 pytest 把收据验证函数当作测试用例。

# policy 映射保留字典兼容性并提供计划中的属性接口。
class PytestReceiptPolicy(dict[str, Any]):
    """配置驱动的 pytest receipt policy 容器。"""

    # 允许调用方按计划字段名读取映射属性。
    def __getattr__(self, str_name: str) -> object:
        """按计划字段名读取 policy 顶层属性。

        参数：str_name 为请求的 policy 字段名。
        返回：对应字段值。
        异常：字段未在 policy 映射中声明时抛出 AttributeError。
        """

        # 已声明字段直接复用映射值，保持字典和属性接口一致。
        if str_name in self:

            # 返回 policy 绑定中的字段对象。
            return self[str_name]

        # 未声明字段使用稳定错误前缀，便于上层记录缺失原因。
        raise AttributeError(f"> ERR: [Python] policy field is unavailable: {str_name}")

# 发布证据最多允许距当前时间二十四小时，超窗必须重新运行完整测试套件。
DEFAULT_FRESHNESS_SECONDS = 24 * 60 * 60  # 默认测试证据有效期。

# 完整套件使用稳定 ID，避免发布收据携带命令原文。
PYTEST_FULL_COMMAND_ID = "pytest-full"  # 完整 pytest 命令的公开标识。

# 该文本是测试签发器和验证器共同计算摘要的唯一输入。
PYTEST_FULL_COMMAND = "python -m pytest -q"  # 完整 pytest 的固定调用。

# 根据已绑定 API 构造 sibling 相互导入时需要的临时模块桥。
def _build_module_bridges() -> dict[str, ModuleType]:
    """构造当前 evidence loader 的临时 sibling 模块桥。

    参数：无；桥接内容来自当前模块已定义的兼容 API。
    返回：模块名到临时 ModuleType 的映射。
    """

    # 建立与当前模块同名的桥，供 sibling 解析已定义的 evidence 合同。
    module_type_evidence_bridge = ModuleType("evidence_validation")  # 让 sibling 解析当前证据校验函数和常量。

    # bridge 复制的是已经完成定义的当前证据 API。
    module_type_evidence_bridge.__dict__.update(globals())  # 复制当前 evidence API。

    # 先登记 evidence bridge，供 pytest/history sibling 使用。
    dict_module_bridges = {"evidence_validation": module_type_evidence_bridge}  # 当前模块桥集合。

    # 仅在当前模块已有 pytest 公共入口时构造 history 适配桥。
    if "validate_pytest_receipt" in globals():

        # 创建 history 读取 pytest 结果时使用的适配模块。
        module_type_pytest_bridge = ModuleType("pytest_receipt_validation")  # history 的 pytest 合同适配模块。

        # 将当前 receipt 校验入口映射给 history 的绝对导入。
        module_type_pytest_bridge.validate_pytest_receipt = globals()["validate_pytest_receipt"]  # history 使用的 pytest 校验入口。

        # 让 history loader 通过固定名称取得 pytest bridge。
        dict_module_bridges.update({"pytest_receipt_validation": module_type_pytest_bridge})  # 保存 pytest 适配模块。

    # 只有已有 history API 时才能为 project 建立兼容桥。
    if "validate_test_evidence_payload" in globals():

        # 创建 project 读取历史证据时使用的适配模块。
        module_type_history_bridge = ModuleType("history_receipt_validation")  # 供 project 解析历史证据的适配模块。

        # 暴露 project 需要的 payload 校验入口。
        module_type_history_bridge.validate_test_evidence_payload = globals()["validate_test_evidence_payload"]  # project 调用的 history payload 实现。

        # 保存 project 读取历史证据时使用的适配模块。
        dict_module_bridges.update({"history_receipt_validation": module_type_history_bridge})  # 让 project loader 取得 history bridge。

    # 返回当前加载阶段所需的最小桥集合。
    return dict_module_bridges

# 兼容模块按当前文件相邻路径隔离加载，不依赖调用方 sys.path。
def _load_sibling_module(str_module_name: str) -> ModuleType:
    """从当前 verify 目录加载一个兼容验证模块。

    参数：str_module_name 为相邻 Python 模块的功能名称。
    返回：已执行的隔离模块对象。
    异常：模块规格缺失或执行失败时抛出 RuntimeError。
    """

    # 当前文件所在目录是 sibling validator 的唯一来源根。
    path_sibling_module = Path(__file__).resolve().with_name(str_module_name + ".py")  # sibling 模块路径。

    # 每个 sibling 使用独立模块名，避免复用外部同名模块。
    str_isolated_name = "agents_evidence_" + str_module_name  # 隔离模块名称。

    # 按文件路径创建模块规格，保持 direct/aggregate 加载一致。
    module_type_spec = importlib.util.spec_from_file_location(str_isolated_name, path_sibling_module)  # sibling 加载规格。

    # 缺失规格或 loader 表示源码布局不可执行。
    if module_type_spec is None or module_type_spec.loader is None:

        # 不猜测环境模块，直接以稳定错误阻断证据验证。
        raise RuntimeError("> ERR: [Python] sibling evidence module could not be loaded")

    # 模块对象只承载当前证据验证器的公开兼容函数。
    module_sibling = importlib.util.module_from_spec(module_type_spec)  # 隔离 sibling 模块。

    # 构造当前加载阶段所需的最小 sibling bridge 集合。
    dict_module_bridges = _build_module_bridges()  # sibling 导入桥集合。

    # 保存调用方原有的同名模块，避免覆盖外部加载上下文。
    dict_previous_modules = {}  # 调用方原有模块绑定。

    # 逐项记录 bridge 名称对应的原始模块。
    for str_bridge_name in dict_module_bridges:

        # 恢复阶段只处理本次声明的模块名称。
        dict_previous_modules[str_bridge_name] = sys.modules.get(str_bridge_name)  # 保存原始 sibling 模块。

    # 在 sibling 执行期间提供临时的跨职责模块上下文。
    for str_bridge_name, module_bridge in dict_module_bridges.items():

        # 仅覆盖当前声明的兼容模块名称。
        sys.modules[str_bridge_name] = module_bridge  # 当前 sibling bridge 绑定。

    # 执行失败必须保留原异常链并转换为稳定错误。
    try:

        # loader 从已解析文件执行 sibling validator。
        module_type_spec.loader.exec_module(module_sibling)

    # sibling 执行异常必须转为证据验证的稳定阻断。
    except (OSError, ImportError, SyntaxError) as object_error:

        # 证据验证依赖不可执行时保持 fail-closed。
        raise RuntimeError(
            f"> ERR: [Python] sibling evidence module execution failed: {str_module_name}"
        ) from object_error

    # 无论 sibling 是否成功，都恢复调用方的模块上下文。
    finally:

        # sibling 执行结束后恢复调用方的全部模块上下文。
        for str_bridge_name, module_previous in dict_previous_modules.items():

            # 没有旧模块时移除本次临时桥接。
            if module_previous is None:

                # 当前名称只由本次 loader 负责回收。
                sys.modules.pop(str_bridge_name, None)

            # 原模块存在时恢复调用方的原始绑定。
            else:

                # 保留调用方此前的 sibling 模块对象。
                sys.modules[str_bridge_name] = module_previous  # 恢复调用方的 sibling 模块。

    # 返回隔离模块供兼容入口绑定函数引用。
    return module_sibling

# 将 sibling validator 的指定 API 绑定到当前兼容模块命名空间。
def _bind_sibling_exports(
    str_module_name: str,
    tuple_export_names: tuple[str, ...],
) -> None:
    """绑定隔离 sibling 模块的兼容 API。

    参数：str_module_name 为 sibling validator 名称；tuple_export_names 为公开 API 名称。
    返回：无；函数引用写入当前模块的兼容命名空间。
    """

    # 每组 API 只加载一次隔离 sibling 模块。
    module_type_sibling = _load_sibling_module(str_module_name)  # 当前导出集合所属的隔离 validator。

    # 逐项绑定外部调用方已经使用的稳定名称。
    for str_export_name in tuple_export_names:

        # 动态边界只读取声明的 sibling 属性，不猜测名称。
        globals()[str_export_name] = getattr(module_type_sibling, str_export_name)  # 将声明 API 绑定到兼容名称。

# 预先计算摘要，避免每次验证重复拼接固定命令。
PYTEST_FULL_COMMAND_SHA256 = hashlib.sha256(PYTEST_FULL_COMMAND.encode("utf-8")).hexdigest()  # 远程命令摘要。

# 双进程全量模式使用独立 ID，避免把并行形态伪装成串行命令。
PYTEST_XDIST_COMMAND_ID = "pytest-full-xdist"  # 受控并行 pytest 命令标识。

# 旧 receipt 保留两个 worker 的兼容校验，避免历史证据失效。
PYTEST_XDIST_LEGACY_WORKER_COUNT = 2  # 历史并行 receipt 的兼容数量。

# 新并行合同允许四到八个 worker，首轮发布验证使用四个。
PYTEST_XDIST_MIN_WORKER_COUNT = 4  # 新合同允许的最小 worker 数量。

# 上限约束防止收据请求超过已批准的并发资源边界。
PYTEST_XDIST_MAX_WORKER_COUNT = 8  # 新合同允许的最大 worker 数量。

# 保留旧公开常量，兼容已有签发器和历史测试引用。
PYTEST_XDIST_WORKER_COUNT = PYTEST_XDIST_LEGACY_WORKER_COUNT  # 历史公开 worker 数量别名。

# 同一测试文件固定到一个 worker，降低模块内共享 fixture 的竞争风险。
PYTEST_XDIST_DISTRIBUTION = "loadfile"  # 已批准的 xdist 分发方式。

# worker 崩溃立即让套件失败，禁止自动重启掩盖不稳定测试或延长挂起。
PYTEST_XDIST_COMMAND_TEMPLATE = (  # selector-free 并行全量 pytest 命令模板。
    "python -m pytest -q -n {worker_count} --dist loadfile --max-worker-restart 0"  # worker 数由收据绑定。
)

# 历史公开命令继续对应两个 worker，新的 worker 数通过模板重建。
PYTEST_XDIST_COMMAND = (  # 历史 selector-free 并行命令。
    "python -m pytest -q -n 2 --dist loadfile --max-worker-restart 0"  # 双进程全量命令正文。
)

# 并行命令摘要由固定逻辑命令生成，不包含远程 timeout 包装或工作目录。
PYTEST_XDIST_COMMAND_SHA256 = hashlib.sha256(  # 受控并行 pytest 命令摘要。
    PYTEST_XDIST_COMMAND.encode("utf-8")  # 固定逻辑命令字节。
).hexdigest()

# 三个显式字段使收据能够复核 worker 数和分发方式而不保存命令原文。
PYTEST_XDIST_FIELDS = frozenset(  # 并行执行形态字段。
    "execution_mode worker_count distribution".split()  # 收据公开的三项并行参数。
)

# 判断 worker 数是否属于历史兼容值或当前四到八 worker 合同。
def _is_allowed_xdist_worker_count(object_worker_count: Any) -> bool:
    """验证 xdist worker 数的类型和批准范围。

    参数：object_worker_count 为收据声明的 worker 数。
    返回：值为非布尔整数且属于批准范围时为 True。
    """

    # worker 数必须是整数，布尔值不能冒充并发数量。
    if isinstance(object_worker_count, bool) or not isinstance(object_worker_count, int):

        # 非整数输入直接拒绝，避免隐式转换改变命令。
        return False

    # 保留两个 worker 历史证据，同时开放四到八 worker。
    return object_worker_count == PYTEST_XDIST_LEGACY_WORKER_COUNT or (
        PYTEST_XDIST_MIN_WORKER_COUNT <= object_worker_count <= PYTEST_XDIST_MAX_WORKER_COUNT
    )

# 按 receipt worker 数重建唯一允许的 selector-free 命令。
def _xdist_command_text(int_worker_count: int) -> str:
    """构造指定 worker 数的 xdist 逻辑命令。

    参数：int_worker_count 为已经通过范围校验的 worker 数。
    返回：不包含 timeout、cwd 或环境包装的逻辑命令文本。
    """

    # 只把已验证的 worker 数写入固定命令模板。
    return PYTEST_XDIST_COMMAND_TEMPLATE.format(worker_count=int_worker_count)

# v2 收据的公开字段不包含输出路径、提示词或服务器细节。
PYTEST_RECEIPT_FIELDS = frozenset(  # v2 pytest 收据允许的公开字段。
    "runner suite command_id command_sha256 exit_code collected passed "
    "failed errors skipped xfailed xpassed tests_tree_sha256 "
    "source_manifest_sha256 test_commit".split()
)

# Git pathspec 在列出候选前排除测试、派生收据、运行态和历史归档。
SOURCE_MANIFEST_EXCLUDES = (  # 非测试发布清单的固定排除边界。
    ":(exclude,glob)tests/**",  # TESTER 独占测试树。
    ":(exclude,glob).conda/**",  # 远程隔离环境不是发布源码。
    ":(exclude,glob)docs/git_manager/test-evidence-*.json",  # 收据自引用路径。
    ":(exclude,glob).test-evidence.json",  # 项目根测试收据不进入自身源码摘要。
    ":(exclude,glob)**/.test-evidence.json",  # 作用域测试收据同样不自引用。
    ":(exclude,glob)test-evidence*.json",  # 根目录其他测试收据命名也不自引用。
    ":(exclude,glob)**/test-evidence*.json",  # 作用域测试收据统一排除。
    ":(exclude,glob)**/CLAUDE.md",  # 兼容 shim 不属于发布源码清单。
    ":(exclude,glob)**/GEMINI.md",  # Gemini 兼容入口不进入发布源码摘要。
    ":(exclude,glob).agents/semantic-review-*.json",  # 临时语义审查证据。
    ":(exclude,glob).agents/**",  # 代理治理运行态不进入源码摘要。
    ":(exclude,glob).settings/**",  # 本地运行配置。
    ":(exclude,glob).erie-remote-ssh/**",  # 远程 runner 运行态与 job 产物。
    ":(exclude,glob)runs/**",  # 远程和本地验证运行态不绑定活动源码。
    ":(exclude,glob)docs/superpowers/**",  # 设计与计划文档不属于远程运行时源码。
    ":(exclude,glob)docs/development/decomposition-plans/**",  # 分解审查文档不进入运行时摘要。
    ":(exclude,glob)docs/git_manager/github-publish-*.json",  # 发布请求记录不绑定活动源码。
    ":(exclude,glob)__init__.py",  # 根级兼容文件不属于技能运行时源码。
    ":(exclude,glob).codebase-memory/**",  # 图谱持久化产物。
    ":(exclude,glob)dist/**",  # 版本化发布产物。
    ":(exclude,glob)docs/handoff/**",  # 收尾交接历史。
    ":(exclude,glob)docs/memory/**",  # 项目记忆运行态。
    ":(exclude,glob)docs/dir_manager/current_structure.json",  # 自动扫描快照不绑定活动源码。
    ":(exclude,glob)docs/development/history_development/**",  # 开发阶段归档不绑定活动源码。
    ":(exclude,glob)docs/git_manager/history_git_manager/**",  # Git 管理归档不绑定活动源码。
    ":(exclude,glob)docs/dir_manager/history_dir_manager/**",  # 目录治理归档不绑定活动源码。
    ":(exclude,glob)docs/experience/history_experience/**",  # 旧经验归档不绑定活动源码。
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
        "remote_pytest",  # schema-1 历史三阶段 pytest 证据。
        "skill_pressure_report_hash",  # 技能压力报告哈希。
        "tests_outside_staged_count",  # tests 外暂存计数。
        "receipt_sha256",  # 排除自身后的收据哈希。
    }
)

# schema=1 历史收据的三类旧阶段仅用于 immutable history 复核。
REQUIRED_REMOTE_PHASES = ("targeted", "regression", "full")  # 固定远程验证阶段顺序。

# 每个远程阶段使用相同的最小不透明字段集合。
REQUIRED_REMOTE_FIELDS = frozenset(  # 单阶段必需字段。
    {"command_hash", "exit_code", "count", "timestamp"}  # 单阶段完整字段集合。
)

# local-test-evidence 仅用于显式 immutable-history 复核，不能满足活动发布门禁。
LOCAL_EVIDENCE_KIND = "local-test-evidence"  # 历史本地 unittest 收据类型。

# 历史本地 final-suite 收据必须具备这些绑定和结果字段。
LOCAL_REQUIRED_FIELDS = frozenset(  # 历史本地收据的固定字段集合。
    "schema kind phase runner command_id command_sha256 timestamp exit_code "
    "collected passed failed errors skipped tests_tree_hash tests_file_count "
    "tests_byte_count source_manifest_hash test_commit_sha receipt_sha256".split()
)

# 历史可选字段只允许边界计数和两份脱敏治理快照，阻止秘密字段进入收据。
LOCAL_OPTIONAL_FIELDS = frozenset(  # 历史本地收据的可选字段集合。
    {"tests_outside_staged_count", "remote_governance", "answers"}  # 可选安全字段。
)

# 历史 local 收据允许字段由必需字段和受控可选字段共同组成。
LOCAL_ALLOWED_FIELDS = LOCAL_REQUIRED_FIELDS | LOCAL_OPTIONAL_FIELDS  # 历史本地收据字段白名单。

# 历史本地收据的命令白名单只登记可重放的固定命令。
LOCAL_COMMANDS = {  # 历史本地命令标识到不可变命令文本的映射。
    "local-unittest-full": "python -B -m unittest discover -s tests -p test*.py",  # 完整本地 unittest 命令。
}

# 结果守恒检查使用固定字段顺序，避免遗漏失败类别。
LOCAL_COUNT_FIELDS = tuple("collected passed failed errors skipped".split())  # 本地测试统计字段。

# 本地元数据计数扩展结果计数以覆盖文件规模和用例规模。
LOCAL_METADATA_COUNT_FIELDS = tuple(  # 本地元数据计数白名单。
    "tests_file_count tests_byte_count collected passed failed errors skipped".split()  # 文件和结果计数。
)  # 本地元数据计数字段。

# pytest v2 的终态统计字段在验证器外保持稳定。
PYTEST_COUNT_FIELDS = tuple(  # pytest 结果计数白名单。
    "collected passed failed errors skipped xfailed xpassed".split()  # pytest 终态计数。
)  # pytest 统计字段。

# 本地摘要字段由固定白名单生成，避免遗漏或意外回显敏感字段。
LOCAL_SUMMARY_FIELDS = tuple(  # 本地低敏摘要字段白名单。
    "phase runner command_id timestamp exit_code collected passed failed errors skipped".split()  # 执行状态字段。
)  # 本地摘要字段。

# pytest 摘要字段只保留执行身份和聚合结果。
PYTEST_SUMMARY_FIELDS = tuple(  # pytest 低敏摘要字段白名单。
    "runner suite command_id exit_code collected passed failed errors skipped xfailed xpassed".split()  # 执行统计字段。
)  # pytest 摘要字段。

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

# 本地收据的提交字段使用完整 Git SHA，避免短前缀碰撞。
def is_full_commit_sha(object_value: Any) -> bool:
    """判断值是否为完整的 40 位 Git 提交 SHA。

    参数：object_value 为收据提交字段。
    返回：值为完整十六进制 SHA 时为 True。
    """

    # 完整长度和十六进制字符共同构成提交身份合同。
    if not isinstance(object_value, str) or len(object_value) != 40:

        # 短 SHA 不足以满足本地收据的独立审计要求。
        return False

    # 大小写仅影响表示，不影响 Git 对象身份。
    return all(str_character in "0123456789abcdef" for str_character in object_value.lower())

# 本地计数和治理布尔值都必须使用精确类型，不能接受 Python 的隐式子类语义。
def is_non_negative_integer(object_value: Any) -> bool:
    """判断值是否为非布尔的非负整数。

    参数：object_value 为待验证的聚合计数。
    返回：值为非负整数且不是布尔值时为 True。
    """

    # type 精确比较同时排除 bool 伪装成整数的情况。
    bool_is_integer = (  # 计数类型和范围判定表达式。
        isinstance(object_value, int)  # 值必须属于整数类型。
        and not isinstance(object_value, bool)  # 布尔值不得伪装计数。
        and object_value >= 0  # 计数必须保持非负。
    )  # 计数类型和范围结论。

    # 返回统一的聚合计数判定结果。
    return bool_is_integer

# 治理合同只接受显式 False，缺失、真值和其他类型都必须阻断。
def is_explicit_false(object_value: Any) -> bool:
    """判断值是否为合同要求的布尔 False。

    参数：object_value 为治理文件或收据中的策略值。
    返回：值为布尔 False 时为 True。
    """

    # 精确 bool 类型避免整数零绕过治理策略。
    bool_is_explicit_false = isinstance(object_value, bool) and not object_value  # 治理关闭结论。

    # 调用方据此区分明确关闭与缺失字段。
    return bool_is_explicit_false

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

# 本地扁平合同的字段形状检查与远程阶段对象保持隔离。
def _validate_local_receipt_shape(dict_receipt: dict[str, Any]) -> list[str]:
    """检查本地收据的字段集合、版本标识和自哈希。

    参数：dict_receipt 为待验证的本地收据对象。
    返回：字段形状或收据完整性错误列表。
    """

    # 形状 helper 只负责字段级错误，避免混入当前仓库状态。
    list_errors: list[str] = []  # 本地字段形状诊断。

    # 先计算缺失字段，便于以固定顺序公开合同名称。
    list_missing_fields: list[str] = sorted(LOCAL_REQUIRED_FIELDS - set(dict_receipt))  # 本地缺失字段。

    # 额外字段可能携带命令输出、路径或秘密，也必须拒绝。
    list_unexpected_fields: list[str] = sorted(set(dict_receipt) - LOCAL_ALLOWED_FIELDS)  # 本地多余字段。

    # 缺失字段直接标记 schema 不完整。
    if list_missing_fields:

        # 错误文本只包含公开合同字段，不泄漏测试内容。
        list_errors.append(
            evidence_error(
                "TEST_EVIDENCE_SCHEMA",
                "local test evidence payload is missing: " + ", ".join(list_missing_fields),
            )
        )

    # 字段白名单错误与缺失字段一样阻断收据复用。
    if list_unexpected_fields:

        # 仅公开字段名，不回显多余字段的值。
        list_errors.append(
            evidence_error(
                "TEST_EVIDENCE_SCHEMA",
                "local test evidence payload has unexpected fields: " + ", ".join(list_unexpected_fields),
            )
        )

    # 固定 schema 和 kind 防止远程或其他历史 JSON 混入本地路径。
    bool_identity_valid = (  # 本地合同身份判定表达式。
        dict_receipt.get("schema") == 1  # schema 必须使用本地版本。
        and dict_receipt.get("kind") == LOCAL_EVIDENCE_KIND  # kind 必须标记本地合同。
    )  # 本地合同身份结论。

    # 身份不匹配时拒绝继续伪装成历史 local-test-evidence。
    if not bool_identity_valid:

        # 调用方只需知道合同标识错误，不需要原始值。
        list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", "local test evidence schema or kind is invalid"))

    # 收据自哈希必须覆盖除自身字段外的全部扁平字段。
    try:

        # 非 JSON 值或递归对象不能绕过门禁，必须落入统一哈希错误。
        bool_receipt_hash_valid = (  # 收据自哈希一致性判定表达式。
            str(dict_receipt.get("receipt_sha256", ""))  # 收据中的自哈希文本。
            == canonical_receipt_sha256(dict_receipt)  # 当前对象复算出的自哈希。
        )  # 本地自哈希结论。

    # 结构化调用方输入异常时保持验证器 fail closed，而不是向外抛异常。
    except (TypeError, ValueError, RecursionError):

        # 无法规范化的对象不可能提供可信自哈希。
        bool_receipt_hash_valid = False  # 非 JSON 收据的自哈希结论。

    # 任何字段被修改后都必须重新签发本地收据。
    if not bool_receipt_hash_valid:

        # 实际摘要不进入门禁输出，避免形成可复制的敏感载荷。
        list_errors.append(evidence_error("TEST_EVIDENCE_RECEIPT_HASH", "test evidence receipt hash does not match"))

    # 返回结构层错误供上层与仓库绑定错误合并。
    return list_errors

# 本地收据的两个 opaque hash 和提交身份必须同时绑定当前状态。
def _validate_local_receipt_bindings(
    dict_receipt: dict[str, Any],
    str_expected_tests_tree_hash: str,
    str_expected_source_manifest_hash: str,
) -> list[str]:
    """检查本地收据的 tests、源码、提交和暂存边界绑定。

    参数：dict_receipt 为本地收据对象。
    参数：str_expected_tests_tree_hash 为当前 tests 树摘要。
    参数：str_expected_source_manifest_hash 为当前源码清单摘要。
    返回：绑定和边界错误列表。
    """

    # 绑定 helper 不读取 tests 成员，只比较调用方提供的摘要事实。
    list_errors: list[str] = []  # 本地绑定诊断。

    # tests 摘要既要满足格式也要等于当前 Git tree 事实。
    bool_tests_hash_valid = (  # tests 树绑定判定表达式。
        _is_sha256_text(dict_receipt.get("tests_tree_hash"))  # 收据摘要必须是 SHA-256。
        and str(dict_receipt.get("tests_tree_hash", "")) == str_expected_tests_tree_hash  # 摘要必须匹配当前树。
    )  # tests 树绑定结论。

    # 不匹配时不回显实际哈希内容。
    if not bool_tests_hash_valid:

        # TESTER 需要基于当前树重新生成收据。
        list_errors.append(evidence_error("TEST_EVIDENCE_TESTS_HASH", "tests tree hash does not match"))

    # 非测试源码摘要同样必须具备 SHA-256 格式和当前值。
    bool_source_hash_valid = (  # 非测试源码绑定判定表达式。
        _is_sha256_text(dict_receipt.get("source_manifest_hash"))  # 源码摘要字段先通过格式校验。
        and str(dict_receipt.get("source_manifest_hash", "")) == str_expected_source_manifest_hash  # 摘要必须匹配源码。
    )  # 非测试源码绑定结论。

    # 源码变化会使此前测试结果失去发布资格。
    if not bool_source_hash_valid:

        # 只报告稳定错误码，不暴露清单成员。
        list_errors.append(evidence_error("TEST_EVIDENCE_SOURCE_HASH", "source manifest hash does not match"))

    # 本地收据必须用完整提交 SHA 绑定测试来源。
    bool_commit_valid = is_full_commit_sha(dict_receipt.get("test_commit_sha"))  # 本地提交格式结论。

    # 短 SHA、空值或非十六进制值都不足以审计。
    if not bool_commit_valid:

        # 项目级入口还会复核该提交是否属于当前历史。
        list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", "local test evidence commit is invalid"))

    # 可选边界计数存在时必须明确为零。
    bool_stage_boundary_valid = (  # tests 暂存边界判定表达式。
        "tests_outside_staged_count" not in dict_receipt  # 缺省字段沿用兼容合同。
        or (  # 显式字段必须保持非布尔非负整数语义。
            is_non_negative_integer(dict_receipt.get("tests_outside_staged_count"))  # 越界计数必须是非布尔非负整数。
            and dict_receipt.get("tests_outside_staged_count") == 0  # 显式字段只能为零。
        )
    )  # tests 暂存边界结论。

    # 越界暂存内容不能被本地合同忽略。
    if not bool_stage_boundary_valid:

        # 不回显越界路径或数量。
        list_errors.append(evidence_error("TEST_EVIDENCE_STAGE_BOUNDARY", "staged content escaped the tests boundary"))

    # 返回所有绑定层错误。
    return list_errors

# 本地文件、字节和测试结果计数必须是非布尔非负整数。
def _validate_local_receipt_counts(dict_receipt: dict[str, Any]) -> list[str]:
    """检查本地收据中的规模和结果计数。

    参数：dict_receipt 为本地收据对象。
    返回：计数类型、范围或空测试集错误列表。
    """

    # 计数 helper 统一处理所有固定聚合字段。
    list_errors: list[str] = []  # 本地计数诊断。

    # 逐项验证避免任何布尔值借用整数语义。
    for str_count_field in LOCAL_METADATA_COUNT_FIELDS:

        # 当前计数只用于类型和范围判断。
        object_count: Any = dict_receipt.get(str_count_field)  # 当前本地聚合计数。

        # 非法计数不能进入发布摘要。
        if not is_non_negative_integer(object_count):

            # 对所有计数统一使用脱敏 schema 错误。
            list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", "local test evidence counts are invalid"))

    # 空 tests 树或空收集结果不能构成完整发布证据。
    bool_receipt_empty = (  # 本地收据非空判定表达式。
        dict_receipt.get("tests_file_count") == 0  # 不允许空 tests 文件集合。
        or dict_receipt.get("collected") == 0  # 不允许零收集用例。
    )  # 本地收据非空结论。

    # 只有明确为零时才追加空收据错误，缺失字段已由 shape helper 报告。
    if bool_receipt_empty:

        # 空测试集不能作为成功发布证明。
        list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", "local test evidence is empty"))

    # 返回本地计数层的所有错误。
    return list_errors

# 本地收据元数据入口只编排三个彼此独立的验证层。
def validate_local_receipt_metadata(
    dict_receipt: dict[str, Any],
    str_expected_tests_tree_hash: str,
    str_expected_source_manifest_hash: str,
) -> list[str]:
    """验证 local-test-evidence 的结构和当前源码绑定。

    参数：dict_receipt 为本地收据对象。
    参数：str_expected_tests_tree_hash 为当前 tests 树摘要。
    参数：str_expected_source_manifest_hash 为当前源码清单摘要。
    返回：全部脱敏元数据错误。
    """

    # 先收集字段形状和自哈希问题。
    list_errors: list[str] = _validate_local_receipt_shape(dict_receipt)  # 本地形状诊断。

    # 再追加不透明源码、tests 和提交绑定问题。
    list_errors.extend(
        _validate_local_receipt_bindings(
            dict_receipt,
            str_expected_tests_tree_hash,
            str_expected_source_manifest_hash,
        )
    )

    # 最后验证计数类型、范围和非空不变量。
    list_errors.extend(_validate_local_receipt_counts(dict_receipt))

    # 返回聚合后的本地元数据错误。
    return list_errors

# 校验本地治理快照，避免历史字段伪造当前发布状态。
def validate_local_governance_fields(dict_receipt: dict[str, Any]) -> list[str]:
    """验证收据中可选的本地治理快照。

    参数：dict_receipt 为本地收据对象。
    返回：治理快照错误列表。
    """

    # 收据快照不是唯一权威，但出现时必须明确声明远程关闭。
    list_errors: list[str] = []  # 本地治理诊断。

    # 收据若携带远程策略对象，必须是明确关闭的布尔值。
    dict_remote_governance: dict[str, object] | None = dict_receipt.get("remote_governance")  # 收据中的远程治理快照。

    # 该布尔值决定快照能否作为本地合同的补充证据。
    bool_remote_snapshot_valid = (  # 收据远程治理一致性判定表达式。
        dict_remote_governance is None  # 缺省快照不制造冲突。
        or (  # 缺省或明确关闭的快照都可继续验证。
            isinstance(dict_remote_governance, dict)  # 快照必须是对象。
            and is_explicit_false(dict_remote_governance.get("enabled"))  # enabled 必须明确为 False。
        )
    )  # 收据远程治理快照结论。

    # 真值、缺失 enabled 或错误类型都不能被本地收据接受。
    if not bool_remote_snapshot_valid:

        # 不回显治理对象内容。
        list_errors.append(
            evidence_error("TEST_EVIDENCE_LOCAL_POLICY", "local test evidence conflicts with remote governance")
        )

    # 收据若携带批准答案，必须同样明确禁用远程服务器。
    dict_answers: dict[str, object] | None = dict_receipt.get("answers")  # 收据中的批准答案快照。

    # 该布尔值决定批准答案能否授权本地测试路径。
    bool_answer_snapshot_valid = (  # 收据批准答案一致性判定表达式。
        dict_answers is None  # 缺省答案快照不制造冲突。
        or (  # 缺省或明确禁用远程的答案都可继续验证。
            isinstance(dict_answers, dict)  # 答案快照必须是对象。
            and is_explicit_false(dict_answers.get("use_remote_server"))  # 远程使用选项必须为 False。
        )
    )  # 收据批准答案快照结论。

    # 任意冲突答案都阻断本地发布路径。
    if not bool_answer_snapshot_valid:

        # 不回显答案对象内容。
        list_errors.append(
            evidence_error("TEST_EVIDENCE_LOCAL_POLICY", "local test evidence conflicts with approved answers")
        )

    # 返回治理快照层的全部诊断。
    return list_errors

# 历史本地阶段和 runner 合同先在独立 helper 中完成，排除 pytest 伪装。
def _validate_local_runner_fields(dict_receipt: dict[str, Any]) -> list[str]:
    """验证本地收据的 final 阶段与 unittest runner。

    参数：dict_receipt 为本地收据对象。
    返回：阶段或 runner 错误列表。
    """

    # 阶段 helper 只处理执行身份，不处理计数和时间。
    list_errors: list[str] = []  # 本地执行身份诊断。

    # final 是本地发布合同唯一允许的阶段。
    bool_phase_valid = dict_receipt.get("phase") == "final"  # 本地阶段结论。

    # 其他阶段不能冒充已完成的发布测试。
    if not bool_phase_valid:

        # 缺失值和历史阶段都统一返回稳定 schema 错误。
        list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", "local test evidence phase is invalid"))

    # unittest 是历史本地合同固定 runner，pytest 不得走该路径。
    bool_runner_valid = dict_receipt.get("runner") == "unittest"  # 本地 runner 结论。

    # 任意其他 runner 都不能满足历史 local-test-evidence。
    if not bool_runner_valid:

        # 错误码明确区分 runner 伪装和一般 schema 损坏。
        list_errors.append(evidence_error("TEST_EVIDENCE_LOCAL_RUNNER", "local test evidence runner is invalid"))

    # 返回执行身份层的诊断。
    return list_errors

# 本地命令只接受登记过的固定文本和对应摘要。
def _validate_local_command_fields(dict_receipt: dict[str, Any]) -> list[str]:
    """验证本地命令 ID 与命令 SHA-256 的绑定。

    参数：dict_receipt 为本地收据对象。
    返回：命令白名单或命令摘要错误列表。
    """

    # 命令 helper 不返回命令正文，避免摘要报告泄漏执行细节。
    list_errors: list[str] = []  # 本地命令诊断。

    # 从收据读取稳定命令标识并在白名单中解析文本。
    str_command_id: str | None = dict_receipt.get("command_id")  # 本地命令标识。

    # 只从登记表解析命令正文，拒绝调用方自带的任意命令。
    str_command_text: str | None = (  # 审计命令文本解析表达式。
        LOCAL_COMMANDS.get(str_command_id) if isinstance(str_command_id, str) else None  # 白名单命令正文。
    )  # 审计命令正文。

    # 未登记命令不能仅凭自报摘要获得信任。
    if str_command_text is None:

        # 命令白名单错误不回显任意输入文本。
        list_errors.append(evidence_error("TEST_EVIDENCE_LOCAL_COMMAND", "local test evidence command is not approved"))

    # 只有命令文本存在时才计算其固定摘要。
    str_expected_command_sha256: str = (  # 审计命令预期摘要表达式。
        hashlib.sha256(str_command_text.encode("utf-8")).hexdigest()  # 固定命令文本的 SHA-256。
        if str_command_text is not None  # 命令存在时才计算摘要。
        else ""  # 未登记命令使用空占位并由后续校验拒绝。
    )  # 审计命令的预期摘要。

    # 收据摘要必须是合法 SHA-256 且与白名单文本完全相等。
    str_command_sha256: str | None = dict_receipt.get("command_sha256")  # 收据提交的命令摘要。

    # 摘要匹配结论同时覆盖格式和固定命令绑定。
    bool_command_hash_valid = (  # 收据命令摘要一致性判定表达式。
        _is_sha256_text(str_command_sha256)  # 收据摘要必须符合 SHA-256 格式。
        and str_command_sha256 == str_expected_command_sha256  # 收据摘要必须匹配白名单命令。
    )  # 命令摘要绑定结论。

    # 空值、伪造值和错误命令都会落入同一稳定错误码。
    if not bool_command_hash_valid:

        # 不回显命令正文或实际摘要。
        list_errors.append(evidence_error("TEST_EVIDENCE_LOCAL_COMMAND", "local test evidence command hash is invalid"))

    # 返回命令层诊断。
    return list_errors

# 本地退出码必须是明确的零整数。
def _validate_local_exit_code(dict_receipt: dict[str, Any]) -> list[str]:
    """验证本地 unittest 的退出码。

    参数：dict_receipt 为本地收据对象。
    返回：退出码 schema 或失败错误列表。
    """

    # 退出码 helper 将类型错误和非零失败分开报告。
    list_errors: list[str] = []  # 本地退出码诊断。

    # 读取退出码并保留原始类型以拒绝 bool。
    object_exit_code: Any = dict_receipt.get("exit_code")  # 原始退出码用于拒绝 bool 并确认 unittest 返回零。

    # 非布尔整数才具备退出状态语义。
    bool_exit_code_valid = (  # 本地退出码类型判定表达式。
        isinstance(object_exit_code, int)  # 整数分支保留 unittest 返回的数值状态。
        and not isinstance(object_exit_code, bool)  # bool 作为 int 子类必须单独排除。
    )  # 退出码类型结论。

    # 类型错误不能继续判断是否成功。
    if not bool_exit_code_valid:

        # 类型诊断不携带实际值。
        list_errors.append(evidence_error("TEST_EVIDENCE_SCHEMA", "local test evidence exit code is invalid"))

    # 明确的非零退出码说明完整套件失败。
    if bool_exit_code_valid and object_exit_code != 0:

        # 只有成功退出码才能进入发布阶段。
        list_errors.append(evidence_error("TEST_EVIDENCE_LOCAL_FAILURE", "local unittest exited unsuccessfully"))

    # 返回退出码层诊断。
    return list_errors

# 本地计数守恒要求所有收集用例都通过且无失败类别。
def _validate_local_result_counts(dict_receipt: dict[str, Any]) -> list[str]:
    """验证本地 unittest 结果计数的守恒关系。

    参数：dict_receipt 为本地收据对象。
    返回：结果不完整或计数不守恒的错误列表。
    """

    # 结果 helper 只在元数据类型合法时计算守恒关系。
    list_errors: list[str] = []  # 本地结果计数诊断。

    # 先确认全部结果字段可安全参与加法。
    bool_counts_valid = all(  # 本地结果计数类型判定表达式。
        is_non_negative_integer(dict_receipt.get(str_count_field))  # 每个结果字段必须是非负整数。
        for str_count_field in LOCAL_COUNT_FIELDS  # 遍历固定的五类结果计数。
    )  # 本地结果计数类型结论。

    # 类型错误已由元数据 helper 报告，此处不重复增加错误。
    if bool_counts_valid:

        # 将收集总数单独命名，便于表达总量守恒。
        int_collected: int = int(dict_receipt["collected"])  # 收集用例总数。

        # 将通过总数单独命名，便于检查全量通过。
        int_passed: int = int(dict_receipt["passed"])  # 通过用例总数。

        # 将失败总数单独命名，便于拒绝隐藏失败。
        int_failed: int = int(dict_receipt["failed"])  # 失败用例总数。

        # 将错误总数单独命名，便于拒绝隐藏错误。
        int_errors: int = int(dict_receipt["errors"])  # 错误用例总数。

        # 将跳过总数单独命名，便于拒绝不完整套件。
        int_skipped: int = int(dict_receipt["skipped"])  # 跳过用例总数。

        # 零收集、未全通过或分类不守恒都不属于完整结果。
        bool_result_complete = (  # 本地完整通过判定表达式。
            int_collected > 0  # 必须至少收集一个用例。
            and int_passed == int_collected  # 通过数必须覆盖全部收集数。
            and int_passed + int_failed + int_errors + int_skipped == int_collected  # 五类结果必须守恒。
            and int_failed == 0  # 不允许隐藏失败用例。
            and int_errors == 0  # 不允许隐藏错误用例。
            and int_skipped == 0  # 不允许用跳过结果冒充完整通过。
        )  # 本地完整通过结论。

        # 结果不完整时阻断发布，不尝试修正 TESTER 数据。
        if not bool_result_complete:

            # 失败、错误、跳过和不守恒统一归为结果失败。
            list_errors.append(evidence_error("TEST_EVIDENCE_LOCAL_FAILURE", "local unittest result is incomplete"))

    # 返回结果守恒层诊断。
    return list_errors

# 本地测试时间必须带时区且位于允许 freshness 窗口内。
def _validate_local_freshness(
    dict_receipt: dict[str, Any],
    str_now_utc: str,
    int_freshness_seconds: int,
) -> list[str]:
    """验证本地收据时间的新鲜度。

    参数：dict_receipt 为本地收据对象。
    参数：str_now_utc 为当前 UTC 时间。
    参数：int_freshness_seconds 为最大允许证据年龄。
    返回：时间格式或 freshness 错误列表。
    """

    # 先解析比较基准和测试完成时间，拒绝无时区值。
    list_errors: list[str] = []  # 本地时间诊断。

    # 当前 UTC 是 freshness 计算的统一基准。
    value_current_datetime: datetime | None = parse_utc_timestamp(str_now_utc)  # 当前 UTC 比较基准。

    # 收据完成时间用于计算证据年龄。
    datetime_test: datetime | None = parse_utc_timestamp(  # 收据测试时间解析结果。
        str(dict_receipt.get("timestamp", ""))  # 只读取公开完成时间字段。
    )  # 本地测试完成时间。

    # 任一时间无法解析时不能证明 freshness。
    if value_current_datetime is None or datetime_test is None:

        # 不回显无效的时间原文。
        list_errors.append(evidence_error("TEST_EVIDENCE_FRESHNESS", "local test timestamp is invalid"))

    # 两个时间都有效时才进行年龄计算。
    if value_current_datetime is not None and datetime_test is not None:

        # 证据年龄统一使用 UTC 秒数比较。
        float_age_seconds: float = (value_current_datetime - datetime_test).total_seconds()  # 本地证据年龄。

        # 未来时间和超窗时间都必须拒绝。
        bool_timestamp_fresh = 0 <= float_age_seconds <= int_freshness_seconds  # 本地时间差位于合同窗口。

        # 只公开稳定 freshness 错误，不公开精确时间。
        if not bool_timestamp_fresh:

            # 过期或未来收据必须重新签发。
            list_errors.append(evidence_error("TEST_EVIDENCE_FRESHNESS", "local test evidence is stale"))

    # 返回时间层诊断。
    return list_errors

# 本地摘要只保留阶段、runner、命令标识和聚合统计。
def _build_local_summary(dict_receipt: dict[str, Any]) -> dict[str, Any]:
    """从本地收据生成不含路径和哈希的摘要。

    参数：dict_receipt 为本地收据对象。
    返回：供发布门禁展示的本地聚合摘要。
    """

    # 公开字段由固定白名单投影，天然排除哈希、路径和治理原文。
    dict_summary: dict[str, Any] = {
        str_field: dict_receipt.get(str_field)  # 当前低敏摘要字段。
        for str_field in LOCAL_SUMMARY_FIELDS  # 固定本地摘要字段顺序。
    }  # 本地安全摘要。

    # 仅返回低敏摘要，哈希、路径和治理原文不进入结果。
    return dict_summary

# 本地 final unittest 结果入口只编排身份、命令、计数和 freshness。
def validate_local_test_result(
    dict_receipt: dict[str, Any],
    str_now_utc: str,
    int_freshness_seconds: int,
) -> dict[str, Any]:
    """验证本地 final unittest 结果并生成安全摘要。

    参数：dict_receipt 为本地收据对象。
    参数：str_now_utc 为当前 UTC 时间。
    参数：int_freshness_seconds 为最大证据年龄。
    返回：包含 errors 和脱敏 summary 的本地结果。
    """

    # 各 helper 分别负责一种不变量，便于单独审计失败原因。
    list_errors: list[str] = _validate_local_runner_fields(dict_receipt)  # 阶段和 runner 诊断。

    # 命令文本只能由固定白名单反解，收据不携带命令正文。
    list_errors.extend(_validate_local_command_fields(dict_receipt))

    # 退出码和结果计数共同决定 unittest 是否完整成功。
    list_errors.extend(_validate_local_exit_code(dict_receipt))

    # 计数守恒检查拒绝隐藏失败、错误或跳过结果。
    list_errors.extend(_validate_local_result_counts(dict_receipt))

    # 时间窗口独立于 runner 和计数，任何一项失败都阻断发布。
    list_errors.extend(_validate_local_freshness(dict_receipt, str_now_utc, int_freshness_seconds))

    # 返回固定的 errors/summary 机器协议。
    return {"errors": list_errors, "summary": _build_local_summary(dict_receipt)}

# 项目级本地发布必须独立复核两个治理来源，不能只相信收据快照。
def validate_local_project_governance(path_project: Path) -> list[str]:
    """验证项目治理明确关闭远程服务器。

    参数：path_project 为仓库根。
    返回：治理文件缺失、解析失败或远程未关闭时的错误列表。
    """

    # 两个文件共同构成本地测试授权事实。
    list_errors: list[str] = []  # 项目治理诊断。

    # 治理文件路径固定在项目根的 .agents 目录内。
    path_control: Path = path_project / ".agents" / "agents-control.json"  # 控制档案路径。

    # 批准答案文件与控制档案共同构成本地-only 授权事实。
    path_answers: Path = path_project / ".agents" / "answers-approved.json"  # 批准答案路径。

    # 缺失任一权威文件都不能让本地证据绕过远程策略。
    bool_governance_files_exist = path_control.is_file() and path_answers.is_file()  # 治理文件存在结论。

    # 未找到完整治理输入时立即 fail closed。
    if not bool_governance_files_exist:

        # 不回显本机绝对路径。
        return [evidence_error("TEST_EVIDENCE_LOCAL_POLICY", "local test evidence governance is unavailable")]

    # 读取 JSON 时只保留可审计的布尔策略，不传播文件内容。
    try:

        # 控制档案和批准答案必须作为两个独立对象解析。
        dict_control: Any = json.loads(path_control.read_text(encoding="utf-8"))  # 项目控制档案对象。

        # 批准答案单独读取以避免缺失字段被默认值掩盖。
        dict_answers: Any = json.loads(path_answers.read_text(encoding="utf-8"))  # 项目批准答案对象。

    # 文件、编码和 JSON 错误都归入同一治理不可用结果。
    except (OSError, UnicodeError, json.JSONDecodeError):

        # 解析失败必须 fail closed。
        return [evidence_error("TEST_EVIDENCE_LOCAL_POLICY", "local test evidence governance is invalid")]

    # 只有对象型控制档案才能提供远程合同字段。
    dict_remote_contract: dict[str, object] | None = (
        dict_control.get("remote_server_contract") if isinstance(dict_control, dict) else None  # 读取公开合同字段。
    )  # 远程服务器合同对象。

    # 控制档案必须明确声明远程服务关闭。
    bool_remote_contract_disabled = (  # 控制档案远程关闭判定表达式。
        isinstance(dict_remote_contract, dict)  # 远程合同必须是对象。
        and is_explicit_false(dict_remote_contract.get("enabled"))  # 合同 enabled 必须明确为 False。
    )  # 控制档案远程关闭结论。

    # enabled 缺失、真值或错误类型都视为不安全。
    if not bool_remote_contract_disabled:

        # 只公开治理合同要求，不回显档案内容。
        list_errors.append(
            evidence_error("TEST_EVIDENCE_LOCAL_POLICY", "local test evidence requires remote governance disabled")
        )

    # 批准答案必须是对象并明确声明不使用远程服务器。
    bool_answers_remote_disabled = (  # 批准答案远程关闭判定表达式。
        isinstance(dict_answers, dict)  # 批准答案必须是对象。
        and is_explicit_false(dict_answers.get("use_remote_server"))  # 该最终开关必须明确关闭远程使用。
    )  # 批准答案远程关闭结论。

    # 缺失或冲突答案不能授权本地发布。
    if not bool_answers_remote_disabled:

        # 只报告稳定策略错误，不泄漏答案内容。
        list_errors.append(
            evidence_error("TEST_EVIDENCE_LOCAL_POLICY", "local test evidence requires remote answers disabled")
        )

    # 返回全部治理诊断，供项目级发布门禁聚合。
    return list_errors

# 暴露 pytest 收据的兼容入口。
_bind_sibling_exports(
    "pytest_receipt_validation",
    (
        "_is_sha256_text",
        "_pytest_command_contract",
        "_validate_pytest_binding_fields",
        "_validate_pytest_contract_fields",
        "_validate_pytest_count",
        "_validate_pytest_execution_fields",
        "_build_pytest_summary",
        "validate_pytest_receipt",
    ),
)

# 暴露远程阶段和历史载荷的兼容入口。
_bind_sibling_exports(
    "history_receipt_validation",
    (
        "_validate_legacy_payload",
        "_validate_local_payload",
        "_validate_pytest_payload",
        "_validate_remote_phase_freshness",
        "_validate_remote_phase_shape",
        "_validate_remote_phase_values",
        "validate_remote_phase",
        "validate_remote_pytest",
        "validate_test_evidence_payload",
    ),
)

# 暴露项目摘要和 Git 绑定的兼容入口。
_bind_sibling_exports(
    "project_evidence_validation",
    (
        "_project_commit_field",
        "_project_evidence_failure",
        "_project_evidence_hashes",
        "_read_project_evidence_context",
        "_read_project_receipt",
        "_resolve_project_receipt_path",
        "local_tests_tree_hash",
        "run_project_git",
        "source_manifest_sha256",
        "test_commit_is_ancestor",
        "tests_tree_git_id",
        "tests_tree_hash",
        "validate_project_test_evidence",
    ),
)

# 读取配置驱动的 pytest policy，供新 receipt 入口逐步迁移。
def load_pytest_policy(
    path_project_root: Path | dict[str, object] | None = None,
    path_skill_root: Path | None = None,
    path_manifest: Path | None = None,
) -> dict[str, Any]:
    """加载带 policy/runtime manifest hash 的 pytest 合同。

    参数：path_project_root 和 path_skill_root 为可选根目录覆盖。
    参数：path_manifest 为可选 runtime manifest 覆盖路径。
    返回：包含 policy 对象和其 runtime binding 的映射。
    异常：runtime contract 缺失、摘要漂移或 policy 字段无效时抛出异常。
    """

    # 共享 loader 从当前模块文件位置动态解析，避免绝对安装路径。
    path_skill = path_skill_root or Path(__file__).resolve().parents[3]  # 当前技能根

    # 解析调用方项目根，缺省时使用当前工作目录。
    path_project = path_project_root or Path.cwd().resolve()  # 当前项目根

    # 共享 loader 目录跟随技能根解析，避免绝对安装路径。
    path_common_dir = path_skill / "scripts" / "python" / "common"  # 共享 loader 目录

    # 直接脚本加载时补充共享模块搜索路径。
    if str(path_common_dir) not in sys.path:

        # 只影响当前验证进程的导入解析。
        sys.path.insert(0, str(path_common_dir))

    # 延迟导入避免历史 receipt 模块在旧安装中初始化失败。
    from runtime_contracts import load_json_role, load_runtime_manifest

    # 已有 binding 直接复用，避免 active receipt 绑定漂移。
    dict_binding = (  # 当前 pytest policy 的 runtime binding
        path_project_root  # 复用调用方已验证的 binding
        if isinstance(path_project_root, dict) and "roles" in path_project_root  # 判断是否已有完整 binding
        else load_runtime_manifest(path_project, path_skill, path_manifest)  # 重新加载并校验 manifest
    )  # pytest policy 的 runtime 绑定结果。

    # 从 role 绑定读取 policy JSON。
    dict_policy = load_json_role(dict_binding, "pytest_receipt_policy")  # 已校验的 pytest policy 对象

    # default_modes 必须提供 targeted 和 full 两个逻辑入口。
    dict_default_modes = dict_policy.get("default_modes")  # policy 默认模式映射

    # 缺少默认模式时不能生成 active receipt。
    if not isinstance(dict_default_modes, dict) or not all(
        isinstance(dict_default_modes.get(str_mode), str) for str_mode in ("targeted", "full")
    ):

        # 错误只描述字段合同，不回显当前模式值。
        raise ValueError("> ERR: [Python] pytest policy default_modes is invalid")

    # 将 policy 和 manifest 摘要一并返回给 active receipt caller。
    str_policy_hash = next(  # 提取已校验策略角色的内容摘要，确保新回执绑定同一份策略事实
        role["content_sha256"]  # 当前 policy role 摘要字段
        for role in dict_binding["roles"].values()  # 遍历已校验 role
        if isinstance(role, dict) and role.get("name") == "pytest_receipt_policy"  # 仅匹配声明为 pytest policy 的角色记录
    )

    # 读取与策略同一 binding 的 manifest 摘要。
    str_manifest_hash = dict_binding["manifest_sha256"]  # runtime manifest 内容摘要

    # 按 mode_name 建立 policy 模式索引，供命令解析复用。
    dict_modes = {
        str(item.get("mode_name")): item  # mode 名到声明对象的映射
        for item in dict_policy.get("modes", [])  # policy 声明的模式列表
        if isinstance(item, dict) and item.get("mode_name")  # 过滤无效模式声明
    }

    # 返回包含 policy 与两个合同摘要的活动绑定。
    return PytestReceiptPolicy({
        "policy": dict_policy,
        "policy_sha256": str_policy_hash,
        "runtime_manifest_sha256": str_manifest_hash,
        "binding": dict_binding,
        "receipt_schema": dict_policy.get("receipt_schema"),
        "freshness_seconds": dict_policy.get("freshness_seconds"),
        "default_targeted_mode": dict_policy["default_modes"]["targeted"],
        "default_full_mode": dict_policy["default_modes"]["full"],
        "modes": dict_modes,
    })

# 计划中的 canonical 名称保留为显式别名入口。
def load_pytest_receipt_policy(
    path_project_root: Path | dict[str, object] | None = None,
    path_skill_root: Path | None = None,
    path_manifest: Path | None = None,
) -> dict[str, Any]:
    """返回与 load_pytest_policy 相同的 active policy 绑定。

    参数：path_project_root、path_skill_root 和 path_manifest 为可选运行时覆盖。
    返回：经过 policy、runtime manifest 摘要校验的活动绑定。
    """

    # 两个入口保持同一 policy/hash 语义。
    return load_pytest_policy(path_project_root, path_skill_root, path_manifest)

# 按 policy 模式模板解析一条逻辑 pytest 命令。
def resolve_pytest_command(
    dict_policy_binding: dict[str, Any],
    str_mode_name: str,
    dict_parameters: dict[str, object] | None = None,
) -> str:
    """从 policy 的 mode template 解析逻辑 pytest 命令。

    参数：dict_policy_binding 为 policy 或活动绑定；str_mode_name 为 mode 标识；dict_parameters 为模板参数。
    返回：由 policy 模板展开出的逻辑命令文本。
    异常：mode 不存在、参数未声明或模板展开失败时抛出 ValueError。
    """

    # mode 列表是命令模板唯一来源。
    dict_policy = dict_policy_binding.get("policy", dict_policy_binding)  # policy 顶层对象

    # 只从映射中读取 mode 声明，其他形状按空列表处理。
    list_modes = dict_policy.get("modes", []) if isinstance(dict_policy, dict) else []  # policy 模式列表

    # 从声明列表中选择调用方请求的 mode。
    dict_mode = next(  # 当前 mode 声明
        (
            item  # mode 声明对象
            for item in list_modes  # 遍历 policy 模式
            if isinstance(item, dict) and item.get("mode_name") == str_mode_name  # 选择目标 mode
        ),
        None,  # 未找到 mode 时返回空值
    )

    # 未知 mode 不能让调用方自行拼接命令替代 policy。
    if not isinstance(dict_mode, dict):

        # 未声明 mode 不允许生成替代命令。
        raise ValueError("> ERR: [Python] pytest policy mode is unknown")

    # 仅允许 policy 声明的参数进入 template。
    dict_values = dict(dict_parameters or {})  # 调用方提供的模板参数

    # 读取该 mode 声明的参数白名单。
    object_rules = dict_mode.get("parameter_rules", {})  # 参数规则对象

    # 每个调用参数都必须在 policy 白名单中。
    if isinstance(object_rules, dict):

        # 遍历调用方参数并拒绝未声明字段。
        for str_name in dict_values:

            # 未声明参数不能进入命令模板展开。
            if str_name not in object_rules:

                # 报告 policy 未声明的调用参数。
                raise ValueError("> ERR: [Python] pytest policy parameter is undeclared")

    # 由 policy 模板生成最终逻辑命令。
    try:

        # 使用已验证参数展开当前 mode 的命令模板。
        return str(dict_mode.get("command_template", "")).format(**dict_values)

    # 缺少模板字段或模板格式错误时保持稳定错误边界。
    except (KeyError, ValueError):

        # 模板展开失败时返回稳定的 policy 错误类型。
        raise ValueError("> ERR: [Python] pytest policy command template is invalid") from None

# 兼容从 evidence_validation 入口调用版本面准备。
def prepare_release_version(*args: object, **kwargs: object) -> dict[str, object]:
    """兼容从 evidence_validation 入口调用版本面准备。

    参数：args 与 kwargs 原样转发给 docs release facade。
    返回：版本面准备入口生成的结构化结果。
    异常：下游 release facade 的校验错误原样传播。
    """

    # 直接脚本加载时补充同一技能的 docs 模块目录。
    path_docs_dir = Path(__file__).resolve().parents[1] / "docs"  # docs facade 模块目录

    # 仅当当前解释器尚未注册 docs 目录时追加搜索路径。
    if str(path_docs_dir) not in sys.path:

        # 当前进程只追加已解析的 docs 目录。
        sys.path.insert(0, str(path_docs_dir))

    # 延迟导入避免 docs facade 与 evidence facade 形成初始化循环。
    from manage_docs_release import prepare_release_version as prepare_surface

    # 转发参数并返回下游版本面准备结果。
    return prepare_surface(*args, **kwargs)
