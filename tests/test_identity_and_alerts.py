"""M3/M4 tests: form identity resolution and alert de-duplication.

DB is isolated per-test by tests/conftest.py.
"""
from src import apply_helper
from src import alert_store


# ── M4: resolve_form_identity ────────────────────────────────────────────────

def test_identity_prefers_real_fields(monkeypatch):
    monkeypatch.setattr(apply_helper, "FULL_NAME", "Saeed Malakzai")
    monkeypatch.setattr(apply_helper, "SUBMISSION_EMAIL", "saeed@example.com")
    monkeypatch.setattr(apply_helper, "SMTP_FROM_NAME", "Applicant")
    monkeypatch.setattr(apply_helper, "SMTP_USER", "smtp-login@gmail.com")
    name, email = apply_helper.resolve_form_identity()
    assert name == "Saeed Malakzai"
    assert email == "saeed@example.com"


def test_identity_falls_back_to_smtp(monkeypatch):
    monkeypatch.setattr(apply_helper, "FULL_NAME", "")
    monkeypatch.setattr(apply_helper, "SUBMISSION_EMAIL", "")
    monkeypatch.setattr(apply_helper, "SMTP_FROM_NAME", "Applicant")
    monkeypatch.setattr(apply_helper, "SMTP_USER", "smtp-login@gmail.com")
    name, email = apply_helper.resolve_form_identity()
    assert name == "Applicant"
    assert email == "smtp-login@gmail.com"


# ── M3: alert de-duplication ─────────────────────────────────────────────────

def test_alert_dedup_roundtrip():
    assert alert_store.already_alerted("<msg-1@x>") is False
    alert_store.mark_alerted(["<msg-1@x>", "<msg-2@x>"])
    assert alert_store.already_alerted("<msg-1@x>") is True
    assert alert_store.already_alerted("<msg-2@x>") is True
    assert alert_store.already_alerted("<msg-3@x>") is False


def test_empty_id_never_marked():
    alert_store.mark_alerted([""])
    assert alert_store.already_alerted("") is False
