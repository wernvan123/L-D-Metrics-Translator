/**
 * Context Summary Display Component
 * Shows comprehensive context information and session state
 */

class ContextSummary {
    constructor() {
        this.summaryPanel = null;
        this.isVisible = false;
        this.updateInterval = null;
        this.init();
    }

    init() {
        this.createSummaryPanel();
        this.setupEventListeners();
        this.startAutoUpdate();
    }

    createSummaryPanel() {
        // Create the context summary panel
        this.summaryPanel = document.createElement('div');
        this.summaryPanel.id = 'context-summary-panel';
        this.summaryPanel.className = 'context-summary-panel hidden';
        this.summaryPanel.innerHTML = `
            <div class="summary-header">
                <div class="summary-title">
                    <i class="fas fa-chart-line"></i>
                    Context Summary
                </div>
                <div class="summary-actions">
                    <button class="summary-refresh" onclick="contextSummary.refreshSummary()" title="Refresh">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                    <button class="summary-toggle" onclick="contextSummary.togglePanel()" title="Minimize">
                        <i class="fas fa-chevron-down"></i>
                    </button>
                    <button class="summary-close" onclick="contextSummary.hidePanel()" title="Close">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            </div>
            
            <div class="summary-content">
                <!-- Session Overview -->
                <div class="summary-section">
                    <h4 class="section-title">
                        <i class="fas fa-clock"></i>
                        Session Overview
                    </h4>
                    <div class="session-stats">
                        <div class="stat-item">
                            <span class="stat-label">Duration</span>
                            <span class="stat-value" id="session-duration">--</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Started</span>
                            <span class="stat-value" id="session-start">--</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-label">Last Activity</span>
                            <span class="stat-value" id="last-activity">--</span>
                        </div>
                    </div>
                </div>

                <!-- Metric Selections -->
                <div class="summary-section">
                    <h4 class="section-title">
                        <i class="fas fa-check-square"></i>
                        Selected Metrics
                        <span class="count-badge" id="metrics-count">0</span>
                    </h4>
                    <div class="metrics-summary" id="metrics-summary">
                        <div class="empty-state">No metrics selected</div>
                    </div>
                </div>

                <!-- Search History -->
                <div class="summary-section">
                    <h4 class="section-title">
                        <i class="fas fa-search"></i>
                        Recent Searches
                        <span class="count-badge" id="searches-count">0</span>
                    </h4>
                    <div class="searches-summary" id="searches-summary">
                        <div class="empty-state">No recent searches</div>
                    </div>
                </div>

                <!-- Context Data -->
                <div class="summary-section">
                    <h4 class="section-title">
                        <i class="fas fa-database"></i>
                        Stored Context
                        <span class="count-badge" id="context-count">0</span>
                    </h4>
                    <div class="context-summary" id="context-summary">
                        <div class="empty-state">No context data</div>
                    </div>
                </div>

                <!-- User Preferences -->
                <div class="summary-section">
                    <h4 class="section-title">
                        <i class="fas fa-cog"></i>
                        Preferences
                    </h4>
                    <div class="preferences-summary" id="preferences-summary">
                        <div class="empty-state">Default preferences</div>
                    </div>
                </div>

                <!-- Quick Actions -->
                <div class="summary-section">
                    <h4 class="section-title">
                        <i class="fas fa-bolt"></i>
                        Quick Actions
                    </h4>
                    <div class="quick-actions">
                        <button class="action-btn" onclick="contextSummary.exportContext()">
                            <i class="fas fa-download"></i>
                            Export Context
                        </button>
                        <button class="action-btn" onclick="contextSummary.clearContext()">
                            <i class="fas fa-trash"></i>
                            Clear Context
                        </button>
                        <button class="action-btn" onclick="contextSummary.saveSession()">
                            <i class="fas fa-save"></i>
                            Save Session
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(this.summaryPanel);

        // Position it on the left side
        this.summaryPanel.style.left = '20px';
        this.summaryPanel.style.top = '50%';
        this.summaryPanel.style.transform = 'translateY(-50%)';
    }

    async refreshSummary() {
        try {
            // Show loading state
            const refreshBtn = this.summaryPanel.querySelector('.summary-refresh i');
            if (refreshBtn) {
                refreshBtn.classList.add('fa-spin');
            }

            // Get current context data
            const [sessionStats, selectedMetrics, preferences] = await Promise.all([
                this.getSessionStats(),
                this.getSelectedMetrics(),
                this.getPreferences()
            ]);

            // Update each section
            await this.updateSessionOverview(sessionStats);
            await this.updateMetricsSummary(selectedMetrics);
            await this.updateSearchesSummary();
            await this.updateContextSummary();
            await this.updatePreferencesSummary(preferences);

            // Remove loading state
            if (refreshBtn) {
                refreshBtn.classList.remove('fa-spin');
            }

        } catch (error) {
            console.error('Error refreshing context summary:', error);
        }
    }

    async getSessionStats() {
        try {
            return await window.contextManager?.getSessionStats() || {};
        } catch (error) {
            console.error('Error getting session stats:', error);
            return {};
        }
    }

    async getSelectedMetrics() {
        try {
            return await window.contextManager?.getSelectedMetrics() || [];
        } catch (error) {
            console.error('Error getting selected metrics:', error);
            return [];
        }
    }

    getPreferences() {
        try {
            return window.contextManager?.getPreferences() || {};
        } catch (error) {
            console.error('Error getting preferences:', error);
            return {};
        }
    }

    updateSessionOverview(stats) {
        const durationEl = document.getElementById('session-duration');
        const startEl = document.getElementById('session-start');
        const activityEl = document.getElementById('last-activity');

        if (durationEl) {
            durationEl.textContent = this.formatDuration(stats.session_duration || 0);
        }

        if (startEl) {
            const startTime = stats.created_date ? new Date(stats.created_date) : new Date();
            startEl.textContent = startTime.toLocaleTimeString();
        }

        if (activityEl) {
            const lastActivity = stats.last_activity ? new Date(stats.last_activity) : new Date();
            activityEl.textContent = this.getTimeAgo(lastActivity);
        }
    }

    updateMetricsSummary(metrics) {
        const countEl = document.getElementById('metrics-count');
        const summaryEl = document.getElementById('metrics-summary');

        if (countEl) {
            countEl.textContent = metrics.length;
        }

        if (summaryEl) {
            if (metrics.length === 0) {
                summaryEl.innerHTML = '<div class="empty-state">No metrics selected</div>';
            } else {
                const metricsHTML = metrics.slice(0, 5).map(metric => `
                    <div class="summary-item">
                        <div class="item-name">${metric.metric_name || `Metric ${metric.metric_id}`}</div>
                        <div class="item-meta">
                            <span class="item-type">${metric.selection_type || 'manual'}</span>
                            <span class="item-time">${this.getTimeAgo(new Date(metric.selected_at))}</span>
                        </div>
                    </div>
                `).join('');

                const moreCount = metrics.length - 5;
                const moreHTML = moreCount > 0 ? `
                    <div class="summary-more">
                        +${moreCount} more metrics
                    </div>
                ` : '';

                summaryEl.innerHTML = metricsHTML + moreHTML;
            }
        }
    }

    async updateSearchesSummary() {
        try {
            const searchHistory = await this.getSearchHistory();
            const countEl = document.getElementById('searches-count');
            const summaryEl = document.getElementById('searches-summary');

            if (countEl) {
                countEl.textContent = searchHistory.length;
            }

            if (summaryEl) {
                if (searchHistory.length === 0) {
                    summaryEl.innerHTML = '<div class="empty-state">No recent searches</div>';
                } else {
                    const searchesHTML = searchHistory.slice(0, 3).map(search => `
                        <div class="summary-item">
                            <div class="item-name">${this.truncateText(search.event_description || search.query, 40)}</div>
                            <div class="item-meta">
                                <span class="item-status ${search.success ? 'success' : 'error'}">
                                    ${search.success ? '✅' : '❌'}
                                </span>
                                <span class="item-time">${this.getTimeAgo(new Date(search.created_date))}</span>
                            </div>
                        </div>
                    `).join('');

                    summaryEl.innerHTML = searchesHTML;
                }
            }
        } catch (error) {
            console.error('Error updating searches summary:', error);
        }
    }

    async getSearchHistory() {
        try {
            const response = await fetch('/api/context/event-analysis/history?limit=10');
            if (response.ok) {
                const data = await response.json();
                return data.history || [];
            }
            return [];
        } catch (error) {
            console.error('Error getting search history:', error);
            return [];
        }
    }

    async updateContextSummary() {
        try {
            const contextData = await this.getContextData();
            const countEl = document.getElementById('context-count');
            const summaryEl = document.getElementById('context-summary');

            if (countEl) {
                countEl.textContent = contextData.length;
            }

            if (summaryEl) {
                if (contextData.length === 0) {
                    summaryEl.innerHTML = '<div class="empty-state">No context data</div>';
                } else {
                    const contextHTML = contextData.slice(0, 3).map(context => `
                        <div class="summary-item">
                            <div class="item-name">${context.context_type}:${context.context_key}</div>
                            <div class="item-meta">
                                <span class="item-size">${this.formatDataSize(context.data_size || 0)}</span>
                                <span class="item-time">${this.getTimeAgo(new Date(context.updated_date))}</span>
                            </div>
                        </div>
                    `).join('');

                    summaryEl.innerHTML = contextHTML;
                }
            }
        } catch (error) {
            console.error('Error updating context summary:', error);
        }
    }

    async getContextData() {
        // This would need to be implemented in the backend API
        // For now, return mock data
        return [];
    }

    updatePreferencesSummary(preferences) {
        const summaryEl = document.getElementById('preferences-summary');

        if (summaryEl) {
            const prefKeys = Object.keys(preferences);
            if (prefKeys.length === 0) {
                summaryEl.innerHTML = '<div class="empty-state">Default preferences</div>';
            } else {
                const prefsHTML = prefKeys.slice(0, 4).map(key => `
                    <div class="summary-item">
                        <div class="item-name">${this.formatPrefKey(key)}</div>
                        <div class="item-value">${this.formatPrefValue(preferences[key])}</div>
                    </div>
                `).join('');

                summaryEl.innerHTML = prefsHTML;
            }
        }
    }

    formatPrefKey(key) {
        return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    formatPrefValue(value) {
        if (typeof value === 'boolean') {
            return value ? 'Enabled' : 'Disabled';
        }
        if (typeof value === 'string' && value.length > 20) {
            return value.substring(0, 20) + '...';
        }
        return String(value);
    }

    formatDuration(seconds) {
        if (seconds < 60) {
            return `${seconds}s`;
        } else if (seconds < 3600) {
            return `${Math.floor(seconds / 60)}m`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${minutes}m`;
        }
    }

    formatDataSize(bytes) {
        if (bytes < 1024) return `${bytes}B`;
        if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)}KB`;
        return `${(bytes / 1048576).toFixed(1)}MB`;
    }

    getTimeAgo(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return date.toLocaleDateString();
    }

    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    showPanel() {
        this.summaryPanel.classList.remove('hidden');
        this.summaryPanel.classList.add('visible');
        this.isVisible = true;
        this.refreshSummary();
    }

    hidePanel() {
        this.summaryPanel.classList.remove('visible');
        this.summaryPanel.classList.add('hidden');
        this.isVisible = false;
    }

    togglePanel() {
        if (this.isVisible) {
            this.hidePanel();
        } else {
            this.showPanel();
        }
    }

    startAutoUpdate() {
        // Update every 30 seconds when visible
        this.updateInterval = setInterval(() => {
            if (this.isVisible) {
                this.refreshSummary();
            }
        }, 30000);
    }

    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    setupEventListeners() {
        // Listen for context changes
        document.addEventListener('contextManager:metricSelectionChanged', () => {
            if (this.isVisible) {
                setTimeout(() => this.refreshSummary(), 500);
            }
        });

        document.addEventListener('contextManager:preferencesUpdated', () => {
            if (this.isVisible) {
                setTimeout(() => this.refreshSummary(), 500);
            }
        });

        // Listen for visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && this.isVisible) {
                this.refreshSummary();
            }
        });

        // Add keyboard shortcut (Ctrl+Shift+S)
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'S') {
                e.preventDefault();
                this.togglePanel();
            }
        });
    }

    // Quick action methods
    async exportContext() {
        try {
            const contextData = {
                session: await this.getSessionStats(),
                metrics: await this.getSelectedMetrics(),
                preferences: this.getPreferences(),
                searches: await this.getSearchHistory(),
                timestamp: new Date().toISOString()
            };

            const blob = new Blob([JSON.stringify(contextData, null, 2)], {
                type: 'application/json'
            });

            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `ld-context-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showSaved('Context Exported', 'Downloaded as JSON file');
            }

        } catch (error) {
            console.error('Error exporting context:', error);
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showError('Export Failed', 'Could not export context');
            }
        }
    }

    async clearContext() {
        if (!confirm('Are you sure you want to clear all context data? This action cannot be undone.')) {
            return;
        }

        try {
            // Clear metric selections
            await window.contextManager?.clearMetricSelections();

            // Clear search history
            await fetch('/api/context/event-analysis/clear', { method: 'DELETE' });

            // Reset preferences to defaults
            await window.contextManager?.updatePreferences({});

            this.refreshSummary();

            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showSaved('Context Cleared', 'All data has been reset');
            }

        } catch (error) {
            console.error('Error clearing context:', error);
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showError('Clear Failed', 'Could not clear context');
            }
        }
    }

    async saveSession() {
        try {
            const sessionKey = await window.sessionRestore?.saveCurrentSession();
            
            if (sessionKey) {
                if (window.contextStatusIndicator) {
                    window.contextStatusIndicator.showSaved('Session Saved', 'Can be restored later');
                }
            } else {
                throw new Error('Failed to save session');
            }

        } catch (error) {
            console.error('Error saving session:', error);
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showError('Save Failed', 'Could not save session');
            }
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.contextSummary = new ContextSummary();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ContextSummary;
}
