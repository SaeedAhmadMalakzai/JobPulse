"""Tests for job filtering: scope, expiry, age parsing."""
from datetime import date, timedelta

from src.sites.base import JobListing
from src import job_utils as ju


def _job(**kw) -> JobListing:
    base = dict(id="1", title="Engineer", company="Acme", url="http://x")
    base.update(kw)
    return JobListing(**base)


def test_local_afghanistan_is_priority_zero():
    assert ju.job_scope_priority(_job(location="Kabul, Afghanistan")) == 0


def test_global_remote_is_priority_one():
    j = _job(location="", description="Fully remote, open to all nationalities")
    assert ju.job_scope_priority(j) == 1


def test_scope_gate_always_allows_local():
    assert ju.should_apply_by_scope(_job(location="Herat"), False, False) is True


def test_scope_gate_blocks_other_regions_by_default():
    j = _job(location="Berlin, Germany", description="onsite")
    assert ju.should_apply_by_scope(j, apply_global_remote=True, apply_other_regions=False) is False


def test_expired_job_detected():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    assert ju.is_job_expired(_job(close_date=yesterday)) is True


def test_future_close_date_not_expired():
    future = (date.today() + timedelta(days=10)).isoformat()
    assert ju.is_job_expired(_job(close_date=future)) is False


def test_missing_close_date_not_expired():
    assert ju.is_job_expired(_job()) is False


def test_relative_age_parsing_days():
    assert ju._parse_relative_age("Posted 3 days ago") == 3


def test_relative_age_parsing_month():
    assert ju._parse_relative_age("1 month ago") == 30


def test_too_old_job():
    posted = (date.today() - timedelta(days=60)).isoformat()
    assert ju.is_job_too_old(_job(posted_date=posted), max_age_days=30) is True


def test_recent_job_not_too_old():
    posted = (date.today() - timedelta(days=5)).isoformat()
    assert ju.is_job_too_old(_job(posted_date=posted), max_age_days=30) is False
