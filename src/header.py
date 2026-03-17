from __future__ import annotations

import math
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
        self._dividers: list[float] = []

        is_dark = ctk.get_appearance_mode().lower() == "dark"
        self._track_color = "#484848" if is_dark else "#b8b8b8"
        self._outline_color = "#000000" if is_dark else "#555555"
        self._bg_color = "#2b2b2b" if is_dark else "#e8e8e8"
        self.configure(bg=self._bg_color)

        self.bind("<Configure>", self._redraw)

    def update_values(self, progress: float, text: str,
                      fill_color: str, text_color: str | None = None,
                      dividers: list[float] | None = None) -> None:
        self._progress = max(0.0, min(progress, 1.0))
        self._text = text
        self._fill_color = fill_color
        self._text_warn_color = text_color
        if dividers is not None:
            self._dividers = dividers
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

        notch_size = 6
        is_dark = ctk.get_appearance_mode().lower() == "dark"
        notch_color = "#000000" if is_dark else "#ffffff"
        for frac in self._dividers:
            x = int(w * frac)
            if x <= cr or x >= w - cr:
                continue
            self.create_polygon(
                x - notch_size, 0, x + notch_size, 0, x, notch_size,
                fill=notch_color, outline="")
            self.create_polygon(
                x - notch_size, h, x + notch_size, h, x, h - notch_size,
                fill=notch_color, outline="")

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
_BAND_WIDTH = 0.176
_TRANS_WIDTH = 0.03


_DAY_COLOR_FALLBACK = "#808080"


def _day_color(weekday: int) -> str:
    """Return a solid band color for a weekday (0=Mon … 4=Fri), grey otherwise."""
    if 0 <= weekday < len(_BAND_COLORS):
        return _BAND_COLORS[weekday]
    return _DAY_COLOR_FALLBACK


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


def _compute_day_dividers(
    per_day: dict[int, float],
    today_weekday: int,
    hours_per_day: float,
    working_days: float,
    week_target_secs: float,
) -> list[float]:
    """Return fractional x-positions (0..1) for dividers between day segments."""
    day_target = hours_per_day * 3600
    num_segments = max(math.ceil(working_days), len(per_day))
    if num_segments <= 1 or week_target_secs <= 0:
        return []

    widths: list[float] = []
    future_indices: list[int] = []
    allocated = 0.0

    for i in range(num_segments):
        if i < today_weekday:
            w = per_day.get(i, 0.0)
        elif i == today_weekday:
            w = max(day_target, per_day.get(i, 0.0))
        else:
            future_indices.append(i)
            widths.append(0.0)
            continue
        allocated += w
        widths.append(w)

    if future_indices:
        remaining = max(week_target_secs - allocated, 0.0)
        each = remaining / len(future_indices)
        for idx in future_indices:
            widths[idx] = each

    total = sum(widths)
    if total <= 0:
        return []

    dividers: list[float] = []
    cumulative = 0.0
    for i in range(num_segments - 1):
        cumulative += widths[i]
        pos = cumulative / total
        if 0.0 < pos < 1.0:
            dividers.append(pos)

    return dividers


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
        self._current_bar_color: str = _BAND_COLORS[0]

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

        # Remaining today (with daily progress bar)
        ctk.CTkLabel(stats, text="Remaining Today", font=label_font,
                     text_color="gray70").grid(row=0, column=1, padx=10, pady=(4, 0))
        self._daily_progress = _ProgressText(stats, height=36, corner_radius=10)
        self._daily_progress.grid(row=1, column=1, padx=10, pady=(0, 4), sticky="ew")

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

    def _nav_tint(self, bar_color: str) -> str:
        """Create a subtle background tint from a progress bar color."""
        is_dark = ctk.get_appearance_mode().lower() == "dark"
        base = "#1a1a1a" if is_dark else "#f4f4f4"
        blend = 0.35 if is_dark else 0.25
        return _lerp_color(base, bar_color, blend)

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
        if state == "working":
            target_hex = self._nav_tint(self._current_bar_color)
        else:
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
                     week_target_secs: float = 1.0,
                     day_target_secs: float = 1.0,
                     per_day: dict[int, float] | None = None) -> None:
        if remaining_secs < 0:
            text_color = "#e74c3c"
        elif remaining_secs < 3600:
            text_color = "#f39c12"
        else:
            text_color = None

        progress = min(week_worked_secs / max(week_target_secs, 1), 1.0)

        bar_color = _progress_color(progress)
        self._current_bar_color = bar_color

        if self._work_state == "working":
            tint = self._nav_tint(bar_color)
            if tint != self._nav_current_hex:
                self._nav.configure(fg_color=tint)
                self._nav_current_hex = tint

        today_weekday = datetime.now().weekday()
        working_days = float(self._days_var.get() or "5")
        dividers = _compute_day_dividers(
            per_day or {}, today_weekday,
            day_target_secs / 3600, working_days, week_target_secs)

        self._progress_text.update_values(
            progress, format_duration(remaining_secs),
            bar_color, text_color, dividers)

        daily_progress = min(worked_today_secs / max(day_target_secs, 1), 1.0)
        daily_remaining = day_target_secs - worked_today_secs
        daily_color = _day_color(self._view_date.weekday())
        if daily_remaining < 0:
            daily_text_color = "#e74c3c"
        elif daily_remaining < 3600:
            daily_text_color = "#f39c12"
        else:
            daily_text_color = None
        self._daily_progress.update_values(
            daily_progress, format_duration(daily_remaining),
            daily_color, daily_text_color)
