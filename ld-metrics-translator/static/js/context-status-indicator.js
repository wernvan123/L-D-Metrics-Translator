/**
 * Context Status Indicator Component
 * Provides visual feedback for context save/load states
 */

class ContextStatusIndicator {
    constructor() {
        this.indicator = null;
        this.statusTimeout = null;
        this.init();
    }

    init() {
        this.createIndicator();
        this.setupEventListeners();
    }

    createIndicator() {
        // Create the status indicator element
        this.indicator = document.createElement('div');
        this.indicator.id = 'context-status-indicator';
        this.indicator.className = 'context-status-indicator';
        this.indicator.innerHTML = `
            <div class="status-icon">
                <svg class="status-svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M12 6v6l4 2"></path>
                </svg>
            </div>
            <div class="status-text">Context Ready</div>
            <div class="status-details"></div>
        `;

        // Add to page
        document.body.appendChild(this.indicator);

        // Position it in the top-right corner
        this.setPosition('top-right');
    }

    setPosition(position = 'top-right') {
        const positions = {
            'top-right': { top: '20px', right: '20px', left: 'auto', bottom: 'auto' },
            'top-left': { top: '20px', left: '20px', right: 'auto', bottom: 'auto' },
            'bottom-right': { bottom: '20px', right: '20px', top: 'auto', left: 'auto' },
            'bottom-left': { bottom: '20px', left: '20px', top: 'auto', right: 'auto' }
        };

        const pos = positions[position] || positions['top-right'];
        Object.assign(this.indicator.style, pos);
    }

    showStatus(type, message, details = '', duration = 3000) {
        if (!this.indicator) return;

        // Clear any existing timeout
        if (this.statusTimeout) {
            clearTimeout(this.statusTimeout);
        }

        // Update indicator content
        const icon = this.indicator.querySelector('.status-icon svg');
        const text = this.indicator.querySelector('.status-text');
        const detailsEl = this.indicator.querySelector('.status-details');

        text.textContent = message;
        detailsEl.textContent = details;

        // Update icon and styling based on type
        this.updateIconAndStyle(type, icon);

        // Show indicator
        this.indicator.classList.remove('hidden');
        this.indicator.classList.add('visible', `status-${type}`);

        // Auto-hide after duration
        if (duration > 0) {
            this.statusTimeout = setTimeout(() => {
                this.hide();
            }, duration);
        }
    }

    updateIconAndStyle(type, icon) {
        // Remove all status classes
        this.indicator.classList.remove('status-saving', 'status-saved', 'status-loading', 'status-error', 'status-synced');

        switch (type) {
            case 'saving':
                icon.innerHTML = `
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M12 6v6l4 2" class="rotating"></path>
                `;
                break;
            case 'saved':
                icon.innerHTML = `
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="m9 12 2 2 4-4"></path>
                `;
                break;
            case 'loading':
                icon.innerHTML = `
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M12 2v10M12 14v8" class="rotating"></path>
                `;
                break;
            case 'error':
                icon.innerHTML = `
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="15" y1="9" x2="9" y2="15"></line>
                    <line x1="9" y1="9" x2="15" y2="15"></line>
                `;
                break;
            case 'synced':
                icon.innerHTML = `
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M8 12l2 2 4-4"></path>
                    <circle cx="18" cy="6" r="3"></circle>
                `;
                break;
            default:
                icon.innerHTML = `
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M12 6v6l4 2"></path>
                `;
        }
    }

    hide() {
        if (this.indicator) {
            this.indicator.classList.remove('visible');
            this.indicator.classList.add('hidden');
        }
    }

    show() {
        if (this.indicator) {
            this.indicator.classList.remove('hidden');
            this.indicator.classList.add('visible');
        }
    }

    updateContextStats(stats) {
        if (!stats) return;

        const details = [
            `${stats.selected_metrics || 0} metrics selected`,
            `${stats.contexts_count || 0} contexts saved`,
            `Session: ${stats.session_duration || 'Active'}`
        ].join(' • ');

        this.showStatus('synced', 'Context Synced', details, 0);
    }

    setupEventListeners() {
        // Listen for context manager events
        document.addEventListener('contextManager:contextInitialized', () => {
            this.showStatus('saved', 'Context Initialized', 'Session started');
        });

        document.addEventListener('contextManager:metricSelectionChanged', (event) => {
            const count = event.detail.selectedMetrics?.length || 0;
            this.showStatus('saving', 'Saving Selection...', `${count} metrics selected`);
            
            setTimeout(() => {
                this.showStatus('saved', 'Selection Saved', `${count} metrics selected`);
            }, 500);
        });

        document.addEventListener('contextManager:preferencesUpdated', () => {
            this.showStatus('saving', 'Saving Preferences...');
            
            setTimeout(() => {
                this.showStatus('saved', 'Preferences Saved');
            }, 300);
        });

        document.addEventListener('contextManager:metricSelectionsCleared', () => {
            this.showStatus('saved', 'Selections Cleared', 'All metrics deselected');
        });

        // Listen for page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.showStatus('loading', 'Syncing Context...');
                
                // Simulate context sync
                setTimeout(() => {
                    this.showStatus('synced', 'Context Synced');
                }, 800);
            }
        });

        // Make indicator clickable to show detailed status
        this.indicator.addEventListener('click', () => {
            this.showDetailedStatus();
        });
    }

    async showDetailedStatus() {
        try {
            // Get current context stats
            const stats = await window.contextManager?.getSessionStats();
            
            if (stats) {
                this.updateContextStats(stats);
            } else {
                this.showStatus('error', 'Context Unavailable', 'Failed to load context data');
            }
        } catch (error) {
            console.error('Error getting context stats:', error);
            this.showStatus('error', 'Context Error', 'Failed to sync context');
        }
    }

    // Public methods for manual status updates
    showSaving(message = 'Saving...', details = '') {
        this.showStatus('saving', message, details);
    }

    showSaved(message = 'Saved', details = '') {
        this.showStatus('saved', message, details);
    }

    showLoading(message = 'Loading...', details = '') {
        this.showStatus('loading', message, details);
    }

    showError(message = 'Error', details = '') {
        this.showStatus('error', message, details);
    }

    showSynced(message = 'Synced', details = '') {
        this.showStatus('synced', message, details);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.contextStatusIndicator = new ContextStatusIndicator();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ContextStatusIndicator;
}
