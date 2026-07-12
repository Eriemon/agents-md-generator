"""集中检查禁止额外 Git worktree 的仓库策略。"""

# 延迟解析类型注解，兼容当前支持的 Python 运行时。
from __future__ import annotations

# 标准库提供路径规范化、Git 查询和结构化类型。
import os
import subprocess
from pathlib import Path
from typing import Any

# 固定名称不能被项目配置缩减，避免治理策略被局部配置放宽。
FORBIDDEN_WORKTREE_DIRECTORY_NAMES = (  # 项目根及父目录的保留容器名称。
    ".worktrees",  # 隐藏复数容器名称。
    "worktrees",  # 非隐藏复数容器名称。
    ".git-worktrees",  # 带 Git 前缀的隐藏容器名称。
    "git-worktrees",  # 带 Git 前缀的普通容器名称。
)

# 将 Git porcelain 文本转换为稳定记录。
def parse_worktree_porcelain(str_text: str) -> list[dict[str, Any]]:
    """
    解析 Git 注册工作区清单。

    :param str_text: ``git worktree list --porcelain`` 的标准输出。
    :return: 按 Git 输出顺序排列的工作区记录。
    """

    # 当前记录承接空行之前的 porcelain 字段。
    dict_current: dict[str, Any] = {}  # 尚未结束的工作区记录。

    # 完整列表保存已经结束且包含路径的记录。
    list_entries: list[dict[str, Any]] = []  # 可供策略判断的注册项。

    # 逐行识别键值字段和 detached 等无值标志。
    for str_raw_line in str_text.splitlines():

        # 去除 Git 输出行两侧不参与字段语义的空白。
        str_line = str_raw_line.strip()  # 当前 porcelain 字段文本。

        # 空行负责结束一条完整的工作区记录。
        if not str_line:

            # 只保留具有 worktree 路径的有效记录。
            if dict_current.get("worktree"):

                # 把当前记录加入最终解析清单。
                list_entries.append(dict_current)

            # 为下一条工作区记录重置独立容器。
            dict_current = {}  # 下一条记录的字段容器。

            # 当前空行不再参与字段解析。
            continue

        # 第一个空格区分字段名、分隔符和字段值。
        str_key, str_separator, str_field_value = str_line.partition(" ")  # 当前 porcelain 字段组成。

        # 无分隔符字段表示 detached、bare 或 locked 等布尔标志。
        dict_current[str_key] = str_field_value if str_separator else True  # 当前记录的规范字段值。

    # Git 输出末尾可以省略用于分隔记录的空行。
    if dict_current.get("worktree"):

        # 保存最后一条未由空行触发收尾的记录。
        list_entries.append(dict_current)

    # 返回经过最小有效性过滤的注册工作区列表。
    return list_entries

# 将 Git 返回路径转换为可比较的绝对路径。
def _resolve_git_path(path_project: Path, str_raw_path: str) -> Path:
    """
    解析 Git 元数据路径。

    :param path_project: 执行 Git 查询的工作目录。
    :param str_raw_path: Git 命令返回的路径文本。
    :return: 消除相对段后的绝对路径。
    """

    # Git 的相对元数据路径以命令工作目录为基准。
    path_resolved = Path(str_raw_path.strip())  # Git 输出表达的路径。

    # 相对路径需要先锚定到调用项目目录。
    if not path_resolved.is_absolute():

        # 拼接调用目录后再统一消除相对段。
        path_resolved = path_project / path_resolved  # 已锚定的 Git 路径。

    # strict=False 允许测试比较尚未实际创建的模拟路径。
    return path_resolved.resolve(strict=False)

# 生成跨 Windows 大小写差异稳定的路径键。
def _path_key(path_value: Path) -> str:
    """
    规范路径比较语义。

    :param path_value: 待比较的绝对或相对路径。
    :return: 已规范分隔符和大小写的字符串键。
    """

    # normcase 在 Windows 上消除盘符和路径大小写差异。
    return os.path.normcase(os.path.normpath(str(path_value.resolve(strict=False))))

# 在指定项目目录执行不会改变仓库状态的 Git 查询。
def _run_git(path_project: Path, list_arguments: list[str]) -> subprocess.CompletedProcess[str]:
    """
    执行只读 Git 查询。

    :param path_project: Git 查询工作目录。
    :param list_arguments: 不含 git 可执行文件名的参数列表。
    :return: 包含退出码和捕获输出的进程结果。
    """

    # 禁用交互并捕获文本输出，避免门禁等待凭据输入。
    return subprocess.run(
        ["git", "-C", str(path_project), *list_arguments],  # 只读 Git 命令及其工作目录。
        check=False,  # 非零退出码由策略层区分不适用与未知故障。
        capture_output=True,  # 标准输出和错误输出进入结构化诊断。
        text=True,  # Git 文本直接按字符串解析。
    )

# 扫描仓库根目录和父目录中的保留容器名称。
def _find_forbidden_directories(path_repository_toplevel: Path) -> list[str]:
    """
    查找 worktree 容器污染。

    :param path_repository_toplevel: Git 报告的仓库顶层目录。
    :return: 命中的规范绝对路径列表。
    """

    # 命中列表同时保留项目层级和父目录层级的诊断。
    list_forbidden_directories: list[str] = []  # 已发现的保留容器路径。

    # 两层扫描覆盖用户工作文件夹及其直接上一级目录。
    for path_scan_root in (path_repository_toplevel, path_repository_toplevel.parent):

        # 固定集合中的任一名称均属于不可配置放宽的污染。
        for str_directory_name in FORBIDDEN_WORKTREE_DIRECTORY_NAMES:

            # 候选路径保持扫描层级，方便用户在外部准确处理。
            path_candidate = path_scan_root / str_directory_name  # 当前保留名称的绝对候选。

            # lexists 同时识别正常目录和已经断链的符号链接。
            if os.path.lexists(path_candidate):

                # 把命中路径写入报告，不执行自动删除或移动。
                list_forbidden_directories.append(str(path_candidate.resolve(strict=False)))

    # 返回只读扫描得到的全部污染证据。
    return list_forbidden_directories

# 核验当前目录在 Git 注册清单中唯一且没有额外工作区。
def _classify_registered_worktrees(
    path_repository_toplevel: Path,
    list_registered_worktrees: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    分类当前与额外注册工作区。

    :param path_repository_toplevel: 当前 Git 工作区顶层目录。
    :param list_registered_worktrees: porcelain 解析后的注册清单。
    :return: 额外注册项和无法证明安全的诊断列表。
    """

    # 额外列表收集所有不等于当前仓库顶层的注册项。
    list_additional_worktrees: list[dict[str, Any]] = []  # 违反单工作区策略的注册项。

    # 错误列表记录缺失路径或当前目录匹配不唯一。
    list_errors: list[str] = []  # 注册清单完整性诊断。

    # 规范路径键避免 Windows 大小写差异导致误报。
    str_project_key = _path_key(path_repository_toplevel)  # 当前仓库顶层的比较键。

    # 匹配计数必须最终严格等于一。
    int_current_matches = 0  # 注册清单中当前工作区的出现次数。

    # 逐条区分当前目录、额外目录和缺少路径的畸形记录。
    for dict_entry in list_registered_worktrees:

        # worktree 字段是每条记录用于身份比较的必需数据。
        str_raw_worktree = str(dict_entry.get("worktree", "")).strip()  # 当前注册路径文本。

        # 缺少路径时无法证明该注册项是否安全。
        if not str_raw_worktree:

            # 将畸形记录作为 fail-closed 诊断保存。
            list_errors.append("Git worktree list contained an entry without a path")

            # 畸形记录不进入路径比较逻辑。
            continue

        # Git porcelain 中的 worktree 路径按绝对路径规范化。
        path_entry = Path(str_raw_worktree).resolve(strict=False)  # 当前注册项的规范路径。

        # 唯一当前记录与所有额外注册记录采用互斥分类。
        if _path_key(path_entry) == str_project_key:

            # 当前路径匹配次数用于发现重复或缺失注册状态。
            int_current_matches += 1  # 记录当前仓库顶层在注册清单中的唯一性证据。

        # 非当前路径全部视为禁止的额外工作区。
        else:

            # 保留 Git 原始字段，便于诊断对应分支和 HEAD。
            list_additional_worktrees.append(dict_entry)

    # 当前目录必须且只能对应一条注册记录。
    if int_current_matches != 1:

        # 任何零次或多次匹配都按未知仓库状态阻断。
        list_errors.append("current project was not uniquely identified in Git worktree list")

    # 返回额外注册项与完整性诊断供总报告组合。
    return list_additional_worktrees, list_errors

# 组装非 Git 目录的不适用报告。
def _not_applicable_report() -> dict[str, Any]:
    """
    返回不参与 Git worktree 治理的稳定载荷。

    :param: 本函数不接收外部参数。
    :return: 标记 Git 策略不适用且不阻断的报告。
    """

    # 非 Git 目录保持通过，但明确标记策略不适用。
    return {
        "ok": True,  # 不存在可治理的 Git worktree 状态。
        "applicable": False,  # 调用方不得把结果解释为 Git 状态已验证。
        "hard_blocking": False,  # 普通目录不触发 Git 专用硬阻断。
        "repository_toplevel": "",  # 非 Git 目录没有仓库顶层。
        "linked_current_worktree": False,  # 不存在 linked worktree 判定对象。
        "core_worktree": "",  # 不读取非 Git 目录的 Git 配置。
        "registered_worktrees": [],  # 非 Git 目录没有注册清单。
        "additional_worktrees": [],  # 非 Git 目录没有额外注册项。
        "forbidden_directories": [],  # Git 不适用路径不扫描仓库保留名称。
        "errors": [],  # 标准非 Git 状态不是查询错误。
    }

# 读取并解释生效的 core.worktree 配置。
def _inspect_core_worktree(path_project: Path) -> tuple[str, list[str]]:
    """
    核验 Git 工作目录重定向配置。

    :param path_project: 当前 Git 仓库中的工作目录。
    :return: 生效配置值和配置查询诊断。
    """

    # 查询所有生效配置来源，includeIf 和全局来源也不能绕过禁令。
    completed_process_core_worktree = _run_git(path_project, ["config", "--get", "core.worktree"])  # 重定向查询结果。

    # 默认值代表 Git 明确返回“未设置”。
    str_core_worktree = ""  # 生效的显式重定向配置值。

    # 错误列表区分异常空值和配置读取故障。
    list_errors: list[str] = []  # 无法证明配置安全的诊断。

    # 返回码 0 表示存在一个生效的显式 core.worktree 值。
    if completed_process_core_worktree.returncode == 0:

        # 保存生效值用于机器可读诊断。
        str_core_worktree = completed_process_core_worktree.stdout.strip()  # Git 解析后的重定向目标。

        # 空配置同样代表无法解释的显式状态。
        if not str_core_worktree:

            # 将异常空值作为未知配置风险阻断。
            list_errors.append("Git reported an empty explicit core.worktree configuration")

    # 返回码 1 专门表示未设置，其他非零码均为查询故障。
    elif completed_process_core_worktree.returncode != 1:

        # 配置查询失败时不能假定没有重定向。
        list_errors.append("unable to verify explicit core.worktree configuration")

    # 返回值与错误分离，方便总协调函数组合硬阻断证据。
    return str_core_worktree, list_errors

# 查询 linked 状态并分类 Git 注册工作区。
def _inspect_registered_state(path_project: Path, path_repository_toplevel: Path) -> dict[str, Any]:
    """
    核验仓库元数据与注册清单。

    :param path_project: 执行只读 Git 查询的工作目录。
    :param path_repository_toplevel: Git 确认的当前仓库顶层。
    :return: linked 状态、注册项、额外项和错误诊断。
    """

    # 三项元数据查询共同证明 linked 状态和注册清单。
    completed_process_git_dir = _run_git(path_project, ["rev-parse", "--git-dir"])  # 当前工作区元数据位置。

    # common-dir 表示所有工作区共享的仓库元数据位置。
    completed_process_common_dir = _run_git(path_project, ["rev-parse", "--git-common-dir"])  # 共享元数据位置。

    # porcelain 清单提供当前仓库注册的全部工作区。
    completed_process_worktree_list = _run_git(path_project, ["worktree", "list", "--porcelain"])  # 注册工作区查询结果。

    # 错误列表统一汇总 Git 查询和清单完整性风险。
    list_errors: list[str] = []  # 所有无法证明注册状态安全的诊断。

    # 注册列表仅在三项仓库元数据查询都成功后解析。
    list_registered_worktrees: list[dict[str, Any]] = []  # Git 报告的全部注册项。

    # 额外列表保存当前仓库顶层以外的每个注册项。
    list_additional_worktrees: list[dict[str, Any]] = []  # 总报告中等待填充的额外注册项集合。

    # linked 标志由 git-dir 与 common-dir 的规范路径差异决定。
    bool_linked_current_worktree = False  # 当前目录是否为 linked worktree。

    # 仓库元数据查询必须全部成功，才允许进一步分类。
    tuple_metadata_results = (  # 共同决定注册状态是否可信的查询集合。
        completed_process_git_dir,  # 当前工作区元数据查询。
        completed_process_common_dir,  # 共享仓库元数据查询。
        completed_process_worktree_list,  # 注册工作区清单查询。
    )

    # 任一元数据查询失败都按未知状态关闭发布路径。
    if any(completed_process.returncode != 0 for completed_process in tuple_metadata_results):

        # 保留稳定错误文本，避免把 Git 本地路径写入治理产物。
        list_errors.append("unable to verify Git worktree policy from repository metadata")

    # 查询全部成功时再计算 linked 状态并分类注册清单。
    else:

        # 当前工作区元数据路径用于 linked 状态比较。
        path_git_dir = _resolve_git_path(path_project, completed_process_git_dir.stdout)  # 当前 git-dir 绝对路径。

        # 共享仓库元数据路径代表主工作区的元数据根。
        path_common_dir = _resolve_git_path(path_project, completed_process_common_dir.stdout)  # common-dir 绝对路径。

        # 路径不同时说明当前目录依赖主仓库的 linked 元数据。
        bool_linked_current_worktree = _path_key(path_git_dir) != _path_key(path_common_dir)  # 元数据根差异标记链接工作区。

        # 将 Git 清单转为结构化记录后再执行唯一性检查。
        list_registered_worktrees = parse_worktree_porcelain(completed_process_worktree_list.stdout)  # 注册工作区结构。

        # 空清单无法证明当前目录是唯一工作区。
        if not list_registered_worktrees:

            # 将缺失清单加入硬阻断诊断。
            list_errors.append("Git worktree list did not contain any registered worktree")

        # 非空清单必须验证当前项唯一且没有额外项。
        else:

            # 分类函数同时返回额外项和清单完整性错误。
            tuple_classification = _classify_registered_worktrees(  # 注册状态分类函数的双列表返回值。
                path_repository_toplevel,  # 当前仓库顶层身份。
                list_registered_worktrees,  # Git 返回的全部注册项。
            )

            # 第一项提供当前仓库之外的全部注册工作区。
            list_additional_worktrees = tuple_classification[0]  # 需要触发硬阻断的额外注册项。

            # 第二项提供注册清单缺失或身份不唯一的诊断。
            list_registration_errors = tuple_classification[1]  # 需要并入错误通道的清单问题。

            # 把清单完整性问题并入统一错误通道。
            list_errors.extend(list_registration_errors)

    # 返回供总协调函数直接组合的注册状态报告。
    return {
        "linked_current_worktree": bool_linked_current_worktree,  # 当前目录的链接工作区判定。
        "registered_worktrees": list_registered_worktrees,  # Git 提供的原始注册记录。
        "additional_worktrees": list_additional_worktrees,  # 当前仓库顶层之外的注册记录。
        "errors": list_errors,  # 元数据查询和清单完整性诊断。
    }

# 检查当前项目是否违反额外 worktree 禁令。
def inspect_worktree_policy(path_project: Path) -> dict[str, Any]:
    """
    检查 linked worktree、显式重定向、额外注册项和保留目录污染。

    :param path_project: 当前项目目录或其仓库子目录。
    :return: 可由分支、发布和安装门禁共同消费的策略报告。
    """

    # 规范调用路径后再执行所有 Git 查询和路径比较。
    path_project = path_project.resolve()  # 当前策略检查的绝对工作目录。

    # 首个查询确定真实仓库顶层，并区分非 Git 目录。
    completed_process_toplevel = _run_git(path_project, ["rev-parse", "--show-toplevel"])  # Git 顶层查询结果。

    # 标准非 Git 错误属于策略不适用而不是未知失败。
    # 单独保存非 Git 判定，避免长条件掩盖退出码语义。
    bool_non_git_directory = (  # 顶层查询是否返回 Git 的标准非仓库诊断。
        completed_process_toplevel.returncode != 0  # 查询没有得到仓库顶层。
        and "not a git repository" in completed_process_toplevel.stderr.lower()  # 错误文本明确表示普通目录。
    )

    # 标准非 Git 结果保留技能对普通项目目录的支持。
    if bool_non_git_directory:

        # 返回稳定不适用载荷，保留非 Git 项目的正常设计流程。
        return _not_applicable_report()

    # 未知顶层查询失败必须阻止继续治理和发布。
    if completed_process_toplevel.returncode != 0:

        # 用统一失败报告记录无法确定仓库顶层的原因。
        return {
            "ok": False,  # 未能证明 worktree 状态安全。
            "applicable": True,  # 查询失败仍属于必须治理的未知 Git 状态。
            "hard_blocking": True,  # fail-closed 阻止后续副作用。
            "repository_toplevel": "",  # 顶层查询没有可信结果。
            "linked_current_worktree": False,  # 未执行 linked 状态推断。
            "core_worktree": "",  # 未读取显式重定向配置。
            "registered_worktrees": [],  # 未取得注册工作区清单。
            "additional_worktrees": [],  # 未分类额外注册项。
            "forbidden_directories": [],  # 缺少可信顶层时不扫描猜测路径。
            "errors": ["unable to determine Git repository toplevel for worktree policy"],  # 稳定阻断诊断。
        }

    # Git 顶层作为路径扫描和注册清单匹配的共同基准。
    path_repository_toplevel = _resolve_git_path(path_project, completed_process_toplevel.stdout)  # 真实仓库顶层。

    # 文件系统扫描只收集证据，不清理用户目录。
    list_forbidden_directories = _find_forbidden_directories(path_repository_toplevel)  # 两层保留名称命中。

    # 独立查询并解释 linked 状态与注册工作区清单。
    dict_registered_state = _inspect_registered_state(path_project, path_repository_toplevel)  # 注册状态报告。

    # 提取 linked 判定用于最终硬阻断组合。
    bool_linked_current_worktree = bool(dict_registered_state["linked_current_worktree"])  # 当前目录是否为链接工作区。

    # 保留 Git 原始记录，供调用方定位额外工作区。
    list_registered_worktrees = list(dict_registered_state["registered_worktrees"])  # 全部注册工作区记录。

    # 额外记录是单工作区合同的直接违规证据。
    list_additional_worktrees = list(dict_registered_state["additional_worktrees"])  # 当前目录之外的注册记录。

    # 元数据查询和清单完整性错误进入统一诊断列表。
    list_errors = list(dict_registered_state["errors"])  # 注册状态无法证明安全的原因。

    # 独立解释显式重定向，避免总协调函数承载配置细节。
    tuple_core_worktree = _inspect_core_worktree(path_project)  # 配置值与查询诊断的组合。

    # 第一项用于报告具体生效值并直接参与硬阻断。
    str_core_worktree = tuple_core_worktree[0]  # 生效的显式工作目录重定向。

    # 第二项记录空配置或读取故障等未知状态。
    list_core_worktree_errors = tuple_core_worktree[1]  # 配置查询形成的阻断诊断。

    # 配置诊断与仓库元数据诊断使用同一错误通道。
    list_errors.extend(list_core_worktree_errors)

    # 任一风险信号都属于不可确认绕过的硬阻断。
    bool_hard_blocking = bool(  # 下游门禁共同消费的最终阻断状态。
        list_errors  # Git 查询或注册清单完整性错误。
        or list_forbidden_directories  # 项目根或父目录保留容器污染。
        or list_additional_worktrees  # 当前目录以外的注册工作区。
        or bool_linked_current_worktree  # 当前目录自身属于 linked worktree。
        or str_core_worktree  # 任意显式 core.worktree 重定向。
    )

    # 返回统一策略载荷供分支、发布和安装入口复用。
    return {
        "ok": not bool_hard_blocking,  # 只有全部证据安全时才通过。
        "applicable": True,  # 当前目录属于 Git 仓库治理范围。
        "hard_blocking": bool_hard_blocking,  # 人工确认不得覆盖该状态。
        "repository_toplevel": str(path_repository_toplevel),  # Git 确认的仓库顶层。
        "linked_current_worktree": bool_linked_current_worktree,  # 当前目录的 linked 状态。
        "core_worktree": str_core_worktree,  # 禁止存在的显式工作目录重定向值。
        "registered_worktrees": list_registered_worktrees,  # 用于证明唯一工作区的原始注册证据。
        "additional_worktrees": list_additional_worktrees,  # 当前目录以外的注册项。
        "forbidden_directories": list_forbidden_directories,  # 两层目录扫描命中。
        "errors": list_errors,  # 未知或畸形 Git 状态诊断。
    }
