"""Tests for data_sources module."""
import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from data_sources import parse_date, map_employee, fetch_sample_json, invalidate_cache


# ---------------------------------------------------------------------------
# parse_date
# ---------------------------------------------------------------------------

class TestParseDate:
    def test_dd_mm_yyyy(self):
        assert parse_date("23-03-1992") == date(1992, 3, 23)

    def test_yyyy_mm_dd(self):
        assert parse_date("1992-03-23") == date(1992, 3, 23)

    def test_dd_slash_mm_slash_yyyy(self):
        assert parse_date("23/03/1992") == date(1992, 3, 23)

    def test_mm_slash_dd_slash_yyyy(self):
        # Unambiguous month-first date (day > 12 forces correct parse)
        assert parse_date("03/23/1992") == date(1992, 3, 23)

    def test_empty_string_returns_none(self):
        assert parse_date("") is None

    def test_none_input_returns_none(self):
        assert parse_date(None) is None

    def test_garbage_returns_none(self):
        assert parse_date("not-a-date") is None

    def test_strips_whitespace(self):
        assert parse_date("  23-03-1992  ") == date(1992, 3, 23)


# ---------------------------------------------------------------------------
# map_employee
# ---------------------------------------------------------------------------

class TestMapEmployee:
    def test_maps_fields_correctly(self, minimal_cfg):
        raw = {
            "EmployeeName": "Priya Sharma",
            "Designation": "Engineer",
            "Vertical": "Tech",
            "Department": "Platform",
            "Location": "Mumbai",
            "DateOfBirth": "23-03-1992",
            "DateOfJoining": "01-06-2019",
            "EmployeeImage": "https://example.com/photo.jpg",
        }
        emp = map_employee(raw, minimal_cfg["field_mapping"])
        assert emp["name"] == "Priya Sharma"
        assert emp["designation"] == "Engineer"
        assert emp["dob"] == date(1992, 3, 23)
        assert emp["doj"] == date(2019, 6, 1)
        assert emp["photo_url"] == "https://example.com/photo.jpg"

    def test_custom_field_mapping(self):
        raw = {"EmpName": "Alice", "DOB": "01-01-1990"}
        mapping = {"name": "EmpName", "dob": "DOB"}
        emp = map_employee(raw, mapping)
        assert emp["name"] == "Alice"
        assert emp["dob"] == date(1990, 1, 1)

    def test_missing_fields_return_empty_string_or_none(self, minimal_cfg):
        emp = map_employee({}, minimal_cfg["field_mapping"])
        assert emp["name"] == ""
        assert emp["dob"] is None
        assert emp["doj"] is None

    def test_raw_passthrough(self, minimal_cfg):
        raw = {"EmployeeName": "Bob", "extra_field": "extra_value"}
        emp = map_employee(raw, minimal_cfg["field_mapping"])
        assert emp["_raw"] == raw


# ---------------------------------------------------------------------------
# fetch_sample_json
# ---------------------------------------------------------------------------

class TestFetchSampleJson:
    def test_fetches_list(self):
        invalidate_cache()
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1}, {"id": 2}]
        mock_resp.raise_for_status = MagicMock()
        with patch("data_sources.requests.get", return_value=mock_resp) as mock_get:
            result = fetch_sample_json("https://example.com/employees")
        assert result == [{"id": 1}, {"id": 2}]
        mock_get.assert_called_once()

    def test_wraps_single_dict_in_list(self):
        invalidate_cache()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": 1, "name": "Solo"}
        mock_resp.raise_for_status = MagicMock()
        with patch("data_sources.requests.get", return_value=mock_resp):
            result = fetch_sample_json("https://example.com/single")
        assert result == [{"id": 1, "name": "Solo"}]

    def test_cache_prevents_second_request(self):
        invalidate_cache()
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"id": 1}]
        mock_resp.raise_for_status = MagicMock()
        with patch("data_sources.requests.get", return_value=mock_resp) as mock_get:
            fetch_sample_json("https://example.com/cached")
            fetch_sample_json("https://example.com/cached")
        assert mock_get.call_count == 1

    def test_sends_auth_header(self):
        invalidate_cache()
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        with patch("data_sources.requests.get", return_value=mock_resp) as mock_get:
            fetch_sample_json("https://example.com/auth", auth_header={"Authorization": "Bearer token"})
        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer token"
