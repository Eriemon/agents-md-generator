"""只读审查受限工作树中的 Python/Markdown 冗余与不匹配。

命令行标准输出是唯一一个 UTF-8 JSON 对象；任何诊断都放入该对象，绝不
写入报告文件、缓存或源码。退出码 0 表示分析完成，2 表示参数、范围或
快照无效，3 表示存在部分解析或证据。
"""

# 延迟注解求值保持 Python 3.10 兼容性。
from __future__ import annotations

# 工具只使用标准库完成 AST、Git 读取、哈希和严格 JSON 输出。
import argparse
import ast

# AST 证据上下文使用 dataclass 保持字段契约集中。
from dataclasses import dataclass

# 哈希、路径、进程和类型库共同支撑只读证据采集。
import hashlib
import json
import os

# 路径、正则、进程和类型库支撑跨平台证据处理。
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Iterable, cast

# 读取角色卡声明的 verdict 集合与范围拒绝结论。
try:
    from .worker_dispatch_contracts import (
        GARDENER_RECEIPT_VERDICTS,
        canonical_worker_id,
        worker_blocking_verdicts,
        worker_scope_rejection_verdict,
    )

# 包内合同导入失败时改用脚本同目录兼容路径。
except ImportError:
    # 脚本入口沿用同目录的 worker 合同导入。
    from worker_dispatch_contracts import (
        GARDENER_RECEIPT_VERDICTS,
        canonical_worker_id,
        worker_blocking_verdicts,
        worker_scope_rejection_verdict,
    )

# 报告 schema 版本用于校验跨进程 gardener 证据。
SCHEMA_VERSION = 1  # gardener 报告结构版本

# worker 名称用于报告归属和审计路由。
WORKER_NAME = canonical_worker_id("gardener")  # 只读 gardener 的协议名称

# 候选扫描只处理 Python 和 Markdown 文件。
ALLOWED_SUFFIXES = {".py", ".md"}  # 允许进入分析范围的文件后缀

# 禁止目录段阻断对治理、发布和引用目录的扫描。
FORBIDDEN_SEGMENTS = {
    ".agents",  # 运行时治理目录
    ".git",  # Git 内部对象目录
    ".codebase-memory",  # 知识图谱持久化目录
    "dist",  # 发布制品目录
    "github",  # 外部发布镜像目录
    "ref",  # 参考资料目录
}  # 扫描必须排除的目录段

# 报告 verdict 只允许使用固定协议值。
VERDICTS = set(GARDENER_RECEIPT_VERDICTS)  # 受支持的分析结论

# 读取角色卡声明的阻断结论集合。
BLOCKING_VERDICTS = worker_blocking_verdicts(WORKER_NAME)  # 角色卡声明的阻断结论

# 选择稳定的阻断结论文本供异常路径复用。
BLOCKING_VERDICT = sorted(BLOCKING_VERDICTS)[0] if BLOCKING_VERDICTS else ""  # 稳定的阻断结论

# 生成稳定事件标识，供主 Agent 去重 gardener 调度。
def gardener_event_id(trigger: str, commit: str | None = None, snapshot_digest: str = "") -> str:
    """构造可去重的触发事件标识。

    参数：
        trigger: 触发扫描的模式名称。
        commit: 可选的提交引用。
        snapshot_digest: 允许范围快照摘要。
    返回：由触发参数和快照绑定的十六进制事件标识。
    """

    # 事件身份只由触发类型、提交和允许范围快照组成，不依赖时间戳。
    str_commit = commit or ""  # 缺省提交引用的稳定空值

    # 事件字段按固定顺序编码，避免同一证据产生不同事件标识。
    return hashlib.sha256(
        f"{trigger}\0{str_commit}\0{snapshot_digest}".encode("utf-8")
    ).hexdigest()

# 判断事件是否已经审查，避免重复启动只读扫描。
def should_dispatch_gardener(event_id: str, reviewed_event_ids: Iterable[str]) -> bool:
    """判断事件是否已经被主 Agent 审查过。

    参数：
        event_id: 待判断的事件标识。
        reviewed_event_ids: 主 Agent 已确认的事件标识集合。
    返回：事件非空且尚未审查时返回 True。
    """

    # 重复事件必须去重，空事件标识视为非法而不触发扫描。
    str_event = str(event_id).strip()  # 去除事件标识外围空白

    # 只调度非空且不在既有审查集合中的事件。
    return bool(str_event) and str_event not in {str(item).strip() for item in reviewed_event_ids}

# 根据治理摘要变化和 verify 结果决定是否调度完整扫描。
def refresh_dispatch_status(
    before_digest: str,
    after_digest: str,
    verify_passed: bool,
) -> str:
    """根据受管 AGENTS 刷新字节变化和 verify 结果返回触发状态。

    参数：
        before_digest: 刷新前的治理文件摘要。
        after_digest: 刷新后的治理文件摘要。
        verify_passed: 根规则验证是否通过。
    返回：可调度的完整扫描状态或不调度状态。
    """

    # 只有字节变化且根规则验证通过才触发 full gardener scan。
    if verify_passed and before_digest and after_digest and before_digest != after_digest:

        # 只有治理内容真实变化且验证通过才放行完整扫描。
        return "dispatch_full_scan"

    # 未满足变化或验证条件时保持关闭调度。
    return "no_dispatch"

# 判断快照摘要漂移是否仍允许一次受控重试。
def snapshot_retry_status(attempt: int, expected_digest: str, actual_digest: str) -> str:
    """返回允许范围快照漂移的 fail-closed 重试状态。

    参数：
        attempt: 当前绑定尝试次数。
        expected_digest: 主 Agent 绑定的快照摘要。
        actual_digest: 本次读取到的快照摘要。
    返回：稳定、一次重试或阻断状态。
    """

    # 首次漂移允许主 Agent 重新绑定一次，第二次直接阻断。
    if expected_digest == actual_digest:

        # 摘要未变化时可以继续使用当前证据。
        return "stable"

    # 首次摘要漂移仍允许一次重新绑定。
    if int(attempt) <= 1:

        # 首次漂移只允许一次重新绑定机会。
        return "retry_once"

    # 重复漂移表示证据不稳定，必须停止继续分析。
    return "BLOCKED_UNSTABLE_SNAPSHOT"

# 路径规范化是所有候选边界检查的统一入口。
def _absolute_root(project_root: str | Path) -> Path:
    """返回规范化项目根路径。

    参数：
        project_root: 项目根目录文本或路径对象。
    返回：不创建文件的绝对规范化项目路径。
    """

    # resolve(strict=False) 只规范路径，不创建或修改文件。
    return Path(project_root).expanduser().resolve(strict=False)

# 将候选路径转换为项目相对 POSIX 文本，统一报告边界。
def _relative_path(path_item: Path, project_root: Path) -> str:
    """返回项目相对 POSIX 路径，越界时抛出 ValueError。

    参数：
        path_item: 待转换的候选路径。
        project_root: 已规范化的项目根路径。
    返回：候选路径的项目相对 POSIX 文本。
    异常：候选路径越出项目根时抛出 ValueError。
    """

    # 解析候选路径后再执行 relative_to，确保边界检查使用同一语义。
    return path_item.resolve(strict=False).relative_to(project_root).as_posix()

# 判断路径是否命中 gardener 的禁止目录段。
def _is_forbidden(relative_path: str) -> bool:
    """判断路径是否命中任一禁止目录段。

    参数：
        relative_path: 项目相对路径文本。
    返回：路径包含禁止段或根 docs 路径时返回 True。
    """

    # 使用路径段比较，避免把合法文件名中的普通片段误判为目录。
    str_normalized = relative_path.replace("\\", "/").casefold()  # 统一分隔符和大小写

    # 禁止段集合按同样的大小写语义比较。
    set_forbidden = {str_part.casefold() for str_part in FORBIDDEN_SEGMENTS}  # 规范化禁止段集合

    # 根 docs 路径属于明确的排除范围。
    bool_root_docs = str_normalized == "docs" or str_normalized.startswith("docs/")  # 根 docs 目录标记

    # 仅按完整路径段匹配，避免合法文件名中的子串误报。
    return bool_root_docs or any(str_part in set_forbidden for str_part in str_normalized.split("/"))

# 检查候选路径的每一层，避免链接目标绕过项目边界。
def _has_link_component(path_item: Path, path_project: Path) -> bool:
    """在解析前检查候选路径及其父段中的链接或重解析点。

    参数：
        path_item: 待审查的候选路径。
        path_project: 已规范化的项目根路径。
    返回：候选路径或父级存在链接、重解析点或越界时返回 True。
    """

    # 链接必须在 resolve 前拒绝，避免把越界目标伪装成普通文件。
    try:

        # 只沿项目内的相对路径段逐级探测链接。
        tuple_parts = path_item.relative_to(path_project).parts  # 候选路径的相对段

    # 越出项目根的路径直接视为不安全。
    except ValueError:

        # 失败关闭，避免后续解析访问项目外部。
        return True

    # 从项目根开始逐段累积待检查路径。
    path_probe = path_project  # 当前正在检查的路径前缀

    # 逐个检查父目录和目标文件是否为链接或重解析点。
    for str_part in tuple_parts:

        # 累加当前路径段，保持探测顺序与解析顺序一致。
        path_probe = path_probe / str_part  # 当前路径探测点

        # pathlib 和 os 两套检查共同覆盖 Windows 与 POSIX 链接。
        if path_probe.is_symlink() or os.path.islink(str(path_probe)):

            # 任何链接组件都不能进入只读候选分析。
            return True

        # lstat 负责检查无需跟随目标的文件属性。
        try:

            # 保留原始文件属性，避免 resolve 隐藏重解析信息。
            stat_result_info: os.stat_result = os.lstat(path_probe)  # 当前探测点的 lstat 结果

        # 路径尚不存在时继续检查后续逻辑，不把缺失误判为链接。
        except OSError:

            # 不存在的候选在调用方后续会由 is_file 再次筛选。
            continue

        # POSIX lstat 模式明确标记的链接必须阻断。
        if stat.S_ISLNK(stat_result_info.st_mode):

            # 保持与 pathlib 检查相同的失败关闭策略。
            return True

        # Windows 重解析点通过 file_attributes 标志识别。
        if int(getattr(stat_result_info, "st_file_attributes", 0)) & 0x400:

            # 重解析点可能跳出工作区，不能作为普通文件处理。
            return True

    # 全部路径组件都通过链接和重解析检查。
    return False

# 过滤 tracked 候选路径，只保留允许根内的 Python 和 Markdown 文件。
def filter_candidate_paths(
    paths: Iterable[str | Path],
    project_root: str | Path,
    source_root: str | Path,
    tests_root: str | Path,
    *,
    trigger: str = "agents-refresh",
) -> list[Path]:
    """过滤 tracked 候选路径，只保留 source/tests 下的 .py/.md。

    参数：
        paths: Git tracked 路径或路径文本迭代器。
        project_root: 项目根目录。
        source_root: 允许扫描的源代码根目录。
        tests_root: 允许扫描的测试根目录。
        trigger: 当前扫描触发模式。
    返回：通过边界、链接、后缀和重复检查的路径列表。
    异常：根目录越出项目根时抛出 ValueError。
    """

    # 三个根目录都必须位于同一个工作文件夹内；commit 模式不能依赖工作树存在性。
    path_project = _absolute_root(project_root)  # 规范化后的项目根目录

    # 先保留调用方的源代码和测试根路径文本。
    path_source = Path(source_root)  # 源代码扫描根

    # 测试根路径与源码根路径保持同一项目边界。
    path_tests = Path(tests_root)  # 测试扫描根

    # 相对根目录统一解析到项目根下，禁止隐式使用当前工作目录。
    if not path_source.is_absolute():

        # 将相对源代码根绑定到项目边界。
        path_source = path_project / path_source  # 组合项目内源码根路径

    # 测试根目录也必须解析到同一项目边界。
    if not path_tests.is_absolute():

        # 将相对测试根绑定到项目边界。
        path_tests = path_project / path_tests  # 组合项目内测试根路径

    # 用绝对路径文本消除不同平台的相对表示差异。
    path_source = Path(os.path.abspath(str(path_source)))  # 规范化源代码根

    # 将测试根也转换为不依赖当前目录的绝对路径。
    path_tests = Path(os.path.abspath(str(path_tests)))  # 规范化测试根

    # relative_to 作为根目录越界的 fail-closed 检查。
    path_source.relative_to(path_project)

    # 测试根越界时立即抛出异常，避免扩大扫描范围。
    path_tests.relative_to(path_project)

    # commit 模式读取 Git 对象，不要求工作树目标实际存在。
    bool_commit = trigger == "commit"  # 当前是否使用提交对象证据

    # 工作树模式在解析根目录前先拒绝链接组件。
    if not bool_commit:

        # 任一允许根含链接时停止候选过滤，避免边界漂移。
        if _has_link_component(path_source, path_project) or _has_link_component(path_tests, path_project):

            # 以空结果表示本次扫描无法获得安全工作树证据。
            return []

        # 仅在通过链接检查后解析根目录的最终路径。
        path_source = path_source.resolve(strict=False)  # 源代码根的最终路径

        # 测试根解析结果用于后续候选边界比较。
        path_tests = path_tests.resolve(strict=False)  # 测试根的最终路径

    # 记录规范化后的唯一候选，避免 Git 输出重复路径。
    set_paths: set[str] = set()  # 已接纳候选的相对路径集合

    # 结果列表保存通过全部边界与文件类型检查的路径。
    list_result: list[Path] = []  # 通过全部过滤条件的候选路径

    # 逐项解析 Git 输出，保留稳定且唯一的候选路径。
    for value_path in paths:

        # 统一把 Git 路径文本转成路径对象。
        path_item = Path(value_path)  # 当前候选路径

        # 相对 Git 路径以项目根为解析起点。
        if not path_item.is_absolute():

            # 将候选路径绑定到已校验的项目根。
            path_item = path_project / path_item  # 组合候选的项目绝对路径

        # 使用绝对路径文本消除相对路径别名。
        path_item = Path(os.path.abspath(str(path_item)))  # 规范化候选绝对路径

        # 工作树模式拒绝候选路径中的链接组件。
        if not bool_commit and _has_link_component(path_item, path_project):

            # 该候选不能提供安全的文件边界证据。
            continue

        # 候选必须先能转换为项目相对路径。
        try:

            # 使用 POSIX 文本作为报告和去重键。
            str_relative = path_item.relative_to(path_project).as_posix()  # 候选相对路径

        # 项目外路径不得进入任何后续判断。
        except ValueError:

            # 丢弃越界路径并继续处理其他 Git 输出。
            continue

        # 治理、发布目录及非目标后缀不在允许范围。
        if _is_forbidden(str_relative) or path_item.suffix.lower() not in ALLOWED_SUFFIXES:

            # 过滤掉不属于当前 gardener 合同的路径。
            continue

        # AGENTS 文件只作为治理证据，不进入 Markdown 内容发现。
        if path_item.name.casefold() == "agents.md":

            # 避免把治理入口重复计入文档候选。
            continue

        # 记录候选是否落在源代码根或测试根之下。
        bool_under_allowed_root = False  # 是否命中允许根目录

        # 两个根目录都使用 relative_to 完成边界判断。
        for path_root in (path_source, path_tests):

            # 当前候选若在该根目录内即可进入下一步。
            try:

                # 验证候选没有越过当前允许根。
                path_item.relative_to(path_root)

                # 记住命中结果，避免重复边界计算。
                bool_under_allowed_root = True  # 标记候选命中当前允许根

                # 已命中一个允许根，不必继续检查另一个根。
                break

            # 候选不在当前根目录时继续检查另一个根。
            except ValueError:

                # 当前根未命中不影响后续根目录判断。
                continue

        # 越出允许根或已经出现的路径都不能重复接纳。
        if not bool_under_allowed_root or str_relative in set_paths:

            # 保持结果集合唯一且边界明确。
            continue

        # 工作树模式还需验证解析后目标是真实普通文件。
        if not bool_commit:

            # 只对已通过链接组件检查的候选解析最终路径。
            path_item = path_item.resolve(strict=False)  # 工作树候选的最终路径

            # 链接目标或非文件对象不作为候选。
            if path_item.is_symlink() or not path_item.is_file():

                # 失败关闭，避免目录或链接进入 AST/Markdown 读取。
                continue

        # 记录唯一相对路径并保留其 Path 对象。
        set_paths.add(str_relative)

        # 保留已验证的候选路径供后续只读分析。
        list_result.append(path_item)

    # 按项目相对 POSIX 路径排序，保证报告顺序跨平台稳定。
    return sorted(list_result, key=lambda item: item.relative_to(path_project).as_posix())

# 执行只读 Git 文本查询，统一封装命令输出和状态。
def _run_git(path_project: Path, list_args: list[str]) -> tuple[int, str, str]:
    """执行只读 Git 查询并返回状态、标准输出和错误。

    参数：
        path_project: Git 仓库项目根目录。
        list_args: 只读 Git 子命令及其参数。
    返回：返回码、UTF-8 标准输出和 UTF-8 错误输出三元组。
    """

    # Git 查询不包含 checkout、reset、写入或 hook 操作。
    completed_process_result: subprocess.CompletedProcess[str] = subprocess.run(  # Git 只读查询结果
        ["git", "-C", str(path_project), *list_args],  # 绑定原始字节查询的仓库根
        check=False,  # 保留失败返回码供调用方判断
        capture_output=True,  # 捕获标准输出和错误文本
        text=True,  # 请求文本模式而不是字节模式
        encoding="utf-8",  # 统一命令输出编码
        errors="replace",  # 处理异常字节而不中断证据收集
    )

    # 返回命令结果的三个稳定字段，禁止额外写入。
    return completed_process_result.returncode, completed_process_result.stdout, completed_process_result.stderr

# 执行返回原始对象字节的 Git 查询，保留 commit 证据原样。
def _run_git_bytes(path_project: Path, list_args: list[str]) -> tuple[int, bytes, bytes]:
    """执行返回原始对象字节的只读 Git 查询。

    参数：
        path_project: Git 仓库项目根目录。
        list_args: 只读 Git 子命令及其参数。
    返回：返回码、原始标准输出和原始错误输出三元组。
    """

    # commit 模式必须绕过当前工作树，保留 Git 对象的真实字节。
    completed_process_result: subprocess.CompletedProcess[bytes] = subprocess.run(  # Git 原始对象字节查询结果
        ["git", "-C", str(path_project), *list_args],  # 绑定项目根的 Git 参数
        check=False,  # 让调用方读取返回码
        capture_output=True,  # 捕获原始对象字节
    )

    # 保留原始字节，避免文本解码改变 commit 内容。
    return completed_process_result.returncode, completed_process_result.stdout, completed_process_result.stderr

# 读取提交对象中的指定 blob，供 commit 模式复核原始内容。
def _git_object_bytes(path_project: Path, commit: str, str_relative: str) -> bytes | None:
    """读取 commit 中指定路径的 blob 字节；失败返回 None。

    参数：
        path_project: Git 仓库项目根目录。
        commit: 已验证的提交引用。
        str_relative: 项目相对路径。
    返回：blob 原始字节；Git 查询失败时返回 None。
    """

    # `cat-file blob` 不会检出、写入或读取当前工作树。
    tuple_int_status, tuple_bytes_output, _ = _run_git_bytes(  # Git blob 查询结果
        path_project,  # cat-file 查询的仓库根目录
        ["cat-file", "blob", f"{commit}:{str_relative}"],  # 指定提交和相对路径
    )

    # 只有完整成功的 Git 查询才能作为原始 blob 证据。
    return tuple_bytes_output if tuple_int_status == 0 else None

# 读取提交对象的 Git blob SHA-1，绑定候选来源。
def _git_blob_id(path_project: Path, commit: str, str_relative: str) -> str:
    """返回 commit 中指定路径的 Git blob SHA-1。

    参数：
        path_project: Git 仓库项目根目录。
        commit: 已验证的提交引用。
        str_relative: 项目相对路径。
    返回：blob SHA-1 文本；查询失败时返回空字符串。
    """

    # blob id 与内容 SHA-256 一起保留，方便主 Agent 复核来源。
    tuple_int_status, tuple_str_output, _ = _run_git(  # blob 标识查询结果
        path_project,  # rev-parse 绑定的对象仓库
        ["rev-parse", f"{commit}:{str_relative}"],  # 指定提交对象路径
    )

    # 仅在 Git 成功时保留去掉换行的 blob 标识。
    return tuple_str_output.strip() if tuple_int_status == 0 else ""

# 验证候选在 Git 中是普通 blob，排除链接和未跟踪文件。
def _tracked_regular(
    path_project: Path,
    str_relative: str,
    trigger: str,
    commit: str | None,
) -> bool:
    """确认候选来自 tracked regular blob，而不是 symlink 或未跟踪文件。

    参数：
        path_project: Git 仓库项目根目录。
        str_relative: 项目相对路径。
        trigger: 当前扫描触发模式。
        commit: 可选的提交引用。
    返回：候选在对应 Git 证据源中是普通 blob 时返回 True。
    """

    # commit 模式直接检查对象类型，refresh 模式检查 index mode。
    if trigger == "commit" and commit:

        # commit 模式读取提交树中的文件类型和 mode。
        tuple_int_status, tuple_str_output, _ = _run_git(  # 提交树查询结果
            path_project,  # ls-tree 使用的提交仓库
            ["ls-tree", commit, "--", str_relative],  # 指定提交和候选路径
        )

        # Git tree 输出按 mode、类型和对象字段拆分。
        list_fields = tuple_str_output.split(None, 2)  # 提交树字段

        # 仅普通 blob 且字段完整的记录允许进入候选集合。
        return (
            tuple_int_status == 0
            and len(list_fields) >= 2
            and list_fields[0] not in {"120000", "160000"}
            and list_fields[1] == "blob"
        )

    # 工作树模式检查 index 的 stage 输出，保持与 commit 模式相同的链接拒绝。
    tuple_int_status, tuple_str_output, _ = _run_git(  # 工作树 index 查询结果
        path_project,  # ls-files 核验的工作树仓库
        ["ls-files", "--stage", "--", str_relative],  # 指定 index 查询范围
    )

    # Git 查询失败时不能把空输出当成普通文件。
    if tuple_int_status != 0:

        # 失败关闭，保持 tracked 证据完整性。
        return False

    # 解析 index mode 字段以识别链接和子模块。
    list_fields = tuple_str_output.split()  # index 字段列表

    # 只有存在字段且 mode 不是链接或子模块时才通过。
    return bool(list_fields) and list_fields[0] not in {"120000", "160000"}

# 读取候选内容并绑定 commit blob 标识，隔离两种触发模式。
def _content_for_path(
    path_project: Path,
    path_item: Path,
    trigger: str,
    commit: str | None,
) -> tuple[bytes | None, str]:
    """按触发模式读取候选字节并返回可复核的 blob id。

    参数：
        path_project: Git 仓库项目根目录。
        path_item: 已通过候选过滤的路径。
        trigger: 当前扫描触发模式。
        commit: 可选的提交引用。
    返回：内容字节和可选的 Git blob SHA-1 二元组。
    """

    # commit 只允许 Git 对象读取，agents-refresh 才允许读取当前工作树。
    str_relative = path_item.relative_to(path_project).as_posix()  # 当前内容读取的相对路径

    # commit 模式只能读取 Git 对象，不能回退到工作树。
    if trigger == "commit" and commit:

        # 返回原始 blob 内容及其来源标识。
        return _git_object_bytes(path_project, commit, str_relative), _git_blob_id(
            path_project,
            commit,
            str_relative,
        )

    # agents-refresh 模式读取当前工作树文件内容。
    try:

        # 读取原始字节，避免换行转换污染后续摘要。
        return path_item.read_bytes(), ""

    # 文件在快照绑定后消失时报告不可用内容。
    except OSError:

        # 由调用方将空内容转换为 partial_evidence。
        return None, ""

# 读取提交树或当前 index 的 tracked 路径清单。
def _tracked_paths(path_project: Path, trigger: str, commit: str | None, base: str | None) -> list[str]:
    """读取提交或当前工作树中的 tracked 路径。

    参数：
        path_project: Git 仓库项目根目录。
        trigger: 当前扫描触发模式。
        commit: 可选的提交引用。
        base: 可选的增量比较基线提交。
    返回：Git 输出中的相对路径列表。
    """

    # 提交模式读取 commit tree；刷新模式读取当前 index 的 tracked 文件。
    if trigger == "commit":

        # 没有提交引用时无法构造 commit tree 证据。
        if not commit:

            # 返回空清单，由上层转换为阻断报告。
            return []

        # 读取提交树中的所有文件名，不访问工作树。
        tuple_int_status, tuple_str_output, _ = _run_git(  # commit tree 路径清单
            path_project,  # commit 路径清单的仓库根目录
            ["ls-tree", "-r", "--name-only", commit],  # 递归读取提交路径
        )

    # 非 commit 触发时改读当前 index 的 tracked 路径。
    else:

        # 刷新模式读取当前 index 的 tracked 文件名。
        tuple_int_status, tuple_str_output, _ = _run_git(  # 工作树 index 路径清单
            path_project,  # index 清单所属的工程根
            ["ls-files"],  # 读取当前 index 路径
        )

    # 任一 Git 清单查询失败都不能继续扫描。
    if tuple_int_status != 0:

        # 失败关闭，避免空结果被误判为无发现。
        return []

    # 先把 Git 多行输出转换为去空白的稳定路径列表。
    list_paths = [  # 清理后的 tracked 相对路径
        str_line.strip()  # 去掉 Git 输出行的外围空白
        for str_line in tuple_str_output.splitlines()  # 遍历 Git 输出的每一行
        if str_line.strip()  # 排除空白路径记录
    ]

    # 增量模式只保留基线到目标提交之间发生变化的路径。
    if trigger == "commit" and base:

        # 查询基线到目标提交之间新增或修改的路径。
        tuple_int_diff_status, tuple_str_diff, _ = _run_git(  # 增量差异查询结果
            path_project,  # diff 差异查询的仓库根目录
            ["diff", "--name-only", "--diff-filter=ACMRT", base, commit],  # 限制差异类型
        )

        # 只有成功的差异查询才能替换完整路径清单。
        if tuple_int_diff_status == 0:

            # 保持增量路径顺序与 Git 输出一致，后续过滤负责排序。
            list_paths = [
                str_line.strip()  # 去掉差异输出行的外围空白
                for str_line in tuple_str_diff.splitlines()  # 遍历差异输出的每一行
                if str_line.strip()  # 排除空白差异记录
            ]

    # 返回当前触发模式下绑定的 tracked 路径清单。
    return list_paths

# 计算当前工作树文件摘要，作为快照内容证据。
def _file_sha256(path_item: Path) -> str:
    """计算当前工作树文件的 SHA-256，不写入任何缓存。

    参数：
        path_item: 待读取的普通文件路径。
    返回：文件内容的十六进制 SHA-256 摘要。
    """

    # 摘要对象按文件读取块逐步累加，避免缓存完整文件内容。
    hash_file = hashlib.sha256()  # 文件内容摘要对象

    # 以二进制分块读取，避免一次性加载大文件。
    with path_item.open("rb") as file_item:

        # 逐块更新摘要，保持证据计算不产生临时文件。
        for bytes_chunk in iter(lambda: file_item.read(1024 * 1024), b""):

            # 将当前文件块纳入 SHA-256 摘要。
            hash_file.update(bytes_chunk)

    # 返回完整文件内容的稳定摘要。
    return hash_file.hexdigest()

# 计算已读取候选字节的摘要，避免重复访问工作树。
def _content_sha256(bytes_content: bytes) -> str:
    """计算已经读取的候选字节摘要。

    参数：
        bytes_content: 已经读取的原始候选字节。
    返回：候选字节的十六进制 SHA-256 摘要。
    """

    # 统一由原始字节计算，避免平台换行转换污染 commit 证据。
    return hashlib.sha256(bytes_content).hexdigest()

# 生成允许范围的 tracked 文件快照，绑定内容和来源摘要。
def _snapshot(
    path_project: Path,
    list_paths: list[Path],
    expected: str | None,
    *,
    trigger: str = "agents-refresh",
    commit: str | None = None,
) -> dict[str, Any]:
    """生成允许范围的 tracked 文件快照和摘要。

    参数：
        path_project: Git 仓库项目根目录。
        list_paths: 已通过候选边界过滤的路径列表。
        expected: 主 Agent 绑定的预期快照摘要。
        trigger: 当前扫描触发模式。
        commit: 可选的提交引用。
    返回：包含摘要、漂移状态、文件记录和读取错误的快照字典。
    """

    # 清单按相对路径和文件内容哈希固定编码，便于主 Agent 重绑证据。
    list_entries: list[dict[str, str]] = []  # 快照中的文件证据条目

    # 读取失败的候选单独保留，防止空结果伪装成完整快照。
    list_errors: list[dict[str, str]] = []  # 无法读取的候选错误条目

    # 清单摘要对象承接所有通过读取的文件记录。
    hash_manifest = hashlib.sha256()  # 快照清单摘要对象

    # 按稳定候选顺序绑定每个文件的相对路径和内容摘要。
    for path_item in list_paths:

        # 把当前候选转换成跨平台一致的相对路径。
        str_relative = path_item.relative_to(path_project).as_posix()  # 当前候选相对路径

        # 按触发模式读取原始内容并取得可选 blob 标识。
        tuple_bytes_content, tuple_str_blob_id = _content_for_path(  # 当前候选内容和 Git 来源
            path_project,  # 快照绑定所使用的仓库根目录
            path_item,  # 快照当前正在读取的候选文件
            trigger,  # 当前扫描触发模式
            commit,  # 可选的提交引用
        )

        # 内容缺失时记录部分证据并继续构造诊断。
        if tuple_bytes_content is None:

            # 错误条目保留相对路径，供主 Agent 复核。
            list_errors.append({"path": str_relative, "reason": "candidate content is unavailable"})

            # 当前文件没有可绑定内容，跳过其余摘要步骤。
            continue

        # 计算当前候选原始字节摘要。
        str_content_hash = _content_sha256(tuple_bytes_content)  # 当前文件内容摘要

        # 构造文件级快照记录，随后按需追加 Git blob 标识。
        dict_entry = {"path": str_relative, "sha256": str_content_hash}  # 当前文件快照条目

        # commit 模式的 blob 标识用于来源复核。
        if tuple_str_blob_id:

            # 只有 Git 返回非空标识时才写入可选字段。
            dict_entry["blob_sha1"] = tuple_str_blob_id  # 绑定 commit 来源的 blob SHA-1

        # 将完整文件记录加入快照列表。
        list_entries.append(dict_entry)

        # 先写入相对路径，固定清单条目的排序键。
        hash_manifest.update(str_relative.encode("utf-8"))

        # 写入路径和内容摘要之间的不可混淆分隔符。
        hash_manifest.update(b"\0")

        # 追加内容摘要，绑定文件原始字节。
        hash_manifest.update(str_content_hash.encode("ascii"))

        # 以换行结束条目，避免相邻字段发生拼接歧义。
        hash_manifest.update(b"\n")

    # 计算整个允许范围清单的摘要。
    str_digest = hash_manifest.hexdigest()  # 当前快照清单摘要

    # 返回机器可读且可重新绑定的快照证据。
    return {
        "algorithm": "sha256",
        "digest": str_digest,
        "expected_digest": expected or "",
        "drifted": bool(expected and expected.lower() != str_digest.lower()),
        "files": list_entries,
        "read_errors": list_errors,
    }

# 构造函数的稳定限定名，供 AST 定义证据引用。
def _qualified_name(path_relative: str, list_names: list[str], str_name: str) -> str:
    """构造稳定的模块函数限定名。

    参数：
        path_relative: 函数所在 Python 文件的相对路径。
        list_names: 外层类或函数的限定名称列表。
        str_name: 当前函数名称。
    返回：使用模块路径和嵌套名称拼接的限定名。
    """

    # 去除 .py 后缀并把路径分隔转为模块点号。
    str_module = path_relative[:-3].replace("/", ".") if path_relative.endswith(".py") else path_relative  # 模块点号名称

    # 嵌套作用域存在时把外层名称放在当前函数之前。
    if list_names:

        # 返回包含模块和嵌套作用域的稳定名称。
        return f"{str_module}:{'.'.join(list_names)}.{str_name}"

    # 顶层函数只需要模块和函数名称。
    return f"{str_module}:{str_name}"

# 提取 AST 调用节点名称，动态调用保持显式风险标记。
def _call_name(node_call: ast.Call) -> str:
    """提取调用节点的末级名称，用于保守候选统计。

    参数：
        node_call: 当前 AST 调用节点。
    返回：名称调用、属性调用的末级名称或 dynamic 标记。
    """

    # 调用目标表达式需要先拆出，后续分支才能区分名称和属性调用。
    value_func = node_call.func  # 调用目标表达式

    # 直接名称调用使用 Name 节点的标识符。
    if isinstance(value_func, ast.Name):

        # 返回直接函数或变量调用名。
        return value_func.id

    # 属性调用使用属性末级名称，避免暴露完整对象路径。
    if isinstance(value_func, ast.Attribute):

        # 返回属性调用的末级名称。
        return value_func.attr

    # 无法静态识别的调用必须保留动态风险标记。
    return "<dynamic>"

# 封装单个模块的定义证据，避免递归遍历函数携带过长参数列表。
@dataclass
class AstDefinitionContext:
    """保存 AST 定义递归遍历所需的模块级证据。

    参数：字段由当前模块解析过程填充，递归遍历只追加定义记录。
    """

    # 当前模块的候选路径对象。
    path_item: Path  # 当前 Python 文件路径

    # 当前模块的项目相对路径文本。
    str_relative: str  # 报告使用的相对路径

    # 当前扫描触发模式决定源码绝对路径的解析方式。
    trigger: str  # 提交对象或工作树读取模式

    # 当前模块的原始源码字节，用于计算内容摘要。
    bytes_source: bytes  # 未解码的 Python 源码

    # 当前模块可选的 Git blob 来源标识。
    str_blob_id: str  # commit 模式绑定的 Git SHA-1

    # 模块级导入名称证据。
    list_imports: list[str]  # 导入名称列表

    # 模块级显式导出名称证据。
    list_exports: list[str]  # __all__ 导出名称列表

    # 模块级字符串引用证据。
    list_strings: list[str]  # 有限字符串引用列表

    # 模块级注册调用证据。
    list_registry: list[str]  # 注册调用名称列表

    # 所有模块共享的函数定义收集列表。
    list_definitions: list[dict[str, Any]]  # 函数定义证据列表

# 单个 AST 节点的静态元数据容器，避免位置元组误读字段。
@dataclass(frozen=True)
class ModuleNodeMetadata:
    """保存一个 AST 节点解析出的局部证据。

    参数：字段由节点解析 helper 填充，调用方只负责合并证据。
    """

    # 当前节点贡献的导入名称。
    list_imports: list[str]  # 节点导入证据

    # 当前节点贡献的显式导出名称。
    list_exports: list[str]  # 节点导出证据

    # 当前节点贡献的字符串引用。
    list_strings: list[str]  # 节点字符串证据

    # 当前节点贡献的注册调用名称。
    list_registry: list[str]  # 节点注册证据

    # 当前节点的调用名称，非调用节点为空字符串。
    str_call: str  # 节点调用名称

# 单个模块的静态元数据容器，绑定跨函数复核所需的全部字段。
@dataclass(frozen=True)
class ModuleAstMetadata:
    """保存一个 Python 模块的静态扫描结果。

    参数：字段由模块扫描 helper 组装，调用方按字段名称读取。
    """

    # 模块导入名称列表。
    list_imports: list[str]  # 模块导入证据

    # 模块显式导出名称列表。
    list_exports: list[str]  # 模块导出证据

    # 模块有限字符串引用列表。
    list_strings: list[str]  # 模块字符串证据

    # 模块注册调用名称列表。
    list_registry: list[str]  # 模块注册证据

    # 模块级调用名称计数。
    dict_module_calls: dict[str, int]  # 模块调用计数

# AST 候选分析结果容器，绑定候选和解析不确定性两类证据。
@dataclass(frozen=True)
class AstCandidateResult:
    """保存一次 Python AST 候选扫描的完整结果。

    参数：字段由 AST 扫描过程生成，调用方按名称消费。
    """

    # 静态调用计数为零的函数候选列表。
    list_candidates: list[dict[str, Any]]  # 函数候选证据

    # 源码缺失或解析失败的不确定性列表。
    list_uncertainties: list[dict[str, Any]]  # AST 不确定性证据

# 递归收集函数、类和控制流中的 Python 定义证据。
def _visit_definition_body(
    context: AstDefinitionContext,
    list_nodes: list[ast.AST],
    list_names: list[str],
) -> None:
    """递归收集当前作用域函数及其装饰器证据。

    参数：
        context: 当前模块的定义证据上下文。
        list_nodes: 当前作用域的 AST 节点列表。
        list_names: 当前嵌套作用域名称列表。
    返回：把定义证据追加到上下文列表，不返回业务值。
    """

    # 逐节点访问当前作用域，保留函数、类和控制流中的定义。
    for node_item in list_nodes:

        # 函数定义需要完整收集调用、装饰器和来源摘要。
        if isinstance(node_item, (ast.FunctionDef, ast.AsyncFunctionDef)):

            # 生成当前函数的稳定限定名。
            str_qualified = _qualified_name(  # 当前函数限定名
                context.str_relative,  # 当前函数所在模块相对路径
                list_names,  # 外层类和函数限定名链
                node_item.name,  # 当前函数的本地名称
            )

            # 收集函数体内所有静态可见的调用名称。
            list_calls = [  # 当前函数调用名称
                _call_name(node_call)  # 调用节点的末级名称
                for node_call in ast.walk(node_item)  # 遍历函数体内节点
                if isinstance(node_call, ast.Call)  # 仅保留调用节点
            ]

            # 动态执行或反射调用会提升候选风险等级。
            list_dynamic_names = [  # 当前函数的动态风险调用
                str_call  # 当前动态调用名称
                for str_call in list_calls  # 检查函数中的静态调用列表
                if str_call == "<dynamic>"  # 保留无法静态解析的调用
                or str_call.casefold() in {"eval", "exec", "getattr", "import_module"}  # 标记反射或动态执行风险
            ]

            # 保留装饰器的源级表达式，供注册和导出复核。
            list_decorators = [  # 当前函数装饰器文本
                ast.unparse(node_decorator)  # 转换装饰器 AST 为稳定文本
                for node_decorator in node_item.decorator_list  # 遍历函数装饰器
            ]

            # 记录函数定义的调用、导入、导出、动态和内容证据。
            context.list_definitions.append(
                {
                    "qualified_name": str_qualified,
                    "name": node_item.name,
                    "path": context.str_relative,
                    "absolute_path": str(
                        context.path_item
                        if context.trigger == "commit"
                        else context.path_item.resolve(strict=False)
                    ),
                    "start_line": int(node_item.lineno),
                    "end_line": int(getattr(node_item, "end_lineno", node_item.lineno)),
                    "calls": list_calls,
                    "imports": sorted(set(context.list_imports)),
                    "exports": sorted(set(context.list_exports)),
                    "decorators": list_decorators,
                    "string_references": sorted(set(context.list_strings))[:128],
                    "registry_references": sorted(set(context.list_registry)),
                    "dynamic_risk": bool(list_dynamic_names),
                    "dynamic_risk_checks": list_dynamic_names,
                    "content_sha256": _content_sha256(context.bytes_source),
                    "blob_sha1": context.str_blob_id,
                }
            )

            # 继续深入函数体，收集其嵌套函数定义。
            _visit_definition_body(context, node_item.body, list_names + [node_item.name])

        # 类定义只改变限定名称，不改变当前模块证据。
        elif isinstance(node_item, ast.ClassDef):

            # 将类名称加入嵌套作用域后继续遍历类体。
            _visit_definition_body(context, node_item.body, list_names + [node_item.name])

        # 控制流节点可能包含局部函数，需要递归访问子节点。
        elif isinstance(node_item, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.AsyncWith)):

            # 使用 AST 子节点列表保持定义发现的原有顺序。
            _visit_definition_body(context, list(ast.iter_child_nodes(node_item)), list_names)

# 从 __all__ 赋值节点提取可静态确认的导出名称。
def _module_export_names(node_assign: ast.Assign) -> list[str]:
    """读取模块级 __all__ 字符串导出，无法确认时返回空列表。

    参数：
        node_assign: 当前模块中的赋值 AST 节点。
    返回：静态可见的字符串导出名称列表。
    """

    # 逐个确认赋值目标是否是模块公开接口声明。
    for node_target in node_assign.targets:

        # 非名称目标不可能是 __all__ 导出声明。
        if not isinstance(node_target, ast.Name) or node_target.id != "__all__":

            # 继续检查同一赋值中的其他目标。
            continue

        # 只有列表或元组字面量能静态提供导出集合。
        if not isinstance(node_assign.value, (ast.List, ast.Tuple)):

            # 动态构造的导出集合必须留给人工复核。
            return []

        # 提取字面量中的字符串导出名称，忽略动态元素。
        return [
            node_element.value
            for node_element in node_assign.value.elts
            if isinstance(node_element, ast.Constant) and isinstance(node_element.value, str)
        ]

    # 没有 __all__ 目标时不产生导出证据。
    return []

# 解析单个 AST 节点，隔离模块扫描循环中的分支复杂度。
def _module_node_metadata(
    node_item: ast.AST,
) -> ModuleNodeMetadata:
    """提取一个 AST 节点的导入、导出、字符串和调用证据。

    参数：
        node_item: 当前模块遍历到的 AST 节点。
    返回：导入、导出、字符串、注册调用和调用名称的五元组。
    """

    # 默认空证据表示当前节点不属于受支持的静态类别。
    list_imports: list[str] = []  # 当前节点导入证据

    # 导出证据只在 __all__ 字面量节点中产生。
    list_exports: list[str] = []  # 当前节点导出证据

    # 单节点最多贡献一个字符串常量，数量上限在调用方统一控制。
    list_strings: list[str] = []  # 当前节点字符串证据

    # 注册调用以列表形式返回，保持调用方可直接合并。
    list_registry: list[str] = []  # 当前节点注册证据

    # 空名称表示当前节点不是函数调用。
    str_call = ""  # 当前节点调用名称

    # 记录普通 import 的完整模块名称。
    if isinstance(node_item, ast.Import):

        # 将 import 别名展开为可读的模块名称。
        list_imports.extend(alias.name for alias in node_item.names)

    # 记录 from import 的模块和名称组合。
    elif isinstance(node_item, ast.ImportFrom):

        # 缺少 module 时使用空字符串保持字段稳定。
        str_module = node_item.module or ""  # from import 的模块名

        # 将每个导入名称绑定到其来源模块。
        list_imports.extend(f"{str_module}:{alias.name}" for alias in node_item.names)

    # 保留字符串常量，数量上限由模块级汇总逻辑决定。
    elif isinstance(node_item, ast.Constant) and isinstance(node_item.value, str):

        # 当前节点的字符串值可以直接作为引用证据。
        list_strings.append(node_item.value)

    # 统计调用名称并记录动态注册相关调用。
    elif isinstance(node_item, ast.Call):

        # 提取调用末级名称，动态调用保留风险标记。
        str_call = _call_name(node_item)  # 当前调用末级名称

        # 常见注册调用必须记录为人工复核证据。
        if str_call.casefold() in {"register", "register_function", "route", "command", "add_command"}:

            # 注册调用可能通过动态路径使用，不能自动删除。
            list_registry.append(str_call)

    # 从 __all__ 赋值中提取显式导出名称。
    elif isinstance(node_item, ast.Assign):

        # 一个赋值节点可能包含多个目标，交给专用 helper 提取导出名称。
        list_exports.extend(_module_export_names(node_item))

    # 返回当前节点的固定证据形状，避免调用方猜测分支类型。
    return ModuleNodeMetadata(
        list_imports=list_imports,
        list_exports=list_exports,
        list_strings=list_strings,
        list_registry=list_registry,
        str_call=str_call,
    )

# 收集单个模块的静态导入、导出、字符串和调用证据。
def _module_ast_metadata(
    tree_module: ast.Module,
) -> ModuleAstMetadata:
    """提取模块级静态元数据，供函数候选分析复用。

    参数：
        tree_module: 已经通过 UTF-8 解析的 Python 模块 AST。
    返回：导入、导出、字符串、注册调用和调用计数的五元组。
    """

    # 导入名称用于人工判断模块依赖是否仍然被使用。
    list_imports: list[str] = []  # 当前模块导入名称

    # 显式导出名称用于保留模块公开接口证据。
    list_exports: list[str] = []  # 当前模块显式导出名称

    # 字符串引用限制数量，避免报告被大文本撑大。
    list_strings: list[str] = []  # 当前模块字符串引用

    # 注册调用名称用于标记可能的外部入口。
    list_registry: list[str] = []  # 当前模块注册调用名称

    # 模块调用计数用于后续零调用候选筛选。
    dict_module_calls: dict[str, int] = {}  # 全局调用名称累加表

    # 遍历节点并合并每个节点的静态证据。
    for node_item in ast.walk(tree_module):

        # 统一解析节点类别，保持主循环只有一层控制流。
        module_node_metadata_record: ModuleNodeMetadata = _module_node_metadata(node_item)  # 当前节点静态元数据

        # 合并导入、导出和注册调用证据。
        list_imports.extend(module_node_metadata_record.list_imports)

        # 合并当前节点声明的公开导出名称。
        list_exports.extend(module_node_metadata_record.list_exports)

        # 合并当前节点发现的注册入口调用。
        list_registry.extend(module_node_metadata_record.list_registry)

        # 只保留前 128 个字符串，避免报告无限增长。
        if len(list_strings) < 128:

            # 计算本轮仍可接纳的字符串数量。
            int_remaining = 128 - len(list_strings)  # 当前字符串证据剩余容量

            # 截断节点证据后追加到模块级列表。
            list_strings.extend(module_node_metadata_record.list_strings[:int_remaining])

        # 将每个调用名称累加到全模块统计中。
        if module_node_metadata_record.str_call:

            # 调用计数供零调用候选判断使用。
            dict_module_calls[module_node_metadata_record.str_call] = (  # 更新当前节点调用计数
                dict_module_calls.get(module_node_metadata_record.str_call, 0) + 1  # 累加节点调用量
            )

    # 返回固定顺序的元数据，保证调用方无需重新遍历模块。
    return ModuleAstMetadata(
        list_imports=list_imports,
        list_exports=list_exports,
        list_strings=list_strings,
        list_registry=list_registry,
        dict_module_calls=dict_module_calls,
    )

# 解析 Python AST 并构造仅供主 Agent 复核的候选证据。
def _ast_candidates(
    path_project: Path,
    list_paths: list[Path],
    *,
    trigger: str = "agents-refresh",
    commit: str | None = None,
) -> AstCandidateResult:
    """解析 Python 定义并保留候选所需的引用、导出和动态风险证据。

    参数：
        path_project: Git 仓库项目根目录。
        list_paths: 已通过边界过滤的候选路径。
        trigger: 当前扫描触发模式。
        commit: 可选的提交引用。
    返回：候选函数证据列表和解析不确定性列表。
    """

    # 第一遍收集定义与模块级证据，第二遍只把零调用项标记为候选。
    list_definitions: list[dict[str, Any]] = []  # 已解析的函数定义证据

    # 解析失败和内容缺失都必须保留为人工复核不确定性。
    list_uncertainties: list[dict[str, Any]] = []  # 无法完整解析的证据记录

    # 模块级调用计数用于避免把静态可见入口误报为零调用函数。
    dict_module_calls: dict[str, int] = {}  # 候选扫描跨模块调用计数

    # 逐个读取允许范围内的 Python 文件。
    for path_item in list_paths:

        # Markdown 或其他后缀不进入 AST 分析。
        if path_item.suffix.lower() != ".py":

            # 当前候选不是 Python 文件，交给文档扫描路径处理。
            continue

        # 计算报告使用的相对路径。
        str_relative = path_item.relative_to(path_project).as_posix()  # 当前 Python 相对路径

        # 按触发模式取得原始源码和可选 blob 标识。
        tuple_bytes_source, tuple_str_blob_id = _content_for_path(  # Python 源码和来源标识
            path_project,  # AST 扫描绑定的仓库根目录
            path_item,  # 当前待解析的 Python 文件
            trigger,  # 当前源码来源触发模式
            commit,  # commit 模式的来源引用
        )

        # 缺少源码字节时保留不确定性，不生成虚假的 AST 结论。
        if tuple_bytes_source is None:

            # 当前文件无法提供完整的 Python 证据。
            list_uncertainties.append(
                {"path": str_relative, "kind": "partial_evidence", "reason": "Python bytes unavailable"}
            )

            # 跳过当前文件的后续解析步骤。
            continue

        # 将 UTF-8 源码解析成 AST，保留语法错误证据。
        try:

            # 源码文本使用 UTF-8 解码以保持报告行号一致。
            str_source = tuple_bytes_source.decode("utf-8")  # 当前文件源码文本

            # AST 文件名使用项目相对路径，便于主 Agent 定位。
            tree_module = ast.parse(str_source, filename=str_relative)  # 当前模块 AST

        # 语法或编码错误只形成部分解析不确定性。
        except (SyntaxError, UnicodeDecodeError) as exc:

            # 记录异常文本而不把解析失败误报为无候选。
            list_uncertainties.append(
                {"path": str_relative, "kind": "partial_parse", "reason": str(exc)}
            )

            # 当前文件不能安全进入第二遍定义收集。
            continue

        # 提取当前模块的静态元数据，避免候选函数继续承担模块扫描职责。
        module_ast_metadata_record: ModuleAstMetadata = _module_ast_metadata(tree_module)  # 当前模块静态证据

        # 合并当前模块调用计数，保留跨文件候选筛选语义。
        for str_call, int_call_count in module_ast_metadata_record.dict_module_calls.items():

            # 每个模块的调用次数累加到全局证据。
            dict_module_calls[str_call] = dict_module_calls.get(str_call, 0) + int_call_count  # 累加当前模块调用量

        # 将当前模块证据封装后交给递归定义收集器。
        definition_context = AstDefinitionContext(  # 当前模块定义上下文
            path_item=path_item,  # 把文件定位绑定到定义上下文
            str_relative=str_relative,  # 供报告引用的文件键

            # 触发来源和原始内容字段保持同一证据来源。
            trigger=trigger,  # 决定源码来源的触发标签
            bytes_source=tuple_bytes_source,  # 未解码源码字节
            str_blob_id=tuple_str_blob_id,  # 可选 Git blob 标识

            # 模块静态证据和共享定义容器交给递归收集器。
            list_imports=module_ast_metadata_record.list_imports,  # 模块 import 证据
            list_exports=module_ast_metadata_record.list_exports,  # 模块公开接口证据
            list_strings=module_ast_metadata_record.list_strings,  # 模块字面量证据
            list_registry=module_ast_metadata_record.list_registry,  # 模块注册入口证据
            list_definitions=list_definitions,  # 跨模块函数定义容器
        )

        # 从模块顶层开始收集所有函数定义。
        _visit_definition_body(definition_context, tree_module.body, [])

    # 名称调用统计只作为候选证据，不直接推出删除结论。
    dict_called: dict[str, int] = dict(dict_module_calls)  # 全局调用名称计数

    # 将每个函数体内调用也并入候选计数。
    for dict_definition in list_definitions:

        # 一个函数可能包含多个相同或不同的调用名称。
        for str_call in dict_definition["calls"]:

            # 调用次数只用于候选筛选，不产生删除决定。
            dict_called[str_call] = dict_called.get(str_call, 0) + 1  # 累加函数体内调用量

    # 只把静态调用计数为零的函数标记为待主 Agent 复核候选。
    list_candidates: list[dict[str, Any]] = []  # 函数候选证据列表

    # 构造候选级引用、回滚和验证证据。
    for dict_definition in list_definitions:

        # 读取当前函数名称的静态调用次数。
        int_call_count = dict_called.get(str(dict_definition["name"]), 0)  # 当前函数调用次数

        # 有静态调用的函数不属于零调用候选。
        if int_call_count != 0:

            # 保留函数但不产生删除候选。
            continue

        # 将当前函数完整证据追加到候选清单。
        list_candidates.append({
            "finding_id": f"code-function-{len(list_candidates) + 1:04d}",
            "qualified_name": dict_definition["qualified_name"],
            "path": dict_definition["path"],
            "absolute_path": dict_definition["absolute_path"],
            "start_line": dict_definition["start_line"],
            "end_line": dict_definition["end_line"],
            "content_sha256": dict_definition["content_sha256"],
            "blob_sha1": dict_definition["blob_sha1"],
            "tool_evidence": {
                "call_count": 0,
                "dynamic_risk": dict_definition["dynamic_risk"],
                "dynamic_risk_checks": dict_definition["dynamic_risk_checks"],
                "imports": dict_definition["imports"],
                "exports": dict_definition["exports"],
                "decorators": dict_definition["decorators"],
                "string_references": dict_definition["string_references"],
                "registry_references": dict_definition["registry_references"],
                "graph_reference_checks": {"status": "main_agent_required"},
                "tests_markdown_alignment": {"status": "main_agent_required"},
                "candidate_only": True,
            },
            "deletion_plan": {
                "status": "candidate_only",
                "functions": [dict_definition["qualified_name"]],
                "callers_exports_tests_markdown": "main_agent_must_verify",
                "execution_order": ["main_review", "user_decision", "delete_if_authorized", "remote_regression"],
                "rollback": "restore_exact_content_sha256",
                "verification": ["graph", "exports", "dynamic references", "tests", "Markdown"],
            },
            "confidence": "low",
            "reason": "AST 未发现静态入调用；仍需图谱、导出、注册、测试和文档人工核实。",
        })

    # 返回候选列表和所有不确定性，保持主 Agent 的人工复核边界。
    return AstCandidateResult(
        list_candidates=list_candidates,
        list_uncertainties=list_uncertainties,
    )

# 检查 Markdown 中明确引用的 Python 路径是否仍在允许清单内。
def _markdown_findings(
    path_project: Path,
    list_paths: list[Path],
    set_python_paths: set[str],
    *,
    trigger: str = "agents-refresh",
    commit: str | None = None,
) -> list[dict[str, Any]]:
    """检查 Markdown 中明确写出的 Python 路径是否仍存在。

    参数：
        path_project: Git 仓库项目根目录。
        list_paths: 已通过边界过滤的 Markdown 和 Python 路径。
        set_python_paths: 允许引用的 Python 相对路径集合。
        trigger: 当前扫描触发模式。
        commit: 可选的提交引用。
    返回：Markdown 路径引用不匹配和部分证据列表。
    """

    # 只审查 .md，其他文档格式完全不进入此函数。
    list_findings: list[dict[str, Any]] = []  # Markdown 路径发现列表

    # 路径正则只匹配可进入 Python 清单比对的 Markdown 引用。
    pattern_path = re.compile(r"[A-Za-z0-9_./-]+\.py")  # Python 路径匹配表达式

    # 逐个读取当前候选集合中的 Markdown 文档。
    for path_item in list_paths:

        # Python 文件和其他后缀不进入 Markdown 路径扫描。
        if path_item.suffix.lower() != ".md":

            # 当前候选不是 Markdown 文档，继续下一个文件。
            continue

        # 计算报告和诊断使用的相对文档路径。
        str_relative = path_item.relative_to(path_project).as_posix()  # 当前文档的项目相对路径

        # 获取当前文档的原始字节，commit 模式仍只读 Git 对象。
        tuple_bytes_source, _ = _content_for_path(  # 当前文档原始内容
            path_project,  # 文档扫描绑定的仓库根目录
            path_item,  # 当前待扫描的 Markdown 文件
            trigger,  # 当前文档来源触发模式
            commit,  # 文档对应的提交对象引用
        )

        # 文档内容缺失时记录部分证据并停止当前文件扫描。
        if tuple_bytes_source is None:

            # 保留文档路径和缺失原因，避免误报无不匹配。
            list_findings.append(
                {"path": str_relative, "kind": "partial_evidence", "reason": "Markdown bytes unavailable"}
            )

            # 当前文档没有可扫描的内容。
            continue

        # 将 UTF-8 Markdown 拆成带一基行号的文本行。
        try:

            # 保留原始行顺序，便于主 Agent 定位引用。
            list_lines = tuple_bytes_source.decode("utf-8").splitlines()  # 解码后的 Markdown 物理行

        # 编码失败只形成部分解析证据。
        except UnicodeDecodeError as exc:

            # 记录解码错误并跳过当前文档。
            list_findings.append(
                {"path": str_relative, "kind": "partial_parse", "reason": str(exc)}
            )

            # 当前文件无法安全执行路径匹配。
            continue

        # 逐行扫描显式写出的 Python 路径。
        for int_line, str_line in enumerate(list_lines, start=1):

            # 一行可能包含多个 Python 路径引用。
            for match_path in pattern_path.finditer(str_line):

                # 使用 POSIX 分隔符与 tracked 清单进行比较。
                str_reference = match_path.group(0).replace("\\", "/")  # 文档引用路径

                # 只对不在允许 Python 清单中的引用生成发现。
                if str_reference not in set_python_paths:

                    # 记录行号、引用和需要用户决定的治理边界。
                    list_findings.append({
                        "finding_id": f"doc-path-{len(list_findings) + 1:04d}",
                        "kind": "document_code_path_mismatch",
                        "path": str_relative,
                        "line": int_line,
                        "reference": str_reference,
                        "reasoning": "Markdown 明确引用的 Python 路径不在允许范围内的 tracked 文件清单中。",
                        "requires_user_decision": True,
                    })

    # 返回文档路径发现，调用方负责将其合并进严格报告。
    return list_findings

# 构造单一 JSON 报告，统一所有主 Agent 可消费的字段。
def build_report(
    *,
    trigger: str,
    **report_fields: Any,
) -> dict[str, Any]:
    """构造 schema_version=1 的严格 gardener 报告。

    参数：
        trigger: 触发扫描的模式。
        report_fields: 包含 scope、snapshot、tool_run、document_findings、
            code_findings、rejected_candidates、uncertainties 和 verdict 的报告字段。
    返回：符合 schema_version=1 的完整报告字典。
    """

    # 未知 verdict 不得混入机器可读协议。
    str_verdict = str(report_fields.get("verdict", ""))  # 受控的最终结论

    # 不在协议集合内的结论统一收敛为阻断状态。
    if str_verdict not in VERDICTS:

        # 未知结论不能被主 Agent 当作成功结果消费。
        str_verdict = BLOCKING_VERDICT  # 将未知报告结论收敛为角色卡阻断结论

    # 返回固定字段顺序的机器可读报告。
    return {
        "schema_version": SCHEMA_VERSION,
        "worker": WORKER_NAME,
        "trigger": trigger,
        "scope": report_fields["scope"],
        "snapshot": report_fields["snapshot"],
        "tool_run": report_fields["tool_run"],
        "document_findings": report_fields["document_findings"],
        "code_findings": report_fields["code_findings"],
        "rejected_candidates": report_fields["rejected_candidates"],
        "uncertainties": report_fields["uncertainties"],
        "verdict": str_verdict,
    }

# 校验提交参数，防止不受控文本进入只读 Git 查询。
def _valid_git_ref(value_ref: str | None) -> bool:
    """判断提交参数是否为安全的 Git 引用或十六进制摘要。

    参数：
        value_ref: 待校验的提交或基线引用。
    返回：引用满足命令参数安全约束时返回 True。
    """

    # 参数作为 argv 传递，仍拒绝空白、选项和双点范围表达式。
    str_ref = str(value_ref or "")  # 规范化后的 Git 引用文本

    # 空值、选项前缀和控制空白不能进入 subprocess argv。
    if not str_ref or str_ref.startswith("-") or any(char in str_ref for char in " \t\r\n"):

        # 失败关闭，拒绝不受控的命令参数。
        return False

    # 双点表达式是范围语法，不是单一安全引用。
    if ".." in str_ref:

        # 只接受单提交或单对象引用。
        return False

    # 允许短 SHA、HEAD 相对引用和安全字符组成的分支名。
    return bool(re.fullmatch(r"[0-9a-fA-F]{7,64}|HEAD(?:~[0-9]+)?|[A-Za-z0-9_./-]+", str_ref))

# 校验 gardener 触发模式的参数组合，避免无证据启动扫描。
def _validate_trigger(trigger: str, commit: str | None, base: str | None, expected: str | None) -> list[str]:
    """返回触发模式的参数错误。

    参数：
        trigger: commit 或 agents-refresh 触发模式。
        commit: 可选的提交引用。
        base: 可选的增量比较基线引用。
        expected: agents-refresh 必需的预期快照摘要。
    返回：参数错误文本列表；空列表表示组合有效。
    """

    # 所有参数问题集中收集，保证调用方一次看到完整诊断。
    list_errors: list[str] = []  # 当前触发参数错误列表

    # 只允许两种已定义的触发模式。
    if trigger not in {"commit", "agents-refresh"}:

        # 未知模式无法选择安全证据源。
        list_errors.append("trigger must be commit or agents-refresh")

    # commit 模式必须提供安全的提交引用。
    if trigger == "commit":

        # 缺失或危险引用均拒绝执行 Git 查询。
        if not _valid_git_ref(commit):

            # 保留可读诊断供 CLI 报告使用。
            list_errors.append("commit trigger requires a safe Git commit reference")

    # agents-refresh 模式必须绑定主 Agent 的预期快照。
    if trigger == "agents-refresh" and not expected:

        # 无预期摘要无法检测扫描过程中的文件漂移。
        list_errors.append("agents-refresh requires expected-snapshot-sha256")

    # 提供 base 时同样校验其 Git 引用安全性。
    if base and not _valid_git_ref(base):

        # 错误文本交给调用方统一构造阻断报告。
        list_errors.append("base must be a safe Git commit reference")

    # 返回全部错误，避免调用方只看到第一处问题。
    return list_errors

# 构造未读取文件时仍可复核的空快照结构。
def _empty_snapshot(expected_snapshot_sha256: str | None) -> dict[str, Any]:
    """返回带有预期摘要绑定信息的空快照。

    参数：
        expected_snapshot_sha256: 调用方声明的预期快照摘要。
    返回：算法、摘要、漂移标记和空文件列表组成的快照字典。
    """

    # 空快照仍保留算法和预期摘要，避免阻断报告失去绑定信息。
    return {
        "algorithm": "sha256",
        "digest": "",
        "expected_digest": expected_snapshot_sha256 or "",
        "drifted": False,
        "files": [],
    }

# 构造分析失败或证据不完整时的统一阻断结果。
def _blocked_analysis_result(
    uncertainty: dict[str, Any],
    expected_snapshot_sha256: str | None,
    mode: str,
    *,
    candidate_paths: list[str] | None = None,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构造不含虚假成功结论的分析阻断报告。

    参数：
        uncertainty: 当前阻断或部分证据的不确定性记录。
        expected_snapshot_sha256: 调用方绑定的预期快照摘要。
        mode: 当前全量或增量扫描模式。
        candidate_paths: 已确认的候选相对路径，可选。
        snapshot: 已生成的快照证据，可选。
    返回：字段完整且 verdict 为 BLOCKED 的分析结果。
    """

    # 缺省候选清单保持为空，避免把未知范围误报为无发现。
    list_candidate_paths: list[str] = candidate_paths or []  # 阻断结果中的候选路径

    # 没有快照时构造空摘要，仍保留预期绑定信息。
    dict_snapshot: dict[str, Any] = snapshot or _empty_snapshot(expected_snapshot_sha256)  # 阻断路径的快照证据

    # 返回与正常分析同形的机器可读阻断结果。
    return {
        "candidate_paths": list_candidate_paths,
        "document_findings": [],
        "code_findings": [],
        "rejected_candidates": [],
        "uncertainties": [uncertainty],
        "snapshot": dict_snapshot,
        "tool_run": {"tool": "pycode_gardener.py", "mode": mode, "function_candidates": []},
        "verdict": BLOCKING_VERDICT,
    }

# 过滤工作树或提交清单中的普通文件候选，隔离 Git 类型检查。
def _filter_regular_candidates(
    path_project: Path,
    list_candidates: list[Path],
    trigger: str,
    commit: str | None,
) -> list[Path]:
    """只保留在对应 Git 证据源中确认的普通 blob 候选。

    参数：
        path_project: Git 仓库项目根目录。
        list_candidates: 已通过路径边界过滤的候选列表。
        trigger: 当前扫描触发模式。
        commit: 可选的提交引用。
    返回：通过 Git regular-file 检查的候选路径列表。
    """

    # Git 类型检查必须逐项绑定项目相对路径，避免路径歧义。
    list_regular_candidates: list[Path] = []  # 通过 regular-file 检查的候选

    # 逐项确认候选在对应 Git 证据源中是普通文件。
    for path_item in list_candidates:

        # 只有 Git 明确确认的 regular blob 才能继续读取内容。
        if _tracked_regular(
            path_project,  # Git 类型检查使用的仓库根目录
            path_item.relative_to(path_project).as_posix(),  # 候选的项目相对路径
            trigger,  # 当前触发模式
            commit,  # 可选提交引用
        ):

            # 保留已通过类型检查的候选路径。
            list_regular_candidates.append(path_item)

    # 返回经过 Git 类型确认的候选列表。
    return list_regular_candidates

# 构造允许范围内的 Python 相对路径集合，供 Markdown 对齐检查使用。
def _python_candidate_paths(path_project: Path, list_candidates: list[Path]) -> set[str]:
    """返回候选列表中的 Python 项目相对路径。

    参数：
        path_project: Git 仓库项目根目录。
        list_candidates: 已通过边界和 Git 类型检查的候选路径。
    返回：用于 Markdown 引用比对的 Python 相对路径集合。
    """

    # 只保留 .py 候选，统一使用 POSIX 路径作为报告键。
    return {
        path_item.relative_to(path_project).as_posix()
        for path_item in list_candidates
        if path_item.suffix.lower() == ".py"
    }

# 根据触发模式执行允许范围内的完整分析。
def analyze_project(
    project_root: str | Path,
    source_root: str | Path,
    tests_root: str | Path,
    **analysis_options: Any,
) -> dict[str, Any]:
    """读取允许范围并执行候选、文档、快照和证据分析。

    参数：
        project_root: Git 仓库项目根目录。
        source_root: 允许扫描的源码根目录。
        tests_root: 允许扫描的测试根目录。
        analysis_options: 包含 trigger、commit、base、expected_snapshot_sha256
            和 mode 的分析选项。
    返回：候选、文档、快照和不确定性组成的分析字典。
    """

    # 将兼容的关键字选项收敛为本地变量，保留既有调用协议。
    str_trigger: str = str(analysis_options.get("trigger", ""))  # 当前分析触发模式

    # 提交引用只在 commit 模式下参与 Git 对象读取。
    str_commit: str | None = cast(str | None, analysis_options.get("commit"))  # Git 对象来源引用

    # 增量基线只用于 commit 模式的差异路径筛选。
    str_base: str | None = cast(str | None, analysis_options.get("base"))  # 可选增量基线

    # 预期快照摘要用于检测 agents-refresh 过程中的漂移。
    str_expected_snapshot_sha256: str | None = cast(  # 绑定的预期快照
        str | None,  # 可选文本类型
        analysis_options.get("expected_snapshot_sha256"),  # CLI 绑定的摘要文本
    )  # 保留摘要为空时的 fail-closed 语义

    # 未声明模式时保持完整扫描的历史默认值。
    str_mode: str = str(analysis_options.get("mode", "full"))  # 全量或增量模式

    # 根目录和相对来源先规范化，所有后续路径均受同一边界约束。
    path_project = _absolute_root(project_root)  # 规范化后的项目根路径

    # 收集触发参数错误，后续统一转成阻断报告。
    list_errors = _validate_trigger(  # 触发参数校验列表
        str_trigger,  # 校验用的触发模式文本
        str_commit,  # 校验用的目标提交文本
        str_base,  # 校验用的比较基线文本
        str_expected_snapshot_sha256,  # 预期快照摘要
    )  # 触发参数错误列表

    # 模式值必须落在受支持的完整或增量扫描集合内。
    if str_mode not in {"incremental", "full"}:

        # 将非法模式加入同一阻断错误列表。
        list_errors.append("mode must be incremental or full")

    # 参数错误时不启动 Git 或工作树读取。
    if list_errors:

        # 把全部参数错误保留在一个机器可读不确定性记录中。
        return _blocked_analysis_result(
            {"kind": "invalid_arguments", "errors": list_errors},
            str_expected_snapshot_sha256,
            str_mode,
        )

    # Git 读取失败必须停线，不允许把空清单当作无发现。
    list_tracked = _tracked_paths(path_project, str_trigger, str_commit, str_base)  # Git tracked 路径证据

    # Git 无法提供 tracked 路径时不能继续作无发现结论。
    if not list_tracked:

        # 将缺失的 Git 证据显式标记为阻断。
        return _blocked_analysis_result(
            {"kind": "git_evidence_missing", "reason": "tracked path query returned no files"},
            str_expected_snapshot_sha256,
            str_mode,
        )

    # 过滤只在用户声明的 source/tests 两个根内进行。
    list_candidates = filter_candidate_paths(  # source/tests 边界过滤结果
        list_tracked,  # Git 返回的已跟踪路径
        path_project,  # 候选所属项目根
        source_root,  # 允许扫描的源码根
        tests_root,  # 允许扫描的测试根
        trigger=str_trigger,  # 内容读取的触发来源
    )

    # 再确认 Git 对象类型，拒绝链接和非普通文件。
    list_candidates = _filter_regular_candidates(  # regular-file 复核后的候选
        path_project,  # regular-file 复核所属的仓库根
        list_candidates,  # 路径边界过滤结果
        str_trigger,  # regular-file 复核的触发来源
        str_commit,  # regular-file 复核的提交对象
    )

    # 绑定候选内容摘要，确保后续分析使用同一快照。
    dict_snapshot = _snapshot(  # 当前候选的内容快照
        path_project,  # 快照使用的仓库根目录
        list_candidates,  # 已通过 regular-file 检查的候选
        str_expected_snapshot_sha256,  # 调用方绑定的预期摘要
        trigger=str_trigger,  # 当前内容读取模式
        commit=str_commit,  # 快照读取的提交对象
    )

    # 快照读取错误表示证据不完整，不能进入 AST 或 Markdown 分析。
    if dict_snapshot.get("read_errors"):

        # 保留已确认路径和快照错误，供主 Agent 重新绑定证据。
        return _blocked_analysis_result(
            {"kind": "partial_evidence", "errors": dict_snapshot["read_errors"]},
            str_expected_snapshot_sha256,
            str_mode,
            candidate_paths=[item.relative_to(path_project).as_posix() for item in list_candidates],
            snapshot=dict_snapshot,
        )

    # 预期摘要漂移时必须停止，避免把不一致源码当作当前证据。
    if dict_snapshot["drifted"]:

        # 将漂移快照原样返回，支持上层重新计算绑定摘要。
        return _blocked_analysis_result(
            {"kind": "SNAPSHOT_DRIFT", "reason": "allowed tracked snapshot differs from expected digest"},
            str_expected_snapshot_sha256,
            str_mode,
            candidate_paths=[item.relative_to(path_project).as_posix() for item in list_candidates],
            snapshot=dict_snapshot,
        )

    # AST 候选与 Markdown 对齐检查分别保留证据来源。
    ast_candidate_result_record: AstCandidateResult = _ast_candidates(  # Python AST 候选分析结果
        path_project,  # AST 候选扫描的仓库根
        list_candidates,  # 已确认的候选文件
        trigger=str_trigger,  # AST 源码来源模式
        commit=str_commit,  # AST 对应的提交对象
    )

    # 提取 AST 函数候选，保持结果字段的明确类型。
    list_function_candidates = ast_candidate_result_record.list_candidates  # 静态函数候选证据

    # 提取 AST 解析不确定性，不能与无发现混淆。
    list_parse_uncertainties = ast_candidate_result_record.list_uncertainties  # 解析不确定性证据

    # 构造 Markdown 引用比对所需的 Python 相对路径集合。
    set_python_paths = _python_candidate_paths(path_project, list_candidates)  # Python 相对路径集合

    # 扫描 Markdown 中的 Python 路径引用。
    list_document_findings = _markdown_findings(  # Markdown 路径发现结果
        path_project,  # 文档扫描所属项目根
        list_candidates,  # Markdown 对齐的候选文件
        set_python_paths,  # 允许引用的 Python 路径
        trigger=str_trigger,  # Markdown 内容来源模式
        commit=str_commit,  # Markdown 的提交内容来源
    )

    # 后续报告统一复用 AST 解析不确定性。
    list_uncertainties = list_parse_uncertainties  # 当前分析不确定性列表

    # 代码发现保留扩展点，但 gardener 不自动生成删除结论。
    list_code_findings: list[dict[str, Any]] = []  # 当前代码发现列表

    # 默认结论排除阻断与范围拒绝，只允许配置声明的无发现结论。
    str_scope_rejection = worker_scope_rejection_verdict(WORKER_NAME)  # 配置声明的范围拒绝结论

    # 从剩余角色结论中选取无发现默认值。
    str_verdict = next(  # 当前分析默认结论
        (
            str_item  # 当前候选 verdict 文本
            for str_item in sorted(VERDICTS)  # 遍历配置声明的候选结论
            if str_item not in {BLOCKING_VERDICT, str_scope_rejection}  # 排除阻断与范围拒绝结论
            and not str_item.startswith("FINDINGS")  # 排除人工复核结论
        ),
        "",  # 无候选结论时返回空文本
    )  # 当前分析结论

    # 存在函数或文档发现时要求主 Agent 人工复核。
    if list_function_candidates or list_document_findings:

        # 发现结果只能进入人工复核流程。
        str_verdict = next((str_item for str_item in VERDICTS if "FINDINGS" in str_item), "")  # 人工复核结论

    # 解析不确定性优先阻断无其他发现的结果。
    if list_uncertainties:

        # 有候选时保留人工复核结论，否则明确阻断。
        str_verdict = BLOCKING_VERDICT if not list_function_candidates and not list_document_findings else str_verdict  # 不确定性收敛结论

    # 返回完整的候选、文档、快照和不确定性证据。
    return {
        "candidate_paths": [item.relative_to(path_project).as_posix() for item in list_candidates],
        "document_findings": list_document_findings,
        "code_findings": list_code_findings,
        "rejected_candidates": [],
        "uncertainties": list_uncertainties,
        "snapshot": dict_snapshot,
        "tool_run": {
            "tool": "pycode_gardener.py",
            "mode": str_mode,
            "function_candidates": list_function_candidates,
            "ast": {"candidate_count": len(list_function_candidates)},
        },
        "verdict": str_verdict,
    }

# 构造报告 scope 字段，只描述允许范围而不读取禁止目录。
def _scope_payload(project_root: Path, source_root: str | Path, tests_root: str | Path, mode: str) -> dict[str, Any]:
    """构造报告 scope 字段，不读取禁止目录。

    参数：
        project_root: 已规范化的项目根目录。
        source_root: 允许扫描的源码根目录。
        tests_root: 允许扫描的测试根目录。
        mode: 当前 gardener 扫描模式。
    返回：供报告使用的范围描述字典。
    """

    # 绝对路径只用于执行证据，同时构造跨平台可比较的范围字段。
    return {
        "project_root": str(project_root),
        "source_root": str(Path(source_root)),
        "tests_root": str(Path(tests_root)),
        "allowed_extensions": [".md", ".py"],
        "mode": mode,
        "forbidden_segments": sorted(FORBIDDEN_SEGMENTS),
    }

# 构造参数或异常路径的完整阻断报告，保持报告 schema 闭合。
def _empty_report(trigger: str, scope: dict[str, Any], reason: str, mode: str) -> dict[str, Any]:
    """构造参数或异常路径的完整阻断报告。

    参数：
        trigger: 触发扫描的模式名称。
        scope: 已构造的允许范围描述。
        reason: 阻断原因文本。
        mode: 当前扫描模式。
    返回：包含空快照和阻断 verdict 的完整报告。
    """

    # 复用统一报告构造器，避免异常路径产生字段漂移。
    return build_report(
        trigger=trigger,
        scope=scope,
        snapshot={"algorithm": "sha256", "digest": "", "expected_digest": "", "drifted": False, "files": []},
        tool_run={"tool": "pycode_gardener.py", "mode": mode, "function_candidates": [], "exit_code": 2},
        document_findings=[],
        code_findings=[],
        rejected_candidates=[],
        uncertainties=[{"kind": "blocked", "reason": reason}],
        verdict=BLOCKING_VERDICT,
    )

# 构造不执行副作用的 gardener CLI 解析器。
def _build_parser() -> argparse.ArgumentParser:
    """构造不执行副作用的 gardener CLI 解析器。

    返回：只负责解析参数、不执行文件或 Git 操作的 ArgumentParser。
    """

    # 参数不使用 argparse required，以便缺参也能输出严格 JSON。
    parser = argparse.ArgumentParser(add_help=False)  # 无副作用的参数解析器

    # 显式注册帮助开关，缺参时仍由 main 输出 JSON。
    parser.add_argument("--help", action="store_true")

    # 注册项目根参数。
    parser.add_argument("--project")

    # 注册触发模式参数。
    parser.add_argument("--trigger")

    # 注册提交引用参数。
    parser.add_argument("--commit")

    # 注册增量基线参数。
    parser.add_argument("--base")

    # 注册快照绑定参数。
    parser.add_argument("--expected-snapshot-sha256")

    # 注册源码根目录参数。
    parser.add_argument("--source-root")

    # 注册测试根目录参数。
    parser.add_argument("--tests-root")

    # 注册全量或增量模式参数。
    parser.add_argument("--mode", default="full")

    # 注册显式 JSON 协议确认开关。
    parser.add_argument("--json", action="store_true")

    # 返回已经完成选项注册的解析器。
    return parser

# 执行 gardener CLI 并把所有路径转换为统一 JSON 报告。
def main(argv: list[str] | None = None) -> int:
    """执行 gardener CLI 并返回约定退出码。

    参数：
        argv: 可选的命令行参数列表；为空时由 argparse 读取进程参数。
    返回：按 JSON 协议约定的退出码。
    """

    # 解析失败也必须转换为单一 JSON，而不是输出 argparse 文本。
    try:

        # 解析参数时保留 Namespace 类型，便于后续静态检查和字段访问。
        namespace_options: argparse.Namespace = _build_parser().parse_args(argv)  # CLI 参数命名空间

    # argparse 的 SystemExit 转换成统一 JSON 阻断报告。
    except SystemExit:

        # 缺参或格式错误必须保持机器可读输出。
        dict_report = _empty_report(  # 参数错误报告
            "unknown",  # 参数解析失败时的占位触发模式
            {"allowed_extensions": [".md", ".py"]},  # 最小范围描述
            "invalid command arguments",  # 统一参数错误原因
            "full",  # 解析失败不进入增量模式
        )

        # stdout 只写完整 JSON 对象，不混入 argparse 文本。
        sys.stdout.write(json.dumps(dict_report, ensure_ascii=False, sort_keys=True) + "\n")

        # 参数解析失败使用协议规定的 2。
        return 2

    # 帮助请求仍输出报告对象，避免 CLI 输出形态分叉。
    if namespace_options.help:

        # 帮助状态报告不启动任何项目扫描。
        dict_report = _empty_report(  # 帮助请求报告
            "help",  # 帮助请求触发标识
            {"allowed_extensions": [".md", ".py"]},  # 帮助路径最小范围
            "help requested; use the documented JSON protocol",  # 帮助诊断文本
            "full",  # 帮助路径不执行增量扫描
        )

        # 保持帮助路径与其他路径相同的 JSON 输出协议。
        sys.stdout.write(json.dumps(dict_report, ensure_ascii=False, sort_keys=True) + "\n")

        # 帮助请求是成功处理的 CLI 请求。
        return 0

    # 缺省项目文本只用于构造诊断，真正的必需项仍由下面检查。
    str_project = namespace_options.project or "."  # CLI 项目根文本

    # 规范化项目根，供范围描述和分析复用。
    path_project = _absolute_root(str_project)  # CLI 项目根路径

    # 构造不读取文件的范围描述。
    dict_scope = _scope_payload(  # 当前 CLI 扫描范围
        path_project,  # 已规范化项目根
        namespace_options.source_root or "",  # CLI 源码边界
        namespace_options.tests_root or "",  # CLI 测试边界
        namespace_options.mode,  # CLI 扫描模式
    )

    # 收集所有缺失的必需 CLI 参数，避免只报告第一项。
    list_required: list[str] = []  # 缺失参数诊断列表

    # 项目根必须由调用方显式提供。
    if not namespace_options.project:

        # 记录缺少项目根的 CLI 错误。
        list_required.append("--project is required")

    # 触发模式决定 Git 或工作树证据来源。
    if not namespace_options.trigger:

        # 记录缺少触发模式的 CLI 错误。
        list_required.append("--trigger is required")

    # 源码根是允许扫描范围的必需边界。
    if not namespace_options.source_root:

        # 记录缺少源码根的 CLI 错误。
        list_required.append("--source-root is required")

    # 测试根同样需要由调用方显式声明。
    if not namespace_options.tests_root:

        # 记录缺少测试根的 CLI 错误。
        list_required.append("--tests-root is required")

    # 缺少必需参数时不启动 Git 或文件分析。
    if list_required:

        # 将所有缺失项合并到一条稳定诊断中。
        dict_report = _empty_report(  # 必需参数错误报告
            namespace_options.trigger or "unknown",  # 已提供的触发模式
            dict_scope,  # 当前 CLI 范围描述
            "; ".join(list_required),  # 缺失参数汇总文本
            namespace_options.mode,  # 当前 CLI 扫描模式
        )

        # 仍只输出完整 JSON 对象。
        sys.stdout.write(json.dumps(dict_report, ensure_ascii=False, sort_keys=True) + "\n")

        # 必需参数缺失使用阻断退出码 2。
        return 2

    # 正式分析路径将所有异常转换为 JSON 阻断报告。
    try:

        # 绑定 CLI 参数并执行只读项目分析。
        dict_analysis = analyze_project(  # 分析结果报告
            path_project,  # 报告构造使用的规范化根
            namespace_options.source_root,  # 源码根目录
            namespace_options.tests_root,  # 测试根目录

            # 触发和版本绑定字段决定读取哪一份 Git 证据。
            trigger=namespace_options.trigger,  # 触发模式
            commit=namespace_options.commit,  # 分析所绑定的 Git 对象引用
            base=namespace_options.base,  # 分析所使用的差异基线
            expected_snapshot_sha256=namespace_options.expected_snapshot_sha256,  # 报告绑定的快照摘要

            # 模式字段保留完整或增量扫描语义。
            mode=namespace_options.mode,  # 报告记录的扫描模式
        )

        # 只把明确的部分证据类型映射到退出码 3。
        set_partial_kinds = {"partial_parse", "partial_evidence"}  # 部分证据种类

        # 检查分析不确定性中是否存在部分证据。
        bool_partial = any(  # 是否存在部分证据
            str(item.get("kind", "")) in set_partial_kinds  # 当前不确定性是否属于部分证据
            for item in dict_analysis["uncertainties"]  # 逐条检查分析不确定性
        )

        # 部分证据优先使用退出码 3，否则使用成功码 0。
        int_exit = 3 if bool_partial else 0  # 分析退出码

        # 没有部分证据但 verdict 阻断时使用退出码 2。
        if dict_analysis["verdict"] in BLOCKING_VERDICTS and not bool_partial:

            # 保持参数或证据阻断的 fail-closed 退出协议。
            int_exit = 2  # 阻断报告对应的进程退出码

        # 将分析字典绑定到统一报告 schema。
        dict_report = build_report(  # 完整分析报告
            trigger=namespace_options.trigger,  # 报告绑定的触发标签
            scope=dict_scope,  # 允许范围
            snapshot=dict_analysis["snapshot"],  # 快照证据
            tool_run={**dict_analysis["tool_run"], "exit_code": int_exit},  # 工具执行证据
            document_findings=dict_analysis["document_findings"],  # 文档发现
            code_findings=dict_analysis["code_findings"],  # 代码发现
            rejected_candidates=dict_analysis["rejected_candidates"],  # 被拒候选
            uncertainties=dict_analysis["uncertainties"],  # 分析产生的不确定性证据
            verdict=dict_analysis["verdict"],  # 分析结论
        )

    # 文件、参数或只读 Git 错误统一落入阻断报告。
    except (OSError, ValueError, subprocess.SubprocessError) as exc:

        # 保留异常文本供主 Agent 诊断失败原因。
        dict_report = _empty_report(namespace_options.trigger, dict_scope, str(exc), namespace_options.mode)  # 异常阻断报告

        # 异常路径使用阻断退出码。
        int_exit = 2  # 异常退出码

    # stdout 严格只写完整 JSON；--json 只是显式确认协议而非切换格式。
    sys.stdout.write(json.dumps(dict_report, ensure_ascii=False, sort_keys=True) + "\n")

    # 返回与报告证据一致的进程退出码。
    return int_exit

# 直接执行脚本时交给 main 处理协议化退出码。
if __name__ == "__main__":

    # 入口把 main 的协议退出码交给 Python 进程。
    raise SystemExit(main())
