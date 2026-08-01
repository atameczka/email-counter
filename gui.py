import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from tkinter import filedialog
from datetime import datetime
from mail_client import ImapMailClient
from exporter import format_date, export_to_csv


class EmailCounterApp:
    def __init__(self, window):
        self.window = window
        self.window.title("Email Counter")
        self.window.geometry("1050x600")

        self.login_frame = tk.Frame(window)
        self.main_frame = tk.Frame(window)

        self.emails = []

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

        self.connect_button = tk.Button(frame, text="Connect", command=self.on_connect)
        self.connect_button.grid(row=3, column=0, columnspan=2, pady=10)

        self.status_label = tk.Label(frame, text="")
        self.status_label.grid(row=4, column=0, columnspan=2)

    def _build_main_frame(self):
        frame = self.main_frame

        tk.Label(frame, text="Folder:").grid(row=0, column=0, sticky="e")
        self.folder_combo = ttk.Combobox(frame, state="readonly")
        self.folder_combo.grid(row=0, column=1)

        tk.Label(frame, text="Date from (YYYY-MM-DD):").grid(row=1, column=0, sticky="e")
        self.date_from_entry = tk.Entry(frame, width=30)
        self.date_from_entry.grid(row=1, column=1)

        tk.Label(frame, text="Date to (YYYY-MM-DD):").grid(row=2, column=0, sticky="e")
        self.date_to_entry = tk.Entry(frame, width=30)
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

        self.client = ImapMailClient(host)
        try:
            self.client.connect(email_address, password)
        except Exception as e:
            self.status_label.config(text=f"Error: {e}")
            return

        folders = self.client.list_folders()
        self.folder_combo["values"] = folders
        if "INBOX" in folders:
            self.folder_combo.set("INBOX")
        elif folders:
            self.folder_combo.current(0)

        self.login_frame.pack_forget()
        self.main_frame.pack()

    def on_fetch(self):
        folder = self.folder_combo.get()

        try:
            date_from = datetime.strptime(self.date_from_entry.get(), "%Y-%m-%d")
            date_to = datetime.strptime(self.date_to_entry.get(), "%Y-%m-%d")
        except ValueError:
            self.result_label.config(text="Invalid date format, use YYYY-MM-DD")
            return

        self.emails = self.client.fetch_emails(folder, date_from, date_to)
        self.result_label.config(text=f"Fetched {len(self.emails)} emails")

        self.tree.delete(*self.tree.get_children())
        for i, e in enumerate(self.emails, start=1):
            body_text = e["body"].replace("\n", " ").replace("\r", " ").strip()
            body_preview = body_text[:50] + ("..." if len(body_text) > 50 else "")
            self.tree.insert("", "end", values=(i, format_date(e["date"]), e["sender"], e["subject"], body_preview))

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

        export_to_csv(self.emails, filepath)
        self.result_label.config(text=f"Exported {len(self.emails)} emails to {filepath}")


if __name__ == "__main__":
    window = tk.Tk()
    app = EmailCounterApp(window)
    window.mainloop()