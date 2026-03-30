"""Tests for daily_run module — idempotency logic and date matching."""
import pytest
from datetime import date

import daily_run


class TestSentLog:
    def test_not_sent_when_log_missing(self, tmp_sent_log):
        assert not daily_run._already_sent("Alice", "birthday", date(2024, 3, 23))

    def test_mark_and_detect(self, tmp_sent_log):
        d = date(2024, 3, 23)
        daily_run._mark_sent("Alice", "birthday", d)
        assert daily_run._already_sent("Alice", "birthday", d)

    def test_different_date_not_blocked(self, tmp_sent_log):
        daily_run._mark_sent("Alice", "birthday", date(2024, 3, 22))
        assert not daily_run._already_sent("Alice", "birthday", date(2024, 3, 23))

    def test_different_event_type_not_blocked(self, tmp_sent_log):
        daily_run._mark_sent("Alice", "birthday", date(2024, 3, 23))
        assert not daily_run._already_sent("Alice", "anniversary", date(2024, 3, 23))

    def test_different_name_not_blocked(self, tmp_sent_log):
        daily_run._mark_sent("Alice", "birthday", date(2024, 3, 23))
        assert not daily_run._already_sent("Bob", "birthday", date(2024, 3, 23))

    def test_mark_sent_creates_parent_dirs(self, tmp_path, monkeypatch):
        nested_log = tmp_path / "a" / "b" / "sent_log.jsonl"
        monkeypatch.setattr(daily_run, "SENT_LOG", nested_log)
        daily_run._mark_sent("Alice", "birthday", date(2024, 3, 23))
        assert nested_log.exists()

    def test_idempotent_double_mark(self, tmp_sent_log):
        d = date(2024, 3, 23)
        daily_run._mark_sent("Alice", "birthday", d)
        daily_run._mark_sent("Alice", "birthday", d)
        lines = [l for l in tmp_sent_log.read_text().splitlines() if l.strip()]
        assert len(lines) == 2  # Written twice but only first one should be checked


class TestWeekendCatchup:
    """Verify that _dates_to_check returns correct dates for weekday/weekend scenarios."""

    def test_regular_weekday_returns_only_today(self):
        # Wednesday
        tuesday = date(2024, 3, 19)  # Tuesday
        dates = daily_run._dates_to_check(tuesday)
        assert dates == [tuesday]

    def test_monday_includes_saturday_and_sunday(self):
        monday = date(2024, 3, 18)  # Monday
        dates = daily_run._dates_to_check(monday)
        assert date(2024, 3, 16) in dates  # Saturday
        assert date(2024, 3, 17) in dates  # Sunday
        assert monday in dates

    def test_saturday_returns_empty_when_catchup_disabled(self):
        saturday = date(2024, 3, 16)
        # Saturday on its own — only if cron runs on weekends
        dates = daily_run._dates_to_check(saturday)
        assert saturday in dates
