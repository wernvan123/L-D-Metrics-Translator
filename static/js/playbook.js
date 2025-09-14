(function(){
  const playbookTreeEl = document.getElementById('playbook-tree');
  const activeSelEl = document.getElementById('active-selections');
  const toggleAI = document.getElementById('toggle-ai-suggestions');
  const suggestionsEl = document.getElementById('playbook-suggestions');

  let frameworkState = null;

  async function getJSON(url){ const r = await fetch(url); return r.json(); }
  async function postJSON(url, body){ const r = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)}); return r.json(); }

  async function init(){
    try {
      frameworkState = await getJSON('/api/context/framework/state');
      renderActiveSelections(frameworkState);
      await loadPlaybook(frameworkState.framework_id);
    } catch (e) {
      playbookTreeEl.innerHTML = '<div class="error">Unable to load playbook.</div>';
      window.notify && window.notify('error', 'Unable to load playbook');
    }
  }

  async function loadPlaybook(frameworkId){
    if (!frameworkId) {
      playbookTreeEl.innerHTML = `
        <div class="empty-state">
          <p><strong>No framework selected yet.</strong></p>
          <p class="meta">Choose a framework to explore competencies and metrics.</p>
          <div class="mt">
            <a class="btn primary" href="/plan-builder">Go to Plan Builder</a>
          </div>
        </div>
      `;
      return;
    }
    try {
      const r = await fetch(`/api/frameworks/${encodeURIComponent(frameworkId)}/tree`);
      if (!r.ok) throw new Error('Unavailable');
      const tree = await r.json();
      playbookTreeEl.innerHTML = renderPlaybookTree(tree);
    } catch(e){
      playbookTreeEl.textContent = 'Playbook not available.';
      window.notify && window.notify('error', 'Playbook not available');
    }
  }

  function renderPlaybookTree(tree){
    if (!tree || !tree.competencies) return '—';
    return `<ul class="list">${tree.competencies.map(c=>`<li>
      <div style="display:flex;align-items:center;gap:8px;"><strong>${c.name}</strong> <button class='btn' data-set-competency='${c.id||c.name}'>Set Active</button></div>
      ${renderConcepts(c.concepts||c.drivers||[])}
      ${renderMetrics(c.metrics||[])}
    </li>`).join('')}</ul>`;
  }

  function renderConcepts(nodes){
    if (!nodes || !nodes.length) return '';
    return `<ul class="list">${nodes.map(n=>`<li><strong>${n.name||n}</strong> ${renderMetrics(n.metrics||[])} </li>`).join('')}</ul>`;
  }

  function renderMetrics(metrics){
    if (!metrics || !metrics.length) return '';
    return `<ul class="list">${metrics.map(m=>`<li>${m.name||m} <button class='btn' data-add-metric='${m.id||m.metric_id||m}'>Add</button> <button class='btn' data-view-metric='${m.id||m.metric_id||m}'>View</button></li>`).join('')}</ul>`;
  }

  function renderActiveSelections(s){
    activeSelEl.innerHTML = `
      <div><strong>Framework:</strong> ${s.framework_name || '—'}</div>
      <div><strong>Active competencies:</strong> ${(s.active_competencies||[]).join(', ') || '—'}</div>
      <div><strong>Selected metrics:</strong> ${s.selected_metrics_count || 0}</div>
    `;
  }

  async function onTreeClick(e){
    const addBtn = e.target.closest('[data-add-metric]');
    if (addBtn) {
      const id = addBtn.getAttribute('data-add-metric');
      try {
        await postJSON('/api/context/metrics/select', { metric_id: id, source: 'playbook' });
        window.dispatchEvent(new Event('context:saved'));
        frameworkState.selected_metrics_count = (frameworkState.selected_metrics_count||0) + 1;
        renderActiveSelections(frameworkState);
      } catch { window.dispatchEvent(new Event('context:error')); }
      return;
    }
    const setComp = e.target.closest('[data-set-competency]');
    if (setComp) {
      const id = setComp.getAttribute('data-set-competency');
      try {
        await postJSON('/api/context/framework/competencies', { competency_ids: [id], replace: false });
        window.dispatchEvent(new Event('context:saved'));
        frameworkState.active_competencies = Array.from(new Set([...(frameworkState.active_competencies||[]), id]));
        renderActiveSelections(frameworkState);
      } catch { window.dispatchEvent(new Event('context:error')); }
      return;
    }
  }

  async function loadAISuggestions(){
    if (!toggleAI.checked) { suggestionsEl.textContent = '—'; return; }
    try {
      const ctx = frameworkState || await getJSON('/api/context/framework/state');
      const r = await fetch('/api/smart-recommendations/generate', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ type: 'metric', session_context: ctx, scope: 'playbook' }) });
      if (!r.ok) throw new Error('AI not available');
      const data = await r.json();
      const recs = data.recommendations||[];
      suggestionsEl.innerHTML = (recs.length? `<ul class="list">${recs.map(s=>{
        const id = s.id || s.metric_id;
        const name = s.name || id;
        return `<li>${name} <button class='btn' data-commit='${id}'>Add</button> <button class='btn' data-view-metric='${id}'>View</button></li>`;
      }).join('')}</ul>` : '—');
    } catch {
      suggestionsEl.textContent = '—';
      window.notify && window.notify('error', 'AI suggestions not available');
    }
  }

  async function onSuggestionsClick(e){
    const btn = e.target.closest('[data-commit]');
    if (!btn) return;
    const id = btn.getAttribute('data-commit');
    try {
      await postJSON('/api/context/metrics/select', { metric_id: id, source: 'playbook_ai' });
      window.dispatchEvent(new Event('context:saved'));
      frameworkState.selected_metrics_count = (frameworkState.selected_metrics_count||0) + 1;
      renderActiveSelections(frameworkState);
    } catch { window.dispatchEvent(new Event('context:error')); }
  }

  playbookTreeEl.addEventListener('click', onTreeClick);
  toggleAI.addEventListener('change', loadAISuggestions);
  suggestionsEl.addEventListener('click', onSuggestionsClick);

  init();
})();
