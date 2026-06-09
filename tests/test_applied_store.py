"""Application-history tests (SQLite-backed via src.db; isolated by conftest)."""
from datetime import datetime, timezone, timedelta

from src import applied_store as store
from src import db


def test_mark_and_load_roundtrip():
    store.mark_applied("acbar_1", "acbar", "Data Analyst", "ACBAR")
    assert "acbar_1" in store.load_applied_ids()
    assert store._normalize_key("Data Analyst", "ACBAR") in store.load_applied_keys()


def test_dedupe_key_same_role_across_sites():
    a = store._normalize_key("Senior  Data Analyst!", "ACBAR Org")
    b = store._normalize_key("senior data analyst", "acbar org")
    assert a == b


def test_clear_history_empties_store():
    store.mark_applied("x1", "site", "T", "C")
    store.clear_applied_history()
    assert store.load_applied_ids() == set()


def test_upsert_same_id_does_not_duplicate():
    store.mark_applied("dup", "site", "T", "C")
    store.mark_applied("dup", "site", "T", "C")
    conn = db.get_conn()
    count = conn.execute("SELECT COUNT(*) FROM applications WHERE id = 'dup'").fetchone()[0]
    assert count == 1


def test_ttl_prune_excludes_old_entries():
    conn = db.get_conn()
    old = (datetime.now(timezone.utc) - timedelta(days=db.APPLIED_MAX_AGE_DAYS + 5)).isoformat()
    conn.execute("INSERT INTO applications(id, site, applied_at, dedupe_key) VALUES (?,?,?,?)",
                 ("old", "s", old, None))
    conn.commit()
    store.mark_applied("new", "s", "T", "C")
    ids = store.load_applied_ids()
    assert "new" in ids and "old" not in ids


def test_cap_enforced_on_write():
    conn = db.get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        "INSERT INTO applications(id, site, applied_at, dedupe_key) VALUES (?,?,?,?)",
        [(str(i), "s", now, None) for i in range(db.APPLIED_MAX_ENTRIES + 50)],
    )
    conn.commit()
    store.mark_applied("trigger", "s", "T", "C")  # triggers prune
    total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    assert total <= db.APPLIED_MAX_ENTRIES


def test_migration_imports_legacy_applied_json(tmp_path, monkeypatch):
    import json
    # Write a legacy applied.json into the migration source dir, then force a fresh DB.
    (tmp_path / "applied.json").write_text(json.dumps({
        "entries": [{"id": "legacy_1", "site": "acbar", "applied_at": datetime.now(timezone.utc).isoformat(),
                     "key": "data analyst|acbar"}]
    }))
    db.reset_for_tests(tmp_path / "migrated.db")
    assert "legacy_1" in store.load_applied_ids()
