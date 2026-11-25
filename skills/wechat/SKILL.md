---
name: wechat
description: 用户的微信（Windows 笔记本上的微信 4.x）：看谁私聊了我、读某个好友的最近消息、给某个好友发/回微信，以及微信私聊提醒（会话台网页右上角）不工作时排查。用户说“微信”“谁给我发消息了”“给 X 发微信/回复 X”“读一下 X 的消息”“微信提醒没反应”时用。群聊一律不发。
---

# wechat — 微信私聊提醒 + 代发消息

命令是 `~/tools/wechat/wx`（细节、原理、限制见 `~/tools/wechat/README.md`）。

## 最常用
```
~/tools/wechat/wx status            # 监看是否正常、当前未读的私聊
~/tools/wechat/wx inbox 20          # 最近的私聊提醒
~/tools/wechat/wx read 名字          # 读这个私聊屏幕上最近的消息（会标成已读，先跟用户说一声）
~/tools/wechat/wx send 名字 内容 --dry   # 试填，不发
~/tools/wechat/wx send 名字 内容     # 真发
```

## 发消息的规矩（必须遵守）
1. **每次发送前先确认**：把「发给谁（微信里显示的名字）」和「原文」完整给用户看，用户明确说可以才执行 `wx send`。
   用户只说了大意的，先起草给他看。用户 2026-11-25 选的就是“每次确认”。
2. **群聊一律不发**（工具也会拒绝）。不群发、不加好友、不频繁发——有被腾讯限制账号的风险。
3. 发完看返回的 `verified`；是 false 就去看笔记本上 `%LOCALAPPDATA%\ClaudeWx\last_send.png`
   （`tsx pull mac 'C:\Users\<WinUser>\AppData\Local\ClaudeWx\last_send.png'`），确认发出去没有，照实告诉用户。
4. 发送时微信会在用户屏幕前台闪 2～3 秒，提前说一句。

## 提醒不工作时
- `wx status` 看状态：`closed`＝微信主窗口被关到托盘、`minimized`＝最小化——这两种工具会在用户键鼠空闲时自动处理（约 10～60 秒）；关到托盘的会进入「托盘模式」（窗口在屏幕外、无任务栏按钮，照常能读，用户点托盘图标会自动挪回来）。用户说找不到微信窗口：`wx show`。一直不恢复看笔记本 agent.log；
  `compact`＝窗口太窄；“笔记本没连上”＝会话台的转发窗口或命令窗口没开 / 笔记本睡了。
- mini 轮询：`launchctl print gui/$(id -u)/com.user.wechat-watch`，日志 `~/.local/state/wechat/watch.log`。
- 笔记本进程：`wx start` 重启（会同步脚本）；日志 `%LOCALAPPDATA%\ClaudeWx\agent.log`。
- 误判：`wx private add 名字`（好友被当成群/免打扰好友也要提醒）、`wx groups add 名字`、`wx ignore add 名字`。
- `wx selftest` 塞一条假提醒，检查网页。
- 改了 `~/tools/wechat/win/*.py` 后执行 `wx start`（自动同步并重启笔记本进程）。
