  const renderer = window.DriverCardRenderer;
  if(!renderer){
    console.error('DriverCardRenderer is required for driver-cards.js');
  }

  // --- Mini Modal for quick nudge/concept preview ---
  function ensureMiniModal(){
    let modal = document.getElementById('dc-mini-modal');
    if(modal) return modal;
    modal = document.createElement('div');
    modal.id = 'dc-mini-modal';
    modal.className = 'mini-modal';
    modal.innerHTML = '<div class="mini-modal-backdrop"></div><div class="mini-modal-content"><button class="mini-close" aria-label="Close">×</button><div class="mini-body"></div></div>';
    document.body.appendChild(modal);
    modal.querySelector('.mini-close').addEventListener('click', ()=> modal.classList.remove('open'));
    modal.querySelector('.mini-modal-backdrop').addEventListener('click', ()=> modal.classList.remove('open'));
    return modal;
  }

  async function fetchByNameForPreview(name){
    try{
      const params = new URLSearchParams({ per_page: '25', q: name });
      const res = await fetch(`/api/metrics?${params.toString()}`);
      if(!res.ok) return null;
      const d = await res.json();
      const list = d.metrics || d.items || [];
      const m = list.find(x => (x.name||'').toLowerCase() === String(name).toLowerCase()) || list[0];
      return m ? renderer.normalize(m) : null;
    }catch{ return null; }
  }

  async function openMiniPreviewByName(name, kindHint){
    const mm = ensureMiniModal();
    const body = mm.querySelector('.mini-body');
    body.innerHTML = '<div class="loading-spinner"></div><p>Loading…</p>';
    mm.classList.add('open');
    const card = await fetchByNameForPreview(name);
    if(!card){
      body.innerHTML = `<div class="no-data-message"><div class="no-data-icon">⚠️</div><p>Could not find a card named "${name}"</p></div>`;
      return;
    }
    body.innerHTML = '';
    renderer.render(body, card, {
      renderActions: (container, normalized) => {
        const view = document.createElement('a');
        view.className = 'btn btn-outline';
        view.textContent = 'View in Playbook';
        view.href = `/playbook?q=${encodeURIComponent(normalized.name || '')}`;
        container.appendChild(view);
        const add = document.createElement('button');
        add.className = 'btn btn-primary';
        add.textContent = 'Add to Plan';
        add.addEventListener('click', () => addToPlan(normalized.kind || kindHint || 'driver', normalized.name, normalized.id, {}));
        container.appendChild(add);
      },
      onItemClick: (label) => openMiniPreviewByName(label),
      onBiasClick: (label) => openMiniPreviewByName(label, 'bias'),
      onNudgeClick: (label) => openMiniPreviewByName(label, 'nudge')
    });
  }
(function(){
  const api = {
    base: '/api/driver-cards'
  };

  const els = {
    search: null,
    grid: null,
    status: null,
    pagination: null,
    kindButtons: [],
    activeTagsBar: null,
    modal: null,
    modalBody: null,
    modalClose: null,
  };

  const state = {
    q: '',
    kind: 'all',
    page: 1,
    pageSize: 20,
    tags: [],
    frameworkId: null,
    frameworkSlug: null,
    competencyId: null,
    competencySlug: null,
  };

  function $(sel){ return document.querySelector(sel); }
  function $all(sel){ return Array.from(document.querySelectorAll(sel)); }

  function setStatus(type, message){
    if(!els.status) return;
    if(!message){ els.status.style.display = 'none'; return; }
    els.status.className = 'notice ' + (type ? `notice-${type}` : '');
    els.status.textContent = message;
    els.status.style.display = 'block';
  }

  // --- Deep-linking helpers ---
  function writeURL({ push=false, replace=false }={}){
    try{
      const ps = new URLSearchParams(window.location.search);
      // q
      if(state.q) ps.set('q', state.q); else ps.delete('q');
      // kind (omit 'all')
      if(state.kind && state.kind !== 'all') ps.set('kind', state.kind); else ps.delete('kind');
      // tags are handled by updateUrlTags(); preserve if already set
      const newUrl = `${window.location.pathname}?${ps.toString()}`;
      if(push) window.history.pushState({ q: state.q, kind: state.kind, tags: state.tags.slice() }, '', newUrl);
      else if(replace) window.history.replaceState({ q: state.q, kind: state.kind, tags: state.tags.slice() }, '', newUrl);
    }catch{}
  }

  function readURLIntoState(){
    try{
      const ps = new URLSearchParams(window.location.search);
      state.q = (ps.get('q')||'').trim();
      const k = (ps.get('kind')||'').toLowerCase();
      state.kind = (k && ['driver','bias','heuristic'].includes(k)) ? k : 'all';
      if(ps.has('tags')){
        const tags = (ps.get('tags')||'').split(',').map(s=>s.trim()).filter(Boolean);
        state.tags = tags;
      } else { state.tags = []; }
    }catch{}
  }

  function renderActiveTags(){
    const bar = els.activeTagsBar;
    if(!bar) return;
    bar.innerHTML = '';
    if(!state.tags || state.tags.length === 0){ bar.style.display = 'none'; return; }
    bar.style.display = 'flex';
    bar.classList.add('active-tags-bar');
    const frag = document.createDocumentFragment();
    state.tags.forEach(t => {
      const chip = document.createElement('button');
      chip.className = 'tag-chip active';
      chip.setAttribute('data-tag', t);
      chip.title = `Remove filter ${t}`;
      chip.innerHTML = `#${escapeHtml(t)} <span class="tag-remove" aria-hidden="true">×</span>`;
      chip.addEventListener('click', () => toggleTag(t));
      frag.appendChild(chip);
    });
    const clearBtn = document.createElement('button');
    clearBtn.className = 'btn btn-sm btn-link';
    clearBtn.textContent = 'Clear tags';
    clearBtn.addEventListener('click', () => {
      state.tags = []; updateUrlTags(); load();
    });
    bar.appendChild(frag);
    bar.appendChild(clearBtn);
  }

  function skeleton(count=6){
    const frag = document.createDocumentFragment();
    for(let i=0;i<count;i++){
      const wrapper = document.createElement('div');
      wrapper.className = 'metric-card playbook-card skeleton';
      wrapper.innerHTML = `
        <div class="driver-card">
          <div class="dc-header">
            <div class="sk-line sk-title"></div>
            <div class="sk-pill"></div>
          </div>
          <div class="sk-line sk-text"></div>
          <div class="sk-block"></div>
        </div>
      `;
      frag.appendChild(wrapper);
    }
    return frag;
  }

  function formatIdentifierType(idType){
    if(!idType) return '';
    const map = {
      trait_attribute: 'Trait/Attribute',
      behavior: 'Behavior',
      behaviour: 'Behavior',
      skill: 'Skill',
      concept: 'Concept',
      competency: 'Competency'
    };
    const key = String(idType).toLowerCase();
    return map[key] || key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  function getFrameworkEntries(card){
    const normalize = renderer && typeof renderer.normalize === 'function' ? renderer.normalize : null;
    const raw = normalize && !card.__normalized ? normalize(card) : card;
    const source = Array.isArray(raw.frameworks) && raw.frameworks.length ? raw.frameworks :
      (Array.isArray(card.associated_frameworks) ? card.associated_frameworks : []);
    return source
      .map(fw => {
        if(!fw) return null;
        if(typeof fw === 'string') return { name: fw };
        if(typeof fw === 'object'){
          const name = fw.name || fw.title || fw.framework_name || '';
          if(!name) return null;
          return { id: fw.id ?? fw.framework_id ?? null, name };
        }
        return null;
      })
      .filter(Boolean);
  }

  function renderGrid(items){
    if(!els.grid) return;
    els.grid.innerHTML = '';
    if(!items || !items.length){
      const empty = document.createElement('div');
      empty.className = 'no-data-message';
      empty.innerHTML = `
        <div class="no-data-icon">📚</div>
        <h3>No drivers match your current filters</h3>
        <p>Try broadening your search or clearing the filters.</p>
        <div style="margin-top:8px;">
          <button id="dc-clear-filters" class="btn btn-secondary">Clear All Filters</button>
        </div>
      `;
      els.grid.appendChild(empty);
      const clear = empty.querySelector('#dc-clear-filters');
      if(clear){
        clear.addEventListener('click', ()=>{
          state.q = '';
          state.kind = 'all';
          state.tags = [];
          writeURL({ replace:true });
          updateUrlTags();
          if(els.search) els.search.value = '';
          // reset segmented buttons UI
          els.kindButtons.forEach(b => b.classList.toggle('active', b.getAttribute('data-kind') === 'all'));
          load();
        });
      }
      return;
    }
    const frag = document.createDocumentFragment();
    for(const card of items){
      const normalized = renderer && typeof renderer.normalize === 'function' ? renderer.normalize(card) : card;
      const cardId = normalized.id ?? card.id;
      const div = document.createElement('div');
      div.className = 'metric-card';
      if(Number.isFinite(cardId)) div.setAttribute('data-id', cardId);
      const kindLabel = badgeForKind(normalized.kind || card.kind);
      const subTypeLabel = formatIdentifierType(normalized.identifier_type || card.identifier_type);
      const outcomeLabel = normalized.outcome?.name ? escapeHtml(normalized.outcome.name) : '—';
      const frameworks = getFrameworkEntries(normalized);
      const fwHtml = frameworks.length ? `
          <div class="metric-frameworks">
            <span class="metric-frameworks-label">Capability Framework${frameworks.length>1?'s':''}</span>
            <div class="metric-frameworks-chips">
              ${frameworks.slice(0,2).map(fw => `<span class="badge badge-framework">${escapeHtml(fw.name)}</span>`).join('')}
              ${frameworks.length>2 ? `<span class="badge badge-framework badge-framework--more">+${frameworks.length-2}</span>` : ''}
            </div>
          </div>` : '';

      let chainHtml = '';
      try{
        const stages = Array.isArray(normalized.driver_chain) ? normalized.driver_chain : Array.isArray(card.driver_chain) ? card.driver_chain : [];
        if(stages.length){
          const blocks = stages.map((st, index) => {
            const items = (st.items || []).slice(0,2).map(name => `<li><button class=\"dc-pill-link\" data-item-name=\"${escapeHtml(name)}\">${escapeHtml(name)}</button></li>`).join('');
            const remaining = Math.max(0, (st.items || []).length - 2);
            const extra = remaining ? `<li class=\"dc-more\">+${remaining} more</li>` : '';
            const empty = !items && !remaining ? '<li class=\"dc-empty\">No entries yet</li>' : '';
            const stageBlock = `
              <div class=\"dc-stage\">
                <div class=\"dc-stage-title\">${escapeHtml(st.title||'')}</div>
                <ul class=\"dc-stage-list\">${items || ''}${extra}${empty}</ul>
              </div>`;
            const arrow = index < stages.length - 1 ? '<div class=\"dc-arrow dc-arrow-down\" aria-hidden=\"true\">↓</div>' : '';
            return stageBlock + arrow;
          }).join('');
          chainHtml = `<div class=\"dc-chain dc-vertical\">${blocks}</div>`;
        }
      }catch{}

      div.innerHTML = `
        <div class="metric-header">
          <h3 class="metric-title">${escapeHtml(normalized.name || card.name || 'Driver')}</h3>
        </div>
        <div class="metric-meta">
          <span class="badge badge-kind">${kindLabel}</span>
          ${subTypeLabel ? `<span class="badge badge-subtype">${escapeHtml(subTypeLabel)}</span>` : ''}
        </div>
        <div class="metric-content">
          <p class="metric-description">${escapeHtml(normalized.description || card.description || '')}</p>
          ${fwHtml}
          <div class="metric-outcome">
            <span class="metric-outcome-label">L&D Outcome</span>
            <span class="metric-outcome-value">${outcomeLabel}</span>
          </div>
          ${chainHtml}
        </div>
        <div class="metric-actions">
          <button class="btn btn-sm btn-primary" data-action="add" data-kind="${escapeHtml((normalized.kind||card.kind||'driver'))}" data-id="${cardId}" data-label="${escapeHtml(normalized.name || card.name || 'Driver')}">Add to Plan</button>
          <button class="btn btn-sm btn-outline" data-action="view" data-id="${cardId}">View Details</button>
        </div>
      `;
      frag.appendChild(div);
    }
    els.grid.appendChild(frag);
    // After paint, update active tags bar if present
    renderActiveTags();
    // Delegate pill link clicks to open mini-preview (avoid binding per card)
    if(!els.grid._dcPillBound){
      els.grid.addEventListener('click', (e)=>{
        const pill = e.target.closest('.dc-pill-link');
        if(pill){
          const name = pill.getAttribute('data-item-name');
          if(name){ openMiniPreviewByName(name); }
        }
        const tag = e.target.closest('.tag-chip');
        if(tag && tag.hasAttribute('data-tag')){
          const t = tag.getAttribute('data-tag');
          if(t) toggleTag(t);
        }
      });
      els.grid._dcPillBound = true;
    }
  }

  function badgeForKind(kind){
    switch(kind){
      case 'bias': return 'Bias';
      case 'heuristic': return 'Heuristic';
      default: return 'Driver';
    }
  }

  async function addToPlan(kind, label, sourceId, meta){
    try{
      const res = await fetch('/api/context/plan/items', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind, label, source_id: sourceId, meta, source_page: 'playbook' })
      });
      if(!res.ok) throw new Error('Failed to add to plan');
      if(window.notify){ window.notify('success', `Added to plan: ${label}`); }
    }catch(err){ alert(err.message || 'Failed to add to plan'); }
  }

  function renderPagination(p){
    if(!els.pagination) return;
    els.pagination.innerHTML = '';
    if(!p || p.pages <= 1){ els.pagination.style.display = 'none'; return; }
    els.pagination.style.display = 'flex';
    const makeBtn = (label, page, disabled=false, active=false) => {
      const b = document.createElement('button');
      b.className = 'page-btn' + (active ? ' active' : '')
      b.textContent = label;
      b.disabled = !!disabled;
      b.addEventListener('click', () => {
        if(state.page === page) return;
        state.page = page; load();
      });
      return b;
    };
    els.pagination.appendChild(makeBtn('Prev', Math.max(1, (p.page || 1)-1), !p.has_prev));
    for(let i=1;i<=p.pages;i++){
      if(i === 1 || i === p.pages || Math.abs(i-(p.page||1)) <= 2){
        els.pagination.appendChild(makeBtn(String(i), i, false, i === (p.page||1)));
      } else if (i === 2 || i === p.pages-1){
        const sep = document.createElement('span'); sep.className='page-sep'; sep.textContent='…';
        els.pagination.appendChild(sep);
      }
    }
    els.pagination.appendChild(makeBtn('Next', Math.min(p.pages, (p.page||1)+1), !p.has_next));
  }

  function buildUrl(){
    const params = new URLSearchParams();
    if(state.q) params.set('q', state.q);
    if(state.kind && state.kind !== 'all') params.set('kind', state.kind);
    if(state.tags && state.tags.length) params.set('tags', state.tags.join(','));
    if(state.frameworkId) params.set('framework_id', String(state.frameworkId));
    if(state.frameworkSlug) params.set('framework_slug', String(state.frameworkSlug));
    if(state.competencyId) params.set('competency_id', String(state.competencyId));
    if(state.competencySlug) params.set('competency_slug', String(state.competencySlug));
    params.set('page', String(state.page));
    params.set('page_size', String(state.pageSize));
    params.set('sort', 'name');
    return `${api.base}?${params.toString()}`;
  }

  async function load(){
    try{
      setStatus(null, '');
      if(els.grid){
        els.grid.innerHTML = '';
        els.grid.appendChild(skeleton(8));
      }
      const res = await fetch(buildUrl(), { headers: { 'Accept': 'application/json' } });
      if(!res.ok){
        let msg = `Failed to load driver cards (${res.status})`;
        try{ const j = await res.json(); if(j && j.error){ msg = `${msg}: ${j.error}`; } }catch{}
        throw new Error(msg);
      }
      const data = await res.json();
      renderGrid(data.items);
      renderPagination(data.pagination);
    }catch(err){
      console.error(err);
      setStatus('warning', err.message || 'Unable to load driver cards');
      if(els.grid) els.grid.innerHTML = '';
    }
  }

  function onSearchInput(){
    const val = (els.search?.value || '').trim();
    state.q = val; state.page = 1; writeURL({ replace:true }); debouncedLoad();
  }

  function onKindClick(e){
    const btn = e.currentTarget;
    const k = btn.getAttribute('data-kind');
    state.kind = k || 'all'; state.page = 1; writeURL({ push:true });
    els.kindButtons.forEach(b => b.classList.toggle('active', b === btn));
    load();
  }

  // Simple debounce
  let tId = null;
  function debouncedLoad(){
    if(tId) window.clearTimeout(tId);
    tId = window.setTimeout(load, 300);
  }

  function escapeHtml(str){
    return (str||'').replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[s]));
  }

  function init(){
    els.search = $('#dc-search');
    els.grid = $('#dc-grid');
    els.status = $('#dc-status');
    els.pagination = $('#dc-pagination');
    els.kindButtons = $all('.seg-btn');
    els.activeTagsBar = $('#dc-active-tags');
    els.modal = document.getElementById('driver-card-modal');
    els.modalBody = document.getElementById('driver-card-modal-body');
    els.modalClose = els.modal ? els.modal.querySelector('.modal-close') : null;
    const clearBtn = document.getElementById('filter-clear');

    if(els.search){ els.search.addEventListener('input', onSearchInput); }
    els.kindButtons.forEach(b => b.addEventListener('click', onKindClick));

    // Clear All resets search, kind, and tags; also resets framework/capability selects if present
    if(clearBtn){
      clearBtn.addEventListener('click', () => {
        try{
          state.q = '';
          state.kind = 'all';
          state.tags = [];
          const fw = document.getElementById('fw-select');
          const comp = document.getElementById('comp-select');
          if(fw) fw.value = '';
          if(comp) comp.value = '';
          if(els.search) els.search.value = '';
          els.kindButtons.forEach(b => b.classList.toggle('active', b.getAttribute('data-kind') === 'all'));
          writeURL({ replace:true });
          updateUrlTags();
          load();
        }catch(err){ console.warn('Clear filters failed', err); }
      });
    }

    // Deep-linking: initialize from URL params if present
    try{
      const ps = new URLSearchParams(window.location.search);
      const toInt = (v) => { const n = parseInt(v, 10); return Number.isFinite(n) ? n : null; };
      if(ps.has('framework_id')) state.frameworkId = toInt(ps.get('framework_id'));
      if(ps.has('competency_id')) state.competencyId = toInt(ps.get('competency_id'));
      if(ps.has('framework_slug')) state.frameworkSlug = (ps.get('framework_slug')||'').trim() || null;
      if(ps.has('competency_slug')) state.competencySlug = (ps.get('competency_slug')||'').trim() || null;
      readURLIntoState();

      // Spreadsheet deep-link support: `filter=bias:[name]` or `filter=kind:bias;name:[name]`
      if(ps.has('filter')){
        const raw = (ps.get('filter')||'').trim();
        if(raw){
          // pattern 1: bias:[name]
          const biasPrefix = 'bias:';
          if(raw.toLowerCase().startsWith(biasPrefix)){
            const name = raw.slice(biasPrefix.length).trim();
            state.kind = 'bias';
            if(name) state.q = name;
          } else {
            // pattern 2: kind:bias;name:[name]
            // split on ';' then on ':'
            const parts = raw.split(';').map(s=>s.trim()).filter(Boolean);
            const kv = {};
            for(const p of parts){
              const idx = p.indexOf(':');
              if(idx > -1){
                const key = p.slice(0, idx).trim().toLowerCase();
                const val = p.slice(idx+1).trim();
                kv[key] = val;
              }
            }
            if(kv.kind && ['driver','bias','heuristic'].includes(kv.kind.toLowerCase())){
              state.kind = kv.kind.toLowerCase();
            }
            if(kv.name){ state.q = kv.name; }
          }
        }
      }
    }catch(err){ console.warn('driver-cards: URL param parse failed', err); }

    // Allow external components to set filters via custom event
    document.addEventListener('driverCards:setFilter', (ev) => {
      const detail = ev.detail || {};
      state.frameworkId = detail.frameworkId ?? null;
      state.frameworkSlug = detail.frameworkSlug ?? null;
      state.competencyId = detail.competencyId ?? null;
      state.competencySlug = detail.competencySlug ?? null;
      state.page = 1;
      load();
    });

    // Tag chip click (event delegation)
    if(els.grid){
      els.grid.addEventListener('click', (e) => {
        const chip = e.target.closest('.tag-chip');
        if(!chip) return;
        const tag = chip.getAttribute('data-tag');
        if(!tag) return;
        toggleTag(tag);
      });
      // View details
      els.grid.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-action="view"]');
        if(!btn) return;
        const id = btn.getAttribute('data-id');
        if(!id) return;
        openDetailsModal(parseInt(id,10));
      });
      // Add to plan (card action)
      els.grid.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-action="add"]');
        if(!btn) return;
        const kind = (btn.getAttribute('data-kind')||'driver').toLowerCase();
        const id = parseInt(btn.getAttribute('data-id'), 10);
        const label = btn.getAttribute('data-label') || 'Item';
        addToPlan(kind, label, Number.isFinite(id) ? id : null, {});
      });
      // Card click opens details (excluding interactive elements)
      els.grid.addEventListener('click', (e) => {
        if(e.defaultPrevented) return;
        if(e.target.closest('button[data-action="add"]')) return;
        if(e.target.closest('button[data-action="view"]')) return;
        if(e.target.closest('.tag-chip')) return;
        if(e.target.closest('.dc-pill-link')) return;
        if(e.target.closest('.seg-btn')) return;
        const cardEl = e.target.closest('.metric-card');
        if(!cardEl) return;
        const id = parseInt(cardEl.getAttribute('data-id'), 10);
        if(!Number.isFinite(id)) return;
        openDetailsModal(id);
      });
    }

    // Modal close handlers
    if(els.modal){
      const backdrop = els.modal.querySelector('.modal-backdrop');
      const close = () => closeModal();
      if(els.modalClose) els.modalClose.addEventListener('click', close);
      if(backdrop) backdrop.addEventListener('click', close);
      document.addEventListener('keydown', (ev) => {
        if(ev.key === 'Escape' && els.modal?.style.display === 'block') close();
      });
    }

    load();
  }

  function toggleTag(tag){
    const idx = state.tags.indexOf(tag);
    if(idx >= 0){ state.tags.splice(idx, 1); }
    else { state.tags.push(tag); }
    state.page = 1;
    // Update URL for deep-linking (non-destructive)
    updateUrlTags();
    load();
  }

  function updateUrlTags(){
    try{
      const ps = new URLSearchParams(window.location.search);
      if(state.tags.length) ps.set('tags', state.tags.join(',')); else ps.delete('tags');
      const newUrl = `${window.location.pathname}?${ps.toString()}`;
      window.history.replaceState({}, '', newUrl);
    }catch{}
    renderActiveTags();
  }

  async function openDetailsModal(id){
    try{
      if(!els.modal || !els.modalBody) return;
      els.modalBody.innerHTML = '<div class="modal-loading">Loading…</div>';
      els.modal.style.display = 'block';
      const res = await fetch(`${api.base}/${id}`, { headers: { 'Accept': 'application/json' }});
      if(!res.ok){ throw new Error(`Failed to load card ${id}`); }
      const data = await res.json();
      const card = data.driver_card || {};
      const normalized = renderer && typeof renderer.normalize === 'function' ? renderer.normalize(card) : card;
      const tags = Array.isArray(normalized.tags) ? normalized.tags : [];
      const tagHtml = tags.length ? `<div class="tag-chips">${tags.map(t=>`<button class=\"tag-chip\" data-tag=\"${escapeHtml(t)}\">#${escapeHtml(t)}</button>`).join('')}</div>` : '';
      const frameworks = getFrameworkEntries(normalized);
      const fwHtml = frameworks.length ? `
        <div class="dc-fw">
          <div class="dc-label">Capability Framework${frameworks.length>1?'s':''}</div>
          <ul class="dc-fw-list">
            ${frameworks.map(fw => {
              const name = escapeHtml(fw.name || 'Framework');
              return `<li><a class=\"dc-fw-link\" href=\"/playbook?q=${encodeURIComponent(fw.name || '')}\">${name}</a></li>`;
            }).join('')}
          </ul>
        </div>` : '';
      const kindLabel = badgeForKind(normalized.kind || card.kind);
      const exploreUrl = buildPlaybookLink(normalized, tags);
      const ident = (normalized.identifier_type || card.identifier_type || '').toString();
      const identLabel = ident ? ident.toUpperCase() : '';
      const identClass = ident ? `ident-${ident.toLowerCase()}` : '';
      const relatedItems = Array.isArray(normalized.related_items) && normalized.related_items.length
        ? normalized.related_items
        : (Array.isArray(card.related_items) ? card.related_items : []);

      // Build Driver Chain
      let chainHtml = '';
      try{
        const stages = Array.isArray(normalized.driver_chain) ? normalized.driver_chain : Array.isArray(card.driver_chain) ? card.driver_chain : [];
        if(stages.length){
          const blocks = stages.map(st => {
            const items = (st.items || []).map(name => `<li><button class=\"dc-pill-link\" data-item-name=\"${escapeHtml(name)}\">${escapeHtml(name)}</button></li>`).join('');
            return `
              <div class=\"dc-stage\">
                <div class=\"dc-stage-title\">${escapeHtml(st.title||'')}</div>
                <ul class=\"dc-stage-list\">${items}</ul>
              </div>`;
          }).join('<div class=\"dc-arrow\">→</div>');
          chainHtml = `<div class=\"dc-chain\">${blocks}</div>`;
        }
      }catch{}

      // Build Classification grid
      let classHtml = '';
      try{
        const c = normalized.classification || card.classification || {};
        const cells = [
          {k: 'L&D OUTCOME', v: c.ld_outcome || normalized.outcome?.name || card.outcome?.name || ''},
          {k: 'METRIC TYPE', v: c.metric_type || normalized.metric_type?.name || card.metric_type?.name || ''},
          {k: 'DATA COLLECTION', v: c.data_collection || normalized.classification?.data_collection || ''},
          {k: 'FREQUENCY', v: c.frequency || normalized.classification?.frequency || ''},
        ];
        classHtml = `
          <div class=\"dc-class\">
            <div class=\"dc-label\">Classification Details</div>
            <div class=\"dc-grid\">
              ${cells.map(c=>`<div class=\"dc-pill\"><div class=\"dc-pill-k\">${escapeHtml(c.k)}</div><div class=\"dc-pill-v\">${escapeHtml(c.v||'—')}</div></div>`).join('')}
            </div>
          </div>`;
      }catch{}

      // Neuro section (optional)
      let neuroHtml = '';
      try{
        const neuro = normalized.neuro_link || normalized.neuropsychology || card.neuro_link || card.neuropsychology;
        if(neuro){
          neuroHtml = `
            <div class=\"dc-neuro\">
              <div class=\"dc-label\">Neuropsychology Link</div>
              <div class=\"dc-neuro-text\">${escapeHtml(neuro)}</div>
            </div>`;
        }
      }catch{}
      els.modalBody.innerHTML = `
        <div class="driver-card-detail">
          <h2>${escapeHtml(normalized.name || card.name || 'Driver')}</h2>
          <div class="detail-badges">
            ${normalized.outcome?.name ? `<span class=\"badge badge-outcome\">${escapeHtml(normalized.outcome.name)}</span>` : ''}
            ${normalized.metric_type?.name ? `<span class=\"badge badge-type\">${escapeHtml(normalized.metric_type.name)}</span>` : ''}
            <span class="badge badge-kind">${kindLabel}</span>
            ${identLabel ? `<span class=\"badge badge-ident ${identClass}\">${escapeHtml(identLabel)}</span>` : ''}
          </div>
          <p class="detail-description">${escapeHtml(normalized.description || card.description || '')}</p>
          ${tagHtml}
          ${fwHtml}
          ${chainHtml}
          ${neuroHtml}
          ${classHtml}
          <div class="detail-actions">
            <button class="btn btn-secondary" data-action="add-plan" data-kind="${normalized.kind||card.kind||'driver'}" data-id="${normalized.id||card.id}" data-label="${escapeHtml(normalized.name||card.name||'Item')}">Add to Plan</button>
            <a class="btn btn-primary" href="${exploreUrl}">Explore Nudges in Playbook</a>
          </div>
          ${relatedItems.length ? `
            <div class="related-list"><h4>Related</h4>
              <div class="dc-related-chips">
                ${relatedItems.map(r => `<button class="tag-chip related-chip" data-related-id="${r.id}" title="View ${escapeHtml(r.name)}">${escapeHtml(r.name)}<span class="related-kind">${escapeHtml(badgeForKind(r.kind))}</span></button>`).join('')}
              </div>
            </div>` : ''}
        </div>
      `;
      // Tag chip and related link interactions inside modal (delegated, persistent)
      const modalDelegatedHandler = (e) => {
        const chip = e.target.closest('.tag-chip');
        if(chip){
          const t = chip.getAttribute('data-tag');
          if(t){ toggleTag(t); }
          return;
        }
        const pill = e.target.closest('.dc-pill-link');
        if(pill){
          const name = pill.getAttribute('data-item-name');
          if(name){ openMiniPreviewByName(name); }
          return;
        }
        const nudge = e.target.closest('.nudge-chip');
        if(nudge){
          const name = nudge.getAttribute('data-nudge-name');
          if(name){ openMiniPreviewByName(name, 'nudge'); }
          return;
        }
        const rel = e.target.closest('.related-chip');
        if(rel){
          e.preventDefault();
          const rid = parseInt(rel.getAttribute('data-related-id'), 10);
          if(rid) openDetailsModal(rid);
          return;
        }
      };
      // Ensure we don't multiply bind across openings
      try { els.modalBody.removeEventListener('click', modalDelegatedHandler); } catch {}
      els.modalBody.addEventListener('click', modalDelegatedHandler);

      // Bind Add to Plan specifically to its button so it cannot be pre-consumed by other clicks
      const addBtn = els.modalBody.querySelector('button[data-action="add-plan"]');
      if(addBtn){
        addBtn.addEventListener('click', () => {
          const kind = (addBtn.getAttribute('data-kind')||'driver').toLowerCase();
          const sid = parseInt(addBtn.getAttribute('data-id'), 10);
          const label = addBtn.getAttribute('data-label') || 'Item';
          addToPlan(kind, label, sid, {});
        }, { once: true });
      }
    }catch(err){
      console.warn(err);
      if(els.modalBody) els.modalBody.innerHTML = `<div class="modal-error">${escapeHtml(err.message || 'Failed to load')}</div>`;
    }
  }

  function closeModal(){ if(els.modal){ els.modal.style.display = 'none'; } }

  function buildPlaybookLink(card, tags){
    try{
      const ps = new URLSearchParams();
      if(card.kind && card.kind !== 'driver') ps.set('kind', card.kind);
      if(tags && tags.length) ps.set('tags', tags.join(','));
      ps.set('q', card.name || '');
      return `/playbook?${ps.toString()}`;
    }catch{ return '/playbook'; }
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
