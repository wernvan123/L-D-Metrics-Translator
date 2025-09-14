(function(){
  const q = id => document.getElementById(id);

  async function getJSON(url){ const r = await fetch(url); return r.json(); }
  async function postJSON(url, body){ const r = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)}); return r.json(); }

  const titleEl = q('report-title');
  const typeEl = q('report-type');
  const incAISumEl = q('include-ai-summary');
  const incMetricsEl = q('include-metrics');

  const selectedMetricsEl = q('selected-metrics');
  const aiSugEl = q('ai-suggestions');
  const fwkSummaryEl = q('framework-summary');
  const fwkTreeEl = q('framework-tree');
  const progressEl = q('report-progress');
  const historyEl = q('report-history');
  const fwkSelectEl = q('framework-select');
  const setFwkBtn = q('set-framework');

  const saveBtn = q('save-plan-config');
  const genBtn = q('generate-report');
  const toggleAI = q('toggle-ai-suggestions');

  let frameworkState = null;
  let aiSuggestions = [];

  async function populateFrameworkOptions(currentId){
    if (!fwkSelectEl) return;
    let frameworks = [];
    try {
      const r = await getJSON('/api/frameworks');
      frameworks = (r && r.items) || [];
    } catch {}
    if (!frameworks.length) {
      // Fallback to a minimal list for local mocks
      frameworks = [
        { id: 'fwk-001', name: "L&D Core Competencies" },
      ];
    }
    fwkSelectEl.innerHTML = '<option value="">— Choose —</option>' + frameworks.map(f=>`<option value="${f.id}">${f.name}</option>`).join('');
    if (currentId) {
      const opt = Array.from(fwkSelectEl.options).find(o=>o.value===currentId);
      if (opt) fwkSelectEl.value = currentId;
    }
    // store last loaded list for lookup when setting
    fwkSelectEl._frameworks = frameworks;
  }

  async function loadState(){
    try {
      frameworkState = await getJSON('/api/context/framework/state');
      renderFrameworkSummary(frameworkState);
      renderSelectedMetrics(frameworkState);
      try { await loadFrameworkTree(frameworkState.framework_id); } catch {}
      try { await loadPlanConfig(); } catch {}
      try { populateFrameworkOptions(frameworkState.framework_id); } catch {}
    } catch (e) {
      fwkSummaryEl.innerHTML = '<div class="error">Unable to load context.</div>';
      window.notify && window.notify('error', 'Unable to load context');
    }
  }

  function renderFrameworkSummary(s){
    fwkSummaryEl.innerHTML = `
      <div><strong>Framework:</strong> ${s.framework_name || '—'}</div>
      <div><strong>Active competencies:</strong> ${(s.active_competencies||[]).join(', ') || '—'}</div>
      <div><strong>Selected metrics:</strong> ${s.selected_metrics_count || 0}</div>
    `;
  }

  async function renderSelectedMetrics(s){
    try {
      const r = await getJSON('/api/context/metrics/list');
      const items = (r && r.items) || [];
      if (!items.length) { selectedMetricsEl.textContent = 'No metrics selected yet.'; return; }
      selectedMetricsEl.innerHTML = `<ul class="list">${items.map(m=>`<li>${m.name} <button class='btn' data-view-metric='${m.id}'>View</button> <button class='btn' data-remove-metric='${m.id}'>Remove</button></li>`).join('')}</ul>`;
    } catch {
      selectedMetricsEl.innerHTML = `${s.selected_metrics_count || 0} metrics selected.`;
    }
  }

  async function loadFrameworkTree(frameworkId){
    if (!frameworkId) {
      fwkTreeEl.innerHTML = `
        <div class="empty-state">
          <p><strong>No framework selected yet.</strong></p>
          <p class="meta">Use the selector above to choose a framework and browse competencies and metrics.</p>
        </div>
      `;
      return;
    }
    try {
      const res = await fetch(`/api/frameworks/${encodeURIComponent(frameworkId)}/tree`);
      if (!res.ok) throw new Error('tree not available');
      const tree = await res.json();
      fwkTreeEl.innerHTML = renderTree(tree);
    } catch {
      fwkTreeEl.textContent = 'Framework tree not available.';
      window.notify && window.notify('error', 'Framework tree not available');
    }
  }

  function renderTree(tree){
    if (!tree || !tree.competencies) return '—';
    return `<ul class="list">${tree.competencies.map(c=>`<li><strong>${c.name}</strong>${renderMetrics(c.metrics||[])}${c.children?renderChildren(c.children):''}</li>`).join('')}</ul>`;
  }
  function renderChildren(children){
    return `<ul class="list">${children.map(ch=>`<li><strong>${ch.name}</strong>${renderMetrics(ch.metrics||[])}</li>`).join('')}</ul>`;
  }
  function renderMetrics(metrics){
    if (!metrics.length) return '';
    return `<ul class="list">${metrics.map(m=>{
      const id = m.id||m.metric_id||m;
      const name = m.name || m;
      return `<li>${name} <button class='btn' data-add-metric='${id}'>Add</button> <button class='btn' data-view-metric='${id}'>View</button></li>`;
    }).join('')}</ul>`;
  }

  async function loadPlanConfig(){
    try {
      const res = await fetch('/api/context/system?key=plan-config');
      if (!res.ok) return; // optional
      const data = await res.json();
      const cfg = data && (data.value || data);
      if (!cfg) return;
      if (cfg.title) titleEl.value = cfg.title;
      if (cfg.report_type) typeEl.value = cfg.report_type;
      if (typeof cfg.include_ai_summary === 'boolean') incAISumEl.checked = cfg.include_ai_summary;
      if (typeof cfg.include_metrics === 'boolean') incMetricsEl.checked = cfg.include_metrics;
    } catch {}
  }

  async function savePlanConfig(){
    const cfg = {
      title: titleEl.value,
      report_type: typeEl.value,
      include_ai_summary: incAISumEl.checked,
      include_metrics: incMetricsEl.checked,
      ts: new Date().toISOString(),
    };
    try {
      window.dispatchEvent(new Event('context:saving'));
      await postJSON('/api/context/system', { key: 'plan-config', value: cfg });
      window.dispatchEvent(new Event('context:saved'));
      window.notify && window.notify('success', 'Plan configuration saved');
    } catch {
      window.dispatchEvent(new Event('context:error'));
      window.notify && window.notify('error', 'Failed to save plan configuration');
    }
  }

  async function generateReport(){
    const payload = {
      title: titleEl.value || 'Development Plan',
      report_type: typeEl.value || 'comprehensive',
      selected_framework: frameworkState && frameworkState.framework_id,
      active_competencies: frameworkState && frameworkState.active_competencies,
      include_ai_summary: incAISumEl.checked,
      include_metrics: incMetricsEl.checked,
    };
    try {
      progressEl.textContent = 'Starting report...';
      window.notify && window.notify('info', 'Starting PDF generation');
      const res = await fetch('/api/dynamic-reports', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
      if (!res.ok) throw new Error('Report API unavailable');
      const { job_id } = await res.json();
      await pollReport(job_id);
    } catch (e) {
      progressEl.innerHTML = '<div class="error">'+(e.message||'Unable to start report.')+'</div>';
      window.notify && window.notify('error', 'Unable to start report');
    }
  }

  async function pollReport(jobId){
    progressEl.textContent = 'Working...';
    const poll = async () => {
      const r = await fetch(`/api/dynamic-reports/${encodeURIComponent(jobId)}/status`);
      if (!r.ok) throw new Error('Polling failed');
      const data = await r.json();
      if (data.status === 'completed') {
        progressEl.innerHTML = `<a class="btn primary" href="${data.download_url}" target="_blank">Download PDF</a>`;
        appendHistory(data);
        window.notify && window.notify('success', 'Report ready');
      } else if (data.status === 'failed') {
        progressEl.innerHTML = '<div class="error">Report failed.</div>';
        window.notify && window.notify('error', 'Report failed');
      } else {
        progressEl.textContent = `Progress: ${data.progress||0}%`;
        setTimeout(poll, 1200);
      }
    };
    try { await poll(); } catch(e){ progressEl.innerHTML = '<div class="error">'+(e.message||'Polling error')+'</div>'; }
  }

  function appendHistory(entry){
    const div = document.createElement('div');
    div.className = 'mt';
    div.innerHTML = `<div><strong>Report:</strong> ${entry.title || 'PDF'} — <a href="${entry.download_url}" target="_blank">Download</a></div>`;
    historyEl.prepend(div);
  }

  async function onTreeClick(e){
    const btn = e.target.closest('[data-add-metric]');
    if (!btn) return;
    const id = btn.getAttribute('data-add-metric');
    try {
      await postJSON('/api/context/metrics/select', { metric_id: id, source: 'plan_builder_tree' });
      window.dispatchEvent(new Event('context:saved'));
      frameworkState.selected_metrics_count = (frameworkState.selected_metrics_count||0) + 1;
      renderSelectedMetrics(frameworkState);
    } catch { window.dispatchEvent(new Event('context:error')); }
  }

  async function loadAISuggestions(){
    if (!toggleAI.checked) { aiSuggestions = []; aiSugEl.textContent = '—'; return; }
    try {
      const ctx = frameworkState || await getJSON('/api/context/framework/state');
      const r = await fetch('/api/smart-recommendations/generate', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ type: 'metric', session_context: ctx, scope: 'plan-builder' }) });
      if (!r.ok) throw new Error('AI not available');
      const data = await r.json();
      aiSuggestions = data.recommendations || [];
      aiSugEl.innerHTML = (aiSuggestions.length? `<ul class="list">${aiSuggestions.map(s=>{
        const id = s.id || s.metric_id;
        const name = s.name || id;
        return `<li>${name} <button class='btn' data-commit='${id}'>Add</button> <button class='btn' data-view-metric='${id}'>View</button></li>`;
      }).join('')}</ul>` : '—');
      // view interaction
      try { await postJSON('/api/smart-recommendations/interact', { action: 'view', scope: 'plan-builder' }); } catch {}
    } catch {
      aiSugEl.textContent = '—';
      window.notify && window.notify('error', 'AI suggestions not available');
    }
  }

  async function onAISuggestionClick(e){
    const btn = e.target.closest('[data-commit]');
    if (!btn) return;
    const id = btn.getAttribute('data-commit');
    try {
      await postJSON('/api/context/metrics/select', { metric_id: id, source: 'plan_builder_ai' });
      window.dispatchEvent(new Event('context:saved'));
      frameworkState.selected_metrics_count = (frameworkState.selected_metrics_count||0) + 1;
      renderSelectedMetrics(frameworkState);
      try { await postJSON('/api/smart-recommendations/interact', { recommendation_id: id, action: 'commit', scope: 'plan-builder' }); } catch {}
      window.notify && window.notify('success', 'Metric added from AI');
    } catch { window.dispatchEvent(new Event('context:error')); }
  }

  saveBtn.addEventListener('click', savePlanConfig);
  genBtn.addEventListener('click', generateReport);
  fwkTreeEl.addEventListener('click', onTreeClick);
  q('toggle-ai-suggestions').addEventListener('change', loadAISuggestions);
  aiSugEl.addEventListener('click', onAISuggestionClick);

  // Set framework from selector
  if (setFwkBtn) {
    setFwkBtn.addEventListener('click', async ()=>{
      const id = fwkSelectEl && fwkSelectEl.value;
      if (!id) { window.notify && window.notify('error', 'Please choose a framework'); return; }
      const frameworks = (fwkSelectEl && fwkSelectEl._frameworks) || [];
      const found = frameworks.find(f=>f.id===id) || { id, name: id };
      try {
        window.dispatchEvent(new Event('context:saving'));
        await postJSON('/api/context/framework/state', { framework_id: id, framework_name: found.name, active_competencies: [] });
        frameworkState = await getJSON('/api/context/framework/state');
        renderFrameworkSummary(frameworkState);
        await loadFrameworkTree(id);
        window.dispatchEvent(new Event('context:saved'));
        window.notify && window.notify('success', 'Framework set');
      } catch {
        window.dispatchEvent(new Event('context:error'));
        window.notify && window.notify('error', 'Failed to set framework');
      }
    });
  }

  // Handle remove from selection
  selectedMetricsEl.addEventListener('click', async (e)=>{
    const btn = e.target.closest('[data-remove-metric]');
    if (!btn) return;
    const id = btn.getAttribute('data-remove-metric');
    try {
      await postJSON('/api/context/metrics/deselect', { metric_id: id });
      window.dispatchEvent(new Event('context:saved'));
      // refresh both state count and list
      try { frameworkState.selected_metrics_count = Math.max(0, (frameworkState.selected_metrics_count||1) - 1); } catch {}
      await renderSelectedMetrics(frameworkState);
      window.notify && window.notify('success', 'Metric removed');
    } catch {
      window.dispatchEvent(new Event('context:error'));
      window.notify && window.notify('error', 'Failed to remove metric');
    }
  });

  loadState();
})();
