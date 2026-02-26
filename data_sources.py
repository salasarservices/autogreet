"""Data sources module: sample JSON URL and ZingHR placeholder."""
from __future__ import annotations

import json
import requests
from datetime import datetime
from typing import Any


DATE_FORMAT = "%d-%m-%Y"


def parse_date(date_str: str) -> datetime | None:
    """Parse a date string in DD-MM-YYYY format, return None on failure."""
    if not date_str:
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def fetch_sample_json(url: str) -> list[dict[str, Any]]:
    """Fetch employee data from a sample JSON URL.

    The endpoint may return a single object or a list of objects.
    """
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError(f"Unexpected JSON structure: {type(data)}")


def fetch_zinghr(config: dict) -> list[dict[str, Any]]:
    """Placeholder ZingHR data fetch.

    Replace this function body once ZingHR API credentials are available.
    config keys expected:
      - base_url
      - client_id
      - client_secret  (from secrets)
    """
    raise NotImplementedError(
        "ZingHR integration is not yet configured. "
        "Update fetch_zinghr() in data_sources.py once API details are available."
    )


def get_employees(cfg: dict, secrets: dict | None = None) -> list[dict[str, Any]]:
    """Return employee list based on the active data source in cfg."""
    mode = cfg.get("data_source", {}).get("mode", "sample_json")

    if mode == "sample_json":
        url = cfg["data_source"].get("sample_url", "")
        if not url:
            raise ValueError("sample_url is not configured in template_config.json.")
        return fetch_sample_json(url)

    if mode == "zinghr":
        zinghr_cfg = dict(cfg["data_source"].get("zinghr", {}))
        if secrets:
            secret_key = zinghr_cfg.get("client_secret_key", "zinghr_client_secret")
            zinghr_cfg["client_secret"] = secrets.get(secret_key, "")
        return fetch_zinghr(zinghr_cfg)

    raise ValueError(f"Unknown data source mode: {mode!r}")


def map_employee(raw: dict, field_mapping: dict) -> dict:
    """Normalise a raw employee record using field_mapping."""
    def _str(key: str, default: str) -> str:
        val = raw.get(field_mapping.get(key, default))
        return val if isinstance(val, str) else (str(val) if val is not None else "")

    return {
        "name": _str("name", "EmployeeName"),
        "designation": _str("designation", "Designation"),
        "vertical": _str("vertical", "Vertical"),
        "department": _str("department", "Department"),
        "location": _str("location", "Location"),
        "dob": parse_date(_str("dob", "DateOfBirth")),
        "doj": parse_date(_str("doj", "DateOfJoining")),
        "photo_url": _str("photo_url", "EmployeeImage"),
        "_raw": raw,
    }
