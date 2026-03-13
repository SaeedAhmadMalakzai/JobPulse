"""JobPulse main window – redesigned with modern layout, animations, and polished styling."""
import json
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QFormLayout,
    QFileDialog,
    QMessageBox,
    QSplitter,
    QGroupBox,
    QScrollArea,
    QFrame,
    QProgressBar,
    QStackedWidget,
    QCheckBox,
    QSpinBox,
    QComboBox,
    QApplication,
    QSizePolicy,
)
from PySide6.QtCore import (
    QProcess,
    QProcessEnvironment,
    Qt,
    QTimer,
    QThread,
    Signal,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtGui import QFont, QColor, QBrush, QShortcut, QKeySequence

from src.gui.env_io import load_env, save_env, get_project_root
from src.gui.output_formatter import parse_log_line, extract_applied_and_skipped
from src.gui.run_history import save_last_run, load_last_run, load_run_history


class InstallDepsThread(QThread):
    """Run pip + playwright (dev) or playwright only (frozen) in background."""
    line_ready = Signal(str)
    finished_ok = Signal(bool)

    def __init__(self, root: Path, python_exe: str = ""):
        super().__init__()
        self._root = root
        self._python = python_exe

    def run(self) -> None:
        import runpy
        ok = True
        if getattr(sys, "frozen", False):
            # Standalone .exe/.app: install Chromium next to the app (one-time download)
            browser_dir = self._root / "playwright-browsers"
            try:
                browser_dir.mkdir(parents=True, exist_ok=True)
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_dir)
                self.line_ready.emit("Downloading Chromium (one-time, ~150 MB)…")
                old_argv = list(sys.argv)
                sys.argv = ["playwright", "install", "chromium"]
                try:
                    runpy.run_module("playwright", run_name="__main__")
                finally:
                    sys.argv = old_argv
                self.line_ready.emit("Chromium ready.")
            except Exception as e:
                self.line_ready.emit(f"Download failed: {e}")
                ok = False
            self.finished_ok.emit(ok)
            return
        import subprocess
        try:
            self.line_ready.emit("Installing Python dependencies (first run)...")
            r = subprocess.run(
                [self._python, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
                cwd=str(self._root),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if r.returncode != 0:
                self.line_ready.emit(
                    f"Warning: pip install returned {r.returncode}. "
                    + (r.stderr or r.stdout or "")[:200]
                )
            else:
                self.line_ready.emit("Python dependencies OK.")
            self.line_ready.emit("Installing Playwright Chromium...")
            r2 = subprocess.run(
                [self._python, "-m", "playwright", "install", "chromium"],
                cwd=str(self._root),
                capture_output=True,
                text=True,
                timeout=180,
            )
            if r2.returncode != 0:
                self.line_ready.emit(
                    "Warning: playwright install had issues. "
                    "You can run 'playwright install chromium' manually."
                )
                ok = False
            else:
                self.line_ready.emit("Playwright Chromium installed.")
        except Exception as e:
            self.line_ready.emit(f"Install error: {e}")
            ok = False
        self.finished_ok.emit(ok)


# Portal display name -> adapter name (for ADAPTERS env)
PORTAL_ADAPTERS = [
    ("Jobs.af", "jobs_af"),
    ("ACBAR", "acbar"),
    ("Wazifaha", "wazifaha"),
    ("Hadaf.af", "hadaf"),
    ("LinkedIn", "linkedin_jobs"),
]

# Keys the GUI manages per tab (subset of .env)
KEYWORDS_KEYS = ("JOB_KEYWORDS", "JOB_EXCLUDE_KEYWORDS")
ACCOUNTS_KEYS = (
    "JOBS_AF_EMAIL", "JOBS_AF_PASSWORD",
    "ACBAR_EMAIL", "ACBAR_PASSWORD",
    "WAZIFAHA_EMAIL", "WAZIFAHA_PASSWORD",
    "HADAF_EMAIL", "HADAF_PASSWORD",
    "LINKEDIN_EMAIL", "LINKEDIN_PASSWORD",
)
SETTINGS_KEYS = (
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM_NAME",
    "ALERT_EMAIL", "IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD",
    "CV_PATH", "COVER_LETTER_PATH",
    "FIRST_NAME", "MIDDLE_NAME", "LAST_NAME", "FULL_NAME", "SALUTATION", "GENDER",
    "PHONE_COUNTRY_CODE", "PHONE_NUMBER", "COUNTRY", "CITY", "YEARS_EXPERIENCE",
    "LINKEDIN_PROFILE_URL", "SUBMISSION_EMAIL", "SUBMISSION_EMAIL_PASSWORD",
    "COVER_LETTER_UNIVERSITY", "COVER_LETTER_PREVIOUS_ORGANIZATION",
    "MAX_JOB_AGE_DAYS", "MAX_APPLICATIONS_PER_RUN",
)
SETTINGS_SMTP = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM_NAME", "ALERT_EMAIL")
SETTINGS_IMAP = ("IMAP_HOST", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD")
SETTINGS_FORM_FILLING = (
    "FIRST_NAME", "MIDDLE_NAME", "LAST_NAME", "FULL_NAME", "SALUTATION", "GENDER",
    "PHONE_COUNTRY_CODE", "PHONE_NUMBER", "COUNTRY", "CITY", "YEARS_EXPERIENCE",
    "LINKEDIN_PROFILE_URL", "SUBMISSION_EMAIL", "SUBMISSION_EMAIL_PASSWORD",
    "COVER_LETTER_UNIVERSITY", "COVER_LETTER_PREVIOUS_ORGANIZATION",
)
SETTINGS_LIMITS = ("MAX_JOB_AGE_DAYS", "MAX_APPLICATIONS_PER_RUN")
ACTIVITY_LIST_MAX_ITEMS = 500
LOG_BATCH_MS = 120


def _make_separator() -> QFrame:
    """Return a thin horizontal separator line."""
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFrameShadow(QFrame.Shadow.Sunken)
    sep.setFixedHeight(1)
    return sep


class MainWindow(QMainWindow):
    # ── Activity log background colours – light theme ────────────────────────
    _LOG_BG_LIGHT = {
        "info":      QColor(238, 242, 255),   # indigo-50
        "success":   QColor(209, 250, 229),   # emerald-100
        "warning":   QColor(254, 243, 199),   # amber-100
        "error":     QColor(254, 226, 226),   # red-100
        "applied":   QColor(187, 247, 208),   # emerald-200
        "skipped":   QColor(254, 249, 195),   # yellow-100
        "discovery": QColor(241, 245, 249),   # slate-100
        "muted":     QColor(248, 250, 252),   # slate-50
    }
    # ── Activity log background colours – dark theme ─────────────────────────
    _LOG_BG_DARK = {
        "info":      QColor(30,  27,  75),    # indigo-950
        "success":   QColor(6,   78,  59),    # emerald-950
        "warning":   QColor(69,  26,   3),    # amber-950
        "error":     QColor(69,  10,  10),    # red-950
        "applied":   QColor(5,   46,  22),    # emerald-950 alt
        "skipped":   QColor(66,  32,   6),    # yellow-950
        "discovery": QColor(15,  23,  42),    # slate-950
        "muted":     QColor(15,  23,  42),
    }
    _TEXT_COLOR_LIGHT = QColor(30, 41, 59)    # slate-800
    _TEXT_COLOR_DARK  = QColor(226, 232, 240) # slate-200

    def __init__(self):
        super().__init__()
        self._process: QProcess | None = None
        self._env = load_env()
        self._shown = False
        self._pulse_state = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(600)
        self._pulse_timer.timeout.connect(self._tick_pulse)

        # Active log colour set (switches with theme)
        self._log_bg = self._LOG_BG_LIGHT
        self._text_color = self._TEXT_COLOR_LIGHT

        self.setWindowTitle("JobPulse")
        self.setMinimumSize(780, 500)
        self.resize(880, 540)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(6, 6, 6, 4)
        root_layout.setSpacing(4)

        # ── Main splitter (left tabs | right panel) ──────────────────────────
        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)

        # Left: tabs
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._build_dashboard(), "  Dashboard  ")
        tabs.addTab(self._build_keywords_tab(), "  Keywords  ")
        tabs.addTab(self._build_accounts_tab(), "  Accounts  ")
        tabs.addTab(self._build_settings_tab(), "  Settings  ")
        tabs.currentChanged.connect(self._on_tab_changed)
        splitter.addWidget(tabs)

        # Right: activity feed + results
        right = QWidget()
        right.setMinimumWidth(260)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(2, 0, 0, 0)
        right_layout.setSpacing(4)

        # Activity feed (with empty state)
        log_group = QGroupBox("Activity Feed")
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(4)
        self._activity_stack = QStackedWidget()
        self._activity_placeholder = QLabel("No runs yet.\nClick Start to run the bot.")
        self._activity_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._activity_placeholder.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 12px;")
        self._activity_stack.addWidget(self._activity_placeholder)
        self._activity_list = QListWidget()
        self._activity_list.setFont(QFont("Segoe UI", 10))
        self._activity_list.setSpacing(1)
        self._activity_list.setUniformItemSizes(False)
        self._activity_list.setWordWrap(True)
        self._log_buffer: list[str] = []
        self._activity_stack.addWidget(self._activity_list)
        log_layout.addWidget(self._activity_stack)

        log_btn_row = QHBoxLayout()
        log_btn_row.setSpacing(4)
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(26)
        clear_btn.clicked.connect(self._clear_output_and_results)
        copy_log_btn = QPushButton("Copy log")
        copy_log_btn.setFixedHeight(26)
        copy_log_btn.setToolTip("Copy the full activity log to clipboard.")
        copy_log_btn.clicked.connect(self._copy_log_to_clipboard)
        tips_btn = QPushButton("Tips")
        tips_btn.setFixedHeight(26)
        tips_btn.clicked.connect(self._show_tips)
        log_btn_row.addWidget(clear_btn)
        log_btn_row.addWidget(copy_log_btn)
        log_btn_row.addWidget(tips_btn)
        log_layout.addLayout(log_btn_row)
        right_layout.addWidget(log_group)

        # Results panel (with filter)
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)
        results_layout.setSpacing(4)
        self._results_filter_edit = QLineEdit()
        self._results_filter_edit.setPlaceholderText("Filter results by text…")
        self._results_filter_edit.textChanged.connect(self._filter_results_lists)
        results_layout.addWidget(self._results_filter_edit)
        results_tabs = QTabWidget()
        results_tabs.setDocumentMode(True)

        self._applied_list = QListWidget()
        self._applied_list.setStyleSheet(
            "QListWidget { background: #f0fdf4; border-color: #bbf7d0; }"
            "QListWidget::item { color: #14532d; }"
            "QListWidget::item:selected { background: #bbf7d0; color: #14532d; }"
        )
        results_tabs.addTab(self._applied_list, "✓  Applied")

        self._skipped_list = QListWidget()
        self._skipped_list.setStyleSheet(
            "QListWidget { background: #fffbeb; border-color: #fde68a; }"
            "QListWidget::item { color: #78350f; }"
            "QListWidget::item:selected { background: #fde68a; color: #78350f; }"
        )
        results_tabs.addTab(self._skipped_list, "⊘  Skipped")
        results_layout.addWidget(results_tabs)

        export_row = QHBoxLayout()
        export_btn = QPushButton("Export (CSV)")
        export_btn.setFixedHeight(26)
        export_btn.setToolTip("Save Applied and Skipped lists to a file.")
        export_btn.clicked.connect(self._export_results)
        copy_results_btn = QPushButton("Copy to clipboard")
        copy_results_btn.setFixedHeight(26)
        copy_results_btn.setToolTip("Copy Applied and Skipped lists to clipboard.")
        copy_results_btn.clicked.connect(self._copy_results_to_clipboard)
        export_row.addWidget(export_btn)
        export_row.addWidget(copy_results_btn)
        results_layout.addLayout(export_row)

        self._results_placeholder = QLabel("Run the bot to see applied and skipped jobs here.")
        self._results_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._results_placeholder.setStyleSheet("color: #94a3b8; font-size: 11px; padding: 12px;")

        self._results_stack = QStackedWidget()
        self._results_stack.addWidget(self._results_placeholder)
        self._results_stack.addWidget(results_group)
        right_layout.addWidget(self._results_stack)
        right_layout.setStretch(0, 3)
        right_layout.setStretch(1, 1)

        splitter.addWidget(right)
        splitter.setSizes([380, 480])
        root_layout.addWidget(splitter, 1)

        # ── Status bar row ───────────────────────────────────────────────────
        status_row = QHBoxLayout()
        status_row.setSpacing(6)

        self._status_dot = QLabel("●")
        self._status_dot.setFixedWidth(18)
        self._status_dot.setStyleSheet("color: #94a3b8; font-size: 16px;")

        self._status_label = QLabel("Idle")
        self._status_label.setObjectName("statusLabel")

        self._progress = QProgressBar()
        self._progress.setMaximum(0)
        self._progress.setFixedHeight(5)
        self._progress.setVisible(False)

        status_row.addWidget(self._status_dot)
        status_row.addWidget(self._status_label)
        status_row.addWidget(self._progress, 1)
        root_layout.addLayout(status_row)

        # ── Init ─────────────────────────────────────────────────────────────
        self._update_run_buttons()
        self._install_thread = None
        self._deps_ok_path = get_project_root() / "data" / ".gui_deps_ok"
        self._status_anim_timer = None
        self._status_dots = 0
        self._schedule_timer = None
        self._log_pending: list = []
        self._log_flush_timer = None
        self._apply_saved_theme()
        self._setup_tray()
        self._reschedule_timer()
        self._setup_shortcuts()

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._shown:
            self._shown = True
            # Smooth fade-in on first show
            self.setWindowOpacity(0.0)
            self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
            self._fade_anim.setDuration(320)
            self._fade_anim.setStartValue(0.0)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade_anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
            self._maybe_show_onboarding()

    def _maybe_show_onboarding(self) -> None:
        flag = get_project_root() / "data" / ".gui_onboarding_done"
        if flag.exists():
            return
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle("Welcome to JobPulse")
        layout = QVBoxLayout(dlg)
        msg = QLabel(
            "Quick start:\n\n"
            "1. Keywords — Add job titles or skills to search for.\n"
            "2. Accounts — Enter portal credentials and choose which sites to use.\n"
            "3. Settings — Set your CV, cover letter, and form-filling details.\n\n"
            "Save each tab, then click Start to run the bot.\n\n"
            "Use Dry run to discover jobs without applying."
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)
        dont_show = QCheckBox("Don't show this again")
        dont_show.setChecked(True)
        layout.addWidget(dont_show)
        btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn.accepted.connect(dlg.accept)
        layout.addWidget(btn)
        dlg.exec()
        if dont_show.isChecked():
            try:
                flag.parent.mkdir(parents=True, exist_ok=True)
                flag.write_text("1", encoding="utf-8")
            except Exception:
                pass

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+Return"), self, self._on_start)
        QShortcut(QKeySequence("Ctrl+."), self, self._on_stop)

    def closeEvent(self, event) -> None:
        """Minimize to tray instead of quitting."""
        if getattr(self, "_tray", None) and self._tray.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

    # ── System tray ──────────────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        from PySide6.QtGui import QIcon, QAction
        from PySide6.QtWidgets import QSystemTrayIcon, QMenu
        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        menu = QMenu()
        run_act = QAction("▶  Run now", self)
        run_act.triggered.connect(self._on_start)
        menu.addAction(run_act)
        stop_act = QAction("■  Stop", self)
        stop_act.triggered.connect(self._on_stop)
        menu.addAction(stop_act)
        menu.addSeparator()
        show_act = QAction("Show window", self)
        show_act.triggered.connect(self.showNormal)
        show_act.triggered.connect(self.raise_)
        show_act.triggered.connect(self.activateWindow)
        menu.addAction(show_act)
        quit_act = QAction("Quit JobPulse", self)
        quit_act.triggered.connect(QApplication.quit)
        menu.addAction(quit_act)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()
        self._update_tray_tooltip()

    def _on_tray_activated(self, reason) -> None:
        from PySide6.QtWidgets import QSystemTrayIcon
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _update_tray_tooltip(self) -> None:
        tray = getattr(self, "_tray", None)
        if not tray:
            return
        last = load_last_run()
        if last:
            a, s = last.get("applied", 0), last.get("skipped", 0)
            tray.setToolTip(f"JobPulse — Last run: {a} applied, {s} skipped")
        else:
            tray.setToolTip("JobPulse")

    # ── Scheduling ────────────────────────────────────────────────────────────

    def _reschedule_timer(self) -> None:
        if self._schedule_timer:
            self._schedule_timer.stop()
            self._schedule_timer = None
        env = load_env()
        hours = int(env.get("SCHEDULE_HOURS") or "0")
        daily = (env.get("SCHEDULE_DAILY_AT") or "").strip()
        if hours <= 0 and not daily:
            return
        self._schedule_timer = QTimer(self)
        self._schedule_timer.timeout.connect(self._on_schedule_tick)
        if hours > 0:
            self._schedule_timer.start(hours * 3600 * 1000)
        else:
            self._schedule_timer.start(60 * 1000)

    def _on_schedule_tick(self) -> None:
        env = load_env()
        daily = (env.get("SCHEDULE_DAILY_AT") or "").strip()
        if daily:
            from datetime import datetime
            try:
                target = datetime.strptime(daily, "%H:%M").time()
                now = datetime.now().time()
                if (now.hour, now.minute) != (target.hour, target.minute):
                    return
            except ValueError:
                return
        if self._process is None or self._process.state() == QProcess.ProcessState.NotRunning:
            self._on_start()

    # ── Dashboard tab ─────────────────────────────────────────────────────────

    def _build_dashboard(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ── Header banner ─────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("dashHeader")
        header.setStyleSheet("""
            QFrame#dashHeader {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #4f46e5, stop:0.6 #6366f1, stop:1 #7c3aed);
                border-radius: 14px;
            }
        """)
        header.setMinimumHeight(58)
        header.setFixedHeight(58)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(14, 6, 14, 6)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        app_title = QLabel("⚡ JobPulse")
        app_title.setStyleSheet(
            "color: #ffffff; font-size: 18px; font-weight: 800; "
            "background: transparent; letter-spacing: -0.3px;"
        )
        app_sub = QLabel("Automated CV Submission Bot")
        app_sub.setStyleSheet(
            "color: rgba(255,255,255,0.85); font-size: 11px; "
            "font-weight: 400; background: transparent;"
        )
        app_sub.setWordWrap(True)
        title_col.addWidget(app_title)
        title_col.addWidget(app_sub)

        shortcut_lbl = QLabel("Ctrl+↵ Start  ·  Ctrl+. Stop")
        shortcut_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.5); font-size: 11px; background: transparent;"
        )
        shortcut_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        h_layout.addLayout(title_col)
        h_layout.addStretch()
        h_layout.addWidget(shortcut_lbl)
        layout.addWidget(header)

        # ── Dry-run checkbox ──────────────────────────────────────────────
        self._dry_run_cb = QCheckBox("  Dry run — discover jobs only, no applications sent")
        self._dry_run_cb.setToolTip(
            "When checked: the bot only finds and lists jobs; it does not submit any applications.\n"
            "When unchecked: the bot discovers jobs and applies using your CV and form details."
        )
        layout.addWidget(self._dry_run_cb)

        # ── Action buttons ────────────────────────────────────────────────
        self._start_btn = QPushButton("🚀   Start Run")
        self._start_btn.setObjectName("startBtn")
        self._start_btn.setToolTip("Save all tabs and start the job discovery and application run.  [Ctrl+Enter]")
        self._start_btn.clicked.connect(self._on_start)

        self._stop_btn = QPushButton("■   Stop")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setToolTip("Stop the current run gracefully.  [Ctrl+.]")
        self._stop_btn.clicked.connect(self._on_stop)
        self._stop_btn.setEnabled(False)

        layout.addWidget(self._start_btn)
        self._run_again_btn = QPushButton("🔄   Run Again")
        self._run_again_btn.setToolTip("Run again with current settings (same as Start).")
        self._run_again_btn.clicked.connect(self._on_start)
        layout.addWidget(self._run_again_btn)
        layout.addWidget(self._stop_btn)

        layout.addWidget(_make_separator())

        # ── Stat cards row ────────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(6)

        self._stats_week_label, week_card = self._make_stat_card("This Week")
        self._stats_month_label, month_card = self._make_stat_card("This Month")
        cards_row.addWidget(week_card)
        cards_row.addWidget(month_card)
        layout.addLayout(cards_row)

        # ── Last run summary ──────────────────────────────────────────────
        self._last_run_label = QLabel("Last run: —")
        self._last_run_label.setObjectName("lastRunLabel")
        self._last_run_label.setWordWrap(True)
        self._last_run_label.setMinimumHeight(28)
        self._last_run_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._last_run_label.setStyleSheet(
            "QLabel#lastRunLabel { font-weight: 600; color: #4f46e5; font-size: 11px; "
            "padding: 6px 8px; margin: 0; min-height: 28px; line-height: 1.3; }"
        )
        layout.addWidget(self._last_run_label)

        view_results_btn = QPushButton("📊   View Results Panel")
        view_results_btn.setToolTip("Switch to the Results panel (Applied / Skipped jobs).")
        view_results_btn.clicked.connect(self._go_to_results)
        layout.addWidget(view_results_btn)

        layout.addWidget(_make_separator())

        # ── Recent runs ───────────────────────────────────────────────────
        recent_label = QLabel("Recent Runs")
        recent_label.setStyleSheet("font-weight: 600; font-size: 11px; color: #64748b;")
        layout.addWidget(recent_label)

        self._history_list = QListWidget()
        self._history_list.setMaximumHeight(115)
        self._history_list.setMinimumHeight(60)
        self._history_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._history_list.setWordWrap(True)
        self._history_list.setSpacing(2)
        self._history_list.setStyleSheet(
            "QListWidget::item { min-height: 22px; padding: 2px 6px; }"
        )
        layout.addWidget(self._history_list)

        check_updates_btn = QPushButton("🔄   Check for Updates")
        check_updates_btn.setToolTip("Open the latest release on GitHub.")
        check_updates_btn.clicked.connect(self._check_for_updates)
        layout.addWidget(check_updates_btn)

        help_btn = QPushButton("📖   Help / Documentation")
        help_btn.setToolTip("Open the README or project documentation.")
        help_btn.clicked.connect(self._open_help)
        layout.addWidget(help_btn)

        # ── Tip ───────────────────────────────────────────────────────────
        tip = QLabel(
            "💡  Fill in Keywords, Accounts, and Settings first — save each tab — then click Start."
        )
        tip.setObjectName("tipBox")
        tip.setWordWrap(True)
        tip.setMinimumHeight(44)
        tip.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(tip)

        layout.addStretch()

        # Load persisted state
        try:
            self._dry_run_cb.setChecked(
                (load_env().get("DRY_RUN") or "").lower() in ("1", "true", "yes")
            )
        except Exception:
            pass
        self._refresh_dashboard_summary()

        # Wrap in scroll area so content is never clipped when window is short
        scroll = QScrollArea()
        scroll.setWidget(w)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        return scroll

    @staticmethod
    def _make_stat_card(title: str):
        """Return (value_label, card_frame). value_label is the big number widget."""
        card = QFrame()
        card.setObjectName("statCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        card.setFixedHeight(52)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 6, 10, 6)
        card_layout.setSpacing(0)
        val_lbl = QLabel("—")
        val_lbl.setObjectName("statValue")
        ttl_lbl = QLabel(title.upper())
        ttl_lbl.setObjectName("statTitle")
        card_layout.addWidget(val_lbl)
        card_layout.addWidget(ttl_lbl)
        return val_lbl, card

    def _go_to_results(self) -> None:
        self._results_stack.setCurrentIndex(1)

    def _refresh_dashboard_summary(self) -> None:
        last = load_last_run()
        if last:
            a, s = last.get("applied", 0), last.get("skipped", 0)
            self._last_run_label.setText(f"Last run:  {a} applied,  {s} skipped")
        else:
            self._last_run_label.setText("Last run: —")

        history = load_run_history()
        self._history_list.clear()
        for r in history[:5]:
            a, s = r.get("applied", 0), r.get("skipped", 0)
            t = r.get("at", "")[:16].replace("T", " ")
            item = QListWidgetItem(f"  {t}   ·   {a} applied,  {s} skipped")
            self._history_list.addItem(item)

        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        week_applied = sum(
            r.get("applied", 0) for r in history if (r.get("at") or "") >= week_start.isoformat()
        )
        month_applied = sum(
            r.get("applied", 0) for r in history if (r.get("at") or "") >= month_start.isoformat()
        )
        self._stats_week_label.setText(str(week_applied))
        self._stats_month_label.setText(str(month_applied))
        self._update_tray_tooltip()

    def _check_for_updates(self) -> None:
        import urllib.request
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/SaeedAhmadMalakzai/JobPulse/releases/latest",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            tag = data.get("tag_name", "?")
            url = data.get("html_url", "https://github.com/SaeedAhmadMalakzai/JobPulse/releases")
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QMessageBox.information(self, "Check for Updates", f"Latest release: {tag}")
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            QMessageBox.warning(self, "Check for Updates", f"Could not check: {e}")

    # ── Keywords tab ──────────────────────────────────────────────────────────

    def _build_keywords_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Include keywords
        inc_group = QGroupBox("Include Keywords")
        inc_layout = QVBoxLayout(inc_group)
        inc_layout.setSpacing(6)
        inc_desc = QLabel("Job titles or skills to match (e.g. \"Data Analyst\", \"Python Developer\")")
        inc_desc.setStyleSheet("color: #64748b; font-size: 12px;")
        inc_layout.addWidget(inc_desc)
        self._include_list = QListWidget()
        inc_layout.addWidget(self._include_list)
        inc_row = QHBoxLayout()
        inc_row.setSpacing(6)
        self._include_edit = QLineEdit()
        self._include_edit.setPlaceholderText("Type a keyword and press Add…")
        self._include_edit.returnPressed.connect(self._add_include_keyword)
        inc_row.addWidget(self._include_edit)
        add_inc = QPushButton("Add")
        add_inc.setFixedWidth(72)
        add_inc.clicked.connect(self._add_include_keyword)
        rem_inc = QPushButton("Remove")
        rem_inc.setFixedWidth(80)
        rem_inc.clicked.connect(lambda: self._remove_selected(self._include_list))
        inc_row.addWidget(add_inc)
        inc_row.addWidget(rem_inc)
        inc_layout.addLayout(inc_row)
        layout.addWidget(inc_group)

        # Exclude keywords
        exc_group = QGroupBox("Exclude Keywords")
        exc_layout = QVBoxLayout(exc_group)
        exc_layout.setSpacing(6)
        exc_desc = QLabel("Job titles to skip even if they match an include keyword")
        exc_desc.setStyleSheet("color: #64748b; font-size: 12px;")
        exc_layout.addWidget(exc_desc)
        self._exclude_list = QListWidget()
        exc_layout.addWidget(self._exclude_list)
        exc_row = QHBoxLayout()
        exc_row.setSpacing(6)
        self._exclude_edit = QLineEdit()
        self._exclude_edit.setPlaceholderText("Type a keyword and press Add…")
        self._exclude_edit.returnPressed.connect(self._add_exclude_keyword)
        exc_row.addWidget(self._exclude_edit)
        add_exc = QPushButton("Add")
        add_exc.setFixedWidth(72)
        add_exc.clicked.connect(self._add_exclude_keyword)
        rem_exc = QPushButton("Remove")
        rem_exc.setFixedWidth(80)
        rem_exc.clicked.connect(lambda: self._remove_selected(self._exclude_list))
        exc_row.addWidget(add_exc)
        exc_row.addWidget(rem_exc)
        exc_layout.addLayout(exc_row)
        layout.addWidget(exc_group)

        save_kw = QPushButton("💾   Save Keywords")
        save_kw.setObjectName("primaryBtn")
        save_kw.setFixedHeight(28)
        save_kw.clicked.connect(self._save_keywords)
        layout.addWidget(save_kw)

        layout.addStretch()
        self._load_keywords()
        return w

    # ── Accounts tab ──────────────────────────────────────────────────────────

    def _build_accounts_tab(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout_inner = QVBoxLayout(inner)
        layout_inner.setSpacing(8)

        # Per-portal enable checkboxes
        portal_group = QGroupBox("Active Portals")
        portal_layout = QVBoxLayout(portal_group)
        portal_layout.setSpacing(6)
        portal_desc = QLabel("Uncheck a portal to skip it during the run")
        portal_desc.setStyleSheet("color: #64748b; font-size: 12px;")
        portal_layout.addWidget(portal_desc)
        self._portal_checks = {}
        for display_name, adapter_name in PORTAL_ADAPTERS:
            cb = QCheckBox(f"  {display_name}")
            cb.setChecked(True)
            self._portal_checks[adapter_name] = cb
            portal_layout.addWidget(cb)
        layout_inner.addWidget(portal_group)

        # Credentials
        creds_group = QGroupBox("Login Credentials")
        form = QFormLayout(creds_group)
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._account_edits = {}
        for key in ACCOUNTS_KEYS:
            is_pass = "PASSWORD" in key
            le = QLineEdit()
            if is_pass:
                le.setEchoMode(QLineEdit.EchoMode.Password)
            le.setPlaceholderText(key)
            self._account_edits[key] = le
            form.addRow(key.replace("_", " ").title(), le)
        layout_inner.addWidget(creds_group)
        layout_inner.addStretch()

        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        save_btn = QPushButton("💾   Save Accounts")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(28)
        save_btn.clicked.connect(self._save_accounts)
        outer.addWidget(save_btn)

        self._load_accounts()
        return w

    # ── Settings tab ──────────────────────────────────────────────────────────

    def _build_settings_tab(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        main_layout = QVBoxLayout(inner)
        main_layout.setSpacing(8)
        self._settings_edits = {}

        def add_section(group_title: str, description: str, keys: tuple) -> None:
            grp = QGroupBox(group_title)
            lay = QFormLayout(grp)
            lay.setSpacing(8)
            lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            if description:
                desc = QLabel(description)
                desc.setWordWrap(True)
                desc.setStyleSheet("color: #64748b; font-size: 12px; margin-bottom: 4px;")
                lay.addRow(desc)
            for key in keys:
                label = key.replace("_", " ").title()
                if key == "MAX_APPLICATIONS_PER_RUN":
                    spin = QSpinBox()
                    spin.setRange(0, 999)
                    spin.setSpecialValueText("No limit")
                    self._settings_edits[key] = spin
                    lay.addRow(label + " (0 = no limit)", spin)
                elif key == "MAX_JOB_AGE_DAYS":
                    spin = QSpinBox()
                    spin.setRange(1, 365)
                    self._settings_edits[key] = spin
                    lay.addRow(label, spin)
                else:
                    le = QLineEdit()
                    if "PASSWORD" in key or "SECRET" in key:
                        le.setEchoMode(QLineEdit.EchoMode.Password)
                    le.setPlaceholderText(key)
                    self._settings_edits[key] = le
                    lay.addRow(label, le)
            main_layout.addWidget(grp)

        add_section(
            "Email (SMTP) — Sending Applications",
            "Used when the bot sends your application by email. Alert email receives notifications.",
            SETTINGS_SMTP,
        )
        add_section(
            "Inbox (IMAP) — Checking Job Responses",
            "Used to check your inbox for replies from employers.",
            SETTINGS_IMAP,
        )

        # CV / Cover letter
        cv_group = QGroupBox("Attachments — CV and Cover Letter")
        cv_layout = QFormLayout(cv_group)
        cv_layout.setSpacing(8)
        cv_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        cv_desc = QLabel("Choose which CV/resume and cover letter to attach to applications.")
        cv_desc.setStyleSheet("color: #64748b; font-size: 12px; margin-bottom: 4px;")
        cv_layout.addRow(cv_desc)

        self._cv_primary_edit = QLineEdit()
        self._cv_primary_edit.setPlaceholderText("Primary CV path (PDF)")
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.addWidget(self._cv_primary_edit)
        b1 = QPushButton("Browse…")
        b1.setFixedWidth(80)
        b1.clicked.connect(lambda: self._browse_cv_path(0))
        row1.addWidget(b1)
        cv_layout.addRow("Primary CV", row1)

        self._cv_alt2_edit = QLineEdit()
        self._cv_alt2_edit.setPlaceholderText("Optional alternate CV")
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.addWidget(self._cv_alt2_edit)
        b2 = QPushButton("Browse…")
        b2.setFixedWidth(80)
        b2.clicked.connect(lambda: self._browse_cv_path(1))
        row2.addWidget(b2)
        cv_layout.addRow("Alternate CV 2", row2)

        self._cv_alt3_edit = QLineEdit()
        self._cv_alt3_edit.setPlaceholderText("Optional alternate CV")
        row3 = QHBoxLayout()
        row3.setSpacing(6)
        row3.addWidget(self._cv_alt3_edit)
        b3 = QPushButton("Browse…")
        b3.setFixedWidth(80)
        b3.clicked.connect(lambda: self._browse_cv_path(2))
        row3.addWidget(b3)
        cv_layout.addRow("Alternate CV 3", row3)

        self._active_cv_combo = QComboBox()
        self._active_cv_combo.addItems(["Primary", "Alternate 2", "Alternate 3"])
        cv_layout.addRow("Use for Runs", self._active_cv_combo)

        cover_le = QLineEdit()
        cover_le.setPlaceholderText("Path to cover letter PDF")
        self._settings_edits["COVER_LETTER_PATH"] = cover_le
        cv_layout.addRow("Cover Letter (PDF)", cover_le)
        self._settings_edits["CV_PATH"] = self._cv_primary_edit
        main_layout.addWidget(cv_group)

        # Form filling
        form_grp = QGroupBox("Form Filling — Your Details")
        form_fill_layout = QFormLayout(form_grp)
        form_fill_layout.setSpacing(8)
        form_fill_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_desc = QLabel(
            "Auto-fill job application forms with your name, phone, location, experience, and LinkedIn."
        )
        form_desc.setWordWrap(True)
        form_desc.setStyleSheet("color: #64748b; font-size: 12px; margin-bottom: 4px;")
        form_fill_layout.addRow(form_desc)
        for key in SETTINGS_FORM_FILLING:
            label = key.replace("_", " ").title()
            le = QLineEdit()
            if "PASSWORD" in key:
                le.setEchoMode(QLineEdit.EchoMode.Password)
            le.setPlaceholderText(key)
            self._settings_edits[key] = le
            form_fill_layout.addRow(label, le)
        main_layout.addWidget(form_grp)

        add_section(
            "Limits",
            "Control how many jobs to consider and how many applications per run.",
            SETTINGS_LIMITS,
        )

        # Appearance
        appearance_grp = QGroupBox("Appearance & Notifications")
        appearance_layout = QVBoxLayout(appearance_grp)
        appearance_layout.setSpacing(8)
        self._dark_theme_cb = QCheckBox("  Dark theme")
        self._dark_theme_cb.stateChanged.connect(self._on_dark_theme_toggled)
        appearance_layout.addWidget(self._dark_theme_cb)
        self._sound_finish_cb = QCheckBox("  Play sound when run finishes")
        appearance_layout.addWidget(self._sound_finish_cb)
        self._start_minimized_cb = QCheckBox("  Start minimized to tray")
        self._start_minimized_cb.setToolTip("On next launch, the window will start hidden in the tray.")
        appearance_layout.addWidget(self._start_minimized_cb)
        main_layout.addWidget(appearance_grp)

        # Schedule
        sched_group = QGroupBox("Schedule (Optional)")
        sched_layout = QFormLayout(sched_group)
        sched_layout.setSpacing(8)
        sched_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._schedule_hours_spin = QSpinBox()
        self._schedule_hours_spin.setRange(0, 168)
        self._schedule_hours_spin.setSpecialValueText("Off")
        sched_layout.addRow("Run every (hours, 0 = off)", self._schedule_hours_spin)
        self._schedule_daily_edit = QLineEdit()
        self._schedule_daily_edit.setPlaceholderText("HH:MM or leave empty")
        sched_layout.addRow("Run daily at (HH:MM)", self._schedule_daily_edit)
        main_layout.addWidget(sched_group)

        # Data
        data_grp = QGroupBox("Data Management")
        data_layout = QVBoxLayout(data_grp)
        data_layout.setSpacing(8)
        clear_btn = QPushButton("🗑   Clear Applied History")
        clear_btn.setObjectName("dangerBtn")
        clear_btn.setToolTip("Remove all recorded applications so you can re-apply to the same jobs.")
        clear_btn.clicked.connect(self._on_clear_applied_history)
        data_layout.addWidget(clear_btn)
        open_data_btn = QPushButton("📂   Open Data Folder")
        open_data_btn.setToolTip("Open the data folder (logs, run history, applied store) in your file manager.")
        open_data_btn.clicked.connect(self._open_data_folder)
        data_layout.addWidget(open_data_btn)
        backup_btn = QPushButton("💾   Backup Config")
        backup_btn.setToolTip("Save a copy of .env to data/backups/ with today's date.")
        backup_btn.clicked.connect(self._backup_config)
        data_layout.addWidget(backup_btn)
        restore_btn = QPushButton("📥   Restore from Backup")
        restore_btn.setToolTip("Restore .env from a backup file.")
        restore_btn.clicked.connect(self._restore_config)
        data_layout.addWidget(restore_btn)
        main_layout.addWidget(data_grp)

        main_layout.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        save_btn = QPushButton("💾   Save Settings")
        save_btn.setObjectName("primaryBtn")
        save_btn.setFixedHeight(28)
        save_btn.setToolTip("Save all settings above to .env")
        save_btn.clicked.connect(self._save_settings)
        outer.addWidget(save_btn)

        self._load_settings()
        self._load_dark_theme()
        self._load_start_minimized()
        return w

    # ── Theme helpers ─────────────────────────────────────────────────────────

    def _load_start_minimized(self) -> None:
        try:
            env = load_env()
            self._start_minimized_cb.setChecked(
                (env.get("GUI_START_MINIMIZED") or "").lower() in ("1", "true", "yes")
            )
        except Exception:
            pass

    def _theme_file(self) -> Path:
        return get_project_root() / "data" / ".gui_theme"

    def _load_dark_theme(self) -> None:
        try:
            self._dark_theme_cb.setChecked(self._theme_file().read_text().strip() == "dark")
        except Exception:
            pass

    def _on_dark_theme_toggled(self) -> None:
        dark = self._dark_theme_cb.isChecked()
        get_project_root().joinpath("data").mkdir(parents=True, exist_ok=True)
        self._theme_file().write_text("dark" if dark else "light", encoding="utf-8")
        self._apply_theme(dark)

    def _apply_theme(self, dark: bool) -> None:
        from src.gui.themes import DARK_STYLESHEET, LIGHT_STYLESHEET
        app = QApplication.instance()
        if app:
            app.setStyleSheet(DARK_STYLESHEET if dark else LIGHT_STYLESHEET)
        # Switch log colour palette
        self._log_bg = self._LOG_BG_DARK if dark else self._LOG_BG_LIGHT
        self._text_color = self._TEXT_COLOR_DARK if dark else self._TEXT_COLOR_LIGHT
        # Update result list inline styles
        if dark:
            self._applied_list.setStyleSheet(
                "QListWidget { background: #052e16; border-color: #14532d; }"
                "QListWidget::item { color: #86efac; }"
                "QListWidget::item:selected { background: #14532d; color: #86efac; }"
            )
            self._skipped_list.setStyleSheet(
                "QListWidget { background: #451a03; border-color: #78350f; }"
                "QListWidget::item { color: #fcd34d; }"
                "QListWidget::item:selected { background: #78350f; color: #fcd34d; }"
            )
            self._last_run_label.setStyleSheet(
                "font-weight: 600; color: #818cf8; font-size: 13px; padding: 2px 0;"
            )
        else:
            self._applied_list.setStyleSheet(
                "QListWidget { background: #f0fdf4; border-color: #bbf7d0; }"
                "QListWidget::item { color: #14532d; }"
                "QListWidget::item:selected { background: #bbf7d0; color: #14532d; }"
            )
            self._skipped_list.setStyleSheet(
                "QListWidget { background: #fffbeb; border-color: #fde68a; }"
                "QListWidget::item { color: #78350f; }"
                "QListWidget::item:selected { background: #fde68a; color: #78350f; }"
            )
            self._last_run_label.setStyleSheet(
                "font-weight: 600; color: #4f46e5; font-size: 13px; padding: 2px 0;"
            )

    def _apply_saved_theme(self) -> None:
        try:
            self._apply_theme(self._theme_file().read_text().strip() == "dark")
        except Exception:
            pass

    # ── CV helpers ────────────────────────────────────────────────────────────

    def _get_selected_cv_path(self) -> str:
        paths = [
            self._cv_primary_edit.text().strip(),
            self._cv_alt2_edit.text().strip(),
            self._cv_alt3_edit.text().strip(),
        ]
        idx = self._active_cv_combo.currentIndex()
        return paths[idx] if 0 <= idx < len(paths) else (paths[0] or "")

    def _browse_cv_path(self, slot: int = 0) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select CV", "", "PDF (*.pdf);;All (*)")
        if path:
            [self._cv_primary_edit, self._cv_alt2_edit, self._cv_alt3_edit][slot].setText(path)

    # ── Keyword helpers ───────────────────────────────────────────────────────

    def _add_include_keyword(self) -> None:
        text = self._include_edit.text().strip()
        if text and not self._include_list.findItems(text, Qt.MatchFlag.MatchExactly):
            self._include_list.addItem(text)
            self._include_edit.clear()

    def _add_exclude_keyword(self) -> None:
        text = self._exclude_edit.text().strip()
        if text and not self._exclude_list.findItems(text, Qt.MatchFlag.MatchExactly):
            self._exclude_list.addItem(text)
            self._exclude_edit.clear()

    def _remove_selected(self, list_widget: QListWidget) -> None:
        for item in list_widget.selectedItems():
            list_widget.takeItem(list_widget.row(item))

    def _load_keywords(self) -> None:
        self._include_list.clear()
        self._exclude_list.clear()
        env = load_env()
        for k in (env.get("JOB_KEYWORDS") or "").split(","):
            k = k.strip()
            if k:
                self._include_list.addItem(k)
        for k in (env.get("JOB_EXCLUDE_KEYWORDS") or "").split(","):
            k = k.strip()
            if k:
                self._exclude_list.addItem(k)

    def _save_keywords(self, show_message: bool = True) -> None:
        include = [self._include_list.item(i).text() for i in range(self._include_list.count())]
        exclude = [self._exclude_list.item(i).text() for i in range(self._exclude_list.count())]
        save_env({"JOB_KEYWORDS": ",".join(include), "JOB_EXCLUDE_KEYWORDS": ",".join(exclude)})
        if show_message:
            QMessageBox.information(self, "Saved", "Keywords saved to .env")

    # ── Account helpers ───────────────────────────────────────────────────────

    def _load_accounts(self) -> None:
        env = load_env()
        for key, le in self._account_edits.items():
            le.setText(env.get(key, ""))
        adapters = [x.strip().lower() for x in (env.get("ADAPTERS") or "").split(",") if x.strip()]
        for adapter_name, cb in self._portal_checks.items():
            cb.setChecked(adapter_name in adapters if adapters else True)

    def _save_accounts(self, show_message: bool = True) -> None:
        updates = {k: le.text().strip() for k, le in self._account_edits.items()}
        enabled = [name for name, cb in self._portal_checks.items() if cb.isChecked()]
        updates["ADAPTERS"] = ",".join(enabled) if enabled else ""
        save_env(updates)
        if show_message:
            QMessageBox.information(self, "Saved", "Account credentials and portal selection saved to .env")

    # ── Settings helpers ──────────────────────────────────────────────────────

    def _load_settings(self) -> None:
        env = load_env()
        self._cv_primary_edit.setText(env.get("CV_PATH", ""))
        self._cv_alt2_edit.setText(env.get("CV_PATH_2", ""))
        self._cv_alt3_edit.setText(env.get("CV_PATH_3", ""))
        ac = (env.get("ACTIVE_CV") or "primary").lower()
        idx = {"primary": 0, "alt2": 1, "alt3": 2}.get(ac, 0)
        self._active_cv_combo.setCurrentIndex(idx)
        try:
            self._sound_finish_cb.setChecked(
                (env.get("GUI_SOUND_FINISH") or "").lower() in ("1", "true", "yes")
            )
        except Exception:
            pass
        try:
            self._schedule_hours_spin.setValue(int(env.get("SCHEDULE_HOURS") or "0"))
        except ValueError:
            self._schedule_hours_spin.setValue(0)
        self._schedule_daily_edit.setText(env.get("SCHEDULE_DAILY_AT", ""))
        try:
            self._start_minimized_cb.setChecked(
                (env.get("GUI_START_MINIMIZED") or "").lower() in ("1", "true", "yes")
            )
        except Exception:
            pass
        for key, widget in self._settings_edits.items():
            if key == "CV_PATH":
                continue
            if isinstance(widget, QSpinBox):
                try:
                    default = "30" if key == "MAX_JOB_AGE_DAYS" else "0"
                    widget.setValue(int(env.get(key, default) or default))
                except ValueError:
                    widget.setValue(30 if key == "MAX_JOB_AGE_DAYS" else 0)
            else:
                widget.setText(env.get(key, ""))

    def _save_settings(self, show_message: bool = True) -> None:
        updates = {}
        for k, widget in self._settings_edits.items():
            if k == "CV_PATH":
                continue
            if isinstance(widget, QSpinBox):
                updates[k] = str(widget.value())
            else:
                updates[k] = widget.text().strip()
        labels = ["primary", "alt2", "alt3"]
        paths = [
            self._cv_primary_edit.text().strip(),
            self._cv_alt2_edit.text().strip(),
            self._cv_alt3_edit.text().strip(),
        ]
        idx = self._active_cv_combo.currentIndex()
        updates["CV_PATH"] = paths[idx] if idx < len(paths) else paths[0]
        updates["CV_PATH_2"] = paths[1]
        updates["CV_PATH_3"] = paths[2]
        updates["ACTIVE_CV"] = labels[idx] if idx < 3 else "primary"
        updates["GUI_SOUND_FINISH"] = "true" if self._sound_finish_cb.isChecked() else "false"
        updates["GUI_START_MINIMIZED"] = "true" if self._start_minimized_cb.isChecked() else "false"
        updates["SCHEDULE_HOURS"] = str(self._schedule_hours_spin.value())
        updates["SCHEDULE_DAILY_AT"] = self._schedule_daily_edit.text().strip()
        save_env(updates)
        self._reschedule_timer()
        if show_message:
            QMessageBox.information(self, "Saved", "Settings saved to .env")

    def _on_clear_applied_history(self) -> None:
        from src.applied_store import clear_applied_history
        reply = QMessageBox.question(
            self,
            "Clear Applied History",
            "This will clear all recorded applications — you'll be able to re-apply to the same jobs.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            clear_applied_history()
            QMessageBox.information(self, "Done", "Applied history cleared.")

    # ── Activity log ──────────────────────────────────────────────────────────

    def _append_log_line(self, line: str) -> None:
        kind, display = parse_log_line(line)
        if not display and kind == "muted":
            return
        self._log_buffer.append(line)
        self._log_pending.append((kind, display))
        if self._log_flush_timer is None:
            self._log_flush_timer = QTimer(self)
            self._log_flush_timer.setSingleShot(True)
            self._log_flush_timer.timeout.connect(self._flush_log_pending)
        self._log_flush_timer.start(LOG_BATCH_MS)

    def _flush_log_pending(self) -> None:
        for kind, display in self._log_pending:
            bg = self._log_bg.get(kind, self._log_bg["info"])
            item = QListWidgetItem(f"  {display}")
            item.setBackground(QBrush(bg))
            item.setForeground(QBrush(self._text_color))
            self._activity_list.addItem(item)
        if getattr(self, "_activity_stack", None) and self._activity_list.count() > 0:
            self._activity_stack.setCurrentIndex(1)
        while self._activity_list.count() > ACTIVITY_LIST_MAX_ITEMS:
            self._activity_list.takeItem(0)
        self._log_pending.clear()
        self._activity_list.scrollToBottom()

    def _show_tips(self) -> None:
        QMessageBox.information(
            self,
            "JobPulse — Tips",
            "• Dry run: discovers jobs without sending any applications.\n\n"
            "• Shortcuts: Ctrl+Enter = Start,  Ctrl+. = Stop.\n\n"
            "• Save each tab (Keywords, Accounts, Settings) before clicking Start.\n\n"
            "• Activity feed colour guide:\n"
            "    Blue = info  ·  Green = applied  ·  Yellow = skipped  ·  Red = errors\n\n"
            "• Stop tries to end the run gracefully, then forces after a few seconds.\n\n"
            "• First run may install dependencies automatically — wait for 'Dependencies ready'.\n\n"
            "• If Chromium is missing, run in terminal:  playwright install chromium",
        )

    def _clear_output_and_results(self) -> None:
        self._activity_list.clear()
        self._log_buffer.clear()
        self._log_pending.clear()
        if getattr(self, "_activity_stack", None):
            self._activity_stack.setCurrentIndex(0)
        self._applied_list.clear()
        self._skipped_list.clear()
        self._results_stack.setCurrentIndex(0)
        if getattr(self, "_results_filter_edit", None):
            self._results_filter_edit.clear()

    def _show_results(self, applied: list, skipped: list) -> None:
        self._applied_list.clear()
        self._skipped_list.clear()
        for t in applied:
            self._applied_list.addItem(f"  ✓  {t}")
        for title, reason in skipped:
            self._skipped_list.addItem(f"  ⊘  {title} — {reason}")
        self._results_stack.setCurrentIndex(1)
        self._filter_results_lists()

    def _export_results(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Results", "", "CSV (*.csv);;Text (*.txt)")
        if not path:
            return
        applied = [self._applied_list.item(i).text().strip() for i in range(self._applied_list.count())]
        skipped = [self._skipped_list.item(i).text().strip() for i in range(self._skipped_list.count())]
        if path.endswith(".csv"):
            lines = ["Applied", *applied, "", "Skipped (title — reason)", *skipped]
            content = "\n".join(lines)
        else:
            content = (
                "Applied:\n"
                + "\n".join(f"  - {t}" for t in applied)
                + "\n\nSkipped:\n"
                + "\n".join(f"  - {t}" for t in skipped)
            )
        Path(path).write_text(content, encoding="utf-8")
        QMessageBox.information(self, "Export", f"Saved to {path}")

    def _filter_results_lists(self) -> None:
        text = getattr(self, "_results_filter_edit", None)
        text = (text.text() if text else "").strip().lower()
        for lst in [self._applied_list, self._skipped_list]:
            for i in range(lst.count()):
                item = lst.item(i)
                show = not text or text in (item.text() or "").lower()
                lst.setRowHidden(i, not show)

    def _copy_log_to_clipboard(self) -> None:
        content = "\n".join(self._log_buffer) if self._log_buffer else "No log content."
        cb = QApplication.clipboard()
        if cb:
            cb.setText(content)
            QMessageBox.information(self, "Copy log", "Activity log copied to clipboard.")

    def _copy_results_to_clipboard(self) -> None:
        applied = [self._applied_list.item(i).text().strip() for i in range(self._applied_list.count())]
        skipped = [self._skipped_list.item(i).text().strip() for i in range(self._skipped_list.count())]
        content = (
            "Applied:\n" + "\n".join(f"  - {t}" for t in applied)
            + "\n\nSkipped:\n" + "\n".join(f"  - {t}" for t in skipped)
        )
        cb = QApplication.clipboard()
        if cb:
            cb.setText(content)
            QMessageBox.information(self, "Copy results", "Results copied to clipboard.")

    def _on_tab_changed(self, index: int) -> None:
        if index == 0:
            self._refresh_dashboard_summary()

    def _open_help(self) -> None:
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        url = "https://github.com/SaeedAhmadMalakzai/JobPulse#readme"
        readme = get_project_root() / "README.md"
        if readme.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(readme)))
        else:
            QDesktopServices.openUrl(QUrl(url))

    def _open_data_folder(self) -> None:
        data_dir = get_project_root() / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        path = str(data_dir)
        if sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        elif sys.platform == "win32":
            subprocess.run(["explorer", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)

    def _backup_config(self) -> None:
        from datetime import date
        root = get_project_root()
        env_path = root / ".env"
        if not env_path.exists():
            QMessageBox.warning(self, "Backup", "No .env file found to backup.")
            return
        backup_dir = root / "data" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        dest = backup_dir / f".env.{date.today().isoformat()}"
        import shutil
        shutil.copy2(env_path, dest)
        QMessageBox.information(self, "Backup", f"Config backed up to:\n{dest}")

    def _restore_config(self) -> None:
        root = get_project_root()
        backup_dir = root / "data" / "backups"
        path, _ = QFileDialog.getOpenFileName(
            self, "Restore from Backup", str(backup_dir) if backup_dir.exists() else "",
            "Env (*.env.*);;All (*)"
        )
        if not path:
            return
        dest = root / ".env"
        import shutil
        shutil.copy2(path, dest)
        self._load_settings()
        self._load_accounts()
        self._load_keywords()
        QMessageBox.information(self, "Restore", "Config restored. Settings reloaded.")

    # ── Run state & animations ────────────────────────────────────────────────

    def _update_run_buttons(self) -> None:
        state = self._process.state() if self._process else QProcess.ProcessState.NotRunning
        running = self._process is not None and state != QProcess.ProcessState.NotRunning
        self._start_btn.setEnabled(not running)
        if getattr(self, "_run_again_btn", None):
            self._run_again_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        self._progress.setVisible(running)
        if running:
            self._status_label.setText("Running")
            self._status_label.setStyleSheet("font-weight: 700; font-size: 13px; color: #059669;")
            self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
            self._status_dot.setStyleSheet("color: #94a3b8; font-size: 16px;")
            self._status_label.setText("Idle")
            self._status_label.setStyleSheet("font-weight: 700; font-size: 13px; color: #94a3b8;")

    def _tick_pulse(self) -> None:
        """Alternate the status dot colour to create a pulsing animation."""
        self._pulse_state = not self._pulse_state
        color = "#059669" if self._pulse_state else "#a7f3d0"
        self._status_dot.setStyleSheet(f"color: {color}; font-size: 16px;")

    # ── Bot lifecycle ─────────────────────────────────────────────────────────

    def _on_start(self) -> None:
        # Persist current form values to .env so the bot subprocess sees them (no popups)
        self._save_keywords(show_message=False)
        self._save_accounts(show_message=False)
        self._save_settings(show_message=False)
        root = get_project_root()
        self._log_buffer.clear()

        root.joinpath("data").mkdir(parents=True, exist_ok=True)
        if not self._deps_ok_path.exists():
            self._append_log_line("First run: checking dependencies…" if not getattr(sys, "frozen", False) else "First run: downloading Chromium…")
            self._start_btn.setEnabled(False)
            self._install_thread = InstallDepsThread(root, "" if getattr(sys, "frozen", False) else sys.executable)
            self._install_thread.line_ready.connect(self._append_log_line)
            self._install_thread.finished_ok.connect(self._on_install_finished)
            self._install_thread.start()
            return

        lock_file = root / "data" / ".run.lock"
        if lock_file.exists() and not self._clear_stale_run_lock(lock_file):
            QMessageBox.warning(
                self,
                "Already Running",
                "A run is already in progress. Stop it first, or wait for it to finish.",
            )
            return

        cv_path = self._get_selected_cv_path()
        if not self._dry_run_cb.isChecked() and cv_path:
            if not Path(cv_path).expanduser().exists():
                reply = QMessageBox.question(
                    self,
                    "CV File Not Found",
                    f"The selected CV path does not exist:\n{cv_path}\n\nContinue anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return
        elif not self._dry_run_cb.isChecked() and not cv_path:
            QMessageBox.warning(
                self, "No CV Selected",
                "Select a CV in Settings (Attachments) and save before running with apply."
            )
            return
        self._run_bot()

    def _on_install_finished(self, ok: bool) -> None:
        self._install_thread = None
        self._start_btn.setEnabled(True)
        if ok:
            self._deps_ok_path.write_text("ok", encoding="utf-8")
            self._append_log_line("✓ Dependencies ready. Starting bot…")
            self._run_bot()
        else:
            self._append_log_line(
                "⚠ You can still try Start again, or run 'playwright install chromium' in a terminal."
            )

    def _clear_stale_run_lock(self, lock_file: Path) -> bool:
        """If lock file is stale (process no longer running), remove it and return True. Else return False."""
        if not lock_file.exists():
            return True
        try:
            raw = lock_file.read_text(encoding="utf-8").strip()
            if not raw:
                lock_file.unlink(missing_ok=True)
                return True
            pid = int(raw)
            if pid <= 0:
                lock_file.unlink(missing_ok=True)
                return True
            os.kill(pid, 0)
            return False
        except (ValueError, ProcessLookupError, OSError):
            lock_file.unlink(missing_ok=True)
            return True

    def _run_bot(self) -> None:
        root = get_project_root()
        lock_file = root / "data" / ".run.lock"
        if lock_file.exists() and not self._clear_stale_run_lock(lock_file):
            QMessageBox.warning(
                self,
                "Already Running",
                "A run is already in progress. Stop it first, or wait for it to finish.",
            )
            return
        self._run_lock_file = lock_file
        try:
            lock_file.parent.mkdir(parents=True, exist_ok=True)
            lock_file.write_text("0", encoding="utf-8")
        except Exception:
            pass

        self._log_buffer.clear()
        self._log_pending.clear()
        self._append_log_line("▶ Starting JobPulse bot…")

        self._process = QProcess(self)
        self._process.setWorkingDirectory(str(root))
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)
        self._process.stateChanged.connect(self._on_process_state_changed)

        proc_env = QProcessEnvironment.systemEnvironment()
        proc_env.insert("PYTHONPATH", str(root))
        cv_path = self._get_selected_cv_path()
        if cv_path:
            proc_env.insert("CV_PATH", cv_path)
        proc_env.insert("DRY_RUN", "1" if self._dry_run_cb.isChecked() else "0")
        if getattr(sys, "frozen", False):
            browser_dir = root / "playwright-browsers"
            proc_env.insert("PLAYWRIGHT_BROWSERS_PATH", str(browser_dir))
        self._process.setProcessEnvironment(proc_env)

        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--run-bot"]
        else:
            cmd = [sys.executable, "-m", "src.main"]
        self._process.start(cmd[0], cmd[1:])
        self._update_run_buttons()
        QTimer.singleShot(150, self._update_run_buttons)

    def _on_stdout(self) -> None:
        if self._process:
            data = self._process.readAllStandardOutput()
            text = bytes(data).decode("utf-8", errors="replace")
            for line in text.splitlines():
                if line.strip():
                    self._append_log_line(line)

    def _on_stderr(self) -> None:
        if self._process:
            data = self._process.readAllStandardError()
            text = bytes(data).decode("utf-8", errors="replace")
            for line in text.splitlines():
                if line.strip():
                    self._append_log_line(line)

    def _tick_status_animation(self) -> None:
        # Legacy – kept for compatibility; pulse is now handled by _tick_pulse
        pass

    def _on_process_state_changed(self, state: QProcess.ProcessState) -> None:
        self._update_run_buttons()
        if state == QProcess.ProcessState.Running and self._process and getattr(self, "_run_lock_file", None):
            try:
                pid = self._process.pid()
                if pid and pid > 0:
                    self._run_lock_file.write_text(str(pid), encoding="utf-8")
            except Exception:
                pass

    def _on_finished(self, code: int, status: QProcess.ExitStatus) -> None:
        self._process = None
        try:
            lock = getattr(self, "_run_lock_file", None) or (get_project_root() / "data" / ".run.lock")
            lock.unlink(missing_ok=True)
        except Exception:
            pass
        self._update_run_buttons()
        full_log = "\n".join(self._log_buffer)
        applied, skipped = extract_applied_and_skipped(full_log)
        save_last_run(len(applied), len(skipped))
        self._refresh_dashboard_summary()
        self._show_results(applied, skipped)
        msg = "✅" if code == 0 else "⚠"
        self._append_log_line(f"{msg} Run finished (exit code {code}).")
        self._notify_run_finished(len(applied), len(skipped))
        self._play_finish_sound()

    def _play_finish_sound(self) -> None:
        env = load_env()
        if (env.get("GUI_SOUND_FINISH") or "").lower() not in ("1", "true", "yes"):
            return
        try:
            QApplication.beep()
        except Exception:
            pass

    def _notify_run_finished(self, applied: int, skipped: int) -> None:
        msg = f"JobPulse: {applied} applied, {skipped} skipped"
        try:
            if sys.platform == "darwin":
                subprocess.run(
                    ["osascript", "-e", f'display notification "{msg}" with title "JobPulse"'],
                    capture_output=True,
                    timeout=2,
                )
        except Exception:
            pass

    def _on_stop(self) -> None:
        if not self._process or self._process.state() == QProcess.ProcessState.NotRunning:
            return
        self._append_log_line("⏹ Stopping… (graceful, then force if needed)")
        self._process.terminate()
        QTimer.singleShot(3000, self._kill_process_if_running)

    def _kill_process_if_running(self) -> None:
        if self._process and self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()
            self._append_log_line("■ Stopped by user (force).")
