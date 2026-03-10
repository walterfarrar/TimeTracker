import { formatDuration } from './time-calc.js';

const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

let viewDate = todayMidnight();
let callbacks = {};
let elDateLabel, elWorkedToday, elRemaining, elDaysInput;

function todayMidnight() {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
}

function formatDateLabel(date) {
  const dow = DAY_NAMES[date.getDay()];
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  const yyyy = date.getFullYear();
  return `${dow} ${mm}/${dd}/${yyyy}`;
}

function shiftDate(delta) {
  viewDate = new Date(viewDate);
  viewDate.setDate(viewDate.getDate() + delta);
  elDateLabel.textContent = formatDateLabel(viewDate);
  callbacks.onDateChanged?.(viewDate);
}

let onMenuToggle = null;

export function setMenuToggle(fn) {
  onMenuToggle = fn;
}

export function initHeader(cb) {
  callbacks = cb;

  const root = document.getElementById('header');
  root.innerHTML = '';

  const navRow = document.createElement('div');
  navRow.className = 'header-nav';

  const btnMenu = document.createElement('button');
  btnMenu.className = 'btn-secondary header-menu-btn';
  btnMenu.textContent = '\u2630';
  btnMenu.title = 'Menu';
  btnMenu.addEventListener('click', () => onMenuToggle?.());

  const btnPrev = document.createElement('button');
  btnPrev.className = 'btn-secondary';
  btnPrev.textContent = '\u25C0';
  btnPrev.addEventListener('click', () => shiftDate(-1));

  elDateLabel = document.createElement('span');
  elDateLabel.className = 'header-date-label';
  elDateLabel.textContent = formatDateLabel(viewDate);

  const btnNext = document.createElement('button');
  btnNext.className = 'btn-secondary';
  btnNext.textContent = '\u25B6';
  btnNext.addEventListener('click', () => shiftDate(1));

  const btnToday = document.createElement('button');
  btnToday.className = 'btn-primary';
  btnToday.textContent = 'Today';
  btnToday.addEventListener('click', () => goToday());

  navRow.append(btnMenu, btnPrev, elDateLabel, btnNext, btnToday);

  const statsRow = document.createElement('div');
  statsRow.className = 'header-stats';

  const daysGroup = document.createElement('label');
  daysGroup.className = 'header-stat-group';
  daysGroup.textContent = 'Days This Week ';
  elDaysInput = document.createElement('input');
  elDaysInput.type = 'number';
  elDaysInput.min = '1';
  elDaysInput.max = '7';
  elDaysInput.className = 'header-days-input';
  elDaysInput.addEventListener('change', () => {
    callbacks.onDaysChanged?.(parseInt(elDaysInput.value, 10) || 5);
  });
  daysGroup.appendChild(elDaysInput);

  const workedGroup = document.createElement('div');
  workedGroup.className = 'header-stat-group';
  const workedLabel = document.createElement('span');
  workedLabel.textContent = 'Worked Today: ';
  elWorkedToday = document.createElement('span');
  elWorkedToday.className = 'header-stat-value';
  elWorkedToday.textContent = '0:00:00';
  workedGroup.append(workedLabel, elWorkedToday);

  const remainGroup = document.createElement('div');
  remainGroup.className = 'header-stat-group';
  const remainLabel = document.createElement('span');
  remainLabel.textContent = 'Remaining: ';
  elRemaining = document.createElement('span');
  elRemaining.className = 'header-stat-value';
  elRemaining.textContent = '0:00:00';
  remainGroup.append(remainLabel, elRemaining);

  statsRow.append(daysGroup, workedGroup, remainGroup);
  root.append(navRow, statsRow);
}

export function updateStats(workedTodaySecs, remainingSecs) {
  elWorkedToday.textContent = formatDuration(workedTodaySecs);

  elRemaining.textContent = formatDuration(remainingSecs);
  elRemaining.classList.remove('stat-negative', 'stat-warning');
  if (remainingSecs < 0) {
    elRemaining.classList.add('stat-negative');
  } else if (remainingSecs < 3600) {
    elRemaining.classList.add('stat-warning');
  }
}

export function setDays(value) {
  elDaysInput.value = value;
}

export function getViewDate() {
  return viewDate;
}

export function isViewingToday() {
  const today = todayMidnight();
  return viewDate.getTime() === today.getTime();
}

export function goToday() {
  viewDate = todayMidnight();
  elDateLabel.textContent = formatDateLabel(viewDate);
  callbacks.onDateChanged?.(viewDate);
}
