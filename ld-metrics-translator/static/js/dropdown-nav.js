// Dropdown Navigation Functionality
class DropdownNavigation {
    constructor() {
        this.selectedCategories = new Set();
        this.selectedOutcomes = new Set();
        this.selectedMetrics = new Set();
        this.selectedNeuroscience = new Set();
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Close dropdowns when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.dropdown-nav-item')) {
                this.closeAllDropdowns();
            }
        });

        // Prevent dropdown from closing when clicking inside
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
        const button = dropdown.previousElementSibling;
        
        // Close other dropdowns
        this.closeAllDropdowns(dropdownId);
        
        if (dropdown.classList.contains('show')) {
            this.closeDropdown(dropdownId);
        } else {
            this.openDropdown(dropdownId);
        }
    }

    openDropdown(dropdownId) {
        const dropdown = document.getElementById(dropdownId);
        const button = dropdown.previousElementSibling;
        
        dropdown.classList.add('show');
        button.classList.add('dropdown-open');
        this.activeDropdown = dropdownId;
    }

    closeDropdown(dropdownId) {
        const dropdown = document.getElementById(dropdownId);
        const button = dropdown.previousElementSibling;
        
        dropdown.classList.remove('show');
        button.classList.remove('dropdown-open');
        
        if (this.activeDropdown === dropdownId) {
            this.activeDropdown = null;
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
        
        if (!except) {
            this.activeDropdown = null;
        }
    }

    updateButtonText(buttonSelector, newText) {
        const button = document.querySelector(buttonSelector);
        if (button) {
            const textElement = button.querySelector('.tab-text');
            if (textElement) {
                textElement.textContent = `[${newText}]`;
            }
        }
    }

    selectMetricCategory(id, name) {
        this.selectedItems.category = { id, name };
        this.updateButtonText('[onclick*="categories-dropdown"]', name);
        this.closeDropdown('categories-dropdown');
        
        // Filter metrics based on selected category
        this.filterMetrics();
        
        // Show success message
        this.showSelectionFeedback('Metric Category', name);
    }

    selectOutcome(id, name) {
        this.selectedItems.outcome = { id, name };
        this.updateButtonText('[onclick*="outcomes-dropdown"]', name);
        this.closeDropdown('outcomes-dropdown');
        
        // Show success message
        this.showSelectionFeedback('L&D Outcome', name);
    }

    selectMetric(id, name) {
        this.selectedItems.metric = { id, name };
        this.updateButtonText('[onclick*="metrics-dropdown"]', name);
        this.closeDropdown('metrics-dropdown');
        
        // Show metric details
        this.showMetricDetails(id, name);
        
        // Show success message
        this.showSelectionFeedback('Metric', name);
    }

    selectNeuroscienceMetric(id, name) {
        this.selectedItems.neuroscience = { id, name };
        this.updateButtonText('[onclick*="neuroscience-dropdown"]', name);
        this.closeDropdown('neuroscience-dropdown');
        
        // Show neuroscience details
        this.showNeuroscienceDetails(id, name);
        
        // Show success message
        this.showSelectionFeedback('Neuroscience Concept', name);
    }

    filterMetrics() {
        if (!this.selectedItems.category) return;
        
        const metricsDropdown = document.getElementById('metrics-dropdown');
        const neuroscienceDropdown = document.getElementById('neuroscience-dropdown');
        
        // This would typically filter the dropdown items based on the selected category
        // For now, we'll just update the display
        console.log('Filtering metrics for category:', this.selectedItems.category.name);
    }

    showMetricDetails(id, name) {
        // Scroll to the metrics section or show details
        const metricsSection = document.querySelector('.metrics-grid');
        if (metricsSection) {
            metricsSection.scrollIntoView({ behavior: 'smooth' });
        }
        
        // Highlight the selected metric if it exists in the grid
        const metricCards = document.querySelectorAll('.metric-card');
        metricCards.forEach(card => {
            card.classList.remove('highlighted');
            if (card.dataset.metricId === id) {
                card.classList.add('highlighted');
            }
        });
    }

    showNeuroscienceDetails(id, name) {
        // Similar to showMetricDetails but for neuroscience concepts
        console.log('Showing neuroscience details for:', name);
    }

    showSelectionFeedback(type, name) {
        // Create a temporary feedback message
        const feedback = document.createElement('div');
        feedback.className = 'selection-feedback';
        feedback.innerHTML = `
            <div class="feedback-content">
                <span class="feedback-icon">✓</span>
                <span class="feedback-text">Selected ${type}: <strong>${name}</strong></span>
            </div>
        `;
        
        document.body.appendChild(feedback);
        
        // Show the feedback
        setTimeout(() => feedback.classList.add('show'), 100);
        
        // Remove after 3 seconds
        setTimeout(() => {
            feedback.classList.remove('show');
            setTimeout(() => feedback.remove(), 300);
        }, 3000);
    }

    getSelectedItems() {
        return this.selectedItems;
    }

    clearSelections() {
        this.selectedItems = {
            category: null,
            outcome: null,
            metric: null,
            neuroscience: null
        };
        
        // Reset button texts
        this.updateButtonText('[onclick*="categories-dropdown"]', 'Metric Categories');
        this.updateButtonText('[onclick*="outcomes-dropdown"]', 'L & D Outcomes');
        this.updateButtonText('[onclick*="metrics-dropdown"]', 'Find Metrics');
        this.updateButtonText('[onclick*="neuroscience-dropdown"]', 'Explore Categories');
    }
}

// Initialize dropdown navigation
let dropdownNav;

document.addEventListener('DOMContentLoaded', function() {
    dropdownNav = new DropdownNavigation();
});

// Global functions for onclick handlers
function toggleDropdown(dropdownId) {
    if (dropdownNav) {
        dropdownNav.toggleDropdown(dropdownId);
    }
}

function selectMetricCategory(id, name) {
    if (dropdownNav) {
        dropdownNav.selectMetricCategory(id, name);
    }
}

function selectOutcome(id, name) {
    if (dropdownNav) {
        dropdownNav.selectOutcome(id, name);
    }
}

function selectMetric(id, name) {
    if (dropdownNav) {
        dropdownNav.selectMetric(id, name);
    }
}

function selectNeuroscienceMetric(id, name) {
    if (dropdownNav) {
        dropdownNav.selectNeuroscienceMetric(id, name);
    }
}
