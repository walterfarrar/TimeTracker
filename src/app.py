from __future__ import annotations

import tkinter as tk
from datetime import datetime
from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageTk

from .database import Database
from .export import prompt_and_export, prompt_and_export_week, export_all_json, import_all_json
from .header import HeaderBar
from .log_view import LogView
from .models import AppSettings, ButtonConfig, TimeEntry
from .reports_view import ReportsView
from .sidebar import Sidebar
from .time_calc import (
    compute_durations,
    compute_per_day_work_time,
    compute_work_time,
    compute_week_work_time,
    compute_time_remaining,
    format_duration,
)
from .tray import TrayManager
from .utils import get_app_icon_png_path, get_buttons_path, get_settings_path


class TimeTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings = AppSettings.load(get_settings_path())
        self.button_config = ButtonConfig.load(get_buttons_path())

        ctk.set_appearance_mode(self.settings.theme)
        ctk.set_default_color_theme("blue")

        self.title("Time Tracker")
        self._apply_window_icon()
        geo = f"{self.settings.window_width}x{self.settings.window_height}"
        if self.settings.window_x is not None and self.settings.window_y is not None:
            geo += f"+{self.settings.window_x}+{self.settings.window_y}"
        self.geometry(geo)
        self.minsize(800, 400)

        self.db = Database(self.settings.effective_db_path())

        self._live_tick_id: Optional[str] = None
        self._tray_tick: int = 0
        self._cached_worked_today: float = 0.0
        self._cached_week_worked: float = 0.0
        self._cached_per_day: dict[int, float] = {}
        self._last_entry_timestamp: float = 0.0
        self._last_entry_is_break: bool = False
        self._day_ended: bool = False

        self._today_last_timestamp: float = 0.0
        self._today_last_is_break: bool = False
        self._today_ended: bool = False

        self._build_ui()
        self._load_sidebar_buttons()
        self.header.set_days(self.settings.working_days_this_week)
        self.refresh_log()

        self.tray = TrayManager(self)
        self.tray.start()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Control-e>", lambda e: self._export_today())
        self.bind("<Control-E>", lambda e: self._export_week())
        self.bind("<Control-j>", lambda e: self._export_json())
        self.bind("<Control-J>", lambda e: self._import_json())

        self._start_live_tick()

    def _apply_window_icon(self) -> None:
        path = get_app_icon_png_path()
        if not path.is_file():
            return
        try:
            img = Image.open(path)
            self._window_icon_photo = ImageTk.PhotoImage(img)
            self.iconphoto(True, self._window_icon_photo)
        except OSError:
            pass

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

        self.log_view = LogView(
            log_tab,
            on_edit=self._on_entry_edit,
            on_delete=self._on_entry_delete,
            on_add_above=self._on_entry_add_above,
            on_add_below=self._on_entry_add_below,
            activity_list=self._get_activity_list(),
            on_activity_changed=self._on_activity_changed,
            project_list=self._get_all_project_list(),
            on_project_changed=self._on_project_changed,
        )
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
        """Shift focus away from the days entry when clicking on non-interactive areas."""
        widget = event.widget
        try:
            if widget != self.header._days_entry and not widget.master == self.header._days_entry:
                interactive = (tk.Entry, tk.Listbox, tk.Text, tk.Spinbox,
                               ctk.CTkEntry, ctk.CTkComboBox, ctk.CTkButton)
                w = widget
                while w is not None:
                    if isinstance(w, interactive):
                        return
                    w = getattr(w, "master", None)
                self.header._days_entry.winfo_toplevel().focus_set()
        except (AttributeError, KeyError, tk.TclError):
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

    def _on_project_button(self, project: str, activity: str) -> None:
        self.db.add_entry(project=project, activity=activity)
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
        self.log_view.refresh(entries, self.settings.break_projects,
                              activity_list=self._get_activity_list(),
                              project_list=self._get_all_project_list())

        durations = compute_durations(entries)
        self._cached_worked_today = compute_work_time(
            entries, durations, self.settings.break_projects)

        today = datetime.now()
        week_entries = self.db.get_entries_for_week(today)
        self._cached_week_worked = compute_week_work_time(
            week_entries, self.settings.break_projects)
        self._cached_per_day = compute_per_day_work_time(
            week_entries, self.settings.break_projects)

        today_entries = self.db.get_entries_for_date(
            today.replace(hour=0, minute=0, second=0, microsecond=0))
        if today_entries:
            last_today = today_entries[-1]
            self._today_last_timestamp = last_today.timestamp
            self._today_last_is_break = last_today.project in self.settings.break_projects
            self._today_ended = last_today.project == "END_OF_DAY"
        else:
            self._today_last_timestamp = 0.0
            self._today_last_is_break = False
            self._today_ended = False

        if entries and self.header.is_viewing_today:
            last = entries[-1]
            self._last_entry_timestamp = last.timestamp
            self._last_entry_is_break = last.project in self.settings.break_projects
            self._day_ended = last.project == "END_OF_DAY"
        else:
            self._last_entry_timestamp = 0.0
            self._last_entry_is_break = False
            self._day_ended = not self.header.is_viewing_today

        if not self.header.is_viewing_today:
            self.header.set_work_state("idle")
        elif self._today_ended or self._today_last_timestamp == 0.0:
            self.header.set_work_state("idle")
        elif self._today_last_is_break:
            self.header.set_work_state("break")
        else:
            self.header.set_work_state("working")

        self._update_header_live()

    def _get_project_list(self) -> list[str]:
        """Collect unique project names from the button config."""
        seen = set()
        projects = []
        for group in self.button_config.groups:
            for btn in group.buttons:
                if btn.project and btn.project not in seen:
                    seen.add(btn.project)
                    projects.append(btn.project)
        return projects

    def _get_all_project_list(self) -> list[str]:
        """Collect unique project names from the database and button config."""
        db_projects = self.db.get_distinct_projects()
        seen = set(db_projects)
        projects = list(db_projects)
        for group in self.button_config.groups:
            for btn in group.buttons:
                if btn.project and btn.project not in seen:
                    seen.add(btn.project)
                    projects.append(btn.project)
        projects.sort(key=str.lower)
        return projects

    def _get_activity_list(self) -> list[str]:
        """Collect unique activity names from the database and button config."""
        db_activities = self.db.get_distinct_activities()
        seen = set(db_activities)
        activities = list(db_activities)
        for group in self.button_config.groups:
            for btn in group.buttons:
                if btn.activity and btn.activity not in seen:
                    seen.add(btn.activity)
                    activities.append(btn.activity)
        activities.sort(key=str.lower)
        return activities

    def _on_project_changed(self, entry: TimeEntry, new_project: str) -> None:
        self.db.update_entry(entry.id, new_project, entry.activity)
        entry.project = new_project
        self.log_view.update_project_list(self._get_all_project_list())

    def _on_activity_changed(self, entry: TimeEntry, new_activity: str) -> None:
        self.db.update_entry(entry.id, entry.project, new_activity)
        entry.activity = new_activity
        self.log_view.update_activity_list(self._get_activity_list())

    def _on_entry_edit(self, entry: TimeEntry) -> None:
        from .edit_dialog import EditEntryDialog
        dialog = EditEntryDialog(
            self, entry, project_list=self._get_project_list(), mode="edit",
        )
        self.wait_window(dialog)
        if dialog.result == "save":
            self.db.update_entry(
                entry.id, dialog.project, dialog.activity,
                timestamp=dialog.timestamp,
            )
            self.refresh_log()
        elif dialog.result == "delete":
            self.db.delete_entry(entry.id)
            self.refresh_log()

    def _on_entry_delete(self, entry: TimeEntry) -> None:
        self.db.delete_entry(entry.id)
        self.refresh_log()

    def _on_entry_add_above(self, entry: TimeEntry) -> None:
        placeholder = TimeEntry(
            id=0, timestamp=entry.timestamp - 1,
            project="", activity="",
        )
        self._open_add_dialog(placeholder)

    def _on_entry_add_below(self, entry: TimeEntry) -> None:
        placeholder = TimeEntry(
            id=0, timestamp=entry.timestamp + 1,
            project="", activity="",
        )
        self._open_add_dialog(placeholder)

    def _open_add_dialog(self, placeholder: TimeEntry) -> None:
        from .edit_dialog import EditEntryDialog
        dialog = EditEntryDialog(
            self, placeholder, project_list=self._get_project_list(), mode="add",
        )
        self.wait_window(dialog)
        if dialog.result == "save":
            self.db.add_entry(
                project=dialog.project, activity=dialog.activity,
                timestamp=dialog.timestamp,
            )
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

    def _export_json(self) -> None:
        export_all_json(self.db, self.settings, self.button_config)

    def _import_json(self) -> None:
        payload = import_all_json(self.db)
        if payload:
            if "buttons" in payload:
                self.button_config = ButtonConfig.from_dict(payload["buttons"])
                self.button_config.save(get_buttons_path())
                self._load_sidebar_buttons()
            if "settings" in payload:
                self.settings = AppSettings.from_dict(payload["settings"])
                self.settings.save(get_settings_path())
                self.header.set_days(self.settings.working_days_this_week)
            self.refresh_log()

    def _update_header_live(self) -> None:
        """Compute live totals by adding elapsed time since last entry."""
        today_elapsed = 0.0
        if (not self._today_ended and not self._today_last_is_break
                and self._today_last_timestamp > 0):
            today_elapsed = datetime.now().timestamp() - self._today_last_timestamp

        live_week_worked = self._cached_week_worked + today_elapsed

        if self.header.is_viewing_today:
            live_worked_today = self._cached_worked_today + today_elapsed
        else:
            live_worked_today = self._cached_worked_today

        remaining = compute_time_remaining(
            live_week_worked,
            self.settings.working_days_this_week,
            self.settings.hours_per_day,
        )

        week_target = self.settings.working_days_this_week * self.settings.hours_per_day * 3600
        work_before_today = live_week_worked - live_worked_today
        day_target = min(self.settings.hours_per_day * 3600,
                         max(week_target - work_before_today, 0.0))

        today_weekday = datetime.now().weekday()
        live_per_day = dict(self._cached_per_day)
        live_per_day[today_weekday] = live_per_day.get(today_weekday, 0.0) + today_elapsed

        self.header.update_stats(
            live_worked_today, remaining, live_week_worked,
            week_target, day_target, per_day=live_per_day)

    def _start_live_tick(self) -> None:
        """Update the header counters and current entry duration every second."""
        self._update_header_live()
        if not self._today_ended:
            if self.header.is_viewing_today:
                self.log_view.tick_live_duration()
            if self._tabview.get() == "Reports":
                self.reports_view.live_tick()
        self._tray_tick += 1
        if self._tray_tick % 60 == 0:
            self._update_tray_tooltip()
        self._live_tick_id = self.after(1000, self._start_live_tick)

    def _update_tray_tooltip(self) -> None:
        elapsed = 0.0
        if self._today_last_timestamp > 0:
            elapsed = datetime.now().timestamp() - self._today_last_timestamp
        if self._today_last_is_break:
            worked = self._cached_worked_today
        else:
            worked = self._cached_worked_today + elapsed

        if self._today_last_timestamp > 0:
            last = self.db.get_last_entry()
            project = last.project if last else "?"
            self.tray.update_tooltip(
                f"Time Tracker - {project} | Worked: {format_duration(worked)}"
            )
        else:
            self.tray.update_tooltip("Time Tracker")

    def _save_window_geometry(self) -> None:
        self.settings.window_width = self.winfo_width()
        self.settings.window_height = self.winfo_height()
        self.settings.window_x = self.winfo_x()
        self.settings.window_y = self.winfo_y()
        self.settings.save(get_settings_path())

    def _on_minimize_to_tray(self) -> None:
        self._save_window_geometry()
        self.withdraw()

    def _on_close(self) -> None:
        if self._live_tick_id:
            self.after_cancel(self._live_tick_id)
        self.tray.stop()
        self._save_window_geometry()
        self.db.close()
        self.destroy()
