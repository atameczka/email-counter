"""IMAP mailbox client for counting and fetching emails in a date range."""

import base64
import email
import imaplib
import re
from datetime import date, datetime, timedelta, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Optional


class ImapError(Exception):
    """Raised when an IMAP operation fails or the client is not connected."""


# Matches an IMAP LIST response line, e.g.:
#   (\HasNoChildren) "/" "INBOX"
#   (\HasNoChildren) "." "INBOX.Sent"
#   (\Noselect \HasChildren) "/" "Archive"
_FOLDER_RE = re.compile(
    r"^\((?P<flags>[^)]*)\)\s+(?P<delim>(?:\"(.)\")|NIL|.)\s+(?P<name>.*)$"
)


def _parse_list_response(line: str) -> Optional[str]:
    """Extract the folder name from a single IMAP LIST response line."""
    match = _FOLDER_RE.match(line)
    if not match:
        return None

    name = match.group("name")
    # Names containing special characters are quoted by the server.
    if len(name) >= 2 and name[0] == name[-1] == '"':
        name = name[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return _decode_modified_utf7(name)


class ImapMailClient:
    """Thin wrapper around :mod:`imaplib` with folder listing and date-range search.

    The client is intentionally provider-agnostic: it works with any mailbox
    that exposes IMAP over SSL. Use it as a context manager to guarantee the
    connection is closed::

        with ImapMailClient("imap.example.com") as client:
            client.connect(user, password)
            folders = client.list_folders()
    """

    def __init__(self, host: str, port: int = 993, timeout: Optional[float] = None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.connection: Optional[imaplib.IMAP4_SSL] = None

    @property
    def connected(self) -> bool:
        """Whether a connection is currently open."""
        return self.connection is not None

    def connect(self, email_address: str, password: str) -> None:
        """Open an SSL connection and authenticate with the given credentials."""
        self.connection = imaplib.IMAP4_SSL(
            self.host, self.port, timeout=self.timeout
        )
        self.connection.login(email_address, password)

    def disconnect(self) -> None:
        """Close the connection. Safe to call multiple times."""
        if self.connection is not None:
            try:
                self.connection.logout()
            except (imaplib.IMAP4.error, OSError):
                pass
            finally:
                self.connection = None

    def __enter__(self) -> "ImapMailClient":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.disconnect()

    def _require_connection(self) -> None:
        if self.connection is None:
            raise ImapError("Not connected - call connect() first")

    def list_folders(self) -> list[str]:
        """Return the names of all folders (mailboxes) on the server."""
        self._require_connection()
        status, data = self.connection.list()
        if status != "OK":
            raise ImapError(f"Could not list folders: {status}")

        folders = []
        for item in data or []:
            if item is None:
                continue
            name = _parse_list_response(item.decode(errors="replace"))
            if name is not None:
                folders.append(name)
        return folders

    def fetch_emails(
        self, folder: str, date_from: datetime | date, date_to: datetime | date
    ) -> list[dict]:
        """Fetch emails in *folder* whose Date falls in [date_from, date_to].

        The end date is inclusive. Returned emails are sorted newest first and
        each entry contains ``date`` (timezone-aware), ``sender``, ``subject``
        and ``body`` keys.
        """
        if date_from > date_to:
            raise ValueError("date_from must not be later than date_to")

        self._require_connection()
        safe_folder = folder.replace('"', '\\"')
        status, _ = self.connection.select(f'"{safe_folder}"', readonly=True)
        if status != "OK":
            raise ImapError(f"Could not select folder {folder!r}")

        since_str = date_from.strftime("%d-%b-%Y")
        # IMAP BEFORE is exclusive, so search up to the day AFTER date_to to
        # make the requested end date inclusive.
        before_str = (date_to + timedelta(days=1)).strftime("%d-%b-%Y")
        search_criteria = f'(SINCE "{since_str}" BEFORE "{before_str}")'

        status, data = self.connection.search(None, search_criteria)
        if status != "OK":
            raise ImapError(f"Search failed: {status}")

        message_ids = (data[0] or b"").split()
        results = []
        for msg_id in message_ids:
            status, msg_data = self.connection.fetch(msg_id, "(BODY.PEEK[])")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw_email = msg_data[0][1]
            if raw_email is None:
                continue

            message = email.message_from_bytes(raw_email)
            date_header = message.get("Date")
            if date_header is None:
                continue
            try:
                parsed_date = parsedate_to_datetime(date_header)
            except (ValueError, TypeError):
                continue

            results.append(
                {
                    "date": _normalize_datetime(parsed_date),
                    "sender": _decode_email_header(message.get("From", "")),
                    "subject": _decode_email_header(message.get("Subject", "")),
                    "body": _extract_body(message),
                }
            )

        results.sort(key=lambda entry: entry["date"], reverse=True)
        return results


def _normalize_datetime(value: datetime) -> datetime:
    """Return an aware, UTC-normalized datetime.

    Some servers emit Date headers without a timezone offset, which would
    otherwise make sorting mixed naive/aware datetimes raise a TypeError.
    Naive values are interpreted as UTC so ordering stays consistent.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _decode_modified_utf7(value: str) -> str:
    """Decode an IMAP modified UTF-7 folder name (RFC 3501, section 5.1.3)."""

    def replace(match: re.Match) -> str:
        encoded = match.group(1)
        if encoded == "":
            return "&"
        encoded = encoded.replace(",", "/")
        padding = "=" * (-len(encoded) % 4)
        raw_bytes = base64.b64decode(encoded + padding)
        return raw_bytes.decode("utf-16-be")

    return re.sub(r"&([^-]*)-", replace, value)


def _decode_email_header(value: str) -> str:
    """Decode an RFC 2047-encoded header (e.g. ``=?UTF-8?B?...?=``)."""
    if not value:
        return ""

    parts = decode_header(value)
    result = []
    for part, encoding in parts:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(encoding or "utf-8", errors="ignore"))
            except LookupError:
                result.append(part.decode("utf-8", errors="ignore"))
        else:
            result.append(part)
    return "".join(result)


def _extract_body(message) -> str:
    """Extract the plain-text body of an email message."""
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                return _decode_payload(part)
        return ""
    return _decode_payload(message)


def _decode_payload(part) -> str:
    """Decode a message part payload to text, ignoring undecodable bytes."""
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        text = payload.decode(charset, errors="ignore")
    except LookupError:
        text = payload.decode("utf-8", errors="ignore")
    return text.strip()
