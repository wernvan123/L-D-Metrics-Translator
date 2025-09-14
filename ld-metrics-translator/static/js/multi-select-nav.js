// Multi-Select Dropdown Navigation for L&D Metrics Translator
// Supports multiple selections with checkboxes

class MultiSelectNavigation {
    constructor() {
        this.selections = {
            categories: new Set(),
            outcomes: new Set(), 
            metrics: new Set(),
            neuroscience: new Set()
        };
        this.init();
    }

    init() {
        document.addEventListener('DOMContentLoaded', () => {
            this.setupEventListeners();
            this.updateAllButtonTexts();
        });
    }

    setupEventListeners() {
        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.dropdown-nav-item')) {
                this.closeAllDropdowns();
            }
        });

        // Prevent dropdown from closing when clicking inside multi-select dropdowns
        document.querySelectorAll('.dropdown-content.multi-select').forEach(dropdown => {
            dropdown.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        });

        // Handle escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllDropdowns();
            }
        });
    }

    toggleDropdown(dropdownId) {
        const dropdown = document.getElementById(dropdownId);
        if (!dropdown) {
            console.warn('Dropdown not found:', dropdownId);
            return;
        }

        const button = dropdown.previousElementSibling || 
                      dropdown.parentElement?.querySelector('.multi-select-display') ||
                      document.querySelector(`[onclick*="${dropdownId}"]`);
        
        // Close other dropdowns first
        this.closeAllDropdowns(dropdownId);
        
        if (dropdown.classList.contains('show') || dropdown.style.display === 'block') {
            this.closeDropdown(dropdownId);
        } else {
            this.openDropdown(dropdownId);
        }
    }

    openDropdown(dropdownId) {
        const dropdown = document.getElementById(dropdownId);
        const button = dropdown?.previousElementSibling || 
                      dropdown?.parentElement?.querySelector('.multi-select-display') ||
                      document.querySelector(`[onclick*="${dropdownId}"]`);
        
        if (dropdown) {
            dropdown.classList.add('show');
            dropdown.style.display = 'block';
            
            if (button) {
                button.classList.add('dropdown-open');
                const arrow = button.querySelector('.dropdown-arrow');
                if (arrow) {
                    arrow.style.transform = 'rotate(180deg)';
                }
            }
            
            // Add smooth animation
            dropdown.style.opacity = '0';
            dropdown.style.transform = 'translateY(-10px)';
            
            setTimeout(() => {
                dropdown.style.transition = 'all 0.3s ease';
                dropdown.style.opacity = '1';
                dropdown.style.transform = 'translateY(0)';
            }, 10);
        }
    }

    closeDropdown(dropdownId) {
        const dropdown = document.getElementById(dropdownId);
        const button = dropdown?.previousElementSibling || 
                      dropdown?.parentElement?.querySelector('.multi-select-display') ||
                      document.querySelector(`[onclick*="${dropdownId}"]`);
        
        if (dropdown) {
            dropdown.classList.remove('show');
            dropdown.style.display = 'none';
            
            if (button) {
                button.classList.remove('dropdown-open');
                const arrow = button.querySelector('.dropdown-arrow');
                if (arrow) {
                    arrow.style.transform = 'rotate(0deg)';
                }
            }
        }
    }

    closeAllDropdowns(except = null) {
        const dropdowns = document.querySelectorAll('.dropdown-content');
        const buttons = document.querySelectorAll('.tab-button');
        
        dropdowns.forEach(dropdown => {
            if (dropdown.id !== except) {
                dropdown.classList.remove('show');
            }
        });
        
        buttons.forEach(button => {
            if (except && button.nextElementSibling && button.nextElementSibling.id === except) {
                return; // Skip the excepted button
            }
            button.classList.remove('dropdown-open');
        });
    }

    toggleSelection(type, id, name) {
        const selections = this.selections[type];
        
        if (selections.has(id)) {
            selections.delete(id);
        } else {
            selections.add(id);
        }
        
        this.updateSelectAllState(type);
        this.updateButtonText(type);
        this.updatePlaceholderText(type);
        this.applyFiltering();
        this.showSelectionFeedback(type, name, selections.has(id));
    }
    
    updatePlaceholderText(type) {
        const container = document.querySelector(`#${type}-dropdown`)?.parentElement;
        const placeholder = container?.querySelector('.placeholder');
        
        if (placeholder) {
            const count = this.selections[type].size;
            if (count === 0) {
                const labels = {
                    outcomes: 'Select outcomes...',
                    categories: 'Select categories...',
                    metrics: 'Select metrics...',
                    neuroscience: 'Select neuroscience...'
                };
                placeholder.textContent = labels[type] || 'Select options...';
            } else {
                const plural = count === 1 ? 'item' : 'items';
                placeholder.textContent = `${count} ${plural} selected`;
            }
        }
    }

    toggleSelectAll(type) {
        const selectAllCheckbox = document.getElementById(`select-all-${type}`);
        const checkboxes = document.querySelectorAll(`#${type}-dropdown input[type="checkbox"]:not(#select-all-${type})`);
        const selections = this.selections[type];
        
        if (selectAllCheckbox.checked) {
            // Select all
            checkboxes.forEach(checkbox => {
                checkbox.checked = true;
                selections.add(checkbox.value);
            });
        } else {
            // Deselect all
            checkboxes.forEach(checkbox => {
                checkbox.checked = false;
                selections.delete(checkbox.value);
            });
        }
        
        this.updateButtonText(type);
        this.applyFiltering();
        this.showSelectionFeedback(type, 'All Items', selectAllCheckbox.checked);
    }

    updateSelectAllState(type) {
        const selectAllCheckbox = document.getElementById(`select-all-${type}`);
        const checkboxes = document.querySelectorAll(`#${type}-dropdown input[type="checkbox"]:not(#select-all-${type})`);
        const checkedBoxes = document.querySelectorAll(`#${type}-dropdown input[type="checkbox"]:not(#select-all-${type}):checked`);
        
        if (!selectAllCheckbox) return;
        
        if (checkedBoxes.length === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else if (checkedBoxes.length === checkboxes.length) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;
        }
    }

    updateButtonText(type) {
        const selections = this.selections[type];
        const count = selections.size;
        
        let buttonSelector, defaultText, singularText, pluralText;
        
        switch(type) {
            case 'categories':
                buttonSelector = '[onclick*="categories-dropdown"] .tab-text';
                defaultText = 'Metric Categories';
                singularText = 'Category';
                pluralText = 'Categories';
                break;
            case 'outcomes':
                buttonSelector = '[onclick*="outcomes-dropdown"] .tab-text';
                defaultText = 'L & D Outcomes';
                singularText = 'Outcome';
                pluralText = 'Outcomes';
                break;
            case 'metrics':
                buttonSelector = '[onclick*="metrics-dropdown"] .tab-text';
                defaultText = 'Find Metrics';
                singularText = 'Metric';
                pluralText = 'Metrics';
                break;
            case 'neuroscience':
                buttonSelector = '[onclick*="neuroscience-dropdown"] .tab-text';
                defaultText = 'Explore Categories';
                singularText = 'Science Metric';
                pluralText = 'Science Metrics';
                break;
        }
        
        const textElement = document.querySelector(buttonSelector);
        if (!textElement) return;
        
        if (count === 0) {
            textElement.textContent = `[${defaultText}]`;
        } else if (count === 1) {
            textElement.textContent = `[1 ${singularText} Selected]`;
        } else {
            textElement.textContent = `[${count} ${pluralText} Selected]`;
        }
    }

    updateAllButtonTexts() {
        Object.keys(this.selections).forEach(type => {
            this.updateButtonText(type);
        });
    }

    applyFiltering() {
        const cards = document.querySelectorAll('.metric-card');
        let visibleCount = 0;
        
        cards.forEach(card => {
            if (this.cardMatchesSelections(card)) {
                card.style.display = 'block';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });
        
        // Update results count in sidebar
        this.updateResultsCount(visibleCount);
        this.updateFilterSummary();
        this.showFilterResults(visibleCount, cards.length);
    }
    
    updateResultsCount(count) {
        const resultsCount = document.getElementById('results-count');
        const resultsSummary = document.getElementById('results-summary');
        
        if (resultsCount) {
            resultsCount.textContent = count;
        }
        
        if (resultsSummary) {
            const plural = count === 1 ? 'metric' : 'metrics';
            resultsSummary.innerHTML = `<span id="results-count">${count}</span> ${plural} found`;
        }
    }

    cardMatchesSelections(card) {
        // If no selections are made, show all cards
        const hasAnySelections = Object.values(this.selections).some(set => set.size > 0);
        if (!hasAnySelections) return true;
        
        // Get card data attributes or text content
        const cardData = this.extractCardData(card);
        
        let matches = true;
        
        // Check category matches (AND logic within categories)
        if (this.selections.categories.size > 0) {
            const categoryMatches = Array.from(this.selections.categories).some(categoryId => {
                return this.checkCategoryMatch(cardData, categoryId);
            });
            if (!categoryMatches) matches = false;
        }
        
        // Check outcome matches (AND logic within outcomes)
        if (this.selections.outcomes.size > 0) {
            const outcomeMatches = Array.from(this.selections.outcomes).some(outcomeId => {
                return this.checkOutcomeMatch(cardData, outcomeId);
            });
            if (!outcomeMatches) matches = false;
        }
        
        // For now, ignore specific metric and neuroscience selections to avoid over-filtering
        // These will be used for priority scoring instead
        
        return matches;
    }

    extractCardData(card) {
        return {
            title: card.querySelector('.metric-title')?.textContent?.toLowerCase() || '',
            type: card.querySelector('.badge-type')?.textContent?.toLowerCase() || '',
            outcome: card.querySelector('.badge-outcome')?.textContent?.toLowerCase() || '',
            description: card.querySelector('.metric-description')?.textContent?.toLowerCase() || '',
            id: card.dataset.metricId || card.id || ''
        };
    }

    checkCategoryMatch(cardData, categoryId) {
        // Get category name from dropdown
        const categoryCheckbox = document.querySelector(`#categories-dropdown input[value="${categoryId}"]`);
        if (categoryCheckbox) {
            const categoryName = categoryCheckbox.dataset.name?.toLowerCase() || categoryCheckbox.nextElementSibling?.textContent?.toLowerCase();
            
            // Direct match with card type badge
            if (cardData.type === categoryName) return true;
            
            // Flexible matching for common variations
            if (categoryName.includes('operational') && cardData.type.includes('operational')) return true;
            if (categoryName.includes('behavioral') && cardData.type.includes('behavioral')) return true;
            if (categoryName.includes('neuroscience') && cardData.type.includes('neuroscience')) return true;
            
            // Fallback to partial matching
            return cardData.type.includes(categoryName) || 
                   cardData.title.includes(categoryName) ||
                   cardData.description.includes(categoryName);
        }
        return true; // If checkbox not found, don't filter out
    }

    checkOutcomeMatch(cardData, outcomeId) {
        const outcomeCheckbox = document.querySelector(`#outcomes-dropdown input[value="${outcomeId}"]`);
        if (outcomeCheckbox) {
            const outcomeName = outcomeCheckbox.dataset.name?.toLowerCase();
            // More flexible matching
            return cardData.outcome.includes(outcomeName) || 
                   cardData.description.includes(outcomeName) ||
                   cardData.title.includes(outcomeName) ||
                   // Handle common outcome variations
                   (outcomeName.includes('engagement') && (cardData.outcome.includes('engagement') || cardData.description.includes('engagement'))) ||
                   (outcomeName.includes('retention') && (cardData.outcome.includes('retention') || cardData.description.includes('retention'))) ||
                   (outcomeName.includes('performance') && (cardData.outcome.includes('performance') || cardData.description.includes('performance')));
        }
        return true; // If checkbox not found, don't filter out
    }

    checkMetricMatch(cardData, metricId) {
        return cardData.id === metricId || cardData.title.includes(metricId);
    }

    checkNeuroscienceMatch(cardData, metricId) {
        return cardData.id === metricId || cardData.type.includes('neuroscience');
    }

    calculateCardPriority(card) {
        const cardData = this.extractCardData(card);
        let matchCount = 0;
        
        // Count how many selection types this card matches
        if (this.selections.categories.size > 0) {
            const categoryMatches = Array.from(this.selections.categories).some(id => 
                this.checkCategoryMatch(cardData, id));
            if (categoryMatches) matchCount++;
        }
        
        if (this.selections.outcomes.size > 0) {
            const outcomeMatches = Array.from(this.selections.outcomes).some(id => 
                this.checkOutcomeMatch(cardData, id));
            if (outcomeMatches) matchCount++;
        }
        
        if (matchCount >= 2) return 'high';
        if (matchCount >= 1) return 'medium';
        return 'normal';
    }

    updateFilterSummary() {
        let filterSummary = document.querySelector('.multi-select-filter-summary');
        
        if (!filterSummary) {
            filterSummary = document.createElement('div');
            filterSummary.className = 'multi-select-filter-summary';
            
            const metricsContainer = document.querySelector('.metrics-grid');
            if (metricsContainer && metricsContainer.parentNode) {
                metricsContainer.parentNode.insertBefore(filterSummary, metricsContainer);
            }
        }
        
        const activeTags = this.generateFilterTags();
        
        if (activeTags.length > 0) {
            filterSummary.innerHTML = `
                <div class="filter-tags-container">
                    <span class="filter-label">Active Filters:</span>
                    <div class="filter-tags">
                        ${activeTags.join('')}
                    </div>
                    <button onclick="multiSelectNav.clearAllSelections()" class="clear-all-filters-btn">
                        Clear All
                    </button>
                </div>
            `;
            filterSummary.style.display = 'block';
        } else {
            filterSummary.style.display = 'none';
        }
    }

    generateFilterTags() {
        const tags = [];
        
        Object.entries(this.selections).forEach(([type, selections]) => {
            selections.forEach(id => {
                const checkbox = document.querySelector(`#${type}-dropdown input[value="${id}"]`);
                if (checkbox) {
                    const name = checkbox.dataset.name;
                    const typeLabel = type.charAt(0).toUpperCase() + type.slice(1, -1); // Remove 's' and capitalize
                    tags.push(`
                        <span class="filter-tag ${type}-tag">
                            <span class="tag-type">${typeLabel}:</span>
                            <span class="tag-name">${name}</span>
                            <button onclick="multiSelectNav.removeSelection('${type}', '${id}')" class="remove-tag">×</button>
                        </span>
                    `);
                }
            });
        });
        
        return tags;
    }

    removeSelection(type, id) {
        this.selections[type].delete(id);
        
        // Uncheck the checkbox
        const checkbox = document.querySelector(`#${type}-dropdown input[value="${id}"]`);
        if (checkbox) {
            checkbox.checked = false;
        }
        
        this.updateButtonText(type);
        this.updateSelectAllState(type);
        this.applyFiltering();
    }

    clearAllSelections() {
        // Clear all selections
        Object.keys(this.selections).forEach(type => {
            this.selections[type].clear();
            
            // Uncheck all checkboxes
            const checkboxes = document.querySelectorAll(`#${type}-dropdown input[type="checkbox"]`);
            checkboxes.forEach(checkbox => {
                checkbox.checked = false;
                checkbox.indeterminate = false;
            });
            
            this.updateButtonText(type);
        });
        
        this.applyFiltering();
        this.showSelectionFeedback('All', 'Filters Cleared', false);
    }

    showSelectionFeedback(type, name, isSelected) {
        const action = isSelected ? 'Selected' : 'Deselected';
        const message = type === 'All' ? name : `${action}: ${name}`;
        
        // Create feedback notification
        const feedback = document.createElement('div');
        feedback.className = 'selection-feedback';
        feedback.innerHTML = `
            <div class="feedback-content">
                <span class="feedback-icon">${isSelected ? '✓' : '✗'}</span>
                <span class="feedback-text">${message}</span>
            </div>
        `;
        
        document.body.appendChild(feedback);
        
        // Show feedback
        setTimeout(() => feedback.classList.add('show'), 100);
        
        // Remove after 2 seconds
        setTimeout(() => {
            feedback.classList.remove('show');
            setTimeout(() => feedback.remove(), 300);
        }, 2000);
    }

    showFilterResults(visible, total) {
        if (visible < total) {
            const message = `Showing ${visible} of ${total} metrics based on your selections`;
            this.showSelectionFeedback('Filter', message, true);
        }
    }

    getActiveSelections() {
        const result = {};
        Object.entries(this.selections).forEach(([type, selections]) => {
            result[type] = Array.from(selections);
        });
        return result;
    }
}

// Global functions for HTML onclick handlers
function toggleDropdown(dropdownId) {
    if (window.multiSelectNav) {
        window.multiSelectNav.toggleDropdown(dropdownId);
    }
}

function applyFilters() {
    if (window.multiSelectNav) {
        window.multiSelectNav.applyFiltering();
    }
}

function clearAllFilters() {
    if (window.multiSelectNav) {
        window.multiSelectNav.clearAllSelections();
    }
}

function toggleSelection(type, id, name) {
    if (window.multiSelectNav) {
        window.multiSelectNav.toggleSelection(type, id, name);
    }
}

function toggleSelectAll(type) {
    if (window.multiSelectNav) {
        window.multiSelectNav.toggleSelectAll(type);
    }
}

// Initialize multi-select navigation
let multiSelectNav;

document.addEventListener('DOMContentLoaded', function() {
    multiSelectNav = new MultiSelectNavigation();
    window.multiSelectNav = multiSelectNav;
});

// Export for global access
window.MultiSelectNavigation = MultiSelectNavigation;
