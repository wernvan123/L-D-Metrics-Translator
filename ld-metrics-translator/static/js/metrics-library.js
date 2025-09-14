class MetricsLibrary {
    constructor() {
        this.allMetrics = [];
        this.filteredMetrics = [];
        this.frameworks = [];
        this.init();
    }

    async init() {
        await this.loadData();
        this.setupEventListeners();
        this.renderMetrics();
    }

    async initializeLibraryTab() {
        // Called when library tab becomes active
        if (!this.allMetrics.length) {
            await this.loadData();
        }
        this.renderMetrics();
    }

    async loadData() {
        try {
            // Load metrics
            const metricsResponse = await fetch('/api/metrics');
            if (metricsResponse.ok) {
                const metricsData = await metricsResponse.json();
                this.allMetrics = metricsData.metrics || [];
            }

            // Load frameworks for filter dropdown
            const frameworksResponse = await fetch('/api/frameworks?include_competencies=true');
            if (frameworksResponse.ok) {
                const frameworksData = await frameworksResponse.json();
                this.frameworks = frameworksData.frameworks || [];
                this.populateFrameworkFilter();
            }

            this.filteredMetrics = [...this.allMetrics];
        } catch (error) {
            console.error('Error loading library data:', error);
            this.showError('Failed to load metrics library data');
        }
    }

    populateFrameworkFilter() {
        const frameworkFilter = document.getElementById('framework-filter');
        if (frameworkFilter && this.frameworks.length > 0) {
            // Clear existing options except "All Frameworks"
            frameworkFilter.innerHTML = '<option value="">All Frameworks</option>';
            
            this.frameworks.forEach(framework => {
                const option = document.createElement('option');
                option.value = framework.id;
                option.textContent = framework.name;
                frameworkFilter.appendChild(option);
            });
        }
    }

    setupEventListeners() {
        const searchInput = document.getElementById('library-search');
        const categoryFilter = document.getElementById('category-filter');
        const frameworkFilter = document.getElementById('framework-filter');

        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.handleSearch(e.target.value);
            });
        }

        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => {
                this.handleCategoryFilter(e.target.value);
            });
        }

        if (frameworkFilter) {
            frameworkFilter.addEventListener('change', (e) => {
                this.handleFrameworkFilter(e.target.value);
            });
        }
    }

    handleSearch(query) {
        this.filterMetrics({
            search: query.toLowerCase(),
            category: document.getElementById('category-filter')?.value || '',
            framework: document.getElementById('framework-filter')?.value || ''
        });
    }

    handleCategoryFilter(category) {
        this.filterMetrics({
            search: document.getElementById('library-search')?.value.toLowerCase() || '',
            category: category,
            framework: document.getElementById('framework-filter')?.value || ''
        });
    }

    handleFrameworkFilter(frameworkId) {
        this.filterMetrics({
            search: document.getElementById('library-search')?.value.toLowerCase() || '',
            category: document.getElementById('category-filter')?.value || '',
            framework: frameworkId
        });
    }

    filterMetrics(filters) {
        this.filteredMetrics = this.allMetrics.filter(metric => {
            // Search filter
            if (filters.search) {
                const searchMatch = 
                    metric.name.toLowerCase().includes(filters.search) ||
                    (metric.description && metric.description.toLowerCase().includes(filters.search)) ||
                    (metric.outcome && metric.outcome.name.toLowerCase().includes(filters.search)) ||
                    (metric.metric_type && metric.metric_type.name.toLowerCase().includes(filters.search));
                
                if (!searchMatch) return false;
            }

            // Category filter
            if (filters.category) {
                const categoryMatch = metric.metric_type && metric.metric_type.name === filters.category;
                if (!categoryMatch) return false;
            }

            // Framework filter (placeholder - would need actual framework-metric relationships)
            if (filters.framework) {
                // For now, show all metrics when framework is selected
                // In real implementation, filter by framework relationships
            }

            return true;
        });

        this.renderMetrics();
        this.updateResultsCount();
    }

    renderMetrics() {
        const grid = document.getElementById('library-metrics-grid');
        if (!grid) return;

        if (this.filteredMetrics.length === 0) {
            grid.innerHTML = `
                <div class="library-empty-state">
                    <div class="empty-state-icon">🔍</div>
                    <h4>No metrics found</h4>
                    <p>Try adjusting your search or filter criteria</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = this.filteredMetrics.map(metric => this.createMetricCard(metric)).join('');
    }

    createMetricCard(metric) {
        const outcomeText = metric.outcome?.name || metric.outcome_name || 'General';
        const typeText = metric.metric_type?.name || metric.type_name || 'Standard';
        
        return `
            <div class="library-metric-card" data-metric-id="${metric.id}">
                <div class="library-metric-header">
                    <h4>${metric.name}</h4>
                    <div class="library-metric-meta">
                        <span class="metric-outcome">${outcomeText}</span>
                        <span class="metric-type">${typeText}</span>
                    </div>
                </div>
                <div class="library-metric-description">
                    ${metric.description || 'No description available'}
                </div>
                <div class="library-metric-actions">
                    <button class="btn btn-sm btn-outline library-view-details" 
                            onclick="metricsLibrary.viewDetails('${metric.id}')">
                        View Details
                    </button>
                    <button class="btn btn-sm btn-primary library-add-to-plan" 
                            onclick="metricsLibrary.addToPlan('${metric.id}')">
                        Add to Plan
                    </button>
                </div>
            </div>
        `;
    }

    updateResultsCount() {
        const countElement = document.getElementById('library-results-count');
        if (countElement) {
            const total = this.allMetrics.length;
            const filtered = this.filteredMetrics.length;
            countElement.textContent = `Showing ${filtered} of ${total} metrics`;
        }
    }

    viewDetails(metricId) {
        // Use existing viewMetricDetails function if available
        if (window.viewMetricDetails) {
            window.viewMetricDetails(metricId);
        } else {
            console.log('View details for metric:', metricId);
        }
    }

    addToPlan(metricId) {
        // Switch to Plan & Measure tab and add metric
        const planTab = document.querySelector('[data-tab="plan"]');
        if (planTab) {
            planTab.click();
            
            // Wait for tab to switch, then add metric
            setTimeout(() => {
                if (window.addToReport) {
                    window.addToReport(metricId);
                }
                
                if (window.showNotification) {
                    const metric = this.allMetrics.find(m => m.id == metricId);
                    const metricName = metric ? metric.name : 'Metric';
                    window.showNotification(`Added "${metricName}" to your development plan`, 'success');
                }
            }, 300);
        }
    }

    showError(message) {
        const grid = document.getElementById('library-metrics-grid');
        if (grid) {
            grid.innerHTML = `
                <div class="library-error-state">
                    <div class="error-icon">⚠️</div>
                    <h4>Error</h4>
                    <p>${message}</p>
                </div>
            `;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Create instance but don't fully initialize until tab is active
    window.metricsLibrary = new MetricsLibrary();
});

// Listen for tab changes to initialize library when needed
document.addEventListener('click', (e) => {
    if (e.target.matches('[data-tab="library"]') || e.target.closest('[data-tab="library"]')) {
        setTimeout(() => {
            if (window.metricsLibrary) {
                window.metricsLibrary.initializeLibraryTab();
            }
        }, 200);
    }
});
