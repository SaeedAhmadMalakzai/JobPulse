"""Send application emails (SMTP) and check inbox (IMAP) for responses."""
import email
import imaplib
import smtplib
import time
from datetime import datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional

from src.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM_NAME,
    IMAP_HOST,
    IMAP_PORT,
    IMAP_USER,
    IMAP_PASSWORD,
)
from src.log import get_logger

LOG = get_logger("email")


def _save_to_sent_folder(msg: MIMEMultipart) -> None:
    """Append a copy of the sent message to the account's Sent folder via IMAP."""
    if not IMAP_USER or not IMAP_PASSWORD:
        return
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=10) as imap:
            imap.login(IMAP_USER, IMAP_PASSWORD)
            raw = msg.as_string()
            if isinstance(raw, str):
                raw = raw.encode("utf-8")
            date_str = imaplib.Time2Internaldate(time.time())
            for sent_name in ("Sent", "Sent Messages", "Sent Mail", "[Gmail]/Sent Mail", "INBOX.Sent"):
                try:
                    imap.append(sent_name, "\\Seen", date_str, raw)
                    return
                except imaplib.IMAP4.error:
                    continue
    except Exception as e:
        LOG.warning("  [IMAP] Could not save to Sent folder: %s: %s", type(e).__name__, e)


def send_application_email(
    to_email: str,
    subject: str,
    body: str,
    cv_path: Optional[Path] = None,
    cover_letter_path: Optional[Path] = None,
) -> bool:
    """Send an application email with optional CV and cover letter attachments."""
    if not SMTP_USER or not SMTP_PASSWORD:
        return False
    msg = MIMEMultipart()
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_USER}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    for path in (cv_path, cover_letter_path):
        if path and Path(path).exists():
            p = Path(path)
            with open(p, "rb") as f:
                data = f.read()
            if p.suffix.lower() == ".pdf":
                part = MIMEApplication(data, _subtype="pdf")
            elif p.suffix.lower() == ".txt":
                part = MIMEText(data.decode("utf-8", errors="replace"), "plain", "utf-8")
            else:
                part = MIMEApplication(data, _subtype="octet-stream")
            part.add_header("Content-Disposition", "attachment", filename=p.name)
            msg.attach(part)

    last_error = None
    for attempt in range(3):
        try:
            if SMTP_PORT == 465:
                with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
                    smtp.login(SMTP_USER, SMTP_PASSWORD)
                    smtp.sendmail(SMTP_USER, to_email, msg.as_string())
            else:
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
                    smtp.starttls()
                    smtp.login(SMTP_USER, SMTP_PASSWORD)
                    smtp.sendmail(SMTP_USER, to_email, msg.as_string())

            # Save a copy to your Sent folder (Riseup/others don't do this when sending via SMTP from a script)
            _save_to_sent_folder(msg)
            return True
        except Exception as e:
            last_error = e
            err = str(e).lower()
            # Don't retry auth failures
            if "authentication" in err or "535" in err or "badcredentials" in err:
                LOG.warning("  [SMTP] Send failed: Gmail rejected login. Use an App Password: https://support.google.com/accounts/answer/185833")
                return False
            if attempt < 2:
                time.sleep(2)
    if last_error:
        LOG.warning("  [SMTP] Send failed after 3 attempts: %s: %s", type(last_error).__name__, last_error)
    return False


def check_inbox_for_responses(since_days: int = 7) -> List[dict]:
    """
    Fetch recent emails from inbox. Returns list of dicts with subject, from, date, snippet.
    Caller can filter for interview/acceptance keywords and trigger alerts.
    """
    if not IMAP_USER or not IMAP_PASSWORD:
        return []
    results = []
    try:
        with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
            imap.login(IMAP_USER, IMAP_PASSWORD)
            imap.select("INBOX")
            # Server-side date filter: only messages newer than since_days. IMAP SINCE
            # expects "DD-Mon-YYYY" (e.g. 02-Jun-2026).
            since_str = (datetime.now() - timedelta(days=max(1, since_days))).strftime("%d-%b-%Y")
            typ, msg_ids = imap.search(None, "SINCE", since_str)
            if typ != "OK" or not msg_ids or not msg_ids[0]:
                # Fall back to recent ALL if SINCE is unsupported/empty.
                typ, msg_ids = imap.search(None, "ALL")
            id_list = msg_ids[0].split() if (msg_ids and msg_ids[0]) else []
            # Cap fetch to most recent 200 to bound work on large mailboxes.
            for uid in id_list[-200:]:
                try:
                    _, data = imap.fetch(uid, "(RFC822)")
                    raw = data[0][1]
                    msg = email.message_from_bytes(raw)
                    subject = msg.get("Subject", "")
                    from_ = msg.get("From", "")
                    date = msg.get("Date", "")
                    # Stable id for de-duplicating alerts across runs.
                    msg_id = (msg.get("Message-ID") or msg.get("Message-Id") or "").strip()
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True)
                                if body:
                                    body = body.decode("utf-8", errors="replace")[:500]
                                break
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode("utf-8", errors="replace")[:500]
                    results.append({
                        "id": msg_id or f"{from_}|{subject}|{date}",
                        "subject": subject,
                        "from": from_,
                        "date": date,
                        "snippet": body or "(no body)",
                    })
                except Exception as e:
                    LOG.warning("  [IMAP] Skipped a message (fetch/parse error): %s", type(e).__name__)
                    continue
    except Exception as e:
        LOG.warning("  [IMAP] Inbox check failed: %s: %s", type(e).__name__, e)
    return results
