"""验证 installer env 与 JSON manifest 的完整绑定。"""

# manifest contract 只依赖标准库，便于随 Skill bundle 一起运行。
from __future__ import annotations

# manifest 绑定依赖哈希、JSON 和文件路径标准库。
import hashlib
import json
from pathlib import Path
from typing import Any

# 读取没有重复键的 JSON 对象。
def _read_json_object(path_file: Path, str_label: str) -> dict[str, Any]:
    """读取没有重复键的 JSON 对象。

    参数:
        path_file: JSON 文件路径。
        str_label: 错误信息使用的资源标签。
    返回:
        根类型已经确认的 JSON 映射。
    异常:
        ValueError 表示文件缺失、重复键、JSON 损坏或根类型错误。
    """

    # 解析 JSON 时保留重复键检测，避免后一个值静默覆盖前一个值。
    def reject_duplicate_pairs(
        list_pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        """拒绝同一 JSON 对象中的重复键。

        参数:
            list_pairs: JSON decoder 传入的键值对列表。
        返回:
            去重检查通过的对象映射。
        异常:
            ValueError 表示同一对象出现重复键。
        """

        # 逐项构造对象，保留 JSON 原始出现顺序。
        dict_result: dict[str, object] = {}  # 当前对象的键值映射。

        # 检查每个键是否已经被当前对象接受。
        for str_key, obj_value in list_pairs:

            # 重复键会改变 manifest 语义，必须立即阻断。
            if str_key in dict_result:

                # 错误中保留具体重复键，方便修复源文件。
                raise ValueError(
                    f"> ERR: [Python] {str_label} contains duplicate key: {str_key}"
                )

            # 保存未重复的键值对。
            dict_result[str_key] = obj_value  # 当前 JSON 字段的原始值。

        # 返回重复检查通过的对象。
        return dict_result

    # JSON 文件缺失时不能使用隐式空配置。
    if not path_file.is_file():

        # 返回带资源标签的可执行错误。
        raise ValueError(f"> ERR: [Python] {str_label} is missing: {path_file}")

    # 读取 JSON 并使用重复键钩子。
    obj_value: object = json.loads(  # JSON 根对象的未验证解析结果。
        path_file.read_text(encoding="utf-8"),  # 使用 UTF-8 读取正文。
        object_pairs_hook=reject_duplicate_pairs,  # 在 decoder 层拒绝重复键。
    )

    # manifest contract 依赖对象字段，不接受数组或标量根。
    if not isinstance(obj_value, dict):

        # 根类型错误必须阻断后续字段读取。
        raise ValueError(f"> ERR: [Python] {str_label} must be a JSON object")

    # 返回根类型已确认的对象。
    return obj_value

# 读取唯一键 env manifest，并拒绝重复键和非法键名。
def read_manifest_env(path_file: Path) -> dict[str, str]:
    """读取唯一键 env manifest，并拒绝重复键和非法键名。

    参数:
        path_file: KEY=VALUE env 文件路径。
    返回:
        env 键到文本值的映射。
    异常:
        ValueError 表示 env 行格式错误、键名非法或键重复。
    """

    # 保持文件行顺序，后续校验只依赖键集合和值。
    dict_values: dict[str, str] = {}  # 已读取的 env 键值映射。

    # 逐行解析 env manifest。
    for str_line in path_file.read_text(encoding="utf-8").splitlines():

        # 空行不代表 env 字段，允许在文件中出现。
        if not str_line.strip():

            # 跳过空行，继续检查后续键值。
            continue

        # 只在第一个等号处分隔键和值，保留值中的等号。
        str_key, str_separator, str_value = str_line.partition("=")  # 当前 env 行的三段文本。

        # env 键必须是大写标识符且必须带等号分隔。
        if not str_separator or not str_key.isupper():

            # 保留原始行，便于定位 env 合同错误。
            raise ValueError(
                f"> ERR: [Python] installer manifest contains an invalid line: {str_line}"
            )

        # 重复 env 键不能让后一个值静默覆盖前一个值。
        if str_key in dict_values:

            # 返回具体重复键，避免调用方猜测覆盖顺序。
            raise ValueError(
                f"> ERR: [Python] installer manifest contains duplicate key: {str_key}"
            )

        # 保存当前 env 键值。
        dict_values[str_key] = str_value  # 当前 env 的最终文本值。

    # 返回已经完成格式和重复键检查的 env 映射。
    return dict_values

# 按 manifest 声明的点分隔字段读取 projection 源值。
def _projection_value(
    dict_manifest: dict[str, Any],
    str_source_path: str,
) -> object:
    """按 manifest 声明的点分隔字段读取 projection 源值。

    参数:
        dict_manifest: JSON manifest 对象。
        str_source_path: 点分隔的源字段路径。
    返回:
        源字段原始值；列表会转换为逗号分隔文本。
    异常:
        ValueError 表示源字段路径缺失或中间节点不是对象。
    """

    # 从 manifest 根开始按路径段逐层读取。
    obj_value: object = dict_manifest  # 当前路径节点。

    # 每个路径段都必须在当前对象中存在。
    for str_segment in str_source_path.split("."):

        # 中间节点类型错误或字段缺失都不能生成 env 事实。
        if not isinstance(obj_value, dict) or str_segment not in obj_value:

            # 返回具体源路径，便于修复 manifest env_projection。
            raise ValueError(
                f"> ERR: [Python] manifest env projection source is missing: {str_source_path}"
            )

        # 进入下一级路径节点。
        obj_value = obj_value[str_segment]  # 当前路径段解析后的下一级值。

    # 列表值使用与生成器一致的逗号表示。
    if isinstance(obj_value, list):

        # 将列表元素转换为单行 env 文本。
        return ",".join(str(item) for item in obj_value)

    # 标量和对象值保持 manifest 原始类型。
    return obj_value

# 解析相对路径并确保结果位于给定根目录。
def _resolve_contained(
    path_root: Path,
    str_relative: str,
    str_label: str,
) -> Path:
    """解析相对路径并确保结果位于给定根目录。

    参数:
        path_root: containment 根目录。
        str_relative: manifest 声明的相对路径。
        str_label: 错误信息使用的资源标签。
    返回:
        根目录内的规范化绝对路径。
    异常:
        ValueError 表示路径为空、绝对化或逃逸 containment 根。
    """

    # 空路径和绝对路径都无法表达受管相对资源。
    if not str_relative or Path(str_relative).is_absolute():

        # 拒绝隐式使用当前目录或外部绝对路径。
        raise ValueError(
            f"> ERR: [Python] {str_label} must be a non-empty relative path"
        )

    # 规范化目标路径，消除 .. 和符号链接表示。
    path_target: Path = (path_root / str_relative).resolve()  # 当前资源的绝对候选路径。

    # 目标必须保持在声明的 containment 根内。
    if not path_target.is_relative_to(path_root):

        # 拒绝目录逃逸，避免 manifest 指向外部文件。
        raise ValueError(
            f"> ERR: [Python] {str_label} escapes its configured root: {str_relative}"
        )

    # 返回通过 containment 校验的资源路径。
    return path_target

# 校验 env 中声明的 projection 键和值绑定。
def _validate_projection_bindings(
    dict_env: dict[str, str],
    dict_projection: dict[str, object],
    dict_manifest: dict[str, Any],
) -> None:
    """校验 env projection 的声明键和逐项值。

    参数:
        dict_env: 已解析的 env 映射。
        dict_projection: manifest env_projection 映射。
        dict_manifest: JSON manifest 对象。
    返回:
        无；任一键或值不匹配时抛出 ValueError。
    异常:
        ValueError 表示 env 含未声明键、映射类型错误或值漂移。
    """

    # 允许键集合决定 env 是否能与 manifest projection 完成对账。
    set_allowed_env_keys: set[str] = {  # 这个集合用于阻断 env 中超出 manifest 白名单的键。
        str(item)  # manifest projection 白名单键。
        for item in dict_projection  # 从 projection 映射提取白名单。
    } | {"MANIFEST_SHA256", "MANIFEST_PROJECTION_SHA256"}

    # 收集 env 中未被 manifest 声明的键。
    list_unknown_env_keys: list[str] = sorted(  # env 中未声明键的稳定排序列表。
        set(dict_env) - set_allowed_env_keys  # 计算 env 与 manifest 白名单的差集。
    )

    # 未声明键会让 installer 读取到无法追溯的事实。
    if list_unknown_env_keys:

        # 一次性返回完整未知键列表。
        raise ValueError(
            "> ERR: [Python] manifest env contains undeclared keys: "
            + ", ".join(list_unknown_env_keys)
        )

    # 逐项确认 manifest projection 映射的源值与 env 相同。
    for str_env_key, obj_source_path in dict_projection.items():

        # 每个 mapping 的 key 和 source path 都必须是字符串。
        if not isinstance(str_env_key, str) or not isinstance(obj_source_path, str):

            # 拒绝无法稳定解释的 env_projection 映射。
            raise ValueError(
                "> ERR: [Python] installer JSON manifest env_projection contains an invalid mapping"
            )

        # 读取 manifest 源值并转换为 env 文本。
        str_expected_value = str(  # 当前 env 键应当写出的 manifest 文本。
            _projection_value(dict_manifest, obj_source_path)  # 读取 manifest 源字段。
        )

        # env 值漂移表示 manifest projection 已经失去绑定。
        if dict_env.get(str_env_key) != str_expected_value:

            # 返回具体漂移键，阻止安装继续。
            raise ValueError(
                f"> ERR: [Python] manifest env projection mismatch: {str_env_key}"
            )

# 校验 manifest projection 文件的摘要、表头和行值。
def _validate_manifest_projection_file(
    path_manifest_projection: Path,
    dict_env: dict[str, str],
    str_manifest_hash: str,
) -> None:
    """校验 manifest projection 文件与 env 的绑定。

    参数:
        path_manifest_projection: manifest projection TSV 路径。
        dict_env: 已解析的 env 映射。
        str_manifest_hash: env 声明的 manifest 摘要。
    返回:
        无；摘要、表头或行值错误时抛出 ValueError。
    异常:
        ValueError 表示 projection 文件不存在、摘要不匹配或记录重复。
    """

    # 读取 projection 原始字节并校验 env 声明的摘要。
    bytes_projection = path_manifest_projection.read_bytes()  # manifest projection 原始字节。

    # env 摘要校验使用真实 projection 文件字节。
    str_projection_hash = hashlib.sha256(bytes_projection).hexdigest()  # 用真实 projection 字节生成对账摘要。

    # env 摘要必须存在且与真实文件一致。
    str_expected_hash = dict_env.get("MANIFEST_PROJECTION_SHA256", "")  # env 声明的 projection 摘要。

    # 缺失或漂移摘要都应阻断安装。
    if not str_expected_hash or str_projection_hash != str_expected_hash:

        # 保留固定错误文本，便于 CLI 和安装器识别。
        raise ValueError(
            "> ERR: [Python] manifest projection SHA-256 does not match MANIFEST_PROJECTION_SHA256"
        )

    # 解码 projection 行，检查摘要头和数据行。
    list_projection_lines: list[str] = path_manifest_projection.read_text(  # 后续按行检查摘要头和三列表格。
        encoding="utf-8"  # 使用 UTF-8 读取 projection 文本。
    ).splitlines()

    # 第二行必须回指同一 manifest 摘要。
    if (
        len(list_projection_lines) < 3
        or list_projection_lines[1] != f"# manifest_json_sha256={str_manifest_hash}"
    ):

        # 摘要头漂移会断开 manifest 与 projection 绑定。
        raise ValueError("> ERR: [Python] manifest projection JSON digest binding is invalid")

    # 逐行检查三列结构和 env 值一致性。
    set_projection_keys: set[str] = set()  # 已确认的 projection env 键集合。

    # 跳过 schema、manifest 摘要和表头后的数据行。
    for str_projection_line in list_projection_lines[3:]:

        # 每行必须是 env_key、source_path、expected_value 三列。
        list_projection_fields: list[str] = str_projection_line.split("\t")  # 当前 projection 三列。

        # 重复键或列数错误都说明 projection 已损坏。
        if len(list_projection_fields) != 3 or list_projection_fields[0] in set_projection_keys:

            # 阻断重复行和非法行结构。
            raise ValueError("> ERR: [Python] manifest projection contains an invalid or duplicate row")

        # 保存当前键，供后续重复检查。
        set_projection_keys.add(list_projection_fields[0])  # 把已验证第一列加入重复检测集合。

        # projection 期望值必须与 env 最终值一致。
        if dict_env.get(list_projection_fields[0]) != list_projection_fields[2]:

            # 返回具体漂移键，便于定位生成链路错误。
            raise ValueError(
                f"> ERR: [Python] manifest projection value mismatch: {list_projection_fields[0]}"
            )

# 校验 env 中声明的相对路径 containment 规则。
def _validate_env_path_bindings(
    dict_env: dict[str, str],
    dict_manifest: dict[str, Any],
    path_skill_root: Path,
    path_bundle: Path,
) -> None:
    """校验 manifest env 的相对路径白名单和 containment。

    参数:
        dict_env: 已解析的 env 映射。
        dict_manifest: JSON manifest 对象。
        path_skill_root: manifest 声明的 Skill 根。
        path_bundle: installer bundle 根。
    返回:
        无；路径白名单或 containment 错误时抛出 ValueError。
    异常:
        ValueError 表示 env_path_bases 缺失、未声明或逃逸。
    """

    # env_path_bases 是所有相对路径字段的唯一白名单来源。
    dict_path_bases = dict_manifest.get("env_path_bases")  # manifest 路径分类配置。

    # 路径分类缺失时不能猜测 containment 根。
    if not isinstance(dict_path_bases, dict):

        # 阻断未声明路径规则的 env。
        raise ValueError("> ERR: [Python] installer JSON manifest env_path_bases is missing")

    # 读取 Skill root 路径白名单。
    set_skill_paths: set[str] = {  # Skill 根 containment 使用的 env 键集合。
        str(item)  # 当前 Skill 根键。
        for item in dict_path_bases.get("skill_root", [])  # 遍历 skill_root 配置。
    }

    # bundle_root 分类决定 bundle 路径是否受管。
    set_bundle_paths: set[str] = {  # bundle containment 使用的 env 键集合。
        str(item)  # bundle_root 白名单中的 env 键。
        for item in dict_path_bases.get("bundle_root", [])  # 从 bundle_root 配置提取键。
    }

    # bundle_local 分类决定是否收紧到 bundle 根。
    set_bundle_local_paths: set[str] = {  # 用于选择 bundle 根的本地路径键集合。
        str(item)  # bundle_local 白名单成员，选择更窄的 bundle 根。
        for item in dict_path_bases.get("bundle_local", [])  # 读取本地 containment 分类。
    }

    # source_root 分类允许其自身绑定直接通过。
    set_source_paths: set[str] = {  # 用于跳过二次解析的 source-root 键集合。
        str(item)  # source_root 白名单成员，跳过后续 bundle 解析。
        for item in dict_path_bases.get("source_root", [])  # 读取自身根绑定分类。
    }

    # 逐项检查 env 中声明的相对路径。
    for str_env_key, str_value in dict_env.items():

        # 非路径字段和空值不参与 containment 检查。
        if not str_value or not (
            str_env_key.endswith("_RELATIVE_PATH")
            or str_env_key.endswith("_ROOT_RELATIVE")
            or str_env_key == "BATCH_ENTRY"
        ):

            # 当前键不属于相对路径合同，继续处理下一个键。
            continue

        # source_root 白名单字段由自身绑定规则处理。
        if str_env_key in set_source_paths:

            # source_root 键不需要再解析到 Skill root。
            continue

        # Skill root 白名单字段必须在 Skill 根内。
        if str_env_key in set_skill_paths:

            # 使用 Skill root 作为 containment 根。
            path_root: Path = path_skill_root  # 当前 env 键的 containment 根。

        # bundle_root 字段根据 bundle_local 决定 containment 根。
        elif str_env_key in set_bundle_paths:

            # 先解析 bundle 相对目标。
            path_target: Path = (path_bundle / str_value).resolve()  # 当前 bundle 相对目标。

            # bundle_local 使用 bundle 根，否则使用 Skill 根。
            path_containment_root: Path = (  # 当前 bundle 字段选中的 containment 根。
                path_bundle  # bundle-local 键只能留在 bundle 内。
                if str_env_key in set_bundle_local_paths  # 检查本地白名单。
                else path_skill_root  # 其他 bundle 键使用 Skill 根边界。
            )

            # 目标必须位于配置选择的 containment 根。
            if not path_target.is_relative_to(path_containment_root):

                # 拒绝 env 路径跨出其配置根。
                raise ValueError(
                    f"> ERR: [Python] {str_env_key} escapes its configured containment root: {str_value}"
                )

            # bundle 路径已经完成直接 containment 校验。
            continue

        # 任何未列入白名单的路径字段都必须阻断。
        else:

            # 不允许通过未知 env 键猜测根目录。
            raise ValueError(
                f"> ERR: [Python] manifest env path binding is undeclared: {str_env_key}"
            )

        # Skill root 路径使用统一 helper 完成最终 containment 检查。
        _resolve_contained(path_root, str_value, str_env_key)

# 校验 env 与 JSON manifest 的字段、摘要和路径边界。
def validate_manifest_projection(
    path_bundle: Path,
    path_manifest_env: Path,
) -> tuple[dict[str, str], dict[str, Any], Path, Path]:
    """校验 env 与 JSON manifest 的字段、摘要和路径边界。

    参数:
        path_bundle: installer bundle 根目录。
        path_manifest_env: manifest env 文件路径。
    返回:
        env 映射、manifest 对象、Skill 根路径和 manifest JSON 路径。
    异常:
        ValueError 表示 env、manifest、projection 摘要或路径边界不合法。
    """

    # 两个输入路径都必须先固定为绝对路径再执行 containment。
    path_bundle = path_bundle.resolve()  # 后续 containment 比较统一使用此绝对 bundle 根。

    # env 文件路径与 bundle 根分开保存，供后续精确比较。
    path_manifest_env = path_manifest_env.resolve()  # manifest env 绝对路径。

    # env 必须是 bundle 内的真实文件。
    if not path_manifest_env.is_relative_to(path_bundle) or not path_manifest_env.is_file():

        # 阻断缺失或跨 bundle 的 env 文件。
        raise ValueError("> ERR: [Python] manifest env is missing or outside the installer bundle")

    # 读取 env 文件并完成重复键、键名和行格式校验。
    dict_env = read_manifest_env(path_manifest_env)  # installer env 字段映射。

    # 提取 source root 和 manifest JSON 的相对绑定。
    str_source_root_relative = dict_env.get("SOURCE_ROOT_RELATIVE", "")  # env 声明的 Skill 根相对绑定。

    # JSON manifest 相对路径单独保存，避免与 source root 混用。
    str_manifest_json_relative = dict_env.get("MANIFEST_JSON_RELATIVE_PATH", "")  # env 声明的 JSON 相对绑定。

    # 两项根绑定缺失时不能定位 manifest。
    if not str_source_root_relative or not str_manifest_json_relative:

        # 保留两个字段共同缺失的稳定错误。
        raise ValueError("> ERR: [Python] manifest env is missing source-root or JSON-manifest binding")

    # 解析 Skill 根，并要求其包含 bundle 根但不能等于 bundle 根。
    path_skill_root: Path = (path_bundle / str_source_root_relative).resolve()  # env 声明的 Skill 根。

    # source root 必须是 bundle 的严格上级目录。
    if path_skill_root == path_bundle or not path_bundle.is_relative_to(path_skill_root):

        # 阻断错误的根目录绑定，避免读取外部 manifest。
        raise ValueError("> ERR: [Python] configured source root does not contain the installer bundle")

    # 定位并读取 JSON manifest。
    path_manifest_json = _resolve_contained(  # 解析唯一 JSON manifest 的受管路径。
        path_skill_root,  # 使用 Skill root 校验 manifest 声明。
        str_manifest_json_relative,  # env 中的 JSON 相对路径。
        "JSON manifest",  # JSON manifest 错误上下文。
    )

    # 读取 JSON manifest，后续所有字段都从同一对象取值。
    dict_manifest = _read_json_object(path_manifest_json, "installer JSON manifest")  # manifest 合同对象。

    # env_projection 必须是非空对象，后续才能校验 env 键值。
    dict_projection = dict_manifest.get("env_projection")  # env_projection 映射供后续键值对账。

    # 缺失 projection 声明时拒绝继续。
    if not isinstance(dict_projection, dict) or not dict_projection:

        # 阻断没有 env 字段来源的 manifest。
        raise ValueError("> ERR: [Python] installer JSON manifest env_projection is missing")

    # 校验 env 键集合和每个 source path 的期望值。
    _validate_projection_bindings(dict_env, dict_projection, dict_manifest)

    # 校验 manifest env 相对路径与 JSON manifest 声明一致。
    str_manifest_env_relative = str(dict_manifest.get("manifest_env_relative_path", ""))  # JSON manifest 规定的 env 输出相对路径。

    # 解析 manifest 声明的 env 目标，供实际路径比较。
    path_expected_env = _resolve_contained(path_bundle, str_manifest_env_relative, "manifest env")  # manifest 声明的 env 路径。

    # env 实际路径必须与 manifest 声明的路径相同。
    if path_expected_env != path_manifest_env:

        # 阻断 env 与 manifest 路径漂移。
        raise ValueError("> ERR: [Python] manifest env path does not match the JSON manifest")

    # 校验 bundle root 声明与当前 bundle 根一致。
    path_expected_bundle = _resolve_contained(  # 使用 bundle_root_relative 解析待比较的绝对根。
        path_skill_root,  # 以 Skill root 作为 bundle 声明的父级。
        str(dict_manifest.get("bundle_root_relative", "")),  # 读取 JSON manifest 的 bundle_relative 字段。
        "bundle root",  # bundle root 路径错误标签。
    )

    # bundle root 漂移会让所有相对资源失去可信边界。
    if path_expected_bundle != path_bundle:

        # 阻断 bundle 根不一致。
        raise ValueError("> ERR: [Python] bundle root does not match the JSON manifest")

    # 读取 manifest 摘要并绑定真实 JSON 文件字节。
    str_manifest_hash = dict_env.get("MANIFEST_SHA256", "")  # env 写入的 JSON manifest 摘要字段。

    # 计算真实 JSON 文件摘要，供下一条件比较。
    str_actual_manifest_hash = hashlib.sha256(path_manifest_json.read_bytes()).hexdigest()  # 真实 manifest 摘要。

    # 摘要比较失败时应立即拒绝安装。
    if str_manifest_hash != str_actual_manifest_hash:

        # 阻断 JSON manifest 摘要漂移。
        raise ValueError("> ERR: [Python] manifest JSON SHA-256 does not match MANIFEST_SHA256")

    # 读取并校验 manifest projection 文件绑定。
    str_projection_relative = dict_env.get("MANIFEST_PROJECTION_RELATIVE_PATH", "")  # env 中记录的派生 projection 相对目标。

    # 使用 env 声明定位并校验派生 projection 文件。
    path_manifest_projection = _resolve_contained(  # 受管 projection 的绝对路径。
        path_bundle,  # 派生 projection 的 bundle 根。
        str_projection_relative,  # 派生 projection 的相对目标。
        "manifest projection",  # 派生文件错误标签。
    )

    # 校验 projection 文件摘要、表头和逐行 env 值。
    _validate_manifest_projection_file(  # 复核 projection 与 env 的完整绑定。
        path_manifest_projection,  # containment 后的 projection 文件。
        dict_env,  # env 期望值和摘要。
        str_manifest_hash,  # JSON manifest 摘要。
    )

    # 校验所有 env 相对路径的声明白名单和 containment。
    _validate_env_path_bindings(
        dict_env,
        dict_manifest,
        path_skill_root,
        path_bundle,
    )

    # 返回调用方继续安装所需的完整绑定事实。
    return dict_env, dict_manifest, path_skill_root, path_manifest_json
