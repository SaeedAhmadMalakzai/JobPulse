"""Kabul Careers - local job board (plausible URL; adjust if site differs)."""
import hashlib
import requests
from bs4 import BeautifulSoup
from typing import List, Optional

from src.sites.base import JobListing, SiteAdapter, matches_job_keywords
from src.config import JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS
from src.apply_helper import apply_via_browser
from src.log import get_logger

LOG = get_logger("kabul_careers")

BASE_URL = "https://www.kabulcareers.com"
JOBS_PATHS = ["/jobs", "/vacancies", "/", ""]


def _discover_from_url(session: requests.Session, url: str, jobs: list, seen_urls: set, adapter: "KabulCareersAdapter") -> None:
    try:
        r = session.get(url, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        for a in soup.select('a[href*="job"], a[href*="vacanc"], a[href*="career"], [class*="job"] a'):
            href = a.get("href", "")
            if not href.startswith("http"):
                href = BASE_URL.rstrip("/") + "/" + href.lstrip("/")
            if href in seen_urls:
                continue
            seen_urls.add(href)
            title = (a.get_text(strip=True) or "").strip()
            if not title or len(title) < 5:
                continue
            job_id = "kabulcareers_" + hashlib.sha256(href.encode()).hexdigest()[:14]
            listing = JobListing(
                id=job_id,
                title=title,
                company="",
                url=href,
                location="Kabul",
            )
            if adapter._matches_filter(listing):
                jobs.append(listing)
    except Exception as e:
        LOG.warning("kabul_careers discover from %s failed: %s", url, e)


class KabulCareersAdapter(SiteAdapter):
    name = "kabul_careers"

    def discover_jobs(self) -> List[JobListing]:
        jobs = []
        seen_urls = set()
        session = requests.Session()
        session.headers["User-Agent"] = "Mozilla/5.0 (compatible; CV-Bot/1.0)"
        for path in JOBS_PATHS:
            url = BASE_URL.rstrip("/") + "/" + path.lstrip("/") if path else BASE_URL
            _discover_from_url(session, url, jobs, seen_urls, self)
        return jobs[:60]

    def _matches_filter(self, job: JobListing) -> bool:
        return matches_job_keywords(job.title, job.company, JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS)

    def apply(self, job: JobListing, cv_path: str, cover_letter_path: Optional[str] = None) -> bool:
        return apply_via_browser(
            job.url,
            job.title,
            cv_path,
            cover_letter_path,
            skip_domains=["kabulcareers.com"],
            adapter_name=self.name,
        )
