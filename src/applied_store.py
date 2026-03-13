"""Persist applied job IDs and dedupe keys. Cap at 500 entries, ignore older than 6 months."""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.config import DATA_DIR, ensure_dirs

APPLIED_FILE = DATA_DIR / "applied.json"
MAX_ENTRIES = 500
MAX_AGE_DAYS = 180


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
    entries = _prune(_load_raw())
    return set(e.get("id") for e in entries if e.get("id"))


def load_applied_keys() -> set:
    """Return set of normalized title|company keys we've applied to (dedupe across sites)."""
    entries = _prune(_load_raw())
    return set(e.get("key") for e in entries if e.get("key"))


def mark_applied(job_id: str, site: str, title: str = "", company: str = "") -> None:
    """Record an application; prune store to cap and TTL."""
    ensure_dirs()
    entries = _load_raw()
    now = datetime.now(timezone.utc).isoformat()
    key = _normalize_key(title, company) if (title or company) else ""
    entries.append({
        "id": job_id,
        "site": site,
        "applied_at": now,
        "key": key or None,
    })
    entries = _prune(entries)
    data = {"entries": entries, "updated": now}
    APPLIED_FILE.write_text(json.dumps(data, indent=2))


def save_applied_id(job_id: str, site: str) -> None:
    """Backward-compat: mark applied without title/company (no dedupe key)."""
    mark_applied(job_id, site, "", "")


def clear_applied_history() -> None:
    """Clear all applied job history (allows re-applying to same jobs)."""
    ensure_dirs()
    data = {"entries": [], "updated": datetime.now(timezone.utc).isoformat()}
    APPLIED_FILE.write_text(json.dumps(data, indent=2))
