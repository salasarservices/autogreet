"""Email sending via SMTP (Office365)."""
from __future__ import annotations

import logging
import smtplib
import time
from datetime import date
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.office365.com"
SMTP_PORT = 587

# Retry settings for transient SMTP failures
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2  # seconds; doubles on each attempt


def _build_message(
    sender: str,
    to: list[str],
    cc: list[str],
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes]],
) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    for filename, data in attachments:
        part = MIMEApplication(data, Name=filename)
        part["Content-Disposition"] = f'attachment; filename="{filename}"'
        msg.attach(part)
    return msg


def send_email(
    sender: str,
    password: str,
    to: list[str],
    cc: list[str],
    subject: str,
    body: str,
    attachments: list[tuple[str, bytes]],
) -> None:
    """Send an email with optional attachments via Office365 SMTP.

    Retries up to _MAX_RETRIES times with exponential backoff on transient
    SMTP errors. Raises the last exception if all attempts fail.
    """
    recipients = to + cc
    msg = _build_message(sender, to, cc, subject, body, attachments)
    last_exc: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, recipients, msg.as_string())
            logger.info("Email sent — subject: %r, recipients: %d", subject, len(recipients))
            return
        except smtplib.SMTPException as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "SMTP attempt %d/%d failed (%s) — retrying in %ds",
                    attempt, _MAX_RETRIES, exc, delay,
                )
                time.sleep(delay)
            else:
                logger.error("SMTP failed after %d attempts: %s", _MAX_RETRIES, exc)

    raise last_exc  # type: ignore[misc]


def _names_summary(names: list[str]) -> str:
    """'Alice', 'Alice & Bob', 'Alice, Bob & 3 others'."""
    if not names:
        return "team members"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} & {names[1]}"
    return f"{names[0]}, {names[1]} & {len(names) - 2} others"


def send_birthday_emails(
    posters: list[tuple[str, bytes]],
    recipients: dict,
    sender: str,
    password: str,
    today: date | None = None,
    employee_names: list[str] | None = None,
) -> None:
    """Send birthday poster email — personalised subject with employee names."""
    if not posters:
        return
    if today is None:
        today = date.today()

    to = recipients.get("to", [])
    cc = recipients.get("cc", [])
    if not to:
        logger.warning("Birthday email skipped — no TO recipients configured.")
        return

    names = employee_names or []
    summary = _names_summary(names)
    subject = f"Happy Birthday – {summary} | {today.strftime('%d %B %Y')}"
    body = (
        f"Hi,\n\n"
        f"Please find attached the birthday greeting poster(s) for today "
        f"({today.strftime('%d %B %Y')}).\n\n"
    )
    if names:
        body += "Celebrating today:\n" + "\n".join(f"  • {n}" for n in names) + "\n\n"
    body += "Warm regards,\nAutoGreet"

    send_email(sender, password, to, cc, subject, body, posters)


def send_anniversary_emails(
    posters: list[tuple[str, bytes]],
    recipients: dict,
    sender: str,
    password: str,
    today: date | None = None,
    employee_names: list[str] | None = None,
) -> None:
    """Send anniversary poster email — personalised subject with employee names."""
    if not posters:
        return
    if today is None:
        today = date.today()

    to = recipients.get("to", [])
    cc = recipients.get("cc", [])
    if not to:
        logger.warning("Anniversary email skipped — no TO recipients configured.")
        return

    names = employee_names or []
    summary = _names_summary(names)
    subject = f"Work Anniversary – {summary} | {today.strftime('%d %B %Y')}"
    body = (
        f"Hi,\n\n"
        f"Please find attached the work anniversary greeting poster(s) for today "
        f"({today.strftime('%d %B %Y')}).\n\n"
    )
    if names:
        body += "Celebrating today:\n" + "\n".join(f"  • {n}" for n in names) + "\n\n"
    body += "Warm regards,\nAutoGreet"

    send_email(sender, password, to, cc, subject, body, posters)
