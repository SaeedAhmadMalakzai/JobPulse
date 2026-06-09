"""Tests for SMTP send: 465 SSL fallback when STARTTLS/587 is blocked, and that
auth failures do NOT fall back or retry."""
import smtplib

import pytest

from src import email_utils as eu


@pytest.fixture(autouse=True)
def _smtp_env(monkeypatch):
    monkeypatch.setattr(eu, "SMTP_USER", "me@hiringorg.test")
    monkeypatch.setattr(eu, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(eu, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(eu, "SMTP_PORT", 587)
    monkeypatch.setattr(eu, "_save_to_sent_folder", lambda msg: None)
    monkeypatch.setattr(eu.time, "sleep", lambda *_: None)  # no real backoff in tests
    yield


class _Blocked587:
    def __init__(self, host, port, timeout=None):
        raise TimeoutError("[Errno 60] Operation timed out")


class _OK465:
    sent_to = None
    def __init__(self, host, port, timeout=None):
        assert port == 465
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def login(self, u, p): pass
    def sendmail(self, frm, to, data): _OK465.sent_to = to


def test_falls_back_to_465_when_587_blocked(monkeypatch):
    _OK465.sent_to = None
    monkeypatch.setattr(smtplib, "SMTP", _Blocked587)
    monkeypatch.setattr(smtplib, "SMTP_SSL", _OK465)
    ok = eu.send_application_email("hr@hiringorg.test", "Application: Engineer", "Hello")
    assert ok is True
    assert _OK465.sent_to == "hr@hiringorg.test"


def test_auth_failure_does_not_fall_back(monkeypatch):
    ssl_calls = {"n": 0}

    class _AuthFail:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, u, p): raise smtplib.SMTPAuthenticationError(535, b"BadCredentials")
        def sendmail(self, *a): pass

    class _SSLCounter:
        def __init__(self, *a, **k): ssl_calls["n"] += 1
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def login(self, *a): pass
        def sendmail(self, *a): pass

    monkeypatch.setattr(smtplib, "SMTP", _AuthFail)
    monkeypatch.setattr(smtplib, "SMTP_SSL", _SSLCounter)
    ok = eu.send_application_email("hr@hiringorg.test", "Subj", "Body")
    assert ok is False
    assert ssl_calls["n"] == 0  # never attempted SSL fallback on an auth error
