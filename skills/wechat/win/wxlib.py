# wxlib — 微信 4.x（Weixin.exe）窗口截图 / OCR / 键鼠 的底层工具（在用户 Windows 电脑上运行）
import ctypes, time, re
from ctypes import wintypes
import numpy as np
import win32gui, win32ui, win32con, win32clipboard, win32process, win32api
from PIL import Image

user32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    user32.SetProcessDPIAware()


def find_main():
    """微信主窗口句柄（类名 Qt…QWindowIcon、标题 微信/Weixin）。找不到返回 0。"""
    res = []
    def cb(h, _):
        try:
            c = win32gui.GetClassName(h)
            if win32gui.GetWindowText(h) in ('微信', 'Weixin', 'WeChat') and c.startswith(('Qt', 'mmui')) \
                    and 'ToolSaveBits' not in c and 'Tray' not in c:
                _, pid = win32process.GetWindowThreadProcessId(h)
                res.append(h)
        except Exception:
            pass
        return True
    win32gui.EnumWindows(cb, None)
    vis = [h for h in res if win32gui.IsWindowVisible(h)]
    return (vis or res or [0])[0]


def dpi_scale(h):
    try:
        return user32.GetDpiForWindow(h) / 96.0
    except Exception:
        return 1.0


def capture(h):
    """PrintWindow 截整个窗口（被遮挡也能截；最小化/隐藏时截不到）。返回 RGB PIL.Image。"""
    l, t, r, b = win32gui.GetWindowRect(h)
    w, hh = r - l, b - t
    hdc = win32gui.GetWindowDC(h)
    dc = win32ui.CreateDCFromHandle(hdc)
    mdc = dc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(dc, w, hh)
    mdc.SelectObject(bmp)
    user32.PrintWindow(h, mdc.GetSafeHdc(), 2)
    info = bmp.GetInfo()
    img = Image.frombuffer('RGB', (info['bmWidth'], info['bmHeight']), bmp.GetBitmapBits(True), 'raw', 'BGRX', 0, 1)
    win32gui.DeleteObject(bmp.GetHandle()); mdc.DeleteDC(); dc.DeleteDC(); win32gui.ReleaseDC(h, hdc)
    return img


_ENG = None


def engine():
    global _ENG
    if _ENG is None:
        from rapidocr_onnxruntime import RapidOCR
        _ENG = RapidOCR()
    return _ENG


def ocr(img, box=None, up=1):
    """检测+识别（RapidOCR）。box=(x0,y0,x1,y1)。返回 [(x,y,w,h,text)]，坐标是原图坐标。约 1~3 秒。"""
    ox = oy = 0
    if box:
        box = tuple(int(v) for v in box)
        img = img.crop(box); ox, oy = box[0], box[1]
    if up != 1:
        img = img.resize((int(img.width * up), int(img.height * up)), Image.LANCZOS)
    res, _ = engine()(np.asarray(img.convert('RGB')))
    out = []
    for b, t, sc in res or []:
        xs = [p[0] for p in b]; ys = [p[1] for p in b]
        out.append((ox + min(xs) / up, oy + min(ys) / up, (max(xs) - min(xs)) / up, (max(ys) - min(ys)) / up, t.replace('\u3000', ' ')))
    return out


_REC_CACHE = {}


def rec_line(img, box):
    """只识别一行字（不做检测，约 20 毫秒），结果按像素内容缓存。返回 (文字, 置信度)。"""
    box = tuple(int(v) for v in box)
    c = img.crop(box)
    key = hash(c.tobytes())
    if key in _REC_CACHE:
        return _REC_CACHE[key]
    a = np.asarray(c.convert('RGB'))
    if a.size == 0 or np.ptp(a) < 25:
        r = ('', 1.0)
    else:
        res, _ = engine()(a, use_det=False, use_cls=False)
        r = (res[0][0].replace('\u3000', ' ').strip(), float(res[0][1])) if res else ('', 0.0)
    if len(_REC_CACHE) > 3000:
        _REC_CACHE.clear()
    _REC_CACHE[key] = r
    return r


# ---------- 键鼠 ----------
def set_clip(text):
    for _ in range(5):
        try:
            win32clipboard.OpenClipboard(); break
        except Exception:
            time.sleep(0.1)
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
    finally:
        win32clipboard.CloseClipboard()


def get_clip():
    try:
        win32clipboard.OpenClipboard()
        try:
            return win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        finally:
            win32clipboard.CloseClipboard()
    except Exception:
        return None


def key(*vks, up_delay=0.03):
    """按下一组键（组合键），再倒序松开。"""
    for v in vks:
        win32api.keybd_event(v, 0, 0, 0); time.sleep(0.02)
    time.sleep(up_delay)
    for v in reversed(vks):
        win32api.keybd_event(v, 0, win32con.KEYEVENTF_KEYUP, 0); time.sleep(0.02)


def click(x, y):
    user32.SetCursorPos(int(x), int(y)); time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0); time.sleep(0.04)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)


def activate(h):
    if win32gui.IsIconic(h):
        win32gui.ShowWindow(h, win32con.SW_RESTORE)
    else:
        win32gui.ShowWindow(h, win32con.SW_SHOW)
    for _ in range(3):
        key(win32con.VK_MENU)          # Alt 轻按一下，绕过前台锁
        try:
            win32gui.SetForegroundWindow(h)
        except Exception:
            pass
        time.sleep(0.25)
        if win32gui.GetForegroundWindow() == h:
            return True
    return win32gui.GetForegroundWindow() == h


def rec_badge(img, box):
    """红底白字的未读数：转灰度反色、放大 3 倍再识别。返回整数或 None。"""
    from PIL import ImageOps
    box = tuple(int(v) for v in box)
    c = img.crop(box)
    key = ('badge', hash(c.tobytes()))
    if key not in _REC_CACHE:
        g = ImageOps.invert(c.convert('L')).convert('RGB').resize((c.width * 3, c.height * 3), Image.LANCZOS)
        res, _ = engine()(np.asarray(g), use_det=False, use_cls=False)
        d = re.sub(r'\D', '', res[0][0]) if res else ''
        _REC_CACHE[key] = int(d) if d else None
    return _REC_CACHE[key]
