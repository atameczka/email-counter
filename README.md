# 📧 Email Counter

A desktop application for counting and reporting email volume from any IMAP mailbox.

## 📖 Overview

**Email Counter** is a lightweight desktop tool that connects to any IMAP-enabled
mailbox (Gmail, Outlook, Yahoo, and others), lets you pick a folder and a date
range, and reports how many emails match — with the option to export the
results to a `.csv` file for further analysis.

This project is also a personal learning exercise in building a well-structured
Python application: the mail-fetching logic, the CSV export, and the GUI are
kept as separate, independent modules, so the interface can be swapped or
extended without touching the core logic.

## ✨ Key Features

- **IMAP connectivity:** works with any mailbox that supports IMAP over SSL, not tied to a single provider.
- **Folder & date range selection:** pick exactly which folder and time window to analyze (the end date is inclusive).
- **CSV export:** save the results (date, sender, subject, body) in Excel-friendly UTF-8 with a BOM; delimiter and display time zone are configurable.
- **Resilient IMAP client:** tolerates non-standard folder hierarchy delimiters, missing time zones in `Date` headers, and unreadable messages instead of crashing.
- **Responsive GUI:** fetching runs in a background thread, so the window stays usable on large mailboxes.
- **Configurable port:** connect to IMAP endpoints on non-standard ports, not just 993.

## 🛠️ Tech Info

- **Language:** Python 3.10+
- **GUI:** Tkinter (standard library)
- **Mailbox access:** `imaplib` (standard library, no external dependencies)
- **Architecture:** logic (`mail_client.py`, `exporter.py`) kept separate from the GUI layer

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or newer
- An email account with IMAP access enabled (for Gmail/Outlook/Yahoo, an
  **app password** is usually required — regular account passwords won't work
  if two-factor authentication is on)

### Installation & Running

1. Clone the repository:

```bash
git clone https://github.com/atameczka/email-counter.git
cd email-counter
```

2. Install dependencies:

```bash
pip install -e ".[dev]"
```

(Or, without packaging: `pip install -r requirements.txt`.)

3. Run the application:

```bash
python main.py
```

After `pip install -e .` you can also launch it with the `email-counter`
console command.

## 🧪 Tests

The test suite covers the IMAP client (parsing, date handling, error cases),
the CSV exporter, and the GUI helper functions. GUI tests are skipped
automatically on machines without a display or `tkinter`:

```bash
pip install -e ".[dev]"
python -m pytest
```

## ✅ Status

- [x] IMAP connection logic
- [x] Folder listing
- [x] Date-range email search
- [x] Tkinter GUI
- [x] CSV export
- [x] Packaging (`pyproject.toml` + `email-counter` console script)
- [x] Test suite

## 🗺️ Roadmap

- Sender-frequency analysis to detect likely spam senders
- STARTTLS support for non-SSL IMAP endpoints (port 143)

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.
