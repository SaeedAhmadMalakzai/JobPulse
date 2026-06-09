"""Send alert email to user when a possible job response is detected."""
import smtplib
from email.mime.text import MIMEText

from src.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL
from src.alert_store import already_alerted, mark_alerted
from src.log import get_logger

LOG = get_logger("alerts")


RESPONSE_KEYWORDS = [
    "interview", "shortlist", "shortlisted", "invitation", "invite you",
    "congratulations", "accepted", "offer", "next step", "schedule a call",
    "selected", "we are pleased", "pleased to inform",
]


def _might_be_response(subject: str, snippet: str) -> bool:
    text = (subject + " " + snippet).lower()
    return any(kw in text for kw in RESPONSE_KEYWORDS)


def check_and_alert(inbox_items: list) -> int:
    """
    Given list of inbox items (dicts with subject, from, snippet),
    send one alert email to ALERT_EMAIL if any look like job responses.
    Returns number of alerts sent.
    """
    if not ALERT_EMAIL or not SMTP_USER or not SMTP_PASSWORD:
        return 0
    candidates = [m for m in inbox_items if _might_be_response(m.get("subject", ""), m.get("snippet", ""))]
    # De-duplicate: don't re-alert messages we've already notified about on a prior run.
    candidates = [m for m in candidates if not already_alerted(m.get("id", ""))]
    if not candidates:
        return 0
    lines = ["Possible job response(s) detected in your application inbox:\n"]
    for m in candidates[:10]:
        lines.append(f"From: {m.get('from', '')}")
        lines.append(f"Subject: {m.get('subject', '')}")
        lines.append(f"Date: {m.get('date', '')}")
        lines.append(f"Snippet: {m.get('snippet', '')[:300]}...")
        lines.append("---")
    body = "\n".join(lines)
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = "Job bot: Possible response / interview"
    msg["From"] = SMTP_USER
    msg["To"] = ALERT_EMAIL
    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
                smtp.sendmail(SMTP_USER, ALERT_EMAIL, msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
                smtp.starttls()
                smtp.login(SMTP_USER, SMTP_PASSWORD)
                smtp.sendmail(SMTP_USER, ALERT_EMAIL, msg.as_string())
        # Only record as alerted after a successful send, so a failed send retries next run.
        mark_alerted([m.get("id", "") for m in candidates[:10]])
        return 1
    except Exception as e:
        LOG.warning("  [alert] Could not send alert email: %s: %s", type(e).__name__, e)
        return 0
