"""
Stage Sidebar Configurações
"""
from __future__ import annotations
from config import * # Importa tudo
from tile import *



# ===== Settings Dialog =====
class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent, monitors, state):
        super().__init__(parent)
        self.setWindowTitle("Stage Sidebar - Settings")
        lay = QtWidgets.QFormLayout(self)

        self.cmb_screen = QtWidgets.QComboBox()
        for i, m in enumerate(monitors, 1):
            l, t, r, b = m["rect"]
            self.cmb_screen.addItem(f"Monitor {i} ({r - l}x{b - t})", userData=i - 1)

        self.cmb_edge = QtWidgets.QComboBox(); self.cmb_edge.addItems(["Left", "Right"])
        self.sp_w = QtWidgets.QSpinBox(); self.sp_w.setRange(160, 1200)
        self.sp_hpct = QtWidgets.QSpinBox(); self.sp_hpct.setRange(20, 100); self.sp_hpct.setSuffix(" %")
        self.sp_offy = QtWidgets.QSpinBox(); self.sp_offy.setRange(0, 3000); self.sp_offy.setSuffix(" px")
        self.sp_vis = QtWidgets.QSpinBox(); self.sp_vis.setRange(1, 20)
        self.sp_ov = QtWidgets.QSpinBox(); self.sp_ov.setRange(0, 80); self.sp_ov.setSuffix(" %")
        self.sp_gap = QtWidgets.QSpinBox(); self.sp_gap.setRange(0, 50); self.sp_gap.setSuffix(" px")
        self.sp_item_w = QtWidgets.QSpinBox(); self.sp_item_w.setRange(120, 1200); self.sp_item_w.setSuffix(" px")
        self.sp_item_h = QtWidgets.QSpinBox(); self.sp_item_h.setRange(80, 1200);  self.sp_item_h.setSuffix(" px")

        # Overlay controls
        self.sp_icon_size = QtWidgets.QSpinBox(); self.sp_icon_size.setRange(12, 128); self.sp_icon_size.setSuffix(" px")
        self.cmb_icon_anchor = QtWidgets.QComboBox(); self.cmb_icon_anchor.addItems([
            "bottom-left","bottom-right","top-left","top-right","center","title-left","title-right","title-center"
        ])
        self.sp_icon_offx = QtWidgets.QSpinBox(); self.sp_icon_offx.setRange(-2000, 2000); self.sp_icon_offx.setSuffix(" px")
        self.sp_icon_offy = QtWidgets.QSpinBox(); self.sp_icon_offy.setRange(-2000, 2000); self.sp_icon_offy.setSuffix(" px")
        self.chk_icon_drag = QtWidgets.QCheckBox("Allow dragging icon")

        self.txt_excl = QtWidgets.QPlainTextEdit(); self.txt_excl.setPlaceholderText("exe per line, ex.: winrar.exe")
        self.chk_focus = QtWidgets.QCheckBox("Single Focus")
        self.chk_start_hidden = QtWidgets.QCheckBox("Start hidden (tray only)")

        # já existente (se você adicionou antes)
        self.chk_show_title = QtWidgets.QCheckBox("Show title")

        # NOVO
        self.chk_max_restore = QtWidgets.QCheckBox("Maximize on restore")

        lay.addRow("Monitor:", self.cmb_screen)
        lay.addRow("Side:", self.cmb_edge)
        lay.addRow("bar_width:", self.sp_w)
        lay.addRow("bar_height_pct (%):", self.sp_hpct)
        lay.addRow("bar_offset_y(px):", self.sp_offy)
        lay.addRow("visible_count:", self.sp_vis)
        lay.addRow("overlap_pct (%):", self.sp_ov)
        lay.addRow("gap_px (px):", self.sp_gap)
        lay.addRow("item_width (px):", self.sp_item_w)
        lay.addRow("item_height (px):", self.sp_item_h)
        lay.addRow("icon_size:", self.sp_icon_size)
        lay.addRow("icon_anchor:", self.cmb_icon_anchor)
        lay.addRow("icon_offset_x:", self.sp_icon_offx)
        lay.addRow("icon_offset_y:", self.sp_icon_offy)
        lay.addRow(self.chk_icon_drag)
        lay.addRow("exclude_execs:", self.txt_excl)
        lay.addRow(self.chk_focus)
        lay.addRow(self.chk_start_hidden)
        lay.addRow(self.chk_show_title)
        lay.addRow(self.chk_max_restore)  # NOVO

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Apply | QtWidgets.QDialogButtonBox.Cancel)
        lay.addRow(btns)
        btns.accepted.connect(self.on_save)
        btns.button(QtWidgets.QDialogButtonBox.Apply).clicked.connect(self.on_apply)
        btns.rejected.connect(self.reject)

        self.apply_state(state)

    def apply_state(self, s: dict) -> None:
        self.cmb_screen.setCurrentIndex(int(s["monitor"]))
        self.cmb_edge.setCurrentIndex(0 if s["edge"] == "left" else 1)
        self.sp_w.setValue(int(s["bar_width"]))
        self.sp_hpct.setValue(int(s["bar_height_pct"]))
        self.sp_offy.setValue(int(s["bar_offset_y"]))
        self.sp_vis.setValue(int(s["visible_count"]))
        self.sp_ov.setValue(int(s["overlap_pct"]))
        self.sp_gap.setValue(int(s.get("gap_px", 2)))
        self.sp_item_w.setValue(int(s.get("item_width", 200)))
        self.sp_item_h.setValue(int(s.get("item_height", 140)))
        self.chk_focus.setChecked(bool(s["focus_single"]))
        self.chk_start_hidden.setChecked(bool(s.get("start_hidden", True)))
        excl = s.get("exclude_execs", [])
        self.txt_excl.setPlainText("\n".join(excl))
        self.sp_icon_size.setValue(int(s.get("icon_size", 22)))
        i_anchor = self.cmb_icon_anchor.findText(str(s.get("icon_anchor", "bottom-left")))
        self.cmb_icon_anchor.setCurrentIndex(max(0, i_anchor))
        self.sp_icon_offx.setValue(int(s.get("icon_offset_x", 6)))
        self.sp_icon_offy.setValue(int(s.get("icon_offset_y", 6)))
        self.chk_icon_drag.setChecked(bool(s.get("icon_allow_drag", True)))
        self.chk_show_title.setChecked(bool(s.get("show_title", True)))
        # NOVO
        self.chk_max_restore.setChecked(bool(s.get("maximize_on_restore", False)))

    def state(self) -> dict:
        excl = [ln.strip().lower() for ln in self.txt_excl.toPlainText().splitlines() if ln.strip()]
        return {
            "monitor": self.cmb_screen.currentData(),
            "edge": "left" if self.cmb_edge.currentIndex() == 0 else "right",
            "bar_width": self.sp_w.value(),
            "bar_height_pct": self.sp_hpct.value(),
            "bar_offset_y": self.sp_offy.value(),
            "visible_count": self.sp_vis.value(),
            "overlap_pct": self.sp_ov.value(),
            "gap_px": self.sp_gap.value(),
            "item_width": self.sp_item_w.value(),
            "item_height": self.sp_item_h.value(),
            "exclude_execs": excl,
            "focus_single": self.chk_focus.isChecked(),
            "start_hidden": self.chk_start_hidden.isChecked(),
            "icon_size": self.sp_icon_size.value(),
            "icon_anchor": self.cmb_icon_anchor.currentText(),
            "icon_offset_x": self.sp_icon_offx.value(),
            "icon_offset_y": self.sp_icon_offy.value(),
            "icon_allow_drag": self.chk_icon_drag.isChecked(),
            "show_title": self.chk_show_title.isChecked(),
            # NOVO
            "maximize_on_restore": self.chk_max_restore.isChecked(),
        }

    def on_apply(self) -> None:
        self.parent().apply_settings(self.state())

    def on_save(self) -> None:
        st = self.state()
        self.parent().apply_settings(st)
        save_conf(st)
        self.accept()