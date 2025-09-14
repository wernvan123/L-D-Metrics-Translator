(function(){
  function $(sel){ return document.querySelector(sel); }
  function $all(sel){ return Array.from(document.querySelectorAll(sel)); }
  function escapeHtml(s){ return String(s||'').replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c])); }

  const els = {
    search: null,
    kind: null,
    status: null,
    grid: null,
    tree: null,
    suggestions: null,
    activeSelections: null,
    modal: null,
    modalBody: null,
  };

  const state = {
    q: '',
    kind: '', // '', 'driver', 'bias'
  };

  function readURL(){
    const u = new URL(window.location.href);
    state.q = u.searchParams.get('q') || '';
    state.kind = u.searchParams.get('kind') || '';
    if(els.search) els.search.value = state.q;
    if(els.kind) els.kind.value = state.kind;
  }

  function writeURL(push=true){
    const u = new URL(window.location.href);
    if(state.q) u.searchParams.set('q', state.q); else u.searchParams.delete('q');
    if(state.kind) u.searchParams.set('kind', state.kind); else u.searchParams.delete('kind');
    if(push) history.pushState({q:state.q,kind:state.kind}, '', u.toString());
  }

  function setStatus(type, message){
    if(!els.status) return;
    if(!message){ els.status.style.display='none'; return; }
    els.status.className = 'notice ' + (type ? `notice-${type}` : '');
    els.status.textContent = message;
    els.status.style.display = 'block';
  }

  function badgeForKind(kind){ return kind==='bias' ? 'Bias' : 'Driver'; }

  function renderGrid(items){
    els.grid.innerHTML = '';
    if(!items || !items.length){
      const empty = document.createElement('div');
      empty.className = 'no-data-message';
      empty.innerHTML = `
        <div class="no-data-icon">🗂️</div>
        <h3>No drivers match your current filters</h3>
        <p>Try broadening your search or clearing filters.</p>
        <div style="margin-top:8px;">
          <button id="pbk-clear-filters" class="btn btn-secondary">Clear All Filters</button>
        </div>
      `;
      els.grid.appendChild(empty);
      // Bind Clear All Filters
      const clear = empty.querySelector('#pbk-clear-filters');
      if(clear){ clear.addEventListener('click', ()=>{ state.q=''; state.kind=''; writeURL(); if(els.search) els.search.value=''; if(els.kind) els.kind.value=''; loadGrid(); }); }
      return;
    }
    const frag = document.createDocumentFragment();
    for(const card of items){
      const div = document.createElement('div');
      div.className = 'metric-card';
      div.setAttribute('data-id', card.id ?? '');
      const kind = (card.kind || state.kind || 'driver').toLowerCase();
      div.innerHTML = `
        <div class="metric-header">
          <h3 class="metric-title">${escapeHtml(card.name || 'Item')}</h3>
          <div class="metric-badges">
            <span class="badge badge-kind">${badgeForKind(kind)}</span>
            ${card.outcome?.name ? `<span class="badge badge-outline badge-outcome">${escapeHtml(card.outcome.name)}</span>` : ''}
            ${card.metric_type?.name ? `<span class="badge badge-outline badge-type">${escapeHtml(card.metric_type.name)}</span>` : ''}
          </div>
        </div>
        <div class="metric-content">
          <p class="metric-description">${escapeHtml(card.description || '')}</p>
        </div>
        <div class="metric-actions">
          <button class="btn btn-sm btn-primary" data-action="add" data-kind="${kind}" data-id="${card.id}" data-label="${escapeHtml(card.name||'Item')}">Add to Plan</button>
          <button class="btn btn-sm btn-outline" data-action="view">View Details</button>
        </div>
      `;
      frag.appendChild(div);
    }
    els.grid.appendChild(frag);
  }

  async function loadGrid(){
    try{
      setStatus(null, '');
      const ps = new URLSearchParams();
      if(state.q) ps.set('q', state.q);
      if(state.kind) ps.set('kind', state.kind);
      ps.set('page', '1');
      ps.set('page_size', '24');
      const url = `/api/driver-cards?${ps.toString()}`;
      const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if(!res.ok) throw new Error(`Failed to load (${res.status})`);
      const data = await res.json();
      renderGrid(data.items || []);
    }catch(err){
      console.warn(err);
      setStatus('warning', err.message || 'Unable to load content');
    }
  }

  async function refreshSelections(){
    try{
      const res = await fetch('/api/context/plan/items', { headers: { 'Accept':'application/json' } });
      if(!res.ok) return;
      const data = await res.json();
      const items = Array.isArray(data.items) ? data.items : [];
      const box = els.activeSelections; if(!box) return;
      box.innerHTML = '';
      if(!items.length){ box.textContent = 'No items yet.'; return; }
      const ul = document.createElement('ul'); ul.className = 'list';
      items.forEach(it => {
        const li = document.createElement('li');
        li.innerHTML = `<span>${escapeHtml(it.label)} <span class="badge badge-kind">${escapeHtml(it.kind)}</span></span>`;
        const rm = document.createElement('button'); rm.className='btn btn-sm btn-outline'; rm.textContent='Remove';
        rm.addEventListener('click', async ()=>{ try{ await fetch(`/api/context/plan/items/${it.id}`, { method:'DELETE' }); await refreshSelections(); }catch{} });
        li.appendChild(rm);
        ul.appendChild(li);
      });
      box.appendChild(ul);
    }catch(err){ console.warn(err); }
  }

  async function addToPlan(kind, label, sourceId, meta){
    try{
      const res = await fetch('/api/context/plan/items', {
        method:'POST', headers:{ 'Content-Type':'application/json' },
        body: JSON.stringify({ kind, label, source_id: sourceId, meta, source_page: 'playbook' })
      });
      if(!res.ok) throw new Error('Failed to add to plan');
      window.notify && window.notify('success', 'Added to plan');
      await refreshSelections();
    }catch(err){ window.notify && window.notify('error', err.message || 'Failed to add to plan'); }
  }

  function initEvents(){
    if(els.search){ els.search.addEventListener('input', ()=>{ state.q = els.search.value.trim(); writeURL(); loadGrid(); }); }
    if(els.kind){ els.kind.addEventListener('change', ()=>{ state.kind = els.kind.value; writeURL(); loadGrid(); }); }
    if(els.grid){ els.grid.addEventListener('click', (e)=>{
      const btn = e.target.closest('button[data-action]');
      if(!btn) return;
      const action = btn.getAttribute('data-action');
      const cardEl = btn.closest('.metric-card');
      if(action === 'view'){
        const title = cardEl ? cardEl.querySelector('.metric-title')?.textContent || 'Details' : 'Details';
        openModal(`<h3>${escapeHtml(title)}</h3>` + (cardEl ? cardEl.querySelector('.metric-description')?.outerHTML || '' : ''));
      } else if(action === 'add'){
        const kind = (btn.getAttribute('data-kind')||'driver').toLowerCase();
        const id = btn.getAttribute('data-id');
        const label = btn.getAttribute('data-label') || 'Item';
        addToPlan(kind, label, id ? parseInt(id,10) : null, {});
      }
    }); }
    window.addEventListener('popstate', (ev)=>{
      if(ev.state){ state.q = ev.state.q || ''; state.kind = ev.state.kind || ''; }
      if(els.search) els.search.value = state.q; if(els.kind) els.kind.value = state.kind;
      loadGrid();
    });
  }

  function openModal(html){
    if(!els.modal) return;
    els.modalBody.innerHTML = html;
    els.modal.style.display = 'block';
  }
  function closeModal(){ if(els.modal) els.modal.style.display = 'none'; }

  function initModal(){
    if(!els.modal) return;
    const close = els.modal.querySelector('.modal-close');
    const backdrop = els.modal.querySelector('.modal-backdrop');
    close && close.addEventListener('click', closeModal);
    backdrop && backdrop.addEventListener('click', closeModal);
    document.addEventListener('keydown', (e)=>{ if(e.key==='Escape') closeModal(); });
  }

  async function init(){
    els.search = $('#pbk-search');
    els.kind = $('#pbk-kind');
    els.status = $('#playbook-status');
    els.grid = $('#playbook-grid');
    els.tree = $('#playbook-tree');
    els.suggestions = $('#playbook-suggestions');
    els.activeSelections = $('#active-selections');
    els.modal = $('#playbook-modal');
    els.modalBody = $('#playbook-modal-body');

    initModal();
    readURL();
    initEvents();
    await Promise.all([loadGrid(), refreshSelections()]);
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }
})();
