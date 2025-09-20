/* Role Architect UI logic: list and wizard */

const RoleArchitect = (() => {
  async function fetchJSON(url, opts = {}) {
    const base = { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' };
    // If sending a body and no explicit content-type set, default to JSON
    if (opts && opts.body && (!opts.headers || !opts.headers['Content-Type'])) {
      base.headers['Content-Type'] = 'application/json';
    }
    const res = await fetch(url, Object.assign(base, opts));
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    return await res.json();
  }

  // List page
  async function loadList() {
    const tbody = document.getElementById('roles-tbody');
    const isAdmin = (document.getElementById('roles-table-wrap')?.dataset?.isAdmin === '1');
    const search = (document.getElementById('roles-search')?.value || '').trim();
    try {
      tbody.innerHTML = '<tr><td colspan="6">Loading…</td></tr>';
      const q = search ? `?q=${encodeURIComponent(search)}` : '';
      const data = await fetchJSON(`/api/roles${q}`);
      console.debug('Roles API data:', data);
      if (!data.roles || data.roles.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No role profiles yet. Click "Create Role Profile" to start.</td></tr>';
        return;
      }
      function fmtDate(dstr){
        try{
          if(!dstr) return '—';
          // Normalize "YYYY-MM-DD HH:MM:SS" to ISO-like for safer parsing
          const iso = dstr.includes('T') ? dstr : dstr.replace(' ', 'T');
          const d = new Date(iso);
          if(isNaN(d.getTime())) return dstr; // fallback to raw value
          return d.toLocaleDateString();
        }catch{ return dstr || '—'; }
      }
      tbody.innerHTML = data.roles.map(r => {
        const created = fmtDate(r.created_date);
        const editHref = isAdmin ? `/admin/roles/new#edit=${r.id}` : `/roles/new#edit=${r.id}`;
        return `
          <tr data-id="${r.id}">
            <td><input type="checkbox" class="row-check"></td>
            <td>${escapeHtml(r.name)}</td>
            <td>${escapeHtml(r.department || '')}</td>
            <td>${r.is_active ? 'Active' : 'Inactive'}</td>
            <td>${created}</td>
            <td>
              <a class="btn" href="${editHref}">Edit</a>
            </td>
          </tr>
        `;
      }).join('');
    } catch (e) {
      console.error(e);
      tbody.innerHTML = `<tr><td colspan="6" class="error">Failed to load roles.</td></tr>`;
    }
  }

  function bindListEvents() {
    const searchEl = document.getElementById('roles-search');
    const refreshBtn = document.getElementById('roles-refresh');
    const compareBtn = document.getElementById('compare-reports');
    if (searchEl) searchEl.addEventListener('input', debounce(loadList, 300));
    if (refreshBtn) refreshBtn.addEventListener('click', loadList);
    if (compareBtn) compareBtn.addEventListener('click', () => {
      // Placeholder: later will navigate to /reports comparison with selected report IDs
      alert('Comparison view will be available in Reports.');
    });
    const tbody = document.getElementById('roles-tbody');
    if (tbody) {
      tbody.addEventListener('change', (e) => {
        if (e.target && e.target.classList.contains('row-check')) {
          const checked = tbody.querySelectorAll('.row-check:checked').length;
          compareBtn.disabled = checked !== 2;
        }
      });
    }
  }

  function initList() {
    bindListEvents();
    loadList();
  }

  // Wizard
  const steps = ['basics','knowledge','skills','abilities','others','targets','review'];
  let state = {
    roleId: null,
    name: '',
    description: '',
    department: '',
    knowledge: [],
    skills: [],
    abilities: [],
    others: [],
    // targets: [{ competency_id, competency_name?, target_level, weight }]
    targets: [],
    targetDefaults: { target: 3 },
    pendingTarget: null, // { id, name, level }
  };
  let stepIndex = 0;
  // lightweight cache for competencies (flattened across frameworks)
  let _competencyCache = null; // [{id, name, framework_id, framework_name}]

  function renderStep() {
    const mount = document.getElementById('role-wizard');
    if (!mount) return;
    const step = steps[stepIndex];
    let html = '';
    if (step === 'basics') {
      html = `
        <div class="grid two">
          <label class="field"><span>Role Name</span>
            <input id="role-name" value="${escapeAttr(state.name)}" placeholder="e.g., Shift Supervisor" />
          </label>
          <label class="field"><span>Department</span>
            <input id="role-dept" value="${escapeAttr(state.department)}" placeholder="e.g., Operations" />
          </label>
        </div>
        <label class="field"><span>Description</span>
          <textarea id="role-desc" placeholder="Describe the primary purpose, key responsibilities, and overall contribution of this role within the organization.">${escapeHtml(state.description)}</textarea>
        </label>
      `;
    } else if (step === 'knowledge' || step === 'skills' || step === 'abilities') {
      const key = step;
      const items = state[key] || [];
      html = `
        <div class="list-editor">
          <h3 style="margin:0 0 8px 0;">${key.charAt(0).toUpperCase()+key.slice(1)}</h3>
          <div class="row gap">
            <input id="item-input" placeholder="Enter a ${key === 'knowledge' ? 'knowledge area' : key === 'skills' ? 'skill' : 'ability'}…" autocomplete="off" />
            <input id="item-notes" placeholder="Notes (optional)" />
            <button id="item-add" class="btn">Add</button>
          </div>
          <div id="ksao-results" class="ksao-results" role="listbox" aria-label="Suggestions"></div>
          <ul id="item-list" class="chips mt">
            ${items.map((x,i)=>`<li class="chip" data-idx="${i}" draggable="true"><span class="chip-label">${escapeHtml(x.name)}${x.description? ' — '+escapeHtml(x.description): ''}</span><button aria-label="Remove" data-action="del" data-idx="${i}" class="chip-x">×</button></li>`).join('')}
          </ul>
        </div>
      `;
    } else if (step === 'others') {
      const key = step;
      const items = state[key] || [];
      html = `
        <div class="list-editor">
          <h3 style="margin:0 0 8px 0;">Certifications & Other Requirements</h3>
          <div class="row gap">
            <input id="other-name" placeholder="Certification/Requirement name (e.g., First Aid Certification)" />
            <input id="other-notes" placeholder="Notes (optional, e.g., Must be renewed annually)" />
            <button id="other-add" class="btn">Add</button>
          </div>
          <ul id="item-list" class="chips mt">
            ${items.map((x,i)=>`<li class="chip" data-idx="${i}"><span class="chip-label">${escapeHtml(x.name)}${x.description? ' — '+escapeHtml(x.description): ''}</span><button aria-label="Remove" data-action="del" data-idx="${i}" class="chip-x">×</button></li>`).join('')}
          </ul>
        </div>
      `;
    } else if (step === 'targets') {
      // Targets UI: role-level target only
      html = `
        <h3 style="margin:0 0 8px;">Set Target Levels for Role</h3>
        <div class="targets-intro notice">Define the ideal competency levels for this role. Search for competencies by name and set their desired proficiency level (1–5) expected for anyone in this position.</div>
        <div class="comp-search-wrap">
          <label class="field" style="margin-bottom: 0;">
            <span>Search Competencies</span>
            <input id="comp-search" placeholder="Type to search (e.g., Strategic Acumen)" autocomplete="off" />
          </label>
          <div id="comp-results" class="comp-results" role="listbox" aria-label="Competency results"></div>
        </div>
        <div class="t-defaults mt" id="t-defaults" style="display:flex; gap:16px; align-items:center;">
          <div style="display:grid; gap:6px; min-width:260px;">
            <label for="def-tgt">Target Level for Role (1–5)</label>
            <input type="range" id="def-tgt" min="1" max="5" step="1" value="${Number(state.targetDefaults?.target||3)}" />
            <div class="hint">1: Foundational · 2: Basic · 3: Proficient · 4: Advanced · 5: Expert</div>
          </div>
        </div>

        ${state.pendingTarget ? `
          <div class="target-row mt" id="pending-target">
            <div class="t-head">
              <div class="t-title">${escapeHtml(state.pendingTarget.name)}</div>
              <button class="btn" id="pt-clear">✕</button>
            </div>
            <div class="t-sliders">
              <div class="slider-block">
                <label for="pt-slider">Target Level for Role</label>
                <input type="range" id="pt-slider" min="1" max="5" step="1" value="${Number(state.pendingTarget.level||Number(state.targetDefaults?.target||3))}" />
                <div class="lvl-value" id="pt-value">${Number(state.pendingTarget.level||Number(state.targetDefaults?.target||3))}: ${levelLabel(Number(state.pendingTarget.level||Number(state.targetDefaults?.target||3)))}</div>
                <div class="hint">1: Foundational · 5: Expert</div>
              </div>
            </div>
            <div class="wizard-actions" style="margin-top:12px;">
              <button class="btn primary" id="pt-add">+ Add Competency</button>
            </div>
          </div>
        ` : ''}

        <div class="targets-summary mt" id="targets-summary">
          ${state.targets.length === 0 ? `<div class="no-data-message">No competencies added yet. Use the search above to add.</div>` : ''}
          ${[...state.targets].sort((a,b)=> (a.competency_name||'').localeCompare(b.competency_name||'')).map((t) => `
            <div class="target-row" data-cid="${t.competency_id}">
              <div class="t-head">
                <div class="t-title">${escapeHtml(t.competency_name || ('#'+t.competency_id))}</div>
                <button class="btn t-remove" data-action="del" data-cid="${t.competency_id}" aria-label="Remove ${escapeAttr(t.competency_name || ('#'+t.competency_id))}">✕</button>
              </div>
              <div class="t-sliders">
                <div class="slider-block">
                  <label for="tgt-${i}">Target Level for Role</label>
                  <input type="range" id="tgt-${t.competency_id}" class="lvl-slider" min="1" max="5" step="1" value="${Number(t.target_level||Number(state.targetDefaults?.target||3))}" data-cid="${t.competency_id}" data-kind="target"/>
                  <div class="lvl-value" aria-live="polite">${Number(t.target_level||Number(state.targetDefaults?.target||3))}: ${levelLabel(Number(t.target_level||Number(state.targetDefaults?.target||3)))}</div>
                  <div class="hint">1: Foundational · 5: Expert</div>
                </div>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    } else if (step === 'review') {
      const chips = (arr) => arr.length
        ? `<ul class="chips">${arr.map(x=>`<li class=\"chip\"><span class=\"chip-label\">${escapeHtml(x.name)}${x.description? ' — '+escapeHtml(x.description): ''}</span></li>`).join('')}</ul>`
        : '<div class="no-data-message">No items specified</div>';
      html = `
        <div class="review-grid">
          <div class="review-card">
            <div class="review-head">
              <h3>Basics</h3>
              <a href="#" class="edit-link" data-edit="basics">Edit</a>
            </div>
            <div class="review-body">
              <div class="grid two">
                <label class="field"><span>Role</span>
                  <span class="field-value">${escapeHtml(state.name || '—')}</span>
                </label>
                <label class="field"><span>Department</span>
                  <span class="field-value">${escapeHtml(state.department || '—')}</span>
                </label>
              </div>
              <p>${escapeHtml(state.description || '—')}</p>
            </div>
          </div>

          <div class="review-card">
            <div class="review-head">
              <h3>Knowledge</h3>
              <a href="#" class="edit-link" data-edit="knowledge">Edit</a>
            </div>
            <div class="review-body">${chips(state.knowledge)}</div>
          </div>

          <div class="review-card">
            <div class="review-head">
              <h3>Skills</h3>
              <a href="#" class="edit-link" data-edit="skills">Edit</a>
            </div>
            <div class="review-body">${chips(state.skills)}</div>
          </div>

          <div class="review-card">
            <div class="review-head">
              <h3>Abilities</h3>
              <a href="#" class="edit-link" data-edit="abilities">Edit</a>
            </div>
            <div class="review-body">${chips(state.abilities)}</div>
          </div>

          <div class="review-card">
            <div class="review-head">
              <h3>Certifications & Other Requirements</h3>
              <a href="#" class="edit-link" data-edit="others">Edit</a>
            </div>
            <div class="review-body">${chips(state.others)}</div>
          </div>

          <div class="review-card wide">
            <div class="review-head">
              <h3>Targets (Role-level)</h3>
              <a href="#" class="edit-link" data-edit="targets">Edit</a>
            </div>
            <div class="review-body">
              ${state.targets.length ? `
                <table class="review-table">
                  <thead><tr><th>Competency</th><th>Target Level</th><th>Proficiency</th></tr></thead>
                  <tbody>
                    ${[...state.targets].sort((a,b)=> (a.competency_name||'').localeCompare(b.competency_name||'')).map(t=>{
                      const n = Number(t.target_level||3);
                      return `<tr><td>${escapeHtml(t.competency_name || ('#'+t.competency_id))}</td><td>${n}</td><td>${levelLabel(n)}</td></tr>`;
                    }).join('')}
                  </tbody>
                </table>
              ` : '<div class="no-data-message">No targets specified</div>'}
            </div>
          </div>
        </div>
      `;
    }
    if (!mount) {
      console.warn('RoleArchitect: wizard mount not found');
      return;
    }
    mount.innerHTML = html;
    bindStepEvents();
    updateWizardButtons();
    updateStepper();
  }

  function bindStepEvents() {
    const step = steps[stepIndex];
    if (step === 'basics') {
      const name = document.getElementById('role-name');
      const dept = document.getElementById('role-dept');
      const desc = document.getElementById('role-desc');
      name?.addEventListener('input', () => state.name = name.value);
      dept?.addEventListener('input', () => state.department = dept.value);
      desc?.addEventListener('input', () => state.description = desc.value);
    } else if (step === 'knowledge' || step === 'skills' || step === 'abilities') {
      const key = step;
      const input = document.getElementById('item-input');
      const notes = document.getElementById('item-notes');
      const addBtn = document.getElementById('item-add');
      const list = document.getElementById('item-list');
      const results = document.getElementById('ksao-results');
      function exists(v){
        const name = (v||'').trim().toLowerCase();
        return (state[key]||[]).some(x => (x.name||'').trim().toLowerCase() === name);
      }
      function addItem(from){
        const v = (input.value || '').trim();
        const d = (notes.value || '').trim();
        if (!v) return;
        if (exists(v)) { showToast('That item already exists', 'info'); return; }
        state[key].push({ name: v, description: d || undefined });
        renderStep();
        if (from !== 'click') input.focus();
      }
      addBtn?.addEventListener('click', () => {
        addItem('click');
      });
      input?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); addItem('enter'); }
      });
      // Suggestions: search metrics/playbook
      input?.addEventListener('input', debounce(async () => {
        const q = (input.value || '').trim();
        if (!q || q.length < 2) { results.style.display = 'none'; results.innerHTML=''; return; }
        try {
          const data = await fetchJSON(`/api/metrics?search=${encodeURIComponent(q)}&per_page=10`);
          const items = (data.metrics||[]).map(m => m.name).filter(Boolean);
          if (items.length === 0) {
            // fallback suggestions
            const s = await fetchJSON(`/api/search/suggestions?q=${encodeURIComponent(q)}&limit=8`);
            const sugg = s.suggestions || [];
            results.innerHTML = sugg.map(n => `<div class="ksao-item" role="option" data-name="${escapeAttr(n)}">${escapeHtml(n)}</div>`).join('');
          } else {
            results.innerHTML = items.map(n => `<div class="ksao-item" role="option" data-name="${escapeAttr(n)}">${escapeHtml(n)}</div>`).join('');
          }
          results.style.display = 'block';
        } catch(e){ results.style.display = 'none'; results.innerHTML=''; }
      }, 200));
      results?.addEventListener('click', (e) => {
        const el = e.target.closest('.ksao-item');
        if (!el) return;
        const v = el.dataset.name || '';
        if (!exists(v)) {
          state[key].push({ name: v });
          renderStep();
        } else { showToast('That item already exists', 'info'); }
      });
      list?.addEventListener('click', (e) => {
        const tgt = e.target;
        if (tgt && tgt.dataset && tgt.dataset.action === 'del') {
          const idx = parseInt(tgt.dataset.idx, 10);
          state[key].splice(idx, 1);
          renderStep();
        }
      });
      // Drag & drop sorting
      let dragIdx = null;
      list?.addEventListener('dragstart', (e) => {
        const li = e.target.closest('.chip');
        if (!li) return; dragIdx = parseInt(li.dataset.idx, 10); li.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
      });
      list?.addEventListener('dragend', (e) => {
        const li = e.target.closest('.chip'); li?.classList.remove('dragging'); dragIdx = null;
      });
      list?.addEventListener('dragover', (e) => {
        e.preventDefault();
        const over = e.target.closest('.chip');
        if (!over) return;
        const overIdx = parseInt(over.dataset.idx, 10);
        if (isNaN(dragIdx) || isNaN(overIdx) || dragIdx === overIdx) return;
        const arr = state[key];
        const [moved] = arr.splice(dragIdx, 1);
        arr.splice(overIdx, 0, moved);
        dragIdx = overIdx;
        // re-render to update indexes
        renderStep();
      });
    } else if (step === 'others') {
      const nameEl = document.getElementById('other-name');
      const notesEl = document.getElementById('other-notes');
      const addBtn = document.getElementById('other-add');
      const list = document.getElementById('item-list');
      addBtn?.addEventListener('click', () => {
        const n = (nameEl.value || '').trim();
        const notes = (notesEl.value || '').trim();
        if (n) {
          state.others.push({ name: n, description: notes || undefined });
          renderStep();
          nameEl.value = '';
          notesEl.value = '';
        }
      });
      list?.addEventListener('click', (e) => {
        const tgt = e.target;
        if (tgt && tgt.dataset && tgt.dataset.action === 'del') {
          const idx = parseInt(tgt.dataset.idx, 10);
          state.others.splice(idx, 1);
          renderStep();
        }
      });
    } else if (step === 'targets') {
      const summary = document.getElementById('targets-summary');
      const defTgt = document.getElementById('def-tgt');
      defTgt?.addEventListener('input', ()=> { state.targetDefaults.target = parseInt(defTgt.value,10)||3; });
      // Remove handlers
      summary?.addEventListener('click', (e) => {
        const el = e.target;
        if (el && el.dataset && el.dataset.action === 'del') {
          const cid = parseInt(el.dataset.cid, 10);
          const idx = state.targets.findIndex(t => t.competency_id === cid);
          if (idx >= 0) state.targets.splice(idx, 1);
          renderStep();
        }
      });
      summary?.addEventListener('input', (e) => {
        const el = e.target;
        if (el && el.classList.contains('lvl-slider')) {
          const cid = parseInt(el.dataset.cid, 10);
          const kind = el.dataset.kind;
          const val = parseInt(el.value, 10) || 1;
          const row = el.closest('.slider-block');
          const labelEl = row?.querySelector('.lvl-value');
          if (labelEl) labelEl.textContent = `${val}: ${levelLabel(val)}`;
          const item = state.targets.find(t => t.competency_id === cid);
          if (item && kind === 'target') item.target_level = val;
        }
      });

      // Searchable dropdown
      const search = document.getElementById('comp-search');
      const results = document.getElementById('comp-results');
      if (search) {
        search.addEventListener('input', debounce(async () => {
          const q = (search.value || '').trim().toLowerCase();
          if (!q) { results.innerHTML = ''; results.style.display = 'none'; return; }
          const items = await loadCompetencies();
          const matches = items.filter(c => c.name_lc.includes(q)).slice(0, 8);
          if (matches.length === 0) { results.innerHTML = '<div class="comp-empty">No results</div>'; results.style.display = 'block'; return; }
          results.innerHTML = matches.map(c => `
            <div class="comp-item" role="option" data-id="${c.id}" data-name="${escapeAttr(c.name)}">${escapeHtml(c.name)} <span class="comp-fw">${escapeHtml(c.framework_name || '')}</span></div>
          `).join('');
          results.style.display = 'block';
        }, 200));
      }
      if (results) {
        results.addEventListener('click', (e) => {
          const el = e.target.closest('.comp-item');
          if (!el) return;
          const id = parseInt(el.dataset.id, 10);
          const name = el.dataset.name || ('#'+id);
          if (state.targets.some(t => t.competency_id === id)) { showToast('Already added to targets', 'info'); results.innerHTML=''; results.style.display='none'; return; }
          const tgt = Number(state.targetDefaults?.target||3);
          state.pendingTarget = { id, name, level: tgt };
          renderStep();
          // Clear & hide results
          const s = document.getElementById('comp-search');
          if (s) s.value = '';
          results.innerHTML = '';
          results.style.display = 'none';
        });
      }

      // Pending add handlers
      const ptSlider = document.getElementById('pt-slider');
      const ptValue = document.getElementById('pt-value');
      const ptAdd = document.getElementById('pt-add');
      const ptClear = document.getElementById('pt-clear');
      ptSlider?.addEventListener('input', () => {
        const v = parseInt(ptSlider.value, 10) || 1;
        if (ptValue) ptValue.textContent = `${v}: ${levelLabel(v)}`;
        if (state.pendingTarget) state.pendingTarget.level = v;
      });
      ptAdd?.addEventListener('click', () => {
        const p = state.pendingTarget;
        if (!p) return;
        if (!state.targets.some(t => t.competency_id === p.id)) {
          state.targets.push({ competency_id: p.id, competency_name: p.name, target_level: Number(p.level||state.targetDefaults?.target||3), weight: 1.0 });
        }
        state.pendingTarget = null;
        renderStep();
      });
      ptClear?.addEventListener('click', () => { state.pendingTarget = null; renderStep(); });
    }
  }

  function updateWizardButtons() {
    const prev = document.getElementById('wiz-prev');
    const next = document.getElementById('wiz-next');
    const save = document.getElementById('wiz-save');
    if (prev) prev.disabled = stepIndex === 0;
    if (next) next.style.display = stepIndex < steps.length - 1 ? '' : 'none';
    if (save) save.style.display = stepIndex === steps.length - 1 ? '' : 'none';
  }

  function updateStepper() {
    // Map progress classes on .wizard-steps li
    const ol = document.querySelector('.wizard-steps');
    if (!ol) return;
    const lis = Array.from(ol.querySelectorAll('li'));
    lis.forEach((li, i) => {
      li.classList.remove('active','completed','upcoming');
      if (i < stepIndex) li.classList.add('completed');
      else if (i === stepIndex) li.classList.add('active');
      else li.classList.add('upcoming');
      // add indicator/check
      const mark = li.querySelector('.step-mark');
      if (!mark) {
        const span = document.createElement('span');
        span.className = 'step-mark';
        span.textContent = (i < stepIndex) ? '✓' : String(i+1);
        li.prepend(span);
      } else {
        mark.textContent = (i < stepIndex) ? '✓' : String(i+1);
      }
    });
    // Clickable stepper (bind once)
    if (!ol.dataset.boundClick) {
      ol.addEventListener('click', (e) => {
        const li = e.target.closest('li');
        if (!li) return;
        const items = Array.from(ol.querySelectorAll('li'));
        const idx = items.indexOf(li);
        if (idx < 0) return;
        if (idx > stepIndex && steps[stepIndex] === 'basics' && !state.name.trim()) {
          alert('Please provide a role name before proceeding.');
          return;
        }
        stepIndex = Math.max(0, Math.min(steps.length - 1, idx));
        renderStep();
      });
      ol.dataset.boundClick = '1';
    }
  }

  function bindWizardChrome() {
    const prev = document.getElementById('wiz-prev');
    const next = document.getElementById('wiz-next');
    const save = document.getElementById('wiz-save');
    prev?.addEventListener('click', () => {
      if (stepIndex > 0) { stepIndex--; renderStep(); }
    });
    next?.addEventListener('click', async () => {
      // Simple validation for basics
      if (steps[stepIndex] === 'basics') {
        if (!state.name.trim()) { alert('Please provide a role name.'); return; }
      }
      stepIndex = Math.min(steps.length - 1, stepIndex + 1);
      renderStep();
    });
    save?.addEventListener('click', async () => {
      try {
        // 1) Create role (or update if editing)
        let roleId = state.roleId;
        if (!roleId) {
          const created = await fetchJSON('/api/roles', { method: 'POST', body: JSON.stringify({
            name: state.name,
            description: state.description,
            department: state.department,
          })});
          roleId = created.role?.id;
          state.roleId = roleId;
        } else {
          await fetchJSON(`/api/roles/${roleId}`, { method: 'PATCH', body: JSON.stringify({
            name: state.name,
            description: state.description,
            department: state.department,
          })});
        }
        if (!roleId) throw new Error('Missing role id after create');
        // 2) Upsert KSAOs
        await fetchJSON(`/api/roles/${roleId}/ksaos`, { method: 'POST', body: JSON.stringify({
          knowledge: state.knowledge,
          skills: state.skills,
          abilities: state.abilities,
          others: state.others,
        })});
        // 3) Upsert targets
        await fetchJSON(`/api/roles/${roleId}/targets`, { method: 'POST', body: JSON.stringify({ targets: state.targets })});
        alert('Role Profile saved.');
        const fromAdmin = window.location.pathname.startsWith('/admin');
        window.location.href = fromAdmin ? '/admin/roles?saved=1' : '/roles';
      } catch (e) {
        console.error(e);
        alert('Failed to save role profile.');
      }
    });
  }

  function initWizard() {
    // Read edit mode if hash contains #edit=ID
    const hash = window.location.hash;
    const m = /edit=(\d+)/.exec(hash || '');
    if (m) {
      state.roleId = parseInt(m[1], 10);
      // Load role to prefill
      fetchJSON(`/api/roles/${state.roleId}?include=ksaos,targets`).then(data => {
        const r = data.role;
        state.name = r.name || '';
        state.description = r.description || '';
        state.department = r.department || '';
        state.knowledge = (r.knowledge || []).map(x=>({ name: x.name || '' }));
        state.skills = (r.skills || []).map(x=>({ name: x.name || '' }));
        state.abilities = (r.abilities || []).map(x=>({ name: x.name || '' }));
        state.others = (r.others || []).map(x=>({ name: x.name || '' }));
        state.targets = r.competency_targets || [];
        renderStep();
      }).catch(() => renderStep());
    } else {
      renderStep();
    }
    bindWizardChrome();
  }

  // Utils
  function escapeHtml(s) {
    return (s || '').toString().replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  }
  function escapeAttr(s) {
    return escapeHtml(s).replace(/"/g, '&quot;');
  }
  function levelLabel(n){
    switch(Number(n)){
      case 1: return 'Foundational';
      case 2: return 'Basic';
      case 3: return 'Proficient';
      case 4: return 'Advanced';
      case 5: return 'Expert';
      default: return '';
    }
  }
  function debounce(fn, wait) {
    let t; return (...args) => { clearTimeout(t); t = setTimeout(()=>fn.apply(null,args), wait); };
  }

  async function loadCompetencies() {
    try {
      if (_competencyCache && Array.isArray(_competencyCache)) return _competencyCache;
      // Use routes.py endpoint that accepts include_competencies=true
      const data = await fetchJSON('/api/frameworks?include_competencies=true');
      const list = [];
      (data.frameworks || []).forEach(fw => {
        (fw.competencies || []).forEach(c => {
          list.push({ id: c.id, name: c.name, name_lc: (c.name||'').toLowerCase(), framework_id: fw.id, framework_name: fw.name });
        });
      });
      _competencyCache = list;
      return list;
    } catch (e) {
      console.warn('Failed to load competencies:', e);
      _competencyCache = [];
      return _competencyCache;
    }
  }

  return { initList, initWizard };
})();
