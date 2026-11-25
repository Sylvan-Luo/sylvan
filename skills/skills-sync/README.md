# skills-sync

把工具箱里的 skill 发布到 GitHub 仓库 [Sylvan-Luo/sylvan](https://github.com/Sylvan-Luo/sylvan)（公开仓库），并保持同步。

## 用法

```
skills-sync            # = push：整理 → 脱敏 → 隐私扫描 → 提交 → 推送
skills-sync check      # 只整理和扫描，看会改哪些文件，不推送
skills-sync list       # 会发布哪些 skill
skills-sync status     # 上次同步结果（~/.local/state/skills-sync/last.json）
```

何时同步：没有自动推送（往公开仓库发东西要有人有意识地做）。按工具箱规矩，每次新建/修改工具并在 `~/tools` 提交后，
由做这件事的会话运行一次 `skills-sync`；只改了 `~/.claude/skills/*/SKILL.md` 也一样。

## 怎么整理的
- 发布哪些：`~/tools/` 下的工具目录 ∪ `~/.claude/skills/` 下的技能目录（不含 `synced/`（Anthropic 自带）和 `_template`），
  去掉 `exclude.txt` 里的名字。
- 每个名字合并成仓库里的 `skills/<名字>/`：工具代码只取 `~/tools` 里 **git 已跟踪** 的文件；`SKILL.md` 取 `~/.claude/skills/<名字>/`。
- 首页 `README.md` 由 `README.tpl.md` 生成，目录表取每个 SKILL.md 的 `description`。仓库级 `.gitignore` 在 `repo-files/`。
- 本地工作副本：`~/.local/share/skills-sync/repo`（每次同步前重置成远端最新，不要在里面手改）。

## 隐私
- 脱敏表 `~/.config/skills-sync/scrub.tsv`（只在本机，不进任何仓库）：每行「原文<TAB>替换成」，长的先换。
  新工具里出现新的私人信息（好友名、学号、新电脑名……）就加一行。
- 脱敏后再扫描：Tailscale/局域网 IP、邮箱、`LAPTOP-`/`DESKTOP-` 电脑名、手机号、私钥、各类 token、`密码=…`，
  以及脱敏表里没换掉的原文。命中任何一条就不推送，并在 `status` 里列出位置。
- 单个文件超过 5 MB 不发布（大文件应在 `~/data`）。

## 依赖和前提
- 推送用部署密钥 `~/.ssh/github_sylvan`（只对 sylvan 这一个仓库有写权限），`~/.ssh/config` 里的别名 `github-sylvan`。
- 提交作者：Sylvan-Luo（GitHub noreply 邮箱），不用真实邮箱。

## 注意
- 仓库是公开的：发布前想清楚。不想公开的工具名写进 `exclude.txt`。
- 不要在 GitHub 网页上直接改文件——下次同步会覆盖。
