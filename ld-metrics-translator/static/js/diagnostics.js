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

  // Store the last AI analysis without intercepting fetch (frontend listens for custom events instead)
  function cacheLastAnalysis(payload){
    if(!payload || typeof payload !== 'object') return;
    if(payload.analysis){
      GAP_lastAnalysis = payload.analysis;
      const ta = document.getElementById('event-description');
      GAP_lastInput = ta ? ta.value : (GAP_lastInput || '');
    }
  }
  function syncPlanButtonsState(root){
    const scope = root || document;
    const btns = scope.querySelectorAll('button[data-action="add-plan"]');
    for(const btn of btns){
      const kind = (btn.getAttribute('data-kind')||'').toLowerCase();
      const label = btn.getAttribute('data-label')||'';
      togglePlanButtonState(btn, hasSelection(kind,label));
    }
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

  // ----------------------------
  // Role Profile targets framing (callouts on diagnostics)
  // ----------------------------
  async function fetchJSON(url){ const r = await fetch(url, { headers: { 'Accept':'application/json' } }); if(!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }
  function esc(s){ return (s||'').toString().replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c])); }
  const PROFICIENCY_NAMES = { 1: 'Foundational', 2: 'Basic', 3: 'Proficient', 4: 'Advanced', 5: 'Expert' };
  function proficiencyName(level){ const n = Number(level); return PROFICIENCY_NAMES[n] || String(level); }
  // Gap report state
  let GAP_selectedRole = null; // { id, name, department }
  let GAP_roleTargets = [];    // [ { competency_name, target_level, ... } ]
  let GAP_lastAnalysis = null; // { learning_needs, recommended_metrics, interventions, success_measures }
  let GAP_lastInput = '';

  // ----------------------------
  // Plan selections (session-scoped)
  // ----------------------------
  const PLAN_SS_KEY = 'plan:selections';
  const PLAN_SHOW_KEY = 'plan:showMini';
  function planKey(kind,label){ return `${(kind||'').toLowerCase()}:${(label||'').toLowerCase()}`; }
  function getSelections(){
    try{ const raw = sessionStorage.getItem(PLAN_SS_KEY); return raw? JSON.parse(raw): []; }catch{ return []; }
  }
  function setSelections(items){ try{ sessionStorage.setItem(PLAN_SS_KEY, JSON.stringify(items||[])); }catch{} }
  function hasSelection(kind,label){ const k = planKey(kind,label); return getSelections().some(it => it.key === k); }
  function addSelection(kind,label,meta){
    const items = getSelections();
    const k = planKey(kind,label);
    if(items.some(it=>it.key===k)) return items;
    const rec = { key:k, kind, label, meta: meta||{}, ts: Date.now() };
    items.push(rec); setSelections(items);
    try{ sessionStorage.setItem(PLAN_SHOW_KEY,'1'); }catch{}
    return items;
  }
  function removeSelection(kind,label){ const k = planKey(kind,label); const items = getSelections().filter(it=>it.key!==k); setSelections(items); return items; }
  function renderPlanMiniSidebar(){
    const list = document.getElementById('plan-mini-list');
    const card = document.getElementById('plan-mini-sidebar');
    if(!list || !card) return;
    const items = getSelections();
    list.innerHTML = items.map(it => `
      <div class="mini-item" data-key="${esc(it.key)}">
        <div>
          <span class="mini-kind pill">${esc((it.kind||'').toUpperCase())}</span>
          <span class="mini-label">${esc(it.label)}</span>
        </div>
        <div class="mini-actions">
          <button class="btn btn-sm btn-outline-danger" data-action="mini-remove" data-key="${esc(it.key)}">×</button>
        </div>
      </div>
    `).join('');
    const showFlag = (()=>{ try{return sessionStorage.getItem(PLAN_SHOW_KEY)==='1';}catch{return false;} })();
    const visible = items.length > 0 && showFlag;
    card.style.display = visible ? 'block' : 'none';
    try{ document.body.setAttribute('data-plan-mini', visible ? '1' : '0'); }catch{}
  }
  function togglePlanButtonState(btn, added){
    if(!btn) return;
    if(added){
      btn.classList.remove('btn-primary');
      btn.classList.add('btn-success');
      btn.textContent = 'Remove from Plan';
      btn.setAttribute('aria-pressed','true');
    } else {
      btn.classList.remove('btn-success');
      btn.classList.add('btn-primary');
      btn.textContent = 'Add to Plan';
      btn.removeAttribute('aria-pressed');
    }
  }
  async function refreshRoleTargets(){
    try{
      const box = document.getElementById('diag-role-targets');
      if(!box) return;
      const sel = await fetchJSON('/api/roles/select');
      const rid = sel.selected_role_profile_id;
      if(!rid){
        box.style.display='none'; box.innerHTML='';
        // Clear role context and hide the gap report when no role is selected
        GAP_selectedRole = null; GAP_roleTargets = [];
        const card = document.getElementById('gap-report-card');
        if(card) card.style.display = 'none';
        return;
      }
      // Fetch role details and targets
      try {
        const roleRes = await fetchJSON(`/api/roles/${rid}`);
        GAP_selectedRole = roleRes.role || roleRes || { id: rid };
      } catch { GAP_selectedRole = { id: rid }; }
      const data = await fetchJSON(`/api/roles/${rid}/targets`);
      const tgts = Array.isArray(data.targets) ? data.targets : [];
      GAP_roleTargets = tgts;
      if(!tgts.length){ box.style.display='none'; box.innerHTML=''; return; }
      const lines = tgts.slice(0,6).map(t => {
        const cname = esc(t.competency?.name || t.competency_name || ('#'+t.competency_id));
        const lvl = t.target_level;
        return `• ${cname}: Target ${lvl} (${proficiencyName(lvl)})`;
      });
      const more = tgts.length>6 ? ` +${tgts.length-6} more` : '';
      box.innerHTML = `<strong>Role Targets</strong><br>${lines.join('<br>')}${more}`;
      box.style.display='block';
      // Also re-render the gap report with latest role context
      renderGapReport();
    }catch(e){ const box = document.getElementById('diag-role-targets'); if(box){ box.style.display='none'; } }
  }
  function initRoleTargetsFraming(){
    const sel = document.getElementById('diag-role-select');
    if(sel){ sel.addEventListener('change', () => setTimeout(refreshRoleTargets, 50)); }
    // initial load
    refreshRoleTargets();
    // also refresh when other modules persist the role
    window.addEventListener('role:selected', () => setTimeout(refreshRoleTargets, 0));
  }

  // ----------------------------
  // Gap Analysis Report renderer
  // ----------------------------
  function renderGapReport(){
    const card = document.getElementById('gap-report-card');
    const headerEl = document.getElementById('gap-report-header');
    const diagEl = document.getElementById('gap-report-diagnosis');
    const causesEl = document.getElementById('gap-report-root-causes');
    const recsEl = document.getElementById('gap-report-recommendations');
    const footerEl = document.getElementById('gap-report-footer');
    if(!card || !headerEl || !diagEl || !causesEl || !recsEl || !footerEl) return;

    // Only show this report when a role is selected AND we have an analysis based on user input
    if(!GAP_selectedRole || !GAP_selectedRole.id){
      // Fallback: use the current selection from the dropdown if present
      const selEl = document.getElementById('diag-role-select');
      const val = selEl && selEl.value ? String(selEl.value).trim() : '';
      if(val){
        const num = parseInt(val, 10);
        GAP_selectedRole = { id: isNaN(num) ? val : num };
      }
    }
    if(!GAP_selectedRole || !GAP_selectedRole.id){
      card.style.display = 'none';
      try{ document.body.setAttribute('data-gap-active','0'); }catch{}
      return;
    }
    const hasAnalysis = !!(GAP_lastAnalysis && GAP_lastInput && String(GAP_lastInput).trim().length > 0);
    if(!hasAnalysis){
      card.style.display = 'none';
      try{ document.body.setAttribute('data-gap-active','0'); }catch{}
      return;
    }

    // Ensure visible once role context exists
    card.style.display = '';
    try{ document.body.setAttribute('data-gap-active','1'); }catch{}
    // Hide the default analysis block when gap report is active
    try{
      const results = document.getElementById('analysis-results');
      if(results) results.style.display = 'none';
    }catch{}

    const roleName = GAP_selectedRole?.name || null;
    const dateStr = new Date().toLocaleDateString();
    const hasAnalysis2 = true; // by this point, we've already validated hasAnalysis

    // Header & Context (compact, in a distinct card)
    headerEl.innerHTML = `
      <div class="section">
        <h3>Gap Analysis for ${roleName ? esc(roleName) : 'Selected Role'} (AI-Driven)</h3>
        <div class="context-card">
          <div class="meta">Assessment for ${esc('an individual in the role')} — ${dateStr}</div>
          <div><strong>Role Profile:</strong> ${roleName ? esc(roleName) : '—'}</div>
          <div class="meta" style="margin-top:6px;">Utilizing its defined KSAOs and target competencies as a benchmark. The AI compares the described performance against the role's ideal expectations.</div>
          ${GAP_lastInput ? `<div class="user-input"><em>Observed Event/Situation:</em> “${esc(GAP_lastInput)}”</div>` : ''}
        </div>
      </div>
    `;

    // Diagnosis (short, prioritized)
    const summary = `Based on the input${roleName? ` and the <strong>${esc(roleName)}</strong> requirements` : ''}, key gaps are highlighted below.`;
    diagEl.innerHTML = `
      <div class="section">
        <h4>The Diagnosis: Understanding the Performance Gap</h4>
        <p>${summary}</p>
        <h5>Identified Core Issues: Key Gaps${roleName? ` for ${esc(roleName)}`:''}</h5>
        <div class="issue-list">
          ${(GAP_roleTargets||[]).slice(0,2).map(t => {
            const cname = esc(t.competency?.name || t.competency_name || 'Competency');
            const tgt = Number(t.target_level);
            const current = null; // unknown estimate; could be filled by model later
            const ticks = [1,2,3,4,5].map(n => `<div class="tick" data-label="${n}">${[n===tgt?'<span class=\"marker target\"></span>':'', current===n?'<span class=\"marker current\"></span>':''].join('')}</div>`).join('');
            // Heuristic grouping: match KPI/Nudge names containing the competency name (case-insensitive)
            const lc = cname.toLowerCase();
            const kpis = (GAP_lastAnalysis?.recommended_metrics||[]).map(x=>typeof x==='string'?x:(x.name||x.metric||'KPI'));
            const nudges = (GAP_lastAnalysis?.interventions||[]).map(x=>typeof x==='string'?x:(x.name||x.description||'Intervention'));
            const relKpis = kpis.filter(k => String(k).toLowerCase().includes(lc)).slice(0,2);
            const relNudges = nudges.filter(n => String(n).toLowerCase().includes(lc)).slice(0,2);
            const fallbackKpis = relKpis.length ? relKpis : kpis.slice(0,1);
            const fallbackNudges = relNudges.length ? relNudges : nudges.slice(0,1);
            const kpiHtml = fallbackKpis.map(name => `<div class=\"kpi-item\"><h3 style=\"margin:0 0 4px\">📊 ${esc(name)}</h3><div class=\"meta\">Relevance: Measures improvement in ${cname}.</div><div style=\"margin-top:6px\"><a class=\"btn btn-sm btn-secondary\" href=\"/playbook?kind=kpi&q=${encodeURIComponent(name)}\">Open KPIs in Playbook</a><button class=\"btn btn-sm btn-primary\" data-action=\"add-plan\" data-kind=\"kpi\" data-label=\"${esc(name)}\" style=\"margin-left:8px\">Add to Plan</button></div></div>`).join('');
            const nudgeHtml = fallbackNudges.map(name => `<div class=\"nudge-item\"><h4 style=\"margin:0 0 4px\">💡 ${esc(name)}</h4><div class=\"meta\">Role Benefit: Supports ${cname} development.</div><div style=\"margin-top:6px\"><a class=\"btn btn-sm btn-secondary\" href=\"/playbook?kind=nudge&q=${encodeURIComponent(name)}\">Open in Playbook</a><button class=\"btn btn-sm btn-primary\" data-action=\"add-plan\" data-kind=\"nudge\" data-label=\"${esc(name)}\" style=\"margin-left:8px\">Add to Plan</button></div></div>`).join('');
            return `
              <div class="issue-card">
                <h3>🔎 ${cname}</h3>
                <div class="issue-body">
                  <div class="gap-scale">${ticks}</div>
                  <div class="gap-legend"><span class="dot target"></span> Target: ${tgt} (${proficiencyName(tgt)}) ${current? `<span style=\"margin-left:12px\" class=\"gap-current\"><span class=\"dot current\"></span> Estimated Current: ${current} (${proficiencyName(current)})</span>` : `<span style=\"margin-left:12px\" class=\"gap-current\"><span class=\"dot current\"></span> Estimated Current: —</span>`}
                  </div>
                  <div class=\"section\"><h5>Related KPIs</h5><div class=\"kpi-list\">${kpiHtml||'<div class=\"meta\">KPIs will appear after analysis.</div>'}</div></div>
                  <div class=\"section\"><h5>Related Interventions</h5><div class=\"nudge-list\">${nudgeHtml||'<div class=\"meta\">Interventions will appear after analysis.</div>'}</div></div>
                </div>
                <div class="issue-actions"><button class="btn btn-sm btn-secondary" data-action="open-playbook" data-label="${cname}">Open in Playbook</button><button class="btn btn-sm btn-primary" data-action="add-plan" data-kind="gap" data-label="${cname}" style="margin-left:8px">Add to Plan</button></div>
              </div>`;
          }).join('') || '<div class="meta">No role targets available. Select a role to contextualize.</div>'}
        </div>
      </div>
    `;

    // Root Causes (simple placeholders; can be enriched later)
    const biases = (GAP_lastAnalysis && Array.isArray(GAP_lastAnalysis.learning_needs)) ? GAP_lastAnalysis.learning_needs.slice(0,2) : [];
    causesEl.innerHTML = `
      <div class="section">
        <h4>Potential Root Causes (Behavioral Biases): Impact on Role Performance</h4>
        ${biases.length ? biases.map(b => `
          <div class="bias-card">
            <h4>🚫 ${esc(b)}</h4>
            <p><strong>Impact Summary:</strong> Directly impedes ${roleName? esc(roleName)+"'s" : 'the role\'s'} effective performance.</p>
            <p class="meta">This bias may hinder conflict resolution and timely performance feedback, leading to unresolved team issues.</p>
            <div><a class="btn btn-sm btn-primary" href="/playbook?kind=bias&q=${encodeURIComponent(b)}">Explore Nudges to Counteract Bias</a></div>
          </div>
        `).join('') : '<div class="meta">Bias drivers will appear after analysis.</div>'}
      </div>
    `;

    // Recommendations: KPIs and Nudges
    const kpis = (GAP_lastAnalysis && Array.isArray(GAP_lastAnalysis.recommended_metrics)) ? GAP_lastAnalysis.recommended_metrics.slice(0,5) : [];
    const nudges = (GAP_lastAnalysis && Array.isArray(GAP_lastAnalysis.interventions)) ? GAP_lastAnalysis.interventions.slice(0,5) : [];
    recsEl.innerHTML = `
      <div class="section">
        <h4>Key Performance Indicators (KPIs) for ${roleName ? esc(roleName)+"'s" : 'Role'} Growth</h4>
        <div class="kpi-list">${kpis.map(k => {
          const name = esc(typeof k==='string'?k:k.name||k.metric||'KPI');
          return `<div class=\"kpi-item\"><h3 style=\"margin:0 0 4px\">📊 ${name}</h3><div class=\"meta\">Relevance to Role: Helps measure improvement in identified gaps for ${roleName? esc(roleName) : 'this role'}.</div><div style=\"margin-top:6px\"><a class=\"btn btn-sm btn-secondary\" href=\"/playbook?kind=kpi&q=${encodeURIComponent(name)}\">Open KPIs in Playbook</a> <button class=\"btn btn-sm btn-primary\" data-action=\"add-plan\" data-kind=\"kpi\" data-label=\"${name}\">Add to Plan</button></div></div>`;
        }).join('') || '<div class="meta">KPIs will appear after analysis.</div>'}</div>
      </div>
      <div class="section">
        <h4>Actionable Interventions & Nudges: Supporting ${roleName ? esc(roleName)+"'s" : 'Role'} Development</h4>
        <div class="nudge-list">${nudges.map(n => {
          const name = esc(typeof n==='string'?n:n.name||n.description||'Intervention');
          return `<div class=\"nudge-item\"><h4 style=\"margin:0 0 4px\">💡 ${name}</h4><div class=\"meta\">Role Benefit: Supports development of competencies tied to the identified gaps.</div><div style=\"margin-top:6px\"><a class=\"btn btn-sm btn-secondary\" href=\"/playbook?kind=nudge&q=${encodeURIComponent(name)}\">Open in Playbook</a> <button class=\"btn btn-sm btn-primary\" data-action=\"add-plan\" data-kind=\"nudge\" data-label=\"${name}\">Add to Plan</button></div></div>`;
        }).join('') || '<div class="meta">Interventions will appear after analysis.</div>'}</div>
      </div>
    `;

    // Footer
    const source = document.querySelector('.analysis-source')?.textContent || '';
    footerEl.innerHTML = `
      <div class="meta">Status: Ready.</div>
      <div class="mt"><a class="btn btn-primary" href="/plan-builder">Review & Finalize Plan</a>
      <span class="meta" style="margin-left:.5rem;">${source || 'GENERATED BY: AI-ASSISTED ANALYSIS'}</span></div>
    `;
    // After rendering, sync button states and mini sidebar
    try { syncPlanButtonsState(card); } catch {}
    try { renderPlanMiniSidebar(); } catch {}
  }

  async function addToPlan(kind, label, sourceId, meta){
    // Toggle local selection state first for immediate UX
    const exists = hasSelection(kind,label);
    if(exists){
      removeSelection(kind,label);
      renderPlanMiniSidebar();
      return { success:true, removed:true };
    }
    addSelection(kind,label,meta);
    renderPlanMiniSidebar();
    // Best-effort: inform backend of add
    try{
      const res = await fetch('/api/context/plan/items', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind, label, source_id: sourceId, meta, source_page: 'diagnostics' })
      });
      // Non-blocking: backend failures should not block UX toggle
      if(!res.ok && window.console) console.warn('Plan add (server) failed', await res.text());
    }catch(_){ /* ignore */ }
    return { success:true, added:true };
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

    function render(text, result, kbItems){
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

      const kbSection = Array.isArray(kbItems) && kbItems.length ? `
        <div class="analysis-card">
          <h4>Knowledge Base Biases</h4>
          <ul class="analysis-list">
            ${kbItems.map(item => `
              <li class="bias-card">
                <div class="bias-card-header">
                  <div class="bias-title">${escapeHtml(item.heading || 'Bias Insight')}</div>
                </div>
                <p class="bias-desc">${escapeHtml(item.content || '')}</p>
                ${Array.isArray(item.tags) && item.tags.length ? `<div class="bias-tags">${item.tags.map(tag => `<span class="badge">${escapeHtml(tag)}</span>`).join(' ')}</div>` : ''}
                <div class="bias-actions">
                  <button class="btn btn-sm btn-secondary" data-action="add-plan" data-kind="bias" data-label="${escapeHtml(item.heading || 'Bias Insight')}">Copy to Plan</button>
                </div>
              </li>
            `).join('')}
          </ul>
        </div>
      ` : '';

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
        ${kbSection}
      `;
      output.style.display = 'block';
    }

    btn.addEventListener('click', async () => {
      const text = textarea.value.trim();
      if(!text){ textarea.focus(); return; }
      const res = analyze(text);
      let kbItems = null;
      if(window.APP_FLAGS?.ENABLE_EVENT_KB === 'true'){
        const kb = await fetchBiasKnowledge(text);
        if(kb?.success) kbItems = kb.items;
      }
      render(text, res, kbItems);
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

    // Defensive: Continue as Guest wiring (in case EventAnalyzer didn't bind yet)
    const continueGuest = document.getElementById('continue-anonymous');
    const actionsRow = document.getElementById('analysis-actions');
    if (continueGuest) {
      continueGuest.addEventListener('click', (e) => {
        e.preventDefault();
        if (loginPrompt) loginPrompt.style.display = 'none';
        try { sessionStorage.setItem('guestMode', 'true'); } catch {}
        if (actionsRow) actionsRow.style.display = 'flex';
      });
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
    initRoleTargetsFraming();
    // EventAnalyzer is responsible for wiring Analyze button; no fallback handler to avoid duplicate submissions
  }

  // ----------------------------
  // Global delegated handlers for Add->Remove and Mini Sidebar
  // ----------------------------
  document.addEventListener('click', async (e) => {
    const addBtn = e.target.closest('button[data-action="add-plan"]');
    if(addBtn){
      e.preventDefault();
      const kind = (addBtn.getAttribute('data-kind')||'').toLowerCase();
      const label = addBtn.getAttribute('data-label')||'';
      const res = await addToPlan(kind, label, null, { source: 'diagnostics-gap-report' });
      togglePlanButtonState(addBtn, !res.removed);
      return;
    }
    const rm = e.target.closest('button[data-action="mini-remove"][data-key]');
    if(rm){
      e.preventDefault();
      const key = rm.getAttribute('data-key');
      // remove by key
      const items = getSelections().filter(it => it.key !== key);
      setSelections(items);
      renderPlanMiniSidebar();
      // sync buttons that correspond to this key
      const [kind,label] = key.split(':');
      const btns = document.querySelectorAll(`button[data-action="add-plan"][data-kind="${kind}"]`);
      for(const b of btns){ if((b.getAttribute('data-label')||'').toLowerCase() === label){ togglePlanButtonState(b, false); } }
      return;
    }
    const clr = e.target.closest('#plan-mini-clear');
    if(clr){
      e.preventDefault();
      setSelections([]);
      try{ sessionStorage.setItem(PLAN_SHOW_KEY,'0'); }catch{}
      renderPlanMiniSidebar();
      syncPlanButtonsState();
      return;
    }
  });

  // Initial hydrate of sidebar on load
  try { renderPlanMiniSidebar(); } catch {}

  // Ensure default state for gap-active on load and set up fetch interceptor
  try { document.body.setAttribute('data-gap-active','0'); } catch {}
  try { setupAnalyzeInterceptor(); } catch {}

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
