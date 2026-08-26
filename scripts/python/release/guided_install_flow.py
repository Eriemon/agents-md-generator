"""执行由 manifest 驱动的 Skill guided 安装流程。"""

# 允许本模块使用统一的现代类型注解。
from __future__ import annotations

# guided flow 需要读取表格、哈希、环境和事务文件。
import argparse
import csv
from datetime import datetime

# 文件内容和事务状态使用标准哈希、JSON 与系统调用。
import hashlib
import json
import os
import shutil
import uuid

# 路径与载荷类型用于 containment 和 receipt。
from pathlib import Path
from typing import Any

# 安装输入和发布验证均来自同一套受管 runtime 模块。
from install_release_manifest import read_receipt, skill_name_error, source_tree_manifest
from install_repository_validation import validate_release_dir
from installer_manifest_contract import validate_manifest_projection

# 解析 bundle 内唯一或显式指定的 env manifest。
def resolve_guided_manifest_path(
    path_bundle: Path,
    path_requested: str | None = None,
) -> Path:
    """解析并校验 guided manifest 的 containment 边界。

    参数:
        path_bundle: guided bundle 根目录。
        path_requested: 调用者显式指定的 manifest env 路径。
    返回:
        bundle 内的规范 manifest env 路径。
    异常:
        ValueError: 候选不唯一、路径越界或文件不存在。
    """

    # 显式值优先，环境变量只作为入口传递的兼容来源。
    str_requested: str = (
        path_requested or os.environ.get("AGENT_INSTALLER_MANIFEST_ENV_PATH", "")  # 显式或环境传入的 manifest 文本。
    ).strip()  # 去除路径两侧空白后再执行 containment 检查。

    # 显式路径只做规范化，不扫描 bundle 的其他文件。
    if str_requested:

        # 规范化调用者指定的 manifest 文件。
        path_manifest: Path = Path(str_requested).expanduser().resolve()  # 显式 manifest 路径。

    # 未指定时仅允许 bundle 内存在一个候选。
    else:

        # 收集 manifest env 候选并保持稳定排序。
        list_candidates: list[Path] = sorted(  # 供唯一候选判定的 manifest 文件集合。
            path_bundle.glob("*.manifest.env")  # 仅扫描当前 bundle 根。
        )

        # 候选数量不明确时拒绝猜测安装输入。
        if len(list_candidates) != 1:

            # 调用者必须修复 bundle 或显式传入路径。
            raise ValueError(
                "> ERR: [Python] exactly one manifest env candidate is required"
            )

        # 唯一候选作为后续校验的 manifest 文件。
        path_manifest = list_candidates[0].resolve()  # bundle 内唯一 manifest 路径。

    # manifest 必须存在且保持在 bundle 边界内。
    if not path_manifest.is_relative_to(path_bundle) or not path_manifest.is_file():

        # 阻断跨 bundle 重定向和缺失输入。
        raise ValueError(
            "> ERR: [Python] manifest env is missing or outside the installer bundle"
        )

    # 返回已经通过 containment 检查的文件。
    return path_manifest

# 读取 guided manifest 的键值字段并检查完整性。
def read_guided_manifest(
    path_bundle: Path,
    path_requested: str | None = None,
) -> dict[str, str]:
    """读取 guided bundle manifest 并拒绝不完整配置。

    参数:
        path_bundle: guided bundle 根目录。
        path_requested: 可选的显式 manifest env 路径。
    返回:
        大写 manifest 键到字符串值的映射。
    异常:
        ValueError: 文件缺失、格式错误、重复键或字段缺失。
    """

    # manifest 是 bundle 内唯一的脚本配置入口。
    path_manifest: Path = resolve_guided_manifest_path(  # 受 containment 约束的 manifest。
        path_bundle,  # 所有候选必须落在 bundle 根内。
        path_requested,  # 透传调用者的显式 manifest 路径。
    )

    # 缺失文件不能产生任何平台或路径默认值。
    if not path_manifest.is_file():

        # 返回具体路径，便于调用者修复 bundle。
        raise ValueError(f"> ERR: [Python] installer manifest is missing: {path_manifest}")

    # 保存解析后的键值，禁止执行不受信任的配置文本。
    dict_values: dict[str, str] = {}  # 后续路径校验使用的完整 manifest 映射。

    # 逐行读取单行键值，空行允许但非法行不允许。
    for str_line in path_manifest.read_text(encoding="utf-8").splitlines():

        # 空行只承担配置分隔作用。
        if not str_line.strip():

            # 跳过空白记录并继续校验后续内容。
            continue

        # 只在第一个等号处拆分，保留值中的等号。
        str_key, str_separator, str_value = str_line.partition("=")  # 当前行拆出的键、分隔符和值。

        # 键必须是大写标识符且必须带分隔符。
        if not str_separator or not str_key.isupper():

            # 原样报告非法行，避免调用者猜测解析结果。
            raise ValueError(
                f"> ERR: [Python] installer manifest contains an invalid line: {str_line}"
            )

        # 重复键会造成多入口读取事实不一致。
        if str_key in dict_values:

            # 具体回显重复键，便于修复 manifest。
            raise ValueError(
                f"> ERR: [Python] installer manifest contains a duplicate key: {str_key}"
            )

        # 保存当前键值供后续路径和哈希验证复用。
        dict_values[str_key] = str_value  # 当前 manifest 键的最终文本。

    # 这些字段共同决定安装根、平台投影和完整性绑定。
    tuple_required_keys: tuple[str, ...] = (
        "ALLOWED_PROJECT_KIND",  # manifest 允许的项目类型字段。
        "MANIFEST_ENV_RELATIVE_PATH",  # env manifest 的相对路径字段。
        "MANIFEST_JSON_RELATIVE_PATH",  # JSON manifest 文件定位字段。
        "MANIFEST_SHA256",  # JSON manifest 的字节身份摘要字段。
        "CATALOG_RELATIVE_PATH",  # 平台 catalog 的相对路径字段。
        "PROJECTION_RELATIVE_PATH",  # 派生平台表的内容位置字段。
        "PROJECTION_SCHEMA_RELATIVE_PATH",  # 校验表结构使用的 schema 位置字段。
        "PROJECTION_GENERATOR_RELATIVE_PATH",  # projection 生成器的相对路径字段。
        "PROJECTION_RECORD_CLASSES",  # projection 记录类声明字段。
        "PROJECTION_REQUIRED_COLUMNS",  # projection 必需列声明字段。
        "SOURCE_ROOT_RELATIVE",  # Skill 源根的相对路径字段。
        "BACKUP_DIRECTORY_NAME",  # 旧安装备份目录名称字段。
        "BATCH_ENTRY",  # Windows 批处理入口字段。
        "POWERSHELL_CANDIDATES",  # PowerShell 候选解释器字段。
        "SHELL_RUNTIME",  # Shell runtime 入口字段。
        "SHELL_UTILITIES",  # Shell 辅助命令字段。
        "PYTHON_CANDIDATES",  # Python 解释器候选字段。
        "HASH_COMMANDS",  # 摘要命令声明字段。
        "LOCK_FILE_NAME",  # 安装事务锁文件字段。
        "STAGING_PREFIX",  # staging 目录前缀字段。
        "SOURCE_MANIFEST_PREFIX",  # 源清单文件前缀字段。
        "RECOVERY_RECEIPT_SUFFIX",  # 恢复收据文件后缀字段。
        "QUARANTINE_DIRECTORY_NAME",  # 失败隔离目录名称字段。
        "ENTRYPOINTS",  # bundle 入口文件列表字段。
        "CATALOG_SHA256",  # catalog 内容摘要字段。
        "PROJECTION_SHA256",  # projection 字节身份校验摘要字段。
    )  # guided manifest 的完整必需字段合同。

    # 一次性列出所有空值或缺失字段。
    list_missing_keys: list[str] = [  # 后续错误载荷要报告的缺失 manifest 字段。
        str_key  # 当前缺失字段名。
        for str_key in tuple_required_keys  # 遍历 manifest 合同。
        if not dict_values.get(str_key)  # 只保留空值和不存在字段。
    ]

    # 配置不完整时禁止进入平台选择和路径解析。
    if list_missing_keys:

        # 统一返回字段级诊断，减少重复试错。
        raise ValueError(
            "> ERR: [Python] installer manifest is missing: "
            + ", ".join(list_missing_keys)
        )

    # 返回经过字段完整性检查的 manifest。
    return dict_values

# 读取 projection schema 中的记录类型和必需列。
def _projection_schema_values(
    path_projection_schema: Path,
) -> tuple[list[object], list[object]]:
    """读取 projection schema 的记录类与列合同。

    参数:
        path_projection_schema: projection JSON schema 路径。
    返回:
        schema 声明的记录类列表和必需列列表。
    异常:
        ValueError: schema 结构或声明值不符合合同。
    """

    # 读取 schema 根对象，避免把固定案例写入安装器。
    obj_schema: object = json.loads(  # projection schema 的未验证对象。
        path_projection_schema.read_text(encoding="utf-8")  # 读取 UTF-8 schema 正文。
    )

    # 逐层取出 schema properties，根类型错误时使用空对象。
    obj_properties: object = (  # schema properties 节点。
        obj_schema.get("properties", {})  # 读取 schema 声明的字段集合。
        if isinstance(obj_schema, dict)  # 根对象允许读取 projection 合同。
        else {}  # 根类型异常时不提供伪造配置。
    )

    # 从 properties 读取记录类和列节点。
    obj_record_schema: object = (  # 记录类节点供下方检查投影类别是否完整。
        obj_properties.get("record_classes", {})  # 取 record_classes 字段供类别完备性校验。
        if isinstance(obj_properties, dict)  # 对象根存在时才读取记录类别合同。
        else {}  # 根类型错误时保留空节点并触发列表门禁。
    )

    # 读取必需列节点作为表头合同。
    obj_column_schema: object = (  # 下游 TSV 表头的 schema 节点。
        obj_properties.get("required_columns", {})  # 取出 required_columns 字段。
        if isinstance(obj_properties, dict)  # 对象根允许读取列合同。
        else {}  # 非对象根不生成隐含列集合。
    )

    # 提取 schema 的常量声明供类型检查。
    obj_record_values: object = (  # schema 记录类原始值。
        obj_record_schema.get("const", [])  # 读取记录类 const 声明。
        if isinstance(obj_record_schema, dict)  # 节点为对象时才可读取。
        else []  # 节点类型错误时保持空声明。
    )

    # 提取必需列声明供 projection 表头检查。
    obj_column_values: object = (  # required_columns 的原始 const 值。
        obj_column_schema.get("const", [])  # 读取列集合常量。
        if isinstance(obj_column_schema, dict)  # schema 节点为对象时读取。
        else []  # 列节点失效时让后续列表门禁显式失败。
    )

    # 记录类声明必须是列表。
    if not isinstance(obj_record_values, list):

        # schema 错误必须在读取 projection 行前阻断。
        raise ValueError(
            "> ERR: [Python] platform projection schema record_classes is invalid"
        )

    # 列声明必须是非空列表。
    if not isinstance(obj_column_values, list) or not obj_column_values:

        # 没有字段合同时不能安全解析 TSV。
        raise ValueError(
            "> ERR: [Python] platform projection schema required_columns is invalid"
        )

    # 返回已经确认是列表的 schema 声明。
    return obj_record_values, obj_column_values

# 把 DictReader 行清洗为不含空列的字符串字段映射。
def _clean_projection_row(
    dict_row: dict[str, str | None],
) -> dict[str, str]:
    """清洗单个平台 projection 行的字段值。

    参数:
        dict_row: csv.DictReader 读取的原始平台行。
    返回:
        去除空键和值后的字符串字段映射。
    """

    # 只保留后续路径解析可以安全使用的完整字段。
    return {
        str_key: str_value  # 保留当前平台字段的字符串值。
        for str_key, str_value in dict_row.items()  # 遍历 DictReader 的全部列。
        if str_key is not None and str_value is not None  # 丢弃尾部空列。
    }

# 读取 projection 的平台行并检查表头和唯一 ID。
def _projection_rows(
    path_projection: Path,
    str_catalog_hash: str,
    list_required_record_classes: list[object],
    list_required_columns: list[object],
) -> list[dict[str, str]]:
    """解析平台投影并校验目录摘要、记录类和列集合。

    参数:
        path_projection: 平台投影 TSV 路径。
        str_catalog_hash: 已验证 catalog 的 SHA-256 摘要。
        list_required_record_classes: schema 声明的记录类。
        list_required_columns: schema 声明的必需列。
    返回:
        平台记录的普通字典列表。
    异常:
        ValueError: 元数据、表头、行数据或平台 ID 无效。
    """

    # 读取原始行，同时保留注释元数据。
    list_lines: list[str] = path_projection.read_text(encoding="utf-8").splitlines()  # 保留元数据行供摘要和记录类校验。

    # schema 中每个记录类都必须在投影元数据中出现。
    list_missing_record_classes: list[str] = [  # projection 缺失记录类。
        str_record_class  # 当前缺失的记录类名称。
        for str_record_class in list_required_record_classes  # 遍历 schema 记录类。
        if not any(  # 当前记录类必须出现在 projection 注释行。
            str_line.startswith(f"# {str_record_class} ")  # 当前记录类的元数据匹配。
            for str_line in list_lines  # 扫描投影头部和表格行。
        )
    ]

    # 缺少记录类时禁止继续构造平台菜单。
    if list_missing_record_classes:

        # 一次性报告全部缺失类，避免隐式降级。
        raise ValueError(
            "> ERR: [Python] platform projection is missing record classes: "
            + ", ".join(list_missing_record_classes)
        )

    # 头部摘要必须和 manifest 与 catalog 三方一致。
    str_header: str = next(  # 以摘要头为对账锚点，防止安装器使用旧 projection。
        (
            str_line  # 保存命中的 catalog 摘要头文本。
            for str_line in list_lines  # 扫描全部投影元数据和表格行。
            if str_line.startswith("# catalog_sha256=")  # 只接受受管 catalog 摘要前缀。
        ),
        "",  # 缺失摘要时返回空文本。
    )

    # 摘要漂移表示 projection 已经不是 catalog 的派生事实。
    if str_header != f"# catalog_sha256={str_catalog_hash}":

        # 不允许用旧菜单解释当前目录。
        raise ValueError(
            "> ERR: [Python] platform projection catalog hash metadata does not match"
        )

    # 去掉空行和注释，保留 TSV 表头及平台记录。
    list_table_lines: list[str] = [  # projection 数据行。
        str_line  # 当前待解析的表格行。
        for str_line in list_lines  # 遍历全部 projection 行。
        if str_line.strip() and not str_line.startswith("#")  # 排除元数据。
    ]

    # 表格至少需要表头和一条平台记录。
    if len(list_table_lines) < 2:

        # 空投影不能产生可交互安装目标。
        raise ValueError(
            "> ERR: [Python] platform projection contains no platform rows"
        )

    # 由表头驱动字段映射，避免复制平台目录顺序。
    list_rows: list[dict[str, str]] = [  # 将 csv.DictReader 行清洗成路径解析字段。
        _clean_projection_row(dict_row)  # 当前平台行的非空字符串字段。
        for dict_row in csv.DictReader(list_table_lines, delimiter="\t")  # 读取 TSV 平台行。
    ]

    # schema 列值统一转为字符串，用于表头合同比较。
    tuple_required_columns: tuple[str, ...] = tuple(  # projection 必需列集合。
        str(item)  # 当前 schema 列名。
        for item in list_required_columns  # 遍历 schema 列合同。
    )

    # 表头必须包含 schema 声明的每个字段。
    if not list_rows or any(
        str_column not in list_rows[0] for str_column in tuple_required_columns
    ):

        # 列错位会让安装路径解释到错误字段。
        raise ValueError(
            "> ERR: [Python] platform projection is missing required columns"
        )

    # 平台 ID 必须存在且在投影内唯一。
    list_platform_ids: list[str] = [  # projection 平台 ID 序列。
        str(dict_row.get("platform_id", "")).strip()  # 当前平台的规范 ID。
        for dict_row in list_rows  # 遍历平台投影行。
    ]

    # 空 ID 无法形成稳定的用户选择。
    if any(not str_platform_id for str_platform_id in list_platform_ids):

        # 阻断空平台项进入目标路径拼接。
        raise ValueError(
            "> ERR: [Python] platform projection contains an empty platform_id"
        )

    # 重复 ID 会让一次选择对应多个目标配置。
    if len(set(list_platform_ids)) != len(list_platform_ids):

        # 拒绝具有歧义的安装菜单。
        raise ValueError(
            "> ERR: [Python] platform projection contains duplicate platform_id values"
        )

    # 返回不依赖 csv 行对象的普通字段映射。
    return list_rows

# 读取 guided bundle 的平台 projection。
def read_guided_projection(
    path_projection: Path,
    str_catalog_hash: str,
    path_projection_schema: Path,
) -> list[dict[str, str]]:
    """读取并验证 guided 平台投影。

    参数:
        path_projection: 平台投影 TSV 路径。
        str_catalog_hash: catalog 的 SHA-256 摘要。
        path_projection_schema: projection schema 路径。
    返回:
        已验证的平台记录列表。
    异常:
        ValueError: schema 或投影内容不符合合同。
    """

    # schema 决定记录类和列，避免入口写死案例。
    tuple_schema_values: tuple[list[object], list[object]] = _projection_schema_values(  # 读取投影类别和表头合同。
        path_projection_schema  # schema 路径是当前 projection 的唯一结构来源。
    )

    # 拆出记录类列表供元数据完整性检查使用。
    list_record_classes: list[object] = tuple_schema_values[0]  # projection 记录类合同。

    # 拆出必需列列表供 TSV 表头检查使用。
    list_required_columns: list[object] = tuple_schema_values[1]  # projection 必需列合同。

    # 表格解析负责摘要、字段和 ID 唯一性检查。
    return _projection_rows(
        path_projection,
        str_catalog_hash,
        list_record_classes,
        list_required_columns,
    )

# 发现项目类型并执行 Skill 类型适用性门禁。
def _resolve_project_kind(
    object_arguments: argparse.Namespace,
    path_skill_root: Path,
    str_allowed_kind: str,
) -> str:
    """解析当前项目类型并确认其允许进入 Skill installer。

    参数:
        object_arguments: guided CLI 参数对象。
        path_skill_root: 发布包中的 Skill 根目录。
        str_allowed_kind: manifest 声明的允许项目类型。
    返回:
        已确认的项目类型字符串。
    异常:
        SystemExit: 类型缺失或与 manifest 不匹配。
    """

    # 优先使用调用者或环境提供的显式治理事实。
    str_project_kind: str = (
        object_arguments.project_kind  # 调用者显式声明的项目类型优先级最高。
        or os.environ.get("AGENT_PROJECT_KIND")  # 环境变量作为入口传递的治理事实。
        or ""  # 两个来源都缺失时保持 fail-closed 空值。
    ).strip()  # 当前项目治理类型。

    # 缺少显式类型时读取相邻治理 profile。
    if not str_project_kind:

        # 发布包所属项目的 profile 作为第一候选来源。
        path_project_profile: Path = (  # 发布包相邻项目 profile。
            path_skill_root.parent / ".agents" / "agents-control.json"  # dist 所属项目治理文件。
        )

        # release bundle 从其他工作目录启动时回退到当前 profile。
        if not path_project_profile.is_file():

            # 当前 cwd profile 只作为明确的第二候选。
            path_project_profile = Path.cwd() / ".agents" / "agents-control.json"  # 当前工作目录 profile。

        # 只读取 JSON kind，不把未知字段变成默认权限。
        if path_project_profile.is_file():

            # profile JSON 是受控事实，不执行其中任何文本。
            obj_project_profile: object = json.loads(  # 项目 profile 未验证对象。
                path_project_profile.read_text(encoding="utf-8")  # 载入治理 profile 的 UTF-8 正文。
            )

            # 根对象确认后提取项目类型。
            str_project_kind = (  # profile 声明的项目类型。
                str(obj_project_profile.get("kind", "")).strip()  # 提取 profile 的项目类型值。
                if isinstance(obj_project_profile, dict)  # 只有 JSON 对象可提供 kind 字段。
                else ""  # 其他根类型不产生默认项目权限。
            )

    # 缺少分类时 fail-closed，不能默认当作 Skill 项目。
    if not str_project_kind:

        # 调用者必须显式补充项目类型后重试。
        raise SystemExit(
            "> ERR: [Python] project kind is required for the Skill installer"
        )

    # 非 Skill 项目必须在任何文件写入前拒绝。
    if str_project_kind != str_allowed_kind:

        # manifest 适用性不匹配时禁止物化安装器。
        raise SystemExit(
            f"> ERR: [Python] project kind '{str_project_kind}' is not eligible for the Skill installer"
        )

    # 返回通过项目分类门禁的 kind。
    return str_project_kind

# 读取 bundle manifest、project kind 和可信 Skill 根。
def _load_guided_manifest_context(
    object_arguments: argparse.Namespace,
    path_bundle: Path,
) -> dict[str, Any]:
    """读取 guided manifest 并完成 project kind 适用性门禁。

    参数:
        object_arguments: guided CLI 参数对象。
        path_bundle: guided bundle 根目录。
    返回:
        manifest、可信 Skill 根和通过门禁的项目类型。
    异常:
        SystemExit: manifest projection 或项目类型校验失败。
    """

    # 复用完整输入加载流程，避免 manifest context 自递归。
    dict_manifest_context: dict[str, Any] = _load_guided_inputs(  # 读取 bundle 的 manifest、根目录和项目分类事实。
        object_arguments,  # 显式平台、项目类型和 manifest env 的 CLI 来源。
        path_bundle,  # manifest projection contract 使用的 bundle 资源边界。
    )

    # 拆出资源验证继续使用的 manifest 映射。
    dict_manifest: dict[str, str] = dict_manifest_context["dict_manifest"]  # 受摘要绑定的 manifest。

    # Skill 根决定 catalog、projection 和发布收据的边界。
    path_skill_root: Path = dict_manifest_context["path_skill_root"]  # catalog、projection 与发布包验证的 Skill 根。

    # 保留 project kind 适用性门禁结论进入最终事实载荷。
    str_project_kind: str = dict_manifest_context["str_project_kind"]  # 已确认的项目类型。

    # 返回资源加载阶段需要的三项可信事实。
    return {
        "dict_manifest": dict_manifest,  # 已完成字段和摘要绑定的 manifest。
        "path_skill_root": path_skill_root,  # 资源读取和 dist provenance 共享的 containment 边界。
        "str_project_kind": str_project_kind,  # 通过 project kind 适用性门禁的类型。
    }

# 验证 bundle 路径、哈希和发布收据，并返回平台事实。
def _load_guided_inputs(
    object_arguments: argparse.Namespace,
    path_bundle: Path,
) -> dict[str, Any]:
    """加载 guided bundle 的 manifest、projection、catalog 和发布身份。

    参数:
        object_arguments: guided CLI 参数对象。
        path_bundle: guided bundle 根目录。
    返回:
        绑定 manifest、Skill 根、平台行、catalog、项目类型和两个内容摘要的对象。
    异常:
        SystemExit: 任一输入、哈希或发布收据验证失败。
    """

    # 统一读取 manifest 和其 projection 的可信 Skill 根。
    dict_manifest: dict[str, str] = read_guided_manifest(  # 读取后续路径和哈希校验所需的 manifest。
        path_bundle,  # bundle 根限制 manifest 候选范围。
        object_arguments.manifest_env_path,  # 使用调用者指定的 env 路径。
    )

    # 解析 projection contract 使用的 env 文件。
    path_manifest_env: Path = resolve_guided_manifest_path(  # manifest env 的规范绝对位置。
        path_bundle,  # manifest env 必须处于同一 bundle。
        object_arguments.manifest_env_path,  # 透传显式 env 路径选择。
    )

    # projection contract 负责 JSON、env、摘要和相对路径绑定。
    try:

        # 取得已验证的 Skill 根，后续所有资源以其为边界。
        tuple_manifest_result: tuple[Any, Any, Path, Any] = validate_manifest_projection(  # 校验 env、JSON 和 Skill 根绑定。
            path_bundle,  # bundle 是所有相对路径的 containment 根。
            path_manifest_env,  # 使用已选择的 manifest env 文件。
        )

        # 只保留 contract 返回的可信 Skill 根供资源校验复用。
        path_skill_root: Path = tuple_manifest_result[2]  # manifest contract 绑定的 Skill 根。

    # 将 manifest 内容错误转换为稳定入口失败。
    except (OSError, TypeError, ValueError) as object_error:

        # 保留底层字段错误，阻止后续平台读取。
        raise SystemExit(
            f"> ERR: [Python] manifest projection validation failed: {object_error}"
        ) from object_error

    # 当前项目类型必须来自显式事实或治理 profile。
    str_project_kind: str = _resolve_project_kind(  # 通过 manifest 适用性门禁的项目类型。
        object_arguments,  # 显式参数和环境治理来源。
        path_skill_root,  # 相邻 profile 的查找根。
        dict_manifest["ALLOWED_PROJECT_KIND"],  # manifest 声明的唯一允许类型。
    )

    # 复用资源验证器完成 bundle 入口、哈希、平台和 release 检查。
    return _load_guided_resource_facts(  # 已验证的安装源事实。
        dict_manifest,  # manifest 路径和摘要声明。
        path_bundle,  # bundle containment 根。
        path_skill_root,  # Skill 资源根。
        str_project_kind,  # 适用性门禁后的项目类型。
    )

# 校验 bundle 入口、projection、catalog 和 dist release 身份。
def _load_guided_resource_facts(
    dict_manifest: dict[str, str],
    path_bundle: Path,
    path_skill_root: Path,
    str_project_kind: str,
) -> dict[str, Any]:
    """加载 guided 安装继续执行所需的资源事实。

    参数:
        dict_manifest: 已完成字段和摘要绑定的 manifest。
        path_bundle: guided bundle 根目录。
        path_skill_root: manifest contract 绑定的 Skill 根。
        str_project_kind: project kind 适用性门禁结果。
    返回:
        平台菜单、catalog 和两个内容摘要的事实映射。
    异常:
        SystemExit: 入口、路径、哈希或发布收据验证失败。
    """

    # manifest 声明的三个脚本入口必须实际存在。
    list_entrypoints: list[str] = [  # bundle 入口文件列表。
        str_entrypoint  # 当前入口文件相对路径。
        for str_entrypoint in dict_manifest["ENTRYPOINTS"].split(",")  # 读取入口声明。
        if str_entrypoint  # 忽略声明末尾的空字段。
    ]

    # 不完整 bundle 不得继续读取用户目标或平台路径。
    if not all(
        (path_bundle / str_entrypoint).is_file()
        for str_entrypoint in list_entrypoints
    ):

        # 缺失入口表示当前 bundle 不是完整安装源。
        raise SystemExit(
            "> ERR: [Python] installer bundle entrypoints are incomplete"
        )

    # 以 catalog_rel 声明构造平台注册集合根文件。
    path_catalog: Path = (  # catalog 是平台注册集合的原始来源。
        path_bundle / dict_manifest["CATALOG_RELATIVE_PATH"]  # 从 catalog_rel 取得文件位置。
    ).resolve()

    # 将 projection_rel 声明转换为平台菜单派生文件。
    path_projection: Path = (  # projection 是平台菜单的派生输入。
        path_bundle / dict_manifest["PROJECTION_RELATIVE_PATH"]  # 目标菜单从此文件读取平台行。
    ).resolve()

    # 让 schema_rel 声明控制平台表头和记录类别约束。
    path_projection_schema: Path = (  # schema 决定平台表头和记录类别约束。
        path_bundle / dict_manifest["PROJECTION_SCHEMA_RELATIVE_PATH"]  # 表结构检查从此文件读取合同。
    ).resolve()

    # manifest 路径不能把读取重定向到 Skill 根之外。
    if (
        not path_catalog.is_relative_to(path_skill_root)
        or not path_projection.is_relative_to(path_skill_root)
        or not path_projection_schema.is_relative_to(path_skill_root)
    ):

        # 所有外部资源路径都必须在已验证的 Skill 根内。
        raise SystemExit(
            "> ERR: [Python] installer manifest path escapes the Skill root"
        )

    # catalog、projection 和 schema 都必须是普通文件。
    if not path_catalog.is_file() or not path_projection.is_file() or not path_projection_schema.is_file():

        # 目录替代物和缺失文件都不能作为配置输入。
        raise SystemExit("> ERR: [Python] platform catalog or projection is missing")

    # 计算原始摘要，并绑定到 manifest 声明的值。
    str_catalog_hash: str = hashlib.sha256(  # catalog 原始字节摘要。
        path_catalog.read_bytes()  # 摘要绑定 catalog 当前字节，不读取解析后对象。
    ).hexdigest()

    # 为 projection 计算独立的原始字节摘要。
    str_projection_hash: str = hashlib.sha256(  # 记录 projection 的菜单派生字节身份。
        path_projection.read_bytes()  # 摘要绑定 projection 当前字节，不读取旧缓存。
    ).hexdigest()

    # catalog 漂移时必须重新生成 projection。
    if str_catalog_hash != dict_manifest["CATALOG_SHA256"]:

        # 拒绝使用与目录不对应的派生菜单。
        raise SystemExit(
            "> ERR: [Python] platform catalog hash mismatch; regenerate the projection"
        )

    # projection 篡改时禁止继续读取平台行。
    if str_projection_hash != dict_manifest["PROJECTION_SHA256"]:

        # 保持 manifest 与投影的一致性绑定。
        raise SystemExit(
            "> ERR: [Python] platform projection hash mismatch; regenerate the projection"
        )

    # 读取平台行并确认 projection 的记录合同。
    list_platforms: list[dict[str, str]] = read_guided_projection(  # 通过 schema 和摘要校验的平台事实。
        path_projection,  # 当前 bundle 的平台 projection。
        str_catalog_hash,  # projection 必须对账到当前 catalog 摘要。
        path_projection_schema,  # projection 行结构的 schema 来源。
    )

    # catalog 根对象和平台映射必须是可比较的结构。
    obj_catalog: object = json.loads(  # 解析 catalog 根对象供平台 ID 对账。
        path_catalog.read_text(encoding="utf-8")  # 载入 catalog 的 UTF-8 正文。
    )

    # 保留可比较的 catalog 映射。
    dict_catalog: dict[str, Any] = (  # 根类型确认后的 catalog 字段集合。
        obj_catalog if isinstance(obj_catalog, dict) else {}  # 根类型异常时进入后续结构门禁。
    )

    # 读取注册平台映射供集合对账。
    obj_catalog_platforms: object = dict_catalog.get("platforms", {})  # catalog 声明的平台字段。

    # 归集 projection 声明的平台 ID。
    set_projection_ids: set[str] = {  # 用于与 catalog 平台键做集合对账。
        str(dict_platform["platform_id"])  # 当前行的稳定平台标识。
        for dict_platform in list_platforms  # 遍历已通过 schema 的平台记录。
    }

    # projection 与注册 catalog 必须逐项对账。
    if not isinstance(obj_catalog_platforms, dict) or set(obj_catalog_platforms) != set_projection_ids:

        # 行集合不一致时阻断安装目标解析。
        raise SystemExit(
            "> ERR: [Python] platform projection rows do not match the registered platform catalog"
        )

    # guided installer 只接受带收据的版本化 dist Skill 根。
    if path_skill_root.parent.name != "dist":

        # 源码树不能伪装成可安装发布包。
        raise SystemExit(
            "> ERR: [Python] guided installer requires a versioned release under dist"
        )

    # 发布目录验证覆盖收据、版本和内容策略。
    dict_release_validation: dict[str, Any] = validate_release_dir(  # 读取版本化 dist 发布包验证证据。
        path_skill_root  # 发布根必须是 projection contract 返回的 Skill 根。
    )

    # 任一发布错误都必须在目标路径解析前停止。
    if dict_release_validation["errors"]:

        # 一次回显所有发布验证错误，保持失败可追踪。
        raise SystemExit(
            "> ERR: [Python] guided installer release validation failed: "
            + "; ".join(
                str(item) for item in dict_release_validation["errors"]
            )
        )

    # 将多项输入事实集中成带字段名的不可变对象。
    return {
        "dict_manifest": dict_manifest,  # 完整 manifest 映射供后续事务读取。
        "path_skill_root": path_skill_root,  # 后续资源 containment 的唯一边界。
        "list_platforms": list_platforms,  # 已绑定摘要的动态平台菜单。
        "dict_catalog": dict_catalog,  # 注册平台集合的对账事实。
        "str_project_kind": str_project_kind,  # manifest 适用性门禁的结果。
        "str_catalog_hash": str_catalog_hash,  # projection 来源的 catalog 字节摘要。
        "str_projection_hash": str_projection_hash,  # 用户菜单绑定的 projection 字节摘要。
    }

# 从投影平台行中取得用户明确选择的一行。
def _select_platform(
    object_arguments: argparse.Namespace,
    list_platforms: list[dict[str, str]],
) -> dict[str, str]:
    """选择唯一平台记录并拒绝未知平台。

    参数:
        object_arguments: guided CLI 参数对象。
        list_platforms: 已通过 projection 校验的平台列表。
    返回:
        用户选定的平台记录。
    异常:
        SystemExit: 输入无效、范围越界或平台不存在。
    """

    # 优先使用调用者传入的平台 ID，缺失时才展示事实菜单。
    str_platform_id: str = str(object_arguments.platform or "").strip()  # 用户平台 ID。

    # 菜单只展示 projection 中存在的平台，不生成隐藏默认值。
    if not str_platform_id:

        # 输出动态平台列表供人工选择。
        print("> INFO: [Python] Available platforms:")

        # 通过显示名和稳定 ID 让选择结果可审计。
        for int_index, dict_platform in enumerate(list_platforms, start=1):

            # 每行同时显示序号、显示名和稳定 ID。
            str_platform_summary: str = f"{dict_platform['display_name']} ({dict_platform['platform_id']})"  # 菜单展示摘要。

            # 输出当前平台摘要，供人工确认菜单选择。
            print(f"> INFO: [Python]   {int_index}) {str_platform_summary}")

        # 读取数字只用于索引已验证的平台列表。
        try:

            # 交互输入不能直接参与路径拼接。
            int_number: int = int(input("Select a platform number: ").strip())  # 菜单序号。

        # 非数字输入不得改变平台事实。
        except (EOFError, ValueError) as object_error:

            # 将交互失败转换为稳定的安装错误。
            raise SystemExit(
                "> ERR: [Python] platform selection is invalid"
            ) from object_error

        # 菜单范围必须落在已验证列表内。
        if int_number < 1 or int_number > len(list_platforms):

            # 越界选择不能猜测相邻平台。
            raise SystemExit(
                "> ERR: [Python] platform selection is outside the available menu"
            )

        # 只从投影行读取最终平台 ID。
        str_platform_id = list_platforms[int_number - 1]["platform_id"]  # 选定平台 ID。

    # 按稳定 ID 匹配唯一平台记录。
    list_matches: list[dict[str, str]] = [  # 匹配的平台记录。
        dict_platform  # 当前候选平台。
        for dict_platform in list_platforms  # 遍历已验证的平台行。
        if dict_platform.get("platform_id") == str_platform_id  # 比较稳定 ID。
    ]

    # 未知或重复平台不能获得任何默认路径。
    if len(list_matches) != 1:

        # 具体回显用户选择，方便修复调用参数。
        raise SystemExit(
            f"> ERR: [Python] platform '{str_platform_id}' is not present in the verified projection"
        )

    # 返回唯一的平台配置事实。
    return list_matches[0]

# 生成版本化发布 Skill 的源树清单和摘要。
def _prepare_source(
    object_arguments: argparse.Namespace,
    path_skill_root: Path,
) -> dict[str, Any]:
    """准备并验证本次安装的不可变源目录。

    参数:
        object_arguments: guided CLI 参数对象。
        path_skill_root: 已验证发布包中的 Skill 根。
    返回:
        绑定源目录、源树清单、清单摘要和技能名称的对象。
    异常:
        SystemExit: 源目录选项、身份文件或源树节点不安全。
    """

    # guided flow 禁止显式源码路径绕过 dist provenance。
    if object_arguments.skill_source:

        # --skill-source 会把源码树直接变成安装输入。
        raise SystemExit(
            "> ERR: [Python] --skill-source is forbidden; install only from a versioned dist release"
        )

    # 安装源固定为通过收据验证的版本化 Skill 根。
    path_source: Path = path_skill_root  # dist provenance 绑定的 Skill 安装源。

    # Skill 入口文件用于确认发布包身份。
    path_skill_file: Path = path_source / "SKILL.md"  # 用户可见技能说明入口。

    # VERSION 文件用于确认发布版本身份。
    path_version_file: Path = path_source / "VERSION"  # 版本化发布包的身份文件。

    # 源目录和身份文件必须完整存在。
    if not path_source.is_dir() or not path_skill_file.is_file() or not path_version_file.is_file():

        # 缺少身份文件时不允许创建任何目标目录。
        raise SystemExit(
            "> ERR: [Python] Skill source must contain SKILL.md and VERSION"
        )

    # 复制前生成包含节点类型的源树事实清单。
    try:

        # 清单同时作为 staging 和 final 的字节身份基准。
        list_source_manifest: list[dict[str, Any]] = source_tree_manifest(  # 源目录清单。
            path_source  # 复制前的源树事实根。
        )

    # 不安全路径必须在复制前被结构化拒绝。
    except (OSError, ValueError) as object_error:

        # 保留底层路径诊断，避免静默跳过节点。
        raise SystemExit(
            f"> ERR: [Python] Skill source manifest contains an unsafe path: {object_error}"
        ) from object_error

    # 空清单可能来自链接根或不可读目录。
    if not list_source_manifest:

        # 空源目录不能生成有效安装副本。
        raise SystemExit(
            "> ERR: [Python] Skill source manifest is empty or unavailable"
        )

    # 符号链接和特殊节点不得进入复制事务。
    list_unsafe_entries: list[str] = [  # 源目录不安全节点路径。
        str(dict_entry["path"])  # 当前不安全节点相对路径。
        for dict_entry in list_source_manifest  # 遍历源树事实。
        if dict_entry.get("kind") not in {"file", "directory"}  # 只允许普通节点。
    ]

    # 一次回显全部不安全节点，便于源树修复。
    if list_unsafe_entries:

        # 在复制前停止，防止跟随外部对象。
        raise SystemExit(
            "> ERR: [Python] Skill source contains unsafe nodes: "
            + ", ".join(list_unsafe_entries)
        )

    # 使用稳定 JSON 绑定本次复制输入。
    bytes_source_manifest: bytes = json.dumps(  # 源树清单规范字节。
        list_source_manifest,  # 将节点清单作为摘要输入。
        ensure_ascii=False,  # 保留非 ASCII 文件名的稳定语义。
        sort_keys=True,  # 消除对象键插入顺序差异。
        separators=(",", ":"),  # 消除 JSON 空白差异。
    ).encode("utf-8")

    # 对规范清单字节计算源身份摘要。
    str_source_manifest_hash: str = hashlib.sha256(  # 源树清单摘要。
        bytes_source_manifest  # 清单摘要绑定本轮不可变复制输入。
    ).hexdigest()

    # 收据中的 skill_name 是去除版本后缀后的安装目标名称权威来源。
    dict_receipt: dict[str, Any] = read_receipt(path_source)[1]  # 已验证的发布收据对象

    # 只接受收据声明的非空单一技能名称，不能把 dist 目录名直接当作目标名。
    str_skill_name: str = str(dict_receipt.get("skill_name", "")).strip()  # 无版本后缀的安装目标名

    # 收据缺少安全名称时阻断目标路径计算。
    str_skill_name_error: str | None = skill_name_error(str_skill_name)  # 收据技能名诊断

    # 只允许经过统一路径叶节点校验的收据名称进入事务。
    if str_skill_name_error:

        # 版本化发布目录不能用不安全或缺失的收据名称安装。
        raise SystemExit(
            f"> ERR: [Python] release receipt skill name is invalid: {str_skill_name_error}"
        )

    # 不安全叶节点不得进入目标路径。
    if not str_skill_name or str_skill_name in {".", ".."}:

        # 拒绝空名称和父目录语义。
        raise SystemExit(
            "> ERR: [Python] Skill source name is not a safe destination component"
        )

    # 将源身份事实集中成不可变对象供复制事务使用。
    return {
        "path_source": path_source,  # 已通过 dist provenance 的源目录。
        "list_source_manifest": list_source_manifest,  # 复制前源树清单。
        "str_source_manifest_hash": str_source_manifest_hash,  # 源目录指纹供 staging 对账。
        "str_skill_name": str_skill_name,  # 安全的目标路径技能名。
    }

# 解析 target_root、环境根和平台相对根。
def _resolve_platform_roots(
    object_arguments: argparse.Namespace,
    dict_platform: dict[str, str],
) -> dict[str, Path]:
    """解析本轮安装使用的 containment 根和平台根。

    参数:
        object_arguments: guided CLI 参数对象。
        dict_platform: 已验证的平台投影记录。
    返回:
        containment 根和平台安装根的路径映射。
    异常:
        SystemExit: 目标根或平台环境根不存在或不安全。
    """

    # 两个路径变量分别承载 containment 根和平台根。
    path_boundary: Path  # 事务所有外部路径必须位于此边界内。

    # projection 解析出的平台根用于拼接受管安装目录。
    path_platform_home: Path  # projection 解析出的平台安装根。

    # 根据调用者是否提供目标根选择路径来源。
    if object_arguments.target_root:

        # 自定义根是本次安装唯一的 containment 起点。
        path_boundary = Path(object_arguments.target_root).expanduser().resolve()  # 显式目标根。

        # 不自动创建拼写错误的根目录。
        if not path_boundary.is_dir():

            # 目标根错误必须在事务开始前失败。
            raise SystemExit("> ERR: [Python] target root does not exist")

        # 自定义根同时作为平台路径根。
        path_platform_home = path_boundary  # 自定义平台根。

    # 未覆盖时按 projection 的环境声明解析平台根。
    else:

        # 读取平台投影声明的环境变量名称和值。
        str_home_env: str = str(dict_platform.get("home_env", ""))  # 平台根环境变量名。

        # 读取环境变量的实际平台根文本供后续目录检查。
        str_home_value: str = os.environ.get(str_home_env, "").strip()  # 平台根环境值。

        # platform_root 模式要求环境目录真实存在。
        if dict_platform.get("home_env_mode") == "platform_root" and str_home_value:

            # 环境值规范化为本轮平台 containment 根。
            path_platform_home = Path(str_home_value).expanduser().resolve()  # 环境平台根。

            # 不允许把不存在的环境值当作新根创建。
            if not path_platform_home.is_dir():

                # 环境根错误必须 fail-closed。
                raise SystemExit("> ERR: [Python] platform home directory is invalid")

            # 环境根作为目标 containment 边界。
            path_boundary = path_platform_home  # 阻断平台环境根外的路径逃逸。

        # 默认模式使用当前用户根和 projection 的子目录。
        else:

            # 操作系统用户根是默认 containment 边界。
            path_boundary = Path.home().resolve()  # 用户根边界。

            # 平台相对根由 projection 的目录字段决定。
            path_platform_home = (  # 平台相对根。
                path_boundary / dict_platform["user_home_dir"]  # 从 projection 读取平台用户根目录。
            ).resolve()

    # 返回两个路径根，后续只在此基础上构造目标。
    return {
        "path_boundary": path_boundary,  # 外部路径的 containment 根。
        "path_platform_home": path_platform_home,  # 目标目录的安装平台根。
    }

# 解析平台根和目标路径，并执行 containment 检查。
def _resolve_destination(
    object_arguments: argparse.Namespace,
    dict_platform: dict[str, str],
    str_skill_name: str,
    path_source: Path,
) -> dict[str, Any]:
    """解析 guided 安装目标并拒绝越界、链接和覆盖风险。

    参数:
        object_arguments: guided CLI 参数对象。
        dict_platform: 已验证的平台投影记录。
        str_skill_name: 已验证的 Skill 名称。
        path_source: 版本化发布源目录。
    返回:
        绑定 containment 根、平台根、最终目标和目标存在状态的对象。
    异常:
        SystemExit: 根目录、目标路径或替换意图不安全。
    """

    # 解析调用者选择的 containment 根和平台安装根。
    dict_platform_roots: dict[str, Path] = _resolve_platform_roots(  # 目标根解析结果。
        object_arguments,  # target_root 和平台环境选项。
        dict_platform,  # 已验证的平台目录字段。
    )

    # 后续目标校验复用统一的 containment 根。
    path_boundary: Path = dict_platform_roots["path_boundary"]  # 外部路径边界。

    # 后续目标拼接复用统一的平台根。
    path_platform_home: Path = dict_platform_roots["path_platform_home"]  # 平台安装根。

    # 目标目录由平台安装子目录和安全技能名构成。
    path_destination: Path = (  # 最终安装目标。
        path_platform_home / dict_platform["skill_install_dir"] / str_skill_name  # 拼接受管技能安装子目录。
    ).resolve()

    # 目标必须保持在选定的 containment 根内。
    if not path_destination.is_relative_to(path_boundary):

        # 拒绝投影目录逃逸。
        raise SystemExit("> ERR: [Python] destination escapes the selected target root")

    # 平台根必须预先存在，安装器只创建其受管下一层。
    if not path_platform_home.is_dir():

        # 缺失平台根不能通过任意层级 mkdir 掩盖。
        raise SystemExit("> ERR: [Python] configured platform root does not exist")

    # 目标不能写回发布源形成递归复制。
    if path_destination.is_relative_to(path_source):

        # 源和目标边界重叠时拒绝安装。
        raise SystemExit("> ERR: [Python] destination is inside the Skill source")

    # 记录普通目录和符号链接的存在状态。
    bool_destination_exists: bool = (  # 目标是否已经有可见节点。
        path_destination.exists() or path_destination.is_symlink()  # 同时识别普通目录和符号链接。
    )

    # 目标符号链接不能交给 replace 事务处理。
    if path_destination.is_symlink():

        # 防止替换逻辑跟随外部链接。
        raise SystemExit(
            "> ERR: [Python] installation destination must not be a symbolic link"
        )

    # 已有目录必须有显式 replace 意图。
    if bool_destination_exists and not object_arguments.replace:

        # 默认保持 fail-closed，避免覆盖用户安装。
        raise SystemExit(
            "> ERR: [Python] destination already exists; explicit replace confirmation is required"
        )

    # replace 选项仍需要 --yes 或交互确认。
    if bool_destination_exists and object_arguments.replace and not object_arguments.yes:

        # 交互确认只影响已存在目标，不改变路径事实。
        try:

            # 任何非肯定回答都保持原目标不变。
            str_replace_answer: str = input(  # 替换确认回答。
                "Destination exists. Replace it? [y/N] "  # 只读取人工确认，不解释为路径。
            ).strip()

        # 非交互环境不能隐式获得覆盖权限。
        except EOFError as object_error:

            # 将缺少确认转换为稳定失败。
            raise SystemExit(
                "> ERR: [Python] replace confirmation was not granted"
            ) from object_error

        # 只有明确肯定的回答才能继续替换。
        if str_replace_answer.lower() not in {"y", "yes"}:

            # 拒绝任何模糊或空回答。
            raise SystemExit(
                "> ERR: [Python] replace confirmation was not granted"
            )

    # 将目标事实集中成不可变对象，防止调用者丢失 containment 状态。
    return {
        "path_boundary": path_boundary,  # 目标路径的 containment 根。
        "path_platform_home": path_platform_home,  # 已确认的平台安装根。
        "path_destination": path_destination,  # 已确认的最终目标目录。
        "bool_destination_exists": bool_destination_exists,  # 事务开始时的目标状态。
    }

# 交互确认和 dry-run 只读阶段。
def _confirm_guided_write(
    object_arguments: argparse.Namespace,
    dict_platform: dict[str, str],
    path_destination: Path,
    str_source_manifest_hash: str,
) -> None:
    """输出 guided 预览并确认是否允许真实写入。

    参数:
        object_arguments: guided CLI 参数对象。
        dict_platform: 已验证的平台记录。
        path_destination: 已通过 containment 的目标路径。
        str_source_manifest_hash: 源树清单摘要。
    返回:
        无；dry-run 正常返回，真实写入前完成用户确认。
    异常:
        SystemExit: 非交互或用户拒绝真实安装。
    """

    # 预览输出只报告已验证的平台、目标和源身份。
    str_platform_display_name: str = str(dict_platform["display_name"])  # 平台展示名称。

    # 把 Path 转为不会触发结构化输出门禁的展示文本。
    str_destination_display: str = str(path_destination)  # 目标路径的人类可读文本。

    # 输出不包含完整结构化载荷的安装预览摘要。
    print(f"> INFO: [Python] Platform: {str_platform_display_name}; destination: {str_destination_display}")

    # 源清单只输出摘要，完整清单留在收据和文件边界内。
    print(f"> INFO: [Python] Source manifest: {str_source_manifest_hash}")

    # dry-run 必须在任何目录或锁文件创建前结束。
    if object_arguments.dry_run:

        # 明确报告本次没有写入副作用。
        print("> INFO: [Python] Dry-run complete; no files were written")

        # 返回调用者，保持源和目标只读。
        return

    # 缺少 --yes 时需要一次明确的安装确认。
    if not object_arguments.yes:

        # 交互确认不能把用户输入直接解释为路径。
        try:

            # 只有肯定回答允许进入复制事务。
            str_install_answer: str = input(  # 安装确认回答。
                "Proceed with installation? [y/N] "  # 肯定回答才允许进入写入事务。
            ).strip()

        # 非交互环境没有确认即终止。
        except EOFError as object_error:

            # 不把 EOF 当作默认同意。
            raise SystemExit(
                "> ERR: [Python] installation confirmation was not granted"
            ) from object_error

        # 非肯定回答保持零副作用。
        if str_install_answer.lower() not in {"y", "yes"}:

            # 拒绝模糊回答，避免意外安装。
            raise SystemExit(
                "> ERR: [Python] installation confirmation was not granted"
            )

# 事务模块提供兼容的复制、恢复和成功 receipt 入口。
from guided_install_transaction import _acquire_lock
from guided_install_transaction import _build_success_receipt
from guided_install_transaction import _copy_to_destination
from guided_install_transaction import _manifest_hash
from guided_install_transaction import _recover_copy_failure
from guided_install_transaction import _transaction_paths
from guided_install_transaction import _write_recovery_receipt
from guided_install_transaction import _write_success_receipt

# 执行 Skill-only guided 安装或只读 dry-run。
def guided_install(object_arguments: argparse.Namespace) -> None:
    """执行 manifest 驱动的 guided bundle 安装流程。

    参数:
        object_arguments: build_argument_parser 解析出的 guided 参数。
    返回:
        无；成功通过标准输出报告，失败抛出 SystemExit。
    异常:
        SystemExit: 输入、确认、复制或恢复事务失败。
    """

    # 统一 bundle 根并加载所有源绑定事实。
    path_bundle: Path = Path(str(object_arguments.bundle_root)).expanduser().resolve()  # guided bundle 的可信根目录。

    # 读取 manifest、catalog 和平台摘要的验证结果。
    dict_guided_inputs: dict[str, Any] = _load_guided_inputs(  # 后续流程唯一的 bundle 输入事实。
        object_arguments,  # 当前 guided CLI 参数。
        path_bundle,  # guided runtime 读取 manifest projection 的 bundle 边界。
    )

    # 将验证结果拆出为带类型的局部事实。
    dict_manifest: dict[str, str] = dict_guided_inputs["dict_manifest"]  # 后续事务使用的 manifest。

    # Skill 根决定 dist provenance 和源树身份。
    path_skill_root: Path = dict_guided_inputs["path_skill_root"]  # 已验证发布包中的 Skill 根。

    # 平台菜单只来自 projection 验证结果。
    list_platforms: list[dict[str, str]] = dict_guided_inputs["list_platforms"]  # 可供用户选择的平台行。

    # 复用 manifest 适用性门禁后的项目类型。
    str_project_kind: str = dict_guided_inputs["str_project_kind"]  # 已确认的项目治理类型。

    # 保留两个配置摘要供最终成功 receipt 绑定。
    str_catalog_hash: str = dict_guided_inputs["str_catalog_hash"]  # catalog 原始字节指纹。

    # projection 摘要绑定用户看到的平台菜单。
    str_projection_hash: str = dict_guided_inputs["str_projection_hash"]  # 已绑定平台菜单的 projection 字节指纹。

    # 从 projection 平台事实中选择唯一安装配置。
    dict_platform: dict[str, str] = _select_platform(  # 用户选定的平台配置。
        object_arguments,  # 平台 ID 或交互菜单来源。
        list_platforms,  # 已通过 schema 的平台集合。
    )

    # 准备通过收据验证的 Skill 源树。
    dict_source_facts: dict[str, Any] = _prepare_source(  # dist 源目录和清单摘要。
        object_arguments,  # 显式源码覆盖和 CLI 门禁参数。
        path_skill_root,  # 通过发布验证的 Skill 根。
    )

    # 解析目标路径并检查替换意图，不创建文件。
    dict_destination_facts: dict[str, Any] = _resolve_destination(  # 解析用户根、技能目录和初始存在状态。
        object_arguments,  # 传入目标根、替换许可和确认开关。
        dict_platform,  # 从平台投影读取安装目录字段。
        dict_source_facts["str_skill_name"],  # 通过安全叶节点校验的技能名。
        dict_source_facts["path_source"],  # 版本化发布源的 containment 根。
    )

    # 预览和最终确认都发生在锁与复制之前。
    _confirm_guided_write(
        object_arguments,  # 输入确认开关和只读模式。
        dict_platform,  # 平台展示摘要来源。
        dict_destination_facts["path_destination"],  # 已通过 containment 的目标。
        dict_source_facts["str_source_manifest_hash"],  # 源树身份摘要。
    )

    # dry-run 的确认助手已经输出预览，后续事务必须完全跳过。
    if object_arguments.dry_run:

        # 只读模式不能创建锁、暂存目录或任何安装副本。
        return

    # dry-run 在确认助手内已经完成，真实流程从事务路径开始。
    dict_transaction_paths: dict[str, Any] = _transaction_paths(  # 检查同一设备上的 staging、备份、锁和隔离目录。
        dict_destination_facts["path_boundary"],  # 外部路径必须限制在这个 containment 根。
        dict_destination_facts["path_platform_home"],  # platform projection 解析出的用户安装根。
        dict_platform,  # skill_install_dir 的平台投影来源。
        dict_manifest,  # 事务前缀、锁名和隔离名的 manifest 来源。
        dict_source_facts["str_skill_name"],  # 安全技能名提供目标路径末段。
    )

    # 锁文件绑定本轮源身份并阻断并发安装。
    _acquire_lock(dict_transaction_paths["path_lock"], dict_source_facts["str_source_manifest_hash"])

    # 预先声明复制结果，异常分支可区分首次安装和替换安装。
    dict_copy_result: dict[str, Any] | None = None  # 复制成功后填入四项事务事实。

    # 复制调用的异常边界从这里开始。
    try:

        # 备份旧目标、复制 staging 并验证 final 目标。
        dict_copy_context: dict[str, Any] = {  # 复制事务输入上下文。
        "path_source": dict_source_facts["path_source"],  # dist provenance 绑定的复制源。
            "path_destination": dict_destination_facts["path_destination"],  # 正式安装目标。
        "path_install_parent": dict_transaction_paths["path_install_parent"],  # 一层受管父目录。
            "path_staging": dict_transaction_paths["path_staging"],  # 本轮 staging 路径。
            "path_backup_root": dict_transaction_paths["path_backup_root"],  # 替换事务备份根。
            "str_skill_name": dict_source_facts["str_skill_name"],  # 安全技能名。
            "bool_destination_exists": dict_destination_facts["bool_destination_exists"],  # 初始目标状态。
            "list_source_manifest": dict_source_facts["list_source_manifest"],  # 源树清单。
        }

        # 使用完整上下文执行 staging 复制和正式切换。
        dict_copy_result = _copy_to_destination(dict_copy_context)  # 复制事务结果。

    # 复制、staging 或 final 复核失败时恢复旧状态。
    except Exception as object_error:

        # 恢复器负责隔离失败副本、恢复旧目标和处理锁。
        dict_recovery_context: dict[str, Any] = {  # 汇总原始异常、隔离边界和三阶段摘要。
            "object_error": object_error,  # 复制阶段原始异常。
            "path_boundary": dict_destination_facts["path_boundary"],  # 失败副本 containment 根。
            "path_staging": dict_transaction_paths["path_staging"],  # 可能遗留的 staging 副本。
            "path_destination": dict_destination_facts["path_destination"],  # 目标目录的失败恢复锚点。
            "path_backup_target": dict_copy_result["path_backup_target"] if dict_copy_result else None,  # 替换前旧目标的可选备份。
            "bool_destination_backed_up": dict_copy_result["bool_destination_backed_up"] if dict_copy_result else False,  # 恢复时是否已有旧目标备份。
            "path_quarantine_root": dict_transaction_paths["path_quarantine_root"],  # 失败副本的受管隔离目录。
            "path_lock": dict_transaction_paths["path_lock"],  # 必须保留的事务锁。
            "str_source_manifest_hash": dict_source_facts["str_source_manifest_hash"],  # 恢复收据要绑定的源指纹。
            "str_staging_manifest_hash": dict_copy_result["str_staging_manifest_hash"] if dict_copy_result else "",  # 恢复收据使用的 staging 现场指纹。
            "str_final_manifest_hash": dict_copy_result["str_final_manifest_hash"] if dict_copy_result else "",  # 正式目标观测指纹。
            "str_recovery_suffix": dict_manifest["RECOVERY_RECEIPT_SUFFIX"],  # 恢复收据后缀。
        }

        # 以失败上下文执行隔离、恢复和收据写入。
        _recover_copy_failure(dict_recovery_context)

    # 身份文件复核通过后写入最终安装收据并释放锁。
    dict_success_context: dict[str, Any] = {  # 为成功 receipt 绑定目标路径、平台身份和三阶段清单指纹。
        "path_destination": dict_destination_facts["path_destination"],  # 目标目录供成功 receipt 写入。
        "dict_manifest": dict_manifest,  # receipt 使用的 bundle 摘要和恢复后缀来源。
        "dict_platform": dict_platform,  # receipt 使用的动态平台身份来源。
        "str_skill_name": dict_source_facts["str_skill_name"],  # receipt 和目标目录共用的技能名。
        "str_projection_hash": str_projection_hash,  # 平台菜单绑定的 projection 字节指纹。
        "str_catalog_hash": str_catalog_hash,  # 注册平台集合绑定的 catalog 字节指纹。
        "str_project_kind": str_project_kind,  # receipt 记录的项目适用性门禁结果。
        "str_source_manifest_hash": dict_source_facts["str_source_manifest_hash"],  # receipt 的复制输入指纹。
        "str_staging_manifest_hash": dict_copy_result["str_staging_manifest_hash"],  # receipt 的 staging 观测指纹。
        "str_final_manifest_hash": dict_copy_result["str_final_manifest_hash"],  # 成功 receipt 记录切换后目录的最终完整性摘要。
        "list_source_manifest": dict_source_facts["list_source_manifest"],  # receipt 回放所需源树清单。
        "path_quarantine_root": dict_transaction_paths["path_quarantine_root"],  # receipt 失败后的隔离边界。
        "path_lock": dict_transaction_paths["path_lock"],  # 成功事务最后释放的锁文件。
    }

    # 以成功上下文写入安装 receipt 并释放锁。
    _write_success_receipt(dict_success_context)

    # 明确报告事务已完成且目标可见。
    print("> INFO: [Python] Installation completed successfully.")
