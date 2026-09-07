# Category Opportunity Report Skill

把标准提需表转成跨国家、跨类目的机会分析与咨询风飞书文档。

## 安装

把以下内容发给支持本地 Skill、文件和终端能力的 AI：

> 请从 https://github.com/Panzi1128/category-opportunity-report/releases/latest 下载最新稳定 Release 中名为 `category-opportunity-report-v*.zip` 的文件，校验 Release 正文公布的 SHA-256，完整解压并保留 `category-opportunity-report` 文件夹，安装到当前宿主可识别的 Skill 目录。请确认 `VERSION`、`SKILL.md`、`agents/`、`scripts/` 和 `references/` 均可访问；无法持久安装时请说明限制，不要假装成功。

首次安装后，每个新任务第一次使用本 Skill 时会检查一次稳定 Release。更新失败不会覆盖当前版本，也不会阻塞业务分析。

## 安全边界

- 不创建系统后台计划任务
- 不把多个 AI 的 Skill 目录链接到同一代码源
- 只接受固定仓库、稳定 SemVer、精确命名的完整 ZIP 和发布的 SHA-256
- 更新前验证包结构和 Skill 身份，更新失败保留旧版
