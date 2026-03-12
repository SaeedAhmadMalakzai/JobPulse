"""Ministry of Finance Afghanistan - government vacancies."""
import hashlib
import requests
from bs4 import BeautifulSoup
from typing import List, Optional

from src.sites.base import JobListing, SiteAdapter, matches_job_keywords
from src.config import JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS
from src.apply_helper import apply_via_browser
from src.log import get_logger

LOG = get_logger("mof_afghanistan")

BASE_URL = "https://mof.gov.af"
# Common paths for MoF vacancy pages (may vary)
VACANCIES_PATHS = ["/en/vacancies", "/vacancies", "/en/jobs", "/jobs", "/", ""]


def _discover_from_url(session: requests.Session, url: str, jobs: list, adapter: "MofAfghanistanAdapter") -> None:
    try:
        r = session.get(url, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        seen = set()
        for a in soup.select('a[href*="vacanc"], a[href*="job"], a[href*="position"], [class*="job"] a, [class*="vacanc"] a'):
            href = a.get("href", "")
            if not href.startswith("http"):
                href = BASE_URL.rstrip("/") + "/" + href.lstrip("/")
            if href in seen:
                continue
            seen.add(href)
            title = (a.get_text(strip=True) or "").strip()
            if not title or len(title) < 5:
                continue
            job_id = "mof_" + hashlib.sha256(href.encode()).hexdigest()[:14]
            listing = JobListing(
                id=job_id,
                title=title,
                company="Ministry of Finance Afghanistan",
                url=href,
                location="Afghanistan",
            )
            if adapter._matches_filter(listing):
                jobs.append(listing)
    except Exception as e:
        LOG.warning("  [mof_afghanistan] Discovery error for %s: %s", url, e)


class MofAfghanistanAdapter(SiteAdapter):
    name = "mof_afghanistan"

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
            skip_domains=["mof.gov.af"], adapter_name=self.name,
        )
