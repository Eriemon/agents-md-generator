#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agents_common import codex_sessions_root, emit_json


TOKEN_KEYS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)


@dataclass
class TokenCounter:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0
    total_tokens: int = 0
    usage_records: int = 0

    def add_usage(self, usage: Mapping[str, Any]) -> bool:
        values: dict[str, int] = {}
        for key in TOKEN_KEYS:
            raw_value = usage.get(key)
            if raw_value is None:
                values[key] = 0
                continue
            try:
                values[key] = int(raw_value)
            except (TypeError, ValueError):
                return False
        for key, value in values.items():
            setattr(self, key, getattr(self, key) + value)
        self.usage_records += 1
        return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize Codex token usage from local session jsonl files."
    )
    parser.add_argument("--sessions-root", help="Path to the Codex sessions directory for testing or diagnostics")
    parser.add_argument("--hours", type=float, default=48.0, help="Lookback window in hours")
    parser.add_argument("--now", help="Override current time with an ISO-8601 timestamp")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument("--verbose", action="store_true", help="Show per-file rows in text output")
    return parser.parse_args()


def parse_timestamp(raw_value: str) -> datetime:
    normalized = raw_value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iter_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return records

    for line in text.splitlines():
        payload = line.strip()
        if not payload:
            continue
        try:
            record = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def extract_last_token_usage(record: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if record.get("type") != "event_msg":
        return None
    payload = record.get("payload")
    if not isinstance(payload, Mapping) or payload.get("type") != "token_count":
        return None
    info = payload.get("info")
    if not isinstance(info, Mapping):
        return None
    usage = info.get("last_token_usage")
    if isinstance(usage, Mapping):
        return usage
    return None


def summarize_sessions(root: Path, since: datetime, now: datetime) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    grand_total = TokenCounter()
    matched_files = 0

    if not root.exists():
        return {
            "ok": True,
            "missing_root": True,
            "matched_file_count": 0,
            "summarized_file_count": 0,
            "rows": [],
            "grand_total": asdict(grand_total),
        }

    for path in sorted(root.rglob("*.jsonl")):
        counter = TokenCounter()
        last_event_timestamp = ""

        for record in iter_records(path):
            raw_timestamp = record.get("timestamp")
            if not isinstance(raw_timestamp, str):
                continue
            try:
                event_time = parse_timestamp(raw_timestamp)
            except ValueError:
                continue
            if event_time < since or event_time > now:
                continue

            usage = extract_last_token_usage(record)
            if usage is None:
                continue
            if counter.add_usage(usage):
                event_iso = event_time.isoformat()
                if not last_event_timestamp or event_iso > last_event_timestamp:
                    last_event_timestamp = event_iso

        if counter.usage_records == 0:
            continue

        matched_files += 1
        grand_total.input_tokens += counter.input_tokens
        grand_total.cached_input_tokens += counter.cached_input_tokens
        grand_total.output_tokens += counter.output_tokens
        grand_total.reasoning_output_tokens += counter.reasoning_output_tokens
        grand_total.total_tokens += counter.total_tokens
        grand_total.usage_records += counter.usage_records
        rows.append(
            {
                "file": str(path),
                "last_event_timestamp": last_event_timestamp,
                **asdict(counter),
            }
        )

    rows.sort(key=lambda item: item["last_event_timestamp"], reverse=True)
    return {
        "ok": True,
        "missing_root": False,
        "matched_file_count": matched_files,
        "summarized_file_count": len(rows),
        "rows": rows,
        "grand_total": asdict(grand_total),
    }


def format_yi(value: int) -> str:
    return f"{value / 100000000:.2f}亿"


def build_guard_failure(codex_root: Path, requested_root: Path | None, hours: float) -> dict[str, Any]:
    sessions_root = requested_root or codex_root
    return {
        "ok": False,
        "reason": "codex_sessions_not_found",
        "hours": hours,
        "codex_sessions_root": str(codex_root),
        "requested_sessions_root": str(requested_root) if requested_root else "",
        "sessions_root": str(sessions_root),
        "message": "Codex sessions directory was not found; token usage review only runs when the current environment resolves a Codex sessions directory.",
    }


def build_requested_root_failure(
    codex_root: Path,
    requested_root: Path,
    hours: float,
) -> dict[str, Any]:
    return {
        "ok": False,
        "reason": "sessions_root_outside_codex_root",
        "hours": hours,
        "codex_sessions_root": str(codex_root),
        "requested_sessions_root": str(requested_root),
        "sessions_root": str(requested_root),
        "message": "Requested sessions root must stay within the active Codex sessions directory.",
    }


def build_summary_payload(
    summary: dict[str, Any],
    *,
    codex_root: Path,
    sessions_root: Path,
    requested_root: Path | None,
    since: datetime,
    now: datetime,
    hours: float,
) -> dict[str, Any]:
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


def render_guard_failure_text(payload: Mapping[str, Any]) -> str:
    lines = [
        f"=== 最近 {payload['hours']:g} 小时 Codex 本机 Token 使用统计 ===",
        f"Codex Sessions 目录: {payload['codex_sessions_root']}",
        f"请求 Sessions 目录: {payload['sessions_root']}",
        "",
        f"未检测到 Codex sessions 目录：{payload['codex_sessions_root']}",
        "此功能仅在当前环境可解析到 `$CODEX_HOME/sessions` 或 `~/.codex/sessions` 且目录存在时可执行。",
    ]
    if payload.get("requested_sessions_root"):
        lines.append("`--sessions-root` 仅用于测试或诊断，不能绕过 Codex 环境检测。")
    return "\n".join(lines)


def render_requested_root_failure_text(payload: Mapping[str, Any]) -> str:
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


def render_text(summary: Mapping[str, Any], *, verbose: bool) -> str:
    lines = [
        f"=== 最近 {summary['hours']:g} 小时 Codex 本机 Token 使用统计 ===",
        f"Sessions 目录: {summary['sessions_root']}",
        f"统计起点: {summary['since']}",
        f"统计终点: {summary['now']}",
        f"匹配 JSONL 文件数: {summary['matched_file_count']}",
        "",
    ]

    if summary.get("missing_root"):
        lines.append(f"未找到指定的 sessions 目录：{summary['sessions_root']}")
        return "\n".join(lines)

    rows = summary["rows"]
    if not rows:
        lines.append("没有在指定时间窗口内找到可汇总的 token_count / last_token_usage 记录。")
        lines.append("建议：在 Codex 当前会话输入 /status 查看当前会话 token。")
        return "\n".join(lines)

    grand = summary["grand_total"]
    lines.extend(
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

    if verbose:
        lines.extend(["", "--- 按文件汇总 ---"])
        for row in rows:
            lines.append(
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
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    now = parse_timestamp(args.now) if args.now else datetime.now(timezone.utc)
    since = now - timedelta(hours=args.hours)
    codex_root = codex_sessions_root().resolve()
    requested_root = Path(args.sessions_root).expanduser().resolve() if args.sessions_root else None

    if not codex_root.exists():
        failure = build_guard_failure(codex_root, requested_root, args.hours)
        if args.json:
            emit_json(failure)
            return
        print(render_guard_failure_text(failure))
        return

    if requested_root is not None:
        try:
            requested_root.relative_to(codex_root)
        except ValueError:
            failure = build_requested_root_failure(codex_root, requested_root, args.hours)
            if args.json:
                emit_json(failure)
                return
            print(render_requested_root_failure_text(failure))
            return

    sessions_root = requested_root or codex_root
    summary = summarize_sessions(sessions_root, since, now)
    payload = build_summary_payload(
        summary,
        codex_root=codex_root,
        sessions_root=sessions_root,
        requested_root=requested_root,
        since=since,
        now=now,
        hours=args.hours,
    )

    if args.json:
        emit_json(payload)
        return
    print(render_text(payload, verbose=args.verbose))


if __name__ == "__main__":
    main()
