"""UN Jobs - Afghanistan listings (unjobs.org).
UNJobs is an aggregator; actual applications go through the source agency portals.
"""
import hashlib
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Optional

from src.sites.base import JobListing, SiteAdapter, matches_job_keywords
from src.config import JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS
from src.apply_helper import apply_via_browser
from src.log import get_logger

LOG = get_logger("unjobs")

UNJOBS_AFGHANISTAN = "https://unjobs.org/duty_stations/afghanistan"


class UnjobsAdapter(SiteAdapter):
    name = "unjobs"

    def discover_jobs(self) -> List[JobListing]:
        jobs = []
        try:
            resp = requests.get(UNJOBS_AFGHANISTAN, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            for a in soup.select('a[href*="/vacancies/"]'):
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = "https://unjobs.org" + href
                title = (a.get_text(strip=True) or "").strip()
                if not title or len(title) < 5:
                    continue
                job_id = hashlib.sha256(f"unjobs_{href}".encode()).hexdigest()[:16]
                parent = a.find_parent("li") or a.find_parent("div")
                company = "UN / International"
                if parent:
                    org_el = parent.select_one(".organization, .org, .agency")
                    if org_el:
                        company = org_el.get_text(strip=True) or company
                listing = JobListing(
                    id=job_id, title=title, company=company,
                    url=href, location="Afghanistan",
                )
                if self._matches_filter(listing):
                    jobs.append(listing)
        except Exception as e:
            LOG.warning("  [unjobs] Discovery error: %s", e)
        return jobs

    def _matches_filter(self, job: JobListing) -> bool:
        return matches_job_keywords(job.title, job.company, JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS)

    def apply(self, job: JobListing, cv_path: str, cover_letter_path: Optional[str] = None) -> bool:
        if job.apply_by_email:
            from pathlib import Path
            from src.email_utils import send_application_email
            body = f"Application for: {job.title}\n\nPlease find my CV and cover letter attached."
            if cover_letter_path and Path(cover_letter_path).exists():
                body = Path(cover_letter_path).read_text(encoding="utf-8")
            return send_application_email(
                job.apply_by_email, f"Application: {job.title}", body,
                cv_path=Path(cv_path),
                cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
            )

        from playwright.sync_api import sync_playwright
        from pathlib import Path
        from src.job_page_utils import extract_apply_from_page

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(30000)
                page.goto(job.url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2000)

                html = page.content()
                to_email, _ = extract_apply_from_page(html, skip_domains=["unjobs.org"])

                if to_email:
                    from src.email_utils import send_application_email
                    body = f"Application for: {job.title}\n\nPlease find my CV and cover letter attached."
                    if cover_letter_path and Path(cover_letter_path).exists():
                        body = Path(cover_letter_path).read_text(encoding="utf-8")
                    browser.close()
                    ok = send_application_email(
                        to_email, f"Application: {job.title}", body,
                        cv_path=Path(cv_path),
                        cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                    )
                    if ok:
                        LOG.info("  [unjobs] Applied via email to %s for: %s", to_email, job.title[:40])
                    return ok

                source_link = None
                for sel in [
                    'a[href*="careers.un.org"]', 'a[href*="jobs.undp.org"]',
                    'a[href*="unicef.org"]', 'a[href*="who.int"]',
                    'a[href*="fao.org"]', 'a[href*="wfp.org"]',
                    'a[href*="unhcr.org"]', 'a[href*="unops.org"]',
                    'a[href*="iom.int"]', 'a[href*="unesco.org"]',
                    'a[href*="ilo.org"]',
                    'a:has-text("Apply")', 'a:has-text("Source")',
                    'a:has-text("Original")', 'a:has-text("View")',
                ]:
                    try:
                        el = page.query_selector(sel)
                        if el:
                            href = (el.get_attribute("href") or "").strip()
                            if href and "unjobs.org" not in href and href.startswith("http"):
                                source_link = href
                                break
                    except Exception:
                        pass

                browser.close()

                if source_link:
                    return apply_via_browser(
                        source_link, job.title, cv_path, cover_letter_path,
                        skip_domains=["unjobs.org"], adapter_name=self.name,
                    )

                LOG.info("  [unjobs] No apply email or source link found for: %s", job.title[:50])
                return False
        except Exception as e:
            LOG.warning("  [unjobs] Apply error for %s: %s", job.title[:40], e)
            return False
