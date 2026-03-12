"""Base class for portal adapters."""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional


@dataclass
class JobListing:
    """A single job listing."""
    id: str
    title: str
    company: str
    url: str
    location: str = ""
    description: str = ""
    apply_by_email: Optional[str] = None
    apply_url: Optional[str] = None
    close_date: Optional[str] = None
    posted_date: Optional[str] = None   # ISO "YYYY-MM-DD" or relative like "2 days ago"
    raw: Optional[dict] = None


@lru_cache(maxsize=4)
def _build_keyword_patterns(keywords_tuple: tuple) -> list:
    """Compile word-boundary regex patterns from keyword list (cached).
    Short all-uppercase tokens (IT, AI, ML, QA, …) are matched case-sensitively
    to avoid false hits on common English words like 'it'.
    """
    patterns = []
    for kw in keywords_tuple:
        kw = kw.strip()
        if not kw:
            continue
        escaped = re.escape(kw)
        if len(kw) <= 3 and kw == kw.upper() and kw.isalpha():
            patterns.append(re.compile(rf"\b{escaped}\b"))
        else:
            patterns.append(re.compile(rf"\b{escaped}\b", re.IGNORECASE))
    return patterns


def matches_job_keywords(
    title: str,
    company: str,
    keywords: list,
    exclude_keywords: list,
) -> bool:
    """Word-boundary keyword matching for job filtering.
    Returns True if any keyword matches as a whole word in title+company.
    Returns False if any exclude keyword matches.
    """
    if not keywords:
        return True
    text = f"{title} {company}"
    if exclude_keywords:
        ex_patterns = _build_keyword_patterns(tuple(exclude_keywords))
        if any(p.search(text) for p in ex_patterns):
            return False
    patterns = _build_keyword_patterns(tuple(keywords))
    return any(p.search(text) for p in patterns)


class SiteAdapter(ABC):
    """Adapter for one job portal: discover jobs and apply."""

    name: str = "base"

    @abstractmethod
    def discover_jobs(self) -> List[JobListing]:
        """Fetch and return job listings from the portal."""
        pass

    @abstractmethod
    def apply(self, job: JobListing, cv_path: str, cover_letter_path: Optional[str] = None) -> bool:
        """
        Apply to the job (form submit or trigger email).
        Returns True if application was submitted successfully.
        """
        pass

    def should_apply(self, job: JobListing, applied_ids: set) -> bool:
        """Override to filter or skip already-applied jobs."""
        if job.id in applied_ids:
            return False
        return True
