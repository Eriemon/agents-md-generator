#!/usr/bin/env python3
"""汇总活动 Codex sessions 树在指定时间窗内的 token 用量。"""

# 延迟求值类型标注，支持运行于不同 Python 版本的治理环境。
from __future__ import annotations

# 分类脚本可从任意任务目录直接执行，这里补齐兄弟任务模块路径。
import sys
from pathlib import Path

# 裸模块兼容路径由函数集中登记，避免模块顶层出现循环控制流。
def extend_task_module_search_path() -> None:
    """把 Python 任务子目录加入当前解释器的模块搜索路径。

    Args:
        None: 搜索根由当前文件位置确定。

    Returns:
        None: 函数仅更新当前解释器搜索路径。
    """

    # Python 脚本根包含 detect 入口依赖的公共任务模块。
    path_scripts_python_root = Path(__file__).resolve().parents[1]  # 各任务分类脚本共同父目录

    # 逐个登记目录，保持历史裸模块导入兼容。
    for path_task_directory in path_scripts_python_root.iterdir():

        # 文件资产不能承载可导入的任务模块。
        if path_task_directory.is_dir():

            # sys.path 接收字符串路径，避免依赖隐式 Path 转换。
            str_task_directory = str(path_task_directory)  # 待登记的任务模块目录

            # 已存在的目录不重复插入，保持导入优先级稳定。
            if str_task_directory not in sys.path:

                # 兄弟任务模块必须在后续裸模块导入前可见。
                sys.path.insert(0, str_task_directory)

# 公共依赖导入前完成一次兼容路径登记。
extend_task_module_search_path()

# 导入 脚本治理 所需的依赖模块。
import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

# 导入 脚本治理 所需的依赖模块。
from agents_common import codex_sessions_root, emit_json

# add_usage 只转换这五个官方计数字段，其他 payload 元数据不得写入计数器属性。
TOKEN_KEYS = (
    "input_tokens",  # 请求消耗的输入 token 计数
    "cached_input_tokens",  # 命中缓存的输入 token 计数
    "output_tokens",  # 响应生成的输出 token 计数
    "reasoning_output_tokens",  # 响应内部推理的输出 token 计数
    "total_tokens",  # 本次请求累计的全部 token 计数
)  # TokenCounter.add_usage 允许从事件写入的五个 dataclass 字段名

# 会话或全局累计量保持与 token_count 事件字段同形。
@dataclass
class TokenCounter:
    """累计一组有效 token_count 事件中的用量字段。"""

    # 输入 token 单独累计，供默认总计输出展示。
    input_tokens: int = 0  # 输入 token 累计值

    # 缓存输入与普通输入分列，避免掩盖缓存使用规模。
    cached_input_tokens: int = 0  # 缓存输入 token 累计值

    # 模型输出 token 保持原始事件字段口径。
    output_tokens: int = 0  # 输出 token 累计值

    # 推理输出独立呈现，便于比较可见输出和推理开销。
    reasoning_output_tokens: int = 0  # 推理输出 token 累计值

    # 总 token 使用事件直接报告值，不由其他字段重复推导。
    total_tokens: int = 0  # 总 token 累计值

    # 有效事件数用于区分零用量事件和没有可用事件。
    usage_records: int = 0  # 成功累计的事件数量

    # 累加采用先验证后提交，保证失败记录不会产生部分更新。
    def add_usage(self, usage: Mapping[str, Any]) -> bool:
        """校验并累计一条 last_token_usage 记录。

        Args:
            usage: token_count 事件中的用量字段映射。

        Returns:
            全部数值字段均可转换并完成累计时为 True。
        """

        # 先完成全部字段转换，避免无效记录只累计部分数值。
        dict_values: dict[str, int] = {}  # 当前记录的归一化 token 值

        # 固定字段之外的事件元数据不参与 token 汇总。
        for key in TOKEN_KEYS:

            # 缺失字段按零处理，兼容不同版本的 token_count 载荷。
            raw_value = usage.get(key)  # 当前 token 字段的原始值

            # None 与缺失字段具有相同的零值语义。
            if raw_value is None:

                # 延迟累计保证后续字段失败时计数器保持原状态。
                dict_values[key] = 0  # 当前缺失字段的归一化值

                # 当前字段已完成归一化，继续检查下一个字段。
                continue

            # JSON 数值或数字文本统一转换为整数。
            try:

                # 转换结果暂存到当前记录，不立即修改累计器。
                dict_values[key] = int(raw_value)  # 当前字段的整数 token 值

            # 非数字字段使整条用量记录无效。
            except (TypeError, ValueError):

                # 返回 False 时调用方不会更新事件时间戳。
                return False

        # 全部字段通过转换后再一次性更新累计器。
        for key, raw_value in dict_values.items():

            # dataclass 字段名来自固定 TOKEN_KEYS，不接受外部属性名。
            setattr(self, key, getattr(self, key) + raw_value)

        # 记录数只统计成功完成全部字段转换的事件。
        self.usage_records += 1  # 当前记录已完整计入累计值

        # 成功标志供会话汇总决定是否接受该事件时间。
        return True

# CLI 只暴露会话根、时间窗、输出格式和明细开关。
def parse_args() -> argparse.Namespace:
    """解析 Codex token 用量复核命令参数。

    Args:
        None: 参数从当前进程命令行读取。

    Returns:
        已解析的命令行命名空间。
    """

    # 描述文本用于帮助页说明脚本仅汇总本地 session JSONL。
    parser = argparse.ArgumentParser(  # token 用量复核参数解析器
        description="Summarize Codex token usage from local session jsonl files."  # 帮助页摘要
    )

    # sessions-root 仅供测试或诊断显式覆盖自动发现位置。
    parser.add_argument("--sessions-root", help="Path to the Codex sessions directory for testing or diagnostics")

    # 默认复核最近 48 小时，与技能文档中的示例窗口一致。
    parser.add_argument("--hours", type=float, default=48.0, help="Lookback window in hours")

    # now 覆盖使时间边界测试具备确定性。
    parser.add_argument("--now", help="Override current time with an ISO-8601 timestamp")

    # JSON 输出供自动化消费，不与人工文本混排。
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")

    # 默认文本只显示总计，verbose 才展开每个 session 文件。
    parser.add_argument("--verbose", action="store_true", help="Show per-file rows in text output")

    # argparse 负责无效参数诊断和退出码。
    return parser.parse_args()

# 时间解析统一输出 UTC aware datetime，便于窗口边界比较。
def parse_timestamp(raw_value: str) -> datetime:
    """解析 ISO 8601 时间并归一化为 UTC。

    Args:
        raw_value: session 记录中的时间戳文本。

    Returns:
        带 UTC 时区的 datetime。

    Raises:
        ValueError: 输入不是有效 ISO 8601 时间。
    """

    # 边界空白不属于时间语义，解析前统一去除。
    str_normalized = raw_value.strip()  # 待解析的 ISO 8601 文本

    # Python fromisoformat 使用显式偏移表达 UTC。
    if str_normalized.endswith("Z"):

        # 将常见 Z 后缀转换为等价的零时区偏移。
        str_normalized = str_normalized[:-1] + "+00:00"  # fromisoformat 兼容形式

    # 解析错误保留为 ValueError 供记录遍历跳过单条坏数据。
    datetime_parsed: datetime = datetime.fromisoformat(str_normalized)  # 已解析时间

    # 无时区输入按 UTC 解释，避免依赖运行机器本地时区。
    if datetime_parsed.tzinfo is None:

        # 补充 UTC 时区但不改变原始时钟字段。
        return datetime_parsed.replace(tzinfo=timezone.utc)

    # 有偏移输入转换到 UTC 后参与统一边界比较。
    return datetime_parsed.astimezone(timezone.utc)

# JSONL 读取采用逐行容错，单条损坏记录不影响其他会话事件。
def iter_records(path: Path) -> list[dict[str, Any]]:
    """读取 session JSONL 中可解析的对象记录。

    Args:
        path: session JSONL 文件路径。

    Returns:
        保持文件顺序的 JSON 对象记录。
    """

    # 返回列表只包含字典，调用方无需再次处理数组或标量。
    list_records: list[dict[str, Any]] = []  # 有效 session 记录

    # 不可读文件视为无可用记录，而不是终止整个目录汇总。
    try:

        # 一次读取当前 session 日志，随后按物理行隔离坏 JSON 与有效事件。
        str_session_jsonl_text = path.read_text(encoding="utf-8")  # splitlines 逐条解析的 session 事件流

    # 权限、并发删除等文件错误仅影响当前文件。
    except OSError:

        # 返回已初始化的空列表，保持调用合同稳定。
        return list_records

    # splitlines 同时兼容不同平台换行符。
    for line in str_session_jsonl_text.splitlines():

        # 空白不属于 JSON 载荷，解析前去除边界空格。
        str_payload = line.strip()  # 当前 JSONL 记录文本

        # 空行不产生 session 记录。
        if not str_payload:

            # 继续处理后续有效行。
            continue

        # 每行独立解析，损坏行不会污染其他记录。
        try:

            # JSON 类型在解析后再限制为对象。
            value_record = json.loads(str_payload)  # 当前行解析结果

        # 不完整或非法 JSON 行按 session 日志容错策略跳过。
        except json.JSONDecodeError:

            # 继续检查同一文件的后续行。
            continue

        # token 事件必须是对象；数组和标量不进入调用方记录流。
        if isinstance(value_record, dict):

            # 保留文件出现顺序，供会话事件遍历使用。
            list_records.append(value_record)

    # 返回当前文件中全部有效对象记录。
    return list_records

# 事件提取器只接受 Codex token_count 中的 last_token_usage 映射。
def extract_last_token_usage(record: Mapping[str, Any]) -> Mapping[str, Any] | None:
    """从 session 事件中提取最后一次 token 用量。

    Args:
        record: 单条 session JSONL 对象。

    Returns:
        last_token_usage 字段映射；记录不匹配时为 None。
    """

    # 其他 session 记录类型不包含可汇总 token_count 事件。
    if record.get("type") != "event_msg":

        # 不匹配记录由调用方直接跳过。
        return None

    # event_msg 的具体事件类型位于 payload 对象。
    value_payload = record.get("payload")  # 当前事件载荷

    # 只接受对象形式的 token_count 事件。
    if not isinstance(value_payload, Mapping) or value_payload.get("type") != "token_count":

        # 缺失或其他事件载荷不计入用量。
        return None

    # token_count 的计数详情位于 info 对象。
    value_info = value_payload.get("info")  # token_count 详情载荷

    # 非对象 info 无法安全读取 last_token_usage。
    if not isinstance(value_info, Mapping):

        # 畸形事件按无可用用量处理。
        return None

    # last_token_usage 表示该 token_count 事件新增的用量片段。
    value_usage = value_info.get("last_token_usage")  # 待验证用量载荷

    # 计数器只接受字段映射，不处理标量或数组。
    if isinstance(value_usage, Mapping):

        # 返回原映射，由 TokenCounter 负责数值转换。
        return value_usage

    # 缺失有效 last_token_usage 时不产生累计量。
    return None

# 会话汇总遍历时间窗内每个 JSONL，并累加文件级与全局计数。
def summarize_sessions(root: Path, since: datetime, now: datetime) -> dict[str, Any]:
    """汇总指定目录和时间窗口内的 Codex token 用量。

    Args:
        root: Codex sessions 根目录。
        since: 统计窗口起点，包含边界。
        now: 统计窗口终点，包含边界。

    Returns:
        文件明细、全局总计和目录状态组成的汇总结果。
    """

    # 明细仅保留至少包含一条有效用量事件的文件。
    list_rows: list[dict[str, Any]] = []  # session 文件汇总行

    # 全局计数器与文件计数器使用相同字段结构。
    token_counter_grand_total: TokenCounter = TokenCounter()  # 当前时间窗的 token 总计

    # 匹配文件数按产生有效用量的 JSONL 计数。
    int_matched_files = 0  # 包含有效用量事件的文件数

    # 不存在的测试覆盖目录返回成功的空汇总，由渲染层说明原因。
    if not root.exists():

        # 空结果仍包含完整字段，便于 JSON 调用方稳定消费。
        return {
            "ok": True,
            "missing_root": True,
            "matched_file_count": 0,
            "summarized_file_count": 0,
            "rows": [],
            "grand_total": asdict(token_counter_grand_total),
        }

    # 路径排序保证相同目录内容产生确定性的初始遍历顺序。
    for path in sorted(root.rglob("*.jsonl")):

        # 每个文件独立累计，避免一条坏记录影响其他 session。
        token_counter_counter: TokenCounter = TokenCounter()  # 当前 JSONL 文件的 token 计数器

        # 最近有效事件时间用于最终明细排序。
        str_last_event_timestamp = ""  # 当前文件最近用量事件时间

        # JSONL 读取器已经过滤空行、坏 JSON 和非对象记录。
        for record in iter_records(path):

            # 时间窗口判断要求记录提供字符串时间戳。
            raw_timestamp = record.get("timestamp")  # 当前记录的原始时间戳

            # 非字符串时间戳无法按 ISO 8601 解析。
            if not isinstance(raw_timestamp, str):

                # 跳过当前记录并继续扫描文件。
                continue

            # 单条无效时间不应阻断其他 session 记录。
            try:

                # 所有事件时间归一化为 UTC 后再比较。
                datetime_event_time = parse_timestamp(raw_timestamp)  # 当前事件 UTC 时间

            # 非 ISO 8601 时间戳视为损坏记录。
            except ValueError:

                # 继续处理同一文件的后续记录。
                continue

            # 窗口同时排除起点之前和终点之后的记录。
            if datetime_event_time < since or datetime_event_time > now:

                # 窗口外记录不进入文件计数器。
                continue

            # 事件结构过滤与数值转换分离，便于解释无效原因边界。
            value_usage = extract_last_token_usage(record)  # 当前记录的用量映射

            # 非 token_count 或缺失用量的事件不参与统计。
            if value_usage is None:

                # 继续扫描下一条 session 记录。
                continue

            # 只有全部 token 字段可转换时才接受事件和时间戳。
            if token_counter_counter.add_usage(value_usage):

                # UTC ISO 文本可直接按字典序比较先后。
                str_event_iso = datetime_event_time.isoformat()  # 当前有效事件时间文本

                # 保留当前文件中时间最晚的有效用量事件。
                if not str_last_event_timestamp or str_event_iso > str_last_event_timestamp:

                    # 最近时间用于跨文件明细排序。
                    str_last_event_timestamp = str_event_iso  # 当前文件最新有效事件时间

        # 没有有效事件的 JSONL 不进入匹配文件数和明细。
        if token_counter_counter.usage_records == 0:

            # 继续处理下一个 session 文件。
            continue

        # 当前文件通过有效事件门槛后计入匹配数量。
        int_matched_files += 1  # 当前文件具有至少一条有效用量事件

        # 文件级各字段逐项合并到全局计数器。
        token_counter_grand_total.input_tokens += token_counter_counter.input_tokens  # 合并文件输入 token

        # 合并当前文件的缓存输入 token。
        token_counter_grand_total.cached_input_tokens += token_counter_counter.cached_input_tokens  # 合并缓存输入 token

        # 合并当前文件的输出 token。
        token_counter_grand_total.output_tokens += token_counter_counter.output_tokens  # 合并文件输出 token

        # 合并当前文件的推理输出 token。
        token_counter_grand_total.reasoning_output_tokens += token_counter_counter.reasoning_output_tokens  # 合并推理输出 token

        # 合并当前文件事件报告的总 token。
        token_counter_grand_total.total_tokens += token_counter_counter.total_tokens  # 合并文件总 token

        # 合并成功解析的用量事件数量。
        token_counter_grand_total.usage_records += token_counter_counter.usage_records  # 合并有效事件数

        # 文件路径、最近事件时间和计数器字段共同构成 verbose 明细行。
        list_rows.append(
            {
                "file": str(path),
                "last_event_timestamp": str_last_event_timestamp,
                **asdict(token_counter_counter),
            }
        )

    # 最近产生有效事件的 session 文件优先展示。
    list_rows.sort(key=lambda item: item["last_event_timestamp"], reverse=True)

    # 返回完整成功载荷，时间窗与根目录由上层补充。
    return {
        "ok": True,
        "missing_root": False,
        "matched_file_count": int_matched_files,
        "summarized_file_count": len(list_rows),
        "rows": list_rows,
        "grand_total": asdict(token_counter_grand_total),
    }

# 中文文本输出以“亿”为辅助量级，同时保留上层精确整数。
def format_yi(value: int) -> str:
    """将 token 整数格式化为两位小数的亿级文本。

    Args:
        value: 精确 token 数。

    Returns:
        带“亿”单位的两位小数文本。
    """

    # 一亿为换算基数，只用于人工展示，不替代精确值。
    return f"{value / 100000000:.2f}亿"

# Codex sessions 根不可用时构造机器可读的环境守卫失败载荷。
def build_guard_failure(codex_root: Path, requested_root: Path | None, hours: float) -> dict[str, Any]:
    """构造未发现 Codex sessions 根目录的失败结果。

    Args:
        codex_root: 当前环境解析出的 sessions 根目录。
        requested_root: 用户显式请求的诊断目录。
        hours: 请求的回溯小时数。

    Returns:
        描述环境守卫失败的结构化载荷。
    """

    # 结果展示用户实际请求位置；未覆盖时展示自动发现位置。
    path_sessions_root = requested_root or codex_root  # 当前请求对应的 sessions 路径

    # 失败载荷保留自动发现与显式请求两个位置以支持诊断。
    return {
        "ok": False,
        "reason": "codex_sessions_not_found",
        "hours": hours,
        "codex_sessions_root": str(codex_root),
        "requested_sessions_root": str(requested_root) if requested_root else "",
        "sessions_root": str(path_sessions_root),
        "message": (
            "Codex sessions directory was not found; token usage review only runs "
            "when the current environment resolves a Codex sessions directory."
        ),
    }

# 显式目录越过活动 Codex 树时构造路径边界失败载荷。
def build_requested_root_failure(
    codex_root: Path,
    requested_root: Path,
    hours: float,
) -> dict[str, Any]:
    """构造请求目录位于活动 Codex sessions 树外的结果。

    Args:
        codex_root: 当前活动 Codex sessions 根目录。
        requested_root: 用户显式请求的目录。
        hours: 请求的回溯小时数。

    Returns:
        描述路径边界失败的结构化载荷。
    """

    # 失败结果明确重复请求位置，避免调用方误用自动发现根。
    return {
        "ok": False,
        "reason": "sessions_root_outside_codex_root",
        "hours": hours,
        "codex_sessions_root": str(codex_root),
        "requested_sessions_root": str(requested_root),
        "sessions_root": str(requested_root),
        "message": "Requested sessions root must stay within the active Codex sessions directory.",
    }

# 成功汇总补充请求上下文，形成 JSON 与文本渲染共享的完整载荷。
def build_summary_payload(
    summary: dict[str, Any],  # 文件明细与总计
    *,

    # 自动发现根与实际扫描根共同描述路径安全上下文。
    codex_root: Path,  # 自动发现的安全根
    sessions_root: Path,  # 实际扫描目录

    # 覆盖路径为空时表示本次使用自动发现根。
    requested_root: Path | None,  # 用户覆盖目录

    # 时间元数据保留包含式窗口的两个边界。
    since: datetime,  # 时间窗起点
    now: datetime,  # 时间窗终点

    # 原始小时数用于标题和 JSON 结果复现请求。
    hours: float,  # 回溯小时数
) -> dict[str, Any]:
    """把 token 汇总与目录、时间窗口元数据合并。

    Args:
        summary: ``summarize_sessions`` 生成的统计结果。
        codex_root: 自动发现的活动 Codex sessions 根。
        sessions_root: 本次实际扫描的 sessions 目录。
        requested_root: 用户显式覆盖目录；未提供时为 None。
        since: 统计窗口起点。
        now: 统计窗口终点。
        hours: 请求的回溯小时数。

    Returns:
        可直接输出或渲染的完整成功载荷。
    """

    # summary 字段在元数据后展开，保持统计结果原始结构。
    return {
        "ok": True,
        "reason": "",
        "hours": hours,
        "codex_sessions_root": str(codex_root),
        "requested_sessions_root": str(requested_root) if requested_root else "",
        "sessions_root": str(sessions_root),
        "since": since.isoformat(),
        "now": now.isoformat(),
        **summary,
    }

# 环境守卫失败文本说明自动发现位置和覆盖参数边界。
def render_guard_failure_text(payload: Mapping[str, Any]) -> str:
    """渲染未发现 Codex sessions 根目录的人工文本。

    Args:
        payload: ``build_guard_failure`` 生成的失败载荷。

    Returns:
        多行中文诊断文本。
    """

    # 基础文本始终展示窗口、自动根、实际请求位置和执行条件。
    list_lines = [  # 守卫失败输出行
        f"=== 最近 {payload['hours']:g} 小时 Codex 本机 Token 使用统计 ===",  # 输出标题
        f"Codex Sessions 目录: {payload['codex_sessions_root']}",  # 自动发现根目录
        f"请求 Sessions 目录: {payload['sessions_root']}",  # 本次请求位置
        "",  # 路径信息与失败原因之间的空行
        f"未检测到 Codex sessions 目录：{payload['codex_sessions_root']}",  # 环境守卫失败原因
        "此功能仅在当前环境可解析到 `$CODEX_HOME/sessions` 或 `~/.codex/sessions` 且目录存在时可执行。",  # 环境执行条件
    ]

    # 显式覆盖存在时补充其不能绕过环境守卫的说明。
    if payload.get("requested_sessions_root"):

        # 附加说明保持在基础失败原因之后。
        list_lines.append("`--sessions-root` 仅用于测试或诊断，不能绕过 Codex 环境检测。")

    # 换行连接保持 CLI 文本可直接打印。
    return "\n".join(list_lines)

# 越界目录失败文本强调工具不能退化为通用文件扫描器。
def render_requested_root_failure_text(payload: Mapping[str, Any]) -> str:
    """渲染 sessions-root 越过活动 Codex 树的人工文本。

    Args:
        payload: ``build_requested_root_failure`` 生成的失败载荷。

    Returns:
        多行中文路径边界诊断。
    """

    # 固定顺序先展示路径事实，再解释边界原因和允许用途。
    return "\n".join(
        [
            f"=== 最近 {payload['hours']:g} 小时 Codex 本机 Token 使用统计 ===",
            f"Codex Sessions 目录: {payload['codex_sessions_root']}",
            f"请求 Sessions 目录: {payload['requested_sessions_root']}",
            "",
            "为避免把该工具退化成通用文件扫描器，`--sessions-root` 必须等于或位于当前 Codex sessions 根目录之下。",
            "`--sessions-root` 仅用于测试或诊断，不能跳出当前 Codex sessions 树。",
        ]
    )

# 成功文本默认只显示总计，verbose 模式再展开文件明细。
def render_text(summary: Mapping[str, Any], *, verbose: bool) -> str:
    """渲染 token 用量汇总的人工可读文本。

    Args:
        summary: 成功汇总载荷。
        verbose: 是否附加逐 JSONL 文件明细。

    Returns:
        多行中文统计文本。
    """

    # 标题区固定展示窗口、目录和匹配文件数。
    list_lines = [  # token 用量文本输出行
        f"=== 最近 {summary['hours']:g} 小时 Codex 本机 Token 使用统计 ===",  # 成功统计标题
        f"Sessions 目录: {summary['sessions_root']}",  # 成功汇总使用的扫描位置
        f"统计起点: {summary['since']}",  # 包含式窗口起点
        f"统计终点: {summary['now']}",  # 包含式窗口终点
        f"匹配 JSONL 文件数: {summary['matched_file_count']}",  # 有有效事件的文件数
        "",  # 汇总元数据与后续结果区之间的空行
    ]

    # 覆盖目录在汇总期间消失时给出明确空结果原因。
    if summary.get("missing_root"):

        # 缺失位置附加到标题区之后。
        list_lines.append(f"未找到指定的 sessions 目录：{summary['sessions_root']}")

        # 缺失目录没有总计或明细可渲染。
        return "\n".join(list_lines)

    # rows 已按最近事件时间排序。
    list_rows = summary["rows"]  # 有有效 token 事件的文件明细

    # 空时间窗提供 /status 替代建议而不是显示零值总计。
    if not list_rows:

        # 说明当前窗口内未发现符合事件合同的记录。
        list_lines.append("没有在指定时间窗口内找到可汇总的 token_count / last_token_usage 记录。")

        # /status 可用于查看当前活动会话自身的 token 信息。
        list_lines.append("建议：在 Codex 当前会话输入 /status 查看当前会话 token。")

        # 空窗口文本到此结束。
        return "\n".join(list_lines)

    # 总计字段与 TokenCounter dataclass 结构一致。
    dict_grand_total = summary["grand_total"]  # 当前时间窗的全局 token 总计

    # 精确整数是主值，TotalTokens 额外显示亿级近似值。
    list_lines.extend(
        [
            "--- 总计 ---",
            f"InputTokens: {dict_grand_total['input_tokens']}",
            f"CachedInputTokens: {dict_grand_total['cached_input_tokens']}",
            f"OutputTokens: {dict_grand_total['output_tokens']}",
            f"ReasoningOutputTokens: {dict_grand_total['reasoning_output_tokens']}",
            (
                f"TotalTokens: {dict_grand_total['total_tokens']} "
                f"(≈{format_yi(dict_grand_total['total_tokens'])})"
            ),
            f"UsageRecords: {dict_grand_total['usage_records']}",
        ]
    )

    # verbose 是唯一展开逐文件路径明细的入口。
    if verbose:

        # 明细区与总计区使用空行和标题分隔。
        list_lines.extend(["", "--- 按文件汇总 ---"])

        # 保持汇总阶段确定的最近事件时间排序。
        for row in list_rows:

            # 每个文件压缩为单行键值，便于终端快速比较。
            list_lines.append(
                " | ".join(
                    [
                        Path(row["file"]).name,
                        f"input={row['input_tokens']}",
                        f"cached={row['cached_input_tokens']}",
                        f"output={row['output_tokens']}",
                        f"reasoning={row['reasoning_output_tokens']}",
                        f"total={row['total_tokens']}",
                        f"records={row['usage_records']}",
                    ]
                )
            )

    # 默认模式在总计区结束，verbose 模式包含附加明细。
    return "\n".join(list_lines)

# 主入口执行环境守卫、路径边界、汇总和输出格式路由。
def main() -> None:
    """运行 Codex token 用量复核命令。

    Args:
        None: 输入由命令行参数和当前 Codex 环境提供。

    Returns:
        None: 结果直接写入标准输出。
    """

    # 参数命名空间决定时间窗、路径覆盖和输出格式。
    args = parse_args()  # token 用量复核命令参数

    # 显式 now 用于确定性诊断，否则使用当前 UTC 时间。
    datetime_now: datetime = (
        parse_timestamp(args.now)  # 显式测试或诊断时间
        if args.now  # 是否提供确定性终点覆盖
        else datetime.now(timezone.utc)  # 当前环境 UTC 时间
    )  # 统计窗口终点

    # 回溯小时数从窗口终点反向计算包含边界的起点。
    datetime_since: datetime = datetime_now - timedelta(hours=args.hours)  # 统计窗口起点

    # 自动发现根是允许扫描路径的安全边界。
    path_codex_root = codex_sessions_root().resolve()  # 活动 Codex sessions 根目录

    # 覆盖路径只用于测试或诊断，并在后续验证仍位于活动树内。
    path_requested_root = (
        Path(args.sessions_root).expanduser().resolve()  # 显式覆盖路径
        if args.sessions_root  # 仅显式覆盖时解析路径
        else None  # 未覆盖时使用自动发现根
    )  # 用户请求的 sessions 目录

    # 环境未提供真实 Codex sessions 根时拒绝退化为任意目录扫描。
    if not path_codex_root.exists():

        # 失败载荷同时服务 JSON 自动化和人工文本输出。
        dict_failure = build_guard_failure(  # Codex sessions 根缺失的结构化诊断
            path_codex_root, path_requested_root, args.hours  # 环境根、覆盖路径和窗口
        )  # Codex 环境守卫失败结果

        # JSON 模式保留结构化失败原因和路径字段。
        if args.json:

            # emit_json 统一序列化和换行行为。
            emit_json(dict_failure)

            # 守卫失败后不再执行目录汇总。
            return

        # 人工模式解释自动发现失败和覆盖参数边界。
        sys.stdout.write(render_guard_failure_text(dict_failure) + "\n")

        # 守卫失败文本输出后结束命令。
        return

    # 显式覆盖存在时验证其仍属于活动 Codex sessions 树。
    if path_requested_root is not None:

        # relative_to 成功是目录位于安全边界内的证明。
        try:

            # 返回值无需使用，调用本身完成归属验证。
            path_requested_root.relative_to(path_codex_root)

        # ValueError 表示请求位置越过活动 Codex 根。
        except ValueError:

            # 越界载荷保留根目录和请求目录以支持诊断。
            dict_failure = build_requested_root_failure(  # 覆盖目录越界的结构化诊断
                path_codex_root, path_requested_root, args.hours  # 边界两端与请求窗口
            )  # sessions-root 路径边界失败结果

            # JSON 模式输出机器可读的边界失败。
            if args.json:

                # 复用公共 JSON 输出合同。
                emit_json(dict_failure)

                # 越界目录不得继续进入扫描流程。
                return

            # 人工模式解释为什么覆盖目录不能跳出活动树。
            sys.stdout.write(render_requested_root_failure_text(dict_failure) + "\n")

            # 边界失败文本输出后结束命令。
            return

    # 合法覆盖优先，否则扫描自动发现的 sessions 根。
    path_sessions_root = path_requested_root or path_codex_root  # 本次实际扫描目录

    # 统计阶段只接收已通过环境和路径边界的目录。
    dict_summary = summarize_sessions(  # 时间窗内按文件和全局累计的 token 结果
        path_sessions_root, datetime_since, datetime_now  # 扫描根和包含式时间窗
    )  # 时间窗内的 token 汇总

    # 完整载荷补充请求路径和时间上下文，供两类输出共享。
    dict_payload = build_summary_payload(  # JSON 与文本输出共享的完整成功载荷
        dict_summary,  # 文件明细和全局计数

        # 路径字段保留自动发现、实际扫描和显式覆盖三种语义。
        codex_root=path_codex_root,  # 自动发现安全根
        sessions_root=path_sessions_root,  # 本次汇总扫描位置
        requested_root=path_requested_root,  # 可选覆盖目录

        # 时间字段记录汇总使用的精确 UTC 边界。
        since=datetime_since,  # 汇总窗口起始边界
        now=datetime_now,  # 汇总窗口结束边界
        hours=args.hours,  # 请求回溯小时数
    )

    # JSON 模式直接输出完整载荷，不生成终端文本。
    if args.json:

        # 公共输出器保证机器可读格式稳定。
        emit_json(dict_payload)

        # JSON 输出完成后无需执行文本渲染。
        return

    # 默认人工模式按 verbose 开关决定是否展开文件明细。
    sys.stdout.write(render_text(dict_payload, verbose=args.verbose) + "\n")

# 导入模块用于测试时不自动读取本地 session 文件。
if __name__ == "__main__":

    # 仅直接执行脚本时启动 CLI，导入模块不会扫描本地 sessions。
    main()

