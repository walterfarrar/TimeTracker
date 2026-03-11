from __future__ import annotations

import tkinter as tk
from datetime import datetime, timedelta
from typing import Callable, Optional

import customtkinter as ctk

from .time_calc import format_duration

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class _ProgressText(tk.Canvas):
    """Canvas that draws a rounded progress bar with outlined text on top."""

    def __init__(self, master, height: int = 36, corner_radius: int = 10,
                 **kwargs):
        super().__init__(master, height=height, highlightthickness=0, **kwargs)
        self._h = height
        self._cr = corner_radius
        self._progress = 0.0
        self._text = "0:00:00"
        self._fill_color = "#2980b9"
        self._text_color = "#ffffff"
        self._text_warn_color: str | None = None

        is_dark = ctk.get_appearance_mode().lower() == "dark"
        self._track_color = "#383838" if is_dark else "#c8c8c8"
        self._outline_color = "#000000" if is_dark else "#555555"
        self.configure(bg="#2b2b2b" if is_dark else "#e8e8e8")

        self.bind("<Configure>", self._redraw)

    def update_values(self, progress: float, text: str,
                      fill_color: str, text_color: str | None = None) -> None:
        self._progress = max(0.0, min(progress, 1.0))
        self._text = text
        self._fill_color = fill_color
        self._text_warn_color = text_color
        self._redraw()

    def _round_rect(self, x1, y1, x2, y2, r, **kw) -> None:
        r = min(r, (x2 - x1) / 2, (y2 - y1) / 2)
        self.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r,
                        start=90, extent=90, style="pieslice", **kw)
        self.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r,
                        start=0, extent=90, style="pieslice", **kw)
        self.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2,
                        start=270, extent=90, style="pieslice", **kw)
        self.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2,
                        start=180, extent=90, style="pieslice", **kw)
        self.create_rectangle(x1 + r, y1, x2 - r, y2, **kw)
        self.create_rectangle(x1, y1 + r, x1 + r, y2 - r, **kw)
        self.create_rectangle(x2 - r, y1 + r, x2, y2 - r, **kw)

    def _redraw(self, _event=None) -> None:
        self.delete("all")
        w = self.winfo_width()
        h = self._h
        cr = self._cr
        if w < 2:
            return

        self._round_rect(0, 0, w, h, cr,
                         fill=self._track_color, outline="")

        fill_w = int(w * self._progress)
        if fill_w > 0:
            fill_w = max(fill_w, cr * 2)
            fill_w = min(fill_w, w)
            self._round_rect(0, 0, fill_w, h, cr,
                             fill=self._fill_color, outline="")

        cx, cy = w / 2, h / 2
        font = ("Segoe UI", 15, "bold")
        fg = self._text_warn_color or self._text_color
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                self.create_text(cx + dx, cy + dy, text=self._text,
                                 font=font, fill=self._outline_color)
        self.create_text(cx, cy, text=self._text, font=font, fill=fg)


_STATE_COLORS = {
    "working": ("#d4edda", "#1a3a2a"),
    "break":   ("#fff3cd", "#3a351a"),
    "idle":    ("gray92",  "gray14"),
}

_ANIM_STEPS = 10
_ANIM_INTERVAL_MS = 30


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    if color.startswith("#"):
        c = color.lstrip("#")
        return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
    from tkinter import Frame
    _tmp = Frame()
    rgb = _tmp.winfo_rgb(color)
    _tmp.destroy()
    return rgb[0] >> 8, rgb[1] >> 8, rgb[2] >> 8


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _lerp_color(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return _rgb_to_hex(r, g, b)


_BAND_COLORS = [
    "#e06060",  # light red
    "#e8a030",  # orange / yellow
    "#40b050",  # green
    "#3080d0",  # blue
    "#8050c0",  # purple
]
_BAND_WIDTH = 0.16
_TRANS_WIDTH = 0.05


def _progress_color(progress: float) -> str:
    colors = _BAND_COLORS
    n = len(colors)
    if progress <= 0:
        return colors[0]
    if progress >= 1:
        return colors[-1]

    pos = 0.0
    for i in range(n):
        band_end = pos + _BAND_WIDTH
        if progress <= band_end:
            return colors[i]
        pos = band_end
        if i < n - 1:
            trans_end = pos + _TRANS_WIDTH
            if progress <= trans_end:
                t = (progress - pos) / _TRANS_WIDTH
                return _lerp_color(colors[i], colors[i + 1], t)
            pos = trans_end

    return colors[-1]


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
        self._work_state = "idle"
        self._anim_after_id: Optional[str] = None

        self.grid_columnconfigure(0, weight=1)

        self._build_date_nav(row=0)
        self._build_stats(row=1)

    def _build_date_nav(self, row: int) -> None:
        is_dark = ctk.get_appearance_mode().lower() == "dark"
        idle_color = _STATE_COLORS["idle"][1 if is_dark else 0]
        self._nav = ctk.CTkFrame(self, fg_color=idle_color, corner_radius=10)
        self._nav_current_hex = idle_color
        nav = self._nav
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

        # Remaining this week (with progress bar)
        ctk.CTkLabel(stats, text="Remaining This Week", font=label_font,
                     text_color="gray70").grid(row=0, column=2, padx=10, pady=(4, 0))

        self._progress_text = _ProgressText(stats, height=36, corner_radius=10)
        self._progress_text.grid(row=1, column=2, padx=10, pady=(0, 4), sticky="ew")

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

    def set_work_state(self, state: str) -> None:
        """Set the work state: 'working', 'break', or 'idle'.
        Animates the nav bar color transition."""
        if state == self._work_state:
            return
        self._work_state = state

        if self._anim_after_id:
            self.after_cancel(self._anim_after_id)
            self._anim_after_id = None

        is_dark = ctk.get_appearance_mode().lower() == "dark"
        target = _STATE_COLORS.get(state, _STATE_COLORS["idle"])
        target_hex = target[1 if is_dark else 0]
        start_hex = self._nav_current_hex

        if start_hex == target_hex:
            return

        step = [0]

        def _animate():
            step[0] += 1
            t = step[0] / _ANIM_STEPS
            color = _lerp_color(start_hex, target_hex, t)
            self._nav.configure(fg_color=color)
            self._nav_current_hex = color
            if step[0] < _ANIM_STEPS:
                self._anim_after_id = self.after(_ANIM_INTERVAL_MS, _animate)
            else:
                self._nav_current_hex = target_hex
                self._anim_after_id = None

        _animate()

    def update_stats(self, worked_today_secs: float,
                     remaining_secs: float,
                     week_worked_secs: float = 0.0,
                     week_target_secs: float = 1.0) -> None:
        self._worked_value.configure(text=format_duration(worked_today_secs))

        if remaining_secs < 0:
            text_color = "#e74c3c"
        elif remaining_secs < 3600:
            text_color = "#f39c12"
        else:
            text_color = None

        progress = min(week_worked_secs / max(week_target_secs, 1), 1.0)

        bar_color = _progress_color(progress)

        self._progress_text.update_values(
            progress, format_duration(remaining_secs),
            bar_color, text_color)
