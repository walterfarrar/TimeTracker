import { formatDuration, computeDurations, computeRunningTotals } from './time-calc.js';

let editCallback = null;
let lastEntryTimestamp = null;
let baseRunningTotal = 0;
let elLiveDuration, elLiveTotal;

function formatDate(epoch) {
  const d = new Date(epoch * 1000);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  const yyyy = d.getFullYear();
  return `${mm}/${dd}/${yyyy}`;
}

function formatTime(epoch) {
  const d = new Date(epoch * 1000);
  let h = d.getHours();
  const ampm = h >= 12 ? 'PM' : 'AM';
  h = h % 12 || 12;
  const mm = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');
  return `${String(h).padStart(2, '0')}:${mm}:${ss} ${ampm}`;
}

function createCell(text, className) {
  const td = document.createElement('td');
  td.textContent = text;
  if (className) td.className = className;
  return td;
}

export function renderLog(entries, breakProjects) {
  const bp = new Set((breakProjects || []).map(p => p.toUpperCase()));
  const root = document.getElementById('log-view');
  root.innerHTML = '';

  const table = document.createElement('table');
  table.className = 'log-table';

  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  ['Date', 'Time', 'Project', 'Activity', 'Detail', 'Duration', 'Total'].forEach(col => {
    const th = document.createElement('th');
    th.textContent = col;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  const durations = computeDurations(entries);
  const totals = computeRunningTotals(durations);

  lastEntryTimestamp = null;
  baseRunningTotal = 0;
  elLiveDuration = null;
  elLiveTotal = null;

  entries.forEach((entry, i) => {
    const tr = document.createElement('tr');
    const isBreak = bp.has(entry.project.toUpperCase());
    if (isBreak) tr.className = 'log-row-break';

    tr.appendChild(createCell(formatDate(entry.timestamp)));
    tr.appendChild(createCell(formatTime(entry.timestamp)));
    tr.appendChild(createCell(entry.project));
    tr.appendChild(createCell(entry.activity));
    tr.appendChild(createCell(entry.detail));

    const isLast = i === entries.length - 1;

    const durCell = createCell(durations[i] !== null ? formatDuration(durations[i]) : '');
    const totCell = createCell(totals[i] !== null ? formatDuration(totals[i]) : '');

    if (isLast) {
      durCell.id = 'live-duration';
      totCell.id = 'live-total';
      elLiveDuration = durCell;
      elLiveTotal = totCell;
      lastEntryTimestamp = entry.timestamp;
      baseRunningTotal = i > 0 && totals[i - 1] !== null ? totals[i - 1] : 0;
    }

    tr.appendChild(durCell);
    tr.appendChild(totCell);

    if (editCallback) {
      tr.addEventListener('dblclick', () => editCallback(entry));
      tr.classList.add('log-row-editable');
    }

    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
  root.appendChild(table);
}

export function tickLiveDuration() {
  if (!lastEntryTimestamp || !elLiveDuration || !elLiveTotal) return;
  const elapsed = Math.floor(Date.now() / 1000) - lastEntryTimestamp;
  elLiveDuration.textContent = formatDuration(elapsed);
  elLiveTotal.textContent = formatDuration(baseRunningTotal + elapsed);
}

export function setEditCallback(fn) {
  editCallback = fn;
}
