"""Track which inbox messages already triggered a response alert, so a scheduled
run doesn't re-alert the same interview/offer email. SQLite-backed (src/db.py).
"""
from src import db


def already_alerted(msg_id: str) -> bool:
    return db.is_alerted(msg_id)


def mark_alerted(msg_ids) -> None:
    """Record one or more message ids as alerted."""
    db.add_alerted(msg_ids)
