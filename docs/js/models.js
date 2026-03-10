const BUTTONS_KEY = "tt_buttons";
const SETTINGS_KEY = "tt_settings";

export function createEntry(project, activity = "", detail = "") {
  return {
    id: null,
    timestamp: Math.floor(Date.now() / 1000),
    project,
    activity,
    detail,
  };
}

export function defaultSettings() {
  return {
    hoursPerDay: 8,
    workingDaysThisWeek: 5,
    breakProjects: ["BREAK"],
    theme: "dark",
  };
}

export function loadSettings() {
  const raw = localStorage.getItem(SETTINGS_KEY);
  if (!raw) return defaultSettings();
  try {
    return { ...defaultSettings(), ...JSON.parse(raw) };
  } catch {
    return defaultSettings();
  }
}

export function saveSettings(settings) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}

export function defaultButtonConfig() {
  return {
    groups: [
      {
        name: "BREAK",
        buttons: [
          { label: "Break", project: "BREAK", activity: "Break", detail: "" },
          { label: "Lunch", project: "BREAK", activity: "Lunch", detail: "" },
        ],
      },
    ],
  };
}

export function loadButtonConfig() {
  const raw = localStorage.getItem(BUTTONS_KEY);
  if (!raw) return defaultButtonConfig();
  try {
    return JSON.parse(raw);
  } catch {
    return defaultButtonConfig();
  }
}

export function saveButtonConfig(config) {
  localStorage.setItem(BUTTONS_KEY, JSON.stringify(config));
}
