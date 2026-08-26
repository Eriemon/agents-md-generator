"""执行目录接管、结构候选识别和 tests 布局治理。"""

# 延迟解析类型注解，避免运行期求值联合类型。
from __future__ import annotations

# 操作系统链接探测补充 pathlib 在不同平台上的符号链接判断。
import os
import stat

# 路径类型支撑结构扫描与迁移结果。
from pathlib import Path
from typing import Any

# 公共忽略规则排除工具缓存和不属于业务结构的目录。
from agents_common import SKIP_DIRS
from agents_decisions import decision_request

# 目录状态常量定义快照、归档和根文件的持久化边界。
from manage_dirs_state import (
    CURRENT_STRUCTURE,
    DIR_MANAGER_MD,
    PLANNED_STRUCTURE,
    TAKEOVER_PRESERVE_ROOT_FILES,
)

# 目录状态函数提供项目配置、归档和路径显示能力。
from manage_dirs_state import (
    archive_dir_manager,
    control_profile,
    display_rel,
    init_dir_manager,
)

# 计划读取和路径规范化维持接管目标的一致表达。
from manage_dirs_state import (
    load_planned,
    normalize_rel,
    planned_structure,
)

# 多平台链接判断统一收口，避免接管扫描遗漏特殊链接对象。
def _is_symbolic_link(path_candidate: Path) -> bool:
    """判断候选路径是否为符号链接或等价链接对象。

    参数：path_candidate 为待检查的目录项。
    返回：能够证明为链接时返回 True；无法读取时保守返回 False。
    """

    # 三种判断覆盖 pathlib、os.path 和底层 lstat 语义。
    try:

        # 任一平台级证据命中都禁止自动接管。
        return (
            path_candidate.is_symlink()
            or os.path.islink(path_candidate)
            or stat.S_ISLNK(path_candidate.lstat().st_mode)
        )

    # 读取失败不把异常转成自动迁移许可。
    except OSError:

        # 上层仍会继续执行解析边界检查，链接无法证明时由其他门禁阻断。
        return False

# 结构扫描函数负责比较批准计划与当前工作区事实。
from manage_dirs_state import (
    allowed_path,
    invalid_path_reason,
    nested_workspace_artifact_reason,
    scan_structure,
    unapproved_root_files,
)

# 结构迁移目标必须先通过安全相对路径合同。
def _safe_primary_root(raw: object) -> str:
    """只返回可用于工作区内结构目标的安全相对路径。

    参数：raw 为治理配置或批准计划中的原始目标根。
    返回：通过路径边界检查的工作区相对目标；不安全时返回空字符串。
    """

    # 结构目标必须来自字符串字段，避免把任意对象转成路径。
    if not isinstance(raw, str):

        # 缺失或类型错误的治理字段不能授权文件系统动作。
        return ""

    # 原始路径必须先过边界检查，再进行显示规范化。
    str_raw = raw.strip().rstrip("/\\")  # 允许目录契约的尾斜杠表示法。

    # 项目根和空值都不能作为自动移动目标。
    if not str_raw or str_raw == ".":

        # 空结果让调用方保持原有的人工处理分支。
        return ""

    # 绝对路径、父级穿越和点号片段一律拒绝。
    if invalid_path_reason(str_raw):

        # 未通过路径合同时不得依赖 normalize_rel 的折叠结果。
        return ""

    # 只在原始路径安全后生成稳定的相对表示。
    str_normalized = normalize_rel(str_raw)  # 结构计划使用的相对路径。

    # 规范化结果仍需排除空值和项目根。
    if not str_normalized or str_normalized == ".":

        # 空目标不能触发目录创建或移动。
        return ""

    # 返回已通过边界合同的相对结构根。
    return str_normalized

# 接管路径证明拒绝绝对路径、链接组件和项目根逃逸。
def _path_stays_inside_project(project: Path, path_candidate: Path) -> bool:
    """判断接管目标及其现有父级是否保持在项目根内。

    参数：project 为已确认的工作区根；path_candidate 为待接管路径。
    返回：候选路径安全且位于工作区内时为 True，否则为 False。
    """

    # 规范化根和候选路径，拒绝绝对路径或父级片段逃逸。
    path_project_absolute = project.absolute()  # 接管项目的词法绝对路径。

    # 解析工作区根作为后续相对关系的安全边界。
    path_project_root = project.resolve()  # 接管项目的实际根目录。

    # 项目根自身若由链接承载，自动迁移边界无法形成可靠证明。
    if path_project_absolute != path_project_root:

        # 即使候选仍落在解析后的项目内也保持 fail-closed。
        return False

    # 非严格解析和相对关系计算形成目标路径的安全证明。
    try:

        # 非严格解析允许校验尚未创建的安全目标路径。
        path_resolved_candidate = path_candidate.resolve(strict=False)  # 候选实际路径。

        # 相对关系计算确认候选没有越出工作区边界。
        path_relative = path_resolved_candidate.relative_to(path_project_root)  # 项目内相对分量。

    # 无法解析或已越过项目根的目标必须停止接管。
    except (OSError, RuntimeError, ValueError):

        # 不依赖字符串前缀判断文件系统边界。
        return False

    # 目标路径的任一现有组件若为链接，都可能改变迁移写入位置。
    path_cursor = path_project_root  # 逐级检查的目标路径。

    # 逐级检查已存在父级和目标本身。
    for str_part in path_relative.parts:

        # 追加当前路径分量。
        path_cursor = path_cursor / str_part  # 当前目标组件。

        # 符号链接不属于可自动接管的目录边界。
        if _is_symbolic_link(path_cursor):

            # 即使链接指回项目内也保持 fail-closed。
            return False

    # 目标通过解析边界与符号链接检查。
    return True

# 自动修复候选只接受“单一未批准目录迁入尚不存在的主项目根”场景。
def obvious_structure_fix_candidate(
    project: Path, profile: dict, planned: dict
) -> dict[str, str]:
    """识别能够安全自动执行的单一结构修复候选。

    参数：project 为项目根，profile 为控制配置，planned 为批准目录计划。
    返回：候选动作字段；不存在唯一保守候选时返回空映射。
    """

    # 控制配置中的目录合同是主项目根的权威声明。
    dict_contract: dict[str, Any] = (  # 当前项目目录合同
        profile.get("directory_contract", {})  # 有效目录合同对象
        if isinstance(profile.get("directory_contract"), dict)  # 拒绝非对象配置
        else {}  # 非法配置按无合同处理
    )

    # 原始目标根先通过边界合同，再参与文件系统路径拼接。
    str_primary_root: str = _safe_primary_root(dict_contract.get("primary_project_root"))  # 通过边界检查的结构目标根。

    # 未声明目标根时不能构造保守移动方案。
    if not str_primary_root:

        # 空映射表示结构门禁需要人工处理。
        return {}

    # 自动修复仅创建尚不存在的主项目目录。
    target = project / str_primary_root  # 计划中的迁入目标

    # 目标及其父级必须在真实项目树内，不能借由链接承载自动移动。
    if not _path_stays_inside_project(project, target):

        # 路径边界无法证明时交由人工处理，不生成修复候选。
        return {}

    # 目标已存在时移动可能覆盖用户内容，必须停止自动修复。
    if target.exists():

        # 已有目标交由人工确认具体合并方式。
        return {}

    # 已批准顶层根不应被误判为待迁移的旧工作区。
    set_allowed_roots: set[str] = {
        normalize_rel(item).split("/", 1)[0]  # 批准路径的顶层根
        for item in planned.get("allowed_top_level_roots", [])  # 计划允许的路径
        if normalize_rel(item)  # 过滤空路径声明
    }  # 已批准顶层目录集合

    # 只有一个未批准业务目录时才满足无歧义自动修复条件。
    list_candidates = []  # 潜在旧主项目目录

    # 稳定扫描工作区根，排除治理和已批准目录。
    for child in sorted(project.iterdir()):

        # 工具缓存与固定治理目录绝不能迁入业务主项目根。
        if child.name in SKIP_DIRS or child.name in {
            ".agents",  # 代理控制目录
            ".settings",  # 工作区设置目录
            "docs",  # 治理文档目录
            "dist",  # 发布历史目录
            "tests",  # 测试目录
            "ref",  # 参考材料目录
        }:

            # 保留成员不参与候选计数。
            continue

        # 顶层链接不能成为自动迁移来源。
        if _is_symbolic_link(child) or child.resolve(strict=False) != child.absolute():

            # 跳过可能指向项目外部的目录或文件链接。
            continue

        # 根级普通文件不能作为需要整体迁移的项目目录。
        if not child.is_dir():

            # 继续检查其他根成员。
            continue

        # 计划已允许的目录不属于结构漂移。
        if child.name in set_allowed_roots:

            # 已批准目录无需修复。
            continue

        # 剩余目录可能是接管前的旧主项目根。
        list_candidates.append(child)

    # 多个候选存在歧义，零候选表示没有可修复对象。
    if len(list_candidates) != 1 or not list_candidates[0].is_dir():

        # 保守策略拒绝猜测用户希望迁移哪个目录。
        return {}

    # 唯一目录候选可以进入项目类型一致性检查。
    path_candidate: Path = list_candidates[0]  # 待迁移旧项目目录

    # 技能项目必须由 SKILL.md 证明候选确实是技能根。
    str_kind: str = str(profile.get("kind", "")).strip().lower()  # 项目控制类型

    # 缺少技能身份文件时不能把普通目录当作技能项目迁移。
    if str_kind == "skill" and not (path_candidate / "SKILL.md").is_file():

        # 类型证据不足时要求人工处理。
        return {}

    # 候选源再次通过链接边界检查，缩小扫描与移动之间的竞态窗口。
    if not _path_stays_inside_project(project, path_candidate):

        # 源路径边界不明时不提供可执行迁移计划。
        return {}

    # 返回最小移动计划，执行阶段仍会再次运行结构门禁。
    return {
        "source": display_rel(path_candidate, project),  # 工作区相对源目录
        "target": str_primary_root,  # 合同声明目标目录
    }

# 接管候选扫描只选择主项目根之外且不属于治理保留面的成员。
def takeover_candidates(project: Path, planned: dict) -> list[Path]:
    """收集接管既有项目时需要迁移到主项目根的成员。

    参数：project 为工作区根，planned 为批准目录计划。
    返回：按名称稳定排序且未与目标冲突的候选路径列表。
    """

    # 计划中的主项目根决定所有接管成员的迁入目标。
    str_primary_root: str = _safe_primary_root(planned.get("primary_project_root"))  # 接管目标必须位于当前工作区内。

    # 工作区根自身若为链接，任何顶层成员都不能形成可靠接管边界。
    if _is_symbolic_link(project):

        # 直接拒绝整个候选集合，避免解析后的真实目录被误接管。
        return []

    # 未配置主项目根时不能推断安全迁移边界。
    if not str_primary_root:

        # 空列表表示不存在可安全计算的候选。
        return []

    # 顶层主项目目录本身不得再次成为迁移候选。
    str_top_primary = str_primary_root.split("/", 1)[0]  # 主项目根顶层名称

    # 治理、发布、测试和主项目目录始终保留在工作区根。
    set_preserve_roots = {
        ".agents",  # 代理控制配置
        ".settings",  # 本地与远程设置
        "docs",  # 项目治理文档
        "dist",  # 版本化发布历史
        "tests",  # 项目测试根目录
        "ref",  # 参考输入与审查材料
        str_top_primary,  # 已批准主项目目录
    }  # 接管时保留的根目录集合

    # 候选列表保持 Path 对象，供执行阶段直接移动。
    list_candidates: list[Path] = []  # 待迁入主项目根的成员

    # 链接目标即使也位于工作区内，也不能被当作独立迁移源。
    set_link_targets: set[Path] = set()  # 顶层链接解析后的目标集合

    # 先收集顶层链接目标，覆盖链接与真实目标同时出现在工作区的情况。
    for path_entry in sorted(project.iterdir()):

        # 非链接成员不改变接管候选边界。
        if not _is_symbolic_link(path_entry):

            # 继续扫描其他根成员。
            continue

        # 解析失败时不加入集合，后续链接自身仍会被跳过。
        try:

            # 目标集合用于阻止重复迁移链接实际指向的目录。
            set_link_targets.add(path_entry.resolve(strict=False))

        # 解析链接失败时保持不确定目标不可迁移。
        except OSError:

            # 损坏链接没有可迁移目标，保持 fail-closed。
            continue

    # 稳定遍历根成员，确保迁移和错误顺序可复现。
    for child in sorted(project.iterdir()):

        # Git 缓存和工具生成目录沿用公共忽略策略。
        if child.name in SKIP_DIRS:

            # 忽略成员不属于项目交付结构。
            continue

        # 明确保留的治理目录不能迁入业务主项目根。
        if child.name in set_preserve_roots:

            # 治理保留目录留在工作区根，不进入业务迁移阶段。
            continue

        # 顶层链接不能被当作目录遍历或迁移来源。
        if _is_symbolic_link(child) or child.resolve(strict=False) != child.absolute():

            # 跳过链接，避免读取或移动其外部目标内容。
            continue

        # 链接目标本身也不参与迁移，避免同一内容被重复接管。
        if child.resolve(strict=False) in set_link_targets:

            # 该目录已经通过链接暴露，保留人工处理边界。
            continue

        # 根级代理说明和编辑器配置维持原位置。
        if child.is_file() and child.name in TAKEOVER_PRESERVE_ROOT_FILES:

            # 保留文件不进入迁移候选集。
            continue

        # 其余成员由 takeover_fix 在冲突检查后迁移。
        list_candidates.append(child)

    # 返回稳定排序的安全候选集合。
    return list_candidates

# 接管修复先保存既有治理证据，再把安全候选迁入批准的业务根目录。
def takeover_fix(project: Path) -> dict[str, Any]:
    """把既有工程或技能工作区迁移到批准的主项目目录。

    参数：project 为待接管工作区根目录。
    返回：包含批准状态、迁移成员和阻断原因的接管结果。
    异常：目录创建、移动或归档失败时传播对应文件系统异常。
    """

    # 读取项目身份，用于识别需要拆平的同名旧包装目录。
    profile = control_profile(project)  # 项目控制配置提供规范名称。

    # 优先采用已批准计划，缺失时根据当前配置生成同等结构契约。
    dict_planned: dict[str, Any] = load_planned(project) or planned_structure(project)  # 统一迁移依据。

    # 接管成员只能进入工作区内已证明安全的业务根。
    str_primary_root: str = _safe_primary_root(dict_planned.get("primary_project_root"))  # 后续目录操作只接收相对根。

    # 没有明确业务根时禁止猜测目标位置。
    if not str_primary_root:

        # 返回可审计的阻断结果，不执行任何目录变更。
        return {
            "project": str(project),  # 标识被检查的工作区。
            "moved": [],  # 阻断前没有迁移成员。
            "errors": [  # 明确缺失的必需结构契约。
                "takeover fix requires a configured primary_project_root"
            ],
            "archive_dir": "",  # 未触发治理归档。
        }

    # 顶层存在任一链接时，整个接管动作必须在移动前 fail-closed。
    list_top_level_links = [  # 当前工作区的顶层链接证据
        path_entry  # 具体链接路径
        for path_entry in sorted(project.iterdir())  # 稳定遍历工作区根成员
        if _is_symbolic_link(path_entry)  # 链接成员阻断全部迁移
    ]

    # 外部链接可能改变未批准目录的真实落点，禁止只跳过链接而迁移其他文件。
    if list_top_level_links:

        # 返回阻断证据，确保 source.txt 等普通候选仍留在原位置。
        return {
            "project": str(project),  # 被阻断的工作区根。
            "primary_project_root": str_primary_root,  # 已解析的业务根。
            "archive_dir": "",  # 阻断前不创建治理归档。
            "moved": [],  # fail-closed 不允许发生任何移动。
            "errors": [
                "takeover blocked by top-level symbolic link: "
                + ", ".join(display_rel(path_link, project) for path_link in list_top_level_links)
            ],
        }

    # 将批准的相对业务根解析到当前工作区内。
    target_root = project / str_primary_root  # 所有候选都迁入该目录。

    # 词法安全根仍需拒绝现有符号链接组件和解析后的外部目标。
    if not _path_stays_inside_project(project, target_root):

        # 边界失败发生在归档前，不创建目录、不保存治理副本或迁移成员。
        return {
            "project": str(project),  # 回显本次边界校验的工作区标识。
            "primary_project_root": str_primary_root,  # 回显批准根配置。
            "archive_dir": "",  # 此分支尚未创建治理归档目录。
            "moved": [],  # 边界失败前没有迁移成员。
            "errors": [
                "takeover primary_project_root must stay inside the project and contain no symbolic link"
            ],
        }

    # 空值表示本次接管前不存在需要归档的旧治理文件。
    str_archive_dir = ""  # 供结果载荷稳定返回字符串字段。

    # 发现旧目录治理文件时，先保存其完整历史再重建治理状态。
    if any(
        (project / rel).exists()  # 任一既有治理文件都要求归档。
        for rel in [  # 仅检查由目录治理器拥有的三个事实文件。
            DIR_MANAGER_MD,
            CURRENT_STRUCTURE,
            PLANNED_STRUCTURE,
        ]
    ):

        # 归档原因固定记录为接管重构，便于后续审计来源。
        dict_archive: dict[str, Any] = archive_dir_manager(  # 保存旧治理状态并返回归档位置。
            project,  # 归档当前工作区根的治理文件。
            reason="takeover directory restructuring",  # 记录变更动机。
        )

        # 提取归档路径作为接管结果证据。
        str_archive_dir = str(dict_archive.get("archive_dir", ""))  # 保持字段类型稳定。

    # 在移动前创建完整目标路径，已有目录可安全复用。
    target_root.mkdir(parents=True, exist_ok=True)  # 不覆盖其中既有成员。

    # 分别记录成功迁移和名称冲突，形成完整执行证据。
    list_moved: list[dict[str, str]] = []  # 每项描述一次源到目标移动。

    # 冲突和重建错误独立于成功迁移清单累计。
    list_errors: list[str] = []  # 冲突不终止其他独立候选的处理。

    # 项目规范名称用于识别工作区根下遗留的同名包装目录。
    project_name = str(profile.get("name", "")).strip()  # 空名称禁用拆平分支。

    # 按稳定顺序处理经过保留规则过滤的安全候选。
    for source in takeover_candidates(project, dict_planned):

        # 同名旧包装目录只迁移其子成员，避免产生重复嵌套层级。
        if source.is_dir() and project_name and source.name == project_name:

            # 稳定排序保证迁移日志和冲突顺序可复现。
            for child in sorted(source.iterdir()):

                # 子成员在批准业务根下保持原名称。
                target = target_root / child.name  # 计算拆平后的目标位置。

                # 目标已存在时保留双方并报告冲突，禁止隐式覆盖。
                if target.exists():

                    # 使用相对路径生成可移植的诊断信息。
                    list_errors.append(
                        f"takeover target already exists: "  # 冲突类别保持稳定。
                        f"{display_rel(target, project)}"  # 指向实际冲突目标。
                    )

                    # 当前冲突不影响同一包装目录中的其他子成员。
                    continue

                # 名称无冲突后执行同一工作区内的原子移动。
                child.rename(target)  # 保留子成员内容和元数据。

                # 记录实际完成的拆平移动，供调用方核对。
                list_moved.append(
                    {
                        "action": "move",  # 统一操作类型。
                        "source": display_rel(child, project),  # 原子成员位置。
                        "target": display_rel(target, project),  # 批准后的新位置。
                    }
                )

            # 所有可迁成员处理完成后，仅删除已经为空的旧包装层。
            if not any(source.iterdir()):

                # rmdir 只允许空目录，天然保护未迁移或冲突成员。
                source.rmdir()  # 清理冗余嵌套层级。

            # 包装目录已独立处理，不再作为整体候选移动。
            continue

        # 普通候选在业务根下保持其顶层名称。
        target = target_root / source.name  # 计算整体迁移目标。

        # 目标冲突时保留源成员，避免数据覆盖或合并歧义。
        if target.exists():

            # 将冲突追加到统一错误列表并继续检查其他候选。
            list_errors.append(
                f"takeover target already exists: "  # 提供稳定诊断前缀。
                f"{display_rel(target, project)}"  # 附加仓库相对目标路径。
            )

            # 跳过当前冲突源，继续处理互不依赖的候选。
            continue

        # 无冲突候选整体迁入批准业务根。
        source.rename(target)  # 同一文件系统内保留目录内容。

        # 保存普通候选的实际迁移证据。
        list_moved.append(
            {
                "action": "move",  # 统一操作语义。
                "source": display_rel(source, project),  # 原始根级位置。
                "target": display_rel(target, project),  # 新业务根位置。
            }
        )

    # 迁移完成后依据新结构重新初始化目录治理事实。
    init_result = init_dir_manager(project)  # 返回重建阶段的独立诊断。

    # 将重建错误合并到同一结果，避免成功移动掩盖治理失败。
    list_errors.extend(  # 保持原有移动证据并追加初始化错误。
        str(item)  # 规范化外部载荷中的错误文本。
        for item in init_result.get("errors", [])  # 缺失错误字段视为空列表。
    )

    # 返回迁移范围、归档位置和所有未解决冲突。
    return {
        "project": str(project),  # 被接管的工作区根。
        "primary_project_root": str_primary_root,  # 批准的业务根契约。
        "archive_dir": str_archive_dir,  # 旧治理证据归档位置。
        "moved": list_moved,  # 已完成的迁移清单。
        "errors": list_errors,  # 冲突与治理重建错误。
    }
