import * as Store from './store.js';
import { loadSettings, loadButtonConfig } from './models.js';
import {
  computeDurations, computeWorkTime, aggregateTime,
  aggregateByDayAndGroup, formatDuration, formatHm, formatHours
} from './time-calc.js';

const COLORS = [
  "#FF6384","#36A2EB","#FFCE56","#4BC0C0","#9966FF",
  "#FF9F40","#E7E9ED","#7BC225","#EA5545","#27AEEF"
];
const DAY_NAMES = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];

let currentMonday = getMonday(new Date());
let rangeMode = 'week';
let roundMinutes = 0;
let projectToGroupMap = {};
let projectChart = null;
let activityChart = null;

function getMonday(date) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  const day = d.getDay();
  d.setDate(d.getDate() - (day === 0 ? 6 : day - 1));
  return d;
}

function addDays(date, n) {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

function fmtDate(d) {
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function toIso(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function buildProjectGroupMap() {
  const config = loadButtonConfig();
  const map = {};
  if (config?.groups) {
    for (const g of config.groups) {
      for (const btn of g.buttons) {
        map[btn.project] = g.name;
      }
    }
  }
  projectToGroupMap = map;
}

function getDateRange() {
  if (rangeMode === 'week') {
    const sunday = addDays(currentMonday, 6);
    return { start: currentMonday, end: sunday };
  }
  const startInput = document.getElementById('reports-start-date');
  const endInput = document.getElementById('reports-end-date');
  if (!startInput?.value || !endInput?.value) return null;
  return { start: new Date(startInput.value + 'T00:00:00'), end: new Date(endInput.value + 'T00:00:00') };
}

function weekLabel() {
  const sunday = addDays(currentMonday, 6);
  return `${fmtDate(currentMonday)} – ${fmtDate(sunday)}`;
}

function canGoPrev() {
  const prevSunday = addDays(currentMonday, -1);
  const prevMonday = addDays(currentMonday, -7);
  return Store.hasEntriesInRange(prevMonday, prevSunday);
}

function canGoNext() {
  const nextMonday = addDays(currentMonday, 7);
  const nextSunday = addDays(currentMonday, 13);
  return Store.hasEntriesInRange(nextMonday, nextSunday);
}

// ── UI Construction ──

function buildControls(root) {
  const row = document.createElement('div');
  row.className = 'reports-controls';

  const segWrap = document.createElement('div');
  segWrap.style.display = 'flex';

  const btnWeek = document.createElement('button');
  btnWeek.textContent = 'Week';
  btnWeek.id = 'reports-seg-week';
  btnWeek.className = rangeMode === 'week' ? 'reports-segment reports-segment-active' : 'reports-segment';

  const btnCustom = document.createElement('button');
  btnCustom.textContent = 'Custom Range';
  btnCustom.id = 'reports-seg-custom';
  btnCustom.className = rangeMode === 'custom' ? 'reports-segment reports-segment-active' : 'reports-segment';

  btnWeek.addEventListener('click', () => { rangeMode = 'week'; renderControls(); refreshReports(); });
  btnCustom.addEventListener('click', () => { rangeMode = 'custom'; renderControls(); refreshReports(); });

  segWrap.append(btnWeek, btnCustom);
  row.appendChild(segWrap);

  if (rangeMode === 'week') {
    const nav = document.createElement('div');
    nav.className = 'reports-nav';

    const prev = document.createElement('button');
    prev.textContent = '\u25C0';
    prev.className = canGoPrev() ? 'nav-btn' : 'nav-btn nav-btn-disabled';
    prev.disabled = !canGoPrev();
    prev.addEventListener('click', () => { currentMonday = addDays(currentMonday, -7); refreshReports(); });

    const label = document.createElement('span');
    label.textContent = weekLabel();

    const next = document.createElement('button');
    next.textContent = '\u25B6';
    next.className = canGoNext() ? 'nav-btn' : 'nav-btn nav-btn-disabled';
    next.disabled = !canGoNext();
    next.addEventListener('click', () => { currentMonday = addDays(currentMonday, 7); refreshReports(); });

    const today = document.createElement('button');
    today.textContent = 'Today';
    today.className = 'nav-btn';
    today.addEventListener('click', () => { currentMonday = getMonday(new Date()); refreshReports(); });

    nav.append(prev, label, next, today);
    row.appendChild(nav);
  } else {
    const nav = document.createElement('div');
    nav.className = 'reports-nav';

    const startInput = document.createElement('input');
    startInput.type = 'date';
    startInput.id = 'reports-start-date';
    startInput.value = toIso(currentMonday);
    startInput.addEventListener('change', () => refreshReports());

    const endInput = document.createElement('input');
    endInput.type = 'date';
    endInput.id = 'reports-end-date';
    endInput.value = toIso(addDays(currentMonday, 6));
    endInput.addEventListener('change', () => refreshReports());

    nav.append(startInput, endInput);
    row.appendChild(nav);
  }

  root.appendChild(row);
}

function renderControls() {
  const root = document.getElementById('reports-tab');
  const existing = root.querySelector('.reports-controls');
  if (existing) existing.remove();
  const ref = root.firstChild;
  const tmp = document.createElement('div');
  buildControls(tmp);
  root.insertBefore(tmp.firstChild, ref);
}

function buildTimesheetSection(root, entries) {
  const section = document.createElement('div');
  section.className = 'reports-section';
  section.id = 'reports-timesheet-section';

  const titleRow = document.createElement('div');
  titleRow.style.display = 'flex';
  titleRow.style.alignItems = 'center';
  titleRow.style.justifyContent = 'space-between';
  titleRow.style.marginBottom = '8px';

  const heading = document.createElement('h3');
  heading.textContent = 'Weekly Timesheet by Group';
  heading.style.margin = '0';

  const roundBtns = document.createElement('div');
  const roundOptions = [
    { label: 'Exact', value: 0 },
    { label: '5m', value: 5 },
    { label: '15m', value: 15 },
    { label: '30m', value: 30 },
  ];

  for (const opt of roundOptions) {
    const btn = document.createElement('button');
    btn.textContent = opt.label;
    btn.className = roundMinutes === opt.value ? 'round-btn round-btn-active' : 'round-btn';
    btn.addEventListener('click', () => {
      roundMinutes = opt.value;
      refreshReports();
    });
    roundBtns.appendChild(btn);
  }

  titleRow.append(heading, roundBtns);
  section.appendChild(titleRow);

  const settings = loadSettings();
  const range = getDateRange();
  if (!range) { root.appendChild(section); return; }

  const agg = aggregateByDayAndGroup(entries, settings.breakProjects, projectToGroupMap);

  let days;
  if (rangeMode === 'week') {
    days = [];
    for (let i = 0; i < 7; i++) days.push(toIso(addDays(currentMonday, i)));
  } else {
    days = [];
    let cursor = new Date(range.start);
    while (cursor <= range.end) {
      days.push(toIso(cursor));
      cursor = addDays(cursor, 1);
    }
  }

  const groups = agg.groups;

  const table = document.createElement('table');
  table.className = 'reports-table';

  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  headerRow.appendChild(el('th', 'Group'));
  for (const day of days) {
    const d = new Date(day + 'T00:00:00');
    const dayName = DAY_NAMES[d.getDay() === 0 ? 6 : d.getDay() - 1] || d.toLocaleDateString('en-US', { weekday: 'short' });
    const th = el('th', `${dayName}\n${d.getDate()}`);
    th.style.whiteSpace = 'pre-line';
    headerRow.appendChild(th);
  }
  headerRow.appendChild(el('th', 'Total'));
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  const colTotals = new Array(days.length).fill(0);

  for (const group of groups) {
    const tr = document.createElement('tr');
    tr.appendChild(el('td', group));
    let rowTotal = 0;
    days.forEach((day, idx) => {
      const secs = (agg.data[day] && agg.data[day][group]) || 0;
      rowTotal += secs;
      colTotals[idx] += secs;
      tr.appendChild(el('td', secs > 0 ? formatHm(secs, roundMinutes) : ''));
    });
    tr.appendChild(el('td', rowTotal > 0 ? formatHm(rowTotal, roundMinutes) : ''));
    tbody.appendChild(tr);
  }

  const totalRow = document.createElement('tr');
  totalRow.style.fontWeight = 'bold';
  totalRow.appendChild(el('td', 'Total'));
  let grandTotal = 0;
  for (const ct of colTotals) {
    grandTotal += ct;
    totalRow.appendChild(el('td', ct > 0 ? formatHm(ct, roundMinutes) : ''));
  }
  totalRow.appendChild(el('td', grandTotal > 0 ? formatHm(grandTotal, roundMinutes) : ''));
  tbody.appendChild(totalRow);

  table.appendChild(tbody);
  section.appendChild(table);
  root.appendChild(section);
}

function buildChartsSection(root, entries) {
  const section = document.createElement('div');
  section.className = 'reports-section';
  section.id = 'reports-charts-section';

  const settings = loadSettings();
  const agg = aggregateTime(entries, settings.breakProjects);

  const projects = Object.keys(agg).sort();
  const projectTotals = projects.map(p => agg[p]._total);

  const activityLabels = [];
  const activityValues = [];
  for (const proj of projects) {
    for (const [act, secs] of Object.entries(agg[proj])) {
      if (act === '_total') continue;
      activityLabels.push(`${proj} / ${act}`);
      activityValues.push(secs);
    }
  }

  const wrap = document.createElement('div');
  wrap.style.display = 'flex';
  wrap.style.flexWrap = 'wrap';
  wrap.style.gap = '24px';

  if (projects.length > 0) {
    wrap.appendChild(buildPieChart('Time by Project', projects, projectTotals, 'project'));
    if (activityLabels.length > 0) {
      wrap.appendChild(buildPieChart('Time by Project + Activity', activityLabels, activityValues, 'activity'));
    }
  }

  section.appendChild(wrap);
  root.appendChild(section);
}

function buildPieChart(title, labels, data, id) {
  const box = document.createElement('div');
  box.className = 'chart-container';

  const h = document.createElement('h3');
  h.textContent = title;
  h.style.margin = '0 0 8px 0';
  box.appendChild(h);

  const canvas = document.createElement('canvas');
  canvas.id = `reports-chart-${id}`;
  canvas.width = 320;
  canvas.height = 320;
  box.appendChild(canvas);

  setTimeout(() => {
    if (id === 'project' && projectChart) { projectChart.destroy(); projectChart = null; }
    if (id === 'activity' && activityChart) { activityChart.destroy(); activityChart = null; }

    const ctx = canvas.getContext('2d');
    const chart = new Chart(ctx, {
      type: 'pie',
      data: {
        labels,
        datasets: [{
          data,
          backgroundColor: labels.map((_, i) => COLORS[i % COLORS.length]),
        }],
      },
      options: {
        responsive: false,
        plugins: {
          tooltip: {
            callbacks: {
              label(context) {
                const secs = context.raw;
                return ` ${context.label}: ${formatHm(secs)}`;
              }
            }
          },
          legend: { position: 'bottom', labels: { boxWidth: 12 } }
        }
      }
    });

    if (id === 'project') projectChart = chart;
    else activityChart = chart;
  }, 0);

  return box;
}

function buildTextBreakdown(root, entries) {
  const section = document.createElement('div');
  section.className = 'reports-section text-breakdown';
  section.id = 'reports-text-section';

  const heading = document.createElement('h3');
  heading.textContent = 'Time Breakdown';
  section.appendChild(heading);

  const settings = loadSettings();
  const agg = aggregateTime(entries, settings.breakProjects);
  const projects = Object.keys(agg).sort();

  if (projects.length === 0) {
    const p = document.createElement('p');
    p.textContent = 'No data for this period.';
    section.appendChild(p);
    root.appendChild(section);
    return;
  }

  const list = document.createElement('ul');
  for (const proj of projects) {
    const li = document.createElement('li');
    li.innerHTML = `<strong>${esc(proj)}</strong> — ${formatHm(agg[proj]._total, roundMinutes)}`;

    const activities = Object.entries(agg[proj]).filter(([k]) => k !== '_total').sort((a, b) => b[1] - a[1]);
    if (activities.length > 0) {
      const sub = document.createElement('ul');
      for (const [act, secs] of activities) {
        const sli = document.createElement('li');
        sli.textContent = `${act}: ${formatHm(secs, roundMinutes)}`;
        sub.appendChild(sli);
      }
      li.appendChild(sub);
    }
    list.appendChild(li);
  }

  section.appendChild(list);
  root.appendChild(section);
}

// ── Helpers ──

function el(tag, text) {
  const e = document.createElement(tag);
  e.textContent = text;
  return e;
}

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

// ── Public API ──

export function initReports() {
  buildProjectGroupMap();
  const root = document.getElementById('reports-tab');
  root.innerHTML = '';
  refreshReports();
}

export function refreshReports() {
  const root = document.getElementById('reports-tab');
  root.innerHTML = '';

  buildControls(root);

  const range = getDateRange();
  if (!range) return;

  const entries = Store.getEntriesRange(range.start, range.end);

  buildTimesheetSection(root, entries);
  buildChartsSection(root, entries);
  buildTextBreakdown(root, entries);
}

export function updateButtonConfig() {
  buildProjectGroupMap();
  refreshReports();
}
