# Coding Behavior Language Skill Routing

Generated root `AGENTS.md` files summarize this routing from `.agents/global-rule-overrides.json` key `coding_behavior.language_skill_routing`. That object has exactly three fields: `shared`, `python`, and `script`. The root keeps the rule compact; this reference records the intended boundaries.

## Baseline Rules

- Language-specific coding skills are a Coding Behavior Baseline rule, not a standalone comment-policy section.
- ROOT create, repair, and verification resolve readable skill installation from `CODEX_HOME/skills/<skill-name>` before choosing route wording.
- Python and script-family create/modify work must think before editing, satisfy applicable gates while creating or modifying, and must not defer gate compliance until after the implementation is complete.
- `shared` contains those cross-language preflight and gate requirements and is rendered as `语言技能共同门禁` only once（只渲染一次）.
- `python` and `script` contain only their target scope, final owner, and cross-language boundaries; neither field may repeat the shared gate body.
- When both readable skills are installed, `shared` requires loading both and continuing only after both gates pass.
- When only the target language owner is installed, that route requires the installed owner and names no missing companion skill.
- When the target language owner is missing, the route remains present with language boundaries, but names no missing skill and does not suggest installation.
- Python and script owner installation states are evaluated independently.
- Python code generation, modification, commenting, and normalization keep final ownership with `readable-python-generator`.
- bat/cmd, shell/bash, PowerShell, and Tcl script generation, review, refactor, repair, explanation, and Chinese semantic commenting keep final ownership with `readable-script-generator`.
- The rendered root keeps the Python ownership phrase Python 最终仍由 `readable-python-generator` 负责.
- The rendered root keeps the script ownership phrase 脚本目标最终由 `readable-script-generator` 负责.
- The script route keeps the explicit cross-language boundary phrase Python 目标继续使用 `readable-python-generator`.
- 调用 Python 外部命令的脚本包装器 remains a script target and keeps final ownership with `readable-script-generator` when that owner is installed.
- Generated code must preserve line breaks and blank-line separation; 不能把语句、注释、函数粘连到一起；严禁把代码压缩到一行，严禁生成人看不懂的炫技代码.

## Python

For `.py` files and explicit Python tasks, satisfy the installation-aware preflight while editing. When available, `readable-python-generator` owns the concrete dispatcher, comment-quality, typed-variable-naming, and quality gates.

## Script Languages

For bat/cmd, shell/bash, PowerShell, and Tcl deliverables, satisfy the installation-aware preflight while editing. When available, `readable-script-generator` owns the concrete script gates:

- bat/cmd: `.bat`, `.cmd`
- shell/bash: `.sh`
- PowerShell: `.ps1`, `.psm1`
- Tcl: `.tcl`

The target language decides the final owner after all applicable installed-skill gates pass. A shell, bat, PowerShell, or Tcl wrapper that invokes `python` remains a script deliverable because the file being generated or edited is still a script.
