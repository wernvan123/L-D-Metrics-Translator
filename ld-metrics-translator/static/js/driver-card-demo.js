(function(){
  const apiUrl = (path)=> `${window.location.origin}${path.startsWith('/')?path:`/${path}`}`;
  async function fetchCard(id){
    // Try driver-cards first (present in dev), then enriched metric-cards
    try {
      const drv = await fetch(apiUrl(`/api/driver-cards/${id}`));
      if (drv.ok) {
        const data2 = await drv.json();
        const card = data2.driver_card || data2;
        return {
          id: card.id,
          title: card.name,
          description: card.description,
          identifier_type: (card.kind || 'driver'),
          outcome: card.outcome,
          metric_type: card.metric_type,
          associated_frameworks: card.tags || [],
          related_biases: card.related_biases || [],
          related_nudges: card.related_nudges || [],
          driver_chain: [
            { key: 'drives_behaviors', title: 'Drives Behavior', items: [] },
            { key: 'measured_by_kpis', title: 'Measured by KPI', items: [] },
            { key: 'leads_to_outcomes', title: 'Leads to Outcome', items: [] }
          ],
          classification: {
            ld_outcome: card.outcome?.name,
            metric_type: card.metric_type?.name,
            data_collection: undefined,
            frequency: undefined,
          }
        };
      }
    } catch (e) {}
    try {
      const res = await fetch(apiUrl(`/api/metric-cards/${id}`));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      return data.metric_card || data.metric || data;
    } catch (e) {
      console.warn('driver-cards and metric-cards failed, trying /api/metrics/<id>', e);
      try {
        return await fetchMetricCard(id);
      } catch (e3) {
        console.error('All fallbacks failed', e3);
        return null;
      }
    }
  }

  // --- Lightweight search by name for preview lookups ---
  async function fetchByName(name){
    if(!name) return null;
    try{
      const res = await fetch(apiUrl(`/api/metrics?per_page=25&q=${encodeURIComponent(name)}`));
      if(!res.ok) return null;
      const data = await res.json();
      const list = data.metrics || data.items || [];
      const best = list.find(m => (m.name||'').toLowerCase() === String(name).toLowerCase()) || list[0];
      if(!best) return null;
      return buildFromMetric(best);
    }catch(e){ return null; }
  }

  async function fetchMetricCard(id){
    const r = await fetch(apiUrl(`/api/metrics/${id}`));
    if(!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    const m = d.metric || d;
    return buildFromMetric(m);
  }

  function buildFromMetric(m){
    const kind = (m.identifier_type||'concept').toLowerCase();
    const dc = m.driver_chain;
    let chain = [];
    try{
      const obj = typeof dc === 'string' ? JSON.parse(dc) : dc;
      if(obj && typeof obj === 'object'){
        if(kind === 'concept'){
          chain = [
            { key:'drives_behaviors', title:'Drives Behavior', items: obj.drives_behaviors||[] },
            { key:'measured_by_kpis', title:'Measured by KPI', items: obj.measured_by_kpis||[] },
            { key:'leads_to_outcomes', title:'Leads to Outcome', items: obj.leads_to_outcomes||[] },
          ];
        } else if(kind === 'behavior'){
          chain = [
            { key:'driven_by_concepts', title:'Driven by Concept', items: obj.driven_by_concepts||[] },
            { key:'measured_by_kpis', title:'Measured by KPI', items: obj.measured_by_kpis||[] },
            { key:'leads_to_outcomes', title:'Leads to Outcome', items: obj.leads_to_outcomes||[] },
          ];
        } else if(kind === 'kpi'){
          chain = [
            { key:'measures_behaviors', title:'Measures Behavior', items: obj.measures_behaviors||[] },
            { key:'indicates_concepts', title:'Indicates Concept', items: obj.indicates_concepts||[] },
            { key:'leads_to_outcomes', title:'Leads to Outcome', items: obj.leads_to_outcomes||[] },
          ];
        } else if(kind === 'outcome'){
          chain = [
            { key:'driven_by_behaviors', title:'Driven by Behavior', items: obj.driven_by_behaviors||[] },
            { key:'driven_by_concepts', title:'Driven by Concept', items: obj.driven_by_concepts||[] },
            { key:'measured_by_kpis', title:'Measured by KPI', items: obj.measured_by_kpis||[] },
          ];
        }
      }
    }catch{}
    const classification = {
      ld_outcome: m.outcome?.name || m.ld_outcome || m.outcome_name,
      metric_type: m.metric_type?.name || m.metric_type_name,
      data_collection: m.data_collection,
      frequency: m.frequency,
    };
    return {
      id: m.id,
      title: m.name,
      description: m.description,
      identifier_type: m.identifier_type,
      driver_chain: chain,
      associated_frameworks: m.associated_frameworks || m.frameworks || [],
      neuro_link: m.neuro_link || m.neuropsychology || null,
      related_biases: m.related_biases || [],
      related_nudges: m.related_nudges || [],
      classification,
    };
  }

  function el(tag, cls, text){
    const n = document.createElement(tag);
    if(cls) n.className = cls;
    if(text) n.textContent = text;
    return n;
  }

  function renderChain(stages){
    const wrap = el('div', 'dc-chain');
    const icons = ['🧍','📈','🎯'];
    stages.forEach((s, i)=>{
      const item = el('div', 'dc-stage');
      const title = el('div', 'dc-stage-title');
      const icon = el('span','dc-stage-icon', icons[i] || '🔹');
      title.appendChild(icon);
      title.appendChild(document.createTextNode(s.title));
      item.appendChild(title);
      const list = el('ul', 'dc-stage-list');
      (s.items||[]).forEach(v=> {
        const li = el('li');
        const btn = el('button','dc-pill-link', v);
        btn.title = `Open preview for ${v}`;
        btn.addEventListener('click', ()=> openMiniPreviewByName(v));
        li.appendChild(btn);
        list.appendChild(li);
      });
      item.appendChild(list);
      wrap.appendChild(item);
      if(i < stages.length - 1){
        wrap.appendChild(el('div','dc-arrow','→'));
      }
    });
    return wrap;
  }

  function renderCard(card){
    const root = document.getElementById('driver-card-demo');
    root.innerHTML = '';
    if(!card){
      const err = el('div','no-data-message');
      err.innerHTML = `<div class="no-data-icon">⚠️</div><h3>Unable to load card</h3><p>Please check the API route is available.</p>`;
      root.appendChild(err);
      return;
    }
    const box = el('div', 'driver-card');
    const header = el('div','dc-header');
    header.appendChild(el('div','dc-title', card.title || card.name));
    const kind = (card.identifier_type||'concept').toLowerCase();
    const badge = el('div','dc-badge', (card.identifier_type||'CONCEPT').toUpperCase());
    badge.setAttribute('data-kind', kind);
    header.appendChild(badge);
    box.appendChild(header);

    if(card.description){
      box.appendChild(el('p','dc-desc', card.description));
    }
    if(card.neuro_link){
      const neuro = el('div','dc-neuro');
      const lbl = el('div','dc-label','Neuropsychology Link');
      const text = el('p','dc-neuro-text', card.neuro_link);
      neuro.appendChild(lbl); neuro.appendChild(text);
      box.appendChild(neuro);
    }

    // frameworks
    const fw = el('div','dc-fw');
    fw.appendChild(el('div','dc-label','Associated Frameworks'));
    const fwl = el('ul','dc-fw-list');
    (card.associated_frameworks||[]).forEach(f=> {
      const li = el('li');
      const a = el('a','dc-fw-link', f.name || String(f));
      a.href = `/playbook?q=${encodeURIComponent(f.name||String(f))}`;
      a.title = 'Open Playbook filtered to this framework';
      li.appendChild(a);
      fwl.appendChild(li);
    });
    fw.appendChild(fwl);
    box.appendChild(fw);

    // chain
    const chain = renderChain(card.driver_chain||[]);
    box.appendChild(chain);

    // Related Biases/Nudges (if present)
    if(Array.isArray(card.related_biases) && card.related_biases.length){
      const rel = el('div','dc-related');
      rel.appendChild(el('div','dc-label','Related Biases'));
      const list = el('div','dc-related-chips');
      card.related_biases.forEach(name=>{
        const chip = el('button','tag-chip');
        chip.textContent = name;
        chip.title = `Preview ${name}`;
        chip.addEventListener('click', ()=> openMiniPreviewByName(name));
        list.appendChild(chip);
      });
      rel.appendChild(list);
      box.appendChild(rel);
    }
    if(Array.isArray(card.related_nudges) && card.related_nudges.length){
      const nud = el('div','dc-related');
      nud.appendChild(el('div','dc-label','Recommended Nudges'));
      const list2 = el('div','dc-related-chips');
      card.related_nudges.forEach(name=>{
        const chip = el('button','tag-chip tag-chip--nudge');
        chip.textContent = name;
        chip.title = `Preview ${name}`;
        chip.addEventListener('click', ()=> openMiniPreviewByName(name));
        list2.appendChild(chip);
      });
      nud.appendChild(list2);
      box.appendChild(nud);
    }

    // classification
    const clsf = el('div','dc-class');
    clsf.appendChild(el('div','dc-label','Classification Details'));
    const kv = card.classification||{};
    const grid = el('div','dc-grid');
    [
      ['L&D OUTCOME', kv.ld_outcome],
      ['METRIC TYPE', kv.metric_type],
      ['DATA COLLECTION', kv.data_collection],
      ['FREQUENCY', kv.frequency],
    ].forEach(([k,v])=>{
      const pill = el('div','dc-pill');
      pill.appendChild(el('div','dc-pill-k',k));
      pill.appendChild(el('div','dc-pill-v',v||'—'));
      grid.appendChild(pill);
    });
    clsf.appendChild(grid);
    box.appendChild(clsf);

    // actions
    const actions = el('div','dc-actions');
    const add = el('button','btn');
    add.textContent = 'Add to Plan';
    add.addEventListener('click', async ()=>{
      add.disabled = true; const prev = add.textContent; add.textContent = 'Adding…';
      try{
        const res = await fetch(apiUrl('/api/context/plan/items'),{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ kind: kind==='kpi'?'kpi': kind==='behavior'?'behavior': kind==='outcome'?'outcome':'concept', label: card.title||card.name, source_id: card.id, source_page: 'driver-card-demo'})});
        if(!res.ok) throw new Error('HTTP '+res.status);
        add.textContent = 'Added!';
        setTimeout(()=>{ add.textContent = 'In Plan'; add.classList.add('btn-secondary'); }, 600);
      }catch(e){ console.warn('Add to Plan failed', e); add.textContent = prev; add.disabled = false; }
    });
    actions.appendChild(add);
    box.appendChild(actions);

    root.appendChild(box);
  }

  // --- Mini Modal for quick preview ---
  function ensureMiniModal(){
    let modal = document.getElementById('dc-mini-modal');
    if(modal) return modal;
    modal = document.createElement('div');
    modal.id = 'dc-mini-modal';
    modal.className = 'mini-modal';
    modal.innerHTML = '<div class="mini-modal-backdrop"></div><div class="mini-modal-content"><button class="mini-close" aria-label="Close">×</button><div class="mini-body"></div></div>';
    document.body.appendChild(modal);
    modal.querySelector('.mini-close').addEventListener('click', ()=> modal.classList.remove('open'));
    modal.querySelector('.mini-modal-backdrop').addEventListener('click', ()=> modal.classList.remove('open'));
    return modal;
  }

  async function openMiniPreviewByName(name){
    const modal = ensureMiniModal();
    const body = modal.querySelector('.mini-body');
    body.innerHTML = '<div class="loading-spinner"></div><p>Loading…</p>';
    modal.classList.add('open');
    const card = await fetchByName(name);
    if(!card){ body.innerHTML = `<div class="no-data-message"><div class="no-data-icon">⚠️</div><p>Could not find a card named "${name}"</p></div>`; return; }
    body.innerHTML = '';
    const title = el('div','mini-title', card.title||card.name);
    const desc = el('div','mini-desc', card.description||'');
    const act = el('div','mini-actions');
    const view = el('a','btn btn-outline');
    view.textContent = 'View Full Card';
    view.href = `/playbook?q=${encodeURIComponent(card.title||card.name)}`;
    const add = el('button','btn btn-primary');
    add.textContent = 'Add to Plan';
    const kind = (card.identifier_type||'concept').toLowerCase();
    add.addEventListener('click', async ()=>{
      add.disabled = true; const prev = add.textContent; add.textContent = 'Adding…';
      try{
        const res = await fetch(apiUrl('/api/context/plan/items'),{ method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ kind: kind==='kpi'?'kpi': kind==='behavior'?'behavior': kind==='outcome'?'outcome':'concept', label: card.title||card.name, source_id: card.id, source_page: 'driver-card-mini'})});
        if(!res.ok) throw new Error('HTTP '+res.status);
        add.textContent = 'Added!';
        setTimeout(()=>{ add.textContent = 'In Plan'; add.classList.add('btn-secondary'); }, 600);
      }catch(e){ add.textContent = prev; add.disabled = false; }
    });
    act.appendChild(view); act.appendChild(add);
    body.appendChild(title); body.appendChild(desc); body.appendChild(act);
  }

  async function init(){
    const root = document.getElementById('driver-card-demo');
    if(!root) return;
    const select = document.getElementById('driver-card-id');
    const btn = document.getElementById('driver-card-load');

    // Populate options dynamically from metrics API by name (strict to preferred list)
    async function populateOptions(){
      const preferred = [
        'Growth Mindset',
        'Giving Recognition',
        'Time to Productivity',
        'Improved Employee Retention'
      ];
      const opts = [];
      try{
        const res = await fetch(apiUrl('/api/metrics?per_page=100'));
        if(res.ok){
          const data = await res.json();
          const list = data.metrics || data.items || [];
          // map by name
          preferred.forEach(name => {
            const m = (list||[]).find(x => (x.name||'').toLowerCase() === name.toLowerCase());
            if(m){
              const id = m.id;
              const label = `${m.name} (${(m.identifier_type||m.metric_type_name||'metric').toString().toUpperCase()})`;
              opts.push({id, label});
            }
          });
        }
      }catch{}
      // If still none found from APIs, show the preferred names to guide seeding
      const usedPreferredAsPlaceholders = opts.length === 0;
      if(usedPreferredAsPlaceholders){
        preferred.forEach(name => opts.push({ id: `name:${name}`, label: `${name} (EXPECTED)` }));
        const container = document.getElementById('driver-card-demo');
        if(container){
          const note = document.createElement('div');
          note.className = 'no-data-message';
          note.innerHTML = '<div class="no-data-icon">ℹ️</div><p>Seed data not found for the four demo cards. Use the seed script to add them, then reload.</p>';
          container.appendChild(note);
        }
      }
      // Update select
      if(select){
        select.innerHTML = '';
        opts.forEach(o => {
          const opt = document.createElement('option');
          opt.value = String(o.id);
          opt.textContent = o.label;
          select.appendChild(opt);
        });
        // Select first option by default
        if(opts.length){ select.value = String(opts[0].id); }
      }
    }

    async function load(){
      let id = parseInt(select.value,10);
      // If value is a placeholder like name:Growth Mindset, resolve by name
      if(Number.isNaN(id)){
        const val = String(select.value||'');
        if(val.startsWith('name:')){
          const name = val.slice(5);
          // Try a few strategies
          const tryResolvers = [
            `/api/metrics?per_page=200`,
            `/api/metrics`,
            `/api/metrics?name=${encodeURIComponent(name)}`,
            `/api/metrics?search=${encodeURIComponent(name)}`,
            `/api/metrics?q=${encodeURIComponent(name)}`,
          ];
          for(const p of tryResolvers){
            try{
              const r = await fetch(apiUrl(p));
              if(r.ok){
                const d = await r.json();
                const list = d.metrics || d.items || d.data || [];
                const m = Array.isArray(list) ? list.find(x => (x.name||'').toLowerCase() === name.toLowerCase()) : (list.name && (list.name||'').toLowerCase()===name.toLowerCase() ? list : null);
                if(m && m.id){ id = m.id; break; }
              }
            }catch{}
          }
          // Last resort: use known seeded IDs provided by user
          if(!Number.isFinite(id)){
            const map = {
              'growth mindset': 12,
              'giving recognition': 13,
              'time to productivity': 4,
              'improved employee retention': 15,
            };
            const k = name.toLowerCase();
            if(map[k]) id = map[k];
          }
        }
      }
      if(!Number.isFinite(id) || id <= 0) return;
      let card = null;
      try{
        // Always prefer driver-cards so related_nudges and related_biases are available
        card = await fetchCard(id);
      }catch(e){
        // Fallback path to metrics
        card = await fetchMetricCard(id);
      }
      if(card) renderCard(card);
    }

    async function doLoad(){
      const sel = (select && select.value) ? select.value : '';
      let card = null;
      if(String(sel).startsWith('name:')){
        card = await fetchByName(String(sel).slice(5));
      } else if(sel){
        card = await fetchCard(sel);
      }
      renderCard(card);
    }

    btn?.addEventListener('click', doLoad);
    select?.addEventListener('change', doLoad);

    // Auto-load when the Driver Card tab is shown
    document.addEventListener('click', (e) => {
      const tab = e.target.closest('.subnav-tab[data-panel="diag-driver-card"]');
      if(tab){
        setTimeout(doLoad, 0);
      }
    });

    // Populate then load first value
    await populateOptions();
    await doLoad();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
