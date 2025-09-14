(function(){
  const q = id => document.getElementById(id);
  const sessionEl = q('session-context');
  const aiSummaryEl = q('ai-summary');
  const aiDriversEl = q('ai-drivers');
  const recMetricsEl = q('recommended-metrics');
  const analyzeBtn = q('analyze-btn');
  const addRecBtn = q('add-recommended-btn');
  const toggleAI = q('toggle-ai-suggestions');

  let lastAnalysis = null;
  let aiSuggestions = [];

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
      if (!res.ok) throw new Error('Analysis endpoint returned an error');
      const data = await res.json();
      lastAnalysis = data;
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
})();
