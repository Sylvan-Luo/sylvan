# Sylvan 的 Claude Skills

我和 Claude Code 一起做出来、日常在用的 skill 和小工具，共 {{COUNT}} 个。
每个目录 `skills/<名字>/` 里：`SKILL.md` 是给 Claude 看的技能说明（什么时候用、怎么用），其余是这个 skill 用到的脚本、模板和说明文档。

> 本仓库由 `skills-sync` 从我本机的工具箱自动同步（最近一次：{{DATE}}），请不要直接在 GitHub 上改——改了会被下次同步覆盖。
> 发布前会自动把用户名、电脑名、IP、邮箱等换成 `<WinUser>`、`<LAPTOP>` 之类的占位符。

## 目录

| 名字 | 类型 | 做什么 / 什么时候用 |
|---|---|---|
{{TABLE}}

## 怎么用到自己的 Claude Code 里

```bash
git clone https://github.com/Sylvan-Luo/sylvan.git ~/sylvan-skills
# 只装技能说明（Claude 会在相关任务里自动调用）：
ln -s ~/sylvan-skills/skills/<名字> ~/.claude/skills/<名字>
```

大多数 skill 原本运行在「一台 Mac mini + 用户自己的 Windows 电脑」的环境里（经 ClaudeHub 的 `tsx` 在用户电脑上执行命令），
脚本里的路径默认是 `~/tools/<名字>/`。拿去用时请先读各目录下的 `README.md`，按自己的环境改路径和前提条件。

## 维护方式

- 本机：代码在 `~/tools/<名字>/`（git 仓库），技能说明在 `~/.claude/skills/<名字>/SKILL.md`，登记表 `~/tools/README.md`。
- 每次新建或修改 skill、在工具箱提交后，运行 `skills-sync` 同步到这里。
- 同步时会做隐私扫描（IP、邮箱、电脑名、手机号、密钥、密码等），有命中就拒绝推送。
