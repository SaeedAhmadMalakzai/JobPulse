"""Shared helpers: extract apply email or application URL from a job detail page HTML."""
import html as html_module
import re
from typing import Optional, Tuple

EMAIL_PATTERN = re.compile(r"\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b")
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.I)


def extract_apply_email(html: str, skip_domains: Optional[list] = None) -> Optional[str]:
    """Extract an application/contact email from job page HTML."""
    skip = set(skip_domains or [])
    skip.add("example.com")
    text_lower = html.lower()
    # Look for common section headers then email in next 200-400 chars
    for phrase in ("submission email", "apply to", "send your cv", "contact email", "hr@", "apply@"):
        if phrase in text_lower:
            idx = text_lower.find(phrase)
            block = html[idx : idx + 400]
            for match in EMAIL_PATTERN.findall(block):
                domain = match.split("@")[-1].lower()
                if domain in skip or "cdn" in domain:
                    continue
                return match
    # mailto links
    for m in re.finditer(r"mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", html, re.I):
        e = m.group(1).strip()
        if e.split("@")[-1].lower() not in skip:
            return e
    # Any email in last 1200 chars (often application section)
    tail = html[-1200:] if len(html) > 1200 else html
    for e in EMAIL_PATTERN.findall(tail):
        if e.split("@")[-1].lower() in skip:
            continue
        return e
    return None


def extract_apply_url(html: str, skip_domains: Optional[list] = None) -> Optional[str]:
    """Extract an application form/careers URL from job page HTML."""
    skip = set(skip_domains or [])
    text_lower = html.lower()
    for phrase in ("submission email", "apply here", "apply at", "application link", "apply online"):
        if phrase in text_lower:
            idx = text_lower.find(phrase)
            block = html[idx : idx + 600]
            for u in URL_PATTERN.findall(block):
                u = html_module.unescape(u).rstrip(".,);>\"'")
                if any(d in u.lower() for d in skip):
                    continue
                if "google.com/forms" in u or "docs.google.com" in u or "workday.com" in u:
                    return u
                if "job" in u or "career" in u or "apply" in u or "recruit" in u:
                    return u
                if u.startswith("https://") and len(u) > 15:
                    return u
    return None


def extract_apply_from_page(html: str, skip_domains: Optional[list] = None) -> Tuple[Optional[str], Optional[str]]:
    """Return (apply_email, apply_url). One or both may be None."""
    email = extract_apply_email(html, skip_domains)
    url = extract_apply_url(html, skip_domains)
    return (email, url)
