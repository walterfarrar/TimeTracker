from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

import customtkinter as ctk

from .time_calc import format_duration

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class HeaderBar(ctk.CTkFrame):
    """Top bar with date navigation and weekly stats."""

    def __init__(self, master: ctk.CTkBaseClass,
                 on_days_changed: Optional[Callable[[float], None]] = None,
                 on_date_changed: Optional[Callable[[datetime], None]] = None,
                 **kwargs):
        super().__init__(master, **kwargs)
        self._on_days_changed = on_days_changed
        self._on_date_changed = on_date_changed
        self._view_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        self.grid_columnconfigure(0, weight=1)

        self._build_date_nav(row=0)
        self._build_stats(row=1)

    def _build_date_nav(self, row: int) -> None:
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.grid(row=row, column=0, sticky="ew", padx=10, pady=(6, 2))
        nav.grid_columnconfigure(1, weight=1)

        btn_font = ctk.CTkFont(size=16, weight="bold")

        self._prev_day_btn = ctk.CTkButton(
            nav, text="\u25C0", width=32, height=28, font=btn_font,
            fg_color="gray40", hover_color="gray50",
            command=self._prev_day)
        self._prev_day_btn.grid(row=0, column=0, padx=(0, 6))

        self._date_label = ctk.CTkLabel(
            nav, text="", font=ctk.CTkFont(size=16, weight="bold"),
            anchor="center")
        self._date_label.grid(row=0, column=1, sticky="ew")

        self._next_day_btn = ctk.CTkButton(
            nav, text="\u25B6", width=32, height=28, font=btn_font,
            fg_color="gray40", hover_color="gray50",
            command=self._next_day)
        self._next_day_btn.grid(row=0, column=2, padx=(6, 4))

        self._today_btn = ctk.CTkButton(
            nav, text="Today", width=60, height=28,
            font=ctk.CTkFont(size=12),
            command=self._go_today)
        self._today_btn.grid(row=0, column=3, padx=(4, 0))

        self._update_date_label()

    def _build_stats(self, row: int) -> None:
        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.grid(row=row, column=0, sticky="ew", padx=0, pady=(0, 4))
        stats.grid_columnconfigure((0, 1, 2), weight=1)

        label_font = ctk.CTkFont(size=12)
        value_font = ctk.CTkFont(size=20, weight="bold")

        # Days this week (editable)
        ctk.CTkLabel(stats, text="Days This Week", font=label_font,
                     text_color="gray70").grid(row=0, column=0, padx=10, pady=(4, 0))
        self._days_var = ctk.StringVar(value="5.0")
        self._days_entry = ctk.CTkEntry(
            stats, textvariable=self._days_var, width=70, height=32,
            font=value_font, justify="center", border_width=1,
            border_color="gray50",
        )
        self._days_entry.grid(row=1, column=0, padx=10, pady=(0, 4))
        self._days_entry.bind("<Return>", self._on_days_edited)
        self._days_entry.bind("<FocusOut>", self._on_days_edited)

        # Worked today
        ctk.CTkLabel(stats, text="Worked Today", font=label_font,
                     text_color="gray70").grid(row=0, column=1, padx=10, pady=(4, 0))
        self._worked_value = ctk.CTkLabel(stats, text="0:00:00", font=value_font)
        self._worked_value.grid(row=1, column=1, padx=10, pady=(0, 4))

        # Remaining this week
        ctk.CTkLabel(stats, text="Remaining This Week", font=label_font,
                     text_color="gray70").grid(row=0, column=2, padx=10, pady=(4, 0))
        self._remaining_value = ctk.CTkLabel(stats, text="0:00:00", font=value_font)
        self._remaining_value.grid(row=1, column=2, padx=10, pady=(0, 4))

    def _update_date_label(self) -> None:
        day_name = DAY_NAMES[self._view_date.weekday()]
        self._date_label.configure(
            text=f"{day_name}  {self._view_date.strftime('%m/%d/%Y')}")

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        is_today = self._view_date == today
        self._today_btn.configure(
            state="disabled" if is_today else "normal",
            fg_color="#2980b9" if not is_today else "gray25")

    def _prev_day(self) -> None:
        self._view_date -= timedelta(days=1)
        self._update_date_label()
        if self._on_date_changed:
            self._on_date_changed(self._view_date)

    def _next_day(self) -> None:
        self._view_date += timedelta(days=1)
        self._update_date_label()
        if self._on_date_changed:
            self._on_date_changed(self._view_date)

    def _go_today(self) -> None:
        self._view_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self._update_date_label()
        if self._on_date_changed:
            self._on_date_changed(self._view_date)

    @property
    def view_date(self) -> datetime:
        return self._view_date

    @property
    def is_viewing_today(self) -> bool:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self._view_date == today

    def _on_days_edited(self, event=None) -> None:
        text = self._days_var.get().strip()
        try:
            val = float(text)
        except ValueError:
            return
        if val < 0:
            return
        if self._on_days_changed:
            self._on_days_changed(val)
        self.focus_set()

    def set_days(self, working_days: float) -> None:
        self._days_var.set(str(working_days))

    def update_stats(self, worked_today_secs: float,
                     remaining_secs: float) -> None:
        self._worked_value.configure(text=format_duration(worked_today_secs))
        self._remaining_value.configure(text=format_duration(remaining_secs))

        if remaining_secs < 0:
            self._remaining_value.configure(text_color="#e74c3c")
        elif remaining_secs < 3600:
            self._remaining_value.configure(text_color="#f39c12")
        else:
            self._remaining_value.configure(text_color=("gray10", "gray90"))
