"""Wazifaha.org - discover jobs; apply via browser."""
import hashlib
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Optional

from src.sites.base import JobListing, SiteAdapter, matches_job_keywords
from src.config import JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS
from src.apply_helper import apply_via_browser
from src.log import get_logger

LOG = get_logger("wazifaha")

BASE_URL = "https://www.wazifaha.org"
JOBS_LIST_URL = "https://www.wazifaha.org/jobs"

_JOB_DETAIL_RE = re.compile(r"/jobs/\d+/")


class WazifahaAdapter(SiteAdapter):
    name = "wazifaha"

    def discover_jobs(self) -> List[JobListing]:
        jobs = []
        try:
            resp = requests.get(JOBS_LIST_URL, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            seen = set()
            for a in soup.select("a[href]"):
                href = a.get("href", "")
                if not _JOB_DETAIL_RE.search(href):
                    continue
                if not href.startswith("http"):
                    href = BASE_URL.rstrip("/") + "/" + href.lstrip("/")
                if href in seen:
                    continue
                seen.add(href)
                title = (a.get_text(strip=True) or "").strip()
                if not title or len(title) < 5:
                    continue
                if re.match(r"^[A-Z][a-z]+\(\d+\)$", title):
                    continue
                job_id = "wazifaha_" + hashlib.sha256(href.encode()).hexdigest()[:12]
                listing = JobListing(
                    id=job_id, title=title, company="",
                    url=href, location="Afghanistan",
                )
                if self._matches_filter(listing):
                    jobs.append(listing)
        except Exception as e:
            LOG.warning("  [wazifaha] Discovery error: %s", e)
        return jobs

    def _matches_filter(self, job: JobListing) -> bool:
        return matches_job_keywords(job.title, job.company, JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS)

    def apply(self, job: JobListing, cv_path: str, cover_letter_path: Optional[str] = None) -> bool:
        return apply_via_browser(
            job.url, job.title, cv_path, cover_letter_path,
            skip_domains=["wazifaha.org"], adapter_name=self.name,
        )
