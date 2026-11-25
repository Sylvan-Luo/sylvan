---
name: pc-remote
description: 远程操作用户自己的 Windows 电脑：截屏看屏幕、点鼠标/敲键盘（pcctl），控制笔记本上已登录教学网/高顿等网站的专用 Chrome、读网页/执行 JS/网页截图（pcweb），在 GPU 台式机上跑 PowerShell（gpups）。用户说“看看我屏幕”“帮我点一下”“在我电脑浏览器里打开/读一下 XX 网页”“在台式机上跑”时用。
---

# pc-remote（pcctl / pcweb / gpups）

- `pcctl shot` → 看截图 → 坐标乘以打印的缩放比例 → `pcctl click X Y`；`pcctl type '中文'`、`pcctl key '{ENTER}'`。
- `pcweb start` 打开专用 Chrome；`pcweb tabs` / `open URL` / `text` / `eval 'JS'` / `clicktext '按钮文字'` / `shot`；`PCWEB_TAB=n` 指定标签。
- `gpups '命令'` 或 `gpups <<'EOF' … EOF`：在 gpu 台式机上执行 PowerShell。

注意：动用户正在用的窗口前先截图；发送、付款、删除、提交类按钮先问用户。需要登录的网站请用户在专用 Chrome 里自己登录，不要从 cookie 取凭证。
详细说明见 `~/tools/pc-remote/README.md`。
