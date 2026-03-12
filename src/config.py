"""Load configuration from environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _get_bool(key: str, default: bool = False) -> bool:
    raw = _get(key, "true" if default else "false").lower()
    return raw in {"1", "true", "yes", "on"}


def _get_int(key: str, default: int) -> int:
    try:
        return int(_get(key, str(default)))
    except Exception:
        return default


def _get_path(key: str, default: str) -> Path:
    raw = _get(key, default)
    p = Path(raw)
    if not p.is_absolute():
        p = _ROOT / p
    return p


# SMTP (send applications)
SMTP_HOST = _get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(_get("SMTP_PORT", "587"))
SMTP_USER = _get("SMTP_USER")
SMTP_PASSWORD = _get("SMTP_PASSWORD")
SMTP_FROM_NAME = _get("SMTP_FROM_NAME", "Applicant")

# Alerts (notify user of responses)
ALERT_EMAIL = _get("ALERT_EMAIL")

# IMAP (check inbox for job responses)
IMAP_HOST = _get("IMAP_HOST", "imap.gmail.com")
IMAP_PORT = int(_get("IMAP_PORT", "993"))
IMAP_USER = _get("IMAP_USER")
IMAP_PASSWORD = _get("IMAP_PASSWORD")

# Attachments
CV_PATH = _get_path("CV_PATH", "cv.pdf")
COVER_LETTER_PATH = _get_path("COVER_LETTER_PATH", "cover_letter.pdf")

# Applicant details for form filling (set in .env; no defaults to avoid leaking personal data)
FIRST_NAME = _get("FIRST_NAME")
MIDDLE_NAME = _get("MIDDLE_NAME")
LAST_NAME = _get("LAST_NAME")
FULL_NAME = _get("FULL_NAME")
SALUTATION = _get("SALUTATION")
GENDER = _get("GENDER")
PHONE_COUNTRY_CODE = _get("PHONE_COUNTRY_CODE")
PHONE_NUMBER = _get("PHONE_NUMBER")
COUNTRY = _get("COUNTRY")
CITY = _get("CITY")
YEARS_EXPERIENCE = _get("YEARS_EXPERIENCE")
LINKEDIN_PROFILE_URL = _get("LINKEDIN_PROFILE_URL")
SUBMISSION_EMAIL = _get("SUBMISSION_EMAIL")
SUBMISSION_EMAIL_PASSWORD = _get("SUBMISSION_EMAIL_PASSWORD")
# Cover letter bio (optional; used in generated letters)
COVER_LETTER_UNIVERSITY = _get("COVER_LETTER_UNIVERSITY")
COVER_LETTER_PREVIOUS_ORGANIZATION = _get("COVER_LETTER_PREVIOUS_ORGANIZATION")

# Portal credentials
JOBS_AF_EMAIL = _get("JOBS_AF_EMAIL")
JOBS_AF_PASSWORD = _get("JOBS_AF_PASSWORD")
ACBAR_EMAIL = _get("ACBAR_EMAIL")
ACBAR_PASSWORD = _get("ACBAR_PASSWORD")
WAZIFAHA_EMAIL = _get("WAZIFAHA_EMAIL")
WAZIFAHA_PASSWORD = _get("WAZIFAHA_PASSWORD")
HADAF_EMAIL = _get("HADAF_EMAIL")
HADAF_PASSWORD = _get("HADAF_PASSWORD")
LINKEDIN_EMAIL = _get("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = _get("LINKEDIN_PASSWORD")
LINKEDIN_STATE_PATH = _get_path("LINKEDIN_STATE_PATH", "data/linkedin_state.json")
LINKEDIN_EASY_APPLY_ONLY = _get_bool("LINKEDIN_EASY_APPLY_ONLY", False)
LINKEDIN_GEO_ID = _get("LINKEDIN_GEO_ID")
LINKEDIN_LOCATION = _get("LINKEDIN_LOCATION")
LINKEDIN_HEADLESS = _get_bool("LINKEDIN_HEADLESS", True)
LINKEDIN_INCLUDE_GLOBAL_REMOTE_SEARCH = _get_bool("LINKEDIN_INCLUDE_GLOBAL_REMOTE_SEARCH", True)
LINKEDIN_DEBUG_ARTIFACTS = _get_bool("LINKEDIN_DEBUG_ARTIFACTS", True)
LINKEDIN_APPLY_TIMEOUT_SEC = _get_int("LINKEDIN_APPLY_TIMEOUT_SEC", 180)
LINKEDIN_DISCOVERY_MAX_PAGES = _get_int("LINKEDIN_DISCOVERY_MAX_PAGES", 5)
LINKEDIN_DISCOVERY_MAX_JOBS_PER_SEARCH = _get_int("LINKEDIN_DISCOVERY_MAX_JOBS_PER_SEARCH", 150)

# Scope policy
APPLY_LOCAL_FIRST = _get_bool("APPLY_LOCAL_FIRST", True)
APPLY_GLOBAL_REMOTE = _get_bool("APPLY_GLOBAL_REMOTE", True)
APPLY_OTHER_REGIONS = _get_bool("APPLY_OTHER_REGIONS", False)
APPLY_ATTEMPT_TIMEOUT_SEC = _get_int("APPLY_ATTEMPT_TIMEOUT_SEC", 120)

# Filters (preserve original case so "IT" can be matched case-sensitively)
JOB_KEYWORDS = [k.strip() for k in _get("JOB_KEYWORDS", "").split(",") if k.strip()]
JOB_EXCLUDE_KEYWORDS = [k.strip() for k in _get("JOB_EXCLUDE_KEYWORDS", "").split(",") if k.strip()]
MAX_JOB_AGE_DAYS = _get_int("MAX_JOB_AGE_DAYS", 30)

# Optional: 2Captcha API key
CAPTCHA_API_KEY = _get("CAPTCHA_API_KEY")

# Optional: run only these adapters
ADAPTERS_FILTER = [n.strip().lower() for n in _get("ADAPTERS", "").split(",") if n.strip()]

# Paths
DATA_DIR = _ROOT / "data"
LOGS_DIR = _ROOT / "logs"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
