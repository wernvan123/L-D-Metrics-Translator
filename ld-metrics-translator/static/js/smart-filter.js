// Smart Filter Integration for L&D Metrics Translator
// Integrates dropdown navigation with search and filtering

class SmartFilterManager {
    constructor() {
        this.dropdownNav = null;
        this.searchManager = null;
        this.activeFilters = {
            search: '',
            category: null,
            outcome: null,
            metric: null,
            neuroscience: null
        };
        this.metricCards = [];
        this.originalOrder = [];
        this.filteredResults = [];
        
        this.init();
    }

    init() {
        // Wait for other managers to initialize
        document.addEventListener('DOMContentLoaded', () => {
            setTimeout(() => {
                this.dropdownNav = window.dropdownNav;
                this.searchManager = window.searchManager;
                this.setupIntegration();
                this.cacheMetricCards();
                this.setupSearchIntegration();
                this.setupFilterUI();
            }, 500);
        });
    }

    setupIntegration() {
        // Override dropdown selection methods to trigger filtering
        if (this.dropdownNav) {
            const originalSelectCategory = this.dropdownNav.selectMetricCategory.bind(this.dropdownNav);
            const originalSelectOutcome = this.dropdownNav.selectOutcome.bind(this.dropdownNav);
            const originalSelectMetric = this.dropdownNav.selectMetric.bind(this.dropdownNav);
            const originalSelectNeuroscience = this.dropdownNav.selectNeuroscienceMetric.bind(this.dropdownNav);

            this.dropdownNav.selectMetricCategory = (id, name) => {
                originalSelectCategory(id, name);
                this.activeFilters.category = { id, name };
                this.applySmartFiltering();
            };

            this.dropdownNav.selectOutcome = (id, name) => {
                originalSelectOutcome(id, name);
                this.activeFilters.outcome = { id, name };
                this.applySmartFiltering();
            };

            this.dropdownNav.selectMetric = (id, name) => {
                originalSelectMetric(id, name);
                this.activeFilters.metric = { id, name };
                this.applySmartFiltering();
            };

            this.dropdownNav.selectNeuroscienceMetric = (id, name) => {
                originalSelectNeuroscience(id, name);
                this.activeFilters.neuroscience = { id, name };
                this.applySmartFiltering();
            };
        }
    }

    setupSearchIntegration() {
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.activeFilters.search = e.target.value.trim();
                this.applySmartFiltering();
            });

            // Clear search integration
            const clearBtn = document.getElementById('clear-search');
            if (clearBtn) {
                clearBtn.addEventListener('click', () => {
                    this.activeFilters.search = '';
                    this.applySmartFiltering();
                });
            }
        }
    }

    cacheMetricCards() {
        this.metricCards = Array.from(document.querySelectorAll('.metric-card'));
        this.originalOrder = this.metricCards.map((card, index) => ({
            element: card,
            originalIndex: index,
            data: this.extractCardData(card)
        }));
    }

    extractCardData(card) {
        return {
            name: card.querySelector('.metric-title')?.textContent?.toLowerCase() || '',
            description: card.querySelector('.metric-description')?.textContent?.toLowerCase() || '',
            type: card.querySelector('.metric-type')?.textContent?.toLowerCase() || '',
            outcome: card.querySelector('.metric-outcome')?.textContent?.toLowerCase() || '',
            categoryId: card.dataset.categoryId || '',
            outcomeId: card.dataset.outcomeId || '',
            metricId: card.dataset.metricId || '',
            example: card.querySelector('.metric-example')?.textContent?.toLowerCase() || ''
        };
    }

    applySmartFiltering() {
        this.filteredResults = this.originalOrder.filter(item => this.matchesFilters(item));
        this.sortByRelevance();
        this.updateDisplay();
        this.updateFilterSummary();
        this.updateResultsCount();
    }

    matchesFilters(item) {
        const { data } = item;
        
        // Search filter
        if (this.activeFilters.search) {
            const searchTerm = this.activeFilters.search.toLowerCase();
            const searchableText = `${data.name} ${data.description} ${data.type} ${data.outcome} ${data.example}`;
            if (!searchableText.includes(searchTerm)) {
                return false;
            }
        }

        // Category filter
        if (this.activeFilters.category) {
            if (data.categoryId !== this.activeFilters.category.id && 
                !data.type.includes(this.activeFilters.category.name.toLowerCase())) {
                return false;
            }
        }

        // Outcome filter
        if (this.activeFilters.outcome) {
            if (data.outcomeId !== this.activeFilters.outcome.id && 
                !data.outcome.includes(this.activeFilters.outcome.name.toLowerCase())) {
                return false;
            }
        }

        // Specific metric filter
        if (this.activeFilters.metric) {
            if (data.metricId !== this.activeFilters.metric.id && 
                !data.name.includes(this.activeFilters.metric.name.toLowerCase())) {
                return false;
            }
        }

        // Neuroscience filter
        if (this.activeFilters.neuroscience) {
            if (data.metricId !== this.activeFilters.neuroscience.id && 
                !data.type.includes('neuroscience')) {
                return false;
            }
        }

        return true;
    }

    sortByRelevance() {
        this.filteredResults.sort((a, b) => {
            let scoreA = this.calculateRelevanceScore(a);
            let scoreB = this.calculateRelevanceScore(b);
            
            // Higher scores first
            return scoreB - scoreA;
        });
    }

    calculateRelevanceScore(item) {
        let score = 0;
        const { data } = item;

        // Exact matches get highest priority
        if (this.activeFilters.category && data.categoryId === this.activeFilters.category.id) {
            score += 100;
        }
        if (this.activeFilters.outcome && data.outcomeId === this.activeFilters.outcome.id) {
            score += 100;
        }
        if (this.activeFilters.metric && data.metricId === this.activeFilters.metric.id) {
            score += 200; // Specific metric gets highest priority
        }

        // Partial matches get medium priority
        if (this.activeFilters.category && data.type.includes(this.activeFilters.category.name.toLowerCase())) {
            score += 50;
        }
        if (this.activeFilters.outcome && data.outcome.includes(this.activeFilters.outcome.name.toLowerCase())) {
            score += 50;
        }

        // Search term relevance
        if (this.activeFilters.search) {
            const searchTerm = this.activeFilters.search.toLowerCase();
            if (data.name.includes(searchTerm)) score += 75;
            if (data.description.includes(searchTerm)) score += 25;
            if (data.type.includes(searchTerm)) score += 50;
            if (data.outcome.includes(searchTerm)) score += 50;
        }

        return score;
    }

    updateDisplay() {
        const container = document.querySelector('.metrics-grid');
        if (!container) return;

        // Hide all cards first
        this.metricCards.forEach(card => {
            card.style.display = 'none';
            card.classList.remove('highlighted', 'priority-high', 'priority-medium');
        });

        // Show and position filtered results
        this.filteredResults.forEach((item, index) => {
            const { element } = item;
            element.style.display = 'block';
            element.style.order = index;
            
            // Add priority classes for visual distinction
            const score = this.calculateRelevanceScore(item);
            if (score >= 150) {
                element.classList.add('priority-high');
            } else if (score >= 75) {
                element.classList.add('priority-medium');
            }
            
            // Append to container to reorder
            container.appendChild(element);
        });

        // Smooth animation
        this.animateResults();
    }

    animateResults() {
        const visibleCards = this.filteredResults.map(item => item.element);
        
        visibleCards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            
            setTimeout(() => {
                card.style.transition = 'all 0.3s ease';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 50);
        });
    }

    updateFilterSummary() {
        let summaryHTML = '';
        const activeCount = Object.values(this.activeFilters).filter(f => f && f !== '').length;
        
        if (activeCount === 0) {
            summaryHTML = '<span class="filter-summary-text">Showing all metrics</span>';
        } else {
            summaryHTML = '<span class="filter-summary-text">Active filters:</span>';
            
            Object.entries(this.activeFilters).forEach(([key, value]) => {
                if (value && value !== '') {
                    const displayValue = typeof value === 'object' ? value.name : value;
                    summaryHTML += `<span class="filter-tag filter-tag-${key}">${displayValue} <button onclick="smartFilter.removeFilter('${key}')" class="filter-tag-remove">×</button></span>`;
                }
            });
        }

        // Update or create filter summary
        let summaryContainer = document.querySelector('.filter-summary');
        if (!summaryContainer) {
            summaryContainer = document.createElement('div');
            summaryContainer.className = 'filter-summary';
            const filtersSection = document.querySelector('.filters-section');
            if (filtersSection) {
                filtersSection.appendChild(summaryContainer);
            }
        }
        
        summaryContainer.innerHTML = summaryHTML;
    }

    updateResultsCount() {
        const count = this.filteredResults.length;
        const total = this.originalOrder.length;
        
        let countContainer = document.querySelector('.results-count');
        if (!countContainer) {
            countContainer = document.createElement('div');
            countContainer.className = 'results-count';
            const container = document.querySelector('.metrics-grid')?.parentNode;
            if (container) {
                container.insertBefore(countContainer, document.querySelector('.metrics-grid'));
            }
        }
        
        countContainer.innerHTML = `
            <span class="count-text">Showing ${count} of ${total} metrics</span>
            ${count < total ? '<button onclick="smartFilter.clearAllFilters()" class="clear-filters-btn">Clear All Filters</button>' : ''}
        `;
    }

    removeFilter(filterKey) {
        this.activeFilters[filterKey] = filterKey === 'search' ? '' : null;
        
        // Update UI elements
        if (filterKey === 'search') {
            const searchInput = document.getElementById('search-input');
            if (searchInput) searchInput.value = '';
        }
        
        // Reset dropdown button text if needed
        if (this.dropdownNav) {
            switch (filterKey) {
                case 'category':
                    this.dropdownNav.updateButtonText('[onclick*="categories-dropdown"]', 'Metric Categories');
                    break;
                case 'outcome':
                    this.dropdownNav.updateButtonText('[onclick*="outcomes-dropdown"]', 'L & D Outcomes');
                    break;
                case 'metric':
                    this.dropdownNav.updateButtonText('[onclick*="metrics-dropdown"]', 'Find Metrics');
                    break;
                case 'neuroscience':
                    this.dropdownNav.updateButtonText('[onclick*="neuroscience-dropdown"]', 'Explore Categories');
                    break;
            }
        }
        
        this.applySmartFiltering();
    }

    clearAllFilters() {
        this.activeFilters = {
            search: '',
            category: null,
            outcome: null,
            metric: null,
            neuroscience: null
        };
        
        // Clear search input
        const searchInput = document.getElementById('search-input');
        if (searchInput) searchInput.value = '';
        
        // Reset all dropdown buttons
        if (this.dropdownNav) {
            this.dropdownNav.clearSelections();
        }
        
        this.applySmartFiltering();
    }

    setupFilterUI() {
        // Add quick filter buttons
        this.addQuickFilters();
        this.addFilterPresets();
    }

    addQuickFilters() {
        const quickFiltersHTML = `
            <div class="quick-filters">
                <h4>Quick Filters:</h4>
                <div class="quick-filter-buttons">
                    <button onclick="smartFilter.applyQuickFilter('popular')" class="quick-filter-btn">Most Popular</button>
                    <button onclick="smartFilter.applyQuickFilter('neuroscience')" class="quick-filter-btn">Neuroscience-Based</button>
                    <button onclick="smartFilter.applyQuickFilter('engagement')" class="quick-filter-btn">Employee Engagement</button>
                    <button onclick="smartFilter.applyQuickFilter('performance')" class="quick-filter-btn">Performance Metrics</button>
                </div>
            </div>
        `;
        
        const filtersSection = document.querySelector('.filters-section');
        if (filtersSection) {
            filtersSection.insertAdjacentHTML('beforeend', quickFiltersHTML);
        }
    }

    addFilterPresets() {
        // Add preset combinations for common use cases
        const presetsHTML = `
            <div class="filter-presets">
                <h4>Common Combinations:</h4>
                <div class="preset-buttons">
                    <button onclick="smartFilter.applyPreset('leadership')" class="preset-btn">Leadership Development</button>
                    <button onclick="smartFilter.applyPreset('training')" class="preset-btn">Training Effectiveness</button>
                    <button onclick="smartFilter.applyPreset('wellbeing')" class="preset-btn">Employee Wellbeing</button>
                </div>
            </div>
        `;
        
        const filtersSection = document.querySelector('.filters-section');
        if (filtersSection) {
            filtersSection.insertAdjacentHTML('beforeend', presetsHTML);
        }
    }

    applyQuickFilter(type) {
        this.clearAllFilters();
        
        switch (type) {
            case 'neuroscience':
                this.activeFilters.search = 'neuroscience';
                break;
            case 'engagement':
                this.activeFilters.search = 'engagement';
                break;
            case 'performance':
                this.activeFilters.search = 'performance';
                break;
            case 'popular':
                // Could be based on usage statistics
                this.activeFilters.search = 'engagement';
                break;
        }
        
        this.applySmartFiltering();
    }

    applyPreset(preset) {
        this.clearAllFilters();
        
        switch (preset) {
            case 'leadership':
                this.activeFilters.search = 'leadership development';
                break;
            case 'training':
                this.activeFilters.search = 'training effectiveness';
                break;
            case 'wellbeing':
                this.activeFilters.search = 'wellbeing wellness';
                break;
        }
        
        this.applySmartFiltering();
    }

    getFilterState() {
        return { ...this.activeFilters };
    }

    restoreFilterState(state) {
        this.activeFilters = { ...state };
        this.applySmartFiltering();
    }
}

// Initialize smart filter manager
let smartFilter;

document.addEventListener('DOMContentLoaded', function() {
    smartFilter = new SmartFilterManager();
});

// Export for global access
window.smartFilter = smartFilter;
