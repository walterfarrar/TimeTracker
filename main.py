"""Time Tracker - Desktop time tracking application."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.app import TimeTrackerApp


def main():
    app = TimeTrackerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
