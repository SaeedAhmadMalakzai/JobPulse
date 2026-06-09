"""Persist applied job IDs and dedupe keys. Cap at 500 entries, ignore older than 6 months.

Writes are ATOMIC (tmp file + os.replace) and guarded by a cross-process advisory
lock so a crash mid-write, a killed subprocess, or a scheduled run racing a manual
run can never truncate or corrupt applied.json (which would otherwise wipe the dedupe
history and cause the bot to re-apply to every job).
"""
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.config import DATA_DIR, ensure_dirs

APPLIED_FILE = DATA_DIR / "applied.json"
LOCK_FILE = DATA_DIR / "applied.json.lock"
MAX_ENTRIES = 500
MAX_AGE_DAYS = 180


def _atomic_write_text(path: Path, text: str) -> None:
    """Write text to a temp file in the same dir, then atomically replace the target.

    os.replace is atomic on POSIX and Windows, so readers never observe a partial
    file and a crash mid-write leaves the previous good file intact.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


@contextmanager
def _file_lock():
    """Best-effort cross-process advisory lock around read-modify-write.

    Uses fcntl on POSIX and msvcrt on Windows. Degrades to a no-op if neither is
    available; atomic writes still prevent corruption, the lock only prevents a
    lost update when two processes write concurrently.
    """
    ensure_dirs()
    lock_fh = None
    try:
        lock_fh = open(LOCK_FILE, "a+")
    except OSError:
        yield
        return
    try:
        try:
            import fcntl  # POSIX
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        except ImportError:
            try:
                import msvcrt  # Windows
                lock_fh.seek(0)
                msvcrt.locking(lock_fh.fileno(), msvcrt.LK_LOCK, 1)
            except Exception:
                pass
        except Exception:
            pass
        yield
    finally:
        try:
            try:
                import fcntl
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
            except ImportError:
                try:
                    import msvcrt
                    lock_fh.seek(0)
                    msvcrt.locking(lock_fh.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception:
                    pass
            except Exception:
                pass
        finally:
            lock_fh.close()


def _normalize_key(title: str, company: str) -> str:
    """Normalize for dedupe: same role on different sites -> same key."""
    t = (title or "").strip().lower()
    c = (company or "").strip().lower()
    t = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", t))[:80]
    c = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", "", c))[:60]
    return f"{t}|{c}"


def _load_raw() -> list:
    ensure_dirs()
    if not APPLIED_FILE.exists():
        return []
    try:
        data = json.loads(APPLIED_FILE.read_text())
        entries = data.get("entries", [])
        if not entries and data.get("ids"):
            # Migrate old format: list of ids -> entries with applied_at
            now = datetime.now(timezone.utc).isoformat()
            entries = [{"id": i, "site": "unknown", "applied_at": now, "key": None} for i in data["ids"]]
        return entries
    except Exception:
        return []


def _prune(entries: list) -> list:
    """Keep only last MAX_AGE_DAYS and at most MAX_ENTRIES (newest first)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).isoformat()
    entries = [e for e in entries if (e.get("applied_at") or "") >= cutoff]
    entries.sort(key=lambda e: e.get("applied_at") or "", reverse=True)
    return entries[:MAX_ENTRIES]


def load_applied_ids() -> set:
    """Return set of job IDs we've applied to (within TTL and cap)."""
    from src import db
    return db.applied_ids()


def load_applied_keys() -> set:
    """Return set of normalized title|company keys we've applied to (dedupe across sites)."""
    from src import db
    return db.applied_keys()


def mark_applied(job_id: str, site: str, title: str = "", company: str = "") -> None:
    """Record an application (SQLite-backed; auto-prunes to cap and TTL)."""
    from src import db
    key = _normalize_key(title, company) if (title or company) else ""
    db.add_application(job_id, site, key)


def save_applied_id(job_id: str, site: str) -> None:
    """Backward-compat: mark applied without title/company (no dedupe key)."""
    mark_applied(job_id, site, "", "")


def clear_applied_history() -> None:
    """Clear all applied job history (allows re-applying to same jobs)."""
    from src import db
    db.clear_applications()
