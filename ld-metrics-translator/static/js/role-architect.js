/* Role Architect UI logic: list and wizard */

const RoleArchitect = (() => {
  async function fetchJSON(url, opts = {}) {
    const base = { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' };
    if (opts && opts.body && (!opts.headers || !opts.headers['Content-Type'])) {
      base.headers['Content-Type'] = 'application/json';
    }
    const res = await fetch(url, Object.assign(base, opts));
    const raw = await res.text();
    let data = null;
    if (raw) {
      try { data = JSON.parse(raw); }
      catch { /* leave data null */ }
    }
    if (!res.ok) {
      const details = data && typeof data === 'object' ? (data.error || data.message || data.detail) : null;
      const err = new Error(details || raw || `Request failed: ${res.status}`);
      err.status = res.status;
      err.payload = data;
      throw err;
    }
    if (data === null && raw) {
      try { data = JSON.parse(raw); }
      catch { data = raw; }
    }
    return data ?? {};
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
            <td class="actions-cell">
              <a class="btn" href="${editHref}">Edit</a>
              ${isAdmin ? `<button class="btn btn-danger" data-action="delete" data-role-id="${r.id}">Delete</button>` : ''}
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
      const tbody = document.getElementById('roles-tbody');
      if (!tbody) return;
      const selected = Array.from(tbody.querySelectorAll('.row-check:checked'))
        .map(cb => cb.closest('tr')?.dataset?.id)
        .filter(Boolean);
      if (selected.length !== 2) {
        alert('Select exactly two roles to compare.');
        return;
      }
      const params = new URLSearchParams();
      params.set('roles', selected.join(','));
      window.location.href = `/reports/compare?${params.toString()}`;
    });
    const tbody = document.getElementById('roles-tbody');
    if (tbody) {
      tbody.addEventListener('change', (e) => {
        if (e.target && e.target.classList.contains('row-check')) {
          const checked = tbody.querySelectorAll('.row-check:checked').length;
          if (compareBtn) compareBtn.disabled = checked !== 2;
        }
      });
      tbody.addEventListener('click', async (e) => {
        const btn = e.target.closest('button[data-action="delete"]');
        if (!btn) return;
        const roleId = parseInt(btn.getAttribute('data-role-id'), 10);
        if (!roleId || Number.isNaN(roleId)) return;
        if (!confirm('Delete this role profile? This cannot be undone.')) return;
        btn.disabled = true;
        try {
          await fetchJSON(`/api/roles/${roleId}`, { method: 'DELETE' });
          loadList();
        } catch (err) {
          console.error(err);
          alert('Failed to delete role profile.');
          btn.disabled = false;
        }
      });
    }
  }

  function initList() {
    bindListEvents();
    loadList();
  }

  // Wizard
  const steps = ['basics','knowledge','skills','abilities','outcomes','others','targets','review'];
  let state = {
    roleId: null,
    name: '',
    description: '',
    department: '',
    knowledge: [],
    skills: [],
    abilities: [],
    outcomes: [],
    others: [],
    targetDefaults: { target: 3 },
  };
  let stepIndex = 0;
  // lightweight cache for competencies (flattened across frameworks)
  let _competencyCache = null; // [{id, name, framework_id, framework_name}]
  let _driverCardCache = [];
  let _driverCardMap = new Map();
  let _driverCardLoadError = false;
  let _driverCardPromise = null;

  async function ensureDriverCards() {
    if (_driverCardCache.length || _driverCardLoadError) return _driverCardCache;
    if (_driverCardPromise) return _driverCardPromise;
    _driverCardPromise = (async () => {
      try {
        const data = await fetchJSON('/api/driver-cards?kind=driver&per_page=250');
        const items = Array.isArray(data.items) ? data.items : [];
        _driverCardCache = items.map(card => ({
          id: Number(card.id),
          name: card.name || `Card #${card.id}`,
          identifier_type: card.identifier_type || null,
          metric_type: card.metric_type?.name || null,
        }));
        _driverCardMap = new Map(_driverCardCache.map(card => [card.id, card]));
        return _driverCardCache;
      } catch (err) {
        console.warn('Failed to load driver cards:', err);
        _driverCardLoadError = true;
        return [];
      } finally {
        _driverCardPromise = null;
      }
    })();
    return _driverCardPromise;
  }

  function driverCardSelectHtml(selected, opts = {}) {
    if (_driverCardLoadError) {
      const errId = opts.id ? ` id="${escapeAttr(opts.id)}"` : ' id="item-driver"';
      return `<div${errId} class="driver-select driver-select--error">Driver cards unavailable</div>`;
    }
    const selectId = opts.id ? String(opts.id) : 'item-driver';
    const selectName = opts.name ? ` name="${escapeAttr(opts.name)}"` : '';
    const classes = ['driver-select'];
    if (opts.className) classes.push(opts.className);
    const classAttr = ` class="${classes.map(escapeAttr).join(' ')}"`;
    const sel = selected && typeof selected === 'object' ? selected.id : selected;
    const selId = sel === undefined || sel === null ? null : Number(sel);
    const meta = driverCardMeta(selId);
    const options = _driverCardCache.map(card => `<option value="${card.id}"${selId === card.id ? ' selected' : ''}>${escapeHtml(card.name)}</option>`).join('');
    let fallbackOption = '';
    if (selId !== null && !meta) {
      const fallbackName = (selected && typeof selected === 'object' && selected.name) ? selected.name : `Card #${selId}`;
      fallbackOption = `<option value="${selId}" selected>${escapeHtml(fallbackName)}</option>`;
    }
    return `<select id="${escapeAttr(selectId)}"${selectName}${classAttr}><option value="">Link driver card (optional)</option>${fallbackOption}${options}</select>`;
  }

  function driverCardMeta(id) {
    if (id === undefined || id === null) return null;
    const num = Number(id);
    if (Number.isNaN(num)) return null;
    return _driverCardMap.get(num) || null;
  }

  function driverCardLabels(cardMeta) {
    if (!cardMeta) return { subtype: '', metric: '' };
    const subtype = cardMeta.identifier_type ? `(${formatIdentifier(cardMeta.identifier_type)})` : '';
    const metric = cardMeta.metric_type || '';
    return { subtype, metric };
  }

  function formatIdentifier(identifier) {
    if (!identifier) return '';
    const map = {
      trait_attribute: 'Trait/Attribute',
      behavior: 'Behavior',
      behaviour: 'Behavior',
      skill: 'Skill',
      concept: 'Concept',
      competency: 'Competency',
    };
    const key = String(identifier).toLowerCase();
    return map[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  function renderKsaoChip(kind, item, idx) {
    const parts = [escapeHtml(item.name || '')];
    let cardName = item.driver_card_name;
    const card = driverCardMeta(item.driver_card_id);
    if (!cardName && card) {
      cardName = card.name;
      item.driver_card_name = cardName;
    }
    if (cardName) {
      const { subtype } = driverCardLabels(card);
      const details = subtype ? ` ${escapeHtml(subtype)}` : '';
      parts.push(`<span class="chip-driver">@ ${escapeHtml(cardName)}${details}</span>`);
    }
    if (['knowledge','skills','abilities','outcomes'].includes(kind) && typeof item.target_level === 'number') {
      parts.push(`<span class="chip-target">Target ${escapeHtml(String(item.target_level))} (${escapeHtml(levelLabel(item.target_level))})</span>`);
    }
    if (item.description) parts.push(`— ${escapeHtml(item.description)}`);
    return `<li class="chip" data-idx="${idx}" draggable="true"><span class="chip-label">${parts.join(' ')}</span><span class="chip-actions"><button aria-label="Edit" data-action="edit" data-idx="${idx}" class="chip-btn">✎</button><button aria-label="Remove" data-action="del" data-idx="${idx}" class="chip-x">×</button></span></li>`;
  }

  function renderReviewList(kind, items) {
    if (!Array.isArray(items) || items.length === 0) {
      return '<div class="no-data-message">No items specified</div>';
    }
    const includeTarget = ['knowledge','skills','abilities','outcomes'].includes(kind);
    return `<ul class="chips">${items.map((item) => {
      const driverId = item.driver_card_id || (item.driver_card && item.driver_card.id);
      const driverMeta = driverCardMeta(driverId);
      const driverName = item.driver_card_name || driverMeta?.name || '';
      const { subtype } = driverCardLabels(driverMeta);
      const showUnlinked = includeTarget && !driverName;
      const parts = [escapeHtml(item.name || '')];
      if (driverName) {
        const details = subtype ? ` ${escapeHtml(subtype)}` : '';
        parts.push(`<span class="chip-driver">@ ${escapeHtml(driverName)}${details}</span>`);
      }
      if (includeTarget && typeof item.target_level === 'number') {
        parts.push(`<span class="chip-target">Target ${escapeHtml(String(item.target_level))} (${escapeHtml(levelLabel(item.target_level))})</span>`);
      }
      if (item.description) parts.push(`— ${escapeHtml(item.description)}`);
      return `<li class="chip${showUnlinked ? ' chip-unlinked' : ''}"><span class="chip-label">${parts.join(' ')}</span></li>`;
    }).join('')}</ul>`;
  }

  function getDriverCardId(item) {
    if (!item) return null;
    if (item.driver_card_id) return Number(item.driver_card_id);
    if (item.driver_card && item.driver_card.id) return Number(item.driver_card.id);
    return null;
  }

  function driverLinkedEntries() {
    const entries = [];
    ['knowledge', 'skills', 'abilities', 'outcomes'].forEach((kind) => {
      (state[kind] || []).forEach((item, index) => {
        const driverCardId = getDriverCardId(item);
        if (!driverCardId) return;
        entries.push({ kind, index, item, driver_card_id: driverCardId });
      });
    });
    return entries;
  }

  function normalizeTargetLevel(value, fallback = undefined) {
    const num = Number(value);
    if (Number.isInteger(num) && num >= 1 && num <= 5) return num;
    return fallback;
  }

  function renderTargetReview(entries) {
    if (!entries.length) return '<div class="no-data-message">No driver-card targets configured</div>';
    const defaultVal = Number(state.targetDefaults?.target || 3);
    return `
      <table class="review-table">
        <thead><tr><th>Driver card</th><th>Linked item</th><th>KSAO Category</th><th>Target</th><th>Measurement</th></tr></thead>
        <tbody>
          ${entries.map(({ kind, item, driver_card_id }) => {
            const driver = driverCardMeta(driver_card_id);
            const driverName = driver?.name || item.driver_card_name || `Driver card #${driver_card_id}`;
            const targetVal = normalizeTargetLevel(item.target_level, defaultVal);
            const isDefault = !(Number.isInteger(item.target_level));
            const { subtype, metric } = driverCardLabels(driver);
            const kindLabel = kind.charAt(0).toUpperCase() + kind.slice(1);
            return `<tr>
              <td>${escapeHtml(driverName)}${subtype ? ` <span class="review-subtype">${escapeHtml(subtype)}</span>` : ''}</td>
              <td>${escapeHtml(item.name || '')}</td>
              <td>${escapeHtml(kindLabel)}</td>
              <td>${targetVal}: ${escapeHtml(levelLabel(targetVal))}${isDefault ? ' <span class="hint">(default)</span>' : ''}</td>
              <td>${metric ? escapeHtml(metric) : '—'}</td>
            </tr>`;
          }).join('')}
        </tbody>
      </table>
    `;
  }

  function renderTargetRow(entry, defaultLevel) {
    const { kind, index, item, driver_card_id } = entry;
    const driver = driverCardMeta(driver_card_id);
    const driverName = driver?.name || item.driver_card_name || `Driver card #${driver_card_id}`;
    const { subtype, metric } = driverCardLabels(driver);
    const sliderValue = normalizeTargetLevel(item.target_level, defaultLevel);
    const sliderId = `target-${kind}-${index}`;
    const usingDefault = !Number.isInteger(item.target_level);
    const control = `
      <button type="button" class="btn btn-link target-reset" data-action="reset" data-kind="${escapeAttr(kind)}" data-index="${index}" style="${usingDefault ? 'display:none;' : ''}">Use default</button>
      <span class="hint target-default-flag" style="${usingDefault ? '' : 'display:none;'}">Using default</span>
    `;
    return `
      <div class="target-row" data-kind="${escapeAttr(kind)}" data-index="${index}">
        <div class="t-head">
          <div>
            <div class="t-name">${escapeHtml(item.name || '')}</div>
            <div class="t-driver hint">${escapeHtml(driverName)}${subtype ? ` · ${escapeHtml(subtype)}` : ''}${metric ? ` · ${escapeHtml(metric)}` : ''}</div>
          </div>
          ${control}
        </div>
        <div class="t-sliders">
          <div class="slider-block">
            <label for="${escapeAttr(sliderId)}">Target level</label>
            <input type="range" id="${escapeAttr(sliderId)}" class="lvl-slider" min="1" max="5" step="1" value="${sliderValue}" data-kind="${escapeAttr(kind)}" data-index="${index}" />
            <div class="lvl-value">${sliderValue}: ${escapeHtml(levelLabel(sliderValue))}</div>
            <div class="hint">1: Foundational · 5: Expert</div>
          </div>
        </div>
      </div>
    `;
  }

  function serializeKsaoItems(items, { includeTarget = true } = {}) {
    const out = [];
    (items || []).forEach((item) => {
      const name = (item?.name || '').trim();
      if (!name) return;
      const record = { name };
      if (item.description) record.description = item.description;
      const driverId = getDriverCardId(item);
      if (driverId) record.driver_card_id = driverId;
      if (includeTarget && driverId) {
        const val = normalizeTargetLevel(item.target_level);
        if (val !== undefined) record.target_level = val;
      }
      out.push(record);
    });
    return out;
  }

  function renderStep() {
    const mount = document.getElementById('role-wizard');
    if (!mount) return;
    const step = steps[stepIndex];
    let html = '';

    if (!_driverCardLoadError && !_driverCardCache.length && ['knowledge','skills','abilities','outcomes','targets','review'].includes(step)) {
      ensureDriverCards().then(() => {
        if (steps[stepIndex] === step) renderStep();
      });
    }
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
      const editing = state._editing && state._editing[key];
      const label = key === 'knowledge' ? 'Knowledge Area' : key === 'skills' ? 'Skill' : 'Ability';
      html = `
        <div class="list-editor">
          <h3 style="margin:0 0 8px 0;">${label}s</h3>
          <div class="list-row">
            <label class="field flex-1"><span>${label} name</span>
              <textarea id="item-input" placeholder="Describe the ${label.toLowerCase()}" rows="3">${editing ? escapeHtml(editing.name || '') : ''}</textarea>
            </label>
            <label class="field flex-1"><span>Driver card</span>
              ${driverCardSelectHtml(editing ? { id: editing.driver_card_id, name: editing.driver_card_name } : undefined)}
            </label>
            <label class="field" style="max-width:220px"><span>Target level</span>
              <input type="range" id="item-target" min="1" max="5" step="1" value="${editing && typeof editing.target_level === 'number' ? editing.target_level : Number(state.targetDefaults?.target||3)}" data-default="${Number(state.targetDefaults?.target||3)}" />
              <div class="hint" id="item-target-hint">Select a driver card to enable target level.</div>
            </label>
            <button id="item-add" class="btn primary" style="align-self:flex-end;">${editing ? 'Update' : 'Add'}</button>
            ${editing ? '<button id="item-cancel" class="btn" style="align-self:flex-end;">Cancel</button>' : ''}
          </div>
          <div id="ksao-results" class="ksao-results" role="listbox" aria-label="Suggestions"></div>
          <ul id="item-list" class="chips mt">
            ${items.map((x,i)=>renderKsaoChip(key, x, i)).join('')}
          </ul>
        </div>
      `;
    } else if (step === 'outcomes') {
      const items = state.outcomes || [];
      const editing = state._editing && state._editing.outcomes;
      html = `
        <div class="list-editor">
          <h3 style="margin:0 0 8px 0;">Outcomes</h3>
          <div class="list-row">
            <label class="field flex-1"><span>Outcome description</span>
              <textarea id="outcome-input" placeholder="Describe the key outcome for this role" rows="3">${editing ? escapeHtml(editing.name || '') : ''}</textarea>
            </label>
            <label class="field flex-1"><span>Driver card</span>
              ${driverCardSelectHtml(editing ? { id: editing.driver_card_id, name: editing.driver_card_name } : undefined, { id: 'outcome-driver' })}
            </label>
            <label class="field" style="max-width:220px"><span>Target level</span>
              <input type="range" id="outcome-target" min="1" max="5" step="1" value="${editing && typeof editing.target_level === 'number' ? editing.target_level : Number(state.targetDefaults?.target||3)}" data-default="${Number(state.targetDefaults?.target||3)}" />
              <div class="hint" id="outcome-target-hint">Select a driver card to enable target level.</div>
            </label>
            <button id="outcome-add" class="btn primary" style="align-self:flex-end;">${editing ? 'Update' : 'Add'}</button>
            ${editing ? '<button id="outcome-cancel" class="btn" style="align-self:flex-end;">Cancel</button>' : ''}
          </div>
          <ul id="outcome-list" class="chips mt">
            ${items.map((x,i)=>renderKsaoChip('outcomes', x, i)).join('')}
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
      const defaultVal = Number(state.targetDefaults?.target || 3);
      const entries = driverLinkedEntries();
      html = `
        <h3 style="margin:0 0 8px;">Configure Target Levels</h3>
        <div class="targets-intro notice">Only Knowledge, Skills, Abilities, and Outcomes linked to driver cards appear below. Adjust target levels as needed or rely on the default.</div>
        <div class="t-defaults mt" id="t-defaults" style="display:flex; gap:16px; align-items:center; flex-wrap:wrap;">
          <div style="display:grid; gap:6px; min-width:260px;">
            <label for="def-tgt">Default target level</label>
            <input type="range" id="def-tgt" min="1" max="5" step="1" value="${defaultVal}" />
            <div class="hint" id="def-tgt-value">${defaultVal}: ${escapeHtml(levelLabel(defaultVal))}</div>
          </div>
          <div class="hint">Items using the default will update automatically when this value changes.</div>
        </div>
        <div class="targets-summary mt" id="targets-summary">
          ${entries.length ? entries.map(entry => renderTargetRow(entry, defaultVal)).join('') : '<div class="no-data-message">Add driver cards to Knowledge, Skills, Abilities, or Outcomes to configure targets.</div>'}
        </div>
      `;
    } else if (step === 'review') {
      const driverEntries = driverLinkedEntries();
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
            <div class="review-body">${renderReviewList('knowledge', state.knowledge)}</div>
          </div>

          <div class="review-card">
            <div class="review-head">
              <h3>Skills</h3>
              <a href="#" class="edit-link" data-edit="skills">Edit</a>
            </div>
            <div class="review-body">${renderReviewList('skills', state.skills)}</div>
          </div>

          <div class="review-card">
            <div class="review-head">
              <h3>Abilities</h3>
              <a href="#" class="edit-link" data-edit="abilities">Edit</a>
            </div>
            <div class="review-body">${renderReviewList('abilities', state.abilities)}</div>
          </div>

          <div class="review-card">
            <div class="review-head">
              <h3>Outcomes</h3>
              <a href="#" class="edit-link" data-edit="outcomes">Edit</a>
            </div>
            <div class="review-body">${renderReviewList('outcomes', state.outcomes)}</div>
          </div>

          <div class="review-card">
            <div class="review-head">
              <h3>Certifications & Other Requirements</h3>
              <a href="#" class="edit-link" data-edit="others">Edit</a>
            </div>
            <div class="review-body">${renderReviewList('others', state.others)}</div>
          </div>

          <div class="review-card wide">
            <div class="review-head">
              <h3>Targets</h3>
              <a href="#" class="edit-link" data-edit="targets">Edit</a>
            </div>
            <div class="review-body">${renderTargetReview(driverEntries)}</div>
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
      const driverSelect = document.getElementById('item-driver');
      const targetSlider = document.getElementById('item-target');
      const targetHint = document.getElementById('item-target-hint');
      const addBtn = document.getElementById('item-add');
      const cancelBtn = document.getElementById('item-cancel');
      const list = document.getElementById('item-list');
      const results = document.getElementById('ksao-results');
      const editing = state._editing && state._editing[key];

      function normalizeName(v){
        return (v || '').trim().toLowerCase();
      }

      function exists(v){
        const name = normalizeName(v);
        return (state[key]||[]).some((x, idx) => {
          if (editing && editing.index === idx) return false;
          return normalizeName(x.name) === name;
        });
      }

      function updateTargetUI(){
        if (!targetSlider) return;
        const hasDriver = !!(driverSelect && driverSelect.value);
        targetSlider.disabled = !hasDriver;
        let val = Number(targetSlider.value);
        if (Number.isNaN(val)) {
          val = Number(targetSlider.dataset.default || 3);
          targetSlider.value = String(val);
        }
        if (targetHint) {
          targetHint.textContent = hasDriver ? `${val}: ${levelLabel(val)}` : 'Select a driver card to enable target level.';
        }
      }

      if (editing) {
        if (input) input.value = editing.name || '';
        if (driverSelect) {
          driverSelect.value = editing.driver_card_id ? String(editing.driver_card_id) : '';
        }
        if (targetSlider) {
          const editLevel = typeof editing.target_level === 'number' ? editing.target_level : Number(targetSlider.dataset.default || 3);
          targetSlider.value = String(editLevel);
        }
      }
      updateTargetUI();

      function resetEditing(){
        if (state._editing) delete state._editing[key];
      }

      function addItem(from){
        if (!input) return;
        const v = (input.value || '').trim();
        if (!v) return;
        const driverIdRaw = driverSelect ? driverSelect.value : '';
        const driverId = driverIdRaw ? Number(driverIdRaw) : null;
        if (exists(v)) { alert('That item already exists'); return; }
        const targetLevel = !targetSlider || targetSlider.disabled ? undefined : Number(targetSlider.value || Number(targetSlider.dataset.default || 3));
        const driver = driverCardMeta(driverId);
        const payload = {
          name: v,
          driver_card_id: driverId || undefined,
          driver_card_name: driver ? driver.name : undefined,
          target_level: driverId ? targetLevel : undefined,
        };
        if (editing) {
          const idx = editing.index;
          if (idx >= 0 && idx < state[key].length) {
            const prev = state[key][idx] || {};
            state[key][idx] = {
              ...prev,
              ...payload,
            };
          }
          resetEditing();
        } else {
          state[key].push(payload);
        }
        renderStep();
        if (from !== 'click' && input) input.focus();
      }

      addBtn?.addEventListener('click', () => addItem('click'));
      cancelBtn?.addEventListener('click', () => { resetEditing(); renderStep(); });
      input?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); addItem('enter'); }
      });
      driverSelect?.addEventListener('change', () => {
        updateTargetUI();
      });
      targetSlider?.addEventListener('input', () => {
        updateTargetUI();
      });

      input?.addEventListener('input', debounce(async () => {
        if (!results) return;
        const q = (input.value || '').trim();
        if (!q || q.length < 2) { results.style.display = 'none'; results.innerHTML=''; return; }
        try {
          const data = await fetchJSON(`/api/metrics?search=${encodeURIComponent(q)}&per_page=10`);
          const items = (data.metrics||[]).map(m => m.name).filter(Boolean);
          if (items.length === 0) {
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
        if (exists(v)) { alert('That item already exists'); return; }
        state[key].push({ name: v });
        renderStep();
      });

      list?.addEventListener('click', (e) => {
        const tgt = e.target;
        if (!tgt || !tgt.dataset) return;
        const idx = parseInt(tgt.dataset.idx, 10);
        if (Number.isNaN(idx)) return;
        if (tgt.dataset.action === 'del') {
          state[key].splice(idx, 1);
          if (state._editing && state._editing[key] && state._editing[key].index === idx){
            resetEditing();
          }
          renderStep();
        } else if (tgt.dataset.action === 'edit') {
          state._editing = state._editing || {};
          const item = state[key][idx] || {};
          state._editing[key] = {
            index: idx,
            name: item.name || '',
            driver_card_id: item.driver_card_id || item.driver_card?.id || null,
            driver_card_name: item.driver_card_name || (item.driver_card && item.driver_card.name) || undefined,
            target_level: typeof item.target_level === 'number' ? item.target_level : undefined,
          };
          renderStep();
        }
      });

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
        renderStep();
      });
    } else if (step === 'outcomes') {
      const input = document.getElementById('outcome-input');
      const driverSelect = document.getElementById('outcome-driver');
      const targetSlider = document.getElementById('outcome-target');
      const targetHint = document.getElementById('outcome-target-hint');
      const addBtn = document.getElementById('outcome-add');
      const cancelBtn = document.getElementById('outcome-cancel');
      const list = document.getElementById('outcome-list');
      const editing = state._editing && state._editing.outcomes;

      function updateTargetUI(){
        if (!targetSlider) return;
        const hasDriver = !!(driverSelect && driverSelect.value);
        targetSlider.disabled = !hasDriver;
        let val = Number(targetSlider.value);
        if (Number.isNaN(val)) {
          val = Number(targetSlider.dataset.default || 3);
          targetSlider.value = String(val);
        }
        if (targetHint) {
          targetHint.textContent = hasDriver ? `${val}: ${levelLabel(val)}` : 'Select a driver card to enable target level.';
        }
      }

      if (editing) {
        if (driverSelect) driverSelect.value = editing.driver_card_id ? String(editing.driver_card_id) : '';
        if (targetSlider) targetSlider.value = String(typeof editing.target_level === 'number' ? editing.target_level : Number(targetSlider.dataset.default || 3));
      }
      updateTargetUI();

      function resetEditing(){
        if (state._editing) delete state._editing.outcomes;
      }

      addBtn?.addEventListener('click', () => {
        if (!input) return;
        const v = (input.value || '').trim();
        if (!v) return;
        const driverIdRaw = driverSelect ? driverSelect.value : '';
        const driverId = driverIdRaw ? Number(driverIdRaw) : null;
        const driver = driverCardMeta(driverId);
        const payload = {
          name: v,
          driver_card_id: driverId || undefined,
          driver_card_name: driver ? driver.name : undefined,
          target_level: driverId ? normalizeTargetLevel(targetSlider?.value, Number(targetSlider?.dataset.default || 3)) : undefined,
        };
        if (editing) {
          const idx = editing.index;
          if (idx >= 0 && idx < state.outcomes.length) {
            const prev = state.outcomes[idx] || {};
            state.outcomes[idx] = { ...prev, ...payload };
          }
          resetEditing();
        } else {
          state.outcomes.push(payload);
        }
        input.value = '';
        if (driverSelect) driverSelect.value = '';
        if (targetSlider) targetSlider.value = String(targetSlider.dataset.default || 3);
        renderStep();
      });

      cancelBtn?.addEventListener('click', () => {
        resetEditing();
        renderStep();
      });

      driverSelect?.addEventListener('change', () => updateTargetUI());
      targetSlider?.addEventListener('input', () => updateTargetUI());

      list?.addEventListener('click', (e) => {
        const btn = e.target.closest('button');
        if (!btn || !btn.dataset) return;
        const idx = parseInt(btn.dataset.idx, 10);
        if (Number.isNaN(idx)) return;
        if (btn.dataset.action === 'del') {
          state.outcomes.splice(idx, 1);
          if (state._editing && state._editing.outcomes && state._editing.outcomes.index === idx) {
            resetEditing();
          }
          renderStep();
        } else if (btn.dataset.action === 'edit') {
          state._editing = state._editing || {};
          const item = state.outcomes[idx] || {};
          state._editing.outcomes = {
            index: idx,
            name: item.name || '',
            driver_card_id: item.driver_card_id || item.driver_card?.id || null,
            driver_card_name: item.driver_card_name || (item.driver_card && item.driver_card.name) || undefined,
            target_level: typeof item.target_level === 'number' ? item.target_level : undefined,
          };
          renderStep();
        }
      });

      list?.addEventListener('dragstart', (e) => {
        const li = e.target.closest('.chip');
        if (!li) return;
        e.dataTransfer.effectAllowed = 'move';
        li.classList.add('dragging');
        list.dataset.dragIndex = li.dataset.idx;
      });

      list?.addEventListener('dragend', (e) => {
        const li = e.target.closest('.chip');
        li?.classList.remove('dragging');
        delete list.dataset.dragIndex;
      });

      list?.addEventListener('dragover', (e) => {
        e.preventDefault();
        const li = e.target.closest('.chip');
        if (!li || !list.dataset.dragIndex) return;
        const from = parseInt(list.dataset.dragIndex, 10);
        const to = parseInt(li.dataset.idx, 10);
        if (Number.isNaN(from) || Number.isNaN(to) || from === to) return;
        const [moved] = state.outcomes.splice(from, 1);
        state.outcomes.splice(to, 0, moved);
        list.dataset.dragIndex = String(to);
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
      const defTgt = document.getElementById('def-tgt');
      const defValue = document.getElementById('def-tgt-value');
      const summary = document.getElementById('targets-summary');

      defTgt?.addEventListener('input', () => {
        const val = Number(defTgt.value || state.targetDefaults.target || 3);
        state.targetDefaults.target = val;
        if (defValue) defValue.textContent = `${val}: ${levelLabel(val)}`;
        driverLinkedEntries().forEach(({ kind, index, item }) => {
          if (!Number.isInteger(item.target_level)) {
            item.target_level = undefined;
          }
        });
        renderStep();
      });

      summary?.addEventListener('input', (e) => {
        const slider = e.target.closest('.lvl-slider');
        if (!slider) return;
        const kind = slider.dataset.kind;
        const index = Number(slider.dataset.index);
        const val = Number(slider.value);
        const entries = driverLinkedEntries();
        const entry = entries.find(en => en.kind === kind && en.index === index);
        const row = slider.closest('.target-row');
        const valueEl = row?.querySelector('.lvl-value');
        const resetBtn = row?.querySelector('.target-reset');
        const flagEl = row?.querySelector('.target-default-flag');
        if (valueEl) valueEl.textContent = `${val}: ${levelLabel(val)}`;
        if (entry) {
          entry.item.target_level = val;
        }
        if (resetBtn) resetBtn.style.display = '';
        if (flagEl) flagEl.style.display = 'none';
      }, true);

      summary?.addEventListener('click', (e) => {
        const btn = e.target.closest('.target-reset');
        if (!btn) return;
        const kind = btn.dataset.kind;
        const index = Number(btn.dataset.index);
        const entries = driverLinkedEntries();
        const entry = entries.find(en => en.kind === kind && en.index === index);
        if (!entry) return;
        entry.item.target_level = undefined;
        renderStep();
      });
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
      setSaving(true);
      try {
        // 1) Create role (or update if editing)
        let roleId = state.roleId;
        let createdNewRole = false;
        if (!roleId) {
          try {
            const created = await fetchJSON('/api/roles', { method: 'POST', body: JSON.stringify({
              name: state.name,
              description: state.description,
              department: state.department,
            }) });
            roleId = created.role?.id;
            state.roleId = roleId;
            createdNewRole = true;
          } catch (err) {
            if (err.status === 400 && (err?.message || '').toLowerCase().includes('already exists')) {
              const existingId = await findRoleIdByName(state.name);
              if (existingId) {
                roleId = existingId;
                state.roleId = roleId;
                showAlert('warning', `Role "${escapeHtml(state.name)}" already exists. Updating that profile instead.`);
              } else {
                showAlert('danger', escapeHtml(err.message || 'Role name already exists.'));
                setSaving(false);
                return;
              }
            } else {
              throw err;
            }
          }
        }

        if (!roleId) {
          showAlert('danger', 'Unable to determine role ID.');
          setSaving(false);
          return;
        }

        if (!createdNewRole) {
          try {
            await fetchJSON(`/api/roles/${roleId}`, { method: 'PATCH', body: JSON.stringify({
              name: state.name,
              description: state.description,
              department: state.department,
              is_active: true,
            }) });
          } catch (err) {
            if (err.status === 400 && (err?.message || '').toLowerCase().includes('already exists')) {
              showAlert('warning', `Using existing role "${escapeHtml(state.name)}".`);
            } else {
              throw err;
            }
          }
        }
        if (!roleId) throw new Error('Missing role id after create');
        // 2) upsert KSAOs
        await fetchJSON(`/api/roles/${roleId}/ksaos`, { method: 'POST', body: JSON.stringify({
          knowledge: serializeKsaoItems(state.knowledge),
          skills: serializeKsaoItems(state.skills),
          abilities: serializeKsaoItems(state.abilities),
          outcomes: serializeKsaoItems(state.outcomes),
        })});
        // 3) Targets are implied by KSAO target levels; no separate endpoint
        alert('Role Profile saved.');
        const fromAdmin = window.location.pathname.startsWith('/admin');
        window.location.href = fromAdmin ? '/admin/roles?saved=1' : '/roles';
      } catch (e) {
        console.error(e);
        const message = e?.message || 'Failed to save role profile.';
        showAlert('danger', message);
        setSaving(false);
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
        state.knowledge = (r.knowledge || []).map(x=>({
          name: x.name || '',
          description: x.description || '',
          driver_card_id: x.driver_card_id,
          driver_card_name: x.driver_card?.name,
          target_level: normalizeTargetLevel(x.target_level),
        }));
        state.skills = (r.skills || []).map(x=>({
          name: x.name || '',
          description: x.description || '',
          driver_card_id: x.driver_card_id,
          driver_card_name: x.driver_card?.name,
          target_level: normalizeTargetLevel(x.target_level),
        }));
        state.abilities = (r.abilities || []).map(x=>({
          name: x.name || '',
          description: x.description || '',
          driver_card_id: x.driver_card_id,
          driver_card_name: x.driver_card?.name,
          target_level: normalizeTargetLevel(x.target_level),
        }));
        state.outcomes = (r.outcomes || []).map(x=>({
          name: x.name || '',
          description: x.description || '',
          driver_card_id: x.driver_card_id,
          driver_card_name: x.driver_card?.name,
          target_level: normalizeTargetLevel(x.target_level),
        }));
        state.others = (r.others || []).map(x=>({ name: x.name || '', description: x.description || '' }));
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
  async function findRoleIdByName(name) {
    const query = (name || '').trim();
    if (!query) return null;
    try {
      const data = await fetchJSON(`/api/roles?q=${encodeURIComponent(query)}`);
      const match = (data.roles || []).find(role => (role.name || '').trim().toLowerCase() === query.toLowerCase());
      return match?.id || null;
    } catch {
      return null;
    }
  }
  function setSaving(isSaving) {
    const save = document.getElementById('wiz-save');
    const next = document.getElementById('wiz-next');
    const prev = document.getElementById('wiz-prev');
    [save, next, prev].forEach(btn => {
      if (!btn) return;
      btn.disabled = !!isSaving;
      btn.classList.toggle('is-loading', !!isSaving);
    });
    if (save) {
      if (isSaving) {
        if (!save.dataset.originalLabel) {
          save.dataset.originalLabel = save.textContent;
        }
        save.textContent = 'Saving…';
      } else if (save.dataset.originalLabel) {
        save.textContent = save.dataset.originalLabel;
      }
    }
  }
  function showAlert(level, message) {
    const container = document.getElementById('global-alerts') || document.querySelector('.flash-messages');
    if (container) {
      const alert = document.createElement('div');
      alert.className = `alert alert-${escapeAttr(level || 'info')}`;
      alert.innerHTML = `<span>${escapeHtml(message || '')}</span>`;
      container.append(alert);
      setTimeout(() => {
        alert.classList.add('alert-dismiss');
        setTimeout(() => alert.remove(), 400);
      }, 4000);
    } else {
      window.alert(message || 'Notification');
    }
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
