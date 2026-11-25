# -*- coding: utf-8 -*-
"""wxagent — 微信 4.x（Weixin.exe）截图 + OCR 自动化，运行在用户的 Windows 电脑上。

用法（一般由 mini 上的 ~/tools/wechat/wx 调用，不用手敲）：
  python wxagent.py scan                 读一次会话列表，打印 JSON
  python wxagent.py loop [秒=4]          常驻：每隔几秒 scan，发现私聊新消息写进 feed.json
  python wxagent.py send <名字b64> <内容b64> [--dry]   给私聊好友发一条消息（群聊一律拒绝）
  python wxagent.py read <名字b64>       打开某个私聊，读出可见的最近消息（会把它标成已读）
  python wxagent.py shot                 把微信窗口截图存成 shot.png

只用截图（PrintWindow）和 Windows 自带中文 OCR，不注入、不读数据库、不改微信文件。
"""
import sys, os, json, time, re, base64, traceback, hashlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import wxlib as L
import win32gui, win32con, win32api

FEED = os.path.join(HERE, 'feed.json')
CONF = os.path.join(HERE, 'config.json')
LOG = os.path.join(HERE, 'agent.log')

# 永远当作“不是私聊好友”的会话名（服务号、折叠群等）
NOT_PRIVATE = {'公众号', '服务号', '订阅号', '订阅号消息', '服务通知', '微信团队', '微信支付', '文件传输助手',
               '折叠的群聊', '群聊', '腾讯新闻', '微信运动', 'QQ邮箱提醒', '腾讯视频', '微信游戏', '视频号',
               '小程序客服消息', '朋友推荐消息', '新的朋友', '漂流瓶', '附近的人', '语音记事本', '微信收款助手',
               '微信卡包', '公众号消息', '看一看', '搜一搜'}


def log(*a):
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(time.strftime('%m-%d %H:%M:%S ') + ' '.join(str(x) for x in a) + '\n')
    except Exception:
        pass


def load_conf():
    try:
        with open(CONF, encoding='utf-8') as f:
            c = json.load(f)
    except Exception:
        c = {}
    c.setdefault('groups', [])        # 手动指定为群聊（识别不出来时用）
    c.setdefault('private', [])       # 手动指定为私聊
    c.setdefault('ignore', [])        # 不提醒
    return c


# ---------------------------------------------------------------- 版面
class Layout:
    def __init__(self, img, s):
        self.img = img
        self.a = np.asarray(img).astype(np.int16)
        self.s = s
        H, W = self.a.shape[:2]
        y = int(H * 0.55)
        row = self.a[y]
        x = int(30 * s)
        # 左侧导航栏 → 会话列表：颜色跳变
        self.list_left = None
        for i in range(x, min(W - 1, int(140 * s))):
            if np.abs(row[i + 1] - row[i]).max() >= 6 and np.abs(row[i + 2] - row[i]).max() >= 6:
                self.list_left = i + 1
                break
        if self.list_left is None:
            self.list_left = int(67 * s)
        # 会话列表 → 聊天区：遇到接近纯白（≥245）且持续
        self.list_right = None
        for i in range(self.list_left + int(120 * s), min(W - 3, self.list_left + int(420 * s))):
            if row[i].min() >= 245 and row[i + 2].min() >= 245 and row[i - 1].min() < 245:
                self.list_right = i
                break
        if self.list_right is None:
            self.list_right = self.list_left + int(161 * s)
        self.H, self.W = H, W

    def compact(self):
        """窗口太窄时微信收起会话列表（只剩聊天，左上角有“<”）：导航栏右边直接是接近纯白的聊天区。"""
        y = int(self.H * 0.55)
        c = self.a[y, self.list_left + int(6 * self.s)]
        return bool(c.min() >= 246) or (self.list_right - self.list_left) > 300 * self.s

    def blank(self):
        """主窗口被关到托盘时，Qt 内容是一整片白。"""
        return float(self.a.std()) < 12


def widen(h, s):
    """窄屏模式时把窗口拉宽到 600 逻辑像素（不激活、不改 Z 顺序；用户同意过）。"""
    l, t, r, b = win32gui.GetWindowRect(h)
    want = int(600 * s)
    if r - l >= want:
        want = r - l + int(120 * s)
    mon = win32api.GetMonitorInfo(win32api.MonitorFromWindow(h, 2))['Work']
    nl = l if os.path.exists(HIDDEN) else max(mon[0], min(l, mon[2] - want))
    win32gui.SetWindowPos(h, 0, nl, t, want, b - t, 0x0004 | 0x0010)   # SWP_NOZORDER | SWP_NOACTIVATE
    time.sleep(0.8)
    log('widen', l, t, r, b, '->', nl, want)


def _tray_rect():
    """微信托盘图标的位置（Shell_NotifyIconGetRect，uID=0）。图标被收进“^”时返回的是“^”的位置。"""
    import ctypes
    from ctypes import wintypes

    class NII(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.DWORD), ('hWnd', wintypes.HWND), ('uID', wintypes.UINT), ('guidItem', ctypes.c_byte * 16)]
    tray = win32gui.FindWindow(None, 'WxTrayIconMessageWindow')
    if not tray:
        return None
    for uid in (0, 1):
        n = NII(); n.cbSize = ctypes.sizeof(NII); n.hWnd = tray; n.uID = uid
        r = wintypes.RECT()
        if ctypes.windll.shell32.Shell_NotifyIconGetRect(ctypes.byref(n), ctypes.byref(r)) == 0:
            return (r.left, r.top, r.right, r.bottom)
    return None


def _chevron_rect():
    try:
        import uiautomation as auto
        auto.SetGlobalSearchTimeout(1.5)
        tb = auto.PaneControl(searchDepth=1, ClassName='Shell_TrayWnd')
        b = tb.ButtonControl(AutomationId='SystemTrayIcon', Name='显示隐藏的图标')
        if b.Exists(0.5):
            r = b.BoundingRectangle
            return (r.left, r.top, r.right, r.bottom)
    except Exception:
        pass
    return None


def idle_seconds():
    import ctypes
    from ctypes import wintypes

    class LII(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.UINT), ('dwTime', wintypes.DWORD)]
    li = LII(); li.cbSize = ctypes.sizeof(LII)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li))
    return (ctypes.windll.kernel32.GetTickCount() - li.dwTime) / 1000.0


def unminimize_quietly(h):
    """最小化的窗口（最小化时读不到）：先挪到屏幕外，再不激活地还原——用户看来还是最小化着，任务栏按钮保留；
    用户点任务栏按钮时，watch_user_open 会把它挪回原位置。"""
    pl = win32gui.GetWindowPlacement(h)   # (flags, showCmd, ptMin, ptMax, rcNormal)
    l, t, r, b = pl[4]
    vx = win32api.GetSystemMetrics(76)
    with open(HIDDEN, 'w') as f:
        json.dump({'rect': [l, t, r, b], 'ts': time.time(), 'keep_tab': True, 'from': 'minimized'}, f)
    off = vx - (r - l) - 2000
    # 仍保持最小化、只把“还原后的位置”改到屏幕外；再不激活地还原。Windows 可能把它贴回屏幕内，所以紧接着再挪一次
    win32gui.SetWindowPlacement(h, (pl[0], 7, pl[2], pl[3], (off, t, off + (r - l), b)))   # SW_SHOWMINNOACTIVE
    win32gui.ShowWindow(h, 4)                                                             # SW_SHOWNOACTIVATE
    win32gui.SetWindowPos(h, 1, off, t, r - l, b - t, 0x0010)                             # HWND_BOTTOM, NOACTIVATE
    time.sleep(0.6)
    log('unminimize quietly', not win32gui.IsIconic(h))
    return not win32gui.IsIconic(h)


def reopen_from_tray(h, to_back=True):
    """主窗口被关到托盘（内容空白）时，像用户一样点右下角托盘里的微信图标把它打开，
    然后把焦点还给原来的窗口、把微信放到最底层（不挡东西，后台照样能读）。返回 True/False。"""
    prev = win32gui.GetForegroundWindow()
    if np.asarray(L.capture(h)).std() >= 12:
        return True                      # 用户刚自己打开了，不动
    r = _tray_rect()
    if not r:
        log('reopen: 找不到托盘图标')
        return False
    chev = _chevron_rect()
    if chev and abs(r[0] - chev[0]) < 4 and abs(r[1] - chev[1]) < 4:
        # 图标在“显示隐藏的图标”里：先点开“^”
        L.click((chev[0] + chev[2]) / 2, (chev[1] + chev[3]) / 2)
        time.sleep(0.8)
        r = _tray_rect()
        if not r or (abs(r[0] - chev[0]) < 4 and abs(r[1] - chev[1]) < 4):
            L.key(win32con.VK_ESCAPE)
            log('reopen: 溢出面板里没找到微信图标')
            return False
    L.click((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
    ok = False
    for _ in range(20):
        time.sleep(0.25)
        if np.asarray(L.capture(h)).std() >= 12:
            ok = True
            break
    if to_back:
        if prev and prev != h:
            restore_fg(prev)
        try:
            if load_conf().get('tray_mode', True):
                hide_offscreen(h)          # 用户关到托盘的本意是“别显示”：挪到屏幕外，看起来还在托盘里
            else:
                win32gui.SetWindowPos(h, 1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)   # HWND_BOTTOM
        except Exception:
            log('hide error', traceback.format_exc())
    log('reopen from tray', ok)
    return ok


# ---------------------------------------------------------------- 托盘模式（窗口挪到屏幕外）
HIDDEN = os.path.join(HERE, 'hidden.json')


def _taskbar(h, add):
    """去掉 / 加回任务栏按钮（ITaskbarList）。"""
    try:
        import comtypes, comtypes.client
        from comtypes import GUID, COMMETHOD, HRESULT
        from ctypes import c_void_p

        class ITaskbarList(comtypes.IUnknown):
            _iid_ = GUID('{56FDF342-FD6D-11d0-958A-006097C9A090}')
            _methods_ = [COMMETHOD([], HRESULT, 'HrInit'),
                         COMMETHOD([], HRESULT, 'AddTab', (['in'], c_void_p, 'hwnd')),
                         COMMETHOD([], HRESULT, 'DeleteTab', (['in'], c_void_p, 'hwnd')),
                         COMMETHOD([], HRESULT, 'ActivateTab', (['in'], c_void_p, 'hwnd')),
                         COMMETHOD([], HRESULT, 'SetActiveAlt', (['in'], c_void_p, 'hwnd'))]
        comtypes.CoInitialize()
        tb = comtypes.client.CreateObject(GUID('{56FDF344-FD6D-11d0-958A-006097C9A090}'), interface=ITaskbarList)
        tb.HrInit()
        (tb.AddTab if add else tb.DeleteTab)(h)
    except Exception:
        log('taskbar error', traceback.format_exc())


def is_hidden(h):
    return os.path.exists(HIDDEN)


def hide_offscreen(h, keep_tab=False):
    """托盘模式：窗口保持打开（微信照常绘制，能读），但挪到所有屏幕外面、去掉任务栏按钮（最小化来的保留按钮）。"""
    l, t, r, b = win32gui.GetWindowRect(h)
    vx = win32api.GetSystemMetrics(76)   # SM_XVIRTUALSCREEN
    if l < vx - 100:
        return
    if win32gui.GetForegroundWindow() == h:
        log('hide skipped: 微信在前台（用户在用）')
        return
    with open(HIDDEN, 'w') as f:
        json.dump({'rect': [l, t, r, b], 'ts': time.time(), 'keep_tab': keep_tab}, f)
    win32gui.SetWindowPos(h, 1, vx - (r - l) - 2000, t, 0, 0, 0x0001 | 0x0010)   # HWND_BOTTOM, NOSIZE, NOACTIVATE
    if not keep_tab:
        _taskbar(h, False)
    log('hide offscreen', l, t, r, b)


def unhide(h, activate=False):
    """挪回原来的位置、加回任务栏按钮。"""
    try:
        with open(HIDDEN) as f:
            l, t, r, b = json.load(f)['rect']
    except Exception:
        return False
    try:
        os.remove(HIDDEN)
    except Exception:
        pass
    win32gui.SetWindowPos(h, 0, l, t, r - l, b - t, 0x0004 | (0 if activate else 0x0010))   # 原位置、原大小
    _taskbar(h, True)
    if activate:
        L.activate(h)
    log('unhide', l, t, r, b)
    return True


def watch_user_open(stop):
    """托盘模式下，用户点托盘图标（微信变成前台）时，立刻把窗口挪回来。"""
    import win32process
    while not stop.is_set():
        try:
            if os.path.exists(HIDDEN) and not busy():
                h = L.find_main()
                fg = win32gui.GetForegroundWindow()
                if h and fg:
                    same = fg == h or win32process.GetWindowThreadProcessId(fg)[1] == win32process.GetWindowThreadProcessId(h)[1]
                    if same:
                        unhide(h, activate=True)
        except Exception:
            pass
        stop.wait(0.15)


def red_clusters(a, x0, x1, y0, y1, min_px=12):
    """在区域里找微信未读红点/红色数字气泡（实心红圆）。返回 [(cx, cy, w, h)]。"""
    r = a[y0:y1, x0:x1]
    m = (r[:, :, 0] >= 225) & (r[:, :, 1] <= 95) & (r[:, :, 2] <= 95)
    ys, xs = np.nonzero(m)
    pts = set(zip(ys.tolist(), xs.tolist()))
    out = []
    while pts:
        p = pts.pop(); st = [p]; c = [p]
        while st:
            yy, xx = st.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    q = (yy + dy, xx + dx)
                    if q in pts:
                        pts.remove(q); st.append(q); c.append(q)
        if len(c) >= min_px:
            cy = [q[0] for q in c]; cx = [q[1] for q in c]
            w = max(cx) - min(cx) + 1; h = max(cy) - min(cy) + 1
            fill = len(c) / float(w * h)
            if 0.45 <= fill and 0.6 <= w / float(h) <= 3.5:
                out.append((x0 + (min(cx) + max(cx)) / 2.0, y0 + (min(cy) + max(cy)) / 2.0, w, h))
    return out


def is_mosaic(a, box):
    """群聊默认头像是“小头像拼图”：拼块之间有贯穿整个头像的浅灰缝。"""
    x0, y0, x1, y1 = [int(v) for v in box]
    r = a[y0:y1, x0:x1]
    if r.size == 0:
        return False
    n, m = r.shape[1], r.shape[0]
    g = (np.ptp(r, axis=2) <= 8) & (r.min(axis=2) >= 212) & (r.max(axis=2) <= 246)
    cols = g.mean(axis=0)[int(n * .15):int(n * .85)]
    rows = g.mean(axis=1)[int(m * .15):int(m * .85)]
    if not cols.size or not rows.size:
        return False
    c, w = cols.max(), rows.max()
    return bool((c >= 0.85 and w >= 0.85) or (max(c, w) >= 0.95 and min(c, w) >= 0.6))

def norm_name(s):
    s = s.strip()
    s = re.sub(r'[\.．。…·、,，“"]+$', '', s)
    return s.strip()


TIME_TAIL = re.compile(r'\s*(昨天\s*\d{1,2}[:：]\d{2}|\d{1,2}[:：]\d{2}|昨天|前天|星期[一二三四五六日天]|周[一二三四五六日天]|'
                       r'\d{2,4}[/年-]\d{1,2}[/月-]\d{1,2}日?|\d{1,2}[/月]\d{1,2}日?)$')
TIME_RE = re.compile(r'^' + TIME_TAIL.pattern.lstrip(r'\s*'))


def split_time(t):
    m = TIME_TAIL.search(t)
    if m and m.start() > 0:
        return t[:m.start()].strip(), m.group(1).replace(' ', '')
    return t.strip(), ''


def avatar_rows(a, lx, s, top):
    """按头像找出每一行会话：头像列里“非背景”像素占多数的连续段，高约 36 逻辑像素。"""
    H = a.shape[0]
    xs = np.arange(int(lx + 14 * s), int(lx + 46 * s))
    bgx = int(lx + 4 * s)
    bg = a[top:H, bgx][:, None, :]
    on = (np.abs(a[top:H][:, xs] - bg).max(axis=2) > 10).mean(axis=1) > 0.5
    runs = []
    y = 0
    n = len(on)
    while y < n:
        if on[y]:
            y0 = y
            while y < n and on[y]:
                y += 1
            if runs and y0 - runs[-1][1] < 6 * s:
                runs[-1][1] = y
            else:
                runs.append([y0, y])
        y += 1
    return [(top + r0, top + r1) for r0, r1 in runs if 30 * s <= r1 - r0 <= 41 * s and top + r1 < H - 2]


def last_bubble_mine(lay):
    """聊天区最下面一个气泡是不是我发的（绿色）。返回 True / False / None（看不出来）。"""
    a, s = lay.a, lay.s
    x0, x1 = lay.list_right + int(10 * s), lay.W - int(10 * s)
    y0, y1 = int(80 * s), lay.H - int(190 * s)
    if y1 <= y0 or x1 <= x0:
        return None
    r = a[y0:y1, x0:x1]
    bg = a[int(100 * s), x0]
    diff = (np.abs(r - bg).max(axis=2) > 6).sum(axis=1)
    ys = np.nonzero(diff > 30)[0]
    if not ys.size:
        return None
    yb = ys[-1]
    seg = r[max(0, yb - int(40 * s)):yb + 1]
    green = (seg[:, :, 1] > 190) & (seg[:, :, 1] - seg[:, :, 0] > 40) & (seg[:, :, 1] - seg[:, :, 2] > 50)
    return bool(green.sum() > 40)


def has_bell(a, ay0, lx, rx, s, bgc):
    """免打扰铃铛：预览行最右边一块约 10 逻辑像素宽的图形，和前面的文字（“...”）之间隔开一段空白。"""
    z = a[int(ay0 + 22 * s):int(ay0 + 38 * s), int(lx + 54 * s):int(rx - 10 * s)]   # 不含最右边的滚动条
    if not z.size:
        return False
    col = (np.abs(z - bgc).max(axis=2) > 40).any(axis=0)
    xs = np.nonzero(col)[0]
    runs = []
    for x in xs:
        if runs and x - runs[-1][1] <= 2:
            runs[-1][1] = x
        else:
            runs.append([x, x])
    if len(runs) < 2:
        return False
    w = runs[-1][1] - runs[-1][0] + 1
    gap = runs[-1][0] - runs[-2][1]
    return bool(7 * s <= w <= 13 * s and gap >= 6 * s)


def ensure_tall(h, s):
    """窗口太矮时会话列表只显示几行，新消息容易落在可见范围外：拉到工作区高度（不激活、不改 Z 顺序）。"""
    l, t, r, b = win32gui.GetWindowRect(h)
    mon = win32api.GetMonitorInfo(win32api.MonitorFromWindow(h, 2))['Work']
    want = mon[3] - mon[1]
    if b - t >= want * 0.9:
        return False
    win32gui.SetWindowPos(h, 0, l, mon[1], r - l, want, 0x0004 | 0x0010)
    time.sleep(0.6)
    log('heighten', l, t, r, b, '->', mon[1], want)
    return True


def scroll_list_top(h, lay):
    """后台给会话列表发滚轮消息滚回顶部（不动鼠标、不抢焦点）。"""
    l, t, r, b = win32gui.GetWindowRect(h)
    x = int(l + (lay.list_left + lay.list_right) / 2)
    y = int(t + lay.H / 2)
    for _ in range(8):
        win32gui.PostMessage(h, win32con.WM_MOUSEWHEEL, (120 * 5) << 16, ((y & 0xFFFF) << 16) | (x & 0xFFFF))
        time.sleep(0.05)
    time.sleep(0.6)


def scan(h=None, fix_scroll=False):
    h = h or L.find_main()
    if not h:
        return {'status': 'no_wechat', 'msg': '没找到微信窗口（微信没开？）'}
    if win32gui.IsIconic(h):
        return {'status': 'minimized', 'msg': '微信窗口最小化了；你不操作键鼠时会自动还原到最底层'}
    s = L.dpi_scale(h)
    img = L.capture(h)
    lay = Layout(img, s)
    if lay.blank():
        return {'status': 'closed', 'msg': '微信主窗口被关到托盘了；你不操作键鼠时会自动从右下角托盘打开、放到最底层'}
    if lay.compact():
        if os.path.exists(HIDDEN):      # 托盘模式下用户看不到，可以随便调；用户打开着的窗口不动
            widen(h, s)
            img = L.capture(h)
            lay = Layout(img, s)
        if lay.compact() or lay.blank():
            return {'status': 'compact', 'msg': '微信窗口太窄，会话列表被收起来了，暂时读不到；关掉微信（进托盘模式）或把窗口拉宽就好'}
    a = lay.a
    lx, rx = lay.list_left, lay.list_right
    top = int(56 * s)
    # 导航栏“聊天”图标上的红色数字＝非免打扰会话的未读总数
    total = 0
    nav = red_clusters(a, int(20 * s), lx, int(70 * s), int(140 * s))
    if nav:
        cx, cy, w, hh = nav[0]
        if w >= 10.5 * s:
            v = L.rec_badge(img, (cx - w / 2 - 1, cy - hh / 2 - 1, cx + w / 2 + 1, cy + hh / 2 + 1))
            total = v if v is not None else -1
        else:
            total = -1  # 只有小红点
    badges = red_clusters(a, int(lx + 30 * s), int(lx + 56 * s), top, lay.H)
    tx0 = lx + 54 * s
    out = []
    for ay0, ay1 in avatar_rows(a, lx, s, top):
        line1, c1 = L.rec_line(img, (tx0, ay0 - 3 * s, rx - 6 * s, ay0 + 19 * s))
        line2, c2 = L.rec_line(img, (tx0, ay0 + 19 * s, rx - 28 * s, ay0 + 39 * s))
        name, tm = split_time(line1)
        name = norm_name(name)
        if not name:
            continue
        unread = None; count = None
        for bx, by, bw, bh in badges:
            if ay0 - 8 * s <= by <= ay0 + 10 * s:
                if bw >= 10.5 * s:
                    unread = 'num'
                    count = L.rec_badge(img, (bx - bw / 2 - 1, by - bh / 2 - 1, bx + bw / 2 + 1, by + bh / 2 + 1))
                else:
                    unread = 'dot'
                break
        px = a[int(ay0 + 18 * s), int(lx + 4 * s)]
        selected = bool(px[1] > 140 and px[0] < 80)
        bgc = a[int(ay0 + 30 * s), int(lx + 4 * s)]
        muted = (not selected) and has_bell(a, ay0, lx, rx, s, bgc)
        mosaic = is_mosaic(a, (lx + 12 * s, ay0 - 1, lx + 48 * s + 1, ay1 + 1))
        prev = line2.strip()
        sender_prefix = bool(re.match(r'^(\[\d+条\])?\s*[^\s:：\[\]]{1,20}[:：]', prev))
        out.append({'name': name, 'time': tm, 'preview': prev, 'conf': round(min(c1, c2), 2),
                    'unread': unread, 'count': count, 'muted': muted, 'selected': selected,
                    'mosaic': mosaic, 'sender_prefix': sender_prefix, 'y': int(ay0)})
    # 有未读、可见范围里却没有带数字的未读：列表多半被往下滚了。只在托盘模式（窗口在屏幕外，用户看不到）时滚回顶部再读；
    # 用户自己打开着的窗口不动
    if fix_scroll and total and total > 0 and not any(o['unread'] == 'num' for o in out) \
            and os.path.exists(HIDDEN) and win32gui.GetForegroundWindow() != h:
        scroll_list_top(h, lay)
        log('scroll list to top (total_unread=%s)' % total)
        return scan(h, fix_scroll=False)
    for o in out:
        if o['count'] == 0:
            o['count'] = None
    return {'status': 'ok', 'total_unread': total, 'rows': out, 'ts': time.time(), 'last_mine': last_bubble_mine(lay),
            'layout': [lx, rx, round(s, 2), lay.W, lay.H]}


def classify(r, conf):
    """返回 'private' / 'maybe'（多半是私聊，但有点像群） / 'group' / 'other'。"""
    n = r['name']
    if n in conf['private']:
        return 'private'
    if n in conf['ignore'] or n in NOT_PRIVATE:
        return 'other'
    if n in conf['groups']:
        return 'group'
    if r['mosaic']:
        return 'group'
    quiet = r['muted'] or r['unread'] == 'dot' or re.match(r'^\[\d+条\]', r['preview'] or '')
    if quiet:
        # 开了免打扰的会话绝大多数是群；真要提醒某个免打扰的好友，把名字加进 config.json 的 private
        return 'group'
    if r['sender_prefix']:
        return 'maybe'
    return 'private'


# ---------------------------------------------------------------- 常驻监看
def write_feed(feed):
    tmp = FEED + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(feed, f, ensure_ascii=False)
    os.replace(tmp, FEED)


def loop(interval=4.0):
    try:
        with open(FEED, encoding='utf-8') as f:
            feed = json.load(f)
    except Exception:
        feed = {'seq': 0, 'events': []}
    feed['pid'] = os.getpid()
    import threading
    threading.Thread(target=watch_user_open, args=(threading.Event(),), daemon=True).start()
    last = {}          # name -> (unread, count, preview)
    last_total = None
    hidden_since = None
    last_reopen = 0
    last_tall = 0
    off_pending = None
    first = True
    while True:
        if busy():                 # 正在发送 / 读取：别插手
            time.sleep(1)
            continue
        conf = load_conf()
        # 微信被关到托盘 / 最小化：用户键鼠空闲时自动打开并放到最底层（config.json 里 auto_reopen=false 可关）
        if conf.get('auto_reopen', True) and feed.get('status') in ('closed', 'minimized'):
            if hidden_since is None:
                hidden_since = time.time()
            if time.time() - hidden_since >= 10 and time.time() - last_reopen >= 60 and idle_seconds() >= 3:
                last_reopen = time.time()
                try:
                    hh = L.find_main()
                    if hh and win32gui.IsIconic(hh):
                        unminimize_quietly(hh)
                    elif hh:
                        reopen_from_tray(hh)
                except Exception:
                    log('reopen error', traceback.format_exc())
        else:
            hidden_since = None
        if conf.get('auto_reopen', True) and feed.get('status') == 'ok' and time.time() - last_tall >= 60 and os.path.exists(HIDDEN):
            last_tall = time.time()
            try:
                hh = L.find_main()
                if hh and not win32gui.IsIconic(hh):
                    ensure_tall(hh, L.dpi_scale(hh))
            except Exception:
                log('heighten error', traceback.format_exc())
        try:
            r = scan(fix_scroll=True)
        except Exception as e:
            r = {'status': 'error', 'msg': repr(e)}
            log('scan error', traceback.format_exc())
        feed['hb'] = time.time()
        feed['status'] = r.get('status')
        feed['msg'] = r.get('msg', '')
        seq_at_tick_start = feed['seq']
        if r.get('status') == 'ok':
            feed['total_unread'] = r.get('total_unread')
            cur = {}
            unread_now = []
            for row in r['rows']:
                kind = classify(row, conf)
                key = row['name']
                st = (row['unread'], row['count'], row['preview'])
                cur[key] = st
                if kind not in ('private', 'maybe'):
                    continue
                if row['unread']:
                    unread_now.append({'name': key, 'preview': row['preview'], 'count': row['count'], 'time': row['time']})
                old = last.get(key)
                new_msg = False
                if row['unread'] and (old is None or old[0] is None or old[2] != row['preview'] or
                                      (row['count'] or 0) > (old[1] or 0)):
                    new_msg = True
                # 正打开着的私聊：没有红点，但预览变了
                if row['selected'] and old is not None and old[2] != row['preview'] and row['preview'] and r.get('last_mine') is False:
                    new_msg = True
                if new_msg and not first:
                    feed['seq'] += 1
                    ev = {'seq': feed['seq'], 'ts': time.time(), 'name': key, 'preview': row['preview'],
                          'count': row['count'], 'time': row['time'], 'open': row['selected'], 'maybe_group': kind == 'maybe'}
                    feed['events'].append(ev)
                    log('event', json.dumps(ev, ensure_ascii=False))
                elif new_msg and first and row['unread']:
                    # 启动时已经存在的未读，也提示一次
                    feed['seq'] += 1
                    feed['events'].append({'seq': feed['seq'], 'ts': time.time(), 'name': key, 'preview': row['preview'],
                                           'count': row['count'], 'time': row['time'], 'open': False, 'startup': True})
            # 兜底：左侧“聊天”图标上的未读总数涨了，但可见的各行都没变化（列表被滚动过，新消息那行不在可见范围）
            tot = r.get('total_unread')
            changed_any = any(last.get(k) != v for k, v in cur.items())
            # 要连续两次（约 8 秒）都找不到才提醒：中间那次通常已经滚回顶部找到了；用户正在用微信时不提醒
            wx_fg = win32gui.GetForegroundWindow() == L.find_main()
            rose = (not first and isinstance(tot, int) and isinstance(last_total, int) and tot > last_total)
            new_private = feed['seq'] > seq_at_tick_start
            if off_pending is None:
                if rose and not changed_any and not new_private and not wx_fg:
                    off_pending = (last_total, tot)
            else:
                base, _ = off_pending
                off_pending = None
                if not new_private and not changed_any and not wx_fg and isinstance(tot, int) and tot > base:
                    feed['seq'] += 1
                    ev = {'seq': feed['seq'], 'ts': time.time(), 'name': '（列表里没看到）',
                          'preview': '微信未读数从 %d 变成 %d，新消息不在会话列表的可见范围内' % (base, tot),
                          'count': tot - base, 'time': '', 'open': False, 'offscreen': True}
                    feed['events'].append(ev)
                    log('event', json.dumps(ev, ensure_ascii=False))
            if isinstance(tot, int) and tot >= 0:
                last_total = tot
            feed['unread'] = unread_now
            # 不在当前可见列表里的会话保留旧状态（滚出可视区不算“读了”）
            for k, v in cur.items():
                last[k] = v
            first = False
        feed['events'] = feed['events'][-200:]
        try:
            write_feed(feed)
        except Exception:
            log('feed write error', traceback.format_exc())
        time.sleep(interval)


# ---------------------------------------------------------------- 打开聊天 / 发送
def chat_header(h):
    """当前聊天区标题（OCR）。"""
    img = L.capture(h)
    lay = Layout(img, L.dpi_scale(h))
    s = lay.s
    t = L.ocr(img, (lay.list_right + int(8 * s), int(30 * s), lay.W - int(150 * s), int(80 * s)), up=1)
    t = [x for x in t if x[1] < 75 * s]
    return ''.join(x[4] for x in sorted(t, key=lambda x: x[0])).strip(), img, lay


def same_name(a, b):
    def k(x):
        return re.sub(r'[\s…\.·]', '', x)
    return k(a) == k(b)


def popup_windows(h):
    """和主窗口同进程、新出现的可见顶层窗口（搜索弹窗类名 Qt…ToolSaveBits）。"""
    import win32process
    _, pid = win32process.GetWindowThreadProcessId(h)
    res = []
    def cb(x, _):
        try:
            if x != h and win32gui.IsWindowVisible(x) and win32process.GetWindowThreadProcessId(x)[1] == pid \
                    and 'ToolSaveBits' in win32gui.GetClassName(x):
                res.append(x)
        except Exception:
            pass
        return True
    win32gui.EnumWindows(cb, None)
    return res


OK_SECTIONS = ('联系人', '功能', '最常使用', '好友')
SECTION_WORDS = ('联系人', '群聊', '功能', '最常使用', '好友', '聊天记录', '收藏', '公众号', '服务号', '小程序', '视频号',
                 '搜索网络结果', '文章', '企业微信联系人', '朋友圈', '直播', '表情', '音乐', '百科', '问一问', '搜一搜')


def selected_kind(h):
    """打开聊天后，会话列表里高亮那一行的分类（防止误开群聊）。"""
    r = scan(h)
    for row in r.get('rows', []):
        if row['selected']:
            return classify(row, load_conf()), row
    return None, None


_WAS_HIDDEN = False


BUSY = os.path.join(HERE, 'busy.lock')


def busy():
    try:
        return time.time() - os.path.getmtime(BUSY) < 90
    except OSError:
        return False


def open_chat(name):
    """点会话列表上方的放大镜，搜 name，在“联系人/功能/最常使用”里找完全同名的一项点开。
    返回 (ok, 说明, 窗口句柄, 打开前的前台窗口)。"""
    h = L.find_main()
    if not h:
        return False, '没找到微信窗口', 0, 0
    prev = win32gui.GetForegroundWindow()
    open(BUSY, 'w').close()        # 告诉后台识别先停一停
    global _WAS_HIDDEN
    _WAS_HIDDEN = is_hidden(h)
    if _WAS_HIDDEN:
        unhide(h)                 # 托盘模式：先挪回屏幕上才能点；发完再藏回去
        time.sleep(0.3)
    if win32gui.IsIconic(h):
        win32gui.ShowWindow(h, win32con.SW_RESTORE)
        time.sleep(0.6)
    img = L.capture(h)
    lay = Layout(img, L.dpi_scale(h))
    if lay.blank():
        reopen_from_tray(h, to_back=False)
        img = L.capture(h)
        lay = Layout(img, L.dpi_scale(h))
        if lay.blank():
            return False, '微信主窗口被关到托盘了，从托盘自动打开没成功，请手动点开微信', h, prev
    if lay.compact():
        widen(h, lay.s)
        img = L.capture(h)
        lay = Layout(img, L.dpi_scale(h))
        if lay.compact():
            return False, '微信窗口太窄（会话列表被收起了），自动拉宽没成功，请手动拉宽再发', h, prev
    s = lay.s
    title, _, _ = chat_header(h)
    if not L.activate(h):
        return False, '没能把微信切到前台', h, prev
    if not same_name(title, name):
        l, t, r, b = win32gui.GetWindowRect(h)
        before = set(popup_windows(h))
        L.click(l + lay.list_right - 62 * s, t + 55 * s)
        pop = None
        for _ in range(15):
            time.sleep(0.15)
            new = [x for x in popup_windows(h) if x not in before] or popup_windows(h)
            if new:
                pop = new[0]; break
        if not pop:
            return False, '点了搜索按钮，但没看到搜索框弹出来', h, prev
        L.set_clip(name); L.key(win32con.VK_CONTROL, ord('V'))
        time.sleep(1.4)
        pimg = L.capture(pop)
        pl, pt, pr, pb = win32gui.GetWindowRect(pop)
        res = L.ocr(pimg)
        res.sort(key=lambda q: q[1])
        # 第一行是搜索框本身，核对一下确实输进去了
        if not res or not same_name(res[0][4], name):
            L.key(win32con.VK_ESCAPE)
            pimg.save(os.path.join(HERE, 'last_search.png'))
            return False, '搜索框里的字和要找的名字对不上（截图 last_search.png）', h, prev
        sec = None; target = None
        for x, y, w, hh, txt in res[1:]:
            tt = txt.replace(' ', '')
            if tt in SECTION_WORDS or tt.startswith('搜索网络'):
                sec = tt; continue
            if sec in OK_SECTIONS and same_name(tt, name):
                target = (x + w / 2, y + hh / 2); break
        if not target:
            L.key(win32con.VK_ESCAPE)
            pimg.save(os.path.join(HERE, 'last_search.png'))
            return False, '搜索结果的“联系人”里没有名字完全一致的「%s」（截图 last_search.png）' % name, h, prev
        L.click(pl + target[0], pt + target[1])
        time.sleep(1.0)
    title, img, lay = chat_header(h)
    if re.search(r'[\(（]\d+[\)）]$', title):
        return False, '打开的是群聊「%s」，拒绝' % title, h, prev
    if not same_name(title, name):
        return False, '打开的聊天标题是「%s」，和「%s」对不上，已停止' % (title, name), h, prev
    kind, row = selected_kind(h)
    if kind == 'group':
        return False, '「%s」看起来是群聊（会话列表里是群头像/免打扰/带发言人前缀），拒绝；确实是私聊的话：wx private add %s' % (title, title), h, prev
    return True, title, h, prev


def restore_fg(prev):
    if prev:
        try:
            L.key(win32con.VK_MENU)
            win32gui.SetForegroundWindow(prev)
        except Exception:
            pass
    try:
        os.remove(BUSY)
    except OSError:
        pass
    # 发送 / 读取前是托盘模式的，做完藏回去
    global _WAS_HIDDEN
    if _WAS_HIDDEN:
        _WAS_HIDDEN = False
        h = L.find_main()
        if h:
            time.sleep(0.2)
            hide_offscreen(h)


def send(name, text, dry=False):
    conf = load_conf()
    if name in conf['groups']:
        return {'ok': False, 'msg': '「%s」在群聊名单里，不发' % name}
    ok, msg, h, prev = open_chat(name)
    if not ok:
        restore_fg(prev)
        return {'ok': False, 'msg': msg}
    s = L.dpi_scale(h)
    l, t, r, b = win32gui.GetWindowRect(h)
    img = L.capture(h); lay = Layout(img, s)
    # 点一下输入框（聊天区底部），保证焦点在输入框
    ix = l + (lay.list_right + lay.W) / 2
    iy = t + lay.H - 90 * s
    L.click(ix, iy); time.sleep(0.15)
    L.set_clip(text)
    L.key(win32con.VK_CONTROL, ord('V')); time.sleep(0.35)
    if dry:
        img = L.capture(h); img.save(os.path.join(HERE, 'last_send.png'))
        # 草稿模式：把输入框清空，不发送
        L.key(win32con.VK_CONTROL, ord('A')); L.key(win32con.VK_DELETE)
        restore_fg(prev)
        return {'ok': True, 'dry': True, 'msg': '已在「%s」的输入框里试填（未发送，已清空）' % msg}
    L.key(win32con.VK_RETURN); time.sleep(0.9)
    img = L.capture(h); img.save(os.path.join(HERE, 'last_send.png'))
    # 校验：聊天区（标题栏以下、输入框以上）右侧应出现刚发的内容
    lay = Layout(img, s)
    tail = L.ocr(img, (lay.list_right + (lay.W - lay.list_right) * 0.25, int(80 * s), lay.W, lay.H - int(190 * s)))
    seen = re.sub(r'[\W_]', '', ''.join(x[4] for x in tail))
    probe = re.sub(r'[\W_]', '', text)
    restore_fg(prev)
    verified = bool(probe) and (probe[:8] in seen or probe[-8:] in seen)
    return {'ok': True, 'verified': verified, 'to': msg,
            'msg': '已发送给「%s」' % msg + ('' if verified else '（没能在截图里核对到原文，请看 last_send.png）')}


def read_chat(name, n=12):
    ok, msg, h, prev = open_chat(name)
    if not ok:
        restore_fg(prev)
        return {'ok': False, 'msg': msg}
    time.sleep(0.4)
    img = L.capture(h); s = L.dpi_scale(h); lay = Layout(img, s)
    restore_fg(prev)
    x0, x1 = lay.list_right, lay.W
    a = lay.a
    bg = a[int(100 * s), int(x0 + 12 * s)]
    lines = L.ocr(img, (x0, int(80 * s), x1, lay.H - int(190 * s)))
    msgs = []
    for x, y, w, hh, t in sorted(lines, key=lambda q: (q[1], q[0])):
        px = a[int(y + hh / 2), max(int(x0), int(x - 5 * s))]
        if px[1] > 190 and px[1] - px[0] > 40 and px[1] - px[2] > 50:
            who = 'me'
        elif np.abs(px - bg).max() > 5:
            who = 'them'
        else:
            who = 'time'
        if msgs and msgs[-1]['who'] == who and who != 'time' and y - msgs[-1]['y'] < 34 * s:
            msgs[-1]['text'] += ('' if re.search(r'[\u4e00-\u9fff，。！？、]$', msgs[-1]['text']) else ' ') + t
            msgs[-1]['y'] = y
        else:
            msgs.append({'who': who, 'text': t, 'y': y})
    for m in msgs:
        m.pop('y', None)
    return {'ok': True, 'chat': msg, 'messages': msgs[-n:]}


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd = sys.argv[1]
    b = lambda x: base64.b64decode(x).decode('utf-8')
    if cmd == 'scan':
        r = scan()
        conf = load_conf()
        for row in r.get('rows', []):
            row['kind'] = classify(row, conf)
        print(json.dumps(r, ensure_ascii=False))
    elif cmd == 'loop':
        loop(float(sys.argv[2]) if len(sys.argv) > 2 else 4.0)
    elif cmd == 'send':
        print(json.dumps(send(b(sys.argv[2]), b(sys.argv[3]), dry='--dry' in sys.argv), ensure_ascii=False))
    elif cmd == 'read':
        print(json.dumps(read_chat(b(sys.argv[2])), ensure_ascii=False))
    elif cmd == 'show':
        h = L.find_main()
        print(json.dumps({'ok': bool(h and unhide(h, activate=True))}))
    elif cmd == 'hide':
        h = L.find_main()
        r = scan(h)
        if r.get('status') == 'closed':
            reopen_from_tray(h)
        else:
            hide_offscreen(h)
        print(json.dumps({'ok': True}))
    elif cmd == 'shot':
        h = L.find_main(); L.capture(h).save(os.path.join(HERE, 'shot.png')); print(os.path.join(HERE, 'shot.png'))
    else:
        print(__doc__)


if __name__ == '__main__':
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except Exception:
        log('fatal', traceback.format_exc())
        raise
