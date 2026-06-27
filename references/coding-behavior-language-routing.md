# Coding Behavior Language Skill Routing

Generated root `AGENTS.md` files summarize this routing from `.agents/global-rule-overrides.json` key `coding_behavior.language_skill_routing`. The root keeps the rule compact; this reference records the intended boundaries.

## Baseline Rules

- Language-specific coding skills are a Coding Behavior Baseline rule, not a standalone comment-policy section.
- Python code generation, modification, commenting, and normalization must use `readable-python-generator` first.
- bat/cmd, shell/bash, PowerShell, and Tcl script generation, review, refactor, repair, explanation, and Chinese semantic commenting must use `readable-script-generator` first.
- Python targets must not be routed to `readable-script-generator`.
- 脚本包装器调用 Python commands are still script targets and use `readable-script-generator`.
- Generated code must preserve line breaks and blank-line separation; 不能把语句、注释、函数粘连到一起；严禁把代码压缩到一行，严禁生成人看不懂的炫技代码.

## Python

Use `readable-python-generator` for `.py` files and explicit Python tasks. Its dispatcher, comment-quality gate, typed-variable-naming checks, and quality gates own the concrete Python style.

## Script Languages

Use `readable-script-generator` when the deliverable stays in one of these script languages:

- bat/cmd: `.bat`, `.cmd`
- shell/bash: `.sh`
- PowerShell: `.ps1`, `.psm1`
- Tcl: `.tcl`

The target language decides the route. A shell, bat, PowerShell, or Tcl wrapper that invokes `python` remains a script deliverable because the file being generated or edited is still a script.
