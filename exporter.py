import csv
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")

def export_to_csv(emails: list[dict], filepath: str) -> None:
    with open(filepath, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["Date", "Sender", "Subject", "Body"])

        for email in emails:
            local_date = email["date"].astimezone(WARSAW)
            writer.writerow([
                local_date.strftime("%Y-%m-%d %H:%M:%S"),
                email["sender"],
                email["subject"],
                email["body"],
            ])