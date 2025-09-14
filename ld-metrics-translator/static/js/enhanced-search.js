/**
 * Enhanced Search Functionality with Autocomplete
 * Handles search, autocomplete, and result display
 */

// Global search state
window.LDMetricsApp = window.LDMetricsApp || {};
window.LDMetricsApp.search = {
    allMetrics: [],
    allOutcomes: [],
    searchCache: new Map(),
    selectedMetrics: new Set()
};

// Initialize search functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing search...');
    try {
        initializeSearch();
        console.log('initializeSearch completed');
        loadSearchData();
        console.log('loadSearchData completed');
    } catch (error) {
        console.error('Error during initialization:', error);
    }
});

// Test function for debugging
window.testSearch = function(query = 'engagement') {
    console.log('=== TESTING SEARCH ===');
    console.log('Query:', query);
    
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = query;
        console.log('Set search input value to:', query);
        
        // Force a hard refresh and try direct search
        console.log('Forcing direct search execution...');
        
        // Direct search implementation
        const results = [];
        const metricCards = document.querySelectorAll('.metric-card');
        console.log('Found metric cards for direct search:', metricCards.length);
        
        metricCards.forEach(card => {
            const name = card.dataset.name || '';
            const outcome = card.dataset.outcomeName || '';
            const type = card.dataset.typeName || '';
            
            if (name.toLowerCase().includes(query.toLowerCase()) || 
                outcome.toLowerCase().includes(query.toLowerCase()) ||
                type.toLowerCase().includes(query.toLowerCase())) {
                results.push({
                    name: name,
                    outcome: outcome,
                    type: type,
                    element: card
                });
            }
        });
        
        console.log('Direct search results:', results.length);
        
        // Display results directly
        const searchResults = document.getElementById('search-results');
        const searchResultsList = document.getElementById('search-results-list');
        
        if (searchResults && searchResultsList) {
            searchResults.style.display = 'block';
            
            if (results.length > 0) {
                searchResultsList.innerHTML = results.map(result => `
                    <div class="search-result-item">
                        <h4>${result.name}</h4>
                        <p>Outcome: ${result.outcome} | Type: ${result.type}</p>
                    </div>
                `).join('');
                console.log('Search results displayed successfully');
            } else {
                searchResultsList.innerHTML = '<div class="no-results">No results found</div>';
                console.log('No results found for query');
            }
        } else {
            console.error('Search results elements not found');
        }
    } else {
        console.error('Search input not found!');
    }
};

/**
 * Initialize search components
 */
function initializeSearch() {
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const clearSearchButton = document.getElementById('clear-search');
    const clearResultsButton = document.getElementById('clear-search-results');
    
    if (!searchInput) return;
    
    // Search input event listeners
    searchInput.addEventListener('input', handleSearchInput);
    searchInput.addEventListener('keydown', handleSearchKeydown);
    searchInput.addEventListener('focus', showAutocomplete);
    searchInput.addEventListener('blur', hideAutocompleteDelayed);
    
    // Button event listeners
    if (searchButton) {
        searchButton.addEventListener('click', performSearchEnhanced);
    }
    
    if (clearSearchButton) {
        clearSearchButton.addEventListener('click', clearSearch);
    }
    
    if (clearResultsButton) {
        clearResultsButton.addEventListener('click', clearSearchResults);
    }
    
    // Initialize autocomplete dropdown
    setupAutocompleteDropdown();
}

/**
 * Load search data from the page
 */
function loadSearchData() {
    console.log('Loading search data...');
    
    // Extract metrics data from metric cards
    const metricCards = document.querySelectorAll('.metric-card');
    console.log('Found metric cards:', metricCards.length);
    
    window.LDMetricsApp.search.allMetrics = Array.from(metricCards).map(card => {
        const metric = {
            id: card.dataset.id,
            name: card.dataset.name,
            outcome: card.dataset.outcomeName,
            type: card.dataset.typeName,
            description: card.querySelector('.metric-description')?.textContent || '',
            element: card
        };
        console.log('Loaded metric:', metric.name);
        return metric;
    });
    
    // Extract outcomes from filter buttons
    const outcomeButtons = document.querySelectorAll('#outcome-filters .filter-tag');
    console.log('Found outcome buttons:', outcomeButtons.length);
    
    window.LDMetricsApp.search.allOutcomes = Array.from(outcomeButtons).map(button => ({
        id: button.dataset.id,
        name: button.textContent.trim(),
        type: 'outcome'
    }));
    
    console.log('Search data loaded:', {
        metrics: window.LDMetricsApp.search.allMetrics.length,
        outcomes: window.LDMetricsApp.search.allOutcomes.length
    });
    
    // Debug: Log first few metrics
    if (window.LDMetricsApp.search.allMetrics.length > 0) {
        console.log('First metric sample:', window.LDMetricsApp.search.allMetrics[0]);
    }
}

/**
 * Handle search input changes
 */
function handleSearchInput(event) {
    const query = event.target.value.trim();
    const clearButton = document.getElementById('clear-search');
    
    // Show/hide clear button
    if (clearButton) {
        clearButton.style.display = query ? 'block' : 'none';
    }
    
    // Update autocomplete
    if (query.length >= 2) {
        updateAutocomplete(query);
        showAutocomplete();
    } else {
        hideAutocomplete();
    }
}

/**
 * Handle search input keydown events
 */
function handleSearchKeydown(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        performSearchEnhanced();
    } else if (event.key === 'Escape') {
        hideAutocomplete();
        event.target.blur();
    } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        navigateAutocomplete('down');
    } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        navigateAutocomplete('up');
    }
}

/**
 * Setup autocomplete dropdown
 */
function setupAutocompleteDropdown() {
    const searchBox = document.querySelector('.search-box');
    if (!searchBox) return;
    
    let dropdown = document.getElementById('autocomplete-dropdown');
    if (!dropdown) {
        dropdown = document.createElement('div');
        dropdown.id = 'autocomplete-dropdown';
        dropdown.className = 'autocomplete-dropdown';
        dropdown.style.display = 'none';
        searchBox.appendChild(dropdown);
    }
}

/**
 * Update autocomplete suggestions
 */
function updateAutocomplete(query) {
    const dropdown = document.getElementById('autocomplete-dropdown');
    if (!dropdown) return;
    
    const suggestions = getSearchSuggestions(query);
    
    if (suggestions.length === 0) {
        hideAutocomplete();
        return;
    }
    
    dropdown.innerHTML = suggestions.map((suggestion, index) => `
        <div class="autocomplete-item ${index === 0 ? 'highlighted' : ''}" 
             data-value="${suggestion.name}" 
             data-type="${suggestion.type}"
             onclick="selectSuggestion('${suggestion.name}', '${suggestion.type}')">
            <div class="suggestion-main">
                <span class="suggestion-name">${highlightMatch(suggestion.name, query)}</span>
                <span class="suggestion-type">${suggestion.type}</span>
            </div>
            ${suggestion.description ? `<div class="suggestion-description">${suggestion.description}</div>` : ''}
        </div>
    `).join('');
}

/**
 * Get search suggestions based on query
 */
function getSearchSuggestions(query) {
    const lowerQuery = query.toLowerCase();
    const suggestions = [];
    
    // Search metrics
    window.LDMetricsApp.search.allMetrics.forEach(metric => {
        if (metric.name.toLowerCase().includes(lowerQuery) || 
            metric.description.toLowerCase().includes(lowerQuery)) {
            suggestions.push({
                name: metric.name,
                type: 'metric',
                description: metric.description.substring(0, 100) + '...'
            });
        }
    });
    
    // Search outcomes
    window.LDMetricsApp.search.allOutcomes.forEach(outcome => {
        if (outcome.name.toLowerCase().includes(lowerQuery)) {
            suggestions.push({
                name: outcome.name,
                type: 'outcome',
                description: ''
            });
        }
    });
    
    // Limit to 8 suggestions
    return suggestions.slice(0, 8);
}

/**
 * Highlight matching text in suggestions
 */
function highlightMatch(text, query) {
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

/**
 * Show autocomplete dropdown
 */
function showAutocomplete() {
    const dropdown = document.getElementById('autocomplete-dropdown');
    if (dropdown && dropdown.innerHTML.trim()) {
        dropdown.style.display = 'block';
    }
}

/**
 * Hide autocomplete dropdown
 */
function hideAutocomplete() {
    const dropdown = document.getElementById('autocomplete-dropdown');
    if (dropdown) {
        dropdown.style.display = 'none';
    }
}

/**
 * Hide autocomplete with delay (for blur events)
 */
function hideAutocompleteDelayed() {
    setTimeout(hideAutocomplete, 200);
}

/**
 * Navigate autocomplete with keyboard
 */
function navigateAutocomplete(direction) {
    const dropdown = document.getElementById('autocomplete-dropdown');
    if (!dropdown || dropdown.style.display === 'none') return;
    
    const items = dropdown.querySelectorAll('.autocomplete-item');
    const currentHighlighted = dropdown.querySelector('.autocomplete-item.highlighted');
    
    if (items.length === 0) return;
    
    let newIndex = 0;
    if (currentHighlighted) {
        const currentIndex = Array.from(items).indexOf(currentHighlighted);
        newIndex = direction === 'down' 
            ? (currentIndex + 1) % items.length 
            : (currentIndex - 1 + items.length) % items.length;
        currentHighlighted.classList.remove('highlighted');
    }
    
    items[newIndex].classList.add('highlighted');
}

/**
 * Select a suggestion from autocomplete
 */
function selectSuggestion(value, type) {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = value;
    }
    
    hideAutocomplete();
    performSearchEnhanced();
    
    // If it's a specific metric, scroll to it
    if (type === 'metric') {
        setTimeout(() => {
            const metricCard = Array.from(document.querySelectorAll('.metric-card'))
                .find(card => card.dataset.name === value);
            if (metricCard) {
                metricCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                metricCard.classList.add('highlight-card');
                setTimeout(() => metricCard.classList.remove('highlight-card'), 2000);
            }
        }, 100);
    }
}

/**
 * Perform search - Enhanced version
 */
function performSearchEnhanced() {
    console.log('performSearchEnhanced called');
    const searchInput = document.getElementById('search-input');
    const query = searchInput?.value.trim();
    
    console.log('Search query:', query);
    console.log('LDMetricsApp object:', window.LDMetricsApp);
    console.log('Search object:', window.LDMetricsApp?.search);
    console.log('Available metrics:', window.LDMetricsApp?.search?.allMetrics?.length || 'undefined');
    
    if (!query) {
        console.log('No query provided, clearing results');
        clearSearchResults();
        return;
    }
    
    if (!window.LDMetricsApp?.search?.allMetrics?.length) {
        console.error('No metrics data available for search!');
        return;
    }
    
    console.log('Calling searchMetrics...');
    const results = searchMetrics(query);
    console.log('Search results:', results.length);
    console.log('First few results:', results.slice(0, 3));
    
    console.log('Calling displaySearchResults...');
    displaySearchResults(results, query);
    hideAutocomplete();
    console.log('performSearchEnhanced completed');
}

/**
 * Search metrics based on query
 */
function searchMetrics(query) {
    const lowerQuery = query.toLowerCase();
    const results = [];
    
    window.LDMetricsApp.search.allMetrics.forEach(metric => {
        let relevance = 0;
        
        // Exact name match (highest relevance)
        if (metric.name.toLowerCase() === lowerQuery) {
            relevance = 100;
        }
        // Name starts with query
        else if (metric.name.toLowerCase().startsWith(lowerQuery)) {
            relevance = 90;
        }
        // Name contains query
        else if (metric.name.toLowerCase().includes(lowerQuery)) {
            relevance = 80;
        }
        // Outcome matches
        else if (metric.outcome.toLowerCase().includes(lowerQuery)) {
            relevance = 70;
        }
        // Type matches
        else if (metric.type.toLowerCase().includes(lowerQuery)) {
            relevance = 60;
        }
        // Description contains query
        else if (metric.description.toLowerCase().includes(lowerQuery)) {
            relevance = 50;
        }
        
        if (relevance > 0) {
            results.push({ ...metric, relevance });
        }
    });
    
    // Sort by relevance
    return results.sort((a, b) => b.relevance - a.relevance);
}

/**
 * Display search results
 */
function displaySearchResults(results, query) {
    console.log('displaySearchResults called with:', results.length, 'results');
    
    const searchResults = document.getElementById('search-results');
    const searchResultsList = document.getElementById('search-results-list');
    
    console.log('Search results elements:', {
        searchResults: !!searchResults,
        searchResultsList: !!searchResultsList
    });
    
    if (!searchResults || !searchResultsList) {
        console.error('Search results elements not found!');
        return;
    }
    
    // Show the search results container
    searchResults.style.display = 'block';
    
    if (results.length === 0) {
        searchResultsList.innerHTML = `
            <div class="no-results">
                <div class="no-results-icon">🔍</div>
                <h4>No results found for "${query}"</h4>
                <p>Try different keywords or check your spelling.</p>
            </div>
        `;
    } else {
        searchResultsList.innerHTML = results.map(result => `
            <div class="search-result-item" data-metric-id="${result.id}">
                <div class="result-header">
                    <h4 class="result-title">${highlightMatch(result.name, query)}</h4>
                    <div class="result-badges">
                        <span class="badge badge-outcome">${result.outcome}</span>
                        <span class="badge badge-type">${result.type}</span>
                        <span class="relevance-indicator relevance-${getRelevanceLevel(result.relevance)}">
                            ${getRelevanceIcon(result.relevance)}
                        </span>
                    </div>
                </div>
                <p class="result-description">${highlightMatch(result.description, query)}</p>
                <div class="result-actions">
                    <button class="btn btn-sm btn-outline" onclick="viewMetricDetails('${result.id}')">
                        View Details
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="addToReport('${result.id}')">
                        Add to Report
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="scrollToMetric('${result.id}')">
                        Show in List
                    </button>
                </div>
            </div>
        `).join('');
    }
    
    searchResults.style.display = 'block';
}

/**
 * Get relevance level for styling
 */
function getRelevanceLevel(relevance) {
    if (relevance >= 80) return 'high';
    if (relevance >= 60) return 'medium';
    return 'low';
}

/**
 * Get relevance icon
 */
function getRelevanceIcon(relevance) {
    if (relevance >= 80) return '🟢'; // High relevance - green
    if (relevance >= 60) return '🟡'; // Medium relevance - yellow
    return '🔴'; // Low relevance - red
}

/**
 * Scroll to metric in the main list
 */
function scrollToMetric(metricId) {
    const metricCard = document.querySelector(`[data-id="${metricId}"]`);
    if (metricCard) {
        metricCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        metricCard.classList.add('highlight-card');
        setTimeout(() => metricCard.classList.remove('highlight-card'), 2000);
    }
}

/**
 * Clear search
 */
function clearSearch() {
    const searchInput = document.getElementById('search-input');
    const clearButton = document.getElementById('clear-search');
    
    if (searchInput) {
        searchInput.value = '';
        searchInput.focus();
    }
    
    if (clearButton) {
        clearButton.style.display = 'none';
    }
    
    hideAutocomplete();
    clearSearchResults();
}

/**
 * Clear search results
 */
function clearSearchResults() {
    const searchResults = document.getElementById('search-results');
    if (searchResults) {
        searchResults.style.display = 'none';
    }
}

// Export functions for global use
window.selectSuggestion = selectSuggestion;
window.scrollToMetric = scrollToMetric;
window.clearSearch = clearSearch;
window.clearSearchResults = clearSearchResults;
window.performSearch = performSearchEnhanced;

console.log('Enhanced search functionality loaded');
