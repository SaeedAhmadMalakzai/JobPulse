"""ACBAR (acbar.org) - Job Centre: discover jobs, extract HR/Submission Email from each post, apply by email."""
import html as html_module
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Optional

from src.sites.base import JobListing, SiteAdapter, matches_job_keywords
from src.config import JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS, SMTP_FROM_NAME, SMTP_USER
from src.email_utils import send_application_email
from src.form_filler import submit_application_form
from src.log import get_logger

LOG = get_logger("acbar")

BASE_URL = "https://www.acbar.org"
JOBS_LIST_URL = "https://www.acbar.org/jobs"

# Match email addresses (avoid matching URLs that contain @)
EMAIL_PATTERN = re.compile(
    r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b"
)
# Match https URLs (for application form links)
URL_PATTERN = re.compile(
    r"https?://[^\s<>\"']+",
    re.I
)


def _extract_submission_email(html: str) -> Optional[str]:
    """Parse job detail page and return Submission Email if it's an email address (not a URL)."""
    # Prefer the "Submission Email:" block (often in following <p> or text)
    if "submission email" in html.lower():
        idx = html.lower().find("submission email")
        block = html[idx : idx + 350]
        for match in EMAIL_PATTERN.findall(block):
            if "acbar.org" in match or "example.com" in match:
                continue
            if "http" in match or "www." in match:
                continue
            return match
    # Block after "Submission Email:" heading (next 150 chars often contain only the email)
    parts = re.split(r"Submission\s+Email\s*:?\s*", html, maxsplit=1, flags=re.I)
    if len(parts) >= 2:
        block = parts[1][:200]
        if "http" in block and "@" not in block.split("http")[0]:
            pass
        else:
            for match in EMAIL_PATTERN.findall(block):
                if "acbar.org" not in match and "example.com" not in match:
                    return match
    # Fallback: any email in last 1500 chars (submission section at end of page)
    tail = html[-1500:] if len(html) > 1500 else html
    emails = EMAIL_PATTERN.findall(tail)
    for e in emails:
        if "acbar.org" in e or "example.com" in e:
            continue
        if e.count(".") >= 2 and "cdn" in e.lower():
            continue
        return e
    # Last resort: mailto link (sometimes the only contact)
    mailto = re.search(r"mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", html, re.I)
    if mailto:
        e = mailto.group(1).strip()
        if "acbar.org" not in e:
            return e
    return None


def _extract_submission_url(html: str) -> Optional[str]:
    """If Submission Email section contains a URL (Google Form, Workday, etc.), return it."""
    if "submission email" not in html.lower():
        return None
    idx = html.lower().find("submission email")
    block = html[idx : idx + 500]
    urls = URL_PATTERN.findall(block)
    for u in urls:
        u = html_module.unescape(u).rstrip(".,);>\"'")
        if "acbar.org" in u:
            continue
        if "google.com/forms" in u or "docs.google.com" in u or "workday.com" in u or "wd1.myworkdayjobs" in u:
            return u
        if "jobs." in u or "career" in u or "apply" in u or "recruit" in u:
            return u
        # Any https URL in the block is likely the application link
        if u.startswith("https://") and len(u) > 20:
            return u
    return None


class AcbarAdapter(SiteAdapter):
    name = "acbar"

    def discover_jobs(self) -> List[JobListing]:
        jobs = []
        try:
            resp = requests.get(JOBS_LIST_URL, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            # Table: # | Title | Organization Name | Location | Close Date
            # Title links are like /jobs/140945/education-officer.jsp
            seen = set()
            # Only job detail pages: /jobs/140945/education-officer.jsp (not /company/jobs/...)
            for a in soup.select('a[href*="/jobs/"]'):
                href = a.get("href", "")
                if not href or href in seen:
                    continue
                if "/company/jobs/" in href:
                    continue
                if not re.search(r"/jobs/\d+/", href):
                    continue
                if not href.startswith("http"):
                    href = BASE_URL.rstrip("/") + "/" + href.lstrip("/")
                seen.add(href)
                title = (a.get_text(strip=True) or "").strip()
                if not title or len(title) < 3:
                    continue
                # Try to get organization and close date from parent row
                company = "ACBAR Member"
                close_date = None
                row = a.find_parent("tr")
                if row:
                    cells = row.select("td")
                    if len(cells) >= 2:
                        org_el = cells[1].select_one("a") or cells[1]
                        if org_el:
                            company = (org_el.get_text(strip=True) or company)[:80]
                    if len(cells) >= 5:
                        close_date = (cells[4].get_text(strip=True) or "").strip()[:10]
                        if close_date and not re.match(r"\d{4}-\d{2}-\d{2}", close_date):
                            close_date = None
                job_id = "acbar_" + (href.split("/jobs/")[-1].split("/")[0] or href)[:30]
                listing = JobListing(
                    id=job_id,
                    title=title,
                    company=company,
                    url=href,
                    location="Afghanistan",
                    close_date=close_date,
                )
                if self._matches_filter(listing):
                    jobs.append(listing)
        except Exception:
            pass
        return jobs

    def _matches_filter(self, job: JobListing) -> bool:
        return matches_job_keywords(job.title, job.company, JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS)

    def apply(self, job: JobListing, cv_path: str, cover_letter_path: Optional[str] = None) -> bool:
        cv = Path(cv_path)
        if not cv.exists():
            return False
        try:
            resp = requests.get(job.url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
            resp.raise_for_status()
            html = resp.text
            to_email = _extract_submission_email(html)
            apply_url = _extract_submission_url(html)

            # Prefer email if available
            if to_email:
                body = (
                    f"Application for: {job.title}\n\n"
                    "Please find my CV and cover letter attached.\n\n"
                    "Thank you for considering my application."
                )
                if cover_letter_path and Path(cover_letter_path).exists():
                    body = Path(cover_letter_path).read_text(encoding="utf-8")
                subject = f"Application: {job.title}"
                ok = send_application_email(
                    to_email,
                    subject,
                    body,
                    cv_path=cv,
                    cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                )
                if not ok:
                    LOG.warning("  [acbar] Email send failed for: %s... (to %s)", job.title[:50], to_email)
                return ok

            # Otherwise try form (Google Form or application link)
            if apply_url:
                ok = submit_application_form(
                    apply_url,
                    job_title=job.title,
                    cv_path=cv,
                    cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                    applicant_name=SMTP_FROM_NAME,
                    applicant_email=SMTP_USER,
                )
                return ok

            LOG.warning("  [acbar] No submission email or form link on page: %s...", job.title[:50])
            return False
        except Exception as e:
            LOG.error("  [acbar] Error applying to %s: %s", job.title[:40], e)
            return False
