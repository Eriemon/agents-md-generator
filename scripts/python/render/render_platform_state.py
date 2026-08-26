"""实现根级与作用域 AGENTS.md 的渲染入口。"""

# CLI 参数和标准输出依赖用于稳定暴露渲染入口。
import argparse
import json
import os
import sys

# 路径类型用于渲染项目根和可选模板目录。
from pathlib import Path
from typing import Any

# 共享忽略目录保证 scoped 扫描与项目发现一致。
from agents_common import SKIP_DIRS
from agent_platform import (
    global_instruction_file_label,
    load_agent_config,
    load_catalog,
    resolve_agent_profile,
    write_agent_config,
)

# Codebase-memory 写入门禁和 worker 画像负责渲染前的受管能力检查。
from codebase_memory_mcp import enforce_codebase_memory_write_gate

# 语言路由校验器仍由独立模块负责，渲染器只投影压缩后的稳定合同。
from reviewer_worker_profile import REVIEWER_WORKER_SHA256, ensure_reviewer_worker_profile
from tester_worker_profile import ensure_tester_worker_profile
from gardener_worker_profile import ensure_gardener_worker_profile

# 从入口文件定位技能根目录，兼容源码和安装副本两种布局。
def _skill_root_from_entrypoint() -> Path:
    """
    返回当前入口所属的技能根目录。

    参数:
        无外部业务参数；位置由当前模块文件确定。
    返回:
        技能源码或安装副本的根目录。
    """

    # 入口文件向上回溯到包含技能资源的目录。
    return Path(__file__).resolve().parents[3]

# 根据显式平台参数或技能目录配置选择 agent 平台。
def selected_agent_profile(str_agent_platform: str | None = None) -> Any:
    """
    按显式参数或技能目录中的 agent.json 解析平台配置。

    参数:
        str_agent_platform: 可选平台标识；为空时读取技能目录配置。
    返回:
        供渲染和 worker 合同使用的平台配置对象。
    """

    # 显式平台优先，确保调用方的选择不会被本地默认值覆盖。
    if str_agent_platform:

        # 解析指定平台的静态配置和运行时能力。
        return resolve_agent_profile(str_agent_platform)

    # 未指定平台时读取当前技能根目录中的默认配置。
    return load_agent_config(_skill_root_from_entrypoint())

# 收集所有平台对应的受管选择状态文件。
def _platform_selection_paths(project: Path) -> list[Path]:
    """
    返回项目内各平台的选择状态路径。

    参数:
        project: 需要查找平台状态文件的项目根目录。
    返回:
        按平台目录顺序排列的选择状态路径列表。
    """

    # 使用显式中间列表保留平台目录的稳定遍历顺序。
    list_paths: list[Path] = []  # 各平台选择状态文件的路径集合

    # 平台目录来自受管 catalog，避免手写平台枚举。
    for str_agent in sorted(load_catalog()["platforms"]):

        # 记录当前平台在项目中的事务状态文件。
        list_paths.append(
            resolve_agent_profile(str_agent).generator_state_root(project) / "platform-selection.json"
        )

    # 返回供事务快照和回滚流程复用的路径集合。
    return list_paths

# 读取单个平台状态文件，以便事务失败时精确恢复。
def _snapshot_platform_path(path_file: Path) -> tuple[str, bytes | str | None]:
    """
    保存单个平台事务文件的原始状态。

    参数:
        path_file: 需要读取原始状态的受管文件路径。
    返回:
        文件类型标记及其字节内容、符号链接目标或缺失标记。
    """

    # 符号链接必须保留链接目标而不是跟随链接读取内容。
    if path_file.is_symlink():

        # 记录符号链接目标，回滚时按链接语义重建。
        return "symlink", os.readlink(path_file)

    # 普通文件需要保留原始字节，避免编码转换改变状态。
    if path_file.is_file():

        # 读取文件字节以保证事务回滚与原文件完全一致。
        return "file", path_file.read_bytes()

    # 非文件状态统一记录为缺失，回滚时不创建占位文件。
    return "missing", None

# 按事务快照恢复单个平台状态文件。
def _restore_platform_path(path_file: Path, snapshot: tuple[str, bytes | str | None]) -> None:
    """
    回滚单个平台事务文件。

    参数:
        path_file: 需要恢复的受管文件路径。
        snapshot: 文件类型及其原始内容或符号链接目标。
    返回:
        无业务返回值；函数仅恢复文件系统状态。
    """

    # 先移除失败事务留下的文件或链接，避免残留状态遮蔽快照。
    if path_file.exists() or path_file.is_symlink():

        # 删除当前路径后再按快照类型恢复原始节点。
        path_file.unlink()

    # 拆出快照类型和原始载荷，分别处理文件与符号链接。
    str_kind, object_value = snapshot  # 快照节点类型及其原始载荷

    # 普通文件按原始字节写回，并先确保父目录存在。
    if str_kind == "file" and isinstance(object_value, bytes):

        # 文件快照写回前恢复其父目录。
        path_file.parent.mkdir(parents=True, exist_ok=True)

        # 使用原始字节恢复文件内容。
        path_file.write_bytes(object_value)

    # 符号链接按原目标重建，保持链接而不是复制目标文件。
    elif str_kind == "symlink" and isinstance(object_value, str):

        # 符号链接创建前恢复其父目录。
        path_file.parent.mkdir(parents=True, exist_ok=True)

        # 重新建立指向原目标的符号链接。
        os.symlink(object_value, path_file)

# 解析并校验单个平台的事务选择状态。
def _read_selection_state(path_selection: Path, profile: Any) -> dict[str, object]:
    """
    读取并严格校验单个平台选择标记。

    参数:
        path_selection: 平台选择状态 JSON 文件路径。
        profile: 当前解析出的平台配置对象。
    返回:
        通过 schema、平台和事务状态校验的选择字段字典。
    异常:
        RuntimeError: 文件缺失、JSON 损坏或字段与当前平台不匹配。
    """

    # 符号链接和普通缺失文件都不能作为受管选择状态来源。
    if path_selection.is_symlink() or not path_selection.is_file():

        # 以稳定错误文本阻断不可信的选择状态。
        raise RuntimeError("> ERR: [Python] malformed platform selection state")

    # 读取 JSON 时把文件、编码和语法错误统一转换为治理错误。
    try:

        # 读取原始选择状态字节，识别事务中断留下的全空占位文件。
        bytes_selection = path_selection.read_bytes()  # 平台选择状态原始字节

        # 全空或全 NUL 文件没有可信状态，可由当前事务安全重建。
        if not bytes_selection.strip(b"\x00 \t\r\n"):

            # 空占位不代表用户配置，返回空映射交给写入阶段覆盖。
            return {}

        # 解析选择状态文件的结构化字段。
        dict_selection = json.loads(bytes_selection.decode("utf-8"))  # 平台选择状态字段

    # 将文件读取、编码和 JSON 语法异常统一转换为稳定治理错误。
    except (OSError, UnicodeError, json.JSONDecodeError) as object_error:

        # 保留原异常作为原因，同时向调用方暴露稳定治理错误。
        raise RuntimeError("> ERR: [Python] malformed platform selection state") from object_error

    # 规定选择状态必须包含完整且不多不少的 schema 字段。
    set_expected = {  # 选择状态 schema 的固定字段集合
        "schema_version",  # 版本字段用于拒绝旧 schema。
        "agent",  # 平台字段用于核对目标画像。
        "instruction_file",  # 指令文件字段用于核对平台入口。
        "workspace_config_dir",  # 配置目录字段用于核对工作区位置。
        "source",  # 来源字段用于核对渲染来源。
        "selection_state",  # 选择字段用于核对确认状态。
        "migration_state",  # 迁移字段用于核对事务状态。
    }

    # 结构或字段集合不匹配时拒绝继续生成平台文件。
    if not isinstance(dict_selection, dict) or set(dict_selection) != set_expected:

        # 不允许部分字段状态进入后续渲染流程。
        raise RuntimeError("> ERR: [Python] malformed platform selection state")

    # 平台、来源和事务状态必须与当前画像逐项一致。
    if (
        dict_selection.get("schema_version") != 1
        or dict_selection.get("agent") != profile.agent
        or dict_selection.get("instruction_file") != profile.instruction_file
        or dict_selection.get("workspace_config_dir") != profile.workspace_config_dir
        or dict_selection.get("source") != "render-interview"
        or dict_selection.get("selection_state") != "confirmed"
        or dict_selection.get("migration_state") != "transactional"
    ):

        # 拒绝借用其他平台或旧事务留下的状态文件。
        raise RuntimeError("> ERR: [Python] platform selection state does not match selected platform")

    # 返回已完成结构和语义校验的状态字段。
    return dict_selection

# 解析显式迁移来源并验证其受管状态根。
def _resolve_migration_state_paths(
    project: Path,
    str_migrate_from: str | None,
    bool_confirm_migration: bool,
) -> tuple[Path | None, Path | None]:
    """
    解析平台迁移来源的状态路径并校验来源目录。

    参数:
        project: 当前项目根目录，用于解析来源平台状态根。
        str_migrate_from: 可选来源平台标识。
        bool_confirm_migration: 是否确认来源目录仅含受管选择文件。
    返回:
        来源选择文件和来源状态根；未请求迁移时两个值均为空。
    异常:
        RuntimeError: 来源目录不存在、包含额外文件或选择状态无效时抛出。
    """

    # 未请求迁移时不构造任何来源路径，避免后续误删其他平台状态。
    path_migration_selection: Path | None = None  # 来源平台选择文件

    # 来源状态根只在迁移分支中解析。
    path_migration_root: Path | None = None  # 来源平台状态根

    # 显式迁移才需要读取来源平台的目录和选择状态。
    if str_migrate_from:

        # 解析来源平台配置，确保迁移使用受管目录合同。
        profile_migration = resolve_agent_profile(str_migrate_from)  # 来源平台配置

        # 共享根没有可安全退休的专属目录，不能自动迁移。
        if not profile_migration.generator_state_subdir:

            # 保护共享状态根免受自动清理。
            raise RuntimeError("> ERR: [Python] shared platform state root cannot be retired automatically")

        # 记录来源平台的专属状态根和选择文件。
        path_migration_root = profile_migration.generator_state_root(project)  # 已解析来源专属状态容器

        # 在来源状态根内定位唯一受管选择节点。
        path_migration_selection = path_migration_root / "platform-selection.json"  # 来源容器内的选择节点

        # 来源状态根必须是普通目录，不能由符号链接替代。
        if not path_migration_root.is_dir() or path_migration_root.is_symlink():

            # 阻止从不存在或越界的来源状态根迁移。
            raise RuntimeError("> ERR: [Python] migration source platform state directory is unavailable")

        # 仅允许来源目录包含唯一的受管选择文件。
        list_migration_entries = sorted(path_migration_root.iterdir())  # 来源状态根目录项

        # 目录内容和显式确认必须同时满足迁移合同。
        if list_migration_entries != [path_migration_selection] or not bool_confirm_migration:

            # 拒绝带有额外文件或缺少确认的来源状态。
            raise RuntimeError(
                "> ERR: [Python] platform migration requires explicit confirmation and a managed-only source state"
            )

        # 校验来源选择状态确实属于来源平台且处于已确认事务状态。
        _read_selection_state(path_migration_selection, profile_migration)

    # 返回迁移校验产生的两个可选路径。
    return path_migration_selection, path_migration_root

# 检查当前项目是否存在不允许并存的平台选择状态。
def _validate_existing_platform_states(
    project: Path,
    path_state_root: Path,
    path_selection: Path,
    path_migration_selection: Path | None,
    profile: Any,
) -> None:
    """
    校验目标状态根和所有已存在的平台选择文件。

    参数:
        project: 当前项目根目录。
        path_state_root: 目标平台状态根。
        path_selection: 目标平台选择文件路径。
        path_migration_selection: 可选来源平台选择文件路径。
        profile: 当前目标平台配置对象。
    返回:
        无业务返回值；校验失败时抛出治理异常。
    异常:
        RuntimeError: 状态节点损坏、选择冲突或 JSON 无效时抛出。
    """

    # 目标状态根不能是链接或普通文件伪装的目录。
    if path_state_root.is_symlink() or (path_state_root.exists() and not path_state_root.is_dir()):

        # 阻止在错误节点类型上创建平台状态。
        raise RuntimeError("> ERR: [Python] malformed platform state directory")

    # 读取所有平台选择文件，用于阻断多平台同时选中的状态。
    list_selection_paths = _platform_selection_paths(project)  # 所有平台选择状态文件

    # 逐一核验当前项目已存在的选择状态文件。
    for path_existing_selection in list_selection_paths:

        # 缺失文件不是冲突，可以继续检查其他平台。
        if not (path_existing_selection.exists() or path_existing_selection.is_symlink()):

            # 当前平台尚未产生选择状态，跳过本轮检查。
            continue

        # 目标平台已有状态时必须验证 schema 和画像一致性。
        if path_existing_selection == path_selection:

            # 复用统一选择状态校验，避免两套 schema 规则漂移。
            _read_selection_state(path_existing_selection, profile)

            # 已验证的目标状态不应继续按其他平台处理。
            continue

        # 迁移来源状态由专用迁移分支验证，避免被误判为并发选择。
        if path_existing_selection == path_migration_selection:

            # 当前文件属于已确认迁移来源，跳过通用冲突处理。
            continue

        # 其他平台状态必须是普通文件，不能接受链接或目录。
        if path_existing_selection.is_symlink() or not path_existing_selection.is_file():

            # 不可信的状态节点直接阻断平台切换。
            raise RuntimeError("> ERR: [Python] malformed platform selection state")

        # 读取其他平台状态，确认它不是可接受的受管状态副本。
        try:

            # 解析其他平台选择文件以便给出确定的冲突结论。
            dict_existing_selection = json.loads(  # 其他平台选择状态字段
                path_existing_selection.read_text(encoding="utf-8")  # 其他平台状态文件文本
            )

        # 文件损坏时保持治理错误边界并保留原异常原因。
        except (OSError, UnicodeError, json.JSONDecodeError) as object_error:

            # 将损坏的其他平台状态转换为统一治理错误。
            raise RuntimeError("> ERR: [Python] malformed platform selection state") from object_error

        # 非字典状态不能作为合法平台选择文件。
        if not isinstance(dict_existing_selection, dict):

            # 阻止标量或数组伪装成平台状态。
            raise RuntimeError("> ERR: [Python] malformed platform selection state")

        # 任何其他平台的合法状态都表示并发选择冲突。
        raise RuntimeError("> ERR: [Python] multiple platform state directories are selected")

# 检查未选平台是否留下需要显式迁移的状态目录。
def _validate_unselected_platform_roots(
    project: Path,
    profile: Any,
    path_migration_root: Path | None,
) -> None:
    """
    校验未选平台的专属状态根为空或属于已确认迁移来源。

    参数:
        project: 当前项目根目录。
        profile: 当前目标平台配置对象。
        path_migration_root: 可选已确认迁移来源状态根。
    返回:
        无业务返回值；发现遗留状态时抛出治理异常。
    异常:
        RuntimeError: 未选平台状态根损坏或非空且未获迁移确认时抛出。
    """

    # 非 Codex 平台的专属状态根只能在确认迁移后继续。
    for str_agent in sorted(load_catalog()["platforms"]):

        # 逐个平台解析状态根，避免使用固定目录名称。
        profile_existing = resolve_agent_profile(str_agent)  # 待检查平台配置

        # 当前平台和无专属目录的平台不参与遗留目录阻断。
        if profile_existing.agent == profile.agent or not profile_existing.generator_state_subdir:

            # 当前或共享根无需作为未选中平台处理。
            continue

        # 读取未选中平台的专属状态根。
        path_unselected_root = profile_existing.generator_state_root(project)  # 未选中平台状态根

        # 未选中状态根必须保持目录节点语义。
        if path_unselected_root.is_symlink() or (
            path_unselected_root.exists()
            and not path_unselected_root.is_dir()
        ):

            # 阻止普通文件或链接伪装平台状态目录。
            raise RuntimeError("> ERR: [Python] malformed unselected platform state directory")

        # 已确认迁移来源由迁移分支负责清理，不在此处重复阻断。
        if path_unselected_root == path_migration_root:

            # 保留来源目录进入后续迁移事务。
            continue

        # 任何非空遗留目录都要求用户显式迁移，不能静默复用。
        if path_unselected_root.is_dir() and any(path_unselected_root.iterdir()):

            # 将遗留平台状态作为明确的迁移阻断原因报告。
            raise RuntimeError("> ERR: [Python] unselected platform state directory requires explicit migration")

# 校验平台迁移参数，避免事务函数同时承担输入分支。
def _validate_platform_request(
    str_agent_platform: str | None,
    str_migrate_from: str | None,
    bool_confirm_migration: bool,
    profile: Any,
) -> None:
    """
    校验平台选择和迁移确认之间的关系。

    参数:
        str_agent_platform: 可选目标平台标识。
        str_migrate_from: 可选迁移来源平台标识。
        bool_confirm_migration: 是否确认来源状态仅包含受管选择状态。
        profile: 已解析的目标平台配置对象。
    返回:
        无业务返回值；非法组合直接抛出治理异常。
    异常:
        RuntimeError: 参数组合不能形成受控平台事务时抛出。
    """

    # 迁移确认必须绑定明确来源，防止无来源的宽泛确认被误用。
    if bool_confirm_migration and not str_migrate_from:

        # 没有来源平台时无法验证迁移范围。
        raise RuntimeError("> ERR: [Python] platform migration confirmation requires a source platform")

    # 指定来源时必须同时指定目标，避免把默认平台当作隐式迁移目标。
    if str_migrate_from and not str_agent_platform:

        # 显式阻止目标平台缺失的迁移请求。
        raise RuntimeError("> ERR: [Python] platform migration requires an explicit target platform")

    # 来源与目标相同不会产生有效迁移，直接拒绝以免覆盖状态。
    if str_migrate_from == profile.agent:

        # 同平台迁移不是允许的状态转换。
        raise RuntimeError("> ERR: [Python] platform migration source and target must differ")

# 收集需要同步的兼容入口路径，保持文件遍历与事务提交分离。
def _collect_platform_shim_paths(project: Path, should_skip: Any) -> list[Path]:
    """
    收集项目内受管 AGENTS.md 对应的兼容入口路径。

    参数:
        project: 当前项目根目录。
        should_skip: 根据目录合同判断路径是否跳过的函数。
    返回:
        按稳定文件顺序排列的 CLAUDE.md 和 GEMINI.md 路径。
    """

    # 只为未跳过的受管 AGENTS.md 生成兼容入口。
    list_shim_paths: list[Path] = []  # 待生成的兼容入口路径

    # 按稳定顺序扫描项目中的受管根文件。
    for path_agents_file in sorted(project.rglob("AGENTS.md")):

        # 跳过目录合同明确排除的文件树。
        if should_skip(path_agents_file, project, SKIP_DIRS):

            # 当前文件不属于本次 shim 事务范围。
            continue

        # 同步收集 CLAUDE.md 和 GEMINI.md 两个兼容入口。
        list_shim_paths.extend(
            path_agents_file.parent / str_name for str_name in ("CLAUDE.md", "GEMINI.md")
        )

    # 返回供快照和提交阶段共同使用的候选路径。
    return list_shim_paths

# 构造平台选择文件的固定 schema，集中维护状态载荷。
def _build_platform_selection(profile: Any) -> dict[str, object]:
    """
    创建当前平台的受管选择状态载荷。

    参数:
        profile: 已解析的目标平台配置对象。
    返回:
        可稳定序列化到 platform-selection.json 的状态字典。
    """

    # 固定字段保证平台状态能够被后续治理检查识别。
    return {
        "schema_version": 1,
        "agent": profile.agent,
        "instruction_file": profile.instruction_file,
        "workspace_config_dir": profile.workspace_config_dir,
        "source": "render-interview",
        "selection_state": "confirmed",
        "migration_state": "transactional",
    }

# 写入技能配置和目标平台选择文件，隔离基础文件落盘步骤。
def _write_platform_files(
    path_state_root: Path,
    path_selection: Path,
    path_skill_config: Path,
    str_agent_platform: str | None,
    profile: Any,
    dict_selection: dict[str, object],
) -> None:
    """
    写入平台技能配置、状态目录和选择文件。

    参数:
        path_state_root: 目标平台状态根目录。
        path_selection: 目标平台选择状态文件。
        path_skill_config: 技能级 agent.json 路径。
        str_agent_platform: 是否有显式平台选择。
        profile: 已解析的目标平台配置对象。
        dict_selection: 待写入的选择状态载荷。
    返回:
        无；文件写入失败时由调用方执行事务回滚。
    """

    # 只有显式目标平台才更新技能级默认配置。
    if str_agent_platform:

        # 将目标平台写入技能配置，供下一次无参数调用读取。
        write_agent_config(_skill_root_from_entrypoint(), profile.agent)

    # 先创建目标状态根，再写入受管选择文件。
    path_state_root.mkdir(parents=True, exist_ok=True)

    # 以稳定排序和 UTF-8 编码写入选择状态 JSON。
    path_selection.write_text(
        json.dumps(dict_selection, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

# 执行兼容入口同步并返回动作和警告，保持提交主函数短小。
def _apply_platform_shims(
    list_shim_paths: list[Path],
    create_link_or_shim: Any,
) -> tuple[list[str], list[str]]:
    """
    创建平台兼容入口并收集事务结果。

    参数:
        list_shim_paths: 待创建的兼容入口路径。
        create_link_or_shim: 执行单个兼容入口创建的函数。
    返回:
        动作清单和非阻断警告清单组成的二元组。
    """

    # 分别收集 shim 动作和非阻断警告，避免与动作清单混用。
    list_actions: list[str] = []  # 待记录的 shim 提交动作

    # 单独收集 shim 过程中的非阻断提示，避免与动作清单混用。
    list_warnings: list[str] = []  # shim 过程中产生的非阻断提示

    # 逐个创建兼容入口，并将结果写入同一事务集合。
    for path_shim_target in list_shim_paths:

        # 当前 shim 写入由专用实现处理，保持目标平台差异隔离。
        create_link_or_shim(path_shim_target, list_warnings, list_actions)

    # 返回提交阶段需要合并到事务结果的两类记录。
    return list_actions, list_warnings

# 迁移事务完成后退休来源状态根，保持来源清理条件集中。
def _retire_platform_migration(
    path_migration_selection: Path | None,
    path_migration_root: Path | None,
) -> None:
    """
    删除已迁移来源的选择文件并清理空状态根。

    参数:
        path_migration_selection: 来源平台选择文件，可为空。
        path_migration_root: 来源平台状态根，可为空。
    返回:
        无；迁移来源为空时不执行任何操作。
    """

    # 迁移事务完成后删除来源选择文件和空状态根。
    if path_migration_selection is not None:

        # 删除已迁移的来源平台选择标记。
        path_migration_selection.unlink()

        # 仅清理迁移后空的来源状态根。
        if path_migration_root is not None and not any(path_migration_root.iterdir()):

            # 来源目录为空时完成目录退休。
            path_migration_root.rmdir()

# 将用户已有平台入口转换为非阻断 warning，保持原文件不可写边界。
def _platform_conflict_warnings(list_conflicts: list[Path]) -> list[str]:
    """构造未受管平台入口的保留提示。

    参数:
        list_conflicts: 已发现且禁止覆盖的用户入口路径。
    返回:
        每个冲突入口对应的非阻断 warning 文本。
    """

    # 每个冲突路径独立进入 warning，便于调用方定位被保留文件。
    list_warnings: list[str] = []  # 用户入口保留提示

    # 遍历冲突路径并保持每个用户文件的独立诊断。
    for path_conflict in list_conflicts:

        # 只报告路径事实，不读取或覆盖用户文件内容。
        list_warnings.append(
            f"> WARNING: [Python] preserved unmanaged platform shim: {path_conflict.as_posix()}"
        )

    # 返回稳定顺序的用户文件保留提示。
    return list_warnings

# 从 shim 写入事务中排除用户已有的非受管入口。
def _filter_platform_shim_paths(
    list_shim_paths: list[Path],
    list_conflicts: list[Path],
) -> list[Path]:
    """返回可以安全交给 shim helper 写入的路径。

    参数:
        list_shim_paths: shim helper 原本计划同步的路径。
        list_conflicts: 已存在的非受管用户入口。
    返回:
        排除用户入口后的可写路径，保持原发现顺序。
    """

    # 冲突集合用于阻断任何覆盖用户入口的写入动作。
    set_conflict_paths = set(list_conflicts)  # 不可覆盖的用户入口集合

    # 逐项保留非冲突目标，维持原始发现顺序。
    list_safe_paths: list[Path] = []  # 可安全同步的入口路径

    # 逐项过滤冲突目标，避免事务覆盖用户文件。
    for path_file in list_shim_paths:

        # 用户入口由上层 warning 记录，不进入写入事务。
        if path_file in set_conflict_paths:

            # 冲突目标保持原样并从可写清单中排除。
            continue

        # 追加当前可写入口路径。
        list_safe_paths.append(path_file)

    # 返回已过滤的 shim 事务目标。
    return list_safe_paths

# 合并用户入口保留提示与 shim helper 的运行期 warning。
def _merge_platform_warnings(
    list_conflict_warnings: list[str],
    list_shim_warnings: list[str],
) -> list[str]:
    """合并平台事务的两类非阻断警告。

    参数:
        list_conflict_warnings: 用户入口被保留时产生的 warning。
        list_shim_warnings: shim helper 产生的降级或兼容 warning。
    返回:
        按产生顺序合并的完整 warning 清单。
    """

    # 复制首批 warning，避免修改调用方持有的冲突列表。
    list_warnings = list(list_conflict_warnings)  # 复制用户入口保留提示，避免修改调用方列表

    # 追加 shim helper 产生的降级或兼容提示。
    list_warnings.extend(list_shim_warnings)

    # 返回事务公开的完整 warning 清单。
    return list_warnings

# 原子创建选定平台状态目录并同步兼容入口。
def ensure_platform_artifacts(
    project: Path,
    str_agent_platform: str | None = None,
    bool_commit: bool = True,
    str_migrate_from: str | None = None,
    bool_confirm_migration: bool = False,
) -> dict[str, object]:
    """
    创建选定平台状态目录并同步两个兼容入口。

    参数:
        project: 需要写入平台状态和兼容入口的项目根目录。
        str_agent_platform: 可选目标平台标识；为空时使用当前配置。
        bool_commit: 是否实际落盘；为 False 时只返回计划动作。
        str_migrate_from: 可选来源平台标识，用于受控平台迁移。
        bool_confirm_migration: 是否明确确认来源平台仅包含受管选择状态。
    返回:
        包含平台标识、状态根、迁移来源、动作和警告的事务结果。
    异常:
        RuntimeError: 平台选择、目录状态、迁移条件或兼容入口冲突时抛出。
    """

    # 解析目标平台，后续所有状态路径都从同一配置对象派生。
    profile = selected_agent_profile(str_agent_platform)  # 当前事务的目标平台配置

    # 输入校验独立执行，平台事务主体只处理状态和文件。
    _validate_platform_request(
        str_agent_platform,
        str_migrate_from,
        bool_confirm_migration,
        profile,
    )

    # 延迟导入 shim 实现，保持平台状态检查模块的依赖边界清晰。
    from create_agent_shims import create_link_or_shim, should_skip, unmanaged_shim_conflicts

    # 先检查项目中是否有未受管的兼容入口，避免覆盖用户文件。
    list_conflicts = unmanaged_shim_conflicts(project, SKIP_DIRS)  # 未受管 shim 冲突列表

    # 用户已有的非受管入口必须保留，转为 warning 而不是覆盖或重复写入。
    list_conflict_warnings = _platform_conflict_warnings(list_conflicts)  # 未覆盖用户入口的 warning 载荷

    # 目标平台状态根和选择文件由平台配置集中派生。
    path_state_root = profile.generator_state_root(project)  # 目标平台状态根

    # 选择文件记录当前平台的 schema 和事务状态。
    path_selection = path_state_root / "platform-selection.json"  # 目标平台选择状态文件

    # 解析显式来源平台状态，并保持原有迁移校验顺序。
    tuple_migration_paths: tuple[Path | None, Path | None] = _resolve_migration_state_paths(  # 迁移来源路径二元组
        project,  # 为 shim 扫描锁定入口传入的仓库边界
        str_migrate_from,  # 显式迁移来源平台
        bool_confirm_migration,  # 来源目录受管确认标记
    )  # 来源选择文件与状态根

    # 将迁移 helper 的有序结果恢复为原有局部变量语义。
    path_migration_selection: Path | None = tuple_migration_paths[0]  # 迁移来源的选择节点

    # 读取来源状态根供未选平台遗留检查复用。
    path_migration_root: Path | None = tuple_migration_paths[1]  # 待退休的来源状态容器

    # 校验目标状态根、当前选择和其他平台的并发选择冲突。
    _validate_existing_platform_states(
        project,
        path_state_root,
        path_selection,
        path_migration_selection,
        profile,
    )

    # 阻断未选平台遗留状态，除非它属于已确认迁移来源。
    _validate_unselected_platform_roots(project, profile, path_migration_root)

    # 预览模式只返回计划，不触碰文件系统。
    if not bool_commit:

        # 预览结果保持与提交结果相同的字段合同。
        return {
            "agent": profile.agent,  # 预览目标平台标识
            "state_root": str(path_state_root),  # 预览目标状态根
            "migration_source": str_migrate_from,  # 预览来源平台标识
            "actions": [],  # 预览模式不产生写入动作
            "warnings": list_conflict_warnings,  # 预览模式公开保留冲突
        }

    # 技能配置文件和兼容入口都纳入同一事务快照。
    path_skill_config = _skill_root_from_entrypoint() / "config" / "agent.json"  # 技能平台配置文件

    # 收集项目内由 AGENTS.md 配套生成的兼容入口路径。
    list_shim_paths = _collect_platform_shim_paths(  # 平台 shim 收集阶段使用同一跳过目录合同
        project,  # 当前项目根目录
        should_skip,  # 目录排除判断函数
    )

    # 已存在的用户入口不进入写入事务，确保保留语义不会被 shim helper 改写。
    list_shim_paths = _filter_platform_shim_paths(list_shim_paths, list_conflicts)  # 过滤冲突入口

    # 快照所有可能被本次事务修改或删除的文件。
    dict_snapshots = {  # 事务回滚所需的原始文件快照
        # 每个路径都保留节点类型和原始载荷，保证异常回滚可逆。
        path_file: _snapshot_platform_path(path_file)  # 当前文件的原始节点状态
        for path_file in [  # 参与回滚的候选文件路径
            path_skill_config,  # 写入前需回滚的技能配置节点
            path_selection,  # 目标平台选择文件
            *( [path_migration_selection] if path_migration_selection else [] ),  # 可选来源节点快照
            *list_shim_paths,  # 项目兼容入口文件
        ]
    }

    # 记录目标状态根是否已存在，用于异常时决定是否清理空目录。
    bool_state_root_preexisting = path_state_root.exists()  # 目标状态根原始存在状态

    # 构造写入选择文件的固定 schema 和事务标记。
    dict_selection = _build_platform_selection(profile)  # 当前平台选择状态载荷

    # 所有落盘步骤共享一个异常回滚边界。
    try:

        # 先写入基础平台文件，再同步兼容入口。
        _write_platform_files(
            path_state_root,
            path_selection,
            path_skill_config,
            str_agent_platform,
            profile,
            dict_selection,
        )

        # 逐个创建兼容入口并收集动作和警告。
        tuple_shim_result = _apply_platform_shims(list_shim_paths, create_link_or_shim)  # 平台 shim 事务结果

        # 将 shim 返回的动作清单恢复为公开结果字段。
        list_actions = tuple_shim_result[0]  # 已提交的 shim 动作清单

        # 将 shim 警告与用户文件保留事实合并为公开结果字段。
        list_shim_warnings = tuple_shim_result[1]  # 当前 shim helper 产生的降级诊断

        # 汇总两类兼容入口诊断，供平台事务结果统一返回。
        list_warnings = _merge_platform_warnings(list_conflict_warnings, list_shim_warnings)  # 合并两类兼容诊断

        # 迁移成功后退休来源平台状态。
        _retire_platform_migration(path_migration_selection, path_migration_root)

    # 任何写入异常都必须恢复全部快照并原样抛回。
    except Exception:

        # 按快照逐文件恢复技能配置、选择文件和兼容入口。
        for path_file, object_snapshot in dict_snapshots.items():

            # 当前文件恢复到事务开始前的节点类型和内容。
            _restore_platform_path(path_file, object_snapshot)

        # 只删除事务新建且最终为空的目标状态根。
        if not bool_state_root_preexisting and path_state_root.is_dir() and not any(path_state_root.iterdir()):

            # 清理未留下有效状态的临时目录。
            path_state_root.rmdir()

        # 保持原始异常类型和堆栈交给调用方处理。
        raise

    # 返回已提交事务的动作、警告和平台状态位置。
    return {
        "agent": profile.agent,  # 已提交目标平台标识
        "state_root": str(path_state_root),  # 已提交状态根
        "migration_source": str_migrate_from,  # 已提交来源平台标识
        "actions": list_actions,  # 提交结果中的 shim 操作清单
            "warnings": list_warnings,  # 事务返回的完整兼容入口诊断
    }
