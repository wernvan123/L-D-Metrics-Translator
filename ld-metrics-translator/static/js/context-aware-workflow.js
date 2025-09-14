// Context-Aware Workflow Manager
// Manages the user's path through the application based on their dashboard choice

class ContextAwareWorkflow {
    constructor() {
        this.currentContext = null; // 'framework' or 'outcome'
        this.selectedFramework = null;
        this.selectedOutcome = null;
        // Default scroll offset to accommodate fixed nav/hero spacing
        this.scrollOffset = 90;
        this.init();
    }

    init() {
        this.bindDashboardButtons();
        this.bindTabNavigation();
        this.loadContextFromURL();
        
        // Set default framework context if on plan tab and no context set
        setTimeout(() => {
            const currentTab = document.querySelector('.nav-tab.active')?.dataset.tab;
            if (currentTab === 'plan') {
                this.setContext('framework');
                this.applyContextToInterface();
            }
        }, 500);
        
        console.log('Context-Aware Workflow initialized');
    }

    bindDashboardButtons() {
        // Bind "Start with Framework" button
        const frameworkBtn = document.getElementById('start-framework-btn');
        if (frameworkBtn) {
            frameworkBtn.addEventListener('click', () => {
                this.setContext('framework');
                this.navigateToPlanTab();
            });
        }

        // Bind "Start with Outcome" button
        const outcomeBtn = document.getElementById('start-outcome-btn');
        if (outcomeBtn) {
            outcomeBtn.addEventListener('click', () => {
                this.setContext('outcome');
                this.navigateToPlanTab();
            });
        }
    }

    bindTabNavigation() {
        // Listen for tab changes to maintain context
        document.addEventListener('click', (e) => {
            if (e.target.matches('.nav-tab')) {
                const tabName = e.target.dataset.tab;
                if (tabName === 'plan') {
                    // Apply framework context when switching to plan tab
                    setTimeout(() => {
                        this.setContext('framework');
                        this.applyContextToInterface();
                    }, 100);
                }
            }
        });
    }

    setContext(context) {
        this.currentContext = context;
        this.updateURL();
        this.showContextIndicator(context);
        console.log(`Context set to: ${context}`);
    }

    navigateToPlanTab() {
        // Switch to Plan & Measure tab
        const planTab = document.querySelector('[data-tab="plan"]');
        const dashboardTab = document.querySelector('[data-tab="dashboard"]');
        
        if (planTab && dashboardTab) {
            // Remove active from dashboard
            dashboardTab.classList.remove('active');
            dashboardTab.setAttribute('aria-selected', 'false');
            
            // Add active to plan tab
            planTab.classList.add('active');
            planTab.setAttribute('aria-selected', 'true');
            if (planTab.dataset.tab === 'plan') {
                if (!this.currentContext) {
                    // Determine initial context based on hash or default to framework-centric
                    const hash = (window.location.hash || '').replace(/^#/, '');
                    const desired = hash.includes('outcome') ? 'outcome' : 'framework';
                    this.switchContext(desired);

                    // Apply context-specific interface
                    setTimeout(() => {
                        this.applyContextToInterface();
                        // Only auto-scroll if user explicitly navigated via dashboard CTA
                        const userInitiated = !!window.__planUserInitiated;
                        if (userInitiated) {
                            const header = document.querySelector('#tab-panel-plan .workspace-header') || planPanel;
                            this.scrollToWithOffset(header, this.scrollOffset);
                            try { delete window.__planUserInitiated; } catch (_) { window.__planUserInitiated = null; }
                        }
                    }, 100);
                }
            }
        }
    }

    applyContextToInterface() {
        if (!this.currentContext) return;

        const frameworksSection = document.getElementById('plan-frameworks-section');
        const filterSection = document.getElementById('plan-filter-section');
        const workspaceHeader = document.querySelector('.workspace-header');

        if (this.currentContext === 'framework') {
            this.showFrameworkPath(frameworksSection, filterSection, workspaceHeader);
        } else if (this.currentContext === 'outcome') {
            this.showOutcomePath(frameworksSection, filterSection, workspaceHeader);
        }

        // Notify others that context has been applied
        try {
            const evt = new CustomEvent('context:applied', { detail: { context: this.currentContext } });
            window.dispatchEvent(evt);
        } catch (_) {}
    }

    showFrameworkPath(frameworksSection, filterSection, workspaceHeader) {
        // Update header
        if (workspaceHeader) {
            workspaceHeader.innerHTML = `
                <div class="context-header">
                    <div class="context-breadcrumb">
                        <span class="breadcrumb-item">🧭 Framework-Based Approach</span>
                        <button class="btn-link context-switch" onclick="contextWorkflow.switchContext()">
                            Switch to Outcome-Based
                        </button>
                    </div>
                    <h2>Plan & Measure</h2>
                    <p>Explore frameworks and their competencies to find relevant metrics</p>
                </div>
            `;
        }

        // Show frameworks section, hide/collapse search section
        if (frameworksSection) {
            frameworksSection.style.display = 'block';
            frameworksSection.classList.add('context-primary');
        }

        if (filterSection) {
            filterSection.style.display = 'none';
            // Add a collapsed toggle option
            this.addCollapsedSearchToggle(filterSection);
        }

        this.addContextInstructions('framework');
    }

    showOutcomePath(frameworksSection, filterSection, workspaceHeader) {
        // Update header
        if (workspaceHeader) {
            workspaceHeader.innerHTML = `
                <div class="context-header">
                    <div class="context-breadcrumb">
                        <span class="breadcrumb-item">🎯 Outcome-Based Approach</span>
                        <button class="btn-link context-switch" onclick="contextWorkflow.switchContext()">
                            Switch to Framework-Based
                        </button>
                    </div>
                    <h2>Plan & Measure</h2>
                    <p>Start with your desired outcomes and discover the metrics to measure them</p>
                </div>
            `;
        }

        // Hide frameworks section, show search/filter section
        if (frameworksSection) {
            frameworksSection.style.display = 'none';
        }

        if (filterSection) {
            filterSection.style.display = 'block';
            filterSection.classList.add('context-primary');
        }

        this.addContextInstructions('outcome');
    }

    addCollapsedSearchToggle(filterSection) {
        // Create a collapsed toggle for search when in framework mode
        const toggle = document.createElement('div');
        toggle.className = 'collapsed-search-toggle';
        toggle.innerHTML = `
            <button class="btn btn-outline btn-sm toggle-search" onclick="contextWorkflow.toggleSearchSection()">
                <span class="toggle-icon">🔍</span>
                <span class="toggle-text">Also search by outcome/category</span>
                <span class="toggle-arrow">▼</span>
            </button>
        `;
        
        // Insert before the filter section
        filterSection.parentNode.insertBefore(toggle, filterSection);
    }

    addContextInstructions(context) {
        const metricsSection = document.getElementById('plan-metrics-section');
        if (!metricsSection) {
            console.log('Metrics section not found');
            return;
        }

        // Remove existing instructions
        const existingInstructions = metricsSection.querySelector('.context-instructions');
        if (existingInstructions) {
            existingInstructions.remove();
        }

        // Add context-specific instructions
        const instructions = document.createElement('div');
        instructions.className = 'context-instructions';
        console.log('Adding context instructions for:', context);
        
        if (context === 'framework') {
            instructions.innerHTML = `
                <div class="instruction-card">
                    <div class="instruction-icon">🧭</div>
                    <div class="instruction-content">
                        <h4>Framework-Based Selection</h4>
                        <p>Choose a framework above to see its competencies, then select metrics that align with those competencies.</p>
                        <div class="instruction-steps">
                            <span class="step">1. Select Framework</span>
                            <span class="step-arrow">→</span>
                            <span class="step">2. Choose Competencies</span>
                            <span class="step-arrow">→</span>
                            <span class="step">3. Pick Metrics</span>
                        </div>
                    </div>
                </div>
            `;
        } else {
            instructions.innerHTML = `
                <div class="instruction-card">
                    <div class="instruction-icon">🎯</div>
                    <div class="instruction-content">
                        <h4>Outcome-Based Selection</h4>
                        <p>Start by selecting the L&D outcomes you want to achieve, then filter by measurement approach.</p>
                        <div class="instruction-steps">
                            <span class="step">1. Choose Outcomes</span>
                            <span class="step-arrow">→</span>
                            <span class="step">2. Filter Categories</span>
                            <span class="step-arrow">→</span>
                            <span class="step">3. Select Metrics</span>
                        </div>
                    </div>
                </div>
            `;
        }

        // Insert instructions and framework dropdown
        const frameworkSelectionContainer = document.getElementById('framework-selection-container');
        if (frameworkSelectionContainer) {
            // Clear existing content
            frameworkSelectionContainer.innerHTML = '';
            
            // Add instructions first
            frameworkSelectionContainer.appendChild(instructions);
            
            // Add framework dropdown
            this.createFrameworkDropdown(frameworkSelectionContainer);
        }
    }

    async createFrameworkDropdown(container) {
        try {
            // Fetch frameworks data
            const response = await fetch('/api/frameworks?include=competencies,metrics');
            const data = await response.json();
            
            if (data.frameworks && data.frameworks.length > 0) {
                // Create dropdown container
                const dropdownContainer = document.createElement('div');
                dropdownContainer.className = 'framework-dropdown-container';
                dropdownContainer.innerHTML = `
                    <div class="dropdown-section">
                        <label for="framework-select" class="dropdown-label">
                            <strong>Step 1: Choose a Framework</strong>
                        </label>
                        <select id="framework-select" class="framework-select">
                            <option value="">Select a framework...</option>
                            ${data.frameworks.map(fw => 
                                `<option value="${fw.id}" data-slug="${fw.slug}">${fw.name}</option>`
                            ).join('')}
                        </select>
                        <div class="framework-description" id="framework-description" style="display: none;">
                            <p id="framework-desc-text"></p>
                        </div>
                    </div>
                `;
                
                container.appendChild(dropdownContainer);
                
                // Bind dropdown change event
                const select = dropdownContainer.querySelector('#framework-select');
                select.addEventListener('change', (e) => {
                    this.onFrameworkSelected(e.target.value, data.frameworks);
                });
                
                // Store frameworks data for later use
                this.frameworksData = data.frameworks;
            }
        } catch (error) {
            console.error('Error loading frameworks:', error);
        }
    }

    onFrameworkSelected(frameworkId, frameworks) {
        const selectedFramework = frameworks.find(fw => fw.id == frameworkId);
        const descriptionDiv = document.getElementById('framework-description');
        const descriptionText = document.getElementById('framework-desc-text');
        const competenciesContainer = document.getElementById('selected-framework-competencies');
        const competenciesList = document.getElementById('competencies-list');
        
        if (selectedFramework) {
            // Show framework description
            descriptionText.textContent = selectedFramework.description || '';
            descriptionDiv.style.display = 'block';
            
            // Show competencies
            competenciesList.innerHTML = '';
            if (selectedFramework.competencies && selectedFramework.competencies.length > 0) {
                const competenciesHTML = selectedFramework.competencies.map(comp => `
                    <div class="competency-item clickable-competency" 
                         data-competency-id="${comp.id}"
                         onclick="contextWorkflow.selectCompetency('${comp.id}', '${comp.name}', this)">
                        <div class="competency-header">
                            <h5>${comp.name}</h5>
                            <span class="metrics-count">${comp.metrics_count || 0} metrics</span>
                        </div>
                        <div class="competency-description">
                            Click to filter metrics for this competency
                        </div>
                    </div>
                `).join('');
                
                competenciesList.innerHTML = `
                    <div class="competencies-header">
                        <strong>Step 2: Explore Competencies</strong>
                        <p>Click any competency to filter metrics and see relevant options</p>
                    </div>
                    <div class="competencies-grid">
                        ${competenciesHTML}
                    </div>
                `;
                
                competenciesContainer.style.display = 'block';
            }
            
            // Store selected framework
            this.selectedFramework = selectedFramework;
            
            // Filter metrics by framework
            this.filterMetricsByFramework(selectedFramework.id);
            
        } else {
            // Hide descriptions and competencies
            descriptionDiv.style.display = 'none';
            competenciesContainer.style.display = 'none';
            this.selectedFramework = null;
            
            // Clear metric filters
            this.clearFrameworkFilters();
        }
    }

    selectCompetency(competencyId, competencyName, element) {
        // Clear previous selections
        document.querySelectorAll('.competency-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Highlight selected competency
        element.classList.add('selected');
        
        // Filter metrics by competency
        this.filterMetricsByCompetency(competencyId, competencyName);
        
        // Show notification
        if (window.showNotification) {
            window.showNotification(`Showing metrics for "${competencyName}" competency`, 'info');
        }
        
        // Store selected competency
        this.selectedCompetency = { id: competencyId, name: competencyName };
    }

    filterMetricsByCompetency(competencyId, competencyName) {
        const metricCards = document.querySelectorAll('.metric-card');
        const metricsSection = document.getElementById('plan-metrics-section');
        const sectionHeader = document.getElementById('metrics-section-description');
        const emptyState = document.getElementById('metrics-empty-state');
        const metricsContainer = document.getElementById('plan-metrics-container');
        
        // Hide empty state and show metrics container
        if (emptyState) emptyState.style.display = 'none';
        if (metricsContainer) metricsContainer.style.display = 'block';
        
        // For now, simulate filtering by showing only a subset of metrics
        // In a real implementation, this would use actual competency-metric relationships
        let visibleCount = 0;
        metricCards.forEach((card, index) => {
            // Show only first 3-4 metrics to simulate competency filtering
            const shouldShow = index < 4;
            card.style.display = shouldShow ? 'block' : 'none';
            if (shouldShow) visibleCount++;
        });
        
        if (sectionHeader) {
            sectionHeader.textContent = `Showing ${visibleCount} metrics for "${competencyName}" competency`;
        }
        
        // Scroll to metrics section with offset to avoid being hidden by fixed header
        if (metricsSection) {
            this.scrollToWithOffset(metricsSection, this.scrollOffset);
        }
    }

    filterMetricsByFramework(frameworkId) {
        // Filter metrics to show only those related to the selected framework
        const metricCards = document.querySelectorAll('.metric-card');
        metricCards.forEach(card => {
            // This is a placeholder - you'll need to add framework relationship data to metrics
            // For now, show all metrics when a framework is selected
            card.style.display = 'block';
        });
    }

    clearFrameworkFilters() {
        // Show empty state and hide metrics
        const emptyState = document.getElementById('metrics-empty-state');
        const metricsContainer = document.getElementById('plan-metrics-container');
        const sectionHeader = document.getElementById('metrics-section-description');
        
        if (emptyState) emptyState.style.display = 'block';
        if (metricsContainer) metricsContainer.style.display = 'none';
        if (sectionHeader) {
            sectionHeader.textContent = 'Select a framework and competency above to see relevant metrics';
        }
        
        // Clear competency selections
        document.querySelectorAll('.competency-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        this.selectedCompetency = null;
    }

    toggleSearchSection() {
        const filterSection = document.getElementById('plan-filter-section');
        const toggle = document.querySelector('.collapsed-search-toggle');
        
        if (filterSection && toggle) {
            const isVisible = filterSection.style.display !== 'none';
            
            if (isVisible) {
                filterSection.style.display = 'none';
                toggle.querySelector('.toggle-text').textContent = 'Also search by outcome/category';
                toggle.querySelector('.toggle-arrow').textContent = '▼';
            } else {
                filterSection.style.display = 'block';
                toggle.querySelector('.toggle-text').textContent = 'Hide search section';
                toggle.querySelector('.toggle-arrow').textContent = '▲';
            }
        }
    }

    switchContext() {
        const newContext = this.currentContext === 'framework' ? 'outcome' : 'framework';
        this.setContext(newContext);
        this.applyContextToInterface();
        
        // Show notification
        this.showContextSwitchNotification(newContext);
    }

    showContextSwitchNotification(newContext) {
        const message = newContext === 'framework' 
            ? 'Switched to Framework-Based approach. Select a framework to explore its competencies.'
            : 'Switched to Outcome-Based approach. Choose your desired outcomes and filter by category.';
        
        if (window.showNotification) {
            window.showNotification(message, 'info');
        }
    }

    showContextIndicator(context) {
        // Create or update context indicator
        let indicator = document.getElementById('context-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'context-indicator';
            indicator.className = 'context-indicator';
            document.body.appendChild(indicator);
        }

        const icon = context === 'framework' ? '🧭' : '🎯';
        const label = context === 'framework' ? 'Framework-Based' : 'Outcome-Based';
        
        indicator.innerHTML = `
            <div class="indicator-content">
                <span class="indicator-icon">${icon}</span>
                <span class="indicator-label">${label}</span>
            </div>
        `;
        
        indicator.className = `context-indicator context-${context} visible`;
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            indicator.classList.remove('visible');
        }, 3000);
    }

    updateURL() {
        if (!this.currentContext) return;
        
        const url = new URL(window.location);
        url.searchParams.set('context', this.currentContext);
        window.history.replaceState({}, '', url);
    }

    loadContextFromURL() {
        const url = new URL(window.location);
        const context = url.searchParams.get('context');
        
        if (context && ['framework', 'outcome'].includes(context)) {
            this.currentContext = context;
            // Apply context if we're on the plan tab
            const planPanel = document.getElementById('tab-panel-plan');
            if (planPanel && !planPanel.hidden) {
                setTimeout(() => this.applyContextToInterface(), 100);
            }
        }
    }

    // Public API for other components
    getCurrentContext() {
        return this.currentContext;
    }

    isFrameworkMode() {
        return this.currentContext === 'framework';
    }

    isOutcomeMode() {
        return this.currentContext === 'outcome';
    }

    // Smoothly scroll an element into view accounting for a fixed header offset
    scrollToWithOffset(targetEl, offset = 90) {
        if (!targetEl) return;
        const rect = targetEl.getBoundingClientRect();
        const absoluteTop = rect.top + window.pageYOffset;
        const top = Math.max(absoluteTop - offset, 0);
        window.scrollTo({ top, behavior: 'smooth' });
    }
}

// Initialize the workflow manager
let contextWorkflow;
document.addEventListener('DOMContentLoaded', () => {
    contextWorkflow = new ContextAwareWorkflow();
    
    // Make it globally available
    window.contextWorkflow = contextWorkflow;
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ContextAwareWorkflow;
}
