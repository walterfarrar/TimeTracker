from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk


class AutocompleteCombobox(ctk.CTkFrame):
    """Compact inline combobox with autocomplete filtering for table cells."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        values: list[str] | None = None,
        initial_value: str = "",
        on_commit: Optional[Callable[[str], None]] = None,
        width: int = 150,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("corner_radius", 0)
        super().__init__(master, **kwargs)

        self._all_values: list[str] = list(values or [])
        self._on_commit = on_commit
        self._original_value = initial_value
        self._committed_value = initial_value
        self._dropdown: Optional[tk.Toplevel] = None
        self._suppressing_blur = False
        self._arrow_pressed = False
        self._global_click_bound = False

        self.grid_columnconfigure(0, weight=1)

        self._var = ctk.StringVar(value=initial_value)
        self._entry = ctk.CTkEntry(
            self,
            textvariable=self._var,
            width=width - 22,
            height=22,
            font=ctk.CTkFont(size=12),
            border_width=1,
            corner_radius=3,
        )
        self._entry.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        self._arrow_btn = ctk.CTkButton(
            self,
            text="\u25bc",
            width=20,
            height=22,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            hover_color=("gray75", "gray30"),
            text_color=("gray40", "gray60"),
            corner_radius=3,
            command=self._on_arrow_click,
        )
        self._arrow_btn.grid(row=0, column=1, padx=0, pady=0)

        self._entry.bind("<KeyRelease>", self._on_key_release)
        self._entry.bind("<Return>", self._on_enter)
        self._entry.bind("<Escape>", self._on_escape)
        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        self._entry.bind("<Down>", self._on_down_key)

    def set_values(self, values: list[str]) -> None:
        self._all_values = list(values)

    def get(self) -> str:
        return self._var.get().strip()

    def set(self, value: str) -> None:
        self._var.set(value)
        self._original_value = value
        self._committed_value = value

    def _on_focus_in(self, event=None) -> None:
        self._original_value = self._var.get().strip()

    def _on_focus_out(self, event=None) -> None:
        if self._suppressing_blur:
            return
        self.after(120, self._deferred_blur_commit)

    def _deferred_blur_commit(self) -> None:
        if self._suppressing_blur:
            self._suppressing_blur = False
            return
        focus = self.focus_get()
        if focus and (focus is self._entry or self._is_child(focus)):
            return
        self._hide_dropdown()
        self._commit()

    def _is_child(self, widget) -> bool:
        try:
            parent = widget.master
            while parent:
                if parent is self:
                    return True
                parent = parent.master
        except (AttributeError, tk.TclError):
            pass
        return False

    def _on_enter(self, event=None) -> None:
        self._hide_dropdown()
        self._commit()
        return "break"

    def _on_escape(self, event=None) -> None:
        self._var.set(self._original_value)
        self._hide_dropdown()
        return "break"

    def _on_key_release(self, event=None) -> None:
        if event and event.keysym in ("Return", "Escape", "Down", "Up",
                                       "Left", "Right", "Shift_L", "Shift_R",
                                       "Control_L", "Control_R", "Alt_L",
                                       "Alt_R", "Tab"):
            return
        text = self._var.get().strip()
        if text:
            filtered = [v for v in self._all_values
                        if text.lower() in v.lower()]
        else:
            filtered = list(self._all_values)
        if filtered:
            self._show_dropdown(filtered)
        else:
            self._hide_dropdown()

    def _on_down_key(self, event=None) -> None:
        if self._dropdown and self._dropdown.winfo_exists():
            self._listbox.focus_set()
            if self._listbox.size() > 0:
                self._listbox.selection_set(0)
                self._listbox.activate(0)
        else:
            self._show_dropdown(self._all_values)
        return "break"

    def _on_arrow_click(self) -> None:
        self._arrow_pressed = True
        self._suppressing_blur = True
        if self._dropdown and self._dropdown.winfo_exists():
            self._hide_dropdown()
        else:
            self._show_dropdown(self._all_values)
        self._entry.focus_set()
        self.after(150, self._clear_arrow_flag)

    def _clear_arrow_flag(self) -> None:
        self._arrow_pressed = False
        self._suppressing_blur = False

    def _show_dropdown(self, values: list[str]) -> None:
        if not values:
            self._hide_dropdown()
            return

        if self._dropdown and self._dropdown.winfo_exists():
            self._listbox.delete(0, tk.END)
            for v in values:
                self._listbox.insert(tk.END, v)
            self._update_dropdown_geometry(values)
            return

        self._dropdown = tk.Toplevel(self)
        self._dropdown.withdraw()
        self._dropdown.overrideredirect(True)
        self._dropdown.attributes("-topmost", True)

        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            bg = "#2b2b2b"
            fg = "#dcdcdc"
            sel_bg = "#3a5f8f"
            sel_fg = "#ffffff"
        else:
            bg = "#ffffff"
            fg = "#1a1a1a"
            sel_bg = "#0078d4"
            sel_fg = "#ffffff"

        frame = tk.Frame(self._dropdown, bg=bg, bd=1, relief="solid")
        frame.pack(fill="both", expand=True)

        self._listbox = tk.Listbox(
            frame,
            bg=bg,
            fg=fg,
            selectbackground=sel_bg,
            selectforeground=sel_fg,
            font=("Segoe UI", 10),
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            exportselection=False,
        )
        self._listbox.pack(fill="both", expand=True, padx=1, pady=1)

        for v in values:
            self._listbox.insert(tk.END, v)

        self._listbox.bind("<ButtonRelease-1>", self._on_listbox_click)
        self._listbox.bind("<Return>", self._on_listbox_enter)
        self._listbox.bind("<Escape>", self._on_escape)
        self._listbox.bind("<FocusOut>", self._on_listbox_focus_out)

        self._update_dropdown_geometry(values)
        self._dropdown.deiconify()
        self._ensure_global_click_bound()

    def _update_dropdown_geometry(self, values: list[str]) -> None:
        if not self._dropdown:
            return
        self._entry.update_idletasks()
        x = self._entry.winfo_rootx()
        y = self._entry.winfo_rooty() + self._entry.winfo_height()
        w = self._entry.winfo_width() + self._arrow_btn.winfo_width()
        row_h = 20
        h = min(len(values), 8) * row_h + 4
        self._dropdown.geometry(f"{w}x{h}+{x}+{y}")

    def _on_listbox_click(self, event=None) -> None:
        sel = self._listbox.curselection()
        if sel:
            value = self._listbox.get(sel[0])
            self._var.set(value)
            self._hide_dropdown()
            self._commit()
            self._entry.focus_set()

    def _on_listbox_enter(self, event=None) -> None:
        self._on_listbox_click()
        return "break"

    def _on_listbox_focus_out(self, event=None) -> None:
        self.after(100, self._check_listbox_focus)

    def _check_listbox_focus(self) -> None:
        focus = self.focus_get()
        if focus is self._entry:
            return
        if self._dropdown and self._dropdown.winfo_exists():
            try:
                if focus and str(focus).startswith(str(self._dropdown)):
                    return
            except tk.TclError:
                pass
        self._hide_dropdown()

    def _hide_dropdown(self) -> None:
        if self._dropdown and self._dropdown.winfo_exists():
            self._dropdown.destroy()
        self._dropdown = None

    def _ensure_global_click_bound(self) -> None:
        if not self._global_click_bound:
            self.winfo_toplevel().bind_all(
                "<Button-1>", self._on_global_click, add=True
            )
            self._global_click_bound = True

    def _on_global_click(self, event) -> None:
        if not self._dropdown or not self._dropdown.winfo_exists():
            return
        widget = event.widget
        try:
            wstr = str(widget)
            if widget is self._entry or widget is self._arrow_btn:
                return
            if wstr.startswith(str(self._entry)):
                return
            if wstr.startswith(str(self._arrow_btn)):
                return
            if wstr.startswith(str(self._dropdown)):
                return
        except (tk.TclError, RuntimeError):
            pass
        self._hide_dropdown()

    def _commit(self) -> None:
        new_val = self._var.get().strip()
        if new_val != self._committed_value:
            self._committed_value = new_val
            self._original_value = new_val
            if self._on_commit:
                self._on_commit(new_val)
        else:
            self._original_value = new_val

    def destroy(self) -> None:
        self._hide_dropdown()
        super().destroy()
