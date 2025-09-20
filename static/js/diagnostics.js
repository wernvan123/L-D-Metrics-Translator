(function(){
  const q = id => document.getElementById(id);
  const sessionEl = q('session-context');
  const aiSummaryEl = q('ai-summary');
  const aiDriversEl = q('ai-drivers');
  const recMetricsEl = q('recommended-metrics');
  const analyzeBtn = q('analyze-btn');
  const addRecBtn = q('add-recommended-btn');
  const toggleAI = q('toggle-ai-suggestions');
  const roleSelect = q('role-profile');
  const gapHeaderEl = q('gap-report-header');
  const gapDiagnosisEl = q('gap-report-diagnosis');
  const gapCausesEl = q('gap-report-root-causes');
  const gapRecsEl = q('gap-report-recommendations');
  const gapFooterEl = q('gap-report-footer');

  let lastAnalysis = null;
  let aiSuggestions = [];
  let selectedRole = null; // {id, name, ...}
  let analysisServiceIssue = false;

  async function loadSession(){
    try {
      const res = await fetch('/api/context/framework/state');
      const s = await res.json();
      sessionEl.innerHTML = `
        <div><strong>Framework:</strong> ${s.framework_name || '—'}</div>
        <div><strong>Active competencies:</strong> ${(s.active_competencies||[]).length}</div>
        <div><strong>Selected metrics:</strong> ${s.selected_metrics_count || 0}</div>
      `;
    } catch (e) {
      sessionEl.innerHTML = '<div class="error">Failed to load session.</div>';
      window.notify && window.notify('error', 'Failed to load session');
    }
  }

  async function analyze(){
    const payload = {
      description: q('challenge-description').value,
      event_type: q('event-type').value,
      audience: q('audience').value,
      timeframe: q('timeframe').value,
      context_snapshot: null
    };
    try {
      window.dispatchEvent(new Event('context:saving'));
      const resCtx = await fetch('/api/context/framework/state');
      payload.context_snapshot = await resCtx.json();
    } catch {}

    try {
      analyzeBtn.disabled = true;
      analyzeBtn.textContent = 'Analyzing...';
      const res = await fetch('/api/analyze-event', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      if (!res.ok) { analysisServiceIssue = true; throw new Error('Analysis endpoint returned an error'); }
      const data = await res.json();
      lastAnalysis = data;
      analysisServiceIssue = false;
      aiSummaryEl.textContent = data.summary || 'No summary provided by AI.';
      aiDriversEl.innerHTML = renderDrivers(data.drivers, data.competencies);
      recMetricsEl.innerHTML = renderMetrics(data.recommended_metrics);
      addRecBtn.disabled = !(data.recommended_metrics && data.recommended_metrics.length);

      // Persist under event-analysis (if your API exists). Swallow errors if missing.
      try {
        await fetch('/api/context/system', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: 'event-analysis', value: data }) });
        window.dispatchEvent(new Event('context:saved'));
        window.notify && window.notify('success', 'AI summary saved to session');
      } catch {
        window.dispatchEvent(new Event('context:error'));
        window.notify && window.notify('error', 'Could not persist AI summary');
      }

      // Refresh Gap Analysis with the latest analysis context
      await renderGapReport();
    } catch (e) {
      aiSummaryEl.innerHTML = '<div class="error">'+(e.message || 'AI analysis failed.')+'</div>';
      window.notify && window.notify('error', 'AI analysis failed');
    } finally {
      analyzeBtn.disabled = false;
      analyzeBtn.textContent = 'Analyze with AI';
    }
  }

  function renderDrivers(drivers = [], competencies = []){
    const d = drivers.map(x=>`<li>${x}</li>`).join('');
    const c = competencies.map(x=>`<li>${x}</li>`).join('');
    return `<div class="grid two">
      <div><div class="meta">Drivers</div><ul class="list">${d || '<li>—</li>'}</ul></div>
      <div><div class="meta">Competencies</div><ul class="list">${c || '<li>—</li>'}</ul></div>
    </div>`;
  }

  function renderMetrics(metrics = []){
    if (!metrics || !metrics.length) return '—';
    return `<ul class="list">${metrics.map(m=>{
      const id = m.id || m.metric_id || m;
      const name = m.name || m;
      const tag = m.tag?`<span class='badge'>${m.tag}</span>`:'';
      return `<li>${name} ${tag} <button class='btn' data-view-metric='${id}'>View</button></li>`;
    }).join('')}</ul>`;
  }

  async function addRecommended(){
    if (!lastAnalysis || !lastAnalysis.recommended_metrics) return;
    addRecBtn.disabled = true;
    try {
      for (const m of lastAnalysis.recommended_metrics) {
        const metric_id = m.id || m.metric_id || m;
        if (!metric_id) continue;
        await fetch('/api/context/metrics/select', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ metric_id, source: 'diagnostics_ai' }) });
        // log commit interaction if available
        try { await fetch('/api/smart-recommendations/interact', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ recommendation_id: metric_id, action: 'commit', scope: 'diagnostics' }) }); } catch {}
      }
      window.dispatchEvent(new Event('context:saved'));
      window.notify && window.notify('success', 'Recommended metrics added');
    } catch(e){
      window.dispatchEvent(new Event('context:error'));
      window.notify && window.notify('error', 'Failed adding recommended metrics');
    } finally {
      addRecBtn.disabled = false;
      loadSession();
    }
  }

  async function loadAISuggestions(){
    if (!toggleAI.checked) { aiSuggestions = []; q('recommended-metrics').insertAdjacentHTML('beforeend',''); return; }
    try {
      const resCtx = await fetch('/api/context/framework/state');
      const ctx = await resCtx.json();
      const res = await fetch('/api/smart-recommendations/generate', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ type: 'metric', session_context: ctx, scope: 'diagnostics' }) });
      if (!res.ok) throw new Error('AI recommendations not available.');
      const data = await res.json();
      aiSuggestions = (data.recommendations||[]);
      const html = `<div class="mt"><div class="meta">AI Suggestions</div>${renderMetrics(aiSuggestions)}</div>`;
      recMetricsEl.innerHTML += html;
      // log view interaction silently
      try { await fetch('/api/smart-recommendations/interact', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ action: 'view', scope: 'diagnostics' }) }); } catch {}
    } catch(e){
      // Friendly notice if endpoint absent
      window.notify && window.notify('error', 'AI suggestions not available');
    }
  }

  // ---------- Roles: load, select, and compute gaps ----------
  async function loadRoles(){
    if (!roleSelect) return;
    try {
      // Preselect from session first
      let pre = null;
      try { const r = await fetch('/api/roles/select'); if (r.ok) { const j = await r.json(); pre = j.selected_role_profile_id; } } catch {}
      const res = await fetch('/api/roles');
      const data = await res.json();
      const roles = (data.roles || []);
      roleSelect.innerHTML = `<option value="">— Select a role profile —</option>` + roles.map(r=>`<option value="${r.id}">${escapeHtml(r.name)}${r.department?` — ${escapeHtml(r.department)}`:''}</option>`).join('');
      if (pre) {
        roleSelect.value = String(pre);
        await handleRoleChange();
      }
    } catch (e) {
      // silent fail for dev if roles not configured
    }
  }

  async function handleRoleChange(){
    const val = (roleSelect && roleSelect.value) ? parseInt(roleSelect.value, 10) : NaN;
    if (!val || isNaN(val)) {
      selectedRole = null;
      try { await fetch('/api/roles/select', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ role_profile_id: null }) }); } catch {}
      try { await fetch('/api/context/system', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ key: 'selected_role_profile', value: null }) }); } catch {}
      window.dispatchEvent(new Event('context:saved'));
      await renderGapReport();
      return;
    }
    try {
      await fetch('/api/roles/select', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ role_profile_id: val }) });
    } catch {}
    try {
      const r = await fetch(`/api/roles/${val}?include=targets,ksaos`);
      const data = await r.json();
      selectedRole = (data.role || { id: val });
    } catch { selectedRole = { id: val }; }
    // Persist selected role to session context for cross-page access
    try {
      const minimal = selectedRole ? { id: selectedRole.id, name: selectedRole.name, department: selectedRole.department } : null;
      await fetch('/api/context/system', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ key: 'selected_role_profile', value: minimal }) });
      window.dispatchEvent(new Event('context:saved'));
    } catch {
      window.dispatchEvent(new Event('context:error'));
    }
    await renderGapReport();
  }

  function escapeHtml(s){
    return String(s||'').replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
  }

  async function fetchGaps(roleId){
    try {
      const r = await fetch(`/api/roles/${roleId}/gaps`);
      if (!r.ok) return { gaps: [], weighted_gap: 0 };
      return await r.json();
    } catch { return { gaps: [], weighted_gap: 0 }; }
  }

  async function renderGapReport(){
    if (!gapHeaderEl || !gapDiagnosisEl || !gapCausesEl || !gapRecsEl || !gapFooterEl) return;
    const desc = q('challenge-description')?.value || '';
    const dateStr = new Date().toLocaleDateString();
    const roleName = selectedRole?.name || '—';

    // Header & context
    gapHeaderEl.innerHTML = `
      <h3>AI-Driven Performance Gap Analysis: ${escapeHtml(roleName)}</h3>
      <div class="meta">Assessment for ${escapeHtml('An individual in the role')} — ${escapeHtml(dateStr)}</div>
      <div class="card mt">
        <div class="card-body">
          <div class="meta">Analysis Context</div>
          <p>This analysis is being performed for an individual in the <strong>${escapeHtml(roleName)}</strong> position, utilizing its defined KSAOs and target competencies as a benchmark. The AI compares the described performance against the role's ideal expectations.</p>
          ${desc ? `<div class="mt"><div class="meta">Observed Event/Situation</div><blockquote>${escapeHtml(desc)}</blockquote></div>` : ''}
        </div>
      </div>
    `;

    // Diagnosis
    const primarySummary = lastAnalysis?.summary || `Based on the input and the ${escapeHtml(roleName)} requirements, the primary challenge likely involves gaps in selected role competencies.`;
    let issuesHtml = '';
    if (selectedRole?.id) {
      const gapData = await fetchGaps(selectedRole.id);
      const gaps = (gapData.gaps || []).slice().sort((a,b)=> (b.gap||0) - (a.gap||0));
      issuesHtml = gaps.slice(0, 4).map(g=>{
        const cname = g.competency_name || `Competency ${g.competency_id}`;
        const target = (g.target_level!=null)? g.target_level : '—';
        const current = (g.current_level!=null)? g.current_level : '—';
        const icon = '🧩';
        return `
          <div class="card mt">
            <div class="card-body">
              <h4>${icon} ${escapeHtml(cname)}</h4>
              <div class="mt-sm">AI Analysis: ${escapeHtml(lastAnalysis?.details?.[cname] || 'Indications of underperformance relative to role expectations for this competency.')}</div>
              <div class="mt-sm"><strong>Role Gap Identified:</strong> Impacts the <strong>${escapeHtml(roleName)}</strong> competency <em>${escapeHtml(cname)}</em>. (Target: ${escapeHtml(String(target))}, Estimated Current: ${escapeHtml(String(current))})</div>
              <div class="mt-sm">
                <button class="btn" data-open-playbook="${escapeHtml(cname)}">Open in Playbook</button>
                <button class="btn" data-add-to-plan="${escapeHtml(cname)}">Add to Plan</button>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }
    gapDiagnosisEl.innerHTML = `
      <h3>The Diagnosis: Understanding the Performance Gap</h3>
      <p>${escapeHtml(primarySummary)}</p>
      ${issuesHtml || '<div class="meta">No role selected or no targets configured to compute gaps.</div>'}
    `;

    // Root Causes (Biases) - basic contextual placeholders; use AI details if available
    const biases = lastAnalysis?.biases || [
      { name: 'Avoidance Bias', impact: `This bias directly hinders a ${roleName}'s ability to effectively manage Conflict Resolution and provide Performance Feedback, leading to unresolved team issues.` }
    ];
    gapCausesEl.innerHTML = `
      <h4>Potential Root Causes (Behavioral Biases): Impact on Role Performance</h4>
      ${biases.map(b=>`
        <div class="card mt">
          <div class="card-body">
            <h4>🚫 ${escapeHtml(b.name)}</h4>
            <div class="mt-sm">AI Analysis: ${escapeHtml(b.analysis || 'Tendency to avoid confronting uncomfortable situations, such as difficult conversations or delivering negative news.')}</div>
            <div class="mt-sm"><strong>Impact on Role:</strong> ${escapeHtml(b.impact)}</div>
            <div class="mt-sm"><button class="btn" data-open-nudges="${escapeHtml(b.name)}">Explore Nudges to Counteract ${escapeHtml(b.name)}</button></div>
          </div>
        </div>
      `).join('')}
    `;

    // Recommendations: KPIs and Nudges
    const kpisHtml = `
      <div class="card mt">
        <div class="card-body">
          <h4>Key Performance Indicators (KPIs) for ${escapeHtml(roleName)}'s Growth</h4>
          <div class="mt-sm">
            <h4>📊 Team Conflict Resolution Rate</h4>
            <div class="mt-sm">AI Analysis: Track the percentage of team conflicts successfully resolved by the supervisor within a specific timeframe.</div>
            <div class="mt-sm"><strong>Relevance to Role:</strong> A direct measure of the ${escapeHtml(roleName)}'s proficiency in Conflict Resolution and Team Management.</div>
            <div class="mt-sm"><button class="btn" data-open-kpis>Open KPIs in Playbook</button> <button class="btn" data-add-kpi>Add to Plan</button></div>
          </div>
        </div>
      </div>`;
    const nudgesHtml = `
      <div class="card mt">
        <div class="card-body">
          <h4>Actionable Interventions & Nudges: Supporting ${escapeHtml(roleName)}'s Development</h4>
          <div class="mt-sm">
            <h4>💡 Structured Feedback Sessions (Nudge)</h4>
            <div class="mt-sm">AI Analysis: Implement regular, structured one-on-one sessions focused on delivering balanced, actionable feedback.</div>
            <div class="mt-sm"><strong>Role Benefit:</strong> Directly develops the ${escapeHtml(roleName)}'s Giving Constructive Feedback skill and confidence, crucial for team growth.</div>
            <div class="mt-sm"><button class="btn" data-open-playbook-nudge>Open in Playbook</button> <button class="btn" data-add-nudge>Add to Plan</button></div>
          </div>
        </div>
      </div>`;
    gapRecsEl.innerHTML = kpisHtml + nudgesHtml;

    // Footer
    const statusMsg = analysisServiceIssue
      ? 'Note: Using fallback due to service issue.'
      : (lastAnalysis ? 'Ready.' : (selectedRole ? 'Waiting for AI analysis.' : 'Select a role to contextualize analysis.'));
    gapFooterEl.innerHTML = `
      <div class="meta">Status: ${statusMsg}</div>
      <div class="mt"><button class="btn" id="copy-all-to-plan">Copy all to Plan</button>
      <span class="meta" style="margin-left: .5rem;">GENERATED BY: AI-ASSISTED ANALYSIS</span></div>
    `;

    // Wire copy-to-plan (basic placeholder behavior)
    const copyBtn = document.getElementById('copy-all-to-plan');
    if (copyBtn) {
      copyBtn.onclick = ()=>{
        window.notify && window.notify('success', 'Report copied to Plan (placeholder)');
      };
    }
  }

  analyzeBtn.addEventListener('click', analyze);
  addRecBtn.addEventListener('click', addRecommended);
  toggleAI.addEventListener('change', loadAISuggestions);

  // Delegate clicks from empty-state CTA inside AI Summary
  aiSummaryEl.addEventListener('click', (e)=>{
    const btn = e.target.closest('[data-trigger-analyze]');
    if (btn) {
      analyzeBtn.click();
    }
  });

  loadSession();
  loadRoles();
  if (roleSelect) roleSelect.addEventListener('change', handleRoleChange);
  // Initial render
  renderGapReport();
})();
