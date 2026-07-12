"""解析安装目标并执行可回滚的技能复制。"""

# 标准库提供 JSON 错误输出、文件复制、时间戳和类型注解。
from datetime import datetime
import json
from pathlib import Path
import shutil
from typing import Any

# 发布清单模块提供 Codex 主目录解析合同。
from install_release_manifest import default_codex_home

# 目标解析器把 CLI 选项转换为最终技能目录。
def target_path(
    str_skill_name: str,
    str_target: str,
    str_codex_home: str | None,
    str_custom_root: str | None,
) -> Path | None:
    """解析安装目标目录。

    参数：str_skill_name 为技能名，str_target 为目标类型。
    参数：str_codex_home 和 str_custom_root 为可选根目录覆盖值。
    返回：skip 时返回 None，其他合法目标返回技能目录。
    异常：custom 缺少根目录或目标类型非法时抛出 SystemExit。
    """

    # skip 仅验证发布包，不执行本地文件复制。
    if str_target == "skip":

        # 空目标明确表示调用方不得进入复制阶段。
        return None

    # codex 目标位于解析后的 Codex 主目录 skills 子目录。
    if str_target == "codex":

        # 技能名作为安装目录叶节点，避免覆盖整个 skills 根目录。
        return default_codex_home(str_codex_home) / "skills" / str_skill_name

    # custom 目标要求调用方显式提供自定义根目录。
    if str_target == "custom":

        # 缺少根目录时拒绝推测写入位置。
        if not str_custom_root:

            # JSON 错误载荷保持安装 CLI 的机器可读协议。
            raise SystemExit(json.dumps({"errors": ["--custom-root is required when --target custom"]}, indent=2))

        # 展开用户目录并解析绝对位置后再拼接技能名。
        return Path(str_custom_root).expanduser().resolve() / str_skill_name

    # 其他目标类型均不在公开安装合同内。
    raise SystemExit(json.dumps({"errors": ["--target must be skip, codex, or custom"]}, indent=2))

# 时间戳助手为备份目录提供可排序名称。
def stamp() -> str:
    """返回当前本地时间的备份名称片段。

    参数：无。
    返回：适合目录名称的秒级本地时间字符串。
    """

    # 秒级时间戳兼顾可读性和常规安装唯一性。
    return datetime.now().strftime("%Y%m%d-%H%M%S")

# 备份根与 skills 目录保持同一 Codex 主目录边界。
def backup_root_for(path_destination: Path) -> Path:
    """返回目标技能对应的统一备份根目录。

    参数：path_destination 为最终技能安装目录。
    返回：与 skills 同属一个 Codex 主目录的备份根。
    """

    # destination 形如 <home>/skills/<skill>，向上两级回到 home。
    return path_destination.parent.parent / "skill_backups"

# 唯一路径助手避免同一秒内多次替换相互覆盖。
def unique_backup_path(path_destination: Path) -> Path:
    """返回尚不存在的目标技能备份目录。

    参数：path_destination 为最终技能安装目录。
    返回：包含技能名、时间戳和可选序号的空闲路径。
    """

    # 基础名称组合技能名和当前时间戳。
    path_base = backup_root_for(path_destination) / f"{path_destination.name}-{stamp()}"  # 首选备份目录。

    # 首次候选直接使用基础名称。
    path_candidate = path_base  # 当前待检查的备份目录。

    # 后续重名候选从序号 2 开始递增。
    int_suffix = 2  # 下一个备份目录序号。

    # 已存在时持续寻找首个可用的带序号名称。
    while path_candidate.exists():

        # 当前序号必须与随后递增的变量一致，避免未定义名称。
        path_candidate = Path(f"{path_base}-{int_suffix}")  # 新的备份目录候选。

        # 下一轮使用更大的序号。
        int_suffix += 1  # 下一候选序号。

    # 不存在的候选可安全交给移动操作。
    return path_candidate

# 复制入口先备份旧安装，再写入经过验证的发布目录。
def copy_skill(path_skill_dir: Path, path_destination: Path, bool_replace: bool) -> dict[str, Any]:
    """复制技能目录，并在替换时保留旧版本备份。

    参数：path_skill_dir 为发布包技能目录，path_destination 为安装目录。
    参数：bool_replace 控制已存在目标是否允许替换。
    返回：包含可选备份目录字符串的安装结果。
    异常：目标已存在且禁止替换时抛出 FileExistsError。
    """

    # 默认无旧安装，因此结果中的备份路径为空。
    path_backup: Path | None = None  # 实际生成的旧安装备份目录。

    # 已存在目标必须按 replace 合同决定拒绝或备份。
    if path_destination.exists():

        # 未授权替换时不得移动或覆盖用户现有安装。
        if not bool_replace:

            # 明确回显冲突目标，供上层转为结构化错误。
            raise FileExistsError(f"> ERR: [Python] target already exists: {path_destination}")

        # 替换前选择唯一备份路径。
        path_backup = unique_backup_path(path_destination)  # 本次旧安装备份目录。

        # 备份根可能尚未创建。
        path_backup.parent.mkdir(parents=True, exist_ok=True)

        # 移走旧目标后才允许复制新发布内容。
        shutil.move(str(path_destination), str(path_backup))

    # 安装目标的父目录必须先存在。
    path_destination.parent.mkdir(parents=True, exist_ok=True)

    # 缓存、字节码和版本库元数据不属于技能安装内容。
    func_ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".git")  # 复制排除规则。

    # 发布技能目录完整复制到最终目标。
    shutil.copytree(path_skill_dir, path_destination, ignore=func_ignore)

    # 历史 evolution 模板已退出当前安装合同。
    path_legacy_evolution = path_destination / "assets" / "templates" / "evolution"  # 旧模板目录。

    # 仅当旧目录随发布内容出现时执行兼容清理。
    if path_legacy_evolution.exists():

        # 清理失败不应破坏已完成的主技能复制。
        shutil.rmtree(path_legacy_evolution, ignore_errors=True)

    # 空字符串维持既有机器可读结果合同。
    return {"backup_path": str(path_backup) if path_backup else ""}
