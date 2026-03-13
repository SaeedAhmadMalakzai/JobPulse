"""Entry point for JobPulse GUI. When frozen (PyInstaller), --run-bot runs the CLI bot and exits."""
import sys


def main_gui() -> int:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from src.gui.main_window import MainWindow
    from src.gui.env_io import load_env

    app = QApplication(sys.argv)
    app.setApplicationName("JobPulse")
    app.setApplicationDisplayName("JobPulse")
    # Fusion base style gives consistent cross-platform rendering; QSS overrides visuals
    app.setStyle("Fusion")

    # Apply saved theme before window appears (avoids flash)
    from pathlib import Path
    from src.gui.env_io import get_project_root
    theme_file = get_project_root() / "data" / ".gui_theme"
    dark = False
    try:
        dark = theme_file.read_text().strip() == "dark"
    except Exception:
        pass
    from src.gui.themes import DARK_STYLESHEET, LIGHT_STYLESHEET
    app.setStyleSheet(DARK_STYLESHEET if dark else LIGHT_STYLESHEET)

    win = MainWindow()
    start_minimized = (load_env().get("GUI_START_MINIMIZED") or "").lower() in ("1", "true", "yes")
    if start_minimized:
        # Don't call win.show() so the fade-in and tray setup still run silently
        win.showMinimized()
        win.hide()
    else:
        win.show()
    return app.exec()


if __name__ == "__main__":
    if "--run-bot" in sys.argv:
        # Used by GUI when frozen: spawns self with --run-bot to run the bot in a subprocess
        sys.argv.remove("--run-bot")
        from src.main import main
        sys.exit(main())
    sys.exit(main_gui())
