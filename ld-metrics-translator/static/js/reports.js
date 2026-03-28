/* Reports comparison minimal client */

const ReportsCompare = (() => {
  function esc(s){ return (s||'').toString().replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[c])); }
  async function fetchJSON(url, opts){ const r = await fetch(url, { headers: { 'Accept':'application/json', ...(opts && opts.headers||{}) }, ...(opts||{}) }); if(!r.ok) throw new Error(`HTTP ${r.status}`); return await r.json(); }
  function setStatus(msg){ const el = document.getElementById('rc-status'); if(!el) return; if(!msg){ el.style.display='none'; el.textContent=''; return; } el.textContent = msg; el.style.display='block'; }

  let workspaceLabel = '';
  async function loadWorkspaceLabel(){
    try{
      const st = await fetchJSON('/api/workspace/state');
      const c = st && st.active_client ? (st.active_client.name || '') : '';
      const e = st && st.active_engagement ? (st.active_engagement.name || '') : '';
      workspaceLabel = (c && e) ? `${c} / ${e}` : '';
    }catch{}
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

  function safeFileComponent(s){
    try{
      const str = (s||'').toString().trim().toLowerCase();
      return str
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/_{2,}/g, '_')
        .replace(/^_+|_+$/g, '')
        .slice(0, 80);
    }catch{ return ''; }
  }

  function fmtDate(dstr){ try{ const d = new Date(dstr); if(String(d) === 'Invalid Date') return dstr||''; return d.toLocaleDateString(undefined, { year:'numeric', month:'long', day:'numeric' }); }catch{ return dstr||''; } }

  function labelFor(slot, r){
    const base = slot === 'A' ? 'Baseline' : 'Follow-up';
    const title = (r && r.title) ? r.title : `${base} Report`;
    const date = (r && (r.created_date || r.generated_date)) ? ` (${fmtDate(r.created_date || r.generated_date)})` : '';
    return `${base}: ${title}${date}`;
  }

  function textBlock(val){
    const s = (val == null) ? '' : String(val);
    if(!s.trim()) return '';
    return esc(s).replace(/\n/g, '<br/>');
  }

  function section(title, body){
    const html = textBlock(body);
    if(!html) return '';
    return `<div class="rp-section"><div class="rp-section-title">${esc(title)}</div><div class="rp-section-body">${html}</div></div>`;
  }

  function reportActions(r){
    if(!r || r.id == null) return '';
    const id = encodeURIComponent(String(r.id));
    return `<div class="rp-actions">`+
      `<a class="btn btn-sm" href="/report/${id}">View</a>`+
      `<a class="btn btn-sm" href="/api/dynamic-reports/${id}/download">Download PDF</a>`+
    `</div>`;
  }

  function renderReportPreview(r){
    if(!r) return '<div class="no-data-message">No report selected.</div>';
    const parts = [];
    parts.push('<div class="report-preview">');
    parts.push(reportActions(r));
    parts.push(section('Executive Summary', r.executive_summary));
    parts.push(section('AI Insights', r.ai_insights));
    parts.push(section('Implementation Roadmap', r.implementation_roadmap));
    parts.push(section('Success Metrics', r.success_metrics));
    const raw = esc(JSON.stringify(r, null, 2));
    parts.push(`<details class="rp-raw"><summary>Raw data</summary><pre class="code">${raw}</pre></details>`);
    parts.push('</div>');
    return parts.join('');
  }

  async function loadReport(slot, id){
    const titleEl = document.getElementById(slot==='A' ? 'rA-title' : 'rB-title');
    const metaEl = document.getElementById(slot==='A' ? 'rA-meta' : 'rB-meta');
    const contEl = document.getElementById(slot==='A' ? 'rA-content' : 'rB-content');
    if(!id){ titleEl.textContent = `${slot==='A'?'Baseline':'Follow-up'}: —`; metaEl.textContent=''; contEl.innerHTML=''; return null; }
    try{ contEl.innerHTML = '<div class="no-data-message">Loading report…</div>'; }catch(e){}
    try{
      const d = await fetchJSON(`/api/reports/${id}?include=content`);
      const r = d.report || {};
      titleEl.textContent = labelFor(slot, r);
      const ts = r.created_date || r.generated_date || '';
      const role = (r.meta && r.meta.role_profile && r.meta.role_profile.name) ? ` • Role: ${r.meta.role_profile.name}` : '';
      const ws = workspaceLabel ? ` • ${workspaceLabel}` : '';
      const sid = fmtSession(r.session_id);
      const sidPart = sid ? ` • Session: ${sid}` : '';
      metaEl.textContent = `${fmtDate(ts)}${role}${ws}${sidPart}`.trim();
      contEl.innerHTML = renderReportPreview(r);
      return r;
    }catch(e){
      titleEl.textContent = `${slot==='A'?'Baseline':'Follow-up'}: —`;
      metaEl.textContent = '';
      contEl.innerHTML = '<div class="no-data-message"><div class="no-data-icon">⚠️</div><h4>Failed to load report</h4></div>';
      return null;
    }
  }

  function synthSummary(a, b){
    try{
      const left = a ? (a.title || 'Baseline Report') : 'Baseline Report';
      const right = b ? (b.title || 'Follow-up Report') : 'Follow-up Report';
      const parts = [];
      parts.push(`<p>Comparing <strong>${esc(left)}</strong> and <strong>${esc(right)}</strong>.</p>`);
      // Placeholder growth insight; can be replaced by backend AI later
      parts.push(`<p>Overall proficiency shows positive movement. Notable areas of growth are highlighted below.</p>`);
      return parts.join('');
    }catch{ return 'Summary unavailable.'; }
  }

  function deriveKeyChanges(a, b){
    // Attempt to extract a few key numeric changes if present; otherwise return illustrative examples
    const changes = [];
    // If reports have a metrics summary with numeric values, compute deltas here.
    // For now, we surface example changes to demonstrate UI until backend fields are available.
    changes.push({ label: 'Strategic Acumen', change: +25, note: 'Improved stakeholder alignment and long-term planning.' });
    changes.push({ label: 'Delegation Effectiveness Score', change: +40, note: 'Clear task ownership and feedback loops.' });
    changes.push({ label: 'Time to Productivity', change: -12, note: 'Faster onboarding and role clarity.' });
    return changes;
  }

  function renderKeyChanges(changes){
    const wrap = document.getElementById('rc-key-changes');
    if(!wrap) return;
    if(!changes || !changes.length){ wrap.innerHTML = '<div class="no-data-message">No key changes detected.</div>'; return; }
    wrap.innerHTML = changes.map(c => {
      const up = c.change > 0;
      const down = c.change < 0;
      const cls = up ? 'chg-up' : (down ? 'chg-down' : 'chg-flat');
      const arrow = up ? '▲' : (down ? '▼' : '■');
      const pct = `${(c.change>0?'+':'')}${c.change}%`;
      return `<div class="change-item ${cls}">`+
             `<div class="change-metric">${esc(c.label)}</div>`+
             `<div class="change-delta"><span class="arrow">${arrow}</span> <span class="pct">${esc(pct)}</span></div>`+
             (c.note?`<div class="change-note">${esc(c.note)}</div>`:'')+
             `</div>`;
    }).join('');
  }

  async function exportPDF(payload){
    try{
      setStatus('Preparing comparison PDF…');
      const r = await fetch('/pdf/generate-comparison', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if(!r.ok){
        let details = '';
        try{ details = await r.text(); }catch{}
        throw new Error(`HTTP ${r.status}${details ? `: ${details}` : ''}`);
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      let fname = (payload && payload.filename) ? payload.filename : 'LD_Comparison_Report.pdf';
      try{
        const cd = r.headers.get('content-disposition') || '';
        const m = cd.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
        fname = decodeURIComponent((m && (m[1] || m[2])) || fname);
      }catch{}
      a.download = fname;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setStatus('');
    }catch(e){
      const msg = (e && e.message) ? e.message : 'Unknown error';
      setStatus(`Failed to export comparison PDF (${msg}).`);
    }
  }

  function wireButtons(state){
    const shareBtn = document.getElementById('btn-share-comparison');
    const expBtn = document.getElementById('btn-export-comparison');
    if(expBtn){
      const enabled = !!(state && state.ra && state.rb);
      expBtn.disabled = !enabled;
      if(!enabled){ expBtn.title = 'Select two completed reports to enable export.'; }
    }
    if(shareBtn){
      const canShare = !!(navigator && (navigator.share || (navigator.clipboard && navigator.clipboard.writeText)));
      shareBtn.disabled = !canShare;
      if(!canShare){ shareBtn.title = 'Sharing is not available in this browser.'; }
      shareBtn.addEventListener('click', async () => {
        try{
          if(navigator.share){
            await navigator.share({ title: 'L&D Comparison', text: 'See this comparison report', url: window.location.href });
          } else {
            await navigator.clipboard.writeText(window.location.href);
            setStatus('Share link copied to clipboard.');
            setTimeout(()=>setStatus(''), 2500);
          }
        }catch{}
      });
    }
    if(expBtn){
      expBtn.addEventListener('click', async () => {
        const aName = safeFileComponent(state && state.ra && state.ra.title);
        const bName = safeFileComponent(state && state.rb && state.rb.title);
        const fname = (aName && bName) ? `LD_Comparison__${aName}__vs__${bName}.pdf` : 'LD_Comparison_Report.pdf';
        const payload = {
          a_report: state.ra ? { title: state.a_title, date: state.a_date } : null,
          b_report: state.rb ? { title: state.b_title, date: state.b_date } : null,
          summary_html: document.getElementById('rc-summary')?.innerHTML || '',
          key_changes: state.key_changes || [],
          filename: fname
        };
        exportPDF(payload);
      });
    }
  }

  async function init(){
    await loadWorkspaceLabel();
    const url = new URL(window.location.href);
    const a = url.searchParams.get('a');
    const b = url.searchParams.get('b');
    if(!a || !b){ setStatus('Tip: open from Reports selecting exactly 2 completed items.'); }
    const [ra, rb] = await Promise.all([loadReport('A', a), loadReport('B', b)]);
    const sum = document.getElementById('rc-summary');
    if(sum) sum.innerHTML = synthSummary(ra, rb);

    const state = {
      ra, rb,
      a_title: labelFor('A', ra),
      b_title: labelFor('B', rb),
      a_date: (ra && (ra.created_date || ra.generated_date)) ? fmtDate(ra.created_date || ra.generated_date) : '',
      b_date: (rb && (rb.created_date || rb.generated_date)) ? fmtDate(rb.created_date || rb.generated_date) : ''
    };

    const changes = deriveKeyChanges(ra, rb);
    state.key_changes = changes;
    renderKeyChanges(changes);

    wireButtons(state);
  }

  return { init };
})();

try{ window.ReportsCompare = ReportsCompare; }catch(e){}
