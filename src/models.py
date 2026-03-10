from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class TimeEntry:
    id: Optional[int]
    timestamp: float  # Unix epoch
    project: str
    activity: str = ""

    @property
    def dt(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)

    @property
    def date_str(self) -> str:
        return self.dt.strftime("%m/%d/%Y")

    @property
    def time_str(self) -> str:
        return self.dt.strftime("%I:%M:%S %p")


@dataclass
class ButtonDef:
    label: str
    project: str
    activity: str = ""

    def to_dict(self) -> dict:
        d = {"label": self.label, "project": self.project}
        if self.activity:
            d["activity"] = self.activity
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ButtonDef:
        return cls(
            label=d["label"],
            project=d["project"],
            activity=d.get("activity", ""),
        )


@dataclass
class ButtonGroup:
    name: str
    buttons: list[ButtonDef] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "buttons": [b.to_dict() for b in self.buttons],
        }

    @classmethod
    def from_dict(cls, d: dict) -> ButtonGroup:
        return cls(
            name=d["name"],
            buttons=[ButtonDef.from_dict(b) for b in d.get("buttons", [])],
        )


@dataclass
class ButtonConfig:
    groups: list[ButtonGroup] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"groups": [g.to_dict() for g in self.groups]}

    @classmethod
    def from_dict(cls, d: dict) -> ButtonConfig:
        return cls(groups=[ButtonGroup.from_dict(g) for g in d.get("groups", [])])

    def project_to_group_map(self) -> dict[str, str]:
        """Build a mapping from project name to group name.

        If a project appears in multiple groups, the first group wins.
        """
        mapping: dict[str, str] = {}
        for group in self.groups:
            for btn in group.buttons:
                if btn.project not in mapping:
                    mapping[btn.project] = group.name
        return mapping

    @classmethod
    def load(cls, path: str | Path) -> ButtonConfig:
        path = Path(path)
        if path.exists():
            with open(path, "r") as f:
                return cls.from_dict(json.load(f))
        return cls()

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


@dataclass
class AppSettings:
    hours_per_day: float = 8.0
    working_days_this_week: float = 5.0
    break_projects: list[str] = field(default_factory=lambda: ["BREAK"])
    theme: str = "dark"
    window_width: int = 1200
    window_height: int = 700
    window_x: int | None = None
    window_y: int | None = None
    db_path: str = ""

    def effective_db_path(self) -> str:
        if self.db_path:
            return self.db_path
        home = Path.home() / ".timetracker"
        home.mkdir(parents=True, exist_ok=True)
        return str(home / "timetracker.db")

    def to_dict(self) -> dict:
        return {
            "hours_per_day": self.hours_per_day,
            "working_days_this_week": self.working_days_this_week,
            "break_projects": self.break_projects,
            "theme": self.theme,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "window_x": self.window_x,
            "window_y": self.window_y,
            "db_path": self.db_path,
        }

    @classmethod
    def from_dict(cls, d: dict) -> AppSettings:
        return cls(
            hours_per_day=d.get("hours_per_day", 8.0),
            working_days_this_week=d.get("working_days_this_week", 5.0),
            break_projects=d.get("break_projects", ["BREAK"]),
            theme=d.get("theme", "dark"),
            window_width=d.get("window_width", 1200),
            window_height=d.get("window_height", 700),
            window_x=d.get("window_x"),
            window_y=d.get("window_y"),
            db_path=d.get("db_path", ""),
        )

    @classmethod
    def load(cls, path: str | Path) -> AppSettings:
        path = Path(path)
        if path.exists():
            with open(path, "r") as f:
                return cls.from_dict(json.load(f))
        return cls()

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
