// L&D Metrics Translator - Advanced Search Functionality

class SearchManager {
    constructor() {
        this.searchInput = null;
        this.searchResults = null;
        this.searchSuggestions = null;
        this.searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');
        this.debounceTimer = null;
        this.currentSearchTerm = '';
        this.searchCache = new Map();
        this.isSearching = false;
        this.maxHistoryItems = 10;
        this.minSearchLength = 2;
        this.debounceDelay = 300;
        
        this.init();
    }

    init() {
        this.searchNames = document.getElementById('modal-search-names');
        this.searchDescriptions = document.getElementById('modal-search-descriptions');
        this.searchExamples = document.getElementById('modal-search-examples');
        this.exactMatch = document.getElementById('modal-exact-match');
        this.selectAllOutcomes = document.getElementById('modal-select-all-outcomes');
        this.selectAllTypes = document.getElementById('modal-select-all-types');
        this.searchInput = document.getElementById('plan-search-input') || document.getElementById('search-input');
        this.searchResults = document.getElementById('search-results');
        this.searchSuggestions = document.getElementById('search-suggestions');
        
        if (!this.searchInput) {
            console.warn('Search input not found');
            return;
        }

        this.setupEventListeners();
        this.createSearchUI();
        this.loadSearchHistory();
    }

    setupEventListeners() {
        // Real-time search with debouncing
        this.searchInput.addEventListener('input', (e) => {
            this.handleSearchInput(e.target.value);
        });

        // Handle search suggestions
        this.searchInput.addEventListener('focus', () => {
            this.showSearchSuggestions();
        });

        // Handle keyboard navigation
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeyboardNavigation(e);
        });

        // Search button functionality
        const searchButton = document.getElementById('search-button');
        if (searchButton) {
            searchButton.addEventListener('click', () => {
                this.performSearch(this.searchInput.value);
            });
        }

        // Clear search functionality
        const clearBtn = document.getElementById('clear-search') || document.getElementById('plan-clear-search');
        if (clearBtn) clearBtn.addEventListener('click', () => this.clearSearch());

        // Close suggestions when clicking outside
        document.addEventListener('click', (e) => {
            const withinContainer = e.target.closest('.search-box') || e.target.closest('.search-container');
            if (!withinContainer) {
                this.hideSearchSuggestions();
            }
        });

        // Advanced search toggle
        const advancedToggle = document.getElementById('advanced-search-toggle');
        if (advancedToggle) {
            advancedToggle.addEventListener('click', () => {
                this.toggleAdvancedSearch();
            });
        }
    }

    createSearchUI() {
        // Create search suggestions container
        if (!this.searchSuggestions) {
            const suggestionsContainer = document.createElement('div');
            suggestionsContainer.id = 'search-suggestions';
            suggestionsContainer.className = 'search-suggestions';
            suggestionsContainer.style.display = 'none';
            
            const searchContainer = this.searchInput.closest('.search-box') || this.searchInput.closest('.search-container');
            if (searchContainer) {
                searchContainer.appendChild(suggestionsContainer);
                this.searchSuggestions = suggestionsContainer;
            }
        }

        // Create search results info container
        if (!document.getElementById('search-info')) {
            const searchInfo = document.createElement('div');
            searchInfo.id = 'search-info';
            searchInfo.className = 'search-info';
            
            const metricsContainer = document.getElementById('plan-metrics-container') || document.getElementById('metrics-container');
            if (metricsContainer) {
                metricsContainer.insertBefore(searchInfo, metricsContainer.firstChild);
            }
        }

        // Create clear search button if it doesn't exist (support plan-specific ID)
        if (!document.getElementById('clear-search') && !document.getElementById('plan-clear-search')) {
            const clearButton = document.createElement('button');
            clearButton.id = 'clear-search';
            clearButton.className = 'clear-search-btn';
            clearButton.innerHTML = '×';
            clearButton.title = 'Clear search';
            clearButton.style.display = 'none';
            
            const searchContainer = this.searchInput.closest('.search-box') || this.searchInput.closest('.search-container');
            if (searchContainer) {
                searchContainer.appendChild(clearButton);
            }
        }
    }

    handleSearchInput(value) {
        const trimmedValue = value.trim();
        
        // Show/hide clear button with smooth animation
        const clearButton = document.getElementById('clear-search') || document.getElementById('plan-clear-search');
        if (clearButton) clearButton.style.display = trimmedValue ? 'block' : 'none';
        
        // Update current search term
        this.currentSearchTerm = trimmedValue;
        
        // Clear previous debounce timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // Immediate filtering for empty search (show all results)
        if (this.currentSearchTerm === '') {
            this.clearSearchResults();
            this.showAllMetrics();
            return;
        }
        
        // Ensure proper binding of this
        this.debounceTimer = setTimeout(() => {
            if (typeof this.performSearch === 'function') {
                this.performSearch(this.currentSearchTerm);
            }
        }, this.debounceDelay);
    }

    async performSearch(searchTerm) {
        if (!searchTerm || searchTerm.length < this.minSearchLength) {
            this.clearSearchResults();
            this.showAllMetrics();
            return;
        }

        this.isSearching = true;
        this.showSearchLoading();
        
        // Check cache first
        if (this.searchCache.has(searchTerm)) {
            this.displaySearchResults(this.searchCache.get(searchTerm), searchTerm);
            this.isSearching = false;
            this.hideSearchLoading();
            return;
        }

        // Perform search across different data sources
        const results = this.searchMetrics(searchTerm);
        
        // Cache results
        this.searchCache.set(searchTerm, results);
        
        // Display results
        this.displaySearchResults(results, searchTerm);
        
        // Add to search history
        this.addToSearchHistory(searchTerm);
        
        this.isSearching = false;
        this.hideSearchLoading();
    }

    displaySearchResults(results, searchTerm) {
        // Update search info
        this.updateSearchInfo(results, searchTerm);
        
        // Filter current DOM cards by matched IDs (non-destructive to AppState)
        const matched = new Set(results.matchedIds || []);
        const cards = document.querySelectorAll('.metric-card');
        cards.forEach(card => {
            const id = card.getAttribute('data-id') || card.dataset.id;
            const isMatch = matched.size === 0 ? true : matched.has(String(id));
            card.style.display = isMatch ? 'block' : 'none';
            card.classList.toggle('search-hidden', !isMatch);
        });

        // Ensure the Plan metrics container is visible during searches
        this.toggleMetricsContainerVisibility(true);

        // Show/hide clear search button
        const clearButton = document.getElementById('clear-search') || document.getElementById('plan-clear-search');
        if (clearButton) clearButton.style.display = searchTerm ? 'block' : 'none';
        
        // Highlight search terms in results
        this.highlightSearchTerms(searchTerm);
    }

    updateSearchInfo(results, searchTerm) {
        const searchInfo = document.getElementById('search-info');
        if (!searchInfo) return;

        const count = results.metrics ? results.metrics.length : 0;
        const totalCount = results.total_count || count;
        
        // Clear previous content
        searchInfo.innerHTML = '';
        
        // Only show search info if there's an active search
        if (!searchTerm) {
            searchInfo.style.display = 'none';
            return;
        }
        
        searchInfo.style.display = 'block';
        
        const infoDiv = document.createElement('div');
        infoDiv.className = 'search-results-info';
        
        // Add count
        const countSpan = document.createElement('span');
        countSpan.className = 'search-count';
        countSpan.textContent = `${count} metric${count !== 1 ? 's' : ''} found`;
        infoDiv.appendChild(countSpan);
        
        // Add search term
        if (searchTerm) {
            const termSpan = document.createElement('span');
            termSpan.className = 'search-term';
            termSpan.innerHTML = ` for "<strong>${this.escapeHtml(searchTerm)}</strong>"`;
            infoDiv.appendChild(termSpan);
            
            // Add clear search button
            const clearButton = document.createElement('button');
            clearButton.className = 'clear-search-text';
            clearButton.innerHTML = 'Clear search';
            clearButton.onclick = () => this.clearSearch();
            infoDiv.appendChild(clearButton);
            
            // Show no results message if applicable
            if (count === 0) {
                const noResultsDiv = document.createElement('div');
                noResultsDiv.className = 'no-results';
                noResultsDiv.innerHTML = `
                    <p>No metrics found matching your search.</p>
                    <p>Try different keywords or check your spelling.</p>
                `;
                searchInfo.appendChild(noResultsDiv);
            }
        }
        
        searchInfo.appendChild(infoDiv);
    }

    highlightSearchTerms(searchTerm) {
        if (!searchTerm || searchTerm.length < this.minSearchLength) return;

        const terms = searchTerm.toLowerCase().split(' ').filter(term => term.length > 1);
        const metricCards = document.querySelectorAll('.metric-card');

        metricCards.forEach(card => {
            const textElements = card.querySelectorAll('.metric-title, .metric-name, .metric-description, .metric-example');
            
            textElements.forEach(element => {
                let html = element.innerHTML;
                
                // Remove existing highlights
                html = html.replace(/<mark class="search-highlight">(.*?)<\/mark>/gi, '$1');
                
                // Add new highlights
                terms.forEach(term => {
                    const regex = new RegExp(`(${this.escapeRegex(term)})`, 'gi');
                    html = html.replace(regex, '<mark class="search-highlight">$1</mark>');
                });
                
                element.innerHTML = html;
            });
        });
    }

    // Case-insensitive search across metric cards and AppState data
    searchMetrics(searchTerm) {
        const term = (searchTerm || '').toLowerCase();
        const cards = Array.from(document.querySelectorAll('.metric-card'));
        const matchedIds = [];

        cards.forEach(card => {
            const id = (card.getAttribute('data-id') || card.dataset.id || '').toString();
            const name = (card.dataset.name || '').toLowerCase();
            const outcome = (card.dataset.outcomeName || '').toLowerCase();
            const type = (card.dataset.typeName || '').toLowerCase();
            const desc = (card.querySelector('.metric-description')?.innerText || '').toLowerCase();
            const example = (card.querySelector('.metric-example')?.innerText || '').toLowerCase();

            const haystack = [name, outcome, type, desc, example].join(' ');
            if (haystack.includes(term)) {
                matchedIds.push(id);
            }
        });

        // Map to a stable baseline of metrics if available
        let matchedMetrics = [];
        if (window.AppState) {
            const baseline = Array.isArray(window.AppState.originalMetrics)
                ? window.AppState.originalMetrics
                : (Array.isArray(window.AppState.metrics) ? window.AppState.metrics : []);
            if (Array.isArray(baseline) && baseline.length > 0) {
                matchedMetrics = baseline.filter(m => matchedIds.includes(String(m.id)));
            }
        }

        return {
            metrics: matchedMetrics,
            matchedIds,
            total_count: cards.length
        };
    }

    showSearchSuggestions(currentInput = '') {
        if (!this.searchSuggestions) return;

        let suggestions = [];

        // Add search history
        if (this.searchHistory.length > 0) {
            suggestions.push({
                type: 'history',
                title: 'Recent Searches',
                items: this.searchHistory.filter(item => 
                    !currentInput || item.toLowerCase().includes(currentInput.toLowerCase())
                ).slice(0, 5)
            });
        }

        // Add quick search suggestions
        const quickSuggestions = this.getQuickSuggestions(currentInput);
        if (quickSuggestions.length > 0) {
            suggestions.push({
                type: 'suggestions',
                title: 'Suggestions',
                items: quickSuggestions
            });
        }

        if (suggestions.length === 0) {
            this.hideSearchSuggestions();
            return;
        }

        let suggestionsHTML = '<div class="search-suggestions-content">';
        
        suggestions.forEach(section => {
            suggestionsHTML += `
                <div class="suggestion-section">
                    <div class="suggestion-title">${section.title}</div>
                    <ul class="suggestion-list">
            `;
            
            section.items.forEach(item => {
                const iconClass = section.type === 'history' ? 'history-icon' : 'suggestion-icon';
                suggestionsHTML += `
                    <li class="suggestion-item" data-value="${this.escapeHtml(item)}">
                        <span class="${iconClass}">${section.type === 'history' ? '🕒' : '💡'}</span>
                        <span class="suggestion-text">${this.escapeHtml(item)}</span>
                    </li>
                `;
            });
            
            suggestionsHTML += '</ul></div>';
        });

        if (this.searchHistory.length > 0) {
            suggestionsHTML += `
                <div class="suggestion-actions">
                    <button class="clear-history-btn" onclick="searchManager.clearSearchHistory()">
                        Clear History
                    </button>
                </div>
            `;
        }

        suggestionsHTML += '</div>';

        this.searchSuggestions.innerHTML = suggestionsHTML;
        this.searchSuggestions.style.display = 'block';

        // Add click handlers for suggestions
        this.searchSuggestions.querySelectorAll('.suggestion-item').forEach(item => {
            item.addEventListener('click', () => {
                const value = item.getAttribute('data-value');
                this.searchInput.value = value;
                this.hideSearchSuggestions();
                this.performSearch(value);
            });
        });
    }

    getQuickSuggestions(input) {
        const suggestions = [
            'engagement', 'completion', 'satisfaction', 'retention',
            'performance', 'assessment', 'feedback', 'participation',
            'time', 'cost', 'ROI', 'effectiveness', 'knowledge',
            'skills', 'competency', 'learning outcomes'
        ];

        if (!input) return suggestions.slice(0, 6);

        return suggestions.filter(suggestion => 
            suggestion.toLowerCase().includes(input.toLowerCase())
        ).slice(0, 6);
    }

    hideSearchSuggestions() {
        if (this.searchSuggestions) {
            this.searchSuggestions.style.display = 'none';
        }
    }

    handleKeyboardNavigation(e) {
        const suggestions = this.searchSuggestions?.querySelectorAll('.suggestion-item');
        const currentActive = this.searchSuggestions?.querySelector('.suggestion-item.active');
        let activeIndex = currentActive ? Array.from(suggestions).indexOf(currentActive) : -1;

        switch (e.key) {
            case 'ArrowDown':
                if (suggestions && suggestions.length > 0) {
                    e.preventDefault();
                    activeIndex = (activeIndex + 1) % suggestions.length;
                    this.setActiveSuggestion(suggestions, activeIndex);
                }
                break;
            case 'ArrowUp':
                if (suggestions && suggestions.length > 0) {
                    e.preventDefault();
                    activeIndex = activeIndex <= 0 ? suggestions.length - 1 : activeIndex - 1;
                    this.setActiveSuggestion(suggestions, activeIndex);
                }
                break;
            case 'Enter':
                e.preventDefault();
                if (currentActive) {
                    // Use selected suggestion
                    currentActive.click();
                } else {
                    // Perform search with current input value
                    const searchTerm = this.searchInput.value.trim();
                    if (searchTerm) {
                        this.performSearch(searchTerm);
                        this.hideSearchSuggestions();
                        this.searchInput.blur(); // Remove focus to hide mobile keyboard
                    }
                }
                break;
            case 'Escape':
                this.hideSearchSuggestions();
                this.searchInput.blur();
                break;
        }
    }

    setActiveSuggestion(suggestions, activeIndex) {
        suggestions.forEach((suggestion, index) => {
            suggestion.classList.toggle('active', index === activeIndex);
        });
    }

    clearSearch() {
        if (this.searchInput) {
            this.searchInput.value = '';
        }
        this.currentSearchTerm = '';
        this.clearSearchResults();
        this.hideSearchSuggestions();
        
        // Hide clear button
        const clearButton = document.getElementById('clear-search');
        if (clearButton) {
            clearButton.style.display = 'none';
        }
        
        // Show all metrics again
        this.showAllMetrics();
    }
    
    showAllMetrics() {
        const allCards = document.querySelectorAll('.metric-card');
        allCards.forEach(card => {
            card.style.display = 'block';
            card.classList.remove('search-hidden');
        });
        this.toggleMetricsContainerVisibility(true);
        
        // Reset all filters and show all metrics
        // Avoid recursive call into performSearch('') which would re-trigger showAllMetrics()
    }

    clearSearchResults() {
        const searchInfo = document.getElementById('search-info');
        if (searchInfo) {
            searchInfo.innerHTML = '';
        }

        // Remove highlights
        const highlights = document.querySelectorAll('.search-highlight');
        highlights.forEach(highlight => {
            const parent = highlight.parentNode;
            parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
            parent.normalize();
        });
    }

    addToSearchHistory(searchTerm) {
        if (!searchTerm || searchTerm.length < this.minSearchLength) return;

        // Remove if already exists
        this.searchHistory = this.searchHistory.filter(item => item !== searchTerm);
        
        // Add to beginning
        this.searchHistory.unshift(searchTerm);
        
        // Limit history size
        this.searchHistory = this.searchHistory.slice(0, this.maxHistoryItems);
        
        // Save to localStorage
        localStorage.setItem('searchHistory', JSON.stringify(this.searchHistory));
    }

    loadSearchHistory() {
        try {
            this.searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');
        } catch (error) {
            console.warn('Failed to load search history:', error);
            this.searchHistory = [];
        }
    }

    clearSearchHistory() {
        this.searchHistory = [];
        localStorage.removeItem('searchHistory');
        this.hideSearchSuggestions();
    }

    setSearchingState(isSearching) {
        this.isSearching = isSearching;
        
        const searchInput = this.searchInput;
        const loadingIndicator = document.getElementById('search-loading');
        
        if (searchInput) {
            searchInput.classList.toggle('searching', isSearching);
        }
        
        if (loadingIndicator) {
            loadingIndicator.style.display = isSearching ? 'block' : 'none';
        }
    }

    // Simple helpers to integrate with existing searching UI state
    showSearchLoading() {
        this.setSearchingState(true);
    }

    hideSearchLoading() {
        this.setSearchingState(false);
    }

    // Plan metrics container visibility helper
    toggleMetricsContainerVisibility(show) {
        const planContainer = document.getElementById('plan-metrics-container');
        const emptyState = document.getElementById('metrics-empty-state');
        if (planContainer) planContainer.style.display = show ? 'block' : 'none';
        if (emptyState) emptyState.style.display = show ? 'none' : 'block';
    }

    showSearchError(message) {
        const searchInfo = document.getElementById('search-info');
        if (searchInfo) {
            searchInfo.innerHTML = `
                <div class="search-error">
                    <span class="error-icon">⚠️</span>
                    <span class="error-message">${this.escapeHtml(message)}</span>
                </div>
            `;
        }
    }

    updateAppState(searchTerm) {
        if (window.AppState) {
            window.AppState.searchQuery = searchTerm;
            
            // Update URL if URLManager exists
            if (window.URLManager && typeof window.URLManager.updateURL === 'function') {
                window.URLManager.updateURL();
            }
        }
    }

    toggleAdvancedSearch() {
        const advancedPanel = document.getElementById('advanced-search-panel');
        if (advancedPanel) {
            const isVisible = advancedPanel.style.display !== 'none';
            advancedPanel.style.display = isVisible ? 'none' : 'block';
            
            const toggle = document.getElementById('advanced-search-toggle');
            if (toggle) {
                toggle.textContent = isVisible ? 'Advanced Search' : 'Hide Advanced';
            }
        }
    }

    // Utility methods
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    escapeRegex(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    // Public API methods
    search(term) {
        this.searchInput.value = term;
        this.performSearch(term);
    }

    getSearchHistory() {
        return [...this.searchHistory];
    }

    clearCache() {
        this.searchCache.clear();
    }
}

// Initialize search manager when DOM is loaded
let searchManager;

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the search manager
    searchManager = new SearchManager();
    
    // Make it globally available for debugging
    window.searchManager = searchManager;
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SearchManager;
}
