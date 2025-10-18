from __future__ import annotations
from sidebar import *
import sys

# ===== main =====
def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pix = QtGui.QPixmap(22, 22); pix.fill(QtGui.QColor(0, 120, 215))
    app.setWindowIcon(QtGui.QIcon(pix))
    w = Sidebar()
    if w.start_hidden:
        w.hide()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())