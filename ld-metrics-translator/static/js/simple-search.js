/**
 * Simple Search Implementation
 * Direct search functionality without complex initialization
 */

// Simple search function that works immediately
function simpleSearch(query) {
    console.log('Simple search called with query:', query);
    
    if (!query || query.trim() === '') {
        clearSearchResults();
        return;
    }
    
    const searchTerm = query.toLowerCase().trim();
    const results = [];
    
    // Find all metric cards
    const metricCards = document.querySelectorAll('.metric-card');
    console.log('Found metric cards:', metricCards.length);
    
    // Search through metric cards
    metricCards.forEach(card => {
        // Get text content from actual DOM elements to preserve case
        const nameElement = card.querySelector('.metric-title');
        const outcomeElement = card.querySelector('.badge-outcome');
        const typeElement = card.querySelector('.badge-type');
        const descriptionElement = card.querySelector('.metric-description');
        
        // Extract text from DOM elements (these should have proper case)
        const name = nameElement?.textContent?.trim() || '';
        const outcome = outcomeElement?.textContent?.trim() || '';
        const type = typeElement?.textContent?.trim() || '';
        const description = descriptionElement?.textContent?.trim() || '';
        
        // Skip empty results
        if (!name && !outcome && !type) return;
        
        // Convert to lowercase only for comparison
        const nameLower = name.toLowerCase();
        const outcomeLower = outcome.toLowerCase();
        const typeLower = type.toLowerCase();
        const descriptionLower = description.toLowerCase();
        
        // Check if search term matches
        if (nameLower.includes(searchTerm) || 
            outcomeLower.includes(searchTerm) || 
            typeLower.includes(searchTerm) || 
            descriptionLower.includes(searchTerm)) {
            
            results.push({
                id: card.dataset.id,
                name: name,
                outcome: outcome,
                type: type,
                description: description,
                element: card
            });
        }
    });
    
    console.log('Search results found:', results.length);
    console.log('First result sample:', results[0]);
    displaySimpleResults(results, query);
}

// Display search results
function displaySimpleResults(results, query) {
    const searchResults = document.getElementById('search-results');
    const searchResultsList = document.getElementById('search-results-list');
    
    if (!searchResults || !searchResultsList) {
        console.error('Search results elements not found');
        return;
    }
    
    // Show search results container
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
            <div class="search-result-item" onclick="window.location.href='/metric/${result.id}'" style="cursor: pointer;">
                <div class="result-header">
                    <h4 class="result-title">${highlightText(result.name, query)}</h4>
                    <div class="result-badges">
                        <span class="badge badge-outcome">${result.outcome}</span>
                        <span class="badge badge-type">${result.type}</span>
                    </div>
                </div>
                <p class="result-description">${highlightText(result.description.substring(0, 150), query)}${result.description.length > 150 ? '...' : ''}</p>
            </div>
        `).join('');
    }
    
    console.log('Search results displayed');
}

// Clear search results
function clearSearchResults() {
    const searchResults = document.getElementById('search-results');
    const searchResultsList = document.getElementById('search-results-list');
    
    if (searchResults) {
        searchResults.style.display = 'none';
    }
    
    if (searchResultsList) {
        searchResultsList.innerHTML = '';
    }
}

// Highlight search terms in text
function highlightText(text, query) {
    if (!query || !text) return text;
    
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

// Scroll to metric card
function scrollToMetric(metricName) {
    const metricCard = Array.from(document.querySelectorAll('.metric-card'))
        .find(card => card.dataset.name === metricName);
    
    if (metricCard) {
        metricCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        metricCard.classList.add('highlight-card');
        setTimeout(() => metricCard.classList.remove('highlight-card'), 2000);
    }
}

// Initialize simple search when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Simple search initialized');
    
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    
    if (searchInput) {
        // Enter key search
        searchInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                simpleSearch(this.value);
            }
        });
        
        // Input change for autocomplete-like behavior
        searchInput.addEventListener('input', function(e) {
            const query = e.target.value.trim();
            if (query.length >= 3) {
                simpleSearch(query);
            } else if (query.length === 0) {
                clearSearchResults();
            }
        });
    }
    
    if (searchButton) {
        searchButton.addEventListener('click', function() {
            const query = searchInput ? searchInput.value : '';
            simpleSearch(query);
        });
    }
    
    // Clear search button
    const clearSearchButton = document.getElementById('clear-search');
    if (clearSearchButton) {
        clearSearchButton.addEventListener('click', function() {
            if (searchInput) {
                searchInput.value = '';
            }
            clearSearchResults();
        });
    }
    
    // Clear results button
    const clearResultsButton = document.getElementById('clear-search-results');
    if (clearResultsButton) {
        clearResultsButton.addEventListener('click', clearSearchResults);
    }
});

// Global test function
window.testSimpleSearch = function(query = 'engagement') {
    console.log('=== TESTING SIMPLE SEARCH ===');
    
    // First, let's see what's actually in the metric cards
    const metricCards = document.querySelectorAll('.metric-card');
    console.log('Total metric cards found:', metricCards.length);
    
    if (metricCards.length > 0) {
        const firstCard = metricCards[0];
        console.log('First card data attributes:', {
            name: firstCard.dataset.name,
            outcomeName: firstCard.dataset.outcomeName,
            typeName: firstCard.dataset.typeName
        });
        
        const titleEl = firstCard.querySelector('.metric-title');
        const outcomeEl = firstCard.querySelector('.badge-outcome');
        const typeEl = firstCard.querySelector('.badge-type');
        
        console.log('First card DOM elements:', {
            titleExists: !!titleEl,
            outcomeExists: !!outcomeEl,
            typeExists: !!typeEl,
            titleText: titleEl?.textContent,
            outcomeText: outcomeEl?.textContent,
            typeText: typeEl?.textContent
        });
        
        // Check if the data is already lowercase in the database
        console.log('Data source analysis:', {
            nameIsLowercase: firstCard.dataset.name === firstCard.dataset.name?.toLowerCase(),
            outcomeIsLowercase: firstCard.dataset.outcomeName === firstCard.dataset.outcomeName?.toLowerCase(),
            typeIsLowercase: firstCard.dataset.typeName === firstCard.dataset.typeName?.toLowerCase()
        });
    }
    
    simpleSearch(query);
};
