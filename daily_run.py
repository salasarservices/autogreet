"""Daily runner: generate today's posters and send emails.

Usage:
    python daily_run.py [--date YYYY-MM-DD] [--dry-run]

Options:
    --date      Override today's date (for testing/backfill)
    --dry-run   Generate posters but do not send emails

Secrets are read from .streamlit/secrets.toml.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Idempotency guard
# ---------------------------------------------------------------------------

SENT_LOG = Path("storage/sent_log.jsonl")


def _already_sent(employee_name: str, event_type: str, run_date: date) -> bool:
    """Return True if we already sent this (name, event_type, date) combo today."""
    key = f"{run_date.isoformat()}|{event_type}|{employee_name}"
    if not SENT_LOG.exists():
        return False
    for line in SENT_LOG.read_text().splitlines():
        if line.strip() == key:
            return True
    return False


def _mark_sent(employee_name: str, event_type: str, run_date: date) -> None:
    SENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    key = f"{run_date.isoformat()}|{event_type}|{employee_name}"
    with SENT_LOG.open("a") as f:
        f.write(key + "\n")


# ---------------------------------------------------------------------------
# Secrets loader
# ---------------------------------------------------------------------------

def _load_secrets() -> dict:
    secrets_path = Path(".streamlit/secrets.toml")
    if not secrets_path.exists():
        logger.warning("secrets.toml not found at %s", secrets_path)
        return {}
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="AutoGreet daily runner")
    parser.add_argument("--date", help="Override date as YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="Generate posters but skip sending")
    args = parser.parse_args()

    if args.date:
        today = date.fromisoformat(args.date)
    else:
        today = date.today()

    logger.info("=== AutoGreet daily run — %s%s ===", today.isoformat(),
                " [DRY RUN]" if args.dry_run else "")

    with open("template_config.json") as f:
        cfg = json.load(f)

    secrets = _load_secrets()

    from data_sources import get_employees, map_employee
    from poster_engine import generate_birthday_poster, generate_anniversary_poster, poster_to_bytes
    from mailer import send_birthday_emails, send_anniversary_emails

    logger.info("Fetching employees...")
    raw_employees = get_employees(cfg, secrets)
    employees = [map_employee(r, cfg.get("field_mapping", {})) for r in raw_employees]
    logger.info("Loaded %d employee(s)", len(employees))

    os.makedirs("storage/output", exist_ok=True)

    birthday_posters: list[tuple[str, bytes]] = []
    birthday_names: list[str] = []
    anniversary_posters: list[tuple[str, bytes]] = []
    anniversary_names: list[str] = []

    for emp in employees:
        name = emp.get("name") or "unknown"
        safe_name = name.replace(" ", "_")

        # --- Birthday ---
        dob = emp.get("dob")
        if dob and dob.month == today.month and dob.day == today.day:
            if _already_sent(name, "birthday", today):
                logger.info("[birthday] Skipping %s — already sent today", name)
            else:
                try:
                    img = generate_birthday_poster(emp, cfg, secrets, today)
                    img_bytes = poster_to_bytes(img)
                    filename = f"birthday_{safe_name}_{today.isoformat()}.png"
                    out_path = Path("storage/output") / filename
                    out_path.write_bytes(img_bytes)
                    birthday_posters.append((filename, img_bytes))
                    birthday_names.append(name)
                    logger.info("[birthday] Generated poster for %s", name)
                except Exception as exc:
                    logger.error("[birthday] Poster failed for %s: %s", name, exc)

        # --- Anniversary ---
        doj = emp.get("doj")
        if doj and doj.month == today.month and doj.day == today.day:
            if _already_sent(name, "anniversary", today):
                logger.info("[anniversary] Skipping %s — already sent today", name)
            else:
                try:
                    img = generate_anniversary_poster(emp, cfg, secrets, today)
                    img_bytes = poster_to_bytes(img)
                    filename = f"anniversary_{safe_name}_{today.isoformat()}.png"
                    out_path = Path("storage/output") / filename
                    out_path.write_bytes(img_bytes)
                    anniversary_posters.append((filename, img_bytes))
                    anniversary_names.append(name)
                    logger.info("[anniversary] Generated poster for %s", name)
                except Exception as exc:
                    logger.error("[anniversary] Poster failed for %s: %s", name, exc)

    logger.info(
        "Generated: %d birthday poster(s), %d anniversary poster(s)",
        len(birthday_posters), len(anniversary_posters),
    )

    if args.dry_run:
        logger.info("Dry run — skipping email send.")
        return

    smtp_sender = secrets.get("smtp_sender", "")
    smtp_password = secrets.get("smtp_password", "")

    if not smtp_sender or not smtp_password:
        logger.error("SMTP credentials missing — set smtp_sender and smtp_password in secrets.toml")
        sys.exit(1)

    try:
        send_birthday_emails(
            birthday_posters,
            cfg.get("recipients", {}).get("birthday", {}),
            smtp_sender,
            smtp_password,
            today,
            employee_names=birthday_names,
        )
        for name in birthday_names:
            _mark_sent(name, "birthday", today)
    except Exception as exc:
        logger.error("Birthday email send failed: %s", exc)

    try:
        send_anniversary_emails(
            anniversary_posters,
            cfg.get("recipients", {}).get("anniversary", {}),
            smtp_sender,
            smtp_password,
            today,
            employee_names=anniversary_names,
        )
        for name in anniversary_names:
            _mark_sent(name, "anniversary", today)
    except Exception as exc:
        logger.error("Anniversary email send failed: %s", exc)

    logger.info("=== Run complete ===")


if __name__ == "__main__":
    main()
