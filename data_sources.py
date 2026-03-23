"""Data sources module: sample JSON URL and ZingHR placeholder."""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, date
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

DATE_FORMATS = ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d")

# Simple in-process cache: {cache_key: (fetched_at_ts, data)}
_cache: dict[str, tuple[float, list[dict]]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def parse_date(date_str: str) -> date | None:
    """Parse a date string in multiple formats; return None on failure."""
    if not date_str:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    logger.warning("Could not parse date string: %r", date_str)
    return None


def fetch_sample_json(url: str, auth_header: dict | None = None) -> list[dict[str, Any]]:
    """Fetch employee data from a JSON URL (object or list)."""
    cache_key = url
    now = time.monotonic()
    if cache_key in _cache:
        fetched_at, cached_data = _cache[cache_key]
        if now - fetched_at < CACHE_TTL_SECONDS:
            logger.debug("Returning cached employee data for %s", url)
            return cached_data

    headers = dict(auth_header) if auth_header else {}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if isinstance(data, dict):
        result = [data]
    elif isinstance(data, list):
        result = data
    else:
        raise ValueError(f"Unexpected JSON structure: {type(data)}")

    _cache[cache_key] = (now, result)
    logger.info("Fetched %d employee(s) from %s", len(result), url)
    return result


def invalidate_cache() -> None:
    """Clear the in-process employee cache."""
    _cache.clear()


def fetch_zinghr(config: dict) -> list[dict[str, Any]]:
    """Placeholder ZingHR fetch — implement once API credentials are available."""
    raise NotImplementedError(
        "ZingHR integration is not yet implemented. "
        "Update fetch_zinghr() in data_sources.py once API details are available."
    )


def get_employees(cfg: dict, secrets: dict | None = None) -> list[dict[str, Any]]:
    """Return employee list based on the active data source in cfg."""
    mode = cfg.get("data_source", {}).get("mode", "sample_json")

    if mode == "sample_json":
        url = cfg["data_source"].get("sample_url", "")
        if not url:
            raise ValueError("sample_url is not configured. Set it in the Data Source page.")
        auth_header_name = cfg["data_source"].get("auth_header_name", "").strip()
        auth_header_value = cfg["data_source"].get("auth_header_value", "").strip()
        auth_header = {auth_header_name: auth_header_value} if auth_header_name else None
        return fetch_sample_json(url, auth_header=auth_header)

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
