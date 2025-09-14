(function(){
  function $(sel){ return document.querySelector(sel); }
  function $all(sel){ return Array.from(document.querySelectorAll(sel)); }

  const els = {
    grid: null,
    status: null,
    pagination: null,
    sidebar: null,
    sidebarContent: null,
    selectionCount: null,
    btnGenerate: null,
    search: null,
    // Initial choice elements
    initialChoice: null,
    choiceFramework: null,
    choiceOutcome: null,
    // Competency step
    stepCompetencies: null,
    competencyList: null,
    searchRow: null,
    btnStartNew: null,
  };

  const state = {
    q: '',
    frameworkId: null,
    outcomeId: null,
    competencyId: null,
    startMode: null, // 'framework' | 'outcome' | null
    page: 1,
    pageSize: 20,
  };

  function setStatus(type, message){
    if(!els.status) return;
    if(!message){ els.status.style.display='none'; return; }
    els.status.className = 'notice ' + (type ? `notice-${type}` : '');
    els.status.textContent = message;
    els.status.style.display = 'block';
  }

  function skeleton(count=8){
    const frag = document.createDocumentFragment();
    for(let i=0;i<count;i++){
      const div = document.createElement('div');
      div.className = 'metric-card skeleton';
      div.innerHTML = '<div class="metric-header"><div class="metric-title sk-line"></div></div><div class="metric-content"><div class="sk-line"></div><div class="sk-line short"></div></div>';
      frag.appendChild(div);
    }
    return frag;
  }

  function badgeForKind(kind){ return (kind==='bias'?'Bias':'Driver'); }
  function iconForKind(kind){ return kind==='bias' ? '🧠' : '🧭'; }

  function renderGrid(items){
    if(!els.grid) return;
    els.grid.innerHTML = '';
    if(!items || !items.length){
      const empty = document.createElement('div');
      empty.className = 'no-data-message';
      empty.innerHTML = '<div class="no-data-icon">🗂️</div><h3>No items</h3><p>Try adjusting filters or search.</p>';
      els.grid.appendChild(empty);
      return;
    }
    const frag = document.createDocumentFragment();
    for(const card of items){
      const div = document.createElement('div');
      div.className = 'metric-card';
      div.setAttribute('data-id', card.id);
      div.innerHTML = `
        <div class="metric-header">
          <h3 class="metric-title">${iconForKind(card.kind||'driver')} ${escapeHtml(card.name)}</h3>
          <div class="metric-badges">
            ${card.outcome?.name ? `<span class="badge badge-outcome">${escapeHtml(card.outcome.name)}</span>` : ''}
            ${card.metric_type?.name ? `<span class="badge badge-type">${escapeHtml(card.metric_type.name)}</span>` : ''}
            <span class="badge badge-kind">${badgeForKind(card.kind)}</span>
          </div>
        </div>
        <div class="metric-content">
          <p class="metric-description">${escapeHtml(card.description || '')}</p>
        </div>
        <div class="metric-actions">
          <button class="btn btn-sm btn-outline" data-action="add" data-kind="${card.kind||'driver'}" data-id="${card.id}" data-label="${escapeAttr(card.name)}">Add to Plan</button>
        </div>
      `;
      frag.appendChild(div);
    }
    els.grid.appendChild(frag);
  }

  function escapeHtml(str){ return (str||'').replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[s])); }
  function escapeAttr(str){ return String(str||'').replace(/"/g,'&quot;'); }

  function updateInitialChoiceUI(){
    if(!els.initialChoice) return;
    // Always show the initial choice selectors at the top
    els.initialChoice.style.display = 'block';
    // Defaults
    if(els.choiceFramework){ els.choiceFramework.disabled = false; els.choiceFramework.parentElement.style.opacity = '1'; }
    if(els.choiceOutcome){ els.choiceOutcome.disabled = false; els.choiceOutcome.parentElement.style.opacity = '1'; }
    // Show competencies only when a framework is selected
    const hasFramework = !!state.frameworkId;
    if(els.stepCompetencies) els.stepCompetencies.style.display = hasFramework ? 'block' : 'none';
    if(!hasFramework && els.competencyList) els.competencyList.innerHTML = '';
    // Show search row only when we can show grid content
    if(els.searchRow){
      if(state.startMode === 'framework'){
        els.searchRow.style.display = state.competencyId ? 'block' : 'none';
      } else if(state.startMode === 'outcome'){
        els.searchRow.style.display = 'block';
      } else {
        els.searchRow.style.display = 'none';
      }
    }
  }

  async function loadGrid(){
    try{
      setStatus(null,'');
      // Gate grid when starting with framework but no competency selected
      if(state.startMode === 'framework' && !state.competencyId && !state.outcomeId){
        if(els.grid){ els.grid.innerHTML = ''; }
        return;
      }
      if(els.grid){ els.grid.innerHTML=''; els.grid.appendChild(skeleton(8)); }
      const ps = new URLSearchParams();
      if(state.q) ps.set('q', state.q);
      if(state.frameworkId) ps.set('framework_id', String(state.frameworkId));
      if(state.outcomeId) ps.set('outcome_id', String(state.outcomeId));
      if(state.competencyId) ps.set('competency_id', String(state.competencyId));
      ps.set('page', String(state.page));
      ps.set('page_size', String(state.pageSize));
      ps.set('sort', 'name');
      const url = `/api/driver-cards?${ps.toString()}`;
      const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if(!res.ok) throw new Error(`Failed to load (${res.status})`);
      const data = await res.json();
      renderGrid(data.items || []);
      // Pagination minimal (optional)
      if(els.pagination){ els.pagination.style.display = (data.pagination && data.pagination.pages>1) ? 'flex' : 'none'; }
    }catch(err){
      console.warn(err);
      setStatus('warning', err.message || 'Unable to load items');
      if(els.grid) els.grid.innerHTML = '';
    }
  }

  async function refreshSidebar(){
    try{
      const res = await fetch('/api/context/plan/items', { headers: { 'Accept': 'application/json' } });
      if(!res.ok) throw new Error('Failed to load plan items');
      const data = await res.json();
      const items = Array.isArray(data.items) ? data.items : [];
      const box = els.sidebarContent;
      box.innerHTML = '';
      // Update selection count
      if(els.selectionCount){ els.selectionCount.textContent = `${items.length} selected`; }
      if(!items.length){ box.innerHTML = '<p class="pb-empty">No items yet. Use “Add to Plan” on any card.</p>'; 
        if(els.btnGenerate){ els.btnGenerate.disabled = true; }
        // Clear CTA states
        $all('#pb-grid [data-action="add"]').forEach(b=>{ b.disabled=false; b.textContent='Add to Plan'; });
        return; }
      if(els.btnGenerate){ els.btnGenerate.disabled = false; }
      // Disable add buttons for items already selected
      try{
        const selectedIds = new Set(items.map(it => parseInt(it.source_id, 10)).filter(Number.isFinite));
        $all('#pb-grid [data-action="add"]').forEach(b=>{
          const id = parseInt(b.getAttribute('data-id'), 10);
          if(selectedIds.has(id)){
            b.disabled = true; b.textContent = 'In Plan'; b.classList.add('btn-success');
          } else {
            b.disabled = false; b.textContent = 'Add to Plan'; b.classList.remove('btn-success');
          }
        });
      }catch{}
      const groups = items.reduce((acc, it)=>{ (acc[it.kind]=acc[it.kind]||[]).push(it); return acc; }, {});
      const frag = document.createDocumentFragment();
      for(const kind of Object.keys(groups)){
        const group = document.createElement('div');
        group.className = 'pb-group';
        const title = document.createElement('div');
        title.style.fontWeight = '700';
        title.textContent = kind.charAt(0).toUpperCase()+kind.slice(1);
        group.appendChild(title);
        groups[kind].forEach(item => {
          const row = document.createElement('div');
          row.className = 'pb-item';
          row.innerHTML = `<span>${escapeHtml(item.label)}</span>`;
          const btn = document.createElement('button');
          btn.className = 'btn btn-sm btn-outline';
          btn.textContent = 'Remove';
          btn.addEventListener('click', async ()=>{
            try{ await fetch(`/api/context/plan/items/${item.id}`, { method:'DELETE' }); refreshSidebar(); }catch{}
          });
          row.appendChild(btn);
          group.appendChild(row);
        });
        frag.appendChild(group);
      }
      box.appendChild(frag);
    }catch(err){
      console.warn(err);
    }
  }

  async function addToPlan(kind, label, sourceId, meta, buttonEl){
    try{
      const res = await fetch('/api/context/plan/items', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind, label, source_id: sourceId, meta, source_page: 'plan_builder' })
      });
      if(!res.ok){ throw new Error('Failed to add to plan'); }
      await refreshSidebar();
      if(window.notify){ window.notify('success', `Added to plan: ${label}`); }
      if(buttonEl){
        buttonEl.disabled = true;
        buttonEl.textContent = 'In Plan';
        buttonEl.classList.add('btn-success');
      }
    }catch(err){ if(window.notify){ window.notify('error', err.message || 'Failed to add to plan'); } else { alert(err.message || 'Failed to add to plan'); } }
  }

  async function initSelectors(){
    // Populate initial choice selects
    try{
      const res = await fetch('/api/frameworks', { headers: { 'Accept': 'application/json' } });
      const data = await res.json();
      const items = (data && (data.frameworks || data.items)) ? (data.frameworks || data.items) : [];
      if(els.choiceFramework){ els.choiceFramework.innerHTML = '<option value="">— Choose a Framework —</option>' + items.map(f=>`<option value="${f.id}">${escapeHtml(f.name)}</option>`).join(''); }
    }catch{}
    try{
      const res = await fetch('/api/outcomes', { headers: { 'Accept': 'application/json' } });
      if(res.ok){ const data = await res.json(); const items = data.items || data.outcomes || []; if(els.choiceOutcome){ els.choiceOutcome.innerHTML = '<option value="">— Choose an Outcome —</option>' + items.map(o=>`<option value="${o.id}">${escapeHtml(o.name)}</option>`).join(''); } }
    }catch{}
  }

  async function renderCompetencies(frameworkId){
    if(!frameworkId || !els.competencyList) return;
    els.competencyList.innerHTML = '';
    try{
      const res = await fetch(`/api/frameworks/${frameworkId}/competencies`, { headers: { 'Accept':'application/json' } });
      if(!res.ok) throw new Error('Failed to load competencies');
      const data = await res.json();
      const comps = data.competencies || [];
      if(!comps.length){ els.competencyList.innerHTML = '<div class="pb-empty">No competencies available.</div>'; return; }
      const frag = document.createDocumentFragment();
      comps.forEach(c => {
        const a = document.createElement('button');
        a.type = 'button';
        a.className = 'badge badge-outline pb-competency';
        a.textContent = c.name;
        a.addEventListener('click', ()=>{
          // toggle active
          $all('.pb-competency').forEach(el => el.classList.remove('is-active'));
          a.classList.add('is-active');
          state.competencyId = c.id;
          state.page = 1;
          if(els.searchRow){ els.searchRow.style.display = 'block'; }
          loadGrid();
        });
        frag.appendChild(a);
      });
      els.competencyList.appendChild(frag);
    }catch(err){ els.competencyList.innerHTML = '<div class="pb-empty">Unable to load competencies.</div>'; }
  }

  function initEvents(){
    if(els.search){ els.search.addEventListener('input', ()=>{ state.q = els.search.value.trim(); state.page=1; loadGrid(); }); }
    // Initial choices
    if(els.choiceFramework){ els.choiceFramework.addEventListener('change', async ()=>{
      const val = els.choiceFramework.value;
      if(!val) return;
      state.startMode = 'framework';
      state.frameworkId = parseInt(val,10);
      state.outcomeId = null; state.competencyId = null; state.q = ''; state.page=1;
      updateInitialChoiceUI();
      if(els.searchRow) els.searchRow.style.display = 'none';
      await renderCompetencies(state.frameworkId);
      // persist framework context (fire-and-forget)
      try{ await fetch('/api/context/framework/state', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ framework_id: state.frameworkId }) }); }catch{}
      // grid will wait until competency selected
      loadGrid();
    }); }
    if(els.choiceOutcome){ els.choiceOutcome.addEventListener('change', ()=>{
      const val = els.choiceOutcome.value;
      if(!val) return;
      state.startMode = 'outcome';
      state.outcomeId = parseInt(val,10);
      state.frameworkId = null; state.competencyId = null; state.q = ''; state.page=1;
      updateInitialChoiceUI();
      if(els.stepCompetencies) els.stepCompetencies.style.display = 'none';
      // Clear any active competency pills (visual state) from previous framework flow
      $all('.pb-competency').forEach(el => el.classList.remove('is-active'));
      if(els.competencyList) els.competencyList.innerHTML = '';
      if(els.searchRow) els.searchRow.style.display = 'block';
      loadGrid();
    }); }
    if(els.grid){ els.grid.addEventListener('click', (e)=>{
      const btn = e.target.closest('button[data-action="add"]');
      if(!btn) return;
      const kind = (btn.getAttribute('data-kind')||'driver').toLowerCase();
      const id = parseInt(btn.getAttribute('data-id'), 10);
      const label = btn.getAttribute('data-label') || 'Item';
      // optimistic UI
      btn.disabled = true; btn.textContent = 'Adding…';
      addToPlan(kind, label, id, {}, btn);
    }); }
    if(els.btnGenerate){ els.btnGenerate.addEventListener('click', ()=>{
      try{ window.location.assign('/plan/report'); }
      catch(e){ setStatus('info', 'Opening report page…'); }
    }); }
    if(els.btnStartNew){ els.btnStartNew.addEventListener('click', async ()=>{
      // Clear plan items
      try{
        const res = await fetch('/api/context/plan/items', { headers:{'Accept':'application/json'} });
        const data = await res.json();
        const items = Array.isArray(data.items) ? data.items : [];
        for(const it of items){ try{ await fetch(`/api/context/plan/items/${it.id}`, { method:'DELETE' }); }catch{} }
      }catch{}
      // Reset framework context
      try{ await fetch('/api/context/framework/state', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ framework_id: null, active_competencies: [] }) }); }catch{}
      // Reset UI state
      state.q=''; state.frameworkId=null; state.outcomeId=null; state.competencyId=null; state.startMode=null; state.page=1;
      if(els.search) els.search.value='';
      if(els.stepCompetencies){ els.stepCompetencies.style.display='none'; if(els.competencyList) els.competencyList.innerHTML=''; }
      if(els.initialChoice) els.initialChoice.style.display='block';
      await refreshSidebar();
      els.grid.innerHTML = '';
    }); }
  }

  async function init(){
    els.grid = $('#pb-grid');
    els.status = $('#pb-status');
    els.pagination = $('#pb-pagination');
    els.sidebar = document.querySelector('.pb-sidebar');
    els.sidebarContent = $('#pb-sidebar-content');
    els.selectionCount = $('#pb-selection-count');
    els.btnGenerate = $('#pb-generate-report');
    els.search = $('#pb-search');
    els.initialChoice = $('#pb-initial-choice');
    els.choiceFramework = $('#pb-choice-framework');
    els.choiceOutcome = $('#pb-choice-outcome');
    els.stepCompetencies = $('#pb-step-competencies');
    els.competencyList = $('#pb-competency-list');
    els.searchRow = $('#pb-search-row');
    els.btnStartNew = $('#pb-start-new');

    await initSelectors();
    initEvents();

    // Detect active plan: existing selections or framework context
    let hasActive = false;
    // Do not resurrect old framework selection from session; require explicit selection now
    try{
      const r1 = await fetch('/api/context/plan/items', { headers:{'Accept':'application/json'} });
      const d1 = await r1.json();
      hasActive = Array.isArray(d1.items) && d1.items.length > 0;
    }catch{}

    if(hasActive){
      // Keep selectors visible but lock to the active mode
      updateInitialChoiceUI();
      if(state.frameworkId){ if(els.stepCompetencies) els.stepCompetencies.style.display='block'; await renderCompetencies(state.frameworkId); }
      await loadGrid();
    } else {
      updateInitialChoiceUI();
      // Ensure no competencies are shown when no framework is selected
      if(els.competencyList) els.competencyList.innerHTML = '';
    }
    await refreshSidebar();

    // Summary modal (Option B)
    const modal = document.getElementById('pb-summary-modal');
    const modalBody = document.getElementById('pb-summary-body');
    const modalClose = modal ? modal.querySelector('.modal-close') : null;
    function closeModal(){ if(modal) modal.style.display='none'; }
    if(modalClose) modalClose.addEventListener('click', closeModal);
    const backdrop = modal ? modal.querySelector('.modal-backdrop') : null;
    if(backdrop) backdrop.addEventListener('click', closeModal);
    document.addEventListener('keydown', (e)=>{ if(e.key==='Escape' && modal && modal.style.display==='block') closeModal(); });
    document.addEventListener('plan:generateReport', async ()=>{
      try{
        const res = await fetch('/api/context/plan/items', { headers: { 'Accept':'application/json' } });
        const data = await res.json();
        const items = Array.isArray(data.items) ? data.items : [];
        const groups = items.reduce((acc, it)=>{ (acc[it.kind]=acc[it.kind]||[]).push(it); return acc; }, {});

        // Compute suggested metric IDs
        const metricIds = new Set();
        // Drivers/heuristics with source_id are already metric IDs
        items.forEach(it => {
          if((it.kind==='driver' || it.kind==='heuristic') && it.source_id != null){
            const n = parseInt(it.source_id, 10); if(Number.isFinite(n)) metricIds.add(n);
          }
        });
        // For biases, query driver-cards with kind=bias&q=label to collect their metric ids
        for(const it of (groups['bias']||[])){
          try{
            const url = `/api/driver-cards?kind=bias&q=${encodeURIComponent(it.label)}&page_size=12`;
            const r = await fetch(url, { headers: { 'Accept':'application/json' } });
            if(r.ok){ const j = await r.json(); (j.items||[]).forEach(c=>{ if(c && c.id!=null) metricIds.add(c.id); }); }
          }catch(e){ /* ignore individual failures */ }
        }

        const section = [];
        section.push('<h2>Plan Summary</h2>');
        if(!items.length){
          section.push('<p>No items in your plan yet. Add drivers or biases using the grid, then try again.</p>');
        } else {
          Object.keys(groups).forEach(kind => {
            section.push(`<h4>${kind.charAt(0).toUpperCase()+kind.slice(1)}</h4>`);
            section.push('<ul>');
            groups[kind].forEach(it => section.push(`<li>${escapeHtml(it.label)}</li>`));
            section.push('</ul>');
          });
          section.push(`<div class="notice notice-info">Suggested metrics identified: <strong>${metricIds.size}</strong>.</div>`);
          if(metricIds.size > 0){
            section.push('<div class="cta-group" style="margin-top:12px;"><button id="pb-export-pdf" class="btn btn-primary">Download PDF (Summary)</button></div>');
          }
        }
        if(modalBody) modalBody.innerHTML = section.join('');
        if(modal) modal.style.display = 'block';

        // Hook up export after content is rendered
        const exportBtn = document.getElementById('pb-export-pdf');
        if(exportBtn){
          exportBtn.addEventListener('click', async ()=>{
            try{
              const body = {
                metric_ids: Array.from(metricIds),
                report_type: 'summary',
                recommendations: {},
                user_selections: { source: 'plan_builder' }
              };
              const r = await fetch('/pdf/generate-report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
              });
              if(!r.ok){
                let msg = `Failed to generate PDF (${r.status})`;
                try{ const j = await r.json(); if(j && j.error) msg += `: ${j.error}`; }catch{}
                throw new Error(msg);
              }
              const blob = await r.blob();
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url; a.download = 'LD_Metrics_Summary.pdf';
              document.body.appendChild(a); a.click(); a.remove();
              window.URL.revokeObjectURL(url);
            }catch(err){ alert(err.message || 'Failed to download PDF'); }
          });
        }
      }catch(err){ console.warn(err); }
    });
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
