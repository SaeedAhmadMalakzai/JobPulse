"""Devex.com - discover development jobs; apply via browser."""
import hashlib
import re
from typing import List, Optional

from playwright.sync_api import sync_playwright

from src.sites.base import JobListing, SiteAdapter, matches_job_keywords
from src.config import JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS
from src.apply_helper import apply_via_browser
from src.log import get_logger

LOG = get_logger("devex")

JOBS_SEARCH_URL = "https://www.devex.com/jobs/search?filter%5Bcountries%5D%5B%5D=Afghanistan"


class DevexAdapter(SiteAdapter):
    name = "devex"

    def discover_jobs(self) -> List[JobListing]:
        jobs = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(25000)
                page.goto(JOBS_SEARCH_URL, wait_until="domcontentloaded", timeout=40000)
                page.wait_for_timeout(3000)
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass
                seen = set()
                for a in page.query_selector_all('a[href*="/jobs/"]'):
                    try:
                        href = a.get_attribute("href") or ""
                        if not href or "/jobs/search" in href or "/jobs/posting" in href or "/jobs/new" in href:
                            continue
                        if not href.startswith("http"):
                            href = "https://www.devex.com" + href
                        if href in seen:
                            continue
                        seen.add(href)
                        title = (a.inner_text() or "").strip()
                        if not title or len(title) < 5:
                            continue
                        job_id = "devex_" + hashlib.sha256(href.encode()).hexdigest()[:12]
                        listing = JobListing(
                            id=job_id, title=title, company="Devex",
                            url=href, location="Afghanistan",
                        )
                        if self._matches_filter(listing):
                            jobs.append(listing)
                    except Exception:
                        continue
                browser.close()
        except Exception as e:
            LOG.warning("  [devex] Discovery error: %s", e)
        return jobs

    def _matches_filter(self, job: JobListing) -> bool:
        return matches_job_keywords(job.title, job.company, JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS)

    def apply(self, job: JobListing, cv_path: str, cover_letter_path: Optional[str] = None) -> bool:
        return apply_via_browser(
            job.url, job.title, cv_path, cover_letter_path,
            skip_domains=["devex.com"], adapter_name=self.name,
        )
