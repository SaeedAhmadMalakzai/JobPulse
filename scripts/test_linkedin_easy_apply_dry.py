"""One-off: run ONE LinkedIn Easy Apply in DRY mode (fills everything, never submits).

Picks the first Easy Apply job for a keyword, opens the application, uploads the CV,
fills all fields, clicks Next/Review — and STOPS the instant it reaches
"Submit application". No application is ever sent.

Run: PYTHONPATH=$PWD LINKEDIN_HEADLESS=false .venv/bin/python scripts/test_linkedin_easy_apply_dry.py
"""
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

os.environ["LINKEDIN_HEADLESS"] = "false"

from src.config import CV_PATH, COVER_LETTER_PATH, JOB_KEYWORDS
from src.sites.base import JobListing
from src.sites.linkedin_jobs import LinkedInJobsAdapter, JOBS_BASE, _first_visible, BASE_URL

KEYWORD = (JOB_KEYWORDS[0] if JOB_KEYWORDS else "software engineer")


def main() -> int:
    cv = Path(CV_PATH)
    print(f"→ CV: {cv}  exists={cv.exists()}")
    if not cv.exists():
        print("  ⚠️  CV not found — the upload step will be skipped, but field-filling still runs.")
    cover = str(COVER_LETTER_PATH) if COVER_LETTER_PATH.is_file() else None

    adapter = LinkedInJobsAdapter()
    if not adapter._ensure_session():
        print("❌ LinkedIn login failed — cannot run dry apply.")
        return 1
    page = adapter._page
    print("✅ Logged in. Searching Easy Apply jobs for:", KEYWORD)

    # Easy Apply only (f_AL=true), remote (f_WT=2) so results aren't region-locked, past month.
    params = {"keywords": KEYWORD, "f_AL": "true", "f_WT": "2", "f_TPR": "r2592000"}
    page.goto(f"{JOBS_BASE}/?{urlencode(params)}", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(4000)

    # Scroll the results list to load more cards.
    for _ in range(4):
        try:
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(1200)
        except Exception:
            break

    # Collect candidate job links.
    candidates = []
    seen = set()
    for a in page.query_selector_all('a[href*="/jobs/view/"]'):
        href = (a.get_attribute("href") or "").split("?")[0]
        if not href:
            continue
        if not href.startswith("http"):
            href = BASE_URL + href
        if href in seen:
            continue
        seen.add(href)
        title = (a.get_attribute("aria-label") or a.inner_text() or "Job").strip().splitlines()[0]
        candidates.append(JobListing(id="dryrun", title=title[:80], company="", url=href))

    def _apply_button_text(pg):
        """Read the real apply button's text/aria to tell Easy Apply from external."""
        try:
            pg.wait_for_selector('button.jobs-apply-button, .jobs-apply-button button',
                                 timeout=8000)
        except Exception:
            return ""
        btn = pg.query_selector('button.jobs-apply-button, .jobs-apply-button button')
        if not btn:
            return ""
        return ((btn.get_attribute("aria-label") or "") + " " + (btn.inner_text() or "")).lower()

    print(f"  {len(candidates)} candidate jobs; finding one with an Easy Apply button…")
    picked = None
    for cand in candidates[:18]:
        page.goto(cand.url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        txt = _apply_button_text(page)
        if "easy apply" in txt:
            picked = cand
            break
        print(f"    skip ({'external' if txt else 'no apply btn'}): {cand.title[:48]}")

    if not picked:
        print("❌ No Easy Apply job found among candidates. Re-run to try a fresh batch.")
        adapter._close_session()
        return 1
    print(f"\n→ Easy Apply job: {picked.title}\n  {picked.url}")

    print("\n=== Running Easy Apply in DRY mode (will NOT submit) ===")
    result = adapter._do_easy_apply(page, picked, cv, cover, dry_run=True)
    print(f"\n=== DRY APPLY RESULT: {'✅ reached Submit and stopped (no application sent)' if result else '⚠️ did not reach Submit (see log above)'} ===")
    print("  Leaving the window open 8s so you can see the final state…")
    page.wait_for_timeout(8000)
    adapter._close_session()
    return 0


if __name__ == "__main__":
    sys.exit(main())
