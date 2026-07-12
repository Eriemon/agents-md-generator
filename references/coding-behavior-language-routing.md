# Coding Behavior Language Skill Routing

Generated root `AGENTS.md` files summarize this routing from `.agents/global-rule-overrides.json` key `coding_behavior.language_skill_routing`. The root keeps the rule compact; this reference records the intended boundaries.

## Baseline Rules

- Language-specific coding skills are a Coding Behavior Baseline rule, not a standalone comment-policy section.
- The rendered root keeps the exact blocker phrases `必须先思考`, `必须同时使用 readable-python-generator 和 readable-script-generator`, and `两个技能的门禁条件都满足后才能继续`.
- Python and script-family create/modify work must think first.
- Python and script-family create/modify work must explicitly load both `readable-python-generator` and `readable-script-generator`.
- Continue only after both skills' gates pass.
- Python code generation, modification, commenting, and normalization keep final ownership with `readable-python-generator`.
- bat/cmd, shell/bash, PowerShell, and Tcl script generation, review, refactor, repair, explanation, and Chinese semantic commenting keep final ownership with `readable-script-generator`.
- The rendered root keeps the Python ownership phrase Python 最终仍由 `readable-python-generator` 负责.
- The rendered root keeps the script ownership phrase 脚本目标最终由 `readable-script-generator` 负责.
- The script route keeps the explicit cross-language boundary phrase Python 目标继续使用 `readable-python-generator`.
- 脚本包装器调用 Python commands are still script targets and keep final ownership with `readable-script-generator`.
- Generated code must preserve line breaks and blank-line separation; 不能把语句、注释、函数粘连到一起；严禁把代码压缩到一行，严禁生成人看不懂的炫技代码.

## Python

For `.py` files and explicit Python tasks, first satisfy the dual-skill preflight, then keep the actual Python deliverable under `readable-python-generator`. Its dispatcher, comment-quality gate, typed-variable-naming checks, and quality gates own the concrete Python style.

## Script Languages

For bat/cmd, shell/bash, PowerShell, and Tcl deliverables, first satisfy the dual-skill preflight, then keep the actual script deliverable under `readable-script-generator`:

- bat/cmd: `.bat`, `.cmd`
- shell/bash: `.sh`
- PowerShell: `.ps1`, `.psm1`
- Tcl: `.tcl`

The target language decides the final owner after the dual-skill gate passes. A shell, bat, PowerShell, or Tcl wrapper that invokes `python` remains a script deliverable because the file being generated or edited is still a script.
