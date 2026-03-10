from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from .models import TimeEntry


def format_duration(seconds: float) -> str:
    """Format seconds as H:MM:SS."""
    negative = seconds < 0
    seconds = abs(seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    sign = "-" if negative else ""
    return f"{sign}{h}:{m:02d}:{s:02d}"


def compute_durations(entries: list[TimeEntry]) -> list[Optional[float]]:
    """Compute how long was spent on each entry's project.

    Duration for entry i = entry[i+1].timestamp - entry[i].timestamp,
    i.e. the time spent working on entry i's project before the next
    entry arrived. The last entry has no duration yet (None).
    """
    durations: list[Optional[float]] = []
    for i, entry in enumerate(entries):
        if i < len(entries) - 1:
            durations.append(entries[i + 1].timestamp - entry.timestamp)
        else:
            durations.append(None)
    return durations


def compute_running_totals(durations: list[Optional[float]]) -> list[Optional[float]]:
    """Compute running cumulative total of durations for the day."""
    totals: list[Optional[float]] = []
    cumulative = 0.0
    for d in durations:
        if d is None:
            totals.append(None)
        else:
            cumulative += d
            totals.append(cumulative)
    return totals


def compute_work_time(entries: list[TimeEntry], durations: list[Optional[float]],
                      break_projects: list[str]) -> float:
    """Total seconds worked today, excluding break entries.

    Duration[i] is the time spent on entry[i]'s project, so we
    exclude it when entry[i] is a break project.
    """
    total = 0.0
    for entry, dur in zip(entries, durations):
        if dur is not None and entry.project not in break_projects:
            total += dur
    return total


def compute_week_work_time(all_week_entries: list[TimeEntry],
                           break_projects: list[str]) -> float:
    """Total seconds worked this week across all days, excluding breaks."""
    if not all_week_entries:
        return 0.0

    by_date: dict[str, list[TimeEntry]] = {}
    for entry in all_week_entries:
        by_date.setdefault(entry.date_str, []).append(entry)

    total = 0.0
    for date_entries in by_date.values():
        durations = compute_durations(date_entries)
        total += compute_work_time(date_entries, durations, break_projects)
    return total


def compute_time_remaining(week_work_seconds: float,
                           working_days: float,
                           hours_per_day: float) -> float:
    """Seconds remaining to work this week."""
    target = working_days * hours_per_day * 3600
    return target - week_work_seconds


def aggregate_time(entries: list[TimeEntry],
                   break_projects: list[str]) -> dict[str, dict[str, float]]:
    """Aggregate time by project, then by activity within each project.

    Returns {project: {"_total": secs, activity1: secs, activity2: secs, ...}}.
    Excludes break projects and END_OF_DAY.
    Processes entries per-day so durations don't span across days.
    """
    skip = set(break_projects) | {"END_OF_DAY"}

    by_date: dict[str, list[TimeEntry]] = {}
    for entry in entries:
        by_date.setdefault(entry.date_str, []).append(entry)

    result: dict[str, dict[str, float]] = {}

    for date_entries in by_date.values():
        durations = compute_durations(date_entries)
        for entry, dur in zip(date_entries, durations):
            if dur is None or entry.project in skip:
                continue
            proj = entry.project
            act = entry.activity or "(none)"
            if proj not in result:
                result[proj] = {"_total": 0.0}
            result[proj]["_total"] += dur
            result[proj][act] = result[proj].get(act, 0.0) + dur

    return result


def aggregate_by_day_and_group(
    entries: list[TimeEntry],
    break_projects: list[str],
    project_to_group: dict[str, str],
) -> tuple[list[str], list[str], dict[str, dict[str, float]]]:
    """Aggregate work time by day-of-week and group.

    Returns (day_labels, group_names, data) where:
      day_labels = sorted list of date strings that had entries
      group_names = sorted list of unique group names
      data = {day_label: {group_name: seconds, ...}}
    """
    skip = set(break_projects) | {"END_OF_DAY"}

    by_date: dict[str, list[TimeEntry]] = {}
    for entry in entries:
        by_date.setdefault(entry.date_str, []).append(entry)

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    data: dict[str, dict[str, float]] = {}
    day_order: dict[str, datetime] = {}
    all_groups: set[str] = set()

    for date_str, date_entries in by_date.items():
        durations = compute_durations(date_entries)
        dt = date_entries[0].dt
        day_label = f"{day_names[dt.weekday()]} {dt.strftime('%m/%d')}"
        day_order[day_label] = dt

        if day_label not in data:
            data[day_label] = {}

        for entry, dur in zip(date_entries, durations):
            if dur is None or entry.project in skip:
                continue
            group = project_to_group.get(entry.project, entry.project)
            all_groups.add(group)
            data[day_label][group] = data[day_label].get(group, 0.0) + dur

    sorted_days = sorted(data.keys(), key=lambda d: day_order[d])
    sorted_groups = sorted(all_groups)
    return sorted_days, sorted_groups, data


def round_seconds(seconds: float, round_minutes: int = 0) -> float:
    """Round seconds to the nearest N minutes. 0 means no rounding."""
    if round_minutes <= 0:
        return seconds
    chunk = round_minutes * 60
    return round(seconds / chunk) * chunk


def format_hours(seconds: float) -> str:
    """Format seconds as decimal hours, e.g. '2.5h'."""
    return f"{seconds / 3600:.1f}h"


def format_hm(seconds: float, round_minutes: int = 0) -> str:
    """Format seconds as '4h 3m' with optional rounding."""
    seconds = round_seconds(seconds, round_minutes)
    total_minutes = int(seconds // 60)
    h = total_minutes // 60
    m = total_minutes % 60
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"
