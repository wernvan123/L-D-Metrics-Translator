/**
 * Context Management System for L&D Metrics Translator
 * Handles authentication-aware context storage, event analysis history, and UI state management
 */

class ContextManager {
    constructor() {
        this.isAuthenticated = false;
        this.adminUserId = null;
        this.adminUsername = null;
        this.sessionId = null;
        this.eventAnalysisHistory = [];
        this.selectedMetrics = [];
        
        // Initialize on page load
        this.init();
    }

    async init() {
        try {
            // Initialize context and check authentication status
            await this.initializeContext();
            await this.checkAuthStatus();
            
            // Setup UI based on authentication
            this.setupUI();
            
            // Load event analysis history
            await this.loadEventAnalysisHistory();
            
            // Setup event listeners
            this.setupEventListeners();
            
            console.log('Context Manager initialized successfully');
        } catch (error) {
            console.error('Failed to initialize Context Manager:', error);
        }
    }

    async initializeContext() {
        try {
            const response = await fetch('/api/context/initialize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    page: 'dashboard',
                    preferences: {
                        theme: 'light',
                        auto_save_selections: true
                    }
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.sessionId = data.session?.session_id;
                console.log('Context initialized:', data);
            }
        } catch (error) {
            console.error('Failed to initialize context:', error);
        }
    }

    async checkAuthStatus() {
        try {
            const response = await fetch('/api/context/auth-status');
            if (response.ok) {
                const data = await response.json();
                this.isAuthenticated = data.is_authenticated;
                this.adminUserId = data.admin_user_id;
                this.adminUsername = data.admin_username;
                this.sessionId = data.session_id;
                
                console.log('Auth status:', {
                    authenticated: this.isAuthenticated,
                    username: this.adminUsername
                });
            }
        } catch (error) {
            console.error('Failed to check auth status:', error);
        }
    }

    setupUI() {
        const loginPrompt = document.getElementById('login-prompt');
        const pastSearchesContainer = document.getElementById('past-searches-container');
        const clearHistoryBtn = document.getElementById('clear-history-btn');

        // If guest mode is active, ensure login prompt is hidden regardless of auth flag
        let isGuestMode = false;
        try {
            isGuestMode = sessionStorage.getItem('guestMode') === 'true';
        } catch (e) {
            // ignore storage errors
        }

        if (isGuestMode && loginPrompt) {
            loginPrompt.style.display = 'none';
        }

        if (this.isAuthenticated) {
            // Hide login prompt for authenticated users
            if (loginPrompt) {
                loginPrompt.style.display = 'none';
            }
            
            // Show clear history button for authenticated users
            if (clearHistoryBtn) {
                clearHistoryBtn.style.display = 'inline-flex';
            }
            
            // Update UI to show authenticated state
            this.updateAuthenticatedUI();
        } else {
            // Show login prompt for anonymous users
            if (loginPrompt && !isGuestMode) {
                loginPrompt.style.display = 'block';
            }
            
            // Hide clear history button for anonymous users
            if (clearHistoryBtn) {
                clearHistoryBtn.style.display = 'none';
            }
        }

        // Always show past searches container
        if (pastSearchesContainer) {
            pastSearchesContainer.style.display = 'block';
        }
    }

    updateAuthenticatedUI() {
        // Update login prompt to show authenticated state
        const loginPrompt = document.getElementById('login-prompt');
        if (loginPrompt && this.isAuthenticated) {
            loginPrompt.innerHTML = `
                <div class="login-prompt-content authenticated">
                    <div class="login-prompt-icon">✅</div>
                    <div class="login-prompt-text">
                        <h4>Welcome back, ${this.adminUsername}!</h4>
                        <p>Your analysis history is saved and personalized recommendations are enabled</p>
                    </div>
                    <div class="login-prompt-actions">
                        <a href="/admin/logout" class="btn btn-outline">Logout</a>
                        <a href="/admin/dashboard" class="btn btn-secondary">Admin Panel</a>
                    </div>
                </div>
            `;
            loginPrompt.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                if (loginPrompt) {
                    loginPrompt.style.display = 'none';
                }
            }, 5000);
        }
    }

    setupEventListeners() {
        // Character counter for event description
        const eventDescription = document.getElementById('event-description');
        const charCount = document.getElementById('char-count');
        
        if (eventDescription && charCount) {
            eventDescription.addEventListener('input', (e) => {
                const count = e.target.value.length;
                charCount.textContent = count;
                
                // Update character counter color based on usage
                if (count > 450) {
                    charCount.style.color = '#e74c3c';
                } else if (count > 350) {
                    charCount.style.color = '#f39c12';
                } else {
                    charCount.style.color = '#7f8c8d';
                }
            });
        }

        // Continue as anonymous button
        const continueAnonymousBtn = document.getElementById('continue-anonymous');
        if (continueAnonymousBtn) {
            continueAnonymousBtn.addEventListener('click', () => {
                const loginPrompt = document.getElementById('login-prompt');
                if (loginPrompt) {
                    loginPrompt.style.display = 'none';
                }
            });
        }

        // Clear history button
        const clearHistoryBtn = document.getElementById('clear-history-btn');
        if (clearHistoryBtn) {
            clearHistoryBtn.addEventListener('click', () => {
                this.clearEventAnalysisHistory();
            });
        }

        // Analyze event button
        const analyzeEventBtn = document.getElementById('analyze-event-btn');
        if (analyzeEventBtn) {
            analyzeEventBtn.addEventListener('click', () => {
                this.analyzeEvent();
            });
        }

        // Show suggestions button is handled by event-analysis.js

        // Suggestion items
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('suggestion-item')) {
                const suggestion = e.target.getAttribute('data-suggestion');
                if (suggestion && eventDescription) {
                    eventDescription.value = suggestion;
                    eventDescription.dispatchEvent(new Event('input'));
                    this.hideSuggestions();
                }
            }
        });

        // Past search items
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('past-search-item')) {
                const searchData = JSON.parse(e.target.getAttribute('data-search'));
                if (searchData && eventDescription) {
                    eventDescription.value = searchData.event_description;
                    eventDescription.dispatchEvent(new Event('input'));
                    
                    // Show previous analysis if available
                    if (searchData.analysis_result) {
                        this.displayAnalysisResults(searchData.analysis_result, searchData.event_description);
                    }
                }
            }
        });
    }

    async analyzeEvent() {
        const eventDescription = document.getElementById('event-description');
        const analyzeBtn = document.getElementById('analyze-event-btn');
        const loadingDiv = document.getElementById('analysis-loading');
        const resultsDiv = document.getElementById('analysis-results');

        if (!eventDescription || !eventDescription.value.trim()) {
            this.showError('Please enter an event description to analyze.');
            return;
        }

        const description = eventDescription.value.trim();

        try {
            // Show loading state
            if (loadingDiv) loadingDiv.style.display = 'block';
            if (resultsDiv) resultsDiv.style.display = 'none';
            if (analyzeBtn) {
                analyzeBtn.disabled = true;
                analyzeBtn.textContent = 'Analyzing...';
            }

            // Call the existing event analysis API
            const response = await fetch('/api/analyze-event', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    event_description: description
                })
            });

            const data = await response.json();

            if (data.success) {
                // Store the analysis in context-aware storage
                await this.storeEventAnalysis(description, data.analysis, 'ai_model', true);
                
                // Display results
                this.displayAnalysisResults(data.analysis, description);
                
                // Reload history to show new analysis
                await this.loadEventAnalysisHistory();
            } else {
                // Store failed analysis
                await this.storeEventAnalysis(description, '', 'ai_model', false, data.error);
                this.showError(data.error || 'Analysis failed. Please try again.');
            }

        } catch (error) {
            console.error('Analysis error:', error);
            await this.storeEventAnalysis(description, '', 'ai_model', false, error.message);
            this.showError('Network error. Please check your connection and try again.');
        } finally {
            // Reset UI state
            if (loadingDiv) loadingDiv.style.display = 'none';
            if (analyzeBtn) {
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M9 11H1l6-6v4h4v2z"></path>
                        <path d="M15 13h8l-6 6v-4h-4v-2z"></path>
                    </svg>
                    Analyze Event
                `;
            }
        }
    }

    async storeEventAnalysis(eventDescription, analysisResult, generatedBy = 'ai_model', success = true, errorMessage = null) {
        try {
            const response = await fetch('/api/context/event-analysis/store', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    event_description: eventDescription,
                    analysis_result: analysisResult,
                    generated_by: generatedBy,
                    success: success,
                    error_message: errorMessage
                })
            });

            if (response.ok) {
                const data = await response.json();
                console.log('Event analysis stored:', data);
                return data;
            }
        } catch (error) {
            console.error('Failed to store event analysis:', error);
        }
    }

    async loadEventAnalysisHistory() {
        try {
            const response = await fetch('/api/context/event-analysis/history?limit=5');
            if (response.ok) {
                const data = await response.json();
                this.eventAnalysisHistory = data.history || [];
                this.displayEventAnalysisHistory();
                console.log('Event analysis history loaded:', data);
            }
        } catch (error) {
            console.error('Failed to load event analysis history:', error);
        }
    }

    displayEventAnalysisHistory() {
        const pastSearchesList = document.getElementById('past-searches-list');
        const pastSearchesEmpty = document.getElementById('past-searches-empty');
        const pastSearchesContainer = document.getElementById('past-searches-container');

        if (!pastSearchesList) return;

        if (this.eventAnalysisHistory.length === 0) {
            pastSearchesList.innerHTML = '';
            if (pastSearchesEmpty) pastSearchesEmpty.style.display = 'block';
            return;
        }

        if (pastSearchesEmpty) pastSearchesEmpty.style.display = 'none';

        const historyHTML = this.eventAnalysisHistory.map(analysis => {
            const date = new Date(analysis.created_date).toLocaleDateString();
            const time = new Date(analysis.created_date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            
            return `
                <div class="past-search-item" data-search='${JSON.stringify(analysis)}'>
                    <div class="past-search-content">
                        <div class="past-search-description">
                            ${analysis.truncated_description || analysis.event_description}
                        </div>
                        <div class="past-search-meta">
                            <span class="past-search-date">${date} ${time}</span>
                            <span class="past-search-status ${analysis.success ? 'success' : 'error'}">
                                ${analysis.success ? '✅' : '❌'}
                            </span>
                        </div>
                    </div>
                    <div class="past-search-actions">
                        <button class="btn btn-sm btn-outline" onclick="contextManager.rerunAnalysis('${analysis.id}')">
                            Rerun
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        pastSearchesList.innerHTML = historyHTML;

        // Show the container
        if (pastSearchesContainer) {
            pastSearchesContainer.style.display = 'block';
        }
    }

    async clearEventAnalysisHistory() {
        if (!confirm('Are you sure you want to clear your analysis history? This action cannot be undone.')) {
            return;
        }

        try {
            const response = await fetch('/api/context/event-analysis/clear', {
                method: 'DELETE'
            });

            if (response.ok) {
                this.eventAnalysisHistory = [];
                this.displayEventAnalysisHistory();
                this.showSuccess('Analysis history cleared successfully.');
            } else {
                this.showError('Failed to clear analysis history.');
            }
        } catch (error) {
            console.error('Failed to clear event analysis history:', error);
            this.showError('Network error. Please try again.');
        }
    }

    async rerunAnalysis(analysisId) {
        const analysis = this.eventAnalysisHistory.find(a => a.id == analysisId);
        if (analysis) {
            const eventDescription = document.getElementById('event-description');
            if (eventDescription) {
                eventDescription.value = analysis.event_description;
                eventDescription.dispatchEvent(new Event('input'));
            }
            await this.analyzeEvent();
        }
    }

    displayAnalysisResults(analysisResult, eventDescription) {
        const resultsDiv = document.getElementById('analysis-results');
        const contentDiv = document.getElementById('analysis-content');

        if (!resultsDiv || !contentDiv) return;

        contentDiv.innerHTML = `
            <div class="analysis-result-content">
                <div class="analysis-input-summary">
                    <h4>📝 Your Event Description</h4>
                    <p class="event-summary">${eventDescription}</p>
                </div>
                <div class="analysis-output">
                    <h4>🎯 AI Analysis & Recommendations</h4>
                    <div class="analysis-text">${this.formatAnalysisResult(analysisResult)}</div>
                </div>
                <div class="analysis-actions">
                    <button class="btn btn-primary" onclick="contextManager.saveAnalysisToReport()">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                            <polyline points="17,21 17,13 7,13 7,21"></polyline>
                            <polyline points="7,3 7,8 15,8"></polyline>
                        </svg>
                        Save to Report
                    </button>
                    <button class="btn btn-secondary" onclick="contextManager.shareAnalysis()">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="18" cy="5" r="3"></circle>
                            <circle cx="6" cy="12" r="3"></circle>
                            <circle cx="18" cy="19" r="3"></circle>
                            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                        </svg>
                        Share
                    </button>
                </div>
            </div>
        `;

        resultsDiv.style.display = 'block';
        resultsDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    formatAnalysisResult(result) {
        // Convert markdown-like formatting to HTML
        return result
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>');
    }

    toggleSuggestions() {
        const suggestionsDiv = document.getElementById('event-suggestions');
        const showBtn = document.getElementById('show-suggestions-btn');

        if (!suggestionsDiv || !showBtn) return;

        if (suggestionsDiv.style.display === 'none' || !suggestionsDiv.style.display) {
            suggestionsDiv.style.display = 'block';
            showBtn.textContent = 'Hide Examples';
        } else {
            suggestionsDiv.style.display = 'none';
            showBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24"></path>
                </svg>
                Show Examples
            `;
        }
    }

    hideSuggestions() {
        const suggestionsDiv = document.getElementById('event-suggestions');
        const showBtn = document.getElementById('show-suggestions-btn');

        if (suggestionsDiv) {
            suggestionsDiv.style.display = 'none';
        }
        
        if (showBtn) {
            showBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24"></path>
                </svg>
                Show Examples
            `;
        }
    }

    saveAnalysisToReport() {
        // Placeholder for save to report functionality
        this.showSuccess('Analysis saved to report! (Feature coming soon)');
    }

    shareAnalysis() {
        // Placeholder for share functionality
        this.showSuccess('Share link copied to clipboard! (Feature coming soon)');
    }

    showError(message) {
        // Create or update error notification
        this.showNotification(message, 'error');
    }

    showSuccess(message) {
        // Create or update success notification
        this.showNotification(message, 'success');
    }

    showNotification(message, type = 'info') {
        // Remove existing notifications
        const existingNotification = document.querySelector('.context-notification');
        if (existingNotification) {
            existingNotification.remove();
        }

        // Create notification element
        const notification = document.createElement('div');
        notification.className = `context-notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">
                    ${type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️'}
                </span>
                <span class="notification-message">${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
            </div>
        `;

        // Add to page
        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

// Initialize context manager when DOM is loaded
let contextManager;
document.addEventListener('DOMContentLoaded', () => {
    contextManager = new ContextManager();
});

// Export for global access
window.contextManager = contextManager;
