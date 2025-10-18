from __future__ import annotations
from PySide6 import QtWidgets
from win_utils import * # Importa tudo


TITLE_GAP = 2 # EspaÃ§o entre titulo e thumb


# ===== Overlay window =====
class IconOverlay(QtWidgets.QLabel):
    def __init__(self, parent_tile: 'TileWidget'):
        # Janela top-most independente
        super().__init__(None)
        self.tile = parent_tile
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setMouseTracking(True)
        self._drag = False
        self._last = QtCore.QPoint()
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)


    def startDrag(self, pos: QtCore.QPoint):
        self._drag = True
        self._last = pos

    def stopDrag(self):
        self._drag = False

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton and self.tile.icon_allow_drag:
            self.startDrag(e.globalPosition().toPoint())
            e.accept()
            return
        if e.button() == QtCore.Qt.LeftButton:
            # Clique simples sobre o overlay aciona o tile
            self.tile.clicked.emit(self.tile.hwnd)
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent):
        if self._drag:
            cur = e.globalPosition().toPoint()
            delta = cur - self._last
            self._last = cur
            self.tile.icon_offx += delta.x()
            self.tile.icon_offy += delta.y()
            self.tile.updateOverlayPos()
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent):
        if self._drag and e.button() == QtCore.Qt.LeftButton:
            self.stopDrag()
            e.accept()
            return
        super().mouseReleaseEvent(e)


class CloseOverlay(QtWidgets.QLabel):
    def __init__(self, parent_tile: 'TileWidget'):
        super().__init__(None)
        self.tile = parent_tile
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setMouseTracking(True)
        self.setFixedSize(24, 24)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        center = self.rect().center()
        r = min(self.width(), self.height()) // 2 - 3
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(0, 0, 0, 60)); p.drawEllipse(center + QtCore.QPoint(0, 1), r, r)
        p.setBrush(QtGui.QColor(255, 255, 255))
        p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 30), 1)); p.drawEllipse(center, r, r)
        inner = int(r * 0.6)
        pen_x = QtGui.QPen(QtGui.QColor(220, 50, 47), 2); pen_x.setCapStyle(QtCore.Qt.RoundCap); pen_x.setJoinStyle(QtCore.Qt.RoundJoin)
        p.setPen(pen_x)
        p.drawLine(center + QtCore.QPoint(-inner, -inner), center + QtCore.QPoint(inner,  inner))
        p.drawLine(center + QtCore.QPoint(-inner,  inner), center + QtCore.QPoint(inner, -inner))
        p.end()

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self.tile.closeClicked.emit(self.tile.hwnd)
            e.accept(); return
        super().mousePressEvent(e)

    # NOVO: sinaliza hover sobre o próprio "X"
    def enterEvent(self, e):
        self.tile._over_close = True
        self.tile.updateOverlayPos()

    def leaveEvent(self, e):
        self.tile._over_close = False
        self.tile.updateOverlayPos()



# ===== Tile Widget =====
class TileWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal(int)
    closeClicked = QtCore.Signal(int)

    def __init__(self, parent, hwnd: int, title: str, icon: QtGui.QPixmap):
        super().__init__(parent)
        self.hwnd = hwnd
        self.title = title
        self.pix = icon
        self.hover = False
        self._over_close = False  # NOVO

        # Config do overlay do ícone
        self.icon_size = 22
        self.icon_anchor = "bottom-left"
        self.icon_offx = 6
        self.icon_offy = 6
        self.icon_allow_drag = True

        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(4, TileSpec.TITLE_H + TITLE_GAP, 4, 6)
        self.layout.setSpacing(0)

        self.thumb = QtWidgets.QLabel()
        self.thumb.setScaledContents(True)
        self.thumb.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.thumb.setStyleSheet("background: transparent;")
        self.thumb.setMouseTracking(True)
        self.thumb.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, False)
        self.layout.addWidget(self.thumb, 1)

        # Overlays top-most
        self.icon_overlay = IconOverlay(self)
        self.close_overlay = CloseOverlay(self)

        self.refreshOverlayPixmap()
        self._last_icon_cache_key = 0
        self._last_overlay_rect = QtCore.QRect()

        # Reage a movimentos globais do mouse para esconder/mostrar o "X"
        QtWidgets.QApplication.instance().installEventFilter(self)

    def forceTopMost(self):
        # Não reexibe a janela do overlay à força.
        try:
            if not self.icon_overlay.isVisible():
                return
            hwnd = int(self.icon_overlay.winId())
            win32gui.SetWindowPos(
                hwnd,
                win32con.HWND_TOPMOST,
                0, 0, 0, 0,
                win32con.SWP_NOMOVE
                | win32con.SWP_NOSIZE
                | win32con.SWP_NOACTIVATE
                | win32con.SWP_NOOWNERZORDER
                | win32con.SWP_NOSENDCHANGING
            )
        except Exception:
            pass

    # ---- API overlay ----
    def refreshOverlayPixmap(self):
        if self.pix and not self.pix.isNull():
            key = int(self.pix.cacheKey())
            if key == self._last_icon_cache_key:
                return  # jÃ¡ estÃ¡ igual; nÃ£o repinte
            pm = self.pix if (self.pix.width() == self.icon_size and self.pix.height() == self.icon_size) else \
                self.pix.scaled(self.icon_size, self.icon_size, QtCore.Qt.KeepAspectRatio,
                                QtCore.Qt.SmoothTransformation)
            self.icon_overlay.setPixmap(pm)
            self._last_icon_cache_key = key

    def setOverlayConfig(self, size: int, anchor: str, offx: int, offy: int, allow_drag: bool):
        self.icon_size = max(12, min(128, int(size)))
        self.icon_anchor = str(anchor)
        self.icon_offx = int(offx)
        self.icon_offy = int(offy)
        self.icon_allow_drag = bool(allow_drag)
        self.refreshOverlayPixmap()
        self.updateOverlayPos()

    def iconRectLocal(self) -> QtCore.QRect:
        s = self.icon_size
        ax, ay = self._anchor_base(s)
        x = ax + self.icon_offx
        y = ay + self.icon_offy
        # NÃ£o clampamos aqui para permitir offsets fora do tile se desejado
        return QtCore.QRect(x, y, s, s)

    def _anchor_base(self, size: int) -> Tuple[int, int]:
        w, h = self.width(), self.height()
        tH = TileSpec.TITLE_H
        a = self.icon_anchor.lower()
        if a == "bottom-left":
            return 0, h - size
        if a == "bottom-right":
            return w - size, h - size
        if a == "top-left":
            return 0, 0
        if a == "top-right":
            return w - size, 0
        if a == "center":
            return (w - size)//2, (h - size)//2
        if a == "title-left":
            return 4, max(0, (tH - size)//2)
        if a == "title-right":
            return max(4, w - size - 4), max(0, (tH - size)//2)
        if a == "title-center":
            return max(0, (w - size)//2), max(0, (tH - size)//2)
        return 0, h - size

    def updateOverlayPos(self):
        # ----- ÍCONE -----
        # Ícone só existe se: tile visível E ainda há itens no Stage
        items_present = True
        try:
            sidebar = self.parent().parent()
            items_present = len(getattr(sidebar, "items", [])) > 0
        except Exception:
            pass

        want_icon = self.isVisible() and items_present

        if want_icon:
            r_local = self.iconRectLocal()
            top_left = self.mapToGlobal(r_local.topLeft())
            geo = QtCore.QRect(top_left, r_local.size())
            if geo != self._last_overlay_rect:
                self.icon_overlay.setGeometry(geo)
                self._last_overlay_rect = geo
            if not self.icon_overlay.isVisible():
                self.icon_overlay.show()
            # só mantém top-most se já está visível
            self.forceTopMost()
        else:
            if self.icon_overlay.isVisible():
                self.icon_overlay.hide()

        # --- FECHAR (overlay) quando título oculto ---
        try:
            sidebar = self.parent().parent()
            show_title = bool(getattr(sidebar, "show_title", True))
        except Exception:
            show_title = True

        if show_title:
            if self.close_overlay.isVisible():
                self.close_overlay.hide()
            return

        # posiciona no canto da área da thumb
        w = self.width()
        y0 = TileSpec.TITLE_H + TITLE_GAP + 6
        x0 = w - 24 - 10
        r_close = QtCore.QRect(x0, y0, 24, 24)
        g_close = QtCore.QRect(self.mapToGlobal(r_close.topLeft()), r_close.size())
        self.close_overlay.setGeometry(g_close)

        # Só visível se mouse está sobre o tile OU sobre o próprio "X"
        inside_tile = self.rect().contains(self.mapFromGlobal(QtGui.QCursor.pos()))
        want_visible = self.isVisible() and (self.hover or inside_tile or self._over_close)
        self.close_overlay.setVisible(want_visible)

        # garante top-most
        try:
            hwnd = int(self.close_overlay.winId())
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE |
                (win32con.SWP_SHOWWINDOW if want_visible else win32con.SWP_HIDEWINDOW)
            )
        except Exception:
            pass

    # ---- Dados ----
    def setData(self, title: str, pix: QtGui.QPixmap) -> None:
        self.title = title
        self.pix = pix
        self.thumb.setPixmap(self.pix)  # a label usa a mesma pixmap para manter consistÃªncia visual
        self.refreshOverlayPixmap()
        self.updateOverlayPos()
        self.update()

    # ---- Eventos ----
    def showEvent(self, e):
        super().showEvent(e)
        self.updateOverlayPos()
        self.forceTopMost()

    def hideEvent(self, e):
        if self.icon_overlay.isVisible(): self.icon_overlay.hide()
        if self.close_overlay.isVisible(): self.close_overlay.hide()
        super().hideEvent(e)

    def moveEvent(self, e):
        super().moveEvent(e)
        self.updateOverlayPos()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.updateOverlayPos()

    def closeEvent(self, e):
        for ov in (self.icon_overlay, self.close_overlay):
            try:
                ov.hide();
                ov.deleteLater()
            except Exception:
                pass
        super().closeEvent(e)

    def enterEvent(self, e):
        self.hover = True
        self.update()
        self.updateOverlayPos()

    def leaveEvent(self, e):
        self.hover = False
        self.update()
        self.updateOverlayPos()

    def eventFilter(self, obj, ev):
        # Atualiza visibilidade ao mover o mouse em qualquer lugar
        if ev.type() == QtCore.QEvent.MouseMove and self.isVisible():
            self.updateOverlayPos()
        return False

    def hideOverlays(self):
        # usado ao restaurar a janela para evitar overlays presos
        try:
            self.icon_overlay.hide()
        except Exception:
            pass
        try:
            self.close_overlay.hide()
        except Exception:
            pass

    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() != QtCore.Qt.LeftButton:
            return
        if TileSpec.closeRect(self.width(), self.height()).adjusted(-4, -4, 4, 4).contains(e.position().toPoint()):
            self.closeClicked.emit(self.hwnd)
        else:
            self.clicked.emit(self.hwnd)

    def wheelEvent(self, e: QtGui.QWheelEvent):
        QtWidgets.QApplication.sendEvent(self.parent(), e)

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        # flag global
        show_title = True
        try:
            show_title = bool(getattr(self.parent().parent(), "show_title", True))
        except Exception:
            pass

        # Título
        if show_title:
            tr = TileSpec.titleRect(self.width(), self.height())
            p.fillRect(tr, QtGui.QColor(0, 0, 0, 120))
            p.setPen(QtGui.QColor(255, 255, 255))
            p.drawText(tr.adjusted(10, 0, -36, 0), QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self.title)

            # Botão fechar clássico (no título)
            if self.hover:
                cr = TileSpec.closeRect(self.width(), self.height())
                center = cr.center()
                r = min(cr.width(), cr.height()) // 2 - 2
                p.setPen(QtCore.Qt.NoPen)
                p.setBrush(QtGui.QColor(0, 0, 0, 50))
                p.drawEllipse(center + QtCore.QPoint(0, 1), r, r)
                p.setBrush(QtGui.QColor(255, 255, 255))
                p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 30), 1))
                p.drawEllipse(center, r, r)
                inner = int(r * 0.6)
                pen_x = QtGui.QPen(QtGui.QColor(220, 50, 47), 2)
                pen_x.setCapStyle(QtCore.Qt.RoundCap)
                pen_x.setJoinStyle(QtCore.Qt.RoundJoin)
                p.setPen(pen_x)
                p.drawLine(QtCore.QPoint(center.x() - inner, center.y() - inner),
                           QtCore.QPoint(center.x() + inner, center.y() + inner))
                p.drawLine(QtCore.QPoint(center.x() - inner, center.y() + inner),
                           QtCore.QPoint(center.x() + inner, center.y() - inner))

        # Realce de hover sobre a thumb
        if self.hover:
            r = QtCore.QRect(4, TileSpec.TITLE_H + TITLE_GAP,
                             self.width() - 8,
                             max(0, self.height() - (TileSpec.TITLE_H + TITLE_GAP) - 6))
            if r.height() > 0:
                p.fillRect(r, QtGui.QColor(255, 255, 255, 28))
                pen = QtGui.QPen(QtGui.QColor(0, 255, 0, 200))
                pen.setWidth(4)
                p.setPen(pen)
                p.drawRect(r.adjusted(0, 0, -1, -1))

        p.end()
