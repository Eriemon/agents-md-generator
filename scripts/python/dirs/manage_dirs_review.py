"""审查目录变更计划，并执行受治理的结构修复与接管迁移。"""

# 延迟解析类型注解，避免运行期求值联合类型。
from __future__ import annotations

# 标准库提供 JSON 编码、路径操作和通用类型。
import json
import re
from pathlib import Path
from typing import Any

# 公共治理模块提供忽略目录、JSON 读取和用户决策载荷。
from agents_common import SKIP_DIRS, read_json
from agents_decisions import decision_request

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
    TAKEOVER_PRESERVE_ROOT_FILES,
    # 路径策略函数负责规范化、白名单和错误原因计算。
    allowed_path,
    archive_dir_manager,
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
        top = normalized.split("/", 1)[0]  # 源路径顶层目录

        # 关键目录只允许在自己的顶层边界内调整后代路径。
        if top in CRITICAL_PREFIXES:

            # 删除或缺少目标的迁移动作会移除关键目录。
            if not target_norm:

                # 无目标时不能证明关键目录仍位于批准边界。
                return f"{action} is blocked for critical directory `{normalized}`"

            # 目标顶层目录用于验证关键结构是否保持原边界。
            target_top = target_norm.split("/", 1)[0]  # 目标路径顶层目录

            # 跨顶层移动会改变关键目录的计划位置。
            if target_top != top:

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
    environment = (  # 空字符串也回退到 local。
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

    # 返回供本地和远程审查共享的稳定字段协议。
    return {
        "action": action,  # create、move、delete 或 rename。
        "environment": environment,  # 本地或远程审查路由值。
        "path": path,  # 变更源路径。
        "target": target,  # 可选目标路径。
        "artifact_state": artifact_state,  # 可选远程制品状态。
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
        invalid = invalid_path_reason(value)  # None 表示路径语法安全。

        # 非法原因按输入顺序保留，便于定位具体字段。
        if invalid:

            # 追加诊断但继续收集同一变更的其他证据。
            list_reasons.append(invalid)  # 保留检测器原始说明。

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
    runtime_reasons = remote_runtime_reasons(  # 可能返回多个独立阻断原因。
        str_action,  # 当前远程动作。
        str_path,  # 受管源路径。
        target,  # 可选迁移目标。
        remote_plan,  # 批准的部署计划。
        str_artifact_state,  # 远端运行制品生命周期状态。
    )

    # 仅在策略实际命中时登记规则标识。
    if runtime_reasons:

        # 保留策略返回的稳定原因顺序。
        list_reasons.extend(runtime_reasons)  # 合并全部运行时风险。

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
    critical = critical_move_reason(  # None 表示边界安全。
        str_action, str_path, target  # 组合动作与源目标边界。
    )

    # 专用边界原因优先于一般目标白名单说明。
    if critical:

        # 保存关键路径风险及命中规则。
        list_reasons.append(critical)  # 保留具体关键目录名称。

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
def review_change_item(
    change: Any,
    planned: dict[str, Any],
    remote_plan: dict[str, Any],
    list_reasons: list[str],
    set_path_classes: set[str],
    list_matched_rules: list[str],
) -> None:
    """审查一个原始变更条目并累计结果。

    参数：change 为原始条目，planned 为本地计划，remote_plan 为远程计划，
    list_reasons、set_path_classes 和 list_matched_rules 为共享结果集合。
    返回：无；所有诊断与证据写入传入集合。
    """

    # 每项变更必须是包含命名字段的 JSON 对象。
    if not isinstance(change, dict):

        # 非对象条目无法安全解释为目录动作。
        list_reasons.append(  # 保持既有公开诊断文本。
            "each change must be a JSON object"
        )

        # 当前条目不可继续解析。
        return

    # 规范化字段，避免各规则重复处理大小写和空白。
    dict_facts = change_facts(change)  # 环境规则共享同一字段事实。

    # 拒绝未声明的动作，防止规则对未知语义作出猜测。
    if dict_facts["action"] not in {"create", "move", "delete", "rename"}:

        # 记录用户提供的规范化动作值。
        list_reasons.append(  # 保持原有错误协议。
            f"unsupported action `{dict_facts['action']}`"
        )

        # 未知动作不进入路径和环境规则。
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
            remote_plan,
            list_reasons,
            set_path_classes,
            list_matched_rules,
        )

        # 远程条目完成后不再应用本地目录计划。
        return

    # 其他环境值延续既有行为，统一按本地变更审查。
    review_local_change(  # 本地计划和关键边界规则。
        dict_facts, planned, list_reasons, list_matched_rules
    )

# 结果构造集中维护批准和阻断两类公开 JSON 协议。
def build_change_review_result(
    list_reasons: list[str],
    set_path_classes: set[str],
    list_matched_rules: list[str],
    dry_run: bool,
) -> dict[str, Any]:
    """根据累计审查证据构造公开结果载荷。

    参数：list_reasons 为原因列表，set_path_classes 为路径类别，
    list_matched_rules 为规则列表，dry_run 为试运行标志。
    返回：字段完整且尚未附加 review_file 的结果映射。
    """

    # 没有阻断原因时批准目录变更。
    approved = not list_reasons  # 决策布尔值驱动后续字段。

    # 风险说明只在阻断结果中出现。
    list_risks = (  # 保持既有五项严重危害说明。
        []
        if approved  # 批准结果没有风险项。
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
        "approved": approved,  # 最终批准状态。
        "decision": "approved" if approved else "blocked",  # 决策枚举。
        "reasons": list_reasons,  # 按检查顺序保存原因。
        "risks": list_risks,  # 阻断时的危害说明。
        "path_classes": sorted(set_path_classes),  # 稳定排序的路径类别。
        "matched_rules": sorted(dict.fromkeys(list_matched_rules)),  # 去重规则。
        "force_confirmation_required": not approved,  # 阻断时要求明确确认。
        "force_override_archive_required": (  # 提供强制执行前归档位置模板。
            str(HISTORY_DIR_MANAGER / "YYYYMMDD-HHMMSS") if not approved else ""
        ),
        "user_message": (  # 阻断结果提供中文风险提示。
            ""
            if approved
            else "目录结构审查未通过，默认拒绝执行。若用户仍强制要求修改，必须明确确认强制执行该目录结构修改，并接受可能产生的严重危害。"
        ),
        "dry_run": dry_run,  # 回显调用方执行模式。
        "decision_request": (  # 批准时不构造交互请求。
            {}
            if approved
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

# 公开审查入口按“初始化、读取、逐项审查、构造、持久化”编排职责。
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

    # 非对象输入或非列表 changes 按空变更集处理，保持既有兼容行为。
    list_changes = (  # 提取候选变更列表。
        raw.get("changes", [])  # 从对象载荷读取变更序列。
        if isinstance(raw, dict)  # 仅对象载荷拥有 changes 字段。
        else []  # 非对象输入没有可审查变更。
    )

    # 非列表 changes 不能逐项解释，回退为空集合。
    if not isinstance(list_changes, list):

        # 空集合产生批准结果，与旧实现保持一致。
        list_changes = []  # 清除非法容器。

    # 加载批准目录计划及其远程部署子合同。
    planned = load_planned(project)  # 本地路径权威计划。

    # 远程部署子合同必须是对象才能参与路径授权。
    remote_plan = (  # 非对象远程配置按未规划处理。
        planned.get("remote_deployment", {})  # 读取远程计划对象。
        if isinstance(planned.get("remote_deployment"), dict)  # 验证映射类型。
        else {}  # 非对象配置不授权任何远程路径。
    )

    # 初始化跨变更共享的原因、类别与规则证据。
    list_reasons: list[str] = []  # 保持诊断发现顺序。

    # 路径类别集合用于去重本地和远程设置分类。
    set_path_classes: set[str] = set()  # 自动去重路径类别。

    # 命中规则保留发现顺序，结果构造阶段再稳定去重。
    list_matched_rules: list[str] = []  # 最终稳定去重排序。

    # 按输入顺序审查每个目录变更。
    for change in list_changes:

        # 单项职责负责验证、环境路由和证据累计。
        review_change_item(  # 不执行任何实际目录变更。
            change,
            planned,
            remote_plan,
            list_reasons,
            set_path_classes,
            list_matched_rules,
        )

    # 根据全部审查证据构造公开决策载荷。
    dict_result = build_change_review_result(  # 尚未附加证据文件路径。
        list_reasons,  # 全部阻断原因。
        set_path_classes,  # 已识别路径类别。
        list_matched_rules,  # 命中的治理规则。
        dry_run,  # 调用方试运行模式。
    )

    # 按 dry-run 模式附加或写入审查记录。
    persist_change_review(project, dict_result, dry_run)  # 原地补充 review_file。

    # 返回字段完整的最终审查结果。
    return dict_result

# 自动修复候选只接受“单一未批准目录迁入尚不存在的主项目根”场景。
def obvious_structure_fix_candidate(
    project: Path, profile: dict, planned: dict
) -> dict[str, str]:
    """识别能够安全自动执行的单一结构修复候选。

    参数：project 为项目根，profile 为控制配置，planned 为批准目录计划。
    返回：候选动作字段；不存在唯一保守候选时返回空映射。
    """

    # 控制配置中的目录合同是主项目根的权威声明。
    contract = (  # 当前项目目录合同
        profile.get("directory_contract", {})  # 有效目录合同对象
        if isinstance(profile.get("directory_contract"), dict)  # 拒绝非对象配置
        else {}  # 非法配置按无合同处理
    )

    # 规范化目标根，防止路径表示差异影响存在性检查。
    primary_root = normalize_rel(  # 自动修复目标根
        str(contract.get("primary_project_root", "")).strip()  # 合同声明目标根
    )

    # 未声明目标根时不能构造保守移动方案。
    if not primary_root:

        # 空映射表示结构门禁需要人工处理。
        return {}

    # 自动修复仅创建尚不存在的主项目目录。
    target = project / primary_root  # 计划中的迁入目标

    # 目标已存在时移动可能覆盖用户内容，必须停止自动修复。
    if target.exists():

        # 已有目标交由人工确认具体合并方式。
        return {}

    # 已批准顶层根不应被误判为待迁移的旧工作区。
    allowed_roots = {
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

        # 根级普通文件不能作为需要整体迁移的项目目录。
        if not child.is_dir():

            # 继续检查其他根成员。
            continue

        # 计划已允许的目录不属于结构漂移。
        if child.name in allowed_roots:

            # 已批准目录无需修复。
            continue

        # 剩余目录可能是接管前的旧主项目根。
        list_candidates.append(child)

    # 多个候选存在歧义，零候选表示没有可修复对象。
    if len(list_candidates) != 1 or not list_candidates[0].is_dir():

        # 保守策略拒绝猜测用户希望迁移哪个目录。
        return {}

    # 唯一目录候选可以进入项目类型一致性检查。
    candidate = list_candidates[0]  # 待迁移旧项目目录

    # 技能项目必须由 SKILL.md 证明候选确实是技能根。
    kind = str(profile.get("kind", "")).strip().lower()  # 项目控制类型

    # 缺少技能身份文件时不能把普通目录当作技能项目迁移。
    if kind == "skill" and not (candidate / "SKILL.md").is_file():

        # 类型证据不足时要求人工处理。
        return {}

    # 返回最小移动计划，执行阶段仍会再次运行结构门禁。
    return {
        "source": display_rel(candidate, project),  # 工作区相对源目录
        "target": primary_root,  # 合同声明目标目录
    }

# 接管候选扫描只选择主项目根之外且不属于治理保留面的成员。
def takeover_candidates(project: Path, planned: dict) -> list[Path]:
    """收集接管既有项目时需要迁移到主项目根的成员。

    参数：project 为工作区根，planned 为批准目录计划。
    返回：按名称稳定排序且未与目标冲突的候选路径列表。
    """

    # 计划中的主项目根决定所有接管成员的迁入目标。
    primary_root = normalize_rel(  # 接管迁移目标根
        str(planned.get("primary_project_root", "")).strip()  # 计划声明的主项目根
    )

    # 未配置主项目根时不能推断安全迁移边界。
    if not primary_root:

        # 空列表表示不存在可安全计算的候选。
        return []

    # 顶层主项目目录本身不得再次成为迁移候选。
    top_primary = primary_root.split("/", 1)[0]  # 主项目根顶层名称

    # 治理、发布、测试和主项目目录始终保留在工作区根。
    set_preserve_roots = {
        ".agents",  # 代理控制配置
        ".settings",  # 本地与远程设置
        "docs",  # 项目治理文档
        "dist",  # 版本化发布历史
        "tests",  # 项目测试根目录
        "ref",  # 参考输入与审查材料
        top_primary,  # 已批准主项目目录
    }  # 接管时保留的根目录集合

    # 候选列表保持 Path 对象，供执行阶段直接移动。
    list_candidates: list[Path] = []  # 待迁入主项目根的成员

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
    planned = load_planned(project) or planned_structure(project)  # 统一迁移依据。

    # 规范化目标根，避免空白或路径表示差异绕过前置检查。
    primary_root = normalize_rel(  # 迁移目标必须采用仓库相对路径。
        str(planned.get("primary_project_root", "")).strip()  # 读取门禁要求的业务根。
    )

    # 没有明确业务根时禁止猜测目标位置。
    if not primary_root:

        # 返回可审计的阻断结果，不执行任何目录变更。
        return {
            "project": str(project),  # 标识被检查的工作区。
            "moved": [],  # 阻断前没有迁移成员。
            "errors": [  # 明确缺失的必需结构契约。
                "takeover fix requires a configured primary_project_root"
            ],
            "archive_dir": "",  # 未触发治理归档。
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
        archive = archive_dir_manager(  # 保存旧治理状态并返回归档位置。
            project,  # 归档当前工作区根的治理文件。
            reason="takeover directory restructuring",  # 记录变更动机。
        )

        # 提取归档路径作为接管结果证据。
        str_archive_dir = str(archive.get("archive_dir", ""))  # 保持字段类型稳定。

    # 将批准的相对业务根解析到当前工作区内。
    target_root = project / primary_root  # 所有候选都迁入该目录。

    # 在移动前创建完整目标路径，已有目录可安全复用。
    target_root.mkdir(parents=True, exist_ok=True)  # 不覆盖其中既有成员。

    # 分别记录成功迁移和名称冲突，形成完整执行证据。
    list_moved: list[dict[str, str]] = []  # 每项描述一次源到目标移动。

    # 冲突和重建错误独立于成功迁移清单累计。
    list_errors: list[str] = []  # 冲突不终止其他独立候选的处理。

    # 项目规范名称用于识别工作区根下遗留的同名包装目录。
    project_name = str(profile.get("name", "")).strip()  # 空名称禁用拆平分支。

    # 按稳定顺序处理经过保留规则过滤的安全候选。
    for source in takeover_candidates(project, planned):

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
        "primary_project_root": primary_root,  # 批准的业务根契约。
        "archive_dir": str_archive_dir,  # 旧治理证据归档位置。
        "moved": list_moved,  # 已完成的迁移清单。
        "errors": list_errors,  # 冲突与治理重建错误。
    }

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
    approved = not list_reasons  # 布尔值驱动所有响应字段。

    # 返回机器决策、人工说明和可选修复计划的完整协议。
    return {
        "project": str(project),
        "approved": approved,
        "decision": "approved" if approved else "blocked",
        "reasons": list_reasons,
        "default_confirmation": "yes",
        "recommended_option": "yes",
        "auto_fix_plan": list_auto_fix_plan,
        "requires_user_confirmation": not approved,
        "user_message": "" if approved else "目录结构不符合治理契约，默认应先按规范整理/迁移。若继续，请明确确认是否执行结构修复，默认推荐“是”。",
        "decision_request": {} if approved else decision_request(
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
    planned = load_planned(project) or planned_structure(project)  # 统一比较基准。

    # 扫描当前目录事实并生成全部结构偏差。
    list_reasons = structure_gate_findings(scan_structure(project), planned)  # 当前结构诊断。

    # 自动修复计划只承载经保守检测器证明无歧义的动作。
    list_auto_fix_plan: list[dict[str, str]] = []  # 默认要求人工规范化。

    # 检查是否恰有一个可安全移动的明显结构候选。
    dict_candidate = obvious_structure_fix_candidate(  # 空字典表示不可自动处理。
        project,  # 在受管工程内寻找明显嵌套候选。
        profile,  # 项目名称辅助识别嵌套目录。
        planned,  # 提供批准目标根。
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
    planned = load_planned(project)  # 缺失计划时不会产生修复候选。

    # 计算唯一可证明安全的源到目标移动。
    dict_candidate = obvious_structure_fix_candidate(  # 空字典表示需人工处理。
        project,  # 待检查的工作区根。
        profile,  # 用于识别项目同名目录。
        planned,  # 提供批准的主项目根。
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
