    let topZ = 20;
    let audioEnabled = true;
    let audioCtx = null;

    const windowState = {
      agents:      { isMaximized: false, isMinimized: false, restoreRect: null, sortCol: 'name', sortAsc: true },
      antigravity: { isMaximized: false, isMinimized: false, restoreRect: null, sortCol: 'name', sortAsc: true },
      codex:       { isMaximized: false, isMinimized: false, restoreRect: null, sortCol: 'name', sortAsc: true },
      claude:      { isMaximized: false, isMinimized: false, restoreRect: null, sortCol: 'name', sortAsc: true },
      taskmgr:     { isMaximized: false, isMinimized: false, restoreRect: null },
      notepad:     { isMaximized: false, isMinimized: false, restoreRect: null, currentPath: null, currentSkillName: null },
      run:         { isMaximized: false, isMinimized: false, restoreRect: null },
      about:       { isMaximized: false, isMinimized: false, restoreRect: null }
    };

    let RAW_DATA = { antigravity: [], codex: [], claude: [], agents: [] };
    let deleteTarget = null;

    // Synthesized Sound Effects (Web Audio API)
    function playBeep(freq, duration, type='sine') {
      if (!audioEnabled) return;
      try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.type = type;
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
      } catch (e) {}
    }

    function playChord() {
      if (!audioEnabled) return;
      playBeep(523.25, 0.4); // C5
      setTimeout(() => playBeep(659.25, 0.4), 80); // E5
      setTimeout(() => playBeep(783.99, 0.5), 160); // G5
      setTimeout(() => playBeep(1046.50, 0.7), 240); // C6
    }

    function toggleAudio() {
      audioEnabled = !audioEnabled;
      document.getElementById('tray-audio').textContent = audioEnabled ? '[Vol]' : '[Mute]';
      showToast(audioEnabled ? 'Sound enabled' : 'Sound muted');
    }

    // Play chord on first click anywhere
    document.addEventListener('click', function initSound() {
      playChord();
      document.removeEventListener('click', initSound);
    }, { once: true });

    // Toast
    function showToast(msg) {
      const t = document.getElementById('toast');
      t.textContent = msg;
      t.style.display = 'block';
      setTimeout(() => { t.style.display = 'none'; }, 2500);
    }

    // Clock
    function updateClock() {
      const now = new Date();
      let hours = now.getHours();
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const ampm = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12 || 12;
      document.getElementById('tray-clock').textContent = `${hours}:${minutes} ${ampm}`;
    }
    setInterval(updateClock, 1000);
    updateClock();

    // -------------------------------------------------------------
    // DESKTOP MARQUEE SELECTION (Удерживать мышью и выделять)
    // -------------------------------------------------------------
    const desktopEl = document.getElementById('desktop');
    const selectionBox = document.getElementById('selection-box');
    let isSelecting = false;
    let selStartX = 0;
    let selStartY = 0;

    desktopEl.addEventListener('mousedown', (e) => {
      // Only start selection if clicking directly on desktop background
      if (e.target !== desktopEl) return;
      if (e.button !== 0) return; // Left mouse button only

      isSelecting = true;
      selStartX = e.clientX;
      selStartY = e.clientY;

      selectionBox.style.left = `${selStartX}px`;
      selectionBox.style.top = `${selStartY}px`;
      selectionBox.style.width = '0px';
      selectionBox.style.height = '0px';
      selectionBox.style.display = 'block';

      // Clear previous selection unless Shift or Ctrl is pressed
      if (!e.shiftKey && !e.ctrlKey) {
        document.querySelectorAll('.desktop-icon').forEach(icon => icon.classList.remove('selected'));
      }
    });

    document.addEventListener('mousemove', (e) => {
      if (!isSelecting) return;

      const currentX = e.clientX;
      const currentY = e.clientY;

      const left = Math.min(selStartX, currentX);
      const top = Math.min(selStartY, currentY);
      const width = Math.abs(currentX - selStartX);
      const height = Math.abs(currentY - selStartY);

      selectionBox.style.left = `${left}px`;
      selectionBox.style.top = `${top}px`;
      selectionBox.style.width = `${width}px`;
      selectionBox.style.height = `${height}px`;

      // Check collision with desktop icons
      const boxRect = { left, top, right: left + width, bottom: top + height };
      document.querySelectorAll('.desktop-icon').forEach(icon => {
        const iconRect = icon.getBoundingClientRect();
        const intersects = !(
          iconRect.right < boxRect.left ||
          iconRect.left > boxRect.right ||
          iconRect.bottom < boxRect.top ||
          iconRect.top > boxRect.bottom
        );
        if (intersects) {
          icon.classList.add('selected');
        } else if (!e.shiftKey && !e.ctrlKey) {
          icon.classList.remove('selected');
        }
      });
    });

    document.addEventListener('mouseup', () => {
      if (isSelecting) {
        isSelecting = false;
        selectionBox.style.display = 'none';
      }
    });

    // -------------------------------------------------------------
    // DESKTOP RIGHT-CLICK CONTEXT MENU
    // -------------------------------------------------------------
    const contextMenu = document.getElementById('context-menu');
    desktopEl.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      contextMenu.style.left = `${Math.min(e.clientX, window.innerWidth - 190)}px`;
      contextMenu.style.top = `${Math.min(e.clientY, window.innerHeight - 240)}px`;
      contextMenu.style.display = 'flex';
    });

    function hideContextMenu() {
      contextMenu.style.display = 'none';
    }

    document.addEventListener('click', (e) => {
      if (!contextMenu.contains(e.target)) hideContextMenu();
    });

    // -------------------------------------------------------------
    // BLUE SCREEN OF DEATH (AI Crash Simulator)
    // -------------------------------------------------------------
    let bsodOpenedAt = 0;

    function triggerBSOD(e) {
      if (e) {
        if (e.stopPropagation) e.stopPropagation();
        if (e.preventDefault) e.preventDefault();
      }
      hideContextMenu();
      toggleStartMenu(false);
      bsodOpenedAt = Date.now();
      const bsod = document.getElementById('bsod');
      if (bsod) bsod.style.display = 'block';
      playBeep(220, 0.8, 'sawtooth');
    }

    function dismissBSOD(e) {
      if (e) {
        if (e.stopPropagation) e.stopPropagation();
      }
      // Require at least 1200ms before allowing dismissal (prevents double-click, mouseup or accidental instant dismiss)
      if (Date.now() - bsodOpenedAt < 1200) {
        return;
      }
      const bsod = document.getElementById('bsod');
      if (bsod) bsod.style.display = 'none';
      playChord();
      showToast('AI Runtime restored from checkpoint.');
    }

    document.addEventListener('keydown', (e) => {
      const bsod = document.getElementById('bsod');
      if (bsod && bsod.style.display === 'block') {
        if (Date.now() - bsodOpenedAt >= 1000) {
          dismissBSOD(e);
        }
      }
    });

    // -------------------------------------------------------------
    // WINDOW MANAGEMENT (Focus, Open, Close, Minimize, Maximize)
    // -------------------------------------------------------------
    function focusWindow(winKey) {
      topZ++;
      const el = document.getElementById(`win-${winKey}`);
      if (!el) return;
      el.style.zIndex = topZ;

      document.querySelectorAll('.window').forEach(w => {
        const tb = w.querySelector('.win-caption');
        if (tb) tb.classList.add('inactive');
      });
      const activeTb = el.querySelector('.win-caption');
      if (activeTb) activeTb.classList.remove('inactive');

      document.querySelectorAll('.taskbar-tab').forEach(t => t.classList.remove('active'));
      const activeTab = document.getElementById(`tab-btn-${winKey}`);
      if (activeTab) activeTab.classList.add('active');
    }

    function openWindow(winKey) {
      const el = document.getElementById(`win-${winKey}`);
      if (!el) return;
      el.style.display = 'flex';
      windowState[winKey].isMinimized = false;
      focusWindow(winKey);

      let tab = document.getElementById(`tab-btn-${winKey}`);
      if (tab) tab.style.display = 'flex';
      playBeep(600, 0.05);
    }

    function closeWindow(winKey) {
      const el = document.getElementById(`win-${winKey}`);
      if (winKey === 'notepad') {
        if (!canLeaveNotepad()) return;
        windowState.notepad.currentPath = null;
        editor.baseline = ''; editor.version = null; editor.changedOnDisk = false;
      }
      if (el) el.style.display = 'none';
      const tab = document.getElementById(`tab-btn-${winKey}`);
      if (tab) tab.style.display = 'none';
      playBeep(400, 0.05);
    }

    function minimizeWindow(winKey) {
      const el = document.getElementById(`win-${winKey}`);
      if (el) el.style.display = 'none';
      windowState[winKey].isMinimized = true;
      const tab = document.getElementById(`tab-btn-${winKey}`);
      if (tab) tab.classList.remove('active');
    }

    function toggleMaximize(winKey) {
      const el = document.getElementById(`win-${winKey}`);
      if (!el) return;
      const state = windowState[winKey];
      const maxBtn = document.getElementById(`maxbtn-${winKey}`);

      if (!state.isMaximized) {
        state.restoreRect = {
          top: el.style.top,
          left: el.style.left,
          width: el.style.width,
          height: el.style.height
        };
        el.classList.add('maximized');
        state.isMaximized = true;
        if (maxBtn) {
          maxBtn.setAttribute('aria-label', 'Restore');
          maxBtn.title = 'Restore';
        }
      } else {
        el.classList.remove('maximized');
        if (state.restoreRect) {
          el.style.top = state.restoreRect.top;
          el.style.left = state.restoreRect.left;
          el.style.width = state.restoreRect.width;
          el.style.height = state.restoreRect.height;
        }
        state.isMaximized = false;
        if (maxBtn) {
          maxBtn.setAttribute('aria-label', 'Maximize');
          maxBtn.title = 'Maximize';
        }
      }
      focusWindow(winKey);
    }

    function handleTaskbarClick(winKey) {
      const el = document.getElementById(`win-${winKey}`);
      const state = windowState[winKey];
      if (el.style.display === 'none' || state.isMinimized) {
        el.style.display = 'flex';
        state.isMinimized = false;
        focusWindow(winKey);
      } else {
        const tb = el.querySelector('.win-caption');
        if (tb && !tb.classList.contains('inactive')) {
          minimizeWindow(winKey);
        } else {
          focusWindow(winKey);
        }
      }
    }

    function cascadeWindows() {
      const keys = ['agents', 'antigravity', 'codex', 'claude'];
      let top = 20;
      let left = 40;
      keys.forEach((k) => {
        const el = document.getElementById(`win-${k}`);
        if (el) {
          el.style.display = 'flex';
          el.classList.remove('maximized');
          windowState[k].isMaximized = false;
          windowState[k].isMinimized = false;
          el.style.top = `${top}px`;
          el.style.left = `${left}px`;
          el.style.width = '640px';
          el.style.height = '470px';
          top += 30;
          left += 30;
          focusWindow(k);
        }
      });
      playBeep(800, 0.08);
    }

    function showAbout() {
      openWindow('about');
    }

    // Start Menu
    function toggleStartMenu(force) {
      const m = document.getElementById('start-menu');
      if (typeof force === 'boolean') {
        m.style.display = force ? 'flex' : 'none';
      } else {
        m.style.display = m.style.display === 'flex' ? 'none' : 'flex';
      }
    }

    document.addEventListener('click', (e) => {
      const startBtn = document.getElementById('start-btn');
      const startMenu = document.getElementById('start-menu');
      if (!startBtn.contains(e.target) && !startMenu.contains(e.target)) {
        startMenu.style.display = 'none';
      }
    });

    // Window Dragger
    function startDrag(e, winId) {
      if (e.target.tagName.toLowerCase() === 'button') return;
      const win = document.getElementById(winId);
      if (!win || win.classList.contains('maximized')) return;

      const winKey = winId.replace('win-', '');
      focusWindow(winKey);

      let isDragging = true;
      const startX = e.clientX;
      const startY = e.clientY;
      const rect = win.getBoundingClientRect();
      const initialLeft = rect.left;
      const initialTop = rect.top;

      function onMouseMove(moveEvent) {
        if (!isDragging) return;
        const dx = moveEvent.clientX - startX;
        const dy = moveEvent.clientY - startY;
        win.style.left = `${Math.max(0, initialLeft + dx)}px`;
        win.style.top = `${Math.max(0, initialTop + dy)}px`;
      }

      function onMouseUp() {
        isDragging = false;
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
      }

      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
    }

    // Window Resizer
    function startResize(e, winId, direction) {
      e.preventDefault();
      e.stopPropagation();
      const win = document.getElementById(winId);
      if (!win || win.classList.contains('maximized')) return;

      const winKey = winId.replace('win-', '');
      focusWindow(winKey);

      const startX = e.clientX;
      const startY = e.clientY;
      const rect = win.getBoundingClientRect();
      const initialLeft = rect.left;
      const initialTop = rect.top;
      const initialWidth = rect.width;
      const initialHeight = rect.height;

      const minW = 320;
      const minH = 220;

      function onMouseMove(moveEvent) {
        const dx = moveEvent.clientX - startX;
        const dy = moveEvent.clientY - startY;

        if (direction.includes('r')) {
          win.style.width = `${Math.max(minW, initialWidth + dx)}px`;
        }
        if (direction.includes('b')) {
          win.style.height = `${Math.max(minH, initialHeight + dy)}px`;
        }
        if (direction.includes('l')) {
          const newWidth = Math.max(minW, initialWidth - dx);
          if (newWidth > minW) {
            win.style.width = `${newWidth}px`;
            win.style.left = `${initialLeft + dx}px`;
          }
        }
        if (direction.includes('t')) {
          const newHeight = Math.max(minH, initialHeight - dy);
          if (newHeight > minH) {
            win.style.height = `${newHeight}px`;
            win.style.top = `${initialTop + dy}px`;
          }
        }
      }

      function onMouseUp() {
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
      }

      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onMouseUp);
    }

    ['agents', 'antigravity', 'codex', 'claude', 'notepad', 'taskmgr'].forEach(key => {
      const el = document.getElementById(`win-${key}`);
      if (el) {
        el.addEventListener('mousedown', () => focusWindow(key));
      }
    });

    // -------------------------------------------------------------
    // RENDER AGENTS
    // -------------------------------------------------------------
    function renderAgents(list) {
      const tbody = document.getElementById('tbody-agents');
      tbody.innerHTML = '';

      document.getElementById('count-agents').textContent = list.length;
      document.getElementById('badge-agents').textContent = `Showing: ${list.length}`;
      document.getElementById('status-total-agents').textContent = `Total: ${list.length}`;

      list.forEach((agent, idx) => {
        const tr = document.createElement('tr');
        tr.id = `row-agent-${idx}`;
        tr.innerHTML = `
          <td><strong>${escapeHtml(agent.name)}</strong></td>
          <td><span class="detail-badge">${escapeHtml(agent.runtime)}</span></td>
          <td>${escapeHtml(agent.role || agent.model || 'Agent')}</td>
          <td title="${escapeHtml(agent.description)}">${escapeHtml(agent.description)}</td>
        `;

        tr.onclick = () => {
          tbody.querySelectorAll('tr').forEach(r => r.classList.remove('highlighted'));
          tr.classList.add('highlighted');
          showAgentDetail(agent);
          document.getElementById('status-agents').textContent = `Selected: ${agent.name} (${agent.runtime})`;
        };

        tr.ondblclick = () => {
          if (agent.path) openNotepad(agent.path, agent.name);
        };

        tbody.appendChild(tr);
      });

      if (list.length > 0) {
        tbody.children[0].click();
      } else {
        document.getElementById('detail-agents').innerHTML = `
          <div class="empty-state-notice">
            Agent runtime information is unavailable.
          </div>
        `;
      }
    }

    function showAgentDetail(agent) {
      const panel = document.getElementById('detail-agents');
      const toolsHtml = (agent.tools || []).map(t => `<span class="detail-badge" class="detail-badge badge-tool">${escapeHtml(t)}</span>`).join(' ');

      panel.innerHTML = `
        <div class="detail-header">
          <div class="detail-title">
            ${escapeHtml(agent.name)}
            <span class="detail-badge badge-active">● ${escapeHtml(agent.status || 'Unknown')}</span>
          </div>
          <div>
            <span class="detail-badge">${escapeHtml(agent.runtime)}</span>
            <span class="detail-badge" class="detail-badge badge-accent">${escapeHtml(agent.model || 'Unknown')}</span>
          </div>
        </div>
        <div class="detail-desc"><strong>Role:</strong> ${escapeHtml(agent.role || 'Assistant')}<br>${escapeHtml(agent.description)}</div>
        <div style="margin-bottom:6px;"><strong>Enabled Tools:</strong> ${toolsHtml || 'Standard Tools'}</div>
        <div class="detail-path">${escapeHtml(agent.path || 'Built-in Antigravity Subagent')}</div>
        <div class="detail-actions">
          ${agent.path ? `<button class="default" onclick="openNotepad('${escapeJs(agent.path)}', '${escapeJs(agent.name)}')">📝 View Config</button>` : ''}
          <button onclick="copyToClipboard('${escapeJs(agent.name)}', this)">📋 Copy Agent Name</button>
          ${agent.path ? `<button onclick="openFolderInExplorer('${escapeJs(agent.path)}')">📂 Reveal in Explorer</button>` : ''}
        </div>
      `;
    }

    function filterAgents() {
      const term = document.getElementById('search-agents').value.toLowerCase().trim();
      const all = RAW_DATA.agents || [];
      if (!term) {
        renderAgents(all);
        return;
      }
      const filtered = all.filter(a => 
        a.name.toLowerCase().includes(term) ||
        (a.description || '').toLowerCase().includes(term) ||
        (a.runtime || '').toLowerCase().includes(term) ||
        (a.role || '').toLowerCase().includes(term)
      );
      renderAgents(filtered);
    }

    // -------------------------------------------------------------
    // RENDER SKILLS
    // -------------------------------------------------------------
    function renderSkills(winKey, list) {
      const tbody = document.getElementById(`tbody-${winKey}`);
      if (!tbody) return;
      tbody.innerHTML = '';

      document.getElementById(`count-${winKey}`).textContent = list.length;
      document.getElementById(`badge-${winKey}`).textContent = `Showing: ${list.length}`;
      document.getElementById(`status-total-${winKey}`).textContent = `Total: ${list.length}`;

      list.forEach((skill, idx) => {
        const tr = document.createElement('tr');
        tr.id = `row-${winKey}-${idx}`;
        tr.tabIndex = 0;
        tr.setAttribute('aria-label', `${skill.name}, ${skill.source}`);
        tr.onkeydown = event => {
          if (event.key === 'Enter') { event.preventDefault(); openNotepad(skill.path, skill.name); }
          if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault();
            const next = event.key === 'ArrowDown' ? tr.nextElementSibling : tr.previousElementSibling;
            if (next) { next.focus(); next.click(); }
          }
        };
        tr.innerHTML = `
          <td><strong>${escapeHtml(skill.name)}</strong></td>
          <td><span class="detail-badge">${escapeHtml(skill.source)}</span></td>
          <td title="${escapeHtml(skill.full_desc)}">${escapeHtml(skill.short_desc)}</td>
        `;

        tr.onclick = () => {
          tbody.querySelectorAll('tr').forEach(r => r.classList.remove('highlighted'));
          tr.classList.add('highlighted');
          showDetail(winKey, skill);
          document.getElementById(`status-${winKey}`).textContent = `Selected: ${skill.name}`;
        };

        tr.ondblclick = () => {
          openNotepad(skill.path, skill.name);
        };

        tbody.appendChild(tr);
      });

      if (list.length > 0) {
        tbody.children[0].click();
      } else {
        document.getElementById(`detail-${winKey}`).innerHTML = `
          <div class="empty-state-notice">
            No matching skills found.
          </div>
        `;
      }
    }

    function showDetail(winKey, skill) {
      const panel = document.getElementById(`detail-${winKey}`);
      panel.innerHTML = `<div class="detail-header"><div class="detail-title"></div><span class="detail-badge"></span></div><div class="detail-desc"></div><div class="detail-path"></div><div class="detail-actions"></div>`;
      panel.querySelector('.detail-title').textContent = skill.name;
      panel.querySelector('.detail-badge').textContent = skill.source;
      panel.querySelector('.detail-desc').textContent = skill.full_desc;
      panel.querySelector('.detail-path').textContent = skill.path;
      const actions = panel.querySelector('.detail-actions');
      const add = (label, action, className = '') => {
        const button = document.createElement('button'); button.textContent = label; button.className = className; button.addEventListener('click', action); actions.appendChild(button);
      };
      add('Edit SKILL.md (Notepad)', () => openNotepad(skill.path, skill.name), 'default');
      add('📂 Reveal in Explorer', () => openFolderInExplorer(skill.path));
      add('Copy Name', event => copyToClipboard(skill.name, event.currentTarget));
      add('Copy Path', event => copyToClipboard(skill.path, event.currentTarget));
      add('Delete…', () => promptDeleteSkill(skill.name, skill.path), 'btn-label-danger');
    }

    function filterSkills(winKey) {
      const term = document.getElementById(`search-${winKey}`).value.toLowerCase().trim();
      const source = document.getElementById(`source-${winKey}`).value;
      const filtered = (RAW_DATA[winKey] || []).filter(skill =>
        (!source || skill.source === source) &&
        [skill.name, skill.full_desc, skill.source, skill.path].some(value => (value || '').toLowerCase().includes(term))
      );
      const state = windowState[winKey];
      filtered.sort((a, b) => String(a[state.sortCol] || '').localeCompare(String(b[state.sortCol] || ''), undefined, {sensitivity: 'base'}) * (state.sortAsc ? 1 : -1));
      renderSkills(winKey, filtered);
    }

    function refreshCatalog() {
      document.getElementById('scan-errors-button').textContent = `Scan errors: ${(RAW_DATA.scan_errors || []).length}`;
      document.getElementById('catalog-updated').textContent = RAW_DATA.updated_at ? `Last scan: ${new Date(RAW_DATA.updated_at).toLocaleString()}` : 'Scan time unavailable';
      ['antigravity', 'codex', 'claude'].forEach(key => {
        const select = document.getElementById(`source-${key}`);
        const old = select.value;
        select.replaceChildren(new Option('All sources', ''));
        [...new Set((RAW_DATA[key] || []).map(item => item.source))].sort().forEach(source => select.add(new Option(source, source)));
        select.value = [...select.options].some(option => option.value === old) ? old : '';
        filterSkills(key);
      });
      filterAgents();
      renderGlobalSearch();
    }

    function clearSearch(winKey) {
      if (winKey === 'agents') {
        document.getElementById('search-agents').value = '';
        filterAgents();
      } else {
        document.getElementById(`search-${winKey}`).value = '';
        document.getElementById(`source-${winKey}`).value = '';
        filterSkills(winKey);
      }
    }

    function sortTable(winKey, col) {
      const state = windowState[winKey];
      if (state.sortCol === col) {
        state.sortAsc = !state.sortAsc;
      } else {
        state.sortCol = col;
        state.sortAsc = true;
      }

      if (winKey === 'agents') {
        const all = RAW_DATA.agents || [];
        all.sort((a, b) => {
          const valA = (a[col] || '').toLowerCase();
          const valB = (b[col] || '').toLowerCase();
          if (valA < valB) return state.sortAsc ? -1 : 1;
          if (valA > valB) return state.sortAsc ? 1 : -1;
          return 0;
        });
        filterAgents();
      } else {
        const all = RAW_DATA[winKey] || [];
        all.sort((a, b) => {
          const valA = (a[col] || '').toLowerCase();
          const valB = (b[col] || '').toLowerCase();
          if (valA < valB) return state.sortAsc ? -1 : 1;
          if (valA > valB) return state.sortAsc ? 1 : -1;
          return 0;
        });
        filterSkills(winKey);
      }
    }

    // -------------------------------------------------------------
    // AI TASK MANAGER LOGIC
    // -------------------------------------------------------------
    function switchTaskmgrTab(tabId) {
      ['perf', 'procs', 'apps'].forEach(t => {
        const panel = document.getElementById(`tabpanel-${t}`);
        if (panel) panel.style.display = (t === tabId ? 'flex' : 'none');
        const tabLi = document.getElementById(`tab-li-${t}`);
        if (tabLi) {
          if (t === tabId) {
            tabLi.setAttribute('aria-selected', 'true');
          } else {
            tabLi.removeAttribute('aria-selected');
          }
        }
      });
      if (tabId === 'apps') updateTaskmgrApps();
    }

    function updateTaskmgrApps() {
      const tbody = document.getElementById('taskmgr-apps-list');
      tbody.innerHTML = '';
      const openWins = ['agents', 'antigravity', 'codex', 'claude', 'notepad', 'taskmgr'];
      openWins.forEach(key => {
        const win = document.getElementById(`win-${key}`);
        if (win && win.style.display !== 'none') {
          const tr = document.createElement('tr');
          const title = win.querySelector('.win-caption-text').textContent.trim();
          tr.innerHTML = `<td>${title}</td><td>Running</td>`;
          tr.onclick = () => {
            tbody.querySelectorAll('tr').forEach(r => r.classList.remove('highlighted'));
            tr.classList.add('highlighted');
            tr.dataset.winKey = key;
          };
          tbody.appendChild(tr);
        }
      });
      if (tbody.children.length > 0) tbody.children[0].click();
    }

    function endSelectedTask() {
      const sel = document.querySelector('#taskmgr-apps-list tr.highlighted');
      if (sel && sel.dataset.winKey) {
        closeWindow(sel.dataset.winKey);
        updateTaskmgrApps();
        showToast('Application terminated.');
      }
    }

    // Oscilloscope canvas animation
    const canvas = document.getElementById('cpu-canvas');
    const ctx = canvas.getContext('2d');
    const waveData = new Array(60).fill(15);
    function drawWave() {
      waveData.shift();
      waveData.push(Math.floor(Math.random() * 45) + 10);

      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Grid
      ctx.strokeStyle = '#003300';
      ctx.lineWidth = 1;
      for (let x = 0; x < canvas.width; x += 20) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke();
      }
      for (let y = 0; y < canvas.height; y += 15) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke();
      }

      // Waveform
      ctx.strokeStyle = '#00ff00';
      ctx.lineWidth = 2;
      ctx.beginPath();
      const step = canvas.width / (waveData.length - 1);
      waveData.forEach((val, i) => {
        const x = i * step;
        const y = canvas.height - val;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    }
    setInterval(drawWave, 250);

    // -------------------------------------------------------------
    // RUN DIALOG
    // -------------------------------------------------------------
    function executeRun() {
      const query = document.getElementById('run-input').value.toLowerCase().trim();
      closeWindow('run');
      if (!query) return;

      // Check agents
      const agent = (RAW_DATA.agents || []).find(a => a.name.toLowerCase() === query);
      if (agent) {
        openWindow('agents');
        document.getElementById('search-agents').value = query;
        filterAgents();
        showToast(`Found agent ${agent.name}`);
        return;
      }

      // Check skills
      for (const k of ['antigravity', 'codex', 'claude']) {
        const sk = (RAW_DATA[k] || []).find(s => s.name.toLowerCase() === query);
        if (sk) {
          openWindow(k);
          document.getElementById(`search-${k}`).value = query;
          filterSkills(k);
          showToast(`Found skill ${sk.name} in ${k}`);
          return;
        }
      }

      showToast(`No exact match for "${query}". Opening general search.`);
      openWindow('antigravity');
      document.getElementById('search-antigravity').value = query;
      filterSkills('antigravity');
    }

    // -------------------------------------------------------------
    // FILE ACTIONS (Edit, Delete, Create, Reveal)
    // -------------------------------------------------------------
    const editor = { baseline: '', version: null, busy: false, changedOnDisk: false, pollBusy: false };
    const editorText = document.getElementById('notepad-content');
    function editorDirty() { return !!windowState.notepad.currentPath && editorText.value !== editor.baseline; }
    function updateEditorTitle() {
      document.getElementById('notepad-title').textContent = `Notepad - ${windowState.notepad.currentSkillName || 'SKILL.md'}${editorDirty() ? ' *' : ''}`;
    }
    function canLeaveNotepad() {
      if (editor.busy) { alert('Please wait for the current file operation to finish.'); return false; }
      return !editorDirty() || confirm('There are unsaved changes. Discard them?');
    }
    editorText.addEventListener('input', updateEditorTitle);
    window.addEventListener('beforeunload', event => {
      if (editorDirty() || editor.busy) { event.preventDefault(); event.returnValue = ''; }
    });
    async function openNotepad(path, name) {
      if (!canLeaveNotepad()) return;
      editor.busy = true;
      editorText.readOnly = true;
      try {
        const response = await fetch('/api/skills/read', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: jsonReq({path})});
        const result = await response.json();
        if (!result.success) throw new Error(result.error);
        windowState.notepad.currentPath = path;
        windowState.notepad.currentSkillName = name;
        editorText.value = result.content;
        editor.baseline = editorText.value;
        editor.version = result.version;
        editor.changedOnDisk = false;
        updateEditorTitle();
        document.getElementById('notepad-status').textContent = `Editing ${name}`;
        openWindow('notepad');
      } catch (err) { alert('Error opening file: ' + err.message); }
      finally { editor.busy = false; editorText.readOnly = false; }
    }
    async function saveNotepadContent() {
      const path = windowState.notepad.currentPath;
      if (!path || editor.busy) return;
      const content = editorText.value;
      editor.busy = true;
      document.getElementById('notepad-status').textContent = 'Saving…';
      try {
        const response = await fetch('/api/skills/save', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: jsonReq({path, content, version: editor.version})});
        const result = await response.json();
        if (!result.success) {
          if (result.conflict) editor.changedOnDisk = true;
          document.getElementById('notepad-status').textContent = result.conflict ? 'File changed on disk — your edits are preserved' : 'Save failed';
          alert(result.error); return;
        }
        editor.baseline = content;
        editor.version = result.version;
        editor.changedOnDisk = false;
        updateEditorTitle();
        document.getElementById('notepad-status').textContent = editorDirty() ? 'Saved earlier version; newer edits are unsaved' : 'Saved successfully';
        if (result.data) { RAW_DATA = result.data; refreshCatalog(); }
        if (result.warning) alert(result.warning); else showToast('File saved and catalog updated');
      } catch (err) { document.getElementById('notepad-status').textContent = 'Save failed'; alert('Save failed: ' + err.message); }
      finally { editor.busy = false; }
    }
    async function checkEditorFile() {
      const path = windowState.notepad.currentPath;
      if (!path || editor.busy || editor.pollBusy || editor.changedOnDisk) return;
      editor.pollBusy = true;
      const expectedVersion = editor.version;
      try {
        const response = await fetch('/api/skills/read', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: jsonReq({path})});
        const result = await response.json();
        if (path !== windowState.notepad.currentPath || editor.busy || expectedVersion !== editor.version) return;
        if (!result.success || result.version !== editor.version) {
          editor.changedOnDisk = true;
          document.getElementById('notepad-status').textContent = 'File changed or became unavailable on disk — your edits are preserved';
          alert('The open file changed or became unavailable on disk. Your editor text has been preserved. Reopen the file to load the disk version.');
        }
      } catch (_) { /* A temporary server outage is not evidence of a file change. */ }
      finally { editor.pollBusy = false; }
    }
    setInterval(checkEditorFile, 10000);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) checkEditorFile(); });

    function promptDeleteSkill(name, path) {
      deleteTarget = { name: name, path: path };
      document.getElementById('delete-skill-name').textContent = `"${name}"`;
      document.getElementById('delete-skill-path').textContent = path;
      const modal = document.getElementById('win-delete-confirm');
      modal.style.display = 'block';
      topZ += 50;
      modal.style.zIndex = topZ;
      playBeep(300, 0.2, 'square');
    }

    function closeDeleteDialog() {
      document.getElementById('win-delete-confirm').style.display = 'none';
      deleteTarget = null;
    }

    function confirmDeleteSkill() {
      if (!deleteTarget) return;
      const target = deleteTarget;
      closeDeleteDialog();

      showToast(`Deleting ${target.name}…`);
      fetch('/api/skills/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: jsonReq({ path: target.path })
      })
      .then(r => r.json())
      .then(res => {
        if (res.success) {
          showToast(`Deleted ${target.name}`);
          RAW_DATA = res.data;
          refreshCatalog();
        } else {
          alert("Failed to delete skill: " + res.error);
        }
      });
    }

    function openNewSkillDialog(defaultRuntime) {
      if (defaultRuntime) {
        document.getElementById('new-skill-runtime').value = defaultRuntime;
      }
      document.getElementById('new-skill-name').value = '';
      document.getElementById('new-skill-desc').value = '';
      const modal = document.getElementById('win-new-skill');
      modal.style.display = 'block';
      topZ += 50;
      modal.style.zIndex = topZ;
      setTimeout(() => document.getElementById('new-skill-name').focus(), 50);
    }

    function closeNewSkillDialog() {
      document.getElementById('win-new-skill').style.display = 'none';
    }

    function submitCreateSkill() {
      const runtime = document.getElementById('new-skill-runtime').value;
      const name = document.getElementById('new-skill-name').value.trim();
      const desc = document.getElementById('new-skill-desc').value.trim();

      if (!name) {
        alert("Please enter a skill name!");
        return;
      }

      closeNewSkillDialog();
      showToast(`Creating skill "${name}"…`);

      fetch('/api/skills/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: jsonReq({ runtime: runtime, name: name, description: desc })
      })
      .then(r => r.json())
      .then(res => {
        if (res.success) {
          showToast(`Skill "${name}" created!`);
          RAW_DATA = res.data;
          refreshCatalog();
          openWindow(runtime);
          openNotepad(res.path, name);
        } else {
          alert("Error creating skill: " + res.error);
        }
      });
    }

    function openFolderInExplorer(path) {
      showToast('Opening in Windows Explorer…');
      fetch('/api/skills/open_folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: jsonReq({ path: path })
      });
    }

    function rescanAllSkills(silent) {
      if (!silent) showToast('Rescanning skills & agents on disk…');
      fetch('/api/skills/rescan', { method: 'POST' })
        .then(r => r.json())
        .then(res => {
          if (res.success) {
            RAW_DATA = res.data;
            refreshCatalog();
            if (!silent) showToast('Database updated successfully!');
          } else { alert('Scan failed: ' + res.error); }
        }).catch(err => alert('Scan failed: ' + err.message));
    }

    function copyToClipboard(text, btn) {
      navigator.clipboard.writeText(text).then(() => {
        const old = btn.textContent;
        btn.textContent = 'Copied!';
        playBeep(900, 0.05);
        setTimeout(() => btn.textContent = old, 1500);
      });
    }

    function escapeHtml(str) {
      return (str || '').replace(/[&<>"']/g, m => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
      }[m]));
    }

    function escapeJs(str) {
      return (str || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/"/g, '\\"');
    }

    function jsonReq(obj) {
      return JSON.stringify(obj);
    }

    async function openScanConfig() {
      const dialog = document.getElementById('scan-config-dialog');
      const error = document.getElementById('scan-config-error');
      error.textContent = '';
      try {
        const result = await (await fetch('/api/skills/config')).json();
        if (!result.success) throw new Error(result.error);
        document.getElementById('scan-config-text').value = JSON.stringify(result.config, null, 2);
        dialog.showModal();
      } catch (err) { alert('Cannot load scan configuration: ' + err.message); }
    }
    async function saveScanConfig() {
      const error = document.getElementById('scan-config-error');
      try {
        const config = JSON.parse(document.getElementById('scan-config-text').value);
        const result = await (await fetch('/api/skills/config', {method:'POST', headers:{'Content-Type':'application/json'}, body:jsonReq({config})})).json();
        if (!result.success) throw new Error(result.error);
        RAW_DATA = result.data; refreshCatalog();
        document.getElementById('scan-config-dialog').close();
        showToast('Scan folders saved and catalog refreshed');
      } catch (err) { error.textContent = err.message; }
    }
    function showScanErrors() {
      const errors = RAW_DATA.scan_errors || [];
      const list = document.getElementById('scan-errors-list'); list.replaceChildren();
      document.getElementById('scan-errors-info').textContent = errors.length ? `${errors.length} issues from the last scan:` : 'No errors in the last scan.';
      errors.forEach(error => { const item = document.createElement('li'); item.textContent = `${error.path}: ${error.message}`; list.appendChild(item); });
      document.getElementById('scan-errors-dialog').showModal();
    }

    const globalSearch = document.getElementById('global-search');
    const globalInput = document.getElementById('search-all');
    function openGlobalSearch() { globalSearch.style.display = 'block'; renderGlobalSearch(); globalInput.focus(); }
    function closeGlobalSearch() { globalSearch.style.display = 'none'; document.getElementById('search-all-open').focus(); }
    function renderGlobalSearch() {
      const results = document.getElementById('search-all-results');
      results.replaceChildren();
      const query = globalInput.value.trim().toLowerCase();
      if (!query) { results.textContent = 'Type to search across all skill catalogs.'; return; }
      let count = 0;
      ['antigravity', 'codex', 'claude'].forEach(key => (RAW_DATA[key] || []).forEach(skill => {
        if (![skill.name, skill.full_desc, skill.source, skill.path].some(v => (v || '').toLowerCase().includes(query))) return;
        count++;
        if (count > 100) return;
        const button = document.createElement('button');
        button.type = 'button'; button.className = 'global-result';
        button.textContent = `${skill.name} — ${key} / ${skill.source} — ${skill.path}`;
        button.addEventListener('click', () => {
          closeGlobalSearch(); openWindow(key);
          document.getElementById(`search-${key}`).value = skill.path;
          document.getElementById(`source-${key}`).value = '';
          filterSkills(key);
          showDetail(key, skill);
          document.getElementById(`status-${key}`).textContent = `Selected: ${skill.name}`;
        });
        results.appendChild(button);
      }));
      if (!count) results.textContent = 'No matching skills.';
      else if (count > 100) { const info = document.createElement('p'); info.textContent = `Showing 100 of ${count} results. Refine your search.`; results.appendChild(info); }
    }
    document.getElementById('search-all-open').addEventListener('click', openGlobalSearch);
    document.getElementById('search-all-close').addEventListener('click', closeGlobalSearch);
    globalInput.addEventListener('input', renderGlobalSearch);
    document.addEventListener('keydown', event => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); openGlobalSearch(); }
      else if (event.key === 'Escape' && globalSearch.style.display === 'block') closeGlobalSearch();
    });

    // Initial Data Load
    fetch('/api/skills/list')
      .then(r => r.json())
      .then(data => {
        RAW_DATA = data;
        refreshCatalog();
      })
      .catch(() => {
        if (window.SKILLS_DATA) {
          RAW_DATA = window.SKILLS_DATA;
          refreshCatalog();
        }
      });


