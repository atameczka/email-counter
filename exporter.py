import csv
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")


def format_date(date):
    return date.astimezone(WARSAW).strftime("%Y-%m-%d %H:%M:%S")


def export_to_csv(emails: list[dict], filepath: str) -> None:
    with open(filepath, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["Date", "Sender", "Subject", "Body"])

        for email in emails:
            writer.writerow([
                format_date(email["date"]),
                email["sender"],
                email["subject"],
                email["body"],
            ])