# -*- coding: utf-8 -*-
# main.py — Sidebar com thumbs DWM de janelas minimizadas
from __future__ import annotations
import sys, threading, collections, ctypes as C
from ctypes import wintypes as W
from typing import Deque, Dict, List

from PySide6 import QtCore, QtGui, QtWidgets
import win32gui, win32con

# ===== WinAPI =====
dwmapi = C.WinDLL("dwmapi", use_last_error=True)
user32 = C.WinDLL("user32", use_last_error=True)

HANDLE=W.HANDLE; HRESULT=W.LONG
DWM_TNP_RECTDESTINATION=0x1; DWM_TNP_VISIBLE=0x8; DWM_TNP_OPACITY=0x4; DWM_TNP_SOURCECLIENTAREAONLY=0x10
EVENT_SYSTEM_MINIMIZESTART=0x0016; EVENT_SYSTEM_MINIMIZEEND=0x0017
EVENT_OBJECT_DESTROY=0x8001; EVENT_OBJECT_SHOW=0x8002; EVENT_OBJECT_HIDE=0x8003
WINEVENT_OUTOFCONTEXT=0x0; WINEVENT_SKIPOWNPROCESS=0x2
DWMWA_CLOAKED=14
EXCLUDED_CLASSES={"Shell_TrayWnd","Shell_SecondaryTrayWnd","Progman","WorkerW"}

class RECT(C.Structure): _fields_=[("left",W.LONG),("top",W.LONG),("right",W.LONG),("bottom",W.LONG)]
class DWM_THUMBNAIL_PROPERTIES(C.Structure):
    _fields_=[("dwFlags",W.DWORD),("rcDestination",RECT),("rcSource",RECT),
              ("opacity",W.BYTE),("fVisible",W.BOOL),("fSourceClientAreaOnly",W.BOOL)]

DwmIsCompositionEnabled=dwmapi.DwmIsCompositionEnabled; DwmIsCompositionEnabled.argtypes=[C.POINTER(W.BOOL)]; DwmIsCompositionEnabled.restype=W.LONG
DwmGetWindowAttribute=dwmapi.DwmGetWindowAttribute; DwmGetWindowAttribute.argtypes=[W.HWND,W.DWORD,C.c_void_p,W.DWORD]; DwmGetWindowAttribute.restype=W.LONG
DwmRegisterThumbnail=dwmapi.DwmRegisterThumbnail; DwmRegisterThumbnail.argtypes=[W.HWND,W.HWND,C.POINTER(HANDLE)]; DwmRegisterThumbnail.restype=W.LONG
DwmUnregisterThumbnail=dwmapi.DwmUnregisterThumbnail; DwmUnregisterThumbnail.argtypes=[HANDLE]; DwmUnregisterThumbnail.restype=W.LONG
DwmUpdateThumbnailProperties=dwmapi.DwmUpdateThumbnailProperties; DwmUpdateThumbnailProperties.argtypes=[HANDLE,C.POINTER(DWM_THUMBNAIL_PROPERTIES)]; DwmUpdateThumbnailProperties.restype=W.LONG

WINEVENTPROC=C.WINFUNCTYPE(None, HANDLE, W.DWORD, W.HWND, W.LONG, W.LONG, W.DWORD, W.DWORD)
SetWinEventHook=user32.SetWinEventHook; SetWinEventHook.argtypes=[W.DWORD,W.DWORD,W.HMODULE,WINEVENTPROC,W.DWORD,W.DWORD,W.DWORD]; SetWinEventHook.restype=HANDLE
UnhookWinEvent=user32.UnhookWinEvent; UnhookWinEvent.argtypes=[HANDLE]; UnhookWinEvent.restype=W.BOOL

def is_cloaked(hwnd:int)->bool:
    v=W.DWORD()
    hr=DwmGetWindowAttribute(W.HWND(int(hwnd)), DWMWA_CLOAKED, C.byref(v), C.sizeof(v))
    return False if hr!=0 else bool(v.value)

def is_top_level(hwnd:int)->bool:
    try:
        if win32gui.GetParent(hwnd): return False
        ex=win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        if ex & win32con.WS_EX_TOOLWINDOW: return False
        cls=win32gui.GetClassName(hwnd)
        if cls in EXCLUDED_CLASSES: return False
        if is_cloaked(hwnd): return False
        title=win32gui.GetWindowText(hwnd)
        if not title.strip(): return False
        return True
    except Exception:
        return False

def list_minimized_windows()->List[int]:
    out=[]
    def cb(h,_):
        try:
            if not win32gui.IsWindowVisible(h): return True
            if not win32gui.IsIconic(h): return True
            if not is_top_level(h): return True
            out.append(h)
        except Exception: pass
        return True
    win32gui.EnumWindows(cb,None)
    return out

class TileSpec:
    TITLE_H=26
    @staticmethod
    def titleRect(w:int,h:int)->QtCore.QRect: return QtCore.QRect(0,0,w,TileSpec.TITLE_H)
    @staticmethod
    def closeRect(w:int,h:int)->QtCore.QRect: return QtCore.QRect(w-30,(TileSpec.TITLE_H-18)//2,24,18)

TITLE_GAP=2

class TileWidget(QtWidgets.QWidget):
    clicked=QtCore.Signal(int)
    closeClicked=QtCore.Signal(int)
    def __init__(self, parent, hwnd:int, title:str):
        super().__init__(parent)
        self.hwnd=hwnd; self.title=title; self.hover=False
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
    def setTitle(self,t:str): self.title=t; self.update()
    def paintEvent(self,_):
        p=QtGui.QPainter(self); p.setRenderHint(QtGui.QPainter.Antialiasing)
        tr=TileSpec.titleRect(self.width(), self.height())
        p.fillRect(tr, QtGui.QColor(0,0,0,120))
        p.setPen(QtGui.QColor(255,255,255))
        p.drawText(tr.adjusted(10,0,-36,0), QtCore.Qt.AlignVCenter|QtCore.Qt.AlignLeft, self.title or "")
        if self.hover:
            r=QtCore.QRect(4, TileSpec.TITLE_H+TITLE_GAP, self.width()-8, max(0,self.height()-(TileSpec.TITLE_H+TITLE_GAP)-6))
            if r.height()>0:
                p.fillRect(r, QtGui.QColor(255,255,255,28))
                pen=QtGui.QPen(QtGui.QColor(0,255,0,200)); pen.setWidth(2); p.setPen(pen); p.drawRect(r.adjusted(0,0,-1,-1))
            cr=TileSpec.closeRect(self.width(), self.height())
            c=cr.center(); r=min(cr.width(),cr.height())//2-2
            p.setPen(QtCore.Qt.NoPen); p.setBrush(QtGui.QColor(255,255,255)); p.drawEllipse(c,r,r)
            pen_x=QtGui.QPen(QtGui.QColor(220,50,47),2); pen_x.setCapStyle(QtCore.Qt.RoundCap); p.setPen(pen_x)
            inner=int(r*0.6); p.drawLine(c+QtCore.QPoint(-inner,-inner), c+QtCore.QPoint(inner,inner)); p.drawLine(c+QtCore.QPoint(-inner, inner), c+QtCore.QPoint(inner,-inner))
        p.end()
    def enterEvent(self,_): self.hover=True; self.update()
    def leaveEvent(self,_): self.hover=False; self.update()
    def mousePressEvent(self,e:QtGui.QMouseEvent):
        if e.button()!=QtCore.Qt.LeftButton: return
        if TileSpec.closeRect(self.width(), self.height()).adjusted(-4,-4,4,4).contains(e.position().toPoint()):
            self.closeClicked.emit(self.hwnd)
        else:
            self.clicked.emit(self.hwnd)

Event=collections.namedtuple("Event","type hwnd")
queue:Deque[Event]=collections.deque()
q_lock=threading.Lock()

@WINEVENTPROC
def _winevent_cb(hook, evt, hwnd, idObj, idChild, thr, ts):
    if idObj!=0 or hwnd==0: return
    if evt in (EVENT_SYSTEM_MINIMIZESTART, EVENT_SYSTEM_MINIMIZEEND, EVENT_OBJECT_DESTROY, EVENT_OBJECT_HIDE, EVENT_OBJECT_SHOW):
        with q_lock: queue.append(Event(evt, hwnd))

class Sidebar(QtWidgets.QMainWindow):
    item_width:int = 220
    item_height:int = 140
    gap_px:int = 8
    bar_width:int = 260
    visible_count:int = 6
    opacity:int = 255

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stage Sidebar")
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        # CORREÇÃO: lista, não dict
        self.items: List[Dict] = []             # <<<<<< FIX
        self.thumbs: Dict[int,HANDLE] = {}
        self.start_index=0

        self.canvas=QtWidgets.QWidget(self); self.setCentralWidget(self.canvas)
        self.canvas.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.tiles: List[TileWidget] = []

        self.enabled=self.check_dwm()

        g=QtWidgets.QApplication.primaryScreen().availableGeometry()
        h=int(g.height()*0.8); top=g.top()+int((g.height()-h)/2)
        self.setGeometry(g.left(), top, self.bar_width, h)

        self.make_tray()
        self.hook=SetWinEventHook(EVENT_SYSTEM_MINIMIZESTART, EVENT_OBJECT_HIDE, 0, _winevent_cb, 0,0, WINEVENT_OUTOFCONTEXT|WINEVENT_SKIPOWNPROCESS)

        self.t_ev=QtCore.QTimer(self); self.t_ev.setInterval(120); self.t_ev.timeout.connect(self.process_events); self.t_ev.start()
        self.t_scan=QtCore.QTimer(self); self.t_scan.setInterval(1000); self.t_scan.timeout.connect(self.reconcile); self.t_scan.start()

        self.show()
        QtCore.QTimer.singleShot(150, self.reconcile)

    def check_dwm(self)->bool:
        b=W.BOOL(); hr=DwmIsCompositionEnabled(C.byref(b)); return hr==0 and bool(b.value)

    def ensure_thumb(self, hwnd:int)->HANDLE|None:
        if hwnd in self.thumbs: return self.thumbs.get(hwnd)
        th=HANDLE(); hr=DwmRegisterThumbnail(W.HWND(int(self.winId())), W.HWND(int(hwnd)), C.byref(th))
        if hr==0 and th: self.thumbs[hwnd]=th; return th
        return None

    def drop_thumb(self, hwnd:int)->None:
        th=self.thumbs.pop(hwnd, None)
        if th:
            try: DwmUnregisterThumbnail(th)
            except Exception: pass

    def add_item(self, hwnd:int)->None:
        if any(x["src_hwnd"]==hwnd for x in self.items): return
        title=win32gui.GetWindowText(hwnd)
        if not title: return
        self.items.append({"src_hwnd":hwnd,"title":title})
        self.layout_visible_tiles()

    def remove_item(self, hwnd:int)->None:
        for i,it in enumerate(list(self.items)):
            if it["src_hwnd"]==hwnd:
                self.items.pop(i); break
        self.drop_thumb(hwnd)
        self.start_index=min(self.start_index, max(0,len(self.items)-self.visible_count))
        self.layout_visible_tiles()

    def ensure_tile_pool(self)->None:
        while len(self.tiles)<self.visible_count:
            tw=TileWidget(self.canvas,0,"")
            tw.clicked.connect(self.on_tile_clicked)
            tw.closeClicked.connect(self.on_close_clicked)
            self.tiles.append(tw)
        while len(self.tiles)>self.visible_count:
            w=self.tiles.pop(); w.setParent(None); w.deleteLater()

    def layout_visible_tiles(self)->None:
        self.ensure_tile_pool()
        area=self.canvas.rect()
        n=min(self.visible_count, max(0, len(self.items)-self.start_index))
        for i,tw in enumerate(self.tiles):
            if i>=n and tw.isVisible(): tw.hide()
        if n<=0: self.update(); return

        pad_x=10
        iw=min(self.item_width, max(120, area.width()-2*pad_x))
        ih=self.item_height
        step=ih+self.gap_px
        x=pad_x

        for i in range(n):
            it=self.items[self.start_index+i]
            y=i*step
            geo=QtCore.QRect(x,y,iw, min(ih, max(0, area.height()-y)))
            tw=self.tiles[i]
            tw.setGeometry(geo); tw.hwnd=it["src_hwnd"]
            if tw.title!=it["title"]: tw.setTitle(it["title"])
            tw.show()

            if self.enabled:
                tl=self.canvas.mapTo(self, QtCore.QPoint(geo.left()+4, geo.top()+TileSpec.TITLE_H+TITLE_GAP))
                br=self.canvas.mapTo(self, QtCore.QPoint(geo.right()-4, geo.bottom()-6))
                dest=RECT(tl.x(), tl.y(), max(tl.x()+10, br.x()), max(tl.y()+10, br.y()))
                props=DWM_THUMBNAIL_PROPERTIES()
                props.dwFlags=DWM_TNP_VISIBLE|DWM_TNP_RECTDESTINATION|DWM_TNP_OPACITY|DWM_TNP_SOURCECLIENTAREAONLY
                props.rcDestination=dest; props.rcSource=RECT(0,0,0,0)
                props.opacity=self.opacity; props.fVisible=True; props.fSourceClientAreaOnly=False
                th=self.ensure_thumb(it["src_hwnd"])
                if th: DwmUpdateThumbnailProperties(th, C.byref(props))
        self.update()

    def resizeEvent(self,e):
        super().resizeEvent(e); self.layout_visible_tiles()

    def on_close_clicked(self, hwnd:int)->None:
        if win32gui.IsWindow(hwnd): win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

    def on_tile_clicked(self, hwnd:int)->None:
        if not win32gui.IsWindow(hwnd): return
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            user32.SetForegroundWindow(W.HWND(int(hwnd)))
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

    def reconcile(self)->None:
        for it in list(self.items):
            h=it["src_hwnd"]
            ok=False
            try: ok = win32gui.IsWindow(h) and is_top_level(h) and (win32gui.IsIconic(h) or win32gui.IsWindowVisible(h))
            except Exception: ok=False
            if not ok: self.remove_item(h)
        for h in list_minimized_windows(): self.add_item(h)

    def process_events(self)->None:
        batch:List[Event]=[]
        with q_lock:
            while queue: batch.append(queue.popleft())
        if not batch: return
        for ev in batch:
            h=ev.hwnd
            if ev.type==EVENT_SYSTEM_MINIMIZESTART:
                self.add_item(h)
            elif ev.type in (EVENT_SYSTEM_MINIMIZEEND, EVENT_OBJECT_DESTROY, EVENT_OBJECT_HIDE, EVENT_OBJECT_SHOW):
                self.remove_item(h)

    def closeEvent(self,e)->None:
        try:
            if getattr(self,'hook',None): UnhookWinEvent(self.hook)
        except Exception: pass
        for h in list(self.thumbs.keys()): self.drop_thumb(h)
        super().closeEvent(e)

    def make_tray(self)->None:
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable(): return
        icon_pix=QtGui.QPixmap(22,22); icon_pix.fill(QtGui.QColor(0,120,215))
        self.tray=QtWidgets.QSystemTrayIcon(QtGui.QIcon(icon_pix), self)
        m=QtWidgets.QMenu()
        m.addAction("Mostrar/Ocultar", lambda: self.setVisible(not self.isVisible()))
        m.addSeparator()
        sub_size=m.addMenu("Tamanho do widget")
        for w,h in ((180,120),(220,140),(260,160),(300,200)):
            m_act=sub_size.addAction(f"{w}x{h}"); m_act.triggered.connect(lambda _=False,W_=w,H_=h: self._set_size(W_,H_))
        sub_gap=m.addMenu("Espaçamento")
        for g in (0,4,8,12,16,24):
            m_act=sub_gap.addAction(f"{g}px"); m_act.triggered.connect(lambda _=False,G_=g: self._set_gap(G_))
        sub_bar=m.addMenu("Largura da barra")
        for bw in (220,260,300,340,400):
            m_act=sub_bar.addAction(f"{bw}px"); m_act.triggered.connect(lambda _=False,BW_=bw: self._set_bar(BW_))
        sub_op=m.addMenu("Opacidade")
        for op in (255,220,192,160,128):
            m_act=sub_op.addAction(str(op)); m_act.triggered.connect(lambda _=False,OP_=op: self._set_opacity(OP_))
        m.addSeparator()
        m.addAction("Sair", QtWidgets.QApplication.instance().quit)
        self.tray.setContextMenu(m); self.tray.setToolTip("Stage Sidebar"); self.tray.show()

    def _set_size(self,w:int,h:int): self.item_width=w; self.item_height=h; self.layout_visible_tiles()
    def _set_gap(self,g:int): self.gap_px=g; self.layout_visible_tiles()
    def _set_bar(self,bw:int):
        r=self.geometry(); self.setGeometry(r.left(), r.top(), bw, r.height()); self.layout_visible_tiles()
    def _set_opacity(self,op:int): self.opacity=max(0,min(255,int(op))); self.layout_visible_tiles()

def main()->int:
    app=QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pix=QtGui.QPixmap(22,22); pix.fill(QtGui.QColor(0,120,215))
    app.setWindowIcon(QtGui.QIcon(pix))
    w=Sidebar()
    return app.exec()

if __name__=="__main__":
    sys.exit(main())
