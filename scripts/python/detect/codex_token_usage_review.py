#!/usr/bin/env python3
from __future__ import annotations

# 分类脚本可从任意任务目录直接执行，这里补齐兄弟任务模块路径。
import sys
from pathlib import Path

_scripts_python_root = Path(__file__).resolve().parents[1]
for _task_dir in _scripts_python_root.iterdir():
    if _task_dir.is_dir():
        _task_path = str(_task_dir)
        if _task_path not in sys.path:
            sys.path.insert(0, _task_path)

# 导入 脚本治理 所需的依赖模块。
import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

# 保留 dont write bytecode 中间值，支撑 模块入口 的当前计算步骤。
sys.dont_write_bytecode = True  # dont write bytecode 用于本步治理判断

# 导入 脚本治理 所需的依赖模块。
from agents_common import codex_sessions_root, emit_json


# 保留 TOKEN KEYS 中间值，支撑 模块入口 的当前计算步骤。
TOKEN_KEYS = (  # TOKEN KEYS 用于本步治理判断
    "input_tokens",  # TOKEN KEYS 用于本步治理判断
    "cached_input_tokens",  # TOKEN KEYS 用于本步治理判断
    "output_tokens",  # TOKEN KEYS 用于本步治理判断
    "reasoning_output_tokens",  # TOKEN KEYS 用于本步治理判断
    "total_tokens",  # TOKEN KEYS 用于本步治理判断
)


# 补充脚本治理代码段的职责说明。
@dataclass
class TokenCounter:

    # 收集 input tokens 条目，保持 模块入口 的处理顺序稳定。
    input_tokens: int = 0  # input tokens 用于本步治理判断

    # 收集 cached input tokens 条目，保持 模块入口 的处理顺序稳定。
    cached_input_tokens: int = 0  # cached input tokens 用于本步治理判断

    # 收集 output tokens 条目，保持 模块入口 的处理顺序稳定。
    output_tokens: int = 0  # output tokens 用于本步治理判断

    # 收集 reasoning output tokens 条目，保持 模块入口 的处理顺序稳定。
    reasoning_output_tokens: int = 0  # reasoning output tokens 用于本步治理判断

    # 收集 total tokens 条目，保持 模块入口 的处理顺序稳定。
    total_tokens: int = 0  # total tokens 用于本步治理判断

    # 收集 usage records 条目，保持 模块入口 的处理顺序稳定。
    usage_records: int = 0  # usage records 用于本步治理判断

    # 定义 add_usage 的脚本治理处理入口。
    def add_usage(self, usage: Mapping[str, Any]) -> bool:

        # 收集 values 条目，保持 add_usage 的处理顺序稳定。
        dict_values: dict[str, int] = {}  # values 用于本步治理判断

        # 逐项推进 add_usage 的候选项检查。
        for key in TOKEN_KEYS:

            # 保留 raw value 中间值，支撑 add_usage 的当前计算步骤。
            raw_value = usage.get(key)  # raw value 用于本步治理判断

            # 检查 add_usage 的当前条件是否需要进入专门分支。
            if raw_value is None:

                # 保留 中间载荷 中间值，支撑 add_usage 的当前计算步骤。
                dict_values[key] = 0  # 中间载荷 用于本步治理判断

                # 分隔 add_usage 的控制流边界。
                continue

            # 保护 add_usage 中允许失败的外部访问。
            try:

                # 保留 中间载荷 中间值，支撑 add_usage 的当前计算步骤。
                dict_values[key] = int(raw_value)  # 中间载荷 用于本步治理判断
            except (TypeError, ValueError):

                # 返回 add_usage 已整理完成的调用载荷。
                return False

        # 逐项推进 add_usage 的候选项检查。
        for key, raw_value in dict_values.items():

            # 调用 setattr 完成 add_usage 的当前动作。
            setattr(self, key, getattr(self, key) + raw_value)

        # 收集 usage records 条目，保持 add_usage 的处理顺序稳定。
        self.usage_records += 1  # usage records 用于本步治理判断

        # 返回 add_usage 已整理完成的调用载荷。
        return True


# 定义 parse_args 的脚本治理处理入口。
def parse_args() -> argparse.Namespace:

    # 保留 parser 中间值，支撑 parse_args 的当前计算步骤。
    parser = argparse.ArgumentParser(  # parser 用于本步治理判断
        description="Summarize Codex token usage from local session jsonl files."  # parser 用于本步治理判断
    )

    # 调用 add_argument 完成 parse_args 的当前动作。
    parser.add_argument("--sessions-root", help="Path to the Codex sessions directory for testing or diagnostics")

    # 调用 add_argument 完成 parse_args 的当前动作。
    parser.add_argument("--hours", type=float, default=48.0, help="Lookback window in hours")

    # 调用 add_argument 完成 parse_args 的当前动作。
    parser.add_argument("--now", help="Override current time with an ISO-8601 timestamp")

    # 调用 add_argument 完成 parse_args 的当前动作。
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")

    # 调用 add_argument 完成 parse_args 的当前动作。
    parser.add_argument("--verbose", action="store_true", help="Show per-file rows in text output")

    # 返回 parse_args 已整理完成的调用载荷。
    return parser.parse_args()


# 定义 parse_timestamp 的脚本治理处理入口。
def parse_timestamp(raw_value: str) -> datetime:

    # 保留 normalized 中间值，支撑 parse_timestamp 的当前计算步骤。
    normalized = raw_value.strip()  # normalized 用于本步治理判断

    # 检查 parse_timestamp 的当前条件是否需要进入专门分支。
    if normalized.endswith("Z"):

        # 保留 normalized 中间值，支撑 parse_timestamp 的当前计算步骤。
        normalized = normalized[:-1] + "+00:00"  # normalized 用于本步治理判断

    # 保留 parsed 中间值，支撑 parse_timestamp 的当前计算步骤。
    parsed = datetime.fromisoformat(normalized)  # parsed 用于本步治理判断

    # 检查 parse_timestamp 的当前条件是否需要进入专门分支。
    if parsed.tzinfo is None:

        # 返回 parse_timestamp 已整理完成的调用载荷。
        return parsed.replace(tzinfo=timezone.utc)

    # 返回 parse_timestamp 已整理完成的调用载荷。
    return parsed.astimezone(timezone.utc)


# 定义 iter_records 的脚本治理处理入口。
def iter_records(path: Path) -> list[dict[str, Any]]:

    # 收集 records 条目，保持 iter_records 的处理顺序稳定。
    list_records: list[dict[str, Any]] = []  # records 用于本步治理判断

    # 保护 iter_records 中允许失败的外部访问。
    try:

        # 保留 text 中间值，支撑 iter_records 的当前计算步骤。
        text = path.read_text(encoding="utf-8")  # text 用于本步治理判断
    except OSError:

        # 返回 iter_records 已整理完成的调用载荷。
        return list_records

    # 逐项推进 iter_records 的候选项检查。
    for line in text.splitlines():

        # 保留 payload 中间值，支撑 iter_records 的当前计算步骤。
        payload = line.strip()  # payload 用于本步治理判断

        # 检查 iter_records 的当前条件是否需要进入专门分支。
        if not payload:

            # 分隔 iter_records 的控制流边界。
            continue

        # 保护 iter_records 中允许失败的外部访问。
        try:

            # 保留 record 中间值，支撑 iter_records 的当前计算步骤。
            record = json.loads(payload)  # record 用于本步治理判断
        except json.JSONDecodeError:

            # 分隔 iter_records 的控制流边界。
            continue

        # 检查 iter_records 的当前条件是否需要进入专门分支。
        if isinstance(record, dict):

            # 调用 append 完成 iter_records 的当前动作。
            list_records.append(record)

    # 返回 iter_records 已整理完成的调用载荷。
    return list_records


# 定义 extract_last_token_usage 的脚本治理处理入口。
def extract_last_token_usage(record: Mapping[str, Any]) -> Mapping[str, Any] | None:

    # 检查 extract_last_token_usage 的当前条件是否需要进入专门分支。
    if record.get("type") != "event_msg":

        # 返回 extract_last_token_usage 已整理完成的调用载荷。
        return None

    # 保留 payload 中间值，支撑 extract_last_token_usage 的当前计算步骤。
    payload = record.get("payload")  # payload 用于本步治理判断

    # 检查 extract_last_token_usage 的当前条件是否需要进入专门分支。
    if not isinstance(payload, Mapping) or payload.get("type") != "token_count":

        # 返回 extract_last_token_usage 已整理完成的调用载荷。
        return None

    # 保留 info 中间值，支撑 extract_last_token_usage 的当前计算步骤。
    dict_info = payload.get("info")  # info 用于本步治理判断

    # 检查 extract_last_token_usage 的当前条件是否需要进入专门分支。
    if not isinstance(dict_info, Mapping):

        # 返回 extract_last_token_usage 已整理完成的调用载荷。
        return None

    # 保留 usage 中间值，支撑 extract_last_token_usage 的当前计算步骤。
    usage = dict_info.get("last_token_usage")  # usage 用于本步治理判断

    # 检查 extract_last_token_usage 的当前条件是否需要进入专门分支。
    if isinstance(usage, Mapping):

        # 返回 extract_last_token_usage 已整理完成的调用载荷。
        return usage

    # 返回 extract_last_token_usage 已整理完成的调用载荷。
    return None


# 定义 summarize_sessions 的脚本治理处理入口。
def summarize_sessions(root: Path, since: datetime, now: datetime) -> dict[str, Any]:

    # 收集 rows 条目，保持 summarize_sessions 的处理顺序稳定。
    list_rows: list[dict[str, Any]] = []  # rows 用于本步治理判断

    # 保留 grand total 中间值，支撑 summarize_sessions 的当前计算步骤。
    grand_total = TokenCounter()  # grand total 用于本步治理判断

    # 收集 matched files 条目，保持 summarize_sessions 的处理顺序稳定。
    int_matched_files = 0  # matched files 用于本步治理判断

    # 检查 summarize_sessions 的当前条件是否需要进入专门分支。
    if not root.exists():

        # 返回 summarize_sessions 已整理完成的调用载荷。
        return {
            "ok": True,
            "missing_root": True,
            "matched_file_count": 0,
            "summarized_file_count": 0,
            "rows": [],
            "grand_total": asdict(grand_total),
        }

    # 逐项推进 summarize_sessions 的候选项检查。
    for path in sorted(root.rglob("*.jsonl")):

        # 保留 counter 中间值，支撑 summarize_sessions 的当前计算步骤。
        counter = TokenCounter()  # counter 用于本步治理判断

        # 保留 last event timestamp 中间值，支撑 summarize_sessions 的当前计算步骤。
        str_last_event_timestamp = ""  # last event timestamp 用于本步治理判断

        # 逐项推进 summarize_sessions 的候选项检查。
        for record in iter_records(path):

            # 保留 raw timestamp 中间值，支撑 summarize_sessions 的当前计算步骤。
            raw_timestamp = record.get("timestamp")  # raw timestamp 用于本步治理判断

            # 检查 summarize_sessions 的当前条件是否需要进入专门分支。
            if not isinstance(raw_timestamp, str):

                # 分隔 summarize_sessions 的控制流边界。
                continue

            # 保护 summarize_sessions 中允许失败的外部访问。
            try:

                # 保留 event time 中间值，支撑 summarize_sessions 的当前计算步骤。
                datetime_event_time = parse_timestamp(raw_timestamp)  # event time 用于本步治理判断
            except ValueError:

                # 分隔 summarize_sessions 的控制流边界。
                continue

            # 检查 summarize_sessions 的当前条件是否需要进入专门分支。
            if datetime_event_time < since or datetime_event_time > now:

                # 分隔 summarize_sessions 的控制流边界。
                continue

            # 保留 usage 中间值，支撑 summarize_sessions 的当前计算步骤。
            usage = extract_last_token_usage(record)  # usage 用于本步治理判断

            # 检查 summarize_sessions 的当前条件是否需要进入专门分支。
            if usage is None:

                # 分隔 summarize_sessions 的控制流边界。
                continue

            # 检查 summarize_sessions 的当前条件是否需要进入专门分支。
            if counter.add_usage(usage):

                # 保留 event iso 中间值，支撑 summarize_sessions 的当前计算步骤。
                event_iso = datetime_event_time.isoformat()  # event iso 用于本步治理判断

                # 检查 summarize_sessions 的当前条件是否需要进入专门分支。
                if not str_last_event_timestamp or event_iso > str_last_event_timestamp:

                    # 保留 last event timestamp 中间值，支撑 summarize_sessions 的当前计算步骤。
                    str_last_event_timestamp = event_iso  # last event timestamp 用于本步治理判断

        # 检查 summarize_sessions 的当前条件是否需要进入专门分支。
        if counter.usage_records == 0:

            # 分隔 summarize_sessions 的控制流边界。
            continue

        # 收集 matched files 条目，保持 summarize_sessions 的处理顺序稳定。
        int_matched_files += 1  # matched files 用于本步治理判断

        # 收集 input tokens 条目，保持 summarize_sessions 的处理顺序稳定。
        grand_total.input_tokens += counter.input_tokens  # input tokens 用于本步治理判断

        # 收集 cached input tokens 条目，保持 summarize_sessions 的处理顺序稳定。
        grand_total.cached_input_tokens += counter.cached_input_tokens  # cached input tokens 用于本步治理判断

        # 收集 output tokens 条目，保持 summarize_sessions 的处理顺序稳定。
        grand_total.output_tokens += counter.output_tokens  # output tokens 用于本步治理判断

        # 收集 reasoning output tokens 条目，保持 summarize_sessions 的处理顺序稳定。
        grand_total.reasoning_output_tokens += counter.reasoning_output_tokens  # reasoning output tokens 用于本步治理判断

        # 收集 total tokens 条目，保持 summarize_sessions 的处理顺序稳定。
        grand_total.total_tokens += counter.total_tokens  # total tokens 用于本步治理判断

        # 收集 usage records 条目，保持 summarize_sessions 的处理顺序稳定。
        grand_total.usage_records += counter.usage_records  # usage records 用于本步治理判断

        # 调用 append 完成 summarize_sessions 的当前动作。
        list_rows.append(
            {
                "file": str(path),
                "last_event_timestamp": str_last_event_timestamp,
                **asdict(counter),
            }
        )

    # 调用 sort 完成 summarize_sessions 的当前动作。
    list_rows.sort(key=lambda item: item["last_event_timestamp"], reverse=True)

    # 返回 summarize_sessions 已整理完成的调用载荷。
    return {
        "ok": True,
        "missing_root": False,
        "matched_file_count": int_matched_files,
        "summarized_file_count": len(list_rows),
        "rows": list_rows,
        "grand_total": asdict(grand_total),
    }


# 定义 format_yi 的脚本治理处理入口。
def format_yi(value: int) -> str:

    # 返回 format_yi 已整理完成的调用载荷。
    return f"{value / 100000000:.2f}亿"


# 定义 build_guard_failure 的脚本治理处理入口。
def build_guard_failure(codex_root: Path, requested_root: Path | None, hours: float) -> dict[str, Any]:

    # 保留 sessions root 中间值，支撑 build_guard_failure 的当前计算步骤。
    sessions_root = requested_root or codex_root  # sessions root 用于本步治理判断

    # 返回 build_guard_failure 已整理完成的调用载荷。
    return {
        "ok": False,
        "reason": "codex_sessions_not_found",
        "hours": hours,
        "codex_sessions_root": str(codex_root),
        "requested_sessions_root": str(requested_root) if requested_root else "",
        "sessions_root": str(sessions_root),
        "message": "Codex sessions directory was not found; token usage review only runs when the current environment resolves a Codex sessions directory.",
    }


# 定义 build_requested_root_failure 的脚本治理处理入口。
def build_requested_root_failure(
    codex_root: Path,
    requested_root: Path,
    hours: float,
) -> dict[str, Any]:

    # 返回 build_requested_root_failure 已整理完成的调用载荷。
    return {
        "ok": False,
        "reason": "sessions_root_outside_codex_root",
        "hours": hours,
        "codex_sessions_root": str(codex_root),
        "requested_sessions_root": str(requested_root),
        "sessions_root": str(requested_root),
        "message": "Requested sessions root must stay within the active Codex sessions directory.",
    }


# 定义 build_summary_payload 的脚本治理处理入口。
def build_summary_payload(
    summary: dict[str, Any],
    *,
    codex_root: Path,
    sessions_root: Path,
    requested_root: Path | None,
    since: datetime,

    # 分隔当前密集代码块，保留原有执行顺序。
    now: datetime,
    hours: float,
) -> dict[str, Any]:

    # 返回 build_summary_payload 已整理完成的调用载荷。
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


# 定义 render_guard_failure_text 的脚本治理处理入口。
def render_guard_failure_text(payload: Mapping[str, Any]) -> str:

    # 收集 lines 条目，保持 render_guard_failure_text 的处理顺序稳定。
    list_lines = [  # lines 用于本步治理判断
        f"=== 最近 {payload['hours']:g} 小时 Codex 本机 Token 使用统计 ===",  # lines 用于本步治理判断
        f"Codex Sessions 目录: {payload['codex_sessions_root']}",  # lines 用于本步治理判断
        f"请求 Sessions 目录: {payload['sessions_root']}",  # lines 用于本步治理判断
        "",  # lines 用于本步治理判断
        f"未检测到 Codex sessions 目录：{payload['codex_sessions_root']}",  # lines 用于本步治理判断
        "此功能仅在当前环境可解析到 `$CODEX_HOME/sessions` 或 `~/.codex/sessions` 且目录存在时可执行。",  # lines 用于本步治理判断
    ]

    # 检查 render_guard_failure_text 的当前条件是否需要进入专门分支。
    if payload.get("requested_sessions_root"):

        # 调用 append 完成 render_guard_failure_text 的当前动作。
        list_lines.append("`--sessions-root` 仅用于测试或诊断，不能绕过 Codex 环境检测。")

    # 返回 render_guard_failure_text 已整理完成的调用载荷。
    return "\n".join(list_lines)


# 定义 render_requested_root_failure_text 的脚本治理处理入口。
def render_requested_root_failure_text(payload: Mapping[str, Any]) -> str:

    # 返回 render_requested_root_failure_text 已整理完成的调用载荷。
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


# 定义 render_text 的脚本治理处理入口。
def render_text(summary: Mapping[str, Any], *, verbose: bool) -> str:

    # 收集 lines 条目，保持 render_text 的处理顺序稳定。
    list_lines = [  # lines 用于本步治理判断
        f"=== 最近 {summary['hours']:g} 小时 Codex 本机 Token 使用统计 ===",  # lines 用于本步治理判断
        f"Sessions 目录: {summary['sessions_root']}",  # lines 用于本步治理判断
        f"统计起点: {summary['since']}",  # lines 用于本步治理判断
        f"统计终点: {summary['now']}",  # lines 用于本步治理判断
        f"匹配 JSONL 文件数: {summary['matched_file_count']}",  # lines 用于本步治理判断
        "",  # lines 用于本步治理判断
    ]

    # 检查 render_text 的当前条件是否需要进入专门分支。
    if summary.get("missing_root"):

        # 调用 append 完成 render_text 的当前动作。
        list_lines.append(f"未找到指定的 sessions 目录：{summary['sessions_root']}")

        # 返回 render_text 已整理完成的调用载荷。
        return "\n".join(list_lines)

    # 收集 rows 条目，保持 render_text 的处理顺序稳定。
    rows = summary["rows"]  # rows 用于本步治理判断

    # 检查 render_text 的当前条件是否需要进入专门分支。
    if not rows:

        # 调用 append 完成 render_text 的当前动作。
        list_lines.append("没有在指定时间窗口内找到可汇总的 token_count / last_token_usage 记录。")

        # 调用 append 完成 render_text 的当前动作。
        list_lines.append("建议：在 Codex 当前会话输入 /status 查看当前会话 token。")

        # 返回 render_text 已整理完成的调用载荷。
        return "\n".join(list_lines)

    # 保留 grand 中间值，支撑 render_text 的当前计算步骤。
    grand = summary["grand_total"]  # grand 用于本步治理判断

    # 调用 extend 完成 render_text 的当前动作。
    list_lines.extend(
        [
            "--- 总计 ---",
            f"InputTokens: {grand['input_tokens']}",
            f"CachedInputTokens: {grand['cached_input_tokens']}",
            f"OutputTokens: {grand['output_tokens']}",
            f"ReasoningOutputTokens: {grand['reasoning_output_tokens']}",
            f"TotalTokens: {grand['total_tokens']} (≈{format_yi(grand['total_tokens'])})",
            f"UsageRecords: {grand['usage_records']}",
        ]
    )

    # 检查 render_text 的当前条件是否需要进入专门分支。
    if verbose:

        # 调用 extend 完成 render_text 的当前动作。
        list_lines.extend(["", "--- 按文件汇总 ---"])

        # 逐项推进 render_text 的候选项检查。
        for row in rows:

            # 调用 append 完成 render_text 的当前动作。
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

    # 返回 render_text 已整理完成的调用载荷。
    return "\n".join(list_lines)


# 定义 main 的脚本治理处理入口。
def main() -> None:

    # 收集 args 条目，保持 main 的处理顺序稳定。
    args = parse_args()  # args 用于本步治理判断

    # 保留 now 中间值，支撑 main 的当前计算步骤。
    now = parse_timestamp(args.now) if args.now else datetime.now(timezone.utc)  # now 用于本步治理判断

    # 保留 since 中间值，支撑 main 的当前计算步骤。
    since = now - timedelta(hours=args.hours)  # since 用于本步治理判断

    # 保留 codex root 中间值，支撑 main 的当前计算步骤。
    codex_root = codex_sessions_root().resolve()  # codex root 用于本步治理判断

    # 保留 requested root 中间值，支撑 main 的当前计算步骤。
    requested_root = Path(args.sessions_root).expanduser().resolve() if args.sessions_root else None  # requested root 用于本步治理判断

    # 检查 main 的当前条件是否需要进入专门分支。
    if not codex_root.exists():

        # 保留 failure 中间值，支撑 main 的当前计算步骤。
        dict_failure = build_guard_failure(codex_root, requested_root, args.hours)  # failure 用于本步治理判断

        # 检查 main 的当前条件是否需要进入专门分支。
        if args.json:

            # 调用 emit_json 完成 main 的当前动作。
            emit_json(dict_failure)

            # 返回 main 已整理完成的调用载荷。
            return

        # 调用 print 完成 main 的当前动作。
        print(render_guard_failure_text(dict_failure))

        # 返回 main 已整理完成的调用载荷。
        return

    # 检查 main 的当前条件是否需要进入专门分支。
    if requested_root is not None:

        # 保护 main 中允许失败的外部访问。
        try:

            # 调用 relative_to 完成 main 的当前动作。
            requested_root.relative_to(codex_root)
        except ValueError:

            # 保留 failure 中间值，支撑 main 的当前计算步骤。
            dict_failure = build_requested_root_failure(codex_root, requested_root, args.hours)  # failure 用于本步治理判断

            # 检查 main 的当前条件是否需要进入专门分支。
            if args.json:

                # 调用 emit_json 完成 main 的当前动作。
                emit_json(dict_failure)

                # 返回 main 已整理完成的调用载荷。
                return

            # 调用 print 完成 main 的当前动作。
            print(render_requested_root_failure_text(dict_failure))

            # 返回 main 已整理完成的调用载荷。
            return

    # 保留 sessions root 中间值，支撑 main 的当前计算步骤。
    sessions_root = requested_root or codex_root  # sessions root 用于本步治理判断

    # 保留 summary 中间值，支撑 main 的当前计算步骤。
    dict_summary = summarize_sessions(sessions_root, since, now)  # summary 用于本步治理判断

    # 保留 payload 中间值，支撑 main 的当前计算步骤。
    dict_payload = build_summary_payload(  # payload 用于本步治理判断
        dict_summary,  # payload 用于本步治理判断
        codex_root=codex_root,  # payload 用于本步治理判断
        sessions_root=sessions_root,  # payload 用于本步治理判断
        requested_root=requested_root,  # payload 用于本步治理判断
        since=since,  # payload 用于本步治理判断
        now=now,  # payload 用于本步治理判断

        # 分隔当前密集代码块，保留原有执行顺序。
        hours=args.hours,  # payload 用于本步治理判断
    )

    # 检查 main 的当前条件是否需要进入专门分支。
    if args.json:

        # 调用 emit_json 完成 main 的当前动作。
        emit_json(dict_payload)

        # 返回 main 已整理完成的调用载荷。
        return

    # 调用 print 完成 main 的当前动作。
    print(render_text(dict_payload, verbose=args.verbose))


# 检查 模块入口 的当前条件是否需要进入专门分支。
if __name__ == "__main__":

    # 调用 main 完成 模块入口 的当前动作。
    main()


