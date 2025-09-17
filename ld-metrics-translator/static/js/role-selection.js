/* Session-scoped Role Profile selector helper */

const RoleSelection = (() => {
  async function fetchJSON(url, opts = {}) {
    const res = await fetch(url, Object.assign({ headers: { 'Accept': 'application/json' } }, opts));
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    return await res.json();
  }

  async function loadRoles() {
    console.debug('[RoleSelection] fetching roles ...');
    const data = await fetchJSON('/api/roles');
    const roles = data.roles || [];
    console.debug('[RoleSelection] roles received:', roles.length);
    return roles;
  }

  async function getSelected() {
    const data = await fetchJSON('/api/roles/select');
    const rid = data.selected_role_profile_id || null;
    console.debug('[RoleSelection] selected role id:', rid);
    return rid;
  }

  async function setSelected(roleId) {
    await fetchJSON('/api/roles/select', { method: 'POST', body: JSON.stringify({ role_profile_id: roleId })});
  }

  function populateOptions(select, roles, selectedId) {
    if (!Array.isArray(roles) || roles.length === 0) {
      select.innerHTML = '<option value="">— No roles found —</option>';
      return;
    }
    select.innerHTML = '<option value="">— Select Role —</option>' + roles.map(r => `<option value="${r.id}">${escapeHtml(r.name)}</option>`).join('');
    if (selectedId) {
      const opt = select.querySelector(`option[value="${selectedId}"]`);
      if (opt) select.value = String(selectedId);
    }
  }

  function escapeHtml(s) {
    return (s || '').toString().replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  }

  async function init(selectId) {
    const select = document.getElementById(selectId);
    if (!select) return;
    try {
      console.debug('[RoleSelection] init on', selectId);
      const [roles, selectedId] = await Promise.all([loadRoles(), getSelected()]);
      populateOptions(select, roles, selectedId);
    } catch (e) {
      console.error('RoleSelection init failed', e);
    }
    select.addEventListener('change', async () => {
      const val = select.value ? parseInt(select.value, 10) : null;
      try {
        await setSelected(val);
      } catch (e) {
        console.error('Failed to set selected role', e);
      }
    });
  }

  return { init };
})();

// Auto-initialize on common pages with a resilient retry to avoid race conditions
(function autoInit(){
  let attempts = 0;
  const maxAttempts = 5;
  const targets = ['diag-role-select','pb-role-select'];
  async function tryInit(){
    attempts++;
    let did = false;
    for(const id of targets){
      const el = document.getElementById(id);
      if(el){
        try{ await RoleSelection.init(id); did = true; }catch(e){ console.warn('[RoleSelection] init failed for', id, e); }
      }
    }
    if(!did && attempts < maxAttempts){
      setTimeout(tryInit, 250 * attempts); // backoff
    }
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', tryInit);
  } else {
    tryInit();
  }
  document.addEventListener('visibilitychange', () => {
    if(!document.hidden) tryInit();
  }, { once: true });
})();
