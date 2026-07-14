import email
import imaplib
import base64
import re

from datetime import datetime
from email.header import decode_header

class ImapMailClient:
    def __init__(self, host: str, port: int = 993):
        self.host = host
        self.port = port
        self.connection = None

    def connect(self, email_address: str, password: str) -> None:
        self.connection = imaplib.IMAP4_SSL(self.host, self.port)
        self.connection.login(email_address, password)

    def disconnect(self) -> None:
        if self.connection is not None:
            self.connection.logout()
            self.connection = None

    def list_folders(self) -> list[str]:
        status, folders = self.connection.list()

        result = []
        for folder in folders:
            decoded_folder = folder.decode()
            name = decoded_folder.split(' "/" ')[1].strip('"')
            result.append(_decode_modified_utf7(name))

        return result

    def fetch_emails(self, folder: str, date_from, date_to) -> list[dict]:
        self.connection.select(f'"{folder}"', readonly=True)

        since_str = date_from.strftime("%d-%b-%Y")
        before_str = date_to.strftime("%d-%b-%Y")
        search_criteria = f'(SINCE "{since_str}" BEFORE "{before_str}")'

        status, data = self.connection.search(None, search_criteria)
        message_ids = data[0].split()

        results = []
        for msg_id in message_ids:
            status, msg_data = self.connection.fetch(
                msg_id, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
            )
            raw_header = msg_data[0][1]
            message = email.message_from_bytes(raw_header)

            results.append({"date": message.get("Date", ""),
                            "sender": _decode_email_header(message.get("From", "")),
                            "subject": _decode_email_header(message.get("Subject", "")),
                            })

        return results


def _decode_modified_utf7(value: str) -> str:
    def replace(match):
        encoded = match.group(1)
        if encoded == "":
            return "&"
        encoded = encoded.replace(",", "/")
        padding = "=" * (-len(encoded) % 4)
        raw_bytes = base64.b64decode(encoded + padding)
        return raw_bytes.decode("utf-16-be")

    return re.sub(r"&([^-]*)-", replace, value)

def _decode_email_header(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    result = ""
    for part, encoding in parts:
        if isinstance(part, bytes):
            result += part.decode(encoding or "utf-8", errors="ignore")
        else:
            result += part
    return result