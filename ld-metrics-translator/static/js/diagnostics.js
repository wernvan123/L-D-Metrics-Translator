(function(){
  function $(sel){ return document.querySelector(sel); }
  function $all(sel){ return Array.from(document.querySelectorAll(sel)); }

  // ----------------------------
  // Sub-tab switching
  // ----------------------------
  function initTabs(){
    const tabs = $all('.subnav-tab');
    const panels = $all('.diag-panel');
    if(!tabs.length || !panels.length) return;

    const showPanel = (id, pushState=true) => {
      panels.forEach(p => {
        const isTarget = p.id === id;
        if(isTarget){
          p.removeAttribute('hidden');
          // allow layout to apply before adding active for transition
          requestAnimationFrame(() => p.classList.add('active'));
        } else {
          p.classList.remove('active');
          p.setAttribute('hidden', '');
        }
      });
      // persist selection in URL hash and sessionStorage
      if(pushState){
        try{ sessionStorage.setItem('diagnostics_tab', id); }catch{}
        const url = new URL(window.location.href);
        url.searchParams.set('tab', id === 'diag-bsd' ? 'bsd' : 'ai');
        history.replaceState(null, '', url);
      }
    };

    tabs.forEach(tab => tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.toggle('active', t === tab));
      const panelId = tab.getAttribute('data-panel');
      if(panelId) showPanel(panelId);
    }));
    // Determine initial tab from URL or session
    const urlTab = new URL(window.location.href).searchParams.get('tab');
    const savedTab = (() => { try{ return sessionStorage.getItem('diagnostics_tab'); }catch{return null;} })();
    let initial = null;
    if(urlTab === 'bsd') initial = 'diag-bsd';
    else if(urlTab === 'ai') initial = 'diag-ai';
    else if(savedTab) initial = savedTab;

    if(initial && panels.some(p => p.id === initial)){
      const t = tabs.find(tb => tb.getAttribute('data-panel') === initial);
      if(t){ tabs.forEach(x => x.classList.toggle('active', x === t)); }
      showPanel(initial, false);
    }else{
      // ensure default active panel animates in
      const defaultActive = document.querySelector('.subnav-tab.active');
      if(defaultActive){ const panelId = defaultActive.getAttribute('data-panel'); if(panelId) showPanel(panelId, false); }
    }
  }

  async function addToPlan(kind, label, sourceId, meta){
    try{
      const res = await fetch('/api/context/plan/items', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind, label, source_id: sourceId, meta, source_page: 'diagnostics' })
      });
      if(!res.ok) throw new Error('Failed to add to plan');
      if(window.notify){ window.notify('success', `Added to plan: ${label}`); }
    }catch(err){ alert(err.message || 'Failed to add to plan'); }
  }

  // ----------------------------
  // Behavioral Science Diagnostic (free-text analyzer)
  // ----------------------------
  const BIAS_MAP = {
    // key -> { terms: [query terms/keywords], title, description, recs: [actions], related: [keys] }
    'status-quo': { terms: ['status quo','stick with','business as usual','as usual','keep doing','resistance to change'], title: 'Status Quo Bias', description: 'Preference for existing practices, even when suboptimal.', recs: ['Surface switching costs explicitly','Run small safe-to-try experiments','Time-box a trial period with success criteria'], related: ['bandwagon','authority'] },
    'authority': { terms: ['authority','executive said','boss said','senior leader','because manager','leadership insisted'], title: 'Authority Bias', description: 'Overweighting opinions from authority figures.', recs: ['Invite dissenting views first (pre-mortem)','Use anonymous voting before discussion','Ask for evidence rather than rank-based claims'], related: ['bandwagon','framing'] },
    'bandwagon': { terms: ['bandwagon','everyone thinks','popular','consensus','most people'], title: 'Bandwagon Effect', description: 'Adopting beliefs because many others hold them.', recs: ['Seek counter-examples and base rates','Split group to argue alternatives','Use written rationale before group talk'], related: ['status-quo','authority'] },
    'time-pressure': { terms: ['time pressure','tight deadline','urgent','rush','last minute','pressure'], title: 'Pressure Heuristic', description: 'Rushed decisions under time or stress constraints.', recs: ['Pause with a 10-minute cooling-off','Define a minimum viable decision','Clarify reversible vs irreversible decisions'], related: ['limited-info','framing'] },
    'limited-info': { terms: ['limited information','incomplete data','don\'t have data','lack of data','gut feel','intuition only'], title: 'Availability Heuristic', description: 'Judging by information that comes easily to mind.', recs: ['Collect a small but representative sample','Use a decision checklist','Seek an external benchmark'], related: ['framing','bandwagon'] },
    'framing': { terms: ['framing','framed as','presented as','loss vs gain','wording changed'], title: 'Framing Effect', description: 'Choices influenced by how options are presented.', recs: ['Reframe options in neutral language','Show both loss and gain perspectives','Compare equal baselines and units'], related: ['authority','limited-info'] }
  };

  function uniqueById(arr){
    const seen = new Set();
    const out = [];
    arr.forEach(x => { const id = x && x.id; if(id != null && !seen.has(id)){ seen.add(id); out.push(x); }});
    return out;
  }

  async function fetchBiasCardsForTerms(terms){
    // Query API for each term and merge results
    const results = [];
    for(const term of terms){
      try{
        const url = `/api/driver-cards?kind=bias&q=${encodeURIComponent(term)}&page_size=12`;
        const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
        if(!res.ok) continue;
        const data = await res.json();
        if(Array.isArray(data.items)) results.push(...data.items);
      }catch(e){ /* swallow and continue */ }
    }
    return uniqueById(results);
  }

  function renderCards(container, cards){
    container.innerHTML = '';
    if(!cards.length){
      const div = document.createElement('div');
      div.className = 'no-data-message';
      div.innerHTML = `<div class="no-data-icon">🧠</div><h3>No bias cards found</h3><p>Try adjusting selections or use the AI Event Analysis tab.</p>`;
      container.appendChild(div);
      return;
    }
    const frag = document.createDocumentFragment();
    for(const card of cards){
      const el = document.createElement('div');
      el.className = 'metric-card';
      el.setAttribute('data-id', card.id ?? '');
      el.innerHTML = `
        <div class="metric-header">
          <h3 class="metric-title">${escapeHtml(card.name || 'Bias')}</h3>
          <div class="metric-badges">
            <span class="badge badge-kind">Bias</span>
            ${card.outcome?.name ? `<span class="badge badge-outcome">${escapeHtml(card.outcome.name)}</span>` : ''}
            ${card.metric_type?.name ? `<span class="badge badge-type">${escapeHtml(card.metric_type.name)}</span>` : ''}
          </div>
        </div>
        <div class="metric-content">
          <p class="metric-description">${escapeHtml(card.description || '')}</p>
        </div>
        <div class="metric-actions">
          <button class="btn btn-sm btn-secondary" data-action="add-plan" data-kind="bias" data-label="${escapeHtml(card.name||'Bias')}">Add to Plan</button>
          <a class="btn btn-sm btn-primary" href="/playbook?kind=bias&q=${encodeURIComponent(card.name||'')}&filter=${encodeURIComponent('kind:bias;name:'+(card.name||''))}">Explore Nudges</a>
        </div>
      `;
      frag.appendChild(el);
    }
    container.appendChild(frag);

    // Delegated click for Add to Plan
    container.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-action="add-plan"]');
      if(!btn) return;
      const kind = (btn.getAttribute('data-kind')||'bias').toLowerCase();
      const label = btn.getAttribute('data-label') || 'Bias';
      addToPlan(kind, label, null, { source: 'bsd' });
    }, { once: true });
  }

  function escapeHtml(s){ return (s||'').replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }

  function initBSD(){
    const btn = $('#bsd-analyze');
    const output = $('#bsd-output');
    const textarea = $('#bsd-text');
    if(!btn || !output || !textarea) return;

    // Restore persisted text
    try{
      const saved = sessionStorage.getItem('bsd_text');
      if(saved) textarea.value = saved;
    }catch{}
    textarea.addEventListener('input', () => {
      try{ sessionStorage.setItem('bsd_text', textarea.value); }catch{}
    });

    function analyze(text){
      const t = (text || '').toLowerCase();
      // Find matching bias keys by keyword presence
      const found = [];
      Object.entries(BIAS_MAP).forEach(([key, meta]) => {
        if(meta.terms.some(term => t.includes(term))){ found.push({ key, ...meta }); }
      });
      // Prepare related suggestions (not already found)
      const foundKeys = new Set(found.map(f => f.key));
      const alsoConsider = [];
      found.forEach(f => (f.related||[]).forEach(r => { if(!foundKeys.has(r) && !alsoConsider.includes(r)) alsoConsider.push(r); }));

      return { found, alsoConsider };
    }

    function playbookLink(name){
      const q = encodeURIComponent(name);
      const filter = encodeURIComponent(`kind:bias;name:${name}`);
      return `/playbook?kind=bias&q=${q}&filter=${filter}`;
    }

    function render(text, result){
      const intro = `You described: “${escapeHtml(text.trim())}”. The context suggests potential cognitive patterns to consider:`;
      const idList = result.found.map(b => {
        const icon = b.key === 'authority' ? '🧑‍💼' : b.key === 'bandwagon' ? '👥' : b.key === 'status-quo' ? '🧱' : b.key === 'time-pressure' ? '⏱️' : b.key === 'limited-info' ? '📉' : b.key === 'framing' ? '🖼️' : '🧠';
        return `
        <li class="bias-card bias-${escapeHtml(b.key)}">
          <div class="bias-card-header">
            <span class="bias-icon">${icon}</span>
            <div class="bias-title">${escapeHtml(b.title)}</div>
          </div>
          <p class="bias-desc">${escapeHtml(b.description)}</p>
          <div class="bias-actions">
            <button class="btn btn-sm btn-secondary" data-action="add-plan" data-kind="bias" data-label="${escapeHtml(b.title)}">Copy to Plan</button>
            <a class="btn btn-sm btn-primary" href="${playbookLink(b.title)}">Open Bias Card</a>
          </div>
          ${b.recs?.length ? `<div class="bias-recs"><div class="recs-title">Counter-bias recommendations</div><ul class="list-disc"><li>${b.recs.map(escapeHtml).join('</li><li>')}</li></ul></div>` : ''}
        </li>`;
      }).join('');

      const also = result.alsoConsider.map(k => {
        const m = BIAS_MAP[k];
        return m ? `<a href="${playbookLink(m.title)}" class="badge">${escapeHtml(m.title)}</a>` : '';
      }).join(' ');

      output.innerHTML = `
        <div class="analysis-card">
          <h4>Introduction</h4>
          <p>${intro}</p>
        </div>
        <div class="analysis-card">
          <h4>Identified Biases, Heuristics, and Fallacies</h4>
          ${result.found.length ? `<ol class="analysis-list">${idList}</ol>` : '<p>No specific biases detected from keywords; consider trying the AI Event Analysis tab for a deeper read.</p>'}
        </div>
        <div class="analysis-card">
          <h4>Other Biases to Watch</h4>
          ${also || '<p>None suggested.</p>'}
        </div>
      `;
      output.style.display = 'block';
    }

    btn.addEventListener('click', async () => {
      const text = textarea.value.trim();
      if(!text){ textarea.focus(); return; }
      const res = analyze(text);
      render(text, res);
    });

    // Inline login prompt dismiss
    const loginPrompt = $('#login-prompt');
    const dismiss = $('#login-dismiss');
    if(loginPrompt && dismiss){
      dismiss.addEventListener('click', () => {
        loginPrompt.style.display = 'none';
        try{ sessionStorage.setItem('login_prompt_dismissed', '1'); }catch{}
      });
      try{ if(sessionStorage.getItem('login_prompt_dismissed') === '1'){ loginPrompt.style.display = 'none'; } }catch{}
    }

    // Delegated handler for Copy to Plan actions inside BSD output
    output.addEventListener('click', (e) => {
      const el = e.target.closest('button[data-action="add-plan"]');
      if(!el) return;
      const kind = (el.getAttribute('data-kind')||'bias').toLowerCase();
      const label = el.getAttribute('data-label')||'Bias';
      addToPlan(kind, label, null, { source: 'bsd-free-text' });
    });
  }

  function init(){
    initTabs();
    initBSD();
    initDriverCardDemo();
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
  // ----------------------------
  // Driver Card Demo minimal wiring (button + select)
  // ----------------------------
  async function fetchDriverCardCard(id){
    try{
      const r = await fetch(`/api/metric-cards/${id}`);
      if(!r.ok) throw new Error('primary-endpoint-failed');
      const d = await r.json();
      return d.metric_card || d.metric || d;
    }catch(e){
      try{
        const r2 = await fetch(`/api/driver-cards/${id}`);
        if(!r2.ok) throw new Error('fallback-endpoint-failed');
        const d2 = await r2.json();
        return d2.driver_card || d2;
      }catch(e2){
        return null;
      }
    }
  }

  function renderSimpleDriverCard(card){
    const root = document.getElementById('driver-card-demo');
    if(!root) return;
    root.innerHTML = '';
    if(!card){
      const div = document.createElement('div');
      div.className = 'no-data-message';
      div.innerHTML = '<div class="no-data-icon">⚠️</div><h3>Unable to load card</h3>';
      root.appendChild(div);
      return;
    }
    const box = document.createElement('div');
    box.className = 'driver-card';
    box.innerHTML = `
      <div class="dc-header">
        <div class="dc-title">${(card.title || card.name || '').toString()}</div>
        <div class="dc-badge">${((card.identifier_type || card.kind || 'CONCEPT')).toString().toUpperCase()}</div>
      </div>
      ${card.description ? `<p class="dc-desc">${card.description}</p>` : ''}
    `;
    root.appendChild(box);
  }

  function initDriverCardDemo(){
    const btn = document.getElementById('driver-card-load');
    const sel = document.getElementById('driver-card-id');
    const panelBtn = document.querySelector('.subnav-tab[data-panel="diag-driver-card"]');
    if(!sel) return;
    async function load(){
      const id = parseInt(sel.value, 10);
      if(!id) return;
      const card = await fetchDriverCardCard(id);
      renderSimpleDriverCard(card);
    }
    if(btn) btn.addEventListener('click', load);
    sel.addEventListener('change', load);
    if(panelBtn){ panelBtn.addEventListener('click', () => setTimeout(load, 0)); }
  }
})();
