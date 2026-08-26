"""审查远程逐项上传清单，并拒绝工作区整体或打包上传。"""

# 延迟类型注解求值，保持远程 Python 3.10 环境兼容。
from __future__ import annotations

# 上传清单只依赖哈希、JSON、路径和标准类型标注。
import hashlib
import json
from pathlib import Path
from typing import Any

# 远程目标必须通过既有目录治理计划验证。
from manage_dirs_remote import allowed_remote_path, normalize_rel

# 禁传源根覆盖仓库元数据、发布物和参考资料目录。
FORBIDDEN_SOURCE_ROOTS = (  # 上传源根的绝对禁传目录名。
    ".git",  # 防止把仓库内部索引和对象带到远端。
    "git",  # 防止把本地 Git 镜像目录误传到远端。
    "github",  # 防止把 GitHub 工作副本当作任务输入。
    "dist",  # 防止把版本化发布物绕过发布治理上传。
    "ref",  # 防止把参考资料树误当作执行输入。
)  # 这些目录命中后整项阻断。

# 常见归档后缀不能借改名绕过逐文件上传策略。
FORBIDDEN_ARCHIVE_SUFFIXES = (  # 上传载荷不得使用的归档容器后缀。
    ".zip",  # 阻止以 ZIP 包替代逐文件清单。
    ".tar",  # 拒绝 TAR 容器，要求上传者列出实际文件。
    ".tar.gz",  # 拒绝 gzip TAR 容器，保持清单可重算。
    ".tgz",  # 阻止以 TGZ 简写包替代逐文件清单。
    ".bundle",  # 阻止把 bundle 容器伪装成单项输入。
    ".archive",  # 阻止通用 archive 容器绕过清单审查。
)  # 命中后必须拆成独立文件项。

# 上传类型只允许任务需要的窄范围对象。
ALLOWED_UPLOAD_KINDS = (  # 清单允许的条目类型。
    "selected_file",  # 单个明确文件。
    "selected_directory",  # 已审查的窄目录。
    "task_input",  # 独立任务输入。
    "runtime_artifact",  # 已批准运行时制品。
)  # 上传类型集合。

# 解析项目内相对源路径，并拒绝越出项目根的路径。
def _relative_source(path_project: Path, raw_path: object) -> tuple[Path | None, str | None]:
    """解析项目内相对源路径，并拒绝越出项目根的路径。

    参数：path_project 为当前工作文件夹；raw_path 为上传载荷中的源路径。
    返回：项目内绝对路径与错误文本；合法时错误为 None。
    """

    # 空值和项目根本身都代表整体工作区上传。
    str_raw = str(raw_path or "").strip()  # 原始源路径文本。

    # 绝对路径、根锚定路径和盘符路径都不能进入 manifest-only 合同。
    path_raw = Path(str_raw)  # 用于识别源文本是否带外部路径锚点。

    # 只接受不携带本机路径语义的项目内相对源路径。
    if path_raw.anchor:

        # 返回明确诊断，避免调用方把绝对路径误认为窄范围源。
        return None, "upload source must be a relative path"

    # 工作区整体上传没有可接受的窄范围语义。
    if not str_raw or normalize_rel(str_raw) == ".":

        # 绝对阻断不能由 force confirmation 绕过。
        return None, "whole work folder upload is forbidden"

    # 所有后续相对路径判断都绑定解析后的项目根。
    path_project_resolved = path_project.resolve()  # 项目根绝对路径。

    # resolve 后再检查可消除 ../ 和符号链接造成的路径歧义。
    path_candidate = (path_project / str_raw).resolve()  # 候选源绝对路径。

    # 只有位于当前工作文件夹内的源才可进入清单展开。
    try:

        # relative_to 成功表示候选路径仍在治理边界内。
        path_candidate.relative_to(path_project_resolved)

    # 越出根目录的路径必须 fail-closed。
    except ValueError:

        # 错误中保留用户提交的原始路径便于修正。
        return None, f"upload source `{str_raw}` is outside the current work folder"

    # 返回已解析且仍在项目根内的候选路径。
    return path_candidate, None

# 检查源路径及其项目内相对部分的禁传根和归档后缀。
def _forbidden_reason(path_project: Path, path_candidate: Path) -> str | None:
    """检查源路径及其项目内相对部分的禁传根和归档后缀。

    参数：path_project 为项目根；path_candidate 为已解析的项目内路径。
    返回：禁传原因文本；允许时返回 None。
    """

    # 目录规则统一使用正斜杠相对路径。
    str_relative = normalize_rel(str(path_candidate.relative_to(path_project.resolve())))  # 项目内相对路径。

    # 分段检查可以阻止嵌套目录伪装成安全文件名。
    list_parts = str_relative.split("/") if str_relative else []  # 路径分段。

    # 任一禁传根命中都阻止整个上传条目。
    if any(str_part in FORBIDDEN_SOURCE_ROOTS for str_part in list_parts):

        # 报告命中的项目内路径，便于治理审计定位。
        return f"upload source `{str_relative}` contains forbidden source root"

    # 归档后缀检查使用小写文本，覆盖大小写变体。
    str_lower = str_relative.lower()  # 小写路径文本。

    # 归档容器不能作为单文件或目录展开结果。
    if str_lower.endswith(FORBIDDEN_ARCHIVE_SUFFIXES):

        # 明确说明该文件必须拆解为独立清单项。
        return f"derived archive `{str_relative}` cannot be uploaded"

    # 未命中禁传规则时交给后续文件类型检查。
    return None

# 把单文件或窄目录展开为稳定文件列表。
def _expand_directory_source(path_project: Path, path_source: Path) -> tuple[list[Path], list[str]]:
    """展开已确认的窄目录，并逐项检查子路径安全性。

    参数：path_project 为项目根；path_source 为待展开目录。
    返回：普通文件列表和目录扫描错误列表。
    """

    # 目录展开只保留普通文件，并按路径排序保证哈希稳定。
    list_files: list[Path] = []  # 目录内普通文件。

    # 递归候选必须逐项检查符号链接、禁传根和文件类型。
    list_errors: list[str] = []  # 目录扫描错误。

    # 按稳定路径顺序检查目录中的每一个候选对象。
    for path_item in sorted(path_source.rglob("*")):

        # 符号链接可能把清单带出项目治理边界。
        if path_item.is_symlink():

            # 即使链接目标看似安全也不能绕过显式路径审查。
            list_errors.append(f"upload source symlink is forbidden: `{path_item.name}`")

            # 当前链接已经违反边界，跳过后续普通文件检查。
            continue

        # 子路径同样必须通过禁传根和归档判定。
        path_item_error = _forbidden_reason(path_project, path_item)  # 子路径禁传原因。

        # 禁传根或归档命中时不把候选加入清单。
        if path_item_error:

            # 目录整体审查必须报告所有命中项。
            list_errors.append(path_item_error)

            # 当前候选已经有明确阻断原因，不再进入文件类型判断。
            continue

        # 目录只收集可计算远程内容摘要的普通文件，忽略空目录本身。
        if path_item.is_file():

            # 排序后的文件列表后续会生成确定性清单。
            list_files.append(path_item)

    # 返回目录审查证据，由上层决定整体是否批准。
    return list_files, list_errors

# 把文件或目录输入路由到对应的展开策略。
def _expand_source(path_project: Path, path_source: Path, str_kind: str) -> tuple[list[Path], list[str]]:
    """把单文件或窄目录展开为稳定文件列表。

    参数：path_project 为项目根；path_source 为源路径；str_kind 为上传类型。
    返回：可进入哈希清单的文件列表和展开错误列表。
    """

    # 展开过程会累计所有可修复的源路径问题。
    list_errors: list[str] = []  # 展开错误集合。

    # 缺失源不能生成可验证的内容哈希。
    if not path_source.exists():

        # 文件名足够定位缺失输入，又避免泄露无关绝对路径。
        return [], [f"upload source `{path_source.name}` does not exist"]

    # 目录本身先经过禁传根和归档检查。
    path_error = _forbidden_reason(path_project, path_source)  # 源路径禁传原因。

    # 命中源级禁传规则时仍保留错误，禁止生成部分清单。
    if path_error:

        # 上层会把该错误提升为不可覆盖阻断。
        list_errors.append(path_error)

    # selected_file 分支只返回一个明确的普通文件。
    if str_kind == "selected_file" or path_source.is_file():

        # 目录或已阻断文件都不能进入文件清单。
        list_files = [path_source] if not list_errors and path_source.is_file() else []  # 单文件结果。

        # 单文件分支不需要递归扫描。
        return list_files, list_errors

    # 只有窄目录类型可以继续递归展开。
    if str_kind != "selected_directory" or not path_source.is_dir():

        # 类型与实际源对象不一致时直接停止展开。
        list_errors.append("selected_directory must reference a directory")

        # 类型错误不允许回退到任意目录上传。
        return [], list_errors

    # 目录扫描由独立函数执行，保持本入口只负责类型路由。
    tuple_directory_result = _expand_directory_source(path_project, path_source)  # 窄目录结果元组。

    # 拆出目录文件和扫描错误，保持返回值契约稳定。
    tuple_list_files, tuple_list_directory_errors = tuple_directory_result  # 目录展开元组。

    # 把元组成员命名为后续返回值，避免隐含索引语义。
    list_files = tuple_list_files  # 窄目录普通文件。

    # 单独保留扫描错误，便于与源级错误合并。
    list_directory_errors = tuple_list_directory_errors  # 窄目录扫描错误。

    # 汇总目录扫描发现的所有阻断原因。
    list_errors.extend(list_directory_errors)

    # 返回窄目录的完整展开证据。
    return list_files, list_errors

# 读取远程计划中的上传策略，缺失策略时 fail-closed。
def _policy(remote_plan: dict[str, Any]) -> dict[str, Any]:
    """读取远程计划中的上传策略，缺失策略时 fail-closed。

    参数：remote_plan 为远程目录治理计划映射。
    返回：upload_policy 映射；缺失或类型不符时返回空映射。
    """

    # 只信任治理计划显式提供的策略对象。
    value_policy = remote_plan.get("upload_policy")  # 原始策略值。

    # 非映射策略不能默认放宽上传边界。
    if not isinstance(value_policy, dict):

        # 空映射会在单项审查中触发 manifest-only 阻断。
        return {}

    # 返回已验证类型的策略映射。
    return value_policy

# 为一个明确文件生成目标路径、大小和内容哈希。
def _manifest_entry(path_project: Path, path_source: Path, str_remote: str) -> dict[str, Any]:
    """为一个明确文件生成目标路径、大小和内容哈希。

    参数：path_project 为项目根；path_source 为普通文件；str_remote 为远程目标。
    返回：包含源路径、远程路径、大小和 SHA-256 的 manifest 条目。
    """

    # 哈希读取只对已经通过路径审查的普通文件执行。
    bytes_content = path_source.read_bytes()  # 文件内容字节。

    # 源路径写入清单时保持项目内相对表示。
    str_relative = normalize_rel(str(path_source.relative_to(path_project.resolve())))  # 清单源路径。

    # 远程目标统一成目录治理使用的相对格式。
    str_target = normalize_rel(str_remote)  # 清单远程路径。

    # 目录目标以源文件名结尾时补齐最后一级文件名。
    if path_source.is_file() and str_target.endswith("/"):

        # 单文件上传仍然保持用户指定的远程目录语义。
        str_target = f"{str_target}{path_source.name}"  # 完整远程文件路径。

    # 返回可审计且可重算的内容摘要。
    return {
        "source": str_relative,
        "remote_path": str_target,
        "size": len(bytes_content),
        "sha256": hashlib.sha256(bytes_content).hexdigest(),
    }

# 读取上传载荷字段并统一兼容旧字段名。
def _item_fields(item: dict[str, Any]) -> tuple[str, str, str, str, str]:
    """读取上传条目的规范字段。

    参数：item 为单项上传载荷。
    返回：kind、local_path、remote_path、purpose 和 requirement_ref 五个文本字段。
    """

    # kind 决定源路径是文件还是窄目录。
    str_kind = str(item.get("kind", "")).strip().lower()  # 上传条目类型。

    # local_path 优先，兼容旧载荷的 path 字段。
    str_local = str(item.get("local_path", item.get("path", ""))).strip()  # 本地源路径。

    # 远端目的地由 remote_path 指定，旧 target 只作兼容。
    str_remote = str(item.get("remote_path", item.get("target", ""))).strip()  # 远程目标路径。

    # purpose 和 requirement_ref 是清单可审计性的必要说明。
    str_purpose = str(item.get("purpose", "")).strip()  # 上传用途。

    # requirement_ref 把每个远程文件绑定回已确认的需求范围。
    str_requirement = str(item.get("requirement_ref", "")).strip()  # 需求引用。

    # 返回统一字段，避免业务审查重复读取原始载荷。
    return str_kind, str_local, str_remote, str_purpose, str_requirement

# 检查上传条目中不依赖文件系统的字段合同。
def _field_blockers(
    str_kind: str,
    str_remote: str,
    str_purpose: str,
    str_requirement: str,
    dict_policy: dict[str, Any],
    remote_plan: dict[str, Any],
) -> list[str]:
    """收集策略、类型、用途和远程目标字段的阻断原因。

    参数:
        str_kind: 规范化的上传条目类型。
        str_remote: 规范化的远程目标路径。
        str_purpose: 远程上传用途说明。
        str_requirement: 已确认需求的引用文本。
        dict_policy: 远程上传策略映射。
        remote_plan: 远程目录治理计划映射。
    返回:
        不依赖本地文件展开的阻断原因列表。
    """

    # 先建立空集合，再按稳定顺序追加字段错误。
    list_blockers: list[str] = []  # 字段阻断集合。

    # 缺失策略必须阻止上传，而不能默认为宽松模式。
    if dict_policy.get("mode") != "manifest-only":

        # 只有 manifest-only 才允许远程传输。
        list_blockers.append("remote upload policy must be manifest-only")

    # force override 永远不能绕过工作区整体上传禁令。
    if dict_policy.get("force_override_allowed", True):

        # 该策略值必须显式写为 false。
        list_blockers.append("remote upload force override must be disabled")

    # 未知类型不能被推断为安全上传。
    if str_kind not in ALLOWED_UPLOAD_KINDS:

        # 报告原始类型帮助调用方改正载荷。
        list_blockers.append(f"unsupported upload kind `{str_kind}`")

    # 没有用途说明的上传无法进入治理审计。
    if not str_purpose:

        # purpose 关联任务目标和远程作用。
        list_blockers.append("upload purpose is required")

    # 没有需求引用的上传缺少授权边界。
    if not str_requirement:

        # requirement_ref 用于追溯用户确认的任务范围。
        list_blockers.append("upload requirement_ref is required")

    # 空目标或未列入计划的目标都必须阻止。
    if not str_remote:

        # 远程路径是 manifest 的必要定位字段。
        list_blockers.append("remote_path is required")

    # 非空目标仍必须落在目录治理计划白名单中。
    if str_remote and not allowed_remote_path(str_remote, remote_plan):

        # 未规划目标不能通过单项清单自行扩展远程范围。
        list_blockers.append(f"remote path `{normalize_rel(str_remote)}` is not planned")

    # 返回字段阶段的完整阻断集合。
    return list_blockers

# 为已展开文件生成逐项远程 manifest，并复核目标白名单。
def _build_item_manifest(
    project: Path,
    path_source: Path,
    list_files: list[Path],
    str_remote: str,
    remote_plan: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """生成单项文件清单并返回目标路径阻断。

    参数：project 为项目根；path_source 为源对象；list_files 为展开文件；str_remote 为目标；remote_plan 为治理计划。
    返回：manifest 条目列表和目标白名单阻断列表。
    """

    # 已展开文件按源路径顺序进入稳定清单。
    list_manifest: list[dict[str, Any]] = []  # 当前条目文件清单。

    # 目标白名单错误必须与文件证据分开返回。
    list_blockers: list[str] = []  # 当前条目目标阻断。

    # 逐文件构造远程目标并再次验证计划路径。
    for path_file in list_files:

        # 单文件默认使用原始远程目标。
        str_target = str_remote  # 当前文件的远程候选。

        # 窄目录文件按相对后缀展开到同一远程目录。
        if path_source.is_dir():

            # 目录相对后缀保持源目录结构。
            str_suffix = normalize_rel(str(path_file.relative_to(path_source)))  # 文件相对后缀。

            # 组合后的目标必须再次经过远程计划白名单。
            str_target = f"{str_remote.rstrip('/')}/{str_suffix}"  # 当前文件远程路径。

        # 目录展开不能凭空扩大已批准的远程目标。
        if not allowed_remote_path(str_target, remote_plan):

            # 记录具体目标并跳过该文件。
            list_blockers.append(f"remote path `{normalize_rel(str_target)}` is not planned")

            # 不能把未规划文件加入清单。
            continue

        # 仅已验证目标才生成可重算的内容条目。
        dict_manifest_entry = _manifest_entry(project, path_file, str_target)  # 当前文件条目。

        # 将当前文件证据追加到稳定顺序的 manifest。
        list_manifest.append(dict_manifest_entry)

    # 返回文件证据及其目标路径问题。
    return list_manifest, list_blockers

# 审查一项逐文件或窄目录远程上传声明。
def review_upload_item(
    project: Path,
    item: dict[str, Any],
    remote_plan: dict[str, Any],
) -> dict[str, Any]:
    """审查一项逐文件或窄目录远程上传声明。

    参数：project 为项目根；item 为上传条目；remote_plan 为远程治理计划。
    返回：包含 approved、blockers、item 和 manifest 的结构化审查结果。
    """

    # 统一读取字段，确保旧载荷不能跳过新门禁。
    tuple_fields = _item_fields(item)  # 上传字段元组。

    # 把兼容字段映射成后续审查使用的五个局部值。
    str_kind, str_local, str_remote, str_purpose, str_requirement = tuple_fields  # 规范字段。

    # 远程策略缺失时由字段审查先 fail-closed。
    dict_policy = _policy(remote_plan)  # 远程上传策略。

    # 收集策略和载荷字段阻断原因。
    tuple_field_values = (str_kind, str_remote, str_purpose, str_requirement, dict_policy, remote_plan)  # 字段校验参数。

    # 统一调用字段审查，保持策略错误顺序稳定。
    list_blockers = _field_blockers(*tuple_field_values)  # 按字段顺序返回的阻断列表。

    # 解析项目内源路径并检查工作区边界。
    tuple_source = _relative_source(project, str_local)  # 源路径解析结果。

    # 拆出路径和错误，避免把元组误当作路径继续使用。
    path_source, source_error = tuple_source  # 解析后的路径与错误。

    # 越根路径和整体上传都是不可覆盖阻断。
    if source_error:

        # 错误会同时进入绝对阻断标记。
        list_blockers.append(source_error)

    # 没有合法源路径时不能读取或生成 manifest。
    if path_source is None:

        # 保留原始 item 供上层审计，但清单必须为空。
        return {
            "approved": False,
            "absolute_blocker": True,
            "blockers": list(dict.fromkeys(list_blockers)),
            "item": item,
            "manifest": [],
        }

    # 文件系统展开会发现符号链接、禁传目录和空目录。
    tuple_expanded = _expand_source(project, path_source, str_kind)  # 展开结果。

    # 拆出文件列表与错误，阻断时不生成部分清单。
    list_files, list_expand_errors = tuple_expanded  # 文件列表与展开错误。

    # 把每个展开问题合并进统一阻断集合。
    list_blockers.extend(list_expand_errors)

    # 阻断条目不得产生部分 manifest。
    list_manifest: list[dict[str, Any]] = []  # 当前条目的文件清单。

    # 只有没有前置阻断时才计算文件哈希。
    if not list_blockers:

        # 仅在前置字段和源路径通过后计算文件哈希。
        tuple_manifest_result = _build_item_manifest(project, path_source, list_files, str_remote, remote_plan)  # 文件清单结果。

        # 拆出文件证据和目标路径阻断。
        list_manifest, list_manifest_blockers = tuple_manifest_result  # 清单与目标阻断。

        # 合并展开阶段之后发现的目标路径错误。
        list_blockers.extend(list_manifest_blockers)

        # 任一目标未获计划授权时，当前条目的部分清单也不能被传输。
        if list_manifest_blockers:

            # 清除已验证子集，避免阻断结果携带可被误用的部分证据。
            list_manifest = []  # 阻断条目不保留任何待传文件。

    # 空目录或空文件集合不是有效上传目标。
    if not list_manifest and not list_blockers:

        # 显式报告无文件，避免返回空 approved 清单。
        list_blockers.append("upload item expands to no files")

    # 清单中的 item 只保留审计所需的规范字段。
    dict_item = {
        "local_path": normalize_rel(str_local),  # 规范本地源路径。
        "remote_path": normalize_rel(str_remote),  # 规范远程目标路径。
        "kind": str_kind,  # 规范上传类型。
        "purpose": str_purpose,  # 审计用途说明。
        "requirement_ref": str_requirement,  # 授权需求引用。
    }  # 规范条目载荷。

    # 返回去重后的阻断与完整 manifest 证据。
    return {
        "approved": not list_blockers,
        "absolute_blocker": bool(list_blockers),
        "blockers": list(dict.fromkeys(list_blockers)),
        "item": dict_item,
        "manifest": list_manifest,
    }

# 审查全部上传条目并生成不可绕过的 manifest-only 结果。
def build_upload_manifest(
    project: Path,
    items: list[Any],
    remote_plan: dict[str, Any],
) -> dict[str, Any]:
    """审查全部上传条目并生成不可绕过的 manifest-only 结果。

    参数：project 为项目根；items 为上传条目列表；remote_plan 为远程治理计划。
    返回：包含决策、逐项审查、manifest 和清单哈希的结果映射。
    """

    # 逐项保存审查证据，便于远程上传前复核。
    list_reviews: list[dict[str, Any]] = []  # 条目审查结果。

    # 所有阻断原因最终都会去重并公开返回。
    list_blockers: list[str] = []  # 汇总阻断集合。

    # 清单只汇总完全通过的条目文件。
    list_manifest: list[dict[str, Any]] = []  # 汇总文件清单。

    # 空列表和非映射条目都必须 fail-closed。
    for item in items:

        # 非对象载荷没有字段合同，不能被推断或展开。
        if not isinstance(item, dict):

            # 记录结构错误并继续检查其他条目。
            list_blockers.append("each upload item must be a JSON object")

            # 当前条目没有可审查内容。
            continue

        # 复用单项审查确保所有路径规则一致。
        dict_review = review_upload_item(project, item, remote_plan)  # 单项审查结果。

        # 保存逐项证据，支持用户检查具体阻断。
        list_reviews.append(dict_review)

        # 汇总条目阻断和已验证文件。
        list_blockers.extend(dict_review["blockers"])

        # 追加当前条目已经通过验证的文件证据。
        list_manifest.extend(dict_review["manifest"])

    # 去重保持输出稳定，避免重复路径造成噪声。
    list_blockers = list(dict.fromkeys(list_blockers))  # 稳定阻断集合。

    # 清单序列化规则固定，保证 manifest_sha256 可重算。
    str_manifest = json.dumps(list_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))  # 规范清单 JSON。

    # 只有存在条目且没有阻断时才批准远程上传。
    bool_approved = not list_blockers and bool(list_reviews)  # 总体批准状态。

    # 返回 manifest-only 决策和完整内容摘要。
    return {
        "approved": bool_approved,
        "decision": "approved" if bool_approved else "blocked",
        "mode": "manifest-only",
        "force_override_allowed": False,
        "absolute_blockers": list_blockers,
        "reviews": list_reviews,
        "manifest": list_manifest,
        "manifest_sha256": hashlib.sha256(str_manifest.encode("utf-8")).hexdigest(),
    }
