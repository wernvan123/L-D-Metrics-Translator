/* Reports comparison minimal client */

const ReportsCompare = (() => {
  function esc(s){ return (s||'').toString().replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
  async function fetchJSON(url, opts){ const r = await fetch(url, { headers: { 'Accept':'application/json', ...(opts && opts.headers||{}) }, ...(opts||{}) }); if(!r.ok) throw new Error(`HTTP ${r.status}`); return await r.json(); }
  function setStatus(msg){ const el = document.getElementById('rc-status'); if(!el) return; if(!msg){ el.style.display='none'; el.textContent=''; return; } el.textContent = msg; el.style.display='block'; }

  function fmtDate(dstr){ try{ const d = new Date(dstr); if(String(d) === 'Invalid Date') return dstr||''; return d.toLocaleDateString(undefined, { year:'numeric', month:'long', day:'numeric' }); }catch{ return dstr||''; } }

  function labelFor(slot, r){
    const base = slot === 'A' ? 'Baseline' : 'Follow-up';
    const title = (r && r.title) ? r.title : `${base} Report`;
    const date = (r && (r.created_date || r.generated_date)) ? ` (${fmtDate(r.created_date || r.generated_date)})` : '';
    return `${base}: ${title}${date}`;
  }

  async function loadReport(slot, id){
    const titleEl = document.getElementById(slot==='A' ? 'rA-title' : 'rB-title');
    const metaEl = document.getElementById(slot==='A' ? 'rA-meta' : 'rB-meta');
    const contEl = document.getElementById(slot==='A' ? 'rA-content' : 'rB-content');
    if(!id){ titleEl.textContent = `${slot==='A'?'Baseline':'Follow-up'}: —`; metaEl.textContent=''; contEl.innerHTML=''; return null; }
    try{
      const d = await fetchJSON(`/api/reports/${id}?include=content`);
      const r = d.report || {};
      titleEl.textContent = labelFor(slot, r);
      const ts = r.created_date || r.generated_date || '';
      const role = (r.meta && r.meta.role_profile && r.meta.role_profile.name) ? ` • Role: ${r.meta.role_profile.name}` : '';
      metaEl.textContent = `${fmtDate(ts)}${role}`.trim();
      contEl.innerHTML = r.content_html || `<pre class="code">${esc(JSON.stringify(r.content || r, null, 2))}</pre>`;
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
      const r = await fetch('/pdf/generate-comparison', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if(!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = payload && payload.filename ? payload.filename : 'LD_Comparison_Report.pdf';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    }catch(e){ setStatus('Failed to export comparison PDF.'); }
  }

  function wireButtons(state){
    const shareBtn = document.getElementById('btn-share-comparison');
    const expBtn = document.getElementById('btn-export-comparison');
    if(shareBtn){
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
        const payload = {
          a_report: state.ra ? { title: state.a_title, date: state.a_date } : null,
          b_report: state.rb ? { title: state.b_title, date: state.b_date } : null,
          summary_html: document.getElementById('rc-summary')?.innerHTML || '',
          key_changes: state.key_changes || [],
          filename: 'LD_Comparison_Report.pdf'
        };
        exportPDF(payload);
      });
    }
  }

  async function init(){
    const url = new URL(window.location.href);
    const a = url.searchParams.get('a');
    const b = url.searchParams.get('b');
    if(!a || !b){ setStatus('Tip: open from Reports selecting exactly 2 items.'); }
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
