"""Shared apply logic: open job page in Playwright, extract email or fill form."""
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright

from src.config import SMTP_FROM_NAME, SMTP_USER
from src.email_utils import send_application_email
from src.form_filler import fill_and_submit_form_on_page
from src.job_page_utils import extract_apply_from_page
from src.log import get_logger

LOG = get_logger("apply_helper")


def apply_via_browser(
    job_url: str,
    job_title: str,
    cv_path: str,
    cover_letter_path: Optional[str] = None,
    skip_domains: Optional[list] = None,
    adapter_name: str = "unknown",
) -> bool:
    """
    Open job_url in a real browser, extract email or fill/submit form.
    Returns True only if application was actually submitted (email sent or form filled+submitted).
    """
    cv = Path(cv_path)
    if not cv.exists():
        LOG.warning("  [%s] CV not found: %s", adapter_name, cv_path)
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(30000)
            try:
                page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                LOG.warning("  [%s] Could not load page %s: %s", adapter_name, job_url[:60], e)
                browser.close()
                return False
            page.wait_for_timeout(2000)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass

            html = page.content()
            to_email, form_url = extract_apply_from_page(html, skip_domains=skip_domains)

            if to_email:
                body = f"Application for: {job_title}\n\nPlease find my CV and cover letter attached."
                if cover_letter_path and Path(cover_letter_path).exists():
                    body = Path(cover_letter_path).read_text(encoding="utf-8")
                browser.close()
                ok = send_application_email(
                    to_email, f"Application: {job_title}", body,
                    cv_path=cv,
                    cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                )
                if ok:
                    LOG.info("  [%s] Applied via email to %s for: %s", adapter_name, to_email, job_title[:40])
                return ok

            if form_url and form_url != job_url:
                try:
                    page.goto(form_url, wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(2000)
                except Exception:
                    pass

            ok = fill_and_submit_form_on_page(
                page, job_title=job_title,
                cv_path=cv,
                cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                applicant_name=SMTP_FROM_NAME, applicant_email=SMTP_USER,
                form_url=form_url or job_url,
            )
            browser.close()
            if ok:
                LOG.info("  [%s] Applied via form for: %s", adapter_name, job_title[:40])
            else:
                LOG.info("  [%s] No email or submittable form found on: %s", adapter_name, job_url[:60])
            return ok
    except Exception as e:
        LOG.error("  [%s] Browser apply error for %s: %s", adapter_name, job_title[:40], e)
        return False
