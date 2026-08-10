# Contributing

感谢你改进 AGENTS.md Generator。贡献前请阅读 `SKILL.md`、`references/review-checklist.md` 和 `references/github-skill-release.md`。

## 开发约定

1. 先读取当前 handoff、AGENTS 和图谱状态，再冻结目标与范围。
2. 修改 Python 或脚本前，先通过 `readable-python-generator` 与 `readable-script-generator` 的过程门禁。
3. 保持可读的多行结构、语义变量名和有理由的注释；不要把代码压缩成单行。
4. 运行验证时遵循项目的远程 pytest 路由；测试目录只由 canonical TESTER 管理。
5. 技能根必须同步维护 `VERSION`、双语 README、许可证、安全、贡献、元数据和引用文件。

## GitHub 关联技能

若贡献涉及远程技能仓库，请在 `.agents/agents-control.json` 登记已有仓库映射，并按 `status → check → 正常 dist 发布/安装 → mirror → plan → 独立远程确认 → verify` 操作。工具只更新当前工作区 `github/` checkout，不创建远程仓库，也不代替维护者执行 push 或 Release。

## 提交前检查

- 双语 README 的插图是本地高分辨率 PNG，且没有 SVG、Mermaid 或远程图片。
- 发布目录与源码版本一致，并带有 `RELEASE_RECEIPT.json`。
- 变更说明、验证证据和剩余风险已写入 handoff。
