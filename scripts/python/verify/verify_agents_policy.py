"""AGENTS 校验策略常量。"""

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

import re

COMMAND_RE = re.compile(r"`([^`\n]+)`")
PATH_RE = re.compile(r"`([^`\n]+(?:/|\\|\.md|\.json|\.toml|\.yml|\.yaml|\.py|\.ts|\.tsx|\.go|\.php)[^`\n]*)`")

ROOT_AGENTS_MAX_KB = 20
ROOT_AGENTS_MAX_BYTES = ROOT_AGENTS_MAX_KB * 1024

LANGUAGE_LOCK_RE = re.compile(
    r"All natural-language responses must use\s+(.+?)\s+unless the user explicitly switches languages\.",
    flags=re.IGNORECASE,
)

PLAN_LANGUAGE_LOCK_RE = re.compile(
    r"In Plan Mode,\s+any content inside\s+`<proposed_plan>`\s+must use\s+(.+?)\s+unless the user explicitly switches languages\.",
    flags=re.IGNORECASE,
)

CODING_BEHAVIOR_LANGUAGE_ROUTING_REQUIRED_SNIPPETS = (
    "编码行为配置来源：`.agents/global-rule-overrides.json`",
    "注释质量：只允许非显然意图、不变量、风险、生成边界或公共 API 行为注释",
    "不能把语句、注释、函数粘连到一起",
    "严禁把代码压缩到一行",
    "炫技代码",
    "语言技能路由（Python）：",
    "readable-python-generator",
    "语言技能路由（脚本）：",
    "readable-script-generator",
    "bat/cmd",
    "shell/bash",
    "PowerShell",
    "Tcl",
    "Python 目标继续使用 `readable-python-generator`",
    "脚本包装器调用 Python",
)

SCRIPT_OUTPUT_POLICY_REQUIRED_SNIPPETS = (
    "配置来源：`.agents/global-rule-overrides.json`",
    "`Kind` 列表只从该 JSON 读取",
    "代码不得内置业务枚举",
    "`> INFO: [{kind}]`",
    "`> WARNING: [{kind}]`",
    "`> ERR: [{kind}]`",
    "Python 过程性 INFO 默认打印",
    "`--quiet`",
    "WARNING 和 ERR 继续可见",
    "机器可读输出不套前缀",
)

PROJECT_LOCAL_GOVERNANCE_RUNTIME_RE = re.compile(
    r"`python\s+"
    r"(?:scripts/|skills/[^/\s]+/scripts/)"
    r"(?:manage_docs|manage_dirs|verify_agents|evaluate_skill|review_governance|"
    r"run_confidence_gate|collect_design_profile|render_agents)"
    r"\.py\b[^`]*`"
)


