"""Entrypoint: run full pipeline or response-check only."""
import argparse
import sys
from datetime import datetime, timezone

from src.config import ensure_dirs, CV_PATH, SMTP_USER, SMTP_PASSWORD, LOGS_DIR
from src.runner import run_full, run_check_responses_only, run_discover_and_apply
from src.log import get_logger

LOG = get_logger("main")


def _write_last_run(stats: dict) -> None:
    """Write a one-line summary to logs/last_run.txt for quick reference."""
    try:
        ensure_dirs()
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"{ts} | discovered={stats.get('discovered', 0)} applied={stats.get('applied', 0)} skipped={stats.get('skipped', 0)} errors={stats.get('errors', 0)} alerts_sent={stats.get('alerts_sent', 0)}\n"
        (LOGS_DIR / "last_run.txt").write_text(line, encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="JobPulse – automated job application bot")
    parser.add_argument(
        "--check-responses-only",
        action="store_true",
        help="Only check inbox for job responses and send alert email",
    )
    parser.add_argument(
        "--discover-only",
        action="store_true",
        help="Only discover jobs (no apply, no response check)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover jobs and show what would be applied, without sending or submitting",
    )
    args = parser.parse_args()

    if args.check_responses_only:
        LOG.info("Running: check responses only")
        n = run_check_responses_only()
        LOG.info("Alerts sent: %s", n)
        return 0

    if args.dry_run:
        LOG.info("Running: dry-run (discover + list would-apply, no send)")
        from src.runner import run_discover_all
        from src.job_utils import is_job_expired, should_apply_by_scope, job_scope_priority
        from src.applied_store import load_applied_ids
        from src.config import APPLY_LOCAL_FIRST, APPLY_GLOBAL_REMOTE, APPLY_OTHER_REGIONS
        ensure_dirs()
        if not CV_PATH.exists():
            LOG.warning("  Warning: CV_PATH missing - no applications would be sent.")
        if not SMTP_USER or not SMTP_PASSWORD:
            LOG.warning("  Warning: SMTP credentials missing - email applications would fail.")
        applied = load_applied_ids()
        would_apply = 0
        for adapter, jobs in run_discover_all():
            if APPLY_LOCAL_FIRST:
                jobs = sorted(jobs, key=job_scope_priority)
            for j in jobs:
                if j.id in applied or is_job_expired(j):
                    continue
                if not should_apply_by_scope(j, APPLY_GLOBAL_REMOTE, APPLY_OTHER_REGIONS):
                    continue
                if not adapter.should_apply(j, applied):
                    continue
                would_apply += 1
                LOG.info("  Would apply [%s]: %s...", adapter.name, j.title[:55])
                if would_apply >= 50:
                    break
            if would_apply >= 50:
                break
        LOG.info("Total would apply (this run): %s", would_apply)
        return 0

    if args.discover_only:
        LOG.info("Running: discover only (no apply) - jobs matching CV, not expired")
        from src.runner import run_discover_all
        from src.job_utils import is_job_expired
        total = 0
        for adapter, jobs in run_discover_all():
            for j in jobs:
                if is_job_expired(j):
                    continue
                total += 1
                close = f" | close {j.close_date}" if j.close_date else ""
                LOG.info("  [%s] %s%s", adapter.name, j.title[:55], close)
                if total >= 30:
                    break
            if total >= 30:
                break
        LOG.info("Total (matching, not expired): %s", total)
        return 0

    # Startup checks
    if not CV_PATH.exists():
        LOG.warning("Warning: CV file not found at CV_PATH. Applications will be skipped.")
    if not SMTP_USER or not SMTP_PASSWORD:
        LOG.warning("Warning: SMTP_USER or SMTP_PASSWORD missing. Email applications will fail.")

    LOG.info("Running: full (discover + apply + check responses)")
    stats = run_full()
    _write_last_run(stats)
    LOG.info("Done. discovered=%s applied=%s skipped=%s errors=%s alerts_sent=%s",
             stats.get("discovered", 0), stats.get("applied", 0), stats.get("skipped", 0),
             stats.get("errors", 0), stats.get("alerts_sent", 0))
    per_adapter = stats.get("per_adapter") or {}
    if per_adapter:
        for name, pa in sorted(per_adapter.items()):
            d, a, s, e = pa.get("discovered", 0), pa.get("applied", 0), pa.get("skipped", 0), pa.get("errors", 0)
            if d or a or s or e:
                LOG.info("  [%s] discovered=%s applied=%s skipped=%s errors=%s", name, d, a, s, e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
