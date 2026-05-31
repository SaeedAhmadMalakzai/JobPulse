"""Shared apply logic: open job page in Playwright, extract email or fill form."""
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright

from src.config import (
    SMTP_FROM_NAME, SMTP_USER, ONLINE_RESUME_URL,
    CV_PATH_EMAIL, CV_PATH_FORM,
)
from src.email_utils import send_application_email
from src.form_filler import fill_and_submit_form_on_page
from src.job_page_utils import extract_apply_from_page, extract_vacancy_number
from src.log import get_logger

LOG = get_logger("apply_helper")


def _pick_cv(base_cv: Path, for_email: bool) -> Path:
    """Return the appropriate CV: formal CV for email, ATS resume for forms."""
    if for_email and CV_PATH_EMAIL and CV_PATH_EMAIL.exists():
        return CV_PATH_EMAIL
    if not for_email and CV_PATH_FORM and CV_PATH_FORM.exists():
        return CV_PATH_FORM
    return base_cv


def _build_email_body(
    job_title: str,
    cover_letter_path: Optional[str],
    vacancy_number: Optional[str] = None,
) -> str:
    """Build email body with cover letter text, vacancy reference, and online resume link."""
    if cover_letter_path and Path(cover_letter_path).exists():
        body = Path(cover_letter_path).read_text(encoding="utf-8")
    else:
        body = f"Dear Hiring Manager,\n\nI am writing to apply for: {job_title}."
        if vacancy_number:
            body += f"\nVacancy/Reference Number: {vacancy_number}"
        body += "\n\nPlease find my CV and cover letter attached."
    if vacancy_number and vacancy_number not in body:
        body += f"\n\nVacancy/Reference Number: {vacancy_number}"
    if ONLINE_RESUME_URL:
        body += f"\n\nOnline Resume: {ONLINE_RESUME_URL}"
    return body


def _build_email_subject(job_title: str, vacancy_number: Optional[str] = None) -> str:
    subj = f"Application: {job_title}"
    if vacancy_number:
        subj += f" (Ref: {vacancy_number})"
    return subj


def apply_via_browser(
    job_url: str,
    job_title: str,
    cv_path: str,
    cover_letter_path: Optional[str] = None,
    skip_domains: Optional[list] = None,
    adapter_name: str = "unknown",
    vacancy_number: Optional[str] = None,
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
            if not vacancy_number:
                vacancy_number = extract_vacancy_number(html)

            if to_email:
                email_cv = _pick_cv(cv, for_email=True)
                body = _build_email_body(job_title, cover_letter_path, vacancy_number)
                subject = _build_email_subject(job_title, vacancy_number)
                browser.close()
                ok = send_application_email(
                    to_email, subject, body,
                    cv_path=email_cv,
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

            form_cv = _pick_cv(cv, for_email=False)
            ok = fill_and_submit_form_on_page(
                page, job_title=job_title,
                cv_path=form_cv,
                cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                applicant_name=SMTP_FROM_NAME, applicant_email=SMTP_USER,
                form_url=form_url or job_url,
                vacancy_number=vacancy_number,
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
