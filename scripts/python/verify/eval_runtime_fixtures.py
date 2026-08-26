"""构造 agents-md-generator 回归评估所需的项目夹具。"""

# 延迟注解求值以兼容 Python 3.10。
from __future__ import annotations

# 哈希、动态导入和序列化服务评估夹具的数据流。
import hashlib
import importlib.util
import json
import os

# 文件复制、子进程和类型标注支撑隔离项目的生成。
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# 模块路径常量用于定位 owner 仓库内的任务脚本。
RUNTIME_DIR = Path(__file__).resolve().parent  # verify 任务目录

# Python 任务根目录包含 design、render、release 等职责目录。
SCRIPTS_PYTHON_DIR = RUNTIME_DIR.parent  # Python 任务分类根

# 评估夹具默认从技能 scripts 根目录发现实现文件。
SCRIPTS_DIR = SCRIPTS_PYTHON_DIR.parent  # 脚本资源根

# 技能根用于需要读取正式资源的评估场景。
SKILL_DIR = SCRIPTS_DIR.parent  # 正式技能根

# 子进程统一从评估启动时的仓库根执行。
REPO_ROOT = Path.cwd().resolve()  # 当前评估仓库根

# runtime manifest 的 canonical_json 哈希与普通字节哈希共用一处实现。
def _runtime_resource_hash(path_resource: Path, str_hash_mode: str) -> str:
    """计算 runtime manifest role 的声明摘要。

    参数：path_resource 为 role 文件；str_hash_mode 为 manifest 声明的哈希模式。
    返回：与 runtime contract loader 相同的 SHA-256 摘要。
    """

    # canonical_json role 必须先解析再按稳定键序列化，避免格式空白影响绑定。
    if str_hash_mode == "canonical_json":

        # 使用 UTF-8 JSON canonical bytes 对齐运行时 loader 的比较语义。
        object_value = json.loads(path_resource.read_text(encoding="utf-8"))  # 解析 role 的语义对象，排除 JSON 空白差异

        # 将规范化后的 JSON 序列化为运行时合同使用的稳定字节。
        bytes_content = json.dumps(  # 供运行时合同比较的稳定 JSON 字节
            object_value,  # 规范化 JSON 的语义对象输入
            ensure_ascii=False,  # 保留中文字符，避免转义改变摘要语义
            sort_keys=True,  # 固定对象键顺序，避免输入顺序改变摘要
            separators=(",", ":"),  # 移除格式空白，生成统一 canonical 字节
        ).encode("utf-8")  # canonical_json role 的绑定字节

    # 普通 role 保留文件实际字节，避免把脚本当作 JSON 解析。
    else:

        # 非 JSON role 的摘要绑定原始文件内容。
        bytes_content = path_resource.read_bytes()  # role 原始字节

    # 所有 runtime role 统一返回小写 SHA-256。
    return hashlib.sha256(bytes_content).hexdigest()

# 根据 manifest 事实刷新 fixture 内 role 与 schema 摘要。
def _refresh_runtime_manifest_hashes(path_skill: Path) -> None:
    """刷新 fixture runtime manifest 的 role 摘要。

    参数：path_skill 为临时技能根。
    返回：无；runtime-manifest.json 在原位置原子语义更新。
    异常：声明的必需 role 或 schema 缺失时抛出 RuntimeError。
    """

    # manifest 自身是 fixture 运行时绑定的唯一角色清单来源。
    path_manifest = path_skill / "config" / "runtime-manifest.json"  # 临时技能使用的 runtime manifest 路径

    # 读取待刷新摘要的 manifest 对象，保留其配置驱动的 role 顺序。
    dict_manifest = json.loads(path_manifest.read_text(encoding="utf-8"))  # manifest 配置对象

    # 逐个刷新声明 role，保持可选 role 的缺失语义不变。
    for dict_role in dict_manifest.get("roles", []):

        # 非对象条目无法形成可验证 role，交给 loader 的结构门禁处理。
        if not isinstance(dict_role, dict):

            # 不在 fixture helper 中猜测损坏条目的替代结构。
            continue

        # 读取 role 相对路径并拒绝越界引用。
        path_relative = Path(str(dict_role.get("relative_path", "")))  # 当前 role 在 fixture 内的相对路径

        # 越界路径会使摘要绑定脱离临时技能根，因此先终止。
        if path_relative.is_absolute() or ".." in path_relative.parts:

            # 防止 fixture 复制阶段突破技能根边界。
            raise RuntimeError(
                f"> ERR: [Python] runtime manifest role escapes skill root: {path_relative}"
            )

        # role 路径必须位于临时技能根内。
        path_role = path_skill / path_relative  # 临时技能内待绑定摘要的 role 路径

        # 不存在的可选 role 保留 loader 的缺失语义，必需 role 则立即失败。
        if not path_role.is_file():

            # 必需 role 缺失时立即报告具体相对路径。
            if bool(dict_role.get("required", False)):

                # 让发布 fixture 在进入 package_release 前失败闭合。
                raise RuntimeError(
                    f"> ERR: [Python] required runtime manifest role is missing: {path_relative}"
                )

            # 可选 role 保留 manifest loader 的可选语义。
            continue

        # 使用 role 自己声明的 hash_mode 更新内容摘要。
        dict_role["content_sha256"] = _runtime_resource_hash(  # 根据实际 role 文件刷新内容摘要
            path_role,  # 临时 fixture 中实际存在的 role 文件
            str(dict_role.get("hash_mode", "")),  # 沿用 manifest 声明的摘要模式
        )  # role 文件的实际内容摘要

        # 声明 schema 时同步 canonical schema 摘要。
        obj_schema_relative: object = dict_role.get("schema_relative_path")  # role 声明的 schema 相对路径

        # 只有声明 schema 的 role 才需要同步 schema 摘要。
        if obj_schema_relative:

            # schema 路径同样必须保持在技能根内。
            path_schema_relative = Path(str(obj_schema_relative))  # role schema 的相对路径

            # schema 越界会破坏 role 与技能根的同源关系，因此拒绝该 manifest。
            if path_schema_relative.is_absolute() or ".." in path_schema_relative.parts:

                # 拒绝由 manifest 驱动的越界 schema 引用。
                raise RuntimeError(
                    f"> ERR: [Python] runtime manifest schema escapes skill root: {path_schema_relative}"
                )

            # schema 缺失表示 role 合同无法完成验证。
            path_schema = path_skill / path_schema_relative  # 临时技能内的 schema 路径

            # 缺失 schema 时无法完成 role 合同校验，必须在 fixture 阶段报告。
            if not path_schema.is_file():

                # 把缺失 schema 绑定到具体 role，避免发布阶段才出现模糊错误。
                raise RuntimeError(
                    f"> ERR: [Python] runtime manifest schema is missing: {path_schema_relative}"
                )

            # schema 始终按 canonical JSON 计算。
            dict_role["schema_sha256"] = _runtime_resource_hash(  # 根据实际 schema 刷新 canonical 摘要
                path_schema,  # 读取临时 fixture 的 schema 文件以生成 role 合同摘要
                "canonical_json",  # schema 合同固定采用规范 JSON 摘要
            )  # schema 的 canonical_json 摘要

    # 以稳定格式回写 manifest，供后续 loader 复核。
    path_manifest.write_text(
        json.dumps(dict_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

# installer manifest 继续声明 bundle 本地入口和投影记录文件。
def _copy_installer_bundle_entries(path_skill: Path) -> None:
    """复制 installer manifest 声明的 bundle 本地文件。

    参数：path_skill 为已经复制 runtime roles 的临时技能根。
    返回：无；bundle 入口和 manifest projection 写入同一相对目录。
    异常：声明文件缺失或路径越界时抛出 RuntimeError。
    """

    # installer manifest 是 bundle 入口清单的配置来源。
    path_manifest = path_skill / "config" / "installer" / "installer.manifest.json"  # installer manifest 配置路径

    # 读取 bundle 入口和跨目录资源的配置对象。
    dict_manifest = json.loads(  # 读取复制入口和资源基准，供后续清单展开
        path_manifest.read_text(encoding="utf-8")  # installer manifest 的原始配置文本
    )

    # bundle 根和入口集合均从 manifest 读取，避免复制代码内置文件名。
    path_bundle_relative = Path(str(dict_manifest.get("bundle_root_relative", "")))  # installer bundle 根相对路径

    # 入口文件必须随 bundle 一并复制，避免发布 guard 看到不完整的本地投影。
    list_bundle_files = [  # installer entrypoint 的 bundle 内相对路径集合
        Path(str(path_item))  # 将入口转换为受校验的相对路径对象
        for path_item in dict_manifest.get("entrypoints", [])  # 遍历 manifest 声明的入口
        if str(path_item).strip()  # 过滤 manifest 中的空入口声明
    ]

    # manifest projection 是 guard 额外要求的本地发布记录。
    str_projection = str(dict_manifest.get("manifest_projection_relative_path", "")).strip()  # 发布投影记录的相对路径

    # 只有声明了投影记录时才把它加入 bundle 复制集合。
    if str_projection:

        # 将投影记录追加到同一配置驱动复制清单。
        list_bundle_files.append(Path(str_projection))

    # 这些 manifest 字段允许 installer 使用 bundle 外但仍受技能根约束的资源。
    tuple_resource_keys = (  # installer manifest 的跨目录资源字段
        "manifest_env_relative_path",  # bundle 内环境投影的配置键
        "projection_relative_path",  # bundle 内投影文件的配置键
        "manifest_projection_relative_path",  # manifest 投影记录的配置键
        "projection_schema_relative_path",  # 投影 schema 的配置键
        "projection_generator_relative_path",  # 投影生成器的配置键
        "catalog_relative_path",  # 平台目录的配置键
        "overrides_relative_path",  # 平台覆盖配置的配置键
        "backend_relative_path",  # installer backend 的配置键
        "runtime_relative_path",  # installer runtime 脚本的配置键
    )

    # 逐字段展开 installer manifest 的跨目录资源声明。
    for str_resource_key in tuple_resource_keys:

        # 只把有值的 manifest 资源加入复制清单。
        str_resource_relative = str(dict_manifest.get(str_resource_key, "")).strip()  # 当前字段声明的资源路径

        # 空字段不产生复制动作，避免把空路径解析为技能根目录。
        if str_resource_relative:

            # 将 manifest 资源纳入复制集合，保留其声明的相对路径。
            list_bundle_files.append(Path(str_resource_relative))  # 记录待复制的 manifest 资源

    # 校验 bundle 根本身再解析其声明的本地文件。
    if path_bundle_relative.is_absolute() or ".." in path_bundle_relative.parts:

        # 拒绝 installer manifest 越界到技能根之外。
        raise RuntimeError(
            f"> ERR: [Python] installer bundle root escapes skill root: {path_bundle_relative}"
        )

    # 逐个复制 bundle 本地资源和 manifest 声明的 skill-root 资源。
    for path_file_relative in dict.fromkeys(list_bundle_files):

        # manifest 资源不能通过绝对路径跳出 skill 根。
        if path_file_relative.is_absolute():

            # 保持 installer manifest 的路径边界 fail-closed。
            raise RuntimeError(
                f"> ERR: [Python] installer resource must be relative: {path_file_relative}"
            )

        # source/target 按 manifest 基准解析并锁定在技能根内。
        path_source = (SKILL_DIR / path_bundle_relative / path_file_relative).resolve()  # owner 资源的解析路径

        # 解析后的目标必须作为临时 fixture 内的真实写入位置。
        path_target = (path_skill / path_bundle_relative / path_file_relative).resolve()  # fixture 资源的写入路径

        # 两个解析结果都必须通过 containment 校验后才允许复制。
        try:

            # 校验源路径保持在正式技能根内，防止配置诱导复制外部文件。
            path_source.relative_to(SKILL_DIR.resolve())

            # 校验目标路径保持在临时技能根内。
            path_target.relative_to(path_skill.resolve())

        # 任何越界解析都阻断复制。
        except ValueError as object_error:

            # 把越界路径转换为可读的 fixture 错误。
            raise RuntimeError(
                f"> ERR: [Python] installer resource escapes skill root: {path_file_relative}"
            ) from object_error

        # 缺少 manifest 声明的资源会让发布包无法自洽，因此立即报告。
        if not path_source.is_file():

            # 缺失入口或投影文件不能等到 release guard 才报告。
            raise RuntimeError(
                f"> ERR: [Python] installer bundle source file is missing: {path_source}"
            )

        # 创建 bundle 本地父目录并复制原始内容。
        path_target.parent.mkdir(parents=True, exist_ok=True)

        # 复制原始 bundle 文件，保留其字节内容供发布 guard 校验。
        shutil.copy2(path_source, path_target)  # installer bundle 文件副本

        # installer runtime/backend 超限时同步项目级 decomposition plan。
        if path_source.suffix == ".py" and path_source.stat().st_size > 65536:

            # plan 路径沿当前 owner skill 名称和 manifest 相对路径生成。
            path_plan_relative = (  # 从超限 role 的相对路径推导同名治理计划
                Path("docs")  # decomposition plan 的文档根目录
                / "development"  # development 文档目录
                / "decomposition-plans"  # 超限文件的计划目录
                / "skills"  # 技能计划的归属目录
                / SKILL_DIR.name  # 当前技能的计划目录
                / path_source.relative_to(SKILL_DIR.resolve()).with_suffix(  # 依据源文件相对路径推导计划文件名
                    path_source.suffix + ".md"  # 由源文件扩展名生成计划后缀
                )
            )

            # 计划来源固定在当前项目根，确保发布审计读取正式文档。
            path_plan_source = REPO_ROOT / path_plan_relative  # 正式治理计划的源路径

            # 计划目标置于临时项目根，随 fixture 一起进入 package_release。
            path_plan_target = path_skill.parents[1] / path_plan_relative  # 临时治理计划的目标路径

            # 只有正式计划存在时才复制，避免生成不可审计的占位证据。
            if path_plan_source.is_file():

                # 先建立计划目标目录，再写入可追溯的治理文档。
                path_plan_target.parent.mkdir(parents=True, exist_ok=True)

                # 写入 role 对应计划，使发布 gate 能关联源文件与分解证据。
                shutil.copy2(path_plan_source, path_plan_target)  # 临时项目中的治理计划副本

# 按 runtime manifest roles 动态复制发布所需资源到 fixture。
def _copy_runtime_manifest_resources(path_skill: Path) -> None:
    """复制 runtime manifest 及其声明的 role/schema 资源。

    参数：path_skill 为临时技能根。
    返回：无；资源路径完全由 owner manifest 驱动。
    异常：必需源资源缺失或路径越界时抛出 RuntimeError。
    """

    # owner skill 的 runtime manifest 是 fixture 资源清单的权威来源。
    path_source_manifest = SKILL_DIR / "config" / "runtime-manifest.json"  # 正式技能 runtime manifest 的源路径

    # 读取正式 manifest，确保临时 fixture 跟随 owner 的 role 配置变化。
    dict_manifest = json.loads(  # owner manifest 的结构化配置对象
        path_source_manifest.read_text(encoding="utf-8")  # 正式技能的 manifest 原始文本
    )

    # manifest 自身必须先落到 fixture，后续 role loader 才能读取它。
    list_relative_paths = [  # 临时 fixture 首先必须拥有可被 loader 读取的 manifest
        Path("config") / "runtime-manifest.json"  # manifest 在临时技能中的固定入口
    ]

    # 从 roles 和 schema_relative_path 动态展开全部发布依赖。
    for dict_role in dict_manifest.get("roles", []):

        # 损坏条目不在复制阶段猜测路径。
        if not isinstance(dict_role, dict):

            # 保留后续 manifest 结构门禁的责任边界。
            continue

        # role 路径加入复制清单。
        list_relative_paths.append(Path(str(dict_role.get("relative_path", ""))))

        # role schema 路径也必须随 role 一并复制。
        obj_schema_relative: object = dict_role.get("schema_relative_path")  # 当前 role 的 schema 复制声明

        # 有 schema 的 role 必须把 schema 文件一并纳入临时清单。
        if obj_schema_relative:

            # 以 manifest 声明作为 schema 复制输入。
            list_relative_paths.append(Path(str(obj_schema_relative)))

    # 保持首次出现顺序并移除重复资源路径。
    for path_relative in dict.fromkeys(list_relative_paths):

        # 复制清单中的路径必须是技能根内相对路径。
        if path_relative.is_absolute() or ".." in path_relative.parts:

            # 防止受配置驱动的 fixture 复制越界。
            raise RuntimeError(
                f"> ERR: [Python] runtime fixture resource escapes skill root: {path_relative}"
            )

        # owner 源路径与 fixture 目标路径保持同一相对布局。
        path_source = SKILL_DIR / path_relative  # 按 manifest 相对路径读取正式 role/schema 原文

        # 临时目标保持 manifest 声明的相对布局，供后续 loader 使用。
        path_target = path_skill / path_relative  # 临时 fixture 的 role/schema 目标路径

        # 可选 role 缺失时由 manifest required 字段决定是否阻断。
        if not path_source.is_file():

            # 对 manifest 自身和 declared schema 不能静默跳过。
            if path_relative == Path("config/runtime-manifest.json") or any(
                path_relative == Path(str(dict_role.get("schema_relative_path", "")))
                for dict_role in dict_manifest.get("roles", [])
                if isinstance(dict_role, dict) and dict_role.get("schema_relative_path")
            ):

                # 缺失核心清单资源直接阻断 fixture 创建。
                raise RuntimeError(
                    f"> ERR: [Python] runtime fixture source resource is missing: {path_relative}"
                )

            # 非必需 role 的源缺失保留运行时可选语义。
            continue

        # 目标父目录按清单路径创建，避免写死资源层级。
        path_target.parent.mkdir(parents=True, exist_ok=True)

        # 保留 role/schema 原始字节，后续步骤再刷新 manifest 摘要。
        shutil.copy2(path_source, path_target)  # role/schema 的临时副本

        # 超限 Python role 需要同步项目级 decomposition plan 才能通过发布治理。
        if path_source.suffix == ".py" and path_source.stat().st_size > 65536:

            # plan 根和 source role 相对路径保持由当前治理配置解释。
            path_plan_relative = (  # 由 role 文件路径推导对应的 decomposition plan
                Path("docs")  # role 治理计划的文档根目录
                / "development"  # 评估文档根目录
                / "decomposition-plans"  # 评估专用的分解计划目录
                / "skills"  # 评估技能的计划归属目录
                / SKILL_DIR.name  # 当前评估技能名称
                / path_relative.with_suffix(path_relative.suffix + ".md")  # 将 role 相对路径转换为计划文件名
            )

            # 计划来源固定到项目根，避免把临时生成物当作治理依据。
            path_plan_source = REPO_ROOT / path_plan_relative  # 正式计划的源路径

            # 计划目标跟随 fixture 项目根，供发布阶段读取。
            path_plan_target = path_skill.parents[1] / path_plan_relative  # fixture 计划的目标路径

            # 只有 owner 已提供正式计划时才写入临时项目。
            if path_plan_source.is_file():

                # 先建立计划目标目录，保证复制动作不会产生隐式失败。
                path_plan_target.parent.mkdir(parents=True, exist_ok=True)

                # 写入已有的正式计划，维持 role 与治理证据的可追溯关系。
                shutil.copy2(path_plan_source, path_plan_target)  # fixture 中的治理计划副本

    # bundle 入口和投影记录不属于 runtime role，单独按 installer manifest 复制。
    _copy_installer_bundle_entries(path_skill)

    # 首次复制后立即把 fixture role hashes 绑定到实际文件。
    _refresh_runtime_manifest_hashes(path_skill)

# 读取 runtime manifest 绑定的评估 fixture 合同。
def _load_fixture_values() -> dict[str, Any]:
    """返回配置驱动的评估 fixture 值。

    参数：无；路径由当前技能运行时根解析。
    返回：经过 runtime manifest 校验的 fixture JSON 对象。
    异常：合同缺失、路径越界或摘要漂移时由 loader 抛出结构化错误。
    """

    # 直接脚本加载时注册共享合同 loader 目录。
    path_common_dir = SCRIPTS_PYTHON_DIR / "common"  # 共享合同 loader 目录

    # 仅在直接脚本入口缺少包上下文时补充共享目录。
    if str(path_common_dir) not in sys.path:

        # 让当前评估进程能够导入 runtime contract loader。
        sys.path.insert(0, str(path_common_dir))

    # 只有经过 manifest 与摘要校验的 fixture 才能进入当前评估流程。
    from runtime_contracts import load_json_role, load_runtime_manifest

    # 只有经过 manifest/hash 校验的 fixture 才能进入 handler。
    dict_binding = load_runtime_manifest(REPO_ROOT, SKILL_DIR)  # 已校验的 fixture 运行时绑定

    # 从绑定 role 读取参数化 fixture JSON。
    return load_json_role(dict_binding, "evaluation_fixtures")

# 夹具类集中维护跨评估复用的稳定测试事实。
class EvalFixtures:
    """集中生成评估脚本复用的项目答案、文件树和命令夹具。"""

    # 初始化可覆盖的脚本发现位置。
    def __init__(
        self,
        scripts_dir: Path | None = None,
        *,
        external_skill_dir: Path | None = None,
    ) -> None:
        """初始化评估夹具的脚本发现根。

        参数：scripts_dir 为可选技能 scripts 目录覆盖；external_skill_dir 为可选外部技能根。
        返回：无业务返回值，保存后续模块与命令定位上下文。
        """

        # 显式覆盖服务隔离测试，缺省值指向 owner 技能脚本根。
        self.scripts_dir = Path(scripts_dir) if scripts_dir is not None else SCRIPTS_DIR  # 脚本发现根

        # 外部技能输入只在配置激活的案例中使用。
        self.external_skill_dir = (
            Path(external_skill_dir).resolve() if external_skill_dir is not None else None  # 外部技能解析目录
        )  # 外部技能输入目录

        # 当前评估合同的版本、名称和相对路径均来自 JSON role。
        self.fixture_values = _load_fixture_values()  # 参数化评估 fixture 值

    # 从参数化 fixture 读取嵌套值，调用方不再维护业务常量。
    def fixture_value(self, *tuple_keys: str, default: object = None) -> object:
        """从 fixture JSON 读取嵌套值。

        参数：tuple_keys 为嵌套字段路径；default 为字段缺失时的显式回退值。
        返回：字段值或 default 回退对象。
        """

        # 从 fixture 根对象开始逐段解析字段路径。
        obj_fixture_value: object = self.fixture_values  # 当前 fixture 中间值

        # 每一段都先确认当前值仍保持映射形状。
        for string_key in tuple_keys:

            # 非映射中间值无法继续解析嵌套字段。
            if not isinstance(obj_fixture_value, dict):

                # 使用调用方声明的回退值结束本次读取。
                return default

            # 读取下一层字段并保留缺失回退值。
            obj_fixture_value = obj_fixture_value.get(string_key, default)  # 当前 fixture 字段值

        # 返回完整路径解析出的 fixture 字段值。
        return obj_fixture_value

    # 构造远程目录治理答案。
    def remote_directory_answers(
        self,
        remote_directory_structure: str | None = None,
        include_remote_policy: bool = True,
    ) -> dict[str, Any]:
        """生成远程目录治理场景使用的访谈答案。

        参数：remote_directory_structure 为远程布局；include_remote_policy 控制运行策略字段。
        返回：可直接合并到设计访谈答案的目录合同映射。
        """

        # 缺省远程布局从 fixture 合同读取，调用方仍可显式覆盖。
        str_remote_structure = remote_directory_structure or str(  # 当前远程布局文本
            self.fixture_value("paths", "remote_directory")  # fixture 远程目录值
        )

        # 基础目录合同覆盖本地、远程、功能放置和确认状态。
        dict_answers: dict[str, Any] = {  # 远程目录治理答案
            "local_directory_structure": "engineering/<skill>/, tests/, dist/",  # 本地工程布局
            "remote_directory_structure": str_remote_structure,  # 调用方指定的远程布局
            "feature_directory_rules": "features in src/features/<name>/ with tests nearby",  # 功能目录规则
            "directory_contract_confirmed": True,  # 模拟用户确认目录合同
        }

        # 启用远程策略时补齐环境、运行产物和归档约束。
        if include_remote_policy:

            # 四个字段共同构成可写入的远程运行合同。
            dict_answers.update(
                {
                    "remote_conda_environment_layout": ".conda/<env-name>/",  # 隔离环境相对路径
                    "remote_run_artifact_active_layout": "runs/<run-id>/",  # 活跃运行产物路径
                    "remote_run_artifact_backup_layout": "backups/runs/<run-id>/",  # 归档备份路径
                    "remote_run_archive_trigger": "after required verification passes",  # 验证通过后归档
                }
            )

        # 返回答案供 skill 或 engineering 画像继续扩展。
        return dict_answers

    # 构造技能项目完整治理答案。
    def skill_answers(
        self,
        name: str | None = None,
        remote_directory_structure: str | None = None,
        include_remote_policy: bool = False,
        use_remote_server: bool = False,
    ) -> dict[str, Any]:
        """生成 skill 项目治理场景的完整访谈答案。

        参数：name 为技能名。
        参数：remote_directory_structure 为远程目录布局。
        参数：include_remote_policy 控制是否补齐远程运行策略。
        参数：use_remote_server 表示是否启用服务器。
        返回：满足强控制写入门禁的完整技能访谈答案。
        """

        # 技能名称由 fixture 合同提供，调用方仍可显式传入场景名称。
        str_skill_name = name or str(self.fixture_value("names", "skill"))  # fixture 技能名称

        # 发布目录版本也由 fixture 提供，避免在答案中写死当前发布版本。
        str_release_version = str(self.fixture_value("versions", "release_fixture"))  # fixture 发布版本

        # 固定答案覆盖技能设计、内存、发布和强控制门禁。
        dict_answers: dict[str, Any] = {  # 技能设计访谈完整答案
            "development_type": "skill",  # 项目开发类型
            "default_conversation_language": "\u4e2d\u6587",  # 默认交互语言
            "use_remote_server": use_remote_server,  # 是否使用远程服务器
            "use_codebase_memory_mcp": False,  # 评估夹具明确禁用代码知识图谱
            "memory_enabled": True,  # 启用项目长期记忆
            "memory_storage_backend": "sqlite-plus-jsonl",  # 评估夹具使用正式记忆后端
            "memory_capture_scope": (  # 长期记忆捕获范围
                "handoff summaries, user-confirmed project preferences, durable decisions, "
                "validation lessons, and release lessons"
            ),
            "memory_read_policy": "read latest handoff plus relevant docs/memory summaries before implementation",  # 记忆读取策略
            "memory_sensitivity_policy": "do not store secrets, credentials, or raw local private paths",  # 敏感信息策略
            "skill_purpose": "Create verified AGENTS.md files.",  # 技能用途
            "skill_reason": "Keep agent onboarding deterministic.",  # 创建原因
            "development_requirements": "Collect facts and render AGENTS.md with strict design-review gates.",  # 开发要求
            "expected_outcome": "Verified AGENTS.md guidance exists.",  # 预期结果
            "validation_method": "automated scripts plus user review",  # 验证方式
            "validation_granularity": "unit tests, AGENTS verification, skill audit, full evaluate chain",  # 验证粒度
            "reference_materials": ["none"],  # 参考材料
            "audience": "maintainers",  # 目标受众
            "name": str_skill_name,  # 访谈答案中的 fixture 技能标识
            "design_notes": "Keep SKILL.md concise.",  # 设计说明
            "trigger_scenarios": "Use when a repo needs AGENTS.md generation or review.",  # 触发场景
            "skill_design_patterns": ["Tool Wrapper", "Generator", "Reviewer", "Inversion", "Pipeline"],  # 设计模式
            "resource_plan": "scripts/ for deterministic checks, references/ for policy, assets/ for templates",  # 资源规划
            "progressive_disclosure_policy": "Keep SKILL.md lean and move detailed policy to references.",  # 渐进披露策略
            "validation_gates": "quick_validate.py, audit_skill.py, verify_agents.py, evaluate_skill.py",  # 验证门禁
            "forward_testing_policy": "Forward-test complex workflows.",  # 前向测试策略
            "git_management": "yes-local-only",  # Git 管理模式
            "branch_model": "master-and-dist-release",  # 分支模型
            "release_contract": f"dist/{str_skill_name}-{str_release_version} plus zip",  # 发布合同
            "has_existing_work": "yes",  # 已有工作状态
            "alignment_confirmed": True,  # 对齐确认状态
        }

        # 目录合同由公共构造器提供，避免远程字段场景漂移。
        dict_answers.update(
            self.remote_directory_answers(
                remote_directory_structure=remote_directory_structure,
                include_remote_policy=include_remote_policy,
            )
        )

        # skill 项目覆盖工程默认布局，限定正式技能目录。
        dict_answers["local_directory_structure"] = f"skills/{str_skill_name}/, tests/, dist/"  # 技能仓库本地布局

        # 技能功能实现和详细政策分别落在 scripts 与 references。
        dict_answers["feature_directory_rules"] = "scripts in scripts/, detailed policy in references/"  # 技能资源放置规则

        # 返回可直接进入设计审查的答案快照。
        return dict_answers

    # 从文件路径动态加载待测脚本模块。
    def load_script_module(self, name: str) -> Any:
        """按文件名从当前脚本目录加载待测模块。

        参数：name 为目标 Python 脚本文件名。
        返回：执行完成且可供测试调用的模块对象。
        异常：文件无法形成 import spec 时抛出带 Python 前缀的 RuntimeError。
        """

        # spec 同时记录目标路径和后续模块加载器。
        module_type_spec = importlib.util.spec_from_file_location(name, self.script_path(name))  # 待读模块导入规范

        # 缺失加载器意味着脚本路径不能作为模块执行。
        if module_type_spec is None or module_type_spec.loader is None:

            # 明确报告无法加载的脚本名。
            raise RuntimeError(f"> ERR: [Python] unable to load script module: {name}")

        # 根据规范创建独立模块对象，避免污染正式包导入路径。
        module_type_object = importlib.util.module_from_spec(module_type_spec)  # 隔离加载的待测模块

        # 将动态模块登记到 sys.modules，保证其 sibling helper 能稳定绝对导入。
        sys.modules[name] = module_type_object  # sibling helper 通过稳定模块名解析当前夹具

        # 执行目标源码以填充模块命名空间。
        module_type_spec.loader.exec_module(module_type_object)

        # 返回模块供评估用例调用公开函数。
        return module_type_object

    # 解析脚本名称对应的正式文件路径。
    def script_path(self, name: str) -> Path:
        """按脚本文件名解析任务分类后的运行时路径。

        参数：name 为目标脚本文件名。
        返回：优先返回 scripts/python 任务目录内的匹配文件，否则返回旧布局路径。
        """

        # 任务目录匹配结果按路径排序以保持确定性。
        list_candidates = sorted((self.scripts_dir / "python").glob(f"*/{name}"))  # 新布局脚本候选

        # 首个任务目录候选优先，空集合时兼容旧 scripts 根布局。
        return list_candidates[0] if list_candidates else self.scripts_dir / name

    # 为答案附加与内容哈希绑定的批准审查。
    def add_approved_design_review(
        self,
        project: Path,
        answers: dict[str, Any],
        reviewer_type: str = "subagent",
        verdict: str = "approve",
        required_user_confirmations: list[Any] | None = None,
        hash_override: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """为答案快照附加可通过写入门禁的设计审查。

        参数：project 为项目根。
        参数：answers 为答案。
        参数：reviewer_type 为审查者类型。
        参数：verdict 为审查结论。
        参数：required_user_confirmations 为待确认事项。
        参数：hash_override 为故障注入使用的哈希覆盖。
        返回：包含 extra_requirements 与 design_review 的独立答案副本。
        """

        # 副本防止评估构造过程修改调用方共享答案。
        dict_reviewed_answers = dict(answers)  # 待附加审查的答案快照

        # 无补充需求是完整访谈必须显式记录的状态。
        dict_reviewed_answers.setdefault("extra_requirements", "none")

        # 正式审查模块提供与生产写入路径相同的摘要哈希。
        module_type_review_gate = self.load_script_module("design_review_gate.py")  # 设计审查门禁模块

        # 两个哈希绑定完整答案与最终画像预览。
        dict_review_hashes = module_type_review_gate.design_review_hashes(project, dict_reviewed_answers)  # 审查对象哈希

        # 篡改场景可覆盖指定哈希以验证拒绝逻辑。
        if hash_override:

            # 仅更新调用方给出的哈希字段。
            dict_review_hashes.update(hash_override)

        # 审查区块模拟 production 设计审查的稳定字段合同。
        dict_reviewed_answers["design_review"] = {  # 写入门禁读取的设计审查证据
            "reviewer_type": reviewer_type,  # 审查者必须可配置为 subagent
            "verdict": verdict,  # approve 或拒绝结论
            "findings": [] if verdict == "approve" else ["design gap requires correction"],  # 拒绝场景发现项
            "required_user_confirmations": required_user_confirmations or [],  # 待用户确认事项
            "reviewed_answers_hash": dict_review_hashes["reviewed_answers_hash"],  # 已审答案摘要
            "reviewed_profile_hash": dict_review_hashes["reviewed_profile_hash"],  # 已审画像摘要
            "review_summary": "Subagent reviewed the complete design profile and approved the plan.",  # 固定审查摘要
        }

        # 返回独立快照供写入或故障注入场景使用。
        return dict_reviewed_answers

    # 写入带批准审查证据的答案文件。
    def write_reviewed_answers(
        self,
        project: Path,
        path: Path,
        answers: dict[str, Any],
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """补齐显式治理字段、附加审查并写入答案文件。

        参数：project 为项目根；path 为输出 JSON；answers 为基础答案；env 为临时环境覆盖。
        返回：实际写入文件的已审答案映射。
        异常：审查构造或文件写入异常原样向上传播，并保证环境恢复。
        """

        # 副本承载缺省字段，避免修改测试共享输入。
        dict_explicit_answers = dict(answers)  # 即将进入审查的显式答案

        # 未声明远程服务器时明确记录禁用状态。
        dict_explicit_answers.setdefault("use_remote_server", False)

        # 正式评估夹具必须显式覆盖知识图谱选择，不能依赖生产默认值。
        dict_explicit_answers.setdefault("use_codebase_memory_mcp", False)

        # 评估项目默认启用长期记忆治理。
        dict_explicit_answers.setdefault("memory_enabled", True)

        # SQLite 与 JSONL 双存储匹配 owner 仓库默认合同。
        dict_explicit_answers.setdefault("memory_storage_backend", "sqlite-plus-jsonl")

        # 捕获范围限定为长期有价值且经过治理的信息。
        dict_explicit_answers.setdefault(
            "memory_capture_scope",
            "handoff summaries, user-confirmed project preferences, durable decisions, "
            "validation lessons, and release lessons",
        )

        # 读取策略要求实现前先恢复最近交接和相关摘要。
        dict_explicit_answers.setdefault(
            "memory_read_policy",
            "read latest handoff plus relevant docs/memory summaries before implementation",
        )

        # 敏感策略禁止凭据和原始本地私有路径进入记忆。
        dict_explicit_answers.setdefault(
            "memory_sensitivity_policy",
            "do not store secrets, credentials, or raw local private paths",
        )

        # 记录被覆盖变量的原值，确保夹具没有跨测试副作用。
        dict_old_environment = {key: os.environ.get(key) for key in (env or {})}  # 环境变量恢复快照

        # 临时环境只覆盖设计审查构造阶段。
        try:

            # 非空覆盖映射才修改当前进程环境。
            if env:

                # 环境覆盖用于测试安装目录等外部事实。
                os.environ.update(env)

            # 生成与当前显式答案哈希匹配的批准审查。
            dict_reviewed_answers = self.add_approved_design_review(project, dict_explicit_answers)  # 最终已审答案

        # 无论审查是否成功都恢复进入方法前的环境。
        finally:

            # 逐个恢复变量，区分原先缺失和原先有值。
            for str_key, str_value in dict_old_environment.items():

                # 原先不存在的变量应从环境中删除。
                if str_value is None:

                    # pop 的缺省值处理覆盖代码未创建变量的边界。
                    os.environ.pop(str_key, None)

                # 原先存在的变量恢复其精确文本值。
                else:

                    # 恢复值防止后续评估观察到本场景覆盖。
                    os.environ[str_key] = str_value  # 恢复进入夹具前的环境值

        # 紧凑 JSON 足以作为生产设计写入命令的输入。
        path.write_text(json.dumps(dict_reviewed_answers), encoding="utf-8")

        # 返回写入内容供测试继续检查或修改。
        return dict_reviewed_answers

    # 创建隔离的已安装技能版本夹具。
    def make_installed_skill_fixture(self, root: Path, version: str | None = None) -> Path:
        """创建最小已安装 agents-md-generator 技能副本。

        参数：root 为夹具根目录；version 为安装副本版本。
        返回：包含 SKILL.md 和 VERSION 的已安装技能目录。
        """

        # 安装版本由 fixture 合同提供，避免把当前案例版本嵌入实现。
        str_version = version or str(self.fixture_value("versions", "release_fixture"))  # fixture 安装版本

        # 安装路径遵循 Codex home 下的标准 skills 布局。
        path_installed_skill = root / "codex-home" / "skills" / "agents-md-generator"  # 已安装技能目录

        # 父目录由夹具独立创建，不依赖调用方预置结构。
        path_installed_skill.mkdir(parents=True)

        # 最小技能入口提供名称和可触发描述。
        str_owner_name = str(self.fixture_value("names", "owner_skill"))  # fixture 所有者名称

        # 写入安装副本入口文件，保持名称与目录事实一致。
        (path_installed_skill / "SKILL.md").write_text(
            f"---\nname: {str_owner_name}\ndescription: Use when testing installed version\n---\n# Skill\n",
            encoding="utf-8",
        )

        # 独立版本文件支持源码与安装副本一致性检查。
        (path_installed_skill / "VERSION").write_text(str_version + "\n", encoding="utf-8")

        # 返回安装目录供渲染命令环境变量引用。
        return path_installed_skill

    # 写入发布流程识别所需的最小治理画像。
    def write_release_governance_profile(
        self,
        root: Path,
        kind: str = "skill",
        name: str | None = None,
    ) -> None:
        """写入发布与目录治理测试使用的控制画像。

        参数：root 为项目根；kind 为 skill 或 engineering；name 为项目名称。
        返回：无业务返回值，写入 .agents/agents-control.json。
        """

        # 项目名称从 fixture 合同读取，调用方可显式覆盖。
        string_name = name or str(self.fixture_value("names", "owner_skill"))  # 控制画像使用的技能名称来自覆盖值或 fixture 合同

        # 控制画像的两个版本事实都由 fixture 提供。
        str_current_version = str(self.fixture_value("versions", "project_skill"))  # fixture 当前项目版本

        # 读取发布目录使用的版本文本。
        str_release_version = str(self.fixture_value("versions", "release_fixture"))  # fixture 发布目录版本

        # 控制画像固定落在项目根的 .agents 目录。
        (root / ".agents").mkdir(exist_ok=True)

        # 项目类型决定正式源码的主目录前缀。
        str_primary_root = f"skills/{string_name}" if kind == "skill" else f"engineering/{string_name}"  # 主要项目根相对路径

        # 发布合同对 skill 启用净化，对 engineering 保持不适用。
        bool_skill_project = kind == "skill"  # 是否需要技能发布净化

        # 控制画像覆盖分支、目录和发布三个门禁域。
        dict_control_profile = {  # 发布治理控制画像
            "schema_version": 1,  # 控制画像 schema 版本
            "kind": kind,  # 控制画像项目类型
            "name": string_name,  # 被治理项目名称
            "memory_enabled": True,  # 发布夹具启用强控制记忆治理
            "memory_storage_backend": "sqlite-plus-jsonl",  # 发布夹具记忆后端
            "memory_capture_scope": "handoff summaries, durable decisions, validation lessons, and release lessons",  # 发布夹具捕获范围
            "memory_read_policy": "read latest handoff plus relevant docs/memory summaries before implementation",  # 发布夹具读取策略
            "memory_sensitivity_policy": "do not store secrets, credentials, or raw local private paths",  # 发布夹具敏感策略
            "git_management": "yes-local-only",  # 仅允许本地 Git 管理
            "branch_model": "master-and-dist-release",  # 主分支和发布分支模型
            "git_branch_policy": {  # 分支保护与发布准备路径
                "protected_branches": ["master", "release"],  # 禁止直接开发的分支
                "development_branches_allowed": True,  # 允许本地开发分支
                "release_prepare_allowed_paths": [  # 发布准备可修改路径
                    f"skills/{string_name}",  # 正式技能源码目录
                    "tests",  # 回归测试目录
                    "docs",  # 治理文档目录
                    ".agents",  # 控制画像目录
                    "AGENTS.md",  # 根级代理规则
                    "dist",  # 版本发布目录
                ],
            },
            "directory_contract": {  # 本地项目放置合同
                "confirmed": True,  # 模拟用户确认目录规则
                "local": f"{str_primary_root}/, tests/, dist/",  # 本地目录摘要
                "remote": "not configured",  # 夹具不启用远程目录
                "features": "features stay inside the governed project root",  # 功能留在项目根内
                "primary_project_root": str_primary_root,  # 正式源码根
                "feature_directory_rules": "keep new work inside the primary project root",  # 新功能放置规则
            },
            "release_contract": {  # 版本化发布与安装合同
                "current_version": str_current_version,  # 控制画像当前版本
                "protected_branches": ["master", "release"],  # 发布相关保护分支
                "dist_pattern": f"dist/{string_name}-{str_release_version}",  # 版本发布目录模式
                "zip_required": True,  # 要求生成对应归档
                "receipt_file": "RELEASE_RECEIPT.json",  # 安装验证收据名
                "install_source_policy": "versioned-dist-release-only",  # 禁止源码目录安装
                "repo_install_validation_level": "strong",  # owner 仓库安装强验证
                "external_install_validation_level": "reduced_assurance",  # 外部副本降低保证
                "sanitization_required": bool_skill_project,  # skill 发布必须净化
                "sanitization_scope": "broad" if bool_skill_project else "not-applicable",  # 净化覆盖范围
                "sanitization_mode": "auto-redact-dist-copy" if bool_skill_project else "disabled",  # 净化执行模式
                "sanitization_receipt_required": bool_skill_project,  # skill 收据记录净化证据
            },
        }

        # JSON 使用稳定缩进，便于门禁读取和测试诊断。
        str_control_json = json.dumps(dict_control_profile, indent=2)  # 控制画像 JSON 文本

        # 将完整控制画像写入项目治理目录。
        (root / ".agents" / "agents-control.json").write_text(str_control_json, encoding="utf-8")

    # 创建具备发布治理事实的最小技能项目。
    def make_governed_skill_project(
        self,
        root: Path,
        name: str | None = None,
        version: str | None = None,
    ) -> Path:
        """创建具备发布治理资料的最小 skill 项目。

        参数：root 为项目根；name 为技能名；version 为源码技能版本。
        返回：已创建的技能源码目录。
        异常：生产文档脚手架失败时抛出 RuntimeError。
        """

        # 技能名称和版本由 fixture 合同解析，显式参数仍优先。
        string_name = name or str(self.fixture_value("names", "owner_skill"))  # 最小技能项目的名称事实来自 fixture

        # 读取源码技能版本，避免把当前发布版本写入夹具实现。
        string_version = version or str(self.fixture_value("versions", "release_fixture"))  # fixture 技能版本

        # skill 源码必须位于 skills/<name> 正式目录。
        path_skill = root / "skills" / string_name  # 技能源码根

        # 递归创建技能根以支持空临时项目。
        path_skill.mkdir(parents=True)

        # 受管工作区夹具默认满足唯一根 tests 目录合同。
        (root / "tests").mkdir(exist_ok=True)

        # scripts 存放可执行验证入口。
        (path_skill / "scripts").mkdir(exist_ok=True)

        # references 存放评审和覆盖说明。
        (path_skill / "references").mkdir(exist_ok=True)

        # 技能入口 frontmatter 保持名称与目录一致。
        (path_skill / "SKILL.md").write_text(
            f"---\nname: {string_name}\ndescription: Use when testing\n---\n# Skill\n\n"
            "Validation chain: python -m unittest discover -s tests -t . -v\n",
            encoding="utf-8",
        )

        # 版本文件作为发布准备的源码事实。
        (path_skill / "VERSION").write_text(string_version + "\n", encoding="utf-8")

        # runtime manifest roles 驱动发布 fixture 的完整资源复制。
        _copy_runtime_manifest_resources(path_skill)

        # 公开文档夹具复用正式双语用户流程，避免评估包退化为内部最小样例。
        self.write_public_package_contract(path_skill, name=string_name, version=string_version)

        # 验证脚本保留历史 skill-creator 路径以触发迁移检查。
        str_legacy_validator = (
            "from pathlib import Path\n\n\ndef quick_validate_path() -> Path:\n"
            "    return Path.home() / '<agent-home>' / 'skills' / '.system' / "
            "'skill-creator' / 'scripts' / 'quick_validate.py'\n"
        )  # 旧路径迁移验证脚本正文

        # 脚本内容刻意保留旧路径以供迁移门禁识别。
        (path_skill / "scripts" / "quick_validate.py").write_text(
            str_legacy_validator,
            encoding="utf-8",
        )

        # 两份参考文档共享正式验证命令文本。
        str_quick_validate_command = (
            f"python skills/{string_name}/scripts/python/verify/quick_validate.py "
            f"skills/{string_name}"
        )  # 快速验证命令

        # 评审清单声明结构门禁的必要证据。
        (path_skill / "references" / "review-checklist.md").write_text(
            "\n".join(
                [
                    "# Review Checklist",
                    "",
                    "| Gate | Required evidence |",
                    "|------|-------------------|",
                    f"| Structure | `{str_quick_validate_command}` passes for this skill |",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        # 设计覆盖文档列出完整验证链。
        (path_skill / "references" / "skill-design-coverage.md").write_text(
            "\n".join(
                [
                    "# Skill Design Coverage",
                    "",
                    "- Validation gates include "
                    f"`{str_quick_validate_command}`, skill audit, AGENTS.md verification, "
                    "and the full evaluate chain.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        # 项目级 docs 目录用于发布治理变更事实。
        (root / "docs").mkdir(exist_ok=True)

        # 最小评估项目也必须具备完整 docs 治理目录，避免 verify_docs 把夹具结构误判为缺失。
        list_docs_directories = [  # 评估项目 docs 治理目录清单
            "docs/handoff",  # handoff 当前目录
            "docs/handoff/history_handoff",  # handoff 历史目录
            "docs/development",  # 当前开发记录的容器
            "docs/development/history_development",  # 已归档开发记录的容器
            "docs/install_configuration",  # 安装配置合同的容器
            "docs/git_manager",  # 当前 Git 发布记录的容器
            "docs/git_manager/history_git_manager",  # 已归档 Git 记录的容器
            "docs/dir_manager",  # 当前目录治理记录的容器
            "docs/dir_manager/change_reviews",  # 目录变更审批记录的容器
            "docs/dir_manager/history_dir_manager",  # 已归档目录治理记录的容器
        ]

        # 按治理目录清单递归创建夹具路径，保持与正式 scaffold 一致。
        for str_doc_directory in list_docs_directories:

            # 为当前目录补齐父级治理路径，保持夹具与正式 scaffold 同构。
            (root / str_doc_directory).mkdir(parents=True, exist_ok=True)

        # 最小文档内容保证 Git 仓库具有治理资料。
        (root / "docs" / "note.md").write_text("release governance\n", encoding="utf-8")

        # 控制画像使项目通过目录和发布合同识别。
        self.write_release_governance_profile(root, kind="skill", name=string_name)

        # 生产 scaffold 负责写入正式 docs、dir-manager 和 memory 资产，避免夹具自造退化文件。
        path_manage_docs = self.scripts_dir / "python" / "docs" / "manage_docs.py"  # 正式文档治理入口

        # 子进程环境关闭字节码缓存，避免污染评估项目。
        dict_scaffold_environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")  # 隔离子进程缓存

        # 调用正式文档脚手架并保留其结构化进程结果。
        process_scaffold = subprocess.run(  # 脚手架执行结果
            [sys.executable, str(path_manage_docs), "scaffold", str(root)],  # 脚手架命令及目标
            cwd=REPO_ROOT,  # 脚手架固定在 owner 仓库根执行
            env=dict_scaffold_environment,  # 子进程使用无缓存环境
            capture_output=True,  # 保留脚手架诊断输出
            text=True,  # 按文本读取标准流
            check=False,  # 由后续统一构造失败诊断
        )

        # scaffold 失败表示夹具不具备可验证的发布治理基线。
        if process_scaffold.returncode != 0:

            # 保留标准错误和标准输出，便于定位生产脚手架回归。
            raise RuntimeError(
                "> ERR: [Python] governed skill fixture scaffold failed: "
                f"{process_scaffold.stderr or process_scaffold.stdout}"
            )

        # 返回技能目录供调用方继续渲染或打包。
        return path_skill

    # 在 fixture 覆盖 role 内容后重新绑定 runtime manifest 摘要。
    def refresh_runtime_manifest_hashes(self, path_skill: Path) -> None:
        """刷新临时技能的 runtime manifest role 摘要。

        参数：path_skill 为已经复制 runtime resources 的临时技能根。
        返回：无；manifest 内容摘要与当前 fixture 文件同步。
        """

        # 复用模块级实现，保持复制和覆盖后的哈希语义一致。
        _refresh_runtime_manifest_hashes(path_skill)

    # 写入普通用户安装、调用、预览和交付所需的公开包资料。
    def write_public_package_contract(
        self,
        path_skill: Path,
        name: str,
        version: str,
    ) -> None:
        """把正式公开包合同写入临时技能目录。

        参数：path_skill 为技能根；name 为包名；version 为包版本。
        返回：无业务返回值，仅写入临时夹具文件和复用的 PNG 资产。
        异常：源资产或目标目录不可写时由文件系统异常直接报告。
        """

        # 版本数字同时写入 README、pyproject 和引用元数据，避免页面漂移。
        str_version_number = version.lstrip("vV")  # 不带 v 前缀的公开版本

        # 从 fixture 读取正式公开页面当前的源版本。
        str_source_public_version = str(  # fixture 公开源码版本
            self.fixture_value("versions", "source_public")  # 读取公开版本事实
        )

        # 正式 README 文案已通过双语用户合同和归属合同，夹具只替换版本事实。
        str_readme_english = (  # 英文普通用户页面
            (SKILL_DIR / "README.md")  # 正式英文页面路径
            .read_text(encoding="utf-8")  # 读取正式英文页面
            .replace(str_source_public_version, version)  # 将页面徽标版本同步到夹具版本
            .replace(str_source_public_version.lstrip("vV"), str_version_number)  # 让引用元数据使用同一版本号
        )

        # 中文页面沿用同一版本替换策略，保持双语安装入口一致。
        str_readme_chinese = (  # 中文普通用户页面
            (SKILL_DIR / "README-CN.md")  # 正式中文页面路径
            .read_text(encoding="utf-8")  # 读取正式中文页面
            .replace(str_source_public_version, version)  # 中文页面沿用夹具版本
            .replace(str_source_public_version.lstrip("vV"), str_version_number)  # 中文引用同步裸版本号
        )

        # 英文页面落盘后由发布包继续读取。
        (path_skill / "README.md").write_text(str_readme_english, encoding="utf-8")

        # 中文页面落盘后与英文页面保持同一版本。
        (path_skill / "README-CN.md").write_text(str_readme_chinese, encoding="utf-8")

        # 公开包元数据使用当前临时技能名称和版本，避免复制所有者版本。
        str_pyproject = f"""[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}"
version = "{str_version_number}"
description = "A Codex skill for repository instructions"
readme = "README.md"
requires-python = ">=3.10"
license = {{ file = "LICENSE" }}
"""  # 临时项目元数据文本

        # 元数据文件必须进入技能根，供发布工具检查名称与版本。
        (path_skill / "pyproject.toml").write_text(str_pyproject, encoding="utf-8")

        # 引用文件只记录当前夹具版本和公开仓库地址。
        str_citation = f"""cff-version: 1.2.0
title: "AGENTS.md Generator"
version: "{str_version_number}"
date-released: 2026-08-12
type: software
authors:
  - family-names: "Liu"
    given-names: "Jiyuan"
    affiliation: "Southeast University"
  - family-names: "Li"
    given-names: "He"
    affiliation: "Southeast University"
repository-code: "https://github.com/Eriemon/agents-md-generator"
url: "https://github.com/Eriemon/agents-md-generator"
license: "Apache-2.0"
"""  # 临时引用元数据文本

        # 引用文件随公开包分发，便于用户追踪版本来源。
        (path_skill / "CITATION.cff").write_text(str_citation, encoding="utf-8")

        # 许可正文直接复用正式 Apache 2.0 文件，避免夹具自造法律文本。
        shutil.copyfile(SKILL_DIR / "LICENSE", path_skill / "LICENSE")

        # 安全和贡献入口保持公开用户可读的最小说明。
        (path_skill / "SECURITY.md").write_text(
            "# Security\n\nReport vulnerabilities privately to the project maintainers.\n",
            encoding="utf-8",
        )

        # 贡献入口让公开包保留最小的协作说明。
        (path_skill / "CONTRIBUTING.md").write_text(
            "# Contributing\n\nDescribe the change and validation before opening a pull request.\n",
            encoding="utf-8",
        )

        # 双语 README 引用的本地 PNG 必须完整进入临时公开包。
        path_readme_assets = path_skill / "assets" / "readme"  # 临时 README 资源目录

        # 资源目录承载与页面逐一对应的本地 PNG 文件。
        path_readme_assets.mkdir(parents=True, exist_ok=True)

        # 资产名称保持与正式双语页面中的角色命名一致。
        tuple_asset_names = (
            "hero.png",  # 英文首屏图
            "hero-cn.png",  # 中文首屏图
            "project-facts.png",  # 英文事实图
            "project-facts-cn.png",  # 中文事实图
            "design-profile.png",  # 英文画像图
            "design-profile-cn.png",  # 中文画像图
            "rule-rendering.png",  # 英文规则图
            "rule-rendering-cn.png",  # 中文规则图
            "evidence-guard.png",  # 英文交付图
            "evidence-guard-cn.png",  # 中文交付图
        )

        # 按页面引用顺序复制资产，避免临时包出现缺图。
        for str_asset_name in tuple_asset_names:

            # 当前资产从正式技能目录复制到隔离夹具。
            shutil.copyfile(
                SKILL_DIR / "assets" / "readme" / str_asset_name,  # 正式资产来源
                path_readme_assets / str_asset_name,  # 临时包目标路径
            )

    # 初始化无需发布分支的基础 Git 仓库。
    def init_basic_git_repo(self, root: Path) -> None:
        """初始化仅含 master 分支的测试 Git 仓库。

        参数：root 为待初始化的临时项目根。
        返回：无业务返回值，Git 命令失败时由 subprocess 抛出异常。
        """

        # 显式指定 master，避免宿主机默认分支配置影响夹具。
        subprocess.run(
            ["git", "init", "-b", "master"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        # 固定作者名使测试提交不依赖全局 Git 配置。
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        # 无效域邮箱明确表示该身份只用于本地夹具。
        subprocess.run(
            ["git", "config", "user.email", "test-user.invalid"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

    # 提交夹具仓库中的全部当前内容。
    def git_commit_all(self, root: Path, message: str, when: str | None = None) -> None:
        """提交临时仓库中的全部文件并可固定提交时间。

        参数：root 为仓库根；message 为提交说明；when 为可选 Git 时间文本。
        返回：无业务返回值，Git 命令失败时由 subprocess 抛出异常。
        """

        # 子进程环境副本允许注入时间且不修改当前测试进程。
        dict_git_environment = dict(os.environ)  # Git 提交命令环境

        # 指定时间时同时固定 author 和 committer，保证历史排序可复现。
        if when:

            # 作者时间用于历史事实和审计显示。
            dict_git_environment["GIT_AUTHOR_DATE"] = when  # 固定作者时间

            # 提交者时间防止宿主当前时间改变排序。
            dict_git_environment["GIT_COMMITTER_DATE"] = when  # 固定提交者时间

        # 夹具提交覆盖当前仓库的全部新增和修改内容。
        subprocess.run(
            ["git", "add", "."],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            env=dict_git_environment,
        )

        # 使用调用方消息创建单个可审计提交。
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            env=dict_git_environment,
        )

    # 初始化包含发布分支的受管 Git 仓库。
    def init_governed_git_repo(self, root: Path) -> None:
        """初始化包含 master 和 release 的受管 Git 仓库。

        参数：root 为已落盘治理项目根。
        返回：无业务返回值，最终保持 master 为当前分支。
        """

        # 基础仓库仍显式使用 master 主分支。
        subprocess.run(
            ["git", "init", "-b", "master"], cwd=root, check=True, capture_output=True, text=True
        )

        # 固定本地提交作者名，避免依赖用户配置。
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=root, check=True, capture_output=True, text=True
        )

        # 固定测试专用邮箱以完成提交身份配置。
        subprocess.run(
            ["git", "config", "user.email", "test-user.invalid"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )

        # 首次提交收录已生成的全部治理文件。
        subprocess.run(["git", "add", "."], cwd=root, check=True, capture_output=True, text=True)

        # 初始化提交为 release 分支创建提供共同基点。
        subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True, text=True)

        # release 分支满足发布门禁要求的本地分支集合。
        subprocess.run(["git", "checkout", "-b", "release"], cwd=root, check=True, capture_output=True, text=True)

        # 评估从 master 开始，保持生产发布准备的入口状态。
        subprocess.run(["git", "checkout", "master"], cwd=root, check=True, capture_output=True, text=True)

    # 创建已渲染且带隔离安装副本的受管技能项目。
    def make_rendered_governed_skill_project(
        self,
        root: Path,
        name: str | None = None,
        project_version: str | None = None,
        installed_version: str | None = None,
    ) -> tuple[Path, Path]:
        """创建完成设计写入、Git 初始化和 AGENTS 渲染的技能项目。

        参数：root 为项目根；name 为技能名；project_version 与 installed_version 控制版本差异。
        返回：技能源码目录和隔离的已安装技能目录。
        """

        # 名称与两类版本由 fixture 合同解析，显式参数仍优先。
        string_name = name or str(self.fixture_value("names", "skill"))  # 渲染夹具使用的 fixture 技能名称

        # 读取源码项目版本，供设计和渲染结果写入。
        string_project_version = project_version or str(  # fixture 项目版本
            self.fixture_value("versions", "project_skill")  # 读取项目版本事实
        )

        # 读取隔离安装版本，供渲染源码优先级对照。
        string_installed_version = installed_version or str(  # 渲染夹具使用的 fixture 安装版本
            self.fixture_value("versions", "release_fixture")  # 读取安装版本事实
        )

        # 首先落盘可被设计和发布流程识别的技能骨架。
        path_skill = self.make_governed_skill_project(  # 技能源码目录
            root,  # 渲染夹具的隔离项目根
            name=string_name,  # 渲染夹具的技能名称
            version=string_project_version,  # 渲染夹具的项目版本
        )  # 已创建的技能源码目录

        # 渲染前满足受管工作区唯一根 tests 目录契约。
        (root / "tests").mkdir(exist_ok=True)

        # 完整技能答案用于强控制设计写入。
        dict_answers = self.skill_answers(name=string_name)  # 技能设计访谈答案

        # 答案文件是 collect_design_profile 批处理入口输入。
        path_answers = root / "answers.json"  # 已审答案输出路径

        # 附加匹配哈希的 subagent 审查并写入答案。
        self.write_reviewed_answers(root, path_answers, dict_answers)

        # 正式设计写入命令生成根 AGENTS 和控制画像派生资产。
        subprocess.run(
            [
                sys.executable,
                str(self.script_path("collect_design_profile.py")),
                str(root),
                "--answers",
                str(path_answers),
                "--write",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

        # 设计资产落盘后建立 master 与 release 的受管历史。
        self.init_governed_git_repo(root)

        # 隔离安装副本用于渲染版本对照，不修改用户真实 Codex home。
        path_installed_skill = self.make_installed_skill_fixture(  # 安装版本夹具目录
            root.parent / f"{root.name}-installed",  # 与项目并列的隔离夹具根
            version=string_installed_version,  # 调用方指定的安装版本
        )

        # 渲染器通过环境变量读取隔离安装副本。
        subprocess.run(
            [
                sys.executable,
                str(self.script_path("render_agents.py")),
                str(root),
                "--write",
                "--confirm-branch-governance",
                "--confirm-docs-layout",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            env=dict(os.environ, AGENTS_MD_INSTALLED_SKILL_DIR=str(path_installed_skill)),
        )

        # 返回源码和安装目录供后续版本、治理和发布断言使用。
        return path_skill, path_installed_skill

    # 为发布目录生成内容完整性收据。
    def make_release_receipt(
        self,
        release_dir: Path,
        skill_name: str,
        version: str,
        validation_level: str = "reduced_assurance",
    ) -> None:
        """为现有发布目录生成可供安装器验证的最小收据。

        参数：release_dir 为发布目录；skill_name 与 version 标识技能；validation_level 控制来源保证级别。
        返回：无业务返回值，写入 RELEASE_RECEIPT.json。
        """

        # 文件表记录每个正式内容文件的相对路径和 SHA-256。
        list_receipt_files: list[dict[str, str]] = []  # 发布收据文件清单

        # 稳定排序保证收据在不同文件系统上可复现。
        for path_entry in sorted(release_dir.rglob("*")):

            # 收据本身不能进入自身哈希清单。
            if path_entry.is_file() and path_entry.name != "RELEASE_RECEIPT.json":

                # 每个条目提供安装器重算所需的路径和摘要。
                list_receipt_files.append(
                    {
                        "path": path_entry.relative_to(release_dir).as_posix(),  # 跨平台发布相对路径
                        "sha256": hashlib.sha256(path_entry.read_bytes()).hexdigest(),  # 文件内容摘要
                    }
                )

        # 强验证表示发布目录直接来自 owner 仓库流程。
        str_provenance_mode = "repository-dist" if validation_level == "strong" else "external-copy"  # 发布来源模式

        # 收据字段覆盖安装器的版本、来源、净化和文件完整性合同。
        bytes_package_tree = json.dumps(  # 发布文件清单的确定性 JSON 字节表示。
            list_receipt_files,  # 收据中待摘要的发布文件清单。
            ensure_ascii=False,  # 保留收据中的非 ASCII 文本。
            sort_keys=True,  # 固定对象键序以保证摘要稳定。
            separators=(",", ":"),  # 使用确定性的紧凑 JSON 分隔符。
        ).encode("utf-8")

        # 构造覆盖安装器完整性合同的最小发布收据。
        dict_release_receipt = {  # 最小可验证发布收据
            "skill_name": skill_name,  # 发布技能名称
            "version": version,  # 发布语义版本
            "source_path": f"skills/{skill_name}",  # owner 仓库源码相对路径
            "generated_at": "2026-05-14T18:00:00",  # 固定生成时间保证夹具稳定
            "current_branch": "master",  # 打包时主分支事实
            "local_branches": ["master", "release"],  # 发布合同要求的本地分支
            "worktree_clean": True,  # 模拟打包时工作树干净
            "phase_results": {"pre": True, "post": True},  # 发布前后门禁结果
            "packaging_mode": "standalone-copy",  # 独立复制打包模式
            "validation_level": validation_level,  # 调用方指定的保证级别
            "provenance_mode": str_provenance_mode,  # 保证级别对应的来源模式
            "sanitization": {  # 发布副本净化证据
                "enabled": True,  # 净化流程已启用
                "scope": "broad",  # 扫描全部文本发布内容
                "mode": "auto-redact-dist-copy",  # 只修改 dist 副本
                "files": [],  # 当前最小夹具没有脱敏文件
                "receipt_required": True,  # 安装器必须复核净化区块
            },
            "files": list_receipt_files,  # 路径与内容摘要表
            "package_tree_sha256": hashlib.sha256(bytes_package_tree).hexdigest(),  # 基础包树摘要
        }

        # 收据使用稳定缩进便于篡改测试读取和修改。
        (release_dir / "RELEASE_RECEIPT.json").write_text(
            json.dumps(dict_release_receipt, indent=2),
            encoding="utf-8",
        )

    # 写入可被精确 cwd 筛选的 Codex 会话夹具。
    def write_codex_session_fixture(
        self,
        codex_home: Path,
        cwd: Path,
        session_id: str,
        lines: list[tuple[str, str]],
    ) -> Path:
        """写入精确 cwd 的最小 Codex rollout JSONL 会话。

        参数：codex_home 为隔离主目录；cwd 为会话工作目录；session_id 为 ID；lines 为角色与文本序列。
        返回：已写入的 rollout JSONL 文件路径。
        """

        # 日期分层路径匹配 Codex sessions 的正式存储布局。
        path_session_file = codex_home / "sessions" / "2026" / "05" / "13" / f"rollout-{session_id}.jsonl"  # 会话夹具文件

        # 隔离 Codex home 初始为空，递归创建日期目录。
        path_session_file.parent.mkdir(parents=True, exist_ok=True)

        # 首行元数据绑定会话 ID、时间、精确 cwd 和 Codex 来源。
        list_session_rows: list[dict[str, Any]] = [  # rollout JSONL 记录序列
            {
                "timestamp": "2026-05-13T10:00:00.000Z",  # 元数据事件时间
                "type": "session_meta",  # Codex 会话元数据类型
                "payload": {  # 精确会话身份和工作目录
                    "id": session_id,  # 调用方指定会话 ID
                    "timestamp": "2026-05-13T10:00:00.000Z",  # 会话创建时间
                    "cwd": str(cwd),  # exact-cwd 筛选依据
                    "originator": "Codex Desktop",  # 会话来源产品
                },
            }
        ]

        # 按调用方顺序追加用户和 agent 消息事件。
        for str_role, str_text in lines:

            # 角色映射为 Codex event_msg 支持的 payload 类型。
            str_message_type = "user_message" if str_role == "user" else "agent_message"  # Codex 消息事件类型

            # 每条输入行生成独立 JSONL 事件。
            list_session_rows.append(
                {
                    "timestamp": "2026-05-13T10:00:01.000Z",  # 消息事件固定时间
                    "type": "event_msg",  # Codex 对话事件类型
                    "payload": {  # 消息角色和正文
                        "type": str_message_type,  # 用户或 agent 消息标识
                        "message": str_text,  # 调用方提供的消息正文
                    },
                }
            )

        # 每个对象单独占一行并保留中文正文。
        str_session_jsonl = (
            "\n".join(json.dumps(row, ensure_ascii=False) for row in list_session_rows) + "\n"  # 序列化记录
        )  # 完整会话 JSONL

        # 写入结果供 session bootstrap 和 memory 测试读取。
        path_session_file.write_text(str_session_jsonl, encoding="utf-8")

        # 返回文件路径便于调用方记录证据来源。
        return path_session_file

    # 生成包含会话复读证据的演进审查结果。
    def ai_evolution_review(
        self,
        target: dict[str, Any],
        **review_options: Any,
    ) -> dict[str, Any]:
        """生成 AI evolution review 评估使用的结构化审查证据。

        参数：target 为候选演进目标。
        参数：review_options 接受结论、目标快照、会话证据和完整说明关键字。
        返回：满足 evolution review 校验器合同的审查映射。
        """

        # 选项键保持旧公共调用的关键字名称和缺省行为。
        str_verdict = review_options.get("verdict", "approve")  # 审查结论

        # 批准目标允许测试覆盖候选演进结果。
        approved_target = review_options.get("approved_target")  # 批准后目标

        # 原始目标允许测试构造审查前后差异。
        original_target = review_options.get("original_target")  # 原始目标

        # 会话标识记录复读证据对应的逻辑 ID。
        list_session_ids = review_options.get("session_ids")  # 已复读会话 ID

        # 会话路径记录复读证据的物理来源。
        session_paths = review_options.get("session_paths")  # 已复读会话路径

        # 状态位区分是否真正执行过历史复读。
        bool_session_reread_performed = review_options.get("session_reread_performed", False)  # 复读状态

        # 原因文本解释为什么需要或不需要复读。
        session_reread_reason = review_options.get("session_reread_reason", "")  # 复读原因

        # 调用方说明可以覆盖五个默认审查维度。
        str_full_explanation = review_options.get("full_explanation")  # 调用方完整说明

        # 缺省说明覆盖开发、设计、问题、分类和发布五个审查维度。
        dict_default_explanation = {  # 演进审查完整说明
            "development_flow": (  # 开发事实链
                "Read repository facts, updated scripts, ran focused tests, "
                "and verified docs governance."
            ),  # 开发流程说明
            "design_flow": (  # 设计控制链
                "Kept deterministic scripts responsible for contracts and blocked template "
                "writes until review matched the target."
            ),  # 模板写入控制说明
            "problem_analysis": (  # 核心风险分析
                "The risk was allowing a plausible summary to evolve templates without "
                "matching repository evidence."
            ),  # 模板演进风险说明
            "classification_rationale": (  # 分类依据
                "The approved target matches repository kind, governance vocabulary, "
                "and current docs evidence."
            ),  # 仓库事实匹配说明
            "release_alignment": "The summary aligns with handoff, changelog, development, and release evidence.",  # 发布证据一致性
        }

        # 返回结构模拟已读取仓库证据的完整 subagent 审查。
        return {
            "verdict": str_verdict,  # approve 或 reject 审查结论
            "approved_target": approved_target or target,  # 审查批准的最终目标
            "original_target": original_target or target,  # 审查前的原始目标
            "evidence_read": {  # 审查者实际读取的证据路径
                "conversation_snapshot_paths": [".agents/conversation-snapshots/example-handoff-10.json"],  # 对话快照证据
                "handoff_paths": ["docs/handoff/HANDOFF.md"],  # 当前交接证据
                "docs_paths": ["docs/git_manager/CHANGELOG.md", "docs/development/DEVELOPMENT.md"],  # 开发文档证据
                "release_evidence_paths": [],  # 默认场景没有独立发布证据
                "session_ids": list_session_ids or [],  # 审查证据会话标识
                "session_paths": session_paths or [],  # 已复读会话文件
            },
            "session_reread_performed": bool_session_reread_performed,  # 是否实际复读历史会话
            "session_reread_reason": session_reread_reason,  # 执行或跳过复读的原因
            "full_explanation": str_full_explanation or dict_default_explanation,  # 调用方覆盖或完整缺省说明
        }

