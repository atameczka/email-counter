"""CSV export helpers for email results."""

import csv
from datetime import datetime
from typing import TextIO
from zoneinfo import ZoneInfo

# Default time zone used for exported timestamps.
WARSAW = ZoneInfo("Europe/Warsaw")

CSV_HEADERS = ["Date", "Sender", "Subject", "Body"]


def format_date(date: datetime, timezone: ZoneInfo = WARSAW) -> str:
    """Format a datetime for CSV output, converted to *timezone*."""
    return date.astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S")


def export_to_csv(emails: list[dict], filepath: str, delimiter: str = ";") -> None:
    """Write *emails* to a UTF-8 CSV file at *filepath*.

    The file is written with a UTF-8 BOM (``utf-8-sig``) so it opens cleanly
    in Excel, and the delimiter defaults to ``;`` for the same reason.
    """
    with open(filepath, "w", newline="", encoding="utf-8-sig") as file:
        _write_emails(file, emails, delimiter)


def _write_emails(file: TextIO, emails: list[dict], delimiter: str) -> None:
    writer = csv.writer(file, delimiter=delimiter)
    writer.writerow(CSV_HEADERS)
    for email in emails:
        writer.writerow(
            [
                format_date(email["date"]),
                email["sender"],
                email["subject"],
                email["body"],
            ]
        )
