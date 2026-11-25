# pku-homework（命令 `hw`）

北大教学网（Blackboard，course.pku.edu.cn）作业助手：找出要交的作业 → 下载题目和附件 → （由 Claude 完成作业）→ 在教学网上原样填表、截图 → 用户同意后提交并核对回执。

## 用法
```
hw list [--todo] [--all]     # 当前学期全部作业（--todo 只看没交且没过期的；--all 含往届课程）
hw show 465165               # 要求、附件、正文链接、允许提交次数、已交记录
hw get 465165 [-d 目录]      # 下载说明.md / 说明.html / 附件 / 正文里教学网文件
                             #   默认到 ~/data/tools/pku-homework/work/<课程>/<作业>/materials，另建 submit/ 放成品
hw me                        # 姓名、学号（作业文件命名用）
hw submit 465165 -f a.zip [-f b.pdf] [--text 文字 | --text-file x.html] [--comment 备注] [--dry|--draft|--confirm]
                             #   默认 --dry：打开上传页、附上文件、填好文字，截图后丢弃，不提交
                             #   --draft：保存草稿（不算提交，用户还能在网页上改）
                             #   --confirm：正式提交，然后自动查提交记录核对
hw status 465165             # 提交记录（状态、文件名、分数）
```
编号是 `hw list` 第一列（成绩中心列号去掉 `_` 和 `_1`）。截图在 `~/data/tools/pku-homework/shots/`。

## 原理
- 所有操作都在用户 Windows 笔记本上的**专用 Chrome**（pcweb 那个，9222 端口）里跑：经 `tsx sh mac` 执行 PowerShell，
  通过 CDP 在一个**属于本工具的标签**里执行 JS（标签 id 记在 `%LOCALAPPDATA%\ClaudeChrome\hw_tab.txt`，不碰别的会话的标签）。
- 读：同源调用 Blackboard 公共 REST（`/learn/api/public/v1|v2/...`），用的是页面本身的登录状态，不取 cookie、不存密码。
  - 课程 `users/me/courses?expand=course`，作业 = 成绩中心里带 `contentId` 的列（`gradebook/columns`），
    提交记录 `columns/{id}/attempts`，题目 `contents/{id}`，附件 `contents/{id}/attachments/{id}/download`。
- 交：打开经典界面的上传页 `/webapps/assignment/uploadAssignment?content_id=..&course_id=..`，
  用 DataTransfer 把文件放进页面自己的“浏览本地文件”控件（页面会把 input 挪成 `newFile_LocalFileN` 并清空，代码会把文件再放回去），
  文字写进 tinymce，再点页面自己的「提交」/「保存草稿」按钮。文件先 `tsx push` 到 `%LOCALAPPDATA%\ClaudeHw\up\`，用完删除。
- 代码：`hw`（Python，mini 上）、`cdp.ps1`（笔记本上执行的 PowerShell 部分）、`lib.js`（页面里执行的 JS）。

## 依赖和前提
- 用户笔记本开着、会话台转发窗口或命令窗口开着（tsx 能连 mac）；专用 Chrome 开着（`pcweb start`）。
- 教学网在专用 Chrome 里登录着（有保活计划任务）；掉线时 hw 会报 `LOGIN`，请用户在专用窗口重新登录。

## 注意
- **正式提交是对外动作**：必须先把要交的文件清单、文字、截图给用户看，用户明确同意后才用 `--confirm`。
  很多作业只允许交 1 次（`hw show` 里“允许提交次数”），交错了只能找老师。
- 只处理“作业”（resource/x-bb-assignment）；在线测验（test）不自动做。
- 有的作业要求在外部网站作答（比如机器学习概论的“标准化作答网站” 222.29.2.84），正文链接会列出来，那部分要另外处理。
- 页面上若已有草稿文件，`submit` 会提示“原来就有草稿文件”，提交时会一起交上去。
- 每次上传都通过 base64 走 CDP，单个文件建议 < 50 MB。

## 实测记录
- 2026-11-25：list / show / get / me、`submit --dry`、`submit --confirm` 均实测通过
  （机器学习概论第三次项目，30 MB zip + PDF，回执 dec4d10c…，教学网显示两个文件、状态 NeedsGrading）。`--draft` 未实测。
- 学生调不了 `attempts/{id}/files` 接口，所以 `hw status` 显示回执编号和提交总字节数（= 各文件大小之和），文件名看提交后截图。
