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

  const PROFICIENCY_NAMES = { 1: 'Foundational', 2: 'Basic', 3: 'Proficient', 4: 'Advanced', 5: 'Expert' };
  function proficiencyName(level){ const n = Number(level); return PROFICIENCY_NAMES[n] || String(level); }

  let GAP_selectedRole = null; // { id, name, department }
  let GAP_roleTargets = [];    // [ { competency_name, target_level, ... } ]
  let GAP_lastAnalysis = null; // enriched analysis object from event analyzer
  let GAP_lastInput = '';
  let GAP_lastAnalysisRoleId = null; // role id used for last analysis (to prevent stale/mismatched gap reports)

  try{
    window.DiagnosticsDebug = window.DiagnosticsDebug || {};
    window.DiagnosticsDebug.getSelectedRole = () => GAP_selectedRole;
    window.DiagnosticsDebug.getRoleTargets = () => GAP_roleTargets;
    window.DiagnosticsDebug.getLastAnalysis = () => GAP_lastAnalysis;
    window.DiagnosticsDebug.getLastInput = () => ({ event_description: GAP_lastInput });
    window.DiagnosticsDebug.getRoleTargetById = (id) => {
      const needle = (id == null) ? '' : String(id).trim().toLowerCase();
      if(!needle) return null;
      const items = GAP_roleTargets || [];
      for(const t of items){
        const tid = t && t.target_id ? String(t.target_id).trim().toLowerCase() : '';
        if(tid && tid === needle) return t;
      }
      return null;
    };
  }catch(e){}

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

  function escapeHtml(s){ return (s||'').replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }

  function esc(s){
    return escapeHtml(s == null ? '' : String(s));
  }

  function toText(value){
    if(value == null) return '';
    if(typeof value === 'string') return value;
    if(typeof value === 'number' || typeof value === 'boolean') return String(value);
    if(Array.isArray(value)) return value.map(toText).filter(Boolean).join('; ');
    if(typeof value === 'object'){
      if(typeof value.summary === 'string') return value.summary;
      if(typeof value.description === 'string') return value.description;
      if(typeof value.text === 'string') return value.text;
      try{ return JSON.stringify(value); }catch{ return String(value); }
    }
    return String(value);
  }

  function _normInputText(s){
    try{
      return String(s || '').replace(/\s+/g, ' ').trim();
    }catch{ return ''; }
  }

  function clearGapReportUI(){
    try{
      const card = document.getElementById('gap-report-card');
      if(card) card.style.display = 'none';
      try{ document.body.setAttribute('data-gap-active','0'); }catch{}

      const ids = [
        'gap-report-header',
        'gap-report-diagnosis',
        'gap-report-root-causes',
        'gap-report-recommendations',
        'gap-report-footer'
      ];
      ids.forEach(id => {
        const el = document.getElementById(id);
        if(el) el.innerHTML = '';
      });
    }catch{ /* ignore */ }
  }

  function renderPressures(){
    const p = GAP_lastAnalysis && typeof GAP_lastAnalysis === 'object' ? GAP_lastAnalysis.pressures : null;
    const promoting = Array.isArray(p?.promoting) ? p.promoting : [];
    const inhibiting = Array.isArray(p?.inhibiting) ? p.inhibiting : [];

    const renderList = (items) => {
      if(!items.length) return '<div class="meta">No items detected.</div>';
      return items.slice(0,3).map(x => {
        const title = esc(toText(x?.pressure || x?.title || x?.name || 'Pressure'));
        const mech = esc(toText(x?.mechanism || ''));
        const why = esc(toText(x?.why || x?.description || ''));
        const lever = esc(toText(x?.suggested_lever || x?.lever || ''));
        const ev = Array.isArray(x?.evidence) ? x.evidence : [];
        const snip = ev.length ? esc(toText(ev[0]?.snippet || ev[0])) : '';
        const quoteHtml = snip ? `<div class="pressure-quote">“${snip}”</div>` : '';
        const mechHtml = mech ? `<div class="meta"><strong>Mechanism:</strong> ${mech}</div>` : '';
        const whyHtml = why ? `<div class="meta"><strong>Why:</strong> ${why}</div>` : '';
        const leverHtml = lever ? `<div class="meta"><strong>Lever:</strong> ${lever}</div>` : '';
        return `
          <div class="pressure-item">
            <div class="pressure-title">${title}</div>
            ${mechHtml}
            ${whyHtml}
            ${leverHtml}
            ${quoteHtml}
          </div>
        `;
      }).join('');
    };

    return `
      <div class="pressure-grid">
        <div>
          <h5>Promoting pressures</h5>
          <div class="pressure-list">${renderList(promoting)}</div>
        </div>
        <div>
          <h5>Inhibiting pressures</h5>
          <div class="pressure-list">${renderList(inhibiting)}</div>
        </div>
      </div>
    `;
  }

  function renderRoleGaps(){
    const roleGapEntries = Array.isArray(GAP_lastAnalysis?.role_gap_analysis)
      ? GAP_lastAnalysis.role_gap_analysis
      : [];
    const roleTargets = GAP_roleTargets || [];
    const targetById = {};
    roleTargets.forEach(t => {
      const tid = t && t.target_id ? String(t.target_id).trim() : '';
      if(!tid) return;
      targetById[tid.toLowerCase()] = t;
    });
    const metrics = (GAP_lastAnalysis?.recommended_metrics || []).map(x => typeof x === 'string' ? { name: x } : x);
    const interventions = (GAP_lastAnalysis?.interventions || []).map(x => typeof x === 'string' ? { name: x } : x);

    const items = roleGapEntries.length ? roleGapEntries : roleTargets.slice(0, 2).map(t => ({
      competency: `${t.kind || 'Target'} — ${t.name || 'KSAO'}`,
      target_expectation: t.target_level ? `Target level ${t.target_level} (${proficiencyName(t.target_level)})` : 'Target expectation',
      observation: 'Event indicates a potential deviation from this benchmark.',
      recommended_action: 'Discuss expectations and provide coaching.',
      linked_target_id: t.target_id
    }));

    if (!items.length) {
      return '<div class="meta">No role targets available. Select a role to contextualize.</div>';
    }

    return items.map(entry => {
      const linkedId = entry && entry.linked_target_id ? String(entry.linked_target_id).trim() : '';
      const linkedTarget = linkedId ? targetById[linkedId.toLowerCase()] : null;

      const displayName = linkedTarget
        ? `${linkedTarget.kind || 'Target'} — ${linkedTarget.name || 'KSAO'}`
        : (entry.competency || 'Competency');
      const cname = esc(displayName);

      const targetText = linkedTarget && linkedTarget.target_level != null
        ? `Target level ${linkedTarget.target_level} (${proficiencyName(linkedTarget.target_level)})`
        : (entry.target_expectation || 'Role benchmark');
      const observationText = toText(entry.observation || 'Event insight related to this benchmark.');
      const actionText = toText(entry.recommended_action || 'Align on expectations and provide targeted coaching.');

      const evidence = Array.isArray(entry && entry.evidence) ? entry.evidence : [];
      const evidenceItems = evidence.slice(0, 2).map(ev => {
        const rawSnip = toText((ev && typeof ev === 'object') ? (ev.snippet || '') : ev).trim();
        const lower = rawSnip.toLowerCase();
        const snip = (rawSnip && lower !== 'context:' && lower !== 'context') ? esc(rawSnip) : '';
        const why = esc(toText((ev && typeof ev === 'object') ? (ev.rationale || '') : ''));
        const whyHtml = why ? `<div class="meta">${why}</div>` : '';
        if(!snip) return '';
        return `<li><div>“${snip}”</div>${whyHtml}</li>`;
      }).filter(Boolean);
      const evidenceHtml = evidenceItems.length
        ? `<div class="meta" style="margin-top:8px;"><strong>Evidence:</strong></div>`
          + `<ul class="list-disc" style="margin-top:4px;">`
          + evidenceItems.join('')
          + `</ul>`
        : '';

      const lc = cname.toLowerCase();
      const relKpis = metrics.filter(m => (m.name || '').toLowerCase().includes(lc)).slice(0,2);
      const relNudges = interventions.filter(n => (n.name || '').toLowerCase().includes(lc)).slice(0,2);
      const fallbackKpis = relKpis.length ? relKpis : metrics.slice(0,1);
      const fallbackNudges = relNudges.length ? relNudges : interventions.slice(0,1);
      const kpiHtml = fallbackKpis.map(item => {
        const nm = esc(item.name || item.metric || 'KPI');
        return `<div class="kpi-item"><h3 style="margin:0 0 4px">📊 ${nm}</h3><div class="meta">Measures progress on ${cname}.</div><div style="margin-top:6px"><a class="btn btn-sm btn-secondary" href="/playbook?kind=kpi&q=${encodeURIComponent(nm)}">Open KPIs in Playbook</a><button class="btn btn-sm btn-primary" data-action="add-plan" data-kind="kpi" data-label="${nm}" style="margin-left:8px">Add to Plan</button></div></div>`;
      }).join('');
      const nudgeHtml = fallbackNudges.map(item => {
        const nm = esc(item.name || item.description || 'Intervention');
        return `<div class="nudge-item"><h4 style="margin:0 0 4px">💡 ${nm}</h4><div class="meta">Supports ${cname} development.</div><div style="margin-top:6px"><a class="btn btn-sm btn-secondary" href="/playbook?kind=nudge&q=${encodeURIComponent(nm)}">Open in Playbook</a><button class="btn btn-sm btn-primary" data-action="add-plan" data-kind="nudge" data-label="${nm}" style="margin-left:8px">Add to Plan</button></div></div>`;
      }).join('');

      return `
        <div class="issue-card">
          <h3>🔎 ${cname}</h3>
          <div class="issue-body">
            <div class="gap-scale gap-scale--single">
              <div class="meta"><strong>Benchmark:</strong> ${esc(targetText)}</div>
              <div class="meta"><strong>Observation:</strong> ${esc(observationText)}</div>
              <div class="meta"><strong>Action:</strong> ${esc(actionText)}</div>
              ${evidenceHtml}
            </div>
            <div class="section"><h5>Related KPIs</h5><div class="kpi-list">${kpiHtml || '<div class="meta">KPIs will appear after analysis.</div>'}</div></div>
            <div class="section"><h5>Related Interventions</h5><div class="nudge-list">${nudgeHtml || '<div class="meta">Interventions will appear after analysis.</div>'}</div></div>
          </div>
          <div class="issue-actions"><button class="btn btn-sm btn-secondary" data-action="open-playbook" data-label="${cname}">Open in Playbook</button><button class="btn btn-sm btn-primary" data-action="add-plan" data-kind="gap" data-label="${cname}" style="margin-left:8px">Add to Plan</button></div>
        </div>`;
    }).join('');
  }

  // ----------------------------
  // Role Profile targets framing (callouts on diagnostics)
  // ----------------------------
  async function fetchJSON(url){ const r = await fetch(url, { headers: { 'Accept':'application/json' } }); if(!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }

  function captureAnalysis(detail){
    if(!detail || typeof detail !== 'object') return;
    GAP_lastAnalysis = detail.analysis || null;
    if(detail.input && typeof detail.input === 'object'){
      GAP_lastInput = toText(detail.input.event_description || detail.input.text || detail.input.event || '');
    } else {
      GAP_lastInput = toText(detail.input || '');
    }
    if(detail.role_context_summary){
      GAP_selectedRole = Object.assign({}, GAP_selectedRole || {}, detail.role_context_summary);
    }
    // Track which role the analysis was actually run against.
    try {
      const metaRole = GAP_lastAnalysis?._meta?.role_context_summary?.id ?? null;
      const included = GAP_lastAnalysis?._meta?.role_context_included;
      if (included && (metaRole != null)) {
        GAP_lastAnalysisRoleId = metaRole;
      } else {
        GAP_lastAnalysisRoleId = null;
      }
    } catch (_) {
      GAP_lastAnalysisRoleId = null;
    }
    renderGapReport();
  }

  async function callBsdEndpoint(text){
    try{
      const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
      const headers = { 'Content-Type': 'application/json', 'Accept': 'application/json' };
      if (csrfToken) headers['X-CSRFToken'] = csrfToken;

      const res = await fetch('/api/analyze-event', {
        method: 'POST',
        headers,
        body: JSON.stringify({ event_description: text })
      });
      if(!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json().catch(() => ({}));
      if(!(data && data.success && data.job_id)){
        throw new Error(data?.error || 'Failed to start analysis job.');
      }

      const jobId = data.job_id;
      const startTime = Date.now();
      while(true){
        await new Promise(r => setTimeout(r, 2000));
        const statusResp = await fetch(`/api/analyze-event/${encodeURIComponent(jobId)}`, {
          method: 'GET',
          headers: { 'Accept': 'application/json' }
        });
        const statusJson = await statusResp.json().catch(() => ({}));
        if(statusResp.ok && statusJson && statusJson.success && statusJson.analysis){
          try { await refreshRoleTargets(); } catch (err) { console.warn('refreshRoleTargets failed after analysis', err); }
          return statusJson;
        }
        if(!statusResp.ok){
          throw new Error(statusJson?.error || `Analysis failed (HTTP ${statusResp.status}).`);
        }
        if((Date.now() - startTime) > 600000){
          throw new Error('Timed out waiting for analysis.');
        }
      }
    }catch(err){
      return { success:false, error: err.message || String(err) };
    }
  }

  function normaliseBiasEntry(entry){
    if(!entry) return null;
    const name = toText(entry.name || entry.heading || entry.title || 'Bias');
    const description = toText(entry.description ?? entry.short_description ?? entry.summary ?? entry.detailed_description ?? '');
    const impact = toText(entry.impact ?? entry.effect ?? '');

    const confidenceRaw = toText(entry.confidence ?? entry.confidence_level ?? '');
    const confidence = confidenceRaw ? confidenceRaw.trim().toLowerCase() : '';
    const evRaw = Array.isArray(entry.evidence)
      ? entry.evidence
      : (Array.isArray(entry.quotes) ? entry.quotes : (Array.isArray(entry.snippets) ? entry.snippets : []));
    const evidence = Array.isArray(evRaw)
      ? evRaw.map(x => {
          if(x && typeof x === 'object'){
            return { snippet: toText(x.snippet ?? x.quote ?? x.text ?? ''), rationale: toText(x.rationale ?? x.reason ?? x.explanation ?? '') };
          }
          return { snippet: toText(x), rationale: '' };
        }).filter(x => x && x.snippet)
      : [];
    return {
      id: entry.id,
      name,
      description,
      impact,
      countermeasures: Array.isArray(entry.countermeasures) ? entry.countermeasures.map(toText).filter(Boolean) : [],
      model_framework: entry.model_framework || entry.related_framework || entry.framework || entry.collection || null,
      confidence: (confidence === 'high' || confidence === 'medium' || confidence === 'low') ? confidence : null,
      evidence,
    };
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
      const data = await fetchJSON(`/api/roles/${rid}/ksao-targets`);
      const tgts = Array.isArray(data.targets) ? data.targets : [];
      GAP_roleTargets = tgts;
      if(!tgts.length){ box.style.display='none'; box.innerHTML=''; return; }

      const tgtsDisplay = tgts.filter(t => {
        const k = kindSlug(t && t.kind ? t.kind : '');
        return k === 'knowledge' || k === 'skill' || k === 'ability' || k === 'outcome';
      });
      const totalDisplay = tgtsDisplay.length;
      if(!totalDisplay){ box.style.display='none'; box.innerHTML=''; return; }

      function cleanTargetNameAndDescription(t){
        try{
          const rawName = String((t && t.name) || '').trim();
          let name = rawName;
          let desc = String((t && t.description) || '').trim();
          if(!desc && /description\s*:/i.test(rawName)){
            const parts = rawName.split(/description\s*:/i);
            name = String(parts[0] || '').trim();
            desc = String(parts.slice(1).join('Description:') || '').trim();
          }
          name = name.split(/\r?\n/)[0].trim();
          if(/^name\s*:/i.test(name)) name = name.split(':', 2).slice(1).join(':').trim();
          if(/description\s*:/i.test(name)) name = name.split(/description\s*:/i)[0].trim();
          if(!name) name = 'KSAO';
          return { name, desc };
        }catch{
          return { name: (t && t.name) ? String(t.name) : 'KSAO', desc: (t && t.description) ? String(t.description) : '' };
        }
      }

      function kindSlug(v){
        return String(v || '').trim().toLowerCase();
      }

      function render(){
        const expanded = box.dataset.expanded === '1';
        const show = expanded ? tgtsDisplay : tgtsDisplay.slice(0, 6);
        const remaining = Math.max(0, totalDisplay - show.length);
        const toggle = totalDisplay > 6
          ? `<button class="btn btn-sm btn-secondary" data-action="toggle-role-targets">${expanded ? 'Show less' : `Show all (${totalDisplay})`}</button>`
          : '';

        const itemsHtml = show.map(t => {
          const kind = String(t.kind || 'Target').trim() || 'Target';
          const ks = kindSlug(kind);
          const { name, desc } = cleanTargetNameAndDescription(t);
          const lvl = t.target_level;
          const drv = t && t.driver_card_name ? String(t.driver_card_name).trim() : '';
          const lvlHtml = (lvl == null)
            ? `<span class="rt-badge rt-badge--muted" title="Target level not set">Target —</span>`
            : `<span class="rt-badge rt-badge--level">Target ${esc(lvl)}/5</span>`;
          const drvHtml = drv ? `<span class="rt-badge rt-badge--driver" title="Linked driver card">Driver: ${esc(drv)}</span>` : '';

          const head = `
            <div class="rt-row">
              <div class="rt-left">
                <span class="rt-kind" data-kind="${esc(ks)}">${esc(kind)}</span>
                <span class="rt-name">${esc(name)}</span>
              </div>
              <div class="rt-right">${lvlHtml}${drvHtml}</div>
            </div>
          `;
          if(desc){
            return `<details class="rt-item"><summary>${head}</summary><div class="rt-desc">${esc(desc)}</div></details>`;
          }
          return `<div class="rt-item rt-item--plain">${head}</div>`;
        }).join('');

        box.innerHTML = `
          <div class="role-targets">
            <div class="role-targets__head">
              <div class="role-targets__title">Role Targets</div>
              <div class="role-targets__actions">
                <span class="rt-count">${esc(totalDisplay)} total</span>
                ${toggle}
              </div>
            </div>
            <div class="role-targets__list">${itemsHtml}</div>
            ${remaining ? `<div class="role-targets__more">+${esc(remaining)} more</div>` : ''}
          </div>
        `;
        box.style.display = 'block';

        const btn = box.querySelector('[data-action="toggle-role-targets"]');
        if(btn){
          btn.addEventListener('click', (e) => {
            e.preventDefault();
            box.dataset.expanded = (box.dataset.expanded === '1') ? '0' : '1';
            render();
          });
        }
      }

      if(!('expanded' in box.dataset)) box.dataset.expanded = '0';
      render();
      // Also re-render the gap report with latest role context
      renderGapReport();
    }catch(e){ const box = document.getElementById('diag-role-targets'); if(box){ box.style.display='none'; } }
  }
  function initRoleTargetsFraming(){
    const sel = document.getElementById('diag-role-select');
    if(sel){
      sel.addEventListener('change', () => {
        // Immediately hide any previously-rendered gap report to avoid stale output flash.
        clearGapReportUI();
        setTimeout(refreshRoleTargets, 50);
      });
    }
    // initial load
    refreshRoleTargets();
    // also refresh when other modules persist the role
    window.addEventListener('role:selected', () => { clearGapReportUI(); setTimeout(refreshRoleTargets, 0); });
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

    // Also require the current textbox content to match the analyzed input.
    // This prevents showing an older gap report when the user edits the event text or when the page restores cached output.
    try{
      const curEl = document.getElementById('event-description');
      const cur = curEl ? _normInputText(curEl.value) : '';
      const last = _normInputText(GAP_lastInput);
      if(cur && last && cur !== last){
        card.style.display = 'none';
        try{ document.body.setAttribute('data-gap-active','0'); }catch{}
        return;
      }
    }catch{ /* ignore */ }

    // Only show gap report if the last analysis was run WITH role context for the currently selected role.
    // Otherwise, the cached analysis can make a gap report appear as an artifact when switching roles.
    const roleIncluded = !!(GAP_lastAnalysis?._meta?.role_context_included);
    const currentRoleId = GAP_selectedRole?.id;
    const roleMatches = roleIncluded && (GAP_lastAnalysisRoleId != null) && (String(GAP_lastAnalysisRoleId) === String(currentRoleId));
    if(!roleMatches){
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

    const roleName = GAP_selectedRole?.name || GAP_lastAnalysis?._meta?.role_context_summary?.name || null;
    const dateStr = new Date().toLocaleDateString();
    const hasAnalysis2 = true; // by this point, we've already validated hasAnalysis

    const inputText = String(GAP_lastInput || '').trim();
    const inputPreview = inputText.length > 160 ? (inputText.slice(0, 160) + '…') : inputText;
    const hasInput = inputText.length > 0;

    // Header & Context (compact, in a distinct card)
    headerEl.innerHTML = `
      <div class="section">
        <h3>Gap Analysis for ${roleName ? esc(roleName) : 'Selected Role'} (AI-Driven)</h3>
        <div class="context-card">
          <div class="meta">Assessment for ${esc('an individual in the role')} — ${dateStr}</div>
          <div><strong>Role Profile:</strong> ${roleName ? esc(roleName) : '—'}</div>
          <div class="meta" style="margin-top:6px;">Utilizing its defined KSAOs and target competencies as a benchmark. The AI compares the described performance against the role's ideal expectations.</div>
          ${hasInput ? `
            <div class="user-input" style="margin-top:10px;">
              <div class="meta"><strong>Input used:</strong> “${esc(inputPreview)}”</div>
              <details style="margin-top:6px;">
                <summary class="meta" style="cursor:pointer;">View full input</summary>
                <div style="margin-top:6px;">${esc(inputText)}</div>
              </details>
            </div>
          ` : ''}
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
          ${renderRoleGaps()}
        </div>
      </div>
    `;

    // Root Causes (simple placeholders; can be enriched later)
    const biasesRaw = Array.isArray(GAP_lastAnalysis?.behavioral_biases)
      ? GAP_lastAnalysis.behavioral_biases
      : (Array.isArray(GAP_lastAnalysis?.biases) ? GAP_lastAnalysis.biases : []);
    const biases = Array.isArray(biasesRaw)
      ? biasesRaw.map(normaliseBiasEntry).filter(Boolean).slice(0,2)
      : [];
    causesEl.innerHTML = `
      <div class="section">
        <h4>Pressures Shaping the Situation</h4>
        <p class="meta">Promoting pressures increase the likelihood of undesired behaviors. Inhibiting pressures block the desired behaviors.</p>
        ${renderPressures()}

        <h4>Potential Root Causes (Behavioral Biases): Impact on Role Performance</h4>
        ${biases.length ? biases.map(b => `
          <div class="bias-card">
            <h4>🚫 ${esc(b.name || 'Bias')}</h4>
            ${b.description ? `<p>${esc(b.description)}</p>` : ''}
            ${b.impact ? `<p><strong>Impact:</strong> ${esc(b.impact)}</p>` : `<p><strong>Impact Summary:</strong> Directly impedes ${roleName? esc(roleName)+"'s" : 'the role\'s'} effective performance.</p>`}
            ${Array.isArray(b.countermeasures) && b.countermeasures.length ? `<div class="bias-recs"><div class="recs-title">Countermeasures</div><ul class="list-disc"><li>${b.countermeasures.map(escapeHtml).join('</li><li>')}</li></ul></div>` : ''}
            ${b.model_framework ? `<p class="meta">Framework: ${esc(b.model_framework)}</p>` : ''}
            <div><a class="btn btn-sm btn-primary" href="/playbook?kind=bias&q=${encodeURIComponent(b.name || '')}">Explore Nudges to Counteract Bias</a></div>
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
  const FALLBACK_BIASES = [
    {
      name: 'Status Quo Bias',
      description: 'Preference for existing practices, even when suboptimal.',
      trigger_keywords: ['status quo','stick with','business as usual','keep doing','resistance to change','same way','always the same','never changes'],
      countermeasures: ['Surface switching costs explicitly','Run small safe-to-try experiments','Time-box a trial period with success criteria'],
    },
    {
      name: 'Authority Bias',
      description: 'Overweighting opinions from authority figures.',
      trigger_keywords: ['authority','executive said','boss said','senior leader','leadership insisted','leaders say'],
      countermeasures: ['Invite dissenting views first (pre-mortem)','Use anonymous voting before discussion','Ask for evidence rather than rank-based claims'],
    },
    {
      name: 'Bandwagon Effect',
      description: 'Adopting beliefs because many others hold them.',
      trigger_keywords: ['bandwagon','everyone thinks','popular','consensus','most people'],
      countermeasures: ['Seek counter-examples and base rates','Split group to argue alternatives','Use written rationale before group talk'],
    },
    {
      name: 'Halo Effect',
      description: 'Letting a single positive trait sway overall judgment.',
      trigger_keywords: ['leadership presence','communicates well','obvious choice','natural leader','charismatic','strong presence','well-liked'],
      countermeasures: ['List explicit evaluation criteria','Have independent reviewers score candidates','Separate style cues from competency evidence'],
    },
    {
      name: 'Pressure Heuristic',
      description: 'Rushed decisions under time or stress constraints.',
      trigger_keywords: ['time pressure','tight deadline','urgent','rush','last minute','pressure'],
      countermeasures: ['Pause with a 10-minute cooling-off','Define a minimum viable decision','Clarify reversible vs irreversible decisions'],
    },
    {
      name: 'Availability Heuristic',
      description: 'Judging by information that comes easily to mind.',
      trigger_keywords: ['limited information','incomplete data','lack of data','gut feel','intuition only'],
      countermeasures: ['Collect a small but representative sample','Use a decision checklist','Seek an external benchmark'],
    },
    {
      name: 'Framing Effect',
      description: 'Choices influenced by how options are presented.',
      trigger_keywords: ['framing','framed as','presented as','loss vs gain','wording changed'],
      countermeasures: ['Reframe options in neutral language','Show both loss and gain perspectives','Compare equal baselines and units'],
    }
  ];

  let biasCatalog = [...FALLBACK_BIASES];

  async function loadBiasCatalog(){
    if(biasCatalog.length) return biasCatalog;
    try{
      const res = await fetch('/api/knowledge/biases?limit=200', { headers: { 'Accept': 'application/json' } });
      if(!res.ok) throw new Error('Failed to load biases');
      const data = await res.json();
      if(Array.isArray(data.items) && data.items.length){
        biasCatalog = data.items.map(item => ({
          id: item.id,
          name: item.heading || item.name || 'Bias',
          description: item.content || item.short_description || '',
          tags: Array.isArray(item.tags) ? item.tags : [],
          trigger_keywords: Array.isArray(item.trigger_keywords) ? item.trigger_keywords : [],
          countermeasures: Array.isArray(item.countermeasures) ? item.countermeasures : [],
        }));
      } else {
        biasCatalog = [...FALLBACK_BIASES];
      }
    }catch(err){
      console.warn('Unable to load bias catalog, fallback to static heuristics', err);
      biasCatalog = [...FALLBACK_BIASES];
    }
    return biasCatalog;
  }

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

  function initBSD(){
    const btn = $('#bsd-analyze');
    const clearBtn = $('#bsd-clear');
    const output = $('#bsd-output');
    const textarea = $('#bsd-text');
    if(!btn || !output || !textarea) return;

    let bsdTimerHandle = null;
    let bsdTimerStart = 0;

    function stopBsdTimer(){
      if(bsdTimerHandle){
        try{ clearInterval(bsdTimerHandle); }catch{}
        bsdTimerHandle = null;
      }
      bsdTimerStart = 0;
    }

    function formatElapsed(ms){
      const total = Math.max(0, Math.floor(ms / 1000));
      const m = Math.floor(total / 60);
      const s = total % 60;
      const ss = String(s).padStart(2, '0');
      return `${m}:${ss}`;
    }

    // Restore persisted text
    try{
      const saved = sessionStorage.getItem('bsd_text');
      if(saved) textarea.value = saved;
    }catch{}
    textarea.addEventListener('input', () => {
      try{ sessionStorage.setItem('bsd_text', textarea.value); }catch{}
    });

    if(clearBtn){
      clearBtn.addEventListener('click', () => {
        stopBsdTimer();
        textarea.value = '';
        try{ sessionStorage.removeItem('bsd_text'); }catch{}
        output.innerHTML = '';
        output.style.display = 'none';
        try{ textarea.focus(); }catch{}
      });
    }

    function analyze(text){
      const t = (text || '').toLowerCase();
      const matches = [];
      biasCatalog.forEach((bias) => {
        const keywords = Array.isArray(bias.trigger_keywords) ? bias.trigger_keywords : [];
        if(keywords.some(term => t.includes(term.toLowerCase()))){
          matches.push(bias);
        }
      });
      return matches;
    }

    function playbookLink(name){
      const q = encodeURIComponent(name);
      const filter = encodeURIComponent(`kind:bias;name:${name}`);
      return `/playbook?kind=bias&q=${q}&filter=${filter}`;
    }

    function render(text, result, kbItems, meta, pressures){
      const inputText = (text || '').trim();
      const inputPreview = inputText.length > 160 ? (inputText.slice(0, 160) + '…') : inputText;
      const inputHtml = inputText ? `
        <div class="analysis-card">
          <h4>Input used</h4>
          <div class="meta"><strong>Input used:</strong> “${escapeHtml(inputPreview)}”</div>
          <details style="margin-top:6px;">
            <summary class="meta" style="cursor:pointer;">View full input</summary>
            <div style="margin-top:6px;">${escapeHtml(inputText)}</div>
          </details>
        </div>
      ` : '';

      const intro = 'This diagnostic surfaces plausible behavioral pressures and cognitive biases suggested by the described event. Treat these as hypotheses to validate with direct observation and data.';
      const idList = result.map(b => {
        const icon = '🧠';
        const framework = b.model_framework ? `<span class="bias-framework">Framework: ${escapeHtml(b.model_framework)}</span>` : '';

        const conf = (b && b.confidence) ? String(b.confidence).toLowerCase() : '';
        const confHtml = (conf === 'high' || conf === 'medium' || conf === 'low')
          ? `<div class="meta"><strong>Confidence:</strong> ${escapeHtml(conf)}</div>`
          : `<div class="meta"><strong>Confidence:</strong> low</div>`;

        const ev = Array.isArray(b?.evidence) ? b.evidence : [];
        const evItems = ev
          .map(x => ({
            snippet: toText(x?.snippet || x),
            rationale: toText(x?.rationale || ''),
            verified: !!(x && typeof x === 'object' && (x.verified === true || x.verified === 'true' || x.verified === 1))
          }))
          .filter(x => x.snippet)
          .slice(0, 2);
        const evHtml = evItems.length
          ? `<div class="meta" style="margin-top:8px;"><strong>Evidence:</strong><div style="margin-top:4px;">${evItems.map(e => {
              const badge = e.verified
                ? '<span class="badge" style="margin-left:6px;">Verified</span>'
                : '<span class="badge" style="margin-left:6px;opacity:.75;">Unverified</span>';
              return `“${escapeHtml(e.snippet)}”${badge}${e.rationale ? `<div class=\"meta\" style=\"margin-top:2px;\"><strong>Why:</strong> ${escapeHtml(e.rationale)}</div>` : ''}`;
            }).join('<div style="height:6px;"></div>')}</div></div>`
          : `<div class="meta" style="margin-top:8px;"><strong>Evidence:</strong> Not provided</div>`;
        return `
        <li class="bias-card">
          <div class="bias-card-header">
            <span class="bias-icon">${icon}</span>
            <div class="bias-title">${escapeHtml(b.name)}</div>
          </div>
          <p class="bias-desc">${escapeHtml(b.description || '')}</p>
          ${confHtml}
          ${framework}
          ${evHtml}
          <div class="bias-actions">
            <button class="btn btn-sm btn-secondary" data-action="add-plan" data-kind="bias" data-label="${escapeHtml(b.name)}">Copy to Plan</button>
            <a class="btn btn-sm btn-primary" href="${playbookLink(b.name)}">Open Bias Card</a>
          </div>
          ${Array.isArray(b.countermeasures) && b.countermeasures.length ? `<div class="bias-recs"><div class="recs-title">Countermeasures</div><ul class="list-disc"><li>${b.countermeasures.map(escapeHtml).join('</li><li>')}</li></ul></div>` : ''}
        </li>`;
      }).join('');

      const renderPressures = (p) => {
        const promoting = Array.isArray(p?.promoting) ? p.promoting : [];
        const inhibiting = Array.isArray(p?.inhibiting) ? p.inhibiting : [];
        const any = promoting.length || inhibiting.length;

        const renderList = (items) => {
          if(!items.length) return '<div class="meta">No items detected.</div>';
          return items.slice(0, 4).map(x => {
            const title = escapeHtml(toText(x?.pressure || x?.title || x?.name || 'Pressure'));
            const mech = escapeHtml(toText(x?.mechanism || ''));
            const why = escapeHtml(toText(x?.why || x?.description || ''));
            const lever = escapeHtml(toText(x?.suggested_lever || x?.lever || ''));

            const conf = String(toText(x?.confidence || x?.confidence_level || '')).trim().toLowerCase();
            const confHtml = (conf === 'high' || conf === 'medium' || conf === 'low')
              ? `<div class="meta"><strong>Confidence:</strong> ${escapeHtml(conf)}</div>`
              : `<div class="meta"><strong>Confidence:</strong> low</div>`;

            const ev = Array.isArray(x?.evidence) ? x.evidence : [];
            const evItems = ev
              .map(e => ({
                snippet: toText(e?.snippet || e),
                rationale: toText(e?.rationale || ''),
                verified: !!(e && typeof e === 'object' && (e.verified === true || e.verified === 'true' || e.verified === 1))
              }))
              .filter(e => e.snippet && e.snippet.trim() && e.snippet.trim().toLowerCase() !== 'context:')
              .slice(0, 2);
            const quoteHtml = evItems.length
              ? `<div class="meta" style="margin-top:8px;"><strong>Evidence:</strong><div style="margin-top:4px;">${evItems.map(e => {
                  const badge = e.verified
                    ? '<span class="badge" style="margin-left:6px;">Verified</span>'
                    : '<span class="badge" style="margin-left:6px;opacity:.75;">Unverified</span>';
                  return `“${escapeHtml(e.snippet)}”${badge}${e.rationale ? `<div class=\"meta\" style=\"margin-top:2px;\"><strong>Why:</strong> ${escapeHtml(e.rationale)}</div>` : ''}`;
                }).join('<div style="height:6px;"></div>')}</div></div>`
              : `<div class="meta" style="margin-top:8px;"><strong>Evidence:</strong> Not provided</div>`;
            const mechHtml = mech ? `<div class="meta"><strong>Mechanism:</strong> ${mech}</div>` : '';
            const whyHtml = why ? `<div class="meta"><strong>Why:</strong> ${why}</div>` : '';
            const leverHtml = lever ? `<div class="meta"><strong>Lever:</strong> ${lever}</div>` : '';
            return `
              <li class="bias-card">
                <div class="bias-card-header">
                  <span class="bias-icon">⚖️</span>
                  <div class="bias-title">${title}</div>
                </div>
                ${mechHtml}
                ${whyHtml}
                ${leverHtml}
                ${confHtml}
                ${quoteHtml}
                <div class="bias-actions">
                  <button class="btn btn-sm btn-secondary" data-action="add-plan" data-kind="driver" data-label="${title}">Copy to Plan</button>
                </div>
              </li>
            `;
          }).join('');
        };

        if(!p && !any) return '';

        return `
          <div class="analysis-card">
            <h4>Pressures (Promoting vs Inhibiting)</h4>
            <p class="meta">Promoting pressures increase the likelihood of undesired behaviors. Inhibiting pressures block the desired behaviors.</p>
            <div class="analysis-grid" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
              <div>
                <h5 style="margin:0 0 8px;">Promoting pressures</h5>
                <ol class="analysis-list">${renderList(promoting)}</ol>
              </div>
              <div>
                <h5 style="margin:0 0 8px;">Inhibiting pressures</h5>
                <ol class="analysis-list">${renderList(inhibiting)}</ol>
              </div>
            </div>
          </div>
        `;
      };

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

      const metaSection = meta ? `
        <div class="analysis-card">
          <h4>Analysis Details</h4>
          <ul class="analysis-list meta-list">
            ${meta.elapsed ? `<li><strong>Completed in:</strong> ${escapeHtml(meta.elapsed)}</li>` : ''}
            ${meta.generated_by ? `<li><strong>Generated by:</strong> ${escapeHtml(meta.generated_by)}</li>` : ''}
            ${meta.ollama_status ? `<li><strong>LLM status:</strong> ${escapeHtml(meta.ollama_status)}</li>` : ''}
            ${meta.error ? `<li class="text-danger"><strong>Note:</strong> ${escapeHtml(meta.error)}</li>` : ''}
          </ul>
        </div>
      ` : '';

      output.innerHTML = `
        ${inputHtml}
        <div class="analysis-card">
          <h4>Overview</h4>
          <p>${intro}</p>
        </div>
        ${renderPressures(pressures)}
        <div class="analysis-card">
          <h4>Identified Biases, Heuristics, and Fallacies</h4>
          ${result.length ? `<ol class="analysis-list">${idList}</ol>` : '<p>No specific biases detected from keywords; consider trying the AI Event Analysis tab for a deeper read.</p>'}
        </div>
        ${kbSection}
        ${metaSection}
      `;
      output.style.display = 'block';
    }

    btn.addEventListener('click', async () => {
      const text = textarea.value.trim();
      if(!text){ textarea.focus(); return; }

      stopBsdTimer();
      bsdTimerStart = Date.now();
      output.innerHTML = '<div class="analysis-card"><p>Analyzing event… <span class="meta" id="bsd-elapsed" style="margin-left:8px;">Elapsed: 0:00</span></p></div>';
      output.style.display = 'block';

      bsdTimerHandle = setInterval(() => {
        const el = document.getElementById('bsd-elapsed');
        if(!el || !bsdTimerStart) return;
        el.textContent = `Elapsed: ${formatElapsed(Date.now() - bsdTimerStart)}`;
      }, 1000);

      let apiResult = null;
      let elapsedMs = 0;
      try{
        apiResult = await callBsdEndpoint(text);
      }finally{
        elapsedMs = bsdTimerStart ? (Date.now() - bsdTimerStart) : 0;
        stopBsdTimer();
      }

      let biases = [];
      let kbItems = null;
      let meta = null;
      let pressures = null;

      if(apiResult.success){
        const kbPayload = apiResult.kb || {};
        kbItems = Array.isArray(kbPayload.biases) ? kbPayload.biases : null;
        const providedBiases = Array.isArray(apiResult.analysis?.behavioral_biases)
          ? apiResult.analysis.behavioral_biases
          : (Array.isArray(apiResult.analysis?.biases) ? apiResult.analysis.biases : []);
        biases = providedBiases.map(normaliseBiasEntry).filter(Boolean);
        if(!biases.length && kbItems){
          biases = kbItems.map(normaliseBiasEntry).filter(Boolean);
        }
        pressures = apiResult.analysis?.pressures || null;
        meta = {
          elapsed: elapsedMs ? formatElapsed(elapsedMs) : null,
          generated_by: apiResult.generated_by,
          ollama_status: apiResult.ollama_status,
        };
      }else{
        meta = { elapsed: elapsedMs ? formatElapsed(elapsedMs) : null, error: apiResult.error };
      }

      if(!biases.length){
        await loadBiasCatalog();
        biases = analyze(text);
      }

      render(text, biases, kbItems, meta, pressures);
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
  window.addEventListener('analysis:completed', (evt) => {
    captureAnalysis(evt.detail || {});
  });

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
