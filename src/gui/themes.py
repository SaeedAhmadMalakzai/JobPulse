"""JobPulse – modern, polished Qt stylesheets for light and dark mode.

Design system:
  Primary  : #4f46e5 (indigo-600)  /  #818cf8 (indigo-400 dark)
  Success  : #059669 (emerald-600) /  #34d399 (emerald-400 dark)
  Danger   : #dc2626 (red-600)     /  #f87171 (red-400 dark)
  Warning  : #d97706 (amber-600)
  Bg light : #f0f4f8  |  Surface: #ffffff  |  Border: #dde3ee
  Bg dark  : #0f172a  |  Surface: #1e293b  |  Border: #334155
"""

# ── Object name aliases (used in main_window.py) ─────────────────────────────
# startBtn   → big green "Start Run" button
# stopBtn    → red "Stop" button
# primaryBtn → indigo save / action buttons
# dangerBtn  → destructive action (clear history, etc.)
# statCard   → dashboard stat card frame
# statValue  → large number inside stat card
# statTitle  → tiny caption inside stat card
# dashHeader → gradient header banner frame
# tipBox     → info-tip QLabel

# ─────────────────────────────────────────────────────────────────────────────
#  LIGHT THEME
# ─────────────────────────────────────────────────────────────────────────────
LIGHT_STYLESHEET = """
/* ── Window & Base ─────────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #f0f4f8;
}
QWidget {
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    font-size: 11px;
    color: #1e293b;
}

/* ── Group Boxes ────────────────────────────────────────────────────────── */
QGroupBox {
    font-weight: 700;
    font-size: 10px;
    color: #64748b;
    margin-top: 14px;
    padding-top: 10px;
    padding-bottom: 6px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background: #ffffff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #64748b;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* ── Tab Widget ─────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #ffffff;
    top: -1px;
}
QTabBar {
    qproperty-drawBase: 0;
}
QTabBar::tab {
    background: transparent;
    color: #64748b;
    padding: 6px 14px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 11px;
    font-weight: 500;
    min-width: 60px;
}
QTabBar::tab:selected {
    color: #4f46e5;
    border-bottom: 3px solid #4f46e5;
    font-weight: 700;
}
QTabBar::tab:hover:!selected {
    color: #4f46e5;
    background: #eef2ff;
    border-radius: 8px 8px 0 0;
}

/* ── Buttons – default ──────────────────────────────────────────────────── */
QPushButton {
    min-width: 72px;
    min-height: 26px;
    padding: 5px 12px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 11px;
    color: #374151;
    background: #f1f5f9;
    border: 1px solid #dde3ee;
    outline: none;
}
QPushButton:hover {
    background: #e0e7ff;
    color: #4f46e5;
    border-color: #a5b4fc;
}
QPushButton:pressed {
    background: #c7d2fe;
    color: #3730a3;
}
QPushButton:disabled {
    background: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* ── Start button (green) ───────────────────────────────────────────────── */
QPushButton#startBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #059669, stop:1 #047857);
    color: #ffffff;
    border: 1px solid #047857;
    font-size: 12px;
    font-weight: 700;
    min-height: 34px;
    border-radius: 8px;
    letter-spacing: 0.2px;
}
QPushButton#startBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #047857, stop:1 #065f46);
    border-color: #059669;
    color: #ffffff;
}
QPushButton#startBtn:pressed {
    background: #065f46;
}
QPushButton#startBtn:disabled {
    background: #d1fae5;
    color: #6ee7b7;
    border-color: #a7f3d0;
}

/* ── Stop button (red) ──────────────────────────────────────────────────── */
QPushButton#stopBtn {
    background: #fef2f2;
    color: #dc2626;
    border: 1px solid #fca5a5;
    min-height: 26px;
    font-weight: 600;
}
QPushButton#stopBtn:hover {
    background: #dc2626;
    color: #ffffff;
    border-color: #dc2626;
}
QPushButton#stopBtn:pressed {
    background: #b91c1c;
    color: #ffffff;
}
QPushButton#stopBtn:disabled {
    background: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* ── Primary / Save buttons (indigo) ────────────────────────────────────── */
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #6366f1, stop:1 #4f46e5);
    color: #ffffff;
    border: 1px solid #4338ca;
    font-weight: 700;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4f46e5, stop:1 #4338ca);
    color: #ffffff;
}
QPushButton#primaryBtn:pressed {
    background: #3730a3;
    color: #ffffff;
}

/* ── Danger button ──────────────────────────────────────────────────────── */
QPushButton#dangerBtn {
    background: #fef2f2;
    color: #dc2626;
    border: 1px solid #fca5a5;
}
QPushButton#dangerBtn:hover {
    background: #dc2626;
    color: #ffffff;
    border-color: #b91c1c;
}

/* ── Line Edits ─────────────────────────────────────────────────────────── */
QLineEdit {
    font-size: 11px;
    color: #1e293b;
    background: #ffffff;
    border: 1px solid #dde3ee;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 20px;
    selection-color: #ffffff;
    selection-background-color: #4f46e5;
}
QLineEdit:focus {
    border: 1.5px solid #4f46e5;
    background: #fafbff;
}
QLineEdit:disabled {
    background: #f8fafc;
    color: #94a3b8;
    border-color: #e2e8f0;
}
QLineEdit[echoMode="2"] {
    font-family: monospace;
    letter-spacing: 2px;
}

/* ── Spin Box ───────────────────────────────────────────────────────────── */
QSpinBox {
    font-size: 11px;
    color: #1e293b;
    background: #ffffff;
    border: 1px solid #dde3ee;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 20px;
}
QSpinBox:focus {
    border: 1.5px solid #4f46e5;
    background: #fafbff;
}
QSpinBox::up-button, QSpinBox::down-button {
    border: none;
    background: transparent;
    width: 18px;
}

/* ── Combo Box ──────────────────────────────────────────────────────────── */
QComboBox {
    font-size: 13px;
    color: #1e293b;
    background: #ffffff;
    border: 1.5px solid #dde3ee;
    border-radius: 8px;
    padding: 7px 12px;
    min-height: 28px;
}
QComboBox:focus {
    border: 1.5px solid #4f46e5;
}
QComboBox::drop-down {
    border: none;
    width: 26px;
}
QComboBox::down-arrow {
    width: 10px;
    height: 10px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #eef2ff;
    selection-color: #4f46e5;
    outline: none;
}

/* ── List Widget ────────────────────────────────────────────────────────── */
QListWidget {
    font-size: 13px;
    border: 1.5px solid #e2e8f0;
    border-radius: 10px;
    padding: 4px;
    color: #1e293b;
    background: #ffffff;
    outline: none;
}
QListWidget::item {
    color: #1e293b;
    padding: 7px 10px;
    border-radius: 6px;
    border: none;
}
QListWidget::item:selected {
    background: #eef2ff;
    color: #4f46e5;
}
QListWidget::item:hover:!selected {
    background: #f8fafc;
}

/* ── Progress Bar ───────────────────────────────────────────────────────── */
QProgressBar {
    border: none;
    border-radius: 4px;
    background: #e2e8f0;
    text-align: center;
    color: transparent;
    min-height: 5px;
    max-height: 5px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4f46e5, stop:0.5 #818cf8, stop:1 #4f46e5);
    border-radius: 4px;
}

/* ── Labels ─────────────────────────────────────────────────────────────── */
QLabel {
    color: #1e293b;
    font-size: 13px;
}
QLabel#statValue {
    color: #4f46e5;
    font-size: 16px;
    font-weight: 700;
    background: transparent;
}
QLabel#statTitle {
    color: #94a3b8;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    background: transparent;
}
QLabel#tipBox {
    color: #3730a3;
    font-size: 10px;
    padding: 8px 10px;
    min-height: 44px;
    background: #eef2ff;
    border-radius: 6px;
    border-left: 3px solid #4f46e5;
}
QLabel#statusLabel {
    font-weight: 700;
    font-size: 11px;
    color: #475569;
}

/* ── Stat Card ──────────────────────────────────────────────────────────── */
QFrame#statCard {
    background: #fafbff;
    border: 1px solid #e0e7ff;
    border-radius: 8px;
}

/* ── Check Boxes ────────────────────────────────────────────────────────── */
QCheckBox {
    color: #1e293b;
    font-size: 13px;
    spacing: 9px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid #dde3ee;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #4f46e5;
    border-color: #4f46e5;
}
QCheckBox::indicator:hover {
    border-color: #818cf8;
}

/* ── Scroll Bars ────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 4px;
    min-height: 36px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 4px;
    min-width: 36px;
}
QScrollBar::handle:horizontal:hover {
    background: #94a3b8;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
}

/* ── Scroll Area ────────────────────────────────────────────────────────── */
QScrollArea {
    background: transparent;
    border: none;
}

/* ── Tool Tips ──────────────────────────────────────────────────────────── */
QToolTip {
    background: #1e293b;
    color: #f1f5f9;
    border: none;
    padding: 6px 12px;
    border-radius: 7px;
    font-size: 12px;
    font-weight: 500;
}

/* ── Splitter ───────────────────────────────────────────────────────────── */
QSplitter::handle {
    background: #e2e8f0;
    width: 1px;
}
QSplitter::handle:hover {
    background: #4f46e5;
}

/* ── Menu ───────────────────────────────────────────────────────────────── */
QMenu {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 5px;
}
QMenu::item {
    padding: 8px 18px;
    border-radius: 6px;
    color: #1e293b;
    font-size: 13px;
}
QMenu::item:selected {
    background: #eef2ff;
    color: #4f46e5;
}
QMenu::separator {
    height: 1px;
    background: #e2e8f0;
    margin: 4px 8px;
}

/* ── Message Box ────────────────────────────────────────────────────────── */
QMessageBox {
    background: #ffffff;
}
QMessageBox QLabel {
    color: #1e293b;
    font-size: 11px;
}

/* ── Frame dividers ─────────────────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #e2e8f0;
}

/* ── Form Layout labels ─────────────────────────────────────────────────── */
QFormLayout QLabel {
    color: #475569;
    font-size: 11px;
    font-weight: 600;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
#  DARK THEME
# ─────────────────────────────────────────────────────────────────────────────
DARK_STYLESHEET = """
/* ── Window & Base ─────────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background-color: #0f172a;
}
QWidget {
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    font-size: 11px;
    color: #f1f5f9;
}

/* ── Group Boxes ────────────────────────────────────────────────────────── */
QGroupBox {
    font-weight: 700;
    font-size: 10px;
    color: #475569;
    margin-top: 14px;
    padding-top: 10px;
    padding-bottom: 6px;
    border: 1px solid #1e293b;
    border-radius: 8px;
    background: #1e293b;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #475569;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* ── Tab Widget ─────────────────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #1e293b;
    border-radius: 8px;
    background: #1e293b;
    top: -1px;
}
QTabBar {
    qproperty-drawBase: 0;
}
QTabBar::tab {
    background: transparent;
    color: #475569;
    padding: 6px 14px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 11px;
    font-weight: 500;
    min-width: 60px;
}
QTabBar::tab:selected {
    color: #818cf8;
    border-bottom: 2px solid #818cf8;
    font-weight: 700;
}
QTabBar::tab:hover:!selected {
    color: #818cf8;
    background: #1e1b4b;
    border-radius: 8px 8px 0 0;
}

/* ── Buttons – default ──────────────────────────────────────────────────── */
QPushButton {
    min-width: 72px;
    min-height: 26px;
    padding: 5px 12px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 11px;
    color: #cbd5e1;
    background: #273549;
    border: 1px solid #334155;
    outline: none;
}
QPushButton:hover {
    background: #2d2b69;
    color: #a5b4fc;
    border-color: #4f46e5;
}
QPushButton:pressed {
    background: #1e1b4b;
    color: #a5b4fc;
}
QPushButton:disabled {
    background: #1a2535;
    color: #334155;
    border-color: #1e293b;
}

/* ── Start button (green) ───────────────────────────────────────────────── */
QPushButton#startBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #065f46, stop:1 #047857);
    color: #6ee7b7;
    border: 1px solid #059669;
    font-size: 12px;
    font-weight: 700;
    min-height: 34px;
    border-radius: 8px;
    letter-spacing: 0.2px;
}
QPushButton#startBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #047857, stop:1 #059669);
    color: #d1fae5;
    border-color: #34d399;
}
QPushButton#startBtn:pressed {
    background: #064e3b;
    color: #d1fae5;
}
QPushButton#startBtn:disabled {
    background: #022c22;
    color: #065f46;
    border-color: #022c22;
}

/* ── Stop button (red) ──────────────────────────────────────────────────── */
QPushButton#stopBtn {
    background: #450a0a;
    color: #f87171;
    border: 1px solid #7f1d1d;
    min-height: 26px;
    font-weight: 600;
}
QPushButton#stopBtn:hover {
    background: #991b1b;
    color: #fecaca;
    border-color: #dc2626;
}
QPushButton#stopBtn:pressed {
    background: #7f1d1d;
    color: #fecaca;
}
QPushButton#stopBtn:disabled {
    background: #1a2535;
    color: #334155;
    border-color: #1e293b;
}

/* ── Primary / Save buttons (indigo) ────────────────────────────────────── */
QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #312e81, stop:1 #1e1b4b);
    color: #a5b4fc;
    border: 1px solid #4f46e5;
    font-weight: 700;
}
QPushButton#primaryBtn:hover {
    background: #4f46e5;
    color: #ffffff;
    border-color: #6366f1;
}
QPushButton#primaryBtn:pressed {
    background: #3730a3;
    color: #ffffff;
}

/* ── Danger button ──────────────────────────────────────────────────────── */
QPushButton#dangerBtn {
    background: #450a0a;
    color: #f87171;
    border: 1px solid #7f1d1d;
}
QPushButton#dangerBtn:hover {
    background: #991b1b;
    color: #fecaca;
    border-color: #dc2626;
}

/* ── Line Edits ─────────────────────────────────────────────────────────── */
QLineEdit {
    font-size: 13px;
    color: #f1f5f9;
    background: #0f172a;
    border: 1.5px solid #334155;
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 22px;
    selection-color: #0f172a;
    selection-background-color: #818cf8;
}
QLineEdit:focus {
    border: 1.5px solid #818cf8;
    background: #111827;
}
QLineEdit:disabled {
    background: #1a2535;
    color: #334155;
    border-color: #1e293b;
}

/* ── Spin Box ───────────────────────────────────────────────────────────── */
QSpinBox {
    font-size: 13px;
    color: #f1f5f9;
    background: #0f172a;
    border: 1.5px solid #334155;
    border-radius: 8px;
    padding: 7px 12px;
    min-height: 22px;
}
QSpinBox:focus {
    border: 1.5px solid #818cf8;
}
QSpinBox::up-button, QSpinBox::down-button {
    border: none;
    background: transparent;
    width: 18px;
}

/* ── Combo Box ──────────────────────────────────────────────────────────── */
QComboBox {
    font-size: 13px;
    color: #f1f5f9;
    background: #0f172a;
    border: 1.5px solid #334155;
    border-radius: 8px;
    padding: 7px 12px;
    min-height: 28px;
}
QComboBox:focus {
    border: 1.5px solid #818cf8;
}
QComboBox::drop-down {
    border: none;
    width: 26px;
}
QComboBox QAbstractItemView {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #312e81;
    selection-color: #a5b4fc;
    outline: none;
}

/* ── List Widget ────────────────────────────────────────────────────────── */
QListWidget {
    font-size: 13px;
    border: 1.5px solid #1e293b;
    border-radius: 10px;
    padding: 4px;
    color: #f1f5f9;
    background: #0f172a;
    outline: none;
}
QListWidget::item {
    color: #f1f5f9;
    padding: 7px 10px;
    border-radius: 6px;
    border: none;
}
QListWidget::item:selected {
    background: #312e81;
    color: #a5b4fc;
}
QListWidget::item:hover:!selected {
    background: #1e293b;
}

/* ── Progress Bar ───────────────────────────────────────────────────────── */
QProgressBar {
    border: none;
    border-radius: 4px;
    background: #1e293b;
    text-align: center;
    color: transparent;
    min-height: 5px;
    max-height: 5px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4f46e5, stop:0.5 #818cf8, stop:1 #4f46e5);
    border-radius: 4px;
}

/* ── Labels ─────────────────────────────────────────────────────────────── */
QLabel {
    color: #f1f5f9;
    font-size: 13px;
}
QLabel#statValue {
    color: #818cf8;
    font-size: 22px;
    font-weight: 700;
    background: transparent;
}
QLabel#statTitle {
    color: #475569;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    background: transparent;
}
QLabel#tipBox {
    color: #a5b4fc;
    font-size: 10px;
    padding: 8px 12px;
    min-height: 44px;
    background: #1e1b4b;
    border-radius: 8px;
    border-left: 4px solid #4f46e5;
}
QLabel#statusLabel {
    font-weight: 700;
    font-size: 13px;
    color: #64748b;
}

/* ── Stat Card ──────────────────────────────────────────────────────────── */
QFrame#statCard {
    background: #1a1935;
    border: 1.5px solid #312e81;
    border-radius: 12px;
}

/* ── Check Boxes ────────────────────────────────────────────────────────── */
QCheckBox {
    color: #f1f5f9;
    font-size: 13px;
    spacing: 9px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1.5px solid #334155;
    background: #0f172a;
}
QCheckBox::indicator:checked {
    background: #4f46e5;
    border-color: #818cf8;
}
QCheckBox::indicator:hover {
    border-color: #818cf8;
}

/* ── Scroll Bars ────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 36px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #334155;
    border-radius: 4px;
    min-width: 36px;
}
QScrollBar::handle:horizontal:hover {
    background: #475569;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
    background: none;
}

/* ── Scroll Area ────────────────────────────────────────────────────────── */
QScrollArea {
    background: transparent;
    border: none;
}

/* ── Tool Tips ──────────────────────────────────────────────────────────── */
QToolTip {
    background: #f1f5f9;
    color: #0f172a;
    border: none;
    padding: 6px 12px;
    border-radius: 7px;
    font-size: 12px;
    font-weight: 500;
}

/* ── Splitter ───────────────────────────────────────────────────────────── */
QSplitter::handle {
    background: #1e293b;
    width: 1px;
}
QSplitter::handle:hover {
    background: #4f46e5;
}

/* ── Menu ───────────────────────────────────────────────────────────────── */
QMenu {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 5px;
}
QMenu::item {
    padding: 8px 18px;
    border-radius: 6px;
    color: #f1f5f9;
    font-size: 13px;
}
QMenu::item:selected {
    background: #312e81;
    color: #a5b4fc;
}
QMenu::separator {
    height: 1px;
    background: #334155;
    margin: 4px 8px;
}

/* ── Message Box ────────────────────────────────────────────────────────── */
QMessageBox {
    background: #1e293b;
}
QMessageBox QLabel {
    color: #f1f5f9;
    font-size: 13px;
}

/* ── Frame dividers ─────────────────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: #334155;
}

/* ── Form Layout labels ─────────────────────────────────────────────────── */
QFormLayout QLabel {
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
}
"""
