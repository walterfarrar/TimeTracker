export function roundSeconds(seconds, roundMinutes = 0) {
  if (roundMinutes <= 0) return seconds;
  const chunk = roundMinutes * 60;
  return Math.round(seconds / chunk) * chunk;
}

export function formatDuration(seconds) {
  const neg = seconds < 0;
  let s = Math.abs(Math.floor(seconds));
  const h = Math.floor(s / 3600);
  s %= 3600;
  const m = Math.floor(s / 60);
  s %= 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(s).padStart(2, "0");
  return `${neg ? "-" : ""}${h}:${mm}:${ss}`;
}

export function formatHm(seconds, roundMinutes = 0) {
  const rounded = roundSeconds(seconds, roundMinutes);
  const neg = rounded < 0;
  const abs = Math.abs(Math.floor(rounded));
  const h = Math.floor(abs / 3600);
  const m = Math.floor((abs % 3600) / 60);
  return `${neg ? "-" : ""}${h}h ${m}m`;
}

export function formatHours(seconds) {
  const h = seconds / 3600;
  return `${h < 0 ? "-" : ""}${Math.abs(h).toFixed(1)}h`;
}

export function computeDurations(entries) {
  return entries.map((e, i) => {
    if (i < entries.length - 1) {
      return entries[i + 1].timestamp - e.timestamp;
    }
    return null;
  });
}

export function computeRunningTotals(durations) {
  let sum = 0;
  return durations.map((d) => {
    if (d === null) return null;
    sum += d;
    return sum;
  });
}

export function computeWorkTime(entries, durations, breakProjects) {
  const bp = new Set(breakProjects.map((p) => p.toUpperCase()));
  let total = 0;
  for (let i = 0; i < entries.length; i++) {
    if (durations[i] === null) continue;
    if (!bp.has(entries[i].project.toUpperCase())) {
      total += durations[i];
    }
  }
  return total;
}

function groupEntriesByDay(entries) {
  const days = new Map();
  for (const e of entries) {
    const d = new Date(e.timestamp * 1000);
    const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
    if (!days.has(key)) days.set(key, []);
    days.get(key).push(e);
  }
  for (const [key, dayEntries] of days) {
    days.set(key, dayEntries.sort((a, b) => a.timestamp - b.timestamp));
  }
  return [...days.values()];
}

export function computeWeekWorkTime(allWeekEntries, breakProjects) {
  const dayGroups = groupEntriesByDay(allWeekEntries);
  let total = 0;
  for (const dayEntries of dayGroups) {
    const durations = computeDurations(dayEntries);
    total += computeWorkTime(dayEntries, durations, breakProjects);
  }
  return total;
}

export function computeTimeRemaining(weekWorkSeconds, workingDays, hoursPerDay) {
  const target = workingDays * hoursPerDay * 3600;
  return target - weekWorkSeconds;
}

export function aggregateTime(entries, breakProjects) {
  const bp = new Set(breakProjects.map((p) => p.toUpperCase()));
  const result = {};
  for (let i = 0; i < entries.length - 1; i++) {
    const e = entries[i];
    if (bp.has(e.project.toUpperCase())) continue;
    const dur = entries[i + 1].timestamp - e.timestamp;
    if (!result[e.project]) result[e.project] = { _total: 0 };
    result[e.project]._total += dur;
    const act = e.activity || "(none)";
    result[e.project][act] = (result[e.project][act] || 0) + dur;
  }
  return result;
}

export function aggregateByDayAndGroup(entries, breakProjects, projectToGroupMap) {
  const bp = new Set(breakProjects.map((p) => p.toUpperCase()));
  const dayBuckets = groupEntriesByDay(entries);
  const days = [];
  const groupSet = new Set();
  const data = {};

  for (const dayEntries of dayBuckets) {
    const d = new Date(dayEntries[0].timestamp * 1000);
    const dayKey = d.toISOString().slice(0, 10);
    days.push(dayKey);
    data[dayKey] = {};

    for (let i = 0; i < dayEntries.length - 1; i++) {
      const e = dayEntries[i];
      if (bp.has(e.project.toUpperCase())) continue;
      const dur = dayEntries[i + 1].timestamp - e.timestamp;
      const group = (projectToGroupMap && projectToGroupMap[e.project]) || e.project;
      groupSet.add(group);
      data[dayKey][group] = (data[dayKey][group] || 0) + dur;
    }
  }

  return { days: days.sort(), groups: [...groupSet].sort(), data };
}
