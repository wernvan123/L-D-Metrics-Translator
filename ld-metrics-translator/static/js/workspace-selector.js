(function(){
  function $(sel){ return document.querySelector(sel); }
  function requiresWorkspace(){
    const v = document.body && document.body.dataset ? document.body.dataset.requiresWorkspace : null;
    return String(v || '0') === '1';
  }
  async function fetchJSON(url, opts){
    const r = await fetch(url, Object.assign({ headers: { 'Accept':'application/json' } }, opts||{}));
    if(!r.ok) throw new Error('HTTP '+r.status);
    return await r.json();
  }

  function esc(s){
    return (s||'').toString().replace(/[&<>"']/g, c=>({
      '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
    }[c]));
  }

  function setStatus(msg, kind){
    const el = $('#workspace-status');
    if(!el) return;
    if(!msg){ el.style.display='none'; el.textContent=''; el.className='workspace-status'; return; }
    el.style.display='inline-flex';
    el.textContent = msg;
    el.className = 'workspace-status' + (kind ? ` ${kind}` : '');
  }

  function setLabel(){
    const clientSel = $('#workspace-client');
    const engSel = $('#workspace-engagement');
    const lbl = $('#workspace-label');
    if(!lbl) return;
    const c = clientSel && clientSel.value ? clientSel.options[clientSel.selectedIndex]?.textContent : 'No client';
    const e = engSel && engSel.value ? engSel.options[engSel.selectedIndex]?.textContent : 'No engagement';
    lbl.textContent = `${c} / ${e}`;
  }

  function setDisabled(disabled){
    const clientSel = $('#workspace-client');
    const engSel = $('#workspace-engagement');
    const btnApply = $('#workspace-apply');
    const btnNew = $('#workspace-new-engagement');
    const btnNewClient = $('#workspace-new-client');
    if(clientSel) clientSel.disabled = disabled;
    if(engSel) engSel.disabled = disabled;
    if(btnApply) btnApply.disabled = disabled;
    if(btnNew) btnNew.disabled = disabled;
    if(btnNewClient) btnNewClient.disabled = disabled;
  }

  function setGateVisible(visible){
    const gate = $('#workspace-gate');
    if(!gate) return;

    const header = document.querySelector('header.header');
    const headerH = header ? header.getBoundingClientRect().height : 0;
    document.documentElement.style.setProperty('--workspace-gate-top', `${Math.max(0, Math.round(headerH))}px`);

    gate.style.display = visible ? 'flex' : 'none';
    gate.setAttribute('aria-hidden', visible ? 'false' : 'true');
  }

  function updateGateFromState(st){
    if(!requiresWorkspace()){
      setGateVisible(false);
      return;
    }
    const ok = !!(st && st.active_client && st.active_engagement);
    setGateVisible(!ok);
  }

  async function loadClients(activeClientId){
    const clientSel = $('#workspace-client');
    if(!clientSel) return;
    const data = await fetchJSON('/api/workspace/clients');
    const clients = data.clients || [];
    clientSel.innerHTML = '<option value="">Select client…</option>' + clients.map(c=>`<option value="${c.id}">${esc(c.name)}</option>`).join('');
    if(activeClientId){
      clientSel.value = String(activeClientId);
    }
  }

  async function loadEngagements(clientId, activeEngagementId){
    const engSel = $('#workspace-engagement');
    if(!engSel) return;
    if(!clientId){
      engSel.innerHTML = '<option value="">Select engagement…</option>';
      engSel.value = '';
      return;
    }
    const data = await fetchJSON(`/api/workspace/clients/${encodeURIComponent(clientId)}/engagements`);
    const engagements = data.engagements || [];
    engSel.innerHTML = '<option value="">Select engagement…</option>' + engagements.map(e=>`<option value="${e.id}">${esc(e.name)}</option>`).join('');
    if(activeEngagementId){
      engSel.value = String(activeEngagementId);
    }
  }

  async function loadState(){
    const st = await fetchJSON('/api/workspace/state');
    const activeClientId = st.active_client ? st.active_client.id : null;
    const activeEngagementId = st.active_engagement ? st.active_engagement.id : null;

    await loadClients(activeClientId);
    await loadEngagements(activeClientId, activeEngagementId);
    setLabel();
    updateGateFromState(st);
    return st;
  }

  async function applySelection(){
    const clientSel = $('#workspace-client');
    const engSel = $('#workspace-engagement');
    const payload = {
      client_id: clientSel ? (clientSel.value || null) : null,
      engagement_id: engSel ? (engSel.value || null) : null,
    };

    setDisabled(true);
    setStatus('Saving…', 'info');
    try{
      const data = await fetchJSON('/api/workspace/select', {
        method:'POST',
        headers: { 'Content-Type':'application/json', 'Accept':'application/json' },
        body: JSON.stringify(payload)
      });
      if(!data.success) throw new Error(data.error || 'Failed');
      setStatus('Workspace saved', 'ok');
      setTimeout(()=>setStatus(''), 1500);
      setLabel();
      updateGateFromState(data);
      window.dispatchEvent(new CustomEvent('workspace:changed', { detail: data }));
    } catch(e){
      setStatus('Failed to save workspace', 'err');
    } finally {
      setDisabled(false);
    }
  }

  async function createEngagement(){
    const clientSel = $('#workspace-client');
    if(!clientSel || !clientSel.value){
      setStatus('Select a client first', 'err');
      setTimeout(()=>setStatus(''), 2000);
      return;
    }
    const name = window.prompt('Engagement name (e.g., 6-week Diagnostic Sprint):');
    if(!name || !name.trim()) return;

    setDisabled(true);
    setStatus('Creating…', 'info');
    try{
      const data = await fetchJSON('/api/workspace/engagements', {
        method:'POST',
        headers: { 'Content-Type':'application/json', 'Accept':'application/json' },
        body: JSON.stringify({ client_id: clientSel.value, name: name.trim() })
      });
      if(!data.success) throw new Error(data.error || 'Failed');
      await loadEngagements(clientSel.value, data.engagement ? data.engagement.id : null);
      const engSel = $('#workspace-engagement');
      if(engSel && data.engagement && data.engagement.id){
        engSel.value = String(data.engagement.id);
      }
      await applySelection();
    } catch(e){
      setStatus('Failed to create engagement', 'err');
    } finally {
      setDisabled(false);
    }
  }

  async function createClient(){
    const name = window.prompt('Client name (e.g., Monkey & River):');
    if(!name || !name.trim()) return;

    setDisabled(true);
    setStatus('Creating…', 'info');
    try{
      const data = await fetchJSON('/api/workspace/clients', {
        method:'POST',
        headers: { 'Content-Type':'application/json', 'Accept':'application/json' },
        body: JSON.stringify({ name: name.trim() })
      });
      if(!data.success) throw new Error(data.error || 'Failed');

      const activeClientId = data.active_client ? data.active_client.id : (data.client ? data.client.id : null);
      await loadClients(activeClientId);
      await loadEngagements(activeClientId, null);
      setLabel();
      updateGateFromState(data);
      setStatus('Client created. Create/select an engagement.', 'ok');
      setTimeout(()=>setStatus(''), 2500);
    } catch(e){
      setStatus('Failed to create client', 'err');
    } finally {
      setDisabled(false);
    }
  }

  function bind(){
    const clientSel = $('#workspace-client');
    const engSel = $('#workspace-engagement');
    const btnApply = $('#workspace-apply');
    const btnNew = $('#workspace-new-engagement');
    const btnNewClient = $('#workspace-new-client');

    if(clientSel){
      clientSel.addEventListener('change', async ()=>{
        const cid = clientSel.value;
        await loadEngagements(cid, null);
        setLabel();
      });
    }
    if(engSel){
      engSel.addEventListener('change', ()=>setLabel());
    }
    if(btnApply){
      btnApply.addEventListener('click', (e)=>{ e.preventDefault(); applySelection(); });
    }
    if(btnNew){
      btnNew.addEventListener('click', (e)=>{ e.preventDefault(); createEngagement(); });
    }
    if(btnNewClient){
      btnNewClient.addEventListener('click', (e)=>{ e.preventDefault(); createClient(); });
    }
  }

  async function init(){
    const root = $('#workspace-bar');
    if(!root) return;
    bind();
    try {
      await loadState();
    } catch(e) {
      setStatus('Workspace unavailable', 'err');
      updateGateFromState(null);
    }
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
