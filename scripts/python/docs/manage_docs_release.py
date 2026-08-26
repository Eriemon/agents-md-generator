"""聚合文档发布策略、打包与门禁实现分片。"""

# 延迟注解求值以兼容直接脚本执行。
from __future__ import annotations

# 标准库按明确文件位置加载验证器，并定位当前模块同目录的实现分片。
import importlib.util
import hashlib
import json
from pathlib import Path
import re
import sys
from types import ModuleType
from typing import Any

# 验证器按文件加载，避免独立导入本分片时依赖聚合入口修改 sys.path。
def _load_test_evidence_module() -> ModuleType:
    """加载不透明测试证据验证模块。

    参数：无。
    返回：从当前源码树明确加载的验证模块。
    异常：验证器文件不能形成可执行模块规格时抛出 RuntimeError。
    """

    # 明确文件路径不受调用方模块搜索顺序影响。
    path_evidence_module = Path(__file__).resolve().parents[1] / "verify" / "evidence_validation.py"  # 验证模块路径。

    # sibling 验证器目录为 evidence_validation 的显式依赖搜索根。
    path_verify_directory = path_evidence_module.parent.resolve()  # 当前 Skill 的 verify 目录。

    # 记录本次临时导入是否修改了当前进程的模块搜索路径。
    str_verify_directory = str(path_verify_directory)  # 规范化 verify 目录文本。

    # 默认不改变调用方已有的模块搜索路径。
    bool_verify_directory_added = False  # 当前调用是否新增搜索路径。

    # 动态执行前补充 sibling 模块的唯一搜索根。
    if str_verify_directory not in sys.path:

        # 只在本次验证器加载期间临时加入当前进程路径。
        sys.path.insert(0, str_verify_directory)

        # 记录本次调用需要在执行结束时回收该路径。
        bool_verify_directory_added = True  # 标记本次调用新增的搜索路径。

    # 独立模块名避免复用环境中可能存在的同名验证器。
    module_type_spec = importlib.util.spec_from_file_location(  # 验证模块加载规格。
        "agents_evidence_validation",  # 当前源码验证器的隔离模块名。
        path_evidence_module,  # 当前源码验证器的明确位置。
    )

    # 缺失加载器表示源码布局或解释器导入机制已损坏。
    if module_type_spec is None or module_type_spec.loader is None:

        # 发布证据验证器不可用时必须阻断发布流程。
        raise RuntimeError("> ERR: [Python] test evidence validator could not be loaded")

    # 模块对象承载验证器执行后公开的稳定 API。
    module_evidence = importlib.util.module_from_spec(module_type_spec)  # 隔离验证模块。

    # 动态模块先登记稳定名称，保证 facade 的 sibling helper 解析到同一实例。
    sys.modules["evidence_validation"] = module_evidence  # 为验证 facade 保留稳定绝对导入名称。

    # 延迟执行避免导入本发布分片时产生跨目录副作用。
    try:

        # sibling 验证器在临时 verify 搜索根内解析其兼容入口。
        module_type_spec.loader.exec_module(module_evidence)

    # 无论 sibling 加载成功与否，都回收本次临时状态。
    finally:

        # 执行结束后撤销本次新增路径，避免污染调用方后续导入。
        if bool_verify_directory_added and str_verify_directory in sys.path:

            # 只移除本函数添加的规范化 sibling 路径。
            sys.path.remove(str_verify_directory)

    # 调用方只读取模块公开验证函数。
    return module_evidence

# 公共包装器保持发布分片既有调用签名，并透传本地或历史合同开关。
def validate_project_test_evidence(
    path_project: Path,
    str_receipt_raw: str,
    int_freshness_seconds: int = 24 * 60 * 60,
    bool_required: bool = False,
    bool_immutable_history: bool = False,
) -> dict[str, Any]:
    """调用不透明测试证据验证器而不依赖导入顺序。

    参数：path_project 为仓库根，str_receipt_raw 为收据路径。
    参数：int_freshness_seconds 为最大证据年龄，bool_required 控制缺失收据策略。
    参数：bool_immutable_history 仅允许旧 schema=1 或历史 local-test-evidence 兼容验证。
    返回：验证器生成的脱敏结构化报告。
    """

    # 每次调用从当前源码树解析验证器，避免环境同名模块污染。
    module_type_evidence = _load_test_evidence_module()  # 当前源码验证模块。

    # 公开函数由固定产品模块提供，缺失时让 AttributeError 明确暴露合同损坏。
    return module_type_evidence.validate_project_test_evidence(
        path_project,  # 待验证项目根。
        str_receipt_raw,  # 调用方提供的收据路径。
        int_freshness_seconds,  # 证据新鲜度上限。
        bool_required,  # 发布态收据必需策略。
        bool_immutable_history,  # 仅旧档案允许历史收据合同。
    )

# 分片加载器保持文档发布 API 的单模块入口。
def _load_module_shards(tuple_shard_names: tuple[str, ...]) -> None:
    """加载文档发布流程的实现分片。

    参数：tuple_shard_names 为按依赖顺序排列的同目录分片名。
    返回：无业务返回值；分片定义直接写入当前模块命名空间。
    """

    # 当前入口目录包含策略、打包和门禁三个分片。
    path_shard_dir = Path(__file__).resolve().parent  # 分片文件查找目录。

    # 固定加载顺序保留策略、打包和门禁之间的符号依赖。
    for str_shard_name in tuple_shard_names:

        # 当前分片路径用于读取源码和保留错误来源。
        path_shard = path_shard_dir / str_shard_name  # 当前待加载分片。

        # 编译对象绑定真实文件名以支持发布故障定位。
        code_shard = compile(path_shard.read_text(encoding="utf-8"), str(path_shard), "exec")  # 当前分片代码对象。

        # 分片共享当前模块命名空间以维持既有调用合同。
        exec(code_shard, globals())

# 策略定义先于打包和门禁实现加载。
_load_module_shards(
    (
        "release_policy.py",
        "release_package.py",
        "release_gate.py",
    )
)

# 版本面解析入口由 runtime manifest 提供配置来源。
def resolve_version_surface(
    path_project_root: Path,
    path_skill_root: Path,
    str_requested_version: str,
    path_manifest: Path | None = None,
) -> dict[str, object]:
    """解析版本面并返回当前版本绑定摘要。

    参数：path_project_root 和 path_skill_root 为项目/技能根目录。
    参数：str_requested_version 为调用方提供的版本文本。
    参数：path_manifest 为可选 runtime manifest 覆盖。
    返回：包含版本面合同、请求版本和摘要的映射。
    """

    # 共享 loader 由当前脚本目录向 common 目录解析。
    path_common_dir = Path(__file__).resolve().parents[1] / "common"  # 共享运行时目录

    # 直接模块加载时补充共享目录搜索路径。
    if str(path_common_dir) not in sys.path:

        # 当前进程范围内添加共享模块目录。
        sys.path.insert(0, str(path_common_dir))

    # 延迟导入保证旧分片调用不改变初始化顺序。
    from runtime_contracts import load_json_role, load_runtime_manifest

    # 读取当前运行时 manifest 和 version surface role。
    dict_binding = load_runtime_manifest(path_project_root, path_skill_root, path_manifest)  # 已校验的运行时绑定

    # 从 role 读取版本面声明，避免入口维护 surface 枚举。
    dict_surfaces = load_json_role(dict_binding, "version_surfaces")  # 已校验的版本面合同

    # 每个 surface 由声明的根类别解析为可审计的路径事实。
    list_surfaces = _resolve_declared_surfaces(dict_binding, dict_surfaces.get("surfaces", []))  # 版本面绑定列表

    # 预览结果使用 canonical JSON 计算稳定自身摘要。
    dict_result = {  # 保存版本面声明、请求版本与当前摘要，供 preview 和 receipt 共同复用
        "requested_version": str_requested_version,  # 调用方请求版本
        "surfaces": list_surfaces,  # 已解析版本面列表
        "version_surfaces_sha256": _role_hash(dict_binding, "version_surfaces"),  # 版本面合同摘要
        "runtime_manifest_sha256": dict_binding["manifest_sha256"],  # 运行时 manifest 内容摘要
    }

    # 计算预览载荷自身摘要，供后续 write receipt 绑定。
    dict_result["receipt_sha256"] = _payload_hash(dict_result)  # 版本面预览摘要

    # 返回调用方用于 preview/write 的参数绑定。
    return dict_result

# 发布计划使用更明确的 canonical 版本面入口名称。
def prepare_release_version(
    path_project_root: Path,
    path_skill_root: Path,
    str_requested_version: str,
    path_manifest: Path | None = None,
    *,
    write: bool = False,
) -> dict[str, object]:
    """返回版本面 preview，后续 write 由受管发布流程执行。

    参数：path_project_root 和 path_skill_root 为项目/技能根目录。
    参数：str_requested_version 为调用方提供的版本文本。
    参数：path_manifest 为可选 runtime manifest 覆盖，write 控制未来写入意图。
    返回：版本面绑定、写入意图和合同摘要。
    """

    # 复用只读版本面解析，避免两个入口的 selector 语义分叉。
    dict_preview = resolve_version_surface(  # 首次版本面只读预览
        path_project_root,  # 项目可信根
        path_skill_root,  # 技能可信根
        str_requested_version,  # 初次预览使用的请求版本文本
        path_manifest,  # 可选 manifest 覆盖
    )

    # 写入由同一份 surface receipt 逐项执行并重新绑定摘要。
    if write:

        # 逐项应用 contract 声明的版本面适配器。
        _write_version_surfaces(  # 受控版本面写入
            dict_preview["surfaces"],  # 已解析 surface 列表
            str_requested_version,  # 请求版本
            path_project_root,  # 项目根
            path_skill_root,  # 技能根
        )

        # 写入后重算 role 摘要，确保下一次 preview 绑定新内容。
        _refresh_manifest_role_hashes(path_skill_root)

        # 重新绑定写入后的版本面和 manifest 摘要。
        dict_preview = resolve_version_surface(  # 写入后版本面复核
            path_project_root,  # 写入复核的项目可信根
            path_skill_root,  # 写入复核的技能可信根
            str_requested_version,  # 写入复核的请求版本
            path_manifest,  # 写入复核的 manifest 覆盖
        )

    # 记录调用方明确提供的写入意图。
    dict_preview["write_requested"] = bool(write)  # 记录调用方写入意图

    # 返回统一版本面准备结果。
    return dict_preview

# 从已验证 binding 读取指定 role 摘要。
def _role_hash(dict_binding: dict[str, object], str_role_name: str) -> str:
    """从已验证 binding 读取 role 摘要。

    参数：dict_binding 为 runtime binding；str_role_name 为 role 名称。
    返回：role content_sha256 字符串。
    异常：role 不存在或形状错误时抛出 ValueError。
    """

    # 从 binding 读取 role 索引，再选择调用方请求的摘要记录。
    dict_roles = dict_binding.get("roles", {})  # 已校验 role 索引

    # 从索引中读取调用方请求的 role 记录。
    dict_role = dict_roles.get(str_role_name) if isinstance(dict_roles, dict) else None  # 当前 role 记录

    # role 记录缺失时拒绝猜测其他摘要来源。
    if not isinstance(dict_role, dict):

        # 缺失 role 时不允许猜测其他文件摘要。
        raise ValueError("> ERR: [Python] version surface role is missing")

    # 返回已校验 role 的内容摘要。
    return str(dict_role.get("content_sha256", ""))

# 计算版本面收据的 canonical 摘要。
def _payload_hash(dict_payload: dict[str, object]) -> str:
    """计算版本面收据的 canonical 摘要。

    参数：dict_payload 为待摘要的版本面映射。
    返回：不含自身 receipt 字段的 UTF-8 canonical SHA-256 摘要。
    """

    # 复制载荷，避免修改调用方当前结果。
    dict_copy = dict(dict_payload)  # 待摘要的载荷副本

    # 自身摘要字段不能参与自身哈希。
    dict_copy.pop("receipt_sha256", None)

    # 以稳定键序列化载荷并固定终止换行。
    bytes_payload = (  # 版本面载荷的 canonical 字节输入
        json.dumps(dict_copy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))  # 固定键序的版本面文本
        + "\n"  # canonical 文本终止换行
    ).encode("utf-8")

    # 返回载荷摘要供 receipt 绑定。
    return hashlib.sha256(bytes_payload).hexdigest()

# 将 version surface 声明绑定到可信根并采集前置摘要。
def _resolve_declared_surfaces(
    dict_binding: dict[str, object],
    object_surfaces: object,
) -> list[dict[str, object]]:
    """把 JSON surface 声明绑定到可信根并采集前置摘要。

    参数：dict_binding 为 runtime binding；object_surfaces 为 JSON surface 列表。
    返回：解析后的 surface 证据列表。
    异常：surface 形状、路径 containment 或文件状态不合法时抛出 ValueError。
    """

    # surface 必须以列表声明，避免调用方猜测配置结构。
    if not isinstance(object_surfaces, list):

        # 结构错误时拒绝继续解析未知 surface 数据。
        raise ValueError("> ERR: [Python] version surface list is invalid")

    # 读取 binding 提供的可信根索引。
    dict_roots = dict_binding.get("roots", {})  # surface 根类别到可信路径的索引

    # 累计所有解析后的 surface 证据。
    list_result: list[dict[str, object]] = []  # surface 证据列表

    # 逐项解析 surface 声明并验证 containment。
    for object_surface in object_surfaces:

        # 每项 surface 必须保持对象形状。
        if not isinstance(object_surface, dict):

            # 非对象条目无法提供可验证的路径与适配器字段。
            raise ValueError("> ERR: [Python] version surface entry is invalid")

        # 读取 surface 根类别。
        str_base_kind = str(object_surface.get("base_kind", ""))  # 当前 surface 的可信根类别

        # 读取并规范化 surface 相对路径。
        str_relative = str(object_surface.get("relative_path", ""))  # surface 相对路径文本

        # 拆分路径段供穿越和空段检查。
        list_parts = str_relative.replace("\\", "/").split("/")  # 用于 containment 检查的路径段

        # 按声明根类别选择可信根，禁止从相对路径猜测。
        path_base = dict_roots.get(str_base_kind) if isinstance(dict_roots, dict) else None  # 当前 surface 可信根

        # 路径必须是安全相对路径并绑定到已声明 root。
        if (
            not isinstance(path_base, Path)
            or not str_relative
            or Path(str_relative).is_absolute()
            or any(part in {"", ".", ".."} for part in list_parts)
        ):

            # 绝对路径、空段或穿越段都会破坏 surface containment。
            raise ValueError("> ERR: [Python] version surface path is unsafe")

        # 解析 surface 文件并验证其位于 trusted root 内。
        path_surface = (path_base / Path(*list_parts)).resolve()  # surface 文件路径

        # surface 文件必须存在、是普通文件且没有越界。
        if not path_surface.is_relative_to(path_base.resolve()) or not path_surface.is_file():

            # 越界、缺失或目录路径都不能参与版本写入。
            raise ValueError("> ERR: [Python] version surface file is unavailable")

        # 记录写入前文件摘要，供 release receipt 比对。
        str_before_hash = hashlib.sha256(path_surface.read_bytes()).hexdigest()  # 写入前摘要

        # 保存当前 surface 的完整声明和前置摘要。
        dict_surface_result = dict(  # 汇总当前文件根类别、适配器和摘要，供发布写入阶段复核
            role=str(object_surface.get("role", "")),  # surface 逻辑名称
            base_kind=str_base_kind,  # surface 可信根类别
            relative_path=Path(*list_parts).as_posix(),  # surface 相对路径
            adapter=str(object_surface.get("adapter", "")),  # surface 版本适配器
            selector=str(object_surface.get("selector", "")),  # 决定版本文本替换位置的选择条件
            required=bool(object_surface.get("required")),  # surface 必选标志
            before_sha256=str_before_hash,  # 写入前文件摘要
            after_sha256=str_before_hash,  # 初始写入后摘要占位
            match_count=1,  # 选择器初始匹配计数
        )

        # 将当前 surface 证据按声明顺序加入结果列表。
        list_result.append(dict_surface_result)
    
    # 返回所有通过 containment/hash 前置检查的 surface 证据。
    return list_result

# 按 adapter 对已解析的版本面执行受控替换。
def _write_version_surfaces(
    list_surfaces: list[dict[str, object]],
    str_version: str,
    path_project_root: Path,
    path_skill_root: Path,
) -> None:
    """按 adapter 对已解析的版本面执行受控替换。

    参数：list_surfaces 为前置解析的 surface 证据；str_version 为请求版本；path_project_root 与 path_skill_root 为可信根。
    返回：无；只写入已通过 selector 和 containment 检查的 surface 文件。
    异常：surface 根、selector 或文件写入失败时抛出 ValueError/OSError。
    """

    # 逐项应用版本面声明并保持写入边界受控。
    for dict_surface in list_surfaces:

        # 根据 surface 根类别解析 trusted root。
        path_base = {  # surface 根类别到可信路径的映射
            "project_root": path_project_root.resolve(),  # 写入调用方项目可信根
            "skill_root": path_skill_root.resolve(),  # 写入调用方技能可信根
        }.get(str(dict_surface["base_kind"]))

        # 未知根类别不允许猜测写入位置。
        if not isinstance(path_base, Path):

            # surface 根类别不在允许集合时停止写入。
            raise ValueError("> ERR: [Python] version surface base is invalid")

        # 解析并确认 surface 文件仍处于 trusted root 内。
        path_surface = (path_base / Path(str(dict_surface["relative_path"]))).resolve()  # 当前 surface 文件

        # 读取写入前文本，后续 selector 与 adapter 共享此快照。
        str_before = path_surface.read_text(encoding="utf-8")  # 写入前 surface 文本

        # 读取声明的 adapter 名称。
        str_adapter = str(dict_surface["adapter"])  # surface 文本适配器

        # 根据 adapter 生成请求版本后的文本。
        str_after = _adapt_version_text(str_before, str_version, str_adapter)  # 写入后候选文本

        # 文本不变时仍需确认 selector 已经命中目标版本。
        if str_after == str_before:

            # selector 未命中表示 surface 声明与当前文件事实不一致。
            if not _surface_matches_version(str_before, str_version, str_adapter):

                # 阻止静默写入错误版本面。
                raise ValueError("> ERR: [Python] version surface selector did not match")

            # 已经满足请求版本时无需产生临时文件。
            continue

        # 临时后缀保持目标目录内写入并支持原子替换。
        path_temp = path_surface.with_suffix(path_surface.suffix + ".version-tmp")  # surface 临时文件

        # 使用 UTF-8 与固定换行写入候选文本。
        path_temp.write_text(str_after, encoding="utf-8", newline="\n")

        # 以目标文件替换临时版本，完成受控写入。
        path_temp.replace(path_surface)

# 在 surface 写入后更新 manifest 绑定的 role 摘要。
def _refresh_manifest_role_hashes(path_skill_root: Path) -> None:
    """在 surface 写入后更新 manifest 绑定的 role 摘要。

    参数：path_skill_root 为技能可信根。
    返回：无；manifest role 摘要更新后写回同一文件。
    """

    # manifest 位于技能配置根，路径不接受调用方任意替换。
    path_manifest = path_skill_root / "config" / "runtime-manifest.json"  # 技能根下的 runtime manifest 文件

    # 读取 manifest 对象并保留原有 role 顺序。
    dict_manifest = json.loads(path_manifest.read_text(encoding="utf-8"))  # 当前 runtime manifest 对象

    # 逐项刷新 role 内容和 schema 摘要。
    for dict_role in dict_manifest.get("roles", []):

        # 非对象 role 由 manifest schema 负责报告，此处跳过。
        if not isinstance(dict_role, dict):

            # 保留其他 role 的刷新机会。
            continue

        # 解析 role 相对路径到技能根。
        path_role = path_skill_root / str(dict_role.get("relative_path", ""))  # 当前 role 的技能根相对路径

        # 缺失或符号链接 role 不参与摘要写回。
        if not path_role.is_file() or path_role.is_symlink():

            # 保留 manifest 当前声明供后续 loader 报告。
            continue

        # 读取 role 声明的摘要模式。
        str_mode = str(dict_role.get("hash_mode", ""))  # role 摘要模式

        # 更新 role 内容摘要以匹配写入后文件。
        dict_role["content_sha256"] = _file_hash(path_role, str_mode)  # role 新内容摘要

        # schema 摘要仅在声明相对路径时刷新。
        obj_schema_relative: object = dict_role.get("schema_relative_path")  # 可选 schema 路径对象。

        # 只为 manifest 明确声明的 schema 计算摘要。
        if obj_schema_relative:

            # 解析 schema 文件并计算 canonical 摘要。
            path_schema = path_skill_root / str(obj_schema_relative)  # schema 文件的技能根相对路径。

            # 把新 schema 摘要写回当前 role 声明。
            dict_role["schema_sha256"] = _file_hash(path_schema, "canonical_json")  # schema 内容摘要

    # 以稳定 JSON 格式写回 manifest，供下一次 binding 使用。
    path_manifest.write_text(
        json.dumps(dict_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

# 计算 manifest role 的 canonical 或原始字节摘要。
def _file_hash(path_file: Path, str_mode: str) -> str:
    """计算 manifest role 的 canonical 或原始字节摘要。

    参数：path_file 为 role 文件；str_mode 为 canonical_json 或原始字节模式。
    返回：小写 SHA-256 摘要文本。
    """

    # JSON role 使用稳定键序和终止换行计算摘要。
    if str_mode == "canonical_json":

        # 读取 JSON role 顶层对象。
        object_payload = json.loads(path_file.read_text(encoding="utf-8"))  # 用于摘要的 role 顶层对象

        # 序列化 canonical JSON 文本作为摘要输入。
        bytes_payload = (  # 保存 canonical role 文本作为摘要输入
            json.dumps(object_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))  # 固定键序的 JSON 文本
            + "\n"  # role 摘要输入的终止换行
        ).encode("utf-8")

    # 非 JSON role 直接使用原始文件字节。
    else:

        # 保持原始换行和编码字节不被文本层改写。
        bytes_payload = path_file.read_bytes()  # role 文件的原始字节

    # 返回当前 role 文件摘要。
    return hashlib.sha256(bytes_payload).hexdigest()

# 使用声明的 adapter 更新一个版本面文本。
def _adapt_version_text(str_text: str, str_version: str, str_adapter: str) -> str:
    """使用声明的 adapter 更新一个版本面文本。

    参数：str_text 为当前 surface 文本；str_version 为请求版本；str_adapter 为适配器名称。
    返回：按适配器规则替换后的文本。
    """

    # plain_version surface 只写入版本文本和终止换行。
    if str_adapter == "plain_version":

        # 返回纯版本面文本，保持调用方声明的换行合同。
        return str_version + "\n"

    # TOML/YAML surface 使用不带 v 前缀的元数据版本。
    if str_adapter in {"toml_project_version", "yaml_version"}:

        # 去除公开版本前缀后用于元数据字段。
        str_metadata_version = str_version.lstrip("vV")  # 元数据版本文本

        # 替换首个声明的版本字段，保持其键和值格式。
        return re.sub(
            r"(?m)^(\s*(?:version\s*=\s*|version:\s*))[^\r\n]+$",
            lambda match: match.group(1)
            + (json.dumps(str_metadata_version) if "=" in match.group(1) else str_metadata_version),
            str_text,
            count=1,
        )

    # 其他 adapter 在公开文本中统一使用 v 前缀版本。
    str_public_version = str_version if str_version.lower().startswith("v") else "v" + str_version  # 当前公开版本文本

    # 替换首个公开版本标记，避免修改无关数字。
    return re.sub(r"v\d+(?:\.\d+){2}", str_public_version, str_text, count=1)

# 判断不变文本是否已经满足 requested version。
def _surface_matches_version(str_text: str, str_version: str, str_adapter: str) -> bool:
    """判断不变文本是否已经满足 requested version。

    参数：str_text 为当前 surface 文本；str_version 为请求版本；str_adapter 为适配器名称。
    返回：文本已经满足 selector 时返回 True。
    """

    # plain_version surface 直接比较去空白文本。
    if str_adapter == "plain_version":

        # 纯版本面要求文件文本与请求版本完全一致。
        return str_text.strip() == str_version

    # TOML/YAML surface 比较不带 v 前缀的元数据版本。
    if str_adapter in {"toml_project_version", "yaml_version"}:

        # 元数据版本比较时忽略公开 v 前缀。
        return str_version.lstrip("vV") in str_text

    # 公开文本 selector 使用带 v 前缀版本。
    str_public_version = str_version if str_version.lower().startswith("v") else "v" + str_version  # selector 使用的公开版本文本

    # 返回公开版本是否存在于 surface 文本。
    return str_public_version in str_text
