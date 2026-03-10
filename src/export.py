from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import Optional

from .database import Database
from .models import TimeEntry
from .time_calc import compute_durations, compute_running_totals, format_duration


def export_entries_csv(entries: list[TimeEntry], filepath: str,
                       break_projects: list[str]) -> None:
    durations = compute_durations(entries)
    running = compute_running_totals(durations)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Time", "Project", "Activity", "Detail",
                         "Duration", "Running Total"])
        for entry, dur, run in zip(entries, durations, running):
            writer.writerow([
                entry.date_str,
                entry.time_str,
                entry.project,
                entry.activity,
                entry.detail,
                format_duration(dur) if dur is not None else "",
                format_duration(run) if run is not None else "",
            ])


def prompt_and_export(db: Database, break_projects: list[str],
                      date: Optional[datetime] = None) -> Optional[str]:
    """Open a save dialog and export today's (or given date's) entries."""
    if date is None:
        date = datetime.now()

    entries = db.get_entries_for_date(date)
    if not entries:
        return None

    default_name = f"timetracker_{date.strftime('%Y%m%d')}.csv"
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile=default_name,
    )
    if not filepath:
        return None

    export_entries_csv(entries, filepath, break_projects)
    return filepath


def prompt_and_export_week(db: Database, break_projects: list[str],
                           ref_date: Optional[datetime] = None) -> Optional[str]:
    """Export the entire week's entries."""
    if ref_date is None:
        ref_date = datetime.now()

    entries = db.get_entries_for_week(ref_date)
    if not entries:
        return None

    default_name = f"timetracker_week_{ref_date.strftime('%Y%m%d')}.csv"
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile=default_name,
    )
    if not filepath:
        return None

    export_entries_csv(entries, filepath, break_projects)
    return filepath
