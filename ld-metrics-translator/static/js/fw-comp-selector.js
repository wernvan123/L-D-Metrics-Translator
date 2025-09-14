(function(){
  function $(sel){ return document.querySelector(sel); }
  function setStatus(el, type, msg){
    if(!el) return;
    el.className = 'notice ' + (type ? `notice-${type}` : '');
    el.textContent = msg || '';
    el.style.display = msg ? 'block' : 'none';
  }

  const els = {
    fw: null,
    comp: null,
    status: null
  };

  let frameworks = [];
  // Store by string id to support APIs that use non-numeric IDs (e.g., "fwk-001")
  let compsByFrameworkId = new Map();

  // Client-side fallback seed (non-destructive): used only if API lacks these
  const FALLBACK_FW = [
    {
      id: 'fw-situational-leadership-model',
      name: 'The Situational Leadership® Model',
      slug: 'situational-leadership-model',
      competencies: [
        { id: 'c-adaptability', name: 'Adaptability', slug: 'adaptability' },
        { id: 'c-coaching', name: 'Coaching', slug: 'coaching' },
        { id: 'c-delegation', name: 'Delegation', slug: 'delegation' },
        { id: 'c-motivation', name: 'Motivation', slug: 'motivation' },
      ]
    },
    {
      id: 'fw-goleman-eq',
      name: "Goleman's Emotional Intelligence (EQ)",
      slug: 'goleman-emotional-intelligence-eq',
      competencies: [
        { id: 'c-self-awareness', name: 'Self-Awareness', slug: 'self-awareness' },
        { id: 'c-self-management', name: 'Self-Management', slug: 'self-management' },
        { id: 'c-social-awareness', name: 'Social Awareness', slug: 'social-awareness' },
        { id: 'c-relationship-management', name: 'Relationship Management', slug: 'relationship-management' },
      ]
    },
    {
      id: 'fw-five-practices',
      name: 'The Five Practices of Exemplary Leadership',
      slug: 'five-practices-of-exemplary-leadership',
      competencies: [
        { id: 'c-model-the-way', name: 'Model the Way', slug: 'model-the-way' },
        { id: 'c-inspire-shared-vision', name: 'Inspire a Shared Vision', slug: 'inspire-a-shared-vision' },
        { id: 'c-challenge-process', name: 'Challenge the Process', slug: 'challenge-the-process' },
        { id: 'c-enable-others', name: 'Enable Others to Act', slug: 'enable-others-to-act' },
        { id: 'c-encourage-heart', name: 'Encourage the Heart', slug: 'encourage-the-heart' },
      ]
    },
    {
      id: 'fw-strengths-based',
      name: 'Strengths-Based Leadership',
      slug: 'strengths-based-leadership',
      competencies: [
        { id: 'c-executing', name: 'Executing', slug: 'executing' },
        { id: 'c-influencing', name: 'Influencing', slug: 'influencing' },
        { id: 'c-relationship-building', name: 'Relationship Building', slug: 'relationship-building' },
        { id: 'c-strategic-thinking', name: 'Strategic Thinking', slug: 'strategic-thinking' },
      ]
    },
  ];

  function mergeFallbackFrameworks(list){
    try{
      const byName = new Set(list.map(f => (f.name||'').toLowerCase()));
      const merged = list.slice();
      for(const f of FALLBACK_FW){
        if(!byName.has((f.name||'').toLowerCase())){
          merged.push({ id: f.id, name: f.name, slug: f.slug, competencies: f.competencies });
        }
      }
      return merged;
    }catch{ return list; }
  }

  function restrictToFallbackOnly(list){
    try{
      const allowed = new Map(FALLBACK_FW.map(f => [(f.name||'').toLowerCase(), f]));
      // Keep only frameworks whose names match allowed set
      const kept = [];
      const seen = new Set();
      for(const fw of list){
        const key = (fw.name||'').toLowerCase();
        if(allowed.has(key)){
          kept.push({ id: String(fw.id ?? fw.slug ?? ''), name: fw.name, slug: fw.slug || '', competencies: fw.competencies });
          seen.add(key);
        }
      }
      // Add any missing ones from FALLBACK_FW
      for(const [key, f] of allowed.entries()){
        if(!seen.has(key)){
          kept.push({ id: f.id, name: f.name, slug: f.slug, competencies: f.competencies });
        }
      }
      return kept;
    }catch{ return list; }
  }

  function populateFrameworks(){
    if(!els.fw) return;
    // Keep first option (All Frameworks)
    // Remove any previous dynamic options
    Array.from(els.fw.options).slice(1).forEach(o => o.remove());
    for(const fw of frameworks){
      const opt = document.createElement('option');
      opt.value = String(fw.id);
      opt.textContent = fw.name;
      opt.dataset.slug = fw.slug || '';
      els.fw.appendChild(opt);
    }
  }

  async function populateCompetencies(fwId){
    if(!els.comp) return;
    els.comp.disabled = !fwId;
    // Reset options
    Array.from(els.comp.options).slice(1).forEach(o => o.remove());
    if(!fwId) return;
    let comps = compsByFrameworkId.get(String(fwId));
    // Fallback: if competencies were not preloaded, try fetching them
    if(!comps){
      try{
        const res = await fetch(`/api/frameworks/${encodeURIComponent(fwId)}/competencies?include=metrics`);
        if(res.ok){
          const data = await res.json();
          // Accept either {competencies:[...]} or {items:[...]}
          const list = Array.isArray(data?.competencies) ? data.competencies
                     : Array.isArray(data?.items) ? data.items
                     : [];
          comps = list.map(c => ({ id: String(c.id ?? c.slug ?? ''), name: c.name, slug: c.slug || '' }));
          compsByFrameworkId.set(String(fwId), comps);
        }
      }catch(err){ console.warn('load competencies failed', err); }
    } else if(Array.isArray(comps)){
      // ok
    }
    comps = comps || [];
    for(const c of comps){
      const opt = document.createElement('option');
      opt.value = String(c.id);
      opt.textContent = c.name;
      opt.dataset.slug = c.slug || '';
      els.comp.appendChild(opt);
    }
  }

  function dispatchFilter(){
    const fwOpt = els.fw?.selectedOptions?.[0];
    const compOpt = els.comp?.selectedOptions?.[0];
    const detail = {
      frameworkId: fwOpt && fwOpt.value ? String(fwOpt.value) : null,
      frameworkSlug: fwOpt ? (fwOpt.dataset.slug || null) : null,
      competencyId: compOpt && compOpt.value ? String(compOpt.value) : null,
      competencySlug: compOpt ? (compOpt.dataset.slug || null) : null,
    };
    document.dispatchEvent(new CustomEvent('driverCards:setFilter', { detail }));
    // Update URL params for deep-linking (without reload)
    try{
      const ps = new URLSearchParams(window.location.search);
      if(detail.frameworkId) ps.set('framework_id', String(detail.frameworkId)); else ps.delete('framework_id');
      if(detail.frameworkSlug) ps.set('framework_slug', detail.frameworkSlug); else ps.delete('framework_slug');
      if(detail.competencyId) ps.set('competency_id', String(detail.competencyId)); else ps.delete('competency_id');
      if(detail.competencySlug) ps.set('competency_slug', detail.competencySlug); else ps.delete('competency_slug');
      const newUrl = `${window.location.pathname}?${ps.toString()}`;
      window.history.replaceState({}, '', newUrl);
    }catch{}
  }

  async function loadFrameworks(){
    try{
      setStatus(els.status, null, '');
      const res = await fetch('/api/frameworks?include=competencies');
      if(!res.ok) throw new Error(`Frameworks load failed (${res.status})`);
      const data = await res.json();
      // Accept either {frameworks:[...]} (Flask) or {items:[...]} (alt API)
      const raw = Array.isArray(data?.frameworks) ? data.frameworks
                 : Array.isArray(data?.items) ? data.items
                 : [];
      // Normalize into our expected shape
      const list = raw.map(fw => ({
        id: String(fw.id ?? fw.slug ?? ''),
        name: fw.name,
        slug: fw.slug || '',
        competencies: Array.isArray(fw.competencies) ? fw.competencies : undefined,
      }));
      // Restrict to the 4 specified frameworks by name, adding any missing via fallback
      frameworks = restrictToFallbackOnly(list);
      compsByFrameworkId.clear();
      for(const fw of frameworks){
        if(Array.isArray(fw.competencies)){
          const comps = fw.competencies.map(c => ({ id: String(c.id ?? c.slug ?? ''), name: c.name, slug: c.slug || '' }));
          compsByFrameworkId.set(String(fw.id), comps);
        }
      }
      populateFrameworks();
      if(!frameworks.length){
        setStatus(els.status, 'info', 'No frameworks found. Seed sample frameworks using ld-metrics-translator/seed_selected_frameworks.py.');
      }
      // Initialize from URL params if present
      try{
        const ps = new URLSearchParams(window.location.search);
        const toInt = (v) => { const n = parseInt(v, 10); return Number.isFinite(n) ? n : null; };
        // Accept string IDs via slug params as fallback
        const initFwId = ps.has('framework_id') ? ps.get('framework_id') : (ps.get('framework_slug') || null);
        const initCompId = ps.has('competency_id') ? ps.get('competency_id') : (ps.get('competency_slug') || null);
        if(initFwId){
          els.fw.value = String(initFwId);
          await populateCompetencies(initFwId);
        }
        if(initCompId){
          els.comp.value = String(initCompId);
        }
        // Emit initial filter if any preset exists
        if(initFwId || initCompId){ dispatchFilter(); }
      }catch{}
    }catch(err){
      console.error(err);
      setStatus(els.status, 'warning', err.message || 'Unable to load frameworks');
    }
  }

  function init(){
    els.fw = $('#fw-select');
    els.comp = $('#comp-select');
    els.status = document.getElementById('dc-status');

    if(els.fw){
      els.fw.addEventListener('change', () => {
        populateCompetencies(els.fw.value || null);
        // Clear competency when framework changes
        if(els.comp) els.comp.value = '';
        dispatchFilter();
      });
    }
    if(els.comp){
      els.comp.addEventListener('change', dispatchFilter);
    }

    loadFrameworks();
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
