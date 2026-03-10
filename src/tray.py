from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw

if TYPE_CHECKING:
    from .app import TimeTrackerApp


def _create_icon_image(size: int = 64) -> Image.Image:
    """Generate a simple clock-like icon programmatically."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 4
    draw.ellipse([margin, margin, size - margin, size - margin],
                 fill="#2980b9", outline="#ecf0f1", width=2)
    cx, cy = size // 2, size // 2
    # Hour hand
    draw.line([cx, cy, cx, cy - 16], fill="#ecf0f1", width=3)
    # Minute hand
    draw.line([cx, cy, cx + 12, cy - 8], fill="#ecf0f1", width=2)
    return img


class TrayManager:
    """Manages the system tray icon using pystray."""

    def __init__(self, app: TimeTrackerApp):
        self._app = app
        self._icon = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        import pystray

        image = _create_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Show", self._show_window, default=True),
            pystray.MenuItem("End Day", self._end_day),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._quit),
        )
        self._icon = pystray.Icon("TimeTracker", image, "Time Tracker", menu)
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def update_tooltip(self, text: str) -> None:
        if self._icon:
            self._icon.title = text

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()

    def _show_window(self, icon=None, item=None) -> None:
        self._app.after(0, self._app.deiconify)
        self._app.after(0, self._app.lift)

    def _end_day(self, icon=None, item=None) -> None:
        self._app.after(0, self._app._on_end_day)

    def _quit(self, icon=None, item=None) -> None:
        self.stop()
        self._app.after(0, self._app._on_close)
