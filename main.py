import sys, os
from PySide6 import QtGui, QtWidgets
from sidebar import Sidebar

def resource_path(relative_path):
    """Resolve path for PyInstaller (inside or outside bundle)."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    icon_path = resource_path("docs/stage-manager-icon.png")
    app.setWindowIcon(QtGui.QIcon(icon_path))

    w = Sidebar()
    if w.start_hidden:
        w.hide()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
