"""Shared pytest fixtures for AutoGreet tests."""
import json
import pathlib
import pytest
from datetime import date


@pytest.fixture()
def tmp_sent_log(tmp_path, monkeypatch):
    """Redirect the sent-log to a temp file for each test."""
    import daily_run
    log = tmp_path / "sent_log.jsonl"
    monkeypatch.setattr(daily_run, "SENT_LOG", log)
    return log


@pytest.fixture()
def minimal_cfg(tmp_path):
    """A minimal template_config dict with safe defaults."""
    return {
        "data_source": {
            "mode": "sample_json",
            "sample_url": "",
            "auth_header_name": "",
            "auth_header_value": "",
            "zinghr": {"base_url": "", "client_id": ""},
        },
        "field_mapping": {
            "name": "EmployeeName",
            "designation": "Designation",
            "vertical": "Vertical",
            "department": "Department",
            "location": "Location",
            "dob": "DateOfBirth",
            "doj": "DateOfJoining",
            "photo_url": "EmployeeImage",
        },
        "fonts": {"regular": "", "bold": "", "year": ""},
        "birthday": {
            "template": "assets/templates/birthday.png",
            "text_colour": "#FFFFFF",
            "photo_box": {"x": 40, "y": 120, "w": 300, "h": 400},
            "text_block": {
                "x": 360, "y": 200,
                "line_spacing": 48,
                "font_size_name": 38,
                "font_size_detail": 26,
            },
        },
        "anniversary": {
            "template": "assets/templates/anniversary.png",
            "text_colour": "#FFFFFF",
            "photo_box": {"x": 40, "y": 100, "w": 280, "h": 320},
            "text_block": {
                "x": 360, "y": 200,
                "line_spacing": 48,
                "font_size_name": 38,
                "font_size_detail": 26,
            },
            "year_label": {"x": 80, "y": 80, "font_size": 64},
        },
        "recipients": {
            "birthday": {"to": [], "cc": []},
            "anniversary": {"to": [], "cc": []},
        },
    }


@pytest.fixture()
def sample_employee():
    """A fully-populated employee dict as returned by map_employee."""
    return {
        "name": "Priya Sharma",
        "designation": "Senior Engineer",
        "vertical": "Technology",
        "department": "Platform",
        "location": "Mumbai",
        "dob": date(1992, 3, 23),
        "doj": date(2019, 3, 23),
        "photo_url": "",
        "_raw": {},
    }
