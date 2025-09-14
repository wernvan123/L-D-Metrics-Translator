/**
 * Context Manager for L&D Metrics Translator Frontend
 * Handles session management, context storage, and metric selections
 */

class ContextManager {
    constructor() {
        this.sessionId = null;
        this.apiBase = '/api/context';
        this.initialized = false;
        this.preferences = {};
        this.selectedMetrics = [];
        this.eventListeners = [];
        
        // Initialize on page load
        this.init();
    }

    /**
     * Initialize context manager
     */
    async init() {
        try {
            // Get or generate session ID
            this.sessionId = this.getSessionId();
            
            // Initialize context with the backend
            await this.initializeContext();
            
            // Set up event listeners
            this.setupEventListeners();
            
            this.initialized = true;
            console.log('Context Manager initialized successfully');
            
            // Dispatch initialization event
            this.dispatchEvent('contextInitialized', {
                sessionId: this.sessionId,
                preferences: this.preferences,
                selectedMetrics: this.selectedMetrics
            });
            
        } catch (error) {
            console.error('Failed to initialize Context Manager:', error);
        }
    }

    /**
     * Get or generate session ID
     */
    getSessionId() {
        // Try to get from localStorage first
        let sessionId = localStorage.getItem('ld_session_id');
        
        if (!sessionId) {
            // Generate new session ID
            sessionId = 'sess_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('ld_session_id', sessionId);
        }
        
        return sessionId;
    }

    /**
     * Initialize context with backend
     */
    async initializeContext() {
        try {
            const response = await fetch(`${this.apiBase}/initialize`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.sessionId
                },
                body: JSON.stringify({
                    page: this.getCurrentPage(),
                    preferences: this.getStoredPreferences()
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.preferences = data.preferences || {};
                    this.selectedMetrics = data.selected_metrics || [];
                    
                    // Store preferences locally
                    localStorage.setItem('ld_preferences', JSON.stringify(this.preferences));
                    
                    return data;
                }
            }
            
            throw new Error('Failed to initialize context');
            
        } catch (error) {
            console.error('Context initialization error:', error);
            // Fall back to local storage
            this.preferences = this.getStoredPreferences();
            this.selectedMetrics = [];
        }
    }

    /**
     * Get current page identifier
     */
    getCurrentPage() {
        const path = window.location.pathname;
        if (path === '/' || path === '/index.html') return 'home';
        if (path.includes('admin')) return 'admin';
        if (path.includes('dashboard')) return 'dashboard';
        return 'unknown';
    }

    /**
     * Get stored preferences from localStorage
     */
    getStoredPreferences() {
        try {
            const stored = localStorage.getItem('ld_preferences');
            return stored ? JSON.parse(stored) : {};
        } catch (error) {
            console.error('Error parsing stored preferences:', error);
            return {};
        }
    }

    /**
     * Store context data
     */
    async storeContext(contextType, contextKey, contextData, expiresInHours = 24) {
        try {
            const response = await fetch(`${this.apiBase}/store`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.sessionId
                },
                body: JSON.stringify({
                    context_type: contextType,
                    context_key: contextKey,
                    context_data: contextData,
                    expires_in_hours: expiresInHours
                })
            });

            if (response.ok) {
                const data = await response.json();
                return data.success;
            }
            
            return false;
            
        } catch (error) {
            console.error('Error storing context:', error);
            return false;
        }
    }

    /**
     * Get context data
     */
    async getContext(contextType, contextKey) {
        try {
            const response = await fetch(`${this.apiBase}/get/${contextType}/${contextKey}`, {
                headers: {
                    'X-Session-ID': this.sessionId
                }
            });

            if (response.ok) {
                const data = await response.json();
                return data.success ? data.context_data : null;
            }
            
            return null;
            
        } catch (error) {
            console.error('Error getting context:', error);
            return null;
        }
    }

    /**
     * Store search context
     */
    async storeSearchContext(query, filters, resultsCount) {
        const searchData = {
            query: query,
            filters: filters,
            results_count: resultsCount,
            timestamp: new Date().toISOString(),
            page: this.getCurrentPage()
        };
        
        return await this.storeContext('search', 'last_search', searchData);
    }

    /**
     * Select/deselect a metric
     */
    async selectMetric(metricId, selectionType = 'manual', contextTags = []) {
        try {
            const response = await fetch(`${this.apiBase}/metrics/select`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.sessionId
                },
                body: JSON.stringify({
                    metric_id: metricId,
                    selection_type: selectionType,
                    context_tags: contextTags
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Update local state
                    await this.refreshSelectedMetrics();
                    
                    // Dispatch event
                    this.dispatchEvent('metricSelectionChanged', {
                        metricId: metricId,
                        selected: data.selected,
                        action: data.action,
                        selectedMetrics: this.selectedMetrics
                    });
                    
                    return data;
                }
            }
            
            throw new Error('Failed to select metric');
            
        } catch (error) {
            console.error('Error selecting metric:', error);
            return null;
        }
    }

    /**
     * Get selected metrics
     */
    async getSelectedMetrics() {
        try {
            const response = await fetch(`${this.apiBase}/metrics/selected`, {
                headers: {
                    'X-Session-ID': this.sessionId
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.selectedMetrics = data.selected_metrics;
                    return this.selectedMetrics;
                }
            }
            
            return [];
            
        } catch (error) {
            console.error('Error getting selected metrics:', error);
            return [];
        }
    }

    /**
     * Refresh selected metrics from server
     */
    async refreshSelectedMetrics() {
        this.selectedMetrics = await this.getSelectedMetrics();
        return this.selectedMetrics;
    }

    /**
     * Update user preferences
     */
    async updatePreferences(newPreferences) {
        try {
            // Merge with existing preferences
            this.preferences = { ...this.preferences, ...newPreferences };
            
            // Store locally
            localStorage.setItem('ld_preferences', JSON.stringify(this.preferences));
            
            // Send to server
            const response = await fetch(`${this.apiBase}/preferences`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': this.sessionId
                },
                body: JSON.stringify(this.preferences)
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Dispatch event
                    this.dispatchEvent('preferencesUpdated', {
                        preferences: this.preferences
                    });
                    
                    return true;
                }
            }
            
            return false;
            
        } catch (error) {
            console.error('Error updating preferences:', error);
            return false;
        }
    }

    /**
     * Get user preferences
     */
    getPreferences() {
        return this.preferences;
    }

    /**
     * Get preference value with default
     */
    getPreference(key, defaultValue = null) {
        return this.preferences[key] !== undefined ? this.preferences[key] : defaultValue;
    }

    /**
     * Check if metric is selected
     */
    isMetricSelected(metricId) {
        return this.selectedMetrics.some(selection => 
            selection.metric_id === metricId && selection.is_active
        );
    }

    /**
     * Get count of selected metrics
     */
    getSelectedMetricsCount() {
        return this.selectedMetrics.filter(selection => selection.is_active).length;
    }

    /**
     * Set up event listeners for page interactions
     */
    setupEventListeners() {
        // Save context on page unload
        window.addEventListener('beforeunload', () => {
            this.savePageContext();
        });

        // Update activity on user interaction
        ['click', 'keypress', 'scroll'].forEach(eventType => {
            document.addEventListener(eventType, this.throttle(() => {
                this.updateActivity();
            }, 30000)); // Throttle to once per 30 seconds
        });

        // Handle visibility change
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.updateActivity();
            }
        });
    }

    /**
     * Save current page context
     */
    async savePageContext() {
        const pageContext = {
            page: this.getCurrentPage(),
            url: window.location.href,
            timestamp: new Date().toISOString(),
            scroll_position: window.pageYOffset,
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            }
        };
        
        await this.storeContext('page', 'last_state', pageContext, 1); // 1 hour expiry
    }

    /**
     * Update activity timestamp
     */
    async updateActivity() {
        // This could be implemented to ping the server to update last_activity
        // For now, we'll just update local timestamp
        this.lastActivity = new Date().toISOString();
    }

    /**
     * Throttle function execution
     */
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }

    /**
     * Add event listener
     */
    addEventListener(eventType, callback) {
        if (!this.eventListeners[eventType]) {
            this.eventListeners[eventType] = [];
        }
        this.eventListeners[eventType].push(callback);
    }

    /**
     * Remove event listener
     */
    removeEventListener(eventType, callback) {
        if (this.eventListeners[eventType]) {
            const index = this.eventListeners[eventType].indexOf(callback);
            if (index > -1) {
                this.eventListeners[eventType].splice(index, 1);
            }
        }
    }

    /**
     * Dispatch custom event
     */
    dispatchEvent(eventType, data) {
        // Call registered listeners
        if (this.eventListeners[eventType]) {
            this.eventListeners[eventType].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event listener for ${eventType}:`, error);
                }
            });
        }

        // Also dispatch as DOM event
        const customEvent = new CustomEvent(`contextManager:${eventType}`, {
            detail: data
        });
        document.dispatchEvent(customEvent);
    }

    /**
     * Get session statistics
     */
    async getSessionStats() {
        try {
            const response = await fetch(`${this.apiBase}/session`, {
                headers: {
                    'X-Session-ID': this.sessionId
                }
            });

            if (response.ok) {
                const data = await response.json();
                return data.success ? data : null;
            }
            
            return null;
            
        } catch (error) {
            console.error('Error getting session stats:', error);
            return null;
        }
    }

    /**
     * Clear all metric selections
     */
    async clearMetricSelections() {
        try {
            const response = await fetch(`${this.apiBase}/metrics/clear`, {
                method: 'DELETE',
                headers: {
                    'X-Session-ID': this.sessionId
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.selectedMetrics = [];
                    
                    this.dispatchEvent('metricSelectionsCleared', {
                        selectedMetrics: this.selectedMetrics
                    });
                    
                    return true;
                }
            }
            
            return false;
            
        } catch (error) {
            console.error('Error clearing metric selections:', error);
            return false;
        }
    }
}

// Create global instance
window.contextManager = new ContextManager();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ContextManager;
}
