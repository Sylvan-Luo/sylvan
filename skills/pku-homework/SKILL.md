---
name: pku-homework
description: 北大教学网（course.pku.edu.cn / Blackboard）作业：查有哪些作业没交、什么时候截止，下载作业要求和附件，帮用户做作业，并在用户同意后提交到教学网、核对是否交上。用户说“教学网”“作业”“有什么作业没交”“帮我做/写/完成 XX 课的作业”“把作业交了/提交作业”“作业截止”时用。
---

# pku-homework — 教学网作业：识别 → 完成 → 提交

命令 `hw`（~/.local/bin/hw → ~/tools/pku-homework/hw，细节见 ~/tools/pku-homework/README.md）。

## 流程（按顺序）
1. **识别**：`hw list --todo`（未交且未过期）。用户没指定哪项时，列出来让他挑；`hw show ID` 看要求、提交次数。
2. **取材料**：`hw get ID` → `~/data/tools/pku-homework/work/<课程>/<作业>/materials/`（说明.md、附件）。
   zip 解压到同级 `src/` 里做；读 readme（docx 用 docx 技能读）。命名要求里的姓名学号用 `hw me`。
3. **完成**：在工作目录里真正把作业做出来（写代码要实际跑通、跑测试；报告写成 PDF/docx 按要求；
   需要 GPU 训练用 `gpu` 台式机，见全局说明）。成品放 `submit/`，按作业要求命名/打包，不带数据集等多余文件。
   拿不准的题意、开放性选择（选题、风格），问用户。
4. **试填**：`hw submit ID -f submit/xxx.zip [--text …] [--comment …]`（默认 --dry，不提交），看 `shots/` 里的截图确认。
5. **请用户确认**：把“交到哪门课哪项作业、文件清单（大小）、文字内容、允许提交次数、截止时间”和成品要点给用户看，
   最好 `tsx push mac` 一份成品到他桌面让他过目。**用户明确说可以提交才执行**
   `hw submit ID -f … --confirm`；用户只想先存着就 `--draft`。
6. **核对**：命令会自动输出提交记录（状态 NeedsGrading、文件名）；照实告诉用户，截图路径一并给。

## 规矩
- 不经用户确认绝不 `--confirm`（很多作业只能交 1 次）。不碰在线测验。不替用户保存密码。
- `LOGIN` 报错 = 教学网掉线：请用户在专用 Chrome 窗口重新登录。`NOCHROME` = 先 `pcweb start`。
- 作业代写有学术诚信风险，用户自己决定怎么用；帮他把思路和关键点讲清楚，方便他看懂、能回答助教提问。
