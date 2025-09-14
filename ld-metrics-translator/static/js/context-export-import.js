/**
 * Context Export/Import Component
 * Handles exporting and importing user context data
 */

class ContextExportImport {
    constructor() {
        this.exportModal = null;
        this.importModal = null;
        this.init();
    }

    init() {
        this.createExportModal();
        this.createImportModal();
        this.setupEventListeners();
    }

    createExportModal() {
        this.exportModal = document.createElement('div');
        this.exportModal.id = 'context-export-modal';
        this.exportModal.className = 'context-modal hidden';
        this.exportModal.innerHTML = `
            <div class="modal-overlay" onclick="contextExportImport.hideExportModal()"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>
                        <i class="fas fa-download"></i>
                        Export Context Data
                    </h3>
                    <button class="modal-close" onclick="contextExportImport.hideExportModal()">×</button>
                </div>
                
                <div class="modal-body">
                    <div class="export-intro">
                        <p>Export your current session data including metrics, preferences, and search history.</p>
                    </div>
                    
                    <div class="export-options">
                        <h4>Export Options</h4>
                        <div class="option-group">
                            <label>
                                <input type="checkbox" id="export-metrics" checked>
                                Selected Metrics (<span id="metrics-count-export">0</span>)
                            </label>
                        </div>
                        <div class="option-group">
                            <label>
                                <input type="checkbox" id="export-preferences" checked>
                                User Preferences
                            </label>
                        </div>
                        <div class="option-group">
                            <label>
                                <input type="checkbox" id="export-search-history" checked>
                                Search History
                            </label>
                        </div>
                        <div class="option-group">
                            <label>
                                <input type="checkbox" id="export-recommendations">
                                AI Recommendations
                            </label>
                        </div>
                        <div class="option-group">
                            <label>
                                <input type="checkbox" id="export-session-data">
                                Session Metadata
                            </label>
                        </div>
                    </div>
                    
                    <div class="export-format">
                        <h4>Export Format</h4>
                        <div class="format-options">
                            <label>
                                <input type="radio" name="export-format" value="json" checked>
                                JSON (Recommended)
                            </label>
                            <label>
                                <input type="radio" name="export-format" value="csv">
                                CSV (Metrics only)
                            </label>
                            <label>
                                <input type="radio" name="export-format" value="txt">
                                Text Summary
                            </label>
                        </div>
                    </div>
                    
                    <div class="export-preview" id="export-preview" style="display: none;">
                        <h4>Export Preview</h4>
                        <pre id="export-preview-content"></pre>
                    </div>
                </div>
                
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="contextExportImport.previewExport()">
                        Preview
                    </button>
                    <button class="btn btn-primary" onclick="contextExportImport.performExport()">
                        <i class="fas fa-download"></i>
                        Export Data
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(this.exportModal);
    }

    createImportModal() {
        this.importModal = document.createElement('div');
        this.importModal.id = 'context-import-modal';
        this.importModal.className = 'context-modal hidden';
        this.importModal.innerHTML = `
            <div class="modal-overlay" onclick="contextExportImport.hideImportModal()"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>
                        <i class="fas fa-upload"></i>
                        Import Context Data
                    </h3>
                    <button class="modal-close" onclick="contextExportImport.hideImportModal()">×</button>
                </div>
                
                <div class="modal-body">
                    <div class="import-intro">
                        <p>Import previously exported context data to restore your session state.</p>
                    </div>
                    
                    <div class="import-methods">
                        <div class="import-method active" data-method="file">
                            <h4>
                                <i class="fas fa-file-upload"></i>
                                Upload File
                            </h4>
                            <div class="file-upload-area" id="file-upload-area">
                                <input type="file" id="context-file-input" accept=".json,.csv,.txt" style="display: none;">
                                <div class="upload-placeholder">
                                    <i class="fas fa-cloud-upload-alt"></i>
                                    <p>Click to select file or drag and drop</p>
                                    <small>Supports JSON, CSV, and TXT files</small>
                                </div>
                                <div class="file-info" id="file-info" style="display: none;">
                                    <div class="file-name"></div>
                                    <div class="file-size"></div>
                                    <button class="btn btn-sm btn-outline" onclick="contextExportImport.clearFile()">
                                        Remove
                                    </button>
                                </div>
                            </div>
                        </div>
                        
                        <div class="import-method" data-method="text">
                            <h4>
                                <i class="fas fa-paste"></i>
                                Paste Data
                            </h4>
                            <textarea id="import-text-data" 
                                     placeholder="Paste your exported context data here..."
                                     rows="8"></textarea>
                        </div>
                    </div>
                    
                    <div class="import-preview" id="import-preview" style="display: none;">
                        <h4>Import Preview</h4>
                        <div class="preview-summary" id="preview-summary"></div>
                        <div class="import-options">
                            <h5>Import Options</h5>
                            <div class="option-group">
                                <label>
                                    <input type="checkbox" id="import-merge" checked>
                                    Merge with existing data (unchecked = replace)
                                </label>
                            </div>
                            <div class="option-group">
                                <label>
                                    <input type="checkbox" id="import-backup" checked>
                                    Create backup of current data
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="contextExportImport.validateImport()">
                        Validate
                    </button>
                    <button class="btn btn-primary" onclick="contextExportImport.performImport()" disabled id="import-btn">
                        <i class="fas fa-upload"></i>
                        Import Data
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(this.importModal);
    }

    setupEventListeners() {
        // File upload handling
        const fileInput = document.getElementById('context-file-input');
        const uploadArea = document.getElementById('file-upload-area');

        if (fileInput && uploadArea) {
            fileInput.addEventListener('change', (e) => {
                this.handleFileSelect(e.target.files[0]);
            });

            uploadArea.addEventListener('click', () => {
                fileInput.click();
            });

            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('drag-over');
            });

            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('drag-over');
            });

            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('drag-over');
                this.handleFileSelect(e.dataTransfer.files[0]);
            });
        }

        // Import method switching
        document.addEventListener('click', (e) => {
            if (e.target.closest('.import-method')) {
                this.switchImportMethod(e.target.closest('.import-method').dataset.method);
            }
        });

        // Text area validation
        const importTextArea = document.getElementById('import-text-data');
        if (importTextArea) {
            importTextArea.addEventListener('input', () => {
                this.validateTextInput();
            });
        }
    }

    showExportModal() {
        this.updateExportCounts();
        this.exportModal.classList.remove('hidden');
        this.exportModal.classList.add('visible');
    }

    hideExportModal() {
        this.exportModal.classList.remove('visible');
        this.exportModal.classList.add('hidden');
    }

    showImportModal() {
        this.importModal.classList.remove('hidden');
        this.importModal.classList.add('visible');
    }

    hideImportModal() {
        this.importModal.classList.remove('visible');
        this.importModal.classList.add('hidden');
    }

    async updateExportCounts() {
        try {
            const metrics = await window.contextManager?.getSelectedMetrics() || [];
            const metricsCountEl = document.getElementById('metrics-count-export');
            if (metricsCountEl) {
                metricsCountEl.textContent = metrics.length;
            }
        } catch (error) {
            console.error('Error updating export counts:', error);
        }
    }

    async previewExport() {
        try {
            const exportData = await this.gatherExportData();
            const format = document.querySelector('input[name="export-format"]:checked')?.value || 'json';
            
            let previewContent = '';
            
            switch (format) {
                case 'json':
                    previewContent = JSON.stringify(exportData, null, 2);
                    break;
                case 'csv':
                    previewContent = this.convertToCSV(exportData);
                    break;
                case 'txt':
                    previewContent = this.convertToText(exportData);
                    break;
            }

            const previewEl = document.getElementById('export-preview');
            const contentEl = document.getElementById('export-preview-content');
            
            if (previewEl && contentEl) {
                contentEl.textContent = previewContent.substring(0, 1000) + (previewContent.length > 1000 ? '\n...(truncated)' : '');
                previewEl.style.display = 'block';
            }

        } catch (error) {
            console.error('Error generating export preview:', error);
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showError('Preview Failed', 'Could not generate preview');
            }
        }
    }

    async gatherExportData() {
        const exportData = {
            metadata: {
                exported_at: new Date().toISOString(),
                version: '1.0',
                source: 'L&D Metrics Translator'
            }
        };

        // Get selected options
        const includeMetrics = document.getElementById('export-metrics')?.checked;
        const includePreferences = document.getElementById('export-preferences')?.checked;
        const includeSearchHistory = document.getElementById('export-search-history')?.checked;
        const includeRecommendations = document.getElementById('export-recommendations')?.checked;
        const includeSessionData = document.getElementById('export-session-data')?.checked;

        try {
            if (includeMetrics) {
                exportData.metrics = await window.contextManager?.getSelectedMetrics() || [];
            }

            if (includePreferences) {
                exportData.preferences = window.contextManager?.getPreferences() || {};
            }

            if (includeSearchHistory) {
                exportData.searchHistory = await this.getSearchHistory();
            }

            if (includeRecommendations) {
                exportData.recommendations = await this.getRecommendations();
            }

            if (includeSessionData) {
                exportData.session = await window.contextManager?.getSessionStats() || {};
            }

        } catch (error) {
            console.error('Error gathering export data:', error);
        }

        return exportData;
    }

    async getSearchHistory() {
        try {
            const response = await fetch('/api/context/event-analysis/history?limit=50');
            if (response.ok) {
                const data = await response.json();
                return data.history || [];
            }
        } catch (error) {
            console.error('Error getting search history:', error);
        }
        return [];
    }

    async getRecommendations() {
        try {
            const response = await fetch('/api/smart-recommendations/history');
            if (response.ok) {
                const data = await response.json();
                return data.recommendations || [];
            }
        } catch (error) {
            console.error('Error getting recommendations:', error);
        }
        return [];
    }

    convertToCSV(data) {
        if (!data.metrics || data.metrics.length === 0) {
            return 'No metrics data to export as CSV';
        }

        const headers = ['Metric ID', 'Metric Name', 'Selection Type', 'Selected At', 'Is Active'];
        const rows = data.metrics.map(metric => [
            metric.metric_id || '',
            metric.metric_name || '',
            metric.selection_type || '',
            metric.selected_at || '',
            metric.is_active || false
        ]);

        return [headers, ...rows].map(row => 
            row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')
        ).join('\n');
    }

    convertToText(data) {
        let text = `L&D Metrics Translator - Context Export\n`;
        text += `Exported: ${data.metadata.exported_at}\n`;
        text += `${'='.repeat(50)}\n\n`;

        if (data.metrics && data.metrics.length > 0) {
            text += `SELECTED METRICS (${data.metrics.length})\n`;
            text += `-`.repeat(30) + '\n';
            data.metrics.forEach((metric, index) => {
                text += `${index + 1}. ${metric.metric_name || `Metric ${metric.metric_id}`}\n`;
                text += `   Type: ${metric.selection_type || 'manual'}\n`;
                text += `   Selected: ${metric.selected_at || 'Unknown'}\n\n`;
            });
        }

        if (data.preferences && Object.keys(data.preferences).length > 0) {
            text += `USER PREFERENCES\n`;
            text += `-`.repeat(30) + '\n';
            Object.entries(data.preferences).forEach(([key, value]) => {
                text += `${key}: ${value}\n`;
            });
            text += '\n';
        }

        if (data.searchHistory && data.searchHistory.length > 0) {
            text += `SEARCH HISTORY (${data.searchHistory.length})\n`;
            text += `-`.repeat(30) + '\n';
            data.searchHistory.slice(0, 10).forEach((search, index) => {
                text += `${index + 1}. ${search.event_description || search.query}\n`;
                text += `   Date: ${search.created_date}\n`;
                text += `   Success: ${search.success ? 'Yes' : 'No'}\n\n`;
            });
        }

        return text;
    }

    async performExport() {
        try {
            const exportBtn = this.exportModal.querySelector('.btn-primary');
            if (exportBtn) {
                exportBtn.disabled = true;
                exportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Exporting...';
            }

            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showLoading('Exporting Context...', 'Gathering data');
            }

            const exportData = await this.gatherExportData();
            const format = document.querySelector('input[name="export-format"]:checked')?.value || 'json';
            
            let content, filename, mimeType;

            switch (format) {
                case 'json':
                    content = JSON.stringify(exportData, null, 2);
                    filename = `ld-context-${new Date().toISOString().split('T')[0]}.json`;
                    mimeType = 'application/json';
                    break;
                case 'csv':
                    content = this.convertToCSV(exportData);
                    filename = `ld-metrics-${new Date().toISOString().split('T')[0]}.csv`;
                    mimeType = 'text/csv';
                    break;
                case 'txt':
                    content = this.convertToText(exportData);
                    filename = `ld-summary-${new Date().toISOString().split('T')[0]}.txt`;
                    mimeType = 'text/plain';
                    break;
            }

            // Create and download file
            const blob = new Blob([content], { type: mimeType });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.hideExportModal();

            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showSaved('Export Complete', `Downloaded ${filename}`);
            }

        } catch (error) {
            console.error('Error performing export:', error);
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showError('Export Failed', 'Could not export context data');
            }
        } finally {
            const exportBtn = this.exportModal.querySelector('.btn-primary');
            if (exportBtn) {
                exportBtn.disabled = false;
                exportBtn.innerHTML = '<i class="fas fa-download"></i> Export Data';
            }
        }
    }

    handleFileSelect(file) {
        if (!file) return;

        const fileInfo = document.getElementById('file-info');
        const uploadPlaceholder = document.querySelector('.upload-placeholder');

        if (fileInfo && uploadPlaceholder) {
            fileInfo.querySelector('.file-name').textContent = file.name;
            fileInfo.querySelector('.file-size').textContent = this.formatFileSize(file.size);
            
            uploadPlaceholder.style.display = 'none';
            fileInfo.style.display = 'block';
        }

        // Read file content
        const reader = new FileReader();
        reader.onload = (e) => {
            this.validateFileContent(e.target.result, file.type);
        };
        reader.readAsText(file);
    }

    clearFile() {
        const fileInput = document.getElementById('context-file-input');
        const fileInfo = document.getElementById('file-info');
        const uploadPlaceholder = document.querySelector('.upload-placeholder');

        if (fileInput) fileInput.value = '';
        if (fileInfo) fileInfo.style.display = 'none';
        if (uploadPlaceholder) uploadPlaceholder.style.display = 'block';

        this.hideImportPreview();
    }

    switchImportMethod(method) {
        document.querySelectorAll('.import-method').forEach(el => {
            el.classList.remove('active');
        });
        document.querySelector(`[data-method="${method}"]`).classList.add('active');
    }

    validateFileContent(content, fileType) {
        try {
            let parsedData;

            if (fileType === 'application/json' || content.trim().startsWith('{')) {
                parsedData = JSON.parse(content);
            } else {
                // Handle CSV or text files
                parsedData = { raw: content };
            }

            this.showImportPreview(parsedData);

        } catch (error) {
            console.error('Error validating file content:', error);
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showError('Invalid File', 'Could not parse file content');
            }
        }
    }

    validateTextInput() {
        const textArea = document.getElementById('import-text-data');
        if (!textArea || !textArea.value.trim()) {
            this.hideImportPreview();
            return;
        }

        try {
            const parsedData = JSON.parse(textArea.value);
            this.showImportPreview(parsedData);
        } catch (error) {
            this.hideImportPreview();
        }
    }

    showImportPreview(data) {
        const previewEl = document.getElementById('import-preview');
        const summaryEl = document.getElementById('preview-summary');
        const importBtn = document.getElementById('import-btn');

        if (!previewEl || !summaryEl) return;

        let summary = '<div class="preview-items">';
        
        if (data.metrics) {
            summary += `<div class="preview-item">
                <i class="fas fa-check-square"></i>
                ${data.metrics.length} metrics
            </div>`;
        }
        
        if (data.preferences) {
            summary += `<div class="preview-item">
                <i class="fas fa-cog"></i>
                ${Object.keys(data.preferences).length} preferences
            </div>`;
        }
        
        if (data.searchHistory) {
            summary += `<div class="preview-item">
                <i class="fas fa-search"></i>
                ${data.searchHistory.length} searches
            </div>`;
        }

        summary += '</div>';

        summaryEl.innerHTML = summary;
        previewEl.style.display = 'block';
        
        if (importBtn) {
            importBtn.disabled = false;
        }

        // Store data for import
        this.importData = data;
    }

    hideImportPreview() {
        const previewEl = document.getElementById('import-preview');
        const importBtn = document.getElementById('import-btn');

        if (previewEl) previewEl.style.display = 'none';
        if (importBtn) importBtn.disabled = true;

        this.importData = null;
    }

    async validateImport() {
        if (!this.importData) {
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showError('No Data', 'Please select a file or paste data first');
            }
            return;
        }

        // Perform validation checks
        const issues = [];

        if (this.importData.metrics) {
            const invalidMetrics = this.importData.metrics.filter(m => !m.metric_id);
            if (invalidMetrics.length > 0) {
                issues.push(`${invalidMetrics.length} metrics missing IDs`);
            }
        }

        if (issues.length > 0) {
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showError('Validation Issues', issues.join(', '));
            }
        } else {
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showSaved('Validation Passed', 'Data is ready to import');
            }
        }
    }

    async performImport() {
        if (!this.importData) return;

        try {
            const importBtn = document.getElementById('import-btn');
            if (importBtn) {
                importBtn.disabled = true;
                importBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Importing...';
            }

            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showLoading('Importing Context...', 'Applying changes');
            }

            const mergeMode = document.getElementById('import-merge')?.checked;
            const createBackup = document.getElementById('import-backup')?.checked;

            // Create backup if requested
            if (createBackup) {
                await this.createBackup();
            }

            // Import data
            if (this.importData.preferences) {
                await window.contextManager?.updatePreferences(this.importData.preferences);
            }

            if (this.importData.metrics && !mergeMode) {
                // Clear existing selections if not merging
                await window.contextManager?.clearMetricSelections();
            }

            if (this.importData.metrics) {
                // Import metric selections
                for (const metric of this.importData.metrics) {
                    await window.contextManager?.selectMetric(metric.metric_id, 'imported');
                }
            }

            this.hideImportModal();

            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showSaved('Import Complete', 'Context data has been restored');
            }

            // Refresh page to apply changes
            setTimeout(() => {
                window.location.reload();
            }, 1500);

        } catch (error) {
            console.error('Error performing import:', error);
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showError('Import Failed', 'Could not import context data');
            }
        } finally {
            const importBtn = document.getElementById('import-btn');
            if (importBtn) {
                importBtn.disabled = false;
                importBtn.innerHTML = '<i class="fas fa-upload"></i> Import Data';
            }
        }
    }

    async createBackup() {
        try {
            const backupData = await this.gatherExportData();
            const backupKey = `ld_backup_${Date.now()}`;
            localStorage.setItem(backupKey, JSON.stringify(backupData));
            
            // Keep only last 3 backups
            const backupKeys = Object.keys(localStorage)
                .filter(key => key.startsWith('ld_backup_'))
                .sort()
                .reverse();
                
            backupKeys.slice(3).forEach(key => {
                localStorage.removeItem(key);
            });

        } catch (error) {
            console.error('Error creating backup:', error);
        }
    }

    formatFileSize(bytes) {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / 1048576).toFixed(1)} MB`;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.contextExportImport = new ContextExportImport();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ContextExportImport;
}
