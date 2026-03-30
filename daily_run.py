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
from datetime import date, timedelta
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
    """Return True if we already sent this (name, event_type, date) combo."""
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
# Weekend catch-up
# ---------------------------------------------------------------------------

def _dates_to_check(today: date) -> list[date]:
    """Return the list of dates to match employees against.

    On Monday, also include the preceding Saturday and Sunday so employees
    with weekend birthdays/anniversaries are never skipped.
    On any other day, returns [today] only.
    """
    # weekday(): Monday == 0
    if today.weekday() == 0:
        return [today - timedelta(days=2), today - timedelta(days=1), today]
    return [today]


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
# Per-employee poster generation (shared between CLI and UI)
# ---------------------------------------------------------------------------

def process_employee_for_date(
    emp: dict,
    target_date: date,
    cfg: dict,
    secrets: dict,
) -> tuple[list[tuple[str, bytes]], list[str], list[tuple[str, bytes]], list[str]]:
    """Generate posters for one employee on one target date.

    Returns (birthday_posters, birthday_names, anniversary_posters, anniversary_names).
    Does NOT send emails — caller batches and sends after iterating all employees.
    """
    from poster_engine import generate_birthday_poster, generate_anniversary_poster, poster_to_bytes

    birthday_posters: list[tuple[str, bytes]] = []
    birthday_names: list[str] = []
    anniversary_posters: list[tuple[str, bytes]] = []
    anniversary_names: list[str] = []

    name = emp.get("name") or "unknown"
    safe_name = name.replace(" ", "_")

    # --- Birthday ---
    dob = emp.get("dob")
    if dob and dob.month == target_date.month and dob.day == target_date.day:
        if _already_sent(name, "birthday", target_date):
            logger.info("[birthday] Skipping %s — already sent for %s", name, target_date)
        else:
            try:
                img = generate_birthday_poster(emp, cfg, secrets, target_date)
                img_bytes = poster_to_bytes(img)
                filename = f"birthday_{safe_name}_{target_date.isoformat()}.png"
                out_path = Path("storage/output") / filename
                out_path.write_bytes(img_bytes)
                birthday_posters.append((filename, img_bytes))
                birthday_names.append(name)
                logger.info("[birthday] Generated poster for %s (date: %s)", name, target_date)
            except Exception as exc:
                logger.error("[birthday] Poster failed for %s: %s", name, exc)

    # --- Anniversary ---
    doj = emp.get("doj")
    if doj and doj.month == target_date.month and doj.day == target_date.day:
        if _already_sent(name, "anniversary", target_date):
            logger.info("[anniversary] Skipping %s — already sent for %s", name, target_date)
        else:
            try:
                img = generate_anniversary_poster(emp, cfg, secrets, target_date)
                img_bytes = poster_to_bytes(img)
                filename = f"anniversary_{safe_name}_{target_date.isoformat()}.png"
                out_path = Path("storage/output") / filename
                out_path.write_bytes(img_bytes)
                anniversary_posters.append((filename, img_bytes))
                anniversary_names.append(name)
                logger.info("[anniversary] Generated poster for %s (date: %s)", name, target_date)
            except Exception as exc:
                logger.error("[anniversary] Poster failed for %s: %s", name, exc)

    return birthday_posters, birthday_names, anniversary_posters, anniversary_names


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
    from mailer import send_birthday_emails, send_anniversary_emails

    logger.info("Fetching employees...")
    raw_employees = get_employees(cfg, secrets)
    employees = [map_employee(r, cfg.get("field_mapping", {})) for r in raw_employees]
    logger.info("Loaded %d employee(s)", len(employees))

    os.makedirs("storage/output", exist_ok=True)

    dates_to_process = _dates_to_check(today)
    if len(dates_to_process) > 1:
        logger.info(
            "Monday catch-up: processing dates %s",
            [d.isoformat() for d in dates_to_process],
        )

    smtp_sender = secrets.get("smtp_sender", "")
    smtp_password = secrets.get("smtp_password", "")

    if not args.dry_run and (not smtp_sender or not smtp_password):
        logger.error("SMTP credentials missing — set smtp_sender and smtp_password in secrets.toml")
        sys.exit(1)

    for target_date in dates_to_process:
        birthday_posters: list[tuple[str, bytes]] = []
        birthday_names: list[str] = []
        anniversary_posters: list[tuple[str, bytes]] = []
        anniversary_names: list[str] = []

        for emp in employees:
            bp, bn, ap, an = process_employee_for_date(emp, target_date, cfg, secrets)
            birthday_posters.extend(bp)
            birthday_names.extend(bn)
            anniversary_posters.extend(ap)
            anniversary_names.extend(an)

        logger.info(
            "[%s] Generated: %d birthday poster(s), %d anniversary poster(s)",
            target_date, len(birthday_posters), len(anniversary_posters),
        )

        if args.dry_run:
            continue

        try:
            send_birthday_emails(
                birthday_posters,
                cfg.get("recipients", {}).get("birthday", {}),
                smtp_sender,
                smtp_password,
                target_date,
                employee_names=birthday_names,
            )
            for name in birthday_names:
                _mark_sent(name, "birthday", target_date)
        except Exception as exc:
            logger.error("Birthday email send failed for %s: %s", target_date, exc)

        try:
            send_anniversary_emails(
                anniversary_posters,
                cfg.get("recipients", {}).get("anniversary", {}),
                smtp_sender,
                smtp_password,
                target_date,
                employee_names=anniversary_names,
            )
            for name in anniversary_names:
                _mark_sent(name, "anniversary", target_date)
        except Exception as exc:
            logger.error("Anniversary email send failed for %s: %s", target_date, exc)

    if args.dry_run:
        logger.info("Dry run — email sending skipped.")

    logger.info("=== Run complete ===")


if __name__ == "__main__":
    main()
