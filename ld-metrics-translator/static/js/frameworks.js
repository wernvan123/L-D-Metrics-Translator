// Frameworks Browser: fetch and render frameworks/competencies for framework-centric navigation
// Depends on fetch API; no external deps. Non-invasive to existing UI.

const FrameworksBrowser = (() => {
  const API_BASE = '/api';
  const qs = (sel, root=document) => root.querySelector(sel);
  const qsa = (sel, root=document) => Array.from(root.querySelectorAll(sel));

  function el(tag, className, html) {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (html !== undefined) n.innerHTML = html;
    return n;
  }

  async function fetchFrameworks() {
    const url = `${API_BASE}/frameworks?include=competencies`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to load frameworks: ${res.status}`);
    return res.json();
  }

  function renderFrameworkCard(fw) {
    const card = el('div', 'fw-card');
    const header = el('div', 'fw-header');
    header.append(
      el('div', 'fw-title', `<strong>${fw.name}</strong>`),
      el('div', 'fw-meta', `${fw.competency_count || 0} competencies`)
    );

    const desc = el('div', 'fw-desc', fw.description || '');

    const compList = el('div', 'fw-competencies');
    (fw.competencies || []).forEach(c => {
      const row = el('div', 'fw-comp');
      const nameSpan = el('span', 'fw-comp-name', c.name);
      const countSpan = el('span', 'fw-comp-metrics', `${c.metrics_count || 0} metrics`);
      row.append(
        nameSpan,
        countSpan
      );
      row.addEventListener('click', async () => {
        // Lazy-load metrics for this framework if needed
        if (!row.dataset.loaded) {
          try {
            const res = await fetch(`${API_BASE}/frameworks/${fw.id}?include=metrics`);
            if (res.ok) {
              const data = await res.json();
              const found = (data.framework?.competencies || []).find(x => x.id === c.id || x.slug === c.slug);
              if (found && (found.metrics || []).length) {
                const ul = el('ul', 'fw-metric-list');
                found.metrics.slice(0, 6).forEach(m => {
                  const li = el('li', 'fw-metric-item');
                  li.textContent = m.name;
                  ul.append(li);
                });
                row.append(ul);
                // Update metrics count based on loaded data
                try {
                  const count = (found.metrics || []).length;
                  countSpan.textContent = `${count} metrics`;
                } catch (_) {
                  // non-fatal
                }
              }
              row.dataset.loaded = '1';
              row.classList.add('expanded');
            }
          } catch (e) {
            // non-fatal
          }
        } else {
          row.classList.toggle('expanded');
        }
      });
      compList.append(row);
    });

    card.append(header, desc, compList);
    return card;
  }

  function render(container, frameworks) {
    container.innerHTML = '';
    const grid = el('div', 'fw-grid');
    frameworks.forEach(fw => grid.append(renderFrameworkCard(fw)));
    container.append(grid);
  }

  async function init() {
    const containers = ['#frameworks-browser', '#plan-frameworks-browser'];
    const data = await fetchFrameworks().catch(() => ({ frameworks: [], count: 0 }));
    const frameworks = data.frameworks || [];
    // Update global UI counts where applicable (prefer API total, fallback to array length)
    try {
      const calcTotal = typeof data.count === 'number' ? data.count : (typeof data.total === 'number' ? data.total : frameworks.length);
      const dashEl = qs('#dashboard-frameworks-count');
      if (dashEl) dashEl.textContent = String(calcTotal);
      const keyNumbersEl = qs('#frameworks-count-card h3');
      if (keyNumbersEl) keyNumbersEl.textContent = String(calcTotal);
    } catch (_) {
      // non-fatal
    }
    
    containers.forEach(selector => {
      const container = qs(selector);
      if (!container) return;
      
      if (frameworks.length === 0) {
        container.innerHTML = '<div class="fw-empty">No frameworks available yet.</div>';
        return;
      }
      
      try {
        render(container, frameworks);
      } catch (e) {
        container.innerHTML = `<div class="fw-error">${e.message || 'Failed to load frameworks'}</div>`;
      }
    });
  }

  return { init };
})();

window.addEventListener('DOMContentLoaded', () => {
  FrameworksBrowser.init();
});
