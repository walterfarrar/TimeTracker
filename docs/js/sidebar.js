let callbacks = {};

function closeMobileSidebar() {
  if (window.innerWidth <= 768) {
    document.getElementById('sidebar').classList.remove('sidebar-open');
    document.getElementById('sidebar-backdrop').classList.remove('sidebar-backdrop-visible');
  }
}

export function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  sidebar.classList.toggle('sidebar-open');
  backdrop.classList.toggle('sidebar-backdrop-visible');
}

export function initSidebar(cb) {
  callbacks = cb;

  const root = document.getElementById('sidebar');
  root.innerHTML = '';

  const topRow = document.createElement('div');
  topRow.className = 'sidebar-top';

  const btnEndDay = document.createElement('button');
  btnEndDay.className = 'btn-danger';
  btnEndDay.textContent = 'End Day';
  btnEndDay.addEventListener('click', () => {
    callbacks.onEndDay?.();
    closeMobileSidebar();
  });

  const btnRefresh = document.createElement('button');
  btnRefresh.className = 'btn-primary';
  btnRefresh.textContent = 'Refresh';
  btnRefresh.addEventListener('click', () => {
    callbacks.onRefresh?.();
    closeMobileSidebar();
  });

  topRow.append(btnEndDay, btnRefresh);

  const buttonArea = document.createElement('div');
  buttonArea.className = 'sidebar-buttons';
  buttonArea.id = 'sidebar-button-area';

  const bottomRow = document.createElement('div');
  bottomRow.className = 'sidebar-bottom';

  const btnSettings = document.createElement('button');
  btnSettings.className = 'btn-secondary';
  btnSettings.textContent = 'Settings';
  btnSettings.addEventListener('click', () => {
    callbacks.onSettings?.();
    closeMobileSidebar();
  });

  const btnExport = document.createElement('button');
  btnExport.className = 'btn-secondary';
  btnExport.textContent = 'Export JSON';
  btnExport.addEventListener('click', () => {
    callbacks.onExportJson?.();
    closeMobileSidebar();
  });

  const btnImport = document.createElement('button');
  btnImport.className = 'btn-secondary';
  btnImport.textContent = 'Import JSON';
  btnImport.addEventListener('click', () => {
    callbacks.onImportJson?.();
    closeMobileSidebar();
  });

  bottomRow.append(btnSettings, btnExport, btnImport);
  root.append(topRow, buttonArea, bottomRow);

  document.getElementById('sidebar-backdrop').addEventListener('click', closeMobileSidebar);
}

export function loadButtons(buttonConfig) {
  const area = document.getElementById('sidebar-button-area');
  area.innerHTML = '';

  if (!buttonConfig?.groups) return;

  for (const group of buttonConfig.groups) {
    const section = document.createElement('div');
    section.className = 'sidebar-group';

    const header = document.createElement('div');
    header.className = 'sidebar-group-header';
    header.textContent = group.name;
    section.appendChild(header);

    const grid = document.createElement('div');
    grid.className = 'sidebar-group-grid';

    for (const btn of group.buttons) {
      const button = document.createElement('button');
      button.className = 'btn-group-item';
      button.textContent = btn.label;
      button.addEventListener('click', () => {
        callbacks.onProjectClick?.(btn.project, btn.activity, btn.detail);
        closeMobileSidebar();
      });
      grid.appendChild(button);
    }

    section.appendChild(grid);
    area.appendChild(section);
  }
}
