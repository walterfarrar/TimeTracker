from __future__ import annotations

from copy import deepcopy

import customtkinter as ctk

from .models import AppSettings, ButtonConfig, ButtonDef, ButtonGroup


class SettingsDialog(ctk.CTkToplevel):
    """Full settings dialog with tabs for General and Buttons."""

    def __init__(self, master, settings: AppSettings, button_config: ButtonConfig):
        super().__init__(master)
        self.result = None
        self.new_settings = deepcopy(settings)
        self.new_button_config = deepcopy(button_config)

        self.title("Settings")
        self.geometry("650x560")
        self.minsize(600, 500)
        self.transient(master)
        self.grab_set()

        self._build_ui()
        self.after(100, self.lift)

    def _build_ui(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._tabview = ctk.CTkTabview(self)
        self._tabview.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 0))

        self._tab_general = self._tabview.add("General")
        self._tab_buttons = self._tabview.add("Buttons")

        self._build_general_tab()
        self._build_buttons_tab()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=8)
        btn_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btn_frame, text="Save", fg_color="#27ae60",
                       hover_color="#2ecc71", command=self._save).grid(
            row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(btn_frame, text="Cancel", fg_color="gray40",
                       hover_color="gray50", command=self._cancel).grid(
            row=0, column=1, padx=4, sticky="ew")

    # ── General Tab ──────────────────────────────────────────────

    def _build_general_tab(self) -> None:
        tab = self._tab_general
        tab.grid_columnconfigure(1, weight=1)
        lf = ctk.CTkFont(size=12)
        row = 0

        ctk.CTkLabel(tab, text="Hours per day:", font=lf, anchor="w").grid(
            row=row, column=0, padx=8, pady=6, sticky="w")
        self._hours_var = ctk.StringVar(value=str(self.new_settings.hours_per_day))
        ctk.CTkEntry(tab, textvariable=self._hours_var, width=80).grid(
            row=row, column=1, padx=8, pady=6, sticky="w")
        row += 1

        ctk.CTkLabel(tab, text="Working days this week:", font=lf, anchor="w").grid(
            row=row, column=0, padx=8, pady=6, sticky="w")
        self._days_var = ctk.StringVar(
            value=str(self.new_settings.working_days_this_week))
        ctk.CTkEntry(tab, textvariable=self._days_var, width=80).grid(
            row=row, column=1, padx=8, pady=6, sticky="w")
        row += 1

        ctk.CTkLabel(tab, text="Break projects (comma-separated):", font=lf,
                     anchor="w").grid(row=row, column=0, padx=8, pady=6, sticky="w")
        self._breaks_var = ctk.StringVar(
            value=", ".join(self.new_settings.break_projects))
        ctk.CTkEntry(tab, textvariable=self._breaks_var, width=200).grid(
            row=row, column=1, padx=8, pady=6, sticky="w")
        row += 1

        ctk.CTkLabel(tab, text="Theme:", font=lf, anchor="w").grid(
            row=row, column=0, padx=8, pady=6, sticky="w")
        self._theme_var = ctk.StringVar(value=self.new_settings.theme)
        ctk.CTkSegmentedButton(tab, values=["dark", "light", "system"],
                                variable=self._theme_var).grid(
            row=row, column=1, padx=8, pady=6, sticky="w")

    # ── Buttons Tab ──────────────────────────────────────────────

    def _build_buttons_tab(self) -> None:
        tab = self._tab_buttons
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.grid(row=0, column=0, sticky="nsew")
        top.grid_rowconfigure(0, weight=1)
        top.grid_columnconfigure(0, weight=1)

        self._btn_scroll = ctk.CTkScrollableFrame(top, fg_color="transparent")
        self._btn_scroll.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self._btn_scroll.grid_columnconfigure(0, weight=1)

        actions = ctk.CTkFrame(tab, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        actions.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(actions, text="+ Add Group", height=30,
                       command=self._add_group).grid(
            row=0, column=0, padx=4, sticky="ew")

        self._render_button_groups()

    def _render_button_groups(self) -> None:
        for child in self._btn_scroll.winfo_children():
            child.destroy()

        for g_idx, group in enumerate(self.new_button_config.groups):
            self._render_one_group(g_idx, group)

    def _render_one_group(self, g_idx: int, group: ButtonGroup) -> None:
        gf = ctk.CTkFrame(self._btn_scroll, fg_color=("gray88", "gray20"),
                          corner_radius=8)
        gf.pack(fill="x", padx=2, pady=(0, 8))
        gf.grid_columnconfigure(1, weight=1)

        header = ctk.CTkFrame(gf, fg_color="transparent")
        header.pack(fill="x", padx=6, pady=(6, 2))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="Group:", font=ctk.CTkFont(size=11),
                     anchor="w").grid(row=0, column=0, padx=(0, 4))
        name_var = ctk.StringVar(value=group.name)
        name_entry = ctk.CTkEntry(header, textvariable=name_var, width=140)
        name_entry.grid(row=0, column=1, sticky="w")
        name_var.trace_add("write", lambda *_, v=name_var, i=g_idx:
                           self._update_group_name(i, v.get()))

        ctk.CTkButton(header, text="Delete Group", width=90, height=24,
                       fg_color="#c0392b", hover_color="#e74c3c",
                       font=ctk.CTkFont(size=11),
                       command=lambda i=g_idx: self._delete_group(i)).grid(
            row=0, column=2, padx=(8, 0))

        for b_idx, bdef in enumerate(group.buttons):
            self._render_one_button(gf, g_idx, b_idx, bdef)

        add_btn = ctk.CTkButton(gf, text="+ Add Button", height=26,
                                 font=ctk.CTkFont(size=11), fg_color="gray40",
                                 hover_color="gray50",
                                 command=lambda i=g_idx: self._add_button(i))
        add_btn.pack(padx=6, pady=(2, 6))

    def _render_one_button(self, parent: ctk.CTkFrame, g_idx: int,
                           b_idx: int, bdef: ButtonDef) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=1)
        f = ctk.CTkFont(size=11)

        fields = [
            ("Label", bdef.label, 90),
            ("Project", bdef.project, 100),
            ("Activity", bdef.activity, 90),
            ("Detail", bdef.detail, 80),
        ]
        vars_: list[ctk.StringVar] = []
        for col, (placeholder, val, w) in enumerate(fields):
            var = ctk.StringVar(value=val)
            e = ctk.CTkEntry(row, textvariable=var, width=w, font=f,
                              placeholder_text=placeholder)
            e.pack(side="left", padx=1)
            vars_.append(var)

        for i, field_name in enumerate(["label", "project", "activity", "detail"]):
            vars_[i].trace_add("write", lambda *_, gi=g_idx, bi=b_idx,
                               fn=field_name, v=vars_[i]:
                               self._update_button_field(gi, bi, fn, v.get()))

        ctk.CTkButton(row, text="X", width=28, height=24, fg_color="#c0392b",
                       hover_color="#e74c3c", font=ctk.CTkFont(size=11),
                       command=lambda gi=g_idx, bi=b_idx:
                       self._delete_button(gi, bi)).pack(side="left", padx=(4, 0))

    # ── Mutation helpers ─────────────────────────────────────────

    def _update_group_name(self, g_idx: int, name: str) -> None:
        self.new_button_config.groups[g_idx].name = name

    def _update_button_field(self, g_idx: int, b_idx: int,
                             field: str, value: str) -> None:
        setattr(self.new_button_config.groups[g_idx].buttons[b_idx], field, value)

    def _add_group(self) -> None:
        self.new_button_config.groups.append(
            ButtonGroup(name="NEW_GROUP", buttons=[
                ButtonDef(label="New", project="NEW_PROJECT"),
            ])
        )
        self._render_button_groups()

    def _delete_group(self, g_idx: int) -> None:
        del self.new_button_config.groups[g_idx]
        self._render_button_groups()

    def _add_button(self, g_idx: int) -> None:
        group = self.new_button_config.groups[g_idx]
        group.buttons.append(ButtonDef(label="New", project=group.name))
        self._render_button_groups()

    def _delete_button(self, g_idx: int, b_idx: int) -> None:
        del self.new_button_config.groups[g_idx].buttons[b_idx]
        self._render_button_groups()

    # ── Save / Cancel ────────────────────────────────────────────

    def _save(self) -> None:
        try:
            self.new_settings.hours_per_day = float(self._hours_var.get())
        except ValueError:
            pass
        try:
            self.new_settings.working_days_this_week = float(self._days_var.get())
        except ValueError:
            pass
        raw_breaks = self._breaks_var.get()
        self.new_settings.break_projects = [
            b.strip() for b in raw_breaks.split(",") if b.strip()
        ]
        self.new_settings.theme = self._theme_var.get()
        self.result = "save"
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()
