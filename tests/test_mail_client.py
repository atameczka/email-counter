"""Tests for mail_client.py — pure helpers and ImapMailClient with a fake connection."""

import base64
from datetime import date, datetime, timezone
from email.message import EmailMessage

import pytest

from mail_client import (
    ImapError,
    ImapMailClient,
    _decode_email_header,
    _decode_modified_utf7,
    _extract_body,
    _normalize_datetime,
    _parse_list_response,
)


# --- pure helpers -----------------------------------------------------------


def test_decode_modified_utf7_ascii_unchanged():
    assert _decode_modified_utf7("INBOX") == "INBOX"


def test_decode_modified_utf7_non_ascii():
    # "日本語" encoded in modified UTF-7
    assert _decode_modified_utf7("&ZeVnLIqe-") == "日本語"


def test_decode_modified_utf7_escaped_ampersand():
    assert _decode_modified_utf7("Ampersand &- folder") == "Ampersand & folder"


def test_decode_modified_utf7_mixed():
    assert _decode_modified_utf7("Sent &ZeVnLIqe-") == "Sent 日本語"


def test_decode_email_header_plain():
    assert _decode_email_header("Alice <alice@example.com>") == "Alice <alice@example.com>"


def test_decode_email_header_encoded_word():
    encoded = base64.b64encode("Zażółć".encode("utf-8")).decode()
    assert _decode_email_header(f"=?UTF-8?B?{encoded}?=") == "Zażółć"


def test_decode_email_header_empty():
    assert _decode_email_header("") == ""


def test_decode_email_header_unknown_charset_ignored():
    assert _decode_email_header("=?X-NO-SUCH-CHARSET?B?aGVsbG8=?=") == "hello"


def test_parse_list_response_slash_delimiter():
    assert _parse_list_response('(\\HasNoChildren) "/" "INBOX"') == "INBOX"


def test_parse_list_response_dot_delimiter():
    assert _parse_list_response('(\\HasNoChildren) "." "INBOX.Sent"') == "INBOX.Sent"


def test_parse_list_response_nil_delimiter():
    assert _parse_list_response('(\\Noselect) NIL "INBOX"') == "INBOX"


def test_parse_list_response_unquoted_name():
    assert _parse_list_response('(\\HasNoChildren) "/" INBOX') == "INBOX"


def test_parse_list_response_modified_utf7_name():
    assert _parse_list_response('(\\HasNoChildren) "/" "&ZeVnLIqe-"') == "日本語"


def test_parse_list_response_quoted_name_with_escaped_quote():
    assert (
        _parse_list_response(r'(\HasChildren) "/" "My \"Quoted\" Folder"')
        == 'My "Quoted" Folder'
    )


def test_parse_list_response_malformed_returns_none():
    assert _parse_list_response("garbage") is None


def test_extract_body_single_part():
    message = EmailMessage()
    message.set_content("Hello world")
    assert _extract_body(message) == "Hello world"


def test_extract_body_multipart_picks_text_plain():
    message = EmailMessage()
    message.set_content("plain body")
    message.add_alternative("<p>html body</p>", subtype="html")
    assert _extract_body(message) == "plain body"


def test_extract_body_skips_attachments():
    message = EmailMessage()
    message.set_content("real body")
    message.add_attachment(b"data", maintype="text", subtype="plain", filename="notes.txt")
    assert _extract_body(message) == "real body"


def test_extract_body_empty_payload():
    message = EmailMessage()
    message["Subject"] = "empty"
    message.set_content("")
    assert _extract_body(message) == ""


def test_normalize_datetime_naive_becomes_utc():
    value = _normalize_datetime(datetime(2024, 1, 1, 12, 0))
    assert value.tzinfo is not None
    assert value.utcoffset() == timezone.utc.utcoffset(None)


def test_normalize_datetime_aware_converts_to_utc():
    aware = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert _normalize_datetime(aware) == aware


# --- ImapMailClient with a fake connection ----------------------------------


class FakeConnection:
    """Minimal stand-in for imaplib.IMAP4_SSL."""

    def __init__(self, messages=None, list_lines=None):
        self.messages = messages or {}  # {msg_id bytes: raw message bytes}
        self.list_lines = list_lines or [b'(\\HasNoChildren) "/" "INBOX"']
        self.selected = None
        self.readonly = None
        self.search_criteria = None
        self.logged_out = False

    def login(self, user, password):
        self.user = user
        self.password = password

    def logout(self):
        self.logged_out = True

    def list(self):
        return ("OK", self.list_lines)

    def select(self, mailbox, readonly=False):
        self.selected = mailbox
        self.readonly = readonly
        return ("OK", [b"1"])

    def search(self, charset, criteria):
        self.search_criteria = criteria
        return ("OK", [b" ".join(self.messages)])

    def fetch(self, msg_id, parts):
        return ("OK", [(msg_id, self.messages[msg_id])])


def make_email(subject, sender, date_str, body):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["Date"] = date_str
    message.set_content(body)
    return message.as_bytes()


def make_client(connection):
    client = ImapMailClient("imap.example.com")
    client.connection = connection
    return client


def test_list_folders_returns_decoded_names():
    connection = FakeConnection(
        list_lines=[
            b'(\\HasNoChildren) "/" "INBOX"',
            b'(\\HasNoChildren) "/" "&ZeVnLIqe-"',
        ]
    )
    assert make_client(connection).list_folders() == ["INBOX", "日本語"]


def test_list_folders_requires_connection():
    with pytest.raises(ImapError):
        ImapMailClient("imap.example.com").list_folders()


def test_list_folders_raises_on_list_failure():
    connection = FakeConnection()
    connection.list = lambda: ("NO", [b"list failed"])
    with pytest.raises(ImapError):
        make_client(connection).list_folders()


def test_fetch_emails_parses_and_sorts_newest_first():
    messages = {
        b"1": make_email("older", "a@example.com", "Mon, 05 Feb 2024 09:00:00 +0000", "first"),
        b"2": make_email("newer", "b@example.com", "Tue, 06 Feb 2024 09:00:00 +0000", "second"),
    }
    client = make_client(FakeConnection(messages))
    results = client.fetch_emails("INBOX", date(2024, 2, 1), date(2024, 2, 29))

    assert [r["subject"] for r in results] == ["newer", "older"]
    assert results[0]["sender"] == "b@example.com"
    assert results[0]["body"] == "second"
    assert results[0]["date"].tzinfo is not None


def test_fetch_emails_end_date_is_inclusive():
    connection = FakeConnection(
        {b"1": make_email("m", "a@example.com", "Mon, 05 Feb 2024 09:00:00 +0000", "b")}
    )
    client = make_client(connection)
    client.fetch_emails("INBOX", date(2024, 2, 1), date(2024, 2, 5))
    assert 'SINCE "01-Feb-2024"' in connection.search_criteria
    assert 'BEFORE "06-Feb-2024"' in connection.search_criteria


def test_fetch_emails_mixed_naive_and_aware_dates_no_crash():
    messages = {
        b"1": make_email("aware", "a@example.com", "Mon, 05 Feb 2024 10:00:00 +0100", "b"),
        b"2": make_email("naive", "b@example.com", "Mon, 05 Feb 2024 08:00:00", "b"),
    }
    client = make_client(FakeConnection(messages))
    # 10:00+0100 = 09:00 UTC sorts after the naive 08:00 UTC interpretation
    results = client.fetch_emails("INBOX", date(2024, 2, 1), date(2024, 2, 29))
    assert [r["subject"] for r in results] == ["aware", "naive"]


def test_fetch_emails_skips_message_without_body_data():
    connection = FakeConnection(
        {b"1": make_email("ok", "a@example.com", "Mon, 05 Feb 2024 09:00:00 +0000", "body")}
    )
    connection.fetch = lambda msg_id, parts: ("OK", [None])
    assert make_client(connection).fetch_emails("INBOX", date(2024, 2, 1), date(2024, 2, 29)) == []


def test_fetch_emails_skips_missing_date_header():
    message = EmailMessage()
    message["Subject"] = "no date"
    message.set_content("body")
    connection = FakeConnection({b"1": message.as_bytes()})
    assert make_client(connection).fetch_emails("INBOX", date(2024, 2, 1), date(2024, 2, 29)) == []


def test_fetch_emails_escapes_quotes_in_folder_name():
    connection = FakeConnection()
    make_client(connection).fetch_emails('My "Folder"', date(2024, 2, 1), date(2024, 2, 5))
    assert connection.selected == '"My \\"Folder\\""'
    assert connection.readonly is True


def test_fetch_emails_validates_date_order():
    with pytest.raises(ValueError):
        make_client(FakeConnection()).fetch_emails("INBOX", date(2024, 2, 29), date(2024, 2, 1))


def test_fetch_emails_requires_connection():
    with pytest.raises(ImapError):
        ImapMailClient("imap.example.com").fetch_emails("INBOX", date(2024, 2, 1), date(2024, 2, 5))


def test_connect_and_disconnect(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr("mail_client.imaplib.IMAP4_SSL", lambda *args, **kwargs: connection)

    client = ImapMailClient("imap.example.com")
    assert not client.connected
    client.connect("user@example.com", "secret")
    assert client.connected
    assert connection.user == "user@example.com"
    client.disconnect()
    assert not client.connected
    assert connection.logged_out


def test_disconnect_is_idempotent():
    ImapMailClient("imap.example.com").disconnect()  # must not raise


def test_context_manager_disconnects():
    connection = FakeConnection()
    client = ImapMailClient("imap.example.com")
    client.connection = connection
    with client:
        assert client.connected
    assert not client.connected
    assert connection.logged_out
