---
name: skills-sync
description: 把用户自己做的 skill / 工具同步到 GitHub 公开仓库 Sylvan-Luo/sylvan（自动脱敏+隐私扫描）。用户说“传到 GitHub”“同步 skill 仓库”“GitHub 上的 skill 更新一下”“skill 仓库”时用；新建或修改任何工具/skill 后也要确认它已同步。
---

# skills-sync

- 不会自动推送：新建/修改工具或 SKILL.md 并在 `~/tools` 提交后，运行 `skills-sync`（整理→脱敏→扫描→提交→推送）。
- `skills-sync check` 先看会发布什么、隐私扫描是否通过；`skills-sync status` 看上次结果（失败原因、命中的位置）。
- 扫描没通过：改源文件，或把私人信息加进 `~/.config/skills-sync/scrub.tsv`（原文<TAB>占位符）再跑。
- 不想公开的工具：名字写进 `~/tools/skills-sync/exclude.txt`。
- 仓库：https://github.com/Sylvan-Luo/sylvan （不要在网页上直接改，会被覆盖）。详见 `~/tools/skills-sync/README.md`。
