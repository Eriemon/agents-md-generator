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
  <img alt="Version" src="https://img.shields.io/badge/version-v2.0.3-7c3aed">
  <a href="SKILL.md"><img alt="Agent Skill" src="https://img.shields.io/badge/agent-skill-16a34a"></a>
  <a href="references/script-guide.md"><img alt="Target" src="https://img.shields.io/badge/target-AGENTS.md-f59e0b"></a>
</p>

<h1 align="center">AGENTS.md Generator</h1>

<p align="center">
  面向 Codex 的 AGENTS.md 生成、修复与验证 Skill。
</p>

<p align="center">
  最新版本：<strong>v2.0.3</strong> · 发布日期：<strong>2026-07-21</strong>
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
- 提供 handoff、memory、development、install、git-manager 等 docs 治理辅助。
- 提供由 JSON source、SQLite FTS 索引和只读查询 CLI 组成的渐进披露命令注册表。
- 通过 `scripts/python/dirs/manage_dirs.py` 执行目录治理审查与结构门禁。
- 在需要时生成 `CLAUDE.md` 与 `GEMINI.md` 兼容 shim。
- 提供验证、审计、自动 review 治理、skill-effectiveness eval 和 aggregate confidence gate，用于发布前把关。

## v2.0.3 重点更新

v2.0.3 收紧了首个公开 v2 版本中仍然耦合的三类边界：已安装技能身份与运行能力、可编辑注册源与生成索引、当前工作区与外部文件系统目标。这个版本保持现有公开 CLI 表面不变，同时让失败诊断更精确，并降低生成治理规则被意外弱化的风险。

### RemoteSSH 能力发现

- 当 `erie-remote-ssh` 的技能目录和根 `SKILL.md` 存在时，就确认技能已经安装；CLI 与设置发现改为独立能力，不再反向改变安装判定。
- 优先使用当前 `scripts/python/runtime/remote_ssh.py` 入口，并把 `scripts/remote_ssh.py` 保留为旧版已安装副本的兼容回退。
- 已安装但没有受支持 CLI 时返回退出码 127 的运行能力错误，不再错误地引导用户重新安装技能。

### 自描述注册表布局

- 将注册表 metadata、治理配置和 JSON Schema 分别迁移到 `metadata/`、`governance/` 与 `schemas/`；`config/registry/` 根目录现在只保留生成的 `registry.sqlite3` 和按职责划分的子目录。
- 在注册表根目录下发现且只允许一个有效 manifest；缺失、重复、位于根级或越过目录边界的声明都会失败关闭，不再依赖硬编码的 `manifest.json` 路径。
- 可选文档治理初始化改为使用 manifest 声明的文档角色和 schema 路径。文档注册仍然只能显式启用，不会因为基础设施存在就自动创建注册状态。

### 受管工作区边界

- 每个生成的受管根必须且只能包含一条 `Workspace boundary`：普通修改仅允许发生在当前工作文件夹或已验证的远程服务器工作文件夹内。
- 外部读取必须必要且无副作用；外部修改前必须披露规范化目标、动作、范围、风险、替代方案和恢复限制，然后分别取得“原则上允许例外”和“批准精确动作”两次独立确认。
- 验证器会拒绝缺失、重复、弱化、笼统授权、紧急绕过或只完成第一次确认的变体；目标或范围发生变化后，两次确认都会失效。

### 兼容、迁移与验证

- 现有公开命令入口继续受支持。直接读取旧版注册表根级 JSON 路径的集成需要改用 manifest/角色布局或注册表辅助函数。
- v2.0.3 之前生成的受管根应使用已安装的 v2.0.3 生成器刷新，使新的工作区边界能够被渲染和验证。
- 公开镜像对最终安装包执行 quick skill validation、无缓存 Python AST 解析、注册表一致性检查、聚焦的 RemoteSSH/注册表/工作区边界场景、发布内容策略检查和脱敏包检查。规范源码仓库的单元测试不存放在本公开镜像中，也不会把上游收据写成本地重跑结果。
- 下载资产排除 tests、smoke 运行、reports、缓存、嵌套 `dist/`、本地认证材料、凭据、私钥和机器专属绝对路径。仓库保留已批准的公开署名，下载资产中的联系邮箱替换为 `<REDACTED_EMAIL>`。

## v2.0.1 重点更新

v2.0.1 是首个公开 v2 版本，专门优化了本 skill 与 Codex 中 [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol) 的配合方式：压缩始终加载的指令面，把详细操作知识转移到确定性的按需查询，并让执行证据更容易复核。这些是架构级效率优化；项目不会声明未经实际测量的耗时或 token 成本提升百分比。

### 更小的 Agent 上下文，更丰富的按需 runtime

- `SKILL.md` 从 44,796 字节、202 行压缩到 12,683 字节、119 行，主要 Agent 指令文件按字节减少 71.7%。
- 详细命令语法迁移到 `config/registry/`，由版本化 JSON source、schema、manifest 和 SQLite FTS 索引共同管理。`query_registry.py ask` 只检索当前任务需要的指令，且绝不会执行查询结果中的命令。
- 明确说明取舍：确定性 Python 模块从 89 个增加到 99 个，因为实现与验证细节是从主提示中迁移到工具层，而不是被直接删除。

### Runtime 与治理架构

- 用面向职责的公开模块替换 26 个旧下划线内部模块及其分解说明，覆盖项目发现、profile 组装、持久记忆、release 策略、渲染、路由合同以及 policy/release eval。
- 新增一等 codebase-memory 集成，在受治理写入前显式检查 full index、architecture analysis、持久化状态和 live/disk 数量一致性。
- 新增持久记忆存储和有界检索视图，同时保留 handoff 与长期记忆合同，并继续拒绝机器本地原始路径。
- 新增可选文档注册，包含 catalog、knowledge、interface、重复项复核和 migration 记录。该能力仍为显式启用：用户没有明确要求文档注册或迁移时，不创建任何注册状态。
- 强化源码治理、内容密度、语义 review 证据、release 打包、脱敏、来源收据以及 command/root/routing 合同评估。

### 兼容与迁移

- 现有公开 CLI 入口继续作为受支持接口；内部模块路径不属于兼容合同。适用时，兼容包装器会把旧公开入口路由到新的职责模块。
- 将 `source_file_limits.max_lines` 和 `source_governance.max_lines` 迁移为基于字节的 `max_bytes`；v2 会拒绝已退役的行数配置字段。
- 将已弃用的 confidence gate 参数 `--skip-missing-eval-runner` 和 `--require-eval-runner` 替换为 `--eval-runner-policy optional` 与 `--eval-runner-policy required`。
- evolution 与 experience 子系统继续保持退役；`CLAUDE.md` 和 `GEMINI.md` 兼容 shim 仍然只能显式启用。

### 发布安全

- 从 v1.4.6 到 v2.0.1 的受管 payload 对比为：新增 50 个文件、更新 52 个文件、淘汰 26 个路径、保持不变 38 个文件；公开发布收据随后重新生成。
- 可安装资产继续排除 repo-local tests、smoke 运行、reports、缓存、嵌套 `dist/`、本地认证文件、凭据、私钥和机器专属绝对路径。
- 经明确批准的作者/联系邮箱继续公开用于署名；未授权联系方式和其他敏感信息仍会被阻止或脱敏。

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
| `scripts/python/` | 检查、访谈、渲染、文档治理、目录治理、release 安装、验证、审计和评估脚本。 |
| `config/registry/` | 按职责划分的 JSON source 与 schema 子目录，以及位于注册表根目录的生成 SQLite FTS 索引。 |
| `assets/templates/` | 当前 release 流程使用的 root/scoped `AGENTS.md` 模板。 |
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
python scripts/python/detect/inspect_project.py <project>
python scripts/python/detect/detect_scopes.py <project>
python scripts/python/detect/extract_commands.py <project>
python scripts/python/detect/extract_context.py <project>
```

分组式设计访谈与 profile 写入：

```powershell
python scripts/python/design/collect_design_profile.py <project> --start
python scripts/python/design/collect_design_profile.py <project> --answer-file partial.json
python scripts/python/design/collect_design_profile.py <project> --answers answers.json --write
```

渲染与验证：

```powershell
python scripts/python/render/render_agents.py <project> --profile <project>/.agents/agents-control.json
python scripts/python/verify/verify_agents.py <project>
python scripts/python/docs/manage_docs.py verify <project>
```

按需查询详细操作说明：

```powershell
python scripts/python/registry/query_registry.py ask "verify" --limit 3 --json
```

FTS 查询优先使用简短的命令或策略关键词；需要缩小结果时使用 `--category` 或 `--kind`，不要把多个无关词直接组合成一个查询。

Codex token 用量审查：

```powershell
python scripts/python/detect/codex_token_usage_review.py --hours 48
python scripts/python/detect/codex_token_usage_review.py --hours 48 --json
python scripts/python/detect/codex_token_usage_review.py --hours 48 --verbose
```

Skill 发布前验证：

```powershell
python scripts/python/verify/quick_validate.py .
python scripts/python/verify/run_skill_evals.py evals/evals.json
python scripts/python/verify/evaluate_skill.py . <project>
```

自身审计合同用于加入公开仓库文档之前的可安装 runtime，因为规范 runtime 有意只把 `SKILL.md` 作为根级说明：

```powershell
python scripts/python/verify/audit_skill.py <runtime-stage>
```

加入 `README.md`、`README-CN.md`、`LICENSE` 和 `CITATION.cff` 后，应使用 release package 检查与 release gate 验证最终 ZIP，而不是把公开镜像误当作规范 runtime 执行自身审计。

源码仓库说明：

- 当前源码仓库不再跟踪 repo-local `tests/`。
- installable release 会显式拒绝 `tests/`、`smoke*`、`reports/` 与缓存类产物进入打包结果。

治理敏感 release 的进阶检查：

```powershell
python scripts/python/verify/review_governance.py <project> --base <sha> --head HEAD --skill-dir . --mode all
python scripts/python/verify/run_confidence_gate.py <project> --review-base <sha> --external-skill-dir <healthy-skill-dir>
```

兼容 shim 仍然是显式选择：

```powershell
python scripts/python/render/create_agent_shims.py <project>
```

## 边界

AGENTS.md Generator 的职责刻意收得很窄：

- 它生成和审查的是 Agent 治理文件，不替代通用项目文档。
- 从仓库中发现的命令只是候选命令，只有真正执行过才算已验证。
- 它会保留 managed generated blocks 之外的手写内容。
- 可维护性和脚本治理细节应尽量放在配置驱动的策略里，而不是在文案里重复堆叠。
- 外部项目应调用已安装 runtime，例如 `python <codex-home>/skills/agents-md-generator/scripts/python/docs/manage_docs.py ...`，不要把本 skill 脚本复制到项目本地工具目录。
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
  version      = {2.0.3},
  date         = {2026-07-21},
  url          = {https://github.com/Eriemon/agents-md-generator},
  license      = {Apache-2.0},
  note         = {Agent skill package for generating and verifying AGENTS.md files}
}
```

## 许可证

Apache License 2.0，详见 [LICENSE](LICENSE)。
