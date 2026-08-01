import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from datetime import date, datetime

from exporter import export_to_csv, format_date
from mail_client import ImapMailClient

DEFAULT_PORT = "993"


def default_date_range(today: date | None = None) -> tuple[date, date]:
    """Return (first day of the current month, today) as the default search window."""
    today = today or date.today()
    return today.replace(day=1), today


class EmailCounterApp:
    def __init__(self, window):
        self.window = window
        self.window.title("Email Counter")
        self.window.geometry("1050x600")

        self.login_frame = tk.Frame(window)
        self.main_frame = tk.Frame(window)

        self.emails = []
        self.client = None

        self._build_login_frame()
        self._build_main_frame()

        self.login_frame.pack()

    def _build_login_frame(self):
        frame = self.login_frame

        tk.Label(frame, text="Email:").grid(row=0, column=0, sticky="e")
        self.email_entry = tk.Entry(frame, width=30)
        self.email_entry.grid(row=0, column=1)

        tk.Label(frame, text="Password:").grid(row=1, column=0, sticky="e")
        self.password_entry = tk.Entry(frame, show="*", width=30)
        self.password_entry.grid(row=1, column=1)

        tk.Label(frame, text="IMAP host:").grid(row=2, column=0, sticky="e")
        self.host_entry = tk.Entry(frame, width=30)
        self.host_entry.grid(row=2, column=1)

        tk.Label(frame, text="Port:").grid(row=3, column=0, sticky="e")
        self.port_entry = tk.Entry(frame, width=10)
        self.port_entry.insert(0, DEFAULT_PORT)
        self.port_entry.grid(row=3, column=1, sticky="w")

        self.connect_button = tk.Button(frame, text="Connect", command=self.on_connect)
        self.connect_button.grid(row=4, column=0, columnspan=2, pady=10)

        self.status_label = tk.Label(frame, text="")
        self.status_label.grid(row=5, column=0, columnspan=2)

    def _build_main_frame(self):
        frame = self.main_frame

        tk.Label(frame, text="Folder:").grid(row=0, column=0, sticky="e")
        self.folder_combo = ttk.Combobox(frame, state="readonly")
        self.folder_combo.grid(row=0, column=1)

        default_from, default_to = default_date_range()
        date_format = "%Y-%m-%d"

        tk.Label(frame, text="Date from (YYYY-MM-DD):").grid(row=1, column=0, sticky="e")
        self.date_from_entry = tk.Entry(frame, width=30)
        self.date_from_entry.insert(0, default_from.strftime(date_format))
        self.date_from_entry.grid(row=1, column=1)

        tk.Label(frame, text="Date to (YYYY-MM-DD):").grid(row=2, column=0, sticky="e")
        self.date_to_entry = tk.Entry(frame, width=30)
        self.date_to_entry.insert(0, default_to.strftime(date_format))
        self.date_to_entry.grid(row=2, column=1)

        self.fetch_button = tk.Button(frame, text="Fetch", command=self.on_fetch)
        self.fetch_button.grid(row=3, column=0, columnspan=2, pady=10)

        self.result_label = tk.Label(frame, text="")
        self.result_label.grid(row=4, column=0, columnspan=2)

        columns = ("no", "date", "sender", "subject", "body")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)
        self.tree.heading("no", text="#")
        self.tree.heading("date", text="Date")
        self.tree.heading("sender", text="Sender")
        self.tree.heading("subject", text="Subject")
        self.tree.heading("body", text="Body")
        self.tree.column("no", width=40, anchor="center")
        self.tree.column("date", width=140)
        self.tree.column("sender", width=180)
        self.tree.column("subject", width=220)
        self.tree.column("body", width=260)
        self.tree.grid(row=5, column=0, columnspan=2, pady=10)

        self.tree.bind("<Double-1>", self.on_row_double_click)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=5, column=2, sticky="ns")

        self.export_button = tk.Button(frame, text="Export to CSV", command=self.on_export)
        self.export_button.grid(row=6, column=0, columnspan=2, pady=10)

    def on_connect(self):
        email_address = self.email_entry.get()
        password = self.password_entry.get()
        host = self.host_entry.get()
        port = self.port_entry.get().strip() or DEFAULT_PORT

        if not host or not email_address:
            self.status_label.config(text="Email and IMAP host are required")
            return

        try:
            port = int(port)
        except ValueError:
            self.status_label.config(text="Port must be a number")
            return

        self.client = ImapMailClient(host, port=port)
        try:
            self.client.connect(email_address, password)
            folders = self.client.list_folders()
        except Exception as e:
            self.status_label.config(text=f"Error: {e}")
            self.client.disconnect()
            return

        self.folder_combo["values"] = folders
        if "INBOX" in folders:
            self.folder_combo.set("INBOX")
        elif folders:
            self.folder_combo.current(0)

        self.login_frame.pack_forget()
        self.main_frame.pack()

    def on_fetch(self):
        folder = self.folder_combo.get()
        if not folder:
            self.result_label.config(text="Select a folder first")
            return

        try:
            date_from = datetime.strptime(self.date_from_entry.get(), "%Y-%m-%d").date()
            date_to = datetime.strptime(self.date_to_entry.get(), "%Y-%m-%d").date()
        except ValueError:
            self.result_label.config(text="Invalid date format, use YYYY-MM-DD")
            return

        if date_from > date_to:
            self.result_label.config(text="Date from must not be after date to")
            return

        # Run the IMAP work off the UI thread so the window stays responsive.
        self.fetch_button.config(state="disabled")
        self.result_label.config(text="Fetching...")
        worker = threading.Thread(
            target=self._fetch_worker, args=(folder, date_from, date_to), daemon=True
        )
        worker.start()

    def _fetch_worker(self, folder, date_from, date_to):
        try:
            emails = self.client.fetch_emails(folder, date_from, date_to)
            error = None
        except Exception as exc:
            emails = []
            error = str(exc)
        self.window.after(0, lambda: self._fetch_finished(emails, error))

    def _fetch_finished(self, emails, error):
        self.fetch_button.config(state="normal")
        if error:
            self.result_label.config(text=f"Error: {error}")
            return

        self.emails = emails
        self.result_label.config(text=f"Fetched {len(emails)} emails")

        self.tree.delete(*self.tree.get_children())
        for i, e in enumerate(emails, start=1):
            body_text = e["body"].replace("\n", " ").replace("\r", " ").strip()
            body_preview = body_text[:50] + ("..." if len(body_text) > 50 else "")
            self.tree.insert(
                "",
                "end",
                values=(i, format_date(e["date"]), e["sender"], e["subject"], body_preview),
            )

    def on_row_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return

        index = int(self.tree.item(item_id, "values")[0]) - 1
        email = self.emails[index]

        detail_window = tk.Toplevel(self.window)
        detail_window.title(email["subject"] or "(no subject)")
        detail_window.geometry("500x400")

        header = f"From: {email['sender']}\nDate: {format_date(email['date'])}\n\n"

        text = scrolledtext.ScrolledText(detail_window, wrap="word")
        text.insert("1.0", header + email["body"])
        text.config(state="disabled")
        text.pack(fill="both", expand=True)

    def on_export(self):
        if not self.emails:
            self.result_label.config(text="Nothing to export - fetch emails first")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not filepath:
            return

        try:
            export_to_csv(self.emails, filepath)
        except OSError as e:
            self.result_label.config(text=f"Export failed: {e}")
            return
        self.result_label.config(text=f"Exported {len(self.emails)} emails to {filepath}")
