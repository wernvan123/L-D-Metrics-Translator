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
        this.isAnalyzing = false;
        
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
        if (this.isAnalyzing) {
            console.warn('AnalyzeEvent skipped: request already in progress');
            return;
        }

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
        if (this.analysisContent) {
            this.analysisContent.dataset.rendered = 'false';
        }
        this.isAnalyzing = true;
        
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

            // Keep KB payload for rendering alongside the core analysis
            this.lastKnowledgeBase = data.kb || null;

            if (data.success && data.analysis) {
                console.log('Analysis successful, displaying results');
                this.displayResults(data.analysis, data.generated_by, null, this.lastKnowledgeBase);
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
                this.displayResults(fallback, data.generated_by || 'rules', note, this.lastKnowledgeBase);
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
                this.displayResults(fallback, 'rules', errorMessage, this.lastKnowledgeBase);
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

    displayResults(analysis, generatedBy, warningMessage = null, knowledgeBase = null) {
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
            // Guard against double render if multiple responses race in
            if (this.isAnalyzing === false && this.analysisContent.dataset.rendered === 'true') {
                console.warn('displayResults skipped: stale render attempt detected');
                return;
            }
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
            resultHTML += this.formatDiagnosisAnalysis(analysis, knowledgeBase?.biases || []);
            
            this.analysisContent.innerHTML = resultHTML;
            this.analysisContent.dataset.rendered = 'true';
            
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
        if (!analysis || typeof analysis !== 'object') {
            return '<p>No analysis available.</p>';
        }

        const buildList = (items, formatter) => {
            if (!Array.isArray(items) || !items.length) return '';
            return items.map((item) => {
                if (item == null) return '';
                if (typeof item === 'string') {
                    return formatter({ name: item });
                }
                if (typeof item === 'object') {
                    return formatter(item);
                }
                return formatter({ name: String(item) });
            }).join('');
        };

        let html = '';

        const needsList = buildList(analysis.learning_needs, (item) => {
            const name = this.escapeHtml(item.name || 'Learning need');
            const summary = item.summary ? ` – ${this.escapeHtml(item.summary)}` : '';
            return `<li><strong>${name}</strong>${summary}</li>`;
        });
        if (needsList) {
            html += `
                <h5>🎯 Key Learning Needs Identified</h5>
                <ul>${needsList}</ul>
            `;
        }

        const metricsList = buildList(analysis.recommended_metrics, (item) => {
            const name = this.escapeHtml(item.name || item.metric || 'Metric');
            const summary = item.summary ? ` – ${this.escapeHtml(item.summary)}` : '';
            const target = item.success_measure || item.target;
            const targetHtml = target ? ` <em>(Target: ${this.escapeHtml(target)})</em>` : '';
            return `<li>${name}${summary}${targetHtml}</li>`;
        });
        if (metricsList) {
            html += `
                <h5>📊 Recommended Metrics to Track</h5>
                <ul>${metricsList}</ul>
            `;
        }

        const interventionsList = buildList(analysis.interventions, (item) => {
            const name = this.escapeHtml(item.name || item.title || 'Intervention');
            const summary = item.summary ? ` – ${this.escapeHtml(item.summary)}` : '';
            return `<li>${name}${summary}</li>`;
        });
        if (interventionsList) {
            html += `
                <h5>🚀 Suggested L&D Interventions</h5>
                <ul>${interventionsList}</ul>
            `;
        }

        const successList = buildList(analysis.success_measures, (item) => {
            const name = this.escapeHtml(item.name || item.metric || 'Success Measure');
            const summary = item.summary ? ` – ${this.escapeHtml(item.summary)}` : '';
            return `<li>${name}${summary}</li>`;
        });
        if (successList) {
            html += `
                <h5>✅ Success Measures</h5>
                <ul>${successList}</ul>
            `;
        }

        if (!html) {
            const raw = analysis?.analysis || analysis?._meta?.raw_response;
            if (typeof raw === 'string' && raw.trim()) {
                html = `<div class="analysis-text">${this.formatText(raw)}</div>`;
            }
        }

        return html || '<p>Analysis completed, but no specific insights were generated.</p>';
    }
    
    formatDiagnosisAnalysis(analysis, knowledgeBaseBiases = []){
        const a = analysis || {};
        const needs = Array.isArray(a.learning_needs) ? a.learning_needs : [];
        const metrics = Array.isArray(a.recommended_metrics) ? a.recommended_metrics : [];
        const intervs = Array.isArray(a.interventions) ? a.interventions : [];
        const htmlParts = [];

        // The Diagnosis header
        htmlParts.push(`<div class="analysis-section"><h3>🩺 The Diagnosis</h3><p>This analysis groups your input into core issues, likely behavioral root causes, and actionable drivers with measures.</p></div>`);

        // Identified Core Issues
        if(needs.length){
            htmlParts.push('<div class="analysis-section analysis-section--issues">');
            htmlParts.push('<h3>🎯 Identified Core Issues</h3>');
            htmlParts.push('<p class="meta">Themes the AI highlighted as underlying blockers that deserve immediate focus.</p>');
            htmlParts.push('<div class="ai-card-grid">');
            needs.forEach((n)=>{
                const name = this.escapeHtml(typeof n === 'string' ? n : (n?.name || n?.title || 'Core Issue'));
                const summary = this.escapeHtml(n?.summary || n?.description || `AI analysis suggests this is a contributing factor.`);
                const playbookUrl = `/playbook?kind=driver&q=${encodeURIComponent(name)}&filter=${encodeURIComponent('kind:driver;name:'+name)}`;
                htmlParts.push(`
                    <div class="ai-card ai-card--issue">
                        <div class="ai-card-header">
                            <h4>🎯 ${name}</h4>
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
        const biases = this.deriveBiasesFromText(
            this.eventInput?.value || '',
            Array.isArray(a.behavioral_biases) ? a.behavioral_biases : (Array.isArray(a.biases) ? a.biases : []),
            Array.isArray(knowledgeBaseBiases) ? knowledgeBaseBiases : [],
        ).slice(0, 5);
        htmlParts.push('<div class="analysis-section analysis-section--biases">');
        htmlParts.push('<h3>🧠 Potential Root Causes (Behavioral Biases)</h3>');
        htmlParts.push('<p class="meta">These patterns may be amplifying the issues surfaced above. Address them with targeted nudges and safeguards.</p>');
        if(biases.length){
            htmlParts.push('<div class="ai-card-grid ai-card-grid--single">');
            biases.forEach((b)=>{
                const name = this.escapeHtml(b.name);
                const description = this.escapeHtml(b.description || 'This bias may be influencing the situation.');
                const impact = b.impact ? `<p class="ai-card-impact"><strong>Impact:</strong> ${this.escapeHtml(b.impact)}</p>` : '';
                const counter = Array.isArray(b.countermeasures) && b.countermeasures.length
                    ? `<div class="ai-card-countermeasures"><strong>Countermeasures:</strong><ul>${b.countermeasures.map(cm => `<li>${this.escapeHtml(cm)}</li>`).join('')}</ul></div>`
                    : '';
                const framework = b.related_framework ? `<p class="meta">Framework: ${this.escapeHtml(b.related_framework)}</p>` : '';
                const url = `/playbook?kind=bias&q=${encodeURIComponent(name)}&filter=${encodeURIComponent('kind:bias;name:'+name)}`;
                htmlParts.push(`
                    <div class="ai-card ai-card--bias">
                        <div class="ai-card-header">
                            <h4>${b.icon || '🧠'} ${name}</h4>
                            <div class="ai-card-actions">
                                <a class="btn btn-sm btn-primary" href="${url}">Explore Nudges to Counteract Bias</a>
                            </div>
                        </div>
                        <p class="ai-card-summary">${description}</p>
                        ${impact}
                        ${counter}
                        ${framework}
                    </div>
                `);
            });
            htmlParts.push('</div>');
        } else {
            htmlParts.push(`
                <div class="ai-card ai-card--bias ai-card--empty">
                    <div class="ai-card-header">
                        <h4>🧠 No Bias Signals Detected Yet</h4>
                    </div>
                    <p class="ai-card-summary">The AI couldnt confidently surface behavioral biases from this description. Try adding more context on decision dynamics, dissent, or pressures, or explore the Playbook for common bias patterns.</p>
                </div>
            `);
        }
        htmlParts.push('</div>');

        // KPIs for Impact
        if(metrics.length){
            htmlParts.push('<div class="analysis-section analysis-section--kpis">');
            htmlParts.push('<h3>📊 Key Performance Indicators (KPIs) for Impact</h3>');
            htmlParts.push('<p class="meta">Track these signals to understand whether interventions are improving outcomes.</p>');
            htmlParts.push('<div class="ai-card-grid">');
            metrics.forEach((m)=>{
                const isObj = m && typeof m === 'object';
                const name = this.escapeHtml(isObj ? (m.name || m.metric || 'KPI') : String(m));
                const summary = this.escapeHtml(isObj ? (m.summary || m.why || m.details || 'Track this KPI to evaluate the impact of your interventions.') : 'Track this KPI to evaluate the impact of your interventions.');
                const target = isObj ? (m.success_measure || m.target) : null;
                const url = `/playbook?kind=driver&q=${encodeURIComponent(name)}&filter=${encodeURIComponent('kind:kpi;name:'+name)}`;
                htmlParts.push(`
                    <div class="ai-card ai-card--kpi">
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
            htmlParts.push('</div></div>');
        }

        // Actionable Interventions & Nudges
        if(intervs.length){
            htmlParts.push('<div class="analysis-section analysis-section--interventions">');
            htmlParts.push('<h3>🛠️ Actionable Interventions & Nudges</h3>');
            htmlParts.push('<p class="meta">Deploy these actions to counter the biases and reinforce desired behaviors.</p>');
            htmlParts.push('<div class="ai-card-grid">');
            intervs.forEach((it)=>{
                const isObj = it && typeof it === 'object';
                const name = this.escapeHtml(isObj ? (it.name || it.title || 'Intervention') : String(it));
                const summary = this.escapeHtml(isObj ? (it.summary || it.details || 'Use this to influence behavior change and decision quality.') : 'Use this to influence behavior change and decision quality.');
                const url = `/playbook?kind=nudge&q=${encodeURIComponent(name)}`;
                htmlParts.push(`
                    <div class="ai-card ai-card--intervention">
                        <div class="ai-card-header">
                            <h4>🛠️ ${name}</h4>
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
                htmlParts.push(`<div class="analysis-cta">${chips}</div>`);
            }
            htmlParts.push('</div></div>');
        }
        // Ensure we always return assembled HTML so callers don't render 'undefined'
        return htmlParts.join('') || '<p>No analysis available.</p>';
    }

    deriveBiasesFromText(text, provided, knowledgeBaseBiases = []){
        const normalizeBias = (entry) => {
            if (entry == null) return null;
            if (typeof entry === 'string') {
                return {
                    name: entry,
                    description: '',
                    impact: '',
                    countermeasures: [],
                    related_framework: null,
                    icon: '🧠'
                };
            }
            const name = typeof entry.name === 'string'
                ? entry.name
                : (typeof entry.heading === 'string' ? entry.heading : (typeof entry.title === 'string' ? entry.title : 'Bias'));
            const description = entry.description || entry.short_description || entry.summary || entry.detailed_description || '';
            const impact = entry.impact || entry.effect || '';
            const counter = Array.isArray(entry.countermeasures)
                ? entry.countermeasures.filter(Boolean).map(String)
                : Array.isArray(entry.actions)
                    ? entry.actions.filter(Boolean).map(String)
                    : [];
            const framework = entry.related_framework || entry.framework || entry.model_framework || entry.model || null;
            const icon = entry.icon || '🧠';
            return {
                name,
                description,
                impact,
                countermeasures: counter,
                related_framework: framework,
                icon
            };
        };

        const direct = Array.isArray(provided) && provided.length
            ? provided.map(normalizeBias).filter(Boolean)
            : [];

        const kbDerived = Array.isArray(knowledgeBaseBiases) && knowledgeBaseBiases.length
            ? knowledgeBaseBiases.map(normalizeBias).filter(Boolean)
            : [];

        const combined = [...direct, ...kbDerived].filter(Boolean);
        if (combined.length) {
            return combined;
        }

        const t = (text || '').toLowerCase();
        const out = [];
        if (/consensus|everyone|no one objected|silence|unanimous/.test(t)) {
            out.push({
                name: 'Groupthink',
                description: 'Pressure for harmony encourages members to suppress warning signals or dissent.',
                impact: 'Critical feedback is withheld, reducing decision quality and risk detection.',
                countermeasures: ['Assign a devil\'s advocate each review', 'Run rapid pre-mortems before key decisions'],
                related_framework: null,
                icon: '🚫'
            });
        }
        if (/first idea|initial suggestion|anchored|stuck on|initial estimate|first estimate/.test(t)) {
            out.push({
                name: 'Anchoring Bias',
                description: 'The team may be over-weighting the earliest information shared.',
                impact: 'Later evidence is undervalued, leading to narrow solution exploration.',
                countermeasures: ['Collect independent estimates before discussion', 'Reveal data ranges before debating solutions'],
                related_framework: null,
                icon: '⚓️'
            });
        }
        if (/status quo|as usual|keep doing|we always/.test(t)) {
            out.push({
                name: 'Status Quo Bias',
                description: 'Defaulting to existing practices despite signals that change is needed.',
                impact: 'Opportunities for improvement or risk mitigation are delayed.',
                countermeasures: ['Highlight switching benefits versus staying put', 'Pilot a time-boxed experiment with review checkpoints'],
                related_framework: null,
                icon: '🧱'
            });
        }
        if (/(senior|executive|leader|leadership|manager|director).*(said|told|insist|decided|must do|demanded)/.test(t) || /(because leadership already decided)/.test(t)) {
            out.push({
                name: 'Authority Bias',
                description: 'Team members defer to the view of an authority figure even when evidence points elsewhere.',
                impact: 'Risks or defects raised by subject matter experts are dismissed without evaluation.',
                countermeasures: ['Collect anonymous input before leaders speak', 'Ask for evidence-based rationale from decision makers', 'Rotate facilitation duties so no single leader dominates'],
                related_framework: 'Decision Quality Safeguards',
                icon: '👔'
            });
        }
        if (/(hesitant|stopped speaking up|won\'t speak up|afraid to speak|fear retaliation|stay silent)/.test(t)) {
            out.push({
                name: 'Spiral of Silence',
                description: 'Perceived social pressure or fear of backlash shuts down constructive dissent.',
                impact: 'Important risks remain hidden because contributors no longer feel psychologically safe.',
                countermeasures: ['Set explicit norms for dissent-friendly discussions', 'Use round-robin sharing or anonymous inputs', 'Leaders model curiosity by asking follow-up questions'],
                related_framework: 'Psychological Safety',
                icon: '🔇'
            });
        }
        if (/interrupt|talked over|cut off|dismissing concerns/.test(t)) {
            out.push({
                name: 'Dominance Bias',
                description: 'A forceful communicator overrides others, skewing how information is weighted.',
                impact: 'Critical insights from quieter contributors never reach the decision table.',
                countermeasures: ['Use facilitation that enforces speaking order', 'Summarize and reflect each contribution before moving on'],
                related_framework: null,
                icon: '🗣️'
            });
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
