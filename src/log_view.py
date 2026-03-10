from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import customtkinter as ctk

from .models import TimeEntry
from .time_calc import compute_durations, compute_running_totals, format_duration


COL_HEADERS = ["Date", "Time", "Project", "Activity", "Detail", "Duration", "Total"]
COL_WIDTHS = [90, 100, 130, 120, 120, 80, 80]


class LogView(ctk.CTkFrame):
    """Scrollable time-entry table for a single day."""

    def __init__(self, master: ctk.CTkBaseClass,
                 on_double_click: Optional[Callable[[TimeEntry], None]] = None,
                 **kwargs):
        super().__init__(master, **kwargs)
        self._on_double_click = on_double_click
        self._entry_rows: list[tuple[TimeEntry, list[ctk.CTkLabel]]] = []
        self._last_entry: Optional[TimeEntry] = None
        self._last_dur_label: Optional[ctk.CTkLabel] = None
        self._last_run_label: Optional[ctk.CTkLabel] = None
        self._base_running: float = 0.0

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_scroll_area()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 0))
        for i, (text, w) in enumerate(zip(COL_HEADERS, COL_WIDTHS)):
            lbl = ctk.CTkLabel(header, text=text, width=w,
                               font=ctk.CTkFont(size=12, weight="bold"),
                               anchor="w")
            lbl.grid(row=0, column=i, padx=2, sticky="w")

    def _build_scroll_area(self) -> None:
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

    def refresh(self, entries: list[TimeEntry], break_projects: list[str]) -> None:
        for _, labels in self._entry_rows:
            for lbl in labels:
                lbl.destroy()
        self._entry_rows.clear()
        self._last_entry = None
        self._last_dur_label = None
        self._last_run_label = None
        self._base_running = 0.0

        durations = compute_durations(entries)
        running = compute_running_totals(durations)

        # Sum all completed durations for the running total baseline
        for d in durations:
            if d is not None:
                self._base_running += d

        for row_idx, (entry, dur, run) in enumerate(zip(entries, durations, running)):
            is_break = entry.project in break_projects
            fg = "#555555" if is_break else "transparent"

            values = [
                entry.date_str,
                entry.time_str,
                entry.project,
                entry.activity,
                entry.detail,
                format_duration(dur) if dur is not None else "",
                format_duration(run) if run is not None else "",
            ]

            labels: list[ctk.CTkLabel] = []
            for col_idx, (val, w) in enumerate(zip(values, COL_WIDTHS)):
                lbl = ctk.CTkLabel(
                    self._scroll, text=val, width=w, anchor="w",
                    font=ctk.CTkFont(size=12),
                    fg_color=fg if is_break else "transparent",
                    corner_radius=4,
                )
                lbl.grid(row=row_idx, column=col_idx, padx=2, pady=1, sticky="w")
                if self._on_double_click:
                    lbl.bind("<Double-Button-1>",
                             lambda e, ent=entry: self._on_double_click(ent))
                labels.append(lbl)

            self._entry_rows.append((entry, labels))

        if entries:
            self._last_entry = entries[-1]
            last_labels = self._entry_rows[-1][1]
            self._last_dur_label = last_labels[5]  # Duration column
            self._last_run_label = last_labels[6]  # Running column

        # Auto-scroll to bottom
        self._scroll.after(50, lambda: self._scroll._parent_canvas.yview_moveto(1.0))

    def tick_live_duration(self) -> None:
        """Update the last row's duration and running total with live elapsed time."""
        if self._last_entry is None or self._last_dur_label is None:
            return
        elapsed = datetime.now().timestamp() - self._last_entry.timestamp
        self._last_dur_label.configure(text=format_duration(elapsed))
        self._last_run_label.configure(text=format_duration(self._base_running + elapsed))
