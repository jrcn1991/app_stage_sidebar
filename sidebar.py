from __future__ import annotations
import  os as _os
from setting import *
from config import *
import sys, os


def resource_path(relative_path: str) -> str:
    """Return absolute path for resources (works inside PyInstaller)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# ===== Sidebar =====
class Sidebar(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stage Sidebar")
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")

        self.items: List[Dict] = []  # {src_hwnd,title,pix,hthumb,mon_idx,exe}
        self.start_index = 0
        self.monitors = enum_monitors()
        self.enabled = self.check_dwm()

        s = load_conf()
        self.target_monitor = int(s["monitor"]) if 0 <= int(s["monitor"]) < len(self.monitors) else 0
        self.edge = ABE_LEFT if s["edge"] == "left" else ABE_RIGHT
        self.bar_width = int(s["bar_width"])
        self.bar_height_pct = int(s["bar_height_pct"])
        self.bar_offset_y = int(s["bar_offset_y"])
        self.visible_count = int(s["visible_count"])
        self.overlap_pct = float(s["overlap_pct"])
        self.gap_px = int(s.get("gap_px", 2))
        self.item_width = int(s.get("item_width", 200))
        self.item_height = int(s.get("item_height", 140))
        self.exclude_execs = [e.lower() for e in s.get("exclude_execs", [])]
        self.focus_single = bool(s["focus_single"])
        self.start_hidden = bool(s.get("start_hidden", True))
        # Overlay config global
        self.icon_size = int(s.get("icon_size", 22))
        self.icon_anchor = str(s.get("icon_anchor", "bottom-left"))
        self.icon_offx = int(s.get("icon_offset_x", 6))
        self.icon_offy = int(s.get("icon_offset_y", 6))
        self.icon_allow_drag = bool(s.get("icon_allow_drag", True))
        self.show_title = bool(s.get("show_title", True))
        self.maximize_on_restore = bool(s.get("maximize_on_restore", False))

        self.canvas = QtWidgets.QWidget(self)
        self.setCentralWidget(self.canvas)
        self.canvas.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.canvas.setAutoFillBackground(False)
        self.canvas.setStyleSheet("background: transparent;")
        self.canvas.installEventFilter(self)
        self.tiles: List[TileWidget] = []
        self.static_thumbs = True
        self.cb_msg = user32.RegisterWindowMessageW("StageSidebarAppBar")
        register_appbar(int(self.winId()), self.cb_msg)
        self.reposition_appbar()

        self.make_tray()

        self.hook = start_winevent_hook()

        self.t_ev = QtCore.QTimer(self); self.t_ev.setInterval(120); self.t_ev.timeout.connect(self.process_events); self.t_ev.start()
        self.t_scan = QtCore.QTimer(self); self.t_scan.setInterval(1000); self.t_scan.timeout.connect(self.reconcile); self.t_scan.start()

        if not self.start_hidden:
            self.show()
        QtCore.QTimer.singleShot(150, self.reconcile)

        self._t_full = QtCore.QTimer(self)
        self._t_full.setInterval(400)
        self._t_full.timeout.connect(self._check_fullscreen)
        self._t_full.start()

    # ===== Tray =====

    def make_tray(self) -> None:
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon_path = resource_path("docs/stage-manager-icon.png")
        self.tray = QtWidgets.QSystemTrayIcon(QtGui.QIcon(icon_path), self)
        m = QtWidgets.QMenu()

        act_show = m.addAction("Show/Hide")
        act_show.triggered.connect(lambda: self.setVisible(not self.isVisible()))

        m.addSeparator()

        act_focus = m.addAction("Single Focus"); act_focus.setCheckable(True); act_focus.setChecked(self.focus_single)
        act_focus.toggled.connect(lambda v: setattr(self, "focus_single", bool(v)))

        sub_edge = m.addMenu("Side")
        a_left = sub_edge.addAction("Left"); a_right = sub_edge.addAction("Right")
        a_left.setCheckable(True); a_right.setCheckable(True)

        def _set_left():
            self.edge = ABE_LEFT; self.reposition_appbar()
        def _set_right():
            self.edge = ABE_RIGHT; self.reposition_appbar()
        a_left.triggered.connect(_set_left); a_right.triggered.connect(_set_right)

        act_settings = m.addAction("Settings"); act_settings.triggered.connect(self.open_settings)
        act_save = m.addAction("Save Settings"); act_save.triggered.connect(self.save_current_conf)

        m.addSeparator()
        act_quit = m.addAction("Exit"); act_quit.triggered.connect(QtWidgets.QApplication.instance().quit)

        self.tray.setContextMenu(m)
        self.tray.setToolTip("Stage Sidebar")
        self.tray.show()

    def save_current_conf(self) -> None:
        save_conf(self.current_state())

    def open_settings(self) -> None:
        dlg = SettingsDialog(self, self.monitors, self.current_state())
        dlg.exec()

    def current_state(self) -> dict:
        return {
            "monitor": self.target_monitor,
            "edge": "left" if self.edge == ABE_LEFT else "right",
            "bar_width": self.bar_width,
            "bar_height_pct": self.bar_height_pct,
            "bar_offset_y": self.bar_offset_y,
            "visible_count": self.visible_count,
            "overlap_pct": self.overlap_pct,
            "gap_px": self.gap_px,
            "item_width": self.item_width,
            "item_height": self.item_height,
            "exclude_execs": self.exclude_execs,
            "focus_single": self.focus_single,
            "start_hidden": not self.isVisible(),
            "icon_size": self.icon_size,
            "icon_anchor": self.icon_anchor,
            "icon_offset_x": self.icon_offx,
            "icon_offset_y": self.icon_offy,
            "icon_allow_drag": self.icon_allow_drag,
            "show_title": getattr(self, "show_title", True),
            # NOVO
            "maximize_on_restore": getattr(self, "maximize_on_restore", False),
        }

    def apply_settings(self, st: dict) -> None:
        self.target_monitor = int(st["monitor"]) if 0 <= int(st["monitor"]) < len(self.monitors) else 0
        self.edge = ABE_LEFT if st["edge"] == "left" else ABE_RIGHT
        self.bar_width = int(st["bar_width"])
        self.bar_height_pct = int(st["bar_height_pct"])
        self.bar_offset_y = int(st["bar_offset_y"])
        self.visible_count = int(st["visible_count"])
        self.overlap_pct = float(st["overlap_pct"])
        self.gap_px = int(st.get("gap_px", self.gap_px))
        self.item_width = int(st.get("item_width", self.item_width))
        self.item_height = int(st.get("item_height", self.item_height))
        self.exclude_execs = [e.lower() for e in st.get("exclude_execs", self.exclude_execs)]
        self.focus_single = bool(st["focus_single"])
        self.icon_size = int(st.get("icon_size", self.icon_size))
        self.icon_anchor = str(st.get("icon_anchor", self.icon_anchor))
        self.icon_offx = int(st.get("icon_offset_x", self.icon_offx))
        self.icon_offy = int(st.get("icon_offset_y", self.icon_offy))
        self.icon_allow_drag = bool(st.get("icon_allow_drag", self.icon_allow_drag))
        self.show_title = bool(st.get("show_title", getattr(self, "show_title", True)))
        # NOVO
        self.maximize_on_restore = bool(st.get("maximize_on_restore", getattr(self, "maximize_on_restore", False)))

        self.reposition_appbar()
        for tw in self.tiles:
            tw.setOverlayConfig(self.icon_size, self.icon_anchor, self.icon_offx, self.icon_offy, self.icon_allow_drag)
        self.layout_visible_tiles()

    # ===== Native/AppBar =====
    def nativeEvent(self, eventType, message):
        if eventType == "windows_generic_MSG":
            try:
                m = MSG.from_address(int(message))
                if m.message == self.cb_msg and m.wParam == ABN_POSCHANGED:
                    self.reposition_appbar()
            except Exception:
                pass
        return False, 0

    def monitor_rect(self) -> Tuple[int, int, int, int]:
        l, t, r, b = self.monitors[self.target_monitor]["rect"]
        return l, t, r, b

    def geometry_for_edge(self) -> RECT:
        l, t, r, b = self.monitor_rect()
        H = b - t
        bh = max(120, int(H * self.bar_height_pct / 100))
        top = min(max(t + self.bar_offset_y, t), b - bh)
        if self.edge == ABE_LEFT:
            return RECT(l, top, l + self.bar_width, top + bh)
        return RECT(r - self.bar_width, top, r, top + bh)

    def reposition_appbar(self) -> None:
        rc = set_appbar_pos(int(self.winId()), self.edge, self.geometry_for_edge())
        self.setGeometry(rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top)
        self.layout_visible_tiles()

    # ===== Layout =====
    def ensure_tile_pool(self) -> None:
        while len(self.tiles) < self.visible_count:
            tw = TileWidget(self.canvas, 0, "", QtGui.QPixmap())
            tw.clicked.connect(self.on_tile_clicked)
            tw.closeClicked.connect(self.on_close_clicked)
            tw.setOverlayConfig(self.icon_size, self.icon_anchor, self.icon_offx, self.icon_offy, self.icon_allow_drag)
            self.tiles.append(tw)
        while len(self.tiles) > self.visible_count:
            w = self.tiles.pop()
            try:
                w.hideOverlays()
            except Exception:
                pass
            w.setParent(None)
            # garante limpeza dos overlays
            try:
                w.icon_overlay.deleteLater()
            except Exception:
                pass
            try:
                w.close_overlay.deleteLater()
            except Exception:
                pass
            w.deleteLater()

    def layout_visible_tiles(self) -> None:
        self.ensure_tile_pool()
        area = self.canvas.rect()
        avail_h = area.height()
        avail_w = area.width()
        n = min(self.visible_count, max(0, len(self.items) - self.start_index))

        # Esconde completamente tiles e overlays fora de uso
        for idx, tw in enumerate(self.tiles):
            if idx >= n:
                if tw.isVisible():
                    tw.hide()
                # força esconder também os overlays top-level
                try:
                    tw.hideOverlays()
                except Exception:
                    pass

        if n <= 0:
            return
        ...

        pad_x = 8
        iw = min(self.item_width, max(50, avail_w - 2 * pad_x))
        ih = self.item_height
        overlap = max(0.0, min(0.8, self.overlap_pct / 100.0))
        step = int(ih * (1 - overlap)) + self.gap_px
        x = pad_x if self.edge == ABE_LEFT else (avail_w - pad_x - iw)

        for i in range(n):
            it = self.items[self.start_index + i]
            y = i * step
            h_draw = min(ih, max(0, avail_h - y))
            if h_draw <= 0:
                break
            geo = QtCore.QRect(x, y, iw, h_draw)
            tw = self.tiles[i]
            tw.setGeometry(geo)
            tw.hwnd = it["src_hwnd"]
            if tw.title != it["title"] or (
                    tw.pix is None or it["pix"] is None or tw.pix.cacheKey() != it["pix"].cacheKey()):
                tw.setData(it["title"], it["pix"])

            # aplica imagem estática se houver
            shot = it.get("shot")
            if shot and not shot.isNull():
                tw.thumb.setPixmap(shot)

            tw.show()
            tw.updateOverlayPos()
            tw.forceTopMost()

            # Thumbnails DWM quando habilitado
            tl = self.canvas.mapTo(self, QtCore.QPoint(geo.left() + 4, geo.top() + TileSpec.TITLE_H + TITLE_GAP))
            br = self.canvas.mapTo(self, QtCore.QPoint(geo.right() - 4, geo.top() + h_draw - 6))
            dest = RECT(tl.x(), tl.y(), max(tl.x() + 10, br.x()), max(tl.y() + 10, br.y()))
            if self.enabled:
                if not it.get("hthumb"):
                    th = HANDLE()
                    hr = DwmRegisterThumbnail(W.HWND(int(self.winId())), W.HWND(int(it["src_hwnd"])), C.byref(th))
                    if hr == 0 and th:
                        it["hthumb"] = th
                if it.get("hthumb"):
                    props = DWM_THUMBNAIL_PROPERTIES()
                    props.dwFlags = DWM_TNP_VISIBLE | DWM_TNP_RECTDESTINATION | DWM_TNP_OPACITY | DWM_TNP_SOURCECLIENTAREAONLY
                    props.rcDestination = dest
                    props.rcSource = RECT(0, 0, 0, 0)
                    props.opacity = 255
                    props.fVisible = True
                    props.fSourceClientAreaOnly = False
                    DwmUpdateThumbnailProperties(it["hthumb"], C.byref(props))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.layout_visible_tiles()

    def _hide_overlays_for_hwnd(self, hwnd: int) -> None:
        # esconde overlays do tile correspondente
        for tw in self.tiles:
            if tw.hwnd == hwnd:
                try:
                    tw.hideOverlays()
                except Exception:
                    pass
        # garantia adicional: se não há itens, esconde de todos
        if not self.items:
            for tw in self.tiles:
                try:
                    tw.hideOverlays()
                except Exception:
                    pass

    def moveEvent(self, e):
        super().moveEvent(e)
        # reposiciona todos overlays ao mover a janela principal
        for tw in self.tiles:
            tw.updateOverlayPos()

    def eventFilter(self, obj, ev):
        if obj is self.canvas and ev.type() == QtCore.QEvent.Wheel:
            if len(self.items) > self.visible_count:
                delta = -1 if ev.angleDelta().y() < 0 else 1
                self.start_index = max(0, min(self.start_index - delta, len(self.items) - self.visible_count))
                self.layout_visible_tiles()
                return True
        return super().eventFilter(obj, ev)

    # ===== Dados =====
    def check_dwm(self) -> bool:
        b = W.BOOL()
        hr = DwmIsCompositionEnabled(C.byref(b))
        return hr == 0 and bool(b.value)

    def add_item(self, hwnd: int, mon_idx: int, snapshot: QtGui.QPixmap | None = None) -> None:
        if any(x["src_hwnd"] == hwnd for x in self.items):
            return
        title = get_title(hwnd)
        if not title:
            return
        exe_full = get_exe_from_hwnd(hwnd)
        exe_name = _os.path.basename(exe_full).lower() if exe_full else ""
        if exe_name and exe_name in self.exclude_execs:
            return
        hicon, own = get_icon_handle(hwnd)
        pix = hicon_to_qpixmap(hicon, self.icon_size)
        if own and hicon:
            try:
                user32.DestroyIcon(W.HICON(int(hicon)))
            except Exception:
                pass
        it = {
            "src_hwnd": hwnd, "title": title, "pix": pix,
            "hthumb": HANDLE(), "mon_idx": mon_idx, "exe": exe_name,
            "shot": snapshot if snapshot and not snapshot.isNull() else QtGui.QPixmap()
        }
        self.items.append(it)
        self.layout_visible_tiles()

    def remove_item(self, hwnd: int) -> None:
        # remove do vetor e desmonta thumbnail DWM
        for i, it in enumerate(list(self.items)):
            if it["src_hwnd"] == hwnd:
                try:
                    th = it.get("hthumb")
                    if th and int(th.value or 0) != 0:
                        DwmUnregisterThumbnail(th)
                except Exception:
                    pass
                self.items.pop(i)
                break

        # esconde overlays desse hwnd
        self._hide_overlays_for_hwnd(hwnd)

        # se ficou vazio, esconde overlays de todos os tiles por segurança
        if not self.items:
            for tw in self.tiles:
                try:
                    tw.hideOverlays()
                except Exception:
                    pass

        # corrige índice e relayout
        self.start_index = min(self.start_index, max(0, len(self.items) - self.visible_count))
        self.layout_visible_tiles()

    # ===== AÃ§Ãµes =====
    def on_close_clicked(self, hwnd: int) -> None:
        if win32gui.IsWindow(hwnd):
            # esconde overlays antes de fechar
            self._hide_overlays_for_hwnd(hwnd)
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

    def minimize_others_same_monitor(self, except_hwnd: int) -> None:
        tgt = self.target_monitor
        host = int(self.winId())

        def cb(h, _):
            try:
                if h in (except_hwnd, host):
                    return True
                if not win32gui.IsWindow(h) or not win32gui.IsWindowVisible(h):
                    return True
                if not is_top_level(h):
                    return True
                if monitor_index_for_hwnd(h, self.monitors) != tgt:
                    return True
                if win32gui.IsIconic(h):
                    return True
                win32gui.ShowWindow(h, win32con.SW_MINIMIZE)
            except Exception:
                pass
            return True

        win32gui.EnumWindows(cb, None)

    def on_tile_clicked(self, hwnd: int) -> None:
        if not win32gui.IsWindow(hwnd):
            return
        if win32gui.IsIconic(hwnd):
            # restaura maximizado se configurado
            if self.maximize_on_restore:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            user32.SetForegroundWindow(W.HWND(int(hwnd)))

            # esconder overlays imediatamente
            for tw in self.tiles:
                if tw.hwnd == hwnd:
                    tw.hideOverlays()

            if self.focus_single:
                self.minimize_others_same_monitor(hwnd)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

        for tw in self.tiles:
            if tw.isVisible():
                tw.forceTopMost()

    # ===== ReconciliaÃ§Ã£o / eventos =====

    def capture_snapshot(self, hwnd: int) -> QtGui.QPixmap:
        scr = QtWidgets.QApplication.primaryScreen()
        if not scr or not win32gui.IsWindow(hwnd):
            return QtGui.QPixmap()
        try:
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            w, h = max(1, r - l), max(1, b - t)
            pm = scr.grabWindow(int(hwnd), 0, 0, w, h)
            return pm
        except Exception:
            return QtGui.QPixmap()

    def reconcile(self) -> None:
        for it in list(self.items):
            h = it["src_hwnd"]
            try:
                valid = win32gui.IsWindow(h)
                same_mon = monitor_index_for_hwnd(h, self.monitors) == self.target_monitor
                eligible = is_top_level(h) and (win32gui.IsIconic(h) or win32gui.IsWindowVisible(h))
            except Exception:
                valid = same_mon = eligible = False
            if not (valid and same_mon and eligible):
                self.remove_item(h)
        for h in list_minimized_windows():
            if monitor_index_for_hwnd(h, self.monitors) == self.target_monitor:
                self.add_item(h, self.target_monitor)

    def process_events(self) -> None:
        batch: List[Event] = []
        with q_lock:
            while queue:
                batch.append(queue.popleft())
        if not batch:
            return
        for ev in batch:
            h = ev.hwnd
            if ev.type == EVENT_SYSTEM_MINIMIZESTART:
                if monitor_index_for_hwnd(h, self.monitors) == self.target_monitor:
                    snap = self.capture_snapshot(h) if self.static_thumbs else None
                    self.add_item(h, self.target_monitor, snapshot=snap)
            elif ev.type in (EVENT_SYSTEM_MINIMIZEEND, EVENT_OBJECT_DESTROY, EVENT_OBJECT_HIDE, EVENT_OBJECT_SHOW):
                self.remove_item(h)

    def _check_fullscreen(self):
        """Esconde a barra se existir QUALQUER janela em fullscreen no monitor configurado."""
        try:
            # obtém área do monitor alvo
            ml, mt, mr, mb = self.monitors[self.target_monitor]["rect"]
            mw, mh = mr - ml, mb - mt

            found_fullscreen = False

            def enum_cb(hwnd, _):
                nonlocal found_fullscreen
                try:
                    if not win32gui.IsWindowVisible(hwnd):
                        return True
                    if not is_top_level(hwnd):
                        return True
                    if monitor_index_for_hwnd(hwnd, self.monitors) != self.target_monitor:
                        return True

                    # área da janela
                    l, t, r, b = win32gui.GetWindowRect(hwnd)
                    w, h = r - l, b - t

                    # se cobre praticamente todo o monitor (tolerância de 2px)
                    if w >= mw - 2 and h >= mh - 2:
                        found_fullscreen = True
                        return False  # parar a enumeração
                except Exception:
                    return True
                return True

            win32gui.EnumWindows(enum_cb, None)

            if found_fullscreen and self.isVisible():
                self.hide()
            elif not found_fullscreen and not self.isVisible():
                self.show()

        except Exception:
            pass

    def closeEvent(self, e) -> None:
        try:
            UnhookWinEvent(getattr(self, "hook", 0))
        except Exception:
            pass
        try:
            remove_appbar(int(self.winId()))
        except Exception:
            pass
        for tw in list(self.tiles):
            try:
                tw.icon_overlay.hide()
                tw.icon_overlay.deleteLater()
            except Exception:
                pass
        for it in list(self.items):
            self.remove_item(it["src_hwnd"])
        super().closeEvent(e)
