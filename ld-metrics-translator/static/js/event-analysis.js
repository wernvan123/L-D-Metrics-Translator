/**
 * Event Analysis Module for L&D Metrics Translator
 * Provides AI-powered analysis of workplace events for L&D insights
 */

console.log('Event Analysis script loaded');

class EventAnalyzer {
    constructor() {
        // Input elements
        this.eventInput = document.getElementById('event-description');
        this.analyzeBtn = document.getElementById('analyze-event-btn');
        this.suggestionsBtn = document.getElementById('show-suggestions-btn');
        this.suggestionsContainer = document.getElementById('event-suggestions');
        
        // Results elements
        this.analysisResults = document.getElementById('analysis-results');
        this.analysisContent = document.getElementById('analysis-content');
        this.analysisLoading = document.getElementById('analysis-loading');
        this.clearAnalysisBtn = document.getElementById('clear-analysis');
        
        // Login elements
        this.loginPrompt = document.getElementById('login-prompt');
        this.analysisActions = document.getElementById('analysis-actions');
        this.loginModal = document.getElementById('login-modal');
        this.loginForm = document.getElementById('login-form');
        this.openLoginBtn = document.getElementById('open-login-btn');
        
        // Past searches elements
        this.pastSearchesContainer = document.getElementById('past-searches-container');
        this.pastSearchesList = document.getElementById('past-searches-list');
        
        // Auth state
        this.isAuthenticated = false;
        
        // Initialize the component
        if (this.eventInput) {
            this.init();
        } else {
            // Soft guard: skip initialization entirely on pages without Event Analysis UI
            console.info('EventAnalyzer: required elements not found. Skipping initialization on this page.');
            return;
        }
    }
    
    async checkAuthStatus() {
        try {
            // Check if we're in guest mode first
            const isGuestMode = sessionStorage.getItem('guestMode') === 'true';
            if (isGuestMode) {
                // Treat guest mode as authenticated for analysis purposes
                this.isAuthenticated = true;
                this.hideLoginPrompt();
                if (this.analysisActions) this.analysisActions.style.display = 'flex';
                return true;
            }
            
            const response = await fetch('/api/auth_status', {
                method: 'GET',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            this.isAuthenticated = data.authenticated === true;
            
            // Update UI based on auth state
            if (this.isAuthenticated) {
                this.hideLoginPrompt();
                // Clear guest mode if user is authenticated
                sessionStorage.removeItem('guestMode');
            } else {
                this.showLoginPrompt();
            }
            
            return this.isAuthenticated;
            
        } catch (error) {
            console.error('Error checking auth status:', error);
            this.isAuthenticated = false;
            // If there's an error, assume not authenticated and show login prompt
            this.showLoginPrompt();
            return false;
        }
    }
    
    showLoginPrompt() {
        console.log('showLoginPrompt called');
        const loginPrompt = document.getElementById('login-prompt');
        const analysisActions = document.getElementById('analysis-actions');
        
        console.log('Login prompt element:', loginPrompt);
        console.log('Analysis actions element:', analysisActions);
        
        if (loginPrompt) {
            console.log('Showing login prompt');
            loginPrompt.style.display = 'block';
            loginPrompt.style.visibility = 'visible';
            loginPrompt.style.opacity = '1';
        } else {
            console.error('Login prompt element not found!');
        }
        
        if (analysisActions) {
            console.log('Hiding analysis actions');
            analysisActions.style.display = 'none';
        }
        
        // Store the current scroll position
        sessionStorage.setItem('scrollPosition', window.scrollY);
        
        // Force a reflow/repaint to ensure the element is visible
        if (loginPrompt) {
            loginPrompt.offsetHeight;
        }
        
        console.log('Login prompt should now be visible');
    }
    
    hideLoginPrompt() {
        const loginPrompt = document.getElementById('login-prompt');
        const analysisActions = document.getElementById('analysis-actions');
        
        if (loginPrompt) {
            loginPrompt.style.display = 'none';
        }
        if (analysisActions) {
            analysisActions.style.display = 'flex';
        }
        
        // Restore scroll position if available
        const savedPosition = sessionStorage.getItem('scrollPosition');
        if (savedPosition !== null) {
            window.scrollTo(0, parseInt(savedPosition, 10));
            sessionStorage.removeItem('scrollPosition');
        }
    }
    
    updateUIAuthState() {
        if (this.isAuthenticated) {
            this.hideLoginPrompt();
            
            // Update any UI elements that depend on auth state
            const loginButtons = document.querySelectorAll('.login-required');
            loginButtons.forEach(btn => {
                btn.disabled = false;
                btn.classList.remove('disabled');
            });
        } else {
            this.showLoginPrompt();
            
            // Disable any elements that require authentication
            const loginButtons = document.querySelectorAll('.login-required');
            loginButtons.forEach(btn => {
                btn.disabled = true;
                btn.classList.add('disabled');
            });
        }
    }
    
    async init() {
        if (!this.eventInput) {
            console.warn('Event input element not found');
            return;
        }
        
        // Default to guest mode if not yet set so anonymous users can use analysis without prompt
        try {
            const existingGuest = sessionStorage.getItem('guestMode');
            if (existingGuest === null) {
                sessionStorage.setItem('guestMode', 'true');
            }
        } catch (e) {
            console.warn('Unable to access sessionStorage for guestMode:', e);
        }

        // Check authentication status
        try {
            await this.checkAuthStatus();
        } catch (error) {
            console.error('Error checking auth status during init:', error);
            // If there's an error, default to showing login prompt
            this.showLoginPrompt();
        }
        
        // Set up event listeners for login/logout
        if (this.openLoginBtn) {
            this.openLoginBtn.addEventListener('click', (e) => {
                e.preventDefault();
                window.location.href = '/admin/login';
            });
        }
        
        // Add click handler for continue as guest button
        const continueGuestBtn = document.getElementById('continue-anonymous');
        if (continueGuestBtn) {
            continueGuestBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.hideLoginPrompt();
                // Enable analysis for guest users
                if (this.analysisActions) this.analysisActions.style.display = 'flex';
                // Store guest preference in session storage
                sessionStorage.setItem('guestMode', 'true');
            });
        }
        
        // Check if user is in guest mode
        const isGuestMode = sessionStorage.getItem('guestMode') === 'true';
        
        // Initialize UI based on auth state
        if (isGuestMode) {
            this.hideLoginPrompt();
            if (this.analysisActions) this.analysisActions.style.display = 'flex';
        } else {
            // Check auth status and update UI
            await this.checkAuthStatus();
        }
        
        // Debug: Check if suggestions elements exist
        console.log('Suggestions button found:', !!this.suggestionsBtn);
        console.log('Suggestions container found:', !!this.suggestionsContainer);
        
        this.bindEvents();
        this.bindSuggestionEvents();
        
        // Set up clear analysis button if it exists
        if (this.clearAnalysisBtn) {
            this.clearAnalysisBtn.addEventListener('click', () => this.clearAnalysis());
        }
        
        // Set up login form submission
        if (this.loginForm) {
            this.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }
        
        // Ensure suggestions are initially hidden
        if (this.suggestionsContainer) {
            this.suggestionsContainer.style.display = 'none';
        }
        
        // Initialize login prompt and check auth status
        await this.initializeLoginPrompt();
        
        // Load past searches on initialization
        this.loadPastSearches();

        // Ensure analyze button reflects current input value on load
        this.updateCharCount();
    }
    
    async initializeLoginPrompt() {
        // Show login prompt for anonymous users
        const loginPrompt = document.getElementById('login-prompt');
        const continueAnonymousBtn = document.getElementById('continue-anonymous');
        
        if (loginPrompt) {
            // Check if user is authenticated
            await this.checkAuthStatus();
            
            // Respect guest mode: do not show the login prompt if guest mode is active
            const isGuestMode = sessionStorage.getItem('guestMode') === 'true';
            // If not authenticated and not in guest mode, show the login prompt
            if (!this.isAuthenticated && !isGuestMode) {
                loginPrompt.style.display = 'flex';
                
                // If there's a continue as guest button, set up its event listener
                if (continueAnonymousBtn) {
                    continueAnonymousBtn.addEventListener('click', () => {
                        loginPrompt.style.display = 'none';
                        // Store guest preference
                        sessionStorage.setItem('continueAsGuest', 'true');
                        this.isAuthenticated = true;
                        this.updateUIAuthState();
                    });
                }
            }
        }
    }
    
    // Removed duplicate checkAuthStatus method to use the async version instead
    
    setupLoginModal() {
        // Close modal when clicking the X button
        const closeButtons = document.querySelectorAll('.close-modal');
        closeButtons.forEach(btn => {
            btn.addEventListener('click', () => this.hideLoginModal());
        });
        
        // Close modal when clicking outside the modal content
        window.addEventListener('click', (e) => {
            if (e.target === this.loginModal) {
                this.hideLoginModal();
            }
        });
    }
    
    showLoginModal() {
        if (this.loginModal) {
            this.loginModal.style.display = 'block';
            document.body.style.overflow = 'hidden'; // Prevent scrolling
        }
    }
    
    hideLoginModal() {
        if (this.loginModal) {
            this.loginModal.style.display = 'none';
            document.body.style.overflow = 'auto'; // Re-enable scrolling
        }
    }
    
    async handleLogin(e) {
        e.preventDefault();
        
        const username = document.getElementById('username')?.value;
        const password = document.getElementById('password')?.value;
        
        if (!username || !password) {
            this.showError('Please enter both username and password');
            return;
        }
        
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.isAuthenticated = true;
                this.updateUIAuthState();
                this.hideLoginModal();
                this.showSuccess('Login successful!');
            } else {
                throw new Error(data.error || 'Login failed');
            }
            
        } catch (error) {
            console.error('Login error:', error);
            this.showError(error.message || 'Failed to log in. Please try again.');
        }
    }
    
    showError(message) {
        // Show error message in the UI
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-error';
        errorDiv.textContent = message;
        
        const form = document.getElementById('login-form');
        if (form) {
            form.prepend(errorDiv);
            
            // Remove error after 5 seconds
            setTimeout(() => {
                if (errorDiv.parentNode === form) {
                    form.removeChild(errorDiv);
                }
            }, 5000);
        }
    }
    
    showSuccess(message) {
        // Show success message in the UI
        const successDiv = document.createElement('div');
        successDiv.className = 'alert alert-success';
        successDiv.textContent = message;
        
        const form = document.getElementById('login-form');
        if (form) {
            form.prepend(successDiv);
            
            // Remove success message after 3 seconds
            setTimeout(() => {
                if (successDiv.parentNode === form) {
                    form.removeChild(successDiv);
                }
            }, 3000);
        }
    }
    
    bindEvents() {
        // Handle analyze button click
        if (this.analyzeBtn) {
            this.analyzeBtn.addEventListener('click', () => {
                 this.analyzeEvent();
            });
        }
        
        // Handle suggestions button click
        if (this.suggestionsBtn) {
            this.suggestionsBtn.addEventListener('click', () => this.toggleSuggestions());
        }
        
        if (this.eventInput) {
            // Add input event for character count
            this.eventInput.addEventListener('input', () => this.updateCharCount());
            
            // Add keyboard shortcut (Ctrl+Enter to submit)
            this.eventInput.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.key === 'Enter') {
                    e.preventDefault();
                    this.analyzeEvent();
                }
            });
        }
    }
    
    async analyzeEvent() {
        const eventDescription = this.eventInput.value.trim();
        
        if (!eventDescription) {
            this.showError('Please enter an event description');
            return;
        }
        
        if (!eventDescription || eventDescription.length < 10) {
            const errorMsg = 'Please provide a more detailed description of the event (at least 10 characters).';
            console.log('Validation failed:', errorMsg);
            this.showError(errorMsg);
            return;
        }
        
        console.log('Showing loading state');
        this.showLoading();
        
        try {
            // Get CSRF token from meta tag
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
            console.log('CSRF token:', csrfToken ? 'found' : 'not found');
            
            // Get selected metrics to include in analysis context
            const selectedMetrics = this.getSelectedMetrics();
            console.log('Selected metrics for context:', selectedMetrics);
            
            const requestBody = {
                event_description: eventDescription,
                selected_metrics: selectedMetrics
            };
            
            console.log('Sending request to /api/analyze-event with body:', requestBody);
            
            const startTime = Date.now();
            const response = await fetch('/api/analyze-event', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify(requestBody)
            });
            
            const responseTime = Date.now() - startTime;
            console.log(`Received response in ${responseTime}ms, status:`, response.status);
            
            if (!response.ok) {
                // Try to parse JSON body for a graceful fallback payload
                let payload = null;
                try { payload = await response.clone().json(); } catch {}
                const errorText = await response.text();
                console.error('API Error Response:', {
                    status: response.status,
                    statusText: response.statusText,
                    headers: Object.fromEntries(response.headers.entries()),
                    body: errorText
                });
                if (payload && payload.analysis) {
                    console.warn('Using server-provided fallback analysis despite non-OK status');
                    this.displayResults(payload.analysis, payload.generated_by || 'rules', payload.error || `Server returned ${response.status}`);
                    this.loadPastSearches();
                    return;
                }
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('API Response Data:', data);
            
            if (data.success && data.analysis) {
                console.log('Analysis successful, displaying results');
                this.displayResults(data.analysis, data.generated_by);
                this.loadPastSearches();
            } else {
                const note = data.error || (!data.success ? 'Using fallback due to service issue.' : '');
                const fallback = data.analysis || {
                    learning_needs: ['Clarify scope and roles', 'Decision hygiene under pressure'],
                    recommended_metrics: ['Cycle time', 'Rework rate', 'Decision quality reviews'],
                    interventions: ['Pre-mortem session', 'Decision checklist', 'Short feedback loops'],
                    success_measures: ['Fewer last-minute changes', 'Higher team confidence', 'On-time delivery']
                };
                console.warn('Rendering fallback analysis path');
                this.displayResults(fallback, data.generated_by || 'rules', note);
                this.loadPastSearches();
            }
            
        } catch (error) {
            console.error('Error in analyzeEvent:', error);
            let errorMessage = 'An error occurred while analyzing the event. ';
            
            if (error.message.includes('Failed to fetch')) {
                errorMessage += 'Please check your internet connection and try again.';
            } else if (error.message.includes('timeout') || error.message.includes('timed out')) {
                errorMessage += 'The request took too long. The AI model might be busy. Please try again in a moment.';
            } else {
                errorMessage += `Error: ${error.message}`;
            }
            
            // Render a lightweight client-side fallback so users still get value
            try {
                const fallback = {
                    learning_needs: ['Clarify scope and roles', 'Decision hygiene under pressure'],
                    recommended_metrics: ['Cycle time', 'Rework rate', 'Decision quality reviews'],
                    interventions: ['Pre-mortem session', 'Decision checklist', 'Short feedback loops'],
                    success_measures: ['Fewer last-minute changes', 'Higher team confidence', 'On-time delivery']
                };
                this.displayResults(fallback, 'rules', errorMessage);
            } catch (_) {
                this.showError(errorMessage);
            }
            
            // Reset button state
            this.analyzeBtn.disabled = false;
            this.analyzeBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M9 11H1l6-6v4h4v2z"></path>
                    <path d="M15 13h8l-6 6v-4h-4v-2z"></path>
                </svg>
                Try Again
            `;
        }
    }
    
    showLoading() {
        if (!this.analyzeBtn || !this.analysisResults || !this.analysisLoading) {
            console.error('Required elements not found for showLoading');
            return;
        }
        
        // Update analyze button
        this.analyzeBtn.disabled = true;
        this.analyzeBtn.innerHTML = `
            <div class="spinner"></div>
            Analyzing...
        `;
        
        // Show loading state
        if (this.analysisResults) this.analysisResults.style.display = 'none';
        if (this.analysisLoading) this.analysisLoading.style.display = 'block';
        
        // Clear previous results
        if (this.analysisContent) this.analysisContent.innerHTML = '';
    }
    
    bindSuggestionEvents() {
        // Bind click events to all suggestion items
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('suggestion-item')) {
                const suggestion = e.target.getAttribute('data-suggestion');
                this.applySuggestion(suggestion);
            }
        });
    }
    
    toggleSuggestions() {
        if (!this.suggestionsContainer || !this.suggestionsBtn) return;
        
        if (this.suggestionsContainer.style.display === 'none' || !this.suggestionsContainer.style.display) {
            this.showSuggestions();
        } else {
            this.hideSuggestions();
        }
    }
    
    showSuggestions() {
        if (this.suggestionsContainer) {
            this.suggestionsContainer.style.display = 'block';
            if (this.suggestionsBtn) {
                this.suggestionsBtn.textContent = 'Hide Examples';
            }
        }
    }
    
    hideSuggestions() {
        if (this.suggestionsContainer) {
            this.suggestionsContainer.style.display = 'none';
            if (this.suggestionsBtn) {
                this.suggestionsBtn.innerHTML = `
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="3"></circle>
                        <path d="M12 1v6M12 17v6M4.22 4.22l4.24 4.24M15.54 15.54l4.24 4.24M1 12h6M17 12h6M4.22 19.78l4.24-4.24M15.54 8.46l4.24-4.24"></path>
                    </svg>
                    Show Examples
                `;
            }
        }
    }
    
    applySuggestion(suggestion) {
        if (this.eventInput) {
            this.eventInput.value = suggestion;
            this.eventInput.focus();
            this.hideSuggestions();
            this.updateCharCount();
        }
    }
    
    clearAnalysis() {
        if (this.analysisResults) this.analysisResults.style.display = 'none';
        if (this.analysisLoading) this.analysisLoading.style.display = 'none';
        if (this.analysisContent) this.analysisContent.innerHTML = '';
        if (this.eventInput) this.eventInput.value = '';
        if (this.analyzeBtn) this.analyzeBtn.disabled = false;
        if (this.suggestionsContainer) this.suggestionsContainer.style.display = 'none';
    }
    
    updateCharCount() {
        if (!this.eventInput) return;
        
        const maxLength = this.eventInput.getAttribute('maxlength') || 500;
        const currentLength = this.eventInput.value.length;
        const remaining = maxLength - currentLength;
        
        // Update character counter if it exists
        const charCounter = document.querySelector('.char-counter');
        if (charCounter) {
            charCounter.textContent = `${remaining} characters remaining`;
            charCounter.style.color = remaining < 50 ? '#dc3545' : '#6c757d';
        }
        
        // Enable/disable analyze button based on input length
        if (this.analyzeBtn) {
            const isValid = currentLength >= 10 && currentLength <= maxLength;
            this.analyzeBtn.disabled = !isValid;
        }
    }
    
    formatStructuredAnalysis(analysis) {
        if (!analysis) return '<p>No analysis available.</p>';
        
        let html = '<div class="analysis-sections">';
        
        // Format each section
        const sections = [
            { key: 'learning_needs', title: 'Learning Needs', icon: '🎯' },
            { key: 'recommended_metrics', title: 'Recommended Metrics', icon: '📊' },
            { key: 'interventions', title: 'Suggested Interventions', icon: '🛠️' },
            { key: 'success_measures', title: 'Success Measures', icon: '✅' }
        ];
        
        sections.forEach(section => {
            const items = analysis[section.key];
            if (!items || !Array.isArray(items) || items.length === 0) return;
            
            html += `
                <div class="analysis-section">
                    <h4>${section.icon} ${section.title}</h4>
                    <ul class="analysis-list">
                        ${items.map(item => `<li>${this.escapeHtml(item)}</li>`).join('')}
                    </ul>
                </div>
            `;
        });
        
        html += '</div>';
        return html;
    }
    
    escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .toString()
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    displayResults(analysis, generatedBy, warningMessage = null) {
        // Store last analysis for copy-all action
        this.lastAnalysis = analysis;
        // Reset button state
        if (this.analyzeBtn) {
            this.analyzeBtn.disabled = false;
            this.analyzeBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M9 11H1l6-6v4h4v2z"></path>
                    <path d="M15 13h8l-6 6v-4h-4v-2z"></path>
                </svg>
                Analyze Event
            `;
        }
        
        // Hide loading state
        if (this.analysisLoading) {
            this.analysisLoading.style.display = 'none';
        }
        
        // Show results container
        if (this.analysisResults) {
            this.analysisResults.style.display = 'block';
        }
        
        // Display results with optional warning
        if (this.analysisContent) {
            let resultHTML = '';
            
            if (warningMessage) {
                resultHTML += `
                    <div class="alert alert-warning">
                        <strong>Note:</strong> ${warningMessage}
                    </div>`;
            }
            
            // Insert toolbar
            resultHTML += `
                <div class="analysis-toolbar" style="display:flex;justify-content:flex-end;margin-bottom:8px;gap:8px;">
                    <button id="ai-copy-all" class="btn btn-sm btn-secondary">Copy all to Plan</button>
                </div>
            `;
            resultHTML += this.formatDiagnosisAnalysis(analysis);
            
            this.analysisContent.innerHTML = resultHTML;
            
            // Scroll to results
            this.analysisContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
            // Bind copy-all handler
            const copyAllBtn = document.getElementById('ai-copy-all');
            if (copyAllBtn) {
                copyAllBtn.addEventListener('click', () => this.copyAllToPlan());
            }

            // Delegated Add-to-Plan for new cards
            this.analysisContent.addEventListener('click', async (e) => {
                const btn = e.target.closest('button[data-action="add-plan"][data-label]');
                if(!btn) return;
                const kind = (btn.getAttribute('data-kind')||'driver').toLowerCase();
                const label = btn.getAttribute('data-label')||'Item';
                await this.addToPlan(kind, label, null, { source: 'ai-event-analysis' });
            });
        }
        
        // Update source if available
        const sourceElement = document.querySelector('.analysis-source');
        if (sourceElement && generatedBy) {
            sourceElement.textContent = `Generated by: ${generatedBy}`;
        }
    }
    
    formatStructuredAnalysis(analysis) {
        console.log('Formatting structured analysis:', analysis);
        let html = '';
        
        // Helper function to safely format array items
        const formatArrayItems = (items, formatter) => {
            if (!Array.isArray(items)) {
                console.warn('Expected array but got:', typeof items, items);
                return '';
            }
            
            return items.map(item => {
                if (typeof item === 'string') {
                    // Try to parse as JSON first
                    try {
                        const parsed = JSON.parse(item);
                        if (typeof parsed === 'object' && parsed !== null) {
                            return formatObjectItem(parsed, formatter);
                        }
                        return formatter(item);
                    } catch (e) {
                        return formatter(item);
                    }
                } else if (typeof item === 'object' && item !== null) {
                    return formatObjectItem(item, formatter);
                } else {
                    return formatter(String(item));
                }
            }).join('');
        };
        
        // Helper function to format object items properly
        const formatObjectItem = (obj, formatter) => {
            if (obj.need && obj.solution) {
                return `<li><strong>Need:</strong> ${this.escapeHtml(obj.need)}<br><strong>Solution:</strong> ${this.escapeHtml(obj.solution)}${obj.success_measure ? `<br><strong>Success Measure:</strong> ${this.escapeHtml(obj.success_measure)}` : ''}</li>`;
            } else if (obj.metric && obj.target) {
                return `<li><strong>Metric:</strong> ${this.escapeHtml(obj.metric)}${obj.target ? `<br><strong>Target:</strong> ${this.escapeHtml(obj.target)}` : ''}${obj.success_measure ? `<br><strong>Success Measure:</strong> ${this.escapeHtml(obj.success_measure)}` : ''}</li>`;
            } else if (obj.name) {
                return formatter(obj.name);
            } else if (obj.description) {
                return formatter(obj.description);
            } else if (obj.topic) {
                return formatter(obj.topic);
            } else {
                // Extract all meaningful values from the object
                const values = Object.values(obj).filter(v => v && typeof v === 'string');
                return formatter(values.join(' - '));
            }
        };
        
        
        if (analysis.learning_needs && Array.isArray(analysis.learning_needs)) {
            html += `
                <h5>🎯 Key Learning Needs Identified</h5>
                <ul>
                    ${formatArrayItems(analysis.learning_needs, need => `<li><strong>${this.escapeHtml(need)}</strong></li>`)}
                </ul>
            `;
        }
        
        if (analysis.recommended_metrics && Array.isArray(analysis.recommended_metrics)) {
            html += `
                <h5>📊 Recommended Metrics to Track</h5>
                <ul>
                    ${formatArrayItems(analysis.recommended_metrics, metric => `<li>${this.escapeHtml(metric)}</li>`)}
                </ul>
            `;
        }
        
        if (analysis.interventions && Array.isArray(analysis.interventions)) {
            html += `
                <h5>🚀 Suggested L&D Interventions</h5>
                <ul>
                    ${formatArrayItems(analysis.interventions, intervention => `<li>${this.escapeHtml(intervention)}</li>`)}
                </ul>
            `;
        }
        
        if (analysis.success_measures && Array.isArray(analysis.success_measures)) {
            html += `
                <h5>✅ Success Measures</h5>
                <ul>
                    ${formatArrayItems(analysis.success_measures, measure => `<li>${this.escapeHtml(measure)}</li>`)}
                </ul>
            `;
        }
        
        // Fallback for unstructured analysis
        if (!html && analysis.analysis) {
            html = `<div class="analysis-text">${this.formatText(analysis.analysis)}</div>`;
        }
        
        return html || '<p>Analysis completed, but no specific insights were generated.</p>';
    }
    
    formatDiagnosisAnalysis(analysis){
        const a = analysis || {};
        const needs = Array.isArray(a.learning_needs) ? a.learning_needs : [];
        const metrics = Array.isArray(a.recommended_metrics) ? a.recommended_metrics : [];
        const intervs = Array.isArray(a.interventions) ? a.interventions : [];

        const htmlParts = [];

        // The Diagnosis header
        htmlParts.push(`<div class="analysis-section"><h3>🩺 The Diagnosis</h3><p>This analysis groups your input into core issues, likely behavioral root causes, and actionable drivers with measures.</p></div>`);

        // Identified Core Issues
        if(needs.length){
            htmlParts.push('<div class="analysis-section"><h3>Identified Core Issues:</h3>');
            htmlParts.push('<div class="card-list">');
            needs.forEach((n)=>{
                const name = this.escapeHtml(typeof n === 'string' ? n : (n?.name || n?.title || 'Core Issue'));
                const summary = this.escapeHtml(n?.summary || n?.description || `AI analysis suggests this is a contributing factor.`);
                const playbookUrl = `/playbook?kind=driver&q=${encodeURIComponent(name)}&filter=${encodeURIComponent('kind:driver;name:'+name)}`;
                htmlParts.push(`
                    <div class="ai-card">
                        <div class="ai-card-header">
                            <h4>🧠 ${name}</h4>
                            <div class="ai-card-actions">
                                <a class="btn btn-sm btn-primary" href="${playbookUrl}">Open in Playbook</a>
                                <button class="btn btn-sm btn-secondary" data-action="add-plan" data-kind="driver" data-label="${name}">Add to Plan</button>
                            </div>
                        </div>
                        <p class="ai-card-summary"><strong>AI Analysis:</strong> ${summary}</p>
                    </div>
                `);
            });
            htmlParts.push('</div></div>');
        }

        // Potential Root Causes (biases)
        const biases = this.deriveBiasesFromText(this.eventInput?.value || '', a.biases);
        if(biases.length){
            htmlParts.push('<div class="analysis-section"><h3>Potential Root Causes (Behavioral Biases):</h3>');
            biases.forEach((b)=>{
                const name = this.escapeHtml(b.name);
                const summary = this.escapeHtml(b.summary || 'This bias may be influencing the situation.');
                const url = `/playbook?kind=bias&q=${encodeURIComponent(name)}&filter=${encodeURIComponent('kind:bias;name:'+name)}`;
                htmlParts.push(`
                    <div class="ai-card">
                        <div class="ai-card-header">
                            <h4>${b.icon||'⚠️'} ${name}</h4>
                            <div class="ai-card-actions">
                                <a class="btn btn-sm btn-primary" href="${url}">Explore Nudges to Counteract ${name}</a>
                            </div>
                        </div>
                        <p class="ai-card-summary"><strong>AI Analysis:</strong> ${summary}</p>
                    </div>
                `);
            });
            htmlParts.push('</div>');
        }

        // KPIs for Impact
        if(metrics.length){
            htmlParts.push('<div class="analysis-section"><h3>Key Performance Indicators (KPIs) for Impact:</h3>');
            metrics.forEach((m)=>{
                const name = this.escapeHtml(typeof m === 'string' ? m : (m?.name || m?.metric || 'KPI'));
                const summary = this.escapeHtml(m?.summary || m?.why || 'Track this KPI to evaluate the impact of your interventions.');
                const url = `/playbook?kind=driver&q=${encodeURIComponent(name)}&filter=${encodeURIComponent('kind:kpi;name:'+name)}`;
                htmlParts.push(`
                    <div class="ai-card">
                        <div class="ai-card-header">
                            <h4>📊 ${name}</h4>
                            <div class="ai-card-actions">
                                <a class="btn btn-sm btn-primary" href="${url}">Open KPI in Playbook</a>
                                <button class="btn btn-sm btn-secondary" data-action="add-plan" data-kind="kpi" data-label="${name}">Add to Plan</button>
                            </div>
                        </div>
                        <p class="ai-card-summary"><strong>AI Analysis:</strong> ${summary}</p>
                    </div>
                `);
            });
            htmlParts.push('</div>');
        }

        // Actionable Interventions & Nudges
        if(intervs.length){
            htmlParts.push('<div class="analysis-section"><h3>Actionable Interventions & Nudges</h3>');
            intervs.forEach((it)=>{
                const name = this.escapeHtml(typeof it === 'string' ? it : (it?.name || it?.title || 'Intervention'));
                const summary = this.escapeHtml(it?.summary || 'Use this to influence behavior change and decision quality.');
                const url = `/playbook?kind=nudge&q=${encodeURIComponent(name)}`;
                htmlParts.push(`
                    <div class="ai-card">
                        <div class="ai-card-header">
                            <h4>🚀 ${name}</h4>
                            <div class="ai-card-actions">
                                <a class="btn btn-sm btn-primary" href="${url}">Open in Playbook</a>
                                <button class="btn btn-sm btn-secondary" data-action="add-plan" data-kind="nudge" data-label="${name}">Add to Plan</button>
                            </div>
                        </div>
                        <p class="ai-card-summary">${summary}</p>
                    </div>
                `);
            });
            // Bottom CTA: Explore nudges to counteract detected biases (chips)
            if(Array.isArray(biases) && biases.length){
                const chips = biases
                  .filter(b => b && typeof b.name === 'string' && b.name.trim().length)
                  .map(b => {
                    const title = this.escapeHtml(b.name);
                    const href = `/playbook?kind=bias&q=${encodeURIComponent(b.name)}&filter=${encodeURIComponent('kind:bias;name:'+b.name)}`;
                    return `<a class="tag-chip tag-chip--nudge" href="${href}">Explore Nudges to Counteract ${title}</a>`;
                  }).join(' ');
                htmlParts.push(`<div class="analysis-cta" style="margin-top:10px;">${chips}</div>`);
            }
            htmlParts.push('</div>');
        }
        // Ensure we always return assembled HTML so callers don't render 'undefined'
        return htmlParts.join('') || '<p>No analysis available.</p>';
    }

    deriveBiasesFromText(text, provided){
        if(Array.isArray(provided) && provided.length){
            return provided
              .map(x=>{
                if(x == null) return null;
                const name = typeof x === 'string' ? x : (typeof x.name === 'string' ? x.name : 'Bias');
                const summary = (x && typeof x.summary === 'string') ? x.summary : '';
                const icon = (x && x.icon) ? x.icon : '🧠';
                return { name, summary, icon };
              })
              .filter(Boolean);
        }
        const t = (text||'').toLowerCase();
        const out = [];
        if(/consensus|everyone|no one objected|silence/.test(t)){
            out.push({ name: 'Groupthink', summary: 'Conformity pressures may be suppressing dissent and critical evaluation.', icon: '🚫' });
        }
        if(/first idea|initial suggestion|anchored|stuck on|initial estimate|first estimate/.test(t)){
            out.push({ name: 'Anchoring Bias', summary: 'Early information may be overly influencing subsequent judgments.', icon: '⚓️' });
        }
        if(/status quo|as usual|keep doing|we always/.test(t)){
            out.push({ name: 'Status Quo Bias', summary: 'Preference for existing practices can block needed change.', icon: '🧱' });
        }
        return out;
    }

    async addToPlan(kind, label, sourceId, meta){
        try{
            await fetch('/api/context/plan/items', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ kind, label, source_id: sourceId, meta, source_page: 'diagnostics' })
            });
        }catch(e){ console.warn('Add to Plan failed', e); }
    }

    formatText(text) {
        // Basic text formatting
        return text
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/^\s*/, '<p>')
            .replace(/\s*$/, '</p>');
    }
    
    showError(message) {
        console.error('Analysis error:', message);
        
        // Reset button state
        if (this.analyzeBtn) {
            this.analyzeBtn.disabled = false;
            this.analyzeBtn.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M9 11H1l6-6v4h4v2z"></path>
                    <path d="M15 13h8l-6 6v-4h-4v-2z"></path>
                </svg>
                Try Again
            `;
        }
        
        // Hide loading state
        if (this.analysisLoading) {
            this.analysisLoading.style.display = 'none';
        }
        
        // Show results container
        if (this.analysisResults) {
            this.analysisResults.style.display = 'block';
        }
        
        // Display error message
        if (this.analysisContent) {
            this.analysisContent.innerHTML = `
                <div class="alert alert-danger">
                    <div class="d-flex align-items-center">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="me-2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                        <div>
                            <h5 class="alert-heading">Analysis Error</h5>
                            <p class="mb-0">${this.escapeHtml(message)}</p>
                            <p class="mb-0 mt-2">Please try again or contact support if the problem persists.</p>
                        </div>
                    </div>
                </div>
            `;
            
            // Scroll to error message
            this.analysisContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
        // Update source to indicate error
        const sourceElement = document.querySelector('.analysis-source');
        if (sourceElement) {
            sourceElement.textContent = 'Error occurred during analysis';
            sourceElement.classList.add('text-danger');
        }
    }
    
    async loadPastSearches() {
        // Load and display past event analysis searches
        if (!this.pastSearchesContainer || !this.pastSearchesList) {
            console.log('Past searches elements not found, skipping load');
            return;
        }
        
        try {
            const response = await fetch('/api/event-analyses/recent?limit=5');
            const data = await response.json();
            
            if (data.success && data.analyses && data.analyses.length > 0) {
                this.displayPastSearches(data.analyses);
                this.pastSearchesContainer.style.display = 'block';
            } else {
                this.pastSearchesContainer.style.display = 'none';
            }
        } catch (error) {
            console.error('Error loading past searches:', error);
            this.pastSearchesContainer.style.display = 'none';
        }
    }
    
    displayPastSearches(analyses) {
        // Display past searches in the UI
        if (!this.pastSearchesList) return;
        
        this.pastSearchesList.innerHTML = '';
        
        analyses.forEach((analysis, index) => {
            const listItem = document.createElement('div');
            listItem.className = 'past-search-item';
            listItem.innerHTML = `
                <div class="past-search-content">
                    <div class="past-search-text">${this.escapeHtml(analysis.display_text)}</div>
                    <div class="past-search-meta">
                        <small class="text-muted">
                            ${this.formatDate(analysis.created_date)} • 
                            Generated by ${analysis.generated_by}
                        </small>
                    </div>
                </div>
            `;
            
            // Make clickable to reuse the search
            listItem.style.cursor = 'pointer';
            listItem.addEventListener('click', () => {
                this.reusePastSearch(analysis.event_description);
            });
            
            this.pastSearchesList.appendChild(listItem);
        });
    }
    
    reusePastSearch(eventDescription) {
        // Reuse a past search by filling the input field
        if (this.eventInput) {
            this.eventInput.value = eventDescription;
            this.eventInput.focus();
            this.updateCharCount();
            
            // Scroll to the input
            this.eventInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
    
    formatDate(dateString) {
        // Format date for display
        if (!dateString) return 'Unknown date';
        
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffMins = Math.floor(diffMs / 60000);
            const diffHours = Math.floor(diffMs / 3600000);
            const diffDays = Math.floor(diffMs / 86400000);
            
            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m ago`;
            if (diffHours < 24) return `${diffHours}h ago`;
            if (diffDays < 7) return `${diffDays}d ago`;
            
            return date.toLocaleDateString();
        } catch (error) {
            return 'Unknown date';
        }
    }
    
    getSelectedMetrics() {
        // Get currently selected metrics from the application state
        const selectedMetrics = [];
        
        // Try to get from global state first
        if (window.selectedMetrics && Array.isArray(window.selectedMetrics)) {
            return window.selectedMetrics.map(metric => ({
                id: metric.id,
                name: metric.name,
                category: metric.category,
                description: metric.description
            }));
        }
        
        // Fallback: get from DOM elements if available
        const selectedCards = document.querySelectorAll('.metric-card.selected, .metric-card.active');
        selectedCards.forEach(card => {
            const metricData = {
                id: card.dataset.metricId || card.id,
                name: card.querySelector('.metric-name, .card-title, h3, h4')?.textContent?.trim(),
                category: card.dataset.category || card.querySelector('.metric-category')?.textContent?.trim(),
                description: card.querySelector('.metric-description, .card-text, p')?.textContent?.trim()
            };
            
            if (metricData.id && metricData.name) {
                selectedMetrics.push(metricData);
            }
        });
        
        // Also check for checked checkboxes in metric lists
        const checkedMetrics = document.querySelectorAll('input[type="checkbox"]:checked[data-metric-id]');
        checkedMetrics.forEach(checkbox => {
            const metricId = checkbox.dataset.metricId;
            const metricName = checkbox.closest('.metric-item, .list-item')?.querySelector('.metric-name, .item-name')?.textContent?.trim();
            
            if (metricId && metricName && !selectedMetrics.find(m => m.id === metricId)) {
                selectedMetrics.push({
                    id: metricId,
                    name: metricName,
                    category: checkbox.dataset.category || 'Unknown',
                    description: checkbox.dataset.description || ''
                });
            }
        });
        
        console.log('Found selected metrics:', selectedMetrics);
        return selectedMetrics;
    }
}

// Initialize EventAnalyzer when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.eventAnalyzer = new EventAnalyzer();
});

// Also initialize immediately if DOM is already loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        if (!window.eventAnalyzer) {
            window.eventAnalyzer = new EventAnalyzer();
        }
    });
} else {
    // DOM is already loaded
    if (!window.eventAnalyzer) {
        window.eventAnalyzer = new EventAnalyzer();
    }
}

// Export for potential use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = EventAnalyzer;
}
