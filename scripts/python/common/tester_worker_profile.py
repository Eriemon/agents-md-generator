"""管理唯一隔离测试智能体的 Codex TOML 配置。"""

# 延迟注解求值保持治理脚本在 Python 3.10 下可直接执行。
from __future__ import annotations

# 标准库负责原子替换、环境解析、时间戳、路径和 TOML 读取。
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil
import sys
import tomllib

# Codex 角色配置只保留当前 CLI 实际接受的字段。
DEFAULT_TESTER_WORKER_TOML = (  # 默认唯一测试智能体配置
    '''# Canonical isolated test-worker profile managed by agents-md-generator.
name = "tester_worker"
description = "唯一的记忆隔离测试智能体；负责 tests/** 的测试树访问、测试编写与验证。"
model = "gpt-5.6-luna"
model_reasoning_effort = "max"
developer_instructions = """
你是唯一的 TESTER。fork_turns=none，使用隔离记忆上下文；不得把 tests/** 委托给其他智能体。
只有你可以列出、读取、创建、修改或运行目标工作文件夹中的 tests/**；实现智能体只能修改 tests/** 之外的产品文件。
先写并运行 RED 测试，再将失败症状、计数、建议反馈给实现智能体；产品修复后由同一 tester_worker 复跑 GREEN 与最终回归。
The same tester_worker performs RED, GREEN, and final regression, then reports the tests tree hash.
Routine test-hash confirmation is prohibited.
Agent autonomously confirms when the canonical tester result agrees with the \
authoritative current tests tree or receipt.
A report-only hash mismatch is corrected to the authoritative value.
Conflicting or insufficient provenance stops for user review without an autonomous rerun.
New test files use functional or behavioral semantic names; filename stems must not \
contain digits, including v1, v2, 1, 2, part1, and part2.
完成前报告 tests/** 最终树哈希；不等待常规用户确认。
遵循目标工作文件夹最近的 AGENTS.md。
修改 tests/** 下的 Python、bat/cmd、shell/bash、PowerShell 或 Tcl 前，先思考并同时加载 readable-python-generator 与
readable-script-generator；两个门禁必须在编辑过程中通过；Python 最终由 readable-python-generator 负责，
脚本最终由 readable-script-generator 负责。
配置握手请求必须返回：TESTER_WORKER_READY。
"""
'''
)  # TOML 文本结束

# 生成的 AGENTS 文本使用同一份稳定授权句，避免重复确认语义漂移。
SINGLE_TASK_AUTHORIZATION_RECEIPT = (  # 单次任务授权收据文本
    "A single-task authorization receipt is confirmed once across the skill, "
    "AGENTS.md, and CLI; it becomes invalid only when the target, scope, or risk changes."
)

# 受管配置必须包含这些不变量，缺一项就不能作为唯一测试智能体。
REQUIRED_INSTRUCTION_FRAGMENTS = (  # tester_worker 指令必需片段
    "fork_turns=none",  # 隔离上下文标记
    "tests/**",  # 测试树所有权标记
    "RED",  # 红灯阶段标记
    "same tester_worker",  # 同一 worker 标记
    "GREEN",  # 绿灯阶段标记
    "final regression",  # 最终回归标记
    "tests/** 最终树哈希",  # 测试树哈希标记
    "Routine test-hash confirmation is prohibited.",  # 哈希无需常规确认
    (
        "Agent autonomously confirms when the canonical tester result agrees with the "
        "authoritative current tests tree or receipt."
    ),  # 权威一致时自主确认
    "A report-only hash mismatch is corrected to the authoritative value.",  # 报告值错误时纠正
    "Conflicting or insufficient provenance stops for user review without an autonomous rerun.",  # 证据冲突时停线
    (
        "New test files use functional or behavioral semantic names; filename stems "
        "must not contain digits, including v1, v2, 1, 2, part1, and part2."
    ),  # 新测试命名合同
    "readable-python-generator",  # Python 门禁标记
    "readable-script-generator",  # 脚本门禁标记
    "TESTER_WORKER_READY",  # 动态握手标记
)

# 唯一 tester_worker 路径解析函数公开稳定参数和返回约定。
def tester_worker_path(codex_home: str | Path | None = None) -> Path:
    """解析唯一 tester_worker.toml 的规范路径。

    参数：codex_home 为可选 Codex 主目录覆盖值。
    返回：`agents/tester_worker.toml` 的规范路径。
    """

    # 测试和隔离运行优先采用显式传入的 Codex 主目录。
    str_codex_home = (  # Codex 主目录覆盖文本
        str(codex_home) if codex_home is not None else os.environ.get("CODEX_HOME", "")  # 主目录来源
    )  # 规范化 Codex 主目录覆盖值

    # 空覆盖值不能把目标误解析到当前目录。
    path_codex_home = (  # 规范化后的 Codex 主目录
        Path(str_codex_home).expanduser() if str_codex_home.strip() else Path.home() / ".codex"  # 主目录路径
    )  # 规范化 Codex 主目录路径

    # 配置文件固定位于 Codex agents 角色目录。
    return path_codex_home / "agents" / "tester_worker.toml"

# 配置字段检查器只返回缺失或不匹配的合同错误。
def _validation_errors(dict_config: object) -> list[str]:
    """返回配置合同中缺失或不匹配的字段。

    参数：dict_config 为 tomllib 解析后的 TOML 根对象。
    返回：按稳定顺序排列的合同错误文本。
    """

    # 非映射 TOML 根不能被当作 Codex 角色配置。
    if not isinstance(dict_config, dict):

        # 以单项错误保持调用方的结构化诊断稳定。
        return ["TOML root must be a table"]

    # 基础字段和值必须与唯一 worker 的公开身份一致。
    list_errors: list[str] = []  # 配置合同错误集合

    # name 字段锁定唯一角色名称。
    if dict_config.get("name") != "tester_worker":

        # 错误文本说明角色身份不匹配。
        list_errors.append("name must be tester_worker")

    # model 字段锁定用户确认的默认模型。
    if dict_config.get("model") != "gpt-5.6-luna":

        # 错误文本说明模型选择不匹配。
        list_errors.append("model must be gpt-5.6-luna")

    # reasoning 字段锁定用户确认的最大推理强度。
    if dict_config.get("model_reasoning_effort") != "max":

        # 错误文本说明推理强度不匹配。
        list_errors.append("model_reasoning_effort must be max")

    # 指令字段承载所有不可由 TOML 顶层表达的隔离约束。
    str_instructions = str(dict_config.get("developer_instructions", ""))  # 规范化后的角色指令文本

    # 缺失指令时先报告空字段，不重复追加片段错误。
    if not str_instructions.strip():

        # 空指令不能安全承载 tests/** 隔离合同。
        list_errors.append("developer_instructions must not be empty")

    # 逐项检查隔离、双技能和握手不变量。
    for str_fragment in REQUIRED_INSTRUCTION_FRAGMENTS:

        # 缺失任一片段都阻止其成为唯一 worker。
        if str_fragment not in str_instructions:

            # 错误文本保留缺失片段，便于修复漂移配置。
            list_errors.append(
                f"developer_instructions missing: {str_fragment}"
            )

    # 调用方需要稳定的错误序列以便报告和验证。
    return list_errors

# TOML 文本解析器同时执行语法和角色合同验证。
def validate_tester_worker_text(str_text: str) -> dict[str, object]:
    """解析并验证 tester_worker TOML 文本。

    参数：str_text 为待解析的 UTF-8 TOML 文本。
    返回：包含 valid、errors 和 config 字段的结构化验证结果。
    """

    # 语法错误和合同错误都转换为机器可读结果，不吞掉具体原因。
    try:

        # TOML 标准库解析结果供后续字段合同复用。
        dict_config = tomllib.loads(str_text)  # TOML 根配置映射

    # TOML 解码异常进入结构化错误分支。
    except tomllib.TOMLDecodeError as exc:

        # 语法错误直接返回失败结果，不继续访问不完整配置。
        return {
            "valid": False,
            "errors": [f"invalid TOML: {exc}"],
            "config": {},
        }

    # 只有语法和所有业务不变量都满足才返回 valid。
    list_errors = _validation_errors(dict_config)  # 角色合同错误

    # 解析成功结果进入合同字段检查。
    return {
        "valid": not list_errors,
        "errors": list_errors,
        "config": dict_config,
    }

# 旧配置备份函数保留同目录和可恢复的原文副本。
def _backup_existing(path_config: Path) -> Path:
    """把已有配置复制到同目录唯一备份文件。

    参数：path_config 为已确认存在的 TOML 文件。
    返回：新建的备份文件路径。
    """

    # UTC 微秒和进程号共同避免同一秒内的备份名冲突。
    str_stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")  # 备份时间戳

    # 备份名保留原文件名并使用可检索的 bak 前缀。
    path_backup = path_config.with_name(  # 备份文件路径
        f"{path_config.name}.bak-{str_stamp}-{os.getpid()}"  # 备份文件名
    )  # 组合时间戳和进程号后的备份路径

    # 复制而非移动，确保刷新失败时旧配置仍可恢复。
    shutil.copy2(path_config, path_backup)

    # 返回备份路径供报告和恢复流程复用。
    return path_backup

# 原子写入函数避免半写入的角色配置被读取。
def _write_atomic(path_config: Path, str_text: str) -> None:
    """以同目录临时文件和替换完成 UTF-8 原子写入。

    参数：path_config 为最终 TOML 文件；str_text 为完整配置文本。
    返回：无；失败时保留原文件并传播异常。
    """

    # 同目录临时文件确保 os.replace 不跨文件系统。
    path_temp = path_config.with_name(  # 临时配置文件路径
        f"{path_config.name}.tmp-{os.getpid()}"  # 临时文件名
    )  # 与目标同目录的临时路径

    # 写入、替换和异常清理由一个可恢复事务边界包围。
    try:

        # UTF-8 和 LF 固定配置文件的跨平台字节表示。
        path_temp.write_text(str_text, encoding="utf-8", newline="\n")

        # 原子替换使读者只能看到旧文件或完整新文件。
        os.replace(path_temp, path_config)

    # finally 分支只负责清理本次事务残留。
    finally:

        # 替换异常时清理临时文件，不触碰既有配置或备份。
        if path_temp.exists():

            # 临时文件没有恢复价值，安全地移除本次残留。
            path_temp.unlink()

# 唯一配置入口负责检查、显示、备份、写入和最终读回验证。
def ensure_tester_worker_profile(
    codex_home: str | Path | None = None,
    *,
    write: bool = False,
    confirm_update: bool = False,
) -> dict[str, object]:
    """检查或创建唯一 tester_worker 配置并验证最终读回内容。

    参数：codex_home 为可选 Codex 主目录；write 控制是否落盘；confirm_update 保留调用方确认字段。
    返回：包含原文、备份、最终文本和 TOML 验证结果的结构化报告。
    """

    # 路径解析集中在一个入口，便于真实主目录和隔离测试复用。
    path_config = tester_worker_path(codex_home)  # 唯一配置目标路径

    # 初始存在性和文件类型决定后续读取分支。
    bool_exists = path_config.exists()  # 目标是否存在

    # 目录或其他非文件目标不应被误当作 TOML 文本。
    str_existing = (  # 旧配置完整原文
        path_config.read_text(encoding="utf-8") if bool_exists and path_config.is_file() else ""  # 文件原文
    )  # 旧配置读取结果

    # 先读取和验证已有内容，报告中保留完整原文供确认或审计。
    dict_existing = (  # 旧配置验证结果
        validate_tester_worker_text(str_existing)  # 旧配置验证
        if str_existing  # 仅有原文时执行解析
        else {"valid": False, "errors": ["configuration is missing"], "config": {}}  # 缺失结果
    )  # 旧配置合同结果

    # 缺失、语义漂移或格式差异都需要刷新默认合同。
    bool_needs_refresh = bool_exists and (  # 是否需要备份并刷新
        not dict_existing["valid"] or str_existing != DEFAULT_TESTER_WORKER_TOML  # 漂移判断
    )  # 漂移配置判定

    # 结果保留授权收据和旧内容，调用方可以先展示再决定后续动作。
    dict_result: dict[str, object] = {  # 配置生命周期报告
        "path": str(path_config),  # 唯一配置路径
        "exists_before": bool_exists,  # 写入前存在性
        "existing_content": str_existing,  # 写入前完整原文
        "existing_validation": dict_existing,  # 写入前验证结果
        "updated": False,  # 初始更新状态
        "backup_path": "",  # 初始备份路径
        "requires_user_confirmation": False,  # 当前任务收据已覆盖
        "authorization_receipt": SINGLE_TASK_AUTHORIZATION_RECEIPT,  # 单次授权收据
        "confirm_update": confirm_update,  # 调用方确认字段
    }

    # 只读检查不创建目录或改动已有文件。
    if not write:

        # 只读状态区分稳定配置和待刷新配置。
        dict_result["status"] = "valid" if not bool_needs_refresh else "needs-refresh"  # 只读状态

        # 返回只读状态而不触碰配置文件。
        return dict_result

    # 目录创建属于首次配置的正常工作流，且不触碰项目文件。
    path_config.parent.mkdir(parents=True, exist_ok=True)

    # 已有内容先展示给调用方，确认是否需要刷新后才进入写入分支。
    if bool_exists and not bool_needs_refresh:

        # 稳定配置也必须留下完整原文的审计输出。
        sys.stderr.write(
            "> ERR: [Python] existing tester_worker.toml before update decision:\n"
            f"{str_existing}\n"
        )

    # 已有漂移配置先显示并备份，再在当前任务授权范围内刷新默认合同。
    if bool_needs_refresh:

        # 覆盖前先把完整旧内容送到错误流，避免与 AGENTS 正文混流。
        sys.stderr.write(  # 旧配置审计输出
            "> ERR: [Python] existing tester_worker.toml before refresh:\n"
            f"{str_existing}\n"
        )

        # 复制而非删除旧内容，保证失败时仍有恢复路径。
        path_backup = _backup_existing(path_config)  # 旧配置备份路径

        # 报告备份位置，供用户核对恢复边界。
        dict_result["backup_path"] = str(path_backup)  # 写入备份证据

    # 缺失配置或已备份漂移配置都写入唯一默认内容。
    if not bool_exists or bool_needs_refresh:

        # 原子写入避免读者观察到半份 TOML。
        _write_atomic(path_config, DEFAULT_TESTER_WORKER_TOML)

        # 标记配置已经写入默认合同。
        dict_result["updated"] = True  # 标记配置已刷新

    # 任何写入路径都重新读取并验证，验证失败即报告错误而非假装成功。
    str_final = path_config.read_text(encoding="utf-8")  # 最终配置原文

    # 重新验证最终读回文本，确保写入没有被截断。
    dict_final = validate_tester_worker_text(str_final)  # 最终配置验证结果

    # 保存最终完整配置供调用方展示。
    dict_result["final_content"] = str_final  # 保存最终完整配置

    # 保存最终 TOML 证据供验证和审计复用。
    dict_result["final_validation"] = dict_final  # 保存最终 TOML 证据

    # 派生最终状态，失败状态不能被误报为成功。
    dict_result["status"] = "valid" if dict_final["valid"] else "invalid"  # 最终状态

    # 验证失败时附加错误列表并阻止调用方宣称成功。
    if not dict_final["valid"]:

        # 错误字段与验证器保持同一结构。
        dict_result["errors"] = dict_final["errors"]  # 保存最终错误列表

    # 返回包含更新、备份和最终验证证据的完整报告。
    return dict_result

# 动态角色验证使用稳定短握手令牌。
def tester_worker_handshake() -> str:
    """返回用于动态角色验证的稳定握手令牌。

    参数：无。
    返回：`TESTER_WORKER_READY` 握手文本。
    """

    # 令牌保持短且唯一，便于 CLI wrapper 在 ANSI 日志中精确筛选。
    return "TESTER_WORKER_READY"
