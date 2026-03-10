# Time Tracker

A desktop time tracking application with a button-driven workflow.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

## Usage

1. **Click a project button** in the sidebar to log a timestamp with that project/activity.
2. The log table shows today's entries with duration and running totals.
3. The header shows time worked today (minus breaks) and time remaining this week.
4. **Double-click** any entry to edit or delete it.
5. **End Day** marks the end of your workday.
6. **Settings** lets you add/edit/remove button groups, set hours per day, working days this week, break projects, and theme.

## Keyboard Shortcuts

- `Ctrl+E` — Export today's entries to CSV
- `Ctrl+Shift+E` — Export this week's entries to CSV

## System Tray

Closing the window minimizes to the system tray. Right-click the tray icon for options including Show, End Day, and Exit.

## Configuration

- `config/buttons.json` — Sidebar button definitions
- `config/settings.json` — App settings (hours/day, theme, etc.)

Both can be edited through the in-app Settings dialog.

## Building a Standalone Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name TimeTracker --add-data "config;config" main.py
```

The executable will be in the `dist/` folder.
