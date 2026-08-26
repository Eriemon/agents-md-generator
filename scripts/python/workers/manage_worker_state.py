"""管理当前工作文件夹根 AGENTS.md 中唯一合法的 worker 状态。"""

# 延迟类型注解求值保持 Python 3.10 运行兼容性。
from __future__ import annotations

# 状态治理读取 JSON 授权配置，并使用哈希、文件、正则和标准类型标注。
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

# 状态解析只认 protocol 声明的 canonical worker，避免子 AGENTS 偷换治理对象。
try:
    from .worker_dispatch_contracts import (
        ROOT_AUTHORIZATION_STATES,
        WORKER_NAMES,
        CANONICAL_WORKER_IDS,
        _worker_protocol_path,
    )

# 直接执行时从同目录导入统一的根状态合同。
except ImportError:
    from worker_dispatch_contracts import (
        ROOT_AUTHORIZATION_STATES,
        WORKER_NAMES,
        CANONICAL_WORKER_IDS,
        _worker_protocol_path,
    )

# canonical worker 名称组成根状态正则的第一组候选。
str_worker_names_pattern: str = "|".join(re.escape(str_name) for str_name in WORKER_NAMES)  # worker 名称匹配片段。

# 合法授权状态组成根状态正则的第二组候选。
str_authorization_states_pattern: str = "|".join(re.escape(str_state) for str_state in ROOT_AUTHORIZATION_STATES)  # 状态值匹配片段。

# 状态行必须是根 AGENTS 中不带缩进的精确列表项。
WORKER_STATE_PATTERN = re.compile(  # 根状态行匹配器。
    rf"^-\s*({str_worker_names_pattern})\s*:\s*({str_authorization_states_pattern})\s*$"  # 精确匹配状态行。
)  # 只接受根 AGENTS 中的合法状态行。

# 根级 worker 状态候选允许先被识别，再由验证器报告未知名称或状态。
WORKER_STATE_ANY_PATTERN = re.compile(  # 根状态候选匹配器。
    r"^-\s*(?:\*\*)?([A-Za-z_][A-Za-z0-9_-]*_worker)(?:\*\*)?\s*:\s*(.*?)\s*$"  # 捕获名称和完整状态文本。
)  # 仅用于 fail-closed 诊断，不直接授予权限。

# 任何带缩进的 worker 状态都属于嵌套治理声明，不能改变根级状态。
WORKER_STATE_INDENTED_PATTERN = re.compile(  # 嵌套状态行匹配器。
    r"^\s+-\s*(?:\*\*)?([A-Za-z_][A-Za-z0-9_-]*_worker)(?:\*\*)?\s*:\s*(.*?)\s*$"  # 匹配带缩进状态。
)  # 仅用于报告非法嵌套声明。

# 根状态路径集中解析，供读写和报告共用。
def worker_state_path(project: str | Path = ".") -> Path:
    """返回当前工作文件夹根 AGENTS.md 的绝对路径。

    参数：project 为当前工作文件夹路径。
    返回：根 AGENTS.md 的绝对路径。
    """

    # 根文件位置不得随层级 AGENTS 变化。
    path_project = Path(project).resolve()  # 工作文件夹绝对路径。

    # 只有当前工作文件夹根文件拥有 worker 状态权限。
    return path_project / "AGENTS.md"

# 解析项目授权和协议路径，统一执行项目边界校验。
def _resolve_worker_authorization_paths(
    project: str | Path,
    path_authorization: str | Path,
    path_protocol: str | Path,
) -> tuple[Path, Path]:
    """返回授权文件和协议文件的绝对路径。

    参数:
        project: 当前受管项目根路径。
        path_authorization: 项目授权 JSON 的绝对或项目相对路径。
        path_protocol: canonical worker 协议 JSON 的调用方路径。
    返回:
        授权文件路径与协议文件路径。
    异常:
        ValueError 表示授权路径越出项目根或协议文件缺失。
    """

    # 项目根决定相对授权路径的解析边界。
    path_project = Path(project).resolve()  # 规范化后的项目根

    # 相对授权路径只能绑定当前项目根。
    path_authorization_candidate = Path(path_authorization)  # 调用方授权路径

    # 仅相对路径需要拼接项目根，绝对路径保持调用方声明。
    if not path_authorization_candidate.is_absolute():

        # 将项目相对路径绑定到受管项目根。
        path_authorization_candidate = path_project / path_authorization_candidate  # 项目内授权候选路径

    # 规范化授权路径后执行根边界校验。
    path_authorization_file = path_authorization_candidate.resolve()  # 授权文件绝对路径

    # 授权文件必须继续位于项目根内。
    if not path_authorization_file.is_relative_to(path_project):

        # 越出项目根的授权来源不得参与 worker 判定。
        raise ValueError("> ERR: [Python] worker authorization path is outside project root")

    # 协议文件必须是普通文件，不能使用源码角色回退。
    path_protocol_file = Path(path_protocol).resolve()  # 协议文件绝对路径

    # 缺失协议文件时无法建立 canonical worker 集合。
    if not path_protocol_file.is_file():

        # 缺失协议无法发现 canonical role 集合。
        raise ValueError("> ERR: [Python] worker protocol configuration is missing")

    # 返回两个经过边界检查的文件路径。
    return path_authorization_file, path_protocol_file

# 读取授权和协议 JSON，拒绝损坏文本。
def _load_worker_authorization_objects(
    path_authorization_file: Path,
    path_protocol_file: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    """读取协议对象和可选授权对象。

    参数:
        path_authorization_file: 已解析的项目授权文件路径。
        path_protocol_file: 已解析的 worker 协议文件路径。
    返回:
        协议根对象与授权根对象。
    异常:
        ValueError 表示文件读取失败、JSON 损坏或根类型错误。
    """

    # 解析协议和项目授权 JSON，拒绝损坏文本。
    try:

        # 协议文件提供角色 ID 和状态枚举。
        obj_protocol = json.loads(path_protocol_file.read_text(encoding="utf-8"))  # 协议根对象

        # 授权文件缺失时使用安全空对象。
        if path_authorization_file.is_file():

            # 读取项目显式授权配置。
            obj_authorization = json.loads(path_authorization_file.read_text(encoding="utf-8"))  # 授权根对象

        # 文件不存在时保持全 disabled 迁移状态。
        else:

            # 缺失配置不从旧 AGENTS 文本恢复权限。
            obj_authorization: object = {}  # 缺失配置安全对象

    # 读取或解析失败必须阻断，而不是回退到旧文本。
    except (OSError, UnicodeError, json.JSONDecodeError) as object_error:

        # 错误摘要保留异常类型，避免回显配置正文。
        raise ValueError(
            "> ERR: [Python] worker authorization configuration is invalid: "
            + type(object_error).__name__
        ) from object_error

    # 只有对象根才能提供确定的角色或状态边界。
    if not isinstance(obj_protocol, dict) or not isinstance(obj_authorization, dict):

        # 非对象根无法形成授权模型。
        raise ValueError("> ERR: [Python] worker authorization and protocol roots must be objects")

    # 返回经过类型确认的两个根对象。
    return obj_protocol, obj_authorization

# 从协议对象发现 worker ID 和安全 disabled 状态。
def _protocol_worker_context(
    obj_protocol: dict[str, object],
) -> tuple[list[str], str]:
    """返回协议 worker ID 列表和安全默认状态。

    参数:
        obj_protocol: 已校验的 worker 协议对象。
    返回:
        canonical worker ID 列表与 disabled 状态。
    异常:
        ValueError 表示角色映射或 disabled 状态无效。
    """

    # canonical_roles 是角色短名到 worker ID 的协议映射。
    obj_canonical_roles = obj_protocol.get("canonical_roles")  # 协议角色映射对象

    # 角色映射缺失时必须停止状态解析。
    if not isinstance(obj_canonical_roles, dict):

        # 缺失角色映射时禁止从源码常量构造 worker 集合。
        raise ValueError("> ERR: [Python] worker protocol canonical_roles must be an object")

    # 只保留协议声明的非空角色 ID。
    list_worker_ids = [  # 协议声明的 canonical worker ID 列表
        str(value).strip()  # 当前角色映射的规范化 ID
        for value in obj_canonical_roles.values()  # 遍历协议角色映射值
        if isinstance(value, str) and value.strip()  # 过滤空或非字符串角色
    ]  # 完成角色集合收集

    # 空集合或重复角色会破坏授权结果的一致性。
    if not list_worker_ids or len(list_worker_ids) != len(set(list_worker_ids)):

        # 角色集合不确定时不能生成授权结果。
        raise ValueError("> ERR: [Python] worker protocol canonical_roles are invalid")

    # 从协议授权状态中发现安全默认 disabled。
    str_disabled_state = next(  # 协议声明的安全默认状态
        (
            str(state).strip()  # 当前状态文本
            for state in ROOT_AUTHORIZATION_STATES  # 遍历协议授权状态
            if str(state).strip().casefold() == "disabled"  # 选择 disabled 状态
        ),
        "",  # 协议缺失状态时保留空值
    )  # 完成安全状态发现

    # 没有协议 disabled 状态就不能安全继续。
    if not str_disabled_state:

        # 协议没有 disabled 状态时必须阻断整个授权解析。
        raise ValueError("> ERR: [Python] worker protocol has no disabled authorization state")

    # 返回协议角色和安全默认状态。
    return list_worker_ids, str_disabled_state

# 返回可持久化的协议授权状态集合。
def _configured_authorization_states() -> set[str]:
    """返回允许写入授权配置的状态集合。

    参数:
        无。
    返回:
        排除 unconfigured 的协议状态集合。
    """

    # 只有 configured authorization states 能进入持久化授权。
    return {
        str(state).strip()
        for state in ROOT_AUTHORIZATION_STATES
        if str(state).strip().casefold() != "unconfigured"
    }

# 应用角色级显式授权状态。
def _apply_explicit_worker_states(
    dict_states: dict[str, str],
    obj_explicit_states: object,
    set_configured_states: set[str],
) -> dict[str, str]:
    """将 states 节点合并到默认授权映射。

    参数:
        dict_states: 已应用 default_state 的角色映射。
        obj_explicit_states: canonical_workers.states 原始对象。
        set_configured_states: 协议允许持久化的状态集合。
    返回:
        合并后的角色授权映射。
    异常:
        ValueError 表示 states 类型、角色或状态非法。
    """

    # 空角色映射表示所有角色沿用 default_state。
    if obj_explicit_states in (None, {}):

        # 空映射无需覆盖任何角色。
        return dict_states

    # states 类型必须明确，避免把字符串解释成角色映射。
    if not isinstance(obj_explicit_states, dict):

        # 非对象 states 无法保证逐角色授权边界。
        raise ValueError("> ERR: [Python] canonical_workers.states must be an object")

    # 逐项校验显式角色，未知角色不能扩展协议授权模型。
    for obj_role_id, obj_state in obj_explicit_states.items():

        # JSON key 必须是协议声明的 worker ID。
        str_role_id = str(obj_role_id).strip()  # 显式角色 ID

        # 未知角色不能扩展协议授权边界。
        if str_role_id not in dict_states:

            # 未知角色一律拒绝，避免拼写错误产生隐藏启用。
            raise ValueError("> ERR: [Python] canonical_workers.states contains unknown role")

        # 状态值必须是协议声明的 configured state。
        str_state = str(obj_state).strip() if isinstance(obj_state, str) else ""  # 显式角色状态

        # 未知或未配置状态不能写入授权映射。
        if str_state not in set_configured_states:

            # unconfigured、空值和未知状态均不能持久化。
            raise ValueError("> ERR: [Python] canonical_workers.states contains invalid state")

        # 显式状态覆盖安全默认，但不会影响其他角色。
        dict_states[str_role_id] = str_state  # 写入该角色的最终状态

    # 返回完成逐角色合并的授权映射。
    return dict_states

# 应用 schema v2 canonical_workers 授权节点。
def _apply_authorization_profile(
    obj_authorization: dict[str, object],
    path_authorization_file: Path,
    list_worker_ids: list[str],
    str_disabled_state: str,
) -> dict[str, str]:
    """返回项目授权与协议组合后的状态映射。

    参数:
        obj_authorization: 已校验的项目授权对象。
        path_authorization_file: 授权文件路径，用于识别缺失配置。
        list_worker_ids: 协议声明的 canonical worker ID。
        str_disabled_state: 协议发现的安全默认状态。
    返回:
        最终 canonical worker 状态映射。
    异常:
        ValueError 表示 canonical_workers 或 states 非法。
    """

    # 缺少或旧版授权配置都先收敛到全 disabled。
    dict_states = {  # 每个协议角色的安全默认状态
        str_worker_id: str_disabled_state  # 当前角色使用 disabled 默认值
        for str_worker_id in list_worker_ids  # 遍历协议角色集合
    }  # 完成默认授权映射

    # 旧 AGENTS 文本即使包含 enabled 也不会影响这个结果。
    if not path_authorization_file.is_file():

        # 返回显式安全状态，等待迁移器写入新的授权配置。
        return dict_states

    # 读取 schema v2 的 canonical_workers 节点。
    obj_canonical_workers = obj_authorization.get("canonical_workers", {})  # canonical worker 授权节点

    # 缺少或空节点只代表旧配置，不能授予权限。
    if obj_canonical_workers in (None, {}):

        # 旧配置没有可信授权节点，保持全 disabled。
        return dict_states

    # canonical_workers 类型必须明确。
    if not isinstance(obj_canonical_workers, dict):

        # 非对象节点不能表达默认状态和角色映射。
        raise ValueError("> ERR: [Python] canonical_workers authorization must be an object")

    # 读取允许持久化的协议状态集合。
    set_configured_states = _configured_authorization_states()  # 可持久化状态集合

    # 缺少 default_state 时继续采用协议发现的 disabled。
    str_default_state = str(obj_canonical_workers.get("default_state", str_disabled_state)).strip()  # 项目授权默认状态

    # 默认状态必须属于协议允许的持久化集合。
    if str_default_state not in set_configured_states:

        # 非法默认状态不能悄悄变成 enabled 或 unconfigured。
        raise ValueError("> ERR: [Python] canonical_workers.default_state is invalid")

    # 显式默认状态覆盖缺失角色。
    dict_states = {  # 应用项目声明的默认授权状态
        str_worker_id: str_default_state  # 当前角色沿用项目默认状态
        for str_worker_id in list_worker_ids  # 重建协议角色默认映射
    }  # 完成项目默认授权映射

    # states 节点允许只声明需要改变的角色。
    obj_explicit_states = obj_canonical_workers.get("states", {})  # 角色级显式授权节点

    # 合并角色级显式状态并返回最终映射。
    return _apply_explicit_worker_states(dict_states, obj_explicit_states, set_configured_states)

# 显式项目配置是唯一能够授予 canonical worker 权限的来源。
def resolve_authorized_worker_states(
    project: str | Path,
    path_authorization: str | Path,
    path_protocol: str | Path,
) -> dict[str, str]:
    """解析项目授权配置并为每个协议角色返回有效状态。

    参数:
        project: 当前受管项目根路径。
        path_authorization: 项目授权 JSON 路径。
        path_protocol: canonical worker 协议 JSON 路径。
    返回:
        canonical worker ID 到授权状态的映射。
    异常:
        ValueError 表示授权或协议缺失、损坏、越界或违反 schema。
    """

    # 解析授权和协议文件路径。
    tuple_path_context = _resolve_worker_authorization_paths(project, path_authorization, path_protocol)  # 受管文件路径元组

    # 拆出项目授权文件路径。
    path_authorization_file = tuple_path_context[0]  # 项目授权文件

    # 拆出 worker 协议文件路径。
    path_protocol_file = tuple_path_context[1]  # worker 协议文件

    # 读取并校验协议和授权根对象。
    tuple_authorization_objects = _load_worker_authorization_objects(path_authorization_file, path_protocol_file)  # 校验后的根对象元组

    # 拆出协议根对象。
    obj_protocol = tuple_authorization_objects[0]  # worker 协议对象

    # 拆出项目授权对象。
    obj_authorization = tuple_authorization_objects[1]  # 项目授权对象

    # 发现协议角色和安全默认状态。
    tuple_worker_context = _protocol_worker_context(obj_protocol)  # 协议角色上下文元组

    # 拆出协议声明的 worker ID 列表。
    list_worker_ids = tuple_worker_context[0]  # 供最终状态映射遍历的协议 worker ID 列表

    # 拆出协议发现的 disabled 状态。
    str_disabled_state = tuple_worker_context[1]  # 安全默认状态

    # 应用显式项目授权，缺失配置保持全 disabled。
    return _apply_authorization_profile(obj_authorization, path_authorization_file, list_worker_ids, str_disabled_state)

# 角色短名到 canonical worker ID 的映射只从协议快照读取。
def canonical_worker_id(str_role: str) -> str:
    """返回协议声明的 canonical worker ID。

    参数：str_role 为协议中的角色短名。
    返回：对应 worker ID；角色未知时返回空字符串。
    """

    # 通过协议映射解析角色，避免渲染器复制 worker 名称。
    return CANONICAL_WORKER_IDS.get(str_role, "")

# 根文件读取失败时返回空文本，交由上层报告缺失状态。
def _read_root_text(project: str | Path) -> str:
    """读取根规则；缺失根文件时返回空文本供状态检查报告。

    参数：project 为当前工作文件夹路径。
    返回：根 AGENTS.md 的 UTF-8 文本，缺失时为空字符串。
    """

    # 状态读取复用唯一根路径解析器。
    path_agents = worker_state_path(project)  # 定位唯一允许声明状态的根文件。

    # 缺失或非普通文件不能成为状态来源。
    if not path_agents.is_file():

        # 空文本让调用方生成明确的缺失诊断。
        return ""

    # 容错读取避免编码噪声中断状态审查。
    return path_agents.read_text(encoding="utf-8", errors="ignore")

# 递归扫描只用于发现禁止的非根状态声明。
def _nested_state_files(project: str | Path) -> list[str]:
    """发现并报告根以外声明 worker 状态的 AGENTS.md。

    参数：project 为待检查的当前工作文件夹。
    返回：包含 worker 状态声明的非根 AGENTS.md 相对路径列表。
    """

    # 扫描边界固定在当前工作文件夹内。
    path_project = Path(project).resolve()  # 限定递归扫描的工作文件夹。

    # 只返回实际越权声明的相对路径。
    list_files: list[str] = []  # 非根状态文件列表。

    # 任何子目录状态声明都会使根级治理失效。
    for path_agents in sorted(path_project.rglob("AGENTS.md")):

        # 当前根文件是唯一允许声明状态的位置。
        if path_agents == path_project / "AGENTS.md":

            # 根文件继续由后续逻辑单独解析。
            continue

        # 不可读文件不应被猜测为状态声明。
        try:

            # 读取子级文本只用于发现状态行。
            str_text = path_agents.read_text(encoding="utf-8", errors="ignore")  # 子级文本。

        # 文件消失或权限变化时跳过该候选。
        except OSError:

            # 不把不可读文件误报为有效或无效状态。
            continue

        # 仅记录实际包含 canonical worker 状态的子文件。
        if any(
            WORKER_STATE_PATTERN.match(str_line) or WORKER_STATE_INDENTED_PATTERN.match(str_line)
            for str_line in str_text.splitlines()
        ):

            # 相对路径便于根级报告定位越权来源。
            list_files.append(path_agents.relative_to(path_project).as_posix())

    # 返回稳定排序的越权路径列表。
    return list_files

# 读取状态时缺少精确声明必须保持未配置。
def read_worker_states(project: str | Path = ".") -> dict[str, str]:
    """读取旧根文档状态，供迁移诊断保留历史输入。

    参数：project 为当前工作文件夹路径。
    返回：canonical worker 到 enabled、disabled 或 unconfigured 的状态映射。
    """

    # 旧根文档没有状态行时只返回未配置诊断，不参与新授权。
    dict_states = {str_name: "unconfigured" for str_name in WORKER_NAMES}  # 未声明 worker 的保守状态。

    # 根文件中的精确状态行覆盖默认值。
    for str_line in _read_root_text(project).splitlines():

        # 只接受完整的 canonical worker 状态格式。
        match_state = WORKER_STATE_PATTERN.match(str_line)  # 状态行匹配结果。

        # 非状态行属于普通 AGENTS 正文，不参与状态解析。
        if match_state:

            # 以根级声明覆盖对应 worker 的默认状态。
            dict_states[match_state.group(1)] = match_state.group(2)  # 覆盖对应 worker 的默认状态。

    # 返回只包含 canonical worker 的状态。
    return dict_states

# 授权读取入口只接受显式项目配置，不再读取 AGENTS 文本。
def read_authorized_worker_states(project: str | Path = ".") -> dict[str, str]:
    """读取项目授权状态；缺失配置安全返回全 disabled。

    参数：project 为当前工作文件夹路径。
    返回：canonical worker 到 enabled 或 disabled 的授权状态映射。
    异常：ValueError 表示协议或授权配置不可用。
    """

    # 统一项目对象后，后续配置拼接不再依赖调用方当前工作目录。
    path_project = Path(project).resolve()  # 当前项目根绝对路径

    # 项目授权文件路径由治理根和配置文件名绑定得到。
    path_authorization = path_project / ".agents" / "agents-control.json"  # 项目授权配置路径

    # 协议路径由 worker 合同模块动态解析，避免复制技能绝对路径。
    path_protocol = _worker_protocol_path()  # canonical worker 协议路径

    # 返回授权解析器根据配置和协议计算的最终状态。
    return resolve_authorized_worker_states(
        path_project,
        path_authorization,
        path_protocol,
    )

# 状态验证同时检查根重复声明和子文件越权。
def validate_worker_states(
    project: str | Path = ".",
    bool_include_nested: bool = True,
) -> dict[str, Any]:
    """验证 worker 授权来自项目配置且根文档不携带状态。

    参数：project 为当前工作文件夹路径；bool_include_nested 控制是否审计子文件。
    返回：包含 valid、errors、states 和路径证据的验证映射。
    """

    # 根状态路径供结果载荷和写入边界共同使用。
    path_agents = worker_state_path(project)  # 根状态路径。

    # reviewer 路径关闭递归审计，避免读取 tests/** 下的 AGENTS.md。
    list_nested = _nested_state_files(project) if bool_include_nested else []  # 子文件越权声明。

    # 根状态文本同时用于检查缩进声明和重复声明。
    str_root_text = _read_root_text(project)  # 根正文用于解析唯一状态来源。

    # 根状态候选保留原文以检查重复、未知和非法状态。
    list_root_matches = [  # 根文件中可疑的 worker 状态行。
        match_state  # 匹配对象保留名称和状态字段。
        for str_line in str_root_text.splitlines()  # 逐行定位根级 canonical 状态声明。
        for match_state in [WORKER_STATE_ANY_PATTERN.match(str_line)]  # 只保留 worker 状态候选。
        if match_state  # 忽略普通 AGENTS 列表文本。
    ]  # 根状态候选集合。

    # 根状态名称用于检查缺失声明和重复授权来源。
    list_root_names = [match_state.group(1) for match_state in list_root_matches]  # 根状态 worker 名称。

    # 根状态候选的完整原文用于保留诊断证据。
    list_root_lines = [match_state.group(0) for match_state in list_root_matches]  # 根状态原文列表。

    # 带缩进的声明不得被误当成根级配置。
    list_indented_lines = [  # 根文件中的非法嵌套状态行。
        str_line  # 原文用于错误证据。
        for str_line in str_root_text.splitlines()  # 遍历根文件每一行。
        if WORKER_STATE_INDENTED_PATTERN.match(str_line)  # 只保留带缩进 worker 状态。
    ]  # 非法嵌套状态集合。

    # 收集所有会阻止状态应用的治理错误。
    list_errors: list[str] = []  # 状态合同错误。

    # 读取显式授权映射，旧 AGENTS 状态不再参与权限判定。
    try:

        # 配置授权结果供验证、预览和调度共同复用。
        dict_states = read_authorized_worker_states(project)  # 解析后的授权状态

    # 配置损坏时保留 unconfigured 诊断并阻断后续写入。
    except ValueError as object_error:

        # 失败状态映射只用于报告，不能被调用方当作授权。
        dict_states = {  # 配置失败的诊断状态
            str_worker_name: "unconfigured"  # 当前角色无法取得授权
            for str_worker_name in WORKER_NAMES  # 为每个协议角色建立失败占位
        }  # 完成配置失败映射

        # 保存具体配置错误，避免验证器吞掉 fail-closed 原因。
        list_errors.append(str(object_error))

    # 同一 worker 的重复根状态会造成歧义。
    if len(list_root_names) != len(set(list_root_names)):

        # 重复声明必须先由用户或根文件维护者修复。
        list_errors.append("root AGENTS.md contains duplicate worker state declarations")

    # 未知 worker 名称不能借助状态行扩展授权模型。
    set_unknown_workers = set(list_root_names) - set(WORKER_NAMES)  # 未知 worker 名称集合。

    # 未知名称逐项报告，便于维护者定位具体错误行。
    for str_unknown_worker in sorted(set_unknown_workers):

        # 未知 worker 不参与状态映射，也不能成为自动授权来源。
        list_errors.append(f"root AGENTS.md contains unknown worker: {str_unknown_worker}")

    # 根级状态必须完整来自 protocol 配置，包含未配置的保守状态。
    list_invalid_states = {  # 非法状态文本集合。
        match_state.group(2)  # 取出根状态候选中的状态字段。
        for match_state in list_root_matches  # 遍历所有根状态候选。
        if match_state.group(2) not in ROOT_AUTHORIZATION_STATES  # 过滤不受支持的状态。
    }

    # 非法状态逐项报告，防止配置被静默降级。
    for str_invalid_state in sorted(list_invalid_states):

        # 非法状态不能改变 unconfigured 的保守默认值。
        list_errors.append(f"worker state must be a configured authorization state: {str_invalid_state}")

    # 任意根级状态行都属于旧格式，不能继续充当授权来源。
    if list_root_matches:

        # 要求迁移器从 AGENTS 文本移除状态并写入项目配置。
        list_errors.append("worker state declarations must be stored in project authorization")

    # settings 等嵌套列表不能声明 worker 状态。
    if list_indented_lines:

        # 明确要求维护者把状态移到根级精确列表项。
        list_errors.append("worker state declarations must be exact root list items")

    # 子级状态声明不得覆盖根级唯一来源。
    if list_nested:

        # 明确指出状态只能存在于当前工作文件夹根。
        list_errors.append("worker state is allowed only in the current work-folder root AGENTS.md")

    # 返回状态、路径和根级约束证据。
    return {
        "valid": not list_errors,
        "errors": list_errors,
        "path": str(path_agents),
        "states": dict_states,
        "nested_state_files": list_nested,
        "root_only": True,
    }

# 预览声明式授权 profile，不接触 AGENTS.md 或 worker profile 文件。
def preview_authorization_state(
    project: str | Path,
    path_state_profile: str | Path,
) -> dict[str, Any]:
    """预览 schema v2 worker 授权配置并生成稳定摘要。

    参数：
        project：当前项目根路径。
        path_state_profile：项目内声明式授权 profile 路径。
    返回：
        包含 current/proposed 状态、错误和 preview_sha256 的机器映射。
    状态映射：shape=角色数，dtype=字符串，unit=无量纲。
    """

    # 项目根统一约束 profile 和最终授权文件的位置。
    path_project = Path(project).resolve()  # 状态预览项目根

    # profile 必须位于项目根内，避免外部文件改变授权结果。
    path_profile_candidate = Path(path_state_profile)  # 调用方提供的状态 profile

    # 只有绝对 profile 路径可以直接进行项目边界比较。
    if not path_profile_candidate.is_absolute():

        # 项目相对 profile 绑定到当前项目根。
        path_profile_candidate = path_project / path_profile_candidate  # 项目内 profile 候选

    # 规范化 profile 路径并执行项目边界校验。
    path_profile = path_profile_candidate.resolve()  # 状态 profile 绝对路径

    # 收集 preview 阶段的确定性错误。
    list_errors: list[str] = []  # 预览错误集合

    # 越界路径不得参与授权预览。
    if not path_profile.is_relative_to(path_project):

        # 记录 profile 越界并返回稳定失败摘要。
        list_errors.append("worker state profile is outside project root")

    # 缺失 profile 必须先报告，再决定是否继续读取状态。
    if not path_profile.is_file():

        # 缺失 profile 必须由调用方修复后重新预览。
        list_errors.append("worker state profile is missing")

    # 读取当前授权状态，失败时保持 fail-closed 诊断。
    try:

        # 当前状态来自项目授权文件，不来自 AGENTS 文本。
        dict_current_states = read_authorized_worker_states(path_project)  # 当前授权状态

        # profile 状态通过同一解析器获得提议映射。
        dict_proposed_states = resolve_authorized_worker_states(  # 预览授权状态
            path_project,  # 状态计算的项目根
            path_profile,  # 调用方声明的 profile
            _worker_protocol_path(),  # 协议权威路径
        )  # 完成提议状态解析

    # 配置或协议错误转成机器可读 preview 失败。
    except ValueError as object_error:

        # 保留具体错误并提供空状态映射，禁止调用方误用部分结果。
        list_errors.append(str(object_error))

        # 当前授权无法解析时用空映射表示无可用事实。
        dict_current_states = {}  # 当前状态不可用

        # 提议状态同样不能在错误路径猜测。
        dict_proposed_states = {}  # 预览状态不可用

    # preview 摘要只包含状态映射和错误，不复制完整配置内容。
    dict_preview = {  # 状态预览机器载荷
        "valid": not list_errors,  # 预览是否通过
        "errors": list_errors,  # 当前预览发现的错误
        "project_root": str(path_project),  # 预览项目根
        "state_profile": str(path_profile),  # 调用方 profile 路径
        "current_states": dict_current_states,  # 当前配置解析得到的角色状态
        "proposed_states": dict_proposed_states,  # 提议授权状态
    }  # 完成状态预览载荷

    # 使用排序 JSON 绑定 preview 输入和输出状态。
    str_preview_payload = json.dumps(  # preview 哈希输入
        dict_preview,  # 当前预览载荷
        ensure_ascii=False,  # 保留可读协议文本
        sort_keys=True,  # 稳定键顺序
        separators=(",", ":"),  # 稳定 JSON 分隔符
    )  # 完成 preview 哈希输入

    # 将排序后的 preview JSON 固定为 apply 输入一致性的证据。
    str_preview_hash = hashlib.sha256(str_preview_payload.encode("utf-8")).hexdigest()  # apply 状态一致性指纹

    # 把摘要写回预览对象，供 state-apply 乐观锁复用。
    dict_preview["preview_sha256"] = str_preview_hash  # apply 摘要绑定

    # 返回只读预览，不产生配置写入。
    dict_preview["write"] = False  # 明确 preview 不执行文件写入

    # 将只读摘要返回给 CLI 和调用方。
    return dict_preview

# 将授权配置以临时文件替换方式落盘，避免半写入状态。
def _write_authorization_json(path_config: Path, dict_config: dict[str, object]) -> None:
    """原子写入项目授权 JSON。

    参数：
        path_config：项目授权配置目标路径。
        dict_config：待写入的 schema v2 配置对象。
    返回：无；目标文件被原子替换。
    """

    # 确保治理目录存在，目录范围由调用方项目根绑定。
    path_config.parent.mkdir(parents=True, exist_ok=True)

    # 临时文件与目标文件保持同一目录，保证 os.replace 原子性。
    file_temp = tempfile.NamedTemporaryFile(  # 授权配置临时文件
        mode="w",  # UTF-8 文本写入模式
        encoding="utf-8",  # 配置文件编码
        dir=path_config.parent,  # 同目录临时文件
        delete=False,  # 交由 os.replace 完成最终替换
    )

    # 临时文件创建完成后开始写入排序配置。
    try:

        # 写入排序 JSON，便于后续 preview 和收据绑定。
        json.dump(dict_config, file_temp, ensure_ascii=False, indent=2, sort_keys=True)

        # 追加固定终止换行，保持配置文件可读和哈希稳定。
        file_temp.write("\n")

        # 关闭文件后才能安全执行原子替换。
        file_temp.close()

        # 以同目录替换提交完整授权 JSON。
        os.replace(file_temp.name, path_config)

    # 失败时清理仍存在的临时文件，避免留下额外配置候选。
    finally:

        # 临时文件若未被替换则安全删除。
        if os.path.exists(file_temp.name):

            # 删除只限于本次原子写入创建的临时文件。
            os.unlink(file_temp.name)

# 应用 hash-bound 授权 profile，并把状态写入项目配置。
def apply_authorization_state(
    project: str | Path,
    path_state_profile: str | Path,
    str_expected_preview_sha256: str,
) -> dict[str, Any]:
    """按 preview 摘要原子应用 schema v2 worker 授权。

    参数：
        project：当前项目根路径。
        path_state_profile：项目内声明式授权 profile 路径。
        str_expected_preview_sha256：调用方确认的 preview 摘要。
    返回：
        应用结果和重新解析后的授权状态。
    状态映射：shape=角色数，dtype=字符串，unit=无量纲。
    """

    # apply 必须先重建完全相同的只读 preview。
    dict_preview = preview_authorization_state(project, path_state_profile)  # 当前 preview 结果

    # apply 只接受与当前 preview 完全一致的摘要。
    if (
        not dict_preview.get("valid")
        or str(str_expected_preview_sha256).strip() != dict_preview.get("preview_sha256")
    ):

        # 返回 preview 事实并声明未写入。
        list_preview_errors = list(dict_preview.get("errors", []))  # 当前 preview 错误副本

        # 记录摘要漂移，避免调用方误以为配置已应用。
        list_preview_errors.append("expected preview sha256 does not match current preview")

        # 返回错误副本并明确没有写入。
        dict_preview["errors"] = list_preview_errors  # apply 错误集合

        # apply 错误路径不会写入目标配置。
        dict_preview["write"] = False  # apply 未写入标记

        # 错误摘要路径必须在写入前结束。
        return dict_preview

    # 读取现有配置并保留非 worker 项目合同。
    path_project = Path(project).resolve()  # 应用项目根

    # 项目治理目录承载最终授权配置。
    path_config = path_project / ".agents" / "agents-control.json"  # 最终授权配置目标

    # 缺失配置时从空对象开始构造 schema v2。
    dict_config: dict[str, object] = {}  # 待更新的项目配置

    # 已有配置需要先解析并合并 canonical_workers 节点。
    if path_config.is_file():

        # 现有配置必须是对象，才能安全合并 canonical_workers 节点。
        obj_config = json.loads(path_config.read_text(encoding="utf-8"))  # 已有治理配置对象

        # 配置根类型必须明确，避免覆盖数组或标量文件。
        if not isinstance(obj_config, dict):

            # 标量或数组配置不能被覆盖为 schema v2。
            dict_preview["valid"] = False  # 配置对象无效标记

            # 记录现有治理配置的根类型错误。
            dict_preview["errors"] = ["existing agents-control.json must be an object"]  # 配置类型错误

            # invalid config 路径不得写入任何目标文件。
            dict_preview["write"] = False  # invalid config 无写入标记

            # 配置类型错误必须在写入前返回。
            return dict_preview

        # 保留既有非 Worker 合同并更新授权节点。
        dict_config = obj_config  # 合并后的项目配置

    # profile 内容作为唯一 canonical_workers 提议来源重新读取。
    path_profile = Path(str(dict_preview["state_profile"]))  # 已验证的 profile 路径

    # 重新读取 profile，确保 apply 使用 preview 绑定的同一文件。
    dict_profile = json.loads(path_profile.read_text(encoding="utf-8"))  # 重新读取的 profile 对象

    # profile 根类型必须保持对象。
    if not isinstance(dict_profile, dict):

        # profile 根类型漂移时停止应用。
        dict_preview["valid"] = False  # profile 根类型无效标记

        # 记录提交 profile 的根类型错误。
        dict_preview["errors"] = ["worker state profile must be an object"]  # profile 类型错误

        # profile 类型错误不会产生配置替换。
        dict_preview["write"] = False  # profile 根类型错误保持目标不变

        # 返回前保留 profile 类型诊断。
        return dict_preview

    # schema v2 只更新 canonical_workers，保留其他治理合同。
    dict_config["schema_version"] = 2  # 写入新的授权配置版本

    # 写入 profile 提出的角色状态节点，保留其他治理合同。
    dict_config["canonical_workers"] = dict_profile.get("canonical_workers", {})  # 最终角色授权节点

    # 以同目录临时文件原子提交治理配置。
    _write_authorization_json(path_config, dict_config)

    # 写入后重新读取授权，确保落盘内容与 preview 一致。
    dict_result = preview_authorization_state(project, path_state_profile)  # 写后授权验证

    # 只有写后 preview 成功返回才标记配置已落盘。
    dict_result["write"] = True  # 写后状态确认配置已落盘

    # apply 标志证明摘要校验和原子替换均完成。
    dict_result["applied"] = True  # 标记 hash-bound apply 已完成

    # 返回写后状态和新的预览证据。
    return dict_result

# 状态预览只计算结果，不写入任何根文件。
def preview_worker_state(project: str | Path, worker: str, state: str) -> dict[str, Any]:
    """预览根状态修改，不写入文件。

    参数：project 为工作文件夹；worker 为 canonical worker 名称；state 为目标状态。
    返回：包含验证错误和预计状态的只读预览映射；shape=标量，dtype=文本映射，unit=无量纲。
    """

    # 规范化调用方输入，避免大小写和空白造成隐式分支。
    str_worker = str(worker).strip()  # 请求修改的 worker 名称。

    # 状态文本参与预览分支判断。
    str_state = str(state).strip().lower()  # 规范化待预览的状态文本。

    # 预览必须先继承当前根级治理结果。
    dict_validation = validate_worker_states(project)  # 当前根状态验证。

    # 复制已有错误，确保预览不改变验证结果对象。
    list_errors = list(dict_validation["errors"])  # 继承既有治理错误。

    # 未知 worker 名称直接阻止预览。
    if str_worker not in WORKER_NAMES:

        # 不允许通过新名称绕过 canonical worker 约束。
        list_errors.append(f"unsupported worker `{str_worker}`")

    # 状态值只能是启用或禁用。
    if str_state not in {"enabled", "disabled"}:

        # 其他状态值没有明确治理含义，必须拒绝。
        list_errors.append("worker state must be enabled or disabled")

    # 在副本上计算预览状态，确保不改变验证结果。
    dict_states = dict(dict_validation["states"])  # 预览状态副本。

    # 只有 canonical worker 和合法状态才更新预览映射。
    if str_worker in WORKER_NAMES and str_state in {"enabled", "disabled"}:

        # 预览值不会写回根文件。
        dict_states[str_worker] = str_state  # 记录该 worker 的预览状态。

    # 输出待写入路径和纯预览标记。
    return {
        "valid": not list_errors,
        "errors": list_errors,
        "path": str(worker_state_path(project)),
        "states": dict_states,
        "root_only": True,
        "write": False,
    }

# 应用状态前必须通过完全相同的预览门禁。
def apply_worker_state(project: str | Path, worker: str, state: str) -> dict[str, Any]:
    """在根 AGENTS.md 中更新一个 worker 状态；路径、状态文本均为无量纲治理字段。

    参数：project 为工作文件夹；worker 为 canonical worker；state 为 enabled 或 disabled。
    返回：写入后重新验证的根状态映射；shape=标量，dtype=文本映射，unit=无量纲。
    """

    # 写入前先执行与预览命令相同的所有检查。
    dict_preview = preview_worker_state(project, worker, state)  # 写入前预览。

    # 任何预览错误都停止写入。
    if not dict_preview["valid"]:

        # 原样返回错误，避免越过根级治理门禁。
        return dict_preview

    # 根路径和原文必须同时存在。
    path_agents = worker_state_path(project)  # 确认只写当前根 AGENTS 文件。

    # 读取待保留的根规则原文，避免覆盖其他条款。
    str_text = _read_root_text(project)  # 读取待保留的根规则原文。

    # 缺失根文件不能被自动创建为 worker 状态文件。
    if not str_text:

        # 让调用方先生成或修复当前根 AGENTS.md。
        dict_preview["valid"] = False  # 缺失根文件阻止写入。

        # 报告缺失根文件的阻断原因。
        dict_preview["errors"] = ["current work-folder root AGENTS.md is missing"]  # 缺失根文件阻断状态写入。

        # 缺失根文件时不产生任何外部写入。
        return dict_preview

    # 规范化写入值，保证最终状态行可被同一正则读取。
    str_worker = str(worker).strip()  # 确定要更新的 canonical worker。

    # 写入文本必须与预览时的状态语义一致。
    str_state = str(state).strip().lower()  # 确定写入根文件的规范状态。

    # 按行保留根文件其他规则内容。
    list_lines = str_text.splitlines()  # 根 AGENTS 行列表。

    # 记录是否已经替换现有 worker 状态行。
    bool_replaced = False  # 是否替换已有状态行。

    # 替换目标 worker 的根级状态声明。
    for int_index, str_line in enumerate(list_lines):

        # 只匹配同一 canonical worker 的状态字段。
        if re.match(rf"^-\s*{re.escape(str_worker)}\s*:", str_line):

            # 保持状态行短而精确，避免修改邻近规则文本。
            list_lines[int_index] = f"- {str_worker}: {str_state}"  # 新的根状态行。

            # 后续不再追加重复声明。
            bool_replaced = True  # 已替换状态行。

    # 未声明的 canonical worker 追加到根文件末尾。
    if not bool_replaced:

        # 新状态仍然只写当前根 AGENTS.md。
        list_lines.append(f"- {str_worker}: {str_state}")

    # 只写根 AGENTS，保持其他层级不可禁用。
    str_new_text = "\n".join(list_lines).rstrip() + "\n"  # 保留规则并追加换行。

    # 通过根文件路径一次性写入新的状态文本。
    path_agents.write_text(str_new_text, encoding="utf-8", newline="\n")

    # 写入后重新验证并记录成功标志。
    dict_result = validate_worker_states(project)  # 写后状态验证。

    # 调用方据此区分预览和实际写入。
    dict_result["write"] = True  # 标记已写入根文件。

    # 返回完整根级治理证据。
    return dict_result
