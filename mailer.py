"""Email sending via SMTP (Office365)."""
from __future__ import annotations

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date
from typing import Sequence


SMTP_HOST = "smtp.office365.com"
SMTP_PORT = 587


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
    """Send an email with optional attachments via Office365 SMTP."""
    recipients = to + cc
    msg = _build_message(sender, to, cc, subject, body, attachments)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())


def send_birthday_emails(
    posters: list[tuple[str, bytes]],
    recipients: dict,
    sender: str,
    password: str,
    today: date | None = None,
) -> None:
    """Send birthday poster email if there are any posters."""
    if not posters:
        return
    if today is None:
        today = date.today()
    to = recipients.get("to", [])
    cc = recipients.get("cc", [])
    if not to:
        return
    subject = f"🎂 Birthday Greetings – {today.strftime('%d %B %Y')}"
    body = "Please find attached the birthday greeting poster(s) for today."
    send_email(sender, password, to, cc, subject, body, posters)


def send_anniversary_emails(
    posters: list[tuple[str, bytes]],
    recipients: dict,
    sender: str,
    password: str,
    today: date | None = None,
) -> None:
    """Send anniversary poster email if there are any posters."""
    if not posters:
        return
    if today is None:
        today = date.today()
    to = recipients.get("to", [])
    cc = recipients.get("cc", [])
    if not to:
        return
    subject = f"🎉 Work Anniversary Greetings – {today.strftime('%d %B %Y')}"
    body = "Please find attached the work anniversary greeting poster(s) for today."
    send_email(sender, password, to, cc, subject, body, posters)
