"""SQLite persistence for JobPulse.

Single source of truth for application history, needs-review queue, and alert
de-duplication. Replaces the ad-hoc JSON files but auto-migrates them on first
use, so existing installs keep their history.

Why SQLite over JSON:
- atomic, durable writes with real transactions (no read-modify-write races),
- queryable (powers stats / search in the UI without loading everything),
- handles concurrent access (busy_timeout) instead of a hand-rolled file lock.

Connection: one shared connection (check_same_thread=False) guarded by a lock.
Writes in this app are single-threaded (applies run sequentially); discovery
threads do not touch these tables.
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

from src.config import DATA_DIR, ensure_dirs

DB_PATH = DATA_DIR / "jobpulse.db"

APPLIED_MAX_ENTRIES = 500
APPLIED_MAX_AGE_DAYS = 180
NEEDS_REVIEW_MAX_ENTRIES = 300
NEEDS_REVIEW_MAX_AGE_DAYS = 30
ALERTED_MAX_AGE_DAYS = 90

_conn: Optional[sqlite3.Connection] = None
_lock = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cutoff(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _connect() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id          TEXT PRIMARY KEY,
            site        TEXT,
            applied_at  TEXT NOT NULL,
            dedupe_key  TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_app_applied_at ON applications(applied_at);
        CREATE INDEX IF NOT EXISTS idx_app_key ON applications(dedupe_key);

        CREATE TABLE IF NOT EXISTS needs_review (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT,
            url         TEXT,
            site        TEXT,
            reasons     TEXT,
            at          TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_nr_at ON needs_review(at);

        CREATE TABLE IF NOT EXISTS alerted (
            msg_id      TEXT PRIMARY KEY,
            at          TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_alerted_at ON alerted(at);
        """
    )
    conn.commit()
    return conn


def get_conn() -> sqlite3.Connection:
    """Return the shared connection, creating + migrating on first use."""
    global _conn
    with _lock:
        if _conn is None:
            _conn = _connect()
            _migrate_from_json(_conn)
        return _conn


def reset_for_tests(path: Optional[Path] = None) -> None:
    """Test hook: point the DB at a fresh file/path and drop the cached connection."""
    global _conn, DB_PATH
    with _lock:
        if _conn is not None:
            try:
                _conn.close()
            except sqlite3.Error:
                pass
            _conn = None
        if path is not None:
            DB_PATH = path


# ── one-time JSON → SQLite migration ─────────────────────────────────────────

def _migrate_from_json(conn: sqlite3.Connection) -> None:
    """Import legacy JSON stores once (only if the corresponding table is empty)."""
    _migrate_applied(conn)
    _migrate_needs_review(conn)
    _migrate_alerted(conn)


def _migrate_applied(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0] > 0:
        return
    path = DATA_DIR / "applied.json"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    entries = data.get("entries") or []
    if not entries and data.get("ids"):
        now = _now()
        entries = [{"id": i, "site": "unknown", "applied_at": now, "key": None} for i in data["ids"]]
    rows = [
        (e.get("id"), e.get("site"), e.get("applied_at") or _now(), e.get("key"))
        for e in entries if e.get("id")
    ]
    if rows:
        conn.executemany(
            "INSERT OR IGNORE INTO applications(id, site, applied_at, dedupe_key) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()


def _migrate_needs_review(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM needs_review").fetchone()[0] > 0:
        return
    path = DATA_DIR / "needs_review.json"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    for e in (data.get("entries") or []):
        conn.execute(
            "INSERT INTO needs_review(title, url, site, reasons, at) VALUES (?, ?, ?, ?, ?)",
            (e.get("title"), e.get("url"), e.get("site"), json.dumps(e.get("reasons") or []), e.get("at") or _now()),
        )
    conn.commit()


def _migrate_alerted(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM alerted").fetchone()[0] > 0:
        return
    path = DATA_DIR / "alerted.json"
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    ids = data.get("ids") or {}
    for msg_id, at in ids.items():
        conn.execute("INSERT OR IGNORE INTO alerted(msg_id, at) VALUES (?, ?)", (msg_id, at or _now()))
    conn.commit()


# ── applications ─────────────────────────────────────────────────────────────

def _prune_applications(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM applications WHERE applied_at < ?", (_cutoff(APPLIED_MAX_AGE_DAYS),))
    # Cap to newest N.
    conn.execute(
        """DELETE FROM applications WHERE id NOT IN (
               SELECT id FROM applications ORDER BY applied_at DESC LIMIT ?
           )""",
        (APPLIED_MAX_ENTRIES,),
    )


def add_application(job_id: str, site: str, dedupe_key: str = "") -> None:
    with _lock:
        conn = get_conn()
        conn.execute(
            """INSERT INTO applications(id, site, applied_at, dedupe_key) VALUES (?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET site=excluded.site, applied_at=excluded.applied_at,
                                             dedupe_key=excluded.dedupe_key""",
            (job_id, site, _now(), dedupe_key or None),
        )
        _prune_applications(conn)
        conn.commit()


def applied_ids() -> set:
    conn = get_conn()
    cutoff = _cutoff(APPLIED_MAX_AGE_DAYS)
    rows = conn.execute("SELECT id FROM applications WHERE applied_at >= ?", (cutoff,)).fetchall()
    return {r["id"] for r in rows if r["id"]}


def applied_keys() -> set:
    conn = get_conn()
    cutoff = _cutoff(APPLIED_MAX_AGE_DAYS)
    rows = conn.execute(
        "SELECT dedupe_key FROM applications WHERE applied_at >= ? AND dedupe_key IS NOT NULL", (cutoff,)
    ).fetchall()
    return {r["dedupe_key"] for r in rows if r["dedupe_key"]}


def clear_applications() -> None:
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM applications")
        conn.commit()


# ── needs review ─────────────────────────────────────────────────────────────

def _prune_needs_review(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM needs_review WHERE at < ?", (_cutoff(NEEDS_REVIEW_MAX_AGE_DAYS),))
    conn.execute(
        """DELETE FROM needs_review WHERE id NOT IN (
               SELECT id FROM needs_review ORDER BY at DESC LIMIT ?
           )""",
        (NEEDS_REVIEW_MAX_ENTRIES,),
    )


def add_needs_review(title: str, url: str, reasons: List[str], site: str = "") -> None:
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO needs_review(title, url, site, reasons, at) VALUES (?, ?, ?, ?, ?)",
            (title, url, site, json.dumps(list(reasons)), _now()),
        )
        _prune_needs_review(conn)
        conn.commit()


def list_needs_review() -> list:
    conn = get_conn()
    cutoff = _cutoff(NEEDS_REVIEW_MAX_AGE_DAYS)
    rows = conn.execute(
        "SELECT title, url, site, reasons, at FROM needs_review WHERE at >= ? ORDER BY at DESC", (cutoff,)
    ).fetchall()
    out = []
    for r in rows:
        try:
            reasons = json.loads(r["reasons"] or "[]")
        except ValueError:
            reasons = []
        out.append({"title": r["title"], "url": r["url"], "site": r["site"], "reasons": reasons, "at": r["at"]})
    return out


# ── alerted ──────────────────────────────────────────────────────────────────

def is_alerted(msg_id: str) -> bool:
    if not msg_id:
        return False
    conn = get_conn()
    return conn.execute("SELECT 1 FROM alerted WHERE msg_id = ?", (msg_id,)).fetchone() is not None


def add_alerted(msg_ids) -> None:
    ids = [m for m in (msg_ids if isinstance(msg_ids, (list, tuple, set)) else [msg_ids]) if m]
    if not ids:
        return
    with _lock:
        conn = get_conn()
        now = _now()
        conn.executemany("INSERT OR IGNORE INTO alerted(msg_id, at) VALUES (?, ?)", [(m, now) for m in ids])
        conn.execute("DELETE FROM alerted WHERE at < ?", (_cutoff(ALERTED_MAX_AGE_DAYS),))
        conn.commit()
