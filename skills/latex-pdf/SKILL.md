---
name: latex-pdf
description: 生成排版精美的 PDF（中文为主）：把 Markdown / Word / HTML / LaTeX 先转 LaTeX、套用户认可的模板（深蓝封面横幅、彩色定义/结论/原话/易错框、两栏选择题），再用 XeLaTeX 编译。用户说“做成 PDF”“生成 PDF”“导出好看的 PDF”“排版成讲义/笔记/复习资料/报告”“用 LaTeX 排一下”“套那个模板”时用。
---

# latex-pdf：Markdown → LaTeX → 模板 → PDF

```bash
latex-pdf 笔记.md                         # 文章版：首页横幅，# = 节 → 笔记.pdf
latex-pdf 笔记.md --book --toc --chapter-name 讲   # 书籍版：整页封面、目录、# = 第 N 讲
latex-pdf 笔记.md --tex -o out.pdf        # 同时留下 .tex
latex-pdf 正文.tex / 报告.docx            # LaTeX 片段或完整文档、Word、HTML 也行
latex-pdf --demo -o demo.pdf              # 全部样式示例（examples/demo.md 是写法范本）
```

做内容时**直接按下面的写法写 Markdown**，再调用命令；写不准时先看 `~/tools/latex-pdf/examples/demo.md`。

- YAML 头：`title` `eyebrow`（标题上小字）`subtitle` `author` `date` `book: true` `toc: true`
  `chapter-name: 讲` `theme: navy|teal|wine|forest|ink|purple|orange` `header-title`
  `info:`（封面键值框，列表 `- 键: 值`）`cover-extra: |`（书籍封面下方内容）`zihao: 5|-4`
- 框：`::: def`（第一行 `### 名称` 作标题，蓝框编号「定义 2.1」）、`thm`/`conclusion`、`example`、
  `key`（浅黄公式）、`warn`（易错）、`intuition`（直觉）、`tip`/`exam`（要点/考场写法）、`note`（注）、
  `said`/`quote`（楷体原话，`——` 开头的段落是署名）、`guide`（绿框，里面用 `键\n: 值` 定义列表）、
  `info`、`card`（白底卡片）、`answer`（答案黄条）、`choices`（列表 → (A)(B)… 两栏，`cols=1/4`）、`newpage`。
  属性：`{.def title="名称" label="公理"}`、`.unnumbered`。`> [!TIP]`/`[!WARNING]`/`[!NOTE]` 也行。
- 行内：`[必会]{.tag}`（必会/重点红、常考洋红、了解灰；`.blue` 等指定色）、`[L2 p.9]{.src}` 出处、
  `[72 ppi]{.hl}` 蓝粗、`==高亮==`、`[字]{.kai}` 楷体、`[ ]{.blank}` 填空线。
- 书籍版分部：`# 标题 {.part}`（`.restart` 章号从 1 重新开始）；不进目录的标题 `{.unnumbered .unlisted}`。
- 公式 `$…$` `$$…$$`，图片 `![说明](相对路径){width=60%}`，表格、脚注、代码块照常。

## 注意

- 只在 mini 上运行（pandoc 在 ~/.local/bin，TinyTeX 在 ~/Library/TinyTeX）。用户电脑上的文件先
  `tsx pull mac "…"`，生成后 `tsx push mac x.pdf -d "~/Desktop"` 放到他桌面。
- 编译失败会打印 LaTeX 报错；缺宏包 `~/Library/TinyTeX/bin/universal-darwin/tlmgr install <包>`。
- 不要在模板里用 STKaiti/Kaiti SC（macOS 按需下载字体，xelatex 会卡死）；楷体用已装的霞鹜文楷。
- 改模板/样式：`~/tools/latex-pdf/template/`，改完 `latex-pdf --demo` 看效果，按 toolbox 规矩提交。
- 详细说明：`~/tools/latex-pdf/README.md`。完整的大文档例子：`~/quant-prep/build_lp.py`（题目框↔解答页码互跳、勘误卡片）
