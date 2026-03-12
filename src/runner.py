"""Orchestrate discovery, filter, apply, and response check."""
import signal
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

from src.config import (
    ensure_dirs,
    CV_PATH,
    COVER_LETTER_PATH,
    ADAPTERS_FILTER,
    APPLY_LOCAL_FIRST,
    APPLY_GLOBAL_REMOTE,
    APPLY_OTHER_REGIONS,
    APPLY_ATTEMPT_TIMEOUT_SEC,
    LINKEDIN_APPLY_TIMEOUT_SEC,
    MAX_JOB_AGE_DAYS,
)
from src.applied_store import load_applied_ids, load_applied_keys, mark_applied
from src.applied_store import _normalize_key as _job_key
from src.job_utils import is_job_expired, is_job_too_old, should_apply_by_scope, job_scope_priority
from src.sites.base import JobListing, SiteAdapter
from src.sites.unjobs import UnjobsAdapter
from src.sites.jobs_af import JobsAfAdapter
from src.sites.acbar import AcbarAdapter
from src.sites.wazifaha import WazifahaAdapter
from src.sites.hadaf import HadafAdapter
from src.sites.reliefweb import ReliefwebAdapter
from src.sites.devex import DevexAdapter
from src.sites.un_careers import UnCareersAdapter
from src.sites.da_afghanistan_bank import DaAfghanistanBankAdapter
from src.sites.ctg_global import CtgGlobalAdapter
from src.sites.samuel_hall import SamuelHallAdapter
from src.sites.netlinks import NetlinksAdapter
from src.sites.kabul_jobs import KabulJobsAdapter
from src.sites.linkedin_jobs import LinkedInJobsAdapter
from src.email_utils import check_inbox_for_responses
from src.alerts import check_and_alert
from src.log import get_logger

LOG = get_logger("runner")

# All adapters (only run those with credentials or that don't need them)
_ALL_ADAPTERS: List[SiteAdapter] = [
    UnjobsAdapter(),
    JobsAfAdapter(),
    AcbarAdapter(),
    WazifahaAdapter(),
    HadafAdapter(),
    ReliefwebAdapter(),
    DevexAdapter(),
    UnCareersAdapter(),
    DaAfghanistanBankAdapter(),
    CtgGlobalAdapter(),
    SamuelHallAdapter(),
    NetlinksAdapter(),
    KabulJobsAdapter(),
    LinkedInJobsAdapter(),
    # Removed (domains down / endpoints gone as of 2026-03):
    # IarcscAdapter(), AfghanistanNgoJobsAdapter(), KabulCareersAdapter(),
    # AfghanJobOpportunitiesAdapter(), ScholarshipsAfAdapter(), MofAfghanistanAdapter(),
]


def _get_adapters() -> List[SiteAdapter]:
    """Return adapters to run; filter by ADAPTERS_FILTER if set."""
    if not ADAPTERS_FILTER:
        return list(_ALL_ADAPTERS)
    return [a for a in _ALL_ADAPTERS if a.name.lower() in ADAPTERS_FILTER]


# Backward compat: ADAPTERS is the filtered list (used by main for discover-only / dry-run)
ADAPTERS = _get_adapters()


class ApplyTimeoutError(TimeoutError):
    """Raised when an apply attempt exceeds configured timeout."""


class _time_limit:
    """Unix alarm-based timeout guard for apply attempts."""

    def __init__(self, seconds: int):
        self.seconds = int(seconds or 0)
        self._old_handler = None

    def _handle(self, signum, frame):
        raise ApplyTimeoutError(f"apply timed out after {self.seconds}s")

    def __enter__(self):
        if self.seconds <= 0 or not hasattr(signal, "SIGALRM"):
            return self
        self._old_handler = signal.getsignal(signal.SIGALRM)
        signal.signal(signal.SIGALRM, self._handle)
        signal.alarm(self.seconds)
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.seconds > 0 and hasattr(signal, "SIGALRM"):
            signal.alarm(0)
            if self._old_handler is not None:
                signal.signal(signal.SIGALRM, self._old_handler)
        return False


def _discover_one(adapter: SiteAdapter) -> Tuple[SiteAdapter, List[JobListing], Exception]:
    """Run discovery for one adapter; return (adapter, jobs, error)."""
    try:
        jobs = adapter.discover_jobs()
        return (adapter, jobs or [], None)
    except Exception as e:
        return (adapter, [], e)


def run_discover_and_apply() -> dict:
    """Discover jobs from all portals (parallel), filter, apply to new ones. Returns stats with per_adapter."""
    from src.cover_letter import write_cover_letter_for_job

    ensure_dirs()
    applied = load_applied_ids()
    applied_keys = load_applied_keys()
    applied_urls_this_run: set = set()  # avoid applying twice to same URL in one run
    cv = str(CV_PATH)
    if not CV_PATH.exists():
        return {"discovered": 0, "applied": 0, "skipped": 0, "errors": 0, "per_adapter": {}}

    adapters = _get_adapters()
    stats = {"discovered": 0, "applied": 0, "skipped": 0, "errors": 0, "per_adapter": {}}
    per_adapter: Dict[str, dict] = {}

    # Parallel discovery
    LOG.info("Discovering jobs from %s site(s)...", len(adapters))
    adapter_to_jobs: Dict[str, Tuple[SiteAdapter, List[JobListing]]] = {}
    with ThreadPoolExecutor(max_workers=min(12, len(adapters))) as ex:
        futures = {ex.submit(_discover_one, a): a for a in adapters}
        for fut in as_completed(futures):
            adapter = futures[fut]
            try:
                a, jobs, err = fut.result()
                if err:
                    LOG.warning("  [%s] Discovery failed: %s", a.name, err)
                    per_adapter[a.name] = {"discovered": 0, "applied": 0, "skipped": 0, "errors": 1}
                    stats["errors"] += 1
                else:
                    adapter_to_jobs[a.name] = (a, jobs)
                    per_adapter[a.name] = {"discovered": len(jobs), "applied": 0, "skipped": 0, "errors": 0}
                    stats["discovered"] += len(jobs)
                    LOG.info("  [%s] discovered %s jobs", a.name, len(jobs))
            except Exception as e:
                LOG.exception("  [%s] Discovery error: %s", adapter.name, e)
                per_adapter[adapter.name] = {"discovered": 0, "applied": 0, "skipped": 0, "errors": 1}
                stats["errors"] += 1

    # Apply sequentially (rate limit, dedupe)
    for a in adapters:
        if a.name not in adapter_to_jobs:
            continue
        adapter, jobs = adapter_to_jobs[a.name]
        if APPLY_LOCAL_FIRST:
            jobs = sorted(jobs, key=job_scope_priority)
        for job in jobs:
            if not should_apply_by_scope(job, APPLY_GLOBAL_REMOTE, APPLY_OTHER_REGIONS):
                per_adapter[adapter.name]["skipped"] += 1
                stats["skipped"] += 1
                LOG.info("  [%s] Skip (outside scope): %s", adapter.name, job.title[:50])
                continue
            if not adapter.should_apply(job, applied):
                per_adapter[adapter.name]["skipped"] += 1
                stats["skipped"] += 1
                LOG.info("  [%s] Skip (already applied by ID): %s", adapter.name, job.title[:50])
                continue
            key = _job_key(job.title, job.company)
            if key and key in applied_keys:
                per_adapter[adapter.name]["skipped"] += 1
                stats["skipped"] += 1
                LOG.info("  [%s] Skip (duplicate title/company): %s", adapter.name, job.title[:50])
                continue
            if job.url and job.url in applied_urls_this_run:
                per_adapter[adapter.name]["skipped"] += 1
                stats["skipped"] += 1
                LOG.info("  [%s] Skip (same URL this run): %s", adapter.name, job.title[:50])
                continue
            if is_job_expired(job):
                per_adapter[adapter.name]["skipped"] += 1
                stats["skipped"] += 1
                LOG.info("  [%s] Skip (expired %s): %s", adapter.name, job.close_date, job.title[:50])
                continue
            if is_job_too_old(job, MAX_JOB_AGE_DAYS):
                per_adapter[adapter.name]["skipped"] += 1
                stats["skipped"] += 1
                LOG.info("  [%s] Skip (posted %s, >%dd old): %s", adapter.name, job.posted_date, MAX_JOB_AGE_DAYS, job.title[:50])
                continue
            cover = None
            try:
                cover_path = write_cover_letter_for_job(job)
                cover = str(cover_path) if cover_path else (str(COVER_LETTER_PATH) if COVER_LETTER_PATH.exists() else None)
                ok = None
                timeout_sec = LINKEDIN_APPLY_TIMEOUT_SEC if adapter.name == "linkedin_jobs" else APPLY_ATTEMPT_TIMEOUT_SEC
                for attempt in range(3):
                    try:
                        with _time_limit(timeout_sec):
                            ok = adapter.apply(job, cv, cover)
                        break
                    except ApplyTimeoutError as timeout_err:
                        if attempt < 2:
                            LOG.warning("  [%s] Apply attempt %s timed out (%ss), retrying in 5s: %s",
                                        adapter.name, attempt + 1, timeout_sec, timeout_err)
                            time.sleep(5)
                        else:
                            raise
                    except Exception as attempt_err:
                        if attempt < 2:
                            LOG.warning("  [%s] Apply attempt %s failed, retrying in 5s: %s", adapter.name, attempt + 1, attempt_err)
                            time.sleep(5)
                        else:
                            raise
                if ok:
                    mark_applied(job.id, adapter.name, job.title, job.company)
                    applied.add(job.id)
                    if key:
                        applied_keys.add(key)
                    if job.url:
                        applied_urls_this_run.add(job.url)
                    per_adapter[adapter.name]["applied"] += 1
                    stats["applied"] += 1
                    LOG.info("  [%s] Applied: %s...", adapter.name, job.title[:55])
                    time.sleep(2)  # Rate limit
                else:
                    per_adapter[adapter.name]["skipped"] += 1
                    stats["skipped"] += 1
                    LOG.info("  [%s] Skip (apply returned False - no form/email/submit): %s", adapter.name, job.title[:50])
            except Exception as e:
                per_adapter[adapter.name]["errors"] = per_adapter[adapter.name].get("errors", 0) + 1
                stats["errors"] += 1
                LOG.error("  [%s] Error applying to %s: %s", adapter.name, job.title[:40], e)

    stats["per_adapter"] = per_adapter
    return stats


def run_discover_all() -> List[Tuple[SiteAdapter, List[JobListing]]]:
    """Run discovery in parallel for all adapters; return list of (adapter, jobs)."""
    adapters = _get_adapters()
    results: List[Tuple[SiteAdapter, List[JobListing]]] = []
    with ThreadPoolExecutor(max_workers=min(12, len(adapters))) as ex:
        futures = {ex.submit(_discover_one, a): a for a in adapters}
        for fut in as_completed(futures):
            try:
                a, jobs, err = fut.result()
                if err:
                    LOG.warning("  [%s] Discovery failed: %s", a.name, err)
                    results.append((a, []))
                else:
                    LOG.info("  [%s] discovered %s jobs", a.name, len(jobs or []))
                    results.append((a, jobs or []))
            except Exception as e:
                adapter = futures[fut]
                LOG.warning("  [%s] Discovery error: %s", adapter.name, e)
                results.append((adapter, []))
    return results


def run_check_responses_only() -> int:
    """Check inbox for job responses and send alert email. Returns number of alerts sent."""
    ensure_dirs()
    inbox = check_inbox_for_responses(since_days=7)
    return check_and_alert(inbox)


def run_full() -> dict:
    """Discover, apply, then check responses and alert."""
    stats = run_discover_and_apply()
    alerts = run_check_responses_only()
    stats["alerts_sent"] = alerts
    return stats
