"""Dry Easy Apply on a SPECIFIC LinkedIn job URL (fills everything, never submits).

Run: PYTHONPATH=$PWD LINKEDIN_HEADLESS=false .venv/bin/python \
        scripts/test_linkedin_dry_apply_url.py "<job_url>"
"""
import os
import sys
from pathlib import Path

os.environ["LINKEDIN_HEADLESS"] = "false"

from src.config import CV_PATH, COVER_LETTER_PATH
from src.sites.base import JobListing
from src.sites.linkedin_jobs import LinkedInJobsAdapter, _robust_find_easy_apply

DEFAULT_URL = "https://www.linkedin.com/jobs/view/4418153037/"


def main() -> int:
    raw = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    url = raw.split("?")[0]
    cv = Path(CV_PATH)
    cover = str(COVER_LETTER_PATH) if COVER_LETTER_PATH.is_file() else None
    print(f"→ Job: {url}")
    print(f"→ CV : {cv.name}  exists={cv.exists()}")

    adapter = LinkedInJobsAdapter()
    if not adapter._ensure_session():
        print("❌ LinkedIn login failed.")
        return 1
    page = adapter._page
    print("✅ Logged in.")

    # Load the job; the Easy Apply control can render slowly, so retry with a reload.
    ea = None
    for attempt in range(3):
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        page.wait_for_timeout(2500)
        ea = _robust_find_easy_apply(page, timeout_ms=18000)
        if ea:
            break
        print(f"  attempt {attempt + 1}: Easy Apply control not rendered yet; reloading…")
        page.wait_for_timeout(2000)

    title = page.title().split(" | ")[0]
    job = JobListing(id="dryrun", title=title[:80], company="", url=url)
    print(f"→ Title: {job.title}")

    if not ea:
        body = (page.content() or "").lower()
        if "applied" in body and "easy apply" not in body:
            print("⚠️  This job shows as ALREADY APPLIED (no Easy Apply button).")
        else:
            print("⚠️  No Easy Apply button found (external apply or LinkedIn throttling renders).")
        adapter._close_session()
        return 1

    print("\n=== Running Easy Apply in DRY mode — will FILL everything but NOT submit ===")
    result = adapter._do_easy_apply(page, job, cv, cover, dry_run=True)
    print("\n" + "=" * 64)
    if result:
        print("✅ DRY RUN SUCCESS — form filled and it reached 'Submit application',")
        print("   then STOPPED. No application was sent.")
    else:
        print("⚠️  Did not reach the Submit button (see log above for where it stopped).")
    print("=" * 64)
    print("  Leaving the window open 10s so you can inspect the filled form…")
    page.wait_for_timeout(10000)
    adapter._close_session()
    return 0 if result else 2


if __name__ == "__main__":
    sys.exit(main())
