from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from .models import ButtonConfig, ButtonDef, ButtonGroup


class Sidebar(ctk.CTkFrame):
    """Right-side panel with special buttons and project group buttons."""

    def __init__(self, master: ctk.CTkBaseClass,
                 on_project_click: Callable[[str, str], None],
                 on_end_day: Callable[[], None],
                 on_refresh: Callable[[], None],
                 on_settings: Callable[[], None],
                 **kwargs):
        super().__init__(master, width=260, **kwargs)
        self._on_project_click = on_project_click
        self._on_end_day = on_end_day
        self._on_refresh = on_refresh
        self._on_settings = on_settings

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_special_buttons()
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        self._scroll.grid_columnconfigure(0, weight=1)

        self._build_footer()

    def _build_special_buttons(self) -> None:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="ew", padx=2, pady=(4, 2))
        frame.grid_columnconfigure((0, 1), weight=1)

        _btn_font = ctk.CTkFont(size=12)
        ctk.CTkButton(frame, text="End Day", fg_color="#c0392b",
                       hover_color="#e74c3c", command=self._on_end_day,
                       height=28, font=_btn_font).grid(
            row=0, column=0, padx=1, pady=1, sticky="ew")
        ctk.CTkButton(frame, text="Refresh", fg_color="#2980b9",
                       hover_color="#3498db", command=self._on_refresh,
                       height=28, font=_btn_font).grid(
            row=0, column=1, padx=1, pady=1, sticky="ew")

    def _build_footer(self) -> None:
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=2, column=0, sticky="ew", padx=2, pady=(0, 4))
        frame.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(frame, text="Settings", fg_color="gray40",
                       hover_color="gray50", command=self._on_settings,
                       height=26, font=ctk.CTkFont(size=12)).grid(
            row=0, column=0, padx=1, pady=1, sticky="ew"
        )

    def load_buttons(self, config: ButtonConfig) -> None:
        for child in self._scroll.winfo_children():
            child.destroy()

        for group in config.groups:
            self._add_group(group)

    def _add_group(self, group: ButtonGroup) -> None:
        group_frame = ctk.CTkFrame(self._scroll, fg_color=("gray88", "gray20"),
                                   corner_radius=6)
        group_frame.pack(fill="x", padx=1, pady=(0, 3))
        group_frame.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(group_frame, text=group.name,
                           font=ctk.CTkFont(size=11, weight="bold"),
                           text_color="gray60", anchor="w")
        lbl.grid(row=0, column=0, columnspan=3, padx=5, pady=(3, 1), sticky="w")

        btn_frame = ctk.CTkFrame(group_frame, fg_color="transparent")
        btn_frame.grid(row=1, column=0, sticky="ew", padx=3, pady=(0, 4))

        cols = min(len(group.buttons), 3)
        for c in range(cols):
            btn_frame.grid_columnconfigure(c, weight=1)

        for idx, bdef in enumerate(group.buttons):
            r, c = divmod(idx, 3)
            btn = ctk.CTkButton(
                btn_frame, text=bdef.label, height=26,
                font=ctk.CTkFont(size=11),
                command=lambda b=bdef: self._on_project_click(
                    b.project, b.activity),
            )
            btn.grid(row=r, column=c, padx=1, pady=1, sticky="ew")
