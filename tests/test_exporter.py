"""Tests for exporter.py — CSV export and date formatting."""

import csv
from datetime import datetime, timezone
from io import StringIO
from zoneinfo import ZoneInfo

from exporter import CSV_HEADERS, _write_emails, export_to_csv, format_date


def test_format_date_converts_to_warsaw():
    value = datetime(2024, 2, 5, 9, 30, tzinfo=timezone.utc)
    assert format_date(value) == "2024-02-05 10:30:00"


def test_format_date_custom_timezone():
    value = datetime(2024, 2, 5, 9, 30, tzinfo=timezone.utc)
    assert format_date(value, ZoneInfo("UTC")) == "2024-02-05 09:30:00"


def test_write_emails_headers_and_rows():
    output = StringIO()
    emails = [
        {
            "date": datetime(2024, 2, 5, 9, 30, tzinfo=timezone.utc),
            "sender": "a@example.com",
            "subject": "Hello",
            "body": "Hi there",
        }
    ]
    _write_emails(output, emails, ";")
    content = output.getvalue()
    # csv.writer uses \r\n line terminators by default (Excel-friendly)
    assert content.startswith("Date;Sender;Subject;Body\r\n")
    assert "2024-02-05 10:30:00;a@example.com;Hello;Hi there\r\n" in content


def test_write_emails_custom_delimiter():
    output = StringIO()
    _write_emails(output, [], ",")
    assert output.getvalue() == "Date,Sender,Subject,Body\r\n"


def test_write_emails_empty_list_only_header():
    output = StringIO()
    _write_emails(output, [], ";")
    assert output.getvalue() == "Date;Sender;Subject;Body\r\n"


def test_export_to_csv_writes_utf8_bom(tmp_path):
    filepath = tmp_path / "emails.csv"
    export_to_csv(
        [
            {
                "date": datetime(2024, 2, 5, 9, 30, tzinfo=timezone.utc),
                "sender": "a@example.com",
                "subject": "Hello",
                "body": "Hi",
            }
        ],
        str(filepath),
    )

    raw = filepath.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM for Excel compatibility
    text = raw.decode("utf-8-sig")
    rows = list(csv.reader(StringIO(text), delimiter=";"))
    assert rows[0] == CSV_HEADERS
    assert rows[1] == ["2024-02-05 10:30:00", "a@example.com", "Hello", "Hi"]
