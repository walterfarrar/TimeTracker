from __future__ import annotations

from datetime import datetime
from typing import Optional

import customtkinter as ctk

from .database import Database
from .export import prompt_and_export, prompt_and_export_week
from .header import HeaderBar
from .log_view import LogView
from .models import AppSettings, ButtonConfig, TimeEntry
from .reports_view import ReportsView
from .sidebar import Sidebar
from .time_calc import (
    compute_durations,
    compute_work_time,
    compute_week_work_time,
    compute_time_remaining,
    format_duration,
)
from .tray import TrayManager
from .utils import get_buttons_path, get_settings_path


class TimeTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings = AppSettings.load(get_settings_path())
        self.button_config = ButtonConfig.load(get_buttons_path())

        ctk.set_appearance_mode(self.settings.theme)
        ctk.set_default_color_theme("blue")

        self.title("Time Tracker")
        self.geometry(f"{self.settings.window_width}x{self.settings.window_height}")
        self.minsize(800, 400)

        self.db = Database(self.settings.effective_db_path())

        self._build_ui()
        self._load_sidebar_buttons()
        self.header.set_days(self.settings.working_days_this_week)
        self.refresh_log()

        self.tray = TrayManager(self)
        self.tray.start()

        self.protocol("WM_DELETE_WINDOW", self._on_minimize_to_tray)
        self.bind("<Control-e>", lambda e: self._export_today())
        self.bind("<Control-E>", lambda e: self._export_week())

        self._auto_refresh_id: Optional[str] = None
        self._live_tick_id: Optional[str] = None
        self._cached_worked_today: float = 0.0
        self._cached_week_worked: float = 0.0
        self._last_entry_timestamp: float = 0.0
        self._last_entry_is_break: bool = False
        self._day_ended: bool = False
        self._start_auto_refresh()
        self._start_live_tick()

    def _build_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._tabview = ctk.CTkTabview(self, anchor="nw")
        self._tabview.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # --- Time Log tab ---
        log_tab = self._tabview.add("Time Log")
        log_tab.grid_rowconfigure(1, weight=1)
        log_tab.grid_columnconfigure(0, weight=1)

        self.header = HeaderBar(log_tab, on_days_changed=self._on_days_changed,
                               on_date_changed=self._on_date_changed,
                               fg_color=("gray92", "gray14"))
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 4))

        self.log_view = LogView(log_tab, on_double_click=self._on_entry_double_click)
        self.log_view.grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=0)

        self.sidebar = Sidebar(
            log_tab,
            on_project_click=self._on_project_button,
            on_end_day=self._on_end_day,
            on_refresh=self.refresh_log,
            on_settings=self._open_settings,
            fg_color=("gray92", "gray14"),
        )
        self.sidebar.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)

        # --- Reports tab ---
        reports_tab = self._tabview.add("Reports")
        reports_tab.grid_rowconfigure(0, weight=1)
        reports_tab.grid_columnconfigure(0, weight=1)

        self.reports_view = ReportsView(
            reports_tab, db=self.db,
            break_projects=self.settings.break_projects,
            button_config=self.button_config,
        )
        self.reports_view.grid(row=0, column=0, sticky="nsew")

        self._tabview.configure(command=self._on_tab_changed)

        self.bind_all("<Button-1>", self._on_global_click, add=True)

    def _on_global_click(self, event) -> None:
        """Shift focus away from the days entry when clicking anywhere else."""
        widget = event.widget
        try:
            if widget != self.header._days_entry and not widget.master == self.header._days_entry:
                self.header._days_entry.winfo_toplevel().focus_set()
        except (AttributeError, KeyError):
            pass

    def _load_sidebar_buttons(self) -> None:
        self.button_config = ButtonConfig.load(get_buttons_path())
        self.sidebar.load_buttons(self.button_config)

    def _on_days_changed(self, value: float) -> None:
        self.settings.working_days_this_week = value
        self.settings.save(get_settings_path())
        self._update_header_live()

    def _on_date_changed(self, date: datetime) -> None:
        self.refresh_log()

    def _on_project_button(self, project: str, activity: str, detail: str) -> None:
        self.db.add_entry(project=project, activity=activity, detail=detail)
        self._snap_to_today()

    def _on_end_day(self) -> None:
        self.db.add_entry(project="END_OF_DAY", activity="Done")
        self._snap_to_today()

    def _snap_to_today(self) -> None:
        if not self.header.is_viewing_today:
            self.header._go_today()
        else:
            self.refresh_log()

    def refresh_log(self) -> None:
        view_date = self.header.view_date
        entries = self.db.get_entries_for_date(view_date)
        self.log_view.refresh(entries, self.settings.break_projects)

        durations = compute_durations(entries)
        self._cached_worked_today = compute_work_time(
            entries, durations, self.settings.break_projects)

        today = datetime.now()
        week_entries = self.db.get_entries_for_week(today)
        self._cached_week_worked = compute_week_work_time(
            week_entries, self.settings.break_projects)

        if entries and self.header.is_viewing_today:
            last = entries[-1]
            self._last_entry_timestamp = last.timestamp
            self._last_entry_is_break = last.project in self.settings.break_projects
            self._day_ended = last.project == "END_OF_DAY"
        else:
            self._last_entry_timestamp = 0.0
            self._last_entry_is_break = False
            self._day_ended = not self.header.is_viewing_today

        self._update_header_live()

    def _on_entry_double_click(self, entry: TimeEntry) -> None:
        from .edit_dialog import EditEntryDialog
        dialog = EditEntryDialog(self, entry)
        self.wait_window(dialog)
        if dialog.result == "save":
            self.db.update_entry(
                entry.id, dialog.project, dialog.activity, dialog.detail,
                timestamp=dialog.timestamp,
            )
            self.refresh_log()
        elif dialog.result == "delete":
            self.db.delete_entry(entry.id)
            self.refresh_log()

    def _open_settings(self) -> None:
        from .settings_dialog import SettingsDialog
        dialog = SettingsDialog(self, self.settings, self.button_config)
        self.wait_window(dialog)
        if dialog.result == "save":
            self.settings = dialog.new_settings
            self.settings.save(get_settings_path())
            self.button_config = dialog.new_button_config
            self.button_config.save(get_buttons_path())
            ctk.set_appearance_mode(self.settings.theme)
            self._load_sidebar_buttons()
            self.header.set_days(self.settings.working_days_this_week)
            self.reports_view.update_break_projects(self.settings.break_projects)
            self.reports_view.update_button_config(self.button_config)
            self.refresh_log()

    def _on_tab_changed(self) -> None:
        if self._tabview.get() == "Reports":
            self.reports_view._refresh()

    def _export_today(self) -> None:
        prompt_and_export(self.db, self.settings.break_projects)

    def _export_week(self) -> None:
        prompt_and_export_week(self.db, self.settings.break_projects)

    def _update_header_live(self) -> None:
        """Compute live totals by adding elapsed time since last entry."""
        if self._day_ended or self._last_entry_is_break:
            live_worked_today = self._cached_worked_today
            live_week_worked = self._cached_week_worked
        else:
            elapsed = 0.0
            if self._last_entry_timestamp > 0:
                elapsed = datetime.now().timestamp() - self._last_entry_timestamp
            live_worked_today = self._cached_worked_today + elapsed
            live_week_worked = self._cached_week_worked + elapsed

        remaining = compute_time_remaining(
            live_week_worked,
            self.settings.working_days_this_week,
            self.settings.hours_per_day,
        )

        self.header.update_stats(live_worked_today, remaining)

    def _start_live_tick(self) -> None:
        """Update the header counters and current entry duration every second."""
        self._update_header_live()
        if not self._day_ended:
            self.log_view.tick_live_duration()
        self._live_tick_id = self.after(1000, self._start_live_tick)

    def _start_auto_refresh(self) -> None:
        """Re-query the database and update the log table every 60 seconds."""
        self.refresh_log()
        self._update_tray_tooltip()
        self._auto_refresh_id = self.after(60_000, self._start_auto_refresh)

    def _update_tray_tooltip(self) -> None:
        elapsed = 0.0
        if self._last_entry_timestamp > 0:
            elapsed = datetime.now().timestamp() - self._last_entry_timestamp
        if self._last_entry_is_break:
            worked = self._cached_worked_today
        else:
            worked = self._cached_worked_today + elapsed

        if self._last_entry_timestamp > 0:
            last = self.db.get_last_entry()
            project = last.project if last else "?"
            self.tray.update_tooltip(
                f"Time Tracker - {project} | Worked: {format_duration(worked)}"
            )
        else:
            self.tray.update_tooltip("Time Tracker")

    def _on_minimize_to_tray(self) -> None:
        self.withdraw()

    def _on_close(self) -> None:
        if self._auto_refresh_id:
            self.after_cancel(self._auto_refresh_id)
        if self._live_tick_id:
            self.after_cancel(self._live_tick_id)
        self.tray.stop()
        w = self.winfo_width()
        h = self.winfo_height()
        self.settings.window_width = w
        self.settings.window_height = h
        self.settings.save(get_settings_path())
        self.db.close()
        self.destroy()
