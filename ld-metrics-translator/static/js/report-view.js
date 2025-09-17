/* Single report view with robust fallbacks */

const ReportView = (() => {
  async function fetchJSON(url){ const r = await fetch(url, { headers: { 'Accept':'application/json' } }); if(!r.ok) throw new Error(`HTTP ${r.status}`); return await r.json(); }
  function setStatus(msg){ const el = document.getElementById('rv-status'); if(!el) return; if(!msg){ el.style.display='none'; el.textContent=''; return; } el.style.display='block'; el.textContent = msg; }
  function esc(s){ return (s||'').toString().replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

  async function load(){
    const id = window.__REPORT_ID__;
    const titleEl = document.getElementById('rv-title');
    const metaEl = document.getElementById('rv-meta');
    const contEl = document.getElementById('rv-content');
    try{
      setStatus('Loading report...');
      const d = await fetchJSON(`/api/reports/${id}?include=content`);
      const r = d.report || {};
      titleEl.textContent = r.title || `Report ${id}`;
      const ts = r.created_date || r.generated_date || '';
      const role = (r.meta && r.meta.role_profile && r.meta.role_profile.name) ? ` • Role: ${r.meta.role_profile.name}` : '';
      metaEl.textContent = `${ts}${role}`;
      contEl.innerHTML = r.content_html || `<pre class="code">${esc(JSON.stringify(r.content || r, null, 2))}</pre>`;
      setStatus('');
    }catch(e){
      setStatus('Failed to load report via /api. Attempting fallback...');
      try {
        // Fallback: if dynamic content is unavailable, at least show basic stub
        const idStr = esc(String(id));
        titleEl.textContent = `Report ${idStr}`;
        metaEl.textContent = 'No API data available';
        contEl.innerHTML = '<div class="no-data-message"><div class="no-data-icon">⚠️</div><h4>Report content unavailable</h4><p>Please try again later.</p></div>';
      } catch {}
    }
  }

  function init(){ load(); }
  return { init };
})();
