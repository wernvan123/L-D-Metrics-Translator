/* Role Architect UI logic: list and wizard */

const RoleArchitect = (() => {
  async function fetchJSON(url, opts = {}) {
    const res = await fetch(url, Object.assign({ headers: { 'Accept': 'application/json' } }, opts));
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    return await res.json();
  }

  // List page
  async function loadList() {
    const tbody = document.getElementById('roles-tbody');
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
        return `
          <tr data-id="${r.id}">
            <td><input type="checkbox" class="row-check"></td>
            <td>${escapeHtml(r.name)}</td>
            <td>${escapeHtml(r.department || '')}</td>
            <td>${r.is_active ? 'Active' : 'Inactive'}</td>
            <td>${created}</td>
            <td>
              <a class="btn" href="/roles/new#edit=${r.id}">Edit</a>
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
    targets: [],
  };
  let stepIndex = 0;

  function renderStep() {
    const mount = document.getElementById('wizard-view');
    if (!mount) return;
    const step = steps[stepIndex];
    let html = '';
    if (step === 'basics') {
      html = `
        <div class="grid two">
          <label class="field"><span>Name</span>
            <input id="role-name" value="${escapeAttr(state.name)}" placeholder="e.g., Shift Supervisor" />
          </label>
          <label class="field"><span>Department</span>
            <input id="role-dept" value="${escapeAttr(state.department)}" placeholder="e.g., Operations" />
          </label>
        </div>
        <label class="field"><span>Description</span>
          <textarea id="role-desc" placeholder="Describe this role">${escapeHtml(state.description)}</textarea>
        </label>
      `;
    } else if (step === 'knowledge' || step === 'skills' || step === 'abilities' || step === 'others') {
      const key = step;
      const items = state[key] || [];
      html = `
        <div class="list-editor">
          <div class="row gap">
            <input id="item-input" placeholder="Add ${key.slice(0, -1)}" />
            <button id="item-add" class="btn">Add</button>
          </div>
          <ul id="item-list" class="list">
            ${items.map((x,i)=>`<li data-idx="${i}">${escapeHtml(x.name)} <button data-action="del" data-idx="${i}" class="btn">Remove</button></li>`).join('')}
          </ul>
        </div>
      `;
    } else if (step === 'targets') {
      html = `
        <div class="notice">Select competencies and their target levels (1-5). For now, paste competency IDs as a quick start.</div>
        <div class="grid two">
          <label class="field"><span>Competency ID</span><input id="tgt-cid" placeholder="e.g., 1" /></label>
          <label class="field"><span>Target level</span><input id="tgt-level" type="number" min="1" max="5" value="3" /></label>
        </div>
        <button id="tgt-add" class="btn">Add Target</button>
        <ul id="tgt-list" class="list mt">
          ${state.targets.map((t,i)=>`<li data-idx="${i}">#${t.competency_id} → ${t.target_level} <button class="btn" data-action="del" data-idx="${i}">Remove</button></li>`).join('')}
        </ul>
      `;
    } else if (step === 'review') {
      html = `
        <div class="review-block">
          <h3>Basics</h3>
          <p><strong>${escapeHtml(state.name)}</strong> (${escapeHtml(state.department)})</p>
          <p>${escapeHtml(state.description)}</p>
          <h3>Knowledge</h3><ul>${state.knowledge.map(x=>`<li>${escapeHtml(x.name)}</li>`).join('')}</ul>
          <h3>Skills</h3><ul>${state.skills.map(x=>`<li>${escapeHtml(x.name)}</li>`).join('')}</ul>
          <h3>Abilities</h3><ul>${state.abilities.map(x=>`<li>${escapeHtml(x.name)}</li>`).join('')}</ul>
          <h3>Others</h3><ul>${state.others.map(x=>`<li>${escapeHtml(x.name)}</li>`).join('')}</ul>
          <h3>Targets</h3><ul>${state.targets.map(t=>`<li>#${t.competency_id} → ${t.target_level}</li>`).join('')}</ul>
        </div>
      `;
    }
    mount.innerHTML = html;
    bindStepEvents();
    updateWizardButtons();
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
    } else if (step === 'knowledge' || step === 'skills' || step === 'abilities' || step === 'others') {
      const key = step;
      const input = document.getElementById('item-input');
      const addBtn = document.getElementById('item-add');
      const list = document.getElementById('item-list');
      addBtn?.addEventListener('click', () => {
        const v = (input.value || '').trim();
        if (v) {
          state[key].push({ name: v });
          renderStep();
          input.value = '';
        }
      });
      list?.addEventListener('click', (e) => {
        const tgt = e.target;
        if (tgt && tgt.dataset && tgt.dataset.action === 'del') {
          const idx = parseInt(tgt.dataset.idx, 10);
          state[key].splice(idx, 1);
          renderStep();
        }
      });
    } else if (step === 'targets') {
      const add = document.getElementById('tgt-add');
      const cid = document.getElementById('tgt-cid');
      const lvl = document.getElementById('tgt-level');
      const list = document.getElementById('tgt-list');
      add?.addEventListener('click', () => {
        const id = parseInt((cid.value || '').trim(), 10);
        const lv = parseInt((lvl.value || '3').trim(), 10);
        if (id && lv >= 1 && lv <= 5) {
          state.targets.push({ competency_id: id, target_level: lv, weight: 1.0 });
          renderStep();
          cid.value = '';
          lvl.value = '3';
        }
      });
      list?.addEventListener('click', (e) => {
        const tgt = e.target;
        if (tgt && tgt.dataset && tgt.dataset.action === 'del') {
          const idx = parseInt(tgt.dataset.idx, 10);
          state.targets.splice(idx, 1);
          renderStep();
        }
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
  function debounce(fn, wait) {
    let t; return (...args) => { clearTimeout(t); t = setTimeout(()=>fn.apply(null,args), wait); };
  }

  return { initList, initWizard };
})();
