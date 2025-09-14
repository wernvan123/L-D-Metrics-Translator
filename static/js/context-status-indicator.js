// Simple status indicator that listens for custom events
// Usage: dispatch events on window: context:saving, context:saved, context:error
(function(){
  const el = document.getElementById('context-status-indicator');
  if (!el) return;
  const dot = el.querySelector('.dot');
  const label = el.querySelector('.label');

  function show(state, text){
    el.classList.remove('hidden');
    label.textContent = text;
    if (state === 'saving') dot.style.background = '#f0ad4e';
    else if (state === 'error') dot.style.background = '#b2002f';
    else dot.style.background = '#21b573';
    clearTimeout((window.__ctxTimer||0));
    window.__ctxTimer = setTimeout(()=>{ el.classList.add('hidden'); }, 2000);
  }

  window.addEventListener('context:saving', ()=>show('saving','Saving...'));
  window.addEventListener('context:saved', ()=>show('saved','Saved'));
  window.addEventListener('context:error', ()=>show('error','Error'));
})();
