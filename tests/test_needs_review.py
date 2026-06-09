"""Tests for the needs-review store (C2 skip-and-flag surface; SQLite-backed)."""
from src import needs_review as nr


def test_record_and_load():
    nr.record_needs_review("Data Analyst", "http://x/apply",
                           ["Years of experience", "Cover letter"], site="acbar")
    entries = nr.load_needs_review()
    assert len(entries) == 1
    e = entries[0]
    assert e["title"] == "Data Analyst"
    assert e["url"] == "http://x/apply"
    assert "Years of experience" in e["reasons"]
    assert e["site"] == "acbar"


def test_load_empty_when_absent():
    assert nr.load_needs_review() == []


def test_newest_first():
    nr.record_needs_review("First", "http://x/1", ["r"], site="a")
    nr.record_needs_review("Second", "http://x/2", ["r"], site="a")
    entries = nr.load_needs_review()
    assert entries[0]["title"] == "Second"
