# pc-remote

从 mini 远程操作用户自己的电脑：看屏幕、点鼠标敲键盘、控制一个专用 Chrome、在 GPU 台式机上跑 PowerShell。
三个命令都是 zsh 脚本，经 ClaudeHub 的 `tsx sh mac`（笔记本）或 `ssh gpu`（台式机）在对方电脑上执行，
对方电脑不用装任何常驻程序（只要命令窗口 / 桌面助手开着）。

## 用法

```
pcctl shot [宽度=1280]      # 截全屏，打印本地 png 路径和缩放比例（点之前把截图坐标乘以比例）
pcctl click X Y | dclick X Y | rclick X Y | move X Y
pcctl scroll N              # 正数向上
pcctl type '文字'           # 经剪贴板粘贴，支持中文
pcctl key '^l'              # SendKeys 语法：^=Ctrl %=Alt +=Shift {ENTER} {TAB} {ESC}

pcweb start [url]           # 启动专用 Chrome（%LOCALAPPDATA%\ClaudeChrome，调试端口 9222 只监听本机）
pcweb tabs | open URL | new URL | close
pcweb text                  # 当前页正文（前 2 万字）
pcweb eval 'JS'             # 在当前页执行 JS 并返回结果
pcweb clicktext '文字'      # 用真实鼠标事件点文字完全相同的元素
pcweb shot                  # 网页截图（窗口不用在前台）
PCWEB_TAB=n pcweb …         # 指定第 n 个标签

gpups '命令'                # 在 gpu 台式机上执行 PowerShell（也可从标准输入读多行脚本）

pcwait [分钟=180]           # 等笔记本能连上（合盖睡着、断线时），连上返回 0；放后台运行，结束时接着做
```

环境变量：`PCCTL_HOST`（默认 `mac`，即当前窗口那台电脑）、`PCCTL_DIR`（截图存放，默认 `~/.cache/pcctl`）。

## 依赖和前提
- 用户的 Windows 电脑在安装 ClaudeHub 时选了「允许执行命令」，命令窗口开着。
- `pcweb` 用一个专用 Chrome 配置（用户日常的 Chrome 配置在 Chrome 136+ 不能开调试端口）；要登录的网站让用户在专用窗口里登录一次。
- `gpups` 需要 `~/.ssh/config` 里有 `gpu` 别名。
- 命令装在 `~/.local/bin/`，是指向这里的软链接。

## 注意
- 操作用户正在用的窗口之前先截图确认；点「发送 / 付款 / 删除 / 提交」之类按钮前先问用户。
- 不从 cookie 取登录凭证自己调网站接口，一律在页面里操作。

## 笔记本睡眠与断线（2026-11-26）
- 笔记本电源设置：插电时合盖“不采取任何操作”（只关屏幕，继续运行）；电池时合盖仍睡眠。插电时本来就不会自动睡眠。
- 笔记本上的计划任务「ClaudeHub助手看门狗」每分钟按正式协议 PING 桌面助手（127.0.0.1:47219）：没在监听就启动
  ClaudeHub-Agent；连续 4 次不回答就核对确是 claudehub-agent.ps1 后结束并重启。「ClaudeHub助手看门狗-唤醒」在系统从睡眠
  醒来时（Power-Troubleshooter 1 / Kernel-Power 107、507）触发，15 秒后连查两次，不回答就立即重启。
  脚本和日志：%LOCALAPPDATA%\ClaudeHubWatchdog\（watchdog.ps1、on-resume.ps1、watchdog.log）。
- 会话里经笔记本的操作失败时，后台跑 `pcwait`，连上后自动接着做。
