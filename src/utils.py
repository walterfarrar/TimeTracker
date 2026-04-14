from __future__ import annotations

import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Return the directory where the application lives (for config files)."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
        # PyInstaller 6+ onedir: bundled data lives next to the runtime under _internal/
        internal = base / "_internal"
        if internal.is_dir():
            return internal
        return base
    return Path(__file__).resolve().parent.parent


def get_config_dir() -> Path:
    return get_app_dir() / "config"


def get_buttons_path() -> Path:
    return get_config_dir() / "buttons.json"


def get_settings_path() -> Path:
    return get_config_dir() / "settings.json"


def get_app_icon_png_path() -> Path:
    return get_app_dir() / "assets" / "icons" / "app.png"
