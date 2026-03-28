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
    btnExportSummary: null,
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
    // Outcome-start panels
    outcomePanels: null,
    outcomeOverview: null,
    outcomeDrivers: null,
    outcomeNudges: null,
    outcomeMetrics: null,
    outcomeReview: null,
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

  function getSessionId(){
    try{
      if(window.currentSession && window.currentSession.id){ return String(window.currentSession.id); }
    }catch{}
    try{
      const stored = sessionStorage.getItem('context:session_id');
      if(stored) return String(stored);
    }catch{}
    try{
      let sid = localStorage.getItem('sessionId');
      if(!sid){ sid = String(Math.floor(Date.now()/1000)); localStorage.setItem('sessionId', sid); }
      return sid;
    }catch{}
    return String(Date.now());
  }

  function loadMiniSelections(){
    try{
      const raw = sessionStorage.getItem('plan:selections');
      if(!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    }catch{return [];}
  }

  async function buildReportPayload(title){
    const miniSelections = loadMiniSelections();
    const payload = {
      title,
      template_type: 'comprehensive',
      selected_outcomes: [],
      selected_metrics: [],
      selected_concepts: [],
      ai_recommendations: [],
      session_id: getSessionId(),
      generation_context: { source: 'plan_builder', mode: state.startMode || null }
    };

    const driverItems = [];
    try{
      const res = await fetch('/api/context/plan/items', { headers:{'Accept':'application/json'} });
      if(res.ok){
        const data = await res.json();
        if(Array.isArray(data.items)) driverItems.push(...data.items);
      }
    }catch{}

    const all = [...driverItems];
    const existingKeys = new Set(all.map(it=>`${it.kind||''}:${(it.label||'').toLowerCase()}`));
    for(const sel of miniSelections){
      const key = `${sel.kind||''}:${(sel.label||'').toLowerCase()}`;
      if(existingKeys.has(key)) continue;
      all.push({ kind: sel.kind, label: sel.label, meta: sel.meta || {} });
    }

    for(const item of all){
      const kind = (item.kind || '').toLowerCase();
      const label = item.label || '';
      if(kind === 'metric' || kind === 'kpi'){
        if(item.source_id != null){
          payload.selected_metrics.push(Number(item.source_id));
        } else if(label){
          payload.selected_metrics.push(label);
        }
      } else if(kind === 'outcome'){
        if(item.source_id != null){ payload.selected_outcomes.push(Number(item.source_id)); }
        else if(label){ payload.selected_outcomes.push(label); }
      } else if(kind === 'driver' || kind === 'nudge' || kind === 'bias' || kind === 'gap'){
        payload.selected_concepts.push({ kind, label });
      }
    }

    payload.selected_outcomes = Array.from(new Set(payload.selected_outcomes)).filter(Boolean);
    payload.selected_metrics = Array.from(new Set(payload.selected_metrics)).filter(Boolean);
    payload.selected_concepts = payload.selected_concepts.filter(x=>x && x.label);

    return payload;
  }

  async function loadOutcomePanels(){
    try{
      // Ensure visibility state matches
      if(els.outcomePanels) els.outcomePanels.style.display = (state.startMode==='outcome' && state.outcomeId)?'block':'none';
      if(!state.outcomeId) return;
      await Promise.all([
        renderOutcomeOverview(state.outcomeId),
        renderSuggestedDrivers(state.outcomeId),
        renderSuggestedNudges(state.outcomeId),
        renderOutcomeMetrics(state.outcomeId),
        renderOutcomeReview()
      ]);
    }catch(e){ console.warn('loadOutcomePanels failed', e); }
  }

  async function renderOutcomeOverview(outcomeId){
    if(!els.outcomeOverview) return;
    try{
      let name = `Outcome #${outcomeId}`; let desc = '';
      // Try to fetch from outcomes list
      const r = await fetch('/api/outcomes', { headers:{'Accept':'application/json'} });
      if(r.ok){ const j = await r.json(); const items = j.items||j.outcomes||[]; const found = items.find(o=>String(o.id)===String(outcomeId)); if(found){ name = found.name||name; desc = found.description||''; } }
      els.outcomeOverview.innerHTML = `<div><strong>${escapeHtml(name)}</strong></div>${desc?`<p class="meta">${escapeHtml(desc)}</p>`:''}`;
    }catch{ els.outcomeOverview.textContent = 'Selected outcome overview unavailable.'; }
  }

  async function renderSuggestedDrivers(outcomeId){
    if(!els.outcomeDrivers) return;
    els.outcomeDrivers.innerHTML = 'Loading…';
    try{
      const url = `/api/driver-cards?outcome_id=${encodeURIComponent(outcomeId)}&kind=driver&page_size=8&sort=name`;
      const r = await fetch(url, { headers:{'Accept':'application/json'} });
      if(!r.ok) throw new Error('Failed');
      const j = await r.json();
      const items = j.items||[];
      if(!items.length){ els.outcomeDrivers.innerHTML = '<div class="pb-empty">No suggested drivers for this outcome.</div>'; return; }
      const headerMeta = items[0]?.outcome?.name ? `Curated for ${escapeHtml(items[0].outcome.name)}` : 'Curated from playbook insights';
      renderSuggestionSection(els.outcomeDrivers, items, {
        kind: 'driver',
        title: 'Suggested Drivers',
        meta: headerMeta,
        renderItem: (card)=>suggestionRow(card,'driver'),
        batchLabel: 'Add all drivers'
      });
    }catch(e){ els.outcomeDrivers.innerHTML = '<div class="pb-empty">Unable to load suggested drivers.</div>'; }
  }

  async function renderSuggestedNudges(outcomeId){
    if(!els.outcomeNudges) return;
    els.outcomeNudges.innerHTML = 'Loading…';
    try{
      const url = `/api/driver-cards?outcome_id=${encodeURIComponent(outcomeId)}&kind=bias&page_size=8&sort=name`;
      const r = await fetch(url, { headers:{'Accept':'application/json'} });
      if(!r.ok) throw new Error('Failed');
      const j = await r.json();
      const items = j.items||[];
      if(!items.length){ els.outcomeNudges.innerHTML = '<div class="pb-empty">No suggested nudges for this outcome.</div>'; return; }
      const headerMeta = items[0]?.outcome?.name ? `Designed to reduce biases affecting ${escapeHtml(items[0].outcome.name)}` : 'Behavioral nudges for this focus area';
      renderSuggestionSection(els.outcomeNudges, items, {
        kind: 'bias',
        title: 'Suggested Nudges',
        meta: headerMeta,
        renderItem: (card)=>suggestionRow(card,'bias'),
        batchLabel: 'Add all nudges'
      });
    }catch(e){ els.outcomeNudges.innerHTML = '<div class="pb-empty">Unable to load suggested nudges.</div>'; }
  }

  async function renderOutcomeMetrics(outcomeId){
    if(!els.outcomeMetrics) return;
    els.outcomeMetrics.innerHTML = 'Loading…';
    try{
      const url = `/api/metrics?outcome_id=${encodeURIComponent(outcomeId)}&per_page=10`;
      const r = await fetch(url, { headers:{'Accept':'application/json'} });
      if(!r.ok) throw new Error('Failed');
      const j = await r.json();
      const items = (j.metrics)||[];
      if(!items.length){ els.outcomeMetrics.innerHTML = '<div class="pb-empty">No metrics found for this outcome.</div>'; return; }
      renderSuggestionSection(els.outcomeMetrics, items, {
        kind: 'metric',
        title: 'Metrics & KPIs',
        meta: 'Evidence-based indicators to track this outcome',
        renderItem: metricSuggestionCard,
        batchLabel: 'Add top 3 metrics',
        batchLimit: 3
      });
      if(!els.outcomeMetrics.dataset.clickBound){
        els.outcomeMetrics.addEventListener('click', onOutcomeMetricsClick);
        els.outcomeMetrics.dataset.clickBound = '1';
      }
    }catch(e){ els.outcomeMetrics.innerHTML = '<div class="pb-empty">Unable to load metrics.</div>'; }
  }

  async function renderOutcomeReview(){
    if(!els.outcomeReview) return;
    try{
      const r = await fetch('/api/context/plan/items', { headers:{'Accept':'application/json'} });
      const j = await r.json();
      const items = Array.isArray(j.items)?j.items:[];
      if(!items.length){ els.outcomeReview.textContent = 'No items in your plan yet.'; return; }
      const groups = items.reduce((acc,it)=>{ (acc[it.kind]=acc[it.kind]||[]).push(it); return acc; },{});
      const html = Object.keys(groups).map(k=>{
        return `<div class="pb-group"><div style="font-weight:700">${k.charAt(0).toUpperCase()+k.slice(1)}</div><ul class="list">${groups[k].map(it=>`<li>${escapeHtml(it.label)}</li>`).join('')}</ul></div>`;
      }).join('');
      els.outcomeReview.innerHTML = html;
    }catch{ els.outcomeReview.textContent = 'Unable to load selections.'; }
  }

  function suggestionRow(card, kind){
    const resolvedKind = (kind || card.kind || 'driver').toLowerCase();
    const id = card.id;
    const title = escapeHtml(card.name || 'Item');
    const desc = escapeHtml(card.description || card.summary || '');
    const outcomeName = escapeHtml(card?.outcome?.name || '');
    const metricTypeName = escapeHtml(card?.metric_type?.name || '');
    const badges = [];
    if(outcomeName){ badges.push(`<span class="badge badge-outcome">${outcomeName}</span>`); }
    if(metricTypeName){ badges.push(`<span class="badge badge-type">${metricTypeName}</span>`); }
    badges.push(`<span class="badge badge-kind">${badgeForKind(resolvedKind)}</span>`);
    const playbookUrl = `/playbook?kind=${encodeURIComponent(resolvedKind)}&q=${encodeURIComponent(card.name || '')}`;

    return `
      <article class="suggestion-card suggestion-card--${resolvedKind}">
        <header class="suggestion-card__header">
          <div class="suggestion-card__title">
            <span class="suggestion-card__icon" aria-hidden="true">${iconForKind(resolvedKind)}</span>
            <span>${title}</span>
          </div>
          <div class="suggestion-card__badges">${badges.join('')}</div>
        </header>
        <p class="suggestion-card__description">${desc || '<span class="suggestion-card__empty">No description provided yet.</span>'}</p>
        <footer class="suggestion-card__footer">
          <button class="btn btn-sm btn-primary" data-suggest-add data-kind="${resolvedKind}" data-id="${id}" data-label="${escapeAttr(card.name)}">Add to Plan</button>
          <a class="suggestion-card__link" href="${playbookUrl}" target="_blank" rel="noopener">Open in Playbook</a>
        </footer>
      </article>
    `;
  }

  function metricSuggestionCard(metric){
    const label = metric.name || `Metric #${metric.id}`;
    const title = escapeHtml(label);
    const description = escapeHtml(metric.description || metric.summary || metric.example || '');
    const outcomeName = escapeHtml(metric?.outcome?.name || metric?.outcome_name || '');
    const metricTypeName = escapeHtml(metric?.metric_type?.name || metric?.metric_type_name || '');
    const badges = [];
    if(outcomeName){ badges.push(`<span class="badge badge-outcome">${outcomeName}</span>`); }
    if(metricTypeName){ badges.push(`<span class="badge badge-type">${metricTypeName}</span>`); }
    badges.push('<span class="badge badge-kind">Metric</span>');
    const playbookUrl = `/playbook?kind=metric&q=${encodeURIComponent(label)}`;

    return `
      <article class="suggestion-card suggestion-card--metric" data-label="${escapeAttr(label)}">
        <header class="suggestion-card__header">
          <div class="suggestion-card__title">
            <span class="suggestion-card__icon" aria-hidden="true">📊</span>
            <span>${title}</span>
          </div>
          <div class="suggestion-card__badges">${badges.join('')}</div>
        </header>
        <p class="suggestion-card__description">${description || '<span class="suggestion-card__empty">Description forthcoming.</span>'}</p>
        <footer class="suggestion-card__footer">
          <button class="btn btn-sm btn-outline" data-add-metric="${metric.id}" data-label="${escapeAttr(label)}">Add KPI</button>
          <a class="suggestion-card__link" href="${playbookUrl}" target="_blank" rel="noopener">Explore in Playbook</a>
        </footer>
      </article>
    `;
  }

  function renderSuggestionSection(targetEl, items, options){
    if(!targetEl || !Array.isArray(items)) return;
    const kind = options.kind;
    const title = options.title || 'Suggestions';
    const meta = options.meta || '';
    const batchLabel = options.batchLabel || '';
    const batchLimit = options.batchLimit;
    const renderItem = options.renderItem || (()=>'');
    const countText = `${items.length} ${items.length === 1 ? 'option' : 'options'}`;
    targetEl.innerHTML = `
      <section class="suggestion-section" data-kind="${kind}">
        <div class="suggestion-section__header">
          <div>
            <h4>${title}</h4>
            <div class="meta">${meta ? `${meta} • ` : ''}${countText}</div>
          </div>
          ${batchLabel ? `<div class="suggestion-section__controls"><button class="btn btn-sm btn-outline" data-add-batch data-kind="${kind}" ${batchLimit?`data-limit="${batchLimit}"`:''}>${batchLabel}</button></div>` : ''}
        </div>
        <div class="suggestion-grid">
          ${items.map(renderItem).join('')}
        </div>
      </section>
    `;
    const grid = targetEl.querySelector('.suggestion-grid');
    if(kind === 'metric'){
      bindSuggestionBatchControls(targetEl, true);
    } else {
      bindSuggestionActions(grid);
      bindSuggestionBatchControls(targetEl, false);
    }
  }

  function bindSuggestionBatchControls(sectionEl, isMetric){
    if(!sectionEl || sectionEl.dataset.batchBound === '1') return;
    sectionEl.addEventListener('click', async (e)=>{
      const btn = e.target.closest('[data-add-batch]');
      if(!btn) return;
      const kind = btn.getAttribute('data-kind') || (isMetric ? 'metric' : 'driver');
      const limit = parseInt(btn.getAttribute('data-limit'), 10);
      const grid = sectionEl.querySelector('.suggestion-grid');
      if(!grid) return;
      const original = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Adding…';
      try{
        let buttons = [];
        if(isMetric){
          buttons = Array.from(grid.querySelectorAll('[data-add-metric]')).filter(b=>!b.disabled);
        } else {
          buttons = Array.from(grid.querySelectorAll(`[data-suggest-add][data-kind="${kind}"]`)).filter(b=>!b.disabled);
        }
        if(!buttons.length) return;
        const subset = Number.isFinite(limit) && limit > 0 ? buttons.slice(0, limit) : buttons;
        for(const b of subset){
          if(isMetric){
            await handleMetricAdd(b);
          } else {
            const label = b.getAttribute('data-label') || 'Item';
            const id = parseInt(b.getAttribute('data-id'), 10);
            b.disabled = true;
            b.textContent = 'Adding…';
            await addToPlan(kind, label, id, {}, b);
          }
        }
        btn.textContent = 'Added to plan';
        btn.classList.add('btn-success');
        setTimeout(()=>{
          btn.textContent = original;
          btn.disabled = false;
          btn.classList.remove('btn-success');
        }, 2400);
      }catch(err){
        console.warn(err);
        btn.textContent = original;
        btn.disabled = false;
      }
    });
    sectionEl.dataset.batchBound = '1';
  }

  function bindSuggestionActions(container){
    container.addEventListener('click', async (e)=>{
      const btn = e.target.closest('[data-suggest-add]');
      if(!btn) return;
      const kind = (btn.getAttribute('data-kind')||'driver').toLowerCase();
      const id = parseInt(btn.getAttribute('data-id'), 10);
      const label = btn.getAttribute('data-label')||'Item';
      btn.disabled = true; btn.textContent = 'Adding…';
      await addToPlan(kind, label, id, {}, btn);
      // Update review panel
      renderOutcomeReview();
    }, { once: false });
  }

  async function onOutcomeMetricsClick(e){
    const btn = e.target.closest('[data-add-metric]');
    if(!btn) return;
    e.preventDefault();
    await handleMetricAdd(btn);
  }

  async function handleMetricAdd(btn){
    if(!btn || btn.dataset.adding === '1') return;
    const id = btn.getAttribute('data-add-metric');
    if(!id) return;
    const card = btn.closest('.suggestion-card');
    const label = btn.getAttribute('data-label') || card?.dataset?.label || `Metric #${id}`;
    const original = btn.textContent;
    btn.dataset.adding = '1';
    btn.disabled = true;
    btn.textContent = 'Adding…';
    try{
      await fetch('/api/context/metrics/select', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ metric_id: id, source: 'plan_builder_outcome' }) });
      await addToPlan('metric', label, parseInt(id, 10), { source: 'outcome_metrics' }, btn);
      if(window.notify) window.notify('success','Metric added');
      renderOutcomeReview();
      refreshSidebar();
    }catch(err){
      console.warn(err);
      btn.disabled = false;
      btn.textContent = original;
    } finally {
      delete btn.dataset.adding;
    }
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

  async function fetchJSON(url, opts){
    const res = await fetch(url, Object.assign({ headers: { 'Accept':'application/json' } }, opts||{}));
    if(!res.ok) throw new Error(`Request failed (${res.status})`);
    return await res.json();
  }

  function updateInitialChoiceUI(){
    if(!els.initialChoice) return;
    // Always show the initial choice selectors at the top
    els.initialChoice.style.display = 'block';
    // Defaults; then lock the other path after a selection is made
    const hasMode = !!state.startMode;
    const lockFramework = hasMode && state.startMode === 'outcome';
    const lockOutcome = hasMode && state.startMode === 'framework';
    if(els.choiceFramework){
      els.choiceFramework.disabled = lockFramework ? true : false;
      if(els.choiceFramework.parentElement){ els.choiceFramework.parentElement.style.opacity = lockFramework ? '0.5' : '1'; }
    }
    if(els.choiceOutcome){
      els.choiceOutcome.disabled = lockOutcome ? true : false;
      if(els.choiceOutcome.parentElement){ els.choiceOutcome.parentElement.style.opacity = lockOutcome ? '0.5' : '1'; }
    }
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
    // Toggle outcome panels visibility
    if(els.outcomePanels){ els.outcomePanels.style.display = (state.startMode === 'outcome' && state.outcomeId) ? 'block' : 'none'; }
  }

  function resetStartSelection(options={}){
    state.startMode = null;
    state.frameworkId = null;
    state.outcomeId = null;
    state.competencyId = null;
    state.q = '';
    state.page = 1;
    if(els.choiceFramework && options.keepFramework !== true){
      els.choiceFramework.value = '';
    }
    if(els.choiceOutcome && options.keepOutcome !== true){
      els.choiceOutcome.value = '';
    }
    if(els.search){ els.search.value = ''; }
    if(els.stepCompetencies){ els.stepCompetencies.style.display = 'none'; }
    if(els.competencyList){ els.competencyList.innerHTML = ''; }
    if(els.searchRow){ els.searchRow.style.display = 'none'; }
    if(els.outcomePanels){ els.outcomePanels.style.display = 'none'; }
    if(els.grid){ els.grid.innerHTML = ''; }
    updateInitialChoiceUI();
    refreshSidebar();
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
        if(els.btnExportSummary){ els.btnExportSummary.disabled = true; }
        // Clear CTA states
        $all('#pb-grid [data-action="add"]').forEach(b=>{ b.disabled=false; b.textContent='Add to Plan'; });
        return; }
      if(els.btnGenerate){ els.btnGenerate.disabled = false; }
      if(els.btnExportSummary){ els.btnExportSummary.disabled = false; }
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
      if(!val){
        resetStartSelection({ keepOutcome: true });
        return;
      }
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
    if(els.choiceOutcome){ els.choiceOutcome.addEventListener('change', async ()=>{
      const val = els.choiceOutcome.value;
      if(!val){
        resetStartSelection({ keepFramework: true });
        return;
      }
      state.startMode = 'outcome';
      state.outcomeId = parseInt(val,10);
      state.frameworkId = null; state.competencyId = null; state.q = ''; state.page=1;
      updateInitialChoiceUI();
      if(els.stepCompetencies) els.stepCompetencies.style.display = 'none';
      // Clear any active competency pills (visual state) from previous framework flow
      $all('.pb-competency').forEach(el => el.classList.remove('is-active'));
      if(els.competencyList) els.competencyList.innerHTML = '';
      if(els.searchRow) els.searchRow.style.display = 'block';
      // Persist outcome context (fire-and-forget)
      try{ await fetch('/api/context/framework/state', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ outcome_id: state.outcomeId }) }); }catch{}
      // Show outcome panels and load their content
      if(els.outcomePanels){ els.outcomePanels.style.display = 'block'; }
      loadOutcomePanels();
      // Also load grid filtered by outcome for discovery
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
    if(els.btnGenerate){ els.btnGenerate.addEventListener('click', async ()=>{
      try{
        setStatus('', '');
        const title = prompt('Name your plan report', 'Development Plan');
        if(title === null) return;
        const trimmed = (title || '').trim();
        if(!trimmed){ setStatus('warning','Report title is required.'); return; }
        const payload = await buildReportPayload(trimmed);
        if(!payload.selected_metrics.length && !payload.selected_outcomes.length && !payload.selected_concepts.length){
          setStatus('warning','Add at least one item to the plan before generating a report.');
          return;
        }
        setStatus('', 'Starting report…');
        const res = await fetch('/api/dynamic-reports', {
          method:'POST',
          headers:{ 'Content-Type':'application/json' },
          body: JSON.stringify(payload)
        });
        if(!res.ok){
          let msg = `Failed to start report (${res.status})`;
          try{ const err = await res.json(); if(err && err.error){ msg += `: ${err.error}`; if(err.missing_fields) msg += ` — missing ${err.missing_fields.join(', ')}`; } }
          catch{}
          throw new Error(msg);
        }
        let reportId = null;
        try{
          const j = await res.json();
          reportId = j && j.report && j.report.id != null ? j.report.id : null;
        }catch{}
        setStatus('success','Report requested. Redirecting to progress view…');
        if(reportId != null){
          window.location.assign(`/plan/report?report_id=${encodeURIComponent(reportId)}`);
        } else {
          window.location.assign('/plan/report');
        }
      }catch(err){
        setStatus('warning', err.message || 'Unable to generate report');
      }
    }); }

    if(els.btnExportSummary){
      els.btnExportSummary.addEventListener('click', ()=>{
        try{ document.dispatchEvent(new Event('plan:generateReport')); }catch(e){}
      });
    }

    if(els.btnStartNew){ els.btnStartNew.addEventListener('click', async ()=>{
      // Clear plan items
      try{
        // Prefer server-side clear-all endpoint
        try{
          await fetch('/api/context/plan/items', { method:'DELETE', headers:{'Accept':'application/json'} });
        }catch{}

        // Fallback: delete items individually if the clear endpoint is unavailable
        const res = await fetch('/api/context/plan/items', { headers:{'Accept':'application/json'} });
        const data = await res.json();
        const items = Array.isArray(data.items) ? data.items : [];
        for(const it of items){
          try{ await fetch(`/api/context/plan/items/${it.id}`, { method:'DELETE' }); }catch{}
        }
      }catch{}

      // Clear any client-side mini selections cache
      try{ sessionStorage.removeItem('plan:selections'); }catch{}
      // Reset framework context
      try{ await fetch('/api/context/framework/state', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ framework_id: null, active_competencies: [] }) }); }catch{}
      // Reset UI state
      state.q=''; state.frameworkId=null; state.outcomeId=null; state.competencyId=null; state.startMode=null; state.page=1;
      if(els.search) els.search.value='';
      if(els.stepCompetencies){ els.stepCompetencies.style.display='none'; if(els.competencyList) els.competencyList.innerHTML=''; }
      if(els.initialChoice) els.initialChoice.style.display='block';
      // Re-enable both starting path selectors
      updateInitialChoiceUI();
      await refreshSidebar();
      els.grid.innerHTML = '';
      if(els.outcomePanels) els.outcomePanels.style.display='none';
    }); }
    // Role Profile controls removed; no role gap or proficiency handlers
  }

  async function init(){
    els.grid = $('#pb-grid');
    els.status = $('#pb-status');
    els.pagination = $('#pb-pagination');
    els.sidebar = document.querySelector('.pb-sidebar');
    els.sidebarContent = $('#pb-sidebar-content');
    els.selectionCount = $('#pb-selection-count');
    els.btnGenerate = $('#pb-generate-report');
    els.btnExportSummary = $('#pb-export-summary');
    els.search = $('#pb-search');
    els.initialChoice = $('#pb-initial-choice');
    els.choiceFramework = $('#pb-choice-framework');
    els.choiceOutcome = $('#pb-choice-outcome');
    els.stepCompetencies = $('#pb-step-competencies');
    els.competencyList = $('#pb-competency-list');
    els.searchRow = $('#pb-search-row');
    els.btnStartNew = $('#pb-start-new');
    // Outcome panels
    els.outcomePanels = $('#pb-outcome-panels');
    els.outcomeOverview = $('#pb-outcome-overview');
    els.outcomeDrivers = $('#pb-outcome-drivers');
    els.outcomeNudges = $('#pb-outcome-nudges');
    els.outcomeMetrics = $('#pb-outcome-metrics');
    els.outcomeReview = $('#pb-outcome-review');

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

    // If outcome was preselected via session or deep link, refresh panels
    if(state.startMode === 'outcome' && state.outcomeId){
      loadOutcomePanels();
    }

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
            section.push('<div class="cta-group" style="margin-top:12px;"><button id="pb-export-pdf" class="btn btn-primary">Download Selection Summary (PDF)</button></div>');
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
                try{
                  const j = await r.json();
                  if(j && j.error) msg += `: ${j.error}`;
                  if(j && j.details) msg += ` (${j.details})`;
                }catch{}
                throw new Error(msg);
              }
              const blob = await r.blob();
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              let fname = 'LD_Metrics_Summary.pdf';
              try{
                const cd = r.headers.get('content-disposition') || '';
                const m = cd.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
                fname = decodeURIComponent((m && (m[1] || m[2])) || fname);
              }catch{}
              a.download = fname;
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
