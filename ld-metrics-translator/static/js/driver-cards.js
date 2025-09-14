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
      return m || null;
    }catch{ return null; }
  }

  async function openMiniPreviewByName(name, kindHint){
    const mm = ensureMiniModal();
    const body = mm.querySelector('.mini-body');
    body.innerHTML = '<div class="loading-spinner"></div><p>Loading…</p>';
    mm.classList.add('open');
    const m = await fetchByNameForPreview(name);
    body.innerHTML = '';
    const title = document.createElement('div'); title.className = 'mini-title'; title.textContent = name;
    const desc = document.createElement('div'); desc.className = 'mini-desc'; desc.textContent = (m && m.description) ? m.description : '';
    const actions = document.createElement('div'); actions.className = 'mini-actions';
    const link = document.createElement('a'); link.className = 'btn btn-outline'; link.textContent = 'Open in Nudge Library'; link.href = `/playbook?kind=nudge&q=${encodeURIComponent(name)}`;
    const add = document.createElement('button'); add.className = 'btn btn-primary'; add.textContent = 'Add to Plan';
    add.addEventListener('click', async ()=>{
      add.disabled = true; const prev = add.textContent; add.textContent = 'Adding…';
      try{
        const res = await fetch('/api/context/plan/items',{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ kind: (kindHint||'driver'), label: name, source_id: m?.id || null, source_page: 'playbook-mini' })});
        if(!res.ok) throw new Error('HTTP '+res.status);
        add.textContent = 'Added!'; setTimeout(()=>{ add.textContent = 'In Plan'; add.classList.add('btn-secondary'); }, 600);
      }catch{ add.textContent = prev; add.disabled = false; }
    });
    actions.appendChild(link); actions.appendChild(add);
    body.appendChild(title); body.appendChild(desc); body.appendChild(actions);
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

  function skeleton(count=8){
    const frag = document.createDocumentFragment();
    for(let i=0;i<count;i++){
      const div = document.createElement('div');
      div.className = 'metric-card skeleton';
      div.innerHTML = `
        <div class="metric-header"><div class="metric-title sk-line"></div></div>
        <div class="metric-content"><div class="sk-line"></div><div class="sk-line short"></div></div>
      `;
      frag.appendChild(div);
    }
    return frag;
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
      const div = document.createElement('div');
      div.className = 'metric-card';
      div.setAttribute('data-id', card.id);
      // Build compact chain (first 2 items per stage)
      let chainHtml = '';
      try{
        const stages = Array.isArray(card.driver_chain) ? card.driver_chain : [];
        if(stages.length){
          const blocks = stages.map(st => {
            const items = (st.items||[]).slice(0,2).map(name => `<li><button class=\"dc-pill-link\" data-item-name=\"${escapeHtml(name)}\">${escapeHtml(name)}</button></li>`).join('');
            return `
              <div class=\"dc-stage\">
                <div class=\"dc-stage-title\">${escapeHtml(st.title||'')}</div>
                <ul class=\"dc-stage-list\">${items}${(st.items||[]).length>2?`<li>+${(st.items||[]).length-2} more</li>`:''}</ul>
              </div>`;
          }).join('<div class=\"dc-arrow\">→</div>');
          chainHtml = `<div class=\"dc-chain dc-compact\">${blocks}</div>`;
        }
      }catch{}
      const ident = (card.identifier_type || '').toString();
      const identLabel = ident ? ident.toUpperCase() : '';
      const identClass = ident ? `ident-${ident.toLowerCase()}` : '';
      div.innerHTML = `
        <div class="metric-header">
          <h3 class="metric-title">${escapeHtml(card.name)}</h3>
          <div class="metric-badges">
            <span class="badge badge-kind">${badgeForKind(card.kind)}</span>
            ${card.outcome?.name ? `<span class="badge badge-outline badge-outcome">${escapeHtml(card.outcome.name)}</span>` : ''}
            ${card.metric_type?.name ? `<span class="badge badge-outline badge-type">${escapeHtml(card.metric_type.name)}</span>` : ''}
          </div>
        </div>
        ${identLabel ? `<span class=\"badge badge-ident ${identClass}\">${escapeHtml(identLabel)}</span>` : ''}
        <div class="metric-content">
          <p class="metric-description">${escapeHtml(card.description || '')}</p>
          ${(Array.isArray(card.tags) && card.tags.length) ? `
            <div class="tag-chips">
              ${card.tags.map(t => `<button class="tag-chip" data-tag="${escapeHtml(t)}" title="Filter by ${escapeHtml(t)}">#${escapeHtml(t)}</button>`).join('')}
            </div>
          ` : ''}
          ${chainHtml}
        </div>
        <div class="metric-actions">
          <button class="btn btn-sm btn-primary" data-action="add" data-kind="${escapeHtml(card.kind||'driver')}" data-id="${card.id}" data-label="${escapeHtml(card.name)}">Add to Plan</button>
          <button class="btn btn-sm btn-outline" data-action="view" data-id="${card.id}">View Details</button>
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
      const tags = Array.isArray(card.tags) ? card.tags : [];
      const tagHtml = tags.length ? `<div class="tag-chips">${tags.map(t=>`<button class=\"tag-chip\" data-tag=\"${escapeHtml(t)}\">#${escapeHtml(t)}</button>`).join('')}</div>` : '';
      const kindLabel = badgeForKind(card.kind);
      const exploreUrl = buildPlaybookLink(card, tags);
      const ident = (card.identifier_type || '').toString();
      const identLabel = ident ? ident.toUpperCase() : '';
      const identClass = ident ? `ident-${ident.toLowerCase()}` : '';

      // Build Driver Chain
      let chainHtml = '';
      try{
        const stages = Array.isArray(card.driver_chain) ? card.driver_chain : [];
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
        const c = card.classification || {};
        const cells = [
          {k: 'L&D OUTCOME', v: c.ld_outcome || card.outcome?.name || ''},
          {k: 'METRIC TYPE', v: c.metric_type || card.metric_type?.name || ''},
          {k: 'DATA COLLECTION', v: c.data_collection || ''},
          {k: 'FREQUENCY', v: c.frequency || ''},
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
        const neuro = card.neuro_link || card.neuropsychology;
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
          <h2>${escapeHtml(card.name || 'Driver')}</h2>
          <div class="detail-badges">
            ${card.outcome?.name ? `<span class=\"badge badge-outcome\">${escapeHtml(card.outcome.name)}</span>` : ''}
            ${card.metric_type?.name ? `<span class=\"badge badge-type\">${escapeHtml(card.metric_type.name)}</span>` : ''}
            <span class="badge badge-kind">${kindLabel}</span>
            ${identLabel ? `<span class=\"badge badge-ident ${identClass}\">${escapeHtml(identLabel)}</span>` : ''}
          </div>
          <p class="detail-description">${escapeHtml(card.description || '')}</p>
          ${tagHtml}
          ${chainHtml}
          ${neuroHtml}
          ${classHtml}
          <div class="detail-actions">
            <button class="btn btn-secondary" data-action="add-plan" data-kind="${card.kind||'driver'}" data-id="${card.id}" data-label="${escapeHtml(card.name||'Item')}">Add to Plan</button>
            <a class="btn btn-primary" href="${exploreUrl}">Explore Nudges in Playbook</a>
          </div>
          ${Array.isArray(card.related_nudges) && card.related_nudges.length ? `
            <div class="related-list"><h4>Recommended Nudges</h4>
              <div class="dc-related-chips">
                ${card.related_nudges.map(n => `<button class=\"tag-chip tag-chip--nudge nudge-chip\" data-nudge-name=\"${escapeHtml(n)}\" title=\"Preview ${escapeHtml(n)}\">${escapeHtml(n)}</button>`).join('')}
              </div>
            </div>` : ''}
          ${Array.isArray(card.related_items) && card.related_items.length ? `
            <div class="related-list"><h4>Related</h4><ul>
              ${card.related_items.map(r => `<li><a href="#" data-related-id="${r.id}" class="related-link">${escapeHtml(r.name)} (${escapeHtml(badgeForKind(r.kind))})</a></li>`).join('')}
            </ul></div>` : ''}
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
        const rel = e.target.closest('.related-link');
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
