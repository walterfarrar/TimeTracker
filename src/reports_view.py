from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import customtkinter as ctk
import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .database import Database
from .models import ButtonConfig
from .time_calc import (
    aggregate_time, aggregate_by_day_and_group,
    format_duration, format_hours, format_hm,
)


_COLORS = [
    "#3498db", "#2ecc71", "#e74c3c", "#f39c12", "#9b59b6",
    "#1abc9c", "#e67e22", "#34495e", "#16a085", "#c0392b",
    "#2980b9", "#8e44ad", "#27ae60", "#d35400", "#7f8c8d",
    "#f1c40f", "#e84393", "#00cec9", "#6c5ce7", "#fd79a8",
]


class ReportsView(ctk.CTkFrame):
    """Reports tab with date range selection, pie charts, and text breakdown."""

    def __init__(self, master: ctk.CTkBaseClass, db: Database,
                 break_projects: list[str],
                 button_config: ButtonConfig | None = None, **kwargs):
        super().__init__(master, **kwargs)
        self._db = db
        self._break_projects = break_projects
        self._button_config = button_config or ButtonConfig()

        now = datetime.now()
        weekday = now.weekday()
        self._current_monday = now.replace(
            hour=0, minute=0, second=0, microsecond=0) - timedelta(days=weekday)

        self._round_minutes = 0
        self._tick_counter = 0

        # Stored label references for in-place updates
        self._dt_structure: tuple = ()
        self._dt_cell_labels: dict[tuple[int, int], ctk.CTkLabel] = {}
        self._dt_row_total_labels: dict[int, ctk.CTkLabel] = {}
        self._dt_col_total_labels: dict[int, ctk.CTkLabel] = {}
        self._dt_grand_label: Optional[ctk.CTkLabel] = None

        self._txt_structure: tuple = ()
        self._txt_proj_labels: dict[str, ctk.CTkLabel] = {}
        self._txt_act_labels: dict[tuple[str, str], ctk.CTkLabel] = {}
        self._txt_grand_label: Optional[ctk.CTkLabel] = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_controls()
        self._build_content()

    def _build_controls(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        self._range_var = ctk.StringVar(value="Week")
        ctk.CTkSegmentedButton(
            bar, values=["Week", "Custom Range"],
            variable=self._range_var,
            command=self._on_range_changed,
        ).pack(side="left", padx=(0, 12))

        self._week_nav = ctk.CTkFrame(bar, fg_color="transparent")
        self._week_nav.pack(side="left", padx=(0, 12))

        btn_font = ctk.CTkFont(size=16, weight="bold")
        self._prev_btn = ctk.CTkButton(
            self._week_nav, text="\u25C0", width=32, height=28,
            font=btn_font, command=self._prev_week,
            fg_color="gray40", hover_color="gray50")
        self._prev_btn.pack(side="left", padx=(0, 4))

        self._week_label = ctk.CTkLabel(
            self._week_nav, text="", font=ctk.CTkFont(size=13, weight="bold"),
            width=260, anchor="center")
        self._week_label.pack(side="left", padx=4)

        self._next_btn = ctk.CTkButton(
            self._week_nav, text="\u25B6", width=32, height=28,
            font=btn_font, command=self._next_week,
            fg_color="gray40", hover_color="gray50")
        self._next_btn.pack(side="left", padx=(4, 0))

        self._today_btn = ctk.CTkButton(
            self._week_nav, text="Today", width=60, height=28,
            font=ctk.CTkFont(size=12), command=self._go_to_this_week)
        self._today_btn.pack(side="left", padx=(8, 0))

        self._start_label = ctk.CTkLabel(bar, text="From:", font=ctk.CTkFont(size=12))
        self._start_entry_var = ctk.StringVar()
        self._start_entry = ctk.CTkEntry(bar, textvariable=self._start_entry_var,
                                          width=110, font=ctk.CTkFont(size=12),
                                          placeholder_text="MM/DD/YYYY")

        self._end_label = ctk.CTkLabel(bar, text="To:", font=ctk.CTkFont(size=12))
        self._end_entry_var = ctk.StringVar()
        self._end_entry = ctk.CTkEntry(bar, textvariable=self._end_entry_var,
                                        width=110, font=ctk.CTkFont(size=12),
                                        placeholder_text="MM/DD/YYYY")

        self._apply_btn = ctk.CTkButton(bar, text="Apply", width=70, height=28,
                                         command=self._refresh)

        self._custom_widgets = [self._start_label, self._start_entry,
                                self._end_label, self._end_entry, self._apply_btn]

    def _build_content(self) -> None:
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        self._scroll.grid_columnconfigure(0, weight=1)

        self._daily_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._daily_frame.pack(fill="x", padx=4, pady=(4, 0))

        self._chart_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._chart_frame.pack(fill="x", padx=4, pady=4)

        self._text_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._text_frame.pack(fill="x", padx=4, pady=4)

    def _on_range_changed(self, value: str) -> None:
        for w in self._custom_widgets:
            w.pack_forget()

        if value == "Custom Range":
            self._week_nav.pack_forget()
            self._start_label.pack(side="left", padx=(0, 4))
            self._start_entry.pack(side="left", padx=(0, 8))
            self._end_label.pack(side="left", padx=(0, 4))
            self._end_entry.pack(side="left", padx=(0, 8))
            self._apply_btn.pack(side="left")
        else:
            self._week_nav.pack(side="left", padx=(0, 12))
            self._refresh()

    def _prev_week(self) -> None:
        candidate = self._current_monday - timedelta(days=7)
        if self._db.has_entries_in_range(candidate, candidate + timedelta(days=7)):
            self._current_monday = candidate
            self._refresh()

    def _next_week(self) -> None:
        candidate = self._current_monday + timedelta(days=7)
        if self._db.has_entries_in_range(candidate, candidate + timedelta(days=7)):
            self._current_monday = candidate
            self._refresh()

    def _go_to_this_week(self) -> None:
        now = datetime.now()
        weekday = now.weekday()
        self._current_monday = now.replace(
            hour=0, minute=0, second=0, microsecond=0) - timedelta(days=weekday)
        self._refresh()

    def _update_nav_buttons(self) -> None:
        prev_mon = self._current_monday - timedelta(days=7)
        next_mon = self._current_monday + timedelta(days=7)
        has_prev = self._db.has_entries_in_range(prev_mon, prev_mon + timedelta(days=7))
        has_next = self._db.has_entries_in_range(next_mon, next_mon + timedelta(days=7))

        self._prev_btn.configure(
            state="normal" if has_prev else "disabled",
            fg_color="gray40" if has_prev else "gray25")
        self._next_btn.configure(
            state="normal" if has_next else "disabled",
            fg_color="gray40" if has_next else "gray25")

        sunday = self._current_monday + timedelta(days=6)
        self._week_label.configure(
            text=f"{self._current_monday.strftime('%m/%d/%Y')}  —  {sunday.strftime('%m/%d/%Y')}")

    def _get_date_range(self) -> tuple[datetime, datetime]:
        if self._range_var.get() == "Week":
            return self._current_monday, self._current_monday + timedelta(days=7)

        start_str = self._start_entry_var.get().strip()
        end_str = self._end_entry_var.get().strip()
        try:
            start = datetime.strptime(start_str, "%m/%d/%Y")
        except ValueError:
            start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            end = datetime.strptime(end_str, "%m/%d/%Y") + timedelta(days=1)
        except ValueError:
            end = start + timedelta(days=7)
        return start, end

    def update_break_projects(self, break_projects: list[str]) -> None:
        self._break_projects = break_projects

    def update_button_config(self, button_config: ButtonConfig) -> None:
        self._button_config = button_config

    # ── Live updates ─────────────────────────────────────────────

    def live_tick(self) -> None:
        """Called every second when the Reports tab is visible and day not ended.
        Updates text values in-place every 60s; redraws charts every 5 min."""
        self._tick_counter += 1
        if self._tick_counter % 60 != 0:
            return

        start, end = self._get_date_range()
        entries = self._db.get_entries_range(start, end)
        agg = aggregate_time(entries, self._break_projects, live=True)

        proj_to_group = self._button_config.project_to_group_map()
        days, groups, daily_data = aggregate_by_day_and_group(
            entries, self._break_projects, proj_to_group, live=True)

        new_dt_structure = (tuple(days), tuple(groups))
        if new_dt_structure != self._dt_structure:
            self._refresh()
            return

        self._update_daily_values(days, groups, daily_data)
        self._update_text_values(agg, start, end)

        if self._tick_counter % 300 == 0:
            self._render_charts(agg)

    # ── Full refresh ─────────────────────────────────────────────

    def _refresh(self, *_args) -> None:
        if self._range_var.get() == "Week":
            self._update_nav_buttons()

        start, end = self._get_date_range()
        entries = self._db.get_entries_range(start, end)
        agg = aggregate_time(entries, self._break_projects, live=True)

        proj_to_group = self._button_config.project_to_group_map()
        days, groups, daily_data = aggregate_by_day_and_group(
            entries, self._break_projects, proj_to_group, live=True)

        self._build_daily_table(days, groups, daily_data)
        self._render_charts(agg)
        self._build_text(agg, start, end)

    def _set_rounding(self, minutes: int) -> None:
        self._round_minutes = minutes
        self._rebuild_rounding_buttons()
        if self._dt_structure:
            days, groups = self._dt_structure
            start, end = self._get_date_range()
            entries = self._db.get_entries_range(start, end)
            proj_to_group = self._button_config.project_to_group_map()
            _, _, daily_data = aggregate_by_day_and_group(
                entries, self._break_projects, proj_to_group, live=True)
            self._update_daily_values(list(days), list(groups), daily_data)

    # ── Daily table ──────────────────────────────────────────────

    def _build_daily_table(self, days: list[str], groups: list[str],
                           data: dict[str, dict[str, float]]) -> None:
        for child in self._daily_frame.winfo_children():
            child.destroy()
        self._dt_cell_labels.clear()
        self._dt_row_total_labels.clear()
        self._dt_col_total_labels.clear()
        self._dt_grand_label = None
        self._dt_structure = (tuple(days), tuple(groups))

        if not days or not groups:
            return

        rm = self._round_minutes
        fmt = lambda s: format_hm(s, rm)

        title_row = ctk.CTkFrame(self._daily_frame, fg_color="transparent")
        title_row.pack(fill="x", padx=8, pady=(8, 4))

        ctk.CTkLabel(title_row, text="Weekly Timesheet by Group",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     anchor="w").pack(side="left")

        self._rounding_frame = ctk.CTkFrame(title_row, fg_color="transparent")
        self._rounding_frame.pack(side="right")
        self._rebuild_rounding_buttons()

        table = ctk.CTkFrame(self._daily_frame, fg_color=("gray88", "gray20"),
                              corner_radius=8)
        table.pack(fill="x", padx=8, pady=(0, 8))

        num_cols = len(days) + 2
        for c in range(num_cols):
            table.grid_columnconfigure(c, weight=1 if c > 0 else 0)

        hdr_font = ctk.CTkFont(size=12, weight="bold")
        cell_font = ctk.CTkFont(size=12)
        total_font = ctk.CTkFont(size=12, weight="bold")

        ctk.CTkLabel(table, text="Group", font=hdr_font, anchor="w").grid(
            row=0, column=0, padx=8, pady=4, sticky="w")
        for ci, day in enumerate(days):
            ctk.CTkLabel(table, text=day, font=hdr_font, anchor="center").grid(
                row=0, column=ci + 1, padx=4, pady=4)
        ctk.CTkLabel(table, text="Total", font=hdr_font, anchor="center").grid(
            row=0, column=len(days) + 1, padx=8, pady=4)

        day_totals = {d: 0.0 for d in days}
        for ri, group in enumerate(groups):
            row = ri + 1
            ctk.CTkLabel(table, text=group, font=cell_font, anchor="w").grid(
                row=row, column=0, padx=8, pady=2, sticky="w")

            group_total = 0.0
            for ci, day in enumerate(days):
                secs = data.get(day, {}).get(group, 0.0)
                group_total += secs
                day_totals[day] += secs
                text = fmt(secs) if secs > 0 else "-"
                lbl = ctk.CTkLabel(table, text=text, font=cell_font, anchor="center",
                                   text_color="gray60" if secs == 0 else None)
                lbl.grid(row=row, column=ci + 1, padx=4, pady=2)
                self._dt_cell_labels[(ri, ci)] = lbl

            rt_lbl = ctk.CTkLabel(table, text=fmt(group_total), font=total_font,
                                  anchor="center")
            rt_lbl.grid(row=row, column=len(days) + 1, padx=8, pady=2)
            self._dt_row_total_labels[ri] = rt_lbl

        total_row = len(groups) + 1
        ctk.CTkLabel(table, text="Daily Total", font=total_font, anchor="w").grid(
            row=total_row, column=0, padx=8, pady=(4, 8), sticky="w")
        grand = 0.0
        for ci, day in enumerate(days):
            grand += day_totals[day]
            ct_lbl = ctk.CTkLabel(table, text=fmt(day_totals[day]), font=total_font,
                                  anchor="center")
            ct_lbl.grid(row=total_row, column=ci + 1, padx=4, pady=(4, 8))
            self._dt_col_total_labels[ci] = ct_lbl

        self._dt_grand_label = ctk.CTkLabel(
            table, text=fmt(grand), font=total_font, anchor="center")
        self._dt_grand_label.grid(
            row=total_row, column=len(days) + 1, padx=8, pady=(4, 8))

    def _rebuild_rounding_buttons(self) -> None:
        if not hasattr(self, "_rounding_frame"):
            return
        for child in self._rounding_frame.winfo_children():
            child.destroy()

        btn_font = ctk.CTkFont(size=11)
        rounding_options = [("Exact", 0), ("5m", 5), ("15m", 15), ("30m", 30)]
        for label, mins in reversed(rounding_options):
            is_active = self._round_minutes == mins
            ctk.CTkButton(
                self._rounding_frame, text=label, width=42, height=24, font=btn_font,
                fg_color="#2980b9" if is_active else "gray40",
                hover_color="#3498db" if is_active else "gray50",
                command=lambda m=mins: self._set_rounding(m),
            ).pack(side="right", padx=2)

        ctk.CTkLabel(self._rounding_frame, text="Round:", font=btn_font,
                     text_color="gray60").pack(side="right", padx=(0, 4))

    def _update_daily_values(self, days: list[str], groups: list[str],
                             data: dict[str, dict[str, float]]) -> None:
        rm = self._round_minutes
        fmt = lambda s: format_hm(s, rm)

        day_totals = {d: 0.0 for d in days}
        for ri, group in enumerate(groups):
            group_total = 0.0
            for ci, day in enumerate(days):
                secs = data.get(day, {}).get(group, 0.0)
                group_total += secs
                day_totals[day] += secs
                text = fmt(secs) if secs > 0 else "-"
                lbl = self._dt_cell_labels.get((ri, ci))
                if lbl:
                    lbl.configure(text=text,
                                  text_color="gray60" if secs == 0 else
                                  ("gray10", "gray90"))

            rt_lbl = self._dt_row_total_labels.get(ri)
            if rt_lbl:
                rt_lbl.configure(text=fmt(group_total))

        grand = 0.0
        for ci, day in enumerate(days):
            grand += day_totals[day]
            ct_lbl = self._dt_col_total_labels.get(ci)
            if ct_lbl:
                ct_lbl.configure(text=fmt(day_totals[day]))

        if self._dt_grand_label:
            self._dt_grand_label.configure(text=fmt(grand))

    # ── Charts ───────────────────────────────────────────────────

    def _render_charts(self, agg: dict[str, dict[str, float]]) -> None:
        for child in self._chart_frame.winfo_children():
            child.destroy()

        if not agg:
            ctk.CTkLabel(self._chart_frame, text="No data for this range.",
                         font=ctk.CTkFont(size=14)).pack(pady=20)
            return

        is_dark = ctk.get_appearance_mode().lower() == "dark"
        bg = "#2b2b2b" if is_dark else "#f0f0f0"
        fg = "#ffffff" if is_dark else "#000000"

        fig = Figure(figsize=(10, 4.5), dpi=100, facecolor=bg)

        ax1 = fig.add_subplot(121)
        ax1.set_facecolor(bg)
        projects = sorted(agg.keys(), key=lambda p: agg[p]["_total"], reverse=True)
        proj_seconds = [agg[p]["_total"] for p in projects]
        proj_labels = [f"{p}\n{format_hours(s)}" for p, s in zip(projects, proj_seconds)]
        colors = [_COLORS[i % len(_COLORS)] for i in range(len(projects))]

        wedges1, texts1 = ax1.pie(
            proj_seconds, labels=proj_labels, colors=colors,
            startangle=90, textprops={"fontsize": 8, "color": fg},
        )
        ax1.set_title("By Project", fontsize=12, fontweight="bold", color=fg, pad=12)

        ax2 = fig.add_subplot(122)
        ax2.set_facecolor(bg)
        act_labels_list = []
        act_seconds = []
        act_colors = []
        for ci, proj in enumerate(projects):
            activities = {k: v for k, v in agg[proj].items() if k != "_total"}
            for act, secs in sorted(activities.items(), key=lambda x: x[1], reverse=True):
                act_labels_list.append(f"{proj}: {act}\n{format_hours(secs)}")
                act_seconds.append(secs)
                act_colors.append(colors[ci])

        if act_seconds:
            wedges2, texts2 = ax2.pie(
                act_seconds, labels=act_labels_list, colors=act_colors,
                startangle=90, textprops={"fontsize": 7, "color": fg},
            )
        ax2.set_title("By Project + Activity", fontsize=12, fontweight="bold",
                       color=fg, pad=12)

        fig.tight_layout(pad=2.0)

        canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", pady=4)

    # ── Text breakdown ───────────────────────────────────────────

    def _text_structure_key(self, agg: dict) -> tuple:
        """Build a hashable key representing the current project/activity structure."""
        result = []
        for proj in sorted(agg.keys(), key=lambda p: agg[p]["_total"], reverse=True):
            activities = tuple(sorted(
                (k for k in agg[proj] if k != "_total"),
                key=lambda k: agg[proj][k], reverse=True))
            result.append((proj, activities))
        return tuple(result)

    def _build_text(self, agg: dict[str, dict[str, float]],
                    start: datetime, end: datetime) -> None:
        for child in self._text_frame.winfo_children():
            child.destroy()
        self._txt_proj_labels.clear()
        self._txt_act_labels.clear()
        self._txt_grand_label = None

        if not agg:
            return

        self._txt_structure = self._text_structure_key(agg)

        range_str = f"{start.strftime('%m/%d/%Y')} - {(end - timedelta(days=1)).strftime('%m/%d/%Y')}"
        if self._range_var.get() == "This Week":
            range_str = f"This Week ({range_str})"

        ctk.CTkLabel(self._text_frame, text=f"Breakdown: {range_str}",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     anchor="w").pack(fill="x", padx=8, pady=(8, 4))

        grand_total = sum(d["_total"] for d in agg.values())
        projects = sorted(agg.keys(), key=lambda p: agg[p]["_total"], reverse=True)

        for proj in projects:
            data = agg[proj]
            proj_total = data["_total"]
            pct = (proj_total / grand_total * 100) if grand_total > 0 else 0

            proj_frame = ctk.CTkFrame(self._text_frame, fg_color=("gray88", "gray20"),
                                       corner_radius=6)
            proj_frame.pack(fill="x", padx=8, pady=2)

            header = ctk.CTkLabel(
                proj_frame,
                text=f"  {proj}    {format_duration(proj_total)}  ({format_hours(proj_total)})    {pct:.1f}%",
                font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
            )
            header.pack(fill="x", padx=4, pady=(4, 0))
            self._txt_proj_labels[proj] = header

            activities = {k: v for k, v in data.items() if k != "_total"}
            for act, secs in sorted(activities.items(), key=lambda x: x[1], reverse=True):
                act_pct = (secs / proj_total * 100) if proj_total > 0 else 0
                act_lbl = ctk.CTkLabel(
                    proj_frame,
                    text=f"      {act}    {format_duration(secs)}  ({format_hours(secs)})    {act_pct:.0f}%",
                    font=ctk.CTkFont(size=12), anchor="w", text_color="gray60",
                )
                act_lbl.pack(fill="x", padx=4)
                self._txt_act_labels[(proj, act)] = act_lbl

            ctk.CTkFrame(proj_frame, height=4, fg_color="transparent").pack()

        self._txt_grand_label = ctk.CTkLabel(
            self._text_frame,
            text=f"  Total Work: {format_duration(grand_total)}  ({format_hours(grand_total)})",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        )
        self._txt_grand_label.pack(fill="x", padx=8, pady=(8, 12))

    def _update_text_values(self, agg: dict[str, dict[str, float]],
                            start: datetime, end: datetime) -> None:
        new_structure = self._text_structure_key(agg)
        if new_structure != self._txt_structure:
            self._build_text(agg, start, end)
            return

        grand_total = sum(d["_total"] for d in agg.values())

        for proj, data in agg.items():
            proj_total = data["_total"]
            pct = (proj_total / grand_total * 100) if grand_total > 0 else 0

            lbl = self._txt_proj_labels.get(proj)
            if lbl:
                lbl.configure(
                    text=f"  {proj}    {format_duration(proj_total)}  ({format_hours(proj_total)})    {pct:.1f}%")

            activities = {k: v for k, v in data.items() if k != "_total"}
            for act, secs in activities.items():
                act_pct = (secs / proj_total * 100) if proj_total > 0 else 0
                act_lbl = self._txt_act_labels.get((proj, act))
                if act_lbl:
                    act_lbl.configure(
                        text=f"      {act}    {format_duration(secs)}  ({format_hours(secs)})    {act_pct:.0f}%")

        if self._txt_grand_label:
            self._txt_grand_label.configure(
                text=f"  Total Work: {format_duration(grand_total)}  ({format_hours(grand_total)})")
