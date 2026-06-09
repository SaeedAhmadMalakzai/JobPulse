"""Tests for centralized config validation."""
import pytest

from src import config as cfg


@pytest.fixture
def blank_config(monkeypatch, tmp_path):
    """Reset the config surface validate_config() reads to empty/missing."""
    monkeypatch.setattr(cfg, "CV_PATH", tmp_path / "missing.pdf")
    monkeypatch.setattr(cfg, "CV_PATH_EMAIL", None)
    monkeypatch.setattr(cfg, "CV_PATH_FORM", None)
    monkeypatch.setattr(cfg, "SMTP_USER", "")
    monkeypatch.setattr(cfg, "SMTP_PASSWORD", "")
    monkeypatch.setattr(cfg, "IMAP_USER", "")
    monkeypatch.setattr(cfg, "IMAP_PASSWORD", "")
    monkeypatch.setattr(cfg, "FULL_NAME", "")
    monkeypatch.setattr(cfg, "FIRST_NAME", "")
    monkeypatch.setattr(cfg, "SMTP_FROM_NAME", "")
    monkeypatch.setattr(cfg, "SUBMISSION_EMAIL", "")
    monkeypatch.setattr(cfg, "JOB_KEYWORDS", [])
    monkeypatch.setattr(cfg, "FORM_FILL_GUESS", False)
    monkeypatch.setattr(cfg, "DISCOVERY_CONCURRENCY", 4)
    yield


def test_apply_mode_flags_missing_cv_and_smtp(blank_config):
    report = cfg.validate_config(for_apply=True)
    joined = " ".join(report["errors"])
    assert "CV" in joined
    assert "SMTP" in joined


def test_discover_mode_relaxes_apply_errors(blank_config):
    report = cfg.validate_config(for_apply=False)
    assert report["errors"] == []


def test_guess_mode_warns(blank_config, monkeypatch):
    monkeypatch.setattr(cfg, "FORM_FILL_GUESS", True)
    report = cfg.validate_config(for_apply=False)
    assert any("FORM_FILL_GUESS" in w for w in report["warnings"])


def test_empty_keywords_warns(blank_config):
    report = cfg.validate_config(for_apply=False)
    assert any("JOB_KEYWORDS" in w for w in report["warnings"])


def test_valid_config_has_no_errors(blank_config, monkeypatch, tmp_path):
    cv = tmp_path / "cv.pdf"
    cv.write_text("x")
    monkeypatch.setattr(cfg, "CV_PATH", cv)
    monkeypatch.setattr(cfg, "SMTP_USER", "me@gmail.com")
    monkeypatch.setattr(cfg, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(cfg, "SUBMISSION_EMAIL", "me@gmail.com")
    monkeypatch.setattr(cfg, "FULL_NAME", "Saeed")
    monkeypatch.setattr(cfg, "JOB_KEYWORDS", ["python"])
    report = cfg.validate_config(for_apply=True)
    assert report["errors"] == []
