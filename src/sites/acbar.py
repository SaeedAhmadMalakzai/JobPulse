"""ACBAR (acbar.org) - Job Centre: discover jobs, extract HR/Submission Email from each post, apply by email."""
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Optional

from src.sites.base import JobListing, SiteAdapter, matches_job_keywords
from src.config import JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS
from src.email_utils import send_application_email
from src.form_filler import submit_application_form
# Submission email/URL extraction is shared (see src/job_page_utils.py) so every
# adapter benefits from the same robust logic. Re-exported under the historical
# private names used by this module and its tests.
from src.job_page_utils import (
    extract_apply_email as _extract_submission_email,
    extract_apply_url as _extract_submission_url,
)
from src.log import get_logger

LOG = get_logger("acbar")

BASE_URL = "https://www.acbar.org"
# ACBAR moved its Job Centre under the /en/ locale prefix; detail pages are now
# /en/jobs/details/<id>/<slug> (server-rendered cards, no <table>).
JOBS_LIST_URL = "https://www.acbar.org/en/jobs"
DETAIL_RE = re.compile(r"/en/jobs/details/(\d+)")
ACBAR_MAX_PAGES = 3
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


class AcbarAdapter(SiteAdapter):
    name = "acbar"

    def discover_jobs(self) -> List[JobListing]:
        jobs = []
        seen = set()
        try:
            for page in range(1, ACBAR_MAX_PAGES + 1):
                url = JOBS_LIST_URL if page == 1 else f"{JOBS_LIST_URL}?page={page}"
                resp = requests.get(url, timeout=30, headers=UA)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                anchors = soup.select('a[href*="/jobs/details/"]')
                if not anchors:
                    break  # no more job cards / end of pagination
                for a in anchors:
                    href = a.get("href", "")
                    m = DETAIL_RE.search(href)
                    if not m:
                        continue
                    if not href.startswith("http"):
                        href = BASE_URL + ("" if href.startswith("/") else "/") + href.lstrip("/")
                    if href in seen:
                        continue
                    seen.add(href)
                    title = (a.get_text(strip=True) or "").strip()
                    if not title or len(title) < 3:
                        continue
                    # Org / close-date live in the surrounding card (no <table> anymore).
                    company = "ACBAR Member"
                    close_date = None
                    card = a.find_parent(["div", "li", "article"])
                    if card:
                        txt = card.get_text(" ", strip=True)
                        cd = re.search(r"(20\d\d-\d\d-\d\d)", txt)
                        if cd:
                            close_date = cd.group(1)
                    listing = JobListing(
                        id="acbar_" + m.group(1),
                        title=title,
                        company=company,
                        url=href,
                        location="Afghanistan",
                        close_date=close_date,
                    )
                    if self._matches_filter(listing):
                        jobs.append(listing)
        except Exception as e:
            LOG.warning("  [acbar] Discovery failed: %s: %s", type(e).__name__, e)
        return jobs

    def _matches_filter(self, job: JobListing) -> bool:
        return matches_job_keywords(job.title, job.company, JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS)

    def apply(self, job: JobListing, cv_path: str, cover_letter_path: Optional[str] = None) -> bool:
        from src.apply_helper import _pick_cv, _build_email_body, _build_email_subject, resolve_form_identity
        cv = Path(cv_path)
        if not cv.exists():
            return False
        try:
            resp = requests.get(job.url, timeout=30, headers=UA)
            resp.raise_for_status()
            html = resp.text
            to_email = _extract_submission_email(html)
            apply_url = _extract_submission_url(html)

            if to_email:
                email_cv = _pick_cv(cv, for_email=True)
                body = _build_email_body(job.title, cover_letter_path, job.vacancy_number)
                subject = _build_email_subject(job.title, job.vacancy_number)
                ok = send_application_email(
                    to_email,
                    subject,
                    body,
                    cv_path=email_cv,
                    cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                )
                if not ok:
                    LOG.warning("  [acbar] Email send failed for: %s... (to %s)", job.title[:50], to_email)
                return ok

            if apply_url:
                form_cv = _pick_cv(cv, for_email=False)
                applicant_name, applicant_email = resolve_form_identity()
                ok = submit_application_form(
                    apply_url,
                    job_title=job.title,
                    cv_path=form_cv,
                    cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                    applicant_name=applicant_name,
                    applicant_email=applicant_email,
                    vacancy_number=job.vacancy_number,
                )
                if not ok:
                    # Couldn't auto-submit (e.g. Google Form file-upload needs a Google
                    # login, or unanswerable required questions) — surface for manual apply
                    # instead of silently dropping it.
                    from src.needs_review import record_needs_review
                    record_needs_review(
                        job.title, apply_url,
                        ["Form could not be auto-submitted — apply manually"], site="acbar",
                    )
                    LOG.info("  [acbar] Flagged for manual review (form): %s -> %s", job.title[:40], apply_url[:60])
                return ok

            LOG.warning("  [acbar] No submission email or form link on page: %s...", job.title[:50])
            from src.needs_review import record_needs_review
            record_needs_review(
                job.title, job.url,
                ["No submission email/form auto-detected — open the post and apply"], site="acbar",
            )
            return False
        except Exception as e:
            LOG.error("  [acbar] Error applying to %s: %s", job.title[:40], e)
            return False
