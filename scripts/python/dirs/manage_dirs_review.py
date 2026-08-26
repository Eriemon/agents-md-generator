"""审查目录变更计划，并执行受治理的结构修复与接管迁移。"""

# 延迟解析类型注解，避免运行期求值联合类型。
from __future__ import annotations

# 标准库提供 JSON 编码、路径操作和通用类型。
import json
import re
from pathlib import Path
from typing import Any

# 公共治理模块提供 JSON 读取和用户决策载荷。
from agents_common import read_json
from agents_decisions import decision_request
from manage_dirs_upload import build_upload_manifest, review_upload_item
# 兼容入口独立承载旧参数校验，核心编排继续留在本模块。
from manage_dirs_compat import review_change_item

# 远程目录策略负责路径白名单、运行时保护和设置文件边界。
from manage_dirs_remote import (
    allowed_remote_path,
    remote_path_classes,
    remote_runtime_reasons,
    remote_workspace_settings_reason,
)

# 状态模块是目录快照、计划、归档和路径规范化的事实来源。
from manage_dirs_state import (
    # 快照路径与受保护前缀定义目录治理的持久化边界。
    CHANGE_REVIEWS,
    CRITICAL_PREFIXES,
    CURRENT_STRUCTURE,
    DIR_MANAGER_MD,
    GOVERNANCE_PREFIXES,
    HISTORY_DIR_MANAGER,
    PLANNED_STRUCTURE,
    # 路径策略函数负责规范化、白名单和错误原因计算。
    allowed_path,
    control_profile,
    display_rel,
    init_dir_manager,
    invalid_path_reason,
    load_planned,
    # 扫描与归档函数维护当前结构和历史审计证据。
    nested_workspace_artifact_reason,
    normalize_rel,
    planned_structure,
    scan_structure,
    stamp,
    unapproved_root_files,
)

# 接管候选和迁移入口从拆分模块导入，保持旧调用方可直接导入。
from manage_dirs_structure import (
    _path_stays_inside_project,
    obvious_structure_fix_candidate,
    takeover_candidates,
    takeover_fix,
)

# 工作区设置策略区分本地凭据配置与可部署远程配置。
from workspace_settings_policy import (
    workspace_settings_location_reason,
    workspace_settings_path_classes,
)

# 关键路径检查在执行目录审查前统一生成不可绕过的阻断原因。
def critical_move_reason(action: str, path: str, target: str | None) -> str | None:
    """判断目录变更是否触碰关键或治理路径边界。

    参数：action 为变更动作，path 为源路径，target 为可选目标路径。
    返回：阻断原因；变更未触碰关键边界时返回 None。
    """

    # 规范源路径以便与治理前缀进行稳定比较。
    normalized = normalize_rel(path)  # 规范化源相对路径

    # 仅移动和重命名动作可能携带目标路径。
    target_norm = normalize_rel(target or "") if target else ""  # 规范化目标相对路径

    # 治理控制面中的任意子路径都禁止普通目录变更。
    for protected in GOVERNANCE_PREFIXES:

        # 精确前缀和其后代路径采用同一保护策略。
        if normalized == protected or normalized.startswith(protected + "/"):

            # 错误保留动作与规范路径，供审查载荷直接展示。
            return f"{action} is blocked for protected governance path `{normalized}`"

    # 创建动作不迁移现有关键目录，无需检查目标边界。
    if action in {"move", "rename", "delete"}:

        # Python 生成缓存不是关键根本身，可在非治理路径中安全清理。
        if action == "delete" and normalized.split("/")[-1] == "__pycache__":

            # 精确末级目录例外不放宽 tests、docs 等真实关键根删除。
            return None

        # 顶层目录决定当前路径是否属于关键项目结构。
        str_top: str = normalized.split("/", 1)[0]  # 源路径顶层目录

        # 关键目录只允许在自己的顶层边界内调整后代路径。
        if str_top in CRITICAL_PREFIXES:

            # 删除或缺少目标的迁移动作会移除关键目录。
            if not target_norm:

                # 无目标时不能证明关键目录仍位于批准边界。
                return f"{action} is blocked for critical directory `{normalized}`"

            # 目标顶层目录用于验证关键结构是否保持原边界。
            target_top = target_norm.split("/", 1)[0]  # 目标路径顶层目录

            # 跨顶层移动会改变关键目录的计划位置。
            if target_top != str_top:

                # 明确指出源路径越出计划边界的风险。
                return f"{action} would move critical directory `{normalized}` outside its planned boundary"

    # 未命中治理或关键目录规则时允许后续通用审查继续。
    return None

# 解析单项变更时统一规范化动作、环境和可选目标字段。
def change_facts(change: dict[str, Any]) -> dict[str, Any]:
    """把原始变更对象转换为目录规则使用的规范字段。

    参数：change 为单项目录变更对象。
    返回：包含动作、环境、源路径、目标路径和制品状态的字段映射。
    """

    # 动作名称使用小写形式匹配公开动作集合。
    action = str(change.get("action", "")).strip().lower()  # 规范化动作值。

    # 未声明环境时按本地目录变更处理。
    str_environment: str = (  # 空字符串也回退到 local。
        str(change.get("environment", "local")).strip().lower()  # 读取环境文本。
        or "local"  # 空环境采用本地治理。
    )

    # 源路径保留用户提供的相对表示，后续规则各自规范化。
    path = str(change.get("path", "")).strip()  # 空值由路径规则诊断。

    # None 表示动作没有目标字段，空字符串仍保留为显式目标。
    target = (  # 区分缺失目标与空目标。
        str(change.get("target", "")).strip()  # 读取显式目标文本。
        if change.get("target") is not None  # 保留显式空目标。
        else None  # 缺失字段保持无目标语义。
    )

    # 远程运行时治理使用规范化制品状态。
    artifact_state = (  # 本地规则忽略该字段。
        str(change.get("artifact_state", "")).strip().lower()  # 规范状态文本。
    )

    # 上传声明的本地源路径复用普通变更路径作为默认值。
    local_path = str(change.get("local_path", path)).strip()  # 上传源路径。

    # 上传声明的远程目标路径复用显式目标作为默认值。
    remote_path = str(change.get("remote_path", target or "")).strip()  # 上传目标路径。

    # 上传条目类型统一使用小写形式参与合同校验。
    str_kind: str = str(change.get("kind", "")).strip().lower()  # 上传条目类型。

    # 上传用途保留用户说明供审查证据回显。
    str_purpose: str = str(change.get("purpose", "")).strip()  # 上传用途说明。

    # 上传需求引用保留用户提供的治理追踪标识。
    str_requirement_ref: str = str(change.get("requirement_ref", "")).strip()  # 上传需求或计划引用。

    # 返回供本地和远程审查共享的稳定字段协议。
    return {
        "action": action,  # create、move、delete、rename 或 upload。
        "environment": str_environment,  # 本地或远程审查路由值。
        "path": path,  # 变更源路径。
        "target": target,  # 可选目标路径。
        "artifact_state": artifact_state,  # 可选远程制品状态。
        "local_path": local_path,  # 上传本地源路径。
        "remote_path": remote_path,  # 上传远程目标路径。
        "kind": str_kind,  # 输出上传条目类型。
        "purpose": str_purpose,  # 上传用途。
        "requirement_ref": str_requirement_ref,  # 上传需求引用。
    }

# 通用路径检查在环境专属规则之前执行，并累计路径类别证据。
def review_common_paths(
    facts: dict[str, Any], list_reasons: list[str], set_path_classes: set[str]
) -> None:
    """检查变更路径语法并登记工作区设置类别。

    参数：facts 为规范变更字段，list_reasons 为共享原因列表，set_path_classes 为类别集合。
    返回：无；通过传入集合累计审查证据。
    """

    # 提取源和目标，保持目标缺失语义。
    str_path = str(facts["path"])  # 规范源路径。

    # 目标保留 None 以区分未提供字段。
    target = facts["target"]  # None 或规范目标字符串。

    # 每个实际参与动作的路径都必须通过通用安全检查。
    for value in [str_path, target] if target else [str_path]:

        # 路径检测器返回首个可解释的非法原因。
        str_invalid_reason: str | None = invalid_path_reason(value)  # None 表示路径语法安全。

        # 非法原因按输入顺序保留，便于定位具体字段。
        if str_invalid_reason:

            # 追加诊断但继续收集同一变更的其他证据。
            list_reasons.append(str_invalid_reason)  # 保留检测器原始说明。

    # 源路径存在时识别本地配置文件类别。
    if str_path:

        # 类别集合去重，不改变原因顺序。
        set_path_classes.update(  # 登记 local、remote 或 server-list 类别。
            workspace_settings_path_classes(str_path)
        )

    # 显式目标也需要相同的配置类别识别。
    if target:

        # 目标路径可能把本地配置迁移到禁止位置。
        set_path_classes.update(  # 合并目标配置类别。
            workspace_settings_path_classes(target)
        )

# 远程审查覆盖部署白名单、设置文件边界和运行时制品约束。
def review_remote_change(
    facts: dict[str, Any],
    remote_plan: dict[str, Any],
    list_reasons: list[str],
    set_path_classes: set[str],
    list_matched_rules: list[str],
) -> None:
    """应用单项远程目录变更的治理规则。

    参数：facts 为变更字段，remote_plan 为部署计划，list_reasons 累计原因，
    set_path_classes 累计路径类别，list_matched_rules 累计命中规则。
    返回：无；审查结果写入传入集合。
    """

    # 提取远程规则需要的全部字段。
    str_action = str(facts["action"])  # 已验证的动作。

    # 远程源路径用于计划和设置边界检查。
    str_path = str(facts["path"])  # 远程源路径。

    # 可选目标仅参与移动和重命名规则。
    target = facts["target"]  # 可选远程目标。

    # 制品状态限定运行时目录的允许操作。
    str_artifact_state = str(facts["artifact_state"])  # 运行时制品状态。

    # 远程源路径类别用于区分部署制品和工作区设置。
    set_path_classes.update(  # 合并计划驱动的远程类别。
        remote_path_classes(str_path, remote_plan)
    )

    # 显式目标同样需要远程类别识别。
    if target:

        # 目标类别揭示跨边界移动风险。
        set_path_classes.update(  # 合并目标的远程类别。
            remote_path_classes(target, remote_plan)
        )

    # 源和目标都不能携带禁止同步的工作区设置。
    for candidate in [str_path, target] if target else [str_path]:

        # 空候选不会形成设置位置原因。
        reason = (  # 检测远程工作区配置泄漏。
            remote_workspace_settings_reason(candidate)  # 检查实际候选。
            if candidate  # 仅检查非空远程路径。
            else None  # 空候选没有远程设置风险。
        )

        # 相同设置原因只保留一次，避免源目标重复噪声。
        if reason and reason not in list_reasons:

            # 保存阻断原因及其命中规则。
            list_reasons.append(reason)  # 具体设置文件风险。

            # 登记远程设置边界规则命中。
            list_matched_rules.append(  # 公开规则标识。
                "remote-workspace-settings"
            )

    # 所有远程动作的源路径必须在部署计划中明确授权。
    if str_path and not allowed_remote_path(str_path, remote_plan):

        # 记录未规划源路径的规范化位置。
        list_reasons.append(  # 说明权威计划文件。
            f"remote path `{normalize_rel(str_path)}` is not listed in "
            "planned_structure.json remote_deployment planning"
        )

        # 登记远程源计划规则命中。
        list_matched_rules.append(  # 标识远程源白名单规则。
            "remote-path-must-be-planned"
        )

    # 移动与重命名的目标还必须独立满足远程计划。
    if str_action in {"move", "rename"} and target and not allowed_remote_path(
        target, remote_plan
    ):

        # 未规划目标会阻止跨目录迁移。
        list_reasons.append(  # 使用规范化目标生成诊断。
            f"remote target path `{normalize_rel(target)}` is not listed in "
            "planned_structure.json remote_deployment planning"
        )

        # 登记远程目标计划规则命中。
        list_matched_rules.append(  # 标识远程目标白名单规则。
            "remote-target-must-be-planned"
        )

    # 运行时目录和制品状态由专用远程策略统一判断。
    list_runtime_reasons: list[str] = remote_runtime_reasons(  # 可能返回多个独立阻断原因。
        str_action,  # 当前远程动作。
        str_path,  # 受管源路径。
        target,  # 可选迁移目标。
        remote_plan,  # 批准的部署计划。
        str_artifact_state,  # 远端运行制品生命周期状态。
    )

    # 仅在策略实际命中时登记规则标识。
    if list_runtime_reasons:

        # 保留策略返回的稳定原因顺序。
        list_reasons.extend(list_runtime_reasons)  # 合并全部运行时风险。

        # 登记运行时制品治理规则命中。
        list_matched_rules.append(  # 标记远程运行时治理命中。
            "remote-runtime-governance"
        )

# 本地审查保护设置位置、批准路径和关键目录边界。
def review_local_change(
    facts: dict[str, Any],
    planned: dict[str, Any],
    list_reasons: list[str],
    list_matched_rules: list[str],
) -> None:
    """应用单项本地目录变更的治理规则。

    参数：facts 为变更字段，planned 为目录计划，list_reasons 累计原因，
    list_matched_rules 累计命中规则。
    返回：无；审查证据写入传入列表。
    """

    # 提取本地规则使用的动作和路径。
    str_action = str(facts["action"])  # 已验证动作。

    # 本地源路径用于批准计划与关键边界检查。
    str_path = str(facts["path"])  # 本地源路径。

    # 可选目标只对移动和重命名动作生效。
    target = facts["target"]  # 可选本地目标。

    # 精确点号只在远程合同中表示配置的工作区根。
    if normalize_rel(str_path) == ".":

        # 本地审查不得批准以项目根为源的目录操作。
        list_reasons.append("local path `.` cannot target the project root")

        # 独立规则标识让审查证据明确指出根保护边界。
        list_matched_rules.append("local-project-root-protected")

    # 源目标都必须遵守工作区设置文件的位置约束。
    for candidate in [str_path, target] if target else [str_path]:

        # 空候选不产生设置位置诊断。
        reason = (  # 检测 local/remote 配置混放。
            workspace_settings_location_reason(candidate)  # 检查实际配置位置。
            if candidate  # 仅检查非空本地路径。
            else None  # 空候选没有本地设置风险。
        )

        # 去重相同原因，保持结果简洁稳定。
        if reason and reason not in list_reasons:

            # 保存设置位置阻断及规则证据。
            list_reasons.append(reason)  # 具体配置位置风险。

            # 登记本地设置位置规则命中。
            list_matched_rules.append(  # 本地配置边界标识。
                "workspace-settings-location"
            )

    # 新建路径必须属于批准目录结构。
    if str_action == "create" and str_path and not allowed_path(str_path, planned):

        # 未规划的新目录默认拒绝创建。
        list_reasons.append(  # 指向批准结构文件。
            f"new path `{normalize_rel(str_path)}` is not listed in "
            "planned_structure.json"
        )

        # 登记本地新建路径计划规则命中。
        list_matched_rules.append(  # 标识本地源计划规则。
            "local-path-must-be-planned"
        )

    # 关键治理目录不得被移出其批准边界。
    str_critical_reason: str | None = critical_move_reason(  # None 表示边界安全。
        str_action, str_path, target  # 组合动作与源目标边界。
    )

    # 专用边界原因优先于一般目标白名单说明。
    if str_critical_reason:

        # 保存关键路径风险及命中规则。
        list_reasons.append(str_critical_reason)  # 保留具体关键目录名称。

        # 登记关键目录边界规则命中。
        list_matched_rules.append(  # 标识关键边界规则。
            "local-critical-boundary"
        )

    # 移动和重命名目标必须落在批准结构内。
    if str_action in {"move", "rename"} and target and not allowed_path(target, planned):

        # 未规划目标会造成目录合同漂移。
        list_reasons.append(  # 输出规范化目标路径。
            f"target path `{normalize_rel(target)}` is not listed in "
            "planned_structure.json"
        )

        # 登记本地目标路径计划规则命中。
        list_matched_rules.append(  # 标识本地目标计划规则。
            "local-target-must-be-planned"
        )

# 单项编排负责动作验证，并把环境专属规则路由到对应职责。
def _review_change_item_context(dict_context: dict[str, Any]) -> None:
    """审查一个原始变更条目并累计结果。

    参数:
        dict_context: 包含项目、变更、计划和共享结果集合的审查上下文。
    返回:
        None；所有诊断与证据写入传入集合。
    """

    # 从统一上下文中读取当前项目锚点。
    path_project: Path = dict_context["project"]  # 当前项目根目录。

    # 从统一上下文中读取当前原始变更。
    obj_change: object = dict_context["change"]  # 当前原始变更条目。

    # 从统一上下文中读取本地目录授权基线。
    dict_planned: dict[str, Any] = dict_context["planned"]  # 本地目录计划。

    # 从统一上下文中读取远程部署授权基线。
    dict_remote_plan: dict[str, Any] = dict_context["remote_plan"]  # 远程部署子计划。

    # 从统一上下文中读取共享阻断原因容器。
    list_reasons: list[str] = dict_context["list_reasons"]  # 共享阻断原因列表。

    # 从统一上下文中读取共享路径类别集合。
    set_path_classes: set[str] = dict_context["set_path_classes"]  # 共享路径类别集合。

    # 从统一上下文中读取共享命中规则列表。
    list_matched_rules: list[str] = dict_context["list_matched_rules"]  # 共享命中规则列表。

    # 从统一上下文中读取可选的不可覆盖阻断容器。
    list_absolute_blockers: list[str] | None = dict_context.get("list_absolute_blockers")  # 可选不可覆盖阻断。

    # 从统一上下文中读取可选的上传证据容器。
    list_upload_reviews: list[dict[str, Any]] | None = dict_context.get("list_upload_reviews")  # 可选上传证据。

    # 每项变更必须是包含命名字段的 JSON 对象。
    if not isinstance(obj_change, dict):

        # 非对象条目无法安全解释为目录动作。
        list_reasons.append(  # 保持既有公开诊断文本。
            "each change must be a JSON object"
        )

        # 当前条目不可继续解析。
        return

    # 规范化字段，避免各规则重复处理大小写和空白。
    dict_facts = change_facts(obj_change)  # 环境规则共享同一字段事实。

    # 拒绝未声明的动作，防止规则对未知语义作出猜测。
    if dict_facts["action"] not in {"create", "move", "delete", "rename", "upload"}:

        # 记录用户提供的规范化动作值。
        list_reasons.append(  # 保持原有错误协议。
            f"unsupported action `{dict_facts['action']}`"
        )

        # 未知动作不进入路径和环境规则。
        return

    # 上传动作只走 manifest-only 审查，不复用目录移动规则。
    if dict_facts["action"] == "upload":

        # 将规范化字段转换为上传审查器所需的最小载荷。
        dict_upload_item = {  # 上传审查输入对象。
            "local_path": dict_facts["local_path"],  # manifest 解析使用的本地源。
            "remote_path": dict_facts["remote_path"],  # manifest 解析使用的远程目标。
            "kind": dict_facts["kind"],  # manifest 规则使用的条目类型。
            "purpose": dict_facts["purpose"],  # manifest 审查回显的用途。
            "requirement_ref": dict_facts["requirement_ref"],  # manifest 追踪使用的需求引用。
        }

        # 对上传载荷执行 manifest-only 目录授权审查。
        dict_upload = review_upload_item(  # 上传逐项审查结果。
            path_project,  # upload 审查的项目锚点。
            dict_upload_item,  # upload 审查的规范化输入。
            dict_remote_plan,  # upload 审查的远程授权基线。
        )

        # 调用方需要时保留逐项上传审查证据。
        if list_upload_reviews is not None:

            # 追加当前上传条目的完整审查结果。
            list_upload_reviews.append(dict_upload)

        # 将每个上传阻断转换成公开原因并保留不可覆盖证据。
        for str_blocker in dict_upload["blockers"]:

            # 上传原因使用统一前缀，便于上层区分目录规则。
            list_reasons.append(f"upload: {str_blocker}")

            # 不可覆盖列表只在调用方提供时追加。
            if list_absolute_blockers is not None:

                # 保留原始阻断文本供 force-confirmation 策略判断。
                list_absolute_blockers.append(str_blocker)

        # 上传条目已经完成专属审查，不再进入普通目录规则。
        return

    # 通用路径语法和设置类别在环境路由前完成。
    review_common_paths(  # 通过共享集合累计结果。
        dict_facts, list_reasons, set_path_classes
    )

    # 远程环境采用部署和运行时治理规则。
    if dict_facts["environment"] == "remote":

        # 路由到远程专属审查职责。
        review_remote_change(  # 保留远程规则的既有执行顺序。
            dict_facts,
            dict_remote_plan,
            list_reasons,
            set_path_classes,
            list_matched_rules,
        )

        # 远程条目完成后不再应用本地目录计划。
        return

    # 其他环境值延续既有行为，统一按本地变更审查。
    review_local_change(  # 本地计划和关键边界规则。
        dict_facts, dict_planned, list_reasons, list_matched_rules
    )

# 上传审查结果在此展开为后续 JSON 载荷使用的 manifest。
def _collect_upload_manifest(
    list_upload_reviews: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """从上传审查证据中提取字典形式的文件清单。

    参数:
        list_upload_reviews: 上传逐项审查结果列表。
    返回:
        所有上传条目中可安全展开的 manifest 文件列表。
    """

    # 初始化展开结果，缺失上传证据时返回空清单。
    list_manifest: list[dict[str, Any]] = []  # 已授权上传文件清单。

    # 逐项读取上传审查器产生的 manifest 字段。
    for dict_upload_review in list_upload_reviews or []:

        # 缺失 manifest 时按空列表处理，不产生隐式文件。
        value_manifest = dict_upload_review.get("manifest", [])  # 当前条目的 manifest 值。

        # 只有列表容器可以展开为文件清单。
        if isinstance(value_manifest, list):

            # 只保留字典条目，避免把标量混入公开 manifest。
            list_manifest.extend(  # 累计当前条目的有效文件。
                item for item in value_manifest if isinstance(item, dict)
            )

    # 返回跨上传条目合并后的清单。
    return list_manifest

# 根据累计审查证据构造公开结果载荷。
def build_change_review_result(
    list_reasons: list[str],
    set_path_classes: set[str],
    list_matched_rules: list[str],
    dry_run: bool,
    list_absolute_blockers: list[str] | None = None,
    list_upload_reviews: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """根据累计审查证据构造公开结果载荷。

    参数:
        list_reasons: 原因列表。
        set_path_classes: 路径类别集合。
        list_matched_rules: 命中规则列表。
        dry_run: 试运行标志。
        list_absolute_blockers: 不可覆盖上传阻断列表。
        list_upload_reviews: 上传逐项审查证据列表。
    返回:
        字段完整且尚未附加 review_file 的结果映射。
    """

    # 上传绝对阻断不允许通过 force-confirmation 绕过。
    list_absolute = list(dict.fromkeys(list_absolute_blockers or []))  # 不可覆盖阻断列表。

    # 复用 manifest 展开器生成稳定的上传文件清单。
    list_manifest = _collect_upload_manifest(list_upload_reviews)  # 上传清单汇总结果。

    # 没有阻断原因时批准目录变更。
    bool_approved: bool = not list_reasons  # 决策布尔值驱动后续字段。

    # 风险说明只在阻断结果中出现。
    list_risks = (  # 保持既有五项严重危害说明。
        []
        if bool_approved  # 批准结果没有风险项。
        else [  # 阻断结果公开固定风险集合。
            "Tests and imports can break because path references become stale.",  # 引用漂移风险。
            "Release packages can point at the wrong files or miss required assets.",  # 发布资产风险。
            "AGENTS.md scoped rules can stop applying to the files they were written for.",  # 规则失效风险。
            "Handoff and git management history links can become invalid.",  # 历史链接风险。
            "Skill installation can fail if bundled resources move unexpectedly.",  # 安装资源风险。
        ]
    )

    # 返回机器决策、风险证据和强制确认请求。
    return {
        "project": "<PROJECT_ROOT>",  # 避免审查记录泄漏绝对路径。
        "approved": bool_approved,  # 最终批准状态。
        "decision": "approved" if bool_approved else "blocked",  # 决策枚举。
        "reasons": list_reasons,  # 按检查顺序保存原因。
        "risks": list_risks,  # 阻断时的危害说明。
        "path_classes": sorted(set_path_classes),  # 稳定排序的路径类别。
        "matched_rules": sorted(dict.fromkeys(list_matched_rules)),  # 去重规则。
        "force_confirmation_required": not bool_approved,  # 阻断时要求明确确认。
        "force_override_allowed": not bool(list_absolute),  # 上传绝对阻断永不允许强制绕过。
        "absolute_blockers": list_absolute,  # 不可覆盖的上传阻断。
        "upload_reviews": list_upload_reviews or [],  # 上传条目审查证据。
        "manifest": list_manifest,  # 已批准上传文件的展开清单。
        "manifest_only": True,  # 明确声明不允许工作区打包上传。
        "force_override_archive_required": (  # 提供强制执行前归档位置模板。
            str(HISTORY_DIR_MANAGER / "YYYYMMDD-HHMMSS") if not bool_approved else ""
        ),
        "user_message": (  # 阻断结果提供中文风险提示。
            ""
            if bool_approved or list_absolute
            else "目录结构审查未通过，默认拒绝执行。若用户仍强制要求修改，必须明确确认强制执行该目录结构修改，并接受可能产生的严重危害。"
        ),
        "dry_run": dry_run,  # 回显调用方执行模式。
        "decision_request": (  # 批准时不构造交互请求。
            {}
            if bool_approved
            else decision_request(
                "force_confirmation",  # 稳定请求标识。
                question="目录结构审查未通过。是否明确强制执行该目录结构修改并接受严重风险？",  # 用户问题。
                options=[  # 默认拒绝或明确强制两种选择。
                    {
                        "label": "不强制执行",  # 安全选项文本。
                        "value": "deny",  # 拒绝协议值。
                        "description": "默认选项；停止目录变更并修改计划。",  # 行为说明。
                        "recommended": True,  # 默认推荐。
                    },
                    {
                        "label": "强制执行",  # 风险选项文本。
                        "value": "force",  # 强制协议值。
                        "description": "先归档 dir manager 状态，再由用户承担风险继续。",  # 前置条件。
                        "recommended": False,  # 非推荐选项。
                    },
                ],
                default="deny",  # 默认停止变更。
                risk="high",  # 强制目录变更属于高风险。
                next_action="archive dir manager state before any force-confirmed blocked directory mutation",  # 闭环动作。
                context={  # 交互层需要的完整证据。
                    "reasons": list_reasons,
                    "risks": list_risks,
                },
            )
        ),
    }

# 审查记录持久化独立于规则判断，dry-run 不产生文件副作用。
def persist_change_review(
    project: Path, dict_result: dict[str, Any], dry_run: bool
) -> None:
    """附加审查文件字段，并按执行模式保存结果。

    参数：project 为项目根，dict_result 为结果映射，dry_run 控制文件写入。
    返回：无；原地补充 review_file 字段。
    异常：目录创建或文件写入失败时传播对应文件系统异常。
    """

    # 试运行明确返回空路径，证明没有生成审查文件。
    if dry_run:

        # 保持公开结果始终包含 review_file 字段。
        dict_result["review_file"] = ""  # 空字符串表示未持久化。

        # dry-run 已完成，无需执行文件系统写入。
        return

    # 使用时间戳生成不可覆盖的审查记录路径。
    review_path = project / CHANGE_REVIEWS / f"review-{stamp()}.json"  # 证据文件。

    # 在写入前确保受管审查目录存在。
    review_path.parent.mkdir(parents=True, exist_ok=True)  # 可复用既有目录。

    # 以稳定键序和缩进保存机器可读结果。
    review_path.write_text(  # 写入完整审查证据。
        json.dumps(dict_result, indent=2, sort_keys=True),  # 确定性 JSON 文本。
        encoding="utf-8",  # 支持中文诊断。
    )

    # 文件成功写入后才公开其真实位置。
    dict_result["review_file"] = str(review_path)  # 调用方可追溯证据。

# 顶层 uploads 审查单独保持 manifest-only 证据边界。
def _review_top_level_uploads(
    project: Path,
    raw: Any,
    remote_plan: dict[str, Any],
) -> dict[str, Any]:
    """审查变更载荷中的顶层 uploads 字段。

    参数:
        project: 当前项目根目录。
        raw: 已读取的顶层 JSON 载荷。
        remote_plan: 远程部署子计划。
    返回:
        包含 reasons、absolute_blockers 和 reviews 的上传证据映射。
    """

    # 初始化顶层上传公开原因集合。
    list_reasons: list[str] = []  # 顶层上传公开原因。

    # 初始化顶层上传不可覆盖阻断集合。
    list_absolute_blockers: list[str] = []  # 顶层上传不可覆盖阻断。

    # 初始化顶层上传逐项证据集合。
    list_upload_reviews: list[dict[str, Any]] = []  # 顶层上传逐项证据。

    # 非对象载荷没有独立的 uploads 字段可审查。
    if not isinstance(raw, dict):

        # 返回空上传证据，顶层形状错误由 review_change 统一记录。
        return {
            "reasons": list_reasons,
            "absolute_blockers": list_absolute_blockers,
            "reviews": list_upload_reviews,
        }

    # 读取顶层上传声明，缺失字段按空列表处理。
    value_uploads = raw.get("uploads", [])  # 顶层上传声明。

    # 非数组 uploads 不能被静默降级为空清单。
    if "uploads" in raw and not isinstance(value_uploads, list):

        # 形状错误进入不可覆盖阻断集合。
        list_absolute_blockers.append("uploads must be a JSON array")

        # 公开原因沿用上传前缀，便于调用方统一展示。
        list_reasons.append("upload: uploads must be a JSON array")

    # 合法且非空的顶层上传声明才进入逐文件审查。
    elif value_uploads:

        # 顶层列表复用同一 manifest-only 审查器。
        dict_upload_manifest = build_upload_manifest(  # 顶层上传 manifest 结果。
            project,  # 顶层 manifest 的项目锚点。
            value_uploads,  # 经过形状校验的 upload 列表。
            remote_plan,  # 顶层 manifest 的授权基线。
        )

        # 保留上传逐项审查证据。
        list_upload_reviews.extend(  # 累计顶层上传审查结果。
            dict_upload_manifest["reviews"]
        )

        # 保留不可覆盖的上传阻断。
        list_absolute_blockers.extend(  # 累计顶层上传阻断。
            dict_upload_manifest["absolute_blockers"]
        )

        # 将不可覆盖阻断转换为公开上传原因。
        list_reasons.extend(  # 累计顶层上传原因。
            f"upload: {str_blocker}"
            for str_blocker in dict_upload_manifest["absolute_blockers"]
        )

    # 返回顶层上传的结构化证据。
    return {
        "reasons": list_reasons,
        "absolute_blockers": list_absolute_blockers,
        "reviews": list_upload_reviews,
    }

# 审查本地或远程目录变更并保存结构化证据。
def review_change(
    project: Path, input_path: str, *, dry_run: bool = False
) -> dict[str, Any]:
    """审查本地或远程目录变更载荷并保存结构化证据。

    参数：project 为项目根，input_path 为变更 JSON 路径，dry_run 控制是否写入审查记录。
    返回：包含批准状态、原因、风险、路径类别和决策请求的审查结果。
    异常：输入文件读取或审查记录写入失败时传播对应文件系统异常。
    """

    # 确保目录治理事实存在，再读取待审查输入。
    init_dir_manager(project)  # 初始化缺失的治理文件。

    # 输入路径按调用进程解析为绝对路径。
    raw = read_json(Path(input_path).resolve())  # 加载原始 JSON 载荷。

    # 非对象输入不能形成可审查的变更载荷，后续会保留阻断原因。
    list_changes = (  # 提取候选变更列表。
        raw.get("changes", [])  # 从对象载荷读取变更序列。
        if isinstance(raw, dict)  # 仅对象载荷拥有 changes 字段。
        else []  # 非对象输入没有可审查变更。
    )

    # 初始化跨变更共享的原因、类别与规则证据。
    list_reasons: list[str] = []  # 保持诊断发现顺序。

    # 非对象或非法 changes 必须 fail-closed，不能被空变更集掩盖。
    if not isinstance(raw, dict):

        # 顶层载荷不是对象时，无法验证任何变更合同。
        list_reasons.append("change review input must be a JSON object")

    # 对象载荷声明了非法 changes 类型时，拒绝静默降级。
    elif "changes" in raw and not isinstance(raw["changes"], list):

        # 公开原因说明非法容器形状。
        list_reasons.append("changes must be a JSON array")

    # 非列表 changes 不能逐项解释，回退为空集合。
    if not isinstance(list_changes, list):

        # 清除非法容器，避免后续把标量当作变更项迭代。
        list_changes = []  # 清除非法容器。

    # 加载批准目录计划及其远程部署子合同。
    dict_planned: dict[str, Any] = load_planned(project)  # 本地路径权威计划。

    # 远程部署子合同必须是对象才能参与路径授权。
    dict_remote_plan: dict[str, Any] = (  # 非对象远程配置按未规划处理。
        dict_planned.get("remote_deployment", {})  # 读取远程计划对象。
        if isinstance(dict_planned.get("remote_deployment"), dict)  # 验证映射类型。
        else {}  # 非对象配置不授权任何远程路径。
    )

    # 路径类别集合用于去重本地和远程设置分类。
    set_path_classes: set[str] = set()  # 自动去重路径类别。

    # 命中规则保留发现顺序，结果构造阶段再稳定去重。
    list_matched_rules: list[str] = []  # 最终稳定去重排序。

    # 上传审查拥有不可覆盖的阻断集合。
    list_absolute_blockers: list[str] = []  # 上传绝对阻断集合。

    # 上传审查拥有逐项证据集合。
    list_upload_reviews: list[dict[str, Any]] = []  # 上传逐项审查证据。

    # 按输入顺序审查每个目录变更。
    for change in list_changes:

        # 组合单项审查所需的共享上下文，避免调用参数顺序漂移。
        dict_item_context = {  # 单项目录变更审查上下文。
            "project": project,  # 上下文使用的项目锚点。
            "change": change,  # 上下文携带的原始变更。
            "planned": dict_planned,  # 上下文使用的本地授权基线。
            "remote_plan": dict_remote_plan,  # 上下文使用的远程授权基线。
            "list_reasons": list_reasons,  # 上下文回写的原因容器。
            "set_path_classes": set_path_classes,  # 上下文回写的路径集合。
            "list_matched_rules": list_matched_rules,  # 上下文回写的规则集合。
            "list_absolute_blockers": list_absolute_blockers,  # 上下文回写的绝对阻断。
            "list_upload_reviews": list_upload_reviews,  # 上下文回写的上传证据。
        }

        # 单项职责负责验证、环境路由和证据累计。
        _review_change_item_context(dict_item_context)  # 不执行任何实际目录变更。

    # 顶层 uploads 字段支持独立的 manifest-only 上传载荷。
    dict_top_level_uploads = _review_top_level_uploads(  # 顶层上传审查结果。
        project,  # 顶层审查使用的项目锚点。
        raw,  # 顶层审查读取的 JSON 原文。
        dict_remote_plan,  # 顶层审查使用的远程基线。
    )

    # 合并顶层上传公开原因。
    list_reasons.extend(dict_top_level_uploads["reasons"])

    # 合并顶层上传不可覆盖阻断。
    list_absolute_blockers.extend(dict_top_level_uploads["absolute_blockers"])

    # 合并顶层上传逐项证据。
    list_upload_reviews.extend(dict_top_level_uploads["reviews"])

    # 根据全部审查证据构造公开决策载荷。
    dict_result = build_change_review_result(  # 尚未附加证据文件路径。
        list_reasons,  # 全部阻断原因。
        set_path_classes,  # 已识别路径类别。
        list_matched_rules,  # 命中的治理规则。
        dry_run,  # 调用方试运行模式。
        list_absolute_blockers,  # 结果载荷接收的绝对阻断。
        list_upload_reviews,  # 结果载荷接收的上传证据。
    )

    # 按 dry-run 模式附加或写入审查记录。
    persist_change_review(project, dict_result, dry_run)  # 原地补充 review_file。

    # 返回字段完整的最终审查结果。
    return dict_result

# 功能目录检查器隔离 tests 一级目录的命名合同。
def append_test_feature_findings(
    list_reasons: list[str],
    list_directories: list[str],
    str_root: str,
    str_feature_pattern: str,
) -> None:
    """追加 tests 一级功能目录的命名违规。

    参数：
        list_reasons: 需要原位追加的布局诊断列表。
        list_directories: 规范化后的当前目录路径。
        str_root: 唯一合法的测试根目录名称。
        str_feature_pattern: 功能目录允许的完整正则模式。
    返回：无；诊断直接追加到 list_reasons。
    """

    # 只检查 tests 下第一层功能目录，文件深度由独立规则负责。
    for str_directory in list_directories:

        # 路径部分用于精确识别 tests/<feature> 层级。
        tuple_parts = str_directory.split("/")  # 当前目录的相对路径部分

        # 非功能目录层级无需参与功能名称判断。
        if len(tuple_parts) != 2 or tuple_parts[0] != str_root:

            # 跳过根外目录和更深的目录层级。
            continue

        # 不符合功能单词模式的目录无法表达测试职责。
        if not re.fullmatch(str_feature_pattern, tuple_parts[1]):

            # 诊断保留实际目录并声明所需命名语义。
            list_reasons.append(
                f"invalid-feature-folder: {str_directory}/ must use lowercase functional words"
            )

# Python 测试检查器隔离根级豁免和固定深度合同。
def append_test_python_findings(
    list_reasons: list[str],
    list_files: list[str],
    str_root: str,
    set_root_exemptions: set[str],
) -> None:
    """追加 Python 测试文件的根级和深度违规。

    参数：
        list_reasons: 需要原位追加的布局诊断列表。
        list_files: 规范化后的当前文件路径。
        str_root: 唯一合法的测试根目录名称。
        set_root_exemptions: 允许保留在 tests 根级的 Python 文件名。
    返回：无；诊断直接追加到 list_reasons。
    """

    # Python 测试文件必须位于 tests 根或恰好一层功能目录中。
    for str_file in list_files:

        # 文件路径部分支持根级豁免和功能目录深度判断。
        tuple_parts = str_file.split("/")  # 当前文件的相对路径部分

        # 非 tests Python 文件不属于当前布局门禁的扫描范围。
        if (
            not tuple_parts  # 空路径不能形成有效测试文件
            or tuple_parts[0] != str_root  # 排除 tests 根以外的文件
            or not str_file.endswith(".py")  # 只约束 Python 测试布局
        ):

            # 跳过非目标文件并继续扫描剩余结构事实。
            continue

        # tests 根级仅允许配置列出的初始化文件。
        if len(tuple_parts) == 2:

            # 未获豁免的 Python 文件必须进入对应功能目录。
            if tuple_parts[-1] not in set_root_exemptions:

                # 根级文件诊断给出目标 tests/<feature>/ 结构。
                list_reasons.append(
                    f"python-at-tests-root: {str_file} must move into tests/<feature>/"
                )

            # 根级文件完成豁免判断后无需再检查三段深度。
            continue

        # 功能测试文件必须精确匹配 tests/<feature>/*.py 三段结构。
        if len(tuple_parts) != 3:

            # 过深或异常路径统一报告固定深度合同。
            list_reasons.append(
                f"invalid-test-depth: {str_file} must match tests/<feature>/*.py"
            )

# 测试布局诊断器验证单一根目录和固定功能层级。
def tests_layout_findings(
    dict_current: dict[str, Any],
    dict_planned: dict[str, Any],
) -> list[str]:
    """返回根 tests、功能目录和 Python 文件深度诊断。

    参数：
        dict_current: 当前工作文件夹的目录与文件事实。
        dict_planned: 已批准的目录治理计划。
    返回：保持检查顺序的 tests 布局违规原因。
    """

    # 计划中的 tests_layout 是本检查的唯一策略来源。
    dict_layout = dict_planned.get("tests_layout", {})  # 根目录与功能分组布局合同

    # 未配置布局策略时保持旧项目的兼容行为。
    if not isinstance(dict_layout, dict) or not dict_layout:

        # 空原因列表表示当前项目不启用 tests 布局门禁。
        return []

    # 规范化根目录名称，空配置回退到固定 tests 合同。
    str_root = normalize_rel(str(dict_layout.get("required_root", "tests"))) or "tests"  # 唯一合法测试根

    # 当前目录事实统一为正斜杠相对路径，便于跨平台比较。
    list_directories = [
        normalize_rel(item)  # 规范化后的实际目录路径
        for item in dict_current.get("directories", [])  # 标准化计划比对所需的每个目录条目
    ]  # 当前工作文件夹的全部目录

    # 文件路径使用同一规范化规则，供 Python 深度检查复用。
    list_files = [
        normalize_rel(item)  # 规范化后的实际文件路径
        for item in dict_current.get("files", [])  # 标准化 Python 深度检查所需的每个文件条目
    ]  # 当前工作文件夹的全部文件

    # 受控验证快照可携带自身 tests 树，但不属于当前项目的测试根。
    list_excluded_roots: list[str] = []  # 不参与当前 tests 布局检查的受控目录

    # 按合同读取每个快照排除根，形成稳定的路径前缀集合。
    for item in dict_layout.get("excluded_roots", []):

        # 目录边界统一使用规范化相对路径，避免前后斜杠造成漏排除。
        str_excluded_root = normalize_rel(str(item)).rstrip("/")  # 当前受控排除根

        # 空配置不应改变默认的单一 tests 根合同。
        if str_excluded_root:

            # 保留声明顺序，便于结构诊断和计划复核稳定。
            list_excluded_roots.append(str_excluded_root)

    # 仅排除受控根及其后代，保留项目其他目录的完整结构证据。
    list_directories = [
        item  # 当前项目结构目录
        for item in list_directories  # 遍历已规范化目录
        if not any(  # 目录路径命中受控根时跳过目录布局检查
            item == str_excluded_root or item.startswith(str_excluded_root + "/")  # 目录边界命中判定
            for str_excluded_root in list_excluded_roots  # 对每个受控文件根执行路径前缀判断
        )
    ]

    # 文件事实使用同一排除边界，避免 Python 深度检查重新发现快照 tests。
    list_files = [
        item  # 当前项目结构文件
        for item in list_files  # 遍历已规范化文件
        if not any(  # 文件路径命中受控根时跳过文件深度检查
            item == str_excluded_root or item.startswith(str_excluded_root + "/")  # 文件边界命中判定
            for str_excluded_root in list_excluded_roots  # 逐项比较受控根前缀
        )
    ]

    # 任意层级同名 tests 都进入唯一根目录检查。
    list_test_roots = [
        item  # 名称等于目标测试根的目录路径
        for item in list_directories  # 检查每个实际目录的末级名称
        if item.split("/")[-1] == str_root  # 收集任意层级出现的 tests 同名目录
    ]  # 当前结构中发现的全部 tests 同名目录

    # 原因列表按缺失、位置、数量、功能名和文件深度依次累计。
    list_reasons: list[str] = []  # tests 布局诊断结果

    # 根目录不存在时报告固定且可测试的缺失代码。
    if str_root not in list_test_roots:

        # 缺失诊断明确指出必须创建的根级目录。
        list_reasons.append(
            f"tests-missing: required root directory {str_root}/ is missing"
        )

    # 所有非根级 tests 都必须迁移到唯一合法位置。
    for str_test_root in list_test_roots:

        # 根级目录自身满足位置合同，不产生重复诊断。
        if str_test_root != str_root:

            # 位置错误保留实际目录，便于生成迁移审查请求。
            list_reasons.append(
                f"tests-not-at-root: {str_test_root}/ must be {str_root}/"
            )

    # 即使一个位于根级，多个 tests 同名目录仍违反唯一性。
    if len(list_test_roots) > 1:

        # 数量诊断与逐目录位置诊断共同提供完整修复信息。
        list_reasons.append(
            "multiple-tests-roots: only one tests directory is allowed"
        )

    # 根级 Python 豁免通常只允许包初始化文件。
    set_root_exemptions = {
        str(item)  # 根级允许保留的 Python 文件名
        for item in dict_layout.get("root_python_exemptions", [])  # 读取批准的根级文件例外
    }  # tests 根级 Python 文件豁免集合

    # 功能目录正则强制使用可读的小写功能单词。
    str_feature_pattern = str(  # tests 一级功能目录必须满足的命名模式
        dict_layout.get("feature_pattern", r"^[a-z]+(?:_[a-z]+)*$")  # 默认小写功能单词模式
    )  # tests 一级功能目录命名正则

    # 功能目录名称和 Python 文件深度分别由单一职责检查器追加。
    append_test_feature_findings(
        list_reasons, list_directories, str_root, str_feature_pattern
    )

    # Python 文件位置检查独立于功能目录命名检查。
    append_test_python_findings(
        list_reasons, list_files, str_root, set_root_exemptions
    )

    # 返回全部 tests 布局问题，空列表表示结构通过。
    return list_reasons

# 结构诊断器比较批准计划与实际目录事实。
def structure_gate_findings(dict_current: dict[str, Any], dict_planned: dict[str, Any]) -> list[str]:
    """返回业务根、目录污染和根文件违规原因。

    参数：dict_current 为当前结构，dict_planned 为批准结构计划。
    返回：保持检查顺序的全部结构偏差原因。
    """

    # 按检查顺序累计所有结构偏差，避免首错掩盖后续问题。
    list_reasons: list[str] = []  # 空列表最终表示批准。

    # 测试布局先形成专用诊断，再继续执行通用目录白名单检查。
    list_reasons.extend(tests_layout_findings(dict_current, dict_planned))

    # 规范化批准的业务根，供存在性和包含关系检查复用。
    primary_root = normalize_rel(  # 目标保持仓库相对形式。
        str(dict_planned.get("primary_project_root", "")).strip()  # 提取计划声明。
    )

    # 仅在计划明确强制业务根且路径有效时检查其存在性。
    if dict_planned.get("enforce_primary_project_root") and primary_root:

        # 业务根本身或其任一后代存在，都证明根目录结构已经建立。
        if primary_root not in dict_current.get("directories", []) and not any(
            path.startswith(primary_root + "/")  # 后代路径隐含父根存在。
            for path in dict_current.get("directories", [])  # 遍历实际目录事实。
        ):

            # 缺失强制业务根是独立的结构阻断原因。
            list_reasons.append(
                f"required primary project root is missing: "  # 稳定诊断类别。
                f"{primary_root}/"  # 标识计划要求的相对目录。
            )

    # 检查每个实际目录是否属于批准结构或嵌套污染。
    for directory in dict_current.get("directories", []):

        # 统一目录分隔形式，确保规则匹配跨平台一致。
        normalized = normalize_rel(directory)  # 当前目录的仓库相对路径。

        # 空路径代表工作区根，不作为子目录漂移处理。
        if not normalized:

            # 跳过根本身并继续检查实际子目录。
            continue

        # 优先识别嵌套工作区或版本控制污染，提供更具体原因。
        nested_reason = nested_workspace_artifact_reason(  # 空值表示没有嵌套污染。
            normalized,  # 待检查的实际目录。
            dict_planned,  # 批准结构提供忽略和根路径语义。
        )

        # 嵌套污染已形成完整原因时，不再追加泛化违规描述。
        if nested_reason:

            # 保存具体污染证据。
            list_reasons.append(nested_reason)  # 保留检测器生成的上下文。

            # 当前目录已经分类，继续检查其余目录。
            continue

        # 非污染目录仍必须匹配批准路径规则。
        if not allowed_path(normalized, dict_planned):

            # 记录未被计划允许的实际目录。
            list_reasons.append(  # 诊断使用规范化相对路径。
                f"directory violates planned structure: {normalized}"
            )

    # 根级文件采用独立白名单检查，避免目录规则误判文件。
    for file_path in unapproved_root_files(dict_current, dict_planned):

        # 每个未批准根文件都形成可独立修复的原因。
        list_reasons.append(  # 保持扫描器提供的仓库相对路径。
            f"root-level file violates planned structure: {file_path}"
        )

    # 调用方使用原因列表构造交互决策和修复候选。
    return list_reasons

# 结构门禁载荷构造器统一机器决策与人工确认协议。
def structure_gate_payload(
    project: Path,
    list_reasons: list[str],
    list_auto_fix_plan: list[dict[str, str]],
) -> dict[str, Any]:
    """根据结构原因和修复候选生成完整门禁载荷。

    参数：project 为项目根，list_reasons 为偏差原因，list_auto_fix_plan 为安全动作。
    返回：保持既有字段、选项与提示文本的门禁载荷。
    """

    # 任一结构偏差都必须阻断并请求明确处理决策。
    bool_approved: bool = not list_reasons  # 布尔值驱动所有响应字段。

    # 返回机器决策、人工说明和可选修复计划的完整协议。
    return {
        "project": str(project),
        "approved": bool_approved,
        "decision": "approved" if bool_approved else "blocked",
        "reasons": list_reasons,
        "default_confirmation": "yes",
        "recommended_option": "yes",
        "auto_fix_plan": list_auto_fix_plan,
        "requires_user_confirmation": not bool_approved,
        "user_message": "" if bool_approved else "目录结构不符合治理契约，默认应先按规范整理/迁移。若继续，请明确确认是否执行结构修复，默认推荐“是”。",
        "decision_request": {} if bool_approved else decision_request(
            "structure_normalization",
            question="目录结构不符合治理契约。是否按推荐方案执行结构修复？",
            options=[
                {
                    "label": "是，执行修复",  # 推荐动作标签。
                    "value": "yes",  # 机器可读确认值。
                    "description": "默认选项；按 auto_fix_plan 或人工整理方案恢复治理结构。",  # 修复路径说明。
                    "recommended": True,  # 默认突出修复动作。
                },
                {
                    "label": "否，暂停",  # 保守动作标签。
                    "value": "no",  # 机器可读暂停值。
                    "description": "保留当前结构，暂停会修改工作区结构的操作。",  # 暂停边界说明。
                    "recommended": False,  # 暂停不作为默认建议。
                },
            ],
            default="yes",
            risk="high",
            next_action="run structure fix or manually normalize the work folder, then rerun structure-gate",
            context={"reasons": list_reasons, "auto_fix_plan": list_auto_fix_plan},
        ),
    }

# 结构门禁把批准计划、实际目录和保守修复候选汇总为统一决策载荷。
def structure_gate(project: Path) -> dict[str, Any]:
    """比较当前目录结构与批准计划并生成结构门禁结果。

    参数：project 为待验证项目根目录。
    返回：包含批准状态、漂移原因和可选修复候选的门禁载荷。
    异常：结构扫描或治理文件读取失败时传播对应文件系统异常。
    """

    # 项目没有启用控制配置时，目录治理保持显式放行。
    profile = control_profile(project)  # 非空配置才启用结构约束。

    # 未受管项目通过空诊断复用同一稳定载荷协议。
    if not profile:

        # 空原因和空计划形成批准结果。
        return structure_gate_payload(project, [], [])

    # 优先读取批准计划，缺失时从控制配置生成预期结构。
    dict_planned: dict[str, Any] = load_planned(project) or planned_structure(project)  # 统一比较基准。

    # 扫描当前目录事实并生成全部结构偏差。
    list_reasons = structure_gate_findings(scan_structure(project), dict_planned)  # 当前结构诊断。

    # 自动修复计划只承载经保守检测器证明无歧义的动作。
    list_auto_fix_plan: list[dict[str, str]] = []  # 默认要求人工规范化。

    # 检查是否恰有一个可安全移动的明显结构候选。
    dict_candidate = obvious_structure_fix_candidate(  # 空字典表示不可自动处理。
        project,  # 在受管工程内寻找明显嵌套候选。
        profile,  # 项目名称辅助识别嵌套目录。
        dict_planned,  # 提供批准目标根。
    )

    # 只有明确候选才进入公开自动修复计划。
    if dict_candidate:

        # 补充统一动作类型并保留候选的源目标证据。
        list_auto_fix_plan.append(  # 门禁本身不执行文件系统变更。
            {"action": "move", **dict_candidate}
        )

    # 载荷构造器保持批准与阻断分支的公开字段一致。
    return structure_gate_payload(project, list_reasons, list_auto_fix_plan)

# 自动修复只执行门禁识别出的单一、无歧义目录移动。
def apply_structure_fix(project: Path) -> dict[str, Any]:
    """执行结构门禁确认过的保守自动修复动作。

    参数：project 为需要修复的项目根目录。
    返回：包含执行状态、动作、源路径和目标路径的修复结果。
    异常：目录创建、移动或归档失败时传播对应文件系统异常。
    """

    # 读取项目身份，供保守候选识别逻辑判断目录语义。
    profile = control_profile(project)  # 项目控制配置可能为空。

    # 自动修复只信任已落盘的批准计划，不临时推导目标结构。
    dict_planned: dict[str, Any] = load_planned(project)  # 缺失计划时不会产生修复候选。

    # 计算唯一可证明安全的源到目标移动。
    dict_candidate = obvious_structure_fix_candidate(  # 空字典表示需人工处理。
        project,  # 待检查的工作区根。
        profile,  # 用于识别项目同名目录。
        dict_planned,  # 提供批准的主项目根。
    )

    # 独立累计成功动作和冲突错误，便于调用方审计部分结果。
    list_moved: list[dict[str, str]] = []  # 最多包含一个保守移动。

    # 冲突场景必须保留源和目标，禁止隐式覆盖。
    list_errors: list[str] = []  # 空列表表示执行阶段没有阻断。

    # 仅在门禁给出明确候选时进入文件系统变更阶段。
    if dict_candidate:

        # 将候选中的仓库相对源路径解析到当前项目。
        source = project / dict_candidate["source"]  # 已由候选生成器验证语义。

        # 将批准的相对目标路径解析到同一工作区。
        target = project / dict_candidate["target"]  # 移动不得越出项目根。

        # 执行前再次检查源和目标，阻断扫描后出现的链接竞态。
        if not _path_stays_inside_project(project, source) or not _path_stays_inside_project(
            project, target
        ):

            # 边界变化时不创建目录、不移动源路径。
            list_errors.append(
                "structure fix source or target contains a symbolic link or escapes the project"
            )

            # 边界失败只返回已记录的错误，不执行任何移动。
            return {
                "project": str(project),
                "moved": list_moved,
                "errors": list_errors,
            }

        # 预先创建目标父目录，但不创建或覆盖最终目标。
        target.parent.mkdir(parents=True, exist_ok=True)  # 支持尚未存在的业务根。

        # 目标存在时保留双方并返回明确冲突。
        if target.exists():

            # 使用仓库相对路径生成稳定、可移植的诊断。
            list_errors.append(
                f"structure fix target already exists: "  # 固定冲突类别。
                f"{display_rel(target, project)}"  # 标识实际目标位置。
            )

        # 只有目标不存在时才允许执行真实移动。
        else:

            # 无冲突时执行同一工作区内的保守移动。
            source.rename(target)  # 保留源目录内容及元数据。

            # 只在移动成功后记录候选，避免虚构执行证据。
            list_moved.append(dict_candidate)  # 返回原始门禁计划字段。

    # 返回执行结果；空动作表示没有可自动修复的结构。
    return {
        "project": str(project),  # 被检查或修复的工作区根。
        "moved": list_moved,  # 实际完成的保守移动。
        "errors": list_errors,  # 未覆盖的目标冲突。
    }
