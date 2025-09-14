// Streamlined Sidebar Manager
// Manages the two-step process: Select → Configure → Generate

class StreamlinedSidebar {
    constructor() {
        this.selectedMetrics = new Set();
        this.selectedFrameworks = new Set();
        this.selectedOutcomes = new Set();
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateSidebarDisplay();
        console.log('Streamlined Sidebar initialized');
    }

    bindEvents() {
        // Bind "Next: Configure Report" button
        const proceedBtn = document.getElementById('plan-proceed-to-report');
        if (proceedBtn) {
            proceedBtn.addEventListener('click', () => {
                this.proceedToReportConfiguration();
            });
        }

        // Bind clear selections button
        const clearBtn = document.getElementById('plan-clear-selections');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearAllSelections();
            });
        }

        // Bind save selections button
        const saveBtn = document.getElementById('plan-save-selections');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveSelections();
            });
        }

        // Listen for metric selection events from other components
        document.addEventListener('metricSelected', (e) => {
            this.addMetric(e.detail);
        });

        document.addEventListener('metricDeselected', (e) => {
            this.removeMetric(e.detail);
        });

        document.addEventListener('frameworkSelected', (e) => {
            this.addFramework(e.detail);
        });

        document.addEventListener('outcomeSelected', (e) => {
            this.addOutcome(e.detail);
        });
    }

    addMetric(metric) {
        this.selectedMetrics.add(metric);
        this.updateSidebarDisplay();
        this.dispatchSelectionChange();
    }

    removeMetric(metricId) {
        // Find and remove metric by ID
        for (let metric of this.selectedMetrics) {
            if (metric.id === metricId) {
                this.selectedMetrics.delete(metric);
                break;
            }
        }
        this.updateSidebarDisplay();
        this.dispatchSelectionChange();
    }

    addFramework(framework) {
        this.selectedFrameworks.add(framework);
        this.updateSidebarDisplay();
    }

    addOutcome(outcome) {
        this.selectedOutcomes.add(outcome);
        this.updateSidebarDisplay();
    }

    clearAllSelections() {
        this.selectedMetrics.clear();
        this.selectedFrameworks.clear();
        this.selectedOutcomes.clear();
        this.updateSidebarDisplay();
        this.dispatchSelectionChange();
        
        // Clear visual selections in the main interface
        document.querySelectorAll('.metric-card.selected').forEach(card => {
            card.classList.remove('selected');
        });

        if (window.showNotification) {
            window.showNotification('All selections cleared', 'info');
        }
    }

    saveSelections() {
        const selectionData = {
            metrics: Array.from(this.selectedMetrics),
            frameworks: Array.from(this.selectedFrameworks),
            outcomes: Array.from(this.selectedOutcomes),
            timestamp: new Date().toISOString()
        };

        // Save to localStorage
        localStorage.setItem('savedSelections', JSON.stringify(selectionData));

        if (window.showNotification) {
            window.showNotification('Selections saved successfully', 'success');
        }
    }

    updateSidebarDisplay() {
        this.updateSelectionStats();
        this.updateSelectedItems();
        this.updateNextStepSection();
        this.updateActionButtons();
    }

    updateSelectionStats() {
        const frameworksCount = document.getElementById('plan-frameworks-count');
        const metricsCount = document.getElementById('plan-metrics-count');
        const outcomesCount = document.getElementById('plan-outcomes-count');

        if (frameworksCount) frameworksCount.textContent = this.selectedFrameworks.size;
        if (metricsCount) metricsCount.textContent = this.selectedMetrics.size;
        if (outcomesCount) outcomesCount.textContent = this.selectedOutcomes.size;
    }

    updateSelectedItems() {
        const selectedItemsContainer = document.getElementById('plan-selected-items');
        if (!selectedItemsContainer) return;

        const totalSelections = this.selectedMetrics.size + this.selectedFrameworks.size + this.selectedOutcomes.size;

        if (totalSelections === 0) {
            selectedItemsContainer.innerHTML = '<p class="no-selection">No items selected yet</p>';
            return;
        }

        let itemsHTML = '';

        // Add frameworks
        this.selectedFrameworks.forEach(framework => {
            itemsHTML += this.createSelectedItemHTML(framework.name, 'Framework', framework.id, 'framework');
        });

        // Add outcomes
        this.selectedOutcomes.forEach(outcome => {
            itemsHTML += this.createSelectedItemHTML(outcome.name, 'Outcome', outcome.id, 'outcome');
        });

        // Add metrics
        this.selectedMetrics.forEach(metric => {
            itemsHTML += this.createSelectedItemHTML(metric.name, 'Metric', metric.id, 'metric');
        });

        selectedItemsContainer.innerHTML = itemsHTML;

        // Bind remove buttons
        selectedItemsContainer.querySelectorAll('.selected-item-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const type = e.target.dataset.type;
                const id = parseInt(e.target.dataset.id);
                this.removeSelectedItem(type, id);
            });
        });
    }

    createSelectedItemHTML(name, type, id, dataType) {
        const truncatedName = name.length > 25 ? name.substring(0, 25) + '...' : name;
        return `
            <div class="selected-item">
                <span class="selected-item-name" title="${name}">${truncatedName}</span>
                <span class="selected-item-type">${type}</span>
                <button class="selected-item-remove" data-type="${dataType}" data-id="${id}" title="Remove ${name}">
                    ×
                </button>
            </div>
        `;
    }

    removeSelectedItem(type, id) {
        switch (type) {
            case 'metric':
                this.removeMetric(id);
                break;
            case 'framework':
                this.selectedFrameworks.forEach(framework => {
                    if (framework.id === id) {
                        this.selectedFrameworks.delete(framework);
                    }
                });
                break;
            case 'outcome':
                this.selectedOutcomes.forEach(outcome => {
                    if (outcome.id === id) {
                        this.selectedOutcomes.delete(outcome);
                    }
                });
                break;
        }
        this.updateSidebarDisplay();
    }

    updateNextStepSection() {
        const nextStepContent = document.getElementById('plan-next-step');
        const nextStepActions = document.getElementById('plan-next-step-actions');
        const selectionPreview = document.getElementById('plan-selection-preview');

        const hasSelections = this.selectedMetrics.size > 0;

        if (hasSelections) {
            // Show next step actions
            if (nextStepContent) nextStepContent.style.display = 'none';
            if (nextStepActions) nextStepActions.style.display = 'block';

            // Update preview text
            if (selectionPreview) {
                const metricCount = this.selectedMetrics.size;
                const frameworkCount = this.selectedFrameworks.size;
                let previewText = `${metricCount} metric${metricCount !== 1 ? 's' : ''}`;
                
                if (frameworkCount > 0) {
                    previewText += `, ${frameworkCount} framework${frameworkCount !== 1 ? 's' : ''}`;
                }
                
                selectionPreview.textContent = previewText;
            }
        } else {
            // Show empty state
            if (nextStepContent) nextStepContent.style.display = 'block';
            if (nextStepActions) nextStepActions.style.display = 'none';
        }
    }

    updateActionButtons() {
        const clearBtn = document.getElementById('plan-clear-selections');
        const saveBtn = document.getElementById('plan-save-selections');

        const hasSelections = this.selectedMetrics.size > 0 || this.selectedFrameworks.size > 0 || this.selectedOutcomes.size > 0;

        if (clearBtn) clearBtn.style.display = hasSelections ? 'block' : 'none';
        if (saveBtn) saveBtn.style.display = hasSelections ? 'block' : 'none';
    }

    proceedToReportConfiguration() {
        if (this.selectedMetrics.size === 0) {
            if (window.showNotification) {
                window.showNotification('Please select at least one metric before proceeding', 'error');
            }
            return;
        }

        // Create report configuration modal/page
        this.showReportConfigurationModal();
    }

    showReportConfigurationModal() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay report-config-modal';
        modal.innerHTML = `
            <div class="modal-content report-config-content">
                <div class="modal-header">
                    <h2>Configure Your Report</h2>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">&times;</button>
                </div>
                <div class="modal-body">
                    <form class="report-config-form" id="report-config-form">
                        <!-- Configuration Summary -->
                        <div class="config-summary">
                            <h3>
                                <span class="section-icon">📋</span>
                                Current Selection Summary
                            </h3>
                            <div class="summary-stats">
                                <div class="summary-stat">
                                    <span class="stat-number">${this.selectedMetrics.size}</span>
                                    <span class="stat-label">Metrics</span>
                                </div>
                                <div class="summary-stat">
                                    <span class="stat-number">${this.selectedFrameworks.size}</span>
                                    <span class="stat-label">Frameworks</span>
                                </div>
                                <div class="summary-stat">
                                    <span class="stat-number">${this.selectedOutcomes.size}</span>
                                    <span class="stat-label">Outcomes</span>
                                </div>
                                <div class="summary-stat">
                                    <span class="stat-number">~${Math.max(5, this.selectedMetrics.size * 2)}</span>
                                    <span class="stat-label">Est. Pages</span>
                                </div>
                            </div>
                        </div>

                        <div class="config-section">
                            <h3>📝 Report Details</h3>
                            <div class="form-group">
                                <label for="report-title">Report Title</label>
                                <input type="text" id="report-title" class="form-control" 
                                       placeholder="Enter report title (e.g., Q4 L&D Metrics Analysis)"
                                       maxlength="200">
                            </div>
                            
                            <div class="form-group">
                                <label for="report-type">Report Type</label>
                                <div class="report-type-selector">
                                    <div class="report-type-option">
                                        <input type="radio" id="basic-report" name="reportType" value="basic" checked>
                                        <label for="basic-report">
                                    <div class="option-header">
                                        <span class="option-icon">📄</span>
                                        <span class="option-title">Basic Report</span>
                                    </div>
                                    <div class="option-description">
                                        <p>Essential metrics and analysis</p>
                                        <span class="option-pages">5-10 pages</span>
                                    </div>
                                </label>
                            </div>
                            
                            <div class="report-type-option">
                                <input type="radio" id="comprehensive-report" name="reportType" value="comprehensive">
                                <label for="comprehensive-report">
                                    <div class="option-header">
                                        <span class="option-icon">📋</span>
                                        <span class="option-title">Comprehensive Report</span>
                                    </div>
                                    <div class="option-description">
                                        <p>Detailed analysis with AI insights</p>
                                        <span class="option-pages">8-20 pages</span>
                                    </div>
                                </label>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="config-section">
                    <h3>⚡ Generation Options</h3>
                    <div class="form-group">
                        <label class="checkbox-label">
                            <input type="checkbox" id="include-ai" checked>
                            Include AI recommendations
                        </label>
                    </div>
                    <div class="form-group">
                        <label class="checkbox-label">
                            <input type="checkbox" id="include-charts">
                            Generate charts and visualizations
                        </label>
                    </div>
                </div>

                        <div class="config-actions">
                            <button type="button" class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                            <button type="button" id="generate-report-btn" class="btn btn-primary btn-lg">
                                <span class="btn-icon">🚀</span>
                                Generate Report
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Dispatch event for presets integration
        document.dispatchEvent(new CustomEvent('reportConfigModalOpened'));
        
        // Setup event handlers
        this.setupReportConfigHandlers(modal);
    }

    setupReportConfigHandlers(modal) {
        const generateBtn = modal.querySelector('#generate-report-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => {
                this.generateReport();
            });
        }
    }

    generateReport() {
        // Get form data
        const form = document.getElementById('report-config-form');
        if (!form) return;

        const title = form.querySelector('#report-title')?.value || 'L&D Metrics Report';
        const reportType = form.querySelector('input[name="reportType"]:checked')?.value || 'basic';
        const includeAI = form.querySelector('#include-ai')?.checked || false;
        const includeCharts = form.querySelector('#include-charts')?.checked || false;

        // Validate form using presets validation if available
        if (window.reportConfigPresets && !window.reportConfigPresets.validateForm()) {
            return; // Validation failed, errors already shown
        }

        // Prepare report data
        const reportData = {
            title: title,
            type: reportType,
            selectedMetrics: Array.from(this.selectedMetrics),
            selectedFrameworks: Array.from(this.selectedFrameworks),
            selectedOutcomes: Array.from(this.selectedOutcomes),
            options: {
                includeAI: includeAI,
                includeCharts: includeCharts
            }
        };

        // Close modal
        document.querySelector('.report-config-modal')?.remove();

        // Integrate with existing report generator
        if (window.dynamicReportGenerator) {
            window.dynamicReportGenerator.generateReport(reportData);
        } else {
            // Fallback: show success message
            if (window.showNotification) {
                window.showNotification(`Report "${title}" generation started`, 'success');
            }
        }

        // Clear selections after successful generation
        this.clearAllSelections();
    }

    // Public API methods
    getSelectedMetrics() {
        return Array.from(this.selectedMetrics);
    }

    getSelectedFrameworks() {
        return Array.from(this.selectedFrameworks);
    }

    getSelectedOutcomes() {
        return Array.from(this.selectedOutcomes);
    }

    hasSelections() {
        return this.selectedMetrics.size > 0 || this.selectedFrameworks.size > 0 || this.selectedOutcomes.size > 0;
    }
    
    dispatchSelectionChange() {
        // Notify other components about selection changes
        const event = new CustomEvent('selectionChanged', {
            detail: {
                metrics: Array.from(this.selectedMetrics),
                frameworks: Array.from(this.selectedFrameworks),
                outcomes: Array.from(this.selectedOutcomes)
            }
        });
        document.dispatchEvent(event);
    }
}

// Initialize the streamlined sidebar
let streamlinedSidebar;
document.addEventListener('DOMContentLoaded', () => {
    streamlinedSidebar = new StreamlinedSidebar();
    
    // Make it globally available
    window.streamlinedSidebar = streamlinedSidebar;
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StreamlinedSidebar;
}
