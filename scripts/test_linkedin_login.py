"""One-off: real LinkedIn login test in a visible browser. Not part of the app.

Run: LINKEDIN_HEADLESS=false .venv/bin/python scripts/test_linkedin_login.py
"""
import os
import sys

# Force a visible browser so a human can solve any 2FA/CAPTCHA challenge.
os.environ["LINKEDIN_HEADLESS"] = "false"

from playwright.sync_api import sync_playwright

from src.config import LINKEDIN_EMAIL, LINKEDIN_STATE_PATH, LINKEDIN_STEALTH
from src.sites.linkedin_jobs import _linkedin_login, _new_context, JOBS_BASE


def main() -> int:
    print(f"→ Testing LinkedIn login as {LINKEDIN_EMAIL[:3]}***  (stealth={LINKEDIN_STEALTH})")
    print(f"  Saved session: {LINKEDIN_STATE_PATH}  exists={LINKEDIN_STATE_PATH.exists()}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=60)
        ctx = _new_context(browser)
        page = ctx.new_page()
        page.set_default_timeout(30000)

        ok = _linkedin_login(page)
        print(f"\n=== LOGIN RESULT: {'✅ LOGGED IN' if ok else '❌ NOT LOGGED IN'} ===")
        print(f"  current url: {page.url}")

        if ok:
            # Prove we can reach the authenticated jobs search and see real cards.
            try:
                page.goto(f"{JOBS_BASE}/?keywords=software%20engineer&f_TPR=r2592000",
                          wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(4000)
                cards = page.query_selector_all('a[href*="/jobs/view/"]')
                print(f"  jobs search reachable: found {len(cards)} job links on first page")
            except Exception as e:
                print(f"  jobs search check failed: {e}")
            try:
                page.context.storage_state(path=str(LINKEDIN_STATE_PATH))
                print(f"  session saved → {LINKEDIN_STATE_PATH}")
            except Exception as e:
                print(f"  could not save session: {e}")

        print("\n  Closing browser in 5s…")
        page.wait_for_timeout(5000)
        browser.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
