// Interactive Competency Filters: Make framework competencies clickable filters for metrics
// Integrates with existing frameworks.js and filtering system

class InteractiveCompetencyFilters {
    constructor() {
        this.selectedCompetencies = new Set();
        this.competencyMetricsMap = new Map(); // competencyId -> Set of metricIds
        this.isInitialized = false;
        
        this.init();
    }
    
    async init() {
        if (this.isInitialized) return;
        
        try {
            await this.loadCompetencyMetricsMapping();
            this.enhanceFrameworkBrowser();
            this.setupEventListeners();
            this.isInitialized = true;
            console.log('Interactive Competency Filters initialized');
        } catch (error) {
            console.error('Failed to initialize Interactive Competency Filters:', error);
        }
    }
    
    async loadCompetencyMetricsMapping() {
        try {
            // Load all frameworks with competencies and their metrics
            const response = await fetch('/api/frameworks?include_competencies=true&include_metrics=true');
            if (!response.ok) throw new Error('Failed to load frameworks data');
            
            const data = await response.json();
            const frameworks = data.frameworks || [];
            
            // Build mapping of competency -> metrics and store competency info
            this.competencyInfo = new Map(); // Store competency details for lookup
            
            frameworks.forEach(framework => {
                if (framework.competencies) {
                    framework.competencies.forEach(competency => {
                        // Store competency info for name-based lookup
                        this.competencyInfo.set(competency.id, {
                            id: competency.id,
                            name: competency.name,
                            slug: competency.slug,
                            frameworkId: framework.id,
                            frameworkName: framework.name
                        });
                        
                        // Store competency name -> id mapping for easier lookup
                        this.competencyInfo.set(competency.name, competency.id);
                        
                        if (competency.metrics && competency.metrics.length > 0) {
                            const metricIds = new Set(competency.metrics.map(m => m.id));
                            this.competencyMetricsMap.set(competency.id, metricIds);
                        }
                    });
                }
            });
            
            console.log(`Loaded ${this.competencyMetricsMap.size} competency-metric mappings`);
            console.log(`Loaded ${frameworks.length} frameworks with competencies`);
        } catch (error) {
            console.error('Error loading competency metrics mapping:', error);
        }
    }
    
    enhanceFrameworkBrowser() {
        // Wait for frameworks to be loaded and then enhance them
        const checkAndEnhance = () => {
            const frameworksContainer = document.getElementById('plan-frameworks-browser');
            if (!frameworksContainer || frameworksContainer.children.length === 0) {
                setTimeout(checkAndEnhance, 500);
                return;
            }
            
            this.addCompetencyFilterButtons();
        };
        
        checkAndEnhance();
    }
    
    addCompetencyFilterButtons() {
        const competencyRows = document.querySelectorAll('.fw-comp');
        
        competencyRows.forEach(row => {
            // Skip if already enhanced
            if (row.querySelector('.competency-filter-btn')) return;
            
            // Extract competency info from the row
            const competencyName = row.querySelector('.fw-comp-name')?.textContent?.trim();
            const metricsCountText = row.querySelector('.fw-comp-metrics')?.textContent?.trim();
            
            if (!competencyName) return;
            
            // Try to find competency ID from data attributes or by name matching
            const competencyId = this.findCompetencyId(competencyName);
            if (!competencyId) return;
            
            // Create filter button
            const filterBtn = document.createElement('button');
            filterBtn.className = 'competency-filter-btn';
            filterBtn.innerHTML = '🔍 Filter';
            filterBtn.title = `Filter metrics by ${competencyName}`;
            filterBtn.dataset.competencyId = competencyId;
            filterBtn.dataset.competencyName = competencyName;
            
            // Add click handler
            filterBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // Prevent row expansion
                this.toggleCompetencyFilter(competencyId, competencyName);
            });
            
            // Add the button to the row
            const actionsContainer = document.createElement('div');
            actionsContainer.className = 'fw-comp-actions';
            actionsContainer.appendChild(filterBtn);
            row.appendChild(actionsContainer);
        });
    }
    
    findCompetencyId(competencyName) {
        // Use the competencyInfo map to find ID by name
        if (this.competencyInfo && this.competencyInfo.has(competencyName)) {
            const competencyId = this.competencyInfo.get(competencyName);
            // If it's already an ID (number), return it; if it's a name, get the mapped ID
            return typeof competencyId === 'number' ? competencyId : competencyId;
        }
        
        // Fallback: try to find by partial name match
        for (const [key, value] of this.competencyInfo.entries()) {
            if (typeof key === 'string' && key.toLowerCase().includes(competencyName.toLowerCase())) {
                return typeof value === 'number' ? value : value.id;
            }
        }
        
        return null;
    }
    
    toggleCompetencyFilter(competencyId, competencyName) {
        const isSelected = this.selectedCompetencies.has(competencyId);
        
        if (isSelected) {
            this.selectedCompetencies.delete(competencyId);
            this.removeCompetencyFilter(competencyId);
        } else {
            this.selectedCompetencies.add(competencyId);
            this.addCompetencyFilter(competencyId, competencyName);
        }
        
        this.updateFilterButtons();
        this.applyCompetencyFilters();
        this.updateActiveFiltersDisplay();
    }
    
    addCompetencyFilter(competencyId, competencyName) {
        // Add to active filters display
        const activeFiltersContainer = document.getElementById('plan-active-filters-list');
        if (!activeFiltersContainer) return;
        
        const filterTag = document.createElement('div');
        filterTag.className = 'active-filter-tag competency-filter';
        filterTag.dataset.competencyId = competencyId;
        filterTag.innerHTML = `
            <span class="filter-icon">🎯</span>
            <span class="filter-text">${competencyName}</span>
            <button class="filter-remove" onclick="window.interactiveCompetencyFilters.removeCompetencyFilter('${competencyId}')">
                ×
            </button>
        `;
        
        activeFiltersContainer.appendChild(filterTag);
        
        // Show active filters section
        const activeFiltersSection = document.getElementById('plan-active-filters');
        if (activeFiltersSection) {
            activeFiltersSection.style.display = 'block';
        }
    }
    
    removeCompetencyFilter(competencyId) {
        this.selectedCompetencies.delete(competencyId);
        
        // Remove from active filters display
        const filterTag = document.querySelector(`[data-competency-id="${competencyId}"]`);
        if (filterTag) {
            filterTag.remove();
        }
        
        // Hide active filters section if empty
        const activeFiltersContainer = document.getElementById('plan-active-filters-list');
        const activeFiltersSection = document.getElementById('plan-active-filters');
        if (activeFiltersContainer && activeFiltersContainer.children.length === 0 && activeFiltersSection) {
            activeFiltersSection.style.display = 'none';
        }
        
        this.updateFilterButtons();
        this.applyCompetencyFilters();
    }
    
    updateFilterButtons() {
        const filterButtons = document.querySelectorAll('.competency-filter-btn');
        
        filterButtons.forEach(btn => {
            const competencyId = btn.dataset.competencyId;
            const isSelected = this.selectedCompetencies.has(competencyId);
            
            if (isSelected) {
                btn.classList.add('active');
                btn.innerHTML = '✓ Filtering';
                btn.style.background = '#667eea';
                btn.style.color = 'white';
            } else {
                btn.classList.remove('active');
                btn.innerHTML = '🔍 Filter';
                btn.style.background = '';
                btn.style.color = '';
            }
        });
    }
    
    applyCompetencyFilters() {
        if (this.selectedCompetencies.size === 0) {
            // No competency filters active, show all metrics
            this.showAllMetrics();
            return;
        }
        
        // Get all metric IDs that match selected competencies
        const matchingMetricIds = new Set();
        
        for (const competencyId of this.selectedCompetencies) {
            const metricIds = this.competencyMetricsMap.get(competencyId);
            if (metricIds) {
                metricIds.forEach(id => matchingMetricIds.add(id));
            }
        }
        
        // Filter metrics display
        this.filterMetricsByIds(matchingMetricIds);
        
        // Update metrics count
        this.updateMetricsCount(matchingMetricIds.size);
        
        // Trigger event for other components
        this.dispatchFilterEvent(matchingMetricIds);
    }
    
    filterMetricsByIds(metricIds) {
        const metricCards = document.querySelectorAll('.metric-card');
        
        metricCards.forEach(card => {
            const metricId = parseInt(card.dataset.id);
            
            if (metricIds.has(metricId)) {
                card.style.display = 'block';
                card.classList.remove('filtered-out');
            } else {
                card.style.display = 'none';
                card.classList.add('filtered-out');
            }
        });
    }
    
    showAllMetrics() {
        const metricCards = document.querySelectorAll('.metric-card');
        
        metricCards.forEach(card => {
            card.style.display = 'block';
            card.classList.remove('filtered-out');
        });
        
        this.updateMetricsCount(metricCards.length);
    }
    
    updateMetricsCount(count) {
        // Update metrics section header with count
        const metricsHeader = document.querySelector('#plan-metrics-section .section-header h3');
        if (metricsHeader) {
            const baseText = '📊 Available Metrics';
            metricsHeader.textContent = `${baseText} (${count})`;
        }
    }
    
    updateActiveFiltersDisplay() {
        // This method can be enhanced to show more detailed filter information
        const activeCount = this.selectedCompetencies.size;
        
        if (activeCount > 0) {
            // Update context indicator if available
            const contextIndicator = document.querySelector('.context-indicator');
            if (contextIndicator) {
                const competencyText = activeCount === 1 ? 'competency' : 'competencies';
                contextIndicator.innerHTML = `
                    <span class="context-icon">🎯</span>
                    <span class="context-text">Filtering by ${activeCount} ${competencyText}</span>
                `;
            }
        }
    }
    
    dispatchFilterEvent(metricIds) {
        // Dispatch custom event for other components to listen to
        const event = new CustomEvent('competencyFiltersChanged', {
            detail: {
                selectedCompetencies: Array.from(this.selectedCompetencies),
                matchingMetricIds: Array.from(metricIds),
                filterCount: this.selectedCompetencies.size
            }
        });
        
        document.dispatchEvent(event);
    }
    
    setupEventListeners() {
        // Listen for framework browser updates
        document.addEventListener('frameworksLoaded', () => {
            setTimeout(() => this.addCompetencyFilterButtons(), 100);
        });
        
        // Listen for clear all filters
        document.addEventListener('clearAllFilters', () => {
            this.clearAllCompetencyFilters();
        });
        
        // Integration with existing filter system
        document.addEventListener('filtersCleared', () => {
            this.clearAllCompetencyFilters();
        });
    }
    
    clearAllCompetencyFilters() {
        // Clear all selected competencies
        this.selectedCompetencies.clear();
        
        // Remove all competency filter tags
        const competencyFilterTags = document.querySelectorAll('.competency-filter');
        competencyFilterTags.forEach(tag => tag.remove());
        
        // Update button states
        this.updateFilterButtons();
        
        // Show all metrics
        this.showAllMetrics();
        
        // Hide active filters if empty
        const activeFiltersContainer = document.getElementById('plan-active-filters-list');
        const activeFiltersSection = document.getElementById('plan-active-filters');
        if (activeFiltersContainer && activeFiltersContainer.children.length === 0 && activeFiltersSection) {
            activeFiltersSection.style.display = 'none';
        }
    }
    
    // Public API methods
    getSelectedCompetencies() {
        return Array.from(this.selectedCompetencies);
    }
    
    getMatchingMetrics() {
        const matchingMetricIds = new Set();
        
        for (const competencyId of this.selectedCompetencies) {
            const metricIds = this.competencyMetricsMap.get(competencyId);
            if (metricIds) {
                metricIds.forEach(id => matchingMetricIds.add(id));
            }
        }
        
        return Array.from(matchingMetricIds);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.interactiveCompetencyFilters = new InteractiveCompetencyFilters();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = InteractiveCompetencyFilters;
}
