# Sylvan 的 Claude Skills

我和 Claude Code 一起做出来、日常在用的 skill 和小工具，共 6 个。
每个目录 `skills/<名字>/` 里：`SKILL.md` 是给 Claude 看的技能说明（什么时候用、怎么用），其余是这个 skill 用到的脚本、模板和说明文档。

> 本仓库由 `skills-sync` 从我本机的工具箱自动同步（最近一次：2026-11-26），请不要直接在 GitHub 上改——改了会被下次同步覆盖。
> 发布前会自动把用户名、电脑名、IP、邮箱等换成 `<WinUser>`、`<LAPTOP>` 之类的占位符。

## 目录

| 名字 | 类型 | 做什么 / 什么时候用 |
|---|---|---|
| [latex-pdf](skills/latex-pdf/) | skill + 工具 | 生成排版精美的 PDF（中文为主）：把 Markdown / Word / HTML / LaTeX 先转 LaTeX、套用户认可的模板（深蓝封面横幅、彩色定义/结论/原话/易错框、两栏选择题），再用 XeLaTeX 编译。用户说“做成 PDF”“生成 PDF”“导出好看的 PDF”“排版成讲义/笔记/复习资料/报告”“用 LaTeX 排一下”“套那个模板”时用。 |
| [pc-remote](skills/pc-remote/) | skill + 工具 | 远程操作用户自己的 Windows 电脑（也管笔记本合盖睡着、连不上时怎么等它回来再接着做）：截屏看屏幕、点鼠标/敲键盘（pcctl），控制笔记本上已登录教学网/高顿等网站的专用 Chrome、读网页/执行 JS/网页截图（pcweb），在 GPU 台式机上跑 PowerShell（gpups）。用户说“看看我屏幕”“帮我点一下”“在我电脑浏览器里打开/读一下 XX 网页”“在台式机上跑”时用。 |
| [pku-homework](skills/pku-homework/) | skill + 工具 | 北大教学网（course.pku.edu.cn / Blackboard）作业：查有哪些作业没交、什么时候截止，下载作业要求和附件，帮用户做作业，并在用户同意后提交到教学网、核对是否交上。用户说“教学网”“作业”“有什么作业没交”“帮我做/写/完成 XX 课的作业”“把作业交了/提交作业”“作业截止”时用。 |
| [skills-sync](skills/skills-sync/) | skill + 工具 | 把用户自己做的 skill / 工具同步到 GitHub 公开仓库 Sylvan-Luo/sylvan（自动脱敏+隐私扫描）。用户说“传到 GitHub”“同步 skill 仓库”“GitHub 上的 skill 更新一下”“skill 仓库”时用；新建或修改任何工具/skill 后也要确认它已同步。 |
| [toolbox](skills/toolbox/) | skill | 用户的工具箱总管。用户要“做一个工具 / 脚本 / 模板 / 自动化”、改进或修复已有工具、问“有哪些工具”、或者要做的事可能已经有现成工具时，先读这个。目录在 ~/tools，登记表 ~/tools/README.md。 |
| [wechat](skills/wechat/) | skill + 工具 | 用户的微信（Windows 笔记本上的微信 4.x）：看谁私聊了我、读某个好友的最近消息、给某个好友发/回微信，以及微信私聊提醒（会话台网页右上角）不工作时排查。用户说“微信”“谁给我发消息了”“给 X 发微信/回复 X”“读一下 X 的消息”“微信提醒没反应”时用。群聊一律不发。 |

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
