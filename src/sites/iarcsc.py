"""IARCSC - Independent Administrative Reform and Civil Service Commission (Afghanistan)."""
import hashlib
import requests
from bs4 import BeautifulSoup
from typing import List, Optional

from src.sites.base import JobListing, SiteAdapter, matches_job_keywords
from src.config import JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS
from src.apply_helper import apply_via_browser
from src.log import get_logger

LOG = get_logger("iarcsc")

BASE_URL = "https://iarcsc.gov.af"
# Common paths for Afghan government vacancy pages
VACANCIES_PATHS = ["/en/vacancies", "/vacancies", "/en/jobs", "/", ""]


def _discover_from_url(session: requests.Session, url: str, jobs: list, adapter: "IarcscAdapter") -> None:
    try:
        r = session.get(url, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        seen = set()
        for a in soup.select('a[href*="vacanc"], a[href*="job"], a[href*="position"], a[href*="detail"], [class*="job"] a, [class*="vacanc"] a'):
            href = a.get("href", "")
            if not href.startswith("http"):
                href = BASE_URL.rstrip("/") + "/" + href.lstrip("/")
            if href in seen or BASE_URL not in href:
                continue
            seen.add(href)
            title = (a.get_text(strip=True) or "").strip()
            if not title or len(title) < 5:
                continue
            job_id = "iarcsc_" + hashlib.sha256(href.encode()).hexdigest()[:14]
            listing = JobListing(
                id=job_id,
                title=title,
                company="IARCSC",
                url=href,
                location="Afghanistan",
            )
            if adapter._matches_filter(listing):
                jobs.append(listing)
    except Exception as e:
        LOG.warning("  [iarcsc] Discovery error for %s: %s", url, e)


class IarcscAdapter(SiteAdapter):
    name = "iarcsc"

    def discover_jobs(self) -> List[JobListing]:
        jobs = []
        session = requests.Session()
        session.headers["User-Agent"] = "Mozilla/5.0 (compatible; CV-Bot/1.0)"
        for path in VACANCIES_PATHS:
            url = BASE_URL.rstrip("/") + "/" + path.lstrip("/") if path else BASE_URL
            _discover_from_url(session, url, jobs, self)
        return jobs[:80]

    def _matches_filter(self, job: JobListing) -> bool:
        return matches_job_keywords(job.title, job.company, JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS)

    def apply(self, job: JobListing, cv_path: str, cover_letter_path: Optional[str] = None) -> bool:
        return apply_via_browser(
            job.url, job.title, cv_path, cover_letter_path,
            skip_domains=["iarcsc.gov.af"], adapter_name=self.name,
        )
