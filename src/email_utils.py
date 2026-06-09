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


SMTP_TIMEOUT = 25  # seconds — bound connect/handshake so a blocked port fails fast


def _is_auth_error(err: str) -> bool:
    e = err.lower()
    return "authentication" in e or "535" in e or "badcredentials" in e or "auth" in e and "login" in e


def _deliver(host: str, port: int, user: str, password: str, to_email: str, msg: MIMEMultipart) -> None:
    """Send via one (host, port). Port 465 uses implicit SSL; others use STARTTLS."""
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=SMTP_TIMEOUT) as smtp:
            smtp.login(user, password)
            smtp.sendmail(user, to_email, msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(user, to_email, msg.as_string())


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

    # Try the configured port first; if it's the STARTTLS submission port and the
    # connection fails (e.g. 587 blocked by the network), fall back to implicit SSL
    # on 465, which many networks/ISPs leave open.
    endpoints = [(SMTP_HOST, SMTP_PORT)]
    if SMTP_PORT != 465:
        endpoints.append((SMTP_HOST, 465))

    last_error = None
    for host, port in endpoints:
        for attempt in range(2):
            try:
                _deliver(host, port, SMTP_USER, SMTP_PASSWORD, to_email, msg)
                _save_to_sent_folder(msg)
                if port != SMTP_PORT:
                    LOG.info("  [SMTP] Sent via fallback port %s (configured %s was unreachable).", port, SMTP_PORT)
                return True
            except Exception as e:
                last_error = e
                if _is_auth_error(str(e)):
                    LOG.warning("  [SMTP] Send failed: login rejected. For Gmail use a 16-char App Password: https://support.google.com/accounts/answer/185833")
                    return False  # auth won't be fixed by retry or fallback
                if attempt == 0:
                    time.sleep(2)
    if last_error:
        LOG.warning("  [SMTP] Send failed (tried %s): %s: %s",
                    ", ".join(f"{h}:{p}" for h, p in endpoints), type(last_error).__name__, last_error)
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
