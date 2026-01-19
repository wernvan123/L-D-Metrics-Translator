/* Session-scoped Role Profile selector helper */

const RoleSelection = (() => {
  async function fetchJSON(url, opts = {}) {
    // Ensure JSON content-type on POST/PATCH with a body so Flask parses correctly
    const base = { headers: { 'Accept': 'application/json' } };
    const hasBody = opts && opts.body != null;
    const isWrite = opts && (opts.method === 'POST' || opts.method === 'PATCH' || opts.method === 'PUT' || opts.method === 'DELETE');
    if (isWrite && hasBody) {
      base.headers['Content-Type'] = 'application/json';
    }
    const res = await fetch(url, Object.assign(base, opts));
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    return await res.json();
  }

  let _rolesCache = [];
  let _currentSelection = null;
  const _initializedSelectIds = new Set();

  async function loadRoles() {
    console.debug('[RoleSelection] fetching roles ...');
    const data = await fetchJSON('/api/roles');
    const roles = data.roles || [];
    _rolesCache = roles;
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
    // Best-effort: also persist a minimal record in session context for cross-page access
    try {
      const rec = (() => {
        if (!roleId) return null;
        const r = (_rolesCache || []).find(x => String(x.id) === String(roleId));
        return r ? { id: r.id, name: r.name, department: r.department } : { id: roleId };
      })();
      _currentSelection = rec;
      const contextPayload = {
        context_type: 'system',
        context_key: 'selected_role_profile',
        context_data: rec ? rec : { id: null },
        expires_in_hours: 24
      };
      await fetch('/api/context/store', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(contextPayload)
      });
      // Notify listeners that role context changed
      window.dispatchEvent(new CustomEvent('role:selected', { detail: rec }));
    } catch (e) {
      if (!roleId) {
        _currentSelection = null;
      }
      console.warn('[RoleSelection] failed to persist selected_role_profile', e);
    }
  }

  function populateOptions(select, roles, selectedId) {
    if (!Array.isArray(roles) || roles.length === 0) {
      select.innerHTML = '<option value="">— No roles found —</option>';
      return;
    }
    // Always render with an explicit unselected placeholder as default
    select.innerHTML = '<option value="">---- Select Role ----</option>' + roles.map(r => `<option value="${r.id}">${escapeHtml(r.name)}</option>`).join('');
    // Do not auto-select a stored id here; we require explicit user choice on this page
  }

  function escapeHtml(s) {
    return (s || '').toString().replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  }

  async function init(selectId) {
    if (_initializedSelectIds.has(selectId)) return;
    const select = document.getElementById(selectId);
    if (!select) return;
    _initializedSelectIds.add(selectId);
    try {
      console.debug('[RoleSelection] init on', selectId);
      const [roles, selectedId] = await Promise.all([loadRoles(), getSelected()]);
      // Always render with placeholder selected by default
      populateOptions(select, roles, null);
      // If there is a previously selected role in session, clear it on Diagnostics to force explicit selection
      if (selectId === 'diag-role-select' && selectedId) {
        try { await setSelected(null); } catch (e) { console.warn('[RoleSelection] unable to clear previous selection', e); }
      } else if (selectedId) {
        const r = roles.find(x => String(x.id) === String(selectedId));
        _currentSelection = r ? { id: r.id, name: r.name, department: r.department } : { id: selectedId };
      }
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

  function getCurrentSelection(){
    return _currentSelection;
  }

  return { init, getCurrentSelection };
})();

// Expose as a window-global so other scripts can access it reliably.
try {
  if (typeof window !== 'undefined') {
    window.RoleSelection = RoleSelection;
  }
} catch (_) {}

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
