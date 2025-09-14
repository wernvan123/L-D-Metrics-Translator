(function(){
  const btn = document.getElementById('btn-context-summary');
  if (!btn) return;
  const overlay = document.getElementById('modal-overlay');
  const body = document.getElementById('modal-body');
  const title = document.getElementById('modal-title');

  async function loadJSON(url){ const r = await fetch(url); if (!r.ok) throw new Error('Request failed'); return r.json(); }

  async function openSummary(){
    title.textContent = 'Context Summary';
    body.innerHTML = 'Loading...';
    overlay.classList.remove('hidden');
    overlay.setAttribute('aria-hidden','false');
    try {
      const [state, planCfgResp, eaResp] = await Promise.all([
        loadJSON('/api/context/framework/state'),
        loadJSON('/api/context/system?key=plan-config').catch(()=>({})),
        loadJSON('/api/context/system?key=event-analysis').catch(()=>({})),
      ]);
      const planCfg = planCfgResp && (planCfgResp.value ?? planCfgResp);
      const eventAnalysis = eaResp && (eaResp.value ?? eaResp);

      const comps = (state.active_competencies||[]).join(', ') || '—';
      const metricsCount = state.selected_metrics_count || 0;

      body.innerHTML = `
        <div class="grid two">
          <div>
            <div class="meta">Framework</div>
            <div><strong>${state.framework_name || '—'}</strong></div>
            <div class="meta mt">Active Competencies</div>
            <div>${comps}</div>
            <div class="meta mt">Selected Metrics</div>
            <div>${metricsCount}</div>
          </div>
          <div>
            <div class="meta">Plan Config</div>
            <pre style="white-space:pre-wrap;background:#f7f7f9;padding:8px;border-radius:8px;">${planCfg?JSON.stringify(planCfg,null,2):'—'}</pre>
            <div class="meta mt">AI Event Analysis</div>
            <pre style="white-space:pre-wrap;background:#f7f7f9;padding:8px;border-radius:8px;">${eventAnalysis?JSON.stringify(eventAnalysis,null,2):'—'}</pre>
          </div>
        </div>
      `;
    } catch (e) {
      body.innerHTML = `<div class="error">Failed to load summary</div>`;
    }
  }

  btn.addEventListener('click', openSummary);
})();
