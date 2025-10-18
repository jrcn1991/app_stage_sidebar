from __future__ import annotations
import ctypes as C
import threading
import collections
from typing import Deque, Dict, List, Tuple
from ctypes import wintypes as W
from PySide6 import QtCore, QtGui
import win32gui, win32con




# ===== DLLs =====
dwmapi   = C.WinDLL("dwmapi",   use_last_error=True)
user32   = C.WinDLL("user32",   use_last_error=True)
gdi32    = C.WinDLL("gdi32",    use_last_error=True)
PTR_BITS = 8 * C.sizeof(C.c_void_p)
PTR_MASK = (1 << PTR_BITS) - 1
def as_void_p(h) -> W.HGDIOBJ:
    try:
        return W.HGDIOBJ(int(h) & PTR_MASK)
    except Exception:
        return W.HGDIOBJ(0)

def safe_DeleteObject(h) -> None:
    try:
        if h:
            gdi32.DeleteObject(as_void_p(h))
    except Exception:
        pass
kernel32 = C.WinDLL("kernel32", use_last_error=True)
shell32  = C.WinDLL("shell32",  use_last_error=True)

# ===== Constantes / Aliases =====
HANDLE = W.HANDLE
HRESULT = W.LONG
ICON_SMALL, ICON_BIG, ICON_SMALL2 = 0, 1, 2
DWMWA_CLOAKED = 14
DWM_TNP_RECTDESTINATION = 0x1
DWM_TNP_VISIBLE = 0x8
DWM_TNP_OPACITY = 0x4
DWM_TNP_SOURCECLIENTAREAONLY = 0x10
EVENT_SYSTEM_MINIMIZESTART = 0x0016
EVENT_SYSTEM_MINIMIZEEND   = 0x0017
EVENT_OBJECT_DESTROY       = 0x8001
EVENT_OBJECT_SHOW          = 0x8002
EVENT_OBJECT_HIDE          = 0x8003
WINEVENT_OUTOFCONTEXT      = 0x0
WINEVENT_SKIPOWNPROCESS    = 0x2
MONITOR_DEFAULTTONEAREST   = 2

# AppBar
ABM_NEW=0; ABM_REMOVE=1; ABM_QUERYPOS=2; ABM_SETPOS=3
ABN_POSCHANGED=1
ABE_LEFT=0; ABE_RIGHT=2

EXCLUDED_CLASSES = {"Shell_TrayWnd", "Shell_SecondaryTrayWnd", "Progman", "WorkerW"}

# ===== Helpers =====
def norm(h) -> int:
    return int(h) & ((1 << (64 if C.sizeof(C.c_void_p) == 8 else 32)) - 1)

# ===== Structs =====
class RECT(C.Structure):
    _fields_ = [("left", W.LONG), ("top", W.LONG), ("right", W.LONG), ("bottom", W.LONG)]

class DWM_THUMBNAIL_PROPERTIES(C.Structure):
    _fields_ = [
        ("dwFlags", W.DWORD), ("rcDestination", RECT), ("rcSource", RECT),
        ("opacity", W.BYTE), ("fVisible", W.BOOL), ("fSourceClientAreaOnly", W.BOOL)
    ]

class ICONINFO(C.Structure):
    _fields_ = [("fIcon", W.BOOL), ("xHotspot", W.DWORD), ("yHotspot", W.DWORD), ("hbmMask", W.HBITMAP), ("hbmColor", W.HBITMAP)]

class BITMAP(C.Structure):
    _fields_ = [("bmType", W.LONG), ("bmWidth", W.LONG), ("bmHeight", W.LONG), ("bmWidthBytes", W.LONG), ("bmPlanes", W.WORD), ("bmBitsPixel", W.WORD), ("bmBits", C.c_void_p)]

class BITMAPINFOHEADER(C.Structure):
    _fields_ = [
        ("biSize", W.DWORD), ("biWidth", W.LONG), ("biHeight", W.LONG), ("biPlanes", W.WORD), ("biBitCount", W.WORD),
        ("biCompression", W.DWORD), ("biSizeImage", W.DWORD), ("biXPelsPerMeter", W.LONG), ("biYPelsPerMeter", W.LONG),
        ("biClrUsed", W.DWORD), ("biClrImportant", W.DWORD)
    ]

class RGBQUAD(C.Structure):
    _fields_ = [("rgbBlue", W.BYTE), ("rgbGreen", W.BYTE), ("rgbRed", W.BYTE), ("rgbReserved", W.BYTE)]

class BITMAPINFO(C.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", RGBQUAD * 1)]

class SHFILEINFO(C.Structure):
    _fields_ = [("hIcon", W.HICON), ("iIcon", C.c_int), ("dwAttributes", W.DWORD), ("szDisplayName", W.WCHAR * 260), ("szTypeName", W.WCHAR * 80)]

class MONITORINFOEXW(C.Structure):
    _fields_ = [("cbSize", W.DWORD), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", W.DWORD), ("szDevice", W.WCHAR * 32)]

class APPBARDATA(C.Structure):
    _fields_ = [("cbSize", W.DWORD), ("hWnd", W.HWND), ("uCallbackMessage", W.UINT), ("uEdge", W.UINT), ("rc", RECT), ("lParam", C.c_long)]

class MSG(C.Structure):
    _fields_ = [("hwnd", W.HWND), ("message", W.UINT), ("wParam", W.WPARAM), ("lParam", W.LPARAM), ("time", W.DWORD), ("pt", W.POINT)]

# ===== Prototipagem =====
WINEVENTPROC   = C.WINFUNCTYPE(None, HANDLE, W.DWORD, W.HWND, W.LONG, W.LONG, W.DWORD, W.DWORD)
MONITORENUMPROC= C.WINFUNCTYPE(C.c_int, W.HMONITOR, W.HDC, C.POINTER(RECT), C.c_long)

DwmIsCompositionEnabled         = dwmapi.DwmIsCompositionEnabled;         DwmIsCompositionEnabled.argtypes         = [C.POINTER(W.BOOL)]
DwmIsCompositionEnabled.restype = W.LONG
DwmGetWindowAttribute           = dwmapi.DwmGetWindowAttribute;           DwmGetWindowAttribute.argtypes           = [W.HWND, W.DWORD, C.c_void_p, W.DWORD]
DwmGetWindowAttribute.restype   = W.LONG
DwmRegisterThumbnail            = dwmapi.DwmRegisterThumbnail;            DwmRegisterThumbnail.argtypes            = [W.HWND, W.HWND, C.POINTER(HANDLE)]
DwmRegisterThumbnail.restype    = W.LONG
DwmUnregisterThumbnail          = dwmapi.DwmUnregisterThumbnail;          DwmUnregisterThumbnail.argtypes          = [HANDLE]
DwmUnregisterThumbnail.restype  = W.LONG
DwmUpdateThumbnailProperties    = dwmapi.DwmUpdateThumbnailProperties;    DwmUpdateThumbnailProperties.argtypes    = [HANDLE, C.POINTER(DWM_THUMBNAIL_PROPERTIES)]
DwmUpdateThumbnailProperties.restype = W.LONG

GetIconInfo     = user32.GetIconInfo;               GetIconInfo.argtypes     = [W.HICON, C.POINTER(ICONINFO)];           GetIconInfo.restype     = W.BOOL
GetObjectW      = gdi32.GetObjectW;                 GetObjectW.argtypes      = [W.HGDIOBJ, C.c_int, C.c_void_p];         GetObjectW.restype      = C.c_int
CreateDIBSection= gdi32.CreateDIBSection;           CreateDIBSection.argtypes= [W.HDC, C.POINTER(BITMAPINFO), W.UINT, C.POINTER(C.c_void_p), W.HANDLE, W.DWORD]
CreateDIBSection.restype = W.HBITMAP

GetWindowThreadProcessId = user32.GetWindowThreadProcessId; GetWindowThreadProcessId.argtypes = [W.HWND, C.POINTER(W.DWORD)]
GetWindowThreadProcessId.restype = W.DWORD
OpenProcess               = kernel32.OpenProcess;           OpenProcess.argtypes               = [W.DWORD, W.BOOL, W.DWORD]
OpenProcess.restype = W.HANDLE
CloseHandle               = kernel32.CloseHandle;           CloseHandle.argtypes               = [HANDLE]; CloseHandle.restype = W.BOOL
QueryFullProcessImageNameW= kernel32.QueryFullProcessImageNameW; QueryFullProcessImageNameW.argtypes = [HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)]
QueryFullProcessImageNameW.restype = W.BOOL

SHGetFileInfoW = shell32.SHGetFileInfoW; SHGetFileInfoW.argtypes = [W.LPCWSTR, W.DWORD, C.POINTER(SHFILEINFO), W.UINT, W.UINT]; SHGetFileInfoW.restype = W.DWORD
SHAppBarMessage= shell32.SHAppBarMessage; SHAppBarMessage.argtypes = [W.DWORD, C.POINTER(APPBARDATA)]; SHAppBarMessage.restype = W.UINT

SetWinEventHook = user32.SetWinEventHook; SetWinEventHook.argtypes = [W.DWORD, W.DWORD, W.HMODULE, WINEVENTPROC, W.DWORD, W.DWORD, W.DWORD]
SetWinEventHook.restype = HANDLE
UnhookWinEvent  = user32.UnhookWinEvent;  UnhookWinEvent.argtypes  = [HANDLE]; UnhookWinEvent.restype = W.BOOL

EnumDisplayMonitors = user32.EnumDisplayMonitors; EnumDisplayMonitors.argtypes = [W.HDC, C.c_void_p, MONITORENUMPROC, C.c_long]
EnumDisplayMonitors.restype = W.BOOL
MonitorFromRect      = user32.MonitorFromRect;      MonitorFromRect.argtypes      = [C.POINTER(RECT), W.DWORD]; MonitorFromRect.restype = W.HMONITOR
GetMonitorInfoW      = user32.GetMonitorInfoW;      GetMonitorInfoW.argtypes      = [W.HMONITOR, C.POINTER(MONITORINFOEXW)]; GetMonitorInfoW.restype = W.BOOL

# ===== Window utils =====
def is_cloaked(hwnd: int) -> bool:
    v = W.DWORD()
    hr = DwmGetWindowAttribute(hwnd, 14, C.byref(v), C.sizeof(v))
    return False if hr != 0 else v.value != 0

def get_title(hwnd: int) -> str:
    try:
        return win32gui.GetWindowText(hwnd)
    except Exception:
        return ""

def is_top_level(hwnd: int) -> bool:
    try:
        if win32gui.GetParent(hwnd):
            return False
        ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if ex & win32con.WS_EX_TOOLWINDOW:
            return False
        cls = win32gui.GetClassName(hwnd)
        if cls in EXCLUDED_CLASSES:
            return False
        if is_cloaked(hwnd):
            return False
        if not get_title(hwnd).strip():
            return False
        return True
    except Exception:
        return False

def get_exe_from_hwnd(hwnd: int) -> str:
    pid = W.DWORD(0)
    GetWindowThreadProcessId(hwnd, C.byref(pid))
    if not pid.value:
        return ""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not h:
        return ""
    try:
        size = W.DWORD(32768)
        buf = C.create_unicode_buffer(size.value)
        ok = QueryFullProcessImageNameW(h, 0, buf, C.byref(size))
        return buf.value if ok else ""
    finally:
        CloseHandle(h)

def shget_icon(path: str, small: bool = True) -> Tuple[int, bool]:
    if not path:
        return 0, False
    sfi = SHFILEINFO()
    SHGFI_ICON = 0x100
    SHGFI_SMALLICON = 0x1
    flags = SHGFI_ICON | (SHGFI_SMALLICON if small else 0)
    if SHGetFileInfoW(path, 0, C.byref(sfi), C.sizeof(sfi), flags):
        return norm(sfi.hIcon), True
    return 0, False

def get_icon_handle(hwnd: int) -> Tuple[int, bool]:
    for wp in (ICON_SMALL2, ICON_SMALL, ICON_BIG):
        h = win32gui.SendMessage(hwnd, win32con.WM_GETICON, wp, 0)
        if h:
            return norm(h), False
    try:
        h = (win32gui.GetClassLongPtr(hwnd, win32con.GCLP_HICONSM) or win32gui.GetClassLongPtr(hwnd, win32con.GCLP_HICON))
        if h:
            return norm(h), False
    except AttributeError:
        h = (win32gui.GetClassLong(hwnd, win32con.GCL_HICONSM) or win32gui.GetClassLong(hwnd, win32con.GCL_HICON))
        if h:
            return norm(h), False
    exe = get_exe_from_hwnd(hwnd)
    h, own = shget_icon(exe, True)
    if h:
        return h, own
    h, own = shget_icon(exe, False)
    return h, own

def hicon_to_qpixmap(hicon: int, prefer: int = 24) -> QtGui.QPixmap:
    if not hicon:
        return QtGui.QPixmap()
    ii = ICONINFO()
    w = h = prefer
    if user32.GetIconInfo(W.HICON(int(hicon)), C.byref(ii)):
        try:
            bmp = BITMAP()
            if gdi32.GetObjectW(ii.hbmColor, C.sizeof(bmp), C.byref(bmp)):
                w, h = bmp.bmWidth, bmp.bmHeight
        finally:
            # Liberação segura evitando OverflowError
            if ii.hbmMask:
                safe_DeleteObject(ii.hbmMask)
            if ii.hbmColor:
                safe_DeleteObject(ii.hbmColor)
    w = max(16, min(64, w)); h = max(16, min(64, h))
    hdc_screen = win32gui.GetDC(0)
    hdc_mem = win32gui.CreateCompatibleDC(hdc_screen)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = C.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h  # top-down
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = win32con.BI_RGB

    bits = C.c_void_p()
    hbm = gdi32.CreateDIBSection(hdc_screen, C.byref(bmi), win32con.DIB_RGB_COLORS, C.byref(bits), None, 0)
    old = win32gui.SelectObject(hdc_mem, hbm)
    try:
        C.memset(bits, 0, w * h * 4)
        win32gui.DrawIconEx(hdc_mem, 0, 0, int(hicon), w, h, 0, 0, win32con.DI_NORMAL)
        buf = (C.c_ubyte * (w * h * 4)).from_address(bits.value)
        qimg = QtGui.QImage(buf, w, h, w * 4, QtGui.QImage.Format.Format_ARGB32)
        return QtGui.QPixmap.fromImage(qimg.copy())
    finally:
        win32gui.SelectObject(hdc_mem, old)
        win32gui.DeleteObject(hbm)
        win32gui.DeleteDC(hdc_mem)
        win32gui.ReleaseDC(0, hdc_screen)


# ===== Monitores =====
def enum_monitors() -> List[Dict]:
    res: List[Dict] = []

    @MONITORENUMPROC
    def cb(hMon, hdc, prc, lp):
        mi = MONITORINFOEXW(); mi.cbSize = C.sizeof(MONITORINFOEXW)
        if GetMonitorInfoW(hMon, C.byref(mi)):
            res.append({"hmon": hMon, "rect": (mi.rcMonitor.left, mi.rcMonitor.top, mi.rcMonitor.right, mi.rcMonitor.bottom)})
        return 1

    EnumDisplayMonitors(0, None, cb, 0)
    return res

def monitor_index_for_hwnd(hwnd: int, monitors: List[Dict]) -> int:
    try:
        wp = win32gui.GetWindowPlacement(hwnd)
        l, t, r, b = wp[4]
        rc = RECT(l, t, r, b)
    except Exception:
        try:
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            rc = RECT(l, t, r, b)
        except Exception:
            return -1
    hmon = MonitorFromRect(C.byref(rc), MONITOR_DEFAULTTONEAREST)
    for i, m in enumerate(monitors):
        if m["hmon"] == hmon:
            return i
    return -1

def list_minimized_windows() -> List[int]:
    out: List[int] = []

    def cb(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            if not win32gui.IsIconic(hwnd):
                return True
            if not is_top_level(hwnd):
                return True
            out.append(hwnd)
        except Exception:
            pass
        return True

    win32gui.EnumWindows(cb, None)
    return out

# ===== Layout helpers =====
class TileSpec:
    TITLE_H = 26  # altura da barra de título

    @staticmethod
    def titleRect(w: int, h: int) -> QtCore.QRect:
        return QtCore.QRect(0, 0, w, TileSpec.TITLE_H)

    @staticmethod
    def closeRect(w: int, h: int) -> QtCore.QRect:
        return QtCore.QRect(w - 24 - 6, (TileSpec.TITLE_H - 18) // 2, 24, 18)

# ===== WinEvent hook (único) =====
Event = collections.namedtuple("Event", "type hwnd")
queue: Deque[Event] = collections.deque()
q_lock = threading.Lock()

@WINEVENTPROC
def _winevent_cb(hook, evt, hwnd, idObj, idChild, thr, ts):
    if idObj != 0 or hwnd == 0:
        return
    if evt in (EVENT_SYSTEM_MINIMIZESTART, EVENT_SYSTEM_MINIMIZEEND, EVENT_OBJECT_DESTROY, EVENT_OBJECT_HIDE, EVENT_OBJECT_SHOW):
        with q_lock:
            queue.append(Event(evt, hwnd))

def start_winevent_hook():
    return SetWinEventHook(EVENT_SYSTEM_MINIMIZESTART, EVENT_OBJECT_HIDE, 0, _winevent_cb, 0, 0, WINEVENT_OUTOFCONTEXT | WINEVENT_SKIPOWNPROCESS)

# ===== AppBar helpers =====
def register_appbar(hwnd: int, cb_msg: int) -> None:
    abd = APPBARDATA(); abd.cbSize = C.sizeof(APPBARDATA); abd.hWnd = W.HWND(hwnd); abd.uCallbackMessage = cb_msg
    SHAppBarMessage(ABM_NEW, C.byref(abd))

def remove_appbar(hwnd: int) -> None:
    abd = APPBARDATA(); abd.cbSize = C.sizeof(APPBARDATA); abd.hWnd = W.HWND(hwnd)
    SHAppBarMessage(ABM_REMOVE, C.byref(abd))

def set_appbar_pos(hwnd: int, edge: int, rc: RECT) -> RECT:
    abd = APPBARDATA(); abd.cbSize = C.sizeof(APPBARDATA); abd.hWnd = W.HWND(hwnd); abd.uEdge = edge; abd.rc = rc
    SHAppBarMessage(ABM_QUERYPOS, C.byref(abd))
    if edge == ABE_LEFT:
        abd.rc.right = abd.rc.left + (rc.right - rc.left)
    elif edge == ABE_RIGHT:
        abd.rc.left = abd.rc.right - (rc.right - rc.left)
    SHAppBarMessage(ABM_SETPOS, C.byref(abd))
    return abd.rc
