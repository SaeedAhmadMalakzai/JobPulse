"""Locate bundled assets (app icon) in both dev and PyInstaller-frozen runs."""
import sys
from pathlib import Path

from PySide6.QtGui import QIcon


def _icon_png_path() -> Path | None:
    """Path to assets/icon.png in dev or frozen (.app / onedir) layout."""
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "assets" / "icon.png")
    # Dev: project_root/assets/icon.png  (this file is src/gui/assets.py)
    candidates.append(Path(__file__).resolve().parent.parent.parent / "assets" / "icon.png")
    for c in candidates:
        if c.is_file():
            return c
    return None


def app_icon() -> QIcon:
    """Return the JobPulse window/tray icon, or an empty QIcon if missing."""
    p = _icon_png_path()
    return QIcon(str(p)) if p else QIcon()
