(function(){
  const btn = document.getElementById('btn-status-check');
  if (!btn) return;
  const overlay = document.getElementById('modal-overlay');
  const body = document.getElementById('modal-body');
  const title = document.getElementById('modal-title');

  async function ping(url, opts){
    try { const r = await fetch(url, opts || {}); return { ok: r.ok, status: r.status }; }
    catch (e) { return { ok: false, status: 'ERR' }; }
  }

  async function openStatus(){
    title.textContent = 'Endpoint Status Check';
    body.innerHTML = 'Checking...';
    overlay.classList.remove('hidden');
    overlay.setAttribute('aria-hidden','false');

    const checks = [
      { name: 'Framework State', method: 'GET', url: '/api/context/framework/state' },
      { name: 'Context System (GET)', method: 'GET', url: '/api/context/system?key=plan-config' },
      { name: 'Context System (POST)', method: 'POST', url: '/api/context/system', opts: { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ key:'_ping', value: Date.now() }) } },
      { name: 'Metrics Select', method: 'POST', url: '/api/context/metrics/select', opts: { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ metric_id: 'm-ping' }) } },
      { name: 'Framework Tree', method: 'GET', url: '/api/frameworks/fwk-001/tree' },
      { name: 'Smart Recs Generate', method: 'POST', url: '/api/smart-recommendations/generate', opts: { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ type:'metric', session_context:{}, scope:'status' }) } },
      { name: 'Reports Start', method: 'POST', url: '/api/dynamic-reports', opts: { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ title:'Ping' }) } },
    ];

    const results = [];
    for (const c of checks) {
      const res = await ping(c.url, c.opts);
      results.push({ name: c.name, status: res.status, ok: res.ok });
    }

    body.innerHTML = `
      <ul class="list">
        ${results.map(r=>`<li>${r.ok? '✅':'❌'} <strong>${r.name}</strong> — ${r.status}</li>`).join('')}
      </ul>
      <div class="mt"><em>Note:</em> Some POST checks may add a harmless ping record to your context store.</div>
    `;
  }

  btn.addEventListener('click', openStatus);

  // Reset demo session (only if button exists)
  const resetBtn = document.getElementById('btn-reset-demo');
  if (resetBtn) {
    resetBtn.addEventListener('click', async ()=>{
      try {
        await fetch('/api/demo/reset', { method:'POST' });
        window.notify && window.notify('success','Demo session reset');
        location.reload();
      } catch {
        window.notify && window.notify('error','Failed to reset demo');
      }
    });
  }
})();
