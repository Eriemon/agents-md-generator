# GitHub 关联技能发布合同

本合同把“技能源码、版本化 `dist/`、用户工作文件夹根目录的 `github/` checkout”视为三个可验证副本。它适用于本技能，也适用于以后开发的任何技能；开发者只需在 `.agents/agents-control.json` 登记一条映射。

## 绑定原则

| 项目 | 合同 |
| --- | --- |
| 仓库策略 | `existing-only`：只连接已经存在的远程仓库；不存在时停止，不自动创建 |
| checkout | `github/<skill-name>/`，必须位于当前工作文件夹内，并保留 `.git/` |
| 来源 | 先完成正常的版本化 `dist/<skill>-vX.Y.Z/` 发布和回执，再执行镜像 |
| 内容 | 镜像后的 checkout 清单必须与 dist 清单逐文件 SHA-256 一致 |
| 远程动作 | 工具不执行 commit、tag、push、GitHub Release 或远程仓库创建 |
| 确认 | 安装确认和远程发布确认是两个独立确认点 |

## 标准流程

1. `status`：确认 checkout、`origin`、分支和工作树状态。
2. `check`：确认源码与 dist 的公开文件合同、版本和内容白名单。
3. 完成普通 release/install 流程；只接受带 `RELEASE_RECEIPT.json` 的版本化 dist。
4. `mirror`：checkout 干净且映射一致时，删除旧的非 `.git` 内容并复制 dist 全部内容。
5. `plan`：生成 `docs/git_manager/github-publish-<skill>-vX.Y.Z.json`，列出差异、清单和人工动作。
6. 获得独立的远程发布确认后，由维护者手动执行 Git/GitHub 写操作。
7. `verify`：复核本地清单；它不能被解释成远程发布成功证明。

## 失败即停止

- 映射缺失、URL 不匹配、分支不匹配或 checkout 是 dirty 状态。
- dist 缺少公开文件、版本元数据漂移、README 使用远程图片或 SVG。
- 任一符号链接、路径越界、清单差异或收据不一致。

其他技能开发者遇到“技能要链接 GitHub 仓库”时，应先补映射并按同一流程操作，不应在技能脚本中另写一套隐式发布逻辑。
