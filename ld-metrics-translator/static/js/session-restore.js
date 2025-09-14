/**
 * Session Restore Component
 * Handles restoring previous user sessions and context state
 */

class SessionRestore {
    constructor() {
        this.restoreModal = null;
        this.availableSessions = [];
        this.currentSession = null;
        this.init();
    }

    init() {
        this.createRestoreModal();
        this.setupEventListeners();
        this.checkForPreviousSessions();
    }

    createRestoreModal() {
        // Create modal for session restore
        this.restoreModal = document.createElement('div');
        this.restoreModal.id = 'session-restore-modal';
        this.restoreModal.className = 'session-restore-modal hidden';
        this.restoreModal.innerHTML = `
            <div class="modal-overlay" onclick="sessionRestore.hideRestoreModal()"></div>
            <div class="modal-content">
                <div class="modal-header">
                    <h3>
                        <i class="fas fa-history"></i>
                        Restore Previous Session
                    </h3>
                    <button class="modal-close" onclick="sessionRestore.hideRestoreModal()">×</button>
                </div>
                
                <div class="modal-body">
                    <div class="session-restore-intro">
                        <p>We found previous sessions with saved context. Would you like to restore one?</p>
                    </div>
                    
                    <div id="sessions-list" class="sessions-list">
                        <!-- Sessions will be populated here -->
                    </div>
                    
                    <div class="restore-options">
                        <div class="option-group">
                            <label>
                                <input type="checkbox" id="restore-selections" checked>
                                Restore metric selections
                            </label>
                        </div>
                        <div class="option-group">
                            <label>
                                <input type="checkbox" id="restore-preferences" checked>
                                Restore user preferences
                            </label>
                        </div>
                        <div class="option-group">
                            <label>
                                <input type="checkbox" id="restore-search-history">
                                Restore search history
                            </label>
                        </div>
                    </div>
                </div>
                
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="sessionRestore.hideRestoreModal()">
                        Start Fresh
                    </button>
                    <button class="btn btn-primary" onclick="sessionRestore.restoreSelectedSession()" disabled id="restore-btn">
                        Restore Session
                    </button>
                </div>
            </div>
        `;

        document.body.appendChild(this.restoreModal);
    }

    async checkForPreviousSessions() {
        try {
            // Check localStorage for recent sessions
            const recentSessions = this.getRecentSessionsFromStorage();
            
            // Check server for session history if authenticated
            const serverSessions = await this.getServerSessions();
            
            // Combine and deduplicate sessions
            this.availableSessions = this.mergeSessions(recentSessions, serverSessions);
            
            // Show restore modal if sessions are available
            if (this.availableSessions.length > 0) {
                this.showRestoreModal();
            }
            
        } catch (error) {
            console.error('Error checking for previous sessions:', error);
        }
    }

    getRecentSessionsFromStorage() {
        try {
            const sessions = [];
            const keys = Object.keys(localStorage);
            
            // Look for session data in localStorage
            keys.forEach(key => {
                if (key.startsWith('ld_session_')) {
                    try {
                        const sessionData = JSON.parse(localStorage.getItem(key));
                        if (sessionData && sessionData.timestamp) {
                            sessions.push({
                                id: key,
                                type: 'local',
                                timestamp: sessionData.timestamp,
                                data: sessionData,
                                source: 'Local Storage'
                            });
                        }
                    } catch (e) {
                        // Skip invalid session data
                    }
                }
            });
            
            // Sort by timestamp (newest first)
            return sessions.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            
        } catch (error) {
            console.error('Error getting sessions from storage:', error);
            return [];
        }
    }

    async getServerSessions() {
        try {
            const response = await fetch('/api/context/recent-sessions', {
                headers: {
                    'X-Session-ID': window.contextManager?.sessionId
                }
            });

            if (response.ok) {
                const data = await response.json();
                return data.sessions?.map(session => ({
                    id: session.session_id,
                    type: 'server',
                    timestamp: session.last_activity,
                    data: session,
                    source: 'Server'
                })) || [];
            }
            
            return [];
            
        } catch (error) {
            console.error('Error getting server sessions:', error);
            return [];
        }
    }

    mergeSessions(localSessions, serverSessions) {
        const allSessions = [...localSessions, ...serverSessions];
        const uniqueSessions = [];
        const seenIds = new Set();

        // Remove duplicates and limit to last 5 sessions
        allSessions.forEach(session => {
            if (!seenIds.has(session.id) && uniqueSessions.length < 5) {
                seenIds.add(session.id);
                uniqueSessions.push(session);
            }
        });

        return uniqueSessions.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    }

    showRestoreModal() {
        this.populateSessionsList();
        this.restoreModal.classList.remove('hidden');
        this.restoreModal.classList.add('visible');
    }

    hideRestoreModal() {
        this.restoreModal.classList.remove('visible');
        this.restoreModal.classList.add('hidden');
    }

    populateSessionsList() {
        const sessionsList = document.getElementById('sessions-list');
        if (!sessionsList) return;

        if (this.availableSessions.length === 0) {
            sessionsList.innerHTML = `
                <div class="no-sessions">
                    <div class="no-sessions-icon">📝</div>
                    <p>No previous sessions found</p>
                </div>
            `;
            return;
        }

        const sessionsHTML = this.availableSessions.map((session, index) => {
            const date = new Date(session.timestamp);
            const timeAgo = this.getTimeAgo(date);
            const sessionInfo = this.getSessionInfo(session);

            return `
                <div class="session-item ${index === 0 ? 'selected' : ''}" 
                     data-session-id="${session.id}" 
                     onclick="sessionRestore.selectSession('${session.id}')">
                    <div class="session-header">
                        <div class="session-title">
                            <i class="fas fa-clock"></i>
                            Session from ${timeAgo}
                        </div>
                        <div class="session-source">${session.source}</div>
                    </div>
                    <div class="session-details">
                        <div class="session-stats">
                            ${sessionInfo.metrics ? `<span class="stat">${sessionInfo.metrics} metrics</span>` : ''}
                            ${sessionInfo.searches ? `<span class="stat">${sessionInfo.searches} searches</span>` : ''}
                            ${sessionInfo.preferences ? `<span class="stat">Custom preferences</span>` : ''}
                        </div>
                        <div class="session-date">${date.toLocaleDateString()} ${date.toLocaleTimeString()}</div>
                    </div>
                </div>
            `;
        }).join('');

        sessionsList.innerHTML = sessionsHTML;

        // Enable restore button if a session is selected
        const restoreBtn = document.getElementById('restore-btn');
        if (restoreBtn && this.availableSessions.length > 0) {
            restoreBtn.disabled = false;
        }
    }

    getSessionInfo(session) {
        const info = {
            metrics: 0,
            searches: 0,
            preferences: false
        };

        try {
            if (session.type === 'local') {
                info.metrics = session.data.selectedMetrics?.length || 0;
                info.searches = session.data.searchHistory?.length || 0;
                info.preferences = Object.keys(session.data.preferences || {}).length > 0;
            } else if (session.type === 'server') {
                info.metrics = session.data.contexts_count || 0;
                info.searches = session.data.search_count || 0;
                info.preferences = session.data.has_preferences || false;
            }
        } catch (error) {
            console.error('Error parsing session info:', error);
        }

        return info;
    }

    getTimeAgo(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 60) {
            return `${diffMins} minutes ago`;
        } else if (diffHours < 24) {
            return `${diffHours} hours ago`;
        } else if (diffDays < 7) {
            return `${diffDays} days ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    selectSession(sessionId) {
        // Remove previous selection
        document.querySelectorAll('.session-item').forEach(item => {
            item.classList.remove('selected');
        });

        // Select new session
        const sessionElement = document.querySelector(`[data-session-id="${sessionId}"]`);
        if (sessionElement) {
            sessionElement.classList.add('selected');
            this.currentSession = this.availableSessions.find(s => s.id === sessionId);
        }
    }

    async restoreSelectedSession() {
        if (!this.currentSession) {
            // Default to first session if none selected
            this.currentSession = this.availableSessions[0];
        }

        if (!this.currentSession) {
            console.error('No session selected for restore');
            return;
        }

        try {
            // Show loading state
            const restoreBtn = document.getElementById('restore-btn');
            if (restoreBtn) {
                restoreBtn.disabled = true;
                restoreBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Restoring...';
            }

            // Get restore options
            const restoreSelections = document.getElementById('restore-selections')?.checked;
            const restorePreferences = document.getElementById('restore-preferences')?.checked;
            const restoreSearchHistory = document.getElementById('restore-search-history')?.checked;

            // Show status
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showLoading('Restoring Session...', 'Loading previous context');
            }

            // Restore session data
            await this.performRestore(this.currentSession, {
                selections: restoreSelections,
                preferences: restorePreferences,
                searchHistory: restoreSearchHistory
            });

            // Hide modal
            this.hideRestoreModal();

            // Show success
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showSaved('Session Restored', 'Previous context loaded successfully');
            }

            // Refresh page to apply restored context
            setTimeout(() => {
                window.location.reload();
            }, 1000);

        } catch (error) {
            console.error('Error restoring session:', error);
            
            if (window.contextStatusIndicator) {
                window.contextStatusIndicator.showError('Restore Failed', 'Could not restore previous session');
            }

            // Reset button
            const restoreBtn = document.getElementById('restore-btn');
            if (restoreBtn) {
                restoreBtn.disabled = false;
                restoreBtn.innerHTML = 'Restore Session';
            }
        }
    }

    async performRestore(session, options) {
        const restoredData = {
            restored: true,
            timestamp: new Date().toISOString(),
            source: session.source
        };

        if (session.type === 'local') {
            // Restore from local storage
            if (options.preferences && session.data.preferences) {
                await window.contextManager?.updatePreferences(session.data.preferences);
                restoredData.preferences = session.data.preferences;
            }

            if (options.selections && session.data.selectedMetrics) {
                // Restore metric selections
                for (const metric of session.data.selectedMetrics) {
                    await window.contextManager?.selectMetric(metric.metric_id, 'restored');
                }
                restoredData.selectedMetrics = session.data.selectedMetrics;
            }

            if (options.searchHistory && session.data.searchHistory) {
                // Store search history in context
                await window.contextManager?.storeContext('search', 'restored_history', session.data.searchHistory);
                restoredData.searchHistory = session.data.searchHistory;
            }

        } else if (session.type === 'server') {
            // Restore from server session
            const response = await fetch('/api/context/restore-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Session-ID': window.contextManager?.sessionId
                },
                body: JSON.stringify({
                    session_id: session.id,
                    restore_options: options
                })
            });

            if (!response.ok) {
                throw new Error('Failed to restore server session');
            }

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Session restore failed');
            }

            restoredData.serverData = data;
        }

        // Store restore information
        localStorage.setItem('ld_session_restored', JSON.stringify(restoredData));
        
        return restoredData;
    }

    setupEventListeners() {
        // Listen for page load to check for restored sessions
        document.addEventListener('DOMContentLoaded', () => {
            this.checkForRestoredSession();
        });

        // Listen for context manager initialization
        document.addEventListener('contextManager:contextInitialized', () => {
            // Delay check to allow context manager to fully initialize
            setTimeout(() => {
                this.checkForPreviousSessions();
            }, 1000);
        });
    }

    checkForRestoredSession() {
        try {
            const restored = localStorage.getItem('ld_session_restored');
            if (restored) {
                const restoredData = JSON.parse(restored);
                
                // Show notification about restored session
                if (window.contextStatusIndicator) {
                    window.contextStatusIndicator.showSynced(
                        'Session Restored', 
                        `From ${restoredData.source} • ${new Date(restoredData.timestamp).toLocaleTimeString()}`
                    );
                }

                // Clear the restore flag
                localStorage.removeItem('ld_session_restored');
            }
        } catch (error) {
            console.error('Error checking for restored session:', error);
        }
    }

    // Public method to manually trigger session restore
    showRestoreDialog() {
        this.checkForPreviousSessions();
    }

    // Save current session for future restore
    async saveCurrentSession() {
        try {
            const sessionData = {
                timestamp: new Date().toISOString(),
                preferences: window.contextManager?.getPreferences() || {},
                selectedMetrics: await window.contextManager?.getSelectedMetrics() || [],
                searchHistory: await window.contextManager?.getContext('search', 'history') || [],
                page: window.location.pathname,
                url: window.location.href
            };

            const sessionKey = `ld_session_${Date.now()}`;
            localStorage.setItem(sessionKey, JSON.stringify(sessionData));

            // Clean up old sessions (keep only last 3)
            this.cleanupOldSessions();

            return sessionKey;
        } catch (error) {
            console.error('Error saving current session:', error);
            return null;
        }
    }

    cleanupOldSessions() {
        try {
            const sessionKeys = Object.keys(localStorage)
                .filter(key => key.startsWith('ld_session_'))
                .sort()
                .reverse(); // Newest first

            // Keep only the 3 most recent sessions
            sessionKeys.slice(3).forEach(key => {
                localStorage.removeItem(key);
            });
        } catch (error) {
            console.error('Error cleaning up old sessions:', error);
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.sessionRestore = new SessionRestore();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SessionRestore;
}
