# AGENTS.md Generator：把仓库事实变成可验证的协作规则

![从仓库事实到可验证 AGENTS.md 的受管路径](assets/readme/hero-cn.png)

这不是一个“把说明文字写长”的模板。它检查真实工作文件夹，询问无法安全推断的策略，生成作用域清晰的 `AGENTS.md`，并把目录、远程、记忆、会话和发布证据留给下一次工作继续使用。

## 一句话理解

`仓库事实 + 已确认意图 → 分层 AGENTS.md + 可追溯治理证据`

## 它解决什么问题

| 场景 | 技能行为 | 交付结果 |
| --- | --- | --- |
| 根规则缺失 | 先判断项目类型，再按分组收集设计答案 | 可执行的根规则和作用域计划 |
| 已有 AGENTS.md | 只更新受管区块，保留人工文本 | 小而清晰的差异 |
| 规则过长 | 围绕决策、路径和门禁压缩 | 适合 Agent 执行的短根文件 |
| 需要远程验证 | 按配置解析任务路由并检查工作区 | 服务器、任务、工作区证据 |
| 会话中断 | 读取 handoff 并恢复精确步骤 | 可安全暂停和继续的状态 |
| 技能发布 | 审计、打包、回执和安装门禁 | `dist/<skill>-vX.Y.Z/RELEASE_RECEIPT.json` |
| 需要 GitHub 仓库 | 把完成的 dist 内容镜像到已有 `github/` checkout | 清单、计划和独立发布边界 |

## 功能子图

主图负责建立全局理解，下面四张子图分别展开真实工作内容：检查什么事实、如何锁定策略、规则写到哪里，以及交接为什么可信。

![项目事实：仓库目录、知识图谱、语言构成、命令面和作用域候选](assets/readme/project-facts-cn.png)

![设计画像：策略回答、关键问题、作用域边界和决策矩阵](assets/readme/design-profile-cn.png)

![规则生成：继承与局部覆盖、受管区块和最小差异](assets/readme/rule-rendering-cn.png)

![证据守门：新鲜度、路径安全、记忆门禁、验证报告和失败即阻断](assets/readme/evidence-guard-cn.png)

## 一个完整请求

```text
为仓库生成根 AGENTS.md，控制在 20 KB 内；把 rtl/ 下的 FPGA 规则放在作用域文件；
在指定远程服务器验证；最后准备发布包，但不要安装。
```

技能会把请求拆成明确答案，检查工作区是否已经有真实内容，只在对齐后写入，并如实报告实际运行过的门禁。它不会凭空编造服务器，不会把本地参考资料静默复制进去，也不会替你执行远程发布。

## 开发与验证入口

```powershell
python skills/agents-md-generator/scripts/python/design/collect_design_profile.py --project .
python skills/agents-md-generator/scripts/python/verify/quick_validate.py skills/agents-md-generator
python skills/agents-md-generator/scripts/python/verify/audit_skill.py skills/agents-md-generator
```

正式安装只接受带回执的版本化目录，禁止从源码目录直接安装：

```powershell
python skills/agents-md-generator/scripts/python/release/install_skill.py `
  dist/agents-md-generator-v2.1.0 --target skip
```

## 链接已有 GitHub 仓库

当另一个技能也需要链接 GitHub 仓库时，先在 `.agents/agents-control.json` 登记映射，再走同一条流程：

```text
status → check → 正常 dist 发布/安装 → mirror → plan →
独立远程发布确认 → 人工 git/gh 操作 → verify
```

```powershell
python skills/agents-md-generator/scripts/python/release/github_skill_release.py `
  check --project . --skill-dir skills/agents-md-generator
python skills/agents-md-generator/scripts/python/release/github_skill_release.py `
  mirror --project . --skill-dir skills/agents-md-generator `
  --release-dir dist/agents-md-generator-v2.1.0
```

镜像工具保留 `.git`，用 dist 内容完整替换 checkout 的其他内容，再比较逐文件 SHA-256。它不会创建远程仓库，也不会执行 `commit`、`push`、`tag` 或 GitHub Release；安装确认和远程发布确认始终分开。

## 公开技能包门禁

每个受管理技能都必须有 `VERSION`、`LICENSE`、`README.md`、`README-CN.md`、`SECURITY.md`、`pyproject.toml`、`CONTRIBUTING.md`、`CITATION.cff` 和 `SKILL.md`。双语 README 必须使用本地光栅 PNG 插图；SVG、Mermaid、远程图片和占位元数据会在打包前被拒绝。

当用户用本技能开发或更新其他技能，并提出 README 插图需求时，也必须遵守同一视觉合同：使用 Image2/ImageGen 生成原创光栅图；主图采用适合 README 的横向 16:9 功能总览；再为核心能力提供风格统一的细节子图；图中应表达真实输入、决策、输出、门禁或数据关系。装饰性截图、流水账步骤图、SVG、Mermaid 和远程图片均不合格。

## 核心取舍

- 事实优先：先检查目录，再提问题。
- 写入收敛：受管区块由生成器维护，人工说明保持人工所有权。
- 证据优先：回执明确记录来源、发布包和实际执行的检查。
- 边界分离：本地镜像、安装和远程发布各自需要独立确认。

## 许可证与引用

本技能使用 Apache-2.0。请阅读 [LICENSE](LICENSE)、[CONTRIBUTING.md](CONTRIBUTING.md)、[SECURITY.md](SECURITY.md) 和 [CITATION.cff](CITATION.cff)。
