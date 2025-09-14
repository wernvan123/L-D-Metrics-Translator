/**
 * Report Generation Functionality
 * Handles comprehensive and basic report creation
 */

// Global report state
window.LDMetricsApp = window.LDMetricsApp || {};
window.LDMetricsApp.reports = {
    selectedMetrics: new Set(),
    analysisResults: null,
    userContext: null
};

// Initialize report functionality
document.addEventListener('DOMContentLoaded', function() {
    initializeReportGeneration();
    setupPreviewMetrics();
});

/**
 * Initialize report generation functionality
 */
function initializeReportGeneration() {
    // Enable export buttons when report is generated
    updateExportButtonStates();
    
    // Load any existing selected metrics
    loadSelectedMetrics();
}

/**
 * Setup preview metrics functionality
 */
function setupPreviewMetrics() {
    const previewBtn = document.getElementById('preview-metrics-btn');
    if (previewBtn) {
        previewBtn.addEventListener('click', showSelectedMetricsPreview);
    }
}

/**
 * Generate comprehensive report
 */
function generateComprehensiveReport() {
    const selectedMetrics = getSelectedMetrics();
    const analysisResults = getAnalysisResults();
    
    if (selectedMetrics.length === 0) {
        showNotification('Please select at least one metric to include in your report.', 'warning');
        return;
    }
    
    const report = {
        type: 'comprehensive',
        title: 'L&D Metrics Analysis Report',
        generatedAt: new Date().toISOString(),
        sections: [
            generateExecutiveSummary(selectedMetrics, analysisResults),
            generateIssueAnalysis(analysisResults),
            generateMetricsAnalysis(selectedMetrics),
            generateNeuroscienceInsights(selectedMetrics),
            generateRecommendations(selectedMetrics, analysisResults),
            generateImplementationPlan(selectedMetrics),
            generateAppendix(selectedMetrics)
        ]
    };
    
    displayGeneratedReport(report);
    enableExportButtons();
    showNotification('Comprehensive report generated successfully!', 'success');
}

/**
 * Generate basic report
 */
function generateBasicReport() {
    const selectedMetrics = getSelectedMetrics();
    const analysisResults = getAnalysisResults();
    
    if (selectedMetrics.length === 0) {
        showNotification('Please select at least one metric to include in your report.', 'warning');
        return;
    }
    
    const report = {
        type: 'basic',
        title: 'L&D Metrics Summary Report',
        generatedAt: new Date().toISOString(),
        sections: [
            generateBasicSummary(selectedMetrics, analysisResults),
            generateKeyMetrics(selectedMetrics),
            generateQuickRecommendations(selectedMetrics, analysisResults)
        ]
    };
    
    displayGeneratedReport(report);
    enableExportButtons();
    showNotification('Basic report generated successfully!', 'success');
}

/**
 * Generate executive summary section
 */
function generateExecutiveSummary(metrics, analysis) {
    const outcomeCategories = [...new Set(metrics.map(m => m.outcome))];
    const metricTypes = [...new Set(metrics.map(m => m.type))];
    
    return {
        title: '1. Executive Summary',
        content: `
            <div class="report-section">
                <h3>Executive Summary</h3>
                <p><strong>Report Overview:</strong> This comprehensive analysis covers ${metrics.length} key L&D metrics across ${outcomeCategories.length} outcome areas and ${metricTypes.length} metric categories.</p>
                
                <div class="summary-highlights">
                    <h4>Key Highlights:</h4>
                    <ul>
                        <li><strong>Scope:</strong> ${metrics.length} metrics analyzed across ${outcomeCategories.join(', ')}</li>
                        <li><strong>Metric Types:</strong> ${metricTypes.join(', ')}</li>
                        ${analysis ? `<li><strong>Context:</strong> Analysis based on specific workplace event/challenge</li>` : ''}
                        <li><strong>Focus Areas:</strong> ${outcomeCategories.map(cat => `${cat} outcomes`).join(', ')}</li>
                    </ul>
                </div>
                
                <div class="executive-recommendations">
                    <h4>Executive Recommendations:</h4>
                    <p>Based on the selected metrics and analysis, we recommend focusing on ${outcomeCategories[0]} as the primary outcome area, with particular attention to ${metricTypes.includes('Behavioral Metric') ? 'behavioral change indicators' : 'operational performance metrics'}.</p>
                </div>
            </div>
        `
    };
}

/**
 * Generate issue analysis section
 */
function generateIssueAnalysis(analysis) {
    if (!analysis) {
        return {
            title: '2. Issue Analysis',
            content: `
                <div class="report-section">
                    <h3>Issue Analysis</h3>
                    <p><em>No specific workplace event or challenge was analyzed. This report focuses on the selected metrics without contextual analysis.</em></p>
                </div>
            `
        };
    }
    
    return {
        title: '2. Issue Analysis',
        content: `
            <div class="report-section">
                <h3>Issue Analysis</h3>
                <div class="issue-context">
                    <h4>Identified Challenge:</h4>
                    <p>${analysis.context || 'Workplace challenge requiring L&D intervention'}</p>
                </div>
                
                <div class="ai-insights">
                    <h4>AI Analysis Results:</h4>
                    ${analysis.learningNeeds ? `
                        <div class="analysis-category">
                            <h5>Learning Needs Identified:</h5>
                            <ul>${analysis.learningNeeds.map(need => `<li>${need}</li>`).join('')}</ul>
                        </div>
                    ` : ''}
                    
                    ${analysis.interventions ? `
                        <div class="analysis-category">
                            <h5>Recommended Interventions:</h5>
                            <ul>${analysis.interventions.map(intervention => `<li>${intervention}</li>`).join('')}</ul>
                        </div>
                    ` : ''}
                </div>
            </div>
        `
    };
}

/**
 * Generate metrics analysis section
 */
function generateMetricsAnalysis(metrics) {
    const groupedMetrics = groupMetricsByOutcome(metrics);
    
    return {
        title: '3. Metrics Analysis',
        content: `
            <div class="report-section">
                <h3>Metrics Analysis</h3>
                <p>Detailed analysis of ${metrics.length} selected metrics organized by L&D outcome:</p>
                
                ${Object.entries(groupedMetrics).map(([outcome, outcomeMetrics]) => `
                    <div class="outcome-group">
                        <h4>${outcome} (${outcomeMetrics.length} metrics)</h4>
                        <div class="metrics-list">
                            ${outcomeMetrics.map(metric => `
                                <div class="metric-analysis">
                                    <h5>${metric.name}</h5>
                                    <p><strong>Type:</strong> ${metric.type}</p>
                                    <p><strong>Description:</strong> ${metric.description}</p>
                                    ${metric.example ? `<p><strong>Example:</strong> ${metric.example}</p>` : ''}
                                    ${metric.neuroscience ? `<p><strong>Neuroscience Basis:</strong> ${metric.neuroscience}</p>` : ''}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        `
    };
}

/**
 * Generate neuroscience insights section
 */
function generateNeuroscienceInsights(metrics) {
    const neuroscienceMetrics = metrics.filter(m => m.neuroscience);
    
    return {
        title: '4. Neuroscience Insights',
        content: `
            <div class="report-section">
                <h3>Neuroscience-Based Insights</h3>
                ${neuroscienceMetrics.length > 0 ? `
                    <p>The following neuroscience concepts support the effectiveness of your selected metrics:</p>
                    <div class="neuroscience-concepts">
                        ${neuroscienceMetrics.map(metric => `
                            <div class="concept-item">
                                <h5>${metric.name}</h5>
                                <p><strong>Neuroscience Basis:</strong> ${metric.neuroscience}</p>
                                <p><strong>Application:</strong> This concept explains why ${metric.name.toLowerCase()} is an effective indicator for measuring ${metric.outcome.toLowerCase()}.</p>
                            </div>
                        `).join('')}
                    </div>
                ` : `
                    <p><em>No neuroscience-based metrics were selected. Consider including neuroscience concepts to strengthen the scientific foundation of your L&D approach.</em></p>
                `}
            </div>
        `
    };
}

/**
 * Generate recommendations section
 */
function generateRecommendations(metrics, analysis) {
    const outcomeCategories = [...new Set(metrics.map(m => m.outcome))];
    
    return {
        title: '5. Recommendations',
        content: `
            <div class="report-section">
                <h3>Strategic Recommendations</h3>
                
                <div class="recommendation-categories">
                    <div class="rec-category">
                        <h4>Measurement Strategy</h4>
                        <ul>
                            <li>Implement a balanced scorecard approach using ${metrics.length} key metrics</li>
                            <li>Focus measurement efforts on ${outcomeCategories.join(' and ')} outcomes</li>
                            <li>Establish baseline measurements before implementing interventions</li>
                            <li>Set up regular monitoring intervals (monthly/quarterly) for each metric</li>
                        </ul>
                    </div>
                    
                    <div class="rec-category">
                        <h4>Implementation Approach</h4>
                        <ul>
                            <li>Start with ${metrics.filter(m => m.type === 'Operational KPI').length > 0 ? 'operational KPIs' : 'behavioral metrics'} for immediate impact measurement</li>
                            <li>Gradually introduce more sophisticated metrics as measurement capability matures</li>
                            <li>Ensure data collection systems are in place for all selected metrics</li>
                            <li>Train stakeholders on metric interpretation and action planning</li>
                        </ul>
                    </div>
                    
                    ${analysis ? `
                        <div class="rec-category">
                            <h4>Context-Specific Recommendations</h4>
                            <ul>
                                <li>Address the identified challenge through targeted L&D interventions</li>
                                <li>Monitor progress using the selected metrics as leading and lagging indicators</li>
                                <li>Adjust interventions based on metric feedback and trends</li>
                            </ul>
                        </div>
                    ` : ''}
                </div>
            </div>
        `
    };
}

/**
 * Generate implementation plan section
 */
function generateImplementationPlan(metrics) {
    return {
        title: '6. Implementation Plan',
        content: `
            <div class="report-section">
                <h3>90-Day Implementation Plan</h3>
                
                <div class="implementation-timeline">
                    <div class="phase">
                        <h4>Phase 1: Foundation (Days 1-30)</h4>
                        <ul>
                            <li>Establish data collection processes for all ${metrics.length} metrics</li>
                            <li>Create measurement dashboards and reporting templates</li>
                            <li>Train team members on metric definitions and collection methods</li>
                            <li>Collect baseline data for all metrics</li>
                        </ul>
                    </div>
                    
                    <div class="phase">
                        <h4>Phase 2: Implementation (Days 31-60)</h4>
                        <ul>
                            <li>Launch L&D interventions based on metric insights</li>
                            <li>Begin regular metric monitoring and data collection</li>
                            <li>Establish feedback loops with stakeholders</li>
                            <li>Refine measurement processes based on initial results</li>
                        </ul>
                    </div>
                    
                    <div class="phase">
                        <h4>Phase 3: Optimization (Days 61-90)</h4>
                        <ul>
                            <li>Analyze trends and patterns in metric data</li>
                            <li>Adjust interventions based on metric feedback</li>
                            <li>Prepare comprehensive progress report</li>
                            <li>Plan for long-term metric monitoring and improvement</li>
                        </ul>
                    </div>
                </div>
            </div>
        `
    };
}

/**
 * Generate appendix section
 */
function generateAppendix(metrics) {
    return {
        title: '7. Appendix',
        content: `
            <div class="report-section">
                <h3>Appendix</h3>
                
                <div class="appendix-content">
                    <h4>Metric Definitions</h4>
                    <div class="metric-definitions">
                        ${metrics.map(metric => `
                            <div class="definition-item">
                                <h5>${metric.name}</h5>
                                <p><strong>Category:</strong> ${metric.type}</p>
                                <p><strong>Outcome:</strong> ${metric.outcome}</p>
                                <p><strong>Definition:</strong> ${metric.description}</p>
                                ${metric.example ? `<p><strong>Example:</strong> ${metric.example}</p>` : ''}
                            </div>
                        `).join('')}
                    </div>
                    
                    <h4>Data Collection Templates</h4>
                    <p>Contact your L&D team for specific data collection templates and measurement tools for each metric.</p>
                    
                    <h4>Additional Resources</h4>
                    <ul>
                        <li>L&D Metrics Best Practices Guide</li>
                        <li>Neuroscience-Based Learning Design Principles</li>
                        <li>ROI Calculation Methodologies for L&D</li>
                    </ul>
                </div>
            </div>
        `
    };
}

/**
 * Generate basic summary for simple report
 */
function generateBasicSummary(metrics, analysis) {
    return {
        title: 'Summary',
        content: `
            <div class="report-section">
                <h3>L&D Metrics Summary</h3>
                <p>This report covers ${metrics.length} key metrics selected for your L&D measurement strategy.</p>
                
                ${analysis ? `
                    <div class="context-summary">
                        <h4>Context</h4>
                        <p>Based on your described workplace challenge, the following metrics will help track progress and measure success.</p>
                    </div>
                ` : ''}
                
                <div class="metric-overview">
                    <h4>Selected Metrics Overview</h4>
                    <p><strong>Outcome Areas:</strong> ${[...new Set(metrics.map(m => m.outcome))].join(', ')}</p>
                    <p><strong>Metric Types:</strong> ${[...new Set(metrics.map(m => m.type))].join(', ')}</p>
                </div>
            </div>
        `
    };
}

/**
 * Generate key metrics section for basic report
 */
function generateKeyMetrics(metrics) {
    return {
        title: 'Key Metrics',
        content: `
            <div class="report-section">
                <h3>Your Selected Metrics</h3>
                <div class="basic-metrics-list">
                    ${metrics.map(metric => `
                        <div class="basic-metric-item">
                            <h4>${metric.name}</h4>
                            <p><span class="metric-badge">${metric.type}</span> | <span class="outcome-badge">${metric.outcome}</span></p>
                            <p>${metric.description}</p>
                        </div>
                    `).join('')}
                </div>
            </div>
        `
    };
}

/**
 * Generate quick recommendations for basic report
 */
function generateQuickRecommendations(metrics, analysis) {
    return {
        title: 'Quick Recommendations',
        content: `
            <div class="report-section">
                <h3>Next Steps</h3>
                <div class="quick-actions">
                    <h4>Immediate Actions:</h4>
                    <ol>
                        <li>Set up data collection for your ${metrics.length} selected metrics</li>
                        <li>Establish baseline measurements</li>
                        <li>Create a simple tracking dashboard</li>
                        <li>Schedule regular review meetings</li>
                    </ol>
                    
                    <h4>Key Focus Areas:</h4>
                    <ul>
                        ${[...new Set(metrics.map(m => m.outcome))].map(outcome => 
                            `<li>Monitor ${outcome.toLowerCase()} through relevant metrics</li>`
                        ).join('')}
                    </ul>
                </div>
            </div>
        `
    };
}

/**
 * Helper functions
 */
function getSelectedMetrics() {
    const selectedCards = document.querySelectorAll('.metric-card.selected');
    return Array.from(selectedCards).map(card => ({
        id: card.dataset.id,
        name: card.dataset.name,
        type: card.dataset.typeName,
        outcome: card.dataset.outcomeName,
        description: card.querySelector('.metric-description')?.textContent || '',
        example: card.querySelector('.metric-example')?.textContent?.replace('Example: ', '') || '',
        neuroscience: card.querySelector('.metric-neuroscience')?.textContent?.replace('🧠 Neuroscience: ', '') || ''
    }));
}

function getAnalysisResults() {
    const analysisContent = document.getElementById('analysis-content');
    if (!analysisContent || analysisContent.style.display === 'none') {
        return null;
    }
    
    // Extract analysis results from the DOM
    return {
        context: 'AI-analyzed workplace event',
        learningNeeds: extractListItems(analysisContent, 'learning needs'),
        interventions: extractListItems(analysisContent, 'interventions'),
        metrics: extractListItems(analysisContent, 'metrics')
    };
}

function extractListItems(container, category) {
    const items = [];
    const lists = container.querySelectorAll('ul, ol');
    lists.forEach(list => {
        const listItems = list.querySelectorAll('li');
        listItems.forEach(item => items.push(item.textContent.trim()));
    });
    return items;
}

function groupMetricsByOutcome(metrics) {
    return metrics.reduce((groups, metric) => {
        const outcome = metric.outcome;
        if (!groups[outcome]) {
            groups[outcome] = [];
        }
        groups[outcome].push(metric);
        return groups;
    }, {});
}

function displayGeneratedReport(report) {
    // Create or update report display area
    let reportContainer = document.getElementById('generated-report');
    if (!reportContainer) {
        reportContainer = document.createElement('div');
        reportContainer.id = 'generated-report';
        reportContainer.className = 'generated-report';
        
        const implementSection = document.getElementById('implement');
        implementSection.appendChild(reportContainer);
    }
    
    reportContainer.innerHTML = `
        <div class="report-header">
            <h2>${report.title}</h2>
            <p class="report-meta">Generated on ${new Date(report.generatedAt).toLocaleDateString()}</p>
        </div>
        <div class="report-content">
            ${report.sections.map(section => section.content).join('')}
        </div>
    `;
    
    reportContainer.style.display = 'block';
    
    // Scroll to report
    reportContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showSelectedMetricsPreview() {
    const selectedMetrics = getSelectedMetrics();
    
    if (selectedMetrics.length === 0) {
        showNotification('No metrics selected. Please select metrics from the Explore section.', 'info');
        return;
    }
    
    const previewContent = `
        <div class="metrics-preview">
            <h3>Selected Metrics Preview (${selectedMetrics.length})</h3>
            <div class="preview-list">
                ${selectedMetrics.map(metric => `
                    <div class="preview-item">
                        <h4>${metric.name}</h4>
                        <p><span class="badge">${metric.type}</span> | <span class="badge">${metric.outcome}</span></p>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    // Show in modal or notification
    showNotification(previewContent, 'info', 8000);
}

function enableExportButtons() {
    const exportButtons = document.querySelectorAll('[onclick*="export"], [onclick*="share"], [onclick*="createActionPlan"]');
    exportButtons.forEach(btn => {
        btn.disabled = false;
        btn.classList.remove('disabled');
    });
}

function updateExportButtonStates() {
    const hasReport = document.getElementById('generated-report')?.style.display !== 'none';
    const exportButtons = document.querySelectorAll('[onclick*="export"], [onclick*="share"], [onclick*="createActionPlan"]');
    
    exportButtons.forEach(btn => {
        btn.disabled = !hasReport;
        if (!hasReport) {
            btn.classList.add('disabled');
        }
    });
}

function loadSelectedMetrics() {
    // Load any previously selected metrics from localStorage or session
    const saved = localStorage.getItem('selectedMetrics');
    if (saved) {
        try {
            const metrics = JSON.parse(saved);
            metrics.forEach(metricId => {
                const card = document.querySelector(`[data-id="${metricId}"]`);
                if (card) {
                    card.classList.add('selected');
                }
            });
        } catch (e) {
            console.warn('Could not load saved metrics:', e);
        }
    }
}

// Export functions for global use
window.generateComprehensiveReport = generateComprehensiveReport;
window.generateBasicReport = generateBasicReport;
window.showSelectedMetricsPreview = showSelectedMetricsPreview;

console.log('Report generation functionality loaded');
