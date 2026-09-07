# 启动时版本同步

每个新任务第一次触发本 Skill 时检查一次，同一任务内不重复检查。

运行：

```bash
python3 "<SKILL_ROOT>/scripts/sync_skill_release.py" --apply --json
```

更新器只接受固定仓库 `Panzi1128/category-opportunity-report` 的稳定 SemVer Release、精确命名的完整 ZIP 和发布的 SHA-256。校验通过后再验证 Skill 身份与包结构，并以备份加原子替换的方式更新。

状态处理：

- `up_to_date`：静默继续
- `updated`：说明已从旧版更新到新版，重新完整读取新版 `SKILL.md` 后继续
- `check_unavailable`：暂时无法联网检查，使用当前版继续
- `update_failed`：保留旧版继续；不要 reset、强制覆盖或反复索权

官方 Git checkout 只在工作区干净、远端精确匹配固定仓库时，快进到最新稳定 Release 标签。符号链接只解析到真实官方 checkout，不整体替换链接目标。

检测到旧版安装遗留的 Skill 根目录软链接时，即使版本号相同，也要下载并校验当前稳定 Release，把链接本身备份后迁移为独立完整目录；不得删除或改写链接指向的源仓库。

没有 Python 或不能持久安装时，使用等价工具完成：稳定版本比较、精确资产下载、SHA-256 校验、完整目录校验、备份和整体替换。只能临时读取时说明“本次使用新版，未持久安装”。

固定最新发布页：<https://github.com/Panzi1128/category-opportunity-report/releases/latest>
