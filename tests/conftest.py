"""Shared test fixtures.

Every test gets a fresh, isolated SQLite database in a tmp dir, and the JSON
migration source is pointed at the (empty) tmp dir so tests never read or write
the real data/ directory.
"""
import pytest

from src import db

_ORIGINAL_DB_PATH = db.DB_PATH


@pytest.fixture(autouse=True)
def isolate_db(tmp_path, monkeypatch):
    # Migration looks for legacy JSON under db.DATA_DIR; point it at an empty dir.
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    db.reset_for_tests(tmp_path / "test.db")
    try:
        yield
    finally:
        db.reset_for_tests(_ORIGINAL_DB_PATH)
