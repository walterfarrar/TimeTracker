import * as Store from './store.js';
import { loadSettings, saveSettings, loadButtonConfig } from './models.js';
import {
  computeDurations, computeWorkTime, computeWeekWorkTime,
  computeTimeRemaining
} from './time-calc.js';
import { initHeader, updateStats, setDays, getViewDate, isViewingToday, goToday } from './header.js';
import { renderLog, tickLiveDuration, setEditCallback } from './log-view.js';
import { initSidebar, loadButtons } from './sidebar.js';
import { openSettings } from './settings-dialog.js';
import { initReports, refreshReports, updateButtonConfig } from './reports.js';
import { exportJson, importJson } from './sync.js';

let dayEnded = false;
let tickInterval = null;
let activeTab = 'log';

function init() {
  const settings = loadSettings();
  applyTheme(settings.theme);

  initHeader({
    onDateChanged: () => refreshLog(),
    onDaysChanged: (days) => {
      const s = loadSettings();
      s.workingDaysThisWeek = days;
      saveSettings(s);
      refreshStats();
    },
  });
  setDays(settings.workingDaysThisWeek);

  initSidebar({
    onProjectClick: (project, activity, detail) => onProjectClick(project, activity, detail),
    onEndDay: () => onEndDay(),
    onRefresh: () => { refreshLog(); refreshReports(); },
    onSettings: () => onOpenSettings(),
    onExportJson: () => exportJson(),
    onImportJson: () => importJson(() => {
      reloadButtonConfig();
      refreshLog();
      refreshReports();
    }),
  });

  reloadButtonConfig();

  setEditCallback((entry) => onEditEntry(entry));

  setupTabs();
  refreshLog();
  initReports();
  startLiveTick();
}

function setupTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      tabBtns.forEach((b) => b.classList.remove('tab-btn-active'));
      btn.classList.add('tab-btn-active');
      activeTab = btn.dataset.tab;
      document.getElementById('log-container').style.display = activeTab === 'log' ? 'flex' : 'none';
      document.getElementById('reports-tab').style.display = activeTab === 'reports' ? 'block' : 'none';
      if (activeTab === 'reports') refreshReports();
    });
  });
}

function reloadButtonConfig() {
  const config = loadButtonConfig();
  loadButtons(config);
}

function onProjectClick(project, activity, detail) {
  if (!isViewingToday()) goToday();
  dayEnded = false;
  Store.addEntry(project, activity || '', detail || '');
  refreshLog();
}

function onEndDay() {
  if (!isViewingToday()) goToday();
  Store.addEntry('END_OF_DAY', '', '');
  dayEnded = true;
  refreshLog();
}

function refreshLog() {
  const settings = loadSettings();
  const viewDate = getViewDate();
  const entries = Store.getEntriesForDate(viewDate);

  const isToday = isViewingToday();
  dayEnded = isToday && entries.some((e) => e.project === 'END_OF_DAY');

  renderLog(entries, settings.breakProjects);
  refreshStats();
}

function refreshStats() {
  const settings = loadSettings();
  const viewDate = getViewDate();
  const entries = Store.getEntriesForDate(viewDate);
  const durations = computeDurations(entries);
  const workedToday = computeWorkTime(entries, durations, settings.breakProjects);

  const weekEntries = Store.getEntriesForWeek(viewDate);
  const weekWork = computeWeekWorkTime(weekEntries, settings.breakProjects);
  const remaining = computeTimeRemaining(weekWork, settings.workingDaysThisWeek, settings.hoursPerDay);

  updateStats(workedToday, remaining);
}

function startLiveTick() {
  if (tickInterval) clearInterval(tickInterval);
  tickInterval = setInterval(() => {
    if (dayEnded || !isViewingToday()) return;
    tickLiveDuration();
    refreshStats();
  }, 1000);
}

function onOpenSettings() {
  openSettings(({ settings, buttonConfig }) => {
    applyTheme(settings.theme);
    reloadButtonConfig();
    refreshLog();
    updateButtonConfig();
  });
}

function onEditEntry(entry) {
  const newProject = prompt('Project:', entry.project);
  if (newProject === null) return;
  const newActivity = prompt('Activity:', entry.activity);
  if (newActivity === null) return;
  const newDetail = prompt('Detail:', entry.detail);
  if (newDetail === null) return;

  const doDelete = confirm('Delete this entry instead?');
  if (doDelete) {
    Store.deleteEntry(entry.id);
  } else {
    Store.updateEntry(entry.id, newProject, newActivity, newDetail);
  }
  refreshLog();
  refreshReports();
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme || 'dark');
}

document.addEventListener('DOMContentLoaded', init);
