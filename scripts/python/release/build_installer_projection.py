"""按 manifest、catalog 和 overrides 生成哈希绑定的 installer projection。

标准输出协议：本模块遵循 machine-readable stdout protocol，仅输出一个 JSON 对象；
投影正文始终写入目标文件，不打印到终端。
"""

# 生成器只依赖标准库，便于随 Skill bundle 一起运行。
from __future__ import annotations

# CLI 参数、哈希、JSON、原子文件和路径处理均来自标准库。
import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

# 使用字节摘要绑定源文件和生成后的 projection。
def sha256_bytes(bytes_value: bytes) -> str:
    """返回输入字节的 SHA-256 摘要。

    参数:
        bytes_value: 待摘要的原始字节。
    返回:
        小写十六进制 SHA-256 字符串。
    """

    # 摘要值用于绑定 catalog、projection 和 manifest projection 文件。
    return hashlib.sha256(bytes_value).hexdigest()

# 读取 JSON 对象并在结构不符时给出字段级错误。
def read_json_object(path_file: Path, str_label: str) -> dict[str, Any]:
    """读取一个受管 JSON 对象。

    参数:
        path_file: JSON 文件路径。
        str_label: 错误信息使用的资源名称。
    返回:
        已确认根类型为 object 的 JSON 映射。
    异常:
        ValueError 表示文件缺失、JSON 损坏或根类型错误。
    """

    # 缺失资源不能被空对象替代，否则会掩盖 bundle 配置错误。
    if not path_file.is_file():

        # 返回稳定字段，便于 CLI 生成机器可读错误。
        raise ValueError(f"> ERR: [Python] {str_label} is missing: {path_file}")

    # 读取 JSON 正文并保留解析错误位置。
    try:

        # JSON 内容必须以 UTF-8 解码，禁止隐式平台编码。
        obj_value: object = json.loads(  # JSON 根对象的未验证解析结果。
            path_file.read_text(encoding="utf-8")  # 读取受管 JSON 正文。
        )

    # 将解析失败转换为资源级 ValueError。
    except json.JSONDecodeError as object_error:

        # 错误中保留资源标签和原始解析原因。
        raise ValueError(f"> ERR: [Python] {str_label} is invalid: {object_error}") from object_error

    # 调用方依赖字段查找，因此拒绝数组和标量根。
    if not isinstance(obj_value, dict):

        # 根类型错误必须阻断 projection 生成。
        raise ValueError(f"> ERR: [Python] {str_label} must be a JSON object: {path_file}")

    # 返回根类型已经确认的对象。
    return obj_value

# 将 manifest 相对路径解析到 bundle 内，并阻断目录逃逸。
def resolve_bundle_path(
    path_bundle: Path,
    path_allowed_root: Path,
    str_relative_path: str,
    str_label: str,
) -> Path:
    """返回允许根内的受管绝对路径。

    参数:
        path_bundle: bundle 根目录。
        path_allowed_root: 允许访问的项目根目录。
        str_relative_path: manifest 声明的相对路径。
        str_label: 错误信息使用的资源名称。
    返回:
        规范化且位于允许根内的绝对路径。
    异常:
        ValueError 表示路径逃逸允许根。
    """

    # 规范化允许根，保证 containment 比较不受当前目录影响。
    path_root: Path = path_allowed_root.resolve()  # containment 校验使用的绝对根。

    # 规范化目标，消除 .. 和符号链接前的相对表示。
    path_target: Path = (path_bundle / str_relative_path).resolve()  # manifest 资源的绝对目标。

    # 所有 bundle 资源都必须保持在允许根内。
    if not path_target.is_relative_to(path_root):

        # 拒绝目录逃逸，避免写入 bundle 外部文件。
        raise ValueError(f"> ERR: [Python] {str_label} escapes bundle root: {str_relative_path}")

    # 返回通过 containment 校验的目标。
    return path_target

# 把平台字段转成无换行、无制表符的单元格。
def cell_text(object_value: object, str_column: str) -> str:
    """校验并返回 projection 单元格文本。

    参数:
        object_value: 待序列化的平台字段值。
        str_column: 当前字段名。
    返回:
        不含控制字符的单元格文本。
    异常:
        ValueError 表示字段含控制字符或不安全路径。
    """

    # 列表字段使用逗号连接，保持 manifest projection 的稳定表示。
    if isinstance(object_value, list):

        # 逐项转成文本，避免列表元素类型影响 TSV 拼接。
        str_value: str = ",".join(str(item) for item in object_value)  # 列表字段的确定性文本。

    # 缺失字段在 projection 中使用空单元格。
    elif object_value is None:

        # None 不应输出 Python 字面量字符串。
        str_value = ""  # 缺失字段的空文本。

    # 标量字段使用其稳定字符串表示。
    else:

        # 保留 manifest/catalog 标量的可读文本。
        str_value = str(object_value)  # 标量字段的 projection 文本。

    # TSV 单元格不能含换行或制表符，否则会破坏记录边界。
    if any(str_character in str_value for str_character in ("\t", "\r", "\n")):

        # 控制字符会使非 Python installer 误读 projection。
        raise ValueError(
            f"> ERR: [Python] projection column contains a control character: {str_column}"
        )

    # 路径类字段必须保持相对且不能包含父目录跳转。
    if any(
        str_token in str_column.lower()
        for str_token in ("path", "dir", "subdir", "home")
    ):

        # 将路径字段转换为 Path 以统一检查绝对路径和父目录片段。
        path_value: Path = Path(str_value)  # 当前 projection 路径字段。

        # 路径字段逃逸会让 projection 指向 bundle 外部资源。
        if path_value.is_absolute() or ".." in path_value.parts:

            # 只允许 bundle 内的相对资源声明。
            raise ValueError(f"> ERR: [Python] projection path field is unsafe: {str_column}")

    # 返回已经完成控制字符和路径检查的文本。
    return str_value

# 根据 manifest 列集合构造确定性 TSV 正文。
def render_projection(
    dict_manifest: dict[str, Any],
    dict_catalog: dict[str, Any],
    dict_overrides: dict[str, Any],
    str_catalog_hash: str,
) -> bytes:
    """从配置对象生成 projection 字节。

    参数:
        dict_manifest: installer manifest 对象。
        dict_catalog: 平台 catalog 对象。
        dict_overrides: 平台覆盖对象。
        str_catalog_hash: catalog 原始字节摘要。
    返回:
        确定性 UTF-8 TSV projection。
    异常:
        ValueError 表示 manifest、catalog 或平台记录结构不合法。
    """

    # 读取 manifest 声明的列集合。
    list_columns = dict_manifest.get("projection_columns")  # projection 原始列列表。

    # 读取 catalog 平台映射。
    dict_catalog_platforms = dict_catalog.get("platforms")  # catalog 平台对象。

    # overrides 缺失时按空覆盖处理，保持 manifest 默认语义。
    dict_override_platforms = dict_overrides.get("platforms", {})  # 平台覆盖映射。

    # projection 必须有显式列集合。
    if not isinstance(list_columns, list) or not list_columns:

        # 缺失列集合时拒绝生成不可解析的 TSV。
        raise ValueError("> ERR: [Python] installer manifest projection_columns is missing")

    # catalog 必须提供至少一个平台对象。
    if not isinstance(dict_catalog_platforms, dict) or not dict_catalog_platforms:

        # 没有平台记录时 projection 无法驱动安装选择。
        raise ValueError("> ERR: [Python] platform catalog platforms is missing")

    # overrides 根必须是对象，即使其内容为空。
    if not isinstance(dict_override_platforms, dict):

        # 拒绝列表或标量覆盖伪造。
        raise ValueError("> ERR: [Python] installer platform overrides must be an object")

    # 规范化列名并拒绝重复列，避免行值错位。
    list_column_names: list[str] = [
        str(column)  # 当前列名的字符串形式。
        for column in list_columns  # 遍历 manifest 声明的列。
    ]

    # 重复列会让下游按列名读取时产生歧义。
    if len(set(list_column_names)) != len(list_column_names):

        # 保持 projection schema 的列集合唯一。
        raise ValueError("> ERR: [Python] installer manifest projection_columns contains duplicates")

    # 记录 projection 的运行时事实类别，类别顺序由 manifest 控制。
    dict_record_lines: dict[str, str] = {  # projection 头部事实记录映射。
        "META": f"# META schema_version={dict_manifest.get('schema_version')}",  # schema 版本事实。
        "SOURCE": (  # catalog 摘要和相对路径事实。
            f"# SOURCE catalog_sha256={str_catalog_hash} "
            f"catalog_path={dict_manifest.get('catalog_relative_path')}"
        ),
        "RUNTIME": (  # runtime、shell 和 shell 工具事实。
            f"# RUNTIME backend={dict_manifest.get('backend_relative_path')} "
            f"runtime={dict_manifest.get('runtime_relative_path')} "
            f"shell={dict_manifest.get('shell_runtime')} "
            f"shell_utils={','.join(str(item) for item in dict_manifest.get('shell_utilities', []))}"
        ),
        "MENU": (  # 菜单来源和确认要求事实。
            f"# MENU selection_source={dict_manifest.get('menu', {}).get('selection_source')} "
            f"confirmation_required={dict_manifest.get('menu', {}).get('confirmation_required')}"
        ),
        "TRANSACTION": (  # 事务锁和失败证据事实。
            f"# TRANSACTION lock_required={dict_manifest.get('transaction', {}).get('lock_required')} "
            f"same_volume_required={dict_manifest.get('transaction', {}).get('same_volume_required')} "
            f"preserve_failure_evidence={dict_manifest.get('transaction', {}).get('preserve_failure_evidence')}"
        ),
        "OUTPUT": (  # 输出格式和 stdout 协议事实。
            f"# OUTPUT format={dict_manifest.get('output', {}).get('format')} "
            f"stdout={dict_manifest.get('output', {}).get('stdout')}"
        ),
        "BATCH_ENTRY": f"# BATCH_ENTRY value={dict_manifest.get('batch_entry')}",  # batch 入口事实。
        "PLATFORM": f"# PLATFORM_COUNT value={len(dict_catalog_platforms)}",  # 平台数量事实。
    }

    # 读取 manifest 声明的事实记录类别顺序。
    list_record_classes: list[str] = [
        str(item)  # 当前记录类别的规范文本。
        for item in dict_manifest.get("projection_record_classes", [])  # 遍历 manifest 类别。
    ]

    # 每个类别都必须在记录映射中有对应头部。
    if not list_record_classes or any(
        str_record not in dict_record_lines
        for str_record in list_record_classes
    ):

        # 拒绝缺失或未知的 projection 事实类别。
        raise ValueError("> ERR: [Python] installer manifest projection_record_classes is invalid")

    # 先写入 manifest 控制的事实头和列名。
    list_lines: list[str] = [
        dict_record_lines[str_record]  # 当前类别的事实行。
        for str_record in list_record_classes  # 保持 manifest 声明的类别顺序。
    ]

    # 追加 schema 和 catalog 摘要，再追加 TSV 表头。
    list_lines.extend(
        [
            f"# schema_version={dict_manifest.get('schema_version')}",  # schema 版本摘要行。
            f"# catalog_sha256={str_catalog_hash}",  # catalog 摘要行。
            "\t".join(list_column_names),  # projection TSV 表头。
        ]
    )

    # 平台行按平台 ID 排序，确保相同输入得到相同字节。
    for str_platform_id in sorted(dict_catalog_platforms):

        # 读取当前平台的 catalog 记录。
        dict_profile = dict_catalog_platforms[str_platform_id]  # 当前平台 profile。

        # 读取当前平台的可选覆盖记录。
        dict_override = dict_override_platforms.get(str_platform_id, {})  # 当前平台覆盖字段的原始映射。

        # catalog 和 override 记录都必须保持对象根。
        if not isinstance(dict_profile, dict) or not isinstance(dict_override, dict):

            # 拒绝无法合并的标量或列表平台记录。
            raise ValueError(f"> ERR: [Python] platform profile is not an object: {str_platform_id}")

        # 复制 catalog 记录，避免修改输入对象。
        dict_row: dict[str, Any] = dict(dict_profile)  # 当前平台的 projection 行副本。

        # override 字段覆盖 catalog 同名字段。
        dict_row.update(dict_override)

        # platform_id 必须写成 catalog 排序使用的 canonical ID。
        dict_row["platform_id"] = str_platform_id  # 当前行的稳定平台键。

        # 缺失 display_name 时使用平台 ID，保证表头字段非空。
        dict_row.setdefault("display_name", str_platform_id)  # 当前行的显示名称。

        # 写入平台事实行，供非 Python installer 读取。
        list_lines.append(
            "# PLATFORM "
            f"platform_id={cell_text(str_platform_id, 'platform_id')} "
            f"display_name={cell_text(dict_row.get('display_name'), 'display_name')}"
        )

        # 写入与表头完全对齐的 TSV 平台数据行。
        list_lines.append(
            "\t".join(
                cell_text(dict_row.get(str_column), str_column)  # 当前列的安全文本。
                for str_column in list_column_names  # 按固定表头顺序写入。
            )
        )

    # 返回带末尾换行的确定性 UTF-8 projection。
    return ("\n".join(list_lines) + "\n").encode("utf-8")

# 根据 projection schema 校验所有结构化记录类别和表头列。
def validate_projection_records(
    bytes_projection: bytes,
    path_schema: Path,
    list_columns: list[str],
) -> None:
    """验证 projection 的记录类别和必需列。

    参数:
        bytes_projection: 待验证的 projection 字节。
        path_schema: projection schema JSON 路径。
        list_columns: manifest 声明的列名列表。
    返回:
        无；验证失败时抛出 ValueError。
    异常:
        ValueError 表示 schema 缺失、类别缺失或列缺失。
    """

    # 读取 schema 根对象及其类别、列约束。
    dict_schema = read_json_object(path_schema, "projection schema")  # 后续校验使用的 schema JSON。

    # 读取 schema.properties 后，两个 const 才能约束 projection 类别与表头。
    obj_schema_properties: object = dict_schema.get("properties", {})  # schema properties 配置快照。

    # 读取 record_classes 的 const 声明。
    dict_record_schema = (  # record_classes 的 schema 对象。
        obj_schema_properties.get("record_classes", {})  # 从 properties 选择类别分支。
        if isinstance(obj_schema_properties, dict)  # 只从对象 properties 读取。
        else {}  # 缺失 properties 时交由后续类型门禁阻断。
    )

    # 读取 required_columns 分支的 const 声明。
    dict_column_schema = (  # required_columns 分支的 schema 节点。
        obj_schema_properties.get("required_columns", {})  # 读取必需列约束节点。
        if isinstance(obj_schema_properties, dict)  # properties 为对象时才读取列约束。
        else {}  # properties 类型错误时保留空节点并由后续门禁阻断。
    )

    # 提取记录类别列表。
    list_record_classes = (  # record_classes 节点声明的类别 const 列表。
        dict_record_schema.get("const")  # 从类别分支提取 const 列表。
        if isinstance(dict_record_schema, dict)  # 类别节点为对象时才读取 const。
        else None  # 类别节点类型错误时保留 None 并由后续门禁阻断。
    )

    # 提取必需列列表。
    list_required_columns = (  # required_columns 节点声明的列 const 列表。
        dict_column_schema.get("const")  # 读取必需列约束值。
        if isinstance(dict_column_schema, dict)  # 列节点为对象时才读取 const。
        else None  # 列节点类型错误时保留 None 并由后续门禁阻断。
    )

    # 将 projection 解码为文本以检查头部事实。
    str_projection = bytes_projection.decode("utf-8")  # 解码后的 projection 文本供类别检查。

    # schema 两个 const 字段都必须是列表。
    if not isinstance(list_record_classes, list) or not isinstance(list_required_columns, list):

        # 缺失 schema 约束时禁止声明验证成功。
        raise ValueError("> ERR: [Python] projection schema record_classes or required_columns is missing")

    # 收集 projection 中缺失的记录类别。
    list_missing_records: list[str] = [
        str_record  # 当前缺失的记录类别。
        for str_record in list_record_classes  # 遍历 schema 声明的类别。
        if f"# {str_record} " not in str_projection  # 只保留未出现的类别。
    ]

    # 每个 schema 类别都必须在 projection 中出现。
    if list_missing_records:

        # 一次性返回完整缺失类别列表。
        raise ValueError(
            "> ERR: [Python] projection record classes are missing: "
            + ", ".join(list_missing_records)
        )

    # 收集 projection 中缺失的表头列。
    list_missing_columns: list[str] = [
        str_column  # 当前缺失的表头列。
        for str_column in list_required_columns  # 遍历 schema 必需列。
        if str_column not in list_columns  # 只保留 manifest 未提供的列。
    ]

    # 每个 schema 列都必须由 manifest 提供。
    if list_missing_columns:

        # 一次性返回完整缺失列列表。
        raise ValueError(
            "> ERR: [Python] projection columns are missing: "
            + ", ".join(list_missing_columns)
        )

# 使用同目录临时文件原子提交 projection 或 manifest/env 更新。
def atomic_write(path_file: Path, bytes_content: bytes) -> None:
    """原子写入一个 UTF-8 或 JSON 文件。

    参数:
        path_file: 目标文件路径。
        bytes_content: 要写入的完整字节。
    返回:
        无。
    异常:
        OSError 表示临时文件或替换操作失败。
    """

    # 目标父目录必须存在，临时文件才可保持同卷替换。
    path_file.parent.mkdir(parents=True, exist_ok=True)

    # 同目录临时文件保证 os.replace 具备原子替换条件。
    int_handle, str_temp_name = tempfile.mkstemp(  # 创建同目录临时文件。
        prefix=f"{path_file.name}.",  # 临时文件名前缀。
        suffix=".tmp",  # 临时文件后缀。
        dir=path_file.parent,  # 与目标使用同一目录和卷。
    )

    # 关闭 mkstemp 返回的底层句柄，后续使用 Path 写入。
    os.close(int_handle)

    # 把临时名称转换为 Path 以复用路径 API。
    path_temp: Path = Path(str_temp_name)  # 当前原子写临时路径。

    # 先写完整内容，再替换目标文件。
    try:

        # 临时文件写入成功后才进入替换阶段。
        path_temp.write_bytes(bytes_content)

        # 同目录替换避免目标文件出现半写状态。
        os.replace(path_temp, path_file)

    # 失败时删除临时文件并原样抛出系统错误。
    except OSError:

        # 保留目标文件旧内容，同时清理未完成的临时文件。
        path_temp.unlink(missing_ok=True)

        # 让 CLI 将原子写失败转换为机器可读错误。
        raise

# 从 manifest 的点分隔字段路径读取一个 env projection 值。
def manifest_projection_value(
    dict_manifest: dict[str, Any],
    str_source_path: str,
) -> object:
    """读取 env projection 声明的字段路径。

    参数:
        dict_manifest: installer manifest 对象。
        str_source_path: 点分隔字段路径。
    返回:
        路径指向的原始 manifest 值。
    异常:
        ValueError 表示路径段缺失或中间值不是对象。
    """

    # 从 manifest 根开始逐段解析声明路径。
    obj_value: object = dict_manifest  # 当前路径解析对象。

    # 每个字段段都必须存在于当前对象中。
    for str_segment in str_source_path.split("."):

        # 中间节点必须是对象且包含当前字段。
        if not isinstance(obj_value, dict) or str_segment not in obj_value:

            # 缺失路径不能用空值替代，否则 env 会产生错误事实。
            raise ValueError(
                f"> ERR: [Python] manifest env projection source is missing: {str_source_path}"
            )

        # 进入下一层对象继续解析。
        obj_value = obj_value[str_segment]  # 进入当前路径段指向的下一级对象。

    # 返回路径声明的原始值，交由调用方序列化。
    return obj_value

# 更新 env 中由 manifest 投影出的字段，不改变 manifest 声明的键顺序。
def update_manifest_env(
    path_env: Path,
    dict_manifest: dict[str, Any],
    str_manifest_sha256: str,
    str_manifest_projection_sha256: str,
) -> None:
    """写回 manifest env 的哈希和入口字段。

    参数:
        path_env: manifest env 输出路径。
        dict_manifest: installer manifest 对象。
        str_manifest_sha256: 更新后 manifest 摘要。
        str_manifest_projection_sha256: manifest projection 摘要。
    返回:
        无。
    异常:
        ValueError 表示 env_projection 配置结构错误。
    """

    # 映射缺失或为空时，update_manifest_env 必须拒绝写入 env 文件。
    obj_env_projection: object = dict_manifest.get("env_projection")  # 每个 env 键的源路径映射。

    # env_projection 必须是非空对象。
    if not isinstance(obj_env_projection, dict) or not obj_env_projection:

        # 缺失声明时拒绝写入不完整的 env 文件。
        raise ValueError("> ERR: [Python] installer manifest env_projection is missing")

    # 维持 manifest 声明顺序收集 env 值。
    dict_env_values: dict[str, object] = {}  # env 输出键和值的有序映射。

    # 按 manifest 声明顺序解析每一个 env 字段。
    for str_env_key, object_source_path in obj_env_projection.items():

        # env key 和 source path 都必须是字符串。
        if not isinstance(str_env_key, str) or not isinstance(object_source_path, str):

            # 拒绝不能稳定写入文本的映射。
            raise ValueError("> ERR: [Python] installer manifest env_projection contains an invalid mapping")

        # 读取 source path 指向的 manifest 值。
        obj_value = manifest_projection_value(dict_manifest, object_source_path)  # 当前 env 字段原始值。

        # 列表值使用逗号连接，与 projection 表示保持一致。
        if isinstance(obj_value, list):

            # 将列表元素转换为稳定文本。
            obj_value = ",".join(  # 将 env 列表压成单行字段。
                str(item)  # 当前待序列化的列表成员。
                for item in obj_value  # 遍历 env_projection 源值。
            )

        # 保存当前 env 字段，等待追加哈希字段。
        dict_env_values[str_env_key] = obj_value  # 保存当前 env 输出值。

    # 写入更新后 manifest 摘要，作为 env 事实绑定。
    dict_env_values["MANIFEST_SHA256"] = str_manifest_sha256  # 保存 manifest 摘要。

    # 写入 manifest projection 摘要，绑定派生 projection 事实。
    dict_env_values["MANIFEST_PROJECTION_SHA256"] = str_manifest_projection_sha256  # 保存派生 projection 摘要。

    # 按收集顺序生成 KEY=VALUE 行。
    list_lines: list[str] = [
        f"{str_key}={str(value) if value is not None else ''}"  # 当前 env 行文本。
        for str_key, value in dict_env_values.items()  # 遍历有序 env 映射。
    ]

    # 使用同目录原子写入提交 env 文件。
    atomic_write(path_env, ("\n".join(list_lines) + "\n").encode("utf-8"))

# 生成供非 Python 入口读取的 manifest env projection 事实表。
def render_manifest_projection(
    dict_manifest: dict[str, Any],
    str_manifest_sha256: str,
) -> bytes:
    """返回 JSON manifest 到 env 字段的确定性 TSV 投影。

    参数:
        dict_manifest: installer manifest 对象。
        str_manifest_sha256: manifest JSON 摘要。
    返回:
        UTF-8 编码的 env projection TSV。
    异常:
        ValueError 表示 env_projection 配置缺失或值含控制字符。
    """

    # 读取用于生成 TSV 头和值的 env_projection。
    obj_env_projection: object = dict_manifest.get("env_projection")  # render 阶段的源字段映射。

    # TSV 生成要求至少有一项 env 映射。
    if not isinstance(obj_env_projection, dict) or not obj_env_projection:

        # 缺失声明时拒绝生成不完整 projection。
        raise ValueError("> ERR: [Python] installer manifest env_projection is missing")

    # list_lines 先承载 schema/manifest 头部，随后追加 env 记录行。
    list_lines: list[str] = [  # 头部和 env 记录追加到此列表，join 后形成完整 TSV。
        f"# schema_version={dict_manifest.get('schema_version')}",  # projection schema_version 头部记录，供读取器确认格式。
        f"# manifest_json_sha256={str_manifest_sha256}",  # 供 env loader 校验来源的 manifest 摘要行。
        "env_key\tsource_path\texpected_value",  # TSV 数据列头。
    ]

    # 按 manifest env_projection 声明顺序写入值。
    for str_env_key, object_source_path in obj_env_projection.items():

        # render 当前 env 键的 source path 值。
        obj_value = manifest_projection_value(  # 作为 TSV expected_value 的原始输入。
            dict_manifest,  # 从 manifest 根查找字段。
            str(object_source_path),  # 当前 env 键的点分隔路径。
        )

        # 列表值与 env 文件使用同一逗号表示。
        if isinstance(obj_value, list):

            # 将列表元素转换为 render 所需的单行文本。
            obj_value = ",".join(  # 当前 TSV expected_value 的列表表示。
                str(item)  # 当前待转换的列表成员。
                for item in obj_value  # 遍历 render 源列表。
            )

        # 将最终值转换为 TSV 单元格文本。
        str_value = str(obj_value)  # 当前 env projection 期望值。

        # TSV 值不能含控制字符，否则会破坏行边界。
        if any(str_character in str_value for str_character in ("\t", "\r", "\n")):

            # 拒绝不可解析的 manifest projection 值。
            raise ValueError(
                f"> ERR: [Python] manifest projection value contains a control character: {str_env_key}"
            )

        # 追加 env key、source path 和期望值三列。
        list_lines.append(
            f"{str_env_key}\t{object_source_path}\t{str_value}"
        )

    # 返回确定性 UTF-8 projection 正文。
    return ("\n".join(list_lines) + "\n").encode("utf-8")

# 解析 projection 工作流使用的全部 bundle 路径并执行 containment 检查。
def _resolve_projection_paths(
    path_bundle: Path,
    path_skill_root: Path,
    dict_manifest: dict[str, Any],
) -> dict[str, Path]:
    """解析 manifest 声明的 projection 输入输出路径。

    参数:
        path_bundle: 已规范化的 installer bundle 根目录。
        path_skill_root: 已规范化的 Skill 根目录。
        dict_manifest: installer manifest 对象。
    返回:
        资源名称到受管绝对路径的映射。
    异常:
        ValueError 表示输出路径逃逸 bundle 根。
    """

    # catalog 路径只从 manifest 声明解析，禁止调用方拼接外部路径。
    dict_paths: dict[str, Path] = {}  # projection 输入输出路径映射。

    # catalog 键缺失或逃逸时，read_json_object 不能安全读取平台 catalog。
    dict_paths["catalog"] = resolve_bundle_path(  # 解析 catalog 相对路径，逃逸时立即阻断读取。
        path_bundle,  # 由 bundle 根提供 catalog containment 起点。
        path_skill_root,  # catalog 的第二层项目边界。
        str(dict_manifest["catalog_relative_path"]),  # catalog 源文件的相对声明，供 containment 解析。
        "catalog",  # catalog 读取失败的诊断上下文。
    )

    # overrides 路径与 catalog 使用同一 containment 根。
    dict_paths["overrides"] = resolve_bundle_path(  # render_projection 合并的平台覆盖必须先完成 containment。
        path_bundle,  # overrides 解析从其资源目录开始。
        path_skill_root,  # 项目根限制 overrides 的可见范围。
        str(dict_manifest["overrides_relative_path"]),  # overrides 的相对源文件声明。
        "overrides",  # overrides 合并失败的诊断上下文。
    )

    # projection 输出路径由 manifest 控制并绑定到 bundle。
    dict_paths["projection"] = resolve_bundle_path(  # 生成 TSV 的写入目标必须先完成 containment。
        path_bundle,  # projection 输出先固定在 bundle 目录。
        path_skill_root,  # Skill 根阻止 projection 跨项目。
        str(dict_manifest["projection_relative_path"]),  # projection 输出的相对目标声明。
        "projection",  # TSV 输出失败的诊断上下文。
    )

    # schema 路径必须与 projection 输入保持同一受管根。
    dict_paths["projection_schema"] = resolve_bundle_path(  # 结构校验 schema 不能从 bundle 外部读取。
        path_bundle,  # schema 读取先锚定在受管 bundle。
        path_skill_root,  # schema 不能越过 Skill 项目根。
        str(dict_manifest["projection_schema_relative_path"]),  # schema 校验文件的相对声明。
        "projection schema",  # schema 校验失败的诊断上下文。
    )

    # manifest projection 是派生输出，仍需通过统一路径解析。
    dict_paths["manifest_projection"] = resolve_bundle_path(  # 派生 env 事实表的写入目标必须受 containment 保护。
        path_bundle,  # 派生文件先绑定 bundle 目录。
        path_skill_root,  # 派生文件共享 Skill 项目根限制。
        str(dict_manifest["manifest_projection_relative_path"]),  # manifest 派生文件字段。
        "manifest projection",  # 派生 projection 写入失败的诊断上下文。
    )

    # 派生 manifest projection 必须位于 bundle 内。
    if not dict_paths["manifest_projection"].is_relative_to(path_bundle):

        # 拒绝 manifest projection 跨出 installer bundle。
        raise ValueError("> ERR: [Python] manifest projection escapes installer bundle")

    # manifest env 也通过同一 containment 解析。
    dict_paths["env"] = resolve_bundle_path(  # KEY=VALUE 文件的写入目标必须受 containment 保护。
        path_bundle,  # env 文件以 bundle 目录作为第一边界。
        path_skill_root,  # env 写入继承 Skill 项目根限制。
        str(dict_manifest["manifest_env_relative_path"]),  # manifest env 输出字段。
        "manifest env",  # KEY=VALUE 写入失败的诊断上下文。
    )

    # env 输出必须位于 bundle 内，不能覆盖外部文件。
    if not dict_paths["env"].is_relative_to(path_bundle):

        # 拒绝 KEY=VALUE env 文件跨出 installer bundle。
        raise ValueError("> ERR: [Python] manifest env escapes installer bundle")

    # 返回已经完成 containment 检查的路径映射。
    return dict_paths

# 执行一次生成或只读预览，并输出唯一机器对象。
def run_projection(namespace_namespace: argparse.Namespace) -> dict[str, object]:
    """执行 projection 生成工作流。

    参数:
        namespace_namespace: 已解析的 CLI 参数对象。
    返回:
        生成或预览结果的机器对象。
    异常:
        OSError、TypeError、ValueError 或 KeyError 表示输入或写入失败。
    """

    # 规范化当前 Skill 根目录。
    path_skill_root: Path = Path(namespace_namespace.skill_root).expanduser().resolve()  # 绑定本次 CLI 的 Skill bundle 根。

    # manifest 参数缺失时使用 Skill 内配置的默认 manifest。
    path_manifest: Path = (  # 当前调用绑定的 installer manifest 路径。
        Path(namespace_namespace.manifest).expanduser().resolve()  # 使用显式 manifest 参数。
        if namespace_namespace.manifest  # 显式参数存在时优先使用。
        else path_skill_root / "config" / "installer" / "installer.manifest.json"  # 使用 bundle 默认 manifest。
    )

    # 读取并确认 installer manifest 根对象。
    dict_manifest = read_json_object(path_manifest, "installer manifest")  # 本次 projection 的路径、列和 env 合同。

    # project kind 必须与 manifest 允许值精确匹配。
    str_project_kind = namespace_namespace.project_kind.strip()  # CLI 声明的项目类型。

    # 不允许在不适用的项目根生成 installer projection。
    if str_project_kind != str(dict_manifest.get("allowed_project_kind", "")).strip():

        # project kind 不匹配时 fail-closed。
        raise ValueError("> ERR: [Python] project kind is not eligible for projection generation")

    # bundle 根由 manifest 声明并绑定到 Skill 根。
    path_bundle: Path = (  # manifest 声明的 installer bundle 绝对根。
        path_skill_root / str(dict_manifest["bundle_root_relative"])  # 将相对 bundle 根绑定到 Skill 根。
    ).resolve()

    # 解析并复用所有已经通过 containment 的 bundle 路径。
    dict_projection_paths = _resolve_projection_paths(  # projection 资源路径映射。
        path_bundle,  # 已规范化的 bundle 根。
        path_skill_root,  # helper 使用的 Skill containment 边界。
        dict_manifest,  # 声明全部 projection 相对路径的 manifest。
    )

    # 提取受管输入输出路径，后续不再重新拼接路径；catalog 用于读取平台 profile。
    path_catalog: Path = dict_projection_paths["catalog"]  # render_projection 使用的 catalog profile 源。

    # overrides 用于覆盖 catalog 字段。
    path_overrides: Path = dict_projection_paths["overrides"]  # render_projection 合并的 override 源。

    # projection 用于写入确定性 TSV 行。
    path_projection: Path = dict_projection_paths["projection"]  # 生成 TSV 字节的落盘目标。

    # schema 用于校验记录类别和表头。
    path_projection_schema: Path = dict_projection_paths["projection_schema"]  # 提供 record_classes 和 required_columns 约束。

    # 派生 projection 用于写入 env 字段事实。
    path_manifest_projection: Path = dict_projection_paths["manifest_projection"]  # env 字段事实表的落盘目标。

    # env 输出用于写入 KEY=VALUE 文件。
    path_env: Path = dict_projection_paths["env"]  # KEY=VALUE manifest env 的落盘目标。

    # 读取 catalog 原始字节并计算源摘要。
    bytes_catalog: bytes = path_catalog.read_bytes()  # catalog 原始字节。

    # SOURCE 事实行和 manifest 回写都使用同一 catalog 摘要。
    str_catalog_hash: str = sha256_bytes(bytes_catalog)  # catalog 字节摘要绑定。

    # 读取 catalog 和 overrides 对象。
    dict_catalog = read_json_object(path_catalog, "platform catalog")  # 供平台行排序和字段读取的 catalog。

    # 单独读取覆盖源，避免把 catalog 原始对象直接改写。
    dict_overrides = read_json_object(path_overrides, "platform overrides")  # 覆盖 catalog 字段的 overrides。

    # 生成确定性 projection 正文。
    bytes_projection = render_projection(  # 构造待验证的确定性 projection 字节。
        dict_manifest,  # 列、事实类别和输出字段配置。
        dict_catalog,  # 平台 profile 输入。
        dict_overrides,  # 平台覆盖输入。
        str_catalog_hash,  # SOURCE 事实绑定的 catalog 摘要。
    )

    # 用 schema 校验类别和表头，再计算 projection 摘要。
    validate_projection_records(
        bytes_projection,
        path_projection_schema,
        [
            str(column)  # manifest projection 列名。
            for column in dict_manifest.get("projection_columns", [])  # 遍历声明列。
        ],
    )

    # manifest 回写和结果对象共享同一 projection 摘要。
    str_projection_hash: str = sha256_bytes(bytes_projection)  # projection 输出字节绑定。

    # --write=false 只生成预览，不改变 bundle 文件。
    if str(namespace_namespace.write).lower() == "true":

        # 将本次 catalog 和 projection 摘要回写 manifest。
        dict_manifest["catalog_sha256"] = str_catalog_hash  # manifest 的 catalog 源摘要字段。

        # 保存 projection 输出摘要，供后续安装器校验。
        dict_manifest["projection_sha256"] = str_projection_hash  # manifest 的 projection 摘要字段。

        # 原子提交 projection 文件。
        atomic_write(path_projection, bytes_projection)

        # 原子提交带摘要的 manifest JSON。
        atomic_write(
            path_manifest,
            (json.dumps(dict_manifest, ensure_ascii=False, indent=2) + "\n").encode(
                "utf-8"
            ),
        )

        # 重新读取已写入 manifest，绑定真实落盘字节摘要。
        str_manifest_sha256: str = sha256_bytes(path_manifest.read_bytes())  # 落盘 manifest 摘要。

        # 生成并原子提交 manifest projection。
        bytes_manifest_projection = render_manifest_projection(  # 生成 env 字段事实表。
            dict_manifest,  # 已回写 catalog/projection 摘要的 manifest。
            str_manifest_sha256,  # 真实落盘 manifest 摘要。
        )

        # 原子提交 manifest projection，避免半写 TSV 被读取。
        atomic_write(path_manifest_projection, bytes_manifest_projection)

        # 计算派生 manifest projection 摘要并更新 env。
        str_manifest_projection_sha256: str = sha256_bytes(bytes_manifest_projection)  # env 事实表的落盘绑定摘要。

        # 使用两项摘要更新 manifest env 文件。
        update_manifest_env(
            path_env,
            dict_manifest,
            str_manifest_sha256,
            str_manifest_projection_sha256,
        )

    # dict_result 在 main 中成为唯一 JSON 输出载荷。
    dict_result: dict[str, object] = dict(  # 带回 write 标志、摘要和三个路径，main 依此生成 JSON。
        ok=True,  # 工作流已经完成。
        written=bool(namespace_namespace.write),  # 是否执行了原子写入。
        catalog_sha256=str_catalog_hash,  # catalog 原始字节的 SHA-256，回写 manifest 和结果。
        projection_sha256=str_projection_hash,  # projection 输出摘要。
        projection_path=str(path_projection),  # projection 目标路径。
        manifest_env_path=str(path_env),  # KEY=VALUE env 文件的目标路径。
        manifest_projection_path=str(path_manifest_projection),  # env projection TSV 的目标路径。
        platform_count=len(dict_catalog["platforms"]),  # catalog 平台数量。
    )

    # 返回机器对象，避免在核心逻辑中直接输出文本。
    return dict_result

# 构造参数并保持 stdout 为单对象 JSON 协议。
def main() -> int:
    """运行 projection CLI。

    参数：无。
    返回：成功为 0，受管输入或写入错误为 2。
    """

    # CLI parser 只声明 manifest projection 所需的四个输入。
    argument_parser = argparse.ArgumentParser(  # projection CLI 参数解析器。
        description="Generate a manifest-bound installer projection."  # CLI 用途说明。
    )

    # Skill 根是唯一必需的 bundle 定位参数。
    argument_parser.add_argument("--skill-root", required=True)

    # manifest 参数可选，缺省使用 bundle 内默认 manifest。
    argument_parser.add_argument("--manifest", default=None)

    # project kind 用于受管项目类型门禁。
    argument_parser.add_argument("--project-kind", required=True)

    # write 开关决定本次调用是否原子提交文件。
    argument_parser.add_argument("--write", action="store_true")

    # 解析 CLI 参数，之后所有输出进入统一错误协议。
    namespace_namespace: argparse.Namespace = argument_parser.parse_args()  # 解析后的 projection CLI 参数。

    # 生成路径和写入失败都必须保持单对象 JSON stdout。
    try:

        # 执行 projection 工作流。
        dict_result = run_projection(namespace_namespace)  # 生成或预览结果对象。

        # 正常 stdout 只输出机器可读 JSON，不夹带进度文本。
        print(json.dumps(dict_result, ensure_ascii=False, sort_keys=True))

        # 正常完成使用零退出码。
        return 0

    # 将受管输入、类型、路径和文件错误转换为错误 JSON。
    except (OSError, TypeError, ValueError, KeyError) as object_error:

        # 错误 stdout 仍保持一个 JSON 对象，供 bat/PowerShell/shell 解析。
        print(
            json.dumps(
                {"ok": False, "errors": [str(object_error)]},
                ensure_ascii=False,
            )
        )

        # CLI 调用方据此区分生成失败。
        return 2

# 直接执行时只通过 main 输出 machine-readable stdout protocol。
if __name__ == "__main__":

    # 将 main 的退出码交回宿主 shell。
    raise SystemExit(main())
