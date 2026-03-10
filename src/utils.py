from __future__ import annotations

import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Return the directory where the application lives (for config files)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def get_config_dir() -> Path:
    return get_app_dir() / "config"


def get_buttons_path() -> Path:
    return get_config_dir() / "buttons.json"


def get_settings_path() -> Path:
    return get_config_dir() / "settings.json"
