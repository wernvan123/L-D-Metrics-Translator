/**
 * Enhanced Filter System for L&D Metrics Translator
 * Provides intuitive filtering with presets and tag-based selection
 */

// Immediate execution test to verify script loading
console.log('Enhanced Filter System: Script loaded successfully at', new Date().toISOString());
window.filterSystemLoaded = true;

// Define functions immediately to ensure they're available
window.refreshFilters = function() {
    console.log('=== Refreshing Filter System ===');
    if (window.enhancedFilters) {
        window.enhancedFilters.loadMetrics();
        window.enhancedFilters.updateFilterDisplay();
        console.log('Filter system refreshed');
    } else {
        console.log('Enhanced filter system not yet initialized');
    }
};

window.testFilters = function() {
    console.log('=== Filter System Debug Test ===');
    console.log('window.enhancedFilters exists:', !!window.enhancedFilters);
    console.log('toggleFilter function exists:', typeof window.toggleFilter);
    console.log('applyFilters function exists:', typeof window.applyFilters);
    
    if (window.enhancedFilters) {
        console.log('All metrics count:', window.enhancedFilters.allMetrics.length);
        console.log('Active filters:', {
            categories: Array.from(window.enhancedFilters.activeFilters.categories),
            outcomes: Array.from(window.enhancedFilters.activeFilters.outcomes)
        });
        
        // Test filter buttons
        const filterButtons = document.querySelectorAll('.filter-tag');
        console.log('Filter buttons found:', filterButtons.length);
        
        if (filterButtons.length > 0) {
            const firstButton = filterButtons[0];
            console.log('First filter button:', {
                type: firstButton.dataset.type,
                id: firstButton.dataset.id,
                text: firstButton.textContent.trim(),
                onclick: firstButton.getAttribute('onclick')
            });
        }
    }
};

class EnhancedFilterSystem {
    constructor() {
        this.activeFilters = {
            categories: new Set(),
            outcomes: new Set(),
            presets: new Set()
        };
        this.allMetrics = [];
        this.filteredMetrics = [];
        this.debounceTimer = null;
        this.debounceDelay = 300; // 300ms debounce delay
        this.init();
    }

    init() {
        document.addEventListener('DOMContentLoaded', () => {
            console.log('Enhanced Filter System: DOM loaded, initializing...');
            this.setupEventListeners();
            
            // Wait for metric cards to be available before loading
            const initializeWhenReady = () => {
                const metricCards = document.querySelectorAll('.metric-card');
                console.log(`Enhanced Filter System: Found ${metricCards.length} metric cards`);
                
                if (metricCards.length > 0) {
                    this.loadMetrics();
                    this.updateFilterDisplay();
                    this.hookIntoExistingSearch();
                    console.log('Enhanced Filter System: Initialization complete');
                    
                    // Notify smart recommendations that metrics are ready
                    if (window.smartRecommendations && typeof window.smartRecommendations.refreshRecommendations === 'function') {
                        console.log('Enhanced Filter System: Notifying smart recommendations that metrics are ready');
                        window.smartRecommendations.refreshRecommendations();
                    }
                } else {
                    console.log('Enhanced Filter System: No metric cards found, retrying in 500ms...');
                    setTimeout(initializeWhenReady, 500);
                }
            };
            
            initializeWhenReady();
        });
    }

    setupEventListeners() {
        // Preset button listeners are handled by onclick attributes
        // Filter tag listeners are handled by onclick attributes
        // Action button listeners are handled by onclick attributes
        
        // Add keyboard support
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.clearAllFilters();
            }
        });
    }

    loadMetrics() {
        console.log('=== ENHANCED FILTER DEBUG: loadMetrics() called ===');
        
        // Check if we're in the right section
        const currentSection = document.querySelector('.page-section:not([style*="display: none"])');
        console.log('Current visible section:', currentSection?.id || 'unknown');
        
        // Get all metric cards from the DOM - try multiple selectors
        let metricCards = document.querySelectorAll('.metric-card');
        console.log(`Enhanced Filter System: Found ${metricCards.length} .metric-card elements`);
        
        // Debug: Check all possible containers
        const containers = [
            document.getElementById('plan-metrics-container') || document.getElementById('metrics-container'),
            document.getElementById('plan-metrics-grid') || document.getElementById('metrics-grid'),
            document.querySelector('.metrics-grid'),
            document.querySelector('.metrics-container')
        ];
        
        containers.forEach((container, index) => {
            if (container) {
                console.log(`Container ${index} (${container.id || container.className}):`, {
                    exists: true,
                    childCount: container.children.length,
                    innerHTML: container.innerHTML.substring(0, 200) + '...'
                });
                
                // Check for metric cards within this container
                const cardsInContainer = container.querySelectorAll('.metric-card');
                console.log(`  - Metric cards in container: ${cardsInContainer.length}`);
            } else {
                console.log(`Container ${index}: null`);
            }
        });
        
        // If no metric cards found, try alternative selectors
        if (metricCards.length === 0) {
            console.log('No .metric-card found, trying alternative selectors...');
            
            // Try different selectors
            const alternativeSelectors = [
                '[data-id]',
                '.metric',
                '[data-metric-id]',
                '.card[data-id]',
                'div[data-id]'
            ];
            
            alternativeSelectors.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                console.log(`Selector "${selector}": ${elements.length} elements`);
                if (elements.length > 0) {
                    console.log(`First element:`, {
                        tagName: elements[0].tagName,
                        className: elements[0].className,
                        id: elements[0].id,
                        dataAttributes: Object.keys(elements[0].dataset)
                    });
                }
            });
            
            metricCards = document.querySelectorAll('[data-id]');
            console.log(`Using fallback selector: Found ${metricCards.length} elements with data-id`);
            
            // Log all elements with data-id to debug
            metricCards.forEach((card, index) => {
                console.log(`Element ${index}:`, {
                    tagName: card.tagName,
                    className: card.className,
                    dataId: card.dataset.id,
                    dataType: card.dataset.type,
                    dataOutcome: card.dataset.outcome,
                    hasMetricCardClass: card.classList.contains('metric-card')
                });
            });
        }
        
        // Map metrics with comprehensive error checking
        this.allMetrics = Array.from(metricCards).map((card, index) => {
            const metric = {
                element: card,
                id: card.dataset.id,
                type: card.dataset.type,
                outcome: card.dataset.outcome,
                name: card.dataset.name || card.querySelector('.metric-name')?.textContent?.trim() || 'Unknown'
            };
            
            console.log(`Metric ${index}:`, metric);
            return metric;
        });
        
        this.filteredMetrics = [...this.allMetrics];
        
        console.log(`Enhanced Filter System: Loaded ${this.allMetrics.length} metrics`);
        console.log('All metrics array:', this.allMetrics);
        
        if (this.allMetrics.length > 0) {
            console.log('Sample metric data:', this.allMetrics[0]);
        } else {
            console.log('=== NO METRICS LOADED - DETAILED DEBUG ===');
            
            // Check document readiness
            console.log('Document ready state:', document.readyState);
            console.log('DOM content loaded:', document.readyState === 'complete');
            
            // Check page structure
            const pageStructure = {
                body: !!document.body,
                exploreSection: !!document.getElementById('explore'),
                metricsContainer: !!document.getElementById('metrics-container'),
            };
            console.log('Page structure:', pageStructure);
            
            // Check if metrics are being loaded dynamically
            const metricsContainer = document.getElementById('plan-metrics-container') || document.getElementById('metrics-container');
            if (metricsContainer) {
                console.log('Metrics container HTML:', metricsContainer.innerHTML);
                
                // Set up observer to watch for dynamic content
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                            console.log('DOM mutation detected - new nodes added:', mutation.addedNodes.length);
                            const newMetricCards = document.querySelectorAll('.metric-card');
                            if (newMetricCards.length > 0) {
                                console.log('Metric cards now available after mutation:', newMetricCards.length);
                                observer.disconnect();
                                this.loadMetrics(); // Retry loading
                            }
                        }
                    });
                });
                
                observer.observe(metricsContainer, { childList: true, subtree: true });
                console.log('Set up mutation observer for dynamic content loading');
            }
        }
        
        console.log('=== END ENHANCED FILTER DEBUG ===');
    }

    applyPreset(presetType) {
        // Clear existing selections
        this.clearAllFilters(false);
        
        // Remove active class from all preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Add active class to selected preset
        const activeBtn = document.querySelector(`[data-preset="${presetType}"]`);
        if (activeBtn) {
            activeBtn.classList.add('active');
        }
        
        // Apply preset filters based on type
        switch (presetType) {
            case 'all':
                // Show all metrics
                break;
            case 'behavioral':
                this.selectFiltersByName('category', ['Behavioral Metric']);
                break;
            case 'operational':
                this.selectFiltersByName('category', ['Operational KPI']);
                break;
            case 'neuroscience':
                this.selectFiltersByName('category', ['Neuroscience-Based Metric']);
                break;
        }
        
        this.activeFilters.presets.clear();
        this.activeFilters.presets.add(presetType);
        
        this.debouncedApplyFilters();
    }

    selectFiltersByName(type, names) {
        const filterContainer = type === 'category' ? 
            document.getElementById('category-filters') : 
            document.getElementById('outcome-filters');
        
        if (!filterContainer) return;
        
        const filterTags = filterContainer.querySelectorAll('.filter-tag');
        filterTags.forEach(tag => {
            const tagText = tag.textContent.trim();
            if (names.some(name => tagText === name || tagText.includes(name))) {
                tag.classList.add('active');
                this.activeFilters[type === 'category' ? 'categories' : 'outcomes'].add(tag.dataset.id);
            }
        });
    }

    toggleFilter(type, id, name) {
        console.log(`Enhanced Filter System: toggleFilter called with type="${type}", id="${id}", name="${name}"`);
        
        const filterSet = type === 'category' ? this.activeFilters.categories : this.activeFilters.outcomes;
        const filterTag = document.querySelector(`[data-type="${type}"][data-id="${id}"]`);
        
        console.log(`Filter tag found:`, filterTag);
        console.log(`Current filter set size: ${filterSet.size}`);
        
        if (filterSet.has(id)) {
            filterSet.delete(id);
            filterTag?.classList.remove('active');
            console.log(`Removed filter ${id}, new size: ${filterSet.size}`);
        } else {
            filterSet.add(id);
            filterTag?.classList.add('active');
            console.log(`Added filter ${id}, new size: ${filterSet.size}`);
        }
        
        // Clear preset selection when manually selecting filters
        this.clearPresetSelection();
        
        console.log('Applying real-time filters...');
        this.debouncedApplyFilters();
    }

    clearPresetSelection() {
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        this.activeFilters.presets.clear();
    }

    applyFilters() {
        console.log('=== APPLY FILTERS DEBUG ===');
        console.log('Enhanced Filter System: applyFilters() called');
        console.log('Active categories:', Array.from(this.activeFilters.categories));
        console.log('Active outcomes:', Array.from(this.activeFilters.outcomes));
        console.log('Total metrics available:', this.allMetrics.length);
        
        // Debug: Log first few metrics to see their structure
        if (this.allMetrics.length > 0) {
            console.log('First 3 metrics structure:');
            this.allMetrics.slice(0, 3).forEach((metric, index) => {
                console.log(`Metric ${index}:`, {
                    id: metric.id,
                    type: metric.type,
                    outcome: metric.outcome,
                    name: metric.name,
                    element: metric.element?.tagName
                });
            });
        } else {
            console.log('ERROR: No metrics in allMetrics array!');
            console.log('Attempting to reload metrics...');
            this.loadMetrics();
            return;
        }
        
        const hasActiveFilters = this.activeFilters.categories.size > 0 || 
                                this.activeFilters.outcomes.size > 0;
        
        console.log('Has active filters:', hasActiveFilters);
        
        // Add loading state for visual feedback
        this.setFilteringState(true);
        
        // Use requestAnimationFrame for smooth updates
        requestAnimationFrame(() => {
            if (!hasActiveFilters) {
                // Show all metrics
                this.filteredMetrics = [...this.allMetrics];
                this.allMetrics.forEach(metric => {
                    if (metric.element) {
                        metric.element.style.display = 'block';
                        metric.element.style.opacity = '1';
                    }
                });
                console.log('Showing all metrics:', this.filteredMetrics.length);
            } else {
                // Filter metrics based on active filters
                console.log('Filtering metrics...');
                this.filteredMetrics = this.allMetrics.filter(metric => {
                    const categoryMatch = this.activeFilters.categories.size === 0 || this.activeFilters.categories.has(metric.type);
                    const outcomeMatch = this.activeFilters.outcomes.size === 0 || this.activeFilters.outcomes.has(metric.outcome);
                    
                    console.log(`Metric ${metric.id}: type=${metric.type}, outcome=${metric.outcome}, categoryMatch=${categoryMatch}, outcomeMatch=${outcomeMatch}`);
                    
                    return categoryMatch && outcomeMatch;
                });
                
                console.log(`Filtered to ${this.filteredMetrics.length} metrics from ${this.allMetrics.length} total`);
                console.log('Filtered metrics:', this.filteredMetrics.map(m => ({ id: m.id, name: m.name })));
                
                // Update DOM visibility with smooth transitions
                this.allMetrics.forEach(metric => {
                    const isVisible = this.filteredMetrics.includes(metric);
                    if (isVisible) {
                        metric.element.style.display = 'block';
                        metric.element.style.opacity = '1';
                    } else {
                        metric.element.style.opacity = '0.3';
                        setTimeout(() => {
                            if (metric.element.style.opacity === '0.3') {
                                metric.element.style.display = 'none';
                            }
                        }, 200);
                    }
                });
            }
            
            this.updateResultsCount();
            this.animateFilteredResults();
            this.setFilteringState(false);
        });
    }

    updateResultsCount() {
        const totalCount = this.allMetrics.length;
        const filteredCount = this.filteredMetrics.length;
        
        // Add relevance indicators to filtered metrics
        this.addRelevanceIndicators();
        
        // Update search info if it exists
        const searchInfo = document.getElementById('search-info');
        if (searchInfo && (this.activeFilters.categories.size > 0 || this.activeFilters.outcomes.size > 0)) {
            searchInfo.style.display = 'block';
            searchInfo.innerHTML = `
                <div class="search-results-summary">
                    <span class="results-count">Showing ${filteredCount} of ${totalCount} metrics</span>
                    ${filteredCount !== totalCount ? '<span class="filter-indicator">• Filtered</span>' : ''}
                </div>
            `;
        } else if (searchInfo) {
            searchInfo.style.display = 'none';
        }
    }

    animateFilteredResults() {
        // Add subtle staggered animation to visible metrics for better UX
        const visibleMetrics = this.filteredMetrics.slice(0, 12); // Limit animation to first 12 for performance
        
        visibleMetrics.forEach((metric, index) => {
            setTimeout(() => {
                if (metric.element.style.display !== 'none') {
                    metric.element.style.transition = 'all 0.2s ease';
                    metric.element.style.transform = 'scale(0.98)';
                    
                    setTimeout(() => {
                        metric.element.style.transform = 'scale(1)';
                    }, 100);
                }
            }, index * 30); // Reduced delay for faster animation
        });
    }
    
    // Add visual feedback during filtering
    setFilteringState(isFiltering) {
        const metricsContainer = document.getElementById('plan-metrics-container') || document.getElementById('metrics-container');
        if (metricsContainer) {
            if (isFiltering) {
                metricsContainer.style.opacity = '0.8';
                metricsContainer.style.pointerEvents = 'none';
            } else {
                metricsContainer.style.opacity = '1';
                metricsContainer.style.pointerEvents = 'auto';
            }
        }
    }
    
    addRelevanceIndicators() {
        // Add traffic light indicators for relevance
        this.allMetrics.forEach(metric => {
            const isFiltered = this.filteredMetrics.includes(metric);
            let relevanceClass = 'relevance-low';
            let relevanceIcon = '🔴';
            
            if (isFiltered) {
                // Calculate relevance based on filter matches
                const categoryMatch = this.activeFilters.categories.size === 0 || 
                                    this.activeFilters.categories.has(metric.categoryId);
                const outcomeMatch = this.activeFilters.outcomes.size === 0 || 
                                   this.activeFilters.outcomes.has(metric.outcomeId);
                
                if (categoryMatch && outcomeMatch) {
                    relevanceClass = 'relevance-high';
                    relevanceIcon = '🟢';
                } else if (categoryMatch || outcomeMatch) {
                    relevanceClass = 'relevance-medium';
                    relevanceIcon = '🟡';
                }
            }
            
            // Add or update relevance indicator
            let indicator = metric.element.querySelector('.relevance-indicator');
            if (!indicator) {
                indicator = document.createElement('div');
                indicator.className = 'relevance-indicator';
                const header = metric.element.querySelector('.metric-header');
                if (header) {
                    header.appendChild(indicator);
                }
            }
            
            indicator.className = `relevance-indicator ${relevanceClass}`;
            indicator.textContent = relevanceIcon;
            indicator.title = `Relevance: ${relevanceClass.replace('relevance-', '')}`;
            
            // Show/hide indicator based on filter state
            const hasActiveFilters = this.activeFilters.categories.size > 0 || this.activeFilters.outcomes.size > 0;
            indicator.style.display = hasActiveFilters ? 'block' : 'none';
        });
    }

    clearAllFilters() {
        // Clear all active filters
        this.activeFilters.categories.clear();
        this.activeFilters.outcomes.clear();
        this.activeFilters.presets.clear();
        
        // Remove active classes from all filter elements
        document.querySelectorAll('.filter-tag.active').forEach(tag => {
            tag.classList.remove('active');
        });
        
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Set "All Metrics" preset as active
        const allBtn = document.querySelector('[data-preset="all"]');
        if (allBtn) {
            allBtn.classList.add('active');
        }
        
        this.activeFilters.presets.add('all');
        
        // Apply filters (will show all metrics) - immediate for clear action
        this.applyFilters();
        this.updateFilterDisplay();
    }

    updateFilterDisplay() {
        const activeFiltersContainer = document.getElementById('active-filters');
        const activeFiltersList = document.getElementById('active-filters-list');
        
        if (!activeFiltersContainer || !activeFiltersList) return;
        
        const hasActiveFilters = this.activeFilters.categories.size > 0 || 
                                this.activeFilters.outcomes.size > 0;
        
        if (hasActiveFilters) {
            activeFiltersContainer.style.display = 'block';
            activeFiltersList.innerHTML = '';
            
            // Add category filters
            this.activeFilters.categories.forEach(categoryId => {
                const filterTag = document.querySelector(`[data-type="category"][data-id="${categoryId}"]`);
                if (filterTag) {
                    const filterName = filterTag.textContent.trim();
                    this.addActiveFilterTag(activeFiltersList, 'category', categoryId, filterName);
                }
            });
            
            // Add outcome filters
            this.activeFilters.outcomes.forEach(outcomeId => {
                const filterTag = document.querySelector(`[data-type="outcome"][data-id="${outcomeId}"]`);
                if (filterTag) {
                    const filterName = filterTag.textContent.trim();
                    this.addActiveFilterTag(activeFiltersList, 'outcome', outcomeId, filterName);
                }
            });
        } else {
            activeFiltersContainer.style.display = 'none';
        }
    }

    addActiveFilterTag(container, type, id, name) {
        const tag = document.createElement('div');
        tag.className = 'active-filter-tag';
        tag.innerHTML = `
            <span>${name}</span>
            <button class="remove-btn" onclick="enhancedFilters.removeFilter('${type}', '${id}')" title="Remove filter">
                ×
            </button>
        `;
        container.appendChild(tag);
    }

    removeFilter(type, id) {
        const filterSet = type === 'category' ? this.activeFilters.categories : this.activeFilters.outcomes;
        filterSet.delete(id);
        
        // Remove active class from filter tag
        const filterTag = document.querySelector(`[data-type="${type}"][data-id="${id}"]`);
        if (filterTag) {
            filterTag.classList.remove('active');
        }
        
        this.clearPresetSelection();
        this.debouncedApplyFilters();
    }

    // Integration with existing search functionality
    integrateWithSearch(searchTerm) {
        if (!searchTerm) {
            this.applyFilters();
            return this.filteredMetrics;
        }
        
        // Apply both search and filter criteria
        const searchResults = this.filteredMetrics.filter(metric => {
            const searchableText = `${metric.name} ${metric.description} ${metric.categoryName} ${metric.outcomeName}`.toLowerCase();
            return searchableText.includes(searchTerm.toLowerCase());
        });
        
        // Update DOM visibility
        this.allMetrics.forEach(metric => {
            const isVisible = searchResults.includes(metric);
            metric.element.style.display = isVisible ? 'block' : 'none';
        });
        
        // Update results count
        this.updateSearchResultsCount(searchResults.length, searchTerm);
        
        return searchResults;
    }

    updateSearchResultsCount(count, searchTerm) {
        const searchInfo = document.getElementById('search-info');
        if (searchInfo) {
            searchInfo.style.display = 'block';
            const hasFilters = this.activeFilters.categories.size > 0 || this.activeFilters.outcomes.size > 0;
            const filterText = hasFilters ? ' (filtered)' : '';
            
            searchInfo.innerHTML = `
                <div class="search-results-summary">
                    <span class="results-count">Found ${count} metrics for "${searchTerm}"${filterText}</span>
                    ${count === 0 ? '<span class="no-results-hint">Try adjusting your search terms or filters</span>' : ''}
                </div>
            `;
        }
    }

    // Debounced filter application for performance with immediate visual feedback
    debouncedApplyFilters() {
        // Provide immediate visual feedback
        this.setFilteringState(true);
        
        // Clear existing timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        
        // Set new timer with optimized delay
        this.debounceTimer = setTimeout(() => {
            this.applyFilters();
            this.updateFilterDisplay();
        }, this.debounceDelay);
    }
    
    // Hook into existing search system with debouncing
    hookIntoExistingSearch() {
        const searchInput = document.getElementById('plan-search-input') || document.getElementById('search-input');
        if (searchInput) {
            let searchDebounceTimer = null;
            
            // Override with enhanced functionality and debouncing
            searchInput.addEventListener('input', (e) => {
                const searchTerm = e.target.value.trim();
                
                // Clear existing search timer
                if (searchDebounceTimer) {
                    clearTimeout(searchDebounceTimer);
                }
                
                // Set new search timer with shorter delay for search
                searchDebounceTimer = setTimeout(() => {
                    this.integrateWithSearch(searchTerm);
                }, 150); // Shorter delay for search responsiveness
            });
        }
    }
}

// Global debug function for browser console testing
window.debugFilters = function() {
    console.log('=== FILTER SYSTEM DEBUG REPORT ===');
    console.log('Enhanced filters initialized:', !!window.enhancedFilters);
    
    if (window.enhancedFilters) {
        const filters = window.enhancedFilters;
        console.log('All metrics count:', filters.allMetrics.length);
        console.log('Filtered metrics count:', filters.filteredMetrics.length);
        console.log('Active filters:', {
            categories: Array.from(filters.activeFilters.categories),
            outcomes: Array.from(filters.activeFilters.outcomes)
        });
        
        // Check DOM elements
        const metricCards = document.querySelectorAll('.metric-card');
        const dataIdElements = document.querySelectorAll('[data-id]');
        console.log('DOM metric cards found:', metricCards.length);
        console.log('DOM data-id elements found:', dataIdElements.length);
        
        // Check containers
        const containers = {
            metricsContainer: document.getElementById('metrics-container'),
            metricsGrid: document.getElementById('metrics-grid'),
            exploreSection: document.getElementById('explore')
        };
        
        Object.entries(containers).forEach(([name, element]) => {
            console.log(`${name}:`, {
                exists: !!element,
                visible: element ? element.style.display !== 'none' : false,
                childCount: element ? element.children.length : 0
            });
        });
        
        // Force reload metrics
        console.log('Forcing metric reload...');
        filters.loadMetrics();
    }
    
    console.log('=== END DEBUG REPORT ===');
};

// Global functions for HTML onclick handlers
window.applyPreset = function(presetType) {
    console.log(`Global applyPreset called with: ${presetType}`);
    if (window.enhancedFilters) {
        window.enhancedFilters.applyPreset(presetType);
    } else {
        console.log('Enhanced filter system not initialized');
    }
};

window.toggleFilter = function(type, id, name) {
    console.log(`Global toggleFilter called with: type=${type}, id=${id}, name=${name}`);
    if (window.enhancedFilters) {
        window.enhancedFilters.toggleFilter(type, id, name);
    } else {
        console.error('Enhanced filter system not initialized');
    }
};

window.applyFilters = function() {
    console.log('Global applyFilters called');
    if (window.enhancedFilters) {
        window.enhancedFilters.applyFilters();
    } else {
        console.error('Enhanced filter system not initialized');
    }
};

window.clearAllFilters = function() {
    console.log('Global clearAllFilters called');
    if (window.enhancedFilters) {
        window.enhancedFilters.clearAllFilters();
    } else {
        console.error('Enhanced filter system not initialized');
    }
};


// Initialize enhanced filter system
document.addEventListener('DOMContentLoaded', function() {
    window.enhancedFilters = new EnhancedFilterSystem();
    console.log('Enhanced Filter System: Initialized with relevance indicators');
    console.log('Run testFilters() in console to debug filter issues');
});
