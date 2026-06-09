"""Shared Playwright helpers: anti-bot stealth context + robust CAPTCHA solving.

LinkedIn and many ATS portals fingerprint headless Chromium (navigator.webdriver,
missing languages/plugins, default UA). These helpers make the browser look like a
normal desktop Chrome so logins/applies are less likely to hit a challenge wall.
"""
import re
import threading
from contextlib import contextmanager
from typing import Optional

from src.config import DISCOVERY_CONCURRENCY
from src.log import get_logger

LOG = get_logger("browser")

# Bound the number of concurrent Chromium instances across all threads so a parallel
# discovery run can't spawn a browser per adapter and exhaust memory.
_BROWSER_SEMAPHORE = threading.BoundedSemaphore(max(1, DISCOVERY_CONCURRENCY))

# A realistic, current desktop Chrome UA (macOS). Kept generic on purpose.
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Injected before any page script runs — hides the most common automation tells.
STEALTH_INIT_JS = r"""
(() => {
  try { Object.defineProperty(navigator, 'webdriver', {get: () => undefined}); } catch (e) {}
  try { Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']}); } catch (e) {}
  try {
    Object.defineProperty(navigator, 'plugins', {
      get: () => [1, 2, 3, 4, 5].map(i => ({name: 'Plugin ' + i, filename: 'p' + i}))
    });
  } catch (e) {}
  try {
    const orig = navigator.permissions && navigator.permissions.query;
    if (orig) {
      navigator.permissions.query = (p) =>
        p && p.name === 'notifications'
          ? Promise.resolve({state: Notification.permission})
          : orig(p);
    }
  } catch (e) {}
  try { window.chrome = window.chrome || {runtime: {}}; } catch (e) {}
  try {
    const gp = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function (p) {
      if (p === 37445) return 'Intel Inc.';
      if (p === 37446) return 'Intel Iris OpenGL Engine';
      return gp.call(this, p);
    };
  } catch (e) {}
})();
"""


def new_stealth_context(
    browser,
    storage_state: Optional[str] = None,
    stealth: bool = True,
):
    """Create a browser context that looks like real desktop Chrome.

    storage_state: path to a saved session JSON (or None for a fresh context).
    """
    kwargs = {
        "viewport": {"width": 1366, "height": 850},
        "locale": "en-US",
        "timezone_id": "Asia/Kabul",
        "user_agent": DEFAULT_UA,
        # Prefer English so localized sites (e.g. LinkedIn job posts) render in English.
        "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
    }
    if storage_state:
        kwargs["storage_state"] = storage_state
    ctx = browser.new_context(**kwargs)
    if stealth:
        try:
            ctx.add_init_script(STEALTH_INIT_JS)
        except Exception as e:
            LOG.warning("  [browser] Could not inject stealth script (continuing without it): %s", e)
    return ctx


@contextmanager
def browser_session(headless: bool = True, stealth: bool = True, storage_state: Optional[str] = None):
    """Yield a ready-to-use Playwright page with guaranteed teardown.

    Centralizes the launch → stealth-context → page → close lifecycle and enforces
    the global concurrency cap. Use this instead of hand-rolling sync_playwright()
    so no code path can leak a Chromium process.

        with browser_session() as page:
            page.goto(url)
            ...
    """
    from playwright.sync_api import sync_playwright

    with _BROWSER_SEMAPHORE:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            try:
                ctx = new_stealth_context(browser, storage_state=storage_state, stealth=stealth)
                page = ctx.new_page()
                yield page
            finally:
                try:
                    browser.close()
                except Exception as e:
                    LOG.warning("  [browser] Error closing browser: %s", e)


def _find_recaptcha_sitekey(page) -> Optional[str]:
    """Best-effort discovery of a reCAPTCHA v2 site key on the current page."""
    try:
        el = page.query_selector("[data-sitekey]")
        if el:
            key = (el.get_attribute("data-sitekey") or "").strip()
            if key:
                return key
    except Exception:
        pass
    try:
        for fr in page.query_selector_all('iframe[src*="recaptcha"]'):
            src = fr.get_attribute("src") or ""
            m = re.search(r"[?&]k=([^&]+)", src)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


def solve_captcha_on_page(page, page_url: str) -> bool:
    """Detect a reCAPTCHA v2 on the page and, if CAPTCHA_API_KEY is set, solve it.

    Injects the token AND fires the grecaptcha callback + input events so the form
    actually accepts it (setting the textarea value alone is usually ignored).
    Returns True if a token was injected, False otherwise.
    """
    from src.config import CAPTCHA_API_KEY

    site_key = _find_recaptcha_sitekey(page)
    if not site_key:
        return False
    if not CAPTCHA_API_KEY:
        LOG.warning(
            "  [captcha] reCAPTCHA detected but CAPTCHA_API_KEY is not set — "
            "cannot solve. Add a 2Captcha key in Settings to auto-solve."
        )
        return False

    LOG.info("  [captcha] reCAPTCHA detected; solving via 2Captcha (up to ~2 min)…")
    try:
        from src.captcha_solver import solve_recaptcha_v2

        token = solve_recaptcha_v2(site_key, page_url)
    except Exception as e:
        LOG.warning("  [captcha] Solver error: %s", e)
        return False
    if not token:
        LOG.warning("  [captcha] Solver returned no token (timeout or bad key).")
        return False

    try:
        page.evaluate(
            """(token) => {
                document.querySelectorAll('textarea[name="g-recaptcha-response"]').forEach(t => {
                    t.value = token;
                    t.innerHTML = token;
                    t.dispatchEvent(new Event('input', {bubbles: true}));
                    t.dispatchEvent(new Event('change', {bubbles: true}));
                });
                // Fire any registered grecaptcha callbacks so the form unlocks.
                try {
                    const cfg = window.___grecaptcha_cfg;
                    if (cfg && cfg.clients) {
                        Object.values(cfg.clients).forEach(client => {
                            Object.values(client).forEach(obj => {
                                if (obj && typeof obj === 'object') {
                                    Object.values(obj).forEach(maybe => {
                                        if (maybe && typeof maybe.callback === 'function') {
                                            try { maybe.callback(token); } catch (e) {}
                                        }
                                    });
                                }
                            });
                        });
                    }
                } catch (e) {}
            }""",
            token,
        )
        LOG.info("  [captcha] Token injected and callback fired.")
        return True
    except Exception as e:
        LOG.warning("  [captcha] Token injection failed: %s", e)
        return False
