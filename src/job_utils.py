"""Helpers for job filtering (expiry, age, scope)."""
import re
from datetime import date, timedelta
from src.sites.base import JobListing

AFG_TERMS = {
    "afghanistan", "kabul", "herat", "kandahar", "mazar", "jalalabad",
    "helmand", "balkh", "nangarhar", "badakhshan", "ghazni", "kunduz",
}
REMOTE_TERMS = {
    "remote", "work from home", "wfh", "distributed", "anywhere",
    "work from anywhere", "fully remote", "home based",
}
GLOBAL_TERMS = {
    "international", "global", "worldwide", "all nationalities",
    "international applicants", "global applicants", "open globally",
}


def _job_text(job: JobListing) -> str:
    return " ".join([
        job.title or "",
        job.company or "",
        job.location or "",
        job.description or "",
        job.url or "",
    ]).lower()


def is_local_afghanistan_job(job: JobListing) -> bool:
    text = _job_text(job)
    return any(t in text for t in AFG_TERMS)


def is_global_remote_job(job: JobListing) -> bool:
    text = _job_text(job)
    has_remote = any(t in text for t in REMOTE_TERMS)
    has_global = any(t in text for t in GLOBAL_TERMS)
    # Remote postings often imply global when location is unspecified.
    no_location = not (job.location or "").strip()
    return has_remote and (has_global or no_location)


def job_scope_priority(job: JobListing) -> int:
    """0=local Afghanistan (highest), 1=global remote, 2=other."""
    if is_local_afghanistan_job(job):
        return 0
    if is_global_remote_job(job):
        return 1
    return 2


def should_apply_by_scope(job: JobListing, apply_global_remote: bool, apply_other_regions: bool) -> bool:
    """Scope gate: always local AF; optional global-remote and other regions."""
    p = job_scope_priority(job)
    if p == 0:
        return True
    if p == 1:
        return apply_global_remote
    return apply_other_regions


def is_job_expired(job: JobListing) -> bool:
    """Return True if job has a close_date that is in the past."""
    if not job.close_date:
        return False
    try:
        parts = job.close_date.strip().split("-")
        if len(parts) == 3 and len(parts[0]) == 4 and parts[0].isdigit():
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            close = date(y, m, d)
            return date.today() > close
    except Exception:
        pass
    return False


_RELATIVE_AGE_RE = re.compile(
    r"(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago", re.IGNORECASE
)


def _parse_relative_age(text: str) -> int | None:
    """Parse '3 days ago', '1 month ago' etc. into number of days. Returns None if unparsable."""
    m = _RELATIVE_AGE_RE.search(text)
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2).lower()
    multiplier = {
        "second": 0, "minute": 0, "hour": 0,
        "day": 1, "week": 7, "month": 30, "year": 365,
    }
    return n * multiplier.get(unit, 0)


def _parse_posted_date(posted: str) -> date | None:
    """Parse ISO date or relative string into a date object."""
    if not posted:
        return None
    posted = posted.strip()
    try:
        parts = posted.split("-")
        if len(parts) == 3 and len(parts[0]) == 4 and parts[0].isdigit():
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        pass
    days = _parse_relative_age(posted)
    if days is not None:
        return date.today() - timedelta(days=days)
    return None


def is_job_too_old(job: JobListing, max_age_days: int = 30) -> bool:
    """Return True if the job was posted more than max_age_days ago."""
    if not job.posted_date:
        return False
    d = _parse_posted_date(job.posted_date)
    if d is None:
        return False
    age = (date.today() - d).days
    return age > max_age_days
