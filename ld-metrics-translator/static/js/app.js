// L&D Metrics Translator - Enhanced Interactive Filtering

// Global state management
const AppState = {
    outcomes: [],
    metricTypes: [],
    metrics: [],
    selectedOutcomes: new Set(),
    selectedTypes: new Set(),
    searchQuery: '',
    currentView: 'grid',
    isLoading: false,
    bookmarkedMetrics: new Set(JSON.parse(localStorage.getItem('bookmarkedMetrics') || '[]')),
    debounceTimer: null,
    debounceDelay: 300 // 300ms debounce delay for real-time filtering
};

// URL parameter management
const URLManager = {
    updateURL() {
        const params = new URLSearchParams();
        
        if (AppState.searchQuery) {
            params.set('q', AppState.searchQuery);
        }
        
        if (AppState.selectedOutcomes.size > 0) {
            params.set('outcomes', Array.from(AppState.selectedOutcomes).join(','));
        }
        
        if (AppState.selectedTypes.size > 0) {
            params.set('types', Array.from(AppState.selectedTypes).join(','));
        }
        
        if (AppState.currentView !== 'grid') {
            params.set('view', AppState.currentView);
        }
        
        const newURL = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
        window.history.replaceState({}, '', newURL);
    },
    
    loadFromURL() {
        const params = new URLSearchParams(window.location.search);
        
        // Load search query
        const query = params.get('q');
        if (query) {
            AppState.searchQuery = query;
            const si = getSearchInput();
            if (si) si.value = query;
        }
        
        // Load selected outcomes
        const outcomes = params.get('outcomes');
        if (outcomes) {
            AppState.selectedOutcomes = new Set(outcomes.split(',').map(id => parseInt(id)));
        }
        
        // Load selected types
        const types = params.get('types');
        if (types) {
            AppState.selectedTypes = new Set(types.split(',').map(id => parseInt(id)));
        }
        
        // Load view preference
        const view = params.get('view');
        if (view && ['grid', 'list'].includes(view)) {
            AppState.currentView = view;
        }
    }
};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    console.log('L&D Metrics Translator - Enhanced Version loaded!');
    
    // Load state from URL
    URLManager.loadFromURL();
    
    // Initialize all components
    initializeApp();
    initializeFilters();
    initializeSearch();
    initializeViewToggle();
    initializeAdminTabs();
    initializeEditAndDelete();
    
    // Load initial data
    loadInitialData();
    
    // Setup browser navigation
    window.addEventListener('popstate', handleBrowserNavigation);
});

// Load initial data from API
async function loadInitialData() {
    console.log('Starting loadInitialData...');
    try {
        setLoadingState(true);
        
        // Load outcomes and metric types in parallel
        const [outcomesResponse, typesResponse] = await Promise.all([
            fetch('/api/outcomes'),
            fetch('/api/types')
        ]);
        
        if (!outcomesResponse.ok || !typesResponse.ok) {
            throw new Error('Failed to load filter data');
        }
        
        const outcomesData = await outcomesResponse.json();
        const typesData = await typesResponse.json();
        
        AppState.outcomes = outcomesData.outcomes || [];
        AppState.metricTypes = typesData.types || [];
        
        console.log('API data loaded successfully:');
        console.log('Outcomes:', AppState.outcomes.length);
        console.log('MetricTypes:', AppState.metricTypes.length);
        
        // Populate filter dropdowns
        populateFilterDropdowns();
        
        // Apply initial filters from URL
        applyFiltersFromState();
        
        // Load metrics with current filters
        await loadMetrics();
        
    } catch (error) {
        console.error('Error loading initial data:', error);
        showError('Failed to load initial data. Please refresh the page.');
    } finally {
        setLoadingState(false);
    }
}

// Initialize filter dropdowns
function initializeFilters() {
    // Outcome filter dropdown
    const outcomeDisplay = document.getElementById('outcome-display');
    const outcomeDropdown = document.getElementById('outcome-dropdown');
    const selectAllOutcomes = document.getElementById('select-all-outcomes');
    
    if (outcomeDisplay) {
        outcomeDisplay.addEventListener('click', () => {
            toggleDropdown('outcome');
        });
    }
    
    if (selectAllOutcomes) {
        selectAllOutcomes.addEventListener('change', (e) => {
            toggleSelectAll('outcomes', e.target.checked);
        });
    }
    
    // Type filter dropdown
    const typeDisplay = document.getElementById('type-display');
    const typeDropdown = document.getElementById('type-dropdown');
    const selectAllTypes = document.getElementById('select-all-types');
    
    if (typeDisplay) {
        typeDisplay.addEventListener('click', () => {
            toggleDropdown('type');
        });
    }
    
    if (selectAllTypes) {
        selectAllTypes.addEventListener('change', (e) => {
            toggleSelectAll('types', e.target.checked);
        });
    }
    
    // Filter action buttons
    const applyBtn = document.getElementById('apply-filters');
    const clearBtn = document.getElementById('clear-filters');
    const resetBtn = document.getElementById('reset-all-filters');
    
    if (applyBtn) {
        applyBtn.addEventListener('click', applyFilters);
    }
    
    if (clearBtn) {
        clearBtn.addEventListener('click', clearAllFilters);
    }
    
    if (resetBtn) {
        resetBtn.addEventListener('click', resetAllFilters);
    }
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.multi-select-container')) {
            closeAllDropdowns();
        }
    });
}

// Initialize search functionality (integrated with SearchManager)
function initializeSearch() {
    // Search functionality is now handled by SearchManager in search.js
    // This function maintains compatibility with existing code
    
    const searchInput = getSearchInput();
    if (searchInput) {
        // Load initial search query from URL
        const urlParams = new URLSearchParams(window.location.search);
        const initialQuery = urlParams.get('q');
        if (initialQuery) {
            searchInput.value = initialQuery;
            AppState.searchQuery = initialQuery;
        }
    }
}

// Initialize view toggle functionality
function initializeViewToggle() {
    const gridViewBtn = document.getElementById('grid-view');
    const listViewBtn = document.getElementById('list-view');
    
    if (gridViewBtn) {
        gridViewBtn.addEventListener('click', () => {
            setView('grid');
        });
    }
    
    if (listViewBtn) {
        listViewBtn.addEventListener('click', () => {
            setView('list');
        });
    }
    
    // Set initial view
    setView(AppState.currentView);
}

function initializeApp() {
    // Initialize bookmark functionality
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('bookmark-btn')) {
            const metricId = parseInt(e.target.dataset.id);
            toggleBookmark(metricId, e.target);
        }
    });
    
    console.log('App initialized with enhanced filtering functionality');
}

function performSearchLegacy() {
    const inputEl = getSearchInput();
    const searchTerm = (inputEl ? inputEl.value : '').toLowerCase().trim();
    const metricCards = document.querySelectorAll('.metric-card');
    const noResults = document.getElementById('no-results');
    let visibleCount = 0;
    
    metricCards.forEach(card => {
        const title = card.querySelector('.metric-title').textContent.toLowerCase();
        const description = card.querySelector('.metric-description').textContent.toLowerCase();
        const type = card.querySelector('.metric-type').textContent.toLowerCase();
        const outcome = card.querySelector('.metric-outcome').textContent.toLowerCase();
        
        const matchesSearch = searchTerm === '' || 
            title.includes(searchTerm) || 
            description.includes(searchTerm) || 
            type.includes(searchTerm) || 
            outcome.includes(searchTerm);
        
        if (matchesSearch && !card.style.display.includes('none')) {
            card.style.display = 'block';
            visibleCount++;
        } else if (!matchesSearch) {
            card.style.display = 'none';
        }
    });
    
    // Show/hide no results message
    if (noResults) {
        noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    }
    
    console.log(`Search performed for: "${searchTerm}", ${visibleCount} results found`);
}

function applyFilters() {
    const outcomeFilter = document.getElementById('outcome-filter')?.value || '';
    const typeFilter = document.getElementById('type-filter')?.value || '';
    const metricCards = document.querySelectorAll('.metric-card');
    const noResults = document.getElementById('no-results');
    let visibleCount = 0;
    
    metricCards.forEach(card => {
        const cardOutcome = card.getAttribute('data-outcome');
        const cardType = card.getAttribute('data-type');
        
        const matchesOutcome = outcomeFilter === '' || cardOutcome === outcomeFilter;
        const matchesType = typeFilter === '' || cardType === typeFilter;
        
        if (matchesOutcome && matchesType) {
            card.style.display = 'block';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });
    
    // Re-apply search after filtering
    if (window.searchManager) {
        const inputEl = getSearchInput();
        window.searchManager.performSearch(inputEl ? inputEl.value : '');
    }
    
    console.log(`Filters applied - Outcome: ${outcomeFilter || 'All'}, Type: ${typeFilter || 'All'}`);
}

function clearAllFilters() {
    // Clear all filter inputs
    const searchInput = getSearchInput();
    const outcomeFilter = document.getElementById('outcome-filter');
    const typeFilter = document.getElementById('type-filter');
    
    if (searchInput) searchInput.value = '';
    if (outcomeFilter) outcomeFilter.value = '';
    if (typeFilter) typeFilter.value = '';
    
    // Show all cards
    const metricCards = document.querySelectorAll('.metric-card');
    metricCards.forEach(card => {
        card.style.display = 'block';
    });
    
    // Hide no results message
    const noResults = document.getElementById('no-results');
    if (noResults) {
        noResults.style.display = 'none';
    }
    
    console.log('All filters cleared');
}

// Admin Tab Functions
function initializeAdminTabs() {
    // Set up tab switching
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Only handle buttons that have showTab function calls
            const onclickStr = this.onclick ? this.onclick.toString() : '';
            const tabMatch = onclickStr.match(/showTab\('(.+?)'\)/);
            if (tabMatch && tabMatch[1]) {
                showTab(tabMatch[1]);
            }
        });
    });
}

function showTab(tabName) {
    // Hide all tab contents
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.classList.remove('active');
    });
    
    // Show the selected tab content
    const selectedTab = document.getElementById(tabName + '-tab');
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Add active class to the clicked button
    const activeButton = Array.from(tabButtons).find(button => 
        button.onclick.toString().includes(`showTab('${tabName}')`)
    );
    if (activeButton) {
        activeButton.classList.add('active');
    }
    
    console.log(`Switched to ${tabName} tab`);
}

// Edit and Delete Functions
function initializeEditAndDelete() {
    // Handle edit buttons
    const editButtons = document.querySelectorAll('.btn-edit');
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const type = this.dataset.type;
            const id = this.dataset.id;
            const name = this.dataset.name;
            const description = this.dataset.description;
            
            if (type === 'outcome') {
                showEditOutcomeModal(id, name, description);
            } else if (type === 'metric-type') {
                showEditMetricTypeModal(id, name, description);
            } else if (type === 'metric') {
                const example = this.dataset.example;
                const outcomeId = this.dataset.outcomeId;
                const typeId = this.dataset.typeId;
                showEditMetricModal(id, name, description, example, outcomeId, typeId);
            }
        });
    });
    
    // Handle delete confirmations
    const deleteForms = document.querySelectorAll('.delete-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const name = this.dataset.name;
            if (!confirm(`Are you sure you want to delete "${name}"? This action cannot be undone.`)) {
                e.preventDefault();
            }
        });
    });
    
    // Get modal and handle its existence
    const modal = document.getElementById('edit-modal');
    
    // Only set up modal events if the modal exists
    if (modal) {
        const closeBtn = modal.querySelector('.close');
        
        // Only add event listener if close button exists
        if (closeBtn) {
            closeBtn.addEventListener('click', closeModal);
        }
        
        // Close modal when clicking outside
        window.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });
    }
}

function showEditOutcomeModal(id, name, description) {
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
        <h3>Edit L&D Outcome</h3>
        <form action="/edit_outcome/${id}" method="POST" class="admin-form">
            <div class="form-group">
                <label for="edit_outcome_name">Outcome Name:</label>
                <input type="text" id="edit_outcome_name" name="outcome_name" value="${name}" required>
            </div>
            <div class="form-group">
                <label for="edit_outcome_description">Description:</label>
                <textarea id="edit_outcome_description" name="outcome_description" rows="3">${description}</textarea>
            </div>
            <button type="submit" class="btn btn-primary">Update L&D Outcome</button>
            <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        </form>
    `;
    document.getElementById('edit-modal').style.display = 'block';
}

function showEditMetricTypeModal(id, name, description) {
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
        <h3>Edit Metric Type</h3>
        <form action="/edit_metric_type/${id}" method="POST" class="admin-form">
            <div class="form-group">
                <label for="edit_type_name">Metric Type Name:</label>
                <input type="text" id="edit_type_name" name="type_name" value="${name}" required>
            </div>
            <div class="form-group">
                <label for="edit_type_description">Description:</label>
                <textarea id="edit_type_description" name="type_description" rows="3">${description}</textarea>
            </div>
            <button type="submit" class="btn btn-primary">Update Metric Type</button>
            <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        </form>
    `;
    document.getElementById('edit-modal').style.display = 'block';
}

function showEditMetricModal(id, name, description, example, outcomeId, typeId) {
    // Get the current outcomes and types for the dropdowns
    const outcomeSelect = document.getElementById('metric_outcome_id');
    const typeSelect = document.getElementById('metric_type_id');
    
    let outcomeOptions = '';
    let typeOptions = '';
    
    if (outcomeSelect) {
        for (let i = 0; i < outcomeSelect.options.length; i++) {
            const option = outcomeSelect.options[i];
            if (option.value) {
                const selected = option.value == outcomeId ? 'selected' : '';
                outcomeOptions += `<option value="${option.value}" ${selected}>${option.text}</option>`;
            }
        }
    }
    
    if (typeSelect) {
        for (let i = 0; i < typeSelect.options.length; i++) {
            const option = typeSelect.options[i];
            if (option.value) {
                const selected = option.value == typeId ? 'selected' : '';
                typeOptions += `<option value="${option.value}" ${selected}>${option.text}</option>`;
            }
        }
    }
    
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = `
        <h3>Edit Metric</h3>
        <form action="/edit_metric/${id}" method="POST" class="admin-form">
            <div class="form-group">
                <label for="edit_metric_name">Metric Name:</label>
                <input type="text" id="edit_metric_name" name="metric_name" value="${name}" required>
            </div>
            <div class="form-group">
                <label for="edit_metric_description">Description:</label>
                <textarea id="edit_metric_description" name="metric_description" rows="4" required>${description}</textarea>
            </div>
            <div class="form-group">
                <label for="edit_metric_example">Example/Use Case:</label>
                <textarea id="edit_metric_example" name="metric_example" rows="3">${example}</textarea>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label for="edit_metric_outcome_id">L&D Outcome:</label>
                    <select id="edit_metric_outcome_id" name="metric_outcome_id" required>
                        <option value="">Select an outcome...</option>
                        ${outcomeOptions}
                    </select>
                </div>
                <div class="form-group">
                    <label for="edit_metric_type_id">Metric Type:</label>
                    <select id="edit_metric_type_id" name="metric_type_id" required>
                        <option value="">Select a type...</option>
                        ${typeOptions}
                    </select>
                </div>
            </div>
            <button type="submit" class="btn btn-primary">Update Metric</button>
            <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
        </form>
    `;
    document.getElementById('edit-modal').style.display = 'block';
}

function closeModal() {
    document.getElementById('edit-modal').style.display = 'none';
}

// Enhanced filtering utility functions

// Populate filter dropdowns with data from API
function populateFilterDropdowns() {
    // Only proceed if we're on a page with filter dropdowns
    const outcomeOptions = document.getElementById('outcome-options');
    const typeOptions = document.getElementById('type-options');
    
    if (!outcomeOptions || !typeOptions) {
        console.log('Filter dropdowns not found on this page, skipping population.');
        return; // Exit if we're not on a page with filter dropdowns
    }
    
    console.log('Populating filter dropdowns...');
    console.log('AppState.outcomes:', AppState.outcomes);
    console.log('AppState.metricTypes:', AppState.metricTypes);
    
    console.log('outcomeOptions element:', outcomeOptions);
    console.log('typeOptions element:', typeOptions);
    
    if (outcomeOptions) {
        outcomeOptions.innerHTML = '';
        AppState.outcomes.forEach(outcome => {
            const isSelected = AppState.selectedOutcomes.has(outcome.id);
            const option = document.createElement('div');
            option.className = 'option-item';
            option.innerHTML = `
                <label>
                    <input type="checkbox" value="${outcome.id}" ${isSelected ? 'checked' : ''}>
                    <span class="option-text">${outcome.name}</span>
                    <span class="option-count">(${outcome.metrics_count || 0})</span>
                </label>
            `;
            
            option.querySelector('input').addEventListener('change', (e) => {
                handleFilterChange('outcomes', outcome.id, e.target.checked);
            });
            
            outcomeOptions.appendChild(option);
        });
    }
    
    if (typeOptions) {
        typeOptions.innerHTML = '';
        AppState.metricTypes.forEach(type => {
            const isSelected = AppState.selectedTypes.has(type.id);
            const option = document.createElement('div');
            option.className = 'option-item';
            option.innerHTML = `
                <label>
                    <input type="checkbox" value="${type.id}" ${isSelected ? 'checked' : ''}>
                    <span class="option-text">${type.name}</span>
                    <span class="option-count">(${type.metrics_count || 0})</span>
                </label>
            `;
            
            option.querySelector('input').addEventListener('change', (e) => {
                handleFilterChange('types', type.id, e.target.checked);
            });
            
            typeOptions.appendChild(option);
        });
    }
    
    updateFilterDisplays();
}

// Handle filter changes with debouncing for real-time filtering
function handleFilterChange(filterType, id, isChecked) {
    if (filterType === 'outcomes') {
        if (isChecked) {
            AppState.selectedOutcomes.add(id);
        } else {
            AppState.selectedOutcomes.delete(id);
        }
    } else if (filterType === 'types') {
        if (isChecked) {
            AppState.selectedTypes.add(id);
        } else {
            AppState.selectedTypes.delete(id);
        }
    }
    
    updateFilterDisplays();
    updateSelectAllStates();
    updateActiveFilters();
    
    // Apply filters in real-time with debouncing
    debouncedLoadMetrics();
    
    // Update URL with current filters
    URLManager.updateURL();
}

// Toggle dropdown visibility
function toggleDropdown(type) {
    const dropdown = document.getElementById(`${type}-dropdown`);
    const display = document.getElementById(`${type}-display`);
    const allDropdowns = document.querySelectorAll('.multi-select-dropdown');
    const allDisplays = document.querySelectorAll('.multi-select-display');
    
    // Close other dropdowns and remove active states
    allDropdowns.forEach(dd => {
        if (dd !== dropdown) {
            dd.classList.remove('show');
            dd.style.display = 'none';
        }
    });
    
    allDisplays.forEach(disp => {
        if (disp !== display) {
            disp.classList.remove('active');
        }
    });
    
    // Toggle current dropdown
    if (dropdown && display) {
        const isVisible = dropdown.classList.contains('show');
        
        if (isVisible) {
            dropdown.classList.remove('show');
            dropdown.style.display = 'none';
            display.classList.remove('active');
        } else {
            dropdown.classList.add('show');
            dropdown.style.display = 'block';
            display.classList.add('active');
        }
    }
}

// Close all dropdowns
function closeAllDropdowns() {
    const dropdowns = document.querySelectorAll('.multi-select-dropdown');
    const displays = document.querySelectorAll('.multi-select-display');
    
    dropdowns.forEach(dropdown => {
        dropdown.classList.remove('show');
        dropdown.style.display = 'none';
    });
    
    displays.forEach(display => {
        display.classList.remove('active');
    });
}

// Toggle select all functionality with real-time updates
function toggleSelectAll(filterType, isChecked) {
    if (filterType === 'outcomes') {
        if (isChecked) {
            AppState.outcomes.forEach(outcome => {
                AppState.selectedOutcomes.add(outcome.id);
            });
        } else {
            AppState.selectedOutcomes.clear();
        }
        
        // Update checkboxes
        const checkboxes = document.querySelectorAll('#outcome-options input[type="checkbox"]');
        checkboxes.forEach(cb => cb.checked = isChecked);
        
    } else if (filterType === 'types') {
        if (isChecked) {
            AppState.metricTypes.forEach(type => {
                AppState.selectedTypes.add(type.id);
            });
        } else {
            AppState.selectedTypes.clear();
        }
        
        // Update checkboxes
        const checkboxes = document.querySelectorAll('#type-options input[type="checkbox"]');
        checkboxes.forEach(cb => cb.checked = isChecked);
    }
    
    updateFilterDisplays();
}

// Update select all checkbox states
function updateSelectAllStates() {
    const selectAllOutcomes = document.getElementById('select-all-outcomes');
    const selectAllTypes = document.getElementById('select-all-types');
    
    if (selectAllOutcomes) {
        const totalOutcomes = AppState.outcomes.length;
        const selectedOutcomes = AppState.selectedOutcomes.size;
        selectAllOutcomes.checked = selectedOutcomes === totalOutcomes;
        selectAllOutcomes.indeterminate = selectedOutcomes > 0 && selectedOutcomes < totalOutcomes;
    }
    
    if (selectAllTypes) {
        const totalTypes = AppState.metricTypes.length;
        const selectedTypes = AppState.selectedTypes.size;
        selectAllTypes.checked = selectedTypes === totalTypes;
        selectAllTypes.indeterminate = selectedTypes > 0 && selectedTypes < totalTypes;
    }
}

// Update filter display text
function updateFilterDisplays() {
    const outcomeDisplay = document.getElementById('outcome-display');
    const typeDisplay = document.getElementById('type-display');
    
    if (outcomeDisplay) {
        const placeholder = outcomeDisplay.querySelector('.placeholder');
        if (AppState.selectedOutcomes.size === 0) {
            placeholder.textContent = 'All L&D Outcomes';
        } else if (AppState.selectedOutcomes.size === 1) {
            const selectedOutcome = AppState.outcomes.find(o => AppState.selectedOutcomes.has(o.id));
            placeholder.textContent = selectedOutcome ? selectedOutcome.name : 'Selected Outcomes';
        } else {
            placeholder.textContent = `${AppState.selectedOutcomes.size} outcomes selected`;
        }
    }
    
    if (typeDisplay) {
        const placeholder = typeDisplay.querySelector('.placeholder');
        if (AppState.selectedTypes.size === 0) {
            placeholder.textContent = 'All Metric Types';
        } else if (AppState.selectedTypes.size === 1) {
            const selectedType = AppState.metricTypes.find(t => AppState.selectedTypes.has(t.id));
            placeholder.textContent = selectedType ? selectedType.name : 'Selected Types';
        } else {
            placeholder.textContent = `${AppState.selectedTypes.size} types selected`;
        }
    }
    
    updateActiveFilters();
}

// Update active filters display
function updateActiveFilters() {
    const activeFilters = document.getElementById('active-filters');
    const filterTags = document.getElementById('filter-tags');
    
    if (!activeFilters || !filterTags) return;
    
    filterTags.innerHTML = '';
    let hasActiveFilters = false;
    
    // Add search filter tag
    if (AppState.searchQuery) {
        hasActiveFilters = true;
        const tag = createFilterTag('search', `Search: "${AppState.searchQuery}"`);
        filterTags.appendChild(tag);
    }
    
    // Add outcome filter tags
    AppState.selectedOutcomes.forEach(outcomeId => {
        const outcome = AppState.outcomes.find(o => o.id === outcomeId);
        if (outcome) {
            hasActiveFilters = true;
            const tag = createFilterTag('outcome', outcome.name, outcomeId);
            filterTags.appendChild(tag);
        }
    });
    
    // Add type filter tags
    AppState.selectedTypes.forEach(typeId => {
        const type = AppState.metricTypes.find(t => t.id === typeId);
        if (type) {
            hasActiveFilters = true;
            const tag = createFilterTag('type', type.name, typeId);
            filterTags.appendChild(tag);
        }
    });
    
    activeFilters.style.display = hasActiveFilters ? 'block' : 'none';
}

// Create filter tag element
function createFilterTag(type, text, id = null) {
    const tag = document.createElement('span');
    tag.className = `filter-tag filter-tag-${type}`;
    tag.innerHTML = `
        ${text}
        <button class="filter-tag-remove" data-type="${type}" data-id="${id || ''}">&times;</button>
    `;
    
    tag.querySelector('.filter-tag-remove').addEventListener('click', (e) => {
        removeFilter(e.target.dataset.type, e.target.dataset.id);
    });
    
    return tag;
}

// Remove individual filter with real-time updates
function removeFilter(type, id) {
    if (type === 'search') {
        AppState.searchQuery = '';
        const inputEl = getSearchInput();
        if (inputEl) inputEl.value = '';
    } else if (type === 'outcome' && id) {
        AppState.selectedOutcomes.delete(parseInt(id));
        const checkbox = document.querySelector(`#outcome-options input[value="${id}"]`);
        if (checkbox) checkbox.checked = false;
    } else if (type === 'type' && id) {
        AppState.selectedTypes.delete(parseInt(id));
        const checkbox = document.querySelector(`#type-options input[value="${id}"]`);
        if (checkbox) checkbox.checked = false;
    }
    
    updateFilterDisplays();
    updateSelectAllStates();
    debouncedLoadMetrics();
}

// Apply filters from current state
async function applyFiltersFromState() {
    updateFilterDisplays();
    updateSelectAllStates();
    await loadMetrics();
}

// Debounced metrics loading for real-time filtering
function debouncedLoadMetrics() {
    // Clear existing timer
    if (AppState.debounceTimer) {
        clearTimeout(AppState.debounceTimer);
    }
    
    // Set new timer
    AppState.debounceTimer = setTimeout(() => {
        loadMetrics();
    }, AppState.debounceDelay);
}

// Load metrics with current filters
async function loadMetrics() {
    try {
        setLoadingState(true);
        
        const params = new URLSearchParams();
        
        if (AppState.searchQuery) {
            params.set('q', AppState.searchQuery);
        }
        
        if (AppState.selectedOutcomes.size > 0) {
            AppState.selectedOutcomes.forEach(id => {
                params.append('outcome', id);
            });
        }
        
        if (AppState.selectedTypes.size > 0) {
            AppState.selectedTypes.forEach(id => {
                params.append('type', id);
            });
        }
        
        const response = await fetch(`/api/metrics?${params.toString()}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        AppState.metrics = data.metrics || data;
        
        renderMetrics();
        updateResultsCount();
        URLManager.updateURL();
        
    } catch (error) {
        console.error('Error loading metrics:', error);
        showError('Failed to load metrics. Please try again.');
    } finally {
        setLoadingState(false);
    }
}

// Render metrics in the DOM
function renderMetrics() {
    // Prefer Plan tab grid if present, else fallback to legacy grid
    const metricsGrid = document.getElementById('plan-metrics-grid') || document.getElementById('metrics-grid');
    if (!metricsGrid) return;
    
    if (AppState.metrics.length === 0) {
        metricsGrid.innerHTML = `
            <div class="no-data">
                <div class="no-data-icon">📈</div>
                <h3>No metrics found</h3>
                <p>Try adjusting your search criteria or filters.</p>
                <button id="reset-all-filters" class="btn btn-primary">Reset All Filters</button>
            </div>
        `;
        
        // Re-attach reset button event listener
        const resetBtn = document.getElementById('reset-all-filters');
        if (resetBtn) {
            resetBtn.addEventListener('click', resetAllFilters);
        }
        return;
    }
    
    const metricsHTML = AppState.metrics.map(metric => {
        const isBookmarked = AppState.bookmarkedMetrics.has(metric.id);
        return `
            <div class="metric-card" 
                 data-id="${metric.id}"
                 data-outcome="${metric.outcome_id}" 
                 data-type="${metric.metric_type_id}"
                 data-outcome-name="${metric.outcome_name || ''}"
                 data-type-name="${metric.metric_type_name || ''}"
                 data-name="${metric.name.toLowerCase()}"
                 data-description="${metric.description.toLowerCase()}">
                <div class="metric-header">
                    <h3 class="metric-title">${metric.name}</h3>
                    <div class="metric-badges">
                        <span class="badge badge-type">${metric.metric_type_name || 'Unknown Type'}</span>
                        <span class="badge badge-outcome">${metric.outcome_name || 'Unknown Outcome'}</span>
                    </div>
                </div>
                <div class="metric-content">
                    <p class="metric-description">${metric.description.length > 150 ? metric.description.substring(0, 150) + '...' : metric.description}</p>
                    ${metric.example ? `
                        <div class="metric-example">
                            <strong>Example:</strong> ${metric.example.length > 100 ? metric.example.substring(0, 100) + '...' : metric.example}
                        </div>
                    ` : ''}
                </div>
                <div class="metric-actions">
                    <a href="/metric/${metric.id}" class="btn btn-primary btn-sm">View Details</a>
                    <button class="btn btn-secondary btn-sm bookmark-btn ${isBookmarked ? 'bookmarked' : ''}" data-id="${metric.id}" title="${isBookmarked ? 'Remove bookmark' : 'Bookmark'}">
                        ${isBookmarked ? '★' : '☆'}
                    </button>
                </div>
            </div>
        `;
    }).join('');
    
    metricsGrid.innerHTML = metricsHTML;
}

// Update results count
function updateResultsCount() {
    // Update any known results counters
    const visibleMetrics = (document.getElementById('plan-metrics-grid') || document).querySelectorAll('.metric-card:not([style*="display: none"])');
    const count = visibleMetrics.length;
    const resultsCount = document.getElementById('results-count');
    if (resultsCount) {
        resultsCount.textContent = `${count} metric${count !== 1 ? 's' : ''} found`;
    }
    const libraryResultsCount = document.getElementById('library-results-count');
    if (libraryResultsCount) {
        libraryResultsCount.textContent = `${count} metric${count !== 1 ? 's' : ''} found`;
    }
}

// Set view mode (grid/list)
function setView(viewMode) {
    AppState.currentView = viewMode;
    
    const metricsGrid = document.getElementById('plan-metrics-grid') || document.getElementById('metrics-grid');
    const gridBtn = document.getElementById('grid-view');
    const listBtn = document.getElementById('list-view');
    
    if (metricsGrid) {
        metricsGrid.className = viewMode === 'list' ? 'metrics-grid view-list' : 'metrics-grid view-grid';
    }
    
    if (gridBtn && listBtn) {
        gridBtn.classList.toggle('active', viewMode === 'grid');
        listBtn.classList.toggle('active', viewMode === 'list');
    }
    
    URLManager.updateURL();
}

// Toggle bookmark
function toggleBookmark(metricId, button) {
    if (AppState.bookmarkedMetrics.has(metricId)) {
        AppState.bookmarkedMetrics.delete(metricId);
        button.classList.remove('bookmarked');
        button.innerHTML = '☆';
        button.title = 'Bookmark';
    } else {
        AppState.bookmarkedMetrics.add(metricId);
        button.classList.add('bookmarked');
        button.innerHTML = '★';
        button.title = 'Remove bookmark';
    }
    
    // Save to localStorage
    localStorage.setItem('bookmarkedMetrics', JSON.stringify(Array.from(AppState.bookmarkedMetrics)));
}

// Set loading state
function setLoadingState(isLoading) {
    AppState.isLoading = isLoading;
    const loadingElement = document.getElementById('loading');
    const metricsContainer = document.getElementById('plan-metrics-container') || document.getElementById('metrics-container');
    
    if (loadingElement) {
        loadingElement.style.display = isLoading ? 'block' : 'none';
    }
    
    if (metricsContainer) {
        metricsContainer.style.opacity = isLoading ? '0.5' : '1';
    }
}

// Show error message
function showError(message) {
    const errorElement = document.getElementById('error-message');
    if (errorElement) {
        const errorText = errorElement.querySelector('.error-text');
        if (errorText) {
            errorText.textContent = message;
        }
        errorElement.style.display = 'block';
        
        // Hide after 5 seconds
        setTimeout(() => {
            errorElement.style.display = 'none';
        }, 5000);
    }
}

// Reset all filters
function resetAllFilters() {
    AppState.selectedOutcomes.clear();
    AppState.selectedTypes.clear();
    AppState.searchQuery = '';
    const inputEl = getSearchInput();
    if (inputEl) inputEl.value = '';
    
    // Uncheck all checkboxes
    const checkboxes = document.querySelectorAll('.multi-select-dropdown input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);
    
    updateFilterDisplays();
    updateSelectAllStates();
    loadMetrics();
}

// Handle browser navigation
function handleBrowserNavigation() {
    URLManager.loadFromURL();
    applyFiltersFromState();
}

// Enhanced search with better matching - delegated to SearchManager
function performSearchEnhanced() {
    if (window.searchManager) {
        const inputEl = getSearchInput();
        const searchTerm = (inputEl ? inputEl.value : '').trim();
        window.searchManager.performSearch(searchTerm);
    } else {
        const inputEl = getSearchInput();
        AppState.searchQuery = (inputEl ? inputEl.value : '').trim();
        loadMetrics();
    }
}

// Enhanced apply filters
function applyFilters() {
    loadMetrics();
}

// Enhanced clear all filters - integrates with competency filters
function clearAllFilters() {
    resetAllFilters();
    
    // Clear competency filters if available
    if (window.interactiveCompetencyFilters) {
        window.interactiveCompetencyFilters.clearAllCompetencyFilters();
    }
    
    // Dispatch event for other components
    document.dispatchEvent(new CustomEvent('clearAllFilters'));
}

// View metric details function - creates a modal with detailed metric information
async function viewMetricDetails(metricId) {
    try {
        // Show loading state
        showMetricDetailsModal('Loading...', true);
        
        // Fetch metric details from API
        const response = await fetch(`/api/metrics/${metricId}`);
        if (!response.ok) {
            throw new Error(`Failed to fetch metric details: ${response.status}`);
        }
        
        const metric = await response.json();
        
        // Create comprehensive modal content
        const modalContent = `
            <div class="metric-details-modal">
                <div class="metric-details-header">
                    <h2 class="metric-details-title">${metric.name}</h2>
                    <div class="metric-details-badges">
                        <span class="badge badge-outcome">${metric.outcome_name || 'General'}</span>
                        <span class="badge badge-type">${metric.metric_type_name || 'Standard'}</span>
                    </div>
                </div>
                
                <div class="metric-details-content">
                    <div class="detail-section">
                        <h3>📋 What It Is</h3>
                        <p>${metric.description || 'A comprehensive metric for measuring learning and development outcomes.'}</p>
                    </div>
                    
                    <div class="detail-section">
                        <h3>💡 Why It Matters</h3>
                        <p>${metric.business_case || 'This metric provides valuable insights into the effectiveness of learning and development initiatives, helping organizations make data-driven decisions about their L&D investments and measure the impact on business outcomes.'}</p>
                    </div>
                    
                    ${metric.calculation_method || metric.formula ? `
                        <div class="detail-section">
                            <h3>🔢 How It's Calculated</h3>
                            <div class="calculation-info">
                                ${metric.formula ? `<div class="formula"><strong>Formula:</strong> ${metric.formula}</div>` : ''}
                                ${metric.calculation_method ? `<p>${metric.calculation_method}</p>` : ''}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${metric.example ? `
                        <div class="detail-section">
                            <h3>📊 Example / Use Case</h3>
                            <p>${metric.example}</p>
                        </div>
                    ` : ''}
                    
                    <div class="detail-section">
                        <h3>🧭 Associated Frameworks</h3>
                        <div class="frameworks-list" id="metric-frameworks-${metric.id}">
                            <p class="loading-frameworks">Loading framework associations...</p>
                        </div>
                    </div>
                    
                    <div class="detail-section">
                        <h3>🏷️ Classification Details</h3>
                        <div class="classification-grid">
                            <div class="classification-item">
                                <strong>L&D Outcome:</strong>
                                <span>${metric.outcome_name || 'General'}</span>
                            </div>
                            <div class="classification-item">
                                <strong>Metric Type:</strong>
                                <span>${metric.metric_type_name || 'Standard'}</span>
                            </div>
                            <div class="classification-item">
                                <strong>Data Collection:</strong>
                                <span>${metric.data_source || 'Survey/Assessment'}</span>
                            </div>
                            <div class="classification-item">
                                <strong>Frequency:</strong>
                                <span>${metric.measurement_frequency || 'Quarterly'}</span>
                            </div>
                        </div>
                    </div>
                    
                    <div class="detail-section">
                        <h3>⚡ Quick Actions</h3>
                        <div class="metric-actions-detailed">
                            <button class="btn btn-primary" onclick="addToReport('${metric.id}')">
                                Add to Plan
                            </button>
                            <button class="btn btn-secondary bookmark-btn ${AppState.bookmarkedMetrics.has(metric.id) ? 'bookmarked' : ''}" 
                                    onclick="toggleBookmarkFromModal('${metric.id}', this)">
                                ${AppState.bookmarkedMetrics.has(metric.id) ? '★ Bookmarked' : '☆ Bookmark'}
                            </button>
                            <button class="btn btn-outline" onclick="copyMetricLink('${metric.id}')">
                                📋 Copy Link
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Load framework associations after showing modal
        setTimeout(() => loadMetricFrameworks(metric.id), 100);
        
        showMetricDetailsModal(modalContent, false);
        
    } catch (error) {
        console.error('Error loading metric details:', error);
        showMetricDetailsModal(`
            <div class="error-state">
                <h3>Error Loading Metric Details</h3>
                <p>Failed to load metric information. Please try again.</p>
                <button class="btn btn-primary" onclick="closeMetricDetailsModal()">Close</button>
            </div>
        `, false);
    }
}

// Load framework associations for a metric
async function loadMetricFrameworks(metricId) {
    try {
        const frameworksContainer = document.getElementById(`metric-frameworks-${metricId}`);
        if (!frameworksContainer) return;
        
        // For now, show placeholder frameworks since we don't have direct metric-framework relationships
        // In a real implementation, this would query the database for actual associations
        const placeholderFrameworks = [
            'Goleman Emotional Intelligence',
            'Situational Leadership'
        ];
        
        if (placeholderFrameworks.length > 0) {
            frameworksContainer.innerHTML = `
                <div class="frameworks-tags">
                    ${placeholderFrameworks.map(fw => 
                        `<span class="framework-tag">${fw}</span>`
                    ).join('')}
                </div>
                <p class="frameworks-note">This metric is commonly used within these leadership frameworks</p>
            `;
        } else {
            frameworksContainer.innerHTML = '<p class="no-frameworks">No specific framework associations found</p>';
        }
    } catch (error) {
        console.error('Error loading frameworks:', error);
        const container = document.getElementById(`metric-frameworks-${metricId}`);
        if (container) {
            container.innerHTML = '<p class="frameworks-error">Unable to load framework associations</p>';
        }
    }
}

// Copy metric link to clipboard
function copyMetricLink(metricId) {
    const url = `${window.location.origin}${window.location.pathname}#metric-${metricId}`;
    navigator.clipboard.writeText(url).then(() => {
        if (window.showNotification) {
            window.showNotification('Metric link copied to clipboard', 'success');
        }
    }).catch(err => {
        console.error('Failed to copy link:', err);
        if (window.showNotification) {
            window.showNotification('Failed to copy link', 'error');
        }
    });
}

// Show metric details modal
function showMetricDetailsModal(content, isLoading = false) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('metric-details-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'metric-details-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content metric-details-content">
                <div class="modal-header">
                    <button class="modal-close" onclick="closeMetricDetailsModal()">&times;</button>
                </div>
                <div class="modal-body" id="metric-details-body">
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Close modal when clicking outside
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeMetricDetailsModal();
            }
        });
        
        // Close modal with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.style.display === 'block') {
                closeMetricDetailsModal();
            }
        });
    }
    
    const modalBody = document.getElementById('metric-details-body');
    modalBody.innerHTML = isLoading ? `
        <div class="loading-state">
            <div class="loading-spinner"></div>
            <p>Loading metric details...</p>
        </div>
    ` : content;
    
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
}

// Close metric details modal
function closeMetricDetailsModal() {
    const modal = document.getElementById('metric-details-modal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = ''; // Restore scrolling
    }
}

// Toggle bookmark from modal
function toggleBookmarkFromModal(metricId, button) {
    const id = parseInt(metricId);
    toggleBookmark(id, button);
    
    // Update button text
    if (AppState.bookmarkedMetrics.has(id)) {
        button.innerHTML = '★ Bookmarked';
        button.classList.add('bookmarked');
    } else {
        button.innerHTML = '☆ Bookmark';
        button.classList.remove('bookmarked');
    }
}

// Add to report function - integrates with streamlined sidebar
function addToReport(metricId) {
    console.log(`Adding metric ${metricId} to report`);
    
    // Find the metric data
    const metric = AppState.metrics.find(m => m.id == metricId);
    if (!metric) {
        console.error('Metric not found:', metricId);
        return;
    }
    
    // Add visual selection to the metric card
    const metricCard = document.querySelector(`[data-id="${metricId}"]`);
    if (metricCard) {
        metricCard.classList.add('selected');
        
        // Update button text
        const addButton = metricCard.querySelector('.btn-primary');
        if (addButton) {
            addButton.innerHTML = '<span class="btn-icon">✓</span> Added';
            addButton.classList.remove('btn-primary');
            addButton.classList.add('btn-success');
            addButton.disabled = true;
        }
    }
    
    // Integrate with streamlined sidebar
    if (window.streamlinedSidebar) {
        window.streamlinedSidebar.addMetric(metric);
    }
    
    // Try to use existing report functionality if available
    if (window.dynamicReportGenerator && window.dynamicReportGenerator.addMetric) {
        window.dynamicReportGenerator.addMetric(metricId);
    }
    
    // Close modal if open
    closeMetricDetailsModal();
    
    // Show notification
    showNotification(`${metric.name} added to selection`, 'success');
}

// Simple notification system
function showNotification(message, type = 'info') {
    // Create notification if it doesn't exist
    let notification = document.getElementById('notification');
    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'notification';
        notification.className = 'notification';
        document.body.appendChild(notification);
    }
    
    notification.className = `notification notification-${type} show`;
    notification.textContent = message;
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Helper: get the active search input element (Plan tab preferred)
function getSearchInput() {
    return document.getElementById('plan-search-input') || document.getElementById('search-input');
}
