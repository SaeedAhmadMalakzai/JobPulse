"""Shared helpers: extract apply email or application URL from a job detail page.

Robust extraction shared by every adapter that applies via a job page (ACBAR,
Wazifaha, LinkedIn external, the generic browser-apply path). Handles posts whose
"how to apply" section is headed "Submission Email", "Submission Guideline" or
"How to Apply", recognizes Google Forms (incl. forms.gle short links) and common
ATS hosts, scans <a href> links, and ignores site-nav / social / CDN noise.
"""
import html as html_module
import re
from typing import Optional, Tuple

from bs4 import BeautifulSoup

EMAIL_PATTERN = re.compile(r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b")
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.I)

# Specific "how to apply" headers — kept narrow so they don't collide with site
# nav ("Job Centre · Application Form · Contact").
APPLY_MARKERS = (
    "submission email", "submission guideline", "submission guidelines",
    "how to apply", "submit your application", "send your application",
    "send your cv", "send cv", "email your application", "email your cv",
    "applications should", "interested applicants", "interested candidates",
    "qualified applicants",
)
# Hosts/paths that indicate an application form or ATS link.
FORM_HOST_HINTS = (
    "forms.gle", "docs.google.com", "google.com/forms", "forms.office.com",
    "myworkdayjobs", "workday", "taleo", "greenhouse", "lever.co", "bamboohr",
    "smartrecruiters", "jotform", "typeform", "airtable", "zoho.com/recruit",
    "/apply", "career", "recruit", "vacanc", "/jobs", "position", "ims.",
    "hrms", "/public-", "survey",
)
# Never treated as an application target.
EXCLUDE_HOSTS = (
    "acbar.org", "facebook.", "twitter.", "x.com", "linkedin.com/company",
    "instagram.", "youtube.", "youtu.be", "t.me", "whatsapp", "wa.me",
    "cdn", "gstatic", "googleapis", "sentry", "/donate", "gravatar", "maps.google",
)
_EXCLUDE_EMAIL_TOKENS = ("acbar.org", "example", "sentry", "noreply", "no-reply")


def _page_text(html: str) -> str:
    try:
        return BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    except Exception:
        return re.sub(r"<[^>]+>", " ", html)


def _apply_section(text: str) -> str:
    """Slice around the LAST apply marker (the submission section sits near the
    end, after nav/boilerplate that may contain similar words)."""
    low = text.lower()
    pos = max((low.rfind(m) for m in APPLY_MARKERS), default=-1)
    if pos >= 0:
        return text[pos: pos + 1300]
    return text[-2000:] if len(text) > 2000 else text


def _clean_url(u: str) -> str:
    return html_module.unescape(u).rstrip(".,);>\"'… ")


def _is_excluded(u: str, skip: set) -> bool:
    lu = u.lower()
    if any(h in lu for h in EXCLUDE_HOSTS):
        return True
    return any(d in lu for d in skip)


def extract_apply_email(html: str, skip_domains: Optional[list] = None) -> Optional[str]:
    """Return the HR/submission email, searching the apply section then the post."""
    skip = {d.lower() for d in (skip_domains or [])}

    def _ok(e: str) -> bool:
        low = e.lower()
        if "www." in e or any(t in low for t in _EXCLUDE_EMAIL_TOKENS):
            return False
        return not any(d in low for d in skip)

    text = _page_text(html)
    for e in EMAIL_PATTERN.findall(_apply_section(text)):
        if _ok(e):
            return e
    mailto = re.search(r"mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", html, re.I)
    if mailto and _ok(mailto.group(1).strip()):
        return mailto.group(1).strip()
    for e in EMAIL_PATTERN.findall(text[-1500:]):
        if _ok(e) and "cdn" not in e.lower():
            return e
    return None


def extract_apply_url(html: str, skip_domains: Optional[list] = None) -> Optional[str]:
    """Return an application form / ATS URL (Google Form incl. forms.gle, Workday, custom)."""
    skip = {d.lower() for d in (skip_domains or [])}
    text = _page_text(html)
    section_urls = [u for u in (_clean_url(x) for x in URL_PATTERN.findall(_apply_section(text)))
                    if not _is_excluded(u, skip)]
    # 1) known form/ATS host mentioned in the apply section
    for u in section_urls:
        if any(h in u.lower() for h in FORM_HOST_HINTS):
            return u
    # 2) known form/ATS host in any <a href> (handles button-only links)
    try:
        for a in BeautifulSoup(html, "lxml").find_all("a"):
            h = _clean_url(a.get("href", "") or "")
            if h.startswith("http") and not _is_excluded(h, skip) and any(x in h.lower() for x in FORM_HOST_HINTS):
                return h
    except Exception:
        pass
    # 3) any plausible https link in the apply section
    for u in section_urls:
        if u.startswith("https://") and len(u) > 20:
            return u
    return None


def extract_vacancy_number(html: str) -> Optional[str]:
    """Extract vacancy/reference number from job page HTML.
    Looks for patterns like 'Vacancy Number: ABC-123' or 'Reference No: 456'.
    """
    text = html_module.unescape(re.sub(r"<[^>]+>", " ", html))
    patterns = [
        r"(?:vacancy\s*(?:number|no\.?|#|id)\s*[:\-]\s*)([A-Za-z0-9\-/_.]+)",
        r"(?:reference\s*(?:number|no\.?|#|id)\s*[:\-]\s*)([A-Za-z0-9\-/_.]+)",
        r"(?:ref\.?\s*(?:number|no\.?|#)?\s*[:\-]\s*)([A-Za-z0-9\-/_.]+)",
        r"(?:position\s*(?:number|no\.?|#)\s*[:\-]\s*)([A-Za-z0-9\-/_.]+)",
        r"(?:job\s*(?:number|no\.?|#|id|code)\s*[:\-]\s*)([A-Za-z0-9\-/_.]+)",
        r"(?:announcement\s*(?:number|no\.?|#)\s*[:\-]\s*)([A-Za-z0-9\-/_.]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            val = m.group(1).strip().rstrip(".,;)")
            if len(val) >= 2:
                return val
    return None


def extract_apply_from_page(html: str, skip_domains: Optional[list] = None) -> Tuple[Optional[str], Optional[str]]:
    """Return (apply_email, apply_url). One or both may be None."""
    return (extract_apply_email(html, skip_domains), extract_apply_url(html, skip_domains))
