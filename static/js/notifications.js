// Simple toast notifications. Usage: window.notify('success'|'error'|'info', 'Message text')
(function(){
  const root = document.getElementById('notifications');
  function ensureRoot(){ return root || document.body.appendChild(Object.assign(document.createElement('div'),{id:'notifications', className:'notifications'})); }
  function notify(type, text, timeout=3000){
    const host = ensureRoot();
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = text;
    host.appendChild(el);
    requestAnimationFrame(()=>{ el.classList.add('show'); });
    setTimeout(()=>{ el.classList.remove('show'); el.addEventListener('transitionend', ()=>el.remove(), {once:true}); }, timeout);
  }
  window.notify = notify;
})();
