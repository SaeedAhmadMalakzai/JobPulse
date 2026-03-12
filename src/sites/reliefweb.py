"""ReliefWeb - humanitarian jobs. Scrape Afghanistan listings."""
import requests
from bs4 import BeautifulSoup
from typing import List, Optional

from src.sites.base import JobListing, SiteAdapter, matches_job_keywords
from src.config import JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS
from src.apply_helper import apply_via_browser
from src.log import get_logger

LOG = get_logger("reliefweb")

RELIEFWEB_JOBS_PAGE = "https://reliefweb.int/jobs?country=13"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}


class ReliefwebAdapter(SiteAdapter):
    name = "reliefweb"

    def discover_jobs(self) -> List[JobListing]:
        jobs = []
        try:
            r = requests.get(RELIEFWEB_JOBS_PAGE, headers=_HEADERS, timeout=30)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select('a[href*="/job/"]'):
                href = a.get("href", "").strip()
                if not href:
                    continue
                if not href.startswith("http"):
                    href = "https://reliefweb.int" + href
                title = a.get_text(strip=True)
                if not title or len(title) < 5:
                    continue
                slug = href.rstrip("/").split("/")[-1][:30]
                job_id = f"reliefweb_{slug}"
                listing = JobListing(
                    id=job_id,
                    title=title,
                    company="NGO",
                    url=href,
                    location="Afghanistan",
                )
                if self._matches_filter(listing):
                    jobs.append(listing)
        except Exception as e:
            LOG.warning("  [reliefweb] Discovery error: %s", e)
        return jobs

    def _matches_filter(self, job: JobListing) -> bool:
        return matches_job_keywords(job.title, job.company, JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS)

    def apply(self, job: JobListing, cv_path: str, cover_letter_path: Optional[str] = None) -> bool:
        return apply_via_browser(
            job.url, job.title, cv_path, cover_letter_path,
            skip_domains=["reliefweb.int"], adapter_name=self.name,
        )
