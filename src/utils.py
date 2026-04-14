from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Return the directory where the application lives (bundled assets, defaults)."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
        internal = base / "_internal"
        if internal.is_dir():
            return internal
        return base
    return Path(__file__).resolve().parent.parent


def get_user_data_dir() -> Path:
    """Persistent per-user directory that survives rebuilds and git operations."""
    d = Path.home() / ".timetracker"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _default_config_dir() -> Path:
    """Bundled/repo config directory (read-only defaults)."""
    return get_app_dir() / "config"


def _ensure_user_config(filename: str) -> Path:
    """Return the user-local config path, seeding from bundled defaults on first run."""
    user_path = get_user_data_dir() / filename
    if not user_path.exists():
        default = _default_config_dir() / filename
        if default.exists():
            shutil.copy2(default, user_path)
    return user_path


def get_buttons_path() -> Path:
    return _ensure_user_config("buttons.json")


def get_settings_path() -> Path:
    return _ensure_user_config("settings.json")


def get_app_icon_png_path() -> Path:
    return get_app_dir() / "assets" / "icons" / "app.png"
