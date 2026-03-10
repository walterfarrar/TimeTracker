from __future__ import annotations

from datetime import datetime

import customtkinter as ctk

from .models import TimeEntry


class EditEntryDialog(ctk.CTkToplevel):
    """Dialog for editing, deleting, or adding a time entry."""

    def __init__(self, master, entry: TimeEntry,
                 project_list: list[str] | None = None,
                 mode: str = "edit"):
        super().__init__(master)
        self.entry = entry
        self.mode = mode
        self.result = None
        self.project = entry.project
        self.activity = entry.activity
        self.timestamp = entry.timestamp

        self._project_list = project_list or []
        if entry.project and entry.project not in self._project_list:
            self._project_list = [entry.project] + self._project_list

        self.title("Add Entry" if mode == "add" else "Edit Entry")
        self.geometry("400x280")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._build_ui()
        self.after(100, self.lift)

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": (8, 0), "sticky": "ew"}
        label_font = ctk.CTkFont(size=12)

        ctk.CTkLabel(self, text="Date & Time", font=label_font, anchor="w").grid(
            row=0, column=0, **pad)
        dt = datetime.fromtimestamp(self.entry.timestamp)
        self._dt_var = ctk.StringVar(value=dt.strftime("%m/%d/%Y %I:%M:%S %p"))
        ctk.CTkEntry(self, textvariable=self._dt_var).grid(row=1, column=0, **pad)

        ctk.CTkLabel(self, text="Project", font=label_font, anchor="w").grid(
            row=2, column=0, **pad)
        self._project_var = ctk.StringVar(value=self.entry.project)
        self._project_combo = ctk.CTkComboBox(
            self, variable=self._project_var,
            values=self._project_list,
            width=360,
        )
        self._project_combo.grid(row=3, column=0, **pad)

        ctk.CTkLabel(self, text="Activity", font=label_font, anchor="w").grid(
            row=4, column=0, **pad)
        self._activity_var = ctk.StringVar(value=self.entry.activity)
        ctk.CTkEntry(self, textvariable=self._activity_var).grid(row=5, column=0, **pad)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=6, column=0, padx=16, pady=16, sticky="ew")

        if self.mode == "add":
            btn_frame.grid_columnconfigure((0, 1), weight=1)
            ctk.CTkButton(btn_frame, text="Add", fg_color="#27ae60",
                           hover_color="#2ecc71", command=self._save).grid(
                row=0, column=0, padx=4, sticky="ew")
            ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray40",
                           hover_color="gray50", command=self._cancel).grid(
                row=0, column=1, padx=4, sticky="ew")
        else:
            btn_frame.grid_columnconfigure((0, 1, 2), weight=1)
            ctk.CTkButton(btn_frame, text="Save", fg_color="#27ae60",
                           hover_color="#2ecc71", command=self._save).grid(
                row=0, column=0, padx=4, sticky="ew")
            ctk.CTkButton(btn_frame, text="Delete", fg_color="#c0392b",
                           hover_color="#e74c3c", command=self._delete).grid(
                row=0, column=1, padx=4, sticky="ew")
            ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray40",
                           hover_color="gray50", command=self._cancel).grid(
                row=0, column=2, padx=4, sticky="ew")

        self.grid_columnconfigure(0, weight=1)

    def _parse_timestamp(self) -> float | None:
        text = self._dt_var.get().strip()
        for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S",
                     "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %I:%M:%S %p"):
            try:
                return datetime.strptime(text, fmt).timestamp()
            except ValueError:
                continue
        return None

    def _save(self) -> None:
        ts = self._parse_timestamp()
        if ts is None:
            self._dt_var.set("Invalid format!")
            return
        self.project = self._project_var.get().strip()
        self.activity = self._activity_var.get().strip()
        self.timestamp = ts
        self.result = "save"
        self.destroy()

    def _delete(self) -> None:
        self.result = "delete"
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
