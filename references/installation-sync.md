# 安装与版本发布

## 更新边界

- 每个 AI：独立保存完整 Skill 目录，不共享软链接
- 每个新任务：第一次触发本 Skill 时检查一次稳定 Release，同一任务不重复检查
- 不同电脑：在实际使用该 Skill 时分别检查更新，不需要后台计划任务
- 云端 AI：只有平台支持持久安装和写入时才能更新；否则本次临时读取新版并说明限制

“自动更新”指使用时检查，不是 GitHub 主动推送，也不是系统后台常驻任务。首次安装仍需用户或宿主完成一次。

## 安装要求

1. 从固定仓库的最新稳定 Release 下载精确命名的 ZIP
2. 完整保留顶层 `category-opportunity-report` 文件夹
3. 安装到宿主可识别的 Skill 目录
4. 确认 `VERSION`、`SKILL.md`、`agents/`、`scripts/` 和 `references/` 完整存在

固定发布页：<https://github.com/Panzi1128/category-opportunity-report/releases/latest>

## 自更新合同

标准命令：

```bash
python3 "<SKILL_ROOT>/scripts/sync_skill_release.py" --apply --json
```

- 只接受稳定三段式 SemVer
- 只接受固定仓库、固定命名的 Release ZIP
- 下载前后校验发布的 SHA-256
- 拒绝压缩包中的符号链接，验证 Skill 身份和完整目录结构
- 普通安装目录采用同目录暂存、备份和原子替换
- 官方 Git checkout 仅在工作区干净、远端匹配时快进到稳定 Release 标签
- 任一步失败都保留旧版，不 reset、不强制覆盖

## 发布规则

1. 只在源目录修改文件
2. 更新 `VERSION` 并运行 Skill 校验
3. 运行 `scripts/package_release.py` 生成完整 ZIP 和 SHA-256
4. 提交、打稳定版本标签并发布同名 Release 资产
5. 在 Release 正文写入 `category-opportunity-report-sha256: <64位摘要>`
6. 用已安装旧版执行一次更新测试，再公开安装链接
