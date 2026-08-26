"""加载受信任的 runtime manifest 与其 role 合同。"""

# 延迟注解求值，兼容源码态和安装态的直接脚本入口。
from __future__ import annotations

# 标准库提供摘要、JSON、路径 containment 与通用类型。
import hashlib
import json
from pathlib import Path
from typing import Any, NoReturn

# 调用方使用映射接口读取 role 证据，业务值仍由 JSON 提供。
class RuntimeContractRole(dict[str, object]):
    """已验证 role 证据的映射容器。"""

# binding 同时保存可信根、manifest 摘要和 role 映射。
class RuntimeContractBinding(dict[str, object]):
    """已验证 runtime binding 的映射容器，并提供计划字段属性。"""

    # 公开项目可信根，供调用方构造受 containment 保护的 role 路径。
    @property

    # 该属性只暴露 loader 已确认的项目根。
    def project_root(self) -> Path:
        """返回项目可信根。

        参数：无；属性从已验证 binding 的 roots 映射读取。
        返回：已经解析的项目根路径。
        """

        # 从已验证的可信根映射中取出项目根。
        return self["roots"]["project_root"]

    # 公开技能可信根，确保 role 与 schema 的解析基准保持一致。
    @property

    # 该属性只暴露 loader 已确认的技能根。
    def skill_root(self) -> Path:
        """返回技能可信根。

        参数：无；属性从已验证 binding 的 roots 映射读取。
        返回：已经解析的技能根路径。
        """

        # 从同一份 binding 中取得技能根，避免调用方自行猜测目录。
        return self["roots"]["skill_root"]

    # 公开可选报告根，缺失时保留显式的 None 状态。
    @property

    # 该属性保留报告根未配置时的可选语义。
    def reports_root(self) -> Path | None:
        """返回可选报告可信根。

        参数：无；属性从已验证 binding 的 roots 映射读取。
        返回：报告根路径，或表示未配置报告根的 None。
        """

        # 报告根不是所有运行模式都需要，因此保留可选值。
        return self["roots"].get("reports_root")

    # 公开 manifest 文件路径，绑定的摘要与此文件一一对应。
    @property

    # 该属性返回与摘要绑定的 manifest 文件。
    def manifest_path(self) -> Path:
        """返回 runtime manifest 文件路径。

        参数：无；属性从已验证 binding 的顶层字段读取。
        返回：已通过可信根检查的 manifest 路径。
        """

        # 调用方只能使用 loader 已验证的 manifest 路径。
        return self["manifest_path"]

    # 公开 manifest 摘要，供 receipt 与后续证据绑定。
    @property

    # 该属性返回与 manifest 内容对应的摘要。
    def manifest_sha256(self) -> str:
        """返回 runtime manifest 的 canonical 摘要。

        参数：无；属性从已验证 binding 的摘要字段读取。
        返回：小写十六进制 SHA-256 摘要文本。
        """

        # 以字符串形式返回摘要，保持映射接口对外稳定。
        return str(self["manifest_sha256"])

    # 公开 role 记录的只读视图，避免调用方重新读取 manifest。
    @property

    # 该属性把已验证 role 映射转换为稳定序列。
    def roles(self) -> tuple[RuntimeContractRole, ...]:
        """返回已验证 role 的只读 tuple 视图。

        参数：无；属性读取 binding 中已经完成校验的 role 映射。
        返回：仅包含映射对象的 role tuple。
        """

        # role 映射只用于生成稳定的只读视图。
        object_roles = self.get("roles", {})  # 已验证的 role 映射

        # 外部篡改 binding 形状时返回空视图而不猜测数据。
        if not isinstance(object_roles, dict):

            # 非映射值不具备可枚举的 role 语义。
            return ()

        # 过滤出仍保持映射形状的 role 记录。
        return tuple(object_role for object_role in object_roles.values() if isinstance(object_role, dict))

# 合同错误携带可机器消费且不含绝对路径的结构化载荷。
class RuntimeContractError(ValueError):
    """表示 runtime manifest 或 role contract 无法使用。"""

    # 保存调用方需要记录的字段级诊断。
    def __init__(self, message: str, payload: dict[str, object]) -> None:
        """初始化合同错误载荷。

        参数：message 为带有错误协议前缀的可见文本；payload 为脱敏的字段级错误映射。
        返回：无；异常实例保存 payload 并使用 message 作为异常文本。
        """

        # 载荷由 loader 统一生成，避免调用方猜测错误结构。
        self.payload = payload  # 供调用方记录的字段级错误

        # 异常文本由调用方显式绑定协议前缀，详细信息只放在 payload。
        super().__init__(message)

# 构造所有合同 loader 共用的字段级错误。
def contract_error(
    code: str,
    field: str,
    message: str,
    *,
    path_class: str = "",
) -> dict[str, object]:
    """返回脱敏的合同错误对象。

    参数：code、field、message 描述错误；path_class 描述路径类别。
    返回：固定字段集合组成的错误映射。
    """

    # 字段集合固定，便于 release/evidence caller 统一处理。
    return {
        "error_code": code,
        "field": field,
        "message": message,
        "path_class": path_class,
    }

# 把合同错误转换为 fail-closed 异常。
def _fail(
    code: str,
    field: str,
    message: str,
    *,
    path_class: str = "",
) -> NoReturn:
    """抛出携带结构化 payload 的 RuntimeContractError。

    参数：code、field、message 描述错误；path_class 描述路径类别。
    返回：不返回；始终抛出 RuntimeContractError。
    """

    # 将字段级错误转换成不回显绝对路径或远端内容的脱敏载荷。
    dict_payload = contract_error(code, field, message, path_class=path_class)  # 结构化合同错误

    # 未验证的合同不得继续进入调用方。
    raise RuntimeContractError(
        "> ERR: [Python] runtime contract validation failed",
        dict_payload,
    )

# 读取 JSON 对象并检查根形状。
def _load_json_object(path_file: Path, field: str) -> dict[str, Any]:
    """加载一个 UTF-8 JSON 对象。

    参数：path_file 为合同文件；field 为错误字段名。
    返回：JSON 顶层对象映射。
    """

    # 解析文件内容，统一捕获文件与 JSON 错误。
    try:

        # 读取合同文件并解析顶层 JSON 对象。
        dict_payload = json.loads(path_file.read_text(encoding="utf-8"))  # JSON 顶层对象

    # 解析失败必须在 except 分支统一转换成结构化错误。
    except (OSError, UnicodeError, json.JSONDecodeError):

        # 文件不可读或 JSON 损坏时只报告合同类别并停止后续 role 验证。
        _fail("RUNTIME_CONTRACT_JSON", field, "contract JSON cannot be loaded", path_class="contract")

    # role 和 schema 合同必须以对象作为根节点。
    if not isinstance(dict_payload, dict):

        # 仅允许对象根节点，避免调用方对列表或标量进行错误推断。
        _fail("RUNTIME_CONTRACT_JSON", field, "contract JSON must be an object", path_class="contract")

    # 类型检查后返回 JSON 映射。
    return dict_payload

# 计算合同声明使用的 canonical 或原始字节摘要。
def _content_hash(path_file: Path, hash_mode: str, field: str) -> str:
    """返回 role 文件的 SHA-256 摘要。

    参数：path_file 为合同文件；hash_mode 为摘要模式；field 为错误字段。
    返回：小写 SHA-256 文本。
    """

    # canonical_json 先解析再以稳定键序列化。
    if hash_mode == "canonical_json":

        # 规范化 JSON 对象，保证键序与分隔符固定后再计算内容摘要。
        dict_payload = _load_json_object(path_file, field)  # 用于摘要的 JSON 对象

        # 把排序后的合同文本固定为摘要输入，避免同一内容因格式差异得到不同哈希。
        bytes_content = (  # 保存规范化合同文本，后续摘要只消费这份确定字节以避免格式差异改变结果
            # 序列化键值内容，保留 Unicode 并固定分隔符。
            json.dumps(dict_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))  # 按固定键序生成无空格合同文本
            + "\n"  # 固定 canonical 文本的终止换行
        ).encode("utf-8")  # canonical UTF-8 字节

    # 原始字节模式用于非 JSON role，避免文本解码改变内容。
    elif hash_mode == "sha256_bytes":

        # 非 JSON role 直接读取原始字节并保留读取异常边界。
        try:

            # 读取文件原始字节，摘要不经过换行转换。
            bytes_content = path_file.read_bytes()  # 原始合同字节

        # 原始字节读取失败时转换为不泄露路径的合同错误。
        except OSError:

            # 不把本地路径或系统异常文本暴露给调用方。
            _fail("RUNTIME_CONTRACT_BYTES", field, "contract bytes cannot be loaded", path_class="contract")

    # 未声明的摘要模式不能由 loader 自行推断。
    else:

        # 未知算法直接终止，避免生成不可复现的合同摘要。
        _fail("RUNTIME_CONTRACT_HASH", field, "contract hash mode is unsupported", path_class="manifest")

    # 返回小写十六进制摘要。
    return hashlib.sha256(bytes_content).hexdigest()

# 验证 manifest-relative 路径不包含穿越、通配或空段。
def _safe_relative(value_path: object, field: str) -> Path:
    """返回安全的相对 Path。

    参数：value_path 为 manifest 路径值；field 为错误字段。
    返回：通过穿越、通配和空段检查的相对 Path。
    """

    # 统一分隔符后检查每一个路径段。
    string_path = str(value_path or "").strip()  # 规范化 manifest-relative 文本

    # 将不同平台分隔符统一后逐段检查 containment 风险。
    list_parts = string_path.replace("\\", "/").split("/")  # 待验证的路径段

    # 绝对路径、空段和通配符都不能来自 manifest。
    if (
        not string_path
        or "*" in string_path
        or Path(string_path).is_absolute()
        or any(part in {"", ".", ".."} for part in list_parts)
    ):

        # 绝对路径、空段和穿越段都会破坏 manifest 的可信边界。
        _fail(
            "RUNTIME_CONTRACT_PATH",
            field,
            "contract-relative path is unsafe",
            path_class="manifest-relative",
        )

    # 返回尚未绑定 trusted root 的相对路径。
    return Path(*list_parts)

# 将 role 声明绑定到一个可信 root。
def _role_base(
    dict_roots: dict[str, Path | None],
    str_base_kind: str,
    str_role_name: str,
) -> Path:
    """返回 role 声明的 trusted root。

    参数：dict_roots 为可信根映射；str_base_kind 为根类别；str_role_name 为 role 名。
    返回：已解析的 trusted root。
    """

    # 根类别只能引用 manifest binding 明确提供的 root。
    path_base = dict_roots.get(str_base_kind)  # role 声明的可信根

    # 只接受 manifest binding 明确提供且已经解析的 Path。
    if not isinstance(path_base, Path):

        # 缺失 reports root 时拒绝猜测其他目录。
        _fail(
            "RUNTIME_CONTRACT_BASE",
            str_role_name,
            "declared contract base is unavailable",
            path_class=str_base_kind,
        )

    # 返回解析后的 trusted root，供 role 文件做 containment 检查。
    return path_base.resolve()

# 验证 role 文件、schema 和摘要并生成 role 证据。
def _validate_role(
    dict_role: dict[str, object],
    dict_roots: dict[str, Path | None],
    path_skill_root: Path,
) -> RuntimeContractRole:
    """返回一个已完成 containment/hash 校验的 role 记录。

    参数：dict_role 为 manifest role；dict_roots 为可信根；path_skill_root 为技能根。
    返回：已完成文件、schema 和摘要校验的 role 映射。
    """

    # 读取 role 逻辑名称并用于后续错误定位。
    str_role_name = str(dict_role.get("name", "")).strip()  # role 逻辑名称

    # 读取 role 的 trusted root 类别。
    str_base_kind = str(dict_role.get("base_kind", "")).strip()  # 当前 role 的根类别

    # 验证 manifest 声明的 role 相对路径。
    path_relative = _safe_relative(dict_role.get("relative_path"), "relative_path")  # role 相对路径

    # 读取 role 内容摘要算法。
    str_hash_mode = str(dict_role.get("hash_mode", "")).strip()  # role 摘要模式

    # 读取 manifest 声明的内容摘要。
    str_expected_hash = str(dict_role.get("content_sha256", "")).strip().lower()  # 期望内容摘要

    # 读取 role 是否必须存在的布尔标志。
    object_required = dict_role.get("required")  # role 必选标记

    # 读取可选 schema 相对路径，稍后固定到技能根。
    object_schema_relative = dict_role.get("schema_relative_path")  # 可选 schema 相对路径

    # schema 相对路径存在时使用同一套安全路径规则。
    path_schema_relative = (
        # 解析 manifest 声明的 schema 相对路径。
        _safe_relative(object_schema_relative, "schema_relative_path")  # manifest 声明的 schema 位置
        if object_schema_relative is not None  # 判断 schema 路径是否声明
        else None  # 未声明时保留可选空值
    )

    # 只有声明 schema 路径时才读取其期望摘要。
    str_expected_schema = (
        # 规范化 schema 摘要文本，便于后续比较。
        str(dict_role.get("schema_sha256", "")).strip().lower()  # 期望 schema 摘要
        if path_schema_relative is not None  # 仅为声明过的 schema 读取摘要
        else None  # 无 schema 时不生成摘要
    )

    # required/hash/content 三项必须同时存在。
    if (
        not str_role_name
        or not isinstance(object_required, bool)
        or len(str_expected_hash) != 64
    ):

        # 必选字段缺失时拒绝构造不完整的 role 记录并阻止进入 binding。
        _fail(
            "RUNTIME_CONTRACT_ROLE",
            str_role_name or "roles",
            "runtime role fields are invalid",
            path_class="manifest",
        )

    # 组合 role 路径并验证 trusted root containment。
    path_base = _role_base(dict_roots, str_base_kind, str_role_name)  # 当前 role 的可信根路径

    # 组合可信根和相对路径，形成 role 文件候选位置。
    path_role = (path_base / path_relative).resolve()  # role 解析路径

    # 文件必须保持在声明的 trusted root 内且不能是符号链接。
    if (
        not path_role.is_relative_to(path_base)
        or not path_role.is_file()
        or path_role.is_symlink()
    ):

        # 可选 role 缺失时保留不可用状态，不伪造文件证据。
        if not object_required:

            # 返回已验证字段，让调用方显式处理 optional role。
            return {
                "name": str_role_name,
                "base_kind": str_base_kind,
                "relative_path": path_relative.as_posix(),
                "schema_relative_path": None,
                "required": False,
                "available": False,
                "hash_mode": str_hash_mode,
                "content_sha256": str_expected_hash,
                "schema_sha256": str_expected_schema,
            }

        # 缺失、目录和符号链接都不能成为 role。
        _fail(
            "RUNTIME_CONTRACT_ROLE_FILE",
            str_role_name,
            "runtime role file is unavailable",
            path_class=str_base_kind,
        )

    # 摘要校验先于 role 对象向调用方暴露。
    str_actual_hash = _content_hash(path_role, str_hash_mode, str_role_name)  # role 实际摘要

    # 只有摘要完全匹配时才允许继续暴露 role。
    if str_actual_hash != str_expected_hash:

        # stale role 必须 fail closed。
        _fail(
            "RUNTIME_CONTRACT_ROLE_HASH",
            str_role_name,
            "runtime role hash mismatch",
            path_class=str_base_kind,
        )

    # schema role 固定相对 skill root 并执行同样 containment 检查。
    if path_schema_relative is not None:

        # 将 schema 相对路径绑定到技能可信根。
        path_schema = (path_skill_root / path_schema_relative).resolve()  # schema 文件候选路径

        # schema 文件也必须位于 skill root 内且不能是符号链接。
        if (
            not path_schema.is_relative_to(path_skill_root)
            or not path_schema.is_file()
            or path_schema.is_symlink()
        ):

            # schema 文件本身不可用时停止。
            _fail(
                "RUNTIME_CONTRACT_SCHEMA",
                str_role_name,
                "runtime role schema is unavailable",
                path_class="skill_root",
            )

        # 计算 schema canonical 摘要，供声明值比对。
        str_schema_hash = _content_hash(path_schema, "canonical_json", str_role_name)  # 当前 schema 摘要

        # schema 摘要漂移时不能继续复用旧的 role 证据。
        if str_schema_hash != str_expected_schema:

            # schema 摘要漂移不能被忽略。
            _fail(
                "RUNTIME_CONTRACT_SCHEMA_HASH",
                str_role_name,
                "runtime role schema mismatch",
                path_class="skill_root",
            )

    # 保存相对路径和摘要，调用方无需重新解析 manifest。
    return {
        "name": str_role_name,
        "base_kind": str_base_kind,
        "relative_path": path_relative.as_posix(),
        "schema_relative_path": (
            path_schema_relative.as_posix() if path_schema_relative is not None else None
        ),
        "required": bool(object_required),
        "available": True,
        "hash_mode": str_hash_mode,
        "content_sha256": str_expected_hash,
        "schema_sha256": str_expected_schema,
    }

# 加载 runtime manifest 并返回唯一 canonical binding。
def load_runtime_manifest(
    path_project_root: Path,
    path_skill_root: Path,
    path_manifest: Path | None = None,
    path_reports_root: Path | None = None,
) -> RuntimeContractBinding:
    """加载并校验 runtime manifest。

    参数：path_project_root、path_skill_root 为可信运行时根；path_manifest 和 path_reports_root 可覆盖默认值。
    返回：包含 trusted roots、role 摘要和 manifest 摘要的 binding。
    异常：任何路径、schema、文件或摘要漂移都抛出 RuntimeContractError。
    """

    # 解析调用方提供的项目根。
    path_project = path_project_root.resolve()  # 项目可信根

    # 解析技能根，作为 manifest 与 schema 的 containment 基准。
    path_skill = path_skill_root.resolve()  # 技能可信根

    # 解析可选报告根，不配置时保持 None。
    path_reports = path_reports_root.resolve() if path_reports_root is not None else None  # 可选报告根

    # 选择显式 manifest 或技能配置中的默认 manifest。
    path_manifest_file = (
        path_manifest if path_manifest is not None else path_skill / "config" / "runtime-manifest.json"  # manifest 候选路径
    ).resolve()

    # manifest 自身必须是普通文件且不能是符号链接。
    if (
        not path_manifest_file.is_file()
        or path_manifest_file.is_symlink()
        or not path_manifest_file.is_relative_to(path_skill)
    ):

        # manifest 缺失、越界或为链接时直接阻断加载。
        _fail(
            "RUNTIME_CONTRACT_MANIFEST",
            "manifest_path",
            "runtime manifest is unavailable",
            path_class="skill_root",
        )

    # manifest 根对象必须先通过 JSON 结构检查。
    dict_manifest = _load_json_object(path_manifest_file, "manifest")  # 已解析的 manifest 对象

    # 只接受当前 loader 支持的 manifest schema。
    if dict_manifest.get("schema_version") != 1:

        # 未知 schema 不可兼容猜测。
        _fail(
            "RUNTIME_CONTRACT_SCHEMA",
            "manifest.schema_version",
            "runtime manifest schema is unsupported",
            path_class="skill_root",
        )

    # roles 列表是调用方可见 binding 的唯一来源。
    object_roles = dict_manifest.get("roles")  # manifest 中的 role 声明列表

    # role 列表为空或形状错误时不能形成可用 binding。
    if not isinstance(object_roles, list) or not object_roles:

        # 空或错误形状的 role 集合不能发布。
        _fail("RUNTIME_CONTRACT_ROLE", "roles", "runtime roles are invalid", path_class="manifest")

    # trusted roots 不包含未解析的字符串路径。
    dict_roots: dict[str, Path | None] = {  # loader 提供的可信根映射
        "project_root": path_project,  # 项目根供 project-base role 使用
        "skill_root": path_skill,  # 技能根供 skill-base role 使用
        "reports_root": path_reports,  # 可选报告根供 reports-base role 使用
    }

    # 逐项校验 role 并拒绝重复逻辑名称。
    dict_roles: dict[str, RuntimeContractRole] = {}  # 已验证 role 映射

    # 遍历 manifest 声明，逐个生成绑定证据。
    for object_role in object_roles:

        # 每个 role 声明必须保持对象形状。
        if not isinstance(object_role, dict):

            # role 顶层必须保持对象形状。
            _fail("RUNTIME_CONTRACT_ROLE", "roles", "runtime role must be an object", path_class="manifest")

        # 生成当前 role 的完整文件与摘要证据。
        runtime_contract_role_record = _validate_role(object_role, dict_roots, path_skill)  # 当前 role 证据

        # 读取 role 名称作为 binding 的唯一索引。
        str_role_name = str(runtime_contract_role_record["name"])  # 当前 role 名称

        # 重名 role 会使后续路径解析产生歧义。
        if str_role_name in dict_roles:

            # 重复 role 会让调用方产生歧义。
            _fail("RUNTIME_CONTRACT_ROLE", str_role_name, "runtime role is duplicated", path_class="manifest")

        # 将唯一 role 记录写入 binding 索引。
        dict_roles[str_role_name] = runtime_contract_role_record  # 登记唯一 role

    # manifest 摘要绑定角色列表和 trusted roots 的当前事实。
    str_manifest_hash = _content_hash(path_manifest_file, "canonical_json", "manifest")  # 本次 binding 的 manifest 摘要

    # 先整理通过 containment 与摘要核验的核心索引，确保返回对象只承载可信证据。
    dict_binding_payload = {  # 保存已通过路径与摘要核验的证据，后续解析与回执绑定都复用这份载荷
        "roots": dict_roots,  # loader 解析的可信根集合
        "roles": dict_roles,  # 已校验的 role 证据
        "manifest_path": path_manifest_file,  # manifest 绝对路径
        "manifest_sha256": str_manifest_hash,  # 绑定 manifest 内容的稳定摘要
    }

    # 补充调用方约定的顶层根字段，保持映射接口兼容。
    dict_binding_payload.update({
        "project_root": path_project,  # 顶层项目根字段
        "skill_root": path_skill,  # 顶层技能根字段
        "reports_root": path_reports,  # 顶层可选报告根字段
    })

    # 返回完成验证的 binding，后续 caller 只能使用此对象。
    return RuntimeContractBinding(dict_binding_payload)

# 计划中的 canonical 名称保留为显式入口。
def load_runtime_contract_binding(
    path_project_root: Path,
    path_skill_root: Path,
    path_manifest: Path | None = None,
    path_reports_root: Path | None = None,
) -> RuntimeContractBinding:
    """返回 runtime manifest 的 canonical binding。

    参数：path_project_root 和 path_skill_root 为可信根；path_manifest 与 path_reports_root 为可选覆盖路径。
    返回：经过 fail-closed 校验的 runtime binding。
    异常：任一合同字段、文件路径或摘要不匹配时抛出 RuntimeContractError。
    """

    # 两个入口共用唯一 fail-closed 实现。
    return load_runtime_manifest(path_project_root, path_skill_root, path_manifest, path_reports_root)

# 从 binding 中解析一个已声明 role 的绝对路径。
def runtime_role_path(
    dict_binding: RuntimeContractBinding,
    string_role_name: str,
) -> Path:
    """返回受 containment 保护的 role 文件路径。

    参数：dict_binding 为已验证 binding；string_role_name 为 role 名称。
    返回：role 的绝对路径。
    异常：role 缺失、根类别漂移或路径离开 trusted root 时抛出 RuntimeContractError。
    """

    # 建立 role 名到记录的索引入口。
    dict_roles = dict_binding.get("roles")  # 当前 binding 的 role 索引

    # 仅从已验证索引中选择调用方请求的 role。
    dict_role = dict_roles.get(string_role_name) if isinstance(dict_roles, dict) else None  # 请求的 role 证据

    # 未声明的 role 不允许调用方从名称推断文件。
    if not isinstance(dict_role, dict):

        # 未声明 role 不允许调用方猜测文件名。
        _fail(
            "RUNTIME_CONTRACT_ROLE_MISSING",
            string_role_name,
            "runtime role is not declared",
            path_class="binding",
        )

    # 读取 binding 提供的可信根索引。
    dict_roots = dict_binding.get("roots")  # binding 的可信根索引

    # 读取 role 声明的根类别。
    str_base_kind = str(dict_role.get("base_kind", ""))  # role 声明的根类别

    # 按根类别解析 role 的 trusted root。
    path_base = dict_roots.get(str_base_kind) if isinstance(dict_roots, dict) else None  # role 对应可信根

    # 只有 Path 类型的根才能参与后续 containment。
    if not isinstance(path_base, Path):

        # role 根类别无法解析时停止，避免猜测替代目录。
        _fail(
            "RUNTIME_CONTRACT_BASE",
            string_role_name,
            "bound contract base is unavailable",
            path_class=str_base_kind,
        )

    # 将 role 相对路径解析为 containment 候选位置。
    path_candidate = (path_base / Path(str(dict_role.get("relative_path", "")))).resolve()  # 当前 role 的候选路径

    # 每次解析都重新验证 containment，防止运行中 binding 或文件漂移。
    if (
        not path_candidate.is_relative_to(path_base.resolve())
        or not path_candidate.is_file()
        or path_candidate.is_symlink()
    ):

        # binding 被外部修改或文件已漂移时 fail closed。
        _fail(
            "RUNTIME_CONTRACT_CONTAINMENT",
            string_role_name,
            "role path escapes or leaves root",
            path_class="resolved",
        )

    # 返回已经通过 containment 的 role 路径。
    return path_candidate

# 读取一个已验证的 JSON role。
def load_json_role(
    dict_binding: RuntimeContractBinding,
    string_role_name: str,
) -> dict[str, Any]:
    """返回 role JSON 对象。

    参数：dict_binding 为已验证 binding；string_role_name 为 JSON role 名称。
    返回：JSON 顶层对象映射。
    """

    # 解析并验证 role 文件路径。
    path_role = runtime_role_path(dict_binding, string_role_name)  # role 文件路径

    # 读取已绑定 JSON role 并校验顶层对象形状。
    dict_payload = _load_json_object(path_role, string_role_name)  # 已验证的 role JSON 对象

    # 返回经过 manifest 摘要和对象形状检查的 role。
    return dict_payload
