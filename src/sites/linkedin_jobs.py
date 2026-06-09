"""
LinkedIn Jobs adapter: login, discover jobs via multiple keyword searches,
apply via Easy Apply (with full form filling) or external company website.
"""
import hashlib
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import parse_qs, urlencode, urlparse


from src.sites.base import JobListing, SiteAdapter, matches_job_keywords
from src.config import (
    JOB_KEYWORDS,
    JOB_EXCLUDE_KEYWORDS,
    LINKEDIN_EMAIL,
    LINKEDIN_PASSWORD,
    LINKEDIN_STATE_PATH,
    LINKEDIN_EASY_APPLY_ONLY,
    LINKEDIN_GEO_ID,
    LINKEDIN_LOCATION,
    LINKEDIN_HEADLESS,
    LINKEDIN_INCLUDE_GLOBAL_REMOTE_SEARCH,
    LINKEDIN_DEBUG_ARTIFACTS,
    LINKEDIN_DISCOVERY_MAX_PAGES,
    LINKEDIN_DISCOVERY_MAX_JOBS_PER_SEARCH,
    LINKEDIN_STEALTH,
    LINKEDIN_CHALLENGE_WAIT_SEC,
    LOGS_DIR,
    ensure_dirs,
    SMTP_USER,
    LINKEDIN_PROFILE_URL,
)
from src.log import get_logger
from src.email_utils import send_application_email
from src.form_filler import fill_and_submit_form_on_page, _select_country_code, _PHONE_LOCAL, _PHONE_FULL_PLUS
from src.job_page_utils import extract_apply_from_page
from src.browser_utils import new_stealth_context

LOG = get_logger("linkedin")

BASE_URL = "https://www.linkedin.com"
LOGIN_URL = "https://www.linkedin.com/login"
JOBS_BASE = "https://www.linkedin.com/jobs/search"

# The Easy Apply trigger is sometimes a <button> and sometimes an <a> (and may be localized,
# e.g. French "Candidature simplifiée"). Match all of these or we fall through to external apply.
_EASY_APPLY_SELECTORS = [
    'button[aria-label*="Easy Apply" i]',
    'a[aria-label*="Easy Apply" i]',
    'button:has-text("Easy Apply")',
    'a:has-text("Easy Apply")',
    'button:has-text("Quick Apply")',
    'button[aria-label*="Candidature simplifiée" i]',
    'a[aria-label*="Candidature simplifiée" i]',
    ':has-text("Candidature simplifiée")',
    '[aria-label*="Easy Apply" i]',
    'button.jobs-apply-button',
    'a.jobs-apply-button',
    '.jobs-apply-button button',
]


def _build_search_urls() -> List[str]:
    """Build multiple LinkedIn search URLs from keyword batches for broader coverage."""
    urls = []
    kws = JOB_KEYWORDS or ["developer"]
    batches = [kws[i:i + 2] for i in range(0, min(len(kws), 20), 2)]
    for batch in batches:
        params = {
            "keywords": " ".join(batch),
            "f_TPR": "r2592000",        # past month only
        }
        if LINKEDIN_EASY_APPLY_ONLY:
            params["f_AL"] = "true"
        if LINKEDIN_GEO_ID:
            params["geoId"] = LINKEDIN_GEO_ID
        elif LINKEDIN_LOCATION:
            params["location"] = LINKEDIN_LOCATION
        urls.append(f"{JOBS_BASE}/?{urlencode(params)}")
    return urls


def _build_global_remote_search_urls() -> List[str]:
    """Build remote search URLs for top keyword batches."""
    urls = []
    kws = JOB_KEYWORDS[:6] if JOB_KEYWORDS else ["developer"]
    batches = [kws[i:i + 3] for i in range(0, len(kws), 3)]
    for batch in batches:
        params = {
            "keywords": " ".join(batch),
            "f_WT": "2",                # remote
            "f_TPR": "r2592000",        # past month only
        }
        if LINKEDIN_EASY_APPLY_ONLY:
            params["f_AL"] = "true"
        urls.append(f"{JOBS_BASE}/?{urlencode(params)}")
    return urls


def _clean_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    words = cleaned.split(" ")
    for n in range(2, min(7, len(words) // 2 + 1)):
        tail = " ".join(words[-n:])
        head = " ".join(words[:-n])
        if tail and tail in head:
            cleaned = head.strip()
            break
    return cleaned


def _first_visible(page, selectors: List[str]):
    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                return el
        except Exception:
            continue
    return None


def _robust_find_easy_apply(page, timeout_ms: int = 15000):
    """Poll for the Easy Apply control (button OR anchor), scrolling it into view.

    LinkedIn renders the apply control a few seconds after load and sometimes off-screen,
    so a plain query + is_visible() check misses it. Returns an ElementHandle or None.
    """
    end = time.time() + (timeout_ms / 1000.0)
    while time.time() < end:
        for sel in _EASY_APPLY_SELECTORS:
            try:
                el = page.query_selector(sel)
            except Exception:
                continue
            if not el:
                continue
            try:
                el.scroll_into_view_if_needed(timeout=1500)
            except Exception:
                pass
            try:
                if el.is_visible():
                    return el
            except Exception:
                continue
        page.wait_for_timeout(800)
    return None


def _wait_for_visible_selector(page, selectors: List[str], timeout_ms: int = 15000) -> Optional[str]:
    end = time.time() + (timeout_ms / 1000.0)
    while time.time() < end:
        for sel in selectors:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    return sel
            except Exception:
                continue
        page.wait_for_timeout(250)
    return None


def _is_logged_in(page) -> bool:
    u = (page.url or "").lower()
    # Explicit signed-out / challenge URLs first (an authenticated session never sits here).
    if any(x in u for x in ("/login", "/authwall", "/checkpoint", "/uas/login", "signup")):
        return False
    if "/feed" in u or "/jobs" in u or "/mynetwork" in u or "/in/" in u:
        return True
    markers = [
        "input[placeholder*='Search']",
        "button[aria-label*='Me']",
        "img.global-nav__me-photo",
        "div.global-nav__me",
        "a[href*='/feed/']",
    ]
    return _first_visible(page, markers) is not None


def _new_context(browser):
    ensure_dirs()
    return new_stealth_context(
        browser,
        storage_state=str(LINKEDIN_STATE_PATH) if LINKEDIN_STATE_PATH.exists() else None,
        stealth=LINKEDIN_STEALTH,
    )


def _save_debug_artifact(page, job: JobListing, reason: str) -> None:
    if not LINKEDIN_DEBUG_ARTIFACTS:
        return
    try:
        ensure_dirs()
        dbg_dir = LOGS_DIR / "linkedin-debug"
        dbg_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_title = re.sub(r"[^a-zA-Z0-9]+", "_", (job.title or "job")).strip("_")[:50]
        stem = f"{ts}_{safe_title}_{reason}"
        page.screenshot(path=str(dbg_dir / f"{stem}.png"), full_page=True)
        (dbg_dir / f"{stem}.html").write_text(page.content(), encoding="utf-8")
    except Exception:
        pass


def _is_challenge(page) -> bool:
    """True if LinkedIn is showing a 2FA / captcha / verification checkpoint."""
    u = (page.url or "").lower()
    if "checkpoint" in u or "/challenge" in u or "add-phone" in u:
        return True
    try:
        markers = [
            "iframe[src*='captcha']", "iframe[title*='captcha' i]",
            "input[name='pin']", "input#input__email_verification_pin",
            "[data-test-id*='challenge']", "h1:has-text('verification')",
        ]
        return _first_visible(page, markers) is not None
    except Exception:
        return False


def _save_state(page) -> None:
    try:
        ensure_dirs()
        page.context.storage_state(path=str(LINKEDIN_STATE_PATH))
    except Exception:
        pass


def _wait_out_challenge(page) -> bool:
    """Give the user time to solve a challenge in a visible browser; poll until logged in.

    Headless runs can't be solved by a human, so we fail fast and tell the user how to fix it.
    """
    if LINKEDIN_HEADLESS:
        LOG.warning(
            "  [linkedin] Login hit a verification/2FA challenge in headless mode — cannot solve "
            "automatically. Set LINKEDIN_HEADLESS=false in Settings and run once to sign in "
            "manually; the session is then saved and reused."
        )
        _save_debug_artifact_safe(page, "login_challenge_headless")
        return False
    wait_s = max(0, LINKEDIN_CHALLENGE_WAIT_SEC)
    LOG.warning(
        "  [linkedin] Verification/2FA challenge shown. Please complete it in the browser window "
        "(waiting up to %ds)…", wait_s
    )
    end = time.time() + wait_s
    while time.time() < end:
        time.sleep(3)
        try:
            if _is_logged_in(page) and not _is_challenge(page):
                LOG.info("  [linkedin] Challenge cleared — logged in.")
                _save_state(page)
                return True
        except Exception:
            continue
    LOG.warning("  [linkedin] Challenge not completed in time.")
    return False


def _save_debug_artifact_safe(page, reason: str) -> None:
    try:
        from src.sites.base import JobListing as _JL
        _save_debug_artifact(page, _JL(id="", title="login", company="", url=""), reason)
    except Exception:
        pass


def _linkedin_login(page, timeout: int = 25000) -> bool:
    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        LOG.warning("  [linkedin] No LINKEDIN_EMAIL/PASSWORD set — skipping LinkedIn.")
        return False
    try:
        # 1) Reuse a saved session if we have one. Let any redirect chain settle first —
        #    an authenticated hit on /feed/ can bounce through an interstitial before landing.
        page.goto(f"{BASE_URL}/feed/", wait_until="domcontentloaded", timeout=timeout)
        try:
            page.wait_for_load_state("networkidle", timeout=6000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
        if _is_logged_in(page):
            LOG.info("  [linkedin] Reusing saved session — already logged in.")
            _save_state(page)
            return True

        # 2) Fresh login.
        LOG.info("  [linkedin] Signing in as %s…", LINKEDIN_EMAIL)
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=timeout)
        if _is_logged_in(page):
            LOG.info("  [linkedin] Already logged in.")
            return True
        for sel in ['button:has-text("Accept")', 'button:has-text("Allow")',
                    'button:has-text("I agree")', '#onetrust-accept-btn-handler']:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    page.wait_for_timeout(500)
                    break
            except Exception:
                continue
        user_sel = _wait_for_visible_selector(page,
            ["#username", "input[name='session_key']", "input[type='email']"], timeout_ms=15000)
        pass_sel = _wait_for_visible_selector(page,
            ["#password", "input[name='session_password']", "input[type='password']"], timeout_ms=15000)
        if not user_sel or not pass_sel:
            # No form usually means LinkedIn redirected an already-authenticated session
            # back to the app — confirm before declaring failure.
            page.wait_for_timeout(1500)
            if _is_logged_in(page):
                LOG.info("  [linkedin] Already authenticated (login form not needed).")
                _save_state(page)
                return True
            if _is_challenge(page):
                return _wait_out_challenge(page)
            LOG.warning("  [linkedin] Login form fields not visible (url=%s). LinkedIn may be "
                        "throttling automated logins; try LINKEDIN_HEADLESS=false.", page.url)
            return False
        page.fill(user_sel, LINKEDIN_EMAIL)
        page.fill(pass_sel, LINKEDIN_PASSWORD)
        page.click('button[type="submit"]')
        try:
            page.wait_for_load_state("domcontentloaded", timeout=timeout)
        except Exception:
            pass
        time.sleep(2)

        # 3) Challenge / verification handling.
        if _is_challenge(page):
            return _wait_out_challenge(page)
        if "login" in page.url.lower():
            # Still on the login page → bad credentials or a soft error.
            err = _first_visible(page, ["[error-for]", ".form__label--error", "#error-for-password"])
            detail = ""
            try:
                detail = (err.inner_text() if err else "") or ""
            except Exception:
                pass
            LOG.warning("  [linkedin] Login failed%s. Check email/password.",
                        f" ({detail.strip()[:80]})" if detail.strip() else "")
            return False

        if _is_logged_in(page):
            LOG.info("  [linkedin] Logged in successfully.")
            _save_state(page)
            return True

        # Unknown state — give the visible browser a chance to settle/redirect.
        page.wait_for_timeout(2000)
        if _is_logged_in(page):
            _save_state(page)
            return True
        LOG.warning("  [linkedin] Login ended in an unexpected state (url=%s).", page.url)
        return False
    except Exception as e:
        LOG.warning("  [linkedin] Login error: %s", e)
        return False


def _fill_easy_apply_step_fields(page) -> None:
    """Fill ONLY fields we can answer truthfully from the user's profile.

    No fabrication: arbitrary screening dropdowns/radios and unknown questions are
    left blank unless FORM_FILL_GUESS is enabled. If a required question can't be
    answered honestly, the step won't validate and the application is abandoned
    (caller flags it for manual review) rather than submitted with invented answers.
    """
    from src.config import (
        FIRST_NAME, LAST_NAME, FULL_NAME, COUNTRY, CITY, YEARS_EXPERIENCE, GENDER,
        SUBMISSION_EMAIL, FORM_FILL_GUESS,
    )

    def _label_of(el) -> str:
        try:
            lid = el.get_attribute("id")
            if lid:
                lab = page.query_selector(f'label[for="{lid}"]')
                if lab:
                    return (lab.inner_text() or "").lower()
            return (el.get_attribute("aria-label") or el.get_attribute("placeholder") or "").lower()
        except Exception:
            return ""

    try:
        # Native <select> / custom listbox: we can't know the correct answer to an
        # arbitrary screening dropdown, so only auto-pick when explicitly opted in.
        if FORM_FILL_GUESS:
            for sel in page.query_selector_all("select"):
                if not sel.is_visible():
                    continue
                try:
                    opts = sel.query_selector_all("option")
                    if len(opts) > 1:
                        val = opts[1].get_attribute("value") or (opts[1].inner_text() or "").strip()
                        if val:
                            sel.select_option(value=val)
                            page.wait_for_timeout(150)
                except Exception:
                    pass
            for lb in page.query_selector_all('[role="listbox"]'):
                if not lb.is_visible():
                    continue
                try:
                    lb.click()
                    page.wait_for_timeout(300)
                    opt = page.query_selector('[role="option"]')
                    if opt and opt.is_visible():
                        opt.click()
                        page.wait_for_timeout(250)
                except Exception:
                    pass

        # Radio groups: only an honest consent/terms option is auto-selected.
        # An affirmative ("yes"/authorized) or first-option guess is opt-in only.
        for group in page.query_selector_all('div[role="radiogroup"], fieldset'):
            try:
                radios = [r for r in group.query_selector_all('input[type="radio"], [role="radio"]') if r.is_visible()]
                if not radios:
                    continue
                if any(r.get_attribute("checked") == "true" or r.get_attribute("aria-checked") == "true" for r in radios):
                    continue
                chosen = None
                for r in radios:
                    lt = _label_of(r)
                    if any(t in lt for t in ("agree", "consent", "terms", "privacy")):
                        chosen = r
                        break
                    if FORM_FILL_GUESS and ("yes" in lt or "authorized" in lt or "authorised" in lt):
                        chosen = r
                        break
                if chosen is None and FORM_FILL_GUESS:
                    chosen = radios[0]
                if chosen is not None:
                    chosen.click()
                    page.wait_for_timeout(150)
            except Exception:
                pass

        # Checkboxes: accept consent/terms; never auto-follow the company; other
        # boxes only when guessing is enabled.
        for cb in page.query_selector_all('input[type="checkbox"]'):
            try:
                if not cb.is_visible() or cb.is_checked():
                    continue
                meta = (cb.get_attribute("id") or "").lower() + " " + _label_of(cb)
                if "follow" in meta:
                    continue
                if any(t in meta for t in ("agree", "consent", "terms", "privacy")) or FORM_FILL_GUESS:
                    cb.click()
                    page.wait_for_timeout(120)
            except Exception:
                pass

        # Text/number/phone/url inputs — fill only what we truly know.
        dialog = page.query_selector('div[role="dialog"], .jobs-easy-apply-modal')
        container = dialog or page
        for inp in container.query_selector_all('input[type="text"], input[type="number"], input[type="tel"], input[type="url"]'):
            try:
                if not inp.is_visible() or (inp.input_value() or "").strip():
                    continue
                itype = (inp.get_attribute("type") or "text").lower()
                lt = _label_of(inp)

                if itype == "tel" or "phone" in lt or "mobile" in lt:
                    if _select_country_code(page, inp):
                        inp.fill(_PHONE_LOCAL)
                    else:
                        inp.fill(_PHONE_FULL_PLUS)
                elif itype == "url" or "linkedin" in lt or "profile" in lt or "website" in lt:
                    if LINKEDIN_PROFILE_URL:
                        inp.fill(LINKEDIN_PROFILE_URL)
                elif "first" in lt and "name" in lt:
                    inp.fill(FIRST_NAME)
                elif ("last" in lt or "family" in lt) and "name" in lt:
                    inp.fill(LAST_NAME)
                elif "name" in lt and "company" not in lt and "user" not in lt:
                    inp.fill(FULL_NAME)
                elif "email" in lt:
                    inp.fill(SUBMISSION_EMAIL or SMTP_USER or "")
                elif "city" in lt or "location" in lt:
                    inp.fill(CITY)
                elif "country" in lt or "nationality" in lt:
                    inp.fill(COUNTRY)
                elif "gender" in lt:
                    inp.fill(GENDER)
                elif ("year" in lt and ("experience" in lt or "exp" in lt)) or "years of experience" in lt:
                    if YEARS_EXPERIENCE:
                        inp.fill(YEARS_EXPERIENCE)
                elif FORM_FILL_GUESS:
                    # Opt-in only — these are guesses, not facts.
                    if "salary" in lt or "compensation" in lt:
                        inp.fill("0")
                    elif itype == "number" or "experience" in lt or "gpa" in lt:
                        inp.fill(YEARS_EXPERIENCE)
                # Otherwise leave blank: an unanswerable required field correctly
                # blocks submission instead of getting a fabricated value.
            except Exception:
                pass
    except Exception:
        pass


class LinkedInJobsAdapter(SiteAdapter):
    name = "linkedin_jobs"

    def __init__(self):
        self._browser = None
        self._context = None
        self._page = None

    def _ensure_session(self):
        """Create or reuse a single browser session for all operations."""
        if self._page and not self._page.is_closed():
            if _is_logged_in(self._page):
                return True
        try:
            if self._browser:
                try:
                    self._browser.close()
                except Exception:
                    pass
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                headless=LINKEDIN_HEADLESS,
                slow_mo=80 if not LINKEDIN_HEADLESS else 0,
            )
            self._context = _new_context(self._browser)
            self._page = self._context.new_page()
            self._page.set_default_timeout(25000)
            return _linkedin_login(self._page)
        except Exception as e:
            LOG.error("  [linkedin] Session setup failed: %s", e)
            return False

    def _close_session(self):
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if hasattr(self, "_pw") and self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._browser = None
        self._context = None
        self._page = None

    def discover_jobs(self) -> List[JobListing]:
        if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
            return []
        jobs = []
        try:
            if not self._ensure_session():
                LOG.warning("  [linkedin] Login failed during discovery")
                return []
            page = self._page
            seen = set()
            max_per_search = max(60, LINKEDIN_DISCOVERY_MAX_JOBS_PER_SEARCH)
            search_urls = _build_search_urls()
            if LINKEDIN_INCLUDE_GLOBAL_REMOTE_SEARCH:
                search_urls.extend(_build_global_remote_search_urls())
            for search_url in search_urls:
                if len(jobs) >= max_per_search:
                    break
                try:
                    page.goto(search_url, wait_until="domcontentloaded", timeout=25000)
                    page.wait_for_timeout(3000)
                except Exception as e:
                    LOG.warning("  [linkedin] Search page failed: %s", e)
                    continue
                max_pages = max(1, LINKEDIN_DISCOVERY_MAX_PAGES)
                for _ in range(max_pages - 1):
                    prev_count = len(page.query_selector_all('a[href*="/jobs/view/"]'))
                    try:
                        container = page.query_selector(
                            ".jobs-search-results-list, .scaffold-layout__list-container, "
                            "[class*='jobs-search-results']"
                        )
                        if container:
                            container.evaluate("el => el.scrollTop = el.scrollHeight")
                        else:
                            page.mouse.wheel(0, 800)
                        page.wait_for_timeout(2000)
                    except Exception:
                        page.mouse.wheel(0, 800)
                        page.wait_for_timeout(2000)
                    new_count = len(page.query_selector_all('a[href*="/jobs/view/"]'))
                    if new_count <= prev_count and prev_count > 0:
                        break
                links = page.query_selector_all('a[href*="/jobs/view/"]')
                for a in links:
                    if len(jobs) >= max_per_search:
                        break
                    try:
                        href = a.get_attribute("href") or ""
                        if "?" in href:
                            href = href.split("?")[0]
                        if not href or not href.strip():
                            continue
                        if not href.startswith("http"):
                            href = BASE_URL + href
                        if href in seen:
                            continue
                        seen.add(href)
                        # Read the WHOLE card via closest() — its text reads
                        # "Title\nTitle\nCompany\nLocation". lines[0] is the title; the first
                        # line that isn't the (repeated) title is the company. This is robust to
                        # LinkedIn's hashed/obfuscated CSS class names. (Search cards carry no
                        # per-job posted date; the search itself is filtered to the last 30 days
                        # via f_TPR, so posted_date is left None rather than guessed.)
                        title = ""
                        company = ""
                        try:
                            card_el = a.evaluate_handle(
                                "el => el.closest('li, div[class*=card], div[class*=job]')"
                            ).as_element()
                            if card_el:
                                lines = [ln.strip() for ln in (card_el.inner_text() or "").split("\n") if ln.strip()]
                                if lines:
                                    title = lines[0]
                                    head = title.lower()
                                    for ln in lines[1:]:
                                        if ln.lower() != head and len(ln) > 1:
                                            company = ln
                                            break
                        except Exception:
                            pass
                        if not title:
                            title = a.get_attribute("aria-label") or (a.inner_text() or "").splitlines()[0]
                        title = _clean_text(title or "Job")
                        if len(title) < 3:
                            continue
                        job_id = "linkedin_" + hashlib.sha256(href.encode()).hexdigest()[:14]
                        jobs.append(JobListing(
                            id=job_id, title=title, company=_clean_text(company), url=href, location="",
                        ))
                    except Exception:
                        continue
            LOG.info("  [linkedin] Total unique jobs collected: %d from %d searches", len(jobs), len(search_urls))
        except Exception as e:
            LOG.warning("  [linkedin] Discovery failed: %s", e)
        finally:
            self._close_session()
        return [j for j in jobs if self._matches_filter(j)]

    def _matches_filter(self, job: JobListing) -> bool:
        return matches_job_keywords(job.title, job.company, JOB_KEYWORDS, JOB_EXCLUDE_KEYWORDS)

    def apply(self, job: JobListing, cv_path: str, cover_letter_path: Optional[str] = None) -> bool:
        if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
            return False
        cv = Path(cv_path)
        if not cv.exists():
            return False
        try:
            if not self._ensure_session():
                LOG.warning("  [linkedin] Login failed during apply for: %s", job.title[:50])
                return False
            page = self._page
            page.goto(job.url, wait_until="domcontentloaded", timeout=25000)
            try:
                page.wait_for_load_state("networkidle", timeout=7000)
            except Exception:
                pass
            page.wait_for_timeout(2000)
            try:
                page.mouse.wheel(0, 1200)
                page.wait_for_timeout(800)
            except Exception:
                pass

            # Try Easy Apply first
            easy_apply = _robust_find_easy_apply(page)
            if easy_apply:
                ok = self._do_easy_apply(page, job, cv, cover_letter_path)
                if ok:
                    return True
                LOG.info("  [linkedin] Easy Apply incomplete for: %s", job.title[:60])
                _save_debug_artifact(page, job, "easy_apply_incomplete")

            # Fallback to external apply (uses self._browser, must be inside session)
            apply_href = self._find_external_apply_url(page)
            if apply_href:
                LOG.info("  [linkedin] External apply URL for: %s -> %s", job.title[:40], apply_href[:80])
                return self._apply_external(apply_href, job, cv_path, cover_letter_path)

            LOG.info("  [linkedin] No apply path found for: %s", job.title[:60])
            _save_debug_artifact(page, job, "no_apply_path")
            from src.needs_review import record_needs_review
            record_needs_review(
                job.title, job.url or "",
                ["LinkedIn — no automatic apply path; open the job and apply manually"],
                site="linkedin",
            )
            return False
        except Exception as e:
            LOG.error("  [linkedin] Apply error: %s", e)
            return False

    def _find_external_apply_url(self, page) -> Optional[str]:
        selectors = [
            'a:has-text("Apply on company website")',
            'a:has-text("Apply on Company Website")',
            'a:has-text("Continue to application")',
            'a:has-text("Apply externally")',
            'a:has-text("Apply")',
            'a[data-control-name*="apply"]',
            'a[data-tracking-control-name*="apply"]',
        ]
        for sel in selectors:
            try:
                els = page.query_selector_all(sel)
                for el in els:
                    href = (el.get_attribute("href") or "").strip()
                    if not href:
                        continue
                    if href.startswith("/"):
                        href = BASE_URL + href
                    if "linkedin.com" in href:
                        try:
                            q = parse_qs(urlparse(href).query)
                            for key in ("url", "u", "redirect", "dest"):
                                for c in q.get(key, []):
                                    c = c.strip()
                                    if c.startswith("http") and "linkedin.com" not in c.lower():
                                        return c
                        except Exception:
                            pass
                    else:
                        return href
            except Exception:
                continue

        # Popup buttons
        for sel in ['button:has-text("Apply on company website")',
                    'button:has-text("Continue to application")',
                    'button:has-text("Apply externally")']:
            try:
                btn = page.query_selector(sel)
                if not btn or not btn.is_visible():
                    continue
                with page.expect_popup(timeout=6000) as pop_info:
                    btn.click()
                popup = pop_info.value
                url = popup.url or ""
                popup.close()
                if url and "linkedin.com" not in url:
                    return url
            except Exception:
                continue
        return None

    def _do_easy_apply(self, page, job: JobListing, cv_path: Path, cover_letter_path: Optional[str],
                       dry_run: bool = False) -> bool:
        try:
            easy_btn = _robust_find_easy_apply(page)
            if not easy_btn:
                return False
            LOG.info("  [linkedin] Easy Apply: opening application for: %s", job.title[:55])
            easy_btn.click()
            page.wait_for_timeout(2500)

            dialog = _first_visible(page, ['div[role="dialog"]', '.jobs-easy-apply-modal'])
            if not dialog:
                page.wait_for_timeout(2000)
                dialog = _first_visible(page, ['div[role="dialog"]', '.jobs-easy-apply-modal'])
                if not dialog:
                    LOG.info("  [linkedin] Easy Apply dialog did not open for: %s", job.title[:50])
                    return False

            submitted = False
            cv_uploaded = False
            for step in range(15):
                page.wait_for_timeout(1000)

                # Resume/CV upload — only once (re-uploading each step replaces the selection
                # and slows the flow). LinkedIn keeps the resume across steps.
                if not cv_uploaded:
                    try:
                        file_inps = page.query_selector_all(
                            'div[role="dialog"] input[type="file"], '
                            '.jobs-easy-apply-modal input[type="file"]'
                        )
                        for fi in file_inps:
                            try:
                                fi.set_input_files(str(cv_path))
                                page.wait_for_timeout(800)
                                cv_uploaded = True
                                LOG.info("  [linkedin] Resume uploaded: %s", cv_path.name)
                            except Exception:
                                pass
                    except Exception:
                        pass

                # Don't auto-follow the company on submit.
                try:
                    follow = page.query_selector(
                        'div[role="dialog"] input#follow-company-checkbox, '
                        'div[role="dialog"] label:has-text("Follow") input[type="checkbox"]'
                    )
                    if follow and follow.is_visible() and follow.is_checked():
                        follow.click()
                        page.wait_for_timeout(150)
                except Exception:
                    pass

                # Cover letter textarea
                if cover_letter_path and Path(cover_letter_path).exists():
                    try:
                        ta = page.query_selector(
                            'div[role="dialog"] textarea, .jobs-easy-apply-modal textarea'
                        )
                        if ta and ta.is_visible():
                            val = (ta.input_value() or "").strip()
                            if not val:
                                cover_text = Path(cover_letter_path).read_text(encoding="utf-8")
                                ta.fill(cover_text[:3000])
                    except Exception:
                        pass

                _fill_easy_apply_step_fields(page)
                page.wait_for_timeout(500)

                # Check for validation errors and retry filling
                for retry in range(2):
                    error_msgs = page.query_selector_all(
                        'div[role="dialog"] [class*="error"]:not([class*="error-icon"]), '
                        'div[role="dialog"] .artdeco-inline-feedback--error, '
                        '.jobs-easy-apply-modal .artdeco-inline-feedback--error'
                    )
                    visible_errors = [e for e in error_msgs if e.is_visible()]
                    if not visible_errors:
                        break
                    LOG.info("  [linkedin] Step %d has %d validation errors, re-filling", step, len(visible_errors))
                    _fill_easy_apply_step_fields(page)
                    page.wait_for_timeout(600)

                # Find the action button (Submit takes priority). Bilingual EN/FR — LinkedIn
                # localizes the Easy Apply modal (Suivant/Réviser/Envoyer la candidature).
                submit_btn = _first_visible(page, [
                    'button[aria-label*="Submit application" i]',
                    'button:has-text("Submit application")',
                    'button[aria-label*="Envoyer la candidature" i]',
                    'button:has-text("Envoyer la candidature")',
                ])
                review_btn = _first_visible(page, [
                    'button[aria-label*="Review" i]',
                    'button:has-text("Review your application")',
                    'button:has-text("Review")',
                    'button[aria-label*="Vérifier" i]',
                    'button:has-text("Réviser")',
                    'button:has-text("Vérifier")',
                ])
                next_btn = _first_visible(page, [
                    'button[aria-label*="Continue to next step" i]',
                    'button[aria-label*="Next" i]',
                    'button:has-text("Next")',
                    'button:has-text("Continue")',
                    'button:has-text("Suivant")',
                    'button:has-text("Continuer")',
                ])

                if submit_btn:
                    if dry_run:
                        LOG.info("  [linkedin] DRY RUN — reached 'Submit application'; STOPPING "
                                 "without submitting (no application sent): %s", job.title[:50])
                        return True
                    content_before = page.url
                    submit_btn.click()
                    page.wait_for_timeout(3000)
                    submitted = True
                    break
                elif review_btn:
                    review_btn.click()
                    page.wait_for_timeout(2000)
                    # After review, look for submit
                    final_submit = _first_visible(page, [
                        'button[aria-label*="Submit application"]',
                        'button:has-text("Submit application")',
                        'button:has-text("Submit")',
                    ])
                    if final_submit:
                        if dry_run:
                            LOG.info("  [linkedin] DRY RUN — reached 'Submit application' after "
                                     "Review; STOPPING without submitting: %s", job.title[:50])
                            return True
                        final_submit.click()
                        page.wait_for_timeout(3000)
                        submitted = True
                        break
                    continue
                elif next_btn:
                    content_before = ""
                    try:
                        dlg = page.query_selector('div[role="dialog"]')
                        if dlg:
                            content_before = dlg.inner_text(timeout=1000) or ""
                    except Exception:
                        pass

                    next_btn.click()
                    page.wait_for_timeout(2000)

                    # Check if step advanced
                    try:
                        dlg = page.query_selector('div[role="dialog"]')
                        content_after = dlg.inner_text(timeout=1000) if dlg else ""
                        if content_after and content_after == content_before:
                            _fill_easy_apply_step_fields(page)
                            page.wait_for_timeout(500)
                    except Exception:
                        pass
                    continue
                else:
                    break

            page.wait_for_timeout(2000)
            try:
                body = (page.content() or "").lower()
            except Exception:
                body = ""

            success_markers = [
                "application submitted", "your application was sent",
                "application has been submitted", "you applied",
            ]
            if any(k in body for k in success_markers):
                LOG.info("  [linkedin] Easy Apply submitted for: %s", job.title[:50])
                return True

            dialog_after = _first_visible(page, ['div[role="dialog"]', '.jobs-easy-apply-modal'])
            if submitted and dialog_after is None:
                LOG.info("  [linkedin] Easy Apply likely submitted (dialog closed) for: %s", job.title[:50])
                return True

            if submitted:
                # Dialog still open after submit click - might have errors
                LOG.info("  [linkedin] Easy Apply submit clicked but dialog still open for: %s", job.title[:50])
                _save_debug_artifact(page, job, "submit_dialog_still_open")
                return False

            LOG.info("  [linkedin] Easy Apply did not reach submit for: %s", job.title[:50])
            _save_debug_artifact(page, job, "no_submit_reached")
            return False
        except Exception as e:
            LOG.warning("  [linkedin] Easy Apply step failed: %s", e)
            return False

    def _apply_external(self, apply_url: str, job: JobListing, cv_path: str, cover_letter_path: Optional[str]) -> bool:
        """Open external URL in a new context of the existing browser."""
        ext_context = None
        try:
            if not self._browser:
                LOG.warning("  [linkedin] No browser for external apply: %s", job.title[:50])
                return False
            ext_context = new_stealth_context(self._browser, stealth=LINKEDIN_STEALTH)
            page = ext_context.new_page()
            page.set_default_timeout(30000)
            try:
                page.goto(apply_url, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                LOG.warning("  [linkedin] External page load failed for %s: %s", apply_url[:60], e)
                ext_context.close()
                from src.needs_review import record_needs_review
                record_needs_review(
                    job.title, apply_url,
                    ["LinkedIn external application (page didn't load) — apply on the company site"],
                    site="linkedin",
                )
                return False
            page.wait_for_timeout(3000)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            html = page.content()
            to_email, _ = extract_apply_from_page(html)
            if to_email:
                from src.apply_helper import _pick_cv, _build_email_body, _build_email_subject
                email_cv = _pick_cv(Path(cv_path), for_email=True)
                body = _build_email_body(job.title, cover_letter_path, job.vacancy_number)
                subject = _build_email_subject(job.title, job.vacancy_number)
                ext_context.close()
                ok = send_application_email(
                    to_email, subject, body,
                    cv_path=email_cv,
                    cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                )
                if ok:
                    LOG.info("  [linkedin] External applied via email to %s for: %s", to_email, job.title[:40])
                return ok
            from src.apply_helper import _pick_cv as _pck, resolve_form_identity
            form_cv = _pck(Path(cv_path), for_email=False)
            applicant_name, applicant_email = resolve_form_identity()
            ok = fill_and_submit_form_on_page(
                page, job_title=job.title,
                cv_path=form_cv,
                cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                applicant_name=applicant_name, applicant_email=applicant_email,
                form_url=apply_url,
                vacancy_number=job.vacancy_number,
            )
            ext_context.close()
            if ok:
                LOG.info("  [linkedin] External applied via form for: %s", job.title[:40])
            else:
                # External ATS sites usually need their own login / arbitrary fields and
                # can't be auto-submitted honestly — surface the company link for manual apply.
                from src.needs_review import record_needs_review
                record_needs_review(
                    job.title, apply_url,
                    ["LinkedIn external application — apply on the company site"],
                    site="linkedin",
                )
                LOG.info("  [linkedin] Flagged for manual review (external): %s -> %s", job.title[:40], apply_url[:60])
            return ok
        except Exception as e:
            LOG.warning("  [linkedin] External apply failed: %s", e)
            if ext_context:
                try:
                    ext_context.close()
                except Exception:
                    pass
        return False
