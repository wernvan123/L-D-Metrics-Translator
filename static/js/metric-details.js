// Global metric details modal controller
(function(){
  const overlay = document.getElementById('modal-overlay');
  const body = document.getElementById('modal-body');
  const closeBtn = document.getElementById('modal-close');

  if (!overlay || !body || !closeBtn) return;

  function show(html){
    body.innerHTML = html || '';
    overlay.classList.remove('hidden');
    overlay.setAttribute('aria-hidden', 'false');
  }
  function hide(){
    overlay.classList.add('hidden');
    overlay.setAttribute('aria-hidden', 'true');
  }

  async function openMetricDetails(metricId){
    if (!metricId) return;
    try {
      body.innerHTML = 'Loading...';
      const r = await fetch(`/api/metrics/${encodeURIComponent(metricId)}`);
      if (!r.ok) throw new Error('Failed to load metric');
      const m = await r.json();
      const html = renderMetric(m);
      show(html);
    } catch (e) {
      body.innerHTML = `<div class="error">${e.message || 'Unable to load metric details'}</div>`;
      show();
    }
  }

  function renderMetric(m){
    const tags = (m.tags||[]).map(t=>`<span class='badge'>${t}</span>`).join(' ');
    const meta = `
      <div class="meta">Category: ${m.category||'—'} | Type: ${m.type||'—'} | ID: ${m.id||m.metric_id||'—'}</div>
    `;
    const quick = `
      <div class="mt">
        <button class="btn primary" data-quick-add="${m.id||m.metric_id}">Add to Selection</button>
      </div>
    `;
    return `
      <div>
        <h4>${m.name||'Metric'}</h4>
        ${meta}
        <p>${m.description||'No description available.'}</p>
        <div>${tags}</div>
        ${quick}
      </div>
    `;
  }

  // Global delegation for opening
  document.addEventListener('click', async (e)=>{
    const btn = e.target.closest('[data-view-metric]');
    if (btn) {
      e.preventDefault();
      const id = btn.getAttribute('data-view-metric');
      show('');
      await openMetricDetails(id);
      return;
    }
    const add = e.target.closest('[data-quick-add]');
    if (add) {
      const id = add.getAttribute('data-quick-add');
      try {
        await fetch('/api/context/metrics/select', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ metric_id: id, source: 'metric_details_modal' }) });
        window.dispatchEvent(new Event('context:saved'));
        window.notify && window.notify('success', 'Metric added');
      } catch {
        window.dispatchEvent(new Event('context:error'));
        window.notify && window.notify('error', 'Failed to add metric');
      }
    }
  });

  overlay.addEventListener('click', (e)=>{
    if (e.target === overlay) hide();
  });
  closeBtn.addEventListener('click', hide);
  document.addEventListener('keydown', (e)=>{
    if (e.key === 'Escape' && !overlay.classList.contains('hidden')) hide();
  });
})();
