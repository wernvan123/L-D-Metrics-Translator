/**
 * Dynamic Report Generator
 * Handles the frontend functionality for dynamic PDF report generation
 */

class DynamicReportGenerator {
    constructor() {
        this.selectedOutcomes = new Set();
        this.selectedMetrics = new Set();
        this.aiRecommendations = [];
        this.reportType = 'comprehensive';
        this.currentReportId = null;
        this.progressInterval = null;
        
        this.init();
    }
    
    init() {
        // Only initialize if the report UI is present on the page
        const hasUI = document.getElementById('report-title') ||
                      document.getElementById('selected-outcomes-list') ||
                      document.getElementById('report-generation-progress');
        if (!hasUI) {
            console.info('DynamicReportGenerator: UI not present on this page. Skipping initialization.');
            return;
        }

        this.bindEvents();
        this.updateSelectionSummary();
        this.loadExistingReports();
        
        // Listen for global selection changes
        document.addEventListener('metricSelectionChanged', (e) => {
            this.handleMetricSelection(e.detail);
        });
        
        document.addEventListener('outcomeSelectionChanged', (e) => {
            this.handleOutcomeSelection(e.detail);
        });
        
        document.addEventListener('aiRecommendationsUpdated', (e) => {
            this.handleAIRecommendations(e.detail);
        });
    }
    
    bindEvents() {
        // Report type selection
        document.querySelectorAll('.report-type-option').forEach(option => {
            option.addEventListener('click', (e) => {
                this.selectReportType(e.currentTarget.dataset.type);
            });
        });
        
        // Report title input
        const titleInput = document.getElementById('report-title');
        if (titleInput) {
            titleInput.addEventListener('input', () => {
                this.validateForm();
            });
        }
        
        // Action buttons
        const generateBtn = document.getElementById('generate-report-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => {
                this.generateReport();
            });
        }
        
        const previewBtn = document.getElementById('preview-report-btn');
        if (previewBtn) {
            previewBtn.addEventListener('click', () => {
                this.previewConfiguration();
            });
        }
        
        const saveConfigBtn = document.getElementById('save-config-btn');
        if (saveConfigBtn) {
            saveConfigBtn.addEventListener('click', () => {
                this.saveConfiguration();
            });
        }
        
        const cancelBtn = document.getElementById('cancel-generation-btn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                this.cancelGeneration();
            });
        }
        
        const refreshBtn = document.getElementById('refresh-reports-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadExistingReports();
            });
        }
    }
    
    selectReportType(type) {
        this.reportType = type;
        
        // Update UI
        document.querySelectorAll('.report-type-option').forEach(option => {
            option.classList.remove('active');
        });
        
        document.querySelector(`[data-type="${type}"]`).classList.add('active');
        
        this.updatePageEstimate();
        this.validateForm();
    }
    
    handleMetricSelection(metrics) {
        this.selectedMetrics = new Set(metrics.map(m => m.id));
        this.updateSelectionSummary();
        this.validateForm();
    }
    
    handleOutcomeSelection(outcomes) {
        this.selectedOutcomes = new Set(outcomes.map(o => o.id));
        this.updateSelectionSummary();
        this.validateForm();
    }
    
    handleAIRecommendations(recommendations) {
        this.aiRecommendations = recommendations || [];
        this.updateSelectionSummary();
        this.updatePageEstimate();
    }
    
    updateSelectionSummary() {
        // Update counts - check if elements exist first
        const outcomesCountEl = document.getElementById('selected-outcomes-count');
        const metricsCountEl = document.getElementById('selected-metrics-count-report');
        const aiCountEl = document.getElementById('ai-recommendations-count');
        
        if (outcomesCountEl) outcomesCountEl.textContent = this.selectedOutcomes.size;
        if (metricsCountEl) metricsCountEl.textContent = this.selectedMetrics.size;
        if (aiCountEl) aiCountEl.textContent = this.aiRecommendations.length;
        
        // Update outcome tags
        const outcomesList = document.getElementById('selected-outcomes-list');
        if (outcomesList) {
            if (this.selectedOutcomes.size === 0) {
                outcomesList.innerHTML = '<span class="no-selection">No outcomes selected</span>';
            } else {
                // Get outcome names from global state if available
                const outcomeNames = Array.from(this.selectedOutcomes).map(id => {
                    // Try to get from global outcomes data
                    if (window.ldOutcomes && window.ldOutcomes[id]) {
                        return window.ldOutcomes[id].name;
                    }
                    return `Outcome ${id}`;
                });
                
                outcomesList.innerHTML = outcomeNames.map(name => 
                    `<span class="tag">${name}</span>`
                ).join('');
            }
        }
        
        // Update metrics tags
        const metricsList = document.getElementById('selected-metrics-list');
        if (metricsList) {
            if (this.selectedMetrics.size === 0) {
                metricsList.innerHTML = '<span class="no-selection">No metrics selected</span>';
            } else {
                // Get metric names from global state if available
                const metricNames = Array.from(this.selectedMetrics).map(id => {
                    // Try to get from global metrics data
                    if (window.metricsData && window.metricsData.find) {
                        const metric = window.metricsData.find(m => m.id === id);
                        return metric ? metric.name : `Metric ${id}`;
                    }
                    return `Metric ${id}`;
                });
                
                metricsList.innerHTML = metricNames.slice(0, 10).map(name => 
                    `<span class="tag">${name}</span>`
                ).join('') + (metricNames.length > 10 ? `<span class="tag">+${metricNames.length - 10} more</span>` : '');
            }
        }
        
        this.updatePageEstimate();
    }
    
    updatePageEstimate() {
        const basePages = this.reportType === 'comprehensive' ? 8 : 5;
        const metricPages = Math.ceil(this.selectedMetrics.size * 0.5);
        const aiPages = Math.ceil(this.aiRecommendations.length * 0.3);
        const outcomePages = Math.ceil(this.selectedOutcomes.size * 0.4);
        
        const estimatedPages = Math.min(basePages + metricPages + aiPages + outcomePages, 
                                      this.reportType === 'comprehensive' ? 20 : 10);
        
        const estimatedPagesEl = document.getElementById('estimated-pages');
        if (estimatedPagesEl) {
            estimatedPagesEl.textContent = estimatedPages;
        }
    }
    
    validateForm() {
        const titleInput = document.getElementById('report-title');
        const generateBtn = document.getElementById('generate-report-btn');
        
        const hasTitle = titleInput && titleInput.value.trim().length > 0;
        const hasSelections = this.selectedMetrics.size > 0 || this.selectedOutcomes.size > 0;
        
        if (generateBtn) {
            generateBtn.disabled = !hasTitle || !hasSelections;
        }
    }
    
    displayReports(reports) {
        const container = document.getElementById('generated-reports-list');
        if (!container) return;
        
        // Ensure reports is an array
        if (!Array.isArray(reports)) {
            console.warn('Reports data is not an array:', reports);
            container.innerHTML = '<p class="no-reports">No reports generated yet</p>';
            return;
        }
        
        if (reports.length === 0) {
            container.innerHTML = '<p class="no-reports">No reports generated yet</p>';
            return;
        }
        
        container.innerHTML = reports.map(report => `
            <div class="report-item">
                <div class="report-item-header">
                    <div>
                        <h6 class="report-item-title">${report.title}</h6>
                        <div class="report-item-meta">Created: ${new Date(report.created_at).toLocaleDateString()} | Type: ${report.report_type}</div>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    async generateReport() {
        const titleInput = document.getElementById('report-title');
        const title = titleInput.value.trim();
        
        if (!title) {
            this.showNotification('Please enter a report title', 'error');
            return;
        }
        
        if (this.selectedMetrics.size === 0 && this.selectedOutcomes.size === 0) {
            this.showNotification('Please select at least one metric or outcome', 'error');
            return;
        }
        
        try {
            // Show progress
            this.showProgress();
            
            // Prepare request data
            const requestData = {
                title: title,
                template_type: this.reportType,
                selected_outcomes: Array.from(this.selectedOutcomes),
                selected_metrics: Array.from(this.selectedMetrics),
                ai_recommendations: this.aiRecommendations,
                session_id: this.getSessionId(),
                generation_context: {}
            };
            
            // Create report
            const response = await fetch('/api/dynamic-reports', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            const report = result.report || result;
            const reportId = (report && (report.id || report.report_id)) || result.report_id || result.id;
            this.currentReportId = String(reportId || '');

            // If backend completed synchronously, finish immediately; else start polling
            const status = report && (report.generation_status || report.status);
            if (status && String(status).toLowerCase() === 'completed') {
                this.onReportCompleted();
            } else if (this.currentReportId) {
                this.trackProgress();
            } else {
                throw new Error('Missing report ID from create response');
            }
            
        } catch (error) {
            console.error('Error generating report:', error);
            this.hideProgress();
            this.showNotification('Failed to generate report. Please try again.', 'error');
        }
    }
    
    async trackProgress() {
        if (!this.currentReportId) return;
        
        this.progressInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/dynamic-reports/${this.currentReportId}/progress`);
                if (!response.ok) throw new Error('Failed to fetch progress');
                
                const data = await response.json();
                const raw = data.progress || data; // backend returns { success, progress: {...} }

                // Normalize to frontend shape
                const status = (raw.status || '').toLowerCase();
                const progressValue = typeof raw.progress === 'number' ? raw.progress : (raw.progress_percentage || 0);

                // Map backend status to UI steps
                const statusToStep = (s) => {
                    if (s === 'queued') return 'analyzing';
                    if (s === 'generating') return 'generating';
                    if (s === 'formatting') return 'formatting';
                    if (s === 'completed') return 'complete';
                    if (s === 'failed') return 'failed';
                    return 'analyzing';
                };

                const normalized = {
                    status: status || raw.status || '',
                    progress_percentage: Math.max(0, Math.min(100, Number(progressValue) || 0)),
                    current_step: raw.current_step || statusToStep(status)
                };

                this.updateProgressDisplay(normalized);
                
                if (normalized.status === 'completed' || normalized.status === 'failed') {
                    clearInterval(this.progressInterval);
                    this.progressInterval = null;
                    
                    if (normalized.status === 'completed') {
                        this.onReportCompleted();
                    } else {
                        this.onReportFailed(raw.error_message || 'Unknown error');
                    }
                }
            } catch (error) {
                console.error('Error tracking progress:', error);
                clearInterval(this.progressInterval);
                this.progressInterval = null;
                this.hideProgress();
            }
        }, 2000);
    }
    
    updateProgressDisplay(progress) {
        const progressFill = document.getElementById('progress-fill');
        const progressPercentage = document.getElementById('progress-percentage');
        const progressStatus = document.getElementById('progress-status');
        
        if (progressFill) {
            progressFill.style.width = `${progress.progress_percentage}%`;
        }
        
        if (progressPercentage) {
            progressPercentage.textContent = `${progress.progress_percentage}%`;
        }
        
        if (progressStatus) {
            const label = (progress.current_step || '').toLowerCase();
            const friendly = label === 'complete' ? 'Completed' : (label ? label.charAt(0).toUpperCase() + label.slice(1) + '...' : 'Processing...');
            progressStatus.textContent = friendly;
        }
        
        // Update step indicators
        const steps = ['analyzing', 'generating', 'formatting', 'complete'];
        const stepName = (progress.current_step || '').toLowerCase();
        const idx = steps.indexOf(stepName);
        const currentStepIndex = idx >= 0 ? idx : 0;
        
        document.querySelectorAll('.progress-step').forEach((step, index) => {
            step.classList.remove('active', 'completed');
            if (index < currentStepIndex) {
                step.classList.add('completed');
            } else if (index === currentStepIndex) {
                step.classList.add('active');
            }
        });
    }
    
    onReportCompleted() {
        this.hideProgress();
        this.showNotification('Report generated successfully!', 'success');
        this.loadExistingReports();
        
        // Offer download
        if (this.currentReportId) {
            const downloadBtn = document.createElement('button');
            downloadBtn.className = 'btn btn-primary';
            downloadBtn.innerHTML = '<span class="btn-icon">📥</span> Download Report';
            downloadBtn.onclick = () => this.downloadReport(this.currentReportId);
            
            // Add to notification or show modal
            this.showDownloadOption(downloadBtn);
        }
    }
    
    onReportFailed(errorMessage) {
        this.hideProgress();
        this.showNotification(`Report generation failed: ${errorMessage}`, 'error');
    }
    
    cancelGeneration() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
        
        this.hideProgress();
        this.showNotification('Report generation cancelled', 'info');
    }
    
    showProgress() {
        document.getElementById('report-generation-progress').style.display = 'block';
        
        // Reset progress display
        document.getElementById('progress-fill').style.width = '0%';
        document.getElementById('progress-percentage').textContent = '0%';
        document.getElementById('progress-status').textContent = 'Initializing...';
        
        // Reset steps
        document.querySelectorAll('.progress-step').forEach(step => {
            step.classList.remove('active', 'completed');
        });
        document.querySelector('[data-step="analyzing"]').classList.add('active');
    }
    
    hideProgress() {
        document.getElementById('report-generation-progress').style.display = 'none';
    }
    
    async loadExistingReports() {
        try {
            const sessionId = this.getSessionId();
            const response = await fetch(`/api/dynamic-reports/session/${sessionId}`);
            
            if (response.ok) {
                const data = await response.json();
                console.log('Reports API response:', data);
                
                // Handle different response formats
                let reports = [];
                if (data.reports && Array.isArray(data.reports)) {
                    reports = data.reports;
                } else if (Array.isArray(data)) {
                    reports = data;
                } else {
                    console.warn('Unexpected reports data format:', data);
                }
                
                this.displayReports(reports);
            } else {
                console.error('Failed to load reports:', response.status);
                this.displayReports([]);
            }
        } catch (error) {
            console.error('Error loading reports:', error);
            this.displayReports([]);
        }
    }
    
    displayReports(reports) {
        const reportsList = document.getElementById('reports-list');
        const noReportsMessage = document.getElementById('no-reports-message');
        
        if (reports.length === 0) {
            reportsList.style.display = 'none';
            noReportsMessage.style.display = 'block';
            return;
        }
        
        reportsList.style.display = 'block';
        noReportsMessage.style.display = 'none';
        
        reportsList.innerHTML = reports.map(report => this.createReportItem(report)).join('');
    }
    
    createReportItem(report) {
        const createdRaw = report.created_date || report.created_at;
        const createdDate = createdRaw ? new Date(createdRaw).toLocaleDateString() : 'Unknown';
        const statusClass = (report.generation_status || '').toLowerCase();
        const reportType = report.report_type || report.template_type || (report.template_id ? `Template #${report.template_id}` : '');
        
        return `
            <div class="report-item">
                <div class="report-item-header">
                    <div>
                        <h6 class="report-item-title">${report.title}</h6>
                        <div class="report-item-meta">Created: ${createdDate} | Type: ${reportType || 'N/A'}</div>
                    </div>
                    <span class="report-status ${statusClass}">${report.generation_status}</span>
                </div>
                
                <div class="report-item-content">
                    <div class="report-item-stats">
                        <span>📊 ${report.metrics_count || 0} metrics</span>
                        <span>🎯 ${report.outcomes_count || 0} outcomes</span>
                        <span>🤖 ${report.ai_recommendations_count || 0} AI insights</span>
                        ${report.file_size ? `<span>📄 ${this.formatFileSize(report.file_size)}</span>` : ''}
                    </div>
                </div>
                
                <div class="report-item-actions">
                    ${report.generation_status === 'completed' ? 
                        `<button class="btn btn-sm btn-primary" onclick="reportGenerator.downloadReport('${report.id}')">
                            <span class="btn-icon">📥</span> Download
                        </button>` : ''
                    }
                    ${report.generation_status === 'generating' ? 
                        `<button class="btn btn-sm btn-outline" onclick="reportGenerator.viewProgress('${report.id}')">
                            <span class="btn-icon">👁️</span> View Progress
                        </button>` : ''
                    }
                    <button class="btn btn-sm btn-outline" onclick="reportGenerator.viewReportDetails('${report.id}')">
                        <span class="btn-icon">ℹ️</span> Details
                    </button>
                    <button class="btn btn-sm btn-outline btn-danger" onclick="reportGenerator.deleteReport('${report.id}')">
                        <span class="btn-icon">🗑️</span> Delete
                    </button>
                </div>
            </div>
        `;
    }
    
    async downloadReport(reportId) {
        try {
            const response = await fetch(`/api/dynamic-reports/${reportId}/download`);
            
            if (!response.ok) {
                throw new Error('Failed to download report');
            }
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            let fname = `report-${reportId}.pdf`;
            try {
                const cd = response.headers.get('content-disposition') || '';
                const m = cd.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
                fname = decodeURIComponent((m && (m[1] || m[2])) || fname);
            } catch (e) {}
            a.download = fname;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            this.showNotification('Report downloaded successfully!', 'success');
            
        } catch (error) {
            console.error('Error downloading report:', error);
            this.showNotification('Failed to download report', 'error');
        }
    }
    
    async viewReportDetails(reportId) {
        try {
            const response = await fetch(`/api/dynamic-reports/${reportId}`);
            
            if (!response.ok) {
                throw new Error('Failed to load report details');
            }
            
            const report = await response.json();
            this.showReportDetailsModal(report);
            
        } catch (error) {
            console.error('Error loading report details:', error);
            this.showNotification('Failed to load report details', 'error');
        }
    }
    
    async deleteReport(reportId) {
        if (!confirm('Are you sure you want to delete this report?')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/dynamic-reports/${reportId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error('Failed to delete report');
            }
            
            this.showNotification('Report deleted successfully', 'success');
            this.loadExistingReports();
            
        } catch (error) {
            console.error('Error deleting report:', error);
            this.showNotification('Failed to delete report', 'error');
        }
    }
    
    previewConfiguration() {
        const config = {
            title: document.getElementById('report-title').value,
            type: this.reportType,
            outcomes: this.selectedOutcomes.size,
            metrics: this.selectedMetrics.size,
            aiRecommendations: this.aiRecommendations.length,
            estimatedPages: document.getElementById('estimated-pages').textContent
        };
        
        this.showPreviewModal(config);
    }
    
    saveConfiguration() {
        const config = {
            title: document.getElementById('report-title').value,
            type: this.reportType,
            outcomes: Array.from(this.selectedOutcomes),
            metrics: Array.from(this.selectedMetrics),
            aiRecommendations: this.aiRecommendations
        };
        
        localStorage.setItem('reportConfiguration', JSON.stringify(config));
        this.showNotification('Configuration saved successfully!', 'success');
    }
    
    loadConfiguration() {
        const saved = localStorage.getItem('reportConfiguration');
        if (saved) {
            const config = JSON.parse(saved);
            
            document.getElementById('report-title').value = config.title || '';
            this.selectReportType(config.type || 'comprehensive');
            
            // Note: Actual selections would need to be restored through the main app
            this.showNotification('Configuration loaded successfully!', 'success');
        }
    }
    
    // Utility methods
    getSessionId() {
        // Try to get from global context or generate one
        if (window.currentSession && window.currentSession.id) {
            return String(window.currentSession.id);
        }
        
        // Use a simple timestamp-based session ID for now
        // In production, this would be managed by proper session handling
        let sessionId = localStorage.getItem('sessionId');
        if (!sessionId) {
            sessionId = String(Math.floor(Date.now() / 1000)); // timestamp string
            localStorage.setItem('sessionId', sessionId);
        }
        return String(sessionId);
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">${message}</span>
                <button class="notification-close">&times;</button>
            </div>
        `;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
        
        // Close button
        notification.querySelector('.notification-close').addEventListener('click', () => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        });
    }
    
    showPreviewModal(config) {
        // Create and show preview modal
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h4>📋 Report Configuration Preview</h4>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="config-preview">
                        <div class="preview-item">
                            <strong>Title:</strong> ${config.title || 'Untitled Report'}
                        </div>
                        <div class="preview-item">
                            <strong>Type:</strong> ${config.type === 'comprehensive' ? 'Comprehensive Report' : 'Basic Report'}
                        </div>
                        <div class="preview-item">
                            <strong>L&D Outcomes:</strong> ${config.outcomes} selected
                        </div>
                        <div class="preview-item">
                            <strong>Metrics:</strong> ${config.metrics} selected
                        </div>
                        <div class="preview-item">
                            <strong>AI Recommendations:</strong> ${config.aiRecommendations} available
                        </div>
                        <div class="preview-item">
                            <strong>Estimated Pages:</strong> ${config.estimatedPages}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary" onclick="this.closest('.modal-overlay').remove()">Close</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close handlers
        modal.querySelector('.modal-close').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }
    
    showReportDetailsModal(report) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h4>📊 Report Details</h4>
                    <button class="modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="report-details">
                        <div class="detail-item">
                            <strong>Title:</strong> ${report.title}
                        </div>
                        <div class="detail-item">
                            <strong>Status:</strong> <span class="report-status ${report.generation_status.toLowerCase()}">${report.generation_status}</span>
                        </div>
                        <div class="detail-item">
                            <strong>Type:</strong> ${report.report_type}
                        </div>
                        <div class="detail-item">
                            <strong>Created:</strong> ${new Date(report.created_at).toLocaleString()}
                        </div>
                        ${report.completed_at ? `
                        <div class="detail-item">
                            <strong>Completed:</strong> ${new Date(report.completed_at).toLocaleString()}
                        </div>
                        ` : ''}
                        <div class="detail-item">
                            <strong>Content Sections:</strong> ${report.content_sections ? Object.keys(report.content_sections).length : 0}
                        </div>
                        ${report.file_size ? `
                        <div class="detail-item">
                            <strong>File Size:</strong> ${this.formatFileSize(report.file_size)}
                        </div>
                        ` : ''}
                        ${report.error_message ? `
                        <div class="detail-item error">
                            <strong>Error:</strong> ${report.error_message}
                        </div>
                        ` : ''}
                    </div>
                </div>
                <div class="modal-footer">
                    ${report.generation_status === 'completed' ? 
                        `<button class="btn btn-primary" onclick="reportGenerator.downloadReport('${report.id}')">Download Report</button>` : ''
                    }
                    <button class="btn btn-outline" onclick="this.closest('.modal-overlay').remove()">Close</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close handlers
        modal.querySelector('.modal-close').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }
    
    showDownloadOption(downloadBtn) {
        const notification = document.createElement('div');
        notification.className = 'notification notification-success download-notification';
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-message">Your report is ready!</span>
                <div class="notification-actions">
                    ${downloadBtn.outerHTML}
                    <button class="notification-close">&times;</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 10 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 10000);
        
        // Close button
        notification.querySelector('.notification-close').addEventListener('click', () => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    try {
        window.dynamicReportGenerator = new DynamicReportGenerator();
        // Backward-compatibility alias used by inline onclick handlers
        window.reportGenerator = window.dynamicReportGenerator;
    } catch (error) {
        console.error('Error initializing DynamicReportGenerator:', error);
    }
});

// Also initialize immediately if DOM is already loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        if (!window.dynamicReportGenerator) {
            try {
                window.dynamicReportGenerator = new DynamicReportGenerator();
                window.reportGenerator = window.dynamicReportGenerator;
            } catch (error) {
                console.error('Error initializing DynamicReportGenerator:', error);
            }
        }
    });
} else {
    // DOM is already loaded
    if (!window.dynamicReportGenerator) {
        try {
            window.dynamicReportGenerator = new DynamicReportGenerator();
            window.reportGenerator = window.dynamicReportGenerator;
        } catch (error) {
            console.error('Error initializing DynamicReportGenerator:', error);
        }
    }
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DynamicReportGenerator;
}
