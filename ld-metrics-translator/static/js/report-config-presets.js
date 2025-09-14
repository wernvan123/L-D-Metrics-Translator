// Report Configuration Presets and Validation
// Enhances the streamlined sidebar with preset management and form validation

class ReportConfigPresets {
    constructor() {
        this.presets = new Map();
        this.currentConfig = null;
        this.validationRules = {
            title: {
                required: true,
                minLength: 3,
                maxLength: 100,
                pattern: /^[a-zA-Z0-9\s\-_.,()]+$/
            },
            reportType: {
                required: true,
                allowedValues: ['basic', 'comprehensive']
            },
            minMetrics: 1,
            maxMetrics: 50
        };
        
        this.init();
    }
    
    init() {
        this.loadPresetsFromStorage();
        this.setupEventListeners();
        console.log('Report Config Presets initialized');
    }
    
    loadPresetsFromStorage() {
        try {
            const stored = localStorage.getItem('reportConfigPresets');
            if (stored) {
                const presetArray = JSON.parse(stored);
                presetArray.forEach(preset => {
                    this.presets.set(preset.id, preset);
                });
                console.log(`Loaded ${this.presets.size} report presets from storage`);
            }
        } catch (error) {
            console.error('Error loading presets from storage:', error);
        }
    }
    
    savePresetsToStorage() {
        try {
            const presetArray = Array.from(this.presets.values());
            localStorage.setItem('reportConfigPresets', JSON.stringify(presetArray));
        } catch (error) {
            console.error('Error saving presets to storage:', error);
        }
    }
    
    setupEventListeners() {
        // Listen for report configuration modal opening
        document.addEventListener('reportConfigModalOpened', () => {
            this.enhanceReportConfigModal();
        });
        
        // Listen for form changes for real-time validation
        document.addEventListener('change', (e) => {
            if (e.target.closest('.report-config-form')) {
                this.validateForm();
            }
        });
        
        document.addEventListener('input', (e) => {
            if (e.target.closest('.report-config-form')) {
                this.validateForm();
            }
        });
    }
    
    enhanceReportConfigModal() {
        const modal = document.querySelector('.report-config-modal');
        if (!modal) return;
        
        // Add presets section if not already added
        if (!modal.querySelector('.config-presets-section')) {
            this.addPresetsSection(modal);
        }
        
        // Add validation indicators
        this.addValidationIndicators(modal);
        
        // Setup form validation
        this.setupFormValidation(modal);
    }
    
    addPresetsSection(modal) {
        const form = modal.querySelector('.report-config-form');
        if (!form) return;
        
        const presetsSection = document.createElement('div');
        presetsSection.className = 'config-presets-section';
        presetsSection.innerHTML = `
            <div class="config-section">
                <h3>
                    <span class="section-icon">⚡</span>
                    Quick Presets
                </h3>
                <div class="presets-container">
                    <div class="preset-buttons" id="preset-buttons">
                        ${this.renderPresetButtons()}
                    </div>
                    <div class="preset-actions">
                        <button type="button" class="btn btn-sm btn-outline preset-save-btn" id="save-preset-btn">
                            💾 Save Current as Preset
                        </button>
                        <button type="button" class="btn btn-sm btn-outline preset-manage-btn" id="manage-presets-btn">
                            ⚙️ Manage Presets
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Insert at the beginning of the form
        form.insertBefore(presetsSection, form.firstChild);
        
        // Setup preset button handlers
        this.setupPresetHandlers();
    }
    
    renderPresetButtons() {
        if (this.presets.size === 0) {
            return `
                <div class="no-presets">
                    <span class="no-presets-icon">📝</span>
                    <span class="no-presets-text">No presets saved yet</span>
                </div>
            `;
        }
        
        return Array.from(this.presets.values()).map(preset => `
            <button type="button" class="preset-btn" data-preset-id="${preset.id}">
                <span class="preset-icon">${preset.icon || '📊'}</span>
                <span class="preset-name">${preset.name}</span>
                <span class="preset-type">${preset.config.reportType}</span>
            </button>
        `).join('');
    }
    
    setupPresetHandlers() {
        // Preset button clicks
        document.addEventListener('click', (e) => {
            if (e.target.closest('.preset-btn')) {
                const presetId = e.target.closest('.preset-btn').dataset.presetId;
                this.applyPreset(presetId);
            }
        });
        
        // Save preset button
        const saveBtn = document.getElementById('save-preset-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.showSavePresetDialog());
        }
        
        // Manage presets button
        const manageBtn = document.getElementById('manage-presets-btn');
        if (manageBtn) {
            manageBtn.addEventListener('click', () => this.showManagePresetsDialog());
        }
    }
    
    addValidationIndicators(modal) {
        const form = modal.querySelector('.report-config-form');
        if (!form) return;
        
        // Add validation summary section
        const validationSummary = document.createElement('div');
        validationSummary.className = 'validation-summary';
        validationSummary.id = 'validation-summary';
        validationSummary.style.display = 'none';
        
        form.appendChild(validationSummary);
        
        // Add validation indicators to form fields
        const titleInput = form.querySelector('#report-title');
        if (titleInput) {
            this.addFieldValidation(titleInput, 'title');
        }
        
        const reportTypeInputs = form.querySelectorAll('input[name="reportType"]');
        if (reportTypeInputs.length > 0) {
            this.addFieldValidation(reportTypeInputs[0].closest('.report-type-selector'), 'reportType');
        }
    }
    
    addFieldValidation(field, fieldName) {
        const wrapper = document.createElement('div');
        wrapper.className = 'field-validation-wrapper';
        
        field.parentNode.insertBefore(wrapper, field);
        wrapper.appendChild(field);
        
        const indicator = document.createElement('div');
        indicator.className = 'validation-indicator';
        indicator.id = `${fieldName}-validation`;
        wrapper.appendChild(indicator);
    }
    
    setupFormValidation(modal) {
        const form = modal.querySelector('.report-config-form');
        if (!form) return;
        
        // Override form submission to include validation
        const generateBtn = form.querySelector('.btn-primary');
        if (generateBtn) {
            generateBtn.addEventListener('click', (e) => {
                if (!this.validateForm()) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.showValidationErrors();
                }
            });
        }
    }
    
    validateForm() {
        const form = document.querySelector('.report-config-form');
        if (!form) return false;
        
        const errors = [];
        let isValid = true;
        
        // Validate title
        const titleInput = form.querySelector('#report-title');
        if (titleInput) {
            const titleErrors = this.validateField('title', titleInput.value);
            if (titleErrors.length > 0) {
                errors.push(...titleErrors);
                isValid = false;
                this.showFieldError('title', titleErrors[0]);
            } else {
                this.showFieldSuccess('title');
            }
        }
        
        // Validate report type
        const reportTypeInput = form.querySelector('input[name="reportType"]:checked');
        if (!reportTypeInput) {
            errors.push('Please select a report type');
            isValid = false;
            this.showFieldError('reportType', 'Please select a report type');
        } else {
            this.showFieldSuccess('reportType');
        }
        
        // Validate metric count
        const metricCount = window.streamlinedSidebar ? window.streamlinedSidebar.selectedMetrics.size : 0;
        if (metricCount < this.validationRules.minMetrics) {
            errors.push(`Please select at least ${this.validationRules.minMetrics} metric(s)`);
            isValid = false;
        } else if (metricCount > this.validationRules.maxMetrics) {
            errors.push(`Please select no more than ${this.validationRules.maxMetrics} metrics`);
            isValid = false;
        }
        
        // Update validation summary
        this.updateValidationSummary(errors);
        
        return isValid;
    }
    
    validateField(fieldName, value) {
        const rules = this.validationRules[fieldName];
        const errors = [];
        
        if (rules.required && (!value || value.trim() === '')) {
            errors.push(`${fieldName} is required`);
            return errors;
        }
        
        if (value && rules.minLength && value.length < rules.minLength) {
            errors.push(`${fieldName} must be at least ${rules.minLength} characters`);
        }
        
        if (value && rules.maxLength && value.length > rules.maxLength) {
            errors.push(`${fieldName} must be no more than ${rules.maxLength} characters`);
        }
        
        if (value && rules.pattern && !rules.pattern.test(value)) {
            errors.push(`${fieldName} contains invalid characters`);
        }
        
        if (rules.allowedValues && !rules.allowedValues.includes(value)) {
            errors.push(`${fieldName} must be one of: ${rules.allowedValues.join(', ')}`);
        }
        
        return errors;
    }
    
    showFieldError(fieldName, message) {
        const indicator = document.getElementById(`${fieldName}-validation`);
        if (indicator) {
            indicator.className = 'validation-indicator error';
            indicator.innerHTML = `<span class="error-icon">⚠️</span><span class="error-text">${message}</span>`;
        }
    }
    
    showFieldSuccess(fieldName) {
        const indicator = document.getElementById(`${fieldName}-validation`);
        if (indicator) {
            indicator.className = 'validation-indicator success';
            indicator.innerHTML = `<span class="success-icon">✓</span>`;
        }
    }
    
    updateValidationSummary(errors) {
        const summary = document.getElementById('validation-summary');
        if (!summary) return;
        
        if (errors.length === 0) {
            summary.style.display = 'none';
        } else {
            summary.style.display = 'block';
            summary.className = 'validation-summary error';
            summary.innerHTML = `
                <div class="validation-header">
                    <span class="validation-icon">⚠️</span>
                    <span class="validation-title">Please fix the following issues:</span>
                </div>
                <ul class="validation-errors">
                    ${errors.map(error => `<li>${error}</li>`).join('')}
                </ul>
            `;
        }
    }
    
    showValidationErrors() {
        const summary = document.getElementById('validation-summary');
        if (summary) {
            summary.scrollIntoView({ behavior: 'smooth', block: 'center' });
            summary.classList.add('highlight');
            setTimeout(() => summary.classList.remove('highlight'), 2000);
        }
    }
    
    applyPreset(presetId) {
        const preset = this.presets.get(presetId);
        if (!preset) return;
        
        const form = document.querySelector('.report-config-form');
        if (!form) return;
        
        // Apply title
        const titleInput = form.querySelector('#report-title');
        if (titleInput) {
            titleInput.value = preset.config.title;
        }
        
        // Apply report type
        const reportTypeInput = form.querySelector(`input[name="reportType"][value="${preset.config.reportType}"]`);
        if (reportTypeInput) {
            reportTypeInput.checked = true;
        }
        
        // Apply other settings
        if (preset.config.includeAI !== undefined) {
            const aiCheckbox = form.querySelector('#include-ai');
            if (aiCheckbox) {
                aiCheckbox.checked = preset.config.includeAI;
            }
        }
        
        // Validate after applying
        this.validateForm();
        
        // Show notification
        if (window.showNotification) {
            window.showNotification(`Applied preset: ${preset.name}`, 'success');
        }
    }
    
    showSavePresetDialog() {
        const form = document.querySelector('.report-config-form');
        if (!form) return;
        
        // Get current configuration
        const config = this.getCurrentConfig();
        if (!config) return;
        
        // Create save dialog
        const dialog = document.createElement('div');
        dialog.className = 'preset-save-dialog modal-overlay';
        dialog.innerHTML = `
            <div class="modal-content preset-dialog-content">
                <div class="modal-header">
                    <h3>Save Report Preset</h3>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="preset-form">
                        <div class="form-group">
                            <label for="preset-name">Preset Name</label>
                            <input type="text" id="preset-name" class="form-control" 
                                   placeholder="e.g., Weekly Team Report" maxlength="50">
                        </div>
                        <div class="form-group">
                            <label for="preset-icon">Icon (emoji)</label>
                            <input type="text" id="preset-icon" class="form-control" 
                                   placeholder="📊" maxlength="2" value="📊">
                        </div>
                        <div class="preset-preview">
                            <h4>Configuration Preview:</h4>
                            <ul>
                                <li><strong>Title:</strong> ${config.title}</li>
                                <li><strong>Type:</strong> ${config.reportType}</li>
                                <li><strong>Include AI:</strong> ${config.includeAI ? 'Yes' : 'No'}</li>
                            </ul>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
                    <button class="btn btn-primary" id="confirm-save-preset">Save Preset</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(dialog);
        
        // Focus on name input
        const nameInput = dialog.querySelector('#preset-name');
        nameInput.focus();
        
        // Handle save
        dialog.querySelector('#confirm-save-preset').addEventListener('click', () => {
            const name = nameInput.value.trim();
            const icon = dialog.querySelector('#preset-icon').value.trim() || '📊';
            
            if (!name) {
                nameInput.focus();
                return;
            }
            
            this.savePreset(name, icon, config);
            dialog.remove();
        });
    }
    
    getCurrentConfig() {
        const form = document.querySelector('.report-config-form');
        if (!form) return null;
        
        const titleInput = form.querySelector('#report-title');
        const reportTypeInput = form.querySelector('input[name="reportType"]:checked');
        const aiCheckbox = form.querySelector('#include-ai');
        
        return {
            title: titleInput ? titleInput.value : '',
            reportType: reportTypeInput ? reportTypeInput.value : 'basic',
            includeAI: aiCheckbox ? aiCheckbox.checked : false
        };
    }
    
    savePreset(name, icon, config) {
        const preset = {
            id: Date.now().toString(),
            name: name,
            icon: icon,
            config: config,
            createdAt: new Date().toISOString()
        };
        
        this.presets.set(preset.id, preset);
        this.savePresetsToStorage();
        this.refreshPresetButtons();
        
        if (window.showNotification) {
            window.showNotification(`Preset "${name}" saved successfully`, 'success');
        }
    }
    
    refreshPresetButtons() {
        const container = document.getElementById('preset-buttons');
        if (container) {
            container.innerHTML = this.renderPresetButtons();
        }
    }
    
    showManagePresetsDialog() {
        const dialog = document.createElement('div');
        dialog.className = 'preset-manage-dialog modal-overlay';
        dialog.innerHTML = `
            <div class="modal-content preset-dialog-content">
                <div class="modal-header">
                    <h3>Manage Presets</h3>
                    <button class="modal-close" onclick="this.closest('.modal-overlay').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="presets-list">
                        ${this.renderPresetsList()}
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Close</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(dialog);
        this.setupManageHandlers(dialog);
    }
    
    renderPresetsList() {
        if (this.presets.size === 0) {
            return '<div class="no-presets">No presets saved yet.</div>';
        }
        
        return Array.from(this.presets.values()).map(preset => `
            <div class="preset-item" data-preset-id="${preset.id}">
                <div class="preset-info">
                    <span class="preset-icon">${preset.icon}</span>
                    <div class="preset-details">
                        <div class="preset-name">${preset.name}</div>
                        <div class="preset-meta">${preset.config.reportType} • Created ${new Date(preset.createdAt).toLocaleDateString()}</div>
                    </div>
                </div>
                <div class="preset-actions">
                    <button class="btn btn-sm btn-outline edit-preset-btn">Edit</button>
                    <button class="btn btn-sm btn-danger delete-preset-btn">Delete</button>
                </div>
            </div>
        `).join('');
    }
    
    setupManageHandlers(dialog) {
        dialog.addEventListener('click', (e) => {
            const presetItem = e.target.closest('.preset-item');
            if (!presetItem) return;
            
            const presetId = presetItem.dataset.presetId;
            
            if (e.target.classList.contains('delete-preset-btn')) {
                this.deletePreset(presetId);
                presetItem.remove();
            }
        });
    }
    
    deletePreset(presetId) {
        this.presets.delete(presetId);
        this.savePresetsToStorage();
        this.refreshPresetButtons();
        
        if (window.showNotification) {
            window.showNotification('Preset deleted', 'info');
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.reportConfigPresets = new ReportConfigPresets();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ReportConfigPresets;
}
