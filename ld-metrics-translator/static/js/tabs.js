// Main Tab Router for new UI structure
(function () {
  const DEBUG = false; // default off to avoid timestamp spam during scroll

  function qs(sel, root = document) { return root.querySelector(sel); }
  function qsa(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }
  const SCROLL_SYNC_KEY = 'scrollSyncEnabled';
  let scrollSyncEnabled = false; // disabled by default in new structure
  let sectionObserver = null;

  function setDebug(msg) {
    try {
      if (!DEBUG) return;
      const box = qs('#tabs-debug');
      if (box) {
        const time = new Date().toISOString();
        const line = document.createElement('div');
        line.textContent = `[${time}] ${msg}`;
        box.style.display = 'block';
        box.appendChild(line);
      }
      console.log('[tabs]', msg);
    } catch (e) {
      console.log('[tabs:debug-error]', e);
    }
  }

  let suppressObserver = false; // prevent feedback between hashchange and scroll observer
  let currentTab = null; // track current active tab to avoid duplicate work/logs

  function debounce(fn, wait = 150) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  function showTab(tab) {
    const panels = {
      dashboard: qs('#tab-panel-dashboard'),
      plan: qs('#tab-panel-plan'),
      analysis: qs('#tab-panel-analysis'),
      library: qs('#tab-panel-library')
    };
    const navBtns = qsa('.main-nav .nav-tab');
    const tabBtns = qsa('.tabs-nav .tab-btn'); // legacy support
    const keyNumbersSection = qs('#key-numbers');

    let found = false;
    Object.entries(panels).forEach(([key, el]) => {
      if (!el) return;
      const active = key === tab;
      el.hidden = !active;
      if (active) found = true;
    });

    // Hide key numbers section on non-dashboard tabs
    if (keyNumbersSection) {
      const shouldHideKeyNumbers = tab === 'plan' || tab === 'analysis' || tab === 'library';
      keyNumbersSection.style.display = shouldHideKeyNumbers ? 'none' : '';
    }

    // Update main navigation buttons
    navBtns.forEach(btn => {
      const isActive = btn.dataset.tab === tab;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', String(isActive));
    });
    
    // Update legacy tab buttons if they exist
    tabBtns.forEach(btn => {
      const isActive = btn.dataset.tab === tab;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', String(isActive));
    });

    if (!found) {
      setDebug(`Unknown tab '${tab}', defaulting to 'dashboard'`);
      showTab('dashboard');
      return;
    }

    try { localStorage.setItem('lastTab', tab); } catch (_) {}
    if (currentTab !== tab) {
      currentTab = tab;
      updateSummaries(tab);
      setDebug(`Switched to tab: ${tab}`);
    }
  }

  function parseHash() {
    const h = (window.location.hash || '').replace(/^#/, '');
    if (!h) return null;
    if (h.startsWith('tab=')) return h.split('=')[1] || 'dashboard';
    if (['dashboard', 'plan', 'analysis'].includes(h)) return h;
    return null;
  }

  function setHashForTab(tab) {
    const newHash = `#tab=${tab}`;
    if (window.location.hash !== newHash) {
      suppressObserver = true;
      window.location.hash = newHash;
      // release after tick
      setTimeout(() => (suppressObserver = false), 50);
    }
  }

  function onHashChange() {
    try {
      const tab = parseHash() || (localStorage.getItem('lastTab') || 'dashboard');
      showTab(tab);
    } catch (e) {
      setDebug(`Error handling hash change: ${e && e.message}`);
    }
  }

  // Section scroll -> tab sync (disabled by default in new structure)
  function initSectionObserver() {
    if (!scrollSyncEnabled) return;
    // Legacy section mapping - mostly disabled in new structure
    const map = new Map([
      ['#key-numbers', 'dashboard']
    ]);
    const entries = Array.from(map.keys()).map(sel => qs(sel)).filter(Boolean);
    if (!entries.length) return;

    sectionObserver = new IntersectionObserver((changes) => {
      if (suppressObserver) return;
      if (!scrollSyncEnabled) return;
      const visible = changes
        .filter(c => c.isIntersecting && c.intersectionRatio >= 0.5)
        .sort((a,b) => b.intersectionRatio - a.intersectionRatio);
      if (!visible.length) return;
      const top = visible[0].target;
      const tab = map.get('#' + top.id);
      if (tab) {
        setHashForTab(tab);
        showTab(tab);
      }
    }, { threshold: [0.5, 0.75, 1] });

    entries.forEach(el => sectionObserver.observe(el));
  }

  // Update dashboard and sidebar stats
  function updateStats() {
    try {
      // Prefer backend truth for framework counts to avoid timing/DOM order issues
      const dashboardCountEl = qs('#dashboard-frameworks-count');
      const keyNumbersCountEl = qs('#frameworks-count-card h3');

      // Fetch count from API (non-blocking update)
      fetch('/api/frameworks')
        .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
        .then(data => {
          const count = typeof data.count === 'number' ? data.count : (Array.isArray(data.frameworks) ? data.frameworks.length : 0);
          if (dashboardCountEl) dashboardCountEl.textContent = String(count);
          if (keyNumbersCountEl) keyNumbersCountEl.textContent = String(count);
        })
        .catch(() => {
          // Fallback: leave existing values as-is
        });

      // Plan sidebar initial stats (selection counts managed elsewhere)
      const planFrameworksCount = qs('#plan-frameworks-count');
      const planMetricsCount = qs('#plan-metrics-count');
      const planOutcomesCount = qs('#plan-outcomes-count');
      if (planFrameworksCount && !planFrameworksCount.dataset.userUpdated) planFrameworksCount.textContent = '0';
      if (planMetricsCount && !planMetricsCount.dataset.userUpdated) planMetricsCount.textContent = '0';
      if (planOutcomesCount && !planOutcomesCount.dataset.userUpdated) planOutcomesCount.textContent = '0';

    } catch (e) {
      setDebug(`Stats update error: ${e && e.message}`);
    }
  }

  // Update summaries when switching tabs - placeholder for tab-specific updates
  function updateSummaries(tab) {
    try {
      setDebug(`Updating summaries for tab: ${tab}`);
      
      // Update stats for all tabs
      updateStats();
      
      // Tab-specific updates
      switch (tab) {
        case 'dashboard':
          // Update dashboard-specific summaries
          updateDashboardSummaries();
          break;
        case 'plan':
          // Update plan tab summaries
          updatePlanSummaries();
          break;
        case 'analysis':
          // Update analysis tab summaries
          updateAnalysisSummaries();
          break;
        case 'library':
          // Update library tab summaries
          updateLibrarySummaries();
          break;
      }
    } catch (e) {
      setDebug(`Summary update error: ${e && e.message}`);
    }
  }

  function updateDashboardSummaries() {
    // Update dashboard key numbers and statistics
    try {
      // Framework count is handled by updateStats()
      // Add other dashboard-specific updates here
    } catch (e) {
      setDebug(`Dashboard summary error: ${e && e.message}`);
    }
  }

  function updatePlanSummaries() {
    // Update plan tab selection summaries
    try {
      // Integration with streamlined sidebar
      if (window.streamlinedSidebar) {
        window.streamlinedSidebar.updateSidebarDisplay();
      }
    } catch (e) {
      setDebug(`Plan summary error: ${e && e.message}`);
    }
  }

  function updateAnalysisSummaries() {
    // Update analysis tab specific summaries
    try {
      setDebug('Updating analysis summaries');
      // Add analysis-specific summary updates here
    } catch (e) {
      setDebug(`Analysis summary update error: ${e && e.message}`);
    }
  }

  function updateLibrarySummaries() {
    // Update library tab specific summaries
    try {
      setDebug('Updating library summaries');
      // Initialize metrics library when tab becomes active
      if (window.metricsLibrary && typeof window.metricsLibrary.initializeLibraryTab === 'function') {
        window.metricsLibrary.initializeLibraryTab();
      }
    } catch (e) {
      setDebug(`Library summary update error: ${e && e.message}`);
    }
  }

  function initFrameworksObserver() {
    const roots = ['#frameworks-browser', '#plan-frameworks-browser'];
    const debounced = debounce(() => updateStats(), 150);
    
    roots.forEach(selector => {
      const root = qs(selector);
      if (root) {
        const mo = new MutationObserver(() => debounced());
        mo.observe(root, { childList: true, subtree: true, characterData: false });
      }
    });
  }

  function updateToggleUI() {
    const btn = qs('#toggle-scroll-sync');
    if (btn) {
      btn.textContent = scrollSyncEnabled ? 'Scroll Sync: On' : 'Scroll Sync: Off';
      btn.setAttribute('aria-pressed', String(scrollSyncEnabled));
      btn.classList.toggle('off', !scrollSyncEnabled);
    }
  }

  function setScrollSyncEnabled(val) {
    scrollSyncEnabled = !!val;
    try { localStorage.setItem(SCROLL_SYNC_KEY, scrollSyncEnabled ? '1' : '0'); } catch (_) {}
    updateToggleUI();
    if (!scrollSyncEnabled && sectionObserver) {
      try { sectionObserver.disconnect(); } catch (_) {}
      sectionObserver = null;
      setDebug('Scroll sync disabled');
    } else if (scrollSyncEnabled && !sectionObserver) {
      initSectionObserver();
      setDebug('Scroll sync enabled');
    }
  }

  function init() {
    try {
      // Prevent browser from restoring scroll position on reload/navigation.
      // This can cause the Plan tab header to appear partially hidden on initial load.
      try { if ('scrollRestoration' in history) { history.scrollRestoration = 'manual'; } } catch (_) {}

      // Check for main navigation
      const mainNav = qs('.main-nav');
      const navBtns = qsa('.main-nav .nav-tab');
      const legacyBtns = qsa('.tabs-nav .tab-btn');
      
      if (!mainNav && !legacyBtns.length) {
        setDebug('No navigation found; skipping init');
        return;
      }

      // Load persisted scroll sync preference (disabled by default)
      try {
        const v = localStorage.getItem(SCROLL_SYNC_KEY);
        if (v !== null) scrollSyncEnabled = (v === '1' || v === 'true');
      } catch (_) {}

      // Wire up main navigation
      navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          const tab = btn.dataset.tab;
          setHashForTab(tab);
          showTab(tab);
        });
      });
      
      // Wire up legacy tab buttons if they exist
      legacyBtns.forEach(btn => {
        btn.addEventListener('click', () => {
          const tab = btn.dataset.tab;
          setHashForTab(tab);
          showTab(tab);
        });
      });

      // Wire up dashboard CTAs
      const frameworkBtn = qs('#start-framework-btn');
      const outcomeBtn = qs('#start-outcome-btn');
      
      if (frameworkBtn) {
        frameworkBtn.addEventListener('click', () => {
          // Mark this navigation as user-initiated (framework path)
          try { window.__planUserInitiated = 'framework'; } catch (_) {}
          setHashForTab('plan');
          showTab('plan');
          // Focus on frameworks section
          setTimeout(() => {
            const section = qs('#plan-frameworks-section');
            if (section) section.scrollIntoView({ behavior: 'smooth' });
          }, 100);
        });
      }
      
      if (outcomeBtn) {
        outcomeBtn.addEventListener('click', () => {
          // Mark this navigation as user-initiated (outcome path)
          try { window.__planUserInitiated = 'outcome'; } catch (_) {}
          setHashForTab('plan');
          showTab('plan');
          // Could trigger outcome selection UI here
        });
      }

      window.addEventListener('hashchange', onHashChange);
      initSectionObserver();
      initFrameworksObserver();

      // Wire up controls if present
      const clearBtn = qs('#clear-last-tab');
      if (clearBtn) {
        clearBtn.addEventListener('click', () => {
          try { localStorage.removeItem('lastTab'); } catch (_) {}
          setDebug('Cleared lastTab');
        });
      }

      const toggleBtn = qs('#toggle-scroll-sync');
      if (toggleBtn) {
        toggleBtn.addEventListener('click', () => setScrollSyncEnabled(!scrollSyncEnabled));
        updateToggleUI();
      }

      // Initial state
      const firstTab = parseHash() || (localStorage.getItem('lastTab') || 'dashboard');
      if (!parseHash()) setHashForTab(firstTab);
      showTab(firstTab);
      updateStats();
      // Retry shortly to catch late async UI/content
      setTimeout(updateStats, 300);
      setTimeout(updateStats, 1000);
      
      // Ensure we start at the very top when landing directly on the Plan tab
      // to avoid the heading/subheading being obscured by prior scroll position.
      if (firstTab === 'plan') {
        const root = document.documentElement;
        const prevBehavior = root.style.scrollBehavior;
        // Temporarily disable smooth behavior to avoid animated jumps
        root.style.scrollBehavior = 'auto';
        window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
        // Restore any prior inline behavior on next tick
        setTimeout(() => { root.style.scrollBehavior = prevBehavior; }, 0);

        // Add a short-lived scroll lock to counter any late programmatic scrolls
        // that might occur during other component initializations.
        const lockStart = Date.now();
        const lockDuration = 1500; // ms — slightly longer to cover delayed inits

        // 1) Temporarily disable any CSS smooth scrolling globally
        const styleEl = document.createElement('style');
        styleEl.setAttribute('data-scroll-lock', 'true');
        styleEl.textContent = `html{scroll-behavior:auto !important}`;
        document.head.appendChild(styleEl);

        // 2) Temporarily neutralize scrollIntoView calls
        const proto = Element.prototype;
        const originalScrollIntoView = proto.scrollIntoView;
        const originalFocus = proto.focus;
        try {
          const original = originalScrollIntoView;
          proto.scrollIntoView = function lockedScrollIntoView() {
            if (Date.now() - lockStart <= lockDuration) {
              console.warn('[tabs] Suppressed scrollIntoView during lock');
              if (typeof console.trace === 'function') console.trace();
              return; // block during lock
            }
            return original.apply(this, arguments);
          };
        } catch (_) {}

        // 2b) Temporarily override focus() to avoid scroll jumps while still focusing
        try {
          proto.focus = function lockedFocus() {
            if (Date.now() - lockStart <= lockDuration) {
              try {
                // Prefer preventScroll when available
                return originalFocus.call(this, { preventScroll: true });
              } catch (_) {
                // Fallback: focus without options (may scroll in old browsers)
                return originalFocus.call(this);
              }
            }
            return originalFocus.apply(this, arguments);
          };
        } catch (_) {}

        // 3) Enforce top on any scroll attempts during the lock window
        const enforceTop = () => {
          if (Date.now() - lockStart > lockDuration) {
            window.removeEventListener('scroll', enforceTop, { capture: false });
            return;
          }
          if (window.scrollY > 0) window.scrollTo(0, 0);
        };
        window.addEventListener('scroll', enforceTop, { passive: true });

        // 3b) Temporarily wrap window.scrollTo to suppress downward programmatic scrolls
        const originalScrollTo = window.scrollTo.bind(window);
        window.scrollTo = function wrappedScrollTo(a, b) {
          const withinLock = Date.now() - lockStart <= lockDuration;
          try {
            // Attempt to detect target top value from args
            let targetTop = 0;
            if (typeof a === 'object' && a !== null) {
              targetTop = typeof a.top === 'number' ? a.top : 0;
            } else {
              targetTop = typeof b === 'number' ? b : 0;
            }
            if (withinLock && targetTop > 0) {
              // Debug log the suppressed call to help identify source
              console.warn('[tabs] Suppressed scrollTo during lock', a, b);
              if (typeof console.trace === 'function') console.trace();
              return; // block downward scroll during lock
            }
          } catch (_) {
            // fail open to avoid breaking
          }
          return originalScrollTo(a, b);
        };

        // 4) Schedule a few top resets to outlast late async tasks
        const resets = [0, 60, 120, 240, 480, 960, 1440];
        resets.forEach(delay => setTimeout(() => window.scrollTo(0, 0), delay));

        // 5) Cleanup after lock window expires
        setTimeout(() => {
          try { proto.scrollIntoView = originalScrollIntoView; } catch (_) {}
          try { proto.focus = originalFocus; } catch (_) {}
          if (styleEl && styleEl.parentNode) styleEl.parentNode.removeChild(styleEl);
          try { window.scrollTo = originalScrollTo; } catch (_) {}
        }, lockDuration + 10);
      }
      // Refresh counts when context workflow applies UI changes
      try {
        window.addEventListener('context:applied', () => {
          updateStats();
        });
      } catch (_) {}
      setDebug('Tabs initialized');
    } catch (e) {
      setDebug(`Init error: ${e && e.message}`);
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
