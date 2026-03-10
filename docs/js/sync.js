import * as Store from "./store.js";
import {
  loadSettings,
  saveSettings,
  loadButtonConfig,
  saveButtonConfig,
} from "./models.js";
import {
  formatDuration,
  computeDurations,
  computeRunningTotals,
} from "./time-calc.js";

/**
 * Triggers a file download from blob content.
 * @param {string} content - Raw file content
 * @param {string} filename - Suggested download filename
 * @param {string} mimeType - MIME type for the blob
 */
function downloadFile(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Formats a Unix timestamp as MM/DD/YYYY.
 * @param {number} timestamp - Unix timestamp in seconds
 * @returns {string}
 */
function formatDateMMDDYYYY(timestamp) {
  const d = new Date(timestamp * 1000);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const y = d.getFullYear();
  return `${m}/${day}/${y}`;
}

/**
 * Formats a Unix timestamp as HH:MM:SS AM/PM.
 * @param {number} timestamp - Unix timestamp in seconds
 * @returns {string}
 */
function formatTimeHHMMSSAMPM(timestamp) {
  const d = new Date(timestamp * 1000);
  const h = d.getHours();
  const m = d.getMinutes();
  const s = d.getSeconds();
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 || 12;
  const hh = String(h12).padStart(2, "0");
  const mm = String(m).padStart(2, "0");
  const ss = String(s).padStart(2, "0");
  return `${hh}:${mm}:${ss} ${ampm}`;
}

/**
 * Escapes a CSV field (wraps in quotes if needed).
 * @param {string} field
 * @returns {string}
 */
function escapeCsvField(field) {
  const s = String(field ?? "");
  if (s.includes(",") || s.includes('"') || s.includes("\n")) {
    return '"' + s.replace(/"/g, '""') + '"';
  }
  return s;
}

/**
 * Builds CSV rows from entries with durations and running totals.
 * @param {Array} entries - Sorted entries with timestamp, project, activity, detail
 * @returns {string}
 */
function buildCsvFromEntries(entries) {
  const durations = computeDurations(entries);
  const runningTotals = computeRunningTotals(durations);
  const headers = ["Date", "Time", "Project", "Activity", "Detail", "Duration", "Total"];
  const rows = [headers.map(escapeCsvField).join(",")];

  for (let i = 0; i < entries.length; i++) {
    const e = entries[i];
    const date = formatDateMMDDYYYY(e.timestamp);
    const time = formatTimeHHMMSSAMPM(e.timestamp);
    const duration = durations[i] !== null ? formatDuration(durations[i]) : "";
    const total = runningTotals[i] !== null ? formatDuration(runningTotals[i]) : "";
    rows.push(
      [
        escapeCsvField(date),
        escapeCsvField(time),
        escapeCsvField(e.project),
        escapeCsvField(e.activity),
        escapeCsvField(e.detail),
        escapeCsvField(duration),
        escapeCsvField(total),
      ].join(",")
    );
  }

  return rows.join("\n");
}

/**
 * Exports all data (entries, buttons config, settings) as a JSON file download.
 */
export function exportJson() {
  const payload = {
    version: 1,
    entries: Store.getAllEntries(),
    buttons: loadButtonConfig(),
    settings: loadSettings(),
  };
  const content = JSON.stringify(payload, null, 2);
  downloadFile(content, "timetracker_backup.json", "application/json");
}

/**
 * Opens a file picker, reads the JSON file, and imports entries, buttons, and settings.
 * @param {function(payload: object): void} onComplete - Called when import is done; receives the parsed payload
 */
export function importJson(onComplete) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".json";
  input.style.display = "none";
  document.body.appendChild(input);

  input.addEventListener("change", () => {
    const file = input.files?.[0];
    document.body.removeChild(input);

    if (!file) {
      onComplete?.({});
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      try {
        const payload = JSON.parse(reader.result);
        const entries = Array.isArray(payload.entries) ? payload.entries : [];

        for (const e of entries) {
          const project = e.project ?? "";
          const activity = e.activity ?? "";
          const detail = e.detail ?? "";
          const timestamp = typeof e.timestamp === "number" ? e.timestamp : null;
          Store.addEntry(project, activity, detail, timestamp);
        }

        if (payload.buttons) {
          saveButtonConfig(payload.buttons);
        }
        if (payload.settings) {
          saveSettings(payload.settings);
        }

        onComplete?.(payload);
      } catch (err) {
        console.error("Import failed:", err);
        onComplete?.({});
      }
    };
    reader.readAsText(file);
  });

  input.click();
}

/**
 * Exports today's entries as a CSV file download.
 * @param {Date} date - The date for which to export entries
 */
export function exportCsvToday(date) {
  const entries = Store.getEntriesForDate(date);
  const csv = buildCsvFromEntries(entries);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  const filename = `timetracker_${y}${m}${d}.csv`;
  downloadFile(csv, filename, "text/csv");
}

/**
 * Exports the whole week's entries as a CSV file download.
 * @param {Date} refDate - A date within the week to export
 */
export function exportCsvWeek(refDate) {
  const entries = Store.getEntriesForWeek(refDate);
  const csv = buildCsvFromEntries(entries);
  const d = new Date(refDate);
  d.setHours(0, 0, 0, 0);
  const day = d.getDay();
  const diffToMonday = (day === 0 ? -6 : 1) - day;
  const monday = new Date(d);
  monday.setDate(d.getDate() + diffToMonday);
  const y = monday.getFullYear();
  const m = String(monday.getMonth() + 1).padStart(2, "0");
  const dayNum = String(monday.getDate()).padStart(2, "0");
  const filename = `timetracker_${y}${m}${dayNum}.csv`;
  downloadFile(csv, filename, "text/csv");
}
