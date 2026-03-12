"""Jobs.af adapter – login via saved session (Cloudflare Turnstile blocks automated login),
discover jobs, apply via browser.

First-time setup:  python -m src.sites.jobs_af
This opens a visible browser so you can log in once; the session is saved for future headless runs.
"""
from pathlib import Path
from typing import List, Optional

from playwright.sync_api import sync_playwright

from src.sites.base import JobListing, SiteAdapter, matches_job_keywords
from src.config import (
    JOBS_AF_EMAIL, JOBS_AF_PASSWORD, JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS,
    DATA_DIR, PHONE_NUMBER, SMTP_FROM_NAME,
)
from src.log import get_logger

LOG = get_logger("jobs_af")

BASE_URL = "https://jobs.af"
LOGIN_URL = f"{BASE_URL}/login"
JOBS_URL = f"{BASE_URL}/jobs"
STATE_PATH = DATA_DIR / "jobs_af_state.json"

_WAIT_MS_AFTER_NAV = 5000
_SCROLL_ROUNDS = 8


def _is_logged_in(page) -> bool:
    url = (page.url or "").lower()
    if "/login" in url:
        return False
    for sel in [
        'a[href*="logout"]', 'a[href*="profile"]', 'button:has-text("Logout")',
        'a:has-text("My Profile")', 'a:has-text("Dashboard")',
        'button:has-text("Profile")', 'button:has-text("Jobs")',
    ]:
        try:
            el = page.query_selector(sel)
            if el:
                return True
        except Exception:
            pass
    return "/login" not in url


def _wait_spa_ready(page, timeout_ms: int = 15_000):
    """Wait for the SPA loading spinner to disappear."""
    try:
        page.wait_for_selector(".animate-spin-slow", state="hidden", timeout=timeout_ms)
    except Exception:
        pass
    page.wait_for_timeout(_WAIT_MS_AFTER_NAV)


def _dismiss_cookie_banner(page):
    for label in ("Allow All", "Only Necessary", "Accept", "OK"):
        try:
            btn = page.query_selector(f'button:has-text("{label}")')
            if btn and btn.is_visible():
                btn.click()
                page.wait_for_timeout(500)
                return
        except Exception:
            pass


def _try_login_with_state(browser) -> tuple:
    """Try using saved session state. Returns (context, page, logged_in)."""
    if not STATE_PATH.exists():
        return None, None, False
    try:
        context = browser.new_context(storage_state=str(STATE_PATH))
        page = context.new_page()
        page.set_default_timeout(25_000)
        page.goto(JOBS_URL, wait_until="domcontentloaded", timeout=30_000)
        _dismiss_cookie_banner(page)
        _wait_spa_ready(page)
        if _is_logged_in(page):
            return context, page, True
        page.close()
        context.close()
    except Exception as e:
        LOG.warning("  [jobs_af] Saved session failed: %s", e)
    return None, None, False


def login_interactive():
    """Open a visible browser for the user to log in manually, then save session.
    Run once:  python -m src.sites.jobs_af
    """
    print(f"Opening Jobs.af login page in a visible browser ...")
    print(f"Please log in manually (email: {JOBS_AF_EMAIL})")
    print("The browser will close automatically once login is detected.\n")
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context()
        page = context.new_page()
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)

        print("Waiting for you to log in ...")
        for _ in range(120):
            page.wait_for_timeout(2_000)
            if _is_logged_in(page):
                DATA_DIR.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(STATE_PATH))
                print(f"\nLogin successful!  Session saved to {STATE_PATH}")
                browser.close()
                return True

        print("\nTimeout – login was not detected within 4 minutes.")
        browser.close()
        return False


def _extract_jobs_from_page(page) -> list[dict]:
    """Return [{title, company, uuid, age}] for each visible Active-Jobs card."""
    return page.evaluate("""() => {
        const cards = document.querySelectorAll('div[role="article"].cursor-pointer');
        return Array.from(cards).map(card => {
            const titleId = card.getAttribute('aria-labelledby') || '';
            const titleEl = titleId ? document.getElementById(titleId) : null;
            let title = titleEl ? titleEl.innerText.trim() : '';

            if (!title) {
                const bk = card.querySelector('button[aria-label*="Add"]');
                if (bk) title = bk.getAttribute('aria-label')
                    .replace(/^Add\\s+/i, '').replace(/\\s+to bookmarks$/i, '');
            }

            const lines = card.innerText.split('\\n').map(l => l.trim()).filter(l => l);
            const titleIdx = lines.indexOf(title);
            const company = titleIdx >= 0 && titleIdx + 1 < lines.length
                ? lines[titleIdx + 1] : '';

            // First line is typically the age text like "9 hours ago", "1 day ago"
            const age = lines.length > 0 && /ago$/i.test(lines[0]) ? lines[0] : '';

            return {title, company, uuid: titleId.replace('job-title-', ''), age};
        });
    }""")


class JobsAfAdapter(SiteAdapter):
    name = "jobs_af"

    def discover_jobs(self) -> List[JobListing]:
        if not JOBS_AF_EMAIL or not JOBS_AF_PASSWORD:
            return []
        jobs: list[JobListing] = []
        seen_uuids: set[str] = set()

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context, page, logged_in = _try_login_with_state(browser)
                if not logged_in:
                    LOG.warning(
                        "  [jobs_af] No valid saved session. Run:  python -m src.sites.jobs_af"
                    )
                    browser.close()
                    return []

                if "/jobs" not in page.url:
                    page.goto(JOBS_URL, wait_until="domcontentloaded", timeout=30_000)
                    _wait_spa_ready(page)

                # Scroll to load more Active-Jobs cards (infinite scroll inside viewport)
                for _ in range(_SCROLL_ROUNDS):
                    count_before = len(page.query_selector_all('div[role="article"].cursor-pointer'))
                    page.evaluate("""() => {
                        const vp = document.getElementById('protected-content-viewport');
                        if (vp) vp.scrollTop = vp.scrollHeight;
                        else window.scrollTo(0, document.body.scrollHeight);
                    }""")
                    page.wait_for_timeout(2_000)
                    count_after = len(page.query_selector_all('div[role="article"].cursor-pointer'))
                    if count_after == count_before:
                        break

                raw_jobs = _extract_jobs_from_page(page)
                LOG.info("  [jobs_af] Discovered %d raw cards", len(raw_jobs))

                for rj in raw_jobs:
                    title = (rj.get("title") or "").strip()
                    company = (rj.get("company") or "").strip()
                    uuid = (rj.get("uuid") or "").strip()
                    age = (rj.get("age") or "").strip()
                    if not title or not uuid or uuid in seen_uuids:
                        continue
                    seen_uuids.add(uuid)

                    listing = JobListing(
                        id=f"jobs_af_{uuid[:30]}",
                        title=title,
                        company=company,
                        url="",
                        location="Afghanistan",
                        posted_date=age or None,
                    )
                    if not self._matches_filter(listing):
                        continue

                    # Click card to capture detail-page URL, then go back
                    card_el = page.query_selector(
                        f'div[aria-labelledby="job-title-{uuid}"]'
                    )
                    if card_el:
                        try:
                            card_el.click()
                            page.wait_for_timeout(3_000)
                            listing.url = page.url
                            page.go_back()
                            page.wait_for_timeout(2_000)
                            _wait_spa_ready(page)
                        except Exception:
                            page.goto(JOBS_URL, wait_until="domcontentloaded", timeout=30_000)
                            _wait_spa_ready(page)

                    if listing.url and listing.url != JOBS_URL:
                        jobs.append(listing)

                browser.close()
        except Exception as e:
            LOG.warning("  [jobs_af] Discovery error: %s", e)

        LOG.info("  [jobs_af] Returning %d matched jobs", len(jobs))
        return jobs

    def _matches_filter(self, job: JobListing) -> bool:
        return matches_job_keywords(job.title, job.company, JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS)

    def apply(self, job: JobListing, cv_path: str, cover_letter_path: Optional[str] = None) -> bool:
        if not JOBS_AF_EMAIL or not JOBS_AF_PASSWORD:
            return False
        cv = Path(cv_path)
        if not cv.exists():
            return False

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context, page, logged_in = _try_login_with_state(browser)
                if not logged_in:
                    LOG.warning("  [jobs_af] No valid session for apply. Run: python -m src.sites.jobs_af")
                    browser.close()
                    return False

                page.goto(job.url, wait_until="domcontentloaded", timeout=30_000)
                _dismiss_cookie_banner(page)
                _wait_spa_ready(page)

                # Click "Apply now" on the detail page
                apply_btn = None
                for sel in [
                    'button:has-text("Apply now")', 'button:has-text("Apply")',
                    'a:has-text("Apply now")', 'a:has-text("Apply")',
                ]:
                    apply_btn = page.query_selector(sel)
                    if apply_btn and apply_btn.is_visible():
                        break
                    apply_btn = None

                if not apply_btn:
                    LOG.info("  [jobs_af] No apply button on: %s", job.title[:50])
                    browser.close()
                    return False

                apply_btn.click()
                page.wait_for_timeout(3_000)

                # Jobs.af shows a "You are leaving Jobs.af" modal for external
                # job applications.  Click "Continue" to follow the redirect.
                continue_btn = page.query_selector('button:has-text("Continue")')
                if continue_btn and continue_btn.is_visible():
                    # Extract destination URL from the modal text
                    modal = page.query_selector('[role="dialog"], [class*="modal"], [class*="Modal"]')
                    dest_url = ""
                    if modal:
                        modal_text = modal.inner_text() or ""
                        for line in modal_text.split("\n"):
                            line = line.strip()
                            if line.startswith("http"):
                                dest_url = line
                                break
                    continue_btn.click()
                    page.wait_for_timeout(5_000)
                    LOG.info("  [jobs_af] Redirected to employer site: %s", (dest_url or page.url)[:80])

                    # Now on the employer's career site – try form filling
                    from src.form_filler import fill_and_submit_form_on_page
                    ok = fill_and_submit_form_on_page(
                        page, job_title=job.title,
                        cv_path=cv, cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                        applicant_name=SMTP_FROM_NAME or "", applicant_email=JOBS_AF_EMAIL,
                        form_url=page.url,
                    )
                    browser.close()
                    if ok:
                        LOG.info("  [jobs_af] Applied on employer site: %s", job.title[:50])
                    else:
                        LOG.info("  [jobs_af] No form on employer site for: %s", job.title[:50])
                    return ok

                # Direct apply form on Jobs.af itself (no redirect)
                self._fill_form(page, cv, cover_letter_path)

                submitted = False
                for sel in [
                    'button[type="submit"]:has-text("Submit")',
                    'button:has-text("Submit Application")',
                    'button:has-text("Submit")',
                    'button:has-text("Apply")',
                    'input[type="submit"]',
                ]:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(4_000)
                        submitted = True
                        break

                if submitted:
                    body = (page.inner_text("body") or "").lower()
                    if any(w in body for w in ("thank", "submitted", "success", "applied")):
                        LOG.info("  [jobs_af] Applied successfully: %s", job.title[:50])
                        browser.close()
                        return True

                browser.close()
                LOG.info("  [jobs_af] Could not confirm application for: %s", job.title[:50])
                return submitted

        except Exception as e:
            LOG.warning("  [jobs_af] Apply error for %s: %s", job.title[:40], e)
            return False

    @staticmethod
    def _fill_form(page, cv: Path, cover_letter_path: Optional[str]):
        """Best-effort fill of any on-page application form."""
        file_inputs = page.query_selector_all('input[type="file"]')
        for i, fi in enumerate(file_inputs):
            try:
                if i == 0:
                    fi.set_input_files(str(cv))
                elif cover_letter_path and Path(cover_letter_path).exists():
                    fi.set_input_files(cover_letter_path)
            except Exception:
                pass

        for inp in page.query_selector_all("input:visible, textarea:visible"):
            try:
                name = (inp.get_attribute("name") or inp.get_attribute("placeholder") or "").lower()
                itype = (inp.get_attribute("type") or "text").lower()
                if itype in ("file", "hidden", "submit", "button", "checkbox", "radio"):
                    continue
                if inp.input_value():
                    continue
                if any(k in name for k in ("phone", "mobile", "tel")):
                    inp.fill(PHONE_NUMBER or "")
                elif any(k in name for k in ("email", "e-mail")):
                    inp.fill(JOBS_AF_EMAIL)
            except Exception:
                pass


if __name__ == "__main__":
    login_interactive()
