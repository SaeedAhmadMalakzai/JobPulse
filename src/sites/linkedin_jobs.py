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

from playwright.sync_api import sync_playwright

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
    LOGS_DIR,
    ensure_dirs,
    CV_PATH,
    SMTP_FROM_NAME,
    SMTP_USER,
    PHONE_NUMBER,
    LINKEDIN_PROFILE_URL,
)
from src.log import get_logger
from src.email_utils import send_application_email
from src.form_filler import fill_and_submit_form_on_page, _select_country_code, _PHONE_LOCAL, _PHONE_FULL_PLUS
from src.job_page_utils import extract_apply_from_page

LOG = get_logger("linkedin")

BASE_URL = "https://www.linkedin.com"
LOGIN_URL = "https://www.linkedin.com/login"
JOBS_BASE = "https://www.linkedin.com/jobs/search"


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
    if "/feed" in u or "/jobs/" in u:
        return True
    markers = [
        "input[placeholder*='Search']",
        "button[aria-label*='Me']",
        "img.global-nav__me-photo",
    ]
    return _first_visible(page, markers) is not None


def _new_context(browser):
    ensure_dirs()
    return browser.new_context(
        storage_state=str(LINKEDIN_STATE_PATH) if LINKEDIN_STATE_PATH.exists() else None
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


def _linkedin_login(page, timeout: int = 25000) -> bool:
    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        return False
    try:
        page.goto(f"{BASE_URL}/feed/", wait_until="domcontentloaded", timeout=timeout)
        if _is_logged_in(page):
            return True
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=timeout)
        if _is_logged_in(page):
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
            LOG.warning("  [linkedin] Login form fields not visible. url=%s", page.url)
            return False
        page.fill(user_sel, LINKEDIN_EMAIL)
        page.fill(pass_sel, LINKEDIN_PASSWORD)
        page.click('button[type="submit"]')
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
        time.sleep(2)
        if "login" in page.url.lower() or "checkpoint" in page.url.lower():
            LOG.warning("  [linkedin] Login may have failed (captcha/verification). Check account.")
            return False
        try:
            ensure_dirs()
            page.context.storage_state(path=str(LINKEDIN_STATE_PATH))
        except Exception:
            pass
        return True
    except Exception as e:
        LOG.warning("  [linkedin] Login error: %s", e)
        return False


def _fill_easy_apply_step_fields(page) -> None:
    """Fill dropdowns, radio, checkbox, text/number/phone inputs in the current Easy Apply step."""
    try:
        # Native <select>
        for sel in page.query_selector_all("select"):
            if not sel.is_visible():
                continue
            try:
                opts = sel.query_selector_all("option")
                if not opts:
                    continue
                val = None
                for opt in opts:
                    text = (opt.inner_text() or opt.get_attribute("value") or "").strip().lower()
                    if text in ("yes", "1", "2", "3", "5", "1 year", "2 years", "3 years",
                                "5 years", "i am", "authorized", "authorised"):
                        val = opt.get_attribute("value") or text
                        break
                if val is None and len(opts) > 1:
                    val = opts[1].get_attribute("value") or (opts[1].inner_text() or "").strip()
                if val is not None:
                    sel.select_option(value=val)
                    page.wait_for_timeout(200)
            except Exception:
                try:
                    sel.select_option(index=1)
                except Exception:
                    pass

        # Custom listbox
        for lb in page.query_selector_all('[role="listbox"]'):
            if not lb.is_visible():
                continue
            try:
                lb.click()
                page.wait_for_timeout(400)
                opt = page.query_selector('[role="option"]')
                if opt and opt.is_visible():
                    opt.click()
                    page.wait_for_timeout(300)
            except Exception:
                pass

        # Radio groups
        for group in page.query_selector_all('div[role="radiogroup"], fieldset'):
            try:
                radios = [r for r in group.query_selector_all('input[type="radio"], [role="radio"]') if r.is_visible()]
                if not radios:
                    continue
                if any(r.get_attribute("checked") == "true" or r.get_attribute("aria-checked") == "true" for r in radios):
                    continue
                for r in radios:
                    label_text = ""
                    try:
                        lid = r.get_attribute("id")
                        if lid:
                            lab = page.query_selector(f'label[for="{lid}"]')
                            if lab:
                                label_text = (lab.inner_text() or "").lower()
                        if not label_text:
                            label_text = (r.get_attribute("aria-label") or "").lower()
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

        # Checkboxes
        for cb in page.query_selector_all('input[type="checkbox"]'):
            try:
                if not cb.is_visible() or cb.is_checked():
                    continue
                cb.click()
                page.wait_for_timeout(150)
            except Exception:
                pass

        from src.config import FIRST_NAME, LAST_NAME, FULL_NAME, COUNTRY, CITY, YEARS_EXPERIENCE, GENDER
        dialog = page.query_selector('div[role="dialog"], .jobs-easy-apply-modal')
        container = dialog or page
        for inp in container.query_selector_all('input[type="text"], input[type="number"], input[type="tel"], input[type="url"]'):
            try:
                if not inp.is_visible():
                    continue
                val = (inp.input_value() or "").strip()
                if val:
                    continue
                input_type = (inp.get_attribute("type") or "text").lower()
                label_text = ""
                try:
                    lid = inp.get_attribute("id")
                    if lid:
                        lab = page.query_selector(f'label[for="{lid}"]')
                        if lab:
                            label_text = (lab.inner_text() or "").lower()
                    if not label_text:
                        label_text = (inp.get_attribute("aria-label") or inp.get_attribute("placeholder") or "").lower()
                except Exception:
                    pass

                if input_type == "tel" or "phone" in label_text or "mobile" in label_text:
                    if _select_country_code(page, inp):
                        inp.fill(_PHONE_LOCAL)
                    else:
                        inp.fill(_PHONE_FULL_PLUS)
                elif input_type == "url" or "linkedin" in label_text or "profile" in label_text or "website" in label_text:
                    inp.fill(LINKEDIN_PROFILE_URL or "")
                elif "first" in label_text and "name" in label_text:
                    inp.fill(FIRST_NAME)
                elif ("last" in label_text or "family" in label_text) and "name" in label_text:
                    inp.fill(LAST_NAME)
                elif "name" in label_text:
                    inp.fill(FULL_NAME)
                elif "email" in label_text:
                    inp.fill(SMTP_USER or "")
                elif "city" in label_text or "location" in label_text:
                    inp.fill(CITY)
                elif "country" in label_text or "nationality" in label_text:
                    inp.fill(COUNTRY)
                elif "gender" in label_text:
                    inp.fill(GENDER)
                elif "salary" in label_text or "compensation" in label_text:
                    inp.fill("0")
                elif "headline" in label_text or "summary" in label_text:
                    inp.fill("Software Engineer with 5+ years experience")
                elif input_type == "number" or "year" in label_text or "experience" in label_text or "gpa" in label_text:
                    inp.fill(YEARS_EXPERIENCE)
                else:
                    inp.fill(YEARS_EXPERIENCE)
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
                        title = ""
                        try:
                            card = a.locator(
                                "xpath=ancestor::div[contains(@class, 'job') or "
                                "contains(@class, 'card') or contains(@class, 'base-card')][1]"
                            )
                            title = card.locator(
                                ".job-card-list__title, .base-search-card__title, h3"
                            ).first.inner_text(timeout=2000)
                        except Exception:
                            title = a.get_attribute("aria-label") or (a.inner_text() or "").splitlines()[0]
                        title = _clean_text(title or "Job")
                        if len(title) < 3:
                            continue
                        job_id = "linkedin_" + hashlib.sha256(href.encode()).hexdigest()[:14]
                        jobs.append(JobListing(
                            id=job_id, title=title, company="", url=href, location="",
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
            easy_apply = _first_visible(page, [
                'button[aria-label*="Easy Apply"]',
                'button:has-text("Easy Apply")',
                'button:has-text("Quick Apply")',
                'button.jobs-apply-button',
                '.jobs-apply-button button',
            ])
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

    def _do_easy_apply(self, page, job: JobListing, cv_path: Path, cover_letter_path: Optional[str]) -> bool:
        try:
            easy_btn = _first_visible(page, [
                'button[aria-label*="Easy Apply"]',
                'button:has-text("Easy Apply")',
                'button:has-text("Quick Apply")',
                'button.jobs-apply-button',
            ])
            if not easy_btn:
                return False
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
            for step in range(15):
                page.wait_for_timeout(1000)

                # Resume/CV upload on every step (some steps have file inputs)
                try:
                    file_inps = page.query_selector_all(
                        'div[role="dialog"] input[type="file"], '
                        '.jobs-easy-apply-modal input[type="file"]'
                    )
                    for fi in file_inps:
                        try:
                            fi.set_input_files(str(cv_path))
                            page.wait_for_timeout(800)
                        except Exception:
                            pass
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

                # Find the action button (Submit takes priority)
                submit_btn = _first_visible(page, [
                    'button[aria-label*="Submit application"]',
                    'button:has-text("Submit application")',
                ])
                review_btn = _first_visible(page, [
                    'button[aria-label*="Review"]',
                    'button:has-text("Review")',
                ])
                next_btn = _first_visible(page, [
                    'button[aria-label*="Next"]',
                    'button:has-text("Next")',
                    'button:has-text("Continue")',
                ])

                if submit_btn:
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
            ext_context = self._browser.new_context()
            page = ext_context.new_page()
            page.set_default_timeout(30000)
            try:
                page.goto(apply_url, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                LOG.warning("  [linkedin] External page load failed for %s: %s", apply_url[:60], e)
                ext_context.close()
                return False
            page.wait_for_timeout(3000)
            try:
                page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass
            html = page.content()
            to_email, _ = extract_apply_from_page(html)
            if to_email:
                body = f"Application for: {job.title}\n\nPlease find my CV and cover letter attached."
                if cover_letter_path and Path(cover_letter_path).exists():
                    body = Path(cover_letter_path).read_text(encoding="utf-8")
                ext_context.close()
                ok = send_application_email(
                    to_email, f"Application: {job.title}", body,
                    cv_path=Path(cv_path),
                    cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                )
                if ok:
                    LOG.info("  [linkedin] External applied via email to %s for: %s", to_email, job.title[:40])
                return ok
            ok = fill_and_submit_form_on_page(
                page, job_title=job.title,
                cv_path=Path(cv_path),
                cover_letter_path=Path(cover_letter_path) if cover_letter_path else None,
                applicant_name=SMTP_FROM_NAME, applicant_email=SMTP_USER,
                form_url=apply_url,
            )
            ext_context.close()
            if ok:
                LOG.info("  [linkedin] External applied via form for: %s", job.title[:40])
            return ok
        except Exception as e:
            LOG.warning("  [linkedin] External apply failed: %s", e)
            if ext_context:
                try:
                    ext_context.close()
                except Exception:
                    pass
        return False
