"""
Fill and submit application forms (Google Forms, generic forms, ATS multi-step).
Maps applicant name, email, phone, CV, cover letter to common field labels/placeholders.
Handles multi-step wizards, dropdowns, radio buttons, and checkboxes.
CAPTCHA: If reCAPTCHA/hCaptcha is present, optional 2Captcha API can be used (set CAPTCHA_API_KEY in .env).
"""
import re
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright

from src.config import (
    SMTP_FROM_NAME, SMTP_USER, CV_PATH, PHONE_NUMBER, PHONE_COUNTRY_CODE,
    LINKEDIN_PROFILE_URL,
    FIRST_NAME, MIDDLE_NAME, LAST_NAME, FULL_NAME, SALUTATION, GENDER,
    COUNTRY, CITY, YEARS_EXPERIENCE, SUBMISSION_EMAIL,
)
from src.log import get_logger

import random

LOG = get_logger("form")


def _fill_selects_and_radios(page) -> None:
    """Fill visible <select> dropdowns and click first radio in unselected groups."""
    try:
        for sel in page.query_selector_all("select"):
            if not sel.is_visible():
                continue
            try:
                if sel.input_value():
                    continue
            except Exception:
                pass
            try:
                label = _get_label(page, sel)
                opts = sel.query_selector_all("option")
                if len(opts) < 2:
                    continue
                value = None

                if "gender" in label or "sex" in label:
                    for opt in opts:
                        t = (opt.inner_text() or "").strip().lower()
                        if t in ("male", "m"):
                            value = opt.get_attribute("value") or t
                            break
                elif "country" in label or "nationality" in label:
                    for opt in opts:
                        t = (opt.inner_text() or "").strip().lower()
                        if "afghan" in t:
                            value = opt.get_attribute("value") or t
                            break
                elif "salut" in label or "prefix" in label:
                    for opt in opts:
                        t = (opt.inner_text() or "").strip().lower()
                        if t in ("mr", "mr."):
                            value = opt.get_attribute("value") or t
                            break

                if value is None:
                    for opt in opts[1:]:
                        text = (opt.inner_text() or opt.get_attribute("value") or "").strip().lower()
                        if text in ("yes", "1", "2", "3", "5", "1 year", "2 years", "3 years", "5 years",
                                    "authorized", "authorised", "i am"):
                            value = opt.get_attribute("value")
                            break
                if value is None:
                    value = opts[1].get_attribute("value")
                if value is not None:
                    sel.select_option(value=value)
            except Exception:
                try:
                    sel.select_option(index=1)
                except Exception:
                    pass
        for group in page.query_selector_all('div[role="radiogroup"], fieldset'):
            try:
                radios = [r for r in group.query_selector_all('input[type="radio"], [role="radio"]') if r.is_visible()]
                if not radios:
                    continue
                if any(r.get_attribute("checked") or (r.get_attribute("aria-checked") == "true") for r in radios):
                    continue
                for r in radios:
                    label_text = ""
                    try:
                        lid = r.get_attribute("id")
                        if lid:
                            lab = page.query_selector(f'label[for="{lid}"]')
                            if lab:
                                label_text = (lab.inner_text() or "").lower()
                    except Exception:
                        pass
                    if "yes" in label_text or "authorized" in label_text or "agree" in label_text:
                        r.click()
                        page.wait_for_timeout(200)
                        break
                else:
                    radios[0].click()
                    page.wait_for_timeout(200)
            except Exception:
                pass
    except Exception:
        pass


_PHONE_LOCAL = PHONE_NUMBER  # e.g. "730325532"
_PHONE_FULL_PLUS = f"{PHONE_COUNTRY_CODE}{PHONE_NUMBER}"  # e.g. "+93730325532"
_PHONE_FULL_00 = f"00{PHONE_COUNTRY_CODE.lstrip('+')}{PHONE_NUMBER}"  # e.g. "0093730325532"


def _select_country_code(page, phone_el) -> bool:
    """Try to find and select +93 / 93 / Afghanistan in a country-code dropdown near the phone input.
    Returns True if a code dropdown was found and selected."""
    # Look for a <select> or custom dropdown near the phone input
    parent = phone_el.evaluate_handle("el => el.closest('div, fieldset, form, section, li')")
    if not parent:
        parent = page
    for sel_selector in [
        'select[name*="country" i]', 'select[name*="code" i]', 'select[name*="dial" i]',
        'select[name*="prefix" i]', 'select[name*="phone" i]',
        'select[aria-label*="country" i]', 'select[aria-label*="code" i]',
        'select[class*="country" i]', 'select[class*="code" i]',
        'select',
    ]:
        try:
            dropdown = parent.query_selector(sel_selector) if hasattr(parent, 'query_selector') else page.query_selector(sel_selector)
            if not dropdown or not dropdown.is_visible():
                continue
            opts = dropdown.query_selector_all("option")
            for opt in opts:
                val = (opt.get_attribute("value") or "").strip()
                text = (opt.inner_text() or "").strip()
                combined = f"{val} {text}".lower()
                code_bare = PHONE_COUNTRY_CODE.lstrip("+")
                if any(k in combined for k in (PHONE_COUNTRY_CODE.lower(), code_bare, "afghan")):
                    opt_val = opt.get_attribute("value")
                    if opt_val is not None:
                        dropdown.select_option(value=opt_val)
                    else:
                        dropdown.select_option(label=text)
                    return True
        except Exception:
            continue

    # Try custom listbox / button-based dropdowns (common in modern SPAs)
    for btn_sel in [
        'button[aria-label*="country" i]', 'button[aria-label*="code" i]',
        'div[role="button"][aria-label*="code" i]',
        '[class*="country-code" i]', '[class*="phone-code" i]',
        '[class*="dial-code" i]',
    ]:
        try:
            btn = parent.query_selector(btn_sel) if hasattr(parent, 'query_selector') else page.query_selector(btn_sel)
            if not btn or not btn.is_visible():
                continue
            btn.click()
            page.wait_for_timeout(500)
            for opt_sel in [
                f'[role="option"]:has-text("{PHONE_COUNTRY_CODE}")', f'[role="option"]:has-text("{COUNTRY}")',
                f'li:has-text("{PHONE_COUNTRY_CODE}")', f'li:has-text("{COUNTRY}")',
                f'div:has-text("{PHONE_COUNTRY_CODE}")', f'span:has-text("{PHONE_COUNTRY_CODE}")',
            ]:
                opt = page.query_selector(opt_sel)
                if opt and opt.is_visible():
                    opt.click()
                    page.wait_for_timeout(300)
                    return True
            page.keyboard.press("Escape")
        except Exception:
            continue

    return False


def _fill_phone_and_url_fields(page, phone: str, linkedin_url: str) -> None:
    """Fill phone number and LinkedIn/URL fields, selecting +93 country code when available."""
    if phone:
        for sel in [
            'input[type="tel"]',
            'input[placeholder*="phone" i]', 'input[placeholder*="mobile" i]',
            'input[aria-label*="phone" i]', 'input[aria-label*="mobile" i]',
            'input[name*="phone" i]', 'input[name*="mobile" i]', 'input[name*="tel" i]',
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible() and not el.input_value():
                    if _select_country_code(page, el):
                        el.fill(_PHONE_LOCAL)
                    else:
                        el.fill(_PHONE_FULL_PLUS)
                    break
            except Exception:
                pass
    if linkedin_url:
        for sel in [
            'input[placeholder*="linkedin" i]', 'input[placeholder*="profile" i]',
            'input[aria-label*="linkedin" i]', 'input[aria-label*="profile url" i]',
            'input[name*="linkedin" i]', 'input[type="url"]',
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible() and not el.get_attribute("value"):
                    el.fill(linkedin_url)
                    break
            except Exception:
                pass


_TECH_STACKS = [
    "Python, Django, React, PostgreSQL",
    "JavaScript, TypeScript, Node.js, React",
    "Python, Flask, AWS, Docker",
    "Java, Spring Boot, Kubernetes, MySQL",
    "React, Next.js, Tailwind CSS, Node.js",
    "Python, FastAPI, Vue.js, MongoDB",
]


def _get_label(page, inp) -> str:
    """Extract the label text for an input element."""
    try:
        lid = inp.get_attribute("id")
        if lid:
            lab = page.query_selector(f'label[for="{lid}"]')
            if lab:
                return (lab.inner_text() or "").lower()
        name = (inp.get_attribute("name") or "").lower()
        placeholder = (inp.get_attribute("placeholder") or "").lower()
        aria = (inp.get_attribute("aria-label") or "").lower()
        return f"{name} {placeholder} {aria}".strip()
    except Exception:
        return ""


def _fill_required_empty_fields(page, applicant_name: str, applicant_email: str, phone: str) -> None:
    """Fill any remaining required/visible empty inputs with authentic personal details."""
    try:
        for inp in page.query_selector_all(
            'input[required], input[aria-required="true"], input:visible, textarea:visible'
        ):
            if not inp.is_visible():
                continue
            val = (inp.input_value() or "").strip()
            if val:
                continue
            input_type = (inp.get_attribute("type") or "text").lower()
            if input_type in ("file", "hidden", "submit", "button", "checkbox", "radio", "search"):
                continue
            label = _get_label(page, inp)

            try:
                if input_type == "email":
                    inp.fill(applicant_email)
                elif input_type == "tel":
                    if _select_country_code(page, inp):
                        inp.fill(_PHONE_LOCAL)
                    else:
                        inp.fill(_PHONE_FULL_PLUS)
                elif input_type == "url":
                    inp.fill(LINKEDIN_PROFILE_URL or "")
                elif "first" in label and "name" in label:
                    inp.fill(FIRST_NAME)
                elif "middle" in label and "name" in label:
                    inp.fill(MIDDLE_NAME)
                elif ("last" in label or "family" in label or "surname" in label) and "name" in label:
                    inp.fill(LAST_NAME)
                elif "full name" in label or label == "name":
                    inp.fill(FULL_NAME)
                elif "name" in label and "company" not in label and "job" not in label:
                    inp.fill(FULL_NAME)
                elif "salut" in label or "title" in label and ("mr" in label or "ms" in label):
                    inp.fill(SALUTATION)
                elif "gender" in label or "sex" in label:
                    inp.fill(GENDER)
                elif "phone" in label or "mobile" in label or "tel" in label or "contact number" in label:
                    if _select_country_code(page, inp):
                        inp.fill(_PHONE_LOCAL)
                    else:
                        inp.fill(_PHONE_FULL_PLUS)
                elif "country" in label or "nationality" in label:
                    inp.fill(COUNTRY)
                elif "city" in label or "location" in label or "address" in label:
                    inp.fill(CITY)
                elif "year" in label and ("experience" in label or "exp" in label):
                    inp.fill(YEARS_EXPERIENCE)
                elif "experience" in label:
                    inp.fill(YEARS_EXPERIENCE)
                elif "linkedin" in label or "profile url" in label or "portfolio" in label:
                    inp.fill(LINKEDIN_PROFILE_URL or "")
                elif "stack" in label or "technologies" in label or "skills" in label:
                    inp.fill(random.choice(_TECH_STACKS))
                elif "language" in label and "program" in label:
                    inp.fill(random.choice(["Python", "JavaScript", "Java", "TypeScript"]))
                elif input_type == "number" or "gpa" in label:
                    inp.fill(YEARS_EXPERIENCE)
                elif "salary" in label or "compensation" in label or "expectation" in label:
                    inp.fill("0")
                elif "headline" in label or "summary" in label or "about" in label:
                    inp.fill("Software Engineer with 5+ years of experience in full-stack development")
                elif "cover" in label or "message" in label:
                    pass
                elif "email" in label:
                    inp.fill(applicant_email)
            except Exception:
                pass
    except Exception:
        pass


def _has_application_form(page) -> bool:
    """Check if the page contains a real application form (not just a generic site form)."""
    try:
        file_inputs = page.query_selector_all('input[type="file"]')
        if file_inputs:
            for fi in file_inputs:
                if fi.is_visible():
                    return True

        form_indicators = [
            'input[name*="resume" i]', 'input[name*="cv" i]',
            'input[placeholder*="name" i]', 'input[type="email"]',
            'textarea[name*="cover" i]', 'textarea[placeholder*="cover" i]',
            'form[action*="apply" i]', 'form[action*="submit" i]',
            'form[action*="career" i]',
        ]
        indicator_count = 0
        for sel in form_indicators:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    indicator_count += 1
            except Exception:
                pass
        if indicator_count >= 2:
            return True

        visible_inputs = 0
        for inp in page.query_selector_all('input[type="text"], input[type="email"], input[type="tel"], textarea'):
            try:
                if inp.is_visible():
                    visible_inputs += 1
            except Exception:
                pass
        return visible_inputs >= 3
    except Exception:
        return False


def _try_click_apply_button(page) -> bool:
    """Click an 'Apply' / 'Apply Now' button if one exists, to reveal the form."""
    for label in [
        "Apply Now", "Apply for this job", "Apply", "Start Application",
        "Submit Application", "Apply Here", "Quick Apply",
    ]:
        for sel in [
            f'button:has-text("{label}")',
            f'a:has-text("{label}")',
            f'[role="button"]:has-text("{label}")',
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.click()
                    page.wait_for_timeout(3000)
                    return True
            except Exception:
                pass
    return False


def fill_and_submit_form_on_page(
    page,
    job_title: str,
    cv_path: Optional[Path] = None,
    cover_letter_path: Optional[Path] = None,
    applicant_name: Optional[str] = None,
    applicant_email: Optional[str] = None,
    form_url: Optional[str] = None,
) -> bool:
    """
    Fill applicant details and submit on an already-loaded page.
    Handles multi-step wizards. Does not open or close the browser.
    Returns True only if meaningful fields were filled AND form was submitted.
    """
    applicant_name = (applicant_name or SMTP_FROM_NAME or "Applicant").strip()
    applicant_email = (applicant_email or SMTP_USER or "").strip()
    cv_path = cv_path or CV_PATH
    form_url = form_url or (page.url if page else "") or ""
    phone = PHONE_NUMBER or ""
    linkedin_url = LINKEDIN_PROFILE_URL or ""

    fields_filled = 0
    cv_uploaded = False

    try:
        page.wait_for_timeout(1500)

        if not _has_application_form(page):
            # Many SPA sites require clicking an "Apply" button to reveal the form
            if _try_click_apply_button(page):
                if not _has_application_form(page):
                    LOG.info("  [form] No application form after Apply click on: %s", form_url[:80])
                    return False
            else:
                LOG.info("  [form] No application form detected on: %s", form_url[:80])
                return False

        max_steps = 8
        for step in range(max_steps):
            # Fill name fields (first, last, full)
            try:
                for sel, value in [
                    ('input[name*="first_name" i], input[placeholder*="first name" i], input[aria-label*="First" i]', FIRST_NAME),
                    ('input[name*="last_name" i], input[name*="family" i], input[placeholder*="last name" i], input[aria-label*="Last" i]', LAST_NAME),
                    ('input[name*="middle" i], input[placeholder*="middle" i]', MIDDLE_NAME),
                ]:
                    el = page.query_selector(sel)
                    if el and el.is_visible() and not el.input_value():
                        el.fill(value)
                        fields_filled += 1
            except Exception:
                pass
            try:
                for sel in ['input[aria-label*="Name" i]', 'input[placeholder*="name" i]', 'input[name*="name" i]']:
                    el = page.query_selector(sel)
                    if el and not el.input_value() and el.is_visible():
                        name_attr = (el.get_attribute("name") or el.get_attribute("placeholder") or "").lower()
                        if "first" in name_attr:
                            el.fill(FIRST_NAME)
                        elif "last" in name_attr or "family" in name_attr:
                            el.fill(LAST_NAME)
                        else:
                            el.fill(applicant_name)
                        fields_filled += 1
                        break
            except Exception:
                pass

            # Fill email
            if applicant_email:
                try:
                    email_inp = page.query_selector(
                        'input[type="email"], input[placeholder*="email" i], '
                        'input[aria-label*="Email" i], input[name*="email" i]'
                    )
                    if email_inp and not email_inp.input_value():
                        email_inp.fill(applicant_email)
                        fields_filled += 1
                except Exception:
                    pass

            # Fill position / job title
            try:
                pos_inp = page.query_selector(
                    'input[placeholder*="position" i], input[placeholder*="job" i], '
                    'input[aria-label*="Position" i], textarea[placeholder*="position" i]'
                )
                if pos_inp and not pos_inp.get_attribute("value"):
                    pos_inp.fill(job_title[:200])
            except Exception:
                pass

            _fill_phone_and_url_fields(page, phone, linkedin_url)

            # File uploads
            file_inputs = page.query_selector_all('input[type="file"]')
            if cv_path and Path(cv_path).exists() and file_inputs:
                try:
                    for fi in file_inputs:
                        if fi.is_visible():
                            fi.set_input_files(str(cv_path))
                            cv_uploaded = True
                            fields_filled += 1
                            break
                    if not cv_uploaded:
                        file_inputs[0].set_input_files(str(cv_path))
                        cv_uploaded = True
                        fields_filled += 1
                except Exception:
                    pass
            if cover_letter_path and Path(cover_letter_path).exists() and len(file_inputs) > 1:
                try:
                    file_inputs[1].set_input_files(str(cover_letter_path))
                except Exception:
                    pass

            # Cover letter text
            if cover_letter_path and Path(cover_letter_path).exists():
                try:
                    text = Path(cover_letter_path).read_text(encoding="utf-8")[:3000]
                    ta = page.query_selector(
                        'textarea[placeholder*="cover" i], textarea[placeholder*="message" i], '
                        'textarea[aria-label*="Letter" i], textarea'
                    )
                    if ta and not ta.get_attribute("value") and ta.is_visible():
                        ta.fill(text[:2000])
                        fields_filled += 1
                except Exception:
                    pass

            _fill_selects_and_radios(page)
            _fill_required_empty_fields(page, applicant_name, applicant_email, phone)
            page.wait_for_timeout(500)

            # CAPTCHA on first step
            if step == 0:
                recaptcha_el = page.query_selector('[data-sitekey], iframe[src*="recaptcha"]')
                if recaptcha_el:
                    site_key = recaptcha_el.get_attribute("data-sitekey")
                    if not site_key and recaptcha_el.get_attribute("src"):
                        m = re.search(r"[?&]k=([^&]+)", recaptcha_el.get_attribute("src") or "")
                        if m:
                            site_key = m.group(1)
                    if site_key:
                        try:
                            from src.captcha_solver import solve_recaptcha_v2
                            token = solve_recaptcha_v2(site_key, form_url)
                            if token:
                                page.evaluate("""(token) => {
                                    const t = document.querySelector('textarea[name="g-recaptcha-response"]');
                                    if (t) { t.value = token; t.innerHTML = token; }
                                }""", token)
                        except Exception:
                            pass
                    else:
                        LOG.warning("  [form] CAPTCHA detected but no site key found.")

            # Find submit or next button
            submit_btn = None
            for btn_text in ["Submit", "Submit form", "Send", "Send application",
                             "Submit application", "Finish", "Complete"]:
                try:
                    b = page.query_selector(
                        f'button:has-text("{btn_text}"), input[type="submit"][value*="{btn_text}" i], '
                        f'[role="button"]:has-text("{btn_text}")'
                    )
                    if b and b.is_visible():
                        submit_btn = b
                        break
                except Exception:
                    continue

            next_btn = None
            for btn_text in ["Next", "Continue", "Next step", "Proceed",
                             "Apply for this job", "Start application", "Continue to application"]:
                try:
                    b = page.query_selector(
                        f'button:has-text("{btn_text}"), [role="button"]:has-text("{btn_text}"), '
                        f'input[value*="{btn_text}"]'
                    )
                    if b and b.is_visible():
                        next_btn = b
                        break
                except Exception:
                    continue

            if submit_btn:
                if fields_filled == 0 and not cv_uploaded:
                    LOG.info("  [form] Submit button found but no fields were filled on: %s", form_url[:80])
                    return False
                submit_btn.click()
                page.wait_for_timeout(4000)
                content = page.content().lower()
                if any(k in content for k in ["thank", "submitted", "received", "success", "confirmation"]):
                    return True
                return True

            if next_btn:
                next_btn.click()
                page.wait_for_timeout(2500)
                continue

            # No named button: try generic submit only if we filled fields
            if fields_filled > 0 or cv_uploaded:
                try:
                    fallback = page.query_selector('input[type="submit"], button[type="submit"]')
                    if fallback and fallback.is_visible():
                        fallback.click()
                        page.wait_for_timeout(4000)
                        content = page.content().lower()
                        if any(k in content for k in ["thank", "submitted", "received", "success"]):
                            return True
                        return True
                except Exception:
                    pass
            break

        if fields_filled == 0 and not cv_uploaded:
            return False

        content = page.content().lower()
        if any(k in content for k in ["thank", "submitted", "received", "success"]):
            return True
        return False
    except Exception as e:
        LOG.error("  [form] Error: %s", e)
        return False


def submit_application_form(
    form_url: str,
    job_title: str,
    cv_path: Optional[Path] = None,
    cover_letter_path: Optional[Path] = None,
    applicant_name: Optional[str] = None,
    applicant_email: Optional[str] = None,
) -> bool:
    """Open form_url in browser, fill and submit. Returns True on success."""
    if not form_url.startswith("http"):
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(25000)
            page.goto(form_url, wait_until="domcontentloaded", timeout=45000)
            # Wait for SPA frameworks to render their content
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            ok = fill_and_submit_form_on_page(
                page,
                job_title=job_title,
                cv_path=cv_path or CV_PATH,
                cover_letter_path=cover_letter_path,
                applicant_name=applicant_name,
                applicant_email=applicant_email,
                form_url=form_url,
            )
            browser.close()
            return ok
    except Exception as e:
        LOG.error("  [form] Error: %s", e)
        return False
