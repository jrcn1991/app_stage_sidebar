import json, os, sys
from pathlib import Path

# ===== Config =====
def get_base_dir() -> Path:
    """Return a writable base directory for config storage."""
    if hasattr(sys, "_MEIPASS"):
        # Running from PyInstaller bundle
        base = Path(os.getenv("APPDATA", Path.home())) / "StageSidebar"
    else:
        # Running from source
        base = Path(__file__).resolve().parent
    base.mkdir(parents=True, exist_ok=True)
    return base

PROJECT_DIR = get_base_dir()
CONF_DIR = PROJECT_DIR / "config"
CONF_DIR.mkdir(parents=True, exist_ok=True)
CONF_PATH = CONF_DIR / "config.json"

DEFAULT_CONF = {
    "monitor": 0,
    "edge": "left",
    "bar_width": 220,
    "bar_height_pct": 80,
    "bar_offset_y": 125,
    "visible_count": 5,
    "overlap_pct": 0,
    "gap_px": 15,
    "item_width": 220,
    "item_height": 165,
    "exclude_execs": [],
    "focus_single": True,
    "start_hidden": False,
    "icon_size": 30,
    "icon_anchor": "bottom-left",
    "icon_offset_x": 6,
    "icon_offset_y": 6,
    "icon_allow_drag": False,
    "show_title": False,
    "maximize_on_restore": True,
}

def load_conf() -> dict:
    if CONF_PATH.exists():
        try:
            with open(CONF_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**DEFAULT_CONF, **data}
        except Exception:
            pass
    return DEFAULT_CONF.copy()

def save_conf(d: dict) -> bool:
    try:
        with open(CONF_PATH, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
