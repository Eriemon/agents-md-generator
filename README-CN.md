<p align="center">
  <a href="README.md">English</a>
  <span>&nbsp;|&nbsp;</span>
  <a href="README-CN.md"><strong>中文</strong></a>
</p>

<p align="center">
  <img src="docs/assets/hero.svg" alt="AGENTS.md Generator" width="100%">
</p>

<p align="center">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-1f6feb"></a>
  <a href="pyproject.toml"><img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-2f81f7"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-v0.9.7-7c3aed">
  <a href="SKILL.md"><img alt="Agent Skill" src="https://img.shields.io/badge/agent-skill-16a34a"></a>
  <a href="references/script-guide.md"><img alt="Target" src="https://img.shields.io/badge/target-AGENTS.md-f59e0b"></a>
</p>

<h1 align="center">AGENTS.md Generator</h1>

<p align="center">
  面向 Codex 的 AGENTS.md 生成、修复与验证 Skill。
</p>

AGENTS.md Generator 用来帮助编程 Agent 根据仓库事实生成可靠的治理文件，而不是凭记忆拼接规则。它把触发元数据、分组式设计访谈、确定性 Python 脚本、文档治理辅助、目录治理门禁和验证链组合在一起，让 Agent 能从仓库事实稳定走到可信的 `AGENTS.md` 输出。

这个仓库首先是一个 **Agent Skill Package**。Python 脚本是确定性执行层，但核心产品其实是 Agent 可加载、可遵循的 skill 工作流。

## 它解决什么问题

很多 Agent 规则文件一开始写得很认真，但很快就会和真实仓库脱节：命令不再存在，路径已经变化，本地约束被写在多个地方还互相冲突。AGENTS.md Generator 强制 Agent 走一条更稳的路径：

- 先检查仓库事实
- 只询问缺失的人类策略
- 保持 root 和 scoped `AGENTS.md` 小而聚焦
- 让 docs、directory、release 治理尽量走脚本化流程
- 在声明完成前，验证元数据、路径、契约和回复语言规则是否一致

## 核心能力

- 为 Codex 类编程 Agent 生成 root 和 scoped `AGENTS.md`。
- 提供可恢复状态的分组式设计访谈与确认门禁。
- 为 root `AGENTS.md` 版本失配的旧工作区提供 takeover 流程。
- 提取命令、文档、CI 线索、作用域和治理信号等仓库事实。
- 为 skill 项目和 engineering 项目生成 strong-control profile。
- 提供 handoff、experience、development、install、git-manager 等 docs 治理辅助。
- 通过 `manage_dirs.py` 执行目录治理审查与结构门禁。
- 在需要时生成 `CLAUDE.md` 与 `GEMINI.md` 兼容 shim。
- 提供验证、审计、自动 review 治理、skill-effectiveness eval 和 aggregate confidence gate，用于发布前把关。

## v0.9.7 重点更新

- 更新 `scripts/design_remote_gate.py`，让 remote-ssh 相关检查同时兼容 `assets/defaults.json` 和旧版 `config/defaults.json` 配置布局。
- 加固 `scripts/source_governance.py`，当 Python 语法解析或 tokenize 失败时返回结构化违规信息，而不是让审计链直接崩掉。
- 扩展 `scripts/manage_docs_sync_verify.py`，新增 Control Profile 版本一致性检查，并可自动修正不匹配的版本行。
- 调整 `scripts/evaluate_skill.py`，让 `erie-remote-ssh` 在 release 校验时能使用预期的兼容验证环境。

## Skill 架构

<p align="center">
  <img src="docs/assets/architecture-cn.svg" alt="AGENTS.md Generator Skill 架构" width="100%">
</p>

## 工作流

<p align="center">
  <img src="docs/assets/workflow-cn.svg" alt="AGENTS.md Generator 工作流" width="100%">
</p>

## 典型使用路径

1. 根文件健康检查：
   对包含 `计划`、`规划`、`准备` 的工作区触发请求，先检查 root `AGENTS.md` 是否健康，健康就只报告通过。
2. 显式 AGENTS 更新：
   启动分组式设计访谈，补足缺失策略，渲染 root/scoped 文件，再执行验证。
3. 旧工作区接管：
   对 root 版本失配的已落地工作区进入 takeover，尽量少问身份信息，但仍完整确认 structured directory contract。
4. 发布前验证：
   用 `quick_validate.py`、`audit_skill.py`、`verify_agents.py`、`evaluate_skill.py` 以及 review/eval 门禁组成完整校验链。

## 仓库结构

| 路径 | 作用 |
| --- | --- |
| `SKILL.md` | 面向 Agent 的触发、流程、约束和验证规则。 |
| `agents/openai.yaml` | 宿主 UI 使用的 skill 元数据。 |
| `scripts/` | 检查、访谈、渲染、文档治理、目录治理、验证、审计和评估脚本。 |
| `assets/templates/` | root/scoped `AGENTS.md` 模板与 evolution 相关模板。 |
| `evals/` | 供治理脚本使用的仓库内 skill-effectiveness 用例与可安全发布的评估数据。 |
| `references/` | 脚本指南、审查清单、问题库、能力覆盖说明和 AGENTS 指南。 |
| `docs/assets/` | 本对 README 使用的 hero、workflow 和 architecture 图。 |

## 安装

直接告诉你的AI让他安装 https://github.com/Eriemon/agents-md-generator

手动安装方式：

```powershell
git clone https://github.com/Eriemon/agents-md-generator.git
cd .\agents-md-generator
python -m pip install -e .
```

如果你在 Codex 或其他支持 skill 的宿主里使用它，把仓库放进 skill 搜索路径后重启宿主即可。

## 快速开始

只读检查与作用域发现：

```powershell
python scripts/inspect_project.py <project>
python scripts/detect_scopes.py <project>
python scripts/extract_commands.py <project>
python scripts/extract_context.py <project>
```

分组式设计访谈与 profile 写入：

```powershell
python scripts/collect_design_profile.py <project> --start
python scripts/collect_design_profile.py <project> --answer-file partial.json
python scripts/collect_design_profile.py <project> --answers answers.json --write
```

渲染与验证：

```powershell
python scripts/render_agents.py <project> --profile <project>/.agents/agents-control.json
python scripts/verify_agents.py <project>
python scripts/manage_docs.py verify <project>
```

Codex token 用量审查：

```powershell
python scripts/codex_token_usage_review.py --hours 48
python scripts/codex_token_usage_review.py --hours 48 --json
python scripts/codex_token_usage_review.py --hours 48 --verbose
```

Skill 发布前验证：

```powershell
python scripts/quick_validate.py .
python scripts/audit_skill.py .
python scripts/evaluate_skill.py . <project>
```

源码仓库说明：

- 当前源码仓库不再跟踪 repo-local `tests/`。
- installable release 会显式拒绝 `tests/`、`smoke*`、`reports/` 与缓存类产物进入打包结果。

治理敏感 release 的进阶检查：

```powershell
python scripts/review_governance.py <project> --base <sha> --head HEAD --skill-dir . --mode all
python scripts/run_confidence_gate.py <project> --review-base <sha> --external-skill-dir <healthy-skill-dir>
```

兼容 shim 仍然是显式选择：

```powershell
python scripts/create_agent_shims.py <project>
```

## 边界

AGENTS.md Generator 的职责刻意收得很窄：

- 它生成和审查的是 Agent 治理文件，不替代通用项目文档。
- 从仓库中发现的命令只是候选命令，只有真正执行过才算已验证。
- 它会保留 managed generated blocks 之外的手写内容。
- 可维护性和脚本治理细节应尽量放在配置驱动的策略里，而不是在文案里重复堆叠。
- 它不应该把密钥、私有基础设施、生成缓存或机器专属绝对路径写进输出。

## 机构说明

Jiyuan Liu 和 He Li 隶属于东南大学电子科学与工程学院。
两位作者所在团队为东南大学电子科学与工程学院异构智能与量子计算实验室（HIQC），相关工作面向异构智能、量子计算及相关计算系统研究。

## 联系方式

问题、合作或学术使用，请联系：[erie@seu.edu.cn](mailto:erie@seu.edu.cn)。

## 引用

如果这个 skill 对你的研究、教学或工程流程有帮助，请引用。规范引用元数据以 [CITATION.cff](CITATION.cff) 为准。

```bibtex
@software{liu_2026_agents_md_generator,
  author       = {Jiyuan Liu and He Li},
  title        = {{AGENTS.md Generator}: An Agent Skill for Coding-Agent Context Files},
  year         = {2026},
  version      = {0.9.7},
  date         = {2026-05-30},
  url          = {https://github.com/Eriemon/agents-md-generator},
  license      = {Apache-2.0},
  note         = {Agent skill package for generating and verifying AGENTS.md files}
}
```

## 许可证

Apache License 2.0，详见 [LICENSE](LICENSE)。
