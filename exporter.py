import csv

def export_to_csv(emails: list[dict], filepath: str) -> None:
    with open(filepath, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(["Date", "Sender", "Subject"])

        for email in emails:
            writer.writerow([email["date"], email["sender"], email["subject"]])