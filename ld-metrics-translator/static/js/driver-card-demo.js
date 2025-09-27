/* Driver Card Demo interactions (diagnostics tab) */
(function(){
  "use strict";

  const renderer = window.DriverCardRenderer;
  if(!renderer){
    console.warn('DriverCardRenderer not loaded.');
    return;
  }

  const apiUrl = (path) => {
    if(!path) return window.location.origin;
    if(path.startsWith('http')) return path;
    return `${window.location.origin}${path.startsWith('/') ? path : `/${path}`}`;
  };

  async function fetchJson(path, opts){
    const res = await fetch(apiUrl(path), opts);
    if(!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async function fetchDriverCard(id){
    try{
      const data = await fetchJson(`/api/driver-cards/${id}`);
      return renderer.normalize(data.driver_card || data);
    }catch(err){ return null; }
  }

  async function fetchMetricCard(id){
    try{
      const data = await fetchJson(`/api/metric-cards/${id}`);
      const card = data.metric_card || data.metric || data;
      return renderer.normalize(card);
    }catch(err){ return null; }
  }

  async function fetchMetric(id){
    try{
      const data = await fetchJson(`/api/metrics/${id}`);
      return renderer.normalize(data.metric || data);
    }catch(err){ return null; }
  }

  async function fetchByName(name){
    if(!name) return null;
    try{
      const data = await fetchJson(`/api/metrics?per_page=50&q=${encodeURIComponent(name)}`);
      const list = data.metrics || data.items || [];
      const match = list.find((m) => (m.name || '').toLowerCase() === name.toLowerCase()) || list[0];
      return match ? renderer.normalize(match) : null;
    }catch(err){ return null; }
  }

  async function resolveCard(idOrName){
    if(!idOrName) return null;
    if(typeof idOrName === 'number' || /^[0-9]+$/.test(String(idOrName))){
      const id = Number(idOrName);
      return (await fetchDriverCard(id)) || (await fetchMetricCard(id)) || (await fetchMetric(id));
    }
    if(String(idOrName).startsWith('name:')){
      return fetchByName(String(idOrName).slice(5));
    }
    const asNumber = Number(idOrName);
    if(Number.isFinite(asNumber)){
      return resolveCard(asNumber);
    }
    return fetchByName(String(idOrName));
  }

  function ensureMiniModal(){
    let modal = document.getElementById('dc-mini-modal');
    if(modal) return modal;
    modal = document.createElement('div');
    modal.id = 'dc-mini-modal';
    modal.className = 'mini-modal';
    modal.innerHTML = '<div class="mini-modal-backdrop"></div><div class="mini-modal-content"><button class="mini-close" aria-label="Close">×</button><div class="mini-body"></div></div>';
    document.body.appendChild(modal);
    modal.querySelector('.mini-close').addEventListener('click', () => modal.classList.remove('open'));
    modal.querySelector('.mini-modal-backdrop').addEventListener('click', () => modal.classList.remove('open'));
    return modal;
  }

  async function openMiniPreviewByName(name){
    if(!name) return;
    const modal = ensureMiniModal();
    const body = modal.querySelector('.mini-body');
    body.innerHTML = '<div class="loading-spinner"></div><p>Loading…</p>';
    modal.classList.add('open');
    const card = await fetchByName(name);
    if(!card){
      body.innerHTML = `<div class="no-data-message"><div class="no-data-icon">??</div><p>Could not find a card named "${name}"</p></div>`;
      return;
    }
    body.innerHTML = '';
    renderer.render(body, card, {
      renderActions: (container, normalized) => {
        const view = document.createElement('a');
        view.className = 'btn btn-outline';
        view.textContent = 'View in Playbook';
        view.href = `/playbook?q=${encodeURIComponent(normalized.name || '')}`;
        container.appendChild(view);
        const add = document.createElement('button');
        add.className = 'btn btn-primary';
        add.textContent = 'Add to Plan';
        add.addEventListener('click', () => addToPlan(add, normalized));
        container.appendChild(add);
      },
      onItemClick: (label) => openMiniPreviewByName(label)
    });
  }

  async function addToPlan(button, card){
    if(!card) return;
    const prev = button.textContent;
    button.disabled = true;
    button.textContent = 'Adding…';
    try{
      const kind = (card.identifier_type || 'concept').toLowerCase();
      const payload = {
        kind: kind === 'behavior' ? 'behavior' : kind === 'kpi' ? 'kpi' : kind === 'outcome' ? 'outcome' : 'concept',
        label: card.name,
        source_id: card.id,
        source_page: 'driver-card-demo'
      };
      const res = await fetch(apiUrl('/api/context/plan/items'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if(!res.ok) throw new Error(`HTTP ${res.status}`);
      button.textContent = 'Added!';
      window.setTimeout(() => { button.textContent = 'In Plan'; button.classList.add('btn-secondary'); }, 600);
    }catch(err){
      console.warn('Add to plan failed', err);
      button.textContent = prev;
      button.disabled = false;
    }
  }

  async function renderSelectedCard(select){
    if(!select) return;
    const value = select.value;
    if(!value) return;
    const card = await resolveCard(value);
    const container = document.getElementById('driver-card-demo');
    if(!card){
      container.innerHTML = '<div class="no-data-message"><div class="no-data-icon">??</div><h3>Unable to load card</h3><p>Please check that driver cards are seeded.</p></div>';
      return;
    }
    renderer.render(container, card, {
      onItemClick: (label) => openMiniPreviewByName(label),
      onBiasClick: (label) => openMiniPreviewByName(label),
      onNudgeClick: (label) => openMiniPreviewByName(label),
      onFrameworkClick: (fw) => { window.location.href = `/playbook?q=${encodeURIComponent(fw.name)}`; },
      renderActions: (actionContainer, normalized) => {
        const addBtn = document.createElement('button');
        addBtn.className = 'btn btn-primary';
        addBtn.textContent = 'Add to Plan';
        addBtn.addEventListener('click', () => addToPlan(addBtn, normalized));
        actionContainer.appendChild(addBtn);
      }
    });
  }

  async function populateSelect(select){
    const preferred = ['Growth Mindset', 'Giving Recognition', 'Time to Productivity', 'Improved Employee Retention'];
    const options = [];
    try{
      const data = await fetchJson('/api/metrics?per_page=200');
      const metrics = data.metrics || data.items || [];
      preferred.forEach((name) => {
        const match = metrics.find((m) => (m.name || '').toLowerCase() === name.toLowerCase());
        if(match){
          options.push({ value: String(match.id), label: `${match.name} (${(match.identifier_type || 'concept').toUpperCase()})` });
        }
      });
    }catch(err){ /* ignore */ }
    if(options.length === 0){
      preferred.forEach((name) => {
        options.push({ value: `name:${name}`, label: `${name} (expected)` });
      });
    }
    select.innerHTML = '';
    options.forEach((opt) => {
      const option = document.createElement('option');
      option.value = opt.value;
      option.textContent = opt.label;
      select.appendChild(option);
    });
    if(options.length) select.value = options[0].value;
  }

  async function init(){
    const container = document.getElementById('driver-card-demo');
    const select = document.getElementById('driver-card-id');
    const button = document.getElementById('driver-card-load');
    if(!container || !select || !button) return;

    await populateSelect(select);
    button.addEventListener('click', () => renderSelectedCard(select));
    select.addEventListener('change', () => renderSelectedCard(select));

    document.addEventListener('click', (event) => {
      const tab = event.target.closest('.subnav-tab[data-panel="diag-driver-card"]');
      if(tab){ window.setTimeout(() => renderSelectedCard(select), 0); }
    });

    renderSelectedCard(select);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
