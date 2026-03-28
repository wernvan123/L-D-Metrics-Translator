// Reports List page client logic
(function(){
  console.log('[ReportsList] script loaded');
  let allItems = [];
  let sortState = { by: 'date', dir: 'desc' }; // by: 'date'|'status', dir: 'asc'|'desc'
  let workspaceLabel = '';

  async function fetchJSON(url){
    const r = await fetch(url, { headers: { 'Accept': 'application/json' } });
    if (!r.ok) throw new Error('HTTP '+r.status);
    return r.json();
  }
  function esc(s){ return (s||'').toString().replace(/[&<>\"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
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
      const lbl = (c && e) ? `${c} / ${e}` : '';
      workspaceLabel = lbl;
      const meta = document.getElementById('reports-table-meta');
      if(meta && lbl){
        meta.textContent = `Workspace: ${lbl}`;
      }
    }catch{}
  }
  function fmtDate(s){
    if(!s) return '';
    // Accept "YYYY-MM-DD HH:MM:SS" or ISO strings
    const tryParse = (val)=>{
      const d = new Date(val.replace(' ', 'T'));
      return isNaN(d.getTime()) ? null : d;
    };
    const d = tryParse(s);
    if(!d) return esc(s);
    return d.toLocaleString(undefined, { year:'numeric', month:'short', day:'2-digit', hour:'2-digit', minute:'2-digit' });
  }
  function statusBadge(status){
    const st = String(status||'').toLowerCase();
    const cls = st==='completed' ? 'ok' : (st==='in_progress' || st==='queued' ? 'info' : (st==='failed' ? 'err' : 'muted'));
    const label = (st||'—').replace('_',' ');
    return `<span class="status-badge ${cls}">${esc(label)}</span>`;
  }

  function sortItems(items){
    const out = items.slice();
    if (sortState.by === 'date'){
      out.sort((a,b)=>{
        const ad = new Date((a.generated_date || a.created_date || '').replace(' ','T')).getTime() || 0;
        const bd = new Date((b.generated_date || b.created_date || '').replace(' ','T')).getTime() || 0;
        return sortState.dir === 'asc' ? (ad - bd) : (bd - ad);
      });
    } else if (sortState.by === 'status'){
      const order = { completed: 3, in_progress: 2, queued: 1, failed: 0 };
      out.sort((a,b)=>{
        const av = order[String(a.generation_status||'').toLowerCase()] ?? -1;
        const bv = order[String(b.generation_status||'').toLowerCase()] ?? -1;
        return sortState.dir === 'asc' ? (av - bv) : (bv - av);
      });
    }
    return out;
  }

  function renderRows(items){
    const tb = document.getElementById('reports-tbody');
    if (!tb) return;
    if (!items.length) { tb.innerHTML = '<tr><td colspan="5">No reports yet.</td></tr>'; return; }
    const isAdmin = !!window.IS_ADMIN;
    tb.innerHTML = items.map(r => {
      const dt = r.generated_date || r.created_date || '';
      const sid = fmtSession(r.session_id);
      const bits = [];
      if(sid) bits.push(`Session: ${esc(sid)}`);
      if(workspaceLabel) bits.push(`Workspace: ${esc(workspaceLabel)}`);
      const metaLine = bits.length ? `<div class="meta">${bits.join(' • ')}</div>` : '';
      const disabledAttr = isAdmin ? '' : 'disabled title="Admin only"';
      const st = String(r.generation_status || '').toLowerCase();
      const compareDisabled = st !== 'completed';
      const compareAttr = compareDisabled ? 'disabled title="Only completed reports can be compared"' : '';
      return `<tr data-id="${r.id}">
        <td><input type="checkbox" class="rcheck" ${compareAttr}/></td>
        <td><div>${esc(r.title)}</div>${metaLine}</td>
        <td>${fmtDate(dt)}</td>
        <td>${statusBadge(r.generation_status)}</td>
        <td>
          <a class="btn" href="/report/${r.id}">View</a>
          <button class="btn btn-muted act-regenerate" ${disabledAttr}>Regenerate</button>
          <button class="btn btn-danger act-delete" ${disabledAttr}>Delete</button>
        </td>
      </tr>`;
    }).join('');
  }

  async function loadReports(){
    const tb = document.getElementById('reports-tbody');
    if (!tb) { console.warn('[ReportsList] tbody not found'); return; }
    try{
      console.log('[ReportsList] loading list ...');
      const data = await fetchJSON('/api/reports');
      console.log('[ReportsList] data:', data);
      allItems = (data && data.reports) || [];
      renderRows(sortItems(allItems));
    } catch (e) {
      console.error('[ReportsList] load failed', e);
      tb.innerHTML = '<tr><td colspan="5" class="error">Failed to load.</td></tr>';
    }
  }

  function bind(){
    const tb = document.getElementById('reports-tbody');
    const cmp = document.getElementById('btn-compare');
    const cmpMeta = document.getElementById('compare-meta');
    const search = document.getElementById('report-search');
    const sortByDate = document.getElementById('sort-date');
    const sortByStatus = document.getElementById('sort-status');
    if (tb && cmp){
      function updateCompareUI(){
        const checked = Array.from(tb.querySelectorAll('.rcheck:checked'));
        const n = checked.length;
        cmp.disabled = n !== 2;
        if(cmpMeta){
          cmpMeta.textContent = n ? `Selected ${n}/2 for comparison.` : 'Select two completed reports to enable comparison.';
        }
        for(const tr of tb.querySelectorAll('tr')){
          const c = tr.querySelector('.rcheck');
          tr.classList.toggle('is-selected', !!(c && c.checked));
        }
      }

      tb.addEventListener('change', (e)=>{
        const target = e.target;
        if(!(target instanceof HTMLInputElement) || !target.classList.contains('rcheck')){
          updateCompareUI();
          return;
        }
        if(target.checked){
          const checked = Array.from(tb.querySelectorAll('.rcheck:checked'));
          if(checked.length > 2){
            target.checked = false;
          }
        }
        updateCompareUI();
      });
      cmp.addEventListener('click', ()=>{
        const ids = Array.from(tb.querySelectorAll('.rcheck:checked')).map(x=> x.closest('tr').getAttribute('data-id'));
        if(ids.length===2) window.location = `/reports/compare?a=${ids[0]}&b=${ids[1]}`;
      });
      // Placeholder actions
      tb.addEventListener('click', (e)=>{
        const t = e.target;
        if (!(t instanceof HTMLElement)) return;
        const row = t.closest('tr');
        if (!row) return;
        const id = row.getAttribute('data-id');
        if (t.classList.contains('act-regenerate')){
          e.preventDefault();
          if (!window.IS_ADMIN) { alert('Admin only'); return; }
          if (confirm(`Regenerate report ${id}? (placeholder)`)) {
            console.log('Regenerate placeholder for report', id);
            alert('Regenerate action is not implemented in demo.');
          }
        }
        if (t.classList.contains('act-delete')){
          e.preventDefault();
          if (!window.IS_ADMIN) { alert('Admin only'); return; }
          if (confirm(`Delete report ${id}? (placeholder)`)) {
            console.log('Delete placeholder for report', id);
            alert('Delete action is not implemented in demo.');
          }
        }
      });
    }
    if (search && tb){
      const doFilter = ()=>{
        const q = search.value.trim().toLowerCase();
        for (const tr of tb.querySelectorAll('tr')){
          const title = (tr.children[1]?.textContent || '').toLowerCase();
          tr.style.display = q && !title.includes(q) ? 'none' : '';
        }
      };
      search.addEventListener('input', doFilter);
    }
    if (sortByDate){
      sortByDate.addEventListener('click', ()=>{
        if (sortState.by === 'date'){
          sortState.dir = sortState.dir === 'asc' ? 'desc' : 'asc';
        } else {
          sortState.by = 'date';
          sortState.dir = 'desc';
        }
        renderRows(sortItems(allItems));
        if(tb && cmp){
          const checked = Array.from(tb.querySelectorAll('.rcheck:checked'));
          cmp.disabled = checked.length !== 2;
          if(cmpMeta) cmpMeta.textContent = checked.length ? `Selected ${checked.length}/2 for comparison.` : 'Select two completed reports to enable comparison.';
        }
      });
    }
    if (sortByStatus){
      sortByStatus.addEventListener('click', ()=>{
        if (sortState.by === 'status'){
          sortState.dir = sortState.dir === 'asc' ? 'desc' : 'asc';
        } else {
          sortState.by = 'status';
          sortState.dir = 'desc';
        }
        renderRows(sortItems(allItems));
        if(tb && cmp){
          const checked = Array.from(tb.querySelectorAll('.rcheck:checked'));
          cmp.disabled = checked.length !== 2;
          if(cmpMeta) cmpMeta.textContent = checked.length ? `Selected ${checked.length}/2 for comparison.` : 'Select two completed reports to enable comparison.';
        }
      });
    }
  }

  function start(){
    bind();
    // Show a fallback if nothing rendered after 2s
    let rendered = false;
    const tb = document.getElementById('reports-tbody');
    setTimeout(()=>{ if(!rendered && tb && tb.innerText.includes('Loading')){ tb.innerHTML = '<tr><td colspan="5">No reports yet.</td></tr>'; } }, 2000);
    loadWorkspaceLabel().finally(()=>{
      loadReports().finally(()=>{ rendered = true; });
    });
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
