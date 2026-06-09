"""Jobs skipped because a form required answers we couldn't fill honestly.

SQLite-backed (see src/db.py); the GUI surfaces these for manual application.
"""
from typing import List

from src import db


def record_needs_review(job_title: str, form_url: str, reasons: List[str], site: str = "") -> None:
    """Record a needs-review entry (job, URL, why it couldn't be auto-filled)."""
    db.add_needs_review(job_title, form_url, reasons, site)


def load_needs_review() -> list:
    """Return current needs-review entries (pruned), newest first."""
    return db.list_needs_review()
