# 安装与版本同步

## 同步边界

- 同一台电脑：通过软链接让 Codex、Claude、Gemini 等 AI 共用同一份仓库克隆，源目录更新后立即生效
- 不同电脑：每台电脑首次安装时注册本地每周更新任务，此后由该电脑每周从 GitHub 拉取新版
- 云端 AI：只有平台支持从 GitHub 动态读取或重新导入时才能同步，否则需要平台侧重新安装

GitHub 不能主动推送到用户电脑。这里的“自动更新”由安装时注册的本地计划任务实现，因此每台电脑都必须至少完成一次新版安装。

## 推荐安装结构

1. 把 GitHub 仓库克隆到一个长期稳定的源目录
2. 在源目录运行 `python3 scripts/sync_installations.py`
3. 脚本把以下默认路径链接到源目录：
   - Codex：`~/.codex/skills/category-opportunity-report`
   - Claude：`~/.claude/skills/category-opportunity-report`
   - Gemini：`~/.gemini/skills/category-opportunity-report`
4. 安装器默认注册每周日 03:00 的更新任务；更新成功后，所有链接无需重建

如果目标路径已有复制版，脚本默认停止，避免覆盖。确认迁移时使用 `--replace`，旧目录会改名为带时间戳的备份，不直接删除。

## 常用命令

仅查看将发生什么：

```bash
python3 scripts/sync_installations.py --dry-run
```

建立默认的三类 AI 链接：

```bash
python3 scripts/sync_installations.py --replace
```

不注册自动更新：

```bash
python3 scripts/sync_installations.py --replace --no-auto-update
```

只同步指定 AI 或自定义路径：

```bash
python3 scripts/sync_installations.py --ai codex --ai claude --replace
python3 scripts/sync_installations.py --target /absolute/path/to/another-ai/skills/category-opportunity-report --replace
```

## 发布规则

1. 只在源目录修改文件
2. 运行 Skill 校验和同步脚本的 `--dry-run`
3. 提交并推送 GitHub
4. 已完成新版安装的电脑会在每周任务运行后获得新版
5. 更新仅允许快进合并；存在本地改动、分支异常或网络失败时保留旧版本
