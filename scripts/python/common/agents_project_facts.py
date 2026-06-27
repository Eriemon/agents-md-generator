from __future__ import annotations

# 该模块按顶层语句拆分到多个 shard，保持公开 API 与 CLI 行为不变。
from pathlib import Path

_SHARD_DIR = Path(__file__).resolve().parent
_SHARD_NAMES = (
    '_agents_project_facts_discovery.py',
    '_agents_project_facts_governance.py',
)

for _shard_name in _SHARD_NAMES:
    _shard_path = _SHARD_DIR / _shard_name
    exec(compile(_shard_path.read_text(encoding="utf-8"), str(_shard_path), "exec"), globals())
