(function(){
  const btn = document.getElementById('btn-session-restore');
  if (!btn) return;
  const overlay = document.getElementById('modal-overlay');
  const body = document.getElementById('modal-body');
  const title = document.getElementById('modal-title');

  async function loadJSON(url){ const r = await fetch(url); if (!r.ok) throw new Error('Request failed'); return r.json(); }
  async function postJSON(url, data){ const r = await fetch(url, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)}); if (!r.ok) throw new Error('Request failed'); return r.json(); }

  async function openRestore(){
    title.textContent = 'Restore Session';
    body.innerHTML = 'Loading...';
    overlay.classList.remove('hidden');
    overlay.setAttribute('aria-hidden','false');

    try {
      const [state, planCfgResp, eaResp, selResp] = await Promise.all([
        loadJSON('/api/context/framework/state'),
        loadJSON('/api/context/system?key=plan-config').catch(()=>({})),
        loadJSON('/api/context/system?key=event-analysis').catch(()=>({})),
        loadJSON('/api/context/metrics/list').catch(()=>({ items: [] })),
      ]);
      const planCfg = planCfgResp && (planCfgResp.value ?? planCfgResp);
      const eventAnalysis = eaResp && (eaResp.value ?? eaResp);
      const selectedItems = (selResp && selResp.items) || [];

      body.innerHTML = `
        <div class="field">
          <label><input type="checkbox" id="restore-framework" checked /> Restore framework & competencies</label>
          <label><input type="checkbox" id="restore-plan" ${planCfg?'checked':''} /> Restore plan configuration</label>
          <label><input type="checkbox" id="restore-ai" ${eventAnalysis?'checked':''} /> Restore AI event analysis</label>
          <label><input type="checkbox" id="restore-metrics" ${selectedItems.length?'checked':''} /> Restore selected metrics <span class="meta">(${selectedItems.length})</span></label>
        </div>
        <div class="actions">
          <button class="btn primary" id="restore-apply">Apply</button>
        </div>
      `;

      document.getElementById('restore-apply').addEventListener('click', async ()=>{
        try {
          window.dispatchEvent(new Event('context:saving'));
          const tasks = [];
          if (document.getElementById('restore-framework').checked) {
            // nothing to post specifically; your backend should already have state. Here we'd no-op or nudge state.
            tasks.push(Promise.resolve());
          }
          if (document.getElementById('restore-plan').checked && planCfg) {
            tasks.push(postJSON('/api/context/system', { key: 'plan-config', value: planCfg }));
          }
          if (document.getElementById('restore-ai').checked && eventAnalysis) {
            tasks.push(postJSON('/api/context/system', { key: 'event-analysis', value: eventAnalysis }));
          }
          await Promise.all(tasks);
          // Restore metrics selection sequentially for clearer progress
          if (document.getElementById('restore-metrics').checked && selectedItems.length) {
            const progress = document.createElement('div');
            progress.className = 'mt';
            body.appendChild(progress);
            let done = 0;
            for (const item of selectedItems) {
              progress.textContent = `Restoring metrics... ${done}/${selectedItems.length}`;
              const id = item.id || item.metric_id || item;
              if (!id) { done++; continue; }
              try { await postJSON('/api/context/metrics/select', { metric_id: id, source: 'session_restore' }); }
              catch { /* ignore failures per item */ }
              done++;
            }
            progress.textContent = `Restoring metrics... ${selectedItems.length}/${selectedItems.length}`;
          }
          window.dispatchEvent(new Event('context:saved'));
          window.notify && window.notify('success', 'Session restored');
        } catch (e) {
          window.dispatchEvent(new Event('context:error'));
          window.notify && window.notify('error', 'Failed to restore');
        }
      }, { once: true });

    } catch (e) {
      body.innerHTML = `<div class="error">Failed to load session for restore</div>`;
    }
  }

  btn.addEventListener('click', openRestore);
})();
