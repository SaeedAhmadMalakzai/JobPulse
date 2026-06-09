"""Tests for keyword matching, including the case-sensitive short-acronym rule."""
from src.sites.base import matches_job_keywords


def test_no_keywords_matches_everything():
    assert matches_job_keywords("Anything", "Co", [], []) is True


def test_word_boundary_match():
    assert matches_job_keywords("Senior Python Developer", "Acme", ["python"], []) is True


def test_no_match_returns_false():
    assert matches_job_keywords("Plumber", "Acme", ["python"], []) is False


def test_exclude_keyword_blocks_match():
    assert matches_job_keywords("Senior Python Developer", "Acme", ["python"], ["senior"]) is False


def test_uppercase_acronym_is_case_sensitive():
    # "IT" should match "IT Officer" but NOT the lowercase "it" in "Audit".
    assert matches_job_keywords("IT Officer", "Acme", ["IT"], []) is True
    assert matches_job_keywords("Audit Manager", "Acme", ["IT"], []) is False


def test_longer_keyword_is_case_insensitive():
    assert matches_job_keywords("DATA analyst", "Acme", ["Data"], []) is True
