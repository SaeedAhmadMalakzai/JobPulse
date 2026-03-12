"""Samuel Hall - consulting/research careers (Afghanistan and region)."""
import hashlib
import requests
from bs4 import BeautifulSoup
from typing import List, Optional

from src.sites.base import JobListing, SiteAdapter, matches_job_keywords
from src.config import JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS
from src.apply_helper import apply_via_browser
from src.log import get_logger

LOG = get_logger("samuel_hall")

BASE_URL = "https://www.samuelhall.org"
CAREERS_URL = "https://www.samuelhall.org/careers/"


class SamuelHallAdapter(SiteAdapter):
    name = "samuel_hall"

    def discover_jobs(self) -> List[JobListing]:
        jobs = []
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; CV-Bot/1.0)"}
            resp = requests.get(CAREERS_URL, headers=headers, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            seen = set()
            for a in soup.select('a[href*="job"], a[href*="career"], a[href*="position"], [class*="job"] a, [class*="opening"] a, article a'):
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = BASE_URL.rstrip("/") + "/" + href.lstrip("/")
                if href in seen or "samuelhall.org" not in href:
                    continue
                seen.add(href)
                title = (a.get_text(strip=True) or "").strip()
                if not title or len(title) < 5:
                    continue
                job_id = "samuelhall_" + hashlib.sha256(href.encode()).hexdigest()[:12]
                listing = JobListing(
                    id=job_id,
                    title=title,
                    company="Samuel Hall",
                    url=href,
                    location="",
                )
                if self._matches_filter(listing):
                    jobs.append(listing)
        except Exception as e:
            LOG.warning("  [samuel_hall] Discovery error: %s", e)
        return jobs

    def _matches_filter(self, job: JobListing) -> bool:
        return matches_job_keywords(job.title, job.company, JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS)

    def apply(self, job: JobListing, cv_path: str, cover_letter_path: Optional[str] = None) -> bool:
        return apply_via_browser(
            job.url, job.title, cv_path, cover_letter_path,
            skip_domains=["samuelhall.org"], adapter_name=self.name,
        )
