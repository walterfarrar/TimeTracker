from __future__ import annotations

import tkinter as tk
from datetime import datetime
from typing import Callable, Optional

import customtkinter as ctk

from .models import TimeEntry
from .time_calc import compute_durations, compute_running_totals, format_duration


COL_HEADERS = ["Date", "Time", "Project", "Activity", "Detail", "Duration", "Total", ""]
COL_WIDTHS = [90, 100, 130, 120, 120, 80, 80, 30]

HOVER_BORDER = "#3a86ff"
NORMAL_BORDER = "transparent"


class LogView(ctk.CTkFrame):
    """Scrollable time-entry table for a single day."""

    def __init__(self, master: ctk.CTkBaseClass,
                 on_edit: Optional[Callable[[TimeEntry], None]] = None,
                 on_delete: Optional[Callable[[TimeEntry], None]] = None,
                 on_add_above: Optional[Callable[[TimeEntry], None]] = None,
                 on_add_below: Optional[Callable[[TimeEntry], None]] = None,
                 **kwargs):
        super().__init__(master, **kwargs)
        self._on_edit = on_edit
        self._on_delete = on_delete
        self._on_add_above = on_add_above
        self._on_add_below = on_add_below

        self._row_frames: list[ctk.CTkFrame] = []
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
        self._scroll.grid_columnconfigure(0, weight=1)

    def refresh(self, entries: list[TimeEntry], break_projects: list[str]) -> None:
        for frame in self._row_frames:
            frame.destroy()
        self._row_frames.clear()
        self._entry_rows.clear()
        self._last_entry = None
        self._last_dur_label = None
        self._last_run_label = None
        self._base_running = 0.0

        durations = compute_durations(entries)
        running = compute_running_totals(durations)

        for d in durations:
            if d is not None:
                self._base_running += d

        for row_idx, (entry, dur, run) in enumerate(zip(entries, durations, running)):
            is_break = entry.project in break_projects
            row_bg = "#3a3a3a" if is_break else "transparent"

            row_frame = ctk.CTkFrame(
                self._scroll, fg_color=row_bg,
                border_width=1, border_color=NORMAL_BORDER,
                corner_radius=4, height=28,
            )
            row_frame.grid(row=row_idx, column=0, sticky="ew", padx=0, pady=1)
            row_frame.grid_propagate(False)
            for c in range(len(COL_WIDTHS)):
                row_frame.grid_columnconfigure(c, weight=0)

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
                    row_frame, text=val, width=w, anchor="w",
                    font=ctk.CTkFont(size=12),
                    fg_color="transparent",
                )
                lbl.grid(row=0, column=col_idx, padx=2, pady=0, sticky="w")
                labels.append(lbl)

            pencil_btn = ctk.CTkButton(
                row_frame, text="\u270E", width=24, height=22,
                font=ctk.CTkFont(size=14),
                fg_color="transparent", hover_color=("gray75", "gray30"),
                text_color=("gray40", "gray60"),
                corner_radius=4,
                command=lambda e=entry, btn=None: None,
            )
            pencil_btn.grid(row=0, column=len(COL_WIDTHS) - 1, padx=(0, 2), pady=0, sticky="e")
            pencil_btn.grid_remove()

            pencil_btn.configure(
                command=lambda e=entry, pb=pencil_btn: self._show_context_menu(e, pb)
            )

            row_frame.bind("<Enter>", lambda ev, rf=row_frame, pb=pencil_btn: self._on_row_enter(rf, pb))
            row_frame.bind("<Leave>", lambda ev, rf=row_frame, pb=pencil_btn: self._on_row_leave(rf, pb))
            for lbl in labels:
                lbl.bind("<Enter>", lambda ev, rf=row_frame, pb=pencil_btn: self._on_row_enter(rf, pb))
                lbl.bind("<Leave>", lambda ev, rf=row_frame, pb=pencil_btn: self._on_row_leave(rf, pb))

            self._row_frames.append(row_frame)
            self._entry_rows.append((entry, labels))

        if entries:
            self._last_entry = entries[-1]
            last_labels = self._entry_rows[-1][1]
            self._last_dur_label = last_labels[5]
            self._last_run_label = last_labels[6]

        self._scroll.after(50, lambda: self._scroll._parent_canvas.yview_moveto(1.0))

    def _on_row_enter(self, row_frame: ctk.CTkFrame, pencil_btn: ctk.CTkButton) -> None:
        row_frame.configure(border_color=HOVER_BORDER)
        pencil_btn.grid()

    def _on_row_leave(self, row_frame: ctk.CTkFrame, pencil_btn: ctk.CTkButton) -> None:
        row_frame.configure(border_color=NORMAL_BORDER)
        pencil_btn.grid_remove()

    def _show_context_menu(self, entry: TimeEntry, pencil_btn: ctk.CTkButton) -> None:
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Edit", command=lambda: self._on_edit and self._on_edit(entry))
        menu.add_command(label="Delete", command=lambda: self._on_delete and self._on_delete(entry))
        menu.add_separator()
        menu.add_command(label="Add Above", command=lambda: self._on_add_above and self._on_add_above(entry))
        menu.add_command(label="Add Below", command=lambda: self._on_add_below and self._on_add_below(entry))

        x = pencil_btn.winfo_rootx()
        y = pencil_btn.winfo_rooty() + pencil_btn.winfo_height()
        menu.tk_popup(x, y)

    def tick_live_duration(self) -> None:
        """Update the last row's duration and running total with live elapsed time."""
        if self._last_entry is None or self._last_dur_label is None:
            return
        elapsed = datetime.now().timestamp() - self._last_entry.timestamp
        self._last_dur_label.configure(text=format_duration(elapsed))
        self._last_run_label.configure(text=format_duration(self._base_running + elapsed))
