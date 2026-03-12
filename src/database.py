from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from .models import TimeEntry


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_tables()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_tables(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                project TEXT NOT NULL,
                activity TEXT DEFAULT ''
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entries_timestamp
            ON entries (timestamp)
        """)
        self.conn.commit()

    def add_entry(self, project: str, activity: str = "",
                  timestamp: Optional[float] = None) -> TimeEntry:
        ts = timestamp if timestamp is not None else datetime.now().timestamp()
        cur = self.conn.execute(
            "INSERT INTO entries (timestamp, project, activity) VALUES (?, ?, ?)",
            (ts, project, activity),
        )
        self.conn.commit()
        return TimeEntry(id=cur.lastrowid, timestamp=ts, project=project,
                         activity=activity)

    def update_entry(self, entry_id: int, project: str, activity: str = "",
                     timestamp: Optional[float] = None) -> None:
        if timestamp is not None:
            self.conn.execute(
                "UPDATE entries SET project=?, activity=?, timestamp=? WHERE id=?",
                (project, activity, timestamp, entry_id),
            )
        else:
            self.conn.execute(
                "UPDATE entries SET project=?, activity=? WHERE id=?",
                (project, activity, entry_id),
            )
        self.conn.commit()

    def delete_entry(self, entry_id: int) -> None:
        self.conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        self.conn.commit()

    def _row_to_entry(self, row: sqlite3.Row) -> TimeEntry:
        return TimeEntry(
            id=row["id"],
            timestamp=row["timestamp"],
            project=row["project"],
            activity=row["activity"],
        )

    def get_entries_for_date(self, date: datetime) -> list[TimeEntry]:
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        rows = self.conn.execute(
            "SELECT * FROM entries WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
            (start.timestamp(), end.timestamp()),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def get_entries_for_week(self, ref_date: datetime) -> list[TimeEntry]:
        """Get all entries for the ISO week containing ref_date."""
        weekday = ref_date.weekday()  # Monday=0
        monday = ref_date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=weekday)
        sunday_end = monday + timedelta(days=7)
        rows = self.conn.execute(
            "SELECT * FROM entries WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
            (monday.timestamp(), sunday_end.timestamp()),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def get_entries_range(self, start: datetime, end: datetime) -> list[TimeEntry]:
        rows = self.conn.execute(
            "SELECT * FROM entries WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
            (start.timestamp(), end.timestamp()),
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def get_last_entry(self) -> Optional[TimeEntry]:
        row = self.conn.execute(
            "SELECT * FROM entries ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def get_date_bounds(self) -> tuple[Optional[float], Optional[float]]:
        """Return (earliest_timestamp, latest_timestamp) or (None, None) if empty."""
        row = self.conn.execute(
            "SELECT MIN(timestamp), MAX(timestamp) FROM entries"
        ).fetchone()
        if row and row[0] is not None:
            return row[0], row[1]
        return None, None

    def get_distinct_projects(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT project FROM entries WHERE project != '' ORDER BY project"
        ).fetchall()
        return [r[0] for r in rows]

    def get_distinct_activities(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT activity FROM entries WHERE activity != '' ORDER BY activity"
        ).fetchall()
        return [r[0] for r in rows]

    def has_entries_in_range(self, start: datetime, end: datetime) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM entries WHERE timestamp >= ? AND timestamp < ? LIMIT 1",
            (start.timestamp(), end.timestamp()),
        ).fetchone()
        return row is not None

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
