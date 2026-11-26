# latex-pdf

把 Markdown（或 Word / HTML / LaTeX）先转成 LaTeX，套一个精美模板，再用 XeLaTeX 编译成 PDF。
版式参照用户给的《图像处理 期中总复习笔记》：深蓝封面横幅、蓝色章节标题、宋体正文 + 冬青黑体/Avenir 标题、
彩色的定义 / 结论 / 原话 / 关键公式 / 易错 / 直觉 / 要点 / 注 框，选择题选项自动排两栏，答案浅黄条。

## 用法

```bash
latex-pdf 笔记.md                       # 生成 笔记.pdf（同目录）
latex-pdf 笔记.md -o ~/Desktop/x.pdf    # 指定输出
latex-pdf 笔记.md --book --toc --chapter-name 讲   # 书籍版：整页封面、目录、# = 「第 N 讲」
latex-pdf 笔记.md --tex                 # 同时保留 笔记.tex（可手改后再 latex-pdf 笔记.tex）
latex-pdf 笔记.md --theme teal          # 主色：navy（默认）teal wine forest ink purple orange
latex-pdf 正文.tex                      # 只有正文的 LaTeX 片段：自动套模板；完整 .tex 直接编译
latex-pdf 报告.docx --title 报告        # pandoc 能读的格式都行（docx/html/odt/rst/ipynb…）
latex-pdf --demo -o ~/Desktop/demo.pdf  # 示例：examples/demo.md，含全部样式
latex-pdf 笔记.md -M date=2026-11-25 -M header-title=页眉右侧文字
```

命令在 `~/.local/bin/latex-pdf`（链接到本目录的 `latex-pdf`）。编译出错时会打印 LaTeX 报错那几行，
加 `--keep` 保留编译目录看完整日志。

## 两种版式

| | 文章版（默认） | 书籍版（`--book` 或 YAML `book: true`） |
|---|---|---|
| 封面 | 首页顶部横幅 + 信息框，正文紧接 | 整页封面 + 信息框 + `cover-extra`，然后目录 |
| `#` | 节「1 进展」 | 章「第 2 讲 / 第 2 章」，每章新页 |
| 编号 | 节、小节编号；定义等框按全文编号 | 只编到节「2.1」；定义等框按章编号「定义 2.1」 |
| 页眉 | 左：当前节，右：标题 | 左：当前章，右：标题 |

## YAML 头（都可选）

```yaml
---
title: 期中总复习笔记           # 大标题
eyebrow: 北京大学 · 2026 秋 · 图像处理   # 标题上方一行小字
subtitle: Image Processing · Midterm Review   # 标题下方一行
author: 某某
date: 2026-11-25
book: true                      # 书籍版
toc: true                       # 目录（也可以 --toc）
toc-depth: 2                    # 目录深度，默认 1（只到节）
chapter-name: 讲                # 书籍版章名
secnumdepth: 2                  # 编号深度，书籍默认 1，文章默认 2
theme: navy                     # 主色
header-title: 图像处理 · 期中总复习   # 页眉右侧，默认等于 title
zihao: 5                        # 正文字号：5 = 五号 10.5pt，-4 = 小四 12pt
cover-art-off: true             # 不要封面右上角的方块装饰
info:                           # 封面信息框（键值对，按顺序）
  - 考试: "**11/12（周四）**，理教 106"
  - 范围: 第 2、3、5–8 讲
cover-extra: |                  # 书籍版封面信息框下方的任意内容（可放 ::: 块）
  ::: {.guide title="怎么读这份笔记"}
  ……
  :::
---
```

## Markdown 写法

书籍版里 `# 标题 {.part}` 是「第一部分」分隔页（上半页主色横幅），加 `.restart` 则下面的章从第 1 章重新编号；
`{.unnumbered .unlisted}` 是不编号也不进目录的标题。

正文里的 Unicode 上下标（xᵢ、n₁、Aᵀ）自动转成真正的上下标，≡ ⇒ ∫ ∀ 等数学符号自动用数学字体，不会缺字。
YAML 的 `header-includes:`（```` ```{=latex} ```` 块）可以加自己的宏。

普通 Markdown（标题、列表、表格、公式 `$…$` `$$…$$`、图片 `![说明](图.png){width=60%}`、
脚注、代码块）照常写。`# 标题 {-}` 是不编号的标题；书籍版里它下面的小标题也自动不编号。

### 彩色框（`:::` 块）

| 写法 | 效果 |
|---|---|
| `::: def` + 第一行 `### 名称`（或 `{.def title="名称"}`） | 蓝色「定义 2.1 名称」框 |
| `::: thm` / `::: conclusion` / `::: theorem` | 青绿「结论 / 定理」框，编号 |
| `::: example` | 灰蓝「例 2.1」框 |
| 加 `.unnumbered`，如 `{.def .unnumbered}` | 不编号 |
| `{.def label="公理"}` | 改左边的字 |
| `::: key` / `::: formula` | 浅黄底居中（关键公式） |
| `::: warn` / `::: pitfall` | 红条「易错」 |
| `::: intuition` | 紫条「直觉」 |
| `::: tip` / `::: exam` | 洋红条「要点 / 考场写法」 |
| `::: note` | 灰条「注」 |
| `{.warn title="注意"}` | 条框换标签 |
| `::: said`（标题「原话」）/ `::: quote`（标题「引用」），`title=` 可改 | 橙条浅底，楷体；以 `——` 开头的段落变成右对齐署名 |
| `::: guide`（`title=` 可改，默认「学习指南」） | 绿框，里面适合放定义列表 `键\n: 值` |
| `::: info`（可带 `title=`） | 主色淡底信息框 |
| `::: answer` | 浅黄条，小号无衬线（答案） |
| `::: choices`（`cols=1/2/4`，默认 2） + 列表 | 选择题选项 (A)(B)(C)(D) 排栏；条目自带 `A.` 的用它自己的 |
| `::: card` | 白底细灰框卡片（条目、勘误等），小号字 |
| `::: center` / `::: newpage` | 居中 / 换页 |
| `> [!NOTE]` `[!TIP]` `[!WARNING]` `[!IMPORTANT]` `[!CAUTION]` | GitHub 风格提示，对应灰/洋红/红/青绿框 |
| 普通 `>` 引用 | 灰色左条 |

### 行内标记（`[文字]{.类}`）

| 写法 | 效果 |
|---|---|
| `[必会]{.tag}` | 小标签；必会/重点 红、常考 洋红、了解/补充 灰，其他灰；`{.tag .blue}` 指定颜色（red orange green blue purple pink gray yellow） |
| `[L2 p.9]{.src}` | 灰色小字出处〔L2 p.9〕 |
| `[72 ppi]{.hl}` | 蓝色加粗强调 |
| `[文字]{.mark}` | 浅黄底高亮 |
| `[文字]{.kai}` | 楷体 |
| `[ ]{.blank}`、`[ ]{.blank width=6em}` | 填空横线 |

### 直接写 LaTeX

Markdown 里可以直接写 LaTeX 命令；整段 LaTeX 用 ```` ```{=latex} ```` 围起来。
模板里的环境：`lpdef lpthm lpexample`（`\begin{lpdef}[标签]{名称}`，带 `*` 不编号）、
`lpwarn lpintuition lptip lpnote lpquote lpguide`（`\begin{lpwarn}[标签]`）、`lpkey lpanswer lpinfo`、
`\lptag[颜色]{}` `\lpsrc{}` `\lphl{}` `\lpattrib{}`。手写完整 .tex 时 `\usepackage{latex-pdf-theme}`
（ctexart/ctexbook，`fontset=none`）。

## 文件

- `latex-pdf`：命令行（Python 3，只用标准库）
- `template/latex-pdf.tex`：pandoc 模板（封面、目录、版式切换）
- `template/latex-pdf-theme.sty`：字体、颜色、标题、页眉、各种框
- `template/boxes.lua`：pandoc 过滤器，把 `:::` 块和行内标记翻成上面的环境
- `examples/demo.md`：全部样式的示例

## 依赖和前提（都装在 mini 的家目录，不需要管理员）

- pandoc 3.14：`~/.local/bin/pandoc`（GitHub 官方 arm64 二进制）
- TinyTeX：`~/Library/TinyTeX`（直接解压官方包，没改系统 PATH；脚本里用全路径）。
  缺宏包时：`~/Library/TinyTeX/bin/universal-darwin/tlmgr install <包名>`；
  不知道包名：`tlmgr search --global --file /xxx.sty`。
- 字体：正文 Songti SC + TeX Gyre Termes，标题 Hiragino Sans GB + Avenir Next，数学 STIX Two Math（都是 macOS 自带）；
  楷体用霞鹜文楷（`~/Library/Fonts/LXGWWenKai-*.ttf`，OFL 开源）。缺字体时自动退回 TeX 自带的 Fandol 字体。

## 注意

- **不要在模板里探测 STKaiti / Kaiti SC**：macOS 上它们是“按需下载”字体，xelatex 查找时会一直卡住。
- 第一次编译要建字体缓存，会慢一些；之后一份几页的文档 2–5 秒。
- 输入在用户电脑上时：`tsx pull mac "~/Desktop/xx.md"` 拉过来，生成后 `desk put xx.pdf -c 类别`（放进桌面对应类别文件夹，见 desk 工具）。
- Markdown 里的图片路径相对于 .md 文件所在目录。
