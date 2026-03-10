import { createEntry } from "./models.js";

const ENTRIES_KEY = "tt_entries";
const NEXT_ID_KEY = "tt_next_id";

function loadAll() {
  const raw = localStorage.getItem(ENTRIES_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw);
  } catch {
    return [];
  }
}

function saveAll(entries) {
  localStorage.setItem(ENTRIES_KEY, JSON.stringify(entries));
}

function nextId() {
  const id = parseInt(localStorage.getItem(NEXT_ID_KEY) || "1", 10);
  localStorage.setItem(NEXT_ID_KEY, String(id + 1));
  return id;
}

export function addEntry(project, activity = "", detail = "", timestamp = null) {
  const entry = createEntry(project, activity, detail);
  entry.id = nextId();
  if (timestamp !== null) entry.timestamp = timestamp;
  const entries = loadAll();
  entries.push(entry);
  saveAll(entries);
  return entry;
}

export function updateEntry(id, project, activity, detail, timestamp = null) {
  const entries = loadAll();
  const idx = entries.findIndex((e) => e.id === id);
  if (idx === -1) return null;
  entries[idx].project = project;
  entries[idx].activity = activity;
  entries[idx].detail = detail;
  if (timestamp !== null) entries[idx].timestamp = timestamp;
  saveAll(entries);
  return entries[idx];
}

export function deleteEntry(id) {
  const entries = loadAll();
  const filtered = entries.filter((e) => e.id !== id);
  if (filtered.length === entries.length) return false;
  saveAll(filtered);
  return true;
}

function startOfDay(date) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return Math.floor(d.getTime() / 1000);
}

function endOfDay(date) {
  const d = new Date(date);
  d.setHours(23, 59, 59, 999);
  return Math.floor(d.getTime() / 1000);
}

export function getEntriesForDate(date) {
  const start = startOfDay(date);
  const end = endOfDay(date);
  return loadAll()
    .filter((e) => e.timestamp >= start && e.timestamp <= end)
    .sort((a, b) => a.timestamp - b.timestamp);
}

function isoWeekBounds(refDate) {
  const d = new Date(refDate);
  d.setHours(0, 0, 0, 0);
  const day = d.getDay();
  const diffToMonday = (day === 0 ? -6 : 1) - day;
  const monday = new Date(d);
  monday.setDate(d.getDate() + diffToMonday);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  sunday.setHours(23, 59, 59, 999);
  return {
    start: Math.floor(monday.getTime() / 1000),
    end: Math.floor(sunday.getTime() / 1000),
  };
}

export function getEntriesForWeek(refDate) {
  const { start, end } = isoWeekBounds(refDate);
  return loadAll()
    .filter((e) => e.timestamp >= start && e.timestamp <= end)
    .sort((a, b) => a.timestamp - b.timestamp);
}

export function getEntriesRange(startDate, endDate) {
  const start = startOfDay(startDate);
  const end = endOfDay(endDate);
  return loadAll()
    .filter((e) => e.timestamp >= start && e.timestamp <= end)
    .sort((a, b) => a.timestamp - b.timestamp);
}

export function getLastEntry() {
  const entries = loadAll();
  if (entries.length === 0) return null;
  return entries.reduce((latest, e) =>
    e.timestamp > latest.timestamp ? e : latest
  );
}

export function getAllEntries() {
  return loadAll().sort((a, b) => a.timestamp - b.timestamp);
}

export function hasEntriesInRange(startDate, endDate) {
  const start = startOfDay(startDate);
  const end = endOfDay(endDate);
  return loadAll().some((e) => e.timestamp >= start && e.timestamp <= end);
}

export function getDateBounds() {
  const entries = loadAll();
  if (entries.length === 0) return null;
  const timestamps = entries.map((e) => e.timestamp);
  return {
    earliest: Math.min(...timestamps),
    latest: Math.max(...timestamps),
  };
}
