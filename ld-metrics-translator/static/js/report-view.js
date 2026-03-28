/* Single report view with robust fallbacks */

const ReportView = (() => {
  async function fetchJSON(url){ const r = await fetch(url, { headers: { 'Accept':'application/json' } }); if(!r.ok) throw new Error(`HTTP ${r.status}`); return await r.json(); }
  function setStatus(msg){ const el = document.getElementById('rv-status'); if(!el) return; if(!msg){ el.style.display='none'; el.textContent=''; return; } el.style.display='block'; el.textContent = msg; }
  function esc(s){ return (s||'').toString().replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
  function pdfUrlFromPath(p){
    try{
      const s = (p||'').toString();
      if(!s) return '';
      const norm = s.replace(/\\/g, '/');
      const low = norm.toLowerCase();
      const marker = '/static/reports/';
      const idx = low.lastIndexOf(marker);
      if(idx >= 0){
        return norm.slice(idx);
      }
      if(low.startsWith('static/reports/')) return `/${norm}`;
      if(low.startsWith('/static/reports/')) return norm;
      return '';
    }catch{ return ''; }
  }
  function richText(val){
    const s = (val == null) ? '' : String(val);
    const trimmed = s.trim();
    if(!trimmed) return '';
    const lines = trimmed.replace(/\r\n/g, '\n').split('\n');
    const blocks = [];
    let cur = [];
    for(const ln of lines){
      if(!ln.trim()){
        if(cur.length){ blocks.push(cur); cur = []; }
        continue;
      }
      cur.push(ln);
    }
    if(cur.length) blocks.push(cur);

    function blockHtml(blockLines){
      const isBullets = blockLines.length > 1 && blockLines.every(l => /^\s*(?:•|-|\*)\s+/.test(l));
      if(isBullets){
        const items = blockLines.map(l => {
          const item = l.replace(/^\s*(?:•|-|\*)\s+/, '');
          return `<li>${esc(item)}</li>`;
        }).join('');
        return `<ul class="rv-list">${items}</ul>`;
      }
      if(blockLines.length === 1 && /:\s*$/.test(blockLines[0])){
        return `<div class="rv-subhead">${esc(blockLines[0])}</div>`;
      }
      const para = esc(blockLines.join('\n')).replace(/\n/g, '<br/>');
      return `<p>${para}</p>`;
    }

    return blocks.map(blockHtml).join('');
  }
  function section(title, body){
    const html = richText(body);
    if(!html) return '';
    return `<div class="rp-section"><div class="rp-section-title">${esc(title)}</div><div class="rp-section-body">${html}</div></div>`;
  }
  function renderPreview(r){
    const parts = [];
    parts.push('<div class="report-preview">');
    parts.push(section('Executive Summary', r.executive_summary));
    parts.push(section('Strategy Context', r.strategy_context));
    parts.push(section('Metric Analysis', r.metric_analysis));
    parts.push(section('AI Insights', r.ai_insights));
    parts.push(section('Implementation Roadmap', r.implementation_roadmap));
    parts.push(section('Success Metrics', r.success_metrics));
    parts.push(section('Appendices', r.appendices));
    parts.push('</div>');
    return parts.join('');
  }
  function shortId(s){
    try{
      const v = (s||'').toString();
      if(!v) return '';
      return v.length <= 10 ? v : v.slice(0, 10);
    }catch{ return ''; }
  }
  function fmtSession(s){
    const sid = shortId(s);
    return sid ? `s${sid}` : '';
  }
  async function loadWorkspaceLabel(){
    try{
      const st = await fetchJSON('/api/workspace/state');
      const c = st && st.active_client ? (st.active_client.name || '') : '';
      const e = st && st.active_engagement ? (st.active_engagement.name || '') : '';
      return (c && e) ? `${c} / ${e}` : '';
    }catch{ return ''; }
  }

  async function load(){
    const id = window.__REPORT_ID__;
    const titleEl = document.getElementById('rv-title');
    const metaEl = document.getElementById('rv-meta');
    const contEl = document.getElementById('rv-content');
    try{
      setStatus('Loading report...');
      const [d, wsLabel] = await Promise.all([
        fetchJSON(`/api/reports/${id}?include=content`),
        loadWorkspaceLabel(),
      ]);
      const r = d.report || {};
      titleEl.textContent = r.title || `Report ${id}`;
      const ts = r.created_date || r.generated_date || '';
      const role = (r.meta && r.meta.role_profile && r.meta.role_profile.name) ? ` • Role: ${r.meta.role_profile.name}` : '';
      const sid = fmtSession(r.session_id);
      const ws = wsLabel ? ` • ${wsLabel}` : '';
      const sidPart = sid ? ` • Session: ${sid}` : '';
      metaEl.textContent = `${ts}${role}${ws}${sidPart}`;
      const pdfUrl = pdfUrlFromPath(r.pdf_path);
      const downloadUrl = (r.id != null) ? `/api/dynamic-reports/${encodeURIComponent(String(r.id))}/download` : '';
      const previewHtml = renderPreview(r);
      const raw = `<details class="mt"><summary>Raw data</summary><pre class="code">${esc(JSON.stringify(r, null, 2))}</pre></details>`;
      const actions = (pdfUrl || downloadUrl)
        ? `<div class="rp-actions" style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px;">`+
          (pdfUrl ? `<a class="btn btn-sm" href="${esc(pdfUrl)}" target="_blank" rel="noopener">Open PDF</a>` : '')+
          (downloadUrl ? `<a class="btn btn-sm" href="${esc(downloadUrl)}">Download PDF</a>` : '')+
        `</div>`
        : '';
      contEl.innerHTML = actions + (r.content_html || previewHtml || '') + raw;
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

try{ window.ReportView = ReportView; }catch(e){}

try{
  const boot = () => {
    try{
      if (typeof ReportView !== 'undefined' && ReportView && typeof ReportView.init === 'function') {
        ReportView.init();
      }
    } catch (e) {}
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
}catch(e){}
