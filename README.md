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

- **IMAP connectivity:** works with any mailbox that supports IMAP, not tied to a single provider.
- **Folder & date range selection:** pick exactly which folder and time window to analyze.
- **CSV export:** save the results (date, sender, subject) for further analysis in Excel or elsewhere.
- **Planned:** sender-frequency analysis to help flag likely spam senders (see Roadmap).

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

```
git clone https://github.com/atameczka/email-counter.git
```

2. Run the application:

```
python main.py
```

No external dependencies are required — everything used is part of the Python standard library.

## 🚧 Current Status

- [ ] IMAP connection logic
- [ ] Folder listing
- [ ] Date-range email search
- [ ] Tkinter GUI
- [ ] CSV export
- [ ] Packaged release

This project is under active development, built incrementally commit by commit.

## 🗺️ Roadmap

- Sender-frequency analysis to detect likely spam senders

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.