import {
  loadSettings,
  saveSettings,
  loadButtonConfig,
  saveButtonConfig,
} from './models.js';

let overlay = null;
let onSaveCallback = null;
let activeTab = 'general';
let editableConfig = null;

export function openSettings(onSave) {
  if (overlay) return;
  onSaveCallback = onSave || null;
  activeTab = 'general';
  editableConfig = structuredClone(loadButtonConfig());
  render();
}

export function closeSettings() {
  if (overlay) {
    overlay.remove();
    overlay = null;
    onSaveCallback = null;
    editableConfig = null;
  }
}

function render() {
  if (overlay) overlay.remove();

  overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeSettings();
  });

  const modal = document.createElement('div');
  modal.className = 'modal-content';

  modal.appendChild(buildHeader());
  modal.appendChild(buildTabs());
  modal.appendChild(activeTab === 'general' ? buildGeneralBody() : buildButtonsBody());
  modal.appendChild(buildFooter());

  overlay.appendChild(modal);
  document.body.appendChild(overlay);
}

function buildHeader() {
  const header = document.createElement('div');
  header.className = 'modal-header';
  header.textContent = 'Settings';
  return header;
}

function buildTabs() {
  const tabs = document.createElement('div');
  tabs.className = 'modal-tabs';

  for (const [id, label] of [['general', 'General'], ['buttons', 'Buttons']]) {
    const tab = document.createElement('button');
    tab.className = activeTab === id ? 'modal-tab modal-tab-active' : 'modal-tab';
    tab.textContent = label;
    tab.addEventListener('click', () => {
      activeTab = id;
      render();
    });
    tabs.appendChild(tab);
  }

  return tabs;
}

function buildGeneralBody() {
  const settings = loadSettings();
  const body = document.createElement('div');
  body.className = 'modal-body';

  body.appendChild(buildField('Hours per day', () => {
    const input = document.createElement('input');
    input.className = 'settings-input';
    input.type = 'number';
    input.step = '0.5';
    input.min = '1';
    input.max = '24';
    input.value = settings.hoursPerDay ?? 8;
    input.dataset.key = 'hoursPerDay';
    return input;
  }));

  body.appendChild(buildField('Break projects', () => {
    const input = document.createElement('input');
    input.className = 'settings-input';
    input.type = 'text';
    input.placeholder = 'BREAK';
    input.value = (settings.breakProjects ?? ['BREAK']).join(', ');
    input.dataset.key = 'breakProjects';
    return input;
  }));

  body.appendChild(buildField('Theme', () => {
    const select = document.createElement('select');
    select.className = 'settings-input';
    select.dataset.key = 'theme';
    for (const value of ['dark', 'light']) {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = value;
      opt.selected = (settings.theme ?? 'dark') === value;
      select.appendChild(opt);
    }
    return select;
  }));

  return body;
}

function buildField(labelText, createInput) {
  const field = document.createElement('div');
  field.className = 'settings-field';

  const label = document.createElement('label');
  label.className = 'settings-label';
  label.textContent = labelText;
  field.appendChild(label);

  field.appendChild(createInput());
  return field;
}

function buildButtonsBody() {
  const body = document.createElement('div');
  body.className = 'modal-body';

  const groups = editableConfig.groups || [];
  groups.forEach((group, gi) => {
    const card = document.createElement('div');
    card.className = 'group-card';

    const header = document.createElement('div');
    header.className = 'group-header';

    const titleInput = document.createElement('input');
    titleInput.className = 'group-title';
    titleInput.type = 'text';
    titleInput.value = group.name;
    titleInput.addEventListener('input', (e) => {
      editableConfig.groups[gi].name = e.target.value;
    });
    header.appendChild(titleInput);

    const deleteGroupBtn = document.createElement('button');
    deleteGroupBtn.className = 'btn-delete';
    deleteGroupBtn.textContent = 'Delete Group';
    deleteGroupBtn.addEventListener('click', () => {
      editableConfig.groups.splice(gi, 1);
      render();
    });
    header.appendChild(deleteGroupBtn);

    card.appendChild(header);

    (group.buttons || []).forEach((btn, bi) => {
      const row = document.createElement('div');
      row.className = 'button-row';

      for (const key of ['label', 'project', 'activity']) {
        const input = document.createElement('input');
        input.className = 'button-field';
        input.type = 'text';
        input.placeholder = key;
        input.value = btn[key] ?? '';
        input.addEventListener('input', (e) => {
          editableConfig.groups[gi].buttons[bi][key] = e.target.value;
        });
        row.appendChild(input);
      }

      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'btn-delete';
      deleteBtn.textContent = '✕';
      deleteBtn.addEventListener('click', () => {
        editableConfig.groups[gi].buttons.splice(bi, 1);
        render();
      });
      row.appendChild(deleteBtn);

      card.appendChild(row);
    });

    const addBtnLink = document.createElement('a');
    addBtnLink.className = 'btn-add';
    addBtnLink.href = '#';
    addBtnLink.textContent = 'Add Button';
    addBtnLink.addEventListener('click', (e) => {
      e.preventDefault();
      editableConfig.groups[gi].buttons.push({ label: '', project: '', activity: '' });
      render();
    });
    card.appendChild(addBtnLink);

    body.appendChild(card);
  });

  const addGroupBtn = document.createElement('button');
  addGroupBtn.className = 'btn-add';
  addGroupBtn.textContent = 'Add Group';
  addGroupBtn.addEventListener('click', () => {
    editableConfig.groups.push({ name: 'New Group', buttons: [] });
    render();
  });
  body.appendChild(addGroupBtn);

  return body;
}

function buildFooter() {
  const footer = document.createElement('div');
  footer.className = 'modal-footer';

  const saveBtn = document.createElement('button');
  saveBtn.className = 'btn-primary';
  saveBtn.textContent = 'Save';
  saveBtn.addEventListener('click', handleSave);

  const cancelBtn = document.createElement('button');
  cancelBtn.className = 'btn-secondary';
  cancelBtn.textContent = 'Cancel';
  cancelBtn.addEventListener('click', closeSettings);

  footer.appendChild(saveBtn);
  footer.appendChild(cancelBtn);
  return footer;
}

function handleSave() {
  const body = overlay.querySelector('.modal-body');
  let settings = loadSettings();

  if (activeTab === 'general') {
    const hoursInput = body.querySelector('[data-key="hoursPerDay"]');
    const breakInput = body.querySelector('[data-key="breakProjects"]');
    const themeSelect = body.querySelector('[data-key="theme"]');

    settings = {
      ...settings,
      hoursPerDay: parseFloat(hoursInput.value) || 8,
      breakProjects: breakInput.value
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      theme: themeSelect.value,
    };
    saveSettings(settings);
  }

  saveButtonConfig(editableConfig);

  if (onSaveCallback) {
    onSaveCallback({ settings, buttonConfig: editableConfig });
  }

  closeSettings();
}
