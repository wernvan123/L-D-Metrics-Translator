/**
 * PDF Generation Frontend for L&D Metrics Translator
 * Handles PDF report generation requests and user interface
 */

class PDFGenerator {
    constructor() {
        this.isGenerating = false;
        this.init();
    }

    init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.initializeAfterDOMReady();
            });
        } else {
            this.initializeAfterDOMReady();
        }
    }

    initializeAfterDOMReady() {
        console.log('PDFGenerator: Initializing PDF generation interface');
        this.initializePDFGenerator();
    }

    initializePDFGenerator() {
        console.log('PDFGenerator: Initializing PDF generator');
        
        // Skip PDF panel creation entirely
        console.log('PDFGenerator: PDF panel creation is disabled');
        return;
        
        // The rest of the method is now unreachable and will be removed

        // Create PDF generation panel
        const panel = document.createElement('div');
        panel.id = 'pdf-generator-panel';
        panel.className = 'pdf-generator-panel';
        panel.innerHTML = `
            <div class="pdf-panel-header">
                <h3>📄 Generate PDF Report</h3>
                <p class="pdf-panel-subtitle">Create professional reports from your selections</p>
            </div>
            <div class="pdf-panel-content">
                <div class="pdf-options">
                    <div class="pdf-option-group">
                        <label class="pdf-option">
                            <input type="radio" name="report-type" value="comprehensive" checked>
                            <div class="option-content">
                                <strong>Comprehensive Report</strong>
                                <p>Full analysis with metrics, recommendations, and implementation roadmap</p>
                            </div>
                        </label>
                        <label class="pdf-option">
                            <input type="radio" name="report-type" value="summary">
                            <div class="option-content">
                                <strong>Quick Summary</strong>
                                <p>1-page overview of selected metrics and key insights</p>
                            </div>
                        </label>
                    </div>
                    
                    <div class="pdf-preview-section">
                        <button id="preview-metrics-btn" class="btn btn-secondary">
                            <span class="btn-icon">👁️</span>
                            Preview Metrics
                        </button>
                        <div id="metrics-preview" class="metrics-preview" style="display: none;"></div>
                    </div>
                    
                    <div class="pdf-actions">
                        <button id="generate-pdf-btn" class="btn btn-primary">
                            <span class="btn-icon">📄</span>
                            <span class="btn-text">Generate PDF Report</span>
                            <div class="btn-loading" style="display: none;">
                                <div class="loading-spinner"></div>
                                Generating...
                            </div>
                        </button>
                    </div>
                </div>
                
                <div class="pdf-status" id="pdf-status" style="display: none;"></div>
            </div>
        `;

        // Insert panel after the Implement section
        const implementSection = document.getElementById('implement');
        const container = document.querySelector('.container');

        if (implementSection && implementSection.parentNode) {
            // Insert after the Implement section
            implementSection.parentNode.insertBefore(panel, implementSection.nextSibling);
            console.log('PDFGenerator: Panel positioned after Implement section');
        } else if (container) {
            // Fallback: Append to end of main container
            container.appendChild(panel);
            console.log('PDFGenerator: Panel appended to container');
        } else {
            // Last resort: Append to body
            document.body.appendChild(panel);
            console.warn('PDFGenerator: Could not find suitable position, appending to body');
        }

        console.log('PDFGenerator: Panel created and inserted');
    }

    bindEvents() {
        // Generate PDF button
        const generateBtn = document.getElementById('generate-pdf-btn');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generatePDF());
        }

        // Preview metrics button
        const previewBtn = document.getElementById('preview-metrics-btn');
        if (previewBtn) {
            previewBtn.addEventListener('click', () => this.previewMetrics());
        }

        // Listen for selection changes to update preview
        document.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox' && e.target.closest('.dropdown-content')) {
                // Clear preview when selections change
                const preview = document.getElementById('metrics-preview');
                if (preview && preview.style.display !== 'none') {
                    preview.style.display = 'none';
                }
            }
        });
    }

    async previewMetrics() {
        try {
            const selections = this.getCurrentSelections();
            
            this.showStatus('Loading preview...', 'info');
            
            const response = await fetch('/pdf/preview-metrics', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(selections)
            });

            if (!response.ok) {
                throw new Error(`Preview failed: ${response.status}`);
            }

            const data = await response.json();
            this.displayMetricsPreview(data);
            this.hideStatus();

        } catch (error) {
            console.error('Preview error:', error);
            this.showStatus(`Preview failed: ${error.message}`, 'error');
        }
    }

    displayMetricsPreview(data) {
        const preview = document.getElementById('metrics-preview');
        if (!preview) return;

        let html = `
            <div class="preview-header">
                <h4>📊 Report Preview</h4>
                <div class="preview-stats">
                    <span class="stat"><strong>${data.total_metrics}</strong> metrics</span>
                    <span class="stat"><strong>${data.summary.categories}</strong> categories</span>
                    <span class="stat"><strong>${data.summary.outcomes}</strong> outcomes</span>
                </div>
            </div>
        `;

        if (data.metrics_by_category && Object.keys(data.metrics_by_category).length > 0) {
            html += '<div class="preview-categories">';
            
            Object.entries(data.metrics_by_category).forEach(([category, metrics]) => {
                html += `
                    <div class="preview-category">
                        <h5>${category} (${metrics.length})</h5>
                        <ul class="preview-metrics-list">
                `;
                
                metrics.slice(0, 5).forEach(metric => {
                    html += `<li>${metric.name}</li>`;
                });
                
                if (metrics.length > 5) {
                    html += `<li class="more-metrics">... and ${metrics.length - 5} more</li>`;
                }
                
                html += '</ul></div>';
            });
            
            html += '</div>';
        } else {
            html += '<p class="no-metrics">No metrics selected. Please make selections above to generate a report.</p>';
        }

        preview.innerHTML = html;
        preview.style.display = 'block';
    }

    async generatePDF() {
        if (this.isGenerating) return;

        try {
            this.isGenerating = true;
            this.showGeneratingState();

            const selections = this.getCurrentSelections();
            const reportType = this.getSelectedReportType();
            
            // Get recommendations if available
            let recommendations = {};
            if (window.recommendationEngine && window.recommendationEngine.recommendations) {
                recommendations = window.recommendationEngine.recommendations;
            }

            const requestData = {
                ...selections,
                recommendations: recommendations,
                report_type: reportType
            };

            // First, generate LLM-powered report content
            this.showStatus('Generating AI-powered report content...', 'info');
            
            // Format data for the generate-report API (ensure we have metrics)
            const reportApiData = {
                metrics: selections.selected_metrics && selections.selected_metrics.length > 0 
                    ? selections.selected_metrics 
                    : ['Employee Engagement Score', 'Training Completion Rate'], // Default metrics for testing
                outcomes: selections.selected_outcomes || ['Performance Improvement'],
                context: selections.context || 'L&D metrics analysis and performance improvement',
                categories: selections.categories || [],
                report_type: reportType
            };
            
            console.log('PDF Generator: Sending data to generate-report API:', reportApiData);
            
            const llmResponse = await fetch('/api/generate-report', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''
                },
                body: JSON.stringify(reportApiData)
            });

            if (!llmResponse.ok) {
                throw new Error('Failed to generate LLM content');
            }

            const llmData = await llmResponse.json();
            if (!llmData.success) {
                throw new Error(llmData.error || 'LLM report generation failed');
            }

            // Add LLM-generated content to request data
            requestData.llm_content = llmData.report_content;
            requestData.llm_source = llmData.generated_by;

            // Now generate the PDF with LLM content
            this.showStatus('Creating PDF document...', 'info');
            const response = await fetch('/pdf/generate-from-selections', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Generation failed: ${response.status}`);
            }

            // Handle file download
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            
            // Get filename from response headers or use default
            const contentDisposition = response.headers.get('content-disposition');
            let filename = 'LD_Metrics_Report.pdf';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            }
            
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            const sourceText = llmData.generated_by === 'ai' ? 'AI-Enhanced' : 'Standard';
            this.showStatus(`${sourceText} PDF generated and downloaded successfully!`, 'success');
            setTimeout(() => this.hideStatus(), 3000);

        } catch (error) {
            console.error('PDF generation error:', error);
            this.showStatus(`Generation failed: ${error.message}`, 'error');
        } finally {
            this.isGenerating = false;
            this.hideGeneratingState();
        }
    }

    getCurrentSelections() {
        const selections = {
            categories: [],
            outcomes: [],
            metrics: [],
            neuroscience: [],
            selected_metrics: [],
            selected_outcomes: []
        };

        // Get selections from multi-select navigation if available
        if (window.multiSelectNav && window.multiSelectNav.selections) {
            Object.keys(selections).forEach(key => {
                if (window.multiSelectNav.selections[key]) {
                    selections[key] = Array.from(window.multiSelectNav.selections[key]);
                }
            });
            
            // Also populate the selected_metrics and selected_outcomes arrays
            selections.selected_metrics = Array.from(window.multiSelectNav.selections.metrics || []);
            selections.selected_outcomes = Array.from(window.multiSelectNav.selections.outcomes || []);
        }

        // If no selections from multiSelectNav, try to get from visible metric cards
        if (selections.selected_metrics.length === 0) {
            const visibleCards = document.querySelectorAll('.metric-card:not([style*="display: none"])');
            selections.selected_metrics = Array.from(visibleCards).map(card => {
                return card.querySelector('h3')?.textContent?.trim() || 'Selected Metric';
            }).filter(Boolean);
        }

        return selections;
    }

    getSelectedReportType() {
        const selectedRadio = document.querySelector('input[name="report-type"]:checked');
        return selectedRadio ? selectedRadio.value : 'comprehensive';
    }

    showGeneratingState() {
        const btn = document.getElementById('generate-pdf-btn');
        if (btn) {
            const btnText = btn.querySelector('.btn-text');
            const btnLoading = btn.querySelector('.btn-loading');
            
            if (btnText) btnText.style.display = 'none';
            if (btnLoading) btnLoading.style.display = 'flex';
            
            btn.disabled = true;
            btn.classList.add('generating');
        }
    }

    hideGeneratingState() {
        const btn = document.getElementById('generate-pdf-btn');
        if (btn) {
            const btnText = btn.querySelector('.btn-text');
            const btnLoading = btn.querySelector('.btn-loading');
            
            if (btnText) btnText.style.display = 'inline';
            if (btnLoading) btnLoading.style.display = 'none';
            
            btn.disabled = false;
            btn.classList.remove('generating');
        }
    }

    showStatus(message, type = 'info') {
        const status = document.getElementById('pdf-status');
        if (status) {
            status.innerHTML = `
                <div class="status-message status-${type}">
                    <span class="status-icon">
                        ${type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️'}
                    </span>
                    <span class="status-text">${message}</span>
                </div>
            `;
            status.style.display = 'block';
        }
    }

    hideStatus() {
        const status = document.getElementById('pdf-status');
        if (status) {
            status.style.display = 'none';
        }
    }
}

// Initialize PDF generator when DOM is ready
const pdfGenerator = new PDFGenerator();

// Make it globally available
window.pdfGenerator = pdfGenerator;
