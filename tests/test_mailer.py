"""Tests for mailer module."""
import pytest
from unittest.mock import patch, MagicMock, call
from datetime import date

from mailer import _names_summary, send_email, send_birthday_emails, send_anniversary_emails


class TestNamesSummary:
    def test_empty_returns_fallback(self):
        assert _names_summary([]) == "team members"

    def test_single_name(self):
        assert _names_summary(["Alice"]) == "Alice"

    def test_two_names(self):
        assert _names_summary(["Alice", "Bob"]) == "Alice & Bob"

    def test_three_names(self):
        result = _names_summary(["Alice", "Bob", "Carol"])
        assert result == "Alice, Bob & 1 others"

    def test_five_names(self):
        result = _names_summary(["A", "B", "C", "D", "E"])
        assert result == "A, B & 3 others"


class TestSendEmail:
    def _make_smtp(self):
        smtp = MagicMock()
        smtp.__enter__ = MagicMock(return_value=smtp)
        smtp.__exit__ = MagicMock(return_value=False)
        return smtp

    def test_sends_to_correct_recipients(self):
        smtp = self._make_smtp()
        with patch("mailer.smtplib.SMTP", return_value=smtp):
            send_email(
                sender="sender@example.com",
                password="pass",
                to=["a@example.com"],
                cc=["b@example.com"],
                subject="Test",
                body="Hello",
                attachments=[],
            )
        smtp.sendmail.assert_called_once()
        _, recipients, _ = smtp.sendmail.call_args[0]
        assert "a@example.com" in recipients
        assert "b@example.com" in recipients

    def test_retries_on_transient_failure(self):
        smtp = self._make_smtp()
        import smtplib
        smtp.sendmail.side_effect = [smtplib.SMTPException("transient"), None]
        with patch("mailer.smtplib.SMTP", return_value=smtp):
            with patch("mailer.time.sleep"):  # speed up test
                send_email(
                    sender="sender@example.com",
                    password="pass",
                    to=["a@example.com"],
                    cc=[],
                    subject="Test",
                    body="Hello",
                    attachments=[],
                )
        assert smtp.sendmail.call_count == 2

    def test_raises_after_max_retries(self):
        smtp = self._make_smtp()
        import smtplib
        smtp.sendmail.side_effect = smtplib.SMTPException("always fails")
        with patch("mailer.smtplib.SMTP", return_value=smtp):
            with patch("mailer.time.sleep"):
                with pytest.raises(smtplib.SMTPException):
                    send_email(
                        sender="sender@example.com",
                        password="pass",
                        to=["a@example.com"],
                        cc=[],
                        subject="Test",
                        body="Hello",
                        attachments=[],
                    )


class TestSendBirthdayEmails:
    def test_skips_when_no_posters(self):
        with patch("mailer.send_email") as mock_send:
            send_birthday_emails([], {"to": ["a@b.com"], "cc": []}, "s", "p", date(2024, 3, 23))
        mock_send.assert_not_called()

    def test_skips_when_no_to_recipients(self):
        with patch("mailer.send_email") as mock_send:
            send_birthday_emails(
                [("poster.png", b"data")], {"to": [], "cc": []}, "s", "p", date(2024, 3, 23)
            )
        mock_send.assert_not_called()

    def test_subject_contains_employee_name(self):
        with patch("mailer.send_email") as mock_send:
            send_birthday_emails(
                [("poster.png", b"data")],
                {"to": ["mgr@co.com"], "cc": []},
                "sender@co.com",
                "pass",
                date(2024, 3, 23),
                employee_names=["Priya Sharma"],
            )
        subject = mock_send.call_args[1]["subject"] if mock_send.call_args[1] else mock_send.call_args[0][4]
        assert "Priya Sharma" in subject


class TestSendAnniversaryEmails:
    def test_skips_when_no_posters(self):
        with patch("mailer.send_email") as mock_send:
            send_anniversary_emails([], {"to": ["a@b.com"], "cc": []}, "s", "p", date(2024, 3, 23))
        mock_send.assert_not_called()
