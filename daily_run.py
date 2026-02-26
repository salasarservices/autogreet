"""Daily runner: generate today's posters and send emails.

Usage:
    python daily_run.py

Secrets are read from .streamlit/secrets.toml (via the toml module) so the
script can be run independently of Streamlit.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path


def _load_secrets() -> dict:
    secrets_path = Path(".streamlit/secrets.toml")
    if not secrets_path.exists():
        return {}
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            # Minimal TOML key=value parser (single level only).
            # For full TOML support on Python <3.11, install `tomli`:
            #   pip install tomli
            import re
            secrets: dict = {}
            for line in secrets_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = re.match(r'^(\w+)\s*=\s*"([^"]*)"', line)
                if m:
                    secrets[m.group(1)] = m.group(2)
            return secrets
    with secrets_path.open("rb") as f:
        return tomllib.load(f)


def main() -> None:
    # Load config
    with open("template_config.json") as f:
        cfg = json.load(f)

    secrets = _load_secrets()
    today = date.today()

    # Import here to avoid circular deps
    from data_sources import get_employees, map_employee
    from poster_engine import generate_birthday_poster, generate_anniversary_poster, poster_to_bytes
    from mailer import send_birthday_emails, send_anniversary_emails

    raw_employees = get_employees(cfg, secrets)
    employees = [map_employee(r, cfg.get("field_mapping", {})) for r in raw_employees]

    birthday_posters: list[tuple[str, bytes]] = []
    anniversary_posters: list[tuple[str, bytes]] = []

    os.makedirs("storage/output", exist_ok=True)

    for emp in employees:
        safe_name = (emp["name"] or "employee").replace(" ", "_")

        # Birthday
        dob = emp.get("dob")
        if dob and dob.month == today.month and dob.day == today.day:
            try:
                img = generate_birthday_poster(emp, cfg, secrets, today)
                img_bytes = poster_to_bytes(img)
                filename = f"birthday_{safe_name}_{today.isoformat()}.png"
                out_path = Path("storage/output") / filename
                out_path.write_bytes(img_bytes)
                birthday_posters.append((filename, img_bytes))
                print(f"[birthday] Generated poster for {emp['name']}")
            except Exception as exc:  # noqa: BLE001
                print(f"[birthday] ERROR for {emp['name']}: {exc}", file=sys.stderr)

        # Anniversary
        doj = emp.get("doj")
        if doj and doj.month == today.month and doj.day == today.day:
            try:
                img = generate_anniversary_poster(emp, cfg, secrets, today)
                img_bytes = poster_to_bytes(img)
                filename = f"anniversary_{safe_name}_{today.isoformat()}.png"
                out_path = Path("storage/output") / filename
                out_path.write_bytes(img_bytes)
                anniversary_posters.append((filename, img_bytes))
                print(f"[anniversary] Generated poster for {emp['name']}")
            except Exception as exc:  # noqa: BLE001
                print(f"[anniversary] ERROR for {emp['name']}: {exc}", file=sys.stderr)

    # Send emails
    smtp_sender = secrets.get("smtp_sender", "")
    smtp_password = secrets.get("smtp_password", "")

    send_birthday_emails(
        birthday_posters,
        cfg.get("recipients", {}).get("birthday", {}),
        smtp_sender,
        smtp_password,
        today,
    )
    send_anniversary_emails(
        anniversary_posters,
        cfg.get("recipients", {}).get("anniversary", {}),
        smtp_sender,
        smtp_password,
        today,
    )

    print(
        f"Done. {len(birthday_posters)} birthday poster(s), "
        f"{len(anniversary_posters)} anniversary poster(s)."
    )


if __name__ == "__main__":
    main()
